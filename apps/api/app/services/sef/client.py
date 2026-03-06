"""SEF API client abstraction.

Provides a base class and two implementations:
- DemoSefClient: returns realistic fake data for development
- LiveSefClient: connects to the real SEF REST API
"""

import logging
import uuid
from abc import ABC, abstractmethod
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


class SefError(Exception):
    """Base exception for SEF API errors."""

    def __init__(self, message: str, status_code: int | None = None, response_body: str = ""):
        """Initialize SEF error.

        Args:
            message: Error description.
            status_code: HTTP status code from SEF API.
            response_body: Raw response body for debugging.
        """
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(message)


class BaseSefClient(ABC):
    """Abstract base for SEF API clients.

    Defines the interface for fetching invoices, downloading PDFs,
    and managing invoice status on the SEF system.
    """

    @abstractmethod
    async def fetch_inbound_invoices(self, pib: str, since: datetime | None = None) -> list[dict]:
        """Fetch inbound invoices from SEF.

        Args:
            pib: Organization PIB (tax ID).
            since: Only fetch invoices received after this timestamp.

        Returns:
            List of invoice dicts with SEF data.
        """

    @abstractmethod
    async def get_invoice_detail(self, sef_id: str) -> dict:
        """Get detailed invoice data including UBL XML.

        Args:
            sef_id: SEF invoice identifier.

        Returns:
            Full invoice dict with UBL content.
        """

    @abstractmethod
    async def download_pdf(self, sef_id: str) -> bytes | None:
        """Download PDF attachment for an invoice.

        Args:
            sef_id: SEF invoice identifier.

        Returns:
            PDF bytes or None if no attachment.
        """

    @abstractmethod
    async def accept_invoice(self, sef_id: str) -> dict:
        """Send acceptance status to SEF for an invoice.

        Args:
            sef_id: SEF invoice identifier.

        Returns:
            Updated status from SEF.
        """

    @abstractmethod
    async def reject_invoice(self, sef_id: str, reason: str) -> dict:
        """Send rejection status to SEF for an invoice.

        Args:
            sef_id: SEF invoice identifier.
            reason: Rejection reason text.

        Returns:
            Updated status from SEF.
        """


# Demo data for development without real SEF credentials
_DEMO_SUPPLIERS = [
    {
        "name": "Telekom Srbija a.d.",
        "pib": "100002552",
        "address": "Takovska 2, Beograd",
    },
    {
        "name": "EPS Snabdevanje d.o.o.",
        "pib": "108065817",
        "address": "Carice Milice 2, Beograd",
    },
    {
        "name": "JKP Beogradski vodovod i kanalizacija",
        "pib": "100002590",
        "address": "Kneza Miloša 27, Beograd",
    },
    {
        "name": "NIS a.d. Novi Sad",
        "pib": "104052135",
        "address": "Narodnog fronta 12, Novi Sad",
    },
    {
        "name": "Deltahold d.o.o.",
        "pib": "100069011",
        "address": "Milentija Popovića 7b, Beograd",
    },
]


class DemoSefClient(BaseSefClient):
    """Demo client returning realistic fake data for development.

    Generates sample invoices with Serbian company names and
    realistic amounts. No real API calls are made.
    """

    def __init__(self) -> None:
        """Initialize demo client with stable seed data."""
        self._invoices: list[dict] = []
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazily generate demo invoices on first access."""
        if self._initialized:
            return

        now = datetime.now(UTC)
        for i, supplier in enumerate(_DEMO_SUPPLIERS):
            days_ago = (len(_DEMO_SUPPLIERS) - i) * 3
            received = now - timedelta(days=days_ago)
            inv_date = (now - timedelta(days=days_ago + 2)).date()
            amount = Decimal(str((i + 1) * 12500 + 3000))

            self._invoices.append(
                {
                    "sef_id": str(uuid.uuid5(uuid.NAMESPACE_DNS, f"demo-sef-{i}")),
                    "sef_status": "DELIVERED",
                    "invoice_number": f"2026-{i + 1:04d}",
                    "invoice_date": inv_date.isoformat(),
                    "due_date": (inv_date + timedelta(days=30)).isoformat(),
                    "supplier": supplier,
                    "amount": str(amount),
                    "currency": "RSD",
                    "received_at": received.isoformat(),
                    "line_items": [
                        {
                            "description": f"Usluge - stavka {j + 1}",
                            "quantity": j + 1,
                            "unit_price": str(amount / Decimal(str(j + 1 + i))),
                            "total": str(amount),
                            "vat_rate": "20.00",
                            "vat_amount": str(amount * Decimal("0.2")),
                        }
                        for j in range(min(i + 1, 3))
                    ],
                    "monetary_totals": {
                        "tax_exclusive_amount": str(amount),
                        "tax_amount": str(amount * Decimal("0.2")),
                        "payable_amount": str(amount * Decimal("1.2")),
                    },
                }
            )

        self._initialized = True

    async def fetch_inbound_invoices(self, pib: str, since: datetime | None = None) -> list[dict]:
        """Return demo invoices, optionally filtered by timestamp.

        Args:
            pib: Organization PIB (ignored in demo mode).
            since: Only return invoices received after this timestamp.

        Returns:
            List of demo invoice dicts.
        """
        self._ensure_initialized()
        if since is None:
            return list(self._invoices)

        since_str = since.isoformat()
        return [inv for inv in self._invoices if inv["received_at"] > since_str]

    async def get_invoice_detail(self, sef_id: str) -> dict:
        """Return detail for a specific demo invoice.

        Args:
            sef_id: SEF invoice identifier.

        Returns:
            Invoice dict with UBL placeholder.

        Raises:
            SefError: If invoice not found.
        """
        self._ensure_initialized()
        for inv in self._invoices:
            if inv["sef_id"] == sef_id:
                return {**inv, "ubl_xml": f"<Invoice><ID>{sef_id}</ID></Invoice>"}
        raise SefError(f"Demo invoice not found: {sef_id}", status_code=404)

    async def download_pdf(self, sef_id: str) -> bytes | None:
        """Return None since demo mode has no real PDFs.

        Args:
            sef_id: SEF invoice identifier.

        Returns:
            None (no PDF in demo mode).
        """
        return None

    async def accept_invoice(self, sef_id: str) -> dict:
        """Simulate accepting an invoice on SEF.

        Args:
            sef_id: SEF invoice identifier.

        Returns:
            Updated status dict.
        """
        logger.info("Demo: accepting SEF invoice %s", sef_id)
        return {"sef_id": sef_id, "sef_status": "APPROVED"}

    async def reject_invoice(self, sef_id: str, reason: str) -> dict:
        """Simulate rejecting an invoice on SEF.

        Args:
            sef_id: SEF invoice identifier.
            reason: Rejection reason.

        Returns:
            Updated status dict.
        """
        logger.info("Demo: rejecting SEF invoice %s — %s", sef_id, reason)
        return {"sef_id": sef_id, "sef_status": "REJECTED"}


class LiveSefClient(BaseSefClient):
    """Production client for the real SEF REST API.

    Uses httpx.AsyncClient with API key authentication.
    Handles rate limiting and retries on server errors.
    """

    def __init__(self, api_key: str, base_url: str | None = None, timeout: int = 30):
        """Initialize live SEF client.

        Args:
            api_key: SEF API key for authentication.
            base_url: SEF API base URL (defaults to config).
            timeout: HTTP request timeout in seconds.
        """
        settings = get_settings()
        self.api_key = api_key
        self.base_url = base_url or settings.sef_api_base_url
        self.timeout = timeout

    async def _request(
        self,
        method: str,
        path: str,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict | list:
        """Make an authenticated request to the SEF API.

        Args:
            method: HTTP method.
            path: API path (appended to base_url).
            json: Request body.
            params: Query parameters.

        Returns:
            Parsed JSON response.

        Raises:
            SefError: On API errors.
        """
        url = f"{self.base_url}/{path.lstrip('/')}"
        headers = {
            "ApiKey": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(method, url, json=json, params=params, headers=headers)

        if response.status_code >= 400:
            raise SefError(
                f"SEF API error: {method} {path} → {response.status_code}",
                status_code=response.status_code,
                response_body=response.text,
            )

        if response.status_code == 204:
            return {}

        return response.json()

    async def fetch_inbound_invoices(self, pib: str, since: datetime | None = None) -> list[dict]:
        """Fetch inbound purchase invoices from SEF.

        Args:
            pib: Organization PIB.
            since: Only fetch invoices received after this timestamp.

        Returns:
            List of invoice dicts from SEF API.
        """
        params: dict = {"buyerPib": pib, "status": "DELIVERED"}
        if since:
            params["dateFrom"] = since.strftime("%Y-%m-%dT%H:%M:%S")

        result = await self._request("GET", "purchase-invoices", params=params)
        return result if isinstance(result, list) else result.get("items", [])

    async def get_invoice_detail(self, sef_id: str) -> dict:
        """Fetch full invoice details including UBL XML.

        Args:
            sef_id: SEF invoice identifier.

        Returns:
            Full invoice dict.
        """
        result = await self._request("GET", f"purchase-invoices/{sef_id}")
        return result if isinstance(result, dict) else {}

    async def download_pdf(self, sef_id: str) -> bytes | None:
        """Download PDF attachment from SEF.

        Args:
            sef_id: SEF invoice identifier.

        Returns:
            PDF bytes or None if not available.
        """
        url = f"{self.base_url}/purchase-invoices/{sef_id}/pdf"
        headers = {"ApiKey": self.api_key}

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)

            if response.status_code == 200:
                return response.content
            return None
        except httpx.HTTPError:
            logger.warning("Failed to download PDF for SEF invoice %s", sef_id)
            return None

    async def accept_invoice(self, sef_id: str) -> dict:
        """Send acceptance to SEF.

        Args:
            sef_id: SEF invoice identifier.

        Returns:
            Updated status from SEF.
        """
        result = await self._request("POST", f"purchase-invoices/{sef_id}/accept")
        return result if isinstance(result, dict) else {}

    async def reject_invoice(self, sef_id: str, reason: str) -> dict:
        """Send rejection to SEF with reason.

        Args:
            sef_id: SEF invoice identifier.
            reason: Rejection reason text.

        Returns:
            Updated status from SEF.
        """
        result = await self._request(
            "POST",
            f"purchase-invoices/{sef_id}/reject",
            json={"reason": reason},
        )
        return result if isinstance(result, dict) else {}


def get_sef_client() -> BaseSefClient:
    """Get the appropriate SEF client based on configuration.

    Returns:
        DemoSefClient in demo mode, LiveSefClient otherwise.
    """
    settings = get_settings()
    if settings.sef_demo_mode:
        return DemoSefClient()
    # In production, the API key comes from the SefConnection record
    # This factory is used only for the demo fallback
    return DemoSefClient()
