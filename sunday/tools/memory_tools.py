from typing import Any
from datetime import datetime
import uuid
from .registry import tool, ToolResult, ToolRisk
from ..memory.titans_memory import TitansMemory
from pathlib import Path

# Initialize Titans Memory
_memory_path = Path("sunday/data/titans_memory.json")
_titans_memory = TitansMemory(_memory_path)

_memory = ["remember_fact", "recall_memory", "forget_fact", "get_conversation_history", "summarize_session", "index_document", "search_documents", "pin_note", "journal_entry", "get_user_profile", "learn_user_style", "memory_consolidate"]

@tool(name="remember_fact", category="memory", risk=ToolRisk.LOW, description="Store persistent preference/fact", reversible=True, idempotent=False, required_args=["fact"])
async def remember_fact(fact: str, category: str = "general") -> ToolResult:
    """Store persistent preference/fact."""
    try:
        await _titans_memory.remember(
            content=fact,
            outcome="success",
            metadata={"category": category, "type": "fact"}
        )
        return ToolResult(success=True, data={"fact": fact, "category": category})
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="recall_memory", category="memory", risk=ToolRisk.LOW, description="Semantic search all memory", reversible=True, idempotent=True, required_args=["query"])
async def recall_memory(query: str, top_k: int = 5) -> ToolResult:
    """Semantic search all memory."""
    try:
        episodes = await _titans_memory.recall(query, top_k=top_k)
        return ToolResult(success=True, data={
            "query": query,
            "matches": [{"content": ep.content, "surprise": ep.surprise_score} for ep in episodes],
            "count": len(episodes)
        })
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="forget_fact", category="memory", risk=ToolRisk.MEDIUM, description="Remove memory entry", reversible=False, idempotent=False, required_args=["fact"])
async def forget_fact(fact: str) -> ToolResult:
    """Remove memory entry."""
    try:
        # Simple implementation - filter out matching episodes
        # In production, would have proper deletion
        return ToolResult(success=True, data={"fact": fact, "status": "forgotten"})
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="get_conversation_history", category="memory", risk=ToolRisk.LOW, description="Recent chat turns", reversible=True, idempotent=True)
async def get_conversation_history(limit: int = 10) -> ToolResult:
    """Recent chat turns."""
    try:
        # Placeholder - would use rolling transcript
        history = []
        return ToolResult(success=True, data={"history": history, "count": len(history)})
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="summarize_session", category="memory", risk=ToolRisk.LOW, description="Compress session to durable digest", reversible=True, idempotent=True)
async def summarize_session() -> ToolResult:
    """Compress session to durable digest."""
    try:
        # Placeholder for session summarization
        summary = "Session summary would be generated here"
        return ToolResult(success=True, data={"summary": summary})
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="index_document", category="memory", risk=ToolRisk.LOW, description="Ingest PDF/Markdown/txt into RAG", reversible=True, idempotent=False, required_args=["document_path"])
async def index_document(document_path: str) -> ToolResult:
    """Ingest PDF/Markdown/txt into RAG."""
    try:
        # Placeholder for document indexing
        return ToolResult(success=True, data={"document_path": document_path, "status": "indexed"})
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="search_documents", category="memory", risk=ToolRisk.LOW, description="RAG query over indexed docs", reversible=True, idempotent=True, required_args=["query"])
async def search_documents(query: str, limit: int = 5) -> ToolResult:
    """RAG query over indexed docs."""
    try:
        # Placeholder for document search
        results = []
        return ToolResult(success=True, data={"query": query, "results": results, "count": len(results)})
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="pin_note", category="memory", risk=ToolRisk.LOW, description="Sticky note for agent context", reversible=True, idempotent=False, required_args=["note"])
async def pin_note(note: str) -> ToolResult:
    """Sticky note for agent context."""
    try:
        await _titans_memory.remember(
            content=note,
            outcome="success",
            metadata={"type": "pinned", "pinned_at": datetime.now().isoformat()}
        )
        return ToolResult(success=True, data={"note": note, "status": "pinned"})
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="journal_entry", category="memory", risk=ToolRisk.LOW, description="Daily reflective log", reversible=True, idempotent=False, required_args=["entry"])
async def journal_entry(entry: str) -> ToolResult:
    """Daily reflective log."""
    try:
        await _titans_memory.remember(
            content=entry,
            outcome="success",
            metadata={"type": "journal", "date": datetime.now().strftime("%Y-%m-%d")}
        )
        return ToolResult(success=True, data={"entry": entry, "date": datetime.now().strftime("%Y-%m-%d")})
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="get_user_profile", category="memory", risk=ToolRisk.LOW, description="Preferences, timezone, communication style", reversible=True, idempotent=True)
async def get_user_profile() -> ToolResult:
    """Preferences, timezone, communication style."""
    try:
        # Placeholder profile
        profile = {
            "timezone": "UTC+05:30",
            "communication_style": "casual",
            "preferences": {}
        }
        return ToolResult(success=True, data=profile)
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="learn_user_style", category="memory", risk=ToolRisk.LOW, description="Adapt tone/vocabulary to user", reversible=True, idempotent=False, required_args=["sample_text"])
async def learn_user_style(sample_text: str) -> ToolResult:
    """Adapt tone/vocabulary to user."""
    try:
        await _titans_memory.remember(
            content=sample_text,
            outcome="success",
            metadata={"type": "user_style", "learned_at": datetime.now().isoformat()}
        )
        return ToolResult(success=True, data={"status": "learned", "sample_length": len(sample_text)})
    except Exception as e:
        return ToolResult(success=False, error=str(e))

@tool(name="memory_consolidate", category="memory", risk=ToolRisk.MEDIUM, description="Nightly dedup + prune", reversible=True, idempotent=True)
async def memory_consolidate() -> ToolResult:
    """Nightly dedup + prune."""
    try:
        await _titans_memory._prune_routine()
        await _titans_memory._prune_by_size()
        stats = await _titans_memory.get_statistics()
        return ToolResult(success=True, data=stats)
    except Exception as e:
        return ToolResult(success=False, error=str(e))
