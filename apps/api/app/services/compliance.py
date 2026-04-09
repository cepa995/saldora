"""ZZPL compliance service — consent management, deletion, breach notifications."""

from datetime import date, datetime

from app.schemas.compliance import (
    BreachNotificationResponse,
    BreachNotificationTemplate,
)

PRIVACY_POLICY_VERSION = "2.0"
PRIVACY_POLICY_EFFECTIVE_DATE = date(2026, 4, 1)
PRIVACY_POLICY_CONTENT = """
Politika privatnosti — Saldora

Poslednje ažuriranje: 01.04.2026.

1. Rukovalac podataka
   Lab42 DOO, Beograd, Republika Srbija.
   Kontakt: privacy@saldora.rs

2. O usluzi
   Saldora je platforma za inteligentnu obradu i analizu faktura. Saldora vrši OCR ekstrakciju podataka, računovodstvenu analitiku, izveštavanje i izvoz podataka u računovodstvene sisteme.
   Saldora NIJE servis za trajno čuvanje dokumenata.

3. Pravni osnov obrade
   - Zakon o zaštiti podataka o ličnosti (ZZPL, Sl. glasnik RS, br. 87/2018)
   - Zakon o računovodstvu (Sl. glasnik RS, br. 73/2019)
   - Saglasnost korisnika za analitičke i marketinške svrhe

4. Kategorije podataka koje obrađujemo
   - Kontakt podaci (ime, prezime, email adresa)
   - Poslovni podaci (PIB, matični broj, naziv firme, adresa)
   - Podaci sa faktura (iznosi, datumi, stavke, dobavljači)
   - Tehnički podaci (IP adresa, tip pretraživača, vreme pristupa)

5. Čuvanje podataka
   Saldora čuva podatke tokom trajanja pretplate korisnika.
   - Fakture i dokumenta: tokom trajanja pretplate + 90 dana nakon isteka
   - Korisnički profili: do brisanja naloga
   - Evidencija revizije: tokom trajanja pretplate
   - Nakon isteka pretplate i roka od 90 dana, svi podaci se trajno brišu

   VAŽNO: Korisnik je odgovoran za čuvanje poslovne dokumentacije u skladu sa Zakonom o računovodstvu (10 godina). Saldora pruža automatski mesečni arhivski izvoz kao mehanizam za preuzimanje podataka. Korisnik se obavezuje da redovno preuzima i čuva arhive.

6. Automatski arhivski izvoz
   Saldora automatski generiše mesečni arhivski izvoz koji uključuje registar faktura, PDV pregled, revizorski trag i originalna dokumenta. Izvoz se šalje na email adresu organizacije prvog u mesecu. Korisnik je odgovoran za preuzimanje i sigurno čuvanje arhive.

7. Prava lica u skladu sa ZZPL
   - Pravo na pristup ličnim podacima (Član 26 ZZPL)
   - Pravo na ispravku netačnih podataka (Član 29 ZZPL)
   - Pravo na brisanje podataka (Član 30 ZZPL)
   - Pravo na ograničenje obrade (Član 31 ZZPL)
   - Pravo na prenosivost podataka (Član 36 ZZPL)
   - Pravo na prigovor (Član 37 ZZPL)

   Za ostvarivanje prava obratite se na: privacy@saldora.rs

8. Deljenje podataka
   Saldora ne prodaje niti deli lične podatke sa trećim stranama, osim:
   - Sa pružaocima usluga neophodnih za rad platforme (hosting, email)
   - Kada je to zakonom propisano (sudski nalog, inspekcijski organi)

9. Bezbednost podataka
   Primenjujemo tehničke i organizacione mere zaštite podataka uključujući enkripciju podataka u prenosu i mirovanju, kontrolu pristupa i redovne sigurnosne provere.

10. Poverenik za informacije od javnog značaja i zaštitu podataka o ličnosti
    Ukoliko smatrate da su vam prava povređena, možete se obratiti Povereniku:
    Bulevar kralja Aleksandra 15, 11000 Beograd
    https://www.poverenik.rs

11. Izmene politike
    Zadržavamo pravo da izmenimo ovu politiku privatnosti. O izmenama ćemo korisnika obavestiti putem email-a najmanje 30 dana pre stupanja na snagu.
""".strip()

TOS_VERSION = "1.0"
TOS_EFFECTIVE_DATE = date(2026, 4, 1)
TOS_CONTENT = """
Uslovi korišćenja — Saldora

Poslednje ažuriranje: 01.04.2026.

1. O usluzi

Saldora je platforma za obradu i analizu faktura. Saldora pruža uslugu inteligentne obrade dokumenata — OCR ekstrakciju podataka, računovodstvenu analitiku, izveštavanje i izvoz podataka u računovodstvene sisteme (npr. MiniMax).

Saldora NIJE servis za trajno čuvanje dokumenata niti zamena za računovodstveni softver.

2. Odgovornost za čuvanje podataka

Korisnik je u potpunosti odgovoran za čuvanje svojih poslovnih dokumenata u skladu sa Zakonom o računovodstvu (Sl. glasnik RS, br. 73/2019), koji propisuje obavezu čuvanja računovodstvenih isprava u roku od 10 godina.

Saldora pruža alate za automatski mesečni izvoz arhive (registar faktura, PDV pregled, revizorski trag i originalna dokumenta) koji se šalje na email adresu organizacije. Korisnik se obavezuje da redovno preuzima i čuva ove arhive na sigurnom mestu.

3. Čuvanje podataka na platformi

Saldora čuva korisničke podatke tokom trajanja pretplate. Nakon isteka ili otkazivanja pretplate:
- Podaci se čuvaju još 90 dana radi omogućavanja izvoza
- Nakon 90 dana, svi podaci se trajno brišu
- Korisnik je dužan da izvrši izvoz svih podataka pre isteka ovog roka

Saldora zadržava pravo da obriše podatke nakon isteka roka čuvanja bez posebnog obaveštenja.

4. Automatski arhivski izvoz

Saldora automatski generiše mesečni arhivski izvoz koji uključuje:
- Registar faktura (CSV format)
- PDV pregled po stopama (Excel format)
- Revizorski trag (CSV format)
- Originalna PDF dokumenta

Arhivski izvoz se šalje na email adresu organizacije prvog u mesecu. Link za preuzimanje važi 24 sata. Korisnik je odgovoran za preuzimanje i sigurno čuvanje arhive.

5. Obaveze korisnika

Korisnik se obavezuje da:
- Koristi platformu u skladu sa važećim propisima Republike Srbije
- Obezbedi tačnost podataka koje unosi u sistem
- Redovno preuzima arhivske izvozne i čuva ih u skladu sa Zakonom o računovodstvu
- Čuva pristupne podatke u tajnosti i ne deli ih sa neovlašćenim licima
- Ne koristi platformu za obradu podataka koji krše prava trećih lica

6. Ograničenje odgovornosti

Saldora se trudi da obezbedi tačnost OCR ekstrakcije, ali ne garantuje 100% tačnost automatski ekstrahovanih podataka. Korisnik je odgovoran za verifikaciju podataka pre izvoza u računovodstveni sistem.

Saldora nije odgovorna za:
- Gubitak podataka usled propusta korisnika da izvrši izvoz
- Netačnosti u automatski ekstrahovanih podacima koje korisnik nije verifikovao
- Prekide u radu usled tehničkih problema ili održavanja sistema
- Štetu nastalu usled neovlašćenog pristupa nalogu korisnika

7. Intelektualna svojina

Saldora platforma, uključujući softver, dizajn, algoritme i dokumentaciju, je vlasništvo Lab42 DOO. Korisnik dobija neekskluzivno pravo korišćenja platforme tokom trajanja pretplate.

8. Raskid

Korisnik može da otkaže pretplatu u bilo kom trenutku. Lab42 DOO zadržava pravo da suspenduje ili ukine nalog korisnika u slučaju kršenja ovih uslova.

9. Primena prava

Na ove uslove korišćenja primenjuje se pravo Republike Srbije. Za sve sporove nadležan je sud u Beogradu.

10. Izmene uslova

Lab42 DOO zadržava pravo da izmeni ove uslove korišćenja. O izmenama ćemo korisnika obavestiti putem email-a najmanje 30 dana pre stupanja na snagu.

11. Kontakt

Lab42 DOO
Beograd, Republika Srbija
Email: info@saldora.rs
Web: https://saldora.rs
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

Kontakt za dodatne informacije: privacy@saldora.ai

S poštovanjem,
Saldora tim"""

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
