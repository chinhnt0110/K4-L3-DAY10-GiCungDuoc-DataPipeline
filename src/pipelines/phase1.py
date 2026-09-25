from __future__ import annotations
import json
from datetime import datetime, timezone
from pathlib import Path
from core.config import load_settings
from ingestion.crossref import fetch_source_records, load_raw_records
from ingestion.cleaning import build_clean_dataframe
from retrieval.index import LocalEmbeddingIndex
from evaluation.testset import build_test_set
from evaluation.metrics import evaluate_pipeline
from observability.quality import run_data_quality_checks, build_freshness_report
from observability.reporting import generate_phase1_report
from retrieval.agent import build_agent, run_agent_question
from datetime import datetime


def main() -> None:
    """TODO(student): xay dung baseline pipeline end-to-end.

    Pseudo-code:
    1. Load settings.
    2. Load hoac fetch raw records.
    3. Clean data.
    4. Save clean CSV/JSON.
    5. Build Chroma index.
    6. Tao hoac load evaluation set.
    7. Evaluate.
    8. Run quality checks va freshness report.
    9. Tao markdown report.
    10. Co the demo agent tren vai sample question.
    """
    # 1. Load settings
    print("\n--- [1/10] Load settings ---")
    settings = load_settings()
    
    # 2. Load hoac fetch raw records
    print("\n--- [2/10] Load hoặc Fetch raw records ---")
    if not settings.refresh_source and settings.paths.raw_records_json.exists():
        records = load_raw_records(settings.paths.raw_records_json)
    else:
        records = fetch_source_records(settings)
    print(f"✅ Đã tải {len(records)} bản ghi thô (raw records).")

    # 3. Clean data
    print("\n--- [3/10] Clean dữ liệu ---")
    run_date = datetime.now(timezone.utc)
    clean_df = build_clean_dataframe(records, run_date)
    print(f"✅ Clean thành công {len(clean_df)} dòng dữ liệu.")

    # 4. Save clean CSV/JSON
    print("\n--- [4/10] Lưu file clean CSV và JSON ---")
    settings.paths.clean_csv.parent.mkdir(parents=True, exist_ok=True)
    clean_df.to_csv(settings.paths.clean_csv, index=False)
    clean_df.to_json(settings.paths.clean_json, orient="records", indent=2, force_ascii=False)
    print(f"✅ Đã lưu vào:\n   - {settings.paths.clean_csv}\n   - {settings.paths.clean_json}")
    
    # 5. Build Chroma index
    print("\n--- [5/10] Build Chroma Index ---")
    index = LocalEmbeddingIndex.build(
        df=clean_df,
        settings=settings,
        embeddings_output_path=settings.paths.embeddings_json,
    )    
    print(f"✅ Đã index {len(clean_df)} documents vào ChromaDB thành công.")
    
    # 6. Tao hoac load evaluation set
    print("\n--- [6/10] Tạo hoặc Load Evaluation Set ---")
    settings.paths.eval_testset.parent.mkdir(parents=True, exist_ok=True)
    if settings.refresh_test_set or not settings.paths.eval_testset.exists():
        test_set = build_test_set(clean_df, output_path=settings.paths.eval_testset)
    else:
        with open(settings.paths.eval_testset, "r", encoding="utf-8") as f:
            test_set = json.load(f)
    print(f"✅ Test set đã sẵn sàng với {len(test_set)} câu hỏi.")

    # 7. Evaluate
    print("\n--- [7/10] Đánh giá pipeline (Evaluation) ---")
    eval_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )    
    print("📊 Kết quả Baseline Metrics:")
    print(json.dumps(eval_bundle.summary, indent=2))

    # 8. Run quality checks va freshness report
    print("\n--- [8/10] Kiểm định chất lượng Data Quality & Freshness SLA ---")
    quality_report = run_data_quality_checks(clean_df, settings, "baseline")
    freshness_report = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    print(f"✅ Quality check status: {quality_report.get('success')}")
    print(f"✅ Freshness SLA status: {freshness_report.get('is_fresh')}")
    
    # 9. Tao markdown report
    print("\n--- [9/10] Xuất báo cáo Phase 1 Markdown Report ---")
    source_summary = {
        "raw_records": len(records),
        "clean_rows": len(clean_df),
        "source_api": settings.source_api,
    }
    settings.paths.baseline_report.parent.mkdir(parents=True, exist_ok=True)
    try:
        generate_phase1_report(
            report_path=settings.paths.baseline_report,
            source_summary=source_summary,
            metrics=eval_bundle.summary,
            quality=quality_report,
            freshness=freshness_report,
        )
        print(f"✅ Đã xuất báo cáo tại: {settings.paths.baseline_report}")
    except NotImplementedError:
        print("⚠️ generate_phase1_report chưa hoàn thiện trong reporting.py. Đang tạm bỏ qua.")
    

    # 10. Demo agent tren vai sample question
    print("\n--- [10/10] Demo Agent trả lời câu hỏi mẫu ---")
    try:
        agent = build_agent(settings, index)
        sample_questions = [
            "What is the summary of the paper about LLM risks in dairy industry?",
            "Who authored the paper 'Advanced Perspectives on Multi-Agent Consensus for High-Stakes Fact Verification'?",
        ]
        demo_results = []
        for q in sample_questions:
            print(f"🔹 Q: {q}")
            ans = run_agent_question(agent, q)
            print(f"🔸 A: {ans}\n")
            demo_results.append({"question": q, "answer": ans})
        settings.paths.demo_answers.parent.mkdir(parents=True, exist_ok=True)
        with open(settings.paths.demo_answers, "w", encoding="utf-8") as f:
            json.dump(demo_results, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"ℹ️ Demo agent tạm dừng (cần API key hợp lệ): {e}")
    # raise NotImplementedError("Student task: implement phase1 pipeline.")

if __name__ == "__main__":
    main()