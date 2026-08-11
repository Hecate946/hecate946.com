import { resolveStatsApiBase } from '@/lib/stats-api';

type AnalyticsProperties = Record<
  string,
  string | number | boolean | null | undefined
>;

type AnalyticsWindow = Window & {
  __hecateAnalyticsInitialized?: boolean;
  __hecateAnalyticsCleanup?: () => void;
};

/* Remote analytics deliberately uses sessionStorage only. There is no
 * persistent cross-session visitor identifier, fingerprint, cookie, referrer,
 * or browser/device profile. */
const SESSION_KEY = 'hecate946:analytics-session';
const LOCAL_STATS_KEY = 'hecate946:your-stats';
const LOCAL_PATH_HISTORY_LIMIT = 160;

interface LocalPathEntry {
  path: string;
  at: string;
  session: string;
}

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
  pathHistory: LocalPathEntry[];
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
    pathHistory: [],
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
    // Personal browser statistics are optional and never affect navigation.
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

  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`;
}

function getSessionId(key: string) {
  try {
    const existing = window.sessionStorage.getItem(key);
    if (existing) return existing;

    const next = createId();
    window.sessionStorage.setItem(key, next);
    return next;
  } catch {
    return createId();
  }
}

function analyticsDisabled() {
  if (typeof window === 'undefined') return true;
  const legacyDoNotTrack = (window as Window & { doNotTrack?: string }).doNotTrack;
  const globalPrivacyControl = (
    navigator as Navigator & { globalPrivacyControl?: boolean }
  ).globalPrivacyControl;

  return (
    navigator.doNotTrack === '1' ||
    legacyDoNotTrack === '1' ||
    globalPrivacyControl === true
  );
}

function sendRemoteEvent(
  name: string,
  properties: AnalyticsProperties = {},
) {
  if (analyticsDisabled()) return;

  const apiBase = resolveStatsApiBase();
  if (!apiBase) return;

  let eventProperties = properties;

  // Local development gets only a coarse timezone hint so the local visitor
  // map can be exercised without geolocation permission or production calls.
  if (apiBase.startsWith('/')) {
    try {
      const localTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone ?? '';
      if (localTimeZone) {
        eventProperties = { ...properties, __localTimeZone: localTimeZone };
      }
    } catch {
      // Optional dev-only hint.
    }
  }

  const sessionId = getSessionId(SESSION_KEY);
  const payload = JSON.stringify({
    name,
    path: window.location.pathname,
    // The analytics backend requires visitor + session fields, but both are the
    // same session-scoped random value. There is no cross-session identifier.
    visitorId: sessionId,
    sessionId,
    properties: eventProperties,
  });

  void fetch(`${apiBase}/api/event`, {
    method: 'POST',
    headers: { 'Content-Type': 'text/plain;charset=UTF-8' },
    body: payload,
    keepalive: true,
    mode: 'cors',
    credentials: 'omit',
    referrerPolicy: 'no-referrer',
  })
    .then((response) => {
      if (response.ok && apiBase.startsWith('/') && name === 'page_view') {
        window.dispatchEvent(new CustomEvent('hecate:local-backend-stats-updated'));
      }
    })
    .catch(() => {
      // Analytics is optional and must never interfere with the site.
    });
}

export function trackEvent(
  name: string,
  properties: AnalyticsProperties = {},
) {
  updateLocalStats((stats) => {
    if (name !== 'page_view') stats.interactions += 1;
    stats.events[name] = (stats.events[name] ?? 0) + 1;
  });

  sendRemoteEvent(name, properties);
}

export function initAnalytics() {
  const analyticsWindow = window as AnalyticsWindow;
  if (analyticsWindow.__hecateAnalyticsInitialized) return;
  analyticsWindow.__hecateAnalyticsInitialized = true;

  let lastTrackedPath = '';
  let activeStartedAt = document.visibilityState === 'visible' ? Date.now() : 0;

  updateLocalStats((stats) => {
    stats.visits += 1;
  });

  const trackPage = () => {
    const path = window.location.pathname;
    if (path === lastTrackedPath) return;
    lastTrackedPath = path;

    const sessionId = getSessionId(SESSION_KEY);
    const visitedAt = new Date().toISOString();

    updateLocalStats((stats) => {
      stats.pageViews += 1;
      stats.pages[path] = (stats.pages[path] ?? 0) + 1;

      if (!Array.isArray(stats.pathHistory)) stats.pathHistory = [];
      const previous = stats.pathHistory.at(-1);
      if (!previous || previous.path !== path || previous.session !== sessionId) {
        stats.pathHistory.push({ path, at: visitedAt, session: sessionId });
        if (stats.pathHistory.length > LOCAL_PATH_HISTORY_LIMIT) {
          stats.pathHistory = stats.pathHistory.slice(-LOCAL_PATH_HISTORY_LIMIT);
        }
      }
    });

    sendRemoteEvent('page_view');
  };

  const sendPresenceHeartbeat = () => {
    if (document.visibilityState !== 'visible') return;
    sendRemoteEvent('heartbeat');
  };

  const presenceInterval = window.setInterval(sendPresenceHeartbeat, 60_000);

  const saveActiveTime = () => {
    if (!activeStartedAt) return;
    const elapsed = Math.max(0, Math.round((Date.now() - activeStartedAt) / 1000));
    activeStartedAt = 0;
    if (elapsed) {
      updateLocalStats((stats) => {
        stats.activeSeconds += elapsed;
      });
    }
  };

  const handleVisibilityChange = () => {
    if (document.visibilityState === 'visible') {
      activeStartedAt = Date.now();
      sendPresenceHeartbeat();
    } else {
      saveActiveTime();
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
  };

  document.addEventListener('astro:page-load', trackPage);
  document.addEventListener('visibilitychange', handleVisibilityChange);
  document.addEventListener('click', handleClick);
  window.addEventListener('pagehide', handlePageHide);

  trackPage();

  analyticsWindow.__hecateAnalyticsCleanup = () => {
    window.clearInterval(presenceInterval);
    document.removeEventListener('astro:page-load', trackPage);
    document.removeEventListener('visibilitychange', handleVisibilityChange);
    document.removeEventListener('click', handleClick);
    window.removeEventListener('pagehide', handlePageHide);
    analyticsWindow.__hecateAnalyticsInitialized = false;
  };
}
