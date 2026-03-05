"""MiniMax XML export generator (miniMAXUvozKnjigovodstvo format).

Generates XML conforming to the MiniMax import schema for:
- Stranke (partners/customers) — deduplicated by PIB
- Temeljnice (journal entries) — from accounting intent konta suggestions
"""

import logging
import xml.etree.ElementTree as ET
from io import BytesIO

from app.models.invoice import Invoice

logger = logging.getLogger(__name__)

NAMESPACE = "http://moj.minimax.si/ip/doc/schemas/miniMAXUvozKnjigovodstvo"


def generate_minimax_xml(invoices: list[Invoice]) -> BytesIO:
    """Generate MiniMax-compatible XML for import.

    Creates XML with:
    - <Stranke> — unique business partners (sellers), keyed by PIB
    - <Temeljnice> — journal entries from accounting intent

    Args:
        invoices: List of Invoice instances with accounting_intent loaded.

    Returns:
        BytesIO buffer containing the XML file.
    """
    root = ET.Element("miniMAXUvozKnjigovodstvo", xmlns=NAMESPACE)

    # Build unique partners from seller data
    _build_stranke(root, invoices)

    # Build journal entries from accounting intents
    _build_temeljnice(root, invoices)

    buffer = BytesIO()
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")
    tree.write(buffer, encoding="utf-8", xml_declaration=True)
    buffer.seek(0)
    return buffer


def _build_stranke(root: ET.Element, invoices: list[Invoice]) -> None:
    """Build <Stranke> element with unique partners.

    Args:
        root: XML root element.
        invoices: Invoices to extract seller data from.
    """
    stranke_el = ET.SubElement(root, "Stranke")

    # Deduplicate sellers by PIB
    seen_pibs: set[str] = set()
    for inv in invoices:
        seller = inv.seller if isinstance(inv.seller, dict) else {}
        pib = seller.get("pib", "")
        if not pib or pib in seen_pibs:
            continue
        seen_pibs.add(pib)

        stranka = ET.SubElement(stranke_el, "Stranka")
        _add_text_element(stranka, "Sifra", pib[:30])
        _add_text_element(stranka, "Naziv", seller.get("name", "Nepoznat")[:250])
        _add_text_element(stranka, "DavcnaStevilka", pib[:12])

        address = seller.get("address", "")
        if address:
            _add_text_element(stranka, "Naslov", address[:250])

        city = seller.get("city", "")
        if city:
            _add_text_element(stranka, "Posta", city[:250])

        # Default to Serbia
        _add_text_element(stranka, "SifraDrzave", "RS")


def _build_temeljnice(root: ET.Element, invoices: list[Invoice]) -> None:
    """Build <Temeljnice> element with journal entries from konta.

    Args:
        root: XML root element.
        invoices: Invoices with accounting intent data.
    """
    temeljnice_el = ET.SubElement(root, "Temeljnice")

    for inv in invoices:
        intent = inv.accounting_intent
        if intent is None:
            continue

        konta = intent.suggested_konta or {}
        debit_entries = konta.get("debit", [])
        credit_entries = konta.get("credit", [])

        if not debit_entries and not credit_entries:
            continue

        temeljnica = ET.SubElement(temeljnice_el, "Temeljnica")

        # Header
        glava = ET.SubElement(temeljnica, "GlavaTemeljnice")
        _add_text_element(glava, "SifraVrsteTemeljnice", "PR")  # Primljene fakture
        if inv.invoice_date:
            _add_text_element(glava, "DatumTemeljnice", inv.invoice_date.isoformat())

        seller = inv.seller if isinstance(inv.seller, dict) else {}
        pib = seller.get("pib", "")
        if pib:
            _add_text_element(glava, "SifraStranke", pib[:30])

        if inv.invoice_number:
            _add_text_element(glava, "Opis", f"Faktura {inv.invoice_number}"[:250])

        # Journal entry lines
        vrstice = ET.SubElement(temeljnica, "VrsticeTemeljnice")
        line_num = 1

        for entry in debit_entries:
            vrstica = ET.SubElement(vrstice, "VrsticaTemeljnice")
            _add_text_element(vrstica, "SifraKonta", str(entry.get("konto", ""))[:10])
            _add_text_element(vrstica, "StevilkaVrstice", str(line_num))

            amount = entry.get("amount")
            if amount is not None:
                _add_text_element(vrstica, "Znesek", str(amount))
                _add_text_element(vrstica, "ZnesekBrem686F", str(amount))  # Debit

            desc = entry.get("name", "")
            if desc:
                _add_text_element(vrstica, "Opis", desc[:250])

            line_num += 1

        for entry in credit_entries:
            vrstica = ET.SubElement(vrstice, "VrsticaTemeljnice")
            _add_text_element(vrstica, "SifraKonta", str(entry.get("konto", ""))[:10])
            _add_text_element(vrstica, "StevilkaVrstice", str(line_num))

            amount = entry.get("amount")
            if amount is not None:
                _add_text_element(vrstica, "Znesek", str(amount))
                _add_text_element(vrstica, "ZnesekDobro", str(amount))  # Credit

            desc = entry.get("name", "")
            if desc:
                _add_text_element(vrstica, "Opis", desc[:250])

            line_num += 1

        # VAT entries from breakdown
        vat_breakdown = intent.vat_breakdown or {}
        if vat_breakdown:
            _build_ddv_entries(temeljnica, vat_breakdown)


def _build_ddv_entries(temeljnica: ET.Element, vat_breakdown: dict) -> None:
    """Build DDV (VAT) entries from breakdown.

    Args:
        temeljnica: Parent journal entry element.
        vat_breakdown: Dict of rate -> {base, tax} from accounting intent.
    """
    for rate_str, amounts in vat_breakdown.items():
        if not isinstance(amounts, dict):
            continue

        ddv = ET.SubElement(temeljnica, "DDV")

        # Map rate to MiniMax VAT level
        try:
            rate = float(rate_str)
        except (ValueError, TypeError):
            continue

        if rate == 20:
            _add_text_element(ddv, "Stopnja", "S")  # Standard
        elif rate == 10:
            _add_text_element(ddv, "Stopnja", "Z")  # Znizana (reduced)
        elif rate == 0:
            _add_text_element(ddv, "Stopnja", "N")  # Neobdavceno (exempt)
        else:
            _add_text_element(ddv, "Stopnja", "S")

        base = amounts.get("base")
        if base is not None:
            _add_text_element(ddv, "Osnova", str(base))

        tax = amounts.get("tax")
        if tax is not None:
            _add_text_element(ddv, "Davek", str(tax))


def _add_text_element(parent: ET.Element, tag: str, text: str) -> ET.Element:
    """Add a child element with text content.

    Args:
        parent: Parent element.
        tag: Element tag name.
        text: Text content.

    Returns:
        The created element.
    """
    el = ET.SubElement(parent, tag)
    el.text = text
    return el
