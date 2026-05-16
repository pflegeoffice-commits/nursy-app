/* df-measures.js – Shared helper for Durchführungsnachweis measure cache
   Written by durchfuehrungsnachweis.html after fetching the Pflegeplanung API.
   Read by patients.js, patient-selector.js, dashboard-care.html for status dots.
   Cache key: nursy_df_measures_v1_<patId>
   Cache format: { total: N, times: [{id, t}] }
*/
(function(w) {
  'use strict';

  var _PREFIX = 'nursy_df_measures_v1_';

  var _FALLBACK = [
    {id:1,t:'07:00'},{id:2,t:'07:30'},{id:3,t:'08:00'},{id:4,t:'08:00'},
    {id:5,t:'09:00'},{id:6,t:'10:00'},{id:7,t:'10:00'},{id:8,t:'11:00'},
    {id:9,t:'12:00'},{id:10,t:'12:00'},{id:11,t:'13:00'},{id:12,t:'14:00'},
    {id:13,t:'15:00'},{id:14,t:'16:00'},{id:15,t:'18:00'},
    {id:16,t:'20:00'},{id:17,t:'20:00'},{id:18,t:'20:00'},
    {id:19,t:'21:00'},{id:20,t:'21:30'},
  ];

  function _read(patId) {
    try {
      var raw = localStorage.getItem(_PREFIX + (patId || 'default'));
      return raw ? JSON.parse(raw) : null;
    } catch(e) { return null; }
  }

  function set(patId, data) {
    try { localStorage.setItem(_PREFIX + (patId || 'default'), JSON.stringify(data)); } catch(e) {}
  }

  function times(patId) {
    var c = _read(patId);
    return (c && Array.isArray(c.times) && c.times.length) ? c.times : _FALLBACK;
  }

  function total(patId) {
    var c = _read(patId);
    return (c && typeof c.total === 'number' && c.total > 0) ? c.total : _FALLBACK.length;
  }

  function names(patId) {
    var c = _read(patId);
    return (c && Array.isArray(c.names) && c.names.length) ? c.names : null;
  }

  w.dfMeasures = { set: set, times: times, total: total, names: names };
}(window));
