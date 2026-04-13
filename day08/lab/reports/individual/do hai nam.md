# Báo Cáo Cá Nhân — Lab Day 08: RAG Pipeline

**Họ và tên:** Đỗ Hải Nam
**Vai trò trong nhóm:** Tech Lead / Retrieval Owner  
**Ngày nộp:** 13/04/2026  
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi đã làm gì trong lab này? (100-150 từ)

Trong dự án này, tôi chịu trách nhiệm chính về kiến trúc hệ thống và tối ưu hóa tầng truy xuất. Cụ thể:
- **Sprint 1 (Indexing):** Thiết lập quy trình tiền xử lý dữ liệu trong `index.py`, sử dụng Regex để bóc tách Metadata (phòng ban, ngày hiệu lực) và triển khai kỹ thuật Section-based Chunking để giữ tính toàn vẹn của nội dung theo phân mục tài liệu.
- **Sprint 2 & 3 (Retrieval & Optimization):** Xây dựng bộ máy tìm kiếm Hybrid kết hợp giữa Dense Retrieval (Jina v5 Embeddings) và Sparse Retrieval (BM25). Tôi đã trực tiếp cài đặt thuật toán Reciprocal Rank Fusion (RRF) để trộn kết quả và tích hợp Jina Reranker v3 để tái xếp hạng ứng viên, giúp tăng độ chính xác đáng kể.
- **Sprint 3 (Advanced):** Triển khai Query Rewriting sử dụng LLM để mở rộng truy vấn, giúp hệ thống hiểu được các thuật ngữ cũ (như Approval Matrix) và ánh xạ chúng về tài liệu mới. Tuy nhiên kết quả không được như mong đợi.
---

## 2. Điều tôi hiểu rõ hơn sau lab này (100-150 từ)

Sau Lab này, tôi hiểu sâu sắc về bản chất của **Hybrid Retrieval và Reciprocal Rank Fusion (RRF)**. Thực tế cho thấy Dense đã "bỏ lỡ" các từ khóa kỹ thuật chính xác như mã lỗi (ERR-403) hoặc tên tài liệu viết tắt. RRF không chỉ đơn thuần là cộng điểm, mà là cách chúng ta tận dụng thế mạnh hiểu ngữ nghĩa của Dense và thế mạnh bắt từ khóa chính xác của Sparse để tạo ra kết quả cân bằng nhất.

Bên cạnh đó, tôi cũng hiểu rõ hơn về **Grounded Prompting**. Việc thêm cơ chế "Chain-of-Thought" vào System Prompt giúp mô hình thực hiện các bước suy luận logic (như kiểm tra quy trình chung khi không thấy quy định riêng cho VIP) thay vì chỉ đơn giản trả lời "Không biết", giúp hệ thống trở nên thông minh và hữu ích hơn trong thực tế.

---

## 3. Điều tôi ngạc nhiên hoặc gặp khó khăn (100-150 từ)

Khó khăn lớn nhất mà tôi gặp phải là lỗi xung đột môi trường với **ChromaDB**. Lỗi `AttributeError: module 'chromadb' has no attribute 'PersistentClient'` đã tiêu tốn nhiều thời gian debug. Nguyên nhân đến từ việc cài đặt đồng thời cả `chromadb-client` (bản thu gọn) và `chromadb` (bản đầy đủ), dẫn đến việc Python load sai thư viện. Bài học rút ra là phải cực kỳ cẩn thận với quản lý dependencies trong các dự án LLM.

Tôi cũng gặp khó khăn trong việc cài đặt các model rerank và embedding trên huggingface về local trong môi trường lớp học do mạng không đủ mạnh, khiến tôi mất rất nhiều thời gian, đó cũng chính là lí do tôi chuyển sang dùng jina API.

Một điều gây ngạc nhiên khác là câu hỏi về "Approval Matrix". Ở bản Baseline, dù hệ thống đã tìm đúng file `access-control-sop.md`, nhưng do nội dung về tên cũ nằm ở phần "Ghi chú" đầu file, các đoạn chunk về quy trình kiểm soát cấp quyền lại có điểm tương đồng vector cao hơn, khiến thông tin quan trọng bị đẩy ra khỏi top-3 context. Điều này khẳng định rằng **Reranking** là bước tối quan trọng để lọc lại thông tin sau khi tìm kiếm.

---

## 4. Phân tích một câu hỏi trong scorecard (150-200 từ)

**Câu hỏi:** "Approval Matrix để cấp quyền hệ thống là tài liệu nào?"

**Phân tích:**
- **Baseline (Dense Search):** Hệ thống tìm đúng file `it/access-control-sop.md` nhưng trả lời: "Tôi không tìm thấy thông tin này". Nguyên nhân là do trong 3 chunks được đưa vào ngữ cảnh, không đoạn nào chứa câu ghi chú "Tài liệu này trước đây có tên Approval Matrix...". Vector search đã ưu tiên các đoạn mô tả chi tiết các Level 1-4 vì chúng xuất hiện nhiều từ khóa liên quan đến "quyền" hơn.
- **Lỗi nằm ở:** **Retrieval (Ranking/Chunk Selection)**. Thông tin cần thiết tồn tại trong database nhưng không được bộ lọc Top-K đưa vào context của LLM.
- **Variant (Hybrid + Rerank + Query Rewrite):** Kết quả được cải thiện hoàn toàn.
    - **Query Rewrite** đã mở rộng query thành "Tài liệu phê duyệt quyền truy cập hệ thống Approval Matrix Access Control SOP".
    - **Sparse (BM25)** đã bắt được chính xác cụm từ "Approval Matrix" nằm trong phần ghi chú của tài liệu.
    - **Reranker** sau đó đã nhận diện đoạn văn chứa ghi chú này là quan trọng nhất và đưa nó lên đầu context. Kết quả là LLM đã trả lời chính xác tài liệu cần tìm.

---

## 5. Nếu có thêm thời gian, tôi sẽ làm gì? (50-100 từ)

Nếu có thêm thời gian, tôi sẽ triển khai kỹ thuật **Parent Document Retrieval**. Thay vì chỉ gửi các đoạn chunk nhỏ lẻ cho LLM, tôi sẽ cấu hình để khi một đoạn chunk được tìm thấy, hệ thống sẽ tự động truy xuất và gửi toàn bộ nội dung của Section hoặc cả tài liệu chứa đoạn đó. Điều này sẽ giúp giải quyết triệt để vấn đề mất ngữ cảnh khi thông tin nằm rải rác ở đầu và cuối các đoạn cắt (như trường hợp ghi chú tên tài liệu). Tôi cũng đang nghiên cứu phần này cho bài tập lớn project của mình.
