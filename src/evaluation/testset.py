from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path: Path | str | None = None) -> list[dict[str, Any]]:
    """Generate standardized benchmark evaluation set of 10 questions across 4 categories."""
    if len(df) < 5:
        raise ValueError(f"Dataframe must have at least 5 records to build test set, got {len(df)}")

    target_count = 10
    records = df.to_dict(orient="records")

    question_types = [
        "summary",
        "authors",
        "date",
        "categories",
        "summary",
        "authors",
        "date",
        "categories",
        "summary",
        "authors",
    ]

    test_set: list[dict[str, Any]] = []

    for idx, q_type in enumerate(question_types):
        record_idx = idx % len(records)
        row = records[record_idx]

        paper_id = str(row.get("paper_id", "")).strip()
        title = str(row.get("title", "")).strip()
        summary = str(row.get("summary", "")).strip()
        published = str(row.get("published", "")).strip()

        authors_val = str(row.get("authors_joined", "")).strip()
        if not authors_val:
            raw_authors = row.get("authors", [])
            authors_val = ", ".join(raw_authors) if isinstance(raw_authors, list) else str(raw_authors)

        categories_val = str(row.get("categories_joined", "")).strip()
        if not categories_val:
            raw_categories = row.get("categories", [])
            categories_val = ", ".join(raw_categories) if isinstance(raw_categories, list) else str(raw_categories)

        if q_type == "summary":
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = first_sentence(summary)
        elif q_type == "authors":
            question = f"Who authored the paper '{title}'?"
            ground_truth = authors_val
        elif q_type == "date":
            question = f"When was the paper '{title}' published?"
            ground_truth = published
        else:  # categories
            question = f"What categories does the paper '{title}' belong to?"
            ground_truth = categories_val

        test_set.append(
            {
                "id": f"eval_{idx + 1:03d}",
                "question_type": q_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            }
        )

    if output_path is not None:
        write_json(Path(output_path), test_set)

    return test_set
