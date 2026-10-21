import hashlib
import shutil
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
from config import Config
from logger import SyncLogger


class SyncEngine:
    def __init__(self, config: Config, logger: SyncLogger):
        self.config = config
        self.logger = logger
        self.sync_state = {}  # Track last sync state for conflict detection

    def get_file_hash(self, file_path: Path, max_retries: int = 3) -> str:
        """Calculate SHA-256 hash of a file with retry logic for locked files."""
        if not file_path.exists():
            return ""

        for attempt in range(max_retries):
            try:
                hasher = hashlib.sha256()
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hasher.update(chunk)
                return hasher.hexdigest()
            except (PermissionError, IOError) as e:
                if attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))  # Exponential backoff
                else:
                    self.logger.log_error(f"Failed to read file for hashing: {str(e)}", {
                        'file': str(file_path)
                    })
                    return ""

    def should_sync_file(self, file_path: Path) -> bool:
        """Check if file matches sync criteria."""
        # Check file extension
        if not any(file_path.match(pattern) for pattern in self.config.file_patterns):
            return False

        # Check exclusion patterns
        if any(file_path.match(pattern) for pattern in self.config.exclude_patterns):
            return False

        return True

    def create_backup(self, file_path: Path) -> Optional[Path]:
        """Create timestamped backup of a file."""
        if not self.config.backup_enabled:
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.name}.{timestamp}.backup"
        backup_path = self.config.backup_dir / backup_name

        try:
            shutil.copy2(file_path, backup_path)
            self.logger.log_backup(file_path, backup_path)
            return backup_path
        except Exception as e:
            self.logger.log_error(f"Backup failed: {str(e)}", {'file': str(file_path)})
            return None

    def sync_file(self, source: Path, dest: Path, event_type: str) -> bool:
        """Sync a file from source to destination."""
        try:
            self.logger.log_sync_start(source, dest, event_type)

            # Check if destination exists and create backup
            if dest.exists():
                self.create_backup(dest)

            # Ensure destination directory exists
            dest.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(source, dest)

            # Update sync state
            self.sync_state[str(source)] = self.get_file_hash(source)
            self.sync_state[str(dest)] = self.get_file_hash(dest)

            self.logger.log_sync_complete(source, dest, True)
            return True

        except Exception as e:
            self.logger.log_error(f"Sync failed: {str(e)}", {
                'source': str(source),
                'destination': str(dest)
            })
            self.logger.log_sync_complete(source, dest, False)
            return False

    def detect_conflict(self, file_path: Path, source_dir: Path, dest_dirs: list[Path]) -> Tuple[bool, list[Path]]:
        """Detect if there's a conflict between versions in different directories."""
        # Get relative path
        try:
            rel_path = file_path.relative_to(source_dir)
        except ValueError:
            return False, []

        conflicting_files = [file_path]
        has_conflict = False
        current_hash = self.get_file_hash(file_path)
        last_sync_hash = self.sync_state.get(str(file_path))

        for dest_dir in dest_dirs:
            other_file = dest_dir / rel_path
            if not other_file.exists():
                continue

            other_hash = self.get_file_hash(other_file)
            last_other_sync_hash = self.sync_state.get(str(other_file))

            # Conflict if both changed since last sync
            if (last_sync_hash and last_other_sync_hash and
                current_hash != last_sync_hash and
                other_hash != last_other_sync_hash):
                conflicting_files.append(other_file)
                has_conflict = True

        if has_conflict:
            return True, conflicting_files

        return False, []

    def delete_file(self, file_path: Path, source_dir: Path, dest_dir: Path) -> bool:
        """Delete corresponding file in other directory."""
        try:
            rel_path = file_path.relative_to(source_dir)
            other_file = dest_dir / rel_path

            if other_file.exists():
                self.create_backup(other_file)
                other_file.unlink()
                return True
            return True
        except Exception as e:
            self.logger.log_error(f"Delete failed: {str(e)}", {'file': str(file_path)})
            return False

    def cleanup_old_backups(self):
        """Remove backups older than retention period."""
        if not self.config.backup_enabled:
            return

        cutoff_date = datetime.now().timestamp() - (self.config.backup_retention_days * 86400)

        for backup_file in self.config.backup_dir.glob("*.backup"):
            if backup_file.stat().st_mtime < cutoff_date:
                try:
                    backup_file.unlink()
                except Exception as e:
                    self.logger.log_error(f"Backup cleanup failed: {str(e)}", {
                        'backup': str(backup_file)
                    })
