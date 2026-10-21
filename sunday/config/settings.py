"""Settings management for Sunday."""

import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field


@dataclass
class LLMSettings:
    """LLM configuration."""
    provider: str = "ollama"
    model: str = "llama3.1"
    base_url: str = "http://localhost:11434"
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 30


@dataclass
class VoiceSettings:
    """Voice pipeline configuration."""
    wake_word: str = "sunday"
    wake_word_model: str = "sunday"
    stt_model: str = "base"
    tts_model: str = "en_US-lessac-medium"
    tts_fallback: str = "edge-tts"
    sample_rate: int = 16000
    channels: int = 1


@dataclass
class MemorySettings:
    """Memory system configuration."""
    db_path: str = "sunday/memory/sunday.db"
    vector_db_path: str = "sunday/memory/vectors"
    embedding_model: str = "all-MiniLM-L6-v2"
    max_conversation_history: int = 100
    memory_retention_days: int = 365


@dataclass
class ToolSettings:
    """Tool system configuration."""
    require_approval: bool = True
    approval_threshold: str = "high"
    max_concurrent_tools: int = 5
    tool_timeout: int = 60


@dataclass
class Settings:
    """Main settings class for Sunday."""
    llm: LLMSettings = field(default_factory=LLMSettings)
    voice: VoiceSettings = field(default_factory=VoiceSettings)
    memory: MemorySettings = field(default_factory=MemorySettings)
    tools: ToolSettings = field(default_factory=ToolSettings)
    
    # Paths
    config_dir: Path = field(default_factory=lambda: Path("sunday/config"))
    data_dir: Path = field(default_factory=lambda: Path("sunday/data"))
    
    @classmethod
    def from_yaml(cls, config_path: Path) -> "Settings":
        """Load settings from YAML file."""
        if not config_path.exists():
            return cls()
        
        with open(config_path, "r") as f:
            config_data = yaml.safe_load(f) or {}
        
        return cls._from_dict(config_data)
    
    @classmethod
    def _from_dict(cls, data: Dict[str, Any]) -> "Settings":
        """Create settings from dictionary."""
        settings = cls()
        
        if "llm" in data:
            settings.llm = LLMSettings(**data["llm"])
        if "voice" in data:
            settings.voice = VoiceSettings(**data["voice"])
        if "memory" in data:
            settings.memory = MemorySettings(**data["memory"])
        if "tools" in data:
            settings.tools = ToolSettings(**data["tools"])
        
        return settings
    
    def to_yaml(self, config_path: Path) -> None:
        """Save settings to YAML file."""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            "llm": self.llm.__dict__,
            "voice": self.voice.__dict__,
            "memory": self.memory.__dict__,
            "tools": self.tools.__dict__,
        }
        
        with open(config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)
