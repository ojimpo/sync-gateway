import { Hono } from "hono";
import { getDB } from "../db/index.ts";

const app = new Hono();

app.get("/books", (c) => {
  const db = getDB();
  const { status, q, limit = "50", offset = "0" } = c.req.query();

  let query = "SELECT * FROM books WHERE 1=1";
  const params: any[] = [];

  if (status) { query += " AND status=?"; params.push(status); }
  if (q) { query += " AND (title LIKE ? OR author LIKE ?)"; params.push(`%${q}%`, `%${q}%`); }

  query += ` ORDER BY read_at DESC LIMIT ? OFFSET ?`;
  params.push(parseInt(limit), parseInt(offset));

  const books = db.prepare(query).all(...params);
  const total = (db.prepare("SELECT COUNT(*) as n FROM books").get() as any).n;

  return c.json({ total, books });
});

app.get("/books/:id", (c) => {
  const db = getDB();
  const book = db.prepare("SELECT * FROM books WHERE id=?").get(c.req.param("id"));
  if (!book) return c.json({ error: "Not found" }, 404);
  return c.json(book);
});

export default app;
