# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4-L3A             |
| Tên nhóm         | GiCungDuoc    |
| Repository         | https://github.com/chinhnt0110/K4-L3-DAY10-GiCungDuoc-DataPipeline |
| Ngày hoàn thành | 2026-09-26               |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Vũ Minh Hiếu | 2A202602779 | Corruption, Evaluation & Repair Lead | `src/ingestion/corruption.py`, `src/pipelines/corruption_flow.py`, `script/run_corruption_flow.py`, `data/reports/corruption_report.md` |
| 2 | Nguyễn Thị Chinh | 2A202602876 | Pipeline Orchestration & Data Observability | `core/`, `script/run_phase1.py`, `src/pipelines/phase1.py`, `src/ingestion/crossref.py`, `src/ingestion/cleaning.py`, `src/observability/quality.py`, `data/reports/phase1_report.md` |

---

## 2. Tóm tắt kết quả

Nhóm đã xây dựng hoàn chỉnh và kiểm thử thành công hệ thống **Data Pipeline & Data Observability** end-to-end cho mô hình RAG Agent theo chuẩn 2 Pha:

1. **Pha 1 (Baseline Pipeline):** Thu thập 24 bản ghi học thuật từ Crossref REST API (có fallback local), làm sạch và chuẩn hóa schema, lưu trữ bản sao gốc (Raw Preservation) tại `data/raw/` và dữ liệu sạch tại `data/clean/`. Vector store ChromaDB được khởi tạo với mô hình embedding `sentence-transformers/all-MiniLM-L6-v2`. Hệ thống kiểm định chất lượng dữ liệu (Data Quality Gate) và giám sát độ tươi (Freshness SLA 180 ngày) ghi nhận trạng thái `Pass`, đạt Retrieval Hit Rate 100.0%, Mean Token F1 1.0000 và LLM Judge Accuracy 100.0%.
2. **Pha 2 (Data Corruption & Idempotent Repair):** Triển khai bộ thử thách tiêm 6 kịch bản lỗi thực tế (bỏ rơi 20% bản ghi mới, xóa rỗng summary, chèn chuỗi nhiễu, cắt ngắn title, lùi ngày xuất bản 365 ngày, nhân bản dòng). Kết quả làm bộc lộ hiện tượng **Silent Failure**: Retrieval Hit Rate sụt giảm nghiêm trọng xuống **70.0%**, Token F1 giảm còn **0.8000**, đồng thời Quality Gate và Freshness SLA lập tức chuyển sang `FAIL`.
3. **Cơ chế Phục hồi An toàn (Idempotent Repair):** Tự động khôi phục dữ liệu từ bản lưu trữ thô nguyên vẹn (`crossref_records.json`), tái cấu trúc lại vector database và đưa toàn bộ các chỉ số `Hit Rate`, `Token F1`, `Judge Accuracy` trở về **100.0%** (khôi phục hoàn toàn phong độ AI).
4. **Giới hạn còn lại:** Việc đánh giá LLM Judge nâng cao phụ thuộc vào API key bên ngoài (Gemini/OpenAI); hiện đã cấu hình fallback heuristic judge và Mock LLM để đảm bảo tính tái hiện độc lập trên mọi môi trường.

---

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref REST API (Fallback: local snapshot)
    ├── [1] Raw Preservation -> data/raw/crossref_response.json & crossref_records.json
    ├── [2] Cleaning & Schema Contract -> data/clean/papers_clean.csv & papers_clean.json
    ├── [3] Dense Embedding (MiniLM) -> ChromaDB collection 'papers-baseline'
    ├── [4] Baseline Evaluation & Observability -> baseline_metrics.json, quality/freshness reports
    ├── [5] Synthetic Corruption Suite -> papers_clean_corrupted.json & corruption_log.json
    ├── [6] Corrupted Re-indexing & Evaluation -> ChromaDB 'papers-corrupted', corrupted_metrics.json
    ├── [7] Idempotent Repair (từ data/raw/) -> papers_clean_repaired.json, ChromaDB 'papers-repaired'
    └── [8] Quantitative Comparison Report -> data/reports/corruption_report.md
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| **Ingestion**         | Crossref REST API / Snapshot | Fetch dữ liệu, chuẩn hóa schema `PaperRecord`, bảo toàn dữ liệu gốc | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Nguyễn Thị Chinh |
| **Cleaning**          | `list[PaperRecord]` | Loại bỏ HTML/XML rác, tính `age_days`, dựng `text_for_embedding`, deduplication | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Nguyễn Thị Chinh |
| **Embedding/Index**   | Clean/Corrupted/Repaired Dataframe | Mã hóa vector `all-MiniLM-L6-v2`, lập chỉ mục ChromaDB theo từng collection | `data/chroma/`, `data/embeddings/papers_embeddings*.json` | Nguyễn Thị Chinh |
| **Evaluation**        | Test set (10 câu hỏi) | Đánh giá độ phủ Retrieval (`Hit Rate`), độ tương đồng `Token F1`, và `Judge Accuracy` | `data/results/*_metrics.json`, `data/results/*_answers.json` | Vũ Minh Hiếu |
| **Observability**     | Clean & Corrupted DataFrame | Kiểm định Great Expectations (Null, Unique, Length) và Freshness SLA (180 ngày) | `data/quality/quality_report_*.json`, `freshness_report*.json` | Nguyễn Thị Chinh |
| **Corruption/Repair** | `papers_clean.json`, `crossref_records.json` | Tiêm 6 kịch bản lỗi, log chi tiết; tự động phục hồi an toàn idempotent | `data/results/corruption_log.json`, `papers_clean_repaired.json` | Vũ Minh Hiếu |
| **Orchestration**     | Pipeline scripts & Core config | Điều phối quy trình Phase 1, quản lý cấu hình và thiết lập môi trường | `core/config.py`, `script/run_phase1.py`, `src/pipelines/phase1.py`, `data/reports/phase1_report.md` | Nguyễn Thị Chinh |



---

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | `gemini` (hỗ trợ fallback mock/heuristic khi thiếu key) |
| `LLM_MODEL`                | `gemini-2.5-flash` |
| Embedding model              | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | `24` |
| Retrieval `top_k`           | `4` |
| Freshness threshold          | `180` ngày |
| Ngưỡng vi phạm Freshness SLA | `> 25%` bài quá hạn |

### Lệnh cài đặt

Kích hoạt môi trường ảo Python 3.11+:
```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

### Lệnh chạy

**1. Baseline Pipeline (Pha 1):**
```bash
python script/run_phase1.py
```

**2. Corruption & Repair Flow (Pha 2):**
```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái  | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------- | ----------------------- | ---------------------------------- |
| `python script/run_phase1.py` | Thành công | 2026-09-25 17:05:00 UTC | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| `python script/run_corruption_flow.py` | Thành công | 2026-09-25 17:14:14 UTC | `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/corruption_report.md` |

---

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API (`https://api.crossref.org/works`) |
| Query/filter                | `query=agentic retrieval augmented generation large language model`, `filter=from-pub-date:2026-03-29,has-abstract:true` |
| Thời điểm lấy dữ liệu | 2026-09-25T10:00:00+00:00 |
| Số record nhận được    | 24 |
| Cơ chế retry/backoff      | Exponential backoff với 3 lần thử lại; tự động fallback đọc snapshot offline nếu không có mạng |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id` | `str` | Có | Định danh DOI bài báo | Drop dòng nếu rỗng hoặc null |
| `title` | `str` | Có | Tiêu đề bài báo học thuật | Strip khoảng trắng; drop nếu rỗng |
| `summary` | `str` | Có | Phần tóm tắt abstract bài báo | Bóc tách xóa thẻ HTML `<jats:p>`, strip khoảng trắng |
| `authors` | `str` | Có | Danh sách tác giả phân tách bởi dấu phẩy | Ghép nối list thành chuỗi |
| `categories` | `str` | Có | Lĩnh vực chuyên ngành | Ghép nối các danh mục phân loại |
| `published` | `str` (YYYY-MM-DD) | Có | Ngày xuất bản chính thức | Parse datetime UTC, format thành chuẩn ISO string |
| `age_days` | `int` | Có | Độ tuổi tài liệu tính theo ngày | `(run_date - published).days` |
| `text_for_embedding` | `str` | Có | Đoạn văn bản tích hợp dùng làm ngữ cảnh nhúng | Tạo format có cấu trúc `Title + Authors + Published + Categories + Summary` |

### Quy tắc cleaning

| Quy tắc | Quality dimension liên quan | Số record bị tác động | Cách xác minh |
| ------- | --------------------------- | --------------------: | ------------- |
| Xóa thẻ HTML/XML rác (`<jats:p>`, `</jats:p>`) trong summary | Validity / Cleanness | 24 | Regex clean trong `crossref.py` |
| Loại bỏ các bài báo trùng mã `paper_id` | Uniqueness | 0 | `df.drop_duplicates(subset=["paper_id"])` |
| Lọc bỏ các dòng có tóm tắt rỗng (`summary_chars == 0`) | Completeness | 0 | `df[df["summary_chars"] > 0]` |
| Chuyển đổi timestamp sang định dạng ngày chuỗi `YYYY-MM-DD` | Consistency | 24 | Phù hợp metadata schema của ChromaDB |

**Cách tạo `text_for_embedding`, document ID và `age_days`:**
- `age_days`: Tính bằng chênh lệch giữa ngày chạy pipeline (`run_date`) và ngày `published` của bài báo.
- `text_for_embedding`: Kết hợp có tiền tố các trường: Title, Authors, Published, Categories, và Summary giúp vector embedding nắm bắt toàn diện ngữ cảnh ngữ nghĩa.
- `record_id`: Định dạng `{paper_id}::{index}` đảm bảo tính duy nhất tuyệt đối khi nạp vào vector store ChromaDB.

---

## 6. Evaluation setup

| Thành phần                            | Cấu hình thực tế         |
| ---------------------------------------| --------------------------|
| Số câu hỏi                            | 10 câu hỏi chuẩn hóa |
| Các `question_type`                    | `summary`, `authors`, `date`, `categories` |
| Ground-truth document ID              | DOI chính xác của bài báo mang thông tin câu trả lời (`ground_truth_doc_ids`) |
| Embedding model                       | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection               | ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`) |
| Retrieval `top_k`                      | 4 |
| LLM provider/model                    | `gemini` (`gemini-2.5-flash`), hỗ trợ structured judge & token-level F1 |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` |

**Vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:**  
Giữ nguyên test set là nguyên tắc then chốt của phương pháp nghiên cứu thực nghiệm có đối chứng (Controlled Experiment). Việc này đảm bảo tính nhất quán của thước đo (measurement invariance). Chỉ khi biến độc lập duy nhất thay đổi là **chất lượng dữ liệu trong kho tri thức**, chúng ta mới có thể kết luận chắc chắn rằng sự suy giảm hay phục hồi của `Retrieval Hit Rate` và `Token F1` là do dữ liệu gây ra chứ không phải do câu hỏi test bị thay đổi độ khó.

---

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Có | 24 bản ghi gốc nguyên vẹn |
| Cleaned dataset          | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Có | 24 dòng sạch hoàn chỉnh |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Có | Collection `papers-baseline` |
| Evaluation set           | `data/eval/test_set.json` | Có | 10 câu hỏi test đại diện |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | Hit rate 100%, F1 1.0000 |
| Quality/freshness        | `data/quality/quality_report_baseline.json`, `freshness_report.json` | Có | All checks PASS |
| Baseline report          | `data/reports/phase1_report.md` | Có | Báo cáo chi tiết Phase 1 |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` | `100.0%` | Retriever tìm thấy 100% tài liệu ground-truth trong Top-4 kết quả |
| `mean_token_f1`      | `1.0000` | Câu trả lời trích xuất khớp chính xác tuyệt đối với Ground Truth |
| `judge_accuracy`     | `100.0%` | LLM Judge đánh giá 10/10 câu trả lời đạt độ chính xác nội dung |
| `mean_judge_score`   | `5.0000` | Điểm chất lượng tối đa (5.0 / 5.0) |
| Ragas, nếu có        | `Skipped` | Tạm bỏ qua để tối ưu tốc độ thực thi (kích hoạt khi `RUN_RAGAS=1`) |

---

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| ----- | ----------------- | -------------- | ---------------- | ---------- |
| Row count >= 5 | Completeness | >= 5 dòng | Pass (24 dòng) | `quality_report_baseline.json` |
| `paper_id` not null & non-empty | Completeness | 100% hợp lệ | Pass (True) | `quality_report_baseline.json` |
| `paper_id` unique | Uniqueness | Không trùng lặp | Pass (True) | `quality_report_baseline.json` |
| `title` not null & non-empty | Completeness | 100% hợp lệ | Pass (True) | `quality_report_baseline.json` |
| `summary` length >= 20 | Validity | >= 20 ký tự | Pass (True) | `quality_report_baseline.json` |
| `age_days` <= 180 days | Freshness | <= 180 ngày | Pass (True) | `quality_report_baseline.json` |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | `data/clean/papers_clean.json` |
| Timestamp mới nhất       | `2026-07-22` |
| Ngưỡng freshness         | 180 ngày (tối đa 25% bài cũ quá 180 ngày) |
| Trạng thái baseline      | `Fresh` (`is_fresh: True`) |
| Lý do                     | 100% bài báo được xuất bản trong khoảng 65 - 160 ngày trước, tỷ lệ stale = 0.0% (<= 25%) |

---

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| ---------- | -------- | -----------------: | ---------------------- | ---------------- | ----------- |
| **Drop latest records** | Bỏ 20% bản ghi mới nhất ở đầu danh sách | 4 bản ghi | Freshness SLA cảnh báo | Mất ngữ cảnh, giảm `Hit Rate` từ 100% xuống 70% | Nạp lại từ `data/raw/crossref_records.json` |
| **Blank summary** | Gán `summary = ""` cho 2 bản ghi | 2 bản ghi | GX check `summary_length_ok = False` | Giảm điểm `Token F1` và nội dung trả lời rỗng | Khôi phục trường tóm tắt từ raw records |
| **Inject noise** | Chèn chuỗi token rác vô nghĩa vào cuối tóm tắt | 2 bản ghi | Semantic drift, vector distortion | Làm sai lệch cosine distance của embedding | Làm sạch lại văn bản từ nguồn thô |
| **Truncate title** | Cắt ngắn tiêu đề xuống < 8 ký tự (`title[:5]`) | 2 bản ghi | Title lookup match thất bại | Không tra cứu được bài báo chính xác theo tên | Ghi đè lại toàn bộ tiêu đề chuẩn |
| **Stale date** | Lùi ngày xuất bản về 365 ngày trước, tăng `age_days` | 8 bản ghi | Freshness SLA `is_fresh = False` (tỷ lệ 36.4% > 25%) | Sai lệch câu trả lời dạng ngày tháng (`eval_date`) | Tính lại `age_days` từ ngày gốc |
| **Duplicate rows** | Nhân đôi 2 dòng bản ghi đã có | 2 bản ghi | GX check `paper_id_unique = False` | Gây nhiễu phân bố xác suất tìm kiếm | Khử trùng lặp qua `drop_duplicates` |

**Corruption log:**
- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log ghi nhận đầy đủ thời điểm thực hiện, số dòng ban đầu (24), số dòng sau biến đổi (22), danh sách chi tiết từng loại lỗi, số lượng và danh sách DOI của các bài báo bị tác động.

**Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy:**  
Cơ chế phục hồi của nhóm tuân thủ triệt để nguyên lý **Data Lineage & Idempotent Processing**. Khi phát hiện sự cố dữ liệu bẩn, hệ thống **không** thực hiện vá víu chắp vá trên file lỗi hiện tại mà kích hoạt quy trình tải lại từ bản snapshot thô gốc ban đầu (`data/raw/crossref_records.json`). Dữ liệu thô này được đưa qua lại toàn bộ quy trình làm sạch (`build_clean_dataframe`), chạy lại các phép khử trùng lặp và tính toán thời gian, sau đó ghi đè an toàn lên vector store ChromaDB. Nhờ đó, quy trình có tính **Idempotent** (bất biến với số lần chạy): chạy bao nhiêu lần cũng cho ra đúng 1 kết quả sạch và chuẩn xác như ban đầu.

---

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   | `100.0%` | `70.0%` | `100.0%` | -30.0% | +30.0% | Khôi phục 100% khả năng truy xuất đúng tài liệu |
| `mean_token_f1`        | `1.0000` | `0.8000` | `1.0000` | -0.2000 | +0.2000 | Khôi phục câu trả lời khớp chính xác Ground Truth |
| `judge_accuracy`       | `100.0%` | `80.0%` | `100.0%` | -20.0% | +20.0% | Phục hồi hoàn toàn độ chính xác nội dung |
| `mean_judge_score`     | `5.0000` | `4.2000` | `5.0000` | -0.8000 | +0.8000 | Điểm đánh giá chất lượng đạt tối đa trở lại |
| Quality checks pass/fail | `Pass`   | `FAIL`   | `Pass`   | Báo động đỏ | Phục hồi hoàn toàn | Great Expectations chặn đứng vi phạm schema |
| Freshness status         | `Pass`   | `FAIL (Stale)` | `Pass` | Vi phạm SLA (>25%) | Phục hồi hoàn toàn | Freshness quay về mức 0.0% bài quá hạn |

### Hai kết luận có quan hệ nhân quả được hỗ trợ bởi artifacts:

1. **[Data corruption] → [Observability signals alert] → [Agent metric degradation]:**  
   Khi thực hiện bỏ rơi 20% bài báo mới nhất và cắt ngắn tiêu đề, `quality_report_corrupted.json` lập tức chuyển `success = False` và `freshness_report_corrupted.json` phát hiện 36.4% bài cũ. Đồng thời trên tập test set, các câu hỏi truy vấn bài báo bị bỏ rơi không thể tìm thấy tài liệu dẫn đến `retrieval_hit_rate` sụt giảm thẳng từ 100% xuống 70%, chứng minh hiện tượng **Silent Failure** nếu không có Data Quality Gate giám sát.
2. **[Idempotent Repair] → [Quality/Freshness recovery] → [Full Agent metric recovery]:**  
   Hệ thống phục hồi dữ liệu từ `data/raw/crossref_records.json` và build lại vector index `papers-repaired`. Báo cáo `quality_report_repaired.json` đạt `success = True`, và kết quả đánh giá tại `repaired_metrics.json` cho thấy `retrieval_hit_rate` và `mean_token_f1` đều quay trở lại **100%** tương đương với Baseline.

---

## 11. Vấn đề tích hợp quan trọng

Mô tả một vấn đề phát sinh khi ghép các module trong pipeline và cách nhóm xử lý:

- **Triệu chứng:** Khi chạy `python script/run_phase1.py` hoặc `python script/run_corruption_flow.py` trên Windows PowerShell, chương trình bị crash ngay lập tức với lỗi `ModuleNotFoundError: No module named 'pipelines'` và sau đó gặp lỗi `UnicodeEncodeError: 'charmap' codec can't encode character '\u2705'`.
- **Nguyên nhân:**
  1. Terminal PowerShell đang mặc định trỏ tới Python hệ thống thay vì môi trường ảo `.venv` nơi package đã được cài đặt editable mode (`pip install -e .`).
  2. Bảng mã console mặc định của Windows PowerShell là `cp1252`, không hỗ trợ in trực tiếp các ký tự Unicode tiếng Việt có dấu và icon cảm xúc (`✅`, `📊`) nếu stdout chưa được cấu hình UTF-8.
- **Cách xử lý:**
  1. Kích hoạt môi trường ảo thông qua lệnh `.\.venv\Scripts\Activate.ps1`.
  2. Bổ sung đoạn mã phòng vệ tự động cấu hình lại `sys.stdout` và `sys.stderr` sang `utf-8` với cơ chế fallback `errors="replace"` ở đầu các file entrypoint (`script/run_phase1.py`, `script/run_corruption_flow.py`, `src/pipelines/corruption_flow.py`).
- **Cách xác minh:** Chạy lại `python script/run_corruption_flow.py` trên PowerShell thuần túy; toàn bộ bảng số liệu tiếng Việt và icon hiển thị trơn tru không phát sinh lỗi mã hóa, tiến trình trả về exit code 0.

---

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Phụ thuộc mạng ngoài khi fetch Crossref API | Có thể bị timeout nếu API quá tải | Mở rộng cơ chế caching local thông minh với checksum hashing SHA-256 |
| LLM Judge yêu cầu API key Google Gemini | Khi chạy ở môi trường air-gapped/offline phải fallback sang heuristic F1 | Tích hợp thêm mô hình local qua Ollama (`qwen2.5` hoặc `llama3.2`) chạy trực tiếp trên máy |
| Tập test set hiện cố định 10 câu hỏi | Chưa bao phủ được độ biến thiên của các bài toán truy vấn phức tạp | Phát triển module tự động sinh câu hỏi đánh giá tổng hợp bằng kỹ thuật Synthetic Data Generation |

---

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
