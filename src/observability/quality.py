from __future__ import annotations

from pathlib import Path
from typing import Any

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

from core.config import Settings
from core.utils import now_utc, write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Execute Great Expectations 1.x quality checks on the dataframe.

    Checks:
    1. Table row count is between 5 and 5000.
    2. Crucial columns (paper_id, title, text_for_embedding) are not null.
    3. paper_id is unique.
    4. summary length >= 30 characters.
    """
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name=f"papers_source_{report_name}")
    data_asset = data_source.add_dataframe_asset(name=f"papers_asset_{report_name}")
    batch_def = data_asset.add_batch_definition_whole_dataframe(f"papers_batch_{report_name}")
    batch = batch_def.get_batch(batch_parameters={"dataframe": df})

    suite = context.suites.add(gx.ExpectationSuite(name=f"papers_suite_{report_name}"))
    suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="title"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="text_for_embedding"))
    suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30))

    validation_result = batch.validate(suite)

    expectation_summaries: list[dict[str, Any]] = []
    for item in validation_result.results:
        exp_type = item.expectation_config.type if hasattr(item, "expectation_config") else "unknown"
        expectation_summaries.append(
            {
                "expectation": exp_type,
                "success": bool(item.success),
                "result": item.result if hasattr(item, "result") else {},
            }
        )

    output_path: Path
    if report_name == "baseline":
        output_path = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        output_path = settings.paths.corrupted_quality_report
    else:
        output_path = settings.paths.quality_dir / f"{report_name}_quality_report.json"

    freshness_summary = build_freshness_report(df, settings, settings.paths.freshness_report)

    report_payload: dict[str, Any] = {
        "report_name": report_name,
        "timestamp": now_utc().isoformat(),
        "total_rows": len(df),
        "success": bool(validation_result.success),
        "expectations": expectation_summaries,
        "freshness": freshness_summary,
    }

    write_json(output_path, report_payload)
    return report_payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path | str | None = None) -> dict[str, Any]:
    """Calculate and summarize freshness metrics based on age_days and publication dates."""
    total_rows = len(df)
    latest_published = ""
    oldest_published = ""
    if "published" in df.columns and not df["published"].dropna().empty:
        latest_published = str(df["published"].dropna().max())
        oldest_published = str(df["published"].dropna().min())

    threshold = settings.freshness_threshold_days
    if "age_days" in df.columns and total_rows > 0:
        stale_rows = int((df["age_days"] > threshold).sum())
    else:
        stale_rows = 0

    stale_ratio = float(stale_rows / total_rows) if total_rows > 0 else 0.0
    is_fresh = stale_ratio <= 0.25

    payload: dict[str, Any] = {
        "timestamp": now_utc().isoformat(),
        "total_rows": total_rows,
        "threshold_days": threshold,
        "stale_rows": stale_rows,
        "stale_ratio": round(stale_ratio, 4),
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "is_fresh": is_fresh,
    }

    target_path = Path(report_path) if report_path else settings.paths.freshness_report
    write_json(target_path, payload)
    return payload
