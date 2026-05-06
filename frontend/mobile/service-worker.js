const CACHE_NAME = 'masar-mobile-v9';

const DEFAULT_API_BASE = 'https://masar-backend-oxnm.onrender.com/api';

const APP_ASSETS = [
  './',
  './index.html',
  './manifest.json',
  './service-worker.js',
  './icons/icon-192.png',
  './icons/icon-512.png'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(APP_ASSETS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME)
          .map((key) => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;

  const url = new URL(event.request.url);

  // لا نخزن طلبات API أو أي طلبات خارج نفس أصل التطبيق
  if (url.origin !== self.location.origin || url.pathname.includes('/api/')) {
    return;
  }

  // صفحات التنقل ترجع إلى index.html عند عدم توفر الشبكة
  if (event.request.mode === 'navigate') {
    event.respondWith(
      fetch(event.request).catch(() => caches.match('./index.html'))
    );
    return;
  }

  // ملفات التطبيق: Cache first ثم تحديث من الشبكة إن أمكن
  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;

      return fetch(event.request)
        .then((response) => {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, copy);
          });
          return response;
        })
        .catch(() => caches.match('./index.html'));
    })
  );
});