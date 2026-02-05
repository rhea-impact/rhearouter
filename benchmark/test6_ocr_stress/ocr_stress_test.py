#!/usr/bin/env python3
"""
RheaRouter OCR Stress Test - Adversarial Text Recognition

Creates images with known text, applies various degradations,
then tests how well vision models can recover the original text.

Degradation types:
- Rotation (slight to extreme)
- Gaussian blur
- Salt & pepper noise
- Perspective warp (skew)
- Brightness/contrast issues
- JPEG artifacts (compression)
- Combination attacks
"""

import subprocess
import time
import json
import base64
import random
import string
from pathlib import Path
from datetime import datetime
from difflib import SequenceMatcher
import requests

# Check for required libraries
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    import numpy as np
except ImportError:
    print("Installing required packages...")
    subprocess.run(['pip', 'install', 'pillow', 'numpy'], check=True)
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    import numpy as np

MODELS = ["minicpm-v:8b", "llava:7b", "qwen2.5vl:7b", "gemma3n:latest"]
TEST_DIR = Path(__file__).parent
IMAGES_DIR = TEST_DIR / "images"
DEGRADED_DIR = TEST_DIR / "degraded"
RESULTS_FILE = TEST_DIR / "results" / "ocr_stress_results.json"

# Test texts - variety of content types
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
    "handwritten_style": {
        "text": """Meeting Notes
- Call client Tuesday
- Review Q4 budget
- Send proposal by EOD
- Follow up with HR
Phone: 555-0123""",
        "font_size": 26,
        "width": 320,
        "height": 300
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
    "address_label": {
        "text": """SHIP TO:
John Smith
1428 Elm Street, Apt 3B
Springfield, IL 62701
USA

PRIORITY MAIL""",
        "font_size": 24,
        "width": 340,
        "height": 280
    }
}

# Degradation configurations
DEGRADATIONS = {
    "clean": {
        "description": "No degradation (baseline)",
        "params": {}
    },
    "rotate_5": {
        "description": "5° rotation",
        "params": {"rotation": 5}
    },
    "rotate_15": {
        "description": "15° rotation",
        "params": {"rotation": 15}
    },
    "rotate_30": {
        "description": "30° rotation (severe)",
        "params": {"rotation": 30}
    },
    "blur_light": {
        "description": "Light Gaussian blur",
        "params": {"blur": 1.5}
    },
    "blur_heavy": {
        "description": "Heavy Gaussian blur",
        "params": {"blur": 3.0}
    },
    "noise_light": {
        "description": "Light noise (5%)",
        "params": {"noise": 0.05}
    },
    "noise_heavy": {
        "description": "Heavy noise (15%)",
        "params": {"noise": 0.15}
    },
    "dark": {
        "description": "Underexposed (dark)",
        "params": {"brightness": 0.5}
    },
    "bright": {
        "description": "Overexposed (washed out)",
        "params": {"brightness": 1.8}
    },
    "low_contrast": {
        "description": "Low contrast",
        "params": {"contrast": 0.4}
    },
    "jpeg_artifacts": {
        "description": "Heavy JPEG compression",
        "params": {"jpeg_quality": 10}
    },
    "perspective_skew": {
        "description": "Perspective skew (photo angle)",
        "params": {"perspective": True}
    },
    "combo_mild": {
        "description": "Mild combo (5° + light blur + light noise)",
        "params": {"rotation": 5, "blur": 1.0, "noise": 0.03}
    },
    "combo_severe": {
        "description": "Severe combo (15° + blur + noise + dark)",
        "params": {"rotation": 15, "blur": 2.0, "noise": 0.08, "brightness": 0.6}
    },
    "crumpled": {
        "description": "Simulated crumple/fold lines",
        "params": {"crumple": True}
    }
}


def get_font(size=24):
    """Get a monospace font, falling back to default if needed."""
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeMono.ttf",
        "/usr/share/fonts/TTF/DejaVuSansMono.ttf",
    ]

    for path in font_paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)

    # Fallback to default
    return ImageFont.load_default()


def create_text_image(text, width=400, height=300, font_size=24, bg_color="white", text_color="black"):
    """Create a clean image with the specified text."""
    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    font = get_font(font_size)

    # Draw text with padding
    padding = 20
    draw.multiline_text((padding, padding), text, font=font, fill=text_color)

    return img


def apply_rotation(img, degrees):
    """Rotate image by specified degrees."""
    return img.rotate(degrees, expand=True, fillcolor='white')


def apply_blur(img, radius):
    """Apply Gaussian blur."""
    return img.filter(ImageFilter.GaussianBlur(radius=radius))


def apply_noise(img, intensity):
    """Add salt and pepper noise."""
    arr = np.array(img)

    # Salt
    num_salt = int(intensity * arr.size * 0.5)
    coords = [np.random.randint(0, i - 1, num_salt) for i in arr.shape[:2]]
    arr[coords[0], coords[1], :] = 255

    # Pepper
    num_pepper = int(intensity * arr.size * 0.5)
    coords = [np.random.randint(0, i - 1, num_pepper) for i in arr.shape[:2]]
    arr[coords[0], coords[1], :] = 0

    return Image.fromarray(arr)


def apply_brightness(img, factor):
    """Adjust brightness (1.0 = original, <1 = darker, >1 = brighter)."""
    enhancer = ImageEnhance.Brightness(img)
    return enhancer.enhance(factor)


def apply_contrast(img, factor):
    """Adjust contrast (1.0 = original, <1 = less contrast)."""
    enhancer = ImageEnhance.Contrast(img)
    return enhancer.enhance(factor)


def apply_jpeg_artifacts(img, quality):
    """Save and reload with JPEG compression to add artifacts."""
    from io import BytesIO
    buffer = BytesIO()
    img.save(buffer, format='JPEG', quality=quality)
    buffer.seek(0)
    return Image.open(buffer).convert('RGB')


def apply_perspective(img):
    """Apply perspective transformation to simulate photo angle."""
    width, height = img.size

    # Define perspective coefficients for a slight skew
    # Top gets narrower, bottom stays same (like looking down at paper)
    coeffs = [
        1.1, 0.1, -width * 0.05,
        0.05, 1.1, -height * 0.05,
        0.0002, 0.0001
    ]

    return img.transform((width, height), Image.PERSPECTIVE, coeffs, Image.BICUBIC, fillcolor='white')


def apply_crumple(img):
    """Simulate crumple/fold lines by adding dark lines."""
    draw = ImageDraw.Draw(img)
    width, height = img.size

    # Add some random fold lines
    for _ in range(3):
        x1 = random.randint(0, width)
        y1 = random.randint(0, height)
        x2 = random.randint(0, width)
        y2 = random.randint(0, height)
        # Draw a semi-transparent gray line
        draw.line([(x1, y1), (x2, y2)], fill=(180, 180, 180), width=2)

    # Add some small wrinkle shadows
    for _ in range(5):
        x = random.randint(0, width - 20)
        y = random.randint(0, height - 20)
        draw.ellipse([x, y, x + random.randint(5, 15), y + random.randint(5, 15)],
                     fill=(220, 220, 220))

    return img


def apply_degradations(img, params):
    """Apply all specified degradations to an image."""
    result = img.copy()

    if 'rotation' in params:
        result = apply_rotation(result, params['rotation'])

    if 'blur' in params:
        result = apply_blur(result, params['blur'])

    if 'noise' in params:
        result = apply_noise(result, params['noise'])

    if 'brightness' in params:
        result = apply_brightness(result, params['brightness'])

    if 'contrast' in params:
        result = apply_contrast(result, params['contrast'])

    if 'jpeg_quality' in params:
        result = apply_jpeg_artifacts(result, params['jpeg_quality'])

    if params.get('perspective'):
        result = apply_perspective(result)

    if params.get('crumple'):
        result = apply_crumple(result)

    return result


def encode_image_base64(image_path):
    """Encode image to base64."""
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')


def run_ocr_request(model, image_path):
    """Run OCR request and return the extracted text."""
    img_base64 = encode_image_base64(image_path)

    payload = {
        "model": model,
        "prompt": "Read and transcribe ALL text in this image exactly as written. Include every word, number, and symbol. Output only the transcribed text, nothing else.",
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
                'text': data.get('response', ''),
                'time': end_time - start_time
            }
        else:
            return {
                'success': False,
                'error': f'HTTP {response.status_code}',
                'time': end_time - start_time
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'time': time.perf_counter() - start_time
        }


def calculate_accuracy(original, extracted):
    """Calculate various accuracy metrics between original and extracted text."""
    # Normalize texts
    orig_clean = ' '.join(original.lower().split())
    ext_clean = ' '.join(extracted.lower().split())

    # Sequence similarity (0-1)
    sequence_ratio = SequenceMatcher(None, orig_clean, ext_clean).ratio()

    # Word-level accuracy
    orig_words = set(orig_clean.split())
    ext_words = set(ext_clean.split())

    if orig_words:
        word_recall = len(orig_words & ext_words) / len(orig_words)
    else:
        word_recall = 0

    # Character-level accuracy (excluding whitespace differences)
    orig_chars = orig_clean.replace(' ', '')
    ext_chars = ext_clean.replace(' ', '')
    char_ratio = SequenceMatcher(None, orig_chars, ext_chars).ratio()

    # Key data extraction (numbers, special strings)
    import re
    orig_numbers = set(re.findall(r'\$?\d+\.?\d*', original))
    ext_numbers = set(re.findall(r'\$?\d+\.?\d*', extracted))

    if orig_numbers:
        number_accuracy = len(orig_numbers & ext_numbers) / len(orig_numbers)
    else:
        number_accuracy = 1.0  # No numbers to match

    return {
        'sequence_similarity': sequence_ratio,
        'word_recall': word_recall,
        'char_similarity': char_ratio,
        'number_accuracy': number_accuracy,
        'combined_score': (sequence_ratio + word_recall + char_ratio + number_accuracy) / 4
    }


def main():
    print("=" * 70)
    print("RheaRouter OCR Stress Test - Adversarial Text Recognition")
    print("=" * 70)
    print(f"Started: {datetime.now().isoformat()}")
    print()

    # Create directories
    IMAGES_DIR.mkdir(exist_ok=True)
    DEGRADED_DIR.mkdir(exist_ok=True)
    (TEST_DIR / "results").mkdir(exist_ok=True)

    # Generate clean images
    print("Generating test images with known text...")
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

    print()

    # Generate degraded versions
    print("Applying degradations...")
    degraded_images = {}

    for text_name, clean_data in clean_images.items():
        degraded_images[text_name] = {}

        for deg_name, deg_config in DEGRADATIONS.items():
            degraded = apply_degradations(clean_data['image'], deg_config['params'])
            path = DEGRADED_DIR / f"{text_name}_{deg_name}.png"
            degraded.save(path)
            degraded_images[text_name][deg_name] = {
                'path': path,
                'description': deg_config['description'],
                'original_text': clean_data['original_text']
            }

    total_images = len(TEST_TEXTS) * len(DEGRADATIONS)
    print(f"  Generated {total_images} degraded images")
    print()

    # Run OCR tests
    all_results = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'num_texts': len(TEST_TEXTS),
            'num_degradations': len(DEGRADATIONS),
            'total_tests': total_images * len(MODELS),
            'models': MODELS
        },
        'test_texts': {k: v['text'] for k, v in TEST_TEXTS.items()},
        'degradations': {k: v['description'] for k, v in DEGRADATIONS.items()},
        'results': {}
    }

    for model in MODELS:
        print(f"\n{'='*70}")
        print(f"MODEL: {model}")
        print(f"{'='*70}")

        # Warmup
        print("  Warming up...")
        first_img = list(degraded_images.values())[0]['clean']['path']
        run_ocr_request(model, first_img)
        time.sleep(2)

        model_results = {}

        for text_name, deg_variants in degraded_images.items():
            print(f"\n  Text: {text_name}")
            model_results[text_name] = {}

            for deg_name, deg_data in deg_variants.items():
                result = run_ocr_request(model, deg_data['path'])

                if result['success']:
                    accuracy = calculate_accuracy(
                        deg_data['original_text'],
                        result['text']
                    )

                    model_results[text_name][deg_name] = {
                        'success': True,
                        'extracted_text': result['text'],
                        'time': result['time'],
                        'accuracy': accuracy
                    }

                    score = accuracy['combined_score']
                    status = f"{score:.0%}"

                    # Color coding in terminal
                    if score >= 0.8:
                        indicator = "✓"
                    elif score >= 0.5:
                        indicator = "~"
                    else:
                        indicator = "✗"

                    print(f"    {deg_name:20s}: {status:>5s} {indicator} ({result['time']:.2f}s)")
                else:
                    model_results[text_name][deg_name] = {
                        'success': False,
                        'error': result.get('error', 'Unknown'),
                        'time': result.get('time', 0)
                    }
                    print(f"    {deg_name:20s}: FAIL - {result.get('error', '')[:30]}")

        all_results['results'][model] = model_results

    # Save results
    with open(RESULTS_FILE, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to: {RESULTS_FILE}")

    # Generate summary
    print("\n" + "=" * 70)
    print("OCR STRESS TEST SUMMARY")
    print("=" * 70)

    for model in MODELS:
        print(f"\n{model}:")
        model_data = all_results['results'][model]

        # Aggregate by degradation type
        deg_scores = {deg: [] for deg in DEGRADATIONS.keys()}

        for text_name, text_results in model_data.items():
            for deg_name, deg_result in text_results.items():
                if deg_result['success']:
                    deg_scores[deg_name].append(deg_result['accuracy']['combined_score'])

        print(f"\n  By Degradation Type:")
        for deg_name, scores in deg_scores.items():
            if scores:
                avg = sum(scores) / len(scores)
                desc = DEGRADATIONS[deg_name]['description']
                bar = "█" * int(avg * 20) + "░" * (20 - int(avg * 20))
                print(f"    {desc:35s} {bar} {avg:.0%}")

    # Head-to-head comparison
    print("\n" + "-" * 40)
    print("MODEL COMPARISON BY DEGRADATION:")
    print("-" * 40)

    for deg_name in DEGRADATIONS.keys():
        scores = {}
        for model in MODELS:
            model_scores = []
            for text_results in all_results['results'][model].values():
                if deg_name in text_results and text_results[deg_name]['success']:
                    model_scores.append(text_results[deg_name]['accuracy']['combined_score'])
            if model_scores:
                scores[model] = sum(model_scores) / len(model_scores)

        if len(scores) == 2:
            m1, m2 = MODELS
            s1, s2 = scores.get(m1, 0), scores.get(m2, 0)
            diff = s1 - s2
            winner = "MiniCPM" if diff > 0.02 else ("LLaVA" if diff < -0.02 else "TIE")
            desc = DEGRADATIONS[deg_name]['description']
            print(f"  {desc:35s}: MiniCPM {s1:.0%} vs LLaVA {s2:.0%} [{winner}]")

    print("\n" + "=" * 70)
    print("OCR STRESS TEST COMPLETE")
    print("=" * 70)

    return all_results


if __name__ == "__main__":
    main()
