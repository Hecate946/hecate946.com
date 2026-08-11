import { createHash } from 'node:crypto';
import { mkdir, readFile, rename, writeFile } from 'node:fs/promises';
import path from 'node:path';

const API_PREFIX = '/__local-stats';
const PRODUCTION_STATS_URL = 'https://hecate-stats.hecate946.workers.dev/api/stats';
const EVENT_NAMES = new Set([
  'page_view',
  'heartbeat',
  'resume_download',
  'command_palette_opened',
  'color_theme_changed',
  'season_changed',
]);

function emptyStore() {
  return {
    version: 2,
    firstEventAt: null,
    updatedAt: null,
    visitors: {},
    sessions: {},
    daily: {},
    pages: {},
    events: {},
    visitorLocations: {},
  };
}

const LOCAL_TIMEZONE_POINTS = new Map([
  ['America/Los_Angeles', [37.0, -120.0, 'Pacific Time']],
  ['America/Vancouver', [49.25, -123.1, 'Pacific Time']],
  ['America/Phoenix', [33.45, -112.07, 'Arizona Time']],
  ['America/Denver', [39.0, -106.0, 'Mountain Time']],
  ['America/Chicago', [39.0, -97.0, 'Central Time']],
  ['America/New_York', [39.0, -77.0, 'Eastern Time']],
  ['America/Toronto', [43.65, -79.38, 'Eastern Time']],
  ['America/Anchorage', [61.2, -149.9, 'Alaska Time']],
  ['Pacific/Honolulu', [21.31, -157.86, 'Hawaii Time']],
  ['America/Mexico_City', [19.43, -99.13, 'Central Mexico Time']],
  ['America/Sao_Paulo', [-23.55, -46.63, 'Brasília Time']],
  ['America/Buenos_Aires', [-34.6, -58.38, 'Argentina Time']],
  ['Europe/London', [51.51, -0.13, 'UK Time']],
  ['Europe/Paris', [48.86, 2.35, 'Central European Time']],
  ['Europe/Berlin', [52.52, 13.4, 'Central European Time']],
  ['Europe/Madrid', [40.42, -3.7, 'Central European Time']],
  ['Europe/Rome', [41.9, 12.5, 'Central European Time']],
  ['Europe/Amsterdam', [52.37, 4.9, 'Central European Time']],
  ['Europe/Warsaw', [52.23, 21.01, 'Central European Time']],
  ['Europe/Moscow', [55.76, 37.62, 'Moscow Time']],
  ['Asia/Jerusalem', [31.78, 35.22, 'Israel Time']],
  ['Asia/Dubai', [25.2, 55.27, 'Gulf Time']],
  ['Asia/Kolkata', [22.57, 88.36, 'India Time']],
  ['Asia/Singapore', [1.35, 103.82, 'Singapore Time']],
  ['Asia/Hong_Kong', [22.32, 114.17, 'Hong Kong Time']],
  ['Asia/Shanghai', [31.23, 121.47, 'China Time']],
  ['Asia/Seoul', [37.57, 126.98, 'Korea Time']],
  ['Asia/Tokyo', [35.68, 139.76, 'Japan Time']],
  ['Australia/Perth', [-31.95, 115.86, 'Western Australia Time']],
  ['Australia/Adelaide', [-34.93, 138.6, 'Central Australia Time']],
  ['Australia/Sydney', [-33.87, 151.21, 'Eastern Australia Time']],
  ['Australia/Melbourne', [-37.81, 144.96, 'Eastern Australia Time']],
  ['Pacific/Auckland', [-36.85, 174.76, 'New Zealand Time']],
  ['Africa/Cairo', [30.04, 31.24, 'Egypt Time']],
  ['Africa/Johannesburg', [-26.2, 28.05, 'South Africa Time']],
  ['Africa/Lagos', [6.52, 3.38, 'West Africa Time']],
  ['Africa/Nairobi', [-1.29, 36.82, 'East Africa Time']],
  ['Etc/UTC', [0, 0, 'UTC']],
  ['UTC', [0, 0, 'UTC']],
]);

const LOCAL_TIMEZONE_FALLBACKS = [
  ['America/', [39, -98, 'Americas timezone']],
  ['Europe/', [50, 10, 'European timezone']],
  ['Africa/', [3, 20, 'African timezone']],
  ['Asia/', [34, 100, 'Asian timezone']],
  ['Australia/', [-25, 134, 'Australian timezone']],
  ['Pacific/', [-12, 170, 'Pacific timezone']],
  ['Indian/', [-12, 75, 'Indian Ocean timezone']],
];

function readLocalApproximateLocation(body) {
  const rawTimeZone = body?.properties?.__localTimeZone;
  if (typeof rawTimeZone !== 'string') return null;

  const timeZone = rawTimeZone.trim().slice(0, 80);
  if (!/^[A-Za-z0-9_+\-/]+$/.test(timeZone)) return null;

  let point = LOCAL_TIMEZONE_POINTS.get(timeZone);
  if (!point) {
    const fallback = LOCAL_TIMEZONE_FALLBACKS.find(([prefix]) =>
      timeZone.startsWith(prefix),
    );
    point = fallback?.[1];
  }
  if (!point) return null;

  const [latitude, longitude, label] = point;
  return {
    key: `timezone:${timeZone}`,
    city: null,
    region: `${label} · local`,
    country: 'Local development',
    countryCode: null,
    latitude,
    longitude,
    timeZone,
  };
}

function sanitizeEventName(value) {
  return typeof value === 'string' && EVENT_NAMES.has(value) ? value : null;
}

function sanitizePath(value) {
  if (typeof value !== 'string') return null;
  const cleaned = value.trim().split('?')[0].split('#')[0];
  if (!cleaned.startsWith('/') || cleaned.length > 200) return null;
  return cleaned;
}

function sanitizeId(value) {
  if (typeof value !== 'string') return null;
  const cleaned = value.trim();
  return /^[A-Za-z0-9-]{16,100}$/.test(cleaned) ? cleaned : null;
}

function hashId(kind, value) {
  return createHash('sha256')
    .update(`hecate946-local-stats-v1:${kind}:${value}`)
    .digest('hex');
}

function clampInteger(value, minimum, maximum, fallback) {
  const parsed = Number.parseInt(String(value ?? ''), 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(maximum, Math.max(minimum, parsed));
}

function dateKey(timestamp) {
  return timestamp.slice(0, 10);
}

function ensureDaily(store, day) {
  store.daily[day] ??= {
    pageViews: 0,
    events: 0,
    visitors: [],
    sessions: [],
  };
  return store.daily[day];
}

function touchIdentity(store, visitorHash, sessionHash, timestamp, pageView) {
  if (!store.visitors[visitorHash]) {
    store.visitors[visitorHash] = {
      firstSeen: timestamp,
      lastSeen: timestamp,
    };
  } else {
    store.visitors[visitorHash].lastSeen = timestamp;
  }

  if (!store.sessions[sessionHash]) {
    store.sessions[sessionHash] = {
      visitorHash,
      firstSeen: timestamp,
      lastSeen: timestamp,
      pageViews: pageView ? 1 : 0,
    };
  } else {
    store.sessions[sessionHash].lastSeen = timestamp;
    if (pageView) store.sessions[sessionHash].pageViews += 1;
  }
}

function recordEvent(store, body) {
  const eventName = sanitizeEventName(body?.name);
  const visitorId = sanitizeId(body?.visitorId);
  const sessionId = sanitizeId(body?.sessionId);
  const page = sanitizePath(body?.path);

  if (!eventName || !visitorId || !sessionId) {
    return { status: 400, body: { error: 'Invalid event' } };
  }

  if (eventName === 'page_view' && !page) {
    return { status: 400, body: { error: 'Page view requires a valid path' } };
  }

  const timestamp = new Date().toISOString();
  const visitorHash = hashId('visitor', visitorId);
  const sessionHash = hashId('session', sessionId);

  if (eventName === 'heartbeat') {
    if (store.visitors[visitorHash]) store.visitors[visitorHash].lastSeen = timestamp;
    if (store.sessions[sessionHash]) store.sessions[sessionHash].lastSeen = timestamp;
    store.updatedAt = timestamp;
    return { status: 202, body: { accepted: true } };
  }

  touchIdentity(store, visitorHash, sessionHash, timestamp, eventName === 'page_view');

  if (eventName === 'page_view') {
    const approximateLocation = readLocalApproximateLocation(body);
    if (approximateLocation) {
      store.visitorLocations ??= {};
      store.visitorLocations[visitorHash] = {
        ...approximateLocation,
        updatedAt: timestamp,
      };
    }
  }

  store.firstEventAt ??= timestamp;
  store.updatedAt = timestamp;
  store.events[eventName] = (store.events[eventName] ?? 0) + 1;

  const day = ensureDaily(store, dateKey(timestamp));
  day.events += 1;

  if (eventName === 'page_view') {
    day.pageViews += 1;
    if (!day.visitors.includes(visitorHash)) day.visitors.push(visitorHash);
    if (!day.sessions.includes(sessionHash)) day.sessions.push(sessionHash);

    store.pages[page] ??= { pageViews: 0, updatedAt: timestamp };
    store.pages[page].pageViews += 1;
    store.pages[page].updatedAt = timestamp;
  }

  return { status: 202, body: { accepted: true } };
}

function fillDailyRows(store, days) {
  const result = [];
  const today = new Date();
  today.setUTCHours(0, 0, 0, 0);

  for (let offset = days - 1; offset >= 0; offset -= 1) {
    const date = new Date(today);
    date.setUTCDate(today.getUTCDate() - offset);
    const dayKey = date.toISOString().slice(0, 10);
    const row = store.daily[dayKey];

    result.push({
      day: dayKey,
      pageViews: Number(row?.pageViews ?? 0),
      estimatedVisitors: Array.isArray(row?.visitors) ? row.visitors.length : 0,
      events: Number(row?.events ?? 0),
    });
  }

  return result;
}

function rankedEntries(record, mapper, limit = 10) {
  return Object.entries(record)
    .map(mapper)
    .sort((a, b) => b.value - a.value || String(a.label).localeCompare(String(b.label)))
    .slice(0, limit);
}

function buildLocalLocations(store) {
  const groups = new Map();

  for (const [visitorHash, location] of Object.entries(store.visitorLocations ?? {})) {
    if (!store.visitors?.[visitorHash]) continue;
    if (!Number.isFinite(location?.latitude) || !Number.isFinite(location?.longitude)) {
      continue;
    }

    const key = location.key ?? `${location.latitude}:${location.longitude}`;
    const existing = groups.get(key);
    if (existing) {
      existing.visitors += 1;
      continue;
    }

    groups.set(key, {
      city: location.city ?? null,
      region: location.region ?? null,
      country: location.country ?? null,
      countryCode: location.countryCode ?? null,
      latitude: Number(location.latitude),
      longitude: Number(location.longitude),
      visitors: 1,
      updatedAt: location.updatedAt ?? null,
    });
  }

  const rows = [];
  const sortedGroups = [...groups.values()].sort((a, b) =>
    String(b.updatedAt ?? '').localeCompare(String(a.updatedAt ?? '')),
  );

  for (const group of sortedGroups) {
    for (let pointIndex = 0; pointIndex < group.visitors; pointIndex += 1) {
      rows.push({
        city: group.city,
        region: group.region,
        country: group.country,
        countryCode: group.countryCode,
        latitude: group.latitude,
        longitude: group.longitude,
        pageViews: 1,
        estimatedVisitors: 1,
        pointIndex,
        pointCount: group.visitors,
      });
    }
  }

  return rows;
}

function fillHourlyRows(store, utcOffsetMinutes = 0) {
  const hours = Array.from({ length: 24 }, (_, hour) => ({ hour, value: 0 }));
  const offsetMs = utcOffsetMinutes * 60 * 1000;

  for (const session of Object.values(store.sessions)) {
    const timestamp = Date.parse(session.firstSeen ?? '');
    if (!Number.isFinite(timestamp)) continue;
    hours[new Date(timestamp + offsetMs).getUTCHours()].value += 1;
  }

  return hours;
}

function statsResponse(store, days, utcOffsetMinutes = 0) {
  const activeCutoff = Date.now() - 2 * 60 * 1000;
  const activeVisitors = new Set();

  for (const session of Object.values(store.sessions)) {
    const lastSeen = Date.parse(session.lastSeen ?? '');
    if (Number.isFinite(lastSeen) && lastSeen >= activeCutoff) {
      activeVisitors.add(session.visitorHash);
    }
  }

  const pages = rankedEntries(
    store.pages,
    ([label, value]) => ({ label, value: Number(value?.pageViews ?? 0) }),
    250,
  );
  const interactions = Object.entries(store.events)
    .filter(([label]) => label !== 'page_view')
    .map(([label, value]) => ({ label, value: Number(value ?? 0) }))
    .sort((a, b) => b.value - a.value || a.label.localeCompare(b.label))
    .slice(0, 10);

  const pageViews = Object.values(store.pages).reduce(
    (sum, value) => sum + Number(value?.pageViews ?? 0),
    0,
  );
  const trackedRequests = Object.values(store.events).reduce(
    (sum, value) => sum + Number(value ?? 0),
    0,
  );
  const locations = buildLocalLocations(store);

  return {
    summary: {
      pageViews,
      estimatedVisitors: Object.keys(store.visitors).length,
      sessions: Object.keys(store.sessions).length,
      trackedRequests,
      // Local coordinates are deliberately coarse browser-timezone points, not
      // IP geolocation, so they are not presented as real country analytics.
      countries: 0,
      visibleLocations: locations.length,
      activeVisitors: activeVisitors.size,
      firstEventAt: store.firstEventAt,
      updatedAt: store.updatedAt,
    },
    daily: fillDailyRows(store, days),
    pages,
    interactions,
    hours: fillHourlyRows(store, utcOffsetMinutes),
    locations,
  };
}

function sendJson(res, status, payload) {
  const json = JSON.stringify(payload);
  res.statusCode = status;
  res.setHeader('Content-Type', 'application/json; charset=utf-8');
  res.setHeader('Cache-Control', 'no-store');
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.end(json);
}

async function readRequestBody(req, maximumBytes = 4096) {
  const chunks = [];
  let length = 0;

  for await (const chunk of req) {
    length += chunk.length;
    if (length > maximumBytes) throw new Error('Payload too large');
    chunks.push(chunk);
  }

  return Buffer.concat(chunks).toString('utf8');
}

export function localStatsDevPlugin() {
  const root = process.cwd();
  const cacheDir = path.join(root, '.cache');
  const dataFile = path.join(cacheDir, 'local-stats.json');
  const tempFile = `${dataFile}.tmp`;
  let store = emptyStore();
  let loaded = false;
  let loadPromise = null;
  let writeChain = Promise.resolve();

  async function ensureLoaded() {
    if (loaded) return;
    if (loadPromise) return loadPromise;

    loadPromise = (async () => {
      await mkdir(cacheDir, { recursive: true });
      try {
        const raw = await readFile(dataFile, 'utf8');
        const parsed = JSON.parse(raw);
        store = {
          ...emptyStore(),
          ...parsed,
          visitorLocations: parsed?.visitorLocations ?? {},
          version: 2,
        };
      } catch (error) {
        if (error?.code !== 'ENOENT') {
          console.warn('[local-stats] Could not read local cache; starting fresh.');
        }
        store = emptyStore();
      }
      loaded = true;
    })();

    return loadPromise;
  }

  function persist() {
    const snapshot = JSON.stringify(store, null, 2);
    writeChain = writeChain
      .then(async () => {
        await mkdir(cacheDir, { recursive: true });
        await writeFile(tempFile, snapshot, 'utf8');
        await rename(tempFile, dataFile);
      })
      .catch((error) => {
        console.warn('[local-stats] Could not persist local stats:', error.message);
      });
    return writeChain;
  }

  return {
    name: 'hecate-local-stats-dev',
    apply: 'serve',
    configureServer(server) {
      server.middlewares.use(async (req, res, next) => {
        const requestUrl = new URL(req.url ?? '/', 'http://localhost');
        if (!requestUrl.pathname.startsWith(API_PREFIX)) {
          next();
          return;
        }

        await ensureLoaded();


        if (requestUrl.pathname === `${API_PREFIX}/api/public-stats` && req.method === 'GET') {
          const days = clampInteger(requestUrl.searchParams.get('days'), 7, 365, 30);
          const utcOffsetMinutes = clampInteger(
            requestUrl.searchParams.get('utcOffsetMinutes'),
            -840,
            840,
            0,
          );
          try {
            const productionUrl = new URL(PRODUCTION_STATS_URL);
            productionUrl.searchParams.set('days', String(days));
            productionUrl.searchParams.set('utcOffsetMinutes', String(utcOffsetMinutes));
            const response = await fetch(productionUrl, {
              headers: { Accept: 'application/json' },
            });
            const body = await response.text();
            res.statusCode = response.status;
            res.setHeader('Content-Type', 'application/json; charset=utf-8');
            res.setHeader('Cache-Control', 'no-store');
            res.setHeader('X-Content-Type-Options', 'nosniff');
            res.end(body);
          } catch (error) {
            sendJson(res, 502, {
              error: `Could not read production stats: ${error instanceof Error ? error.message : String(error)}`,
            });
          }
          return;
        }

        if (requestUrl.pathname === `${API_PREFIX}/api/stats` && req.method === 'GET') {
          const days = clampInteger(requestUrl.searchParams.get('days'), 7, 365, 30);
          const utcOffsetMinutes = clampInteger(
            requestUrl.searchParams.get('utcOffsetMinutes'),
            -840,
            840,
            0,
          );
          sendJson(res, 200, statsResponse(store, days, utcOffsetMinutes));
          return;
        }

        if (requestUrl.pathname === `${API_PREFIX}/api/event` && req.method === 'POST') {
          try {
            const raw = await readRequestBody(req);
            const result = recordEvent(store, JSON.parse(raw));
            if (result.status < 400) void persist();
            sendJson(res, result.status, result.body);
          } catch (error) {
            const tooLarge = error instanceof Error && error.message === 'Payload too large';
            sendJson(res, tooLarge ? 413 : 400, {
              error: tooLarge ? 'Payload too large' : 'Invalid JSON',
            });
          }
          return;
        }

        if (req.method === 'OPTIONS') {
          res.statusCode = 204;
          res.end();
          return;
        }

        sendJson(res, 404, { error: 'Not found' });
      });
    },
  };
}
