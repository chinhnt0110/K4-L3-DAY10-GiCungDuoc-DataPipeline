# 📊 BÁO CÁO ĐỐI CHIẾU ĐỊNH LƯỢNG 3 TRẠNG THÁI (CORRUPTION REPORT)
> **Mục tiêu:** Đo lường sự suy giảm chất lượng của RAG Agent khi dữ liệu bị lỗi (Silent Failure) và kiểm chứng năng lực tự phục hồi an toàn (Idempotent Repair).

---

## 1. 📈 Bảng Đối Chiếu Định Lượng 3 Trạng Thái

| Chỉ Số Đánh Giá (Metric) | Baseline (Dữ liệu Sạch) | Corrupted (Dữ liệu Tiêm Lỗi) | Repaired (Sau Phục Hồi) | Phục Hồi (Delta R vs C) |
| :--- | :---: | :---: | :---: | :---: |
| **Data Quality Gate (GX)** | `Pass` | `FAIL` | `Pass` | ✅ Khôi phục 100% |
| **Freshness SLA** | `Pass` | `FAIL (Stale)` | `Pass` | ✅ Khôi phục SLA |
| **Retrieval Hit Rate** | `100.0%` | `70.0%` | `100.0%` | 🔺 +30.0% |
| **Mean Token F1** | `1.0000` | `0.8000` | `1.0000` | 🔺 +0.2000 |
| **LLM Judge Accuracy** | `100.0%` | `80.0%` | `100.0%` | 🔺 +20.0% |
| **Mean Judge Score** | `5.0000` | `4.2000` | `5.0000` | 🔺 +0.8000 |

---

## 2. 🔍 Phân Tích Hiện Tượng Suy Giảm (Silent Failure Analysis)

1. **Quan sát từ chốt kiểm dịch Data Quality (Observability Gate):**
   - Khi tiêm 6 kịch bản lỗi dữ liệu (xóa tóm tắt, cắt ngắn tiêu đề, lùi ngày xuất bản, chèn ký tự rác, nhân bản, mất bản ghi mới), hệ thống kiểm định **Great Expectations 1.x** lập tức gióng chuông báo động (`success = False`).
   - Cảnh báo Freshness SLA phát hiện tỷ lệ bài báo quá hạn vượt ngưỡng quy định.

2. **Tác động tiêu cực đến RAG Agent (Silent Failure):**
   - **Độ phủ tìm kiếm (Hit Rate) sụt giảm:** Embedding vector bị sai lệch do văn bản bị cắt ngắn hoặc nhiễu rác, khiến retriever không kéo được đúng ngữ cảnh.
   - **Ảo giác và suy giảm điểm trả lời (F1 / Judge Score):** Thiếu ngữ cảnh chuẩn dẫn đến việc LLM trả lời mơ hồ hoặc từ chối trả lời, chứng minh rõ ràng: *"Dữ liệu bẩn làm suy sụp năng lực AI"*.

---

## 3. 🛠️ Cơ Chế Tự Phục Hồi An Toàn (Idempotent Repair)

- **Cơ chế hoạt động:** Hệ thống tự động kích hoạt luồng sửa chữa an toàn, tải lại dữ liệu nguyên gốc từ bản lưu trữ thô (`data/raw/crossref_records.json`), chạy lại pipeline làm sạch và tái cấu trúc vector database trên ChromaDB.
- **Tính Idempotent:** Luồng phục hồi có tính bất biến với số lần thực thi — dù chạy 1 lần hay 100 lần, kết quả đầu ra luôn nhất quán, sạch sẽ và an toàn.
- **Kết quả nghiệm thu:** Sau khi phục hồi, toàn bộ các chỉ số `Hit Rate`, `Token F1` và `Judge Accuracy` đều quay trở lại mức ngang bằng với trạng thái **Baseline**, chứng minh AI lấy lại 100% phong độ.
