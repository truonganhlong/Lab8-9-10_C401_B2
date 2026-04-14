# Single Agent vs Multi-Agent Comparison — Lab Day 09

**Nhóm:** C401_B2  
**Ngày:** 14/04/2026

> Dữ liệu thực tế từ:
> - Day 09: `python eval_trace.py` — 15 test questions, 18 trace files (do chạy nhiều lần)
> - Day 08 baseline: ước tính từ kết quả Day 08 eval.py (single-agent RAG pipeline)

---

## 1. Metrics Comparison

| Metric | Day 08 (Single Agent) | Day 09 (Multi-Agent) | Delta | Ghi chú |
|--------|----------------------|---------------------|-------|---------|
| Avg confidence | 0.72 (estimate) | **0.38** | −0.34 | Day 09 thấp hơn vì confidence đo từ chunk cosine score thực tế, không hard-code |
| Avg latency (ms) | ~2,500 | **~10,000** | +7,500ms | Multi-agent thêm 3 LLM/embedding calls vs 1 |
| Abstain rate (%) | ~5% | **~7%** | +2% | Day 09 abstain đúng hơn (q09 ERR-403-AUTH) |
| Multi-hop accuracy | ~40% | **~65%** | +25% | Supervisor route đúng cho q13, q15 — cross-doc |
| Routing visibility | ✗ Không có | ✓ Có route_reason | N/A | Trace rõ từng bước |
| Debug time (estimate) | ~20 phút | **~5 phút** | −15 phút | Có trace → xem supervisor_route ngay |
| Workers per query | 1 (monolith) | **2.1 avg** | +1.1 | policy path gọi thêm retrieval_worker |

> **Lưu ý:** Day 08 avg confidence 0.72 là từ single-agent RAG với ground-truth scoring. Day 09 confidence thấp hơn vì dùng cosine similarity thực tế, phản ánh chính xác hơn quality của retrieval.

---

## 2. Phân tích theo loại câu hỏi

### 2.1 Câu hỏi đơn giản (single-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | ~85% | ~80% |
| Latency | ~2,500ms | ~8,500ms |
| Observation | Trả lời nhanh, ít overhead | Có routing overhead nhưng trace rõ hơn |

**Kết luận:** Multi-agent KHÔNG cải thiện accuracy cho câu đơn giản. Latency cao hơn do thêm bước supervisor. Đây là trade-off rõ ràng nhất — với câu hỏi simple, single agent hiệu quả hơn.

### 2.2 Câu hỏi multi-hop (cross-document)

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Accuracy | ~40% | ~65% |
| Routing visible? | ✗ | ✓ |
| Observation | Không có cơ chế ưu tiên tài liệu — retrieve random | policy_tool_worker gọi search_kb 2 lần với query khác nhau; retrieval_worker lấy thêm evidence từ file thứ 2 |

**Kết luận:** Multi-agent cải thiện rõ ràng cho multi-hop. Câu q15 (SLA + access control) và q13 (Level 3 emergency) được giải quyết nhờ 2 workers phối hợp — điều Day 08 không thể làm.

### 2.3 Câu hỏi cần abstain

| Nhận xét | Day 08 | Day 09 |
|---------|--------|--------|
| Abstain rate | ~5% | ~7% |
| Hallucination cases | ~2 câu | ~1 câu |
| Observation | LLM có xu hướng "invent" answer khi không có context | Synthesis worker detect "không đủ thông tin" trong context → confidence = 0.2, trả lời abstain |

**Kết luận:** Day 09 abstain chính xác hơn nhờ confidence estimation thực sự — không hard-code.

---

## 3. Debuggability Analysis

### Day 08 — Debug workflow
```
Khi answer sai → phải đọc toàn bộ RAG pipeline code → tìm lỗi ở indexing/retrieval/generation
Không có trace → không biết bắt đầu từ đâu
Thời gian ước tính: ~20 phút
```

### Day 09 — Debug workflow
```
Khi answer sai → đọc trace → xem supervisor_route + route_reason
  → Nếu route sai → sửa supervisor routing logic (keyword sets)
  → Nếu retrieval sai → test retrieval_worker độc lập: python workers/retrieval.py
  → Nếu synthesis sai → test synthesis_worker độc lập: python workers/synthesis.py
Thời gian ước tính: ~5 phút
```

**Câu cụ thể nhóm đã debug:** Trong quá trình chạy, câu q03 ("Ai phê duyệt cấp quyền Level 3?") bị route sang `policy_tool_worker` nhưng policy_tool không gọi retrieval trước. Fix: thêm logic trong `build_graph()` — nếu `policy_tool_worker` chạy xong mà `retrieved_chunks` trống, gọi thêm `retrieval_worker`. Trace ngay sau đó cho thấy `workers_called: ['policy_tool_worker', 'retrieval_worker', 'synthesis_worker']`.

---

## 4. Extensibility Analysis

| Scenario | Day 08 | Day 09 |
|---------|--------|--------|
| Thêm 1 tool/API mới | Phải sửa toàn prompt | Thêm MCP tool trong `mcp_server.py` + 1 dòng routing rule |
| Thêm 1 domain mới | Phải retrain/re-prompt | Thêm keyword set mới trong `supervisor_node()` |
| Thay đổi retrieval strategy | Sửa trực tiếp trong pipeline | Sửa `retrieval_worker.py` độc lập, không đụng graph |
| A/B test một phần | Khó — phải clone toàn pipeline | Dễ — swap worker hoặc MCP tool |

**Nhận xét:**
Multi-agent có chi phí setup cao hơn (nhiều file, contracts yaml, trace format), nhưng khi cần mở rộng thì từng phần có thể swap độc lập. Day 08 nhanh hơn cho MVP nhưng "debt" khi scale.

---

## 5. Cost & Latency Trade-off

| Scenario | Day 08 calls | Day 09 calls |
|---------|-------------|-------------|
| Simple query (retrieval path) | 1 LLM call | 2 calls (synthesis) + 1 embedding |
| Complex query (policy path) | 1 LLM call | 3 calls (policy LLM + synthesis) + 2 embeddings |
| MCP tool call | N/A | +1 mock call (< 5ms overhead) |

**Nhận xét về cost-benefit:**

Day 09 tốn gấp 2–3x LLM calls so với Day 08 cho cùng 1 câu hỏi. Với gpt-4o-mini, chi phí này vẫn nhỏ (~$0.001/run). Nhưng với gpt-4o thì significant. Trade-off rõ ràng: accuracy + debuggability tốt hơn, đổi lấy latency cao hơn và cost cao hơn.

---

## 6. Kết luận

> **Multi-agent tốt hơn single agent ở điểm nào?**

1. **Multi-hop queries**: Cross-document reasoning tốt hơn rõ rệt (+25% accuracy) — nhờ supervisor route đúng và 2 workers phối hợp.
2. **Debuggability**: Từ trace có thể xác định root cause trong ~5 phút thay vì ~20 phút — mỗi bước đều ghi `route_reason` và `worker_io_logs`.

> **Multi-agent kém hơn hoặc không khác biệt ở điểm nào?**

1. **Simple queries**: Latency cao hơn 4x mà accuracy không tăng. Single agent đơn giản hơn và đủ dùng cho câu hỏi 1 tài liệu.

> **Khi nào KHÔNG nên dùng multi-agent?**

Khi tất cả các câu hỏi đều thuộc 1 domain, 1 tài liệu, và latency quan trọng hơn accuracy chi tiết. Ví dụ: chatbot FAQ đơn giản với < 10 documents.

> **Nếu tiếp tục phát triển hệ thống này, nhóm sẽ thêm gì?**

Thay keyword matching bằng LLM intent classifier — một LLM call nhỏ (gpt-4o-mini, temp=0) để classify intent thành `[retrieval, policy, human_review]` trước khi route. Từ trace thấy 2/15 câu bị miss do user viết không đúng keyword set.
