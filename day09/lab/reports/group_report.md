# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** C401_B2
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Đỗ Xuân Bằng | Supervisor Owner (Sprint 1) | doxuanbang14122005@gmail.com |
| Đỗ Việt Anh | Worker Owner (Sprint 2) | vietanh201004@gmail.com |
| Trương Anh Long | MCP Owner (Sprint 3) | truonganhlong.1209@gmail.com |
| Lã Thị Linh | Trace & Docs Owner (Sprint 4) | lalinhkhmt@gmail.com |
| Lê Thành Long | Tech Lead | lethanhlong9a1819@gmail.com |

**Ngày nộp:** 14/04/2026
**Repo:** [truonganhlong/Lab8_C401_B2](https://github.com/truonganhlong/Lab8_C401_B2)
**Độ dài khuyến nghị:** 600–1000 từ

---

> **Hướng dẫn nộp group report:**
> 
> - File này nộp tại: `reports/group_report.md`
> - Deadline: Được phép commit **sau 18:00** (xem SCORING.md)
> - Tập trung vào **quyết định kỹ thuật cấp nhóm** — không trùng lặp với individual reports
> - Phải có **bằng chứng từ code/trace** — không mô tả chung chung
> - Mỗi mục phải có ít nhất 1 ví dụ cụ thể từ code hoặc trace thực tế của nhóm

---

## 1. Kiến trúc nhóm đã xây dựng (150–200 từ)

**Hệ thống tổng quan:**
Nhóm xây dựng hệ thống phân tán theo pattern **Supervisor-Worker** (Python thuần không dùng LangGraph). Hệ thống bao gồm 1 phần Supervisor (thuộc `graph.py`) đảm nhận việc route request đến các component khác; 3 Workers hành động song song gồm retrieval_worker, policy_tool_worker, và synthesis dùng LLM là gpt-5.4-mini thu thập lượng dữ liệu state để tạo câu trả lời cuối.

**Routing logic cốt lõi:**
Supervisor điều hướng dựa trên **Keyword Matching**. Các keyword bao gồm `POLICY_KEYWORDS`, `SLA_KEYWORDS`, `RISK_KEYWORDS`.
- Task chứa keyword cảnh báo UNKNOWN cộng cờ risk_high bật True sẽ đưa đến kiểm duyệt `human_review`.
- Task chứa khóa policy/quyền sẽ chuyển giao tại `policy_tool_worker`.
- Mặc định hoặc dính SLA sẽ qua `retrieval_worker` xử lý thông tin thông thường.

**MCP tools đã tích hợp:**
Hệ thống sử dụng các tool gọi bên trong worker nhằm lấy thêm context chuyên môn rẽ nhánh:
- `search_kb`: vector search context để lấy thêm minh chứng cho chính sách trả hàng.
- `get_ticket_info`: Lấy thông tin về ticket và status của vé dưới dạng hệ mock API.
- `check_access_permission`: Cung cấp kiểm soát cấp phép (vd: cấp độ 3 sẽ cho phép những người nào duyệt).

---

## 2. Quyết định kỹ thuật quan trọng nhất (200–250 từ)

**Quyết định:** Thêm Flow **Fallback Retrieval** ngay bên trong vòng lặp Graph thay vì tự để LLM tự check hoặc biến Policy Tools thành Agent to hơn.

**Bối cảnh vấn đề:**
Rất nhiều câu hỏi như *"Ai phê duyệt cấp quyền Level 3?"* chứa keyword policy, bị chuyển ngay đến `policy_tool_worker`. Tuy thế worker này lại không có sẵn kiến thức để lấy tài liệu cấp quyền trong DB, dẫn đến kết quả context là rỗng, Synthesis báo abstain dù DB có file tài liệu.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Nhúng Vector Search vào thẳng Worker | Chạy trong một nhánh, ít phức tạp cho state của Graph Pipeline | Vi phạm thiết kế đơn tầng, biến Worker thành một Pipeline thứ 2 dư thừa code. |
| Fallback qua Supervisor | Quản trị tập trung, Supervisor có thể tiếp tục phân loại ý định | Khá rườm rà trong quản lý đệ quy để tránh rơi vào infinite loop (VD gửi lại cho policy tool). |
| Gọi thêm Pipeline Fallback trong Graph loop | Code dễ đoán, tái sử dụng tuyệt đối được Worker khác. Rất rõ chức năng. | Tuồng thực thi cứng hơn và chỉ giải quyết được dạng thiếu chunks. |

**Phương án đã chọn và lý do:**
Bọn mình chọn **gọi thêm Pipeline trực tiếp fallback trong `build_graph()`**. Cụ thể, khi `policy_tool_worker` xử lý xong mà mảng `retrieved_chunks` rỗng thì sẽ kích hoạt chạy `retrieval_worker`. Lý do là giúp cho Debug cực tốt nhờ vào dấu vết trace `workers_called` tuần tự, và đồng thời giải quyết 100% tỷ lệ đứt quãng multi-hop mà vẫn bảo lưu tính đơn nhiệm của code từng Worker.

**Bằng chứng từ trace/code:**
Trace log cụ thể xử lý câu hỏi q03 cho thấy việc tái gọi retrieval:
```json
{
  "supervisor_route": "policy_tool_worker",
  "route_reason": "Contains policy keywords: ['phê duyệt', 'quyền']",
  "workers_called": ["policy_tool_worker", "retrieval_worker", "synthesis_worker"]
}
```

---

## 3. Kết quả grading questions (150–200 từ)

**Tổng điểm raw ước tính:** 90 / 96

**Câu pipeline xử lý tốt nhất:**
- ID: `q13`, `q15` — Lý do tốt: Đây là các câu hỏi Multi-hop ghép nhặt SLA và access control. Hệ thống làm rất hiệu quả nhờ Supervisor định tuyến trúng 2 lần thu thập context. Điểm Multi-hop accuracy từ 40% của v8 tăng ngoạn mục lên 65%.

**Câu pipeline fail hoặc partial:**
- ID: `q10` — Fail ở đâu: Keyword matching rất thiếu linh hoạt đối với trường hợp ngoại lệ. User gõ câu bình thường nhưng không trúng keyword thì rơi thẳng về Retrieval mù.
  Root cause: Thiếu Model nhận diện ý định.

**Câu gq07 (abstain):** Nhóm xử lý thế nào?
Từ trace cho mã lỗi `ERR-403-AUTH`, List trả về file chunks rác và LLM Synthesis chạy kiểm duyệt thấy không có nội dung khớp trong document chuẩn xác -> tự ý hạ tự tin `confidence = 0.2` để ném ra kết quả "Không đủ thông tin". Pipeline hoạt động Abstain đúng hơn gấp rưỡi Day 08.

**Câu gq09 (multi-hop khó nhất):** Trace ghi được 2 workers không? Kết quả thế nào?
Có. Trace của nhóm cho thấy `workers_called: ['policy_tool_worker', 'retrieval_worker']`. Worker thứ 1 kiểm tra exception policy qua MCP nhưng chưa ra ngay, tiếp đó nhờ fallback lấy file context thứ 2. Câu trả lời chiết xuất thành công tuyệt đối cả 2 dữ kiện.

---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được (150–200 từ)

**Metric thay đổi rõ nhất (có số liệu):**
- **Avg latency:** Tăng vọt từ `~2,500ms` lên `~10,000 - 12,958ms`.
- **Debug time:** Thời gian debug giảm từ 20 phút/lỗi xuống thành 5 phút/lỗi.
- **Mult-hop Accuracy:** Nâng từ mức yếu (~40%) sang mức trung bình khá (~65%).

**Điều nhóm bất ngờ nhất khi chuyển từ single sang multi-agent:**
Sự minh bạch tuyệt vời về luồng thông tin. Trong Day 08, ta hoàn toàn mù tịt về bước mà con bot bị fail, nhưng với Day 09 dựa vào check state, mỗi trace chỉ đích danh route nào bị lỗi và log IO worker được dump ra đầy đủ. Do đó có thể lôi riêng 1 model Worker đi Test Độc Lập bằng một mock state. Thao tác cực nhanh.

**Trường hợp multi-agent KHÔNG giúp ích hoặc làm chậm hệ thống:**
Sử dụng trên các cấu trúc tài liệu tĩnh dễ, loại single document nhỏ (ví dụ chỉ tra cái SLA nội bộ 1 dòng). Pipeline chạy gọi LLM 2-3 nhịp overhead vô ích và kéo thời gian chờ cho người dùng lâu gấp 4 lần.

---

## 5. Phân công và đánh giá nhóm (100–150 từ)

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| Đỗ Xuân Bằng | Supervisor logic & Graph state | 1 |
| Đỗ Việt Anh | Các Workers base & test script | 2 |
| Trương Anh Long | Tích hợp các MCP (Search, Tickets) | 3 |
| Lã Thị Linh | Evaluation Trace & Docs report | 4 |
| Lê Thành Long | Tech lead đánh giá system, architecture | All |

**Điều nhóm làm tốt:**
Chia Sprint cực kỳ nhịp nhàng vì bản thân pattern Multi-Agent chia Code tách bạch. Người nào nhận code worker người đó, không đụng chạm đến repository của người khác gây ra conflict merge.

**Điều nhóm làm chưa tốt hoặc gặp vấn đề về phối hợp:**
Sprint đầu bị rối cấu trúc và lúng túng trong định nghĩa Schema truyền JSON giữa các node Graph, mất khá nhiều thời gian để ra rule chuẩn.

**Nếu làm lại, nhóm sẽ thay đổi gì trong cách tổ chức?**
Nhóm sẽ sử dụng `Pydantic` ngay từ khởi đầu dự án để định nghĩa strict schema. Như thế tránh được rất nhiều error đánh máy khi read và write vào dictionary tự dọn của Python.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì? (50–100 từ)

Nhóm sẽ áp dụng **LLM Intent Classifier** chuyên nghiệp (dùng model nhỏ mạnh). Thay thế cái set `SLA_KEYWORDS` hiện thời bằng một cuộc gọi model 50ms để nhận dạng ý định. Như thế loại trừ được sai số người dùng gõ sai chính tả hoặc sai lệch cú pháp (nguyên nhân gây miss câu q10), đẩy tỷ lệ Route chuẩn xác lên mức 99%.

---

*File này lưu tại: `reports/group_report.md`*
*Commit sau 18:00 được phép theo SCORING.md*
