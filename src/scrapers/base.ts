export interface Credentials {
  username?: string;
  password?: string;
  userId?: string;
  cookie?: string;
  [key: string]: string | undefined;
}

export interface ScrapeRecord {
  type: "book" | "movie";
  data: Record<string, unknown>;
}

export interface ScraperPlugin {
  id: string;
  name: string;
  sync(credentials: Credentials): AsyncGenerator<ScrapeRecord>;
  validate(credentials: Credentials): Promise<boolean>;
}
