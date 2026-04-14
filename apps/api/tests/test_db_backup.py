"""Tests for daily database backup (issue #159).

Verifies that the backup task:
- Creates a valid ZIP with SQL dump + manifest
- Manifest record counts match actual DB state
- Manifest contains schema version
- Compressed SQL dump is valid gzip

Since pg_dump requires a real PostgreSQL client binary, we mock the
subprocess call and provide a fake SQL dump. The manifest generation
and ZIP creation are tested against the real test database.
"""

import gzip
import json
import sys
import zipfile
from io import BytesIO
from unittest.mock import MagicMock, patch
from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import decode_token

# Ensure ocr_worker is importable
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[3] / "workers"))


async def _register_and_login(
    client: AsyncClient,
    email: str = "backup-test@example.com",
) -> dict[str, str]:
    """Register a user, create an organization, and return auth headers."""
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "Backup",
            "last_name": "Tester",
        },
    )
    reg_token = reg_resp.json()["access_token"]
    org_resp = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": f"Backup Org {email}"},
        headers={"Authorization": f"Bearer {reg_token}"},
    )
    token = org_resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _get_org_id(headers: dict) -> str:
    token = headers["Authorization"].removeprefix("Bearer ")
    return decode_token(token)["org"]


async def _insert_invoice(test_engine, org_id: str) -> str:
    inv_id = str(uuid4())
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        await session.execute(
            text(
                "INSERT INTO invoices (id, organization_id, status, currency, "
                "created_at, updated_at) VALUES (:id, :org_id, 'review', 'RSD', "
                "NOW(), NOW())"
            ),
            {"id": inv_id, "org_id": org_id},
        )
        await session.commit()
    return inv_id


FAKE_SQL_DUMP = b"""--
-- PostgreSQL database dump
--
CREATE TABLE organizations (id uuid PRIMARY KEY);
CREATE TABLE invoices (id uuid PRIMARY KEY);
INSERT INTO organizations VALUES ('test-org-id');
"""


async def test_backup_creates_valid_zip_with_manifest(client: AsyncClient, test_engine):
    """Backup produces ZIP with SQL dump and manifest matching DB state."""
    headers = await _register_and_login(client, "backup-zip@test.com")
    org_id = _get_org_id(headers)
    await _insert_invoice(test_engine, org_id)

    captured_zip = {}

    def mock_put_object(**kwargs):
        captured_zip["body"] = kwargs["Body"]

    mock_s3 = MagicMock()
    mock_s3.put_object = mock_put_object
    mock_s3.list_objects_v2.return_value = {"Contents": []}

    # Mock pg_dump to return fake SQL
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = FAKE_SQL_DUMP

    sync_url = test_engine.url.render_as_string(hide_password=False).replace("+asyncpg", "")

    # Create a sync session factory for the test DB
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    sync_engine = create_engine(sync_url)
    sync_factory = sessionmaker(bind=sync_engine)

    # Reset the cached engine in ocr_worker.database
    import ocr_worker.database as db_mod

    old_engine = db_mod._engine
    old_factory = db_mod._SessionLocal
    db_mod._engine = sync_engine
    db_mod._SessionLocal = sync_factory

    try:
        with (
            patch("boto3.client", return_value=mock_s3),
            patch("subprocess.run", return_value=mock_result),
            patch.dict(
                "os.environ",
                {
                    "DATABASE_URL": sync_url,
                    "STORAGE_ENDPOINT": "http://localhost:9010",
                    "STORAGE_ACCESS_KEY": "test",
                    "STORAGE_SECRET_KEY": "test",
                    "STORAGE_BUCKET": "test-bucket",
                },
            ),
        ):
            from ocr_worker.tasks import backup_database

            result = backup_database()
    finally:
        db_mod._engine = old_engine
        db_mod._SessionLocal = old_factory
        sync_engine.dispose()

    assert result["status"] == "success"
    assert result["total_records"] > 0
    assert result["tables"] > 0

    # Verify ZIP structure
    zip_bytes = captured_zip["body"]
    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        assert any(n.endswith(".sql.gz") for n in names)
        assert "manifest.json" in names

        # Verify manifest
        manifest = json.loads(zf.read("manifest.json"))
        assert "tables" in manifest
        assert "total_records" in manifest
        assert "schema_version" in manifest
        assert manifest["total_records"] > 0

        # Manifest should include organizations and invoices
        assert "organizations" in manifest["tables"]
        assert "invoices" in manifest["tables"]
        assert manifest["tables"]["organizations"] >= 1
        assert manifest["tables"]["invoices"] >= 1

        # SQL dump should be valid gzip
        sql_gz_name = [n for n in names if n.endswith(".sql.gz")][0]
        sql_text = gzip.decompress(zf.read(sql_gz_name)).decode("utf-8")
        assert "CREATE TABLE" in sql_text


async def test_backup_manifest_counts_match_db(client: AsyncClient, test_engine):
    """Manifest record counts match actual database state."""
    headers = await _register_and_login(client, "backup-counts@test.com")
    org_id = _get_org_id(headers)

    # Insert multiple invoices
    for _ in range(3):
        await _insert_invoice(test_engine, org_id)

    # Get real DB counts
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        org_count = (await session.execute(text("SELECT COUNT(*) FROM organizations"))).scalar()
        inv_count = (await session.execute(text("SELECT COUNT(*) FROM invoices"))).scalar()

    captured_zip = {}

    def mock_put_object(**kwargs):
        captured_zip["body"] = kwargs["Body"]

    mock_s3 = MagicMock()
    mock_s3.put_object = mock_put_object
    mock_s3.list_objects_v2.return_value = {"Contents": []}

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = FAKE_SQL_DUMP

    sync_url = test_engine.url.render_as_string(hide_password=False).replace("+asyncpg", "")

    from sqlalchemy import create_engine as create_sync_engine
    from sqlalchemy.orm import sessionmaker as sync_sessionmaker

    sync_engine = create_sync_engine(sync_url)
    sync_factory = sync_sessionmaker(bind=sync_engine)

    import ocr_worker.database as db_mod

    old_engine = db_mod._engine
    old_factory = db_mod._SessionLocal
    db_mod._engine = sync_engine
    db_mod._SessionLocal = sync_factory

    try:
        with (
            patch("boto3.client", return_value=mock_s3),
            patch("subprocess.run", return_value=mock_result),
            patch.dict(
                "os.environ",
                {
                    "DATABASE_URL": sync_url,
                    "STORAGE_ENDPOINT": "http://localhost:9010",
                    "STORAGE_ACCESS_KEY": "test",
                    "STORAGE_SECRET_KEY": "test",
                    "STORAGE_BUCKET": "test-bucket",
                },
            ),
        ):
            from ocr_worker.tasks import backup_database

            result = backup_database()
    finally:
        db_mod._engine = old_engine
        db_mod._SessionLocal = old_factory
        sync_engine.dispose()

    assert result["status"] == "success"

    with zipfile.ZipFile(BytesIO(captured_zip["body"])) as zf:
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["tables"]["organizations"] == org_count
        assert manifest["tables"]["invoices"] == inv_count


async def test_backup_handles_pg_dump_failure(client: AsyncClient, test_engine):
    """Backup returns failure status when pg_dump fails."""
    await _register_and_login(client, "backup-fail@test.com")

    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = b"connection refused"

    sync_url = test_engine.url.render_as_string(hide_password=False).replace("+asyncpg", "")

    with (
        patch("subprocess.run", return_value=mock_result),
        patch.dict("os.environ", {"DATABASE_URL": sync_url}),
    ):
        from ocr_worker.tasks import backup_database

        result = backup_database()

    assert result["status"] == "failed"
    assert "pg_dump failed" in result["error"]
