#!/usr/bin/env python3
"""
RheaRouter Test 2: Concurrent Request Stress Test

Tests how models handle multiple simultaneous requests:
- Queue handling
- VRAM stability under load
- Response time degradation
- Error rate under pressure
"""

import subprocess
import time
import json
import os
import base64
import threading
import queue
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

MODELS = ["minicpm-v:8b", "llava:7b"]
TEST_DIR = Path(__file__).parent
RESULTS_DIR = TEST_DIR / "results"

# Use images from the main benchmark
IMAGES_DIR = Path(__file__).parent.parent / "images"

def get_vram_usage():
    """Get current VRAM usage."""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=memory.used', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return int(result.stdout.strip())
    except:
        pass
    return None

def encode_image_base64(image_path):
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def make_request(model, image_path, prompt, request_id):
    """Make a single request and return timing info."""
    img_base64 = encode_image_base64(image_path)

    payload = {
        "model": model,
        "prompt": prompt,
        "images": [img_base64],
        "stream": False
    }

    start_time = time.perf_counter()
    vram_before = get_vram_usage()

    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json=payload,
            timeout=180  # Longer timeout for queued requests
        )

        end_time = time.perf_counter()
        vram_after = get_vram_usage()

        if response.status_code == 200:
            data = response.json()
            return {
                'request_id': request_id,
                'success': True,
                'total_time': end_time - start_time,
                'response_length': len(data.get('response', '')),
                'eval_count': data.get('eval_count', 0),
                'vram_before': vram_before,
                'vram_after': vram_after,
                'error': None
            }
        else:
            return {
                'request_id': request_id,
                'success': False,
                'total_time': end_time - start_time,
                'error': f'HTTP {response.status_code}'
            }
    except requests.Timeout:
        return {
            'request_id': request_id,
            'success': False,
            'total_time': 180,
            'error': 'TIMEOUT'
        }
    except Exception as e:
        return {
            'request_id': request_id,
            'success': False,
            'total_time': time.perf_counter() - start_time,
            'error': str(e)
        }

def run_concurrent_test(model, num_concurrent, num_total, images):
    """Run concurrent requests and collect results."""
    prompt = "Briefly describe this image in one sentence."

    results = []
    vram_samples = []

    print(f"    Sending {num_total} requests with concurrency={num_concurrent}...")

    # Sample VRAM during test
    vram_samples.append(('start', get_vram_usage()))

    start_time = time.perf_counter()

    with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
        futures = []
        for i in range(num_total):
            image = images[i % len(images)]
            future = executor.submit(make_request, model, image, prompt, i)
            futures.append(future)

        # Collect results as they complete
        for future in as_completed(futures):
            result = future.result()
            results.append(result)

            # Sample VRAM periodically
            if len(results) % 3 == 0:
                vram_samples.append((len(results), get_vram_usage()))

    total_time = time.perf_counter() - start_time
    vram_samples.append(('end', get_vram_usage()))

    return results, total_time, vram_samples

def main():
    print("=" * 70)
    print("RheaRouter Test 2: Concurrent Request Stress Test")
    print("=" * 70)
    print(f"Started: {datetime.now().isoformat()}")
    print()

    RESULTS_DIR.mkdir(exist_ok=True)

    # Get test images
    images = list(IMAGES_DIR.glob("*.jpg")) + list(IMAGES_DIR.glob("*.png"))
    if not images:
        print("ERROR: No test images found!")
        return
    print(f"Using {len(images)} test images")

    # Test configurations
    test_configs = [
        (1, 5, "Baseline (sequential)"),
        (2, 6, "Light load (2 concurrent)"),
        (3, 9, "Medium load (3 concurrent)"),
        (5, 10, "Heavy load (5 concurrent)"),
    ]

    all_results = {}

    for model in MODELS:
        print(f"\n{'='*70}")
        print(f"MODEL: {model}")
        print(f"{'='*70}")

        # Warmup
        print("  Warming up model...")
        make_request(model, images[0], "What is this?", -1)
        time.sleep(2)

        model_results = {}

        for num_concurrent, num_total, description in test_configs:
            print(f"\n  Test: {description}")

            results, total_time, vram_samples = run_concurrent_test(
                model, num_concurrent, num_total, images
            )

            # Calculate metrics
            successful = [r for r in results if r['success']]
            failed = [r for r in results if not r['success']]

            if successful:
                times = [r['total_time'] for r in successful]
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                throughput = len(successful) / total_time
            else:
                avg_time = min_time = max_time = 0
                throughput = 0

            # VRAM analysis
            vram_values = [v for _, v in vram_samples if v is not None]
            vram_peak = max(vram_values) if vram_values else None
            vram_min = min(vram_values) if vram_values else None

            test_result = {
                'description': description,
                'num_concurrent': num_concurrent,
                'num_total': num_total,
                'total_time': total_time,
                'success_count': len(successful),
                'failure_count': len(failed),
                'success_rate': len(successful) / num_total,
                'avg_response_time': avg_time,
                'min_response_time': min_time,
                'max_response_time': max_time,
                'throughput_rps': throughput,
                'vram_peak_mb': vram_peak,
                'vram_min_mb': vram_min,
                'errors': [r['error'] for r in failed],
            }

            model_results[description] = test_result

            # Print summary
            print(f"    Success: {len(successful)}/{num_total} ({test_result['success_rate']:.0%})")
            print(f"    Avg time: {avg_time:.2f}s (min: {min_time:.2f}s, max: {max_time:.2f}s)")
            print(f"    Throughput: {throughput:.2f} req/s")
            print(f"    VRAM: {vram_min}-{vram_peak} MB")

            if failed:
                print(f"    Errors: {set(r['error'] for r in failed)}")

            # Brief pause between tests
            time.sleep(3)

        all_results[model] = model_results

    # Save results
    results_file = RESULTS_DIR / f"concurrent_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to: {results_file}")

    # Summary comparison
    print("\n" + "=" * 70)
    print("CONCURRENT TEST SUMMARY")
    print("=" * 70)

    print("\n{:<25} {:<15} {:<15} {:<15} {:<15}".format(
        "Test", "Model", "Success%", "Avg Time", "Throughput"
    ))
    print("-" * 85)

    for desc in [c[2] for c in test_configs]:
        for model in MODELS:
            r = all_results[model][desc]
            print("{:<25} {:<15} {:<15.0%} {:<15.2f}s {:<15.2f}".format(
                desc[:24], model.split(':')[0], r['success_rate'],
                r['avg_response_time'], r['throughput_rps']
            ))
        print()

    # Determine winner based on throughput at heavy load
    heavy_load = "Heavy load (5 concurrent)"
    throughput_minicpm = all_results["minicpm-v:8b"][heavy_load]['throughput_rps']
    throughput_llava = all_results["llava:7b"][heavy_load]['throughput_rps']

    success_minicpm = all_results["minicpm-v:8b"][heavy_load]['success_rate']
    success_llava = all_results["llava:7b"][heavy_load]['success_rate']

    print("-" * 40)
    if success_minicpm > success_llava:
        print(f"WINNER (reliability): minicpm-v:8b ({success_minicpm:.0%} vs {success_llava:.0%})")
    elif success_llava > success_minicpm:
        print(f"WINNER (reliability): llava:7b ({success_llava:.0%} vs {success_minicpm:.0%})")
    else:
        if throughput_minicpm > throughput_llava:
            print(f"WINNER (throughput): minicpm-v:8b ({throughput_minicpm:.2f} vs {throughput_llava:.2f} req/s)")
        elif throughput_llava > throughput_minicpm:
            print(f"WINNER (throughput): llava:7b ({throughput_llava:.2f} vs {throughput_minicpm:.2f} req/s)")
        else:
            print("TIE")

    print("\n" + "=" * 70)
    print("TEST 2 COMPLETE")
    print("=" * 70)

    return all_results

if __name__ == "__main__":
    main()
