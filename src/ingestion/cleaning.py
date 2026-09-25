from __future__ import annotations

from datetime import datetime

import pandas as pd

from ingestion.crossref import PaperRecord
from dataclasses import asdict


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """TODO(student): clean raw records thanh dataframe san sang de embed.

    Pseudo-code:
    1. Normalize title, summary, authors, categories.
    2. Parse published/updated date.
    3. Tinh age_days.
    4. Tao cot helper:
       - authors_joined
       - categories_joined
       - summary_chars
       - text_for_embedding
    5. Drop duplicates va filter row xau.
    6. Sort dataframe va return.
    """
    # Normalize title, summary, authors, categories
    df = pd.DataFrame([asdict(r) for r in records])
    df["title"] = df["title"].str.strip()
    df["summary"] = df["summary"].str.strip()
    df["authors"] = df["authors"].apply(lambda x: ", ".join(x))
    df["categories"] = df["categories"].apply(lambda x: ", ".join(x))
    
    # Parse published/updated date
    df["published"] = pd.to_datetime(df["published"], utc=True)
    df["updated"] = pd.to_datetime(df["updated"], utc=True)
    
    # Calculate age_days
    df["age_days"] = (run_date - df["published"]).dt.days
    
    # Create helper columns
    df["authors_joined"] = df["authors"]
    df["categories_joined"] = df["categories"]
    df["summary_chars"] = df["summary"].str.len()
    df["text_for_embedding"] = (
        "Title: " + df["title"] + "\n"
        + "Authors: " + df["authors_joined"] + "\n"
        + "Published: " + df["published"].astype(str) + "\n"
        + "Categories: " + df["categories_joined"] + "\n"
        + "Summary: " + df["summary"]
    )

    
    # Drop duplicates and filter bad rows
    df = df.drop_duplicates(subset=["paper_id"])
    df = df[df["summary_chars"] > 0]
    
    # Sort dataframe and return
    df = df.sort_values(by="published", ascending=False)
      # Chuyển Timestamp về chuỗi YYYY-MM-DD để ChromaDB chấp nhận metadata
    df["published"] = df["published"].dt.strftime("%Y-%m-%d")
    df["updated"] = df["updated"].dt.strftime("%Y-%m-%d")

    return df
    

    
    #  raise NotImplementedError("Student task: implement cleaning pipeline.")
