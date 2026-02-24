"""Phase 3: Regex-based fact extraction from bill text.

Ported from v0 extract_legislative_facts.py with improvements:
- Module interface returning structured dicts
- Better funding amount parsing (handles millions/billions notation)
- Improved entity detection
- Deduplication built in
"""

import re
from typing import Any


# --- Reference patterns ---
US_CODE_PATTERN = re.compile(r"\b(\d+)\s*U\.S\.C\.?\s*([\w\(\)\.\-]*)", re.IGNORECASE)
PUBLIC_LAW_PATTERN = re.compile(r"Public Law (\d+)[–\-](\d+)", re.IGNORECASE)
ACT_PATTERN = re.compile(
    r"\b((?:[A-Z][a-zA-Z.]+\s+){1,6}(?:Act|Code))\b"
)

# --- Funding patterns ---
DOLLAR_PATTERN = re.compile(
    r"\$\s*(?P<amount>[\d,]+(?:\.\d+)?)\s*(?P<scale>thousand|million|billion|trillion)?",
    re.IGNORECASE,
)
APPROPRIATION_PATTERN = re.compile(
    r"\$\s*[\d,]+(?:\.\d+)?\s*(?:thousand|million|billion|trillion)?"
    r"(?P<context>[^.;]{0,200})",
    re.IGNORECASE,
)

# --- Date patterns ---
DATE_PATTERN = re.compile(
    r"(January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+\d{1,2},\s*\d{4}",
    re.IGNORECASE,
)
FISCAL_YEAR_PATTERN = re.compile(r"fiscal year (\d{4})", re.IGNORECASE)
NOT_LATER_THAN = re.compile(
    r"not later than\s+(?:(\d+)\s+days?\s+after\s+[^,;.]+|"
    r"((?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+\d{1,2},\s*\d{4}))",
    re.IGNORECASE,
)

# --- Duty/requirement patterns ---
DUTY_PATTERN = re.compile(
    r"(The (?:Secretary|Administrator|Comptroller General|Director|Commissioner|"
    r"Attorney General|Inspector General|Chairman|President)"
    r"(?:\s+of\s+[A-Za-z& ]+)?)\s+(shall|may|must)\s+(.{10,300}?)(?:\.|;|$)",
    re.IGNORECASE,
)

# --- Entity patterns ---
ENTITY_PATTERN = re.compile(
    r"\b(Department of [A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}|"
    r"Office of [A-Z][a-z]+(?:\s+(?:and\s+)?[A-Z][a-z]+){0,3}|"
    r"Bureau of [A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}|"
    r"(?:Federal|National) [A-Z][a-z]+ (?:Agency|Administration|Commission|Authority)|"
    r"(?:Environmental Protection|Small Business|General Services) (?:Agency|Administration)|"
    r"Inspector General)\b",
)

SCALE_MULTIPLIERS = {
    "thousand": 1_000,
    "million": 1_000_000,
    "billion": 1_000_000_000,
    "trillion": 1_000_000_000_000,
}


def parse_dollar_amount(amount_str: str, scale: str | None = None) -> float:
    """Parse a dollar amount string to a float."""
    cleaned = amount_str.replace(",", "").strip()
    try:
        value = float(cleaned)
    except ValueError:
        return 0.0
    if scale:
        value *= SCALE_MULTIPLIERS.get(scale.lower(), 1)
    return value


def extract_facts(text: str) -> dict[str, Any]:
    """Extract structured facts from a chunk of bill text using regex."""
    facts: dict[str, Any] = {
        "references": {"us_code": [], "public_laws": [], "acts": []},
        "funding": [],
        "dates": [],
        "deadlines": [],
        "duties": [],
        "entities": [],
        "fiscal_years": [],
    }

    seen_refs = set()
    seen_entities = set()

    # --- References ---
    for m in US_CODE_PATTERN.finditer(text):
        ref = f"{m.group(1)} U.S.C. {m.group(2)}".strip()
        if ref not in seen_refs:
            seen_refs.add(ref)
            facts["references"]["us_code"].append(ref)

    for m in PUBLIC_LAW_PATTERN.finditer(text):
        ref = f"Public Law {m.group(1)}-{m.group(2)}"
        if ref not in seen_refs:
            seen_refs.add(ref)
            facts["references"]["public_laws"].append(ref)

    for m in ACT_PATTERN.finditer(text):
        act_name = m.group(1).strip()
        if len(act_name) > 10 and act_name not in seen_refs:
            seen_refs.add(act_name)
            facts["references"]["acts"].append(act_name)

    # --- Funding ---
    for m in APPROPRIATION_PATTERN.finditer(text):
        dollar_match = DOLLAR_PATTERN.match(m.group(0))
        if not dollar_match:
            continue
        amount_str = dollar_match.group("amount")
        scale = dollar_match.group("scale")
        amount_numeric = parse_dollar_amount(amount_str, scale)
        context = m.group("context").strip()

        # Try to extract purpose from context
        purpose_match = re.search(r"for\s+(.{5,100}?)(?:,|;|\.|$)", context, re.IGNORECASE)
        purpose = purpose_match.group(1).strip() if purpose_match else None

        # Check availability
        avail_match = re.search(
            r"(?:until|to remain available (?:until)?|through)\s+"
            r"((?:September|October|December|March) \d{1,2}, \d{4}|expended)",
            context,
            re.IGNORECASE,
        )
        availability = avail_match.group(1) if avail_match else None

        display = f"${amount_str}"
        if scale:
            display += f" {scale}"

        facts["funding"].append(
            {
                "amount": display,
                "amount_numeric": amount_numeric,
                "purpose": purpose or "unspecified",
                "availability": availability,
                "source_text": m.group(0)[:300],
            }
        )

    # --- Dates ---
    seen_dates = set()
    for m in DATE_PATTERN.finditer(text):
        d = m.group(0)
        if d not in seen_dates:
            seen_dates.add(d)
            facts["dates"].append(d)

    for m in FISCAL_YEAR_PATTERN.finditer(text):
        fy = m.group(1)
        if fy not in facts["fiscal_years"]:
            facts["fiscal_years"].append(fy)

    # --- Deadlines ---
    for m in NOT_LATER_THAN.finditer(text):
        date = m.group(2) or f"{m.group(1)} days"
        # Look backward in text for context
        start = max(0, m.start() - 200)
        context = text[start : m.start()].strip()
        # Get last sentence fragment for the action
        action_parts = re.split(r"[.;]", context)
        action = action_parts[-1].strip() if action_parts else "unspecified"
        facts["deadlines"].append({"date": date, "action": action})

    # --- Duties ---
    for m in DUTY_PATTERN.finditer(text):
        facts["duties"].append(
            {
                "entity": m.group(1).strip(),
                "modal": m.group(2).strip(),
                "action": m.group(3).strip(),
            }
        )

    # --- Entities ---
    for m in ENTITY_PATTERN.finditer(text):
        name = m.group(1).strip()
        if name.lower() not in seen_entities:
            seen_entities.add(name.lower())
            facts["entities"].append(name)

    return facts


def extract_from_chunks(chunks: list) -> list[dict]:
    """Extract facts from a list of Chunk objects."""
    results = []
    for chunk in chunks:
        text = chunk.text if hasattr(chunk, "text") else chunk
        facts = extract_facts(text)
        facts["chunk_id"] = chunk.chunk_id if hasattr(chunk, "chunk_id") else None
        results.append(facts)
    return results
