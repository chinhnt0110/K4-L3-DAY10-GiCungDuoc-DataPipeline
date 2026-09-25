from __future__ import annotations

from typing import Any
from pathlib import Path
import pandas as pd
from datetime import datetime
from core.config import Settings
import json

def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Tao bo data quality checks."""
    row_count = len(df)
    
    # Ép kiểu bool thuần túy cho tất cả các điều kiện:
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

    run_date = datetime.now()
    quality_report = {
        "run_date": run_date.isoformat(),
        "total_rows": row_count,
        "success": all_passed,  # 👈 Có key "success"
        "paper_id_not_null": paper_id_not_null,
        "paper_id_unique": paper_id_unique,
        "title_not_null": title_not_null,
        "summary_length_ok": summary_length_ok,
        "freshness_ok": freshness_ok,
    }

    # Ghi file với default=str
    report_path = settings.paths.quality_dir / f"quality_report_{report_name}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
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
