import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path | str) -> pd.DataFrame:
    """Simulate realistic data corruption across 6 key scenarios.

    1. Drop latest records: Drop ~20% of the freshest records.
    2. Blank summary: Set summary to empty string on selected rows.
    3. Inject noise: Inject garbage characters into summaries.
    4. Truncate title: Truncate titles to < 8 characters.
    5. Stale date: Roll back publication dates by 365 days (violating Freshness SLA).
    6. Duplicate rows: Re-inject duplicate rows to violate uniqueness.
    7. Rebuild `text_for_embedding` and helper fields.
    8. Write corruption log to output_log_path.
    """
    corrupted = df.copy()
    initial_count = len(corrupted)
    log_scenarios: list[dict[str, Any]] = []

    # 1. Drop latest records (20% of newest records)
    n_drop = max(1, int(initial_count * 0.20))
    dropped_records = corrupted.iloc[:n_drop]
    dropped_paper_ids = dropped_records["paper_id"].tolist()
    corrupted = corrupted.iloc[n_drop:].copy().reset_index(drop=True)
    log_scenarios.append({
        "type": "drop_latest_records",
        "description": f"Dropped {n_drop} latest records (~20%) to simulate ingestion freshness loss.",
        "affected_count": n_drop,
        "affected_paper_ids": dropped_paper_ids,
    })

    # 2. Blank summary on selected rows
    blank_indices = [0, 1] if len(corrupted) >= 2 else [0]
    blank_paper_ids = []
    for idx in blank_indices:
        corrupted.at[idx, "summary"] = ""
        blank_paper_ids.append(corrupted.at[idx, "paper_id"])
    log_scenarios.append({
        "type": "blank_summary",
        "description": "Cleared summary text to empty string (simulating scraper failure).",
        "affected_count": len(blank_paper_ids),
        "affected_paper_ids": blank_paper_ids,
    })

    # 3. Inject noise into summary on selected rows
    noise_indices = [2, 3] if len(corrupted) >= 4 else []
    noise_paper_ids = []
    noise_str = " \n[###_CORRUPTED_NOISE_$$$### RANDOM_NOISE_@@@###_JUNK_DATA_TOKEN_FAILURE]"
    for idx in noise_indices:
        corrupted.at[idx, "summary"] = str(corrupted.at[idx, "summary"]) + noise_str
        noise_paper_ids.append(corrupted.at[idx, "paper_id"])
    log_scenarios.append({
        "type": "inject_noise",
        "description": "Injected random garbage/noise tokens into summary text.",
        "affected_count": len(noise_paper_ids),
        "affected_paper_ids": noise_paper_ids,
    })

    # 4. Truncate title to < 8 chars
    truncate_indices = [4, 5] if len(corrupted) >= 6 else []
    truncated_paper_ids = []
    for idx in truncate_indices:
        corrupted.at[idx, "title"] = str(corrupted.at[idx, "title"])[:5]
        truncated_paper_ids.append(corrupted.at[idx, "paper_id"])
    log_scenarios.append({
        "type": "truncate_title",
        "description": "Truncated title to < 8 characters to cause title lookup failure.",
        "affected_count": len(truncated_paper_ids),
        "affected_paper_ids": truncated_paper_ids,
    })

    # 5. Stale date: Roll back publication dates by 365 days on records to violate Freshness SLA (>25% stale)
    stale_count = max(6, int(len(corrupted) * 0.40))
    stale_indices = list(range(len(corrupted) - stale_count, len(corrupted)))
    stale_paper_ids = []
    for idx in stale_indices:
        current_pub = pd.to_datetime(corrupted.at[idx, "published"])
        new_pub = current_pub - pd.Timedelta(days=365)
        corrupted.at[idx, "published"] = new_pub.strftime("%Y-%m-%d")
        corrupted.at[idx, "age_days"] = int(corrupted.at[idx, "age_days"]) + 365
        stale_paper_ids.append(corrupted.at[idx, "paper_id"])
    log_scenarios.append({
        "type": "stale_date",
        "description": "Pushed published date back by 365 days, violating Freshness SLA.",
        "affected_count": len(stale_paper_ids),
        "affected_paper_ids": stale_paper_ids,
    })

    # 6. Duplicate rows: re-insert 2 rows to cause duplicate paper_id violation
    dup_indices = [len(corrupted) - 2, len(corrupted) - 1] if len(corrupted) >= 2 else [0]
    duplicate_rows = corrupted.iloc[dup_indices].copy()
    duplicate_paper_ids = duplicate_rows["paper_id"].tolist()
    corrupted = pd.concat([corrupted, duplicate_rows], ignore_index=True)
    log_scenarios.append({
        "type": "duplicate_rows",
        "description": "Duplicated rows to simulate duplicate ingestion and break uniqueness constraint.",
        "affected_count": len(duplicate_paper_ids),
        "affected_paper_ids": duplicate_paper_ids,
    })

    # 7. Rebuild summary_chars and text_for_embedding
    corrupted["summary_chars"] = corrupted["summary"].astype(str).str.len()
    corrupted["text_for_embedding"] = (
        "Title: " + corrupted["title"].astype(str) + "\n"
        + "Authors: " + corrupted["authors_joined"].astype(str) + "\n"
        + "Published: " + corrupted["published"].astype(str) + "\n"
        + "Categories: " + corrupted["categories_joined"].astype(str) + "\n"
        + "Summary: " + corrupted["summary"].astype(str)
    )

    # 8. Write corruption log to output_log_path
    log_data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "original_rows": initial_count,
        "corrupted_rows": len(corrupted),
        "scenarios": log_scenarios,
    }
    output_path = Path(output_log_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=2)

    return corrupted

