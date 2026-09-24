// Raíz y nervio: service worker (cache-first, offline total)
const CACHE = 'raiz-nervio-v1.2.0';
const FILES = ['./', './index.html', './manifest.webmanifest', './icon-192.png', './icon-512.png', './apple-touch-icon.png'];
self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(async c => {
    await c.addAll(FILES.map(f => new Request(f, { cache: 'reload' })));
    // imágenes de músculos (opcionales)
    try {
      const r = await fetch('./img/index.json', { cache: 'reload' });
      if (r.ok) {
        await c.put('./img/index.json', r.clone());
        const idx = await r.json();
        const files = [...new Set(Object.values(idx).map(e => './' + e.file))];
        await Promise.all(files.map(f => c.add(new Request(f, { cache: 'reload' })).catch(() => {})));
      }
    } catch (e) {}
  }).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  e.respondWith(
    caches.match(e.request, { ignoreSearch: true }).then(hit => hit || fetch(e.request).then(res => {
      if (res.ok && new URL(e.request.url).origin === location.origin) {
        const copy = res.clone(); caches.open(CACHE).then(c => c.put(e.request, copy));
      }
      return res;
    }).catch(() => e.request.mode === 'navigate' ? caches.match('./index.html') : undefined))
  );
});
