#!/usr/bin/env python3
"""
RheaRouter Test 5: Multi-Turn Vision Conversation Test

Tests models' ability to:
- Remember context from previous turns
- Answer follow-up questions about an image
- Maintain coherent conversation
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

def encode_image_base64(image_path):
    with open(image_path, 'rb') as f:
        return base64.b64encode(f.read()).decode('utf-8')

def run_chat_turn(model, messages, image_base64=None):
    """Run a single chat turn using Ollama chat API."""

    # Build the request for chat endpoint
    payload = {
        "model": model,
        "messages": messages,
        "stream": False
    }

    # Add image to the last user message if provided
    if image_base64 and messages:
        # Find last user message and add image
        for msg in reversed(messages):
            if msg['role'] == 'user':
                msg['images'] = [image_base64]
                break

    start_time = time.perf_counter()

    try:
        response = requests.post(
            'http://localhost:11434/api/chat',
            json=payload,
            timeout=120
        )

        end_time = time.perf_counter()

        if response.status_code == 200:
            data = response.json()
            return {
                'success': True,
                'response': data.get('message', {}).get('content', ''),
                'total_time': end_time - start_time,
                'eval_count': data.get('eval_count', 0),
            }
        else:
            return {
                'success': False,
                'error': f'HTTP {response.status_code}: {response.text[:100]}',
                'total_time': end_time - start_time,
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'total_time': time.perf_counter() - start_time,
        }

# Define test conversations
TEST_CONVERSATIONS = [
    {
        'name': 'Cat Description',
        'image': '04_pet_cat.jpg',
        'turns': [
            "What animal is in this image?",
            "What color is it?",
            "Is it indoors or outdoors?",
            "What is it doing?",
            "Based on what you can see, does it look like a pet or a stray?"
        ],
        'expected_keywords': [
            ['cat', 'feline'],
            ['gray', 'grey', 'white', 'brown', 'tabby'],
            ['outdoor', 'outside', 'garden'],
            ['sitting', 'lying', 'resting', 'relaxing'],
            ['pet', 'domestic', 'well-kept', 'groomed']
        ]
    },
    {
        'name': 'Art Analysis',
        'image': '05_art_monalisa.jpg',
        'turns': [
            "What is this image?",
            "Who painted it?",
            "What expression does the subject have?",
            "Describe the background of the painting.",
            "Why is this painting famous?"
        ],
        'expected_keywords': [
            ['mona lisa', 'painting', 'portrait'],
            ['leonardo', 'da vinci', 'davinci'],
            ['smile', 'mysterious', 'enigmatic', 'serene'],
            ['landscape', 'mountains', 'river', 'nature', 'background'],
            ['famous', 'masterpiece', 'iconic', 'louvre', 'renaissance']
        ]
    },
    {
        'name': 'Object Identification',
        'image': '01_nature_ant.jpg',
        'turns': [
            "What insect do you see?",
            "How many legs does it have?",
            "What surface is it on?",
            "Is this a close-up or a distant shot?",
        ],
        'expected_keywords': [
            ['ant', 'insect'],
            ['six', '6', 'legs'],
            ['concrete', 'pavement', 'stone', 'ground', 'surface'],
            ['close-up', 'close up', 'macro', 'detailed', 'close'],
        ]
    }
]

def score_response(response, expected_keywords):
    """Score response based on expected keywords."""
    response_lower = response.lower()
    for keyword in expected_keywords:
        if keyword.lower() in response_lower:
            return 1.0
    return 0.0

def run_conversation_test(model, conversation, image_path):
    """Run a multi-turn conversation test."""
    img_base64 = encode_image_base64(image_path)

    results = []
    messages = []

    for turn_idx, question in enumerate(conversation['turns']):
        # Add user message
        messages.append({'role': 'user', 'content': question})

        # Only include image on first turn
        include_image = turn_idx == 0

        # Run the turn
        result = run_chat_turn(
            model,
            messages.copy(),
            img_base64 if include_image else None
        )

        if result['success']:
            # Add assistant response to conversation history
            messages.append({'role': 'assistant', 'content': result['response']})

            # Score the response
            expected = conversation['expected_keywords'][turn_idx]
            score = score_response(result['response'], expected)

            results.append({
                'turn': turn_idx + 1,
                'question': question,
                'response': result['response'],
                'expected_keywords': expected,
                'score': score,
                'time': result['total_time'],
                'success': True
            })
        else:
            results.append({
                'turn': turn_idx + 1,
                'question': question,
                'error': result.get('error', 'Unknown error'),
                'score': 0,
                'time': result.get('total_time', 0),
                'success': False
            })
            # Don't continue conversation if a turn fails
            break

    return results

def main():
    print("=" * 70)
    print("RheaRouter Test 5: Multi-Turn Vision Conversation")
    print("=" * 70)
    print(f"Started: {datetime.now().isoformat()}")
    print()

    RESULTS_DIR.mkdir(exist_ok=True)

    all_results = {}

    for model in MODELS:
        print(f"\n{'='*70}")
        print(f"MODEL: {model}")
        print(f"{'='*70}")

        # Warmup
        print("  Warming up...")
        warmup_img = encode_image_base64(IMAGES_DIR / "04_pet_cat.jpg")
        run_chat_turn(model, [{'role': 'user', 'content': 'What is this?', 'images': [warmup_img]}])
        time.sleep(2)

        model_results = []

        for conv in TEST_CONVERSATIONS:
            image_path = IMAGES_DIR / conv['image']
            if not image_path.exists():
                print(f"  [SKIP] Image not found: {conv['image']}")
                continue

            print(f"\n  Conversation: {conv['name']}")
            print(f"  Image: {conv['image']}")

            results = run_conversation_test(model, conv, image_path)

            # Calculate conversation metrics
            successful_turns = [r for r in results if r['success']]
            total_score = sum(r['score'] for r in results)
            avg_score = total_score / len(results) if results else 0
            total_time = sum(r['time'] for r in results)

            conv_result = {
                'conversation_name': conv['name'],
                'image': conv['image'],
                'num_turns': len(conv['turns']),
                'successful_turns': len(successful_turns),
                'total_score': total_score,
                'avg_score': avg_score,
                'total_time': total_time,
                'turns': results
            }

            model_results.append(conv_result)

            # Print turn-by-turn results
            for r in results:
                status = "✓" if r['score'] == 1.0 else "✗" if r['success'] else "!"
                print(f"    Turn {r['turn']}: [{status}] {r['question'][:40]}...")
                if r['success']:
                    print(f"           Response: {r['response'][:60]}...")
                else:
                    print(f"           Error: {r.get('error', 'Unknown')[:60]}")

            print(f"    Score: {total_score}/{len(results)} ({avg_score:.0%}), Time: {total_time:.1f}s")

        all_results[model] = model_results

    # Save results
    results_file = RESULTS_DIR / f"conversation_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    print(f"\nResults saved to: {results_file}")

    # Summary
    print("\n" + "=" * 70)
    print("MULTI-TURN CONVERSATION SUMMARY")
    print("=" * 70)

    for model in MODELS:
        print(f"\n{model}:")

        total_turns = sum(c['num_turns'] for c in all_results[model])
        total_score = sum(c['total_score'] for c in all_results[model])
        avg_accuracy = total_score / total_turns if total_turns > 0 else 0

        print(f"  Overall Accuracy: {avg_accuracy:.0%} ({total_score}/{total_turns} correct)")

        for conv in all_results[model]:
            print(f"    {conv['conversation_name']}: {conv['avg_score']:.0%} ({conv['total_time']:.1f}s)")

    # Determine winner
    print("\n" + "-" * 40)

    score_minicpm = sum(c['total_score'] for c in all_results["minicpm-v:8b"])
    score_llava = sum(c['total_score'] for c in all_results["llava:7b"])
    total_turns = sum(c['num_turns'] for c in all_results["minicpm-v:8b"])

    if score_minicpm > score_llava:
        print(f"WINNER (conversation): minicpm-v:8b ({score_minicpm}/{total_turns} vs {score_llava}/{total_turns})")
    elif score_llava > score_minicpm:
        print(f"WINNER (conversation): llava:7b ({score_llava}/{total_turns} vs {score_minicpm}/{total_turns})")
    else:
        print(f"TIE ({score_minicpm}/{total_turns})")

    print("\n" + "=" * 70)
    print("TEST 5 COMPLETE")
    print("=" * 70)

    return all_results

if __name__ == "__main__":
    main()
