"""Phase 1: Bill ingestion from Congress.gov API and GovInfo.

Fetch any bill by number. Supports:
- Congress.gov API v3 for metadata + text URLs
- GovInfo API for bulk XML (USLM format)
- Local file import as fallback

Requires a free api.data.gov API key (set CONGRESS_API_KEY env var).
"""

import os
import re
import time
from typing import Optional

import httpx

CONGRESS_API_BASE = "https://api.congress.gov/v3"
GOVINFO_API_BASE = "https://api.govinfo.gov"

BILL_TYPES = {
    "hr": "hr",
    "s": "s",
    "hjres": "hjres",
    "sjres": "sjres",
    "hconres": "hconres",
    "sconres": "sconres",
    "hres": "hres",
    "sres": "sres",
}

VERSION_NAMES = {
    "ih": "Introduced in House",
    "is": "Introduced in Senate",
    "rh": "Reported in House",
    "rs": "Reported in Senate",
    "eh": "Engrossed in House",
    "es": "Engrossed in Senate",
    "enr": "Enrolled",
    "pcs": "Placed on Calendar Senate",
    "pch": "Placed on Calendar House",
    "ats": "Agreed to Senate",
    "ath": "Agreed to House",
    "cps": "Considered and Passed Senate",
    "cph": "Considered and Passed House",
    "rfs": "Referred in Senate",
    "rfh": "Referred in House",
}


def get_api_key() -> str:
    """Get Congress.gov API key from environment."""
    key = os.environ.get("CONGRESS_API_KEY", "")
    if not key:
        raise ValueError(
            "CONGRESS_API_KEY not set. Get a free key at https://api.data.gov/signup/"
        )
    return key


def parse_bill_id(bill_id: str) -> tuple[int, str, int]:
    """Parse a bill identifier like 'HR-10515', 'hr10515', 'HR 10515-118', '118-hr-10515'.

    Returns (congress, bill_type, bill_number).
    If congress is not specified, defaults to the current congress.
    """
    bill_id = bill_id.strip().upper()

    # Try pattern: 118-HR-10515 or 118/HR/10515
    m = re.match(r"(\d{2,3})[/\-]([A-Z]+)[/\-](\d+)", bill_id)
    if m:
        return int(m.group(1)), m.group(2).lower(), int(m.group(3))

    # Try pattern: HR-10515 or HR10515 or HR 10515
    m = re.match(r"([A-Z]+)[/\-\s]*(\d+)(?:[/\-](\d{2,3}))?", bill_id)
    if m:
        bill_type = m.group(1).lower()
        bill_number = int(m.group(2))
        congress = int(m.group(3)) if m.group(3) else _current_congress()
        return congress, bill_type, bill_number

    raise ValueError(f"Cannot parse bill ID: {bill_id}")


def _current_congress() -> int:
    """Estimate the current congress number from the year."""
    from datetime import date
    year = date.today().year
    return ((year - 1789) // 2) + 1


class CongressClient:
    """Client for the Congress.gov API v3."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or get_api_key()
        self.client = httpx.Client(
            base_url=CONGRESS_API_BASE,
            params={"api_key": self.api_key},
            headers={"Accept": "application/json"},
            timeout=30.0,
        )

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def get_bill(self, congress: int, bill_type: str, bill_number: int) -> dict:
        """Fetch bill metadata."""
        resp = self.client.get(f"/bill/{congress}/{bill_type}/{bill_number}")
        resp.raise_for_status()
        return resp.json().get("bill", resp.json())

    def get_bill_text_info(self, congress: int, bill_type: str, bill_number: int) -> list[dict]:
        """Fetch available text versions and format URLs for a bill."""
        resp = self.client.get(f"/bill/{congress}/{bill_type}/{bill_number}/text")
        resp.raise_for_status()
        data = resp.json()
        return data.get("textVersions", [])

    def get_bill_actions(self, congress: int, bill_type: str, bill_number: int) -> list[dict]:
        """Fetch bill actions/history."""
        resp = self.client.get(f"/bill/{congress}/{bill_type}/{bill_number}/actions")
        resp.raise_for_status()
        data = resp.json()
        return data.get("actions", [])

    def get_bill_subjects(self, congress: int, bill_type: str, bill_number: int) -> dict:
        """Fetch bill subjects/topics."""
        resp = self.client.get(f"/bill/{congress}/{bill_type}/{bill_number}/subjects")
        resp.raise_for_status()
        return resp.json()

    def search_bills(self, query: str, congress: Optional[int] = None, limit: int = 20) -> list[dict]:
        """Search for bills by keyword."""
        params = {"query": query, "limit": limit}
        if congress:
            params["congress"] = congress
        resp = self.client.get("/bill", params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("bills", [])

    def fetch_text_content(self, text_url: str) -> str:
        """Fetch actual bill text from a Congress.gov URL."""
        # Congress.gov text URLs are direct HTML/text pages
        resp = httpx.get(
            text_url,
            headers={"Accept": "text/plain"},
            follow_redirects=True,
            timeout=60.0,
        )
        resp.raise_for_status()
        return resp.text


class GovInfoClient:
    """Client for the GovInfo API (bulk data)."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or get_api_key()
        self.client = httpx.Client(
            base_url=GOVINFO_API_BASE,
            params={"api_key": self.api_key},
            headers={"Accept": "application/json"},
            timeout=30.0,
        )

    def close(self):
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def get_bill_package(
        self, congress: int, bill_type: str, bill_number: int, version: str = "enr"
    ) -> dict:
        """Fetch a bill package from GovInfo.

        Package ID format: BILLS-{congress}{billtype}{number}{version}
        Example: BILLS-118hr10515enr
        """
        package_id = f"BILLS-{congress}{bill_type}{bill_number}{version}"
        resp = self.client.get(f"/packages/{package_id}/summary")
        resp.raise_for_status()
        return resp.json()

    def get_bill_text(
        self, congress: int, bill_type: str, bill_number: int, version: str = "enr"
    ) -> str:
        """Fetch bill text in HTM format from GovInfo."""
        package_id = f"BILLS-{congress}{bill_type}{bill_number}{version}"
        resp = self.client.get(
            f"/packages/{package_id}/htm",
            follow_redirects=True,
        )
        resp.raise_for_status()
        return resp.text

    def get_bill_xml(
        self, congress: int, bill_type: str, bill_number: int, version: str = "enr"
    ) -> str:
        """Fetch bill text in XML (USLM) format from GovInfo."""
        package_id = f"BILLS-{congress}{bill_type}{bill_number}{version}"
        resp = self.client.get(
            f"/packages/{package_id}/xml",
            follow_redirects=True,
        )
        resp.raise_for_status()
        return resp.text


def fetch_bill(bill_id: str, db=None) -> dict:
    """High-level: fetch a bill and store in database.

    Returns dict with bill metadata, text versions, and database IDs.
    """
    congress, bill_type, bill_number = parse_bill_id(bill_id)

    with CongressClient() as client:
        # Fetch metadata
        bill_data = client.get_bill(congress, bill_type, bill_number)

        result = {
            "congress": congress,
            "bill_type": bill_type,
            "bill_number": bill_number,
            "title": bill_data.get("title", ""),
            "short_title": bill_data.get("shortTitle"),
            "introduced_date": bill_data.get("introducedDate"),
            "sponsors": _extract_sponsors(bill_data),
            "status": bill_data.get("latestAction", {}).get("text", ""),
        }

        # Fetch text versions
        text_versions = client.get_bill_text_info(congress, bill_type, bill_number)
        result["versions"] = []
        for tv in text_versions:
            version_info = {
                "version_code": tv.get("type", "unknown"),
                "version_name": VERSION_NAMES.get(
                    tv.get("type", "").lower(), tv.get("type", "unknown")
                ),
                "date": tv.get("date"),
                "formats": {},
            }
            for fmt in tv.get("formats", []):
                url = fmt.get("url", "")
                if "Formatted Text" in fmt.get("type", ""):
                    version_info["formats"]["text"] = url
                elif "XML" in fmt.get("type", ""):
                    version_info["formats"]["xml"] = url
                elif "PDF" in fmt.get("type", ""):
                    version_info["formats"]["pdf"] = url
            result["versions"].append(version_info)

        # Store in database if provided
        if db:
            bill_db_id = db.upsert_bill(
                congress,
                bill_type,
                bill_number,
                title=result["title"],
                short_title=result.get("short_title"),
                introduced_date=result.get("introduced_date"),
                sponsors=result.get("sponsors"),
                status=result.get("status"),
                source="congress.gov",
            )
            result["db_id"] = bill_db_id

            # Store versions
            for v in result["versions"]:
                version_id = db.upsert_version(
                    bill_db_id,
                    v["version_code"],
                    version_name=v["version_name"],
                    text_url=v["formats"].get("text"),
                    xml_url=v["formats"].get("xml"),
                )
                v["db_id"] = version_id

    return result


def fetch_bill_text(bill_id: str, version: str = "latest", db=None) -> str:
    """Fetch the actual text of a bill version.

    If version is 'latest', fetches the most recent version.
    """
    congress, bill_type, bill_number = parse_bill_id(bill_id)

    with CongressClient() as client:
        text_versions = client.get_bill_text_info(congress, bill_type, bill_number)

        if not text_versions:
            raise ValueError(f"No text versions available for {bill_id}")

        if version == "latest":
            target = text_versions[-1]
        else:
            target = None
            for tv in text_versions:
                if tv.get("type", "").lower() == version.lower():
                    target = tv
                    break
            if not target:
                available = [tv.get("type", "?") for tv in text_versions]
                raise ValueError(
                    f"Version '{version}' not found. Available: {available}"
                )

        # Prefer formatted text, fall back to XML
        text_url = None
        for fmt in target.get("formats", []):
            if "Formatted Text" in fmt.get("type", ""):
                text_url = fmt.get("url")
                break
        if not text_url:
            for fmt in target.get("formats", []):
                if "XML" in fmt.get("type", ""):
                    text_url = fmt.get("url")
                    break

        if not text_url:
            raise ValueError("No text or XML URL found for this version")

        text = client.fetch_text_content(text_url)

        # Store in database if provided
        if db:
            bill_db_id = db.find_bill(congress, bill_type, bill_number)
            if bill_db_id:
                version_code = target.get("type", "unknown")
                db.upsert_version(
                    bill_db_id["id"],
                    version_code,
                    raw_text=text,
                )

        return text


def import_from_file(file_path: str, bill_id: str, db=None) -> dict:
    """Import bill text from a local file."""
    congress, bill_type, bill_number = parse_bill_id(bill_id)

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    result = {
        "congress": congress,
        "bill_type": bill_type,
        "bill_number": bill_number,
        "title": f"{bill_type.upper()} {bill_number} ({congress}th Congress)",
        "text": text,
        "source": "local_file",
    }

    if db:
        bill_db_id = db.upsert_bill(
            congress,
            bill_type,
            bill_number,
            title=result["title"],
            source="local_file",
        )
        version_id = db.upsert_version(
            bill_db_id,
            "local",
            version_name="Local Import",
            raw_text=text,
        )
        result["db_id"] = bill_db_id
        result["version_id"] = version_id

    return result


def _extract_sponsors(bill_data: dict) -> str:
    """Extract sponsor names from bill data."""
    sponsors = []
    for sponsor in bill_data.get("sponsors", []):
        name = sponsor.get("fullName") or sponsor.get("name", "")
        if name:
            sponsors.append(name)
    return ", ".join(sponsors)
