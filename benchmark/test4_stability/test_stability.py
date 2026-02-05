#!/usr/bin/env python3
"""
RheaRouter Test 4: Long-Running Stability Test

Tests sustained operation over many requests:
- VRAM leaks
- Response time drift
- Error rate over time
- Temperature/throttling
"""

import subprocess
import time
import json
import os
import base64
from pathlib import Path
from datetime import datetime
import requests

MODELS = ["minicpm-v:8b", "llava:7b"]
TEST_DIR = Path(__file__).parent
RESULTS_DIR = TEST_DIR / "results"
IMAGES_DIR = Path(__file__).parent.parent / "images"

# Test configuration
NUM_REQUESTS = 50  # Total requests per model
SAMPLE_INTERVAL = 5  # Sample metrics every N requests

def get_gpu_metrics():
    """Get GPU temperature, utilization, and VRAM."""
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw',
             '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(', ')
            return {
                'temperature_c': int(parts[0]),
                'utilization_pct': int(parts[1]),
                'vram_used_mb': int(parts[2]),
                'vram_total_mb': int(parts[3]),
                'power_w': float(parts[4]) if parts[4] != '[N/A]' else None
            }
    except:
        pass
    return None

def encode_image_base64(image_path):
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def make_request(model, image_path, prompt):
    """Make a single request."""
    img_base64 = encode_image_base64(image_path)

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

        if response.status_code == 200:
            data = response.json()
            return {
                'success': True,
                'total_time': end_time - start_time,
                'eval_count': data.get('eval_count', 0),
                'response_length': len(data.get('response', '')),
            }
        else:
            return {
                'success': False,
                'total_time': end_time - start_time,
                'error': f'HTTP {response.status_code}'
            }
    except Exception as e:
        return {
            'success': False,
            'total_time': time.perf_counter() - start_time,
            'error': str(e)
        }

def run_stability_test(model, images, num_requests):
    """Run stability test for a single model."""
    prompts = [
        "What is in this image?",
        "Describe what you see.",
        "What's the main subject?",
    ]

    results = []
    gpu_samples = []
    start_time = datetime.now()

    print(f"    Running {num_requests} requests...")
    print(f"    Progress: ", end='', flush=True)

    for i in range(num_requests):
        # Select image and prompt (rotate through them)
        image = images[i % len(images)]
        prompt = prompts[i % len(prompts)]

        # Sample GPU metrics periodically
        if i % SAMPLE_INTERVAL == 0:
            metrics = get_gpu_metrics()
            if metrics:
                metrics['request_num'] = i
                metrics['elapsed_sec'] = (datetime.now() - start_time).total_seconds()
                gpu_samples.append(metrics)

        # Make request
        result = make_request(model, image, prompt)
        result['request_num'] = i
        result['timestamp'] = datetime.now().isoformat()
        results.append(result)

        # Progress indicator
        if i % 10 == 0:
            print(f"{i}", end='', flush=True)
        else:
            print(".", end='', flush=True)

    print(f" {num_requests} Done!")

    # Final GPU sample
    metrics = get_gpu_metrics()
    if metrics:
        metrics['request_num'] = num_requests
        metrics['elapsed_sec'] = (datetime.now() - start_time).total_seconds()
        gpu_samples.append(metrics)

    return results, gpu_samples

def analyze_stability(results, gpu_samples):
    """Analyze stability metrics."""
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    analysis = {
        'total_requests': len(results),
        'successful': len(successful),
        'failed': len(failed),
        'success_rate': len(successful) / len(results) if results else 0,
    }

    if successful:
        times = [r['total_time'] for r in successful]
        analysis['avg_time'] = sum(times) / len(times)
        analysis['min_time'] = min(times)
        analysis['max_time'] = max(times)

        # Time drift analysis (compare first 10 vs last 10)
        first_10 = times[:10]
        last_10 = times[-10:]
        analysis['first_10_avg'] = sum(first_10) / len(first_10) if first_10 else 0
        analysis['last_10_avg'] = sum(last_10) / len(last_10) if last_10 else 0
        analysis['time_drift_pct'] = ((analysis['last_10_avg'] - analysis['first_10_avg']) /
                                       analysis['first_10_avg'] * 100) if analysis['first_10_avg'] > 0 else 0

    if gpu_samples:
        temps = [s['temperature_c'] for s in gpu_samples if s.get('temperature_c')]
        vrams = [s['vram_used_mb'] for s in gpu_samples if s.get('vram_used_mb')]

        if temps:
            analysis['temp_start'] = temps[0]
            analysis['temp_end'] = temps[-1]
            analysis['temp_max'] = max(temps)
            analysis['temp_drift'] = temps[-1] - temps[0]

        if vrams:
            analysis['vram_start'] = vrams[0]
            analysis['vram_end'] = vrams[-1]
            analysis['vram_max'] = max(vrams)
            analysis['vram_leak_mb'] = vrams[-1] - vrams[0]

    if failed:
        analysis['errors'] = list(set(r.get('error', 'unknown') for r in failed))

    return analysis

def main():
    print("=" * 70)
    print("RheaRouter Test 4: Long-Running Stability Test")
    print("=" * 70)
    print(f"Started: {datetime.now().isoformat()}")
    print(f"Configuration: {NUM_REQUESTS} requests per model")
    print()

    RESULTS_DIR.mkdir(exist_ok=True)

    # Get test images
    images = list(IMAGES_DIR.glob("*.jpg")) + list(IMAGES_DIR.glob("*.png"))
    if not images:
        print("ERROR: No test images found!")
        return
    print(f"Using {len(images)} test images")
    print()

    all_results = {}

    for model in MODELS:
        print(f"\n{'='*70}")
        print(f"MODEL: {model}")
        print(f"{'='*70}")

        # Initial GPU state
        initial_gpu = get_gpu_metrics()
        if initial_gpu:
            print(f"  Initial state: {initial_gpu['temperature_c']}°C, "
                  f"{initial_gpu['vram_used_mb']}MB VRAM, "
                  f"{initial_gpu['utilization_pct']}% util")

        # Warmup
        print("  Warming up...")
        make_request(model, images[0], "What is this?")
        time.sleep(3)

        # Run stability test
        results, gpu_samples = run_stability_test(model, images, NUM_REQUESTS)

        # Analyze
        analysis = analyze_stability(results, gpu_samples)

        all_results[model] = {
            'analysis': analysis,
            'raw_results': results,
            'gpu_samples': gpu_samples,
        }

        # Print summary
        print(f"\n  Results:")
        print(f"    Success rate: {analysis['success_rate']:.0%} ({analysis['successful']}/{analysis['total_requests']})")
        print(f"    Avg time: {analysis.get('avg_time', 0):.2f}s")
        print(f"    Time range: {analysis.get('min_time', 0):.2f}s - {analysis.get('max_time', 0):.2f}s")
        print(f"    Time drift: {analysis.get('time_drift_pct', 0):+.1f}% (first 10 vs last 10)")

        if 'temp_drift' in analysis:
            print(f"    Temperature: {analysis['temp_start']}°C → {analysis['temp_end']}°C (Δ{analysis['temp_drift']:+d}°C)")
        if 'vram_leak_mb' in analysis:
            print(f"    VRAM: {analysis['vram_start']}MB → {analysis['vram_end']}MB (Δ{analysis['vram_leak_mb']:+d}MB)")

        if analysis.get('errors'):
            print(f"    Errors: {analysis['errors']}")

        # Brief cooldown between models
        time.sleep(5)

    # Save results
    results_file = RESULTS_DIR / f"stability_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        # Don't save raw results to keep file size manageable
        save_data = {
            model: {
                'analysis': data['analysis'],
                'gpu_samples': data['gpu_samples'],
            }
            for model, data in all_results.items()
        }
        json.dump(save_data, f, indent=2)
    print(f"\nResults saved to: {results_file}")

    # Summary comparison
    print("\n" + "=" * 70)
    print("STABILITY TEST SUMMARY")
    print("=" * 70)

    print("\n{:<15} {:<10} {:<12} {:<12} {:<12} {:<12}".format(
        "Model", "Success%", "Avg Time", "Time Drift", "Temp Δ", "VRAM Δ"
    ))
    print("-" * 75)

    for model in MODELS:
        a = all_results[model]['analysis']
        print("{:<15} {:<10.0%} {:<12.2f}s {:<12.1f}% {:<12} {:<12}".format(
            model.split(':')[0],
            a['success_rate'],
            a.get('avg_time', 0),
            a.get('time_drift_pct', 0),
            f"{a.get('temp_drift', 'N/A'):+d}°C" if 'temp_drift' in a else "N/A",
            f"{a.get('vram_leak_mb', 'N/A'):+d}MB" if 'vram_leak_mb' in a else "N/A"
        ))

    # Determine winner based on stability
    print("\n" + "-" * 40)

    a_minicpm = all_results["minicpm-v:8b"]['analysis']
    a_llava = all_results["llava:7b"]['analysis']

    # Score: higher success rate is better, lower time drift is better, lower VRAM leak is better
    score_minicpm = a_minicpm['success_rate'] - abs(a_minicpm.get('time_drift_pct', 0)) / 100
    score_llava = a_llava['success_rate'] - abs(a_llava.get('time_drift_pct', 0)) / 100

    if score_minicpm > score_llava:
        print(f"WINNER (stability): minicpm-v:8b")
    elif score_llava > score_minicpm:
        print(f"WINNER (stability): llava:7b")
    else:
        print("TIE")

    print("\n" + "=" * 70)
    print("TEST 4 COMPLETE")
    print("=" * 70)

    return all_results

if __name__ == "__main__":
    main()
