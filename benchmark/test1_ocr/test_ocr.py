#!/usr/bin/env python3
"""
RheaRouter Test 1: OCR/Document Reading Test

Tests vision models' ability to read and extract text from:
- Receipts
- Handwritten notes
- Code screenshots
- Documents with mixed text/graphics
"""

import subprocess
import time
import json
import os
import base64
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

MODELS = ["minicpm-v:8b", "llava:7b"]
TEST_DIR = Path(__file__).parent
IMAGES_DIR = TEST_DIR / "images"
RESULTS_DIR = TEST_DIR / "results"

def create_test_images():
    """Generate synthetic test images for OCR testing."""
    IMAGES_DIR.mkdir(exist_ok=True)

    # Try to use a monospace font, fall back to default
    try:
        font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 24)
        font_medium = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 18)
        font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 14)
    except:
        font_large = ImageFont.load_default()
        font_medium = font_large
        font_small = font_large

    images_created = []

    # 1. Simple receipt
    img = Image.new('RGB', (400, 500), 'white')
    draw = ImageDraw.Draw(img)
    receipt_text = """
    ACME GROCERY STORE
    123 Main Street
    -----------------

    Milk 2%      $3.99
    Bread        $2.49
    Eggs (12)    $4.99
    Cheese       $5.49
    Apples       $3.29

    -----------------
    SUBTOTAL    $20.25
    TAX (8%)     $1.62
    -----------------
    TOTAL       $21.87

    THANK YOU!
    """
    draw.text((20, 20), receipt_text, fill='black', font=font_medium)
    img.save(IMAGES_DIR / "01_receipt.png")
    images_created.append(("01_receipt.png", "Receipt with prices", "$21.87"))

    # 2. Code snippet
    img = Image.new('RGB', (600, 400), '#1e1e1e')
    draw = ImageDraw.Draw(img)
    code_text = """def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

# Calculate first 10 numbers
for i in range(10):
    print(f"fib({i}) = {fibonacci(i)}")
"""
    # Syntax highlighting simulation
    draw.text((20, 20), code_text, fill='#9cdcfe', font=font_medium)
    img.save(IMAGES_DIR / "02_code.png")
    images_created.append(("02_code.png", "Python code", "fibonacci"))

    # 3. Handwritten-style note (simulated with italic/rough font)
    img = Image.new('RGB', (500, 300), '#ffffd0')  # Yellow notepad
    draw = ImageDraw.Draw(img)
    note_text = """Meeting Notes - Nov 24

- Call John at 555-1234
- Review Q4 budget report
- Send email to marketing
- Book flight to NYC
- Deadline: Friday 5pm
"""
    draw.text((30, 30), note_text, fill='#333366', font=font_medium)
    img.save(IMAGES_DIR / "03_handwritten.png")
    images_created.append(("03_handwritten.png", "Handwritten note", "555-1234"))

    # 4. Mixed document (text + table)
    img = Image.new('RGB', (600, 450), 'white')
    draw = ImageDraw.Draw(img)

    # Title
    draw.text((20, 20), "QUARTERLY SALES REPORT", fill='black', font=font_large)
    draw.text((20, 50), "Q3 2025", fill='gray', font=font_medium)

    # Draw table
    draw.rectangle([20, 90, 580, 130], outline='black', width=2)
    draw.text((30, 95), "Region", fill='black', font=font_medium)
    draw.text((200, 95), "Sales", fill='black', font=font_medium)
    draw.text((350, 95), "Growth", fill='black', font=font_medium)

    rows = [
        ("North", "$1.2M", "+15%"),
        ("South", "$890K", "+8%"),
        ("East", "$1.5M", "+22%"),
        ("West", "$2.1M", "+31%"),
    ]

    y = 140
    for region, sales, growth in rows:
        draw.rectangle([20, y, 580, y+35], outline='gray')
        draw.text((30, y+5), region, fill='black', font=font_small)
        draw.text((200, y+5), sales, fill='black', font=font_small)
        color = 'green' if '+' in growth else 'red'
        draw.text((350, y+5), growth, fill=color, font=font_small)
        y += 35

    draw.text((20, y+20), "Total Revenue: $5.69M", fill='black', font=font_medium)

    img.save(IMAGES_DIR / "04_document.png")
    images_created.append(("04_document.png", "Sales report table", "$5.69M"))

    # 5. License plate / short text
    img = Image.new('RGB', (300, 150), '#1a5fb4')
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 30, 280, 120], fill='white', outline='black', width=3)
    try:
        plate_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
    except:
        plate_font = font_large
    draw.text((50, 50), "ABC-1234", fill='black', font=plate_font)
    img.save(IMAGES_DIR / "05_plate.png")
    images_created.append(("05_plate.png", "License plate", "ABC-1234"))

    return images_created

def encode_image_base64(image_path):
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def run_ocr_test(model, image_path, prompt):
    """Run OCR test and return results."""
    import requests

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
                'response': data.get('response', ''),
                'total_time': end_time - start_time,
                'eval_count': data.get('eval_count', 0),
            }
        else:
            return {
                'success': False,
                'response': f'HTTP {response.status_code}',
                'total_time': end_time - start_time,
            }
    except Exception as e:
        return {
            'success': False,
            'response': str(e),
            'total_time': time.perf_counter() - start_time,
        }

def score_ocr_accuracy(response, expected_text):
    """Score OCR accuracy based on whether key text was found."""
    response_lower = response.lower()
    expected_lower = expected_text.lower()

    # Check if the expected text appears in response
    if expected_lower in response_lower:
        return 1.0

    # Partial matching - check individual words/numbers
    expected_parts = expected_lower.replace('-', ' ').replace('$', '').split()
    found = sum(1 for part in expected_parts if part in response_lower)
    return found / len(expected_parts) if expected_parts else 0

def main():
    print("=" * 70)
    print("RheaRouter Test 1: OCR/Document Reading")
    print("=" * 70)
    print(f"Started: {datetime.now().isoformat()}")
    print()

    RESULTS_DIR.mkdir(exist_ok=True)

    # Create test images
    print("Creating test images...")
    test_images = create_test_images()
    print(f"Created {len(test_images)} test images")
    print()

    all_results = []
    model_scores = {model: [] for model in MODELS}

    prompt = "Read and extract all text from this image. List every piece of text you can see."

    for model in MODELS:
        print(f"\n{'='*70}")
        print(f"MODEL: {model}")
        print(f"{'='*70}")

        # Warmup
        print("  Warming up...")
        warmup_img = IMAGES_DIR / test_images[0][0]
        run_ocr_test(model, warmup_img, "What is this?")
        print()

        for img_name, description, expected_text in test_images:
            image_path = IMAGES_DIR / img_name
            print(f"  Testing: {img_name} ({description})")
            print(f"    Expected to find: '{expected_text}'")

            result = run_ocr_test(model, image_path, prompt)

            if result['success']:
                accuracy = score_ocr_accuracy(result['response'], expected_text)
                model_scores[model].append(accuracy)

                result['model'] = model
                result['image'] = img_name
                result['description'] = description
                result['expected_text'] = expected_text
                result['accuracy_score'] = accuracy
                result['timestamp'] = datetime.now().isoformat()

                all_results.append(result)

                found = "FOUND" if accuracy == 1.0 else f"PARTIAL ({accuracy:.0%})" if accuracy > 0 else "NOT FOUND"
                print(f"    [{found}] Time: {result['total_time']:.2f}s")
                print(f"    Response preview: {result['response'][:150]}...")
            else:
                print(f"    [FAIL] {result['response'][:100]}")
                model_scores[model].append(0)
            print()

    # Save results
    results_file = RESULTS_DIR / f"ocr_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to: {results_file}")

    # Summary
    print("\n" + "=" * 70)
    print("OCR TEST SUMMARY")
    print("=" * 70)

    for model in MODELS:
        scores = model_scores[model]
        avg_score = sum(scores) / len(scores) if scores else 0
        perfect = sum(1 for s in scores if s == 1.0)

        model_results = [r for r in all_results if r.get('model') == model]
        avg_time = sum(r['total_time'] for r in model_results) / len(model_results) if model_results else 0

        print(f"\n{model}:")
        print(f"  OCR Accuracy: {avg_score:.0%}")
        print(f"  Perfect Reads: {perfect}/{len(scores)}")
        print(f"  Avg Response Time: {avg_time:.2f}s")

    # Determine winner
    print("\n" + "-" * 40)
    scores_minicpm = model_scores["minicpm-v:8b"]
    scores_llava = model_scores["llava:7b"]

    avg_minicpm = sum(scores_minicpm) / len(scores_minicpm) if scores_minicpm else 0
    avg_llava = sum(scores_llava) / len(scores_llava) if scores_llava else 0

    if avg_minicpm > avg_llava:
        print(f"WINNER: minicpm-v:8b ({avg_minicpm:.0%} vs {avg_llava:.0%})")
    elif avg_llava > avg_minicpm:
        print(f"WINNER: llava:7b ({avg_llava:.0%} vs {avg_minicpm:.0%})")
    else:
        print(f"TIE: Both scored {avg_minicpm:.0%}")

    print("\n" + "=" * 70)
    print("TEST 1 COMPLETE")
    print("=" * 70)

    return {
        'test_name': 'OCR/Document Reading',
        'models': MODELS,
        'scores': model_scores,
        'winner': 'minicpm-v:8b' if avg_minicpm > avg_llava else 'llava:7b' if avg_llava > avg_minicpm else 'tie'
    }

if __name__ == "__main__":
    import requests
    main()
