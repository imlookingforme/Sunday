"""Entity Extractor - Extracts named entities (apps, tools, files, times, contacts) from natural language."""

import logging
import re
from typing import Any

from sunday.core.intelligence.hf_model_loader import HFModelLoader

logger = logging.getLogger(__name__)


class EntityExtractor:
    """Extracts entities to enable seamless natural language tool argument population."""

    COMMON_APPS = [
        "cursor",
        "antigravity",
        "devin",
        "claude",
        "chatgpt",
        "chrome",
        "firefox",
        "spotify",
        "vscode",
        "terminal",
        "powershell",
        "notion",
        "slack",
    ]

    TIME_PATTERNS = [
        r"\b\d+\s*(?:minutes?|mins?|hours?|hrs?|seconds?|secs?)\b",
        r"\b(?:tomorrow|today|tonight|yesterday)\b",
        r"\bat\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)?\b",
        r"\bin\s*\d+\s*(?:minutes?|hours?|days?)\b",
    ]

    def __init__(self, enable_hf: bool = False):
        self.enable_hf = enable_hf
        self.loader = HFModelLoader()

    def extract_entities(self, text: str) -> dict[str, Any]:
        """Extracts structured entities from input text."""
        entities: dict[str, Any] = {
            "apps": [],
            "time_expressions": [],
            "files": [],
            "named_entities": [],
        }

        lowered = text.lower()

        # 1. App name extraction
        for app in self.COMMON_APPS:
            if re.search(rf"\b{re.escape(app)}\b", lowered):
                entities["apps"].append(app)

        # 2. Time expressions
        for pat in self.TIME_PATTERNS:
            matches = re.findall(pat, lowered)
            entities["time_expressions"].extend(matches)

        # 3. File references (e.g., script.py, todo.md, data.json)
        file_matches = re.findall(r"\b[\w\-_]+\.(?:py|md|json|yaml|yml|txt|csv|html|js|ts)\b", text)
        entities["files"].extend(file_matches)

        # 4. Neural NER (if enabled and model available)
        if self.enable_hf:
            ner_pipe = self.loader.get_ner_pipeline()
            if ner_pipe:
                try:
                    res = ner_pipe(text)
                    for item in res:
                        entities["named_entities"].append(
                            {
                                "word": item.get("word"),
                                "entity": item.get("entity_group", item.get("entity")),
                                "score": float(item.get("score", 0.0)),
                            }
                        )
                except Exception as e:
                    logger.debug(f"NER extraction error: {e}")

        return entities
