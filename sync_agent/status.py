from enum import Enum
from datetime import datetime
from colorama import Fore, Style, init


class SyncStatus(Enum):
    IDLE = "idle"
    SYNCING = "syncing"
    CONFLICT = "conflict"
    ERROR = "error"


class StatusIndicator:
    def __init__(self):
        init(autoreset=True)
        self.current_status = SyncStatus.IDLE
        self.last_sync_time = None
        self.message = ""

    def set_status(self, status: SyncStatus, message: str = ""):
        self.current_status = status
        self.message = message
        self._display_status()

    def update_sync_time(self):
        self.last_sync_time = datetime.now()

    def _display_status(self):
        timestamp = self.last_sync_time.strftime("%H:%M:%S") if self.last_sync_time else "Never"

        status_colors = {
            SyncStatus.IDLE: Fore.GREEN,
            SyncStatus.SYNCING: Fore.YELLOW,
            SyncStatus.CONFLICT: Fore.RED,
            SyncStatus.ERROR: Fore.RED
        }

        color = status_colors.get(self.current_status, Fore.WHITE)
        status_text = self.current_status.value.upper()

        print(f"{color}[{status_text}] {Style.RESET_ALL}{self.message} (Last sync: {timestamp})")

    def display_idle(self):
        self.set_status(SyncStatus.IDLE, "Sync agent running")

    def display_syncing(self, file_name: str):
        self.set_status(SyncStatus.SYNCING, f"Syncing: {file_name}")

    def display_conflict(self, file_name: str):
        self.set_status(SyncStatus.CONFLICT, f"Conflict detected: {file_name}")

    def display_error(self, error: str):
        self.set_status(SyncStatus.ERROR, f"Error: {error}")
