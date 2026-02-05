#!/usr/bin/env python3
"""
RheaRouter Benchmark Script 01: CUDA Availability Check

Verifies that CUDA is properly configured and accessible via PyTorch.
"""

import sys

def check_cuda():
    print("=" * 60)
    print("RheaRouter CUDA Check")
    print("=" * 60)

    try:
        import torch
        print(f"\n[OK] PyTorch version: {torch.__version__}")
    except ImportError:
        print("\n[FAIL] PyTorch not installed!")
        print("  Install with: pip install torch")
        return False

    print(f"[INFO] CUDA available: {torch.cuda.is_available()}")

    if not torch.cuda.is_available():
        print("\n[FAIL] CUDA is not available!")
        print("  Check that NVIDIA drivers are installed")
        print("  Check that PyTorch was installed with CUDA support")
        return False

    print(f"[OK] CUDA version: {torch.version.cuda}")
    print(f"[OK] cuDNN version: {torch.backends.cudnn.version()}")
    print(f"[OK] Device count: {torch.cuda.device_count()}")

    for i in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(i)
        print(f"\n--- GPU {i}: {props.name} ---")
        print(f"  Total VRAM: {props.total_memory / 1024**3:.2f} GB")
        print(f"  Compute capability: {props.major}.{props.minor}")
        print(f"  Multi-processors: {props.multi_processor_count}")

    # Test basic tensor operation on GPU
    print("\n--- Testing GPU Tensor Operations ---")
    try:
        x = torch.randn(1000, 1000, device='cuda')
        y = torch.randn(1000, 1000, device='cuda')
        z = torch.matmul(x, y)
        torch.cuda.synchronize()
        print("[OK] Basic tensor operations work")
    except Exception as e:
        print(f"[FAIL] Tensor operation failed: {e}")
        return False

    # Check available memory
    print("\n--- VRAM Status ---")
    allocated = torch.cuda.memory_allocated() / 1024**3
    reserved = torch.cuda.memory_reserved() / 1024**3
    total = torch.cuda.get_device_properties(0).total_memory / 1024**3
    free = total - reserved

    print(f"  Total: {total:.2f} GB")
    print(f"  Allocated: {allocated:.2f} GB")
    print(f"  Reserved: {reserved:.2f} GB")
    print(f"  Free (approx): {free:.2f} GB")

    print("\n" + "=" * 60)
    print("[SUCCESS] CUDA check passed!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = check_cuda()
    sys.exit(0 if success else 1)
