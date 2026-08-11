const EVENT_NAMES = new Set([
  'page_view',
  'heartbeat',
  'resume_download',
  'command_palette_opened',
  'site_map_opened',
  'color_theme_changed',
  'season_changed',
]);

const BOT_PATTERN =
  /bot|crawler|spider|crawling|headless|preview|facebookexternalhit|slackbot|discordbot|whatsapp|telegrambot|uptimerobot/i;

const LEGACY_LOCAL_MATCH = 'local|%';
const PUBLIC_SITE_HOSTS = new Set(['hecate946.com', 'www.hecate946.com']);
const PUBLIC_SITE_PROTOCOLS = new Set(['http:', 'https:']);

export default {
  async scheduled(_controller, env, context) {
    context.waitUntil(
      env.DB.batch([
        // Remove any localhost rows written by the older shared-Worker design.
        env.DB.prepare(
          `DELETE FROM visitor_locations WHERE visitor_hash LIKE ?`,
        ).bind(LEGACY_LOCAL_MATCH),
        env.DB.prepare(
          `DELETE FROM location_stats WHERE location_key LIKE ?`,
        ).bind(LEGACY_LOCAL_MATCH),
        env.DB.prepare(
          `DELETE FROM daily_visitors WHERE day LIKE ?`,
        ).bind(LEGACY_LOCAL_MATCH),
        env.DB.prepare(
          `DELETE FROM daily_sessions WHERE day LIKE ?`,
        ).bind(LEGACY_LOCAL_MATCH),
        env.DB.prepare(
          `DELETE FROM daily_stats WHERE day LIKE ?`,
        ).bind(LEGACY_LOCAL_MATCH),
        env.DB.prepare(
          `DELETE FROM page_stats WHERE path LIKE ?`,
        ).bind(LEGACY_LOCAL_MATCH),
        env.DB.prepare(
          `DELETE FROM event_stats WHERE event_name LIKE ?`,
        ).bind(LEGACY_LOCAL_MATCH),
        env.DB.prepare(
          `DELETE FROM sessions WHERE visitor_hash LIKE ?`,
        ).bind(LEGACY_LOCAL_MATCH),
        env.DB.prepare(
          `DELETE FROM visitors WHERE visitor_hash LIKE ?`,
        ).bind(LEGACY_LOCAL_MATCH),
        env.DB.prepare(
          `DELETE FROM daily_visitors WHERE day < date('now', '-2 day')`,
        ),
        env.DB.prepare(
          `DELETE FROM daily_sessions WHERE day < date('now', '-2 day')`,
        ),
        env.DB.prepare(
          `DELETE FROM sessions WHERE last_seen < datetime('now', '-30 day')`,
        ),
      ]),
    );
  },

  async fetch(request, env) {
    const url = new URL(request.url);
    const publicRead = url.pathname === '/api/stats';

    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: corsHeaders(request, publicRead),
      });
    }

    if (url.pathname === '/api/event' && request.method === 'POST') {
      return ingestEvent(request, env);
    }

    if (url.pathname === '/api/stats' && request.method === 'GET') {
      if (!isAllowedReadOrigin(request.headers.get('Origin'))) {
        return json({ error: 'Origin not allowed' }, 403, request);
      }
      return readStats(request, env, url);
    }

    return json({ error: 'Not found' }, 404, request);
  },
};

async function ingestEvent(request, env) {
  const origin = request.headers.get('Origin');
  if (!isAllowedWriteOrigin(origin)) {
    return json({ error: 'Origin not allowed' }, 403, request);
  }

  const contentLength = Number(request.headers.get('Content-Length') ?? 0);
  if (contentLength > 4096) {
    return json({ error: 'Payload too large' }, 413, request);
  }

  const userAgent = request.headers.get('User-Agent') ?? '';
  if (!userAgent || BOT_PATTERN.test(userAgent)) {
    return json({ accepted: false, reason: 'bot' }, 202, request);
  }

  let body;
  try {
    body = JSON.parse(await request.text());
  } catch {
    return json({ error: 'Invalid JSON' }, 400, request);
  }

  const eventName = sanitizeEventName(body?.name);
  const path = sanitizePath(body?.path);
  const visitorId = sanitizeId(body?.visitorId);
  const sessionId = sanitizeId(body?.sessionId);

  if (!eventName || !visitorId || !sessionId) {
    return json({ error: 'Invalid event' }, 400, request);
  }

  if (eventName === 'page_view' && !path) {
    return json({ error: 'Page view requires a valid path' }, 400, request);
  }

  const now = new Date();
  const timestamp = now.toISOString();
  const day = timestamp.slice(0, 10);
  const dayKey = day;
  const eventKey = eventName;
  const pathKey = path;

  const visitorHash = await hashIdentifier(`visitor:${visitorId}`, env);
  const sessionHash = await hashIdentifier(`session:${sessionId}`, env);

  if (eventName === 'heartbeat') {
    await env.DB.batch([
      env.DB.prepare(
        `UPDATE visitors
         SET last_seen = ?
         WHERE visitor_hash = ?`,
      ).bind(timestamp, visitorHash),
      env.DB.prepare(
        `UPDATE sessions
         SET last_seen = ?
         WHERE session_hash = ? AND visitor_hash = ?`,
      ).bind(timestamp, sessionHash, visitorHash),
    ]);
    return json({ accepted: true }, 202, request);
  }

  await upsertEventCount(env.DB, eventKey, timestamp);

  if (eventName !== 'page_view') {
    const statements = [
      env.DB.prepare(
        `UPDATE visitors
         SET last_seen = ?
         WHERE visitor_hash = ?`,
      ).bind(timestamp, visitorHash),
      env.DB.prepare(
        `UPDATE sessions
         SET last_seen = ?
         WHERE session_hash = ? AND visitor_hash = ?`,
      ).bind(timestamp, sessionHash, visitorHash),
      env.DB.prepare(
        `INSERT INTO daily_stats (day, events)
         VALUES (?, 1)
         ON CONFLICT(day) DO UPDATE SET events = events + 1`,
      ).bind(dayKey),
    ];

    statements.push(
      env.DB.prepare(
        `UPDATE totals
         SET events = events + 1,
             first_event_at = COALESCE(first_event_at, ?),
             updated_at = ?
         WHERE id = 1`,
      ).bind(timestamp, timestamp),
    );

    await env.DB.batch(statements);
    return json({ accepted: true }, 202, request);
  }

  const newVisitorResult = await env.DB.prepare(
    `INSERT OR IGNORE INTO visitors (visitor_hash, first_seen, last_seen)
     VALUES (?, ?, ?)`,
  )
    .bind(visitorHash, timestamp, timestamp)
    .run();
  const isNewVisitor = changedRows(newVisitorResult) > 0;

  if (!isNewVisitor) {
    await env.DB.prepare(
      `UPDATE visitors SET last_seen = ? WHERE visitor_hash = ?`,
    )
      .bind(timestamp, visitorHash)
      .run();
  }

  const newSessionResult = await env.DB.prepare(
    `INSERT OR IGNORE INTO sessions
      (session_hash, visitor_hash, first_seen, last_seen, page_views)
     VALUES (?, ?, ?, ?, 1)`,
  )
    .bind(sessionHash, visitorHash, timestamp, timestamp)
    .run();
  const isNewSession = changedRows(newSessionResult) > 0;

  if (!isNewSession) {
    await env.DB.prepare(
      `UPDATE sessions
       SET last_seen = ?, page_views = page_views + 1
       WHERE session_hash = ?`,
    )
      .bind(timestamp, sessionHash)
      .run();
  }

  const dailyVisitorResult = await env.DB.prepare(
    `INSERT OR IGNORE INTO daily_visitors (day, visitor_hash) VALUES (?, ?)`,
  )
    .bind(dayKey, visitorHash)
    .run();
  const isNewDailyVisitor = changedRows(dailyVisitorResult) > 0;

  const dailySessionResult = await env.DB.prepare(
    `INSERT OR IGNORE INTO daily_sessions (day, session_hash) VALUES (?, ?)`,
  )
    .bind(dayKey, sessionHash)
    .run();
  const isNewDailySession = changedRows(dailySessionResult) > 0;

  const pageViewStatements = [
    env.DB.prepare(
      `INSERT INTO daily_stats
        (day, page_views, events, estimated_visitors, sessions)
       VALUES (?, 1, 1, ?, ?)
       ON CONFLICT(day) DO UPDATE SET
         page_views = page_views + 1,
         events = events + 1,
         estimated_visitors = estimated_visitors + excluded.estimated_visitors,
         sessions = sessions + excluded.sessions`,
    ).bind(dayKey, isNewDailyVisitor ? 1 : 0, isNewDailySession ? 1 : 0),
    env.DB.prepare(
      `INSERT INTO page_stats (path, page_views, updated_at)
       VALUES (?, 1, ?)
       ON CONFLICT(path) DO UPDATE SET
         page_views = page_views + 1,
         updated_at = excluded.updated_at`,
    ).bind(pathKey, timestamp),
  ];

  pageViewStatements.unshift(
    env.DB.prepare(
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
  );

  await env.DB.batch(pageViewStatements);

  const location = readApproximateLocation(request);
  if (location) {
    const locationKey = location.key;

    await env.DB.prepare(
      `DELETE FROM visitor_locations
       WHERE visitor_hash = ? AND location_key <> ?`,
    )
      .bind(visitorHash, locationKey)
      .run();

    const newVisitorLocationResult = await env.DB.prepare(
      `INSERT OR IGNORE INTO visitor_locations (visitor_hash, location_key)
       VALUES (?, ?)`,
    )
      .bind(visitorHash, locationKey)
      .run();

    await env.DB.prepare(
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
        locationKey,
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

  return json({ accepted: true }, 202, request);
}

async function readStats(request, env, url) {
  const days = clampInteger(url.searchParams.get('days'), 7, 365, 30);
  const utcOffsetMinutes = clampInteger(
    url.searchParams.get('utcOffsetMinutes'),
    -840,
    840,
    0,
  );
  const localTimeModifier = `${utcOffsetMinutes >= 0 ? '+' : ''}${utcOffsetMinutes} minutes`;
  const cutoff = new Date(Date.now() - 2 * 60 * 1000).toISOString();

  const totalsQuery = env.DB.prepare('SELECT * FROM totals WHERE id = 1');
  const activeQuery = env.DB.prepare(
    `SELECT COUNT(DISTINCT visitor_hash) AS count
     FROM sessions
     WHERE visitor_hash NOT LIKE ? AND last_seen >= ?`,
  ).bind(LEGACY_LOCAL_MATCH, cutoff);
  const dailyQuery = env.DB.prepare(
    `SELECT day, page_views, events, estimated_visitors
     FROM daily_stats
     WHERE day NOT LIKE ? AND day >= date('now', ?)
     ORDER BY day ASC`,
  ).bind(LEGACY_LOCAL_MATCH, `-${days - 1} day`);
  // Return the complete route inventory so lower-traffic pages still receive
  // accurate counts in the public observatory.
  const pageQuery = env.DB.prepare(
    `SELECT path AS label, page_views AS value
     FROM page_stats
     WHERE path NOT LIKE ?
     ORDER BY page_views DESC, path ASC
     LIMIT 250`,
  ).bind(LEGACY_LOCAL_MATCH);
  const interactionQuery = env.DB.prepare(
    `SELECT event_name AS label, total AS value
     FROM event_stats
     WHERE event_name NOT LIKE ? AND event_name <> 'page_view'
     ORDER BY total DESC, event_name ASC
     LIMIT 10`,
  ).bind(LEGACY_LOCAL_MATCH);
  const hourlyQuery = env.DB.prepare(
    `SELECT CAST(strftime('%H', first_seen, ?) AS INTEGER) AS hour,
            COUNT(*) AS value
     FROM sessions
     WHERE visitor_hash NOT LIKE ?
     GROUP BY hour
     ORDER BY hour ASC`,
  ).bind(localTimeModifier, LEGACY_LOCAL_MATCH);
  const locationQuery = env.DB.prepare(
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
       WHERE visitor_locations.visitor_hash NOT LIKE ?
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
  ).bind(LEGACY_LOCAL_MATCH);
  const countryQuery = env.DB.prepare(
    `SELECT COUNT(DISTINCT country_code) AS count
     FROM location_stats
     WHERE country_code IS NOT NULL
       AND country_code <> ''
       AND estimated_visitors > 0`,
  );

  const [
    totals,
    active,
    dailyResult,
    pageResult,
    interactionResult,
    hourlyResult,
    locationResult,
    countryResult,
  ] = await Promise.all([
    totalsQuery.first(),
    activeQuery.first(),
    dailyQuery.all(),
    pageQuery.all(),
    interactionQuery.all(),
    hourlyQuery.all(),
    locationQuery.all(),
    countryQuery.first(),
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
    hours: fillHourlyRows(hourlyResult.results),
    locations,
  };

  const origin = request.headers.get('Origin');
  return json(response, 200, request, {
    'Cache-Control': 'public, max-age=20, stale-while-revalidate=40',
    'Access-Control-Allow-Origin': origin || '*',
    ...(origin ? { Vary: 'Origin' } : {}),
  });
}

function fillHourlyRows(rows) {
  const byHour = new Map(
    rows.map((row) => [Number(row.hour), Number(row.value ?? 0)]),
  );

  return Array.from({ length: 24 }, (_, hour) => ({
    hour,
    value: byHour.get(hour) ?? 0,
  }));
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

  // Keep only coarse location precision (~1 km at the equator). The map
  // does not need street-level coordinates and the database should never store them.
  const roundedLatitude = Math.round(latitude * 100) / 100;
  const roundedLongitude = Math.round(longitude * 100) / 100;
  const city = cleanText(cf?.city, 80);
  const region = cleanText(cf?.region, 80);
  const country = cleanText(cf?.country, 80);
  const countryCode = cleanText(cf?.country, 3)?.toUpperCase() ?? null;
  const key = [
    countryCode ?? 'XX',
    region ?? '',
    city ?? '',
    roundedLatitude.toFixed(2),
    roundedLongitude.toFixed(2),
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
  const salt = env.VISITOR_SALT || 'hecate946-stats-v1';
  const bytes = new TextEncoder().encode(`${salt}:${value}`);
  const digest = await crypto.subtle.digest('SHA-256', bytes);
  return Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, '0'),
  ).join('');
}

function isAllowedReadOrigin(origin) {
  if (!origin) return true;
  return isAllowedSiteOrigin(origin);
}

function isAllowedWriteOrigin(origin) {
  return isAllowedSiteOrigin(origin);
}

function isAllowedSiteOrigin(origin) {
  if (!origin) return false;

  try {
    const url = new URL(origin);
    return (
      PUBLIC_SITE_PROTOCOLS.has(url.protocol) &&
      PUBLIC_SITE_HOSTS.has(url.hostname) &&
      url.port === ''
    );
  } catch {
    return false;
  }
}

function corsHeaders(request, publicRead = false) {
  const origin = request.headers.get('Origin');
  const allowedOrigin = publicRead
    ? isAllowedReadOrigin(origin)
      ? origin || '*'
      : 'null'
    : isAllowedWriteOrigin(origin)
      ? origin
      : 'null';

  return {
    'Access-Control-Allow-Origin': allowedOrigin,
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
    ...(origin ? { Vary: 'Origin' } : {}),
  };
}

function json(payload, status, request, extraHeaders = {}) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'X-Content-Type-Options': 'nosniff',
      'Referrer-Policy': 'no-referrer',
      'Permissions-Policy': 'geolocation=(), camera=(), microphone=()',
      'Content-Security-Policy': "default-src 'none'; frame-ancestors 'none'; base-uri 'none'",
      'X-Frame-Options': 'DENY',
      ...corsHeaders(request),
      ...extraHeaders,
    },
  });
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
