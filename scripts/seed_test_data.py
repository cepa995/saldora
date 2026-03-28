"""Seed the database with test restaurant data for end-to-end testing.

Bypasses OCR entirely — directly inserts invoices, line items, and
product catalog entries so all reports can be tested immediately.

Usage:
    docker exec saldora-api python /app/../scripts/seed_test_data.py

Or from host:
    docker exec saldora-api python -c "exec(open('/app/../scripts/seed_test_data.py').read())"
"""

import asyncio
import sys
import uuid
from datetime import date, timedelta
from decimal import Decimal

# ---------------------------------------------------------------------------
# Must run inside the API container where app modules are importable
# ---------------------------------------------------------------------------

async def main():
    from sqlalchemy import select, text
    from app.database import async_engine, AsyncSessionLocal
    from app.models.invoice import Invoice
    from app.models.line_item import InvoiceLineItem
    from app.models.product_catalog import ProductCatalog
    from app.models.organization import Organization
    from app.models.user import User

    async with AsyncSessionLocal() as db:
        # Find the first organization
        result = await db.execute(select(Organization).limit(1))
        org = result.scalar_one_or_none()
        if not org:
            print("ERROR: No organization found. Register a user first.")
            sys.exit(1)

        org_id = org.id
        print(f"Using organization: {org.name} (ID: {org_id})")

        # Check if test data already exists
        result = await db.execute(
            select(Invoice).where(
                Invoice.organization_id == org_id,
                Invoice.invoice_number.like("TEST-%"),
            ).limit(1)
        )
        if result.scalar_one_or_none():
            print("Test data already exists. Delete existing test invoices first.")
            print("Run: DELETE FROM invoices WHERE invoice_number LIKE 'TEST-%';")
            sys.exit(0)

        # --- Supplier data ---
        suppliers = {
            "metro": {
                "pib": "100002857", "name": "METRO Cash & Carry d.o.o.",
                "address": "Autoput za Zagreb bb", "city": "Novi Beograd",
                "postal_code": "11070",
            },
            "aroma": {
                "pib": "101234567", "name": "Aroma d.o.o.",
                "address": "Batajnicki drum 15", "city": "Zemun",
                "postal_code": "11080",
            },
            "drink": {
                "pib": "103456789", "name": "Drink Shop d.o.o.",
                "address": "Vojvodjanskih brigada 22", "city": "Novi Sad",
                "postal_code": "21000",
            },
            "meso": {
                "pib": "104567890", "name": "Meso Promet d.o.o.",
                "address": "Industrijska zona bb", "city": "Batajnica",
                "postal_code": "11210",
            },
            "mlekara": {
                "pib": "100345678", "name": "Mlekara Subotica a.d.",
                "address": "Tolminska 10", "city": "Subotica",
                "postal_code": "24000",
            },
        }

        buyer = {
            "pib": org.settings.get("pib", "112345678") if isinstance(org.settings, dict) else "112345678",
            "name": org.name, "address": "", "city": "", "postal_code": "",
        }

        # --- Invoice definitions ---
        invoices_data = [
            # Invoice 1: Metro weekly (March 10)
            {
                "number": "TEST-MCS-001", "date": date(2026, 3, 10),
                "due": date(2026, 4, 10), "supplier": "metro",
                "items": [
                    ("Coca Cola 0.5l", "kom", 48, 85.00, 20),
                    ("Fanta 0.5l", "kom", 24, 85.00, 20),
                    ("Knjaz Milos 0.5l", "kom", 48, 55.00, 20),
                    ("Rosa 0.5l", "kom", 48, 45.00, 20),
                    ("Pilece belo meso", "kg", 15, 620.00, 20),
                    ("Pileci batak", "kg", 10, 450.00, 20),
                    ("Svinjski vrat", "kg", 8, 780.00, 20),
                    ("Juneci but", "kg", 5, 1350.00, 20),
                    ("Paradajz", "kg", 10, 180.00, 20),
                    ("Krastavac", "kg", 8, 150.00, 20),
                    ("Paprika babura", "kg", 6, 220.00, 20),
                    ("Crni luk", "kg", 5, 90.00, 20),
                    ("Beli luk", "kg", 2, 450.00, 20),
                    ("Ulje suncokretovo 1l", "kom", 20, 210.00, 20),
                    ("Maslinovo ulje 1l", "kom", 5, 1250.00, 20),
                    ("Lav pivo 0.5l", "kom", 120, 75.00, 20),
                    ("Jelen pivo 0.5l", "kom", 120, 80.00, 20),
                    ("Vranac 0.75l", "fla", 24, 450.00, 20),
                ],
            },
            # Invoice 2: Aroma voce/povrce (March 12)
            {
                "number": "TEST-AR-001", "date": date(2026, 3, 12),
                "due": date(2026, 4, 12), "supplier": "aroma",
                "items": [
                    ("Paradajz", "kg", 15, 170.00, 20),
                    ("Krastavac", "kg", 10, 140.00, 20),
                    ("Paprika babura", "kg", 8, 210.00, 20),
                    ("Tikvice", "kg", 5, 190.00, 20),
                    ("Brokoli", "kg", 4, 350.00, 20),
                    ("Spanac", "kg", 3, 280.00, 20),
                    ("Sampinjon", "kg", 5, 420.00, 20),
                    ("Limun", "kg", 5, 250.00, 20),
                    ("Narandza", "kg", 8, 180.00, 20),
                    ("Jagode", "kg", 3, 650.00, 20),
                    ("Banana", "kg", 5, 160.00, 20),
                    ("Persun", "veza", 10, 40.00, 20),
                    ("Bosiljak", "veza", 5, 60.00, 20),
                ],
            },
            # Invoice 3: Drink Shop (March 13)
            {
                "number": "TEST-BD-001", "date": date(2026, 3, 13),
                "due": date(2026, 3, 28), "supplier": "drink",
                "items": [
                    ("Jack Daniels 0.7l", "kom", 6, 4200.00, 20),
                    ("Absolut Vodka 0.7l", "kom", 6, 2800.00, 20),
                    ("Beefeater Gin 0.7l", "kom", 4, 2600.00, 20),
                    ("Coca Cola 0.25l", "kom", 96, 65.00, 20),
                    ("Schweppes Tonic 0.25l", "kom", 48, 75.00, 20),
                    ("Red Bull 0.25l", "kom", 48, 180.00, 20),
                    ("Lavazza espresso 1kg", "kg", 5, 2400.00, 20),
                    ("Mleko za kafu 1l", "kom", 20, 140.00, 20),
                ],
            },
            # Invoice 4: Meso Promet (March 14)
            {
                "number": "TEST-MP-001", "date": date(2026, 3, 14),
                "due": date(2026, 3, 29), "supplier": "meso",
                "items": [
                    ("Pilece belo meso", "kg", 25, 610.00, 20),
                    ("Pileci batak", "kg", 15, 440.00, 20),
                    ("Svinjski vrat", "kg", 15, 770.00, 20),
                    ("Svinjska plecka", "kg", 10, 650.00, 20),
                    ("Juneci but", "kg", 10, 1320.00, 20),
                    ("Junetina mlevena", "kg", 10, 850.00, 20),
                    ("Cevapi 1kg", "kg", 20, 720.00, 20),
                    ("Pljeskavica 150g", "kom", 100, 120.00, 20),
                    ("Kobasica domaca", "kg", 8, 850.00, 20),
                    ("Pastrmka", "kg", 8, 1200.00, 20),
                ],
            },
            # Invoice 5: Mlekara (March 15)
            {
                "number": "TEST-MLS-001", "date": date(2026, 3, 15),
                "due": date(2026, 3, 30), "supplier": "mlekara",
                "items": [
                    ("Mleko 2.8% 1l", "kom", 50, 120.00, 20),
                    ("Pavlaka 200ml", "kom", 40, 95.00, 20),
                    ("Kajmak 250g", "kom", 20, 280.00, 20),
                    ("Jogurt 1l", "kom", 30, 110.00, 20),
                    ("Sir beli mekan", "kg", 5, 850.00, 20),
                    ("Kackavalj", "kg", 4, 1200.00, 20),
                    ("Puter 200g", "kom", 20, 250.00, 20),
                    ("Mascarpone 250g", "kom", 10, 380.00, 20),
                ],
            },
            # Invoice 6: Metro 2nd delivery (March 17) — same items, price changes
            {
                "number": "TEST-MCS-002", "date": date(2026, 3, 17),
                "due": date(2026, 4, 17), "supplier": "metro",
                "items": [
                    ("Coca Cola 0.5l", "kom", 48, 87.00, 20),
                    ("Knjaz Milos 0.5l", "kom", 48, 55.00, 20),
                    ("Pilece belo meso", "kg", 20, 630.00, 20),
                    ("Svinjski vrat", "kg", 10, 790.00, 20),
                    ("Paradajz", "kg", 12, 185.00, 20),
                    ("Krastavac", "kg", 8, 155.00, 20),
                    ("Lav pivo 0.5l", "kom", 120, 75.00, 20),
                    ("Jelen pivo 0.5l", "kom", 120, 80.00, 20),
                    ("Ulje suncokretovo 1l", "kom", 10, 215.00, 20),
                ],
            },
            # Invoice 7: Aroma 2nd delivery (March 21) — overlapping items
            {
                "number": "TEST-AR-002", "date": date(2026, 3, 21),
                "due": date(2026, 4, 21), "supplier": "aroma",
                "items": [
                    ("Paradajz", "kg", 20, 175.00, 20),
                    ("Krastavac", "kg", 12, 145.00, 20),
                    ("Paprika babura", "kg", 10, 215.00, 20),
                    ("Tikvice", "kg", 8, 195.00, 20),
                    ("Patlidzan", "kg", 5, 240.00, 20),
                    ("Sampinjon", "kg", 8, 430.00, 20),
                    ("Limun", "kg", 8, 255.00, 20),
                    ("Narandza", "kg", 10, 185.00, 20),
                    ("Jabuka zlatni del.", "kg", 8, 180.00, 20),
                    ("Persun", "veza", 15, 40.00, 20),
                    ("Ruzmarin", "veza", 5, 80.00, 20),
                ],
            },
        ]

        # --- Create invoices and line items ---
        print(f"\nCreating {len(invoices_data)} invoices...")

        for inv_data in invoices_data:
            supplier = suppliers[inv_data["supplier"]]
            items = inv_data["items"]

            # Calculate totals
            subtotal = sum(Decimal(str(qty * price)) for _, _, qty, price, _ in items)
            tax_rate = Decimal("20")
            tax_amount = (subtotal * tax_rate / 100).quantize(Decimal("0.01"))
            total = subtotal + tax_amount

            line_items_json = [
                {
                    "description": desc,
                    "quantity": qty,
                    "unit_price": price,
                    "total": round(qty * price, 2),
                    "tax_rate": tr,
                    "tax_amount": round(qty * price * tr / 100, 2),
                }
                for desc, unit, qty, price, tr in items
            ]

            invoice = Invoice(
                id=uuid.uuid4(),
                organization_id=org_id,
                status="verified",
                invoice_number=inv_data["number"],
                invoice_date=inv_data["date"],
                due_date=inv_data["due"],
                seller=supplier,
                buyer=buyer,
                subtotal=subtotal,
                tax_rate=tax_rate,
                tax_amount=tax_amount,
                total_amount=total,
                currency="RSD",
                line_items=line_items_json,
                confidence_score=Decimal("0.95"),
                ocr_engine="test_seed",
            )
            db.add(invoice)
            await db.flush()

            # Populate denormalized line items
            for desc, unit, qty, price, tr in items:
                li = InvoiceLineItem(
                    invoice_id=invoice.id,
                    organization_id=org_id,
                    description=desc,
                    quantity=Decimal(str(qty)),
                    unit_price=Decimal(str(price)),
                    total=Decimal(str(round(qty * price, 2))),
                    tax_rate=Decimal(str(tr)),
                    tax_amount=Decimal(str(round(qty * price * tr / 100, 2))),
                    seller_name=supplier["name"],
                    seller_pib=supplier["pib"],
                    invoice_date=inv_data["date"],
                    currency="RSD",
                )
                db.add(li)

            print(f"  {inv_data['number']}: {len(items)} items, total: {total} RSD")

        # --- Create product catalog entries ---
        print("\nCreating product catalog entries...")

        categories = {
            "piće": [
                ("Coca Cola 0.5l", "kom", 200.00, 135),
                ("Fanta 0.5l", "kom", 200.00, 135),
                ("Knjaz Milos 0.5l", "kom", 120.00, 118),
                ("Rosa 0.5l", "kom", 100.00, 122),
                ("Lav pivo 0.5l", "kom", 250.00, 233),
                ("Jelen pivo 0.5l", "kom", 260.00, 225),
                ("Vranac 0.75l", "fla", 1200.00, 167),
                ("Jack Daniels 0.7l", "kom", 800.00, None),
                ("Coca Cola 0.25l", "kom", 150.00, 131),
                ("Red Bull 0.25l", "kom", 400.00, 122),
                ("Lavazza espresso 1kg", "kg", 300.00, None),
            ],
            "meso": [
                ("Pilece belo meso", "kg", 1100.00, 77),
                ("Pileci batak", "kg", 800.00, 78),
                ("Svinjski vrat", "kg", 1400.00, 79),
                ("Juneci but", "kg", 2400.00, 78),
                ("Cevapi 1kg", "kg", 1400.00, 94),
                ("Pljeskavica 150g", "kom", 250.00, 108),
                ("Pastrmka", "kg", 2200.00, 83),
            ],
            "povrce": [
                ("Paradajz", "kg", 350.00, 94),
                ("Krastavac", "kg", 300.00, 100),
                ("Paprika babura", "kg", 450.00, 105),
                ("Tikvice", "kg", 400.00, 111),
                ("Crni luk", "kg", 180.00, 100),
                ("Beli luk", "kg", 900.00, 100),
                ("Sampinjon", "kg", 850.00, 102),
            ],
            "voce": [
                ("Limun", "kg", 500.00, 100),
                ("Narandza", "kg", 350.00, 94),
                ("Jagode", "kg", 1200.00, 85),
                ("Banana", "kg", 300.00, 88),
            ],
            "mlecni": [
                ("Mleko 2.8% 1l", "kom", 200.00, 67),
                ("Pavlaka 200ml", "kom", 180.00, 89),
                ("Kajmak 250g", "kom", 500.00, 79),
                ("Sir beli mekan", "kg", 1500.00, 76),
                ("Kackavalj", "kg", 2200.00, 83),
            ],
            "suva_roba": [
                ("Ulje suncokretovo 1l", "kom", 350.00, 67),
                ("Maslinovo ulje 1l", "kom", 2000.00, 60),
            ],
        }

        product_count = 0
        for category, products in categories.items():
            for name, uom, sell_price, margin in products:
                product = ProductCatalog(
                    organization_id=org_id,
                    canonical_name=name,
                    unit_of_measure=uom,
                    category=category,
                    aliases=[name],
                    selling_price=Decimal(str(sell_price)),
                    default_margin_pct=Decimal(str(margin)) if margin else None,
                )
                db.add(product)
                product_count += 1

        await db.flush()

        # Link line items to products by matching description
        print("Linking line items to product catalog...")
        products_result = await db.execute(
            select(ProductCatalog).where(ProductCatalog.organization_id == org_id)
        )
        products = products_result.scalars().all()

        linked = 0
        for product in products:
            from sqlalchemy import update, func as sa_func
            stmt = (
                update(InvoiceLineItem)
                .where(
                    InvoiceLineItem.organization_id == org_id,
                    sa_func.lower(sa_func.trim(InvoiceLineItem.description))
                    == sa_func.lower(sa_func.trim(product.canonical_name)),
                    InvoiceLineItem.product_id.is_(None),
                )
                .values(product_id=product.id)
            )
            result = await db.execute(stmt)
            linked += result.rowcount
            product.match_count = result.rowcount

        await db.commit()

        # --- Summary ---
        total_invoices = len(invoices_data)
        total_items = sum(len(inv["items"]) for inv in invoices_data)

        print(f"\n{'='*50}")
        print(f"SEED COMPLETE")
        print(f"{'='*50}")
        print(f"Invoices created:    {total_invoices}")
        print(f"Line items created:  {total_items}")
        print(f"Products in catalog: {product_count}")
        print(f"Items linked:        {linked}")
        print(f"")
        print(f"TEST EACH REPORT:")
        print(f"  /izvestaji → Primljena roba      (date: 2026-03-01 to 2026-03-31)")
        print(f"  /izvestaji → Potrosnja dobavljac  (same dates)")
        print(f"  /izvestaji → Mesecni pregled      (same dates)")
        print(f"  /izvestaji → Poredjenje cena       (Paradajz: Metro 180 vs Aroma 170)")
        print(f"  /izvestaji → Pregled troskova      (weekly/monthly)")
        print(f"  /izvestaji → Kalkulacija            (margin + selling prices)")
        print(f"  /izvestaji → RUC                    (markup analysis)")
        print(f"  /izvestaji → Po kategorijama        (pice, meso, povrce...)")
        print(f"  /katalog                             (42 products with prices)")
        print(f"  /dpu        → date: 2026-03-10      (Metro delivery)")
        print(f"  /dpu        → date: 2026-03-12      (Aroma delivery)")
        print(f"  /dpu        → date: 2026-03-14      (Meso Promet delivery)")


if __name__ == "__main__":
    asyncio.run(main())
else:
    # When exec'd inside container
    asyncio.run(main())
