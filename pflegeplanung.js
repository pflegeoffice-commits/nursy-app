/* Nursy – Pflegeplanung (Frontend-Demo)
   Modal UI nach Skizze: Anamnese / Vorlagen / Frei definiert
   Hinweis: Demo-Daten, keine Speicherung.
*/

(function () {
  'use strict';

  const qs = (sel, el = document) => el.querySelector(sel);
  const qsa = (sel, el = document) => Array.from(el.querySelectorAll(sel));

  const demoTemplates = [
    // 13 Kategorien – Vorlagen (erweitert, detaillierter)

    // 1 Mobilität
    { atl:'Sich bewegen', kat:'Mobilität', symptom:'Eingeschränkte Mobilität / unsicherer Gang', massnahme:'Mobilisation & Gehtraining', ziel:'Sicheres Gehen', details:[
      'Transfer/Stand/Gangbild einschätzen; Hilfsmittel anpassen.',
      'Kurze Einheiten, Pausen, Sturzprophylaxe integrieren.',
      'Dokumentation: Strecke, Assistenzgrad, Belastbarkeit.'
    ]},
    { atl:'Sich bewegen', kat:'Mobilität', symptom:'Kontrakturgefahr (Immobilität)', massnahme:'Bewegungsübungen (ROM), Lagerung, Aktivierung', ziel:'Beweglichkeit erhalten', details:[
      'ROM nach AO, schmerzadaptiert; Gelenkstellung beachten.',
      'Lagerungswechsel + Positionierung; ggf. Hilfsmittel.',
      'Dokumentation: Schmerz, Bewegungsausmaß, Hautstatus.'
    ]},
    { atl:'Sich bewegen', kat:'Mobilität', symptom:'Transfer unsicher (Bett–Stuhl)', massnahme:'Transfertraining + Anleitung Kinästhetik', ziel:'Sicherer Transfer', details:[
      'Rutschbrett/Standhilfe nach AO; Umgebung vorbereiten.',
      'Ressourcen fördern, klare Schritt-für-Schritt-Anleitung.',
      'Dokumentation: benötigte Hilfe, Risiken, Reaktion.'
    ]},
    { atl:'Sich bewegen', kat:'Mobilität', symptom:'Eingeschränkte Belastbarkeit', massnahme:'Belastungsdosierung, Aktivierung, Pausenplan', ziel:'Belastbarkeit gesteigert', details:[
      'Borg-/Dyspnoe-Skala nutzen; Überforderung vermeiden.',
      'Aktivitäten in Etappen; Ruhephasen strukturieren.',
      'Dokumentation: Aktivitätsdauer, Vitalzeichen falls vorhanden.'
    ]},

    // 2 Körperpflege
    { atl:'Körperpflege', kat:'Körperpflege', symptom:'Teilweise Unterstützung bei Körperpflege', massnahme:'Anleitung + Unterstützung morgens/abends', ziel:'Selbstständigkeit erhalten', details:[
      'Hilfsmittel bereitstellen; Reihenfolge gemeinsam planen.',
      'Intimsphäre wahren, Ressourcen fördern, Pausen anbieten.',
      'Dokumentation: Hilfestufe, Hautbesonderheiten.'
    ]},
    { atl:'Körperpflege', kat:'Körperpflege', symptom:'Mundpflege erschwert (Prothesen)', massnahme:'Mundpflege anleiten/übernehmen, Prothesenpflege', ziel:'Mundschleimhaut intakt', details:[
      'Weiche Bürste/geeignete Pflege; Druckstellen beobachten.',
      'Flüssigkeitszufuhr unterstützen; ggf. Lippenpflege.',
      'Dokumentation: Befund, Beschwerden, Maßnahmen.'
    ]},
    { atl:'Körperpflege', kat:'Körperpflege', symptom:'Intimhygiene benötigt Unterstützung', massnahme:'Intimpflege, Hautschutz, Anleitung', ziel:'Hautreizungen vermeiden', details:[
      'Von sauber nach weniger sauber; sanfte Reinigung, trocken tupfen.',
      'Barrierecreme nach Bedarf; Inko-Material anpassen.',
      'Dokumentation: Rötung, Schmerzen, Verträglichkeit.'
    ]},
    { atl:'Körperpflege', kat:'Körperpflege', symptom:'Hilfebedarf beim An-/Auskleiden', massnahme:'Ankleidetraining, Hilfsmittel, Ressourcenförderung', ziel:'Mehr Selbstständigkeit', details:[
      'Kleidung vorbereiten; betroffene Seite zuerst/zuletzt je nach Situation.',
      'Greifzange/Anziehhilfen; Zeit einplanen.',
      'Dokumentation: Assistenzgrad, Fortschritt.'
    ]},

    // 3 Ernährung & Flüssigkeit
    { atl:'Essen & Trinken', kat:'Ernährung & Flüssigkeit', symptom:'Unzureichende Flüssigkeitsaufnahme', massnahme:'Trinkplan + Erinnerung', ziel:'Ausreichende Hydrierung', details:[
      'Zielmenge nach AO; bevorzugte Getränke berücksichtigen.',
      'Trinkgefäß griffbereit; Erinnerungsintervalle vereinbaren.',
      'Dokumentation: Trinkprotokoll, Exsikkosezeichen.'
    ]},
    { atl:'Essen & Trinken', kat:'Ernährung & Flüssigkeit', symptom:'Mangelernährungsrisiko', massnahme:'Ernährungsprotokoll, Zwischenmahlzeiten', ziel:'Gewicht stabil', details:[
      'Kau-/Schluckprobleme, Übelkeit, Appetit abklären.',
      'Anreicherung (Eiweiß/Energie), kleine Portionen, Snacks.',
      'Dokumentation: Intake, Gewicht, Verträglichkeit.'
    ]},
    { atl:'Essen & Trinken', kat:'Ernährung & Flüssigkeit', symptom:'Dysphagie (Schluckstörung) Verdacht', massnahme:'Konsistenz anpassen, Schlucktraining anleiten', ziel:'Aspirationsrisiko reduziert', details:[
      'Aufrechte Position, kleine Bissen/Schlucke; Nachschluck anleiten.',
      'Getränke ggf. andicken; Ruhe beim Essen.',
      'Dokumentation: Husten/“Verschlucken”, Stimme, Sättigung.'
    ]},
    { atl:'Essen & Trinken', kat:'Ernährung & Flüssigkeit', symptom:'Appetitlosigkeit', massnahme:'Wunschkost, kleine Mahlzeiten, Essbegleitung', ziel:'Energiezufuhr ausreichend', details:[
      'Essenszeiten an Tagesform; Gerüche/Reize reduzieren.',
      'Lieblingsspeisen; soziale Unterstützung/Essbegleitung.',
      'Dokumentation: Portionen, Gründe, Maßnahmenwirkung.'
    ]},
    { atl:'Essen & Trinken', kat:'Ernährung & Flüssigkeit', symptom:'Diabetes: Ernährung unsicher', massnahme:'Ernährungsberatung (AO), Blutzucker-Routine unterstützen', ziel:'BZ-Werte stabiler', details:[
      'Kohlenhydrate erklären; regelmäßige Mahlzeiten fördern.',
      'BZ-Messen/Protokoll unterstützen nach Plan.',
      'Dokumentation: BZ, Hypo-/Hyperzeichen, Schulungsinhalt.'
    ]},

    // 4 Ausscheidung
    { atl:'Ausscheiden', kat:'Ausscheidung', symptom:'Obstipationsrisiko', massnahme:'Flüssigkeit, Bewegung, Ernährung', ziel:'Regelmäßige Ausscheidung', details:[
      'Stuhlgewohnheiten erheben; Bauchstatus beobachten.',
      'Toilettenrhythmus; Ballaststoffe/Bewegung fördern.',
      'Dokumentation: Stuhlprotokoll, Beschwerden, Maßnahmen.'
    ]},
    { atl:'Ausscheiden', kat:'Ausscheidung', symptom:'Harninkontinenz', massnahme:'Toilettentraining, Hautschutz, Hilfsmittel', ziel:'Hautschutz & Sicherheit', details:[
      'Miktionsplan; Trinkverhalten prüfen; Scham reduzieren.',
      'Hautschutz; passendes Inko-Material wählen.',
      'Dokumentation: Episoden, Hautstatus, Akzeptanz.'
    ]},
    { atl:'Ausscheiden', kat:'Ausscheidung', symptom:'Harnwegsinfekt-Risiko', massnahme:'Trinkmenge fördern, Intimhygiene, Beobachtung', ziel:'Infekt vermeiden', details:[
      'Anzeichen: Brennen, Geruch, Fieber, Verwirrtheit beobachten.',
      'Hygiene von vorne nach hinten; Wechsel Inko-Material.',
      'Dokumentation: Symptome, Temperatur, Maßnahmen.'
    ]},
    { atl:'Ausscheiden', kat:'Ausscheidung', symptom:'Stuhlinkontinenz', massnahme:'Hautschutz, Toilettenzeiten, Hilfsmittelmanagement', ziel:'Haut intakt, Würde gewahrt', details:[
      'Schneller Wechsel, sanfte Reinigung, Barrierecreme.',
      'Toilettenzeiten; Ernährung/Medikation prüfen (AO).',
      'Dokumentation: Häufigkeit, Hautstatus, Auslöser.'
    ]},

    // 5 Atmung
    { atl:'Sich bewegen', kat:'Atmung', symptom:'Atemnot bei Belastung', massnahme:'Atemübungen, Pausen, Oberkörper hoch', ziel:'Dyspnoe reduziert', details:[
      'Atemerleichternde Positionen (Kutschersitz) anleiten.',
      'Belastung dosieren; ggf. O2 nach AO/Plan.',
      'Dokumentation: Atemfrequenz, SpO2 (wenn vorhanden), Dyspnoe.'
    ]},
    { atl:'Sich bewegen', kat:'Atmung', symptom:'Sekret / produktiver Husten', massnahme:'Inhalation (AO), Atemtherapie, Flüssigkeit fördern', ziel:'Sekret gelöst', details:[
      'Inhalation nach Plan; Lippenbremse, PEP nach AO.',
      'Ausreichend trinken, wenn möglich; Mobilisation unterstützen.',
      'Dokumentation: Auswurf, Atemgeräusche, Wirkung.'
    ]},
    { atl:'Sich bewegen', kat:'Atmung', symptom:'Atemmuster ineffektiv (flach)', massnahme:'Atemlenkung, Positionierung, Entspannung', ziel:'Tiefere Atmung', details:[
      'Handkontakt zur Atemlenkung; ruhige Umgebung.',
      'Oberkörperhochlagerung; Pausen bei Aktivität.',
      'Dokumentation: Dyspnoe, Anstrengung, Wirkung.'
    ]},

    // 6 Schmerz
    { atl:'Körperpflege', kat:'Schmerz', symptom:'Schmerzen bei Bewegung', massnahme:'Schmerzassessment, Lagerung, Wärme/Kälte nach Bedarf', ziel:'Schmerz < 3/10', details:[
      'NRS vor/nach Maßnahme; Trigger identifizieren.',
      'Entlastung, Wärme/Kälte (AO), Ablenkung/Atmung.',
      'Dokumentation: NRS, Wirkung, Nebenwirkungen.'
    ]},
    { atl:'Körperpflege', kat:'Schmerz', symptom:'Chronischer Schmerz (dauerhaft)', massnahme:'Schmerztagebuch, Aktivitätsplanung, Entspannung', ziel:'Besserer Umgang mit Schmerz', details:[
      'Pacing: Aktivität/Erholung balancieren; Überlastung vermeiden.',
      'Entspannung/Atmung; Edukation nach AO.',
      'Dokumentation: Verlauf, Auslöser, Wirksamkeit.'
    ]},
    { atl:'Körperpflege', kat:'Schmerz', symptom:'Schmerz bei Wundversorgung', massnahme:'Vorbereitung, Analgesie nach AO, atraumatisch versorgen', ziel:'Schmerz reduziert', details:[
      'Zeitpunkt/Analgesie abstimmen; sanftes Vorgehen.',
      'Ablenkung; Verbandmaterial passend wählen.',
      'Dokumentation: Schmerz, Material, Wundstatus.'
    ]},

    // 7 Wunde & Haut
    { atl:'Körperpflege', kat:'Wunde & Haut', symptom:'Dekubitusrisiko', massnahme:'Positionswechsel, Hautkontrolle, Druckentlastung', ziel:'Haut intakt', details:[
      'Risikoeinschätzung; Lagerungsintervall festlegen.',
      'Druckentlastende Hilfsmittel; Haut täglich inspizieren.',
      'Dokumentation: Lokalisation, Hautzustand, Lagerungsplan.'
    ]},
    { atl:'Körperpflege', kat:'Wunde & Haut', symptom:'Dekubitus Grad 1 (Rötung)', massnahme:'Druckentlastung, Hautschutz, Beobachtung', ziel:'Rötung rückläufig', details:[
      'Druck vermeiden; Lagerung anpassen; Reibung reduzieren.',
      'Hautschutz, Feuchtigkeitsmanagement.',
      'Dokumentation: Fläche, Farbe, Wärme, Schmerz.'
    ]},
    { atl:'Körperpflege', kat:'Wunde & Haut', symptom:'Intertrigo-Risiko (Hautfalten)', massnahme:'Hautfalten trocken halten, Schutz, Kontrolle', ziel:'Entzündung vermeiden', details:[
      'Sanft reinigen, gründlich trocknen; ggf. Schutztextilien.',
      'Barriere/Antimykotisch nur nach AO.',
      'Dokumentation: Rötung, Geruch, Juckreiz.'
    ]},
    { atl:'Körperpflege', kat:'Wunde & Haut', symptom:'Hauttrockenheit / Juckreiz', massnahme:'Rückfettende Pflege, Trigger reduzieren', ziel:'Haut geschmeidig', details:[
      'pH-neutrale Reinigung; rückfettend eincremen.',
      'Nägel kurz; Kratzen vermeiden; Kleidung weich.',
      'Dokumentation: Hautzustand, Verträglichkeit.'
    ]},
    { atl:'Körperpflege', kat:'Wunde & Haut', symptom:'Wundheilungsrisiko (z.B. diabetisch)', massnahme:'Wundkontrolle, Druckschutz, Edukation', ziel:'Wunde stabil/verbessert', details:[
      'Druck vermeiden; Fuß-/Wundkontrolle; Hygiene.',
      'BZ-Management nach Plan; Schuhwerk prüfen.',
      'Dokumentation: Wundrand, Exsudat, Geruch, Schmerz.'
    ]},

    // 8 Schlaf & Ruhe
    { atl:'Körperpflege', kat:'Schlaf & Ruhe', symptom:'Schlafstörung (Ein-/Durchschlaf)', massnahme:'Schlafhygiene, Tagesstruktur, Reize reduzieren', ziel:'Erholsamer Schlaf', details:[
      'Abendroutine; Licht/Lärm reduzieren; Tagschlaf dosieren.',
      'Schmerz/Harndrang als Ursache prüfen; Entspannung.',
      'Dokumentation: Schlafprotokoll, Einflussfaktoren.'
    ]},
    { atl:'Körperpflege', kat:'Schlaf & Ruhe', symptom:'Tag-Nacht-Umkehr', massnahme:'Tagesaktivierung, Lichtsteuerung, Routinen', ziel:'Tagesrhythmus stabilisiert', details:[
      'Tagsüber Aktivität/Licht; abends beruhigende Rituale.',
      'Koffein/Spätmahlzeiten reduzieren.',
      'Dokumentation: Ruhezeiten, Aktivität, Wirkung.'
    ]},
    { atl:'Körperpflege', kat:'Schlaf & Ruhe', symptom:'Unruhe nachts (Umherwandern)', massnahme:'Sicherheitscheck, Orientierung, Beruhigung', ziel:'Nächtliche Sicherheit erhöht', details:[
      'Stolperfallen entfernen; Nachtlicht; Klingel erreichbar.',
      'Beruhigende Ansprache; Toilettenangebot.',
      'Dokumentation: Auslöser, Zeiten, Maßnahmen.'
    ]},

    // 9 Psyche & Kommunikation
    { atl:'Kommunizieren', kat:'Psyche & Kommunikation', symptom:'Angst/Unruhe', massnahme:'Orientierung, Gespräch, Struktur', ziel:'Ruhe & Sicherheit', details:[
      'Validieren; ruhige Kommunikation; Trigger identifizieren.',
      'Tagesstruktur sichtbar; Bezugspersonen einbinden.',
      'Dokumentation: Auslöser, Wirkung der Interventionen.'
    ]},
    { atl:'Kommunizieren', kat:'Psyche & Kommunikation', symptom:'Depressive Stimmung / Antrieb vermindert', massnahme:'Aktivierung, Ressourcenarbeit, Gespräche', ziel:'Mehr Antrieb/Teilhabe', details:[
      'Kleine erreichbare Ziele; Tagesplan; Erfolgserlebnisse.',
      'Soziale Kontakte fördern; ggf. Fachstelle nach AO.',
      'Dokumentation: Stimmung, Aktivität, Rückmeldung.'
    ]},
    { atl:'Kommunizieren', kat:'Psyche & Kommunikation', symptom:'Aggression/Abwehr bei Pflege', massnahme:'Deeskalation, Wahlmöglichkeiten, Tempo anpassen', ziel:'Kooperation verbessert', details:[
      'Trigger vermeiden; vorher ankündigen; kurze Schritte.',
      'Validation; Pausen; ggf. Teamabsprachen.',
      'Dokumentation: Situation, Auslöser, erfolgreiche Strategien.'
    ]},

    // 10 Kognition & Orientierung
    { atl:'Kommunizieren', kat:'Kognition & Orientierung', symptom:'Desorientierung (Zeit/Ort)', massnahme:'Orientierungshilfen, Tagesplan, Validation', ziel:'Orientierung verbessert', details:[
      'Uhr/Kalender, Namensschilder, bekannte Gegenstände nutzen.',
      'Kurze klare Sätze; Wiederholungen; Validation.',
      'Dokumentation: Orientierung, Kooperation, Verhalten.'
    ]},
    { atl:'Kommunizieren', kat:'Kognition & Orientierung', symptom:'Gedächtnisprobleme (Vergesslichkeit)', massnahme:'Gedächtnisstützen, Routinen, Reminder', ziel:'Alltag strukturierter', details:[
      'Notizzettel, Checklisten, fixe Abläufe.',
      'Medikamenten-/Termin-Reminder; Angehörige einbinden.',
      'Dokumentation: Selbstständigkeit, Fehlerquellen.'
    ]},
    { atl:'Kommunizieren', kat:'Kognition & Orientierung', symptom:'Delir-Risiko (akute Verwirrtheit)', massnahme:'Reorientierung, Flüssigkeit, Schlaf fördern (AO)', ziel:'Delirzeichen reduziert', details:[
      'Reorientierung häufig; Brille/Hörgerät; Reize dosieren.',
      'Schmerz/Infekt/Dehydratation abklären (AO).',
      'Dokumentation: Verlauf, Auslöser, Beobachtungen.'
    ]},

    // 11 Sicherheit & Sturz
    { atl:'Sich bewegen', kat:'Sicherheit & Sturz', symptom:'Sturzrisiko / Schwindel', massnahme:'Sturzprophylaxe, Hilfsmittel prüfen', ziel:'Stürze vermeiden', details:[
      'Umgebung sichern; rutschfeste Schuhe; Nachtlicht.',
      'Orthostase beachten; langsam aufstehen; Hilfsmittel einstellen.',
      'Dokumentation: Beinahe-Stürze, Maßnahmen, Wirksamkeit.'
    ]},
    { atl:'Sich bewegen', kat:'Sicherheit & Sturz', symptom:'Sturz nach Ereignis (Post-Fall)', massnahme:'Sturzassessment, Umfeldanpassung, Beobachtung', ziel:'Folgestürze vermeiden', details:[
      'Schmerzen/Verletzung prüfen; Arztkontakt nach AO.',
      'Ursachenanalyse; Maßnahmenplan (Umgebung/Hilfsmittel).',
      'Dokumentation: Hergang, Befund, Maßnahmen.'
    ]},
    { atl:'Sich bewegen', kat:'Sicherheit & Sturz', symptom:'Unsichere Medikation (Sedierung)', massnahme:'Beobachtung, Rückmeldung an Arzt (AO), Sicherheitsmaßnahmen', ziel:'Sicherheit erhöht', details:[
      'Schläfrigkeit, Gangunsicherheit beobachten.',
      'Rücksprache nach AO; Sturzprophylaxe verstärken.',
      'Dokumentation: Symptome, Zeiten, Rückmeldungen.'
    ]},

    // 12 Medikation
    { atl:'Essen & Trinken', kat:'Medikation', symptom:'Unregelmäßige Medikamenteneinnahme', massnahme:'Mediplan, Einnahme-Reminder, Kontrolle', ziel:'Adhärenz verbessert', details:[
      'Mediplan erklären; Einnahmezeiten alltagsnah planen.',
      'Pillendose/Reminder; Nebenwirkungen beobachten.',
      'Dokumentation: Einnahme, Auffälligkeiten, Rückmeldung.'
    ]},
    { atl:'Essen & Trinken', kat:'Medikation', symptom:'Nebenwirkungsbeobachtung erforderlich', massnahme:'Monitoring, Symptomcheck, Rückmeldung (AO)', ziel:'Nebenwirkungen früh erkannt', details:[
      'Schwindel, Übelkeit, Obstipation, Müdigkeit etc. beobachten.',
      'Einnahme korrekt; Wechselwirkungen nach AO abklären.',
      'Dokumentation: Symptome, Zeitpunkt, Maßnahmen.'
    ]},
    { atl:'Essen & Trinken', kat:'Medikation', symptom:'Polypharmazie / Einnahme unsicher', massnahme:'Medikationscheck unterstützen (AO), Strukturierung', ziel:'Einnahme sicherer', details:[
      'Sortiersystem; Liste aktuell halten; Doppelmedikation vermeiden (AO).',
      'Apotheke/Arztkontakt nach AO.',
      'Dokumentation: Planversion, Änderungen, Verständnis.'
    ]},

    // 13 Prophylaxen
    { atl:'Körperpflege', kat:'Prophylaxen', symptom:'Thromboserisiko', massnahme:'Aktivierung, Wadenpumpe, Kompression nach AO', ziel:'Thrombose vermeiden', details:[
      'Frühmobilisation; Venengymnastik anleiten.',
      'Kompression/Heparin nur nach AO/Verordnung.',
      'Dokumentation: Schwellung/Schmerz, Umfang, Compliance.'
    ]},
    { atl:'Körperpflege', kat:'Prophylaxen', symptom:'Pneumonieprophylaxe erforderlich', massnahme:'Atemtraining, Mobilisation, Inhalation nach AO', ziel:'Pneumonie vermeiden', details:[
      'Tiefes Durchatmen, Lippenbremse; Positionswechsel.',
      'Mobilisation; Flüssigkeit fördern, wenn möglich.',
      'Dokumentation: Atemstatus, Sekret, Wirkung.'
    ]},
    { atl:'Körperpflege', kat:'Prophylaxen', symptom:'Dekubitusprophylaxe erforderlich', massnahme:'Lagerungsplan, Druckentlastung, Hautpflege', ziel:'Haut intakt', details:[
      'Risikoeinschätzung; Lagerungsintervalle festlegen.',
      'Druckentlastung; Feuchtigkeitsmanagement.',
      'Dokumentation: Hautbefund, Lagerungen, Hilfsmittel.'
    ]},
    { atl:'Körperpflege', kat:'Prophylaxen', symptom:'Kontrakturprophylaxe erforderlich', massnahme:'Bewegung, Positionierung, Aktivierung', ziel:'Kontrakturen vermeiden', details:[
      'Aktive/passive Bewegungen; Alltag integrieren.',
      'Positionierung; Hilfsmittel prüfen.',
      'Dokumentation: Beweglichkeit, Schmerz, Mitarbeit.'
    ]},

    // ── ERWEITERTE VORLAGEN (150+) ────────────────────────────────────────────

    // 1 Mobilität
    { atl:'Sich bewegen', kat:'Mobilität', symptom:'Unsicherer Gang / Sturzrisiko erhöht', massnahme:'Gehumgebung sichern, Rollator oder Gehstock bereitstellen, Begleitung beim Gehen, Schuhwerk prüfen', ziel:'Sturzrisiko wird reduziert, sicheres Gehen ermöglicht', details:[] },
    { atl:'Sich bewegen', kat:'Mobilität', symptom:'Transfer Bett–Rollstuhl unsicher', massnahme:'Transfer nach kinästhetischen Prinzipien unterstützen, Rutschbrett oder Hilfsgeräte einsetzen, Anleitung und Begleitung', ziel:'Sicherer Transfer ohne Verletzung', details:[] },
    { atl:'Sich bewegen', kat:'Mobilität', symptom:'Rollatornutzung erlernen / unsicher', massnahme:'Rollatorhandhabung erklären und üben, auf korrekte Einstellung achten, Sicherheitsregeln erläutern', ziel:'Selbstständige und sichere Rollatornutzung', details:[] },
    { atl:'Sich bewegen', kat:'Mobilität', symptom:'Bettlägerigkeit', massnahme:'Lagerungswechsel alle 2–4 Stunden, Mobilisation nach Ressourcen, Prophylaxen einleiten', ziel:'Komplikationen durch Immobilität werden vermieden', details:[] },
    { atl:'Sich bewegen', kat:'Mobilität', symptom:'Schwäche nach Krankenhausaufenthalt', massnahme:'Mobilisation langsam steigern, kurze Einheiten mit Pausen, Ressourcen stärken, Sicherheit fördern', ziel:'Körperliche Belastbarkeit wird schrittweise aufgebaut', details:[] },
    { atl:'Sich bewegen', kat:'Mobilität', symptom:'Bewegungseinschränkung der Gelenke', massnahme:'Passive und aktive Bewegungsübungen durchführen, Lagerung ergänzen, Schmerz beobachten', ziel:'Gelenkbeweglichkeit erhalten, Kontrakturen vermieden', details:[] },
    { atl:'Sich bewegen', kat:'Mobilität', symptom:'Eingeschränkte Selbstständigkeit beim Aufstehen', massnahme:'Aufstehtraining unterstützen, Orthostasereaktion beobachten, langsam aufstehen lassen', ziel:'Selbstständiges Aufstehen gefördert, Schwindel vermieden', details:[] },
    { atl:'Sich bewegen', kat:'Mobilität', symptom:'Hemiparese / einseitige Lähmung', massnahme:'Mobilisation der betroffenen Seite fördern, Kompensation der gesunden Seite unterstützen, Hilfsmittel einsetzen', ziel:'Restmobilität genutzt, Selbstständigkeit erhalten', details:[] },
    { atl:'Sich bewegen', kat:'Mobilität', symptom:'Gehstrecke stark reduziert', massnahme:'Gehtraining in sicherer Umgebung, Strecke langsam steigern, Pausen einplanen', ziel:'Gehausdauer wird gesteigert', details:[] },

    // 2 Körperpflege
    { atl:'Körperpflege', kat:'Körperpflege', symptom:'Vollständige Übernahme der Körperpflege notwendig', massnahme:'Ganzkörperpflege vollständig durchführen, Hautzustand beobachten, Würde wahren', ziel:'Körperpflege sichergestellt, Haut intakt', details:[] },
    { atl:'Körperpflege', kat:'Körperpflege', symptom:'Teilwaschung erforderlich', massnahme:'Teilwaschung im Rahmen der Ressourcen unterstützen, Selbstständigkeit fördern', ziel:'Hygiene gewährleistet, Selbstständigkeit erhalten', details:[] },
    { atl:'Körperpflege', kat:'Körperpflege', symptom:'Haarpflege benötigt Unterstützung', massnahme:'Haare waschen und kämmen nach Wunsch der Person, Hilfsmittel nutzen', ziel:'Wohlbefinden und Hygiene gesichert', details:[] },
    { atl:'Körperpflege', kat:'Körperpflege', symptom:'Nagelpflege erforderlich', massnahme:'Finger- und Zehennägel pflegen, Auffälligkeiten dokumentieren, bei Diabetikern besondere Sorgfalt', ziel:'Verletzungsrisiko durch lange Nägel vermieden', details:[] },
    { atl:'Körperpflege', kat:'Körperpflege', symptom:'Trockene oder rissige Haut', massnahme:'Hautpflegemittel auftragen, Inhaltsstoffe abstimmen, Hautveränderungen dokumentieren', ziel:'Haut wird gepflegt und geschützt', details:[] },
    { atl:'Körperpflege', kat:'Körperpflege', symptom:'Hilfebedarf beim Ankleiden vollständig', massnahme:'An- und Auskleiden vollständig übernehmen oder anleiten, auf Kleidungswünsche eingehen', ziel:'Kleidung angezogen, Selbstbestimmung gefördert', details:[] },
    { atl:'Körperpflege', kat:'Körperpflege', symptom:'Mund- und Zahnhygiene erschwert', massnahme:'Zahnpflege morgens und abends durchführen, Prothesen reinigen, Schleimhaut beurteilen', ziel:'Mundgesundheit erhalten, Aspiration vermieden', details:[] },
    { atl:'Körperpflege', kat:'Körperpflege', symptom:'Prothesenpflege erforderlich', massnahme:'Prothesen täglich reinigen und auf Sitz prüfen, Druckstellen beobachten, Lagerung über Nacht', ziel:'Druckstellen vermieden, Prothese hygienisch', details:[] },
    { atl:'Körperpflege', kat:'Körperpflege', symptom:'Rasur erforderlich (Mann)', massnahme:'Rasur durchführen oder unterstützen, Hautverträglichkeit beachten, Wunsch der Person einbeziehen', ziel:'Hygiene und Wohlbefinden gesichert', details:[] },
    { atl:'Körperpflege', kat:'Körperpflege', symptom:'Augenpflege erforderlich', massnahme:'Augen reinigen, Ablagerungen entfernen, bei Auffälligkeiten dokumentieren und weiterleiten', ziel:'Augenkomfort und Hygiene gewährleistet', details:[] },

    // 3 Ernährung und Trinken
    { atl:'Essen & Trinken', kat:'Ernährung & Flüssigkeit', symptom:'Geringe Nahrungsaufnahme', massnahme:'Ernährungsprotokoll führen, kleine Portionen, Lieblingsmahlzeiten anbieten, Essbegleitung', ziel:'Ausreichende Kalorienaufnahme sichergestellt', details:[] },
    { atl:'Essen & Trinken', kat:'Ernährung & Flüssigkeit', symptom:'Dehydrationsrisiko', massnahme:'Trinkplan einführen, bevorzugte Getränke anbieten, Trinkmenge dokumentieren', ziel:'Flüssigkeitsbedarf täglich gedeckt', details:[] },
    { atl:'Essen & Trinken', kat:'Ernährung & Flüssigkeit', symptom:'Schluckstörung (Dysphagie)', massnahme:'Konsistenz nach Anordnung anpassen, aufrechte Sitzposition, Schlucktraining nach Anordnung begleiten', ziel:'Aspirationsrisiko minimiert, Ernährung sicher', details:[] },
    { atl:'Essen & Trinken', kat:'Ernährung & Flüssigkeit', symptom:'Appetitlosigkeit / fehlendes Hungergefühl', massnahme:'Wunschkost berücksichtigen, angenehme Essatmosphäre schaffen, kleine häufige Mahlzeiten', ziel:'Nahrungsaufnahme verbessert', details:[] },
    { atl:'Essen & Trinken', kat:'Ernährung & Flüssigkeit', symptom:'Mangelernährung / Gewichtsverlust', massnahme:'Gewicht regelmäßig kontrollieren, Hochkalorische Kost nach Anordnung, Ernährungsberatung einleiten', ziel:'Gewicht stabilisiert, Mangelernährung gestoppt', details:[] },
    { atl:'Essen & Trinken', kat:'Ernährung & Flüssigkeit', symptom:'Unterstützung beim Essen erforderlich', massnahme:'Essen reichen, Hilfsmittel nutzen (angepasstes Besteck), Selbstständigkeit fördern', ziel:'Ausreichende Nahrungsaufnahme mit geringstmöglicher Unterstützung', details:[] },
    { atl:'Essen & Trinken', kat:'Ernährung & Flüssigkeit', symptom:'Sondenkost / PEG-Versorgung', massnahme:'PEG-Pflege nach Anordnung, Sondenkostgabe durchführen, Stoma und Schlauch beobachten', ziel:'Komplikationsfreie Sondenkostgabe, PEG intakt', details:[] },
    { atl:'Essen & Trinken', kat:'Ernährung & Flüssigkeit', symptom:'Fehlende Sitzstabilität beim Essen', massnahme:'Sitzposition sichern, Kissen oder Hilfsmittel einsetzen, Sturz beim Essen vermeiden', ziel:'Sichere Körperhaltung beim Essen gewährleistet', details:[] },
    { atl:'Essen & Trinken', kat:'Ernährung & Flüssigkeit', symptom:'Kostanpassung bei Erkrankung erforderlich', massnahme:'Spezialdiät nach Anordnung einhalten, über Kostform informieren, Einhaltung dokumentieren', ziel:'Diätvorschriften werden eingehalten', details:[] },

    // 4 Ausscheidung
    { atl:'Ausscheiden', kat:'Ausscheidung', symptom:'Harninkontinenz (belastend)', massnahme:'Inkontinenzversorgung wechseln, Hautschutz anwenden, Toilettentraining anbieten', ziel:'Haut intakt, Würde erhalten', details:[] },
    { atl:'Ausscheiden', kat:'Ausscheidung', symptom:'Obstipation / Verstopfung', massnahme:'Flüssigkeit fördern, ballaststoffreiche Kost, Bewegung anregen, Laxans nach Anordnung', ziel:'Regelmäßige Darmtätigkeit wiederhergestellt', details:[] },
    { atl:'Ausscheiden', kat:'Ausscheidung', symptom:'Durchfall', massnahme:'Flüssigkeitszufuhr sicherstellen, Haut bei Inkontinenz schützen, Elektrolyte nach Anordnung, Ursache beobachten', ziel:'Ausscheidung normalisiert, Dehydration verhindert', details:[] },
    { atl:'Ausscheiden', kat:'Ausscheidung', symptom:'Harnverhalt', massnahme:'Blasentraining unterstützen, Hinweiszeichen erkennen, Katheter nach Anordnung, Arzt informieren', ziel:'Blasenentleerung sichergestellt', details:[] },
    { atl:'Ausscheiden', kat:'Ausscheidung', symptom:'Dauerkatheter vorhanden', massnahme:'Katheter nach Anordnung pflegen, Hygiene einhalten, Rötungen oder Ausfluss dokumentieren', ziel:'Infektionsrisiko minimiert, Katheter funktionsfähig', details:[] },
    { atl:'Ausscheiden', kat:'Ausscheidung', symptom:'Stomaversorgung erforderlich', massnahme:'Stoma nach Anordnung versorgen, Beutel wechseln, Haut um das Stoma beobachten', ziel:'Stoma komplikationslos versorgt, Haut intakt', details:[] },
    { atl:'Ausscheiden', kat:'Ausscheidung', symptom:'Toilettentraining notwendig', massnahme:'Regelmäßige Toilettengänge zu festen Zeiten anbieten, Protokoll führen', ziel:'Kontinenz verbessert, Unfälle reduziert', details:[] },
    { atl:'Ausscheiden', kat:'Ausscheidung', symptom:'Hautschutz bei Inkontinenz erforderlich', massnahme:'Barrierecreme auftragen, feuchte Haut sofort trocknen, geeignete Inkontinenzprodukte wählen', ziel:'Inkontinenzdermatitis vermieden', details:[] },
    { atl:'Ausscheiden', kat:'Ausscheidung', symptom:'Harnwegsinfekt-Zeichen beobachtet', massnahme:'Symptome dokumentieren und weiterleiten, Trinkmenge erhöhen, Hygiene verstärken', ziel:'Infektion früh erkannt und behandelt', details:[] },

    // 5 Behandlungspflege
    { atl:'Essen & Trinken', kat:'Behandlungspflege', symptom:'Infusion vorbereiten (nach Anordnung)', massnahme:'Infusion nach ärztlicher Anordnung vorbereiten, hygienisch arbeiten, Material bereitstellen', ziel:'Infusion sicher und korrekt vorbereitet', details:[] },
    { atl:'Essen & Trinken', kat:'Behandlungspflege', symptom:'Infusion überwachen', massnahme:'Laufrate prüfen, Zugang beobachten, Verträglichkeit kontrollieren, Auffälligkeiten weiterleiten', ziel:'Komplikationsfreie Infusionsgabe', details:[] },
    { atl:'Essen & Trinken', kat:'Behandlungspflege', symptom:'Infusionszugang vorhanden / Infektionsrisiko', massnahme:'Einstichstelle kontrollieren, Verband sauber und trocken halten, hygienisch arbeiten, Auffälligkeiten dokumentieren', ziel:'Keine Infektionszeichen, Zugang bleibt nutzbar', details:[] },
    { atl:'Essen & Trinken', kat:'Behandlungspflege', symptom:'Rötung oder Schwellung an Einstichstelle', massnahme:'Befund dokumentieren und sofort weiterleiten, Infusion stoppen nach Anordnung, Arzt informieren', ziel:'Komplikation frühzeitig erkannt und behandelt', details:[] },
    { atl:'Essen & Trinken', kat:'Behandlungspflege', symptom:'Paravasat-Risiko bei Infusion', massnahme:'Einlaufstelle regelmäßig prüfen, Schwellung oder Kälte sofort melden, Infusion nach Anordnung stoppen', ziel:'Paravasat verhindert oder früh erkannt', details:[] },
    { atl:'Essen & Trinken', kat:'Behandlungspflege', symptom:'Medikamentengabe nach ärztlicher Anordnung', massnahme:'Medikament nach Anordnung vorbereiten und verabreichen, 5R-Regel anwenden, dokumentieren', ziel:'Korrekte und sichere Medikamentengabe', details:[] },
    { atl:'Essen & Trinken', kat:'Behandlungspflege', symptom:'Medikamenteneinnahme unsicher / Vergessen', massnahme:'Einnahme überwachen, Erklären, Pillendose vorbereiten, Reminder setzen', ziel:'Therapietreue verbessert', details:[] },
    { atl:'Essen & Trinken', kat:'Behandlungspflege', symptom:'Subkutane Injektion (nach Anordnung)', massnahme:'Subkutane Injektion nach Anordnung durchführen, Injektionsstellen rotieren, Auffälligkeiten notieren', ziel:'Injektion sicher und komplikationslos', details:[] },
    { atl:'Essen & Trinken', kat:'Behandlungspflege', symptom:'Insulingabe erforderlich', massnahme:'Blutzucker messen, Insulin nach Anordnung berechnen und spritzen, Injektionsstellen rotieren', ziel:'BZ-Werte im Zielbereich, Injektion korrekt', details:[] },
    { atl:'Essen & Trinken', kat:'Behandlungspflege', symptom:'Blutzuckerkontrolle erforderlich', massnahme:'BZ zu festgelegten Zeiten messen, Werte dokumentieren und weiterleiten, Abweichungen melden', ziel:'BZ-Verlauf kontrolliert, Handlungsbedarf erkannt', details:[] },
    { atl:'Sich bewegen', kat:'Behandlungspflege', symptom:'Blutdruckkontrolle erforderlich', massnahme:'Blutdruck zu festgelegten Zeiten messen, korrekte Manschettenanlage, Werte dokumentieren', ziel:'Blutdruckverlauf überwacht, Abweichungen erkannt', details:[] },
    { atl:'Sich bewegen', kat:'Behandlungspflege', symptom:'Vitalzeichenkontrolle erforderlich', massnahme:'Puls, Temperatur, Blutdruck, SpO2 nach Anordnung messen und dokumentieren', ziel:'Frühzeitiges Erkennen von Veränderungen', details:[] },
    { atl:'Sich bewegen', kat:'Behandlungspflege', symptom:'Sauerstoffgabe erforderlich', massnahme:'O2-Sonde/Maske nach Anordnung anlegen, Flussrate einstellen, SpO2 kontrollieren', ziel:'Ausreichende Sauerstoffversorgung sichergestellt', details:[] },
    { atl:'Sich bewegen', kat:'Behandlungspflege', symptom:'Absaugung nach Qualifikation und Anordnung erforderlich', massnahme:'Absaugung nach Anordnung durchführen, hygienisch und schonend vorgehen, Sekret beurteilen', ziel:'Atemwege frei, Aspiration verhindert', details:[] },
    { atl:'Essen & Trinken', kat:'Behandlungspflege', symptom:'Nebenwirkungsbeobachtung nach Medikament', massnahme:'Bekannte Nebenwirkungen beobachten, Symptome dokumentieren, bei Auffälligkeiten weiterleiten', ziel:'Nebenwirkungen früh erkannt, Sicherheit gewährleistet', details:[] },

    // 6 Wunde und Haut
    { atl:'Körperpflege', kat:'Wunde & Haut', symptom:'Wundversorgung erforderlich', massnahme:'Wunde nach Anordnung versorgen, Wundzustand beurteilen, Wundprotokoll führen', ziel:'Wundheilung wird unterstützt', details:[] },
    { atl:'Körperpflege', kat:'Wunde & Haut', symptom:'Verbandwechsel notwendig', massnahme:'Verbandwechsel nach Anordnung und Hygienestandard durchführen, Material bereitstellen, dokumentieren', ziel:'Wunde sauber und gut versorgt', details:[] },
    { atl:'Körperpflege', kat:'Wunde & Haut', symptom:'Dekubitusrisiko erhöht', massnahme:'Risikoeinschätzung, Lagerungsintervalle einhalten, Druckentlastung, Hautpflege', ziel:'Dekubitus verhindert', details:[] },
    { atl:'Körperpflege', kat:'Wunde & Haut', symptom:'Bestehender Dekubitus', massnahme:'Dekubitus nach Anordnung versorgen, Druckentlastung sichern, Lage des Dekubitus dokumentieren', ziel:'Heilungsfortschritt gefördert, weitere Schädigung verhindert', details:[] },
    { atl:'Körperpflege', kat:'Wunde & Haut', symptom:'Hautrötung / Druckstelle', massnahme:'Rötung dokumentieren, Druck entlasten, Ursache suchen und beseitigen', ziel:'Druckstelle heilt ab, kein Dekubitus', details:[] },
    { atl:'Körperpflege', kat:'Wunde & Haut', symptom:'Hautmazeration bei Feuchtigkeit', massnahme:'Feuchte Haut trocknen, Barrierepflege, Inkontinenzversorgung optimieren', ziel:'Haut trocknet ab, Mazeration verhindert', details:[] },
    { atl:'Körperpflege', kat:'Wunde & Haut', symptom:'Infektionsrisiko bei bestehender Wunde', massnahme:'Hygiene bei Verbandwechsel einhalten, Infektionszeichen beobachten, weiterleiten', ziel:'Wundinfektion verhindert', details:[] },
    { atl:'Körperpflege', kat:'Wunde & Haut', symptom:'Wundschmerzen', massnahme:'Schmerz bei Verbandwechsel ansprechen, schonend vorgehen, Analgesie nach Anordnung vorab', ziel:'Schmerz während Wundversorgung minimiert', details:[] },
    { atl:'Körperpflege', kat:'Wunde & Haut', symptom:'Ödeme an den Extremitäten', massnahme:'Lagerung, Kompression nach Anordnung, Bewegung fördern, Flüssigkeit dokumentieren', ziel:'Ödeme reduziert, Haut geschützt', details:[] },
    { atl:'Körperpflege', kat:'Wunde & Haut', symptom:'Trockene und spröde Haut', massnahme:'Rückfettende Pflege täglich auftragen, reizstofffrei waschen, Hautzustand beobachten', ziel:'Haut bleibt geschmeidig und intakt', details:[] },

    // 7 Schmerz
    { atl:'Sich bewegen', kat:'Schmerz', symptom:'Akuter Schmerz', massnahme:'Schmerz einschätzen (Skala), Analgesie nach Anordnung, Lagerung, Ablenkung anbieten', ziel:'Schmerz reduziert, Wohlbefinden verbessert', details:[] },
    { atl:'Sich bewegen', kat:'Schmerz', symptom:'Chronischer Schmerz', massnahme:'Schmerzprotokoll führen, Analgesie nach Anordnung regelmäßig geben, entlastende Lagerung', ziel:'Chronischer Schmerz beherrschbar, Lebensqualität erhalten', details:[] },
    { atl:'Sich bewegen', kat:'Schmerz', symptom:'Bewegungsschmerz', massnahme:'Schmerz vor Mobilisation erfassen, Analgesie rechtzeitig nach Anordnung, schonende Bewegung', ziel:'Mobilisation mit erträglichem Schmerzniveau', details:[] },
    { atl:'Sich bewegen', kat:'Schmerz', symptom:'Ruheschmerz', massnahme:'Analgesie nach Anordnung, entlastende Lagerung, Wärmeanwendung nach Anordnung', ziel:'Ruheschmerz gelindert, Schlaf möglich', details:[] },
    { atl:'Sich bewegen', kat:'Schmerz', symptom:'Schmerzen bei der Wundversorgung', massnahme:'Analgesie vor Verbandwechsel nach Anordnung, schonend arbeiten, kurze Pausen einbauen', ziel:'Verbandwechsel so schmerzarm wie möglich', details:[] },
    { atl:'Essen & Trinken', kat:'Schmerz', symptom:'Schmerzmittelwirkung beobachten', massnahme:'Wirkung nach Einnahme einschätzen, NRS-Wert dokumentieren, Rückmeldung an Arzt', ziel:'Schmerztherapie optimiert', details:[] },

    // 8 Atmung
    { atl:'Sich bewegen', kat:'Atmung', symptom:'Atemnot in Ruhe', massnahme:'Oberkörper hochlagern, O2 nach Anordnung, Atemübungen anleiten, Ruhe fördern', ziel:'Atemnot gelindert, Atemarbeit reduziert', details:[] },
    { atl:'Sich bewegen', kat:'Atmung', symptom:'Belastungsdyspnoe', massnahme:'Belastungen dosieren, Pausen einbauen, Atemtechnik anleiten, O2 nach Anordnung', ziel:'Dyspnoe bei Belastung reduziert', details:[] },
    { atl:'Sich bewegen', kat:'Atmung', symptom:'Sekretansammlung / zäher Schleim', massnahme:'Inhalation nach Anordnung, Flüssigkeit fördern, Atemübungen, Klopfmassage nach Anordnung', ziel:'Sekret gelöst, Husten produktiv', details:[] },
    { atl:'Sich bewegen', kat:'Atmung', symptom:'Anhaltender Husten', massnahme:'Husten beobachten (produktiv/trocken), Auslöser erkennen, Flüssigkeit fördern, Arzt informieren', ziel:'Husten gelindert, Ursache behandelt', details:[] },
    { atl:'Sich bewegen', kat:'Atmung', symptom:'COPD – stabile Phase', massnahme:'Inhalation nach Anordnung, Atemübungen, Belastungsdosierung, auf Exazerbationszeichen achten', ziel:'Stabile Atemfunktion erhalten', details:[] },
    { atl:'Sich bewegen', kat:'Atmung', symptom:'Erhöhter Sauerstoffbedarf', massnahme:'SpO2 kontrollieren, O2-Gabe nach Anordnung, Wirkung dokumentieren', ziel:'SpO2 im Zielbereich', details:[] },
    { atl:'Kommunizieren', kat:'Atmung', symptom:'Atemangst', massnahme:'Beruhigen, aufrechte Position, Umgebung lüften, Atemtechnik anleiten, bei Bedarf Arzt', ziel:'Angst reduziert, Atemnot beherrschbar', details:[] },

    // 9 Demenz und Orientierung
    { atl:'Kommunizieren', kat:'Kognition & Orientierung', symptom:'Ausgeprägte Desorientierung', massnahme:'Orientierungshilfen einsetzen, Tagesstruktur bieten, Validation und Realitätsorientierung', ziel:'Orientierung verbessert, Sicherheit erhöht', details:[] },
    { atl:'Kommunizieren', kat:'Kognition & Orientierung', symptom:'Vergesslichkeit / Gedächtnisabbau', massnahme:'Gedächtnisstützen bereitstellen, Routinen fördern, ruhig erklären, Angehörige einbinden', ziel:'Alltagskompetenz so lang wie möglich erhalten', details:[] },
    { atl:'Kommunizieren', kat:'Kognition & Orientierung', symptom:'Unruhe / Agitiertheit', massnahme:'Auslöser erkennen, beruhigen, bekannte Objekte einsetzen, Ablenkung anbieten, dokumentieren', ziel:'Unruhe gelindert, Wohlbefinden gesteigert', details:[] },
    { atl:'Kommunizieren', kat:'Kognition & Orientierung', symptom:'Weglauftendenz / Hinlaufen', massnahme:'Sicherheitsmaßnahmen nach Anordnung, Beschäftigung anbieten, Bewegungsdrang ernst nehmen', ziel:'Sicherheit gewährleistet, Verletzungen vermieden', details:[] },
    { atl:'Schlafen', kat:'Kognition & Orientierung', symptom:'Tag-Nacht-Umkehr', massnahme:'Tagsüber aktiv halten, Licht tagsüber fördern, abends beruhigen, Schlafrituale einführen', ziel:'Tag-Nacht-Rhythmus normalisiert', details:[] },
    { atl:'Kommunizieren', kat:'Kognition & Orientierung', symptom:'Angst bei Demenz', massnahme:'Behutsam nähern, beruhigen, Sicherheit vermitteln, bekannte Personen einbeziehen', ziel:'Angst reduziert, Vertrauen aufgebaut', details:[] },
    { atl:'Kommunizieren', kat:'Kognition & Orientierung', symptom:'Herausforderndes Verhalten', massnahme:'Auslöser erkennen, deeskalierend kommunizieren, Strategie dokumentieren, Team informieren', ziel:'Situation deeskaliert, Sicherheit für alle erhalten', details:[] },
    { atl:'Kommunizieren', kat:'Kognition & Orientierung', symptom:'Fehlende Krankheitseinsicht', massnahme:'Sanft informieren, nicht korrigieren, Sicherheit im Vordergrund, Angehörige einbinden', ziel:'Kooperation gefördert, Konflikte vermieden', details:[] },

    // 10 Schlaf und Ruhe
    { atl:'Schlafen', kat:'Schlaf & Ruhe', symptom:'Einschlafstörung', massnahme:'Schlafrituale einführen, Schlafumgebung optimieren, Abendaktivitäten beruhigen', ziel:'Einschlafen erleichtert', details:[] },
    { atl:'Schlafen', kat:'Schlaf & Ruhe', symptom:'Durchschlafstörung', massnahme:'Ursachen erfassen (Schmerz, Harndrang), gezielt entgegenwirken, Schlafprotokoll führen', ziel:'Durchschlafqualität verbessert', details:[] },
    { atl:'Schlafen', kat:'Schlaf & Ruhe', symptom:'Nächtliche Unruhe', massnahme:'Ruhige Umgebung schaffen, beruhigen, Licht dosieren, Schmerz oder Harndrang ausschließen', ziel:'Ruhige Nacht gefördert', details:[] },
    { atl:'Schlafen', kat:'Schlaf & Ruhe', symptom:'Schmerzen in der Nacht', massnahme:'Analgesie nach Anordnung rechtzeitig geben, Lagerung optimieren, Schlafkomfort steigern', ziel:'Nacht schmerzfrei oder schmerzarm', details:[] },
    { atl:'Schlafen', kat:'Schlaf & Ruhe', symptom:'Angst in der Nacht', massnahme:'Kurzbesuche einplanen, Nachtlicht, Klingel erreichbar, beruhigend kommunizieren', ziel:'Sicherheitsgefühl gestärkt, Angst reduziert', details:[] },
    { atl:'Schlafen', kat:'Schlaf & Ruhe', symptom:'Fehlender Tag-Nacht-Rhythmus', massnahme:'Tagsüber Aktivierung, Schlafen am Tag reduzieren, abends ruhige Aktivitäten', ziel:'Stabiler Schlaf-Wach-Rhythmus', details:[] },

    // 11 Prophylaxen
    { atl:'Sich bewegen', kat:'Prophylaxen', symptom:'Sturzprophylaxe notwendig', massnahme:'Umgebung sichern, Hilfsmittel bereitstellen, Schuhwerk prüfen, Nachtlicht einsetzen', ziel:'Stürze verhindert', details:[] },
    { atl:'Sich bewegen', kat:'Prophylaxen', symptom:'Intertrigoprophylaxe erforderlich', massnahme:'Hautfalten täglich reinigen und trocken halten, Barrierepflege, Feuchtigkeitsschutz', ziel:'Intertrigo verhindert, Haut intakt', details:[] },
    { atl:'Ausscheiden', kat:'Prophylaxen', symptom:'Obstipationsprophylaxe notwendig', massnahme:'Ballaststoffreich ernähren, Flüssigkeit fördern, Bewegung anregen, Ausscheidung dokumentieren', ziel:'Regelmäßige Darmtätigkeit erhalten', details:[] },
    { atl:'Essen & Trinken', kat:'Prophylaxen', symptom:'Dehydrationsprophylaxe notwendig', massnahme:'Tägliche Trinkmenge sicherstellen, Trinkplan einhalten, bevorzugte Getränke anbieten', ziel:'Dehydration verhindert', details:[] },
    { atl:'Essen & Trinken', kat:'Prophylaxen', symptom:'Aspirationsprophylaxe notwendig', massnahme:'Aufrechte Sitzposition beim Essen, Konsistenz anpassen, langsam essen lassen, Bewusstsein prüfen', ziel:'Aspiration verhindert', details:[] },
    { atl:'Körperpflege', kat:'Prophylaxen', symptom:'Pneumonieprophylaxe (Bettlägerigkeit)', massnahme:'Atemübungen anleiten, Oberkörper hochlagern, regelmäßig mobilisieren, Flüssigkeit fördern', ziel:'Pneumonie vermieden', details:[] },

    // 12 Betreuung und Alltag
    { atl:'Kommunizieren', kat:'Soziales & Alltag', symptom:'Einsamkeit / soziale Isolation', massnahme:'Gespräche anbieten, Besuchsdienste empfehlen, Aktivitäten einplanen, Angehörige einbinden', ziel:'Soziale Kontakte verbessert, Einsamkeit reduziert', details:[] },
    { atl:'Kommunizieren', kat:'Soziales & Alltag', symptom:'Fehlende Tagesstruktur', massnahme:'Tagesplan gemeinsam erstellen, feste Routinen einführen, Aktivitäten sinnvoll einplanen', ziel:'Stabile Tagesstruktur etabliert', details:[] },
    { atl:'Kommunizieren', kat:'Soziales & Alltag', symptom:'Eingeschränkte Alltagskompetenz', massnahme:'Alltagshandlungen unterstützen und anleiten, Ressourcen fördern, Hilfsmittel einsetzen', ziel:'Selbstständigkeit im Alltag so lange wie möglich erhalten', details:[] },
    { atl:'Kommunizieren', kat:'Soziales & Alltag', symptom:'Unterstützungsbedarf im Haushalt', massnahme:'Haushaltstätigkeiten unterstützen oder übernehmen, Sicherheit bei der Arbeit gewährleisten', ziel:'Haushalt bewältigbar, Sicherheit gewahrt', details:[] },
    { atl:'Kommunizieren', kat:'Soziales & Alltag', symptom:'Angehörige belastet / überlastet', massnahme:'Angehörige ansprechen, Entlastungsangebote informieren, Pflegeberatung empfehlen', ziel:'Angehörige entlastet, Pflegequalität erhalten', details:[] },
    { atl:'Kommunizieren', kat:'Soziales & Alltag', symptom:'Fehlende Beschäftigung / Langeweile', massnahme:'Interessensgerechte Aktivitäten anbieten, Hobby fördern, einfache Alltagshandlungen einbinden', ziel:'Lebensqualität durch sinnvolle Beschäftigung gesteigert', details:[] },
    { atl:'Kommunizieren', kat:'Soziales & Alltag', symptom:'Aktivierungsbedarf vorhanden', massnahme:'Bewegung, Kommunikation und kognitive Aufgaben in den Alltag integrieren', ziel:'Ressourcen genutzt, Wohlbefinden gefördert', details:[] },
    { atl:'Kommunizieren', kat:'Soziales & Alltag', symptom:'Trauer / emotionale Belastung', massnahme:'Empathisch zuhören, Zeit lassen, professionelle Unterstützung vermitteln wenn nötig', ziel:'Emotionale Belastung verringert, Vertrauen aufgebaut', details:[] },

    // 13 Notfall und Risiko
    { atl:'Sich bewegen', kat:'Notfall & Risiko', symptom:'Akute Verschlechterung des Zustands', massnahme:'Vitalzeichen messen, Arzt/Notruf nach Anordnung informieren, Situation dokumentieren', ziel:'Verschlechterung früh erkannt, Maßnahmen eingeleitet', details:[] },
    { atl:'Sich bewegen', kat:'Notfall & Risiko', symptom:'Sturzereignis eingetreten', massnahme:'Verletzungen einschätzen, nicht alleine bewegen, Arzt informieren, Sturzprotokoll erstellen', ziel:'Folgeschäden minimiert, Ursache analysiert', details:[] },
    { atl:'Sich bewegen', kat:'Notfall & Risiko', symptom:'Fieber', massnahme:'Temperatur messen und dokumentieren, Flüssigkeit fördern, Arzt informieren, Antipyretikum nach Anordnung', ziel:'Körpertemperatur normalisiert, Ursache abgeklärt', details:[] },
    { atl:'Kommunizieren', kat:'Notfall & Risiko', symptom:'Plötzliche Verwirrtheit / Desorientiertheit', massnahme:'Situation einschätzen, Reorientierung versuchen, Ursache suchen, Arzt informieren', ziel:'Delir erkannt, Sicherheit gewährleistet', details:[] },
    { atl:'Sich bewegen', kat:'Notfall & Risiko', symptom:'Allergische Reaktion beobachtet', massnahme:'Auslöser entfernen, Symptome dokumentieren, Arzt/Notruf nach Schwere, Antiallergikum nach Anordnung', ziel:'Reaktion gestoppt, Sicherheit hergestellt', details:[] },
    { atl:'Sich bewegen', kat:'Notfall & Risiko', symptom:'Kreislaufprobleme / Kollaps', massnahme:'Flache Lagerung, Beine hochlagern, Vitalzeichen messen, Arzt informieren, Notruf wenn nötig', ziel:'Kreislauf stabilisiert', details:[] },
    { atl:'Essen & Trinken', kat:'Notfall & Risiko', symptom:'Unterzuckerung (Hypoglykämie)', massnahme:'Schnell wirksame Kohlenhydrate geben, BZ messen, Arzt informieren, dokumentieren', ziel:'BZ normalisiert, Bewusstsein erhalten', details:[] },
    { atl:'Essen & Trinken', kat:'Notfall & Risiko', symptom:'Überzuckerung (Hyperglykämie)', massnahme:'BZ messen, Flüssigkeit anbieten, Arzt informieren, Insulingabe nach Anordnung', ziel:'BZ in Zielbereich gesenkt', details:[] },
    { atl:'Sich bewegen', kat:'Notfall & Risiko', symptom:'Akute Atemnot', massnahme:'Oberkörper hochlagern, O2 nach Anordnung, Arzt/Notruf informieren, beruhigen', ziel:'Atemnot gelindert, Versorgung gesichert', details:[] },
    { atl:'Sich bewegen', kat:'Notfall & Risiko', symptom:'Akute Schmerzen (unbekannte Ursache)', massnahme:'Schmerz einschätzen, Arzt informieren, Analgesie nach Anordnung, Lagerung, dokumentieren', ziel:'Schmerz gelindert, Ursache abgeklärt', details:[] },

    // 14 Palliativpflege
    { atl:'Sich bewegen', kat:'Palliativpflege', symptom:'Schmerzen in palliativer Situation', massnahme:'Schmerztherapie nach Anordnung regelmäßig und konsequent durchführen, Wirkung beurteilen', ziel:'Schmerzfreiheit oder Schmerzarmut angestrebt', details:[] },
    { atl:'Sich bewegen', kat:'Palliativpflege', symptom:'Atemnot in palliativer Situation', massnahme:'Lagerung, Lüften, O2 nach Anordnung, Opioide nach Anordnung, Ruhe und Nähe', ziel:'Luftnot gelindert, Würde gewahrt', details:[] },
    { atl:'Kommunizieren', kat:'Palliativpflege', symptom:'Angst und Unruhe in Sterbephase', massnahme:'Beruhigende Präsenz, Sedation nach Anordnung, vertraute Personen einbeziehen', ziel:'Angst gelindert, ruhige Sterbebegleitung', details:[] },
    { atl:'Körperpflege', kat:'Palliativpflege', symptom:'Mundtrockenheit in palliativer Situation', massnahme:'Mundpflege häufig, Lippen befeuchten, angenehme Geschmacksstoffe anbieten', ziel:'Mundkomfort verbessert, Durstgefühl gelindert', details:[] },
    { atl:'Sich bewegen', kat:'Palliativpflege', symptom:'Extreme Schwäche / Kachexie', massnahme:'Unterstützung bei allen Aktivitäten, Energie sparen, Würde und Autonomie respektieren', ziel:'Würde erhalten, Ressourcen geschont', details:[] },
    { atl:'Essen & Trinken', kat:'Palliativpflege', symptom:'Übelkeit und Erbrechen (Palliativ)', massnahme:'Antiemetika nach Anordnung, kleine Portionen, Lieblingsgerüche meiden, Umgebung anpassen', ziel:'Übelkeit gelindert, Wohlbefinden verbessert', details:[] },
    { atl:'Kommunizieren', kat:'Palliativpflege', symptom:'Angehörigenbegleitung in der Sterbephase', massnahme:'Angehörige informieren, emotionale Unterstützung anbieten, Abschied ermöglichen', ziel:'Angehörige begleitet, Abschied würdevoll', details:[] },
    { atl:'Kommunizieren', kat:'Palliativpflege', symptom:'Kommunikation erschwert (sterbend)', massnahme:'Nonverbale Kommunikation nutzen, Berührung, Stimme, Nähe anbieten', ziel:'Würde und Verbindung bis zuletzt', details:[] },

    // 15 Reisebegleitung / Akuteinsätze
    { atl:'Sich bewegen', kat:'Reise & Akuteinsatz', symptom:'Mobilitätsunterstützung bei Reise / Fahrt', massnahme:'Transfer in Fahrzeug sichern, Hilfsmittel mitführen, Pausen einplanen', ziel:'Sicherer Transport gewährleistet', details:[] },
    { atl:'Essen & Trinken', kat:'Reise & Akuteinsatz', symptom:'Medikamentensicherheit während Reise', massnahme:'Medikamente vollständig mitnehmen, Kühlpflicht beachten, Einnahmezeiten einhalten', ziel:'Keine Medikamentenpause, sicherer Transport', details:[] },
    { atl:'Ausscheiden', kat:'Reise & Akuteinsatz', symptom:'Toilettenhilfe während Reise', massnahme:'Toilettengänge vor und während Reise planen, Inkontinenzversorgung dabei, Orte kennen', ziel:'Kontinenzversorgung auf Reise gewährleistet', details:[] },
    { atl:'Kommunizieren', kat:'Reise & Akuteinsatz', symptom:'Orientierung in fremder Umgebung eingeschränkt', massnahme:'Begleitung sicherstellen, bekannte Gegenstände mitnehmen, ruhig erklären, nicht alleine lassen', ziel:'Sicherheit in fremder Umgebung gewährleistet', details:[] },
    { atl:'Sich bewegen', kat:'Reise & Akuteinsatz', symptom:'Erschöpfung während Reise / Einsatz', massnahme:'Pausen einplanen, Energie dosieren, Vitalzeichen beobachten, auf Beschwerden reagieren', ziel:'Erschöpfung verhindert, Wohlbefinden erhalten', details:[] },
    { atl:'Sich bewegen', kat:'Reise & Akuteinsatz', symptom:'Notfallbereitschaft während Reise sicherstellen', massnahme:'Notfallkontakte mitführen, Notfallset dabei, Arztbrief verfügbar, Telefon geladen', ziel:'Im Notfall sofort handlungsfähig', details:[] },

    // Weitere Ergänzungen für vollständige Abdeckung
    { atl:'Körperpflege', kat:'Körperpflege', symptom:'Körperpflege wird abgelehnt', massnahme:'Vertrauen aufbauen, Ablehnung respektieren, Zeitpunkt anpassen, Angehörige einbeziehen', ziel:'Körperpflege schrittweise möglich, Würde gewahrt', details:[] },
    { atl:'Sich bewegen', kat:'Mobilität', symptom:'Muskelabbau / Sarkopenie', massnahme:'Tägliche Bewegungsübungen, proteinreiche Ernährung nach Anordnung, Aktivierung fördern', ziel:'Muskelabbau verlangsamt', details:[] },
    { atl:'Essen & Trinken', kat:'Ernährung & Flüssigkeit', symptom:'Ernährung bei Schluckproblemen unsicher', massnahme:'Getränke andicken, weiche Kost vorbereiten, langsam füttern, Schluckablauf beobachten', ziel:'Sichere Nahrungsaufnahme ohne Aspiration', details:[] },
    { atl:'Sich bewegen', kat:'Sicherheit & Sturz', symptom:'Sturz in der Anamnese (Sturzvorgeschichte)', massnahme:'Sturzrisiko neu einschätzen, Hilfsmittel prüfen, Umgebung anpassen, Bewegungssicherheit trainieren', ziel:'Erneuter Sturz verhindert', details:[] },
    { atl:'Körperpflege', kat:'Wunde & Haut', symptom:'Chronische Wunde / Ulkus', massnahme:'Wundversorgung nach Anordnung, Wunddokumentation regelmäßig, Ursachenbehandlung unterstützen', ziel:'Chronische Wunde unter Kontrolle', details:[] },
    { atl:'Sich bewegen', kat:'Atmung', symptom:'Pneumonie / Lungenentzündung (Verlauf)', massnahme:'Atemübungen, Positionierung, Vitalzeichen überwachen, Antibiotika nach Anordnung begleiten', ziel:'Genesungsverlauf unterstützt', details:[] },
    { atl:'Kommunizieren', kat:'Soziales & Alltag', symptom:'Sprachbarriere / Verständigungsprobleme', massnahme:'Einfache Sprache, Bildkarten, Dolmetscher einbeziehen, Geduld zeigen', ziel:'Kommunikation gelingt trotz Barriere', details:[] },
    { atl:'Essen & Trinken', kat:'Behandlungspflege', symptom:'Wundspülung erforderlich', massnahme:'Wunde nach Anordnung spülen, geeignetes Spülmittel verwenden, Wundzustand beurteilen', ziel:'Wunde sauber, Heilung gefördert', details:[] },
    { atl:'Essen & Trinken', kat:'Behandlungspflege', symptom:'Augentropfen / Salbe nach Anordnung', massnahme:'Augentropfen/-salbe nach Anordnung verabreichen, hygienisch, Wirkung beobachten', ziel:'Augenbehandlung korrekt durchgeführt', details:[] },
    { atl:'Essen & Trinken', kat:'Behandlungspflege', symptom:'Ohrentropfen nach Anordnung', massnahme:'Ohrentropfen nach Anordnung verabreichen, korrekte Seitenlage, Wirkung beobachten', ziel:'Ohrenbehandlung sicher durchgeführt', details:[] },
    { atl:'Körperpflege', kat:'Körperpflege', symptom:'Ganzkörperpflege im Bett erforderlich', massnahme:'Bettbad durchführen, warmes Wasser, angenehme Temperatur, Hautstatus beurteilen', ziel:'Hygiene sichergestellt, Wohlbefinden gefördert', details:[] },
    { atl:'Körperpflege', kat:'Wunde & Haut', symptom:'Eingewachsener Zehennagel / auffälliger Befund', massnahme:'Befund dokumentieren und weiterleiten, keine eigenständige Behandlung, Podologie empfehlen', ziel:'Fachgerechte Behandlung veranlasst', details:[] },
    { atl:'Sich bewegen', kat:'Prophylaxen', symptom:'Thromboseprophylaxe (medikamentös nach AO)', massnahme:'Heparin-Injektion nach Anordnung durchführen, Injektionsstellen rotieren, Wirkung beobachten', ziel:'Thrombose verhindert, Injektion korrekt', details:[] },
    { atl:'Sich bewegen', kat:'Mobilität', symptom:'Rollstuhlversorgung / Sitzposition', massnahme:'Sitzposition im Rollstuhl optimieren, Dekubitusrisiko beachten, Lagerungshilfsmittel einsetzen', ziel:'Druckentlastung im Sitzen, Sitzkomfort verbessert', details:[] },
    { atl:'Sich bewegen', kat:'Schmerz', symptom:'Gelenkschmerzen (Arthrose/Arthritis)', massnahme:'Entlastung, Wärme oder Kälte nach Anordnung, Mobilisation schonend, Schmerzmittel nach AO', ziel:'Gelenkschmerzen reduziert, Mobilität erhalten', details:[] },
    { atl:'Kommunizieren', kat:'Soziales & Alltag', symptom:'Selbstgefährdung / fehlende Gefahrenerkennung', massnahme:'Sicherheit der Umgebung prüfen, beobachten, weiterleiten, nicht alleine lassen wenn nötig', ziel:'Sicherheit gewährleistet, Risiken minimiert', details:[] },
    { atl:'Essen & Trinken', kat:'Ernährung & Flüssigkeit', symptom:'Ernährung nach Kau- oder Zahnproblemen anpassen', massnahme:'Weichkost oder pürierte Kost anbieten, Zahnarztbesuch empfehlen, Essfreude erhalten', ziel:'Ausreichende Ernährung trotz Kauproblemen', details:[] },
    { atl:'Ausscheiden', kat:'Ausscheidung', symptom:'Blasentraining bei Inkontinenz', massnahme:'Miktionsprotokoll führen, Toilettenzeiten festlegen, Beckenbodenübungen anleiten', ziel:'Kontinenz verbessert, Lebensqualität gesteigert', details:[] },
    { atl:'Körperpflege', kat:'Behandlungspflege', symptom:'Pflasterverband / kleines Wundpflaster wechseln', massnahme:'Pflaster nach Anordnung wechseln, Wundzustand beurteilen, hygienisch arbeiten', ziel:'Wunde versorgt, Infektion verhindert', details:[] },
    { atl:'Sich bewegen', kat:'Notfall & Risiko', symptom:'Beobachtung nach Sturz ohne Verletzungszeichen', massnahme:'Person engmaschig beobachten, auf verzögerte Symptome achten, Arzt informieren bei Auffälligkeiten', ziel:'Spätkomplikationen rechtzeitig erkannt', details:[] },
    { atl:'Kommunizieren', kat:'Palliativpflege', symptom:'Spirituelle / religiöse Bedürfnisse in Sterbephase', massnahme:'Individuelle Bedürfnisse erfragen und ermöglichen, Seelsorge einbeziehen, Wünsche respektieren', ziel:'Spirituelle Begleitung sichergestellt, Würde gewahrt', details:[] },
    { atl:'Sich bewegen', kat:'Atmung', symptom:'Sauerstoffgerät zu Hause in Betrieb', massnahme:'O2-Gerät nach Anordnung bedienen, Flussrate prüfen, Schlauchsystem kontrollieren, Sicherheit beachten', ziel:'O2-Versorgung sicher und reibungslos', details:[] },
    { atl:'Essen & Trinken', kat:'Behandlungspflege', symptom:'Magensonde vorhanden (nasogastral)', massnahme:'Sondenlage prüfen nach Anordnung, Sondenkost verabreichen, Tubus pflegen', ziel:'Sondenkostgabe sicher, Tubus komplikationslos', details:[] },
    { atl:'Kommunizieren', kat:'Soziales & Alltag', symptom:'Rückzug / depressive Verstimmung', massnahme:'Empathisch ansprechen, Aktivitäten sanft anbieten, weiterleiten an Fachperson bei anhaltender Symptomatik', ziel:'Stimmung aufgehellt, professionelle Unterstützung eingeleitet', details:[] },
    { atl:'Körperpflege', kat:'Prophylaxen', symptom:'Intertrigoprophylaxe Achseln / Leistenbereich', massnahme:'Hautfalten täglich reinigen und abtrocknen, Zinkpaste oder Barrierepflege anwenden', ziel:'Hautentzündung in Falten verhindert', details:[] },
  ];



  /* ── Anamnese: Laden + Mapping ─────────────────────────────────────── */

  function loadAnamnese() {
    /* Erst patientenspezifisch suchen, dann global */
    try {
      const pat = typeof getPatient === 'function' ? getPatient() : null;
      if (pat && pat.id) {
        const raw = localStorage.getItem('nursy_anamnese_v1_' + pat.id);
        if (raw) return JSON.parse(raw);
      }
      const raw = localStorage.getItem('nursy_anamnese_v1');
      if (raw) return JSON.parse(raw);
    } catch (e) {}
    return null;
  }

  function freqLabel(code) {
    const map = {
      '1x-tgl': '1x täglich', '2x-tgl': '2x täglich',
      '3x-tgl': '3x täglich', 'woechentlich': 'Wöchentlich',
      'nach-bedarf': 'Nach Bedarf'
    };
    return map[code] || code || '';
  }

  function anamneseToSuggestions(an) {
    const items = [];

    /* Mobilisation */
    if (an.mobilisation === 'teilweise' || an.mobilisation === 'komplett') {
      items.push({
        atl: 'Bewegung & Mobilität', kat: 'ATL',
        symptom: 'Mobilisation: ' + (an.mobilisation === 'komplett' ? 'komplette Übernahme' : 'teilweise Unterstützung nötig'),
        massnahme: 'Unterstützung bei Transfer und Mobilisation, Hilfsmittel einsetzen',
        ziel: 'Mobilität erhalten, Selbstständigkeit fördern, Kontrakturprophylaxe'
      });
    }

    /* Körperpflege */
    if (an.koerperpflege === 'teilweise' || an.koerperpflege === 'komplett') {
      const orte = Array.isArray(an.koerperpflegeOrt) && an.koerperpflegeOrt.length
        ? ' (' + an.koerperpflegeOrt.join(', ') + ')' : '';
      items.push({
        atl: 'Körperpflege', kat: 'ATL',
        symptom: 'Körperpflege: ' + (an.koerperpflege === 'komplett' ? 'komplette Übernahme' : 'Unterstützung erforderlich'),
        massnahme: 'Waschen, Duschen' + orte + ', Hautpflege durchführen',
        ziel: 'Sauberkeit, Wohlbefinden, Hautintegrität erhalten'
      });
    }

    /* Ankleiden */
    if (an.ankleiden === 'teilweise' || an.ankleiden === 'komplett') {
      items.push({
        atl: 'Körperpflege', kat: 'ATL',
        symptom: 'An-/Auskleiden: Unterstützung erforderlich',
        massnahme: 'An-/Auskleiden begleiten, situationsgerechte Kleidung wählen',
        ziel: 'Würde und Selbstständigkeit erhalten'
      });
    }

    /* Sturzrisiko */
    if (an.sturzrisiko === 'mittel' || an.sturzrisiko === 'hoch') {
      items.push({
        atl: 'Sicherheit', kat: 'Prophylaxen',
        symptom: 'Erhöhtes Sturzrisiko (' + an.sturzrisiko + ')',
        massnahme: 'Sturzprophylaxe: sichere Umgebung, Hilfsmittel prüfen, Bewegungsübungen',
        ziel: 'Sturz verhindern, Sicherheit gewährleisten'
      });
    }

    /* Inkontinenz */
    const inkArr = Array.isArray(an.inkontinenz) ? an.inkontinenz : [];
    const inkPos = inkArr.filter(function(i) { return i !== 'kontinent'; });
    if (inkPos.length) {
      items.push({
        atl: 'Ausscheidung', kat: 'ATL',
        symptom: 'Inkontinenz (' + inkPos.join(', ') + ')',
        massnahme: 'Inkontinenzversorgung' + (an.inkVersorgtMit ? ' mit ' + an.inkVersorgtMit : '') + ', Intimhygiene',
        ziel: 'Würde erhalten, Hautintegrität gewährleisten, Infektionsprophylaxe'
      });
    }

    /* Stuhlausscheidung */
    const stuhlArr = Array.isArray(an.stuhlAusscheidung) ? an.stuhlAusscheidung : [];
    if (stuhlArr.includes('obstipation')) {
      items.push({
        atl: 'Ausscheidung', kat: 'Prophylaxen',
        symptom: 'Obstipation',
        massnahme: 'Obstipationsprophylaxe: ausreichend Flüssigkeit, Bewegung, Ernährung, Laxantien nach AVO',
        ziel: 'Regelmäßige Stuhlentleerung fördern, Komplikationen vermeiden'
      });
    }
    if (stuhlArr.includes('diarrhoe')) {
      items.push({
        atl: 'Ausscheidung', kat: 'ATL',
        symptom: 'Diarrhö',
        massnahme: 'Flüssigkeits- und Elektrolytausgleich, Diät, Hautschutz, Dokumentation',
        ziel: 'Dehydratation verhindern, Hautintegrität erhalten'
      });
    }

    /* Ableitende Systeme */
    const stomaArr = Array.isArray(an.ableitendeSysteme) ? an.ableitendeSysteme : [];
    const stomaPos = stomaArr.filter(function(s) { return s !== 'nicht-vorhanden' && s !== 'sonstiges-ableit'; });
    if (stomaPos.length) {
      items.push({
        atl: 'Ausscheidung', kat: 'ATL',
        symptom: 'Ableitendes System: ' + stomaPos.join(', '),
        massnahme: 'Katheter-/Stomapflege, Beutelwechsel nach Standard, Hygiene, Dokumentation',
        ziel: 'Infektionsprophylaxe, komplikationsfreie Versorgung gewährleisten'
      });
    }

    /* Haut & Wunden */
    const hautArr = Array.isArray(an.haut && an.haut.zustand) ? an.haut.zustand : [];
    const wundOrte = Array.isArray(an.haut && an.haut.wundOrtLabels) ? an.haut.wundOrtLabels : [];
    if (hautArr.includes('wunden') || wundOrte.length) {
      items.push({
        atl: 'Haut & Wunden', kat: 'ATL',
        symptom: 'Wunden/Hautdefekte' + (wundOrte.length ? ' an: ' + wundOrte.join(', ') : ''),
        massnahme: 'Wundversorgung nach AVO, Wunddokumentation, Wundbeurteilung bei jedem Besuch',
        ziel: 'Wundheilung fördern, Infektionsprophylaxe'
      });
    }
    if (hautArr.includes('dekubitus-risiko')) {
      items.push({
        atl: 'Haut & Wunden', kat: 'Prophylaxen',
        symptom: 'Erhöhtes Dekubitusrisiko',
        massnahme: 'Lagerung alle 2h, Druckentlastung, Hilfsmittel (Antidekubitusmatratze), Hautpflege',
        ziel: 'Dekubitusentstehung verhindern'
      });
    }
    if (hautArr.includes('trockene-haut')) {
      items.push({
        atl: 'Körperpflege', kat: 'ATL',
        symptom: 'Trockene Haut',
        massnahme: 'Regelmäßige Hautreinigung und -pflege mit rückfettenden Produkten',
        ziel: 'Hautintegrität erhalten, Juckreiz reduzieren'
      });
    }

    /* Ernährung */
    const ern = an.ernaehrung || {};
    if (ern.schluck && ern.schluck !== 'nein' && ern.schluck !== '') {
      items.push({
        atl: 'Ernährung', kat: 'Prophylaxen',
        symptom: 'Schluckstörung / Aspirationsrisiko (' + ern.schluck + ')',
        massnahme: 'Angepasste Konsistenz, aufrechte Sitzposition beim Essen, Schlucktraining nach AVO',
        ziel: 'Aspirationspneumonie verhindern, ausreichende Nahrungsaufnahme sichern'
      });
    }
    if (ern.appetit && ern.appetit !== 'nein' && ern.appetit !== '') {
      items.push({
        atl: 'Ernährung', kat: 'ATL',
        symptom: 'Appetitlosigkeit (' + ern.appetit + ' ausgeprägt)',
        massnahme: 'Lieblingsmahlzeiten berücksichtigen, kleine Portionen, kalorische Anreicherung, Gewichtskontrolle',
        ziel: 'Ausreichende Kalorienzufuhr sichern, Mangelernährung verhindern'
      });
    }
    if (ern.durstgefuehl && ern.durstgefuehl !== 'nein' && ern.durstgefuehl !== '') {
      items.push({
        atl: 'Ernährung', kat: 'Prophylaxen',
        symptom: 'Vermindertes Durstgefühl',
        massnahme: 'Regelmäßig Trinken anbieten, Flüssigkeitsprotokoll führen, mind. 1,5l/Tag',
        ziel: 'Dehydratation verhindern, ausreichende Flüssigkeitszufuhr gewährleisten'
      });
    }

    /* Vorerkrankungen */
    const vorerArr = Array.isArray(an.vorerkrankungen) ? an.vorerkrankungen : [];
    if (vorerArr.includes('demenz')) {
      items.push({
        atl: 'Kognition & Kommunikation', kat: 'ATL',
        symptom: 'Demenz / kognitive Einschränkung',
        massnahme: 'Orientierungshilfen, Biographiearbeit, ruhige Ansprache, strukturierter Tagesablauf',
        ziel: 'Orientierung fördern, Wohlbefinden sichern, Sicherheit gewährleisten'
      });
    }
    if (vorerArr.includes('diabetes')) {
      items.push({
        atl: 'Medikamente & Behandlung', kat: 'ATL',
        symptom: 'Diabetes mellitus',
        massnahme: 'Blutzuckerkontrolle, Insulingabe nach AVO, diabetische Fußpflege, Ernährungsberatung',
        ziel: 'Blutzucker im Zielbereich, Folgeerkrankungen verhindern'
      });
    }
    if (vorerArr.includes('parkinson')) {
      items.push({
        atl: 'Bewegung & Mobilität', kat: 'ATL',
        symptom: 'Parkinson-Erkrankung',
        massnahme: 'Medikamente nach AVO (pünktlich!), Bewegungsübungen, Schlucktraining, Sturzprophylaxe',
        ziel: 'Motorische Funktion erhalten, Komplikationen verhindern'
      });
    }
    if (vorerArr.includes('schlaganfall')) {
      items.push({
        atl: 'Bewegung & Mobilität', kat: 'ATL',
        symptom: 'Schlaganfall / Hemiplegie',
        massnahme: 'Mobilisation, Lagerung, Kontrakturprophylaxe, Aktivierung nach Bobath, Physiotherapie unterstützen',
        ziel: 'Funktionen erhalten/fördern, Komplikationen verhindern'
      });
    }
    if (vorerArr.includes('herzinsuffizienz')) {
      items.push({
        atl: 'Medikamente & Behandlung', kat: 'ATL',
        symptom: 'Herzinsuffizienz',
        massnahme: 'Flüssigkeitsbilanz, Gewichtskontrolle täglich, Medikamente nach AVO, körperliche Schonung',
        ziel: 'Dekompensation verhindern, Lebensqualität erhalten'
      });
    }
    if (vorerArr.includes('copd')) {
      items.push({
        atl: 'Medikamente & Behandlung', kat: 'ATL',
        symptom: 'COPD / Lungenerkrankung',
        massnahme: 'Inhalatoren nach AVO, Atemübungen, O2-Versorgung prüfen, körperliche Belastung anpassen',
        ziel: 'Atemnot reduzieren, Sauerstoffversorgung sichern'
      });
    }
    if (vorerArr.includes('osteoporose')) {
      items.push({
        atl: 'Bewegung & Mobilität', kat: 'Prophylaxen',
        symptom: 'Osteoporose',
        massnahme: 'Sturzprophylaxe verstärken, Bewegungsübungen (gelenkschonend), Calcium/Vitamin D nach AVO',
        ziel: 'Frakturen verhindern, Knochendichte erhalten'
      });
    }
    if (vorerArr.includes('psychisch')) {
      items.push({
        atl: 'Kognition & Kommunikation', kat: 'ATL',
        symptom: 'Psychische Erkrankung',
        massnahme: 'Einfühlsame Kommunikation, Medikamente nach AVO, Krisenplan beachten, Bezugspflege',
        ziel: 'Psychisches Wohlbefinden fördern, Sicherheit gewährleisten'
      });
    }

    return items;
  }

  const demoAnamnese = demoTemplates.slice(0, 6); // Fallback Demo-Vorschläge

  const frequencyOptions = ['Bitte wählen', '1x täglich', '2x täglich', '3x täglich', 'Wöchentlich', 'Bei Bedarf'];
  const evalOptions = ['Bitte wählen', 'täglich', 'alle 2 Tage', 'wöchentlich', 'bei Änderung'];

  function getActivePatientLabel() {
    if (typeof getPatient === 'function') {
      const p = getPatient();
      return p ? (p.name + ' (geb. ' + p.birth + ')') : 'Name, Geb. Datum';
    }
    return 'Name, Geb. Datum';
  }

  function buildSelect(id, label, options, value = '') {
    const optHtml = options
      .map((t) => `<option value="${escapeHtml(t)}" ${t === value ? 'selected' : ''}>${escapeHtml(t)}</option>`)
      .join('');

    return `
      <label class="pp-field" for="${id}">
        <span class="pp-label">${escapeHtml(label)}</span>
        <select id="${id}" class="pp-control">
          ${optHtml}
        </select>
      </label>
    `;
  }

  function escapeHtml(str) {
    return String(str)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }

  function modalShell({ title, bodyHtml, footerHtml, wide = true }) {
    return `
      <div class="pp-modal" role="dialog" aria-modal="true" aria-label="${escapeHtml(title)}">
        <div class="pp-modal__panel ${wide ? 'pp-modal__panel--wide' : ''}">
          <div class="pp-modal__header">
            <h2 class="pp-modal__title">${escapeHtml(title)}</h2>
            <button type="button" class="pp-modal__close" data-close aria-label="Schließen">×</button>
          </div>
          <div class="pp-modal__body">${bodyHtml}</div>
          <div class="pp-modal__footer">${footerHtml}</div>
        </div>
      </div>
    `;
  }

  function tableHtml(rows, { checkbox = true } = {}) {
    const head = `
      <div class="pp-table__head">
        ${checkbox ? '<div class="pp-table__cell pp-table__cell--check"></div>' : ''}
        <div class="pp-table__cell"><strong>Symptome</strong></div>
        <div class="pp-table__cell"><strong>Maßnahme</strong></div>
        <div class="pp-table__cell"><strong>Ziel</strong></div>
      </div>
    `;

    const body = rows
      .map((r, i) => `
        <label class="pp-table__row" data-symptom="${escapeHtml(r.symptom)}">
          ${checkbox ? `<div class="pp-table__cell pp-table__cell--check"><input type="checkbox" class="pp-rowcheck" data-rowcheck="${i}"></div>` : ''}
          <div class="pp-table__cell">${escapeHtml(r.symptom)}</div>
          <div class="pp-table__cell">${escapeHtml(r.massnahme)}</div>
          <div class="pp-table__cell">${escapeHtml(r.ziel)}</div>
        </label>
      `)
      .join('');

    return `
      <div class="pp-table" role="table">
        ${head}
        <div class="pp-table__body" role="rowgroup">${body}</div>
      </div>
    `;
  }

  function renderAnamnese() {
    const patient = getActivePatientLabel();
    const anamnese = loadAnamnese();
    const suggestions = anamnese ? anamneseToSuggestions(anamnese) : [];
    const rows = suggestions.length ? suggestions : demoAnamnese;
    const isReal = suggestions.length > 0;

    const freqPreset = (anamnese && anamnese.frequenz) ? freqLabel(anamnese.frequenz) : '';

    const savedAt = anamnese && anamnese.savedAt
      ? new Date(anamnese.savedAt).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit', year: 'numeric' })
      : '';

    const badgeHtml = isReal
      ? `<span style="margin-left:8px;font-size:11px;background:#dcfce7;color:#166534;border-radius:999px;padding:2px 10px;font-weight:700;">Anamnesebogen vom ${escapeHtml(savedAt)}</span>`
      : `<span style="margin-left:8px;font-size:11px;background:#fef9c3;color:#854d0e;border-radius:999px;padding:2px 10px;font-weight:700;">Demo-Vorschläge</span>`;

    const top = `
      <div class="pp-modal__top">
        <div class="pp-patientline">
          <span class="pp-muted">akt. Pat.:</span>
          <strong>${escapeHtml(patient)}</strong>
          ${badgeHtml}
        </div>
        <div class="pp-topgrid">
          ${buildSelect('ppFreq', 'Frequenz', frequencyOptions, freqPreset)}
          ${buildSelect('ppEval', 'Evaluierung', evalOptions)}
        </div>
      </div>
    `;

    const pflegestufeHint = (anamnese && anamnese.pflegestufe)
      ? `<p class="pp-hint" style="margin-bottom:4px">Pflegestufe aus Anamnese: <strong>${escapeHtml(anamnese.pflegestufe)}</strong></p>`
      : '';

    const hint = isReal
      ? `${pflegestufeHint}<p class="pp-hint">${escapeHtml(String(rows.length))} Vorschlag${rows.length !== 1 ? 'äge' : ''} aus dem Anamnesebogen – Maßnahmen ankreuzen und „Übernehmen“ drücken.</p>`
      : `<p class="pp-hint" style="color:#b45309;">Kein Anamnesebogen hinterlegt – Demo-Vorschläge werden angezeigt. Bitte zuerst die <a href="register-client-need.html" style="color:#3f6fe8;font-weight:600;">Pflegeanamnese</a> ausfüllen.</p>`;

    const body = `
      ${top}
      <div class="pp-section">
        ${tableHtml(rows, { checkbox: true })}
        ${hint}
      </div>
    `;

    const footer = `
      <button type="button" class="pp-btn pp-btn--ghost" data-close>Abbrechen</button>
      <button type="button" class="pp-btn" data-selectall>Alles auswählen</button>
      <button type="button" class="pp-btn pp-btn--primary" data-accept>Übernehmen</button>
    `;

    return modalShell({ title: 'Aus Anamnese übernehmen', bodyHtml: body, footerHtml: footer, wide: true });
  }

  function renderTemplates() {
    const patient = getActivePatientLabel();

    const right = `
      <div class="pp-card">
        <h3 class="pp-card__title">Einstellungen</h3>
        <div class="pp-patientline pp-patientline--small">
          <span class="pp-muted">akt. Pat.:</span>
          <strong>${escapeHtml(patient)}</strong>
        </div>
        <div class="pp-stack">
          ${buildSelect('ppFreq2', 'Frequenz', frequencyOptions)}
          ${buildSelect('ppEval2', 'Evaluierung', evalOptions)}
          <label class="pp-field" for="ppUhrzeit2">
            <span class="pp-label">Uhrzeit (optional)</span>
            <input id="ppUhrzeit2" class="pp-control" type="time" placeholder="08:00">
          </label>
          ${buildSelect('ppZeitpunkt2', 'Tageszeit', ['Bitte wählen', 'Früh', 'Mittag', 'Abend'])}
          ${buildSelect('ppAtl', 'ATL auswählen', ['Bitte wählen', 'Sich bewegen', 'Essen & Trinken', 'Ausscheiden', 'Körperpflege', 'Kommunizieren'])}
          ${buildSelect('ppKat', 'Kategorie', ['Bitte wählen', 'Mobilität', 'Körperpflege', 'Ernährung & Flüssigkeit', 'Ausscheidung', 'Atmung', 'Schmerz', 'Wunde & Haut', 'Schlaf & Ruhe', 'Psyche & Kommunikation', 'Kognition & Orientierung', 'Sicherheit & Sturz', 'Medikation', 'Prophylaxen'])}
          <label class="pp-field">
            <span class="pp-label">Suche</span>
            <input id="ppSearch" class="pp-control" type="text" placeholder="z.B. Sturz, Schmerz, Dekubitus …">
          </label>
          <div class="pp-card" style="padding:12px;border-radius:14px;background:rgba(63,111,232,.04);border:1px solid rgba(63,111,232,.16);">
            <div class="pp-label" style="margin-bottom:6px;">Details</div>
            <div id="ppTplDetail" class="pp-hint" style="margin:0;">Tippe auf eine Vorlage (Zeile), um Details zu sehen.</div>
          </div>
        </div>
      </div>
    `;

    const left = `
      <div class="pp-card">
        <h3 class="pp-card__title">Vorlagenliste</h3>
        <div id="ppTemplateTable">
          ${tableHtml(demoTemplates, { checkbox: true })}
        </div>
        <p class="pp-hint">Filter & Suche wirken sofort. Danach auswählen und übernehmen.</p>
      </div>
    `;

    const body = `
      <div class="pp-grid2">
        ${left}
        ${right}
      </div>
    `;

    const footer = `
      <button type="button" class="pp-btn pp-btn--ghost" data-close>Abbrechen</button>
      <button type="button" class="pp-btn" data-selectall>Alles auswählen</button>
      <button type="button" class="pp-btn pp-btn--primary" data-accept>Übernehmen</button>
    `;

    return modalShell({ title: 'Vorlagen', bodyHtml: body, footerHtml: footer, wide: true });
  }

  function renderFree() {
    const patient = getActivePatientLabel();

    const left = `
      <div class="pp-card">
        <h3 class="pp-card__title">Freie Planung</h3>
        <div class="pp-stack">
          <label class="pp-field">
            <span class="pp-label">Symptom</span>
            <textarea class="pp-control pp-control--ta" rows="3" placeholder="Symptom / Pflegeproblem …"></textarea>
          </label>
          <label class="pp-field">
            <span class="pp-label">Maßnahme</span>
            <textarea class="pp-control pp-control--ta" rows="3" placeholder="Pflegemaßnahmen …"></textarea>
          </label>
          <label class="pp-field">
            <span class="pp-label">Ziel</span>
            <textarea class="pp-control pp-control--ta" rows="3" placeholder="Pflegeziel …"></textarea>
          </label>
        </div>
      </div>
    `;

    const right = `
      <div class="pp-card">
        <h3 class="pp-card__title">Einstellungen</h3>
        <div class="pp-patientline pp-patientline--small">
          <span class="pp-muted">akt. Pat.:</span>
          <strong>${escapeHtml(patient)}</strong>
        </div>
        <div class="pp-topgrid pp-topgrid--tight">
          ${buildSelect('ppFreq3', 'Frequenz', frequencyOptions)}
          ${buildSelect('ppEval3', 'Evaluierung', evalOptions)}
        </div>
        <div class="pp-topgrid pp-topgrid--tight" style="margin-top:8px;">
          <label class="pp-field" for="ppUhrzeit3">
            <span class="pp-label">Uhrzeit (optional)</span>
            <input id="ppUhrzeit3" class="pp-control" type="time" placeholder="08:00">
          </label>
          ${buildSelect('ppZeitpunkt3', 'Tageszeit', ['Bitte wählen', 'Früh', 'Mittag', 'Abend'])}
        </div>
        <p class="pp-hint">Demo: keine Speicherung/Logik.</p>
      </div>
    `;

    const body = `
      <div class="pp-grid2 pp-grid2--free">
        ${left}
        ${right}
      </div>
    `;

    const footer = `
      <button type="button" class="pp-btn pp-btn--ghost" data-close>Abbrechen</button>
      <button type="button" class="pp-btn pp-btn--primary" data-accept>Übernehmen</button>
    `;

    return modalShell({ title: 'Frei definiert', bodyHtml: body, footerHtml: footer, wide: false });
  }

  function attachModalHandlers(modalEl) {
    // Close
    qsa('[data-close]', modalEl).forEach((btn) => {
      btn.addEventListener('click', () => closeModal());
    });

    // Click outside panel closes
    modalEl.addEventListener('click', (e) => {
      const panel = qs('.pp-modal__panel', modalEl);
      if (panel && !panel.contains(e.target)) closeModal();
    });

    // Escape closes
    const onKey = (e) => {
      if (e.key === 'Escape') closeModal();
    };
    window.addEventListener('keydown', onKey, { once: true });

    // Select all
    const selectAllBtn = qs('[data-selectall]', modalEl);
    if (selectAllBtn) {
      selectAllBtn.addEventListener('click', () => {
        qsa('.pp-rowcheck', modalEl).forEach((c) => (c.checked = true));
      });
    }

    // Accept
    const acceptBtn = qs('[data-accept]', modalEl);
    if (acceptBtn) {
      acceptBtn.addEventListener('click', () => {

        const planBody = document.getElementById('planBody');
        if (!planBody) {
          closeModal();
          return;
        }

        // Frequenz + Evaluierung + Uhrzeit + Zeitpunkt aus dem aktiven Modal lesen (je nach Dialog-ID)
        const freqEl      = qs('#ppFreq, #ppFreq2, #ppFreq3', modalEl);
        const evalEl      = qs('#ppEval, #ppEval2, #ppEval3', modalEl);
        const uhrzeitEl   = qs('#ppUhrzeit, #ppUhrzeit2, #ppUhrzeit3', modalEl);
        const zeitpunktEl = qs('#ppZeitpunkt, #ppZeitpunkt2, #ppZeitpunkt3', modalEl);

        const freqValRaw      = freqEl      ? String(freqEl.value      || '').trim() : '';
        const evalValRaw      = evalEl      ? String(evalEl.value      || '').trim() : '';
        const uhrzeitValRaw   = uhrzeitEl   ? String(uhrzeitEl.value   || '').trim() : '';
        const zeitpunktValRaw = zeitpunktEl ? String(zeitpunktEl.value || '').trim() : '';

        const freqVal      = (freqValRaw && freqValRaw !== 'Bitte wählen') ? freqValRaw : '';
        const evalVal      = (evalValRaw && evalValRaw !== 'Bitte wählen') ? evalValRaw : '';
        const uhrzeitVal   = uhrzeitValRaw || '';
        const zeitpunktVal = (zeitpunktValRaw && zeitpunktValRaw !== 'Bitte wählen') ? zeitpunktValRaw.toLowerCase() : '';

        function addDays(d, n){
          const x = new Date(d.getTime());
          x.setDate(x.getDate() + n);
          return x;
        }
        const today = new Date();
        const plannedStr = today.toLocaleDateString('de-DE');

        let evalStr = '—';
        if (evalVal === 'täglich') evalStr = addDays(today, 1).toLocaleDateString('de-DE');
        else if (evalVal === 'alle 2 Tage') evalStr = addDays(today, 2).toLocaleDateString('de-DE');
        else if (evalVal === 'wöchentlich') evalStr = addDays(today, 7).toLocaleDateString('de-DE');
        else if (evalVal === 'bei Änderung') evalStr = 'bei Änderung';

        const checked = qsa('.pp-rowcheck:checked', modalEl);

        if (checked.length > 0) {
          checked.forEach(cb => {
            const row = cb.closest('.pp-table__row');
            if (!row) return;

            const cells = qsa('.pp-table__cell', row);
            if (cells.length < 4) return;

            const diagnose = cells[1].textContent.trim();
            const massnahmeBase = cells[2].textContent.trim();
            const ziel = cells[3].textContent.trim();

            const massnahme = freqVal ? `${massnahmeBase} (${freqVal})` : massnahmeBase;

            const tr = document.createElement('tr');
            if (uhrzeitVal)   tr.dataset.uhrzeit   = uhrzeitVal;
            if (zeitpunktVal) tr.dataset.zeitpunkt = zeitpunktVal;
            tr.innerHTML = `
              <td class="pp-date" data-label="Geplant am">${plannedStr}</td>
              <td data-label="Diagnose">${diagnose}</td>
              <td data-label="Maßnahme">${massnahme}</td>
              <td data-label="Ziel">${ziel}</td>
              <td class="pp-date pp-date--right" data-label="Evaluation am">${evalStr}</td>
            `;
            planBody.appendChild(tr);
          });
        } else {
          const textareas = qsa('textarea', modalEl);
          if (textareas.length >= 3) {
            const diagnose = textareas[0].value.trim();
            const massnahmeBase = textareas[1].value.trim();
            const ziel = textareas[2].value.trim();

            const massnahme = freqVal ? `${massnahmeBase} (${freqVal})` : massnahmeBase;

            if (diagnose || massnahmeBase || ziel) {
              const tr = document.createElement('tr');
              if (uhrzeitVal)   tr.dataset.uhrzeit   = uhrzeitVal;
              if (zeitpunktVal) tr.dataset.zeitpunkt = zeitpunktVal;
              tr.innerHTML = `
                <td class="pp-date" data-label="Geplant am">${plannedStr}</td>
                <td data-label="Diagnose">${diagnose}</td>
                <td data-label="Maßnahme">${massnahme}</td>
                <td data-label="Ziel">${ziel}</td>
                <td class="pp-date pp-date--right" data-label="Evaluation am">${evalStr}</td>
              `;
              planBody.appendChild(tr);
            }
          }
        }

        acceptBtn.blur();
        closeModal();
      });
    }
    // Templates: Filter-Logik (ATL + Kategorie + Suche) + Detail-Preview
    const tplWrap = qs('#ppTemplateTable', modalEl);
    const atlSel = qs('#ppAtl', modalEl);
    const katSel = qs('#ppKat', modalEl);
    const searchInp = qs('#ppSearch', modalEl);
    const detailBox = qs('#ppTplDetail', modalEl);

    if (tplWrap && (atlSel || katSel || searchInp)) {
      let lastFiltered = demoTemplates.slice();

      const norm = (s) => String(s || '').toLowerCase().trim();

      const applyFilters = () => {
        const atl = atlSel ? String(atlSel.value || '').trim() : '';
        const kat = katSel ? String(katSel.value || '').trim() : '';
        const q = searchInp ? norm(searchInp.value) : '';

        const atlOk = (atl && atl !== 'Bitte wählen') ? atl : '';
        const katOk = (kat && kat !== 'Bitte wählen') ? kat : '';

        lastFiltered = demoTemplates.filter((t) => {
          const okAtl = !atlOk || t.atl === atlOk;
          const okKat = !katOk || t.kat === katOk;
          const okQ = !q || (norm(t.symptom).includes(q) || norm(t.massnahme).includes(q) || norm(t.ziel).includes(q));
          return okAtl && okKat && okQ;
        });

        tplWrap.innerHTML = tableHtml(lastFiltered, { checkbox: true }) +
          (lastFiltered.length ? '' : '<p class="pp-hint">Keine Treffer – Filter/Suche anpassen.</p>');

        // reset details on rerender
        if (detailBox) detailBox.innerHTML = 'Tippe auf eine Vorlage (Zeile), um Details zu sehen.';
      };

      if (atlSel) atlSel.addEventListener('change', applyFilters);
      if (katSel) katSel.addEventListener('change', applyFilters);
      if (searchInp) searchInp.addEventListener('input', applyFilters);

      tplWrap.addEventListener('click', (e) => {
        const row = e.target && e.target.closest ? e.target.closest('.pp-table__row') : null;
        if (!row || !detailBox) return;

        const sym = row.getAttribute('data-symptom') || '';
        const t = lastFiltered.find(x => x.symptom === sym) || demoTemplates.find(x => x.symptom === sym);
        if (!t) return;

        const bullets = (t.details && t.details.length)
          ? ('<ul style="margin:8px 0 0; padding-left: 18px;">' + t.details.map(d => '<li>' + escapeHtml(d) + '</li>').join('') + '</ul>')
          : '';

        detailBox.innerHTML = ''
          + '<div><strong>' + escapeHtml(t.symptom) + '</strong></div>'
          + '<div class="pp-hint" style="margin:6px 0 0;"><b>Maßnahme:</b> ' + escapeHtml(t.massnahme) + '</div>'
          + '<div class="pp-hint" style="margin:4px 0 0;"><b>Ziel:</b> ' + escapeHtml(t.ziel) + '</div>'
          + '<div class="pp-hint" style="margin:4px 0 0;"><b>ATL/Kategorie:</b> ' + escapeHtml(t.atl) + ' · ' + escapeHtml(t.kat) + '</div>'
          + bullets;
      });

      applyFilters();
    }

  }

  function openModal(kind) {
    const root = qs('#modalRoot');
    if (!root) return;

    let html = '';
    if (kind === 'anam') html = renderAnamnese();
    else if (kind === 'templates') html = renderTemplates();
    else if (kind === 'free') html = renderFree();
    else html = modalShell({ title: 'Hinweis', bodyHtml: '<p>Unbekannter Dialog.</p>', footerHtml: '<button class="pp-btn pp-btn--primary" data-close>OK</button>', wide: false });

    root.innerHTML = html;

    const modalEl = qs('.pp-modal', root);
    if (!modalEl) return;

    // lock scroll
    document.documentElement.classList.add('pp-modal-open');

    // focus close button
    const closeBtn = qs('.pp-modal__close', modalEl);
    if (closeBtn) closeBtn.focus();

    attachModalHandlers(modalEl);
  }

  function closeModal() {
    const root = qs('#modalRoot');
    if (!root) return;
    root.innerHTML = '';
    document.documentElement.classList.remove('pp-modal-open');
  }

  function wireOpenButtons() {
    qsa('[data-open]').forEach((btn) => {
      btn.addEventListener('click', (e) => {
        e.preventDefault();
        const kind = btn.getAttribute('data-open');
        openModal(kind);
      });
    });
  }

  function init() {
    wireOpenButtons();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
