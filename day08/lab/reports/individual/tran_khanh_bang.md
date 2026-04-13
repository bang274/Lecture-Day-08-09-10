# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Trần Khánh Bằng  
**Vai trò trong nhóm:** Tech Lead  
**Ngày nộp:** 2026-04-13  
**Độ dài:** ~650 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong bài Lab Day 08, em đóng vai trò là Tech Lead của nhóm, chịu trách nhiệm điều phối kỹ thuật và trực tiếp thực thi hai giai đoạn then chốt ban đầu. Cụ thể, em phụ trách **Sprint 1 (Indexing Pipeline)** và **Sprint 2 (Baseline RAG)**. 

Ở Sprint 1, em đã thiết kế thuật toán chunking thông minh dựa trên cấu trúc đề mục (Heading-based split) của tài liệu và cấu hình hệ thống metadata (department, effective_date) để tối ưu hóa khả năng lọc dữ liệu. Sang Sprint 2, em tập trung vào việc tích hợp ChromaDB với Jina Embeddings và hoàn thiện hàm `rag_answer` cơ bản để hệ thống có thể trả lời câu hỏi kèm theo trích dẫn nguồn. 

Sau khi nền tảng pipeline đã ổn định, em chuyển sang hỗ trợ các thành viên khác trong Sprint 3 để thử nghiệm các Variant nâng cao. Một đóng góp quan trọng khác của em là quản trị source code trên GitHub. Nhận thấy một số bạn trong nhóm chưa quen với workflow chuyên nghiệp, em đã trực tiếp hướng dẫn cách tạo branch, thực hiện commit theo quy chuẩn và giải quyết xung đột (conflict) khi merge code, giúp quy trình làm việc của nhóm diễn ra trơn tru.

---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Khái niệm cốt lõi mà em hiểu sâu sắc và thú vị nhất sau bài lab này chính là **Chiến lược Chunking**. 

Trước đây, em chỉ coi việc cắt văn bản là một thao tác kỹ thuật đơn giản theo số lượng ký tự. Tuy nhiên, khi trực tiếp xây dựng pipeline, em nhận ra sự tương đồng giữa cách máy tính xử lý thông tin và cách não bộ con người hoạt động thông qua các "chunks" (đoạn thông tin có nghĩa). Việc tách data thành các đoạn có cấu trúc logic giúp model LLM không chỉ truy xuất đúng đoạn văn bản cần thiết mà còn giữ được bối cảnh (context) quan trọng nhất cho câu trả lời. 

Em đã học được rằng nếu chunking quá nhỏ, thông tin sẽ bị vụn vặt và mất ngữ cảnh; nhưng nếu quá lớn, vector embedding sẽ bị "loãng" và làm giảm độ chính xác của tìm kiếm. Việc tìm ra điểm cân bằng giữa `chunk_size` (~400 tokens) và `overlap` (~80 tokens) chính là yếu tố then chốt để tối ưu hóa cả tính chính xác (Faithfulness) và khả năng bao quát (Relevance) của hệ thống RAG.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Điều khiến em ngạc nhiên nhất trong quá trình thực hiện là "sự đánh đổi" (trade-off) tất yếu giữa khả năng tìm kiếm và tính trung thực của câu trả lời. 

Khi chúng em nâng cấp lên chiến lược **Hybrid Retrieval + Reranking** ở Variant 1, điểm Relevance (độ liên quan) đã tăng vọt từ 2.9 lên 3.8. Tuy nhiên, đồng thời điểm Faithfulness (tính trung thực) lại có xu hướng giảm nhẹ. Giả thuyết ban đầu của em là càng nhiều context thì câu trả lời càng tốt, nhưng thực tế cho thấy khi chúng em tăng `top_k_select` lên 7, model LLM đôi khi bị "nhiễu" bởi các thông tin có vẻ liên quan nhưng không trực tiếp giải quyết vấn đề, dẫn đến việc model tự suy luận thêm (hallucinate).

Khó khăn lớn nhất về mặt kỹ thuật là việc xử lý lỗi rate limit và timeout từ Groq API trong quá trình chạy evaluation tự động. Đôi khi model judge trả về kết quả lỗi khiến điểm trung bình bị sai lệch hoàn toàn. Em đã phải dành khá nhiều thời gian để cấu hình lại cơ chế retry và thêm các khoảng nghỉ `time.sleep()` trong script `eval.py` để đảm bảo kết quả đo lường là chính xác nhất.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

Trong bảng scorecard, em chọn câu hỏi **q03: "Ai phải phê duyệt để cấp quyền Level 3?"** để phân tích vì đây là trường hợp minh họa rõ nét nhất cho sự cải tiến.

**Phân tích:**
*   **Baseline (Dense Search):** Hệ thống chỉ đạt điểm Relevance = 1/5 và Completeness = 4/5. Model đã tìm thấy tài liệu về Access Control nhưng lại không thể chỉ ra đúng đoạn về "Level 3". Nguyên nhân là do ở mô hình Dense-only, thuật ngữ "Level 3" là một từ khóa rất đặc thù nhưng lại bị embedding model xử lý theo hướng ngữ nghĩa chung chung, dẫn đến việc truy xuất không đúng trọng tâm.
*   **Variant (Hybrid + Rerank):** Điểm Relevance đã nhảy vọt lên **5/5**. Đây là thắng lợi của sự kết hợp giữa BM25 (Sparse) và Cross-Encoder (Rerank). Thành phần BM25 giúp bắt chính xác từ khóa "Level 3" trong văn bản, và sau đó Jina Reranker v3 đã ưu tiên đưa đoạn văn bản từ "IT Security Access SOP" lên đầu ngữ cảnh. Kết quả là model LLM đã trích dẫn cực kỳ chính xác: "Việc cấp quyền Level 3 phải được phê duyệt bởi IT Security Manager và bộ phận Compliance". 

Ví dụ này củng cố niềm tin của em rằng với các tài liệu quy trình có nhiều thuật ngữ kỹ thuật khô khan, Hybrid Search là cấu hình bắt buộc để đạt được hiệu năng cao nhất.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, em sẽ tập trung triển khai kỹ thuật **"Small-to-Big Retrieval"**. Kết quả đánh giá cho thấy hiện tại chúng ta đang dùng chunk 400 tokens cho cả tìm kiếm và trả lời, dẫn đến việc đôi khi context bị loãng hoặc thiếu ý. Em muốn thử nghiệm việc dùng các chunk nhỏ (100-200 tokens) để tìm kiếm chính xác từ khóa, nhưng khi đưa vào LLM sẽ trả về "Parent Chunk" lớn hơn (800-1000 tokens). Điều này theo em sẽ giúp cải thiện điểm Completeness và khắc phục triệt để lỗi mất ngữ cảnh ở các câu hỏi phức tạp.

