(function(){
'use strict';

/* ── Storage helpers ── */
const safe = {
  get(k){ try{ return localStorage.getItem(k); }catch(e){ return null; } },
  set(k,v){ try{ localStorage.setItem(k,v); }catch(e){} },
  remove(k){ try{ localStorage.removeItem(k); }catch(e){} }
};

const DEMO_KEY     = 'nursy_patients_demo_v3';
/* Dynamischer Schlüssel – user-spezifisch via getCarePatKey() (script.js) */
function _accKey(){ return window.getCarePatKey ? window.getCarePatKey() : 'nursy_accepted_patients_v1'; }

/* ── DN-Maßnahmen: Uhrzeiten aus Cache lesen (geschrieben von durchfuehrungsnachweis.html) ── */
function _getDfTimes(patId){
  return window.dfMeasures ? window.dfMeasures.times(patId) : [];
}
function _getDfTotal(patId){
  return window.dfMeasures ? window.dfMeasures.total(patId) : 0;
}

/* ── Status-Berechnung für heutige Einsätze ── */
function dfStatus(p, visit){
  if(!visit) return '';
  const todayStr = isoDate();
  const now = new Date();

  function toMin(hhmm){
    const [h,m] = (hhmm||'00:00').split(':').map(Number);
    return h*60+m;
  }
  const nowMin  = now.getHours()*60 + now.getMinutes();
  const fromMin = toMin(visit.from);

  // 1) Noch nicht gestartet → orange
  if(nowMin < fromMin) return 'upcoming';

  // 2) DN-Daten laden
  let dfData = {};
  try{ dfData = JSON.parse(localStorage.getItem('nursy_df_v1_'+p.id+'_'+todayStr)||'{}'); }catch(e){}
  const signedIds = new Set(Object.keys(dfData));
  const signedCount = signedIds.size;

  const dfTimes = _getDfTimes(p.id);
  const dfTotal = _getDfTotal(p.id);

  // 3) Alle abgezeichnet → grün
  if(signedCount >= dfTotal) return 'done';

  // 4) Überfällige Maßnahmen = Uhrzeit <= jetzt UND nicht abgezeichnet
  const overdue = dfTimes.filter(function(m){
    return toMin(m.t) <= nowMin && !signedIds.has(String(m.id));
  });

  if(overdue.length > 0) return 'overdue'; // rot
  return 'done'; // alle fälligen erledigt → grün
}

/* ── Datum-Utils ── */
function isoDate(d = new Date()){
  return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
}
function fmtDate(iso){
  if(!iso) return '—';
  const [y,m,d] = iso.split('-');
  return `${d}.${m}.${y}`;
}

/* ── Demo-Patienten entfernt – alle Patienten kommen aus der API/accepted-Liste ── */
function seedDemo(){ return []; }

function loadDemoPatients(){
  /* Alten Demo-Key + alten globalen Patienten-Key bereinigen */
  safe.remove(DEMO_KEY);
  safe.remove('nursy_db_patients_v1');
  return [];
}

function loadAcceptedPatients(){
  const raw = safe.get(_accKey());
  if(!raw) return [];
  try{ return JSON.parse(raw); }catch(e){ return []; }
}

/* Convert accepted-patient format → internal patient format */
function acceptedToPatient(ap){
  let visits;
  if(Array.isArray(ap.visits) && ap.visits.length){
    visits = ap.visits;
  } else {
    visits = ap.visitDate ? [{ date: ap.visitDate, from: ap.visitFrom||'', to: ap.visitTo||'' }] : [];
  }
  return {
    id: ap.id,
    name: ap.name,
    gender: ap.gender || '',
    age: ap.age || null,
    pflegestufe: ap.pflegestufe || null,
    address: ap.address || '',
    needs: ap.needs || '',
    wunsch: ap.wunsch || '',
    haeufigkeit: ap.haeufigkeit || '',
    hauptgrund: ap.hauptgrund || '',
    active: true,
    source: 'accepted',
    visits: visits
  };
}

function savePatientGender(id, gender){
  const acc = loadAcceptedPatients();
  const ai = acc.findIndex(a => a.id === id);
  if(ai >= 0){ acc[ai].gender = gender; safe.set(_accKey(), JSON.stringify(acc)); }
}

/* Nur eigene angenommene Klienten – komplett isoliert pro Pfleger */
function loadAllPatients(){
  return loadAcceptedPatients().map(acceptedToPatient).filter(p => p.active !== false);
}

function savePatient(p){
  const acc = loadAcceptedPatients();
  const idx = acc.findIndex(a => a.id === p.id);
  if(idx >= 0){
    acc[idx].visits     = p.visits;
    acc[idx].visitDate  = p.visits[0]?.date  || acc[idx].visitDate;
    acc[idx].visitFrom  = p.visits[0]?.from  || acc[idx].visitFrom;
    acc[idx].visitTo    = p.visits[0]?.to    || acc[idx].visitTo;
    safe.set(_accKey(), JSON.stringify(acc));
  }
}

function saveAllVisits(patients){
  const accepted = loadAcceptedPatients();
  patients.forEach(p => {
    const idx = accepted.findIndex(a => a.id === p.id);
    if(idx >= 0){
      accepted[idx].visits    = p.visits;
      accepted[idx].visitDate = p.visits[0]?.date || '';
      accepted[idx].visitFrom = p.visits[0]?.from || '';
      accepted[idx].visitTo   = p.visits[0]?.to   || '';
    }
  });
  safe.set(_accKey(), JSON.stringify(accepted));
}

/* ── Patient entfernen ── */
function removePatientById(patientId){
  const accepted = loadAcceptedPatients();
  const accIdx   = accepted.findIndex(a => a.id === patientId);
  if(accIdx >= 0){
    accepted.splice(accIdx, 1);
    safe.set(_accKey(), JSON.stringify(accepted));
  }
}

/* ── Initials helper ── */
function initials(name){
  const pts = (name||'?').trim().split(' ');
  return (pts[0][0]+(pts[1]?pts[1][0]:'')).toUpperCase();
}

/* ── Aktueller Edit-Kontext ── */
let __currentEdit = null;

/* ── Row bauen ── */
function makeRow(p, visit){
  const row = document.createElement('div');
  row.className = 'patient-row';

  /* Avatar + Status-Dot */
  const avWrap = document.createElement('div');
  avWrap.className = 'patient-avatar-wrap';

  const av = document.createElement('div');
  av.className = 'patient-avatar';
  av.textContent = initials(p.name);
  if(p.source === 'accepted') av.classList.add('patient-avatar--accepted');
  if(p.gender === 'f') av.classList.add('patient-avatar--f');
  else if(p.gender === 'm') av.classList.add('patient-avatar--m');

  avWrap.appendChild(av);

  /* Status nur für heutige Einsätze berechnen */
  const todayVisit = visit && visit.date === isoDate() ? visit : null;
  if(todayVisit){
    const allPats = loadAllPatients();
    const status  = dfStatus(p, todayVisit, allPats);
    if(status){
      const dot = document.createElement('span');
      dot.className = 'visit-dot visit-dot--' + status;
      dot.title = status === 'upcoming' ? 'Einsatz noch bevorstehend'
                : status === 'done'     ? 'Alle fälligen Maßnahmen abgezeichnet'
                :                         'Überfällige Maßnahmen nicht abgezeichnet!';
      avWrap.appendChild(dot);
    }
  }

  avWrap.appendChild(av);

  /* Status nur für heutige Einsätze berechnen */
  const todayVisit = visit && visit.date === isoDate() ? visit : null;
  if(todayVisit){
    const status  = dfStatus(p, todayVisit);
    if(status){
      const dot = document.createElement('span');
      dot.className = 'visit-dot visit-dot--' + status;
      dot.title = status === 'upcoming' ? 'Einsatz noch bevorstehend'
                : status === 'done'     ? 'Alle fälligen Maßnahmen abgezeichnet'
                :                         'Überfällige Maßnahmen nicht abgezeichnet!';
      avWrap.appendChild(dot);
    }
  }

  /* Info */
  const info = document.createElement('div');
  info.className = 'patient-info';
  const nameEl = document.createElement('div');
  nameEl.className = 'patient-name';
  nameEl.textContent = p.name;

  const metaEl = document.createElement('div');
  metaEl.className = 'patient-address';
  let metaParts = [p.address];
  if(p.pflegestufe) metaParts.unshift(p.pflegestufe);
  metaEl.textContent = metaParts.join(' · ');

  /* Inline-Geschlecht-Auswahl wenn noch kein Geschlecht gesetzt */
  const genderEl = document.createElement('div');
  genderEl.className = 'patient-gender-pick';
  if(!p.gender){
    genderEl.innerHTML =
      '<span class="pgp-label">Geschlecht:</span>' +
      '<select class="pgp-select">' +
        '<option value="">— wählen —</option>' +
        '<option value="f">Weiblich</option>' +
        '<option value="m">Männlich</option>' +
        '<option value="d">Divers</option>' +
      '</select>';
    genderEl.querySelector('select').addEventListener('change', function(){
      const g = this.value;
      if(!g) return;
      savePatientGender(p.id, g);
      p.gender = g;
      av.className = 'patient-avatar';
      if(p.source === 'accepted') av.classList.add('patient-avatar--accepted');
      if(g === 'f') av.classList.add('patient-avatar--f');
      else if(g === 'm') av.classList.add('patient-avatar--m');
      genderEl.remove();
    });
  }

  info.append(nameEl, metaEl, genderEl);

  /* Zeitfeld */
  const timeText = visit ? `${visit.from} – ${visit.to}` : '—';
  const time = document.createElement('button');
  time.className = 'patient-time patient-time--editable';
  time.type = 'button';
  time.title = 'Zeit bearbeiten';

  const isCancelled = !!(visit && visit.cancelled);
  if(isCancelled) row.classList.add('is-cancelled');

  const dateForEdit = visit?.date || isoDate();
  time.innerHTML = `<span class="pt-time-val">${timeText}</span><span class="pt-date-val">${fmtDate(dateForEdit)}</span>`;
  time.classList.add(isCancelled ? 'pt--cancelled' : 'pt--active');
  time.dataset.patientId = p.id;
  time.dataset.visitDate  = dateForEdit;
  time.addEventListener('click', () => openTimeModal(p.id, dateForEdit, visit?.from));

  /* Actions */
  const actions = document.createElement('div');
  actions.className = 'patient-actions';

  const profBtn = document.createElement('button');
  profBtn.className = 'btn btn--ghost';
  profBtn.type = 'button';
  profBtn.textContent = 'Profil';
  profBtn.addEventListener('click', () => openProfileModal(p.id));

  const navBtn = document.createElement('button');
  navBtn.className = 'btn btn--secondary';
  navBtn.type = 'button';
  navBtn.textContent = 'Navigation';
  navBtn.addEventListener('click', () => openMapsAddress(p.address));

  const msgBtn = document.createElement('button');
  msgBtn.className = 'btn btn--primary';
  msgBtn.type = 'button';
  msgBtn.textContent = 'Nachricht';
  msgBtn.addEventListener('click', () => openMessageModal(p.id));

  const ablBtn = document.createElement('button');
  ablBtn.className = 'btn btn--danger btn--ablehnen';
  ablBtn.type = 'button';
  ablBtn.textContent = 'Beenden';
  ablBtn.title = 'Betreuung beenden';
  ablBtn.addEventListener('click', () => openBeendenModal(p.id, p.name));

  actions.append(profBtn, navBtn, msgBtn, ablBtn);
  row.append(avWrap, info, time, actions);
  return row;
}

/* ── Tour-Button ── */
function openTourPlanning(patients){
  const today = isoDate();
  const todayPats = patients
    .filter(p => (p.visits||[]).some(v => v.date === today && !v.cancelled))
    .sort((a,b) => {
      const va = (a.visits||[]).find(v=>v.date===today);
      const vb = (b.visits||[]).find(v=>v.date===today);
      return (va?.from||'').localeCompare(vb?.from||'');
    });

  if(!todayPats.length){
    alert('Für heute sind keine aktiven Einsätze geplant.');
    return;
  }
  const addresses = todayPats.map(p => encodeURIComponent(p.address)).join('/');
  const url = `https://www.google.com/maps/dir/${addresses}`;
  window.open(url, '_blank');
}

/* ── Navigation ── */
function openMapsAddress(address){
  if(!address){ alert('Keine Adresse hinterlegt.'); return; }
  const url = `https://www.google.com/maps/search/${encodeURIComponent(address)}`;
  window.open(url, '_blank');
}

/* ── Render ── */
function render(){
  const patients   = loadAllPatients();
  const today      = isoDate();
  const todayList  = document.getElementById('todayList');
  const activeList = document.getElementById('activeList');
  const todayEmpty = document.getElementById('todayEmpty');
  const activeEmpty= document.getElementById('activeEmpty');
  const todayCount = document.getElementById('todayCount');
  const activeCount= document.getElementById('activeCount');

  todayList.innerHTML  = '';
  activeList.innerHTML = '';

  const active    = patients.filter(p => p.active !== false);
  const todayRows = [];

  for(const p of active){
    const todayVisits = (p.visits||[]).filter(v => v.date === today);
    for(const v of todayVisits) todayRows.push({p, v});
  }

  todayCount.textContent  = String(todayRows.length);
  todayEmpty.hidden       = todayRows.length !== 0;

  /* Tour-Button */
  const tourBtn = document.getElementById('tourBtn');
  if(tourBtn) tourBtn.style.display = todayRows.length > 0 ? '' : 'none';

  for(const r of todayRows.sort((a,b)=>a.v.from.localeCompare(b.v.from))){
    todayList.appendChild(makeRow(r.p, r.v));
  }

  activeCount.textContent = String(active.length);
  activeEmpty.hidden      = active.length !== 0;

  // Sortierung nach heutiger Besuchszeit (morgens → mittags → abends),
  // danach nach nächstem Termin, Patienten ohne Termin zuletzt
  const sortedActive = active.slice().sort((a, b) => {
    const va = (a.visits||[]).find(x => x.date === today && !x.cancelled);
    const vb = (b.visits||[]).find(x => x.date === today && !x.cancelled);
    if (va && vb) return (va.from||'').localeCompare(vb.from||'');
    if (va) return -1;
    if (vb) return  1;
    // kein heutiger Termin: nach nächstem zukünftigen Termin sortieren
    const na = (a.visits||[]).filter(x=>x.date>=today).sort((x,y)=>(x.date+x.from).localeCompare(y.date+y.from))[0];
    const nb = (b.visits||[]).filter(x=>x.date>=today).sort((x,y)=>(x.date+x.from).localeCompare(y.date+y.from))[0];
    if (na && nb) return (na.date+na.from).localeCompare(nb.date+nb.from);
    if (na) return -1;
    if (nb) return  1;
    return 0;
  });

  for(const p of sortedActive){
    const visits = (p.visits||[]).slice().sort((a,b)=>(a.date+a.from).localeCompare(b.date+b.from));
    const v = visits.find(x=>x.date===today) || visits[0];
    activeList.appendChild(makeRow(p, v||null));
  }
}

/* ════════════════════════════════
   ZEIT-MODAL
════════════════════════════════ */
let modalState = { patientId:null, date:null, fromOrig:null };

function openTimeModal(patientId, date, fromOrig){
  __currentEdit = { patientId, date, fromOrig: fromOrig || null };
  updateCancelUI();
  const modal = document.getElementById('timeModal');
  const from  = document.getElementById('timeFrom');
  const to    = document.getElementById('timeTo');
  const hint  = document.getElementById('timeHint');
  const dateF = document.getElementById('timeDate');
  if(!modal) return;

  const patients = loadAllPatients();
  const p = patients.find(x => x.id === patientId);
  const v = fromOrig
    ? (p?.visits||[]).find(x => x.date === date && x.from === fromOrig)
    : (p?.visits||[]).find(x => x.date === date);

  if(from) from.value = v?.from || '08:00';
  if(to)   to.value   = v?.to   || '09:00';
  if(dateF) dateF.value = date;
  if(hint) hint.textContent = `${p?.name||''} · ${fmtDate(date)}`;

  modalState = { patientId, date, fromOrig: fromOrig || null };
  modal.hidden = false;
  setTimeout(() => from?.focus(), 50);
}

function closeTimeModal(){
  const modal = document.getElementById('timeModal');
  if(modal) modal.hidden = true;
  modalState = { patientId:null, date:null, fromOrig:null };
}

function saveTimeModal(){
  const from = document.getElementById('timeFrom');
  const to   = document.getElementById('timeTo');
  const dateF= document.getElementById('timeDate');
  const hint = document.getElementById('timeHint');
  if(!modalState.patientId) return;

  const newDate = dateF?.value || modalState.date;
  const f = from?.value || '';
  const t = to?.value   || '';
  if(!f||!t){ if(hint) hint.textContent='Bitte beide Zeiten auswählen.'; return; }
  if(t<=f){   if(hint) hint.textContent='Endzeit muss nach der Startzeit liegen.'; return; }

  const patients = loadAllPatients();
  const p = patients.find(x => x.id === modalState.patientId);
  if(!p) return;

  p.visits = Array.isArray(p.visits) ? p.visits : [];
  /* Remove only the specific visit being edited, then add updated one */
  const oldCancelled = modalState.fromOrig
    ? (p.visits.find(x => x.date === modalState.date && x.from === modalState.fromOrig) || {}).cancelled
    : (p.visits.find(x => x.date === modalState.date) || {}).cancelled;
  p.visits = p.visits.filter(x => {
    if(modalState.fromOrig)
      return !(x.date === modalState.date && x.from === modalState.fromOrig);
    return x.date !== modalState.date;
  });
  p.visits.push({ date: newDate, from: f, to: t, ...(oldCancelled ? {cancelled: true} : {}) });

  saveAllVisits(patients);
  closeTimeModal();
  render();
}

function updateCancelUI(){
  const btn  = document.getElementById('timeCancel');
  const hint = document.getElementById('timeHint');
  if(!btn || !__currentEdit) return;
  const patients = loadAllPatients();
  const p = patients.find(x => x.id === __currentEdit.patientId);
  const v = __currentEdit.fromOrig
    ? (p?.visits||[]).find(x => x.date === __currentEdit.date && x.from === __currentEdit.fromOrig)
    : (p?.visits||[]).find(x => x.date === __currentEdit.date);
  const cancelled = !!(v && v.cancelled);
  if(hint){
    hint.innerHTML = `<strong>${p?.name||''}</strong> · ${fmtDate(__currentEdit.date)} · ` +
      `<span style="color:${cancelled?'#b91c1c':'#065f46'};font-weight:700">${cancelled?'Storniert':'Aktiv'}</span>` +
      (cancelled?' — Stornierung aufheben möglich.':'');
  }
  btn.textContent = cancelled ? 'Stornierung aufheben' : 'Auftrag stornieren';
  btn.classList.remove('btn--danger','btn--success');
  btn.classList.add(cancelled ? 'btn--success' : 'btn--danger');
}

function toggleCancel(){
  if(!__currentEdit) return;
  const patients = loadAllPatients();
  const p = patients.find(x => x.id === __currentEdit.patientId);
  if(!p) return;
  const v = __currentEdit.fromOrig
    ? (p.visits||[]).find(x => x.date === __currentEdit.date && x.from === __currentEdit.fromOrig)
    : (p.visits||[]).find(x => x.date === __currentEdit.date);
  if(!v) return;
  const msg = v.cancelled
    ? 'Stornierung aufheben und Auftrag wieder aktivieren?'
    : 'Diesen Auftrag wirklich stornieren?';
  if(!confirm(msg)) return;
  v.cancelled = !v.cancelled;
  saveAllVisits(patients);
  updateCancelUI();
  render();
}

/* ════════════════════════════════
   PROFIL-MODAL
════════════════════════════════ */
function openProfileModal(patientId){
  const modal = document.getElementById('profileModal');
  if(!modal) return;
  const patients = loadAllPatients();
  const p = patients.find(x => x.id === patientId);
  if(!p) return;

  document.getElementById('pm-avatar').textContent   = initials(p.name);
  document.getElementById('pm-name').textContent     = p.name;
  document.getElementById('pm-age').textContent      = p.age ? p.age + ' Jahre' : '';
  document.getElementById('pm-stufe').textContent    = p.pflegestufe || '—';
  document.getElementById('pm-address').textContent  = p.address || '—';
  document.getElementById('pm-needs').textContent    = p.needs || '—';

  const hRow = document.getElementById('pm-haeufigkeit-row');
  const hEl  = document.getElementById('pm-haeufigkeit');
  if(hEl){
    const hText = p.haeufigkeit ||
      (p.visits && p.visits.length > 0 ? p.visits.length + '× geplant' : '');
    hEl.textContent = hText || '—';
    if(hRow) hRow.style.display = hText ? '' : 'none';
  }

  const gRow = document.getElementById('pm-hauptgrund-row');
  const gEl  = document.getElementById('pm-hauptgrund');
  if(gEl){
    gEl.textContent = p.hauptgrund || '—';
    if(gRow) gRow.style.display = p.hauptgrund ? '' : 'none';
  }

  const wunschEl = document.getElementById('pm-wunsch');
  if(wunschEl){
    wunschEl.textContent = p.wunsch || '';
    wunschEl.closest('.pm-wish-wrap').style.display = p.wunsch ? '' : 'none';
  }

  const visits = (p.visits||[]).slice().sort((a,b)=>(a.date+a.from).localeCompare(b.date+b.from));
  const vList = document.getElementById('pm-visits');
  if(vList){
    if(visits.length){
      vList.innerHTML = visits.map(v =>
        `<div class="pm-visit ${v.cancelled?'pm-visit--cancelled':''}">
          <span class="pm-visit__date">${fmtDate(v.date)}</span>
          <span class="pm-visit__time">${v.from} – ${v.to}</span>
          <span class="pm-visit__status">${v.cancelled?'Storniert':'Aktiv'}</span>
        </div>`
      ).join('');
    } else {
      vList.innerHTML = '<p class="muted" style="margin:0">Noch keine Einsätze geplant.</p>';
    }
  }

  /* Nav-Button im Profil */
  const navBtnP = document.getElementById('pm-navBtn');
  if(navBtnP) navBtnP.onclick = () => openMapsAddress(p.address);

  /* Nachricht-Button im Profil */
  const msgBtnP = document.getElementById('pm-msgBtn');
  if(msgBtnP) msgBtnP.onclick = () => { closeProfileModal(); openMessageModal(p.id); };

  /* Beenden-Button im Profil */
  const ablBtnP = document.getElementById('pm-ablBtn');
  if(ablBtnP) ablBtnP.onclick = () => {
    closeProfileModal();
    openBeendenModal(p.id, p.name);
  };

  modal.hidden = false;
}

function closeProfileModal(){
  const modal = document.getElementById('profileModal');
  if(modal) modal.hidden = true;
}

/* ════════════════════════════════
   NACHRICHTEN-MODAL
════════════════════════════════ */
let __msgPatientId = null;

function openMessageModal(patientId){
  const modal = document.getElementById('msgModal');
  if(!modal) return;
  const patients = loadAllPatients();
  const p = patients.find(x => x.id === patientId);
  __msgPatientId = patientId;
  const toEl = document.getElementById('msg-to');
  const ta   = document.getElementById('msg-text');
  const conf = document.getElementById('msg-confirm');
  if(toEl) toEl.textContent = p?.name || '—';
  if(ta)   ta.value = '';
  if(conf) conf.style.display = 'none';
  modal.hidden = false;
  setTimeout(()=> ta?.focus(), 50);
}

function closeMessageModal(){
  const modal = document.getElementById('msgModal');
  if(modal) modal.hidden = true;
  __msgPatientId = null;
}

function sendMessage(){
  const ta   = document.getElementById('msg-text');
  const conf = document.getElementById('msg-confirm');
  if(!ta?.value.trim()){ ta?.focus(); return; }
  if(conf) conf.style.display = '';
  if(ta)   ta.value = '';
  setTimeout(() => closeMessageModal(), 1800);
}

/* ════════════════════════════════
   INIT
════════════════════════════════ */
document.addEventListener('DOMContentLoaded', () => {
  render();

  /* Automatische Aktualisierung: alle 60 s neu rendern (orange→rot bei Zeitüberschreitung) */
  setInterval(render, 60_000);

  /* Sofort-Aktualisierung wenn Durchführungsnachweis-Daten geändert werden */
  window.addEventListener('storage', function(e){
    if(e.key && (e.key.startsWith('nursy_df_v1_') || e.key.startsWith('nursy_pp_wund_v1_'))) render();
  });
  window.addEventListener('nursy:df-updated', function(){ render(); });
  window.addEventListener('nursy:wunddoku-updated', function(){ render(); });
  window.addEventListener('nursy:ppwund-updated', function(){ render(); });

  const allPatients = loadAllPatients();

  /* Tour-Button */
  document.getElementById('tourBtn')?.addEventListener('click', () => openTourPlanning(allPatients));

  /* Demo-Key beim Start bereinigen */
  safe.remove(DEMO_KEY);

  /* Zeit-Modal */
  document.getElementById('timeSave')?.addEventListener('click', saveTimeModal);
  document.getElementById('timeCancel')?.addEventListener('click', toggleCancel);
  document.getElementById('timeModal')?.addEventListener('click', e => {
    if(e.target.matches('[data-close]')) closeTimeModal();
  });

  /* Profil-Modal */
  document.getElementById('profileModal')?.addEventListener('click', e => {
    if(e.target.matches('[data-close]')) closeProfileModal();
  });

  /* Nachrichten-Modal */
  document.getElementById('msgSend')?.addEventListener('click', sendMessage);
  document.getElementById('msgModal')?.addEventListener('click', e => {
    if(e.target.matches('[data-close]')) closeMessageModal();
  });

  /* ESC schließt alle Modals */
  document.addEventListener('keydown', e => {
    if(e.key !== 'Escape') return;
    closeTimeModal();
    closeProfileModal();
    closeMessageModal();
    closeBeendenModal();
  });
});

/* ════════ BEENDEN-MODAL ════════ */
let _beendenPatId   = null;
let _beendenPatName = '';

function openBeendenModal(patId, patName){
  _beendenPatId   = patId;
  _beendenPatName = patName;
  const modal  = document.getElementById('beendenModal');
  const sub    = document.getElementById('beendenSubtitle');
  const errEl  = document.getElementById('beendenError');
  const sField = document.getElementById('beendenSonstField');
  if(sub)    sub.textContent   = patName;
  if(errEl)  errEl.textContent = '';
  if(sField) sField.style.display = 'none';
  /* Alle Radios zurücksetzen */
  document.querySelectorAll('input[name="beendenGrund"]').forEach(r => r.checked = false);
  const sText = document.getElementById('beendenSonstText');
  if(sText) sText.value = '';
  if(modal) modal.hidden = false;
}

function closeBeendenModal(){
  const modal = document.getElementById('beendenModal');
  if(modal) modal.hidden = true;
  _beendenPatId = null;
}

(function initBeendenModal(){
  /* Radio → highlight & Sonstiges-Feld */
  document.querySelectorAll('input[name="beendenGrund"]').forEach(radio => {
    radio.addEventListener('change', function(){
      document.querySelectorAll('label[id^="bGrund"]').forEach(l => {
        l.style.borderColor  = 'rgba(11,27,58,.15)';
        l.style.background   = '#fff';
      });
      const lbl = this.closest('label');
      if(lbl){ lbl.style.borderColor = '#1d2b4f'; lbl.style.background = '#f0f4fb'; }
      const sField = document.getElementById('beendenSonstField');
      if(sField) sField.style.display = (this.value === 'Sonstiges') ? 'block' : 'none';
    });
  });

  /* Schließen */
  ['beendenClose','beendenAbbrechen','beendenBackdrop'].forEach(id => {
    const el = document.getElementById(id);
    if(el) el.addEventListener('click', closeBeendenModal);
  });

  /* Speichern */
  const saveBtn = document.getElementById('beendenSaveBtn');
  if(saveBtn){
    saveBtn.addEventListener('click', async function(){
      const errEl  = document.getElementById('beendenError');
      const chosen = document.querySelector('input[name="beendenGrund"]:checked');
      if(!chosen){ errEl.textContent = 'Bitte einen Grund wählen.'; return; }
      let grund = chosen.value;
      if(grund === 'Sonstiges'){
        const txt = (document.getElementById('beendenSonstText').value||'').trim();
        if(!txt){ errEl.textContent = 'Bitte Grund für „Sonstiges" eingeben.'; return; }
        grund = 'Sonstiges: ' + txt;
      }
      errEl.textContent = '';
      saveBtn.disabled = true;
      /* 1. Zuerst Server beenden – dann kann kein Reload mehr wiederherstellen */
      try {
        await fetch('/api/care/meine-patienten/' + encodeURIComponent(_beendenPatId), {
          method: 'DELETE',
          credentials: 'include'
        });
      } catch(e) {}
      /* 2. Lokal entfernen + UI aktualisieren */
      removePatientById(_beendenPatId);
      closeBeendenModal();
      render();
      saveBtn.disabled = false;
      /* Toast */
      const toast = document.createElement('div');
      toast.textContent = (_beendenPatName || 'Patient') + ' wurde beendet.';
      toast.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#b91c1c;color:#fff;padding:12px 22px;border-radius:12px;font-size:14px;font-weight:700;z-index:9999;box-shadow:0 4px 20px rgba(0,0,0,.2);white-space:nowrap;';
      document.body.appendChild(toast);
      setTimeout(() => toast.remove(), 3000);
    });
  }
})();

/* Async: eigene Klienten vom Server laden (isoliert per Pfleger via caregiver_id) */
(async function(){
  try{
    const resp = await fetch('/api/care/meine-patienten', {credentials:'include'});
    if(!resp.ok) return;
    const data = await resp.json();
    if(!data.ok || !Array.isArray(data.patients)) return;
    if(data.caregiver_id && window.setCareUid) window.setCareUid(data.caregiver_id);
    safe.set(_accKey(), JSON.stringify(data.patients));
    render();
  }catch(e){}
})();

})();
