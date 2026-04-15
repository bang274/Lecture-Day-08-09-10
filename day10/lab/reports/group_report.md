# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** Nguyễn Đức Cường, Trần Khánh Bằng, Đỗ Hải Nam
**Thành viên:** Nguyễn Đức Cường, Trần Khánh Bằng, Đỗ Hải Nam
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| Trần Khánh Bằng | Ingestion / Raw Owner | khanhbangvt123@gmail.com |
| Nguyễn Đưc Cường | Cleaning & Quality Owner | cuong111103hd@gmail.com |
| Đỗ Hải Nam | Embed & Idempotency Owner | nam.dh200418@gmail.com |
| AI Engineer | Monitoring / Docs Owner |  |

**Ngày nộp:** 2026-04-15  
**Repo:** VinUni-AI20k/Lecture-Day-08-09-10  

---

## 1. Pipeline tổng quan

Nguồn raw là file `policy_export_dirty.csv` mô phỏng export từ hệ thống CRM/Policy Management. 
Hệ thống xử lý qua các bước: Ingest -> Clean (fix logic & format) -> Validate (check expectations) -> Embed (upsert into ChromaDB) -> Monitor (freshness check).

**Lệnh chạy một dòng:**
```bash
python etl_pipeline.py run --run-id sprint4_final
```
`run_id` được lưu trong tên file log, manifest và cả trong metadata của vector store để truy xuất nguồn gốc (Lineage).

---

## 2. Cleaning & expectation

Nhóm đã thêm **3 rule mới** và **2 expectation mới** vào hệ thống.

### 2a. Bảng metric_impact

| Rule / Expectation mới | Trước (sprint1) | Sau / khi inject v2 | Chứng cứ |
|-------------------------|------------------|-----------------------------|-------------------------------|
| `pii_detected_email` | 0 | 1 record bị quarantine | artifacts/quarantine/quarantine_sprint2_v2.csv |
| `too_short_chunk` (<3 words) | 0 | 1 record bị quarantine | artifacts/quarantine/quarantine_sprint2_v2.csv |
| `SLA_P_Normalization` | p1 (lowercase) | P1 (uppercase) | `grep "P1" artifacts/cleaned/...` |
| `no_pii_emails` (Halt) | Pass | Pass | Pipeline log |
| `min_word_count_3` (Warn) | Pass | Pass | Pipeline log |

**Rule chính:**
- Loại bỏ PII (Email) để tránh rò rỉ thông tin cá nhân vào vector store.
- Chuẩn hóa SLA (p1 -> P1) để đồng nhất câu trả lời cho Agent.
- Loại bỏ các chunk quá ngắn (< 3 từ) không có giá trị thông tin.

---

## 3. Before / after ảnh hưởng retrieval

**Kịch bản inject:**
Nhóm chạy pipeline với `--no-refund-fix` để giữ lại thông tin sai "14 ngày hoàn tiền" và đẩy vào vector store.

**Kết quả định lượng:**
- **Good State**: `hits_forbidden=no` cho câu hỏi hoàn tiền. Người dùng nhận thông tin 7 ngày.
- **Bad State**: `hits_forbidden=yes`. Query trả về chunk chứa "14 ngày làm việc" (stale), có thể gây ra hallucination cho Agent.
Bằng chứng nằm ở:
- `artifacts/eval/before_after_eval_good.csv`
- `artifacts/eval/before_after_eval_bad.csv`
- Re-run validation: `artifacts/eval/before_after_eval_good_check.csv`, `artifacts/eval/before_after_eval_bad_check.csv`

---

## 4. Freshness & monitoring

Nhóm chọn SLA Freshness là **24 giờ**. Kết quả hiện tại là **FAIL** vì dữ liệu mẫu có `exported_at` từ ngày 2026-04-10, vượt quá ngưỡng cho phép. Trong thực tế, điều này sẽ kích hoạt cảnh báo để kỹ sư kiểm tra hệ thống export.

**Lưu ý vận hành:** Freshness FAIL ở đây là hành vi mong đợi trên data mẫu stale của lab, không phải lỗi code pipeline.

---

## 4.1. Test execution evidence (math_agent)

Nhóm đã tái chạy full test commands trong môi trường Anaconda `math_agent`:

- `python etl_pipeline.py run --run-id good_state_check` -> pass (`PIPELINE_OK`)
- `python etl_pipeline.py run --run-id inject_bad_check --no-refund-fix --skip-validate` -> pass có chủ đích, expectation refund fail và vẫn publish do skip validate
- `python eval_retrieval.py --out ...good_check.csv` và `...bad_check.csv` -> tạo thành công file so sánh
- `python etl_pipeline.py freshness --manifest artifacts/manifests/manifest_good_state_check.json` -> FAIL đúng kỳ vọng do stale timestamp

**Điểm chặn hiện tại:** `grading_run.py` chưa chạy được vì thiếu file `data/grading_questions.json` trong repo tại thời điểm test. 
Khi giảng viên public file này, nhóm chỉ cần chạy lại:
`python grading_run.py --out artifacts/eval/grading_run.jsonl`
và
`python instructor_quick_check.py --grading artifacts/eval/grading_run.jsonl`.

---

## 5. Liên hệ Day 09

Dữ liệu sau khi embed vào collection `day10_kb` sẽ được Agent ở Day 09 sử dụng. Việc làm sạch ở tầng Data Pipeline giúp Agent không cần xử lý các trường hợp format ngày lỗi hay thông tin stale, từ đó phản hồi chính xác và chuyên nghiệp hơn.

---

## 6. Rủi ro còn lại & việc chưa làm

- Cần thêm các rule kiểm tra mâu thuẫn semantic (ví dụ: một policy nói A, policy khác nói B cùng thời điểm).
- Chưa có dashboard visual cho số liệu quality hàng ngày.