"""Phase 1: Text cleaning — remove GPO formatting artifacts from raw bill text.

Ported from v0 cleanText.py with improvements:
- Module interface (not script)
- Configurable phases
- Preserves section references that v0's aggressive regex mangled
"""

import re


# Phase 1: Line-level removal patterns
LINE_REMOVAL_PATTERNS = [
    # VerDate headers from GPO publishing
    re.compile(r"^VerDate.*$", re.MULTILINE),
    # Jkt job ticket references
    re.compile(r"^.*Jkt.*$", re.MULTILINE),
    # Windows file paths (C:\USERS\..., I:\FY25\...)
    re.compile(r"^[A-Z]:\\.*$", re.MULTILINE),
    # XML file references with pipe notation
    re.compile(r"^\s*[A-Za-z]:\\.*\.xml\s*\(\d+\|\d+\)\s*$", re.MULTILINE),
    # Mixed number + XML references
    re.compile(r"^\s*\d*,?\s*[A-Za-z]:\\.*\.xml\s*\(\d+\|\d+\)\s*$", re.MULTILINE),
    # Any line with pipe notation (###|###)
    re.compile(r"^\s*.*\(\d+\|\d+\).*$", re.MULTILINE),
    # Timestamp lines: "December 17, 2024 (5:46 p.m.)"
    re.compile(
        r"^\w+\s+\d{1,2},\s+\d{4}\s*\(\d{1,2}:\d{2}\s*[ap]\.m\.\).*$",
        re.MULTILINE,
    ),
    # Standalone page numbers (just digits, possibly with commas)
    re.compile(r"^\s*\d+(\s*,\s*\d+)*\s*$", re.MULTILINE),
]

# Phase 2: Leading line number pattern
LEADING_LINE_NUMBER = re.compile(r"^\s*\d+\s+")

# Phase 2: Embedded number artifacts — but only when surrounded by lowercase letters
# v0 used ([A-Za-z])(\d+)\s+([A-Za-z]) which mangled section refs like "42 U.S.C."
# Improved: only match lowercase-digit-space-lowercase (OCR artifact pattern)
EMBEDDED_NUMBER_ARTIFACT = re.compile(r"([a-z])(\d+)\s+([a-z])")


def clean_text(text: str) -> str:
    """Clean raw GPO bill text through 3 phases.

    Phase 1: Remove extraneous lines (VerDate, Jkt, XML refs, timestamps, page numbers)
    Phase 2: Strip leading line numbers, fix OCR embedded-number artifacts
    Phase 3: Normalize whitespace
    """
    # Phase 1: Remove entire lines matching noise patterns
    for pattern in LINE_REMOVAL_PATTERNS:
        text = pattern.sub("", text)

    # Phase 2: Clean individual lines
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Remove leading line numbers (e.g., "3 " or "10 ")
        stripped = LEADING_LINE_NUMBER.sub("", stripped)

        # Fix OCR artifacts: "strate2 gies" -> "strategies"
        # Only lowercase-to-lowercase to avoid mangling "42 U.S.C." style refs
        stripped = EMBEDDED_NUMBER_ARTIFACT.sub(r"\1\3", stripped)

        if stripped:
            cleaned.append(stripped)

    text = "\n".join(cleaned)

    # Phase 3: Normalize whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()

    return text


def clean_file(input_path: str, output_path: str | None = None) -> str:
    """Clean a bill text file. Returns cleaned text and optionally writes to output_path."""
    with open(input_path, "r", encoding="utf-8") as f:
        raw = f.read()

    cleaned = clean_text(raw)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(cleaned)

    return cleaned
