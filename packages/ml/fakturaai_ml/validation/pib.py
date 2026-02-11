"""PIB (Tax ID) validation for Serbian companies."""

import logging
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

    def validate(self, pib: str) -> bool:
        """
        Validate PIB format using mod-11 algorithm.

        Args:
            pib: PIB string to validate

        Returns:
            True if valid, False otherwise
        """
        self._warnings = []

        # Basic format check
        if not pib or not pib.isdigit():
            self._warnings.append(
                ValidationWarning(
                    warning_type=WarningType.PIB_INVALID_FORMAT,
                    message="PIB mora sadržati samo cifre",
                    field_name="pib",
                    severity="error",
                    blocking=True,
                )
            )
            return False

        if len(pib) != 9:
            self._warnings.append(
                ValidationWarning(
                    warning_type=WarningType.PIB_INVALID_FORMAT,
                    message="PIB mora imati tačno 9 cifara",
                    field_name="pib",
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
                    message="PIB ne može počinjati sa 0",
                    field_name="pib",
                    severity="error",
                    blocking=True,
                )
            )
            return False

        # Mod-11 checksum validation
        if not self._validate_checksum(pib):
            self._warnings.append(
                ValidationWarning(
                    warning_type=WarningType.PIB_INVALID_FORMAT,
                    message="PIB nije validan (kontrolna cifra)",
                    field_name="pib",
                    severity="warning",
                    blocking=False,  # Allow with warning - OCR might have misread
                )
            )
            return False

        return True

    def _validate_checksum(self, pib: str) -> bool:
        """
        Validate PIB using Serbian mod-11 checksum algorithm.

        The algorithm:
        1. Take first 8 digits
        2. Multiply each by weight (starting from 2)
        3. Sum all products
        4. Calculate 11 - (sum mod 11)
        5. If result is 10, use 0; if 11, use 0
        6. Compare with 9th digit
        """
        try:
            digits = [int(d) for d in pib]

            # Calculate weighted sum
            weights = [2, 3, 4, 5, 6, 7, 8, 9]
            weighted_sum = sum(d * w for d, w in zip(digits[:8], weights))

            # Calculate check digit
            remainder = weighted_sum % 11
            check_digit = 11 - remainder

            if check_digit >= 10:
                check_digit = 0

            return digits[8] == check_digit

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
