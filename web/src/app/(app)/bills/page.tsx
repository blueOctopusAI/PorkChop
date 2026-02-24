import type { Metadata } from "next";
import Link from "next/link";
import { listBills, getTotalSpending } from "@/lib/db";
import { formatCurrencyFull, formatBillId } from "@/lib/format";

export const metadata: Metadata = { title: "Bills" };

export default function BillsPage() {
  const bills = listBills(100);

  return (
    <div className="max-w-6xl">
      <h1 className="text-3xl font-bold mb-6">Bills</h1>

      {bills.length === 0 ? (
        <div className="bg-surface border border-border rounded-lg p-8 text-center text-text-dim">
          No bills analyzed yet.
        </div>
      ) : (
        <div className="bg-surface border border-border rounded-lg overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left text-xs text-text-dim font-semibold uppercase tracking-wider px-4 py-3">
                  Bill
                </th>
                <th className="text-left text-xs text-text-dim font-semibold uppercase tracking-wider px-4 py-3">
                  Title
                </th>
                <th className="text-right text-xs text-text-dim font-semibold uppercase tracking-wider px-4 py-3">
                  Total Spending
                </th>
                <th className="text-left text-xs text-text-dim font-semibold uppercase tracking-wider px-4 py-3">
                  Status
                </th>
              </tr>
            </thead>
            <tbody>
              {bills.map((bill) => {
                const total = getTotalSpending(bill.id);
                return (
                  <tr
                    key={bill.id}
                    className="border-b border-border last:border-0 hover:bg-surface-hover transition-colors"
                  >
                    <td className="px-4 py-3">
                      <Link
                        href={`/bills/${bill.id}`}
                        className="font-mono text-sm text-accent hover:underline"
                      >
                        {formatBillId(bill)}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-sm max-w-md truncate">
                      {bill.title || "Untitled"}
                    </td>
                    <td className="px-4 py-3 text-sm text-right font-mono">
                      {formatCurrencyFull(total)}
                    </td>
                    <td className="px-4 py-3 text-sm text-text-dim">
                      {bill.status || "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
