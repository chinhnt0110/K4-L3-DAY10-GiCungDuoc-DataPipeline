import json
import sys
from datetime import datetime, timezone

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import pandas as pd

from core.config import load_settings
from core.utils import read_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex


def main() -> None:
    """End-to-end corruption, evaluation, idempotent repair, and comparison flow."""
    # 1. Load settings & baseline metrics & clean dataset
    print("\n--- [1/8] Load Settings, Baseline Metrics & Clean Dataset ---")
    settings = load_settings()
    if not settings.paths.baseline_metrics.exists() or not settings.paths.clean_json.exists():
        raise RuntimeError("Baseline metrics or clean dataset missing. Please run script/run_phase1.py first.")

    baseline_metrics = read_json(settings.paths.baseline_metrics)
    clean_df = pd.read_json(settings.paths.clean_json)
    print(f"✅ Baseline Metrics đã tải (samples={baseline_metrics.get('samples')}).")
    print(f"✅ Clean Dataset đã tải ({len(clean_df)} dòng).")

    # 2. Tạo corrupted dataframe
    print("\n--- [2/8] Tiêm 6 Kịch Bản Lỗi Dữ Liệu (Data Corruption Suite) ---")
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    print(f"✅ Đã tạo dataframe hỏng ({len(corrupted_df)} dòng).")
    print(f"   Corruption log lưu tại: {settings.paths.corruption_log}")

    # 3. Lưu corrupted artifacts
    print("\n--- [3/8] Lưu Corrupted CSV và JSON ---")
    settings.paths.corrupted_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    corrupted_df.to_csv(settings.paths.corrupted_clean_csv, index=False)
    corrupted_df.to_json(settings.paths.corrupted_clean_json, orient="records", indent=2, force_ascii=False)
    print(f"✅ Đã lưu vào:\n   - {settings.paths.corrupted_clean_csv}\n   - {settings.paths.corrupted_clean_json}")

    # 4. Rebuild index và evaluate trên dữ liệu corrupted
    print("\n--- [4/8] Build Chroma Index & Đánh Giá Hiệu Năng Trên Dữ Liệu Bẩn ---")
    corrupted_index = LocalEmbeddingIndex.build(
        df=corrupted_df,
        settings=settings,
        embeddings_output_path=settings.paths.corrupted_embeddings_json,
    )
    corrupted_eval = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    print("📊 Kết quả Corrupted Metrics (Silent Failure):")
    print(json.dumps(corrupted_eval.summary, indent=2))

    # 5. Chạy quality checks/freshness trên corrupted data
    print("\n--- [5/8] Kiểm Định Chất Lượng & Freshness Trên Dữ Liệu Bẩn ---")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness = build_freshness_report(
        corrupted_df,
        settings,
        settings.paths.quality_dir / "freshness_report_corrupted.json",
    )
    print(f"⚠️ Quality check status: {corrupted_quality.get('success')} (Kỳ vọng: False)")
    print(f"⚠️ Freshness SLA status: {corrupted_freshness.get('is_fresh')} (Kỳ vọng: False)")

    # 6. Repair lại từ raw records (Idempotent Repair)
    print("\n--- [6/8] Tự Động Phục Hồi Dữ Liệu Từ Raw Backup (Idempotent Repair) ---")
    if settings.paths.raw_records_json.exists():
        raw_records = load_raw_records(settings.paths.raw_records_json)
    else:
        raw_records = fetch_source_records(settings)
    
    run_date = datetime.now(timezone.utc)
    repaired_df = build_clean_dataframe(raw_records, run_date)
    settings.paths.repaired_clean_csv.parent.mkdir(parents=True, exist_ok=True)
    repaired_df.to_csv(settings.paths.repaired_clean_csv, index=False)
    repaired_df.to_json(settings.paths.repaired_clean_json, orient="records", indent=2, force_ascii=False)
    print(f"✅ Đã phục hồi thành công {len(repaired_df)} dòng dữ liệu từ raw backup.")
    print(f"✅ Đã lưu vào:\n   - {settings.paths.repaired_clean_csv}\n   - {settings.paths.repaired_clean_json}")

    # 7. Evaluate repaired dataset
    print("\n--- [7/8] Build Chroma Index & Đánh Giá Sau Phục Hồi ---")
    repaired_index = LocalEmbeddingIndex.build(
        df=repaired_df,
        settings=settings,
        embeddings_output_path=settings.paths.repaired_embeddings_json,
    )
    repaired_eval = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness = build_freshness_report(
        repaired_df,
        settings,
        settings.paths.quality_dir / "freshness_report_repaired.json",
    )
    print("📊 Kết quả Repaired Metrics:")
    print(json.dumps(repaired_eval.summary, indent=2))
    print(f"✅ Repaired Quality check: {repaired_quality.get('success')} (Kỳ vọng: True)")
    print(f"✅ Repaired Freshness SLA: {repaired_freshness.get('is_fresh')} (Kỳ vọng: True)")

    # 8. Tạo comparison report
    print("\n--- [8/8] Xuất Báo Cáo Đối Chiếu 3 Trạng Thái (Baseline vs Corrupted vs Repaired) ---")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_eval.summary,
        repaired_metrics=repaired_eval.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )


if __name__ == "__main__":
    main()

