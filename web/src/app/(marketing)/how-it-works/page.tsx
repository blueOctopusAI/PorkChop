import type { Metadata } from "next";
import {
  Eraser,
  Scissors,
  Search,
  Brain,
  GitCompare,
  Target,
  Globe,
} from "lucide-react";

export const metadata: Metadata = {
  title: "How It Works",
  description:
    "How PorkChop turns raw congressional bill text into structured, searchable spending data.",
};

const stages = [
  {
    icon: Eraser,
    number: 1,
    title: "Clean",
    description:
      "Raw government text is full of formatting noise — headers, page numbers, artifacts. PorkChop strips all of that out so only the actual legislation remains.",
    detail: "Typically removes 20%+ of junk from raw text",
  },
  {
    icon: Scissors,
    number: 2,
    title: "Chunk",
    description:
      "The cleaned text is split along the bill's natural structure — Divisions, Titles, and Sections. Each chunk becomes a logical unit that can be analyzed independently.",
    detail: "Follows the bill's own organizational structure",
  },
  {
    icon: Search,
    number: 3,
    title: "Extract",
    description:
      "Every dollar amount, legal reference, deadline, and government entity is automatically pulled from the text. You get a complete inventory of what's in the bill.",
    detail: "Hundreds of data points extracted per bill",
  },
  {
    icon: Brain,
    number: 4,
    title: "Analyze",
    description:
      "AI reads each section and writes a plain English summary, identifies who gets the money, flags new authorities being created, and spots potential pork.",
    detail: "Section-level detail with a bill-level synthesis",
  },
  {
    icon: GitCompare,
    number: 5,
    title: "Compare",
    description:
      "Bills change as they move through Congress. PorkChop tracks what changed between versions — spending added, removed, or modified.",
    detail: "Introduced → Committee → Enrolled: see every change",
  },
  {
    icon: Target,
    number: 6,
    title: "Score",
    description:
      "Every spending item gets a pork score from 0 to 100 based on earmark signals, geographic specificity, and Citizens Against Government Waste criteria.",
    detail: "Combines rule-based checks with AI judgment",
  },
  {
    icon: Globe,
    number: 7,
    title: "Browse",
    description:
      "Everything is browsable through the web interface, accessible via API for developers, and available through MCP so AI assistants can query bill data directly.",
    detail: "Built for humans, developers, and AI alike",
  },
];

export default function HowItWorksPage() {
  return (
    <div className="max-w-4xl mx-auto px-6 py-16">
      <h1 className="text-4xl font-bold text-accent mb-4">How It Works</h1>
      <p className="text-text-dim text-lg mb-12">
        PorkChop runs a 7-stage pipeline that turns raw congressional bill text
        into structured, searchable data you can actually understand.
      </p>

      {/* Pipeline */}
      <div className="space-y-8">
        {stages.map((stage) => (
          <div
            key={stage.number}
            className="flex gap-6 bg-surface border border-border rounded-lg p-6 hover:border-accent/30 transition-colors"
          >
            <div className="flex-shrink-0">
              <div className="w-12 h-12 rounded-full bg-accent/10 flex items-center justify-center">
                <stage.icon className="w-6 h-6 text-accent" />
              </div>
            </div>
            <div>
              <div className="flex items-center gap-3 mb-2">
                <span className="text-accent font-mono text-sm">
                  Stage {stage.number}
                </span>
                <h3 className="font-semibold text-lg">{stage.title}</h3>
              </div>
              <p className="text-text-dim text-sm mb-2">
                {stage.description}
              </p>
              <p className="text-xs text-accent/70 font-mono">
                {stage.detail}
              </p>
            </div>
          </div>
        ))}
      </div>

      {/* Data Sources */}
      <section className="mt-16">
        <h2 className="text-2xl font-bold mb-6">Where the Data Comes From</h2>
        <div className="grid md:grid-cols-2 gap-4">
          <div className="bg-surface border border-border rounded-lg p-5">
            <h3 className="font-semibold mb-2">Congress.gov</h3>
            <p className="text-text-dim text-sm">
              Bill metadata, sponsors, cosponsors, legislative actions, and links to every text version.
            </p>
          </div>
          <div className="bg-surface border border-border rounded-lg p-5">
            <h3 className="font-semibold mb-2">GovInfo</h3>
            <p className="text-text-dim text-sm">
              The full official bill text as published by the Government Publishing Office.
            </p>
          </div>
        </div>
        <p className="text-text-dim text-sm mt-4">
          Every number PorkChop shows links back to the original source text so you can verify it yourself.
        </p>
      </section>
    </div>
  );
}
