const CACHE = 'nursy-v9';
const PRECACHE = [
  '/',
  '/index.html',
  '/login-client.html',
  '/dashboard-client.html',
  '/portal/',
  '/portal/app',
  '/portal/admin',
  '/pflege-portal-login.html',
  '/pflege-portal.html',
  '/pfleger-einsatz.html',
  '/styles.css',
  '/icon-nursy-192.png',
  '/icon-nursy-512.png',
  '/icon-portal-192.png',
  '/icon-portal-512.png',
  '/manifest-client.json',
  '/manifest-nursy.json',
  '/manifest-portal.json'
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
  /* Externe Requests (Karten-Tiles, Nominatim, OSRM) direkt durchlassen */
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith('/api/')) return;
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

// ── Push Notifications ───────────────────────────────────────────────────────

self.addEventListener('push', function(event) {
  var data = {};
  try { data = event.data ? event.data.json() : {}; } catch(e) {}
  var title = data.title || '🚨 Nursy Alarm';
  var options = {
    body:               data.body || 'Neuer Einsatz – bitte App öffnen.',
    icon:               '/icon-nursy-192.png',
    badge:              '/icon-nursy-192.png',
    vibrate:            [300, 100, 300, 100, 300],
    tag:                'nursy-alarm',
    requireInteraction: true,
    silent:             false,
    data:               { url: data.url || '/pfleger-einsatz.html' }
  };
  event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function(event) {
  event.notification.close();
  var url = (event.notification.data && event.notification.data.url) || '/pfleger-einsatz.html';
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then(function(list) {
      for (var i = 0; i < list.length; i++) {
        if (list[i].url.indexOf(url) !== -1 && 'focus' in list[i]) {
          return list[i].focus();
        }
      }
      if (clients.openWindow) return clients.openWindow(url);
    })
  );
});
