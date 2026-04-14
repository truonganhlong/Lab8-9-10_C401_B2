# Routing Decisions Log — Lab Day 09

**Nhóm:** C401_B2  
**Ngày:** 14/04/2026

> Dữ liệu lấy từ trace thật trong `artifacts/traces/` — run ngày 2026-04-14.

---

## Routing Decision #1

**Task đầu vào:**
> "Ticket P1 duoc tao luc 22:47. SLA deadline la khi nao va ai nhan thong bao?"

**Worker được chọn:** `retrieval_worker`  
**Route reason (từ trace):** `SLA/incident/helpdesk keyword detected: ['p1', 'sla', 'ticket'] → retrieval_worker`  
**MCP tools được gọi:** Không có (`mcp_tools_used: []`)  
**Workers called sequence:** `retrieval_worker → synthesis_worker`

**Kết quả thực tế:**
- final_answer (ngắn): "Ticket P1 lúc 22:47 có SLA deadline là 02:47 (4 giờ resolution). Thông báo gửi ngay tới Slack #incident-p1 và email incident@company.internal [sla_p1_2026.txt]."
- confidence: 0.34 (low — do retrieval trả về 3 chunks từ 3 tài liệu khác nhau, cosine score thấp)
- Correct routing? **Yes** — P1/SLA câu hỏi đúng là retrieval_worker

**Nhận xét:** Routing đúng. Supervisor detect được 3 keywords: `p1`, `sla`, `ticket`. Tuy nhiên confidence thấp vì ChromaDB trả về mixed chunks (sla + access_control + refund), không filter theo relevance cao. Cần cải thiện top-k retrieval hoặc re-ranker.

---

## Routing Decision #2

**Task đầu vào:**
> "Khach hang Flash Sale yeu cau hoan tien vi san pham loi -- duoc khong?"

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `policy/access keyword detected: ['hoan tien', 'flash sale'] → policy_tool_worker`  
**MCP tools được gọi:** `search_kb` (qua MCP client trong policy_tool.py)  
**Workers called sequence:** `policy_tool_worker → retrieval_worker → synthesis_worker`

**Kết quả thực tế:**
- final_answer (ngắn): "Không được hoàn tiền. Đơn hàng Flash Sale thuộc ngoại lệ theo Điều 3 chính sách hoàn tiền v4 — không được hoàn tiền dù sản phẩm lỗi [policy_refund_v4.txt]."
- confidence: 0.80 (cao — policy exception được xác định rõ)
- Correct routing? **Yes** — Flash Sale refund question đúng là policy_tool_worker

**Nhận xét:** Routing đúng. Policy worker detect được Flash Sale exception và trả về đúng kết quả. MCP `search_kb` được ghi vào `mcp_tools_used` trong trace. Synthesis worker nhận `exceptions_found` từ policy_result và ưu tiên rule này trong câu trả lời.

---

## Routing Decision #3

**Task đầu vào:**
> "Ticket P1 luc 2am. Can cap Level 2 access tam thoi cho contractor de thuc hien emergency fix. Dong thoi can notify stakeholders theo SLA. Neu du ca hai quy trinh."

**Worker được chọn:** `policy_tool_worker`  
**Route reason (từ trace):** `policy/access keyword detected: ['cap quyen', 'access level', 'level 2', 'contractor', 'tam thoi'] → policy_tool_worker | risk_high=True (emergency/contractor context)`  
**MCP tools được gọi:** `search_kb`, `check_access_permission`  
**Workers called sequence:** `policy_tool_worker → retrieval_worker → synthesis_worker`

**Kết quả thực tế:**
- final_answer (ngắn): "Hai quy trình song song: (1) SLA P1: Slack #incident-p1, PagerDuty, email ngay lập tức. Escalate Senior Engineer sau 10 phút không phản hồi. (2) Level 2 emergency access: IT Admin on-call cấp tạm thời max 24h sau Tech Lead approval. [sla_p1_2026.txt][access_control_sop.txt]"
- confidence: 0.52
- Correct routing? **Yes** — multi-hop query (SLA + access control) cần policy_tool_worker

**Nhận xét:** Đây là câu khó nhất (tương đương gq09/gq15). Supervisor detect được cả `risk_high=True` và route vào policy_tool_worker. Worker gọi 2 MCP tools, sau đó retrieval lấy thêm evidence từ 2 tài liệu khác nhau. Trace ghi rõ 2 workers được call (`policy_tool_worker`, `retrieval_worker`).

---

## Routing Decision #4 — Trường hợp routing khó (abstain)

**Task đầu vào:**
> "ERR-403-AUTH là lỗi gì và cách xử lý?"

**Worker được chọn:** `retrieval_worker`  
**Route reason:** `no specific policy or SLA keyword matched → default to retrieval_worker for general Q&A`

**Nhận xét: Đây là trường hợp routing khó nhất trong lab. Tại sao?**

Câu hỏi có mã lỗi `ERR-403-AUTH` nhưng KHÔNG có flag `risk_high` (pattern kiểm tra `err-` + `risk_high` để trigger `human_review`). Supervisor route về `retrieval_worker` (default). Retrieval không tìm được chunk nào liên quan trong 5 tài liệu. Synthesis worker nhận context rỗng và abstain đúng: "Không tìm thấy thông tin về mã lỗi ERR-403-AUTH trong tài liệu nội bộ." — đây là behavior đúng cho câu hỏi abstain.

---

## Tổng kết

### Routing Distribution

| Worker | Số câu được route | % tổng |
|--------|------------------|--------|
| retrieval_worker | 9 | 60% |
| policy_tool_worker | 6 | 40% |
| human_review | 0 | 0% |

*(Từ 15 test questions — q01–q15)*

### Routing Accuracy

> Trong 15 câu đã chạy, supervisor route đúng bao nhiêu?

- Câu route đúng: **13 / 15**
- Câu route sai: 2 câu (q02 và q05 được route retrieval_worker thay vì policy — vì câu hỏi bằng tiếng Việt thông thường không có từ khóa rõ ràng)
- Câu trigger HITL: 0

### Lesson Learned về Routing

> Quyết định kỹ thuật quan trọng nhất nhóm đưa ra về routing logic là gì?

1. **Keyword matching hai ngôn ngữ** — phải cover cả từ có dấu lẫn không dấu (vd: "hoan tien" và "hoàn tiền"). Thiếu một trong hai dẫn đến miss routing.
2. **Thứ tự ưu tiên routing** — `unknown+risk` > `policy` > `SLA` > `default`. Nếu không có thứ tự rõ ràng, câu hỏi multi-keyword sẽ bị route sai.

### Route Reason Quality

> Nhìn lại các `route_reason` trong trace — chúng có đủ thông tin để debug không?

`route_reason` hiện có format: `keyword_type keyword_list → worker_name`. Đủ để biết supervisor bắt được keyword nào. Tuy nhiên thiếu thông tin về keywords nào *không* match — thêm field `unmatched_hints` sẽ giúp debug routing miss cases nhanh hơn.
