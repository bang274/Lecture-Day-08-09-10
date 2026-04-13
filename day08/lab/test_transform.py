import os
from dotenv import load_dotenv
from rag_answer import transform_query

load_dotenv()

def test_transform():
    queries = [
        ("Xử lý ticket P1 như thế nào?", "expansion"),
        ("Approval Matrix và quy trình cấp quyền máy tính", "decomposition"),
        ("Số điện thoại hỗ trợ kỹ thuật khẩn cấp", "hyde")
    ]

    for q, strategy in queries:
        print(f"\n--- Strategy: {strategy} ---")
        print(f"Original Query: {q}")
        transformed = transform_query(q, strategy=strategy)
        print(f"Transformed Result:")
        for i, item in enumerate(transformed):
            print(f"  [{i}] {item}")

if __name__ == "__main__":
    test_transform()
