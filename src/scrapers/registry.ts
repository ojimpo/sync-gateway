import type { ScraperPlugin } from "./base.ts";
import { booklogScraper } from "./booklog.ts";
import { filmarksScraper } from "./filmarks.ts";

const plugins: Map<string, ScraperPlugin> = new Map();

export function registerScraper(plugin: ScraperPlugin) {
  plugins.set(plugin.id, plugin);
  console.log(`[registry] Registered scraper: ${plugin.id}`);
}

export function getScraper(id: string): ScraperPlugin | undefined {
  return plugins.get(id);
}

export function getAllScrapers(): ScraperPlugin[] {
  return Array.from(plugins.values());
}

export function initRegistry() {
  registerScraper(booklogScraper);
  registerScraper(filmarksScraper);
}
