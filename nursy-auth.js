// Nursy Auth Helper — token-based fallback for environments where cookies fail
(function(global) {
  var KEYS = { admin: 'nursy_tok_admin', leitstelle: 'nursy_tok_ls' };

  var NursyAuth = {
    save: function(role, token) {
      try { sessionStorage.setItem(KEYS[role] || ('nursy_tok_' + role), token); } catch(e) {}
    },
    get: function(role) {
      try { return sessionStorage.getItem(KEYS[role] || ('nursy_tok_' + role)) || ''; } catch(e) { return ''; }
    },
    clear: function(role) {
      try {
        if (role) {
          sessionStorage.removeItem(KEYS[role] || ('nursy_tok_' + role));
        } else {
          Object.values(KEYS).forEach(function(k) { sessionStorage.removeItem(k); });
        }
      } catch(e) {}
    },
    headers: function(role) {
      var tok = NursyAuth.get(role);
      return tok ? { 'X-Nursy-Token': tok } : {};
    }
  };

  // Patch global fetch to automatically inject X-Nursy-Token for /api/ requests
  var _origFetch = global.fetch.bind(global);
  global.fetch = function(url, opts) {
    opts = opts || {};
    var u = typeof url === 'string' ? url : (url.url || '');
    if (u.indexOf('/api/') !== -1) {
      var existingHeaders = opts.headers || {};
      if (!existingHeaders['X-Nursy-Token']) {
        var adminTok = NursyAuth.get('admin');
        var lsTok    = NursyAuth.get('leitstelle');
        var tok = adminTok || lsTok;
        if (tok) {
          if (typeof existingHeaders.get === 'function') {
            // Headers object
            if (!existingHeaders.get('X-Nursy-Token')) {
              opts = Object.assign({}, opts);
              var h = {};
              existingHeaders.forEach(function(v, k) { h[k] = v; });
              h['X-Nursy-Token'] = tok;
              opts.headers = h;
            }
          } else {
            opts = Object.assign({}, opts, {
              headers: Object.assign({}, existingHeaders, { 'X-Nursy-Token': tok })
            });
          }
        }
      }
    }
    return _origFetch(url, opts);
  };

  global.NursyAuth = NursyAuth;
})(window);
