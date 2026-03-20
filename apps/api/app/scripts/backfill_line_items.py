"""Backfill invoice_line_items from existing invoices.

Run once after migration 0006 to populate the denormalized table
from the invoices.line_items JSON column.

Usage:
    cd apps/api && python -m app.scripts.backfill_line_items
"""

import asyncio
import sys

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models.invoice import Invoice
from app.services.line_item_sync import sync_line_items_orm


async def backfill() -> None:
    """Backfill all invoices with non-null line_items.

    Returns:
        None
    """
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with session_factory() as db:
        result = await db.execute(select(Invoice).where(Invoice.line_items.isnot(None)))
        invoices = list(result.scalars().all())
        print(f"Found {len(invoices)} invoices with line items to backfill")

        count = 0
        for invoice in invoices:
            if not invoice.line_items:
                continue
            await sync_line_items_orm(db, invoice)
            count += 1
            if count % 100 == 0:
                await db.commit()
                print(f"  Processed {count}/{len(invoices)}")

        await db.commit()
        print(f"Done. Backfilled {count} invoices.")

    await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(backfill())
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)
