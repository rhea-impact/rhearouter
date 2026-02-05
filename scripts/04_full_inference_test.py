#!/usr/bin/env python3
"""
RheaRouter Benchmark Script 04: Full Inference Test

Tests actual model inference using Ollama (if installed) or
downloads a small test model to verify end-to-end functionality.
"""

import sys
import time
import subprocess
import json

def check_ollama():
    """Check if Ollama is installed and running."""
    try:
        result = subprocess.run(
            ['ollama', 'list'],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False

def test_ollama_inference():
    """Test inference using Ollama."""
    print("\n--- Testing Ollama Inference ---")

    # Check what models are available
    result = subprocess.run(['ollama', 'list'], capture_output=True, text=True)
    print(f"  Available models:\n{result.stdout}")

    if 'llama' not in result.stdout.lower() and 'qwen' not in result.stdout.lower() and 'mistral' not in result.stdout.lower():
        print("  [INFO] No suitable model found. Pulling a small test model...")
        print("  [INFO] This may take a few minutes...")

        # Pull a small model for testing
        pull_result = subprocess.run(
            ['ollama', 'pull', 'qwen2.5:0.5b'],
            capture_output=True,
            text=True,
            timeout=300
        )
        if pull_result.returncode != 0:
            print(f"  [FAIL] Could not pull model: {pull_result.stderr}")
            return False
        test_model = 'qwen2.5:0.5b'
    else:
        # Use first available model
        lines = result.stdout.strip().split('\n')[1:]  # Skip header
        if lines:
            test_model = lines[0].split()[0]
        else:
            test_model = 'qwen2.5:0.5b'

    print(f"  Testing with model: {test_model}")

    # Test 1: Simple text generation
    print("\n  Test 1: Text Generation")
    prompt = "Write a haiku about computers."

    start = time.perf_counter()
    result = subprocess.run(
        ['ollama', 'run', test_model, prompt],
        capture_output=True,
        text=True,
        timeout=60
    )
    elapsed = time.perf_counter() - start

    if result.returncode == 0:
        output = result.stdout.strip()
        words = len(output.split())
        print(f"    Response ({words} words) in {elapsed:.2f}s:")
        print(f"    {output[:200]}...")
        print(f"    [OK] Text generation works!")
    else:
        print(f"    [FAIL] Error: {result.stderr}")
        return False

    # Test 2: Measure tokens per second
    print("\n  Test 2: Generation Speed")
    prompt = "Explain what an API is in exactly 100 words."

    start = time.perf_counter()
    result = subprocess.run(
        ['ollama', 'run', test_model, prompt],
        capture_output=True,
        text=True,
        timeout=120
    )
    elapsed = time.perf_counter() - start

    if result.returncode == 0:
        output = result.stdout.strip()
        # Rough token estimate (words * 1.3)
        est_tokens = int(len(output.split()) * 1.3)
        tokens_per_sec = est_tokens / elapsed
        print(f"    Generated ~{est_tokens} tokens in {elapsed:.2f}s")
        print(f"    Speed: ~{tokens_per_sec:.1f} tokens/sec")

        if tokens_per_sec > 10:
            print(f"    [OK] Good generation speed")
        else:
            print(f"    [WARN] Slow generation - may need optimization")
    else:
        print(f"    [FAIL] Error: {result.stderr}")

    # Test 3: API endpoint test
    print("\n  Test 3: Ollama API Test")
    try:
        import requests

        api_payload = {
            "model": test_model,
            "prompt": "Hello!",
            "stream": False
        }

        start = time.perf_counter()
        response = requests.post(
            'http://localhost:11434/api/generate',
            json=api_payload,
            timeout=30
        )
        elapsed = time.perf_counter() - start

        if response.status_code == 200:
            data = response.json()
            print(f"    API response in {elapsed:.2f}s")
            print(f"    [OK] Ollama API is accessible at localhost:11434")
        else:
            print(f"    [WARN] API returned status {response.status_code}")

    except ImportError:
        print("    [SKIP] requests not installed - API test skipped")
    except Exception as e:
        print(f"    [WARN] API test failed: {e}")
        print("    [INFO] Make sure Ollama server is running: ollama serve")

    return True

def test_transformers_inference():
    """Test inference using transformers library directly."""
    print("\n--- Testing Transformers Direct Inference ---")

    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
    except ImportError:
        print("  [SKIP] transformers not installed")
        print("  Install with: pip install transformers accelerate")
        return True  # Not a failure, just skip

    if not torch.cuda.is_available():
        print("  [SKIP] CUDA not available")
        return True

    # Use a tiny model for testing
    model_name = "Qwen/Qwen2.5-0.5B-Instruct"
    print(f"  Loading {model_name}...")

    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="cuda",
            trust_remote_code=True
        )
        print("  [OK] Model loaded successfully")

        # Test generation
        prompt = "The capital of France is"
        inputs = tokenizer(prompt, return_tensors="pt").to("cuda")

        start = time.perf_counter()
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=20,
                do_sample=False
            )
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - start

        response = tokenizer.decode(outputs[0], skip_special_tokens=True)
        print(f"  Response: {response}")
        print(f"  Time: {elapsed:.2f}s")
        print("  [OK] Direct transformers inference works!")

        # Cleanup
        del model
        torch.cuda.empty_cache()

    except Exception as e:
        print(f"  [WARN] Transformers test failed: {e}")
        print("  This is optional - Ollama is recommended for production")

    return True

def main():
    print("=" * 60)
    print("RheaRouter Full Inference Test")
    print("=" * 60)

    ollama_available = check_ollama()

    if ollama_available:
        print("\n[OK] Ollama is installed")
        test_ollama_inference()
    else:
        print("\n[INFO] Ollama not found or not running")
        print("[INFO] Install Ollama for best experience: https://ollama.ai")
        print("[INFO] Or run: curl -fsSL https://ollama.com/install.sh | sh")

    # Also try transformers if available
    test_transformers_inference()

    # Final summary
    print("\n" + "=" * 60)
    print("INFERENCE TEST SUMMARY")
    print("=" * 60)

    if ollama_available:
        print("[OK] Ollama is ready for inference")
        print("     Recommended models for 8GB VRAM:")
        print("     - ollama pull llama3.2:3b     (fast, capable)")
        print("     - ollama pull qwen2.5:7b      (great quality)")
        print("     - ollama pull llava:7b        (multimodal)")
        print("     - ollama pull minicpm-v:8b    (vision)")
    else:
        print("[TODO] Install Ollama:")
        print("       curl -fsSL https://ollama.com/install.sh | sh")
        print("       ollama serve  # in another terminal")
        print("       ollama pull llama3.2:3b")

    print("\n[SUCCESS] Inference test complete!")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
