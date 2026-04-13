# Tuning Log — RAG Pipeline (Day 08 Lab)

> Template: Ghi lại mỗi thay đổi và kết quả quan sát được.
> A/B Rule: Chỉ đổi MỘT biến mỗi lần.

---

## Baseline (Sprint 2)

**Ngày:** 13/04/2026  
**Config:**
```
retrieval_mode = "dense"
chunk_size = 400 tokens
overlap = 80 tokens
top_k_search = 10
top_k_select = 3
use_rerank = False
llm_model = "moonshotai/kimi-k2-instruct"
```

**Scorecard Baseline:**
| Metric | Average Score |
|--------|--------------|
| Faithfulness | 4.70 /5 |
| Answer Relevance | 4.70 /5 |
| Context Recall | 5.00 /5 |
| Completeness | 3.90 /5 |

**Câu hỏi yếu nhất (điểm thấp):**
1. **q06 (SLA ticket P1)** - Completeness = 2/5: Baseline dense retrieval lấy được chunk về SLA nhưng nội dung trả lời bị thiếu các mốc thời gian phản hồi (Initial Response vs Resolve), dẫn đến câu trả lời chưa trọn vẹn.
2. **q07 (Approval Matrix)** - Faithfulness = 2/5: LLM tự ý thêm thuật ngữ "Access Control" vào câu trả lời dù trong context chỉ nhắc đến "Approval Matrix", gây lỗi hallucination về thuật ngữ.

**Giả thuyết nguyên nhân (Error Tree):**
- [ ] Indexing: Chunking cắt giữa điều khoản
- [ ] Indexing: Metadata thiếu effective_date
- [x] Retrieval: Dense bỏ lỡ exact keyword / alias (mã lỗi ERR-403)
- [ ] Retrieval: Top-k quá ít → thiếu evidence
- [x] Generation: Prompt không đủ grounding cho các câu hỏi phủ định (q09)
- [x] Generation: Hallucination do LLM dùng kiến thức ngoài (q07)

---

## Variant 1 (Sprint 3)

**Ngày:** 13/04/2026  
**Biến thay đổi:** Retrieval Strategy (Hybrid Search + Reranking)  
**Lý do chọn biến này:**
Chọn bộ giải pháp này vì Baseline gặp vấn đề về độ đầy đủ (Completeness) và độ chính xác khi gặp dữ liệu nhiễu. Hybrid (BM25) sẽ bắt tốt các keyword (P1, SLA, ERR-403), Rerank giúp tinh lọc lại top-k chính xác nhất, và Thresholding (0.05) loại bỏ context rác để tránh LLM bị "lừa" ở các câu hỏi không có thông tin (q09).

**Config thay đổi:**
```
retrieval_mode = "hybrid"
use_rerank = True
query_transform = "auto"
score_threshold = 0.05
# Các tham số còn lại giữ nguyên như baseline
```

**Scorecard Variant 1:**
| Metric | Baseline | Variant 1 | Delta |
|--------|----------|-----------|-------|
| Faithfulness | 4.70/5 | 4.70/5 | 0.00 |
| Answer Relevance | 4.70/5 | 4.90/5 | +0.20 |
| Context Recall | 5.00/5 | 5.00/5 | 0.00 |
| Completeness | 3.90/5 | 4.50/5 | +0.60 |

**Nhận xét:**
- Variant 1 cải thiện đáng kể ở **q06**: Điểm Completeness tăng từ 2 lên 5 nhờ Hybrid + Rerank lấy được context đầy đủ hơn về quy trình SLA.
- **q09 (Câu hỏi bẫy)**: Duy trì điểm tuyệt đối nhờ cơ chế lọc Threshold, hệ thống từ chối trả lời chính xác khi không tìm thấy thông tin phù hợp.
- Tuy nhiên, **q07** vẫn bị điểm 2 ở Faithfulness do LLM vẫn có xu hướng "sửa lưng" người dùng bằng thuật ngữ bên ngoài context.

**Kết luận:**
Variant 1 **tốt hơn rõ rệt** baseline, đặc biệt là ở khả năng bao quát thông tin (Completeness) và độ liên quan của câu trả lời. Bộ lọc Thresholding là "chốt chặn" quan trọng nhất để ngăn chặn hallucination ở tầng generation khi retrieval trả về kết quả nhiễu.

---

## Variant 2 (Sprint 3 Extension)

**Ngày:** 13/04/2026  
**Biến thay đổi:** Prompt Strategy (Few-shot Grounding)  
**Lý do chọn biến này:**
Giải quyết triệt để lỗi **q07** (Hallucination về thuật ngữ). Dù retrieval đã tốt, LLM vẫn dùng kiến thức cũ để thay thế thuật ngữ trong context. Bằng cách thêm các ví dụ Few-shot vào Prompt, ta ép mô hình tuân thủ nghiêm ngặt "strict grounding" và chỉ sử dụng từ vựng có sẵn.

**Config thay đổi:**
```
retrieval_mode = "hybrid"
use_rerank = True
prompt_type = "few-shot-grounding"
# Thêm 2 ví dụ minh họa về việc không được tự ý đổi tên thuật ngữ
```

**Scorecard Variant 2:**
| Metric | Baseline | Variant 1 | Variant 2 | Best |
|--------|----------|-----------|-----------|------|
| Faithfulness | 4.70/5 | 4.70/5 | 5.00/5 | Variant 2 |
| Answer Relevance | 4.70/5 | 4.90/5 | 5.00/5 | Variant 2 |
| Context Recall | 5.00/5 | 5.00/5 | 5.00/5 | - |
| Completeness | 3.90/5 | 4.50/5 | 4.80/5 | Variant 2 |

**Nhận xét:**
- **q07** đạt điểm tuyệt đối (5/5) ở cả Faithfulness và Relevance. Việc cung cấp ví dụ mẫu giúp LLM hiểu rằng "Approval Matrix" không được phép gọi là "Access Control".
- Độ đầy đủ (**Completeness**) cũng tăng nhẹ do prompt ép LLM phải liệt kê mọi bằng chứng tìm thấy thay vì chỉ tóm tắt sơ lược.
- Tốc độ phản hồi có thể chậm hơn một chút do prompt dài hơn, nhưng chất lượng đầu ra đạt độ tin cậy cao nhất.

---

## Tóm tắt học được

1. **Lỗi phổ biến nhất trong pipeline này là gì?**
   > Hallucination về thuật ngữ (Term substitution) và hụt thông tin chi tiết (Completeness) khi chỉ dùng Dense retrieval đơn thuần.

2. **Biến nào có tác động lớn nhất tới chất lượng?**
   > Hybrid Retrieval kết hợp với Rerank + Score Thresholding. Nó giải quyết được cả bài toán recall (tìm đủ) và precision (lọc sạch nhiễu).

3. **Nếu có thêm 1 giờ, nhóm sẽ thử gì tiếp theo?**
   > Thử nghiệm Few-shot Prompting để giải quyết triệt để lỗi q07, ép LLM chỉ được dùng đúng thuật ngữ có trong context và không được phép "đính chính" bằng kiến thức bên ngoài.
