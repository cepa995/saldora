"""ZZPL compliance service — consent management, deletion, breach notifications."""

from datetime import date, datetime

from app.schemas.compliance import (
    BreachNotificationResponse,
    BreachNotificationTemplate,
)

PRIVACY_POLICY_VERSION = "1.0"
PRIVACY_POLICY_EFFECTIVE_DATE = date(2026, 3, 1)
PRIVACY_POLICY_CONTENT = """
Politika privatnosti — FakturaAI

1. Rukovalac podataka
   Lab42 DOO, Beograd, Republika Srbija.

2. Svrha obrade
   Obrada faktura, OCR ekstrakcija podataka, računovodstvena analitika.

3. Pravni osnov
   Zakon o zaštiti podataka o ličnosti (ZZPL), Zakon o računovodstvu.

4. Kategorije podataka
   - Kontakt podaci (ime, email, telefon)
   - Poslovni podaci (PIB, matični broj, adresa)
   - Podaci sa faktura (iznosi, datumi, stavke)

5. Čuvanje podataka
   - Računi i fakture: 10 godina (Zakon o računovodstvu)
   - Korisnički profili: do brisanja naloga
   - Evidencija revizije: 7 godina
   - Analitički podaci: do opoziva saglasnosti

6. Prava lica
   - Pravo na pristup (Član 26 ZZPL)
   - Pravo na ispravku (Član 29 ZZPL)
   - Pravo na brisanje (Član 30 ZZPL)
   - Pravo na ograničenje obrade (Član 31 ZZPL)
   - Pravo na prenosivost podataka (Član 36 ZZPL)

7. Poverenik
   Zahteve možete uputiti na: privacy@fakturaai.rs

8. Poverenik za informacije od javnog značaja i zaštitu podataka o ličnosti
   Bulevar kralja Aleksandra 15, 11000 Beograd
   https://www.poverenik.rs
""".strip()

# Categories retained during deletion (with legal basis)
RETAINED_CATEGORIES = {
    "invoices": "Zakon o računovodstvu — obavezno čuvanje 10 godina",
    "audit_logs": "ZZPL — evidencija obrade podataka, čuvanje 7 godina",
    "consent_records": "ZZPL — evidencija saglasnosti, čuvanje do isteka roka",
}


def render_breach_notification(
    template: BreachNotificationTemplate,
) -> BreachNotificationResponse:
    """Render a ZZPL-compliant breach notification in Serbian.

    Args:
        template: Breach incident details.

    Returns:
        Rendered notification with subject and body.
    """
    affected = ", ".join(template.affected_data_types)
    subject = (
        f"Obaveštenje o povredi zaštite podataka o ličnosti — "
        f"{template.incident_date.strftime('%d.%m.%Y.')}"
    )
    body = f"""Poštovani,

U skladu sa članom 52 Zakona o zaštiti podataka o ličnosti (ZZPL), \
obaveštavamo vas o sledećem incidentu:

Datum incidenta: {template.incident_date.strftime("%d.%m.%Y.")}

Opis incidenta:
{template.description}

Kategorije ugroženih podataka:
{affected}

Preduzete mere:
{template.measures_taken}

Preporuke za korisnike:
{template.recommendations}

Rok za prijavu Povereniku: 72 sata od saznanja o povredi.

Kontakt za dodatne informacije: privacy@fakturaai.rs

S poštovanjem,
FakturaAI tim"""

    return BreachNotificationResponse(subject=subject, body=body)


def get_deletion_retained_categories() -> dict:
    """Return categories that must be retained during data deletion.

    Returns:
        Dict mapping category name to legal basis in Serbian.
    """
    return RETAINED_CATEGORIES.copy()


def anonymize_user_data(user) -> dict:
    """Anonymize user profile fields for deletion compliance.

    Args:
        user: User model instance to anonymize.

    Returns:
        Dict of old values for audit logging.
    """
    old_values = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
    }
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    user.first_name = "Obrisani"
    user.last_name = "Korisnik"
    user.email = f"deleted_{timestamp}@anonymized.local"
    return old_values
