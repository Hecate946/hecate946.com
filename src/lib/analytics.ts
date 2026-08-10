import { resolveStatsApiBase } from '@/lib/stats-api';

type AnalyticsProperties = Record<
  string,
  string | number | boolean | null | undefined
>;

type AnalyticsWindow = Window & {
  __hecateAnalyticsInitialized?: boolean;
  __hecateAnalyticsCleanup?: () => void;
};

const VISITOR_KEY = 'hecate946:visitor-id';
const SESSION_KEY = 'hecate946:session-id';
const LOCAL_STATS_KEY = 'hecate946:your-stats';


interface LocalVisitorStats {
  firstVisitAt: string;
  lastVisitAt: string;
  visits: number;
  pageViews: number;
  activeSeconds: number;
  interactions: number;
  pages: Record<string, number>;
  events: Record<string, number>;
  colorTheme: string;
  season: string;
}

function readLocalStats(): LocalVisitorStats {
  const now = new Date().toISOString();
  const fallback: LocalVisitorStats = {
    firstVisitAt: now,
    lastVisitAt: now,
    visits: 0,
    pageViews: 0,
    activeSeconds: 0,
    interactions: 0,
    pages: {},
    events: {},
    colorTheme: 'system',
    season: 'auto',
  };

  try {
    const saved = window.localStorage.getItem(LOCAL_STATS_KEY);
    return saved ? { ...fallback, ...JSON.parse(saved) } : fallback;
  } catch {
    return fallback;
  }
}

function updateLocalStats(update: (stats: LocalVisitorStats) => void) {
  if (typeof window === 'undefined') return;
  try {
    const stats = readLocalStats();
    update(stats);
    stats.lastVisitAt = new Date().toISOString();
    stats.colorTheme = window.localStorage.getItem('color-theme') ?? 'system';
    stats.season = window.localStorage.getItem('season-preference') ?? 'auto';
    window.localStorage.setItem(LOCAL_STATS_KEY, JSON.stringify(stats));
    window.dispatchEvent(new CustomEvent('hecate:local-stats-updated'));
  } catch {
    // Local visit statistics are optional and must never affect the site.
  }
}

function createId() {
  const cryptoApi = globalThis.crypto;
  if (cryptoApi && typeof cryptoApi.randomUUID === 'function') {
    return cryptoApi.randomUUID();
  }

  if (cryptoApi && typeof cryptoApi.getRandomValues === 'function') {
    const bytes = cryptoApi.getRandomValues(new Uint8Array(16));
    return Array.from(bytes, (byte) => byte.toString(16).padStart(2, '0')).join('');
  }

  // Analytics IDs are anonymous deduplication tokens, not security credentials.
  // Keep tracking functional even on older/non-secure HTTP contexts where Web
  // Crypto may be unavailable.
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;
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
  if (typeof window === 'undefined') return true;
  const legacyDoNotTrack = (window as Window & { doNotTrack?: string })
    .doNotTrack;
  return navigator.doNotTrack === '1' || legacyDoNotTrack === '1';
}

export function trackEvent(
  name: string,
  properties: AnalyticsProperties = {},
) {
  updateLocalStats((stats) => {
    stats.interactions += 1;
    stats.events[name] = (stats.events[name] ?? 0) + 1;
  });

  if (analyticsDisabled()) return;

  const apiBase = resolveStatsApiBase();
  let eventProperties = properties;

  // Local analytics has no IP/Cloudflare context. Give only the local dev
  // backend a coarse browser-timezone hint so its visitor map can render a
  // meaningful test light without contacting production or prompting for
  // geolocation permission.
  if (apiBase.startsWith('/')) {
    let localTimeZone = '';
    try {
      localTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone ?? '';
    } catch {
      localTimeZone = '';
    }

    if (localTimeZone) {
      eventProperties = { ...properties, __localTimeZone: localTimeZone };
    }
  }

  const payload = JSON.stringify({
    name,
    path: window.location.pathname,
    visitorId: getStoredId(window.localStorage, VISITOR_KEY),
    sessionId: getStoredId(window.sessionStorage, SESSION_KEY),
    properties: eventProperties,
  });
  const endpoint = `${apiBase}/api/event`;
  const requestInit: RequestInit = {
    method: 'POST',
    headers: { 'Content-Type': 'text/plain;charset=UTF-8' },
    body: payload,
    keepalive: true,
    mode: 'cors',
    credentials: 'omit',
  };

  // The local endpoint is same-origin and cheap. Await its completion in the
  // background so the Stats page can refresh immediately after its own page
  // view is stored instead of briefly showing an empty map for up to a minute.
  if (apiBase.startsWith('/')) {
    void fetch(endpoint, requestInit)
      .then((response) => {
        if (response.ok && name === 'page_view') {
          window.dispatchEvent(new CustomEvent('hecate:local-backend-stats-updated'));
        }
      })
      .catch(() => {
        // Local analytics is optional and must never interfere with dev.
      });
    return;
  }

  if ('sendBeacon' in navigator) {
    const blob = new Blob([payload], { type: 'text/plain;charset=UTF-8' });
    if (navigator.sendBeacon(endpoint, blob)) return;
  }

  void fetch(endpoint, requestInit).catch(() => {
    // Analytics must never interfere with the website itself.
  });
}

export function initAnalytics() {
  if (analyticsDisabled()) return;

  const analyticsWindow = window as AnalyticsWindow;
  if (analyticsWindow.__hecateAnalyticsInitialized) return;
  analyticsWindow.__hecateAnalyticsInitialized = true;

  let lastTrackedPath = '';
  let heartbeatTimer = 0;
  let activeStartedAt = document.visibilityState === 'visible' ? Date.now() : 0;

  updateLocalStats((stats) => {
    stats.visits += 1;
  });

  const trackPage = () => {
    const path = window.location.pathname;
    if (path === lastTrackedPath) return;
    lastTrackedPath = path;
    updateLocalStats((stats) => {
      stats.pageViews += 1;
      stats.pages[path] = (stats.pages[path] ?? 0) + 1;
    });
    trackEvent('page_view');
  };

  const stopHeartbeat = () => {
    window.clearInterval(heartbeatTimer);
    heartbeatTimer = 0;
  };

  const sendHeartbeat = () => {
    if (document.visibilityState === 'visible') {
      trackEvent('heartbeat');
    }
  };

  const startHeartbeat = (sendImmediately = false) => {
    stopHeartbeat();

    if (document.visibilityState !== 'visible') return;
    if (sendImmediately) sendHeartbeat();

    heartbeatTimer = window.setInterval(sendHeartbeat, 120_000);
  };

  const saveActiveTime = () => {
    if (!activeStartedAt) return;
    const elapsed = Math.max(0, Math.round((Date.now() - activeStartedAt) / 1000));
    activeStartedAt = 0;
    if (elapsed) updateLocalStats((stats) => { stats.activeSeconds += elapsed; });
  };

  const handleVisibilityChange = () => {
    if (document.visibilityState === 'visible') {
      activeStartedAt = Date.now();
      startHeartbeat(true);
    } else {
      saveActiveTime();
      stopHeartbeat();
    }
  };

  const handlePageHide = () => saveActiveTime();

  const handleClick = (event: MouseEvent) => {
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
  };

  document.addEventListener('astro:page-load', trackPage);
  document.addEventListener('visibilitychange', handleVisibilityChange);
  document.addEventListener('click', handleClick);
  window.addEventListener('pagehide', handlePageHide);

  trackPage();
  startHeartbeat();

  analyticsWindow.__hecateAnalyticsCleanup = () => {
    stopHeartbeat();
    document.removeEventListener('astro:page-load', trackPage);
    document.removeEventListener('visibilitychange', handleVisibilityChange);
    document.removeEventListener('click', handleClick);
    window.removeEventListener('pagehide', handlePageHide);
    analyticsWindow.__hecateAnalyticsInitialized = false;
  };
}
