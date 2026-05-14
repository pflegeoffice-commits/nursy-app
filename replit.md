# Nursy – Pflege-Marketplace Prototype (Akut Plus Pflegeportal)

## Overview
Nursy is a German-language care marketplace prototype. Stack: Flask/PostgreSQL backend + plain HTML/CSS/JS frontend, port 5000.
Admin login: ADMIN_PASSWORD env var | Portal/Care login: über Admin anlegen (kein Demo-Account mehr)

## Key Pages
- `index.html` – landing page
- `leitstelle-ansicht.html` – Leitstelle (dispatch center) dashboard with Admiral floating-window layout
- `pfleger-einsatz.html` – mobile-first care worker app (receives alarms, shows mission + care plan + documentation + messages)
- `durchfuehrungsnachweis.html` – care documentation form
- `admin.html` – admin dashboard (billing + Pflege-Portal quick-access cards)
- `dashboard-care.html` – care worker dashboard (Pflege-Portal quick-access banner)
- `matching-patient.html` – **öffentlicher Bereich**: Anfrage stellen (Formular + Pfleger-Suche integriert) / Meine Verbindung (2 Tabs)
- `matching-pfleger.html` – **öffentlicher Bereich**: Anfragen (Eingehende gezielt + Offene zusammen) / Meine Patienten (2 Tabs)
- `passwort-reset.html` – Klienten-Passwort per E-Mail zurücksetzen (Token-basiert, 1h Gültigkeit)
- `billing-login.html` / `billing.html` – Verrechnungsstelle login + dashboard
- `nutzer-verwaltung.html` – Admiral-only: interne Benutzer, Rollen & Seitenzugriff verwalten
- `pflege-portal-login.html` – Akut Plus Pflegeportal login (care@test.at / Test1234!)
- `pflege-portal.html` – Akut Plus Pflegeportal: month calendar, shift self-registration (Bezirk + Fahrzeug), events, info
- `pflege-portal-register.html` – 2-step registration form for new applicants
- `pflege-portal-bewerbung.html` – token-based detailed application form (sent via admin)
- `pflege-portal-admin.html` – admin/admiral management: Bewerbungen, Dienstplan, Events, Info
- `fahrzeug-bestaetigung.html` – **internes Modul**: mobile Dienst- & Fahrzeugbestätigung (Signaturfeld, Fotos, 10 Checkboxen, PDF-Generierung); nur für eingeloggte Portal-Mitarbeiter
- `fahrzeug-admin.html` – **internes Modul**: Admin-Dateimanager für Fahrzeugbestätigungen (Ordnerbaum Bundesland→Bezirk→Datum, Suche/Filter, Detail-Modal, PDF-Download); nur Admin/Admiral
- `styles.css` – shared design system (CSS variables: --primary, --text, --muted, --panel, --panel2)

## Backend (server.py + PostgreSQL via DATABASE_URL)
Flask routes + PostgreSQL (psycopg2, falls back to SQLite if DATABASE_URL absent).
Compatibility layer: `db.py` – auto-translates `?`→`%s`, `INSERT OR IGNORE`→`ON CONFLICT DO NOTHING`,
`AUTOINCREMENT`→`BIGSERIAL`, `datetime('now','localtime')`→`CURRENT_TIMESTAMP`.
Passwords: werkzeug PBKDF2-SHA256 (`hash_pw`) + legacy-SHA256 fallback in `check_pw`.
Admin password: `ADMIN_PASSWORD` env var (default: NursyAdmin2024!).
Session secret: `SESSION_SECRET` env var (fallback: SECRET_KEY → dev hardcoded).

Key tables:
- `caregivers`, `patients`, `requests`, `dienste`, `admin_messages`
- `einsaetze` – dispatch missions; `einsatz_nachrichten` – messages
- `billing_users`, `leistungskatalog`, `rechnungen` – billing system
- `portal_bewerbungen` – applicants (status: ausstehend/gespräch/freigegeben/abgelehnt, token for link)
- `portal_dienste` – self-registered shifts (datum, art, fahrzeug, bezirk, user_id)
- `portal_events` + `portal_event_anmeldungen` – training/events with registrations
- `portal_info` – info posts (typ: info/warning/wichtig/success)
- `pfleger_bereitschaft_saetze` – Bereitschaftszulage rates per shift type (Früh/Spät/Nacht)
- `billing_settings` – Rechnungsfußzeile key/value (ap_*/nu_* fields)
- `push_subscriptions` – Web Push subscriptions (id, fahrzeug, user_id, endpoint, p256dh, auth)
- `matching_anfragen` – Pflegeanfragen (pflegebedarf+leistungen **Fernet-verschlüsselt** at-rest)
- `matching_verbindungen` – bestätigte Patient↔Pfleger-Verbindungen (UNIQUE patient_id)
- `public_password_reset_tokens` – Passwort-Reset-Token (email, token UNIQUE, expires_at, used)
- `fahrzeug_bestaetigungen` – Dienst- & Fahrzeugbestätigungen (id, caregiver_id/name, dienstnummer, fahrzeug, kennzeichen, bundesland, bezirk, datum, uhrzeit, 10×cb_*, bemerkungen, unterschrift_data, foto_pfade, formular_pfad, pdf_pfad, gespeichert_am, dienst_gestartet)
- `fahrzeuge.kennzeichen` – neue Spalte für Kfz-Kennzeichen
- `leitstelle_users.seiten_zugriff` / `billing_users.seiten_zugriff` – JSON-Array erlaubter Seiten-Keys per Benutzer

Key Portal API routes:
- `POST /api/portal/login|logout` · `GET /api/portal/me`
- `POST /api/portal/registrieren` – new applicant registration
- `GET/POST /api/portal/bewerbung/<token>` – token-based application form
- `GET/POST /api/portal/dienste` – shift calendar (self-registration with Bezirk + Fahrzeug)
- `DELETE /api/portal/dienste/<id>` – remove own shift
- `GET /api/portal/events` + `POST/DELETE /api/portal/events/<id>/anmelden`
- `GET /api/portal/info` · `GET /api/portal/fahrzeuge`
- `GET /api/admin/portal/bewerbungen` + `PUT /<id>` + `POST /<id>/link-senden`
- `GET/PUT/DELETE /api/admin/portal/dienste/<id>`
- `GET/POST/PUT/DELETE /api/admin/portal/events/<id>`
- `GET/POST /api/admin/portal/info` + `DELETE /<id>`
- `GET /api/admin/portal/stats|fahrzeuge`
- `GET /api/fahrzeug/aktuell` – Auto-fill-Daten für Formular (Person + Fahrzeug aus Session + portal_dienste)
- `GET /api/fahrzeug/check` – prüft ob für heute + aktuelles Fahrzeug bereits unterschrieben
- `POST /api/fahrzeug/bestaetigung` – speichert Formular + Unterschrift (JSON+PDF auf Disk, DB-Eintrag)
- `POST /api/fahrzeug/foto` – lädt Schadensfotos hoch (multipart, Zielordner: formulare/…/fotos/)
- `POST /api/fahrzeug/dienst-starten` – markiert Dienst als gestartet (nach gültiger Bestätigung)
- `GET /api/admin/fahrzeug/struktur` – Baumstruktur (Bundesland→Bezirk→Datum) mit Formular-Anzahl
- `GET /api/admin/fahrzeug/formulare` – Liste mit Filtern (name, dienstnummer, fahrzeug, kennzeichen, bundesland, bezirk, datum)
- `GET /api/admin/fahrzeug/formular/<id>` – vollständige Formulardaten inkl. Unterschrift
- `GET /api/admin/fahrzeug/pdf/<id>` – generiert & liefert PDF (reportlab, A4)
- `GET /api/admin/fahrzeug/foto/<id>/<filename>` – liefert Schadensfoto
- `GET /api/push/vapid-public-key` – returns VAPID public key for push subscription
- `POST /api/push/subscribe` – register device push subscription (endpoint, keys, fahrzeug)
- `POST /api/push/unsubscribe` – remove push subscription by endpoint or fahrzeug
- `POST /api/leitstelle/change-password` – Passwort ändern (old_password + new_password); löscht must_change_pw-Flag
- `GET /api/billing/pflegerpersonal?monat=YYYY-MM&frueh=X&spaet=Y&nacht=Z` – Pfleger Abrechnung (Dienste + Einsätze + Bereitschaftszulage)
- `GET/PUT /api/billing/pflegerpersonal/saetze` – Bereitschaftszulage-Sätze verwalten
- `GET/PUT /api/billing/settings` – Rechnungsfußzeile (Admiral only)
- `GET /api/admin/nutzer` · `POST /api/admin/nutzer/<typ>` · `PUT|DELETE /api/admin/nutzer/<typ>/<id>` – Benutzerverwaltung

## Invoice System (localStorage, per-user isolated)
All invoice-related localStorage keys are suffixed with `_<userId>` (resolved async via `/api/me` → `/api/billing/me` → 'default'):
- `nursy_invoice_template_v1_<uid>` – Rechnungsdesigner template (invoice-designer.js)
- `nursy_invoice_logo_v1_<uid>` – Logo (invoice-designer.js)
- `nursy_price_list_v1_<uid>` – Preisliste (price-list-designer.js + invoice-create.js)
- `nursy_invoices_v1_<uid>` – Gespeicherte Rechnungen (invoice-create.js + invoices-client.js)
- `nursy_service_records_v1_<uid>` – Leistungserfassungen (invoice-create.js)
Each care worker has fully independent template design, price list, and invoice list.

## Replit Setup
- Workflow `Start application` runs `python3 server.py` on port 5000.
- Database: PostgreSQL via `DATABASE_URL` secret (Replit Helium). `db.py` handles the compatibility layer.
- `--card: #ffffff` defined in leitstelle-ansicht.html :root (not in styles.css).
- Admiral floating window manager in leitstelle-ansicht.html (PANELS 0–5, STORE='nursy_ls_admiral_v5').
- Portal auth: `session['portal_user_id']` — checks portal_bewerbungen (freigegeben) then caregivers table.
- Admin/Admiral access: `_require_admin_or_admiral()` checks `session['admin']` OR `leitstelle_role` in (admiral, disponent).
- Demo portal user: care@test.at / Test1234! (pb_demo, status=freigegeben, 2. Bezirk, W-02).
- Login routes all use 2-step auth: fetch by email/dienstnummer, then `check_pw(stored_hash, pw)`.
- `nachrichten.id` uses BIGSERIAL (PostgreSQL) / INTEGER AUTOINCREMENT (SQLite).
