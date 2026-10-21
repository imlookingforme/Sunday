"""Environment variable and .env loader for Sunday's TokenPool and credentials."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def parse_env_file(env_path: Path | str) -> Dict[str, str]:
    """Parse a .env file without external dependencies."""
    path = Path(env_path)
    if not path.is_file():
        return {}

    env_vars: Dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    if key and val:
                        env_vars[key] = val
    except Exception as e:
        logger.warning(f"Error reading .env from {path}: {e}")

    return env_vars


def load_env_into_environ(env_path: Optional[Path | str] = None) -> None:
    """Load variables from .env into os.environ if not already present."""
    search_paths = []
    if env_path:
        search_paths.append(Path(env_path))

    # Also check current working directory and repo root
    search_paths.append(Path.cwd() / ".env")
    search_paths.append(Path(__file__).resolve().parent.parent.parent.parent / ".env")

    for p in search_paths:
        if p.is_file():
            parsed = parse_env_file(p)
            for k, v in parsed.items():
                if k not in os.environ and v:
                    os.environ[k] = v
            logger.info(f"Loaded {len(parsed)} variables from {p}")
            break


def populate_token_pool_from_env(pool: Any) -> None:
    """Scan os.environ for known LLM provider keys and populate a TokenPool."""
    load_env_into_environ()

    providers = {
        "openai": ["OPENAI_API_KEY", "OPENAI_API_KEY_2", "OPENAI_API_KEY_3"],
        "anthropic": ["ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY_2", "ANTHROPIC_API_KEY_3"],
        "gemini": ["GEMINI_API_KEY", "GEMINI_API_KEY_2", "GOOGLE_API_KEY"],
        "groq": ["GROQ_API_KEY"],
        "mistral": ["MISTRAL_API_KEY"],
    }

    for provider, env_keys in providers.items():
        for env_key in env_keys:
            val = os.environ.get(env_key)
            if val and val.strip():
                pool.add_key(provider=provider, key=val.strip(), label=env_key)
