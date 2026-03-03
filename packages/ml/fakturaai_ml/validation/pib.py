"""PIB (Tax ID) validation for Serbian companies."""

import logging
import re
from typing import Any

from fakturaai_ml.types import ValidationWarning, WarningType

logger = logging.getLogger(__name__)


class PIBValidator:
    """
    Validate Serbian PIB (Poreski Identifikacioni Broj).

    PIB is a 9-digit tax identification number.
    Uses mod-11 checksum algorithm for format validation.
    """

    def __init__(self):
        """Initialize PIB validator."""
        self._warnings: list[ValidationWarning] = []

    def validate(self, pib: str, entity: str = "pib") -> bool:
        """
        Validate PIB format using ISO 7064 Mod 11,10 algorithm.

        Args:
            pib: PIB string to validate.
            entity: Field name for warnings — "seller_pib" or "buyer_pib".

        Returns:
            True if valid, False otherwise.
        """
        self._warnings = []

        # Sanitize: strip whitespace and common OCR separators
        pib = re.sub(r"[\s\-./]", "", pib.strip()) if pib else ""

        entity_label = (
            "PIB prodavca"
            if entity == "seller_pib"
            else "PIB kupca"
            if entity == "buyer_pib"
            else "PIB"
        )

        # Basic format check
        if not pib or not pib.isdigit():
            self._warnings.append(
                ValidationWarning(
                    warning_type=WarningType.PIB_INVALID_FORMAT,
                    message=f"{entity_label} mora sadržati samo cifre",
                    field_name=entity,
                    severity="error",
                    blocking=True,
                )
            )
            return False

        if len(pib) != 9:
            self._warnings.append(
                ValidationWarning(
                    warning_type=WarningType.PIB_INVALID_FORMAT,
                    message=f"{entity_label} mora imati tačno 9 cifara",
                    field_name=entity,
                    severity="error",
                    blocking=True,
                )
            )
            return False

        # PIB cannot start with 0
        if pib[0] == "0":
            self._warnings.append(
                ValidationWarning(
                    warning_type=WarningType.PIB_INVALID_FORMAT,
                    message=f"{entity_label} ne može počinjati sa 0",
                    field_name=entity,
                    severity="error",
                    blocking=True,
                )
            )
            return False

        # ISO 7064 Mod 11,10 checksum validation
        if not self._validate_checksum(pib):
            self._warnings.append(
                ValidationWarning(
                    warning_type=WarningType.PIB_INVALID_FORMAT,
                    message=f"{entity_label} nije validan (kontrolna cifra)",
                    field_name=entity,
                    severity="warning",
                    blocking=False,  # Allow with warning - OCR might have misread
                )
            )
            return False

        return True

    def _validate_checksum(self, pib: str) -> bool:
        """
        Validate PIB using ISO 7064 Mod 11,10 checksum algorithm.

        Algorithm:
            1. Set product = 10.
            2. For each of the first 8 digits:
               a. sum = (product + digit) % 10; if sum == 0: sum = 10
               b. product = (sum * 2) % 11
            3. check_digit = (11 - product) % 10
            4. Compare with the 9th digit.

        Args:
            pib: 9-digit string (caller ensures length and digit-only).

        Returns:
            True if the check digit matches.
        """
        try:
            product = 10
            for i in range(8):
                digit = int(pib[i])
                s = (product + digit) % 10
                if s == 0:
                    s = 10
                product = (s * 2) % 11

            check_digit = (11 - product) % 10
            return int(pib[8]) == check_digit

        except (ValueError, IndexError):
            return False

    def get_warnings(self) -> list[ValidationWarning]:
        """Get warnings from last validation."""
        return self._warnings.copy()

    def clear_warnings(self) -> None:
        """Clear accumulated warnings."""
        self._warnings = []


class APRVerifier:
    """
    Verify PIB against APR (Serbian Business Registry) database.

    This is a placeholder - actual implementation requires
    APR API credentials and integration.
    """

    def __init__(self, api_url: str | None = None, cache_ttl: int = 86400):
        """
        Initialize APR verifier.

        Args:
            api_url: APR API endpoint
            cache_ttl: Cache TTL in seconds (default 24 hours)
        """
        self.api_url = api_url or "https://api.apr.gov.rs"
        self.cache_ttl = cache_ttl
        self._cache: dict[str, Any] = {}

    async def verify(self, pib: str) -> dict[str, Any]:
        """
        Verify PIB against APR database.

        Args:
            pib: PIB to verify

        Returns:
            Company info if found, empty dict otherwise
        """
        # Check cache first
        if pib in self._cache:
            return self._cache[pib]

        # TODO: Implement actual APR API call
        # This would be:
        # async with httpx.AsyncClient() as client:
        #     response = await client.get(f"{self.api_url}/companies/{pib}")
        #     if response.status_code == 200:
        #         data = response.json()
        #         self._cache[pib] = data
        #         return data

        # Placeholder return
        return {
            "pib": pib,
            "verified": False,
            "status": "not_verified",
            "message": "APR verification not implemented",
        }

    def is_active(self, apr_data: dict[str, Any]) -> bool:
        """Check if company is active based on APR data."""
        status = apr_data.get("status", "").upper()
        return status in ["AKTIVAN", "ACTIVE"]
