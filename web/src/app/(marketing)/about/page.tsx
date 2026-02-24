import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "About",
  description:
    "PorkChop was built for a congressional staffer who needed to read 1,500-page bills overnight. Now it's open source.",
};

export default function AboutPage() {
  return (
    <div className="max-w-3xl mx-auto px-6 py-16">
      <h1 className="text-4xl font-bold text-accent mb-8">About PorkChop</h1>

      {/* Origin Story */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold mb-4">The Problem</h2>
        <p className="text-text-dim mb-4">
          Congressional staff receive massive omnibus bills hours before votes.
          The &ldquo;Further Continuing Appropriations and Disaster Relief
          Supplemental Appropriations Act, 2025&rdquo; is 1,574,896 bytes of
          text. No human can read this in a night.
        </p>
        <p className="text-text-dim mb-4">
          Tim&apos;s brother is chief of staff for Congressman Thomas Massie.
          Staff get 1,500-page bills dropped on their desk the night before a
          vote with no time to read them. They need to know: Where is the money
          going? What deadlines are being set? What was added in the last
          amendment?
        </p>
        <p className="text-text-dim">
          PorkChop was built to answer those questions.
        </p>
      </section>

      {/* How It Started */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold mb-4">How It Started</h2>
        <p className="text-text-dim mb-4">
          December 2024: a regex-only prototype that could clean GPO formatting
          artifacts and extract dollar amounts from raw bill text. It worked, but
          regex can&apos;t tell you <em>why</em> money is being spent or whether
          a spending item is related to the bill&apos;s stated purpose.
        </p>
        <p className="text-text-dim">
          February 2026: rebuilt from the ground up with Claude-powered semantic
          analysis, Congress.gov API integration, a web frontend, version
          comparison, and pork scoring. The regex layer is retained — it&apos;s
          free, fast, and reliable for structured data. Claude adds the semantic
          understanding layer on top.
        </p>
      </section>

      {/* What It Does */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold mb-4">What It Does</h2>
        <div className="bg-surface border border-border rounded-lg p-6">
          <p className="text-text-dim mb-4">
            Drop in a bill number or raw text file. Within minutes you get:
          </p>
          <ul className="space-y-2 text-text-dim">
            <li className="flex items-start gap-2">
              <span className="text-accent mt-1">&#x2022;</span>
              Plain English summary of every section
            </li>
            <li className="flex items-start gap-2">
              <span className="text-accent mt-1">&#x2022;</span>
              Every dollar amount with what it&apos;s for and who controls it
            </li>
            <li className="flex items-start gap-2">
              <span className="text-accent mt-1">&#x2022;</span>
              Every deadline and who&apos;s responsible
            </li>
            <li className="flex items-start gap-2">
              <span className="text-accent mt-1">&#x2022;</span>
              Every new program or authority created
            </li>
            <li className="flex items-start gap-2">
              <span className="text-accent mt-1">&#x2022;</span>
              Comparison to previous versions — what was added in the amendment?
            </li>
            <li className="flex items-start gap-2">
              <span className="text-accent mt-1">&#x2022;</span>
              Pork score — anomalous or unrelated spending items flagged
            </li>
          </ul>
        </div>
      </section>

      {/* Open Source */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold mb-4">Open Source</h2>
        <p className="text-text-dim mb-4">
          Bill text is public record — US government documents have no copyright.
          PorkChop is MIT licensed. The data is free, the tool is free, and the
          APIs it uses are free.
        </p>
        <p className="text-text-dim">
          Commercial tools like FiscalNote, Plural Policy, and BillTrack50
          charge enterprise prices for similar analysis. PorkChop makes this
          accessible to everyone — congressional staff, journalists, lobbyists,
          and citizens.
        </p>
      </section>

      {/* Built By */}
      <section className="mb-12">
        <h2 className="text-2xl font-bold mb-4">Built By</h2>
        <p className="text-text-dim">
          PorkChop is a{" "}
          <span className="text-accent">Blue Octopus Technology</span> project.
        </p>
      </section>

      <div className="text-center mt-16">
        <Link
          href="/dashboard"
          className="bg-accent text-bg px-6 py-3 rounded-lg font-semibold hover:bg-accent-dim hover:text-white transition-colors"
        >
          Try It Now
        </Link>
      </div>
    </div>
  );
}
