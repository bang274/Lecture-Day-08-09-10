# Data contract — Lab Day 10

> Bắt đầu từ `contracts/data_contract.yaml` — mở rộng và đồng bộ file này.

---

## 1. Nguồn dữ liệu (source map)

| Nguồn | Phương thức ingest | Failure mode chính | Metric / alert |
|-------|-------------------|-------------------|----------------|
| Policy DB (PostgreSQL) | Batch CSV export qua cron 02:00 UTC | Export stale, migration lỗi (14→7 ngày) | `freshness_check` FAIL, `refund_no_stale_14d_window` expectation |
| HR Policy PDF | Parser → text extract | Version conflict (10 vs 12 ngày phép), OCR lỗi | `stale_hr_policy_effective_date` quarantine reason |
| IT Helpdesk CMS | REST API (pagination + rate limit) | 429 Too Many Requests, partial JSON | Retry-Backoff-Jitter, DLQ cho partial response |
| Access Control SOP | Static file trong `data/docs/` | File cũ không được cập nhật | Content hash check + `effective_date` metadata |

**Ingest risk summary:** 4 sources, 2 batch (CSV + static file), 1 API, 1 parser (PDF). Priority monitor: **Freshness SLA** trên policy DB export — ảnh hưởng trực tiếp đến refund policy correctness.

---

## 2. Schema cleaned

| Cột | Kiểu | Bắt buộc | Ghi chú |
|-----|------|----------|---------|
| chunk_id | string | Có | SHA-256 hash 16 ký tự: `doc_id\|chunk_text\|seq` |
| doc_id | string | Có | Must be in `ALLOWED_DOC_IDS` allowlist |
| chunk_text | string | Có | Min 8 chars, Max 2000 chars, no PII |
| effective_date | date | Có | ISO 8601 `YYYY-MM-DD`, chuẩn hóa từ DD/MM/YYYY |
| exported_at | datetime | Có | ISO 8601, dùng cho freshness tracking |

---

## 3. Quy tắc quarantine vs drop

| Reason | Action | Severity |
|--------|--------|----------|
| `unknown_doc_id` | Quarantine | halt (không cho vào cleaned) |
| `missing_effective_date` | Quarantine | halt |
| `invalid_effective_date_format` | Quarantine | halt |
| `stale_hr_policy_effective_date` | Quarantine | halt |
| `missing_chunk_text` | Quarantine | halt |
| `contains_pii` | Quarantine | halt — security risk |
| `chunk_too_long` | Quarantine | halt — embedding quality |
| `duplicate_chunk_text` | Quarantine | warn — giữ bản đầu tiên |

**Quarantine destination:** `artifacts/quarantine/quarantine_<run-id>.csv` — file này được review bởi Cleaning Owner trước khi merge lại hoặc delete permanent.

**Không có silent drop:** mọi row bị loại đều được ghi vào quarantine với `reason` field — đảm bảo lineage.

---

## 4. Phiên bản & canonical

| Policy | Source of truth | Version hiện tại | Cutoff |
|--------|----------------|------------------|--------|
| Refund window | `data/docs/policy_refund_v4.txt` | v4 = **7 ngày làm việc** | Bản v3 (14 ngày) là stale |
| SLA P1 | `data/docs/sla_p1_2026.txt` | 2026 = 15 phút response | — |
| HR Leave | `data/docs/hr_leave_policy.txt` | 2026 = **12 ngày phép năm** | `effective_date < 2026-01-01` = stale |
| IT FAQ | `data/docs/it_helpdesk_faq.txt` | Current | — |
| Access SOP | `data/docs/access_control_sop.txt` | Current | — |

**Versioning strategy:** `effective_date` dùng làm version boundary — không hard-code ngày trong code mà đọc từ `contracts/data_contract.yaml` (`policy_versioning.hr_leave_min_effective_date`).
