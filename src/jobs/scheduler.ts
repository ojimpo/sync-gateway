import { getDB } from "../db/index.ts";
import { getScraper } from "../scrapers/registry.ts";
import { randomUUID } from "crypto";

export async function runScraper(scraperId: string): Promise<string> {
  const db = getDB();
  const jobId = randomUUID();

  const scraper_row = db.prepare("SELECT * FROM scrapers WHERE id = ?").get(scraperId) as any;
  if (!scraper_row) throw new Error(`Scraper not found: ${scraperId}`);

  const plugin = getScraper(scraperId);
  if (!plugin) throw new Error(`Plugin not found: ${scraperId}`);

  db.prepare(`
    INSERT INTO jobs (id, scraper_id, status, started_at)
    VALUES (?, ?, 'running', datetime('now'))
  `).run(jobId, scraperId);

  // Run async, don't await
  (async () => {
    let count = 0;
    try {
      const credentials = JSON.parse(scraper_row.credentials_json || "{}");
      const insertBook = db.prepare(`
        INSERT OR REPLACE INTO books (id, isbn, title, author, publisher, cover_url, rating, read_at, status, raw_json, synced_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
      `);
      const insertMovie = db.prepare(`
        INSERT OR REPLACE INTO movies (id, filmarks_id, title, director, year, cover_url, rating, watched_at, status, raw_json, synced_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
      `);

      for await (const record of plugin.sync(credentials)) {
        if (record.type === "book") {
          const b = record.data as any;
          const id = b.isbn || randomUUID();
          insertBook.run(id, b.isbn, b.title, b.author, b.publisher, b.cover_url, b.rating, b.read_at, b.status, JSON.stringify(b));
        } else if (record.type === "movie") {
          const m = record.data as any;
          const id = m.filmarks_id || randomUUID();
          insertMovie.run(id, m.filmarks_id, m.title, m.director, m.year, m.cover_url, m.rating, m.watched_at, m.status, JSON.stringify(m));
        }
        count++;
      }

      db.prepare(`
        UPDATE jobs SET status='completed', finished_at=datetime('now'), records_fetched=?
        WHERE id=?
      `).run(count, jobId);
      db.prepare(`UPDATE scrapers SET last_synced_at=datetime('now') WHERE id=?`).run(scraperId);

      console.log(`[jobs] ${scraperId} completed: ${count} records`);
    } catch (err: any) {
      db.prepare(`
        UPDATE jobs SET status='failed', finished_at=datetime('now'), error_message=?
        WHERE id=?
      `).run(err.message, jobId);
      console.error(`[jobs] ${scraperId} failed:`, err.message);
    }
  })();

  return jobId;
}

export function startScheduler() {
  const db = getDB();
  const CHECK_INTERVAL_MS = 60_000; // check every minute

  setInterval(() => {
    const scrapers = db.prepare("SELECT * FROM scrapers WHERE enabled=1").all() as any[];
    const now = new Date();

    for (const scraper of scrapers) {
      const lastSynced = scraper.last_synced_at ? new Date(scraper.last_synced_at + "Z") : null;
      const intervalMs = (scraper.interval_minutes || 60) * 60 * 1000;

      if (!lastSynced || now.getTime() - lastSynced.getTime() > intervalMs) {
        console.log(`[scheduler] Triggering sync for: ${scraper.id}`);
        runScraper(scraper.id).catch(console.error);
      }
    }
  }, CHECK_INTERVAL_MS);

  console.log("[scheduler] Started");
}
