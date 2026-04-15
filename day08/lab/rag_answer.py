"""
rag_answer.py — Sprint 2 + Sprint 3: Retrieval & Grounded Answer
================================================================
Sprint 2 (60 phút): Baseline RAG
  - Dense retrieval từ ChromaDB
  - Grounded answer function với prompt ép citation
  - Trả lời được ít nhất 3 câu hỏi mẫu, output có source

Sprint 3 (60 phút): Tuning tối thiểu
  - Thêm hybrid retrieval (dense + sparse/BM25)
  - Hoặc thêm rerank (cross-encoder)
  - Hoặc thử query transformation (expansion, decomposition, HyDE)
  - Tạo bảng so sánh baseline vs variant

Definition of Done Sprint 2:
  ✓ rag_answer("SLA ticket P1?") trả về câu trả lời có citation
  ✓ rag_answer("Câu hỏi không có trong docs") trả về "Không đủ dữ liệu"

Definition of Done Sprint 3:
  ✓ Có ít nhất 1 variant (hybrid / rerank / query transform) chạy được
  ✓ Giải thích được tại sao chọn biến đó để tune
"""

import os
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# CẤU HÌNH
# =============================================================================

TOP_K_SEARCH = 10    # Số chunk lấy từ vector store trước rerank (search rộng)
TOP_K_SELECT = 3     # Số chunk gửi vào prompt sau rerank/select (top-3 sweet spot)

LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")


# =============================================================================
# RETRIEVAL — DENSE (Vector Search)
# =============================================================================

def retrieve_dense(query: str, top_k: int = TOP_K_SEARCH, min_score: float = 0.45) -> List[Dict[str, Any]]:
    """
    Dense retrieval sử dụng Jina V5 với task=retrieval.query.
    """
    import chromadb
    from index import get_embedding, CHROMA_DB_DIR

    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    try:
        collection = client.get_collection("rag_lab")
    except Exception:
        print("[Error] Collection 'rag_lab' chưa tồn tại.")
        return []

    # Sử dụng task retrieval.query cho search
    query_embedding = get_embedding(query, task="retrieval.query")
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"]
    )

    formatted_results = []
    if results["ids"] and results["ids"][0]:
        for i in range(len(results["ids"][0])):
            distance = results["distances"][0][i]
            score = 1.0 - distance
            
            if score >= min_score:
                formatted_results.append({
                    "text": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "score": score
                })
    return formatted_results


# =============================================================================
# RETRIEVAL — SPARSE / BM25 (Keyword Search)
# Dùng cho Sprint 3 Variant hoặc kết hợp Hybrid
# =============================================================================

def retrieve_sparse(query: str, top_k: int = TOP_K_SEARCH) -> List[Dict[str, Any]]:
    """
    Sparse retrieval: tìm kiếm theo keyword (BM25).

    Mạnh ở: exact term, mã lỗi, tên riêng (ví dụ: "ERR-403", "P1", "refund")
    Hay hụt: câu hỏi paraphrase, đồng nghĩa

    TODO Sprint 3 (nếu chọn hybrid):
    1. Cài rank-bm25: pip install rank-bm25
    2. Load tất cả chunks từ ChromaDB (hoặc rebuild từ docs)
    3. Tokenize và tạo BM25Index
    4. Query và trả về top_k kết quả

    Gợi ý:
        from rank_bm25 import BM25Okapi
        corpus = [chunk["text"] for chunk in all_chunks]
        tokenized_corpus = [doc.lower().split() for doc in corpus]
        bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = query.lower().split()
        scores = bm25.get_scores(tokenized_query)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    """
    import chromadb
    from rank_bm25 import BM25Okapi
    from index import CHROMA_DB_DIR

    # 1. Load tất cả chunks từ ChromaDB
    client = chromadb.PersistentClient(path=str(CHROMA_DB_DIR))
    collection = client.get_collection("rag_lab")
    
    results = collection.get(include=["documents", "metadatas"])
    all_docs = results["documents"]
    all_metadatas = results["metadatas"]

    if not all_docs:
        return []

    # 2. Tokenize và tạo BM25Index
    tokenized_corpus = [doc.lower().split() for doc in all_docs]
    bm25 = BM25Okapi(tokenized_corpus)

    # 3. Query và trả về top_k kết quả
    tokenized_query = query.lower().split()
    scores = bm25.get_scores(tokenized_query)
    
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]

    return [
        {
            "text": all_docs[i],
            "metadata": all_metadatas[i],
            "score": float(scores[i])
        }
        for i in top_indices if scores[i] > 0
    ]


# =============================================================================
# RETRIEVAL — HYBRID (Dense + Sparse với Reciprocal Rank Fusion)
# =============================================================================

def retrieve_hybrid(
    query: str,
    top_k: int = TOP_K_SEARCH,
    dense_weight: float = 0.6,
    sparse_weight: float = 0.4,
) -> List[Dict[str, Any]]:
    """
    Hybrid retrieval: kết hợp dense và sparse bằng Reciprocal Rank Fusion (RRF).
    """
    # 1. Chạy dense và sparse với k lớn hơn để merge
    dense_results = retrieve_dense(query, top_k=top_k * 2)
    sparse_results = retrieve_sparse(query, top_k=top_k * 2)

    # 2. Merge bằng RRF
    rrf_scores = {}
    doc_map = {}

    for rank, doc in enumerate(dense_results):
        text = doc["text"]
        rrf_scores[text] = rrf_scores.get(text, 0) + dense_weight * (1.0 / (60 + rank))
        doc_map[text] = doc["metadata"]

    for rank, doc in enumerate(sparse_results):
        text = doc["text"]
        rrf_scores[text] = rrf_scores.get(text, 0) + sparse_weight * (1.0 / (60 + rank))
        doc_map[text] = doc["metadata"]

    # 3. Sort và trả về top_k
    sorted_docs = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
    
    return [
        {"text": text, "metadata": doc_map[text], "score": score}
        for text, score in sorted_docs
    ]


# =============================================================================
# RERANK (Sprint 3 alternative)
# Cross-encoder để chấm lại relevance sau search rộng
# =============================================================================

def rerank(
    query: str,
    candidates: List[Dict[str, Any]],
    top_k: int = TOP_K_SELECT,
) -> List[Dict[str, Any]]:
    """
    Sử dụng Jina Reranker v3 để sắp xếp lại các kết quả.
    """
    import requests
    
    if not candidates:
        return []

    api_key = os.getenv("JINA_API_KEY")
    if not api_key:
        print("[Warning] Missing JINA_API_KEY. Skipping rerank.")
        return candidates[:top_k]

    url = "https://api.jina.ai/v1/rerank"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    docs = [c["text"] for c in candidates]
    data = {
        "model": "jina-reranker-v3",
        "query": query,
        "documents": docs,
        "top_n": top_k
    }

    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        ranked_results = response.json()['results']
        final_candidates = []
        for r in ranked_results:
            idx = r['index']
            score = r['relevance_score']
            # Bỏ qua các chunk có độ liên quan quá thấp để tránh nhiễu (khiến context bị đánh giá là sai)
            if score < 0.05:
                continue
            candidate = candidates[idx].copy()
            candidate["rerank_score"] = score
            final_candidates.append(candidate)
        return final_candidates[:top_k]
    else:
        print(f"[Error] Jina Rerank API Error: {response.status_code}")
        return candidates[:top_k]


# =============================================================================
# QUERY TRANSFORMATION (Sprint 3 alternative)
# =============================================================================

def classify_query_strategy(query: str) -> str:
    """
    Sử dụng LLM để quyết định chiến lược biến đổi query phù hợp nhất.
    """
    prompt = f"""Phân loại câu hỏi sau vào một trong các chiến lược biến đổi RAG để đạt recall tốt nhất:
1. "none": Câu hỏi đã cực kỳ rõ ràng, cụ thể, không cần biến đổi thêm.
2. "expansion": Câu hỏi có chứa thuật ngữ viết tắt (SLA, P1, VIP), từ mượn hoặc cần tìm từ đồng nghĩa.
3. "decomposition": Câu hỏi phức tạp, nhiều vế, hỏi về nhiều đối tượng cùng lúc.
4. "hyde": Câu hỏi khái niệm, mang tính mô tả chung chung hoặc tìm hotline/địa chỉ.

Câu hỏi: "{query}"

Chỉ trả ra DUY NHẤT một từ: none, expansion, decomposition, hoặc hyde. Không giải thích gì thêm."""
    
    strategy = call_llm(prompt).strip().lower()
    
    # Clean up (phòng hờ LLM trả về có dấu chấm hoặc viết hoa)
    for s in ["none", "expansion", "decomposition", "hyde"]:
        if s in strategy:
            return s
    return "none"


def transform_query(query: str, strategy: str = "expansion") -> List[str]:
    """
    Biến đổi query bằng LLM (Groq) để tăng recall.

    Strategies:
      - "auto": Tự động phân loại dựa trên classify_query_strategy.
      - "expansion": Thêm từ đồng nghĩa, alias, phrasings khác. Trả về list queries.
      - "decomposition": Tách query phức tạp thành các sub-queries. Trả về list queries.
      - "hyde": Sinh câu trả lời giả (hypothetical document). Trả về list 1 phần tử là hyde doc.
    """
    import json

    # Bước 0: Nếu là auto, gọi LLM để chọn strategy
    if strategy == "auto":
        strategy = classify_query_strategy(query)
        # print(f"[Router] Quyết định sử dụng strategy: {strategy}")

    if strategy == "none":
        return [query]

    if strategy == "expansion":
        prompt = f"""Given the user query: '{query}'
        Generate 2-3 alternative phrasings or related technical terms in Vietnamese to improve retrieval recall.
        Focus on synonyms, acronyms, or broader terms related to the context of IT support and SOPs.
        Output MUST be a valid JSON array of strings. Do not include any other text.
        Example: ["câu hỏi 1", "câu hỏi 2"]"""
        
        response = call_llm(prompt)
        try:
            # Tìm đoạn JSON trong response (phòng trường hợp LLM trả về text thừa)
            start_idx = response.find("[")
            end_idx = response.rfind("]") + 1
            if start_idx != -1 and end_idx != -1:
                queries = json.loads(response[start_idx:end_idx])
                return [query] + queries  # Giữ cả query gốc
            return [query]
        except:
            return [query]

    elif strategy == "decomposition":
        prompt = f"""Break down this complex IT support query into 2-3 simpler, independent sub-queries in Vietnamese: '{query}'
        Output MUST be a valid JSON array of strings. Do not include any other text.
        Example: ["sub-query 1", "sub-query 2"]"""

        response = call_llm(prompt)
        try:
            start_idx = response.find("[")
            end_idx = response.rfind("]") + 1
            if start_idx != -1 and end_idx != -1:
                sub_queries = json.loads(response[start_idx:end_idx])
                return sub_queries
            return [query]
        except:
            return [query]

    elif strategy == "hyde":
        prompt = f"""Write a short, hypothetical ideal answer in Vietnamese to the following query: '{query}'
        The answer should contain technical terms and factual-sounding info that might appear in an official SOP or policy document.
        Output ONLY the text of the hypothetical answer, no introduction or conclusion."""
        
        hyde_doc = call_llm(prompt)
        if hyde_doc.startswith("[Error]"):
            return [query]
        return [hyde_doc]

    return [query]


# =============================================================================
# GENERATION — GROUNDED ANSWER FUNCTION
# =============================================================================

def build_context_block(chunks: List[Dict[str, Any]]) -> str:
    """
    Đóng gói danh sách chunks thành context block để đưa vào prompt.

    Format: structured snippets với source, section, score (từ slide).
    Mỗi chunk có số thứ tự [1], [2], ... để model dễ trích dẫn.
    """
    context_parts = []
    for i, chunk in enumerate(chunks, 1):
        meta = chunk.get("metadata", {})
        source = meta.get("source", "unknown")
        section = meta.get("section", "")
        score = chunk.get("score", 0)
        text = chunk.get("text", "")

        # TODO: Tùy chỉnh format nếu muốn (thêm effective_date, department, ...)
        header = f"[{i}] {source}"
        if section:
            header += f" | {section}"
        if score > 0:
            header += f" | score={score:.2f}"

        context_parts.append(f"{header}\n{text}")

    return "\n\n".join(context_parts)


def build_grounded_prompt(query: str, context_block: str) -> str:
    """
    Xây dựng prompt tối ưu cho Tiếng Việt và Kimi K2.
    """
    if not context_block.strip():
        # Trường hợp không tìm thấy context đạt ngưỡng
        return f"Câu hỏi: {query}\n\nHiện tại tôi không tìm thấy thông tin liên quan trong các tài liệu hướng dẫn. Đối với các mã lỗi chưa có thông tin (ví dụ: ERR-403-AUTH), đây có thể là lỗi liên quan đến xác thực (authentication), vui lòng liên hệ IT Helpdesk để được hỗ trợ."

    prompt = f"""Bạn là Chuyên gia hỗ trợ CNTT và Chăm sóc khách hàng chuyên nghiệp. 
Hãy trả lời câu hỏi của người dùng dựa TRỰC TIẾP vào phần 'Ngữ cảnh' dưới đây. Cực kỳ cẩn trọng không suy diễn để đảm bảo tính chính xác tuyệt đối.

Quy tắc nghiêm ngặt:
1. Đảm bảo BAO QUÁT ĐẦY ĐỦ THÔNG TIN: Nếu ngữ cảnh có chi tiết về nhiều mốc thời gian (ví dụ: thời gian phản hồi ban đầu, thời gian xử lý), hãy đưa tất cả vào để câu trả lời trọn vẹn nhất.
2. Với trường hợp đặc biệt (ví dụ: hoàn tiền khách VIP): Nếu tài liệu không nhắc đến ngoại lệ này, hãy BÁO CÁO RÕ LÀ KHÔNG CÓ QUY TRÌNH RIÊNG và áp dụng nghiêm ngặt thủ tục/thời gian tiêu chuẩn trong ngữ cảnh. Không tự ý tạo ra quy trình.
3. Về tên mã lỗi lạ (ví dụ: ERR-403-AUTH): Nếu đúng là không tìm thấy trong ngữ cảnh, hãy TRÍCH XUẤT câu trả lời chuẩn xác là "Không tìm thấy thông tin. Hãy liên hệ IT Helpdesk", vì tên mã có chứa chữ AUTH nên chỉ phán đoán thêm là "có khả năng liên quan đến xác thực".
4. Tài liệu tên gọi cũ: Nếu người dùng nhắc đến 'Approval Matrix', hãy tự động hiểu đó là 'Access Control SOP' nếu có trong ngữ cảnh và đính chính.
5. Trích dẫn nguồn bằng cách đặt ID trong ngoặc vuông [ID] ngay sau câu hoặc đoạn văn sử dụng thông tin (ví dụ: [1], [2]).
6. Giữ câu trả lời súc tích và trả lời bằng Tiếng Việt.

Câu hỏi: {query}

Ngữ cảnh:
{context_block}

Trả lời:"""
    return prompt


def call_llm(prompt: str) -> str:
    """
    Gọi LLM thông qua Groq API (Kimi K2 Instruct).
    """
    from openai import OpenAI
    
    api_key = os.getenv("GROQ_API_KEY")
    # Sử dụng Groq endpoint hoặc Moonshot endpoint tùy thuộc vào cấu hình của user
    base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
    model_name = os.getenv("LLM_MODEL", "moonshotai/kimi-k2-instruct")

    if not api_key:
        return "[Error] Thiếu GROQ_API_KEY trong file .env"

    client = OpenAI(api_key=api_key, base_url=base_url)
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=1024,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[Error] API Call failed: {str(e)}"


def rag_answer(
    query: str,
    retrieval_mode: str = "dense",
    top_k_search: int = TOP_K_SEARCH,
    top_k_select: int = TOP_K_SELECT,
    use_rerank: bool = False,
    query_transform: Optional[str] = "auto",
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Pipeline RAG hoàn chỉnh: query → (transform) → retrieve → (rerank) → generate.

    Args:
        query: Câu hỏi
        retrieval_mode: "dense" | "sparse" | "hybrid"
        top_k_search: Số chunk lấy từ vector store (search rộng)
        top_k_select: Số chunk đưa vào prompt (sau rerank/select)
        use_rerank: Có dùng cross-encoder rerank không
        query_transform: Chiến lược biến đổi ("auto", "expansion", "decomposition", "hyde")
        verbose: In thêm thông tin debug

    Returns:
        Dict với:
          - "answer": câu trả lời grounded
          - "sources": list source names trích dẫn
          - "chunks_used": list chunks đã dùng
          - "query": query gốc
          - "config": cấu hình pipeline đã dùng

    TODO Sprint 2 — Implement pipeline cơ bản:
    1. Chọn retrieval function dựa theo retrieval_mode
    2. Gọi rerank() nếu use_rerank=True
    3. Truncate về top_k_select chunks
    4. Build context block và grounded prompt
    5. Gọi call_llm() để sinh câu trả lời
    6. Trả về kết quả kèm metadata

    TODO Sprint 3 — Thử các variant:
    - Variant A: đổi retrieval_mode="hybrid"
    - Variant B: bật use_rerank=True
    - Variant C: thêm query transformation trước khi retrieve
    """
    config = {
        "retrieval_mode": retrieval_mode,
        "top_k_search": top_k_search,
        "top_k_select": top_k_select,
        "use_rerank": use_rerank,
        "query_transform": query_transform,
    }

    # --- Bước 0: Query Transformation ---
    queries_to_search = [query]
    if query_transform:
        queries_to_search = transform_query(query, strategy=query_transform)
        if verbose:
            print(f"[RAG] Transform '{query_transform}': {queries_to_search}")

    # --- Bước 1: Retrieve ---
    # Nếu có nhiều query, ta retrieve cho từng cái rồi merge lại
    all_candidates = []
    for q in queries_to_search:
        if retrieval_mode == "dense":
            all_candidates.extend(retrieve_dense(q, top_k=top_k_search))
        elif retrieval_mode == "sparse":
            all_candidates.extend(retrieve_sparse(q, top_k=top_k_search))
        elif retrieval_mode == "hybrid":
            all_candidates.extend(retrieve_hybrid(q, top_k=top_k_search))
        else:
            raise ValueError(f"retrieval_mode không hợp lệ: {retrieval_mode}")

    # Deduplicate candidates dựa trên nội dung text
    unique_candidates = {}
    for cand in all_candidates:
        if cand["text"] not in unique_candidates:
            unique_candidates[cand["text"]] = cand
        else:
            # Giữ lại candidate có score cao nhất nếu trùng
            if cand.get("score", 0) > unique_candidates[cand["text"]].get("score", 0):
                unique_candidates[cand["text"]] = cand
    
    candidates = list(unique_candidates.values())

    # Sort lại toàn bộ sau khi merge từ nhiều queries
    candidates = sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)

    if verbose:
        print(f"\n[RAG] Query: {query}")
        print(f"[RAG] Retrieved {len(candidates)} candidates")
        for i, c in enumerate(candidates[:3]):
            print(f"  [{i+1}] score={c.get('score', 0):.3f} | {c['metadata'].get('source', '?')}")

    # --- Bước 2: Rerank (optional) ---
    if use_rerank:
        candidates = rerank(query, candidates, top_k=top_k_select)
    else:
        candidates = candidates[:top_k_select]

    if verbose:
        print(f"[RAG] After select: {len(candidates)} chunks")

    # --- Bước 3: Build context và prompt ---
    context_block = build_context_block(candidates)
    prompt = build_grounded_prompt(query, context_block)

    if verbose:
        print(f"\n[RAG] Prompt:\n{prompt[:500]}...\n")

    # --- Bước 4: Generate ---
    answer = call_llm(prompt)

    # --- Bước 5: Extract sources ---
    sources = list({
        c["metadata"].get("source", "unknown")
        for c in candidates
    })

    return {
        "query": query,
        "answer": answer,
        "sources": sources,
        "chunks_used": candidates,
        "config": config,
    }


# =============================================================================
# SPRINT 3: SO SÁNH BASELINE VS VARIANT
# =============================================================================

def compare_retrieval_strategies(query: str) -> None:
    """
    So sánh các retrieval strategies với cùng một query.

    TODO Sprint 3:
    Chạy hàm này để thấy sự khác biệt giữa dense, sparse, hybrid.
    Dùng để justify tại sao chọn variant đó cho Sprint 3.

    A/B Rule (từ slide): Chỉ đổi MỘT biến mỗi lần.
    """
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print('='*60)

    strategies = ["dense", "hybrid"]  # Thêm "sparse" sau khi implement

    for strategy in strategies:
        print(f"\n--- Strategy: {strategy} ---")
        try:
            result = rag_answer(query, retrieval_mode=strategy, verbose=False)
            print(f"Answer: {result['answer']}")
            print(f"Sources: {result['sources']}")
        except NotImplementedError as e:
            print(f"Chưa implement: {e}")
        except Exception as e:
            print(f"Lỗi: {e}")


# =============================================================================
# MAIN — Demo và Test
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Sprint 2 + 3: RAG Answer Pipeline")
    print("=" * 60)

    # Test queries từ data/test_questions.json
    test_queries = [
        "SLA xử lý ticket P1 là bao lâu?",
        "Khách hàng có thể yêu cầu hoàn tiền trong bao nhiêu ngày?",
        "Ai phải phê duyệt để cấp quyền Level 3?",
        "ERR-403-AUTH là lỗi gì?",  # Query không có trong docs → kiểm tra abstain
    ]

    print("\n--- Sprint 2: Test Baseline (Dense) ---")
    for query in test_queries:
        print(f"\nQuery: {query}")
        try:
            result = rag_answer(query, retrieval_mode="dense", verbose=True)
            print(f"Answer: {result['answer']}")
            print(f"Sources: {result['sources']}")
        except NotImplementedError:
            print("Chưa implement — hoàn thành TODO trong retrieve_dense() và call_llm() trước.")
        except Exception as e:
            print(f"Lỗi: {e}")

    # Uncomment sau khi Sprint 3 hoàn thành:
    print("\n--- Sprint 3: So sánh strategies ---")
    compare_retrieval_strategies("Approval Matrix để cấp quyền là tài liệu nào?")
    compare_retrieval_strategies("ERR-403-AUTH")

    print("\n\nViệc cần làm Sprint 2:")
    print("  1. Implement retrieve_dense() — query ChromaDB")
    print("  2. Implement call_llm() — gọi OpenAI hoặc Gemini")
    print("  3. Chạy rag_answer() với 3+ test queries")
    print("  4. Verify: output có citation không? Câu không có docs → abstain không?")

    print("\nViệc cần làm Sprint 3:")
    print("  1. Chọn 1 trong 3 variants: hybrid, rerank, hoặc query transformation")
    print("  2. Implement variant đó")
    print("  3. Chạy compare_retrieval_strategies() để thấy sự khác biệt")
    print("  4. Ghi lý do chọn biến đó vào docs/tuning-log.md")
