# src/interfaces/secret_sync_interface.py

from abc import ABC, abstractmethod


class SecretSyncInterface(ABC):
    """Abstract Interface for secret synchronization"""
    @abstractmethod
    def fetch_secrets(self):
        """Fetch secrets from the backend"""
        pass