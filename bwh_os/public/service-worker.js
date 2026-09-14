// BWH OS service worker. bwh_os.pwa.service_worker serves it with scope /os.
//
// It only gives a navigation an offline page. Hashed build assets already get long HTTP caching,
// and the app shell carries a CSRF token, so the worker caches neither.

const CACHE = "bwh-os-v1";
const OFFLINE_URL = "/assets/bwh_os/offline.html";

self.addEventListener("install", (event) => {
	event.waitUntil(
		caches
			.open(CACHE)
			.then((cache) => cache.addAll([OFFLINE_URL, "/assets/bwh_os/images/os-logo.svg"]))
			.then(() => self.skipWaiting())
	);
});

self.addEventListener("activate", (event) => {
	event.waitUntil(
		caches
			.keys()
			.then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))))
			.then(() => self.clients.claim())
	);
});

self.addEventListener("fetch", (event) => {
	if (event.request.mode !== "navigate") return;
	event.respondWith(fetch(event.request).catch(() => caches.match(OFFLINE_URL)));
});
