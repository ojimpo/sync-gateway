import { Hono } from "hono";
import { getDB } from "../db/index.ts";
import { runScraper } from "../jobs/scheduler.ts";

const app = new Hono();

app.get("/", (c) => {
  const db = getDB();
  const scrapers = db.prepare("SELECT * FROM scrapers ORDER BY name").all();
  return c.json(scrapers);
});

app.get("/:id/status", (c) => {
  const db = getDB();
  const scraper = db.prepare("SELECT * FROM scrapers WHERE id=?").get(c.req.param("id")) as any;
  if (!scraper) return c.json({ error: "Not found" }, 404);

  const recentJobs = db.prepare(
    "SELECT * FROM jobs WHERE scraper_id=? ORDER BY created_at DESC LIMIT 5"
  ).all(scraper.id);

  return c.json({ scraper, recentJobs });
});

app.post("/:id/sync", async (c) => {
  try {
    const jobId = await runScraper(c.req.param("id"));
    return c.json({ jobId, status: "started" });
  } catch (err: any) {
    return c.json({ error: err.message }, 400);
  }
});

app.put("/:id", async (c) => {
  const db = getDB();
  const body = await c.req.json();
  const { enabled, interval_minutes, credentials_json } = body;

  db.prepare(`
    UPDATE scrapers SET enabled=COALESCE(?,enabled), interval_minutes=COALESCE(?,interval_minutes), credentials_json=COALESCE(?,credentials_json)
    WHERE id=?
  `).run(
    enabled !== undefined ? (enabled ? 1 : 0) : null,
    interval_minutes ?? null,
    credentials_json ? JSON.stringify(credentials_json) : null,
    c.req.param("id")
  );

  const updated = db.prepare("SELECT * FROM scrapers WHERE id=?").get(c.req.param("id"));
  return c.json(updated);
});

export default app;
