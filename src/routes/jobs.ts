import { Hono } from "hono";
import { getDB } from "../db/index.ts";

const app = new Hono();

app.get("/", (c) => {
  const db = getDB();
  const { scraper_id, status, limit = "50" } = c.req.query();

  let query = "SELECT j.*, s.name as scraper_name FROM jobs j JOIN scrapers s ON j.scraper_id=s.id WHERE 1=1";
  const params: any[] = [];

  if (scraper_id) { query += " AND j.scraper_id=?"; params.push(scraper_id); }
  if (status) { query += " AND j.status=?"; params.push(status); }

  query += ` ORDER BY j.created_at DESC LIMIT ?`;
  params.push(parseInt(limit));

  const jobs = db.prepare(query).all(...params);
  return c.json(jobs);
});

app.get("/:id", (c) => {
  const db = getDB();
  const job = db.prepare("SELECT j.*, s.name as scraper_name FROM jobs j JOIN scrapers s ON j.scraper_id=s.id WHERE j.id=?").get(c.req.param("id"));
  if (!job) return c.json({ error: "Not found" }, 404);
  return c.json(job);
});

export default app;
