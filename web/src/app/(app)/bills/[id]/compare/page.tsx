import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getBill, getVersions, getComparison } from "@/lib/db";
import { formatBillId } from "@/lib/format";
import CompareForm from "./CompareForm";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const bill = getBill(Number(id));
  return { title: bill ? `${formatBillId(bill)} Compare` : "Not Found" };
}

export default async function ComparePage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ from?: string; to?: string }>;
}) {
  const { id } = await params;
  const sp = await searchParams;
  const billId = Number(id);
  const bill = getBill(billId);
  if (!bill) notFound();

  const versions = getVersions(billId);
  const fromId = sp.from ? Number(sp.from) : undefined;
  const toId = sp.to ? Number(sp.to) : undefined;

  let comparison = null;
  let changes: Array<{ section: string; type: string; detail: string }> = [];
  let spendingDiff: Array<{ type: string; amount: string; text: string }> = [];

  if (fromId && toId) {
    comparison = getComparison(billId, fromId, toId);
    if (comparison?.changes_json) {
      try {
        changes = JSON.parse(comparison.changes_json);
      } catch {
        /* ignore */
      }
    }
    if (comparison?.spending_diff_json) {
      try {
        spendingDiff = JSON.parse(comparison.spending_diff_json);
      } catch {
        /* ignore */
      }
    }
  }

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
        <span className="text-sm">Compare</span>
      </div>
      <h1 className="text-2xl font-bold mb-6">Version Comparison</h1>

      {versions.length < 2 ? (
        <div className="bg-surface border border-border rounded-lg p-8 text-center text-text-dim">
          Need at least 2 versions to compare. This bill has {versions.length}.
        </div>
      ) : (
        <>
          <CompareForm billId={billId} versions={versions} fromId={fromId} toId={toId} />

          {comparison && (
            <div className="mt-8 space-y-6">
              {/* Stats */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-surface border border-border rounded-lg p-4">
                  <span className="block text-2xl font-bold text-green-500">
                    +{comparison.additions_count}
                  </span>
                  <span className="text-xs text-text-dim">Additions</span>
                </div>
                <div className="bg-surface border border-border rounded-lg p-4">
                  <span className="block text-2xl font-bold text-red-500">
                    -{comparison.removals_count}
                  </span>
                  <span className="text-xs text-text-dim">Removals</span>
                </div>
              </div>

              {/* Spending Changes */}
              {spendingDiff.length > 0 && (
                <div>
                  <h2 className="text-lg font-semibold mb-3">
                    Spending Changes
                  </h2>
                  <div className="space-y-2">
                    {spendingDiff.map((d, i) => (
                      <div
                        key={i}
                        className={`bg-surface border rounded-lg px-4 py-3 text-sm ${
                          d.type === "added"
                            ? "border-green-500/30"
                            : "border-red-500/30"
                        }`}
                      >
                        <span
                          className={
                            d.type === "added"
                              ? "text-green-500"
                              : "text-red-500"
                          }
                        >
                          {d.type === "added" ? "+" : "-"} {d.amount}
                        </span>
                        <span className="text-text-dim ml-3">{d.text}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Section Changes */}
              {changes.length > 0 && (
                <div>
                  <h2 className="text-lg font-semibold mb-3">
                    Section Changes
                  </h2>
                  <div className="space-y-2">
                    {changes.map((c, i) => (
                      <div
                        key={i}
                        className="bg-surface border border-border rounded-lg px-4 py-3"
                      >
                        <div className="flex items-center gap-3 mb-1">
                          <span className="text-accent text-sm font-mono">
                            {c.section}
                          </span>
                          <span
                            className={`text-xs px-1.5 py-0.5 rounded ${
                              c.type === "added"
                                ? "bg-green-500/20 text-green-400"
                                : c.type === "removed"
                                  ? "bg-red-500/20 text-red-400"
                                  : "bg-amber-500/20 text-amber-400"
                            }`}
                          >
                            {c.type}
                          </span>
                        </div>
                        <p className="text-sm text-text-dim">{c.detail}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </>
      )}
    </div>
  );
}
