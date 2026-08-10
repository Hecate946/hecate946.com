import { createHash } from 'node:crypto';
import { mkdir, readFile, rename, writeFile } from 'node:fs/promises';
import path from 'node:path';

const API_PREFIX = '/__local-stats';
const EVENT_NAMES = new Set([
  'page_view',
  'heartbeat',
  'resume_download',
  'project_open',
  'graph_drag',
  'graph_node_opened',
  'command_palette_opened',
  'site_search',
  'theme_change',
  'color_theme_changed',
  'season_changed',
  'outbound_click',
]);

function emptyStore() {
  return {
    version: 1,
    firstEventAt: null,
    updatedAt: null,
    visitors: {},
    sessions: {},
    daily: {},
    pages: {},
    events: {},
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

function statsResponse(store, days) {
  const activeCutoff = Date.now() - 5 * 60 * 1000;
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

  return {
    summary: {
      pageViews,
      estimatedVisitors: Object.keys(store.visitors).length,
      sessions: Object.keys(store.sessions).length,
      trackedRequests,
      countries: 0,
      visibleLocations: 0,
      activeVisitors: activeVisitors.size,
      firstEventAt: store.firstEventAt,
      updatedAt: store.updatedAt,
    },
    daily: fillDailyRows(store, days),
    pages,
    interactions,
    // Local development deliberately does not geolocate the developer. Doing so
    // would either require a permission prompt or an external production service.
    locations: [],
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
        store = { ...emptyStore(), ...JSON.parse(raw) };
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

        if (requestUrl.pathname === `${API_PREFIX}/api/stats` && req.method === 'GET') {
          const days = clampInteger(requestUrl.searchParams.get('days'), 7, 365, 30);
          sendJson(res, 200, statsResponse(store, days));
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
