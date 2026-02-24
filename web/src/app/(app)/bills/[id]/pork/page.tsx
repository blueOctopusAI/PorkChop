import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getBill, getPorkScores, getPorkSummary } from "@/lib/db";
import { formatBillId, truncate, cleanAmount } from "@/lib/format";
import { getPorkBadgeClass, getPorkColor, getPorkLabel } from "@/lib/pork-colors";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const bill = getBill(Number(id));
  return { title: bill ? `${formatBillId(bill)} Pork Analysis` : "Not Found" };
}

export default async function PorkPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const billId = Number(id);
  const bill = getBill(billId);
  if (!bill) notFound();

  const scores = getPorkScores(billId);
  const summary = getPorkSummary(billId);

  // Distribution
  const lowCount = scores.filter((s) => s.score < 30).length;
  const medCount = scores.filter((s) => s.score >= 30 && s.score < 60).length;
  const highCount = scores.filter((s) => s.score >= 60).length;

  return (
    <div className="max-w-6xl">
      <div className="flex items-center gap-3 mb-2">
        <Link
          href={`/bills/${billId}`}
          className="text-text-dim hover:text-text text-sm"
        >
          {formatBillId(bill)}
        </Link>
        <span className="text-text-dim">/</span>
        <span className="text-sm">Pork Analysis</span>
      </div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Pork Analysis</h1>
        <Link
          href={`/bills/${billId}/spending`}
          className="text-sm text-accent hover:underline"
        >
          Full Spending Table &rarr;
        </Link>
      </div>

      {scores.length === 0 ? (
        <div className="bg-surface border border-border rounded-lg p-8 text-center text-text-dim">
          <p>No pork scores yet.</p>
          <p className="text-sm font-mono mt-2">porkchop score {billId}</p>
        </div>
      ) : (
        <>
          {/* Summary Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div className="bg-surface border border-border rounded-lg p-5 text-center">
              <span
                className="block text-4xl font-bold"
                style={{
                  color: summary.avg_score
                    ? getPorkColor(summary.avg_score)
                    : undefined,
                }}
              >
                {summary.avg_score !== null
                  ? Math.round(summary.avg_score)
                  : "—"}
              </span>
              <span className="block text-xs text-text-dim mt-1">
                Average Score
              </span>
            </div>
            <div className="bg-surface border border-border rounded-lg p-5 text-center">
              <span className="block text-4xl font-bold text-text">
                {summary.max_score ?? "—"}
              </span>
              <span className="block text-xs text-text-dim mt-1">
                Highest Score
              </span>
            </div>
            <div className="bg-surface border border-border rounded-lg p-5 text-center">
              <span className="block text-4xl font-bold text-pork-high">
                {summary.high_pork_count}
              </span>
              <span className="block text-xs text-text-dim mt-1">
                High Pork (&gt;70)
              </span>
            </div>
            <div className="bg-surface border border-border rounded-lg p-5 text-center">
              <span className="block text-4xl font-bold text-text-dim">
                {summary.scored_items}
              </span>
              <span className="block text-xs text-text-dim mt-1">
                Items Scored
              </span>
            </div>
          </div>

          {/* Distribution Bar */}
          <div className="bg-surface border border-border rounded-lg p-5 mb-8">
            <h2 className="font-semibold mb-3">Score Distribution</h2>
            <div className="flex rounded-lg overflow-hidden h-8">
              {lowCount > 0 && (
                <div
                  className="bg-green-500 flex items-center justify-center text-xs font-bold text-black"
                  style={{
                    width: `${(lowCount / scores.length) * 100}%`,
                  }}
                >
                  {lowCount}
                </div>
              )}
              {medCount > 0 && (
                <div
                  className="bg-amber-500 flex items-center justify-center text-xs font-bold text-black"
                  style={{
                    width: `${(medCount / scores.length) * 100}%`,
                  }}
                >
                  {medCount}
                </div>
              )}
              {highCount > 0 && (
                <div
                  className="bg-red-500 flex items-center justify-center text-xs font-bold text-white"
                  style={{
                    width: `${(highCount / scores.length) * 100}%`,
                  }}
                >
                  {highCount}
                </div>
              )}
            </div>
            <div className="flex justify-between text-xs text-text-dim mt-2">
              <span>Clean (0-29): {lowCount}</span>
              <span>Watch (30-59): {medCount}</span>
              <span>Pork (60-100): {highCount}</span>
            </div>
          </div>

          {/* Scored Items Table */}
          <h2 className="text-xl font-semibold mb-3">All Scored Items</h2>
          <div className="bg-surface border border-border rounded-lg overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-center text-xs text-text-dim font-semibold uppercase tracking-wider px-4 py-3 w-20">
                    Score
                  </th>
                  <th className="text-left text-xs text-text-dim font-semibold uppercase tracking-wider px-4 py-3">
                    Amount
                  </th>
                  <th className="text-left text-xs text-text-dim font-semibold uppercase tracking-wider px-4 py-3">
                    Purpose
                  </th>
                  <th className="text-left text-xs text-text-dim font-semibold uppercase tracking-wider px-4 py-3">
                    Flags
                  </th>
                </tr>
              </thead>
              <tbody>
                {scores.map((s) => {
                  const rowBg =
                    s.score >= 60
                      ? "bg-red-500/5"
                      : s.score >= 30
                        ? "bg-amber-500/5"
                        : "";
                  return (
                    <tr
                      key={s.id}
                      className={`border-b border-border last:border-0 hover:bg-surface-hover ${rowBg}`}
                    >
                      <td className="px-4 py-2.5 text-center">
                        <span
                          className={`inline-block text-xs font-bold px-2.5 py-0.5 rounded ${getPorkBadgeClass(s.score)}`}
                        >
                          {s.score}
                        </span>
                      </td>
                      <td className="px-4 py-2.5 font-mono text-sm text-accent whitespace-nowrap">
                        {s.amount ? cleanAmount(s.amount) : "—"}
                      </td>
                      <td className="px-4 py-2.5 text-sm max-w-md">
                        {truncate(s.purpose || "—", 100)}
                      </td>
                      <td className="px-4 py-2.5 text-xs text-text-dim max-w-xs">
                        {s.flags || "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
