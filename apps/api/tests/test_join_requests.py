"""
API tests for join request management endpoints.

These tests cover the full join request lifecycle: searching organizations,
submitting a request, listing pending requests, and approving or rejecting them.
Tests use two user roles — an admin who owns an org, and a requester who has
no organization.
"""

from httpx import AsyncClient


async def _auth_headers(
    client: AsyncClient, email: str = "test@example.com", org_name: str = "Test Org"
) -> dict:
    """Register a user and create an organization, returning auth headers.

    Args:
        client: HTTP test client.
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
    return {"Authorization": f"Bearer {org.json()['access_token']}"}


async def _register_only_headers(client: AsyncClient, email: str) -> dict:
    """Register a user WITHOUT creating an organization, returning auth headers.

    Args:
        client: HTTP test client.
        email: Email address to register.

    Returns:
        Dict with Authorization header bearing a valid JWT token (no org).
    """
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "first_name": "Requester",
            "last_name": "User",
        },
    )
    token = reg.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---- Search organizations ----


async def test_search_organizations_returns_matches(client: AsyncClient):
    """Search returns organizations whose names contain the query string."""
    await _auth_headers(client, "jr-searchadmin@example.com", "Searchable Komercijal")

    response = await client.get("/api/v1/join-requests/organizations/search?q=Searchable")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    names = [item["name"] for item in data]
    assert any("Searchable" in name for name in names)


async def test_search_organizations_no_auth_required(client: AsyncClient):
    """Organization search is public — no Authorization header needed."""
    await _auth_headers(client, "jr-pubsearch@example.com", "Public Search Corp")

    response = await client.get("/api/v1/join-requests/organizations/search?q=Public")
    assert response.status_code == 200


async def test_search_organizations_short_query_returns_422(client: AsyncClient):
    """Query shorter than 3 characters returns 422 (Pydantic min_length validation)."""
    response = await client.get("/api/v1/join-requests/organizations/search?q=ab")
    assert response.status_code == 422


async def test_search_organizations_returns_id_name_slug(client: AsyncClient):
    """Search result items contain id, name, and slug fields."""
    await _auth_headers(client, "jr-fieldscheck@example.com", "Fields Check Inc")

    response = await client.get("/api/v1/join-requests/organizations/search?q=Fields")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    item = data[0]
    assert "id" in item
    assert "name" in item
    assert "slug" in item


async def test_search_organizations_empty_when_no_match(client: AsyncClient):
    """Search returns an empty list when no organization matches."""
    response = await client.get("/api/v1/join-requests/organizations/search?q=zzznomatch999")
    assert response.status_code == 200
    assert response.json() == []


# ---- Get my pending request ----


async def test_get_my_pending_request_returns_null_when_none(client: AsyncClient):
    """A user with no pending request gets null (not an error)."""
    requester_headers = await _register_only_headers(client, "jr-noreq@example.com")

    response = await client.get("/api/v1/join-requests/mine", headers=requester_headers)
    assert response.status_code == 200
    assert response.json() is None


async def test_get_my_pending_request_returns_request_after_creation(client: AsyncClient):
    """After submitting a request, GET /mine returns that request."""
    await _auth_headers(client, "jr-mineadmin@example.com", "Mine Org")
    requester_headers = await _register_only_headers(client, "jr-minereq@example.com")

    # Get the org id via search
    search = await client.get("/api/v1/join-requests/organizations/search?q=Mine")
    org_id = next(o["id"] for o in search.json() if o["name"] == "Mine Org")

    await client.post(
        "/api/v1/join-requests",
        json={"organization_id": org_id, "message": "Please let me in"},
        headers=requester_headers,
    )

    response = await client.get("/api/v1/join-requests/mine", headers=requester_headers)
    assert response.status_code == 200
    data = response.json()
    assert data is not None
    assert data["status"] == "pending"
    assert str(data["organization_id"]) == org_id
    assert data["user_email"] == "jr-minereq@example.com"
    assert data["organization_name"] == "Mine Org"


async def test_get_my_pending_request_unauthenticated_returns_401(client: AsyncClient):
    """GET /mine without auth returns 401."""
    response = await client.get("/api/v1/join-requests/mine")
    assert response.status_code == 401


# ---- Create join request ----


async def test_create_join_request_success(client: AsyncClient):
    """User without an org can submit a join request; returns 201."""
    await _auth_headers(client, "jr-createadmin@example.com", "Create Target Org")
    requester_headers = await _register_only_headers(client, "jr-createreq@example.com")

    search = await client.get("/api/v1/join-requests/organizations/search?q=Create Target")
    org_id = search.json()[0]["id"]

    response = await client.post(
        "/api/v1/join-requests",
        json={"organization_id": org_id, "message": "I would like to join"},
        headers=requester_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "pending"
    assert str(data["organization_id"]) == org_id
    assert data["message"] == "I would like to join"
    assert data["user_email"] == "jr-createreq@example.com"


async def test_create_join_request_without_message(client: AsyncClient):
    """Join request with no message field is accepted (message is optional)."""
    await _auth_headers(client, "jr-nomsgadmin@example.com", "NoMsg Org")
    requester_headers = await _register_only_headers(client, "jr-nomsgreq@example.com")

    search = await client.get("/api/v1/join-requests/organizations/search?q=NoMsg")
    org_id = search.json()[0]["id"]

    response = await client.post(
        "/api/v1/join-requests",
        json={"organization_id": org_id},
        headers=requester_headers,
    )
    assert response.status_code == 201
    assert response.json()["message"] is None


async def test_create_join_request_duplicate_pending_returns_409(client: AsyncClient):
    """Submitting a second join request when one is already pending returns 409."""
    await _auth_headers(client, "jr-dupeadmin@example.com", "Dupe Org")
    requester_headers = await _register_only_headers(client, "jr-dupereq@example.com")

    search = await client.get("/api/v1/join-requests/organizations/search?q=Dupe")
    org_id = search.json()[0]["id"]

    first = await client.post(
        "/api/v1/join-requests",
        json={"organization_id": org_id},
        headers=requester_headers,
    )
    assert first.status_code == 201

    second = await client.post(
        "/api/v1/join-requests",
        json={"organization_id": org_id},
        headers=requester_headers,
    )
    assert second.status_code == 409
    assert "pending" in second.json()["detail"].lower()


async def test_create_join_request_user_already_in_org_returns_409(client: AsyncClient):
    """A user who already belongs to an organization cannot submit a join request."""
    # This user has an org (created via _auth_headers)
    await _auth_headers(client, "jr-hasorg@example.com", "HasOrg Target")
    another_org_headers = await _auth_headers(client, "jr-anotherorg@example.com", "Another Org")

    search = await client.get("/api/v1/join-requests/organizations/search?q=HasOrg Target")
    org_id = search.json()[0]["id"]

    response = await client.post(
        "/api/v1/join-requests",
        json={"organization_id": org_id},
        headers=another_org_headers,
    )
    assert response.status_code == 409
    assert "already belong" in response.json()["detail"].lower()


async def test_create_join_request_nonexistent_org_returns_404(client: AsyncClient):
    """Submitting a request to a non-existent organization returns 404."""
    requester_headers = await _register_only_headers(client, "jr-badorg@example.com")

    fake_org_id = "00000000-0000-0000-0000-000000000000"
    response = await client.post(
        "/api/v1/join-requests",
        json={"organization_id": fake_org_id},
        headers=requester_headers,
    )
    assert response.status_code == 404


async def test_create_join_request_unauthenticated_returns_401(client: AsyncClient):
    """Creating a join request without auth returns 401."""
    response = await client.post(
        "/api/v1/join-requests",
        json={"organization_id": "00000000-0000-0000-0000-000000000000"},
    )
    assert response.status_code == 401


# ---- Pending count (admin only) ----


async def test_get_pending_count_returns_correct_number(client: AsyncClient):
    """Admin gets the correct count of pending join requests for their org."""
    admin_headers = await _auth_headers(client, "jr-countadmin@example.com", "Count Org")
    req1_headers = await _register_only_headers(client, "jr-countreq1@example.com")
    req2_headers = await _register_only_headers(client, "jr-countreq2@example.com")

    search = await client.get("/api/v1/join-requests/organizations/search?q=Count Org")
    org_id = search.json()[0]["id"]

    await client.post(
        "/api/v1/join-requests",
        json={"organization_id": org_id},
        headers=req1_headers,
    )
    await client.post(
        "/api/v1/join-requests",
        json={"organization_id": org_id},
        headers=req2_headers,
    )

    response = await client.get("/api/v1/join-requests/pending-count", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["count"] == 2


async def test_get_pending_count_zero_when_none(client: AsyncClient):
    """Pending count is 0 when there are no requests."""
    admin_headers = await _auth_headers(client, "jr-zerocount@example.com", "Zero Count Org")

    response = await client.get("/api/v1/join-requests/pending-count", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["count"] == 0


async def test_get_pending_count_unauthenticated_returns_401(client: AsyncClient):
    """Accessing pending count without auth returns 401."""
    response = await client.get("/api/v1/join-requests/pending-count")
    assert response.status_code == 401


# ---- List pending join requests (admin only) ----


async def test_list_pending_join_requests(client: AsyncClient):
    """Admin sees all pending join requests for their organization."""
    admin_headers = await _auth_headers(client, "jr-listadmin@example.com", "List JR Org")
    requester_headers = await _register_only_headers(client, "jr-listreq@example.com")

    search = await client.get("/api/v1/join-requests/organizations/search?q=List JR")
    org_id = search.json()[0]["id"]

    await client.post(
        "/api/v1/join-requests",
        json={"organization_id": org_id, "message": "Hello admin"},
        headers=requester_headers,
    )

    response = await client.get("/api/v1/join-requests", headers=admin_headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    item = data[0]
    assert item["status"] == "pending"
    assert item["user_email"] == "jr-listreq@example.com"
    assert item["message"] == "Hello admin"


async def test_list_pending_join_requests_empty(client: AsyncClient):
    """Admin sees an empty list when no join requests exist."""
    admin_headers = await _auth_headers(client, "jr-emptylist@example.com", "EmptyList Org")

    response = await client.get("/api/v1/join-requests", headers=admin_headers)
    assert response.status_code == 200
    assert response.json() == []


async def test_list_pending_join_requests_unauthenticated_returns_401(client: AsyncClient):
    """Listing pending join requests without auth returns 401."""
    response = await client.get("/api/v1/join-requests")
    assert response.status_code == 401


# ---- Approve join request ----


async def test_approve_join_request_success(client: AsyncClient):
    """Admin can approve a pending join request; returns 200 with success message."""
    admin_headers = await _auth_headers(client, "jr-approveadmin@example.com", "Approve Org")
    requester_headers = await _register_only_headers(client, "jr-approvereq@example.com")

    search = await client.get("/api/v1/join-requests/organizations/search?q=Approve Org")
    org_id = search.json()[0]["id"]

    create_resp = await client.post(
        "/api/v1/join-requests",
        json={"organization_id": org_id},
        headers=requester_headers,
    )
    request_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/join-requests/{request_id}/approve",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert "approved" in response.json()["message"].lower()


async def test_approve_join_request_removes_from_pending_list(client: AsyncClient):
    """After approval, the request no longer appears in the pending list."""
    admin_headers = await _auth_headers(client, "jr-approvecheck@example.com", "ApproveCheck Org")
    requester_headers = await _register_only_headers(client, "jr-approvecheckreq@example.com")

    search = await client.get("/api/v1/join-requests/organizations/search?q=ApproveCheck")
    org_id = search.json()[0]["id"]

    create_resp = await client.post(
        "/api/v1/join-requests",
        json={"organization_id": org_id},
        headers=requester_headers,
    )
    request_id = create_resp.json()["id"]

    await client.post(f"/api/v1/join-requests/{request_id}/approve", headers=admin_headers)

    list_resp = await client.get("/api/v1/join-requests", headers=admin_headers)
    pending_ids = [item["id"] for item in list_resp.json()]
    assert request_id not in pending_ids


async def test_approve_join_request_not_found_returns_404(client: AsyncClient):
    """Approving a non-existent join request returns 404."""
    admin_headers = await _auth_headers(client, "jr-approve404@example.com", "Approve404 Org")

    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.post(
        f"/api/v1/join-requests/{fake_id}/approve",
        headers=admin_headers,
    )
    assert response.status_code == 404


async def test_approve_join_request_unauthenticated_returns_401(client: AsyncClient):
    """Approving a join request without auth returns 401."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.post(f"/api/v1/join-requests/{fake_id}/approve")
    assert response.status_code == 401


# ---- Reject join request ----


async def test_reject_join_request_success(client: AsyncClient):
    """Admin can reject a pending join request; returns 200 with success message."""
    admin_headers = await _auth_headers(client, "jr-rejectadmin@example.com", "Reject Org")
    requester_headers = await _register_only_headers(client, "jr-rejectreq@example.com")

    search = await client.get("/api/v1/join-requests/organizations/search?q=Reject Org")
    org_id = search.json()[0]["id"]

    create_resp = await client.post(
        "/api/v1/join-requests",
        json={"organization_id": org_id},
        headers=requester_headers,
    )
    request_id = create_resp.json()["id"]

    response = await client.post(
        f"/api/v1/join-requests/{request_id}/reject",
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert "rejected" in response.json()["message"].lower()


async def test_reject_join_request_removes_from_pending_list(client: AsyncClient):
    """After rejection, the request no longer appears in the pending list."""
    admin_headers = await _auth_headers(client, "jr-rejectcheck@example.com", "RejectCheck Org")
    requester_headers = await _register_only_headers(client, "jr-rejectcheckreq@example.com")

    search = await client.get("/api/v1/join-requests/organizations/search?q=RejectCheck")
    org_id = search.json()[0]["id"]

    create_resp = await client.post(
        "/api/v1/join-requests",
        json={"organization_id": org_id},
        headers=requester_headers,
    )
    request_id = create_resp.json()["id"]

    await client.post(f"/api/v1/join-requests/{request_id}/reject", headers=admin_headers)

    list_resp = await client.get("/api/v1/join-requests", headers=admin_headers)
    pending_ids = [item["id"] for item in list_resp.json()]
    assert request_id not in pending_ids


async def test_reject_join_request_not_found_returns_404(client: AsyncClient):
    """Rejecting a non-existent join request returns 404."""
    admin_headers = await _auth_headers(client, "jr-reject404@example.com", "Reject404 Org")

    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.post(
        f"/api/v1/join-requests/{fake_id}/reject",
        headers=admin_headers,
    )
    assert response.status_code == 404


async def test_reject_join_request_unauthenticated_returns_401(client: AsyncClient):
    """Rejecting a join request without auth returns 401."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = await client.post(f"/api/v1/join-requests/{fake_id}/reject")
    assert response.status_code == 401


async def test_reject_already_approved_request_returns_404(client: AsyncClient):
    """Attempting to reject an already-approved request returns 404 (no longer pending)."""
    admin_headers = await _auth_headers(
        client, "jr-rejectapproved@example.com", "RejectApproved Org"
    )
    requester_headers = await _register_only_headers(client, "jr-rejectapprovedreq@example.com")

    search = await client.get("/api/v1/join-requests/organizations/search?q=RejectApproved")
    org_id = search.json()[0]["id"]

    create_resp = await client.post(
        "/api/v1/join-requests",
        json={"organization_id": org_id},
        headers=requester_headers,
    )
    request_id = create_resp.json()["id"]

    # Approve first
    await client.post(f"/api/v1/join-requests/{request_id}/approve", headers=admin_headers)

    # Attempt to reject after approval — not pending anymore
    response = await client.post(
        f"/api/v1/join-requests/{request_id}/reject",
        headers=admin_headers,
    )
    assert response.status_code == 404
