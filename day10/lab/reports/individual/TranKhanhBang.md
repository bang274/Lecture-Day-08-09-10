# Individual Report — Lab Day 10 (GV format)

**Họ và tên:** Tran Khanh Bang
**Mã số:** AI20K-274
**Vai trò:** Full-stack Pipeline Owner
**Độ dài:** ~500 từ

---

## 1. Phụ trách

Tôi triển khai toàn bộ pipeline Day 10: `transform/cleaning_rules.py` (rules 1–10), `quality/expectations.py` (E1–E9), embed ChromaDB với upsert + prune stale ids, manifest + freshness_check, và toàn bộ documentation (architecture, data contract, runbook, quality report).

**Bằng chứng:** `artifacts/logs/run_final-run.log` (raw=10, cleaned=6, quarantine=4, 9 expectations OK), `artifacts/eval/final_grading.jsonl` (3/3 PASS), `artifacts/eval/final_eval.csv` (4/4 PASS).

---

## 2. Quyết định kỹ thuật

**Halt vs warn:** `refund_no_stale_14d_window` → **halt** vì sai policy trực tiếp ảnh hưởng agent retrieval. `exported_at_present` → **warn** vì missing exported_at không làm sai retrieval content, chỉ ảnh hưởng freshness tracking downstream.

**Idempotency:** Pipeline prune các vector id trong collection nhưng không còn trong batch hiện tại — tránh top-k còn "14 ngày làm việc" sau khi inject-bad.

---

## 3. Sự cố / anomaly

Khi thử bỏ prune, `grading_run.jsonl` báo `hits_forbidden=true` dù cleaned đã sạch — nguyên nhân vector cũ còn trong ChromaDB. Fix: prune trong `etl_pipeline.py` sau khi so sánh `prev_ids` vs `ids`.

---

## 4. Before/after

**Log:** `expectation[refund_no_stale_14d_window] OK (halt) :: violations=0` sau run chuẩn `final-run`; trước đó với `--no-refund-fix` expectation `FAIL :: violations=1`.

**CSV:** dòng `q_refund_window` có `hits_forbidden=no`, `contains_expected=yes` trong `artifacts/eval/final_eval.csv`.

**Grading:** `gq_d10_01` → `contains_expected=true, hits_forbidden=false`; `gq_d10_02` → `contains_expected=true`; `gq_d10_03` → `top1_doc_matches=true`.

---

## 5. Cải tiến thêm 2 giờ

Đọc cutoff HR `2026-01-01` từ `contracts/data_contract.yaml` thay vì hard-code trong Python (hướng Distinction d).
