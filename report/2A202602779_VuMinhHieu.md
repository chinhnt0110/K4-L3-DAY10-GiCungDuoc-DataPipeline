# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Vũ Minh Hiếu               |
| MSSV               | 2A202602779                |
| Khóa/Lớp         | K4-L3A                     |
| Tên nhóm         | GiCungDuoc                 |
| Vai trò chính    | Corruption, Evaluation & Repair Lead |
| Repository         | https://github.com/chinhnt0110/K4-L3-DAY10-GiCungDuoc-DataPipeline |
| Ngày hoàn thành | 2026-09-26                 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ---------- |
| **Data Corruption Suite** | `src/ingestion/corruption.py` (`corrupt_clean_dataframe`) | Clean DataFrame (`papers_clean.json`) | Corrupted DataFrame & `data/results/corruption_log.json` | Hoàn thành |
| **Phase 2 Pipeline Integration** | `src/pipelines/corruption_flow.py`, `script/run_corruption_flow.py` | Cấu hình `Settings`, baseline metrics, clean & raw records | Quy trình thực thi Phase 2 end-to-end 8 bước | Hoàn thành |
| **Quantitative Comparison Reporting** | `src/observability/reporting.py` (`generate_corruption_report`) | Baseline, Corrupted, Repaired metrics & quality signals | Bảng đối chiếu 3 cột và file `data/reports/corruption_report.md` | Hoàn thành |
| **Idempotent Repair Execution** | `src/pipelines/corruption_flow.py` (Step 6) | `data/raw/crossref_records.json` | Khôi phục 24 bản ghi sạch, ghi đè ChromaDB, trả lại chỉ số 100% | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ----------------------------- | ------- |
| Hỗ trợ debug môi trường ảo và bảng mã console Windows | Nguyễn Thị Chinh (`phase1.py`, `quality.py`) | Khắc phục lỗi `ModuleNotFoundError` và lỗi font `cp1252` bằng `sys.stdout.reconfigure(encoding="utf-8")` |
| Rà soát schema đối chiếu đánh giá | Module Evaluation (`testset.py`, `metrics.py`) | Đảm bảo test set 10 câu hỏi bao phủ đủ 4 loại truy vấn và kiểm thử tính toàn vẹn của `ground_truth_doc_ids` |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ---------------- | ------------- |
| Thiết kế 6 kịch bản tiêm lỗi dữ liệu | `src/ingestion/corruption.py` | Dataframe hỏng 22 dòng, nhật ký `corruption_log.json` | `python -c "from ingestion.corruption import corrupt_clean_dataframe; ..."` |
| Triển khai luồng Phase 2 Corruption & Repair | `src/pipelines/corruption_flow.py` | Pipeline tự động hóa trọn gói, xử lý silent failure & repair | `python script/run_corruption_flow.py` |
| Xuất báo cáo đối chiếu định lượng 3 trạng thái | `src/observability/reporting.py` | Bảng so sánh 3 cột in console và lưu `corruption_report.md` | Kiểm tra `data/reports/corruption_report.md` |
| Đo lường sự sụt giảm và mức độ phục hồi | `data/results/` | `corrupted_metrics.json`, `repaired_metrics.json` | Đối chiếu số liệu JSON thực tế |

**Output cụ thể tạo ra:**  
Báo cáo đối chiếu định lượng 3 trạng thái [data/reports/corruption_report.md](file:///c:/Users/hungn/OneDrive/Desktop/vin/K4-L3A-Day10-Data-Pipeline-Data-Observability/data/reports/corruption_report.md) chứng minh hiện tượng **Silent Failure** (Retrieval Hit Rate rơi từ 100% xuống 70%, F1 rơi từ 1.0000 xuống 0.8000 khi tiêm lỗi) và xác nhận năng lực **Idempotent Repair** khôi phục hoàn toàn 100% phong độ của AI.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Trong các hệ thống RAG Agent phục vụ sản xuất, dữ liệu lỗi thường không làm hệ thống sập (crash) mà âm thầm gây suy thoái kết quả trả lời của AI (Silent Failure). Trách nhiệm của tôi là:
1. Xây dựng bộ thử thách tiêm 6 dạng độc tố dữ liệu phổ biến để kiểm thử độ bền của vector database.
2. Đo lường định lượng mức độ sụt giảm qua các chỉ số retrieval và generation.
3. Hiện thực hóa cơ chế tự phục hồi bất biến (Idempotent Repair) từ nguồn dữ liệu thô ban đầu để đưa hệ thống trở lại trạng thái hoàn hảo.

### Cách triển khai
1. Trong `src/ingestion/corruption.py`:
   - `Drop latest records`: Bỏ 20% bản ghi mới nhất ở đầu dataframe để kiểm tra phản ứng của hệ thống khi mất dữ liệu mới.
   - `Blank summary`: Xóa trắng phần tóm tắt ở 2 dòng để kích hoạt lỗi độ dài của Great Expectations (`summary_length_ok = False`).
   - `Inject noise`: Chèn chuỗi token rác vào cuối summary ở 2 dòng nhằm làm méo mó không gian vector embedding.
   - `Truncate title`: Cắt ngắn tiêu đề bài báo xuống < 8 ký tự (`title[:5]`) làm vô hiệu hóa khả năng tìm kiếm chính xác theo tiêu đề.
   - `Stale date`: Lùi ngày xuất bản về 365 ngày trước trên 8 bản ghi (chiếm 36.4%), vượt quá ngưỡng cho phép 25% của Freshness SLA.
   - `Duplicate rows`: Nhân bản 2 dòng bản ghi đã có để vi phạm tính duy nhất của khóa chính (`paper_id_unique = False`).
   - Tái tạo lại chuỗi ngữ cảnh nhúng `text_for_embedding` và ghi log chi tiết từng kịch bản vào `data/results/corruption_log.json`.
2. Trong `src/pipelines/corruption_flow.py`:
   - Kết nối toàn bộ 8 bước từ nạp baseline metrics, tạo corrupted data, lập chỉ mục vector store `papers-corrupted`, đánh giá sụt giảm, kích hoạt khôi phục an toàn từ `data/raw/crossref_records.json`, nạp vector store `papers-repaired`, đánh giá lại và xuất báo cáo so sánh.

### Input, output và contract

| Thành phần | Mô tả |
| ---------- | ----- |
| **Input** | `papers_clean.json` (24 dòng sạch), `crossref_records.json` (24 bản ghi thô gốc) |
| **Output** | `papers_clean_corrupted.json`, `corruption_log.json`, `corrupted_metrics.json`, `papers_clean_repaired.json`, `repaired_metrics.json`, `corruption_report.md` |
| **Module phụ thuộc** | `ingestion/cleaning.py`, `retrieval/index.py`, `evaluation/metrics.py`, `observability/quality.py` |
| **Module sử dụng output** | Toàn bộ nhóm và hội đồng chấm bài dùng để nghiệm thu Checkpoint 4 & 5 |
| **Điều kiện lỗi cần xử lý** | Thiếu file baseline, xung đột bảng mã Windows console cp1252, trùng lặp ID trong ChromaDB |

### Cách xác minh

```bash
# 1. Kiểm tra xác minh module corruption (Bước 7)
python -c "import sys; sys.stdout.reconfigure(encoding='utf-8'); from core.config import load_settings; from ingestion.corruption import corrupt_clean_dataframe; import pandas as pd; s=load_settings(); df=pd.read_json(s.paths.clean_json); c=corrupt_clean_dataframe(df, s.paths.corruption_log); print(f'Tín hiệu hoàn thành: Corrupted {len(c)} dòng')"

# 2. Chạy toàn bộ quy trình tích hợp Pha 2 (Bước 8)
python script/run_corruption_flow.py
```
- **Kết quả mong đợi:** In ra bảng đối chiếu 3 cột rõ ràng; các chỉ số Baseline đạt 100%, Corrupted sụt giảm xuống 70% (Quality FAIL), Repaired khôi phục 100% (Quality PASS).
- **Kết quả thực tế:** Khớp 100% kỳ vọng.
- **Artifact/log:** `data/results/corruption_log.json`, `data/reports/corruption_report.md`.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn cách thức phục hồi dữ liệu khi chốt kiểm dịch Data Quality báo động đỏ: Phục hồi vá lỗi tại chỗ (In-place patching) hay Khôi phục bất biến từ nguồn thô (Idempotent Repair từ raw snapshot).
- **Các phương án đã cân nhắc:**
  - *Phương án 1 (In-place patching):* Viết script duyệt qua file bị lỗi, tìm các dòng summary rỗng để điền giá trị giả định, xóa các dòng trùng lặp.
  - *Phương án 2 (Idempotent Repair từ Raw Backup):* Không can thiệp sửa chữa chắp vá trên dữ liệu hỏng; tái nạp toàn bộ từ bản sao lưu thô ban đầu (`data/raw/crossref_records.json`), chạy lại pipeline làm sạch và build lại vector index.
- **Phương án đã chọn:** Phương án 2 (Idempotent Repair từ Raw Backup).
- **Lý do:** Phương án 1 không thể giải quyết được việc dữ liệu mới bị mất (20% bản ghi mới bị drop) và dễ để lại "rác dữ liệu" hoặc ghost vectors trong ChromaDB. Phương án 2 đảm bảo tính nguyên tử (Atomicity), nguyên lý Data Lineage và tính Idempotent: chạy bao nhiêu lần thì kết quả đầu ra vẫn luôn sạch sẽ và nhất quán như lần đầu.
- **Bằng chứng:** Sau khi chạy repair theo phương án 2, các chỉ số `retrieval_hit_rate` và `mean_token_f1` lập tức quay trở lại mức 100% tuyệt đối, khôi phục toàn vẹn 24 bản ghi sạch.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  Traceback (most recent call last):
    File "script/run_phase1.py", line 3, in <module>
      from pipelines.phase1 import main
  ModuleNotFoundError: No module named 'pipelines'
  ...
  UnicodeEncodeError: 'charmap' codec can't encode character '\u2705' in position 0: character maps to <undefined>
  ```
- **Lệnh hoặc bước tái hiện:** Chạy `python script/run_phase1.py` trên cửa sổ Windows PowerShell mới.
- **Nguyên nhân gốc:**
  1. Terminal chưa kích hoạt môi trường ảo `.venv` mà đang trỏ tới Python mặc định của hệ thống (`AppData/Local/...`) vốn không chứa package đã cài editable mode (`pip install -e .`).
  2. Bảng mã mặc định của Windows console là `cp1252`, không thể render các ký tự Unicode tiếng Việt có dấu và icon (`✅`, `📊`) nếu stdout chưa được cấu hình UTF-8.
- **Cách xử lý:**
  1. Kích hoạt môi trường ảo: `.\.venv\Scripts\Activate.ps1`.
  2. Thêm đoạn mã xử lý encoding tự động ở đầu các file entrypoint:
     ```python
     import sys
     if hasattr(sys.stdout, "reconfigure"):
         sys.stdout.reconfigure(encoding="utf-8", errors="replace")
         sys.stderr.reconfigure(encoding="utf-8", errors="replace")
     ```
- **Cách xác minh sau khi sửa:** Chạy lại `python script/run_corruption_flow.py` trên PowerShell thuần túy; pipeline chạy mượt mà từ bước 1 đến bước 8, hiển thị đầy đủ icon và bảng đối chiếu mà không phát sinh lỗi mã hóa.
- **Điều học được:** Cần luôn chú ý đến sự khác biệt giữa các hệ điều hành (Windows vs Linux) về cơ chế path resolution và terminal character encoding khi xây dựng các pipeline dữ liệu chuyên nghiệp.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index:** Dữ liệu được fetch từ Crossref REST API -> lưu snapshot thô vào `crossref_response.json` (Lineage) -> trích xuất `PaperRecord` -> làm sạch HTML, chuẩn hóa trường, tính `age_days` trong `cleaning.py` -> tạo chuỗi `text_for_embedding` tích hợp đầy đủ metadata -> mã hóa thành vector 384 chiều bằng mô hình MiniLM -> lập chỉ mục vào collection của ChromaDB.
2. **Evaluation set và ground-truth document IDs:** Tập 10 câu hỏi test bao phủ 4 khía cạnh trọng yếu (summary, authors, date, categories). Mỗi câu hỏi đi kèm danh sách DOI tài liệu chuẩn (`ground_truth_doc_ids`). Nếu retriever kéo về tài liệu chứa đúng DOI thì tính là Hit (`retrieval_hit = True`). Câu trả lời trích xuất sau đó được so khớp từ vựng với `ground_truth` để tính điểm `Token F1`.
3. **Quality checks khác Freshness monitoring:** Quality checks (Great Expectations) kiểm định tính đúng đắn cấu trúc tĩnh của dữ liệu (không null, không trùng ID, độ dài tối thiểu). Freshness monitoring theo dõi thuộc tính động theo thời gian (tuổi của tài liệu so với SLA quy định), giúp nhận diện dữ liệu lỗi thời kể cả khi schema hoàn toàn hợp lệ.
4. **Vì sao phải dùng cùng test set:** Đảm bảo nguyên lý nghiên cứu thực nghiệm có đối chứng (Controlled Experiment). Cố định tập câu hỏi giúp ta khẳng định chắc chắn rằng sự sụt giảm hay phục hồi của `Hit Rate` và `Token F1` bắt nguồn 100% từ chất lượng của kho dữ liệu, chứ không phải do sự thay đổi ngẫu nhiên của câu hỏi test.
5. **Repair được xem là thành công:** Khi hội tụ đủ 3 điều kiện: (1) Data Quality check đạt `success: True`, (2) Freshness SLA đạt `is_fresh: True`, và (3) Các chỉ số hiệu năng của AI (`Retrieval Hit Rate`, `Token F1`, `Judge Accuracy`) phục hồi hoàn toàn về mức 100% tương đương trạng thái Baseline.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | `100.0%` | `70.0%`   | `100.0%` | Mất 30% độ phủ tìm kiếm khi bị drop bài mới & cắt tiêu đề; phục hồi hoàn toàn 100% |
| `mean_token_f1`      | `1.0000` | `0.8000`  | `1.0000` | Sụt giảm do summary bị rỗng hoặc dính nhiễu; khôi phục hoàn hảo sau khi repair |
| `judge_accuracy`     | `100.0%` | `80.0%`   | `100.0%` | 2 câu hỏi bị judge đánh giá sai do ngữ cảnh bị cắt xén; khôi phục 10/10 câu đạt chuẩn |
| `mean_judge_score`   | `5.0000` | `4.2000`  | `5.0000` | Điểm chất lượng trung bình giảm về 4.2; khôi phục điểm trần 5.0 |
| Quality checks         | `Pass`   | `FAIL`    | `Pass`   | Great Expectations phát hiện tức thì các vi phạm null, length và uniqueness |
| Freshness status       | `Pass`   | `FAIL`    | `Pass`   | Phát hiện 36.4% bài quá hạn (vượt ngưỡng SLA 25%), phát tín hiệu cảnh báo kịp thời |

### Kết luận từ số liệu

1. **[Tiêm lỗi: Drop 20% bài mới + Blank summary] → [GX & Freshness đồng loạt báo FAIL] → [Hit Rate giảm xuống 70%, F1 còn 0.8]:** Chứng minh hiện tượng Silent Failure cực kỳ nguy hiểm trong thực tế: hệ thống không báo lỗi ứng dụng nhưng trí tuệ nhân tạo bị suy sụp năng lực nghiêm trọng.
2. **[Idempotent Repair từ Raw snapshot] → [Observability signals xanh trở lại] → [Toàn bộ metrics Agent đạt lại 100%]:** Khẳng định cơ chế bảo tồn dữ liệu thô (Raw Preservation) là chốt chặn phòng thủ vững chắc nhất cho toàn bộ hệ thống dữ liệu.

**Corruption ảnh hưởng rõ nhất:**  
Kịch bản **Drop latest records** và **Truncate title** gây thiệt hại nặng nề nhất cho bộ truy xuất (Retriever) vì làm đứt gãy mối liên kết giữa câu hỏi và tài liệu tương ứng trong vector space, khiến Agent không thể tìm thấy thông tin cần thiết.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Bảo tồn dữ liệu thô (Raw Preservation) là sống còn:** Không bao giờ ghi đè trực tiếp lên dữ liệu gốc; luôn lưu trữ snapshot thô để có thể tái tạo pipeline bất cứ lúc nào (Data Lineage & Reproducibility).
2. **Data Observability là lá chắn chống Silent Failure:** Giám sát liên tục chất lượng dữ liệu và Freshness SLA là điều kiện tiên quyết để đảm bảo AI đưa ra câu trả lời trung thực và đáng tin cậy.
3. **Thiết kế Idempotent cho Pipeline:** Một data pipeline tiêu chuẩn sản xuất phải có tính bất biến với số lần chạy (Idempotent), đảm bảo quá trình phục hồi không để lại trạng thái rác hay xung đột dữ liệu.

### Nếu có thêm thời gian

Tôi sẽ nghiên cứu tích hợp thêm **Automated Anomaly Detection** dựa trên mô hình Isolation Forest để tự động phát hiện các bất thường trong phân bố embedding vector mà không cần phải đặt trước các ngưỡng heuristic tĩnh.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Vũ Minh Hiếu  
**Ngày xác nhận:** 2026-09-26
