# HOW-IT-WORKS.md — PorkChop

## Overview

PorkChop is a legislative bill text processor that turns raw congressional documents into structured, queryable data. The pipeline takes a 1,500+ page bill and outputs spending breakdowns, legal references, deadlines, entity maps, plain English summaries, and pork scores — stored in SQLite and browsable via a web UI.

## The Problem

Congressional staff receive massive omnibus bills hours before votes. The "Further Continuing Appropriations and Disaster Relief Supplemental Appropriations Act, 2025" is 1,574,896 bytes of text with embedded formatting artifacts from the Government Publishing Office's XML-to-text pipeline. No human can read this in a night.

## System Architecture

```
Python CLI (writes)             Next.js Web (reads)           MCP Server (reads)
  │                                │                              │
  ▼                                ▼                              ▼
Ingestion → Processing         App Pages + REST API           12 LLM tools
(Congress.gov API,             (marketing, dashboard,         (stdio transport)
 GovInfo API,                   bills, spending, pork,
 local file import)             compare, search)
  │                                │                              │
  │  clean → chunk → extract       │  13 API endpoints            │
  │  analyze → compare → score     │  under /api/v1/              │
  │                                │                              │
  └────────────────────────────────┼──────────────────────────────┘
                                   │
                              SQLite DB
                         (10 tables, WAL mode)
```

## Pipeline Stages

### Stage 1: Text Cleaning (`cleaner.py`)

Raw congressional text contains significant formatting noise from the GPO publishing system:

```
VerDate Nov 24 2008 17:46 Dec 17, 2024 Jkt 000000 PO 00000 Frm 00001 Fmt 6652 Sfmt 6211
C:\USERS\KSALMON\APPDATA\ROAMING\SOFTQUAD\XMETAL\11.0\GEN\C\D121724.03
December 17, 2024 (5:46 p.m.)
I:\FY25\SUPPS\D121724.038.XML
l:\v7\121724\7121724.012.xml (955033|8)
```

Three cleaning phases:

1. **Line removal** — VerDate headers, Jkt lines, XML file references, timestamps, standalone page numbers, Windows file paths
2. **Inline cleanup** — Strip leading line numbers, fix embedded-number OCR artifacts (e.g., "strate2 gies" -> "strategies"). Improved from prototype: only matches lowercase-to-lowercase to avoid mangling "42 U.S.C." style references.
3. **Normalization** — Collapse whitespace, remove excessive blank lines

Result: 37,261 raw lines -> 29,525 clean lines (21% reduction)

### Stage 2: Chunking (`chunker.py`)

Two strategies, both returning structured `Chunk` objects with metadata:

**Structure-based** (default): Split on DIVISION and TITLE markers. Preserves legislative structure — each chunk represents a logical unit. Oversized sections auto-split into sub-chunks.

**Size-based**: Split at configurable character boundaries (default 20K). Simple, predictable sizes for LLM context windows.

Each chunk carries: `chunk_id`, `text`, `division`, `title`, `position`, `char_count`.

### Stage 3: Fact Extraction (`extractor.py`)

Regex-based extraction produces structured dicts per chunk:

- **US Code references** — "42 U.S.C. 3030a" pattern
- **Public Laws** — "Public Law 118-42" pattern
- **Named Acts** — Multi-word phrases ending in "Act" or "Code"
- **Funding** — Dollar amounts with multi-strategy purpose extraction, recipient detection, availability, fiscal years. Handles scale words (million, billion). All patterns use `re.DOTALL` to cross newlines in raw bill text.
  - 5 purpose extraction patterns: "necessary expenses", "additional amount for FY...for X", "made available for", "carry out/conduct/provide/make/fund", generic "for X" with negative lookaheads
  - Backward purpose search: tries forward patterns on preceding text, then matches uppercase subheadings (e.g., "OPERATIONS AND MAINTENANCE, NAVY"), then legislative structure headings
  - Recipient extraction: "transferred to X", "to the Secretary of X", "to the Department of X", agency patterns
  - Junk purpose filter: rejects fiscal year references, "such purpose", "this section/chapter", "to the Secretary", "related expenses", emergency requirement boilerplate, quoted amounts
  - Purpose quality gate: rejects strings under 10 chars
  - Result: 40% of spending items have meaningful purposes (up from ~5% in v0)
- **Dates** — Full date pattern + fiscal year extraction
- **Deadlines** — "not later than" with forward-looking action extraction (captures text AFTER the deadline date, not before). Garbage filter rejects fragments starting with punctuation, "Provided, That" clauses, or section headers. 92% of deadlines have meaningful action text.
- **Duties** — "The Secretary shall/may/must..." with entity and action
- **Entities** — Departments, Offices, Bureaus, Agencies with deduplication

### Stage 4: Claude Analysis (`analyzer.py`)

Replaces regex with semantic understanding for deeper analysis:

- **Per-section analysis** (Haiku) — plain English summary, funding with recipients, new authorities, pork flags
- **Bill-level summary** (Sonnet) — synthesizes all section analyses into a comprehensive accessible overview
- **Structured JSON output** — enforced schema for consistent data
- **Cost**: ~$0.50-2.00 per bill using Haiku for bulk, Sonnet only for synthesis

Regex extraction is retained as a fast, free baseline. Claude adds the semantic layer.

### Stage 5: Version Comparison (`comparator.py`)

Tracks what changed between bill versions (Introduced -> Enrolled):

- **Text diff** — line-by-line additions/removals with similarity ratio
- **Spending detection** — automatically finds dollar amounts in diff lines
- **Section matching** — aligns sections across versions by heading
- **Semantic comparison** (optional, Claude) — explains what each change means
- **Changelog generation** — human-readable summary across all versions

### Stage 6: Pork Scoring (`scorer.py`)

Scores spending items 0-100 for pork likelihood:

**Heuristic pre-screen** (free, fast):
- Earmark signals: "located in", "county of", "university of", "memorial", "bridge"
- Geographic specificity: county, district, parish references
- Named entity specificity: universities, hospitals, museums, foundations
- Small specific amounts in large bills
- Purpose unrelated to bill title
- Open-ended availability ("until expended")

**AI deep scoring** (optional, Claude):
- Contextual analysis against bill purpose
- CAGW Pig Book criteria evaluation
- Blended score: 30% heuristic + 70% AI

### Stage 7: Web Frontend (`web/`)

Next.js 16 app with dark theme and pork-score color coding. Three interfaces:

**Marketing pages** (`(marketing)/`): Landing page, How It Works, About — explain what PorkChop is.

**App pages** (`(app)/`):

| Page | What |
|------|------|
| `/dashboard` | Recent bills, aggregate stats |
| `/bills` | Bill list with sorting |
| `/bills/:id` | Bill detail — summary, spending, deadlines, refs, entities, pork, external links to Congress.gov/GovInfo, AI chat |
| `/bills/:id/spending` | Full spending table with expandable source text and pork scores |
| `/bills/:id/pork` | Pork analysis — distribution, scored items |
| `/bills/:id/compare` | Version comparison picker + diff view |
| `/process` | On-demand bill processing — enter a bill number, PorkChop fetches and analyzes it |
| `/search` | Full-text search across bills |

**REST API** (`/api/v1/`): 15 JSON endpoints including `/process` (on-demand bill processing) and `/chat` (AI Q&A about bills).

**MCP server** (`web/mcp/`): 12 tools for LLM access via stdio transport. Tested and working.

## Database Schema

10 tables with indexes and WAL mode:

| Table | What | Key Fields |
|-------|------|-----------|
| `bills` | Bill metadata | congress, bill_type, bill_number, title, status |
| `bill_versions` | Version text storage | version_code, raw_text, cleaned_text |
| `sections` | Chunked bill sections | text, division, title, position |
| `spending_items` | Every dollar amount | amount, amount_numeric, purpose, recipient |
| `legal_references` | US Code, Public Laws, Acts | ref_type, ref_text |
| `deadlines` | Dates with required actions | date, action, responsible_entity |
| `entities` | Departments, agencies, offices | name, entity_type, role |
| `summaries` | Claude-generated summaries | summary_text, model_used |
| `pork_scores` | Spending item scores | score (0-100), flags, reasons |
| `comparisons` | Version diff results | additions_count, removals_count, changes_json |

## Data Sources

| Source | Used For | Auth |
|--------|----------|------|
| **Congress.gov API v3** | Bill metadata, text version URLs, sponsors, actions | api.data.gov key (free) |
| **GovInfo API** | Bill text (HTML/XML), package metadata | api.data.gov key (free) |
| **Local files** | Direct text file import | None |

Bill ID parser accepts flexible formats: `HR-10515`, `118-hr-10515`, `hr10515`, `HR 10515`, `118/hr/10515`.

## Bill Processed

7 bills processed. Flagship example:

**H.R. 10515** — Further Continuing Appropriations and Disaster Relief Supplemental Appropriations Act, 2025

| Metric | Value |
|--------|-------|
| Raw lines | 37,261 |
| Cleaned lines | 29,525 (21% reduction) |
| Sections | 207 |
| Funding items | 203 (50% with extracted purpose, 4 recipients) |
| Total spending | $192B |
| Legal references | 891 |
| Deadlines | 46 (87% with meaningful actions) |
| Entities | 117 |

**All bills combined:** 3,220 spending items, 1,521 with purposes (40%), 49 recipients, 317 deadlines

Structure: Division A (Continuing Appropriations), Division B (Disaster Relief — Helene/WNC), Division C (Veterans, Foreign Affairs, Cybersecurity), Division D (Commerce, Blockchain, 6G), plus additional divisions for healthcare, energy, education, defense.

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Regex + Claude coexist** | Regex is free and reliable for structured data. Claude adds semantic understanding. Neither replaces the other. |
| **SQLite** | Portable, no server, proven at this scale (bluePages uses same pattern for 1,166 businesses). |
| **Click CLI** | Consistent with bluePages, subcommand-friendly, better than argparse for complex tools. |
| **Next.js 16** | Full-stack React with API routes, replaces Flask. Same stack as other projects. |
| **BYOK (Bring Your Own Key)** | Users provide their own LLM API keys (Anthropic/OpenAI/xAI). Stored in browser localStorage only, never server-side. |
| **Haiku for bulk, Sonnet for synthesis** | Cost optimization. Per-section extraction is high-volume/low-complexity (Haiku). Bill summary is low-volume/high-complexity (Sonnet). |
| **Structure-based chunking default** | Preserves legislative intent. A chunk = a logical legislative unit. Size-based available as option for when structure markers are absent. |
