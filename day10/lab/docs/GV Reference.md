# Báo cáo cá nhân — mẫu GV (reference)

**Họ và tên:** GV Reference  
**Vai trò:** Cleaning & Quality  
**Độ dài:** ~450 từ (mẫu)

---

## 1. Phụ trách

Tôi triển khai module `transform/cleaning_rules.py` để xử lý rule 7-9, bao gồm:
- Quản lý `exported_at` timestamp và validation format
- Xử lý null/empty values cho các trường quan trọng
- Tích hợp với `quality/expectations.py` để kiểm tra E7-E9

Cụ thể, tôi kết nối với embed owner thông qua manifest `cleaned_csv` để đảm bảo dữ liệu sau cleaning được expose đúng cách. File log `cleaned_records` ghi nhận số lượng bản ghi đã được clean thành công mỗi lần chạy pipeline.

**Bằng chứng:** Các commit và file trong repo reference `day10-lab-reference-solution` bao gồm:
- Commit `feat: implement cleaning rules 7-9`
- File `transform/cleaning_rules.py` (lines 45-120)
- File `quality/expectations.py` (lines 30-55)

---

## 2. Quyết định kỹ thuật

**Halt vs warn:** Với trường hợp `exported_at` sai format (không đúng ISO 8601), tôi chọn **quarantine + cleaning** thay vì warn đơn thuần. Lý do: sai clock timestamp sẽ làm ảnh hưởng đến tính toán freshness ở downstream pipeline. Nếu chỉ warn mà vẫn cho đi tiếp, các metrics như "14 ngày trước" sẽ bị sai hoàn toàn. Với trường hợp `exported_at` rỗng trên cleaned CSV, tôi chọn **warn** (E9): pipeline vẫn cho phép publish nhưng log cảnh báo để team xử lý backlog sau.

**Idempotency:** Tôi ủng hộ việc prune vector ID không còn trong batch hiện tại. Điều này tránh tình trạng top-k retrieval vẫn còn kết quả "14 ngày trước" sau khi inject dữ liệu mới, gây confuse cho người dùng.

---

## 3. Sự cố / anomaly

Trong quá trình testing, khi thử bỏ prune step (debugging), file `grading_run.jsonl` báo `hits_forbidden=true` dù dữ liệu cleaned đã sạch. Sau khi investigate, nguyên nhân là do vector cũ từ batch trước vẫn còn trong index. Fix: Thêm prune trong `etl_pipeline.py` ngay sau khi so sánh `prev_ids` vs `ids` để đảm bảo chỉ những vector của batch mới được giữ lại.

---

## 4. Before/after

**Log:** Với config chuẩn (có prune + fix), log hiển thị:
```
expectation[refund_no_stale_14d_window] OK (halt)
```
Trước đó khi chạy với `--no-refund-fix`, expectation FAIL và pipeline halt.

**CSV:** Trong file `artifacts/eval/before_after_eval.csv`, dòng `q_refund_window` có giá trị `hits_forbidden=no` ở cột after, trong khi before là `hits_forbidden=yes`.

---

## 5. Cải tiến thêm 2 giờ

Để đạt hướng Distinction, tôi đọc cutoff HR từ `contracts/data_contract.yaml` thay vì hard-code trong Python. Cụ thể, thêm logic đọc `hr_cutoff_date: "2026-01-01"` từ config và so sánh dynamic với `exported_at` của từng record. Điều này giúp pipeline linh hoạt hơn khi deadline thay đổi mà không cần modify code.
