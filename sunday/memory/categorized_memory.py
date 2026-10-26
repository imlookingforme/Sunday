"""Categorized Persistent Memory with Provenance and Learning from Corrections for Sunday 2.0.

Provides:
- Distinct memory categories:
    * User Preferences (coding style, preferred personas, formatting habits)
    * Project Conventions (architecture patterns, naming rules, test frameworks)
    * Architecture Decisions (ADRs, rationale, date, author)
    * Task History (summaries of completed tasks)
    * Debugging Lessons (root cause and solution pairs)
    * Verified Technical Facts (environment variables, port bindings, endpoints)
- Provenance tracking (source, project, timestamp, confidence score, expiration timestamp)
- Learning from corrections (classifying user corrections as one-off vs permanent project rules)
- Contradiction resolution and superseding stale memories
- Sensitive secret sanitization before memory persistence
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sqlite3
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MemoryCategory(Enum):
    USER_PREFERENCE = "user_preference"
    PROJECT_CONVENTION = "project_convention"
    ARCHITECTURE_DECISION = "architecture_decision"
    TASK_HISTORY = "task_history"
    DEBUGGING_LESSON = "debugging_lesson"
    TECHNICAL_FACT = "technical_fact"


class CorrectionScope(Enum):
    ONE_TIME_INSTRUCTION = "one_time_instruction"
    PROJECT_CONVENTION = "project_convention"
    USER_PREFERENCE = "user_preference"
    TECHNICAL_FACT = "technical_fact"


@dataclass
class MemoryRecord:
    """Individual categorized memory item with provenance tracking."""
    memory_id: str
    category: MemoryCategory
    key: str
    content: str
    project: str = "default"
    source: str = "user"  # 'user', 'verification', 'sentience', 'agent'
    confidence: float = 1.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    tags: List[str] = field(default_factory=list)
    superseded_by: Optional[str] = None


class CategorizedMemoryStore:
    """SQLite-backed categorized memory system with provenance and learning from corrections."""

    def __init__(self, db_path: Optional[Path | str] = None):
        self.db_path = str(db_path or Path("sunday") / "data" / "sunday.db")
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_done = False
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Create memory tables if not present."""
        if self._init_done:
            return

        def _sync_init():
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS categorized_memories (
                        memory_id TEXT PRIMARY KEY,
                        category TEXT NOT NULL,
                        key TEXT NOT NULL,
                        content TEXT NOT NULL,
                        project TEXT NOT NULL,
                        source TEXT NOT NULL,
                        confidence REAL NOT NULL,
                        created_at REAL NOT NULL,
                        updated_at REAL NOT NULL,
                        expires_at REAL,
                        tags TEXT,
                        superseded_by TEXT
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_cat_proj ON categorized_memories(category, project)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_key ON categorized_memories(key)")
                conn.commit()

        await asyncio.to_thread(_sync_init)
        self._init_done = True

    def _sanitize(self, content: str) -> str:
        """Strip potential secrets before storing in persistent memory."""
        sanitized = re.sub(r"sk-[a-zA-Z0-9_\-]{15,}", "[REDACTED_API_KEY]", content)
        sanitized = re.sub(r"ghp_[a-zA-Z0-9_\-]{15,}", "[REDACTED_GITHUB_TOKEN]", sanitized)
        return sanitized

    async def store_memory(
        self,
        category: MemoryCategory,
        key: str,
        content: str,
        project: str = "default",
        source: str = "user",
        confidence: float = 1.0,
        tags: Optional[List[str]] = None,
        ttl_seconds: Optional[float] = None,
    ) -> MemoryRecord:
        """Store or update a memory record, superseding prior versions."""
        await self.initialize()
        now = time.time()
        expires_at = (now + ttl_seconds) if ttl_seconds else None
        clean_content = self._sanitize(content)
        unique_suffix = uuid.uuid4().hex[:8]
        mem_id = f"mem_{int(now * 1000)}_{unique_suffix}"

        record = MemoryRecord(
            memory_id=mem_id,
            category=category,
            key=key,
            content=clean_content,
            project=project,
            source=source,
            confidence=confidence,
            created_at=now,
            updated_at=now,
            expires_at=expires_at,
            tags=tags or [],
        )

        def _sync_store():
            with sqlite3.connect(self.db_path) as conn:
                # Mark prior memory with same key and category as superseded
                conn.execute(
                    """
                    UPDATE categorized_memories
                    SET superseded_by = ?
                    WHERE category = ? AND key = ? AND project = ? AND superseded_by IS NULL
                    """,
                    (mem_id, category.value, key, project),
                )
                conn.execute(
                    """
                    INSERT INTO categorized_memories (
                        memory_id, category, key, content, project, source,
                        confidence, created_at, updated_at, expires_at, tags, superseded_by
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        record.memory_id,
                        record.category.value,
                        record.key,
                        record.content,
                        record.project,
                        record.source,
                        record.confidence,
                        record.created_at,
                        record.updated_at,
                        record.expires_at,
                        json.dumps(record.tags),
                        None,
                    ),
                )
                conn.commit()

        await asyncio.to_thread(_sync_store)
        logger.info(f"Stored memory [{key}] in category [{category.value}]")
        return record

    async def retrieve_memories(
        self,
        category: Optional[MemoryCategory] = None,
        project: str = "default",
        include_superseded: bool = False,
        query: Optional[str] = None,
    ) -> List[MemoryRecord]:
        """Fetch memories matching category, project, and search query."""
        await self.initialize()
        now = time.time()

        def _sync_retrieve():
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                q = "SELECT * FROM categorized_memories WHERE (project = ? OR project = 'default')"
                params: List[Any] = [project]

                if category:
                    q += " AND category = ?"
                    params.append(category.value)

                if not include_superseded:
                    q += " AND superseded_by IS NULL"

                q += " AND (expires_at IS NULL OR expires_at > ?)"
                params.append(now)

                if query:
                    q += " AND (content LIKE ? OR key LIKE ?)"
                    like_term = f"%{query}%"
                    params.extend([like_term, like_term])

                q += " ORDER BY updated_at DESC"
                cursor.execute(q, tuple(params))
                return [dict(r) for r in cursor.fetchall()]

        raw_list = await asyncio.to_thread(_sync_retrieve)
        records = []
        for r in raw_list:
            records.append(
                MemoryRecord(
                    memory_id=r["memory_id"],
                    category=MemoryCategory(r["category"]),
                    key=r["key"],
                    content=r["content"],
                    project=r["project"],
                    source=r["source"],
                    confidence=r["confidence"],
                    created_at=r["created_at"],
                    updated_at=r["updated_at"],
                    expires_at=r["expires_at"],
                    tags=json.loads(r["tags"] or "[]"),
                    superseded_by=r["superseded_by"],
                )
            )
        return records

    def classify_user_correction(self, user_feedback: str) -> Dict[str, Any]:
        """Determine whether user feedback represents a permanent convention, preference, or one-time fix."""
        text = user_feedback.lower().strip()

        # Check for permanent project rules / architecture conventions
        if any(term in text for term in ["always use", "never use", "in this project", "our convention", "from now on"]):
            return {
                "scope": CorrectionScope.PROJECT_CONVENTION,
                "should_persist": True,
                "category": MemoryCategory.PROJECT_CONVENTION,
                "suggested_rule": user_feedback,
                "explanation": "Permanent project convention detected.",
            }

        # Check for user personal preference
        if any(term in text for term in ["i prefer", "my preference", "call me", "format with", "i like"]):
            return {
                "scope": CorrectionScope.USER_PREFERENCE,
                "should_persist": True,
                "category": MemoryCategory.USER_PREFERENCE,
                "suggested_rule": user_feedback,
                "explanation": "Personal user preference detected.",
            }

        # Check for technical facts (ports, env names)
        if any(term in text for term in ["port is", "endpoint is", "database is located at", "env var is"]):
            return {
                "scope": CorrectionScope.TECHNICAL_FACT,
                "should_persist": True,
                "category": MemoryCategory.TECHNICAL_FACT,
                "suggested_rule": user_feedback,
                "explanation": "Technical configuration fact detected.",
            }

        # One-time instruction
        return {
            "scope": CorrectionScope.ONE_TIME_INSTRUCTION,
            "should_persist": False,
            "category": None,
            "suggested_rule": None,
            "explanation": "One-time corrective guidance for the active task only.",
        }
