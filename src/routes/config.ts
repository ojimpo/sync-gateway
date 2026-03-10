import { Hono } from "hono";
import { getDB } from "../db/index.ts";

const app = new Hono();

app.get("/", (c) => {
  const db = getDB();
  const scrapers = db.prepare("SELECT id, name, enabled, interval_minutes, last_synced_at FROM scrapers").all();
  return c.json({ scrapers });
});

app.put("/scrapers/:id/credentials", async (c) => {
  const db = getDB();
  const body = await c.req.json();

  db.prepare("UPDATE scrapers SET credentials_json=? WHERE id=?").run(
    JSON.stringify(body),
    c.req.param("id")
  );

  return c.json({ ok: true });
});

export default app;
