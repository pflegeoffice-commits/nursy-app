const CACHE = 'auftragslage-v2';
const PRECACHE = [
  '/auftragslage/',
  '/auftragslage/login',
  '/styles.css',
  '/icon-auftragslage-192.png',
  '/icon-auftragslage-512.png',
  '/manifest-auftragslage.json'
];

self.addEventListener('install', function(e) {
  e.waitUntil(
    caches.open(CACHE).then(function(cache) {
      return cache.addAll(PRECACHE);
    }).then(function() { return self.skipWaiting(); })
  );
});

self.addEventListener('activate', function(e) {
  e.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(
        keys.filter(function(k) { return k !== CACHE; })
            .map(function(k) { return caches.delete(k); })
      );
    }).then(function() { return self.clients.claim(); })
  );
});

self.addEventListener('fetch', function(e) {
  if (e.request.method !== 'GET') return;
  var url = new URL(e.request.url);
  if (url.pathname.startsWith('/api/')) return;
  // Always fetch HTML fresh from network; only use cache as offline fallback
  var isHtml = url.pathname.endsWith('/') || url.pathname.endsWith('.html')
               || url.pathname === '/auftragslage/login';
  if (isHtml) {
    e.respondWith(
      fetch(e.request)
        .then(function(resp) {
          var clone = resp.clone();
          caches.open(CACHE).then(function(cache) { cache.put(e.request, clone); });
          return resp;
        })
        .catch(function() {
          return caches.match(e.request);
        })
    );
    return;
  }
  // Static assets: network-first, cache fallback
  e.respondWith(
    fetch(e.request)
      .then(function(resp) {
        var clone = resp.clone();
        caches.open(CACHE).then(function(cache) { cache.put(e.request, clone); });
        return resp;
      })
      .catch(function() {
        return caches.match(e.request);
      })
  );
});
