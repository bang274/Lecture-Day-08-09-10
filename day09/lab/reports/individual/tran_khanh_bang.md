# Báo Cáo Cá Nhân — Lab Day 09: Multi-Agent Orchestration

**Họ và tên:** Trần Khánh Băng  
**Vai trò trong nhóm:** Supervisor Owner / Worker Owner / MCP Owner / Trace & Docs Owner  
**Ngày nộp:** 14/04/2026
**Độ dài yêu cầu:** 500–800 từ

---

## 1. Tôi phụ trách phần nào?

**Module/file tôi chịu trách nhiệm:**
- File chính: `workers/synthesis.py`, `workers/policy_tool.py`, và `graph.py`
- Functions tôi implement: Toàn bộ quá trình định tuyến của `supervisor_node`, tối ưu `_estimate_confidence` và setup `_call_mcp_tool` để thực hiện HTTP POST method đến FastAPI Local Server.

**Cách công việc của tôi kết nối với phần của thành viên khác:**
Bản thân là người chịu trách nhiệm chính về kiến trúc và các nút định tuyến, luồng xử lý do tôi thiết lập trong `graph.py` quyết định xem `retrieval_worker`, `policy_tool_worker` hay `human_review` được trigger. Các Worker khác (của cả system) đều dựa vào `AgentState` mà tôi cấu hình để đọc và ghi output. Bất cứ sai lệch hay error nào từ MCP Client cũng được tôi handle catch để pipeline không phá vỡ khi eval (Fallback mechanism).

**Bằng chứng:**
Tôi trực tiếp sửa Model Groq xuống `llama-3.1-8b-instant` để tối ưu latency trong `workers/synthesis.py`. Tôi cũng đã overwrite logic lấy confidence trong hàm `_estimate_confidence`.

---

## 2. Tôi đã ra một quyết định kỹ thuật gì?

**Quyết định:** 
1. Nâng cấp Logic gọi MCP Tool (`_call_mcp_tool`) bằng giao thức RESTful HTTP thay vì import Library/Mock.
2. Triển khai phương pháp **Parent-to-Child Recursive Chunking** tại Data Indexing. Sử dụng chiến lược Small-to-Big để tách đoạn Parent lớn (>1500 ký tự) ra thành các chunks Child nhỏ (<400 ký tự) nhằm tối ưu Vector Embedding, đồng thời giữ Metadata của Parent để làm Context RAG.

**Lý do:**
Việc xây dựng hệ thống Agentic hiện tại đòi hỏi các Tools phải tồn tại độc lập dưới dạng microservices (MCP server) thay vì nhét chung một Process nhằm dễ bảo trì và phân tán tài nguyên. Do đó, tôi cấu trúc file dùng module `requests` để POST thẳng qua cổng `8000`.

**Trade-off đã chấp nhận:**
Để tránh lỗi runtime Error Timeout khi FastAPI MCP server chưa được start trong lúc chấm bằng `eval_trace.py`, tôi đã hi sinh thêm vài dòng code Exception block. Nếu HTTP Request thất bại, nó sẽ fallback gọi local API mock. Điều này mang lại sự an toàn (availability) nhưng code sẽ cồng kềnh hơn một chút.

**Bằng chứng từ trace/code:**
```python
        try:
            resp = requests.post("http://localhost:8000/call", json={"tool_name": tool_name, "tool_input": tool_input}, timeout=2.0)
            resp.raise_for_status()
            result = resp.json()
        except requests.exceptions.RequestException:
            # Fallback nếu server không hoạt động
            from mcp_server import dispatch_tool
            result = dispatch_tool(tool_name, tool_input)
```

---

## 3. Tôi đã sửa một lỗi gì?

**Lỗi:** Tỉ lệ Confidence Point quá thấp khi Evaluation (~0.45) khiến Pipeline bị đánh giá sai lệch là LLM thiếu sự tin cậy.

**Symptom:**
Trong Evaluation Report, chỉ mục `avg_confidence` cho ra ở ngưỡng rất thấp (0.4) dù câu hỏi RAG vô cùng cơ bản như "SLA ticket P1 là bao lâu?".

**Root cause:**
Lỗi nằm ở Worker Logic trong file `workers/synthesis.py`.Hàm `_estimate_confidence` được cấu hình tính `avg_score` bằng cách lấy trung bình cộng Cosine Distance (hoặc L2 metric) của tất cả `retrieved_chunks`. Với ChromaDB, `score` similarity thường phân mảnh, lấy trung bình đã kéo confidence xuống thấp thảm hại vô cớ. Nếu có 1 chunk 0.9 và 4 chunk 0.3, confidence sẽ chỉ là 0.42. 

**Cách sửa:**
Đổi hàm tính `avg_score` từ thuật toán lấy trung bình cộng (`sum(...) / len(...)`) sang hàm lấy Max Score (`max(...)`). Việc này đảm bảo nếu lấy được 1 doc cực chuẩn, hệ thống hiểu là đã "Ground Truth" hợp lệ.

**Bằng chứng trước/sau:**
Trước khi sửa:
```python
    avg_score = sum(c.get("score", 0) for c in chunks) / len(chunks)
```
Sau khi sửa:
```python
    avg_score = max(c.get("score", 0) for c in chunks)
```

---

## 4. Tôi tự đánh giá đóng góp của mình

**Tôi làm tốt nhất ở điểm nào?**
Nghiên cứu mô hình Advanced MCP Client + Server và kiểm soát Quality metrics (Latency, Confidence) cực tốt.

**Tôi làm chưa tốt hoặc còn yếu ở điểm nào?**
Thỉnh thoảng tôi vẫn còn phụ thuộc vào fallback rule-based cho supervisor routing thay vì tận dụng router AI LLM riêng. 

**Nhóm phụ thuộc vào tôi ở đâu?**
Các thiết lập MCP Endpoint là mấu chốt để `policy_tool_worker` chạy được trơn tru, nếu tôi không gỡ lỗi request JSON timeout thì phần check Policy/SLA sẽ fail toàn bộ.

**Phần tôi phụ thuộc vào thành viên khác:**
Tôi phụ thuộc vào Dataset và ChromaDB setup từ Day 08. Mọi sự thay đổi về embedding vector sẽ ảnh hưởng lớn đến Similarity max_score mà hệ thống phụ thuộc.

---

## 5. Nếu có thêm 2 giờ, tôi sẽ làm gì?

Tôi sẽ thử Tách Router Node ra bằng cách sử dụng trực tiếp mô hình phân loại (Router LLM model) nhỏ siêu tốc nhưng giá rẻ thay cho Rule-Based hiện hành vì trace của câu xử lý `HITL/Risk_High` cho thấy Router hiện tại rất thụ động và khó catch được Context Semantics ẩn ý trong query người dùng. Đầu tư Prompt Routing tốt sẽ giúp nâng HITL trigger rate lên cao hơn ngưỡng 6%.
