/* سرویس‌ورکر باغ حفظ — کار آفلاین
   برای عوض‌کردن نسخهٔ برنامه، عدد VERSION را بالا ببرید. */
const VERSION = 'v7';
const SHELL = 'hifz-shell-' + VERSION;
const AUDIO = 'hifz-audio-v1';           // نام‌هایی که برنامه برای ذخیرهٔ صدا و تصویر آیه‌ها استفاده می‌کند
const IMG = 'hifz-img-v1';
const FILES = ['./', 'index.html', 'manifest.json', 'icon-192.png', 'icon-512.png', 'fonts/scheherazade-new-regular.woff2'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(SHELL).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k.startsWith('hifz-shell-') && k !== SHELL).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

/* مرورگرها (به‌ویژه Safari) برای فایل صوتی درخواست Range می‌فرستند؛ از روی نسخهٔ ذخیره‌شده پاسخ می‌دهیم */
async function rangeFrom(req, res) {
  const m = /bytes=(\d*)-(\d*)/.exec(req.headers.get('range') || '');
  if (!m || !res || res.status !== 200) return res;
  const buf = await res.arrayBuffer(), size = buf.byteLength;
  let start = m[1] ? +m[1] : 0, end = m[2] ? Math.min(+m[2], size - 1) : size - 1;
  if (!m[1] && m[2]) { start = Math.max(0, size - +m[2]); end = size - 1; }
  if (start >= size) return new Response(null, { status: 416, headers: { 'Content-Range': 'bytes */' + size } });
  return new Response(buf.slice(start, end + 1), { status: 206, headers: { 'Content-Type': res.headers.get('Content-Type') || 'audio/mpeg', 'Content-Length': String(end - start + 1), 'Content-Range': `bytes ${start}-${end}/${size}`, 'Accept-Ranges': 'bytes' } });
}

self.addEventListener('fetch', e => {
  const req = e.request, url = new URL(req.url);
  if (req.method !== 'GET') return;

  /* تصویر آیهٔ EveryAyah: اگر ذخیره شده بود از حافظه، وگرنه از اینترنت */
  if (url.hostname === 'everyayah.com' && /\/images_png\//.test(url.pathname)) {
    e.respondWith(caches.match(req.url).then(r => r || fetch(req)));
    return;
  }
  if (url.origin !== location.origin) return;

  if (/\/(audio|images)\//.test(url.pathname)) {
    e.respondWith((async () => {
      const hit = await caches.match(url.pathname.endsWith('.json') ? req : new Request(req.url), { ignoreSearch: true });
      if (hit) return req.headers.has('range') ? rangeFrom(req, hit) : hit;
      return fetch(req);
    })());
    return;
  }

  if (req.mode === 'navigate') {            // نسخهٔ ذخیره‌شده را فوری می‌دهد و در پس‌زمینه تازه می‌کند (دفعهٔ بعد نسخهٔ نو می‌آید)
    e.respondWith(caches.match('index.html').then(r => {
      const net = fetch(req).then(res => { if (res.ok) caches.open(SHELL).then(c => c.put('index.html', res.clone())); return res; }).catch(() => null);
      if (r) { e.waitUntil(net); return r; }
      return net.then(res => res || Response.error());
    }));
    return;
  }
  e.respondWith(caches.match(req).then(r => r || fetch(req).then(res => {
    if (res.ok) { const copy = res.clone(); caches.open(SHELL).then(c => c.put(req, copy)); }
    return res;
  })));
});
