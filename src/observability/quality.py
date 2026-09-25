from __future__ import annotations

from typing import Any
from pathlib import Path
import pandas as pd
from datetime import datetime
from core.config import Settings
import json

def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Execute Data Quality checks using Great Expectations 1.x (Ephemeral Context) with safe fallback.
    
    4 Hàng rào kiểm định (Expectations):
    1. ExpectTableRowCountToBeBetween: 5 <= row_count <= 5000
    2. ExpectColumnValuesToNotBeNull: paper_id, title, text_for_embedding
    3. ExpectColumnValuesToBeUnique: paper_id
    4. ExpectColumnValueLengthsToBeBetween: summary >= 20 ký tự
    """
    row_count = len(df)
    run_date = datetime.now()
    
    # 1. Thử thực thi bằng Great Expectations 1.x Fluent API
    try:
        import great_expectations as gx
        import great_expectations.expectations as gxe

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
        suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=20))

        validation_result = batch.validate(suite)
        success = bool(validation_result.success)

        expectation_summaries = []
        for item in validation_result.results:
            exp_type = item.expectation_config.type if hasattr(item, "expectation_config") else "unknown"
            expectation_summaries.append({
                "expectation": exp_type,
                "success": bool(item.success),
                "result": item.result if hasattr(item, "result") else {},
            })

        quality_report = {
            "run_date": run_date.isoformat(),
            "total_rows": row_count,
            "success": success,
            "engine": "Great Expectations 1.x (Fluent Ephemeral)",
            "expectations": expectation_summaries,
            "paper_id_not_null": bool(df["paper_id"].notna().all()),
            "paper_id_unique": bool(df["paper_id"].is_unique),
            "title_not_null": bool(df["title"].notna().all()),
            "summary_length_ok": bool((df["summary"].astype(str).str.len() >= 20).all()),
            "freshness_ok": bool((df["age_days"] <= settings.freshness_threshold_days).all()),
        }
    except Exception:
        # 2. Fallback assertions tính toán tương đương nếu môi trường chưa cài GX
        paper_id_not_null = bool(df["paper_id"].notna().all() and (df["paper_id"].astype(str).str.strip() != "").all())
        paper_id_unique = bool(df["paper_id"].is_unique)
        title_not_null = bool(df["title"].notna().all() and (df["title"].astype(str).str.strip() != "").all())
        summary_length_ok = bool((df["summary"].astype(str).str.len() >= 20).all())
        freshness_ok = bool((df["age_days"] <= settings.freshness_threshold_days).all())

        all_passed = bool(
            row_count >= 5
            and paper_id_not_null
            and paper_id_unique
            and title_not_null
            and summary_length_ok
        )

        quality_report = {
            "run_date": run_date.isoformat(),
            "total_rows": row_count,
            "success": all_passed,
            "engine": "Pandas Assertions Fallback",
            "paper_id_not_null": paper_id_not_null,
            "paper_id_unique": paper_id_unique,
            "title_not_null": title_not_null,
            "summary_length_ok": summary_length_ok,
            "freshness_ok": freshness_ok,
        }

    # Ghi file với default=str theo chuẩn config (baseline_quality_report.json) và backward-compatible
    std_report_path = getattr(settings.paths, f"{report_name}_quality_report", settings.paths.quality_dir / f"{report_name}_quality_report.json")
    compat_report_path = settings.paths.quality_dir / f"quality_report_{report_name}.json"
    
    std_report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(std_report_path, "w", encoding="utf-8") as f:
        json.dump(quality_report, f, ensure_ascii=False, indent=2, default=str)
    with open(compat_report_path, "w", encoding="utf-8") as f:
        json.dump(quality_report, f, ensure_ascii=False, indent=2, default=str)

    return quality_report



def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Tong hop freshness report theo SLA."""
    report_path = Path(report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    latest_published = str(df["published"].max())
    oldest_published = str(df["published"].min())
    total_rows = len(df)
    
    threshold = settings.freshness_threshold_days # 180 ngay
    stale_rows = int((df["age_days"] > threshold).sum())
    
    # SLA: Fresh khi tỷ lệ bài cũ <= 25% (theo đề bài)
    stale_ratio = stale_rows / total_rows if total_rows > 0 else 0.0
    is_fresh = bool(stale_ratio <= 0.25)

    max_age_days = int(df["age_days"].max()) if total_rows > 0 else 0
    avg_age_days = round(float(df["age_days"].mean()), 1) if total_rows > 0 else 0.0

    report = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "total_rows": total_rows,
        "stale_rows": stale_rows,
        "stale_ratio": round(stale_ratio, 4),
        "sla_days": threshold,             
        "max_age_days": max_age_days,       
        "avg_age_days": avg_age_days,       
        "is_fresh": is_fresh,               
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    return report
