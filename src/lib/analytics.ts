type AnalyticsProperties = Record<
  string,
  string | number | boolean | null | undefined
>;

type AnalyticsWindow = Window & {
  __hecateAnalyticsInitialized?: boolean;
};

const API_BASE = String(import.meta.env.PUBLIC_STATS_API_URL ?? '').replace(
  /\/$/,
  '',
);
const VISITOR_KEY = 'hecate946:visitor-id';
const SESSION_KEY = 'hecate946:session-id';

function createId() {
  const cryptoApi = globalThis.crypto;
  if (typeof cryptoApi.randomUUID === 'function') return cryptoApi.randomUUID();

  const bytes = cryptoApi.getRandomValues(new Uint8Array(16));
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
}

function getStoredId(storage: Storage, key: string) {
  try {
    const existing = storage.getItem(key);
    if (existing) return existing;

    const next = createId();
    storage.setItem(key, next);
    return next;
  } catch {
    return createId();
  }
}

function analyticsDisabled() {
  if (!API_BASE || typeof window === 'undefined') return true;
  const legacyDoNotTrack = (window as Window & { doNotTrack?: string })
    .doNotTrack;
  return navigator.doNotTrack === '1' || legacyDoNotTrack === '1';
}

export function trackEvent(
  name: string,
  properties: AnalyticsProperties = {},
) {
  if (analyticsDisabled()) return;

  const payload = JSON.stringify({
    name,
    path: window.location.pathname,
    visitorId: getStoredId(window.localStorage, VISITOR_KEY),
    sessionId: getStoredId(window.sessionStorage, SESSION_KEY),
    properties,
  });
  const endpoint = `${API_BASE}/api/event`;

  if ('sendBeacon' in navigator) {
    const blob = new Blob([payload], { type: 'text/plain;charset=UTF-8' });
    if (navigator.sendBeacon(endpoint, blob)) return;
  }

  void fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'text/plain;charset=UTF-8' },
    body: payload,
    keepalive: true,
    mode: 'cors',
    credentials: 'omit',
  }).catch(() => {
    // Analytics must never interfere with the website itself.
  });
}

export function initAnalytics() {
  if (analyticsDisabled()) return;

  const analyticsWindow = window as AnalyticsWindow;
  if (analyticsWindow.__hecateAnalyticsInitialized) return;
  analyticsWindow.__hecateAnalyticsInitialized = true;

  let lastTrackedPath = '';

  const trackPage = () => {
    const path = window.location.pathname;
    if (path === lastTrackedPath) return;
    lastTrackedPath = path;
    trackEvent('page_view');
  };

  document.addEventListener('astro:page-load', trackPage);
  trackPage();

  document.addEventListener('click', (event) => {
    const target = event.target;
    if (!(target instanceof Element)) return;

    const trackedElement = target.closest<HTMLElement>('[data-track-event]');
    if (trackedElement?.dataset.trackEvent) {
      trackEvent(trackedElement.dataset.trackEvent, {
        label: trackedElement.dataset.trackLabel,
      });
    }

    const link = target.closest<HTMLAnchorElement>('a[href]');
    if (!link) return;

    const destination = new URL(link.href, window.location.href);

    if (
      link.hasAttribute('download') ||
      destination.pathname.startsWith('/resumes/')
    ) {
      trackEvent('resume_download', {
        file: destination.pathname.split('/').pop() ?? null,
      });
    }

    if (destination.origin !== window.location.origin) {
      trackEvent('outbound_click', {
        host: destination.hostname,
      });
    }
  });
}
