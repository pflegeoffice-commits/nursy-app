(function(){
  let PRICE_KEY;

  const DEFAULT_PRICE_LIST = [
    { service: 'Grundpflege Hausbesuch', category: 'Pflege', unit: 'Einsatz', price: 68.00, tax: 0 },
    { service: 'Bezugspflege-Zuschlag', category: 'Zuschlag', unit: 'Einsatz', price: 22.50, tax: 0 },
    { service: 'Wundversorgung', category: 'Pflege', unit: 'Leistung', price: 35.00, tax: 0 },
    { service: 'Physiotherapie zuhause', category: 'Physiotherapie', unit: 'Einheit', price: 82.00, tax: 20 },
    { service: 'Fahrtkosten', category: 'Fahrtkosten', unit: 'km', price: 0.72, tax: 20 }
  ];

  let state = {
    priceList: []
  };

  document.addEventListener('DOMContentLoaded', init);

  async function _resolveUserId() {
    try {
      const r = await fetch('/api/billing/me', { credentials: 'include' });
      if (r.ok) { const d = await r.json(); if (d.ok && d.user && d.user.id) return d.user.id; }
    } catch(e) {}
    try {
      const r2 = await fetch('/api/me', { credentials: 'include' });
      if (r2.ok) { const d2 = await r2.json(); if (d2.id) return d2.id; }
    } catch(e) {}
    return 'default';
  }

  async function init(){
    const uid = await _resolveUserId();
    PRICE_KEY = 'nursy_price_list_v1_' + uid;
    state.priceList = sanitize(readJSON(PRICE_KEY, null) || DEFAULT_PRICE_LIST.slice());
    cacheEls();
    bindEvents();
    renderTable();
    renderPreview();
  }

  function cacheEls(){
    state.els = {
      body: document.getElementById('plBody'),
      preview: document.getElementById('plPreview'),
      addRow: document.getElementById('plAddRow'),
      loadDemo: document.getElementById('plLoadDemo'),
      reset: document.getElementById('plReset'),
      saveTop: document.getElementById('plSaveTop')
    };
  }

  function bindEvents(){
    if (state.els.addRow){
      state.els.addRow.addEventListener('click', function(){
        state.priceList.push({ service:'', category:'Pflege', unit:'Einsatz', price:0, tax:0 });
        renderTable();
        renderPreview();
      });
    }
    if (state.els.loadDemo){
      state.els.loadDemo.addEventListener('click', function(){
        state.priceList = sanitize(DEFAULT_PRICE_LIST.slice());
        renderTable();
        renderPreview();
      });
    }
    if (state.els.reset){
      state.els.reset.addEventListener('click', function(){
        state.priceList = [];
        renderTable();
        renderPreview();
      });
    }
    if (state.els.saveTop){
      state.els.saveTop.addEventListener('click', saveAll);
    }
  }

  function renderTable(){
    const body = state.els.body;
    if (!body) return;
    body.innerHTML = '';

    if (!state.priceList.length){
      const tr = document.createElement('tr');
      tr.innerHTML = '<td colspan="6"><div class="pl-empty">Noch keine Preispositionen vorhanden.</div></td>';
      body.appendChild(tr);
      return;
    }

    state.priceList.forEach((item, index) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><input class="pl-mini-input" data-field="service" data-index="${index}" type="text" value="${escAttr(item.service)}" placeholder="Leistung" /></td>
        <td>
          <select class="pl-mini-select" data-field="category" data-index="${index}">
            ${categoryOptions(item.category)}
          </select>
        </td>
        <td><input class="pl-mini-input" data-field="unit" data-index="${index}" type="text" value="${escAttr(item.unit)}" placeholder="Einheit" /></td>
        <td><input class="pl-mini-input" data-field="price" data-index="${index}" type="number" min="0" step="0.01" value="${Number(item.price || 0)}" /></td>
        <td><input class="pl-mini-input" data-field="tax" data-index="${index}" type="number" min="0" step="0.1" value="${Number(item.tax || 0)}" /></td>
        <td><button class="control btn" type="button" data-remove="${index}">Entfernen</button></td>
      `;
      body.appendChild(tr);
    });

    body.querySelectorAll('[data-index]').forEach((el) => {
      el.addEventListener('input', handleChange);
      el.addEventListener('change', handleChange);
    });
    body.querySelectorAll('[data-remove]').forEach((btn) => {
      btn.addEventListener('click', function(){
        const idx = Number(btn.getAttribute('data-remove'));
        state.priceList.splice(idx, 1);
        renderTable();
        renderPreview();
      });
    });
  }

  function handleChange(e){
    const el = e.target;
    const idx = Number(el.getAttribute('data-index'));
    const field = el.getAttribute('data-field');
    if (!state.priceList[idx] || !field) return;

    state.priceList[idx][field] = (field === 'price' || field === 'tax')
      ? Number(el.value || 0)
      : el.value;

    renderPreview();
  }

  function renderPreview(){
    const wrap = state.els.preview;
    if (!wrap) return;
    wrap.innerHTML = '';

    if (!state.priceList.length){
      wrap.innerHTML = '<div class="pl-empty">Noch keine Preispositionen angelegt.</div>';
      return;
    }

    state.priceList.forEach((item) => {
      const row = document.createElement('div');
      row.className = 'pl-preview-item';
      row.innerHTML = `
        <div>
          <strong>${esc(item.service || 'Leistung')}</strong>
          <span>${esc(item.category || 'Kategorie')} · ${esc(item.unit || 'Einheit')} · Steuer ${Number(item.tax || 0)}%</span>
        </div>
        <div><strong>${formatCurrency(item.price)}</strong></div>
      `;
      wrap.appendChild(row);
    });
  }

  function saveAll(){
    localStorage.setItem(PRICE_KEY, JSON.stringify(sanitize(state.priceList)));
    _showSaveBanner('Preisliste gespeichert.');
  }

  function categoryOptions(selected){
    const list = ['Pflege', 'Physiotherapie', 'Zuschlag', 'Fahrtkosten', 'Beratung', 'Sonstiges'];
    return list.map((item) => {
      const isSelected = String(item) === String(selected || 'Pflege') ? 'selected' : '';
      return `<option ${isSelected}>${esc(item)}</option>`;
    }).join('');
  }

  function sanitize(list){
    return (list || []).map((item) => ({
      service: String(item.service || ''),
      category: String(item.category || 'Pflege'),
      unit: String(item.unit || 'Einheit'),
      price: Number(item.price || 0),
      tax: Number(item.tax || 0)
    }));
  }

  function formatCurrency(value){
    return new Intl.NumberFormat('de-AT', { style:'currency', currency:'EUR' }).format(Number(value || 0));
  }

  function readJSON(key, fallback){
    try{
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    }catch(e){
      return fallback;
    }
  }

  function esc(value){
    return String(value == null ? '' : value)
      .replace(/&/g,'&amp;')
      .replace(/</g,'&lt;')
      .replace(/>/g,'&gt;')
      .replace(/"/g,'&quot;')
      .replace(/'/g,'&#39;');
  }

  function escAttr(value){
    return esc(value);
  }

  function _showSaveBanner(msg){
    let el = document.getElementById('_nursySaveBanner');
    if (!el){
      el = document.createElement('div');
      el.id = '_nursySaveBanner';
      el.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#1a3a6b;color:#fff;padding:10px 22px;border-radius:12px;font-size:14px;font-weight:600;box-shadow:0 4px 20px rgba(0,0,0,.22);z-index:9999;pointer-events:none;transition:opacity .3s';
      document.body.appendChild(el);
    }
    el.textContent = msg;
    el.style.opacity = '1';
    clearTimeout(el._t);
    el._t = setTimeout(() => { el.style.opacity = '0'; }, 2400);
  }
})();
