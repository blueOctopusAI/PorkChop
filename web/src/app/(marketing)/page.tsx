import Link from "next/link";
import Image from "next/image";
import { getStats } from "@/lib/db";
import { formatCurrency, formatNumber } from "@/lib/format";
import {
  FileText,
  DollarSign,
  Clock,
  Building2,
  Scale,
  GitCompare,
} from "lucide-react";

const features = [
  {
    icon: FileText,
    title: "Spending Breakdowns",
    description:
      "Every dollar amount extracted and categorized — who gets it, what for, and when it expires.",
  },
  {
    icon: Scale,
    title: "Pork Scoring",
    description:
      "Each spending item scored 0-100 for pork likelihood. Earmarks, geographic specificity, and unrelated spending flagged automatically.",
  },
  {
    icon: GitCompare,
    title: "Version Comparison",
    description:
      "See exactly what changed between bill drafts. What spending was added in the amendment? What was quietly removed?",
  },
  {
    icon: Clock,
    title: "Deadline Tracking",
    description:
      "Every \"not later than\" date extracted with the responsible entity and required action.",
  },
  {
    icon: Building2,
    title: "Entity Mapping",
    description:
      "Departments, agencies, and offices identified throughout the bill with their roles and responsibilities.",
  },
  {
    icon: DollarSign,
    title: "Plain English Summaries",
    description:
      "AI-generated summaries for every section. No legal jargon — just what the bill actually does.",
  },
];

export default function HomePage() {
  const stats = getStats();

  return (
    <div>
      {/* Hero */}
      <section className="text-center py-24 px-6">
        <div className="mb-6">
          <Image
            src="/porkchop-logo.jpg"
            alt="PorkChop Logo"
            width={180}
            height={180}
            className="mx-auto rounded-2xl"
            priority
            unoptimized
          />
        </div>
        <h1 className="text-5xl md:text-6xl font-bold text-accent mb-4">
          PorkChop
        </h1>
        <p className="text-xl text-text-dim mb-8 max-w-2xl mx-auto">
          AI that reads the bills so you don&apos;t have to.
        </p>
        <p className="text-text-dim mb-10 max-w-xl mx-auto">
          Drop in a bill number. Get back spending breakdowns, pork scores,
          legal references, deadlines, and plain English summaries. In minutes,
          not hours.
        </p>
        <div className="flex justify-center gap-4">
          <Link
            href="/dashboard"
            className="bg-accent text-bg px-6 py-3 rounded-lg font-semibold hover:bg-accent-dim hover:text-white transition-colors"
          >
            Launch App
          </Link>
          <Link
            href="/how-it-works"
            className="border border-border text-text px-6 py-3 rounded-lg font-semibold hover:bg-surface transition-colors"
          >
            How It Works
          </Link>
        </div>
      </section>

      {/* Live Stats */}
      {stats.bills_analyzed > 0 && (
        <section className="max-w-4xl mx-auto px-6 mb-16">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard
              value={formatNumber(stats.bills_analyzed)}
              label="Bills Analyzed"
            />
            <StatCard
              value={formatNumber(stats.spending_items)}
              label="Spending Items"
            />
            <StatCard
              value={formatCurrency(stats.total_spending)}
              label="Total Tracked"
            />
            <StatCard
              value={formatNumber(stats.items_scored)}
              label="Items Scored"
            />
          </div>
        </section>
      )}

      {/* Features */}
      <section className="max-w-6xl mx-auto px-6 py-16">
        <h2 className="text-3xl font-bold text-center mb-12">
          What You Get
        </h2>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((f) => (
            <div
              key={f.title}
              className="bg-surface border border-border rounded-lg p-6 hover:border-accent/30 transition-colors"
            >
              <f.icon className="w-8 h-8 text-accent mb-3" />
              <h3 className="font-semibold text-lg mb-2">{f.title}</h3>
              <p className="text-text-dim text-sm">{f.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="text-center py-20 px-6">
        <h2 className="text-3xl font-bold mb-4">
          See it in action
        </h2>
        <p className="text-text-dim mb-8 max-w-lg mx-auto">
          H.R. 10515 — the $192 billion spending bill with Helene disaster
          relief — is already analyzed and waiting.
        </p>
        <Link
          href="/dashboard"
          className="bg-accent text-bg px-6 py-3 rounded-lg font-semibold hover:bg-accent-dim hover:text-white transition-colors"
        >
          View the Dashboard
        </Link>
      </section>
    </div>
  );
}

function StatCard({ value, label }: { value: string; label: string }) {
  return (
    <div className="bg-surface border border-border rounded-lg p-4 text-center">
      <span className="block text-2xl font-bold text-accent">{value}</span>
      <span className="block text-xs text-text-dim mt-1">{label}</span>
    </div>
  );
}
