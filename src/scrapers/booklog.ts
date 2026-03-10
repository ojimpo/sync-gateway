import type { ScraperPlugin, Credentials, ScrapeRecord } from "./base.ts";

export const booklogScraper: ScraperPlugin = {
  id: "booklog",
  name: "読書メーター",

  async validate(credentials: Credentials): Promise<boolean> {
    if (!credentials.userId) return false;
    // TODO: implement real validation by attempting to fetch user page
    return true;
  },

  async *sync(credentials: Credentials): AsyncGenerator<ScrapeRecord> {
    if (!credentials.userId) {
      console.warn("[booklog] No userId configured, skipping sync");
      return;
    }

    // TODO: Real implementation would:
    // 1. GET https://bookmeter.com/users/{userId}/books/read
    // 2. Parse pagination with Cheerio
    // 3. Yield each book record
    //
    // Example:
    // const cheerio = await import("cheerio");
    // let page = 1;
    // while (true) {
    //   const res = await fetch(`https://bookmeter.com/users/${credentials.userId}/books/read?page=${page}`, {
    //     headers: { Cookie: credentials.cookie || "" },
    //   });
    //   const html = await res.text();
    //   const $ = cheerio.load(html);
    //   const books = $(".book-item").map((_, el) => ({
    //     title: $(el).find(".book-title").text().trim(),
    //     author: $(el).find(".book-author").text().trim(),
    //     isbn: $(el).attr("data-isbn") || "",
    //     rating: parseFloat($(el).find(".rating").text()) || 0,
    //     read_at: $(el).find(".read-date").text().trim(),
    //   })).get();
    //   if (books.length === 0) break;
    //   for (const book of books) yield { type: "book", data: book };
    //   page++;
    // }

    // Stub: yield sample data to demonstrate the pipeline
    const sampleBooks = [
      {
        isbn: "9784167110119",
        title: "こころ",
        author: "夏目漱石",
        publisher: "文春文庫",
        cover_url: "",
        rating: 4.5,
        read_at: "2024-12-01",
        status: "read",
      },
      {
        isbn: "9784101092058",
        title: "人間失格",
        author: "太宰治",
        publisher: "新潮文庫",
        cover_url: "",
        rating: 4.0,
        read_at: "2024-11-15",
        status: "read",
      },
    ];

    for (const book of sampleBooks) {
      yield {
        type: "book",
        data: book,
      };
    }
  },
};
