"""Phase 3: Regex-based fact extraction from bill text.

Ported from v0 extract_legislative_facts.py with improvements:
- Module interface returning structured dicts
- Better funding amount parsing (handles millions/billions notation)
- Improved entity detection
- Deduplication built in
- Multi-strategy purpose extraction (forward context, backward context, heading)
- Recipient extraction (transferred to, Department of, Agency)
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
    r"\$\s*(?P<amount>[\d,]+(?:\.\d+)?),?\s*(?P<scale>thousand|million|billion|trillion)?",
    re.IGNORECASE,
)
APPROPRIATION_PATTERN = re.compile(
    r"\$\s*[\d,]+(?:\.\d+)?,?\s*(?:thousand|million|billion|trillion)?"
    r"(?P<context>.{0,300}?)(?:\.\s|\.$|;\s|$)",
    re.IGNORECASE | re.DOTALL,
)

# --- Purpose extraction patterns (ordered by specificity) ---
_P = re.IGNORECASE | re.DOTALL
# End-of-purpose terminators: period+space, period+end, newline pair, semicolon, Provided clause, end-of-string
_END = r"(?:[:,]\s*(?:to\s|of\s|and\s)|;\s|\.\s|\.$|\n\n|:\s*Provided|$)"
PURPOSE_PATTERNS = [
    # "for necessary expenses related to X"
    re.compile(rf"for\s+necessary\s+expenses\s+(?:related\s+to\s+|of\s+)?(.{{10,150}}?){_END}", _P),
    # "for an additional amount for FY XXXX, ... for the X program"
    re.compile(rf"for\s+an\s+additional\s+amount\s+for\s+fiscal\s+year\s+\d{{4}}.{{0,100}}?for\s+(?:the\s+)?(.{{10,150}}?){_END}", _P),
    # "shall be made available for the Secretary to X"
    re.compile(rf"shall\s+be\s+(?:made\s+)?available\s+(?:for\s+)?(?:the\s+)?(?:Secretary\s+to\s+)?(.{{10,150}}?){_END}", _P),
    # "to carry out X" / "to conduct X" / "to provide X" / "to make X" / "to fund X"
    re.compile(rf"(?:to\s+carry\s+out|to\s+conduct|to\s+provide|to\s+make|to\s+fund)\s+(.{{10,150}}?){_END}", _P),
    # "for X" — generic, but skip fiscal year / periods / additional amount as purpose
    re.compile(rf"for\s+(?!(?:fiscal\s+year|each\s+of\s+fiscal|the\s+period\s+beginning|an\s+additional\s+amount|the\s+period\s+of))(.{{10,150}}?){_END}", _P),
]

# --- Recipient patterns ---
RECIPIENT_PATTERNS = [
    # "transferred to 'Department of X—Y'" or "transferred to ''X''"
    re.compile(r"transferred\s+to\s+['\u2018\u2019\u201c\u201d]{0,2}([^''\n]{5,80}?)['\u2018\u2019\u201c\u201d]{0,2}(?:\s+for|\s*$)", re.IGNORECASE),
    # "to the Secretary of X"
    re.compile(r"to\s+the\s+(Secretary\s+of\s+[A-Z][a-z]+(?:\s+(?:and\s+)?[A-Z][a-z]+){0,3})", re.IGNORECASE),
    # "to the Department of X"
    re.compile(r"to\s+the\s+(Department\s+of\s+[A-Z][a-z]+(?:\s+(?:and\s+)?[A-Z][a-z]+){0,3})", re.IGNORECASE),
    # "to the X Administration/Agency/Commission"
    re.compile(r"to\s+(?:the\s+)?((?:[A-Z][a-z]+\s+){1,4}(?:Administration|Agency|Commission|Authority))", re.IGNORECASE),
]

# --- Section heading pattern (for fallback context) ---
HEADING_PATTERN = re.compile(
    r"(?:TITLE|DIVISION|CHAPTER)\s+[IVXLCDM\dA-Z]+\s*[—\-]\s*(.+?)(?:\n|$)",
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
    r"not\s+later\s+than\s+(?:(\d+)\s+days?\s+after\s+(?:the\s+date\s+of\s+)?[^,;.]{5,80}|"
    r"((?:January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+\d{1,2},\s*\d{4}))"
    r"[,;]?\s*(?:the\s+)?(.{10,200}?)(?:\.\s|\.$|\n\n|;\s|:\s*Provided)",
    re.IGNORECASE | re.DOTALL,
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

# Noise patterns that shouldn't be accepted as purpose
_FISCAL_YEAR_ONLY = re.compile(r"^(?:fiscal\s+year\s+\d{4}|each\s+of\s+(?:the\s+)?fiscal\s+years|each\s+of\s+those\s+fiscal)", re.IGNORECASE)
_PERIOD_BEGINNING = re.compile(r"^the\s+period\s+(?:beginning|of\s+fiscal)", re.IGNORECASE)
_JUNK_PURPOSE = re.compile(
    r"^(?:such\s+purpose|this\s+(?:section|subsection|chapter|title)|such\s+amounts?|"
    r"``\$|an\s+emergency\s+requirement|the\s+period\s+of|"
    r"the\s+matter\s+preceding|paragraph\s+\(\d|that\s+amount|"
    r"to\s+the\s+Secretary\b|related\s+expenses$)",
    re.IGNORECASE,
)


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


def _clean_purpose(purpose: str | None) -> str | None:
    """Clean and validate an extracted purpose string."""
    if not purpose:
        return None
    purpose = purpose.strip().rstrip(",;:")
    # Remove leading "the" if it makes the purpose clearer
    purpose = re.sub(r"^the\s+", "", purpose, flags=re.IGNORECASE)
    # Reject if too short (single word or less)
    if len(purpose) < 10:
        return None
    # Reject if it's just a fiscal year reference or other junk
    if _FISCAL_YEAR_ONLY.match(purpose):
        return None
    if _PERIOD_BEGINNING.match(purpose):
        return None
    if _JUNK_PURPOSE.match(purpose):
        return None
    # Clean up newlines from source text
    purpose = re.sub(r"\s+", " ", purpose)
    return purpose


def _extract_purpose(context: str) -> str | None:
    """Try multiple patterns to extract a meaningful purpose from context."""
    for pattern in PURPOSE_PATTERNS:
        m = pattern.search(context)
        if m:
            purpose = _clean_purpose(m.group(1))
            if purpose:
                return purpose
    return None


def _extract_purpose_backward(text: str, match_start: int) -> str | None:
    """Look backward from the dollar amount for purpose context.

    Useful when the purpose precedes the amount, e.g.:
    "for the Virginia Class Submarine program ... $5,691,000,000"
    or when a section heading provides context.
    """
    start = max(0, match_start - 300)
    backward = text[start:match_start]

    # Try forward purpose patterns on the backward text (purpose before amount)
    purpose = _extract_purpose(backward)
    if purpose:
        return purpose

    # Look for heading context
    heading_m = HEADING_PATTERN.search(backward)
    if heading_m:
        heading = heading_m.group(1).strip()
        if len(heading) > 10:
            return _clean_purpose(heading)

    # Look for sub-heading patterns like "OPERATIONS AND MAINTENANCE" or "PROCUREMENT"
    subheading = re.search(r"\n\s*([A-Z][A-Z ,\-&]{8,80})\s*\n", backward)
    if subheading:
        heading = subheading.group(1).strip()
        # Skip if it's just a state or boilerplate
        if len(heading) > 10 and not re.match(r"^(SEC|SECTION|TITLE|DIVISION)\b", heading):
            return _clean_purpose(heading.title())

    return None


def _extract_recipient(context: str) -> str | None:
    """Extract the receiving entity from spending context."""
    for pattern in RECIPIENT_PATTERNS:
        m = pattern.search(context)
        if m:
            recipient = m.group(1).strip().rstrip(",;:")
            # Clean up quotes and formatting
            recipient = re.sub(r"['\u2018\u2019\u201c\u201d]", "", recipient)
            recipient = re.sub(r"\s+", " ", recipient)
            # Remove em-dash suffixes for clean entity names
            if "\u2014" in recipient:
                recipient = recipient.split("\u2014")[0].strip()
            if "—" in recipient:
                recipient = recipient.split("—")[0].strip()
            if len(recipient) > 5:
                return recipient
    return None


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

        # Multi-strategy purpose extraction
        purpose = _extract_purpose(context)
        if not purpose:
            purpose = _extract_purpose_backward(text, m.start())

        # Extract recipient from context
        recipient = _extract_recipient(context)

        # Check availability
        avail_match = re.search(
            r"(?:until|to remain available (?:until)?|through)\s+"
            r"((?:September|October|December|March) \d{1,2}, \d{4}|expended)",
            context,
            re.IGNORECASE,
        )
        availability = avail_match.group(1) if avail_match else None

        # Extract fiscal years from context
        fy_matches = FISCAL_YEAR_PATTERN.findall(context)
        fiscal_years = ", ".join(sorted(set(fy_matches))) if fy_matches else None

        # Clean display amount — strip trailing comma
        display = f"${amount_str}"
        if scale:
            display += f" {scale}"

        facts["funding"].append(
            {
                "amount": display,
                "amount_numeric": amount_numeric,
                "purpose": purpose or "unspecified",
                "recipient": recipient,
                "availability": availability,
                "fiscal_years": fiscal_years,
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
        # Action is group 3 (text after the deadline date)
        action = m.group(3) or ""
        action = re.sub(r"\s+", " ", action).strip()
        # Clean up leading boilerplate
        action = re.sub(r"^(?:the\s+)?(?:Secretary|Administrator|Director|Commissioner)\s+shall\s+", "", action, flags=re.IGNORECASE)
        # Reject garbage: starts with punctuation, "Provided", "SEC.", truncated words
        if not action or len(action) < 10:
            action = "unspecified"
        elif re.match(r"^[.;,''\"]|^That\s+such|^SEC\.\s|^TITLE\s|^\w{1,4}$", action, re.IGNORECASE):
            action = "unspecified"
        # Truncate long actions
        if len(action) > 200:
            action = action[:200].rsplit(" ", 1)[0] + "..."
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
