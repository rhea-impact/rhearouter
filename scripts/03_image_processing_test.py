#!/usr/bin/env python3
"""
RheaRouter Benchmark Script 03: Image Processing Test

Tests image loading, preprocessing, and GPU transfer speeds.
This simulates the image handling portion of multimodal inference.
"""

import sys
import time
import io
import base64

def test_image_processing():
    print("=" * 60)
    print("RheaRouter Image Processing Test")
    print("=" * 60)

    # Check dependencies
    try:
        import torch
        print(f"[OK] PyTorch: {torch.__version__}")
    except ImportError:
        print("[FAIL] PyTorch not installed")
        return False

    try:
        from PIL import Image
        print(f"[OK] Pillow available")
    except ImportError:
        print("[FAIL] Pillow not installed - run: pip install Pillow")
        return False

    try:
        import torchvision.transforms as transforms
        print(f"[OK] torchvision available")
    except ImportError:
        print("[WARN] torchvision not installed - limited testing")
        transforms = None

    if not torch.cuda.is_available():
        print("[FAIL] CUDA not available")
        return False

    device = torch.device('cuda')
    results = {}

    # Test 1: Create synthetic test images of various sizes
    print("\n--- Test 1: Image Loading & Preprocessing ---")
    test_sizes = [(224, 224), (336, 336), (512, 512), (768, 768)]

    for width, height in test_sizes:
        # Create synthetic image
        img = Image.new('RGB', (width, height), color='blue')

        # Simulate loading from base64 (common in API requests)
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_bytes = buffer.getvalue()
        b64_data = base64.b64encode(img_bytes).decode('utf-8')

        # Benchmark: decode base64 + load image
        start = time.perf_counter()
        iterations = 100
        for _ in range(iterations):
            decoded = base64.b64decode(b64_data)
            loaded_img = Image.open(io.BytesIO(decoded))
            loaded_img.load()  # Force load
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / iterations) * 1000
        results[f'load_{width}x{height}'] = avg_ms
        print(f"  {width}x{height}: Load from base64: {avg_ms:.2f} ms")

    # Test 2: Image to tensor conversion + GPU transfer
    print("\n--- Test 2: Image to GPU Tensor ---")

    if transforms:
        preprocess = transforms.Compose([
            transforms.Resize((336, 336)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])

        # Create test image
        img = Image.new('RGB', (1024, 1024), color='red')

        # Warmup
        for _ in range(5):
            tensor = preprocess(img).unsqueeze(0).to(device)
        torch.cuda.synchronize()

        # Benchmark
        start = time.perf_counter()
        iterations = 100
        for _ in range(iterations):
            tensor = preprocess(img).unsqueeze(0).to(device)
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / iterations) * 1000
        results['preprocess_to_gpu'] = avg_ms
        print(f"  1024x1024 -> 336x336 + normalize + GPU: {avg_ms:.2f} ms")
    else:
        print("  [SKIP] torchvision not available")

    # Test 3: Batch image processing
    print("\n--- Test 3: Batch Image Processing ---")

    batch_sizes = [1, 4, 8]
    img_size = 336

    for bs in batch_sizes:
        # Create batch of images on CPU
        batch = torch.randn(bs, 3, img_size, img_size)

        # Warmup
        for _ in range(5):
            gpu_batch = batch.to(device, non_blocking=True)
        torch.cuda.synchronize()

        # Benchmark transfer
        start = time.perf_counter()
        iterations = 100
        for _ in range(iterations):
            gpu_batch = batch.to(device, non_blocking=True)
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - start

        avg_ms = (elapsed / iterations) * 1000
        throughput = bs * iterations / elapsed
        results[f'batch_{bs}_transfer'] = avg_ms
        print(f"  Batch size {bs}: {avg_ms:.2f} ms, {throughput:.1f} images/sec to GPU")

    # Test 4: Simulate vision encoder forward pass
    print("\n--- Test 4: Vision Encoder Simulation ---")

    # Simulate CLIP-like vision encoder dimensions
    batch_size = 1
    patches = 576  # 24x24 patches for 336x336 image with patch_size=14
    hidden_dim = 1024

    # Create fake patch embeddings
    patch_embeds = torch.randn(batch_size, patches, hidden_dim, device=device, dtype=torch.float16)

    # Simulate a few transformer layers
    num_layers = 12
    weights = [torch.randn(hidden_dim, hidden_dim, device=device, dtype=torch.float16) for _ in range(num_layers)]

    # Warmup
    for _ in range(3):
        x = patch_embeds
        for w in weights:
            x = torch.matmul(x, w)
    torch.cuda.synchronize()

    # Benchmark
    start = time.perf_counter()
    iterations = 50
    for _ in range(iterations):
        x = patch_embeds
        for w in weights:
            x = torch.matmul(x, w)
    torch.cuda.synchronize()
    elapsed = time.perf_counter() - start

    avg_ms = (elapsed / iterations) * 1000
    results['vision_encoder_sim'] = avg_ms
    print(f"  12-layer vision encoder simulation: {avg_ms:.2f} ms")

    # Test 5: Memory usage for vision models
    print("\n--- Test 5: VRAM Estimation for Vision Models ---")

    # Estimate VRAM for common vision model sizes
    estimates = [
        ("CLIP ViT-L/14", 0.4),
        ("LLaVA 7B (vision + LLM)", 5.0),
        ("MiniCPM-V 2.6", 4.5),
        ("Qwen-VL 7B", 5.5),
    ]

    total_vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
    available = total_vram - 0.5  # Reserve 0.5GB for system

    print(f"  Total VRAM: {total_vram:.1f} GB")
    print(f"  Available for models: {available:.1f} GB")
    print()

    for model_name, vram_gb in estimates:
        status = "[OK]" if vram_gb < available else "[NO]"
        print(f"  {status} {model_name}: ~{vram_gb} GB")

    # Summary
    print("\n" + "=" * 60)
    print("IMAGE PROCESSING SUMMARY")
    print("=" * 60)
    print(f"  Base64 decode + load (512x512): {results.get('load_512x512', 'N/A'):.2f} ms")
    print(f"  Preprocess + GPU transfer: {results.get('preprocess_to_gpu', 'N/A'):.2f} ms")
    print(f"  Vision encoder simulation: {results.get('vision_encoder_sim', 'N/A'):.2f} ms")

    # Verdict
    print("\n--- VERDICT ---")
    total_image_pipeline = (
        results.get('load_512x512', 10) +
        results.get('preprocess_to_gpu', 10) +
        results.get('vision_encoder_sim', 50)
    )

    if total_image_pipeline < 100:
        print(f"[OK] Image preprocessing pipeline: ~{total_image_pipeline:.0f} ms")
        print("[OK] Fast enough for interactive multimodal inference")
    else:
        print(f"[WARN] Image preprocessing pipeline: ~{total_image_pipeline:.0f} ms")
        print("[WARN] May feel sluggish for real-time use")

    print("\n[SUCCESS] Image processing test complete!")
    return True

if __name__ == "__main__":
    success = test_image_processing()
    sys.exit(0 if success else 1)
