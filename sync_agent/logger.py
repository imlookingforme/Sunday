import json
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime
from typing import Dict, Any
from config import Config


class SyncLogger:
    def __init__(self, config: Config):
        self.config = config
        self.sync_logger = self._setup_logger('sync', self.config.log_dir / 'sync.log')
        self.conflict_logger = self._setup_logger('conflict', self.config.log_dir / 'conflict.log')

    def _setup_logger(self, name: str, log_path: Path) -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(logging.DEBUG)

        # Rotating file handler
        max_bytes = self.config.log_max_size_mb * 1024 * 1024
        handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=self.config.log_backup_count,
            encoding='utf-8'
        )

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        return logger

    def log_sync_start(self, source_path: Path, dest_path: Path, event_type: str):
        self.sync_logger.info(json.dumps({
            'event': 'sync_start',
            'source': str(source_path),
            'destination': str(dest_path),
            'event_type': event_type,
            'timestamp': datetime.now().isoformat()
        }))

    def log_sync_complete(self, source_path: Path, dest_path: Path, success: bool):
        self.sync_logger.info(json.dumps({
            'event': 'sync_complete',
            'source': str(source_path),
            'destination': str(dest_path),
            'success': success,
            'timestamp': datetime.now().isoformat()
        }))

    def log_conflict(self, file_path: Path, cursor_path: Path, devin_path: Path):
        self.conflict_logger.error(json.dumps({
            'event': 'conflict',
            'file': str(file_path),
            'cursor_version': str(cursor_path),
            'devin_version': str(devin_path),
            'timestamp': datetime.now().isoformat()
        }))

    def log_error(self, error: str, context: Dict[str, Any]):
        self.sync_logger.error(json.dumps({
            'event': 'error',
            'error': error,
            'context': context,
            'timestamp': datetime.now().isoformat()
        }))

    def log_backup(self, original_path: Path, backup_path: Path):
        self.sync_logger.info(json.dumps({
            'event': 'backup',
            'original': str(original_path),
            'backup': str(backup_path),
            'timestamp': datetime.now().isoformat()
        }))
