# CLAUDE.md — PorkChop

## What This Is

Legislative bill processor — fetches bills from Congress.gov, cleans GPO formatting, chunks by structure, extracts facts (regex + Claude), stores in SQLite, serves via Flask web UI. Scores spending items for pork.

**Name origin:** "PorkChop" — chopping up pork barrel spending bills into digestible pieces.

**Tagline:** "AI that reads the bills so you don't have to."

## Origin Story

Built Dec 2024 for a real use case: Tim's brother is chief of staff for Congressman Thomas Massie. Staff get 1,500-page bills dropped on their desk the night before a vote with no time to read them. PorkChop was built to solve that problem.

Originally a regex-only prototype (Dec 2024, pre-Claude Code). Modernized Feb 2026 into a full product: proper package structure, Click CLI, SQLite storage, Congress.gov/GovInfo API ingestion, Claude-powered semantic extraction, Flask web frontend, version comparison, and pork scoring.

## Current State

- **Version:** 1.0.0
- **Tests:** 102 passing (cleaner, chunker, extractor, database, ingestion, comparator, scorer, web)
- **Bill processed:** H.R. 10515 — 37,261 raw lines → 207 sections, 311 funding items ($192B), 1,554 legal refs, 94 deadlines, 51 entities
- **Stack:** Python 3.10+, Click, Flask, SQLite, Claude API (Haiku + Sonnet), httpx, Rich
- **Dependencies:** click, flask, anthropic, httpx, rich (dev: pytest, pytest-cov)

## Architecture

```
User → CLI (Click) or Web (Flask)
              │
    ┌─────────┼─────────────────────────────┐
    │         │                              │
    ▼         ▼                              ▼
Ingestion   Processing                    Web Frontend
(API fetch)  (clean → chunk → extract)    (Flask + Jinja2)
    │         │                              │
    │    ┌────┼────────┐                     │
    │    │    │        │                     │
    │    ▼    ▼        ▼                     │
    │  Regex  Claude   Comparator            │
    │  extract analyze  (version diff)       │
    │    │    │        │                     │
    └────┴────┴────────┴─────────────────────┘
                   │
                   ▼
              SQLite DB
         (bills, sections, spending,
          refs, deadlines, entities,
          summaries, pork_scores,
          comparisons)
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
│   ├── extractor.py              # Regex fact extraction
│   ├── database.py               # SQLite — 10 tables, CRUD, stats
│   ├── ingestion.py              # Congress.gov + GovInfo API clients
│   ├── analyzer.py               # Claude-powered semantic analysis
│   ├── comparator.py             # Bill version diff + semantic comparison
│   ├── scorer.py                 # Pork scoring (heuristic + AI)
│   └── web/
│       ├── __init__.py
│       ├── app.py                # Flask — 5 pages + 5 API endpoints
│       ├── templates/            # 6 Jinja2 templates
│       │   ├── base.html
│       │   ├── index.html
│       │   ├── bill.html
│       │   ├── spending.html
│       │   ├── compare.html
│       │   └── search.html
│       └── static/
│           └── style.css         # Dark theme with pork-score colors
├── tests/                        # 102 tests
│   ├── conftest.py               # Fixtures (sample text, temp DB)
│   ├── test_cleaner.py           # 16 tests
│   ├── test_chunker.py           # 11 tests
│   ├── test_extractor.py         # 15 tests
│   ├── test_database.py          # 18 tests
│   ├── test_ingestion.py         # 9 tests
│   ├── test_comparator.py        # 8 tests
│   ├── test_scorer.py            # 9 tests
│   └── test_web.py               # 16 tests
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

# Web server
PYTHONPATH=src python -m porkchop.cli web

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
- **bluePages** — Same pattern (crawl → parse → score → report), same stack (Python/Flask/SQLite/Click)
- **BanksAerospace** — Government contract data, same domain (federal spending)
