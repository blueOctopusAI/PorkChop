import type { Metadata } from "next";
import Link from "next/link";
import { searchBills } from "@/lib/db";
import { formatBillId, formatCurrency, truncate } from "@/lib/format";
import { getTotalSpending } from "@/lib/db";
import SearchInput from "./SearchInput";

export const metadata: Metadata = { title: "Search" };

export default async function SearchPage({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const sp = await searchParams;
  const query = sp.q || "";
  const results = query ? searchBills(query) : [];

  return (
    <div className="max-w-4xl">
      <h1 className="text-3xl font-bold mb-6">Search Bills</h1>

      <SearchInput defaultValue={query} />

      {query && (
        <p className="text-sm text-text-dim mb-4">
          {results.length} result{results.length !== 1 ? "s" : ""} for &ldquo;{query}&rdquo;
        </p>
      )}

      {results.length > 0 && (
        <div className="space-y-3">
          {results.map((bill) => {
            const total = getTotalSpending(bill.id);
            return (
              <Link
                key={bill.id}
                href={`/bills/${bill.id}`}
                className="block bg-surface border border-border rounded-lg p-5 hover:border-accent/30 transition-colors"
              >
                <div className="flex items-start justify-between mb-2">
                  <span className="font-mono text-sm text-accent">
                    {formatBillId(bill)}
                  </span>
                  <span className="text-sm text-text-dim">
                    {formatCurrency(total)}
                  </span>
                </div>
                <h3 className="text-sm font-medium mb-1">
                  {bill.title || "Untitled"}
                </h3>
                {bill.summary && (
                  <p className="text-xs text-text-dim">
                    {truncate(bill.summary, 200)}
                  </p>
                )}
              </Link>
            );
          })}
        </div>
      )}

      {query && results.length === 0 && (
        <div className="bg-surface border border-border rounded-lg p-8 text-center text-text-dim">
          No bills match &ldquo;{query}&rdquo;
        </div>
      )}
    </div>
  );
}
