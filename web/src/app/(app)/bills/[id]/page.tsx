import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  getBill,
  getSpending,
  getTotalSpending,
  getReferences,
  getDeadlines,
  getEntities,
  getBillSummary,
  getPorkSummary,
  getVersions,
  getSections,
} from "@/lib/db";
import {
  formatCurrency,
  formatCurrencyFull,
  formatNumber,
  formatBillId,
  formatBillIdFull,
  truncate,
  cleanAmount,
} from "@/lib/format";
import { ExternalLink } from "lucide-react";
import { getPorkBadgeClass, getPorkLabel, getPorkColor } from "@/lib/pork-colors";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const bill = getBill(Number(id));
  return { title: bill ? formatBillId(bill) : "Bill Not Found" };
}

export default async function BillDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const billId = Number(id);
  const bill = getBill(billId);
  if (!bill) notFound();

  const spending = getSpending(billId);
  const totalSpending = getTotalSpending(billId);
  const refs = getReferences(billId);
  const deadlines = getDeadlines(billId);
  const entities = getEntities(billId);
  const summary = getBillSummary(billId);
  const pork = getPorkSummary(billId);
  const versions = getVersions(billId);
  const sections = getSections(billId);

  const refsByType = refs.reduce(
    (acc, r) => {
      const type = r.ref_type || "other";
      if (!acc[type]) acc[type] = [];
      acc[type].push(r);
      return acc;
    },
    {} as Record<string, typeof refs>
  );

  return (
    <div className="max-w-6xl">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <span className="font-mono text-accent text-lg">
            {formatBillId(bill)}
          </span>
          {bill.status && (
            <span className="text-xs bg-surface border border-border px-2 py-0.5 rounded text-text-dim">
              {bill.status}
            </span>
          )}
        </div>
        <h1 className="text-2xl font-bold mb-2">{bill.title || "Untitled"}</h1>
        <p className="text-sm text-text-dim">{formatBillIdFull(bill)}</p>
        {bill.introduced_date && (
          <p className="text-sm text-text-dim mt-1">
            Introduced: {bill.introduced_date}
          </p>
        )}
        <div className="flex flex-wrap gap-3 mt-4">
          <Link
            href={`/bills/${billId}/spending`}
            className="bg-accent text-bg px-4 py-2 rounded-lg text-sm font-semibold hover:bg-accent-dim hover:text-white transition-colors"
          >
            Full Spending Table
          </Link>
          <Link
            href={`/bills/${billId}/pork`}
            className="border border-border px-4 py-2 rounded-lg text-sm font-semibold hover:bg-surface transition-colors"
          >
            Pork Analysis
          </Link>
          {versions.length > 1 && (
            <Link
              href={`/bills/${billId}/compare`}
              className="border border-border px-4 py-2 rounded-lg text-sm font-semibold hover:bg-surface transition-colors"
            >
              Compare Versions
            </Link>
          )}
          <a
            href={`https://www.congress.gov/bill/${bill.congress}th-congress/house-bill/${bill.bill_number}`}
            target="_blank"
            rel="noopener noreferrer"
            className="border border-border px-4 py-2 rounded-lg text-sm font-semibold hover:bg-surface transition-colors flex items-center gap-1.5"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Congress.gov
          </a>
          <a
            href={`https://www.govinfo.gov/app/search/%7B%22query%22%3A%22${bill.bill_type}${bill.bill_number}%22%2C%22offset%22%3A0%7D`}
            target="_blank"
            rel="noopener noreferrer"
            className="border border-border px-4 py-2 rounded-lg text-sm font-semibold hover:bg-surface transition-colors flex items-center gap-1.5"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            GovInfo
          </a>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
        <MiniStat value={formatCurrency(totalSpending)} label="Total Spending" />
        <MiniStat value={formatNumber(spending.length)} label="Spending Items" />
        <MiniStat value={formatNumber(refs.length)} label="Legal Refs" />
        <MiniStat value={formatNumber(deadlines.length)} label="Deadlines" />
        <MiniStat value={formatNumber(entities.length)} label="Entities" />
      </div>

      {/* Pork Summary */}
      {pork.scored_items > 0 && pork.avg_score !== null && (
        <div className="bg-surface border border-border rounded-lg p-5 mb-8">
          <h2 className="font-semibold mb-3">Pork Score</h2>
          <div className="flex items-center gap-6">
            <div className="text-center">
              <div
                className="text-4xl font-bold"
                style={{ color: getPorkColor(pork.avg_score) }}
              >
                {Math.round(pork.avg_score)}
              </div>
              <div className="text-xs text-text-dim mt-1">Average</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-text">
                {pork.max_score}
              </div>
              <div className="text-xs text-text-dim mt-1">Highest</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-pork-high">
                {pork.high_pork_count}
              </div>
              <div className="text-xs text-text-dim mt-1">High Pork Items</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-text-dim">
                {pork.scored_items}
              </div>
              <div className="text-xs text-text-dim mt-1">Items Scored</div>
            </div>
          </div>
        </div>
      )}

      {/* Summary */}
      {summary && (
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-3">Summary</h2>
          <div className="bg-surface border border-border rounded-lg p-5 whitespace-pre-wrap text-sm leading-relaxed">
            {summary}
          </div>
        </div>
      )}

      {/* Top Spending */}
      <div className="mb-8">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-xl font-semibold">Top Spending Items</h2>
          <Link
            href={`/bills/${billId}/spending`}
            className="text-sm text-accent hover:underline"
          >
            View all {spending.length} items
          </Link>
        </div>
        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left text-xs text-text-dim font-semibold uppercase tracking-wider px-4 py-3">
                  Amount
                </th>
                <th className="text-left text-xs text-text-dim font-semibold uppercase tracking-wider px-4 py-3">
                  Purpose
                </th>
                <th className="text-left text-xs text-text-dim font-semibold uppercase tracking-wider px-4 py-3">
                  Recipient
                </th>
              </tr>
            </thead>
            <tbody>
              {spending.slice(0, 15).map((item) => (
                <tr
                  key={item.id}
                  className="border-b border-border last:border-0 hover:bg-surface-hover"
                >
                  <td className="px-4 py-2.5 font-mono text-sm text-accent whitespace-nowrap">
                    {cleanAmount(item.amount)}
                  </td>
                  <td className="px-4 py-2.5 text-sm max-w-sm truncate">
                    {truncate(item.purpose || "—", 80)}
                  </td>
                  <td className="px-4 py-2.5 text-sm text-text-dim">
                    {truncate(item.recipient || "—", 40)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Deadlines */}
      {deadlines.length > 0 && (
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-3">
            Deadlines ({deadlines.length})
          </h2>
          <div className="space-y-2">
            {deadlines.slice(0, 20).map((dl) => (
              <div
                key={dl.id}
                className="bg-surface border border-border rounded-lg px-4 py-3 flex items-start gap-4"
              >
                {dl.date && (
                  <span className="font-mono text-sm text-accent whitespace-nowrap">
                    {dl.date}
                  </span>
                )}
                <div className="flex-1 text-sm">
                  <span>{dl.action || "—"}</span>
                  {dl.responsible_entity && (
                    <span className="text-text-dim ml-2">
                      ({dl.responsible_entity})
                    </span>
                  )}
                </div>
              </div>
            ))}
            {deadlines.length > 20 && (
              <p className="text-sm text-text-dim text-center mt-2">
                + {deadlines.length - 20} more deadlines
              </p>
            )}
          </div>
        </div>
      )}

      {/* Entities */}
      {entities.length > 0 && (
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-3">
            Entities ({entities.length})
          </h2>
          <div className="flex flex-wrap gap-2">
            {entities.map((e, i) => (
              <span
                key={i}
                className="bg-surface border border-border rounded px-3 py-1.5 text-sm text-text-dim"
              >
                {e.name}
                {e.entity_type && (
                  <span className="text-xs text-accent ml-1.5">
                    {e.entity_type}
                  </span>
                )}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Legal References */}
      {refs.length > 0 && (
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-3">
            Legal References ({refs.length})
          </h2>
          <div className="space-y-4">
            {Object.entries(refsByType).map(([type, items]) => (
              <div key={type}>
                <h3 className="text-sm font-semibold text-text-dim uppercase tracking-wider mb-2">
                  {type.replace(/_/g, " ")} ({items.length})
                </h3>
                <div className="flex flex-wrap gap-1.5">
                  {items.slice(0, 30).map((ref, i) => {
                    const colorClass =
                      type === "us_code"
                        ? "border-blue text-blue"
                        : type === "public_law"
                          ? "border-pork-low text-pork-low"
                          : "border-accent text-accent";
                    return (
                      <span
                        key={i}
                        className={`border rounded px-2 py-0.5 text-xs ${colorClass}`}
                      >
                        {ref.ref_text}
                      </span>
                    );
                  })}
                  {items.length > 30 && (
                    <span className="text-xs text-text-dim px-2 py-0.5">
                      +{items.length - 30} more
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Versions */}
      {versions.length > 0 && (
        <div className="mb-8">
          <h2 className="text-xl font-semibold mb-3">
            Versions ({versions.length})
          </h2>
          <div className="bg-surface border border-border rounded-lg overflow-hidden">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left text-xs text-text-dim font-semibold uppercase tracking-wider px-4 py-3">
                    Version
                  </th>
                  <th className="text-left text-xs text-text-dim font-semibold uppercase tracking-wider px-4 py-3">
                    Name
                  </th>
                  <th className="text-left text-xs text-text-dim font-semibold uppercase tracking-wider px-4 py-3">
                    Fetched
                  </th>
                </tr>
              </thead>
              <tbody>
                {versions.map((v) => (
                  <tr
                    key={v.id}
                    className="border-b border-border last:border-0 hover:bg-surface-hover"
                  >
                    <td className="px-4 py-2.5 font-mono text-sm text-accent">
                      {v.version_code}
                    </td>
                    <td className="px-4 py-2.5 text-sm">
                      {v.version_name || "—"}
                    </td>
                    <td className="px-4 py-2.5 text-sm text-text-dim">
                      {v.fetched_at}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Sections count */}
      <div className="text-sm text-text-dim">
        {sections.length} sections analyzed
      </div>
    </div>
  );
}

function MiniStat({ value, label }: { value: string; label: string }) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4">
      <span className="block text-xl font-bold text-accent">{value}</span>
      <span className="block text-xs text-text-dim mt-0.5">{label}</span>
    </div>
  );
}
