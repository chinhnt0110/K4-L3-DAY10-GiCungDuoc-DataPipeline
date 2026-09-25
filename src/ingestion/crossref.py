from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path

from core.config import Settings
import requests
import json

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


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """TODO(student): parse Crossref payload thanh list PaperRecord.

    Pseudo-code:
    1. Duyet `payload["message"]["items"]`.
    2. Lay DOI, title, abstract, authors, subject, dates, URLs.
    3. Chuan hoa text va bo record khong hop le.
    4. Tra ve list `PaperRecord`.
    """
    records = []
    for item in payload["message"]["items"]:
        # Lay DOI
        paper_id = item.get("DOI")

        # Lay title
        title = item.get("title", [""])[0]

        # Lay abstract
        abstract = item.get("abstract", "")
        if abstract.startswith("<jats:title>") and abstract.endswith("</jats:title>"):
            abstract = abstract[len("<jats:title>"):-len("</jats:title>")]

        # Lay authors
        authors = [author.get("name", "") for author in item.get("author", [])]

        # Lay categories
        categories = [subject.get("id", "") for subject in item.get("subject", [])]

        # Lay primary category
        primary_category = categories[0] if categories else ""

        # Lay dates
        published = item.get("created", {}).get("date-parts", [[]])[0]
        updated = item.get("updated", {}).get("date-parts", [[]])[0]

        # Lay URLs
        abs_url = item.get("link", [{}])[0].get("URL", "")
        pdf_url = ""
        for link in item.get("link", []):
            if link.get("content-type", "") == "application/pdf":
                pdf_url = link.get("URL", "")
                break

        # Lay comment
        comment = item.get("comment", "")

        # Create PaperRecord
        paper_record = PaperRecord(
            paper_id=paper_id,
            title=title,
            summary=abstract,
            authors=authors,
            categories=categories,
            primary_category=primary_category,
            published=published,
            updated=updated,
            abs_url=abs_url,
            pdf_url=pdf_url,
            comment=comment,
        )

        # Append to list
        records.append(paper_record)
    return records
    # raise NotImplementedError("Student task: implement Crossref payload parsing.")


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """TODO(student): goi source API, luu raw response, parse thanh records.

    Pseudo-code:
    1. Tao params tu `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    2. Goi API voi retry cho cac status code nhu 429/503.
    3. Luu raw response vao `settings.paths.raw_api_response`.
    4. Parse payload bang `parse_crossref_payload`.
    5. Luu records vao `settings.paths.raw_records_json`.
    """
    # Tao params tu `settings.source_query`, `settings.source_filter`, `settings.max_results`.
    params = {
        "query": settings.source_query,
        "filter": settings.source_filter,
        "rows": settings.max_results,
    }
    url = "https://api.crossref.org/works"
    resp = requests.get(url, params=params)
    # Goi API voi retry cho cac status code nhu 429/503

    # Luu raw response vao `settings.paths.raw_api_response`
    with open(settings.paths.raw_api_response, "w", encoding="utf-8") as f:
        json.dump(resp.json(), f, ensure_ascii=False, indent=2)
    
    # Parse payload bang `parse_crossref_payload`
    records = parse_crossref_payload(resp.json())

    # Luu records vao `settings.paths.raw_records_json`
    with open(settings.paths.raw_records_json, "w", encoding="utf-8") as f:
        json.dump([asdict(r) for r in records], f, ensure_ascii=False, indent=2)
    return records
    # raise NotImplementedError("Student task: implement source fetching.")


def load_raw_records(path: Path) -> list[PaperRecord]:
    """TODO(student): doc JSON snapshot va map thanh `PaperRecord`."""
    with open(path, "r", encoding="utf-8") as f:
        return [PaperRecord(**r) for r in json.load(f)]
    # raise NotImplementedError("Student task: implement raw record loading.")
