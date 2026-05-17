let __currentEdit = null;
function firstNonCancelled(visits){ return (visits||[]).find(v=>!v.cancelled) || null; }
document.addEventListener('DOMContentLoaded',()=>{});

// Registrierung / Login
(function(){
  function showError(form, msg){
    const box = form.querySelector('.form-error');
    if (box){
      box.textContent = msg;
      box.style.display = 'block';
    } else {
      alert(msg);
    }
  }

  // Multi-Schritt-Registrierung: Rolle speichern für Folgeschritte.
  // Die eigentlichen API-Aufrufe übernehmen die inline-Scripts in
  // register-care.html (POST /api/register/care) und
  // register-client.html (POST /api/register/patient).
  document.querySelectorAll('form[data-demo-register]').forEach(form => {
    form.addEventListener('submit', (e) => {
      const role = form.getAttribute('data-demo-register');
      const pw  = form.querySelector('input[type="password"][id$="pw"]');
      const pw2 = form.querySelector('input[type="password"][id$="pw2"]');
      if (pw && pw2 && pw.value !== pw2.value){
        e.preventDefault();
        showError(form, 'Die Passwörter stimmen nicht überein.');
        return;
      }
      try{ localStorage.setItem('nursy_register_role', role); }catch(err){}
    });
  });

  // Multi-Schritt-Navigation (Profil → Verfügbarkeit → Dashboard)
  document.querySelectorAll('form[data-demo-next]').forEach(form => {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const next = form.getAttribute('data-demo-next');
      if (next === 'client'){
        window.location.href = 'dashboard-client.html';
        return;
      }
      if (next === 'care'){
        try{
          const existing = JSON.parse(localStorage.getItem('nursy_profile_care_v1') || '{}');
          const fields = Object.assign({}, existing.fields || {}, {
            bio:      document.getElementById('p-bio')?.value || '',
            qualMain: document.getElementById('p-qual-main')?.value || '',
            qualOther:document.getElementById('p-qual-other')?.value || ''
          });
          const extras = [];
          document.querySelectorAll('#extrasList .extras__row').forEach(row => {
            const sel = row.querySelector('.extras__select');
            const other = row.querySelector('.extras__other');
            const name = sel ? sel.value : '';
            const otherVal = other ? other.value : '';
            if (name || otherVal) extras.push({name, other: otherVal});
          });
          localStorage.setItem('nursy_profile_care_v1', JSON.stringify(Object.assign({}, existing, {fields, extras})));
        }catch(err){}
        window.location.href = 'register-care-availability.html';
        return;
      }
      if (next === 'care-finish'){
        const timeInputs = document.querySelectorAll('.avail-time');
        if (timeInputs.length){
          const data = {};
          timeInputs.forEach(inp => {
            const d = inp.dataset.day;
            const s = inp.dataset.slot;
            data[d] = data[d] || {};
            data[d][s] = inp.value || '';
          });
          try{ localStorage.setItem('nursy_availability_v1', JSON.stringify(data)); }catch(err){}
          try{ localStorage.setItem('nursy_availability_compact_v1', JSON.stringify(data)); }catch(err){}
        }
        window.location.href = 'dashboard-care.html';
      }
    });
  });

  // Wundkarte (Lokalisation)
  const wzMapWrap = document.getElementById('wzMapWrap');
  if (wzMapWrap){
    const zones   = wzMapWrap.querySelectorAll('.wz-zone');
    const summary = document.getElementById('wzSummary');
    const selected = {};
    zones.forEach(zone => {
      zone.addEventListener('click', () => {
        const id    = zone.dataset.id;
        const label = zone.dataset.label;
        if (selected[id]){ delete selected[id]; zone.classList.remove('sel'); }
        else { selected[id] = label; zone.classList.add('sel'); }
        if (summary){
          const vals = Object.values(selected);
          summary.textContent = vals.length ? vals.join(' · ') : 'Keine Lokalisation markiert';
        }
      });
    });
    const profileForm = document.getElementById('profileForm');
    if (profileForm){
      profileForm.addEventListener('submit', () => {
        try{
          const existing = JSON.parse(localStorage.getItem('nursy_profile_care_v1') || '{}');
          const woundDoc = {
            localisations:   Object.values(selected),
            localisationIds: Object.keys(selected),
            art:             document.getElementById('wzArt')?.value || '',
            dekubitusGrad:   document.getElementById('wzDekGrad')?.value || '',
            sonstiges:       document.getElementById('wzSonstiges')?.value || '',
            seitWann:        document.getElementById('wzSeitWann')?.value || '',
            beschreibung:    document.getElementById('wzBeschreibung')?.value || '',
            versorgtMit:     document.getElementById('wzVersorgtMit')?.value || '',
            naechsteEval:    document.getElementById('wzNaechsteEval')?.value || '',
            dokumentiertAm:  document.getElementById('wzDokDatum')?.value || ''
          };
          localStorage.setItem('nursy_profile_care_v1', JSON.stringify(Object.assign({}, existing, {woundDoc})));
        }catch(err){}
      }, true);
    }
  }

  // E-Mail-Bestätigung: Weiterleitung je nach Rolle
  const cont = document.getElementById('verifyContinue');
  if (cont){
    cont.addEventListener('click', (e) => {
      e.preventDefault();
      let role = null;
      try{ role = localStorage.getItem('nursy_register_role'); }catch(err){}
      window.location.href = (role === 'care') ? 'register-care-profile.html' : 'register-client-need.html';
    });
  }

  // ── Login ──────────────────────────────────────────────────────────────────
  // Alle Login-Formulare mit data-login-role="care|client" senden an /api/login
  // mit der Rolle im Request-Body. Korrekte Fehlermeldungen vom Server werden
  // direkt angezeigt.
  document.querySelectorAll('form[data-login-role]').forEach(form => {
    const emailEl  = form.querySelector('#loginEmail');
    const pwEl     = form.querySelector('#loginPassword');
    const submitEl = form.querySelector('[type="submit"]');
    const role     = form.getAttribute('data-login-role');

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      if (!emailEl || !pwEl) return;

      const email = emailEl.value.trim();
      const pw    = pwEl.value;

      if (!email || !pw){
        showError(form, 'Bitte E-Mail-Adresse und Passwort eingeben.');
        return;
      }

      if (submitEl) submitEl.disabled = true;

      try {
        const resp = await fetch('http://178.105.53.33:5000/api/login', {
          method:      'POST',
          headers:     { 'Content-Type': 'application/json' },
          credentials: 'include',
          body:        JSON.stringify({ email, password: pw, role })
        });
        const data = await resp.json();

        if (!resp.ok || !data.ok){
          showError(form, data.error || 'Anmeldung fehlgeschlagen.');
          if (submitEl) submitEl.disabled = false;
          return;
        }

        try { localStorage.setItem('nursy_current_user', JSON.stringify(data.user)); } catch(err){}

        const returnUrl = new URLSearchParams(window.location.search).get('return');
        window.location.href = returnUrl ||
          (role === 'care' ? 'dashboard-care.html' : 'dashboard-client.html');

      } catch(err){
        showError(form, 'Server nicht erreichbar. Bitte versuche es erneut.');
        if (submitEl) submitEl.disabled = false;
      }
    });
  });

  // Registrierungs-Link nach E-Mail-Bestätigung aktualisieren
  try{
    const role = localStorage.getItem('nursy_register_role');
    if (role){
      document.querySelectorAll('a[data-verify-next]').forEach(a => {
        a.href = (a.textContent.includes('Pflegekraft') || role === 'care')
          ? 'register-care-profile.html'
          : 'register-client-need.html';
      });
    }
  }catch(err){}
})();


// QUALI UI – Pflegekraft Profil (Dropdowns + dynamische Zusatzausbildungen)
document.addEventListener('DOMContentLoaded', () => {
  const main = document.getElementById('p-qual-main');
  const otherWrap = document.getElementById('qualOtherWrap');
  if (main && otherWrap){
    const toggleOther = () => {
      const show = main.value === 'Sonstiges';
      otherWrap.style.display = show ? '' : 'none';
    };
    main.addEventListener('change', toggleOther);
    toggleOther();
  }

  const list = document.getElementById('extrasList');
  const addBtn = document.getElementById('addExtra');
  if (list && addBtn){
    const wireRow = (row) => {
      const sel = row.querySelector('.extras__select');
      const other = row.querySelector('.extras__other');
      const remove = row.querySelector('.extras__remove');

      const toggleOther = () => {
        if (!sel || !other) return;
        const show = sel.value === 'Sonstiges';
        other.style.display = show ? '' : 'none';
      };
      if (sel) sel.addEventListener('change', toggleOther);
      toggleOther();

      if (remove){
        remove.addEventListener('click', () => {
          const rows = list.querySelectorAll('.extras__row');
          if (rows.length <= 1){
            // keep at least one row
            if (sel) sel.value = '';
            if (other){ other.value = ''; other.style.display='none'; }
            return;
          }
          row.remove();
        });
      }
    };

    list.querySelectorAll('.extras__row').forEach(wireRow);
    addBtn.addEventListener('click', () => {
      const tpl = document.querySelector('#extrasTpl');
      const node = tpl.content.firstElementChild.cloneNode(true);
      list.appendChild(node);
      wireRow(node);
    });
  }
});

/* ── Hamburger-Menü für mobile Navigation ─────────────────────────────── */
(function(){
  document.addEventListener('DOMContentLoaded', function(){
    var nav = document.querySelector('.topbar .nav');
    if(!nav) return;

    var btn = document.createElement('button');
    btn.className = 'nav-toggle';
    btn.setAttribute('type','button');
    btn.setAttribute('aria-label','Navigation öffnen');
    btn.setAttribute('aria-expanded','false');
    btn.innerHTML = '&#9776;';
    nav.parentNode.insertBefore(btn, nav);

    btn.addEventListener('click', function(){
      var open = nav.classList.toggle('nav--open');
      btn.innerHTML = open ? '&#10005;' : '&#9776;';
      btn.setAttribute('aria-label', open ? 'Navigation schließen' : 'Navigation öffnen');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
    });

    nav.addEventListener('click', function(e){
      if(e.target.tagName === 'A'){
        nav.classList.remove('nav--open');
        btn.innerHTML = '&#9776;';
        btn.setAttribute('aria-expanded','false');
      }
    });

    document.addEventListener('click', function(e){
      if(!btn.contains(e.target) && !nav.contains(e.target)){
        nav.classList.remove('nav--open');
        btn.innerHTML = '&#9776;';
        btn.setAttribute('aria-expanded','false');
      }
    });
  });
}());

/* ── Care-User-Isolation ─────────────────────────────────────────────────────
   Jeder Pfleger bekommt einen eigenen localStorage-Schlüssel für seine
   Patienten. Die User-ID wird nach dem Profil-Fetch gesetzt und in
   sessionStorage gecacht (wird beim Tab-Schließen automatisch gelöscht).

   Aufruf nach Profil-Fetch:  setCareUid(d.profil.id)
   Schlüssel lesen:           getCarePatKey()
   ──────────────────────────────────────────────────────────────────────── */
(function(){
  var _uid = sessionStorage.getItem('_nursy_care_uid') || '';

  window.setCareUid = function(uid){
    var newUid = uid ? String(uid) : '';
    if(newUid && newUid !== _uid){
      /* Alten globalen Schlüssel bereinigen damit kein anderer Pfleger die Daten sieht */
      try{ localStorage.removeItem('nursy_accepted_patients_v1'); }catch(e){}
    }
    _uid = newUid;
    if(_uid) sessionStorage.setItem('_nursy_care_uid', _uid);
    else sessionStorage.removeItem('_nursy_care_uid');
  };

  window.getCarePatKey = function(){
    var uid = _uid || sessionStorage.getItem('_nursy_care_uid') || '';
    return uid ? ('nursy_accepted_patients_v1_' + uid) : 'nursy_accepted_patients_v1';
  };
}());
