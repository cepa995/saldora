"""Tests for PDV book (KPR/KIR) generation endpoints."""


from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app as fastapi_app
from app.services.export.pdv_books import (
    KPR_COLUMNS,
    _compute_totals,
    _flatten_entry,
    generate_pdv_book_csv,
    generate_pdv_book_xlsx,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_user_with_plan(
    client: AsyncClient,
    email: str,
    plan: str = "free",
) -> dict[str, str]:
    """Register a user, create an organization, set plan, return auth headers."""
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    reg_token = reg_resp.json()["access_token"]
    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": f"Org-{email}"},
        headers={"Authorization": f"Bearer {reg_token}"},
    )
    token = org_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    if plan != "free":
        from app.database import get_db

        db_gen = fastapi_app.dependency_overrides[get_db]()
        db: AsyncSession = await db_gen.__anext__()
        await db.execute(
            text(
                "UPDATE organizations SET plan = :plan "
                "WHERE id = (SELECT organization_id FROM users WHERE email = :email)"
            ),
            {"plan": plan, "email": email},
        )
        await db.commit()
        try:
            await db_gen.__anext__()
        except StopAsyncIteration:
            pass

    return headers


SAMPLE_KPR_ENTRY = {
    "book_type": "KPR",
    "period": "2026-03",
    "sequence": 1,
    "entry_date": "2026-03-01",
    "invoice_date": "2026-03-01",
    "invoice_number": "INV-001",
    "counterparty_pib": "123456789",
    "counterparty_name": "Test Supplier",
    "base_20": "10000",
    "vat_20": "2000",
    "base_10": "5000",
    "vat_10": "500",
    "total": "17500",
    "pp_pdv_fields": {
        "polje_8_1": "10000",
        "polje_8_2": "2000",
        "polje_9_1": "5000",
        "polje_9_2": "500",
    },
}

SAMPLE_KIR_ENTRY = {
    "book_type": "KIR",
    "period": "2026-03",
    "sequence": 1,
    "entry_date": "2026-03-01",
    "invoice_date": "2026-03-01",
    "invoice_number": "OUT-001",
    "counterparty_pib": "987654321",
    "counterparty_name": "Test Buyer",
    "base_20": "20000",
    "vat_20": "4000",
    "base_10": "0",
    "vat_10": "0",
    "total": "24000",
    "pp_pdv_fields": {
        "polje_3_1": "20000",
        "polje_4_1": "4000",
        "polje_6_1": "0",
        "polje_6a_1": "0",
    },
}


# ---------------------------------------------------------------------------
# Unit tests — generation functions
# ---------------------------------------------------------------------------


def test_flatten_entry_kpr():
    """KPR entry flattens pp_pdv_fields into pp_pdv_polje_X keys."""
    flat = _flatten_entry(SAMPLE_KPR_ENTRY, "KPR")
    assert flat["pp_pdv_polje_8"] == "12000"  # 10000 + 2000
    assert flat["pp_pdv_polje_8a"] == "0"
    assert flat["pp_pdv_polje_9"] == "5500"  # 5000 + 500


def test_flatten_entry_kir():
    """KIR entry flattens pp_pdv_fields into pp_pdv_polje_X keys."""
    flat = _flatten_entry(SAMPLE_KIR_ENTRY, "KIR")
    assert flat["pp_pdv_polje_3"] == "20000"
    assert flat["pp_pdv_polje_4"] == "4000"
    assert flat["pp_pdv_polje_6"] == "0"
    assert flat["pp_pdv_polje_6a"] == "0"


def test_compute_totals():
    """Totals correctly sum numeric columns."""
    entries = [
        _flatten_entry(SAMPLE_KPR_ENTRY, "KPR"),
        _flatten_entry(
            {
                **SAMPLE_KPR_ENTRY,
                "sequence": 2,
                "total": "5000",
                "base_20": "3000",
                "vat_20": "600",
            },
            "KPR",
        ),
    ]
    totals = _compute_totals(entries, KPR_COLUMNS)
    assert totals["total"] == 22500.0  # 17500 + 5000
    assert totals["base_20"] == 13000.0  # 10000 + 3000


def test_generate_xlsx_kpr():
    """XLSX generation produces a valid file with correct sheet name."""
    entries = [_flatten_entry(SAMPLE_KPR_ENTRY, "KPR")]
    buffer = generate_pdv_book_xlsx(entries, "KPR", "2026-03")

    from openpyxl import load_workbook

    wb = load_workbook(buffer)
    ws = wb.active
    assert ws.title == "KPR 2026-03"
    # Headers in row 1
    assert ws.cell(1, 1).value == "R.br."
    assert ws.cell(1, 5).value == "Naziv dobavljača"
    # Data in row 2
    assert ws.cell(2, 4).value == "INV-001"
    # Totals in row 3
    assert ws.cell(3, 1).value == "UKUPNO"


def test_generate_xlsx_kir():
    """XLSX KIR has Kupac header instead of Dobavljač."""
    entries = [_flatten_entry(SAMPLE_KIR_ENTRY, "KIR")]
    buffer = generate_pdv_book_xlsx(entries, "KIR", "2026-03")

    from openpyxl import load_workbook

    wb = load_workbook(buffer)
    ws = wb.active
    assert ws.title == "KIR 2026-03"
    assert ws.cell(1, 5).value == "Naziv kupca"
    assert ws.cell(1, 6).value == "PIB kupca"


def test_generate_xlsx_empty():
    """XLSX with empty entries still generates valid file."""
    buffer = generate_pdv_book_xlsx([], "KPR", "2026-03")
    from openpyxl import load_workbook

    wb = load_workbook(buffer)
    ws = wb.active
    assert ws.cell(1, 1).value == "R.br."
    assert ws.cell(2, 1).value is None  # No data rows


def test_generate_csv_kpr():
    """CSV uses semicolon delimiter, quoting, and sep hint for Excel."""
    entries = [_flatten_entry(SAMPLE_KPR_ENTRY, "KPR")]
    buffer = generate_pdv_book_csv(entries, "KPR", "2026-03")
    content = buffer.read().decode("utf-8-sig")
    lines = content.strip().split("\n")
    assert lines[0] == "sep=;"  # Excel separator hint
    assert len(lines) == 4  # sep hint + header + data + totals
    # Header uses semicolons with quoting
    assert '"R.br."' in lines[1]
    # Totals row present
    assert '"UKUPNO"' in lines[3]


def test_generate_csv_decimal_comma():
    """CSV numeric values use comma as decimal separator."""
    entry = {**SAMPLE_KPR_ENTRY, "total": "17500.50"}
    entries = [_flatten_entry(entry, "KPR")]
    buffer = generate_pdv_book_csv(entries, "KPR", "2026-03")
    content = buffer.read().decode("utf-8-sig")
    assert "17500,50" in content


# ---------------------------------------------------------------------------
# API endpoint tests
# ---------------------------------------------------------------------------


async def test_free_user_blocked_from_pdv_books(client: AsyncClient):
    """Free plan users get 403 when accessing PDV book endpoints."""
    headers = await _create_user_with_plan(client, "free-pdv@test.com", "free")
    resp = await client.get(
        "/api/v1/export/pdv-books/preview?book_type=KPR&period=2026-03",
        headers=headers,
    )
    assert resp.status_code == 403


async def test_pro_user_can_preview(client: AsyncClient):
    """Pro plan users can access the preview endpoint."""
    headers = await _create_user_with_plan(client, "pro-pdv@test.com", "pro")
    resp = await client.get(
        "/api/v1/export/pdv-books/preview?book_type=KPR&period=2026-03",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["entry_count"] == 0
    assert data["period"] == "2026-03"
    assert data["book_type"] == "KPR"


async def test_preview_invalid_book_type(client: AsyncClient):
    """Invalid book type returns 400."""
    headers = await _create_user_with_plan(client, "pro-pdv-invalid@test.com", "pro")
    resp = await client.get(
        "/api/v1/export/pdv-books/preview?book_type=INVALID&period=2026-03",
        headers=headers,
    )
    assert resp.status_code == 400


async def test_generate_empty_xlsx(client: AsyncClient):
    """Generate XLSX with no entries returns valid empty file."""
    headers = await _create_user_with_plan(client, "pro-pdv-gen@test.com", "pro")
    resp = await client.post(
        "/api/v1/export/pdv-books",
        json={"book_type": "KPR", "period": "2026-03", "format": "xlsx"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert "application/vnd.openxmlformats" in resp.headers["content-type"]
    assert "KPR_2026-03.xlsx" in resp.headers["content-disposition"]


async def test_generate_empty_csv(client: AsyncClient):
    """Generate CSV with no entries returns valid file."""
    headers = await _create_user_with_plan(client, "pro-pdv-csv@test.com", "pro")
    resp = await client.post(
        "/api/v1/export/pdv-books",
        json={"book_type": "KIR", "period": "2026-03", "format": "csv"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "KIR_2026-03.csv" in resp.headers["content-disposition"]


async def test_invalid_period_format(client: AsyncClient):
    """Invalid period format returns 422."""
    headers = await _create_user_with_plan(client, "pro-pdv-period@test.com", "pro")
    resp = await client.post(
        "/api/v1/export/pdv-books",
        json={"book_type": "KPR", "period": "2026-13", "format": "xlsx"},
        headers=headers,
    )
    assert resp.status_code == 422
