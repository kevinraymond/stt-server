#!/bin/bash
# Start the STT server with CUDA/cuDNN support

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CUDNN_PATH="$SCRIPT_DIR/.venv/lib/python3.13/site-packages/nvidia/cudnn/lib"

export LD_LIBRARY_PATH="$CUDNN_PATH:$LD_LIBRARY_PATH"

cd "$SCRIPT_DIR"
exec uv run python -m src.server "$@"
