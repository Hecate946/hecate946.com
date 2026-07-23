PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS totals (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  page_views INTEGER NOT NULL DEFAULT 0,
  events INTEGER NOT NULL DEFAULT 0,
  estimated_visitors INTEGER NOT NULL DEFAULT 0,
  sessions INTEGER NOT NULL DEFAULT 0,
  first_event_at TEXT,
  updated_at TEXT
);

INSERT OR IGNORE INTO totals (id) VALUES (1);

CREATE TABLE IF NOT EXISTS visitors (
  visitor_hash TEXT PRIMARY KEY,
  first_seen TEXT NOT NULL,
  last_seen TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS sessions (
  session_hash TEXT PRIMARY KEY,
  visitor_hash TEXT NOT NULL,
  first_seen TEXT NOT NULL,
  last_seen TEXT NOT NULL,
  page_views INTEGER NOT NULL DEFAULT 0
) WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS sessions_last_seen_idx ON sessions(last_seen);

CREATE TABLE IF NOT EXISTS daily_stats (
  day TEXT PRIMARY KEY,
  page_views INTEGER NOT NULL DEFAULT 0,
  events INTEGER NOT NULL DEFAULT 0,
  estimated_visitors INTEGER NOT NULL DEFAULT 0,
  sessions INTEGER NOT NULL DEFAULT 0
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS daily_visitors (
  day TEXT NOT NULL,
  visitor_hash TEXT NOT NULL,
  PRIMARY KEY (day, visitor_hash)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS daily_sessions (
  day TEXT NOT NULL,
  session_hash TEXT NOT NULL,
  PRIMARY KEY (day, session_hash)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS page_stats (
  path TEXT PRIMARY KEY,
  page_views INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS event_stats (
  event_name TEXT PRIMARY KEY,
  total INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS location_stats (
  location_key TEXT PRIMARY KEY,
  city TEXT,
  region TEXT,
  country TEXT,
  country_code TEXT,
  latitude REAL NOT NULL,
  longitude REAL NOT NULL,
  page_views INTEGER NOT NULL DEFAULT 0,
  estimated_visitors INTEGER NOT NULL DEFAULT 0,
  updated_at TEXT NOT NULL
) WITHOUT ROWID;

CREATE INDEX IF NOT EXISTS location_country_idx ON location_stats(country_code);

CREATE TABLE IF NOT EXISTS visitor_locations (
  visitor_hash TEXT NOT NULL,
  location_key TEXT NOT NULL,
  PRIMARY KEY (visitor_hash, location_key)
) WITHOUT ROWID;
