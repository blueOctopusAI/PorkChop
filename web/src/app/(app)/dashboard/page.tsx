import type { Metadata } from "next";
import Link from "next/link";
import { listBills, getStats, getTotalSpending, getPorkSummary } from "@/lib/db";
import { formatCurrency, formatNumber, formatBillId } from "@/lib/format";
import { getPorkBadgeClass, getPorkLabel } from "@/lib/pork-colors";

export const metadata: Metadata = { title: "Dashboard" };

export default function DashboardPage() {
  const stats = getStats();
  const bills = listBills(20);

  return (
    <div className="max-w-6xl">
      <h1 className="text-3xl font-bold mb-6">Dashboard</h1>

      {/* Stats Row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard value={formatNumber(stats.bills_analyzed)} label="Bills Analyzed" />
        <StatCard value={formatNumber(stats.spending_items)} label="Spending Items" />
        <StatCard value={formatCurrency(stats.total_spending)} label="Total Tracked" />
        <StatCard value={formatNumber(stats.items_scored)} label="Items Scored" />
      </div>

      {/* Bills Grid */}
      <h2 className="text-xl font-semibold mb-4">Analyzed Bills</h2>
      {bills.length === 0 ? (
        <div className="bg-surface border border-border rounded-lg p-8 text-center text-text-dim">
          <p className="mb-2">No bills analyzed yet.</p>
          <p className="text-sm font-mono">
            porkchop process &lt;file&gt; --bill-id HR-10515
          </p>
        </div>
      ) : (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
          {bills.map((bill) => (
            <BillCard key={bill.id} bill={bill} />
          ))}
        </div>
      )}
    </div>
  );
}

function StatCard({ value, label }: { value: string; label: string }) {
  return (
    <div className="bg-surface border border-border rounded-lg p-5">
      <span className="block text-2xl font-bold text-accent">{value}</span>
      <span className="block text-xs text-text-dim mt-1">{label}</span>
    </div>
  );
}

function BillCard({ bill }: { bill: ReturnType<typeof listBills>[number] }) {
  const total = getTotalSpending(bill.id);
  const pork = getPorkSummary(bill.id);

  return (
    <Link
      href={`/bills/${bill.id}`}
      className="bg-surface border border-border rounded-lg p-5 hover:border-accent/30 transition-colors block"
    >
      <div className="flex items-start justify-between mb-2">
        <span className="font-mono text-sm text-accent">
          {formatBillId(bill)}
        </span>
        {pork.scored_items > 0 && pork.avg_score !== null && (
          <span
            className={`text-xs font-bold px-2 py-0.5 rounded ${getPorkBadgeClass(pork.avg_score)}`}
          >
            {Math.round(pork.avg_score)} {getPorkLabel(pork.avg_score)}
          </span>
        )}
      </div>
      <h3 className="text-sm font-medium mb-3 line-clamp-2">
        {bill.title || "Untitled"}
      </h3>
      <div className="flex justify-between text-xs text-text-dim">
        <span>{formatCurrency(total)}</span>
        <span>{bill.status || "Unknown"}</span>
      </div>
    </Link>
  );
}
