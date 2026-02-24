"""Phase 2: Claude-powered semantic analysis of bill text.

Replaces regex extraction with LLM understanding. Uses:
- Haiku for bulk per-section extraction (cost-effective)
- Sonnet for bill-level summaries and complex analysis

Requires ANTHROPIC_API_KEY env var.
"""

import json
import os
from typing import Optional

from .chunker import Chunk
from .database import Database

SECTION_ANALYSIS_PROMPT = """You are a nonpartisan legislative analyst. Analyze this section of a congressional bill and extract structured data.

<bill_section>
{text}
</bill_section>

Extract the following. Be precise — use exact dollar amounts, exact dates, exact entity names from the text. If a field has no data, return an empty array.

Return JSON with this exact structure:
{{
  "summary": "2-3 sentence plain English summary of what this section does",
  "funding": [
    {{
      "amount": "$X,XXX,XXX",
      "amount_numeric": 1000000,
      "purpose": "what the money is for",
      "recipient": "who gets the money (department, agency, program)",
      "availability": "when funds expire or 'until expended'",
      "fiscal_years": ["2025", "2026"]
    }}
  ],
  "deadlines": [
    {{
      "date": "exact date or 'X days after enactment'",
      "action": "what must happen by this date",
      "responsible_entity": "who is responsible"
    }}
  ],
  "legal_references": [
    {{
      "ref_type": "us_code|public_law|act",
      "ref_text": "exact citation as written",
      "context": "what the reference is about"
    }}
  ],
  "new_authorities": [
    {{
      "entity": "who gets new authority",
      "authority": "what they can now do",
      "conditions": "any conditions or limitations"
    }}
  ],
  "entities": [
    {{
      "name": "exact entity name",
      "role": "what role they play in this section"
    }}
  ],
  "pork_flags": [
    "any spending items that appear unrelated to the bill's stated purpose, earmarks for specific locations/entities, or unusually specific appropriations"
  ]
}}"""

BILL_SUMMARY_PROMPT = """You are a nonpartisan legislative analyst writing for a general audience. Summarize this entire bill based on the section analyses below.

<bill_title>{title}</bill_title>

<section_analyses>
{analyses}
</section_analyses>

Write a comprehensive but accessible summary covering:
1. **What this bill does** (1-2 paragraphs, plain English)
2. **Total spending** — sum of all appropriations with the biggest line items
3. **Key deadlines** — the most important dates and what happens
4. **Who's affected** — which agencies, programs, populations
5. **Notable provisions** — anything surprising, controversial, or particularly impactful
6. **Pork watch** — any spending items that seem unrelated to the bill's stated purpose

Write for a smart non-expert. No jargon. If something is $100,000,000, say "$100 million."
"""

COMPARE_PROMPT = """You are a nonpartisan legislative analyst. Compare these two versions of the same bill section and identify what changed.

<version_a label="{label_a}">
{text_a}
</version_a>

<version_b label="{label_b}">
{text_b}
</version_b>

Return JSON:
{{
  "summary": "1-2 sentence summary of what changed",
  "additions": ["list of new provisions, funding items, or requirements added"],
  "removals": ["list of provisions, funding items, or requirements removed"],
  "modifications": [
    {{
      "what": "what was modified",
      "from": "original language/amount",
      "to": "new language/amount"
    }}
  ],
  "spending_changes": [
    {{
      "item": "what the spending is for",
      "old_amount": "$X or null if new",
      "new_amount": "$Y or null if removed",
      "change": "+$Z or -$Z"
    }}
  ]
}}"""


def _get_client():
    """Get Anthropic client (lazy import to avoid dependency when not analyzing)."""
    try:
        import anthropic
    except ImportError:
        raise ImportError(
            "anthropic package required for analysis. Install: pip install anthropic"
        )
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")
    return anthropic.Anthropic(api_key=api_key)


def analyze_section(text: str, model: str = "claude-haiku-4-5-20251001") -> dict:
    """Analyze a single section of bill text using Claude.

    Uses Haiku by default for cost efficiency on bulk extraction.
    """
    client = _get_client()

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": SECTION_ANALYSIS_PROMPT.format(text=text[:15000]),
            }
        ],
    )

    # Parse JSON from response
    response_text = response.content[0].text
    # Handle potential markdown code blocks
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]

    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        return {"summary": response_text, "parse_error": True}


def summarize_bill(
    title: str,
    section_analyses: list[dict],
    model: str = "claude-sonnet-4-6-20250514",
) -> str:
    """Generate a bill-level summary from section analyses.

    Uses Sonnet for higher quality on the synthesis task.
    """
    client = _get_client()

    # Format section analyses for the prompt
    analyses_text = ""
    for i, analysis in enumerate(section_analyses, 1):
        summary = analysis.get("summary", "No summary available")
        funding = analysis.get("funding", [])
        funding_text = ""
        if funding:
            items = [f"  - {f['amount']} for {f['purpose']}" for f in funding[:5]]
            funding_text = "\n" + "\n".join(items)
        analyses_text += f"\n### Section {i}\n{summary}{funding_text}\n"

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": BILL_SUMMARY_PROMPT.format(
                    title=title, analyses=analyses_text
                ),
            }
        ],
    )

    return response.content[0].text


def compare_sections(
    text_a: str,
    text_b: str,
    label_a: str = "Version A",
    label_b: str = "Version B",
    model: str = "claude-haiku-4-5-20251001",
) -> dict:
    """Compare two versions of bill text using Claude."""
    client = _get_client()

    # Truncate if too long for context
    max_per_version = 10000
    text_a = text_a[:max_per_version]
    text_b = text_b[:max_per_version]

    response = client.messages.create(
        model=model,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": COMPARE_PROMPT.format(
                    text_a=text_a,
                    text_b=text_b,
                    label_a=label_a,
                    label_b=label_b,
                ),
            }
        ],
    )

    response_text = response.content[0].text
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]

    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        return {"summary": response_text, "parse_error": True}


def analyze_bill(bill_id: int, db: Database, model: str = "claude-haiku-4-5-20251001") -> dict:
    """Full analysis pipeline: analyze all sections of a bill and generate summary.

    1. Get sections from database
    2. Analyze each section with Claude (Haiku)
    3. Store results in database
    4. Generate bill-level summary (Sonnet)
    5. Store summary

    Returns analysis results dict.
    """
    bill = db.get_bill(bill_id)
    if not bill:
        raise ValueError(f"Bill {bill_id} not found in database")

    sections = db.get_sections(bill_id)
    if not sections:
        raise ValueError(f"No sections found for bill {bill_id}. Run chunking first.")

    results = {"bill_id": bill_id, "title": bill["title"], "sections": []}

    # Analyze each section
    for section in sections:
        analysis = analyze_section(section["text"], model=model)
        analysis["section_id"] = section["id"]
        analysis["section_number"] = section.get("section_number")
        results["sections"].append(analysis)

        # Store in database
        if analysis.get("summary"):
            db.add_summary(
                bill_id,
                analysis["summary"],
                section_id=section["id"],
                model_used=model,
            )

        for item in analysis.get("funding", []):
            db.add_spending_item(
                bill_id,
                item["amount"],
                section_id=section["id"],
                amount_numeric=item.get("amount_numeric", 0),
                purpose=item.get("purpose"),
                recipient=item.get("recipient"),
                availability=item.get("availability"),
                fiscal_years=json.dumps(item.get("fiscal_years", [])),
                source_text=item.get("source_text"),
            )

        for ref in analysis.get("legal_references", []):
            db.add_reference(
                bill_id,
                ref["ref_type"],
                ref["ref_text"],
                section_id=section["id"],
            )

        for deadline in analysis.get("deadlines", []):
            db.add_deadline(
                bill_id,
                section_id=section["id"],
                date=deadline.get("date"),
                action=deadline.get("action"),
                responsible_entity=deadline.get("responsible_entity"),
            )

        for entity in analysis.get("entities", []):
            db.add_entity(
                bill_id,
                entity["name"],
                section_id=section["id"],
                role=entity.get("role"),
            )

    # Generate bill-level summary
    bill_summary = summarize_bill(
        bill["title"],
        results["sections"],
        model="claude-sonnet-4-6-20250514",
    )
    results["summary"] = bill_summary
    db.add_summary(bill_id, bill_summary, model_used="claude-sonnet-4-6-20250514")

    return results
