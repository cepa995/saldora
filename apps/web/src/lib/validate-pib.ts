/**
 * Validate Serbian PIB (Poreski Identifikacioni Broj).
 *
 * Rules:
 *   - Exactly 9 digits
 *   - Cannot start with 0
 *   - Must pass ISO 7064 Mod 11,10 checksum
 *
 * Returns null if valid, or an i18n error key if invalid.
 */
export function validatePib(pib: string): string | null {
  const cleaned = pib.replace(/[\s\-.\/]/g, '');

  if (!cleaned || !/^\d+$/.test(cleaned)) {
    return 'pibDigitsOnly';
  }

  if (cleaned.length !== 9) {
    return 'pibLength';
  }

  if (cleaned[0] === '0') {
    return 'pibNoLeadingZero';
  }

  // ISO 7064 Mod 11,10 checksum
  let product = 10;
  for (let i = 0; i < 8; i++) {
    let s = (product + parseInt(cleaned[i], 10)) % 10;
    if (s === 0) s = 10;
    product = (s * 2) % 11;
  }
  const checkDigit = (11 - product) % 10;
  if (parseInt(cleaned[8], 10) !== checkDigit) {
    return 'pibInvalidChecksum';
  }

  return null;
}
