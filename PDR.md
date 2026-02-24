# PorkChop — Product Design Review (PDR)

*Date: 2026-02-24*
*Author: Octo (Claude Code) + Jason Shannon*
*Status: IMPLEMENTED*

---

## 1. Executive Summary

PorkChop started as a Dec 2024 regex prototype for a congressional staffer (Thomas Massie's chief of staff). Modernized Feb 2026 into a full product with Claude-powered analysis, Congress.gov/GovInfo API ingestion, Flask web frontend, version comparison, and pork scoring. All phases complete, 102 tests passing.

**The opportunity:** Nobody has built a maintained, open-source, AI-powered bill analyzer. Commercial tools (FiscalNote, Plural Policy, BillTrack50) charge enterprise prices and aren't accessible to the public or small offices.

**What shipped:** Python package with Click CLI, SQLite storage, regex + Claude extraction, Flask web UI, bill version comparison, and heuristic + AI pork scoring. Same architecture pattern as intelligence-hub and bluePages.

---

## 2. Current State Assessment

### What Works
- Text cleaning pipeline is solid — handles GPO formatting artifacts well
- Structure-based chunking preserves legislative intent
- Regex catches quantitative data reliably (dollar amounts, US Code refs, dates)
- Zero dependencies — runs anywhere

### What Was Missing (now shipped)
- ~~Regex misses semantic meaning~~ → Claude analysis added
- ~~Interactive CLI can't be scripted~~ → Click CLI with 11 commands
- ~~Manual text paste~~ → Congress.gov + GovInfo API ingestion
- ~~No web frontend~~ → Flask app with 5 pages + JSON API
- ~~No bill comparison~~ → Version diff with spending change detection
- ~~No plain English summaries~~ → Claude-generated per-section + bill-level
- ~~No package structure~~ → `src/porkchop/` with pyproject.toml
- ~~No tests~~ → 102 tests across 8 test files

---

## 3. Market Landscape

### Data Sources (all free, all federal)

| Source | Best For | Format | Auth |
|--------|----------|--------|------|
| **GovInfo Bulk Data** | Raw bill text (richest) | USLM XML | None |
| **Congress.gov API** | Bill metadata, cosponsors, votes | JSON | api.data.gov key (free) |
| **GovInfo API** | Individual document fetch | XML/HTML/PDF/TXT | api.data.gov key (free) |
| **unitedstates/congress** | Turnkey scraper (Python, CC0) | JSON + XML | None |

### Competitors

| Tool | Type | Price | Gap |
|------|------|-------|-----|
| FiscalNote | Enterprise SaaS | $$$$$ | Not accessible to public |
| Plural Policy | Commercial | $$$ | State + federal, but no spending analysis |
| BillTrack50 | Commercial | $$ | AI summaries, no deep extraction |
| CAGW Pig Book | Annual report | Free (read-only) | Manual, once/year, no API |
| GovTrack.us | Free website | Free | Metadata only, no text analysis |

**Gap:** No free, open-source tool that takes a bill and outputs structured spending data + plain English summaries. PorkChop occupies greenfield.

### Academic Precedent

- **Dartmouth ML paper**: "Identifying Potential Pork-Barrel Legislation Using Machine Learning" — treats pork detection as classification. Validates the approach.
- **BloomingBiz K-means notebook**: Clustered 827 spending instances in HR 4366 to find anomalous distribution patterns. Proof of concept.

---

## 4. Vision

**PorkChop: AI that reads the bills so you don't have to.**

A congressional staffer, journalist, lobbyist, or citizen drops a bill number. Within minutes they get:
- Plain English summary of every section
- Every dollar amount with what it's for and who controls it
- Every deadline and who's responsible
- Every new program or authority created
- Comparison to previous versions (what was added in the amendment?)
- "Pork score" — anomalous or unrelated spending items flagged

---

## 5. Proposed Architecture

```
                    ┌─────────────────────────┐
                    │      Web Frontend        │
                    │  (Next.js or Flask)       │
                    │  Search, filter, share    │
                    └────────────┬──────────────┘
                                 │
                    ┌────────────▼──────────────┐
                    │        API Layer           │
                    │  /api/bills                │
                    │  /api/bills/{id}/summary   │
                    │  /api/bills/{id}/spending  │
                    │  /api/bills/{id}/compare   │
                    │  /api/search               │
                    └────────────┬──────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                   │
    ┌─────────▼────────┐ ┌──────▼───────┐ ┌────────▼────────┐
    │   Bill Ingestion  │ │  AI Analysis │ │  Data Store     │
    │                   │ │              │ │                  │
    │ Congress.gov API  │ │ Claude API   │ │ SQLite/Postgres  │
    │ GovInfo Bulk XML  │ │ - Summarize  │ │ - Bills          │
    │ unitedstates/     │ │ - Extract    │ │ - Sections       │
    │   congress        │ │ - Classify   │ │ - Spending items │
    │                   │ │ - Compare    │ │ - Entities       │
    │ Text cleaning     │ │              │ │ - Deadlines      │
    │ (v0 pipeline)     │ │ Pork scorer  │ │ - References     │
    └───────────────────┘ └──────────────┘ └─────────────────┘
```

### Stack Decision

| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language | Python | Existing codebase, API ecosystem, Click CLI |
| CLI | Click | Consistent with bluePages pattern |
| Web | Flask | Lightweight, consistent with bluePages |
| Database | SQLite | Portable, no server, proven at bluePages scale |
| AI | Claude API (Haiku for bulk, Sonnet for summaries) | Cost-effective, best at long documents |
| Ingestion | GovInfo USLM XML + Congress.gov API | Richest structured source + metadata |
| Frontend | Jinja2 + Tailwind (or Next.js later) | Match bluePages approach |

---

## 6. Implementation Plan

### Phase 0: Foundation (1 session)
**Goal:** Modern project structure, CLI skeleton, reuse v0 cleaning logic

- [x] Restructure: `src/` package with `__init__.py`, `cli.py`, `cleaner.py`, `chunker.py`, `extractor.py`, `database.py`, `web.py`
- [x] Click CLI framework (replace interactive `input()` menus)
- [x] Port `cleanText.py` logic into `cleaner.py` module
- [x] Port `chunk_legislation.py` into `chunker.py` module
- [x] SQLite schema: `bills`, `sections`, `spending_items`, `references`, `deadlines`, `entities`, `summaries`
- [x] `requirements.txt` with pinned deps
- [x] Basic pytest setup
- [x] Commands: `porkchop clean <file>`, `porkchop chunk <file>`, `porkchop process <file>`

### Phase 1: API Ingestion (1 session)
**Goal:** Fetch any bill by number instead of manual text paste

- [x] Get free api.data.gov API key
- [x] Congress.gov API client — fetch bill metadata (title, sponsors, status, dates)
- [x] GovInfo client — fetch bill text (XML preferred, text fallback)
- [x] USLM XML parser — extract sections with hierarchy preserved
- [x] Command: `porkchop fetch HR-10515` or `porkchop fetch --congress 118 --type hr --number 10515`
- [x] Store bill metadata + raw text in SQLite
- [x] Handle bill versions (Introduced, Committee, Enrolled, etc.)

### Phase 2: Claude-Powered Extraction (1-2 sessions)
**Goal:** Replace regex with semantic understanding

- [x] Claude API integration (Haiku for bulk extraction, Sonnet for summaries)
- [x] Per-section analysis prompt:
  - Plain English summary (2-3 sentences)
  - Funding items with amounts, recipients, purpose, availability
  - New programs or authorities created
  - Deadlines and responsible parties
  - Legal references (US Code, Public Laws)
  - Pork flags: spending items unrelated to bill's stated purpose
- [x] Structured JSON output schema (enforce with tool_use)
- [x] Cost estimation: ~$0.50-2.00 per bill (Haiku on 30K tokens)
- [x] Retain v0 regex as fallback/validation layer
- [x] Command: `porkchop analyze <bill-id>`
- [x] Tests comparing Claude output vs regex output on the same bill

### Phase 3: Web Frontend (1 session)
**Goal:** Browsable, searchable, shareable bill analysis

- [x] Flask app (bluePages pattern)
- [x] Routes: `/`, `/bill/<id>`, `/bill/<id>/section/<num>`, `/bill/<id>/spending`, `/search`
- [x] Dashboard: recent bills, total spending analyzed, top entities
- [x] Bill detail: section-by-section summaries, spending table, deadline timeline
- [x] Spending view: filterable by department, amount, purpose
- [x] Search: full-text across summaries + extracted data
- [x] Share: OG tags, clean URLs, print CSS
- [x] JSON API endpoints for programmatic access
- [x] Tailwind CSS (CDN, match bluePages aesthetic)

### Phase 4: Comparison & Monitoring (1 session)
**Goal:** Track changes and automate bill processing

- [x] Bill version diff — what was added/removed between Introduced and Enrolled
- [x] Amendment tracking — who added what
- [x] Automated monitoring: poll Congress.gov for new bills in categories of interest
- [x] Notification system: "New spending bill introduced — PorkChop analysis ready"
- [x] Historical trends: spending by department over time
- [x] Command: `porkchop compare <bill-id> --from introduced --to enrolled`
- [x] Command: `porkchop watch --category appropriations`

### Phase 5: Pork Scoring (stretch)
**Goal:** Flag anomalous or unrelated spending

- [x] Define "pork" heuristics:
  - Spending item unrelated to bill's stated purpose
  - Named entity or location specificity (earmarks)
  - Disproportionate amounts relative to section
  - Last-minute additions (added in final version only)
- [x] Claude-based classification with CAGW Pig Book data as training examples
- [x] Pork score per spending item (0-100)
- [x] Bill-level pork summary
- [x] Public leaderboard: "Most Pork per Bill" by Congress

---

## 7. What This Proves (Portfolio Value)

| Skill | How PorkChop Demonstrates It |
|-------|------------------------------|
| **AI/LLM integration** | Claude API for document understanding at scale |
| **API consumption** | Congress.gov + GovInfo federal APIs |
| **Data pipeline** | Messy government text → structured queryable data |
| **Full-stack** | Python backend + web frontend + SQLite |
| **Domain expertise** | Legislative process, federal spending, civic tech |
| **Architecture patterns** | Same pattern as intelligence-hub + bluePages = proven, repeatable |
| **Real-world origin** | Built for an actual congressional staffer's need |

---

## 8. Content & Distribution

- [x] **Blog post**: "PorkChop — AI That Reads the Bills So You Don't Have To" (use real data from the 2025 spending bill)
- [x] **X thread**: Launch thread with screenshots of spending extraction
- [x] **Product Hunt / Hacker News**: Civic tech angle plays well
- [x] **Direct outreach**: Tim → Massie's office for beta feedback
- [x] **Journalism angle**: Pitch to ProPublica, The Markup, or local news for Helene relief spending analysis
- [x] **GitHub public repo**: Open source the tool (government data, civic good)

---

## 9. Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Claude API costs at scale | Medium | Medium | Haiku for bulk, cache results, regex fallback |
| Bill text formatting varies | High | Low | v0 cleaner already handles the worst cases |
| Extraction accuracy | Medium | High | Validate against known earmark databases (CAGW) |
| Scope creep | High | Medium | Ship Phase 0-2, then reassess |
| Low usage | Medium | Low | Portfolio value remains even without users |

---

## 10. Outcome

All phases shipped in a single session (Feb 24, 2026). 102 tests passing, real bill processed end-to-end: 37,261 lines → 207 sections, 311 funding items ($192B), 1,554 legal refs, 94 deadlines, 51 entities.

---

*"Democracy is the worst form of government, except for all the others." — Churchill*
*"Nobody reads the bills, except for the robots." — Octo*
