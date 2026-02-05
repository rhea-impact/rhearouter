#!/usr/bin/env python3
"""
RheaRouter Extended Benchmark - 10 New Diverse Images

Tests both models on a wider variety of image types.
Skips stability testing per user request.
"""

import subprocess
import time
import json
import base64
from pathlib import Path
from datetime import datetime
import requests

MODELS = ["minicpm-v:8b", "llava:7b"]
TEST_DIR = Path(__file__).parent
IMAGES_DIR = TEST_DIR / "images"
RESULTS_FILE = TEST_DIR / "extended_results.json"

# Image metadata for scoring
IMAGE_INFO = {
    "01_landscape_sunrise.jpg": {
        "category": "landscape",
        "description": "Sunrise over the sea",
        "expected_keywords": ["sunrise", "sun", "ocean", "sea", "sky", "water", "horizon", "clouds", "orange", "yellow"]
    },
    "02_urban_street.jpg": {
        "category": "urban",
        "description": "City street scene",
        "expected_keywords": ["street", "city", "urban", "building", "road", "car", "people", "sidewalk"]
    },
    "03_food_display.jpg": {
        "category": "food",
        "description": "Food display with fruits and vegetables",
        "expected_keywords": ["food", "fruit", "vegetable", "fresh", "healthy", "display", "colorful", "produce"]
    },
    "04_animals_dogs.jpg": {
        "category": "animals",
        "description": "Collage of different dog breeds",
        "expected_keywords": ["dog", "dogs", "puppy", "breed", "pet", "canine", "collage", "multiple"]
    },
    "05_architecture_paris.jpg": {
        "category": "architecture",
        "description": "Eiffel Tower in Paris",
        "expected_keywords": ["eiffel", "tower", "paris", "france", "landmark", "architecture", "metal", "iron"]
    },
    "06_art_starrynight.jpg": {
        "category": "art",
        "description": "Van Gogh's Starry Night",
        "expected_keywords": ["starry", "night", "van gogh", "painting", "stars", "swirl", "sky", "village", "cypress"]
    },
    "07_wildlife_tiger.jpg": {
        "category": "wildlife",
        "description": "Bengal tiger",
        "expected_keywords": ["tiger", "cat", "stripes", "wild", "predator", "orange", "bengal", "feline"]
    },
    "08_landmark_goldengate.jpg": {
        "category": "landmark",
        "description": "Golden Gate Bridge",
        "expected_keywords": ["golden gate", "bridge", "san francisco", "red", "bay", "suspension", "landmark"]
    },
    "09_space_astronaut.jpg": {
        "category": "space",
        "description": "Astronaut in spacewalk",
        "expected_keywords": ["astronaut", "space", "nasa", "suit", "earth", "floating", "spacewalk", "orbit"]
    },
    "10_art_wave.jpg": {
        "category": "art",
        "description": "The Great Wave off Kanagawa by Hokusai",
        "expected_keywords": ["wave", "japan", "hokusai", "woodblock", "ocean", "mount fuji", "boat", "art"]
    }
}

def get_vram_usage():
    try:
        result = subprocess.run(
            ['nvidia-smi', '--query-gpu=memory.used,temperature.gpu', '--format=csv,noheader,nounits'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            parts = result.stdout.strip().split(', ')
            return int(parts[0]), int(parts[1])
    except:
        pass
    return None, None

def encode_image_base64(image_path):
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def run_vision_request(model, image_path, prompt):
    """Run a vision request and return detailed results."""
    img_base64 = encode_image_base64(image_path)
    vram_before, temp_before = get_vram_usage()

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
        vram_after, temp_after = get_vram_usage()

        if response.status_code == 200:
            data = response.json()
            return {
                'success': True,
                'response': data.get('response', ''),
                'total_time': end_time - start_time,
                'eval_count': data.get('eval_count', 0),
                'eval_duration_ns': data.get('eval_duration', 0),
                'prompt_eval_duration_ns': data.get('prompt_eval_duration', 0),
                'vram_mb': vram_after,
                'temp_c': temp_after,
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

def score_response(response, expected_keywords):
    """Score how many expected keywords were found."""
    response_lower = response.lower()
    found = []
    missing = []

    for kw in expected_keywords:
        if kw.lower() in response_lower:
            found.append(kw)
        else:
            missing.append(kw)

    return {
        'score': len(found) / len(expected_keywords) if expected_keywords else 0,
        'found': found,
        'missing': missing,
        'found_count': len(found),
        'total_keywords': len(expected_keywords)
    }

def main():
    print("=" * 70)
    print("RheaRouter Extended Benchmark - 10 Diverse Images")
    print("=" * 70)
    print(f"Started: {datetime.now().isoformat()}")
    print()

    # Get all images
    images = sorted(IMAGES_DIR.glob("*.jpg"))
    print(f"Found {len(images)} test images:")
    for img in images:
        size_kb = img.stat().st_size / 1024
        info = IMAGE_INFO.get(img.name, {})
        print(f"  {img.name}: {info.get('category', 'unknown')} - {size_kb:.1f} KB")
    print()

    # Test prompts
    prompts = {
        'describe': "Describe this image in detail. What do you see?",
        'identify': "What is the main subject of this image? Identify it specifically.",
        'context': "What is the context or setting of this image? Where might this be?"
    }

    all_results = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'num_images': len(images),
            'models': MODELS,
            'prompts': list(prompts.keys())
        },
        'results': {}
    }

    for model in MODELS:
        print(f"\n{'='*70}")
        print(f"MODEL: {model}")
        print(f"{'='*70}")

        # Warmup
        print("  Warming up...")
        run_vision_request(model, images[0], "What is this?")
        time.sleep(2)

        model_results = []

        for image_path in images:
            image_name = image_path.name
            info = IMAGE_INFO.get(image_name, {})

            print(f"\n  Image: {image_name} ({info.get('category', 'unknown')})")

            image_results = {
                'image': image_name,
                'category': info.get('category', 'unknown'),
                'expected_description': info.get('description', ''),
                'prompts': {}
            }

            for prompt_name, prompt_text in prompts.items():
                result = run_vision_request(model, image_path, prompt_text)

                if result['success']:
                    # Score the response
                    scoring = score_response(result['response'], info.get('expected_keywords', []))

                    tokens_per_sec = 0
                    if result.get('eval_duration_ns', 0) > 0:
                        tokens_per_sec = result['eval_count'] / (result['eval_duration_ns'] / 1e9)

                    prompt_result = {
                        'success': True,
                        'response': result['response'],
                        'time': result['total_time'],
                        'tokens': result['eval_count'],
                        'tokens_per_sec': tokens_per_sec,
                        'vram_mb': result['vram_mb'],
                        'temp_c': result['temp_c'],
                        'word_count': len(result['response'].split()),
                        'score': scoring['score'],
                        'keywords_found': scoring['found_count'],
                        'keywords_total': scoring['total_keywords'],
                        'keywords_missing': scoring['missing']
                    }

                    status = f"{scoring['score']:.0%}"
                else:
                    prompt_result = {
                        'success': False,
                        'error': result.get('error', 'Unknown'),
                        'time': result.get('total_time', 0)
                    }
                    status = "FAIL"

                image_results['prompts'][prompt_name] = prompt_result

                # Print brief status
                if prompt_result['success']:
                    print(f"    {prompt_name}: {prompt_result['time']:.2f}s | "
                          f"{prompt_result['word_count']} words | "
                          f"Score: {status}")
                else:
                    print(f"    {prompt_name}: FAILED - {prompt_result.get('error', '')[:50]}")

            model_results.append(image_results)

        all_results['results'][model] = model_results

    # Save results
    with open(RESULTS_FILE, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to: {RESULTS_FILE}")

    # Generate summary statistics
    print("\n" + "=" * 70)
    print("EXTENDED BENCHMARK SUMMARY")
    print("=" * 70)

    for model in MODELS:
        print(f"\n{model}:")
        model_data = all_results['results'][model]

        # Aggregate stats
        all_times = []
        all_scores = []
        all_words = []
        all_tokens_per_sec = []
        category_scores = {}

        for img_result in model_data:
            category = img_result['category']
            if category not in category_scores:
                category_scores[category] = []

            for prompt_name, prompt_result in img_result['prompts'].items():
                if prompt_result['success']:
                    all_times.append(prompt_result['time'])
                    all_scores.append(prompt_result['score'])
                    all_words.append(prompt_result['word_count'])
                    all_tokens_per_sec.append(prompt_result['tokens_per_sec'])
                    category_scores[category].append(prompt_result['score'])

        if all_times:
            print(f"  Overall Stats:")
            print(f"    Avg Response Time: {sum(all_times)/len(all_times):.2f}s")
            print(f"    Avg Keyword Score: {sum(all_scores)/len(all_scores):.0%}")
            print(f"    Avg Words/Response: {sum(all_words)/len(all_words):.0f}")
            print(f"    Avg Tokens/sec: {sum(all_tokens_per_sec)/len(all_tokens_per_sec):.1f}")

            print(f"\n  By Category:")
            for category, scores in sorted(category_scores.items()):
                avg = sum(scores) / len(scores) if scores else 0
                print(f"    {category}: {avg:.0%} ({len(scores)} tests)")

    # Compare models
    print("\n" + "-" * 40)
    print("MODEL COMPARISON:")

    minicpm_scores = []
    llava_scores = []

    for img_result in all_results['results']['minicpm-v:8b']:
        for p_result in img_result['prompts'].values():
            if p_result['success']:
                minicpm_scores.append(p_result['score'])

    for img_result in all_results['results']['llava:7b']:
        for p_result in img_result['prompts'].values():
            if p_result['success']:
                llava_scores.append(p_result['score'])

    avg_minicpm = sum(minicpm_scores) / len(minicpm_scores) if minicpm_scores else 0
    avg_llava = sum(llava_scores) / len(llava_scores) if llava_scores else 0

    print(f"  MiniCPM-V avg score: {avg_minicpm:.0%}")
    print(f"  LLaVA avg score: {avg_llava:.0%}")

    if avg_minicpm > avg_llava:
        print(f"\n  WINNER: minicpm-v:8b (+{(avg_minicpm-avg_llava)*100:.1f}%)")
    elif avg_llava > avg_minicpm:
        print(f"\n  WINNER: llava:7b (+{(avg_llava-avg_minicpm)*100:.1f}%)")
    else:
        print(f"\n  TIE")

    print("\n" + "=" * 70)
    print("EXTENDED BENCHMARK COMPLETE")
    print("=" * 70)

    return all_results

if __name__ == "__main__":
    main()
