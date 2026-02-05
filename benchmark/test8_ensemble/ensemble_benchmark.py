#!/usr/bin/env python3
"""
RheaRouter Ensemble Benchmark - Multi-Agent Debate vs Individual Models

Comprehensive benchmark comparing:
1. Individual models (Qwen2.5-VL, MiniCPM-V, LLaVA)
2. Traditional OCR (Tesseract, EasyOCR)
3. Ensemble techniques (Weighted Voting, Escalation Chain, Socratic Debate)

Goal: Demonstrate that ensemble beats individual models, especially on degraded images.
"""

import sys
import subprocess
import time
import json
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher
import re

# Check dependencies
try:
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np
except ImportError:
    print("Installing required packages...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'pillow', 'numpy', 'scipy'], check=True)
    from PIL import Image, ImageDraw, ImageFont
    import numpy as np

# Add src to path
BENCHMARK_DIR = Path(__file__).parent
PROJECT_ROOT = BENCHMARK_DIR.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from degradation_suite import EXTREME_DEGRADATIONS, apply_degradation, DegradationConfig

# Directories
IMAGES_DIR = BENCHMARK_DIR / "images"
DEGRADED_DIR = BENCHMARK_DIR / "degraded"
RESULTS_DIR = BENCHMARK_DIR / "results"

# Test texts (same as OCR stress test)
TEST_TEXTS = {
    "receipt": {
        "text": """COFFEE SHOP
123 Main Street
Date: 11/24/2025

Latte          $4.50
Croissant      $3.25
Tip            $1.25
-----------------
TOTAL:         $9.00

Thank you!""",
        "font_size": 24,
        "width": 300,
        "height": 400
    },
    "invoice": {
        "text": """INVOICE #2847
Acme Corporation
billing@acme.com

Item: Widget Pro X
Qty: 5 @ $29.99
Subtotal: $149.95
Tax (8%): $12.00
TOTAL: $161.95

Due: 12/15/2025""",
        "font_size": 22,
        "width": 350,
        "height": 380
    },
    "serial_number": {
        "text": """SERIAL: XK7-9842-BETA
MODEL: RTX-4090-Ti
S/N: 8A3F2B1C9D0E
MAC: 00:1A:2B:3C:4D:5E
UUID: 550e8400-e29b""",
        "font_size": 20,
        "width": 320,
        "height": 220
    },
}


def get_font(size=24):
    """Get a monospace font."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
    ]
    for path in font_paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def create_text_image(text, width=400, height=300, font_size=24):
    """Create a clean image with text."""
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    font = get_font(font_size)
    draw.multiline_text((20, 20), text, font=font, fill='black')
    return img


def calculate_accuracy(original: str, extracted: str) -> dict:
    """Calculate OCR accuracy metrics."""
    orig_clean = ' '.join(original.lower().split())
    ext_clean = ' '.join(extracted.lower().split())

    sequence_ratio = SequenceMatcher(None, orig_clean, ext_clean).ratio()

    orig_words = set(orig_clean.split())
    ext_words = set(ext_clean.split())
    word_recall = len(orig_words & ext_words) / len(orig_words) if orig_words else 0

    orig_chars = orig_clean.replace(' ', '')
    ext_chars = ext_clean.replace(' ', '')
    char_ratio = SequenceMatcher(None, orig_chars, ext_chars).ratio()

    orig_numbers = set(re.findall(r'\$?\d+\.?\d*', original))
    ext_numbers = set(re.findall(r'\$?\d+\.?\d*', extracted))
    number_accuracy = len(orig_numbers & ext_numbers) / len(orig_numbers) if orig_numbers else 1.0

    return {
        'sequence_similarity': sequence_ratio,
        'word_recall': word_recall,
        'char_similarity': char_ratio,
        'number_accuracy': number_accuracy,
        'combined_score': (sequence_ratio + word_recall + char_ratio + number_accuracy) / 4
    }


def run_individual_model_test(model_name: str, image_path: Path, original_text: str) -> dict:
    """Run individual model test using Ollama API."""
    import requests
    import base64

    with open(image_path, 'rb') as f:
        img_base64 = base64.b64encode(f.read()).decode('utf-8')

    payload = {
        "model": model_name,
        "prompt": "Read and transcribe ALL text in this image exactly as written. Output only the transcribed text.",
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

        elapsed = time.perf_counter() - start_time

        if response.status_code == 200:
            data = response.json()
            extracted_text = data.get('response', '')
            accuracy = calculate_accuracy(original_text, extracted_text)

            return {
                'success': True,
                'model': model_name,
                'text': extracted_text,
                'time': elapsed,
                'accuracy': accuracy
            }
        else:
            return {
                'success': False,
                'model': model_name,
                'error': f'HTTP {response.status_code}',
                'time': elapsed,
                'accuracy': {'combined_score': 0}
            }

    except Exception as e:
        return {
            'success': False,
            'model': model_name,
            'error': str(e),
            'time': time.perf_counter() - start_time,
            'accuracy': {'combined_score': 0}
        }


def run_ensemble_test(technique: str, image_path: Path, original_text: str) -> dict:
    """Run ensemble technique test."""
    try:
        from ensemble.facade import EnsembleOCR

        ensemble = EnsembleOCR(use_traditional_ocr=True)
        start_time = time.perf_counter()

        result = ensemble.extract(str(image_path), technique=technique)
        elapsed = time.perf_counter() - start_time

        accuracy = calculate_accuracy(original_text, result.text)

        return {
            'success': result.success,
            'technique': technique,
            'text': result.text,
            'time': elapsed,
            'accuracy': accuracy,
            'models_used': result.models_used,
            'confidence': result.confidence
        }

    except ImportError as e:
        print(f"Warning: Ensemble not available - {e}")
        return {
            'success': False,
            'technique': technique,
            'error': str(e),
            'time': 0,
            'accuracy': {'combined_score': 0}
        }
    except Exception as e:
        return {
            'success': False,
            'technique': technique,
            'error': str(e),
            'time': 0,
            'accuracy': {'combined_score': 0}
        }


def main():
    print("=" * 70)
    print("RheaRouter Ensemble Benchmark")
    print("Multi-Agent Debate vs Individual Models")
    print("=" * 70)
    print(f"Started: {datetime.now().isoformat()}")
    print()

    # Create directories
    IMAGES_DIR.mkdir(exist_ok=True)
    DEGRADED_DIR.mkdir(exist_ok=True)
    RESULTS_DIR.mkdir(exist_ok=True)

    # Generate clean images
    print("Generating test images...")
    clean_images = {}
    for name, config in TEST_TEXTS.items():
        img = create_text_image(
            config['text'],
            width=config['width'],
            height=config['height'],
            font_size=config['font_size']
        )
        path = IMAGES_DIR / f"{name}_clean.png"
        img.save(path)
        clean_images[name] = {
            'path': path,
            'original_text': config['text'],
            'image': img
        }
        print(f"  Created: {name}_clean.png")

    # Generate degraded versions
    print("\nGenerating extreme degraded images...")
    degraded_images = {}

    for text_name, clean_data in clean_images.items():
        degraded_images[text_name] = {}

        for deg_name, deg_config in EXTREME_DEGRADATIONS.items():
            try:
                degraded = apply_degradation(clean_data['image'].copy(), deg_config)
                path = DEGRADED_DIR / f"{text_name}_{deg_name}.png"
                degraded.save(path)
                degraded_images[text_name][deg_name] = {
                    'path': path,
                    'severity': deg_config.severity,
                    'original_text': clean_data['original_text']
                }
            except Exception as e:
                print(f"  Warning: Failed to apply {deg_name} to {text_name}: {e}")

    total_degraded = sum(len(v) for v in degraded_images.values())
    print(f"  Generated {total_degraded} degraded images")

    # Define test subjects
    individual_models = ['qwen2.5vl:7b', 'minicpm-v:8b', 'llava:7b']
    ensemble_techniques = ['weighted_voting', 'escalation_chain', 'socratic_debate']

    # Results storage
    all_results = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'num_texts': len(TEST_TEXTS),
            'num_degradations': len(EXTREME_DEGRADATIONS),
            'individual_models': individual_models,
            'ensemble_techniques': ensemble_techniques,
        },
        'individual_results': {},
        'ensemble_results': {},
    }

    # =========================================================================
    # PHASE 1: Test Individual Models
    # =========================================================================
    print("\n" + "=" * 70)
    print("PHASE 1: Individual Model Testing")
    print("=" * 70)

    for model_name in individual_models:
        print(f"\n--- Testing {model_name} ---")
        all_results['individual_results'][model_name] = {}

        # Warmup
        print("  Warming up...")
        first_image = list(clean_images.values())[0]['path']
        run_individual_model_test(model_name, first_image, "warmup")
        time.sleep(2)

        # Test clean images
        print("  Testing clean images...")
        for text_name, clean_data in clean_images.items():
            result = run_individual_model_test(model_name, clean_data['path'], clean_data['original_text'])
            all_results['individual_results'][model_name][f"{text_name}_clean"] = result
            score = result['accuracy']['combined_score']
            status = "✓" if score > 0.8 else ("~" if score > 0.5 else "✗")
            print(f"    {text_name}_clean: {score:.0%} {status}")

        # Test degraded images (sample for time)
        print("  Testing degraded images...")
        sample_degradations = ['motion_blur_heavy', 'thermal_fade', 'phone_photo_bad', 'ultimate_stress']

        for text_name in clean_images.keys():
            for deg_name in sample_degradations:
                if deg_name not in degraded_images[text_name]:
                    continue

                deg_data = degraded_images[text_name][deg_name]
                result = run_individual_model_test(model_name, deg_data['path'], deg_data['original_text'])
                all_results['individual_results'][model_name][f"{text_name}_{deg_name}"] = result
                score = result['accuracy']['combined_score']
                status = "✓" if score > 0.8 else ("~" if score > 0.5 else "✗")
                print(f"    {text_name}_{deg_name}: {score:.0%} {status}")

    # =========================================================================
    # PHASE 2: Test Ensemble Techniques
    # =========================================================================
    print("\n" + "=" * 70)
    print("PHASE 2: Ensemble Technique Testing")
    print("=" * 70)

    for technique in ensemble_techniques:
        print(f"\n--- Testing {technique} ---")
        all_results['ensemble_results'][technique] = {}

        # Test clean images
        print("  Testing clean images...")
        for text_name, clean_data in clean_images.items():
            result = run_ensemble_test(technique, clean_data['path'], clean_data['original_text'])
            all_results['ensemble_results'][technique][f"{text_name}_clean"] = result
            score = result['accuracy']['combined_score']
            status = "✓" if score > 0.8 else ("~" if score > 0.5 else "✗")
            print(f"    {text_name}_clean: {score:.0%} {status}")

        # Test degraded images
        print("  Testing degraded images...")
        sample_degradations = ['motion_blur_heavy', 'thermal_fade', 'phone_photo_bad', 'ultimate_stress']

        for text_name in clean_images.keys():
            for deg_name in sample_degradations:
                if deg_name not in degraded_images[text_name]:
                    continue

                deg_data = degraded_images[text_name][deg_name]
                result = run_ensemble_test(technique, deg_data['path'], deg_data['original_text'])
                all_results['ensemble_results'][technique][f"{text_name}_{deg_name}"] = result
                score = result['accuracy']['combined_score']
                status = "✓" if score > 0.8 else ("~" if score > 0.5 else "✗")
                print(f"    {text_name}_{deg_name}: {score:.0%} {status}")

    # =========================================================================
    # PHASE 3: Results Summary
    # =========================================================================
    print("\n" + "=" * 70)
    print("RESULTS SUMMARY")
    print("=" * 70)

    # Calculate averages
    print("\n--- Individual Models ---")
    for model_name in individual_models:
        results = all_results['individual_results'].get(model_name, {})
        scores = [r['accuracy']['combined_score'] for r in results.values() if r.get('success')]
        avg = sum(scores) / len(scores) if scores else 0
        print(f"  {model_name}: {avg:.0%} average ({len(scores)} tests)")

    print("\n--- Ensemble Techniques ---")
    for technique in ensemble_techniques:
        results = all_results['ensemble_results'].get(technique, {})
        scores = [r['accuracy']['combined_score'] for r in results.values() if r.get('success')]
        avg = sum(scores) / len(scores) if scores else 0
        print(f"  {technique}: {avg:.0%} average ({len(scores)} tests)")

    # Save results
    results_file = RESULTS_DIR / f"ensemble_benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2, default=str)

    print(f"\n✅ Results saved to: {results_file}")
    print(f"Completed: {datetime.now().isoformat()}")


if __name__ == "__main__":
    main()
