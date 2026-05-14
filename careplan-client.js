(function(){
  var KEY = 'nursy_careplan_client_v1';

  function esc(s){
    return String(s == null ? '' : s)
      .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
      .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
  }

  function seed(){
    try{
      if(localStorage.getItem(KEY)) return;
      var data = {
        updated: '2026-04-22',
        areas: [
          {
            title: 'Mobilität',
            tag: 'Bezugspflege: Anna Müller',
            measures: [
              { measure:'Mobilisation an die Bettkante', goal:'Erhalt der Mobilität', frequency:'1x täglich' },
              { measure:'Gehübungen mit Rollator', goal:'Stärkung Beinmuskulatur', frequency:'3x wöchentlich' }
            ]
          },
          {
            title: 'Körperpflege',
            tag: 'Pflegekraft: Anna Müller',
            measures: [
              { measure:'Ganzkörperwäsche im Bett', goal:'Hautintegrität sicherstellen', frequency:'1x täglich' },
              { measure:'Mundpflege', goal:'Mundhygiene erhalten', frequency:'2x täglich' }
            ]
          },
          {
            title: 'Medikation',
            tag: 'Pflegekraft: Markus Berger',
            measures: [
              { measure:'Medikamentengabe oral', goal:'Schmerzreduktion und stabile Medikation', frequency:'08:00 / 20:00' },
              { measure:'Insulingabe', goal:'Stabile Blutzuckerwerte', frequency:'vor den Mahlzeiten' }
            ]
          },
          {
            title: 'Vitalzeichen & Beobachtung',
            tag: 'Alle Pflegekräfte',
            measures: [
              { measure:'Blutdruckkontrolle', goal:'Kreislauf überwachen', frequency:'2x täglich' },
              { measure:'Flüssigkeitsbilanz beobachten', goal:'Ausreichende Hydrierung sichern', frequency:'laufend' }
            ]
          }
        ]
      };
      localStorage.setItem(KEY, JSON.stringify(data));
    }catch(e){}
  }

  function load(){
    seed();
    try{ return JSON.parse(localStorage.getItem(KEY) || 'null') || { updated:'', areas:[] }; }
    catch(e){ return { updated:'', areas:[] }; }
  }

  function formatDate(iso){
    if(!iso) return '—';
    var d = new Date(iso + 'T00:00:00');
    return new Intl.DateTimeFormat('de-AT', { day:'2-digit', month:'2-digit', year:'numeric' }).format(d);
  }

  function render(){
    var data = load();
    var areas = data.areas || [];
    var totalMeasures = areas.reduce(function(s, a){ return s + (a.measures || []).length; }, 0);

    var statAreas = document.getElementById('cpStatAreas');
    var statMeasures = document.getElementById('cpStatMeasures');
    var statUpdated = document.getElementById('cpStatUpdated');
    if(statAreas) statAreas.textContent = String(areas.length);
    if(statMeasures) statMeasures.textContent = String(totalMeasures);
    if(statUpdated) statUpdated.textContent = formatDate(data.updated);

    var host = document.getElementById('cpAreas');
    if(!host) return;
    host.innerHTML = areas.map(function(a){
      var rows = (a.measures || []).map(function(m){
        return '' +
          '<tr>' +
            '<td data-label="Maßnahme">' +
              '<div class="cp-measure">' + esc(m.measure) + '</div>' +
              '<div class="cp-goal">Ziel: ' + esc(m.goal) + '</div>' +
            '</td>' +
            '<td data-label="Häufigkeit">' + esc(m.frequency) + '</td>' +
          '</tr>';
      }).join('');
      return '' +
        '<div class="cp-area">' +
          '<div class="cp-area__head">' +
            '<h3 class="cp-area__title">' + esc(a.title) + '</h3>' +
            (a.tag ? '<span class="cp-tag">' + esc(a.tag) + '</span>' : '') +
          '</div>' +
          '<table class="cp-table">' +
            '<thead><tr><th>Maßnahme</th><th style="width:30%">Häufigkeit</th></tr></thead>' +
            '<tbody>' + rows + '</tbody>' +
          '</table>' +
        '</div>';
    }).join('') || '<p class="muted">Es liegt aktuell kein Pflegeplan vor.</p>';
  }

  document.addEventListener('DOMContentLoaded', function(){
    seed();
    render();
    var print = document.getElementById('cpPrint');
    if(print) print.addEventListener('click', function(){ window.print(); });
  });
})();
