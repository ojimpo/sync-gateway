import { Hono } from "hono";
import { getDB } from "../db/index.ts";

const app = new Hono();

app.get("/movies", (c) => {
  const db = getDB();
  const { status, q, limit = "50", offset = "0" } = c.req.query();

  let query = "SELECT * FROM movies WHERE 1=1";
  const params: any[] = [];

  if (status) { query += " AND status=?"; params.push(status); }
  if (q) { query += " AND (title LIKE ? OR director LIKE ?)"; params.push(`%${q}%`, `%${q}%`); }

  query += ` ORDER BY watched_at DESC LIMIT ? OFFSET ?`;
  params.push(parseInt(limit), parseInt(offset));

  const movies = db.prepare(query).all(...params);
  const total = (db.prepare("SELECT COUNT(*) as n FROM movies").get() as any).n;

  return c.json({ total, movies });
});

app.get("/movies/:id", (c) => {
  const db = getDB();
  const movie = db.prepare("SELECT * FROM movies WHERE id=?").get(c.req.param("id"));
  if (!movie) return c.json({ error: "Not found" }, 404);
  return c.json(movie);
});

export default app;
