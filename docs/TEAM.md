# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `GiCungDuoc`
- **Mã Nhóm / Lớp:** `K4-L3A`
- **Tên Repository Nộp Bài:** `https://github.com/chinhnt0110/K4-L3-DAY10-GiCungDuoc-DataPipeline`

---

## # Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Vũ Minh Hiếu | 2A202602779 | hieuvm@example.com | Corruption, Evaluation & Repair Lead (`corruption.py`, `corruption_flow.py`, `run_corruption_flow.py`, `reporting.py`) | `report/2A202602779_VuMinhHieu.md` |
| 2 | Nguyễn Thị Chinh | 2A202602876 | chinhnt0110@gmail.com | Pipeline Orchestration & Data Observability (`core/`, `phase1.py`, `crossref.py`, `cleaning.py`, `quality.py`) | `report/2A202602876_NguyenThiChinh.md` |

---

## # Cá nhân

### ## VuMinhHieu-2A202602779
- **Vai trò:** Corruption, Evaluation & Repair Lead.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết kế và triển khai 6 kịch bản tiêm lỗi dữ liệu thực tế trong `src/ingestion/corruption.py` và nhật ký `data/results/corruption_log.json`.
  - Xây dựng quy trình tích hợp toàn tuyến Phase 2 trong `src/pipelines/corruption_flow.py` và entrypoint `script/run_corruption_flow.py`.
  - Hiện thực hóa cơ chế Idempotent Repair khôi phục dữ liệu từ raw snapshot, tái nạp vector database ChromaDB `papers-repaired`.
  - Xuất bảng đối chiếu định lượng 3 trạng thái (Baseline vs Corrupted vs Repaired) trong `src/observability/reporting.py`.
- **Điều học được / Đóng góp chính:**
  - Nắm vững cơ chế phát hiện Silent Failure và thiết kế quy trình phục hồi bất biến Idempotent Pipeline.

### ## NguyenThiChinh-2A202602876
- **Vai trò:** Pipeline Orchestration & Data Observability.
- **Công việc chi tiết đã hoàn thành:**
  - Quản lý cấu hình toàn hệ thống `core/config.py` và điều phối luồng Baseline Pipeline `src/pipelines/phase1.py`.
  - Xây dựng module thu thập Crossref REST API với cơ chế fallback snapshot trong `src/ingestion/crossref.py`.
  - Chuẩn hóa schema, khử trùng lặp và tính `text_for_embedding`, `age_days` trong `src/ingestion/cleaning.py`.
  - Thiết lập Data Quality checks (Great Expectations) và Freshness SLA (180 ngày) trong `src/observability/quality.py`.

- **Điều học được / Đóng góp chính:**
  - Tầm quan trọng của Raw Data Preservation (bảo tồn bản thô) và thiết lập chốt kiểm dịch dữ liệu trước khi cung cấp cho AI.
