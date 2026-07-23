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

const BOT_PATTERN =
  /bot|crawler|spider|crawling|headless|preview|facebookexternalhit|slackbot|discordbot|whatsapp|telegrambot|uptimerobot/i;

export default {
  async scheduled(_controller, env, context) {
    env = withDatabaseBinding(env);

    context.waitUntil(
      env.hecate_stats.batch([
        env.hecate_stats.prepare(
          `DELETE FROM daily_visitors WHERE day < date('now', '-2 day')`,
        ),
        env.hecate_stats.prepare(
          `DELETE FROM daily_sessions WHERE day < date('now', '-2 day')`,
        ),
        env.hecate_stats.prepare(
          `DELETE FROM sessions WHERE last_seen < datetime('now', '-30 day')`,
        ),
      ]),
    );
  },

  async fetch(request, env) {
    env = withDatabaseBinding(env);

    const url = new URL(request.url);

    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: corsHeaders(request, env),
      });
    }

    if (url.pathname === '/health' && request.method === 'GET') {
      return json(
        {
          ok: true,
          service: 'hecate-stats',
          storage: 'Cloudflare D1',
          time: new Date().toISOString(),
        },
        200,
        request,
        env,
      );
    }

    if (url.pathname === '/api/event' && request.method === 'POST') {
      return ingestEvent(request, env);
    }

    if (url.pathname === '/api/stats' && request.method === 'GET') {
      return readStats(request, env, url);
    }

    return json({ error: 'Not found' }, 404, request, env);
  },
};

function withDatabaseBinding(env) {
  const database = env.hecate_stats ?? env.DB;

  if (!database) {
    throw new Error(
      'D1 binding is missing. Set the Wrangler D1 binding to "hecate_stats" or "DB".',
    );
  }

  const runtimeEnv = Object.create(env);
  runtimeEnv.hecate_stats = database;
  return runtimeEnv;
}

async function ingestEvent(request, env) {
  const origin = request.headers.get('Origin');
  if (!isAllowedOrigin(origin, env)) {
    return json({ error: 'Origin not allowed' }, 403, request, env);
  }

  const contentLength = Number(request.headers.get('Content-Length') ?? 0);
  if (contentLength > 4096) {
    return json({ error: 'Payload too large' }, 413, request, env);
  }

  const userAgent = request.headers.get('User-Agent') ?? '';
  if (!userAgent || BOT_PATTERN.test(userAgent)) {
    return json({ accepted: false, reason: 'bot' }, 202, request, env);
  }

  let body;
  try {
    body = JSON.parse(await request.text());
  } catch {
    return json({ error: 'Invalid JSON' }, 400, request, env);
  }

  const eventName = sanitizeEventName(body?.name);
  const path = sanitizePath(body?.path);
  const visitorId = sanitizeId(body?.visitorId);
  const sessionId = sanitizeId(body?.sessionId);

  if (!eventName || !visitorId || !sessionId) {
    return json({ error: 'Invalid event' }, 400, request, env);
  }

  const now = new Date();
  const timestamp = now.toISOString();
  const day = timestamp.slice(0, 10);
  const visitorHash = await hashIdentifier(`visitor:${visitorId}`, env);
  const sessionHash = await hashIdentifier(`session:${sessionId}`, env);

  if (eventName === 'page_view' && !path) {
    return json({ error: 'Page view requires a valid path' }, 400, request, env);
  }

  if (eventName === 'heartbeat') {
    await env.hecate_stats.batch([
      env.hecate_stats.prepare(
        `UPDATE visitors
         SET last_seen = ?
         WHERE visitor_hash = ?`,
      ).bind(timestamp, visitorHash),
      env.hecate_stats.prepare(
        `UPDATE sessions
         SET last_seen = ?
         WHERE session_hash = ? AND visitor_hash = ?`,
      ).bind(timestamp, sessionHash, visitorHash),
    ]);

    return json({ accepted: true }, 202, request, env);
  }

  await upsertEventCount(env.hecate_stats, eventName, timestamp);

  if (eventName !== 'page_view') {
    await env.hecate_stats.batch([
      env.hecate_stats.prepare(
        `UPDATE visitors
         SET last_seen = ?
         WHERE visitor_hash = ?`,
      ).bind(timestamp, visitorHash),
      env.hecate_stats.prepare(
        `UPDATE sessions
         SET last_seen = ?
         WHERE session_hash = ? AND visitor_hash = ?`,
      ).bind(timestamp, sessionHash, visitorHash),
      env.hecate_stats.prepare(
        `UPDATE totals
         SET events = events + 1,
             first_event_at = COALESCE(first_event_at, ?),
             updated_at = ?
         WHERE id = 1`,
      ).bind(timestamp, timestamp),
      env.hecate_stats.prepare(
        `INSERT INTO daily_stats (day, events)
         VALUES (?, 1)
         ON CONFLICT(day) DO UPDATE SET events = events + 1`,
      ).bind(day),
    ]);

    return json({ accepted: true }, 202, request, env);
  }

  const newVisitorResult = await env.hecate_stats.prepare(
    `INSERT OR IGNORE INTO visitors (visitor_hash, first_seen, last_seen)
     VALUES (?, ?, ?)`,
  )
    .bind(visitorHash, timestamp, timestamp)
    .run();
  const isNewVisitor = changedRows(newVisitorResult) > 0;

  if (!isNewVisitor) {
    await env.hecate_stats.prepare(
      `UPDATE visitors SET last_seen = ? WHERE visitor_hash = ?`,
    )
      .bind(timestamp, visitorHash)
      .run();
  }

  const newSessionResult = await env.hecate_stats.prepare(
    `INSERT OR IGNORE INTO sessions
      (session_hash, visitor_hash, first_seen, last_seen, page_views)
     VALUES (?, ?, ?, ?, 1)`,
  )
    .bind(sessionHash, visitorHash, timestamp, timestamp)
    .run();
  const isNewSession = changedRows(newSessionResult) > 0;

  if (!isNewSession) {
    await env.hecate_stats.prepare(
      `UPDATE sessions
       SET last_seen = ?, page_views = page_views + 1
       WHERE session_hash = ?`,
    )
      .bind(timestamp, sessionHash)
      .run();
  }

  const dailyVisitorResult = await env.hecate_stats.prepare(
    `INSERT OR IGNORE INTO daily_visitors (day, visitor_hash) VALUES (?, ?)`,
  )
    .bind(day, visitorHash)
    .run();
  const isNewDailyVisitor = changedRows(dailyVisitorResult) > 0;

  const dailySessionResult = await env.hecate_stats.prepare(
    `INSERT OR IGNORE INTO daily_sessions (day, session_hash) VALUES (?, ?)`,
  )
    .bind(day, sessionHash)
    .run();
  const isNewDailySession = changedRows(dailySessionResult) > 0;

  await env.hecate_stats.batch([
    env.hecate_stats.prepare(
      `UPDATE totals
       SET page_views = page_views + 1,
           events = events + 1,
           estimated_visitors = estimated_visitors + ?,
           sessions = sessions + ?,
           first_event_at = COALESCE(first_event_at, ?),
           updated_at = ?
       WHERE id = 1`,
    ).bind(
      isNewVisitor ? 1 : 0,
      isNewSession ? 1 : 0,
      timestamp,
      timestamp,
    ),
    env.hecate_stats.prepare(
      `INSERT INTO daily_stats
        (day, page_views, events, estimated_visitors, sessions)
       VALUES (?, 1, 1, ?, ?)
       ON CONFLICT(day) DO UPDATE SET
         page_views = page_views + 1,
         events = events + 1,
         estimated_visitors = estimated_visitors + excluded.estimated_visitors,
         sessions = sessions + excluded.sessions`,
    ).bind(day, isNewDailyVisitor ? 1 : 0, isNewDailySession ? 1 : 0),
    env.hecate_stats.prepare(
      `INSERT INTO page_stats (path, page_views, updated_at)
       VALUES (?, 1, ?)
       ON CONFLICT(path) DO UPDATE SET
         page_views = page_views + 1,
         updated_at = excluded.updated_at`,
    ).bind(path, timestamp),
  ]);

  const location = readApproximateLocation(request);
  if (location) {
    // Keep one current public location mapping per anonymous visitor. This also
    // removes an older one-decimal mapping after the visitor returns.
    await env.hecate_stats.prepare(
      `DELETE FROM visitor_locations
       WHERE visitor_hash = ? AND location_key <> ?`,
    )
      .bind(visitorHash, location.key)
      .run();

    const newVisitorLocationResult = await env.hecate_stats.prepare(
      `INSERT OR IGNORE INTO visitor_locations (visitor_hash, location_key)
       VALUES (?, ?)`,
    )
      .bind(visitorHash, location.key)
      .run();

    await env.hecate_stats.prepare(
      `INSERT INTO location_stats (
        location_key, city, region, country, country_code,
        latitude, longitude, page_views, estimated_visitors, updated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
      ON CONFLICT(location_key) DO UPDATE SET
        page_views = page_views + 1,
        estimated_visitors = estimated_visitors + excluded.estimated_visitors,
        updated_at = excluded.updated_at`,
    )
      .bind(
        location.key,
        location.city,
        location.region,
        location.country,
        location.countryCode,
        location.latitude,
        location.longitude,
        changedRows(newVisitorLocationResult) > 0 ? 1 : 0,
        timestamp,
      )
      .run();
  }

  return json({ accepted: true }, 202, request, env);
}

async function readStats(request, env, url) {
  const days = clampInteger(url.searchParams.get('days'), 7, 365, 30);
  // Each anonymous visitor-location row is public as its own dot.
  // Raw IP addresses are never stored; Cloudflare's approximate coordinates
  // are retained to four decimal places.
  const cutoff = new Date(Date.now() - 2 * 60 * 1000).toISOString();

  const [
    totals,
    active,
    dailyResult,
    pageResult,
    interactionResult,
    locationResult,
    countryResult,
  ] = await Promise.all([
    env.hecate_stats.prepare('SELECT * FROM totals WHERE id = 1').first(),
    env.hecate_stats.prepare(
      `SELECT COUNT(DISTINCT visitor_hash) AS count
       FROM sessions WHERE last_seen >= ?`,
    )
      .bind(cutoff)
      .first(),
    env.hecate_stats.prepare(
      `SELECT day, page_views, events, estimated_visitors
       FROM daily_stats
       WHERE day >= date('now', ?)
       ORDER BY day ASC`,
    )
      .bind(`-${days - 1} day`)
      .all(),
    env.hecate_stats.prepare(
      `SELECT path AS label, page_views AS value
       FROM page_stats
       ORDER BY page_views DESC, path ASC
       LIMIT 10`,
    ).all(),
    env.hecate_stats.prepare(
      `SELECT event_name AS label, total AS value
       FROM event_stats
       WHERE event_name <> 'page_view'
       ORDER BY total DESC, event_name ASC
       LIMIT 10`,
    ).all(),
    env.hecate_stats.prepare(
      `WITH point_rows AS (
         SELECT
           locations.location_key,
           locations.city,
           locations.region,
           locations.country,
           locations.country_code,
           locations.latitude,
           locations.longitude,
           locations.updated_at,
           ROW_NUMBER() OVER (
             PARTITION BY locations.location_key
             ORDER BY visitor_locations.visitor_hash
           ) - 1 AS point_index,
           COUNT(*) OVER (
             PARTITION BY locations.location_key
           ) AS point_count
         FROM visitor_locations
         INNER JOIN location_stats AS locations
           ON locations.location_key = visitor_locations.location_key
       )
       SELECT
         city,
         region,
         country,
         country_code,
         latitude,
         longitude,
         point_index,
         point_count
       FROM point_rows
       WHERE point_count >= 1
       ORDER BY updated_at DESC, location_key ASC, point_index ASC
       LIMIT 2000`,
    ).all(),
    env.hecate_stats.prepare(
      `SELECT COUNT(DISTINCT locations.country_code) AS count
       FROM visitor_locations
       INNER JOIN location_stats AS locations
         ON locations.location_key = visitor_locations.location_key
       WHERE locations.country_code IS NOT NULL`,
    ).first(),
  ]);

  const locations = locationResult.results.map((row) => ({
    city: row.city ?? null,
    region: row.region ?? null,
    country: row.country ?? null,
    countryCode: row.country_code ?? null,
    latitude: Number(row.latitude),
    longitude: Number(row.longitude),
    pageViews: 1,
    estimatedVisitors: 1,
    pointIndex: Number(row.point_index ?? 0),
    pointCount: Number(row.point_count ?? 1),
  }));

  const response = {
    summary: {
      pageViews: Number(totals?.page_views ?? 0),
      estimatedVisitors: Number(totals?.estimated_visitors ?? 0),
      sessions: Number(totals?.sessions ?? 0),
      trackedRequests: Number(totals?.events ?? 0),
      countries: Number(countryResult?.count ?? 0),
      visibleLocations: locations.length,
      activeVisitors: Number(active?.count ?? 0),
      firstEventAt: totals?.first_event_at ?? null,
      updatedAt: totals?.updated_at ?? null,
    },
    daily: fillDailyRows(dailyResult.results, days),
    pages: pageResult.results.map((row) => ({
      label: row.label,
      value: Number(row.value ?? 0),
    })),
    interactions: interactionResult.results.map((row) => ({
      label: row.label,
      value: Number(row.value ?? 0),
    })),
    locations,
  };

  return json(response, 200, request, env, {
    'Cache-Control': 'no-store',
  });
}

function fillDailyRows(rows, days) {
  const byDay = new Map(rows.map((row) => [row.day, row]));
  const result = [];
  const today = new Date();
  today.setUTCHours(0, 0, 0, 0);

  for (let offset = days - 1; offset >= 0; offset -= 1) {
    const date = new Date(today);
    date.setUTCDate(today.getUTCDate() - offset);
    const day = date.toISOString().slice(0, 10);
    const row = byDay.get(day);

    result.push({
      day,
      pageViews: Number(row?.page_views ?? 0),
      estimatedVisitors: Number(row?.estimated_visitors ?? 0),
      events: Number(row?.events ?? 0),
    });
  }

  return result;
}

async function upsertEventCount(db, eventName, timestamp) {
  await db
    .prepare(
      `INSERT INTO event_stats (event_name, total, updated_at)
       VALUES (?, 1, ?)
       ON CONFLICT(event_name) DO UPDATE SET
         total = total + 1,
         updated_at = excluded.updated_at`,
    )
    .bind(eventName, timestamp)
    .run();
}

function readApproximateLocation(request) {
  const cf = request.cf;
  const latitude = Number(cf?.latitude);
  const longitude = Number(cf?.longitude);

  if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null;

  const roundedLatitude = Math.round(latitude * 10_000) / 10_000;
  const roundedLongitude = Math.round(longitude * 10_000) / 10_000;
  const city = cleanText(cf?.city, 80);
  const region = cleanText(cf?.region, 80);
  const country = cleanText(cf?.country, 80);
  const countryCode = cleanText(cf?.country, 3)?.toUpperCase() ?? null;
  const key = [
    countryCode ?? 'XX',
    region ?? '',
    city ?? '',
    roundedLatitude.toFixed(4),
    roundedLongitude.toFixed(4),
  ].join('|');

  return {
    key,
    city,
    region,
    country,
    countryCode,
    latitude: roundedLatitude,
    longitude: roundedLongitude,
  };
}

async function hashIdentifier(value, env) {
  if (!env.VISITOR_SALT) {
    throw new Error('VISITOR_SALT is not configured.');
  }

  const bytes = new TextEncoder().encode(`${env.VISITOR_SALT}:${value}`);
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, '0'),
  ).join('');
}

function sanitizeEventName(value) {
  return typeof value === 'string' && EVENT_NAMES.has(value) ? value : null;
}

function sanitizePath(value) {
  if (typeof value !== 'string') return null;
  const path = value.trim().split('?')[0].split('#')[0];
  if (!path.startsWith('/') || path.length > 200) return null;
  return path;
}

function sanitizeId(value) {
  if (typeof value !== 'string') return null;
  const id = value.trim();
  return /^[A-Za-z0-9-]{16,100}$/.test(id) ? id : null;
}

function cleanText(value, maximumLength) {
  if (typeof value !== 'string') return null;
  const cleaned = value.trim().replace(/[\u0000-\u001f\u007f]/g, '');
  return cleaned ? cleaned.slice(0, maximumLength) : null;
}

function clampInteger(value, minimum, maximum, fallback) {
  const parsed = Number.parseInt(String(value ?? ''), 10);
  if (!Number.isFinite(parsed)) return fallback;
  return Math.min(maximum, Math.max(minimum, parsed));
}

function changedRows(result) {
  return Number(result?.meta?.changes ?? result?.meta?.changed_db ?? 0);
}

function allowedOrigins(env) {
  return String(env.ALLOWED_ORIGINS ?? '')
    .split(',')
    .map((origin) => origin.trim())
    .filter(Boolean);
}

function isAllowedOrigin(origin, env) {
  if (!origin) return false;
  return allowedOrigins(env).includes(origin);
}

function corsHeaders(request, env) {
  const origin = request.headers.get('Origin');
  const allowedOrigin = isAllowedOrigin(origin, env) ? origin : 'null';

  return {
    'Access-Control-Allow-Origin': allowedOrigin,
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
    Vary: 'Origin',
  };
}

function json(payload, status, request, env, extraHeaders = {}) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'X-Content-Type-Options': 'nosniff',
      ...corsHeaders(request, env),
      ...extraHeaders,
    },
  });
}
