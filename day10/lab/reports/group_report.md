# Báo Cáo Lab Day 10: Data Pipeline & Data Observability

**Sinh viên:** Tran Khanh Bang
**Mã số:** AI20K-274
**Ngày nộp:** 2026-04-15
**Repo:** Obsidian/Lecture-Day-08-09-10/day10/lab/

---

## 1. Pipeline tổng quan

Nguồn raw là CSV export mẫu `data/raw/policy_export_dirty.csv` mô phỏng dữ liệu từ policy DB — gồm 10 rows có duplicate, missing date, stale HR version, unknown doc_id, và refund window sai (14→7 ngày).

**Tóm tắt luồng:**
```
raw CSV → load_raw_csv → clean_rows (10 rules) → run_expectations (9 checks)
  → embed ChromaDB (upsert + prune) → manifest.json → freshness_check
```

**Lệnh chạy một dòng:**
```bash
python etl_pipeline.py run --run-id final-run
```

**Run-id trong log:** `final-run` → file log `artifacts/logs/run_final-run.log` ghi đầy đủ `raw_records=10`, `cleaned_records=6`, `quarantine_records=4`, và kết quả 9 expectations.

---

## 2. Cleaning & expectation

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| R7: Quarantine PII (email/phone) | 0 rows bị quarantine | Khi thêm row có email → quarantine_records+1 | `artifacts/quarantine/quarantine_final-run.csv` |
| R8: Normalize whitespace | chunk_text giữ nguyên | Whitespace ≥3 spaces → chuẩn hóa, dedup hoạt động chính xác hơn | `_normalize_whitespace()` trong `cleaning_rules.py` |
| R9: Validate exported_at | ISO sẵn | DD/MM/YYYY format → normalize ISO, hỗ trợ freshness | `_normalize_exported_at()` |
| R10: Quarantine chunk>2000 chars | 0 rows | Khi thêm chunk dài → quarantine_records+1 | `chunk_too_long` reason trong quarantine CSV |
| E7: exported_at_present | PASS (0 missing) | Nếu xóa exported_at → `missing_exported_at=N`, warn | Log: `expectation[exported_at_present]` |
| E8: chunk_id_unique | PASS (0 duplicate) | Nếu duplicate → halt pipeline | Log: `expectation[chunk_id_unique]` |
| E9: doc_id_distribution_balanced | PASS (33.33% top ratio) | Nếu 1 doc chiếm >80% → warn | Log: `expectation[doc_id_distribution_balanced]` |

**Rule chính (baseline + mở rộng):**

- Baseline (6): allowlist doc_id, normalize date, quarantine stale HR, quarantine empty text, dedup, fix refund 14→7
- Mới thêm (4): PII quarantine, whitespace normalize, exported_at validate, chunk length cap

**Ví dụ 1 lần expectation fail và cách xử lý:**

Inject-bad run (`--no-refund-fix --skip-validate`): `expectation[refund_no_stale_14d_window] FAIL (halt) :: violations=1`. Pipeline trả về exit code 0 do `--skip-validate` nhưng log ghi `WARN: expectation failed but --skip-validate → tiếp tục embed`. Eval retrieval sau đó cho `hits_forbidden=yes` trên `q_refund_window` — chứng minh dữ liệu xấu ảnh hưởng retrieval.

---

## 3. Before / after ảnh hưởng retrieval hoặc agent

**Kịch bản inject:** Chạy `python etl_pipeline.py run --run-id inject-bad-final --no-refund-fix --skip-validate` — cố ý không fix refund window, bỏ qua expectation halt để embed chunk stale "14 ngày làm việc".

**Kết quả định lượng (từ grading JSONL):**

| Câu | contains_expected | hits_forbidden | top1_doc_matches |
|-----|-------------------|----------------|-----------------|
| gq_d10_01 (refund: 7 ngày) | ✅ true | ✅ false | N/A |
| gq_d10_02 (SLA: 4h resolution) | ✅ true | ✅ false | N/A |
| gq_d10_03 (HR leave: 12 ngày) | ✅ true | ✅ false | ✅ true |

**Trước (inject-bad-final):** Chunk stale "14 ngày làm việc" còn trong index → eval `q_refund_window` có `hits_forbidden=yes` (top-k chứa forbidden text).

**Sau (final-run):** Refund đã fix thành "7 ngày làm việc" → `hits_forbidden=no`, `contains_expected=yes`. HR leave policy đúng version 2026 (12 ngày) → `top1_doc_expected=yes`. SLA P1 resolution 4 giờ được retrieve đúng.

**Evidence files:**
- `artifacts/eval/final_eval.csv` — 4 golden questions, tất cả PASS
- `artifacts/eval/final_grading.jsonl` — 3 grading questions, tất cả đúng criteria
- `artifacts/logs/run_inject-bad-final.log` — expectation FAIL + embed prune (1 stale vector removed)

---

## 4. Freshness & monitoring

**SLA chọn:** `FRESHNESS_SLA_HOURS=24` — dữ liệu phải được export trong vòng 24h.

**Kết quả:** `freshness_check=FAIL` (age=122.2h) — hợp lý vì CSV mẫu có `exported_at=2026-04-10`. Đây là **tính năng** của lab: dạy sinh viên nhận diện stale data trước khi debug model/prompt.

**Trong production:** Tôi sẽ (1) tăng `FRESHNESS_SLA_HOURS` cho phù hợp tần suất sync thực tế, hoặc (2) trigger export mới, và (3) ghi trong runbook: SLA đo tại "publish boundary" (sau embed) chứ không phải "ingest start".

---

## 5. Liên hệ Day 09

Pipeline Day 10 cung cấp corpus đã qua quality gate cho multi-agent Day 09. Collection `day10_kb` có thể thay thế hoặc bổ sung cho retrieval worker trong supervisor-Workers architecture. Khi policy thay đổi, chỉ cần rerun `etl_pipeline.py run` → index tự động cập nhật (idempotent upsert + prune), đảm bảo Day 09 agent luôn retrieval trên dữ liệu đúng version.

---

## 6. Rủi ro còn lại & việc chưa làm

- Chưa đo freshness ở 2 boundary (ingest + publish) — bonus +1
- Chưa tích hợp Great Expectations library — bonus +2
- Eval retrieval chỉ dùng keyword, chưa có LLM-judge
- Chưa test với API ingestion thật (chỉ mock CSV)
- Chưa có queue/backpressure/DLQ implementation (chỉ mô tả trong architecture doc)
