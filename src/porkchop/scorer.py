"""Phase 5: Pork scoring — flag anomalous or unrelated spending.

Scores spending items 0-100 on "pork likelihood" using:
- Heuristic pre-screening (fast, no API)
- Claude-powered classification (deep analysis)

Scoring criteria:
- Unrelated to bill's stated purpose
- Named entity or location specificity (earmarks)
- Disproportionate amounts relative to section
- Last-minute additions (added in final version only)
- Unusually specific language for an appropriations bill
"""

import json
import os
from typing import Optional

from .database import Database


# Heuristic pork indicators (fast pre-screen)
EARMARK_SIGNALS = [
    "located in",
    "city of",
    "county of",
    "state of",
    "the university of",
    "the college of",
    "named after",
    "in honor of",
    "for the benefit of",
    "specific to",
    "exclusively for",
    "memorial",
    "institute",
    "foundation",
    "museum",
    "center for",
    "bridge",
    "highway",
    "road",
    "airport",
    "port",
    "harbor",
]

LARGE_AMOUNT_THRESHOLD = 100_000_000  # $100M
SMALL_EARMARK_THRESHOLD = 10_000_000  # $10M — specific small items are more suspicious


def heuristic_score(spending_item: dict, bill_title: str = "") -> dict:
    """Quick heuristic pork score (0-100) without API calls.

    Returns score and list of triggered flags.
    """
    score = 0
    flags = []

    purpose = (spending_item.get("purpose") or "").lower()
    recipient = (spending_item.get("recipient") or "").lower()
    source_text = (spending_item.get("source_text") or "").lower()
    amount = spending_item.get("amount_numeric", 0)
    combined = f"{purpose} {recipient} {source_text}"

    # Check earmark signals
    earmark_count = sum(1 for signal in EARMARK_SIGNALS if signal in combined)
    if earmark_count > 0:
        score += min(earmark_count * 15, 45)
        flags.append(f"earmark_signals:{earmark_count}")

    # Geographic specificity
    if any(
        word in combined
        for word in ["county", "district", "parish", "township", "borough"]
    ):
        score += 20
        flags.append("geographic_specificity")

    # Named entity specificity (specific organizations, not departments)
    if any(
        word in combined
        for word in ["university", "college", "hospital", "museum", "foundation", "institute"]
    ):
        score += 15
        flags.append("named_entity")

    # Amount anomalies
    if 0 < amount < SMALL_EARMARK_THRESHOLD:
        # Small specific amounts in large bills are more suspicious
        score += 10
        flags.append("small_specific_amount")

    # Check if purpose seems unrelated to bill title
    if bill_title:
        bill_words = set(bill_title.lower().split())
        purpose_words = set(purpose.split())
        # Very rough relevance check
        overlap = bill_words & purpose_words
        if len(overlap) == 0 and purpose != "unspecified":
            score += 15
            flags.append("potentially_unrelated")

    # Availability: "until expended" with no fiscal year limit
    if "until expended" in combined and not any(
        f"fiscal year" in combined for _ in [1]
    ):
        score += 5
        flags.append("open_ended_availability")

    return {
        "score": min(score, 100),
        "flags": flags,
        "method": "heuristic",
    }


PORK_SCORING_PROMPT = """You are a nonpartisan government spending analyst. Score this spending item for "pork" characteristics on a scale of 0-100.

**Bill title:** {bill_title}
**Bill purpose:** {bill_purpose}

**Spending item:**
- Amount: {amount}
- Purpose: {purpose}
- Recipient: {recipient}
- Source text: {source_text}

**Scoring criteria (0 = clearly on-topic, 100 = textbook pork barrel):**
- 0-20: Clearly related to the bill's stated purpose
- 20-40: Related but with some specificity that raises questions
- 40-60: Tangentially related, could reasonably belong elsewhere
- 60-80: Appears unrelated to bill's purpose, specific beneficiary
- 80-100: Classic earmark — named beneficiary, specific location, no clear connection to bill

**Consider:**
1. Is this spending directly related to the bill's stated purpose?
2. Does it name a specific institution, location, or individual?
3. Could this have been in a separate, more focused bill?
4. Is the amount proportionate?
5. Does the language suggest it was added as an amendment rather than part of the original bill?

**Historical context:** Compare against known earmark patterns from CAGW's Pig Book criteria:
- Requested by only one chamber of Congress
- Not specifically authorized
- Not competitively awarded
- Not requested by the President
- Greatly exceeds the President's budget request or previous year's funding
- Not the subject of congressional hearings
- Serves only a local or special interest

Return JSON:
{{
  "score": <0-100>,
  "reasoning": "2-3 sentences explaining the score",
  "flags": ["list of specific concerns"],
  "related_to_bill": true/false,
  "earmark_indicators": ["any CAGW Pig Book criteria met"]
}}"""


def ai_score(
    spending_item: dict,
    bill_title: str,
    bill_purpose: str = "",
    model: str = "claude-haiku-4-5-20251001",
) -> dict:
    """Score a spending item using Claude for deep analysis."""
    try:
        import anthropic
    except ImportError:
        raise ImportError("anthropic package required. Install: pip install anthropic")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)

    response = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[
            {
                "role": "user",
                "content": PORK_SCORING_PROMPT.format(
                    bill_title=bill_title,
                    bill_purpose=bill_purpose,
                    amount=spending_item.get("amount", "unknown"),
                    purpose=spending_item.get("purpose", "unspecified"),
                    recipient=spending_item.get("recipient", "unspecified"),
                    source_text=(spending_item.get("source_text") or "")[:500],
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
        result = json.loads(response_text)
        result["method"] = "ai"
        result["model"] = model
        return result
    except json.JSONDecodeError:
        return {
            "score": 50,
            "reasoning": response_text,
            "flags": ["parse_error"],
            "method": "ai",
            "model": model,
        }


def score_bill(
    bill_id: int,
    db: Database,
    use_ai: bool = False,
    ai_threshold: int = 30,
) -> dict:
    """Score all spending items in a bill.

    Strategy:
    1. Run heuristic scoring on all items (free, fast)
    2. If use_ai=True, run AI scoring on items above ai_threshold
    3. Store all scores in database

    Returns summary statistics.
    """
    bill = db.get_bill(bill_id)
    if not bill:
        raise ValueError(f"Bill {bill_id} not found")

    spending_items = db.get_spending(bill_id)
    if not spending_items:
        raise ValueError(f"No spending items found for bill {bill_id}. Run analysis first.")

    results = {
        "bill_id": bill_id,
        "title": bill["title"],
        "items_scored": 0,
        "avg_score": 0,
        "max_score": 0,
        "high_pork": [],  # Items scoring >= 60
        "all_scores": [],
    }

    total_score = 0

    for item in spending_items:
        # Heuristic first
        h_result = heuristic_score(item, bill.get("title", ""))

        # AI scoring for items above threshold
        if use_ai and h_result["score"] >= ai_threshold:
            try:
                a_result = ai_score(
                    item,
                    bill.get("title", ""),
                    bill.get("summary", ""),
                )
                # Blend scores: 30% heuristic + 70% AI
                final_score = int(h_result["score"] * 0.3 + a_result["score"] * 0.7)
                flags = list(set(h_result["flags"] + a_result.get("flags", [])))
                reasoning = a_result.get("reasoning", "")
                method = "blended"
            except Exception:
                final_score = h_result["score"]
                flags = h_result["flags"]
                reasoning = "AI scoring failed, using heuristic only"
                method = "heuristic"
        else:
            final_score = h_result["score"]
            flags = h_result["flags"]
            reasoning = ""
            method = "heuristic"

        # Store in database
        db.add_pork_score(
            bill_id,
            item["id"],
            final_score,
            reasons=reasoning,
            flags=json.dumps(flags),
            model_used=method,
        )

        score_entry = {
            "spending_item_id": item["id"],
            "amount": item["amount"],
            "purpose": item.get("purpose"),
            "score": final_score,
            "flags": flags,
        }
        results["all_scores"].append(score_entry)

        if final_score >= 60:
            results["high_pork"].append(score_entry)

        total_score += final_score
        results["items_scored"] += 1

        if final_score > results["max_score"]:
            results["max_score"] = final_score

    if results["items_scored"] > 0:
        results["avg_score"] = round(total_score / results["items_scored"], 1)

    # Sort high pork by score descending
    results["high_pork"].sort(key=lambda x: x["score"], reverse=True)
    results["all_scores"].sort(key=lambda x: x["score"], reverse=True)

    return results
