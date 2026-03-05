"""Celery tasks for invoice OCR processing."""

import asyncio
import logging
import os
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

    bucket = os.getenv("STORAGE_BUCKET", "fakturaai-documents")

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
        session.commit()
        logger.info(f"Saved extraction result for invoice {invoice_id}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


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
