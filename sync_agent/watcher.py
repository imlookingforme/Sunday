import time
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from config import Config
from sync_engine import SyncEngine
from conflict_resolver import ConflictResolver
from status import StatusIndicator


class SyncEventHandler(FileSystemEventHandler):
    def __init__(
        self,
        config: Config,
        sync_engine: SyncEngine,
        conflict_resolver: ConflictResolver,
        status: StatusIndicator,
        source_dir: Path,
        dest_dirs: list[Path],
        shared_sync_state: dict
    ):
        self.config = config
        self.sync_engine = sync_engine
        self.conflict_resolver = conflict_resolver
        self.status = status
        self.source_dir = source_dir
        self.dest_dirs = dest_dirs
        self.shared_sync_state = shared_sync_state  # Shared between handlers
        self.debounce_time = 0.5  # 500ms debounce
        self.ignore_time = 3.0  # Ignore events for 3 seconds after we write a file
        self.last_event_time = {}

    def _should_process_event(self, file_path: Path) -> bool:
        """Check if event should be processed (debounce and filter)."""
        # Check file patterns
        if not self.sync_engine.should_sync_file(file_path):
            return False
        
        # Check if we recently wrote this file (prevent sync loops)
        current_time = time.time()
        last_write = self.shared_sync_state.get(str(file_path), 0)
        if current_time - last_write < self.ignore_time:
            return False
        
        # Debounce check
        last_time = self.last_event_time.get(str(file_path), 0)
        if current_time - last_time < self.debounce_time:
            return False
        
        self.last_event_time[str(file_path)] = current_time
        return True

    def _get_dest_paths(self, file_path: Path) -> list[Path]:
        """Get corresponding paths in all destination directories."""
        paths = []
        try:
            rel_path = file_path.relative_to(self.source_dir)
            for dest_dir in self.dest_dirs:
                paths.append(dest_dir / rel_path)
            return paths
        except ValueError:
            return []

    def on_created(self, event: FileSystemEvent):
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        if not self._should_process_event(file_path):
            return
        
        dest_paths = self._get_dest_paths(file_path)
        if dest_paths:
            self.status.display_syncing(file_path.name)
            for dest_path in dest_paths:
                success = self.sync_engine.sync_file(file_path, dest_path, "created")
                if success:
                    # Mark both files as recently written to prevent sync loops
                    self.shared_sync_state[str(file_path)] = time.time()
                    self.shared_sync_state[str(dest_path)] = time.time()
            self.status.update_sync_time()
            self.status.display_idle()

    def on_modified(self, event: FileSystemEvent):
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        if not self._should_process_event(file_path):
            return
        
        dest_paths = self._get_dest_paths(file_path)
        if dest_paths:
            # Check for conflict
            has_conflict, conflicting_files = self.sync_engine.detect_conflict(
                file_path, self.source_dir, self.dest_dirs
            )
            
            if has_conflict:
                self.status.display_conflict(file_path.name)
                self.conflict_resolver.resolve_conflict(conflicting_files)
            else:
                self.status.display_syncing(file_path.name)
                for dest_path in dest_paths:
                    success = self.sync_engine.sync_file(file_path, dest_path, "modified")
                    if success:
                        self.shared_sync_state[str(file_path)] = time.time()
                        self.shared_sync_state[str(dest_path)] = time.time()
                self.status.update_sync_time()
            
            self.status.display_idle()

    def on_deleted(self, event: FileSystemEvent):
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        if not self._should_process_event(file_path):
            return
        
        self.status.display_syncing(f"Deleting {file_path.name}")
        for dest_dir in self.dest_dirs:
            self.sync_engine.delete_file(file_path, self.source_dir, dest_dir)
        self.status.update_sync_time()
        self.status.display_idle()

    def on_moved(self, event: FileSystemEvent):
        if event.is_directory:
            return
        
        src_path = Path(event.src_path)
        dest_path = Path(event.dest_path)
        
        if not self._should_process_event(src_path):
            return
        
        old_dests = self._get_dest_paths(src_path)
        new_dests = self._get_dest_paths(dest_path)
        
        if old_dests and new_dests:
            self.status.display_syncing(f"Moving {src_path.name}")
            
            for dest_dir in self.dest_dirs:
                # Delete old destination
                old_dest = dest_dir / src_path.relative_to(self.source_dir)
                if old_dest.exists():
                    self.sync_engine.delete_file(src_path, self.source_dir, dest_dir)
                
                # Sync new location
                new_dest = dest_dir / dest_path.relative_to(self.source_dir)
                success = self.sync_engine.sync_file(dest_path, new_dest, "moved")
                if success:
                    self.shared_sync_state[str(new_dest)] = time.time()
            self.shared_sync_state[str(dest_path)] = time.time()
                
            self.status.update_sync_time()
            self.status.display_idle()


class SyncWatcher:
    def __init__(self, config: Config, sync_engine: SyncEngine, 
                 conflict_resolver: ConflictResolver, status: StatusIndicator):
        self.config = config
        self.sync_engine = sync_engine
        self.conflict_resolver = conflict_resolver
        self.status = status
        self.observer = Observer()
        self.shared_sync_state = {}  # Shared state to prevent sync loops

    def start(self):
        """Start watching all configured directories."""
        directories = self.config.directories
        
        for name, source_dir in directories.items():
            dest_dirs = [d for n, d in directories.items() if n != name]
            handler = SyncEventHandler(
                self.config, self.sync_engine, self.conflict_resolver, self.status,
                source_dir, dest_dirs, self.shared_sync_state
            )
            self.observer.schedule(handler, str(source_dir), recursive=True)
            
        self.observer.start()
        self.status.display_idle()

    def stop(self):
        """Stop watching."""
        self.observer.stop()
        self.observer.join()

    def run_forever(self):
        """Run the watcher indefinitely."""
        try:
            self.start()
            while self.observer.is_alive():
                self.observer.join(1)
        except KeyboardInterrupt:
            self.stop()
