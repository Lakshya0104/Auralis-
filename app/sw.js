// Offline cache so the app keeps working without network once loaded.
const CACHE = 'auralis-v1';
const FILES = ['./', 'index.html', 'app.js', 'i18n.js', 'memory.js', 'router.js', 'fusion.js', 'fusion_weights.json', 'manifest.json'];
self.addEventListener('install', (e) => e.waitUntil(caches.open(CACHE).then((c) => c.addAll(FILES))));
self.addEventListener('fetch', (e) => e.respondWith(
  caches.match(e.request).then((r) => r || fetch(e.request).then((res) => {
    const copy = res.clone();
    caches.open(CACHE).then((c) => c.put(e.request, copy));
    return res;
  }))));
