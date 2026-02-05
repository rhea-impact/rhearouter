#!/usr/bin/env python3
"""
RheaRouter Python Client Examples

Uses OpenAI Python SDK to interact with RheaRouter.

Installation:
    pip install openai

Usage:
    python3 python-client.py
"""

import os
import sys
from openai import OpenAI

# Configuration
RHEA_URL = os.getenv("RHEA_URL", "http://localhost:8000/v1")
API_KEY = os.getenv("RHEA_API_KEY", "not-needed")

# Initialize client
client = OpenAI(
    base_url=RHEA_URL,
    api_key=API_KEY
)


def print_header(title):
    """Print section header."""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60 + "\n")


def print_response(response):
    """Print formatted response."""
    print(f"Model: {response.model}")
    print(f"Content: {response.choices[0].message.content}")
    print(f"Tokens: {response.usage.total_tokens} "
          f"(prompt: {response.usage.prompt_tokens}, "
          f"completion: {response.usage.completion_tokens})")
    print(f"Request ID: {response.id}")


# ============================================================================
# Example 1: Simple Text Completion
# ============================================================================
def example_simple_completion():
    print_header("Example 1: Simple Text Completion")

    response = client.chat.completions.create(
        model="llama3.1:8b",
        messages=[
            {"role": "user", "content": "What is 2+2?"}
        ]
    )

    print_response(response)


# ============================================================================
# Example 2: Auto Model Selection
# ============================================================================
def example_auto_model():
    print_header("Example 2: Auto Model Selection")

    # Omit model parameter - RheaRouter selects automatically
    response = client.chat.completions.create(
        messages=[
            {"role": "user", "content": "Tell me a joke"}
        ]
    )

    print("Auto-selected model:")
    print_response(response)


# ============================================================================
# Example 3: Multi-Turn Conversation
# ============================================================================
def example_conversation():
    print_header("Example 3: Multi-Turn Conversation")

    messages = [
        {"role": "user", "content": "My name is Alice"},
    ]

    # First turn
    response = client.chat.completions.create(
        model="llama3.1:8b",
        messages=messages
    )
    print("Turn 1:")
    print(f"User: {messages[0]['content']}")
    print(f"Assistant: {response.choices[0].message.content}\n")

    # Add assistant response to history
    messages.append({
        "role": "assistant",
        "content": response.choices[0].message.content
    })

    # Second turn
    messages.append({"role": "user", "content": "What is my name?"})
    response = client.chat.completions.create(
        model="llama3.1:8b",
        messages=messages
    )
    print("Turn 2:")
    print(f"User: {messages[2]['content']}")
    print(f"Assistant: {response.choices[0].message.content}")


# ============================================================================
# Example 4: System Message
# ============================================================================
def example_system_message():
    print_header("Example 4: System Message (Personality)")

    response = client.chat.completions.create(
        model="llama3.1:8b",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that speaks like Shakespeare."},
            {"role": "user", "content": "What is Python?"}
        ]
    )

    print_response(response)


# ============================================================================
# Example 5: Temperature Control
# ============================================================================
def example_temperature():
    print_header("Example 5: Temperature Control")

    prompt = "Write a one-sentence story about a robot"

    # Low temperature (deterministic)
    print("Low temperature (0.1 - Deterministic):")
    response = client.chat.completions.create(
        model="llama3.1:8b",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )
    print(f"  {response.choices[0].message.content}\n")

    # High temperature (creative)
    print("High temperature (1.5 - Creative):")
    response = client.chat.completions.create(
        model="llama3.1:8b",
        messages=[{"role": "user", "content": prompt}],
        temperature=1.5
    )
    print(f"  {response.choices[0].message.content}")


# ============================================================================
# Example 6: Max Tokens Limit
# ============================================================================
def example_max_tokens():
    print_header("Example 6: Max Tokens Limit")

    response = client.chat.completions.create(
        model="llama3.1:8b",
        messages=[
            {"role": "user", "content": "Explain quantum physics in detail"}
        ],
        max_tokens=50
    )

    print(f"Content: {response.choices[0].message.content}")
    print(f"Finish reason: {response.choices[0].finish_reason}")
    print(f"Tokens used: {response.usage.completion_tokens}/50")


# ============================================================================
# Example 7: Token Usage Tracking
# ============================================================================
def example_token_tracking():
    print_header("Example 7: Token Usage Tracking")

    prompts = [
        "Hi",
        "What is the capital of France?",
        "Explain the theory of relativity in simple terms"
    ]

    print(f"{'Prompt':<50} {'Prompt Tokens':>15} {'Completion Tokens':>20}")
    print("-" * 90)

    for prompt in prompts:
        response = client.chat.completions.create(
            model="llama3.1:8b",
            messages=[{"role": "user", "content": prompt}]
        )

        print(f"{prompt:<50} {response.usage.prompt_tokens:>15} "
              f"{response.usage.completion_tokens:>20}")


# ============================================================================
# Example 8: Error Handling
# ============================================================================
def example_error_handling():
    print_header("Example 8: Error Handling")

    # Model not found
    print("Attempting to use non-existent model...")
    try:
        response = client.chat.completions.create(
            model="nonexistent:model",
            messages=[{"role": "user", "content": "Hello"}]
        )
    except Exception as e:
        print(f"Error caught: {type(e).__name__}")
        print(f"Message: {str(e)[:100]}...")


# ============================================================================
# Example 9: List Available Models
# ============================================================================
def example_list_models():
    print_header("Example 9: List Available Models")

    models = client.models.list()

    print(f"{'Model ID':<30} {'Owner':<15}")
    print("-" * 50)
    for model in models.data:
        print(f"{model.id:<30} {model.owned_by:<15}")


# ============================================================================
# Example 10: Reasoning Model
# ============================================================================
def example_reasoning():
    print_header("Example 10: Reasoning Model (DeepSeek R1)")

    # Check if model exists
    models = client.models.list()
    model_ids = [m.id for m in models.data]

    if "deepseek-r1:8b" not in model_ids:
        print("Skipping: deepseek-r1:8b not installed")
        print("Install with: ollama pull deepseek-r1:8b")
        return

    response = client.chat.completions.create(
        model="deepseek-r1:8b",
        messages=[
            {"role": "user", "content": "If x^2 = 16, what is x? Show your reasoning step by step."}
        ],
        temperature=0.1
    )

    print_response(response)


# ============================================================================
# Example 11: Batch Requests
# ============================================================================
def example_batch_requests():
    print_header("Example 11: Batch Requests")

    prompts = [
        "What is 2+2?",
        "What is the capital of France?",
        "What is the speed of light?"
    ]

    print("Sending batch of requests...\n")

    for i, prompt in enumerate(prompts, 1):
        response = client.chat.completions.create(
            model="llama3.1:8b",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=50
        )

        print(f"Request {i}:")
        print(f"  Q: {prompt}")
        print(f"  A: {response.choices[0].message.content}")
        print(f"  Tokens: {response.usage.total_tokens}\n")


# ============================================================================
# Example 12: Rate Limit Handling
# ============================================================================
def example_rate_limiting():
    print_header("Example 12: Rate Limit Handling")

    import time

    print("Sending rapid requests to test rate limiting...\n")

    success_count = 0
    rate_limited_count = 0

    for i in range(10):
        try:
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": f"Count to {i+1}"}],
                max_tokens=20
            )
            success_count += 1
            print(f"Request {i+1}: ✓ Success")
        except Exception as e:
            if "429" in str(e) or "rate limit" in str(e).lower():
                rate_limited_count += 1
                print(f"Request {i+1}: ✗ Rate Limited")
            else:
                print(f"Request {i+1}: ✗ Error: {e}")

        time.sleep(0.1)

    print(f"\nResults: {success_count} successful, {rate_limited_count} rate limited")


# ============================================================================
# Main
# ============================================================================
def main():
    print("\n" + "=" * 60)
    print(" RheaRouter Python Client Examples")
    print("=" * 60)
    print(f"\nConnecting to: {RHEA_URL}")
    print(f"API Key: {'***' if API_KEY != 'not-needed' else 'not-needed'}\n")

    # Check connection
    try:
        models = client.models.list()
        print(f"✓ Connected successfully ({len(models.data)} models available)\n")
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print("\nMake sure RheaRouter is running:")
        print("  uvicorn src.api.main:app --host 0.0.0.0 --port 8000")
        sys.exit(1)

    # Run examples
    try:
        example_simple_completion()
        example_auto_model()
        example_conversation()
        example_system_message()
        example_temperature()
        example_max_tokens()
        example_token_tracking()
        example_error_handling()
        example_list_models()
        example_reasoning()
        example_batch_requests()
        example_rate_limiting()

        print("\n" + "=" * 60)
        print(" All examples completed successfully!")
        print("=" * 60 + "\n")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
