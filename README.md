# Obsidian STT Server

Local speech-to-text server for Obsidian using OpenAI's Whisper. Runs on your computer - no cloud required.

## Features

- **100% Local** - Your audio never leaves your computer
- **Multi-language** - Supports 99 languages
- **Auto-detection** - Automatically optimizes for your hardware (GPU/CPU)
- **Fast** - Optimized with faster-whisper and CTranslate2

## Quick Start

Choose your preferred installation method:

### Option 1: Docker (Recommended)

```bash
# CPU (works on any machine, including Mac)
docker run -d -p 8765:8765 ghcr.io/kevinraymond/stt-server:latest

# GPU (requires NVIDIA GPU + driver 545+)
docker run -d --gpus all -p 8765:8765 ghcr.io/kevinraymond/stt-server:gpu

# GPU Legacy (for older drivers 525-544)
docker run -d --gpus all -p 8765:8765 ghcr.io/kevinraymond/stt-server:gpu-legacy
```

Check your driver version with `nvidia-smi`.

### Option 2: One-Line Install

**Linux/macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/kevinraymond/stt-server/main/scripts/install.sh | bash
```

**Windows (PowerShell as Admin):**
```powershell
iwr -useb https://raw.githubusercontent.com/kevinraymond/stt-server/main/scripts/install.ps1 | iex
```

### Option 3: pip (for Python developers)

```bash
pip install obsidian-stt-server
obsidian-stt-server --auto
```

## Connecting to Obsidian

1. Start the server using one of the methods above
2. Note the WebSocket URL (usually `ws://127.0.0.1:8765`)
3. In Obsidian, open the STT plugin settings
4. Paste the WebSocket URL and test the connection

## Configuration

The server auto-detects your hardware and chooses optimal settings. You can override:

```bash
# Force CPU mode with small model
obsidian-stt-server --device cpu --model small

# Use a specific language
obsidian-stt-server --language es

# Bind to all interfaces (for network access)
obsidian-stt-server --host 0.0.0.0
```

### Available Models

| Model | Size | Speed | Accuracy | Best For |
|-------|------|-------|----------|----------|
| `tiny` | 75MB | Fastest | Basic | Quick notes, weak CPU |
| `base` | 145MB | Fast | Good | Casual use |
| `small` | 488MB | Moderate | Better | **CPU recommended** |
| `medium` | 1.5GB | Slower | Great | Good CPU/GPU |
| `large-v3` | 3GB | Slowest | Best | Accuracy-first |
| `distil-large-v3` | 756MB | Fast | Great | **GPU recommended** |

### Supported Languages

Supports all 99 languages from Whisper, including:

- English (en), Spanish (es), French (fr), German (de)
- Chinese (zh), Japanese (ja), Korean (ko)
- Arabic (ar), Russian (ru), Portuguese (pt)
- And 89 more...

Use language codes with `--language`:
```bash
obsidian-stt-server --language ja  # Japanese
```

## Troubleshooting

### "CUDA not available" warning
This is normal on CPU-only machines. The server will automatically use CPU mode.

### Slow transcription
- Try a smaller model: `--model small` or `--model tiny`
- Ensure no other heavy processes are running
- If on laptop, connect to power

### Connection refused
- Check the server is running
- Verify the port (default: 8765)
- Check firewall settings

### Out of memory
- Use a smaller model: `--model tiny`
- Close other applications
- Use `--compute-type int8` for lower memory usage

## Requirements

- **Python 3.10+** (for pip install)
- **Docker** (for Docker install)
- **ffmpeg** (for audio processing)
- ~500MB-3GB disk space (depends on model)

### GPU Support (Optional)
- NVIDIA GPU with CUDA support
- NVIDIA drivers: 545+ for `:gpu` image, 525+ for `:gpu-legacy` image
- For Docker: [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)

| Docker Image | CUDA | cuDNN | Driver Required |
|--------------|------|-------|-----------------|
| `:gpu` | 12.3 | 9 | 545+ |
| `:gpu-legacy` | 12.1 | 8 | 525+ |

## Development

```bash
# Clone the repo
git clone https://github.com/kevinraymond/stt-server
cd stt-server

# Install with uv
uv sync

# Run locally
uv run python -m src.cli --auto
```

## License

MIT
