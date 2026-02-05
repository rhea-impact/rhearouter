#!/bin/bash
#
# RheaRouter - Run All Benchmark Scripts
#
# This script runs all benchmark tests in sequence to verify
# that the server hardware is capable of running inference.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "RheaRouter Hardware Benchmark Suite"
echo "============================================================"
echo ""
echo "This will run 4 tests to verify your hardware:"
echo "  1. CUDA availability check"
echo "  2. GPU compute benchmark"
echo "  3. Image processing test"
echo "  4. Full inference test (requires Ollama)"
echo ""
echo "Press Enter to start or Ctrl+C to cancel..."
read

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[FAIL] Python3 not found!"
    exit 1
fi

# Check for required packages
echo ""
echo "Checking Python dependencies..."
python3 -c "import torch" 2>/dev/null || {
    echo "[WARN] PyTorch not installed"
    echo "Install with: pip install torch"
    echo ""
    echo "Would you like to install it now? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        pip install torch torchvision
    else
        echo "Skipping PyTorch installation. Some tests may fail."
    fi
}

python3 -c "from PIL import Image" 2>/dev/null || {
    echo "[WARN] Pillow not installed, installing..."
    pip install Pillow
}

# Run benchmarks
echo ""
echo "============================================================"
echo "Running Test 1: CUDA Check"
echo "============================================================"
python3 01_check_cuda.py || echo "[WARN] CUDA check had issues"

echo ""
echo "============================================================"
echo "Running Test 2: GPU Benchmark"
echo "============================================================"
python3 02_gpu_benchmark.py || echo "[WARN] GPU benchmark had issues"

echo ""
echo "============================================================"
echo "Running Test 3: Image Processing"
echo "============================================================"
python3 03_image_processing_test.py || echo "[WARN] Image processing test had issues"

echo ""
echo "============================================================"
echo "Running Test 4: Full Inference Test"
echo "============================================================"
python3 04_full_inference_test.py || echo "[WARN] Inference test had issues"

echo ""
echo "============================================================"
echo "ALL BENCHMARKS COMPLETE"
echo "============================================================"
echo ""
echo "Review the results above to determine if your hardware"
echo "is ready for RheaRouter inference server deployment."
echo ""
echo "Next steps:"
echo "  1. Install Ollama if not already: curl -fsSL https://ollama.com/install.sh | sh"
echo "  2. Pull recommended models: ollama pull llama3.2:3b"
echo "  3. For multimodal: ollama pull llava:7b"
echo "  4. Proceed to API server setup"
