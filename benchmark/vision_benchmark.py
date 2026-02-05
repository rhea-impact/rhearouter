#!/usr/bin/env python3
"""
RheaRouter Vision Model Benchmark

Tests multiple vision models against diverse images and measures:
- Response time (time to first token, total time)
- Response quality (subjective, logged for review)
- VRAM usage
- Tokens generated
"""

import subprocess
import time
import json
import os
import base64
from pathlib import Path
from datetime import datetime

# Configuration
MODELS = ["minicpm-v:8b", "llava:7b"]
IMAGES_DIR = Path(__file__).parent / "images"
RESULTS_DIR = Path(__file__).parent / "results"

# Test prompts - varied to test different capabilities
PROMPTS = [
    "Describe this image in detail.",
    "What objects can you identify in this image?",
    "What is the main subject of this image and what is it doing?",
]

def get_image_files():
    """Get all image files from the images directory."""
    extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    images = []
    for f in sorted(IMAGES_DIR.iterdir()):
        if f.suffix.lower() in extensions:
            images.append(f)
    return images

def encode_image_base64(image_path):
    """Encode image to base64."""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def get_vram_usage():
    """Get current VRAM usage from nvidia-smi."""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=memory.used,memory.total', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            used, total = result.stdout.strip().split(', ')
            return int(used), int(total)
    except:
        pass
    return None, None

def run_ollama_vision(model, image_path, prompt):
    """Run Ollama vision model on an image and return timing + response."""

    # Construct the command
    cmd = ['ollama', 'run', model, f'{prompt}']

    # Get VRAM before
    vram_before, vram_total = get_vram_usage()

    # Time the execution
    start_time = time.perf_counter()

    try:
        # Run with image input via stdin description
        result = subprocess.run(
            cmd,
            input=f"[Image: {image_path}]",
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, 'OLLAMA_HOST': 'http://localhost:11434'}
        )

        end_time = time.perf_counter()

        # Get VRAM after
        vram_after, _ = get_vram_usage()

        response = result.stdout.strip() if result.returncode == 0 else f"ERROR: {result.stderr}"

        return {
            'success': result.returncode == 0,
            'response': response,
            'total_time': end_time - start_time,
            'vram_before_mb': vram_before,
            'vram_after_mb': vram_after,
            'vram_total_mb': vram_total,
            'word_count': len(response.split()),
            'char_count': len(response),
        }

    except subprocess.TimeoutExpired:
        return {
            'success': False,
            'response': 'TIMEOUT after 120s',
            'total_time': 120,
            'vram_before_mb': vram_before,
            'vram_after_mb': None,
            'vram_total_mb': vram_total,
            'word_count': 0,
            'char_count': 0,
        }
    except Exception as e:
        return {
            'success': False,
            'response': f'EXCEPTION: {str(e)}',
            'total_time': time.perf_counter() - start_time,
            'vram_before_mb': vram_before,
            'vram_after_mb': None,
            'vram_total_mb': vram_total,
            'word_count': 0,
            'char_count': 0,
        }

def run_ollama_vision_api(model, image_path, prompt):
    """Run Ollama vision model via API for more accurate timing."""
    import requests

    # Encode image
    img_base64 = encode_image_base64(image_path)

    # Get VRAM before
    vram_before, vram_total = get_vram_usage()

    payload = {
        "model": model,
        "prompt": prompt,
        "images": [img_base64],
        "stream": False
    }

    start_time = time.perf_counter()

    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json=payload,
            timeout=120
        )

        end_time = time.perf_counter()
        vram_after, _ = get_vram_usage()

        if response.status_code == 200:
            data = response.json()
            return {
                'success': True,
                'response': data.get('response', ''),
                'total_time': end_time - start_time,
                'eval_duration_ns': data.get('eval_duration', 0),
                'prompt_eval_duration_ns': data.get('prompt_eval_duration', 0),
                'eval_count': data.get('eval_count', 0),
                'vram_before_mb': vram_before,
                'vram_after_mb': vram_after,
                'vram_total_mb': vram_total,
                'word_count': len(data.get('response', '').split()),
                'char_count': len(data.get('response', '')),
            }
        else:
            return {
                'success': False,
                'response': f'HTTP {response.status_code}: {response.text}',
                'total_time': end_time - start_time,
                'vram_before_mb': vram_before,
                'vram_after_mb': vram_after,
                'vram_total_mb': vram_total,
                'word_count': 0,
                'char_count': 0,
            }

    except requests.Timeout:
        return {
            'success': False,
            'response': 'TIMEOUT after 120s',
            'total_time': 120,
            'vram_before_mb': vram_before,
            'vram_after_mb': None,
            'vram_total_mb': vram_total,
            'word_count': 0,
            'char_count': 0,
        }
    except Exception as e:
        return {
            'success': False,
            'response': f'EXCEPTION: {str(e)}',
            'total_time': time.perf_counter() - start_time,
            'vram_before_mb': vram_before,
            'vram_after_mb': None,
            'vram_total_mb': vram_total,
            'word_count': 0,
            'char_count': 0,
        }

def main():
    print("=" * 70)
    print("RheaRouter Vision Model Benchmark")
    print("=" * 70)
    print(f"Started: {datetime.now().isoformat()}")
    print()

    # Create results directory
    RESULTS_DIR.mkdir(exist_ok=True)

    # Get images
    images = get_image_files()
    print(f"Found {len(images)} test images:")
    for img in images:
        size_kb = img.stat().st_size / 1024
        print(f"  - {img.name} ({size_kb:.1f} KB)")
    print()

    # Use single prompt for consistency
    prompt = PROMPTS[0]  # "Describe this image in detail."
    print(f"Test prompt: \"{prompt}\"")
    print()

    all_results = []

    for model in MODELS:
        print(f"\n{'='*70}")
        print(f"MODEL: {model}")
        print(f"{'='*70}")

        # Warm up the model first
        print(f"  Warming up {model}...")
        warmup = run_ollama_vision_api(model, images[0], "What is this?")
        print(f"  Warmup complete ({warmup['total_time']:.2f}s)")
        print()

        for image_path in images:
            print(f"  Testing: {image_path.name}")

            result = run_ollama_vision_api(model, image_path, prompt)

            # Add metadata
            result['model'] = model
            result['image'] = image_path.name
            result['prompt'] = prompt
            result['timestamp'] = datetime.now().isoformat()

            all_results.append(result)

            # Print summary
            if result['success']:
                tokens_per_sec = 0
                if result.get('eval_duration_ns', 0) > 0:
                    tokens_per_sec = result.get('eval_count', 0) / (result['eval_duration_ns'] / 1e9)

                print(f"    [OK] {result['total_time']:.2f}s | "
                      f"{result['word_count']} words | "
                      f"{tokens_per_sec:.1f} tok/s | "
                      f"VRAM: {result.get('vram_after_mb', 'N/A')} MB")
                print(f"    Response preview: {result['response'][:100]}...")
            else:
                print(f"    [FAIL] {result['response'][:100]}")
            print()

    # Save raw results
    results_file = RESULTS_DIR / f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nRaw results saved to: {results_file}")

    # Print summary table
    print("\n" + "=" * 70)
    print("BENCHMARK SUMMARY")
    print("=" * 70)

    # Group by model
    for model in MODELS:
        model_results = [r for r in all_results if r['model'] == model]
        successful = [r for r in model_results if r['success']]

        if successful:
            avg_time = sum(r['total_time'] for r in successful) / len(successful)
            avg_words = sum(r['word_count'] for r in successful) / len(successful)

            total_tokens = sum(r.get('eval_count', 0) for r in successful)
            total_eval_time = sum(r.get('eval_duration_ns', 0) for r in successful) / 1e9
            avg_tokens_per_sec = total_tokens / total_eval_time if total_eval_time > 0 else 0

            print(f"\n{model}:")
            print(f"  Success rate: {len(successful)}/{len(model_results)}")
            print(f"  Avg response time: {avg_time:.2f}s")
            print(f"  Avg words per response: {avg_words:.0f}")
            print(f"  Avg tokens/sec: {avg_tokens_per_sec:.1f}")

            # Show VRAM
            vram_samples = [r.get('vram_after_mb') for r in successful if r.get('vram_after_mb')]
            if vram_samples:
                print(f"  VRAM usage: {max(vram_samples)} MB peak")
        else:
            print(f"\n{model}: All tests failed!")

    print("\n" + "=" * 70)
    print("BENCHMARK COMPLETE")
    print("=" * 70)

    return all_results

if __name__ == "__main__":
    try:
        import requests
    except ImportError:
        print("Installing requests...")
        subprocess.run(['pip', 'install', 'requests'], check=True)
        import requests

    main()
