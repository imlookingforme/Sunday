"""
ToolRAG for Sunday.
Maintains embeddings of tool descriptions and retrieves the most relevant tools.
"""
import logging
from typing import List, Dict, Any

class ToolRAG:
    def __init__(self):
        self.tools = []
        self.logger = logging.getLogger(__name__)
        try:
            import chromadb
            self.client = chromadb.Client()
            self.collection = self.client.get_or_create_collection("sunday_tools")
            self.use_chroma = True
        except ImportError:
            self.logger.warning("chromadb not installed. Falling back to simple keyword matching.")
            self.use_chroma = False

    async def index_tools(self, tools: List[Dict[str, Any]]):
        """Index a list of tools."""
        self.tools = tools
        if self.use_chroma:
            documents = [t.get("description", "") for t in tools]
            metadatas = [{"name": t.get("name", "")} for t in tools]
            ids = [t.get("name", "") for t in tools]
            if documents:
                self.collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
    
    async def retrieve_tools(self, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Retrieve top_k most relevant tools for a given query."""
        if not self.tools:
            return []
            
        if self.use_chroma:
            results = self.collection.query(query_texts=[query], n_results=min(top_k, len(self.tools)))
            retrieved_names = [meta["name"] for meta in results["metadatas"][0]]
            return [t for t in self.tools if t["name"] in retrieved_names]
        else:
            # Simple keyword fallback
            query_words = set(query.lower().split())
            scored_tools = []
            for t in self.tools:
                desc_words = set(t.get("description", "").lower().split())
                score = len(query_words.intersection(desc_words))
                scored_tools.append((score, t))
            scored_tools.sort(key=lambda x: x[0], reverse=True)
            return [t for score, t in scored_tools[:top_k]]
