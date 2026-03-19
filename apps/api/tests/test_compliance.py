"""
API tests for ZZPL compliance endpoints.

Covers consent management, deletion requests, DPA lifecycle,
breach notification preview, and privacy policy.
"""

from httpx import AsyncClient

from app.auth import decode_token


async def _auth_headers(
    client: AsyncClient,
    email: str = "zzpl@example.com",
    org_name: str = "ZZPL Org",
) -> dict:
    """Register a user, create an org, return auth headers.

    Args:
        client: HTTP test client.
        email: Registration email.
        org_name: Organization name.

    Returns:
        Authorization headers dict.
    """
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "Test",
            "last_name": "User",
        },
    )
    token = reg.json()["access_token"]
    org = await client.post(
        "/api/v1/auth/create-organization",
        json={"name": org_name},
        headers={"Authorization": f"Bearer {token}"},
    )
    return {"Authorization": f"Bearer {org.json()['access_token']}"}


def _get_user_id(headers: dict) -> str:
    """Extract user_id from JWT.

    Args:
        headers: Auth headers dict.

    Returns:
        User ID string.
    """
    token = headers["Authorization"].removeprefix("Bearer ")
    payload = decode_token(token)
    return payload["sub"]


# ---- Consent ----


async def test_grant_consent_analytics(client: AsyncClient):
    """Granting analytics consent returns 201 with record details."""
    headers = await _auth_headers(client, "zzpl-grant1@example.com", "Grant Org 1")
    resp = await client.post(
        "/api/v1/compliance/consent",
        json={"consent_type": "analytics", "consent_text_version": "1.0"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["consent_type"] == "analytics"
    assert data["granted"] is True
    assert data["granted_at"] is not None
    assert data["consent_text_version"] == "1.0"


async def test_grant_consent_marketing(client: AsyncClient):
    """Granting marketing consent returns 201."""
    headers = await _auth_headers(client, "zzpl-grant2@example.com", "Grant Org 2")
    resp = await client.post(
        "/api/v1/compliance/consent",
        json={"consent_type": "marketing"},
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["consent_type"] == "marketing"


async def test_revoke_consent_analytics(client: AsyncClient):
    """Revoking analytics consent returns 200 with confirmation."""
    headers = await _auth_headers(client, "zzpl-revoke1@example.com", "Revoke Org 1")

    await client.post(
        "/api/v1/compliance/consent",
        json={"consent_type": "analytics"},
        headers=headers,
    )

    resp = await client.post(
        "/api/v1/compliance/consent/revoke",
        json={"consent_type": "analytics"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert "opozvana" in resp.json()["message"]


async def test_revoke_basic_processing_fails(client: AsyncClient):
    """Revoking basic_processing consent returns 422."""
    headers = await _auth_headers(client, "zzpl-revokebasic@example.com", "Basic Org")

    resp = await client.post(
        "/api/v1/compliance/consent/revoke",
        json={"consent_type": "basic_processing"},
        headers=headers,
    )
    assert resp.status_code == 422
    assert "ne može" in resp.json()["detail"]


async def test_list_consent_status(client: AsyncClient):
    """Listing consent returns status for all three types."""
    headers = await _auth_headers(client, "zzpl-list1@example.com", "List Org 1")

    await client.post(
        "/api/v1/compliance/consent",
        json={"consent_type": "analytics"},
        headers=headers,
    )

    resp = await client.get("/api/v1/compliance/consent", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 3
    types = {s["consent_type"] for s in data}
    assert types == {"basic_processing", "analytics", "marketing"}

    analytics = next(s for s in data if s["consent_type"] == "analytics")
    assert analytics["granted"] is True


async def test_consent_history_requires_admin(client: AsyncClient):
    """Consent history endpoint requires admin role."""
    headers = await _auth_headers(client, "zzpl-hist1@example.com", "Hist Org 1")
    resp = await client.get("/api/v1/compliance/consent/history", headers=headers)
    assert resp.status_code == 200


async def test_consent_unauthenticated(client: AsyncClient):
    """Consent endpoints require authentication."""
    resp = await client.get("/api/v1/compliance/consent")
    assert resp.status_code == 401


# ---- Deletion requests ----


async def test_create_deletion_request(client: AsyncClient):
    """Creating a deletion request returns 201 with pending status."""
    headers = await _auth_headers(client, "zzpl-del1@example.com", "Del Org 1")
    resp = await client.post(
        "/api/v1/compliance/deletion-requests",
        json={"request_type": "user_only"},
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "pending"
    assert data["request_type"] == "user_only"


async def test_duplicate_deletion_request_rejected(client: AsyncClient):
    """Creating a second pending request returns 409."""
    headers = await _auth_headers(client, "zzpl-del2@example.com", "Del Org 2")
    await client.post(
        "/api/v1/compliance/deletion-requests",
        json={"request_type": "user_only"},
        headers=headers,
    )
    resp = await client.post(
        "/api/v1/compliance/deletion-requests",
        json={"request_type": "user_only"},
        headers=headers,
    )
    assert resp.status_code == 409


async def test_list_deletion_requests(client: AsyncClient):
    """Admin can list deletion requests for the organization."""
    headers = await _auth_headers(client, "zzpl-del3@example.com", "Del Org 3")
    await client.post(
        "/api/v1/compliance/deletion-requests",
        json={"request_type": "user_only"},
        headers=headers,
    )
    resp = await client.get(
        "/api/v1/compliance/deletion-requests",
        headers=headers,
    )
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


async def test_get_deletion_request_detail(client: AsyncClient):
    """Admin can get a specific deletion request."""
    headers = await _auth_headers(client, "zzpl-del4@example.com", "Del Org 4")
    create_resp = await client.post(
        "/api/v1/compliance/deletion-requests",
        json={"request_type": "user_only"},
        headers=headers,
    )
    req_id = create_resp.json()["id"]

    resp = await client.get(
        f"/api/v1/compliance/deletion-requests/{req_id}",
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == req_id


async def test_process_deletion_completed(client: AsyncClient):
    """Processing a deletion request anonymizes user data and retains invoices."""
    headers = await _auth_headers(client, "zzpl-del5@example.com", "Del Org 5")
    create_resp = await client.post(
        "/api/v1/compliance/deletion-requests",
        json={"request_type": "user_only"},
        headers=headers,
    )
    req_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/compliance/deletion-requests/{req_id}/process",
        json={"status": "completed"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "completed"
    assert data["retained_categories"] is not None
    assert "invoices" in data["retained_categories"]


async def test_process_deletion_rejected(client: AsyncClient):
    """Rejecting a deletion request records the reason."""
    headers = await _auth_headers(client, "zzpl-del6@example.com", "Del Org 6")
    create_resp = await client.post(
        "/api/v1/compliance/deletion-requests",
        json={"request_type": "user_only"},
        headers=headers,
    )
    req_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/compliance/deletion-requests/{req_id}/process",
        json={"status": "rejected", "reason": "Postoje aktivni ugovori"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    assert resp.json()["reason"] == "Postoje aktivni ugovori"


async def test_process_already_processed_returns_400(client: AsyncClient):
    """Processing an already-processed request returns 400."""
    headers = await _auth_headers(client, "zzpl-del7@example.com", "Del Org 7")
    create_resp = await client.post(
        "/api/v1/compliance/deletion-requests",
        json={"request_type": "user_only"},
        headers=headers,
    )
    req_id = create_resp.json()["id"]

    await client.post(
        f"/api/v1/compliance/deletion-requests/{req_id}/process",
        json={"status": "completed"},
        headers=headers,
    )
    resp = await client.post(
        f"/api/v1/compliance/deletion-requests/{req_id}/process",
        json={"status": "completed"},
        headers=headers,
    )
    assert resp.status_code == 400


async def test_deletion_request_not_found(client: AsyncClient):
    """Getting a non-existent deletion request returns 404."""
    headers = await _auth_headers(client, "zzpl-del8@example.com", "Del Org 8")
    resp = await client.get(
        "/api/v1/compliance/deletion-requests/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert resp.status_code == 404


# ---- DPA ----


async def test_create_dpa(client: AsyncClient):
    """Creating a DPA returns 201 with draft status."""
    headers = await _auth_headers(client, "zzpl-dpa1@example.com", "DPA Org 1")
    resp = await client.post(
        "/api/v1/compliance/dpa",
        json={
            "title": "DPA sa procesorom",
            "version": "1.0",
            "effective_from": "2026-03-01",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "DPA sa procesorom"
    assert data["status"] == "draft"


async def test_list_dpas(client: AsyncClient):
    """Listing DPAs returns created agreements."""
    headers = await _auth_headers(client, "zzpl-dpa2@example.com", "DPA Org 2")
    await client.post(
        "/api/v1/compliance/dpa",
        json={
            "title": "DPA 1",
            "version": "1.0",
            "effective_from": "2026-01-01",
        },
        headers=headers,
    )
    resp = await client.get("/api/v1/compliance/dpa", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


async def test_sign_dpa(client: AsyncClient):
    """Signing a draft DPA sets status to active."""
    headers = await _auth_headers(client, "zzpl-dpa3@example.com", "DPA Org 3")
    create_resp = await client.post(
        "/api/v1/compliance/dpa",
        json={
            "title": "DPA za potpisivanje",
            "version": "1.0",
            "effective_from": "2026-03-01",
        },
        headers=headers,
    )
    dpa_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/compliance/dpa/{dpa_id}/sign",
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "active"
    assert data["signed_at"] is not None
    assert data["signed_by"] is not None


async def test_sign_already_signed_dpa_returns_400(client: AsyncClient):
    """Signing an already-active DPA returns 400."""
    headers = await _auth_headers(client, "zzpl-dpa4@example.com", "DPA Org 4")
    create_resp = await client.post(
        "/api/v1/compliance/dpa",
        json={
            "title": "DPA dupli potpis",
            "version": "1.0",
            "effective_from": "2026-03-01",
        },
        headers=headers,
    )
    dpa_id = create_resp.json()["id"]
    await client.post(f"/api/v1/compliance/dpa/{dpa_id}/sign", headers=headers)

    resp = await client.post(
        f"/api/v1/compliance/dpa/{dpa_id}/sign",
        headers=headers,
    )
    assert resp.status_code == 400


async def test_dpa_not_found(client: AsyncClient):
    """Getting a non-existent DPA returns 404."""
    headers = await _auth_headers(client, "zzpl-dpa5@example.com", "DPA Org 5")
    resp = await client.get(
        "/api/v1/compliance/dpa/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert resp.status_code == 404


# ---- Breach notification ----


async def test_breach_notification_preview(client: AsyncClient):
    """Breach notification preview returns Serbian-language notification."""
    headers = await _auth_headers(client, "zzpl-breach1@example.com", "Breach Org")
    resp = await client.post(
        "/api/v1/compliance/breach-notification/preview",
        json={
            "incident_date": "2026-03-15",
            "description": "Neovlašćen pristup bazi podataka",
            "affected_data_types": ["email adrese", "imena"],
            "measures_taken": "Promena lozinki i blokada pristupa",
            "recommendations": "Promenite lozinke na svim servisima",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "Obaveštenje" in data["subject"]
    assert "15.03.2026" in data["subject"]
    assert "Neovlašćen pristup" in data["body"]
    assert "72 sata" in data["body"]


# ---- Privacy policy ----


async def test_privacy_policy_public(client: AsyncClient):
    """Privacy policy is accessible without authentication."""
    resp = await client.get("/api/v1/compliance/privacy-policy")
    assert resp.status_code == 200
    data = resp.json()
    assert data["version"] == "1.0"
    assert "ZZPL" in data["content"]
    assert "Poverenik" in data["content"]


async def test_privacy_policy_contains_required_sections(client: AsyncClient):
    """Privacy policy includes all ZZPL-required sections."""
    resp = await client.get("/api/v1/compliance/privacy-policy")
    content = resp.json()["content"]
    assert "Rukovalac podataka" in content
    assert "Svrha obrade" in content
    assert "Pravni osnov" in content
    assert "Prava lica" in content
    assert "Član 30 ZZPL" in content
