"""SEF invoice sync service.

Orchestrates pulling invoices from SEF and storing them as SefInvoice records.
Uses Redis locking to prevent concurrent syncs for the same organization.
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sef_connection import SefConnection
from app.models.sef_invoice import SefInvoice
from app.services.sef.client import BaseSefClient, LiveSefClient, get_sef_client

logger = logging.getLogger(__name__)

SYNC_LOCK_TTL = 300  # 5 minutes


async def get_sef_client_for_org(
    db: AsyncSession, org_id: UUID
) -> tuple[BaseSefClient, SefConnection | None]:
    """Get the SEF client configured for an organization.

    Args:
        db: Database session.
        org_id: Organization UUID.

    Returns:
        Tuple of (client, connection). Connection may be None in demo mode.
    """
    from app.config import get_settings

    settings = get_settings()

    # Check for org-level SEF connection
    result = await db.execute(select(SefConnection).where(SefConnection.organization_id == org_id))
    connection = result.scalar_one_or_none()

    if settings.sef_demo_mode or not connection:
        return get_sef_client(), connection

    # Use live client with org's API key
    return LiveSefClient(
        api_key=connection.api_key_encrypted or "",
        base_url=settings.sef_api_base_url,
    ), connection


async def acquire_sync_lock(redis, org_id: UUID) -> bool:
    """Acquire a Redis lock to prevent concurrent syncs.

    Args:
        redis: Redis client instance.
        org_id: Organization UUID.

    Returns:
        True if lock acquired, False if already locked.
    """
    key = f"sef:sync:{org_id}:in_progress"
    return await redis.set(key, "1", ex=SYNC_LOCK_TTL, nx=True)


async def release_sync_lock(redis, org_id: UUID) -> None:
    """Release the sync lock.

    Args:
        redis: Redis client instance.
        org_id: Organization UUID.
    """
    key = f"sef:sync:{org_id}:in_progress"
    await redis.delete(key)


async def is_sync_in_progress(redis, org_id: UUID) -> bool:
    """Check if a sync is currently in progress.

    Args:
        redis: Redis client instance.
        org_id: Organization UUID.

    Returns:
        True if sync is in progress.
    """
    key = f"sef:sync:{org_id}:in_progress"
    return bool(await redis.exists(key))


async def sync_sef_invoices(db: AsyncSession, org_id: UUID, redis) -> int:
    """Pull new invoices from SEF and store as SefInvoice records.

    Deduplicates by sef_id. Creates records with status 'new'.
    Updates the SefConnection sync metadata.

    Args:
        db: Database session.
        org_id: Organization UUID.
        redis: Redis client for locking.

    Returns:
        Number of new invoices synced.

    Raises:
        RuntimeError: If sync lock cannot be acquired.
    """
    if not await acquire_sync_lock(redis, org_id):
        raise RuntimeError("Sync already in progress for this organization")

    try:
        client, connection = await get_sef_client_for_org(db, org_id)

        # Determine the since timestamp
        since = connection.last_sync_at if connection else None

        # Determine PIB
        pib = connection.pib if connection else "000000000"

        # Fetch invoices from SEF
        raw_invoices = await client.fetch_inbound_invoices(pib=pib, since=since)

        synced_count = 0
        for raw in raw_invoices:
            sef_id = raw.get("sef_id", "")
            if not sef_id:
                continue

            # Check if already exists
            existing = await db.execute(
                select(SefInvoice).where(
                    SefInvoice.organization_id == org_id,
                    SefInvoice.sef_id == sef_id,
                )
            )
            if existing.scalar_one_or_none():
                continue

            # Parse amount safely
            amount = None
            raw_amount = raw.get("amount") or raw.get("monetary_totals", {}).get("payable_amount")
            if raw_amount:
                try:
                    amount = Decimal(str(raw_amount))
                except (InvalidOperation, ValueError):
                    logger.warning("Invalid amount for SEF invoice %s: %s", sef_id, raw_amount)

            # Parse received_at
            received_str = raw.get("received_at", "")
            try:
                received_at = datetime.fromisoformat(received_str)
            except (ValueError, TypeError):
                received_at = datetime.now(UTC)

            # Parse invoice_date
            invoice_date = None
            inv_date_str = raw.get("invoice_date")
            if inv_date_str:
                try:
                    from datetime import date as date_type

                    invoice_date = date_type.fromisoformat(inv_date_str)
                except (ValueError, TypeError):
                    pass

            supplier = raw.get("supplier", {})

            sef_invoice = SefInvoice(
                organization_id=org_id,
                sef_id=sef_id,
                status="new",
                sef_status=raw.get("sef_status", "DELIVERED"),
                direction="INBOUND",
                invoice_number=raw.get("invoice_number"),
                supplier_name=supplier.get("name"),
                supplier_pib=supplier.get("pib"),
                amount=amount,
                currency=raw.get("currency", "RSD"),
                invoice_date=invoice_date,
                received_at=received_at,
                sef_response_json=raw,
            )
            db.add(sef_invoice)
            synced_count += 1

        # Update connection sync metadata
        if connection:
            connection.last_sync_at = datetime.now(UTC)
            connection.last_sync_status = "success"
            connection.last_sync_error = None
            connection.total_invoices_synced = (
                connection.total_invoices_synced or 0
            ) + synced_count

        await db.commit()
        logger.info("SEF sync for org %s: %d new invoices", org_id, synced_count)
        return synced_count

    except Exception as exc:
        await db.rollback()
        # Update connection with error
        if connection:
            connection.last_sync_at = datetime.now(UTC)
            connection.last_sync_status = "error"
            connection.last_sync_error = str(exc)
            await db.commit()
        logger.error("SEF sync failed for org %s: %s", org_id, exc)
        raise
    finally:
        await release_sync_lock(redis, org_id)


async def get_sync_status(db: AsyncSession, org_id: UUID, redis) -> dict:
    """Get the current SEF sync status for an organization.

    Args:
        db: Database session.
        org_id: Organization UUID.
        redis: Redis client for checking lock.

    Returns:
        Dict with last_sync_at, pending_count, is_syncing.
    """
    # Check connection for last sync time
    result = await db.execute(select(SefConnection).where(SefConnection.organization_id == org_id))
    connection = result.scalar_one_or_none()

    last_sync_at = None
    if connection and connection.last_sync_at:
        last_sync_at = connection.last_sync_at.isoformat()

    # Count pending (new) invoices
    count_result = await db.execute(
        select(func.count())
        .select_from(SefInvoice)
        .where(
            SefInvoice.organization_id == org_id,
            SefInvoice.status == "new",
        )
    )
    pending_count = count_result.scalar() or 0

    # Check if sync is in progress
    syncing = await is_sync_in_progress(redis, org_id)

    return {
        "last_sync_at": last_sync_at,
        "pending_count": pending_count,
        "is_syncing": syncing,
    }
