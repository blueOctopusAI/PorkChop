"""PorkChop FastAPI — HTTP wrapper around the bill processing pipeline.

Replaces the subprocess-based approach in the Next.js process route.
Run with: uvicorn porkchop.api:app --host 0.0.0.0 --port 8000

Endpoints:
  POST /api/process  — Full pipeline: fetch -> clean -> chunk -> extract -> score
  GET  /api/health   — Health check with bill count
  GET  /api/bills    — List all processed bills
"""

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from porkchop.database import Database
from porkchop.ingestion import fetch_bill, fetch_bill_text, parse_bill_id
from porkchop.cleaner import clean_text
from porkchop.chunker import chunk_text
from porkchop.extractor import extract_from_chunks
from porkchop.scorer import score_bill

app = FastAPI(
    title="PorkChop API",
    description="AI that reads the bills so you don't have to.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# Database path: data/porkchop.db relative to project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DB_PATH = PROJECT_ROOT / "data" / "porkchop.db"


def get_db() -> Database:
    """Get a Database instance using the standard path."""
    return Database(DB_PATH)


# --- Request/Response Models ---


class ProcessRequest(BaseModel):
    bill_id: str
    congress_api_key: Optional[str] = None


class ProcessResponse(BaseModel):
    status: str
    bill_db_id: int
    title: str
    message: str


class HealthResponse(BaseModel):
    status: str
    bills: int


class BillSummary(BaseModel):
    id: int
    congress: int
    bill_type: str
    bill_number: int
    title: Optional[str] = None
    short_title: Optional[str] = None
    status: Optional[str] = None
    introduced_date: Optional[str] = None
    sponsors: Optional[str] = None
    fetched_at: Optional[str] = None


class ErrorResponse(BaseModel):
    error: str


# --- Endpoints ---


@app.get("/api/health", response_model=HealthResponse)
def health():
    """Health check with bill count from the database."""
    db = get_db()
    stats = db.get_stats()
    return HealthResponse(status="ok", bills=stats["bills_analyzed"])


@app.get("/api/bills", response_model=list[BillSummary])
def list_bills():
    """List all bills in the database."""
    db = get_db()
    bills = db.list_bills(limit=100)
    return [BillSummary(**b) for b in bills]


@app.post("/api/process")
def process_bill(req: ProcessRequest):
    """Full pipeline: fetch -> clean -> chunk -> extract -> store -> score.

    Accepts a bill ID (e.g., "HR-815") and an optional Congress API key.
    If the bill already exists in the database, returns the cached result.
    """
    db = get_db()

    # --- Handle Congress API key ---
    api_key = req.congress_api_key or os.environ.get("CONGRESS_API_KEY")
    if not api_key:
        return ErrorResponse(
            error="Congress.gov API key required. Get one free at https://api.data.gov/signup/"
        )

    # Set the key in the environment so ingestion module picks it up
    original_key = os.environ.get("CONGRESS_API_KEY")
    os.environ["CONGRESS_API_KEY"] = api_key

    try:
        # --- Parse bill ID ---
        congress, bill_type, bill_number = parse_bill_id(req.bill_id)

        # --- Check if bill already exists ---
        existing = db.find_bill(congress, bill_type, bill_number)
        if existing:
            # Check if it has sections (i.e., has been fully processed)
            sections = db.get_sections(existing["id"])
            if sections:
                return ProcessResponse(
                    status="cached",
                    bill_db_id=existing["id"],
                    title=existing.get("title") or f"{bill_type.upper()} {bill_number}",
                    message="Bill already processed. View it now.",
                )

        # --- Step 1: Fetch bill metadata + text ---
        bill_result = fetch_bill(req.bill_id, db=db)
        bill_db_id = bill_result.get("db_id")

        if not bill_db_id:
            return ErrorResponse(error="Failed to fetch bill metadata")

        # Fetch the full text
        raw_text = fetch_bill_text(req.bill_id, version="latest", db=db)

        if not raw_text:
            return ErrorResponse(error="Bill text not available from Congress.gov")

        # --- Step 2: Clean ---
        cleaned = clean_text(raw_text)

        # --- Step 3: Chunk ---
        chunks = chunk_text(cleaned, strategy="structure")

        # --- Step 4: Extract facts ---
        all_facts = extract_from_chunks(chunks)

        # --- Step 5: Store sections + extracted data ---
        # Get or create a version record for the cleaned text
        versions = db.get_versions(bill_db_id)
        version_id = versions[-1]["id"] if versions else None

        # Update the version with cleaned text
        if version_id:
            db.upsert_version(
                bill_db_id,
                versions[-1]["version_code"],
                cleaned_text=cleaned,
            )

        for i, (chunk, facts) in enumerate(zip(chunks, all_facts)):
            section_id = db.add_section(
                bill_db_id,
                chunk.text,
                version_id=version_id,
                section_number=chunk.chunk_id,
                title=chunk.division or chunk.title,
                level=(
                    "division" if chunk.division
                    else "title" if chunk.title
                    else "chunk"
                ),
                position=i,
            )

            for item in facts.get("funding", []):
                db.add_spending_item(
                    bill_db_id,
                    item["amount"],
                    section_id=section_id,
                    amount_numeric=item.get("amount_numeric", 0),
                    purpose=item.get("purpose"),
                    recipient=item.get("recipient"),
                    availability=item.get("availability"),
                    fiscal_years=item.get("fiscal_years"),
                    source_text=item.get("source_text"),
                )

            for ref in facts.get("references", {}).get("us_code", []):
                db.add_reference(bill_db_id, "us_code", ref, section_id=section_id)
            for ref in facts.get("references", {}).get("public_laws", []):
                db.add_reference(bill_db_id, "public_law", ref, section_id=section_id)
            for ref in facts.get("references", {}).get("acts", []):
                db.add_reference(bill_db_id, "act", ref, section_id=section_id)

            for dl in facts.get("deadlines", []):
                db.add_deadline(
                    bill_db_id,
                    section_id=section_id,
                    date=dl.get("date"),
                    action=dl.get("action"),
                )

            for entity in facts.get("entities", []):
                db.add_entity(bill_db_id, entity, section_id=section_id)

        # --- Step 6: Pork scoring (heuristic, no AI) ---
        spending_items = db.get_spending(bill_db_id)
        if spending_items:
            score_bill(bill_db_id, db, use_ai=False)

        title = bill_result.get("title") or f"{bill_type.upper()} {bill_number}"

        return ProcessResponse(
            status="processed",
            bill_db_id=bill_db_id,
            title=title,
            message="Bill fetched, processed, and scored.",
        )

    except ValueError as e:
        return ErrorResponse(error=str(e))
    except Exception:
        return ErrorResponse(error="Processing failed. Please try again.")
    finally:
        # Restore original API key
        if original_key is not None:
            os.environ["CONGRESS_API_KEY"] = original_key
        elif "CONGRESS_API_KEY" in os.environ and req.congress_api_key:
            del os.environ["CONGRESS_API_KEY"]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
