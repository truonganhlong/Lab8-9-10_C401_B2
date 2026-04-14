# System Architecture — Lab Day 09

**Nhóm:** C401_B2  
**Ngày:** 14/04/2026  

---

## 1. Tổng quan kiến trúc

**Pattern đã chọn:** Supervisor-Worker (Python thuần, không dùng LangGraph)

**Lý do chọn pattern này (thay vì single agent):**

Day 08 dùng một RAG pipeline đơn khối: retrieve → generate nằm trong một hàm duy nhất. Khi pipeline trả lời sai, không thể xác định lỗi nằm ở bước nào — retrieval sai hay LLM hallucinate. Supervisor-Worker tách bạch trách nhiệm: Supervisor chỉ ra quyết định *route nào*, mỗi Worker làm đúng *một việc*. Kết quả: có thể test từng worker độc lập, trace ghi rõ từng bước, dễ debug và mở rộng.

---

## 2. Sơ đồ Pipeline

**Sơ đồ thực tế của nhóm:**

```
User Request (task)
      │
      ▼
┌─────────────────────┐
│     Supervisor      │  ← Keyword matching: POLICY_KEYWORDS, SLA_KEYWORDS, RISK_KEYWORDS
│   (graph.py)        │  → ghi: supervisor_route, route_reason, risk_high, needs_tool
└──────────┬──────────┘
           │ route_decision()
     ┌─────┴──────────────────────────────┐
     │             │                      │
     ▼             ▼                      ▼
retrieval_worker  policy_tool_worker   human_review
 (SLA/helpdesk)   (refund/access/MCP)  (unknown error
                                        + risk_high)
     │             │
     │    ┌────────┤ (nếu không có chunks: gọi thêm retrieval)
     │    │        │
     └────┴────────┘
                 │
                 ▼
       ┌──────────────────┐
       │ Synthesis Worker │  ← LLM: gpt-4o-mini, grounded prompt
       │ (synthesis.py)   │  → ghi: final_answer, sources, confidence
       └────────┬─────────┘
                │
                ▼
         Output + Trace (artifacts/traces/)
```

---

## 3. Vai trò từng thành phần

### Supervisor (`graph.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Phân tích task, quyết định route sang worker nào, detect risk flag |
| **Input** | `task` (câu hỏi từ user) |
| **Output** | `supervisor_route`, `route_reason`, `risk_high`, `needs_tool` |
| **Routing logic** | Keyword matching ưu tiên: UNKNOWN+risk → human_review; POLICY_KEYWORDS → policy_tool_worker; SLA_KEYWORDS → retrieval_worker; default → retrieval_worker |
| **HITL condition** | Khi task có mã lỗi không rõ (err-, bug-) VÀ `risk_high=True` |

### Retrieval Worker (`workers/retrieval.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Embed query → query ChromaDB → trả top-k chunks có bằng chứng |
| **Embedding model** | `all-MiniLM-L6-v2` (local, 384 dims) / Jina v5 nếu có API key |
| **Top-k** | 3 (mặc định, cấu hình qua `retrieval_top_k` trong state) |
| **Stateless?** | Yes — nhận state, trả state, không giữ internal state |

### Policy Tool Worker (`workers/policy_tool.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **Nhiệm vụ** | Kiểm tra policy, detect exception cases, gọi MCP tools |
| **MCP tools gọi** | `search_kb`, `get_ticket_info`, `check_access_permission` |
| **Exception cases xử lý** | Flash Sale exception, digital product exception, temporal scoping (đơn trước effective date) |

### Synthesis Worker (`workers/synthesis.py`)

| Thuộc tính | Mô tả |
|-----------|-------|
| **LLM model** | `gpt-4o-mini` (cấu hình qua `LLM_MODEL` trong .env) |
| **Temperature** | 0.1 (minimize hallucination) |
| **Grounding strategy** | Chỉ dùng evidence từ `retrieved_chunks` + `policy_result`; system prompt yêu cầu cite nguồn |
| **Abstain condition** | Khi context trống hoặc LLM trả lời "không đủ thông tin" → confidence = 0.2 |

### MCP Server (`mcp_server.py`)

| Tool | Input | Output |
|------|-------|--------|
| `search_kb` | `query`, `top_k` | `chunks`, `sources` |
| `get_ticket_info` | `ticket_id` | ticket details (mock) |
| `check_access_permission` | `access_level`, `requester_role` | `can_grant`, `approvers` |

---

## 4. Shared State Schema

| Field | Type | Mô tả | Ai đọc/ghi |
|-------|------|-------|-----------| 
| `task` | str | Câu hỏi đầu vào | supervisor đọc |
| `supervisor_route` | str | Worker được chọn (`retrieval_worker` / `policy_tool_worker` / `human_review`) | supervisor ghi |
| `route_reason` | str | Lý do route, có keyword matched | supervisor ghi |
| `risk_high` | bool | True nếu task có emergency/contractor context | supervisor ghi |
| `needs_tool` | bool | True nếu policy_tool_worker cần gọi MCP | supervisor ghi |
| `retrieved_chunks` | list | Evidence từ retrieval: `{text, source, score, metadata}` | retrieval ghi, synthesis đọc |
| `retrieved_sources` | list | Danh sách tên file nguồn | retrieval ghi, synthesis đọc |
| `policy_result` | dict | Kết quả kiểm tra policy + exceptions | policy_tool ghi, synthesis đọc |
| `mcp_tools_used` | list | Tool calls với `{tool, input, output, timestamp}` | policy_tool ghi |
| `final_answer` | str | Câu trả lời cuối với citation | synthesis ghi |
| `confidence` | float | 0.0–1.0 — tính từ avg chunk score + abstain check | synthesis ghi |
| `hitl_triggered` | bool | True nếu HITL node được kích hoạt | human_review ghi |
| `workers_called` | list | Sequence các workers đã chạy | mỗi worker append |
| `latency_ms` | int | Tổng thời gian chạy (ms) | graph ghi sau khi kết thúc |

---

## 5. Lý do chọn Supervisor-Worker so với Single Agent (Day 08)

| Tiêu chí | Single Agent (Day 08) | Supervisor-Worker (Day 09) |
|----------|----------------------|--------------------------|
| Debug khi sai | Không rõ lỗi ở đâu — phải đọc toàn pipeline | Xem trace → `route_reason` → test worker độc lập |
| Thêm capability mới | Phải sửa toàn bộ prompt hoặc pipeline | Thêm MCP tool hoặc worker mới — không đụng core |
| Routing visibility | Không có — black box | `supervisor_route` + `route_reason` trong mỗi trace |
| Test độc lập | Không thể test từng bước | Mỗi worker có `__main__` test block riêng |
| Multi-hop queries | Một hàm phải handle tất cả | Supervisor có thể gọi 2 workers tuần tự |

**Quan sát từ thực tế lab:**

- Câu `q15` (multi-hop: SLA + access control) được route đúng sang `policy_tool_worker`, gọi thêm `retrieval_worker` để lấy context từ 2 tài liệu khác nhau.
- Câu `q09` (ERR-403-AUTH abstain) được retrieval_worker trả về chunks không liên quan, synthesis worker tự động nhận ra context không đủ và trả về abstain response.

---

## 6. Giới hạn và điểm cần cải tiến

1. **Routing dựa vào keyword** — dễ miss edge case khi user viết không đúng từ khóa (ví dụ viết tiếng Việt không dấu). Cải tiến: dùng LLM classifier hoặc embedding similarity để classify intent.
2. **ChromaDB embedding dimension** — nếu Jina API key có sẵn thì dùng 1024 dims, local fallback dùng 384 dims, hai cái không tương thích → cần chuẩn hóa dimension một lần.
3. **Confidence score chưa calibrated** — hiện tính từ avg cosine similarity của chunks, chưa phản ánh chất lượng câu trả lời thực sự.
