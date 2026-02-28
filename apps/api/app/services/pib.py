"""PIB (Poreski Identifikacioni Broj) validation.

Validates Serbian tax identification numbers using format checks
and the mod-11 checksum algorithm used by the Serbian Tax Administration.
"""


def validate_pib(pib: str) -> tuple[bool, str | None]:
    """Validate a Serbian PIB format and mod-11 checksum.

    Args:
        pib: Tax identification number string.

    Returns:
        Tuple of (is_valid, error_message). Error message is None when valid.
    """
    if not pib or not pib.isdigit():
        return False, "PIB mora sadržati samo cifre"

    if len(pib) != 9:
        return False, "PIB mora imati tačno 9 cifara"

    if pib[0] == "0":
        return False, "PIB ne sme počinjati nulom"

    if not _mod11_check(pib):
        return False, "PIB nije validan (kontrolna cifra)"

    return True, None


def _mod11_check(pib: str) -> bool:
    """Verify the ISO 7064 Mod 11,10 checksum for a 9-digit Serbian PIB.

    Algorithm (ISO 7064 Mod 11,10 — recursive):
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
    product = 10
    for i in range(8):
        digit = int(pib[i])
        s = (product + digit) % 10
        if s == 0:
            s = 10
        product = (s * 2) % 11

    check_digit = (11 - product) % 10
    return int(pib[8]) == check_digit
