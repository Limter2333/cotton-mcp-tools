"""Configuration management for MCP tools.

Centralizes environment variables and settings.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class Config:
    """Application configuration loaded from environment variables."""

    debug: bool = field(
        default_factory=lambda: os.getenv(
            "COTTON_DEBUG", "false"
        ).lower() == "true"
    )
    log_level: str = field(
        default_factory=lambda: os.getenv("COTTON_LOG_LEVEL", "INFO")
    )

    # Multimodal API keys
    openai_api_key: str = field(
        default_factory=lambda: os.getenv("OPENAI_API_KEY", "")
    )
    anthropic_api_key: str = field(
        default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", "")
    )

    # Multimodal defaults
    default_provider: str = field(
        default_factory=lambda: os.getenv("MULTIMODAL_PROVIDER", "openai")
    )
    default_model: str = field(
        default_factory=lambda: os.getenv("MULTIMODAL_MODEL", "gpt-4o")
    )

    # Xiaohongshu (XHS) settings
    xhs_cookie: str = field(
        default_factory=lambda: os.getenv("XHS_COOKIE", "")
    )
    xhs_proxy: str = field(
        default_factory=lambda: os.getenv("XHS_PROXY", "")
    )

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
