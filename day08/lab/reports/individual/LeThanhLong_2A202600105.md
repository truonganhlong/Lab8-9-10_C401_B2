# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Lê Thành Long  
**Vai trò trong nhóm:** Tech Lead + Eval Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong lab này, tôi kiêm cả **Tech Lead** và **Eval Owner**. Ở vai trò Tech Lead, tôi chốt hướng kỹ thuật chung cho pipeline: `Raw Docs -> Index -> ChromaDB -> Dense Retrieval -> Optional Rerank -> Grounded Answer`, đồng thời phân chia việc theo sprint để tránh chồng chéo. Tôi cũng là người ưu tiên baseline trước với dense retrieval, `chunk_size=400`, `top_k_search=10`, `top_k_select=3`, model `gpt-5.4-mini`, thay vì nhảy ngay vào nhiều biến thể. Ở vai trò Eval Owner, tôi tổng hợp kết quả từ scorecard baseline và variant, đọc metric cùng notes trong `ab_comparison.csv` để xác định pipeline đang yếu ở đâu. Từ đó, tôi đề xuất chỉ bật **rerank** làm biến duy nhất cho variant vì baseline đã có `Context Recall = 5.0/5`.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau lab này, tôi hiểu rõ hơn mối liên hệ giữa **vai trò dẫn hướng kỹ thuật** và **vai trò đánh giá hệ thống**. Trước đây tôi khá dễ bị cuốn vào suy nghĩ “cứ thêm hybrid retrieval hay prompt phức tạp thì hệ thống sẽ mạnh hơn”. Nhưng khi trực tiếp đọc scorecard, tôi thấy baseline đã đạt recall rất cao, nghĩa là bài toán không nằm ở chuyện không tìm thấy tài liệu. Điều quan trọng hơn là evidence nào được đẩy vào prompt và model có giữ đúng kỷ luật grounded khi trả lời hay không. Từ góc nhìn này, tôi hiểu sâu hơn giá trị của A/B rule: chỉ đổi một biến mỗi lần để kết quả eval đủ sạch cho việc ra quyết định.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó khăn lớn nhất với tôi là phải giữ được **kỷ luật đánh giá** trong lúc cả nhóm đều muốn thử thêm nhiều ý tưởng. Với một corpus nhỏ và chỉ có 10 câu hỏi eval, nếu thay đồng thời chunking, top-k, retrieval strategy và prompt thì kết quả nhìn có thể “hay hơn”, nhưng gần như không còn giá trị để phân tích. Đây là chỗ tôi phải vừa điều phối kỹ thuật, vừa tự phản biện chính quyết định của nhóm. Điều làm tôi ngạc nhiên là chỉ một thay đổi khá nhỏ, bật `jina-reranker-v3`, đã cải thiện `Completeness` từ `4.40` lên `4.70`, đặc biệt sửa rõ lỗi ở `q06`. Nhưng một số câu như `q02` hay `q10` vẫn cho thấy rerank không giải quyết hết vấn đề.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?

**Phân tích:**

Tôi chọn `q02` vì đây không phải là một lỗi “sai hoàn toàn”, mà là một case rất điển hình cho việc **đúng ý nhưng chưa chắc đúng chuẩn**. Ở baseline, câu trả lời đạt `Completeness = 5/5` nhưng `Faithfulness = 4/5`. Sang variant bật rerank, `Faithfulness` tăng lên `5/5` nhưng `Completeness` lại giảm xuống `4/5`. Cả hai phiên bản đều có `Context Recall = 5/5`, nên với góc nhìn Eval Owner, tôi có thể loại trừ khá chắc lỗi ở indexing hay retrieval.

Điểm đáng chú ý là model đang xử lý một fact tưởng đơn giản nhưng có nuance về cách diễn đạt: baseline thiên về câu trả lời gần với đáp án mong đợi là `7 ngày làm việc`, trong khi variant lại bám sát phrasing ngắn hơn là `7 ngày`. Nhìn từ góc độ Tech Lead, đây là tín hiệu quan trọng: khi hệ thống trả lời policy question chứa mốc thời gian hoặc điều kiện, chỉ “gần đúng” là chưa đủ. Với tôi, `q02` cho thấy eval không chỉ phát hiện câu sai, mà còn phát hiện những câu tưởng đúng nhưng vẫn có rủi ro nếu đem dùng trong policy thật.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ ưu tiên một lớp **answer guardrail cho factual policy questions**. Với các câu có mốc thời gian hoặc điều kiện, prompt nên ép model giữ nguyên qualifier từ context, ví dụ `ngày` hay `ngày làm việc`. Tôi cũng muốn thử một bước hậu kiểm đơn giản cho các fact dạng số, để nếu answer làm rơi mất qualifier quan trọng thì hệ thống sẽ sinh lại thay vì trả ra ngay.

---
