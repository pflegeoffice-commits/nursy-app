#!/usr/bin/env python3
import os, json, uuid, hashlib, hmac, time, smtplib, ssl, base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from cryptography.fernet import Fernet
from flask import Flask, request, jsonify, session, send_from_directory, redirect
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash as _wz_check
from db import get_db, USE_PG

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, 'uploads')

# ── E-Mail (SMTP) ─────────────────────────────────────────────────────────────

def _smtp_config():
    from_raw = os.environ.get('SMTP_FROM', 'pflege@akutplus.at')
    return {
        'host':       os.environ.get('SMTP_HOST', ''),
        'port':       int(''.join(filter(str.isdigit, os.environ.get('SMTP_PORT', '587'))) or 587),
        'user':       os.environ.get('SMTP_USER', ''),
        'password':   os.environ.get('SMTP_PASS', ''),
        'from_email': from_raw,
        'from_name':  'Akut Plus Pflege',
    }

def smtp_configured():
    c = _smtp_config()
    return all([c['host'], c['user'], c['password'], c['from_email']])

def send_email(to, subject, text_body, html_body=None):
    """Sendet eine E-Mail via SMTP. Gibt (True, '') oder (False, fehlermeldung) zurück."""
    c = _smtp_config()
    if not smtp_configured():
        missing = [k for k in ('host','user','password','from_email') if not c[k]]
        return False, f"SMTP nicht konfiguriert. Fehlende Secrets: {', '.join(missing)}"

    sender = f"{c['from_name']} <{c['from_email']}>" if c['from_name'] else c['from_email']

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From']    = sender
    msg['To']      = to

    msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
    if html_body:
        msg.attach(MIMEText(html_body, 'html', 'utf-8'))

    try:
        port = c['port']
        if port == 465:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(c['host'], port, context=ctx, timeout=15) as srv:
                srv.login(c['user'], c['password'])
                srv.sendmail(c['from_email'], [to], msg.as_string())
        else:
            with smtplib.SMTP(c['host'], port, timeout=15) as srv:
                srv.ehlo()
                srv.starttls(context=ssl.create_default_context())
                srv.ehlo()
                srv.login(c['user'], c['password'])
                srv.sendmail(c['from_email'], [to], msg.as_string())
        return True, ''
    except smtplib.SMTPAuthenticationError:
        return False, 'SMTP-Authentifizierung fehlgeschlagen (Benutzer/Passwort prüfen)'
    except smtplib.SMTPConnectError:
        return False, f'Verbindung zu {c["host"]}:{port} fehlgeschlagen'
    except Exception as ex:
        return False, str(ex)


# ── Fernet-Verschlüsselung (öffentlicher Bereich – at-rest) ──────────────────
def _fernet():
    """Leitet Fernet-Schlüssel aus SESSION_SECRET ab (SHA-256 → base64url)."""
    secret = os.environ.get('SESSION_SECRET') or os.environ.get('SECRET_KEY') or 'nursy-dev-fallback-2024'
    raw_key = hashlib.sha256(('nursy:data:' + secret).encode()).digest()
    return Fernet(base64.urlsafe_b64encode(raw_key))

def enc(text):
    """Verschlüsselt einen String (Fernet/AES-128). Leer → unverändert."""
    if not text:
        return text
    try:
        return _fernet().encrypt(str(text).encode()).decode()
    except Exception:
        return text

def dec(text):
    """Entschlüsselt einen Fernet-String. Nicht-verschlüsselte Werte werden durchgelassen (Rückwärtskompatibilität)."""
    if not text:
        return text
    try:
        return _fernet().decrypt(text.encode()).decode()
    except Exception:
        return text  # Legacy-Daten (unverschlüsselt) unverändert zurückgeben


os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {'png','jpg','jpeg','gif','webp','pdf','doc','docx','txt','heic','heif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

app = Flask(__name__, static_folder=BASE_DIR)
app.secret_key = os.environ.get('SESSION_SECRET') or os.environ.get('SECRET_KEY') or 'nursy-dev-secret-2024'
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# When running behind Replit's HTTPS proxy, use Secure + SameSite=None so that
# session cookies are forwarded correctly even inside cross-origin iframes.
_is_https = bool(
    os.environ.get('REPLIT_DEPLOYMENT') or
    os.environ.get('REPLIT_DEV_DOMAIN') or
    os.environ.get('REPLIT_DOMAINS')
)
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE']   = _is_https
app.config['SESSION_COOKIE_SAMESITE'] = 'None' if _is_https else 'Lax'

# ── Security Headers (nach jedem Response) ───────────────────────────────────

@app.after_request
def add_security_headers(resp):
    resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
    resp.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    resp.headers.setdefault('X-XSS-Protection', '1; mode=block')
    resp.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
    resp.headers.setdefault(
        'Permissions-Policy',
        'camera=(self), microphone=(), geolocation=(self), payment=()'
    )
    resp.headers.setdefault(
        'Content-Security-Policy',
        (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://unpkg.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com; "
            "font-src 'self' https://fonts.gstatic.com data:; "
            "img-src 'self' data: blob: https://*.tile.openstreetmap.org https://tile.openstreetmap.org https://*.cartocdn.com https://basemaps.cartocdn.com; "
            "connect-src 'self' https://nominatim.openstreetmap.org https://router.project-osrm.org https://*.cartocdn.com; "
            "worker-src 'self' blob:; "
            "manifest-src 'self'; "
            "frame-ancestors 'self';"
        )
    )
    if _is_https:
        resp.headers.setdefault(
            'Strict-Transport-Security',
            'max-age=31536000; includeSubDomains; preload'
        )
    return resp


# ── Admin-Passwort (aus Umgebungsvariable) ───────────────────────────────────

ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'NursyAdmin2024!')

# ── Web Push Notifications ───────────────────────────────────────────────────

def _send_push_to_fahrzeug(fahrzeug, title, body, url='/pfleger-einsatz.html'):
    """Send a Web Push notification to all subscribed devices for a vehicle."""
    try:
        from pywebpush import webpush, WebPushException
        priv_key   = os.environ.get('VAPID_PRIVATE_KEY', '').replace('\\n', '\n')
        vapid_sub  = os.environ.get('VAPID_EMAIL', 'mailto:admin@akutplus.at')
        if not priv_key:
            return
        with get_db() as db:
            subs = db.execute(
                'SELECT * FROM push_subscriptions WHERE fahrzeug=?', (fahrzeug,)
            ).fetchall()
        dead_endpoints = []
        for sub in subs:
            try:
                webpush(
                    subscription_info={
                        'endpoint': sub['endpoint'],
                        'keys': {'p256dh': sub['p256dh'], 'auth': sub['auth']}
                    },
                    data=json.dumps({'title': title, 'body': body, 'url': url}),
                    vapid_private_key=priv_key,
                    vapid_claims={'sub': vapid_sub}
                )
            except WebPushException as ex:
                resp = getattr(ex, 'response', None)
                if resp is not None and resp.status_code in (404, 410):
                    dead_endpoints.append(sub['endpoint'])
            except Exception:
                pass
        if dead_endpoints:
            with get_db() as db:
                for ep in dead_endpoints:
                    db.execute('DELETE FROM push_subscriptions WHERE endpoint=?', (ep,))
                db.commit()
    except Exception:
        pass


# ── Token Auth (fallback for environments where cookies fail) ────────────────

def _make_token(role, uid=''):
    ts   = str(int(time.time()))
    data = f"{role}|{uid}|{ts}"
    sig  = hmac.new(app.secret_key.encode(), data.encode(), 'sha256').hexdigest()
    return f"{data}|{sig}"

def _verify_token(token, max_age=86400 * 7):
    try:
        parts = token.split('|')
        if len(parts) != 4:
            return None
        role, uid, ts, sig = parts
        if time.time() - int(ts) > max_age:
            return None
        data     = f"{role}|{uid}|{ts}"
        expected = hmac.new(app.secret_key.encode(), data.encode(), 'sha256').hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        return {'role': role, 'uid': uid}
    except Exception:
        return None

def _token_from_request():
    auth = request.headers.get('X-Nursy-Token', '')
    if auth:
        return _verify_token(auth)
    return None

def init_db():
    with get_db() as db:
        db.execute('''CREATE TABLE IF NOT EXISTS caregivers (
            id TEXT PRIMARY KEY,
            vorname TEXT NOT NULL,
            nachname TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            gender TEXT DEFAULT '',
            address TEXT DEFAULT '',
            plz TEXT DEFAULT '',
            ort TEXT DEFAULT '',
            bezirk TEXT DEFAULT '',
            dienstnummer TEXT DEFAULT '',
            qualifikation TEXT DEFAULT '',
            profil_extra TEXT DEFAULT '{}',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        # Spalten-Migrationen für caregivers – direkt nach CREATE TABLE,
        # mit eigenem Commit damit Transaction-Fehler später nichts rückgängig machen
        for _cg_m in [
            "ALTER TABLE caregivers ADD COLUMN dienstnummer TEXT DEFAULT ''",
            "ALTER TABLE caregivers ADD COLUMN qualifikation TEXT DEFAULT ''",
            "ALTER TABLE caregivers ADD COLUMN profil_extra TEXT DEFAULT '{}'",
        ]:
            db.execute_safe(_cg_m)
        db.commit()
        db.execute('''CREATE TABLE IF NOT EXISTS patients (
            id TEXT PRIMARY KEY,
            vorname TEXT NOT NULL,
            nachname TEXT NOT NULL,
            email TEXT DEFAULT '',
            password_hash TEXT DEFAULT '',
            gender TEXT DEFAULT '',
            address TEXT DEFAULT '',
            plz TEXT DEFAULT '',
            ort TEXT DEFAULT '',
            bezirk TEXT DEFAULT '',
            birth TEXT DEFAULT '',
            hauptgrund TEXT DEFAULT '',
            haeufigkeit TEXT DEFAULT '',
            angehoerige TEXT DEFAULT '[]',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS requests (
            id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            patient_name TEXT NOT NULL,
            patient_gender TEXT DEFAULT '',
            patient_address TEXT DEFAULT '',
            patient_plz TEXT DEFAULT '',
            patient_ort TEXT DEFAULT '',
            patient_birth TEXT DEFAULT '',
            patient_data TEXT DEFAULT '{}',
            anamnese TEXT DEFAULT '{}',
            pflegestufe TEXT DEFAULT '',
            frequenz TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            caregiver_id TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS caregiver_status (
            caregiver_id TEXT PRIMARY KEY,
            status TEXT DEFAULT 'active',
            plan TEXT DEFAULT 'normal',
            notes TEXT DEFAULT '',
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS dienste (
            id TEXT PRIMARY KEY,
            caregiver_id TEXT NOT NULL,
            caregiver_name TEXT NOT NULL,
            datum TEXT NOT NULL,
            von TEXT NOT NULL,
            bis TEXT NOT NULL,
            typ TEXT DEFAULT 'bereitschaft',
            fahrzeug TEXT DEFAULT '',
            notiz TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS admin_messages (
            id TEXT PRIMARY KEY,
            text TEXT NOT NULL,
            typ TEXT DEFAULT 'info',
            aktiv INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS einsaetze (
            id TEXT PRIMARY KEY,
            nummer TEXT DEFAULT '',
            art TEXT DEFAULT '',
            dringlichkeit TEXT DEFAULT '',
            patient_name TEXT DEFAULT '',
            patient_adresse TEXT DEFAULT '',
            patient_plz TEXT DEFAULT '',
            patient_ort TEXT DEFAULT '',
            patient_geburt TEXT DEFAULT '',
            patient_sv TEXT DEFAULT '',
            patient_tel TEXT DEFAULT '',
            bezirk TEXT DEFAULT '',
            schluessel TEXT DEFAULT '',
            adressinfo TEXT DEFAULT '',
            problem TEXT DEFAULT '',
            risiken TEXT DEFAULT '[]',
            allergien TEXT DEFAULT '',
            medikamente TEXT DEFAULT '',
            anordnungen TEXT DEFAULT '',
            qualifikation TEXT DEFAULT '',
            fahrzeug TEXT DEFAULT '',
            disponent TEXT DEFAULT '',
            datum TEXT DEFAULT '',
            zeit TEXT DEFAULT '',
            ang_name TEXT DEFAULT '',
            ang_tel TEXT DEFAULT '',
            notiz TEXT DEFAULT '',
            extra TEXT DEFAULT '{}',
            status TEXT DEFAULT 'alarmiert',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        # Migration: Zeitstempel-Spalten für Status-Übergänge
        for col in ('zeit_unterwegs', 'zeit_eingetroffen', 'zeit_beendet', 'zeit_angenommen'):
            db.execute_safe(f"ALTER TABLE einsaetze ADD COLUMN {col} TEXT DEFAULT ''")
        # Migration: Leitstelle-Änderungs-Flag für Auftragslage-Goldmarkierung
        db.execute_safe("ALTER TABLE einsaetze ADD COLUMN ls_geaendert TEXT DEFAULT ''")
        db.execute('''CREATE TABLE IF NOT EXISTS einsatz_nachrichten (
            id TEXT PRIMARY KEY,
            einsatz_id TEXT NOT NULL,
            sender TEXT DEFAULT 'pfleger',
            text TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS einsatz_protokoll (
            id         BIGSERIAL PRIMARY KEY,
            einsatz_id TEXT NOT NULL,
            zeitpunkt  TEXT DEFAULT CURRENT_TIMESTAMP,
            aktion     TEXT NOT NULL,
            details    TEXT DEFAULT '',
            akteur     TEXT DEFAULT '',
            akteur_typ TEXT DEFAULT 'system'
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS leitstelle_users (
            id TEXT PRIMARY KEY,
            vorname TEXT NOT NULL,
            nachname TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            rolle TEXT DEFAULT 'disponent',
            aktiv INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS fahrzeuge (
            name       TEXT PRIMARY KEY,
            typ        TEXT DEFAULT 'HKP',
            bundesland TEXT DEFAULT '',
            bezirk     TEXT DEFAULT '',
            aktiv      INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS vehicle_sessions (
            fahrzeug     TEXT PRIMARY KEY,
            caregiver_id TEXT DEFAULT '',
            caregiver_name TEXT DEFAULT '',
            dienstnummer TEXT DEFAULT '',
            eingeloggt_seit TEXT DEFAULT '',
            status TEXT DEFAULT 'bereit'
        )''')
        # Pfleger → Leitstelle Nachrichten
        db.execute('''CREATE TABLE IF NOT EXISTS nachrichten (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            von_name     TEXT DEFAULT '',
            von_dnr      TEXT DEFAULT '',
            fahrzeug     TEXT DEFAULT '',
            typ          TEXT DEFAULT 'nachricht',
            text         TEXT DEFAULT '',
            gelesen      INTEGER DEFAULT 0,
            created_at   TEXT DEFAULT (datetime('now','localtime'))
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS patient_dokumente (
            id          TEXT PRIMARY KEY,
            patient_id  TEXT NOT NULL,
            typ         TEXT DEFAULT 'sonstiges',
            original_name TEXT DEFAULT '',
            stored_name TEXT DEFAULT '',
            beschreibung TEXT DEFAULT '',
            uploaded_by TEXT DEFAULT '',
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS einsatz_dokumente (
            id          TEXT PRIMARY KEY,
            einsatz_id  TEXT NOT NULL,
            original_name TEXT DEFAULT '',
            stored_name TEXT DEFAULT '',
            beschreibung TEXT DEFAULT '',
            uploaded_by TEXT DEFAULT '',
            file_data   TEXT DEFAULT '',
            mime_type   TEXT DEFAULT '',
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        )''')
        # Migrations
        for migration in [
            "ALTER TABLE caregivers ADD COLUMN dienstnummer TEXT DEFAULT ''",
            "ALTER TABLE fahrzeuge ADD COLUMN bundesland TEXT DEFAULT ''",
            "ALTER TABLE fahrzeuge ADD COLUMN bezirk TEXT DEFAULT ''",
            "ALTER TABLE einsaetze ADD COLUMN patient_id TEXT DEFAULT ''",
            "ALTER TABLE rechnungen ADD COLUMN freitext TEXT DEFAULT ''",
            "ALTER TABLE leitstelle_users ADD COLUMN seiten_zugriff TEXT DEFAULT '[]'",
            "ALTER TABLE leitstelle_users ADD COLUMN notizen TEXT DEFAULT ''",
            "ALTER TABLE billing_users ADD COLUMN seiten_zugriff TEXT DEFAULT '[]'",
            "ALTER TABLE billing_users ADD COLUMN notizen TEXT DEFAULT ''",
            "ALTER TABLE caregivers ADD COLUMN profil_extra TEXT DEFAULT '{}'",
            "ALTER TABLE patients ADD COLUMN profil_extra TEXT DEFAULT '{}'",
            "ALTER TABLE leitstelle_users ADD COLUMN must_change_pw INTEGER DEFAULT 0",
            "ALTER TABLE leitstelle_users ADD COLUMN pw_reset_token TEXT DEFAULT NULL",
            "ALTER TABLE leitstelle_users ADD COLUMN pw_reset_expires TEXT DEFAULT NULL",
            "ALTER TABLE vehicle_sessions ADD COLUMN lat REAL DEFAULT NULL",
            "ALTER TABLE vehicle_sessions ADD COLUMN lng REAL DEFAULT NULL",
            "ALTER TABLE vehicle_sessions ADD COLUMN position_ts TEXT DEFAULT NULL",
            "ALTER TABLE einsaetze ADD COLUMN archiviert INTEGER DEFAULT 0",
            "ALTER TABLE einsaetze ADD COLUMN archiviert_am TEXT DEFAULT ''",
            "ALTER TABLE einsaetze ADD COLUMN bundesland TEXT DEFAULT ''",
            "ALTER TABLE caregivers ADD COLUMN profil_extra TEXT DEFAULT '{}'",
            "ALTER TABLE leitstelle_users ADD COLUMN disponier_bundesland TEXT DEFAULT ''",
            "ALTER TABLE leitstelle_users ADD COLUMN disponier_bezirk TEXT DEFAULT ''",
            "ALTER TABLE rechnungen ADD COLUMN billing_user_id TEXT DEFAULT ''",
            "ALTER TABLE patients ADD COLUMN patient_status TEXT DEFAULT 'aktiv'",
            "ALTER TABLE patient_dokumente ADD COLUMN file_data TEXT DEFAULT ''",
            "ALTER TABLE patient_dokumente ADD COLUMN mime_type TEXT DEFAULT ''",
            "ALTER TABLE fahrzeuge ADD COLUMN kennzeichen TEXT DEFAULT ''",
            "ALTER TABLE fahrzeug_bestaetigungen ADD COLUMN agb_akzeptiert INTEGER DEFAULT 0",
        ]:
            db.execute_safe(migration)
        # ── Seed: Admiral-User (einmalig, falls nicht vorhanden) ─────────
        db.execute_safe(
            '''INSERT OR IGNORE INTO leitstelle_users
               (id, vorname, nachname, email, password_hash, rolle, aktiv, must_change_pw, seiten_zugriff, notizen)
               VALUES (?,?,?,?,?,?,?,?,?,?)''',
            ['ls_admiral01', 'Admiral', 'Nursy', 'admiral@nursy.at',
             hash_pw('Admiral2024!'), 'admiral', 1, 0, '[]', '']
        )
        db.commit()
        # ── Neue Tabellen: Care-Matching, Tourenlog, Wunddoku ────────────
        db.execute('''CREATE TABLE IF NOT EXISTS care_accepted_patients (
            id TEXT PRIMARY KEY,
            caregiver_id TEXT NOT NULL,
            patient_id TEXT NOT NULL,
            patient_json TEXT NOT NULL DEFAULT '{}',
            accepted_at TEXT DEFAULT CURRENT_TIMESTAMP,
            active INTEGER DEFAULT 1
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS care_tourenlog (
            id TEXT PRIMARY KEY,
            caregiver_id TEXT NOT NULL,
            datum TEXT NOT NULL,
            log_json TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS patient_wunddoku (
            id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            datum TEXT NOT NULL,
            data_json TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        # ── Fahrzeug-Bestätigung ─────────────────────────────────────────
        db.execute('''CREATE TABLE IF NOT EXISTS fahrzeug_bestaetigungen (
            id TEXT PRIMARY KEY,
            caregiver_id TEXT DEFAULT '',
            caregiver_name TEXT DEFAULT '',
            dienstnummer TEXT DEFAULT '',
            fahrzeug TEXT DEFAULT '',
            kennzeichen TEXT DEFAULT '',
            bundesland TEXT DEFAULT '',
            bezirk TEXT DEFAULT '',
            datum TEXT DEFAULT '',
            uhrzeit TEXT DEFAULT '',
            cb_uebernommen INTEGER DEFAULT 0,
            cb_sauber INTEGER DEFAULT 0,
            cb_schaeden INTEGER DEFAULT 0,
            cb_material INTEGER DEFAULT 0,
            cb_med_geprueft INTEGER DEFAULT 0,
            cb_med_verwendbar INTEGER DEFAULT 0,
            cb_haftung INTEGER DEFAULT 0,
            cb_selbstbehalt INTEGER DEFAULT 0,
            cb_rueckgabe INTEGER DEFAULT 0,
            cb_eigen_haftung INTEGER DEFAULT 0,
            bemerkungen TEXT DEFAULT '',
            unterschrift_data TEXT DEFAULT '',
            foto_pfade TEXT DEFAULT '[]',
            formular_pfad TEXT DEFAULT '',
            pdf_pfad TEXT DEFAULT '',
            gespeichert_am TEXT DEFAULT '',
            dienst_gestartet INTEGER DEFAULT 0,
            dienst_gestartet_am TEXT DEFAULT ''
        )''')
        # ── Verträge & digitale Unterschriften ───────────────────────────
        db.execute('''CREATE TABLE IF NOT EXISTS vertraege (
            id TEXT PRIMARY KEY,
            caregiver_id TEXT NOT NULL DEFAULT '',
            caregiver_name TEXT DEFAULT '',
            titel TEXT NOT NULL DEFAULT '',
            datei_pfad TEXT DEFAULT '',
            erstellt_am TEXT DEFAULT '',
            aktiv INTEGER DEFAULT 1
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS vertrag_signaturen (
            id TEXT PRIMARY KEY,
            vertrag_id TEXT NOT NULL DEFAULT '',
            patient_name TEXT DEFAULT '',
            unterschrift_data TEXT DEFAULT '',
            signiert_am TEXT DEFAULT '',
            token TEXT DEFAULT '',
            token_verwendet INTEGER DEFAULT 0,
            ip_adresse TEXT DEFAULT ''
        )''')
        db.commit()
        # ── Matching-System (Nursy öffentlicher Bereich) ─────────────────
        db.execute('''CREATE TABLE IF NOT EXISTS matching_anfragen (
            id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            pflegebedarf TEXT DEFAULT '',
            leistungen TEXT DEFAULT '[]',
            bezirk TEXT DEFAULT '',
            schicht_wunsch TEXT DEFAULT '[]',
            modus TEXT DEFAULT 'entwurf',
            ziel_caregiver_id TEXT DEFAULT '',
            status TEXT DEFAULT 'aktiv',
            angenommen_von TEXT DEFAULT '',
            angenommen_am TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS matching_verbindungen (
            id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            caregiver_id TEXT NOT NULL,
            anfrage_id TEXT DEFAULT '',
            verbunden_am TEXT DEFAULT CURRENT_TIMESTAMP,
            aktiv INTEGER DEFAULT 1
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS public_password_reset_tokens (
            id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            email TEXT NOT NULL,
            token TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        db.commit()
        # Fahrzeuge werden nur über die Admin-Oberfläche angelegt (kein Demo-Seeding)
        # ── Billing: Verrechnungsstelle ──────────────────────────────────
        db.execute('''CREATE TABLE IF NOT EXISTS billing_users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            rolle TEXT DEFAULT 'verrechnungsstelle',
            aktiv INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS leistungskatalog (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            beschreibung TEXT DEFAULT '',
            kategorie TEXT DEFAULT 'Allgemein',
            preis REAL DEFAULT 0.0,
            einheit TEXT DEFAULT 'Einsatz',
            mwst_prozent REAL DEFAULT 0.0,
            aktiv INTEGER DEFAULT 1,
            sort_order INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS rechnungen (
            id TEXT PRIMARY KEY,
            nummer TEXT NOT NULL UNIQUE,
            typ TEXT DEFAULT 'notdienst',
            layout TEXT DEFAULT 'akutplus',
            empfaenger_name TEXT DEFAULT '',
            empfaenger_adresse TEXT DEFAULT '',
            empfaenger_plz TEXT DEFAULT '',
            empfaenger_ort TEXT DEFAULT '',
            empfaenger_email TEXT DEFAULT '',
            einsatz_id TEXT DEFAULT '',
            positionen TEXT DEFAULT '[]',
            netto REAL DEFAULT 0,
            mwst REAL DEFAULT 0,
            brutto REAL DEFAULT 0,
            status TEXT DEFAULT 'entwurf',
            faellig_am TEXT DEFAULT '',
            notiz TEXT DEFAULT '',
            erstellt_von TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        # Leistungskatalog — Akut Plus Pflege Notdienst Preisliste (gültig ab April 2026)
        default_lk = [
            # ── Pflegeeinsätze ───────────────────────────────────────────────
            ('lk01','Hauskrankenpflegeeinsatz',
             '45–65 € je nach Aufwand und Tageszeit. Reguläre Pflegebetreuung zu Hause.',
             'Pflegeeinsatz',55.0,'Einsatz',0.0,10),
            ('lk02','Pflegeeinsatz (pflegerelevante Situation)',
             '45–65 € je nach Aufwand. Bei akut aufgetretenen pflegerelevanten Situationen.',
             'Pflegeeinsatz',55.0,'Einsatz',0.0,20),
            ('lk03','Palliativbegleitung',
             '45–65 € je Einsatz. Palliativ-Einsätze werden wöchentlich verrechnet.',
             'Palliativ',55.0,'Einsatz',0.0,30),
            # ── Telemedizinische Leistungen ──────────────────────────────────
            ('lk10','Erstvisite (Telemedizin)',
             'Telemedizinische Erstuntersuchung ab 130 €.',
             'Telemedizin',130.0,'Visite',0.0,100),
            ('lk11','Folgevisite (Telemedizin)',
             'Telemedizinische Folgeuntersuchung ab 95 €.',
             'Telemedizin',95.0,'Visite',0.0,110),
            ('lk12','Optionale Untersuchung: EKG',
             'Bei Folgevisite – Elektrokardiogramm.',
             'Telemedizin',30.0,'Einheit',0.0,120),
            ('lk13','Optionale Untersuchung: Ultraschall',
             'Bei Folgevisite – Sonographie.',
             'Telemedizin',50.0,'Einheit',0.0,130),
            ('lk14','Optionale Untersuchung: Blutgasanalyse',
             'Bei Folgevisite – Blutgasanalyse.',
             'Telemedizin',35.0,'Einheit',0.0,140),
            ('lk15','Technische Pauschale (inkl. Pflegeperson)',
             'Wird bei jeder Visite vom PFLEGENOTDIENST verrechnet.',
             'Telemedizin',70.0,'Visite',0.0,150),
            # ── Notdienst / Sonstige Kosten ──────────────────────────────────
            ('lk04','Akut-Einsatzgebühr',
             '90 € einmalig – für die schnelle Organisation und den Einsatz innerhalb von 24 Stunden.',
             'Notdienst',90.0,'einmalig',0.0,200),
            ('lk05','Alarmierungsgebühr',
             'Wird pro Einsatz zusätzlich verrechnet.',
             'Notdienst',3.50,'Einsatz',0.0,210),
            ('lk06','Fahrtkosten (ab dem 5. Kilometer)',
             '0,76 €/km ab dem 5. Kilometer ab Standort des Pflegepersonals.',
             'Notdienst',0.76,'km',0.0,220),
            ('lk07','Versorgung außerhalb regulärer Zeiten',
             'Reguläre Zeiten: Mo–Fr 06:00–18:00. Außerhalb gilt ein Aufschlag von 15 €.',
             'Notdienst',15.0,'Einsatz',0.0,230),
            ('lk08','Wochenend-/Feiertagszuschlag',
             '30 € (Samstag/Sonntag) bzw. 40 € (gesetzliche Feiertage).',
             'Notdienst',30.0,'Einsatz',0.0,240),
        ]
        for row in default_lk:
            try:
                db.execute(
                    'INSERT OR IGNORE INTO leistungskatalog (id,name,beschreibung,kategorie,preis,einheit,mwst_prozent,sort_order) '
                    'VALUES (?,?,?,?,?,?,?,?)',
                    row
                )
            except Exception:
                pass
        db.execute('''CREATE TABLE IF NOT EXISTS startseite_blocks (
            id TEXT PRIMARY KEY,
            titel TEXT DEFAULT '',
            inhalt TEXT DEFAULT '',
            bild_url TEXT DEFAULT '',
            link_text TEXT DEFAULT '',
            link_url TEXT DEFAULT '',
            typ TEXT DEFAULT 'info',
            aktiv INTEGER DEFAULT 1,
            reihenfolge INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')
        # ── Pflege-Portal ─────────────────────────────────────────────────────
        db.execute('''CREATE TABLE IF NOT EXISTS portal_bewerbungen (
            id TEXT PRIMARY KEY,
            vorname TEXT NOT NULL,
            nachname TEXT NOT NULL,
            email TEXT NOT NULL,
            telefon TEXT DEFAULT '',
            password_hash TEXT DEFAULT '',
            qualifikation TEXT DEFAULT '',
            erfahrung_jahre INTEGER DEFAULT 0,
            bezirk TEXT DEFAULT '',
            fahrzeug_pref TEXT DEFAULT '',
            dienst_arten TEXT DEFAULT '[]',
            adresse TEXT DEFAULT '',
            status TEXT DEFAULT 'ausstehend',
            token TEXT DEFAULT '',
            notizen TEXT DEFAULT '',
            rolle TEXT DEFAULT 'pfleger',
            dienstnummer TEXT DEFAULT '',
            caregiver_id TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )''')
        # Migrations für portal_bewerbungen – hier nach CREATE TABLE damit sie
        # auf bestehenden Tabellen greifen, ohne von fehlender Tabelle blockiert zu werden
        for _pb_migration in [
            "ALTER TABLE portal_bewerbungen ADD COLUMN rolle TEXT DEFAULT 'pfleger'",
            "ALTER TABLE portal_bewerbungen ADD COLUMN dienstnummer TEXT DEFAULT ''",
            "ALTER TABLE portal_bewerbungen ADD COLUMN caregiver_id TEXT DEFAULT ''",
        ]:
            db.execute_safe(_pb_migration)
        db.commit()
        db.execute('''CREATE TABLE IF NOT EXISTS portal_dienste (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            user_name TEXT NOT NULL,
            datum TEXT NOT NULL,
            art TEXT NOT NULL,
            von TEXT DEFAULT '',
            bis TEXT DEFAULT '',
            fahrzeug TEXT DEFAULT '',
            bezirk TEXT DEFAULT '',
            status TEXT DEFAULT 'eingetragen',
            notiz TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS portal_events (
            id TEXT PRIMARY KEY,
            titel TEXT NOT NULL,
            datum TEXT NOT NULL,
            von TEXT DEFAULT '',
            bis TEXT DEFAULT '',
            typ TEXT DEFAULT 'Schulung',
            beschreibung TEXT DEFAULT '',
            ort TEXT DEFAULT '',
            slots INTEGER DEFAULT 0,
            erstellt_von TEXT DEFAULT '',
            aktiv INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS portal_event_anmeldungen (
            id TEXT PRIMARY KEY,
            event_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            user_name TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            UNIQUE(event_id, user_id)
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS portal_info (
            id TEXT PRIMARY KEY,
            titel TEXT NOT NULL,
            text TEXT NOT NULL,
            typ TEXT DEFAULT 'info',
            erstellt_von TEXT DEFAULT '',
            aktiv INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )''')
        # Seed demo events
        for ev in [
            ('ev01','EKG-Grundkurs','2026-05-12','09:00','12:00','Schulung','Grundlagen der EKG-Ableitung und Interpretation.','Wien, Zentrale',8),
            ('ev02','Wundmanagement Update','2026-05-20','14:00','17:00','Schulung','Aktuelle Standards im Wundmanagement.','Wien, Zentrale',12),
            ('ev03','Teamabend Frühjahr 2026','2026-05-28','18:00','21:00','Event','Gemeinsamer Abend für alle Mitarbeiterinnen.','Wien, Gasthof zum Wohl',40),
        ]:
            try:
                db.execute('INSERT OR IGNORE INTO portal_events (id,titel,datum,von,bis,typ,beschreibung,ort,slots) VALUES (?,?,?,?,?,?,?,?,?)', ev)
            except Exception:
                pass
        # Seed demo info
        for inf in [
            ('inf01','Neue Dienstplanrichtlinie ab Juni','Ab Juni gilt die neue Richtlinie für Überstundenregelungen.','warning','Admin'),
            ('inf02','Pflichtschulung Brandschutz – Frist 31.05.','Alle Mitarbeiterinnen müssen bis 31. Mai die Brandschutzschulung absolviert haben.','wichtig','Admin'),
            ('inf03','Kollektivvertragliche Gehaltserhöhung ab 1. Juni','Wir freuen uns, eine Erhöhung von 4,2 % bekanntgeben zu können.','success','Admin'),
        ]:
            try:
                db.execute('INSERT OR IGNORE INTO portal_info (id,titel,text,typ,erstellt_von) VALUES (?,?,?,?,?)', inf)
            except Exception:
                pass
        # ── Digitales Fahrtenbuch ──
        db.execute('''CREATE TABLE IF NOT EXISTS fahrtenbuch (
            id TEXT PRIMARY KEY,
            fahrzeug TEXT NOT NULL DEFAULT '',
            kennzeichen TEXT DEFAULT '',
            fahrer TEXT DEFAULT '',
            user_id TEXT DEFAULT '',
            datum TEXT NOT NULL DEFAULT '',
            uhrzeit_von TEXT DEFAULT '',
            uhrzeit_bis TEXT DEFAULT '',
            von_ort TEXT DEFAULT '',
            nach_ort TEXT DEFAULT '',
            zweck TEXT DEFAULT '',
            km_start INTEGER DEFAULT 0,
            km_ende INTEGER DEFAULT 0,
            km_gesamt INTEGER DEFAULT 0,
            getankt_liter REAL DEFAULT 0,
            kraftstoff_art TEXT DEFAULT '',
            bemerkungen TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )''')
        # Migration: Spalten nachrüsten falls Tabelle bereits existiert
        db.execute_safe("ALTER TABLE fahrtenbuch ADD COLUMN getankt_liter REAL DEFAULT 0")
        db.execute_safe("ALTER TABLE fahrtenbuch ADD COLUMN kraftstoff_art TEXT DEFAULT ''")

        # ── Care-Daten: Dokumentation, Vitalzeichen, Durchführungsnachweis, Pflegeplanung ──
        db.execute('''CREATE TABLE IF NOT EXISTS patient_dokumentation (
            id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            patient_name TEXT DEFAULT '',
            birth TEXT DEFAULT '',
            typ TEXT DEFAULT 'allgemein',
            plan TEXT DEFAULT '',
            grp TEXT DEFAULT 'Pfleger',
            datum TEXT DEFAULT '',
            uhrzeit TEXT DEFAULT '',
            text TEXT DEFAULT '',
            important INTEGER DEFAULT 0,
            wund_refs TEXT DEFAULT '[]',
            updated_at TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS patient_vitalzeichen (
            id TEXT PRIMARY KEY,
            patient_id TEXT NOT NULL,
            datum TEXT NOT NULL,
            uhrzeit TEXT NOT NULL,
            sys INTEGER,
            dia INTEGER,
            puls INTEGER,
            spo2 INTEGER,
            temp REAL,
            vz_score INTEGER,
            gewicht REAL,
            groesse INTEGER,
            bz REAL,
            bz_methode TEXT DEFAULT '',
            in_ml INTEGER,
            out_ml INTEGER,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS patient_df_eintraege (
            patient_id TEXT NOT NULL,
            datum TEXT NOT NULL,
            state TEXT DEFAULT '{}',
            updated_at TEXT DEFAULT (datetime('now','localtime')),
            PRIMARY KEY (patient_id, datum)
        )''')
        db.execute('''CREATE TABLE IF NOT EXISTS patient_pflegeplaene (
            patient_id TEXT PRIMARY KEY,
            plaene TEXT DEFAULT '[]',
            wund_plan TEXT DEFAULT 'null',
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )''')
        # ── Pflegerpersonal-Abrechnung ────────────────────────────────────────
        db.execute('''CREATE TABLE IF NOT EXISTS pfleger_bereitschaft_saetze (
            art TEXT PRIMARY KEY,
            satz_eur REAL DEFAULT 0.0,
            beschreibung TEXT DEFAULT ''
        )''')
        for art, satz, beschr in [
            ('Frühdienst',  65.00, 'Bereitschaftszulage 06:00–14:00'),
            ('Spätdienst',  70.00, 'Bereitschaftszulage 14:00–22:00'),
            ('Nachtdienst', 85.00, 'Bereitschaftszulage 22:00–06:00'),
        ]:
            db.execute(
                'INSERT OR IGNORE INTO pfleger_bereitschaft_saetze (art,satz_eur,beschreibung) VALUES (?,?,?)',
                [art, satz, beschr]
            )
        # ── Billing-Einstellungen (Rechnungsfußzeile etc.) ───────────────────
        db.execute('''CREATE TABLE IF NOT EXISTS billing_settings (
            key TEXT PRIMARY KEY,
            value TEXT DEFAULT ''
        )''')
        for k, v in {
            'ap_firma':   'Akut Plus PFLEGENOTDIENST GmbH',
            'ap_strasse': 'Musterstraße 1',
            'ap_plzort':  '1010 Wien',
            'ap_email':   'office@akutplus.at',
            'ap_web':     'www.akutplus.at',
            'ap_uid':     'ATU12345678',
            'ap_iban':    'AT12 0000 0000 0000 0000',
            'ap_bic':     'MUSTRAT',
            'nu_firma':   'Nursy GmbH',
            'nu_strasse': 'Plattformstraße 1',
            'nu_plzort':  '1010 Wien',
            'nu_email':   'office@nursy.at',
            'nu_web':     'www.nursy.at',
            'nu_uid':     'ATU87654321',
            'nu_iban':    'AT98 0000 0000 0000 0001',
            'nu_bic':     'NRSYATW1',
            'ap_freitext_default': 'Zahlbar innerhalb von 14 Tagen ohne Abzug.\nBei Fragen: office@akutplus.at\n\nVielen Dank für Ihr Vertrauen!',
            'nu_freitext_default': 'Zahlbar innerhalb von 14 Tagen.\nVielen Dank für die Nutzung von Nursy.',
        }.items():
            db.execute('INSERT OR IGNORE INTO billing_settings (key,value) VALUES (?,?)', [k, v])

        # ── Rechnungs-Vorlagen ────────────────────────────────────────────────
        db.execute('''CREATE TABLE IF NOT EXISTS billing_vorlagen (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            typ TEXT DEFAULT 'beide',
            betreff TEXT DEFAULT '',
            freitext TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        db.execute('''CREATE TABLE IF NOT EXISTS push_subscriptions (
            id TEXT PRIMARY KEY,
            fahrzeug TEXT NOT NULL,
            user_id TEXT DEFAULT '',
            endpoint TEXT NOT NULL UNIQUE,
            p256dh TEXT NOT NULL,
            auth TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )''')

        db.commit()

        # ── Einmalige Bereinigung: Wien-Demo-Fahrzeuge entfernen ─────────────
        try:
            for fz_name in ['W-01', 'W-02', 'W-03']:
                db.execute('DELETE FROM vehicle_sessions WHERE fahrzeug=?', [fz_name])
                db.execute('DELETE FROM fahrzeuge WHERE name=?', [fz_name])
            db.commit()
        except Exception:
            try: db.rollback()
            except Exception: pass


def hash_pw(pw):
    """Erzeugt einen sicheren PBKDF2-SHA256-Hash (werkzeug)."""
    return generate_password_hash(pw, method='pbkdf2:sha256', salt_length=16)

def check_pw(stored_hash, pw):
    """Prüft Passwort gegen werkzeug-PBKDF2 oder Legacy-SHA256."""
    if not stored_hash or not pw:
        return False
    legacy = hashlib.sha256(pw.encode('utf-8')).hexdigest()
    if hmac.compare_digest(stored_hash, legacy):
        return True
    try:
        return _wz_check(stored_hash, pw)
    except Exception:
        return False

def row_to_dict(row):
    return dict(row) if row else None

# Initialize DB on module load so gunicorn workers also set up tables
init_db()


# ── Auth helpers ────────────────────────────────────────────────────────────



# ── API: Pflegekraft ────────────────────────────────────────────────────────

@app.route('/api/register/care', methods=['POST'])
def register_care():
    data = request.get_json(silent=True) or {}
    required = ['vorname', 'nachname', 'email', 'password']
    for f in required:
        if not data.get(f, '').strip():
            return jsonify({'error': f'Feld "{f}" fehlt'}), 400
    if len(data['password']) < 8:
        return jsonify({'error': 'Passwort muss mind. 8 Zeichen haben'}), 400

    uid = 'c' + uuid.uuid4().hex[:8]
    try:
        with get_db() as db:
            db.execute(
                'INSERT INTO caregivers (id,vorname,nachname,email,password_hash,gender,address,plz,ort,bezirk) '
                'VALUES (?,?,?,?,?,?,?,?,?,?)',
                [uid, data['vorname'].strip(), data['nachname'].strip(),
                 data['email'].strip().lower(), hash_pw(data['password']),
                 data.get('gender',''), data.get('address',''),
                 data.get('plz',''), data.get('ort',''), data.get('bezirk','')]
            )
            db.commit()
    except Exception:
        return jsonify({'error': 'Diese E-Mail-Adresse ist bereits registriert'}), 409

    session['user_id']   = uid
    session['user_role'] = 'care'
    user = {'id': uid, 'vorname': data['vorname'], 'nachname': data['nachname'],
            'email': data['email'], 'role': 'care'}
    return jsonify({'ok': True, 'user': user})


@app.route('/api/login', methods=['POST'])
def login_unified():
    """Einheitlicher Login-Endpunkt – Rolle wird im Body mitgeschickt.
    Unterstützte Rollen: care, client.
    Delegiert an die rollenspezifischen Logik-Funktionen.
    """
    data = request.get_json(silent=True) or {}
    role = data.get('role', '').strip().lower()
    if role == 'care':
        return login_care()
    if role in ('client', 'patient'):
        return login_client()
    return jsonify({'ok': False, 'error': 'Unbekannte Rolle. Bitte "care" oder "client" angeben.'}), 400


@app.route('/api/login/client', methods=['POST'])
def login_client():
    data  = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    pw    = data.get('password', '')
    if not email or not pw:
        return jsonify({'error': 'E-Mail / Benutzer-ID und Passwort erforderlich'}), 400
    with get_db() as db:
        # Try by email first, then by patient ID (for patients without email)
        row = db.execute('SELECT * FROM patients WHERE email=? AND email != ?', [email, '']).fetchone()
        if not row:
            row = db.execute('SELECT * FROM patients WHERE id=?', [email]).fetchone()
    if not row or not check_pw(row['password_hash'] or '', pw):
        return jsonify({'error': 'E-Mail / Benutzer-ID oder Passwort falsch'}), 401
    session['patient_id'] = row['id']
    session['user_role']  = 'client'
    return jsonify({'ok': True, 'user': {
        'id': row['id'],
        'vorname': row['vorname'], 'nachname': row['nachname'],
        'email': row['email'],
        'bezirk': row['bezirk'] or '',
        'hauptgrund': row['hauptgrund'] or '',
        'role': 'client'
    }})


@app.route('/api/logout/client', methods=['POST'])
def logout_client():
    session.pop('patient_id', None)
    if session.get('user_role') == 'client':
        session.pop('user_role', None)
    return jsonify({'ok': True})


@app.route('/api/client/account', methods=['DELETE'])
def client_delete_account():
    pid = session.get('patient_id')
    if not pid:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    with get_db() as db:
        db.execute('DELETE FROM matching_verbindungen WHERE patient_id=?', [pid])
        db.execute('DELETE FROM matching_anfragen WHERE patient_id=?', [pid])
        db.execute("DELETE FROM public_password_reset_tokens WHERE email=(SELECT COALESCE(email,'') FROM patients WHERE id=?)", [pid])
        db.execute('DELETE FROM patients WHERE id=?', [pid])
        db.commit()
    session.clear()
    return jsonify({'ok': True})


@app.route('/api/client/me')
def client_me():
    pid = session.get('patient_id')
    if not pid:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    with get_db() as db:
        row = db.execute('SELECT * FROM patients WHERE id=?', [pid]).fetchone()
    if not row:
        return jsonify({'ok': False, 'error': 'Patient nicht gefunden'}), 404
    return jsonify({'ok': True, 'user': {
        'id': row['id'],
        'vorname': row['vorname'], 'nachname': row['nachname'],
        'email': row['email'] or '',
        'bezirk': row['bezirk'] or '',
        'ort': row['ort'] or '',
        'hauptgrund': row['hauptgrund'] or '',
        'role': 'client'
    }})


@app.route('/api/login/care', methods=['POST'])
def login_care():
    data  = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    pw    = data.get('password', '')

    with get_db() as db:
        row = db.execute(
            'SELECT * FROM caregivers WHERE email=?',
            [email]
        ).fetchone()

    if not row or not check_pw(row['password_hash'], pw):
        return jsonify({'error': 'E-Mail oder Passwort falsch'}), 401

    session['user_id']   = row['id']
    session['user_role'] = 'care'
    user = {'id': row['id'], 'vorname': row['vorname'], 'nachname': row['nachname'],
            'email': row['email'], 'gender': row['gender'],
            'address': row['address'], 'plz': row['plz'], 'ort': row['ort'],
            'dienstnummer': row['dienstnummer'] or '', 'role': 'care'}
    return jsonify({'ok': True, 'user': user})


# ── Fahrzeug-Login ───────────────────────────────────────────────────────────

@app.route('/api/login/fahrzeug', methods=['POST'])
def login_fahrzeug():
    data = request.get_json(silent=True) or {}
    dnr  = data.get('dienstnummer', '').strip().upper()
    pw   = data.get('password', '')
    fz   = data.get('fahrzeug', '').strip()

    if not dnr or not pw or not fz:
        return jsonify({'error': 'Dienstnummer, Passwort und Fahrzeug erforderlich'}), 400

    with get_db() as db:
        row = db.execute(
            'SELECT * FROM caregivers WHERE dienstnummer=?',
            [dnr]
        ).fetchone()
        # Fallback: Portal-Pfleger der noch keinen caregivers-Eintrag hat
        if not row:
            try:
                pb = db.execute(
                    "SELECT id FROM portal_bewerbungen WHERE dienstnummer=? AND status='freigegeben'",
                    [dnr]
                ).fetchone()
                if pb:
                    _ensure_caregiver_from_portal(pb['id'], db)
                    row = db.execute(
                        'SELECT * FROM caregivers WHERE dienstnummer=?', [dnr]
                    ).fetchone()
            except Exception:
                pass

        if not row:
            return jsonify({'error': 'Dienstnummer oder Passwort falsch'}), 401

        # Portal-Passwort ist maßgeblich — immer mit portal_bewerbungen abgleichen
        pb_pw_row = db.execute(
            "SELECT password_hash FROM portal_bewerbungen WHERE dienstnummer=? AND status='freigegeben'",
            [dnr]
        ).fetchone()
        auth_hash = (pb_pw_row['password_hash']
                     if pb_pw_row and pb_pw_row['password_hash']
                     else row['password_hash'])
        if not check_pw(auth_hash, pw):
            return jsonify({'error': 'Dienstnummer oder Passwort falsch'}), 401
        # Passwort-Hash in caregivers synchron halten
        if pb_pw_row and pb_pw_row['password_hash'] and pb_pw_row['password_hash'] != row['password_hash']:
            db.execute('UPDATE caregivers SET password_hash=? WHERE id=?',
                       [pb_pw_row['password_hash'], row['id']])
            db.commit()

        fz_row = db.execute('SELECT name FROM fahrzeuge WHERE name=? AND aktiv=1', [fz]).fetchone()
    if not fz_row:
        return jsonify({'error': 'Fahrzeug nicht gefunden'}), 404

    session['user_id']   = row['id']
    session['user_role'] = 'care'
    session['fahrzeug']  = fz
    name = row['vorname'] + ' ' + row['nachname']
    _set_vehicle_session(fz, row['id'], name, dnr)
    user = {
        'id': row['id'], 'vorname': row['vorname'], 'nachname': row['nachname'],
        'email': row['email'], 'gender': row['gender'], 'dienstnummer': dnr,
        'fahrzeug': fz, 'role': 'care'
    }
    return jsonify({'ok': True, 'user': user, 'token': _make_token('care', row['id'])})


@app.route('/api/login/pfleger-direkt', methods=['POST'])
def login_pfleger_direkt():
    """Login for a caregiver who is already assigned to a vehicle by admin.
    Only requires Dienstnummer + Password — vehicle is looked up automatically."""
    data = request.get_json(silent=True) or {}
    dnr  = data.get('dienstnummer', '').strip().upper()
    pw   = data.get('password', '')

    if not dnr or not pw:
        return jsonify({'error': 'Dienstnummer und Passwort erforderlich'}), 400

    with get_db() as db:
        row = db.execute(
            'SELECT * FROM caregivers WHERE dienstnummer=?', [dnr]
        ).fetchone()
        if not row:
            try:
                pb = db.execute(
                    "SELECT id FROM portal_bewerbungen WHERE dienstnummer=? AND status='freigegeben'",
                    [dnr]
                ).fetchone()
                if pb:
                    _ensure_caregiver_from_portal(pb['id'], db)
                    row = db.execute(
                        'SELECT * FROM caregivers WHERE dienstnummer=?', [dnr]
                    ).fetchone()
            except Exception:
                pass

        if not row:
            return jsonify({'error': 'Dienstnummer oder Passwort falsch'}), 401

        # Portal-Passwort ist maßgeblich — immer mit portal_bewerbungen abgleichen
        pb_pw_row = db.execute(
            "SELECT password_hash FROM portal_bewerbungen WHERE dienstnummer=? AND status='freigegeben'",
            [dnr]
        ).fetchone()
        auth_hash = (pb_pw_row['password_hash']
                     if pb_pw_row and pb_pw_row['password_hash']
                     else row['password_hash'])
        if not check_pw(auth_hash, pw):
            return jsonify({'error': 'Dienstnummer oder Passwort falsch'}), 401
        # Passwort-Hash in caregivers synchron halten
        if pb_pw_row and pb_pw_row['password_hash'] and pb_pw_row['password_hash'] != row['password_hash']:
            db.execute('UPDATE caregivers SET password_hash=? WHERE id=?',
                       [pb_pw_row['password_hash'], row['id']])
            db.commit()

        vs = db.execute(
            "SELECT fahrzeug FROM vehicle_sessions WHERE caregiver_id=? AND fahrzeug IS NOT NULL AND fahrzeug != ''",
            [row['id']]
        ).fetchone()
        # Fallback: vehicle_sessions könnte noch die pb_xxx ID enthalten (Altdaten)
        if not vs:
            pb_id_row = db.execute(
                "SELECT id FROM portal_bewerbungen WHERE dienstnummer=? AND status='freigegeben'",
                [dnr]
            ).fetchone()
            if pb_id_row:
                vs = db.execute(
                    "SELECT fahrzeug FROM vehicle_sessions WHERE caregiver_id=? AND fahrzeug IS NOT NULL AND fahrzeug != ''",
                    [pb_id_row['id']]
                ).fetchone()
                if vs:
                    # Normalisieren: cg_xxx ID in vehicle_sessions schreiben
                    db.execute(
                        'UPDATE vehicle_sessions SET caregiver_id=?, caregiver_name=?, dienstnummer=? WHERE fahrzeug=?',
                        [row['id'], row['vorname'] + ' ' + row['nachname'], dnr, vs['fahrzeug']]
                    )
                    db.commit()

    if not vs or not vs['fahrzeug']:
        return jsonify({'error': 'Kein Fahrzeug zugewiesen. Bitte Fahrzeug manuell wählen.', 'kein_fahrzeug': True}), 404

    fz = vs['fahrzeug']
    session['user_id']   = row['id']
    session['user_role'] = 'care'
    session['fahrzeug']  = fz
    name = row['vorname'] + ' ' + row['nachname']
    _set_vehicle_session(fz, row['id'], name, dnr)
    user = {
        'id': row['id'], 'vorname': row['vorname'], 'nachname': row['nachname'],
        'email': row['email'], 'gender': row['gender'], 'dienstnummer': dnr,
        'fahrzeug': fz, 'role': 'care'
    }
    return jsonify({'ok': True, 'user': user, 'token': _make_token('care', row['id'])})


def _set_vehicle_session(fahrzeug, cid, name, dnr):
    import datetime
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
    with get_db() as db:
        if USE_PG:
            db.execute(
                'INSERT INTO vehicle_sessions (fahrzeug,caregiver_id,caregiver_name,dienstnummer,eingeloggt_seit,status) '
                'VALUES (?,?,?,?,?,?) ON CONFLICT (fahrzeug) DO UPDATE SET '
                'caregiver_id=EXCLUDED.caregiver_id, caregiver_name=EXCLUDED.caregiver_name, '
                'dienstnummer=EXCLUDED.dienstnummer, eingeloggt_seit=EXCLUDED.eingeloggt_seit, '
                'status=EXCLUDED.status',
                [fahrzeug, cid, name, dnr, now, 'im Dienst']
            )
        else:
            db.execute(
                'INSERT OR REPLACE INTO vehicle_sessions (fahrzeug,caregiver_id,caregiver_name,dienstnummer,eingeloggt_seit,status) '
                'VALUES (?,?,?,?,?,?)',
                [fahrzeug, cid, name, dnr, now, 'im Dienst']
            )
        db.commit()


@app.route('/api/fahrzeuge/position', methods=['POST'])
def fahrzeug_position():
    """Caregiver sends their GPS position; stored on the vehicle_session."""
    data = request.get_json(silent=True) or {}
    lat  = data.get('lat')
    lng  = data.get('lng')
    fz   = data.get('fahrzeug', '').strip().upper() or session.get('fahrzeug', '')
    if not fz or lat is None or lng is None:
        return jsonify({'ok': False, 'error': 'fahrzeug, lat und lng erforderlich'}), 400
    try:
        lat = float(lat); lng = float(lng)
    except (TypeError, ValueError):
        return jsonify({'ok': False, 'error': 'Ungültige Koordinaten'}), 400
    with get_db() as db:
        db.execute(
            "UPDATE vehicle_sessions SET lat=?, lng=?, position_ts=CURRENT_TIMESTAMP WHERE fahrzeug=?",
            [lat, lng, fz]
        )
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/fahrzeuge/abmelden', methods=['POST'])
def fahrzeug_abmelden():
    fz = session.get('fahrzeug') or (request.get_json(silent=True) or {}).get('fahrzeug', '')
    if fz:
        with get_db() as db:
            db.execute(
                "UPDATE vehicle_sessions SET caregiver_id='',caregiver_name='',dienstnummer='',eingeloggt_seit='',status='bereit' WHERE fahrzeug=?",
                [fz]
            )
            db.commit()
    session.clear()
    return jsonify({'ok': True})


@app.route('/api/fahrzeuge')
def get_fahrzeuge():
    bl_filter = request.args.get('bundesland', '').strip()
    with get_db() as db:
        sql = '''
            SELECT f.name, f.typ, f.bundesland, f.bezirk, f.aktiv,
                   COALESCE(vs.caregiver_name,'') AS caregiver_name,
                   COALESCE(vs.dienstnummer,'')   AS dienstnummer,
                   COALESCE(vs.eingeloggt_seit,'') AS eingeloggt_seit,
                   COALESCE(vs.status,'bereit')    AS status,
                   vs.lat, vs.lng, vs.position_ts
            FROM fahrzeuge f
            LEFT JOIN vehicle_sessions vs ON f.name = vs.fahrzeug
            WHERE f.aktiv = 1
        '''
        params = []
        if bl_filter:
            sql += ' AND f.bundesland = ?'
            params.append(bl_filter)
        sql += ' ORDER BY f.bundesland, f.bezirk, f.name'
        rows = db.execute(sql, params).fetchall()
        # Also return distinct Bundesländer
        bl_rows = db.execute(
            "SELECT DISTINCT bundesland FROM fahrzeuge WHERE aktiv=1 AND bundesland!='' ORDER BY bundesland"
        ).fetchall()
    result = []
    for r in rows:
        row = dict(r)
        # include GPS position if available and recent (within 2 hours)
        if row.get('lat') is not None and row.get('lng') is not None:
            row['gps_lat']   = row['lat']
            row['gps_lng']   = row['lng']
            row['gps_ts']    = row.get('position_ts', '')
        else:
            row['gps_lat'] = None
            row['gps_lng'] = None
            row['gps_ts']  = None
        result.append(row)
    return jsonify({
        'ok': True,
        'fahrzeuge': result,
        'bundeslaender': [r['bundesland'] for r in bl_rows]
    })


@app.route('/api/fahrzeuge/alle')
def get_fahrzeuge_alle():
    """Admin/Admiral: all vehicles incl. inactive + current driver info."""
    err = require_admin()
    if err: return err
    with get_db() as db:
        rows = db.execute('''
            SELECT f.name, f.typ, f.bundesland, f.bezirk, f.aktiv,
                   COALESCE(vs.caregiver_id,'')   AS caregiver_id,
                   COALESCE(vs.caregiver_name,'') AS caregiver_name,
                   COALESCE(vs.dienstnummer,'')   AS dienstnummer,
                   COALESCE(vs.eingeloggt_seit,'') AS eingeloggt_seit,
                   COALESCE(vs.status,'bereit')    AS fz_status
            FROM fahrzeuge f
            LEFT JOIN vehicle_sessions vs ON f.name = vs.fahrzeug
            ORDER BY f.bundesland, f.bezirk, f.name
        ''').fetchall()
    return jsonify({'ok': True, 'fahrzeuge': [dict(r) for r in rows]})


@app.route('/api/admin/fahrzeuge/pfleger')
def admin_fahrzeuge_pfleger():
    """Returns portal-freigegeben + registered caregivers for driver assignment dropdown."""
    err = require_admin()
    if err: return err
    with get_db() as db:
        portal = db.execute(
            "SELECT id, vorname, nachname, email, qualifikation, bezirk, dienstnummer FROM portal_bewerbungen "
            "WHERE status='freigegeben' ORDER BY nachname, vorname"
        ).fetchall()
        care = db.execute(
            "SELECT id, vorname, nachname, email, dienstnummer, bezirk FROM caregivers ORDER BY nachname, vorname"
        ).fetchall()
    pfleger = []
    seen_emails = set()
    for r in portal:
        email = (r['email'] or '').lower()
        if email in seen_emails: continue
        seen_emails.add(email)
        # Prefer caregivers.id (cg_xxx) if this portal user already has a caregivers entry
        cg_entry = None
        for c in care:
            if (c['email'] or '').lower() == email:
                cg_entry = c
                break
        use_id  = cg_entry['id']  if cg_entry else r['id']
        use_dnr = (cg_entry['dienstnummer'] or r.get('dienstnummer') or '') if cg_entry else (r.get('dienstnummer') or '')
        pfleger.append({
            'id': use_id,
            'pb_id': r['id'],
            'name': (r['vorname'] or '') + ' ' + (r['nachname'] or ''),
            'qualifikation': r['qualifikation'] or '',
            'bezirk': r['bezirk'] or '',
            'quelle': 'Portal',
            'dienstnummer': use_dnr
        })
    for r in care:
        email = (r['email'] or '').lower()
        if email in seen_emails: continue
        seen_emails.add(email)
        pfleger.append({
            'id': r['id'],
            'pb_id': '',
            'name': (r['vorname'] or '') + ' ' + (r['nachname'] or ''),
            'qualifikation': '',
            'bezirk': r['bezirk'] or '',
            'quelle': 'Pfleger',
            'dienstnummer': r['dienstnummer'] or ''
        })
    return jsonify({'ok': True, 'pfleger': pfleger})


@app.route('/api/fahrzeuge', methods=['POST'])
def add_fahrzeug():
    err = require_admin()
    if err: return err
    data = request.get_json(silent=True) or {}
    name       = data.get('name', '').strip().upper()
    typ        = data.get('typ', 'HKP').strip()[:20]
    bundesland = data.get('bundesland', '').strip()[:60]
    bezirk     = data.get('bezirk', '').strip()[:60]
    if not name:
        return jsonify({'error': 'Name erforderlich'}), 400
    with get_db() as db:
        try:
            db.execute('INSERT INTO fahrzeuge (name,typ,bundesland,bezirk) VALUES (?,?,?,?)',
                       [name, typ, bundesland, bezirk])
            db.execute('INSERT OR IGNORE INTO vehicle_sessions (fahrzeug) VALUES (?)', [name])
            db.commit()
        except Exception:
            return jsonify({'error': 'Fahrzeug existiert bereits'}), 409
    return jsonify({'ok': True, 'name': name})


@app.route('/api/fahrzeuge/<name>', methods=['PUT'])
def update_fahrzeug(name):
    err = require_admin()
    if err: return err
    data = request.get_json(silent=True) or {}
    fields, params = [], []
    for col in ('typ', 'bundesland', 'bezirk'):
        if col in data:
            fields.append(f'{col}=?')
            params.append(str(data[col])[:60])
    if 'aktiv' in data:
        fields.append('aktiv=?')
        params.append(1 if data['aktiv'] else 0)
    if not fields:
        return jsonify({'error': 'Keine Felder'}), 400
    params.append(name.upper())
    with get_db() as db:
        db.execute(f'UPDATE fahrzeuge SET {",".join(fields)} WHERE name=?', params)
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/fahrzeuge/<name>/status', methods=['PUT'])
def fahrzeug_status_setzen(name):
    """Leitstelle/Admin: update vehicle status in vehicle_sessions."""
    err = require_admin()
    if err: return err
    data   = request.get_json(silent=True) or {}
    status = data.get('status', 'bereit').strip()
    if status not in ('bereit', 'einsatz', 'pause', 'ausfall'):
        return jsonify({'error': 'Ungültiger Status'}), 400
    fz = name.upper()
    with get_db() as db:
        if not db.execute('SELECT name FROM fahrzeuge WHERE name=?', [fz]).fetchone():
            return jsonify({'ok': False, 'error': 'Fahrzeug nicht gefunden'}), 404
        db.execute('UPDATE vehicle_sessions SET status=? WHERE fahrzeug=?', [status, fz])
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/fahrzeuge/<name>/fahrer', methods=['PUT'])
def fahrzeug_fahrer_setzen(name):
    """Admin/Admiral: assign a caregiver as driver for a vehicle."""
    err = require_admin()
    if err: return err
    import datetime as _dt
    data  = request.get_json(silent=True) or {}
    cid   = data.get('caregiver_id', '').strip()
    cname = data.get('caregiver_name', '').strip()
    dnr   = data.get('dienstnummer', '').strip()
    now   = _dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    fz    = name.upper()
    with get_db() as db:
        if not db.execute('SELECT name FROM fahrzeuge WHERE name=?', [fz]).fetchone():
            return jsonify({'ok': False, 'error': 'Fahrzeug nicht gefunden'}), 404
        # Wenn cid eine Portal-Bewerbungs-ID ist (pb_xxx), auf caregivers-ID (cg_xxx) auflösen
        if cid.startswith('pb_'):
            resolved_cg_id, resolved_dnr = _ensure_caregiver_from_portal(cid, db)
            cg_row = db.execute(
                'SELECT id, vorname, nachname, dienstnummer FROM caregivers WHERE id=?',
                [resolved_cg_id]
            ).fetchone() if resolved_cg_id else None
            if cg_row:
                cid   = cg_row['id']
                cname = (cg_row['vorname'] or '') + ' ' + (cg_row['nachname'] or '')
                dnr   = cg_row['dienstnummer'] or dnr
        if USE_PG:
            db.execute(
                '''INSERT INTO vehicle_sessions (fahrzeug,caregiver_id,caregiver_name,dienstnummer,eingeloggt_seit,status)
                   VALUES (?,?,?,?,?,?)
                   ON CONFLICT (fahrzeug) DO UPDATE SET
                   caregiver_id=EXCLUDED.caregiver_id, caregiver_name=EXCLUDED.caregiver_name,
                   dienstnummer=EXCLUDED.dienstnummer, eingeloggt_seit=EXCLUDED.eingeloggt_seit,
                   status=EXCLUDED.status''',
                [fz, cid, cname, dnr, now, 'im Dienst']
            )
        else:
            db.execute(
                'INSERT OR REPLACE INTO vehicle_sessions (fahrzeug,caregiver_id,caregiver_name,dienstnummer,eingeloggt_seit,status) VALUES (?,?,?,?,?,?)',
                [fz, cid, cname, dnr, now, 'im Dienst']
            )
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/fahrzeuge/<name>/fahrer', methods=['DELETE'])
def fahrzeug_fahrer_abmelden(name):
    """Admin/Admiral: remove driver assignment from a vehicle."""
    err = require_admin()
    if err: return err
    with get_db() as db:
        db.execute(
            "UPDATE vehicle_sessions SET caregiver_id='',caregiver_name='',dienstnummer='',eingeloggt_seit='',status='bereit' WHERE fahrzeug=?",
            [name.upper()]
        )
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/fahrzeuge/<name>', methods=['DELETE'])
def delete_fahrzeug(name):
    err = require_admin()
    if err: return err
    with get_db() as db:
        db.execute('DELETE FROM fahrzeuge WHERE name=?', [name.upper()])
        db.execute('DELETE FROM vehicle_sessions WHERE fahrzeug=?', [name.upper()])
        db.commit()
    return jsonify({'ok': True})

@app.route('/api/admin/fahrzeuge/alle', methods=['DELETE'])
def delete_alle_fahrzeuge():
    err = require_admin()
    if err: return err
    with get_db() as db:
        db.execute('DELETE FROM vehicle_sessions')
        db.execute('DELETE FROM fahrzeuge')
        db.commit()
    return jsonify({'ok': True, 'message': 'Alle Fahrzeuge und Sessions gelöscht'})


@app.route('/api/nachrichten', methods=['POST'])
def send_nachricht():
    data = request.get_json(silent=True) or {}
    text = (data.get('text') or '').strip()
    if not text:
        return jsonify({'error': 'Kein Text'}), 400
    typ      = (data.get('typ') or 'nachricht').strip()[:30]
    # Try to get sender info from session, then fallback to body
    me = session.get('user_id')
    von_name = data.get('von_name', session.get('user_name', '')).strip()[:80]
    von_dnr  = data.get('von_dnr',  '').strip().upper()[:20]
    fahrzeug = data.get('fahrzeug', '').strip().upper()[:20]
    with get_db() as db:
        db.execute(
            'INSERT INTO nachrichten (von_name,von_dnr,fahrzeug,typ,text) VALUES (?,?,?,?,?)',
            [von_name, von_dnr, fahrzeug, typ, text]
        )
        db.commit()
    return jsonify({'ok': True})

@app.route('/api/nachrichten')
def get_nachrichten():
    uid  = session.get('user_id')
    role = session.get('user_role')
    lid  = session.get('leitstelle_id')
    # Leitstelle and admin can read all
    if role not in ('leitstelle', 'admin') and uid != 'admin' and not lid:
        tok = _token_from_request()
        if not tok or tok['role'] not in ('leitstelle', 'admin', 'admiral', 'disponent'):
            return jsonify({'error': 'Kein Zugriff'}), 403
    since_id = request.args.get('since', 0, type=int)
    with get_db() as db:
        rows = db.execute(
            'SELECT * FROM nachrichten WHERE id > ? ORDER BY id DESC LIMIT 100',
            [since_id]
        ).fetchall()
    return jsonify({'nachrichten': [dict(r) for r in rows]})

@app.route('/api/nachrichten/<int:nid>/gelesen', methods=['POST'])
def mark_nachricht_gelesen(nid):
    uid  = session.get('user_id')
    role = session.get('user_role')
    lid  = session.get('leitstelle_id')
    if role not in ('leitstelle', 'admin') and uid != 'admin' and not lid:
        tok = _token_from_request()
        if not tok or tok['role'] not in ('leitstelle', 'admin', 'admiral', 'disponent'):
            return jsonify({'error': 'Kein Zugriff'}), 403
    with get_db() as db:
        db.execute('UPDATE nachrichten SET gelesen=1 WHERE id=?', [nid])
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/caregivers/<cid>/dienstnummer', methods=['POST'])
def set_dienstnummer(cid):
    uid = session.get('user_id'); role = session.get('user_role')
    if uid != 'admin' and role != 'admin':
        return jsonify({'error': 'Kein Zugriff'}), 403
    data = request.get_json(silent=True) or {}
    dnr  = data.get('dienstnummer', '').strip().upper()
    if not dnr:
        return jsonify({'error': 'Dienstnummer erforderlich'}), 400
    with get_db() as db:
        db.execute('UPDATE caregivers SET dienstnummer=? WHERE id=?', [dnr, cid])
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/caregivers')
def list_caregivers():
    with get_db() as db:
        cg_rows = db.execute(
            'SELECT id,vorname,nachname,email,gender,address,plz,ort,bezirk,created_at '
            'FROM caregivers ORDER BY created_at DESC'
        ).fetchall()
        pb_rows = db.execute(
            "SELECT id,vorname,nachname,email,''as gender,adresse as address,"
            "'' as plz,'' as ort,bezirk,created_at "
            "FROM portal_bewerbungen WHERE status='freigegeben' ORDER BY created_at DESC"
        ).fetchall()
    seen = set()
    result = []
    for r in cg_rows:
        d = dict(r)
        d['name'] = d['vorname'] + ' ' + d['nachname']
        d['role'] = 'care'
        result.append(d)
        seen.add(d['id'])
    for r in pb_rows:
        d = dict(r)
        d['name'] = d['vorname'] + ' ' + d['nachname']
        d['role'] = 'care'
        if d['id'] not in seen:
            result.append(d)
    return jsonify({'ok': True, 'caregivers': result})


# ── API: Patienten ──────────────────────────────────────────────────────────

@app.route('/api/register/patient', methods=['POST'])
def register_patient():
    data = request.get_json(silent=True) or {}
    for f in ['vorname', 'nachname']:
        if not data.get(f, '').strip():
            return jsonify({'error': f'Feld "{f}" fehlt'}), 400

    uid = 'p' + uuid.uuid4().hex[:8]
    pw  = data.get('password', '')
    ang = json.dumps(data.get('angehoerige', []))
    profil_extra = json.dumps({
        'sv':          data.get('sv', ''),
        'tel':         data.get('tel', ''),
        'erkrankungen': data.get('erkrankungen', []),
        'allergien':   data.get('allergien', ''),
        'medikamente': data.get('medikamente', ''),
        'wichtig':     data.get('wichtig', ''),
    })

    with get_db() as db:
        db.execute(
            'INSERT INTO patients (id,vorname,nachname,email,password_hash,gender,address,plz,ort,bezirk,birth,hauptgrund,haeufigkeit,angehoerige,profil_extra) '
            'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            [uid, data['vorname'].strip(), data['nachname'].strip(),
             data.get('email','').strip().lower(),
             hash_pw(pw) if pw else '',
             data.get('gender',''), data.get('address',''),
             data.get('plz',''), data.get('ort',''), data.get('bezirk',''),
             data.get('birth',''), data.get('hauptgrund',''),
             data.get('haeufigkeit',''), ang, profil_extra]
        )
        db.commit()

    return jsonify({'ok': True, 'id': uid,
                    'name': data['vorname'].strip() + ' ' + data['nachname'].strip()})


@app.route('/api/patient/data/<pid>')
def get_patient_data_public(pid):
    with get_db() as db:
        row = db.execute(
            'SELECT id,vorname,nachname,email,gender,address,plz,ort,bezirk,birth,hauptgrund,haeufigkeit,angehoerige FROM patients WHERE id=?',
            (pid,)).fetchone()
    if not row:
        return jsonify({'ok': False, 'error': 'Nicht gefunden'}), 404
    ang = []
    try: ang = json.loads(row['angehoerige'] or '[]')
    except Exception: pass
    return jsonify({'ok': True, 'patient': {
        'vorname': row['vorname'], 'nachname': row['nachname'],
        'email': row['email'], 'gender': row['gender'],
        'address': row['address'], 'plz': row['plz'], 'ort': row['ort'],
        'bezirk': row['bezirk'], 'birth': row['birth'] or '',
        'hauptgrund': row['hauptgrund'] or '', 'haeufigkeit': row['haeufigkeit'] or '',
        'angehoerige': ang
    }})


@app.route('/api/patient/data/<pid>', methods=['PUT'])
def update_patient_data_public(pid):
    data = request.get_json(silent=True) or {}
    with get_db() as db:
        row = db.execute('SELECT id FROM patients WHERE id=?', (pid,)).fetchone()
        if not row:
            return jsonify({'ok': False, 'error': 'Nicht gefunden'}), 404
        update_fields = {}
        for field in ('vorname', 'nachname', 'email', 'gender', 'address', 'plz', 'ort', 'bezirk', 'birth', 'hauptgrund', 'haeufigkeit'):
            if field in data:
                update_fields[field] = data[field]
        if 'angehoerige' in data:
            update_fields['angehoerige'] = json.dumps(data['angehoerige'])
        if update_fields:
            set_clause = ', '.join(k + '=?' for k in update_fields)
            values = list(update_fields.values()) + [pid]
            db.execute('UPDATE patients SET ' + set_clause + ' WHERE id=?', values)
            db.commit()
    return jsonify({'ok': True})


@app.route('/api/match/caregivers')
def match_caregivers():
    plz    = request.args.get('plz', '').strip()
    bezirk = request.args.get('bezirk', '').strip()
    with get_db() as db:
        rows = []
        if bezirk:
            rows = db.execute(
                "SELECT id, vorname, nachname, bezirk, plz, ort, qualifikation FROM caregivers WHERE bezirk=? ORDER BY nachname, vorname",
                [bezirk]).fetchall()
        if not rows and plz:
            rows = db.execute(
                "SELECT id, vorname, nachname, bezirk, plz, ort, qualifikation FROM caregivers WHERE plz=? ORDER BY nachname, vorname",
                [plz]).fetchall()
    result = [{'id': r['id'], 'name': ((r['vorname'] or '') + ' ' + (r['nachname'] or '')).strip(),
               'bezirk': r['bezirk'] or '', 'plz': r['plz'] or '', 'ort': r['ort'] or '',
               'qualifikation': r['qualifikation'] or ''} for r in rows]
    return jsonify({'ok': True, 'matches': result, 'count': len(result)})


@app.route('/api/patients')
def list_patients():
    role = session.get('user_role') or session.get('leitstelle_role')
    if not role:
        tok = _token_from_request()
        if tok:
            role = tok.get('role')
    if role not in ('leitstelle', 'admin', 'billing'):
        return jsonify({'ok': False, 'error': 'Kein Zugriff', 'patients': []}), 403
    with get_db() as db:
        rows = db.execute('SELECT * FROM patients ORDER BY created_at DESC').fetchall()
    result = []
    for r in rows:
        addr_parts = [r['address'], r['plz'], r['ort']]
        addr = ', '.join(p for p in addr_parts if p)
        result.append({
            'id': r['id'],
            'vorname': r['vorname'], 'nachname': r['nachname'],
            'name': r['vorname'] + ' ' + r['nachname'],
            'email': r['email'], 'gender': r['gender'],
            'address': addr, 'plz': r['plz'], 'ort': r['ort'],
            'birth': r['birth'],
            'hauptgrund': r['hauptgrund'],
            'haeufigkeit': r['haeufigkeit'],
            'active': True, 'source': 'db', 'visits': []
        })
    return jsonify({'ok': True, 'patients': result})


# ── API: Patientenakte ──────────────────────────────────────────────────────

def _patient_to_dict(r):
    keys = r.keys()
    addr_parts = [r['address'] if 'address' in keys else '',
                  r['plz'] if 'plz' in keys else '',
                  r['ort'] if 'ort' in keys else '']
    extra = {}
    if 'profil_extra' in keys and r['profil_extra']:
        try:
            extra = json.loads(r['profil_extra'])
        except Exception:
            extra = {}
    return {
        'id': r['id'], 'vorname': r['vorname'], 'nachname': r['nachname'],
        'name': r['vorname'] + ' ' + r['nachname'],
        'email': r['email'] if 'email' in keys else '',
        'gender': r['gender'] if 'gender' in keys else '',
        'address': ', '.join(p for p in addr_parts if p),
        'plz': r['plz'] if 'plz' in keys else '',
        'ort': r['ort'] if 'ort' in keys else '',
        'bezirk': r['bezirk'] if 'bezirk' in keys else '',
        'birth': r['birth'] if 'birth' in keys else '',
        'hauptgrund': r['hauptgrund'] if 'hauptgrund' in keys else '',
        'haeufigkeit':    r['haeufigkeit'] if 'haeufigkeit' in keys else '',
        'patient_status': (r['patient_status'] if 'patient_status' in keys else None) or 'aktiv',
        'angehoerige': json.loads(r['angehoerige'] if 'angehoerige' in keys else '[]'),
        'sv':              extra.get('sv', ''),
        'tel':             extra.get('tel', ''),
        'erkrankungen':    extra.get('erkrankungen', []),
        'allergien':       extra.get('allergien', ''),
        'medikamente':     extra.get('medikamente', ''),
        'wichtig':         extra.get('wichtig', ''),
        'anamnese':        extra.get('anamnese', {}),
        'einverstaendnis': extra.get('einverstaendnis', {}),
    }

def _get_session_role_fahrzeug():
    if session.get('leitstelle_id'):
        role = session.get('leitstelle_role')
    else:
        role = session.get('user_role')
    fahrzeug = session.get('fahrzeug')
    if not role:
        tok = _token_from_request()
        if tok:
            role = tok.get('role')
    return role, fahrzeug

def _care_has_einsatz_for_patient(db, fahrzeug, pid):
    row = db.execute(
        "SELECT id FROM einsaetze WHERE fahrzeug=? AND patient_id=? AND status NOT IN ('storniert')",
        (fahrzeug, pid)
    ).fetchone()
    return row is not None

@app.route('/api/patienten')
def patienten_suche():
    role, fahrzeug = _get_session_role_fahrzeug()
    if role == 'care':
        return jsonify({'ok': False, 'error': 'Kein Zugriff: Patientensuche nur für Leitstelle'}), 403
    name = request.args.get('name', '').strip()
    with get_db() as db:
        if name:
            like = '%' + name + '%'
            rows = db.execute(
                "SELECT * FROM patients WHERE (vorname||' '||nachname) LIKE ? OR nachname LIKE ? OR vorname LIKE ? ORDER BY nachname",
                (like, like, like)
            ).fetchall()
        else:
            rows = db.execute('SELECT * FROM patients ORDER BY nachname, vorname').fetchall()
        patients_list = [_patient_to_dict(r) for r in rows]

        # Also search care_accepted_patients (Nursy App patients)
        nursy_patients = []
        seen_cap_ids = set()
        if name:
            cap_rows = db.execute(
                "SELECT patient_id, patient_json FROM care_accepted_patients WHERE active=1 AND patient_json LIKE ?",
                ['%' + name + '%']
            ).fetchall()
        else:
            cap_rows = db.execute(
                "SELECT patient_id, patient_json FROM care_accepted_patients WHERE active=1"
            ).fetchall()
        for row in cap_rows:
            pid = row['patient_id']
            if pid in seen_cap_ids:
                continue
            seen_cap_ids.add(pid)
            try:
                pj = json.loads(row['patient_json'] or '{}')
            except Exception:
                continue
            pj['_cap_patient_id'] = pid
            pj['_source_type'] = 'nursy'
            nursy_patients.append(pj)

    return jsonify({'ok': True, 'patients': patients_list, 'nursy_patients': nursy_patients})

@app.route('/api/patienten/pruefen')
def patienten_duplikat_check():
    """Duplicate check by name + birthdate (accessible by care role too)"""
    name   = request.args.get('name', '').strip()
    geburt = request.args.get('geburt', '').strip()
    if not name:
        return jsonify({'ok': True, 'matches': []})
    with get_db() as db:
        parts = [p for p in name.replace(',', ' ').split() if len(p) > 1]
        if not parts:
            return jsonify({'ok': True, 'matches': []})
        conditions, params = [], []
        for part in parts:
            like = '%' + part + '%'
            conditions.append("(vorname LIKE ? OR nachname LIKE ?)")
            params.extend([like, like])
        rows = db.execute(
            "SELECT * FROM patients WHERE " + ' AND '.join(conditions) + " ORDER BY nachname",
            params
        ).fetchall()
    matches = [_patient_to_dict(r) for r in rows]
    if geburt:
        g = geburt.replace('-','').replace('.','').replace('/','')
        exact = [m for m in matches if (m.get('birth','') or '').replace('-','').replace('.','').replace('/','') == g]
        if exact:
            matches = exact
    return jsonify({'ok': True, 'matches': matches[:5]})


@app.route('/api/patienten/<pid>')
def patient_detail(pid):
    role, fahrzeug = _get_session_role_fahrzeug()
    with get_db() as db:
        if role == 'care':
            if not fahrzeug or not _care_has_einsatz_for_patient(db, fahrzeug, pid):
                return jsonify({'ok': False, 'error': 'Kein Zugriff: Kein aktiver Einsatz für diesen Patienten auf diesem Fahrzeug'}), 403
        row = db.execute('SELECT * FROM patients WHERE id=?', (pid,)).fetchone()
    if not row:
        return jsonify({'ok': False, 'error': 'Patient nicht gefunden'}), 404
    return jsonify({'ok': True, 'patient': _patient_to_dict(row)})

@app.route('/api/patienten/<pid>', methods=['PUT'])
def update_patient(pid):
    role, fahrzeug = _get_session_role_fahrzeug()
    if not role:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    data = request.get_json(silent=True) or {}
    with get_db() as db:
        if role == 'care':
            if not fahrzeug or not _care_has_einsatz_for_patient(db, fahrzeug, pid):
                return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
        row = db.execute('SELECT * FROM patients WHERE id=?', (pid,)).fetchone()
        if not row:
            return jsonify({'ok': False, 'error': 'Patient nicht gefunden'}), 404
        existing = {}
        try:
            existing = json.loads(row['profil_extra'] or '{}')
        except Exception:
            pass
        if 'anamnese' in data:
            existing['anamnese'] = {**(existing.get('anamnese') or {}), **data['anamnese']}
        for field in ('sv', 'tel', 'erkrankungen', 'allergien', 'medikamente', 'wichtig', 'einverstaendnis'):
            if field in data:
                existing[field] = data[field]
        update_fields = {'profil_extra': json.dumps(existing)}
        for field in ('vorname', 'nachname', 'email', 'gender', 'address', 'plz', 'ort', 'bezirk', 'birth', 'hauptgrund', 'haeufigkeit', 'patient_status'):
            if field in data:
                update_fields[field] = data[field]
        if 'angehoerige' in data:
            update_fields['angehoerige'] = json.dumps(data['angehoerige'])
        set_clause = ', '.join(k + '=?' for k in update_fields)
        values = list(update_fields.values()) + [pid]
        db.execute('UPDATE patients SET ' + set_clause + ' WHERE id=?', values)
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/patienten/<pid>/einsaetze')
def patient_einsatz_history(pid):
    role, fahrzeug = _get_session_role_fahrzeug()
    if not role:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    with get_db() as db:
        rows = db.execute(
            '''SELECT id,nummer,art,dringlichkeit,status,datum,zeit,fahrzeug,disponent,
                      zeit_angenommen,zeit_unterwegs,zeit_eingetroffen,zeit_beendet,created_at
               FROM einsaetze WHERE patient_id=?
               ORDER BY datum DESC, zeit DESC, created_at DESC''',
            (pid,)
        ).fetchall()
    einsaetze = [dict(r) for r in rows]
    return jsonify({'ok': True, 'einsaetze': einsaetze})


@app.route('/api/einsaetze/<eid>/dokumente', methods=['GET'])
def list_einsatz_dokumente(eid):
    role, fahrzeug = _get_session_role_fahrzeug()
    if not role:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    with get_db() as db:
        rows = db.execute(
            'SELECT id,original_name,stored_name,beschreibung,uploaded_by,mime_type,created_at FROM einsatz_dokumente WHERE einsatz_id=? ORDER BY created_at DESC',
            (eid,)
        ).fetchall()
    docs = [{'id':r['id'],'original_name':r['original_name'],'beschreibung':r['beschreibung'],
              'uploaded_by':r['uploaded_by'],'created_at':r['created_at'],
              'url':'/api/einsatz-uploads/'+r['stored_name']} for r in rows]
    return jsonify({'ok': True, 'dokumente': docs})

@app.route('/api/einsaetze/<eid>/dokumente', methods=['POST'])
def upload_einsatz_dokument(eid):
    role, fahrzeug = _get_session_role_fahrzeug()
    if not role:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    file = request.files.get('file')
    if not file or file.filename == '':
        return jsonify({'ok': False, 'error': 'Keine Datei angegeben'}), 400
    if not allowed_file(file.filename):
        return jsonify({'ok': False, 'error': 'Dateityp nicht erlaubt'}), 400
    original_name = file.filename
    ext = original_name.rsplit('.', 1)[-1].lower() if '.' in original_name else 'bin'
    doc_id = 'edok_' + uuid.uuid4().hex[:12]
    stored_name = doc_id + '.' + ext
    mime_type = MIME_MAP.get(ext, 'application/octet-stream')
    try:
        file_bytes = file.read()
        file_data  = base64.b64encode(file_bytes).decode('utf-8')
    except Exception as e:
        return jsonify({'ok': False, 'error': 'Datei konnte nicht gelesen werden: ' + str(e)}), 500
    try:
        with open(os.path.join(UPLOAD_DIR, stored_name), 'wb') as fh:
            fh.write(file_bytes)
    except Exception:
        pass
    beschreibung = request.form.get('beschreibung', '')
    uploaded_by  = (session.get('leitstelle_name') or session.get('user_name') or
                    session.get('user_id') or 'unbekannt')
    with get_db() as db:
        db.execute(
            'INSERT INTO einsatz_dokumente (id,einsatz_id,original_name,stored_name,beschreibung,uploaded_by,file_data,mime_type) VALUES (?,?,?,?,?,?,?,?)',
            (doc_id, eid, original_name, stored_name, beschreibung, uploaded_by, file_data, mime_type)
        )
        db.commit()
    return jsonify({'ok': True, 'id': doc_id, 'url': '/api/einsatz-uploads/' + stored_name})

@app.route('/api/einsatz-uploads/<path:filename>')
def serve_einsatz_upload(filename):
    try:
        with get_db() as db:
            row = db.execute('SELECT file_data, mime_type, original_name FROM einsatz_dokumente WHERE stored_name=?', (filename,)).fetchone()
        if row and row['file_data']:
            from flask import Response
            file_bytes = base64.b64decode(row['file_data'])
            mime = row['mime_type'] or 'application/octet-stream'
            resp = Response(file_bytes, mimetype=mime)
            resp.headers['Content-Disposition'] = 'inline; filename="' + (row['original_name'] or filename) + '"'
            return resp
    except Exception:
        pass
    try:
        return send_from_directory(UPLOAD_DIR, filename)
    except Exception:
        return jsonify({'error': 'Datei nicht gefunden'}), 404

@app.route('/api/einsaetze/<eid>/patient', methods=['POST'])
def link_patient_to_einsatz(eid):
    """Link a patient_id to an existing Einsatz (after new patient creation)"""
    role, fahrzeug = _get_session_role_fahrzeug()
    if not role:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    data = request.get_json(silent=True) or {}
    pid = data.get('patient_id', '').strip()
    if not pid:
        return jsonify({'ok': False, 'error': 'patient_id fehlt'}), 400
    with get_db() as db:
        db.execute('UPDATE einsaetze SET patient_id=? WHERE id=?', (pid, eid))
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/patienten/<pid>/dokumente', methods=['GET'])
def list_dokumente(pid):
    role, fahrzeug = _get_session_role_fahrzeug()
    with get_db() as db:
        if role == 'care':
            if not fahrzeug or not _care_has_einsatz_for_patient(db, fahrzeug, pid):
                return jsonify({'ok': False, 'error': 'Kein Zugriff: Kein aktiver Einsatz für diesen Patienten auf diesem Fahrzeug'}), 403
        rows = db.execute(
            'SELECT * FROM patient_dokumente WHERE patient_id=? ORDER BY created_at DESC', (pid,)
        ).fetchall()
    docs = []
    for r in rows:
        docs.append({
            'id': r['id'], 'typ': r['typ'],
            'original_name': r['original_name'],
            'stored_name': r['stored_name'],
            'beschreibung': r['beschreibung'],
            'uploaded_by': r['uploaded_by'],
            'created_at': r['created_at'],
            'url': '/api/uploads/' + r['stored_name'],
        })
    return jsonify({'ok': True, 'dokumente': docs})

MIME_MAP = {
    'pdf':'application/pdf','png':'image/png','jpg':'image/jpeg','jpeg':'image/jpeg',
    'gif':'image/gif','webp':'image/webp','heic':'image/heic','heif':'image/heif',
    'doc':'application/msword',
    'docx':'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'txt':'text/plain',
}

@app.route('/api/patienten/<pid>/dokumente', methods=['POST'])
def upload_dokument(pid):
    role, fahrzeug = _get_session_role_fahrzeug()
    with get_db() as db:
        if role == 'care':
            if not fahrzeug or not _care_has_einsatz_for_patient(db, fahrzeug, pid):
                return jsonify({'ok': False, 'error': 'Kein Zugriff: Kein aktiver Einsatz für diesen Patienten auf diesem Fahrzeug'}), 403
        patient = db.execute('SELECT id FROM patients WHERE id=?', (pid,)).fetchone()
    if not patient:
        return jsonify({'ok': False, 'error': 'Patient nicht gefunden'}), 404

    file = request.files.get('file')
    if not file or file.filename == '':
        return jsonify({'ok': False, 'error': 'Keine Datei angegeben'}), 400
    if not allowed_file(file.filename):
        return jsonify({'ok': False, 'error': 'Dateityp nicht erlaubt'}), 400

    original_name = file.filename
    ext = original_name.rsplit('.', 1)[-1].lower() if '.' in original_name else 'bin'
    doc_id = 'dok_' + uuid.uuid4().hex[:12]
    stored_name = doc_id + '.' + ext
    mime_type = MIME_MAP.get(ext, 'application/octet-stream')

    # Read file and store as base64 in DB (works in all environments)
    try:
        file_bytes = file.read()
        file_data  = base64.b64encode(file_bytes).decode('utf-8')
    except Exception as e:
        return jsonify({'ok': False, 'error': 'Datei konnte nicht gelesen werden: ' + str(e)}), 500

    # Also try to save to disk as fallback (ignore errors)
    try:
        with open(os.path.join(UPLOAD_DIR, stored_name), 'wb') as fh:
            fh.write(file_bytes)
    except Exception:
        pass

    typ = request.form.get('typ', 'sonstiges')
    beschreibung = request.form.get('beschreibung', '')
    uploaded_by  = (session.get('leitstelle_name') or session.get('user_name') or
                    session.get('user_id') or 'unbekannt')

    with get_db() as db:
        db.execute(
            'INSERT INTO patient_dokumente (id,patient_id,typ,original_name,stored_name,beschreibung,uploaded_by,file_data,mime_type) VALUES (?,?,?,?,?,?,?,?,?)',
            (doc_id, pid, typ, original_name, stored_name, beschreibung, uploaded_by, file_data, mime_type)
        )
        db.commit()
    return jsonify({'ok': True, 'id': doc_id, 'url': '/api/uploads/' + stored_name})

@app.route('/api/patienten/<pid>/dokumente/json', methods=['POST'])
def upload_dokument_json(pid):
    role, fahrzeug = _get_session_role_fahrzeug()
    with get_db() as db:
        if role == 'care':
            if not fahrzeug or not _care_has_einsatz_for_patient(db, fahrzeug, pid):
                return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
        patient = db.execute('SELECT id FROM patients WHERE id=?', (pid,)).fetchone()
    if not patient:
        return jsonify({'ok': False, 'error': 'Patient nicht gefunden'}), 404
    _ALLOWED_JSON_TYPS = {'protokoll','einverstaendnis','arztbrief','befund','verlauf','foto','wundfoto','sonstiges'}
    _MAX_B64_BYTES = 8 * 1024 * 1024  # 8 MB base64 string limit
    data = request.get_json(silent=True) or {}
    file_data_b64 = data.get('file_data_b64', '')
    if not file_data_b64:
        return jsonify({'ok': False, 'error': 'Keine Daten'}), 400
    if len(file_data_b64) > _MAX_B64_BYTES:
        return jsonify({'ok': False, 'error': 'Datei zu groß (max 6 MB)'}), 413
    if ',' in file_data_b64:
        file_data_b64 = file_data_b64.split(',', 1)[1]
    try:
        import base64 as _b64mod
        _b64mod.b64decode(file_data_b64, validate=True)
    except Exception:
        return jsonify({'ok': False, 'error': 'Ungültige Base64-Daten'}), 400
    typ           = data.get('typ', 'sonstiges')
    if typ not in _ALLOWED_JSON_TYPS:
        typ = 'sonstiges'
    original_name = (data.get('original_name') or 'dokument.txt')[:255]
    beschreibung  = (data.get('beschreibung') or '')[:500]
    mime_type     = data.get('mime_type', 'text/plain')
    ext = original_name.rsplit('.', 1)[-1].lower() if '.' in original_name else 'txt'
    doc_id = 'dok_' + uuid.uuid4().hex[:12]
    stored_name = doc_id + '.' + ext
    uploaded_by = (session.get('leitstelle_name') or session.get('user_name') or
                   session.get('user_id') or 'unbekannt')
    with get_db() as db:
        db.execute(
            'INSERT INTO patient_dokumente (id,patient_id,typ,original_name,stored_name,beschreibung,uploaded_by,file_data,mime_type) VALUES (?,?,?,?,?,?,?,?,?)',
            (doc_id, pid, typ, original_name, stored_name, beschreibung, uploaded_by, file_data_b64, mime_type)
        )
        db.commit()
    return jsonify({'ok': True, 'id': doc_id, 'url': '/api/uploads/' + stored_name})

@app.route('/api/uploads/<path:filename>')
def serve_upload(filename):
    # Try DB first (always works)
    try:
        with get_db() as db:
            row = db.execute('SELECT file_data, mime_type, original_name FROM patient_dokumente WHERE stored_name=?', (filename,)).fetchone()
        if row and row['file_data']:
            from flask import Response
            file_bytes = base64.b64decode(row['file_data'])
            mime = row['mime_type'] or 'application/octet-stream'
            resp = Response(file_bytes, mimetype=mime)
            resp.headers['Content-Disposition'] = 'inline; filename="' + (row['original_name'] or filename) + '"'
            return resp
    except Exception:
        pass
    # Fallback: filesystem
    try:
        return send_from_directory(UPLOAD_DIR, filename)
    except Exception:
        return jsonify({'error': 'Datei nicht gefunden'}), 404

@app.route('/api/patienten/dokumente/<doc_id>', methods=['DELETE'])
def delete_dokument(doc_id):
    with get_db() as db:
        row = db.execute('SELECT * FROM patient_dokumente WHERE id=?', (doc_id,)).fetchone()
        if not row:
            return jsonify({'ok': False, 'error': 'Dokument nicht gefunden'}), 404
        stored = row['stored_name']
        db.execute('DELETE FROM patient_dokumente WHERE id=?', (doc_id,))
        db.commit()
    try:
        os.remove(os.path.join(UPLOAD_DIR, stored))
    except Exception:
        pass
    return jsonify({'ok': True})


# ── API: Session / Me ───────────────────────────────────────────────────────

@app.route('/api/me')
def me():
    uid  = session.get('user_id')
    role = session.get('user_role')
    # Token-Fallback
    if not uid:
        tok = _token_from_request()
        if tok:
            uid  = tok['uid']
            role = tok['role']
            session['user_id']   = uid
            session['user_role'] = role
            # Restore fahrzeug from vehicle_sessions
            if role == 'care':
                with get_db() as db:
                    vs2 = db.execute('SELECT fahrzeug FROM vehicle_sessions WHERE caregiver_id=?', [uid]).fetchone()
                if vs2 and vs2['fahrzeug']:
                    session['fahrzeug'] = vs2['fahrzeug']
    if not uid:
        return jsonify({'error': 'Nicht angemeldet'}), 401
    if role == 'care':
        fz = session.get('fahrzeug', '')
        with get_db() as db:
            row = db.execute('SELECT * FROM caregivers WHERE id=?', [uid]).fetchone()
            vs  = db.execute('SELECT * FROM vehicle_sessions WHERE fahrzeug=?', [fz]).fetchone() if fz else None
        if row:
            return jsonify({'ok': True, 'user': {
                'id': row['id'], 'vorname': row['vorname'], 'nachname': row['nachname'],
                'name': (row['vorname'] or '') + ' ' + (row['nachname'] or ''),
                'email': row['email'], 'gender': row['gender'],
                'address': row['address'], 'plz': row['plz'], 'ort': row['ort'],
                'dienstnummer': row['dienstnummer'] or '',
                'fahrzeug': fz,
                'eingeloggt_seit': vs['eingeloggt_seit'] if vs else '',
                'role': 'care'
            }})
    return jsonify({'error': 'Sitzung abgelaufen'}), 401


@app.route('/api/logout', methods=['POST'])
def logout():
    fz = session.get('fahrzeug', '')
    if fz:
        with get_db() as db:
            db.execute(
                "UPDATE vehicle_sessions SET caregiver_id='',caregiver_name='',dienstnummer='',eingeloggt_seit='',status='bereit' WHERE fahrzeug=?",
                [fz]
            )
            db.commit()
    session.clear()
    return jsonify({'ok': True})


@app.route('/api/care/account', methods=['DELETE'])
def care_delete_account():
    uid = session.get('user_id')
    if not uid:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    with get_db() as db:
        db.execute('DELETE FROM matching_verbindungen WHERE caregiver_id=?', [uid])
        db.execute("UPDATE matching_anfragen SET ziel_caregiver_id='', modus='offen' WHERE ziel_caregiver_id=? AND status='aktiv'", [uid])
        db.execute('DELETE FROM care_accepted_patients WHERE caregiver_id=?', [uid])
        db.execute('DELETE FROM caregivers WHERE id=?', [uid])
        db.commit()
    session.clear()
    return jsonify({'ok': True})


# ── API: Leitstelle Auth ─────────────────────────────────────────────────────

@app.route('/api/login/leitstelle', methods=['POST'])
def login_leitstelle():
    data  = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    pw    = data.get('password', '')

    with get_db() as db:
        row = db.execute(
            'SELECT * FROM leitstelle_users WHERE email=? AND aktiv=1',
            [email]
        ).fetchone()

    if not row or not check_pw(row['password_hash'], pw):
        return jsonify({'error': 'E-Mail oder Passwort falsch'}), 401

    must_change = bool(row['must_change_pw']) if 'must_change_pw' in row.keys() else False
    session['leitstelle_id']         = row['id']
    session['leitstelle_role']       = row['rolle']
    session['leitstelle_bundesland'] = (row['disponier_bundesland'] if 'disponier_bundesland' in row.keys() else '') or ''
    session['leitstelle_bezirk']     = (row['disponier_bezirk']     if 'disponier_bezirk'     in row.keys() else '') or ''
    user = {'id': row['id'], 'vorname': row['vorname'], 'nachname': row['nachname'],
            'email': row['email'], 'rolle': row['rolle'], 'role': 'leitstelle',
            'disponier_bundesland': session['leitstelle_bundesland'],
            'disponier_bezirk':     session['leitstelle_bezirk']}
    return jsonify({'ok': True, 'user': user, 'must_change_pw': must_change,
                    'token': _make_token(row['rolle'], str(row['id']))})


@app.route('/api/leitstelle/change-password', methods=['POST'])
def leitstelle_change_password():
    lid = session.get('leitstelle_id')
    if not lid:
        return jsonify({'error': 'Nicht angemeldet'}), 401
    data   = request.get_json(silent=True) or {}
    pw_old = data.get('old_password', '')
    pw_new = data.get('new_password', '').strip()
    if len(pw_new) < 8:
        return jsonify({'error': 'Neues Passwort mind. 8 Zeichen'}), 400
    with get_db() as db:
        row = db.execute('SELECT * FROM leitstelle_users WHERE id=? AND aktiv=1', [lid]).fetchone()
        if not row:
            return jsonify({'error': 'Benutzer nicht gefunden'}), 404
        if not check_pw(row['password_hash'], pw_old):
            return jsonify({'error': 'Aktuelles Passwort falsch'}), 400
        db.execute(
            'UPDATE leitstelle_users SET password_hash=?, must_change_pw=0 WHERE id=?',
            [hash_pw(pw_new), lid]
        )
        db.commit()
    return jsonify({'ok': True})


# ── Leitstelle / Auftragslage Backup ─────────────────────────────────────────
@app.route('/api/leitstelle/backup')
def leitstelle_backup():
    err = require_leitstelle()
    if err: return err
    import json as _j, datetime as _dt
    with get_db() as db:
        def rows(sql, params=[]):
            return [dict(r) for r in db.execute(sql, params).fetchall()]
        data = {
            'exported_at': _dt.datetime.now().isoformat(),
            'bereich': 'Leitstelle',
            'einsaetze': rows(
                "SELECT e.*,p.name as patient_name,"
                "COALESCE(c.name,'') as caregiver_name "
                "FROM einsaetze e "
                "LEFT JOIN patients p ON p.id=e.patient_id "
                "LEFT JOIN caregivers c ON c.id=e.caregiver_id "
                "ORDER BY e.id DESC LIMIT 2000"),
            'einsatz_nachrichten': rows(
                "SELECT * FROM einsatz_nachrichten ORDER BY id DESC LIMIT 5000"),
            'dienste': rows(
                "SELECT d.*,c.name as caregiver_name "
                "FROM dienste d LEFT JOIN caregivers c ON c.id=d.caregiver_id "
                "ORDER BY d.datum DESC LIMIT 1000"),
            'patients': rows(
                "SELECT id,name,adresse,pflegestufe,diagnose,notizen,aktiv FROM patients ORDER BY id"),
        }
    resp = make_response(_j.dumps(data, ensure_ascii=False, indent=2, default=str))
    fname = 'nursy_backup_leitstelle_' + _dt.date.today().isoformat() + '.json'
    resp.headers['Content-Type'] = 'application/json; charset=utf-8'
    resp.headers['Content-Disposition'] = f'attachment; filename="{fname}"'
    return resp

@app.route('/api/leitstelle/gebiet', methods=['GET'])
def get_leitstelle_gebiet():
    lid = session.get('leitstelle_id')
    if not lid:
        return jsonify({'error': 'Nicht angemeldet'}), 401
    with get_db() as db:
        row = db.execute(
            'SELECT disponier_bundesland, disponier_bezirk FROM leitstelle_users WHERE id=?', [lid]
        ).fetchone()
    bl = (row['disponier_bundesland'] if row and 'disponier_bundesland' in row.keys() else '') or ''
    bz = (row['disponier_bezirk']     if row and 'disponier_bezirk'     in row.keys() else '') or ''
    return jsonify({'ok': True, 'bundesland': bl, 'bezirk': bz})


@app.route('/api/leitstelle/gebiet', methods=['PUT'])
def set_leitstelle_gebiet():
    lid = session.get('leitstelle_id')
    if not lid:
        return jsonify({'error': 'Nicht angemeldet'}), 401
    data = request.get_json(silent=True) or {}
    bl = data.get('bundesland', '').strip()
    bz = data.get('bezirk', '').strip()
    with get_db() as db:
        db.execute(
            'UPDATE leitstelle_users SET disponier_bundesland=?, disponier_bezirk=? WHERE id=?',
            [bl, bz, lid]
        )
        db.commit()
    session['leitstelle_bundesland'] = bl
    session['leitstelle_bezirk']     = bz
    return jsonify({'ok': True, 'bundesland': bl, 'bezirk': bz})


@app.route('/api/leitstelle/forgot-password', methods=['POST'])
def leitstelle_forgot_password():
    data  = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    if not email:
        return jsonify({'ok': True})  # kein Hinweis ob E-Mail existiert (Security)
    if not smtp_configured():
        return jsonify({'error': 'E-Mail-Versand nicht konfiguriert. Bitte Administrator kontaktieren.'}), 503

    with get_db() as db:
        row = db.execute(
            'SELECT id, vorname, nachname FROM leitstelle_users WHERE email=? AND aktiv=1', [email]
        ).fetchone()

    if not row:
        return jsonify({'ok': True})  # keine Info an Angreifer

    token   = os.urandom(32).hex()
    expires = str(int(time.time()) + 3600)  # 1 Stunde gültig

    with get_db() as db:
        db.execute(
            'UPDATE leitstelle_users SET pw_reset_token=?, pw_reset_expires=? WHERE id=?',
            [token, expires, row['id']]
        )
        db.commit()

    base_url = request.host_url.rstrip('/')
    reset_link = f"{base_url}/leitstelle-reset-pw.html?token={token}"
    name = f"{row['vorname']} {row['nachname']}"

    text = (
        f"Hallo {name},\n\n"
        f"Sie haben das Zurücksetzen Ihres Passworts angefordert.\n\n"
        f"Klicken Sie auf folgenden Link (gültig 1 Stunde):\n{reset_link}\n\n"
        f"Falls Sie diese Anfrage nicht gestellt haben, können Sie diese E-Mail ignorieren.\n\n"
        f"Mit freundlichen Grüßen\nNursy Leitstelle"
    )
    html = f"""<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:20px;">
<div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;padding:32px 28px;box-shadow:0 2px 12px rgba(0,0,0,.08);">
  <h2 style="color:#0f1a33;margin:0 0 8px;">Passwort zurücksetzen</h2>
  <p style="color:#64748b;font-size:.92rem;">Hallo {name},</p>
  <p style="color:#374151;">Sie haben das Zurücksetzen Ihres Passworts angefordert.</p>
  <div style="text-align:center;margin:24px 0;">
    <a href="{reset_link}" style="background:linear-gradient(135deg,#3f6fe8,#1e3a8a);color:#fff;text-decoration:none;padding:13px 28px;border-radius:10px;font-weight:700;font-size:1rem;display:inline-block;">
      Passwort zurücksetzen
    </a>
  </div>
  <p style="color:#64748b;font-size:.8rem;">Dieser Link ist <strong>1 Stunde</strong> gültig.</p>
  <p style="color:#64748b;font-size:.8rem;">Falls Sie diese Anfrage nicht gestellt haben, ignorieren Sie diese E-Mail.</p>
  <hr style="border:none;border-top:1px solid #e2e8f0;margin:20px 0;">
  <p style="color:#94a3b8;font-size:.75rem;text-align:center;">Nursy Leitstelle</p>
</div></body></html>"""

    ok, err = send_email(email, 'Nursy – Passwort zurücksetzen', text, html)
    if not ok:
        return jsonify({'error': f'E-Mail konnte nicht gesendet werden: {err}'}), 500
    return jsonify({'ok': True})


@app.route('/api/leitstelle/reset-password/validate')
def leitstelle_reset_validate():
    token = request.args.get('token', '').strip()
    if not token:
        return jsonify({'ok': False, 'error': 'Kein Token'}), 400
    now = int(time.time())
    with get_db() as db:
        row = db.execute(
            'SELECT id FROM leitstelle_users WHERE pw_reset_token=? AND aktiv=1', [token]
        ).fetchone()
    if not row:
        return jsonify({'ok': False, 'error': 'Token ungültig'})
    with get_db() as db:
        exp_row = db.execute(
            'SELECT pw_reset_expires FROM leitstelle_users WHERE pw_reset_token=?', [token]
        ).fetchone()
    expires = int(exp_row['pw_reset_expires'] or 0) if exp_row else 0
    if now > expires:
        return jsonify({'ok': False, 'error': 'Token abgelaufen'})
    return jsonify({'ok': True})


@app.route('/api/leitstelle/reset-password', methods=['POST'])
def leitstelle_reset_password():
    data   = request.get_json(silent=True) or {}
    token  = data.get('token', '').strip()
    pw_new = data.get('new_password', '').strip()
    if not token:
        return jsonify({'error': 'Kein Token'}), 400
    if len(pw_new) < 8:
        return jsonify({'error': 'Passwort mind. 8 Zeichen'}), 400
    now = int(time.time())
    with get_db() as db:
        row = db.execute(
            'SELECT id, pw_reset_expires FROM leitstelle_users WHERE pw_reset_token=? AND aktiv=1', [token]
        ).fetchone()
    if not row:
        return jsonify({'error': 'Token ungültig oder abgelaufen'}), 400
    if now > int(row['pw_reset_expires'] or 0):
        return jsonify({'error': 'Token abgelaufen – bitte neuen Link anfordern'}), 400
    with get_db() as db:
        db.execute(
            'UPDATE leitstelle_users SET password_hash=?, pw_reset_token=NULL, pw_reset_expires=NULL, must_change_pw=0 WHERE id=?',
            [hash_pw(pw_new), row['id']]
        )
        db.commit()
    return jsonify({'ok': True})


# ── E-Mail: Status + Test ─────────────────────────────────────────────────────

@app.route('/api/email/status')
def email_status():
    if not (session.get('admin') or session.get('leitstelle_id')):
        return jsonify({'error': 'Kein Zugriff'}), 403
    c = _smtp_config()
    return jsonify({'ok': True, 'configured': smtp_configured(), 'secrets': {
        'SMTP_HOST':       bool(c['host']),
        'SMTP_PORT':       bool(c['port']),
        'SMTP_USER':       bool(c['user']),
        'SMTP_PASSWORD':   bool(c['password']),
        'SMTP_FROM_NAME':  bool(c['from_name']),
        'SMTP_FROM_EMAIL': bool(c['from_email']),
    }})


@app.route('/api/email/test', methods=['POST'])
def email_test():
    if not (session.get('admin') or session.get('leitstelle_id')):
        return jsonify({'error': 'Kein Zugriff'}), 403
    data = request.get_json(silent=True) or {}
    to   = data.get('to', '').strip()
    if not to:
        return jsonify({'error': 'Empfänger fehlt'}), 400
    text = "Dies ist eine Testmail von Nursy.\n\nSMTP-Konfiguration ist korrekt eingerichtet."
    html = """<!DOCTYPE html>
<html><body style="font-family:Arial,sans-serif;background:#f4f4f4;margin:0;padding:20px;">
<div style="max-width:480px;margin:0 auto;background:#fff;border-radius:12px;padding:32px 28px;box-shadow:0 2px 12px rgba(0,0,0,.08);">
  <h2 style="color:#0f1a33;">✅ Nursy Testmail</h2>
  <p style="color:#374151;">Die SMTP-Konfiguration ist korrekt eingerichtet.</p>
  <p style="color:#64748b;font-size:.85rem;">Diese Testmail wurde über das Admin-Panel versendet.</p>
  <hr style="border:none;border-top:1px solid #e2e8f0;margin:20px 0;">
  <p style="color:#94a3b8;font-size:.75rem;text-align:center;">Nursy Leitstelle</p>
</div></body></html>"""
    ok, err = send_email(to, 'Nursy – Testmail', text, html)
    if ok:
        return jsonify({'ok': True})
    return jsonify({'error': err}), 500


@app.route('/api/leitstelle/logout', methods=['POST'])
def leitstelle_logout():
    session.clear()
    return jsonify({'ok': True})


@app.route('/api/leitstelle/me')
def leitstelle_me():
    lid = session.get('leitstelle_id')
    if session.get('admin'):
        return jsonify({'ok': True, 'user': {'id': 'admin', 'vorname': 'Admin', 'nachname': '', 'role': 'admin', 'rolle': 'admin'}})
    if not lid:
        tok = _token_from_request()
        if tok and tok['role'] in ('leitstelle', 'admin'):
            lid = tok['uid']
        else:
            return jsonify({'error': 'Nicht angemeldet'}), 401
    with get_db() as db:
        row = db.execute('SELECT * FROM leitstelle_users WHERE id=? AND aktiv=1', [lid]).fetchone()
    if not row:
        return jsonify({'error': 'Sitzung abgelaufen'}), 401
    import json as _j
    return jsonify({'ok': True, 'user': {
        'id': row['id'], 'vorname': row['vorname'], 'nachname': row['nachname'],
        'email': row['email'], 'rolle': row['rolle'], 'role': 'leitstelle',
        'seiten_zugriff': _j.loads(row['seiten_zugriff'] or '[]') if 'seiten_zugriff' in row.keys() else []
    }})


def require_leitstelle():
    if session.get('admin') or session.get('leitstelle_id'):
        return None
    tok = _token_from_request()
    if tok and tok['role'] in ('leitstelle', 'admin', 'admiral', 'disponent'):
        return None
    return jsonify({'error': 'Kein Zugriff'}), 403


# ── API: Anfragen ───────────────────────────────────────────────────────────

@app.route('/api/requests', methods=['POST'])
def create_request():
    data = request.get_json(silent=True) or {}
    patient_id = data.get('patient_id', '').strip()
    if not patient_id:
        return jsonify({'error': 'patient_id fehlt'}), 400

    # Fetch patient info from DB
    with get_db() as db:
        pat = db.execute('SELECT * FROM patients WHERE id=?', [patient_id]).fetchone()
    if not pat:
        return jsonify({'error': 'Patient nicht gefunden'}), 404

    rid = 'r' + uuid.uuid4().hex[:8]
    pat_name = pat['vorname'] + ' ' + pat['nachname']
    addr_parts = [pat['address'], pat['plz'], pat['ort']]
    pat_addr = ', '.join(p for p in addr_parts if p)
    anamnese = data.get('anamnese', {})
    pflegestufe = anamnese.get('pflegestufe', '') if isinstance(anamnese, dict) else ''
    frequenz = anamnese.get('frequenz', '') if isinstance(anamnese, dict) else ''

    with get_db() as db:
        db.execute(
            'INSERT INTO requests (id,patient_id,patient_name,patient_gender,patient_address,patient_plz,patient_ort,patient_birth,anamnese,pflegestufe,frequenz) '
            'VALUES (?,?,?,?,?,?,?,?,?,?,?)',
            [rid, patient_id, pat_name, pat['gender'],
             pat_addr, pat['plz'], pat['ort'], pat['birth'],
             json.dumps(anamnese), pflegestufe, frequenz]
        )
        db.commit()

    return jsonify({'ok': True, 'id': rid})


@app.route('/api/requests/pending')
def list_pending_requests():
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM requests WHERE status='pending' ORDER BY created_at DESC"
        ).fetchall()
    result = []
    for r in rows:
        try:
            anamnese = json.loads(r['anamnese'] or '{}')
        except Exception:
            anamnese = {}
        result.append({
            'id': r['id'],
            'patient_id': r['patient_id'],
            'patient_name': r['patient_name'],
            'patient_gender': r['patient_gender'],
            'patient_address': r['patient_address'],
            'patient_plz': r['patient_plz'],
            'patient_ort': r['patient_ort'],
            'patient_birth': r['patient_birth'],
            'anamnese': anamnese,
            'pflegestufe': r['pflegestufe'],
            'frequenz': r['frequenz'],
            'status': r['status'],
            'created_at': r['created_at'],
        })
    return jsonify({'ok': True, 'requests': result})


@app.route('/api/requests/<rid>/accept', methods=['POST'])
def accept_request(rid):
    caregiver_id = session.get('user_id', '')
    with get_db() as db:
        row = db.execute("SELECT * FROM requests WHERE id=?", [rid]).fetchone()
        if not row:
            return jsonify({'error': 'Anfrage nicht gefunden'}), 404
        db.execute(
            "UPDATE requests SET status='accepted', caregiver_id=? WHERE id=?",
            [caregiver_id, rid]
        )
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/requests/<rid>/decline', methods=['POST'])
def decline_request(rid):
    with get_db() as db:
        row = db.execute("SELECT * FROM requests WHERE id=?", [rid]).fetchone()
        if not row:
            return jsonify({'error': 'Anfrage nicht gefunden'}), 404
        db.execute("UPDATE requests SET status='declined' WHERE id=?", [rid])
        db.commit()
    return jsonify({'ok': True})


# ── Admin Auth ──────────────────────────────────────────────────────────────

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json(silent=True) or {}
    pw = data.get('password', '')
    if pw == ADMIN_PASSWORD:
        session['admin'] = True
        return jsonify({'ok': True, 'token': _make_token('admin')})
    return jsonify({'error': 'Falsches Passwort'}), 401

@app.route('/api/admin/me')
def admin_me():
    if session.get('admin'):
        return jsonify({'ok': True})
    tok = _token_from_request()
    if tok and tok['role'] == 'admin':
        return jsonify({'ok': True})
    if session.get('leitstelle_role') in ('admiral', 'disponent'):
        return jsonify({'ok': True})
    return jsonify({'ok': False}), 401

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.clear()
    return jsonify({'ok': True})

def require_admin():
    if session.get('admin'):
        return None
    if session.get('leitstelle_role') in ('admiral', 'disponent'):
        return None
    tok = _token_from_request()
    if tok and tok['role'] in ('admin', 'admiral', 'disponent'):
        return None
    return jsonify({'error': 'Kein Zugriff'}), 403


def _require_care_or_admin():
    """Allow care workers, leitstelle roles, and admin."""
    if bool(session.get('admin')):
        return None
    role = session.get('user_role') or session.get('leitstelle_role')
    if not role:
        tok = _token_from_request()
        if tok:
            role = tok.get('role')
    if role not in ('care', 'leitstelle', 'admiral', 'disponent'):
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    return None


# ── Admin: Pflegekräfte ──────────────────────────────────────────────────────

@app.route('/api/admin/caregivers')
def admin_caregivers():
    err = require_admin()
    if err: return err
    with get_db() as db:
        rows = db.execute(
            'SELECT c.id, c.vorname, c.nachname, c.email, c.gender, c.ort, c.bezirk, c.qualifikation, c.dienstnummer, c.created_at, '
            "COALESCE(s.status,'active') as status, COALESCE(s.plan,'normal') as plan, COALESCE(s.notes,'') as notes "
            'FROM caregivers c LEFT JOIN caregiver_status s ON c.id=s.caregiver_id '
            'ORDER BY c.created_at DESC'
        ).fetchall()
        result = []
        for r in rows:
            cg = dict(r)
            cg['verbindungen'] = db.execute(
                "SELECT mv.id, p.vorname, p.nachname, p.email, mv.verbunden_am "
                "FROM matching_verbindungen mv JOIN patients p ON mv.patient_id=p.id "
                "WHERE mv.caregiver_id=? AND mv.aktiv=1",
                [cg['id']]
            ).fetchall()
            cg['verbindungen'] = [dict(v) for v in cg['verbindungen']]
            cg['verbindungen_count'] = len(cg['verbindungen'])
            result.append(cg)
    return jsonify({'ok': True, 'caregivers': result})

@app.route('/api/admin/caregivers/<cid>/status', methods=['POST'])
def admin_set_caregiver_status(cid):
    err = require_admin()
    if err: return err
    data = request.get_json(silent=True) or {}
    status = data.get('status', 'active')
    plan   = data.get('plan', 'normal')
    notes  = data.get('notes', '')
    with get_db() as db:
        db.execute(
            'INSERT INTO caregiver_status (caregiver_id, status, plan, notes, updated_at) VALUES (?,?,?,?,CURRENT_TIMESTAMP) '
            'ON CONFLICT(caregiver_id) DO UPDATE SET status=excluded.status, plan=excluded.plan, notes=excluded.notes, updated_at=excluded.updated_at',
            [cid, status, plan, notes]
        )
        db.commit()
    return jsonify({'ok': True})

@app.route('/api/admin/caregivers/<cid>', methods=['DELETE'])
def admin_delete_caregiver(cid):
    err = require_admin()
    if err: return err
    with get_db() as db:
        db.execute('DELETE FROM caregivers WHERE id=?', [cid])
        db.execute('DELETE FROM caregiver_status WHERE caregiver_id=?', [cid])
        db.commit()
    return jsonify({'ok': True})


# ── Admin: Klienten (Patienten) ───────────────────────────────────────────────

@app.route('/api/admin/klienten')
def admin_list_klienten():
    err = require_admin()
    if err: return err
    q = request.args.get('q', '').strip()
    with get_db() as db:
        if q:
            like = f'%{q}%'
            rows = db.execute(
                "SELECT * FROM patients WHERE vorname LIKE ? OR nachname LIKE ? OR email LIKE ? OR ort LIKE ? "
                "ORDER BY created_at DESC",
                [like, like, like, like]
            ).fetchall()
        else:
            rows = db.execute('SELECT * FROM patients ORDER BY created_at DESC').fetchall()
        # Attach request counts
        result = []
        for r in rows:
            reqs = db.execute(
                "SELECT id, status, pflegestufe, frequenz, created_at FROM requests WHERE patient_id=? ORDER BY created_at DESC",
                [r['id']]
            ).fetchall()
            p = dict(r)
            p.pop('password_hash', None)
            p['anfragen'] = [dict(x) for x in reqs]
            p['anfragen_total']   = len(reqs)
            p['anfragen_pending'] = sum(1 for x in reqs if x['status'] == 'pending')
            # Matching-Status
            ma = db.execute(
                "SELECT id, modus, status FROM matching_anfragen WHERE patient_id=? AND status='aktiv' LIMIT 1",
                [p['id']]
            ).fetchone()
            mv = db.execute(
                "SELECT mv.id, mv.verbunden_am, c.vorname, c.nachname, c.email "
                "FROM matching_verbindungen mv JOIN caregivers c ON mv.caregiver_id=c.id "
                "WHERE mv.patient_id=? AND mv.aktiv=1 LIMIT 1",
                [p['id']]
            ).fetchone()
            p['matching_anfrage']   = dict(ma) if ma else None
            p['matching_verbindung'] = dict(mv) if mv else None
            result.append(p)
    return jsonify({'ok': True, 'klienten': result})


@app.route('/api/admin/klienten/<kid>', methods=['DELETE'])
def admin_delete_klient(kid):
    err = require_admin()
    if err: return err
    with get_db() as db:
        db.execute('DELETE FROM matching_verbindungen WHERE patient_id=?', [kid])
        db.execute('DELETE FROM matching_anfragen WHERE patient_id=?', [kid])
        db.execute("DELETE FROM public_password_reset_tokens WHERE email=(SELECT COALESCE(email,'') FROM patients WHERE id=?)", [kid])
        db.execute('DELETE FROM care_accepted_patients WHERE patient_id=?', [kid])
        db.execute('DELETE FROM requests WHERE patient_id=?', [kid])
        db.execute('DELETE FROM patients WHERE id=?', [kid])
        db.commit()
    return jsonify({'ok': True})


# ── Admin: Dienste / Leitstelle ──────────────────────────────────────────────

@app.route('/api/admin/app-klienten')
def admin_list_app_klienten():
    err = require_admin()
    if err: return err
    with get_db() as db:
        rows = db.execute(
            '''SELECT cap.id, cap.caregiver_id, cap.patient_id, cap.patient_json, cap.accepted_at,
                      c.vorname AS cg_vorname, c.nachname AS cg_nachname, c.dienstnummer AS cg_dienstnummer
               FROM care_accepted_patients cap
               LEFT JOIN caregivers c ON cap.caregiver_id = c.id
               WHERE cap.active = 1
               ORDER BY cap.accepted_at DESC'''
        ).fetchall()
    result = []
    for r in rows:
        try:
            pj = json.loads(r['patient_json'] or '{}')
        except Exception:
            pj = {}
        result.append({
            'id':            r['id'],
            'caregiver_id':  r['caregiver_id'],
            'patient_id':    r['patient_id'],
            'accepted_at':   r['accepted_at'],
            'cg_name':       (r['cg_vorname'] or '') + ' ' + (r['cg_nachname'] or ''),
            'cg_dienstnummer': r['cg_dienstnummer'] or '',
            'pat_name':      pj.get('name', ''),
            'pat_address':   pj.get('address', ''),
            'pat_hauptgrund': pj.get('hauptgrund', ''),
            'pat_gender':    pj.get('gender', ''),
        })
    return jsonify({'ok': True, 'klienten': result})


@app.route('/api/admin/app-klienten/<row_id>', methods=['DELETE'])
def admin_delete_app_klient(row_id):
    err = require_admin()
    if err: return err
    with get_db() as db:
        db.execute('UPDATE care_accepted_patients SET active=0 WHERE id=?', [row_id])
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/admin/dienste')
def admin_list_dienste():
    err = require_admin()
    if err: return err
    datum = request.args.get('datum', '')
    with get_db() as db:
        if datum:
            rows = db.execute('SELECT * FROM dienste WHERE datum=? ORDER BY von', [datum]).fetchall()
        else:
            rows = db.execute('SELECT * FROM dienste ORDER BY datum DESC, von', []).fetchall()
    return jsonify({'ok': True, 'dienste': [dict(r) for r in rows]})

@app.route('/api/admin/dienste', methods=['POST'])
def admin_create_dienst():
    err = require_admin()
    if err: return err
    data = request.get_json(silent=True) or {}
    required = ['caregiver_id', 'caregiver_name', 'datum', 'von', 'bis']
    for f in required:
        if not data.get(f, '').strip():
            return jsonify({'error': f'Feld {f} fehlt'}), 400
    did = 'd' + uuid.uuid4().hex[:8]
    with get_db() as db:
        db.execute(
            'INSERT INTO dienste (id, caregiver_id, caregiver_name, datum, von, bis, typ, fahrzeug, notiz) VALUES (?,?,?,?,?,?,?,?,?)',
            [did, data['caregiver_id'], data['caregiver_name'],
             data['datum'], data['von'], data['bis'],
             data.get('typ', 'bereitschaft'), data.get('fahrzeug', ''), data.get('notiz', '')]
        )
        db.commit()
    return jsonify({'ok': True, 'id': did})

@app.route('/api/admin/dienste/<did>', methods=['DELETE'])
def admin_delete_dienst(did):
    err = require_admin()
    if err: return err
    with get_db() as db:
        db.execute('DELETE FROM dienste WHERE id=?', [did])
        db.commit()
    return jsonify({'ok': True})


# ── Admin: Leitstelle-Benutzer ───────────────────────────────────────────────

@app.route('/api/admin/leitstelle-users')
def admin_list_leitstelle_users():
    err = require_admin()
    if err: return err
    with get_db() as db:
        rows = db.execute('SELECT id,vorname,nachname,email,rolle,aktiv,created_at FROM leitstelle_users ORDER BY created_at DESC').fetchall()
    return jsonify({'ok': True, 'users': [dict(r) for r in rows]})

# ── Benutzerverwaltung (Admiral) ─────────────────────────────────────────────

# ── Admin Backup ─────────────────────────────────────────────────────────────
@app.route('/api/admin/backup')
def admin_backup():
    if not _require_admin_or_admiral():
        return jsonify({'error': 'Kein Zugriff'}), 403
    import json as _j, datetime as _dt
    with get_db() as db:
        def rows(sql, params=[]):
            return [dict(r) for r in db.execute(sql, params).fetchall()]
        data = {
            'exported_at': _dt.datetime.now().isoformat(),
            'bereich': 'Admin',
            'leitstelle_users': rows(
                "SELECT id,vorname,nachname,email,rolle,aktiv,dienstnummer,"
                "COALESCE(seiten_zugriff,'[]') as seiten_zugriff,"
                "COALESCE(notizen,'') as notizen FROM leitstelle_users ORDER BY id"),
            'billing_users': rows(
                "SELECT id,vorname,nachname,email,rolle,aktiv,"
                "COALESCE(seiten_zugriff,'[]') as seiten_zugriff FROM billing_users ORDER BY id"),
            'caregivers': rows(
                "SELECT id,name,email,telefon,qualifikation,aktiv,dienstnummer,"
                "COALESCE(fahrzeug,'') as fahrzeug,COALESCE(bezirk,'') as bezirk "
                "FROM caregivers ORDER BY id"),
            'patients': rows(
                "SELECT id,name,adresse,pflegestufe,diagnose,notizen,aktiv FROM patients ORDER BY id"),
            'fahrzeuge': rows(
                "SELECT id,name,typ,bundesland,bezirk,aktiv,"
                "COALESCE(kennzeichen,'') as kennzeichen FROM fahrzeuge ORDER BY id"),
            'admin_messages': rows(
                "SELECT id,text,typ,erstellt_am FROM admin_messages ORDER BY id DESC LIMIT 500"),
            'billing_settings': rows("SELECT schluessel,wert FROM billing_settings"),
        }
    resp = make_response(_j.dumps(data, ensure_ascii=False, indent=2, default=str))
    fname = 'nursy_backup_admin_' + _dt.date.today().isoformat() + '.json'
    resp.headers['Content-Type'] = 'application/json; charset=utf-8'
    resp.headers['Content-Disposition'] = f'attachment; filename="{fname}"'
    return resp

@app.route('/api/admin/nutzer')
def admin_nutzer_list():
    if not _require_admin_or_admiral():
        return jsonify({'error': 'Kein Zugriff'}), 403
    import json as _j
    with get_db() as db:
        ls = db.execute(
            "SELECT id, vorname||' '||nachname as name, email, rolle, aktiv,"
            " COALESCE(seiten_zugriff,'[]') as seiten_zugriff,"
            " COALESCE(notizen,'') as notizen,"
            " COALESCE(must_change_pw,0) as must_change_pw"
            ' FROM leitstelle_users ORDER BY vorname, nachname'
        ).fetchall()
        bu = db.execute(
            "SELECT id, name, email, rolle, aktiv,"
            " COALESCE(seiten_zugriff,'[]') as seiten_zugriff,"
            " COALESCE(notizen,'') as notizen"
            ' FROM billing_users ORDER BY name'
        ).fetchall()
    def row(r, typ):
        d = {'id': r['id'], 'name': r['name'], 'email': r['email'],
             'rolle': r['rolle'], 'aktiv': bool(r['aktiv']),
             'seiten_zugriff': _j.loads(r['seiten_zugriff'] or '[]'),
             'notizen': r['notizen'], 'typ': typ}
        if typ == 'leitstelle':
            d['must_change_pw'] = bool(r['must_change_pw'])
        return d
    return jsonify({'ok': True,
                    'leitstelle': [row(r,'leitstelle') for r in ls],
                    'billing':    [row(r,'billing')    for r in bu]})


@app.route('/api/admin/nutzer/<typ>/<uid>', methods=['PUT'])
def admin_nutzer_update(typ, uid):
    if not _require_admin_or_admiral():
        return jsonify({'error': 'Kein Zugriff'}), 403
    import json as _j
    data = request.get_json(silent=True) or {}
    if typ == 'leitstelle':
        table = 'leitstelle_users'
    elif typ == 'billing':
        table = 'billing_users'
    else:
        return jsonify({'error': 'Unbekannter Typ'}), 400
    sets, vals = [], []
    if 'rolle' in data:
        sets.append('rolle=?'); vals.append(data['rolle'])
    if 'aktiv' in data:
        sets.append('aktiv=?'); vals.append(1 if data['aktiv'] else 0)
    if 'seiten_zugriff' in data:
        sets.append('seiten_zugriff=?'); vals.append(_j.dumps(data['seiten_zugriff'], ensure_ascii=False))
    if 'notizen' in data:
        sets.append('notizen=?'); vals.append(data['notizen'])
    if 'password' in data and data['password']:
        if len(data['password']) < 8:
            return jsonify({'error': 'Passwort mind. 8 Zeichen'}), 400
        sets.append('password_hash=?'); vals.append(hash_pw(data['password']))
        if typ == 'leitstelle':
            sets.append('must_change_pw=?'); vals.append(1)
    if 'must_change_pw' in data:
        if typ == 'leitstelle':
            sets.append('must_change_pw=?'); vals.append(1 if data['must_change_pw'] else 0)
    if not sets:
        return jsonify({'error': 'Nichts zu aktualisieren'}), 400
    vals.append(uid)
    with get_db() as db:
        db.execute(f'UPDATE {table} SET {",".join(sets)} WHERE id=?', vals)
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/admin/nutzer/<typ>', methods=['POST'])
def admin_nutzer_create(typ):
    if not _require_admin_or_admiral():
        return jsonify({'error': 'Kein Zugriff'}), 403
    import json as _j
    data = request.get_json(silent=True) or {}
    pw = data.get('password', '').strip()
    if len(pw) < 8:
        return jsonify({'error': 'Passwort mind. 8 Zeichen'}), 400
    rolle = data.get('rolle', 'disponent' if typ == 'leitstelle' else 'verrechnungsstelle')
    sz = _j.dumps(data.get('seiten_zugriff', []), ensure_ascii=False)
    notizen = data.get('notizen', '')
    if typ == 'leitstelle':
        vn = data.get('vorname', '').strip()
        nn = data.get('nachname', '').strip()
        em = data.get('email', '').strip().lower()
        if not vn or not nn or not em:
            return jsonify({'error': 'Vorname, Nachname und E-Mail erforderlich'}), 400
        uid = 'ls_' + __import__('uuid').uuid4().hex[:8]
        with get_db() as db:
            db.execute(
                'INSERT INTO leitstelle_users (id,vorname,nachname,email,password_hash,rolle,aktiv,seiten_zugriff,notizen,must_change_pw)'
                ' VALUES (?,?,?,?,?,?,1,?,?,1)',
                [uid, vn, nn, em, hash_pw(pw), rolle, sz, notizen]
            )
            db.commit()
        return jsonify({'ok': True, 'id': uid})
    elif typ == 'billing':
        name = data.get('name', '').strip()
        em   = data.get('email', '').strip().lower()
        if not name or not em:
            return jsonify({'error': 'Name und E-Mail erforderlich'}), 400
        uid = 'bu_' + __import__('uuid').uuid4().hex[:8]
        with get_db() as db:
            db.execute(
                'INSERT INTO billing_users (id,name,email,password_hash,rolle,aktiv,seiten_zugriff,notizen)'
                ' VALUES (?,?,?,?,?,1,?,?)',
                [uid, name, em, hash_pw(pw), rolle, sz, notizen]
            )
            db.commit()
        return jsonify({'ok': True, 'id': uid})
    return jsonify({'error': 'Unbekannter Typ'}), 400


@app.route('/api/admin/nutzer/<typ>/<uid>', methods=['DELETE'])
def admin_nutzer_delete(typ, uid):
    if not _require_admin_or_admiral():
        return jsonify({'error': 'Kein Zugriff'}), 403
    if typ == 'leitstelle':
        table = 'leitstelle_users'
    elif typ == 'billing':
        table = 'billing_users'
    else:
        return jsonify({'error': 'Unbekannter Typ'}), 400
    with get_db() as db:
        db.execute(f'DELETE FROM {table} WHERE id=?', [uid])
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/admin/leitstelle-users', methods=['POST'])
def admin_create_leitstelle_user():
    err = require_admin()
    if err: return err
    data = request.get_json(silent=True) or {}
    for f in ['vorname', 'nachname', 'email', 'password']:
        if not data.get(f, '').strip():
            return jsonify({'error': f'Feld "{f}" fehlt'}), 400
    if len(data['password']) < 8:
        return jsonify({'error': 'Passwort mind. 8 Zeichen'}), 400
    uid = 'ls_' + uuid.uuid4().hex[:8]
    try:
        with get_db() as db:
            db.execute(
                'INSERT INTO leitstelle_users (id,vorname,nachname,email,password_hash,rolle,aktiv) VALUES (?,?,?,?,?,?,1)',
                [uid, data['vorname'].strip(), data['nachname'].strip(),
                 data['email'].strip().lower(), hash_pw(data['password']),
                 data.get('rolle', 'disponent')]
            )
            db.commit()
    except Exception as ex:
        return jsonify({'error': str(ex)}), 409
    return jsonify({'ok': True, 'id': uid})

@app.route('/api/admin/leitstelle-users/<uid>', methods=['DELETE'])
def admin_delete_leitstelle_user(uid):
    err = require_admin()
    if err: return err
    with get_db() as db:
        db.execute('DELETE FROM leitstelle_users WHERE id=?', [uid])
        db.commit()
    return jsonify({'ok': True})

@app.route('/api/admin/leitstelle-users/<uid>/password', methods=['POST'])
def admin_reset_leitstelle_pw(uid):
    err = require_admin()
    if err: return err
    data = request.get_json(silent=True) or {}
    pw = data.get('password', '').strip()
    if len(pw) < 8:
        return jsonify({'error': 'Passwort mind. 8 Zeichen'}), 400
    with get_db() as db:
        db.execute('UPDATE leitstelle_users SET password_hash=? WHERE id=?', [hash_pw(pw), uid])
        db.commit()
    return jsonify({'ok': True})


# ── Admin: Pfleger-Konten (Kurzerfassung) ────────────────────────────────────

@app.route('/api/admin/pfleger', methods=['POST'])
def admin_create_pfleger():
    err = require_admin()
    if err: return err
    data = request.get_json(silent=True) or {}
    for f in ['vorname', 'nachname', 'email', 'password']:
        if not data.get(f, '').strip():
            return jsonify({'error': f'Feld "{f}" fehlt'}), 400
    if len(data['password']) < 8:
        return jsonify({'error': 'Passwort mind. 8 Zeichen'}), 400
    uid = 'c' + uuid.uuid4().hex[:8]
    try:
        with get_db() as db:
            db.execute(
                'INSERT INTO caregivers (id,vorname,nachname,email,password_hash,gender,address,plz,ort,bezirk) VALUES (?,?,?,?,?,?,?,?,?,?)',
                [uid, data['vorname'].strip(), data['nachname'].strip(),
                 data['email'].strip().lower(), hash_pw(data['password']),
                 data.get('gender',''), data.get('address',''),
                 data.get('plz',''), data.get('ort',''), data.get('bezirk','')]
            )
            db.commit()
    except Exception as ex:
        return jsonify({'error': str(ex)}), 409
    return jsonify({'ok': True, 'id': uid})


# ── Admin: Nachrichten ───────────────────────────────────────────────────────

@app.route('/api/admin/messages')
def admin_list_messages():
    err = require_admin()
    if err: return err
    with get_db() as db:
        rows = db.execute('SELECT * FROM admin_messages ORDER BY created_at DESC').fetchall()
    return jsonify({'ok': True, 'messages': [dict(r) for r in rows]})

@app.route('/api/admin/messages', methods=['POST'])
def admin_create_message():
    err = require_admin()
    if err: return err
    data = request.get_json(silent=True) or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'Text fehlt'}), 400
    mid = 'm' + uuid.uuid4().hex[:8]
    with get_db() as db:
        db.execute(
            'INSERT INTO admin_messages (id, text, typ, aktiv) VALUES (?,?,?,1)',
            [mid, text, data.get('typ', 'info')]
        )
        db.commit()
    return jsonify({'ok': True, 'id': mid})

@app.route('/api/admin/messages/<mid>', methods=['DELETE'])
def admin_delete_message(mid):
    err = require_admin()
    if err: return err
    with get_db() as db:
        db.execute('DELETE FROM admin_messages WHERE id=?', [mid])
        db.commit()
    return jsonify({'ok': True})

# Public: aktive Meldungen fürs Dashboard
@app.route('/api/messages/active')
def public_active_messages():
    with get_db() as db:
        rows = db.execute('SELECT id, text, typ FROM admin_messages WHERE aktiv=1 ORDER BY created_at DESC').fetchall()
    return jsonify({'ok': True, 'messages': [dict(r) for r in rows]})


# ── Admin: Stats ─────────────────────────────────────────────────────────────

@app.route('/api/admin/stats')
def admin_stats():
    err = require_admin()
    if err: return err
    with get_db() as db:
        cg_total  = db.execute('SELECT COUNT(*) FROM caregivers').fetchone()[0]
        cg_active = db.execute("SELECT COUNT(*) FROM caregivers c LEFT JOIN caregiver_status s ON c.id=s.caregiver_id WHERE COALESCE(s.status,'active')='active'").fetchone()[0]
        cg_locked = db.execute("SELECT COUNT(*) FROM caregiver_status WHERE status='locked'").fetchone()[0]
        pat_total = db.execute('SELECT COUNT(*) FROM patients').fetchone()[0]
        req_pend  = db.execute("SELECT COUNT(*) FROM requests WHERE status='pending'").fetchone()[0]
        today = __import__('datetime').date.today().isoformat()
        dienste_today      = db.execute("SELECT COUNT(*) FROM dienste WHERE datum=?", (today,)).fetchone()[0]
        match_verbindungen = db.execute("SELECT COUNT(*) FROM matching_verbindungen WHERE aktiv=1").fetchone()[0]
        match_anfragen     = db.execute("SELECT COUNT(*) FROM matching_anfragen WHERE status='aktiv'").fetchone()[0]
    return jsonify({'ok': True, 'stats': {
        'cg_total': cg_total, 'cg_active': cg_active, 'cg_locked': cg_locked,
        'pat_total': pat_total, 'req_pending': req_pend, 'dienste_today': dienste_today,
        'match_verbindungen': match_verbindungen, 'match_anfragen': match_anfragen,
    }})


# ── Einsätze API ─────────────────────────────────────────────────────────────

@app.route('/api/fahrzeuge/<name>/nachrichten', methods=['GET'])
def get_fahrzeug_nachrichten(name):
    """Return the message thread for the current active einsatz of a vehicle."""
    with get_db() as db:
        row = db.execute(
            "SELECT id FROM einsaetze WHERE fahrzeug=? AND status NOT IN ('beendet','storniert') ORDER BY datum DESC, zeit DESC LIMIT 1",
            (name,)
        ).fetchone()
        if not row:
            return jsonify({'einsatz_id': None, 'nachrichten': []})
        eid = row['id']
        msgs = db.execute(
            "SELECT * FROM einsatz_nachrichten WHERE einsatz_id=? ORDER BY created_at ASC", (eid,)
        ).fetchall()
    return jsonify({'einsatz_id': eid, 'nachrichten': [row_to_dict(r) for r in msgs]})

@app.route('/api/fahrzeuge/<name>/nachrichten', methods=['POST'])
def send_fahrzeug_nachricht(name):
    """Send a message from Leitstelle to the active einsatz of a vehicle."""
    data = request.get_json(silent=True) or {}
    text = data.get('text', '').strip()
    if not text:
        return jsonify({'error': 'empty'}), 400
    with get_db() as db:
        row = db.execute(
            "SELECT id FROM einsaetze WHERE fahrzeug=? AND status NOT IN ('beendet','storniert') ORDER BY datum DESC, zeit DESC LIMIT 1",
            (name,)
        ).fetchone()
        if not row:
            return jsonify({'error': 'Kein aktiver Einsatz'}), 404
        eid = row['id']
        mid = 'msg_' + str(uuid.uuid4())[:8]
        db.execute(
            "INSERT INTO einsatz_nachrichten (id,einsatz_id,sender,text) VALUES (?,?,?,?)",
            (mid, eid, 'leitstelle', text)
        )
    return jsonify({'ok': True, 'id': mid, 'einsatz_id': eid})


# ── Push API ─────────────────────────────────────────────────────────────────

@app.route('/api/push/vapid-public-key')
def push_vapid_public_key():
    return jsonify({'key': os.environ.get('VAPID_PUBLIC_KEY', '')})

@app.route('/api/push/subscribe', methods=['POST'])
def push_subscribe():
    data     = request.get_json(silent=True) or {}
    endpoint = data.get('endpoint', '').strip()
    keys     = data.get('keys') or {}
    p256dh   = keys.get('p256dh', '').strip()
    auth     = keys.get('auth', '').strip()
    fahrzeug = data.get('fahrzeug', '').strip()
    if not endpoint or not p256dh or not auth or not fahrzeug:
        return jsonify({'ok': False, 'error': 'Fehlende Felder'}), 400
    sub_id  = 'ps_' + uuid.uuid4().hex[:8]
    user_id = session.get('user_id', '') or ''
    with get_db() as db:
        db.execute('DELETE FROM push_subscriptions WHERE endpoint=?', (endpoint,))
        db.execute(
            'INSERT INTO push_subscriptions (id,fahrzeug,user_id,endpoint,p256dh,auth) VALUES (?,?,?,?,?,?)',
            (sub_id, fahrzeug, user_id, endpoint, p256dh, auth)
        )
        db.commit()
    return jsonify({'ok': True})

@app.route('/api/push/unsubscribe', methods=['POST'])
def push_unsubscribe():
    data     = request.get_json(silent=True) or {}
    endpoint = data.get('endpoint', '').strip()
    fahrzeug = data.get('fahrzeug', '').strip()
    with get_db() as db:
        if endpoint:
            db.execute('DELETE FROM push_subscriptions WHERE endpoint=?', (endpoint,))
        elif fahrzeug:
            db.execute('DELETE FROM push_subscriptions WHERE fahrzeug=?', (fahrzeug,))
        db.commit()
    return jsonify({'ok': True})

@app.route('/api/einsaetze', methods=['GET'])
def list_einsaetze():
    import datetime as _dt
    cutoff = (_dt.datetime.utcnow() - _dt.timedelta(hours=12)).strftime('%Y-%m-%d %H:%M:%S')
    with get_db() as db:
        rows = db.execute(
            """SELECT * FROM einsaetze
               WHERE status NOT IN ('beendet','storniert')
                  OR (status IN ('beendet','storniert') AND archiviert_am > ?)
               ORDER BY created_at DESC LIMIT 100""",
            (cutoff,)
        ).fetchall()
    result = []
    for row in rows:
        e = row_to_dict(row)
        e['risiken'] = json.loads(e.get('risiken') or '[]')
        e['extra']   = json.loads(e.get('extra')   or '{}')
        result.append(e)
    return jsonify(result)

@app.route('/api/einsaetze', methods=['POST'])
def create_einsatz():
    data = request.get_json(silent=True) or {}
    eid  = data.get('id') or ('e_' + str(uuid.uuid4())[:8])
    pname = data.get('patient_name', '').strip()
    with get_db() as db:
        pid_lookup = ''
        if pname:
            parts = pname.strip().split()
            if len(parts) >= 2:
                prow = db.execute(
                    "SELECT id FROM patients WHERE vorname=? AND nachname=?",
                    (parts[0], parts[-1])
                ).fetchone()
                if not prow:
                    like = '%' + pname + '%'
                    prow = db.execute(
                        "SELECT id FROM patients WHERE (vorname||' '||nachname) LIKE ?",
                        (like,)
                    ).fetchone()
            else:
                like = '%' + pname + '%'
                prow = db.execute(
                    "SELECT id FROM patients WHERE (vorname||' '||nachname) LIKE ?",
                    (like,)
                ).fetchone()
            if prow:
                pid_lookup = prow['id']
        _einsatz_params = (eid,
             data.get('nummer',''),   data.get('art',''),        data.get('dringlichkeit',''),
             pname, data.get('patient_adresse',''),
             data.get('patient_plz',''),  data.get('patient_ort',''),
             data.get('patient_geburt',''), data.get('patient_sv',''), data.get('patient_tel',''),
             data.get('bezirk',''),    data.get('bundesland',''), data.get('schluessel',''), data.get('adressinfo',''),
             data.get('problem',''),   json.dumps(data.get('risiken',[])),
             data.get('allergien',''), data.get('medikamente',''), data.get('anordnungen',''),
             data.get('qualifikation',''), data.get('fahrzeug',''), data.get('disponent',''),
             data.get('datum',''),     data.get('zeit',''),
             data.get('ang_name',''),  data.get('ang_tel',''),
             data.get('notiz',''),     json.dumps(data.get('extra',{})),
             data.get('status','alarmiert'), pid_lookup)
        if USE_PG:
            db.execute(
                '''INSERT INTO einsaetze
                   (id,nummer,art,dringlichkeit,patient_name,patient_adresse,patient_plz,patient_ort,
                    patient_geburt,patient_sv,patient_tel,bezirk,bundesland,schluessel,adressinfo,
                    problem,risiken,allergien,medikamente,anordnungen,qualifikation,
                    fahrzeug,disponent,datum,zeit,ang_name,ang_tel,notiz,extra,status,patient_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT (id) DO UPDATE SET
                   nummer=EXCLUDED.nummer, art=EXCLUDED.art, dringlichkeit=EXCLUDED.dringlichkeit,
                   patient_name=EXCLUDED.patient_name, patient_adresse=EXCLUDED.patient_adresse,
                   patient_plz=EXCLUDED.patient_plz, patient_ort=EXCLUDED.patient_ort,
                   patient_geburt=EXCLUDED.patient_geburt, patient_sv=EXCLUDED.patient_sv,
                   patient_tel=EXCLUDED.patient_tel, bezirk=EXCLUDED.bezirk,
                   bundesland=EXCLUDED.bundesland,
                   schluessel=EXCLUDED.schluessel, adressinfo=EXCLUDED.adressinfo,
                   problem=EXCLUDED.problem, risiken=EXCLUDED.risiken,
                   allergien=EXCLUDED.allergien, medikamente=EXCLUDED.medikamente,
                   anordnungen=EXCLUDED.anordnungen, qualifikation=EXCLUDED.qualifikation,
                   fahrzeug=EXCLUDED.fahrzeug, disponent=EXCLUDED.disponent,
                   datum=EXCLUDED.datum, zeit=EXCLUDED.zeit,
                   ang_name=EXCLUDED.ang_name, ang_tel=EXCLUDED.ang_tel,
                   notiz=EXCLUDED.notiz, extra=EXCLUDED.extra, status=EXCLUDED.status,
                   patient_id=EXCLUDED.patient_id''',
                _einsatz_params)
        else:
            db.execute(
                '''INSERT OR REPLACE INTO einsaetze
                   (id,nummer,art,dringlichkeit,patient_name,patient_adresse,patient_plz,patient_ort,
                    patient_geburt,patient_sv,patient_tel,bezirk,bundesland,schluessel,adressinfo,
                    problem,risiken,allergien,medikamente,anordnungen,qualifikation,
                    fahrzeug,disponent,datum,zeit,ang_name,ang_tel,notiz,extra,status,patient_id)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                _einsatz_params)
        db.commit()
    # ── Push-Alarm an zugewiesenes Fahrzeug ──────────────────────────────────
    fz_alarm = data.get('fahrzeug', '').strip()
    if fz_alarm:
        _art     = (data.get('art') or 'Einsatz').strip()
        _patient = (data.get('patient_name') or '').strip()
        _bezirk  = (data.get('bezirk') or '').strip()
        _dring   = (data.get('dringlichkeit') or '').strip().upper()
        _body    = ' · '.join(filter(None, [_patient, _bezirk, _dring]))
        _send_push_to_fahrzeug(fz_alarm, f'🚨 {_art}', _body or 'Neuer Einsatz!')
    return jsonify({'id': eid, 'ok': True, 'patient_id': pid_lookup})

@app.route('/api/einsaetze/aktuell')
def get_aktuell_einsatz():
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM einsaetze WHERE status NOT IN ('beendet','storniert') ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
    if not row:
        return jsonify(None)
    e = row_to_dict(row)
    e['risiken'] = json.loads(e.get('risiken') or '[]')
    e['extra']   = json.loads(e.get('extra')   or '{}')
    return jsonify(e)

@app.route('/api/einsaetze/<eid>')
def get_einsatz(eid):
    with get_db() as db:
        row = db.execute("SELECT * FROM einsaetze WHERE id=?", (eid,)).fetchone()
    if not row:
        return jsonify({'error': 'not found'}), 404
    e = row_to_dict(row)
    e['risiken'] = json.loads(e.get('risiken') or '[]')
    e['extra']   = json.loads(e.get('extra')   or '{}')
    return jsonify(e)

@app.route('/api/einsaetze/<eid>', methods=['PUT'])
def update_einsatz_content(eid):
    """Leitstelle edits content fields of an existing Einsatz; sets ls_geaendert flag."""
    import datetime as _dt
    err = require_leitstelle()
    if err:
        return err
    data = request.get_json(silent=True) or {}
    with get_db() as db:
        row = db.execute('SELECT * FROM einsaetze WHERE id=?', (eid,)).fetchone()
        if not row:
            return jsonify({'ok': False, 'error': 'Nicht gefunden'}), 404
        update_fields = {}
        content_changed = False
        # All editable content fields → change triggers gold flag in Auftragslage
        for field in ('notiz', 'art', 'dringlichkeit', 'problem', 'adressinfo',
                      'patient_name', 'patient_adresse', 'patient_plz', 'patient_ort',
                      'patient_geburt', 'patient_sv', 'patient_tel',
                      'ang_name', 'ang_tel',
                      'datum', 'zeit', 'nummer',
                      'qualifikation', 'bezirk', 'bundesland', 'schluessel',
                      'allergien', 'medikamente', 'anordnungen'):
            if field in data:
                new_val = str(data[field]).strip()
                old_val = str(row[field] or '').strip()
                update_fields[field] = new_val
                if new_val != old_val:
                    content_changed = True
        # extra (JSON) — save but compare as string for change detection
        if 'extra' in data:
            import json as _json
            new_extra = _json.dumps(data['extra'], ensure_ascii=False, sort_keys=True)
            old_extra = str(row['extra'] or '{}')
            update_fields['extra'] = new_extra
            if new_extra != old_extra:
                content_changed = True
        # fahrzeug = reassignment; save but NO gold flag
        if 'fahrzeug' in data:
            update_fields['fahrzeug'] = str(data['fahrzeug']).strip()
        if content_changed:
            update_fields['ls_geaendert'] = _dt.datetime.now().strftime('%H:%M')
        if update_fields:
            set_clause = ', '.join(k + '=?' for k in update_fields)
            db.execute('UPDATE einsaetze SET ' + set_clause + ' WHERE id=?',
                       list(update_fields.values()) + [eid])
            db.commit()
    return jsonify({'ok': True, 'content_changed': content_changed})


@app.route('/api/einsaetze/<eid>/geaendert-quittieren', methods=['POST'])
def einsatz_geaendert_quittieren(eid):
    """Care worker acknowledges a Leitstelle edit; clears the gold flag."""
    with get_db() as db:
        db.execute("UPDATE einsaetze SET ls_geaendert='' WHERE id=?", (eid,))
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/einsaetze/<eid>/status', methods=['POST'])
def update_einsatz_status(eid):
    import datetime as _dt
    data   = request.get_json(silent=True) or {}
    status = data.get('status','')
    if status not in ('alarmiert','angenommen','unterwegs','eingetroffen','beendet','einsatzbereit','storniert'):
        return jsonify({'error': 'invalid status'}), 400
    client_zeit = (data.get('zeit') or '').strip()
    import re as _re
    now = client_zeit if _re.match(r'^\d{2}:\d{2}$', client_zeit) else _dt.datetime.now().strftime('%H:%M')
    ts_col = {'angenommen': 'zeit_angenommen', 'unterwegs': 'zeit_unterwegs', 'eingetroffen': 'zeit_eingetroffen', 'beendet': 'zeit_beendet'}.get(status)
    akteur = data.get('akteur', '') or session.get('caregiver_name', '') or session.get('username', '')
    akteur_typ = data.get('akteur_typ', 'pfleger')
    status_labels = {
        'alarmiert': 'Alarmiert', 'angenommen': 'Angenommen', 'unterwegs': 'Unterwegs',
        'eingetroffen': 'Eingetroffen', 'beendet': 'Einsatz beendet', 'einsatzbereit': 'Einsatzbereit'
    }
    with get_db() as db:
        if ts_col:
            db.execute(f"UPDATE einsaetze SET status=?, {ts_col}=? WHERE id=?", (status, now, eid))
        else:
            db.execute("UPDATE einsaetze SET status=? WHERE id=?", (status, eid))
        # Abschluss-Zeitstempel setzen (archiviert=1 erst nach 12 Std. via /api/archiv)
        if status in ('beendet', 'storniert'):
            db.execute("UPDATE einsaetze SET archiviert_am=CURRENT_TIMESTAMP WHERE id=?", (eid,))
        # Log to Protokoll
        db.execute(
            "INSERT INTO einsatz_protokoll (einsatz_id, aktion, details, akteur, akteur_typ) VALUES (?,?,?,?,?)",
            (eid, 'status', status_labels.get(status, status), akteur, akteur_typ)
        )
        db.commit()
        row = db.execute("SELECT status,zeit_angenommen,zeit_unterwegs,zeit_eingetroffen,zeit_beendet FROM einsaetze WHERE id=?", (eid,)).fetchone()
    r = dict(row) if row else {}
    return jsonify({'ok': True, 'status': status,
                    'zeit_angenommen':  r.get('zeit_angenommen',''),
                    'zeit_unterwegs':   r.get('zeit_unterwegs',''),
                    'zeit_eingetroffen':r.get('zeit_eingetroffen',''),
                    'zeit_beendet':     r.get('zeit_beendet','')})


@app.route('/api/einsaetze/<eid>/protokoll', methods=['GET'])
def get_einsatz_protokoll(eid):
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM einsatz_protokoll WHERE einsatz_id=? ORDER BY zeitpunkt ASC", (eid,)
        ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route('/api/einsaetze/<eid>/protokoll', methods=['POST'])
def add_einsatz_protokoll(eid):
    data = request.get_json(silent=True) or {}
    aktion = data.get('aktion','').strip()
    if not aktion:
        return jsonify({'error': 'aktion erforderlich'}), 400
    akteur = data.get('akteur', '') or session.get('caregiver_name', '') or session.get('username', '')
    with get_db() as db:
        db.execute(
            "INSERT INTO einsatz_protokoll (einsatz_id, aktion, details, akteur, akteur_typ) VALUES (?,?,?,?,?)",
            (eid, aktion, data.get('details',''), akteur, data.get('akteur_typ','pfleger'))
        )
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/einsaetze/<eid>/protokoll-voll')
def get_einsatz_protokoll_voll(eid):
    """Aggregiert alle Protokolldaten eines Einsatzes für die Protokoll-Ansicht."""
    with get_db() as db:
        einsatz_row = db.execute("SELECT * FROM einsaetze WHERE id=?", (eid,)).fetchone()
        if not einsatz_row:
            return jsonify({'error': 'Einsatz nicht gefunden'}), 404
        e = row_to_dict(einsatz_row)
        e['risiken'] = json.loads(e.get('risiken') or '[]')
        e['extra']   = json.loads(e.get('extra')   or '{}')

        # Patient
        patient = {}
        if e.get('patient_id'):
            pr = db.execute("SELECT * FROM patients WHERE id=?", (e['patient_id'],)).fetchone()
            if pr:
                patient = row_to_dict(pr)
                patient['extra'] = json.loads(patient.get('extra') or patient.get('profil_extra') or '{}')

        # Protokoll-Timeline
        protokoll = [dict(r) for r in db.execute(
            "SELECT * FROM einsatz_protokoll WHERE einsatz_id=? ORDER BY zeitpunkt ASC", (eid,)
        ).fetchall()]

        # Nachrichten
        nachrichten = [dict(r) for r in db.execute(
            "SELECT * FROM einsatz_nachrichten WHERE einsatz_id=? ORDER BY created_at ASC", (eid,)
        ).fetchall()]

        # Pflege-Dokumentation (am Einsatzdatum)
        dokumentation = []
        if e.get('patient_id'):
            datum_filter = (e.get('datum') or '')[:10]
            if datum_filter:
                dokumentation = [dict(r) for r in db.execute(
                    "SELECT * FROM patient_dokumentation WHERE patient_id=? AND datum=? ORDER BY uhrzeit ASC",
                    (e['patient_id'], datum_filter)
                ).fetchall()]
            else:
                dokumentation = [dict(r) for r in db.execute(
                    "SELECT * FROM patient_dokumentation WHERE patient_id=? ORDER BY datum DESC, uhrzeit DESC LIMIT 20",
                    (e['patient_id'],)
                ).fetchall()]

            # Vitalzeichen (am Einsatzdatum)
            vitalzeichen = [dict(r) for r in db.execute(
                "SELECT * FROM patient_vitalzeichen WHERE patient_id=? AND datum=? ORDER BY uhrzeit ASC",
                (e['patient_id'], datum_filter or '9999')
            ).fetchall()]

            # Dokumente / Dateien
            dokumente = [dict(r) for r in db.execute(
                "SELECT id,typ,original_name,stored_name,beschreibung,uploaded_by,created_at FROM patient_dokumente WHERE patient_id=? ORDER BY created_at DESC",
                (e['patient_id'],)
            ).fetchall()]
            for d in dokumente:
                d['url'] = '/api/uploads/' + d['stored_name'] if d.get('stored_name') else ''
        else:
            vitalzeichen = []
            dokumente    = []

    return jsonify({
        'ok': True,
        'einsatz': e,
        'patient': patient,
        'protokoll': protokoll,
        'nachrichten': nachrichten,
        'dokumentation': dokumentation,
        'vitalzeichen': vitalzeichen,
        'dokumente': dokumente,
    })


@app.route('/api/archiv/einsaetze')
def archiv_list():
    if not _require_admin_or_admiral():
        return jsonify({'error': 'Kein Zugriff'}), 403
    import datetime as _dt
    cutoff = (_dt.datetime.utcnow() - _dt.timedelta(hours=12)).strftime('%Y-%m-%d %H:%M:%S')
    with get_db() as db:
        # Legacy archiviert=1 + neue: beendet/storniert, älter als 12h
        rows = db.execute(
            """SELECT * FROM einsaetze
               WHERE archiviert=1
                  OR (status IN ('beendet','storniert')
                      AND archiviert_am != ''
                      AND archiviert_am <= ?)
               ORDER BY archiviert_am DESC LIMIT 500""",
            (cutoff,)
        ).fetchall()
    result = []
    for row in rows:
        e = row_to_dict(row)
        e['risiken'] = json.loads(e.get('risiken') or '[]')
        e['extra']   = json.loads(e.get('extra')   or '{}')
        result.append(e)
    return jsonify({'ok': True, 'einsaetze': result})


@app.route('/api/archiv/einsaetze/<eid>/folgeeinsatz', methods=['POST'])
def archiv_folgeeinsatz(eid):
    if not _require_admin_or_admiral():
        return jsonify({'error': 'Kein Zugriff'}), 403
    data = request.get_json(silent=True) or {}
    with get_db() as db:
        orig = db.execute("SELECT * FROM einsaetze WHERE id=?", (eid,)).fetchone()
    if not orig:
        return jsonify({'error': 'Einsatz nicht gefunden'}), 404
    o = row_to_dict(orig)
    new_id = 'e_' + str(uuid.uuid4())[:8]
    import datetime as _dt
    today = _dt.date.today().strftime('%Y-%m-%d')
    time_now = _dt.datetime.now().strftime('%H:%M')
    new_data = {
        'id': new_id,
        'nummer': data.get('nummer', ''),
        'art': o.get('art', ''),
        'dringlichkeit': o.get('dringlichkeit', ''),
        'patient_name': o.get('patient_name', ''),
        'patient_adresse': o.get('patient_adresse', ''),
        'patient_plz': o.get('patient_plz', ''),
        'patient_ort': o.get('patient_ort', ''),
        'patient_geburt': o.get('patient_geburt', ''),
        'patient_sv': o.get('patient_sv', ''),
        'patient_tel': o.get('patient_tel', ''),
        'bezirk': o.get('bezirk', ''),
        'bundesland': o.get('bundesland', ''),
        'schluessel': o.get('schluessel', ''),
        'adressinfo': o.get('adressinfo', ''),
        'problem': data.get('problem', o.get('problem', '')),
        'risiken': json.loads(o.get('risiken') or '[]'),
        'allergien': o.get('allergien', ''),
        'medikamente': o.get('medikamente', ''),
        'anordnungen': o.get('anordnungen', ''),
        'qualifikation': o.get('qualifikation', ''),
        'fahrzeug': data.get('fahrzeug', ''),
        'disponent': session.get('username', ''),
        'datum': today,
        'zeit': time_now,
        'ang_name': o.get('ang_name', ''),
        'ang_tel': o.get('ang_tel', ''),
        'notiz': f"Folgeeinsatz von {eid}. " + data.get('notiz', ''),
        'extra': {},
        'status': 'alarmiert',
        'patient_id': o.get('patient_id', ''),
    }
    # Reuse create_einsatz logic
    with get_db() as db:
        params = (
            new_id, new_data['nummer'], new_data['art'], new_data['dringlichkeit'],
            new_data['patient_name'], new_data['patient_adresse'], new_data['patient_plz'],
            new_data['patient_ort'], new_data['patient_geburt'], new_data['patient_sv'],
            new_data['patient_tel'], new_data['bezirk'], new_data['bundesland'],
            new_data['schluessel'], new_data['adressinfo'], new_data['problem'],
            json.dumps(new_data['risiken']), new_data['allergien'], new_data['medikamente'],
            new_data['anordnungen'], new_data['qualifikation'], new_data['fahrzeug'],
            new_data['disponent'], new_data['datum'], new_data['zeit'],
            new_data['ang_name'], new_data['ang_tel'], new_data['notiz'],
            json.dumps(new_data['extra']), 'alarmiert', new_data['patient_id']
        )
        db.execute(
            '''INSERT INTO einsaetze
               (id,nummer,art,dringlichkeit,patient_name,patient_adresse,patient_plz,patient_ort,
                patient_geburt,patient_sv,patient_tel,bezirk,bundesland,schluessel,adressinfo,
                problem,risiken,allergien,medikamente,anordnungen,qualifikation,
                fahrzeug,disponent,datum,zeit,ang_name,ang_tel,notiz,extra,status,patient_id)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            params
        )
        db.execute(
            "INSERT INTO einsatz_protokoll (einsatz_id, aktion, details, akteur, akteur_typ) VALUES (?,?,?,?,?)",
            (new_id, 'erstellt', f'Folgeeinsatz von Archiv-Einsatz {eid}', session.get('username',''), 'leitstelle')
        )
        db.commit()
    return jsonify({'ok': True, 'id': new_id})

@app.route('/api/einsaetze/<eid>/nachrichten', methods=['GET'])
def get_einsatz_nachrichten(eid):
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM einsatz_nachrichten WHERE einsatz_id=? ORDER BY created_at ASC", (eid,)
        ).fetchall()
    return jsonify([row_to_dict(r) for r in rows])

@app.route('/api/einsaetze/<eid>/nachrichten', methods=['POST'])
def send_einsatz_nachricht(eid):
    data   = request.get_json(silent=True) or {}
    text   = data.get('text','').strip()
    if not text:
        return jsonify({'error': 'empty'}), 400
    sender = data.get('sender','pfleger')
    mid    = 'msg_' + str(uuid.uuid4())[:8]
    with get_db() as db:
        db.execute(
            "INSERT INTO einsatz_nachrichten (id,einsatz_id,sender,text) VALUES (?,?,?,?)",
            (mid, eid, sender, text)
        )
    return jsonify({'ok': True, 'id': mid})


@app.route('/api/auftraege')
def get_auftraege():
    """Return all einsaetze assigned to the current vehicle session."""
    fahrzeug = session.get('fahrzeug', '')
    # Token-Fallback: falls Session abgelaufen, Token aus Header prüfen
    if not fahrzeug:
        tok = _token_from_request()
        if tok:
            with get_db() as db:
                vs = db.execute(
                    'SELECT fahrzeug FROM vehicle_sessions WHERE caregiver_id=?',
                    (tok['uid'],)
                ).fetchone()
            if vs and vs['fahrzeug']:
                fahrzeug = vs['fahrzeug']
                # Session neu setzen
                session['fahrzeug']  = fahrzeug
                session['user_id']   = tok['uid']
                session['user_role'] = tok['role']
    if not fahrzeug:
        return jsonify({'error': 'Nicht angemeldet', 'auftraege': []}), 200
    import datetime as _dt
    cutoff = (_dt.datetime.utcnow() - _dt.timedelta(hours=12)).strftime('%Y-%m-%d %H:%M:%S')
    with get_db() as db:
        rows = db.execute(
            """SELECT * FROM einsaetze
               WHERE fahrzeug=?
                 AND (status NOT IN ('beendet','storniert')
                      OR (status IN ('beendet','storniert')
                          AND COALESCE(archiviert_am, created_at) > ?))
               ORDER BY datum DESC, zeit DESC LIMIT 200""",
            (fahrzeug, cutoff)
        ).fetchall()
        if not rows:
            pass  # No demo seeding – return empty list
    result = []
    for row in rows:
        e = row_to_dict(row)
        e['risiken'] = json.loads(e.get('risiken') or '[]')
        e['extra']   = json.loads(e.get('extra')   or '{}')
        result.append(e)
    return jsonify({'ok': True, 'fahrzeug': fahrzeug, 'auftraege': result})


# ── Static files ────────────────────────────────────────────────────────────

# ══════════════════════════════════════════════════════════════════════════════
# BILLING / VERRECHNUNGSSTELLE API
# ══════════════════════════════════════════════════════════════════════════════

def _require_billing_admiral():
    """Only admiral/admin billing users may call this."""
    if session.get('admin'):
        return None
    bid = session.get('billing_user_id')
    if bid == 'admin':
        return None
    if bid:
        with get_db() as db:
            u = db.execute('SELECT rolle FROM billing_users WHERE id=?', [bid]).fetchone()
        if u and u['rolle'] in ('admiral', 'admin'):
            return None
    return jsonify({'ok': False, 'error': 'Nur Admiral darf das'}), 403


def require_billing():
    """Allow billing_users AND admin session."""
    if session.get('admin'):
        return None
    if session.get('billing_user_id'):
        return None
    tok = _token_from_request()
    if tok and tok.get('role') in ('billing', 'admin'):
        return None
    return jsonify({'error': 'Nicht angemeldet'}), 401


@app.route('/api/billing/login', methods=['POST'])
def billing_login():
    data  = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    pw    = data.get('password', '')
    # Allow admiral/admin password as bypass
    if pw == ADMIN_PASSWORD:
        session['billing_user_id'] = 'admin'
        return jsonify({'ok': True, 'user': {'id': 'admin', 'name': 'Admiral', 'rolle': 'admiral'}})
    with get_db() as db:
        row = db.execute(
            'SELECT * FROM billing_users WHERE email=? AND aktiv=1',
            [email]
        ).fetchone()
    if not row or not check_pw(row['password_hash'], pw):
        return jsonify({'error': 'E-Mail oder Passwort falsch'}), 401
    session['billing_user_id'] = row['id']
    return jsonify({'ok': True, 'user': {
        'id': row['id'], 'name': row['name'], 'email': row['email'], 'rolle': row['rolle']
    }})


@app.route('/api/admin/billing-zugang', methods=['GET', 'POST'])
def admin_billing_zugang():
    """Admin/Admiral: setzt Billing-Session und gibt {ok:True} zurück (POST via fetch mit X-Nursy-Token)."""
    err = require_admin()
    if err:
        if request.method == 'POST':
            return jsonify({'ok': False, 'error': 'Nicht autorisiert'}), 403
        return redirect('/billing-login.html')
    session['billing_user_id'] = 'admin'
    if request.method == 'POST':
        return jsonify({'ok': True})
    return redirect('/billing.html')


@app.route('/api/billing/logout', methods=['POST'])
def billing_logout():
    session.pop('billing_user_id', None)
    return jsonify({'ok': True})


@app.route('/api/billing/me')
def billing_me():
    bid = session.get('billing_user_id')
    if session.get('admin'):
        return jsonify({'ok': True, 'user': {'id': 'admin', 'name': 'Admiral', 'rolle': 'admiral'}})
    if not bid:
        return jsonify({'error': 'Nicht angemeldet'}), 401
    if bid == 'admin':
        return jsonify({'ok': True, 'user': {'id': 'admin', 'name': 'Admiral', 'rolle': 'admiral'}})
    with get_db() as db:
        row = db.execute('SELECT * FROM billing_users WHERE id=? AND aktiv=1', [bid]).fetchone()
    if not row:
        return jsonify({'error': 'Sitzung abgelaufen'}), 401
    import json as _jj
    return jsonify({'ok': True, 'user': {
        'id': row['id'], 'name': row['name'], 'email': row['email'], 'rolle': row['rolle'],
        'seiten_zugriff': _jj.loads(row['seiten_zugriff'] or '[]') if 'seiten_zugriff' in row.keys() else []
    }})


# ── Leistungskatalog ──────────────────────────────────────────────────────────

@app.route('/api/preisliste')
def public_preisliste():
    """Public endpoint — Leitstelle can read pricing without billing login."""
    with get_db() as db:
        rows = db.execute(
            'SELECT id,name,beschreibung,kategorie,preis,einheit,mwst_prozent,sort_order '
            'FROM leistungskatalog WHERE aktiv=1 ORDER BY sort_order, name'
        ).fetchall()
    return jsonify({'ok': True, 'leistungen': [dict(r) for r in rows],
                    'gueltig_ab': 'April 2026'})


@app.route('/api/billing/leistungskatalog')
def billing_leistungskatalog_list():
    err = require_billing()
    if err: return err
    with get_db() as db:
        rows = db.execute('SELECT * FROM leistungskatalog ORDER BY sort_order, name').fetchall()
    return jsonify({'ok': True, 'leistungen': [dict(r) for r in rows]})


@app.route('/api/billing/leistungskatalog', methods=['POST'])
def billing_leistungskatalog_create():
    err = require_billing()
    if err: return err
    data = request.get_json(silent=True) or {}
    lid  = 'lk_' + uuid.uuid4().hex[:8]
    with get_db() as db:
        max_sort = db.execute('SELECT COALESCE(MAX(sort_order),0)+1 FROM leistungskatalog').fetchone()[0]
        db.execute(
            'INSERT INTO leistungskatalog (id,name,beschreibung,kategorie,preis,einheit,mwst_prozent,aktiv,sort_order) '
            'VALUES (?,?,?,?,?,?,?,?,?)',
            [lid, data.get('name','Neue Leistung'), data.get('beschreibung',''),
             data.get('kategorie','Allgemein'), float(data.get('preis',0)),
             data.get('einheit','Einsatz'), float(data.get('mwst_prozent',0)),
             1, max_sort]
        )
        db.commit()
    return jsonify({'ok': True, 'id': lid})


@app.route('/api/billing/leistungskatalog/<lid>', methods=['PUT'])
def billing_leistungskatalog_update(lid):
    err = require_billing()
    if err: return err
    data = request.get_json(silent=True) or {}
    with get_db() as db:
        db.execute(
            'UPDATE leistungskatalog SET name=?,beschreibung=?,kategorie=?,preis=?,einheit=?,mwst_prozent=?,aktiv=? WHERE id=?',
            [data.get('name',''), data.get('beschreibung',''), data.get('kategorie','Allgemein'),
             float(data.get('preis',0)), data.get('einheit','Einsatz'),
             float(data.get('mwst_prozent',0)), int(data.get('aktiv',1)), lid]
        )
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/billing/leistungskatalog/<lid>', methods=['DELETE'])
def billing_leistungskatalog_delete(lid):
    err = require_billing()
    if err: return err
    with get_db() as db:
        db.execute('DELETE FROM leistungskatalog WHERE id=?', [lid])
        db.commit()
    return jsonify({'ok': True})


# ── Rechnungen ────────────────────────────────────────────────────────────────

def _billing_uid():
    """Return billing_user_id for non-admin sessions, None for admin/admiral (sees all)."""
    if session.get('admin'):
        return None
    bid = session.get('billing_user_id')
    if not bid or bid == 'admin':
        return None
    return bid


def _next_re_nummer(db, prefix):
    year  = __import__('datetime').date.today().year
    like  = f'{prefix}-{year}-%'
    last  = db.execute("SELECT nummer FROM rechnungen WHERE nummer LIKE ? ORDER BY nummer DESC LIMIT 1", [like]).fetchone()
    if last:
        try:
            n = int(last['nummer'].split('-')[-1]) + 1
        except Exception:
            n = 1
    else:
        n = 1
    return f'{prefix}-{year}-{n:04d}'


@app.route('/api/billing/rechnungen')
def billing_rechnungen_list():
    err = require_billing()
    if err: return err
    typ = request.args.get('typ', '')
    uid = _billing_uid()
    with get_db() as db:
        if uid:
            if typ:
                rows = db.execute('SELECT * FROM rechnungen WHERE billing_user_id=? AND typ=? ORDER BY created_at DESC', [uid, typ]).fetchall()
            else:
                rows = db.execute('SELECT * FROM rechnungen WHERE billing_user_id=? ORDER BY created_at DESC', [uid]).fetchall()
        else:
            if typ:
                rows = db.execute('SELECT * FROM rechnungen WHERE typ=? ORDER BY created_at DESC', [typ]).fetchall()
            else:
                rows = db.execute('SELECT * FROM rechnungen ORDER BY created_at DESC').fetchall()
    return jsonify({'ok': True, 'rechnungen': [dict(r) for r in rows]})


@app.route('/api/billing/rechnungen/<rid>')
def billing_rechnung_get(rid):
    err = require_billing()
    if err: return err
    uid = _billing_uid()
    with get_db() as db:
        row = db.execute('SELECT * FROM rechnungen WHERE id=?', [rid]).fetchone()
    if not row:
        return jsonify({'error': 'Nicht gefunden'}), 404
    if uid and row['billing_user_id'] and row['billing_user_id'] != uid:
        return jsonify({'error': 'Kein Zugriff'}), 403
    return jsonify({'ok': True, 'rechnung': dict(row)})


@app.route('/api/billing/rechnungen', methods=['POST'])
def billing_rechnungen_create():
    err = require_billing()
    if err: return err
    data   = request.get_json(silent=True) or {}
    rid    = 're_' + uuid.uuid4().hex[:10]
    typ    = data.get('typ', 'notdienst')
    layout = data.get('layout', 'akutplus')
    prefix = 'AP' if layout == 'akutplus' else 'NU'
    user_name = ''
    bid = session.get('billing_user_id', 'system')
    if bid and bid != 'admin':
        with get_db() as db:
            bu = db.execute('SELECT name FROM billing_users WHERE id=?', [bid]).fetchone()
            user_name = bu['name'] if bu else ''
    else:
        user_name = 'Admiral'

    positionen = data.get('positionen', [])
    netto   = sum(float(p.get('menge',1)) * float(p.get('preis',0)) for p in positionen)
    mwst_total = sum(float(p.get('menge',1)) * float(p.get('preis',0)) * float(p.get('mwst_prozent',0)) / 100 for p in positionen)
    brutto  = netto + mwst_total

    uid = _billing_uid()
    with get_db() as db:
        nummer = _next_re_nummer(db, prefix)
        db.execute(
            'INSERT INTO rechnungen (id,nummer,typ,layout,empfaenger_name,empfaenger_adresse,empfaenger_plz,'
            'empfaenger_ort,empfaenger_email,einsatz_id,positionen,netto,mwst,brutto,status,faellig_am,notiz,freitext,erstellt_von,billing_user_id) '
            'VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
            [rid, nummer, typ, layout,
             data.get('empfaenger_name',''), data.get('empfaenger_adresse',''),
             data.get('empfaenger_plz',''), data.get('empfaenger_ort',''),
             data.get('empfaenger_email',''), data.get('einsatz_id',''),
             __import__('json').dumps(positionen, ensure_ascii=False),
             round(netto,2), round(mwst_total,2), round(brutto,2),
             data.get('status','entwurf'), data.get('faellig_am',''),
             data.get('notiz',''), data.get('freitext',''), user_name,
             uid or bid]
        )
        db.commit()
    return jsonify({'ok': True, 'id': rid, 'nummer': nummer})


@app.route('/api/billing/rechnungen/<rid>', methods=['PUT'])
def billing_rechnungen_update(rid):
    err = require_billing()
    if err: return err
    uid = _billing_uid()
    data = request.get_json(silent=True) or {}
    import json as _json
    with get_db() as db:
        row = db.execute('SELECT billing_user_id FROM rechnungen WHERE id=?', [rid]).fetchone()
        if not row:
            return jsonify({'error': 'Nicht gefunden'}), 404
        if uid and row['billing_user_id'] and row['billing_user_id'] != uid:
            return jsonify({'error': 'Kein Zugriff'}), 403
        positionen = data.get('positionen', [])
        netto      = sum(float(p.get('menge',1)) * float(p.get('preis',0)) for p in positionen)
        mwst_total = sum(float(p.get('menge',1)) * float(p.get('preis',0)) * float(p.get('mwst_prozent',0)) / 100 for p in positionen)
        brutto     = netto + mwst_total
        db.execute(
            'UPDATE rechnungen SET empfaenger_name=?,empfaenger_adresse=?,empfaenger_plz=?,empfaenger_ort=?,'
            'empfaenger_email=?,positionen=?,netto=?,mwst=?,brutto=?,status=?,faellig_am=?,notiz=?,freitext=? WHERE id=?',
            [data.get('empfaenger_name',''), data.get('empfaenger_adresse',''),
             data.get('empfaenger_plz',''), data.get('empfaenger_ort',''),
             data.get('empfaenger_email',''), _json.dumps(positionen, ensure_ascii=False),
             round(netto,2), round(mwst_total,2), round(brutto,2),
             data.get('status','entwurf'), data.get('faellig_am',''), data.get('notiz',''),
             data.get('freitext',''), rid]
        )
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/billing/rechnungen/<rid>/status', methods=['POST'])
def billing_rechnung_status(rid):
    err = require_billing()
    if err: return err
    uid = _billing_uid()
    data   = request.get_json(silent=True) or {}
    status = data.get('status', '')
    if status not in ('entwurf','gesendet','bezahlt','storniert'):
        return jsonify({'error': 'Ungültiger Status'}), 400
    with get_db() as db:
        row = db.execute('SELECT billing_user_id FROM rechnungen WHERE id=?', [rid]).fetchone()
        if not row:
            return jsonify({'error': 'Nicht gefunden'}), 404
        if uid and row['billing_user_id'] and row['billing_user_id'] != uid:
            return jsonify({'error': 'Kein Zugriff'}), 403
        db.execute('UPDATE rechnungen SET status=? WHERE id=?', [status, rid])
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/billing/rechnungen/<rid>', methods=['DELETE'])
def billing_rechnungen_delete(rid):
    err = require_billing()
    if err: return err
    uid = _billing_uid()
    with get_db() as db:
        row = db.execute('SELECT billing_user_id FROM rechnungen WHERE id=?', [rid]).fetchone()
        if not row:
            return jsonify({'error': 'Nicht gefunden'}), 404
        if uid and row['billing_user_id'] and row['billing_user_id'] != uid:
            return jsonify({'error': 'Kein Zugriff'}), 403
        db.execute('DELETE FROM rechnungen WHERE id=?', [rid])
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/billing/einsaetze-abgeschlossen')
def billing_einsaetze():
    """Return completed Einsätze for invoice generation, including patient address data."""
    err = require_billing()
    if err: return err
    with get_db() as db:
        rows = db.execute(
            "SELECT e.*, COALESCE(r.nummer,'') as rechnung_nummer, "
            "COALESCE(p.address,'') as pat_adresse, "
            "COALESCE(p.plz,'') as pat_plz, "
            "COALESCE(p.ort,'') as pat_ort, "
            "COALESCE(p.email,'') as pat_email "
            "FROM einsaetze e "
            "LEFT JOIN rechnungen r ON r.einsatz_id=e.id "
            "LEFT JOIN patients p ON p.id=e.patient_id "
            "WHERE e.status IN ('beendet') ORDER BY e.datum DESC, e.zeit DESC LIMIT 100"
        ).fetchall()
    return jsonify({'ok': True, 'einsaetze': [dict(r) for r in rows]})


def _map_rechnung_to_js(r):
    import json as _j
    try:
        pos = _j.loads(r['positionen'] or '[]')
    except Exception:
        pos = []
    lines = []
    for p in pos:
        bez    = p.get('bezeichnung') or p.get('name') or ''
        menge  = float(p.get('menge', 1))
        preis  = float(p.get('preis', 0))
        einheit = p.get('einheit', 'Einheit')
        lines.append({
            'label':  bez,
            'qty':    str(int(menge)) + '\u00a0' + einheit,
            'amount': round(menge * preis, 2)
        })
    status_map = {'bezahlt': 'paid', 'storniert': 'overdue'}
    js_status  = status_map.get(r['status'], 'open')
    created    = (r['created_at'] or '')[:10]
    return {
        'id':          r['nummer'],
        'patient':     r['empfaenger_name'],
        'period':      created,
        'invoiceDate': created,
        'dueDate':     r['faellig_am'] or '',
        'amount':      float(r['brutto']),
        'status':      js_status,
        'lines':       lines,
        '_server':     True
    }


@app.route('/api/my/rechnungen')
def my_rechnungen():
    """Return Nursy invoices for the currently logged-in care worker."""
    uid  = session.get('user_id')
    role = session.get('user_role')
    if not uid or role != 'care':
        return jsonify({'ok': True, 'rechnungen': []})
    with get_db() as db:
        row = db.execute('SELECT email FROM caregivers WHERE id=?', [uid]).fetchone()
    email = row['email'] if row else None
    if not email:
        return jsonify({'ok': True, 'rechnungen': []})
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM rechnungen WHERE layout='nursy' AND lower(empfaenger_email)=? ORDER BY created_at DESC",
            [email.lower()]
        ).fetchall()
    return jsonify({'ok': True, 'rechnungen': [_map_rechnung_to_js(r) for r in rows]})


@app.route('/api/nursy/rechnungen-by-email')
def nursy_rechnungen_by_email():
    """Return Nursy invoices for a given e-mail address (patient / client view)."""
    email = request.args.get('email', '').strip().lower()
    if not email:
        return jsonify({'ok': True, 'rechnungen': []})
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM rechnungen WHERE layout='nursy' AND lower(empfaenger_email)=? ORDER BY created_at DESC",
            [email]
        ).fetchall()
    return jsonify({'ok': True, 'rechnungen': [_map_rechnung_to_js(r) for r in rows]})


@app.route('/api/billing/stats')
def billing_stats():
    err = require_billing()
    if err: return err
    with get_db() as db:
        total_ap  = db.execute("SELECT COUNT(*) FROM rechnungen WHERE layout='akutplus'").fetchone()[0]
        total_nu  = db.execute("SELECT COUNT(*) FROM rechnungen WHERE layout='nursy'").fetchone()[0]
        offen_ap  = db.execute("SELECT COALESCE(SUM(brutto),0) FROM rechnungen WHERE layout='akutplus' AND status='gesendet'").fetchone()[0]
        offen_nu  = db.execute("SELECT COALESCE(SUM(brutto),0) FROM rechnungen WHERE layout='nursy' AND status='gesendet'").fetchone()[0]
        bezahlt   = db.execute("SELECT COALESCE(SUM(brutto),0) FROM rechnungen WHERE status='bezahlt'").fetchone()[0]
        entwuerfe = db.execute("SELECT COUNT(*) FROM rechnungen WHERE status='entwurf'").fetchone()[0]
        lk_count  = db.execute("SELECT COUNT(*) FROM leistungskatalog WHERE aktiv=1").fetchone()[0]
    return jsonify({'ok': True, 'stats': {
        'total_ap': total_ap, 'total_nu': total_nu,
        'offen_ap': round(offen_ap,2), 'offen_nu': round(offen_nu,2),
        'bezahlt': round(bezahlt,2), 'entwuerfe': entwuerfe,
        'lk_count': lk_count
    }})


# ── Startseite Content Blocks ────────────────────────────────────────────────

@app.route('/api/startseite/blocks')
def public_startseite_blocks():
    with get_db() as db:
        rows = db.execute(
            'SELECT id, titel, inhalt, bild_url, link_text, link_url, typ FROM startseite_blocks WHERE aktiv=1 ORDER BY reihenfolge ASC, created_at ASC'
        ).fetchall()
    return jsonify({'ok': True, 'blocks': [dict(r) for r in rows]})

@app.route('/api/admin/startseite-blocks')
def admin_list_startseite_blocks():
    err = require_admin()
    if err: return err
    with get_db() as db:
        rows = db.execute('SELECT * FROM startseite_blocks ORDER BY reihenfolge ASC, created_at ASC').fetchall()
    return jsonify({'ok': True, 'blocks': [dict(r) for r in rows]})

@app.route('/api/admin/startseite-blocks', methods=['POST'])
def admin_create_startseite_block():
    err = require_admin()
    if err: return err
    data = request.get_json(silent=True) or {}
    bid = 'sb' + uuid.uuid4().hex[:8]
    with get_db() as db:
        db.execute(
            'INSERT INTO startseite_blocks (id, titel, inhalt, bild_url, link_text, link_url, typ, aktiv, reihenfolge) VALUES (?,?,?,?,?,?,?,?,?)',
            [bid, data.get('titel',''), data.get('inhalt',''), data.get('bild_url',''),
             data.get('link_text',''), data.get('link_url',''),
             data.get('typ','info'), 1 if data.get('aktiv', True) else 0,
             int(data.get('reihenfolge', 0))]
        )
        db.commit()
    return jsonify({'ok': True, 'id': bid})

@app.route('/api/admin/startseite-blocks/<bid>', methods=['PUT'])
def admin_update_startseite_block(bid):
    err = require_admin()
    if err: return err
    data = request.get_json(silent=True) or {}
    with get_db() as db:
        db.execute(
            'UPDATE startseite_blocks SET titel=?, inhalt=?, bild_url=?, link_text=?, link_url=?, typ=?, aktiv=?, reihenfolge=? WHERE id=?',
            [data.get('titel',''), data.get('inhalt',''), data.get('bild_url',''),
             data.get('link_text',''), data.get('link_url',''),
             data.get('typ','info'), 1 if data.get('aktiv', True) else 0,
             int(data.get('reihenfolge', 0)), bid]
        )
        db.commit()
    return jsonify({'ok': True})

@app.route('/api/admin/startseite-blocks/<bid>', methods=['DELETE'])
def admin_delete_startseite_block(bid):
    err = require_admin()
    if err: return err
    with get_db() as db:
        db.execute('DELETE FROM startseite_blocks WHERE id=?', [bid])
        db.commit()
    return jsonify({'ok': True})

@app.route('/api/admin/startseite-blocks/<bid>/toggle', methods=['POST'])
def admin_toggle_startseite_block(bid):
    err = require_admin()
    if err: return err
    with get_db() as db:
        db.execute('UPDATE startseite_blocks SET aktiv = 1 - aktiv WHERE id=?', [bid])
        db.commit()
        row = db.execute('SELECT aktiv FROM startseite_blocks WHERE id=?', [bid]).fetchone()
    return jsonify({'ok': True, 'aktiv': row['aktiv'] if row else 0})


@app.route('/')
def index():
    resp = send_from_directory(BASE_DIR, 'index.html')
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@app.route('/portal/')
@app.route('/portal')
def pwa_portal_login():
    resp = send_from_directory(BASE_DIR, 'pflege-portal-login.html')
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@app.route('/portal/app')
def pwa_portal_app():
    resp = send_from_directory(BASE_DIR, 'pflege-portal.html')
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@app.route('/portal/admin')
def pwa_portal_admin():
    resp = send_from_directory(BASE_DIR, 'pflege-portal-admin.html')
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@app.route('/portal/sw.js')
def pwa_portal_sw():
    resp = send_from_directory(BASE_DIR, 'sw.js')
    resp.headers['Content-Type'] = 'application/javascript'
    resp.headers['Service-Worker-Allowed'] = '/portal/'
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return resp

# ── Auftragslage PWA routes (own scope /auftragslage/) ────────────────────────
@app.route('/auftragslage/')
@app.route('/auftragslage')
def pwa_auftragslage():
    resp = send_from_directory(BASE_DIR, 'auftragslage.html')
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@app.route('/auftragslage/login')
def pwa_auftragslage_login():
    resp = send_from_directory(BASE_DIR, 'login-fahrzeug.html')
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

@app.route('/auftragslage/sw.js')
def pwa_auftragslage_sw():
    resp = send_from_directory(BASE_DIR, 'sw-auftragslage.js')
    resp.headers['Content-Type'] = 'application/javascript'
    resp.headers['Service-Worker-Allowed'] = '/auftragslage/'
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return resp

@app.route('/leitstelle/sw.js')
def pwa_leitstelle_sw():
    resp = send_from_directory(BASE_DIR, 'leitstelle-sw.js')
    resp.headers['Content-Type'] = 'application/javascript'
    resp.headers['Service-Worker-Allowed'] = '/'
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return resp

# ══════════════════════════════════════════════════════════════════════════════
# ── Pflege-Portal ─────────────────────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

def _get_portal_user():
    uid = session.get('portal_user_id')
    if not uid:
        return None
    with get_db() as db:
        row = db.execute("SELECT * FROM portal_bewerbungen WHERE id=? AND status='freigegeben'", [uid]).fetchone()
        if row:
            import json as _j2
            da_raw = row['dienst_arten'] or '[]'
            try:
                da_list = _j2.loads(da_raw)
            except Exception:
                da_list = []
            return {
                'id': row['id'],
                'name': row['vorname'] + ' ' + row['nachname'],
                'vorname': row['vorname'], 'nachname': row['nachname'],
                'email': row['email'],
                'telefon': row['telefon'] or '',
                'adresse': row['adresse'] or '',
                'bezirk': row['bezirk'] or '',
                'qualifikation': row['qualifikation'] or '',
                'erfahrung_jahre': row['erfahrung_jahre'] or 0,
                'fahrzeug_pref': row['fahrzeug_pref'] or '',
                'dienst_arten': da_list,
                'dienstnummer': row.get('dienstnummer', '') or '',
            }
        row = db.execute('SELECT * FROM caregivers WHERE id=?', [uid]).fetchone()
        if row:
            return {
                'id': row['id'],
                'name': row['vorname'] + ' ' + row['nachname'],
                'vorname': row['vorname'], 'nachname': row['nachname'],
                'email': row['email'],
                'telefon': '', 'adresse': '',
                'bezirk': '', 'qualifikation': '', 'erfahrung_jahre': 0,
                'fahrzeug_pref': '', 'dienst_arten': [],
                'dienstnummer': row.get('dienstnummer', '') or '',
            }
    return None

def _require_admin_or_admiral():
    if session.get('admin'):
        return True
    if session.get('leitstelle_role') in ('admiral', 'disponent'):
        return True
    tok = _token_from_request()
    if tok and tok['role'] in ('admin', 'admiral', 'disponent'):
        return True
    return False

@app.route('/api/portal/login', methods=['POST'])
def portal_login():
    data = request.get_json(silent=True) or {}
    email = data.get('email','').strip().lower()
    pw    = data.get('password','')
    if not email or not pw:
        return jsonify({'ok': False, 'error': 'E-Mail und Passwort erforderlich'}), 400
    with get_db() as db:
        row = db.execute("SELECT * FROM portal_bewerbungen WHERE LOWER(email)=? AND status='freigegeben'", [email]).fetchone()
        if row and row['password_hash'] and check_pw(row['password_hash'], pw):
            session['portal_user_id']   = row['id']
            session['portal_user_name'] = row['vorname'] + ' ' + row['nachname']
            return jsonify({'ok': True, 'name': session['portal_user_name']})
        row = db.execute('SELECT * FROM caregivers WHERE LOWER(email)=?', [email]).fetchone()
        if row and check_pw(row['password_hash'], pw):
            session['portal_user_id']   = row['id']
            session['portal_user_name'] = row['vorname'] + ' ' + row['nachname']
            return jsonify({'ok': True, 'name': session['portal_user_name']})
    return jsonify({'ok': False, 'error': 'E-Mail oder Passwort falsch'}), 401

@app.route('/api/portal/logout', methods=['POST'])
def portal_logout():
    session.pop('portal_user_id', None)
    session.pop('portal_user_name', None)
    return jsonify({'ok': True})

@app.route('/api/portal/me')
def portal_me():
    u = _get_portal_user()
    if not u:
        return jsonify({'ok': False}), 401
    return jsonify({'ok': True, **u})

def _next_ap_dienstnummer(db):
    """Generates next sequential AP-XXX Dienstnummer from caregivers (canonical source)."""
    try:
        rows = db.execute("SELECT dienstnummer FROM caregivers WHERE dienstnummer LIKE 'AP-%'").fetchall()
    except Exception:
        rows = []
    nums = []
    for r in rows:
        dnr = (r.get('dienstnummer') or '').strip().upper()
        if dnr.startswith('AP-'):
            try:
                nums.append(int(dnr[3:]))
            except ValueError:
                pass
    # also scan portal_bewerbungen as fallback so we never reuse a number
    try:
        rows2 = db.execute("SELECT dienstnummer FROM portal_bewerbungen WHERE dienstnummer LIKE 'AP-%'").fetchall()
        for r in rows2:
            dnr = (r.get('dienstnummer') or '').strip().upper()
            if dnr.startswith('AP-'):
                try:
                    nums.append(int(dnr[3:]))
                except ValueError:
                    pass
    except Exception:
        pass
    return f"AP-{(max(nums) + 1) if nums else 1:03d}"


def _ensure_caregiver_from_portal(pb_id, db):
    """Ensures a portal applicant (id=pb_id) has a caregivers entry + Dienstnummer.
    Creates caregivers row if needed. Returns the (cg_id, dienstnummer) tuple."""
    pb = db.execute('SELECT * FROM portal_bewerbungen WHERE id=?', [pb_id]).fetchone()
    if not pb:
        return ('', '')

    existing_dnr = (pb.get('dienstnummer') or '').strip()
    existing_cid = (pb.get('caregiver_id') or '').strip()

    # If both are set, verify caregivers entry actually exists
    if existing_dnr and existing_cid:
        cg_check = db.execute('SELECT id FROM caregivers WHERE id=?', [existing_cid]).fetchone()
        if cg_check:
            return (existing_cid, existing_dnr)
        # caregiver_id in pb points to deleted/nonexistent entry — fall through to recreate

    # Try to find caregivers entry by email
    existing_cg = db.execute(
        'SELECT id, dienstnummer FROM caregivers WHERE LOWER(email)=?',
        [pb['email'].lower()]
    ).fetchone()
    if existing_cg:
        cg_id = existing_cg['id']
        dnr = (existing_cg['dienstnummer'] or '').strip()
        if not dnr:
            dnr = _next_ap_dienstnummer(db)
            db.execute('UPDATE caregivers SET dienstnummer=? WHERE id=?', [dnr, cg_id])
        db.execute(
            'UPDATE portal_bewerbungen SET dienstnummer=?, caregiver_id=? WHERE id=?',
            [dnr, cg_id, pb_id]
        )
        db.commit()
        return (cg_id, dnr)

    # Create new caregivers entry
    cid = 'cg_' + uuid.uuid4().hex[:8]
    dnr = existing_dnr if existing_dnr else _next_ap_dienstnummer(db)
    db.execute(
        '''INSERT INTO caregivers
           (id, vorname, nachname, email, password_hash, gender, address, bezirk, qualifikation, dienstnummer)
           VALUES (?,?,?,?,?,?,?,?,?,?)''',
        [cid, pb['vorname'], pb['nachname'], pb['email'],
         pb.get('password_hash', ''), '',
         pb.get('adresse', ''), pb.get('bezirk', ''),
         pb.get('qualifikation', ''), dnr]
    )
    db.execute(
        'UPDATE portal_bewerbungen SET dienstnummer=?, caregiver_id=? WHERE id=?',
        [dnr, cid, pb_id]
    )
    db.commit()
    return (cid, dnr)


@app.route('/api/portal/registrieren', methods=['POST'])
def portal_registrieren():
    data  = request.get_json(silent=True) or {}
    rolle = data.get('rolle', 'pfleger').strip().lower()
    if rolle not in ('pfleger', 'klient'):
        rolle = 'pfleger'
    required = ['vorname', 'nachname', 'email', 'password']
    if rolle == 'pfleger':
        required += ['bezirk', 'qualifikation']
    for f in required:
        if not data.get(f, '').strip():
            return jsonify({'ok': False, 'error': f'Feld "{f}" fehlt'}), 400
    bid   = 'pb_' + uuid.uuid4().hex[:8]
    token = uuid.uuid4().hex
    with get_db() as db:
        db.execute_safe("ALTER TABLE portal_bewerbungen ADD COLUMN rolle TEXT DEFAULT 'pfleger'")
        ex = db.execute('SELECT id FROM portal_bewerbungen WHERE LOWER(email)=?', [data['email'].lower()]).fetchone()
        if ex:
            return jsonify({'ok': False, 'error': 'E-Mail bereits registriert'}), 409
        db.execute(
            '''INSERT INTO portal_bewerbungen
               (id,vorname,nachname,email,telefon,password_hash,qualifikation,erfahrung_jahre,
                bezirk,fahrzeug_pref,dienst_arten,adresse,status,token,rolle)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            [bid, data['vorname'].strip(), data['nachname'].strip(),
             data['email'].strip().lower(), data.get('telefon', ''),
             hash_pw(data['password']), data.get('qualifikation', ''),
             int(data.get('erfahrung_jahre', 0)),
             data.get('bezirk', ''), data.get('fahrzeug_pref', ''),
             json.dumps(data.get('dienst_arten', [])),
             data.get('adresse', ''), 'freigegeben', token, rolle]
        )
        db.commit()
        if rolle == 'pfleger':
            _, dnr = _ensure_caregiver_from_portal(bid, db)
        else:
            dnr = ''
    # auto-login after registration
    session['portal_user_id']   = bid
    session['portal_user_name'] = data['vorname'].strip() + ' ' + data['nachname'].strip()
    return jsonify({'ok': True, 'id': bid, 'token': token, 'rolle': rolle,
                    'dienstnummer': dnr,
                    'link': f'/pflege-portal-bewerbung.html?token={token}'})

@app.route('/api/portal/bewerbung/<token>')
def portal_bewerbung_get(token):
    with get_db() as db:
        row = db.execute('SELECT id,vorname,nachname,email,qualifikation,bezirk,status FROM portal_bewerbungen WHERE token=?', [token]).fetchone()
        if not row:
            return jsonify({'ok': False, 'error': 'Ungültiger Link'}), 404
        return jsonify({'ok': True, 'bewerbung': dict(row)})

@app.route('/api/portal/bewerbung/<token>', methods=['POST'])
def portal_bewerbung_submit(token):
    data = request.get_json(silent=True) or {}
    with get_db() as db:
        row = db.execute('SELECT id FROM portal_bewerbungen WHERE token=?', [token]).fetchone()
        if not row:
            return jsonify({'ok': False, 'error': 'Ungültiger Link'}), 404
        db.execute("UPDATE portal_bewerbungen SET notizen=?, status='gespräch' WHERE token=?",
                   [data.get('notizen',''), token])
        db.commit()
    return jsonify({'ok': True})

@app.route('/api/portal/dienste')
def portal_dienste_get():
    if not _get_portal_user():
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    monat = request.args.get('monat','')
    with get_db() as db:
        if monat:
            rows = db.execute('SELECT * FROM portal_dienste WHERE datum LIKE ? ORDER BY datum', [f'{monat}%']).fetchall()
        else:
            rows = db.execute('SELECT * FROM portal_dienste ORDER BY datum DESC LIMIT 300').fetchall()
    return jsonify({'ok': True, 'dienste': [dict(r) for r in rows]})

@app.route('/api/portal/dienste', methods=['POST'])
def portal_dienst_create():
    u = _get_portal_user()
    if not u:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    data = request.get_json(silent=True) or {}
    for f in ['datum','art']:
        if not data.get(f,'').strip():
            return jsonify({'ok': False, 'error': f'Feld "{f}" fehlt'}), 400
    ART_ZEITEN = {
        'Tagdienst':   ('06:00','20:00'),
        'Nachtdienst': ('20:00','06:00'),
        'Frühdienst':  ('06:00','14:00'),
        'Spätdienst':  ('14:00','22:00'),
    }
    von, bis = ART_ZEITEN.get(data['art'],('',''))
    did = 'pd_' + uuid.uuid4().hex[:8]
    with get_db() as db:
        ex = db.execute(
            "SELECT id FROM portal_dienste WHERE user_id=? AND datum=? AND art=? AND status!='storniert'",
            [u['id'], data['datum'], data['art']]
        ).fetchone()
        if ex:
            return jsonify({'ok': False, 'error': 'Bereits für diesen Dienst eingetragen'}), 409
        db.execute(
            'INSERT INTO portal_dienste (id,user_id,user_name,datum,art,von,bis,fahrzeug,bezirk,notiz) VALUES (?,?,?,?,?,?,?,?,?,?)',
            [did, u['id'], u['name'], data['datum'], data['art'],
             data.get('von',von), data.get('bis',bis),
             data.get('fahrzeug',''), data['bezirk'], data.get('notiz','')]
        )
        db.commit()
    return jsonify({'ok': True, 'id': did})

@app.route('/api/portal/dienste/<did>', methods=['DELETE'])
def portal_dienst_delete(did):
    u = _get_portal_user()
    if not u:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    with get_db() as db:
        row = db.execute('SELECT * FROM portal_dienste WHERE id=?', [did]).fetchone()
        if not row:
            return jsonify({'ok': False, 'error': 'Nicht gefunden'}), 404
        if row['user_id'] != u['id'] and not _require_admin_or_admiral():
            return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
        db.execute('DELETE FROM portal_dienste WHERE id=?', [did])
        db.commit()
    return jsonify({'ok': True})

@app.route('/api/portal/events')
def portal_events_get():
    u = _get_portal_user()
    if not u:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    with get_db() as db:
        events = db.execute('SELECT * FROM portal_events WHERE aktiv=1 ORDER BY datum').fetchall()
        result = []
        for ev in events:
            cnt = db.execute('SELECT COUNT(*) as c FROM portal_event_anmeldungen WHERE event_id=?', [ev['id']]).fetchone()['c']
            my  = db.execute('SELECT id FROM portal_event_anmeldungen WHERE event_id=? AND user_id=?', [ev['id'], u['id']]).fetchone()
            d = dict(ev); d['angemeldet_count'] = cnt; d['ich_angemeldet'] = bool(my)
            result.append(d)
    return jsonify({'ok': True, 'events': result})

@app.route('/api/portal/events/<eid>/anmelden', methods=['POST'])
def portal_event_anmelden(eid):
    u = _get_portal_user()
    if not u:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    with get_db() as db:
        ev = db.execute('SELECT * FROM portal_events WHERE id=? AND aktiv=1', [eid]).fetchone()
        if not ev:
            return jsonify({'ok': False, 'error': 'Event nicht gefunden'}), 404
        cnt = db.execute('SELECT COUNT(*) as c FROM portal_event_anmeldungen WHERE event_id=?', [eid]).fetchone()['c']
        if ev['slots'] > 0 and cnt >= ev['slots']:
            return jsonify({'ok': False, 'error': 'Keine freien Plätze mehr'}), 409
        try:
            db.execute('INSERT INTO portal_event_anmeldungen (id,event_id,user_id,user_name) VALUES (?,?,?,?)',
                       ['ea_'+uuid.uuid4().hex[:8], eid, u['id'], u['name']])
            db.commit()
        except Exception:
            return jsonify({'ok': False, 'error': 'Bereits angemeldet'}), 409
    return jsonify({'ok': True})

@app.route('/api/portal/events/<eid>/anmelden', methods=['DELETE'])
def portal_event_abmelden(eid):
    u = _get_portal_user()
    if not u:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    with get_db() as db:
        db.execute('DELETE FROM portal_event_anmeldungen WHERE event_id=? AND user_id=?', [eid, u['id']])
        db.commit()
    return jsonify({'ok': True})

@app.route('/api/portal/info')
def portal_info_get():
    if not _get_portal_user():
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    with get_db() as db:
        rows = db.execute('SELECT * FROM portal_info WHERE aktiv=1 ORDER BY created_at DESC').fetchall()
    return jsonify({'ok': True, 'info': [dict(r) for r in rows]})

# ── Admin: Portal-Verwaltung ─────────────────────────────────────────────────

@app.route('/api/admin/portal/stats')
def admin_portal_stats():
    if not _require_admin_or_admiral():
        return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
    with get_db() as db:
        offen      = db.execute("SELECT COUNT(*) as c FROM portal_bewerbungen WHERE status='ausstehend'").fetchone()['c']
        freigeg    = db.execute("SELECT COUNT(*) as c FROM portal_bewerbungen WHERE status='freigegeben'").fetchone()['c']
        dienste    = db.execute('SELECT COUNT(*) as c FROM portal_dienste WHERE datum >= CURRENT_DATE::text').fetchone()['c'] if USE_PG else db.execute('SELECT COUNT(*) as c FROM portal_dienste WHERE datum >= date("now")').fetchone()['c']
        events     = db.execute('SELECT COUNT(*) as c FROM portal_events WHERE aktiv=1').fetchone()['c']
    return jsonify({'ok': True, 'offen': offen, 'freigegeben': freigeg, 'dienste': dienste, 'events': events})

@app.route('/api/admin/portal/fahrzeuge')
def admin_portal_fahrzeuge():
    if not _require_admin_or_admiral():
        return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
    with get_db() as db:
        rows = db.execute('SELECT * FROM fahrzeuge WHERE aktiv=1 ORDER BY name').fetchall()
    return jsonify({'ok': True, 'fahrzeuge': [dict(r) for r in rows]})

# ── Portal Admin Backup ───────────────────────────────────────────────────────
@app.route('/api/admin/portal/backup')
def admin_portal_backup():
    if not _require_admin_or_admiral():
        return jsonify({'error': 'Kein Zugriff'}), 403
    import json as _j, datetime as _dt
    with get_db() as db:
        def rows(sql, params=[]):
            return [dict(r) for r in db.execute(sql, params).fetchall()]
        data = {
            'exported_at': _dt.datetime.now().isoformat(),
            'bereich': 'Pflege-Portal',
            'bewerbungen': rows(
                "SELECT id,vorname,nachname,email,telefon,bezirk,fahrzeug,"
                "status,erstellt_am,token FROM portal_bewerbungen ORDER BY id DESC"),
            'dienste': rows(
                "SELECT pd.*,pb.vorname||' '||pb.nachname as name "
                "FROM portal_dienste pd "
                "LEFT JOIN portal_bewerbungen pb ON pb.id=pd.user_id "
                "ORDER BY pd.datum DESC LIMIT 2000"),
            'events': rows(
                "SELECT * FROM portal_events ORDER BY datum DESC"),
            'event_anmeldungen': rows(
                "SELECT ea.*,pb.vorname||' '||pb.nachname as name "
                "FROM portal_event_anmeldungen ea "
                "LEFT JOIN portal_bewerbungen pb ON pb.id=ea.user_id "
                "ORDER BY ea.id DESC"),
            'info': rows("SELECT * FROM portal_info ORDER BY erstellt_am DESC"),
        }
    resp = make_response(_j.dumps(data, ensure_ascii=False, indent=2, default=str))
    fname = 'nursy_backup_portal_' + _dt.date.today().isoformat() + '.json'
    resp.headers['Content-Type'] = 'application/json; charset=utf-8'
    resp.headers['Content-Disposition'] = f'attachment; filename="{fname}"'
    return resp

@app.route('/api/leitstelle/portal-dienste')
def leitstelle_portal_dienste():
    """Return today's and upcoming portal_dienste for Leitstelle view."""
    err = require_leitstelle()
    if err: return err
    datum = request.args.get('datum', '')
    if not datum:
        import datetime as _dt
        datum = _dt.date.today().isoformat()
    with get_db() as db:
        rows = db.execute(
            'SELECT user_name, art, fahrzeug, bezirk, datum, von, bis, notiz '
            "FROM portal_dienste WHERE datum=? AND status!='storniert' ORDER BY art, user_name",
            [datum]
        ).fetchall()
    return jsonify({'ok': True, 'datum': datum, 'dienste': [dict(r) for r in rows]})


@app.route('/api/portal/fahrzeuge')
def portal_fahrzeuge():
    if not _get_portal_user():
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    with get_db() as db:
        rows = db.execute('SELECT name,bezirk,bundesland FROM fahrzeuge WHERE aktiv=1 ORDER BY name').fetchall()
    return jsonify({'ok': True, 'fahrzeuge': [dict(r) for r in rows]})

@app.route('/api/admin/portal/bewerbungen')
def admin_portal_bewerbungen():
    if not _require_admin_or_admiral():
        return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
    with get_db() as db:
        rows = db.execute('SELECT * FROM portal_bewerbungen ORDER BY created_at DESC').fetchall()
        result = []
        for r in rows:
            d = dict(r)
            # Freigegeben Pfleger ohne Dienstnummer → jetzt nachholen
            if (d.get('status') == 'freigegeben'
                    and (d.get('rolle') or 'pfleger') == 'pfleger'
                    and not (d.get('dienstnummer') or '').strip()):
                try:
                    _, dnr = _ensure_caregiver_from_portal(d['id'], db)
                    d['dienstnummer'] = dnr
                except Exception:
                    pass
            result.append(d)
    return jsonify({'ok': True, 'bewerbungen': result})

@app.route('/api/admin/portal/pfleger-anlegen', methods=['POST'])
def admin_portal_pfleger_anlegen():
    if not _require_admin_or_admiral():
        return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
    data = request.get_json(silent=True) or {}
    for f in ('vorname', 'nachname', 'email', 'password'):
        if not data.get(f, '').strip():
            return jsonify({'ok': False, 'error': f'Feld "{f}" fehlt'}), 400
    bid   = 'pb_' + uuid.uuid4().hex[:8]
    token = uuid.uuid4().hex
    with get_db() as db:
        ex = db.execute('SELECT id FROM portal_bewerbungen WHERE LOWER(email)=?', [data['email'].strip().lower()]).fetchone()
        if ex:
            return jsonify({'ok': False, 'error': 'E-Mail bereits registriert'}), 409
        db.execute(
            '''INSERT INTO portal_bewerbungen
               (id,vorname,nachname,email,telefon,password_hash,qualifikation,erfahrung_jahre,
                bezirk,fahrzeug_pref,dienst_arten,adresse,status,token,rolle)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            [bid, data['vorname'].strip(), data['nachname'].strip(),
             data['email'].strip().lower(), data.get('telefon', ''),
             hash_pw(data['password']), data.get('qualifikation', ''),
             0, data.get('bezirk', ''), '',
             json.dumps([]), '', 'freigegeben', token, 'pfleger']
        )
        db.commit()
        _, dnr = _ensure_caregiver_from_portal(bid, db)
    return jsonify({'ok': True, 'id': bid, 'dienstnummer': dnr})


@app.route('/api/admin/portal/bewerbungen/<bid>', methods=['PUT'])
def admin_portal_bewerbung_update(bid):
    if not _require_admin_or_admiral():
        return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
    data = request.get_json(silent=True) or {}
    with get_db() as db:
        row = db.execute('SELECT id FROM portal_bewerbungen WHERE id=?', [bid]).fetchone()
        if not row:
            return jsonify({'ok': False, 'error': 'Nicht gefunden'}), 404
        updates, vals = [], []
        for f in ('status','notizen','bezirk','fahrzeug_pref','qualifikation'):
            if f in data:
                updates.append(f'{f}=?'); vals.append(data[f])
        if updates:
            vals.append(bid)
            db.execute(f'UPDATE portal_bewerbungen SET {", ".join(updates)} WHERE id=?', vals)
            db.commit()
        dnr = ''
        new_status = data.get('status', '')
        if new_status == 'freigegeben':
            pb_row = db.execute('SELECT * FROM portal_bewerbungen WHERE id=?', [bid]).fetchone()
            rolle  = (pb_row or {}).get('rolle', 'pfleger') if pb_row else 'pfleger'
            if rolle == 'pfleger':
                _, dnr = _ensure_caregiver_from_portal(bid, db)
    return jsonify({'ok': True, 'dienstnummer': dnr})

@app.route('/api/admin/portal/bewerbungen/<bid>', methods=['DELETE'])
def admin_portal_bewerbung_delete(bid):
    if not _require_admin_or_admiral():
        return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
    with get_db() as db:
        row = db.execute('SELECT id FROM portal_bewerbungen WHERE id=?', [bid]).fetchone()
        if not row:
            return jsonify({'ok': False, 'error': 'Nicht gefunden'}), 404
        db.execute('DELETE FROM portal_bewerbungen WHERE id=?', [bid])
        db.commit()
    return jsonify({'ok': True})

@app.route('/api/admin/portal/bewerbungen/<bid>/link-senden', methods=['POST'])
def admin_portal_link_senden(bid):
    if not _require_admin_or_admiral():
        return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
    with get_db() as db:
        row = db.execute('SELECT * FROM portal_bewerbungen WHERE id=?', [bid]).fetchone()
        if not row:
            return jsonify({'ok': False, 'error': 'Nicht gefunden'}), 404
        token = row['token'] or uuid.uuid4().hex
        if not row['token']:
            db.execute('UPDATE portal_bewerbungen SET token=? WHERE id=?', [token, bid])
            db.commit()
    link = f'/pflege-portal-bewerbung.html?token={token}'
    return jsonify({'ok': True, 'link': link, 'email': row['email'],
                    'name': row['vorname']+' '+row['nachname']})

@app.route('/api/admin/portal/dienste')
def admin_portal_dienste():
    if not _require_admin_or_admiral():
        return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
    monat = request.args.get('monat','')
    with get_db() as db:
        if monat:
            rows = db.execute('SELECT * FROM portal_dienste WHERE datum LIKE ? ORDER BY datum,art', [f'{monat}%']).fetchall()
        else:
            rows = db.execute('SELECT * FROM portal_dienste ORDER BY datum DESC,art LIMIT 500').fetchall()
    return jsonify({'ok': True, 'dienste': [dict(r) for r in rows]})

@app.route('/api/admin/portal/dienste/<did>', methods=['PUT'])
def admin_portal_dienst_update(did):
    if not _require_admin_or_admiral():
        return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
    data = request.get_json(silent=True) or {}
    with get_db() as db:
        updates, vals = [], []
        for f in ('datum','art','von','bis','fahrzeug','bezirk','status','notiz','user_name'):
            if f in data:
                updates.append(f'{f}=?'); vals.append(data[f])
        if updates:
            vals.append(did)
            db.execute(f'UPDATE portal_dienste SET {", ".join(updates)} WHERE id=?', vals)
            db.commit()
    return jsonify({'ok': True})

@app.route('/api/admin/portal/dienste/<did>', methods=['DELETE'])
def admin_portal_dienst_delete(did):
    if not _require_admin_or_admiral():
        return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
    with get_db() as db:
        db.execute('DELETE FROM portal_dienste WHERE id=?', [did])
        db.commit()
    return jsonify({'ok': True})

@app.route('/api/admin/portal/events', methods=['GET'])
def admin_portal_events_get():
    if not _require_admin_or_admiral():
        return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
    with get_db() as db:
        events = db.execute('SELECT * FROM portal_events ORDER BY datum DESC').fetchall()
        result = []
        for ev in events:
            cnt = db.execute('SELECT COUNT(*) as c FROM portal_event_anmeldungen WHERE event_id=?', [ev['id']]).fetchone()['c']
            d = dict(ev); d['angemeldet_count'] = cnt; result.append(d)
    return jsonify({'ok': True, 'events': result})

@app.route('/api/admin/portal/events', methods=['POST'])
def admin_portal_event_create():
    if not _require_admin_or_admiral():
        return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
    data = request.get_json(silent=True) or {}
    if not data.get('titel') or not data.get('datum'):
        return jsonify({'ok': False, 'error': 'Titel und Datum erforderlich'}), 400
    eid = 'ev_' + uuid.uuid4().hex[:8]
    who = 'Admin' if session.get('admin') else session.get('leitstelle_name','Leitstelle')
    with get_db() as db:
        db.execute(
            'INSERT INTO portal_events (id,titel,datum,von,bis,typ,beschreibung,ort,slots,erstellt_von) VALUES (?,?,?,?,?,?,?,?,?,?)',
            [eid, data['titel'], data['datum'], data.get('von',''), data.get('bis',''),
             data.get('typ','Schulung'), data.get('beschreibung',''), data.get('ort',''),
             int(data.get('slots',0)), who]
        )
        db.commit()
    return jsonify({'ok': True, 'id': eid})

@app.route('/api/admin/portal/events/<eid>', methods=['PUT'])
def admin_portal_event_update(eid):
    if not _require_admin_or_admiral():
        return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
    data = request.get_json(silent=True) or {}
    with get_db() as db:
        updates, vals = [], []
        for f in ('titel','datum','von','bis','typ','beschreibung','ort','slots','aktiv'):
            if f in data:
                updates.append(f'{f}=?'); vals.append(data[f])
        if updates:
            vals.append(eid)
            db.execute(f'UPDATE portal_events SET {", ".join(updates)} WHERE id=?', vals)
            db.commit()
    return jsonify({'ok': True})

@app.route('/api/admin/portal/events/<eid>', methods=['DELETE'])
def admin_portal_event_delete(eid):
    if not _require_admin_or_admiral():
        return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
    with get_db() as db:
        db.execute('DELETE FROM portal_events WHERE id=?', [eid])
        db.execute('DELETE FROM portal_event_anmeldungen WHERE event_id=?', [eid])
        db.commit()
    return jsonify({'ok': True})

@app.route('/api/admin/portal/info', methods=['GET'])
def admin_portal_info_get():
    if not _require_admin_or_admiral():
        return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
    with get_db() as db:
        rows = db.execute('SELECT * FROM portal_info ORDER BY created_at DESC').fetchall()
    return jsonify({'ok': True, 'info': [dict(r) for r in rows]})

@app.route('/api/admin/portal/info', methods=['POST'])
def admin_portal_info_create():
    if not _require_admin_or_admiral():
        return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
    data = request.get_json(silent=True) or {}
    if not data.get('titel') or not data.get('text'):
        return jsonify({'ok': False, 'error': 'Titel und Text erforderlich'}), 400
    iid = 'inf_' + uuid.uuid4().hex[:8]
    with get_db() as db:
        db.execute('INSERT INTO portal_info (id,titel,text,typ,erstellt_von) VALUES (?,?,?,?,?)',
                   [iid, data['titel'], data['text'], data.get('typ','info'),
                    'Admin' if session.get('admin') else 'Leitstelle'])
        db.commit()
    return jsonify({'ok': True, 'id': iid})

@app.route('/api/admin/portal/info/<iid>', methods=['DELETE'])
def admin_portal_info_delete(iid):
    if not _require_admin_or_admiral():
        return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
    with get_db() as db:
        db.execute('DELETE FROM portal_info WHERE id=?', [iid])
        db.commit()
    return jsonify({'ok': True})

# ── Pflegerpersonal-Abrechnung ─────────────────────────────────────────────

@app.route('/api/billing/pflegerpersonal/saetze')
def billing_pp_saetze_get():
    err = require_billing()
    if err: return err
    with get_db() as db:
        rows = db.execute('SELECT * FROM pfleger_bereitschaft_saetze ORDER BY art').fetchall()
    return jsonify({'ok': True, 'saetze': [dict(r) for r in rows]})


@app.route('/api/billing/pflegerpersonal/saetze', methods=['PUT'])
def billing_pp_saetze_put():
    err = require_billing()
    if err: return err
    data = request.get_json(silent=True) or {}
    with get_db() as db:
        for art, satz in data.items():
            db.execute('UPDATE pfleger_bereitschaft_saetze SET satz_eur=? WHERE art=?',
                       [float(satz), art])
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/billing/pflegerpersonal')
def billing_pflegerpersonal():
    err = require_billing()
    if err: return err
    monat = request.args.get('monat', datetime.now().strftime('%Y-%m'))
    # Allow UI to pass in ad-hoc rates (for preview before saving)
    rate_frueh  = float(request.args.get('frueh',  0) or 0)
    rate_spaet  = float(request.args.get('spaet',  0) or 0)
    rate_nacht  = float(request.args.get('nacht',  0) or 0)
    with get_db() as db:
        # Stored rates (fallback)
        saetze_rows = db.execute('SELECT * FROM pfleger_bereitschaft_saetze').fetchall()
        stored = {r['art']: r['satz_eur'] for r in saetze_rows}
        saetze = {
            'Frühdienst':  rate_frueh  if rate_frueh  else stored.get('Frühdienst',  65.0),
            'Spätdienst':  rate_spaet  if rate_spaet  else stored.get('Spätdienst',  70.0),
            'Nachtdienst': rate_nacht  if rate_nacht  else stored.get('Nachtdienst', 85.0),
        }
        # Einsatzvergütung per mission (lk01)
        lk = db.execute("SELECT preis FROM leistungskatalog WHERE id='lk01'").fetchone()
        einsatz_satz = lk['preis'] if lk else 55.0
        # All shifts in month
        dienste = db.execute(
            'SELECT * FROM portal_dienste WHERE datum LIKE ? ORDER BY datum, user_name',
            [f'{monat}%']
        ).fetchall()
        users = {}
        for d in dienste:
            uid = d['user_id']
            if uid not in users:
                users[uid] = {
                    'user_id': uid, 'user_name': d['user_name'],
                    'dienste': [], 'frueh': 0, 'spaet': 0, 'nacht': 0,
                    'einsaetze': 0, 'bereitschaftszulage': 0.0,
                }
            u = users[uid]
            # Count missions for this shift's vehicle on that date
            ez_count = 0
            if d['fahrzeug']:
                ez = db.execute(
                    "SELECT COUNT(*) as c FROM einsaetze WHERE fahrzeug=? AND DATE(COALESCE(updated_at,created_at))=?",
                    [d['fahrzeug'], d['datum']]
                ).fetchone()
                ez_count = ez['c'] if ez else 0
            art = d['art'] or ''
            satz = saetze.get(art, 0.0)
            u['dienste'].append({
                'id': d['id'], 'datum': d['datum'], 'art': art,
                'fahrzeug': d['fahrzeug'] or '', 'bezirk': d['bezirk'] or '',
                'von': d['von'] or '', 'bis': d['bis'] or '',
                'einsaetze': ez_count, 'bereitschaftszulage': satz,
            })
            u['einsaetze'] += ez_count
            u['bereitschaftszulage'] += satz
            if art == 'Frühdienst':  u['frueh']  += 1
            elif art == 'Spätdienst': u['spaet'] += 1
            elif art == 'Nachtdienst':u['nacht']  += 1
        result = []
        for u in users.values():
            u['einsatzverguetung'] = round(u['einsaetze'] * einsatz_satz, 2)
            u['bereitschaftszulage'] = round(u['bereitschaftszulage'], 2)
            u['gesamt'] = round(u['bereitschaftszulage'] + u['einsatzverguetung'], 2)
            u['einsatz_satz'] = einsatz_satz
            result.append(u)
        result.sort(key=lambda x: x['user_name'])
    return jsonify({'ok': True, 'pflegepersonal': result, 'saetze': saetze, 'monat': monat})


# ── Billing: Honorarnoten ────────────────────────────────────────────────────

@app.route('/api/billing/honorar/personal')
def billing_honorar_personal():
    """Pflegekräfte + Disponenten für Honorarnoten-Dropdown."""
    err = require_billing()
    if err: return err
    with get_db() as db:
        cg = db.execute(
            "SELECT id, TRIM(COALESCE(vorname,'')||' '||COALESCE(nachname,'')) AS name,"
            " COALESCE(dienstnummer,'') AS dienstnummer, 'pfleger' AS typ"
            " FROM caregivers WHERE aktiv=1 ORDER BY name"
        ).fetchall()
        ls = db.execute(
            "SELECT id, name, COALESCE(dienstnummer,'') AS dienstnummer, leitstelle_role AS typ"
            " FROM leitstelle_users WHERE aktiv=1 ORDER BY name"
        ).fetchall()
    return jsonify({'ok': True, 'personal': [dict(r) for r in cg] + [dict(r) for r in ls]})


@app.route('/api/billing/honorar/vorschau')
def billing_honorar_vorschau():
    """Auto-Vorschau: Positionen aus Auftragslage für Datum + Person."""
    err = require_billing()
    if err: return err
    datum    = request.args.get('datum', datetime.now().strftime('%Y-%m-%d'))
    user_id  = request.args.get('user_id', '')
    user_typ = request.args.get('user_typ', 'pfleger')
    satz_pat = float(request.args.get('satz_pat', 50) or 50)
    satz_ber = float(request.args.get('satz_ber', 100) or 100)

    with get_db() as db:
        if user_typ == 'pfleger':
            row = db.execute(
                "SELECT TRIM(COALESCE(vorname,'')||' '||COALESCE(nachname,'')) AS name,"
                " COALESCE(dienstnummer,'') AS dienstnummer FROM caregivers WHERE id=?",
                [user_id]
            ).fetchone()
        else:
            row = db.execute(
                "SELECT name, COALESCE(dienstnummer,'') AS dienstnummer FROM leitstelle_users WHERE id=?",
                [user_id]
            ).fetchone()
        name      = row['name'].strip() if row else 'Unbekannt'
        dienst_nr = row['dienstnummer'] if row else ''

        fahrzeug = bezirk = diensttyp = von = bis = ''
        if user_typ == 'pfleger':
            d_row = db.execute(
                "SELECT * FROM portal_dienste WHERE user_id=? AND datum=?", [user_id, datum]
            ).fetchone()
            if d_row:
                fahrzeug  = d_row['fahrzeug'] or ''
                bezirk    = d_row['bezirk']   or ''
                diensttyp = d_row['art']       or ''
                von       = d_row['von']       or ''
                bis       = d_row['bis']       or ''

        if user_typ == 'pfleger' and fahrzeug:
            ez_rows = db.execute(
                "SELECT e.id, e.fahrzeug, e.status,"
                " TRIM(COALESCE(p.vorname,'')||' '||COALESCE(p.nachname,'')) AS pat_name"
                " FROM einsaetze e LEFT JOIN patients p ON p.id=e.patient_id"
                " WHERE e.fahrzeug=? AND DATE(COALESCE(e.updated_at,e.created_at))=?",
                [fahrzeug, datum]
            ).fetchall()
        elif user_typ in ('disponent', 'admin', 'admiral'):
            ez_rows = db.execute(
                "SELECT e.id, e.fahrzeug, e.status,"
                " TRIM(COALESCE(p.vorname,'')||' '||COALESCE(p.nachname,'')) AS pat_name"
                " FROM einsaetze e LEFT JOIN patients p ON p.id=e.patient_id"
                " WHERE DATE(COALESCE(e.updated_at,e.created_at))=?",
                [datum]
            ).fetchall()
        else:
            ez_rows = []

        einsaetze = [dict(r) for r in ez_rows]
        ez_count  = len(einsaetze)

    positionen = []
    if user_typ == 'pfleger':
        bez_ber = 'Bereitschaftspauschale'
        if diensttyp: bez_ber += f' ({diensttyp})'
        if fahrzeug:  bez_ber += f' – Fahrzeug {fahrzeug}'
        if bezirk:    bez_ber += f', {bezirk}. Bezirk'
        positionen.append({'bezeichnung': bez_ber, 'menge': 1, 'preis': satz_ber, 'einheit': 'einmalig'})
        if ez_count:
            namen = sorted(set(e['pat_name'].strip() or 'Patient' for e in einsaetze))
            bez_pat = 'Patienteneinsätze'
            if namen: bez_pat += f' ({", ".join(namen[:4])}{"…" if len(namen)>4 else ""})'
            positionen.append({'bezeichnung': bez_pat, 'menge': ez_count, 'preis': satz_pat, 'einheit': 'Einsatz'})
    else:
        positionen.append({
            'bezeichnung': f'Leitstellen-Disponent – {ez_count} koordinierte Einsatz/Einsätze am {datum}',
            'menge': ez_count or 1, 'preis': satz_pat, 'einheit': 'Einsatz'
        })

    netto = round(sum(p['menge'] * p['preis'] for p in positionen), 2)
    return jsonify({'ok': True, 'name': name, 'dienstnummer': dienst_nr, 'datum': datum,
                    'fahrzeug': fahrzeug, 'bezirk': bezirk, 'diensttyp': diensttyp,
                    'von': von, 'bis': bis, 'einsaetze': einsaetze, 'ez_count': ez_count,
                    'positionen': positionen, 'netto': netto})


@app.route('/api/billing/honorarnoten')
def billing_honorarnoten_list():
    err = require_billing()
    if err: return err
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM rechnungen WHERE typ='honorar' ORDER BY created_at DESC LIMIT 300"
        ).fetchall()
    return jsonify({'ok': True, 'honorarnoten': [dict(r) for r in rows]})


@app.route('/api/billing/honorarnoten', methods=['POST'])
def billing_honorarnoten_create():
    err = require_billing()
    if err: return err
    import uuid as _uuid
    d   = request.get_json(silent=True) or {}
    bid = session.get('billing_user_id') or 'admin'
    with get_db() as db:
        year = datetime.now().year
        last = db.execute(
            "SELECT nummer FROM rechnungen WHERE nummer LIKE ? ORDER BY nummer DESC LIMIT 1",
            [f'HN-{year}-%']
        ).fetchone()
        seq = 1
        if last:
            try: seq = int(last['nummer'].rsplit('-', 1)[-1]) + 1
            except: seq = 1
        nummer = f'HN-{year}-{seq:03d}'
        rid    = str(_uuid.uuid4())
        pos    = d.get('positionen', [])
        netto  = round(sum(float(p.get('menge', 1)) * float(p.get('preis', 0)) for p in pos), 2)
        db.execute(
            "INSERT INTO rechnungen (id,nummer,typ,layout,empfaenger_name,empfaenger_adresse,"
            "empfaenger_plz,empfaenger_ort,empfaenger_email,einsatz_id,positionen,"
            "netto,mwst,brutto,status,faellig_am,notiz,freitext,erstellt_von,billing_user_id)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [rid, nummer, 'honorar', 'honorar',
             d.get('empfaenger_name',''), d.get('empfaenger_adresse',''),
             d.get('empfaenger_plz',''), d.get('empfaenger_ort',''),
             d.get('empfaenger_email',''),
             d.get('referenz',''),
             json.dumps(pos, ensure_ascii=False),
             netto, 0.0, netto,
             'entwurf',
             d.get('faellig_am',''),
             d.get('notiz',''),
             d.get('freitext',''),
             'billing', bid]
        )
        db.commit()
    return jsonify({'ok': True, 'nummer': nummer, 'id': rid, 'netto': netto})


@app.route('/api/billing/honorarnoten/<hid>/status', methods=['POST'])
def billing_honorarnoten_status(hid):
    err = require_billing()
    if err: return err
    status = (request.get_json(silent=True) or {}).get('status', 'entwurf')
    if status not in ('entwurf', 'gestellt', 'bezahlt', 'storniert'):
        return jsonify({'ok': False, 'error': 'Ungültiger Status'}), 400
    with get_db() as db:
        db.execute("UPDATE rechnungen SET status=? WHERE id=? AND typ='honorar'", [status, hid])
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/billing/honorarnoten/<hid>', methods=['DELETE'])
def billing_honorarnoten_delete(hid):
    err = require_billing()
    if err: return err
    with get_db() as db:
        db.execute("DELETE FROM rechnungen WHERE id=? AND typ='honorar'", [hid])
        db.commit()
    return jsonify({'ok': True})


# ── Billing Backup ───────────────────────────────────────────────────────────
@app.route('/api/billing/backup')
def billing_backup():
    err = require_billing()
    if err: return err
    import json as _j, datetime as _dt
    with get_db() as db:
        def rows(sql, params=[]):
            return [dict(r) for r in db.execute(sql, params).fetchall()]
        data = {
            'exported_at': _dt.datetime.now().isoformat(),
            'bereich': 'Verrechnungsstelle',
            'rechnungen': rows(
                "SELECT * FROM rechnungen ORDER BY id DESC"),
            'leistungskatalog': rows(
                "SELECT * FROM leistungskatalog ORDER BY id"),
            'billing_settings': rows(
                "SELECT schluessel,wert FROM billing_settings"),
            'bereitschaftssaetze': rows(
                "SELECT * FROM pfleger_bereitschaft_saetze ORDER BY id"),
        }
    resp = make_response(_j.dumps(data, ensure_ascii=False, indent=2, default=str))
    fname = 'nursy_backup_verrechnungsstelle_' + _dt.date.today().isoformat() + '.json'
    resp.headers['Content-Type'] = 'application/json; charset=utf-8'
    resp.headers['Content-Disposition'] = f'attachment; filename="{fname}"'
    return resp

# ── Billing-Einstellungen (Fußzeile etc.) ──────────────────────────────────

@app.route('/api/billing/settings')
def billing_settings_get():
    err = require_billing()
    if err: return err
    with get_db() as db:
        rows = db.execute('SELECT key, value FROM billing_settings').fetchall()
    return jsonify({'ok': True, 'settings': {r['key']: r['value'] for r in rows}})


@app.route('/api/billing/settings', methods=['PUT'])
def billing_settings_put():
    # Only admiral/admin may change settings
    is_admin = bool(session.get('admin'))
    if not is_admin:
        bid = session.get('billing_user_id')
        if bid == 'admin':
            is_admin = True
        elif bid:
            with get_db() as db:
                u = db.execute('SELECT rolle FROM billing_users WHERE id=?', [bid]).fetchone()
            is_admin = bool(u and u['rolle'] in ('admiral', 'admin'))
    if not is_admin:
        return jsonify({'ok': False, 'error': 'Nur Admiral darf Einstellungen ändern'}), 403
    data = request.get_json(silent=True) or {}
    with get_db() as db:
        for k, v in data.items():
            if USE_PG:
                db.execute('INSERT INTO billing_settings (key,value) VALUES (?,?) ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value',
                           [k, str(v)])
            else:
                db.execute('INSERT OR REPLACE INTO billing_settings (key,value) VALUES (?,?)',
                           [k, str(v)])
        db.commit()
    return jsonify({'ok': True})


# ── Rechnungs-Vorlagen (CRUD, Admiral only for write) ─────────────────────────

@app.route('/api/billing/vorlagen')
def billing_vorlagen_list():
    err = require_billing()
    if err: return err
    with get_db() as db:
        rows = db.execute('SELECT * FROM billing_vorlagen ORDER BY created_at DESC').fetchall()
    return jsonify({'ok': True, 'vorlagen': [dict(r) for r in rows]})


@app.route('/api/billing/vorlagen', methods=['POST'])
def billing_vorlagen_create():
    err = _require_billing_admiral()
    if err: return err
    data = request.get_json(silent=True) or {}
    vid = 'v_' + uuid.uuid4().hex[:10]
    with get_db() as db:
        db.execute(
            'INSERT INTO billing_vorlagen (id,name,typ,betreff,freitext) VALUES (?,?,?,?,?)',
            [vid, data.get('name', 'Neue Vorlage'), data.get('typ', 'beide'),
             data.get('betreff', ''), data.get('freitext', '')]
        )
        db.commit()
    return jsonify({'ok': True, 'id': vid})


@app.route('/api/billing/vorlagen/<vid>', methods=['PUT'])
def billing_vorlagen_update(vid):
    err = _require_billing_admiral()
    if err: return err
    data = request.get_json(silent=True) or {}
    with get_db() as db:
        db.execute(
            'UPDATE billing_vorlagen SET name=?,typ=?,betreff=?,freitext=? WHERE id=?',
            [data.get('name', ''), data.get('typ', 'beide'),
             data.get('betreff', ''), data.get('freitext', ''), vid]
        )
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/billing/vorlagen/<vid>', methods=['DELETE'])
def billing_vorlagen_delete(vid):
    err = _require_billing_admiral()
    if err: return err
    with get_db() as db:
        db.execute('DELETE FROM billing_vorlagen WHERE id=?', [vid])
        db.commit()
    return jsonify({'ok': True})


# ── Care: Dokumentation ──────────────────────────────────────────────────────

@app.route('/api/care/dokumentation')
def care_dok_list():
    err = _require_care_or_admin()
    if err: return err
    pat_id = request.args.get('patient_id', '')
    with get_db() as db:
        if pat_id:
            rows = db.execute(
                'SELECT * FROM patient_dokumentation WHERE patient_id=? ORDER BY datum DESC, uhrzeit DESC',
                [pat_id]
            ).fetchall()
        else:
            rows = db.execute(
                'SELECT * FROM patient_dokumentation ORDER BY datum DESC, uhrzeit DESC'
            ).fetchall()
    return jsonify({'ok': True, 'eintraege': [dict(r) for r in rows]})


@app.route('/api/care/dokumentation', methods=['POST'])
def care_dok_create():
    err = _require_care_or_admin()
    if err: return err
    d = request.get_json(silent=True) or {}
    eid = d.get('id') or ('dok_' + uuid.uuid4().hex[:12])
    with get_db() as db:
        if USE_PG:
            db.execute(
                '''INSERT INTO patient_dokumentation
                   (id, patient_id, patient_name, birth, typ, plan, grp, datum, uhrzeit, text, important, wund_refs, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                   ON CONFLICT (id) DO UPDATE SET
                   patient_id=EXCLUDED.patient_id, patient_name=EXCLUDED.patient_name,
                   birth=EXCLUDED.birth, typ=EXCLUDED.typ, plan=EXCLUDED.plan, grp=EXCLUDED.grp,
                   datum=EXCLUDED.datum, uhrzeit=EXCLUDED.uhrzeit, text=EXCLUDED.text,
                   important=EXCLUDED.important, wund_refs=EXCLUDED.wund_refs, updated_at=EXCLUDED.updated_at''',
                [eid, d.get('patientId', ''), d.get('patientName', ''), d.get('birth', ''),
                 d.get('type', 'allgemein'), d.get('plan', ''), d.get('group', 'Pfleger'),
                 d.get('date', ''), d.get('time', ''), d.get('text', ''),
                 1 if d.get('important') else 0,
                 json.dumps(d.get('wundRefs', [])), d.get('updatedAt', '')]
            )
        else:
            db.execute(
                '''INSERT OR REPLACE INTO patient_dokumentation
                   (id, patient_id, patient_name, birth, typ, plan, grp, datum, uhrzeit, text, important, wund_refs, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                [eid, d.get('patientId', ''), d.get('patientName', ''), d.get('birth', ''),
                 d.get('type', 'allgemein'), d.get('plan', ''), d.get('group', 'Pfleger'),
                 d.get('date', ''), d.get('time', ''), d.get('text', ''),
                 1 if d.get('important') else 0,
                 json.dumps(d.get('wundRefs', [])), d.get('updatedAt', '')]
            )
        db.commit()
    return jsonify({'ok': True, 'id': eid})


@app.route('/api/care/dokumentation/<eid>', methods=['PUT'])
def care_dok_update(eid):
    err = _require_care_or_admin()
    if err: return err
    d = request.get_json(silent=True) or {}
    with get_db() as db:
        db.execute(
            '''UPDATE patient_dokumentation SET
               patient_id=?, patient_name=?, birth=?, typ=?, plan=?, grp=?, datum=?, uhrzeit=?,
               text=?, important=?, wund_refs=?, updated_at=?
               WHERE id=?''',
            [d.get('patientId', ''), d.get('patientName', ''), d.get('birth', ''),
             d.get('type', 'allgemein'), d.get('plan', ''), d.get('group', 'Pfleger'),
             d.get('date', ''), d.get('time', ''), d.get('text', ''),
             1 if d.get('important') else 0,
             json.dumps(d.get('wundRefs', [])), d.get('updatedAt', ''), eid]
        )
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/care/dokumentation/<eid>', methods=['DELETE'])
def care_dok_delete(eid):
    err = _require_care_or_admin()
    if err: return err
    with get_db() as db:
        db.execute('DELETE FROM patient_dokumentation WHERE id=?', [eid])
        db.commit()
    return jsonify({'ok': True})


# ── Care: Vitalzeichen ────────────────────────────────────────────────────────

@app.route('/api/care/vitalzeichen/<pat_id>')
def care_vz_list(pat_id):
    err = _require_care_or_admin()
    if err: return err
    with get_db() as db:
        rows = db.execute(
            'SELECT * FROM patient_vitalzeichen WHERE patient_id=? ORDER BY datum ASC, uhrzeit ASC',
            [pat_id]
        ).fetchall()
    return jsonify({'ok': True, 'eintraege': [dict(r) for r in rows]})


@app.route('/api/care/vitalzeichen', methods=['POST'])
def care_vz_create():
    err = _require_care_or_admin()
    if err: return err
    d = request.get_json(silent=True) or {}
    vid = 'vz_' + uuid.uuid4().hex[:12]
    def _n(k):
        v = d.get(k)
        return None if (v is None or v == '') else v
    with get_db() as db:
        db.execute(
            '''INSERT INTO patient_vitalzeichen
               (id, patient_id, datum, uhrzeit, sys, dia, puls, spo2, temp, vz_score,
                gewicht, groesse, bz, bz_methode, in_ml, out_ml)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            [vid, d.get('patientId', ''), d.get('date', ''), d.get('time', ''),
             _n('sys'), _n('dia'), _n('puls'), _n('spo2'), _n('temp'), _n('vzScore'),
             _n('weight'), _n('height'), _n('bz'), d.get('bzMethod', ''),
             _n('in_ml'), _n('out_ml')]
        )
        db.commit()
    return jsonify({'ok': True, 'id': vid})


@app.route('/api/care/vitalzeichen/<vid>', methods=['DELETE'])
def care_vz_delete(vid):
    err = _require_care_or_admin()
    if err: return err
    with get_db() as db:
        db.execute('DELETE FROM patient_vitalzeichen WHERE id=?', [vid])
        db.commit()
    return jsonify({'ok': True})


# ── Care: Durchführungsnachweis ───────────────────────────────────────────────

@app.route('/api/care/df/<pat_id>/<datum>')
def care_df_get(pat_id, datum):
    err = _require_care_or_admin()
    if err: return err
    with get_db() as db:
        row = db.execute(
            'SELECT state FROM patient_df_eintraege WHERE patient_id=? AND datum=?',
            [pat_id, datum]
        ).fetchone()
    state = json.loads(row['state']) if row else {}
    return jsonify({'ok': True, 'state': state})


@app.route('/api/care/df/<pat_id>/<datum>', methods=['POST'])
def care_df_save(pat_id, datum):
    err = _require_care_or_admin()
    if err: return err
    d = request.get_json(silent=True) or {}
    state = d.get('state', {})
    with get_db() as db:
        if USE_PG:
            db.execute(
                '''INSERT INTO patient_df_eintraege (patient_id, datum, state, updated_at)
                   VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT (patient_id, datum) DO UPDATE SET
                   state=EXCLUDED.state, updated_at=EXCLUDED.updated_at''',
                [pat_id, datum, json.dumps(state)]
            )
        else:
            db.execute(
                '''INSERT OR REPLACE INTO patient_df_eintraege (patient_id, datum, state, updated_at)
                   VALUES (?, ?, ?, datetime('now','localtime'))''',
                [pat_id, datum, json.dumps(state)]
            )
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/care/df/<pat_id>/archive')
def care_df_archive(pat_id):
    err = _require_care_or_admin()
    if err: return err
    import datetime as _dt
    today = _dt.date.today().isoformat()
    with get_db() as db:
        rows = db.execute(
            'SELECT datum, state FROM patient_df_eintraege WHERE patient_id=? AND datum<? ORDER BY datum DESC',
            [pat_id, today]
        ).fetchall()
    archive = [{'date': r['datum'], 'data': json.loads(r['state'])} for r in rows]
    return jsonify({'ok': True, 'archive': archive})


# ── Care: Pflegeplanung ───────────────────────────────────────────────────────

@app.route('/api/care/pflegeplanung/<pat_id>')
def care_pp_get(pat_id):
    err = _require_care_or_admin()
    if err: return err
    with get_db() as db:
        row = db.execute(
            'SELECT plaene, wund_plan FROM patient_pflegeplaene WHERE patient_id=?', [pat_id]
        ).fetchone()
    if row:
        wund = json.loads(row['wund_plan']) if row['wund_plan'] and row['wund_plan'] != 'null' else None
        return jsonify({'ok': True, 'plaene': json.loads(row['plaene']), 'wundPlan': wund})
    return jsonify({'ok': True, 'plaene': [], 'wundPlan': None})


@app.route('/api/care/pflegeplanung/<pat_id>', methods=['PUT'])
def care_pp_save(pat_id):
    err = _require_care_or_admin()
    if err: return err
    d = request.get_json(silent=True) or {}
    with get_db() as db:
        if USE_PG:
            db.execute(
                '''INSERT INTO patient_pflegeplaene (patient_id, plaene, wund_plan, updated_at)
                   VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT (patient_id) DO UPDATE SET
                   plaene=EXCLUDED.plaene, wund_plan=EXCLUDED.wund_plan, updated_at=EXCLUDED.updated_at''',
                [pat_id, json.dumps(d.get('plaene', [])), json.dumps(d.get('wundPlan'))]
            )
        else:
            db.execute(
                '''INSERT OR REPLACE INTO patient_pflegeplaene (patient_id, plaene, wund_plan, updated_at)
                   VALUES (?, ?, ?, datetime('now','localtime'))''',
                [pat_id, json.dumps(d.get('plaene', [])), json.dumps(d.get('wundPlan'))]
            )
        db.commit()
    return jsonify({'ok': True})


# ── Care: Meine Patienten (angenommene Matches) ───────────────────────────────

@app.route('/api/care/meine-patienten')
def care_meine_patienten_list():
    err = _require_care_or_admin()
    if err: return err
    cg_id = session.get('user_id')
    with get_db() as db:
        rows = db.execute(
            'SELECT patient_json FROM care_accepted_patients WHERE caregiver_id=? AND active=1 ORDER BY accepted_at DESC',
            [cg_id]
        ).fetchall()
    patients = [json.loads(r['patient_json']) for r in rows]
    return jsonify({'ok': True, 'patients': patients, 'caregiver_id': cg_id})


@app.route('/api/care/meine-patienten', methods=['POST'])
def care_meine_patienten_add():
    err = _require_care_or_admin()
    if err: return err
    cg_id = session.get('user_id')
    d = request.get_json(silent=True) or {}
    pat_id = d.get('id', '')
    if not pat_id:
        return jsonify({'error': 'id fehlt'}), 400
    row_id = cg_id + '_' + pat_id
    with get_db() as db:
        if USE_PG:
            db.execute(
                '''INSERT INTO care_accepted_patients (id, caregiver_id, patient_id, patient_json, accepted_at, active)
                   VALUES (?,?,?,?,CURRENT_TIMESTAMP,1)
                   ON CONFLICT (id) DO UPDATE SET patient_json=EXCLUDED.patient_json, active=1, accepted_at=EXCLUDED.accepted_at''',
                [row_id, cg_id, pat_id, json.dumps(d)]
            )
        else:
            db.execute(
                "INSERT OR REPLACE INTO care_accepted_patients (id,caregiver_id,patient_id,patient_json,accepted_at,active) "
                "VALUES (?,?,?,?,datetime('now','localtime'),1)",
                [row_id, cg_id, pat_id, json.dumps(d)]
            )
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/care/meine-patienten/<pid>', methods=['DELETE'])
def care_meine_patienten_remove(pid):
    err = _require_care_or_admin()
    if err: return err
    cg_id = session.get('user_id')
    row_id = cg_id + '_' + pid
    with get_db() as db:
        db.execute('UPDATE care_accepted_patients SET active=0 WHERE id=?', [row_id])
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/care/meine-patienten/reset', methods=['POST'])
def care_meine_patienten_reset():
    err = _require_care_or_admin()
    if err: return err
    cg_id = session.get('user_id')
    with get_db() as db:
        db.execute('UPDATE care_accepted_patients SET active=0 WHERE caregiver_id=?', [cg_id])
        db.commit()
    return jsonify({'ok': True})


# ── Care: Profil ──────────────────────────────────────────────────────────────

@app.route('/api/care/profil')
def care_profil_get():
    err = _require_care_or_admin()
    if err: return err
    cg_id = session.get('user_id')
    with get_db() as db:
        row = db.execute('SELECT * FROM caregivers WHERE id=?', [cg_id]).fetchone()
    if not row:
        return jsonify({'ok': True, 'profil': {}})
    extra = {}
    try:
        raw = row['profil_extra'] if row.get('profil_extra') else '{}'
        extra = json.loads(raw) if raw and raw not in ('null', '') else {}
    except Exception:
        pass
    profil = {
        'id': row['id'],
        'firstName': row['vorname'] or '',
        'lastName': row['nachname'] or '',
        'email': row['email'] or '',
        'gender': row['gender'] or '',
        'street': row.get('address', '') or '',
        'zip': row.get('plz', '') or '',
        'city': row.get('ort', '') or '',
        'district': row.get('bezirk', '') or '',
        'dienstnummer': row.get('dienstnummer', '') or '',
    }
    profil.update(extra)
    return jsonify({'ok': True, 'profil': profil})


@app.route('/api/care/profil', methods=['PUT'])
def care_profil_save():
    err = _require_care_or_admin()
    if err: return err
    cg_id = session.get('user_id')
    d = request.get_json(silent=True) or {}
    base_keys = {'id', 'firstName', 'lastName', 'email', 'gender', 'street', 'zip', 'city', 'district', 'dienstnummer'}
    extra = {k: v for k, v in d.items() if k not in base_keys}
    with get_db() as db:
        db.execute(
            'UPDATE caregivers SET vorname=?,nachname=?,gender=?,address=?,plz=?,ort=?,bezirk=?,profil_extra=? WHERE id=?',
            [d.get('firstName', ''), d.get('lastName', ''), d.get('gender', ''),
             d.get('street', ''), d.get('zip', ''), d.get('city', ''),
             d.get('district', ''), json.dumps(extra), cg_id]
        )
        db.commit()
    return jsonify({'ok': True})


# ── Care: Wunddokumentation ───────────────────────────────────────────────────

@app.route('/api/care/wunddoku/<pat_id>')
def care_wunddoku_get(pat_id):
    err = _require_care_or_admin()
    if err: return err
    with get_db() as db:
        row = db.execute(
            'SELECT data_json FROM patient_wunddoku WHERE patient_id=? ORDER BY datum DESC LIMIT 1',
            [pat_id]
        ).fetchone()
    if not row:
        return jsonify({'ok': True, 'data': None})
    return jsonify({'ok': True, 'data': json.loads(row['data_json'])})


@app.route('/api/care/wunddoku/<pat_id>', methods=['POST'])
def care_wunddoku_save(pat_id):
    err = _require_care_or_admin()
    if err: return err
    import datetime as _dt
    d = request.get_json(silent=True) or {}
    today = _dt.date.today().isoformat()
    row_id = pat_id + '_' + today
    with get_db() as db:
        if USE_PG:
            db.execute(
                '''INSERT INTO patient_wunddoku (id,patient_id,datum,data_json,updated_at)
                   VALUES (?,?,?,?,CURRENT_TIMESTAMP)
                   ON CONFLICT (id) DO UPDATE SET data_json=EXCLUDED.data_json, updated_at=EXCLUDED.updated_at''',
                [row_id, pat_id, today, json.dumps(d)]
            )
        else:
            db.execute(
                "INSERT OR REPLACE INTO patient_wunddoku (id,patient_id,datum,data_json,updated_at) "
                "VALUES (?,?,?,?,datetime('now','localtime'))",
                [row_id, pat_id, today, json.dumps(d)]
            )
        db.commit()
    return jsonify({'ok': True})


# ── Care: Vollständiger Backup (alle Daten auf einmal) ───────────────────────

@app.route('/api/care/backup', methods=['POST'])
def care_backup_save():
    """Speichert alle Pfleger-Daten als Komplett-Backup (Wunddoku, DN-Einträge, Pflegeplanung)."""
    err = _require_care_or_admin()
    if err: return err
    cg_id = session.get('user_id') or session.get('leitstelle_id') or 'unknown'
    import datetime as _dt
    today = _dt.date.today().isoformat()
    d = request.get_json(silent=True) or {}
    saved = []

    with get_db() as db:
        # 1. DN-Einträge (nursy_df_v1_<patId>_<datum>)
        for entry in d.get('df_eintraege', []):
            pat_id = entry.get('patient_id', '')
            datum  = entry.get('datum', today)
            state  = entry.get('state', {})
            if not pat_id: continue
            if USE_PG:
                db.execute(
                    '''INSERT INTO patient_df_eintraege (patient_id, datum, state, updated_at)
                       VALUES (?,?,?,CURRENT_TIMESTAMP)
                       ON CONFLICT (patient_id, datum) DO UPDATE SET state=EXCLUDED.state, updated_at=EXCLUDED.updated_at''',
                    [pat_id, datum, json.dumps(state)]
                )
            else:
                db.execute(
                    "INSERT OR REPLACE INTO patient_df_eintraege (patient_id,datum,state,updated_at) VALUES (?,?,?,datetime('now','localtime'))",
                    [pat_id, datum, json.dumps(state)]
                )
            saved.append('df:' + pat_id + ':' + datum)

        # 2. Wunddokumentation (nursy_wunddoku_v1)
        for wd in d.get('wunddoku', []):
            pat_id = wd.get('patient_id', '')
            datum  = wd.get('datum', today)
            if not pat_id: continue
            row_id = pat_id + '_' + datum
            if USE_PG:
                db.execute(
                    '''INSERT INTO patient_wunddoku (id,patient_id,datum,data_json,updated_at)
                       VALUES (?,?,?,?,CURRENT_TIMESTAMP)
                       ON CONFLICT (id) DO UPDATE SET data_json=EXCLUDED.data_json, updated_at=EXCLUDED.updated_at''',
                    [row_id, pat_id, datum, json.dumps(wd.get('data', {}))]
                )
            else:
                db.execute(
                    "INSERT OR REPLACE INTO patient_wunddoku (id,patient_id,datum,data_json,updated_at) VALUES (?,?,?,?,datetime('now','localtime'))",
                    [row_id, pat_id, datum, json.dumps(wd.get('data', {}))]
                )
            saved.append('wunddoku:' + pat_id)

        # 3. Pflegeplanung / Wundplan (nursy_pp_wund_v1_<patId>)
        for pp in d.get('pflegeplanung', []):
            pat_id = pp.get('patient_id', '')
            if not pat_id: continue
            wund_plan = pp.get('wundPlan')
            med_plan  = pp.get('medPlan')
            if USE_PG:
                db.execute(
                    '''INSERT INTO patient_pflegeplanung (patient_id, wund_plan, med_plan, updated_at)
                       VALUES (?,?,?,CURRENT_TIMESTAMP)
                       ON CONFLICT (patient_id) DO UPDATE SET
                       wund_plan=COALESCE(EXCLUDED.wund_plan, patient_pflegeplanung.wund_plan),
                       med_plan=COALESCE(EXCLUDED.med_plan, patient_pflegeplanung.med_plan),
                       updated_at=EXCLUDED.updated_at''',
                    [pat_id, json.dumps(wund_plan) if wund_plan is not None else None,
                     json.dumps(med_plan) if med_plan is not None else None]
                )
            else:
                row = db.execute('SELECT patient_id FROM patient_pflegeplanung WHERE patient_id=?', [pat_id]).fetchone()
                if row:
                    db.execute(
                        '''UPDATE patient_pflegeplanung SET
                           wund_plan=COALESCE(?,wund_plan), med_plan=COALESCE(?,med_plan),
                           updated_at=datetime('now','localtime') WHERE patient_id=?''',
                        [json.dumps(wund_plan) if wund_plan is not None else None,
                         json.dumps(med_plan) if med_plan is not None else None, pat_id]
                    )
                else:
                    db.execute(
                        "INSERT INTO patient_pflegeplanung (patient_id,wund_plan,med_plan,updated_at) VALUES (?,?,?,datetime('now','localtime'))",
                        [pat_id, json.dumps(wund_plan) if wund_plan is not None else None,
                         json.dumps(med_plan) if med_plan is not None else None]
                    )
            saved.append('pflegeplanung:' + pat_id)

        db.commit()
    return jsonify({'ok': True, 'saved': saved, 'count': len(saved)})


@app.route('/api/care/backup', methods=['GET'])
def care_backup_load():
    """Lädt alle gesicherten Daten des eingeloggten Pflegers."""
    err = _require_care_or_admin()
    if err: return err
    cg_id = session.get('user_id') or ''
    # Patient-IDs des Pflegers ermitteln
    with get_db() as db:
        cap_rows = db.execute(
            "SELECT DISTINCT patient_id FROM care_accepted_patients WHERE caregiver_id=? AND active=1",
            [cg_id]
        ).fetchall()
        pat_ids = [r['patient_id'] for r in cap_rows]
        result = {'df_eintraege': [], 'wunddoku': [], 'pflegeplanung': []}
        for pid in pat_ids:
            df_rows = db.execute(
                'SELECT datum, state FROM patient_df_eintraege WHERE patient_id=? ORDER BY datum DESC LIMIT 90',
                [pid]
            ).fetchall()
            for r in df_rows:
                result['df_eintraege'].append({'patient_id': pid, 'datum': r['datum'], 'state': json.loads(r['state'])})
            wd_row = db.execute(
                'SELECT datum, data_json FROM patient_wunddoku WHERE patient_id=? ORDER BY datum DESC LIMIT 1',
                [pid]
            ).fetchone()
            if wd_row:
                result['wunddoku'].append({'patient_id': pid, 'datum': wd_row['datum'], 'data': json.loads(wd_row['data_json'])})
            pp_row = db.execute(
                'SELECT wund_plan, med_plan FROM patient_pflegeplanung WHERE patient_id=?', [pid]
            ).fetchone()
            if pp_row:
                result['pflegeplanung'].append({
                    'patient_id': pid,
                    'wundPlan': json.loads(pp_row['wund_plan']) if pp_row['wund_plan'] else None,
                    'medPlan':  json.loads(pp_row['med_plan'])  if pp_row['med_plan']  else None,
                })
    return jsonify({'ok': True, **result})


# ── Care: Vollständiger Daten-Export (Festplatten-Backup) ────────────────────

@app.route('/api/care/export')
def care_export():
    """Erstellt einen vollständigen Daten-Export für den eingeloggten Pfleger."""
    err = _require_care_or_admin()
    if err: return err
    import datetime as _dt
    cg_id  = session.get('user_id') or ''
    today  = _dt.date.today().isoformat()
    now_ts = _dt.datetime.now().strftime('%Y-%m-%dT%H:%M:%S')

    with get_db() as db:
        # Profil
        cg_row = db.execute('SELECT * FROM caregivers WHERE id=?', [cg_id]).fetchone()
        profil = {}
        if cg_row:
            profil = {k: cg_row[k] for k in cg_row.keys() if k not in ('password_hash',)}

        # Patienten
        cap_rows = db.execute(
            'SELECT * FROM care_accepted_patients WHERE caregiver_id=? ORDER BY accepted_at DESC',
            [cg_id]
        ).fetchall()
        patienten = []
        for cap in cap_rows:
            try: pj = json.loads(cap['patient_json'] or '{}')
            except: pj = {}
            patienten.append({
                'patient_id':  cap['patient_id'],
                'accepted_at': cap['accepted_at'],
                'active':      cap['active'],
                'daten':       pj,
            })

        pat_ids = [r['patient_id'] for r in cap_rows if r['active'] == 1]

        # DN-Einträge
        df_eintraege = []
        for pid in pat_ids:
            rows = db.execute(
                'SELECT datum,state FROM patient_df_eintraege WHERE patient_id=? ORDER BY datum DESC',
                [pid]
            ).fetchall()
            for r in rows:
                df_eintraege.append({'patient_id': pid, 'datum': r['datum'],
                                     'state': json.loads(r['state'])})

        # Wunddokumentation
        wunddoku = []
        for pid in pat_ids:
            rows = db.execute(
                'SELECT datum,data_json FROM patient_wunddoku WHERE patient_id=? ORDER BY datum DESC',
                [pid]
            ).fetchall()
            for r in rows:
                wunddoku.append({'patient_id': pid, 'datum': r['datum'],
                                 'data': json.loads(r['data_json'])})

        # Pflegeplanung
        pflegeplanung = []
        for pid in pat_ids:
            row = db.execute(
                'SELECT wund_plan,med_plan,updated_at FROM patient_pflegeplanung WHERE patient_id=?',
                [pid]
            ).fetchone()
            if row:
                pflegeplanung.append({
                    'patient_id': pid,
                    'wundPlan':   json.loads(row['wund_plan']) if row['wund_plan'] else None,
                    'medPlan':    json.loads(row['med_plan'])  if row['med_plan']  else None,
                    'updated_at': row['updated_at'],
                })

        # Vitalzeichen
        vitalzeichen = []
        for pid in pat_ids:
            rows = db.execute(
                'SELECT * FROM patient_vitalzeichen WHERE patient_id=? ORDER BY datum DESC, uhrzeit DESC',
                [pid]
            ).fetchall()
            for r in rows:
                vitalzeichen.append(dict(r))

        # Dokumentation
        dokumentation = []
        for pid in pat_ids:
            rows = db.execute(
                'SELECT * FROM patient_dokumentation WHERE patient_id=? ORDER BY datum DESC',
                [pid]
            ).fetchall()
            for r in rows:
                dokumentation.append(dict(r))

        # Tourenlog (letzte 90 Tage)
        tourenlog = []
        rows = db.execute(
            "SELECT datum,log_json FROM care_tourenlog WHERE caregiver_id=? ORDER BY datum DESC LIMIT 90",
            [cg_id]
        ).fetchall()
        for r in rows:
            tourenlog.append({'datum': r['datum'], 'log': json.loads(r['log_json'])})

    export_data = {
        '_meta': {
            'version':      '1.0',
            'exported_at':  now_ts,
            'export_date':  today,
            'source':       'Nursy Pflege-Marketplace',
            'caregiver_id': cg_id,
        },
        'profil':       profil,
        'patienten':    patienten,
        'df_eintraege': df_eintraege,
        'wunddoku':     wunddoku,
        'pflegeplanung': pflegeplanung,
        'vitalzeichen': vitalzeichen,
        'dokumentation': dokumentation,
        'tourenlog':    tourenlog,
    }

    name_slug = (profil.get('nachname','') + '_' + profil.get('vorname','')).strip('_') or 'pfleger'
    filename  = f'nursy_backup_{name_slug}_{today}.json'

    response = make_response(json.dumps(export_data, ensure_ascii=False, indent=2))
    response.headers['Content-Type']        = 'application/json; charset=utf-8'
    response.headers['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@app.route('/api/care/import', methods=['POST'])
def care_import():
    """Importiert einen Nursy-Export zurück in die Datenbank."""
    err = _require_care_or_admin()
    if err: return err
    import datetime as _dt
    cg_id = session.get('user_id') or ''
    today = _dt.date.today().isoformat()
    d = request.get_json(silent=True) or {}
    meta = d.get('_meta', {})

    # Sicherheitscheck: nur eigene Daten importieren (oder Admin)
    if meta.get('caregiver_id') and meta['caregiver_id'] != cg_id and not session.get('admin'):
        return jsonify({'ok': False, 'error': 'Export gehört einem anderen Pfleger'}), 403

    counts = {}
    with get_db() as db:
        # DN-Einträge
        c = 0
        for entry in d.get('df_eintraege', []):
            pid   = entry.get('patient_id', '')
            datum = entry.get('datum', today)
            state = entry.get('state', {})
            if not pid: continue
            if USE_PG:
                db.execute(
                    '''INSERT INTO patient_df_eintraege (patient_id,datum,state,updated_at)
                       VALUES (?,?,?,CURRENT_TIMESTAMP)
                       ON CONFLICT (patient_id,datum) DO UPDATE SET
                       state=EXCLUDED.state, updated_at=EXCLUDED.updated_at''',
                    [pid, datum, json.dumps(state)]
                )
            else:
                db.execute(
                    "INSERT OR REPLACE INTO patient_df_eintraege (patient_id,datum,state,updated_at) VALUES (?,?,?,datetime('now','localtime'))",
                    [pid, datum, json.dumps(state)]
                )
            c += 1
        counts['df_eintraege'] = c

        # Wunddokumentation
        c = 0
        for wd in d.get('wunddoku', []):
            pid   = wd.get('patient_id', '')
            datum = wd.get('datum', today)
            if not pid: continue
            row_id = pid + '_' + datum
            if USE_PG:
                db.execute(
                    '''INSERT INTO patient_wunddoku (id,patient_id,datum,data_json,updated_at)
                       VALUES (?,?,?,?,CURRENT_TIMESTAMP)
                       ON CONFLICT (id) DO UPDATE SET data_json=EXCLUDED.data_json,updated_at=EXCLUDED.updated_at''',
                    [row_id, pid, datum, json.dumps(wd.get('data', {}))]
                )
            else:
                db.execute(
                    "INSERT OR REPLACE INTO patient_wunddoku (id,patient_id,datum,data_json,updated_at) VALUES (?,?,?,?,datetime('now','localtime'))",
                    [row_id, pid, datum, json.dumps(wd.get('data', {}))]
                )
            c += 1
        counts['wunddoku'] = c

        # Vitalzeichen
        c = 0
        for vz in d.get('vitalzeichen', []):
            vid = vz.get('id')
            if not vid: continue
            if USE_PG:
                db.execute(
                    '''INSERT INTO patient_vitalzeichen (id,patient_id,datum,uhrzeit,blutdruck_s,blutdruck_d,puls,temperatur,blutzucker,sauerstoff,atemfrequenz,gewicht,bemerkung,erfasst_von,updated_at)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
                       ON CONFLICT (id) DO NOTHING''',
                    [vid, vz.get('patient_id',''), vz.get('datum',''), vz.get('uhrzeit',''),
                     vz.get('blutdruck_s'), vz.get('blutdruck_d'), vz.get('puls'),
                     vz.get('temperatur'), vz.get('blutzucker'), vz.get('sauerstoff'),
                     vz.get('atemfrequenz'), vz.get('gewicht'), vz.get('bemerkung',''),
                     vz.get('erfasst_von','')]
                )
            else:
                db.execute(
                    "INSERT OR IGNORE INTO patient_vitalzeichen (id,patient_id,datum,uhrzeit,blutdruck_s,blutdruck_d,puls,temperatur,blutzucker,sauerstoff,atemfrequenz,gewicht,bemerkung,erfasst_von) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    [vid, vz.get('patient_id',''), vz.get('datum',''), vz.get('uhrzeit',''),
                     vz.get('blutdruck_s'), vz.get('blutdruck_d'), vz.get('puls'),
                     vz.get('temperatur'), vz.get('blutzucker'), vz.get('sauerstoff'),
                     vz.get('atemfrequenz'), vz.get('gewicht'), vz.get('bemerkung',''),
                     vz.get('erfasst_von','')]
                )
            c += 1
        counts['vitalzeichen'] = c

        db.commit()

    return jsonify({'ok': True, 'counts': counts,
                    'message': f"Import erfolgreich: {sum(counts.values())} Einträge wiederhergestellt."})


# ── Care: Tourenlog ───────────────────────────────────────────────────────────

@app.route('/api/care/tourenlog/<datum>')
def care_tourenlog_get(datum):
    err = _require_care_or_admin()
    if err: return err
    cg_id = session.get('user_id')
    row_id = cg_id + '_' + datum
    with get_db() as db:
        row = db.execute('SELECT log_json FROM care_tourenlog WHERE id=?', [row_id]).fetchone()
    if not row:
        return jsonify({'ok': True, 'log': None})
    return jsonify({'ok': True, 'log': json.loads(row['log_json'])})


@app.route('/api/care/tourenlog/<datum>', methods=['PUT'])
def care_tourenlog_save(datum):
    err = _require_care_or_admin()
    if err: return err
    cg_id = session.get('user_id')
    d = request.get_json(silent=True) or {}
    row_id = cg_id + '_' + datum
    log_data = d.get('log') if 'log' in d else d
    with get_db() as db:
        if USE_PG:
            db.execute(
                '''INSERT INTO care_tourenlog (id,caregiver_id,datum,log_json,updated_at)
                   VALUES (?,?,?,?,CURRENT_TIMESTAMP)
                   ON CONFLICT (id) DO UPDATE SET log_json=EXCLUDED.log_json, updated_at=EXCLUDED.updated_at''',
                [row_id, cg_id, datum, json.dumps(log_data)]
            )
        else:
            db.execute(
                "INSERT OR REPLACE INTO care_tourenlog (id,caregiver_id,datum,log_json,updated_at) "
                "VALUES (?,?,?,?,datetime('now','localtime'))",
                [row_id, cg_id, datum, json.dumps(log_data)]
            )
        db.commit()
    return jsonify({'ok': True})


# ── Care: Verträge & digitale Signaturen ─────────────────────────────────────

VERTRAEGE_DIR = os.path.join(UPLOAD_DIR, 'vertraege')
os.makedirs(VERTRAEGE_DIR, exist_ok=True)

@app.route('/api/care/vertraege')
def care_vertraege_list():
    err = _require_care_or_admin()
    if err: return err
    cg_id = session.get('user_id') or ''
    with get_db() as db:
        rows = db.execute(
            'SELECT v.*, '
            '(SELECT COUNT(*) FROM vertrag_signaturen s WHERE s.vertrag_id=v.id) as signatur_anzahl '
            'FROM vertraege v WHERE v.caregiver_id=? AND v.aktiv=1 ORDER BY v.erstellt_am DESC',
            [cg_id]
        ).fetchall()
    return jsonify({'ok': True, 'vertraege': [dict(r) for r in rows]})

@app.route('/api/care/vertraege', methods=['POST'])
def care_vertraege_upload():
    err = _require_care_or_admin()
    if err: return err
    import datetime as _dt
    cg_id   = session.get('user_id') or ''
    cg_name = session.get('username') or session.get('caregiver_name') or ''
    titel   = request.form.get('titel', '').strip()
    if not titel:
        return jsonify({'ok': False, 'error': 'Titel fehlt'}), 400
    f = request.files.get('datei')
    if not f or not f.filename.lower().endswith('.pdf'):
        return jsonify({'ok': False, 'error': 'Nur PDF-Dateien erlaubt'}), 400
    vid = 'vtr_' + uuid.uuid4().hex[:12]
    folder = os.path.join(VERTRAEGE_DIR, cg_id)
    os.makedirs(folder, exist_ok=True)
    fname = vid + '.pdf'
    fpath = os.path.join(folder, fname)
    f.save(fpath)
    now = _dt.datetime.now().isoformat(timespec='seconds')
    with get_db() as db:
        db.execute(
            'INSERT INTO vertraege (id,caregiver_id,caregiver_name,titel,datei_pfad,erstellt_am,aktiv) '
            'VALUES (?,?,?,?,?,?,1)',
            [vid, cg_id, cg_name, titel, fpath, now]
        )
        db.commit()
    return jsonify({'ok': True, 'id': vid})

@app.route('/api/care/vertraege/<vid>', methods=['DELETE'])
def care_vertraege_delete(vid):
    err = _require_care_or_admin()
    if err: return err
    cg_id = session.get('user_id') or ''
    with get_db() as db:
        row = db.execute('SELECT * FROM vertraege WHERE id=? AND caregiver_id=?', [vid, cg_id]).fetchone()
        if not row:
            return jsonify({'ok': False, 'error': 'Nicht gefunden'}), 404
        db.execute('UPDATE vertraege SET aktiv=0 WHERE id=?', [vid])
        db.commit()
    return jsonify({'ok': True})

@app.route('/api/care/vertraege/<vid>/download')
def care_vertraege_download(vid):
    err = _require_care_or_admin()
    if err: return err
    cg_id = session.get('user_id') or ''
    with get_db() as db:
        row = db.execute('SELECT * FROM vertraege WHERE id=? AND caregiver_id=?', [vid, cg_id]).fetchone()
    if not row or not os.path.isfile(row['datei_pfad']):
        return jsonify({'error': 'Nicht gefunden'}), 404
    folder = os.path.dirname(row['datei_pfad'])
    filename = os.path.basename(row['datei_pfad'])
    return send_from_directory(folder, filename, as_attachment=True,
                               download_name=row['titel'] + '.pdf')

@app.route('/api/care/vertraege/<vid>/signatur-link', methods=['POST'])
def care_vertraege_signatur_link(vid):
    err = _require_care_or_admin()
    if err: return err
    cg_id = session.get('user_id') or ''
    with get_db() as db:
        row = db.execute('SELECT * FROM vertraege WHERE id=? AND caregiver_id=? AND aktiv=1', [vid, cg_id]).fetchone()
        if not row:
            return jsonify({'ok': False, 'error': 'Nicht gefunden'}), 404
        token = uuid.uuid4().hex
        db.execute(
            'INSERT INTO vertrag_signaturen (id,vertrag_id,token,token_verwendet) VALUES (?,?,?,0)',
            ['sig_' + uuid.uuid4().hex[:12], vid, token]
        )
        db.commit()
    return jsonify({'ok': True, 'token': token})

@app.route('/api/care/vertrag-signaturen/<vid>')
def care_vertrag_signaturen(vid):
    err = _require_care_or_admin()
    if err: return err
    cg_id = session.get('user_id') or ''
    with get_db() as db:
        vrow = db.execute('SELECT id FROM vertraege WHERE id=? AND caregiver_id=?', [vid, cg_id]).fetchone()
        if not vrow:
            return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
        rows = db.execute(
            'SELECT id,patient_name,signiert_am,token_verwendet,ip_adresse FROM vertrag_signaturen '
            'WHERE vertrag_id=? ORDER BY signiert_am DESC',
            [vid]
        ).fetchall()
    return jsonify({'ok': True, 'signaturen': [dict(r) for r in rows]})

# ── Öffentlich: Vertrag anzeigen & signieren ──────────────────────────────────

@app.route('/api/vertrag/info/<token>')
def vertrag_info_public(token):
    with get_db() as db:
        sig = db.execute(
            'SELECT s.*,v.titel,v.datei_pfad,v.caregiver_name '
            'FROM vertrag_signaturen s JOIN vertraege v ON v.id=s.vertrag_id '
            'WHERE s.token=?', [token]
        ).fetchone()
    if not sig:
        return jsonify({'ok': False, 'error': 'Ungültiger Link'}), 404
    if sig['token_verwendet'] and sig['patient_name']:
        return jsonify({'ok': False, 'error': 'Dieser Link wurde bereits verwendet', 'bereits_signiert': True}), 410
    return jsonify({
        'ok': True,
        'titel': sig['titel'],
        'caregiver_name': sig['caregiver_name'],
        'bereits_signiert': bool(sig['token_verwendet'] and sig['patient_name'])
    })

@app.route('/api/vertrag/pdf/<token>')
def vertrag_pdf_public(token):
    with get_db() as db:
        sig = db.execute(
            'SELECT s.*,v.datei_pfad FROM vertrag_signaturen s JOIN vertraege v ON v.id=s.vertrag_id '
            'WHERE s.token=?', [token]
        ).fetchone()
    if not sig or not os.path.isfile(sig['datei_pfad']):
        return jsonify({'error': 'Nicht gefunden'}), 404
    folder = os.path.dirname(sig['datei_pfad'])
    filename = os.path.basename(sig['datei_pfad'])
    return send_from_directory(folder, filename, mimetype='application/pdf')

@app.route('/api/vertrag/signieren/<token>', methods=['POST'])
def vertrag_signieren_public(token):
    import datetime as _dt
    data = request.get_json(silent=True) or {}
    patient_name = (data.get('patient_name') or '').strip()
    unterschrift  = (data.get('unterschrift') or '').strip()
    if not patient_name or not unterschrift:
        return jsonify({'ok': False, 'error': 'Name und Unterschrift erforderlich'}), 400
    with get_db() as db:
        sig = db.execute(
            'SELECT s.*,v.titel FROM vertrag_signaturen s JOIN vertraege v ON v.id=s.vertrag_id '
            'WHERE s.token=?', [token]
        ).fetchone()
        if not sig:
            return jsonify({'ok': False, 'error': 'Ungültiger Link'}), 404
        if sig['token_verwendet'] and sig['patient_name']:
            return jsonify({'ok': False, 'error': 'Bereits signiert'}), 410
        now = _dt.datetime.now().isoformat(timespec='seconds')
        ip  = request.headers.get('X-Forwarded-For', request.remote_addr or '')
        db.execute(
            'UPDATE vertrag_signaturen SET patient_name=?,unterschrift_data=?,signiert_am=?,'
            'token_verwendet=1,ip_adresse=? WHERE token=?',
            [patient_name, unterschrift, now, ip, token]
        )
        db.commit()
    return jsonify({'ok': True, 'signiert_am': now})

# ── Client: Profil ────────────────────────────────────────────────────────────

@app.route('/api/client/profil')
def client_profil_get():
    pat_id = session.get('patient_id') or session.get('user_id')
    if not pat_id:
        return jsonify({'error': 'Nicht angemeldet'}), 401
    with get_db() as db:
        row = db.execute('SELECT * FROM patients WHERE id=?', [pat_id]).fetchone()
    if not row:
        return jsonify({'ok': True, 'profil': {}})
    extra = {}
    try:
        raw = row['profil_extra'] if row.get('profil_extra') else '{}'
        raw = dec(raw)  # Fernet-Entschlüsselung (graceful fallback für unverschlüsselte Altdaten)
        extra = json.loads(raw) if raw and raw not in ('null', '') else {}
    except Exception:
        pass
    profil = {
        'id': row['id'],
        'firstName': row['vorname'] or '',
        'lastName': row['nachname'] or '',
        'email': row.get('email', '') or '',
        'gender': row.get('gender', '') or '',
        'street': row.get('address', '') or '',
        'zip': row.get('plz', '') or '',
        'city': row.get('ort', '') or '',
        'hauptgrund': row.get('hauptgrund', '') or '',
        'haeufigkeit': row.get('haeufigkeit', '') or '',
        'mobility': extra.get('mobility', ''),
        'problem': row.get('hauptgrund', '') or '',
    }
    profil.update(extra)
    return jsonify({'ok': True, 'profil': profil})


@app.route('/api/client/profil', methods=['PUT'])
def client_profil_save():
    pat_id = session.get('patient_id') or session.get('user_id')
    if not pat_id:
        return jsonify({'error': 'Nicht angemeldet'}), 401
    d = request.get_json(silent=True) or {}
    base_keys = {'id', 'firstName', 'lastName', 'email', 'gender', 'street', 'zip', 'city', 'hauptgrund', 'haeufigkeit', 'mobility', 'problem'}
    extra = {k: v for k, v in d.items() if k not in base_keys}
    if d.get('problem') and not d.get('hauptgrund'):
        d['hauptgrund'] = d['problem']
    with get_db() as db:
        db.execute(
            'UPDATE patients SET vorname=?,nachname=?,gender=?,address=?,plz=?,ort=?,hauptgrund=?,haeufigkeit=?,profil_extra=? WHERE id=?',
            [d.get('firstName', ''), d.get('lastName', ''), d.get('gender', ''),
             d.get('street', ''), d.get('zip', ''), d.get('city', ''),
             d.get('hauptgrund', '') or d.get('problem', ''), d.get('haeufigkeit', ''),
             enc(json.dumps(extra)), pat_id]
        )
        db.commit()
    return jsonify({'ok': True})


# ── Passwort-Reset (öffentlicher Bereich – Klienten) ─────────────────────────

@app.route('/api/client/passwort-vergessen', methods=['POST'])
def client_passwort_vergessen():
    data  = request.get_json(silent=True) or {}
    email = data.get('email', '').strip().lower()
    if not email:
        return jsonify({'ok': False, 'error': 'E-Mail erforderlich'}), 400
    with get_db() as db:
        patient = db.execute('SELECT id, vorname FROM patients WHERE email=?', [email]).fetchone()
    # Kein Hinweis ob E-Mail existiert (Security – kein User-Enumeration)
    if not patient:
        return jsonify({'ok': True})
    token = uuid.uuid4().hex
    from datetime import datetime, timedelta
    expires = (datetime.utcnow() + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
    with get_db() as db:
        db.execute('DELETE FROM public_password_reset_tokens WHERE email=?', [email])
        db.execute(
            'INSERT INTO public_password_reset_tokens (id,patient_id,email,token,expires_at) VALUES (?,?,?,?,?)',
            [uuid.uuid4().hex, patient['id'], email, token, expires]
        )
        db.commit()
    host = request.host_url.rstrip('/')
    reset_url = f"{host}/passwort-reset.html?token={token}"
    vorname = patient['vorname'] or 'Klient/in'
    text_body = (
        f"Hallo {vorname},\n\n"
        f"du hast eine Passwort-Zurücksetzung für dein Nursy-Konto angefordert.\n\n"
        f"Klicke auf folgenden Link, um ein neues Passwort zu setzen (gültig 1 Stunde):\n{reset_url}\n\n"
        f"Falls du diese Anfrage nicht gestellt hast, kannst du diese E-Mail ignorieren.\n\n"
        f"Mit freundlichen Grüßen\nDein Nursy-Team"
    )
    html_body = f"""<!DOCTYPE html><html><body style="font-family:sans-serif;color:#1a2e6e;max-width:520px;margin:auto;padding:24px">
<h2 style="color:#0f2744;">Passwort zurücksetzen</h2>
<p>Hallo <strong>{vorname}</strong>,</p>
<p>du hast eine Passwort-Zurücksetzung für dein <strong>Nursy</strong>-Konto angefordert.</p>
<p style="margin:24px 0">
  <a href="{reset_url}" style="background:#0f2744;color:#fff;padding:12px 28px;border-radius:8px;text-decoration:none;font-weight:700;display:inline-block;">
    Passwort zurücksetzen
  </a>
</p>
<p style="font-size:.85rem;color:#555;">Der Link ist <strong>1 Stunde</strong> gültig.<br>
Falls du diese Anfrage nicht gestellt hast, kannst du diese E-Mail einfach ignorieren.</p>
<hr style="border:none;border-top:1px solid #eee;margin:24px 0"/>
<p style="font-size:.75rem;color:#999;">Nursy – Fürsorge mit Herz &nbsp;|&nbsp; Akut Plus Pflege</p>
</body></html>"""
    ok, err = send_email(email, 'Nursy – Passwort zurücksetzen', text_body, html_body)
    if not ok:
        app.logger.warning(f'Passwort-Reset E-Mail Fehler: {err}')
    return jsonify({'ok': True})


@app.route('/api/client/passwort-reset', methods=['POST'])
def client_passwort_reset():
    data   = request.get_json(silent=True) or {}
    token  = data.get('token', '').strip()
    new_pw = data.get('password', '')
    if not token or not new_pw:
        return jsonify({'ok': False, 'error': 'Token und neues Passwort erforderlich'}), 400
    if len(new_pw) < 8:
        return jsonify({'ok': False, 'error': 'Passwort muss mindestens 8 Zeichen haben'}), 400
    from datetime import datetime
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    with get_db() as db:
        row = db.execute(
            "SELECT * FROM public_password_reset_tokens WHERE token=? AND used=0 AND expires_at > ?",
            [token, now]
        ).fetchone()
        if not row:
            return jsonify({'ok': False, 'error': 'Link ungültig oder abgelaufen. Bitte erneut anfordern.'}), 400
        db.execute('UPDATE patients SET password_hash=? WHERE id=?', [hash_pw(new_pw), row['patient_id']])
        db.execute('UPDATE public_password_reset_tokens SET used=1 WHERE token=?', [token])
        db.commit()
    return jsonify({'ok': True, 'info': 'Passwort erfolgreich geändert.'})


# ══════════════════════════════════════════════════════════════════════════════
# ── Matching-System (Nursy öffentlicher Bereich) ──────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

# ── Patient: Status & Vorschläge ─────────────────────────────────────────────

@app.route('/api/matching/status')
def matching_status():
    pid = session.get('patient_id')
    if not pid:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    with get_db() as db:
        anfrage = db.execute(
            "SELECT * FROM matching_anfragen WHERE patient_id=? AND status IN ('aktiv','angenommen') ORDER BY created_at DESC LIMIT 1",
            [pid]
        ).fetchone()
        verbindung = db.execute(
            "SELECT * FROM matching_verbindungen WHERE patient_id=? AND aktiv=1 LIMIT 1",
            [pid]
        ).fetchone()
        caregiver = None
        if verbindung:
            cg = db.execute(
                "SELECT id,vorname,nachname,email,bezirk,ort,qualifikation,address,plz FROM caregivers WHERE id=?",
                [verbindung['caregiver_id']]
            ).fetchone()
            if cg:
                caregiver = dict(cg)
    anf = dict(anfrage) if anfrage else None
    if anf:
        anf['pflegebedarf'] = dec(anf.get('pflegebedarf') or '')
        try: anf['leistungen'] = json.loads(dec(anf.get('leistungen') or '[]'))
        except: anf['leistungen'] = []
        try: anf['schicht_wunsch'] = json.loads(anf.get('schicht_wunsch') or '[]')
        except: anf['schicht_wunsch'] = []
    return jsonify({'ok': True, 'anfrage': anf, 'verbunden': bool(verbindung), 'caregiver': caregiver})


@app.route('/api/matching/vorschlaege')
def matching_vorschlaege():
    pid = session.get('patient_id')
    if not pid:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    bezirk = request.args.get('bezirk', '').strip()
    with get_db() as db:
        if bezirk:
            rows = db.execute(
                "SELECT id,vorname,bezirk,ort,plz,qualifikation FROM caregivers WHERE bezirk=? ORDER BY vorname",
                [bezirk]
            ).fetchall()
            if not rows:
                rows = db.execute(
                    "SELECT id,vorname,bezirk,ort,plz,qualifikation FROM caregivers ORDER BY vorname LIMIT 30"
                ).fetchall()
        else:
            rows = db.execute(
                "SELECT id,vorname,bezirk,ort,plz,qualifikation FROM caregivers ORDER BY vorname LIMIT 30"
            ).fetchall()
        verbunden_ids = {r['caregiver_id'] for r in db.execute(
            "SELECT caregiver_id FROM matching_verbindungen WHERE aktiv=1"
        ).fetchall()}
    result = [{
        'id': r['id'],
        'vorname': r['vorname'],
        'bezirk': r['bezirk'] or '',
        'ort': r['ort'] or '',
        'qualifikation': r['qualifikation'] or '',
        'hat_verbindung': r['id'] in verbunden_ids,
    } for r in rows]
    return jsonify({'ok': True, 'vorschlaege': result})


@app.route('/api/matching/anfrage', methods=['POST'])
def matching_anfrage_erstellen():
    pid = session.get('patient_id')
    if not pid:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    d = request.get_json(silent=True) or {}
    with get_db() as db:
        existing = db.execute(
            "SELECT id FROM matching_anfragen WHERE patient_id=? AND status='aktiv' LIMIT 1",
            [pid]
        ).fetchone()
        if existing:
            db.execute(
                "UPDATE matching_anfragen SET pflegebedarf=?,leistungen=?,bezirk=?,schicht_wunsch=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                [enc(d.get('pflegebedarf','')), enc(json.dumps(d.get('leistungen',[]))),
                 d.get('bezirk',''), json.dumps(d.get('schicht_wunsch',[])), existing['id']]
            )
            anfrage_id = existing['id']
        else:
            anfrage_id = 'ma' + uuid.uuid4().hex[:10]
            db.execute(
                "INSERT INTO matching_anfragen (id,patient_id,pflegebedarf,leistungen,bezirk,schicht_wunsch,modus,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)",
                [anfrage_id, pid, enc(d.get('pflegebedarf','')), enc(json.dumps(d.get('leistungen',[]))),
                 d.get('bezirk',''), json.dumps(d.get('schicht_wunsch',[])), 'entwurf', 'aktiv']
            )
        db.commit()
    return jsonify({'ok': True, 'anfrage_id': anfrage_id})


@app.route('/api/matching/anfrage/freistellen', methods=['POST'])
def matching_anfrage_freistellen():
    pid = session.get('patient_id')
    if not pid:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    with get_db() as db:
        anfrage = db.execute(
            "SELECT id FROM matching_anfragen WHERE patient_id=? AND status='aktiv' LIMIT 1", [pid]
        ).fetchone()
        if not anfrage:
            return jsonify({'ok': False, 'error': 'Keine aktive Anfrage gefunden'}), 404
        db.execute(
            "UPDATE matching_anfragen SET modus='offen',ziel_caregiver_id='',updated_at=CURRENT_TIMESTAMP WHERE id=?",
            [anfrage['id']]
        )
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/matching/anfrage/ziel/<cg_id>', methods=['POST'])
def matching_anfrage_ziel(cg_id):
    pid = session.get('patient_id')
    if not pid:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    with get_db() as db:
        cg = db.execute("SELECT id FROM caregivers WHERE id=?", [cg_id]).fetchone()
        if not cg:
            return jsonify({'ok': False, 'error': 'Pflegekraft nicht gefunden'}), 404
        anfrage = db.execute(
            "SELECT id FROM matching_anfragen WHERE patient_id=? AND status='aktiv' LIMIT 1", [pid]
        ).fetchone()
        if not anfrage:
            return jsonify({'ok': False, 'error': 'Keine aktive Anfrage gefunden'}), 404
        db.execute(
            "UPDATE matching_anfragen SET modus='ziel',ziel_caregiver_id=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
            [cg_id, anfrage['id']]
        )
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/matching/anfrage', methods=['DELETE'])
def matching_anfrage_zurueckziehen():
    pid = session.get('patient_id')
    if not pid:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    with get_db() as db:
        db.execute(
            "UPDATE matching_anfragen SET status='zurueckgezogen',updated_at=CURRENT_TIMESTAMP WHERE patient_id=? AND status='aktiv'",
            [pid]
        )
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/matching/verbindung/pfleger')
def matching_verbindung_pfleger():
    pid = session.get('patient_id')
    if not pid:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    with get_db() as db:
        v = db.execute(
            "SELECT * FROM matching_verbindungen WHERE patient_id=? AND aktiv=1 LIMIT 1", [pid]
        ).fetchone()
        if not v:
            return jsonify({'ok': True, 'verbunden': False})
        cg = db.execute("SELECT * FROM caregivers WHERE id=?", [v['caregiver_id']]).fetchone()
        if not cg:
            return jsonify({'ok': True, 'verbunden': False})
    return jsonify({'ok': True, 'verbunden': True, 'pfleger': {
        'id': cg['id'],
        'vorname': cg['vorname'], 'nachname': cg['nachname'],
        'email': cg['email'] or '',
        'bezirk': cg['bezirk'] or '', 'ort': cg['ort'] or '',
        'address': cg['address'] or '', 'plz': cg['plz'] or '',
        'qualifikation': cg['qualifikation'] or '',
        'verbunden_am': v['verbunden_am'] or '',
    }})


# ── Caregiver: Matching ───────────────────────────────────────────────────────

@app.route('/api/care/matching/status')
def care_matching_status():
    err = _require_care_or_admin()
    if err: return err
    cg_id = session.get('user_id')
    with get_db() as db:
        offene      = db.execute("SELECT COUNT(*) AS c FROM matching_anfragen WHERE modus='offen' AND status='aktiv'").fetchone()['c']
        eingehende  = db.execute("SELECT COUNT(*) AS c FROM matching_anfragen WHERE modus='ziel' AND ziel_caregiver_id=? AND status='aktiv'", [cg_id]).fetchone()['c']
        verbindungen = db.execute("SELECT COUNT(*) AS c FROM matching_verbindungen WHERE caregiver_id=? AND aktiv=1", [cg_id]).fetchone()['c']
    return jsonify({'ok': True, 'offene': offene, 'eingehende': eingehende, 'verbindungen': verbindungen})


@app.route('/api/care/matching/offene')
def care_matching_offene():
    err = _require_care_or_admin()
    if err: return err
    with get_db() as db:
        rows = db.execute(
            "SELECT id,pflegebedarf,leistungen,bezirk,schicht_wunsch,created_at FROM matching_anfragen WHERE modus='offen' AND status='aktiv' ORDER BY created_at DESC"
        ).fetchall()
    result = []
    for r in rows:
        item = {'id': r['id'], 'pflegebedarf': dec(r['pflegebedarf'] or ''), 'bezirk': r['bezirk'] or '', 'created_at': r['created_at'] or ''}
        try: item['leistungen'] = json.loads(dec(r['leistungen'] or '[]'))
        except: item['leistungen'] = []
        try: item['schicht_wunsch'] = json.loads(r['schicht_wunsch'] or '[]')
        except: item['schicht_wunsch'] = []
        result.append(item)
    return jsonify({'ok': True, 'anfragen': result})


@app.route('/api/care/matching/eingehende')
def care_matching_eingehende():
    err = _require_care_or_admin()
    if err: return err
    cg_id = session.get('user_id')
    with get_db() as db:
        rows = db.execute(
            "SELECT id,pflegebedarf,leistungen,bezirk,schicht_wunsch,created_at FROM matching_anfragen WHERE modus='ziel' AND ziel_caregiver_id=? AND status='aktiv' ORDER BY created_at DESC",
            [cg_id]
        ).fetchall()
    result = []
    for r in rows:
        item = {'id': r['id'], 'pflegebedarf': dec(r['pflegebedarf'] or ''), 'bezirk': r['bezirk'] or '', 'created_at': r['created_at'] or ''}
        try: item['leistungen'] = json.loads(dec(r['leistungen'] or '[]'))
        except: item['leistungen'] = []
        try: item['schicht_wunsch'] = json.loads(r['schicht_wunsch'] or '[]')
        except: item['schicht_wunsch'] = []
        result.append(item)
    return jsonify({'ok': True, 'anfragen': result})


@app.route('/api/care/matching/annehmen/<anfrage_id>', methods=['POST'])
def care_matching_annehmen(anfrage_id):
    err = _require_care_or_admin()
    if err: return err
    cg_id = session.get('user_id')
    with get_db() as db:
        anfrage = db.execute(
            "SELECT * FROM matching_anfragen WHERE id=? AND status='aktiv' AND (modus='offen' OR (modus='ziel' AND ziel_caregiver_id=?))",
            [anfrage_id, cg_id]
        ).fetchone()
        if not anfrage:
            return jsonify({'ok': False, 'error': 'Anfrage nicht (mehr) verfügbar – vielleicht war jemand schneller'}), 409
        db.execute(
            "UPDATE matching_anfragen SET status='angenommen',angenommen_von=?,angenommen_am=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP WHERE id=? AND status='aktiv'",
            [cg_id, anfrage_id]
        )
        vid = 'mv' + uuid.uuid4().hex[:10]
        if USE_PG:
            db.execute(
                "INSERT INTO matching_verbindungen (id,patient_id,caregiver_id,anfrage_id,verbunden_am,aktiv) VALUES (?,?,?,?,CURRENT_TIMESTAMP,1) ON CONFLICT (patient_id) DO UPDATE SET caregiver_id=EXCLUDED.caregiver_id,anfrage_id=EXCLUDED.anfrage_id,verbunden_am=EXCLUDED.verbunden_am,aktiv=1",
                [vid, anfrage['patient_id'], cg_id, anfrage_id]
            )
        else:
            db.execute(
                "INSERT OR REPLACE INTO matching_verbindungen (id,patient_id,caregiver_id,anfrage_id,verbunden_am,aktiv) VALUES (?,?,?,?,datetime('now','localtime'),1)",
                [vid, anfrage['patient_id'], cg_id, anfrage_id]
            )
        pat = db.execute("SELECT * FROM patients WHERE id=?", [anfrage['patient_id']]).fetchone()
        if pat:
            pat_json = json.dumps({
                'id': pat['id'], 'vorname': pat['vorname'], 'nachname': pat['nachname'],
                'email': pat['email'] or '', 'gender': pat['gender'] or '',
                'address': pat['address'] or '', 'plz': pat['plz'] or '',
                'ort': pat['ort'] or '', 'bezirk': pat['bezirk'] or '',
                'birth': pat['birth'] or '', 'hauptgrund': pat['hauptgrund'] or '',
                'haeufigkeit': pat['haeufigkeit'] or '',
            })
            row_id = cg_id + '_' + pat['id']
            if USE_PG:
                db.execute(
                    "INSERT INTO care_accepted_patients (id,caregiver_id,patient_id,patient_json,accepted_at,active) VALUES (?,?,?,?,CURRENT_TIMESTAMP,1) ON CONFLICT (id) DO UPDATE SET patient_json=EXCLUDED.patient_json,active=1,accepted_at=EXCLUDED.accepted_at",
                    [row_id, cg_id, pat['id'], pat_json]
                )
            else:
                db.execute(
                    "INSERT OR REPLACE INTO care_accepted_patients (id,caregiver_id,patient_id,patient_json,accepted_at,active) VALUES (?,?,?,?,datetime('now','localtime'),1)",
                    [row_id, cg_id, pat['id'], pat_json]
                )
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/care/matching/ablehnen/<anfrage_id>', methods=['POST'])
def care_matching_ablehnen(anfrage_id):
    err = _require_care_or_admin()
    if err: return err
    cg_id = session.get('user_id')
    with get_db() as db:
        anfrage = db.execute(
            "SELECT id FROM matching_anfragen WHERE id=? AND modus='ziel' AND ziel_caregiver_id=? AND status='aktiv'",
            [anfrage_id, cg_id]
        ).fetchone()
        if not anfrage:
            return jsonify({'ok': False, 'error': 'Anfrage nicht gefunden'}), 404
        db.execute(
            "UPDATE matching_anfragen SET modus='entwurf',ziel_caregiver_id='',updated_at=CURRENT_TIMESTAMP WHERE id=?",
            [anfrage_id]
        )
        db.commit()
    return jsonify({'ok': True})


# ══════════════════════════════════════════════════════════════════════════════
# ── Fahrzeug-Bestätigung (internes Modul) ─────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════
import io as _fbio
from pathlib import Path as _fbPath
import re as _fbre

FORMULARE_DIR = _fbPath(BASE_DIR) / 'formulare'
try:
    FORMULARE_DIR.mkdir(exist_ok=True)
except Exception:
    pass

def _fb_sanitize(s):
    return _fbre.sub(r'[^\w\-.]', '_', str(s or 'x').strip())[:40]

def _fb_form_dir(bundesland, bezirk, datum):
    p = FORMULARE_DIR / _fb_sanitize(bundesland) / _fb_sanitize(bezirk) / _fb_sanitize(datum)
    p.mkdir(parents=True, exist_ok=True)
    return p

_FB_CHECKS = ['cb_uebernommen','cb_sauber','cb_schaeden','cb_material',
              'cb_med_geprueft','cb_med_verwendbar','cb_haftung',
              'cb_selbstbehalt','cb_rueckgabe','cb_eigen_haftung',
              'agb_akzeptiert']
_FB_LABELS = [
    'Fahrzeug ordnungsgemäß übernommen',
    'Fahrzeug sauber übernommen',
    'Keine sichtbaren Schäden oder Schäden wurden dokumentiert',
    'Material vollständig vorhanden',
    'Medizinische Produkte überprüft',
    'Medizinische Produkte können fachgerecht verwendet werden',
    'Haftungsregelung gelesen und akzeptiert',
    'Selbstverschuldeter Fahrzeugschaden: 1/3 des Versicherungs-Selbstbehalts',
    'Fahrzeug, Material und med. Produkte nach Dienstende sauber hinterlassen',
    'Jede Pflegekraft haftet im gesetzlichen Rahmen für eigenes Fehlverhalten',
    'Dienst- und Bereitschaftsvereinbarung gelesen und akzeptiert',
]

def _now_vienna():
    """Gibt aktuelle Datetime in Österreich/Wien zurück (naive, für DB-Vergleiche)."""
    try:
        from zoneinfo import ZoneInfo
        import datetime as _dt
        return _dt.datetime.now(ZoneInfo('Europe/Vienna')).replace(tzinfo=None)
    except Exception:
        import datetime as _dt
        return _dt.datetime.now()

def _fb_generate_pdf(f):
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                        Table, TableStyle, Image, HRFlowable)
        from reportlab.lib.enums import TA_CENTER
        import base64
        buf = _fbio.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, rightMargin=1.5*cm,
                                leftMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
        styles = getSampleStyleSheet()
        dark  = colors.HexColor('#0f2744')
        mid   = colors.HexColor('#2563eb')
        gray  = colors.HexColor('#6b7280')
        lgray = colors.HexColor('#f8fafc')
        h1 = ParagraphStyle('h1', parent=styles['Heading1'], textColor=dark, fontSize=16, spaceAfter=2)
        h2 = ParagraphStyle('h2', parent=styles['Heading2'], textColor=mid, fontSize=11, spaceAfter=4, spaceBefore=10)
        small  = ParagraphStyle('sm', parent=styles['Normal'], fontSize=7.5, textColor=gray, leading=11)
        normal = ParagraphStyle('n',  parent=styles['Normal'], fontSize=9, spaceAfter=2, leading=13)
        legal  = ParagraphStyle('lg', parent=styles['Normal'], fontSize=8, textColor=gray, leading=11)
        center = ParagraphStyle('ct', parent=styles['Normal'], fontSize=7.5, textColor=gray, alignment=TA_CENTER)
        story = []
        story.append(Paragraph('Akut Plus Pflegenotdienst', h1))
        story.append(Paragraph('Dienst- und Fahrzeugbestätigung', ParagraphStyle('sub', parent=styles['Normal'], fontSize=12, textColor=mid, spaceAfter=2)))
        story.append(Paragraph(f"Formular-ID: {f.get('id','–')}", small))
        story.append(HRFlowable(width='100%', thickness=1, color=mid, spaceAfter=8))
        story.append(Paragraph('Dienstdaten', h2))
        info = [
            ['Pflegekraft:', f.get('caregiver_name','–'), 'Dienstnummer:', f.get('dienstnummer','–')],
            ['Fahrzeug:',   f.get('fahrzeug','–'),       'Kennzeichen:',  f.get('kennzeichen','–')],
            ['Bundesland:', f.get('bundesland','–'),       'Bezirk:',       f.get('bezirk','–')],
            ['Datum:',      f.get('datum','–'),            'Uhrzeit:',      f.get('uhrzeit','–')],
        ]
        it = Table(info, colWidths=[3*cm, 5.8*cm, 3*cm, 5.8*cm])
        it.setStyle(TableStyle([
            ('FONTNAME', (0,0),(-1,-1), 'Helvetica'), ('FONTSIZE', (0,0),(-1,-1), 9),
            ('FONTNAME', (0,0),(0,-1), 'Helvetica-Bold'), ('FONTNAME', (2,0),(2,-1), 'Helvetica-Bold'),
            ('TEXTCOLOR', (0,0),(0,-1), dark), ('TEXTCOLOR', (2,0),(2,-1), dark),
            ('ROWBACKGROUNDS', (0,0),(-1,-1), [lgray, colors.white]),
            ('GRID', (0,0),(-1,-1), 0.25, colors.HexColor('#e5e7eb')), ('PADDING', (0,0),(-1,-1), 5),
        ]))
        story.append(it)
        story.append(Paragraph('Bestätigungen', h2))
        cb_data = [['✓/✗', 'Bestätigung']]
        for key, label in zip(_FB_CHECKS, _FB_LABELS):
            cb_data.append(['✓' if f.get(key) else '✗', label])
        ct = Table(cb_data, colWidths=[1.2*cm, 16.4*cm])
        ts = [('FONTNAME', (0,0),(-1,-1), 'Helvetica'), ('FONTSIZE', (0,0),(-1,-1), 9),
              ('FONTNAME', (0,0),(-1,0), 'Helvetica-Bold'),
              ('BACKGROUND', (0,0),(-1,0), dark), ('TEXTCOLOR', (0,0),(-1,0), colors.white),
              ('ALIGN', (0,0),(0,-1), 'CENTER'),
              ('ROWBACKGROUNDS', (0,1),(-1,-1), [lgray, colors.white]),
              ('GRID', (0,0),(-1,-1), 0.25, colors.HexColor('#e5e7eb')), ('PADDING', (0,0),(-1,-1), 5)]
        for i, key in enumerate(_FB_CHECKS, 1):
            col = colors.HexColor('#16a34a') if f.get(key) else colors.HexColor('#dc2626')
            ts.append(('TEXTCOLOR', (0,i),(0,i), col))
        ct.setStyle(TableStyle(ts))
        story.append(ct)
        bem = (f.get('bemerkungen') or '').strip()
        if bem:
            story.append(Paragraph('Bemerkungen', h2))
            story.append(Paragraph(bem, normal))
        story.append(Spacer(1, 0.3*cm))
        story.append(HRFlowable(width='100%', thickness=0.5, color=gray))
        story.append(Spacer(1, 0.2*cm))
        story.append(Paragraph(
            'Mit meiner digitalen Unterschrift bestätige ich, dass ich die Dienst-, Haftungs-, '
            'Fahrzeug- und Materialregelungen gelesen, verstanden und akzeptiert habe. Ich bestätige '
            'außerdem, dass ich eigenverantwortlich handle und mit den verwendeten medizinischen '
            'Produkten und Materialien fachgerecht umgehen kann.', legal))
        sig = f.get('unterschrift_data', '')
        if sig and sig.startswith('data:image'):
            story.append(Paragraph('Digitale Unterschrift', h2))
            try:
                _, b64 = sig.split(',', 1)
                img_bytes = base64.b64decode(b64)
                img_buf = _fbio.BytesIO(img_bytes)
                story.append(Image(img_buf, width=8*cm, height=3*cm))
            except Exception:
                story.append(Paragraph('[Unterschrift konnte nicht geladen werden]', small))
        story.append(Spacer(1, 0.4*cm))
        story.append(Paragraph(f"Gespeichert: {f.get('gespeichert_am','–')}  |  ID: {f.get('id','–')}", center))
        doc.build(story)
        buf.seek(0)
        return buf.getvalue()
    except Exception:
        return None


@app.route('/api/fahrzeug/aktuell')
def fahrzeug_aktuell():
    uid = session.get('portal_user_id') or session.get('user_id')
    if not uid:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    with get_db() as db:
        pb  = db.execute('SELECT vorname,nachname,dienstnummer,bezirk FROM portal_bewerbungen WHERE id=? AND status=?', [uid,'freigegeben']).fetchone()
        cg  = db.execute('SELECT vorname,nachname,dienstnummer,bezirk FROM caregivers WHERE id=?', [uid]).fetchone()
        fzn = session.get('fahrzeug') or ''
        fz_row = db.execute('SELECT name,typ,bundesland,bezirk,kennzeichen FROM fahrzeuge WHERE name=?', [fzn]).fetchone() if fzn else None
        today = time.strftime('%Y-%m-%d')
        dienst = db.execute("SELECT fahrzeug,art FROM portal_dienste WHERE user_id=? AND datum=? ORDER BY id DESC LIMIT 1", [uid, today]).fetchone()
    src = pb or cg or {}
    name = ((src.get('vorname') or '') + ' ' + (src.get('nachname') or '')).strip() if src else ''
    person = {'vorname': src.get('vorname',''), 'nachname': src.get('nachname',''),
              'dienstnummer': src.get('dienstnummer',''), 'bezirk': src.get('bezirk','')} if src else {}
    if not fzn and dienst and dienst['fahrzeug']:
        fzn = dienst['fahrzeug']
        if not fz_row:
            with get_db() as db:
                fz_row = db.execute('SELECT name,typ,bundesland,bezirk,kennzeichen FROM fahrzeuge WHERE name=?', [fzn]).fetchone()
    fz = {}
    if fz_row:
        fz = {'name': fz_row['name'], 'kennzeichen': fz_row.get('kennzeichen') or '',
              'bundesland': fz_row['bundesland'] or '', 'bezirk': fz_row['bezirk'] or person.get('bezirk','') or ''}
    elif fzn:
        fz = {'name': fzn, 'kennzeichen': '', 'bundesland': '', 'bezirk': person.get('bezirk','') or ''}
    return jsonify({'ok': True, 'name': name, 'person': person, 'fahrzeug': fz,
                    'today': today, 'now': time.strftime('%H:%M')})


@app.route('/api/fahrzeug/check')
def fahrzeug_check():
    """Prüft ob eine gültige Bestätigung der letzten 12 Stunden vorliegt (deckt Nachtdienste ab)."""
    uid = session.get('portal_user_id') or session.get('user_id')
    if not uid:
        return jsonify({'ok': False, 'signed': False}), 401
    import datetime as _dt
    fzn = session.get('fahrzeug') or ''
    now = _now_vienna()
    cutoff = (now - _dt.timedelta(hours=12)).strftime('%Y-%m-%d %H:%M:%S')
    with get_db() as db:
        row = db.execute(
            'SELECT id,fahrzeug,gespeichert_am FROM fahrzeug_bestaetigungen '
            'WHERE caregiver_id=? AND gespeichert_am>=? ORDER BY gespeichert_am DESC LIMIT 1',
            [uid, cutoff]).fetchone()
    if not row:
        return jsonify({'ok': True, 'signed': False})
    # Fahrzeug gewechselt → neue Bestätigung nötig
    if fzn and row['fahrzeug'] and row['fahrzeug'] != fzn:
        return jsonify({'ok': True, 'signed': False, 'reason': 'fahrzeug_gewechselt'})
    # Gültig – Ablaufzeit berechnen
    try:
        signed_dt  = _dt.datetime.strptime(row['gespeichert_am'], '%Y-%m-%d %H:%M:%S')
        expires_dt = signed_dt + _dt.timedelta(hours=12)
        remaining  = max(0.0, (expires_dt - now).total_seconds())
        h_rem = int(remaining // 3600)
        m_rem = int((remaining % 3600) // 60)
        expires_str = expires_dt.strftime('%H:%M')
        signed_str  = signed_dt.strftime('%H:%M')
    except Exception:
        h_rem = m_rem = None
        expires_str = signed_str = None
    return jsonify({
        'ok': True, 'signed': True, 'form_id': row['id'],
        'signed_at':       row['gespeichert_am'],
        'signed_time':     signed_str,
        'expires_at':      expires_str,
        'hours_remaining': h_rem,
        'mins_remaining':  m_rem,
    })


@app.route('/api/fahrzeug/bestaetigung', methods=['POST'])
def fahrzeug_bestaetigung_submit():
    uid = session.get('portal_user_id') or session.get('user_id')
    if not uid:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    data = request.get_json(silent=True) or {}
    if not data.get('unterschrift_data'):
        return jsonify({'ok': False, 'error': 'Unterschrift fehlt'}), 400
    for cb in _FB_CHECKS:
        if not data.get(cb):
            return jsonify({'ok': False, 'error': f'Pflichtbestätigung fehlt: {cb}'}), 400
    form_id  = 'FB-' + uuid.uuid4().hex[:10].upper()
    _now_v   = _now_vienna()
    now_ts   = _now_v.strftime('%Y-%m-%d %H:%M:%S')
    today    = _now_v.strftime('%Y-%m-%d')
    now_t    = _now_v.strftime('%H:%M')
    bundesland = data.get('bundesland') or ''
    bezirk     = data.get('bezirk')     or ''
    fahrzeug   = data.get('fahrzeug')   or ''
    dienstnr   = data.get('dienstnummer') or ''
    form_dir  = _fb_form_dir(bundesland or 'Unbekannt', bezirk or 'Unbekannt', today)
    file_stem = f"formular_{_fb_sanitize(dienstnr or 'x')}_{_fb_sanitize(fahrzeug or 'x')}_{today}_{now_t.replace(':','_')}"
    json_path = form_dir / (file_stem + '.json')
    pdf_path  = form_dir / (file_stem + '.pdf')
    foto_pfade = []
    try: foto_pfade = json.loads(data.get('foto_pfade') or '[]')
    except Exception: pass
    row = {'id': form_id, 'caregiver_id': uid, 'caregiver_name': data.get('caregiver_name',''),
           'dienstnummer': dienstnr, 'fahrzeug': fahrzeug, 'kennzeichen': data.get('kennzeichen',''),
           'bundesland': bundesland, 'bezirk': bezirk, 'datum': today, 'uhrzeit': now_t,
           'bemerkungen': data.get('bemerkungen',''), 'unterschrift_data': data.get('unterschrift_data',''),
           'foto_pfade': json.dumps(foto_pfade), 'formular_pfad': str(json_path), 'pdf_pfad': str(pdf_path),
           'gespeichert_am': now_ts, 'dienst_gestartet': 0, 'dienst_gestartet_am': ''}
    for cb in _FB_CHECKS:
        row[cb] = int(bool(data.get(cb)))
    cols = ['id','caregiver_id','caregiver_name','dienstnummer','fahrzeug','kennzeichen',
            'bundesland','bezirk','datum','uhrzeit'] + _FB_CHECKS + \
           ['bemerkungen','unterschrift_data','foto_pfade','formular_pfad','pdf_pfad',
            'gespeichert_am','dienst_gestartet','dienst_gestartet_am']
    with get_db() as db:
        db.execute(f"INSERT INTO fahrzeug_bestaetigungen ({','.join(cols)}) VALUES ({','.join('?'*len(cols))})",
                   [row[c] for c in cols])
        db.commit()
    try:
        exp = {k: v for k, v in row.items() if k != 'unterschrift_data'}
        exp['foto_pfade'] = foto_pfade
        json_path.write_text(json.dumps(exp, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception: pass
    try:
        pdf_bytes = _fb_generate_pdf(row)
        if pdf_bytes: pdf_path.write_bytes(pdf_bytes)
    except Exception: pass
    return jsonify({'ok': True, 'form_id': form_id})


@app.route('/api/fahrzeug/foto', methods=['POST'])
def fahrzeug_foto_upload():
    uid = session.get('portal_user_id') or session.get('user_id')
    if not uid:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    bundesland = request.form.get('bundesland','Unbekannt')
    bezirk     = request.form.get('bezirk','Unbekannt')
    today      = time.strftime('%Y-%m-%d')
    foto_dir   = _fb_form_dir(bundesland, bezirk, today) / 'fotos'
    foto_dir.mkdir(exist_ok=True)
    saved = []
    for f in request.files.getlist('fotos'):
        if not f or not f.filename: continue
        ext   = _fbPath(f.filename).suffix.lower() or '.jpg'
        fname = f'foto_{uid[:8]}_{uuid.uuid4().hex[:6]}{ext}'
        try:
            f.save(str(foto_dir / fname))
            saved.append({'name': fname, 'path': str(foto_dir / fname)})
        except Exception: pass
    return jsonify({'ok': True, 'fotos': saved})


@app.route('/api/fahrzeug/dienst-starten', methods=['POST'])
def fahrzeug_dienst_starten():
    uid = session.get('portal_user_id') or session.get('user_id')
    if not uid:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    data    = request.get_json(silent=True) or {}
    form_id = data.get('form_id','')
    with get_db() as db:
        row = db.execute('SELECT id,caregiver_id FROM fahrzeug_bestaetigungen WHERE id=?', [form_id]).fetchone()
        if not row: return jsonify({'ok': False, 'error': 'Formular nicht gefunden'}), 404
        if row['caregiver_id'] != uid: return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
        db.execute('UPDATE fahrzeug_bestaetigungen SET dienst_gestartet=1,dienst_gestartet_am=? WHERE id=?',
                   [time.strftime('%Y-%m-%d %H:%M:%S'), form_id])
        db.commit()
    return jsonify({'ok': True})


@app.route('/api/admin/fahrzeug/struktur')
def admin_fahrzeug_struktur():
    if not _require_admin_or_admiral():
        return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
    with get_db() as db:
        rows = db.execute('''SELECT bundesland,bezirk,datum,COUNT(*) as n
            FROM fahrzeug_bestaetigungen GROUP BY bundesland,bezirk,datum ORDER BY datum DESC,bundesland,bezirk''').fetchall()
    struktur = {}
    for r in rows:
        bl = r['bundesland'] or 'Unbekannt'
        bz = r['bezirk']     or 'Unbekannt'
        dt = r['datum']      or 'Unbekannt'
        struktur.setdefault(bl, {}).setdefault(bz, {})[dt] = r['n']
    return jsonify({'ok': True, 'struktur': struktur})


@app.route('/api/admin/fahrzeug/formulare')
def admin_fahrzeug_formulare():
    if not _require_admin_or_admiral():
        return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
    args = request.args
    sql = ('SELECT id,caregiver_name,dienstnummer,fahrzeug,kennzeichen,bundesland,bezirk,'
           'datum,uhrzeit,gespeichert_am,dienst_gestartet,foto_pfade '
           'FROM fahrzeug_bestaetigungen WHERE 1=1')
    params = []
    for col, key in [('bundesland','bundesland'),('bezirk','bezirk'),('datum','datum')]:
        if args.get(key): sql += f' AND {col}=?'; params.append(args[key])
    for col, key in [('fahrzeug','fahrzeug'),('dienstnummer','dienstnummer'),
                     ('caregiver_name','name'),('kennzeichen','kennzeichen')]:
        if args.get(key): sql += f' AND {col} LIKE ?'; params.append(f'%{args[key]}%')
    sql += ' ORDER BY gespeichert_am DESC LIMIT 300'
    with get_db() as db:
        rows = db.execute(sql, params).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        try: d['foto_pfade'] = json.loads(d.get('foto_pfade') or '[]')
        except: d['foto_pfade'] = []
        result.append(d)
    return jsonify({'ok': True, 'formulare': result})


@app.route('/api/admin/fahrzeug/formular/<form_id>')
def admin_fahrzeug_formular(form_id):
    if not _require_admin_or_admiral():
        return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
    with get_db() as db:
        row = db.execute('SELECT * FROM fahrzeug_bestaetigungen WHERE id=?', [form_id]).fetchone()
    if not row: return jsonify({'ok': False, 'error': 'Nicht gefunden'}), 404
    d = dict(row)
    try: d['foto_pfade'] = json.loads(d.get('foto_pfade') or '[]')
    except: d['foto_pfade'] = []
    return jsonify({'ok': True, 'formular': d})


@app.route('/api/admin/fahrzeug/pdf/<form_id>')
def admin_fahrzeug_pdf(form_id):
    if not _require_admin_or_admiral():
        return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
    with get_db() as db:
        row = db.execute('SELECT * FROM fahrzeug_bestaetigungen WHERE id=?', [form_id]).fetchone()
    if not row: return jsonify({'ok': False, 'error': 'Nicht gefunden'}), 404
    pdf_bytes = _fb_generate_pdf(dict(row))
    if not pdf_bytes: return jsonify({'ok': False, 'error': 'PDF-Erstellung fehlgeschlagen'}), 500
    from flask import Response
    d = dict(row)
    fn = f"formular_{_fb_sanitize(d.get('dienstnummer','x'))}_{_fb_sanitize(d.get('fahrzeug','x'))}_{d.get('datum','x')}.pdf"
    resp = Response(pdf_bytes, mimetype='application/pdf')
    resp.headers['Content-Disposition'] = f'attachment; filename="{fn}"'
    return resp


@app.route('/api/admin/fahrzeug/foto/<form_id>/<path:filename>')
def admin_fahrzeug_foto(form_id, filename):
    if not _require_admin_or_admiral():
        return jsonify({'ok': False, 'error': 'Kein Zugriff'}), 403
    with get_db() as db:
        row = db.execute('SELECT bundesland,bezirk,datum FROM fahrzeug_bestaetigungen WHERE id=?', [form_id]).fetchone()
    if not row: return jsonify({'ok': False}), 404
    foto_dir = _fb_form_dir(row['bundesland'] or 'Unbekannt', row['bezirk'] or 'Unbekannt', row['datum']) / 'fotos'
    from flask import send_from_directory
    return send_from_directory(str(foto_dir), _fbPath(filename).name)


# ═══════════════════════════════════════════════════════════════════════════
# DIGITALES FAHRTENBUCH
# ═══════════════════════════════════════════════════════════════════════════

@app.route('/api/fahrtenbuch', methods=['GET'])
def fahrtenbuch_list():
    uid = session.get('user_id')
    if not uid:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    ses_fahrzeug = session.get('fahrzeug') or ''
    fahrzeug = request.args.get('fahrzeug') or ses_fahrzeug
    # Fahrername aus vehicle_sessions
    ses_name = ''
    ses_kennzeichen = ''
    if ses_fahrzeug:
        with get_db() as db:
            vs = db.execute(
                'SELECT caregiver_name FROM vehicle_sessions WHERE fahrzeug=?',
                [ses_fahrzeug]).fetchone()
            fzr = db.execute(
                'SELECT kennzeichen FROM fahrzeuge WHERE name=?',
                [ses_fahrzeug]).fetchone()
        if vs: ses_name = vs['caregiver_name'] or ''
        if fzr: ses_kennzeichen = fzr['kennzeichen'] or ''
    with get_db() as db:
        if fahrzeug:
            rows = db.execute(
                'SELECT * FROM fahrtenbuch WHERE fahrzeug=? ORDER BY datum DESC, uhrzeit_von DESC LIMIT 200',
                [fahrzeug]).fetchall()
        else:
            rows = db.execute(
                'SELECT * FROM fahrtenbuch ORDER BY datum DESC, uhrzeit_von DESC LIMIT 200').fetchall()
    return jsonify({
        'ok': True,
        'fahrzeug':    ses_fahrzeug,
        'kennzeichen': ses_kennzeichen,
        'name':        ses_name,
        'eintraege':   [dict(r) for r in rows],
    })


@app.route('/api/fahrtenbuch', methods=['POST'])
def fahrtenbuch_create():
    uid = session.get('user_id')
    if not uid:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    d = request.get_json(force=True) or {}
    import uuid as _uuid
    eid = str(_uuid.uuid4())
    km_s = int(d.get('km_start') or 0)
    km_e = int(d.get('km_ende') or 0)
    km_g = max(0, km_e - km_s)
    getankt = float(d.get('getankt_liter') or 0)
    with get_db() as db:
        db.execute(
            '''INSERT INTO fahrtenbuch
               (id,fahrzeug,kennzeichen,fahrer,user_id,datum,uhrzeit_von,uhrzeit_bis,
                von_ort,nach_ort,zweck,km_start,km_ende,km_gesamt,
                getankt_liter,kraftstoff_art,bemerkungen)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
            [eid,
             d.get('fahrzeug',''), d.get('kennzeichen',''), d.get('fahrer',''), uid,
             d.get('datum',''), d.get('uhrzeit_von',''), d.get('uhrzeit_bis',''),
             d.get('von_ort',''), d.get('nach_ort',''), d.get('zweck',''),
             km_s, km_e, km_g,
             getankt, d.get('kraftstoff_art',''), d.get('bemerkungen','')])
    return jsonify({'ok': True, 'id': eid, 'km_gesamt': km_g})


@app.route('/api/fahrtenbuch/<eid>', methods=['PUT'])
def fahrtenbuch_update(eid):
    uid = session.get('user_id')
    if not uid:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    d = request.get_json(force=True) or {}
    km_s = int(d.get('km_start') or 0)
    km_e = int(d.get('km_ende') or 0)
    km_g = max(0, km_e - km_s)
    getankt = float(d.get('getankt_liter') or 0)
    with get_db() as db:
        db.execute(
            '''UPDATE fahrtenbuch SET
               fahrzeug=?,kennzeichen=?,fahrer=?,datum=?,uhrzeit_von=?,uhrzeit_bis=?,
               von_ort=?,nach_ort=?,zweck=?,km_start=?,km_ende=?,km_gesamt=?,
               getankt_liter=?,kraftstoff_art=?,bemerkungen=?
               WHERE id=?''',
            [d.get('fahrzeug',''), d.get('kennzeichen',''), d.get('fahrer',''),
             d.get('datum',''), d.get('uhrzeit_von',''), d.get('uhrzeit_bis',''),
             d.get('von_ort',''), d.get('nach_ort',''), d.get('zweck',''),
             km_s, km_e, km_g,
             getankt, d.get('kraftstoff_art',''), d.get('bemerkungen',''), eid])
    return jsonify({'ok': True, 'km_gesamt': km_g})


@app.route('/api/fahrtenbuch/<eid>', methods=['DELETE'])
def fahrtenbuch_delete(eid):
    uid = session.get('user_id')
    if not uid:
        return jsonify({'ok': False, 'error': 'Nicht angemeldet'}), 401
    with get_db() as db:
        db.execute('DELETE FROM fahrtenbuch WHERE id=?', [eid])
    return jsonify({'ok': True})


@app.route('/__mockup/', defaults={'subpath': ''})
@app.route('/__mockup/<path:subpath>')
def mockup_proxy(subpath):
    import urllib.request, urllib.error
    target = f'http://localhost:23636/__mockup/{subpath}'
    if request.query_string:
        target += '?' + request.query_string.decode()
    try:
        req = urllib.request.Request(target, headers={k: v for k, v in request.headers if k.lower() not in ('host',)})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = r.read()
            resp = app.response_class(data, status=r.status, content_type=r.headers.get('Content-Type', 'application/octet-stream'))
            for h in ('Cache-Control', 'ETag', 'Last-Modified', 'X-Content-Type-Options'):
                if r.headers.get(h):
                    resp.headers[h] = r.headers[h]
            return resp
    except urllib.error.HTTPError as e:
        return app.response_class(e.read(), status=e.code, content_type=e.headers.get('Content-Type', 'text/plain'))
    except Exception:
        return jsonify({'error': 'Mockup sandbox not reachable'}), 502

@app.route('/<path:filename>')
def static_files(filename):
    resp = send_from_directory(BASE_DIR, filename)
    if filename.endswith('.html'):
        resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        resp.headers['Pragma'] = 'no-cache'
        resp.headers['Expires'] = '0'
    return resp


# ── Startup: Dienstnummern für bestehende freigegebene Pfleger nachholen ────
# Läuft bei jedem Modulload (inkl. gunicorn-Worker). Idempotent: bereits
# vergebene Nummern werden nicht überschrieben.
try:
    with get_db() as _sdb:
        _pb_rows = _sdb.execute(
            "SELECT id FROM portal_bewerbungen WHERE status='freigegeben'"
            " AND (rolle IS NULL OR rolle='pfleger')"
        ).fetchall()
        for _pbr in _pb_rows:
            try:
                _dnr_row = _sdb.execute(
                    'SELECT dienstnummer FROM portal_bewerbungen WHERE id=?',
                    [_pbr['id']]
                ).fetchone()
                if _dnr_row and (_dnr_row.get('dienstnummer') or '').strip():
                    continue
                _ensure_caregiver_from_portal(_pbr['id'], _sdb)
            except Exception:
                pass
except Exception:
    pass

# ── Entry point ─────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    print(f'Nursy API + static server on port {port}', flush=True)
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
