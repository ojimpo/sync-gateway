import { Hono } from "hono";
import { logger } from "hono/logger";
import { cors } from "hono/cors";
import { getDB } from "./db/index.ts";
import { initRegistry } from "./scrapers/registry.ts";
import { startScheduler } from "./jobs/scheduler.ts";

import healthRoutes from "./routes/health.ts";
import scraperRoutes from "./routes/scrapers.ts";
import booklogRoutes from "./routes/booklog.ts";
import filmarksRoutes from "./routes/filmarks.ts";
import jobRoutes from "./routes/jobs.ts";
import configRoutes from "./routes/config.ts";
import adminRoutes from "./routes/admin.ts";

const app = new Hono();

app.use("*", logger());
app.use("/api/*", cors());

// Initialize
getDB();
initRegistry();
startScheduler();

// Routes
app.route("/health", healthRoutes);
app.route("/api/scrapers", scraperRoutes);
app.route("/api/booklog", booklogRoutes);
app.route("/api/filmarks", filmarksRoutes);
app.route("/api/jobs", jobRoutes);
app.route("/api/config", configRoutes);
app.route("/admin", adminRoutes);

// Redirect root to admin
app.get("/", (c) => c.redirect("/admin/"));

const PORT = parseInt(process.env.PORT || "3000");
console.log(`[arigato-gateway] Starting on port ${PORT}`);

export default {
  port: PORT,
  fetch: app.fetch,
};
