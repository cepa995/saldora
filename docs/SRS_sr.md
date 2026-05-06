# Specifikacija softverskih zahteva (SRS)
# Saldora — Sloj inteligencije za srpske računovodstvene agencije sa ugostiteljskim klijentima

**Verzija:** 4.0
**Datum:** 2026-04-29
**Status:** Aktivan (post-pivot izvor istine)

---

## Trenutna teza (post-pivot)

Saldora je **sloj inteligencije za srpske računovodstvene agencije čiji su klijenti ugostiteljski objekti** — restorani, kafići, barovi, brze hrane, ketering. Klin je dvostruk:

1. **OCR papirnih faktura sa mnogo stavki** — distributeri pića, suvoroba, sveža hrana, meso, sredstva za čišćenje, održavanje opreme — vrste faktura koje i dalje stižu u papirnoj formi ili kao PDF prilozi e-pošte i koje SEF (eFaktura) ne pokriva i verovatno neće uskoro pokriti.
2. **Generisanje zakonom propisanih ugostiteljskih obrazaca** iz ekstrahovanih stavki — kalkulacije, šank lista, cenovnik, KEP, popis. Danas agencije ovo rade ručno u Excel-u.

Kupac je **vlasnik agencije**; svakodnevni korisnici su **agencijski knjigovođe** koji vode 30–40 ugostiteljskih klijenata, pri čemu svaki klijent generiše 20–40 faktura mesečno. Saldora je pipeline od papirne fakture na ulazu do potpuno klasifikovanih, zakonski tačnih podataka na izlazu, koje predaje **MiniMax-u** (dominantni srpski cloud računovodstveni proizvod) za glavnu knjigu i finansijsko izveštavanje. **Saldora ne zamenjuje MiniMax.** Saldora ne radi bankarsko usaglašavanje, praćenje plaćanja niti knjiženja u glavnu knjigu.

Originalna pozicija ovog dokumenta — generička obrada faktura — je zamenjena ugostiteljskom tezom. Sposobnosti koje su bile generičke (multi-tenant model, OCR + LLM ekstrakcija, izvoz, automatizovana pravila, upravljanje klijentima) i dalje rade i u opsegu su; jednostavno više nisu primarno marketinški ili produktni okvir. Sve što je bilo specifično za paušalce, oblikovano kao generički B2B portal ili nosivo na SEF-u je otpisano ili odloženo (vidi Odeljak 4.17, "Van obima / Otpisano").

Za strateški narativ vidi [`saldora-strategy-and-ux-redesign.md`](saldora-strategy-and-ux-redesign.md). Za status milestoneova vidi [`saldora-implementation-plan.md`](saldora-implementation-plan.md).

---

## Sadržaj

1. [Uvod](#1-uvod)
2. [Opšti opis](#2-opšti-opis)
3. [Arhitektura sistema](#3-arhitektura-sistema)
4. [Funkcionalni zahtevi](#4-funkcionalni-zahtevi)
   - 4.1 [Autentifikacija i autorizacija korisnika](#41-autentifikacija-i-autorizacija-korisnika)
   - 4.9 [Poslovna logika i pravila validacije](#49-poslovna-logika-i-pravila-validacije)
   - 4.10 [Sloj računovodstvene namere](#410-sloj-računovodstvene-namere)
   - 4.11 [Motor za automatizaciju pravila](#411-motor-za-automatizaciju-pravila)
   - 4.12 [Upravljanje klijentima (Agencija)](#412-upravljanje-klijentima-agencija)
   - 4.13 [Izveštaji o fakturama (Izveštaji)](#413-izveštaji-o-fakturama-izveštaji)
   - 4.14 [Email ingestion pipeline (planirano)](#414-email-ingestion-pipeline-planirano)
   - 4.15 [Katalog proizvoda](#415-katalog-proizvoda)
   - 4.16 [Sistem podrške u aplikaciji (planirano)](#416-sistem-podrske-u-aplikaciji-planirano)
   - 4.17 [Van obima / Otpisani moduli](#417-van-obima--otpisani-moduli)
   - 4.18 [Klijent-prvi UI (M19)](#418-klijent-prvi-ui-m19)
   - 4.19 [Ugostiteljski zakonski obrasci (M20, odloženo)](#419-ugostiteljski-zakonski-obrasci-m20-odlozeno)
5. [Nefunkcionalni zahtevi](#5-nefunkcionalni-zahtevi)
6. [Tehnološki stek](#6-tehnološki-stek)
7. [Dizajn baze podataka](#7-dizajn-baze-podataka)
8. [API specifikacija](#8-api-specifikacija)
9. [AI/ML komponente](#9-aiml-komponente)
10. [Bezbednosni zahtevi](#10-bezbednosni-zahtevi)
    - 10.6 [Pravni i regulatorni tokovi](#106-pravni-i-regulatorni-tokovi)
11. [Arhitektura deployovanja](#11-arhitektura-deployovanja)
12. [Integracije sa spoljnim sistemima](#12-integracije-sa-spoljnim-sistemima)
    - 12.5 [SEF integracija (eFaktura)](#125-sef-integracija-efaktura)
13. [Zahtevi korisničkog interfejsa](#13-zahtevi-korisničkog-interfejsa)
14. [Zahtevi testiranja](#14-zahtevi-testiranja)
15. [Dodaci](#15-dodaci)

---

## 1. Uvod

### 1.1 Svrha

Ovaj dokument Specifikacije softverskih zahteva (SRS) je opis-izvor-istine platforme Saldora — sloja inteligencije za srpske računovodstvene agencije koje opslužuju ugostiteljske klijente. Dokument opisuje funkcionalne i nefunkcionalne zahteve, arhitekturu sistema i tehničke specifikacije onako kako proizvod postoji danas (post-pivot, april 2026).

Ovo je živi dokument. Sadržaj koji je opisivao pre-pivot generičku B2B poziciju je ili napisan iznova kako bi odražavao ugostiteljsku tezu ili eksplicitno označen kao zamenjen.

### 1.2 Obim

Saldora je SaaS platforma koja omogućava srpskim računovodstvenim agencijama sa ugostiteljskim portfeljima (restorani, kafići, barovi) da:

- Primaju papirne fakture, fiskalne isečke i PDF priloge e-pošte u velikom obimu
- Automatski ekstrahuju strukturirane podatke (zaglavlja **i** stavke) koristeći vision-language OCR pipeline plus LLM sloj za ekstrakciju
- Obrađuju dokumenta na ćiriličnom i latiničnom pismu
- Normalizuju opise stavki na kanonske identitete proizvoda kroz katalog proizvoda po organizaciji
- Upravljaju klijentima (agencijskim ugostiteljskim subjektima), dodeljuju svaku fakturu jednom klijentu i pregledaju portfelj agencije na prvi pogled
- Primenjuju pravila automatizacije po klijentu i na nivou organizacije (tip dokumenta, PDV tretman, predloženi konto)
- Generišu nabavnu inteligenciju (kalkulacija, RUC, troškovi po kategoriji, dnevna evidencija robe) povrh normalizovanih stavki
- Izvoze strukturirane podatke u MiniMax (XML fajl ili REST API push), XLSX, CSV, JSON
- Generišu mesečne arhive (ZIP sa registrom faktura, PDV pregledom, audit tragom, originalnim PDF-ovima) za retenciju

Namerni ne-ciljevi sistema dokumentovani su u Odeljku 4.17.

### 1.3 Definicije, akronimi i skraćenice

| Termin | Definicija |
|--------|-----------|
| OCR | Optičko prepoznavanje karaktera (Optical Character Recognition) |
| PIB | Poreski identifikacioni broj |
| APR | Agencija za privredne registre |
| PDV | Porez na dodatu vrednost |
| SEF | Sistem elektronskih faktura (eFaktura) |
| Konto | Šifra konta u srpskom kontnom planu |
| MB | Matični broj |
| PPPDV | Poreska prijava PDV |
| KPR | Knjiga primljenih računa |
| KIR | Knjiga izdatih računa |
| ZZPL | Zakon o zaštiti podataka o ličnosti |
| NBS | Narodna banka Srbije |
| SaaS | Softver kao usluga (Software as a Service) |
| JWT | JSON Web Token |
| REST | Representational State Transfer |

### 1.4 Ciljna publika

**Primarno:**
- Računovodstvene agencije čiji portfelji uključuju ugostiteljske klijente (restorani, kafići, barovi, ketering, brza hrana). Kupac = vlasnik agencije; svakodnevni korisnici = agencijski knjigovođe.

**Sekundarno (i dalje podržano, ali više nije primarni pravac):**
- Samostalni računovođe i male/srednje računovodstvene prakse koje vode mešovite portfelje.
- Ugostiteljska MSP koja vode sopstveno knjigovodstvo interno (mali deo tržišta).

**Uklonjeno iz ciljne publike:**
- Paušalci kao persona — paušal modul je vraćen; MiniMax-ov dedikovani paušal proizvod opslužuje taj segment.
- Krajnji klijenti agencija (npr. vlasnik restorana koji direktno koristi Saldoru) — vidi "bez klijent portala" u Odeljku 4.17. Agencija ostaje jedina klasa korisnika.
- Generički enterprise B2B korisnici (velike korporacije sa hiljadama faktura mesečno) — nije klin; ove kompanije primaju većinu faktura preko SEF-a i imaju ustaljene tokove rada.

### 1.5 Konvencije dokumenta

- **MORA** - Obavezan zahtev
- **TREBALO BI** - Preporučen zahtev
- **MOŽE** - Opcioni zahtev

---

## 2. Opšti opis

### 2.1 Perspektiva proizvoda

Saldora funkcioniše kao samostalna veb aplikacija sa sledećim tačkama integracije:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Saldora platforma                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  Veb aplik. │  │  REST API   │  │    AI procesor           │  │
│  │  (Next.js)  │  │  (FastAPI)  │  │    (Python/PyTorch)      │  │
│  └──────┬──────┘  └──────┬──────┘  └────────────┬────────────┘  │
│         │                │                      │                │
│         └────────────────┼──────────────────────┘                │
│                          │                                       │
├──────────────────────────┼───────────────────────────────────────┤
│                    Spoljni servisi                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │  APR API    │  │   Storage   │  │    Platni procesor       │  │
│  │  (Srbija)   │  │   (S3/R2)   │  │    (Paddle)              │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Funkcionalnosti proizvoda (viši nivo)

| Funkcionalnost | Opis | Prioritet |
|----------------|------|-----------|
| Otpremanje faktura | Otpremanje dokumenata u više formata (PDF, JPG, PNG, TIFF) | P0 |
| AI ekstrakcija podataka | Automatska ekstrakcija polja fakture | P0 |
| Podrška za ćirilicu/latinicu | Potpuna podrška za srpska pisma | P0 |
| PIB verifikacija | Verifikacija u realnom vremenu prema APR bazi | P0 |
| Izvoz podataka | Izvoz u Excel, CSV, JSON formate | P0 |
| Grupna obrada | Istovremena obrada više faktura | P1 |
| Upravljanje korisnicima | Višekorisnički nalozi sa kontrolom pristupa na osnovu uloga | P1 |
| Kontrolna tabla i analitika | Statistike korišćenja i istorija obrade | P1 |
| Upravljanje klijentima | Upravljanje klijentima i filtriranje faktura po klijentu (Agency plan) | P1 |
| API pristup | RESTful API za integracije sa trećim sistemima | P2 |
| Prilagođene integracije | Webhookovi i prilagođeni šabloni izvoza | P2 |

### 2.3 Klase korisnika i karakteristike

#### 2.3.1 Vlasnik agencije (kupac)
- Donosi odluku o kupovini i upravlja pretplatom
- Tipična agencija vodi 30–40 ugostiteljskih klijenata (restorani, kafići, barovi)
- Ocenjuje proizvod prema uštedi vremena na knjigovodstvenim poslovima i izveštajima
- Konfiguriše tim, planove, integraciju sa MiniMax-om

#### 2.3.2 Agencijski knjigovođa (svakodnevni korisnik)
- Vodi knjigovodstvo za nekoliko ugostiteljskih klijenata istovremeno
- Svaki klijent generiše 20–40 faktura mesečno (papirnih, PDF priloga e-pošte, povremeno SEF)
- Otprema fakture, verifikuje OCR ekstrakciju, primenjuje pravila, generiše izveštaje (kalkulacija, šank lista, KEP)
- Radi u Klijent-prvi UI-u (vidi 4.18): prelazi između radnih tabli pojedinačnih klijenata
- Zahteva pouzdano izdvajanje stavki, brze masovne tokove i jasne tragove revizije

#### 2.3.3 Sekundarni korisnik — interno knjigovodstvo ugostiteljskog MSP-a
- Mali ugostiteljski subjekti koji rade sopstveno knjigovodstvo
- Manji obim (jedna lokacija, 20–40 faktura mesečno)
- I dalje podržan, ali nije primarni pravac

> **Napomena:** Paušalci, krajnji klijenti agencija (klijent portal) i generički enterprise B2B korisnici **NISU** u opsegu (vidi 1.4 i 4.17).

### 2.4 Okruženje rada

- **Klijentska strana:** Moderni veb pregledači (Chrome 90+, Firefox 88+, Safari 14+, Edge 90+)
- **Serverska strana:** Linux-bazirana cloud infrastruktura
- **Mobilni:** Responzivni dizajn za tableta/mobilne uređaje (otpremanje putem mobilne kamere)

### 2.5 Ograničenja dizajna i implementacije

1. MORA da bude usklađen sa Zakonom o zaštiti podataka o ličnosti (ZZPL) Republike Srbije
2. Podaci MORAJU biti skladišteni u data centrima koji obezbeđuju adekvatan nivo zaštite (EU/EEA ili Srbija)
3. MORA da podržava i ćirilično i latinično pismo
4. Vreme obrade OCR-a NE SME da premaši 10 sekundi po stranici
5. Sistem MORA da podržava istovremenu obradu do 100 dokumenata

### 2.6 Pretpostavke i zavisnosti

**Pretpostavke:**
- Korisnici imaju stabilnu internet konekciju
- Dokumenti faktura su čitljivi (nisu ozbiljno oštećeni ili zamućeni)
- APR ostaje dostupan i zadržava trenutni format podataka

**Zavisnosti:**
- APR za PIB verifikaciju (komercijalnim ugovorom ili putem posrednika)
- Provajder cloud skladišta (AWS S3 ili Cloudflare R2)
- Platni procesor (Paddle) za upravljanje pretplatama

---

## 3. Arhitektura sistema

### 3.1 Arhitektura visokog nivoa

```
┌────────────────────────────────────────────────────────────────────────┐
│                             KLIJENTSKI SLOJ                              │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                     Next.js veb aplikacija                        │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │  │
│  │  │  Stranice  │  │ Komponente │  │   Hookovi  │  │   Store    │  │  │
│  │  │  (App Dir) │  │    (UI)    │  │  (Logika)  │  │  (Zustand) │  │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ HTTPS
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                              API SLOJ                                    │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    FastAPI aplikacija                              │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │  │
│  │  │  Ruteri    │  │   Auth     │  │ Middleware │  │ Validatori │  │  │
│  │  │ (Endpointi)│  │   (JWT)    │  │  (CORS)    │  │ (Pydantic) │  │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
┌──────────────────────┐ ┌──────────────────┐ ┌──────────────────────┐
│   AI OBRADA           │ │    BAZA PODATAKA │ │   SKLADIŠTE FAJLOVA  │
│  ┌────────────────┐  │ │  ┌────────────┐  │ │  ┌────────────────┐  │
│  │ vLLM Server   │  │ │  │ PostgreSQL │  │ │  │   S3/R2        │  │
│  │ - dots.ocr VLM│  │ │  │            │  │ │  │   Kompatibilan │  │
│  │ (GPU sidecar) │  │ │  └────────────┘  │ │  └────────────────┘  │
│  └────────────────┘  │ │  ┌────────────┐  │ └──────────────────────┘
│  ┌────────────────┐  │ │  │   Redis    │  │
│  │ OCR Radnik     │  │ │  │  (Keš)     │  │
│  │(Celery+OpenAI) │  │ │  └────────────┘  │
│  └────────────────┘  │ └──────────────────┘
└──────────────────────┘
```

### 3.2 Dijagram komponenti

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Frontend komponente                           │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐  │
│  │   Auth      │    │  Kontrolna  │    │    Obrada faktura       │  │
│  │  - Prijava  │    │   tabla     │    │    - Otpremanje         │  │
│  │  - Registr. │    │  - Statist. │    │    - Pregled            │  │
│  │  - Reset    │    │  - Istorija │    │    - Izmena              │  │
│  └─────────────┘    └─────────────┘    │    - Izvoz              │  │
│                                         └─────────────────────────┘  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐  │
│  │ Podešavanja │    │  Naplata    │    │    Deljene komponente   │  │
│  │  - Profil   │    │  - Planovi  │    │    - Navigacija         │  │
│  │  - API klj. │    │  - Koriš.   │    │    - Forme              │  │
│  │  - Tim      │    │  - Fakture  │    │    - Tabele             │  │
│  └─────────────┘    └─────────────┘    └─────────────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                        Backend servisi                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │  Auth servis    │    │ Servis faktura  │    │  Servis izvoza  │  │
│  │  - JWT tokeni   │    │ - CRUD operac.  │    │  - XLSX gen.    │  │
│  │  - OAuth        │    │ - Pretraga      │    │  - CSV gen.     │  │
│  │  - Sesije       │    │ - Filtriranje   │    │  - JSON gen.    │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│                                                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │  OCR servis     │    │  APR servis     │    │ Servis skladišta│  │
│  │  - Preprocessing│    │ - PIB pretraga  │    │  - Otpremanje   │  │
│  │  - Ekstrakcija  │    │ - Info o firmi  │    │  - Preuzimanje  │  │
│  │  - Parsiranje   │    │ - Keširanje     │    │  - Brisanje     │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│                                                                      │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐  │
│  │ Servis naplate  │    │ Servis redova   │    │ Webhook servis  │  │
│  │  - Paddle int.  │    │ - Celery zadat. │    │  - Obaveštenja  │  │
│  │  - Praćenje kor.│    │ - Status posla  │    │  - Callback     │  │
│  │  - Fakturisanje │    │ - Retry logika  │    │  - Događaji     │  │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘  │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.3 Dijagram toka podataka

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Korisnik │     │  Servis  │     │   OCR    │     │Ekstrakcija│
│ otprema  │────▶│otpremanja│────▶│  engine  │────▶│  polja   │
│ fakturu  │     │          │     │          │     │          │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
                                                         │
                                                         ▼
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Izvoz   │     │ Korisnik │     │   PIB    │     │   NER    │
│ podataka │◀────│ pregled  │◀────│verifikac.│◀────│  model   │
│          │     │ i izmena │     │  (APR)   │     │          │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
```

---

## 4. Funkcionalni zahtevi

### 4.1 Autentifikacija i autorizacija korisnika

#### FZ-4.1.1 Registracija korisnika
| ID | FZ-4.1.1 |
|----|----------|
| **Opis** | Sistem MORA da omogući registraciju korisnika putem e-pošte i lozinke |
| **Ulaz** | E-pošta, lozinka, naziv firme (opciono) |
| **Izlaz** | Kreiran korisnički nalog, poslat verifikacioni e-mail |
| **Validacija** | Format e-pošte, jačina lozinke (min 8 karaktera, 1 veliko slovo, 1 broj) |

#### FZ-4.1.2 Prijava korisnika
| ID | FZ-4.1.2 |
|----|----------|
| **Opis** | Sistem MORA da autentifikuje korisnike putem e-pošte/lozinke ili OAuth |
| **Ulaz** | E-pošta, lozinka ILI OAuth token |
| **Izlaz** | JWT pristupni token, refresh token |
| **Sesija** | Pristupni token ističe za 1 sat, refresh token za 7 dana |

#### FZ-4.1.3 Resetovanje lozinke
| ID | FZ-4.1.3 |
|----|----------|
| **Opis** | Sistem MORA da omogući resetovanje lozinke putem e-pošte |
| **Tok** | Zahtev za reset → E-mail sa linkom → Forma za novu lozinku → Potvrda |

#### FZ-4.1.4 Kontrola pristupa zasnovana na ulogama
| ID | FZ-4.1.4 |
|----|----------|
| **Opis** | Sistem MORA da podržava više korisničkih uloga |
| **Uloge** | Admin, Menadžer, Operater, Čitalac |

| Uloga | Dozvole |
|-------|---------|
| Admin | Potpuni pristup, naplata, upravljanje timom |
| Menadžer | Obrada faktura, izvoz, pregled tima |
| Operater | Obrada faktura, izvoz |
| Čitalac | Pristup za čitanje obrađenih faktura |

#### FR-4.1.5 Ručno odobrenje naloga (registracija → pristup)

| ID | FR-4.1.5 |
|----|----------|
| **Opis** | Nove organizacije MORAJU da slete u `subscription_status = 'pending'` i ne smeju da pristupaju funkcionalnim endpointima dok admin ručno ne odobri nalog |
| **Sprovođenje** | Deljena `require_role(...)` zavisnost vraća 403 sa telom `{"code": "subscription_pending_approval", "subscription_status": "pending"}` kad god korisnik pripada organizaciji čiji je `subscription_status` jednak `pending` |
| **Frontend** | Korisnici sa pending statusom se rutiraju na `/awaiting-approval`, koji povlači user info svakih ~10 sekundi; čim se status promeni u `active` ili `trial`, AuthContext se osvežava i korisnik prelazi u aplikaciju |
| **Admin obaveštenje** | Pri registraciji, Resend e-mail se šalje na adresu iz `ADMIN_EMAIL` sa nazivom organizacije, slug-om, kontaktom i e-mailom registranta |
| **Mehanizam odobrenja** | Interaktivni skript `scripts/admin_orgs.py` (pokreće Saldora osoblje preko SSH-a) lista organizacije na čekanju i dozvoljava operateru da promeni `subscription_status` u `active` ili `trial` i izabere tier plana. U ovoj fazi kompanije nema koraka sa karticom na fajlu; naplata se obrađuje vanlinijski preko Paddle-a kada organizacija postane aktivna. |
| **Razlog** | Pre faze prihoda, svaka registracija se ručno proverava da bi se izbegle zloupotrebe i zadržao fokus na agencijskim kupcima. Ovo je namerno ručno dok se self-serve onboarding ne poveže sa Paddle Checkout-om. |

**Dozvoljene vrednosti `subscription_status`:**

| Vrednost | Značenje |
|----------|----------|
| `pending` | Novoregistrovana organizacija na čekanju admin odobrenja (default za nove registracije) |
| `trial` | Odobrena, aktivna u trial periodu |
| `active` | Odobrena, plaća ili je u evaluaciji |
| `canceled` | Pretplata otkazana od strane korisnika/admina; pristup obično ukinut na kraju perioda |
| `expired` | Trial završen bez konverzije ili pretplata istekla |
| `NULL` | Legacy vrednost za organizacije kreirane pre nego što je kolona postojala; gating logika je tretira kao `active` i backfilluje pri pristupu |

#### FR-4.1.6 Pozivnice za tim i zahtevi za pristup

| ID | FR-4.1.6 |
|----|----------|
| **Opis** | Admini MORAJU moći da pozovu članove tima preko e-maila; pozvani prihvata preko tokenizovanog linka |
| **Modeli** | `invitations` (admin → e-mail, uloga, token, expires_at), `join_requests` (korisnik traži pristup poznatoj organizaciji preko e-mail podudaranja, zahteva odobrenje) |
| **Limiti** | Plan-definisana ograničenja broja sedišta |

### 4.2 Otpremanje i upravljanje fakturama

#### FZ-4.2.1 Otpremanje pojedinačne fakture
| ID | FZ-4.2.1 |
|----|----------|
| **Opis** | Sistem MORA da omogući otpremanje pojedinačnog fajla fakture |
| **Podržani formati** | PDF, JPEG, PNG, TIFF, BMP, WEBP |
| **Maksimalna veličina** | 20 MB po fajlu |
| **Validacija** | Tip fajla, veličina fajla, provera kvaliteta slike |

#### FZ-4.2.2 Grupno otpremanje
| ID | FZ-4.2.2 |
|----|----------|
| **Opis** | Sistem MORA da omogući otpremanje više faktura |
| **Maks. fajlova** | 50 fajlova po grupi |
| **Maks. ukupna veličina** | 200 MB po grupi |
| **Napredak** | Indikator napretka otpremanja u realnom vremenu |

#### FZ-4.2.3 Otpremanje prevlačenjem (Drag & Drop)
| ID | FZ-4.2.3 |
|----|----------|
| **Opis** | Sistem TREBALO BI da podržava otpremanje fajlova prevlačenjem |
| **Povratna info** | Vizuelna indikacija zone za otpremanje, povratna informacija o validaciji |

#### FZ-4.2.4 Otpremanje putem mobilne kamere
| ID | FZ-4.2.4 |
|----|----------|
| **Opis** | Sistem TREBALO BI da omogući direktno snimanje kamerom na mobilnom uređaju |
| **Funkcionalnosti** | Auto-isecanje, predlog korekcije perspektive |

### 4.3 Ekstrakcija podataka pomoću AI

#### FZ-4.3.1 OCR obrada
| ID | FZ-4.3.1 |
|----|----------|
| **Opis** | Sistem MORA da ekstrahuje tekst iz otpremljenih dokumenata |
| **Pisma** | Potpuna podrška za ćirilično i latinično pismo |
| **Tačnost** | Minimum 95% tačnost karaktera na čitljivim dokumentima |
| **Jezici** | Srpski (primarni), engleski (sekundarni) |

#### FZ-4.3.2 Ekstrakcija polja
| ID | FZ-4.3.2 |
|----|----------|
| **Opis** | Sistem MORA da ekstrahuje strukturirana polja fakture |

**Obavezna polja:**

| Polje | Opis | Validacija |
|-------|------|-----------|
| invoice_number | Jedinstveni identifikator fakture | Alfanumerički |
| invoice_date | Datum izdavanja fakture | Validan format datuma |
| due_date | Datum dospeća plaćanja | Validan datum, >= invoice_date |
| seller_name | Naziv firme prodavca | Neprazan string |
| seller_pib | PIB prodavca | 9 cifara |
| seller_address | Adresa prodavca | Neprazan string |
| buyer_name | Naziv firme kupca | Neprazan string |
| buyer_pib | PIB kupca | 9 cifara |
| buyer_address | Adresa kupca | Neprazan string |
| subtotal | Iznos pre poreza | Decimalni broj |
| tax_rate | Primenjena stopa PDV-a | 0%, 10% ili 20% |
| tax_amount | Izračunati porez | Decimalni broj |
| total_amount | Ukupan iznos sa porezom | Decimalni broj |
| currency | Kod valute | RSD, EUR, USD |
| line_items | Pojedinačne stavke/usluge | Niz stavki |

**Polja stavki:**

| Polje | Opis |
|-------|------|
| description | Opis stavke/usluge |
| quantity | Količina |
| unit_price | Cena po jedinici |
| discount | Rabat (%), npr. 7.00 za 7% (može biti null) |
| tax_base | Poreska osnovica — iznos posle rabata, pre PDV-a (može biti null) |
| total | Ukupno za stavku |
| tax_rate | Stopa PDV-a za stavku |
| tax_amount | Iznos PDV-a za stavku (može biti null) |

#### FZ-4.3.3 Ocena pouzdanosti
| ID | FZ-4.3.3 |
|----|----------|
| **Opis** | Sistem MORA da pruži ocene pouzdanosti za ekstraktovana polja |
| **Skala** | 0-100% pouzdanost |
| **Prag** | Polja ispod 80% pouzdanosti se označavaju za manuelni pregled |
| **Prikaz** | Tekstualne oznake umesto procenata: "Pouzdano" (zeleno, ≥75%), "Proveriti" (žuto, 50-74%), "Nepouzdano" (crveno, <50%) |

#### FZ-4.3.4 Podrška za višestranična dokumenta
| ID | FZ-4.3.4 |
|----|----------|
| **Opis** | Sistem MORA da obrađuje fakture sa više stranica |
| **Detekcija** | Automatska detekcija nastavka fakture |
| **Spajanje** | Kombinovanje podataka sa više stranica u jedan zapis |

### 4.4 Verifikacija podataka

#### FZ-4.4.1 PIB verifikacija
| ID | FZ-4.4.1 |
|----|----------|
| **Opis** | Sistem MORA da verifikuje PIB brojeve prema APR bazi podataka |
| **Preuzeti podaci** | Naziv firme, adresa, status, datum registracije |
| **Keširanje** | Keširanje APR odgovora na 24 sata |
| **Nedostupnost** | Prikaz upozorenja ako je APR nedostupan, omogućavanje manuelnog unosa |

**Napomena:** APR ne pruža besplatan javni API. Pristup podacima zahteva komercijalni ugovor sa APR-om ili korišćenje licenciranog posrednika (npr. DataCentric, Bisnode/Dun & Bradstreet). Sistem MORA biti dizajniran tako da podržava zamenu APR provajdera bez značajnih izmena koda.

#### FZ-4.4.2 Matematička verifikacija
| ID | FZ-4.4.2 |
|----|----------|
| **Opis** | Sistem MORA da verifikuje proračune fakture |
| **Provere** | Osnovica + PDV = Ukupno, Zbir stavki = Osnovica |
| **Tolerancija** | Dozvoljena razlika zaokruživanja 0,01 RSD |

#### FZ-4.4.3 Detekcija duplikata
| ID | FZ-4.4.3 |
|----|----------|
| **Opis** | Sistem TREBALO BI da detektuje duplirane fakture |
| **Kriterijumi** | Isti broj fakture + PIB prodavca + datum |
| **Akcija** | Upozorenje, opcija za preskakanje ili obradu |

### 4.5 Pregled i izmena podataka

#### FZ-4.5.1 Uporedni prikaz
| ID | FZ-4.5.1 |
|----|----------|
| **Opis** | Sistem MORA da prikaže originalni dokument pored ekstraktovanih podataka |
| **Funkcije** | Zumiranje, pomeranje, rotacija prikaza dokumenta |
| **Isticanje** | Klik na polje ističe odgovarajuću oblast u dokumentu |

#### FZ-4.5.2 Izmena u liniji
| ID | FZ-4.5.2 |
|----|----------|
| **Opis** | Sistem MORA da omogući izmenu ekstraktovanih polja |
| **Validacija** | Validacija u realnom vremenu pri izmeni |
| **Istorija** | Praćenje izmena sa vremenskim oznakama |

#### FZ-4.5.3 Grupna izmena
| ID | FZ-4.5.3 |
|----|----------|
| **Opis** | Sistem TREBALO BI da omogući grupnu izmenu na više faktura |
| **Slučaj korišćenja** | Ispravljanje čestih grešaka ekstrakcije u grupi |

### 4.6 Izvoz podataka

#### FZ-4.6.1 Excel izvoz (XLSX)
| ID | FZ-4.6.1 |
|----|----------|
| **Opis** | Sistem MORA da izveze podatke u Excel format |
| **Funkcije** | Formatirani zaglavlja, validacija podataka, više listova |
| **Šabloni** | Podrška za prilagođene šablone izvoza |

#### FZ-4.6.2 CSV izvoz
| ID | FZ-4.6.2 |
|----|----------|
| **Opis** | Sistem MORA da izveze podatke u CSV format |
| **Kodiranje** | UTF-8 sa BOM za Excel kompatibilnost |
| **Delimiter** | Podesiv (zarez, tačka-zarez, tab) |

#### FZ-4.6.3 JSON izvoz
| ID | FZ-4.6.3 |
|----|----------|
| **Opis** | Sistem MORA da izveze podatke u JSON format |
| **Struktura** | Podesiva (ravna ili ugnežđena) |
| **Slučaj korišćenja** | API integracija, razmena podataka |

#### FZ-4.6.4 Prilagođeni šabloni izvoza
| ID | FZ-4.6.4 |
|----|----------|
| **Opis** | Sistem TREBALO BI da podržava prilagođeno mapiranje polja izvoza |
| **Funkcije** | Selekcija polja, redosled, preimenovanje, formatiranje |

#### FZ-4.6.5 MiniMax XML izvoz
| ID | FZ-4.6.5 |
|----|----------|
| **Opis** | Sistem MORA da izveze podatke u MiniMax-kompatibilan XML format |
| **Format** | XML po MiniMax import šemi (Stranke + Temeljnice) |
| **Sadržaj** | Deduplicirani partneri po PIB-u, nalozi za knjiženje iz accounting_intent |
| **Slučaj korišćenja** | Uvoz u MiniMax računovodstveni softver (minimax.rs) |

#### FZ-4.6.6 MiniMax REST API slanje
| ID | FZ-4.6.6 |
|----|----------|
| **Opis** | Sistem TREBALO BI da podrži direktno slanje faktura u MiniMax putem REST API-ja |
| **Autentifikacija** | OAuth 2.0 (client_id, client_secret, korisničko ime, lozinka) |
| **Funkcije** | Slanje primljenih faktura, pronalaženje/kreiranje kupaca po PIB-u, pretraga valuta |
| **Konfiguracija** | Kredencijali po organizaciji i MiniMax org ID |

#### FZ-4.6.7 Korisnički interfejs za izvoz
| ID | FZ-4.6.7 |
|----|----------|
| **Opis** | Sistem MORA da obezbedi dijalog za izbor formata i opcija izvoza |
| **Pokretanje** | Grupni izvoz sa liste faktura (višestruki izbor) ili pojedinačni izvoz sa detalja fakture |
| **Formati** | XLSX, CSV, JSON, MiniMax XML — svaki sa specifičnim opcijama |
| **Obrada grešaka** | Prikaz blokiranih faktura sa razlozima kada je izvoz odbijen (422) |

### 4.7 Kontrolna tabla i analitika

#### FZ-4.7.1 Statistike obrade
| ID | FZ-4.7.1 |
|----|----------|
| **Opis** | Sistem MORA da prikaže statistike obrade |
| **Metrike** | Ukupno obrađeno, stopa uspešnosti, prosečno vreme obrade |
| **Period** | Dnevno, nedeljno, mesečno, prilagođeni opseg |

#### FZ-4.7.2 Praćenje korišćenja
| ID | FZ-4.7.2 |
|----|----------|
| **Opis** | Sistem MORA da prati korišćenje u odnosu na limite pretplate |
| **Prikaz** | Trenutno korišćenje, preostala kvota, istorija korišćenja |
| **Upozorenja** | Obaveštenje na 80%, 90%, 100% limita |

#### FZ-4.7.3 Istorija obrade
| ID | FZ-4.7.3 |
|----|----------|
| **Opis** | Sistem MORA da održava pretražljivu istoriju obrade |
| **Pretraga** | Po datumu, broju fakture, prodavcu/kupcu, iznosu |
| **Čuvanje** | Minimum 10 godina (prema Zakonu o računovodstvu) |

### 4.8 API pristup

#### FZ-4.8.1 REST API
| ID | FZ-4.8.1 |
|----|----------|
| **Opis** | Sistem MORA da pruži REST API za programski pristup |
| **Autentifikacija** | API ključ ili OAuth 2.0 |
| **Ograničenje stope** | Na osnovu nivoa pretplate |

#### FZ-4.8.2 Webhook obaveštenja
| ID | FZ-4.8.2 |
|----|----------|
| **Opis** | Sistem TREBALO BI da podržava webhook povratne pozive |
| **Događaji** | Obrada završena, greška, izvoz spreman |
| **Ponovni pokušaj** | 3 pokušaja sa eksponencijalnim odlaganjem |

### 4.9 Poslovna logika i pravila validacije

Ovaj odeljak definiše eksplicitna pravila odlučivanja za obradu faktura, određujući kada automatski odobriti, označiti za pregled ili blokirati izvoz.

#### 4.9.1 Pravila validacije PIB-a

| Scenario | APR odgovor | Akcija | Obaveštenje korisniku |
|----------|-------------|--------|-----------------------|
| Validan PIB, aktivna firma | Status: "AKTIVAN" | ✅ Automatski odobri | Zelena kvačica, naziv firme prikazan |
| Validan PIB, neaktivna firma | Status: "BRISAN" / "U LIKVIDACIJI" | ⚠️ Označi za pregled | Upozorenje: "Firma nije aktivna u APR" |
| Validan PIB, firma u stečaju | Status: "STEČAJ" | ⚠️ Označi za pregled | Upozorenje: "Firma u stečaju" |
| Nevažeći format PIB-a | N/A (provera formata) | 🚫 Blokiraj izvoz | Greška: "PIB mora imati 9 cifara" |
| PIB nije pronađen u APR | 404 odgovor | ⚠️ Označi za pregled | Upozorenje: "PIB nije pronađen u APR bazi" |
| APR servis nedostupan | Timeout/5xx | ⚠️ Dozvoli sa upozorenjem | Upozorenje: "APR verifikacija nedostupna" |

**Matrica odlučivanja:**
```
PIB_FORMAT_VALIDAN(pib):
  - MORA biti tačno 9 cifara
  - NE SME počinjati sa 0
  - TREBALO BI da prođe mod-11 kontrolni zbir (algoritam srpskog PIB-a)

PIB_ISHOD_VALIDACIJE(pib) → { AUTOMATSKI_ODOBRI, PREGLED, BLOKIRAJ }:
  AKO NIJE PIB_FORMAT_VALIDAN(pib) → BLOKIRAJ
  AKO APR_NEDOSTUPAN → PREGLED (dozvoli manuelno premošćavanje)
  AKO APR.status == "AKTIVAN" → AUTOMATSKI_ODOBRI
  AKO APR.status U ["BRISAN", "U LIKVIDACIJI", "STEČAJ"] → PREGLED
  AKO APR.status == "NIJE_PRONAĐEN" → PREGLED
```

#### 4.9.2 Validacija istog prodavca/kupca

| Scenario | Akcija | Obrazloženje |
|----------|--------|-------------|
| seller_pib == buyer_pib | ⚠️ Označi za pregled | Može biti validno (interni transfer) ili OCR greška |
| Isti naziv firme, različiti PIB | ⚠️ Označi za pregled | Moguća OCR greška u čitanju PIB-a |
| Prodavac == Kupac potvrdio korisnik | ✅ Dozvoli izvoz | Korisnik eksplicitno potvrdio interni transfer |

**Logika odlučivanja:**
```
PROVERA_ISTE_STRANE(prodavac, kupac):
  AKO prodavac.pib == kupac.pib:
    OZNACI_ZA_PREGLED("Prodavac i kupac imaju isti PIB")
    ZAHTEVAJ_POTVRDU("Da li je ovo interni transfer?")

  AKO sličnost(prodavac.naziv, kupac.naziv) > 0.85 I prodavac.pib != kupac.pib:
    OZNACI_ZA_PREGLED("Slična imena, različiti PIB-ovi")
```

#### 4.9.3 Validacija stope PDV-a

| Ekstraktovana stopa | Validne stope | Akcija |
|----------------------|---------------|--------|
| 0%, 10%, 20% | Standardne srpske stope | ✅ Automatski odobri |
| Druga vrednost (npr. 17%, 25%) | Nevažeća za Srbiju | ⚠️ Označi za pregled |
| Nedostaje/nejasno | N/A | ⚠️ Označi za pregled, predloži 20% |

**Obrada fakture sa više stopa:**
```
VALIDIRAJ_STOPE_PDV(stavke):
  validne_stope = [0, 10, 20]

  ZA SVAKU stavku U stavke:
    AKO stavka.poreska_stopa NIJE U validne_stope:
      OZNACI_ZA_PREGLED(f"Nepoznata stopa PDV: {stavka.poreska_stopa}%")

  # Izračunaj očekivane ukupne iznose po stopi
  ukupno_po_stopi = GRUPIŠI_PO(stavke, poreska_stopa)
  ZA stopa, stavke U ukupno_po_stopi:
    očekivani_pdv = ZBIR(stavke.osnovica) * stopa / 100
    AKO ABS(očekivani_pdv - stavke.iznos_pdv) > TOLERANCIJA:
      OZNACI_ZA_PREGLED("Neslaganje u obračunu PDV-a")
```

#### 4.9.4 Obrada valuta

| Scenario | Akcija | Konverzija |
|----------|--------|------------|
| RSD (srpski dinar) | ✅ Podrazumevano | N/A |
| EUR detektovan | ✅ Prihvati, sačuvaj original | Opciono: prikaži RSD ekvivalent po kursu NBS |
| USD detektovan | ✅ Prihvati, sačuvaj original | Opciono: prikaži RSD ekvivalent po kursu NBS |
| Mešovite valute u stavkama | 🚫 Blokiraj izvoz | Greška: "Mešovite valute" |
| Simbol valute nejasan | ⚠️ Označi za pregled | Pitaj korisnika za potvrdu |

**Pravila detekcije valuta:**
```
DETEKTUJ_VALUTU(tekst):
  obrasci = {
    "RSD": [r"RSD", r"дин", r"din", r"динара"],
    "EUR": [r"EUR", r"€", r"евра", r"evra"],
    "USD": [r"USD", r"\$", r"долара", r"dolara"]
  }

  AKO detektovano_više_valuta:
    OZNACI_ZA_PREGLED("Detektovane različite valute")
```

**Napomena:** Za konverziju stranih valuta u RSD, sistem TREBALO BI da koristi srednji kurs Narodne banke Srbije (NBS) na dan fakture. Kursna lista NBS-a se ažurira dnevno i dostupna je putem javnog API-ja NBS-a.

#### 4.9.5 Matematička verifikacija i zaokruživanje

**Pravila tolerancije:**
| Opseg iznosa | Prihvatljiva razlika | Akcija ako prekorači |
|-------------|----------------------|---------------------|
| 0 - 10.000 RSD | ±1 RSD | ⚠️ Označi za pregled |
| 10.001 - 100.000 RSD | ±5 RSD | ⚠️ Označi za pregled |
| 100.001 - 1.000.000 RSD | ±10 RSD | ⚠️ Označi za pregled |
| > 1.000.000 RSD | ±50 RSD | ⚠️ Označi za pregled |

**Provere verifikacije:**
```
VERIFIKUJ_PRORAČUNE(faktura):
  # Provera 1: Zbir stavki = osnovica
  izračunata_osnovica = ZBIR(stavke.ukupno)
  AKO ABS(izračunata_osnovica - faktura.osnovica) > TOLERANCIJA:
    OZNAČI("Stavke se ne slažu sa međuzbirom")

  # Provera 2: Obračun PDV-a
  očekivani_pdv = faktura.osnovica * faktura.poreska_stopa / 100
  AKO ABS(očekivani_pdv - faktura.iznos_pdv) > TOLERANCIJA:
    OZNAČI("Obračun PDV-a nije tačan")

  # Provera 3: Ukupno = Osnovica + PDV
  očekivani_ukupno = faktura.osnovica + faktura.iznos_pdv
  AKO ABS(očekivani_ukupno - faktura.ukupan_iznos) > TOLERANCIJA:
    OZNAČI("Zbir nije tačan")

  # Provera 4: Matematika stavki
  ZA SVAKU stavku U stavke:
    očekivano = stavka.količina * stavka.jedinična_cena
    AKO ABS(očekivano - stavka.ukupno) > 1:  # 1 RSD tolerancija po stavci
      OZNAČI(f"Greška u stavci: {stavka.opis}")
```

#### 4.9.6 Validacija datuma

| Scenario | Akcija |
|----------|--------|
| Datum fakture u budućnosti | ⚠️ Označi za pregled |
| Datum dospeća pre datuma fakture | ⚠️ Označi za pregled |
| Datum fakture stariji od 1 godine | ⚠️ Upozorenje (dozvoljeno) |
| Nečitljiv format datuma | ⚠️ Označi za pregled |

#### 4.9.7 Pravila blokiranja izvoza

**Faktura NE SME biti izvezena ako:**
1. Format PIB-a je nevažeći (ni prodavca ni kupca)
2. Obavezna polja nedostaju: invoice_number, invoice_date, seller_pib, total_amount
3. Matematička verifikacija ne prolazi izvan tolerancije
4. Korisnik nije pregledao označena upozorenja
5. Ocena pouzdanosti < 60% i nije manuelno verifikovano

**Izvoz dozvoljen sa upozorenjima ako:**
1. APR verifikacija nije uspela (servis nedostupan)
2. Ocena pouzdanosti između 60-80%
3. Nekritično polje nedostaje (npr. adresa kupca)
### 4.10 Sloj računovodstvene namere (AccountingIntent)

Ovaj odeljak definiše **AccountingIntent** - kritičan domenski model koji se nalazi između sirove ekstrakcije fakture i izvoza u računovodstveni sistem. Ovo transformiše Saldoru iz "OCR alata" u "platformu za računovodstvenu inteligenciju".

#### 4.10.1 Pregled

Sloj AccountingIntent premošćava jaz između ekstraktovanih podataka fakture i računovodstvene semantike:

```
┌──────────────┐    ┌──────────────────┐    ┌───────────────────┐    ┌─────────────┐
│   Otpremanje │    │   Ekstraktovani  │    │   Računovodstvena │    │   Izvoz     │
│   dokumenta  │───▶│   podaci fakture │───▶│   namera           │───▶│   (Konta,   │
│              │    │   (OCR + NER)    │    │   (Semantika)      │    │   PDV, ERP) │
└──────────────┘    └──────────────────┘    └───────────────────┘    └─────────────┘
                                                     │
                                                     │ Uključuje:
                                                     │ • Klasifikaciju dokumenta
                                                     │ • Odluku o PDV tretmanu
                                                     │ • Predložena konta
                                                     │ • Mapiranje PDV knjiga
                                                     │ • Tip transakcije
```

#### 4.10.2 AccountingIntent model podataka

| Polje | Tip | Opis | Obavezno |
|-------|-----|------|----------|
| id | UUID | Jedinstveni identifikator | Da |
| invoice_id | UUID | Referenca na izvornu fakturu | Da |
| document_type | Enum | Klasifikacija dokumenta | Da |
| transaction_type | Enum | Priroda transakcije | Da |
| vat_treatment | Enum | Način obrade PDV-a | Da |
| vat_breakdown | JSON | Iznosi PDV-a po stopi | Da |
| suggested_konta | JSON | Predložene šifre konta | Da |
| pdv_book_entries | JSON | Mapiranja polja PDV-PP | Da |
| is_deductible | Boolean | Indikator odbitnosti PDV-a | Da |
| confidence | Decimal | AI pouzdanost u klasifikaciju | Da |
| requires_review | Boolean | Potrebna ljudska verifikacija | Da |
| reviewed_by | UUID | Korisnik koji je verifikovao (ako je pregledano) | Ne |
| reviewed_at | Timestamp | Kada je verifikovano | Ne |
| notes | Text | Napomene računovođe | Ne |

**Tipovi dokumenata:**

| Vrednost | Srpski | Opis |
|----------|--------|------|
| `INPUT_INVOICE` | Ulazna faktura | Faktura primljena od dobavljača |
| `OUTPUT_INVOICE` | Izlazna faktura | Faktura izdata kupcu |
| `CREDIT_NOTE_IN` | Knjižno odobrenje (primljeno) | Primljeno knjižno odobrenje |
| `CREDIT_NOTE_OUT` | Knjižno odobrenje (izdato) | Izdato knjižno odobrenje |
| `DEBIT_NOTE_IN` | Knjižno zaduženje (primljeno) | Primljeno knjižno zaduženje |
| `DEBIT_NOTE_OUT` | Knjižno zaduženje (izdato) | Izdato knjižno zaduženje |
| `ADVANCE_INVOICE` | Avansna faktura | Faktura za avansno plaćanje |
| `FINAL_INVOICE` | Konačna faktura | Konačna faktura (posle avansa) |
| `PROFORMA` | Profaktura | Profaktura (ne knjižiti) |

**Tipovi transakcija:**

| Vrednost | Srpski | Implikacija za PDV |
|----------|--------|-------------------|
| `DOMESTIC` | Domaći promet | Primenjuje se standardni srpski PDV |
| `FOREIGN_EU` | Uvoz/Izvoz EU | EU PDV pravila, potencijalni obrnuti obračun |
| `FOREIGN_NON_EU` | Uvoz/Izvoz van EU | Uvozni PDV ili nulta stopa za izvoz |
| `REVERSE_CHARGE` | Obrnuta naplata | Kupac obračunava PDV |
| `EXEMPT` | Oslobođeno PDV | Transakcija oslobođena PDV-a |
| `INTERNAL` | Interni prenos | Interni transfer (isti PIB) |

**PDV tretman:**

| Vrednost | Opis | Polje PDV-PP |
|----------|------|-------------|
| `DEDUCTIBLE_FULL` | Potpuno odbitni ulazni PDV | Polje 8 |
| `DEDUCTIBLE_PARTIAL` | Delimično odbitni (mešovita upotreba) | Izračunato |
| `NON_DEDUCTIBLE` | Neodbitni (reprezentacija itd.) | N/A |
| `OUTPUT_STANDARD` | Izlazni PDV po standardnoj stopi | Polje 3 |
| `OUTPUT_REDUCED` | Izlazni PDV po sniženoj stopi | Polje 4 |
| `OUTPUT_EXEMPT` | Oslobođen izlazni (izvoz itd.) | Polje 6 |
| `REVERSE_CHARGE_IN` | Obrnuti obračun (strana kupca) | Polje 8a |
| `REVERSE_CHARGE_OUT` | Obrnuti obračun (strana prodavca) | Polje 6a |

#### 4.10.3 Predložena konta (šifre konta)

Sistem TREBALO BI da predloži odgovarajuće šifre konta na osnovu:
- Tipa dokumenta
- Tipa transakcije
- Opisa stavki
- Istorijskih obrazaca za tog dobavljača/kupca
- Kontnog plana organizacije

**Standardni predlozi konta (srpski kontni plan):**

| Scenario | Predložena konta | Opis |
|----------|-----------------|------|
| Ulazna faktura - usluge | 5xx (npr. 5330) | Rashod - usluge |
| Ulazna faktura - roba | 5xx (npr. 5010) | Rashod - nabavna vrednost robe |
| Ulazna faktura - PDV | 2700 | Ulazni PDV |
| Ulazna faktura - obaveza | 4330 | Dobavljači |
| Izlazna faktura - prihod | 6xx (npr. 6010) | Prihod - prodaja |
| Izlazna faktura - PDV | 4700 | Izlazni PDV |
| Izlazna faktura - potraživanje | 2040 | Kupci |
| Primljeni avans | 4300 | Avansi od kupaca |
| Dati avans | 1500 | Avansi dobavljačima |

**Struktura podataka predloga konta:**

```json
{
  "suggested_konta": {
    "debit": [
      {
        "konto": "5330",
        "description": "Usluge održavanja",
        "amount": 50000.00,
        "confidence": 0.92,
        "source": "keyword_match",
        "keywords_matched": ["održavanje", "servis"]
      },
      {
        "konto": "2700",
        "description": "PDV u primljenim fakturama",
        "amount": 10000.00,
        "confidence": 1.00,
        "source": "vat_calculation"
      }
    ],
    "credit": [
      {
        "konto": "4330",
        "description": "Dobavljači u zemlji",
        "amount": 60000.00,
        "confidence": 0.95,
        "source": "document_type"
      }
    ]
  }
}
```

#### 4.10.4 Mapiranje PDV knjiga

Sistem MORA da mapira podatke fakture na ispravne unose u PDV knjigama:

**KPR (Knjiga primljenih računa) - Primljene fakture:**

| Polje KPR | Izvor | Izračunavanje |
|-----------|-------|-------------|
| Redni broj | Auto-increment | Sekvencijalno |
| Datum prijema | invoice.created_at | Datum importa |
| Datum fakture | invoice.invoice_date | Iz OCR-a |
| Broj fakture | invoice.invoice_number | Iz OCR-a |
| PIB isporučioca | seller.pib | Verifikovan putem APR |
| Naziv isporučioca | seller.name | Iz OCR/APR |
| Osnovica 20% | vat_breakdown.rate_20.base | Izračunato |
| PDV 20% | vat_breakdown.rate_20.tax | Izračunato |
| Osnovica 10% | vat_breakdown.rate_10.base | Izračunato |
| PDV 10% | vat_breakdown.rate_10.tax | Izračunato |
| Ukupno | invoice.total_amount | Validirano |

**KIR (Knjiga izdatih računa) - Izdate fakture:**

| Polje KIR | Izvor |
|-----------|-------|
| Redni broj | Auto-increment |
| Datum fakture | invoice.invoice_date |
| Broj fakture | invoice.invoice_number |
| PIB kupca | buyer.pib |
| Naziv kupca | buyer.name |
| (Ista PDV polja kao KPR) | |

**PDV-PP mapiranje:**

```json
{
  "pdv_book_entries": {
    "book_type": "KPR",
    "period": "2025-01",
    "pp_pdv_fields": {
      "polje_8_1": 50000.00,
      "polje_8_2": 10000.00,
      "polje_9_1": 0.00,
      "polje_9_2": 0.00
    },
    "kpr_entry": {
      "sequence": 42,
      "entry_date": "2025-01-15",
      "invoice_date": "2025-01-10",
      "invoice_number": "2025-0001",
      "supplier_pib": "123456789",
      "supplier_name": "Dobavljač ABC d.o.o.",
      "base_20": 50000.00,
      "vat_20": 10000.00,
      "base_10": 0.00,
      "vat_10": 0.00,
      "total": 60000.00
    }
  }
}
```

#### 4.10.5 Pipeline generisanja AccountingIntent

```
┌─────────────────────────────────────────────────────────────────────┐
│             Pipeline generisanja AccountingIntent                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐                                                   │
│  │ Ekstraktovana│                                                   │
│  │ faktura      │                                                   │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Korak 1: Klasifikacija dokumenta                             │  │
│  │ • Analiziraj odnos PIB prodavca/kupca prema organizaciji    │  │
│  │ • Proveri indikatore za knjižno odobrenje ("odobrenje",     │  │
│  │   "storno")                                                  │  │
│  │ • Detektuj obrasce avansne fakture                          │  │
│  │ • Identifikuj indikatore profakture                         │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Korak 2: Detekcija tipa transakcije                          │  │
│  │ • Proveri da li je PIB prodavca/kupca strani (ne-srpski)    │  │
│  │ • Detektuj EU PDV brojeve (prefiks države)                  │  │
│  │ • Identifikuj indikatore obrnutog obračuna u tekstu         │  │
│  │ • Proveri izvoznu dokumentaciju                             │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Korak 3: Odluka o PDV tretmanu                               │  │
│  │ • Primeni pravila odbitnosti organizacije                   │  │
│  │ • Proveri kategorije stavki za neodbitne rashode            │  │
│  │ • Izračunaj delimičan odbitak ako je primenjivo             │  │
│  │ • Primeni pravila obrnutog obračuna za strane transakcije  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Korak 4: Predlog konta                                       │  │
│  │ • Upari opise stavki sa kategorijama rashoda                │  │
│  │ • Proveri istoriju dobavljača za ovu organizaciju           │  │
│  │ • Primeni prilagođena pravila organizacije (Odeljak 4.11)   │  │
│  │ • Generiši balansirane duguje/potražuje unose               │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ Korak 5: Odluka o označavanju za pregled                    │  │
│  │ • Označi ako je ukupna pouzdanost < 80%                     │  │
│  │ • Označi ako je tip transakcije neobičan za ovog dobavljača │  │
│  │ • Označi ako je predlog konta nov (nikada ranije korišćen)  │  │
│  │ • Označi ako iznos prelazi prag organizacije                │  │
│  └──────────────────────────────────────────────────────────────┘  │
│         │                                                           │
│         ▼                                                           │
│  ┌──────────────┐                                                   │
│  │Računovodstv. │                                                   │
│  │ namera       │                                                   │
│  └──────────────┘                                                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

#### 4.10.6 Šema baze podataka

```sql
CREATE TABLE accounting_intents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    organization_id UUID NOT NULL REFERENCES organizations(id),

    -- Klasifikacija
    document_type VARCHAR(30) NOT NULL,
    transaction_type VARCHAR(30) NOT NULL,
    vat_treatment VARCHAR(30) NOT NULL,
    is_deductible BOOLEAN NOT NULL DEFAULT TRUE,

    -- PDV razrada
    vat_breakdown JSONB NOT NULL DEFAULT '{}',

    -- Predložena konta
    suggested_konta JSONB NOT NULL DEFAULT '{}',

    -- Mapiranje PDV knjiga
    pdv_book_entries JSONB NOT NULL DEFAULT '{}',

    -- Pouzdanost i pregled
    confidence DECIMAL(5, 2) NOT NULL,
    requires_review BOOLEAN NOT NULL DEFAULT FALSE,
    review_reasons JSONB DEFAULT '[]',
    reviewed_by UUID REFERENCES users(id),
    reviewed_at TIMESTAMP WITH TIME ZONE,

    -- Primenjena pravila (za reviziju)
    applied_rules JSONB DEFAULT '[]',

    -- Napomene računovođe
    notes TEXT,

    -- Vremenski žigovi
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_document_type CHECK (document_type IN (
        'INPUT_INVOICE', 'OUTPUT_INVOICE',
        'CREDIT_NOTE_IN', 'CREDIT_NOTE_OUT',
        'DEBIT_NOTE_IN', 'DEBIT_NOTE_OUT',
        'ADVANCE_INVOICE', 'FINAL_INVOICE', 'PROFORMA'
    )),
    CONSTRAINT valid_transaction_type CHECK (transaction_type IN (
        'DOMESTIC', 'FOREIGN_EU', 'FOREIGN_NON_EU',
        'REVERSE_CHARGE', 'EXEMPT', 'INTERNAL'
    )),
    CONSTRAINT valid_vat_treatment CHECK (vat_treatment IN (
        'DEDUCTIBLE_FULL', 'DEDUCTIBLE_PARTIAL', 'NON_DEDUCTIBLE',
        'OUTPUT_STANDARD', 'OUTPUT_REDUCED', 'OUTPUT_EXEMPT',
        'REVERSE_CHARGE_IN', 'REVERSE_CHARGE_OUT'
    ))
);

CREATE INDEX idx_accounting_intents_invoice ON accounting_intents(invoice_id);
CREATE INDEX idx_accounting_intents_org ON accounting_intents(organization_id);
CREATE INDEX idx_accounting_intents_review ON accounting_intents(requires_review) WHERE requires_review = TRUE;
CREATE INDEX idx_accounting_intents_type ON accounting_intents(document_type, transaction_type);
```

#### 4.10.7 Kategorije neodbitinih rashoda

Sistem MORA da prepozna i označi neodbitne PDV rashode prema srpskom poreskom zakonu:

| Kategorija | Srpski | Primeri | PDV odbitni |
|-----------|--------|---------|------------|
| Reprezentacija | Reprezentacija | Restorani, pokloni > praga | 50% |
| Benefiti zaposlenih | Benefiti zaposlenih | Privatna upotreba službenog vozila | 0% |
| Zabava | Zabava | Događaji, sponzorstva | 0% |
| Lična upotreba | Lična upotreba | Mešovita poslovna/privatna | Proporcionalno |
| Oslobođene isporuke | Oslobođene isporuke | Bankarske, usluge osiguranja | 0% |

**Ključne reči za detekciju:**

```python
OBRASCI_NEODBITINIH = {
    "reprezentacija": {
        "keywords": ["ručak", "večera", "restoran", "kafić", "poklon", "dar"],
        "deductibility": 0.50,
        "vat_treatment": "DEDUCTIBLE_PARTIAL"
    },
    "gorivo_putničko": {
        "keywords": ["gorivo", "benzin", "dizel", "gas"],
        "vehicle_type_check": True,
        "deductibility": 0.00,
        "vat_treatment": "NON_DEDUCTIBLE"
    },
    "zabava": {
        "keywords": ["sponzorstvo", "donacija", "event", "proslava"],
        "deductibility": 0.00,
        "vat_treatment": "NON_DEDUCTIBLE"
    }
}
```

### 4.11 Motor za automatizaciju pravila

Ovaj odeljak definiše motor pravila specifičan za kancelariju koji omogućava računovodstvenim agencijama da prilagode obradu faktura sopstvenim heuristikama.

#### 4.11.1 Pregled

Motor pravila omogućava računovođama da definišu prilagođena pravila automatizacije koja:
- Automatski dodeljuju konta na osnovu dobavljača ili ključnih reči
- Označavaju fakture za pregled na osnovu prilagođenih kriterijuma
- Postavljaju podrazumevani PDV tretman za specifične scenarije
- Automatizuju ponavljajuće odluke o klasifikaciji

#### 4.11.2 Struktura pravila

| Polje | Tip | Opis | Obavezno |
|-------|-----|------|----------|
| id | UUID | Jedinstveni identifikator | Da |
| organization_id | UUID | Organizacija vlasnik | Da |
| name | String | Ljudski čitljivo ime pravila | Da |
| description | String | Šta pravilo radi | Ne |
| rule_type | Enum | Tip pravila | Da |
| priority | Integer | Redosled izvršavanja (niži = prvi) | Da |
| conditions | JSON | Kada se pravilo primenjuje | Da |
| actions | JSON | Šta pravilo radi | Da |
| is_active | Boolean | Pravilo aktivno | Da |
| created_by | UUID | Korisnik koji je kreirao | Da |
| stats | JSON | Statistike izvršavanja | Ne |

**Tipovi pravila:**

| Tip | Opis | Slučaj korišćenja |
|-----|------|-------------------|
| `KONTO_ASSIGNMENT` | Dodeli specifičan konto | "Fakture od dobavljača X → konto 5330" |
| `VAT_TREATMENT` | Postavi PDV tretman | "Fakture za gorivo → neodbitno" |
| `AUTO_APPROVE` | Preskoči pregled | "Fakture < 5000 RSD → automatski odobri" |
| `FLAG_FOR_REVIEW` | Forsiraj pregled | "Novi dobavljač → uvek pregledaj" |
| `DOCUMENT_TYPE` | Zameni klasifikaciju | "Dobavljač Y uvek šalje knjižna odobrenja" |
| `CUSTOM_FIELD` | Postavi metapodatke | "Dodaj centar troškova na osnovu koda projekta" |

#### 4.11.3 Sintaksa uslova

Uslovi koriste strukturirani JSON format koji podržava:

**Uslovi polja:**

```json
{
  "conditions": {
    "operator": "AND",
    "rules": [
      {
        "field": "seller.pib",
        "operator": "equals",
        "value": "123456789"
      },
      {
        "field": "total_amount",
        "operator": "greater_than",
        "value": 10000
      }
    ]
  }
}
```

**Dostupni operatori:**

| Operator | Opis | Primenjivo na |
|----------|------|--------------|
| `equals` | Tačno poklapanje | Sva polja |
| `not_equals` | Nije jednako | Sva polja |
| `contains` | Poklapanje podstringa | String polja |
| `starts_with` | Poklapanje prefiksa | String polja |
| `ends_with` | Poklapanje sufiksa | String polja |
| `regex` | Regex obrazac | String polja |
| `greater_than` | > vrednost | Numerička polja |
| `less_than` | < vrednost | Numerička polja |
| `between` | Opseg inkluzivno | Numerička/datumska polja |
| `in` | Vrednost u listi | Sva polja |
| `not_in` | Vrednost nije u listi | Sva polja |
| `is_null` | Polje je prazno | Sva polja |
| `is_not_null` | Polje ima vrednost | Sva polja |

#### 4.11.4 Sintaksa akcija

Akcije definišu šta se dešava kada uslovi odgovaraju:

**Dodeljivanje konta:**
```json
{
  "actions": [
    {
      "type": "SET_KONTO",
      "target": "expense",
      "value": "5330",
      "description": "IT usluge"
    }
  ]
}
```

**PDV tretman:**
```json
{
  "actions": [
    {
      "type": "SET_VAT_TREATMENT",
      "value": "NON_DEDUCTIBLE",
      "reason": "Gorivo za putnička vozila"
    }
  ]
}
```

**Označavanje za pregled:**
```json
{
  "actions": [
    {
      "type": "FLAG_REVIEW",
      "reason": "Faktura preko 100.000 RSD - potrebna dodatna provera",
      "assign_to": "senior_accountant"
    }
  ]
}
```

#### 4.11.5 Primeri pravila

**Pravilo 1: Telekom provajder → Specifičan konto**
```json
{
  "name": "Telekom Srbija - Telefonija",
  "description": "Sve fakture od Telekoma idu na konto 5210 (PTT troškovi)",
  "rule_type": "KONTO_ASSIGNMENT",
  "priority": 10,
  "conditions": {
    "operator": "AND",
    "rules": [
      {"field": "seller.pib", "operator": "in", "value": ["100002534", "100002535"]},
      {"field": "document_type", "operator": "equals", "value": "INPUT_INVOICE"}
    ]
  },
  "actions": [
    {"type": "SET_KONTO", "target": "expense", "value": "5210", "description": "PTT troškovi"},
    {"type": "SET_VAT_TREATMENT", "value": "DEDUCTIBLE_FULL"}
  ]
}
```

**Pravilo 2: Fakture za gorivo → Neodbitno**
```json
{
  "name": "Gorivo - putnička vozila",
  "description": "PDV na gorivo za putnička vozila nije priznat",
  "rule_type": "VAT_TREATMENT",
  "priority": 5,
  "conditions": {
    "operator": "AND",
    "rules": [
      {"field": "line_items[].description", "operator": "regex", "value": "(gorivo|benzin|dizel|nafta)"},
      {"field": "seller.name", "operator": "regex", "value": "(NIS|MOL|OMV|Petrol|Lukoil)"}
    ]
  },
  "actions": [
    {"type": "SET_VAT_TREATMENT", "value": "NON_DEDUCTIBLE", "reason": "Gorivo za putnička vozila - PDV se ne priznaje"},
    {"type": "SET_KONTO", "target": "expense", "value": "5130", "description": "Troškovi goriva"}
  ]
}
```

**Pravilo 3: Velika faktura → Pregled starijeg računovođe**
```json
{
  "name": "Velike fakture - pregled",
  "description": "Fakture preko 500.000 RSD zahtevaju pregled starijeg računovođe",
  "rule_type": "FLAG_FOR_REVIEW",
  "priority": 1,
  "conditions": {
    "operator": "AND",
    "rules": [
      {"field": "total_amount", "operator": "greater_than", "value": 500000},
      {"field": "currency", "operator": "equals", "value": "RSD"}
    ]
  },
  "actions": [
    {"type": "FLAG_REVIEW", "reason": "Faktura prelazi 500.000 RSD", "assign_to_role": "manager"}
  ]
}
```

**Pravilo 4: Novi dobavljač → Uvek pregledaj**
```json
{
  "name": "Novi dobavljač",
  "description": "Prve fakture od novih dobavljača uvek pregledati",
  "rule_type": "FLAG_FOR_REVIEW",
  "priority": 2,
  "conditions": {
    "operator": "AND",
    "rules": [
      {"field": "is_first_from_supplier", "operator": "equals", "value": true}
    ]
  },
  "actions": [
    {"type": "FLAG_REVIEW", "reason": "Prvi put primamo fakturu od ovog dobavljača"}
  ]
}
```

**Pravilo 5: Mala faktura - automatsko odobrenje**
```json
{
  "name": "Male fakture - automatski",
  "description": "Fakture ispod 5.000 RSD od poznatih dobavljača idu automatski",
  "rule_type": "AUTO_APPROVE",
  "priority": 100,
  "conditions": {
    "operator": "AND",
    "rules": [
      {"field": "total_amount", "operator": "less_than", "value": 5000},
      {"field": "supplier_invoice_count", "operator": "greater_than", "value": 5},
      {"field": "confidence", "operator": "greater_than", "value": 0.90}
    ]
  },
  "actions": [
    {"type": "AUTO_APPROVE", "skip_review": true}
  ]
}
```

#### 4.11.6 Šema baze podataka

```sql
CREATE TABLE automation_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),

    -- Definicija pravila
    name VARCHAR(255) NOT NULL,
    description TEXT,
    rule_type VARCHAR(30) NOT NULL,
    priority INTEGER NOT NULL DEFAULT 50,

    -- Logika pravila (JSON)
    conditions JSONB NOT NULL,
    actions JSONB NOT NULL,

    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Metapodaci
    created_by UUID NOT NULL REFERENCES users(id),
    updated_by UUID REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Statistike
    execution_count INTEGER DEFAULT 0,
    last_executed_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT valid_rule_type CHECK (rule_type IN (
        'KONTO_ASSIGNMENT', 'VAT_TREATMENT', 'AUTO_APPROVE',
        'FLAG_FOR_REVIEW', 'DOCUMENT_TYPE', 'CUSTOM_FIELD'
    )),
    CONSTRAINT unique_rule_name_per_org UNIQUE (organization_id, name)
);

CREATE INDEX idx_rules_org ON automation_rules(organization_id);
CREATE INDEX idx_rules_active ON automation_rules(organization_id, is_active) WHERE is_active = TRUE;
CREATE INDEX idx_rules_type ON automation_rules(rule_type);

-- Dnevnik izvršavanja pravila za reviziju
CREATE TABLE rule_executions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id UUID NOT NULL REFERENCES automation_rules(id),
    invoice_id UUID NOT NULL REFERENCES invoices(id),
    accounting_intent_id UUID REFERENCES accounting_intents(id),

    -- Detalji izvršavanja
    conditions_matched JSONB NOT NULL,
    actions_applied JSONB NOT NULL,

    -- Vreme
    executed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    execution_time_ms INTEGER
);

CREATE INDEX idx_rule_exec_rule ON rule_executions(rule_id);
CREATE INDEX idx_rule_exec_invoice ON rule_executions(invoice_id);
CREATE INDEX idx_rule_exec_date ON rule_executions(executed_at);
```

#### 4.11.7 Redosled evaluacije pravila

Pravila se evaluiraju sledećim redosledom:

1. **Po prioritetu** (niži broj = viši prioritet)
2. **Unutar istog prioriteta**: Po datumu kreiranja (stariji prvi)
3. **Prioritet tipa pravila** za konflikte:
   - `FLAG_FOR_REVIEW` se uvek primenjuje (aditivno)
   - `AUTO_APPROVE` može biti zamenjeno sa `FLAG_FOR_REVIEW`
   - `KONTO_ASSIGNMENT` - poslednje poklopljeno pravilo pobeđuje
   - `VAT_TREATMENT` - poslednje poklopljeno pravilo pobeđuje

**Rešavanje konflikata:**
```
AKO se više KONTO_ASSIGNMENT pravila poklope:
    Koristi pravilo sa najnižim brojem prioriteta
    Zapiši upozorenje o konfliktu

AKO se i AUTO_APPROVE i FLAG_FOR_REVIEW poklope:
    FLAG_FOR_REVIEW pobeđuje (bezbednost na prvom mestu)
    Zapiši oba pravila u revizijski trag
```

#### 4.11.8 Šabloni pravila

Sistem TREBALO BI da pruži unapred pripremljene šablone pravila za česte srpske računovodstvene scenarije:

| Šablon | Opis |
|--------|------|
| `fuel_non_deductible` | Fakture za gorivo → neodbitni PDV |
| `telecom_expenses` | Telekom provajderi → konto PTT troškova |
| `office_supplies` | Dobavljači kancelarijskog materijala → konto materijalnog rashoda |
| `professional_services` | Konsalting/pravne usluge → konto rashoda usluga |
| `utilities` | Komunalna preduzeća → konto komunalnih troškova |
| `rent_payments` | Fakture za zakup → konto troškova zakupa |
| `large_invoice_review` | Prag pregleda faktura visokih vrednosti |
| `new_supplier_review` | Prva faktura od novog dobavljača |
| `foreign_supplier_review` | Pregled dobavljača van Srbije |

### 4.12 Upravljanje klijentima (Agencija)

Ovaj odeljak definiše funkcionalnost Upravljanja klijentima koja je dostupna isključivo organizacijama na Agency planu. Omogućava računovodstvenim agencijama da upravljaju kompanijama klijenata i filtriraju fakture po klijentu.

**Kontrola pristupa:** Celokupna funkcionalnost Upravljanja klijentima je zaštićena oznakom funkcionalnosti `CLIENT_MANAGEMENT`, koja MORA biti omogućena samo za Agency plan.

#### FZ-4.12.1 CRUD operacije za klijente
| ID | FZ-4.12.1 |
|----|-----------|
| **Opis** | Sistem MORA da omogući korisnicima na Agency planu kreiranje, pregled, izmenu i deaktivaciju klijenata |
| **Kreiranje** | Naziv (obavezno), PIB (obavezno, jedinstven po organizaciji, validiran format), kontakt e-pošta, adresa, napomene |
| **Pregled** | Paginirana lista sa pretragom po nazivu ili PIB-u; podržava `?search=` i `?page=`/`?page_size=` parametre upita |
| **Izmena** | Sva polja klijenta osim `organization_id` i `id` |
| **Deaktivacija** | Postavlja `is_active = false`; podaci klijenta se zadržavaju za reviziju; fakture ostaju povezane |
| **Autorizacija** | Samo korisnici u organizacijama sa omogućenom `CLIENT_MANAGEMENT` oznakom funkcionalnosti |

#### FZ-4.12.2 Auto-dodela faktura na osnovu PIB-a
| ID | FZ-4.12.2 |
|----|-----------|
| **Opis** | Posle OCR ekstrakcije, sistem MORA automatski dodeliti fakturu odgovarajućem klijentu na osnovu PIB-a prodavca |
| **Logika poklapanja** | Uporedi ekstraktovani `seller.pib` sa PIB-ovima svih aktivnih klijenata u istoj organizaciji |
| **Poklapanje pronađeno** | Postavi `invoice.client_id` na ID poklopljenog klijenta |
| **Nema poklapanja** | Ostavi `invoice.client_id` kao NULL; faktura ostaje nedodeljena |
| **Tajming** | Dodela se dešava tokom post-OCR obrade, pre čuvanja fakture |

#### FZ-4.12.3 Filtriranje faktura po klijentu
| ID | FZ-4.12.3 |
|----|-----------|
| **Opis** | Sistem MORA da podržava filtriranje faktura po `client_id` |
| **Parametar upita** | `GET /invoices?client_id={uuid}` vraća samo fakture dodeljene tom klijentu |
| **Bez filtera** | Kada je `client_id` izostavljen, vraćaju se sve fakture organizacije |
| **Autorizacija** | Klijent MORA pripadati organizaciji korisnika koji šalje zahtev |

#### FZ-4.12.4 Selektor klijenata u bočnom meniju (zamenjeno u M19)
| ID | FZ-4.12.4 |
|----|-----------|
| **Opis** | **Zamenjeno u M19.** Bočni selektor klijenata je uklonjen u korist klijent-prvi UI-a (vidi 4.18). Pregled portfelja (`/pregled`) i radne table klijenata (`/klijenti/{id}`) sada zamenjuju filter u bočnom meniju. |
| **Status** | Otpisano; ne implementirati u novom radu |

#### FR-4.12.5 Log događaja klijenta (client_events)

| ID | FR-4.12.5 |
|----|-----------|
| **Opis** | Append-only log događaja po klijentu, koji napaja tab "Hronologija" u radnoj tabli klijenta (vidi 4.18) |
| **Model** | Tabela `client_events` — `id`, `organization_id`, `client_id`, `event_type`, `entity_type`, `entity_id`, `metadata` (JSONB), `created_by`, `created_at` |
| **Tipovi događaja** | `invoice_uploaded`, `invoice_verified`, `invoice_exported`, `accounting_intent_classified`, `rule_fired`, `client_assigned` |
| **Pisanje** | Servisni sloj upisuje događaje pri otpremanju fakture, verifikaciji, izvozu, klasifikaciji namere, paljenju pravila i dodeli klijentu. Neuspeh upisa se loguje ali ne prekida glavni tok. |
| **Čitanje** | Hronologija tab u workspace-u klijenta (`/klijenti/{id}`) prikazuje paginirane događaje sortirane po `created_at DESC` |
| **Indeksi** | `idx_client_events_org_client (organization_id, client_id, created_at DESC)`, `idx_client_events_type (event_type)`, `idx_client_events_entity (entity_type, entity_id)` |

#### FR-4.12.6 Pravila po klijentu (rule_client_associations)

| ID | FR-4.12.6 |
|----|-----------|
| **Opis** | Pravila automatizacije mogu biti globalna (svi klijenti) ili vezana za određenog klijenta |
| **Model** | Join tabela `rule_client_associations` — `rule_id`, `client_id`, `created_at` |
| **Semantika** | Pravilo bez asocijacija se primenjuje na sve klijente organizacije; pravilo sa jednom ili više asocijacija se primenjuje samo na te klijente |
| **UI** | Pravila se mogu kreirati direktno iz radne table klijenta (CTA "Kreiraj pravilo za ovog klijenta") sa pre-popunjenom asocijacijom; org-wide pravila se uređuju iz globalne stranice `Pravila` u bočnom meniju |
| **Indeksi** | `idx_rca_client (client_id)` |

---

### 4.13 Izveštaji o fakturama (Izveštaji)

Ovaj odeljak definiše funkcionalnost Izveštaja o fakturama, koja zamenjuje ranije planiranu generaciju PDV knjiga (KPR/KIR). Izveštaji pružaju pet unapred definisanih analitičkih prikaza nad denormalizovanom tabelom `invoice_line_items`. Svi izveštaji se generišu isključivo SQL agregacijom — bez LLM poziva.

**Kontrola pristupa:** Funkcionalnost Izveštaja je zaštićena oznakom `REPORTS`, koja MORA biti omogućena za Professional i Agency planove. Korisnici na Starter planu dobijaju 403 odgovor.

#### 4.13.1 Denormalizovana tabela stavki faktura

Kako bi se izbeglo raspakovavanje JSON-a pri svakom upitu za izveštaj, sistem održava posebnu tabelu `invoice_line_items` koja preslikava stavke iz obrađenih faktura u ravnom obliku.

**Pravila popunjavanja:**
- Popunjava se neblokijarujuće odmah nakon završetka OCR obrade (worker upisuje redove nakon čuvanja fakture).
- Ponovo se popunjava (brisanje + ponovni unos za odgovarajuću fakturu) kad god korisnik sačuva izmene stavki na stranici detalja fakture.
- Svaki upit je ograničen na `organization_id`.

**Šema tabele:**

```sql
CREATE TABLE invoice_line_items (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    invoice_id    UUID NOT NULL REFERENCES invoices(id) ON DELETE CASCADE,
    description   TEXT,
    quantity      NUMERIC(12, 4),
    unit_price    NUMERIC(15, 4),
    total         NUMERIC(15, 2),
    tax_rate      NUMERIC(5, 2),
    currency      VARCHAR(3) NOT NULL DEFAULT 'RSD',
    supplier_name TEXT,
    supplier_pib  VARCHAR(20),
    invoice_date  DATE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX ix_invoice_line_items_org     ON invoice_line_items(organization_id);
CREATE INDEX ix_invoice_line_items_invoice ON invoice_line_items(invoice_id);
CREATE INDEX ix_invoice_line_items_date    ON invoice_line_items(invoice_date);
CREATE INDEX ix_invoice_line_items_supplier ON invoice_line_items(supplier_pib);
```

#### 4.13.2 Šabloni izveštaja

Svi endpoint-i za izveštaje su pod `/api/v1/reports/` i prihvataju zajednički skup parametara upita:

| Parametar | Tip | Opis |
|-----------|-----|------|
| `date_from` | `YYYY-MM-DD` | Početak perioda izveštavanja (obavezno) |
| `date_to` | `YYYY-MM-DD` | Kraj perioda izveštavanja (obavezno) |
| `supplier_pib` | String | Opcionalno — filtriranje po jednom dobavljaču |
| `search` | String | Opcionalno — pretraga po ključnoj reči u opisu stavke (ne razlikuje velika/mala slova) |

##### FZ-4.13.2.1 Pregled primljene robe (`/received-goods`)

| ID | FZ-4.13.2.1 |
|----|-------------|
| **Opis** | Grupuje stavke faktura po opisu, sabira količinu i ukupan iznos, i prikazuje sve dobavljače koji su isporučili svaki artikal |
| **Grupisanje** | `description` (ne razlikuje velika/mala slova, bez razmaka) |
| **Agregati** | `SUM(quantity)`, `SUM(total)`, `array_agg(DISTINCT supplier_name)` |
| **Primena** | "Koliko smo primili artikla X i od kojih dobavljača?" |

##### FZ-4.13.2.2 Troškovi po dobavljaču (`/spending-by-supplier`)

| ID | FZ-4.13.2.2 |
|----|-------------|
| **Opis** | Vraća ukupan iznos faktura po dobavljaču za izabrani period |
| **Grupisanje** | `supplier_pib`, `supplier_name` |
| **Agregati** | `SUM(total)`, `COUNT(DISTINCT invoice_id)` |
| **Primena** | "Koji su naši najveći dobavljači po iznosu troškova?" |

##### FZ-4.13.2.3 Mesečni pregled stavki (`/monthly-breakdown`)

| ID | FZ-4.13.2.3 |
|----|-------------|
| **Opis** | Paginirana ravna lista svih pojedinačnih stavki faktura za izabrani period |
| **Sortiranje** | `invoice_date DESC`, zatim `supplier_name ASC` |
| **Paginacija** | `?page=` i `?page_size=` (podrazumevano 50 redova po stranici) |
| **Primena** | "Prikaži sve što smo kupili u martu." |

##### FZ-4.13.2.4 Poređenje cena (`/price-comparison`)

| ID | FZ-4.13.2.4 |
|----|-------------|
| **Opis** | Za svaki jedinstven opis artikla koji se javlja kod više od jednog dobavljača, prikazuje minimalnu, maksimalnu i prosečnu jediničnu cenu uz listu dobavljača |
| **Grupisanje** | `description` |
| **Agregati** | `MIN(unit_price)`, `MAX(unit_price)`, `AVG(unit_price)`, `array_agg(DISTINCT supplier_name)` |
| **Filter** | Samo opisi sa `COUNT(DISTINCT supplier_pib) > 1` |
| **Primena** | "Da li plaćamo različite cene za isti artikal kod različitih dobavljača?" |

##### FZ-4.13.2.5 Pregled troškova (`/expense-summary`)

| ID | FZ-4.13.2.5 |
|----|-------------|
| **Opis** | Ukupni troškovi grupisani po mesecu ili nedelji |
| **Grupisanje** | `date_trunc('month', invoice_date)` ili `date_trunc('week', invoice_date)`, kontrolisano parametrom `?group_by=month\|week` |
| **Agregati** | `SUM(total)`, `COUNT(DISTINCT invoice_id)` |
| **Primena** | "Kako su se naši troškovi menjali od meseca do meseca?" |

##### FZ-4.13.2.6 Kalkulacija cena (`/kalkulacija`)

| ID | FZ-4.13.2.6 |
|----|-------------|
| **Opis** | Kalkulacija cene po stavci: nabavna cena, marža i prodajna cena za svaki artikal |
| **Izvor podataka** | `invoice_line_items` spojen sa `product_catalog` putem FK `product_id` |
| **Kolone** | `description`, `unit_price` (nabavna cena), `default_margin_pct`, izračunata `selling_price` |
| **Primena** | "Koja je prodajna cena i marža za svaki kupljeni artikal?" |

##### FZ-4.13.2.7 Razlika u ceni — RUC (`/ruc`)

| ID | FZ-4.13.2.7 |
|----|-------------|
| **Opis** | Analiza razlike u ceni (RUC) grupisana po unosu u katalogu proizvoda |
| **Grupisanje** | `product_id` (kanonički proizvod) |
| **Agregati** | `AVG(unit_price)` kao prosečna nabavna cena, `selling_price` iz kataloga, izračunati iznos i procenat RUC-a |
| **Primena** | "Kolika je naša marža za sve nabavke svakog proizvoda?" |

##### FZ-4.13.2.8 Troškovi po kategoriji (`/spending-by-category`)

| ID | FZ-4.13.2.8 |
|----|-------------|
| **Opis** | Ukupni troškovi grupisani po kategoriji iz kataloga proizvoda |
| **Grupisanje** | `category` iz `product_catalog` |
| **Agregati** | `SUM(total)`, `COUNT(DISTINCT invoice_id)`, `array_agg(DISTINCT supplier_name)` |
| **Primena** | "Koliko smo potrošili po svakoj kategoriji proizvoda?" |

##### FZ-4.13.2.9 Dnevna evidencija robe (`/dpu`)

| ID | FZ-4.13.2.9 |
|----|-------------|
| **Opis** | Sve stavke primljene na određeni datum (zamenjuje nekadašnju stranicu "Šank lista" / DPU) |
| **Filter** | `invoice_date` (obavezno — tačan datum) |
| **Kolone** | `description`, `quantity`, `unit_price`, `total`, `supplier_name`, `invoice_number` |
| **Primena** | "Koja roba je primljena određenog dana?" |

#### 4.13.3 CSV izvoz

Svaki endpoint za izveštaj prihvata zaglavlje `Accept: text/csv` (ili parametar `?format=csv`) i vraća CSV sa UTF-8 BOM oznakom:

- Tačka-zarez kao separator polja
- Zarez kao decimalni separator (srpski lokalni format)
- Zaglavlja kolona na srpskom jeziku
- Naziv fajla: `izvestaj_{tip_izvestaja}_{date_from}_{date_to}.csv`

#### 4.13.4 Stranica u aplikaciji

Stranica `/izvestaji` je objedinjeni centar za sve izveštaje, upravljanje katalogom proizvoda i dnevnu evidenciju robe. Zamenjuje ranije odvojene stranice `/katalog` i `/dpu`.

| Zahtev | Detalj |
|--------|--------|
| **Ruta** | `/{orgSlug}/izvestaji` |
| **Navigacija** | Dugmad za grupe na vrhu: "Opšti" (5 opštih izveštaja), "Nabavka i prodaja" (kalkulacija, RUC, kategorije, dnevna evidencija), "Upravljanje" (katalog proizvoda) |
| **Raspored tabova** | Horizontalni tabovi unutar svake grupe za pojedinačne izveštaje/upravljanje |
| **Filteri** | Birač opsega datuma, opcionalno polje za PIB/naziv dobavljača, opcionalna pretraga (po tabu) |
| **Rezultati** | Prikazani u tabeli sa mogućnošću sortiranja ispod trake filtera |
| **Izvoz** | Dugme "Izvezi CSV" — pokreće preuzimanje fajla u pregledaču |
| **Kontrola plana** | Korisnici koji nisu na PRO planu vide modal za nadogradnju umesto forme za filtere |
| **Uklonjene stranice** | Rute `/katalog` i `/dpu` su uklonjene; sadržaj je objedinjen ovde |

---

### 4.14 Email Ingestion Pipeline (planirano, još nije implementirano)

| ID | FR-4.14 |
|----|---------|
| **Status** | Planirano. Tabele i kolone postoje u nekim migracijama, ali pipeline nije povezan u produkciji. |
| **Opis** | Inbox po klijentu (npr. `klijent-slug@in.saldora.rs`) prima fakture kao priloge e-pošte; sistem ekstrahuje priloge, klasifikuje ih kao fakture i ubacuje ih u redovni OCR pipeline sa ispravnom dodelom klijenta. |
| **Razlog za odlaganje** | Vlasnici agencija trenutno koriste zajedničke inbox-e ili upload-e; potreba za dedikovanim email ingestion-om je realno potvrđena tek nakon razgovora sa pilot agencijama. Specifikacija će se revidirati pre implementacije. |

---

### 4.15 Katalog proizvoda

Ovaj odeljak definiše funkcionalnost Kataloga proizvoda, koja obezbeđuje kanonički spisak proizvoda za tačno praćenje zaliha, analizu marže i poređenje cena — pre svega za ugostiteljske i hotelijerske klijente.

**Kontrola pristupa:** Katalog proizvoda je dostupan na Professional i Agency planovima.

#### 4.15.1 Pregled

Katalog proizvoda čuva kanonička imena proizvoda sa aliasima (alternativna imena od različitih dobavljača). Kada su stavke faktura povezane sa unosima u katalogu, sistem može normalizovati opise stavki između dobavljača i omogućiti izveštaje o nabavci (Odeljak 4.13.2.6–4.13.2.9).

#### 4.15.2 Šema baze podataka

```sql
CREATE TABLE product_catalog (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    canonical_name  TEXT NOT NULL,
    unit_of_measure VARCHAR(20),
    category        VARCHAR(50),
    aliases         JSONB NOT NULL DEFAULT '[]',
    selling_price   NUMERIC(15, 2),
    default_margin_pct NUMERIC(5, 2),
    match_count     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX ix_pc_org_name ON product_catalog(organization_id, canonical_name);
CREATE INDEX ix_pc_org_id ON product_catalog(organization_id);
CREATE INDEX ix_pc_category ON product_catalog(category);
```

PostgreSQL ekstenzija **`pg_trgm`** se koristi za trigramsko fuzzy poređenje vrednosti `description` u `invoice_line_items` sa unosima u katalogu. Tabela `invoice_line_items` sadrži nullable FK kolonu `product_id` (dodata u migraciji 0007) za povezivanje stavki sa kanonički unosom u katalogu.

#### 4.15.3 API endpoint-i

Svi endpoint-i za katalog su pod `/api/v1/products/`:

| Metod | Endpoint | Opis |
|-------|----------|------|
| `GET` | `/api/v1/products/` | Lista svih unosa u katalogu za organizaciju |
| `POST` | `/api/v1/products/` | Kreiranje novog unosa |
| `GET` | `/api/v1/products/{id}` | Preuzimanje jednog unosa |
| `PATCH` | `/api/v1/products/{id}` | Izmena kanonijskog imena, aliasa, prodajne cene, marže, kategorije |
| `DELETE` | `/api/v1/products/{id}` | Brisanje unosa |
| `GET` | `/api/v1/products/merge-suggestions` | Lista parova unosa koji su verovatno duplikati (trigramska sličnost iznad praga) |
| `POST` | `/api/v1/products/merge` | Spajanje dva unosa: zadržava jedan kao kanonički, premešta aliase, ažurira FK veze |

#### 4.15.4 Frontend (u okviru /izvestaji)

Upravljanje katalogom proizvoda je dostupno iz grupe "Upravljanje" na stranici `/izvestaji`:

| Funkcionalnost | Detalj |
|----------------|--------|
| **Lista unosa** | Tabela kanonijskih naziva, kategorija, broja aliasa, prodajne cene, marže |
| **Dodavanje/izmena unosa** | Forma za kanonijsko ime, kategoriju, jedinicu mere, aliase (unos tagova), prodajnu cenu, maržu |
| **Predlozi spajanja** | Tab sa parovima verovatnih duplikata i akcijom "Spoji" |
| **Pretraga/filtriranje** | Pretraga po kanonijskom imenu ili kategoriji |

---

### 4.16 Sistem podrške u aplikaciji (planirano)

> **Status:** Planirano. Šema i osnovni endpoint-i su definisani, ali UI sistem podrške nije povezan u produkciji. Trenutno se podrška obrađuje preko e-pošte; ovaj odeljak ostaje kao referentna specifikacija za buduću implementaciju.

Sistem podrške zasnovan na tiketima, ugrađen u aplikaciju. Klijenti kreiraju tikete sa stranice Podrška, dodaju fajlove i prate status. Administratori upravljaju svim tiketima iz posebnog admin panela.

**Kontrola pristupa:** Dostupno na svim planovima.

#### 4.16.1 Model podataka

**support_tickets:**
- id, organization_id, user_id (kreator), subject, status (open/in_progress/resolved/closed), priority (low/normal/high), category (billing/technical/feature_request/other), created_at, updated_at

**support_messages:**
- id, ticket_id, user_id (pošiljalac), body (TEXT), is_admin_reply (BOOLEAN), created_at

**support_attachments:**
- id, message_id, file_name, file_path (S3 ključ), file_size, content_type, created_at

#### 4.16.2 Klijentski endpoint-i
- POST /api/v1/support/tickets — kreiranje tiketa sa inicijalnom porukom
- GET /api/v1/support/tickets — lista tiketa organizacije (paginirano, sa filterima)
- GET /api/v1/support/tickets/{id} — detalji tiketa sa porukama
- POST /api/v1/support/tickets/{id}/messages — dodavanje odgovora (sa fajlovima)
- POST /api/v1/support/tickets/{id}/close — zatvaranje tiketa

#### 4.16.3 Admin endpoint-i
- GET /api/v1/admin/support/tickets — svi tiketi svih organizacija
- PATCH /api/v1/admin/support/tickets/{id} — izmena statusa/prioriteta
- POST /api/v1/admin/support/tickets/{id}/messages — admin odgovor

#### 4.16.4 Frontend
- Klijent: /{orgSlug}/podrska — lista tiketa, forma za kreiranje, prikaz konverzacije
- Admin: /{orgSlug}/admin/podrska — upravljanje tiketima svih organizacija
- Bedž u bočnoj traci: broj nepročitanih odgovora
- Status bedževi: Otvoren (zeleni), U obradi (žuti), Rešen (plavi), Zatvoren (sivi)

#### 4.16.5 Obaveštenja
- Bedž u bočnoj traci za nepročitane odgovore (klijent) i otvorene tikete (admin)
- Opciono email obaveštenje pri admin odgovoru i novom tiketu

---

### 4.17 Van obima / Otpisani moduli

Ovaj odeljak konsoliduje sve što je eksplicitno uklonjeno, odloženo ili je trajno van obima. Postoji da budući saradnici ne bi trošili vreme ponavljajući već donete odluke.

| Funkcionalnost | Status | Razlog |
|----------------|--------|--------|
| **Paušal modul** (M14) — KPO knjiga, paušalci kao kupci, polje `direction` na fakturama, `client_type`, tabela `customers`, `invoice_counters`, paušal-specifični ruteri | **Otpisano, kod vraćen** | Paušalci nisu ciljno tržište. MiniMax-ov dedikovani paušal proizvod opslužuje taj segment dobro; takmičenje tu je višegodišnja borba koju ne možemo dobiti. |
| **Klijent portal** (krajnji klijenti šalju dokumente direktno) | **Otpisano** | Vlasnici ugostiteljskih objekata nisu portal korisnici. Agencija danas prima dokumente preko e-pošte/WhatsApp-a/papira i taj kanal nije Saldora-ina površina. Agencija ostaje jedina klasa korisnika. |
| **Compliance Watchdog** (M18) — zakazana evaluacija pravila koja proizvodi alarme | **Otpisano** | Razmišljanje iz paušal ere. Pravila i dalje pucaju na događaje; zakazani watchdog ne dodaje vrednost ugostiteljskim agencijama. |
| **Strani reverse-charge kao samostalan modul** (M15) | **Trajno odloženo** | Postojeća NBS konverzija + AccountingIntent već adekvatno opslužuju mali obim stranih ugostiteljskih faktura. Vratiti se samo ako agencije prijave kao stvarnu bol. |
| **Praćenje plaćanja** (FR-4.7.4 u ranijim verzijama) — `payment_status`, `paid_amount`, `paid_date`, otvorene stavke, izveštaji starenja | **Uklonjeno** | Saldora je samo sloj inteligencije. Plaćanje pripada MiniMax-u. |
| **Webhook obaveštenja** (FR-4.8.2 u ranijim verzijama) | **Deprioritetizovano** | Webhookovi postaju korisni tek kada je ceo radni tok API-driven sa kupčeve strane; nismo tu. Paddle webhookovi za naplatu ostaju u opsegu. |
| **SEF integracija kao nosivi izvor podataka** (M-SEF, ranije Odeljak 12.5/12.6) | **Deprioritetizovano** | Klin su papirne fakture koje SEF ne pokriva. SEF ingestion kao sekundarni izvor podataka ostaje van-milestone aktivnost ali nije ni na jednom aktivnom milestone-u i uklonjen je iz ovog SRS-a kao prvoklasni odeljak. |
| **Bankarsko usaglašavanje, knjiženja u glavnu knjigu, povezivanje plaćanja** | **Trajno van obima** | MiniMax to obrađuje. Saldora predaje podatke; ne vodi knjige. |
| **Retreniranje modela / fine-tuning na korisničkim podacima** | **Trajno van obima** | Samo pre-trenirani modeli (dots.ocr za OCR, Claude Haiku za ekstrakciju). Logovi korekcija (Odeljak 9.8) postoje za monitoring kvaliteta, ne za treniranje. |
| **Predprocesiranje slike za VLM** (deskewing, binarizacija, podešavanje kontrasta pre slanja u dots.ocr) | **Onemogućeno** | dots.ocr najbolje radi na originalnim slikama u boji. Pipeline za predprocesiranje koji je postojao za tradicionalne OCR engine je preskočen za VLM put. |
| **EasyOCR fallback** kada dots.ocr ne uspe | **Uklonjen** | Alternativni OCR engine ne pružaju dovoljnu tačnost na srpskim ćiriličnim/latiničnim dokumentima. Ako dots.ocr ne uspe, faktura se markira za ručni pregled — bez automatskog fallback engine-a. |
| **Stripe integracija** | **Trajno van obima** | Stripe nije dostupan u Srbiji. Paddle je Merchant of Record. Bilo koje reference na Stripe u starijim verzijama nisu aktuelne (ne Stripe). |
| **SEF kao nosivi tok** | **Deprioritetizovano** | Vidi gore. SEF nema webhook podršku — samo polling. Zbog ugostiteljske teze ovaj modul više nije nosivi. |

---

### 4.18 Klijent-prvi UI (M19)

Ovaj odeljak definiše klijent-prvi UI površinu uvedenu u milestone M19. Prethodni feature-indeksiran UI (top-level `Fakture`, `Klijenti`, `Izveštaji`, `Pravila` u bočnom meniju sa globalnim listama filtriranim po klijentu) je **zamenjen** klijent-osa UI-om u kojem agencija prvo bira klijenta i pronalazi sve sposobnosti po klijentu unutar tog klijentskog workspace-a.

Pun UX obrazloženje živi u [`saldora-strategy-and-ux-redesign.md`](saldora-strategy-and-ux-redesign.md), Deo Treći. Ovaj odeljak hvata samo površinu na nivou zahteva.

#### FR-4.18.1 Pregled portfelja (`/pregled`)

| ID | FR-4.18.1 |
|----|-----------|
| **Opis** | Početni prikaz na nivou agencije. Mreža svih klijenata agencije, gde svaka kartica prikazuje indikatore zdravlja |
| **Indikatori (na startu)** | Fakture na čekanju za pregled, fakture blokirane za izvoz, recentnost aktivnosti (timestamp poslednje obrađene fakture) |
| **Indikatori (proširivi)** | Novi tipovi indikatora se priključuju kako se novi podaci pojavljuju (npr. zakasneli obrasci kada M20 isporuči) |
| **Akcija** | Svaka kartica linkuje na `/klijenti/{id}` (workspace pojedinačnog klijenta) |
| **Default ruta** | `/pregled` je default landing stranica nakon prijave za agencijske korisnike |

#### FR-4.18.2 Radna tabla klijenta (`/klijenti/{id}`)

| ID | FR-4.18.2 |
|----|-----------|
| **Opis** | Single-page površina za jednog klijenta. Header sa imenom klijenta, PIB-om, detaljima aktivnosti, mesečnom navigacijom |
| **Tabovi (na M19 merge)** | Hronologija (default), Fakture, Izveštaji, Pravila |
| **Pre-scoping** | Svaki tab je pre-scope-ovan na trenutnog klijenta; ugnežđene komponente lista imaju uklonjene kontrole filtera klijenta |
| **Proširivost** | Tabovi su rutabilne podsekcije; nove sposobnosti (obrasci, close checklist) sleću kao dodatni tabovi bez restrukturiranja shell-a |

#### FR-4.18.3 Hronologija tab

| ID | FR-4.18.3 |
|----|-----------|
| **Opis** | Default tab unutar klijentskog workspace-a. Renderuje događaje iz `client_events` (FR-4.12.5) za izabrani period |
| **Grupisanje** | Po danu, obrnuto hronološki |
| **Filtriranje** | Po tipu događaja (chip-ovi na vrhu taba) |
| **Click-through** | Klik na događaj otvara osnovni entitet (detalje fakture, detalje izvršenja pravila, detalje računovodstvene namere) |

#### FR-4.18.4 Fakture tab

Postojeća komponenta liste faktura ugnežđena u workspace klijenta, pre-scope-ovana na trenutnog klijenta. Kontrola filtera klijenta je sakrivena (implicitna je). Svi ostali filteri (raspon datuma, status, pretraga, dobavljač) ostaju.

#### FR-4.18.5 Izveštaji tab

Postojeća površina izveštaja (FR-4.13) ugnežđena u klijentski workspace, pre-scope-ovana na trenutnog klijenta. Izveštaji koriste `client_id` kao fiksni filter. Ugostiteljski obrasci (M20, odloženo) će sleteti kao dodatne grupacije unutar ovog taba.

#### FR-4.18.6 Pravila tab

Lista pravila povezanih sa ovim klijentom (preko `rule_client_associations`) plus pravila na nivou organizacije. CTA "Kreiraj pravilo za ovog klijenta" otvara editor pravila sa pre-popunjenom asocijacijom klijenta. Upravljanje pravilima na nivou organizacije ostaje pod stavkom `Pravila` u bočnom meniju.

#### FR-4.18.7 Struktura bočne trake (post-M19)

```
— Klijent radna tabla —
🏠 Pregled portfelja          (/pregled — default home)
👥 Klijenti                   (flat lista klijenata, brzi skok u workspace)

— Operacije agencije —
⚙️ Pravila                    (org-wide editor pravila)
📦 Arhiviranje                (periodne arhive za poreze/retenciju)
📁 Katalog proizvoda          (kanonički proizvodi, deljeni među klijentima)

— Pomoćno —
📊 Dashboard                  (globalna statistika, zadržana zasad)
🔧 Podešavanja
👤 Tim
💳 Naplata
```

Top-level stavke `Fakture` i `Izveštaji` su **uklonjene**. Obe su client-scoped i žive unutar workspace-a po klijentu.

#### FR-4.18.8 Politika koegzistencije

Saldora još nije deploy-ovana na klijente koji plaćaju. M19 redizajn isporučuje se kao **zamena**, ne paralelna površina. Stare feature stranice su dostupne iz novog shell-a samo tokom razvoja i uklanjaju se pre nego što M19 grana merge-uje.

---

### 4.19 Ugostiteljski zakonski obrasci (M20, odloženo)

> **Status:** Opseg je namerno TBD dok radna sesija sa stvarnim srpskim računovođom koji vodi ugostiteljske klijente ne proizvede dokument zahteva. Pravljenje ovih obrazaca samo iz čitanja zakona poznato proizvodi pogrešne kolone i pogrešne tokove rada.

Namerni sledeći sloj vrednosti, povrh postojeće OCR + product catalog osnove podataka, je generisanje zakonom propisanih srpskih ugostiteljskih obrazaca direktno iz ekstrahovanih podataka faktura:

| Obrazac | Srpski | Svrha | Izvor podataka |
|---------|--------|-------|----------------|
| **Kalkulacija** | Kalkulacija | Po proizvodu nabavna cena → marža → PDV → prodajna cena, regeneriše se kada se doda novi proizvod ili se dobavljačka cena promeni | `invoice_line_items` + `product_catalog` (selling_price, default_margin_pct) |
| **Šank lista** | Šank lista | Periodni inventar bara: primljena roba, prodata roba, zalihe na kraju | Stavke + prodajni podaci (akvizicija prodajnih podataka je deo otvorenog opsega) |
| **Cenovnik** | Cenovnik | Trenutni cenovnik / meni, mora se podudarati sa onim što se naplaćuje i mora biti javno izložen | `product_catalog.selling_price` |
| **KEP** | Knjiga evidencije prometa | Knjiga evidencije prometa — knjiga sve primljene robe i sve prodaje | Stavke + prodajni podaci |
| **Popis** | Popis | Periodni fizički popis sa procenom vrednosti na kraju perioda | Stanje zaliha izvedeno iz primljeno minus prodato (po periodu) |

#### Status osnove podataka (već u mestu)

- **Ekstrakcija stavki** sa popustom/poreskom osnovicom/količinom/jediničnom cenom/ukupno po redu (FR-4.3.2, FR-4.5.2).
- **Denormalizovana `invoice_line_items`** tabela popunjena post-OCR i pri izmenama (FR-4.13.1).
- **Katalog proizvoda** sa kanoničkim imenima, aliasima, kategorijama, prodajnim cenama, podrazumevanim maržama i pg_trgm fuzzy matching-om opisa stavki (Odeljak 4.15).
- **Per-line-item `product_id` FK** koji povezuje svaku ekstrahovanu stavku sa kanoničkim unosom u katalogu.

#### Otvorena pitanja (za sastanak sa računovođom)

1. Tačan skup obrazaca koje agencija mora po zakonu da proizvede za ugostiteljskog klijenta i koliko često.
2. Za svaki obrazac: tačne kolone / polja / formule koje zakon zahteva i bilo koji audit-trail zahtevi.
3. Izvor podataka za svaki obrazac — samo nabavna strana ili i prodajna?
4. Mesečni close workflow kako ga računovođe stvarno izvode, korak po korak.
5. Da li je integracija sa fiskalnim isečcima potrebna za KEP i kako agencija danas prima dnevne prodajne podatke.

#### Plan implementacije nakon izlaza sa sastanka

- Dodaci modela podataka (npr. per-client override marže proizvoda, entitet perioda).
- Generatori obrazaca (jedan Celery-friendly modul po zakonskom obrascu).
- Novi tabovi / sekcije unutar `Izveštaji` taba po klijentu.
- PDF + Excel export šabloni (Excel minimum; PDF verovatno takođe).

#### M21 — Close Checklist & Semantika perioda (dalje odloženo)

Entitet perioda sa close/lock semantikom, plus per-period checklist koji vodi mesec ugostiteljskog klijenta do završetka, sleće u M21. Oba zavise od poznatog skupa obrazaca i hvatanja close workflow-a sa sastanka. Ne otvaraju se issue-i dok M20 ne proizvede izlaz.

---

## 5. Nefunkcionalni zahtevi

### 5.1 Zahtevi performansi

| Zahtev | Specifikacija |
|--------|--------------|
| **Vreme učitavanja stranice** | < 2 sekunde za inicijalno učitavanje |
| **Vreme OCR obrade** | < 5 sekundi po stranici (pojedinačna stranica) |
| **Grupna obrada** | < 2 minuta za 50 dokumenata |
| **Vreme odziva API-ja** | < 200ms za endpointe bez obrade |
| **Istovremeni korisnici** | Podrška za 500 istovremenih korisnika |
| **Istovremena obrada** | Podrška za 100 istovremenih OCR poslova |

### 5.2 Zahtevi skalabilnosti

| Zahtev | Specifikacija |
|--------|--------------|
| **Horizontalno skaliranje** | API i worker servisi moraju se skalirati horizontalno |
| **Automatsko skaliranje** | Skaliranje na osnovu dubine reda i iskorišćenosti CPU-a |
| **Baza podataka** | Podrška za read replike za skaliranje čitanja |
| **Skladište** | Neograničen kapacitet za skladištenje dokumenata |

### 5.3 Zahtevi dostupnosti

| Zahtev | Specifikacija |
|--------|--------------|
| **SLA** | 99,9% mesečno vreme rada (isključujući planirano održavanje) |
| **Planirano održavanje** | Maksimalno 4 sata/mesečno, van radnog vremena |
| **Vreme oporavka** | < 1 sat za kritične kvarove |
| **Rezervna kopija podataka** | Dnevne automatske rezervne kopije, čuvanje 30 dana |

### 5.4 Bezbednosni zahtevi

| Zahtev | Specifikacija |
|--------|--------------|
| **Enkripcija podataka** | TLS 1.3 u prenosu, AES-256 u mirovanju |
| **Autentifikacija** | JWT sa bezbednom rotacijom refresh tokena |
| **Skladištenje lozinki** | Argon2id heširanje |
| **Upravljanje sesijama** | Bezbedni, HTTP-only kolačići |
| **Validacija ulaza** | Serverska validacija za sve ulaze |
| **SQL injekcija** | Samo parametrizovani upiti |
| **XSS prevencija** | Content Security Policy, enkodiranje izlaza |
| **CSRF zaštita** | CSRF zaštita bazirana na tokenima |

### 5.5 Zahtevi usklađenosti

| Zahtev | Specifikacija |
|--------|--------------|
| **ZZPL** | Potpuna usklađenost sa Zakonom o zaštiti podataka o ličnosti Republike Srbije |
| **GDPR** | Praćenje GDPR standarda kao referentnog okvira (Srbija kandidat za EU) |
| **Rezidencija podataka** | Podaci skladišteni u data centrima sa adekvatnim nivoom zaštite (EU/EEA) |
| **Čuvanje podataka** | Podesive politike čuvanja, minimum 10 godina za računovodstvena dokumenta |
| **Pravo na brisanje** | Podrška za potpuno brisanje podataka (uz zakonske izuzetke) |
| **Revizijski dnevnik** | Evidentiranje svih pristupa i modifikacija podataka |

### 5.6 Zahtevi upotrebljivosti

| Zahtev | Specifikacija |
|--------|--------------|
| **Pristupačnost** | WCAG 2.1 AA usklađenost |
| **Podrška pregledača** | Poslednje 2 verzije glavnih pregledača |
| **Mobilna podrška** | Responzivni dizajn, prilagođen za dodirne uređaje |
| **Jezik** | Srpski (primarni), engleski (sekundarni) |
| **Pismo** | Podrška za prebacivanje između ćirilice i latinice u korisničkom interfejsu |
| **Uvodni vodič** | Interaktivni vodič za nove korisnike |

### 5.7 Zahtevi pouzdanosti

| Zahtev | Specifikacija |
|--------|--------------|
| **Obrada grešaka** | Graciozna degradacija, korisniku prijatne poruke o greškama |
| **Integritet podataka** | Podrška za transakcije, bez delimičnih ažuriranja |
| **Tolerancija na greške** | Automatski ponovni pokušaj za prolazne greške |
| **Monitoring** | Praćenje zdravlja u realnom vremenu i upozoravanje |

---

## 6. Tehnološki stek

### 6.1 Frontend

| Komponenta | Tehnologija | Verzija | Svrha |
|-----------|------------|---------|-------|
| **Okvir** | Next.js | 15.x | React okvir sa App Router-om |
| **Jezik** | TypeScript | 5.x | Tipski bezbedan JavaScript |
| **Stilizovanje** | Tailwind CSS | 4.x | Utility-first CSS |
| **Upravljanje stanjem** | Zustand | 5.x | Lagano upravljanje stanjem |
| **Dohvatanje podataka** | TanStack Query | 5.x | Upravljanje serverskim stanjem |
| **Forme** | React Hook Form | 7.x | Rukovanje formama |
| **Validacija** | Zod | 3.x | Validacija šema |
| **Grafikoni** | Recharts | 2.x | Vizualizacija podataka |
| **Tabele** | TanStack Table | 8.x | Tabele podataka |
| **Otpremanje fajlova** | react-dropzone | 14.x | Drag & drop otpremanje |
| **PDF pregled** | react-pdf | 7.x | Pregled dokumenata |
| **Ikone** | Heroicons | 2.x | Biblioteka ikona |
| **Animacije** | Framer Motion | 11.x | Animacije |

### 6.2 Backend

| Komponenta | Tehnologija | Verzija | Svrha |
|-----------|------------|---------|-------|
| **Okvir** | FastAPI | 0.110.x | Asinhroni Python veb okvir |
| **Jezik** | Python | 3.12.x | Backend jezik |
| **ORM** | SQLAlchemy | 2.x | ORM za bazu podataka |
| **Migracije** | Alembic | 1.x | Migracije baze podataka |
| **Validacija** | Pydantic | 2.x | Validacija podataka |
| **Auth** | python-jose | 3.x | Rukovanje JWT-om |
| **Lozinka** | passlib[argon2] | 1.7.x | Heširanje lozinki |
| **HTTP klijent** | httpx | 0.27.x | Asinhroni HTTP klijent |
| **Red zadataka** | Celery | 5.x | Distribuirani red zadataka |
| **Broker poruka** | Redis | 7.x | Celery broker + keširanje |

### 6.3 AI/ML stek

| Komponenta | Tehnologija | Verzija | Svrha |
|-----------|------------|---------|-------|
| **Hosting modela** | Modal (serverless GPU) | — | dots.ocr je deploy-ovan na Modal sa A10G GPU-om i scale-to-zero (zamenjuje vLLM kontejner u klasteru); ~2 min hladan start, milisekunde topao |
| **Document AI** | dots.ocr | najnovija | Vizuelno-jezički model za objedinjenu detekciju rasporeda + OCR (~100 jezika, ćirilica/latinica) |
| **OCR klijent** | openai (Python) | 1.x | OpenAI-kompatibilan klijent za pozivanje Modal endpoint-a |
| **LLM ekstraktor** | Anthropic Claude (Haiku) | — | Transformacija OCR teksta u strukturirane stavke fakture (zaglavlja + linije) |
| **PDF obrada** | PyMuPDF | 1.24.x | Parsiranje PDF-a |
| **Obrada slika** | Pillow | 10.x | Manipulacija slikama |

**EasyOCR fallback uklonjen.** Predprocesiranje slike (deskewing/binarizacija/kontrast) je preskočeno za VLM put — dots.ocr radi bolje na originalnim slikama u boji.

### 6.4 Baza podataka

| Komponenta | Tehnologija | Verzija | Svrha |
|-----------|------------|---------|-------|
| **Primarna BP** | PostgreSQL | 16.x | Relaciona baza podataka |
| **Keš** | Redis | 7.x | Keširanje, sesije |
| **Pretraga** | PostgreSQL FTS | - | Pretraga punog teksta |

### 6.5 Infrastruktura

| Komponenta | Tehnologija | Svrha |
|-----------|------------|-------|
| **Container Runtime** | Docker | Kontejnerizacija |
| **Orkestracija** | docker-compose na jednom Hetzner CX32 VPS-u | Zamenjuje Kubernetes; jednostavnost u skladu sa veličinom proizvoda |
| **Reverse proxy / TLS** | Caddy | Automatski TLS sa Let's Encrypt; routing za FastAPI i Next.js |
| **Cloud provajder** | Hetzner (CX32) | Primarni VPS — FastAPI + Next.js + PostgreSQL + Redis + Celery worker |
| **GPU compute** | Modal (serverless) | dots.ocr scale-to-zero hosting (zamenjuje GPU sidecar u klasteru) |
| **Objektno skladište** | Cloudflare R2 (prod), MinIO (dev) | Skladištenje originalnih dokumenata i izvoznih ZIP-ova |
| **E-pošta** | Resend (jedini provajder) | Transakcioni e-mailovi (admin obaveštenja, reset lozinke, pozivnice) |
| **CDN** | Cloudflare | Statički resursi, DDoS zaštita |
| **DNS** | Cloudflare | Upravljanje DNS-om za saldora.rs |

### 6.6 DevOps i monitoring

| Komponenta | Tehnologija | Svrha |
|-----------|------------|-------|
| **CI/CD** | GitHub Actions | Kontinuirana integracija |
| **Container Registry** | GitHub Container Registry | Docker slike |
| **Monitoring** | Prometheus + Grafana | Metrike i kontrolne table |
| **Logovanje** | Loki | Agregacija logova |
| **Praćenje grešaka** | Sentry | Monitoring grešaka |
| **APM** | OpenTelemetry | Distribuirano praćenje |

### 6.7 Razvojni alati

| Komponenta | Tehnologija | Svrha |
|-----------|------------|-------|
| **Kvalitet koda** | ESLint, Ruff | Lintanje |
| **Formatiranje** | Prettier, Black | Formatiranje koda |
| **Testiranje** | Jest, Pytest | Jedinično testiranje |
| **E2E testiranje** | Playwright | End-to-end testiranje |
| **API dokumentacija** | OpenAPI/Swagger | API dokumentacija |

---

## 7. Dizajn baze podataka

### 7.1 Dijagram relacija entiteta

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│      users      │       │  organizations  │       │      teams      │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │──┐    │ id (PK)         │───────│ id (PK)         │
│ email           │  │    │ name            │       │ organization_id │
│ password_hash   │  │    │ slug            │       │ name            │
│ first_name      │  └───▶│ billing_email   │       │ created_at      │
│ last_name       │       │ plan_id (FK)    │◀──┐   └─────────────────┘
│ organization_id │───────│ created_at      │   │
│ role            │       └─────────────────┘   │
│ created_at      │                             │
│ last_login      │       ┌─────────────────┐   │
└─────────────────┘       │      plans      │   │
                          ├─────────────────┤   │
                          │ id (PK)         │───┘
                          │ name            │
                          │ price_monthly   │
                          │ price_yearly    │
                          │ invoice_limit   │
                          │ features (JSON) │
                          └─────────────────┘

┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│    invoices     │       │   line_items    │       │   companies     │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │───────│ id (PK)         │       │ id (PK)         │
│ organization_id │       │ invoice_id (FK) │       │ pib             │
│ user_id (FK)    │       │ description     │       │ mb              │
│ document_id(FK) │       │ quantity        │       │ name            │
│ status          │       │ unit_price      │       │ address         │
│ invoice_number  │       │ total           │       │ status          │
│ invoice_date    │       │ position        │       │ apr_data (JSON) │
│ due_date        │       └─────────────────┘       │ last_verified   │
│ seller_id (FK)  │─────────────────────────────────│ is_foreign      │
│ buyer_id (FK)   │─────────────────────────────────└─────────────────┘
│ subtotal        │
│ tax_rate        │       ┌─────────────────┐       ┌─────────────────┐
│ tax_amount      │       │    documents    │       │  api_keys       │
│ total_amount    │       ├─────────────────┤       ├─────────────────┤
│ currency        │       │ id (PK)         │       │ id (PK)         │
│ confidence      │       │ organization_id │       │ organization_id │
│ raw_data (JSON) │       │ original_name   │       │ user_id (FK)    │
│ created_at      │       │ storage_path    │       │ key_hash        │
│ updated_at      │       │ mime_type       │       │ name            │
└─────────────────┘       │ size_bytes      │       │ permissions     │
                          │ page_count      │       │ last_used       │
                          │ created_at      │       │ expires_at      │
                          └─────────────────┘       └─────────────────┘
```

### 7.2 Definicije tabela

#### 7.2.1 users
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    organization_id UUID REFERENCES organizations(id),
    role VARCHAR(20) NOT NULL DEFAULT 'operator',
    email_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE,

    CONSTRAINT valid_role CHECK (role IN ('admin', 'manager', 'operator', 'viewer'))
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_organization ON users(organization_id);
```

#### 7.2.2 organizations
```sql
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    billing_email VARCHAR(255),
    plan_id UUID REFERENCES plans(id),
    payment_provider_customer_id VARCHAR(255),  -- Paddle customer ID
    subscription_status VARCHAR(20),  -- 'pending' | 'trial' | 'active' | 'canceled' | 'expired' | NULL
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_organizations_slug ON organizations(slug);
```

**Semantika `subscription_status`:** vidi FR-4.1.5. Nove registracije su default `pending`; `require_role` zavisnost vraća 403 sa `subscription_pending_approval` dok je status `pending`. NULL je legacy vrednost koja se tretira kao `active` i backfilluje pri pristupu.

#### 7.2.3 invoices
```sql
CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    user_id UUID NOT NULL REFERENCES users(id),
    document_id UUID REFERENCES documents(id),

    status VARCHAR(20) NOT NULL DEFAULT 'processing',

    invoice_number VARCHAR(100),
    invoice_date DATE,
    due_date DATE,

    seller_id UUID REFERENCES companies(id),
    buyer_id UUID REFERENCES companies(id),

    subtotal DECIMAL(15, 2),
    tax_rate DECIMAL(5, 2),
    tax_amount DECIMAL(15, 2),
    total_amount DECIMAL(15, 2),
    currency VARCHAR(3) DEFAULT 'RSD',

    confidence_score DECIMAL(5, 2),
    raw_ocr_data JSONB,
    extracted_data JSONB,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_status CHECK (status IN ('processing', 'review', 'verified', 'exported', 'error'))
);

CREATE INDEX idx_invoices_organization ON invoices(organization_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_date ON invoices(invoice_date);
CREATE INDEX idx_invoices_seller ON invoices(seller_id);
CREATE INDEX idx_invoices_buyer ON invoices(buyer_id);
```

#### 7.2.4 companies
```sql
CREATE TABLE companies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pib VARCHAR(20) NOT NULL,  -- Dozvoljava duže PIB za strane entitete (EU VAT ID itd.)
    mb VARCHAR(8),
    name VARCHAR(255) NOT NULL,
    address TEXT,
    city VARCHAR(100),
    postal_code VARCHAR(10),
    country_code VARCHAR(2) DEFAULT 'RS',
    is_foreign BOOLEAN DEFAULT FALSE,
    status VARCHAR(20),
    apr_data JSONB,
    last_verified_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_pib_country UNIQUE (pib, country_code)
);

CREATE INDEX idx_companies_pib ON companies(pib);
CREATE INDEX idx_companies_name ON companies USING gin(to_tsvector('simple', name));
```

#### 7.2.5 documents
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    original_filename VARCHAR(255) NOT NULL,
    storage_path VARCHAR(500) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    size_bytes BIGINT NOT NULL,
    page_count INTEGER DEFAULT 1,
    checksum VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_documents_organization ON documents(organization_id);
```

#### 7.2.6 product_catalog

Kanonički unosi proizvoda za nabavnu inteligenciju (Odeljak 4.15). Popunjava se i upravlja se putem API-ja za katalog.

```sql
CREATE TABLE product_catalog (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    canonical_name  TEXT NOT NULL,
    unit_of_measure VARCHAR(20),
    category        VARCHAR(50),
    aliases         JSONB NOT NULL DEFAULT '[]',
    selling_price   NUMERIC(15, 2),
    default_margin_pct NUMERIC(5, 2),
    match_count     INTEGER NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX ix_pc_org_name ON product_catalog(organization_id, canonical_name);
CREATE INDEX ix_pc_org_id ON product_catalog(organization_id);
CREATE INDEX ix_pc_category ON product_catalog(category);
```

Napomena: tabela `invoice_line_items` sadrži nullable FK kolonu `product_id UUID REFERENCES product_catalog(id) ON DELETE SET NULL` (dodata u migraciji 0007).

#### 7.2.7 client_events

Append-only log događaja po klijentu, koji napaja Hronologija prikaz (FR-4.12.5, FR-4.18.3).

```sql
CREATE TABLE client_events (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    client_id       UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    event_type      VARCHAR(50) NOT NULL,  -- invoice_uploaded | invoice_verified | invoice_exported | accounting_intent_classified | rule_fired | client_assigned
    entity_type     VARCHAR(50),           -- npr. 'invoice', 'rule', 'accounting_intent'
    entity_id       UUID,
    metadata        JSONB NOT NULL DEFAULT '{}',
    created_by      UUID REFERENCES users(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_client_events_org_client ON client_events(organization_id, client_id, created_at DESC);
CREATE INDEX idx_client_events_type       ON client_events(event_type);
CREATE INDEX idx_client_events_entity     ON client_events(entity_type, entity_id);
```

#### 7.2.8 rule_client_associations

Per-client scoping za pravila automatizacije (FR-4.12.6).

```sql
CREATE TABLE rule_client_associations (
    rule_id     UUID NOT NULL REFERENCES automation_rules(id) ON DELETE CASCADE,
    client_id   UUID NOT NULL REFERENCES clients(id) ON DELETE CASCADE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (rule_id, client_id)
);

CREATE INDEX idx_rca_client ON rule_client_associations(client_id);
```

---

## 8. API specifikacija

### 8.1 Pregled API-ja

**Bazni URL:** `https://api.saldora.rs/v1`

**Autentifikacija:** Bearer token (JWT) ili API ključ

**Tip sadržaja:** `application/json`

**Ograničenja stope:**

| Plan | Zahtevi/minut | Zahtevi/dan |
|------|--------------|------------|
| Starter | 30 | 1.000 |
| Profesional | 100 | 10.000 |
| Enterprise | 500 | Neograničeno |

### 8.2 Endpointi za autentifikaciju

#### POST /auth/register
Registracija novog korisničkog naloga.

**Zahtev:**
```json
{
  "email": "korisnik@primer.com",
  "password": "SigurnaLozinka123",
  "first_name": "Marko",
  "last_name": "Petrović",
  "organization_name": "Računovodstvo Petrović"
}
```

**Odgovor (201 Created):**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "korisnik@primer.com",
  "organization_id": "660e8400-e29b-41d4-a716-446655440001",
  "message": "Verifikacioni e-mail poslat"
}
```

#### POST /auth/login
Autentifikacija korisnika i dobijanje tokena.

**Zahtev:**
```json
{
  "email": "korisnik@primer.com",
  "password": "SigurnaLozinka123"
}
```

**Odgovor (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

#### POST /auth/refresh
Osvežavanje pristupnog tokena.

**Zahtev:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

### 8.3 Endpointi za fakture

#### POST /invoices/upload
Otpremanje dokumenta fakture za obradu.

**Zahtev:** `multipart/form-data`

| Polje | Tip | Obavezno | Opis |
|-------|-----|----------|------|
| file | File | Da | Dokument fakture |
| priority | String | Ne | `normal` ili `high` |
| callback_url | String | Ne | Webhook URL |

**Odgovor (202 Accepted):**
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "status": "processing",
  "estimated_time": 5,
  "document_id": "880e8400-e29b-41d4-a716-446655440003"
}
```

#### GET /invoices/{id}
Preuzimanje detalja fakture.

**Odgovor (200 OK):**
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "status": "verified",
  "confidence_score": 94.5,
  "invoice_number": "2025-00042",
  "invoice_date": "2025-01-15",
  "due_date": "2025-02-15",
  "seller": {
    "pib": "123456789",
    "name": "Firma ABC d.o.o.",
    "address": "Bulevar Kralja Aleksandra 1, Beograd",
    "verified": true
  },
  "buyer": {
    "pib": "987654321",
    "name": "Kompanija XYZ d.o.o.",
    "address": "Cara Dušana 15, Novi Sad",
    "verified": true
  },
  "line_items": [
    {
      "description": "Usluge konsaltinga",
      "quantity": 10,
      "unit_price": 5000.00,
      "total": 50000.00
    }
  ],
  "subtotal": 50000.00,
  "tax_rate": 20.00,
  "tax_amount": 10000.00,
  "total_amount": 60000.00,
  "currency": "RSD",
  "document_url": "https://storage.saldora.rs/docs/...",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:05Z"
}
```

#### GET /invoices
Lista faktura sa filtriranjem.

**Parametri upita:**

| Parametar | Tip | Opis |
|-----------|-----|------|
| page | Integer | Broj stranice (podrazumevano: 1) |
| per_page | Integer | Stavki po stranici (podrazumevano: 20, maks: 100) |
| status | String | Filter po statusu |
| date_from | Date | Filter od datuma |
| date_to | Date | Filter do datuma |
| seller_pib | String | Filter po PIB-u prodavca |
| buyer_pib | String | Filter po PIB-u kupca |
| search | String | Pretraga punog teksta |
| sort | String | Polje za sortiranje |
| order | String | `asc` ili `desc` |

#### PATCH /invoices/{id}
Ažuriranje podataka fakture.

#### DELETE /invoices/{id}
Brisanje fakture i pridruženog dokumenta.

### 8.4 Endpointi za izvoz

#### POST /export
Izvoz faktura u zadatom formatu.

**Zahtev:**
```json
{
  "format": "xlsx",
  "invoice_ids": ["id1", "id2", "id3"],
  "template_id": "default",
  "options": {
    "include_line_items": true,
    "date_format": "DD.MM.YYYY"
  }
}
```

### 8.5 Endpointi za verifikaciju

#### GET /verify/pib/{pib}
Verifikacija PIB-a prema APR bazi podataka.

**Odgovor (200 OK):**
```json
{
  "pib": "123456789",
  "valid": true,
  "company": {
    "name": "Firma ABC d.o.o.",
    "address": "Bulevar Kralja Aleksandra 1",
    "city": "Beograd",
    "postal_code": "11000",
    "status": "active",
    "registration_date": "2015-03-20"
  },
  "verified_at": "2025-01-15T10:30:00Z",
  "source": "apr"
}
```

### 8.6 Odgovori o greškama

**Standardni format greške:**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Nevažeći ulazni podaci",
    "details": [
      {
        "field": "email",
        "message": "Nevažeći format e-pošte"
      }
    ]
  }
}
```

**Kodovi grešaka:**

| HTTP status | Kod | Opis |
|-------------|-----|------|
| 400 | VALIDATION_ERROR | Nevažeći podaci zahteva |
| 401 | UNAUTHORIZED | Nedostajući ili nevažeći token |
| 403 | FORBIDDEN | Nedovoljne dozvole |
| 404 | NOT_FOUND | Resurs nije pronađen |
| 409 | CONFLICT | Resurs već postoji |
| 422 | PROCESSING_ERROR | OCR obrada neuspešna |
| 429 | RATE_LIMITED | Previše zahteva |
| 500 | INTERNAL_ERROR | Serverska greška |

---

## 9. AI/ML komponente

### 9.1 Arhitektura OCR pipeline-a

dots.ocr je vizuelno-jezički model (VLM) koji izvodi **objedinjenu detekciju rasporeda i ekstrakciju teksta** u jednom prolazu. Pokreće se na **Modal** (serverless GPU) sa A10G uređajem i scale-to-zero (~2 min hladan start, milisekunde topao); poziva ga laki OCR radnik putem OpenAI-kompatibilnog chat completions API-ja. Prethodna arhitektura (vLLM HTTP server kao GPU sidecar u klasteru) je zamenjena Modal hosting-om.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        OCR processing pipeline                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────┐    ┌─────────────────────────────────────────────┐  │
│  │   Ulazni    │    │          vLLM Server (GPU sidecar)          │  │
│  │  dokument   │    │  ┌───────────────────────────────────────┐  │  │
│  │ (PDF/Slika) │    │  │  dots.ocr vizuelno-jezički model      │  │  │
│  └──────┬──────┘    │  │  (rednote-hilab/dots.ocr, 1,7B)      │  │  │
│         │           │  └───────────────────────────────────────┘  │  │
│         ▼           │  OpenAI-kompatibilan API (:8000/v1)         │  │
│  ┌─────────────┐    └──────────────────────┬──────────────────────┘  │
│  │ OCR Radnik  │                           │                         │
│  │ (Celery,    │    HTTP POST              │ Strukturirani           │
│  │  bez GPU)   │───▶/v1/chat/completions   │ JSON izlaz              │
│  │             │    (base64 slika +        │ (raspored +             │
│  │ openai      │     specijalni tokeni)    │  tekst + bbox)          │
│  │ Python      │◀──────────────────────────┘                         │
│  │ klijent     │                                                     │
│  └──────┬──────┘                                                     │
│         │                                                            │
│         ▼                                                            │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              dots.ocr strukturirani izlaz                    │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────────────┐ │    │
│  │  │Zaglavlje│  │  Tabela │  │ Podnožje│  │  Tekstualni     │ │    │
│  │  │ + tekst │  │  + HTML │  │ + tekst │  │  blokovi + MD   │ │    │
│  │  └────┬────┘  └────┬────┘  └────┬────┘  └────────┬────────┘ │    │
│  └───────┼────────────┼────────────┼────────────────┼──────────┘    │
│          └────────────┴────────────┴────────────────┘                │
│                                    │                                 │
│                                    ▼                                 │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              Ekstrakcija polja i NER (opciono)               │    │
│  │           (Pattern matching + spaCy za rubne slučajeve)      │    │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────────┐ │    │
│  │  │ PIB  │ │Datum │ │Iznos │ │Naziv │ │Adresa│ │ Br. fakt.│ │    │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────────┘ │    │
│  └──────────────────────────┬──────────────────────────────────┘    │
│                             │                                        │
│                             ▼                                        │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Post-obrada                               │    │
│  │      - Validacija polja      - Ocena pouzdanosti            │    │
│  │      - Normalizacija formata - Strukturiranje podataka      │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                    Rezervni put (ako je potreban)            │    │
│  │   Ako dots.ocr ne uspe → ručni pregled od strane korisnika  │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**Napomena:** Predprocesiranje slike (konverzija u sive tonove, ispravljanje nagiba, uklanjanje šuma) se **preskače** za dots.ocr — VLM modeli najbolje rade sa originalnim slikama u boji. Predprocesiranje se primenjuje samo pri korišćenju tradicionalnih OCR engine-a.

**Ključne prednosti dots.ocr VLM pristupa:**
- **Jedan model** obrađuje detekciju rasporeda + OCR (nije potreban zasebni LayoutParser)
- **Strukturirani izlaz** sa semantičkim regionima, bounding box-ovima i tekstom
- **~100 jezika** uključujući srpsku ćirilicu i latinicu
- **Očuvanje redosleda čitanja** za logičan tok dokumenta
- **Razumevanje tabela** sa HTML izlazom za strukturirane tabele
- **1,7B parametara** - kompaktan ali moćan
- **Sidecar arhitektura** — GPU izolovan u vLLM serveru, radnik je lak i bez GPU-a

### 9.2 Predprocesiranje slike

> **Status:** **Onemogućeno za VLM put.** dots.ocr radi najbolje na originalnim slikama u boji; tradicionalni preprocessing pipeline (deskewing/binarizacija/kontrast) je preskočen kad god je dots.ocr primarni engine. Sledeći detalji ostaju za referencu i potencijalnu upotrebu sa tradicionalnim OCR engine-ima.

**Modul:** `app/ml/preprocessing.py`

```python
class InvoicePreprocessor:
    """
    Predprocesira slike faktura za optimalne OCR performanse.
    """

    def process(self, image: np.ndarray) -> np.ndarray:
        """
        Primeni pipeline predprocesiranja.

        Koraci:
        1. Korekcija boje
        2. Ispravljanje nagiba
        3. Smanjenje šuma
        4. Binarizacija
        5. Normalizacija rezolucije
        """
        pass
```

**Operacije predprocesiranja:**

| Operacija | Opis | Biblioteka |
|----------|------|-----------|
| Ispravljanje nagiba | Korekcija rotacije dokumenta | OpenCV |
| Uklanjanje šuma | Uklanjanje artefakata šuma | OpenCV |
| Binarizacija | Konverzija u crno-belo | OpenCV (Otsu) |
| Poboljšanje kontrasta | Poboljšanje vidljivosti teksta | PIL/OpenCV |
| Skaliranje rezolucije | Normalizacija na 300 DPI | PIL |
| Uklanjanje okvira | Uklanjanje artefakata skenera | OpenCV |

### 9.3 OCR engine

**Primarni engine:** dots.ocr (hostovan na Modal-u)

dots.ocr je optimizovan za razumevanje dokumenata i pruža superiornu tačnost na strukturiranim dokumentima poput faktura, sa odličnom podrškom za ćirilično i latinično pismo. Pokreće se kao **Modal serverless GPU** funkcija (A10G, scale-to-zero), a OCR radnik je poziva putem OpenAI-kompatibilnog chat completions API-ja.

**Arhitektura:**
- **Modal endpoint**: `rednote-hilab/dots.ocr` model deploy-ovan kao Modal Python aplikacija sa GPU dekoratorom (A10G), scale-to-zero (~2 min hladan start, ~milisekunde topao)
- **ocr-worker**: Lak Python 3.12 Celery worker (na Hetzner CX32, bez GPU-a) koji poziva Modal endpoint putem `openai` Python klijenta
- Radnik šalje base64-kodirane slike sa `<|img|><|imgpad|><|endofimg|>` prefiksom u promptu

**Konfiguracija (promenljive okruženja):**
```
DOTS_OCR_SERVER_URL=https://<workspace>--saldora-dots-ocr.modal.run/v1
DOTS_OCR_MODEL_NAME=model
OCR_PRIMARY_ENGINE=dots
OCR_FALLBACK_ENGINE=none
```

**Strategija rezerve:** Ručni pregled od strane korisnika

Ne postoji automatski rezervni OCR engine. Ako dots.ocr ne uspe ili vrati rezultate niske pouzdanosti, faktura se označava za ručni pregled od strane krajnjeg korisnika. Ova projektna odluka je doneta jer alternativni OCR engine-i (npr. EasyOCR) pružaju nedovoljnu tačnost za srpske dokumente na ćirilici/latinici. **EasyOCR fallback je uklonjen.**

### 9.4 Analiza rasporeda dokumenta

**Model:** dots.ocr (integrisani VLM - nije potreban zasebni parser rasporeda)

dots.ocr pruža detekciju rasporeda kao deo svog objedinjenog vizuelno-jezičkog modela. Model daje strukturirani JSON sa semantičkom klasifikacijom regiona i bounding box-ovima.

**Detektovani regioni:**

| Tip regiona | Opis | Format izlaza |
|------------|------|--------------|
| Zaglavlje | Zaglavlje fakture (logo, info o firmi) | Markdown tekst |
| Info o prodavcu | Blok sa detaljima firme prodavca | Markdown tekst |
| Info o kupcu | Blok sa detaljima firme kupca | Markdown tekst |
| Tabela stavki | Tabela proizvoda/usluga | HTML tabela |
| Ukupni iznosi | Osnovica, porez, ukupno | Markdown tekst |
| Podnožje | Informacije u podnožju, potpisi | Markdown tekst |
| Metapodaci | Broj fakture, datumi | Markdown tekst |

### 9.5 Prepoznavanje imenovanih entiteta (NER)

**Model:** spaCy NER model za srpske fakture

**Tipovi entiteta:**

| Entitet | Primeri obrazaca | Validacija |
|---------|-----------------|-----------|
| PIB | `PIB: 123456789`, `ПИБ: 123456789` | 9-cifreni broj |
| MB | `МБ: 12345678`, `MB: 12345678` | 8-cifreni broj |
| DATE | `15.01.2025`, `15/01/2025` | Validan datum |
| AMOUNT | `45.000,00 RSD`, `45000.00` | Decimalni broj |
| INVOICE_NUM | `Faktura br: 2025-042` | Alfanumerički |
| COMPANY | `Firma ABC d.o.o.` | Naziv firme |
| ADDRESS | `Bulevar Kralja Aleksandra 1` | String adrese |
| TAX_RATE | `PDV 20%`, `ПДВ 20%` | 0%, 10%, 20% |

### 9.6 Ocena pouzdanosti

**Izračunavanje pouzdanosti:**

```python
def calculate_confidence(extracted_data: dict) -> float:
    """
    Izračunaj ukupnu ocenu pouzdanosti za ekstraktovane podatke.

    Faktori:
    - OCR pouzdanost karaktera (40%)
    - Uspeh validacije polja (30%)
    - Konzistentnost rasporeda (20%)
    - Unakrsna validacija (10%)
    """
    weights = {
        "ocr_confidence": 0.4,
        "field_validation": 0.3,
        "layout_consistency": 0.2,
        "cross_validation": 0.1
    }

    scores = {
        "ocr_confidence": calculate_ocr_confidence(extracted_data),
        "field_validation": validate_fields(extracted_data),
        "layout_consistency": check_layout(extracted_data),
        "cross_validation": cross_validate(extracted_data)
    }

    return sum(weights[k] * scores[k] for k in weights)
```

### 9.7 ML infrastruktura

**GPU zahtevi:**

| Komponenta | Hosting | Napomene |
|-----------|---------|----------|
| dots.ocr (rednote-hilab/dots.ocr, 1,7B parametara) | **Modal.com (A10G GPU)** | Scale-to-zero; ~2 min hladno pokretanje na prvi zahtev nakon mirovanja; kontejner ostaje topao 5 min nakon poslednjeg zahteva. Definicija u `infra/modal/dots_ocr.py`, deploy preko `modal deploy`. |
| OCR Radnik | Hetzner CX32 (Celery, samo CPU) | Lak Celery radnik koji poziva Modal endpoint preko OpenAI-kompatibilnog API-ja (`DOTS_OCR_SERVER_URL`). |

**Napomena:** dots.ocr zamenjuje potrebu za zasebnim Layout Parser + OCR Engine, smanjujući složenost infrastrukture. **Ne postoji EasyOCR rezerva** — neuspešan OCR rezultira ručnim pregledom od strane korisnika.

**Serviranje modela:**
- **Modal.com** (produkcija) — A10G GPU, scale-to-zero, OpenAI-kompatibilan endpoint. Drži VPS bez GPU-a (Hetzner CX32 je samo CPU).
- **Lokalni razvoj** — opciono `vllm/vllm-openai:latest` Docker kontejner za testiranje van Modal-a; ovo nije nosivi put i nije obavezno za rad lokalnog stack-a.

**Napomena o modelu:** Sistem koristi unapred trenirane modele (dots.ocr, spaCy) bez naknadnog treniranja na korisničkim podacima. Ovaj pristup eliminiše potrebu za prikupljanjem podataka za trening, upravljanjem saglasnošću i složenom MLOps infrastrukturom, dok istovremeno obezbeđuje zaštitu privatnosti korisnika.

**Opcije deployovanja:**

| Opcija | Trošak | Hladno pokretanje | Slučaj korišćenja |
|--------|--------|-------------------|--------------------|
| Lokalni vLLM (Docker) | $0 (sopstveni GPU) | Bez | Razvoj |
| Hetzner GEX44 | ~$200/mes. fiksno | Bez | Produkcija (10+ klijenata) |
| Google Cloud Run (L4 GPU) | ~$0.0002/sek. | 10-30s | Produkcija (skaliranje do nule) |
| Cerebrium Serverless | ~$0.0006/fakturi | 30-60s | Produkcija (rana faza) |

OCR radnik se povezuje na bilo koji OpenAI-kompatibilan API endpoint putem environment varijable `DOTS_OCR_SERVER_URL`. Prelaz između lokalnog, Cloud Run ili Cerebrium okruženja zahteva samo promenu environment varijable — bez izmena koda.

### 9.8 Praćenje kvaliteta ekstrakcije

Sistem MORA da prati kvalitet ekstrakcije putem logovanja korekcija korisnika, ali isključivo u svrhu monitoringa kvaliteta i analitike, NE za treniranje modela.

#### 9.8.1 Logovanje korekcija

**Svaka korekcija korisnika MORA biti evidentirana:**

```python
class CorrectionLog:
    """
    Prati svaku korekciju polja koju izvrši korisnik.
    Koristi se za monitoring kvaliteta i analitiku, ne za trening modela.
    """
    id: UUID
    invoice_id: UUID
    user_id: UUID
    field_name: str           # npr. "seller_pib", "total_amount"
    original_value: str       # Šta je model ekstraktovao
    corrected_value: str      # Šta je korisnik uneo
    model_confidence: float   # Pouzdanost u trenutku ekstrakcije
    correction_type: str      # "ocr_error", "ner_error", "layout_error", "business_logic"
    created_at: datetime
```

**Šema baze podataka:**
```sql
CREATE TABLE correction_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    invoice_id UUID NOT NULL REFERENCES invoices(id),
    user_id UUID NOT NULL REFERENCES users(id),
    field_name VARCHAR(50) NOT NULL,
    original_value TEXT,
    corrected_value TEXT NOT NULL,
    model_confidence DECIMAL(5, 2),
    correction_type VARCHAR(30),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_corrections_field ON correction_logs(field_name);
CREATE INDEX idx_corrections_date ON correction_logs(created_at);
```

#### 9.8.2 Kontrolna tabla kvaliteta

Sistem TREBALO BI da pruži kontrolnu tablu za praćenje tačnosti ekstrakcije po polju:

| Metrika | Opis | Prag za upozorenje |
|---------|------|--------------------|
| Stopa grešaka po polju | % faktura koje zahtevaju korekciju po polju | > 15% |
| Greške visoke pouzdanosti | Korekcije gde je pouzdanost modela > 90% | > 5% |
| Ponavljajuće greške | Isti obrazac greške na više dokumenata | > 10 pojavljivanja |

Ove metrike služe za identifikaciju sistemskih problema i informisanje tima o potencijalnim problemima sa kvalitetom ulaznih dokumenata ili konfiguracijom sistema.
## 10. Bezbednosni zahtevi

### 10.1 Bezbednost autentifikacije

| Zahtev | Implementacija |
|--------|---------------|
| Heširanje lozinki | Argon2id sa salt-om |
| JWT tokeni | RS256 potpisivanje, istek od 1 sata; algoritam fiksiran na HS256 (bez konfuzije algoritma) |
| Refresh tokeni | Bezbedni HTTP-only kolačići, istek od 7 dana |
| MFA | TOTP-bazirana 2FA (opciona) |
| Upravljanje sesijama | Sesije podržane u Redis-u |
| Zaštita od brute force | Ograničenje stope, zaključavanje naloga |
| Zaključavanje naloga | 5 neuspelih pokušaja → 15 min zaključavanja putem Redis-a |
| Crna lista tokena | Odjava poništava token putem Redis seta |
| Ograničenje stope | slowapi, ograničenja po planu (videti 8.1) |

### 10.2 Bezbednost podataka

| Zahtev | Implementacija |
|--------|---------------|
| Enkripcija u prenosu | TLS 1.3 |
| Enkripcija u mirovanju | AES-256 |
| Skladištenje dokumenata | Enkriptovani S3 bucket-i |
| Baza podataka | Enkriptovan PostgreSQL |
| Upravljanje ključevima | AWS KMS ili HashiCorp Vault |
| Maskiranje podataka | PII maskiranje u logovima |

### 10.3 Bezbednost aplikacije

| Zahtev | Implementacija |
|--------|---------------|
| Validacija ulaza | Serverska validacija (Pydantic) |
| SQL injekcija | Parametrizovani upiti (SQLAlchemy) |
| XSS prevencija | Enkodiranje izlaza, CSP zaglavlja |
| CSRF zaštita | CSRF baziran na tokenima |
| Otpremanje fajlova | Validacija tipa, ograničenja veličine, skeniranje virusa |
| API bezbednost | Ograničenje stope, rotacija API ključeva |
| Bezbednosna zaglavlja | X-Content-Type-Options, X-Frame-Options, Referrer-Policy, Permissions-Policy putem middleware-a |
| JWT algoritam | Fiksiran na HS256 (bez konfuzije algoritma) |
| PII maskiranje | Email i PIB vrednosti maskirane u logovima aplikacije |

### 10.4 Bezbednost infrastrukture

| Zahtev | Implementacija |
|--------|---------------|
| Mrežna bezbednost | VPC, bezbednosne grupe, WAF |
| DDoS zaštita | Cloudflare |
| Upravljanje tajnama | Environment varijable, Vault |
| Bezbednost kontejnera | Distroless slike, skeniranje |
| Kontrola pristupa | IAM uloge, princip najmanje privilegije |

### 10.5 Usklađenost

| Regulativa | Zahtevi |
|-----------|---------|
| ZZPL (primarni) | Potpuna usklađenost sa Zakonom o zaštiti podataka o ličnosti (Sl. glasnik RS, br. 87/2018). Ugovor o obradi podataka, lice za zaštitu podataka, politika privatnosti. ZZPL je primarni regulatorni okvir za zaštitu podataka u Republici Srbiji. |
| GDPR (referentni standard) | Usklađenost sa GDPR principima kao referentnim standardom. Srbija nije članica EU - GDPR se primenjuje kao smernica za najbolje prakse i pripremu za buduće članstvo. |
| PCI DSS | Ne čuvamo podatke o plaćanju. Paddle kao Merchant of Record obrađuje sve platne transakcije i preuzima odgovornost za usklađenost sa PCI DSS standardima. |

### 10.6 Pravni i regulatorni tokovi

Ovaj odeljak definiše tokove rada za pravnu usklađenost, ugovore o obradi podataka i zahteve revizije.

#### 10.6.1 Ugovor o obradi podataka (DPA)

**Za enterprise klijente:**

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Enterprise │    │   Prodaja   │    │  Pravno     │    │   Nalog     │
│   registr.  │───▶│   pregled   │───▶│  pregled    │───▶│   aktivan   │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
       │                  │                  │                  │
       ▼                  ▼                  ▼                  ▼
  DPA obavezan       Posebni uslovi?    Potpiši DPA      DPA skladišten
  Flag postavljen    Pregled SLA        Kontrapotpis     u Vault-u
```

**DPA šema baze podataka:**
```sql
CREATE TABLE data_processing_agreements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    version VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    signed_by_customer VARCHAR(255),
    signed_by_customer_at TIMESTAMP WITH TIME ZONE,
    signed_by_saldora VARCHAR(255),
    signed_by_saldora_at TIMESTAMP WITH TIME ZONE,
    document_url VARCHAR(500),
    custom_clauses JSONB,
    valid_from DATE,
    valid_until DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_dpa_status CHECK (status IN ('pending', 'customer_signed', 'active', 'expired', 'terminated'))
);
```

**Kontrolna lista zahteva za DPA:**
- [ ] Definisan odnos rukovalac/obrađivač podataka
- [ ] Navedeni podobrađivači sa obavezom obaveštavanja
- [ ] Specificirani periodi čuvanja podataka
- [ ] Dokumentovane procedure brisanja podataka
- [ ] Opisane bezbednosne mere
- [ ] Uključen vremenski rok za obaveštavanje o povredi (72 sata)
- [ ] Uključena prava revizije
- [ ] Opisani mehanizmi za prenos podataka

#### 10.6.2 Upravljanje saglasnošću

**Tipovi saglasnosti:**

| Tip saglasnosti | Opseg | Granularnost | Opozivo |
|-----------------|-------|-------------|---------|
| Osnovna obrada | OCR faktura, ekstrakcija podataka | Obavezno | Ne (neophodno za uslugu) |
| Analitika | Obrasci korišćenja, metrike performansi | Nivo organizacije | Da |
| Marketing | Novosti o proizvodu, bilteni | Nivo korisnika | Da |

**Šema baze podataka za saglasnosti:**
```sql
CREATE TABLE consent_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    user_id UUID NOT NULL REFERENCES users(id),
    consent_type VARCHAR(50) NOT NULL,
    granted BOOLEAN NOT NULL,
    granted_at TIMESTAMP WITH TIME ZONE,
    revoked_at TIMESTAMP WITH TIME ZONE,
    ip_address INET,
    user_agent TEXT,
    consent_text_version VARCHAR(20),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_consent_org ON consent_records(organization_id);
CREATE INDEX idx_consent_type ON consent_records(consent_type);
```

**Proces opoziva saglasnosti:**
1. Korisnik klikne "Opozovi saglasnost" u podešavanjima
2. Dijalog potvrde objašnjava posledice
3. Po potvrdi: postavlja se `revoked_at` vremenski žig
4. Sistem prestaje sa korišćenjem podataka u tu svrhu
5. E-mail potvrda poslat korisniku

#### 10.6.3 Izvoz za poresku inspekciju

**Zahtevi Poreske uprave Republike Srbije:**

Kada je poreska inspekcija zatražena, sistem MORA da pruži:

| Tip izvoza | Format | Sadržaj | Čuvanje |
|-----------|--------|---------|---------|
| Registar faktura | XML (eFaktura format) | Sve fakture u periodu | 10 godina |
| Arhiva dokumenata | ZIP sa PDF-ovima | Originalna otpremljena dokumenta | 10 godina |
| Revizijski trag | CSV/Excel | Sve akcije na fakturama | 10 godina |
| PDV rezime | PDF/Excel | PDV-PP razrada | 10 godina |

**Tok izvoza za inspekciju:**

```
Admin → Izveštaji → Izvoz za inspekciju
┌─────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  Izvoz podataka za poresku inspekciju                               │
│                                                                      │
│  Period:  [01.01.2024] do [31.12.2024]                              │
│                                                                      │
│  Sadržaj izvoza:                                                    │
│  ☑ Registar faktura (XML)                                          │
│  ☑ Originalna dokumenta (PDF)                                      │
│  ☑ Revizorski trag (CSV)                                           │
│  ☑ PDV pregled (Excel)                                             │
│                                                                      │
│  Format: [ZIP arhiva]                                               │
│                                                                      │
│  ⚠ Ovaj izvoz će biti evidentiran u revizorskom tragu.             │
│                                                                      │
│  [Generiši izvoz]                                                   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

**XML format izvoza (kompatibilan sa eFaktura):**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<RegistarFaktura xmlns="urn:saldora:export:v1">
  <Zaglavlje>
    <Organizacija>
      <Naziv>Računovodstvo Petrović d.o.o.</Naziv>
      <PIB>123456789</PIB>
      <MB>12345678</MB>
    </Organizacija>
    <PeriodOd>2024-01-01</PeriodOd>
    <PeriodDo>2024-12-31</PeriodDo>
    <DatumIzvoza>2025-01-15T10:30:00</DatumIzvoza>
    <BrojFaktura>1542</BrojFaktura>
  </Zaglavlje>
  <Fakture>
    <Faktura id="inv-001">
      <BrojFakture>2024-0001</BrojFakture>
      <DatumFakture>2024-01-15</DatumFakture>
      <DatumValute>2024-02-15</DatumValute>
      <Prodavac>
        <Naziv>Dobavljač ABC d.o.o.</Naziv>
        <PIB>987654321</PIB>
      </Prodavac>
      <Kupac>
        <Naziv>Računovodstvo Petrović d.o.o.</Naziv>
        <PIB>123456789</PIB>
      </Kupac>
      <Osnovica>100000.00</Osnovica>
      <PDV stopa="20">20000.00</PDV>
      <Ukupno>120000.00</Ukupno>
      <Valuta>RSD</Valuta>
      <DokumentRef>doc-uuid-here</DokumentRef>
    </Faktura>
    <!-- Više faktura... -->
  </Fakture>
</RegistarFaktura>
```

**Šema za izvoz revizije:**
```sql
CREATE TABLE audit_exports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id),
    requested_by UUID NOT NULL REFERENCES users(id),
    export_type VARCHAR(50) NOT NULL,
    date_from DATE NOT NULL,
    date_to DATE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    file_path VARCHAR(500),
    file_size_bytes BIGINT,
    invoice_count INTEGER,
    reason TEXT,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_export_status CHECK (status IN ('pending', 'processing', 'ready', 'downloaded', 'expired'))
);
```

#### 10.6.4 Čuvanje i brisanje podataka

**Periodi čuvanja:**

| Tip podataka | Period čuvanja | Pravni osnov |
|-------------|---------------|-------------|
| Podaci o fakturama | 10 godina | Zakon o računovodstvu RS |
| Originalna dokumenta | 10 godina | Zakon o računovodstvu RS |
| Korisnički nalozi | Aktivni + 2 godine | Poslovna potreba |
| Revizijski dnevnici | 7 godina | Usklađenost |
| Dnevnici korekcija | 3 godine | Praćenje kvaliteta |
| Podaci o sesijama | 30 dana | Tehnička potreba |
| Privremeni fajlovi | 24 sata | Obrada |

**Pravo na brisanje (ZZPL Član 30):**

```
Zahtev korisnika → Validacija → Delimično brisanje → Potvrda
     │              │              │                │
     ▼              ▼              ▼                ▼
  Putem e-maila  Provera da li  Briše se:         E-mail poslat
  ili u aplikac. je zakonski     - Podaci profila  sa potvrdom
                 obavezno        - Podešavanja     šta je obrisano
                 čuvati          - Podaci sesije   i šta je
                                 Čuva se:          zadržano
                                 - Podaci faktura  (sa razlogom)
                                   (zakonski zah.)
```

**Šema zahteva za brisanje:**
```sql
CREATE TABLE deletion_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    organization_id UUID REFERENCES organizations(id),
    request_type VARCHAR(30) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    data_categories JSONB,
    retained_categories JSONB,
    processed_by UUID REFERENCES users(id),
    processed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT valid_deletion_status CHECK (status IN ('pending', 'processing', 'completed', 'rejected'))
);
```

#### 10.6.5 Obaveštavanje o povredi podataka

**Vremenski okvir reagovanja na povredu:**

| Vremenski okvir | Akcija | Odgovornost |
|----------------|--------|-------------|
| 0-4 sata | Detekcija incidenta, inicijalna procena | Inženjering |
| 4-24 sata | Analiza uticaja, obustavljanje | Bezbednost + Pravno |
| 24-72 sata | Obavesti Poverenika (srpski organ za zaštitu podataka) ako je potrebno | Pravno |
| 24-72 sata | Obavesti pogođene korisnike ako postoji visok rizik | Pravno + Podrška |
| 72+ sati | Remedijacija, post-mortem | Svi timovi |

**Šablon obaveštenja o povredi:**
```
Obaveštenje o bezbednosnom incidentu

Poštovani [Ime],

Obaveštavamo vas da je [datum] došlo do bezbednosnog incidenta
koji je mogao uticati na vaše podatke.

Šta se desilo:
[Opis incidenta]

Koji podaci su mogli biti ugroženi:
[Lista tipova podataka]

Šta smo preduzeli:
[Preduzete mere]

Šta vi možete preduzeti:
[Preporuke za korisnika]

Kontakt za dodatna pitanja:
privacy@saldora.rs

S poštovanjem,
Saldora Tim
```

### 10.7 Revizija i logovanje

**Evidentirani događaji:**
- Događaji autentifikacije (prijava, odjava, neuspeli pokušaji)
- Pristup podacima (čitanje, kreiranje, ažuriranje, brisanje)
- Administrativne akcije
- API pristup
- Bezbednosni događaji

**Čuvanje logova:** Minimum 12 meseci

---

## 11. Arhitektura deployovanja

### 11.1 Produkciono okruženje (jednomašinski Hetzner CX32)

> **Promena u v4.0:** Kubernetes je zamenjen jedinstvenim Hetzner CX32 VPS-om sa docker-compose-om. Veličina proizvoda (jedna do nekoliko desetina agencija u prvoj fazi) ne opravdava operativni overhead k8s-a. GPU rad za dots.ocr je premešten na Modal (serverless).

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Internet                                     │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      Cloudflare (CDN + WAF + DNS)                   │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│           Hetzner CX32 VPS (jedan host, docker-compose)             │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Caddy (reverse proxy, automatski TLS sa Let's Encrypt)       │  │
│  └─────────────┬───────────────────────────────────┬─────────────┘  │
│                │                                   │                │
│                ▼                                   ▼                │
│  ┌──────────────────────┐              ┌──────────────────────┐    │
│  │  Next.js (web)       │              │  FastAPI (api)       │    │
│  │  saldora.rs          │              │  api.saldora.rs      │    │
│  └──────────────────────┘              └──────────┬───────────┘    │
│                                                    │                │
│                                                    ▼                │
│                                ┌──────────────────────────────┐    │
│                                │  Celery worker (CPU)         │    │
│                                │  poziva Modal preko HTTP-a   │    │
│                                └──────────┬───────────────────┘    │
│                                           │                        │
│  ┌──────────────┐  ┌──────────────┐       │                        │
│  │  PostgreSQL  │  │  Redis       │◀──────┘                        │
│  │  16          │  │  7 (broker)  │                                │
│  └──────────────┘  └──────────────┘                                │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────┐                ┌─────────────────────────────┐
│  Modal (serverless)  │                │  Cloudflare R2              │
│  dots.ocr (A10G)     │                │  Originalni dokumenti, ZIP  │
│  scale-to-zero       │                │  arhive                     │
└──────────────────────┘                └─────────────────────────────┘
```

### 11.2 docker-compose servisi

| Servis | Slika | Svrha |
|--------|-------|-------|
| `caddy` | `caddy:2` | Reverse proxy + automatski TLS |
| `web` | `ghcr.io/saldora/web:latest` | Next.js frontend |
| `api` | `ghcr.io/saldora/api:latest` | FastAPI |
| `worker` | `ghcr.io/saldora/api:latest` (`celery worker`) | Celery worker (OCR + ekstrakcija + izvoz) |
| `beat` | `ghcr.io/saldora/api:latest` (`celery beat`) | Zakazani zadaci |
| `postgres` | `postgres:16` | Primarna baza |
| `redis` | `redis:7-alpine` | Broker + keš |

> **Modal** se ne pokreće lokalno; deploy se vrši zasebno (`modal deploy`) i `worker` ga poziva preko HTTPS-a.

### 11.3 CI/CD pipeline

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Commit    │───▶│    Build    │───▶│    Test     │───▶│   Deploy    │
│   na main   │    │   i Lint    │    │   Suite     │    │  Staging    │
└─────────────┘    └─────────────┘    └─────────────┘    └──────┬──────┘
                                                                │
                                                                ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Monitoring │◀───│   Deploy    │◀───│  Odobrenje  │◀───│  E2E testovi│
│  i upozor.  │    │    Prod     │    │  (manuelno) │    │  (Staging)  │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

**GitHub Actions tok rada:**

```yaml
name: Deploy
on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build and push Docker images
        run: |
          docker build -t ghcr.io/saldora/web:${{ github.sha }} ./apps/web
          docker push ghcr.io/saldora/web:${{ github.sha }}
          docker build -t ghcr.io/saldora/api:${{ github.sha }} ./apps/api
          docker push ghcr.io/saldora/api:${{ github.sha }}

  test:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Run tests
        run: |
          npm test
          pytest tests/

  deploy-prod:
    needs: test
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: SSH to Hetzner CX32 and pull/restart
        run: |
          ssh deploy@saldora.rs "cd /srv/saldora && docker compose pull && docker compose up -d"

  deploy-modal:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Deploy dots.ocr to Modal
        run: modal deploy modal_app.py
```

### 11.4 Monitoring stek

| Komponenta | Alat | Svrha |
|-----------|------|-------|
| Metrike | Prometheus | Metrike vremenskih serija |
| Kontrolne table | Grafana | Vizualizacija |
| Logovanje | Loki | Agregacija logova |
| Praćenje | Jaeger | Distribuirano praćenje |
| Upozoravanje | Alertmanager | Rutiranje upozorenja |
| Praćenje grešaka | Sentry | Monitoring grešaka |

**Ključne metrike:**
- Latencija zahteva (p50, p95, p99)
- Stopa grešaka
- Vreme OCR obrade
- Dubina reda
- Iskorišćenost GPU-a
- Pool konekcija baze podataka

---

## 12. Integracije sa spoljnim sistemima

### 12.1 APR integracija (Agencija za privredne registre)

**Pristup:** APR API (komercijalni ugovor ili licencirani posrednik)

**Napomena:** APR ne pruža besplatan javni API za programski pristup. Pristup podacima zahteva:
- Komercijalni ugovor direktno sa APR-om, ili
- Korišćenje licenciranog posrednika (npr. DataCentric, Bisnode/Dun & Bradstreet za srpsko tržište)

Sistem MORA biti dizajniran sa apstrakcijskim slojem koji omogućava zamenu APR provajdera bez značajnih izmena koda.

**Korišćenje:**
- PIB verifikacija
- Pretraga informacija o firmi
- Validacija poslovnog statusa

**Strategija keširanja:**
- Keširanje odgovora na 24 sata
- Osvežavanje u pozadini za često pristupane PIB-ove

### 12.2 Integracija plaćanja (Paddle)

**Zašto Paddle (ne Stripe):** Paddle funkcioniše kao Merchant of Record (MoR), što znači da Paddle upravlja svim platnim transakcijama, PDV obavezama i poreskom usklađenošću globalno, u ime Saldore. Ovo je kritično za srpsko tržište jer:
- Paddle preuzima odgovornost za obračun i naplatu PDV-a u svim jurisdikcijama
- Nije potreban lokalni merchant nalog u Srbiji
- Pojednostavljeno finansijsko izveštavanje - jedna uplata od Paddle-a umesto hiljada pojedinačnih transakcija
- Automatska usklađenost sa poreskim propisima za digitalne usluge u EU i globalno

**Korišćene funkcionalnosti:**
- Paddle Checkout za pretplate
- Paddle Billing za upravljanje pretplatama i naplatom
- Webhooks za događaje pretplata
- Automatsko generisanje faktura za krajnje korisnike
- Upravljanje PDV-om za SaaS u EU i Srbiji

**Webhook događaji:**
- `subscription.created` - Nova pretplata kreirana
- `subscription.updated` - Pretplata ažurirana (promena plana, itd.)
- `subscription.canceled` - Pretplata otkazana
- `transaction.completed` - Transakcija uspešno završena
- `transaction.payment_failed` - Neuspelo plaćanje

**Obrada webhook-ova:**

```python
async def handle_paddle_webhook(payload: dict, signature: str):
    """
    Obrada Paddle webhook događaja.
    """
    # 1. Verifikuj potpis webhook-a
    if not verify_paddle_signature(payload, signature):
        raise HTTPException(401, "Nevažeći potpis")

    event_type = payload.get("event_type")

    match event_type:
        case "subscription.created":
            # Nova pretplata - aktiviraj plan
            await activate_subscription(
                paddle_subscription_id=payload["data"]["id"],
                customer_id=payload["data"]["customer_id"],
                plan=payload["data"]["items"][0]["price"]["product_id"]
            )

        case "subscription.canceled":
            # Otkazana pretplata - zakaži deaktivaciju
            await schedule_deactivation(
                paddle_subscription_id=payload["data"]["id"],
                effective_date=payload["data"]["scheduled_change"]["effective_at"]
            )

        case "transaction.payment_failed":
            # Neuspelo plaćanje - obavesti korisnika
            await notify_payment_failure(
                customer_id=payload["data"]["customer_id"]
            )

    return {"status": "processed"}
```

### 12.3 Servis e-pošte (Resend)

> **Promena u v4.0:** Resend je jedini provajder e-pošte. Reference na SendGrid u starijim verzijama nisu više aktuelne.

**Transakcione e-poruke:**
- Admin obaveštenje o novoj registraciji (FR-4.1.5; šalje se na adresu iz `ADMIN_EMAIL`)
- Pozivnice za tim (FR-4.1.6)
- Verifikacija e-pošte
- Resetovanje lozinke
- Obrada fakture završena
- Obaveštenja o pretplati (Paddle webhook hook-ovi)

### 12.4 Skladištenje (Cloudflare R2 prod, MinIO dev)

**Bucket-i:**
- `saldora-documents` (R2 prod) — Otpremljene fakture
- `saldora-exports` (R2 prod) — Generisani izvozi
- `saldora-backups` (R2 prod) — Rezervne kopije baze
- MinIO se koristi u dev okruženju za S3-kompatibilan API bez troška R2-a

**Konvencija ključeva objekata:**
Dokumenta su organizovana po organizaciji radi multi-tenant izolacije:
```
organizations/{organization_id}/invoices/{invoice_id}/original.{ext}
```

**Pravila životnog ciklusa:**
- Dokumenta: čuvanje 10 godina (prema Zakonu o računovodstvu, Sl. glasnik RS, br. 73/2019)
- Izvozi: automatsko brisanje posle 30 dana
- Rezervne kopije: čuvanje 90 dana

### 12.5 MiniMax integracija

MiniMax (minimax.rs) je najkorišćeniji cloud računovodstveni softver u Srbiji. Saldora se integriše sa MiniMax-om putem XML izvoza i direktnog REST API slanja.

#### 12.5.1 MiniMax XML izvoz

Generiše XML fajl kompatibilan sa MiniMax-ovim alatom za uvoz:
- **Stranke** (Partneri): Deduplicirani prodavci po PIB-u — Sifra (PIB), Naziv, DavcnaStevilka, Naslov, Posta
- **Temeljnice** (Nalozi za knjiženje): Generisani iz `accounting_intent.suggested_konta` — GlavaTemeljnice (datum, partner, referenca), VrsticeTemeljnice (konto + duguje/potražuje iznosi), DDV (stavke PDV-a)

Dostupno kao `minimax_xml` format u POST `/api/v1/export`.

#### 12.5.2 MiniMax REST API integracija

Direktno slanje faktura u MiniMax putem REST API-ja:
- **Autentifikacija:** OAuth 2.0 — POST `https://moj.minimax.rs/RS/AUT/OAuth20/Token`
- **Slanje primljenih faktura:** POST `/api/orgs/{orgId}/receivedinvoices`
- **Upravljanje kupcima:** Pretraga po PIB-u, kreiranje ako ne postoji
- **Pretraga valuta:** Dobijanje ID valute po ISO kodu
- Keširanje tokena sa automatskim osvežavanjem na 401

#### 12.5.3 Konfiguracija

Kredencijali po organizaciji čuvani u tabeli `minimax_configs`:
- `client_id`, `client_secret` — OAuth kredencijali aplikacije
- `username`, `password` — MiniMax korisnički kredencijali
- `minimax_org_id` — MiniMax ID organizacije (integer)
- `is_active` — Aktiviranje/deaktiviranje integracije
- `last_sync_at` — Vreme poslednjeg uspešnog slanja

**API endpointi:** GET/PUT/PATCH `/api/v1/export/minimax/config`

#### 12.5.4 Referenca API polja MiniMax (RS)

Nazivi polja i ID-ovi validirani prema MiniMax RS Swagger API specifikaciji:

**Zemlja i valuta (Srbija):**
- ID zemlje: 3 (Kod: "RS", Naziv: "Republika Srbija")
- ID valute: 2 (Kod: "RSD")

**Obavezna polja ReceivedInvoice:**
| API polje | Izvor | Napomena |
|-----------|-------|----------|
| DocumentReference | invoice_number | Originalni broj fakture (NE InvoiceNumber) |
| Customer | {ID: customer_id} | FK referenca |
| Currency | {ID: 2} | RSD podrazumevano |
| PaymentType | "N" | N=Neplaćen, D=Dospeo, Z=Zatvoreno, P=Plaćen, R=Rata |
| DateIssued | invoice_date | ISO datetime |
| DateTransaction | invoice_date | |
| DateDue | due_date | |
| DateReceived | invoice_date | |
| InvoiceAmount | total_amount | Zaokruženo na 2 decimale |
| InvoiceAmountDomesticCurrency | total_amount | Mora biti jednako InvoiceAmount za RSD |

**Obavezna polja pri kreiranju kupca:**
| Polje | Vrednost |
|-------|----------|
| Country | {ID: 3} |
| CountryName | "Republika Srbija" |
| Currency | {ID: 2} |
| SubjectToVAT | "D" (ne "Y") |
| PostalCode | Obavezno, neprazno |

**Mapiranje PDV stopa:**
| Srpska stopa | MiniMax VatRateId | Kod |
|-------------|-------------------|-----|
| 20% | 4 | S |
| 10% | 5 | Z |
| 8% | 3 | P |
| 0% | 1 | N |

### 12.6 SEF integracija (eFaktura) — deprioritetizovano

Deprioritizovano. SEF nema webhook podršku — samo polling. Zbog ugostiteljske teze, ovaj modul nije više nosivi. Prethodna detaljna specifikacija (podešavanje konekcije, sinhronizacija ulaznih i izlaznih faktura, polling statusa, hibridna obrada SEF + OCR, SEF inbox UI, obrada grešaka i tabele `sef_connections` / `sef_invoices`) uklonjena je iz ove verzije SRS-a. Ako se SEF rad pokrene ponovo, specifikacija će biti vraćena iz istorije verzionisanja (SRS v3.2 i ranije) umesto da se održava kao mrtav tekst ovde.

Pridružene tabele `sef_connections` i `sef_invoices` nisu nikada izgrađene i nisu prisutne u šemi.

### 12.7 NBS integracija (Narodna banka Srbije)

Sistem TREBALO BI da integriše kursnu listu Narodne banke Srbije za konverziju stranih valuta u RSD.

#### 12.7.1 Pregled

NBS objavljuje dnevni srednji kurs za sve valute koje se trguju na deviznom tržištu. Kursna lista se ažurira svakog radnog dana i dostupna je putem javnog API-ja.

**Korišćenje:**
- Prikaz RSD ekvivalenta za fakture u stranim valutama (EUR, USD, CHF, GBP)
- Konverzija iznosa faktura denominiranih u stranoj valuti u RSD
- Korišćenje srednjeg kursa NBS na dan fakture
- Arhiviranje kursa korišćenog pri konverziji za revizorske svrhe

#### 12.7.2 API pristup

**API endpoint:** `https://nbs.rs/kursnaListaMod498/kursnaLista`

**Napomena:** NBS pruža javni API za kursnu listu koji je besplatan za korišćenje. API vraća kursnu listu u XML ili JSON formatu.

**Konfiguracija:**

```json
{
  "nbs_exchange_rates": {
    "api_url": "https://nbs.rs/kursnaListaMod498/kursnaLista",
    "cache_ttl_hours": 24,
    "default_currency": "RSD",
    "supported_currencies": ["EUR", "USD", "CHF", "GBP"],
    "fallback_on_holiday": true
  }
}
```

#### 12.7.3 Strategija keširanja

- Kursna lista se kešira na 24 sata
- Za neradne dane (vikendi, praznici) koristi se poslednja dostupna kursna lista
- Keš se osvežava svakog radnog dana u 08:30 (NBS objavljuje kursnu listu do 08:00)
- U slučaju nedostupnosti NBS API-ja, koristi se poslednja keširana kursna lista

#### 12.7.4 Primena

**Konverzija za fakture u stranoj valuti:**

```python
async def get_exchange_rate(currency: str, date: date) -> Decimal:
    """
    Preuzmi srednji kurs NBS za zadatu valutu i datum.
    """
    # 1. Proveri keš
    cached_rate = await cache.get(f"nbs_rate:{currency}:{date}")
    if cached_rate:
        return Decimal(cached_rate)

    # 2. Proveri bazu podataka
    db_rate = await db.query(
        ExchangeRate,
        where=and_(
            ExchangeRate.currency == currency,
            ExchangeRate.rate_date == date
        )
    )
    if db_rate:
        await cache.set(f"nbs_rate:{currency}:{date}", str(db_rate.middle_rate), ttl=86400)
        return db_rate.middle_rate

    # 3. Preuzmi sa NBS API-ja
    rate = await nbs_api.fetch_rate(currency, date)
    if rate:
        await save_exchange_rate(currency, date, rate)
        return rate.middle_rate

    # 4. Fallback: koristi poslednju poznatu kursnu listu
    latest_rate = await get_latest_known_rate(currency)
    return latest_rate.middle_rate if latest_rate else None


async def convert_to_rsd(amount: Decimal, currency: str, invoice_date: date) -> dict:
    """
    Konvertuj iznos iz strane valute u RSD po kursu NBS.
    """
    if currency == "RSD":
        return {"rsd_amount": amount, "exchange_rate": Decimal("1"), "rate_date": invoice_date}

    rate = await get_exchange_rate(currency, invoice_date)
    if not rate:
        return {"rsd_amount": None, "exchange_rate": None, "error": "Kurs nedostupan"}

    rsd_amount = (amount * rate).quantize(Decimal("0.01"))
    return {
        "rsd_amount": rsd_amount,
        "exchange_rate": rate,
        "rate_date": invoice_date,
        "source": "NBS srednji kurs"
    }
```

#### 12.7.5 Šema baze podataka

```sql
CREATE TABLE exchange_rates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    currency VARCHAR(3) NOT NULL,
    rate_date DATE NOT NULL,

    -- Kursevi
    buying_rate DECIMAL(15, 6),
    middle_rate DECIMAL(15, 6) NOT NULL,
    selling_rate DECIMAL(15, 6),

    -- Jedinica (npr. 1 EUR = X RSD, ali 100 JPY = X RSD)
    unit INTEGER NOT NULL DEFAULT 1,

    -- Metapodaci
    source VARCHAR(20) NOT NULL DEFAULT 'NBS',
    fetched_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    CONSTRAINT unique_currency_date UNIQUE (currency, rate_date)
);

CREATE INDEX idx_exchange_rates_currency ON exchange_rates(currency);
CREATE INDEX idx_exchange_rates_date ON exchange_rates(rate_date);
CREATE INDEX idx_exchange_rates_lookup ON exchange_rates(currency, rate_date DESC);
```

**Celery periodični zadatak za ažuriranje kursne liste:**

```python
# Celery beat konfiguracija
CELERY_BEAT_SCHEDULE = {
    "fetch-nbs-exchange-rates": {
        "task": "fetch_nbs_exchange_rates",
        "schedule": crontab(hour=8, minute=30, day_of_week="1-5"),  # Radnim danima u 08:30
    },
}

@celery_app.task(name="fetch_nbs_exchange_rates")
async def fetch_nbs_exchange_rates():
    """
    Preuzmi dnevnu kursnu listu NBS-a i sačuvaj u bazu podataka.
    """
    today = date.today()

    for currency in ["EUR", "USD", "CHF", "GBP"]:
        try:
            rate_data = await nbs_api.fetch_rate(currency, today)
            if rate_data:
                await db.upsert(ExchangeRate(
                    currency=currency,
                    rate_date=today,
                    buying_rate=rate_data.buying_rate,
                    middle_rate=rate_data.middle_rate,
                    selling_rate=rate_data.selling_rate,
                    unit=rate_data.unit,
                    source="NBS"
                ))
                # Ažuriraj keš
                await cache.set(
                    f"nbs_rate:{currency}:{today}",
                    str(rate_data.middle_rate),
                    ttl=86400
                )
        except Exception as e:
            logger.error(f"Greška pri preuzimanju kursa za {currency}: {e}")
```
## 13. Zahtevi korisnickog interfejsa

### 13.1 Dizajn sistem

**Paleta boja:**
- Primarna: Violet (#7c3aed)
- Sekundarna: Indigo (#6366f1)
- Uspeh: Emerald (#10b981)
- Upozorenje: Amber (#f59e0b)
- Greska: Red (#ef4444)
- Pozadina: White (#ffffff)
- Tekst: Gray-900 (#0f172a)

**Tipografija:**
- Font familija: Inter
- Naslovi: Bold, tracking-tight
- Telo: Regular, text-base

**Razmak:**
- Bazna jedinica: 4px
- Konzistentna skala za padding/margin

### 13.2 Ključni ekrani

| Ekran | Opis |
|-------|------|
| Landing stranica | Marketing stranica sa funkcionalnostima, cenama (saldora.rs) |
| Prijava / Registracija / Awaiting Approval | Auth ekrani; nove organizacije sleću na `/awaiting-approval` dok admin ne odobri (FR-4.1.5) |
| **Pregled portfelja** (`/pregled`) | Default home za agencijske korisnike; mreža kartica klijenata sa indikatorima zdravlja (FR-4.18.1) |
| **Klijent radna tabla** (`/klijenti/{id}`) | Single-page workspace za jednog klijenta sa tabovima Hronologija (default), Fakture, Izveštaji, Pravila (FR-4.18.2) |
| Hronologija tab | Render `client_events` događaja, grupisanih po danu, filterabilan po tipu (FR-4.18.3) |
| Fakture tab | Lista faktura pre-scope-ovana na trenutnog klijenta (FR-4.18.4) |
| Izveštaji tab | Izveštaji (FR-4.13) pre-scope-ovani na trenutnog klijenta; budući ugostiteljski obrasci (M20) (FR-4.18.5) |
| Pravila tab | Pravila po klijentu + org-wide; CTA "Kreiraj pravilo za ovog klijenta" (FR-4.18.6) |
| Klijenti (flat lista) | Brzi skok u workspace pojedinog klijenta |
| Pravila (org-wide editor) | Globalna pravila van per-client konteksta |
| Arhiviranje | Periodne arhive za poreze/retenciju |
| Katalog proizvoda | Kanonički proizvodi deljeni među klijentima |
| Otpremanje | Drag & drop interfejs za otpremanje |
| Pregled fakture | Uporedni prikaz dokumenta i podataka |
| Izvoz | Izbor formata, mapiranje polja |
| Podešavanja / Tim / Naplata | Profil, članovi tima, plan i naplata |

**Bočna struktura (post-M19):** vidi FR-4.18.7. Top-level stavke `Fakture` i `Izveštaji` su uklonjene; obe žive unutar workspace-a po klijentu.

### 13.3 Responzivne tačke preloma

| Tačka preloma | Širina | Cilj |
|--------------|-------|------|
| sm | 640px | Mobilni landscape |
| md | 768px | Tablet |
| lg | 1024px | Desktop |
| xl | 1280px | Veliki desktop |
| 2xl | 1536px | Ekstra veliki |

### 13.4 Pristupačnost

- WCAG 2.1 AA usklađenost
- Podrška za navigaciju tastaturom
- Kompatibilnost sa čitačima ekrana
- Dovoljan kontrast boja
- Indikatori fokusa
- Alt tekst za slike

### 13.5 Podrška za ćirilicu i latinicu

Srpski jezik koristi dva pisma - ćirilicu i latinicu. Sistem MORA podržavati oba pisma u potpunosti kako bi zadovoljio potrebe svih korisnika.

- Sistem MORA podržavati prikaz interfejsa na oba pisma (ćirilica i latinica)
- Korisnik može izabrati preferirano pismo u podešavanjima profila
- OCR mora prepoznavati oba pisma na fakturama
- Svi izveštaji i izvozi moraju podržavati oba pisma
- Podrazumevano pismo: Latinica
- Dugme za promenu pisma dostupno u zaglavlju aplikacije

| Zahtev | Specifikacija |
|--------|--------------|
| Podrazumevano pismo | Latinica (širi obuhvat korisnika) |
| Opcija prebacivanja | Vidljiv prekidač u zaglavlju aplikacije |
| Čuvanje preferenci | Sačuvaj izbor korisnika u podešavanjima profila |
| Obim | Svi UI elementi, poruke o greškama, pomoćni tekstovi |
| OCR podrška | Prepoznavanje oba pisma na ulaznim fakturama |
| Izveštaji i izvozi | Generisanje u izabranom pismu |
| Izuzetak | Tehnički termini (API, URL, itd.) ostaju u latinici |

---

## 14. Zahtevi testiranja

### 14.1 Strategija testiranja

| Tip testa | Cilj pokrivenosti | Alati |
|----------|-------------------|-------|
| Jedinični testovi | 80% | Jest, Pytest |
| Integracioni testovi | 70% | Pytest, Supertest |
| E2E testovi | Kritične putanje | Playwright |
| Testovi performansi | Ključni endpointi | k6 |
| Bezbednosni testovi | OWASP Top 10 | OWASP ZAP |

### 14.2 Kategorije test slučajeva

**Testovi autentifikacije:**
- Tok registracije
- Prijava sa validnim/nevažećim kredencijalima
- Resetovanje lozinke
- Osvežavanje tokena
- Istek sesije

**Testovi obrade faktura:**
- Otpremanje raznih formata
- Validacija OCR tačnosti
- Tačnost ekstrakcije polja
- Grupna obrada
- Obrada grešaka

**Integracioni testovi:**
- APR API integracija
- Paddle webhook obrada
- Isporuka e-pošte
- Operacije skladištenja fajlova

### 14.3 Performansni benchmarkovi

| Scenario | Cilj | Prag |
|----------|------|------|
| Učitavanje stranice (LCP) | < 2s | < 4s |
| OCR pojedinačne fakture | < 5s | < 10s |
| Grupna obrada (50 dok.) | < 2 min | < 5 min |
| API odgovor | < 200ms | < 500ms |
| Upit pretrage | < 500ms | < 1s |

---

## 15. Dodaci

### 15.1 Rečnik

| Termin | Definicija |
|--------|-----------|
| APR | Agencija za privredne registre |
| PIB | Poreski identifikacioni broj |
| PDV | Porez na dodatu vrednost |
| OCR | Optičko prepoznavanje karaktera |
| NER | Prepoznavanje imenovanih entiteta |
| JWT | JSON Web Token |
| ZZPL | Zakon o zaštiti podataka o ličnosti |
| KPR | Knjiga primljenih računa |
| KIR | Knjiga izdatih računa |
| SEF | Sistem elektronskih faktura |
| NBS | Narodna banka Srbije |

### 15.2 Standardi srpskih faktura

**Obavezna polja fakture (prema srpskom zakonu):**
- Broj fakture i datum
- Naziv prodavca, adresa, PIB, MB
- Naziv kupca, adresa, PIB (ako je primenjivo)
- Opis robe/usluga
- Količina i jedinična cena
- Poreska osnovica, poreska stopa, iznos poreza
- Ukupan iznos
- Uslovi plaćanja

**Stope PDV-a:**
- Standardna stopa: 20%
- Snižena stopa: 10%
- Oslobođeno: 0%

### 15.3 Primer strukture fakture

```
┌────────────────────────────────────────────────────────────┐
│                      ФАКТУРА / FAKTURA                      │
│                         Br: 2025-042                        │
├────────────────────────────────────────────────────────────┤
│ Datum: 15.01.2025                                          │
│ Valuta: 15.02.2025                                         │
├────────────────────────────────────────────────────────────┤
│ ПРОДАВАЦ / PRODAVAC:          │ КУПАЦ / KUPAC:            │
│ Firma ABC d.o.o.              │ Kompanija XYZ d.o.o.      │
│ Bulevar Kralja Aleksandra 1   │ Cara Dušana 15            │
│ 11000 Beograd                 │ 21000 Novi Sad            │
│ PIB: 123456789                │ PIB: 987654321            │
│ MB: 12345678                  │ MB: 87654321              │
├────────────────────────────────────────────────────────────┤
│ R.br │ Opis                    │ Kol. │ Cena   │ Iznos    │
├──────┼─────────────────────────┼──────┼────────┼──────────┤
│ 1    │ Usluge konsaltinga     │ 10   │ 5.000  │ 50.000   │
│ 2    │ Izrada dokumentacije   │ 1    │ 10.000 │ 10.000   │
├────────────────────────────────────────────────────────────┤
│                                  Osnovica:      60.000 RSD │
│                                  PDV (20%):     12.000 RSD │
│                                  ─────────────────────────│
│                                  UKUPNO:        72.000 RSD │
└────────────────────────────────────────────────────────────┘
```

### 15.4 Reference

1. Zakon o računovodstvu (Sl. glasnik RS, br. 73/2019)
2. Zakon o porezu na dodatu vrednost (Sl. glasnik RS, br. 84/2004, sa izmenama)
3. Zakon o zaštiti podataka o ličnosti - ZZPL (Sl. glasnik RS, br. 87/2018)
4. GDPR - Opšta uredba o zaštiti podataka (referentni standard)
5. dots.ocr dokumentacija (vizuelno-jezički model) — https://github.com/rednote-hilab/dots.ocr
6. vLLM dokumentacija (server za inferencu modela) — https://docs.vllm.ai
7. FastAPI dokumentacija
8. Next.js dokumentacija
9. Zakon o elektronskom fakturisanju (Sl. glasnik RS, br. 44/2021)
10. NBS API za kursnu listu

---

## Istorija dokumenta

| Verzija | Datum | Autor | Izmene |
|---------|-------|-------|--------|
| 1.0 | Januar 2025 | FakturaAI Tim | Inicijalno izdanje |
| 1.1 | Januar 2025 | FakturaAI Tim | Dodato: Poslovna logika i pravila validacije (4.9), Legal & Compliance tokovi (10.6) |
| 1.2 | Januar 2025 | FakturaAI Tim | Dodato: Sloj računovodstvene namere (4.10), Motor za automatizaciju pravila (4.11), SEF integracija (12.5) |
| 1.3 | Januar 2025 | FakturaAI Tim | Ažuriran OCR stek: dots.ocr (VLM) kao primarni engine, EasyOCR kao rezerva |
| 2.0 | Februar 2026 | FakturaAI Tim | Srpska verzija sa svim ispravkama: uklonjen model training/retraining, ZZPL kao primarni zakon, Paddle umesto Stripe, KPR/KIR terminologija, SEF polling umesto webhook-ova, NBS kursna lista, podrška za ćirilicu i latinicu, PIB constraint za strane entitete, retencija dokumenata 10 godina |
| 2.1 | Februar 2026 | FakturaAI Tim | dots.ocr arhitektura: vLLM HTTP server sidecar (GPU) + lak OCR radnik (CPU, OpenAI klijent), uklonjen EasyOCR kao rezerva (ručni pregled umesto toga), preskakanje predprocesiranja za VLM |
| 2.2 | Mart 2026 | FakturaAI Tim | Generacija PDV knjiga (KPR/KIR) zamenjena funkcionalnosti Izveštaja (4.13): denormalizovana tabela invoice_line_items koja se popunjava pri završetku OCR obrade i pri izmenama; pet unapred definisanih šablona izveštaja (pregled primljene robe, troškovi po dobavljaču, mesečni pregled stavki, poređenje cena, pregled troškova) na /api/v1/reports/; nulti LLM trošak; CSV izvoz; stranica na /{orgSlug}/izvestaji; kontrola PRO plana. Dodato upravljanje klijentima za Agency plan (4.12). |
| 2.8 | Mart 2026 | Saldora Tim | Dodat Katalog proizvoda (4.15): kanonička imena, aliasi (JSONB), kategorije, prodajne cene, marže, pg_trgm fuzzy matching, FK product_id na invoice_line_items, CRUD + merge API na /api/v1/products/. Dodata četiri endpoint-a za nabavnu inteligenciju (4.13.2.6–4.13.2.9): /kalkulacija, /ruc, /spending-by-category, /dpu (dnevna evidencija robe). Stranica /izvestaji objedinjena sa tri grupe: Opšti, Nabavka i prodaja, Upravljanje; uklonjene odvojene stranice /katalog i /dpu. Dodat product_catalog u šemu baze (7.2.6). Preimenovano: "Šank lista" → "Dnevna evidencija robe"; "Ugostiteljstvo" → "Nabavka i prodaja". Ispravke: sinhronizacija stavki pri verifikaciji fakture; kaskadno brisanje pri grupnom brisanju; mesečni pregled prikazuje PDV % i PDV iznos; poruke o greškama verifikacije prevedene na srpski. |
| 2.9 | Mart 2026 | Saldora Tim | Dodat sistem podrške u aplikaciji (4.16). Ažurirana referenca MiniMax API polja (12.5.4). Ažurirani detalji bezbednosnih poboljšanja (10.1, 10.3). Dodate serverless GPU opcije deployovanja (9.7). Ažuriran prikaz pouzdanosti sa procenata na tekstualne oznake (4.3.3). |
| 4.0 | 2026-04-29 | Saldora Tim | **Ugostiteljski pivot.** Repozicioniran dokument kao izvor istine za post-pivot proizvod (sloj inteligencije za srpske računovodstvene agencije sa ugostiteljskim klijentima). Novo zaglavlje ("trenutna teza"). Ažurirane persone (1.4, 2.3) — vlasnici agencija i knjigovođe kao primarni; paušalci uklonjeni kao persona. Dodat FR-4.1.5 ručno odobrenje naloga (subscription_status, /awaiting-approval, admin_orgs.py) i FR-4.1.6 pozivnice/zahtevi za pristup. Proširen Odeljak 4.12 sa FR-4.12.5 client_events log i FR-4.12.6 rule_client_associations; uklonjen bočni selektor klijenata u korist klijent-prvi UI-a. Dodat Odeljak 4.17 (Van obima / Otpisano) konsolidacija otpisanih funkcionalnosti: paušal modul, klijent portal, compliance watchdog, strani reverse-charge modul, praćenje plaćanja, webhookovi, EasyOCR fallback, Stripe, predprocesiranje slike za VLM. Dodat Odeljak 4.18 (Klijent-prvi UI / M19) sa `/pregled`, `/klijenti/{id}`, tabovima Hronologija/Fakture/Izveštaji/Pravila, restrukturom bočne trake. Dodat Odeljak 4.19 (Ugostiteljski zakonski obrasci / M20) označen kao odložen do sastanka sa računovođom; dokumentovani kalkulacije, šank lista, cenovnik, KEP, popis kao sledeći sloj sa osnovom podataka u mestu. Označen Odeljak 4.14 (email ingestion) i 4.16 (in-app podrška) kao planirano/još nije povezano. Ažuriran tehnološki stek (Odeljak 6) na Modal-hosted dots.ocr (zamenjuje vLLM kontejner), Hetzner CX32 jednomašinski docker-compose (zamenjuje k8s), Cloudflare R2 (prod) + MinIO (dev), Resend (jedini). Zamenjena arhitektura deployovanja iz Odeljka 11 sa single-host Caddy/FastAPI/Next.js/PostgreSQL/Redis/Celery topologijom. Uklonjeni svi SEF integracioni podOdeljci (12.6.2–12.6.8) — zadržan stub koji ukazuje na deprioritizaciju i upućuje na v3.2 za prethodnu specifikaciju. Dodate 7.2.7 (client_events) i 7.2.8 (rule_client_associations) DB šeme; dokumentovana semantika subscription_status na organizations (7.2.2). Ažurirani UI ključni ekrani (13.2). Razne čišćenja zastarelih referenci (fakturaai.rs → saldora.rs, fakturaai DB nazivi kolona → saldora). |

---

**Kraj dokumenta**
