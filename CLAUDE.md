# CLAUDE.md — PorkChop

## What This Is

Legislative bill processor — fetches bills from Congress.gov, cleans GPO formatting, chunks by structure, extracts facts (regex + Claude), stores in SQLite. Next.js web frontend with REST API and MCP server. Scores spending items for pork.

**Name origin:** "PorkChop" — chopping up pork barrel spending bills into digestible pieces.

**Tagline:** "AI that reads the bills so you don't have to."

## Origin Story

Built Dec 2024 for a real use case: Tim's brother is chief of staff for Congressman Thomas Massie. Staff get 1,500-page bills dropped on their desk the night before a vote with no time to read them. PorkChop was built to solve that problem.

Originally a regex-only prototype (Dec 2024, pre-Claude Code). Modernized Feb 2026 into a full product: proper package structure, Click CLI, SQLite storage, Congress.gov/GovInfo API ingestion, Claude-powered semantic extraction, Next.js web frontend with REST API and MCP server, version comparison, and pork scoring.

## Current State

- **Version:** 1.0.0
- **Tests:** 104 passing (cleaner, chunker, extractor, database, ingestion, comparator, scorer)
- **Bills processed:** 7 bills including H.R. 10515, 3684, 5376, 815, 3935, 2670, 4366 — 1,521 spending items with purposes (40%), 49 recipients, 317 deadlines
- **Backend stack:** Python 3.10+, Click, SQLite, Claude API (Haiku + Sonnet), httpx, Rich
- **Frontend stack:** Next.js 16, TypeScript, Tailwind v4, better-sqlite3, MCP SDK
- **Dependencies:** click, anthropic, httpx, rich (dev: pytest, pytest-cov)
- **MCP server:** Tested and working — 12 tools, stdio transport, Claude Desktop ready

## Architecture

```
Python CLI (writes)          Next.js Web (reads)        MCP Server (reads)
  │                              │                          │
  ▼                              ▼                          ▼
Ingestion → Processing      App Pages + REST API      12 LLM tools
(fetch)     (clean/chunk/   (dashboard, bills,        (stdio transport)
             extract/        spending, pork,
             analyze/        compare, search)
             compare/
             score)
  │                              │                          │
  └──────────────────────────────┼──────────────────────────┘
                                 │
                            SQLite DB
```

## File Map

```
PorkChop/
├── README.md                     # Project overview + quick start
├── CLAUDE.md                     # This file — Claude Code context
├── HOW-IT-WORKS.md               # Technical deep dive
├── PDR.md                        # Product Design Review (proposal → implemented)
├── pyproject.toml                # Python packaging, entry point: porkchop
├── porkchop_logo.jpg             # Logo (generated via Grok)
├── src/porkchop/                 # Source package
│   ├── __init__.py               # Version (1.0.0)
│   ├── cli.py                    # Click CLI — 11 commands
│   ├── cleaner.py                # Text cleaning (3-phase regex)
│   ├── chunker.py                # Chunking (size + structure strategies)
│   ├── extractor.py              # Regex fact extraction (DOTALL cross-newline, 5 purpose strategies, subheading fallback, recipient detection)
│   ├── database.py               # SQLite — 10 tables, CRUD, stats
│   ├── ingestion.py              # Congress.gov + GovInfo API clients
│   ├── analyzer.py               # Claude-powered semantic analysis
│   ├── comparator.py             # Bill version diff + semantic comparison
│   ├── scorer.py                 # Pork scoring (heuristic + AI)
│   └── api.py                    # FastAPI standalone API (process, health, bills)
├── tests/                        # 104 tests
│   ├── conftest.py               # Fixtures (sample text, temp DB)
│   ├── test_cleaner.py           # 16 tests
│   ├── test_chunker.py           # 11 tests
│   ├── test_extractor.py         # 33 tests (purpose, recipient, fiscal year, deadlines, subheadings)
│   ├── test_database.py          # 18 tests
│   ├── test_ingestion.py         # 9 tests (requires httpx)
│   ├── test_comparator.py        # 8 tests
│   └── test_scorer.py            # 9 tests
├── web/                          # Next.js frontend
│   ├── src/
│   │   ├── app/                  # App Router pages + API routes
│   │   │   ├── (marketing)/      # Landing, How It Works, About
│   │   │   ├── (app)/            # Dashboard, bills, spending, pork, compare, search, process
│   │   │   └── api/v1/           # 15 REST API endpoints (incl. chat + process)
│   │   ├── components/           # SettingsModal, BillChat, layout/
│   │   └── lib/                  # db.ts, types.ts, format.ts, pork-colors.ts, llm.ts, settings.ts
│   └── mcp/                      # MCP server (12 tools, stdio transport)
│       └── src/index.ts
└── data/                         # Runtime (gitignored)
    └── porkchop.db               # SQLite database
```

## Running

```bash
# Full pipeline on a local file
PYTHONPATH=src python -m porkchop.cli process <bill-text-file> --bill-id HR-10515

# Fetch from Congress.gov (needs CONGRESS_API_KEY)
PYTHONPATH=src python -m porkchop.cli fetch HR-10515 --text

# Claude analysis (needs ANTHROPIC_API_KEY)
PYTHONPATH=src python -m porkchop.cli analyze 1

# Pork scoring
PYTHONPATH=src python -m porkchop.cli score 1

# Next.js web frontend
cd web && npm install && npm run dev

# Tests
PYTHONPATH=src pytest tests/ -v
```

## Key Design Decisions

- **Regex retained alongside Claude** — regex is free, fast, and reliable for structured data (dollar amounts, US Code refs). Claude adds semantic understanding. Both coexist.
- **SQLite over Postgres** — portable, no server, proven at this scale. Same pattern as bluePages.
- **Click over argparse** — consistent with bluePages, better UX, subcommand-friendly.
- **Haiku for bulk, Sonnet for summaries** — cost optimization. ~$0.50-2.00 per bill with Haiku; Sonnet only for the bill-level synthesis.
- **Structure-based chunking default** — preserves legislative intent. A chunk = a logical legislative unit. Size-based available when structure markers are absent.

## Sensitive Data

- Bill text is public record (government documents, no copyright)
- No PII, API keys, or credentials in this repo
- API keys loaded from environment variables only
- `data/` directory is gitignored (runtime database)

## Related Projects

- **intelligence-hub** — Same architecture pattern (messy input → chunk → extract → structure)
- **bluePages** — Same pattern (crawl → parse → score → report), same stack (Python/SQLite/Click)
- **BanksAerospace** — Government contract data, same domain (federal spending)
