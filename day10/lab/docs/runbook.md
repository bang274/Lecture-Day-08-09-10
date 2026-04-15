# Runbook — Lab Day 10 (incident tối giản)

---

## Symptom

> **Trường hợp thực tế:** User hỏi "Hoàn tiền trong bao lâu?" → Agent trả lời "14 ngày làm việc" (sai — policy hiện hành là **7 ngày**).

Hoặc: Agent trả lời "10 ngày phép năm" cho nhân viên mới (sai — policy 2026 là **12 ngày**).

---

## Detection

| Metric | Threshold | Alert type |
|--------|-----------|------------|
| `freshness_check` | age > SLA (24h) | WARN/FAIL trên log |
| `eval hits_forbidden` | `hits_forbidden=yes` trên `q_refund_window` | Retrieval quality gate fail |
| `expectation refund_no_stale_14d_window` | FAIL + halt | Pipeline halt |
| `grading gq_d10_01` | `hits_forbidden=true` | Grading fail |

**Phát hiện sớm:** Chạy `python eval_retrieval.py --out artifacts/eval/before_after_eval.csv` sau mỗi pipeline run.

---

## Diagnosis

| Bước | Việc làm | Kết quả mong đợi |
|------|----------|------------------|
| 1 | Kiểm tra `artifacts/manifests/manifest_*.json` — xem `no_refund_fix` flag | `no_refund_fix=false` (đã áp dụng fix) |
| 2 | Mở `artifacts/quarantine/*.csv` — tìm `reason=stale_hr_policy_effective_date` | HR cũ (10 ngày) bị quarantine |
| 3 | Chạy `python eval_retrieval.py` — xem `q_refund_window` row | `contains_expected=yes`, `hits_forbidden=no` |
| 4 | Kiểm tra log: `expectation[refund_no_stale_14d_window] OK` | Không còn chunk 14 ngày trong cleaned |
| 5 | Kiểm tra ChromaDB: `col.get()` — đếm vector count | Count khớp `cleaned_records` trong manifest |

**Lệnh nhanh:**
```bash
# Xem log run mới nhất
ls -lt artifacts/logs/ | head -1

# Xem manifest
cat artifacts/manifests/manifest_*.json | python -m json.tool

# Check eval
cat artifacts/eval/before_after_eval.csv | grep q_refund
```

---

## Mitigation

| Tình huống | Hành động |
|------------|-----------|
| Pipeline halt do expectation fail | Fix data source → rerun `python etl_pipeline.py run` |
| Eval `hits_forbidden=yes` | Kiểm tra chunk stale trong DB → xóa manual khỏi ChromaDB → rerun pipeline |
| Freshness FAIL (>24h) | Trigger export mới từ source → cập nhật `FRESHNESS_SLA_HOURS` nếu hợp lý |
| Agent vẫn trả lời sai sau fix | Kiểm tra collection Day 09 có đang trỏ sang `day10_kb` không — nếu không, update config |

**Rollback nhanh (tạm thời):**
```bash
# Banner "data stale" trên UI agent
# Rerun pipeline với run-id rõ ràng
python etl_pipeline.py run --run-id hotfix-$(date +%H%M)
python eval_retrieval.py --out artifacts/eval/hotfix_eval.csv
```

---

## Prevention

| Việc làm | Owner | Tần suất |
|----------|-------|----------|
| Thêm expectation `refund_no_stale_14d_window` | Cleaning & Quality | Một lần trong code |
| Freshness SLA alert (#ai-pipeline-alerts) | Monitoring / Docs | Liên tục (cron check manifest) |
| Golden question eval (`test_questions.json`) | Embed Owner | Mỗi lần pipeline run |
| Review quarantine CSV | Cleaning & Quality | Hàng tuần hoặc sau mỗi incident |
| Data contract version bump | Ingestion Owner | Khi có policy change |

**Liên hệ Day 11 (guardrail):** Tự động hóa freshness check trong CI/CD — pipeline không deploy nếu `freshness_check=FAIL` hoặc `hits_forbidden=yes` trên golden questions.
