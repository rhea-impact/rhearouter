#!/bin/bash
#
# RheaRouter - Dependency Setup Script
#
# Run this first to install required Python packages for benchmarking.
#

set -e

echo "============================================================"
echo "RheaRouter Dependency Setup"
echo "============================================================"
echo ""

# Check if running as root (needed for apt)
if [ "$EUID" -ne 0 ]; then
    echo "This script needs sudo to install system packages."
    echo "You may be prompted for your password."
    echo ""
fi

# Install pip if not available
echo "[1/4] Checking pip..."
if ! python3 -m pip --version &>/dev/null; then
    echo "  Installing pip..."
    sudo apt update
    sudo apt install -y python3-pip python3-venv
fi
echo "  [OK] pip available"

# Create virtual environment (recommended)
VENV_DIR="$HOME/.venv/rhearouter"
echo ""
echo "[2/4] Setting up virtual environment at $VENV_DIR..."

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo "  [OK] Virtual environment created"
else
    echo "  [OK] Virtual environment already exists"
fi

# Activate venv
source "$VENV_DIR/bin/activate"
echo "  [OK] Virtual environment activated"

# Upgrade pip
pip install --upgrade pip

# Install PyTorch with CUDA support
echo ""
echo "[3/4] Installing PyTorch with CUDA support..."
echo "  This may take a few minutes..."
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121

# Install other dependencies
echo ""
echo "[4/4] Installing additional dependencies..."
pip install Pillow requests transformers accelerate

echo ""
echo "============================================================"
echo "SETUP COMPLETE"
echo "============================================================"
echo ""
echo "To use the virtual environment, run:"
echo "  source $VENV_DIR/bin/activate"
echo ""
echo "Then run the benchmarks:"
echo "  cd $(dirname "$0")"
echo "  python3 01_check_cuda.py"
echo ""
echo "Or run all benchmarks:"
echo "  ./run_all_benchmarks.sh"
