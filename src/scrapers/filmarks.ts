import type { ScraperPlugin, Credentials, ScrapeRecord } from "./base.ts";

export const filmarksScraper: ScraperPlugin = {
  id: "filmarks",
  name: "Filmarks",

  async validate(credentials: Credentials): Promise<boolean> {
    if (!credentials.userId) return false;
    return true;
  },

  async *sync(credentials: Credentials): AsyncGenerator<ScrapeRecord> {
    if (!credentials.userId) {
      console.warn("[filmarks] No userId configured, skipping sync");
      return;
    }

    // TODO: Real implementation would:
    // 1. GET https://filmarks.com/users/{userId}
    // 2. Parse movie list with Cheerio
    // 3. Follow pagination and yield each movie
    //
    // Example:
    // const cheerio = await import("cheerio");
    // let page = 1;
    // while (true) {
    //   const res = await fetch(`https://filmarks.com/users/${credentials.userId}?page=${page}`, {
    //     headers: { Cookie: credentials.cookie || "" },
    //   });
    //   const html = await res.text();
    //   const $ = cheerio.load(html);
    //   const movies = $(".c-content-card").map((_, el) => ({
    //     filmarks_id: $(el).attr("data-content-id") || "",
    //     title: $(el).find(".c-content-card__title").text().trim(),
    //     rating: parseFloat($(el).find(".c-rating__score").text()) || 0,
    //     watched_at: $(el).find(".p-mark__date").text().trim(),
    //   })).get();
    //   if (movies.length === 0) break;
    //   for (const movie of movies) yield { type: "movie", data: movie };
    //   page++;
    // }

    // Stub sample data
    const sampleMovies = [
      {
        filmarks_id: "movie-1",
        title: "ドライブ・マイ・カー",
        director: "濱口竜介",
        year: 2021,
        cover_url: "",
        rating: 4.8,
        watched_at: "2024-12-10",
        status: "watched",
      },
      {
        filmarks_id: "movie-2",
        title: "ゴジラ-1.0",
        director: "山崎貴",
        year: 2023,
        cover_url: "",
        rating: 4.2,
        watched_at: "2024-11-20",
        status: "watched",
      },
    ];

    for (const movie of sampleMovies) {
      yield {
        type: "movie",
        data: movie,
      };
    }
  },
};
