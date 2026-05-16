(function(){

  /* ── Lokale Namensliste, befüllt beim Laden via /api/care/pflegeplanung/<patId> ── */
  var _localNameMap = {}; /* patId → { id → massnahme } */

  /* Statische Fallback-Liste für häufige Standard-Maßnahmen */
  var HARDCODED_MEASURES = [
    {id:'1',  massnahme:'Medikamentengabe oral (Frühgabe)'},
    {id:'2',  massnahme:'Ganzkörperpflege / Körperpflege'},
    {id:'3',  massnahme:'Blutdruck- & Pulskontrolle'},
    {id:'4',  massnahme:'Atemübungen & Positionierung'},
    {id:'5',  massnahme:'Medikamentengabe oral (Abendgabe)'},
    {id:'6',  massnahme:'Abendpflege / Mundpflege'},
    {id:'7',  massnahme:'Mobilisation & Gehtraining'},
    {id:'8',  massnahme:'Verbandwechsel'},
    {id:'9',  massnahme:'Blutzuckermessung'},
    {id:'10', massnahme:'Lagerung / Dekubitusprophylaxe'},
  ];

  /* ── Maßnahmen-Name auflösen:
       1. lokale Map (befüllt via API-Fetch beim Laden)
       2. dfMeasures-Cache (geschrieben von pflegeplanung.html / durchfuehrungsnachweis.html)
       3. statische Fallback-Liste
       4. generisches Label ── */
  function measureName(id, patId){
    var sid = String(id);
    /* 1. lokale Map */
    if(patId && _localNameMap[patId] && _localNameMap[patId][sid]){
      return _localNameMap[patId][sid];
    }
    /* 2. dfMeasures-Cache */
    var names = (window.dfMeasures && window.dfMeasures.names(patId)) || [];
    var m = names.filter(function(x){ return String(x.id) === sid; })[0];
    if(m && m.massnahme) return m.massnahme;
    /* 3. statische Fallback-Liste */
    var hc = HARDCODED_MEASURES.filter(function(x){ return x.id === sid; })[0];
    if(hc) return hc.massnahme;
    /* 4. generisch */
    return 'Maßnahme ' + id;
  }

  function esc(s){
    return String(s == null ? '' : s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
  }

  /* ── Gender-Avatar Chip ── */
  function cgGender(name){
    try{
      var all = JSON.parse(localStorage.getItem('nursy_client_caregivers_v1') || '[]') || [];
      var found = all.filter(function(x){ return x.name === name; })[0];
      if(found) return found.gender || '';
    }catch(e){}
    return '';
  }
  function cgInitials(name){
    var p = String(name||'').trim().split(/\s+/).filter(Boolean);
    if(!p.length) return '?';
    return (p[0][0] + (p.length > 1 ? p[p.length-1][0] : '')).toUpperCase();
  }
  function cgAvatar(name){
    var g = cgGender(name);
    var cls = g === 'f' ? 'cg-chip cg-chip--f' : g === 'm' ? 'cg-chip cg-chip--m' : 'cg-chip';
    return '<span class="' + cls + '" title="' + esc(name) + '">' + esc(cgInitials(name)) + '</span>';
  }

  function isoToday(){
    var d = new Date();
    return d.getFullYear() + '-' +
      String(d.getMonth()+1).padStart(2,'0') + '-' +
      String(d.getDate()).padStart(2,'0');
  }

  function formatDate(iso){
    if(!iso) return '—';
    var d = new Date(iso + 'T00:00:00');
    return new Intl.DateTimeFormat('de-AT',{weekday:'long',day:'2-digit',month:'2-digit',year:'numeric'}).format(d);
  }

  /* ── Aktuellen Patienten-ID ermitteln ── */
  function getCurrentPatId(){
    return localStorage.getItem('nursy_df_current_pat_id') || null;
  }

  /* ── Echte Pflegekraft-Daten laden ── */
  function loadRealEntries(){
    var patId = getCurrentPatId();
    if(!patId) return [];
    var today = isoToday();
    var rows = [];

    /* Heutiger Tag */
    try{
      var dayKey = 'nursy_df_v1_' + patId + '_' + today;
      var dayData = JSON.parse(localStorage.getItem(dayKey) || '{}') || {};
      Object.keys(dayData).forEach(function(taskId){
        var signed = dayData[taskId];
        if(!signed || !signed.time) return;
        rows.push({date:today, time:signed.time, measure:measureName(taskId, patId), caregiver:signed.name||'Pflegekraft'});
      });
    }catch(e){}

    /* Archiv vergangener Tage */
    try{
      var archKey = 'nursy_df_archive_v1_' + patId;
      var archive = JSON.parse(localStorage.getItem(archKey) || '[]') || [];
      archive.forEach(function(entry){
        var date = entry.date;
        var data = entry.data || {};
        Object.keys(data).forEach(function(taskId){
          var signed = data[taskId];
          if(!signed || !signed.time) return;
          rows.push({date:date, time:signed.time, measure:measureName(taskId, patId), caregiver:signed.name||'Pflegekraft'});
        });
      });
    }catch(e){}

    return rows;
  }

  /* ── Demo-Fallback (nur wenn keinerlei echte Daten vorhanden) ── */
  function demoEntries(){
    var t = isoToday();
    var off = function(n){
      var d = new Date(); d.setDate(d.getDate()+n);
      return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
    };
    return [
      {date:t,      time:'08:15', measure:'Medikamentengabe oral (Frühgabe)',  caregiver:'Markus Berger'},
      {date:t,      time:'09:30', measure:'Ganzkörperpflege / Körperpflege',  caregiver:'Anna Müller'},
      {date:t,      time:'12:00', measure:'Blutdruck- & Pulskontrolle',       caregiver:'Anna Müller'},
      {date:off(-1),time:'08:00', measure:'Medikamentengabe oral (Frühgabe)', caregiver:'Markus Berger'},
      {date:off(-1),time:'09:00', measure:'Atemübungen & Positionierung',     caregiver:'Markus Berger'},
      {date:off(-1),time:'20:10', measure:'Medikamentengabe oral (Abendgabe)',caregiver:'Markus Berger'},
      {date:off(-2),time:'08:00', measure:'Medikamentengabe oral (Frühgabe)', caregiver:'Anna Müller'},
      {date:off(-2),time:'10:00', measure:'Abendpflege / Mundpflege',        caregiver:'Anna Müller'},
      {date:off(-2),time:'14:00', measure:'Mobilisation & Gehtraining',      caregiver:'Anna Müller'},
    ];
  }

  function load(){
    var patId = getCurrentPatId();
    var rows = loadRealEntries();
    if(rows.length === 0 && patId) rows = demoEntries();
    return rows;
  }

  function withinRange(date, range){
    if(range === 'all') return true;
    if(range === 'today') return date === isoToday();
    if(range === 'week'){
      var d = new Date(date + 'T00:00:00');
      var now = new Date();
      var weekAgo = new Date(); weekAgo.setDate(now.getDate()-6); weekAgo.setHours(0,0,0,0);
      return d >= weekAgo && d <= now;
    }
    return true;
  }

  function renderStats(items){
    var today = isoToday();
    var todayCount = items.filter(function(x){ return x.date === today; }).length;
    var days = {};
    items.forEach(function(x){ days[x.date] = true; });
    var sorted = items.slice().sort(function(a,b){
      if(a.date !== b.date) return a.date < b.date ? 1 : -1;
      return a.time < b.time ? 1 : -1;
    });
    var last = sorted[0] ? sorted[0].date.slice(5).replace('-','.') + ' ' + sorted[0].time : '—';

    var elTotal = document.getElementById('dnStatTotal');
    var elToday = document.getElementById('dnStatToday');
    var elDays  = document.getElementById('dnStatDays');
    var elLast  = document.getElementById('dnStatLast');
    if(elTotal) elTotal.textContent = String(items.length);
    if(elToday) elToday.textContent = String(todayCount);
    if(elDays)  elDays.textContent  = String(Object.keys(days).length);
    if(elLast)  elLast.textContent  = last;
  }

  function render(){
    var rangeFilter = document.getElementById('dnRangeFilter');
    var search = document.getElementById('dnSearch');
    var host  = document.getElementById('dnDays');
    var empty = document.getElementById('dnEmpty');
    if(!host) return;

    var range = rangeFilter ? rangeFilter.value : 'week';
    var query = search ? search.value.trim().toLowerCase() : '';

    var items = load().filter(function(x){
      if(!withinRange(x.date, range)) return false;
      if(query){
        var hay = (x.measure + ' ' + x.caregiver).toLowerCase();
        if(hay.indexOf(query) === -1) return false;
      }
      return true;
    });

    renderStats(items);

    items.sort(function(a,b){
      if(a.date !== b.date) return a.date < b.date ? 1 : -1;
      return a.time < b.time ? -1 : 1;
    });

    var groups = {}, order = [];
    items.forEach(function(x){
      if(!groups[x.date]){ groups[x.date]=[]; order.push(x.date); }
      groups[x.date].push(x);
    });

    if(empty) empty.hidden = items.length !== 0;

    host.innerHTML = order.map(function(date){
      var rows = groups[date].map(function(x){
        return '<tr>' +
          '<td data-label="Zeit" style="width:80px;">' + esc(x.time) + '</td>' +
          '<td data-label="Maßnahme"><div class="dn-measure">' + esc(x.measure) + '</div></td>' +
          '<td data-label="Pflegekraft" style="white-space:nowrap;">' +
            cgAvatar(x.caregiver) + ' ' + esc(x.caregiver) +
          '</td>' +
          '<td data-label="Status"><span class="dn-status is-done">Abgezeichnet</span></td>' +
          '</tr>';
      }).join('');
      return '<div class="dn-day">' +
        '<div class="dn-day__head">' +
          '<h3 class="dn-day__title">' + esc(formatDate(date)) + '</h3>' +
          '<span class="muted">' + groups[date].length + ' Maßnahmen</span>' +
        '</div>' +
        '<table class="dn-table">' +
          '<thead><tr><th>Zeit</th><th>Maßnahme</th><th>Pflegekraft</th><th>Status</th></tr></thead>' +
          '<tbody>' + rows + '</tbody>' +
        '</table>' +
        '</div>';
    }).join('');
  }

  /* ── Pflegeplan vom Server laden → lokale Map + dfMeasures-Cache befüllen → neu rendern ── */
  function fetchAndCachePflegeplan(patId, onDone){
    if(!patId) return onDone && onDone();
    fetch('/api/care/pflegeplanung/' + encodeURIComponent(patId), {credentials:'include'})
      .then(function(r){ return r.ok ? r.json() : null; })
      .then(function(d){
        if(!d || !d.ok || !Array.isArray(d.plaene)) return;
        var active = d.plaene.filter(function(p){ return !p.abgesetzt; });
        /* 1. lokale Map direkt befüllen – unabhängig von window.dfMeasures */
        var map = {};
        active.forEach(function(p){ map[String(p.id)] = p.massnahme || ''; });
        _localNameMap[patId] = map;
        /* 2. dfMeasures-Cache aktualisieren (falls auf dieser Seite verfügbar) */
        if(window.dfMeasures){
          var times = window.dfMeasures.times(patId) || [];
          window.dfMeasures.set(patId, {
            total: active.length,
            times: active.length ? times : [],
            names: active.map(function(p){ return {id: p.id, massnahme: p.massnahme || ''}; })
          });
        }
      })
      .catch(function(){})
      .then(function(){ onDone && onDone(); });
  }

  document.addEventListener('DOMContentLoaded', function(){
    render();
    var rf = document.getElementById('dnRangeFilter');
    var s  = document.getElementById('dnSearch');
    var p  = document.getElementById('dnPrint');
    if(rf) rf.addEventListener('change', render);
    if(s)  s.addEventListener('input', render);
    if(p)  p.addEventListener('click', function(){ window.print(); });

    /* Pflegeplan laden, Cache befüllen und Ansicht mit echten Maßnahmen-Namen neu rendern */
    fetchAndCachePflegeplan(getCurrentPatId(), render);

    /* Patient-Wechsel in einem anderen Tab (storage-Event feuert nur in anderen Tabs) */
    window.addEventListener('storage', function(e){
      if(e.key === 'nursy_df_current_pat_id' && e.newValue){
        fetchAndCachePflegeplan(e.newValue, render);
      }
    });

    /* Patient-Wechsel auf derselben Seite via patient-selector.js (CustomEvent) */
    window.addEventListener('nursy:patient-changed', function(e){
      var newId = e.detail && e.detail.patientId;
      if(newId) fetchAndCachePflegeplan(newId, render);
    });
  });
})();
