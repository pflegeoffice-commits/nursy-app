(function(){
  var KEY = 'nursy_invoices_v1_default';
  var currentInvoiceId = null;
  var serverInvoices = [];

  function euro(n){
    return new Intl.NumberFormat('de-AT', { style:'currency', currency:'EUR' }).format(Number(n || 0));
  }

  function formatDate(iso){
    if(!iso) return '—';
    var d = new Date(iso + 'T00:00:00');
    return new Intl.DateTimeFormat('de-AT', { day:'2-digit', month:'2-digit', year:'numeric' }).format(d);
  }

  function statusLabel(status){
    if(status === 'paid') return 'Bezahlt';
    if(status === 'overdue') return 'Überfällig';
    return 'Offen';
  }

  function statusClass(status){
    if(status === 'paid') return 'is-paid';
    if(status === 'overdue') return 'is-overdue';
    return 'is-open';
  }

  function esc(s){
    return String(s == null ? '' : s)
      .replace(/&/g,'&amp;')
      .replace(/</g,'&lt;')
      .replace(/>/g,'&gt;')
      .replace(/"/g,'&quot;')
      .replace(/'/g,'&#39;');
  }

  function seedInvoices(){
    try{
      if(localStorage.getItem(KEY)) return;
      var data = [
        {
          id:'INV-2026-001',
          patient:'Test Klient',
          period:'01.04.2026 – 07.04.2026',
          invoiceDate:'2026-04-08',
          dueDate:'2026-04-22',
          amount:248.00,
          status:'open',
          lines:[
            {label:'Grundpflege', qty:'4 Einsätze', amount:160.00},
            {label:'Medikamentengabe', qty:'4 Einsätze', amount:48.00},
            {label:'Bezugspflege-Zuschlag', qty:'2 Einsätze', amount:40.00}
          ]
        },
        {
          id:'INV-2026-002',
          patient:'Test Klient',
          period:'25.03.2026 – 31.03.2026',
          invoiceDate:'2026-04-01',
          dueDate:'2026-04-15',
          amount:186.00,
          status:'paid',
          lines:[
            {label:'Grundpflege', qty:'3 Einsätze', amount:120.00},
            {label:'Vitalzeichenkontrolle', qty:'3 Einsätze', amount:36.00},
            {label:'Anfahrtspauschale', qty:'3 Einsätze', amount:30.00}
          ]
        },
        {
          id:'INV-2026-003',
          patient:'Test Klient',
          period:'18.03.2026 – 24.03.2026',
          invoiceDate:'2026-03-25',
          dueDate:'2026-04-08',
          amount:322.50,
          status:'overdue',
          lines:[
            {label:'Akutpflege', qty:'5 Einsätze', amount:250.00},
            {label:'Bezugspflege-Zuschlag', qty:'1 Einsatz', amount:22.50},
            {label:'Dokumentation & Übergabe', qty:'5 Einsätze', amount:50.00}
          ]
        }
      ];
      localStorage.setItem(KEY, JSON.stringify(data));
    }catch(e){}
  }

  function loadInvoices(){
    seedInvoices();
    var local;
    try{ local = JSON.parse(localStorage.getItem(KEY) || '[]') || []; }catch(e){ local = []; }
    var localIds = {};
    local.forEach(function(x){ localIds[x.id] = true; });
    var merged = serverInvoices.filter(function(x){ return !localIds[x.id]; });
    return merged.concat(local);
  }

  function fetchServerInvoices(){
    var profile;
    try{ profile = JSON.parse(localStorage.getItem('nursy_profile_client_v1') || '{}'); }catch(e){ profile = {}; }
    var email = (profile.email || '').trim().toLowerCase();
    if(!email) return;
    fetch('/api/nursy/rechnungen-by-email?email=' + encodeURIComponent(email), { credentials: 'include' })
      .then(function(r){ return r.ok ? r.json() : null; })
      .then(function(d){
        if(!d || !d.ok || !Array.isArray(d.rechnungen)) return;
        serverInvoices = d.rechnungen;
        if(serverInvoices.length) renderList();
      })
      .catch(function(){});
  }

  function saveInvoices(items){
    try{ localStorage.setItem(KEY, JSON.stringify(items || [])); }catch(e){}
  }

  function markPaid(id){
    var items = loadInvoices();
    var changed = false;
    items.forEach(function(inv){
      if(inv.id === id && inv.status !== 'paid'){
        inv.status = 'paid';
        changed = true;
      }
    });
    if(changed){
      saveInvoices(items);
      renderList();
      if(currentInvoiceId === id) openModal(id);
    }
  }

  function getInvoice(id){
    return loadInvoices().find(function(inv){ return inv.id === id; }) || null;
  }

  function downloadInvoice(inv){
    if(!inv) return;
    var lines = (inv.lines || []).map(function(line){
      return line.label + ' | ' + line.qty + ' | ' + euro(line.amount);
    }).join('\n');

    var text = [
      'Nursy – Pflege mit Herz',
      'Rechnung: ' + inv.id,
      'Empfänger: ' + inv.patient,
      'Leistungszeitraum: ' + inv.period,
      'Rechnungsdatum: ' + formatDate(inv.invoiceDate),
      'Fällig am: ' + formatDate(inv.dueDate),
      'Status: ' + statusLabel(inv.status),
      '',
      'Positionen:',
      lines,
      '',
      'Gesamtbetrag: ' + euro(inv.amount)
    ].join('\n');

    var blob = new Blob([text], { type:'text/plain;charset=utf-8' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    a.download = inv.id + '.txt';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function renderStats(items){
    var totalCount = document.getElementById('invoiceTotalCount');
    var openAmount = document.getElementById('invoiceOpenAmount');
    var paidAmount = document.getElementById('invoicePaidAmount');

    var openSum = items.filter(function(x){ return x.status === 'open' || x.status === 'overdue'; })
      .reduce(function(sum, x){ return sum + Number(x.amount || 0); }, 0);
    var paidSum = items.filter(function(x){ return x.status === 'paid'; })
      .reduce(function(sum, x){ return sum + Number(x.amount || 0); }, 0);

    if(totalCount) totalCount.textContent = String(items.length);
    if(openAmount) openAmount.textContent = euro(openSum);
    if(paidAmount) paidAmount.textContent = euro(paidSum);
  }

  function renderList(){
    var list = document.getElementById('invoiceList');
    var empty = document.getElementById('invoiceEmpty');
    var statusFilter = document.getElementById('invoiceStatusFilter');
    var search = document.getElementById('invoiceSearch');
    if(!list) return;

    var status = statusFilter ? statusFilter.value : 'all';
    var query = search ? search.value.trim().toLowerCase() : '';

    var items = loadInvoices();
    renderStats(items);

    var filtered = items.filter(function(inv){
      var statusOk = status === 'all' ? true : inv.status === status;
      var searchOk = !query || inv.id.toLowerCase().includes(query);
      return statusOk && searchOk;
    });

    list.innerHTML = '';
    if(empty) empty.hidden = filtered.length !== 0;

    filtered.forEach(function(inv){
      var row = document.createElement('div');
      row.className = 'invoice-row';
      var payBtn = inv.status === 'paid'
        ? ''
        : '<button class="control btn primary" type="button" data-pay-invoice="' + esc(inv.id) + '">Bezahlen</button>';
      row.innerHTML = '' +
        '<div>' +
          '<div class="invoice-title">' + esc(inv.id) + '</div>' +
          '<div class="invoice-sub">Leistungszeitraum: ' + esc(inv.period) + '</div>' +
        '</div>' +
        '<div class="invoice-date">' + esc(formatDate(inv.invoiceDate)) + '</div>' +
        '<div class="invoice-amount">' + esc(euro(inv.amount)) + '</div>' +
        '<div><span class="invoice-status ' + statusClass(inv.status) + '">' + esc(statusLabel(inv.status)) + '</span></div>' +
        '<div class="invoice-actions">' +
          '<button class="control btn" type="button" data-open-invoice="' + esc(inv.id) + '">Details</button>' +
          '<button class="control btn" type="button" data-export-invoice="' + esc(inv.id) + '">Herunterladen</button>' +
          payBtn +
        '</div>';
      list.appendChild(row);
    });
  }

  function openModal(id){
    var modal = document.getElementById('invoiceModal');
    var sub = document.getElementById('invoiceModalSub');
    var body = document.getElementById('invoiceModalBody');
    var payBtn = document.getElementById('invoicePaySingle');
    var inv = getInvoice(id);
    if(!modal || !body || !inv) return;

    currentInvoiceId = id;
    if(sub) sub.textContent = inv.id + ' · ' + statusLabel(inv.status);

    body.innerHTML = '' +
      '<div class="invoice-detail-grid">' +
        '<div class="invoice-detail-box"><strong>Leistungszeitraum</strong><div class="muted" style="margin-top:6px;">' + esc(inv.period) + '</div></div>' +
        '<div class="invoice-detail-box"><strong>Status</strong><div style="margin-top:6px;"><span class="invoice-status ' + statusClass(inv.status) + '">' + esc(statusLabel(inv.status)) + '</span></div></div>' +
        '<div class="invoice-detail-box"><strong>Rechnungsdatum</strong><div class="muted" style="margin-top:6px;">' + esc(formatDate(inv.invoiceDate)) + '</div></div>' +
        '<div class="invoice-detail-box"><strong>Fällig am</strong><div class="muted" style="margin-top:6px;">' + esc(formatDate(inv.dueDate)) + '</div></div>' +
      '</div>' +
      '<div class="invoice-lines">' +
        '<div class="invoice-line--head"><div>Leistung</div><div class="il-menge-col">Menge</div><div>Betrag</div></div>' +
        (inv.lines || []).map(function(line){
          return '<div class="invoice-line"><div>' + esc(line.label) + '<span class="il-qty"> &times; ' + esc(line.qty) + '</span></div><div class="il-menge-col">' + esc(line.qty) + '</div><div>' + esc(euro(line.amount)) + '</div></div>';
        }).join('') +
      '</div>' +
      '<div class="invoice-detail-box"><strong>Gesamtbetrag</strong><div style="font-size:26px; font-weight:900; margin-top:8px;">' + esc(euro(inv.amount)) + '</div></div>';

    if(payBtn){
      if(inv.status === 'paid'){
        payBtn.disabled = true;
        payBtn.textContent = 'Bezahlt';
      } else {
        payBtn.disabled = false;
        payBtn.textContent = 'Jetzt bezahlen';
      }
    }

    modal.hidden = false;
    document.documentElement.classList.add('pp-modal-open');
  }

  function closeModal(){
    var modal = document.getElementById('invoiceModal');
    if(modal) modal.hidden = true;
    document.documentElement.classList.remove('pp-modal-open');
    currentInvoiceId = null;
  }

  function _resolveUserId(){
    return Promise.all([
      fetch('/api/me', {credentials:'include'}).then(function(r){ return r.ok ? r.json() : null; }).catch(function(){ return null; }),
      fetch('/api/billing/me', {credentials:'include'}).then(function(r){ return r.ok ? r.json() : null; }).catch(function(){ return null; })
    ]).then(function(results){
      var me = results[0], bme = results[1];
      if(me && me.id) return me.id;
      if(bme && bme.ok && bme.user && bme.user.id) return bme.user.id;
      return 'default';
    });
  }

  document.addEventListener('DOMContentLoaded', function(){
    _resolveUserId().then(function(uid){
      KEY = 'nursy_invoices_v1_' + uid;
      seedInvoices();
      renderList();
      fetchServerInvoices();

    var statusFilter = document.getElementById('invoiceStatusFilter');
    var search = document.getElementById('invoiceSearch');
    var exportAll = document.getElementById('invoiceExportAll');
    var exportSingle = document.getElementById('invoiceExportSingle');
    var paySingle = document.getElementById('invoicePaySingle');

    if(statusFilter) statusFilter.addEventListener('change', renderList);
    if(search) search.addEventListener('input', renderList);

    document.addEventListener('click', function(e){
      var openBtn = e.target.closest('[data-open-invoice]');
      var exportBtn = e.target.closest('[data-export-invoice]');
      var payBtn = e.target.closest('[data-pay-invoice]');
      var closeBtn = e.target.closest('[data-close-invoice-modal]');

      if(openBtn) openModal(openBtn.getAttribute('data-open-invoice'));
      if(exportBtn) downloadInvoice(getInvoice(exportBtn.getAttribute('data-export-invoice')));
      if(payBtn){
        var id = payBtn.getAttribute('data-pay-invoice');
        if(confirm('Demo: Rechnung ' + id + ' jetzt als bezahlt markieren?')) markPaid(id);
      }
      if(closeBtn) closeModal();
    });

    if(exportAll){
      exportAll.addEventListener('click', function(){
        loadInvoices().forEach(downloadInvoice);
      });
    }

    if(exportSingle){
      exportSingle.addEventListener('click', function(){
        if(currentInvoiceId) downloadInvoice(getInvoice(currentInvoiceId));
      });
    }

    if(paySingle){
      paySingle.addEventListener('click', function(){
        if(!currentInvoiceId) return;
        var inv = getInvoice(currentInvoiceId);
        if(!inv || inv.status === 'paid') return;
        if(confirm('Demo: Rechnung ' + inv.id + ' jetzt als bezahlt markieren?')) markPaid(inv.id);
      });
    }

    document.addEventListener('keydown', function(e){
      if(e.key === 'Escape') closeModal();
    });
    });  /* end _resolveUserId().then */
  });
})();
