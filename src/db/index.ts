import { Database } from "bun:sqlite";
import { readFileSync } from "fs";
import { join } from "path";

const DB_PATH = process.env.DB_PATH || "./data/arigato.db";

let db: Database;

export function getDB(): Database {
  if (!db) {
    db = new Database(DB_PATH, { create: true });
    db.exec("PRAGMA journal_mode=WAL;");
    db.exec("PRAGMA foreign_keys=ON;");
    const schema = readFileSync(join(import.meta.dir, "schema.sql"), "utf-8");
    db.exec(schema);
  }
  return db;
}
