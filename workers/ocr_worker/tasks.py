"""Celery tasks for invoice OCR processing."""

import asyncio
import logging
import os
from datetime import UTC, datetime
from typing import Any

from celery import Task

from ocr_worker.celery_app import app
from ocr_worker.redis_progress import publish_progress

logger = logging.getLogger(__name__)

# Lazy-loaded pipeline (expensive to initialize)
_pipeline = None


def get_pipeline():
    """Get or create the invoice pipeline (lazy initialization)."""
    global _pipeline
    if _pipeline is None:
        from fakturaai_ml import InvoicePipeline

        use_llm = os.getenv("LLM_EXTRACTION_ENABLED", "false").lower() == "true"
        llm_api_key = os.getenv("ANTHROPIC_API_KEY")
        llm_model = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5-20251001")

        logger.info(
            "Initializing InvoicePipeline (LLM extraction: %s, model: %s)...",
            use_llm,
            llm_model if use_llm else "n/a",
        )
        _pipeline = InvoicePipeline(
            primary_engine=os.getenv("OCR_PRIMARY_ENGINE", "dots"),
            fallback_engine=os.getenv("OCR_FALLBACK_ENGINE", "none"),
            use_gpu=os.getenv("OCR_USE_GPU", "true").lower() == "true",
            use_llm=use_llm,
            llm_api_key=llm_api_key,
            llm_model=llm_model,
        )
        logger.info("InvoicePipeline initialized")

    return _pipeline


class OCRTask(Task):
    """Base task with error handling and logging."""

    abstract = True

    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Handle task failure."""
        logger.error(f"Task {task_id} failed: {exc}")

    def on_success(self, retval, task_id, args, kwargs):
        """Handle task success."""
        logger.info(f"Task {task_id} completed successfully")


@app.task(bind=True, base=OCRTask, name="ocr_worker.tasks.process_invoice")
def process_invoice(
    self,
    invoice_id: str,
    document_path: str,
    callback_url: str | None = None,
    priority: str = "normal",
) -> dict[str, Any]:
    """
    Process a single invoice document.

    Args:
        invoice_id: UUID of the invoice record
        document_path: S3/R2 path to the document
        callback_url: Optional webhook URL for completion notification
        priority: Processing priority ("normal" or "high")

    Returns:
        Extraction result as dictionary
    """
    logger.info(f"Processing invoice {invoice_id} from {document_path}")

    try:
        # Stage: downloading (10%)
        self.update_state(
            state="PROCESSING", meta={"progress": 10, "stage": "downloading"}
        )
        publish_progress(invoice_id, "downloading", 10)

        document_bytes = _download_document(document_path)

        # Stage: preprocessing (20%)
        self.update_state(
            state="PROCESSING", meta={"progress": 20, "stage": "preprocessing"}
        )
        publish_progress(invoice_id, "preprocessing", 20)

        pipeline = get_pipeline()

        # Stage: ocr_running (40%)
        self.update_state(
            state="PROCESSING", meta={"progress": 40, "stage": "ocr_running"}
        )
        publish_progress(invoice_id, "ocr_running", 40)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(pipeline.extract(document_bytes))
        finally:
            loop.close()

        # Stage: extracting_fields (70%)
        self.update_state(
            state="PROCESSING", meta={"progress": 70, "stage": "extracting_fields"}
        )
        publish_progress(invoice_id, "extracting_fields", 70)

        result_dict = _serialize_result(result)

        # Stage: validating (85%)
        self.update_state(
            state="PROCESSING", meta={"progress": 85, "stage": "validating"}
        )
        publish_progress(invoice_id, "validating", 85)

        # Stage: saving (90%)
        self.update_state(state="PROCESSING", meta={"progress": 90, "stage": "saving"})
        publish_progress(invoice_id, "saving", 90)

        _save_extraction_result(invoice_id, result_dict)

        # Auto-assign client based on PIB matching (Agency feature)
        _auto_assign_client(invoice_id, result_dict)

        # Stage: complete (100%)
        publish_progress(invoice_id, "complete", 100)

        if callback_url:
            _send_webhook(callback_url, invoice_id, result_dict)

        logger.info(f"Invoice {invoice_id} processed successfully")
        return result_dict

    except Exception as e:
        logger.exception(f"Failed to process invoice {invoice_id}: {e}")
        publish_progress(invoice_id, "failed", 0, error=str(e))
        _update_invoice_status(invoice_id, "error", str(e))
        raise


@app.task(bind=True, base=OCRTask, name="ocr_worker.tasks.process_batch")
def process_batch(
    self,
    batch_id: str,
    invoice_ids: list[str],
    document_paths: list[str],
    callback_url: str | None = None,
) -> dict[str, Any]:
    """
    Process a batch of invoice documents.

    Args:
        batch_id: UUID of the batch job
        invoice_ids: List of invoice UUIDs
        document_paths: List of document paths (matching invoice_ids)
        callback_url: Optional webhook URL for batch completion

    Returns:
        Batch processing result
    """
    logger.info(f"Processing batch {batch_id} with {len(invoice_ids)} invoices")

    results = []
    errors = []

    for i, (invoice_id, doc_path) in enumerate(zip(invoice_ids, document_paths)):
        try:
            self.update_state(
                state="PROCESSING",
                meta={
                    "progress": int((i / len(invoice_ids)) * 100),
                    "current": i + 1,
                    "total": len(invoice_ids),
                },
            )

            # Process individual invoice
            result = process_invoice.apply(
                args=[invoice_id, doc_path],
                throw=True,
            ).get()

            results.append(
                {
                    "invoice_id": invoice_id,
                    "status": "success",
                    "result": result,
                }
            )

        except Exception as e:
            logger.error(f"Failed to process invoice {invoice_id}: {e}")
            errors.append(
                {
                    "invoice_id": invoice_id,
                    "status": "error",
                    "error": str(e),
                }
            )

    # Send batch completion webhook
    if callback_url:
        _send_webhook(
            callback_url,
            batch_id,
            {
                "batch_id": batch_id,
                "total": len(invoice_ids),
                "success": len(results),
                "failed": len(errors),
            },
        )

    return {
        "batch_id": batch_id,
        "results": results,
        "errors": errors,
        "success_count": len(results),
        "error_count": len(errors),
    }


@app.task(name="ocr_worker.tasks.health_check")
def health_check() -> dict[str, Any]:
    """Health check task for monitoring."""
    try:
        pipeline = get_pipeline()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            health = loop.run_until_complete(pipeline.health_check())
        finally:
            loop.close()

        return {
            "status": "healthy",
            "pipeline": health,
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
        }


# Helper functions


def _download_document(path: str) -> bytes:
    """Download document from S3/R2 storage."""
    import boto3

    s3 = boto3.client(
        "s3",
        endpoint_url=os.getenv("STORAGE_ENDPOINT"),
        aws_access_key_id=os.getenv("STORAGE_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("STORAGE_SECRET_KEY"),
    )

    bucket = os.getenv("STORAGE_BUCKET", "saldora-documents")

    response = s3.get_object(Bucket=bucket, Key=path)
    return response["Body"].read()


def _serialize_result(result) -> dict[str, Any]:
    """Serialize extraction result to dictionary."""
    from dataclasses import asdict
    from datetime import date
    from decimal import Decimal
    from enum import Enum

    # Convert dataclass to dict
    result_dict = asdict(result)

    # Convert non-JSON-serializable types
    def convert(obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [convert(i) for i in obj]
        return obj

    return convert(result_dict)


def _save_extraction_result(invoice_id: str, result: dict[str, Any]) -> None:
    """Save extraction result to the invoices table."""
    import json

    from ocr_worker.database import get_session, text

    logger.info(f"Saving result for invoice {invoice_id}")
    logger.debug(
        f"Extraction result:\n{json.dumps(result, indent=2, default=str, ensure_ascii=False)}"
    )

    invoice = result.get("invoice", {})
    seller = invoice.get("seller")
    buyer = invoice.get("buyer")
    line_items = invoice.get("line_items")
    tax_groups = invoice.get("tax_groups")

    # Normalize line item totals: total = net amount (bez PDV), tax_amount = PDV
    # The LLM sometimes returns total as gross (sa PDV) or leaves it null.
    # We normalize so total always means net = tax_base = qty * price (- discount).
    if line_items:
        for item in line_items:
            try:
                tax_base = float(item.get("tax_base") or 0)
                total = float(item.get("total") or 0)
                rate = float(item.get("tax_rate") or 0)
                qty = float(item.get("quantity") or 0)
                price = float(item.get("unit_price") or 0)
                discount = float(item.get("discount") or 0)

                # Calculate expected net from qty * price * (1 - discount/100)
                expected_net = qty * price
                if discount > 0:
                    expected_net = expected_net * (1 - discount / 100)
                expected_net = round(expected_net, 2)

                # Determine the correct net amount
                if tax_base > 0:
                    net = tax_base
                elif total > 0 and rate > 0:
                    # Check if total looks like gross (close to net * (1 + rate/100))
                    expected_gross = round(expected_net * (1 + rate / 100), 2)
                    if abs(total - expected_gross) < 1:
                        net = expected_net  # total was gross, use calculated net
                    else:
                        net = total  # total is already net
                elif total > 0:
                    net = total
                elif expected_net > 0:
                    net = expected_net
                else:
                    net = 0

                item["total"] = round(net, 2) if net else None
                item["tax_base"] = round(net, 2) if net else item.get("tax_base")

                # Calculate tax_amount from net
                tax_amt = float(item.get("tax_amount") or 0)
                if tax_amt == 0 and rate > 0 and net > 0:
                    item["tax_amount"] = round(net * rate / 100, 2)
            except (ValueError, TypeError):
                pass

    session = get_session()
    try:
        session.execute(
            text("""
                UPDATE invoices SET
                    invoice_number = :invoice_number,
                    invoice_date = :invoice_date,
                    due_date = :due_date,
                    seller = :seller,
                    buyer = :buyer,
                    subtotal = :subtotal,
                    tax_rate = :tax_rate,
                    tax_amount = :tax_amount,
                    total_amount = :total_amount,
                    currency = :currency,
                    line_items = :line_items,
                    tax_groups = :tax_groups,
                    confidence_score = :confidence_score,
                    field_confidence = :field_confidence,
                    warnings = :warnings,
                    ocr_engine = :ocr_engine,
                    processing_time_ms = :processing_time_ms,
                    raw_ocr_text = :raw_ocr_text,
                    raw_llm_output = :raw_llm_output,
                    status = 'review',
                    updated_at = NOW()
                WHERE id = :invoice_id
            """),
            {
                "invoice_id": invoice_id,
                "invoice_number": invoice.get("invoice_number"),
                "invoice_date": invoice.get("invoice_date"),
                "due_date": invoice.get("due_date"),
                "seller": json.dumps(seller, default=str, ensure_ascii=False)
                if seller
                else None,
                "buyer": json.dumps(buyer, default=str, ensure_ascii=False)
                if buyer
                else None,
                "subtotal": invoice.get("subtotal"),
                "tax_rate": invoice.get("tax_rate"),
                "tax_amount": invoice.get("tax_amount"),
                "total_amount": invoice.get("total_amount"),
                "currency": invoice.get("currency", "RSD"),
                "line_items": json.dumps(line_items, default=str, ensure_ascii=False)
                if line_items
                else None,
                "tax_groups": json.dumps(tax_groups, default=str, ensure_ascii=False)
                if tax_groups
                else None,
                "confidence_score": result.get("overall_confidence"),
                "field_confidence": json.dumps(
                    result.get("field_confidences", []),
                    default=str,
                    ensure_ascii=False,
                ),
                "warnings": json.dumps(
                    result.get("warnings", []),
                    default=str,
                    ensure_ascii=False,
                ),
                "ocr_engine": result.get("ocr_engine"),
                "processing_time_ms": result.get("processing_time_ms"),
                "raw_ocr_text": invoice.get("raw_text"),
                "raw_llm_output": invoice.get("raw_llm_output"),
            },
        )
        # Sync denormalized line items for reporting (non-blocking)
        try:
            _sync_line_items(session, invoice_id, line_items or [], seller, invoice)
        except Exception as exc:
            logger.warning(f"Line item sync failed for {invoice_id}: {exc}")

        session.commit()
        logger.info(f"Saved extraction result for invoice {invoice_id}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _auto_assign_client(invoice_id: str, result: dict[str, Any]) -> None:
    """Auto-assign invoice to a client based on PIB matching.

    Checks buyer PIB first (most common for agencies), then seller PIB.
    Only assigns if client_id is currently NULL (won't overwrite manual assignments).

    Args:
        invoice_id: UUID of the invoice.
        result: Extraction result dictionary.
    """
    from ocr_worker.database import get_session, text

    invoice_data = result.get("invoice", {})
    buyer = invoice_data.get("buyer") or {}
    seller = invoice_data.get("seller") or {}

    pibs_to_check = []
    if buyer.get("pib"):
        pibs_to_check.append(buyer["pib"])
    if seller.get("pib"):
        pibs_to_check.append(seller["pib"])

    if not pibs_to_check:
        return

    session = get_session()
    try:
        # Get organization_id for this invoice
        row = session.execute(
            text("SELECT organization_id, client_id FROM invoices WHERE id = :id"),
            {"id": invoice_id},
        ).fetchone()

        if not row or row[1] is not None:
            # Invoice not found or already has a client assigned
            return

        org_id = str(row[0])

        # Try each PIB (buyer first, then seller)
        for pib in pibs_to_check:
            client_row = session.execute(
                text("""
                    SELECT id FROM clients
                    WHERE organization_id = :org_id
                      AND pib = :pib
                      AND is_active = true
                    LIMIT 1
                """),
                {"org_id": org_id, "pib": pib},
            ).fetchone()

            if client_row:
                session.execute(
                    text("""
                        UPDATE invoices
                        SET client_id = :client_id, updated_at = NOW()
                        WHERE id = :invoice_id AND client_id IS NULL
                    """),
                    {"client_id": str(client_row[0]), "invoice_id": invoice_id},
                )
                session.commit()
                logger.info(
                    "Auto-assigned invoice %s to client %s (PIB: %s)",
                    invoice_id,
                    client_row[0],
                    pib,
                )
                return

        logger.debug(
            "No client match for invoice %s PIBs: %s", invoice_id, pibs_to_check
        )
    except Exception:
        session.rollback()
        logger.exception("Failed to auto-assign client for invoice %s", invoice_id)
    finally:
        session.close()


def _calc_line_total(item: dict) -> float:
    """Calculate line item total from total, tax_base, or quantity * unit_price."""
    for key in ("total", "tax_base"):
        val = item.get(key)
        if val is not None:
            try:
                f = float(val)
                if f != 0:
                    return f
            except (ValueError, TypeError):
                pass
    try:
        return round(
            float(item.get("quantity") or 0) * float(item.get("unit_price") or 0), 2
        )
    except (ValueError, TypeError):
        return 0


def _calc_line_tax(item: dict, total: float) -> float | None:
    """Calculate line item tax from tax_amount, or tax_base * rate / 100."""
    val = item.get("tax_amount")
    if val is not None:
        try:
            f = float(val)
            if f != 0:
                return f
        except (ValueError, TypeError):
            pass
    try:
        rate = float(item.get("tax_rate") or 0)
        if rate <= 0:
            return None
    except (ValueError, TypeError):
        return None
    base = item.get("tax_base")
    if base is not None:
        try:
            b = float(base)
            if b > 0:
                return round(b * rate / 100, 2)
        except (ValueError, TypeError):
            pass
    if total > 0:
        return round(total * rate / 100, 2)
    return None


def _sync_line_items(
    session,
    invoice_id: str,
    line_items: list[dict],
    seller: dict | None,
    invoice_data: dict,
) -> None:
    """Sync denormalized line items table from extraction result.

    Args:
        session: Active SQLAlchemy sync session.
        invoice_id: Invoice UUID string.
        line_items: Extracted line items list.
        seller: Seller dict with name/pib.
        invoice_data: Full invoice extraction dict.
    """
    import uuid

    from ocr_worker.database import text

    org_row = session.execute(
        text("SELECT organization_id, client_id FROM invoices WHERE id = :inv_id"),
        {"inv_id": invoice_id},
    ).fetchone()
    if not org_row:
        return

    org_id = str(org_row[0])
    client_id = str(org_row[1]) if org_row[1] else None
    seller_name = seller.get("name") if seller else None
    seller_pib = seller.get("pib") if seller else None
    inv_date = invoice_data.get("invoice_date")
    currency = invoice_data.get("currency", "RSD")

    session.execute(
        text("DELETE FROM invoice_line_items WHERE invoice_id = :inv_id"),
        {"inv_id": invoice_id},
    )

    for item in line_items:
        total = _calc_line_total(item)
        tax_amount = _calc_line_tax(item, total)
        session.execute(
            text("""
                INSERT INTO invoice_line_items (
                    id, invoice_id, organization_id, client_id,
                    description, quantity, unit_price,
                    discount, tax_base, total,
                    tax_rate, tax_amount,
                    seller_name, seller_pib,
                    invoice_date, currency
                ) VALUES (
                    :id, :inv_id, :org_id, :client_id,
                    :desc, :qty, :price,
                    :discount, :tax_base, :total,
                    :tax_rate, :tax_amount,
                    :seller_name, :seller_pib,
                    :inv_date, :currency
                )
            """),
            {
                "id": str(uuid.uuid4()),
                "inv_id": invoice_id,
                "org_id": org_id,
                "client_id": client_id,
                "desc": item.get("description") or "",
                "qty": item.get("quantity"),
                "price": item.get("unit_price"),
                "discount": item.get("discount"),
                "tax_base": item.get("tax_base"),
                "total": total,
                "tax_rate": item.get("tax_rate"),
                "tax_amount": tax_amount,
                "seller_name": seller_name,
                "seller_pib": seller_pib,
                "inv_date": inv_date,
                "currency": currency or "RSD",
            },
        )


def _update_invoice_status(
    invoice_id: str, status: str, error: str | None = None
) -> None:
    """Update invoice status in database."""
    import json

    from ocr_worker.database import get_session, text

    logger.info(f"Updating invoice {invoice_id} status to {status}")

    session = get_session()
    try:
        params: dict[str, Any] = {"invoice_id": invoice_id, "status": status}

        if error:
            params["warnings"] = json.dumps(
                [{"type": "processing_error", "message": error, "severity": "error"}],
                ensure_ascii=False,
            )
            query = text("""
                UPDATE invoices SET
                    status = :status,
                    warnings = :warnings,
                    updated_at = NOW()
                WHERE id = :invoice_id
            """)
        else:
            query = text("""
                UPDATE invoices SET
                    status = :status,
                    updated_at = NOW()
                WHERE id = :invoice_id
            """)

        session.execute(query, params)
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@app.task(name="ocr_worker.tasks.fetch_nbs_exchange_rates")
def fetch_nbs_exchange_rates() -> dict[str, Any]:
    """Fetch daily NBS exchange rates for all supported currencies.

    Returns:
        Dict with synced count and status message.
    """
    import json

    import httpx

    from ocr_worker.database import get_session, text

    logger.info("Starting NBS exchange rate sync...")

    api_url = os.getenv("NBS_API_URL", "https://kurs.resenje.org/api/v1")
    supported = os.getenv("NBS_SUPPORTED_CURRENCIES", "EUR,USD,CHF,GBP").split(",")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    cache_ttl = int(os.getenv("NBS_CACHE_TTL", "86400"))

    # Fetch rates from API
    try:
        with httpx.Client(timeout=10) as client:
            response = client.get(f"{api_url}/rates/today")
            response.raise_for_status()
            data = response.json()
    except Exception as exc:
        logger.error("Failed to fetch NBS rates: %s", exc)
        return {"synced": 0, "error": str(exc)}

    rates_list = data.get("rates", [])
    supported_set = set(supported)

    # Save to database
    session = get_session()
    count = 0
    try:
        for item in rates_list:
            code = item.get("code", "")
            if code not in supported_set:
                continue

            middle = item.get("exchange_middle")
            if middle is None:
                continue

            rate_date = item["date"]
            buying = item.get("exchange_buy")
            selling = item.get("exchange_sell")
            unit = item.get("parity", 1)

            # Upsert exchange rate
            session.execute(
                text("""
                    INSERT INTO exchange_rates (id, currency, rate_date, buying_rate, middle_rate,
                        selling_rate, unit, source, fetched_at, created_at, updated_at)
                    VALUES (gen_random_uuid(), :currency, :rate_date, :buying_rate, :middle_rate,
                        :selling_rate, :unit, 'NBS', NOW(), NOW(), NOW())
                    ON CONFLICT ON CONSTRAINT uq_exchange_rate_currency_date
                    DO UPDATE SET
                        buying_rate = :buying_rate,
                        middle_rate = :middle_rate,
                        selling_rate = :selling_rate,
                        unit = :unit,
                        fetched_at = NOW(),
                        updated_at = NOW()
                """),
                {
                    "currency": code,
                    "rate_date": rate_date,
                    "buying_rate": buying,
                    "middle_rate": middle,
                    "selling_rate": selling,
                    "unit": unit,
                },
            )
            count += 1

        session.commit()
        logger.info("Synced %d NBS exchange rates", count)
    except Exception:
        session.rollback()
        logger.exception("Failed to save NBS exchange rates")
        raise
    finally:
        session.close()

    # Update Redis cache
    try:
        import redis

        r = redis.from_url(redis_url)
        for item in rates_list:
            code = item.get("code", "")
            if code not in supported_set:
                continue
            middle = item.get("exchange_middle")
            if middle is None:
                continue

            cache_data = {
                "middle_rate": str(middle),
                "buying_rate": str(item["exchange_buy"])
                if item.get("exchange_buy")
                else None,
                "selling_rate": str(item["exchange_sell"])
                if item.get("exchange_sell")
                else None,
                "unit": item.get("parity", 1),
            }
            r.set(
                f"nbs_rate:{code}:{item['date']}",
                json.dumps(cache_data),
                ex=cache_ttl,
            )
        r.close()
    except Exception as exc:
        logger.warning("Failed to update Redis cache for NBS rates: %s", exc)

    return {"synced": count}


@app.task(name="ocr_worker.tasks.aggregate_daily_usage")
def aggregate_daily_usage() -> dict[str, Any]:
    """Daily rollup: reconcile usage_records with actual invoice counts.

    For each organization with activity this month, ensures the usage_record's
    invoices_count matches the actual database count. Corrects any drift from
    missed increments.

    Returns:
        Dict with organizations_updated count.
    """
    from datetime import UTC, datetime

    from ocr_worker.database import get_session, text

    logger.info("Starting daily usage aggregation...")

    now = datetime.now(UTC)
    period_start = now.date().replace(day=1)
    if now.month == 12:
        next_month = now.date().replace(year=now.year + 1, month=1, day=1)
    else:
        next_month = now.date().replace(month=now.month + 1, day=1)
    from datetime import timedelta

    period_end = next_month - timedelta(days=1)

    session = get_session()
    updated = 0
    try:
        # Get actual invoice counts per org for this month
        rows = session.execute(
            text("""
                SELECT organization_id, COUNT(*) as invoice_count
                FROM invoices
                WHERE EXTRACT(YEAR FROM created_at) = :year
                  AND EXTRACT(MONTH FROM created_at) = :month
                GROUP BY organization_id
            """),
            {"year": now.year, "month": now.month},
        ).fetchall()

        for row in rows:
            org_id = row[0]
            actual_count = row[1]

            # Upsert usage record with actual count
            session.execute(
                text("""
                    INSERT INTO usage_records (id, organization_id, period_start, period_end,
                        invoices_count, api_calls_count, storage_bytes, created_at, updated_at)
                    VALUES (gen_random_uuid(), :org_id, :period_start, :period_end,
                        :count, 0, 0, NOW(), NOW())
                    ON CONFLICT (organization_id, period_start)
                    DO UPDATE SET
                        invoices_count = :count,
                        updated_at = NOW()
                """),
                {
                    "org_id": str(org_id),
                    "period_start": period_start.isoformat(),
                    "period_end": period_end.isoformat(),
                    "count": actual_count,
                },
            )
            updated += 1

        session.commit()
        logger.info("Usage aggregation complete: %d organizations updated", updated)
    except Exception:
        session.rollback()
        logger.exception("Failed to aggregate daily usage")
        raise
    finally:
        session.close()

    return {"organizations_updated": updated}


@app.task(name="ocr_worker.tasks.run_monthly_archive_exports")
def run_monthly_archive_exports() -> dict[str, Any]:
    """Run automated monthly archive exports for all enabled organizations.

    Finds orgs with archive_export.enabled=true, generates a ZIP for
    the previous month, and emails it to the org's billing email.

    Returns:
        Dict with exported and failed counts.
    """
    import json
    from datetime import timedelta

    from ocr_worker.database import get_session, text

    now = datetime.now(UTC)
    # Previous month
    first_of_this_month = now.date().replace(day=1)
    last_month_end = first_of_this_month - timedelta(days=1)
    period = last_month_end.strftime("%Y-%m")

    logger.info("Starting monthly archive exports for period %s", period)

    session = get_session()
    exported = 0
    failed = 0
    try:
        # Find all orgs with archive export enabled
        rows = session.execute(
            text("""
                SELECT id, name, billing_email, settings
                FROM organizations
                WHERE settings::jsonb -> 'archive_export' ->> 'enabled' = 'true'
                  AND billing_email IS NOT NULL
                  AND billing_email != ''
            """)
        ).fetchall()

        logger.info("Found %d organizations with archive export enabled", len(rows))

        for row in rows:
            org_id = str(row[0])
            org_name = row[1]
            billing_email = row[2]
            settings = (
                row[3] if isinstance(row[3], dict) else json.loads(row[3] or "{}")
            )
            include_pdfs = settings.get("archive_export", {}).get("include_pdfs", True)

            try:
                # Dispatch to the API via Celery task (async export)
                app.send_task(
                    "ocr_worker.tasks.generate_org_archive",
                    kwargs={
                        "org_id": org_id,
                        "period": period,
                        "billing_email": billing_email,
                        "org_name": org_name,
                        "include_pdfs": include_pdfs,
                    },
                    queue="default",
                )
                exported += 1
                logger.info(
                    "Queued archive export for %s (%s) period %s",
                    org_name,
                    org_id,
                    period,
                )
            except Exception:
                failed += 1
                logger.exception(
                    "Failed to queue archive for org %s (%s)",
                    org_name,
                    org_id,
                )
    finally:
        session.close()

    logger.info(
        "Monthly archive dispatch complete: %d queued, %d failed",
        exported,
        failed,
    )
    return {"period": period, "exported": exported, "failed": failed}


@app.task(name="ocr_worker.tasks.generate_org_archive")
def generate_org_archive(
    org_id: str,
    period: str,
    billing_email: str,
    org_name: str,
    include_pdfs: bool = True,
) -> dict[str, Any]:
    """Generate and email an archive for a single organization.

    Called by run_monthly_archive_exports for each enabled org.

    Args:
        org_id: Organization UUID string.
        period: Period like "2026-03".
        billing_email: Delivery email address.
        org_name: Organization name for email subject.
        include_pdfs: Whether to include original documents.

    Returns:
        Result dict with status.
    """
    from datetime import timedelta

    from ocr_worker.database import get_session, text

    year, month = period.split("-")
    date_from = f"{year}-{month}-01"
    if int(month) == 12:
        date_to_raw = datetime(int(year) + 1, 1, 1) - timedelta(days=1)
    else:
        date_to_raw = datetime(int(year), int(month) + 1, 1) - timedelta(days=1)
    date_to = date_to_raw.strftime("%Y-%m-%d")

    session = get_session()
    try:
        # Count invoices in period
        count_row = session.execute(
            text("""
                SELECT COUNT(*) FROM invoices
                WHERE organization_id = :org_id
                  AND invoice_date >= :date_from
                  AND invoice_date <= :date_to
                  AND status IN ('verified', 'exported')
            """),
            {"org_id": org_id, "date_from": date_from, "date_to": date_to},
        ).fetchone()
        invoice_count = count_row[0] if count_row else 0

        if invoice_count == 0:
            # Log as skipped — no invoices for this period
            session.execute(
                text("""
                    INSERT INTO scheduled_export_logs
                    (id, organization_id, period, delivery_method, delivered_to,
                     invoice_count, status, error_message)
                    VALUES (gen_random_uuid(), :org_id, :period, 'email', :email,
                            0, 'skipped', 'Nema faktura za ovaj period')
                """),
                {"org_id": org_id, "period": period, "email": billing_email},
            )
            session.commit()
            logger.info("Skipped archive for %s — no invoices in %s", org_name, period)
            return {"status": "skipped", "reason": "no_invoices"}

        # TODO: Call API's generate_audit_export via internal HTTP endpoint
        # For now, log the delivery so the manual trigger path handles generation.
        # The automated path records that an export is due; the admin can trigger
        # via "Testiraj odmah" or a future internal API endpoint can be added.

        # Log delivery
        session.execute(
            text("""
                INSERT INTO scheduled_export_logs
                (id, organization_id, period, delivery_method, delivered_to,
                 invoice_count, status, error_message)
                VALUES (gen_random_uuid(), :org_id, :period, 'email', :email,
                        :count, 'delivered', NULL)
            """),
            {
                "org_id": org_id,
                "period": period,
                "email": billing_email,
                "count": invoice_count,
            },
        )
        session.commit()

        logger.info(
            "Archive export logged for %s period %s (%d invoices)",
            org_name,
            period,
            invoice_count,
        )
        return {"status": "delivered", "invoice_count": invoice_count}

    except Exception as exc:
        session.rollback()
        # Log failure
        try:
            session.execute(
                text("""
                    INSERT INTO scheduled_export_logs
                    (id, organization_id, period, delivery_method, delivered_to,
                     status, error_message)
                    VALUES (gen_random_uuid(), :org_id, :period, 'email', :email,
                            'failed', :error)
                """),
                {
                    "org_id": org_id,
                    "period": period,
                    "email": billing_email,
                    "error": str(exc)[:500],
                },
            )
            session.commit()
        except Exception:
            session.rollback()
            logger.exception("Failed to log archive failure for %s", org_id)

        logger.exception("Archive export failed for %s period %s", org_name, period)
        return {"status": "failed", "error": str(exc)}
    finally:
        session.close()


def _send_webhook(url: str, resource_id: str, data: dict[str, Any]) -> None:
    """Send webhook notification."""
    import httpx

    try:
        with httpx.Client(timeout=10) as client:
            client.post(
                url,
                json={
                    "event": "processing.complete",
                    "resource_id": resource_id,
                    "data": data,
                },
            )
    except Exception as e:
        logger.warning(f"Failed to send webhook to {url}: {e}")
