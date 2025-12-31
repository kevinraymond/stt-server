# Obsidian STT Server Installer for Windows
# Usage: iwr -useb https://raw.githubusercontent.com/YOUR_USERNAME/obsidian-stt-server/main/scripts/install.ps1 | iex
# Or: powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"

# Installation directory
$INSTALL_DIR = "$env:USERPROFILE\.obsidian-stt-server"
$VENV_DIR = "$INSTALL_DIR\venv"

function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Show-Banner {
    Write-ColorOutput @"

╔══════════════════════════════════════════════════════════════╗
║           Obsidian STT Server Installer                      ║
╚══════════════════════════════════════════════════════════════╝

"@ -Color Cyan
}

function Test-PythonVersion {
    Write-ColorOutput "Checking Python version..." -Color Yellow

    # Try to find Python
    $pythonCmd = $null
    foreach ($cmd in @("python", "python3", "py")) {
        try {
            $version = & $cmd --version 2>&1
            if ($version -match "Python (\d+)\.(\d+)") {
                $major = [int]$Matches[1]
                $minor = [int]$Matches[2]
                if ($major -ge 3 -and $minor -ge 10) {
                    $pythonCmd = $cmd
                    Write-ColorOutput "Found Python $major.$minor" -Color Green
                    break
                }
            }
        } catch {
            continue
        }
    }

    if (-not $pythonCmd) {
        Write-ColorOutput "Error: Python 3.10+ not found." -Color Red
        Write-Host @"

Please install Python 3.10 or later:
  1. Download from https://www.python.org/downloads/
  2. Make sure to check 'Add Python to PATH' during installation
  3. Restart this terminal and run the installer again

Or install via winget:
  winget install Python.Python.3.11

"@
        exit 1
    }

    return $pythonCmd
}

function Test-FFmpeg {
    Write-ColorOutput "Checking for ffmpeg..." -Color Yellow

    try {
        $null = & ffmpeg -version 2>&1
        Write-ColorOutput "Found ffmpeg" -Color Green
        return $true
    } catch {
        Write-ColorOutput "Warning: ffmpeg not found. Audio processing may not work." -Color Yellow
        Write-Host @"

Install ffmpeg:
  1. Download from https://ffmpeg.org/download.html
  2. Extract and add to PATH

Or install via winget:
  winget install FFmpeg.FFmpeg

"@
        $response = Read-Host "Continue anyway? (y/n)"
        if ($response -ne "y" -and $response -ne "Y") {
            exit 1
        }
        return $false
    }
}

function New-InstallDir {
    Write-ColorOutput "Creating installation directory..." -Color Yellow

    if (Test-Path $INSTALL_DIR) {
        Write-ColorOutput "Removing existing installation..." -Color Yellow
        Remove-Item -Recurse -Force $INSTALL_DIR
    }

    New-Item -ItemType Directory -Path $INSTALL_DIR -Force | Out-Null
    Write-ColorOutput "Created $INSTALL_DIR" -Color Green
}

function New-VirtualEnv {
    param([string]$PythonCmd)

    Write-ColorOutput "Creating virtual environment..." -Color Yellow
    & $PythonCmd -m venv $VENV_DIR
    Write-ColorOutput "Created virtual environment" -Color Green
}

function Install-Package {
    Write-ColorOutput "Installing obsidian-stt-server..." -Color Yellow
    Write-Host "(This may take a few minutes)"

    # Activate venv
    $activateScript = "$VENV_DIR\Scripts\Activate.ps1"
    . $activateScript

    # Upgrade pip
    & python -m pip install --upgrade pip --quiet

    # Install dependencies
    # When published to PyPI: pip install obsidian-stt-server
    & pip install websockets numpy faster-whisper torch --quiet

    Write-ColorOutput "Installed dependencies" -Color Green
}

function Get-WhisperModel {
    Write-ColorOutput "Downloading Whisper model (this may take a few minutes)..." -Color Yellow

    # Activate venv
    $activateScript = "$VENV_DIR\Scripts\Activate.ps1"
    . $activateScript

    # Check for CUDA
    $hasCuda = python -c "import torch; print(torch.cuda.is_available())" 2>$null

    if ($hasCuda -eq "True") {
        Write-Host "GPU detected - downloading distil-large-v3 model..."
        $model = "distil-large-v3"
    } else {
        Write-Host "No GPU detected - downloading small model (optimized for CPU)..."
        $model = "small"
    }

    # Download model
    python -c "from faster_whisper import WhisperModel; WhisperModel('$model')"

    Write-ColorOutput "Model downloaded successfully" -Color Green
}

function New-StartupScript {
    Write-ColorOutput "Creating startup script..." -Color Yellow

    # Create batch file for easy startup
    $batchContent = @"
@echo off
echo Starting Obsidian STT Server...
call "$VENV_DIR\Scripts\activate.bat"
python -m src.cli --auto
pause
"@
    Set-Content -Path "$INSTALL_DIR\start-server.bat" -Value $batchContent

    # Create PowerShell script
    $psContent = @"
# Start Obsidian STT Server
Write-Host "Starting Obsidian STT Server..."
& "$VENV_DIR\Scripts\Activate.ps1"
python -m src.cli --auto
"@
    Set-Content -Path "$INSTALL_DIR\start-server.ps1" -Value $psContent

    Write-ColorOutput "Created startup scripts" -Color Green
}

function New-StartupShortcut {
    Write-ColorOutput "Creating Start Menu shortcut..." -Color Yellow

    $WshShell = New-Object -ComObject WScript.Shell
    $startMenuPath = [System.Environment]::GetFolderPath('StartMenu')
    $shortcutPath = "$startMenuPath\Programs\Obsidian STT Server.lnk"

    $Shortcut = $WshShell.CreateShortcut($shortcutPath)
    $Shortcut.TargetPath = "$INSTALL_DIR\start-server.bat"
    $Shortcut.WorkingDirectory = $INSTALL_DIR
    $Shortcut.Description = "Start Obsidian STT Server"
    $Shortcut.Save()

    Write-ColorOutput "Created Start Menu shortcut" -Color Green
}

function Show-Success {
    Write-Host ""
    Write-ColorOutput @"
╔══════════════════════════════════════════════════════════════╗
║           Installation Complete!                             ║
╚══════════════════════════════════════════════════════════════╝
"@ -Color Green

    Write-Host @"

To start the server:
  Double-click: $INSTALL_DIR\start-server.bat
  Or from PowerShell: $INSTALL_DIR\start-server.ps1

You can also find "Obsidian STT Server" in your Start Menu.

WebSocket URL for Obsidian plugin:
  ws://127.0.0.1:8765

"@
}

# Main installation
function Main {
    Show-Banner
    $pythonCmd = Test-PythonVersion
    Test-FFmpeg
    New-InstallDir
    New-VirtualEnv -PythonCmd $pythonCmd
    Install-Package
    Get-WhisperModel
    New-StartupScript
    New-StartupShortcut
    Show-Success
}

Main
