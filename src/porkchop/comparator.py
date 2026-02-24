"""Phase 4: Bill version comparison — track what changed between versions.

Supports:
- Text-level diff (line-by-line)
- Claude-powered semantic diff (what does the change mean?)
- Spending change tracking (amounts added/removed/modified)
- Amendment detection
"""

import difflib
import json
import re
from typing import Optional

from .database import Database


def text_diff(text_a: str, text_b: str) -> dict:
    """Generate a structured diff between two bill text versions.

    Returns additions, removals, and modification statistics.
    """
    lines_a = text_a.splitlines()
    lines_b = text_b.splitlines()

    differ = difflib.unified_diff(lines_a, lines_b, lineterm="", n=3)
    diff_lines = list(differ)

    additions = []
    removals = []
    context_buffer = []

    for line in diff_lines:
        if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
            continue
        if line.startswith("+"):
            additions.append(line[1:])
        elif line.startswith("-"):
            removals.append(line[1:])

    # Find spending changes by looking for dollar amounts in additions/removals
    spending_added = _extract_spending_lines(additions)
    spending_removed = _extract_spending_lines(removals)

    return {
        "additions_count": len(additions),
        "removals_count": len(removals),
        "additions": additions[:100],  # Cap for storage
        "removals": removals[:100],
        "spending_added": spending_added,
        "spending_removed": spending_removed,
        "similarity_ratio": difflib.SequenceMatcher(None, text_a, text_b).ratio(),
    }


def compare_versions(
    db: Database,
    bill_id: int,
    from_version_id: int,
    to_version_id: int,
    use_ai: bool = False,
) -> dict:
    """Compare two stored bill versions.

    If use_ai=True, also runs Claude-powered semantic comparison.
    """
    from_version = db.get_version(from_version_id)
    to_version = db.get_version(to_version_id)

    if not from_version or not to_version:
        raise ValueError("One or both version IDs not found")

    text_a = from_version.get("cleaned_text") or from_version.get("raw_text", "")
    text_b = to_version.get("cleaned_text") or to_version.get("raw_text", "")

    if not text_a or not text_b:
        raise ValueError("One or both versions have no text content")

    result = text_diff(text_a, text_b)
    result["from_version"] = from_version["version_code"]
    result["to_version"] = to_version["version_code"]
    result["from_version_name"] = from_version.get("version_name", "")
    result["to_version_name"] = to_version.get("version_name", "")

    # AI-powered semantic diff
    if use_ai:
        from .analyzer import compare_sections

        # Compare in chunks to stay within context limits
        chunk_size = 10000
        ai_diffs = []

        # Split into comparable sections using division/title markers
        sections_a = _split_sections(text_a)
        sections_b = _split_sections(text_b)

        # Match sections by heading
        matched = _match_sections(sections_a, sections_b)

        for heading, (sec_a, sec_b) in list(matched.items())[:20]:  # Cap at 20 sections
            if sec_a and sec_b and sec_a != sec_b:
                ai_diff = compare_sections(
                    sec_a,
                    sec_b,
                    label_a=f"{result['from_version']} - {heading}",
                    label_b=f"{result['to_version']} - {heading}",
                )
                ai_diff["section"] = heading
                ai_diffs.append(ai_diff)
            elif sec_b and not sec_a:
                ai_diffs.append(
                    {"section": heading, "summary": "New section added", "additions": [sec_b[:500]]}
                )
            elif sec_a and not sec_b:
                ai_diffs.append(
                    {"section": heading, "summary": "Section removed", "removals": [sec_a[:500]]}
                )

        result["ai_analysis"] = ai_diffs

    # Store comparison in database
    db.add_comparison(
        bill_id,
        from_version_id,
        to_version_id,
        additions_count=result["additions_count"],
        removals_count=result["removals_count"],
        changes_json=json.dumps(result.get("ai_analysis", [])),
        spending_diff_json=json.dumps(
            {
                "added": result["spending_added"],
                "removed": result["spending_removed"],
            }
        ),
    )

    return result


def generate_changelog(db: Database, bill_id: int) -> str:
    """Generate a human-readable changelog across all versions of a bill."""
    versions = db.get_versions(bill_id)
    if len(versions) < 2:
        return "Only one version available — no changes to report."

    changelog = []
    for i in range(len(versions) - 1):
        v_from = versions[i]
        v_to = versions[i + 1]

        comparison = db.get_comparison(bill_id, v_from["id"], v_to["id"])
        if not comparison:
            changelog.append(
                f"\n## {v_from['version_code']} -> {v_to['version_code']}\nNo comparison data available."
            )
            continue

        entry = f"\n## {v_from.get('version_name', v_from['version_code'])} -> {v_to.get('version_name', v_to['version_code'])}"
        entry += f"\n- Lines added: {comparison['additions_count']}"
        entry += f"\n- Lines removed: {comparison['removals_count']}"

        # Parse spending diff
        spending = json.loads(comparison.get("spending_diff_json", "{}"))
        if spending.get("added"):
            entry += "\n- **Spending added:**"
            for s in spending["added"][:5]:
                entry += f"\n  - {s['amount']} — {s.get('context', 'unspecified')}"
        if spending.get("removed"):
            entry += "\n- **Spending removed:**"
            for s in spending["removed"][:5]:
                entry += f"\n  - {s['amount']} — {s.get('context', 'unspecified')}"

        # Parse AI analysis
        changes = json.loads(comparison.get("changes_json", "[]"))
        if changes:
            entry += "\n- **Key changes:**"
            for change in changes[:5]:
                entry += f"\n  - {change.get('section', '?')}: {change.get('summary', '')}"

        changelog.append(entry)

    bill = db.get_bill(bill_id)
    title = bill["title"] if bill else f"Bill #{bill_id}"
    header = f"# Changelog: {title}\n"
    return header + "\n".join(changelog)


def _extract_spending_lines(lines: list[str]) -> list[dict]:
    """Find dollar amounts in diff lines."""
    dollar_pattern = re.compile(
        r"\$\s*(?P<amount>[\d,]+(?:\.\d+)?)\s*(?P<scale>thousand|million|billion|trillion)?",
        re.IGNORECASE,
    )
    results = []
    for line in lines:
        m = dollar_pattern.search(line)
        if m:
            results.append(
                {
                    "amount": f"${m.group('amount')}"
                    + (f" {m.group('scale')}" if m.group("scale") else ""),
                    "context": line.strip()[:200],
                }
            )
    return results


def _split_sections(text: str) -> dict[str, str]:
    """Split bill text into sections keyed by heading."""
    sections = {}
    current_heading = "Preamble"
    current_lines = []

    heading_pattern = re.compile(
        r"^(DIVISION\s+[A-Z]+|TITLE\s+[IVXLCDM]+|SEC(?:TION)?\.?\s+\d+)\b.*$",
        re.IGNORECASE,
    )

    for line in text.splitlines():
        m = heading_pattern.match(line.strip())
        if m:
            if current_lines:
                sections[current_heading] = "\n".join(current_lines)
            current_heading = m.group(1).strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections[current_heading] = "\n".join(current_lines)

    return sections


def _match_sections(
    sections_a: dict[str, str], sections_b: dict[str, str]
) -> dict[str, tuple[Optional[str], Optional[str]]]:
    """Match sections between two versions by heading."""
    all_headings = list(dict.fromkeys(list(sections_a.keys()) + list(sections_b.keys())))
    return {
        heading: (sections_a.get(heading), sections_b.get(heading))
        for heading in all_headings
    }
