from __future__ import annotations

from dataclasses import asdict, dataclass
import logging
from pathlib import Path
import re
from typing import Any
import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_text(raw: Any) -> str:
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    cleaned = re.sub(r"<[^>]+>", " ", str(raw or ""))
    return normalize_whitespace(cleaned)


def _format_authors(author_list: list[dict[str, Any]]) -> list[str]:
    authors: list[str] = []
    for item in author_list:
        given = item.get("given", "").strip()
        family = item.get("family", "").strip()
        name = f"{given} {family}".strip() if given or family else item.get("name", "").strip()
        if name:
            authors.append(name)
    return authors


def _format_date(date_obj: dict[str, Any] | None) -> str:
    if not date_obj or not isinstance(date_obj, dict):
        return ""
    date_parts = date_obj.get("date-parts", [[]])
    if date_parts and date_parts[0]:
        parts = date_parts[0]
        if len(parts) >= 3:
            return f"{int(parts[0]):04d}-{int(parts[1]):02d}-{int(parts[2]):02d}"
        if len(parts) == 2:
            return f"{int(parts[0]):04d}-{int(parts[1]):02d}-01"
        if len(parts) == 1:
            return f"{int(parts[0]):04d}-01-01"
    return ""


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref API payload into a list of PaperRecord instances."""
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []
    for item in items:
        paper_id = str(item.get("DOI") or item.get("id") or "").strip()
        title = _clean_text(item.get("title", ""))
        summary = _clean_text(item.get("abstract", ""))
        if not summary:
            summary = title

        authors = _format_authors(item.get("author", []))
        categories = [str(cat) for cat in item.get("subject", []) if cat]
        if not categories:
            categories = ["Artificial Intelligence"]
        primary_category = categories[0]

        published = _format_date(item.get("published") or item.get("published-print") or item.get("published-online"))
        if not published:
            created_dt = item.get("created", {}).get("date-time", "")
            published = created_dt[:10] if created_dt else "2026-01-01"

        updated = _format_date(item.get("updated")) or published
        abs_url = str(item.get("URL") or f"https://doi.org/{paper_id}")
        pdf_url = abs_url
        comment = f"Crossref record {paper_id}"

        if paper_id and title:
            records.append(
                PaperRecord(
                    paper_id=paper_id,
                    title=title,
                    summary=summary,
                    authors=authors,
                    categories=categories,
                    primary_category=primary_category,
                    published=published,
                    updated=updated,
                    abs_url=abs_url,
                    pdf_url=pdf_url,
                    comment=comment,
                )
            )
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Load JSON snapshot and map into list of PaperRecord."""
    data = read_json(path)
    if isinstance(data, dict) and "message" in data:
        return parse_crossref_payload(data)

    records: list[PaperRecord] = []
    for item in data:
        records.append(
            PaperRecord(
                paper_id=str(item["paper_id"]),
                title=str(item["title"]),
                summary=str(item["summary"]),
                authors=list(item.get("authors", [])),
                categories=list(item.get("categories", [])),
                primary_category=str(item.get("primary_category", "")),
                published=str(item.get("published", "")),
                updated=str(item.get("updated", "")),
                abs_url=str(item.get("abs_url", "")),
                pdf_url=str(item.get("pdf_url", "")),
                comment=str(item.get("comment", "")),
            )
        )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch metadata from Crossref API with retry and offline local snapshot fallback."""
    raw_api_path = settings.paths.raw_api_response
    raw_records_path = settings.paths.raw_records_json

    if not settings.refresh_source and raw_records_path.exists():
        try:
            records = load_raw_records(raw_records_path)
            if records:
                return records
        except Exception as exc:
            logger.warning("Failed to load existing raw records, will attempt fetch or fallback: %s", exc)

    records: list[PaperRecord] = []
    payload: dict[str, Any] | None = None

    if settings.refresh_source or not raw_api_path.exists():
        api_url = "https://api.crossref.org/works"
        params: dict[str, Any] = {
            "query": settings.source_query,
            "rows": settings.max_results,
        }
        if settings.source_filter:
            params["filter"] = settings.source_filter

        headers = {
            "User-Agent": "VinUni-AI-Engineer-Lab/1.0 (mailto:student@vinuni.edu.vn)"
        }

        for attempt in range(1, 4):
            try:
                response = requests.get(api_url, params=params, headers=headers, timeout=15)
                if response.status_code == 200:
                    payload = response.json()
                    parsed = parse_crossref_payload(payload)
                    if len(parsed) >= 5:
                        records = parsed[: settings.max_results]
                        write_json(raw_api_path, payload)
                        write_json(raw_records_path, [asdict(r) for r in records])
                        logger.info("Successfully fetched %d records from Crossref API", len(records))
                        return records
                elif response.status_code in {429, 503}:
                    logger.warning("Crossref API rate limit (status %d), attempt %d/3", response.status_code, attempt)
            except Exception as exc:
                logger.warning("Crossref API request error on attempt %d/3: %s", attempt, exc)

    if raw_api_path.exists():
        try:
            payload = read_json(raw_api_path)
            records = parse_crossref_payload(payload)
        except Exception as exc:
            logger.warning("Failed to parse raw_api_response snapshot: %s", exc)

    if not records and raw_records_path.exists():
        records = load_raw_records(raw_records_path)

    if records:
        write_json(raw_records_path, [asdict(r) for r in records])
        return records

    raise RuntimeError("Unable to load records from Crossref API or offline snapshots.")
