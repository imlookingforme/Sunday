"""Secret vault for secure credential storage."""

from abc import ABC, abstractmethod
from typing import Optional
import os
import keyring
from pathlib import Path


class Vault(ABC):
    """Abstract base class for secret vaults."""

    @abstractmethod
    async def get_secret(self, name: str) -> Optional[str]:
        """Retrieve a secret by name."""
        pass

    @abstractmethod
    async def set_secret(self, name: str, value: str) -> None:
        """Store a secret by name."""
        pass


class KeyringVault(Vault):
    """OS keystore-based vault using keyring library."""

    def __init__(self, service_name: str = "Sunday"):
        self.service_name = service_name

    async def get_secret(self, name: str) -> Optional[str]:
        """Retrieve secret from OS keystore."""
        try:
            secret = keyring.get_password(self.service_name, name)
            return secret
        except Exception:
            return None

    async def set_secret(self, name: str, value: str) -> None:
        """Store secret in OS keystore."""
        try:
            keyring.set_password(self.service_name, name, value)
        except Exception as e:
            raise RuntimeError(f"Failed to store secret in keyring: {e}")


class EnvVault(Vault):
    """Environment variable-based vault (fallback)."""

    async def get_secret(self, name: str) -> Optional[str]:
        """Retrieve secret from environment variables."""
        return os.getenv(name)

    async def set_secret(self, name: str, value: str) -> None:
        """Cannot set environment variables at runtime."""
        raise RuntimeError("EnvVault is read-only. Set secrets in environment before startup.")


class FileVault(Vault):
    """File-based vault (fallback, not recommended for production)."""

    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.vault_path.parent.mkdir(parents=True, exist_ok=True)
        self._secrets: dict = {}
        self._load()

    def _load(self) -> None:
        """Load secrets from file."""
        if self.vault_path.exists():
            import json
            with open(self.vault_path, "r") as f:
                self._secrets = json.load(f)

    def _save(self) -> None:
        """Save secrets to file."""
        import json
        with open(self.vault_path, "w") as f:
            json.dump(self._secrets, f)

    async def get_secret(self, name: str) -> Optional[str]:
        """Retrieve secret from file."""
        return self._secrets.get(name)

    async def set_secret(self, name: str, value: str) -> None:
        """Store secret in file."""
        self._secrets[name] = value
        self._save()
