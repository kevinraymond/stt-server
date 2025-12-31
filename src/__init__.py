# STT Server package
"""Local speech-to-text server for Obsidian using Whisper."""

from .config import (
    ServerConfig,
    TranscriberConfig,
    get_optimal_config,
    get_hardware_info,
)
from .server import STTServer, run_server

__version__ = "0.1.0"
__all__ = [
    "ServerConfig",
    "TranscriberConfig",
    "STTServer",
    "run_server",
    "get_optimal_config",
    "get_hardware_info",
]
