(function(){

  /* ── Maßnahmen (gleiche Tabelle wie beim Pfleger) ── */
  var MEASURES = [
    {id:1,  massnahme:'Ganzkörperpflege / Körperpflege'},
    {id:2,  massnahme:'Atemübungen & Positionierung'},
    {id:3,  massnahme:'Medikamentengabe oral (Frühgabe)'},
    {id:4,  massnahme:'Blutdruck- & Pulskontrolle'},
    {id:5,  massnahme:'Trinkplan – Erinnerung (Früh)'},
    {id:6,  massnahme:'Mobilisation & Gehtraining'},
    {id:7,  massnahme:'Lagerungswechsel'},
    {id:8,  massnahme:'Wundversorgung / Verbandswechsel'},
    {id:9,  massnahme:'Trinkplan – Erinnerung (Mittag)'},
    {id:10, massnahme:'Mittagsmedikation'},
    {id:11, massnahme:'Ernährungsprotokoll / Zwischenmahlzeit'},
    {id:12, massnahme:'Lagerungswechsel'},
    {id:13, massnahme:'Stuhlgang-/Ausscheidungskontrolle'},
    {id:14, massnahme:'Sturzprophylaxe (Rundgang)'},
    {id:15, massnahme:'Trinkplan – Erinnerung (Abend)'},
    {id:16, massnahme:'Medikamentengabe oral (Abendgabe)'},
    {id:17, massnahme:'Abendpflege / Mundpflege'},
    {id:18, massnahme:'Lagerungswechsel'},
    {id:19, massnahme:'Schlafförderung / Nachtruhe'},
    {id:20, massnahme:'Sicherheitscheck / Bettgitter'},
  ];

  function measureName(id){
    var m = MEASURES.filter(function(x){ return String(x.id) === String(id); })[0];
    return m ? m.massnahme : 'Maßnahme ' + id;
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
        rows.push({date:today, time:signed.time, measure:measureName(taskId), caregiver:signed.name||'Pflegekraft'});
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
          rows.push({date:date, time:signed.time, measure:measureName(taskId), caregiver:signed.name||'Pflegekraft'});
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

  document.addEventListener('DOMContentLoaded', function(){
    render();
    var rf = document.getElementById('dnRangeFilter');
    var s  = document.getElementById('dnSearch');
    var p  = document.getElementById('dnPrint');
    if(rf) rf.addEventListener('change', render);
    if(s)  s.addEventListener('input', render);
    if(p)  p.addEventListener('click', function(){ window.print(); });
  });
})();
