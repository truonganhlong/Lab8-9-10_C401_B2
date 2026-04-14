# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Lê Thành Long  
**MSSV:** 2A202600105  
**Vai trò trong nhóm:** Tech Lead  
**Ngày nộp:** 14/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào? (100–150 từ)

Tôi đảm nhận vai trò **Tech Lead**, chịu trách nhiệm xuyên suốt cả 4 Sprint.

**Module/file tôi chịu trách nhiệm:**
- File chính: `contracts/worker_contracts.yaml` — định nghĩa I/O schema, routing rules, constraints cho toàn bộ supervisor và workers
- Setup project: `.env`, `.env.example`, `requirements.txt`, cấu trúc thư mục, API keys (OpenAI, Jina)
- Review và phê duyệt Pull Request từ tất cả Sprint 1–4
- Thiết kế kiến trúc tổng thể: chọn pattern Supervisor-Worker, quy định mỗi worker là stateless function `run(state) -> state`

**Cách công việc của tôi kết nối với phần của thành viên khác:**

`worker_contracts.yaml` là "bản hợp đồng" chung mà cả 4 Sprint phải tuân theo. Tôi quy định rõ input/output schema cho từng worker — nếu contract thiếu field `mcp_tools_used` hoặc sai type `retrieved_chunks`, toàn bộ workers sẽ implement sai và crash `KeyError` khi integration. API keys và `.env` do tôi cung cấp — thiếu key thì không ai chạy được pipeline.

**Bằng chứng:**
- File `contracts/worker_contracts.yaml` version 1.0, updated 2026-04-13
- Quản lý PR merges trên repo `truonganhlong/Lab8_C401_B2`

---

## 2. Tôi đã ra một quyết định kỹ thuật gì? (150–200 từ)

**Quyết định:** Chọn kiến trúc **Supervisor-Worker bằng Python thuần** (if/else orchestrator) thay vì dùng LangGraph StateGraph.

**Các lựa chọn đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Python thuần (đã chọn) | Zero dependency thêm, debug bằng `print()`, mọi thành viên đọc hiểu ngay | Không có graph visualization, phải tự quản lý flow |
| LangGraph StateGraph | Visualization đẹp, conditional edges khai báo rõ, hỗ trợ `interrupt_before` cho HITL | Thêm dependency, learning curve cho cả nhóm, debug khó hơn |

**Lý do chọn Python thuần:**

Nhóm có 5 người làm song song 4 Sprint, mỗi Sprint là 1 module riêng biệt. Nếu dùng LangGraph, Sprint 2 (Worker Owner) phải hiểu cách LangGraph compile graph trước khi test worker — tạo bottleneck. Với Python thuần, tôi quy định mỗi worker chỉ cần implement đúng hàm `run(state) -> state` theo contract, rồi Sprint 1 kết nối các worker trong `build_graph()` bằng if/else đơn giản. Điều này giúp cả nhóm chạy song song mà không block nhau.

**Bằng chứng từ contract** (`worker_contracts.yaml`):

```yaml
supervisor:
  constraints:
    - "Supervisor không được tự trả lời policy questions"
    - "route_reason KHÔNG được là chuỗi rỗng hoặc 'unknown'"
    - "Nếu risk_high=True → luôn ghi lý do cụ thể"
```

Contract quy định rõ ranh giới: "Supervisor giữ quyết định luồng. Worker giữ domain skill." — giúp 4 người implement song song mà không đụng chạm code nhau.

**Trade-off chấp nhận:** Không có graph visualization và `interrupt_before` cho HITL — chấp nhận dùng placeholder trong lab scope.

---

## 3. Tôi đã sửa một lỗi gì? (150–200 từ)

**Lỗi:** **Dimension mismatch** giữa embedding models khi index và query ChromaDB → retrieval trả về 0 kết quả hoặc crash.

**Symptom:** Khi integration test, `search_kb` liên tục trả `total_found: 0` hoặc ChromaDB báo lỗi dimension mismatch. Pipeline chạy qua retrieval nhưng không lấy được chunk nào, Synthesis luôn trả "Không đủ thông tin".

**Root cause:** Ban đầu ChromaDB được index bằng model embedding có dimension 512. Khi Sprint 2 dùng SentenceTransformer (`all-MiniLM-L6-v2`, dimension 384) để query, ChromaDB từ chối vì vector dimension không khớp. Đồng thời, `.env` thiếu config `OPENAI_API_KEY` dẫn đến `synthesis.py` không gọi được LLM — lỗi kép khiến pipeline trả kết quả rỗng toàn bộ.

**Cách sửa:**

1. Chuẩn hóa toàn nhóm dùng **Jina Embeddings v5** (`jina-embeddings-v5-text-small`, dimension 1024) — cả index lẫn query đều dùng chung 1 model thông qua API
2. Xóa ChromaDB collection cũ, index lại toàn bộ 5 tài liệu với Jina
3. Cấu hình đầy đủ `.env` với `JINA_API_KEY` và `OPENAI_API_KEY`, đảm bảo mọi máy thành viên đều chạy được

**Bằng chứng trước/sau:**
- Trước fix: `search_kb` → `total_found: 0`, dimension mismatch error
- Sau fix: trace `run_20260414_194509.json` → `total_found: 3`, sources: `['access_control_sop.txt', 'sla_p1_2026.txt', 'hr_leave_policy.txt']`

**Lesson learned:** Khi nhiều Sprint cùng dùng chung vector DB, Tech Lead phải chuẩn hóa embedding model từ đầu trong contract — không để mỗi người tự chọn model riêng.

---

## 4. Tự đánh giá (100–150 từ)

**Tôi làm tốt nhất ở điểm nào?**

Thiết kế contract và kiến trúc rõ ràng ngay từ đầu — `worker_contracts.yaml` giúp 4 Sprint implement song song mà không đụng chạm code của nhau, giảm merge conflict xuống gần 0. Chuẩn hóa embedding model (Jina v5) giúp loại bỏ hoàn toàn lỗi dimension mismatch sau khi fix.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**

Chưa enforce contract bằng code (ví dụ Pydantic validation). Hiện tại contract chỉ là file YAML mô tả — nếu worker trả sai field name, chỉ phát hiện khi chạy trace. Lẽ ra nên dùng Pydantic BaseModel để validate state ở runtime.

**Nhóm phụ thuộc vào tôi ở đâu?**

`worker_contracts.yaml` — nếu contract sai, cả 4 Sprint implement sai. `.env` với API keys — thiếu key thì hệ thống không chạy. Review PR — nếu tôi không review kịp, code không merge được vào main.

**Phần tôi phụ thuộc vào thành viên khác:**

Tôi cần Sprint 1–4 hoàn thành đúng contract để integration test pass. Đặc biệt phụ thuộc vào Sprint 4 (Lã Thị Linh) để có trace data cho group report.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì? (50–100 từ)

Tôi sẽ thay thế `AgentState` TypedDict bằng **Pydantic BaseModel** với strict validation. Từ trace, câu `q10` bị route sai vì `route_reason` trả chuỗi rỗng — vi phạm constraint trong `worker_contracts.yaml` ("route_reason KHÔNG được là chuỗi rỗng"). Nếu dùng Pydantic với `@validator`, lỗi này sẽ bị bắt ngay tại runtime thay vì chờ đến khi phân tích trace mới phát hiện. Ước tính: +2 giờ refactor, nhưng tiết kiệm debug time cho cả nhóm ở mọi sprint sau.

---

*Lưu file này với tên: `reports/individual/LeThanhLong_2A202600105.md`*
