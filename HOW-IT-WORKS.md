# HOW-IT-WORKS.md — PorkChop

## Overview

PorkChop is a legislative bill text processor that turns raw congressional documents into structured, queryable data. The pipeline takes a 1,500+ page bill and outputs spending breakdowns, legal references, deadlines, entity maps, plain English summaries, and pork scores — stored in SQLite and browsable via a web UI.

## The Problem

Congressional staff receive massive omnibus bills hours before votes. The "Further Continuing Appropriations and Disaster Relief Supplemental Appropriations Act, 2025" is 1,574,896 bytes of text with embedded formatting artifacts from the Government Publishing Office's XML-to-text pipeline. No human can read this in a night.

## System Architecture

```
                         ┌──────────────┐
                         │   User       │
                         │  CLI or Web  │
                         └──────┬───────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                  │
    ┌─────────▼────────┐ ┌─────▼──────┐ ┌────────▼────────┐
    │   Ingestion       │ │ Processing │ │  Web Frontend    │
    │                   │ │            │ │                  │
    │ Congress.gov API  │ │ clean      │ │ Flask + Jinja2   │
    │ GovInfo API       │ │ chunk      │ │ 5 pages          │
    │ Local file import │ │ extract    │ │ 5 API endpoints  │
    │                   │ │ analyze    │ │ Dark theme       │
    │ Bill ID parser:   │ │ compare    │ │ Pork colors      │
    │ HR-10515          │ │ score      │ │                  │
    │ 118-hr-10515      │ │            │ │                  │
    └─────────┬────────┘ └─────┬──────┘ └────────┬────────┘
              │                │                  │
              └────────────────┼──────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │     SQLite DB       │
                    │                     │
                    │ bills               │
                    │ bill_versions       │
                    │ sections            │
                    │ spending_items      │
                    │ legal_references    │
                    │ deadlines           │
                    │ entities            │
                    │ summaries           │
                    │ pork_scores         │
                    │ comparisons         │
                    └─────────────────────┘
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
- **Funding** — Dollar amounts with purpose, availability, fiscal years. Handles scale words (million, billion).
- **Dates** — Full date pattern + fiscal year extraction
- **Deadlines** — "not later than" with backward context search for action
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

### Stage 7: Web Frontend (`web/app.py`)

Flask app with dark theme and pork-score color coding:

| Page | What |
|------|------|
| `/` | Dashboard — recent bills, aggregate stats |
| `/bill/<id>` | Bill detail — summary, spending, deadlines, refs, entities, pork |
| `/bill/<id>/spending` | Full spending table with pork scores |
| `/bill/<id>/compare` | Version comparison picker + diff view |
| `/search` | Full-text search across bills |

JSON API mirrors all pages at `/api/*`.

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

**H.R. 10515** — Further Continuing Appropriations and Disaster Relief Supplemental Appropriations Act, 2025

| Metric | Value |
|--------|-------|
| Raw lines | 37,261 |
| Cleaned lines | 29,525 (21% reduction) |
| Sections | 207 |
| Funding items | 311 |
| Total spending | $192,015,988,007 |
| Legal references | 1,554 |
| Deadlines | 94 |
| Entities | 51 |

Structure: Division A (Continuing Appropriations), Division B (Disaster Relief — Helene/WNC), Division C (Veterans, Foreign Affairs, Cybersecurity), Division D (Commerce, Blockchain, 6G), plus additional divisions for healthcare, energy, education, defense.

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Regex + Claude coexist** | Regex is free and reliable for structured data. Claude adds semantic understanding. Neither replaces the other. |
| **SQLite** | Portable, no server, proven at this scale (bluePages uses same pattern for 1,166 businesses). |
| **Click CLI** | Consistent with bluePages, subcommand-friendly, better than argparse for complex tools. |
| **Flask + Jinja2** | Lightweight, same pattern as bluePages, no JS build step needed. |
| **Haiku for bulk, Sonnet for synthesis** | Cost optimization. Per-section extraction is high-volume/low-complexity (Haiku). Bill summary is low-volume/high-complexity (Sonnet). |
| **Structure-based chunking default** | Preserves legislative intent. A chunk = a logical legislative unit. Size-based available as option for when structure markers are absent. |
