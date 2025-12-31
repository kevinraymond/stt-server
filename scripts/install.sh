#!/bin/bash
# Obsidian STT Server Installer for Linux/macOS
# Usage: curl -fsSL https://raw.githubusercontent.com/YOUR_USERNAME/obsidian-stt-server/main/scripts/install.sh | bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Installation directory
INSTALL_DIR="${HOME}/.obsidian-stt-server"
VENV_DIR="${INSTALL_DIR}/venv"

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║           Obsidian STT Server Installer                      ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Check for Python 3.10+
check_python() {
    echo -e "${YELLOW}Checking Python version...${NC}"

    # Try python3 first, then python
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo -e "${RED}Error: Python not found. Please install Python 3.10 or later.${NC}"
        echo ""
        echo "Install Python:"
        echo "  macOS: brew install python@3.11"
        echo "  Ubuntu/Debian: sudo apt install python3.11 python3.11-venv"
        echo "  Fedora: sudo dnf install python3.11"
        exit 1
    fi

    # Check version
    PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

    if [ "$MAJOR" -lt 3 ] || ([ "$MAJOR" -eq 3 ] && [ "$MINOR" -lt 10 ]); then
        echo -e "${RED}Error: Python 3.10+ required, found $PYTHON_VERSION${NC}"
        echo "Please install Python 3.10 or later."
        exit 1
    fi

    echo -e "${GREEN}Found Python $PYTHON_VERSION${NC}"
}

# Check for ffmpeg
check_ffmpeg() {
    echo -e "${YELLOW}Checking for ffmpeg...${NC}"

    if ! command -v ffmpeg &> /dev/null; then
        echo -e "${RED}Warning: ffmpeg not found. Audio processing may not work.${NC}"
        echo ""
        echo "Install ffmpeg:"
        echo "  macOS: brew install ffmpeg"
        echo "  Ubuntu/Debian: sudo apt install ffmpeg"
        echo "  Fedora: sudo dnf install ffmpeg"
        echo ""
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo -e "${GREEN}Found ffmpeg${NC}"
    fi
}

# Create installation directory
create_install_dir() {
    echo -e "${YELLOW}Creating installation directory...${NC}"
    mkdir -p "$INSTALL_DIR"
    echo -e "${GREEN}Created $INSTALL_DIR${NC}"
}

# Create virtual environment
create_venv() {
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    $PYTHON_CMD -m venv "$VENV_DIR"
    echo -e "${GREEN}Created virtual environment${NC}"
}

# Install package
install_package() {
    echo -e "${YELLOW}Installing obsidian-stt-server...${NC}"
    echo "(This may take a few minutes)"

    # Activate venv
    source "$VENV_DIR/bin/activate"

    # Upgrade pip
    pip install --upgrade pip --quiet

    # Install the package
    # For now, install dependencies directly. When published to PyPI, use:
    # pip install obsidian-stt-server
    pip install websockets numpy faster-whisper torch --quiet

    echo -e "${GREEN}Installed dependencies${NC}"
}

# Download the model
download_model() {
    echo -e "${YELLOW}Downloading Whisper model (this may take a few minutes)...${NC}"

    source "$VENV_DIR/bin/activate"

    # Check for CUDA
    HAS_CUDA=$($PYTHON_CMD -c "import torch; print(torch.cuda.is_available())" 2>/dev/null || echo "False")

    if [ "$HAS_CUDA" = "True" ]; then
        echo "GPU detected - downloading distil-large-v3 model..."
        MODEL="distil-large-v3"
    else
        echo "No GPU detected - downloading small model (optimized for CPU)..."
        MODEL="small"
    fi

    # Download model
    $PYTHON_CMD -c "from faster_whisper import WhisperModel; WhisperModel('$MODEL')"

    echo -e "${GREEN}Model downloaded successfully${NC}"
}

# Create startup script
create_startup_script() {
    echo -e "${YELLOW}Creating startup script...${NC}"

    cat > "$INSTALL_DIR/start-server.sh" << 'EOF'
#!/bin/bash
# Start the Obsidian STT Server

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/venv/bin/activate"

# Run with auto-detection
python -c "
from src.cli import main
import sys
sys.argv = ['obsidian-stt-server', '--auto']
main()
" 2>/dev/null || python -m src.cli --auto

EOF

    chmod +x "$INSTALL_DIR/start-server.sh"

    # Also create a simpler runner
    cat > "$INSTALL_DIR/run.sh" << EOF
#!/bin/bash
cd "$INSTALL_DIR"
source venv/bin/activate
python -c "
import sys
sys.path.insert(0, '.')
from faster_whisper import WhisperModel
import asyncio
import websockets
import json
import base64
import subprocess
import numpy as np

# Simple inline server for installed version
print('Starting Obsidian STT Server...')
print('WebSocket URL: ws://127.0.0.1:8765')
print('Press Ctrl+C to stop')

# Use the installed CLI
" && python -m src.cli --auto
EOF
    chmod +x "$INSTALL_DIR/run.sh"

    echo -e "${GREEN}Created startup script${NC}"
}

# Create systemd service (Linux only)
create_systemd_service() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo -e "${YELLOW}Creating systemd service...${NC}"

        SERVICE_FILE="$HOME/.config/systemd/user/obsidian-stt.service"
        mkdir -p "$(dirname "$SERVICE_FILE")"

        cat > "$SERVICE_FILE" << EOF
[Unit]
Description=Obsidian STT Server
After=network.target

[Service]
Type=simple
ExecStart=$INSTALL_DIR/start-server.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

        echo -e "${GREEN}Created systemd service${NC}"
        echo ""
        echo "To enable auto-start on login:"
        echo "  systemctl --user enable obsidian-stt"
        echo "  systemctl --user start obsidian-stt"
    fi
}

# Print success message
print_success() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║           Installation Complete!                             ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "To start the server:"
    echo -e "  ${BLUE}$INSTALL_DIR/start-server.sh${NC}"
    echo ""
    echo "Or add an alias to your shell config:"
    echo -e "  ${BLUE}echo 'alias stt-server=\"$INSTALL_DIR/start-server.sh\"' >> ~/.bashrc${NC}"
    echo ""
    echo "WebSocket URL for Obsidian plugin:"
    echo -e "  ${BLUE}ws://127.0.0.1:8765${NC}"
    echo ""
}

# Main installation
main() {
    check_python
    check_ffmpeg
    create_install_dir
    create_venv
    install_package
    download_model
    create_startup_script
    create_systemd_service
    print_success
}

main "$@"
