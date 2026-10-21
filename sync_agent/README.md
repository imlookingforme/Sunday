# Sunday Sync Agent

N-directory bidirectional mesh file synchronization agent for `.cursor`, `.devin`, `.antigravity`, and any other configured directories with conflict detection, logging, and automatic backups.

## Features

- **N-directory mesh sync**: Changes in any monitored directory automatically sync to all others
- **Smart conflict detection**: Detects concurrent modifications and generates highlighted diffs
- **Automatic backups**: Creates timestamped backups before overwriting files
- **Comprehensive logging**: JSON-structured logs for all sync operations
- **File filtering**: Only syncs `.md` and `.txt` files with configurable exclusion patterns
- **Status indicator**: Real-time sync status with color-coded console output
- **IDE integration**: Auto-starts with Cursor/Windsurf and stops when IDE closes

## Installation

1. **Install Python 3.8+** if not already installed

2. **Install dependencies**:
   ```bash
   cd sync_agent
   pip install -r requirements.txt
   ```

3. **Configure** (optional):
   Edit `config.yaml` to customize:
   - Directory paths
   - File patterns
   - Exclusion patterns
   - Backup retention
   - Logging settings

## Usage

### Manual Start

Run the sync agent manually:
```bash
python sync_agent.py
```

The agent will:
- Monitor all configured directories (`.cursor`, `.devin`, `.antigravity`, etc.)
- Sync changes automatically across the mesh
- Display status in the console
- Press `Ctrl+C` to stop

### IDE Integration

#### Cursor IDE

1. Edit `start_with_cursor.ps1` to verify the Cursor installation path
2. Run the script instead of launching Cursor directly:
   ```powershell
   .\sync_agent\start_with_cursor.ps1
   ```

#### Windsurf IDE

1. Edit `start_with_windsurf.ps1` to verify the Windsurf installation path
2. Run the script instead of launching Windsurf directly:
   ```powershell
   .\sync_agent\start_with_windsurf.ps1
   ```

### Desktop Shortcut (Optional)

Create a desktop shortcut that runs the PowerShell script:
1. Right-click desktop → New → Shortcut
2. Target: `powershell.exe -ExecutionPolicy Bypass -File "path\to\start_with_cursor.ps1"`
3. Name it "Cursor with Sync"

## Configuration

### Default Configuration

```yaml
directories:
  cursor: ".cursor"
  devin: ".devin"
  antigravity: ".antigravity"

file_patterns:
  - "*.md"
  - "*.txt"

exclude_patterns:
  - "*.tmp"
  - "*~"
  - ".gitkeep"
  - "*.swp"
  - "*.bak"

backup:
  enabled: true
  directory: ".sync_backups"
  retention_days: 7

logging:
  directory: ".sync_logs"
  max_size_mb: 10
  backup_count: 5

conflict:
  directory: ".sync_conflicts"
  auto_open_editor: true
```

### Customization

- **File patterns**: Add more file types to sync (e.g., `*.json`, `*.yaml`)
- **Exclusion patterns**: Ignore temporary files, swap files, etc.
- **Backup retention**: Adjust how long to keep backups
- **Logging**: Change log size limits and backup count
- **Conflict editor**: Set to `false` to disable auto-opening conflict files

## Conflict Resolution

When versions of a file change concurrently in multiple directories:

1. Sync agent detects the conflict
2. Creates a conflict file in `.sync_conflicts/` with:
   - Timestamps of both versions
   - Unified diff with highlighted differences
   - Resolution instructions
3. Opens the conflict file in your default editor (if enabled)
4. Original files remain unchanged
5. Edit either original file with your resolution
6. Sync agent will propagate your changes automatically

## Directory Structure

```
sync_agent/
├── sync_agent.py              # Main entry point
├── watcher.py                 # File system event handler
├── sync_engine.py            # Sync logic and conflict detection
├── conflict_resolver.py      # Diff generation and conflict handling
├── config.py                 # Configuration management
├── logger.py                 # Logging system
├── status.py                 # Status indicator
├── config.yaml               # Configuration file
├── requirements.txt          # Python dependencies
├── start_with_cursor.ps1     # Cursor startup script
├── start_with_windsurf.ps1   # Windsurf startup script
├── README.md                 # This file
├── .sync_backups/            # Backup directory (auto-created)
├── .sync_logs/               # Log directory (auto-created)
└── .sync_conflicts/          # Conflict directory (auto-created)
```

## Logging

Logs are stored in `.sync_logs/`:

- **sync.log**: All sync operations (JSON format)
- **conflict.log**: Conflict events only

Logs rotate when they reach the size limit (default: 10MB).

## Troubleshooting

### Sync agent not starting

- Check Python is installed: `python --version`
- Verify dependencies: `pip list`
- Check config.yaml exists and is valid YAML

### Files not syncing

- Verify file extensions match `file_patterns` in config
- Check files aren't matched by `exclude_patterns`
- Ensure both directories exist

### Conflicts not detected

- Conflict detection requires both files to have changed since last sync
- Check logs for conflict events
- Verify sync state is being tracked

### IDE integration not working

- Verify IDE installation path in PowerShell script
- Run PowerShell script manually to test
- Check execution policy: `Set-ExecutionPolicy RemoteSigned`

## Performance

- **CPU usage**: Minimal (event-driven, no polling)
- **Memory usage**: ~50MB
- **Latency**: <1 second from file change to sync

## Security

- No network connections (local-only)
- No external dependencies beyond Python packages
- Backups prevent data loss
- Atomic file operations prevent corruption

## License

Part of the Sunday Personal Agent project.
