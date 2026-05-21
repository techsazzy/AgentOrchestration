"""Configuration management module."""

import os
import json
from typing import Any, Dict, Optional


class Config:
    def __init__(self, config_path: Optional[str] = None):
        self._path = config_path
        self._data: Dict[str, Any] = {}
        self.reload()

    def reload(self) -> None:
        """Reload configuration from file and environment atomically."""
        new_data = {}
        if self._path and os.path.exists(self._path):
            with open(self._path) as f:
                new_data = json.load(f)
        
        # Apply environment overrides to the new data before swapping
        self._apply_env_overrides(new_data)
        
        # Atomic swap
        self._data = new_data

    def _apply_env_overrides(self, data: Dict[str, Any]) -> None:
        prefix = "AO_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                config_key = key[len(prefix):].lower().replace("_", ".")
                # Issue #1402: Only override if the key already exists
                if self._get_nested_from_dict(config_key, data) is not None:
                    self._set_nested_in_dict(config_key, value, data)

    def _set_nested_in_dict(self, key: str, value: Any, data: Dict[str, Any]) -> None:
        parts = key.split(".")
        current = data
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    def _get_nested_from_dict(self, key: str, data: Dict[str, Any], default: Any = None) -> Any:
        parts = key.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
                if current is None:
                    return default
            else:
                return default
        return current

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by dot-notated key."""
        return self._get_nested_from_dict(key, self._data, default)

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        self._set_nested_in_dict(key, value, self._data)

    def to_dict(self) -> Dict:
        """Return the configuration as a dictionary."""
        return self._data.copy()
