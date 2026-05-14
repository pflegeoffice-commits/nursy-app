(function(){

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

  function isoOffset(offsetDays){
    var d = new Date();
    if(offsetDays) d.setDate(d.getDate() + offsetDays);
    return d.getFullYear() + '-' +
      String(d.getMonth()+1).padStart(2,'0') + '-' +
      String(d.getDate()).padStart(2,'0');
  }

  function formatDate(iso){
    if(!iso) return '—';
    var d = new Date(iso + 'T00:00:00');
    return new Intl.DateTimeFormat('de-AT',{weekday:'long',day:'2-digit',month:'2-digit',year:'numeric'}).format(d);
  }

  function shortDate(iso){
    if(!iso) return '—';
    var d = new Date(iso + 'T00:00:00');
    return new Intl.DateTimeFormat('de-AT',{day:'2-digit',month:'2-digit'}).format(d);
  }

  /* ── Aktuellen Patienten-ID ermitteln ── */
  function getCurrentPatId(){
    return localStorage.getItem('nursy_df_current_pat_id') || null;
  }

  /* ── Echte Pflegekraft-Dokumentation laden ── */
  function loadRealEntries(){
    var patId = getCurrentPatId();
    try{
      var all = JSON.parse(localStorage.getItem('nursy_dokumentation_v5') || '[]') || [];
      var filtered = patId
        ? all.filter(function(x){ return String(x.patientId) === String(patId); })
        : all;
      /* Felder normalisieren: real hat 'type'+'group', demo hat 'category'+'author' */
      return filtered.map(function(x){
        return {
          date:     x.date     || '',
          time:     x.time     || '00:00',
          category: x.category || x.type || 'allgemein',
          author:   x.author   || x.group || 'Pflegekraft',
          text:     x.text     || ''
        };
      });
    }catch(e){ return []; }
  }

  /* ── Demo-Fallback ── */
  function demoEntries(){
    var t = isoOffset(0), y = isoOffset(-1), d2 = isoOffset(-2), d3 = isoOffset(-3), d4 = isoOffset(-4);
    return [
      {date:t,  time:'10:30', category:'bericht',  author:'Anna Müller',
       text:'Klient war heute Vormittag aufgeweckt und kooperativ. Körperpflege im Bett gut toleriert. Hautzustand unauffällig.'},
      {date:t,  time:'12:05', category:'vital',    author:'Anna Müller',
       text:'RR 128/82 mmHg, Puls 76/min, Temperatur 36.7 °C, SpO₂ 97%.'},
      {date:t,  time:'14:20', category:'uebergabe',author:'Anna Müller',
       text:'Übergabe an Spätdienst: Mobilisation am Nachmittag noch offen, Schmerzbedarfsmedikation bei Bedarf möglich.'},
      {date:y,  time:'09:15', category:'bericht',  author:'Markus Berger',
       text:'Patient klagte heute über leichte Übelkeit nach Frühstück. Antiemetikum nach Anordnung verabreicht, Beschwerden rückläufig.'},
      {date:y,  time:'12:30', category:'vital',    author:'Markus Berger',
       text:'RR 132/86 mmHg, Puls 80/min, Blutzucker 142 mg/dl postprandial.'},
      {date:y,  time:'20:45', category:'bericht',  author:'Markus Berger',
       text:'Abendmedikation gegeben, Patient ruht. Keine Auffälligkeiten.'},
      {date:d2, time:'08:50', category:'bericht',  author:'Anna Müller',
       text:'Gehübungen mit Rollator durchgeführt, ca. 10 Minuten Flur. Patient war zufrieden, leichte Erschöpfung danach.'},
      {date:d2, time:'15:10', category:'vital',    author:'Anna Müller',
       text:'RR 125/80 mmHg, Puls 72/min.'},
      {date:d3, time:'09:20', category:'bericht',  author:'Markus Berger',
       text:'Wundkontrolle am Unterschenkel: Wundgrund sauber, Verband erneuert. Foto im Akt.'},
      {date:d3, time:'13:00', category:'uebergabe',author:'Markus Berger',
       text:'Übergabe: Verbandwechsel morgen früh wieder eingeplant.'},
      {date:d4, time:'10:00', category:'bericht',  author:'Anna Müller',
       text:'Patient stabil, Stimmung gut. Familie zu Besuch.'}
    ];
  }

  function load(){
    var rows = loadRealEntries();
    if(rows.length === 0) rows = demoEntries();
    return rows;
  }

  function catLabel(c){
    if(c === 'bericht')   return 'Pflegebericht';
    if(c === 'vital')     return 'Vitalzeichen';
    if(c === 'uebergabe') return 'Übergabe';
    if(c === 'allgemein') return 'Allgemein';
    if(c === 'planung')   return 'Pflegeplanung';
    return c || 'Eintrag';
  }
  function catClass(c){
    if(c === 'bericht')   return 'is-bericht';
    if(c === 'vital')     return 'is-vital';
    if(c === 'uebergabe') return 'is-uebergabe';
    if(c === 'allgemein') return 'is-bericht';
    if(c === 'planung')   return 'is-uebergabe';
    return '';
  }

  function withinRange(date, range){
    if(range === 'all') return true;
    if(range === 'today') return date === isoOffset(0);
    if(range === 'week'){
      var d = new Date(date + 'T00:00:00');
      var now = new Date();
      var weekAgo = new Date(); weekAgo.setDate(now.getDate()-6); weekAgo.setHours(0,0,0,0);
      return d >= weekAgo && d <= now;
    }
    return true;
  }

  function renderStats(items){
    var elT = document.getElementById('docStatTotal');
    var elD = document.getElementById('docStatDays');
    var elL = document.getElementById('docStatLast');
    var days = {};
    items.forEach(function(x){ days[x.date] = true; });
    if(elT) elT.textContent = String(items.length);
    if(elD) elD.textContent = String(Object.keys(days).length);
    if(elL){
      var sorted = items.slice().sort(function(a,b){
        if(a.date !== b.date) return a.date < b.date ? 1 : -1;
        return a.time < b.time ? 1 : -1;
      });
      elL.textContent = sorted[0] ? (shortDate(sorted[0].date) + ' ' + sorted[0].time) : '—';
    }
  }

  function render(){
    var rangeFilter = document.getElementById('docRangeFilter');
    var catFilter   = document.getElementById('docCatFilter');
    var search      = document.getElementById('docSearch');
    var host        = document.getElementById('docDays');
    var empty       = document.getElementById('docEmpty');
    if(!host) return;

    var range = rangeFilter ? rangeFilter.value : 'week';
    var cat   = catFilter   ? catFilter.value   : 'all';
    var query = search ? search.value.trim().toLowerCase() : '';

    var items = load().filter(function(x){
      if(!withinRange(x.date, range)) return false;
      if(cat !== 'all' && x.category !== cat) return false;
      if(query){
        var hay = ((x.text||'') + ' ' + (x.author||'') + ' ' + catLabel(x.category)).toLowerCase();
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
      var entries = groups[date].map(function(x){
        return '<div class="doc-entry">' +
          '<div class="doc-time">' + esc(x.time) +
            '<div class="doc-author" style="display:flex;align-items:center;gap:5px;margin-top:3px;">' +
              cgAvatar(x.author) +
              '<span>' + esc(x.author) + '</span>' +
            '</div>' +
          '</div>' +
          '<div>' +
            '<span class="doc-cat ' + catClass(x.category) + '">' + esc(catLabel(x.category)) + '</span>' +
            '<div class="doc-text">' + esc(x.text) + '</div>' +
          '</div>' +
          '</div>';
      }).join('');
      return '<div class="doc-day">' +
        '<div class="doc-day__head">' +
          '<h3 class="doc-day__title">' + esc(formatDate(date)) + '</h3>' +
          '<span class="muted">' + groups[date].length + ' Einträge</span>' +
        '</div>' +
        entries +
        '</div>';
    }).join('');
  }

  document.addEventListener('DOMContentLoaded', function(){
    render();
    var rf = document.getElementById('docRangeFilter');
    var cf = document.getElementById('docCatFilter');
    var s  = document.getElementById('docSearch');
    var p  = document.getElementById('docPrint');
    if(rf) rf.addEventListener('change', render);
    if(cf) cf.addEventListener('change', render);
    if(s)  s.addEventListener('input', render);
    if(p)  p.addEventListener('click', function(){ window.print(); });
  });
})();
