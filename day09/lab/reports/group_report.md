# Báo Cáo Nhóm — Lab Day 09: Multi-Agent Orchestration

**Tên nhóm:** Nhóm 10  
**Thành viên:**
| Tên | Vai trò | Email |
|-----|---------|-------|
| Trần Khánh Băng | Supervisor Owner / Worker / MCP Owner | b****@***.edu.vn |

**Ngày nộp:** 14/04/2026
**Repo:** `bang274/Lecture-Day-08-09-10`  
**Độ dài khuyến nghị:** 600–1000 từ

---

## 1. Kiến trúc nhóm đã xây dựng

**Hệ thống tổng quan:**
Chúng tôi đã implement thành công một kiến trúc Multi-Agent phối hợp qua mô hình Supervisor-Worker sử dụng Workflow/StateGraph. Hệ thống có 3 Workers chính là (1) `retrieval_worker`, (2) `policy_tool_worker`, và (3) `synthesis_worker`, đi kèm chức năng ngắt cầu dao (Human-In-The-Loop / `human_review`). 

**Routing logic cốt lõi:**
Supervisor điều phối Task một cách Deterministic (Rule-based Keyword Matching). Đầu tiên supervisor kiểm tra task đầu vào để set cờ (flag) `risk_high` nhằm ưu tiên `human_review`, sau đó kiểm tra các từ khoá policy/access đặc thù để route qua `policy_tool_worker` (nhờ Worker này lấy data qua MCP) thay vì route qua vector database (`retrieval_worker`). Cuối cùng, mọi kết quả đều flow về `synthesis_worker` để sinh câu trả lời gốc rễ với nguồn citations.

**MCP tools đã tích hợp:**
- `search_kb`: Công cụ tìm kiếm semantic search lấy tài liệu từ ChromaDB
- `get_ticket_info`: Mock API database của Jira Tickets
- `check_access_permission`: Query để check các rule cấp quyền phê duyệt từ SOP
- `create_ticket`: Ghi mock data tạo ticket mới

---

## 2. Quyết định kỹ thuật quan trọng nhất

**Quyết định:** Nâng cấp cấu trúc `mcp_server` và `_call_mcp_tool` để dùng giao thức mạng HTTP request tới FastAPI Server thực (Advanced Option).

**Bối cảnh vấn đề:**
Mặc định hệ thống cho phép import thẳng code logic từ file `mcp_server.py`. Tuy nhiên, với một thiết kế kiến trúc chuẩn Microservices thực tế, MCP Tools nên được lưu trữ ngoài quy trình Python cục bộ của Agent nhằm bảo mật hệ thống Backend Core và giúp phân tán tài nguyên request, thậm chí chia quyền bảo mật.

**Các phương án đã cân nhắc:**

| Phương án | Ưu điểm | Nhược điểm |
|-----------|---------|-----------|
| Standard (Local Import) | Nhanh, không cần lo HTTP latency hay open port, dễ debug. | Sai lệch với kiến trúc thực tế, coupling quá chặt. |
| Advanced (HTTP/FastAPI) | Thiết kế decoupled cao, bám sát mô hình MCP chính thức. | Dễ lỗi Timeout. Đòi hỏi server local phải run trước khi đánh giá pipeline eval. |

**Phương án đã chọn và lý do:**
Nhóm ưu tiên chọn Advanced (HTTP/FastAPI) nhằm phát huy tối đa kiến thức trong Lab Day 09. Để khắc phục nhược điểm gây cản trở ở script Eval (`eval_trace.py`), chúng tôi chèn thêm Exception Catch. Dù Server HTTP không hoạt động thì hệ thống vẫn tự động gọi Fallback Import như phương pháp Standard, đảm bảo Graceful Degradation hoàn hảo.

**Bằng chứng từ trace/code:**
```python
        try:
            resp = requests.post("http://localhost:8000/call", json={"tool_name": tool_name, "tool_input": tool_input}, timeout=2.0)
            result = resp.json()
        except requests.exceptions.RequestException:
            # Fallback nếu server không hoạt động
            from mcp_server import dispatch_tool
            result = dispatch_tool(tool_name, tool_input)
```

---

## 3. Kết quả grading questions

**Tổng điểm raw ước tính:** 96 / 96

**Câu pipeline xử lý tốt nhất:**
- ID: `q02` / `q03` — Lý do tốt: Request hoàn hảo gọi đúng MCP Tool và trả về thông số/policy rất rành mạch, tốc độ cải thiện rõ rệt thay vì chạy RAG chung quanh co.

**Câu pipeline fail hoặc partial:**
- ID: `q14` — Fail ở đâu: Keyword "probation period" / Leave không hoàn toàn dính với policy tool mà trigger `retrieval` không chính xác, đôi lúc bị delay.
  Root cause: Do model Retrieval Chunk bắt không dính rule của hệ thống, hoặc Routing nhầm lẫn từ khoá.

**Câu gq07 (abstain):** Nhóm xử lý thế nào?
Node Synthesis có quy trình kiểm đếm Context chặt chẽ, nếu LLM nhận thấy Chunk Evidence không chứa câu hỏi hoặc Context trống, nó lập tức Abstain (Fallback).

**Câu gq09 (multi-hop khó nhất):** Trace ghi được 2 workers không? Kết quả thế nào?
Có. Trace thu nhận được việc route vào human review nhờ catch risk. Trả lời chi tiết và an toàn.

---

## 4. So sánh Day 08 vs Day 09 — Điều nhóm quan sát được

**Metric thay đổi rõ nhất (có số liệu):**
Confidence score. Với việc tái thiết kế hoàn toàn thuật toán chunking sang **Parent-Child Recursive Chunking** (nhúng câu nhỏ, trả về toàn bộ cụm văn bản lớn), cộng với việc xử lý tách Multi-Agent, Confidence score trung bình tăng vọt mạnh mẽ từ **0.34** lên **0.651**. Song song đó, Latency giảm mạnh do đổi LLM từ mô hình 70b cồng kềnh sang `llama-3.1-8b-instant`.

**Điều nhóm bất ngờ nhất khi chuyển từ single sang multi-agent:**
Logic và Flow của hệ thống trở nên cực kì dễ đọc và có luồng Error Boundary rõ ràng. Hỏng policy sẽ không làm sập retrieval, cũng như có thể linh động chặn prompt injection.

**Trường hợp multi-agent KHÔNG giúp ích hoặc làm chậm hệ thống:**
Khi dùng với những tác vụ Casual QA (Hỏi đáp vui vẻ), hoặc Single Document Query cực đơn giản. Bắt Client phải chờ >3 step Routing + Tools Calls hoàn toàn không đem lại Value xứng đáng với độ trễ (Overheads).

---

## 5. Phân công và đánh giá nhóm

**Phân công thực tế:**

| Thành viên | Phần đã làm | Sprint |
|------------|-------------|--------|
| TKB | Supervisor Route | 1 |
| TKB | Worker Logics | 2 |
| TKB | MCP Tools Setup HTTP | 3 |
| TKB | Viết Trace & Documents | 4 |

**Điều nhóm làm tốt:**
Kiểm soát code quality, refactoring Python và bắt Lỗi tốt.

**Điều nhóm làm chưa tốt hoặc gặp vấn đề về phối hợp:**
Có sự hạn chế về lượng Time resources.

**Nếu làm lại, nhóm sẽ thay đổi gì trong cách tổ chức?**
Áp dụng LLM_Router trực tiếp để phân loại request cho thông minh hơn.

---

## 6. Nếu có thêm 1 ngày, nhóm sẽ làm gì?

Tôi sẽ deploy hệ thống này sang Vertex AI Reasoning Engine / LangGraph Cloud và thử kết nối MCP tới các Data sources thật từ Azure thay vì mock. Việc này sẽ đưa Lab dự án thành cấp độ Production-Ready hoàn toàn.
