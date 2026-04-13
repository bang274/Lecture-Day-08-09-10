import sys
import os
from rag_answer import rerank

def test_rerank():
    query = "SLA xử lý ticket P1 là bao lâu?"
    
    candidates = [
        {
            "text": "SLA xử lý ticket P1 là trong vòng 2 giờ kể từ khi tiếp nhận. Đây là yêu cầu khẩn cấp nhất.",
            "metadata": {"source": "SOP_SLA.pdf", "section": "Emergency"}
        },
        {
            "text": "Quy trình nghỉ phép của nhân viên phải được phê duyệt trước 3 ngày.",
            "metadata": {"source": "HR_Policy.pdf", "section": "Leave"}
        },
        {
            "text": "Hướng dẫn sử dụng máy photocopy trong văn phòng.",
            "metadata": {"source": "Office_Guide.pdf", "section": "Equipment"}
        },
        {
            "text": "Thông tin về các gói bảo hiểm sức định kỳ cho nhân viên.",
            "metadata": {"source": "Insurance.pdf", "section": "Benefits"}
        }
    ]
    
    print(f"Query: {query}")
    print("\n--- Before Rerank ---")
    for i, c in enumerate(candidates):
        print(f"[{i}] {c['text'][:50]}... (Source: {c['metadata']['source']})")
    
    # Run rerank
    top_k = 2
    ranked_results = rerank(query, candidates, top_k=top_k)
    
    print(f"\n--- After Rerank (Top {top_k}) ---")
    for i, c in enumerate(ranked_results):
        score = c.get('rerank_score', 'N/A')
        print(f"[{i}] Score: {score:.4f} | {c['text'][:100]}... (Source: {c['metadata']['source']})")

    # Debug: print all scores
    print("\n--- All Candidates with Rerank Scores ---")
    for i, c in enumerate(candidates):
        print(f"Chunk {i}: Score {c.get('rerank_score', 'N/A'):.4f} | Text: {c['text'][:50]}...")

    # Basic assertion
    assert len(ranked_results) <= top_k
    # assert "P1" in ranked_results[0]['text'] 
    print(f"\nTop 1 text: {ranked_results[0]['text']}")
    print("\nTest finished.")

if __name__ == "__main__":
    test_rerank()
