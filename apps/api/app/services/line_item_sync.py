"""Line item sync service.

Populates the denormalized invoice_line_items table from the
invoices.line_items JSON column. Provides both a raw-SQL variant for
use from the Celery worker (psycopg2 connection) and an async ORM
variant for use from the FastAPI application.

The invoices.line_items JSON column remains the source of truth;
this table is a read-optimised copy rebuilt on every OCR completion
or user edit.
"""

from __future__ import annotations

import logging
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.invoice import Invoice

logger = logging.getLogger(__name__)


def sync_line_items_raw_sql(
    session,
    invoice_id: str,
    organization_id: str,
    line_items: list[dict],
    seller: dict | None,
    invoice_date: str | None,
    currency: str,
    client_id: str | None = None,
) -> None:
    """Rebuild invoice_line_items rows using a SQLAlchemy sync session.

    Deletes all existing rows for the given invoice then inserts one
    row per item in *line_items*. Called from the Celery worker after
    saving extraction results, within the same transaction.

    Args:
        session: Active SQLAlchemy sync Session (caller manages commit).
        invoice_id: UUID string of the invoice being synced.
        organization_id: UUID string of the owning organization.
        line_items: List of line-item dicts from the extraction result.
        seller: Seller dict with optional name/pib keys, or None.
        invoice_date: ISO-8601 date string (YYYY-MM-DD) or None.
        currency: ISO-4217 currency code, e.g. "RSD".

    Returns:
        None
    """
    from sqlalchemy import text

    seller_name: str | None = None
    seller_pib: str | None = None
    if seller:
        seller_name = seller.get("name")
        seller_pib = seller.get("pib")

    try:
        session.execute(
            text("DELETE FROM invoice_line_items WHERE invoice_id = :inv_id"),
            {"inv_id": invoice_id},
        )

        if not line_items:
            return

        for item in line_items:
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
                        :id, :invoice_id, :organization_id, :client_id,
                        :description, :quantity, :unit_price,
                        :discount, :tax_base, :total,
                        :tax_rate, :tax_amount,
                        :seller_name, :seller_pib,
                        :invoice_date, :currency
                    )
                """),
                {
                    "id": str(uuid.uuid4()),
                    "invoice_id": invoice_id,
                    "organization_id": organization_id,
                    "client_id": client_id,
                    "description": item.get("description") or "",
                    "quantity": item.get("quantity"),
                    "unit_price": item.get("unit_price"),
                    "discount": item.get("discount"),
                    "tax_base": item.get("tax_base"),
                    "total": item.get("total") or 0,
                    "tax_rate": item.get("tax_rate"),
                    "tax_amount": item.get("tax_amount"),
                    "seller_name": seller_name,
                    "seller_pib": seller_pib,
                    "invoice_date": invoice_date,
                    "currency": currency or "RSD",
                },
            )
    except Exception as exc:
        logger.warning(
            "sync_line_items_raw_sql failed for invoice %s: %s",
            invoice_id,
            exc,
        )


async def sync_line_items_orm(
    db: AsyncSession,
    invoice: Invoice,
) -> None:
    """Rebuild invoice_line_items rows for one invoice using the async ORM session.

    Deletes all existing rows for *invoice* then inserts fresh rows
    derived from *invoice.line_items* (JSON column).  Intended to be
    called from FastAPI route handlers after an invoice is updated.

    The caller is responsible for committing the session; this function
    does not commit so that it can participate in the caller's
    transaction.

    Args:
        db: Active async SQLAlchemy session.
        invoice: Invoice ORM instance whose line_items JSON should be
            synced.  The following attributes are read:
            id, organization_id, line_items, seller,
            invoice_date, currency.

    Returns:
        None
    """
    from sqlalchemy import delete

    from app.models.line_item import InvoiceLineItem

    try:
        # Remove stale rows
        await db.execute(delete(InvoiceLineItem).where(InvoiceLineItem.invoice_id == invoice.id))

        line_items: list[dict] = invoice.line_items or []
        if not line_items:
            return

        seller: dict | None = invoice.seller or {}
        seller_name: str | None = seller.get("name") if seller else None
        seller_pib: str | None = seller.get("pib") if seller else None

        invoice_date = invoice.invoice_date
        currency: str = invoice.currency or "RSD"

        client_id = getattr(invoice, "client_id", None)

        new_rows = []
        for item in line_items:
            new_rows.append(
                InvoiceLineItem(
                    invoice_id=invoice.id,
                    organization_id=invoice.organization_id,
                    client_id=client_id,
                    description=item.get("description") or "",
                    quantity=item.get("quantity"),
                    unit_price=item.get("unit_price"),
                    discount=item.get("discount"),
                    tax_base=item.get("tax_base"),
                    total=item.get("total") or 0,
                    tax_rate=item.get("tax_rate"),
                    tax_amount=item.get("tax_amount"),
                    seller_name=seller_name,
                    seller_pib=seller_pib,
                    invoice_date=invoice_date,
                    currency=currency,
                )
            )

        db.add_all(new_rows)
    except Exception as exc:
        logger.warning(
            "sync_line_items_orm failed for invoice %s: %s",
            invoice.id,
            exc,
        )
