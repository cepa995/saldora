# Saldora - Specifikacija proizvoda
## Platforma za obradu faktura pomoću veštačke inteligencije

**Verzija:** 2.9
**Datum:** Mart 2026
**Namena dokumenta:** Poslovni pregled za računovođe, partnere i investitore

---

## Sadržaj

1. [Šta je Saldora?](#1-šta-je-saldora)
2. [Za koga je Saldora?](#2-za-koga-je-saldora)
3. [Pregled funkcionalnosti](#3-pregled-funkcionalnosti)
4. [Tok obrade fakture](#4-tok-obrade-fakture)
5. [Funkcionalni zahtevi](#5-funkcionalni-zahtevi)
6. [Poslovna pravila i validacije](#6-poslovna-pravila-i-validacije)
7. [Računovodstvena logika](#7-računovodstvena-logika)
8. [Pravila automatizacije](#8-pravila-automatizacije)
9. [Integracije](#9-integracije)
10. [Pretplatni planovi](#10-pretplatni-planovi)
11. [Bezbednost i zaštita podataka](#11-bezbednost-i-zaštita-podataka)
12. [Korisničko iskustvo](#12-korisničko-iskustvo)

---

## 1. Šta je Saldora?

Saldora je veb platforma dizajnirana za srpsko tržište koja pomoću veštačke inteligencije automatizuje obradu faktura. Umesto ručnog prepisivanja podataka iz faktura u Excel ili računovodstveni softver, korisnik otpremi fakture (PDF, sliku ili iz SEF-a), a sistem automatski:

- **Prepoznaje tekst** sa fakture (i ćirilicu i latinicu)
- **Ekstrahuje podatke** (PIB, naziv firme, iznose, stavke, PDV...)
- **Verifikuje podatke** (proverava PIB u APR bazi, računa matematiku)
- **Predlaže knjiženje** (predložena konta, PDV tretman, KPR/KIR unose)
- **Izvozi podatke** u formate pogodne za računovodstveni softver

Računovođa ostaje u potpunoj kontroli - pregleda predloge sistema, ispravlja greške ako ih ima, i odobrava izvoz.

---

## 2. Za koga je Saldora?

### 2.1 Samostalni računovođa

- Obrađuje 50-200 faktura mesečno
- Potreban mu je jednostavan, intuitivan interfejs
- Osetljiv na cenu
- Ograničeno tehničko znanje

### 2.2 Računovodstvena agencija

- Obrađuje 500-5.000 faktura mesečno
- Upravlja sa više klijenata (svaki klijent je zasebna organizacija u sistemu)
- Zahteva grupnu obradu (otpremanje 50 faktura odjednom)
- Potrebna mogućnost definisanja pravila automatizacije po klijentu

### 2.3 Korporativni korisnik

- Obrađuje 5.000+ faktura mesečno
- Zahteva prilagođene integracije sa postojećim ERP sistemima
- Potrebne SLA garancije i dedicirani suport

---

## 3. Pregled funkcionalnosti

| Funkcionalnost | Opis | Prioritet |
|----------------|------|-----------|
| Otpremanje faktura | PDF, JPG, PNG, TIFF - pojedinačno ili grupno (do 50) | Visok |
| AI ekstrakcija podataka | Automatsko prepoznavanje svih polja fakture | Visok |
| Podrška za ćirilicu i latinicu | Potpuna podrška za oba srpska pisma | Visok |
| PIB verifikacija | Provera u APR bazi u realnom vremenu | Visok |
| Matematička verifikacija | Provera da li se iznosi slažu | Visok |
| Predlog knjiženja | Predložena konta, PDV tretman, KPR/KIR | Visok |
| Izvoz podataka | Excel, CSV, JSON sa prilagodivim šablonima | Visok |
| SEF integracija | Automatsko preuzimanje faktura iz Sistema Elektronskih Faktura | Visok |
| Grupna obrada | Istovremena obrada više faktura | Srednji |
| Pravila automatizacije | Definisanje pravila za automatsko knjiženje | Srednji |
| Kontrolna tabla | Statistike obrade, praćenje korišćenja | Srednji |
| NBS kursna lista | Automatska konverzija stranih valuta po kursu NBS | Srednji |
| Izveštaji o nabavci | Kalkulacija cena, RUC analiza, troškovi po kategoriji, dnevna evidencija robe | Srednji |
| Katalog proizvoda | Kanonička lista proizvoda sa aliasima za normalizaciju stavki faktura | Srednji |
| Sistem podrške (Podrška) | Tiketi za podršku sa chat pregledom i fajlovima — dostupno na svim planovima | Srednji |
| API pristup | REST API za integracije sa trećim sistemima | Nizak |

---

## 4. Tok obrade fakture

Kompletna obrada jedne fakture prolazi kroz sledeće korake:

```
  ┌──────────────────┐
  │  1. OTPREMANJE   │   Korisnik otpremi PDF/sliku fakture
  │                  │   ili se faktura preuzme iz SEF-a
  └────────┬─────────┘
           ▼
  ┌──────────────────┐
  │  2. PREPOZNAVANJE│   AI prepoznaje tekst (ćirilica + latinica)
  │     (OCR)        │   i detektuje strukturu dokumenta
  └────────┬─────────┘
           ▼
  ┌──────────────────┐
  │  3. EKSTRAKCIJA  │   Sistem ekstrahuje sva polja:
  │     PODATAKA     │   PIB, nazive, iznose, stavke, datume...
  └────────┬─────────┘
           ▼
  ┌──────────────────┐
  │  4. VERIFIKACIJA │   • PIB verifikacija u APR bazi
  │     I VALIDACIJA │   • Matematička provera iznosa
  │                  │   • Provera PDV stopa (0%, 10%, 20%)
  │                  │   • Detekcija duplikata
  └────────┬─────────┘
           ▼
  ┌──────────────────┐
  │  5. PREDLOG      │   Sistem predlaže:
  │     KNJIŽENJA    │   • Tip dokumenta (ulazna, izlazna, avansna...)
  │ (AccountingIntent│   • PDV tretman (odbitni, neodbitni, obrnuti...)
  │                  │   • Konta za knjiženje
  │                  │   • KPR/KIR unose
  └────────┬─────────┘
           ▼
  ┌──────────────────┐
  │  6. PREGLED      │   Računovođa pregleda sve predloge
  │     I KOREKCIJA  │   Uporedni prikaz: original ↔ ekstraktovani podaci
  │                  │   Ispravlja greške ako ih ima
  │                  │   Odobrava ili menja predložena konta
  └────────┬─────────┘
           ▼
  ┌──────────────────┐
  │  7. IZVOZ        │   Izvoz u Excel, CSV ili JSON
  │                  │   Sa svim računovodstvenim podacima
  │                  │   Spreman za uvoz u ERP/računovodstveni softver
  └──────────────────┘
```

**Ključna napomena:** Sistem nikada ne izvozi podatke automatski bez potvrde računovođe. Korisnik uvek ima poslednju reč.

---

## 5. Funkcionalni zahtevi

### 5.1 Otpremanje faktura

| Zahtev | Specifikacija |
|--------|---------------|
| Podržani formati | PDF, JPEG, PNG, TIFF, BMP, WEBP |
| Maksimalna veličina | 20 MB po fajlu |
| Grupno otpremanje | Do 50 fajlova odjednom (ukupno do 200 MB) |
| Način otpremanja | Drag & drop, dugme za izbor fajla, mobilna kamera |
| Višestranične fakture | Automatska detekcija i spajanje u jedan zapis |

### 5.2 AI ekstrakcija podataka

Sistem prepoznaje i ekstrahuje sledeća polja sa svake fakture:

**Obavezna polja:**

| Polje | Validacija |
|-------|-----------|
| Broj fakture | Alfanumerički identifikator |
| Datum fakture | Validan format datuma |
| Datum dospeća | Validan datum, posle datuma fakture |
| Naziv prodavca | Neprazan tekst |
| PIB prodavca | 9 cifara, mod-11 kontrolni zbir |
| Adresa prodavca | Neprazan tekst |
| Naziv kupca | Neprazan tekst |
| PIB kupca | 9 cifara (za domaće subjekte) |
| Adresa kupca | Neprazan tekst |
| Osnovica | Decimalni broj |
| Stopa PDV-a | 0%, 10% ili 20% |
| Iznos PDV-a | Decimalni broj |
| Ukupan iznos | Decimalni broj |
| Valuta | RSD, EUR, USD |
| Stavke | Opis, količina, jedinična cena, ukupno |

**Ocena pouzdanosti:** Svako polje dobija ocenu pouzdanosti 0-100%. Polja ispod 80% se automatski označavaju za ručni pregled.

### 5.3 Verifikacija i validacija

| Provera | Šta radi | Šta se dešava ako ne prođe |
|---------|----------|---------------------------|
| PIB verifikacija | Proverava PIB u APR bazi | Prikazuje upozorenje, zahteva potvrdu |
| Matematička provera | Osnovica + PDV = Ukupno? Zbir stavki = Osnovica? | Označava neslaganje za pregled |
| PDV stope | Da li je stopa 0%, 10% ili 20%? | Označava nepoznatu stopu |
| Detekcija duplikata | Da li faktura sa istim brojem i PIB-om već postoji? | Upozorava korisnika |
| Validacija datuma | Da li je datum u budućnosti? Da li je dospeće pre datuma? | Označava za pregled |
| Prodavac = Kupac | Da li prodavac i kupac imaju isti PIB? | Traži potvrdu (interni transfer?) |

### 5.4 Pregled i korekcija

- **Uporedni prikaz:** Leva strana - originalni dokument (PDF/slika); desna strana - ekstraktovani podaci
- **Isticanje:** Klik na polje u ekstraktovanim podacima ističe odgovarajuću oblast na originalnom dokumentu
- **Izmena:** Sva polja se mogu ručno izmeniti sa validacijom u realnom vremenu
- **Grupna izmena:** Moguća korekcija istog polja na više faktura odjednom

### 5.5 Izvoz podataka

| Format | Opis |
|--------|------|
| Excel (XLSX) | Formatirani zaglavlja, validacija podataka, više listova |
| CSV | UTF-8 kodiranje, podesiv separator (zarez, tačka-zarez, tab) |
| JSON | Za integraciju sa drugim sistemima |
| Prilagođeni šabloni | Korisnik može definisati koja polja, kojim redom, sa kojim nazivima |

### 5.6 Kontrolna tabla

- Ukupno obrađenih faktura (dnevno, nedeljno, mesečno)
- Stopa uspešnosti ekstrakcije
- Prosečno vreme obrade
- Praćenje korišćenja u odnosu na limite pretplate (upozorenja na 80%, 90%, 100%)
- Pretraživa istorija svih obrađenih faktura (čuvanje minimum 10 godina)

### 5.7 Korisničke uloge i dozvole

| Uloga | Šta može |
|-------|----------|
| Admin | Sve - upravljanje timom, naplata, podešavanja |
| Menadžer | Obrada faktura, izvoz, pregled rada tima |
| Operater | Obrada faktura, izvoz |
| Čitalac | Samo pregled obrađenih faktura |

---

## 6. Poslovna pravila i validacije

### 6.1 Pravila validacije PIB-a

| Scenario | Reakcija sistema |
|----------|-----------------|
| Validan PIB, aktivna firma u APR-u | Automatski odobrava, prikazuje naziv firme |
| Validan PIB, firma u likvidaciji/stečaju | Upozorava, zahteva pregled |
| Nevažeći format PIB-a (nije 9 cifara) | Blokira izvoz |
| PIB nije pronađen u APR bazi | Upozorava, zahteva pregled |
| APR servis nedostupan | Dozvoljava sa upozorenjem |

**Format PIB-a:**
- Tačno 9 cifara
- Ne počinje nulom
- Mora proći mod-11 kontrolni zbir

### 6.2 Pravila validacije PDV-a

| Ekstraktovana stopa | Reakcija |
|----------------------|----------|
| 0%, 10%, 20% | Standardne srpske stope - automatski odobrava |
| Druga vrednost (npr. 17%, 25%) | Označava za pregled - nevažeća za Srbiju |
| Nedostaje ili nejasno | Označava za pregled, predlaže 20% kao podrazumevanu |

**Fakture sa više stopa PDV-a:** Sistem proverava obračun za svaku stopu posebno i upozorava ako se iznosi ne slažu.

### 6.3 Matematička verifikacija

Sistem proverava 4 jednačine na svakoj fakturi:

1. **Zbir stavki = Osnovica** (ukupno svih stavki mora biti jednako poreskoj osnovici)
2. **Osnovica × Stopa = PDV** (obračun poreza mora biti tačan)
3. **Osnovica + PDV = Ukupno** (zbir mora odgovarati)
4. **Količina × Cena = Iznos** (za svaku pojedinačnu stavku)

**Prihvatljive tolerancije zaokruživanja:**

| Opseg iznosa | Dozvoljena razlika |
|-------------|-------------------|
| do 10.000 RSD | ±1 RSD |
| 10.001 - 100.000 RSD | ±5 RSD |
| 100.001 - 1.000.000 RSD | ±10 RSD |
| preko 1.000.000 RSD | ±50 RSD |

### 6.4 Obrada valuta

| Scenario | Reakcija |
|----------|----------|
| RSD (srpski dinar) | Podrazumevana valuta, normalna obrada |
| EUR ili USD | Prihvata, čuva original, prikazuje RSD ekvivalent po kursu NBS |
| Mešovite valute u stavkama | Blokira izvoz - greška |
| Nejasan simbol valute | Označava za pregled |

**Konverzija:** Za strane valute koristi se srednji kurs Narodne banke Srbije na dan fakture.

### 6.5 Validacija datuma

| Scenario | Reakcija |
|----------|----------|
| Datum fakture u budućnosti | Označava za pregled |
| Dospeće pre datuma fakture | Označava za pregled |
| Faktura starija od 1 godine | Upozorava (ali dozvoljava) |

### 6.6 Pravila blokiranja izvoza

**Faktura NE MOŽE biti izvezena ako:**
1. Format PIB-a je nevažeći
2. Nedostaju obavezna polja (broj fakture, datum, PIB prodavca, ukupan iznos)
3. Matematička verifikacija ne prolazi
4. Korisnik nije pregledao označena upozorenja
5. Pouzdanost ekstrakcije ispod 60% i nije ručno verifikovano

**Izvoz dozvoljen sa upozorenjem ako:**
1. APR verifikacija nije uspela (servis nedostupan)
2. Pouzdanost između 60-80%
3. Nedostaje nekritično polje (npr. adresa kupca)

---

## 7. Računovodstvena logika

### 7.1 Predlog knjiženja (AccountingIntent)

Za svaku fakturu, sistem generiše **predlog knjiženja** koji uključuje:

| Komponenta | Šta sadrži |
|------------|-----------|
| Tip dokumenta | Ulazna faktura, izlazna faktura, knjižno odobrenje, avansna faktura... |
| Tip transakcije | Domaći promet, uvoz/izvoz, obrnuta naplata, oslobođeno... |
| PDV tretman | Potpuno odbitno, delimično odbitno, neodbitno... |
| Predložena konta | Šifre konta za duguje/potražuje stranu |
| KPR/KIR unosi | Gotovi unosi za knjige primljenih/izdatih računa |
| Polja PDV-PP | Mapiranje na polja poreske prijave |

**Sve predloge korisnik pregleda i može izmeniti pre izvoza.**

### 7.2 Tipovi dokumenata

| Tip | Srpski naziv | Opis |
|-----|-------------|------|
| Ulazna faktura | Ulazna faktura | Primljena od dobavljača |
| Izlazna faktura | Izlazna faktura | Izdata kupcu |
| Knjižno odobrenje (primljeno) | Primljeno knjižno odobrenje | Smanjenje obaveze prema dobavljaču |
| Knjižno odobrenje (izdato) | Izdato knjižno odobrenje | Smanjenje potraživanja od kupca |
| Knjižno zaduženje (primljeno) | Primljeno knjižno zaduženje | Uvećanje obaveze |
| Knjižno zaduženje (izdato) | Izdato knjižno zaduženje | Uvećanje potraživanja |
| Avansna faktura | Avansna faktura | Za avansno plaćanje |
| Konačna faktura | Konačna faktura | Nakon avansnog plaćanja |
| Profaktura | Profaktura | Informativna - ne knjiži se |

### 7.3 PDV tretman

| Tretman | Opis | Polje PDV-PP |
|---------|------|-------------|
| Potpuno odbitni ulazni PDV | Standardna ulazna faktura za poslovnu upotrebu | Polje 8 |
| Delimično odbitni PDV | Mešovita poslovna/privatna upotreba | Izračunato proporcionalno |
| Neodbitni PDV | Reprezentacija, putnička vozila i sl. | N/A |
| Izlazni PDV - standardna stopa | Faktura izdata po stopi od 20% | Polje 3 |
| Izlazni PDV - snižena stopa | Faktura izdata po stopi od 10% | Polje 4 |
| Oslobođen izlazni PDV | Izvoz i sl. | Polje 6 |
| Obrnuti obračun (kupac) | Kupac obračunava PDV | Polje 8a |
| Obrnuti obračun (prodavac) | Prodavac fakturiše bez PDV-a | Polje 6a |

### 7.4 Predložena konta (srpski kontni plan)

Sistem predlaže šifre konta na osnovu tipa dokumenta, opisa stavki i istorije dobavljača:

| Scenario | Duguje | Potražuje | Opis |
|----------|--------|-----------|------|
| Ulazna faktura - usluge | 5330 | 4330 | Rashod usluga / Dobavljači |
| Ulazna faktura - roba | 5010 | 4330 | Nabavna vrednost / Dobavljači |
| Ulazna faktura - PDV | 2700 | - | Ulazni PDV |
| Izlazna faktura - prihod | 2040 | 6010 | Kupci / Prihod od prodaje |
| Izlazna faktura - PDV | - | 4700 | Izlazni PDV |
| Primljeni avans | - | 4300 | Avansi od kupaca |
| Dati avans | 1500 | - | Avansi dobavljačima |

**Prilagodljivost:** Organizacije mogu definisati sopstveni kontni plan i pravila automatskog dodeljivanja konta.

### 7.5 KPR i KIR

**KPR (Knjiga primljenih računa) - za ulazne fakture:**

| Polje | Odakle dolazi |
|-------|--------------|
| Redni broj | Automatski sekvencijalno |
| Datum prijema | Datum otpremanja u sistem |
| Datum fakture | Iz OCR-a, verifikovan |
| Broj fakture | Iz OCR-a |
| PIB isporučioca | Verifikovan u APR-u |
| Naziv isporučioca | Iz OCR-a ili APR-a |
| Osnovica 20% | Izračunato iz stavki |
| PDV 20% | Izračunato |
| Osnovica 10% | Izračunato iz stavki |
| PDV 10% | Izračunato |
| Ukupno | Validirano (matematička provera) |

**KIR (Knjiga izdatih računa) - za izlazne fakture:**

Ista struktura kao KPR, ali sa podacima kupca umesto dobavljača.

**PDV-PP mapiranje:** Sistem automatski mapira podatke na polja poreske prijave PDV-PP (polja 3, 4, 6, 6a, 8, 8a, 9 itd.).

---

## 8. Pravila automatizacije

Računovodstvene agencije mogu definisati **prilagođena pravila** koja automatizuju ponavljajuće odluke o knjiženju:

### 8.1 Tipovi pravila

| Tip pravila | Šta radi | Primer |
|-------------|----------|--------|
| Dodeljivanje konta | Automatski dodeljuje konto | "Fakture od Telekoma → konto 5130 (Telekomunikacije)" |
| PDV tretman | Postavlja PDV tretman | "Fakture za gorivo → neodbitno (putničko vozilo)" |
| Automatsko odobrenje | Preskače ručni pregled | "Fakture ispod 5.000 RSD → automatski odobri" |
| Obavezni pregled | Forsira ručni pregled | "Novi dobavljač → uvek pregledaj" |
| Tip dokumenta | Menja klasifikaciju | "Dobavljač XYZ uvek šalje knjižna odobrenja" |

### 8.2 Kako funkcionišu

Svako pravilo ima:
- **Uslov:** Kada se primenjuje (npr. "PIB prodavca = 123456789" ILI "iznos > 100.000 RSD")
- **Akcija:** Šta radi (npr. "postavi konto 5330" ILI "označi za pregled")
- **Prioritet:** Redosled izvršavanja (ako se više pravila poklapa)

Korisnik kreira pravila putem jednostavnog interfejsa bez potrebe za programiranjem.

### 8.3 Primeri korišćenja

**Primer 1 - Redovni dobavljač:**
> "Sve fakture od EPS Snabdevanja (PIB: 108057105) automatski knjižiti na konto 5130 (Energija) sa potpuno odbitnim PDV-om."

**Primer 2 - Reprezentacija:**
> "Fakture koje u opisu sadrže 'restoran', 'hotel' ili 'ručak' označiti PDV kao neodbitni."

**Primer 3 - Kontrola velikih iznosa:**
> "Fakture preko 500.000 RSD uvek zahtevaju ručni pregled od menadžera."

---

## 9. Integracije

### 9.1 SEF - Sistem Elektronskih Faktura

Saldora se integriše sa SEF-om (eFaktura) za automatsko preuzimanje elektronskih faktura:

**Šta SEF integracija omogućava:**
- Automatsko preuzimanje novih faktura svakih 15 minuta
- Obrada kroz isti pipeline kao i ručno otpremljene fakture
- Slanje prihvatanja/odbijanja nazad na SEF
- Praćenje statusa faktura (isporučena, odobrena, odbijena, plaćena)

**Statusi faktura na SEF-u:**

| Status | Značenje | Šta Saldora radi |
|--------|---------|---------------------|
| Isporučena | Nova faktura stigla | Preuzima i obrađuje |
| Viđena | Korisnik je video | Ažurira status |
| Odobrena | Faktura prihvaćena | Označava kao prihvaćenu |
| Odbijena | Faktura odbijena | Označava sa razlogom odbijanja |
| Stornirana | Faktura poništena | Kreira storno zapis ako je već proknjižena |
| Plaćena | Plaćanje evidentirano | Ažurira status plaćanja |

**SEF Inbox:** Poseban ekran za upravljanje elektronskim fakturama sa opcijama: Obradi, Prihvati, Odbij, Arhiviraj.

**Napomena:** SEF ne podržava obaveštenja u realnom vremenu (webhook). Sistem periodično proverava nove fakture (polling svakih 15 minuta).

**Hibridna obrada:** Kada faktura dolazi sa SEF-a, sistem koristi i strukturirane podatke iz XML-a (autoritativno za PIB, iznose) i OCR prepoznavanje PDF-a (za dodatne detalje, vizuelnu verifikaciju).

### 9.2 APR - Agencija za privredne registre

- PIB verifikacija u realnom vremenu
- Preuzimanje naziva firme, adrese, statusa (aktivna, u likvidaciji, stečaj...)
- Keširanje rezultata na 24 sata

**Napomena:** APR ne pruža besplatan javni API. Potreban je komercijalni ugovor sa APR-om ili korišćenje licenciranog posrednika (npr. DataCentric, Bisnode/Dun & Bradstreet). Sistem je dizajniran da podržava zamenu provajdera bez značajnih izmena.

### 9.3 NBS - Narodna banka Srbije

- Automatsko preuzimanje dnevne kursne liste NBS-a
- Srednji kurs za konverziju stranih valuta u RSD
- Koristi se za: prikaz RSD ekvivalenta na fakturama u stranoj valuti
- Za neradne dane koristi se poslednja dostupna kursna lista

### 9.4 Plaćanja - Paddle

- Paddle upravlja svim platnim transakcijama kao Merchant of Record
- Paddle preuzima odgovornost za obračun PDV-a u svim jurisdikcijama
- Korisnici plaćaju pretplatu putem kartice ili PayPal-a

### 9.5 MiniMax integracija

Saldora se integriše sa MiniMax-om (minimax.rs), najkorišćenijim cloud računovodstvenim softverom u Srbiji:

- **XML izvoz:** Generiše XML fajl za uvoz u MiniMax (Stranke + Temeljnice format)
- **Direktno slanje putem API-ja:** Automatsko slanje primljenih faktura u MiniMax putem REST API-ja (OAuth 2.0)
- **Upravljanje kupcima:** Automatska pretraga ili kreiranje kupca po PIB-u
- **Konfiguracija po organizaciji:** Svaka organizacija čuva sopstvene MiniMax kredencijale

---

## 10. Pretplatni planovi

| | Starter | Profesional | Enterprise |
|---|---------|-------------|------------|
| **Ciljni korisnik** | Samostalni računovođa | Računovodstvena agencija | Korporativni korisnik |
| **Broj faktura/mesečno** | Do 200 | Do 2.000 | Neograničeno |
| **Broj korisnika** | 1 | Do 10 | Neograničeno |
| **Broj organizacija** | 1 | Do 20 | Neograničeno |
| **Grupno otpremanje** | Do 10 | Do 50 | Do 50 |
| **SEF integracija** | Osnovna | Potpuna | Potpuna |
| **Pravila automatizacije** | 5 pravila | Neograničeno | Neograničeno |
| **API pristup** | Ne | Da | Da |
| **Prilagođeni šabloni** | Ne | Da | Da |
| **Dedicirani suport** | Ne | Ne | Da |
| **SLA garancija** | Ne | Ne | Da |

---

## 11. Bezbednost i zaštita podataka

### 11.1 Zaštita podataka

- **ZZPL (Zakon o zaštiti podataka o ličnosti)** - Potpuna usklađenost sa srpskim zakonom o zaštiti podataka
- GDPR kao referentni standard za najbolje prakse
- Svi podaci su šifrovani (u prenosu i na disku)
- Dokumenti se čuvaju u bezbednom skladištu sa šifrovanim pristupom

### 11.2 Čuvanje podataka

| Tip podataka | Period čuvanja | Pravni osnov |
|-------------|---------------|-------------|
| Podaci o fakturama | 10 godina | Zakon o računovodstvu |
| Originalna dokumenta | 10 godina | Zakon o računovodstvu |
| Korisnički nalozi | Dok je aktivan + 2 godine | Poslovna potreba |
| Logovi revizije | 7 godina | Usklađenost |
| Privremeni fajlovi | 24 sata | Tehnička potreba |

### 11.3 Izvoz za poresku inspekciju

Kada Poreska uprava zatraži podatke, sistem omogućava izvoz:

| Tip izvoza | Format | Sadržaj |
|------------|--------|---------|
| Registar faktura | XML (eFaktura format) | Sve fakture u periodu |
| Arhiva dokumenata | ZIP sa PDF-ovima | Originalna dokumenta |
| Revizijski trag | CSV/Excel | Sve akcije na fakturama |
| PDV pregled | PDF/Excel | PDV-PP razrada |

### 11.4 Pravo na brisanje

- Korisnici mogu zahtevati brisanje ličnih podataka (profil, preferencije, sesije)
- Podaci o fakturama se ne mogu obrisati tokom zakonskog roka čuvanja (10 godina)
- Korisnik se obaveštava šta je obrisano i šta je zadržano (sa obrazloženjem)

### 11.5 Korisničke saglasnosti

| Tip saglasnosti | Obavezno? | Može se opozvati? |
|----------------|-----------|-------------------|
| Osnovna obrada (OCR, ekstrakcija) | Da - neophodno za uslugu | Ne |
| Analitika (obrasci korišćenja) | Ne | Da |
| Marketing (novosti, bilteni) | Ne | Da |

**Napomena:** Sistem NE koristi korisničke podatke za treniranje AI modela. Koriste se isključivo unapred trenirani modeli.

---

## 12. Korisničko iskustvo

### 12.1 Ključni ekrani

| Ekran | Šta korisnik radi |
|-------|-------------------|
| Početna stranica | Upoznaje se sa proizvodom, bira plan |
| Prijava/Registracija | Kreira nalog ili se prijavljuje |
| Kontrolna tabla | Vidi statistike, pristupa brzim akcijama |
| Otpremanje | Prevlači fakture ili ih bira sa diska |
| Obrada | Prati status obrade u realnom vremenu |
| Pregled fakture | Uporedni prikaz (original ↔ podaci), ispravlja greške |
| Lista faktura | Pretražuje, filtrira, sortira sve fakture |
| SEF Inbox | Upravlja fakturama iz Sistema Elektronskih Faktura |
| Izvoz | Bira format, prilagođava šablon, preuzima fajl |
| Podrška | Kreira tikete, prati status, razmenjuje poruke sa timom Saldore |
| Podešavanja | Profil, tim, pravila automatizacije, API ključevi |
| Naplata | Bira plan, prati korišćenje, upravlja pretplatom |

### 12.2 Podrška za oba pisma

- Korisnik bira između ćirilice i latinice u podešavanjima
- Dugme za brzo prebacivanje pisma u zaglavlju aplikacije
- OCR prepoznaje oba pisma na fakturama
- Izveštaji i izvozi se generišu u izabranom pismu
- Podrazumevano pismo: Latinica

### 12.3 Responzivnost

Aplikacija radi na svim uređajima:
- Desktop (optimalno iskustvo za svakodnevni rad)
- Tablet (pregled i odobravanje faktura)
- Mobilni telefon (otpremanje faktura kamerom, pregled statusa)

### 12.4 Sistem podrške (Podrška)

Saldora ima ugrađen sistem podrške dostupan na svim planovima. Korisnici mogu:

- Kreirati tikete za podršku direktno iz aplikacije (bez odlaska na email ili spoljni portal)
- Priložiti fajlove (snimke ekrana, PDF-ove) uz poruke
- Pratiti status tiketa: **Otvoren** → **U obradi** → **Rešen** → **Zatvoren**
- Primati odgovore tima Saldore u obliku chat-like konverzacije

Bedž u bočnoj traci označava broj nepročitanih odgovora.

---

## Dodatak: Standardi srpskih faktura

**Obavezna polja fakture prema srpskom zakonu:**
- Broj fakture i datum
- Naziv prodavca, adresa, PIB, MB
- Naziv kupca, adresa, PIB (ako je primenjivo)
- Opis robe/usluga
- Količina i jedinična cena
- Poreska osnovica, stopa, iznos poreza
- Ukupan iznos
- Uslovi plaćanja

**Stope PDV-a u Srbiji:**
- Standardna stopa: **20%**
- Snižena stopa: **10%**
- Oslobođeno: **0%**

**Primer fakture:**

```
┌────────────────────────────────────────────────────────────┐
│                      ФАКТУРА / FAKTURA                      │
│                         Br: 2025-042                        │
├────────────────────────────────────────────────────────────┤
│ Datum: 15.01.2025                 Valuta: 15.02.2025       │
├────────────────────────────────────────────────────────────┤
│ PRODAVAC:                    │ KUPAC:                      │
│ Firma ABC d.o.o.             │ Kompanija XYZ d.o.o.        │
│ Bulevar Kralja Aleksandra 1  │ Cara Dušana 15              │
│ 11000 Beograd                │ 21000 Novi Sad              │
│ PIB: 123456789               │ PIB: 987654321              │
│ MB: 12345678                 │ MB: 87654321                │
├──────┬─────────────────────────┬──────┬────────┬──────────┤
│ R.br │ Opis                    │ Kol. │ Cena   │ Iznos    │
├──────┼─────────────────────────┼──────┼────────┼──────────┤
│ 1    │ Usluge konsaltinga      │ 10   │ 5.000  │ 50.000   │
│ 2    │ Izrada dokumentacije    │ 1    │ 10.000 │ 10.000   │
├────────────────────────────────────────────────────────────┤
│                                  Osnovica:      60.000 RSD │
│                                  PDV (20%):     12.000 RSD │
│                                  ─────────────────────────│
│                                  UKUPNO:        72.000 RSD │
└────────────────────────────────────────────────────────────┘
```

---

## Dodatak: Nabavna inteligencija (M16)

### Katalog proizvoda

Za ugostiteljske i maloprodajne klijente, Saldora omogućava kreiranje kataloga proizvoda — kanonijskog spiska artikala sa alternativnim imenima (aliasima), kategorijama, prodajnim cenama i maržama. Sistem automatski pokušava da poveže stavke faktura sa unosima u katalogu koristeći fuzzy poređenje teksta (pg_trgm). Ovo normalizuje različite opise istog proizvoda od različitih dobavljača.

### Izveštaji o nabavci i prodaji

Na stranici Izveštaji ("Nabavka i prodaja" grupa) dostupna su četiri nova izveštaja:

| Izveštaj | Šta prikazuje |
|----------|--------------|
| **Kalkulacija** | Nabavna cena, marža i prodajna cena po stavci |
| **RUC** | Razlika u ceni grupisana po proizvodu iz kataloga |
| **Troškovi po kategoriji** | Ukupni troškovi grupisani po kategorijama iz kataloga |
| **Dnevna evidencija robe** | Sve primljene stavke za određeni datum |

### Objedinjena stranica izveštaja

Stranica `/izvestaji` sada objedinjuje sve izveštaje, katalog proizvoda i dnevnu evidenciju robe u jednom mestu. Navigacija se vrši putem tri grupe: **Opšti** (5 opštih izveštaja), **Nabavka i prodaja** (4 nabavna izveštaja), **Upravljanje** (katalog proizvoda).

---

**Kraj dokumenta**
