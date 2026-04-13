# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Nguyen Duc Cuong  
**Vai trò trong nhóm:** Retrieval Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Tôi chủ yếu phụ trách Sprint 3 và Sprint 4 với vai trò là Retrieval Owner. Trong lab này, tôi đã trực tiếp triển khai các chức năng quan trọng để nâng cấp pipeline từ Baseline lên Advanced RAG:
*   Xây dựng hàm `retrieve_sparse` sử dụng thuật toán BM25 để bắt chính xác các từ khóa kỹ thuật và mã lỗi.
*   Thiết kế hàm `retrieve_hybrid` kết hợp kết quả từ Dense và Sparse Search bằng kỹ thuật Reciprocal Rank Fusion (RRF), giúp tăng recall toàn diện.
*   Triển khai bộ định tuyến câu hỏi `classify_query_strategy` và hàm `transform_query` (Expansion, Decomposition, HyDE) để làm rõ ý định của người dùng trước khi truy vấn.
*   Thiết lập bộ lọc ngưỡng (Score Thresholding) tại bước Rerank để loại bỏ các đoạn văn bản nhiễu (noise) không liên quan.

Công việc của tôi là cầu nối giữa tầng dữ liệu (Sprint 1) và tầng sinh câu trả lời (Sprint 2), giúp LLM có được ngữ cảnh "sạch" và đầy đủ nhất để trả lời.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Mặc dù đã có kiến thức cơ bản về **Hybrid Retrieval** từ trước, nhưng sau buổi lab này, tôi thực sự hiểu rõ hơn về sức mạnh của **Reranking** khi được kết hợp với cơ chế **Score Thresholding**. Trước đây, tôi chỉ coi Reranking là một bước sắp xếp lại thứ tự ưu tiên, nhưng qua thực tế debug, tôi nhận ra nó còn là một "màng lọc" chất lượng cực kỳ quan trọng.

Tôi hiểu rằng trong một pipeline RAG phức tạp, việc lấy về được nhiều dữ liệu (High Recall) đôi khi lại là "con dao hai lưỡi" nếu không có tầng lọc Precision hiệu quả. Việc áp dụng chỉ số ngưỡng (0.05) sau khi Rerank đã giúp tôi ngộ ra rằng: thà để LLM trả lời "Tôi không biết" còn tốt hơn là cung cấp cho nó các context có độ liên quan thấp dẫn đến sai lệch thông tin. Đây là bài học thực tế quý giá nhất về việc tối ưu hóa độ tin cậy của hệ thống thay vì chỉ đuổi theo điểm số retrieval.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó khăn lớn nhất mà tôi gặp phải là khi triển khai Rerank, hệ thống ban đầu đưa về quá nhiều dữ liệu không cần thiết (noise). Mặc dù Reranker luôn trả về Top-k, nhưng nếu tất cả các kết quả tìm được đều có độ liên quan cực thấp, chúng vẫn bị ép vào ngữ cảnh, dẫn đến việc LLM bị "nhiễu" và cố gắng bịa ra câu trả lời (hallucination).

Tôi đã mất khá nhiều thời gian debug tại câu hỏi q09 (một mã lỗi không tồn tại trong tài liệu). Ban đầu, hệ thống vẫn lấy về các chunk rác và trả lời sai. Giải pháp mà tôi áp dụng là dùng một **chỉ số ngưỡng (threshold)** để chặn: nếu kết quả Rerank có score dưới 0.05, tôi sẽ coi như không tìm thấy thông tin. Việc "chặn" này hóa ra lại hiệu quả hơn nhiều so với việc cố gắng cải thiện prompt, vì nó giải quyết vấn đề ngay từ tầng dữ liệu đầu vào.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** "ERR-403-AUTH là lỗi gì?" (q09)

**Phân tích:**
Ở phiên bản **Baseline (Dense)**, hệ thống cố gắng tìm các đoạn văn bản có ý nghĩa gần giống nhất với "lỗi xác thực" và trả về một đoạn về Access Control. LLM sau đó dựa vào đó để "suy diễn" và cho rằng đây là lỗi quyền truy cập, dẫn đến điểm Faithfulness thấp vì thông tin không thực sự có trong docs.

Trong phiên bản **Variant** do tôi thiết kế, tôi đã kết hợp bộ lọc Threshold. Khi query "ERR-403-AUTH", Hybrid Search vẫn tìm thấy một số đoạn văn chứa từ "AUTH" nhưng khi qua tầng Reranker, điểm score của chúng đều cực thấp (dưới 0.05). Hệ thống đã nhận diện được đây là context rác và trả về kết quả rỗng. Nhờ prompt được thiết lập chặt chẽ, LLM đã trả lời đúng theo quy định: "Hiện tại tôi không tìm thấy thông tin liên quan... vui lòng liên hệ IT Helpdesk". 

Kết quả là điểm **Faithfulness** và **Relevance** của câu này đạt tuyệt đối 5/5 trong Variant, minh chứng cho việc lọc dữ liệu ở tầng Retrieval quan trọng như thế nào đối với độ tin cậy của RAG.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ tập trung vào việc xử lý lỗi hallucination thuật ngữ ở câu q07. Tôi muốn thử nghiệm kỹ thuật **Few-shot Prompting** trong hàm `build_grounded_prompt` để hướng dẫn LLM tuyệt đối không được tự ý thay thế thuật ngữ trong tài liệu (ví dụ: không được đổi "Approval Matrix" thành "Access Control"). Ngoài ra, tôi muốn thử áp dụng **MMR (Maximum Marginal Relevance)** trong bước retrieval để tăng tính đa dạng của context, tránh việc lấy quá nhiều chunk trùng lặp nội dung.

---

*Lưu file này với tên: `reports/individual/[ten_ban].md`*
*Ví dụ: `reports/individual/nguyen_van_a.md`*
