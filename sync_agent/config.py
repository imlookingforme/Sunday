import yaml
import os
from pathlib import Path
from typing import Dict, List, Any


class Config:
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._validate_config()
        self._create_directories()

    def _load_config(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def _validate_config(self):
        required_keys = ['directories', 'file_patterns']
        for key in required_keys:
            if key not in self.config:
                raise ValueError(f"Missing required config key: {key}")

    def _create_directories(self):
        base_dir = self.config_path.parent
        directories = [
            self.config['backup']['directory'],
            self.config['logging']['directory'],
            self.config['conflict']['directory']
        ]
        
        for dir_name in directories:
            dir_path = base_dir / dir_name
            dir_path.mkdir(parents=True, exist_ok=True)

    @property
    def directories(self) -> Dict[str, Path]:
        base_dir = self.config_path.parent
        return {
            name: base_dir / rel_path 
            for name, rel_path in self.config['directories'].items()
        }

    @property
    def cursor_dir(self) -> Path:
        return self.config_path.parent / self.config['directories']['cursor']

    @property
    def devin_dir(self) -> Path:
        return self.config_path.parent / self.config['directories']['devin']

    @property
    def antigravity_dir(self) -> Path:
        return self.config_path.parent / self.config['directories']['antigravity']

    @property
    def file_patterns(self) -> List[str]:
        return self.config['file_patterns']

    @property
    def exclude_patterns(self) -> List[str]:
        return self.config.get('exclude_patterns', [])

    @property
    def backup_dir(self) -> Path:
        return self.config_path.parent / self.config['backup']['directory']

    @property
    def backup_enabled(self) -> bool:
        return self.config['backup'].get('enabled', True)

    @property
    def backup_retention_days(self) -> int:
        return self.config['backup'].get('retention_days', 7)

    @property
    def log_dir(self) -> Path:
        return self.config_path.parent / self.config['logging']['directory']

    @property
    def log_max_size_mb(self) -> int:
        return self.config['logging'].get('max_size_mb', 10)

    @property
    def log_backup_count(self) -> int:
        return self.config['logging'].get('backup_count', 5)

    @property
    def conflict_dir(self) -> Path:
        return self.config_path.parent / self.config['conflict']['directory']

    @property
    def conflict_auto_open_editor(self) -> bool:
        return self.config['conflict'].get('auto_open_editor', True)
