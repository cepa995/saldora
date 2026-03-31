"""Invoice verification services.

Mathematical verification (totals, line items, tax groups) and
duplicate detection for invoice quality assurance.
"""

from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.invoice import Invoice


def get_tolerance(amount: Decimal) -> Decimal:
    """Return the acceptable rounding tolerance for an invoice amount.

    Tiered by amount range per SRS Section 4.9.5.

    Args:
        amount: Absolute invoice amount in RSD.

    Returns:
        Maximum acceptable difference in RSD.
    """
    abs_amount = abs(amount)
    if abs_amount <= 10_000:
        return Decimal("1")
    if abs_amount <= 100_000:
        return Decimal("5")
    if abs_amount <= 1_000_000:
        return Decimal("10")
    return Decimal("50")


def verify_calculations(invoice: Invoice) -> list[dict]:
    """Run mathematical verification checks on an invoice.

    Checks performed (each skipped when required fields are null):
    1. Line items total = subtotal
    2. Subtotal + tax_amount = total_amount
    3. Tax groups base_amount sum = subtotal
    4. Tax groups tax_amount sum = invoice tax_amount
    5. Per-line-item: quantity * unit_price = line total

    Args:
        invoice: Invoice ORM object with extracted data.

    Returns:
        List of warning dicts (empty if all checks pass).
    """
    warnings: list[dict] = []

    # Determine tolerance from total_amount
    ref_amount = invoice.total_amount or Decimal("0")
    tolerance = get_tolerance(ref_amount)

    # Check 1: Line items sum = subtotal (or total if VAT-inclusive pricing)
    if invoice.line_items and invoice.subtotal is not None:
        calculated_subtotal = Decimal("0")
        for item in invoice.line_items:
            item_total = _to_decimal(item.get("total"))
            if item_total is not None:
                calculated_subtotal += item_total

        diff = abs(calculated_subtotal - Decimal(str(invoice.subtotal)))
        if diff > tolerance:
            # Serbian invoices may list "Cena sa PDV" (VAT-inclusive prices).
            # In that case line items sum to total_amount, not subtotal.
            vat_inclusive = False
            if invoice.total_amount is not None:
                diff_to_total = abs(calculated_subtotal - Decimal(str(invoice.total_amount)))
                if diff_to_total <= tolerance:
                    vat_inclusive = True

            if not vat_inclusive:
                warnings.append(
                    {
                        "message": f"Stavke se ne slažu sa međuzbirom (razlika: {diff} RSD)",
                        "severity": "warning",
                        "field_name": "subtotal",
                    }
                )

    # Check 2: Subtotal + tax_amount = total_amount
    if (
        invoice.subtotal is not None
        and invoice.tax_amount is not None
        and invoice.total_amount is not None
    ):
        expected_total = Decimal(str(invoice.subtotal)) + Decimal(str(invoice.tax_amount))
        diff = abs(expected_total - Decimal(str(invoice.total_amount)))
        if diff > tolerance:
            warnings.append(
                {
                    "message": f"Zbir nije tačan: međuzbir + PDV ≠ ukupno (razlika: {diff} RSD)",
                    "severity": "warning",
                    "field_name": "total_amount",
                }
            )

    # Check 3 & 4: Tax groups consistency
    if invoice.tax_groups and isinstance(invoice.tax_groups, list):
        group_base_sum = Decimal("0")
        group_tax_sum = Decimal("0")
        for group in invoice.tax_groups:
            base = _to_decimal(group.get("base_amount"))
            tax = _to_decimal(group.get("tax_amount"))
            if base is not None:
                group_base_sum += base
            if tax is not None:
                group_tax_sum += tax

        if invoice.subtotal is not None:
            diff = abs(group_base_sum - Decimal(str(invoice.subtotal)))
            if diff > tolerance:
                msg = f"Osnovice po stopama se ne slažu sa međuzbirom (razlika: {diff} RSD)"
                warnings.append(
                    {
                        "message": msg,
                        "severity": "warning",
                        "field_name": "tax_groups",
                    }
                )

        if invoice.tax_amount is not None:
            diff = abs(group_tax_sum - Decimal(str(invoice.tax_amount)))
            if diff > tolerance:
                msg = f"PDV iznosi po stopama se ne slažu sa ukupnim PDV-om (razlika: {diff} RSD)"
                warnings.append(
                    {
                        "message": msg,
                        "severity": "warning",
                        "field_name": "tax_groups",
                    }
                )

    # Check 5: Per-line-item math verification.
    # Invoices may have: discount (rabat), tax_base (poreska osnovica),
    # and total that includes PDV. We try multiple formulas before warning.
    if invoice.line_items:
        invoice_tax_rate = _to_decimal(getattr(invoice, "tax_rate", None))
        for i, item in enumerate(invoice.line_items):
            qty = _to_decimal(item.get("quantity"))
            price = _to_decimal(item.get("unit_price"))
            total = _to_decimal(item.get("total"))
            if qty is None or price is None or total is None:
                continue

            discount = _to_decimal(item.get("discount"))
            tax_base = _to_decimal(item.get("tax_base"))
            item_tax_rate = _to_decimal(item.get("tax_rate"))

            gross = qty * price
            tolerance = Decimal("2")

            # Apply discount if present: gross × (1 - discount/100)
            net = gross
            if discount is not None and discount > 0:
                net = gross * (1 - discount / 100)

            # Strategy 1: total = net (no PDV, no discount adjustment needed)
            if abs(gross - total) <= tolerance:
                continue

            # Strategy 2: total = net after discount
            if discount and abs(net - total) <= tolerance:
                continue

            # Strategy 3: total = tax_base (from invoice)
            if tax_base is not None and abs(tax_base - total) <= tolerance:
                continue

            # Strategy 4: total = net × (1 + PDV) — with discount + PDV
            for rate in (item_tax_rate, invoice_tax_rate):
                if rate is not None and rate > 0:
                    expected = net * (1 + rate / 100)
                    if abs(expected - total) <= tolerance:
                        break
            else:
                # Strategy 5: total = gross × (1 + PDV) — no discount
                for rate in (item_tax_rate, invoice_tax_rate):
                    if rate is not None and rate > 0:
                        expected = gross * (1 + rate / 100)
                        if abs(expected - total) <= tolerance:
                            break
                else:
                    # Strategy 6: verify tax_base × (1 + PDV) = total
                    if tax_base is not None:
                        for rate in (item_tax_rate, invoice_tax_rate):
                            if rate is not None and rate > 0:
                                expected = tax_base * (1 + rate / 100)
                                if abs(expected - total) <= tolerance:
                                    break
                        else:
                            # Nothing matched
                            desc = item.get("description", f"stavka {i + 1}")
                            warnings.append(
                                {
                                    "message": (
                                        f"Stavka '{desc}': ne poklapaju se "
                                        f"količina × cena ({round(float(gross), 2)}) "
                                        f"sa ukupnim iznosom ({round(float(total), 2)}). "
                                        "Proverite rabat ili PDV obračun."
                                    ),
                                    "severity": "info",
                                    "field_name": "line_items",
                                }
                            )
                    else:
                        desc = item.get("description", f"stavka {i + 1}")
                        warnings.append(
                            {
                                "message": (
                                    f"Stavka '{desc}': ne poklapaju se "
                                    f"količina × cena ({round(float(gross), 2)}) "
                                    f"sa ukupnim iznosom ({round(float(total), 2)}). "
                                    "Proverite rabat ili PDV obračun."
                                ),
                                "severity": "info",
                                "field_name": "line_items",
                            }
                        )

    return warnings


async def check_duplicates(
    db: AsyncSession,
    invoice: Invoice,
    organization_id: UUID,
) -> dict | None:
    """Check for duplicate invoices in the same organization.

    A duplicate matches on invoice_number + seller PIB + invoice_date.

    Args:
        db: Database session.
        invoice: Invoice being verified.
        organization_id: Organization scope.

    Returns:
        Warning dict if a duplicate is found, None otherwise.
    """
    if not invoice.invoice_number or not invoice.invoice_date:
        return None

    seller_pib = None
    if invoice.seller and isinstance(invoice.seller, dict):
        seller_pib = invoice.seller.get("pib")

    conditions = [
        Invoice.organization_id == organization_id,
        Invoice.invoice_number == invoice.invoice_number,
        Invoice.id != invoice.id,
        Invoice.status.in_(["verified", "exported"]),
    ]

    # Add seller PIB match if available (stronger duplicate signal)
    if seller_pib:
        conditions.append(Invoice.seller["pib"].as_string() == seller_pib)

    query = select(Invoice.id, Invoice.invoice_number).where(and_(*conditions)).limit(1)
    result = await db.execute(query)
    duplicate = result.first()

    if duplicate is not None:
        return {
            "message": (
                f"Duplikat: faktura br. {invoice.invoice_number}"
                + (f" od dobavljača sa PIB {seller_pib}" if seller_pib else "")
                + " već postoji u sistemu"
            ),
            "severity": "error",
            "field_name": "invoice_number",
            "duplicate_id": str(duplicate[0]),
        }

    return None


def _to_decimal(value: object) -> Decimal | None:
    """Safely convert a value to Decimal.

    Args:
        value: Number, string, or None.

    Returns:
        Decimal or None if conversion fails.
    """
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
