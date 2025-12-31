"""Configuration for the STT server."""

from dataclasses import dataclass
from typing import Literal
import os


@dataclass
class ServerConfig:
    """WebSocket server configuration."""
    host: str = "127.0.0.1"
    port: int = 8765


@dataclass
class TranscriberConfig:
    """Faster-whisper transcriber configuration."""
    # Model settings
    model: str = "distil-large-v3"  # Best balance of speed/accuracy

    # Compute settings
    compute_type: Literal["float16", "int8_float16", "int8"] = "int8_float16"
    device: str = "cuda"

    # Transcription settings
    beam_size: int = 1  # Greedy decoding for lowest latency
    language: str = "en"


def cuda_available() -> bool:
    """Check if CUDA is available for GPU inference."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def get_system_memory_gb() -> float:
    """Get total system memory in GB."""
    try:
        import psutil
        return psutil.virtual_memory().total / (1024 ** 3)
    except ImportError:
        # Fallback: read from /proc/meminfo on Linux
        try:
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        kb = int(line.split()[1])
                        return kb / (1024 ** 2)
        except Exception:
            pass
        return 8.0  # Assume 8GB if we can't detect


def get_optimal_config() -> TranscriberConfig:
    """Auto-detect hardware and return optimal transcriber configuration.

    Returns configuration optimized for the detected hardware:
    - GPU (CUDA): distil-large-v3 with int8_float16 for best quality
    - CPU with 8GB+ RAM: small model with int8 for good balance
    - CPU with <8GB RAM: tiny model with int8 for speed
    """
    has_cuda = cuda_available()
    memory_gb = get_system_memory_gb()

    if has_cuda:
        # GPU mode: use best quality model
        return TranscriberConfig(
            model="distil-large-v3",
            device="cuda",
            compute_type="int8_float16",
            beam_size=1,
        )
    elif memory_gb >= 8:
        # CPU with enough RAM: balanced model
        return TranscriberConfig(
            model="small",
            device="cpu",
            compute_type="int8",
            beam_size=1,
        )
    else:
        # Low memory: fast/small model
        return TranscriberConfig(
            model="tiny",
            device="cpu",
            compute_type="int8",
            beam_size=1,
        )


def get_hardware_info() -> dict:
    """Get information about available hardware for display."""
    has_cuda = cuda_available()
    memory_gb = get_system_memory_gb()

    gpu_name = None
    if has_cuda:
        try:
            import torch
            gpu_name = torch.cuda.get_device_name(0)
        except Exception:
            gpu_name = "Unknown GPU"

    return {
        "cuda_available": has_cuda,
        "gpu_name": gpu_name,
        "system_memory_gb": round(memory_gb, 1),
        "cpu_count": os.cpu_count() or 1,
    }


# Default configurations
DEFAULT_SERVER_CONFIG = ServerConfig()
DEFAULT_TRANSCRIBER_CONFIG = TranscriberConfig()
