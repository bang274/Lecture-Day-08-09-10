import chromadb
import os
import sys

class RecursiveChunker:
    """
    Recursively split text using separators in priority order.
    """
    DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

    def __init__(self, separators=None, chunk_size=500):
        self.separators = self.DEFAULT_SEPARATORS if separators is None else list(separators)
        self.chunk_size = chunk_size

    def chunk(self, text):
        if not text:
            return []
        return self._split(text, self.separators)

    def _split(self, text, separators):
        if len(text) <= self.chunk_size:
            return [text]

        if not separators:
            return [text[i:i + self.chunk_size] for i in range(0, len(text), self.chunk_size)]

        separator = separators[0]
        remaining = separators[1:]
        
        if not separator:
            return self._split(text, [])

        splits = text.split(separator)
        
        final_chunks = []
        current_chunk = ""
        
        for i, part in enumerate(splits):
            if i < len(splits) - 1:
                part += separator
            
            if not part:
                continue

            if len(part) > self.chunk_size:
                if current_chunk:
                    final_chunks.append(current_chunk.strip())
                    current_chunk = ""
                final_chunks.extend(self._split(part, remaining))
            elif len(current_chunk) + len(part) <= self.chunk_size:
                current_chunk += part
            else:
                if current_chunk:
                    final_chunks.append(current_chunk.strip())
                current_chunk = part
        
        if current_chunk:
            final_chunks.append(current_chunk.strip())
            
        return [c for c in final_chunks if c]


class ParentChildChunker:
    """
    Implements Small-to-Big (Parent-Child) chunking using RecursiveChunker.
    """
    def __init__(self, parent_size=1500, child_size=400):
        self.parent_chunker = RecursiveChunker(chunk_size=parent_size)
        self.child_chunker = RecursiveChunker(chunk_size=child_size)

    def chunk_to_docs(self, text: str, doc_name: str):
        docs = []
        parents = self.parent_chunker.chunk(text)
        for i, parent_text in enumerate(parents):
            children = self.child_chunker.chunk(parent_text)
            for j, child_text in enumerate(children):
                docs.append({
                    "id": f"{doc_name}_p{i}_c{j}",
                    "text": child_text,
                    "metadata": {
                        "source": doc_name,
                        "parent_content": parent_text,
                        "is_child": True
                    }
                })
        return docs


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
        
    chunker = ParentChildChunker(parent_size=1500, child_size=400)
        
    for fname in os.listdir(docs_dir):
        if not fname.endswith('.txt'): continue
        with open(os.path.join(docs_dir, fname), 'r', encoding='utf-8') as f:
            content = f.read()
            
        docs = chunker.chunk_to_docs(content, fname)
        
        if not docs:
            continue
            
        chunks = [d["text"] for d in docs]
        embeddings = model.encode(chunks).tolist()
        ids = [d["id"] for d in docs]
        metadatas = [d["metadata"] for d in docs]
        
        col.add(documents=chunks, embeddings=embeddings, ids=ids, metadatas=metadatas)
        print(f"Indexed: {fname} into {len(chunks)} child chunks.")
        
    print("Index ready")

if __name__ == "__main__":
    main()
