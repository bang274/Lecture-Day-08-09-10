# Báo cáo cá nhân — Lab Day 10

**Họ và tên:** Tran Khanh Bang
**Mã số:** AI20K-274
**Vai trò:** Full-stack (Ingest, Cleaning & Quality, Embed, Monitoring/Docs)
**Độ dài:** ~500 từ

---

## 1. Phụ trách

Tôi tự triển khai toàn bộ pipeline Day 10, bao gồm:

- **`transform/cleaning_rules.py`**: 10 rules — 6 baseline (allowlist, normalize date, quarantine stale HR, quarantine empty, dedup, fix refund 14→7) + 4 rules mới (R7 PII quarantine, R8 whitespace normalize, R9 exported_at validate, R10 chunk length cap).
- **`quality/expectations.py`**: 9 expectations — 6 baseline + 3 mới (E7 exported_at_present warn, E8 chunk_id_unique halt, E9 doc_id_distribution_balanced warn).
- **Documentation**: pipeline_architecture.md, data_contract.md, runbook.md, quality_report.md.
- **Embed & Monitor**: ChromaDB upsert + prune stale ids, manifest.json, freshness_check.py.

**Bằng chứng:** commit trong repo, `artifacts/logs/run_final-run.log`, `artifacts/eval/final_grading.jsonl`, `artifacts/eval/final_eval.csv`.

---

## 2. Quyết định kỹ thuật

**Halt vs warn cho `exported_at_present`:**

Tôi chọn **warn** thay vì **halt** vì missing exported_at không ảnh hưởng correctness của retrieval — chunk vẫn đúng nội dung. Halt toàn pipeline vì 1 field metadata sẽ làm pipeline quá nhạy cảm, dễ false positive. Warn đủ để monitoring track trend: nếu % missing tăng → điều tra source export.

Ngược lại, `chunk_id_unique` chọn **halt** vì duplicate id gây silent upsert overwrite — mất vector cũ mà không ai biết, khó debug hơn nhiều so với missing metadata.

**Idempotency:** Pipeline dùng upsert theo `chunk_id` + prune stale ids trước khi upsert — tránh top-k còn "14 ngày" sau inject.

---

## 3. Sự cố / anomaly

**Phát hiện:** Khi chạy inject-bad (`--no-refund-fix --skip-validate`), expectation `refund_no_stale_14d_window` FAIL (violations=1) nhưng pipeline vẫn embed do `--skip-validate`.

**Fix:** Eval retrieval sau inject cho `hits_forbidden=yes` trên `q_refund_window` — chứng minh chunk stale vẫn trong top-k. Pipeline đã prune 1 stale vector (`embed_prune_removed=1`) nhưng chunk stale mới (với chunk_id khác do text khác) vẫn được upsert.

**Evidence:** Log inject-bad-final:
```
expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1
WARN: expectation failed but --skip-validate → tiếp tục embed
embed_prune_removed=1
```

---

## 4. Before/after

**Log trước (inject-bad-final):**
```
expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1
```

**Log sau (final-run):**
```
expectation[refund_no_stale_14d_window] OK (halt) :: violations=0
embed_prune_removed=1
```

**Grading results:**
- `gq_d10_01` (refund 7 ngày): `contains_expected=true`, `hits_forbidden=false` ✅
- `gq_d10_02` (SLA 4h resolution): `contains_expected=true` ✅
- `gq_d10_03` (HR leave 12 ngày): `contains_expected=true`, `hits_forbidden=false`, `top1_doc_matches=true` ✅

**Eval CSV:** `artifacts/eval/final_eval.csv` — 4 golden questions, tất cả `contains_expected=yes`, `hits_forbidden=no`.

---

## 5. Cải tiến thêm 2 giờ

1. **Đọc cutoff HR `2026-01-01` từ `contracts/data_contract.yaml`** thay vì hard-code trong `cleaning_rules.py` — hỗ trợ Distinction criterion (d).
2. **Thêm Great Expectations integration** — thay thế custom expectation runner bằng GE suite để có data profile + automated documentation (bonus +2).
