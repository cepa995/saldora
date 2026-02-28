"""
Unit tests for PIB (Serbian tax ID) validation.

Tests the mod-11 checksum algorithm and format validation
without requiring database or HTTP client.
"""

from app.services.pib import validate_pib

# ---- Valid PIBs ----


def test_valid_pib_known_values():
    """Known valid Serbian PIBs pass validation."""
    # These PIBs satisfy the ISO 7064 Mod 11,10 checksum
    valid_pibs = ["100000016", "100000073", "123456788"]
    for pib in valid_pibs:
        is_valid, err = validate_pib(pib)
        assert is_valid, f"PIB {pib} should be valid, got error: {err}"
        assert err is None


def test_valid_pib_check_digit_zero():
    """PIB where the ISO 7064 Mod 11,10 check digit is 0."""
    is_valid, err = validate_pib("100000090")
    assert is_valid, f"PIB 100000090 should be valid, got error: {err}"


# ---- Invalid PIBs ----


def test_invalid_pib_wrong_length_short():
    """PIB shorter than 9 digits is rejected."""
    is_valid, err = validate_pib("12345678")
    assert not is_valid
    assert "9 cifara" in err


def test_invalid_pib_wrong_length_long():
    """PIB longer than 9 digits is rejected."""
    is_valid, err = validate_pib("1234567890")
    assert not is_valid
    assert "9 cifara" in err


def test_invalid_pib_starts_with_zero():
    """PIB starting with 0 is rejected."""
    is_valid, err = validate_pib("012345678")
    assert not is_valid
    assert "nulom" in err


def test_invalid_pib_non_numeric():
    """PIB containing non-digit characters is rejected."""
    is_valid, err = validate_pib("12345678A")
    assert not is_valid
    assert "cifre" in err


def test_invalid_pib_bad_checksum():
    """PIB with incorrect check digit is rejected."""
    # Take a valid PIB and change the last digit
    is_valid, err = validate_pib("100000017")  # valid is 100000016
    assert not is_valid
    assert "kontrolna cifra" in err


def test_invalid_pib_empty_string():
    """Empty string is rejected."""
    is_valid, err = validate_pib("")
    assert not is_valid


def test_invalid_pib_all_same_digits():
    """PIB of all same digits has invalid checksum."""
    is_valid, _ = validate_pib("111111111")
    # 111111117 is valid by Mod 11,10; 111111111 is not
    assert not is_valid
