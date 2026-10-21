"""Titans Memory - surprise-weighted persistent memory based on NeurIPS 2025 research."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
import json
import numpy as np
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None  # Fallback if library is missing


@dataclass
class Episode:
    """A memory episode with surprise score."""
    content: str
    outcome: str  # "success", "error", "unexpected"
    timestamp: datetime
    surprise_score: float = 0.0
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class TitansMemory:
    """Surprise-weighted persistent memory based on NeurIPS 2025 research.
    
    Key principles:
    - Routine tasks fade (low surprise)
    - Unexpected outcomes persist (high surprise)
    - Bounded memory (never grows forever)
    - Semantic similarity + recency weighting
    """
    
    def __init__(
        self,
        memory_path: Path,
        surprise_threshold: float = 0.5,
        decay_rate: float = 0.95,
        max_episodes: int = 1000
    ):
        self.memory_path = memory_path
        self.memory_path.parent.mkdir(parents=True, exist_ok=True)
        self.surprise_threshold = surprise_threshold
        self.decay_rate = decay_rate
        self.max_episodes = max_episodes
        self.episodes: List[Episode] = []
        self._embedding_model = None
        self._load()
    
    def _load(self) -> None:
        """Load episodes from disk."""
        if self.memory_path.exists():
            with open(self.memory_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            for ep_data in data:
                ep_data["timestamp"] = datetime.fromisoformat(ep_data["timestamp"])
                self.episodes.append(Episode(**ep_data))
            
            # Apply decay on load
            self._apply_decay()
    
    def _save(self) -> None:
        """Save episodes to disk."""
        data = []
        for ep in self.episodes:
            ep_dict = {
                "content": ep.content,
                "outcome": ep.outcome,
                "timestamp": ep.timestamp.isoformat(),
                "surprise_score": ep.surprise_score,
                "metadata": ep.metadata
            }
            data.append(ep_dict)
        
        with open(self.memory_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    
    async def remember(self, content: str, outcome: str = "success", metadata: dict = None) -> None:
        """Store episode with surprise score."""
        episode = Episode(
            content=content,
            outcome=outcome,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        # Calculate surprise score
        episode.surprise_score = self._calculate_surprise(episode)
        
        self.episodes.append(episode)
        await self._prune_routine()
        await self._prune_by_size()
        self._save()
    
    def _calculate_surprise(self, episode: Episode) -> float:
        """Calculate surprise based on novelty and outcome."""
        # Novelty: how different from existing memories
        novelty = self._calculate_novelty(episode.content)
        
        # Outcome: unexpected outcomes are more surprising
        outcome_surprise = {
            "success": 0.3,
            "error": 1.0,
            "unexpected": 0.8
        }.get(episode.outcome, 0.5)
        
        # Combine with recency bonus for very recent events
        recency_bonus = 0.2 if len(self.episodes) < 10 else 0.0
        
        return min(1.0, (novelty + outcome_surprise + recency_bonus) / 2)
    
    def _calculate_novelty(self, content: str) -> float:
        """Calculate novelty based on semantic similarity to existing memories."""
        if not self.episodes:
            return 1.0  # First episode is maximally novel
        
        try:
            if self._embedding_model is None:
                self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Get embedding for new content
            new_embedding = self._embedding_model.encode([content])[0]
            
            # Get embeddings for recent episodes (last 50 for efficiency)
            recent_episodes = self.episodes[-50:]
            existing_embeddings = self._embedding_model.encode(
                [ep.content for ep in recent_episodes]
            )
            
            # Calculate max similarity
            similarities = np.dot(existing_embeddings, new_embedding)
            max_similarity = np.max(similarities)
            
            # Novelty = 1 - max_similarity
            return float(1.0 - max_similarity)
        
        except Exception:
            # Fallback: simple string matching
            content_lower = content.lower()
            for ep in reversed(self.episodes[-20:]):
                if content_lower == ep.content.lower():
                    return 0.0
                if content_lower in ep.content.lower() or ep.content.lower() in content_lower:
                    return 0.3
            return 0.7
    
    async def recall(self, query: str, top_k: int = 5) -> List[Episode]:
        """Recall episodes weighted by surprise + recency + semantic similarity."""
        if not self.episodes:
            return []
        
        scored = []
        for ep in self.episodes:
            # Score = surprise * recency_weight * semantic_similarity
            recency_weight = self._recency_weight(ep.timestamp)
            semantic = self._semantic_similarity(query, ep.content)
            score = ep.surprise_score * recency_weight * semantic
            scored.append((score, ep))
        
        scored.sort(reverse=True, key=lambda x: x[0])
        return [ep for _, ep in scored[:top_k]]
    
    def _recency_weight(self, timestamp: datetime) -> float:
        """Calculate recency weight (more recent = higher weight)."""
        age_hours = (datetime.now() - timestamp).total_seconds() / 3600
        # Decay over 30 days
        return max(0.1, np.exp(-age_hours / (30 * 24)))
    
    def _semantic_similarity(self, query: str, content: str) -> float:
        """Calculate semantic similarity between query and content."""
        try:
            if self._embedding_model is None:
                self._embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            
            embeddings = self._embedding_model.encode([query, content])
            similarity = float(np.dot(embeddings[0], embeddings[1]))
            return max(0.1, similarity)
        except Exception:
            # Fallback: simple word overlap
            query_words = set(query.lower().split())
            content_words = set(content.lower().split())
            if not query_words:
                return 0.1
            overlap = len(query_words & content_words) / len(query_words)
            return max(0.1, overlap)
    
    async def _prune_routine(self) -> None:
        """Prune low-surprise routine episodes."""
        # Decay scores over time
        for ep in self.episodes:
            age_hours = (datetime.now() - ep.timestamp).total_seconds() / 3600
            # Decay over 7 days
            decay_factor = np.exp(-age_hours / (7 * 24))
            ep.surprise_score *= (self.decay_rate * decay_factor)
        
        # Remove episodes below threshold
        self.episodes = [ep for ep in self.episodes 
                        if ep.surprise_score > self.surprise_threshold]
    
    async def _prune_by_size(self) -> None:
        """Prune to max_episodes if exceeded."""
        if len(self.episodes) > self.max_episodes:
            # Keep highest surprise episodes
            self.episodes.sort(key=lambda ep: ep.surprise_score, reverse=True)
            self.episodes = self.episodes[:self.max_episodes]
    
    def _apply_decay(self) -> None:
        """Apply time-based decay to all episodes."""
        for ep in self.episodes:
            age_hours = (datetime.now() - ep.timestamp).total_seconds() / 3600
            decay_factor = np.exp(-age_hours / (7 * 24))
            ep.surprise_score *= decay_factor
    
    async def get_statistics(self) -> dict:
        """Get memory statistics."""
        if not self.episodes:
            return {
                "total_episodes": 0,
                "avg_surprise": 0.0,
                "high_surprise_count": 0
            }
        
        avg_surprise = sum(ep.surprise_score for ep in self.episodes) / len(self.episodes)
        high_surprise = sum(1 for ep in self.episodes if ep.surprise_score > 0.7)
        
        return {
            "total_episodes": len(self.episodes),
            "avg_surprise": avg_surprise,
            "high_surprise_count": high_surprise
        }
