import sys
import asyncio
from pathlib import Path
from config import Config
from logger import SyncLogger
from sync_engine import SyncEngine
from conflict_resolver import ConflictResolver
from status import StatusIndicator
from watcher import SyncWatcher


def main():
    # Initialize components
    script_dir = Path(__file__).parent
    config_path = script_dir / "config.yaml"

    try:
        config = Config(config_path)
        logger = SyncLogger(config)
        sync_engine = SyncEngine(config, logger)
        conflict_resolver = ConflictResolver(config, logger)
        status = StatusIndicator()

        # Clean up old backups on startup
        sync_engine.cleanup_old_backups()

        # Start the watcher
        watcher = SyncWatcher(config, sync_engine, conflict_resolver, status)

        print("Sunday Sync Agent Starting...")
        print("Monitoring directories:")
        for name, dir_path in config.directories.items():
            print(f"  - {name}: {dir_path}")
        print("Press Ctrl+C to stop")

        watcher.run_forever()

    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nSync agent stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
