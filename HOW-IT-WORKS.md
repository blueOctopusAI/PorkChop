# HOW-IT-WORKS.md — PorkChop

## Overview

PorkChop is a legislative bill text processor that turns raw congressional documents into structured, queryable data. The pipeline takes a 1,500+ page bill (37K lines of formatting-heavy government text) and outputs structured JSON with funding amounts, legal references, deadlines, duties, and entity mentions.

## The Problem

Congressional staff receive massive omnibus bills hours before votes. The "Further Continuing Appropriations and Disaster Relief Supplemental Appropriations Act, 2025" is 1,574,896 bytes of text with embedded formatting artifacts from the Government Publishing Office's XML-to-text pipeline. No human can read this in a night.

## Pipeline Stages

### Stage 1: Text Cleaning (`cleanText.py`)

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
2. **Inline cleanup** — Strip leading line numbers, fix embedded-number OCR artifacts (e.g., "strate2 gies" → "strategies")
3. **Normalization** — Collapse whitespace, remove excessive blank lines

Result: 37,261 raw lines → 29,525 clean lines (21% reduction)

### Stage 2: Chunking (`chunk_legislation.py`)

Two strategies available:

**Size-based** (default): Split at 20,000 character boundaries. Simple, predictable chunk sizes. Good for LLM context windows.

**Structure-based**: Split on DIVISION and TITLE markers using regex:
```python
division_pattern = re.compile(r'^DIVISION\s+([A-Z]+)\b', re.IGNORECASE)
title_pattern = re.compile(r'^TITLE\s+([IVXLC]+)\b', re.IGNORECASE)
```

This preserves legislative structure — each chunk represents a logical unit of the bill.

### Stage 3: Fact Extraction (`extract_legislative_facts.py`)

Per-chunk regex extraction produces structured JSON:

```json
{
  "chunk_id": "001_division_a",
  "original_text": "...",
  "references": {
    "us_code": ["42 U.S.C. 3030a"],
    "public_laws": ["Public Law 118–42"],
    "other_legislative_refs": ["Robert T. Stafford Disaster Relief and Emergency Assistance Act"]
  },
  "funding": [{
    "amount": "$100,000,000",
    "purpose": "disaster relief",
    "availability": "until September 30, 2025"
  }],
  "deadlines": [{"action": "unknown", "date": "January 15, 2025"}],
  "duties_and_requirements": [{
    "entity": "The Secretary of Homeland Security",
    "action": "submit a report to Congress..."
  }],
  "programs_and_entities": ["Department of Homeland Security", "Office of Management and Budget"],
  "dates": ["January 15, 2025", "September 30, 2025"]
}
```

### Stage 4: Reconstruction (`legislative_processor.py`)

Combines all JSON chunks into a single document with:
- Aggregated references (deduplicated)
- All funding items
- All deadlines
- All duties and entity mentions
- Optional: full text inclusion

### Stage 5: Validation (`chunk_test.py`)

Checks each JSON chunk for:
- Required structural keys present
- At least one reference found (US Code, Public Law, or other)
- Configurable requirements per data category

## Data Flow

```
raw_input.txt (2.0MB, 37K lines)
    ↓ cleanText.py
cleaned_output.txt (1.5MB, 29K lines)
    ↓ chunk_legislation.py
chunks/*.txt (N files, 20K chars each)
    ↓ extract_legislative_facts.py
json_chunks/*.json (structured data per chunk)
    ↓ legislative_processor.py
output/combined_document.json (aggregated facts)
output/reconstructed_document.txt (clean full text)
```

## Bill Processed

**H.R. 10515** — Further Continuing Appropriations and Disaster Relief Supplemental Appropriations Act, 2025

Structure:
- **Division A** — Further Continuing Appropriations Act, 2025
- **Division B** — Disaster Relief Supplemental Appropriations (includes Tropical Storm Helene relief for WNC)
- **Division C** — Other Matters (Veterans, Foreign Affairs, Cybersecurity, etc.)
- **Division D** — Commerce Matters (Second Chance Act, Consumer Safety, Supply Chains, Blockchain, 6G)
- Additional divisions covering healthcare, energy, education, defense

## Known Issues

1. Regex extraction quality varies — structured references (US Code, dollar amounts) are reliable; semantic meaning (purpose, context) is weak
2. The embedded-number cleanup heuristic (`([A-Za-z])(\d+)\s+([A-Za-z])` → `\1\3`) can mangle legitimate references
3. Interactive CLI (`input()` prompts) prevents automation
4. No incremental processing — must re-run entire pipeline for each bill
5. JSON output noted as "broken" in original README — likely edge cases in extraction patterns

## Design Decisions

- **Pure stdlib** — Zero external dependencies. Intentional: runs anywhere Python exists.
- **Regex over NLP** — Dec 2024 choice. LLM APIs existed but cost/complexity tradeoff favored regex for a prototype.
- **Text input over API** — Manual paste because the goal was speed-to-demo, not scalability.
- **Structure-based chunking** — Preserves legislative intent better than arbitrary size splits.
