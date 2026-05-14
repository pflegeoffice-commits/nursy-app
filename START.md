# Nursy – Akut Plus Pflegeportal · Starthilfe

## Voraussetzungen
- Python 3.10 oder neuer
- pip (Python-Paketmanager)

## 1. Pakete installieren
```
pip install -r requirements.txt
```

## 2. Server starten (Entwicklung)
```
python3 server.py
```
Die App ist dann erreichbar unter: http://localhost:5000

## 3. Server starten (Produktion / stabil)
```
gunicorn --bind 0.0.0.0:5000 --workers 2 server:app
```

---

## Zugangsdaten (Demo)

| Bereich | E-Mail / User | Passwort |
|---|---|---|
| Admin / Admiral | admin | NursyAdmin2024! |
| Pflegeportal | care@test.at | Test1234! |
| Verrechnungsstelle | billing@nursy.at | Billing2024! |
| Leitstelle | disponent@nursy.at | Leitstelle2024! |

## Wichtige Seiten
- `/` — Startseite
- `/leitstelle-ansicht.html` — Leitstellen-Dashboard (Admiral)
- `/auftragslage.html` — Auftragslage (Pflegekraft-App)
- `/pflege-portal-login.html` — Akut Plus Pflegeportal
- `/admin.html` — Admin-Dashboard
- `/billing-login.html` — Verrechnungsstelle
