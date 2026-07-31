// ══════════════════════════════════════════════════════════════════
//  ORION SCHOOL MANAGEMENT SYSTEM — SERVICE WORKER  (sw.js)
//  Version: 1.0.0  |  Strategy: Cache-first static, Network-first API
// ══════════════════════════════════════════════════════════════════

const CACHE_NAME = 'orion-v1';
const OFFLINE_PAGE = '/offline.html';

// Assets to pre-cache on install
const PRECACHE_ASSETS = [
    '/',
    '/css/styles.css',
    '/js/app.js',
    '/manifest.json',
    OFFLINE_PAGE
];

// API paths that should always go to network (never cached long-term)
const API_PATH_PREFIX = '/api/';

// IndexedDB config for offline sync queue
const IDB_NAME = 'orion-sync-db';
const IDB_STORE = 'sync-queue';

// ── INSTALL: Pre-cache static shell ───────────────────────────────
self.addEventListener('install', event => {
    console.log('[SW] Installing Orion Service Worker...');
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            console.log('[SW] Pre-caching static assets');
            // Use individual adds so one failure doesn't block the rest
            return Promise.allSettled(
                PRECACHE_ASSETS.map(url => cache.add(url).catch(err => {
                    console.warn(`[SW] Failed to cache ${url}:`, err);
                }))
            );
        }).then(() => self.skipWaiting())
    );
});

// ── ACTIVATE: Clean old caches ─────────────────────────────────────
self.addEventListener('activate', event => {
    console.log('[SW] Activating Orion Service Worker...');
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames
                    .filter(name => name !== CACHE_NAME)
                    .map(name => {
                        console.log(`[SW] Deleting old cache: ${name}`);
                        return caches.delete(name);
                    })
            );
        }).then(() => self.clients.claim())
    );
});

// ── FETCH: Route requests intelligently ───────────────────────────
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);

    // Only handle same-origin requests
    if (url.origin !== location.origin) return;

    // Skip SSE / streaming endpoints entirely — do not cache
    if (url.pathname === '/api/notifications/stream') return;

    // Skip non-GET methods for caching (they'll be handled by BackgroundSync)
    if (request.method !== 'GET') {
        event.respondWith(networkWithOfflineQueue(request));
        return;
    }

    // API requests → Network-first, fallback to cache, then offline page
    if (url.pathname.startsWith(API_PATH_PREFIX)) {
        event.respondWith(networkFirstStrategy(request));
        return;
    }

    // Static assets → Cache-first, fallback to network
    event.respondWith(cacheFirstStrategy(request));
});

// ── Cache-first strategy ───────────────────────────────────────────
async function cacheFirstStrategy(request) {
    const cached = await caches.match(request);
    if (cached) return cached;

    try {
        const networkResponse = await fetch(request);
        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch {
        // If it's a navigation, return the cached index
        if (request.mode === 'navigate') {
            const index = await caches.match('/');
            return index || new Response('Offline', { status: 503 });
        }
        return new Response('Offline', { status: 503 });
    }
}

// ── Network-first strategy (for API calls) ─────────────────────────
async function networkFirstStrategy(request) {
    try {
        const networkResponse = await fetch(request);
        // Cache successful GET API responses briefly for offline fallback
        if (networkResponse.ok) {
            const cache = await caches.open(CACHE_NAME);
            cache.put(request, networkResponse.clone());
        }
        return networkResponse;
    } catch {
        // Fallback to cached API response if available
        const cached = await caches.match(request);
        if (cached) return cached;

        // Return offline JSON for API requests
        return new Response(
            JSON.stringify({ error: 'offline', detail: 'You are currently offline. Data may be outdated.' }),
            { status: 503, headers: { 'Content-Type': 'application/json' } }
        );
    }
}

// ── Offline queue for mutating requests (POST/PUT) ─────────────────
async function networkWithOfflineQueue(request) {
    try {
        return await fetch(request);
    } catch {
        // Clone request data and store in IndexedDB for later sync
        const body = await request.text().catch(() => '');
        await enqueueForSync({
            url: request.url,
            method: request.method,
            headers: Object.fromEntries(request.headers.entries()),
            body,
            timestamp: Date.now()
        });

        // Return optimistic 202 so UI doesn't show error
        return new Response(
            JSON.stringify({ queued: true, message: 'Saved offline. Will sync when connection restores.' }),
            { status: 202, headers: { 'Content-Type': 'application/json' } }
        );
    }
}

// ── IndexedDB helpers ─────────────────────────────────────────────
function openSyncDB() {
    return new Promise((resolve, reject) => {
        const req = indexedDB.open(IDB_NAME, 1);
        req.onupgradeneeded = e => {
            e.target.result.createObjectStore(IDB_STORE, { autoIncrement: true });
        };
        req.onsuccess = e => resolve(e.target.result);
        req.onerror = e => reject(e.target.error);
    });
}

async function enqueueForSync(entry) {
    try {
        const db = await openSyncDB();
        const tx = db.transaction(IDB_STORE, 'readwrite');
        tx.objectStore(IDB_STORE).add(entry);
        await new Promise((res, rej) => { tx.oncomplete = res; tx.onerror = rej; });
        // Register background sync if supported
        if (self.registration.sync) {
            await self.registration.sync.register('orion-data-sync');
        }
    } catch (err) {
        console.error('[SW] Failed to enqueue for sync:', err);
    }
}

async function drainSyncQueue() {
    const db = await openSyncDB();
    const tx = db.transaction(IDB_STORE, 'readwrite');
    const store = tx.objectStore(IDB_STORE);
    const allKeys = await new Promise(res => {
        const req = store.getAllKeys(); req.onsuccess = () => res(req.result);
    });
    const allEntries = await new Promise(res => {
        const req = store.getAll(); req.onsuccess = () => res(req.result);
    });

    let successCount = 0;
    for (let i = 0; i < allEntries.length; i++) {
        const entry = allEntries[i];
        try {
            const res = await fetch(entry.url, {
                method: entry.method,
                headers: entry.headers,
                body: entry.body || undefined
            });
            if (res.ok || res.status < 500) {
                store.delete(allKeys[i]);
                successCount++;
            }
        } catch {
            // Still offline, leave in queue
            break;
        }
    }

    if (successCount > 0) {
        // Notify all open windows that sync happened
        const clients = await self.clients.matchAll({ type: 'window' });
        clients.forEach(client => client.postMessage({
            type: 'SYNC_COMPLETE',
            count: successCount
        }));
    }
}

// ── Background Sync ────────────────────────────────────────────────
self.addEventListener('sync', event => {
    if (event.tag === 'orion-data-sync') {
        console.log('[SW] Background sync triggered');
        event.waitUntil(drainSyncQueue());
    }
});

// ── Push Notifications (scaffold for future use) ───────────────────
self.addEventListener('push', event => {
    const data = event.data ? event.data.json() : {};
    const title = data.title || 'Orion School System';
    const options = {
        body: data.body || 'You have a new notification',
        icon: '/icons/icon-192.png',
        badge: '/icons/icon-192.png',
        tag: data.tag || 'orion-notification',
        data: { url: data.url || '/' }
    };
    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', event => {
    event.notification.close();
    const targetUrl = event.notification.data?.url || '/';
    event.waitUntil(
        self.clients.matchAll({ type: 'window' }).then(clients => {
            const existing = clients.find(c => c.url === targetUrl && 'focus' in c);
            if (existing) return existing.focus();
            return self.clients.openWindow(targetUrl);
        })
    );
});

// ── Message handler (from main thread) ────────────────────────────
self.addEventListener('message', event => {
    if (event.data?.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
    if (event.data?.type === 'MANUAL_SYNC') {
        drainSyncQueue();
    }
});

console.log('[SW] Orion Service Worker script loaded');
