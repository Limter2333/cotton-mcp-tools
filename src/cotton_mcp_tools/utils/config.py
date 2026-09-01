"""Configuration management for MCP tools.

Centralizes environment variables and settings.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    # Add your configuration fields here
    debug: bool = field(default_factory=lambda: os.getenv("COTTON_DEBUG", "false").lower() == "true")
    log_level: str = field(default_factory=lambda: os.getenv("COTTON_LOG_LEVEL", "INFO"))

    @classmethod
    def from_env(cls) -> Config:
        """Create a Config instance from environment variables."""
        return cls()


# Global config singleton
_config: Config | None = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config
