import os
import asyncio
from typing import List, Dict, Any, Optional

try:
    import chromadb
    from chromadb.utils import embedding_functions
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False

DEFAULT_VECTOR_DIR = os.path.join("sunday", "data", "vectors")

class VectorStore:
    def __init__(self, persist_directory: str = DEFAULT_VECTOR_DIR):
        self.persist_directory = persist_directory
        os.makedirs(self.persist_directory, exist_ok=True)
        self._collection = None
        self._initialized = False
        self._fallback_store = []

    async def initialize(self):
        if self._initialized:
            return
        
        if HAS_CHROMADB:
            def sync_init():
                client = chromadb.PersistentClient(path=self.persist_directory)
                emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
                return client.get_or_create_collection(name="sunday_memory", embedding_function=emb_fn)
            self._collection = await asyncio.to_thread(sync_init)
            
        self._initialized = True

    async def add_document(self, doc_id: str, text: str, metadata: Dict[str, Any] = None):
        await self.initialize()
        
        if HAS_CHROMADB:
            def sync_add():
                self._collection.upsert(
                    ids=[doc_id],
                    documents=[text],
                    metadatas=[metadata or {}]
                )
            await asyncio.to_thread(sync_add)
        else:
            self._fallback_store.append({"id": doc_id, "text": text, "metadata": metadata or {}})
            
    async def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        await self.initialize()
        
        if HAS_CHROMADB:
            def sync_search():
                results = self._collection.query(
                    query_texts=[query],
                    n_results=limit
                )
                
                formatted_results = []
                if results.get('ids') and len(results['ids']) > 0:
                    for i in range(len(results['ids'][0])):
                        formatted_results.append({
                            "id": results['ids'][0][i],
                            "document": results['documents'][0][i],
                            "metadata": results['metadatas'][0][i],
                            "distance": results['distances'][0][i] if results.get('distances') else None
                        })
                return formatted_results
            return await asyncio.to_thread(sync_search)
        else:
            query_terms = query.lower().split()
            scored_docs = []
            for doc in self._fallback_store:
                score = sum(1 for term in query_terms if term in doc["text"].lower())
                if score > 0:
                    scored_docs.append({"doc": doc, "score": score})
            
            scored_docs.sort(key=lambda x: x["score"], reverse=True)
            return [
                {
                    "id": item["doc"]["id"],
                    "document": item["doc"]["text"],
                    "metadata": item["doc"]["metadata"],
                    "distance": -item["score"]
                } for item in scored_docs[:limit]
            ]
