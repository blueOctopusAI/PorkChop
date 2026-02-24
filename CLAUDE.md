# CLAUDE.md — PorkChop

## What This Is

Legislative bill processor — ingests raw congressional bill text, cleans formatting artifacts, chunks by structure or size, extracts structured facts (funding, deadlines, US Code references, duties, entities), and reconstructs into queryable JSON.

**Name origin:** "PorkChop" — chopping up pork barrel spending bills into digestible pieces.

**Tagline:** "AI that reads the bills so you don't have to."

## Origin Story

Built Dec 2024 for a real use case: Tim's brother is chief of staff for Congressman Thomas Massie. Staff get 1,500-page bills dropped on their desk the night before a vote with no time to read them. PorkChop was built to solve that problem.

## Current State

- **Phase:** v0 prototype (Dec 2024, pre-Claude Code era)
- **Bill processed:** "Further Continuing Appropriations and Disaster Relief Supplemental Appropriations Act, 2025" (H.R. 10515) — includes Tropical Storm Helene disaster relief (relevant to WNC)
- **Scale:** 37,261 raw lines → 29,525 cleaned lines → chunked → structured JSON
- **Extraction:** Regex-only (no LLM). Catches US Code refs, Public Laws, dollar amounts, dates, deadlines, duties, entities.
- **Stack:** Pure Python 3.6+, zero dependencies (stdlib only)
- **Tests:** One validation script (`chunk_test.py`) — checks JSON structure and data presence

## Architecture

```
raw_input.txt (congressional formatting, VerDate headers, XML refs, page numbers)
    │
    ▼
cleanText.py — 3-phase regex cleaning
    │  Phase 1: Remove extraneous lines (VerDate, Jkt, XML refs, timestamps, page nums)
    │  Phase 2: Strip line numbers, fix embedded-number-in-word OCR artifacts
    │  Phase 3: Normalize whitespace
    │
    ▼
cleaned_output.txt (reader-friendly bill text, 29K lines)
    │
    ▼
chunk_legislation.py — Split into processable pieces
    │  Strategy 1: Size-based (20K char chunks)
    │  Strategy 2: Structure-based (split on DIVISION/TITLE markers)
    │
    ▼
chunks/ (numbered .txt files)
    │
    ▼
extract_legislative_facts.py — Regex extraction per chunk
    │  US Code references, Public Laws, funding ($), dates, deadlines,
    │  duties (who shall/may/must do what), programs/entities
    │
    ▼
json_chunks/ (structured JSON per chunk)
    │
    ▼
legislative_processor.py — Orchestrator + reconstructor
    │  Interactive menu CLI, combines chunks, outputs final JSON + text
    │
    ▼
output/ (combined_document.json + reconstructed_document.txt)
```

## File Map

```
PorkChop/
├── README.md                          # Project overview
├── CLAUDE.md                          # This file
├── porkchop_by_blueOctopusAI.txt      # Cleaned bill output (1.5MB, 29K lines)
├── porkchop_logo.jpg                  # Logo (generated via Grok)
└── code/
    ├── README.md                      # Code-level docs
    ├── config.json                    # Pipeline configuration
    ├── raw_input.txt                  # Original bill text (2MB, 37K lines)
    ├── cleaned_output.txt             # After cleanText.py (1.5MB, 29K lines)
    ├── cleanText.py                   # Phase 1: Text cleaning (3 regex phases)
    ├── chunk_legislation.py           # Phase 2: Chunking (size or structure)
    ├── extract_legislative_facts.py   # Phase 3: Fact extraction (regex)
    ├── combine_chunks.py              # Simple JSON array combiner
    ├── chunk_test.py                  # Validation: checks JSON chunks for data
    ├── legislative_processor.py       # Orchestrator: interactive menu CLI
    ├── bill.txt                       # Alternate bill text (2MB)
    ├── chunks/                        # Generated: text chunks
    ├── json_chunks/                   # Generated: JSON per chunk
    └── output/                        # Generated: final combined output
```

## Running the Pipeline

```bash
cd code/
python legislative_processor.py
# Interactive menu — select option 1 to run all steps
```

Or run steps individually:
```bash
python cleanText.py              # Clean raw text
python chunk_legislation.py      # Chunk cleaned text
python extract_legislative_facts.py  # Extract facts from chunks
python combine_chunks.py         # Combine JSON chunks
python chunk_test.py             # Validate JSON output
```

## Known Limitations

1. **Regex extraction misses semantic meaning** — catches "The Secretary shall" but doesn't understand *why* or the broader context
2. **No bill source automation** — requires manual text paste into raw_input.txt
3. **Interactive CLI** — uses `input()` prompts, can't be scripted/automated
4. **No web frontend** — output is JSON files on disk
5. **Single bill only** — no comparison between bill versions or across bills
6. **JSON noted as "broken"** in original README — extraction quality varies by section
7. **Embedded number cleanup is aggressive** — the regex `([A-Za-z])(\d+)\s+([A-Za-z])` could mangle legitimate text like section references

## Sensitive Data

- Bill text is public record (government documents, no copyright)
- No PII, API keys, or credentials in this repo
- Logo generated by Grok (xAI) — watermark visible

## Related Projects

- **intelligence-hub** — Same architecture pattern (messy input → chunk → extract → structure)
- **bluePages** — Same pattern (crawl → parse → score → report)
- **BanksAerospace** — Government contract data, same domain (federal spending)
