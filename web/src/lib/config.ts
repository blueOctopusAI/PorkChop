import path from "path";

export const DB_PATH =
  process.env.PORKCHOP_DB_PATH ||
  path.resolve(process.cwd(), "..", "data", "porkchop.db");

export const APP_VERSION = "1.0.0";
