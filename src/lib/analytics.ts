type AnalyticsProperties = Record<
  string,
  string | number | boolean | null | undefined
>;

type AnalyticsWindow = Window & {
  __hecateAnalyticsInitialized?: boolean;
  __hecateAnalyticsCleanup?: () => void;
};

const API_BASE = String(import.meta.env.PUBLIC_STATS_API_URL ?? '').replace(
  /\/$/,
  '',
);
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
  updateLocalStats((stats) => {
    stats.interactions += 1;
    stats.events[name] = (stats.events[name] ?? 0) + 1;
  });

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

    heartbeatTimer = window.setInterval(sendHeartbeat, 45_000);
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
