"""SEF invoice processing service.

Converts a SEF invoice into a FakturaAI Invoice record by extracting
structured data from the cached SEF response JSON.
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice
from app.models.sef_invoice import SefInvoice

logger = logging.getLogger(__name__)


async def process_sef_invoice(db: AsyncSession, sef_invoice_id: UUID, org_id: UUID) -> SefInvoice:
    """Create a FakturaAI Invoice from a SEF invoice.

    Extracts structured data from the SEF response JSON, creates an
    Invoice record with status 'review', and links it to the SefInvoice.

    Args:
        db: Database session.
        sef_invoice_id: UUID of the SefInvoice to process.
        org_id: Organization UUID for multi-tenant scoping.

    Returns:
        Updated SefInvoice with status 'processed' and linked invoice_id.

    Raises:
        ValueError: If the SefInvoice is not found or not in 'new' status.
    """
    result = await db.execute(
        select(SefInvoice).where(
            SefInvoice.id == sef_invoice_id,
            SefInvoice.organization_id == org_id,
        )
    )
    sef_inv = result.scalar_one_or_none()

    if not sef_inv:
        raise ValueError(f"SEF invoice not found: {sef_invoice_id}")

    if sef_inv.status not in ("new", "pending"):
        raise ValueError(
            f"SEF invoice {sef_invoice_id} cannot be processed (status: {sef_inv.status})"
        )

    # Mark as pending while processing
    sef_inv.status = "pending"
    await db.flush()

    try:
        raw = sef_inv.sef_response_json or {}
        supplier = raw.get("supplier", {})
        monetary = raw.get("monetary_totals", {})
        raw_line_items = raw.get("line_items", [])

        # Parse amounts
        subtotal = _parse_decimal(monetary.get("tax_exclusive_amount"))
        tax_amount = _parse_decimal(monetary.get("tax_amount"))
        total_amount = _parse_decimal(monetary.get("payable_amount"))

        # Build seller/buyer dicts (matching Invoice model's JSON format)
        seller_dict = {
            "pib": supplier.get("pib"),
            "name": supplier.get("name"),
            "address": supplier.get("address"),
            "mb": supplier.get("mb"),
        }

        # Line items
        line_items = []
        for item in raw_line_items:
            line_items.append(
                {
                    "description": item.get("description", ""),
                    "quantity": item.get("quantity"),
                    "unit_price": item.get("unit_price"),
                    "total": item.get("total"),
                    "tax_rate": item.get("vat_rate"),
                    "tax_amount": item.get("vat_amount"),
                }
            )

        # Determine tax rate from first line item or default
        tax_rate = None
        if raw_line_items:
            tax_rate = _parse_decimal(raw_line_items[0].get("vat_rate"))

        # Create FakturaAI Invoice
        invoice = Invoice(
            organization_id=org_id,
            status="review",
            invoice_number=sef_inv.invoice_number,
            invoice_date=sef_inv.invoice_date,
            seller=seller_dict,
            buyer=None,  # Buyer is the current org — populated later if needed
            subtotal=subtotal,
            tax_rate=tax_rate,
            tax_amount=tax_amount,
            total_amount=total_amount,
            currency=sef_inv.currency,
            line_items=line_items if line_items else None,
            confidence_score=Decimal("100.00"),  # SEF data is authoritative
            ocr_engine="sef",
        )
        db.add(invoice)
        await db.flush()

        # Link SEF invoice to the created invoice
        sef_inv.invoice_id = invoice.id
        sef_inv.status = "processed"
        sef_inv.processed_at = datetime.now(UTC)
        sef_inv.processing_error = None

        await db.commit()
        await db.refresh(sef_inv)
        logger.info(
            "Processed SEF invoice %s → Invoice %s",
            sef_invoice_id,
            invoice.id,
        )
        return sef_inv

    except Exception as exc:
        await db.rollback()
        sef_inv.status = "new"  # Revert to allow retry
        sef_inv.processing_error = str(exc)
        await db.commit()
        logger.error("Failed to process SEF invoice %s: %s", sef_invoice_id, exc)
        raise


def _parse_decimal(value: str | int | float | None) -> Decimal | None:
    """Safely parse a value to Decimal.

    Args:
        value: String, number, or None.

    Returns:
        Decimal or None if parsing fails.
    """
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
