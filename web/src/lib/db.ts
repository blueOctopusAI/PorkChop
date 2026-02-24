/**
 * SQLite database reader (server-side only).
 * Mirrors the Python Database class — read-only access to porkchop.db.
 */

import Database from "better-sqlite3";
import { DB_PATH } from "./config";
import type {
  Bill,
  BillVersion,
  Section,
  SpendingItem,
  LegalReference,
  Deadline,
  Entity,
  Summary,
  PorkScore,
  PorkSummary,
  Comparison,
  Stats,
} from "./types";

let _db: Database.Database | null = null;

function getDb(): Database.Database {
  if (!_db) {
    _db = new Database(DB_PATH, { readonly: true });
    _db.pragma("journal_mode = WAL");
    _db.pragma("foreign_keys = ON");
  }
  return _db;
}

// --- Bills ---

export function listBills(limit = 50): Bill[] {
  return getDb()
    .prepare("SELECT * FROM bills ORDER BY fetched_at DESC LIMIT ?")
    .all(limit) as Bill[];
}

export function getBill(billId: number): Bill | undefined {
  return getDb()
    .prepare("SELECT * FROM bills WHERE id = ?")
    .get(billId) as Bill | undefined;
}

export function searchBills(query: string): Bill[] {
  const pattern = `%${query}%`;
  return getDb()
    .prepare(
      "SELECT * FROM bills WHERE title LIKE ? OR short_title LIKE ? OR summary LIKE ?"
    )
    .all(pattern, pattern, pattern) as Bill[];
}

// --- Versions ---

export function getVersions(billId: number): BillVersion[] {
  return getDb()
    .prepare(
      "SELECT id, bill_id, version_code, version_name, text_url, xml_url, fetched_at FROM bill_versions WHERE bill_id = ? ORDER BY fetched_at"
    )
    .all(billId) as BillVersion[];
}

export function getVersion(versionId: number): BillVersion | undefined {
  return getDb()
    .prepare("SELECT * FROM bill_versions WHERE id = ?")
    .get(versionId) as BillVersion | undefined;
}

// --- Sections ---

export function getSections(
  billId: number,
  versionId?: number
): Section[] {
  if (versionId) {
    return getDb()
      .prepare(
        "SELECT * FROM sections WHERE bill_id = ? AND version_id = ? ORDER BY position"
      )
      .all(billId, versionId) as Section[];
  }
  return getDb()
    .prepare("SELECT * FROM sections WHERE bill_id = ? ORDER BY position")
    .all(billId) as Section[];
}

// --- Spending ---

export function getSpending(billId: number): SpendingItem[] {
  return getDb()
    .prepare(
      "SELECT * FROM spending_items WHERE bill_id = ? ORDER BY amount_numeric DESC"
    )
    .all(billId) as SpendingItem[];
}

export function getTotalSpending(billId: number): number {
  const row = getDb()
    .prepare(
      "SELECT COALESCE(SUM(amount_numeric), 0) as total FROM spending_items WHERE bill_id = ?"
    )
    .get(billId) as { total: number };
  return row.total;
}

// --- Legal References ---

export function getReferences(
  billId: number,
  refType?: string
): LegalReference[] {
  if (refType) {
    return getDb()
      .prepare(
        "SELECT * FROM legal_references WHERE bill_id = ? AND ref_type = ?"
      )
      .all(billId, refType) as LegalReference[];
  }
  return getDb()
    .prepare("SELECT * FROM legal_references WHERE bill_id = ?")
    .all(billId) as LegalReference[];
}

// --- Deadlines ---

export function getDeadlines(billId: number): Deadline[] {
  return getDb()
    .prepare("SELECT * FROM deadlines WHERE bill_id = ?")
    .all(billId) as Deadline[];
}

// --- Entities ---

export function getEntities(billId: number): Entity[] {
  return getDb()
    .prepare(
      "SELECT DISTINCT name, entity_type, role FROM entities WHERE bill_id = ?"
    )
    .all(billId) as Entity[];
}

// --- Summaries ---

export function getSummaries(billId: number): Summary[] {
  return getDb()
    .prepare(
      "SELECT * FROM summaries WHERE bill_id = ? ORDER BY created_at DESC"
    )
    .all(billId) as Summary[];
}

export function getBillSummary(billId: number): string | null {
  const row = getDb()
    .prepare(
      "SELECT summary_text FROM summaries WHERE bill_id = ? AND section_id IS NULL ORDER BY created_at DESC LIMIT 1"
    )
    .get(billId) as { summary_text: string } | undefined;
  return row?.summary_text ?? null;
}

// --- Pork Scores ---

export function getPorkScores(billId: number): PorkScore[] {
  return getDb()
    .prepare(
      `SELECT ps.*, si.amount, si.purpose, si.recipient
       FROM pork_scores ps
       JOIN spending_items si ON ps.spending_item_id = si.id
       WHERE ps.bill_id = ?
       ORDER BY ps.score DESC`
    )
    .all(billId) as PorkScore[];
}

export function getPorkSummary(billId: number): PorkSummary {
  const row = getDb()
    .prepare(
      `SELECT COUNT(*) as scored_items,
              AVG(score) as avg_score,
              MAX(score) as max_score,
              SUM(CASE WHEN score >= 70 THEN 1 ELSE 0 END) as high_pork_count
       FROM pork_scores WHERE bill_id = ?`
    )
    .get(billId) as PorkSummary;
  return row;
}

// --- Comparisons ---

export function getComparison(
  billId: number,
  fromVersionId: number,
  toVersionId: number
): Comparison | undefined {
  return getDb()
    .prepare(
      "SELECT * FROM comparisons WHERE bill_id = ? AND from_version_id = ? AND to_version_id = ?"
    )
    .get(billId, fromVersionId, toVersionId) as Comparison | undefined;
}

// --- Stats ---

export function getStats(): Stats {
  const db = getDb();
  const bills = (
    db.prepare("SELECT COUNT(*) as c FROM bills").get() as { c: number }
  ).c;
  const spending = (
    db.prepare("SELECT COUNT(*) as c FROM spending_items").get() as {
      c: number;
    }
  ).c;
  const total = (
    db
      .prepare(
        "SELECT COALESCE(SUM(amount_numeric), 0) as t FROM spending_items"
      )
      .get() as { t: number }
  ).t;
  const scored = (
    db.prepare("SELECT COUNT(*) as c FROM pork_scores").get() as {
      c: number;
    }
  ).c;
  return {
    bills_analyzed: bills,
    spending_items: spending,
    total_spending: total,
    items_scored: scored,
  };
}
