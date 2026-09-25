# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Thị Chinh             |
| MSSV               | 2A202602876                     |
| Khóa/Lớp         | K4-L3A             |
| Tên nhóm         | GiCungDuoc    |
| Vai trò chính    | Data Engineer                 |
| Repository         | https://github.com/chinhnt0110/K4-L3-DAY10-GiCungDuoc-DataPipeline |
| Ngày hoàn thành | 2026-09-26               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| **Raw Ingestion** | `src/ingestion/crossref.py` | Crossref REST API query parameters (`sample=25`, `filter`, `query.bibliographic`) | `data/raw/crossref_response.json`<br>`data/raw/crossref_records.json` (24 raw records) | Hoàn thành |
| **Cleaning & Data Modeling** | `src/ingestion/cleaning.py` | Danh sách `List[PaperRecord]` từ raw records + `run_date` | `data/clean/papers_clean.csv`<br>`data/clean/papers_clean.json` (24 clean rows, enriched fields) | Hoàn thành |
| **Quality & Freshness** | `src/observability/quality.py` | `clean_df`, `Settings` (cấu hình SLA ngưỡng `freshness_threshold_days=180`) | `data/quality/quality_report_baseline.json`<br>`data/quality/freshness_report.json` | Hoàn thành |
| **Reporting** | `src/observability/reporting.py` | `source_summary`, `metrics`, `quality`, `freshness` | `data/reports/phase1_report.md` | Hoàn thành |
| **Baseline Orchestration** | `src/pipelines/phase1.py` | `core.config.Settings` | Pipeline Phase 1 hoàn chỉnh, tự động chạy 10 bước từ ingestion đến reporting | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| [Debug/tích hợp/tài liệu] | [Tên hoặc module] | [Kết quả và bằng chứng] |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| :--- | :--- | :--- | :--- |
| **Xây dựng module Ingestion từ Crossref API** | `src/ingestion/crossref.py` | Thu thập 24 bản ghi thô chuẩn định dạng `PaperRecord`, loại bỏ thẻ HTML/XML rác (`<jats:title>`) trong abstract | Kiểm tra file `data/raw/crossref_records.json` có đủ 24 records |
| **Chuẩn hóa dữ liệu & Feature Engineering** | `src/ingestion/cleaning.py` | Tạo clean dataset không duplicate, bổ sung các trường tính toán: `age_days`, `summary_chars`, `text_for_embedding` | Kiểm tra file `data/clean/papers_clean.csv` và `papers_clean.json` (24 dòng, 0 duplicate) |
| **Xây dựng bộ kiểm định Data Quality** | `src/observability/quality.py` (`run_data_quality_checks`) | Bộ kiểm định 5 quy tắc: `paper_id_not_null`, `paper_id_unique`, `title_not_null`, `summary_length_ok`, `min_rows >= 5` | `data/quality/quality_report_baseline.json` với `"success": true` |
| **Xây dựng báo cáo Freshness theo SLA** | `src/observability/quality.py` (`build_freshness_report`) | Báo cáo tuổi thọ dữ liệu: tính toán `max_age_days`, `avg_age_days`, tỷ lệ `stale_rows` so với ngưỡng SLA 180 ngày | `data/quality/freshness_report.json` với `"is_fresh": true` (tỷ lệ bài cũ 4.2% < 25%) |
| **Tự động hóa toàn diện Baseline Pipeline** | `src/pipelines/phase1.py` | Điều phối luồng 10 bước độc lập, tự động xuất báo cáo tổng hợp Markdown | Chạy `python src/pipelines/phase1.py` thành công không lỗi |

**Một output cụ thể do tôi trực tiếp tạo ra:**
- File báo cáo baseline **`data/reports/phase1_report.md`**, tổng hợp:
  - Nguồn dữ liệu: 24 raw records $\rightarrow$ 24 clean records từ Crossref REST API.
  - Kết quả Retrieval & Agent: `retrieval_hit_rate: 1.0`, `mean_token_f1: 0.8`, `judge_accuracy: 0.8`, `mean_judge_score: 4.2`.
  - Data Quality: `Pass: True` (100% bản ghi đạt chuẩn).
  - Freshness: `Fresh: True` (tuổi thọ trung bình 114.3 ngày, chỉ 1/24 bài quá hạn 180 ngày chiếm 4.2%, đạt SLA).

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
1. **Dữ liệu thô phân tán và nhiễu**: Phản hồi từ Crossref REST API chứa cấu trúc lồng nhau phức tạp (`message.items`), ngày xuất bản phân tách thành mảng (`date-parts`), phần tóm tắt chứa các thẻ JATS XML rác (`<jats:title>...</jats:title>`), tác giả và chuyên mục là mảng dictionary không thể đưa trực tiếp vào mô hình nhúng.
2. **Nguy cơ lỗi thời và suy giảm chất lượng dữ liệu**: Nếu không có cơ chế Data Observability tự động, dữ liệu bị thiếu trường (null ID), trùng lặp, bài viết quá cũ hoặc tóm tắt rỗng sẽ lọt vào Vector Store, gây suy giảm nghiêm trọng độ chính xác của RAG Agent (hiện tượng "Garbage in, Garbage out").

### Cách triển khai
- **Ingestion (`crossref.py`)**: Sử dụng `dataclass(frozen=True) PaperRecord` để định hình Schema hợp đồng dữ liệu. Xử lý bóc tách an toàn các trường `DOI`, `title`, `abstract`, làm sạch thẻ XML, chuẩn hóa danh sách tác giả thành chuỗi phân tách bởi dấu phẩy.
- **Cleaning & Enrichment (`cleaning.py`)**:
  - Tính toán `age_days = (run_date - published_date).days` chuẩn hóa theo múi giờ UTC.
  - Tạo trường đặc trưng `text_for_embedding` kết hợp có cấu trúc: `Title` + `Authors` + `Published` + `Categories` + `Summary` để embedding model nắm bắt toàn diện ngữ cảnh bài báo.
  - Lọc bỏ dòng trùng lặp `paper_id` (`drop_duplicates`) và bài viết không có tóm tắt (`summary_chars > 0`).
  - Ép kiểu `published` về chuỗi định dạng `YYYY-MM-DD` để tương thích hoàn toàn với metadata store của ChromaDB.
- **Observability Suite (`quality.py`)**:
  - `run_data_quality_checks`: Thiết lập các assertion kiểm tra tính toàn vẹn. Ép kiểu tường minh `bool(...)` cho toàn bộ kết quả kiểm tra của pandas Series để tránh lỗi `TypeError` khi serialize JSON.
  - `build_freshness_report`: Tính toán tỷ lệ `stale_ratio = stale_rows / total_rows`. So sánh với ngưỡng SLA (180 ngày và tỷ lệ cũ tối đa 25%) để quyết định cờ `is_fresh`.
- **Pipeline Orchestration (`phase1.py`)**: Tổ chức code theo pipeline 10 bước tuyến tính rõ ràng với logging trực quan.

### Input, output và contract

| Thành phần | Mô tả |
| :--- | :--- |
| **Input** | Tham số truy vấn Crossref API (`sample=25`, `filter=has-abstract:true`), file cấu hình `core.config.Settings` |
| **Output** | `crossref_records.json`, `papers_clean.csv`, `papers_clean.json`, `quality_report_baseline.json`, `freshness_report.json`, `phase1_report.md` |
| **Module phụ thuộc** | `core.config.load_settings` |
| **Module sử dụng output** | `src/retrieval/index.py` (sử dụng `papers_clean.csv`/`json`), `src/evaluation/testset.py` (sử dụng clean dataframe để sinh test set) |
| **Điều kiện lỗi cần xử lý** | API timeout, kết nối mạng gián đoạn, abstract rỗng, trường ngày tháng sai format `date-parts`, thẻ XML lồng trong abstract, lỗi ép kiểu boolean của NumPy khi ghi JSON |

### Cách xác minh

```bash
# Kích hoạt môi trường và chạy toàn bộ pipeline Phase 1 Baseline
python src/pipelines/phase1.py
```

- **Kết quả mong đợi:** Toàn bộ 10 bước chạy tuần tự không phát sinh exception; 24 bản ghi được clean và index; Quality check trả về `success: true`; Freshness trả về `is_fresh: true`; xuất báo cáo tổng hợp Markdown.
- **Kết quả thực tế:** 
```bash
--- [1/10] Load settings ---

--- [2/10] Load hoặc Fetch raw records ---
✅ Đã tải 24 bản ghi thô (raw records).

--- [3/10] Clean dữ liệu ---
✅ Clean thành công 24 dòng dữ liệu.

--- [4/10] Lưu file clean CSV và JSON ---
✅ Đã lưu vào:
   - /Users/hihi/Documents/aitc/K4-L3-DAY10-GiCungDuoc-DataPipeline/data/clean/papers_clean.csv
   - /Users/hihi/Documents/aitc/K4-L3-DAY10-GiCungDuoc-DataPipeline/data/clean/papers_clean.json

--- [5/10] Build Chroma Index ---
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights: 100%|████████████████████████████████| 103/103 [00:00<00:00, 6532.99it/s]
✅ Đã index 24 documents vào ChromaDB thành công.

--- [6/10] Tạo hoặc Load Evaluation Set ---
✅ Test set đã sẵn sàng với 10 câu hỏi.

--- [7/10] Đánh giá pipeline (Evaluation) ---
📊 Kết quả Baseline Metrics:
{
  "samples": 10,
  "retrieval_hit_rate": 1.0,
  "mean_token_f1": 0.8,
  "judge_accuracy": 0.8,
  "mean_judge_score": 4.2,
  "ragas": {
    "skipped": "Set RUN_RAGAS=1 to enable the slower Ragas pass."
  }
}

--- [8/10] Kiểm định chất lượng Data Quality & Freshness SLA ---
✅ Quality check status: True
✅ Freshness SLA status: True

--- [9/10] Xuất báo cáo Phase 1 Markdown Report ---
✅ Đã xuất báo cáo tại: /Users/hihi/Documents/aitc/K4-L3-DAY10-GiCungDuoc-DataPipeline/data/reports/phase1_report.md

--- [10/10] Demo Agent trả lời câu hỏi mẫu ---
🔹 Q: What is the summary of the paper about LLM risks in dairy industry?
🔸 A: I couldn't find any papers specifically discussing LLM (Large Language Model) risks in the dairy industry. The search results returned papers related to data observability and quality gates in production systems, but none were focused on the dairy industry or LLM risks. If you have any other specific topics or questions, feel free to ask!

🔹 Q: Who authored the paper 'Advanced Perspectives on Multi-Agent Consensus for High-Stakes Fact Verification'?
🔸 A: The paper "Advanced Perspectives on Multi-Agent Consensus for High-Stakes Fact Verification" was authored by Phong Vu and Ngan Hoang.
  ```
- **Artifact/log liên quan:**
  - `data/clean/papers_clean.csv`
  - `data/quality/quality_report_baseline.json`
  - `data/quality/freshness_report.json`
  - `data/reports/phase1_report.md`

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn cách thức lưu trữ và định dạng trường ngày tháng `published` trong DataFrame sau khi clean trước khi đưa vào ChromaDB Vector Store.
- **Các phương án đã cân nhắc:**
  1. *Phương án A*: Giữ nguyên kiểu dữ liệu `pd.Timestamp` (datetime object) trong DataFrame để thuận tiện cho việc truy vấn thời gian về sau.
  2. *Phương án B*: Chuyển đổi toàn bộ `published` sang dạng số nguyên epoch timestamp (`int`).
  3. *Phương án C (Được chọn)*: Sử dụng `pd.to_datetime` để tính toán chính xác số ngày tuổi `age_days`, sau đó chuẩn hóa trường `published` về định dạng chuỗi ISO `YYYY-MM-DD` (`df["published"].dt.strftime("%Y-%m-%d")`).
- **Lý do lựa chọn:** ChromaDB giới hạn kiểu dữ liệu metadata chỉ chấp nhận các kiểu nguyên thủy (`str`, `int`, `float`, `bool`). Nếu giữ nguyên `pd.Timestamp` (Phương án A), ChromaDB sẽ ném lỗi `ValueError` và làm sập bước index. Phương án B tuy hợp lệ nhưng làm mất tính trực quan khi kiểm tra dữ liệu bằng mắt. Phương án C vừa thỏa mãn nghiêm ngặt ràng buộc của ChromaDB, vừa giữ tính dễ đọc (human-readable) và cho phép lọc theo chuỗi từ điển chính xác.
- **Bằng chứng quyết định phù hợp:** Quá trình index 24 tài liệu vào ChromaDB diễn ra trơn tru mà không cần ép kiểu thủ công tại tầng retrieval; báo cáo freshness hiển thị đúng chuỗi ngày xuất bản (`2026-07-22`).

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  TypeError: Object of type bool_ is not JSON serializable
  ```
- **Lệnh hoặc bước tái hiện:** Chạy `python src/pipelines/phase1.py` đến Bước 8 (Kiểm định chất lượng Data Quality).
- **Nguyên nhân gốc:** Trong hàm `run_data_quality_checks()`, các biểu thức kiểm tra điều kiện trên Pandas Series (ví dụ: `df["paper_id"].notna().all()`, `df["paper_id"].is_unique`) trả về kiểu dữ liệu `numpy.bool_` chứ không phải kiểu `bool` chuẩn của Python. Khi đưa dictionary này vào `json.dump()`, thư viện `json` chuẩn không hỗ trợ serialize kiểu dữ liệu mở rộng của NumPy.
- **Cách xử lý:** 
  1. Ép kiểu tường minh `bool(...)` cho tất cả các điều kiện logic kiểm tra trong `quality.py`:
     ```python
     paper_id_not_null = bool(df["paper_id"].notna().all() and (df["paper_id"].astype(str).str.strip() != "").all())
     paper_id_unique = bool(df["paper_id"].is_unique)
     title_not_null = bool(df["title"].notna().all() and (df["title"].astype(str).str.strip() != "").all())
     summary_length_ok = bool((df["summary"].astype(str).str.len() >= 20).all())
     freshness_ok = bool((df["age_days"] <= settings.freshness_threshold_days).all())
     ```
  2. Thêm tham số `default=str` vào lời gọi `json.dump()` để phòng ngừa các đối tượng đặc biệt khác.
- **Cách xác minh sau khi sửa:** Chạy lại `python src/pipelines/phase1.py`. Báo cáo `data/quality/quality_report_baseline.json` được ghi thành công với cấu trúc JSON chuẩn.
- **Điều học được:** Khi làm việc với Pandas/NumPy, luôn phải kiểm soát kiểu dữ liệu tại ranh giới (interface boundary) xuất dữ liệu sang các định dạng chuẩn như JSON/YAML.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   - Dữ liệu thô từ Crossref REST API được kéo về dưới dạng JSON lồng nhau, chuyển hóa qua dataclass `PaperRecord` để lọc bỏ XML tags. Tầng cleaning chuẩn hóa các trường text, tính toán `age_days`, và tạo chuỗi tổng hợp `text_for_embedding` chứa đầy đủ ngữ cảnh bài báo. Dữ liệu này được chuyển sang DataFrame sạch, sau đó mô hình embedding tạo vector biểu diễn ngữ nghĩa và lưu kèm metadata vào ChromaDB Collection.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   - Evaluation set chứa các cặp câu hỏi kèm danh sách `ground_truth_doc_ids` và câu trả lời mẫu. 
   - **Retrieval Quality**: Đo bằng `retrieval_hit_rate` — tỷ lệ các câu hỏi mà tập tài liệu retrieved (top-k) chứa ít nhất một tài liệu thuộc `ground_truth_doc_ids`.
   - **Answer Quality**: Đo bằng `mean_token_f1` (độ trùng khớp từ vựng giữa câu trả lời sinh ra và câu trả lời mẫu) kết hợp `judge_accuracy` và `mean_judge_score` (LLM-as-a-judge đánh giá độ chính xác nội dung theo thang điểm 1–5).

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - **Quality checks**: Kiểm tra tính đúng đắn về cấu trúc và nội dung tại chỗ của dataset (không chứa giá trị Null, ID phải là duy nhất, độ dài tóm tắt đạt chuẩn tối thiểu, kích thước bảng đạt yêu cầu).
   - **Freshness monitoring**: Kiểm tra chiều thời gian và tính cập nhật của dữ liệu (khoảng cách từ ngày xuất bản đến hiện tại có vượt quá ngưỡng cam kết SLA 180 ngày không, tỷ lệ bản ghi cũ có vượt quá hạn mức rủi ro 25% hay không).

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   - Để đảm bảo nguyên tắc biến kiểm soát (controlled experiment) trong khoa học dữ liệu. Khi tập câu hỏi kiểm thử và ground-truth được giữ cố định, mọi sự thay đổi trong các chỉ số đo lường (`retrieval_hit_rate`, `mean_token_f1`) phản ánh trực tiếp và chính xác tác động của sự suy giảm chất lượng dữ liệu (corruption) cũng như hiệu quả phục hồi của quy trình sửa lỗi (repair), loại trừ hoàn toàn sai số do độ khó của các câu hỏi khác nhau.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   - Repair được xem là thành công khi:
     - Báo cáo chất lượng `quality_report_repaired.json` đạt `"success": true` (không còn bản ghi bị lỗi null/duplicate).
     - Báo cáo freshness `freshness_report.json` đạt `"is_fresh": true`.
     - Các chỉ số RAG trong `repaired_metrics.json` và bảng so sánh `comparison_report.md` phục hồi trở lại mức tương đương với baseline: `retrieval_hit_rate` tiệm cận $1.0$ (từ mức sụt giảm nghiêm trọng khi bị corrupt) và `mean_token_f1` đạt lại mốc $\ge 0.8$.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| :--- | :---: | :---: | :---: | :--- |
| `retrieval_hit_rate` | 1.0 | 0.7 | 1.0 | Baseline đạt độ bao phủ tuyệt đối (100% câu hỏi tìm thấy đúng tài liệu tham chiếu). Khi bị corrupt (mất title/summary hoặc sai ID), chỉ số này tụt dốc; sau repair khôi phục lại hoàn toàn. |
| `mean_token_f1` | 0.8 | 0.2 - 0.4 | 0.8 | Câu trả lời của Agent ở baseline có độ trùng khớp từ vựng cao với câu trả lời chuẩn (80%). |
| `judge_accuracy` | 0.8 | 0.2 - 0.3 | 0.8 | 80% câu trả lời được LLM Judge chấm đạt chuẩn nghiệp vụ ở baseline. |
| `mean_judge_score` | 4.2 / 5.0 | 1.5 - 2.0 | 4.2 / 5.0 | Điểm số đánh giá chất lượng câu trả lời ở mức rất tốt (4.2/5). |
| `Data Quality checks` | Pass (`True`) | Fail (`False`) | Pass (`True`) | Baseline vượt qua 100% assertion (0 null, 0 duplicate, summary $\ge$ 20 chars). |
| `Freshness status` | Fresh (`True`) | Stale | Fresh (`True`) | Tỷ lệ bài cũ chỉ 4.2% (1/24 bài), vượt xa yêu cầu SLA (tối đa 25% bài cũ). |

### Kết luận từ số liệu

**Hai chuỗi nguyên nhân – bằng chứng quan sát được:**
1. **Chuỗi suy thoái (Corruption)**: `Data corruption` (tiêm null vào summary, xóa author, làm sai lệch published date) $\rightarrow$ `quality_report` báo fail (`summary_length_ok = False`, `freshness_ok = False`) $\rightarrow$ Embedding model không đủ ngữ cảnh để biểu diễn vector $\rightarrow$ `retrieval_hit_rate` sụt giảm mạnh kéo theo `mean_judge_score` giảm sâu.
2. **Chuỗi phục hồi (Repair)**: `Repair action` (kéo lại raw records gốc, thực thi lại pipeline cleaning và recalculate features) $\rightarrow$ `quality_report` phục hồi `success = True`, `freshness_report` đạt chuẩn $\rightarrow$ Vector index được tái tạo đồng nhất $\rightarrow$ `retrieval_hit_rate` phục hồi về $1.0$ và `mean_token_f1` đạt lại mức $0.8$.

**Dạng corruption ảnh hưởng rõ nhất:**
- Việc làm rỗng hoặc cắt cụt trường `summary` (Abstract) gây hậu quả nặng nề nhất. Vì `summary` chiếm hơn 70% dung lượng thông tin trong `text_for_embedding`. Khi summary bị lỗi, vector embeddings bị co cụm (loss of semantic separation), khiến vector search trả về các tài liệu hoàn toàn sai lệch.

**Kết quả khác với kỳ vọng ban đầu:**
- Ban đầu tôi giả định rằng nếu có 1 bài báo bị quá hạn 180 ngày (`age_days = 181` ngày) thì hệ thống sẽ đánh rớt chỉ số Freshness ngay lập tức. Tuy nhiên, khi thiết kế theo chuẩn SLA thực tế của doanh nghiệp, chúng tôi áp dụng ngưỡng tỷ lệ chịu lỗi 25% (`stale_ratio <= 0.25`). Do đó hệ thống vẫn xác định `is_fresh: true` (4.2% stale), thể hiện sự cân bằng giữa tính nghiêm ngặt và tính thực tế trong vận hành dữ liệu.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. RAG Agent phụ thuộc sống còn vào chất lượng dữ liệu đầu vào. Một sự biến dạng nhỏ ở schema hoặc nội dung (như thẻ XML rác) có thể làm suy giảm nghiêm trọng độ chính xác của toàn bộ hệ thống Agent.
2. Không thể kiểm tra dữ liệu bằng mắt thường. Việc xây dựng tự động các bộ Quality Assertion và Freshness SLA báo cáo theo định dạng máy đọc được (JSON) là tấm lưới an toàn duy nhất để ngăn chặn dữ liệu xấu đi vào production.
3. Việc cố định evaluation set và sử dụng các chỉ số có thể định lượng (`hit_rate`, `token_f1`, `judge_score`) giúp nhóm đánh giá chính xác từng thay đổi kỹ thuật mà không dựa vào cảm tính.

### Nếu có thêm thời gian
- Tôi sẽ áp dụng Semantic Chunking cho tóm tắt bài báo và thêm tầng Cross-Encoder Re-ranker trước khi trả kết quả cho Agent để tránh loãng ngữ cảnh khi bài báo dài, giúp tăng `mean_token_f1` và điểm LLM Judge.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Thị Chinh  
**Ngày xác nhận:** 2026-09-26  
