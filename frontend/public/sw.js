const CACHE_NAME = 'autodiag-ai-shell-v1';

const APP_SHELL = [
  '/',
  '/index.html',
  '/manifest.json',
  '/favicon.svg',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  if (url.pathname.startsWith('/api/')) {
    return;
  }

  if (url.origin !== self.location.origin) {
    return;
  }

  const isStaticAsset = /\.(js|css|png|svg|jpg|jpeg|gif|webp|glb|gltf|obj|mtl|json|txt|ico)$/i.test(url.pathname);

  event.respondWith(
    (async () => {
      try {
        const networkResponse = await fetch(request.clone());

        if (networkResponse && networkResponse.status === 200) {
          const cache = await caches.open(CACHE_NAME);
          cache.put(request, networkResponse.clone());
        }

        return networkResponse;
      } catch {
        const cachedResponse = await caches.match(request);
        if (cachedResponse) return cachedResponse;

        if (request.mode === 'navigate') {
          const indexHtml = await caches.match('/index.html');
          if (indexHtml) return indexHtml;
        }

        return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
      }
    })()
  );
});
