(function(){
  var KEY = 'nursy_client_caregivers_v1';
  var currentId = null;

  function esc(s){
    return String(s == null ? '' : s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
  }

  function initials(name){
    var parts = String(name || '').trim().split(/\s+/).filter(Boolean);
    if(!parts.length) return '?';
    var s = parts[0][0] + (parts.length > 1 ? parts[parts.length-1][0] : '');
    return s.toUpperCase();
  }

  function seed(){
    try{
      var existing = JSON.parse(localStorage.getItem(KEY) || 'null');
      /* Migration: gender-Feld nachträglich eintragen wenn noch fehlt */
      if(existing && Array.isArray(existing) && existing.some(function(x){ return !x.gender; })){
        localStorage.removeItem(KEY);
      }
      if(localStorage.getItem(KEY)) return;
      var data = [
        {
          id:'cg1', name:'Anna Müller', gender:'f', qualification:'DGKP',
          city:'4040 Linz', phone:'+43 660 1234567', email:'anna.mueller@nursy.demo',
          status:'active', since:'2025-09-12',
          tags:['Wundmanagement','Mobilisation'],
          nextVisit:'Heute 14:00 – 16:00',
          services:'Körperpflege, Mobilisation, Medikamentengabe',
          note:'Bezugspflegekraft – Hauptansprechperson.'
        },
        {
          id:'cg2', name:'Markus Berger', gender:'m', qualification:'PFA',
          city:'4040 Linz', phone:'+43 676 9876543', email:'markus.berger@nursy.demo',
          status:'active', since:'2026-01-08',
          tags:['Medikamentengabe','Vitalzeichen'],
          nextVisit:'Morgen 09:00 – 10:30',
          services:'Medikamentengabe, Vitalzeichenkontrolle',
          note:'Vertretung bei Frühdiensten.'
        },
        {
          id:'cg3', name:'Sophie Lechner', gender:'f', qualification:'PA',
          city:'4020 Linz', phone:'+43 699 5550123', email:'sophie.lechner@nursy.demo',
          status:'paused', since:'2025-11-03',
          tags:['Hauswirtschaft','Begleitung'],
          nextVisit:'—',
          services:'Hauswirtschaftliche Hilfe, Begleitdienste',
          note:'Aktuell pausiert – verfügbar ab Mai.'
        }
      ];
      localStorage.setItem(KEY, JSON.stringify(data));
    }catch(e){}
  }

  function load(){
    seed();
    try{ return JSON.parse(localStorage.getItem(KEY) || '[]') || []; }
    catch(e){ return []; }
  }

  function get(id){
    return load().find(function(c){ return c.id === id; }) || null;
  }

  function statusLabel(s){ return s === 'paused' ? 'Pausiert' : 'Aktiv'; }
  function statusClass(s){ return s === 'paused' ? 'is-paused' : 'is-active'; }

  function renderStats(items){
    var total = document.getElementById('cgStatTotal');
    var active = document.getElementById('cgStatActive');
    var next = document.getElementById('cgStatNext');
    if(total) total.textContent = String(items.length);
    if(active) active.textContent = String(items.filter(function(x){ return x.status === 'active'; }).length);
    if(next){
      var upcoming = items.find(function(x){ return x.status === 'active' && x.nextVisit && x.nextVisit !== '—'; });
      next.textContent = upcoming ? upcoming.nextVisit : '—';
    }
  }

  function renderList(){
    var list = document.getElementById('cgList');
    var empty = document.getElementById('cgEmpty');
    var statusFilter = document.getElementById('cgStatusFilter');
    var search = document.getElementById('cgSearch');
    if(!list) return;

    var status = statusFilter ? statusFilter.value : 'all';
    var query = search ? search.value.trim().toLowerCase() : '';

    var items = load();
    renderStats(items);

    var filtered = items.filter(function(c){
      var statusOk = status === 'all' ? true : c.status === status;
      var hay = (c.name + ' ' + c.qualification + ' ' + (c.tags || []).join(' ')).toLowerCase();
      var searchOk = !query || hay.indexOf(query) !== -1;
      return statusOk && searchOk;
    });

    list.innerHTML = '';
    if(empty) empty.hidden = filtered.length !== 0;

    filtered.forEach(function(c){
      var card = document.createElement('div');
      card.className = 'cg-card';
      var tags = (c.tags || []).map(function(t){ return '<span class="cg-tag">' + esc(t) + '</span>'; }).join('');
      var gCls = c.gender === 'f' ? ' cg-avatar--f' : c.gender === 'm' ? ' cg-avatar--m' : '';
      card.innerHTML = '' +
        '<div class="cg-avatar' + gCls + '" aria-hidden="true">' + esc(initials(c.name)) + '</div>' +
        '<div>' +
          '<div class="cg-name">' + esc(c.name) +
            ' <span class="cg-status ' + statusClass(c.status) + '" style="margin-left:8px;">' + esc(statusLabel(c.status)) + '</span>' +
          '</div>' +
          '<div class="cg-meta">' +
            '<span>' + esc(c.qualification) + '</span>' +
            '<span class="sep">·</span>' +
            '<span>' + esc(c.city) + '</span>' +
            '<span class="sep">·</span>' +
            '<span>Nächster Termin: ' + esc(c.nextVisit || '—') + '</span>' +
          '</div>' +
          (tags ? '<div class="cg-tags">' + tags + '</div>' : '') +
        '</div>' +
        '<div class="cg-actions-row">' +
          '<button class="control btn" type="button" data-open-cg="' + esc(c.id) + '">Details</button>' +
          '<button class="control btn" type="button" data-call-cg="' + esc(c.id) + '">Anrufen</button>' +
          '<button class="control btn primary" type="button" data-msg-cg="' + esc(c.id) + '">Nachricht</button>' +
        '</div>';
      list.appendChild(card);
    });
  }

  function openModal(id){
    var modal = document.getElementById('cgModal');
    var title = document.getElementById('cgModalTitle');
    var sub = document.getElementById('cgModalSub');
    var body = document.getElementById('cgModalBody');
    var c = get(id);
    if(!modal || !body || !c) return;

    currentId = id;
    if(title) title.textContent = c.name;
    if(sub) sub.textContent = c.qualification + ' · ' + statusLabel(c.status);

    body.innerHTML = '' +
      '<div class="cg-detail-grid">' +
        '<div class="cg-detail-box"><strong>Telefon</strong><div class="muted" style="margin-top:6px;">' + esc(c.phone || '—') + '</div></div>' +
        '<div class="cg-detail-box"><strong>E-Mail</strong><div class="muted" style="margin-top:6px;">' + esc(c.email || '—') + '</div></div>' +
        '<div class="cg-detail-box"><strong>Standort</strong><div class="muted" style="margin-top:6px;">' + esc(c.city || '—') + '</div></div>' +
        '<div class="cg-detail-box"><strong>Im Team seit</strong><div class="muted" style="margin-top:6px;">' + esc(c.since || '—') + '</div></div>' +
      '</div>' +
      '<div class="cg-detail-box"><strong>Leistungen</strong><div class="muted" style="margin-top:6px;">' + esc(c.services || '—') + '</div></div>' +
      '<div class="cg-detail-box"><strong>Nächster Termin</strong><div style="margin-top:6px; font-weight:800;">' + esc(c.nextVisit || '—') + '</div></div>' +
      (c.note ? '<div class="cg-detail-box"><strong>Notiz</strong><div class="muted" style="margin-top:6px;">' + esc(c.note) + '</div></div>' : '');

    modal.hidden = false;
    document.documentElement.classList.add('pp-modal-open');
  }

  function closeModal(){
    var modal = document.getElementById('cgModal');
    if(modal) modal.hidden = true;
    document.documentElement.classList.remove('pp-modal-open');
    currentId = null;
  }

  document.addEventListener('DOMContentLoaded', function(){
    seed();
    renderList();

    var statusFilter = document.getElementById('cgStatusFilter');
    var search = document.getElementById('cgSearch');
    if(statusFilter) statusFilter.addEventListener('change', renderList);
    if(search) search.addEventListener('input', renderList);

    document.addEventListener('click', function(e){
      var openBtn = e.target.closest('[data-open-cg]');
      var callBtn = e.target.closest('[data-call-cg]');
      var msgBtn = e.target.closest('[data-msg-cg]');
      var closeBtn = e.target.closest('[data-close-cg-modal]');

      if(openBtn) openModal(openBtn.getAttribute('data-open-cg'));
      if(callBtn){
        var c1 = get(callBtn.getAttribute('data-call-cg'));
        if(c1) alert('Demo: Anruf an ' + c1.name + ' (' + (c1.phone || '—') + ')');
      }
      if(msgBtn){
        var c2 = get(msgBtn.getAttribute('data-msg-cg'));
        if(c2) alert('Demo: Nachricht an ' + c2.name + ' senden.');
      }
      if(closeBtn) closeModal();
    });

    var contactBtn = document.getElementById('cgModalContact');
    if(contactBtn){
      contactBtn.addEventListener('click', function(){
        if(!currentId) return;
        var c = get(currentId);
        if(c) alert('Demo: Nachricht an ' + c.name + ' senden.');
      });
    }

    document.addEventListener('keydown', function(e){
      if(e.key === 'Escape') closeModal();
    });
  });
})();
