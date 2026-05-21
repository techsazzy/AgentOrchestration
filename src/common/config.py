"""Configuration management for the agent orchestrator."""

import os
import json
from typing import Any, Dict, Optional


class Config:
    """Manages system configuration and environment overrides."""

    def __init__(self, path: str = None):
        self._data = {}
        if path and os.path.exists(path):
            self._load_file(path)
        self._load_env_overrides()

    def _load_file(self, path: str) -> None:
        with open(path) as f:
            self._data = json.load(f)

    def _load_env_overrides(self) -> None:
        prefix = "AO_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower().replace("_", ".")
                # Only override if the key already exists in the config to avoid
                # importing unrelated environment variables (Issue #1402)
                if self.get(config_key) is not None:
                    self._set_nested(config_key, value)

    def _set_nested(self, key: str, value: Any) -> None:
        parts = key.split(".")
        current = self._data
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by dot-notated key."""
        parts = key.split(".")
        current = self._data
        try:
            for part in parts:
                current = current.get(part)
            return current if current is not None else default
        except (AttributeError, TypeError):
            return default
