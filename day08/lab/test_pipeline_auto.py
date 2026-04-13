import os
from dotenv import load_dotenv
from rag_answer import rag_answer

load_dotenv()

def test_pipeline_with_routing():
    test_queries = [
        "SLA ticket P1?",  # Expect expansion or none
        "Làm sao để xin nghỉ phép và ai là người duyệt?", # Expect decomposition
        "Hotline hỗ trợ kỹ thuật là số nào?", # Expect hyde
    ]

    print("="*60)
    print("TEST FULL PIPELINE WITH AUTO ROUTING")
    print("="*60)

    for q in test_queries:
        print(f"\n>>> USER QUERY: {q}")
        try:
            # Chạy với query_transform="auto" và verbose=True để thấy quá trình routing
            result = rag_answer(
                query=q, 
                retrieval_mode="dense", 
                use_rerank=True, 
                query_transform="auto",
                verbose=True
            )
            print(f"\nFINAL ANSWER:\n{result['answer']}")
        except Exception as e:
            print(f"Lỗi: {e}")

if __name__ == "__main__":
    test_pipeline_with_routing()
