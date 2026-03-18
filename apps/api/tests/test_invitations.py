"""
API tests for invitation management endpoints.

These tests cover the full invitation lifecycle: creating invitations,
listing them, revoking them, and accepting them as a new or existing user.
Email sending is mocked to avoid network calls.
"""

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker


async def _auth_headers(
    client: AsyncClient, test_engine, email: str = "test@example.com", org_name: str = "Test Org"
) -> dict:
    """Register a user, create an organization, upgrade to agency plan, and return auth headers.

    Args:
        client: HTTP test client.
        test_engine: SQLAlchemy async engine for DB operations.
        email: Email address to register.
        org_name: Organization name to create.

    Returns:
        Dict with Authorization header bearing a valid JWT token.
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
    # Upgrade to agency plan to bypass member quota
    session_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        await db.execute(
            text(f"UPDATE organizations SET plan = 'agency' WHERE name = '{org_name}'")
        )
        await db.commit()
    return {"Authorization": f"Bearer {org.json()['access_token']}"}


# ---- Create invitation ----


async def test_create_invitation_success(client: AsyncClient, test_engine):
    """Admin can create an invitation; returns 201 with invitation details."""
    headers = await _auth_headers(client, test_engine, "inv-admin1@example.com", "Inv Org 1")

    with patch(
        "app.routers.invitations.send_invitation_email",
        new_callable=AsyncMock,
        return_value=True,
    ):
        response = await client.post(
            "/api/v1/invitations",
            json={"email": "inv-newmember@example.com", "role": "operator"},
            headers=headers,
        )

    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "inv-newmember@example.com"
    assert data["role"] == "operator"
    assert data["status"] == "pending"
    assert "token" in data
    assert "id" in data
    assert "expires_at" in data


async def test_create_invitation_sends_email(client: AsyncClient, test_engine):
    """Creating an invitation triggers the email-sending function."""
    headers = await _auth_headers(client, test_engine, "inv-emailsend@example.com", "Email Org")

    with patch(
        "app.routers.invitations.send_invitation_email",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_send:
        await client.post(
            "/api/v1/invitations",
            json={"email": "inv-recipient@example.com", "role": "viewer"},
            headers=headers,
        )

    mock_send.assert_awaited_once()
    call_kwargs = mock_send.call_args.kwargs
    assert call_kwargs["to_email"] == "inv-recipient@example.com"
    assert call_kwargs["role"] == "viewer"


async def test_create_invitation_duplicate_email_returns_409(client: AsyncClient, test_engine):
    """Creating a second pending invitation for the same email returns 409."""
    headers = await _auth_headers(client, test_engine, "inv-admin2@example.com", "Inv Org 2")

    with patch(
        "app.routers.invitations.send_invitation_email",
        new_callable=AsyncMock,
        return_value=True,
    ):
        # First invitation
        first = await client.post(
            "/api/v1/invitations",
            json={"email": "inv-dupe@example.com", "role": "operator"},
            headers=headers,
        )
        assert first.status_code == 201

        # Second invitation to same email
        second = await client.post(
            "/api/v1/invitations",
            json={"email": "inv-dupe@example.com", "role": "operator"},
            headers=headers,
        )

    assert second.status_code == 409
    assert "pending invitation" in second.json()["detail"].lower()


async def test_create_invitation_unauthenticated_returns_401(client: AsyncClient, test_engine):
    """Creating an invitation without auth returns 401."""
    response = await client.post(
        "/api/v1/invitations",
        json={"email": "inv-unauth@example.com", "role": "operator"},
    )
    assert response.status_code == 401


async def test_create_invitation_invalid_role_returns_422(client: AsyncClient, test_engine):
    """Creating an invitation with an unsupported role returns 422."""
    headers = await _auth_headers(client, test_engine, "inv-badrole@example.com", "BadRole Org")

    response = await client.post(
        "/api/v1/invitations",
        json={"email": "inv-badrole-target@example.com", "role": "superuser"},
        headers=headers,
    )
    assert response.status_code == 422


# ---- List invitations ----


async def test_list_invitations_returns_pending_only(client: AsyncClient, test_engine):
    """GET /invitations/ returns the list of pending invitations for the org."""
    headers = await _auth_headers(client, test_engine, "inv-list@example.com", "List Org")

    with patch(
        "app.routers.invitations.send_invitation_email",
        new_callable=AsyncMock,
        return_value=True,
    ):
        await client.post(
            "/api/v1/invitations",
            json={"email": "inv-listed1@example.com", "role": "operator"},
            headers=headers,
        )
        await client.post(
            "/api/v1/invitations",
            json={"email": "inv-listed2@example.com", "role": "viewer"},
            headers=headers,
        )

    response = await client.get("/api/v1/invitations", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    emails = {item["email"] for item in data}
    assert "inv-listed1@example.com" in emails
    assert "inv-listed2@example.com" in emails


async def test_list_invitations_empty_when_none(client: AsyncClient, test_engine):
    """GET /invitations/ returns an empty list when no pending invitations exist."""
    headers = await _auth_headers(client, test_engine, "inv-empty@example.com", "Empty Org")

    response = await client.get("/api/v1/invitations", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


async def test_list_invitations_unauthenticated_returns_401(client: AsyncClient, test_engine):
    """Listing invitations without auth returns 401."""
    response = await client.get("/api/v1/invitations")
    assert response.status_code == 401


# ---- Revoke invitation ----


async def test_revoke_invitation_success(client: AsyncClient, test_engine):
    """Admin can revoke a pending invitation; returns 200 with success message."""
    headers = await _auth_headers(client, test_engine, "inv-revoke@example.com", "Revoke Org")

    with patch(
        "app.routers.invitations.send_invitation_email",
        new_callable=AsyncMock,
        return_value=True,
    ):
        create_resp = await client.post(
            "/api/v1/invitations",
            json={"email": "inv-revoke-target@example.com", "role": "operator"},
            headers=headers,
        )
    invitation_id = create_resp.json()["id"]

    response = await client.delete(
        f"/api/v1/invitations/{invitation_id}",
        headers=headers,
    )
    assert response.status_code == 200
    assert "revoked" in response.json()["message"].lower()


async def test_revoke_invitation_not_found_returns_404(client: AsyncClient, test_engine):
    """Revoking a non-existent invitation returns 404."""
    headers = await _auth_headers(
        client, test_engine, "inv-revokenotfound@example.com", "NotFound Org"
    )

    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.delete(
        f"/api/v1/invitations/{fake_id}",
        headers=headers,
    )
    assert response.status_code == 404


async def test_revoke_invitation_removes_from_list(client: AsyncClient, test_engine):
    """After revoking, the invitation no longer appears in the list."""
    headers = await _auth_headers(
        client, test_engine, "inv-revokecheck@example.com", "RevokeCheck Org"
    )

    with patch(
        "app.routers.invitations.send_invitation_email",
        new_callable=AsyncMock,
        return_value=True,
    ):
        create_resp = await client.post(
            "/api/v1/invitations",
            json={"email": "inv-revokecheck-target@example.com", "role": "viewer"},
            headers=headers,
        )
    invitation_id = create_resp.json()["id"]

    await client.delete(f"/api/v1/invitations/{invitation_id}", headers=headers)

    list_resp = await client.get("/api/v1/invitations", headers=headers)
    remaining_ids = [item["id"] for item in list_resp.json()]
    assert invitation_id not in remaining_ids


# ---- Get invitation info (public) ----


async def test_get_invitation_info_success(client: AsyncClient, test_engine):
    """Anyone can retrieve public info about a valid invitation by token."""
    headers = await _auth_headers(client, test_engine, "inv-infocheck@example.com", "Info Org")

    with patch(
        "app.routers.invitations.send_invitation_email",
        new_callable=AsyncMock,
        return_value=True,
    ):
        create_resp = await client.post(
            "/api/v1/invitations",
            json={"email": "inv-infotarget@example.com", "role": "manager"},
            headers=headers,
        )
    token = create_resp.json()["token"]

    # No auth required for this endpoint
    response = await client.get(f"/api/v1/invitations/accept/{token}")
    assert response.status_code == 200
    data = response.json()
    assert "organization_name" in data
    assert data["organization_name"] == "Info Org"
    assert data["role"] == "manager"
    assert data["email"] == "inv-infotarget@example.com"
    assert "expires_at" in data


async def test_get_invitation_info_invalid_token_returns_404(client: AsyncClient, test_engine):
    """A non-existent invitation token returns 404."""
    response = await client.get("/api/v1/invitations/accept/invalid-token-xyz")
    assert response.status_code == 404


async def test_get_invitation_info_revoked_returns_410(client: AsyncClient, test_engine):
    """A revoked invitation token returns 410 Gone."""
    headers = await _auth_headers(client, test_engine, "inv-revoked410@example.com", "Gone Org")

    with patch(
        "app.routers.invitations.send_invitation_email",
        new_callable=AsyncMock,
        return_value=True,
    ):
        create_resp = await client.post(
            "/api/v1/invitations",
            json={"email": "inv-revoked410-target@example.com", "role": "viewer"},
            headers=headers,
        )
    invitation = create_resp.json()
    token = invitation["token"]
    invitation_id = invitation["id"]

    # Revoke the invitation
    await client.delete(f"/api/v1/invitations/{invitation_id}", headers=headers)

    response = await client.get(f"/api/v1/invitations/accept/{token}")
    assert response.status_code == 410


# ---- Accept invitation ----


async def test_accept_invitation_creates_new_user(client: AsyncClient, test_engine):
    """Accepting an invitation with a new email creates a user account."""
    headers = await _auth_headers(client, test_engine, "inv-acceptadmin@example.com", "Accept Org")

    with patch(
        "app.routers.invitations.send_invitation_email",
        new_callable=AsyncMock,
        return_value=True,
    ):
        create_resp = await client.post(
            "/api/v1/invitations",
            json={"email": "inv-brandnew@example.com", "role": "operator"},
            headers=headers,
        )
    token = create_resp.json()["token"]

    response = await client.post(
        f"/api/v1/invitations/accept/{token}",
        json={
            "first_name": "Brand",
            "last_name": "New",
            "password": "newpass123",
        },
    )
    assert response.status_code == 201
    assert "accepted" in response.json()["message"].lower()


async def test_accept_invitation_moves_existing_user(client: AsyncClient, test_engine):
    """Accepting an invitation for an existing user moves them to the new org."""
    # Admin creates an org and an invitation
    admin_headers = await _auth_headers(
        client, test_engine, "inv-moveadmin@example.com", "Move Org"
    )

    # Register the target user (they have no org yet)
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "inv-existing@example.com",
            "password": "securepass123",
            "first_name": "Existing",
            "last_name": "User",
        },
    )

    with patch(
        "app.routers.invitations.send_invitation_email",
        new_callable=AsyncMock,
        return_value=True,
    ):
        create_resp = await client.post(
            "/api/v1/invitations",
            json={"email": "inv-existing@example.com", "role": "viewer"},
            headers=admin_headers,
        )
    token = create_resp.json()["token"]

    response = await client.post(
        f"/api/v1/invitations/accept/{token}",
        json={"password": "securepass123"},
    )
    assert response.status_code == 201
    assert "accepted" in response.json()["message"].lower()


async def test_accept_invitation_invalid_token_returns_404(client: AsyncClient, test_engine):
    """Accepting a non-existent token returns 404."""
    response = await client.post(
        "/api/v1/invitations/accept/nonexistent-token",
        json={"password": "somepassword"},
    )
    assert response.status_code == 404


async def test_accept_invitation_after_revoke_returns_410(client: AsyncClient, test_engine):
    """Accepting a revoked invitation returns 410 Gone."""
    headers = await _auth_headers(
        client, test_engine, "inv-acceptrevoked@example.com", "AcceptRevoke Org"
    )

    with patch(
        "app.routers.invitations.send_invitation_email",
        new_callable=AsyncMock,
        return_value=True,
    ):
        create_resp = await client.post(
            "/api/v1/invitations",
            json={"email": "inv-acceptrevoked-target@example.com", "role": "operator"},
            headers=headers,
        )
    invitation = create_resp.json()
    token = invitation["token"]
    invitation_id = invitation["id"]

    await client.delete(f"/api/v1/invitations/{invitation_id}", headers=headers)

    response = await client.post(
        f"/api/v1/invitations/accept/{token}",
        json={"password": "somepassword"},
    )
    assert response.status_code == 410


async def test_accept_invitation_twice_returns_410(client: AsyncClient, test_engine):
    """Accepting an already-accepted invitation returns 410 Gone."""
    headers = await _auth_headers(
        client, test_engine, "inv-doubleaccept@example.com", "DoubleAccept Org"
    )

    with patch(
        "app.routers.invitations.send_invitation_email",
        new_callable=AsyncMock,
        return_value=True,
    ):
        create_resp = await client.post(
            "/api/v1/invitations",
            json={"email": "inv-doubleaccept-target@example.com", "role": "operator"},
            headers=headers,
        )
    token = create_resp.json()["token"]

    # Accept once
    await client.post(
        f"/api/v1/invitations/accept/{token}",
        json={"first_name": "Once", "last_name": "Done", "password": "newpass123"},
    )

    # Accept again
    response = await client.post(
        f"/api/v1/invitations/accept/{token}",
        json={"first_name": "Twice", "last_name": "Done", "password": "newpass123"},
    )
    assert response.status_code == 410
