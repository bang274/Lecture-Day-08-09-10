# Quality report — Lab Day 10

**run_id:** final-run
**Ngày:** 2026-04-15

---

## 1. Tóm tắt số liệu

| Chỉ số | Trước | Sau | Ghi chú |
|--------|-------|-----|---------|
| raw_records | 10 | 10 | Từ `data/raw/policy_export_dirty.csv` |
| cleaned_records | — | 6 | Sau khi áp dụng 10 cleaning rules |
| quarantine_records | — | 4 | duplicate(1), unknown_doc_id(1), missing_effective_date(1), stale_hr(1) |
| Expectation halt? | — | Không | Tất cả 9 expectations PASS trên final-run |

**Inject-bad run (Sprint 3):** `cleaned_records=6`, `quarantine_records=4`, expectation `refund_no_stale_14d_window` **FAIL** (violations=1) → pipeline halt, nhưng `--skip-validate` cho phép tiếp tục embed.

---

## 2. Before / after retrieval (bắt buộc)

**Câu hỏi then chốt:** refund window (`q_refund_window`)

**Sau (final-run):**
```
question_id=q_refund_window
top1_doc_id=policy_refund_v4
contains_expected=yes
hits_forbidden=no
top1_preview="Yêu cầu được gửi trong vòng 7 ngày làm việc kể từ thời điểm xác nhận đơn hàng."
```

**Merit: versioning HR — `q_leave_version`:**
```
question_id=q_leave_version
top1_doc_id=hr_leave_policy
contains_expected=yes
hits_forbidden=no
top1_doc_expected=yes
top1_preview="Nhân viên dưới 3 năm kinh nghiệm được 12 ngày phép năm theo chính sách 2026."
```

**Trước (inject-bad-final — stale 14 ngày):** expectation `refund_no_stale_14d_window` FAIL (violations=1) → chunk chứa "14 ngày làm việc" vẫn được embed. Eval retrieval sẽ có `hits_forbidden=yes` vì top-k vẫn chứa chunk stale.

---

## 3. Freshness & monitor

**Kết quả:** `freshness_check=FAIL` (age=122.2h, SLA=24h)

**Giải thích:** CSV mẫu có `exported_at=2026-04-10T08:00:00` — cũ hơn 24h so với thời điểm run. Đây là **FAIL hợp lý** — đúng với kịch bản slide 3 Day 10: "data từ database công ty đột nhiên sai". Trong production, tôi sẽ:
1. Cập nhật `FRESHNESS_SLA_HOURS` cho phù hợp với tần suất sync thực tế
2. Hoặc trigger export mới từ source
3. Ghi trong runbook: SLA áp dụng cho "pipeline run" chứ không phải "data snapshot" cũ

---

## 4. Corruption inject (Sprint 3)

**Mô tả:** Chạy pipeline với `--no-refund-fix --skip-validate`:
- Không áp dụng rule fix 14→7 ngày
- Bỏ qua expectation halt
- Embed dữ liệu còn chunk stale "14 ngày làm việc"

**Cách phát hiện:**
- expectation `refund_no_stale_14d_window` FAIL (violations=1)
- Eval retrieval `q_refund_window` → `hits_forbidden=yes` (top-k chứa chunk stale)
- Grading `gq_d10_01` → `hits_forbidden=true` (trước fix)

**Sau fix (final-run):**
- expectation PASS (violations=0)
- Eval `q_refund_window` → `hits_forbidden=no`
- Grading `gq_d10_01` → `hits_forbidden=false`, `contains_expected=true`

---

## 5. Hạn chế & việc chưa làm

- Chưa tích hợp Great Expectations library (bonus +2)
- Freshness chỉ đo tại 1 boundary (publish) — chưa đo ingest boundary (bonus +1)
- Chưa mở rộng thêm source API thật (chỉ mock CSV)
- Eval retrieval dùng keyword-based — chưa dùng LLM-judge
