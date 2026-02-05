#!/usr/bin/env python3
"""
RheaRouter Benchmark Script 02: GPU Performance Benchmark

Tests GPU compute performance with matrix operations typical of ML inference.
"""

import sys
import time

def benchmark_gpu():
    print("=" * 60)
    print("RheaRouter GPU Performance Benchmark")
    print("=" * 60)

    try:
        import torch
    except ImportError:
        print("[FAIL] PyTorch not installed!")
        return False

    if not torch.cuda.is_available():
        print("[FAIL] CUDA not available!")
        return False

    device = torch.device('cuda')
    print(f"\n[INFO] Running on: {torch.cuda.get_device_name(0)}")

    results = {}

    # Benchmark 1: Matrix multiplication (core of transformer inference)
    print("\n--- Benchmark 1: Matrix Multiplication ---")
    sizes = [(1024, 1024), (2048, 2048), (4096, 4096)]

    for size in sizes:
        n = size[0]
        a = torch.randn(n, n, device=device, dtype=torch.float16)
        b = torch.randn(n, n, device=device, dtype=torch.float16)

        # Warmup
        for _ in range(3):
            torch.matmul(a, b)
        torch.cuda.synchronize()

        # Benchmark
        start = time.perf_counter()
        iterations = 100
        for _ in range(iterations):
            torch.matmul(a, b)
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / iterations) * 1000
        flops = 2 * n * n * n * iterations / elapsed / 1e12  # TFLOPS
        results[f'matmul_{n}x{n}'] = avg_ms
        print(f"  {n}x{n} matmul: {avg_ms:.2f} ms/op, {flops:.2f} TFLOPS (FP16)")

    # Benchmark 2: Attention-like operation
    print("\n--- Benchmark 2: Attention Simulation ---")
    batch_size = 1
    seq_len = 2048
    hidden_dim = 4096
    num_heads = 32
    head_dim = hidden_dim // num_heads

    q = torch.randn(batch_size, num_heads, seq_len, head_dim, device=device, dtype=torch.float16)
    k = torch.randn(batch_size, num_heads, seq_len, head_dim, device=device, dtype=torch.float16)
    v = torch.randn(batch_size, num_heads, seq_len, head_dim, device=device, dtype=torch.float16)

    # Warmup
    for _ in range(3):
        attn = torch.matmul(q, k.transpose(-2, -1)) / (head_dim ** 0.5)
        attn = torch.softmax(attn, dim=-1)
        out = torch.matmul(attn, v)
    torch.cuda.synchronize()

    # Benchmark
    start = time.perf_counter()
    iterations = 50
    for _ in range(iterations):
        attn = torch.matmul(q, k.transpose(-2, -1)) / (head_dim ** 0.5)
        attn = torch.softmax(attn, dim=-1)
        out = torch.matmul(attn, v)
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - start

    avg_ms = (elapsed / iterations) * 1000
    results['attention_2048_seq'] = avg_ms
    print(f"  Seq len 2048, 32 heads: {avg_ms:.2f} ms/forward")

    # Benchmark 3: Memory bandwidth test
    print("\n--- Benchmark 3: Memory Bandwidth ---")
    size_gb = 1.0
    elements = int(size_gb * 1024**3 / 4)  # float32 = 4 bytes
    tensor = torch.randn(elements, device=device, dtype=torch.float32)

    # Warmup
    for _ in range(3):
        tensor.clone()
    torch.cuda.synchronize()

    # Benchmark
    start = time.perf_counter()
    iterations = 20
    for _ in range(iterations):
        _ = tensor.clone()
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - start

    bandwidth_gbps = (size_gb * 2 * iterations) / elapsed  # read + write
    results['mem_bandwidth_gbps'] = bandwidth_gbps
    print(f"  Memory bandwidth: {bandwidth_gbps:.1f} GB/s")

    # Benchmark 4: Batch inference simulation
    print("\n--- Benchmark 4: Batch Processing ---")
    batch_sizes = [1, 4, 8]
    hidden = 4096

    for bs in batch_sizes:
        x = torch.randn(bs, hidden, device=device, dtype=torch.float16)
        w = torch.randn(hidden, hidden, device=device, dtype=torch.float16)

        # Warmup
        for _ in range(5):
            torch.matmul(x, w)
        torch.cuda.synchronize()

        # Benchmark
        start = time.perf_counter()
        iterations = 200
        for _ in range(iterations):
            torch.matmul(x, w)
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / iterations) * 1000
        throughput = bs * iterations / elapsed
        results[f'batch_{bs}_throughput'] = throughput
        print(f"  Batch size {bs}: {avg_ms:.3f} ms/batch, {throughput:.1f} samples/sec")

    # Memory usage summary
    print("\n--- VRAM Usage After Benchmarks ---")
    allocated = torch.cuda.memory_allocated() / 1024**3
    reserved = torch.cuda.memory_reserved() / 1024**3
    print(f"  Allocated: {allocated:.2f} GB")
    print(f"  Reserved: {reserved:.2f} GB")

    # Summary
    print("\n" + "=" * 60)
    print("BENCHMARK SUMMARY")
    print("=" * 60)
    print(f"  4096x4096 MatMul (FP16): {results.get('matmul_4096x4096', 'N/A'):.2f} ms")
    print(f"  Attention (2048 seq): {results.get('attention_2048_seq', 'N/A'):.2f} ms")
    print(f"  Memory Bandwidth: {results.get('mem_bandwidth_gbps', 'N/A'):.1f} GB/s")
    print(f"  Batch-1 Throughput: {results.get('batch_1_throughput', 'N/A'):.1f} samples/sec")

    # Verdict
    print("\n--- VERDICT ---")
    if results.get('matmul_4096x4096', 999) < 50:
        print("[OK] GPU is fast enough for 7B model inference")
    else:
        print("[WARN] GPU may be slow for larger models")

    if results.get('mem_bandwidth_gbps', 0) > 100:
        print("[OK] Memory bandwidth is adequate")
    else:
        print("[WARN] Memory bandwidth may bottleneck inference")

    print("\n[SUCCESS] Benchmark complete!")
    return True

if __name__ == "__main__":
    success = benchmark_gpu()
    sys.exit(0 if success else 1)
