(function(){
  let TEMPLATE_KEY, PRICE_KEY, LOGO_KEY, SERVICE_KEY, GENERATED_KEY;
  const PROFILE_KEY = 'nursy_profile_care_v1';
  const PATIENT_KEYS = ['nursy_patients_v1', 'nursy_demo_patients_v1', 'NURSY_DEMO_PATIENTS', 'patients', 'PATIENTS'];

  const DEFAULT_TEMPLATE = {
    providerName: 'Nursy Mobile Pflege',
    providerSubline: 'Pflege · Physio · Betreuung zuhause',
    companyBlock: 'Musterstraße 1\n4020 Linz\n+43 000 000000 · office@nursy.at',
    accent: '#3f6fe8',
    dueDays: 14,
    logoPosition: 'left',
    invoiceDate: isoToday(),
    invoiceNumber: createInvoiceNumber(),
    taxRate: 0,
    patientId: '',
    patientName: '',
    patientAddress: '',
    intro: 'Vielen Dank für Ihr Vertrauen. Für die im untenstehenden Zeitraum erbrachten Leistungen erlauben wir uns folgende Rechnung zu stellen.',
    paymentHint: 'Bitte überweisen Sie den Betrag binnen 14 Tagen spesenfrei auf das unten angeführte Konto.',
    bankBlock: 'IBAN AT00 0000 0000 0000 0000\nBIC NURSATWW\nKontoinhaber: Nursy Mobile Pflege',
    bankAlign: 'left',
    taxNumber: '',
    registryNumber: '',
    uidNumber: ''
  };

  const DEFAULT_PRICE_LIST = [
    { service: 'Grundpflege Hausbesuch', unit: 'Einsatz', price: 68.00, tax: 0 },
    { service: 'Bezugspflege-Zuschlag', unit: 'Einsatz', price: 22.50, tax: 0 },
    { service: 'Wundversorgung', unit: 'Leistung', price: 35.00, tax: 0 },
    { service: 'Physiotherapie zuhause', unit: 'Einheit', price: 82.00, tax: 20 },
    { service: 'Fahrtkosten', unit: 'km', price: 0.72, tax: 20 }
  ];

  const DEFAULT_SERVICES = [];

  let state = {
    template: null,
    priceList: [],
    services: [],
    selectedPatientId: '',
    selectedPatientName: '',
    selectedPatientAddress: '',
    logo: '',
    patients: []
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
    TEMPLATE_KEY  = 'nursy_invoice_template_v1_'  + uid;
    PRICE_KEY     = 'nursy_price_list_v1_'         + uid;
    LOGO_KEY      = 'nursy_invoice_logo_v1_'       + uid;
    SERVICE_KEY   = 'nursy_service_records_v1_'    + uid;
    GENERATED_KEY = 'nursy_generated_invoice_drafts_v1_' + uid;

    state.template = Object.assign({}, DEFAULT_TEMPLATE, readJSON(TEMPLATE_KEY, {}) || {});
    state.priceList = sanitizePriceList(readJSON(PRICE_KEY, null) || DEFAULT_PRICE_LIST.slice());
    state.logo = safeGet(LOGO_KEY) || '';
    state.patients = buildPatients();
    state.services = readJSON(SERVICE_KEY, null) || [];

    ensureProviderFromProfile();
    cacheEls();
    bindEvents();
    fillTemplateInputs();
    renderPatientOptions();
    renderPriceList();
    if (!state.services.length) setServiceHint('Noch keine Leistungen gefunden. Du kannst Demo-Leistungen laden oder später den echten Durchführungsnachweis anbinden.');
    syncPatientFromSelection();
    renderServiceLines();
    renderPreview();
    refreshLogoPositionChips();
  }

  function cacheEls(){
    state.els = {
      providerName: byId('invoiceProviderName'),
      providerSubline: byId('invoiceProviderSubline'),
      companyBlock: byId('invoiceCompanyBlock'),
      accent: byId('invoiceAccent'),
      dueDays: byId('invoiceDueDays'),
      patientSelect: byId('invoicePatientSelect'),
      invoiceDate: byId('invoiceDate'),
      invoiceNumber: byId('invoiceNumber'),
      taxRate: byId('invoiceTax'),
      uidNumber: byId('invoiceUID'),
      taxNumber: byId('invoiceTaxNumber'),
      registryNumber: byId('invoiceRegistryNumber'),
      address: byId('invoiceAddress'),
      intro: byId('invoiceIntro'),
      paymentHint: byId('invoicePaymentHint'),
      bankBlock: byId('invoiceBankBlock'),
      bankAlign: byId('invoiceBankAlign'),
      logoInput: byId('invoiceLogoInput'),
      removeLogo: byId('removeInvoiceLogo'),
      priceListBody: byId('priceListBody'),
      serviceLinesBody: byId('serviceLinesBody'),
      previewBrand: byId('previewBrand'),
      previewLogo: byId('previewLogo'),
      previewProviderName: byId('previewProviderName'),
      previewProviderSubline: byId('previewProviderSubline'),
      previewCompanyBlock: byId('previewCompanyBlock'),
      previewLegalBlock: byId('previewLegalBlock'),
      previewAddress: byId('previewAddress'),
      previewInvoiceNumber: byId('previewInvoiceNumber'),
      previewInvoiceDate: byId('previewInvoiceDate'),
      previewInvoiceDue: byId('previewInvoiceDue'),
      previewTaxNumber: byId('previewTaxNumber'),
      previewRegistryNumber: byId('previewRegistryNumber'),
      previewTaxNumberWrap: byId('previewTaxNumberWrap'),
      previewRegistryNumberWrap: byId('previewRegistryNumberWrap'),
      previewIntro: byId('previewIntro'),
      previewLinesBody: byId('previewLinesBody'),
      previewSubtotal: byId('previewSubtotal'),
      previewTax: byId('previewTax'),
      previewTotal: byId('previewTotal'),
      previewPaymentHint: byId('previewPaymentHint'),
      previewBankBlock: byId('previewBankBlock'),
      previewBankFooter: byId('previewBankFooter'),
      invoicePreview: byId('invoicePreview'),
      importServices: byId('importServices'),
      loadDemoServices: byId('loadDemoServices'),
      addPriceRow: byId('addPriceRow'),
      resetPriceList: byId('resetPriceList'),
      saveInvoiceTemplate: byId('saveInvoiceTemplate'),
      printInvoice: byId('printInvoice'),
      serviceHint: byId('serviceHint'),
      logoPositionGroup: byId('logoPositionGroup')
    };
  }

  function bindEvents(){
    [
      'providerName','providerSubline','companyBlock','accent','dueDays','invoiceDate','invoiceNumber','taxRate','uidNumber','taxNumber','registryNumber','address','intro','paymentHint','bankBlock','bankAlign'
    ].forEach((key) => {
      const el = state.els[key];
      if (!el) return;
      el.addEventListener('input', () => {
        mapInputToTemplate(key, el.value);
        if (key === 'invoiceDate' || key === 'dueDays') updateDueDate();
        renderPreview();
      });
    });

    if (state.els.patientSelect){
      state.els.patientSelect.addEventListener('change', () => {
        state.template.patientId = state.els.patientSelect.value || '';
        syncPatientFromSelection();
        renderServiceLines();
        renderPreview();
      });
    }

    document.querySelectorAll('input[name="logoPosition"]').forEach((radio) => {
      radio.addEventListener('change', () => {
        if (!radio.checked) return;
        state.template.logoPosition = radio.value;
        refreshLogoPositionChips();
        renderPreview();
      });
    });

    if (state.els.logoInput){
      state.els.logoInput.addEventListener('change', handleLogoUpload);
    }
    if (state.els.removeLogo){
      state.els.removeLogo.addEventListener('click', () => {
        state.logo = '';
        safeSet(LOGO_KEY, '');
        if (state.els.logoInput) state.els.logoInput.value = '';
        renderPreview();
      });
    }
    if (state.els.addPriceRow){
      state.els.addPriceRow.addEventListener('click', () => {
        state.priceList.push({ service:'', unit:'Einsatz', price:0, tax:0 });
        renderPriceList();
      });
    }
    if (state.els.resetPriceList){
      state.els.resetPriceList.addEventListener('click', () => {
        state.priceList = sanitizePriceList(DEFAULT_PRICE_LIST.slice());
        renderPriceList();
        renderServiceLines();
        renderPreview();
      });
    }
    if (state.els.importServices){
      state.els.importServices.addEventListener('click', importServicesFromStorage);
    }
    if (state.els.loadDemoServices){
      state.els.loadDemoServices.addEventListener('click', () => {
        state.services = DEFAULT_SERVICES.slice();
        safeSetJSON(SERVICE_KEY, state.services);
        renderPatientOptions();
        syncPatientFromSelection();
        renderServiceLines();
        renderPreview();
        setServiceHint('Demo-Leistungen geladen. Diese kannst du später durch echte Daten aus dem Durchführungsnachweis ersetzen.');
      });
    }
    if (state.els.saveInvoiceTemplate){
      state.els.saveInvoiceTemplate.addEventListener('click', saveAll);
    }
    if (state.els.printInvoice){
      state.els.printInvoice.addEventListener('click', () => {
        saveAll();
        window.print();
      });
    }
  }

  function fillTemplateInputs(){
    state.els.providerName.value = state.template.providerName || '';
    state.els.providerSubline.value = state.template.providerSubline || '';
    state.els.companyBlock.value = state.template.companyBlock || '';
    state.els.accent.value = state.template.accent || '#3f6fe8';
    state.els.dueDays.value = Number.isFinite(+state.template.dueDays) ? state.template.dueDays : 14;
    state.els.invoiceDate.value = state.template.invoiceDate || isoToday();
    state.els.invoiceNumber.value = state.template.invoiceNumber || createInvoiceNumber();
    state.els.taxRate.value = Number.isFinite(+state.template.taxRate) ? state.template.taxRate : 0;
    if (state.els.uidNumber) state.els.uidNumber.value = state.template.uidNumber || '';
    if (state.els.taxNumber) state.els.taxNumber.value = state.template.taxNumber || '';
    if (state.els.registryNumber) state.els.registryNumber.value = state.template.registryNumber || '';
    state.els.address.value = state.template.patientAddress || '';
    state.els.intro.value = state.template.intro || '';
    state.els.paymentHint.value = state.template.paymentHint || '';
    state.els.bankBlock.value = state.template.bankBlock || '';
    if (state.els.bankAlign) state.els.bankAlign.value = state.template.bankAlign || 'left';
    const radio = document.querySelector(`input[name="logoPosition"][value="${state.template.logoPosition || 'left'}"]`);
    if (radio) radio.checked = true;
  }

  function renderPatientOptions(){
    const select = state.els.patientSelect;
    if (!select) return;
    const allPatients = mergePatientsWithServices();
    select.innerHTML = '<option value="">Bitte auswählen</option>' + allPatients.map((p) => {
      return `<option value="${escapeAttr(p.id)}">${escapeHtml(p.name || 'Patient')}</option>`;
    }).join('');
    if (!state.template.patientId && allPatients[0]) state.template.patientId = allPatients[0].id;
    select.value = state.template.patientId || '';
  }

  function syncPatientFromSelection(){
    const allPatients = mergePatientsWithServices();
    const selected = allPatients.find((p) => String(p.id) === String(state.template.patientId)) || allPatients[0] || null;
    if (!selected){
      state.selectedPatientId = '';
      state.selectedPatientName = '';
      state.selectedPatientAddress = '';
      renderPreview();
      return;
    }
    state.template.patientId = selected.id;
    state.template.patientName = selected.name || '';
    if (!state.template.patientAddress || state.template.patientId !== state.selectedPatientId){
      state.template.patientAddress = selected.address || '';
      if (state.els.address) state.els.address.value = state.template.patientAddress;
    }
    state.selectedPatientId = selected.id;
    state.selectedPatientName = selected.name || '';
    state.selectedPatientAddress = selected.address || '';
    if (state.els.patientSelect) state.els.patientSelect.value = selected.id;
  }

  function renderPriceList(){
    const body = state.els.priceListBody;
    if (!body) return;
    body.innerHTML = '';
    state.priceList.forEach((item, index) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td><input class="mini-input" data-field="service" data-index="${index}" type="text" value="${escapeAttr(item.service)}" placeholder="Leistung" /></td>
        <td><input class="mini-input" data-field="unit" data-index="${index}" type="text" value="${escapeAttr(item.unit)}" placeholder="Einheit" /></td>
        <td><input class="mini-input" data-field="price" data-index="${index}" type="number" min="0" step="0.01" value="${Number(item.price || 0)}" /></td>
        <td><input class="mini-input" data-field="tax" data-index="${index}" type="number" min="0" step="0.1" value="${Number(item.tax || 0)}" /></td>
        <td><button class="control btn" data-remove-price="${index}" type="button">Entfernen</button></td>
      `;
      body.appendChild(tr);
    });

    body.querySelectorAll('input[data-index]').forEach((input) => {
      input.addEventListener('input', () => {
        const idx = Number(input.getAttribute('data-index'));
        const field = input.getAttribute('data-field');
        if (!state.priceList[idx]) return;
        state.priceList[idx][field] = (field === 'price' || field === 'tax') ? Number(input.value || 0) : input.value;
        renderServiceLines();
        renderPreview();
      });
    });
    body.querySelectorAll('[data-remove-price]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const idx = Number(btn.getAttribute('data-remove-price'));
        state.priceList.splice(idx, 1);
        renderPriceList();
        renderServiceLines();
        renderPreview();
      });
    });
  }

  function renderServiceLines(){
    const body = state.els.serviceLinesBody;
    if (!body) return;
    const lines = collectInvoiceLines();
    body.innerHTML = '';
    if (!lines.length){
      body.innerHTML = '<tr><td colspan="6"><div class="empty-state">Noch keine Leistungen für diesen Patienten gefunden.</div></td></tr>';
      renderPreviewLines([]);
      return;
    }
    lines.forEach((line) => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${escapeHtml(formatDate(line.date))}</td>
        <td>${escapeHtml(line.service)}</td>
        <td>${formatNumber(line.quantity)}</td>
        <td>${escapeHtml(line.unit)}</td>
        <td>${formatCurrency(line.unitPrice)}</td>
        <td>${formatCurrency(line.total)}</td>
      `;
      body.appendChild(tr);
    });
    renderPreviewLines(lines);
  }

  function renderPreview(){
    const accent = state.template.accent || '#3f6fe8';
    document.documentElement.style.setProperty('--designer-accent', accent);
    document.documentElement.style.setProperty('--designer-soft', hexToSoft(accent));

    state.els.previewBrand.className = `invoice-brand is-${state.template.logoPosition || 'left'}`;
    state.els.previewProviderName.textContent = state.template.providerName || DEFAULT_TEMPLATE.providerName;
    state.els.previewProviderSubline.textContent = state.template.providerSubline || DEFAULT_TEMPLATE.providerSubline;
    state.els.previewCompanyBlock.innerHTML = nl2br(state.template.companyBlock || '');
    if (state.els.previewLegalBlock){
      const legal = [];
      if ((state.template.uidNumber || '').trim()) legal.push('UID-Nummer: ' + state.template.uidNumber);
      if ((state.template.taxNumber || '').trim()) legal.push('Steuernummer: ' + state.template.taxNumber);
      if ((state.template.registryNumber || '').trim()) legal.push('Gesundheitsberuferegister-Nr.: ' + state.template.registryNumber);
      state.els.previewLegalBlock.innerHTML = legal.join('<br>');
      state.els.previewLegalBlock.style.display = legal.length ? '' : 'none';
    }
    state.els.previewAddress.innerHTML = nl2br(state.template.patientAddress || 'Patient auswählen, damit hier die Rechnungsadresse erscheint.');
    state.els.previewInvoiceNumber.textContent = state.template.invoiceNumber || createInvoiceNumber();
    state.els.previewInvoiceDate.textContent = formatDate(state.template.invoiceDate || isoToday());
    state.els.previewInvoiceDue.textContent = formatDate(calcDueDate(state.template.invoiceDate, state.template.dueDays));
    state.els.previewIntro.textContent = state.template.intro || DEFAULT_TEMPLATE.intro;
    state.els.previewPaymentHint.textContent = state.template.paymentHint || DEFAULT_TEMPLATE.paymentHint;
    state.els.previewBankBlock.innerHTML = nl2br(state.template.bankBlock || '');
    if (state.els.previewBankFooter){
      const align = state.template.bankAlign || 'left';
      state.els.previewBankFooter.style.textAlign = align;
    }
    renderPreviewLogo();
    renderPreviewLines(collectInvoiceLines());
    autoSaveTemplate();
  }

  function renderPreviewLogo(){
    const box = state.els.previewLogo;
    if (!box) return;
    if (state.logo){
      box.innerHTML = `<img src="${state.logo}" alt="Logo" />`;
    } else {
      box.textContent = 'Logo';
    }
  }

  function renderPreviewLines(lines){
    const body = state.els.previewLinesBody;
    if (!body) return;
    body.innerHTML = '';
    if (!lines.length){
      body.innerHTML = '<tr><td colspan="6"><div class="empty-state">Noch keine verrechenbaren Leistungen vorhanden.</div></td></tr>';
      state.els.previewSubtotal.textContent = formatCurrency(0);
      state.els.previewTax.textContent = formatCurrency(0);
      state.els.previewTotal.textContent = formatCurrency(0);
      return;
    }

    let subtotal = 0;
    let taxTotal = 0;
    lines.forEach((line) => {
      subtotal += line.total;
      taxTotal += line.total * (Number(line.taxRate || state.template.taxRate || 0) / 100);
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td>${escapeHtml(formatDate(line.date))}</td>
        <td>${escapeHtml(line.service)}${line.notes ? `<div class="designer-note">${escapeHtml(line.notes)}</div>` : ''}</td>
        <td class="num">${formatNumber(line.quantity)}</td>
        <td>${escapeHtml(line.unit)}</td>
        <td class="num">${formatCurrency(line.unitPrice)}</td>
        <td class="num">${formatCurrency(line.total)}</td>
      `;
      body.appendChild(tr);
    });
    const total = subtotal + taxTotal;
    state.els.previewSubtotal.textContent = formatCurrency(subtotal);
    state.els.previewTax.textContent = formatCurrency(taxTotal);
    state.els.previewTotal.textContent = formatCurrency(total);
  }

  function collectInvoiceLines(){
    const patientId = String(state.template.patientId || '');
    const patientName = String(state.template.patientName || '').trim().toLowerCase();
    let matches = state.services.filter((record) => {
      const recordPatientId = String(record.patientId || '');
      const recordName = String(record.patientName || '').trim().toLowerCase();
      return (patientId && recordPatientId === patientId) || (patientName && recordName === patientName);
    });

    if (!matches.length && state.services.length === DEFAULT_SERVICES.length){
      matches = state.services.filter((record) => String(record.patientId || '') === String(state.template.patientId || ''));
    }

    return matches.map((record) => {
      const priceMatch = matchPriceEntry(record.service);
      const quantity = Number(record.quantity || 1);
      const unitPrice = Number(record.unitPrice != null ? record.unitPrice : (priceMatch ? priceMatch.price : 0));
      const unit = record.unit || (priceMatch ? priceMatch.unit : 'Einheit');
      const taxRate = record.taxRate != null ? Number(record.taxRate) : (priceMatch ? Number(priceMatch.tax || 0) : Number(state.template.taxRate || 0));
      return {
        date: record.date || isoToday(),
        service: record.service || 'Leistung',
        quantity,
        unit,
        unitPrice,
        taxRate,
        total: quantity * unitPrice,
        notes: record.notes || ''
      };
    });
  }

  function importServicesFromStorage(){
    const imported = discoverServiceRecords();
    if (!imported.length){
      state.services = [];
      renderServiceLines();
      renderPreview();
      setServiceHint('Es wurden keine verwertbaren Leistungsdaten gefunden. Sobald dein Durchführungsnachweis Leistungen in localStorage speichert, kann dieser Button sie übernehmen.');
      return;
    }
    state.services = imported;
    safeSetJSON(SERVICE_KEY, state.services);
    renderPatientOptions();
    syncPatientFromSelection();
    renderServiceLines();
    renderPreview();
    setServiceHint(`${imported.length} Leistung${imported.length === 1 ? '' : 'en'} übernommen.`);
  }

  function discoverServiceRecords(){
    const candidates = [];
    Object.keys(localStorage).forEach((key) => {
      const lowered = key.toLowerCase();
      if (!/(durch|nachweis|service|leistung|doku|dokumentation|invoice)/.test(lowered)) return;
      const parsed = readJSON(key, null);
      flattenPossibleRecords(parsed, candidates);
    });
    return normalizeRecords(candidates);
  }

  function flattenPossibleRecords(value, into){
    if (!value) return;
    if (Array.isArray(value)){
      value.forEach((item) => flattenPossibleRecords(item, into));
      return;
    }
    if (typeof value !== 'object') return;
    const hasServiceLike = ['service','leistung','task','title','name','quantity','qty','unit','date','patientName','patientId'].some((k) => Object.prototype.hasOwnProperty.call(value, k));
    if (hasServiceLike) into.push(value);
    Object.keys(value).forEach((key) => {
      const child = value[key];
      if (child && typeof child === 'object') flattenPossibleRecords(child, into);
    });
  }

  function normalizeRecords(records){
    const normalized = records.map((item, index) => {
      const service = item.service || item.leistung || item.task || item.title || item.name || '';
      const patientName = item.patientName || item.patient || item.clientName || item.klient || item.namePatient || '';
      const address = item.patientAddress || item.address || item.patientStreet || item.anschrift || '';
      const quantity = Number(item.quantity || item.qty || item.amount || 1);
      const unit = item.unit || item.einheit || 'Einheit';
      const date = normalizeDate(item.date || item.datum || item.performedAt || item.createdAt || isoToday());
      const patientId = item.patientId || item.clientId || item.klientId || patientName || `p-${index+1}`;
      const notes = item.notes || item.notiz || item.description || '';
      const unitPrice = item.unitPrice != null ? Number(item.unitPrice) : undefined;
      const taxRate = item.taxRate != null ? Number(item.taxRate) : undefined;
      return service ? { id:`imp-${index+1}`, patientId, patientName, patientAddress: address, date, service, quantity, unit, notes, unitPrice, taxRate } : null;
    }).filter(Boolean);

    const unique = [];
    const seen = new Set();
    normalized.forEach((item) => {
      const key = [item.patientId, item.date, item.service, item.quantity, item.unit].join('|');
      if (seen.has(key)) return;
      seen.add(key);
      unique.push(item);
    });
    return unique;
  }

  function buildPatients(){
    const patients = [];
    PATIENT_KEYS.forEach((key) => {
      const parsed = readJSON(key, []);
      if (!Array.isArray(parsed)) return;
      parsed.forEach((patient, index) => {
        const name = patient.name || `${patient.firstName || ''} ${patient.lastName || ''}`.trim();
        if (!name) return;
        const address = patient.address || joinAddress(patient.street, patient.zip, patient.city);
        patients.push({ id: patient.id || `${key}-${index}`, name, address });
      });
    });
    return dedupePatients(patients);
  }

  function mergePatientsWithServices(){
    const fromServices = state.services.map((item, index) => ({
      id: item.patientId || `svc-${index}`,
      name: item.patientName || 'Patient',
      address: item.patientAddress || ''
    }));
    return dedupePatients([].concat(state.patients, fromServices));
  }

  function dedupePatients(list){
    const out = [];
    const seen = new Set();
    list.forEach((p) => {
      const key = `${String(p.id || '').trim()}|${String(p.name || '').trim().toLowerCase()}`;
      if (!p.name || seen.has(key)) return;
      seen.add(key);
      out.push(p);
    });
    return out;
  }

  function ensureProviderFromProfile(){
    const profile = readJSON(PROFILE_KEY, null);
    if (!profile) return;
    const name = `${profile.firstName || ''} ${profile.lastName || ''}`.trim();
    if (name && (!state.template.providerName || state.template.providerName === DEFAULT_TEMPLATE.providerName)){
      state.template.providerName = name;
    }
    const city = profile.fields && profile.fields.city ? profile.fields.city : '';
    const street = profile.fields && profile.fields.street ? profile.fields.street : '';
    const zip = profile.fields && profile.fields.zip ? profile.fields.zip : '';
    const district = profile.districtLabel || profile.district || '';
    const addressBits = [street, joinZipCity(zip, city), district ? `Bezirk: ${district}` : ''].filter(Boolean).join('\n');
    if (addressBits && (!state.template.companyBlock || state.template.companyBlock === DEFAULT_TEMPLATE.companyBlock)){
      state.template.companyBlock = addressBits;
    }
  }

  function autoSaveTemplate(){
    try{
      state.template.patientAddress = state.els.address ? (state.els.address.value || '') : (state.template.patientAddress || '');
      localStorage.setItem(TEMPLATE_KEY, JSON.stringify(state.template));
      localStorage.setItem(PRICE_KEY, JSON.stringify(sanitizePriceList(state.priceList)));
      localStorage.setItem(SERVICE_KEY, JSON.stringify(state.services));
    }catch(e){}
  }

  function saveAll(){
    state.template.patientAddress = state.els.address.value || '';
    safeSetJSON(TEMPLATE_KEY, state.template);
    safeSetJSON(PRICE_KEY, sanitizePriceList(state.priceList));
    safeSetJSON(SERVICE_KEY, state.services);
    const drafts = readJSON(GENERATED_KEY, []);
    const draft = {
      invoiceNumber: state.template.invoiceNumber,
      patientId: state.template.patientId,
      patientName: state.template.patientName,
      createdAt: new Date().toISOString(),
      template: state.template,
      lines: collectInvoiceLines()
    };
    drafts.unshift(draft);
    safeSetJSON(GENERATED_KEY, drafts.slice(0, 20));
    _showSaveBanner('Rechnungsvorlage und Preisliste wurden gespeichert.');
  }

  function handleLogoUpload(e){
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = function(){
      state.logo = String(reader.result || '');
      safeSet(LOGO_KEY, state.logo);
      renderPreview();
    };
    reader.readAsDataURL(file);
  }

  function refreshLogoPositionChips(){
    document.querySelectorAll('#logoPositionGroup .designer-chip').forEach((chip) => {
      const radio = chip.querySelector('input[type="radio"]');
      chip.classList.toggle('is-active', !!(radio && radio.checked));
    });
  }

  function setServiceHint(text){
    if (state.els.serviceHint) state.els.serviceHint.textContent = text;
  }

  function matchPriceEntry(serviceName){
    const normalized = normalizeText(serviceName);
    return state.priceList.find((item) => normalizeText(item.service) === normalized) ||
      state.priceList.find((item) => normalized.includes(normalizeText(item.service)) || normalizeText(item.service).includes(normalized)) || null;
  }

  function sanitizePriceList(list){
    return (list || []).map((item) => ({
      service: String(item.service || ''),
      unit: String(item.unit || 'Einheit'),
      price: Number(item.price || 0),
      tax: Number(item.tax || 0)
    }));
  }

  function mapInputToTemplate(key, value){
    const map = {
      providerName:'providerName',
      providerSubline:'providerSubline',
      companyBlock:'companyBlock',
      accent:'accent',
      dueDays:'dueDays',
      invoiceDate:'invoiceDate',
      invoiceNumber:'invoiceNumber',
      taxRate:'taxRate',
      uidNumber:'uidNumber',
      taxNumber:'taxNumber',
      registryNumber:'registryNumber',
      address:'patientAddress',
      intro:'intro',
      paymentHint:'paymentHint',
      bankBlock:'bankBlock',
      bankAlign:'bankAlign'
    };
    const target = map[key];
    if (!target) return;
    state.template[target] = (target === 'dueDays' || target === 'taxRate') ? Number(value || 0) : value;
  }

  function updateDueDate(){
    state.template.invoiceDate = state.els.invoiceDate.value || isoToday();
    state.template.dueDays = Number(state.els.dueDays.value || 0);
  }

  function createInvoiceNumber(){
    const d = new Date();
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, '0');
    const dd = String(d.getDate()).padStart(2, '0');
    return `R-${yyyy}${mm}${dd}-001`;
  }

  function calcDueDate(dateStr, dueDays){
    const date = new Date(dateStr || isoToday());
    date.setDate(date.getDate() + Number(dueDays || 0));
    return date.toISOString().slice(0,10);
  }

  function normalizeDate(value){
    if (!value) return isoToday();
    if (/^\d{4}-\d{2}-\d{2}$/.test(String(value))) return String(value);
    const d = new Date(value);
    if (!Number.isNaN(d.getTime())) return d.toISOString().slice(0,10);
    const match = String(value).match(/^(\d{2})\.(\d{2})\.(\d{4})$/);
    if (match) return `${match[3]}-${match[2]}-${match[1]}`;
    return isoToday();
  }

  function formatDate(value){
    const iso = normalizeDate(value);
    const [y,m,d] = iso.split('-');
    return `${d}.${m}.${y}`;
  }

  function formatCurrency(value){
    return new Intl.NumberFormat('de-AT', { style:'currency', currency:'EUR' }).format(Number(value || 0));
  }

  function formatNumber(value){
    return new Intl.NumberFormat('de-AT', { maximumFractionDigits:2 }).format(Number(value || 0));
  }

  function isoToday(){
    return new Date().toISOString().slice(0,10);
  }

  function hexToSoft(hex){
    const clean = String(hex || '').replace('#','');
    const full = clean.length === 3 ? clean.split('').map((c) => c + c).join('') : clean;
    const r = parseInt(full.slice(0,2),16) || 63;
    const g = parseInt(full.slice(2,4),16) || 111;
    const b = parseInt(full.slice(4,6),16) || 232;
    return `rgba(${r},${g},${b},.12)`;
  }

  function nl2br(text){
    return escapeHtml(String(text || '')).replace(/\n/g,'<br>');
  }

  function joinAddress(street, zip, city){
    return [street || '', joinZipCity(zip, city)].filter(Boolean).join('\n');
  }

  function joinZipCity(zip, city){
    return [zip || '', city || ''].filter(Boolean).join(' ').trim();
  }

  function normalizeText(text){
    return String(text || '').trim().toLowerCase();
  }

  function readJSON(key, fallback){
    try{
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    }catch(e){
      return fallback;
    }
  }

  function safeGet(key){
    try{ return localStorage.getItem(key) || ''; }catch(e){ return ''; }
  }

  function safeSet(key, value){
    try{ localStorage.setItem(key, value); }catch(e){}
  }

  function safeSetJSON(key, value){
    try{ localStorage.setItem(key, JSON.stringify(value)); }catch(e){}
  }

  function byId(id){ return document.getElementById(id); }

  function escapeHtml(value){
    return String(value == null ? '' : value)
      .replace(/&/g,'&amp;')
      .replace(/</g,'&lt;')
      .replace(/>/g,'&gt;')
      .replace(/"/g,'&quot;')
      .replace(/'/g,'&#39;');
  }

  function escapeAttr(value){ return escapeHtml(value); }

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
