#!/usr/bin/env python3
"""
RheaRouter Test 3: Image Resolution Scaling Test

Tests how resolution affects:
- Response time
- Response quality
- VRAM usage
- Find optimal resolution for speed/quality tradeoff
"""

import subprocess
import time
import json
import os
import base64
from pathlib import Path
from datetime import datetime
from PIL import Image
import io
import requests

MODELS = ["minicpm-v:8b", "llava:7b"]
TEST_DIR = Path(__file__).parent
IMAGES_DIR = TEST_DIR / "images"
RESULTS_DIR = TEST_DIR / "results"

# Source image from main benchmark
SOURCE_IMAGE = Path(__file__).parent.parent / "images" / "04_pet_cat.jpg"

# Resolutions to test
RESOLUTIONS = [
    (128, 128, "tiny"),
    (256, 256, "small"),
    (512, 512, "medium"),
    (768, 768, "large"),
    (1024, 1024, "xlarge"),
    (1536, 1536, "xxlarge"),
]

def get_vram_usage():
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

def create_scaled_images(source_path):
    """Create test images at different resolutions."""
    IMAGES_DIR.mkdir(exist_ok=True)

    original = Image.open(source_path)
    images = []

    for width, height, label in RESOLUTIONS:
        # Resize maintaining aspect ratio, then center crop
        scaled = original.copy()
        scaled.thumbnail((width * 2, height * 2), Image.Resampling.LANCZOS)

        # Center crop to exact size
        w, h = scaled.size
        left = (w - width) // 2
        top = (h - height) // 2
        right = left + width
        bottom = top + height

        if left >= 0 and top >= 0:
            scaled = scaled.crop((left, top, right, bottom))
        else:
            # If image is smaller, resize with padding
            scaled = original.copy()
            scaled = scaled.resize((width, height), Image.Resampling.LANCZOS)

        output_path = IMAGES_DIR / f"cat_{label}_{width}x{height}.jpg"
        scaled.save(output_path, "JPEG", quality=90)

        file_size = output_path.stat().st_size / 1024  # KB
        images.append((output_path, width, height, label, file_size))

    return images

def encode_image_base64(image_path):
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def run_resolution_test(model, image_path, prompt):
    """Run test and return results."""
    img_base64 = encode_image_base64(image_path)

    payload = {
        "model": model,
        "prompt": prompt,
        "images": [img_base64],
        "stream": False
    }

    vram_before = get_vram_usage()
    start_time = time.perf_counter()

    try:
        response = requests.post(
            'http://localhost:11434/api/generate',
            json=payload,
            timeout=180
        )

        end_time = time.perf_counter()
        vram_after = get_vram_usage()

        if response.status_code == 200:
            data = response.json()
            return {
                'success': True,
                'response': data.get('response', ''),
                'total_time': end_time - start_time,
                'eval_count': data.get('eval_count', 0),
                'eval_duration_ns': data.get('eval_duration', 0),
                'prompt_eval_duration_ns': data.get('prompt_eval_duration', 0),
                'vram_before': vram_before,
                'vram_after': vram_after,
            }
        else:
            return {
                'success': False,
                'error': f'HTTP {response.status_code}',
                'total_time': end_time - start_time,
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'total_time': time.perf_counter() - start_time,
        }

def score_response_quality(response):
    """Score response quality based on detail keywords."""
    keywords = [
        'cat', 'fur', 'eyes', 'whiskers', 'tail', 'paws',
        'sitting', 'lying', 'resting', 'looking',
        'gray', 'white', 'brown', 'tabby', 'fluffy',
        'garden', 'outdoor', 'ground', 'stone', 'pavement'
    ]

    response_lower = response.lower()
    found = sum(1 for kw in keywords if kw in response_lower)
    return found / len(keywords)

def main():
    print("=" * 70)
    print("RheaRouter Test 3: Image Resolution Scaling")
    print("=" * 70)
    print(f"Started: {datetime.now().isoformat()}")
    print()

    RESULTS_DIR.mkdir(exist_ok=True)

    # Create scaled images
    print("Creating scaled test images...")
    images = create_scaled_images(SOURCE_IMAGE)
    print(f"Created {len(images)} images at different resolutions:")
    for path, w, h, label, size_kb in images:
        print(f"  {label}: {w}x{h} ({size_kb:.1f} KB)")
    print()

    prompt = "Describe this image in detail. What do you see?"

    all_results = {}

    for model in MODELS:
        print(f"\n{'='*70}")
        print(f"MODEL: {model}")
        print(f"{'='*70}")

        # Warmup
        print("  Warming up...")
        run_resolution_test(model, images[2][0], "What is this?")
        time.sleep(2)

        model_results = []

        for image_path, width, height, label, size_kb in images:
            print(f"\n  Testing: {label} ({width}x{height}, {size_kb:.1f} KB)")

            # Run 3 times for average
            times = []
            responses = []
            vram_usages = []

            for run in range(3):
                result = run_resolution_test(model, image_path, prompt)

                if result['success']:
                    times.append(result['total_time'])
                    responses.append(result['response'])
                    vram_usages.append(result.get('vram_after'))

            if times:
                avg_time = sum(times) / len(times)
                avg_vram = sum(v for v in vram_usages if v) / len([v for v in vram_usages if v]) if vram_usages else None

                # Score quality of best response
                quality_scores = [score_response_quality(r) for r in responses]
                avg_quality = sum(quality_scores) / len(quality_scores)
                best_response = responses[quality_scores.index(max(quality_scores))]

                # Calculate efficiency (quality per second)
                efficiency = avg_quality / avg_time if avg_time > 0 else 0

                test_result = {
                    'resolution': f"{width}x{height}",
                    'label': label,
                    'file_size_kb': size_kb,
                    'avg_time': avg_time,
                    'min_time': min(times),
                    'max_time': max(times),
                    'avg_quality': avg_quality,
                    'efficiency': efficiency,
                    'vram_mb': avg_vram,
                    'sample_response': best_response[:200],
                    'word_count': len(best_response.split()),
                }

                model_results.append(test_result)

                print(f"    Time: {avg_time:.2f}s (±{max(times)-min(times):.2f}s)")
                print(f"    Quality: {avg_quality:.0%}")
                print(f"    Efficiency: {efficiency:.2f} quality/sec")
                print(f"    VRAM: {avg_vram:.0f} MB" if avg_vram else "    VRAM: N/A")
            else:
                print(f"    [FAIL] All 3 attempts failed")

        all_results[model] = model_results

    # Save results
    results_file = RESULTS_DIR / f"resolution_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to: {results_file}")

    # Summary
    print("\n" + "=" * 70)
    print("RESOLUTION SCALING SUMMARY")
    print("=" * 70)

    for model in MODELS:
        print(f"\n{model}:")
        print(f"{'Resolution':<12} {'Time':>8} {'Quality':>10} {'Efficiency':>12} {'Words':>8}")
        print("-" * 55)

        for r in all_results[model]:
            print(f"{r['resolution']:<12} {r['avg_time']:>7.2f}s {r['avg_quality']:>9.0%} {r['efficiency']:>11.2f} {r['word_count']:>8}")

        # Find optimal resolution
        best_efficiency = max(all_results[model], key=lambda x: x['efficiency'])
        best_quality = max(all_results[model], key=lambda x: x['avg_quality'])

        print(f"\n  Best efficiency: {best_efficiency['resolution']} ({best_efficiency['efficiency']:.2f})")
        print(f"  Best quality: {best_quality['resolution']} ({best_quality['avg_quality']:.0%})")

    # Compare models at medium resolution (512x512)
    print("\n" + "-" * 40)
    medium_minicpm = next((r for r in all_results["minicpm-v:8b"] if r['label'] == 'medium'), None)
    medium_llava = next((r for r in all_results["llava:7b"] if r['label'] == 'medium'), None)

    if medium_minicpm and medium_llava:
        if medium_minicpm['efficiency'] > medium_llava['efficiency']:
            print(f"WINNER (512x512 efficiency): minicpm-v:8b ({medium_minicpm['efficiency']:.2f} vs {medium_llava['efficiency']:.2f})")
        elif medium_llava['efficiency'] > medium_minicpm['efficiency']:
            print(f"WINNER (512x512 efficiency): llava:7b ({medium_llava['efficiency']:.2f} vs {medium_minicpm['efficiency']:.2f})")
        else:
            print("TIE at 512x512")

    print("\n" + "=" * 70)
    print("TEST 3 COMPLETE")
    print("=" * 70)

    return all_results

if __name__ == "__main__":
    main()
