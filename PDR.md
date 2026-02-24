# PorkChop — Product Design Review (PDR)

*Date: 2026-02-24*
*Author: Octo (Claude Code) + Jason Shannon*
*Status: PROPOSAL*

---

## 1. Executive Summary

PorkChop v0 is a working prototype that processes legislative bill text through regex-based extraction. Built in Dec 2024 for a congressional staffer (Thomas Massie's chief of staff), it solves a real problem: nobody has time to read 1,500-page bills.

**The opportunity:** Nobody has built a maintained, open-source, AI-powered bill analyzer. The Dartmouth ML paper and a few Jupyter notebooks exist as proofs of concept, but there's no product. Commercial tools (FiscalNote, Plural Policy, BillTrack50) charge enterprise prices and aren't accessible to the public or small offices.

**The modernization:** Replace regex with Claude, add Congress.gov/GovInfo APIs for automated ingestion, build a web frontend. Same architecture pattern as intelligence-hub and bluePages — we've built this system three times now.

---

## 2. Current State Assessment

### What Works
- Text cleaning pipeline is solid — handles GPO formatting artifacts well
- Structure-based chunking preserves legislative intent
- Regex catches quantitative data reliably (dollar amounts, US Code refs, dates)
- Zero dependencies — runs anywhere

### What Doesn't
- Regex misses semantic meaning ("why is this money being spent?")
- Interactive CLI can't be automated or scripted
- Manual text paste — no API integration
- No web frontend
- No bill comparison (what changed between versions?)
- No "plain English" summaries
- JSON output quality is inconsistent

### Architecture Debt
- All code in flat `code/` directory — no package structure
- No proper CLI framework (uses `input()` prompts)
- No tests beyond chunk validation
- No error recovery — pipeline fails silently on edge cases
- Config management is minimal

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

**PorkChop v2: AI that reads the bills so you don't have to.**

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

- [ ] Restructure: `src/` package with `__init__.py`, `cli.py`, `cleaner.py`, `chunker.py`, `extractor.py`, `database.py`, `web.py`
- [ ] Click CLI framework (replace interactive `input()` menus)
- [ ] Port `cleanText.py` logic into `cleaner.py` module
- [ ] Port `chunk_legislation.py` into `chunker.py` module
- [ ] SQLite schema: `bills`, `sections`, `spending_items`, `references`, `deadlines`, `entities`, `summaries`
- [ ] `requirements.txt` with pinned deps
- [ ] Basic pytest setup
- [ ] Commands: `porkchop clean <file>`, `porkchop chunk <file>`, `porkchop process <file>`

### Phase 1: API Ingestion (1 session)
**Goal:** Fetch any bill by number instead of manual text paste

- [ ] Get free api.data.gov API key
- [ ] Congress.gov API client — fetch bill metadata (title, sponsors, status, dates)
- [ ] GovInfo client — fetch bill text (XML preferred, text fallback)
- [ ] USLM XML parser — extract sections with hierarchy preserved
- [ ] Command: `porkchop fetch HR-10515` or `porkchop fetch --congress 118 --type hr --number 10515`
- [ ] Store bill metadata + raw text in SQLite
- [ ] Handle bill versions (Introduced, Committee, Enrolled, etc.)

### Phase 2: Claude-Powered Extraction (1-2 sessions)
**Goal:** Replace regex with semantic understanding

- [ ] Claude API integration (Haiku for bulk extraction, Sonnet for summaries)
- [ ] Per-section analysis prompt:
  - Plain English summary (2-3 sentences)
  - Funding items with amounts, recipients, purpose, availability
  - New programs or authorities created
  - Deadlines and responsible parties
  - Legal references (US Code, Public Laws)
  - Pork flags: spending items unrelated to bill's stated purpose
- [ ] Structured JSON output schema (enforce with tool_use)
- [ ] Cost estimation: ~$0.50-2.00 per bill (Haiku on 30K tokens)
- [ ] Retain v0 regex as fallback/validation layer
- [ ] Command: `porkchop analyze <bill-id>`
- [ ] Tests comparing Claude output vs regex output on the same bill

### Phase 3: Web Frontend (1 session)
**Goal:** Browsable, searchable, shareable bill analysis

- [ ] Flask app (bluePages pattern)
- [ ] Routes: `/`, `/bill/<id>`, `/bill/<id>/section/<num>`, `/bill/<id>/spending`, `/search`
- [ ] Dashboard: recent bills, total spending analyzed, top entities
- [ ] Bill detail: section-by-section summaries, spending table, deadline timeline
- [ ] Spending view: filterable by department, amount, purpose
- [ ] Search: full-text across summaries + extracted data
- [ ] Share: OG tags, clean URLs, print CSS
- [ ] JSON API endpoints for programmatic access
- [ ] Tailwind CSS (CDN, match bluePages aesthetic)

### Phase 4: Comparison & Monitoring (1 session)
**Goal:** Track changes and automate bill processing

- [ ] Bill version diff — what was added/removed between Introduced and Enrolled
- [ ] Amendment tracking — who added what
- [ ] Automated monitoring: poll Congress.gov for new bills in categories of interest
- [ ] Notification system: "New spending bill introduced — PorkChop analysis ready"
- [ ] Historical trends: spending by department over time
- [ ] Command: `porkchop compare <bill-id> --from introduced --to enrolled`
- [ ] Command: `porkchop watch --category appropriations`

### Phase 5: Pork Scoring (stretch)
**Goal:** Flag anomalous or unrelated spending

- [ ] Define "pork" heuristics:
  - Spending item unrelated to bill's stated purpose
  - Named entity or location specificity (earmarks)
  - Disproportionate amounts relative to section
  - Last-minute additions (added in final version only)
- [ ] Claude-based classification with CAGW Pig Book data as training examples
- [ ] Pork score per spending item (0-100)
- [ ] Bill-level pork summary
- [ ] Public leaderboard: "Most Pork per Bill" by Congress

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

- [ ] **Blog post**: "PorkChop — AI That Reads the Bills So You Don't Have To" (use real data from the 2025 spending bill)
- [ ] **X thread**: Launch thread with screenshots of spending extraction
- [ ] **Product Hunt / Hacker News**: Civic tech angle plays well
- [ ] **Direct outreach**: Tim → Massie's office for beta feedback
- [ ] **Journalism angle**: Pitch to ProPublica, The Markup, or local news for Helene relief spending analysis
- [ ] **GitHub public repo**: Open source the tool (government data, civic good)

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

## 10. Decision Required

**Recommended path:** Phase 0 → 1 → 2 → 3 (4 sessions to a working product)

**Minimum viable demo:** Phase 0 + 2 (CLI that takes a bill file and outputs Claude-analyzed JSON). Two sessions.

**Question for Jason:** Do we promote this to INCUBATING or ACTIVE? The modernization is 4 sessions of work. The civic tech + BanksAerospace synergy + blog content + portfolio value make it high ROI. But the job search is the priority.

---

*"Democracy is the worst form of government, except for all the others." — Churchill*
*"Nobody reads the bills, except for the robots." — Octo*
