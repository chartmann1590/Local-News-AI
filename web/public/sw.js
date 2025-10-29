/* Simple service worker for runtime caching and offline support */
const CACHE_NAME = 'news-ai-cache-v1'
const CORE_URLS = [
  '/',
  '/static/',
  '/static/index.html',
]

self.addEventListener('install', (event) => {
  self.skipWaiting()
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(CORE_URLS).catch(()=>{}))
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.map((k) => (k === CACHE_NAME ? null : caches.delete(k)))))
  )
  self.clients.claim()
})

function isHtmlRequest(request) {
  return request.mode === 'navigate' || (request.headers.get('accept') || '').includes('text/html')
}

self.addEventListener('fetch', (event) => {
  const { request } = event
  const url = new URL(request.url)

  // Skip non-GET
  if (request.method !== 'GET') return
  // Bypass API calls
  if (url.pathname.startsWith('/api/')) return

  // Network-first for HTML navigations
  if (isHtmlRequest(request)) {
    event.respondWith(
      fetch(request)
        .then((resp) => {
          const copy = resp.clone()
          caches.open(CACHE_NAME).then((cache) => cache.put('/static/index.html', copy).catch(()=>{}))
          return resp
        })
        .catch(async () => {
          const cached = await caches.match('/static/index.html')
          return cached || new Response('<h1>Offline</h1>', { headers: { 'Content-Type': 'text/html' } })
        })
    )
    return
  }

  // Stale-while-revalidate for other assets (JS, CSS, images, CDN)
  event.respondWith(
    caches.match(request).then((cached) => {
      const fetchPromise = fetch(request)
        .then((resp) => {
          const copy = resp.clone()
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy).catch(()=>{}))
          return resp
        })
        .catch(() => cached)
      return cached || fetchPromise
    })
  )
})

