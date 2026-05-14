# Nursy – Pflege-Marketplace
### Akut Plus Pflegeportal · Vollständige Projektdokumentation

---

## Inhaltsverzeichnis
1. [Projektübersicht](#1-projektübersicht)
2. [Design-System & Farben](#2-design-system--farben)
3. [Benutzerrollen & Zugriffsrechte](#3-benutzerrollen--zugriffsrechte)
4. [Seitenübersicht & Funktionen](#4-seitenübersicht--funktionen)
5. [Benutzerabläufe (User Flows)](#5-benutzerabläufe-user-flows)
6. [Technische Architektur](#6-technische-architektur)
7. [Datenbank-Schema](#7-datenbank-schema)
8. [API-Routen Übersicht](#8-api-routen-übersicht)
9. [Setup & Betrieb](#9-setup--betrieb)

---

## 1. Projektübersicht

**Nursy** ist ein österreichischer Pflege-Marketplace-Prototyp der Firma **Akut Plus**.  
Die Plattform verbindet Pflegekräfte, Patienten/Klienten, Leitstellen-Disponenten und Administratoren über ein gemeinsames digitales System.

**Kernbereiche:**
- Einsatzvermittlung (Leitstelle ↔ Pfleger)
- Patienten-Pfleger-Matching (öffentlich)
- Digitale Pflege-Dokumentation (offline-fähig)
- Akut Plus Pflegeportal (Dienstplan, Bewerbungen, Events)
- Fahrzeug- & Dienstbestätigung (mit PDF & Unterschrift)
- Rechnungssystem für Pflegekräfte

**Tech-Stack:** Python 3 / Flask · PostgreSQL · HTML5 / CSS3 / Vanilla JS · Leaflet.js · ReportLab

---

## 2. Design-System & Farben

### Globale CSS-Variablen (`styles.css`)

| Variable | Hex-Wert | Verwendung |
|---|---|---|
| `--bg0` | `#eaf2ff` | Seitenhintergrund (sehr helles Blau) |
| `--bg1` | `#dbe7ff` | Zweiter Hintergrund (etwas dunkler) |
| `--text` | `#0f1a33` | Primärer Text (Dunkelblau-Schwarz) |
| `--muted` | `rgba(15,26,51,.65)` | Gedämpfter Text (65% Deckkraft) |
| `--primary` | `#3f6fe8` | Primärfarbe (Markenblau) |
| `--primary-soft` | `rgba(63,111,232,.25)` | Primärfarbe transparent (Hover, Borders) |
| `--accent` | `#3fc6c0` | Akzentfarbe (Türkis/Teal) |
| `--accent-soft` | `rgba(63,198,192,.25)` | Akzent transparent |
| `--panel` | `#ffffff` | Karten-Hintergrund (weiß) |
| `--panel2` | `#f2f6ff` | Zweiter Panel-Hintergrund (sehr helles Blau) |
| `--border` | `rgba(63,111,232,.18)` | Standard-Rahmen |
| `--radius` | `14px` | Eckenrundung (Cards, Inputs) |
| `--shadow` | `0 14px 40px rgba(15,26,51,.12)` | Card-Schatten |
| `--control-h` | `48px` | Mindesthöhe für Buttons & Inputs |

### Statusfarben

| Status / Bedeutung | Farbe | Hex |
|---|---|---|
| Erfolgreich / Aktiv / OK | Grün | `#22c55e` · `#15803d` · `#16a34a` |
| Warnung / Ausstehend | Amber | `#d97706` |
| Fehler / Abgelehnt | Rot | `#dc2626` · `#b91c1c` |
| Info / Blau | Blau | `#1d4ed8` · `#1e3a8a` |
| Deaktiviert / Grau | Grau | `#64748b` · `#6b7280` |
| Aktiver Einsatz (Badge) | Grün | `#22c55e` (Dot) · `#166534` (Text) |
| Abgesagt / Storniert | Rot | `#b91c1c` |
| Abgeschlossen | Grün | `#065f46` |

### Bereichs-Farbcodes (Gradient-Karten im Admin)

| Bereich | Gradient von → bis | Button-Farbe |
|---|---|---|
| Akut Plus Pflegeportal | `#0f4435` → `#059669` | `#065f46` |
| Verrechnungsstelle | `#0f2744` → `#1d4ed8` | `#0f2744` |
| Benutzerverwaltung | `#3b0764` → `#7c3aed` | `#3b0764` |
| Einsatzarchiv | `#1c1917` → `#78350f` | `#78350f` |
| E-Mail-Konfiguration | `#0c4a6e` → `#0284c7` | `#0c4a6e` |
| Datensicherungs-Karte | `#eff6ff` → `#f8faff` | Blauer Rand `#bfdbfe` |
| Export-Button | `#1d4ed8` (solide) | Weiße Schrift |
| Notformular-Button | `#eff6ff` | `#1d4ed8` |
| Cloud-Backup-Button | `#f0fdf4` | `#15803d` |

### Info-Post Typen (Pflegeportal)

| Typ | Bedeutung | Farbe |
|---|---|---|
| `info` | Allgemeine Info | Blau `#1d4ed8` |
| `warning` | Achtung / Hinweis | Amber `#d97706` |
| `wichtig` | Wichtige Mitteilung | Rot `#dc2626` |
| `success` | Positiv / Erledigt | Grün `#16a34a` |

### Nachrichten-Typen (Leitstelle)

| Typ | Badge-Farbe |
|---|---|
| `warn` | `#d97706` |
| `ok` | `#16a34a` |
| Standard | `--text` (`#0f1a33`) |

### Typographie

| Element | Größe | Gewicht |
|---|---|---|
| Schriftfamilie | `-apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif` | — |
| Basis | `15px` | `400` |
| H1 | `1.7rem` | `900` |
| H2 | `1.2rem` | `800` |
| H3 | `1rem` | `700` |
| Kleintext / Muted | `0.82rem` | `400` |
| Badge / Label | `0.72rem` | `600–700` |
| Button | `0.9rem` | `700` |

### Leitstelle (Sonderdesign)
- Hintergrund: `#0f2744` (sehr dunkles Marineblau)
- Cards: `--card: #ffffff`
- PWA Theme-Color: `#0f2744`
- Admiral-Fenster: schwebend, verschiebbar, minimierbar

---

## 3. Benutzerrollen & Zugriffsrechte

| Rolle | Login-Seite | Beschreibung |
|---|---|---|
| **Admiral** | `admin-login.html` | Vollzugriff — einzige Rolle mit Nutzerverwaltung & Billing-Settings |
| **Admin** | `admin-login.html` | Wie Admiral, ohne Nutzerverwaltung & Billing-Settings |
| **Disponent** | `leitstelle-login.html` | Leitstelle, Einsatzverwaltung, Patientensuche |
| **Pfleger (App)** | `login-care.html` | Mobile Pfleger-App: Einsätze, Dokumentation, Matching, Backup |
| **Klient** | `login-client.html` | Patienten-App: Anfragen, Verbindungen, Passwort-Reset |
| **Billing** | `billing-login.html` | Verrechnungsstelle: Rechnungen, Monatsabrechnung |
| **Portal-Mitarbeiter** | `pflege-portal-login.html` | Dienstplan, Events, Info, Fahrzeugbestätigung |

### Seitenzugriff-Steuerung
Disponenten und Billing-Nutzer können auf **einzelne Seiten begrenzt** werden.  
Spalte `seiten_zugriff` (JSON-Array) in `leitstelle_users` / `billing_users`.  
Verwaltung ausschließlich über `nutzer-verwaltung.html` (nur Admiral).

---

## 4. Seitenübersicht & Funktionen

---

### 🏠 Startseite
| | |
|---|---|
| **Datei** | `index.html` |
| **Zugang** | Öffentlich |
| **Aussehen** | Hintergrund `#eaf2ff`, Nursy-Logo, blauer CTA-Button `#3f6fe8` |
| **Funktion** | Links zu Pfleger-Login, Klienten-Login, Portal-Login |

---

### 📡 Leitstelle
| | |
|---|---|
| **Datei** | `leitstelle-ansicht.html` |
| **Zugang** | Disponent, Admin, Admiral |
| **Hintergrund** | `#0f2744` (sehr dunkles Marineblau) |
| **Panels** | Bis zu 6 schwebende Admiral-Fenster (PANELS 0–5) |
| **localStorage** | `nursy_ls_admiral_v5` (Panel-Positionen & Zustände) |

**Funktionen:**
- Echtzeit-Einsatzübersicht (offen / laufend / abgeschlossen)
- Patienten-Suche (Nursy-App-Patienten 🏠 + externe Daten)
- Einsatz erstellen & Pfleger zuweisen
- Nachrichten an Pfleger senden
- Karte mit OSRM-Routing (Leaflet + OpenStreetMap)
- Einsatzprotokoll & Archiv-Zugang

---

### 👩‍⚕️ Pfleger-Einsatz (Mobile)
| | |
|---|---|
| **Datei** | `pfleger-einsatz.html` |
| **Zugang** | Eingeloggte Pflegekraft (Push-Alarm) |
| **Aussehen** | Mobile-First (≤480px), Alarm-Banner Rot bei neuem Einsatz |

**Funktionen:**
- Alarm empfangen & bestätigen / ablehnen
- Einsatzdetails: Patient, Adresse, Pflegeplan
- Dokumentation direkt am Einsatz eintragen
- Nachrichtenaustausch mit Leitstelle

---

### 📊 Pfleger-Dashboard
| | |
|---|---|
| **Datei** | `dashboard-care.html` |
| **Zugang** | Eingeloggte Pflegekraft |
| **Hintergrund** | `#eaf2ff` (globales `--bg0`) |

**Karten (von oben nach unten):**

| # | Karte | Hintergrund | Inhalt |
|---|---|---|---|
| 1 | Profil | `#ffffff` | Name, Foto, Bezirk, Arbeitszeiten |
| 2 | Karte | `#ffffff` | Tages-Tour auf OpenStreetMap mit OSRM-Routing |
| 3 | Heutige Einsätze | `#ffffff` | Liste der heutigen Patienten |
| 4 | Matching-Anfragen | `#ffffff` | Eingehende Klienten-Anfragen |
| 5 | Meine Patienten | `#ffffff` | Alle verbundenen Langzeit-Patienten |
| 6 | Durchführungsnachweis | `#ffffff` | → Link zur DN-Seite |
| 7 | Dokumentation | `#ffffff` | 📋 Notformular · ☁️ Backup · Öffnen |
| 8 | Meine Rechnungen | `#ffffff` | → Link zur Rechnungsübersicht |
| 9 | 💾 Datensicherung | Blauer Verlauf (`#eff6ff`→`#f8faff`) | Export herunterladen + Backup wiederherstellen |

**Auto-Sync:** Beim Laden (3 Sek. Verzögerung) · alle 5 Minuten · bei localStorage-Änderungen

---

### 📝 Durchführungsnachweis
| | |
|---|---|
| **Datei** | `durchfuehrungsnachweis.html` |
| **Zugang** | Eingeloggte Pflegekraft |
| **Offline** | Ja — localStorage + Server-Sync |

**Felder:** 20 Maßnahmen mit Uhrzeit-Feldern · Tagesauswahl · historische Ansicht

---

### 📋 Notformular (Offline-Notfallformular)
| | |
|---|---|
| **Datei** | `notformular.html` |
| **Zugang** | Eingeloggte Pflegekraft (offline-fähig) |
| **Druck** | Print-CSS: alle Buttons ausgeblendet, nur Formularinhalt sichtbar |

**Abschnitte:**
1. Patientenauswahl (aus localStorage)
2. Stammdaten (Name, SVNr., Adresse, Telefon, E-Mail)
3. Notfallkontakt & Angehörige
4. Erkrankungen (farbige Chips), Allergien, Medikamente
5. DN-Status heute (✓ Erledigt / Offen + Uhrzeit)
6. Vitalzeichen-Tabelle (Blutdruck, Puls, Temperatur, Blutzucker, O₂, Atemfrequenz, Gewicht)
7. Notizfeld → beim Druck: gestrichelte Linien zum Beschreiben
8. Zwei Unterschriftsfelder (Pfleger + Patient/Angehöriger)

---

### 🏥 Admin-Dashboard
| | |
|---|---|
| **Datei** | `admin.html` |
| **Zugang** | Admin, Admiral |

**Tabs:**

| Tab | Inhalt |
|---|---|
| Übersicht | Statistik-Kacheln: Verbindungen (grün `#16a34a`), Anfragen (amber `#d97706`) |
| Klienten | 📱 App Klienten · 🌐 Portal-Klienten |
| Einsätze | Laufende & abgeschlossene Einsätze |
| Nachrichten | Admin-Broadcasts an Pfleger |

**Schnellzugriff-Karten:**

| Karte | Gradient | Beschreibung |
|---|---|---|
| 🏥 Akut Plus Pflegeportal | `#0f4435` → `#059669` | Portal-Verwaltung |
| 🧾 Verrechnungsstelle | `#0f2744` → `#1d4ed8` | Abrechnung & Rechnungen |
| 🔐 Benutzerverwaltung | `#3b0764` → `#7c3aed` | Nur Admiral sichtbar |
| 🗂️ Einsatzarchiv | `#1c1917` → `#78350f` | Archivierte Einsätze |
| 📧 E-Mail-Konfiguration | `#0c4a6e` → `#0284c7` | SMTP-Test |

---

### 🔐 Nutzerverwaltung (Admiral only)
| | |
|---|---|
| **Datei** | `nutzer-verwaltung.html` |
| **Zugang** | Nur Admiral |

**Sektionen:**

| Sektion | Funktion |
|---|---|
| Leitstelle-Benutzer | Disponenten & Admins: anlegen, bearbeiten, löschen, Seitenzugriff per Checkbox |
| Billing-Benutzer | Verrechnungsstelle-Zugänge verwalten |
| Pfleger (App) | Pflegekräfte anlegen, Dienstnummer vergeben, Passwort setzen |
| 📱 App Klienten | Patienten in `care_accepted_patients` (zugewiesene Klienten) |
| 🌐 Portal-Klienten | Öffentlich registrierte Klienten |

---

### 🔍 Matching
| | |
|---|---|
| **Klienten** | `matching-patient.html` |
| **Pfleger** | `matching-pfleger.html` |
| **Zugang** | Eingeloggter Klient / eingeloggte Pflegekraft |
| **Datenschutz** | Pflegebedarf & Leistungen: **Fernet-verschlüsselt** at-rest |

**Klienten-Seite (2 Tabs):**
- **Anfrage stellen** — Pflegebedarf-Formular + Pfleger-Suche (Bezirk, Verfügbarkeit, Qualifikation)
- **Meine Verbindung** — aktive Verbindung mit Pfleger anzeigen

**Pfleger-Seite (2 Tabs):**
- **Anfragen** — Eingehende gezielte + offene allgemeine Anfragen (gemeinsam)
- **Meine Patienten** — alle bestätigten Verbindungen mit Kontaktdaten

---

### 🟢 Akut Plus Pflegeportal
| | |
|---|---|
| **Login** | `pflege-portal-login.html` |
| **Pfleger** | `pflege-portal.html` |
| **Admin** | `pflege-portal-admin.html` |
| **Demo** | `care@test.at` / `Test1234!` |

**Pfleger-Ansicht:**

| Bereich | Funktion |
|---|---|
| Monatskalender | Eigene eingetragene Dienste farblich markiert |
| Dienstregistrierung | Datum, Diensttyp (Früh/Spät/Nacht), Bezirk, Fahrzeug |
| Events & Schulungen | Liste mit Anmelde- / Abmeldefunktion |
| Info-Board | Mitteilungen nach Typ (info / warning / wichtig / success) |

**Admin-Verwaltung:**

| Bereich | Funktion |
|---|---|
| Bewerbungen | Status: ausstehend → gespräch → freigegeben / abgelehnt |
| Token-Link | Token-basiertes Bewerbungsformular per E-Mail senden |
| Dienstplan | Alle eingetragenen Dienste einsehen & bearbeiten |
| Events | Schulungen anlegen, bearbeiten, löschen |
| Info-Posts | Mitteilungen veröffentlichen & löschen |

---

### 🚗 Fahrzeug-Modul
| | |
|---|---|
| **Bestätigung** | `fahrzeug-bestaetigung.html` |
| **Admin** | `fahrzeug-admin.html` |
| **Zugang** | Eingeloggte Portal-Mitarbeiter / Admin |

**Bestätigungsformular:**
- Auto-Befüllung aus Session + aktuellem Dienstplan-Eintrag
- 10 Pflicht-Checkboxen (Fahrzeugzustand & Vollständigkeit)
- Unterschriftsfeld (Canvas, Finger/Stift auf Touchscreen)
- Schadensfotos aufnehmen & hochladen (Kamera-API)
- PDF-Generierung (ReportLab, A4) + Ablage auf Disk
- Einmalig pro Tag + Fahrzeug — doppelte Abgabe blockiert (`/api/fahrzeug/check`)
- Nach Bestätigung: "Dienst starten"-Button → Dienst wird als aktiv markiert

**Admin-Dateimanager:**
- Baumstruktur: Bundesland → Bezirk → Datum → Formulare
- Suche & Filter (Name, Fahrzeug, Kennzeichen, Bezirk, Datum)
- Detail-Modal mit Unterschriftsbild & allen Fotos
- PDF-Download direkt im Browser

**Datei-Ablage auf dem Server:**
```
formulare/
└── <Bundesland>/
    └── <Bezirk>/
        └── <Datum>/
            ├── bestaetigung_<id>.json
            ├── bestaetigung_<id>.pdf
            └── fotos/
                └── schaden_<id>_1.jpg
```

---

### 🧾 Rechnungssystem
| | |
|---|---|
| **Seiten** | `billing.html`, `invoice-create.html`, `invoice-designer.html`, `invoices.html`, `price-list-designer.html` |
| **Zugang** | Billing-Nutzer, Admin, Admiral |

**Module:**

| Modul | Funktion |
|---|---|
| Rechnungsdesigner | Logo, Layout, Farbschema, Fußzeile personalisieren |
| Preislisten-Designer | Eigene Leistungen mit Preisen & Einheiten definieren |
| Rechnung erstellen | Leistungen wählen, Positionen berechnen, PDF exportieren |
| Rechnungsübersicht | Status-Filter, Download, Drucken |
| Monatsabrechnung | Dienste + Einsätze + Bereitschaftszulage je Monat |

**Datenisolation (localStorage-Keys mit `_<userId>` Suffix):**

| Key | Inhalt |
|---|---|
| `nursy_invoice_template_v1_<uid>` | Rechnungs-Template (Layout, Farben) |
| `nursy_invoice_logo_v1_<uid>` | Logo-Bild (Base64) |
| `nursy_price_list_v1_<uid>` | Eigene Preisliste |
| `nursy_invoices_v1_<uid>` | Gespeicherte Rechnungen |
| `nursy_service_records_v1_<uid>` | Leistungserfassungen |

---

### 💾 Datensicherung (Festplatten-Backup)
| | |
|---|---|
| **Export** | `GET /api/care/export` |
| **Import** | `POST /api/care/import` |
| **Zugang** | Eingeloggte Pflegekraft |

**Export-Dateistruktur:**
```
nursy_backup_Nachname_Vorname_YYYY-MM-DD.json
├── _meta           → Version, Exportdatum, Quelle ("Nursy Pflege-Marketplace")
├── profil          → Pfleger-Stammdaten (ohne Passwort-Hash)
├── patienten       → alle verbundenen Patienten inkl. JSON-Blob
├── df_eintraege    → alle Durchführungsnachweise (jeder Tag, jede Maßnahme)
├── wunddoku        → Wunddokumentation
├── pflegeplanung   → Wund- & Medikamentenplan
├── vitalzeichen    → Alle Messwerte
├── dokumentation   → Tages-Dokumentation
└── tourenlog       → letzte 90 Tage
```

**Import-Sicherheit:** Signaturprüfung (`source: Nursy Pflege-Marketplace`), cross-user Import blockiert (außer Admin), Bestätigungsdialog mit Datum + Anzahl Einträge.

---

### 🔄 Passwort-Reset
| | |
|---|---|
| **Datei** | `passwort-reset.html` |
| **Zugang** | Öffentlich |
| **Token-Gültigkeit** | 1 Stunde · einmalig verwendbar |

**Ablauf:** E-Mail eingeben → Token per SMTP → Link öffnen → Neues Passwort setzen

---

## 5. Benutzerabläufe (User Flows)

### Flow 1: Neuer Klient → Pfleger finden
```
index.html
  └── register-client.html         → Name, E-Mail, Passwort
  └── register-client-need.html    → Pflegebedarf eingeben
  └── verify-email.html            → E-Mail bestätigen
  └── dashboard-client.html        → Übersicht

matching-patient.html
  ├── Tab "Anfrage stellen"
  │   ├── Pflegebedarf-Formular (Fernet-verschlüsselt gespeichert)
  │   └── Pfleger suchen (Filter: Bezirk, Verfügbarkeit, Qualifikation)
  │       └── Anfrage senden →→→ Pfleger erhält Benachrichtigung
  │
  └── Tab "Meine Verbindung"
      └── Aktive Verbindung anzeigen (nach Bestätigung durch Pfleger)
```

---

### Flow 2: Leitstellen-Einsatz (Disponent → Pfleger)
```
leitstelle-ansicht.html (Disponent)
  ├── Patient suchen (Nursy-DB 🏠 oder manuell)
  ├── Einsatz erstellen → Pfleger zuweisen
  └── Nachrichten senden

pfleger-einsatz.html (Pfleger)
  ├── Push-Benachrichtigung empfangen (Web Push / VAPID)
  ├── Alarm annehmen → Navigation starten
  ├── Vor-Ort: Dokumentation eintragen
  └── Einsatz abschließen

leitstelle-ansicht.html (Disponent)
  └── Status-Update in Echtzeit → Protokoll → Archiv
```

---

### Flow 3: Neuer Portal-Mitarbeiter
```
pflege-portal-register.html
  ├── Schritt 1: Name, E-Mail, Geburtsdatum
  └── Schritt 2: Qualifikation, Erfahrung, Bezirk
      └── Status: "ausstehend"

pflege-portal-admin.html (Admin)
  ├── Bewerbung prüfen → Status: "gespräch"
  ├── Token-Link generieren → per E-Mail senden
  └── Nach Bewerbung: Status → "freigegeben"

pflege-portal-bewerbung.html (Bewerber, Token-Link)
  └── Vollständiges Bewerbungsformular ausfüllen

pflege-portal-login.html
  └── Zugang aktiv → Portal nutzbar
```

---

### Flow 4: Dienst- und Fahrzeugbestätigung
```
pflege-portal-login.html → einloggen

fahrzeug-bestaetigung.html
  ├── Daten auto-befüllt (Name, Fahrzeug, Bezirk aus Dienstplan)
  ├── 10 Checkboxen abhaken
  ├── Unterschrift zeichnen (Canvas, Touchscreen)
  ├── Schadensfotos aufnehmen (optional)
  └── Absenden → PDF generiert → auf Server gespeichert
      └── "Dienst starten" Button → bestätigen

fahrzeug-admin.html (Admin)
  └── Baumstruktur: Bundesland → Bezirk → Datum
      └── Formular öffnen → PDF herunterladen
```

---

### Flow 5: Monatsabschluss & Datensicherung
```
dashboard-care.html
  └── Karte "💾 Datensicherung"
      └── "⬇️ Export herunterladen" klicken
          ├── Server sammelt alle Daten → JSON erstellen
          ├── Datei: nursy_backup_Mustermann_Max_2026-05-31.json
          └── → Download → auf Nursy-Festplatte kopieren

Bei Gerätewechsel / Datenverlust:
  └── "⬆️ Backup wiederherstellen"
      ├── JSON-Datei auswählen
      ├── Bestätigungsdialog (Datum + Anzahl Einträge)
      └── Daten werden in Datenbank eingespielt → Reload
```

---

### Flow 6: Rechnungserstellung (Pflegekraft)
```
invoice-designer.html   → Layout & Logo einrichten (einmalig)
price-list-designer.html → Leistungen & Preise definieren (einmalig)

invoice-create.html
  ├── Klient auswählen
  ├── Leistungen aus Preisliste wählen + Mengen eingeben
  ├── Summe wird automatisch berechnet
  └── Rechnung speichern → PDF exportieren

invoices.html
  └── Alle Rechnungen: Status, Filter, Download
```

---

## 6. Technische Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                      Browser / PWA                          │
│  HTML5 · CSS3 · Vanilla JS · localStorage · Service Worker │
│  Leaflet.js (Karte) · Web Push API · Canvas API            │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP Fetch API (JSON)
┌───────────────────────────▼─────────────────────────────────┐
│              Flask Backend  (server.py, Port 5000)          │
│  Session-Auth · Werkzeug PBKDF2-SHA256 · Fernet             │
│  ReportLab (PDF) · SMTP (E-Mail) · VAPID (Web Push)        │
└───────────────────────────┬─────────────────────────────────┘
                            │ psycopg2
┌───────────────────────────▼─────────────────────────────────┐
│              PostgreSQL  (Replit Helium, via DATABASE_URL)   │
│              db.py — Kompatibilitäts-Layer                  │
│   ? → %s · AUTOINCREMENT → BIGSERIAL                        │
│   INSERT OR IGNORE → ON CONFLICT DO NOTHING                 │
│   datetime('now','localtime') → CURRENT_TIMESTAMP           │
└─────────────────────────────────────────────────────────────┘
```

### Offline-Strategie
| Schicht | Technologie | Verhalten |
|---|---|---|
| Dokumentation | localStorage | Zuerst lokal speichern |
| Auto-Sync | Fetch API | Beim Laden (3s), alle 5 Min., bei Storage-Events |
| Notformular | Kein Server | Vollständig offline (nur localStorage) |
| Karte | Leaflet / OSM | Tiles werden gecacht (Service Worker) |

### Datensicherheit
| Bereich | Methode |
|---|---|
| Passwörter | PBKDF2-SHA256 (Werkzeug) + SHA256 Legacy-Fallback |
| Matching-Daten | Fernet-Verschlüsselung at-rest |
| Session | Flask-Session mit `SESSION_SECRET` env var |
| Admin-Passwort | `ADMIN_PASSWORD` env var |
| Push | VAPID-Schlüsselpaar (VAPID_PRIVATE/PUBLIC_KEY) |

---

## 7. Datenbank-Schema

### Kernentitäten

| Tabelle | Beschreibung |
|---|---|
| `caregivers` | Pflegekräfte (App-Nutzer), inkl. Dienstnummer, Bezirk, Foto |
| `patients` | Alle Patienten (Leitstelle + Portal registriert) |
| `care_accepted_patients` | Pfleger↔Patient-Zuweisung (`patient_json` Blob, `active` Flag) |
| `requests` | Einsatz-Anfragen von Klienten |
| `dienste` | Geplante Dienste |
| `einsaetze` | Leitstelle-Einsätze mit Status & Zeitstempel |
| `einsatz_nachrichten` | Nachrichten pro Einsatz (BIGSERIAL id) |
| `admin_messages` | Admin-Broadcasts an Pflegekräfte |

### Dokumentation (pro Patient)

| Tabelle | Schlüssel | Inhalt |
|---|---|---|
| `patient_df_eintraege` | `patient_id, datum` | DN-Einträge (state JSON, 20 Maßnahmen) |
| `patient_wunddoku` | `id = pid_datum` | Wunddokumentation-JSON |
| `patient_pflegeplanung` | `patient_id` | Wund- & Medikamentenplan (JSON) |
| `patient_vitalzeichen` | `id` (UUID) | Einzelne Messwerte (7 Parameter) |
| `patient_dokumentation` | `patient_id, datum` | Tages-Dokumentation |
| `care_tourenlog` | `caregiver_id, datum` | Tourenlog-JSON pro Tag |

### Portal & Fahrzeug

| Tabelle | Beschreibung |
|---|---|
| `portal_bewerbungen` | Bewerber (token, status: ausstehend/gespräch/freigegeben/abgelehnt) |
| `portal_dienste` | Selbst-eingetragene Dienste (datum, art, fahrzeug, bezirk, user_id) |
| `portal_events` | Schulungen & Events mit Teilnehmerzahl |
| `portal_event_anmeldungen` | Event-Registrierungen (user↔event UNIQUE) |
| `portal_info` | Info-Posts (typ: info/warning/wichtig/success) |
| `fahrzeuge` | Fahrzeugliste inkl. Kennzeichen |
| `fahrzeug_bestaetigungen` | Formular-Einträge (10×cb_, Unterschrift als Data-URL, Foto-Pfade, PDF-Pfad) |

### Rechnungen & Billing

| Tabelle | Beschreibung |
|---|---|
| `billing_users` | Verrechnungsstelle-Zugänge (inkl. `seiten_zugriff` JSON) |
| `leistungskatalog` | Standard-Leistungspositionen |
| `rechnungen` | Erstellte Rechnungen mit Status |
| `billing_settings` | Rechnungsfußzeile (ap_* / nu_* Felder, key-value) |
| `pfleger_bereitschaft_saetze` | Bereitschaftszulage-Sätze (Früh / Spät / Nacht) |

### Infrastruktur

| Tabelle | Beschreibung |
|---|---|
| `leitstelle_users` | Disponenten & Admins (leitstelle_role, seiten_zugriff JSON) |
| `push_subscriptions` | Web-Push-Subscriptions (endpoint, p256dh, auth, fahrzeug) |
| `matching_anfragen` | Fernet-verschlüsselte Pflegeanfragen |
| `matching_verbindungen` | Bestätigte Verbindungen (UNIQUE patient_id) |
| `public_password_reset_tokens` | Reset-Tokens (email, token UNIQUE, expires_at, used) |

---

## 8. API-Routen Übersicht

### Authentifizierung
| Methode | Route | Beschreibung |
|---|---|---|
| POST | `/api/login` | Pfleger-Login |
| POST | `/api/logout` | Pfleger-Logout |
| GET | `/api/me` | Aktuelle Session |
| POST | `/api/leitstelle/change-password` | Leitstelle-Passwort ändern |
| POST | `/api/portal/login` | Portal-Login |
| POST | `/api/portal/logout` | Portal-Logout |
| GET | `/api/portal/me` | Portal-Session |

### Pfleger-Dokumentation
| Methode | Route | Beschreibung |
|---|---|---|
| GET | `/api/care/profil` | Profil laden |
| GET | `/api/care/meine-patienten` | Verbundene Patienten |
| GET/POST | `/api/care/df/<pat_id>/<datum>` | DN-Einträge |
| GET/POST | `/api/care/backup` | Server-Backup (Bulk-Sync) |
| GET | `/api/care/export` | Vollständiger JSON-Export (Download) |
| POST | `/api/care/import` | Backup-Datei wiederherstellen |
| GET/POST | `/api/care/pflegeplanung/<pat_id>` | Pflegeplanung |
| GET/POST | `/api/care/wunddoku/<pat_id>` | Wunddokumentation |
| GET/POST | `/api/care/tourenlog/<datum>` | Tourenlog |
| GET/POST | `/api/care/vitalzeichen/<pat_id>` | Vitalzeichen |

### Matching
| Methode | Route | Beschreibung |
|---|---|---|
| GET | `/api/patienten` | Patienten-Suche (Nursy + extern) |
| GET | `/api/care/matching/eingehende` | Eingehende Anfragen |
| GET | `/api/care/matching/offene` | Offene allgemeine Anfragen |
| POST | `/api/care/matching/anfrage/<id>/annehmen` | Anfrage bestätigen |

### Admin
| Methode | Route | Beschreibung |
|---|---|---|
| GET | `/api/admin/app-klienten` | App-Klienten auflisten |
| DELETE | `/api/admin/app-klienten/<id>` | App-Klient entfernen |
| GET | `/api/admin/nutzer` | Alle Nutzer |
| POST | `/api/admin/nutzer/<typ>` | Nutzer anlegen |
| PUT | `/api/admin/nutzer/<typ>/<id>` | Nutzer bearbeiten |
| DELETE | `/api/admin/nutzer/<typ>/<id>` | Nutzer löschen |
| GET/PUT | `/api/billing/settings` | Rechnungsfußzeile (Admiral) |

### Fahrzeug-Modul
| Methode | Route | Beschreibung |
|---|---|---|
| GET | `/api/fahrzeug/aktuell` | Auto-Fill-Daten aus Session + Dienstplan |
| GET | `/api/fahrzeug/check` | Bereits heute ausgefüllt? |
| POST | `/api/fahrzeug/bestaetigung` | Formular speichern (JSON + PDF) |
| POST | `/api/fahrzeug/foto` | Schadensfoto hochladen |
| POST | `/api/fahrzeug/dienst-starten` | Dienst als gestartet markieren |
| GET | `/api/admin/fahrzeug/struktur` | Ordnerbaum (Bundesland→Bezirk→Datum) |
| GET | `/api/admin/fahrzeug/formulare` | Liste mit Filtern |
| GET | `/api/admin/fahrzeug/formular/<id>` | Vollständige Formulardaten |
| GET | `/api/admin/fahrzeug/pdf/<id>` | PDF generieren & liefern |
| GET | `/api/admin/fahrzeug/foto/<id>/<filename>` | Schadensfoto liefern |

### Portal
| Methode | Route | Beschreibung |
|---|---|---|
| GET/POST | `/api/portal/dienste` | Dienstplan (Selbstregistrierung) |
| DELETE | `/api/portal/dienste/<id>` | Eigenen Dienst löschen |
| GET | `/api/portal/events` | Events laden |
| POST | `/api/portal/events/<id>/anmelden` | Event anmelden |
| DELETE | `/api/portal/events/<id>/anmelden` | Event abmelden |
| GET | `/api/portal/info` | Info-Posts laden |
| GET | `/api/portal/fahrzeuge` | Fahrzeugliste |
| GET | `/api/admin/portal/bewerbungen` | Alle Bewerbungen |
| PUT | `/api/admin/portal/bewerbungen/<id>` | Status ändern |
| POST | `/api/admin/portal/bewerbungen/<id>/link-senden` | Token-Link per E-Mail |
| GET/POST | `/api/admin/portal/events/<id>` | Event verwalten |
| GET/POST | `/api/admin/portal/info` | Info-Post erstellen |
| DELETE | `/api/admin/portal/info/<id>` | Info-Post löschen |
| GET | `/api/admin/portal/stats` | Portal-Statistiken |

### Push & Billing
| Methode | Route | Beschreibung |
|---|---|---|
| GET | `/api/push/vapid-public-key` | VAPID Public Key |
| POST | `/api/push/subscribe` | Push-Subscription anlegen |
| POST | `/api/push/unsubscribe` | Push-Subscription entfernen |
| GET | `/api/billing/pflegerpersonal` | Monatsabrechnung (`?monat=YYYY-MM`) |
| GET/PUT | `/api/billing/pflegerpersonal/saetze` | Bereitschaftszulage-Sätze |

---

## 9. Setup & Betrieb

### Umgebungsvariablen

| Variable | Pflicht | Beschreibung |
|---|---|---|
| `DATABASE_URL` | ✅ | PostgreSQL-Verbindungsstring |
| `ADMIN_PASSWORD` | ✅ | Admin-Login-Passwort |
| `SESSION_SECRET` | ✅ | Flask-Session-Schlüssel |
| `SMTP_HOST` | ✅ | E-Mail-Server Host |
| `SMTP_PORT` | ✅ | E-Mail-Server Port |
| `SMTP_USER` | ✅ | E-Mail-Benutzername |
| `SMTP_PASS` | ✅ | E-Mail-Passwort |
| `SMTP_FROM` | ✅ | Absender-Adresse |
| `VAPID_PRIVATE_KEY` | ⚠️ | Web Push (optional, für Push-Funktion) |
| `VAPID_PUBLIC_KEY` | ⚠️ | Web Push (optional) |
| `FERNET_KEY` | ⚠️ | Matching-Datenverschlüsselung (optional, wird auto-generiert) |

### Anwendung starten

```bash
python3 server.py
# → Server läuft auf http://0.0.0.0:5000
```

### Demo-Zugänge

| Bereich | Zugangsdaten |
|---|---|
| Admin | Passwort aus `ADMIN_PASSWORD` env var |
| Pflegeportal (Demo) | `care@test.at` / `Test1234!` |

### Fallback ohne PostgreSQL
Wenn `DATABASE_URL` nicht gesetzt ist, fällt `db.py` automatisch auf **SQLite** zurück (nur für Entwicklung).

### Projekt-Struktur

```
/
├── server.py                 → Flask-Backend (alle Routen)
├── db.py                     → Datenbank-Kompatibilitäts-Layer
├── styles.css                → Globales Design-System
├── script.js                 → Gemeinsame JS-Hilfsfunktionen
├── patients.js               → Patienten-Helpers
├── sw.js                     → Service Worker (PWA, Caching)
├── leitstelle-sw.js          → Service Worker für Leitstelle
│
├── index.html                → Startseite (öffentlich)
├── dashboard-care.html       → Pfleger-Dashboard
├── leitstelle-ansicht.html   → Leitstelle (Admiral-Layout)
├── admin.html                → Admin-Dashboard
├── nutzer-verwaltung.html    → Benutzerverwaltung (Admiral)
│
├── pflege-portal*.html       → Akut Plus Pflegeportal
├── fahrzeug-*.html           → Fahrzeug-Modul
├── matching-*.html           → Matching-Bereich
├── invoice-*.html            → Rechnungssystem
├── billing*.html             → Verrechnungsstelle
│
└── formulare/                → PDF & Foto-Ablage (auto-erstellt)
    └── <Bundesland>/<Bezirk>/<Datum>/
```

---

*Erstellt: 2026-05-13 · Nursy – Akut Plus Pflegeportal · Alle Rechte vorbehalten*
