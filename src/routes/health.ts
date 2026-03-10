import { Hono } from "hono";
import { getDB } from "../db/index.ts";

const app = new Hono();

app.get("/", (c) => {
  const db = getDB();
  const lastJob = db.prepare("SELECT * FROM jobs ORDER BY created_at DESC LIMIT 1").get() as any;

  return c.json({
    status: "ok",
    timestamp: new Date().toISOString(),
    db: "connected",
    lastJob: lastJob ? {
      id: lastJob.id,
      scraper_id: lastJob.scraper_id,
      status: lastJob.status,
      created_at: lastJob.created_at,
    } : null,
  });
});

export default app;
