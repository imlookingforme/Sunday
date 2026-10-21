"""Multi-Account Token & Session Pool for automatic credential rotation.

Manages:
- Multiple API keys per provider (OpenAI, Anthropic, Gemini, etc.)
- Multiple browser session profiles
- Automatic failover on 429 / quota exhaustion
- Rate-limit backoff timers per exhausted key
"""

import asyncio
import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Marker value for "no key available" 
_SENTINEL = object()


class CredentialEntry:
    """A single credential (API key or session token) with usage tracking."""
    
    def __init__(self, value: str, provider: str, label: str = ""):
        self.value = value
        self.provider = provider
        self.label = label or f"{provider}_{value[:8]}"
        self.exhausted_at: Optional[float] = None  # Unix timestamp when exhausted
        self.backoff_seconds: float = 60.0          # Initial backoff on 429
        self.error_count: int = 0

    @property
    def is_available(self) -> bool:
        """True if this credential is currently usable."""
        if self.exhausted_at is None:
            return True
        elapsed = time.time() - self.exhausted_at
        if elapsed >= self.backoff_seconds:
            # Backoff period expired — reset and mark available again
            self.exhausted_at = None
            self.error_count = 0
            self.backoff_seconds = min(self.backoff_seconds * 0.5, 60.0)  # Reduce backoff
            logger.info(f"Credential [{self.label}] recovered after backoff.")
            return True
        return False

    def mark_exhausted(self) -> None:
        """Mark as exhausted (rate-limited or quota exceeded)."""
        self.exhausted_at = time.time()
        self.error_count += 1
        # Exponential backoff up to 30 min
        self.backoff_seconds = min(self.backoff_seconds * 2.0, 1800.0)
        logger.warning(
            f"Credential [{self.label}] exhausted. Backoff: {self.backoff_seconds:.0f}s "
            f"(errors={self.error_count})"
        )


class TokenPool:
    """
    Manages pools of credentials per provider and exposes simple
    get_key() / mark_exhausted() / rotate_key() APIs.
    """

    def __init__(self):
        # provider -> list of CredentialEntry
        self._pools: Dict[str, List[CredentialEntry]] = defaultdict(list)
        # provider -> current active index
        self._current_index: Dict[str, int] = defaultdict(int)
        self._lock = asyncio.Lock()
        self._load_from_env()

    def _load_from_env(self):
        """Load known API keys from environment variables or .env."""
        import os
        from dotenv import load_dotenv
        
        # Load from .env if it exists
        dotenv_path = os.environ.get("DOTENV_PATH", ".env")
        if os.path.exists(dotenv_path):
            load_dotenv(dotenv_path)
        
        # Load OpenAI
        openai_key = os.environ.get("OPENAI_API_KEY")
        if openai_key:
            self.add_key("openai", openai_key, "env_openai")
            
        # Load Anthropic
        anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        if anthropic_key:
            self.add_key("anthropic", anthropic_key, "env_anthropic")
            
        # Load SerpAPI
        serp_key = os.environ.get("SERPAPI_API_KEY")
        if serp_key:
            self.add_key("serpapi", serp_key, "env_serpapi")

    def add_key(self, provider: str, key: str, label: str = "") -> None:
        """Register a single API key or session token for a provider."""
        entry = CredentialEntry(value=key, provider=provider, label=label)
        self._pools[provider].append(entry)
        logger.info(f"Registered credential [{entry.label}] for provider [{provider}].")

    def add_keys(self, provider: str, keys: List[str]) -> None:
        """Register multiple keys for a provider."""
        for key in keys:
            self.add_key(provider, key)

    def get_key(self, provider: str) -> Optional[str]:
        """
        Return the currently active key for a provider.
        Automatically skips exhausted keys by scanning forward.
        """
        pool = self._pools.get(provider, [])
        if not pool:
            return None

        # Round-robin scan for an available key
        n = len(pool)
        start_idx = self._current_index[provider] % n
        for offset in range(n):
            idx = (start_idx + offset) % n
            entry = pool[idx]
            if entry.is_available:
                self._current_index[provider] = idx
                return entry.value

        # All exhausted — return the first anyway with a warning
        logger.warning(f"All {n} credentials for [{provider}] are exhausted. Using first.")
        self._current_index[provider] = 0
        return pool[0].value

    def mark_exhausted(self, provider: str, key: Optional[str] = None) -> Optional[str]:
        """
        Mark the current (or specified) key for a provider as exhausted.
        Automatically rotates to the next available key and returns it.
        """
        pool = self._pools.get(provider, [])
        if not pool:
            return None

        # Find the matching entry
        if key:
            for entry in pool:
                if entry.value == key:
                    entry.mark_exhausted()
                    break
        else:
            # Mark current
            idx = self._current_index[provider] % len(pool)
            pool[idx].mark_exhausted()

        # Rotate to next available
        return self.rotate(provider)

    def rotate(self, provider: str) -> Optional[str]:
        """Rotate to the next available credential. Returns new active key."""
        pool = self._pools.get(provider, [])
        if not pool:
            return None

        n = len(pool)
        if n == 1:
            logger.warning(f"Only 1 credential for [{provider}], cannot rotate further.")
            return pool[0].value if pool[0].is_available else None

        current = self._current_index.get(provider, 0)
        for offset in range(1, n + 1):
            idx = (current + offset) % n
            if pool[idx].is_available:
                self._current_index[provider] = idx
                logger.info(f"Rotated [{provider}] to credential [{pool[idx].label}].")
                return pool[idx].value

        logger.error(f"No available credentials for [{provider}] after rotation scan.")
        return None

    def get_pool_status(self, provider: str) -> Dict[str, Any]:
        """Return a status summary of a provider's credential pool."""
        pool = self._pools.get(provider, [])
        return {
            "provider": provider,
            "total": len(pool),
            "available": sum(1 for e in pool if e.is_available),
            "exhausted": sum(1 for e in pool if not e.is_available),
            "current_index": self._current_index.get(provider, 0),
        }

    def list_providers(self) -> List[str]:
        """List all registered providers."""
        return list(self._pools.keys())

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Return status for all registered providers."""
        return {provider: self.get_pool_status(provider) for provider in self._pools}
