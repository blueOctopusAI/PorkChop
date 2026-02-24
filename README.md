# PorkChop

**AI that reads the bills so you don't have to.**

PorkChop processes congressional bills into structured, queryable data. Drop in a bill number or raw text file — get back spending breakdowns, legal references, deadlines, entity maps, plain English summaries, and pork scores.

Built for a real use case: Tim's brother is chief of staff for Congressman Thomas Massie. Staff get 1,500-page bills dropped on their desk the night before a vote with no time to read them.

## What It Does

- **Cleans** raw GPO text (strips VerDate headers, XML refs, page numbers, OCR artifacts)
- **Chunks** by legislative structure (Division/Title markers) or size
- **Extracts** funding items, legal references, deadlines, duties, entities via regex
- **Fetches** any bill by number from Congress.gov and GovInfo APIs
- **Analyzes** sections using Claude for semantic understanding and plain English summaries
- **Compares** bill versions (what spending was added/removed between drafts?)
- **Scores** spending items 0-100 for pork likelihood (earmarks, geographic specificity, unrelatedness)
- **Serves** a Next.js web frontend with dashboard, spending detail, version comparison, search, REST API, and MCP server for LLM access

## Quick Start

```bash
# Install
python3 -m venv .venv && source .venv/bin/activate
pip install click anthropic httpx rich pytest

# Process a local bill file
PYTHONPATH=src python -m porkchop.cli process <bill-text-file> --bill-id HR-10515

# Fetch a bill from Congress.gov (requires CONGRESS_API_KEY)
PYTHONPATH=src python -m porkchop.cli fetch HR-10515 --text

# Run Claude analysis (requires ANTHROPIC_API_KEY)
PYTHONPATH=src python -m porkchop.cli analyze 1

# Score spending for pork
PYTHONPATH=src python -m porkchop.cli score 1

# Start Next.js web frontend
cd web && npm install && npm run dev
```

## CLI Commands

| Command | What |
|---------|------|
| `porkchop process <file>` | Full pipeline: clean → chunk → extract → store |
| `porkchop clean <file>` | Clean raw GPO bill text |
| `porkchop chunk <file>` | Chunk cleaned text |
| `porkchop fetch <bill-id>` | Fetch from Congress.gov API |
| `porkchop import <file> <bill-id>` | Import local file into database |
| `porkchop analyze <bill-id>` | Claude-powered semantic analysis |
| `porkchop compare <bill-id>` | Compare two bill versions |
| `porkchop score <bill-id>` | Pork scoring (heuristic + optional AI) |
| `porkchop info <bill-id>` | Show stored bill details |
| `porkchop search <query>` | Search analyzed bills |
| `porkchop stats` | Database statistics |


## Real Data

Processed H.R. 10515 — "Further Continuing Appropriations and Disaster Relief Supplemental Appropriations Act, 2025" (includes Tropical Storm Helene disaster relief for WNC):

- 37,261 raw lines → 29,525 cleaned → 207 sections
- 285 funding items ($192B total) with purpose and recipient extraction
- 891 legal references (US Code + Public Laws + Acts)
- 94 deadlines
- 117 entities
- 89 tests passing (27 extractor, 18 database, 16 cleaner, 11 chunker, 9 scorer, 8 comparator)

## Web Frontend

The `web/` directory contains the Next.js frontend:

- **Marketing pages** — Landing, How It Works, About
- **App pages** — Dashboard, bill detail, spending tables, pork analysis, version comparison, search
- **REST API** — 15 endpoints under `/api/v1/` (bills, spending, pork, deadlines, entities, references, sections, versions, summaries, comparison, search, stats, process, chat)
- **MCP server** — 12 tools for LLM access to bill data (`web/mcp/`) — tested and working
- **On-demand processing** — Enter any bill number, PorkChop fetches and processes it
- **AI chat** — Ask questions about any bill using your own API key (Anthropic, OpenAI, xAI)
- **BYOK** — Users bring their own API keys, stored in browser localStorage only

```bash
cd web && npm install && npm run dev
```

## Stack

**Backend:** Python 3.10+ | Click CLI | SQLite | Claude API (Haiku + Sonnet) | Congress.gov API | GovInfo API
**Frontend:** Next.js 16 | TypeScript | Tailwind v4 | better-sqlite3

## Environment Variables

| Variable | Required For | Where |
|----------|-------------|-------|
| `CONGRESS_API_KEY` | `fetch` command | Free at https://api.data.gov/signup/ |
| `ANTHROPIC_API_KEY` | `analyze`, `score --ai` | https://console.anthropic.com/ |

## Tests

```bash
PYTHONPATH=src pytest tests/ -v
```

89 tests across 7 test files: cleaner, chunker, extractor (27), database, ingestion, comparator, scorer.

## License

MIT. Bill text is public record (US government documents, no copyright).
