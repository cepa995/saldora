"""Generate sample restaurant supplier invoices for testing.

Creates realistic Serbian wholesale invoices with food/drink line items.
Proper column spacing to avoid text overlap. Multi-page support for large invoices.
Usage: python scripts/generate_test_invoices.py
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "test-invoices")

# Column definitions: (x_start_mm, width_mm, alignment, header_label)
COLUMNS = [
    (10, 8, "left", "R.br"),
    (19, 12, "left", "Sifra"),
    (32, 48, "left", "Naziv artikla"),
    (81, 10, "left", "J.M."),
    (92, 18, "right", "Kolicina"),
    (111, 22, "right", "Cena"),
    (134, 22, "right", "Rabat %"),
    (157, 28, "right", "Iznos"),
]

ROW_HEIGHT = 4.0  # mm per row
MARGIN_TOP = 25  # mm
MARGIN_BOTTOM = 25  # mm
TABLE_FONT_SIZE = 7


def _draw_cell(c, col_idx, y, text):
    """Draw text in a table cell respecting column alignment."""
    x_start, width, align, _ = COLUMNS[col_idx]
    if align == "right":
        c.drawRightString((x_start + width) * mm, y, str(text))
    else:
        # Truncate if too wide for the column
        max_chars = int(width / 1.8)  # rough estimate at font size 7
        t = str(text)
        if len(t) > max_chars:
            t = t[: max_chars - 1] + "."
        c.drawString(x_start * mm, y, t)


def _draw_table_header(c, y):
    """Draw the table header row and underline."""
    c.setFont("Helvetica-Bold", TABLE_FONT_SIZE)
    for i, (x, w, align, label) in enumerate(COLUMNS):
        _draw_cell(c, i, y, label)
    c.line(COLUMNS[0][0] * mm, y - 1.5 * mm, 188 * mm, y - 1.5 * mm)
    return y - ROW_HEIGHT * mm - 2 * mm


def draw_invoice(filename: str, data: dict):
    """Draw a single invoice PDF with multi-page support."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)
    c = canvas.Canvas(filepath, pagesize=A4)
    _, h = A4

    def _draw_header():
        """Draw invoice header, returns y position for table start."""
        c.setFont("Helvetica-Bold", 14)
        c.drawString(10 * mm, h - MARGIN_TOP * mm, "RACUN - OTPREMNICA")

        c.setFont("Helvetica", 9)
        c.drawString(10 * mm, h - (MARGIN_TOP + 8) * mm, f"Broj: {data['invoice_number']}")
        c.drawString(10 * mm, h - (MARGIN_TOP + 13) * mm, f"Datum: {data['date']}")
        c.drawString(10 * mm, h - (MARGIN_TOP + 18) * mm, f"Datum valute: {data['due_date']}")

        # Seller
        c.setFont("Helvetica-Bold", 9)
        c.drawString(10 * mm, h - (MARGIN_TOP + 28) * mm, "PRODAVAC:")
        c.setFont("Helvetica", 8)
        sy = h - (MARGIN_TOP + 33) * mm
        for line in data["seller"]:
            c.drawString(10 * mm, sy, line)
            sy -= 4 * mm

        # Buyer
        c.setFont("Helvetica-Bold", 9)
        c.drawString(110 * mm, h - (MARGIN_TOP + 28) * mm, "KUPAC:")
        c.setFont("Helvetica", 8)
        by = h - (MARGIN_TOP + 33) * mm
        for line in data["buyer"]:
            c.drawString(110 * mm, by, line)
            by -= 4 * mm

        table_start = h - (MARGIN_TOP + 33 + max(len(data["seller"]), len(data["buyer"])) * 4 + 8) * mm
        return _draw_table_header(c, table_start)

    y = _draw_header()
    page_bottom = MARGIN_BOTTOM * mm
    subtotal = 0.0
    discount_col = any(item.get("discount") for item in data["items"])

    c.setFont("Helvetica", TABLE_FONT_SIZE)

    for idx, item in enumerate(data["items"], 1):
        qty = item["qty"]
        price = item["price"]
        discount = item.get("discount", 0) or 0
        line_total = round(qty * price * (1 - discount / 100), 2)
        subtotal += line_total

        # Check if we need a new page
        if y < page_bottom + 20 * mm:
            c.showPage()
            c.setFont("Helvetica", 8)
            c.drawString(10 * mm, h - 15 * mm, f"{data['invoice_number']} — str. (nastavak)")
            y = h - 22 * mm
            y = _draw_table_header(c, y)
            c.setFont("Helvetica", TABLE_FONT_SIZE)

        _draw_cell(c, 0, y, str(idx))
        _draw_cell(c, 1, y, item.get("code", ""))
        _draw_cell(c, 2, y, item["name"])
        _draw_cell(c, 3, y, item["unit"])
        _draw_cell(c, 4, y, f"{qty:,.2f}".replace(",", "."))
        _draw_cell(c, 5, y, f"{price:,.2f}".replace(",", "."))
        if discount_col:
            _draw_cell(c, 6, y, f"{discount:.1f}" if discount else "")
        _draw_cell(c, 7, y, f"{line_total:,.2f}".replace(",", "."))
        y -= ROW_HEIGHT * mm

    # Totals
    y -= 3 * mm
    c.line(10 * mm, y + 2 * mm, 188 * mm, y + 2 * mm)

    tax_rate = data.get("tax_rate", 20)
    tax_amount = round(subtotal * tax_rate / 100, 2)
    total_amount = round(subtotal + tax_amount, 2)

    c.setFont("Helvetica", 9)
    c.drawString(130 * mm, y, "Osnovica:")
    c.drawRightString(186 * mm, y, f"{subtotal:,.2f} RSD".replace(",", "."))
    y -= 5 * mm
    c.drawString(130 * mm, y, f"PDV ({tax_rate}%):")
    c.drawRightString(186 * mm, y, f"{tax_amount:,.2f} RSD".replace(",", "."))
    y -= 5 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(130 * mm, y, "UKUPNO:")
    c.drawRightString(186 * mm, y, f"{total_amount:,.2f} RSD".replace(",", "."))

    c.save()
    print(f"  Created: {filepath} ({len(data['items'])} stavki)")


# ── Seller/buyer data ────────────────────────────────────────────────────────

BUYER = [
    "Restoran Kod Marka d.o.o.",
    "Knez Mihailova 15",
    "11000 Beograd",
    "PIB: 112345678",
    "MB: 21234567",
]

METRO = [
    "METRO Cash & Carry d.o.o.",
    "Autoput za Zagreb bb, 11070 N. Beograd",
    "PIB: 100002857",
    "MB: 17335014",
]

AROMA = [
    "Aroma d.o.o.",
    "Batajnicki drum 15, 11080 Zemun",
    "PIB: 101234567",
    "MB: 20123456",
]

DRINK_SHOP = [
    "Drink Shop d.o.o.",
    "Vojvodjanskih brigada 22, 21000 Novi Sad",
    "PIB: 103456789",
    "MB: 22345678",
]

MESO_PROMET = [
    "Meso Promet d.o.o.",
    "Industrijska zona bb, 11210 Batajnica",
    "PIB: 104567890",
    "MB: 23456789",
]

MLEKARA = [
    "Mlekara Subotica a.d.",
    "Tolminska 10, 24000 Subotica",
    "PIB: 100345678",
    "MB: 08042508",
]

PEKARNICA = [
    "Pekara Don Don d.o.o.",
    "Autoput 20A, 11070 N. Beograd",
    "PIB: 105678901",
    "MB: 24567890",
]


def main():
    print("Generating 10 test restaurant invoices...\n")

    # ── Invoice 1: Metro weekly order (23 items) ─────────────────────────────
    draw_invoice("01_metro_nedeljni.pdf", {
        "invoice_number": "MCS-2026/03-00142",
        "date": "10.03.2026",
        "due_date": "10.04.2026",
        "seller": METRO, "buyer": BUYER, "tax_rate": 20,
        "items": [
            {"code": "10234", "name": "Coca Cola 0.5l", "unit": "kom", "qty": 48, "price": 85.00},
            {"code": "10235", "name": "Coca Cola 1.5l", "unit": "kom", "qty": 24, "price": 135.00},
            {"code": "10240", "name": "Fanta 0.5l", "unit": "kom", "qty": 24, "price": 85.00},
            {"code": "10250", "name": "Knjaz Milos 0.5l", "unit": "kom", "qty": 48, "price": 55.00},
            {"code": "10260", "name": "Rosa 0.5l", "unit": "kom", "qty": 48, "price": 45.00},
            {"code": "20100", "name": "Pilece belo meso", "unit": "kg", "qty": 15, "price": 620.00},
            {"code": "20105", "name": "Pileci batak", "unit": "kg", "qty": 10, "price": 450.00},
            {"code": "20200", "name": "Svinjski vrat", "unit": "kg", "qty": 8, "price": 780.00},
            {"code": "20300", "name": "Juneci but", "unit": "kg", "qty": 5, "price": 1350.00},
            {"code": "30100", "name": "Paradajz", "unit": "kg", "qty": 10, "price": 180.00},
            {"code": "30110", "name": "Krastavac", "unit": "kg", "qty": 8, "price": 150.00},
            {"code": "30120", "name": "Paprika babura", "unit": "kg", "qty": 6, "price": 220.00},
            {"code": "30130", "name": "Crni luk", "unit": "kg", "qty": 5, "price": 90.00},
            {"code": "30140", "name": "Beli luk", "unit": "kg", "qty": 2, "price": 450.00},
            {"code": "40100", "name": "Brasno T-400 25kg", "unit": "kom", "qty": 2, "price": 2100.00},
            {"code": "40110", "name": "Secer 1kg", "unit": "kom", "qty": 10, "price": 120.00},
            {"code": "40120", "name": "So morska 1kg", "unit": "kom", "qty": 5, "price": 85.00},
            {"code": "40130", "name": "Ulje suncokret. 1l", "unit": "kom", "qty": 20, "price": 210.00},
            {"code": "40140", "name": "Maslinovo ulje 1l", "unit": "kom", "qty": 5, "price": 1250.00},
            {"code": "50100", "name": "Lav pivo 0.5l", "unit": "kom", "qty": 120, "price": 75.00},
            {"code": "50110", "name": "Jelen pivo 0.5l", "unit": "kom", "qty": 120, "price": 80.00},
            {"code": "50200", "name": "Vranac 0.75l", "unit": "fla", "qty": 24, "price": 450.00},
            {"code": "50210", "name": "Sauvignon Blanc 0.75l", "unit": "fla", "qty": 12, "price": 650.00},
        ],
    })

    # ── Invoice 2: Aroma voce/povrce (14 items) ─────────────────────────────
    draw_invoice("02_aroma_voce_povrce.pdf", {
        "invoice_number": "AR-0326/0087",
        "date": "12.03.2026",
        "due_date": "12.04.2026",
        "seller": AROMA, "buyer": BUYER, "tax_rate": 20,
        "items": [
            {"code": "V001", "name": "Paradajz", "unit": "kg", "qty": 15, "price": 170.00},
            {"code": "V002", "name": "Krastavac", "unit": "kg", "qty": 10, "price": 140.00},
            {"code": "V003", "name": "Paprika babura", "unit": "kg", "qty": 8, "price": 210.00},
            {"code": "V004", "name": "Tikvice", "unit": "kg", "qty": 5, "price": 190.00},
            {"code": "V005", "name": "Brokoli", "unit": "kg", "qty": 4, "price": 350.00},
            {"code": "V006", "name": "Spanac", "unit": "kg", "qty": 3, "price": 280.00},
            {"code": "V007", "name": "Sampinjon", "unit": "kg", "qty": 5, "price": 420.00},
            {"code": "F001", "name": "Limun", "unit": "kg", "qty": 5, "price": 250.00},
            {"code": "F002", "name": "Narandza", "unit": "kg", "qty": 8, "price": 180.00},
            {"code": "F003", "name": "Jagode", "unit": "kg", "qty": 3, "price": 650.00},
            {"code": "F004", "name": "Banana", "unit": "kg", "qty": 5, "price": 160.00},
            {"code": "Z001", "name": "Persun", "unit": "veza", "qty": 10, "price": 40.00},
            {"code": "Z002", "name": "Mirodzija", "unit": "veza", "qty": 5, "price": 50.00},
            {"code": "Z003", "name": "Bosiljak", "unit": "veza", "qty": 5, "price": 60.00},
        ],
    })

    # ── Invoice 3: Drink Shop alkohol + bezalkohol (10 items) ────────────────
    draw_invoice("03_drink_shop_pica.pdf", {
        "invoice_number": "BD-2026-0334",
        "date": "13.03.2026",
        "due_date": "28.03.2026",
        "seller": DRINK_SHOP, "buyer": BUYER, "tax_rate": 20,
        "items": [
            {"code": "JW01", "name": "Jack Daniels 0.7l", "unit": "kom", "qty": 6, "price": 4200.00},
            {"code": "AB01", "name": "Absolut Vodka 0.7l", "unit": "kom", "qty": 6, "price": 2800.00},
            {"code": "BF01", "name": "Beefeater Gin 0.7l", "unit": "kom", "qty": 4, "price": 2600.00},
            {"code": "HV01", "name": "Havana Club 0.7l", "unit": "kom", "qty": 4, "price": 3100.00},
            {"code": "CC01", "name": "Coca Cola 0.25l", "unit": "kom", "qty": 96, "price": 65.00},
            {"code": "TN01", "name": "Schweppes Tonic 0.25l", "unit": "kom", "qty": 48, "price": 75.00},
            {"code": "RB01", "name": "Red Bull 0.25l", "unit": "kom", "qty": 48, "price": 180.00},
            {"code": "EP01", "name": "Lavazza espresso 1kg", "unit": "kg", "qty": 5, "price": 2400.00},
            {"code": "ML01", "name": "Mleko za kafu 1l", "unit": "kom", "qty": 20, "price": 140.00},
            {"code": "SK01", "name": "Secer kesica 5g x1000", "unit": "pak", "qty": 2, "price": 1800.00},
        ],
    })

    # ── Invoice 4: Metro 2nd delivery — same items, different prices (9 items)
    draw_invoice("04_metro_dopuna.pdf", {
        "invoice_number": "MCS-2026/03-00198",
        "date": "17.03.2026",
        "due_date": "17.04.2026",
        "seller": METRO, "buyer": BUYER, "tax_rate": 20,
        "items": [
            {"code": "10234", "name": "Coca Cola 0.5l", "unit": "kom", "qty": 48, "price": 87.00},
            {"code": "10250", "name": "Knjaz Milos 0.5l", "unit": "kom", "qty": 48, "price": 55.00},
            {"code": "20100", "name": "Pilece belo meso", "unit": "kg", "qty": 20, "price": 630.00},
            {"code": "20200", "name": "Svinjski vrat", "unit": "kg", "qty": 10, "price": 790.00},
            {"code": "30100", "name": "Paradajz", "unit": "kg", "qty": 12, "price": 185.00},
            {"code": "30110", "name": "Krastavac", "unit": "kg", "qty": 8, "price": 155.00},
            {"code": "50100", "name": "Lav pivo 0.5l", "unit": "kom", "qty": 120, "price": 75.00},
            {"code": "50110", "name": "Jelen pivo 0.5l", "unit": "kom", "qty": 120, "price": 80.00},
            {"code": "40130", "name": "Ulje suncokret. 1l", "unit": "kom", "qty": 10, "price": 215.00},
        ],
    })

    # ── Invoice 5: Meso Promet — large meat order with discount (20 items) ───
    draw_invoice("05_meso_promet_veliki.pdf", {
        "invoice_number": "MP-2026/1247",
        "date": "14.03.2026",
        "due_date": "29.03.2026",
        "seller": MESO_PROMET, "buyer": BUYER, "tax_rate": 20,
        "items": [
            {"code": "M001", "name": "Pilece belo meso", "unit": "kg", "qty": 25, "price": 610.00, "discount": 5},
            {"code": "M002", "name": "Pileci batak", "unit": "kg", "qty": 15, "price": 440.00, "discount": 5},
            {"code": "M003", "name": "Pileca krila", "unit": "kg", "qty": 10, "price": 320.00, "discount": 5},
            {"code": "M004", "name": "Svinjski vrat", "unit": "kg", "qty": 15, "price": 770.00},
            {"code": "M005", "name": "Svinjska plecka", "unit": "kg", "qty": 10, "price": 650.00},
            {"code": "M006", "name": "Svinjski kotlet", "unit": "kg", "qty": 8, "price": 720.00},
            {"code": "M007", "name": "Juneci but", "unit": "kg", "qty": 10, "price": 1320.00},
            {"code": "M008", "name": "Junece rebra", "unit": "kg", "qty": 8, "price": 980.00},
            {"code": "M009", "name": "Junetina mlev.", "unit": "kg", "qty": 10, "price": 850.00},
            {"code": "M010", "name": "Teletina but", "unit": "kg", "qty": 5, "price": 1550.00},
            {"code": "M011", "name": "Jagnjece meso", "unit": "kg", "qty": 5, "price": 1800.00},
            {"code": "M012", "name": "Cevapi 1kg", "unit": "kg", "qty": 20, "price": 720.00},
            {"code": "M013", "name": "Pljeskavica 150g", "unit": "kom", "qty": 100, "price": 120.00},
            {"code": "M014", "name": "Kobasica domaca", "unit": "kg", "qty": 8, "price": 850.00},
            {"code": "M015", "name": "Slanina dimljena", "unit": "kg", "qty": 5, "price": 950.00},
            {"code": "M016", "name": "Sunka kuvana", "unit": "kg", "qty": 5, "price": 1100.00},
            {"code": "M017", "name": "Kulen", "unit": "kg", "qty": 3, "price": 2200.00},
            {"code": "M018", "name": "Pastrmka", "unit": "kg", "qty": 8, "price": 1200.00},
            {"code": "M019", "name": "Skusa fileti", "unit": "kg", "qty": 5, "price": 750.00},
            {"code": "M020", "name": "Lignje ociscene", "unit": "kg", "qty": 4, "price": 1400.00},
        ],
    })

    # ── Invoice 6: Mlekara Subotica (12 items) ──────────────────────────────
    draw_invoice("06_mlekara_subotica.pdf", {
        "invoice_number": "MLS-2026-03/0456",
        "date": "15.03.2026",
        "due_date": "30.03.2026",
        "seller": MLEKARA, "buyer": BUYER, "tax_rate": 20,
        "items": [
            {"code": "D001", "name": "Mleko 2.8% 1l", "unit": "kom", "qty": 50, "price": 120.00},
            {"code": "D002", "name": "Mleko 3.2% 1l", "unit": "kom", "qty": 30, "price": 130.00},
            {"code": "D003", "name": "Pavlaka 200ml", "unit": "kom", "qty": 40, "price": 95.00},
            {"code": "D004", "name": "Kajmak 250g", "unit": "kom", "qty": 20, "price": 280.00},
            {"code": "D005", "name": "Jogurt 1l", "unit": "kom", "qty": 30, "price": 110.00},
            {"code": "D006", "name": "Kefir 1l", "unit": "kom", "qty": 15, "price": 105.00},
            {"code": "D007", "name": "Sir beli mekan", "unit": "kg", "qty": 5, "price": 850.00},
            {"code": "D008", "name": "Kackavalj", "unit": "kg", "qty": 4, "price": 1200.00},
            {"code": "D009", "name": "Gauda sir", "unit": "kg", "qty": 3, "price": 1450.00},
            {"code": "D010", "name": "Puter 200g", "unit": "kom", "qty": 20, "price": 250.00},
            {"code": "D011", "name": "Slag 500ml", "unit": "kom", "qty": 10, "price": 320.00},
            {"code": "D012", "name": "Mascarpone 250g", "unit": "kom", "qty": 10, "price": 380.00},
        ],
    })

    # ── Invoice 7: Pekara Don Don (8 items) ──────────────────────────────────
    draw_invoice("07_pekara_don_don.pdf", {
        "invoice_number": "DD-26/03-0089",
        "date": "16.03.2026",
        "due_date": "31.03.2026",
        "seller": PEKARNICA, "buyer": BUYER, "tax_rate": 20,
        "items": [
            {"code": "P001", "name": "Hleb beli 500g", "unit": "kom", "qty": 30, "price": 65.00},
            {"code": "P002", "name": "Hleb integralni", "unit": "kom", "qty": 15, "price": 95.00},
            {"code": "P003", "name": "Lepinja za burger", "unit": "kom", "qty": 100, "price": 35.00},
            {"code": "P004", "name": "Tortilija 25cm", "unit": "pak", "qty": 10, "price": 280.00},
            {"code": "P005", "name": "Ciabatta", "unit": "kom", "qty": 20, "price": 85.00},
            {"code": "P006", "name": "Focaccia", "unit": "kom", "qty": 10, "price": 120.00},
            {"code": "P007", "name": "Kroasan maslac", "unit": "kom", "qty": 30, "price": 75.00},
            {"code": "P008", "name": "Pita kore gotove", "unit": "pak", "qty": 10, "price": 150.00},
        ],
    })

    # ── Invoice 8: Metro MEGA order — 50 items, multi-page ──────────────────
    draw_invoice("08_metro_mega_narudzba.pdf", {
        "invoice_number": "MCS-2026/03-00250",
        "date": "20.03.2026",
        "due_date": "20.04.2026",
        "seller": METRO, "buyer": BUYER, "tax_rate": 20,
        "items": [
            # Pica
            {"code": "10234", "name": "Coca Cola 0.5l", "unit": "kom", "qty": 96, "price": 85.00},
            {"code": "10235", "name": "Coca Cola 1.5l", "unit": "kom", "qty": 48, "price": 135.00},
            {"code": "10240", "name": "Fanta 0.5l", "unit": "kom", "qty": 48, "price": 85.00},
            {"code": "10241", "name": "Sprite 0.5l", "unit": "kom", "qty": 48, "price": 85.00},
            {"code": "10250", "name": "Knjaz Milos 0.5l", "unit": "kom", "qty": 96, "price": 55.00},
            {"code": "10260", "name": "Rosa 0.5l", "unit": "kom", "qty": 96, "price": 45.00},
            {"code": "10270", "name": "Guarana 0.25l", "unit": "kom", "qty": 48, "price": 90.00},
            {"code": "10280", "name": "Cedevita limun 500g", "unit": "kom", "qty": 12, "price": 380.00},
            # Pivo
            {"code": "50100", "name": "Lav pivo 0.5l", "unit": "kom", "qty": 240, "price": 75.00},
            {"code": "50110", "name": "Jelen pivo 0.5l", "unit": "kom", "qty": 240, "price": 80.00},
            {"code": "50120", "name": "Zajecarsko 0.5l", "unit": "kom", "qty": 120, "price": 78.00},
            {"code": "50130", "name": "Heineken 0.33l", "unit": "kom", "qty": 72, "price": 120.00},
            {"code": "50140", "name": "Erdinger 0.5l", "unit": "kom", "qty": 48, "price": 250.00},
            # Vino
            {"code": "50200", "name": "Vranac 0.75l", "unit": "fla", "qty": 36, "price": 450.00},
            {"code": "50210", "name": "Sauvignon Blanc 0.75l", "unit": "fla", "qty": 24, "price": 650.00},
            {"code": "50220", "name": "Chardonnay 0.75l", "unit": "fla", "qty": 12, "price": 700.00},
            {"code": "50230", "name": "Rose 0.75l", "unit": "fla", "qty": 12, "price": 550.00},
            # Meso
            {"code": "20100", "name": "Pilece belo meso", "unit": "kg", "qty": 30, "price": 620.00},
            {"code": "20105", "name": "Pileci batak", "unit": "kg", "qty": 20, "price": 450.00},
            {"code": "20110", "name": "Pileca krila", "unit": "kg", "qty": 15, "price": 320.00},
            {"code": "20200", "name": "Svinjski vrat", "unit": "kg", "qty": 15, "price": 780.00},
            {"code": "20210", "name": "Svinjska plecka", "unit": "kg", "qty": 10, "price": 650.00},
            {"code": "20300", "name": "Juneci but", "unit": "kg", "qty": 10, "price": 1350.00},
            {"code": "20310", "name": "Junetina mlevena", "unit": "kg", "qty": 10, "price": 850.00},
            # Povrce
            {"code": "30100", "name": "Paradajz", "unit": "kg", "qty": 20, "price": 180.00},
            {"code": "30110", "name": "Krastavac", "unit": "kg", "qty": 15, "price": 150.00},
            {"code": "30120", "name": "Paprika babura", "unit": "kg", "qty": 10, "price": 220.00},
            {"code": "30125", "name": "Paprika ljuta", "unit": "kg", "qty": 3, "price": 280.00},
            {"code": "30130", "name": "Crni luk", "unit": "kg", "qty": 10, "price": 90.00},
            {"code": "30140", "name": "Beli luk", "unit": "kg", "qty": 5, "price": 450.00},
            {"code": "30150", "name": "Krompir", "unit": "kg", "qty": 25, "price": 80.00},
            {"code": "30160", "name": "Sargarepa", "unit": "kg", "qty": 8, "price": 100.00},
            {"code": "30170", "name": "Zelena salata", "unit": "kom", "qty": 15, "price": 80.00},
            {"code": "30180", "name": "Kupus", "unit": "kg", "qty": 10, "price": 70.00},
            # Suva roba
            {"code": "40100", "name": "Brasno T-400 25kg", "unit": "kom", "qty": 4, "price": 2100.00},
            {"code": "40105", "name": "Brasno T-500 25kg", "unit": "kom", "qty": 2, "price": 2200.00},
            {"code": "40110", "name": "Secer 1kg", "unit": "kom", "qty": 20, "price": 120.00},
            {"code": "40120", "name": "So morska 1kg", "unit": "kom", "qty": 10, "price": 85.00},
            {"code": "40130", "name": "Ulje suncokret. 1l", "unit": "kom", "qty": 40, "price": 210.00},
            {"code": "40140", "name": "Maslinovo ulje 1l", "unit": "kom", "qty": 10, "price": 1250.00},
            {"code": "40150", "name": "Pirinac 1kg", "unit": "kom", "qty": 10, "price": 180.00},
            {"code": "40160", "name": "Testenina spagete", "unit": "kom", "qty": 20, "price": 130.00},
            {"code": "40170", "name": "Testenina pene", "unit": "kom", "qty": 15, "price": 130.00},
            {"code": "40180", "name": "Paradajz pelat 400g", "unit": "kom", "qty": 30, "price": 110.00},
            {"code": "40190", "name": "Kecap 500ml", "unit": "kom", "qty": 10, "price": 220.00},
            {"code": "40200", "name": "Majonez 500ml", "unit": "kom", "qty": 10, "price": 280.00},
            {"code": "40210", "name": "Senf 350g", "unit": "kom", "qty": 10, "price": 160.00},
            {"code": "40220", "name": "Ajvar blagi 720ml", "unit": "kom", "qty": 12, "price": 420.00},
            {"code": "40230", "name": "Vegeta 500g", "unit": "kom", "qty": 10, "price": 350.00},
            {"code": "40240", "name": "Biber crni mlev. 50g", "unit": "kom", "qty": 10, "price": 180.00},
        ],
    })

    # ── Invoice 9: Aroma 2nd delivery — overlapping items (18 items) ────────
    draw_invoice("09_aroma_dopuna.pdf", {
        "invoice_number": "AR-0326/0112",
        "date": "21.03.2026",
        "due_date": "21.04.2026",
        "seller": AROMA, "buyer": BUYER, "tax_rate": 20,
        "items": [
            {"code": "V001", "name": "Paradajz", "unit": "kg", "qty": 20, "price": 175.00},
            {"code": "V002", "name": "Krastavac", "unit": "kg", "qty": 12, "price": 145.00},
            {"code": "V003", "name": "Paprika babura", "unit": "kg", "qty": 10, "price": 215.00},
            {"code": "V004", "name": "Tikvice", "unit": "kg", "qty": 8, "price": 195.00},
            {"code": "V008", "name": "Patlidzan", "unit": "kg", "qty": 5, "price": 240.00},
            {"code": "V009", "name": "Cvekla", "unit": "kg", "qty": 4, "price": 120.00},
            {"code": "V010", "name": "Celer koren", "unit": "kg", "qty": 3, "price": 150.00},
            {"code": "V011", "name": "Praziluk", "unit": "kg", "qty": 4, "price": 200.00},
            {"code": "V007", "name": "Sampinjon", "unit": "kg", "qty": 8, "price": 430.00},
            {"code": "V012", "name": "Vrganj susi", "unit": "kg", "qty": 1, "price": 4500.00},
            {"code": "F001", "name": "Limun", "unit": "kg", "qty": 8, "price": 255.00},
            {"code": "F002", "name": "Narandza", "unit": "kg", "qty": 10, "price": 185.00},
            {"code": "F005", "name": "Jabuka zlatni del.", "unit": "kg", "qty": 8, "price": 180.00},
            {"code": "F006", "name": "Kruska", "unit": "kg", "qty": 5, "price": 220.00},
            {"code": "F007", "name": "Kivi", "unit": "kg", "qty": 4, "price": 350.00},
            {"code": "Z001", "name": "Persun", "unit": "veza", "qty": 15, "price": 40.00},
            {"code": "Z004", "name": "Korijander", "unit": "veza", "qty": 5, "price": 70.00},
            {"code": "Z005", "name": "Ruzmarin", "unit": "veza", "qty": 5, "price": 80.00},
        ],
    })

    # ── Invoice 10: Drink Shop 2nd — large spirits order (30 items) ──────────
    draw_invoice("10_drink_shop_mesecni.pdf", {
        "invoice_number": "BD-2026-0389",
        "date": "23.03.2026",
        "due_date": "07.04.2026",
        "seller": DRINK_SHOP, "buyer": BUYER, "tax_rate": 20,
        "items": [
            {"code": "JW01", "name": "Jack Daniels 0.7l", "unit": "kom", "qty": 12, "price": 4200.00},
            {"code": "JW02", "name": "Jack Daniels Honey", "unit": "kom", "qty": 6, "price": 4400.00},
            {"code": "AB01", "name": "Absolut Vodka 0.7l", "unit": "kom", "qty": 12, "price": 2800.00},
            {"code": "AB02", "name": "Absolut Citron 0.7l", "unit": "kom", "qty": 6, "price": 2900.00},
            {"code": "BF01", "name": "Beefeater Gin 0.7l", "unit": "kom", "qty": 8, "price": 2600.00},
            {"code": "HV01", "name": "Havana Club 3yo 0.7l", "unit": "kom", "qty": 8, "price": 3100.00},
            {"code": "HV02", "name": "Havana Club 7yo 0.7l", "unit": "kom", "qty": 4, "price": 4800.00},
            {"code": "BL01", "name": "Baileys 0.7l", "unit": "kom", "qty": 4, "price": 2900.00},
            {"code": "JB01", "name": "Jagermeister 0.7l", "unit": "kom", "qty": 6, "price": 3200.00},
            {"code": "CH01", "name": "Chivas Regal 12 0.7l", "unit": "kom", "qty": 4, "price": 5500.00},
            {"code": "JM01", "name": "Jameson Irish 0.7l", "unit": "kom", "qty": 6, "price": 3800.00},
            {"code": "TQ01", "name": "Jose Cuervo 0.7l", "unit": "kom", "qty": 4, "price": 3500.00},
            {"code": "SC01", "name": "Sljivovica domaca 1l", "unit": "kom", "qty": 10, "price": 1500.00},
            {"code": "SC02", "name": "Lozovaca 1l", "unit": "kom", "qty": 6, "price": 1200.00},
            {"code": "SC03", "name": "Viljamovka 1l", "unit": "kom", "qty": 4, "price": 1800.00},
            # Bezalkoholna
            {"code": "CC01", "name": "Coca Cola 0.25l", "unit": "kom", "qty": 192, "price": 65.00},
            {"code": "CC02", "name": "Coca Cola Zero 0.25l", "unit": "kom", "qty": 96, "price": 65.00},
            {"code": "TN01", "name": "Schweppes Tonic 0.25l", "unit": "kom", "qty": 96, "price": 75.00},
            {"code": "TN02", "name": "Schweppes Bitter L.", "unit": "kom", "qty": 48, "price": 75.00},
            {"code": "RB01", "name": "Red Bull 0.25l", "unit": "kom", "qty": 96, "price": 180.00},
            {"code": "RB02", "name": "Red Bull Sugar Free", "unit": "kom", "qty": 48, "price": 180.00},
            # Kafa i dodaci
            {"code": "EP01", "name": "Lavazza espresso 1kg", "unit": "kg", "qty": 10, "price": 2400.00},
            {"code": "EP02", "name": "Lavazza decaf 1kg", "unit": "kg", "qty": 2, "price": 2600.00},
            {"code": "ML01", "name": "Mleko za kafu 1l", "unit": "kom", "qty": 40, "price": 140.00},
            {"code": "ML02", "name": "Mleko bademovo 1l", "unit": "kom", "qty": 10, "price": 320.00},
            {"code": "ML03", "name": "Mleko sojino 1l", "unit": "kom", "qty": 10, "price": 280.00},
            {"code": "SK01", "name": "Secer kesica 5g x1000", "unit": "pak", "qty": 4, "price": 1800.00},
            {"code": "CJ01", "name": "Cokolada topla 1kg", "unit": "kg", "qty": 3, "price": 1500.00},
            {"code": "CJ02", "name": "Sirup vanila 750ml", "unit": "kom", "qty": 4, "price": 1200.00},
            {"code": "CJ03", "name": "Sirup karamel 750ml", "unit": "kom", "qty": 4, "price": 1200.00},
        ],
    })

    print(f"\nDone! 10 invoices saved to: {OUTPUT_DIR}/")
    print("Upload these via the Saldora UI to test restaurant features.")


if __name__ == "__main__":
    main()
