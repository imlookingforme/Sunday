"""Hash-chained audit ledger for tamper-evident logging."""

from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional
import json
import hashlib
import asyncio


@dataclass
class AuditEntry:
    """Single audit log entry."""
    timestamp: str
    tool: str
    actor: str
    channel: str
    args: dict
    result: any
    success: bool
    risk: str
    previous_hash: str
    hash: str


class AuditLedger:
    """Hash-chained audit ledger for tamper-evident logging."""
    
    def __init__(self, log_path: Path):
        self.log_path = log_path
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._last_hash = ""
        self._lock = asyncio.Lock()
        
    async def log(
        self,
        tool: str,
        actor: str,
        channel: str,
        args: dict,
        result: any,
        success: bool,
        risk: str
    ) -> None:
        """Append an audit entry to the ledger."""
        async with self._lock:
            entry = await self._create_entry(
                tool=tool,
                actor=actor,
                channel=channel,
                args=args,
                result=result,
                success=success,
                risk=risk
            )
            await self._append_entry(entry)
            self._last_hash = entry.hash
    
    async def _create_entry(
        self,
        tool: str,
        actor: str,
        channel: str,
        args: dict,
        result: any,
        success: bool,
        risk: str
    ) -> AuditEntry:
        """Create an audit entry with hash chain."""
        timestamp = datetime.utcnow().isoformat()
        
        # Serialize data for hashing
        data = {
            "timestamp": timestamp,
            "tool": tool,
            "actor": actor,
            "channel": channel,
            "args": args,
            "result": str(result),
            "success": success,
            "risk": risk,
            "previous_hash": self._last_hash
        }
        
        # Calculate hash
        hash_input = json.dumps(data, sort_keys=True, default=str)
        entry_hash = hashlib.sha256(hash_input.encode()).hexdigest()
        
        return AuditEntry(
            timestamp=timestamp,
            tool=tool,
            actor=actor,
            channel=channel,
            args=args,
            result=result,
            success=success,
            risk=risk,
            previous_hash=self._last_hash,
            hash=entry_hash
        )
    
    async def _append_entry(self, entry: AuditEntry) -> None:
        """Append entry to log file."""
        def _write():
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(entry), default=str) + "\n")
        await asyncio.to_thread(_write)
    
    async def verify_integrity(self) -> bool:
        """Verify the hash chain integrity of the ledger."""
        if not self.log_path.exists():
            return True
        
        with open(self.log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        previous_hash = ""
        for line in lines:
            entry_data = json.loads(line)
            entry_hash = entry_data["hash"]
            entry_data["hash"] = ""  # Clear hash for verification
            
            # Recalculate hash
            hash_input = json.dumps(entry_data, sort_keys=True, default=str)
            calculated_hash = hashlib.sha256(hash_input.encode()).hexdigest()
            
            if calculated_hash != entry_hash:
                return False
            
            if entry_data["previous_hash"] != previous_hash:
                return False
            
            previous_hash = entry_hash
        
        return True
    
    async def get_recent_entries(self, limit: int = 100) -> list[AuditEntry]:
        """Get recent audit entries."""
        if not self.log_path.exists():
            return []
        
        entries = []
        with open(self.log_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        for line in lines[-limit:]:
            entry_data = json.loads(line)
            entries.append(AuditEntry(**entry_data))
        
        return entries
