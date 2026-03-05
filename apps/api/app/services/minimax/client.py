"""MiniMax REST API client with OAuth2 authentication.

Integrates with MiniMax accounting software (minimax.rs) via their REST API.
Supports received invoice creation, customer lookup/creation, and document attachment.
"""

import logging
from datetime import UTC, datetime, timedelta

import httpx

logger = logging.getLogger(__name__)

TOKEN_URL = "https://moj.minimax.rs/RS/AUT/OAuth20/Token"
API_BASE = "https://moj.minimax.rs/RS/API/api"


class MiniMaxError(Exception):
    """Base exception for MiniMax API errors."""

    def __init__(self, message: str, status_code: int | None = None, response_body: str = ""):
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)


class MiniMaxClient:
    """HTTP client for MiniMax REST API.

    Handles OAuth2 token lifecycle and provides methods for the
    ReceivedInvoice, Customer, and Document modules.

    Args:
        client_id: OAuth2 client ID.
        client_secret: OAuth2 client secret.
        username: MiniMax username.
        password: MiniMax password.
        org_id: MiniMax organization ID (numeric).
        timeout: HTTP request timeout in seconds.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        username: str,
        password: str,
        org_id: int,
        timeout: int = 30,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.username = username
        self.password = password
        self.org_id = org_id
        self.timeout = timeout

        self._access_token: str | None = None
        self._token_expires_at: datetime | None = None

    async def authenticate(self) -> str:
        """Obtain or refresh OAuth2 access token.

        Returns:
            The access token string.

        Raises:
            MiniMaxError: If authentication fails.
        """
        token_valid = (
            self._access_token
            and self._token_expires_at
            and datetime.now(UTC) < self._token_expires_at
        )
        if token_valid:
            return self._access_token

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                TOKEN_URL,
                data={
                    "grant_type": "password",
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "username": self.username,
                    "password": self.password,
                    "scope": "minimax.rs",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

        if response.status_code != 200:
            raise MiniMaxError(
                f"Authentication failed: {response.status_code}",
                status_code=response.status_code,
                response_body=response.text,
            )

        data = response.json()
        self._access_token = data["access_token"]
        expires_in = data.get("expires_in", 3600)
        # Refresh 60s before actual expiry
        self._token_expires_at = datetime.now(UTC) + timedelta(seconds=expires_in - 60)

        logger.info("MiniMax: authenticated successfully, token expires in %ds", expires_in)
        return self._access_token

    async def _request(
        self,
        method: str,
        path: str,
        json: dict | list | None = None,
        params: dict | None = None,
    ) -> dict | list:
        """Make an authenticated API request with auto-retry on 401.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            path: API path relative to /api/orgs/{org_id}/.
            json: Request body.
            params: Query parameters.

        Returns:
            Parsed JSON response.

        Raises:
            MiniMaxError: On API error.
        """
        token = await self.authenticate()
        url = f"{API_BASE}/orgs/{self.org_id}/{path}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(
                method,
                url,
                json=json,
                params=params,
                headers=headers,
            )

        # Retry once on 401 (token expired)
        if response.status_code == 401:
            self._access_token = None
            token = await self.authenticate()
            headers["Authorization"] = f"Bearer {token}"
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method,
                    url,
                    json=json,
                    params=params,
                    headers=headers,
                )

        if response.status_code >= 400:
            raise MiniMaxError(
                f"MiniMax API error: {method} {path} → {response.status_code}",
                status_code=response.status_code,
                response_body=response.text,
            )

        if response.status_code == 204:
            return {}

        return response.json()

    async def find_customer_by_pib(self, pib: str) -> dict | None:
        """Look up a customer (partner) by PIB (tax ID).

        Args:
            pib: Serbian tax identification number.

        Returns:
            Customer dict if found, None otherwise.
        """
        result = await self._request(
            "GET",
            "customers",
            params={"filter": f"TaxNumber eq '{pib}'"},
        )

        rows = result.get("Rows", []) if isinstance(result, dict) else result
        if rows:
            return rows[0]
        return None

    async def create_customer(self, name: str, pib: str, address: str = "", city: str = "") -> dict:
        """Create a new customer in MiniMax.

        Args:
            name: Customer/company name.
            pib: Tax identification number.
            address: Street address.
            city: City name.

        Returns:
            Created customer dict with MiniMax ID.
        """
        payload = {
            "Name": name,
            "TaxNumber": pib,
            "Address": address,
            "City": city,
            "Country": {"Code": "RS"},
            "SubjectToVAT": "Y",
        }
        return await self._request("POST", "customers", json=payload)

    async def find_or_create_customer(
        self,
        pib: str,
        name: str,
        address: str = "",
        city: str = "",
    ) -> dict:
        """Find a customer by PIB or create if not found.

        Args:
            pib: Tax identification number.
            name: Customer name (used for creation).
            address: Street address (used for creation).
            city: City name (used for creation).

        Returns:
            Customer dict with MiniMax ID.
        """
        existing = await self.find_customer_by_pib(pib)
        if existing:
            logger.info("MiniMax: found existing customer for PIB %s", pib)
            return existing

        logger.info("MiniMax: creating new customer for PIB %s (%s)", pib, name)
        return await self.create_customer(name, pib, address, city)

    async def push_received_invoice(self, data: dict) -> dict:
        """Create a received invoice in MiniMax.

        Args:
            data: MiniMax ReceivedInvoice payload (see mapper.py).

        Returns:
            Created invoice response with MiniMax ID.
        """
        return await self._request("POST", "receivedinvoices", json=data)

    async def attach_document(
        self,
        invoice_id: int,
        pdf_bytes: bytes,
        filename: str,
    ) -> dict:
        """Attach a PDF document to an existing received invoice.

        Args:
            invoice_id: MiniMax invoice ID.
            pdf_bytes: PDF file content.
            filename: Original filename.

        Returns:
            Attachment response.
        """
        token = await self.authenticate()
        url = f"{API_BASE}/orgs/{self.org_id}/receivedinvoices/{invoice_id}/attachments"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                files={"file": (filename, pdf_bytes, "application/pdf")},
                headers={"Authorization": f"Bearer {token}"},
            )

        if response.status_code >= 400:
            raise MiniMaxError(
                f"Document attachment failed: {response.status_code}",
                status_code=response.status_code,
                response_body=response.text,
            )

        return response.json() if response.content else {}

    async def get_currency(self, code: str) -> dict | None:
        """Look up a currency by ISO code.

        Args:
            code: ISO 4217 currency code (e.g., 'RSD', 'EUR').

        Returns:
            Currency dict with MiniMax ID, or None if not found.
        """
        result = await self._request(
            "GET",
            "currencies",
            params={"filter": f"Code eq '{code}'"},
        )
        rows = result.get("Rows", []) if isinstance(result, dict) else result
        return rows[0] if rows else None
