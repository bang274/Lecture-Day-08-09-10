import chromadb
import os
import sys

def main():
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        print("Please install sentence-transformers: pip install sentence-transformers")
        sys.exit(1)
        
    client = chromadb.PersistentClient(path='./chroma_db')
    try:
        client.delete_collection('day09_docs')
    except Exception:
        pass
    
    col = client.get_or_create_collection('day09_docs', metadata={"hnsw:space": "cosine"})
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    docs_dir = './data/docs'
    if not os.path.exists(docs_dir):
        print(f"Directory {docs_dir} not found")
        sys.exit(1)
        
    for fname in os.listdir(docs_dir):
        if not fname.endswith('.txt'): continue
        with open(os.path.join(docs_dir, fname), 'r', encoding='utf-8') as f:
            content = f.read()
            
        chunks = [content] # simpler single chunk per doc
        embeddings = model.encode(chunks).tolist()
        ids = [f"{fname}_{i}" for i in range(len(chunks))]
        metadatas = [{"source": fname} for _ in chunks]
        
        col.add(documents=chunks, embeddings=embeddings, ids=ids, metadatas=metadatas)
        print(f"Indexed: {fname}")
        
    print("Index ready")

if __name__ == "__main__":
    main()
