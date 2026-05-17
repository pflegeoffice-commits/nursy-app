(function(){
  var KEY = 'nursy_invoices_v1';
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

  function esc(s){
    return String(s == null ? '' : s)
      .replace(/&/g,'&amp;')
      .replace(/</g,'&lt;')
      .replace(/>/g,'&gt;')
      .replace(/"/g,'&quot;')
      .replace(/'/g,'&#39;');
  }

  function seedInvoices(){ /* Demo-Rechnungen entfernt */ }

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
    fetch('/api/my/rechnungen', { credentials: 'include' })
      .then(function(r){ return r.ok ? r.json() : null; })
      .then(function(d){
        if(!d || !d.ok || !Array.isArray(d.rechnungen)) return;
        serverInvoices = d.rechnungen;
        if(serverInvoices.length) renderList();
      })
      .catch(function(){});
  }

  function saveInvoices(items){
    try{
      localStorage.setItem(KEY, JSON.stringify(items || []));
    }catch(e){}
  }

  function updateInvoiceStatus(id, status){
    var items = loadInvoices();
    var changed = false;
    items.forEach(function(inv){
      if(inv.id === id){
        inv.status = status;
        changed = true;
      }
    });
    if(changed){
      saveInvoices(items);
      renderList();
      if(currentInvoiceId === id){
        openModal(id);
      }
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
      'Patient: ' + inv.patient,
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
      var searchOk = !query || inv.id.toLowerCase().includes(query) || inv.patient.toLowerCase().includes(query);
      return statusOk && searchOk;
    });

    list.innerHTML = '';
    if(empty) empty.hidden = filtered.length !== 0;

    filtered.forEach(function(inv){
      var row = document.createElement('div');
      row.className = 'invoice-row';
      row.innerHTML = '' +
        '<div>' +
          '<div class="invoice-title">' + esc(inv.id) + '</div>' +
          '<div class="invoice-sub">' + esc(inv.patient) + ' · ' + esc(inv.period) + '</div>' +
        '</div>' +
        '<div class="invoice-date">' + esc(formatDate(inv.invoiceDate)) + '</div>' +
        '<div class="invoice-amount">' + esc(euro(inv.amount)) + '</div>' +
        '<div><select class="invoice-status-select" data-status-invoice="' + esc(inv.id) + '" aria-label="Status ändern">' +
          '<option value="open"' + (inv.status === 'open' ? ' selected' : '') + '>Offen</option>' +
          '<option value="paid"' + (inv.status === 'paid' ? ' selected' : '') + '>Bezahlt</option>' +
          '<option value="overdue"' + (inv.status === 'overdue' ? ' selected' : '') + '>Überfällig</option>' +
        '</select></div>' +
        '<div class="invoice-actions">' +
          '<button class="control btn" type="button" data-open-invoice="' + esc(inv.id) + '">Öffnen</button>' +
          '<button class="control btn primary" type="button" data-export-invoice="' + esc(inv.id) + '">Export</button>' +
        '</div>';
      list.appendChild(row);
    });
  }

  function openModal(id){
    var modal = document.getElementById('invoiceModal');
    var sub = document.getElementById('invoiceModalSub');
    var body = document.getElementById('invoiceModalBody');
    var inv = getInvoice(id);
    if(!modal || !body || !inv) return;

    currentInvoiceId = id;
    if(sub) sub.textContent = inv.patient + ' · ' + inv.id;

    body.innerHTML = '' +
      '<div class="invoice-detail-grid">' +
        '<div class="invoice-detail-box"><strong>Leistungszeitraum</strong><div class="muted" style="margin-top:6px;">' + esc(inv.period) + '</div></div>' +
        '<div class="invoice-detail-box"><strong>Status</strong><div style="margin-top:6px;">' +
          '<select class="invoice-status-select" data-status-invoice="' + esc(inv.id) + '" aria-label="Status ändern">' +
            '<option value="open"' + (inv.status === 'open' ? ' selected' : '') + '>Offen</option>' +
            '<option value="paid"' + (inv.status === 'paid' ? ' selected' : '') + '>Bezahlt</option>' +
            '<option value="overdue"' + (inv.status === 'overdue' ? ' selected' : '') + '>Überfällig</option>' +
          '</select>' +
        '</div></div>' +
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

    modal.hidden = false;
    document.documentElement.classList.add('pp-modal-open');
  }

  function closeModal(){
    var modal = document.getElementById('invoiceModal');
    if(modal) modal.hidden = true;
    document.documentElement.classList.remove('pp-modal-open');
    currentInvoiceId = null;
  }

  document.addEventListener('DOMContentLoaded', function(){
    seedInvoices();
    renderList();
    fetchServerInvoices();

    var statusFilter = document.getElementById('invoiceStatusFilter');
    var search = document.getElementById('invoiceSearch');
    var exportAll = document.getElementById('invoiceExportAll');
    var exportSingle = document.getElementById('invoiceExportSingle');

    if(statusFilter) statusFilter.addEventListener('change', renderList);
    if(search) search.addEventListener('input', renderList);

    document.addEventListener('click', function(e){
      var openBtn = e.target.closest('[data-open-invoice]');
      var exportBtn = e.target.closest('[data-export-invoice]');
      var closeBtn = e.target.closest('[data-close-invoice-modal]');

      if(openBtn){
        openModal(openBtn.getAttribute('data-open-invoice'));
      }
      if(exportBtn){
        downloadInvoice(getInvoice(exportBtn.getAttribute('data-export-invoice')));
      }
      if(closeBtn){
        closeModal();
      }
    });

    document.addEventListener('change', function(e){
      var statusSelect = e.target.closest('[data-status-invoice]');
      if(statusSelect){
        updateInvoiceStatus(statusSelect.getAttribute('data-status-invoice'), statusSelect.value);
      }
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

    document.addEventListener('keydown', function(e){
      if(e.key === 'Escape') closeModal();
    });
  });
})();
