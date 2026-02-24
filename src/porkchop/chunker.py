"""Phase 2: Chunking — split cleaned bill text into processable pieces.

Ported from v0 chunk_legislation.py with improvements:
- Returns structured Chunk objects instead of writing files
- Both size-based and structure-based strategies
- Preserves legislative hierarchy metadata
"""

import re
from dataclasses import dataclass, field


DIVISION_PATTERN = re.compile(r"^DIVISION\s+([A-Z]+)\b", re.IGNORECASE)
TITLE_PATTERN = re.compile(r"^TITLE\s+([IVXLCDM]+)\b", re.IGNORECASE)
SECTION_PATTERN = re.compile(r"^(?:SEC(?:TION)?\.?\s+)(\d+)", re.IGNORECASE)

DEFAULT_MAX_CHARS = 20000


@dataclass
class Chunk:
    """A chunk of bill text with metadata."""

    chunk_id: str
    text: str
    division: str | None = None
    title: str | None = None
    section: str | None = None
    position: int = 0
    char_count: int = 0

    def __post_init__(self):
        self.char_count = len(self.text)


def chunk_by_size(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> list[Chunk]:
    """Split text into chunks of approximately max_chars, breaking at line boundaries."""
    lines = text.split("\n")
    chunks = []
    current_lines = []
    current_size = 0
    chunk_num = 0

    for line in lines:
        line_size = len(line) + 1  # +1 for newline
        if current_size + line_size > max_chars and current_lines:
            chunk_num += 1
            chunks.append(
                Chunk(
                    chunk_id=f"{chunk_num:03d}",
                    text="\n".join(current_lines),
                    position=chunk_num,
                )
            )
            current_lines = []
            current_size = 0

        current_lines.append(line)
        current_size += line_size

    if current_lines:
        chunk_num += 1
        chunks.append(
            Chunk(
                chunk_id=f"{chunk_num:03d}",
                text="\n".join(current_lines),
                position=chunk_num,
            )
        )

    return chunks


def chunk_by_structure(text: str, max_chars: int = DEFAULT_MAX_CHARS) -> list[Chunk]:
    """Split text on DIVISION/TITLE boundaries, sub-splitting oversized chunks."""
    lines = text.split("\n")
    chunks = []
    current_lines = []
    chunk_num = 0
    current_division = None
    current_title = None

    def flush():
        nonlocal current_lines, chunk_num
        if not current_lines:
            return
        content = "\n".join(current_lines)
        # Sub-split if oversized
        if len(content) > max_chars:
            sub_chunks = chunk_by_size(content, max_chars)
            for i, sc in enumerate(sub_chunks, 1):
                chunk_num += 1
                sc.chunk_id = _make_id(chunk_num, current_division, current_title, part=i)
                sc.division = current_division
                sc.title = current_title
                sc.position = chunk_num
                chunks.append(sc)
        else:
            chunk_num += 1
            chunks.append(
                Chunk(
                    chunk_id=_make_id(chunk_num, current_division, current_title),
                    text=content,
                    division=current_division,
                    title=current_title,
                    position=chunk_num,
                )
            )
        current_lines = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_lines:
                current_lines.append("")
            continue

        div_match = DIVISION_PATTERN.match(stripped)
        title_match = TITLE_PATTERN.match(stripped)

        if div_match:
            flush()
            current_division = div_match.group(1)
            current_title = None
            current_lines.append(stripped)
        elif title_match:
            flush()
            current_title = title_match.group(1)
            current_lines.append(stripped)
        else:
            current_lines.append(stripped)

    flush()
    return chunks


def chunk_text(
    text: str, strategy: str = "structure", max_chars: int = DEFAULT_MAX_CHARS
) -> list[Chunk]:
    """Chunk text using the specified strategy."""
    if strategy == "structure":
        return chunk_by_structure(text, max_chars)
    return chunk_by_size(text, max_chars)


def _make_id(
    num: int,
    division: str | None,
    title: str | None,
    part: int | None = None,
) -> str:
    parts = [f"{num:03d}"]
    if division:
        parts.append(f"div_{division.lower()}")
    if title:
        parts.append(f"title_{title.lower()}")
    if part:
        parts.append(f"part{part}")
    return "_".join(parts)
