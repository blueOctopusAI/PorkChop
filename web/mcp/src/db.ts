/**
 * SQLite reader for the MCP server.
 * Same queries as the Next.js lib/db.ts — reads porkchop.db directly.
 */

import Database from "better-sqlite3";

let _db: Database.Database | null = null;

export function initDb(dbPath: string) {
  _db = new Database(dbPath, { readonly: true });
  _db.pragma("journal_mode = WAL");
  _db.pragma("foreign_keys = ON");
}

function db(): Database.Database {
  if (!_db) throw new Error("Database not initialized. Call initDb() first.");
  return _db;
}

export function listBills(limit = 50) {
  return db()
    .prepare("SELECT * FROM bills ORDER BY fetched_at DESC LIMIT ?")
    .all(limit);
}

export function getBill(billId: number) {
  return db().prepare("SELECT * FROM bills WHERE id = ?").get(billId);
}

export function searchBills(query: string) {
  const pattern = `%${query}%`;
  return db()
    .prepare(
      "SELECT * FROM bills WHERE title LIKE ? OR short_title LIKE ? OR summary LIKE ?"
    )
    .all(pattern, pattern, pattern);
}

export function getSpending(billId: number) {
  return db()
    .prepare(
      "SELECT * FROM spending_items WHERE bill_id = ? ORDER BY amount_numeric DESC"
    )
    .all(billId);
}

export function getTotalSpending(billId: number): number {
  const row = db()
    .prepare(
      "SELECT COALESCE(SUM(amount_numeric), 0) as total FROM spending_items WHERE bill_id = ?"
    )
    .get(billId) as { total: number };
  return row.total;
}

export function getPorkScores(billId: number) {
  return db()
    .prepare(
      `SELECT ps.*, si.amount, si.purpose, si.recipient
       FROM pork_scores ps
       JOIN spending_items si ON ps.spending_item_id = si.id
       WHERE ps.bill_id = ?
       ORDER BY ps.score DESC`
    )
    .all(billId);
}

export function getPorkSummary(billId: number) {
  return db()
    .prepare(
      `SELECT COUNT(*) as scored_items,
              AVG(score) as avg_score,
              MAX(score) as max_score,
              SUM(CASE WHEN score >= 70 THEN 1 ELSE 0 END) as high_pork_count
       FROM pork_scores WHERE bill_id = ?`
    )
    .get(billId);
}

export function getDeadlines(billId: number) {
  return db()
    .prepare("SELECT * FROM deadlines WHERE bill_id = ?")
    .all(billId);
}

export function getEntities(billId: number) {
  return db()
    .prepare(
      "SELECT DISTINCT name, entity_type, role FROM entities WHERE bill_id = ?"
    )
    .all(billId);
}

export function getReferences(billId: number, refType?: string) {
  if (refType) {
    return db()
      .prepare(
        "SELECT * FROM legal_references WHERE bill_id = ? AND ref_type = ?"
      )
      .all(billId, refType);
  }
  return db()
    .prepare("SELECT * FROM legal_references WHERE bill_id = ?")
    .all(billId);
}

export function getBillSummary(billId: number): string | null {
  const row = db()
    .prepare(
      "SELECT summary_text FROM summaries WHERE bill_id = ? AND section_id IS NULL ORDER BY created_at DESC LIMIT 1"
    )
    .get(billId) as { summary_text: string } | undefined;
  return row?.summary_text ?? null;
}

export function getVersions(billId: number) {
  return db()
    .prepare(
      "SELECT id, bill_id, version_code, version_name, fetched_at FROM bill_versions WHERE bill_id = ? ORDER BY fetched_at"
    )
    .all(billId);
}

export function getComparison(
  billId: number,
  fromVersionId: number,
  toVersionId: number
) {
  return db()
    .prepare(
      "SELECT * FROM comparisons WHERE bill_id = ? AND from_version_id = ? AND to_version_id = ?"
    )
    .get(billId, fromVersionId, toVersionId);
}

export function getStats() {
  const d = db();
  const bills = (d.prepare("SELECT COUNT(*) as c FROM bills").get() as { c: number }).c;
  const spending = (d.prepare("SELECT COUNT(*) as c FROM spending_items").get() as { c: number }).c;
  const total = (
    d.prepare("SELECT COALESCE(SUM(amount_numeric), 0) as t FROM spending_items").get() as {
      t: number;
    }
  ).t;
  const scored = (d.prepare("SELECT COUNT(*) as c FROM pork_scores").get() as { c: number }).c;
  return { bills_analyzed: bills, spending_items: spending, total_spending: total, items_scored: scored };
}
