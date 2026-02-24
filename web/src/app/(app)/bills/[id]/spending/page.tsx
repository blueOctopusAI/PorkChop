import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getBill, getSpending, getTotalSpending, getPorkScores } from "@/lib/db";
import { formatBillId, formatCurrencyFull } from "@/lib/format";
import { ExternalLink } from "lucide-react";
import SpendingRow from "./SpendingRow";

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const bill = getBill(Number(id));
  return { title: bill ? `${formatBillId(bill)} Spending` : "Not Found" };
}

export default async function SpendingPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const billId = Number(id);
  const bill = getBill(billId);
  if (!bill) notFound();

  const spending = getSpending(billId);
  const total = getTotalSpending(billId);
  const porkScores = getPorkScores(billId);
  const porkMap = new Map(porkScores.map((s) => [s.spending_item_id, s]));

  return (
    <div className="max-w-7xl">
      <div className="flex items-center gap-3 mb-2">
        <Link
          href={`/bills/${billId}`}
          className="text-text-dim hover:text-text text-sm"
        >
          {formatBillId(bill)}
        </Link>
        <span className="text-text-dim">/</span>
        <span className="text-sm">Spending</span>
      </div>
      <h1 className="text-2xl font-bold mb-2">
        Spending Breakdown
      </h1>
      <div className="flex items-center justify-between mb-6">
        <p className="text-text-dim text-sm">
          {spending.length} items totaling {formatCurrencyFull(total)}.
          Click any row to see the source text.
        </p>
        <a
          href={`https://www.congress.gov/bill/${bill.congress}th-congress/house-bill/${bill.bill_number}/text`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-text-dim hover:text-accent flex items-center gap-1 transition-colors"
        >
          <ExternalLink className="w-3 h-3" />
          Verify on Congress.gov
        </a>
      </div>

      <div className="bg-surface border border-border rounded-lg overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-border">
              <th className="w-8 px-4 py-3" />
              <th className="text-left text-xs text-text-dim font-semibold uppercase tracking-wider px-4 py-3">
                Amount
              </th>
              <th className="text-left text-xs text-text-dim font-semibold uppercase tracking-wider px-4 py-3">
                Purpose
              </th>
              <th className="text-left text-xs text-text-dim font-semibold uppercase tracking-wider px-4 py-3">
                Recipient
              </th>
              <th className="text-left text-xs text-text-dim font-semibold uppercase tracking-wider px-4 py-3">
                Availability
              </th>
              {porkScores.length > 0 && (
                <th className="text-center text-xs text-text-dim font-semibold uppercase tracking-wider px-4 py-3">
                  Pork
                </th>
              )}
            </tr>
          </thead>
          <tbody>
            {spending.map((item) => (
              <SpendingRow
                key={item.id}
                item={item}
                pork={porkMap.get(item.id)}
                hasPorkScores={porkScores.length > 0}
              />
            ))}
          </tbody>
        </table>
      </div>

      <p className="text-xs text-text-dim mt-4">
        All amounts extracted from the official bill text via regex pattern matching.
        Source text shown for each item is the surrounding context from which the amount was extracted.
        Always verify against the{" "}
        <a
          href={`https://www.congress.gov/bill/${bill.congress}th-congress/house-bill/${bill.bill_number}/text`}
          target="_blank"
          rel="noopener noreferrer"
          className="text-accent hover:underline"
        >
          official bill text
        </a>.
      </p>
    </div>
  );
}
