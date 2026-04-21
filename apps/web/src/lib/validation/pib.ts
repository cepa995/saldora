/**
 * Serbian PIB validation — mirrors app/services/pib.py.
 *
 * Validates the mod-11 checksum used by the Serbian Tax Administration
 * so we can surface issues inline before the backend 422s.
 */

/**
 * ISO 7064 Mod 11,10 recursive checksum for a 9-digit Serbian PIB.
 */
function mod11Check(pib: string): boolean {
  let product = 10;
  for (let i = 0; i < 8; i++) {
    const digit = Number(pib[i]);
    let s = (product + digit) % 10;
    if (s === 0) s = 10;
    product = (s * 2) % 11;
  }
  const checkDigit = (11 - product) % 10;
  return Number(pib[8]) === checkDigit;
}

export interface PibValidationResult {
  valid: boolean;
  error: string | null;
}

/**
 * Validate a Serbian PIB format and checksum.
 *
 * Returns `{ valid: true, error: null }` when acceptable. Use with
 * inline form UX — do not replace backend enforcement.
 */
export function validateSerbianPib(pib: string): PibValidationResult {
  if (!pib) return { valid: false, error: 'PIB mora biti unet' };
  if (!/^\d+$/.test(pib)) return { valid: false, error: 'PIB mora sadržati samo cifre' };
  if (pib.length !== 9) return { valid: false, error: 'PIB mora imati tačno 9 cifara' };
  if (pib[0] === '0') return { valid: false, error: 'PIB ne sme počinjati nulom' };
  if (!mod11Check(pib)) return { valid: false, error: 'PIB nije validan (kontrolna cifra)' };
  return { valid: true, error: null };
}
