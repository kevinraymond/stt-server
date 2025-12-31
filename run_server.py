#!/usr/bin/env python3
"""CLI entry point for the STT server."""

import argparse
import sys

from src.server import run_server
from src.config import get_optimal_config, get_hardware_info


def print_banner(host: str, port: int, model: str, device: str, compute_type: str, language: str, auto_mode: bool = False):
    """Print the startup banner with configuration info."""
    hw = get_hardware_info()

    mode_str = "AUTO-DETECTED" if auto_mode else "MANUAL"
    gpu_str = hw["gpu_name"] if hw["cuda_available"] else "Not available"

    print(f"""
┌──────────────────────────────────────────────────────────────┐
│                   STT Server for Obsidian                    │
├──────────────────────────────────────────────────────────────┤
│  Configuration: {mode_str:<20}                       │
├──────────────────────────────────────────────────────────────┤
│  Hardware Detected:                                          │
│    GPU: {gpu_str[:40]:<42}│
│    RAM: {hw['system_memory_gb']:<5} GB    CPUs: {hw['cpu_count']:<3}                            │
├──────────────────────────────────────────────────────────────┤
│  Settings:                                                   │
│    Model:    {model:<20}                          │
│    Device:   {device:<10}  Compute: {compute_type:<15}    │
│    Language: {language:<10}                                    │
├──────────────────────────────────────────────────────────────┤
│  WebSocket URL: ws://{host}:{port:<5}                            │
│  (Copy this URL into the Obsidian plugin settings)           │
└──────────────────────────────────────────────────────────────┘
""")


def main():
    parser = argparse.ArgumentParser(
        description="WebSocket server for speech-to-text transcription using Whisper",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  obsidian-stt-server --auto              # Auto-detect best settings
  obsidian-stt-server --model small       # Use small model (good for CPU)
  obsidian-stt-server --device cpu        # Force CPU mode
  obsidian-stt-server --language es       # Spanish transcription

Models (smallest to largest):
  tiny    - 75MB,  fastest, less accurate
  base    - 145MB, fast, basic accuracy
  small   - 488MB, balanced (recommended for CPU)
  medium  - 1.5GB, good accuracy
  large-v3        - 3GB, best accuracy
  distil-large-v3 - 756MB, best for GPU (default)
        """,
    )

    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto-detect optimal settings based on your hardware (recommended)",
    )

    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind the server to (default: 127.0.0.1)",
    )

    parser.add_argument(
        "--port",
        type=int,
        default=8765,
        help="Port to bind the server to (default: 8765)",
    )

    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Whisper model to use (see list below)",
    )

    parser.add_argument(
        "--language",
        type=str,
        default="en",
        help="Language code for transcription (e.g., en, es, fr, de, ja, zh)",
    )

    parser.add_argument(
        "--device",
        type=str,
        default=None,
        choices=["cuda", "cpu"],
        help="Device to run inference on",
    )

    parser.add_argument(
        "--compute-type",
        type=str,
        default=None,
        choices=["float16", "int8_float16", "int8"],
        help="Compute type for inference",
    )

    args = parser.parse_args()

    # Determine configuration
    if args.auto or (args.model is None and args.device is None):
        # Auto mode: detect optimal settings
        auto_config = get_optimal_config()
        model = args.model or auto_config.model
        device = args.device or auto_config.device
        compute_type = args.compute_type or auto_config.compute_type
        auto_mode = True
    else:
        # Manual mode: use provided settings with sensible defaults
        model = args.model or "distil-large-v3"
        device = args.device or "cuda"
        compute_type = args.compute_type or "int8_float16"
        auto_mode = False

    print_banner(
        host=args.host,
        port=args.port,
        model=model,
        device=device,
        compute_type=compute_type,
        language=args.language,
        auto_mode=auto_mode,
    )

    run_server(
        host=args.host,
        port=args.port,
        model=model,
        language=args.language,
        device=device,
        compute_type=compute_type,
    )


if __name__ == "__main__":
    main()
