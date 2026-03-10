import { Hono } from "hono";
import { readFileSync } from "fs";
import { join } from "path";

const app = new Hono();
const html = readFileSync(join(import.meta.dir, "../admin/index.html"), "utf-8");

app.get("/", (c) => c.html(html));
app.get("/*", (c) => c.html(html));

export default app;
