/* ── patient-selector.js ──────────────────────────────────
   Einheitliche Patientenanzeige + Auswahl für alle Nursy-Unterseiten.
   Liest live aus nursy_accepted_patients_v1 (Demo-Patienten entfernt).

   Verwendung:
     initPatientSelector({
       container:  'patBlock',      // id des <div> für den Patient-Chip
       openBtnId:  'openPatModal',  // id des Öffnen-Buttons
       nameEl:     'hiddenName',    // optional
       birthEl:    'hiddenBirth',   // optional
       onChange:   fn(id, patient) // Callback bei Patientenwechsel
     });

   Globale Funktionen:
     getPatient()   → aktuelles Patient-Objekt { id, name, birth, address, … }
     getCurrentPatIdx() → Rückwärtskompatibilität (Index in der internen Liste)
   ────────────────────────────────────────────────────── */

var _allPatients = [];
var _selectedId  = localStorage.getItem('nursy_df_current_pat_id') || '';
var _onChangeCb  = null;
var _nameElId    = null;
var _birthElId   = null;
var _containerId = null;

/* ── Patienten aus localStorage laden und normalisieren ── */
function _loadPatients() {
  var today = (function(){
    var d = new Date();
    return d.getFullYear() + '-' +
      String(d.getMonth()+1).padStart(2,'0') + '-' +
      String(d.getDate()).padStart(2,'0');
  })();

  var seen = {};
  var result = [];

  function _safe(key) {
    try { return JSON.parse(localStorage.getItem(key) || '[]'); } catch(e) { return []; }
  }

  function _birthFromDate(iso) {
    if (!iso) return '';
    var p = iso.split('-');
    return p[2] + '.' + p[1] + '.' + p[0];
  }

  function _ageToApproxBirth(age) {
    if (!age) return '';
    var y = new Date().getFullYear() - age;
    return 'ca. ' + y;
  }

  function _normalize(p, isAccepted) {
    var id   = p.id || ('gen-' + p.name);
    var name = p.name || '?';
    var birth = p.birthdate
      ? _birthFromDate(p.birthdate)
      : (p.age ? _ageToApproxBirth(p.age) : '');
    var address = p.address || '';
    var phone   = p.phone   || '';
    var email   = p.loginEmail || p.email || '';
    var pflegestufe = p.pflegestufe || '';
    var hauptgrund  = p.hauptgrund  || '';
    var source = isAccepted ? 'accepted' : 'demo';

    /* Heutiger Einsatz? */
    var visitToday = false;
    if (isAccepted) {
      visitToday = (p.visitDate === today);
    } else {
      visitToday = (p.visits || []).some(function(v){ return v.date === today && !v.cancelled; });
    }

    var gender = p.gender || '';

    return { id:id, name:name, birth:birth, address:address, phone:phone,
             email:email, pflegestufe:pflegestufe, hauptgrund:hauptgrund,
             visitToday:visitToday, source:source, gender:gender, _raw:p };
  }

  /* Demo-Patienten (inaktive/beendete ausschließen) */
  _safe('nursy_patients_demo_v3').forEach(function(p){
    if (p.active === false) return;
    if (!seen[p.id || p.name]) {
      seen[p.id || p.name] = true;
      result.push(_normalize(p, false));
    }
  });

  /* Manuell aufgenommene Patienten – user-spezifischer Schlüssel */
  var _psKey = window.getCarePatKey ? window.getCarePatKey() : 'nursy_accepted_patients_v1';
  _safe(_psKey).forEach(function(p){
    if (p.active === false) return;
    if (!seen[p.id || p.name]) {
      seen[p.id || p.name] = true;
      result.push(_normalize(p, true));
    }
  });

  /* Heute zuerst, dann alphabetisch */
  result.sort(function(a,b){
    if (a.visitToday && !b.visitToday) return -1;
    if (!a.visitToday && b.visitToday) return 1;
    return a.name.localeCompare(b.name);
  });

  _allPatients = result;

  /* Selektion validieren: falls gespeicherte ID nicht mehr existiert → erste nehmen */
  if (_allPatients.length && !_allPatients.find(function(p){ return p.id === _selectedId; })) {
    _selectedId = _allPatients[0].id;
  }
}

/* ── Initialen aus Name ── */
function _initials(name) {
  var parts = (name || '').split(' ');
  return (parts[0] ? parts[0].charAt(0) : '') +
         (parts[1] ? parts[1].charAt(0) : '');
}

function _currentPat() {
  return _allPatients.find(function(p){ return p.id === _selectedId; }) || _allPatients[0] || null;
}

/* ── Styles einmalig injizieren ── */
(function _injectStyles() {
  if (document.getElementById('pat-selector-css')) return;
  var s = document.createElement('style');
  s.id = 'pat-selector-css';
  s.textContent = [
    '.pat-chip{display:flex;align-items:center;gap:12px;}',
    '.pat-chip__avatar{width:44px;height:44px;border-radius:50%;background:linear-gradient(135deg,#e8eef8,#c5d5f5);color:#3f6fe8;',
      'display:flex;align-items:center;justify-content:center;',
      'font-weight:900;font-size:15px;flex-shrink:0;letter-spacing:-.5px;user-select:none;}',
    '.pat-chip__avatar--accepted{background:linear-gradient(135deg,#bbf7d0,#86efac)!important;color:#166534!important;}',
    '.pat-chip__text{display:flex;flex-direction:column;gap:1px;}',
    '.pat-chip__name{font-size:20px;font-weight:800;color:#1d2b4f;line-height:1.2;}',
    '.pat-chip__birth{font-size:12px;color:#72809d;font-weight:500;}',
    '.pat-modal{position:fixed;inset:0;z-index:9000;display:flex;align-items:center;justify-content:center;}',
    '.pat-modal[hidden]{display:none!important;}',
    '.pat-backdrop{position:absolute;inset:0;background:rgba(11,27,58,.38);backdrop-filter:blur(4px);}',
    '.pat-panel{position:relative;background:#fff;border-radius:18px;',
      'border:1px solid rgba(63,111,232,.14);',
      'box-shadow:0 30px 80px rgba(11,27,58,.25);',
      'width:min(440px,calc(100% - 28px));max-height:80vh;overflow-y:auto;',
      '-webkit-overflow-scrolling:touch;z-index:1;}',
    '.pat-panel__head{display:flex;justify-content:space-between;align-items:center;',
      'padding:18px 22px;border-bottom:1px solid #e7edf7;',
      'position:sticky;top:0;background:#fff;z-index:2;}',
    '.pat-panel__title{font-size:16px;font-weight:800;color:#1d2b4f;}',
    '.pat-close{width:32px;height:32px;border:none;background:none;font-size:22px;',
      'color:#72809d;cursor:pointer;border-radius:8px;',
      'display:flex;align-items:center;justify-content:center;}',
    '.pat-close:hover{background:#e7edf7;}',
    '.pat-section-label{font-size:10px;font-weight:800;letter-spacing:.8px;text-transform:uppercase;',
      'color:#7a8faa;padding:10px 22px 4px;}',
    '.pat-list{padding:6px 0 10px;}',
    '.pat-row{display:flex;align-items:center;gap:14px;padding:11px 22px;cursor:pointer;transition:background .12s;}',
    '.pat-row:hover{background:#f7f9fe;}',
    '.pat-row.active{background:rgba(63,111,232,.07);}',
    '.pat-row__avatar-wrap{position:relative;flex-shrink:0;display:inline-flex;}',
    '.pat-row__avatar{width:40px;height:40px;border-radius:50%;background:linear-gradient(135deg,#e8eef8,#c5d5f5);color:#3f6fe8;',
      'display:flex;align-items:center;justify-content:center;',
      'font-weight:800;font-size:14px;flex-shrink:0;letter-spacing:-.5px;}',
    '.pat-row__avatar--accepted{background:linear-gradient(135deg,#bbf7d0,#86efac)!important;color:#166534!important;}',
    '.pat-row__avatar--f{background:linear-gradient(135deg,#f9a8d4,#fce7f3)!important;color:#831843!important;border:2px solid rgba(236,72,153,.35)!important;}',
    '.pat-row__avatar--m{background:linear-gradient(135deg,#93c5fd,#dbeafe)!important;color:#1e3a8a!important;border:2px solid rgba(59,130,246,.35)!important;}',
    '.pat-chip__avatar--f{background:linear-gradient(135deg,#f9a8d4,#fce7f3)!important;color:#831843!important;border:2px solid rgba(236,72,153,.35)!important;}',
    '.pat-chip__avatar--m{background:linear-gradient(135deg,#93c5fd,#dbeafe)!important;color:#1e3a8a!important;border:2px solid rgba(59,130,246,.35)!important;}',
    '.pat-row__dot{position:absolute;top:-2px;right:-2px;width:11px;height:11px;',
      'border-radius:50%;border:2px solid #fff;z-index:2;',
      'box-shadow:0 1px 3px rgba(0,0,0,.2);pointer-events:none;}',
    '.pat-row__dot--upcoming{background:#f59e0b;}',
    '.pat-row__dot--done{background:#22c55e;}',
    '.pat-row__dot--overdue{background:#ef4444;}',
    '.pat-row__info{flex:1;}',
    '.pat-row__name{font-size:13px;font-weight:700;color:#1d2b4f;}',
    '.pat-row__birth{font-size:11px;color:#72809d;margin-top:2px;}',
    '.pat-row__today{font-size:10px;font-weight:700;color:#16a34a;background:#dcfce7;',
      'border-radius:6px;padding:2px 6px;margin-left:6px;}',
    '.pat-row__check{color:#3f6fe8;font-size:18px;font-weight:900;}',
    '.pat-empty{padding:20px 22px;font-size:13px;color:#7a8faa;text-align:center;}',
    '.pat-search-wrap{padding:10px 16px 6px;position:sticky;top:57px;background:#fff;z-index:2;border-bottom:1px solid #edf0f7;}',
    '.pat-search{width:100%;box-sizing:border-box;height:38px;border-radius:10px;',
      'border:1.5px solid rgba(63,111,232,.22);background:#f7f9fe;',
      'padding:0 12px 0 34px;font-size:14px;color:#1d2b4f;font-family:inherit;outline:none;',
      'background-image:url("data:image/svg+xml,%3Csvg xmlns=\'http://www.w3.org/2000/svg\' width=\'16\' height=\'16\' fill=\'none\' viewBox=\'0 0 24 24\'%3E%3Ccircle cx=\'11\' cy=\'11\' r=\'7\' stroke=\'%2372809d\' stroke-width=\'2\'/%3E%3Cpath d=\'m16.5 16.5 3.5 3.5\' stroke=\'%2372809d\' stroke-width=\'2\' stroke-linecap=\'round\'/%3E%3C/svg%3E");',
      'background-repeat:no-repeat;background-position:10px center;}',
    '.pat-search:focus{border-color:#3f6fe8;background-color:#fff;box-shadow:0 0 0 3px rgba(63,111,232,.12);}',
  ].join('');
  document.head.appendChild(s);
})();

/* ── Chip rendern ── */
function _renderChip() {
  var p = _currentPat();
  var container = _containerId ? document.getElementById(_containerId) : null;
  if (container) {
    if (!p) {
      container.innerHTML = '<div class="pat-chip"><div class="pat-chip__text"><div class="pat-chip__name" style="color:#7a8faa;font-size:15px;">Kein Patient ausgewählt</div></div></div>';
    } else {
      var chipGCls = p.gender === 'f' ? ' pat-chip__avatar--f' : p.gender === 'm' ? ' pat-chip__avatar--m' : '';
      container.innerHTML =
        '<div class="pat-chip">' +
          '<div class="pat-chip__avatar' + (p.source === 'accepted' ? ' pat-chip__avatar--accepted' : '') + chipGCls + '">' + _initials(p.name) + '</div>' +
          '<div class="pat-chip__text">' +
            '<div class="pat-chip__name">' + p.name + '</div>' +
            '<div class="pat-chip__birth">' + (p.birth ? '\u2217\u00a0' + p.birth : (p.address || '')) + '</div>' +
          '</div>' +
        '</div>';
    }
  }
  var ne = _nameElId  ? document.getElementById(_nameElId)  : null;
  var be = _birthElId ? document.getElementById(_birthElId) : null;
  if (ne) ne.textContent = p ? p.name  : '';
  if (be) be.textContent = p ? p.birth : '';
}

/* ── Modal einmalig in <body> injizieren ── */
function _injectModal() {
  if (document.getElementById('patModal')) return;
  var wrap = document.createElement('div');
  wrap.innerHTML =
    '<div class="pat-modal" id="patModal" hidden>' +
      '<div class="pat-backdrop" id="patBackdrop"></div>' +
      '<div class="pat-panel">' +
        '<div class="pat-panel__head">' +
          '<span class="pat-panel__title">Patient auswählen</span>' +
          '<button class="pat-close" id="closePatModal" type="button">&#215;</button>' +
        '</div>' +
        '<div class="pat-search-wrap">' +
          '<input class="pat-search" id="patSearch" type="search" placeholder="Suchen…" autocomplete="off" />' +
        '</div>' +
        '<div class="pat-list" id="patList"></div>' +
      '</div>' +
    '</div>';
  document.body.appendChild(wrap.firstElementChild);
  document.getElementById('closePatModal').addEventListener('click', _closeModal);
  document.getElementById('patBackdrop').addEventListener('click',  _closeModal);

  /* Search live filter */
  document.getElementById('patSearch').addEventListener('input', function(){
    _renderPatList(this.value);
  });
}

function _closeModal() {
  var m = document.getElementById('patModal');
  if (m) m.hidden = true;
}

/* ── Patientenliste im Modal rendern ── */
/* ── DN-Status für Selector-Einträge ── */
var _PS_DF_TIMES = [
  {id:1,t:'07:00'},{id:2,t:'07:30'},{id:3,t:'08:00'},{id:4,t:'08:00'},
  {id:5,t:'09:00'},{id:6,t:'10:00'},{id:7,t:'10:00'},{id:8,t:'11:00'},
  {id:9,t:'12:00'},{id:10,t:'12:00'},{id:11,t:'13:00'},{id:12,t:'14:00'},
  {id:13,t:'15:00'},{id:14,t:'16:00'},{id:15,t:'18:00'},
  {id:16,t:'20:00'},{id:17,t:'20:00'},{id:18,t:'20:00'},
  {id:19,t:'21:00'},{id:20,t:'21:30'},
];
function _psdfStatus(p) {
  if (!p.visitToday) return '';
  var d = new Date();
  var today = d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
  function toMin(s){ var pp=(s||'00:00').split(':'); return +pp[0]*60+ +pp[1]; }
  var nowMin = d.getHours()*60+d.getMinutes();
  var from = p.visitFrom || p.from || '';
  if (nowMin < toMin(from)) return 'upcoming';
  var dfData = {};
  try{ dfData = JSON.parse(localStorage.getItem('nursy_df_v1_'+p.id+'_'+today)||'{}'); }catch(e){}
  var signedIds = {};
  Object.keys(dfData).forEach(function(k){ signedIds[+k]=1; });
  if (Object.keys(signedIds).length >= 20) return 'done';
  var overdue = _PS_DF_TIMES.filter(function(m){ return toMin(m.t)<=nowMin && !signedIds[m.id]; });
  return overdue.length>0 ? 'overdue' : 'done';
}

function _renderPatList(query) {
  _loadPatients();
  var list = document.getElementById('patList');
  if (!list) return;
  list.innerHTML = '';

  /* Filter by search query */
  var q = (query || '').trim().toLowerCase();
  var visible = q
    ? _allPatients.filter(function(p){
        return p.name.toLowerCase().indexOf(q) !== -1 ||
               (p.address||'').toLowerCase().indexOf(q) !== -1 ||
               (p.birth||'').indexOf(q) !== -1;
      })
    : _allPatients;

  if (!_allPatients.length) {
    var empty = document.createElement('div');
    empty.className = 'pat-empty';
    empty.textContent = 'Noch keine Patienten angelegt. Bitte zuerst Patienten in „Meine Patienten" hinzufügen.';
    list.appendChild(empty);
    return;
  }

  if (q && !visible.length) {
    var noRes = document.createElement('div');
    noRes.className = 'pat-empty';
    noRes.textContent = 'Keine Patienten gefunden.';
    list.appendChild(noRes);
    return;
  }

  var todayPats = visible.filter(function(p){ return p.visitToday; });
  var otherPats = visible.filter(function(p){ return !p.visitToday; });

  function _addLabel(text) {
    var lbl = document.createElement('div');
    lbl.className = 'pat-section-label';
    lbl.textContent = text;
    list.appendChild(lbl);
  }

  function _addRow(p) {
    var row = document.createElement('div');
    var isActive = (p.id === _selectedId);
    row.className = 'pat-row' + (isActive ? ' active' : '');
    var status  = _psdfStatus(p);
    var dotHtml = status
      ? '<span class="pat-row__dot pat-row__dot--'+status+'" title="'+
          (status==='upcoming' ? 'Einsatz noch bevorstehend'
          :status==='done'     ? 'Alle fälligen Maßnahmen abgezeichnet'
          :                      'Überfällige Maßnahmen nicht abgezeichnet!')+
          '"></span>'
      : '';
    var isAccepted = (p.source === 'accepted');
    var rowGCls = p.gender === 'f' ? ' pat-row__avatar--f' : p.gender === 'm' ? ' pat-row__avatar--m' : '';
    row.innerHTML =
      '<div class="pat-row__avatar-wrap">' +
        '<div class="pat-row__avatar' + (isAccepted ? ' pat-row__avatar--accepted' : '') + rowGCls + '">' + _initials(p.name) + '</div>' +
        dotHtml +
      '</div>' +
      '<div class="pat-row__info">' +
        '<div class="pat-row__name">' + p.name +
          (p.visitToday ? '<span class="pat-row__today">Heute</span>' : '') +
        '</div>' +
        '<div class="pat-row__birth">' +
          (p.birth ? '\u2217\u00a0' + p.birth : '') +
          (p.birth && p.pflegestufe ? '\u2002\u00b7\u2002' : '') +
          (p.pflegestufe ? 'PS\u00a0' + p.pflegestufe : '') +
        '</div>' +
      '</div>' +
      (isActive ? '<span class="pat-row__check">&#10003;</span>' : '');
    row.addEventListener('click', function(){ _selectPatient(p.id); });
    list.appendChild(row);
  }

  if (!q) {
    if (todayPats.length) {
      _addLabel('Heute im Einsatz');
      todayPats.forEach(_addRow);
    }
    if (otherPats.length) {
      _addLabel('Alle Patienten');
      otherPats.forEach(_addRow);
    }
  } else {
    visible.forEach(_addRow);
  }
}

/* ── Patient auswählen ── */
function _selectPatient(id) {
  _selectedId = id;
  localStorage.setItem('nursy_df_current_pat_id', id);
  _renderChip();
  _closeModal();
  _renderPatList();
  var idx = _allPatients.findIndex(function(p){ return p.id === id; });
  var p = _allPatients[idx >= 0 ? idx : 0];
  if (_onChangeCb && p) _onChangeCb(idx >= 0 ? idx : 0, p);
}

/* ── Öffentliche API ── */
function initPatientSelector(opts) {
  opts = opts || {};
  _containerId = opts.container || null;
  _nameElId    = opts.nameEl   || null;
  _birthElId   = opts.birthEl  || null;
  _onChangeCb  = opts.onChange || null;

  _loadPatients();
  _injectModal();
  _renderChip();

  var btnId = opts.openBtnId || 'openPatModal';
  var btn   = document.getElementById(btnId);
  if (btn) {
    btn.addEventListener('click', function() {
      var searchEl = document.getElementById('patSearch');
      if (searchEl) searchEl.value = '';
      _renderPatList('');
      document.getElementById('patModal').hidden = false;
      setTimeout(function(){ if(searchEl) searchEl.focus(); }, 80);
    });
  }
}

/* Rückwärtskompatibilität */
function getCurrentPatIdx() {
  return _allPatients.findIndex(function(p){ return p.id === _selectedId; });
}
function getCurrentPatientId() {
  return _selectedId || (_allPatients[0] ? _allPatients[0].id : '');
}
function getPatient(idxOrId) {
  if (idxOrId === undefined) return _currentPat();
  if (typeof idxOrId === 'number') return _allPatients[idxOrId] || null;
  return _allPatients.find(function(p){ return p.id === idxOrId; }) || null;
}

/* PATIENTS-Array für Rückwärtskompatibilität mit altem Index-Code */
var PATIENTS = new Proxy([], {
  get: function(target, prop) {
    if (prop === 'length') return _allPatients.length;
    var idx = Number(prop);
    if (!isNaN(idx)) return _allPatients[idx];
    return target[prop];
  }
});
