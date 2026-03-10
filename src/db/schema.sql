CREATE TABLE IF NOT EXISTS scrapers (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  base_url TEXT NOT NULL,
  credentials_json TEXT DEFAULT '{}',
  enabled INTEGER DEFAULT 1,
  interval_minutes INTEGER DEFAULT 60,
  last_synced_at TEXT,
  created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  scraper_id TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  started_at TEXT,
  finished_at TEXT,
  records_fetched INTEGER DEFAULT 0,
  error_message TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  FOREIGN KEY (scraper_id) REFERENCES scrapers(id)
);

CREATE TABLE IF NOT EXISTS books (
  id TEXT PRIMARY KEY,
  isbn TEXT,
  title TEXT NOT NULL,
  author TEXT,
  publisher TEXT,
  cover_url TEXT,
  rating REAL,
  read_at TEXT,
  status TEXT DEFAULT 'read',
  raw_json TEXT,
  synced_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS movies (
  id TEXT PRIMARY KEY,
  filmarks_id TEXT,
  title TEXT NOT NULL,
  director TEXT,
  year INTEGER,
  cover_url TEXT,
  rating REAL,
  watched_at TEXT,
  status TEXT DEFAULT 'watched',
  raw_json TEXT,
  synced_at TEXT DEFAULT (datetime('now'))
);

INSERT OR IGNORE INTO scrapers (id, name, base_url) VALUES
  ('booklog', '読書メーター', 'https://bookmeter.com'),
  ('filmarks', 'Filmarks', 'https://filmarks.com');
