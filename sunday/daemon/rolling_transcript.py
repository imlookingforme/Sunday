"""Rolling transcript buffer for conversational awareness (isair/jarvis pattern)."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional


@dataclass
class TranscriptEntry:
    """A single transcript entry."""
    text: str
    speaker: str  # "user", "sunday", "other"
    timestamp: datetime
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class RollingTranscript:
    """Rolling transcript buffer for conversational awareness.

    Provides "third person in the room" capability - Sunday can understand
    context from recent conversation even when not directly addressed.
    """

    def __init__(self, window_seconds: int = 120):
        """Initialize rolling transcript with time window.

        Args:
            window_seconds: How many seconds of conversation to retain
        """
        self.window_seconds = window_seconds
        self.transcript: List[TranscriptEntry] = []

    def add(self, text: str, speaker: str = "user", metadata: dict = None) -> None:
        """Add a transcript entry."""
        entry = TranscriptEntry(
            text=text,
            speaker=speaker,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        self.transcript.append(entry)
        self._prune_old()

    def get_context(self, max_entries: int = 20) -> str:
        """Get recent context as formatted string."""
        self._prune_old()
        recent = self.transcript[-max_entries:]
        return "\n".join(
            f"[{e.timestamp.strftime('%H:%M:%S')}] {e.speaker}: {e.text}"
            for e in recent
        )

    def get_recent_by_speaker(self, speaker: str, limit: int = 5) -> List[TranscriptEntry]:
        """Get recent entries from a specific speaker."""
        self._prune_old()
        speaker_entries = [e for e in self.transcript if e.speaker == speaker]
        return speaker_entries[-limit:]

    def search(self, query: str, limit: int = 5) -> List[TranscriptEntry]:
        """Search transcript for query (case-insensitive)."""
        self._prune_old()
        query_lower = query.lower()
        matches = [
            e for e in self.transcript
            if query_lower in e.text.lower()
        ]
        return matches[-limit:]

    def get_last_user_input(self) -> Optional[str]:
        """Get the last user input."""
        user_entries = self.get_recent_by_speaker("user", 1)
        return user_entries[0].text if user_entries else None

    def get_last_sunday_response(self) -> Optional[str]:
        """Get the last Sunday response."""
        sunday_entries = self.get_recent_by_speaker("sunday", 1)
        return sunday_entries[0].text if sunday_entries else None

    def _prune_old(self) -> None:
        """Remove entries older than window."""
        cutoff = datetime.now() - timedelta(seconds=self.window_seconds)
        self.transcript = [e for e in self.transcript
                          if e.timestamp > cutoff]

    def clear(self) -> None:
        """Clear all transcript entries."""
        self.transcript.clear()

    def get_entry_count(self) -> int:
        """Get number of entries in transcript."""
        return len(self.transcript)

    def get_duration(self) -> float:
        """Get duration of transcript in seconds."""
        if not self.transcript:
            return 0.0
        return (self.transcript[-1].timestamp - self.transcript[0].timestamp).total_seconds()
