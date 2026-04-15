# Individual Report — Lab Day 10

**Tên:** Tran Khanh Bang
**Mã số:** AI20K-274
**run_id:** clean-run-002
**Ngày:** 2026-04-15

---

## Phần việc cụ thể

Toàn bộ pipeline do tôi tự triển khai, bao gồm tất cả các thành phần:

**Cleaning rules** (`transform/cleaning_rules.py`):
1. **R7 — PII Quarantine:** Hàm `_contains_pii()` phát hiện email/phone pattern trong chunk_text → quarantine để tránh data leak.
2. **R8 — Whitespace Normalization:** Hàm `_normalize_whitespace()` chuẩn hóa ≥3 consecutive spaces/tabs → single space, cải thiện embedding quality và dedup accuracy.
3. **R9 — Exported-at Validation:** Hàm `_normalize_exported_at()` parse DD/MM/YYYY HH:MM format → ISO 8601, hỗ trợ freshness tracking.
4. **R10 — Chunk Length Cap:** Quarantine chunks >2000 chars để tránh oversized embedding.

**Quality expectations** (`quality/expectations.py`):
1. **E7 — exported_at_present (warn):** Đảm bảo mọi row có exported_at để freshness check hoạt động.
2. **E8 — chunk_id_unique (halt):** Phát hiện duplicate chunk_id trước khi upsert — tránh silent data loss.
3. **E9 — doc_id_distribution_balanced (warn):** Alert khi 1 doc_id chiếm >80% cleaned rows — dấu hiệu ingestion filter failure.

**Documentation:** pipeline_architecture.md, data_contract.md, runbook.md, quality_report.md.

---

## 1 quyết định kỹ thuật

**Warn vs Halt cho expectation `exported_at_present`:**

Tôi chọn **warn** thay vì **halt** vì:
- Missing exported_at không ảnh hưởng correctness của retrieval — chunk vẫn đúng nội dung
- Halt toàn pipeline vì 1 field metadata sẽ làm pipeline quá nhạy cảm, dễ false positive
- Warn đủ để monitoring track trend: nếu % missing tăng → điều tra source export

Ngược lại, `chunk_id_unique` chọn **halt** vì duplicate id gây silent upsert overwrite — mất vector cũ mà không ai biết, khó debug hơn nhiều so với missing metadata.

---

## 1 sự cố / anomaly

**Phát hiện:** Khi chạy inject-bad (`--no-refund-fix --skip-validate`), expectation `refund_no_stale_14d_window` FAIL nhưng pipeline vẫn embed do `--skip-validate`.

**Fix:** Eval retrieval sau inject cho `hits_forbidden=yes` trên `q_refund_window` — chứng minh chunk stale vẫn trong top-k. Pipeline đã prune 1 stale vector (`embed_prune_removed=1`) nhưng chunk stale mới (với chunk_id khác do text khác) vẫn được upsert.

**Evidence:** Log inject-bad:
```
expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1
WARN: expectation failed but --skip-validate → tiếp tục embed
embed_prune_removed=1
```

---

## Before/after

**Before (inject-bad):**
```
expectation[refund_no_stale_14d_window] FAIL :: violations=1
```

**After (clean-run-002):**
```
expectation[refund_no_stale_14d_window] OK :: violations=0
embed_prune_removed=1
grading gq_d10_01: contains_expected=true, hits_forbidden=false
```

Delta: 1 violation → 0 violation, grading PASS cả 3 câu.

---

## Cải tiến tiếp theo

1. **Đọc policy cutoff từ env/contract** thay vì hard-code `"2026-01-01"` trong `cleaning_rules.py` — hỗ trợ Distinction criterion (d).
2. **Thêm Great Expectations integration** — thay thế custom expectation runner bằng GE suite để có data profile + automated documentation (bonus +2).
