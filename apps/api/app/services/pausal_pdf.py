"""PDF generation for outgoing paušal invoices using ReportLab.

Produces a legally-compliant plain A4 invoice in Serbian Latin script
containing the fields required by Serbian tax regulations for paušalci.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _fmt_money(value: Decimal | str, currency: str = "RSD") -> str:
    """Format a monetary amount as ``1.234,56 RSD`` (Serbian convention)."""
    d = Decimal(value) if not isinstance(value, Decimal) else value
    whole = f"{int(d):,}".replace(",", ".")
    frac = f"{d:.2f}".split(".")[-1]
    return f"{whole},{frac} {currency}"


def _addr_line(entity: dict) -> str:
    """Format an entity's address into a single display line."""
    bits = []
    if entity.get("address"):
        bits.append(entity["address"])
    city_bits = []
    if entity.get("postal_code"):
        city_bits.append(entity["postal_code"])
    if entity.get("city"):
        city_bits.append(entity["city"])
    if city_bits:
        bits.append(" ".join(city_bits))
    return ", ".join(bits) if bits else "—"


def _identifier_line(entity: dict) -> str:
    """Return the ``PIB: X  MB: Y`` line (or JMBG for natural persons)."""
    parts = []
    if entity.get("is_natural_person") and entity.get("jmbg"):
        parts.append(f"JMBG: {entity['jmbg']}")
    else:
        if entity.get("pib"):
            parts.append(f"PIB: {entity['pib']}")
        if entity.get("mb"):
            parts.append(f"MB: {entity['mb']}")
    return "   ".join(parts) if parts else "—"


def build_pausal_invoice_pdf(
    *,
    invoice_number: str,
    invoice_date: date,
    due_date: date | None,
    place_of_issue: str,
    delivery_date: date | None,
    delivery_place: str | None,
    seller: dict,
    customer: dict,
    items: list[dict],
    subtotal: Decimal,
    currency: str,
    notes: str | None,
) -> bytes:
    """Render a paušal invoice to an A4 PDF and return the bytes.

    Args:
        invoice_number: Sequential invoice number (e.g. ``2026-001``).
        invoice_date: Date of issue.
        due_date: Payment due date (optional).
        place_of_issue: City of issuance.
        delivery_date: Date of delivery / completion of service.
        delivery_place: Place of delivery / service completion.
        seller: Seller (paušalac) snapshot dict.
        customer: Buyer (customer) snapshot dict.
        items: List of line item dicts (description, quantity, unit, unit_price, total).
        subtotal: Total amount (paušalci do not charge PDV; subtotal == total).
        currency: Currency code (ISO 4217, 3 chars).
        notes: Optional free-text note.

    Returns:
        The generated PDF as bytes.
    """
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=f"Faktura {invoice_number}",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=styles["Heading1"], spaceAfter=4)
    normal = ParagraphStyle("body", parent=styles["BodyText"], fontSize=9, leading=12)
    small = ParagraphStyle("small", parent=styles["BodyText"], fontSize=8, leading=10)

    story: list = []

    # Header
    story.append(Paragraph(f"Faktura br. {invoice_number}", h1))
    story.append(Spacer(1, 4 * mm))

    # Seller / buyer side-by-side
    header_table = Table(
        [
            [
                Paragraph("<b>Izdavalac (prodavac)</b>", normal),
                Paragraph("<b>Primalac (kupac)</b>", normal),
            ],
            [
                Paragraph(seller.get("name", "—"), normal),
                Paragraph(customer.get("name", "—"), normal),
            ],
            [
                Paragraph(_addr_line(seller), normal),
                Paragraph(_addr_line(customer), normal),
            ],
            [
                Paragraph(_identifier_line(seller), normal),
                Paragraph(_identifier_line(customer), normal),
            ],
            [
                Paragraph(f"Šifra delatnosti: {seller.get('activity_code') or '—'}", normal),
                Paragraph("", normal),
            ],
        ],
        colWidths=[85 * mm, 85 * mm],
    )
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 6 * mm))

    # Dates & place
    meta_rows = [
        ["Datum izdavanja:", invoice_date.isoformat()],
        ["Mesto izdavanja:", place_of_issue],
    ]
    if delivery_date is not None:
        meta_rows.append(["Datum prometa:", delivery_date.isoformat()])
    if delivery_place:
        meta_rows.append(["Mesto prometa:", delivery_place])
    if due_date is not None:
        meta_rows.append(["Rok plaćanja:", due_date.isoformat()])

    meta_table = Table(meta_rows, colWidths=[40 * mm, 120 * mm])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ("TOPPADDING", (0, 0), (-1, -1), 1),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 6 * mm))

    # Items table
    item_rows: list[list] = [["#", "Opis", "Kol.", "JM", "Jed. cena", "Ukupno"]]
    for i, item in enumerate(items, start=1):
        item_rows.append(
            [
                str(i),
                item["description"],
                str(item["quantity"]),
                item.get("unit") or "—",
                _fmt_money(item["unit_price"], currency),
                _fmt_money(item["total"], currency),
            ]
        )
    item_rows.append(
        ["", "", "", "", Paragraph("<b>Ukupno</b>", normal), _fmt_money(subtotal, currency)]
    )

    items_table = Table(
        item_rows,
        colWidths=[8 * mm, 80 * mm, 15 * mm, 12 * mm, 27 * mm, 32 * mm],
        repeatRows=1,
    )
    items_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ede9fe")),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ("ALIGN", (0, 0), (-1, 0), "LEFT"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#7c3aed")),
                ("LINEABOVE", (0, -1), (-1, -1), 0.5, colors.HexColor("#7c3aed")),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(items_table)
    story.append(Spacer(1, 6 * mm))

    # Bank / payment info
    if seller.get("bank_account"):
        story.append(Paragraph(f"<b>Uplata na račun:</b> {seller['bank_account']}", normal))

    if notes:
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(f"<b>Napomena:</b> {notes}", normal))

    # Paušal legal disclaimer
    story.append(Spacer(1, 6 * mm))
    story.append(
        Paragraph(
            "Obveznik PDV-a: <b>Ne</b>. Izdavalac nije u sistemu PDV-a u skladu sa"
            " članom 33. Zakona o porezu na dodatu vrednost.",
            small,
        )
    )

    doc.build(story)
    return buf.getvalue()
