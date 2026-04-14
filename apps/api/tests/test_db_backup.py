"""Tests for daily database backup (issue #159).

Verifies that the backup task:
- Creates a valid ZIP with SQL dump + manifest
- Manifest record counts match actual DB state
- Manifest contains checksums (SHA-256) for integrity verification
- Separate checksum.json file uploaded alongside the ZIP
- Compressed SQL dump is valid gzip
- Checksums in manifest match recomputed values from ZIP contents
"""

import gzip
import hashlib
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
    """Extract organization_id from the JWT token in auth headers."""
    token = headers["Authorization"].removeprefix("Bearer ")
    return decode_token(token)["org"]


async def _insert_invoice(test_engine, org_id: str) -> str:
    """Insert a minimal invoice row into the test database."""
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


def _setup_mocks(test_engine):
    """Create mock S3, pg_dump, and sync DB session for backup tests.

    Returns:
        Tuple of (captured_uploads dict, mock_s3, mock_pg_result, sync_url).
    """
    captured = {}

    def mock_put_object(**kwargs):
        captured[kwargs["Key"]] = kwargs["Body"]

    mock_s3 = MagicMock()
    mock_s3.put_object = mock_put_object
    mock_s3.list_objects_v2.return_value = {"Contents": []}

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = (
        b"--\n-- PostgreSQL database dump\n--\n"
        b"CREATE TABLE organizations (id uuid PRIMARY KEY);\n"
        b"CREATE TABLE invoices (id uuid PRIMARY KEY);\n"
        b"INSERT INTO organizations VALUES ('test-org-id');\n"
    )

    sync_url = test_engine.url.render_as_string(hide_password=False).replace("+asyncpg", "")

    return captured, mock_s3, mock_result, sync_url


def _run_backup(captured, mock_s3, mock_result, sync_url):
    """Execute the backup task with mocked externals.

    Args:
        captured: Dict that collects uploaded S3 objects by key.
        mock_s3: Mocked boto3 S3 client.
        mock_result: Mocked subprocess.run result for pg_dump.
        sync_url: Synchronous database URL for the test DB.

    Returns:
        Result dict from backup_database().
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    sync_engine = create_engine(sync_url)
    sync_factory = sessionmaker(bind=sync_engine)

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

    return result


async def test_backup_creates_valid_zip_with_manifest(client: AsyncClient, test_engine):
    """Backup produces ZIP with SQL dump and manifest matching DB state."""
    headers = await _register_and_login(client, "backup-zip@test.com")
    org_id = _get_org_id(headers)
    await _insert_invoice(test_engine, org_id)

    captured, mock_s3, mock_result, sync_url = _setup_mocks(test_engine)
    result = _run_backup(captured, mock_s3, mock_result, sync_url)

    assert result["status"] == "success"
    assert result["total_records"] > 0
    assert result["tables"] > 0

    # Find the ZIP in captured uploads
    zip_key = [k for k in captured if k.endswith(".zip")][0]
    zip_bytes = captured[zip_key]

    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        names = zf.namelist()
        assert any(n.endswith(".sql.gz") for n in names)
        assert "manifest.json" in names

        # Verify manifest structure
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

    for _ in range(3):
        await _insert_invoice(test_engine, org_id)

    # Get real DB counts
    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        org_count = (await session.execute(text("SELECT COUNT(*) FROM organizations"))).scalar()
        inv_count = (await session.execute(text("SELECT COUNT(*) FROM invoices"))).scalar()

    captured, mock_s3, mock_result, sync_url = _setup_mocks(test_engine)
    result = _run_backup(captured, mock_s3, mock_result, sync_url)

    assert result["status"] == "success"

    zip_key = [k for k in captured if k.endswith(".zip")][0]
    with zipfile.ZipFile(BytesIO(captured[zip_key])) as zf:
        manifest = json.loads(zf.read("manifest.json"))
        assert manifest["tables"]["organizations"] == org_count
        assert manifest["tables"]["invoices"] == inv_count


async def test_backup_manifest_contains_checksums(client: AsyncClient, test_engine):
    """Manifest includes SHA-256 checksums for SQL dump and compressed file."""
    headers = await _register_and_login(client, "backup-checksum@test.com")
    org_id = _get_org_id(headers)
    await _insert_invoice(test_engine, org_id)

    captured, mock_s3, mock_result, sync_url = _setup_mocks(test_engine)
    result = _run_backup(captured, mock_s3, mock_result, sync_url)

    assert result["status"] == "success"

    zip_key = [k for k in captured if k.endswith(".zip")][0]
    with zipfile.ZipFile(BytesIO(captured[zip_key])) as zf:
        manifest = json.loads(zf.read("manifest.json"))

        # Checksums must be present
        assert "sql_sha256" in manifest
        assert "compressed_sha256" in manifest
        assert len(manifest["sql_sha256"]) == 64  # SHA-256 hex length
        assert len(manifest["compressed_sha256"]) == 64


async def test_backup_checksums_match_zip_contents(client: AsyncClient, test_engine):
    """Recomputed checksums from ZIP contents match manifest values."""
    headers = await _register_and_login(client, "backup-verify@test.com")
    org_id = _get_org_id(headers)
    await _insert_invoice(test_engine, org_id)

    captured, mock_s3, mock_result, sync_url = _setup_mocks(test_engine)
    result = _run_backup(captured, mock_s3, mock_result, sync_url)

    assert result["status"] == "success"

    zip_key = [k for k in captured if k.endswith(".zip")][0]
    zip_bytes = captured[zip_key]

    with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
        manifest = json.loads(zf.read("manifest.json"))

        # Extract the compressed SQL dump from the ZIP
        sql_gz_name = [n for n in zf.namelist() if n.endswith(".sql.gz")][0]
        compressed_bytes = zf.read(sql_gz_name)

        # Recompute checksums
        recomputed_compressed_sha256 = hashlib.sha256(compressed_bytes).hexdigest()
        assert recomputed_compressed_sha256 == manifest["compressed_sha256"]

        # Decompress and verify raw SQL checksum
        raw_sql = gzip.decompress(compressed_bytes)
        recomputed_sql_sha256 = hashlib.sha256(raw_sql).hexdigest()
        assert recomputed_sql_sha256 == manifest["sql_sha256"]

        # Verify sizes match
        assert len(raw_sql) == manifest["sql_dump_size_bytes"]
        assert len(compressed_bytes) == manifest["compressed_size_bytes"]


async def test_backup_uploads_checksum_file(client: AsyncClient, test_engine):
    """Separate checksum.json file uploaded alongside the ZIP for independent verification."""
    headers = await _register_and_login(client, "backup-csfile@test.com")
    org_id = _get_org_id(headers)
    await _insert_invoice(test_engine, org_id)

    captured, mock_s3, mock_result, sync_url = _setup_mocks(test_engine)
    result = _run_backup(captured, mock_s3, mock_result, sync_url)

    assert result["status"] == "success"

    # A checksum.json should be uploaded alongside the ZIP
    checksum_key = [k for k in captured if k.endswith(".checksum.json")][0]
    checksum = json.loads(captured[checksum_key])

    assert "zip_sha256" in checksum
    assert "sql_sha256" in checksum
    assert "compressed_sha256" in checksum
    assert "total_records" in checksum
    assert "schema_version" in checksum
    assert len(checksum["zip_sha256"]) == 64

    # Verify the zip_sha256 matches the actual ZIP
    zip_key = [k for k in captured if k.endswith(".zip")][0]
    actual_zip_sha256 = hashlib.sha256(captured[zip_key]).hexdigest()
    assert actual_zip_sha256 == checksum["zip_sha256"]


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
