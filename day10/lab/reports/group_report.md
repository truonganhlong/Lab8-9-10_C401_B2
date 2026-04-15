# Báo Cáo Nhóm — Lab Day 10: Data Pipeline & Data Observability

**Tên nhóm:** ___________  
**Thành viên:**
| Tên | Vai trò (Day 10) | Email |
|-----|------------------|-------|
| ___ | Ingestion / Raw Owner | ___ |
| ___ | Cleaning & Quality Owner | ___ |
| ___ | Embed & Idempotency Owner | ___ |
| ___ | Monitoring / Docs Owner | ___ |

**Ngày nộp:** ___________  
**Repo:** ___________  
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Nộp tại:** `reports/group_report.md`  
> **Deadline commit:** xem `SCORING.md` (code/trace sớm; report có thể muộn hơn nếu được phép).  
> Phải có **run_id**, **đường dẫn artifact**, và **bằng chứng before/after** (CSV eval hoặc screenshot).

---

## 1. Pipeline tổng quan (150–200 từ)

> Nguồn raw là gì (CSV mẫu / export thật)? Chuỗi lệnh chạy end-to-end? `run_id` lấy ở đâu trong log?

**Tóm tắt luồng:**

_________________

**Lệnh chạy một dòng (copy từ README thực tế của nhóm):**

_________________

---

## 2. Cleaning & expectation (150–200 từ)

> Baseline đã có nhiều rule (allowlist, ngày ISO, HR stale, refund, dedupe…). Nhóm thêm **≥3 rule mới** + **≥2 expectation mới**. Khai báo expectation nào **halt**.

### 2a. Bảng metric_impact (bắt buộc — chống trivial)

| Rule / Expectation mới (tên ngắn) | Trước (số liệu) | Sau / khi inject (số liệu) | Chứng cứ (log / CSV / commit) |
|-----------------------------------|------------------|-----------------------------|-------------------------------|
| `stale_source_marker` | `manifest_smoke-provider.json`: `cleaned=6`, `quarantine=4` | `manifest_sprint2-sample.json`: `cleaned=5`, `quarantine=5` | `artifacts/quarantine/quarantine_sprint2-sample.csv` có thêm reason `stale_source_marker` |
| `invalid_exported_at_format` | Trước probe chưa có guard cho timestamp lỗi | `run_id=sprint2-probe`: 1 row bị quarantine vì `invalid_exported_at_format` | `artifacts/quarantine/quarantine_sprint2-probe.csv` dòng `chunk_id=103` |
| `effective_date_after_exported_at` | Trước probe chưa chặn timeline ngược | `run_id=sprint2-probe`: 1 row bị quarantine vì `effective_date_after_exported_at` | `artifacts/quarantine/quarantine_sprint2-probe.csv` dòng `chunk_id=104` |
| `refund_single_active_chunk` (expectation halt) | Sample cũ còn 2 row `policy_refund_v4` active sau clean | `run_id=sprint2-sample`: log `active_refund_rows=1` và expectation `OK (halt)` | `artifacts/logs/run_sprint2-sample.log` |

**Rule chính (baseline + mở rộng):**

- Baseline 6 rule cũ vẫn giữ nguyên: allowlist `doc_id`, normalize `effective_date`, quarantine HR stale, quarantine `chunk_text` rỗng, dedupe, fix refund `14 -> 7`.
- Sprint 2 bổ sung 3 rule mới có impact đo được: validate `exported_at`, chặn `effective_date > exported_at`, và quarantine stale marker như `bản sync cũ` / `lỗi migration`.
- Expectation mới bám vào rule mới gồm `exported_at_iso_datetime`, `no_stale_source_markers`, `effective_date_not_after_exported_at`, và `refund_single_active_chunk`.

**Ví dụ 1 lần expectation fail (nếu có) và cách xử lý:**

Nếu bỏ rule `stale_source_marker`, sample refund cũ vẫn có thể đi vào cleaned dataset và expectation `refund_single_active_chunk` sẽ fail vì còn hơn 1 chunk active cho `policy_refund_v4`. Sau khi quarantine row stale ở `run_id=sprint2-sample`, log chuyển sang `expectation[refund_single_active_chunk] OK (halt) :: active_refund_rows=1`.

---

## 3. Before / after ảnh hưởng retrieval hoặc agent (200–250 từ)

> Bắt buộc: inject corruption (Sprint 3) — mô tả + dẫn `artifacts/eval/…` hoặc log.

**Kịch bản inject:**

_________________

**Kết quả định lượng (từ CSV / bảng):**

_________________

---

## 4. Freshness & monitoring (100–150 từ)

> SLA bạn chọn, ý nghĩa PASS/WARN/FAIL trên manifest mẫu.

_________________

---

## 5. Liên hệ Day 09 (50–100 từ)

> Dữ liệu sau embed có phục vụ lại multi-agent Day 09 không? Nếu có, mô tả tích hợp; nếu không, giải thích vì sao tách collection.

_________________

---

## 6. Rủi ro còn lại & việc chưa làm

- …
