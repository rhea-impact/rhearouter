"""Tests for message_utils module"""

import pytest
from src.backend.models import ChatMessage
from src.backend.message_utils import (
    convert_messages_to_prompt,
    extract_images_from_messages,
    estimate_tokens,
    build_ollama_options,
)


def test_convert_messages_simple():
    """Test simple message conversion"""
    messages = [
        ChatMessage(role="user", content="Hello")
    ]

    prompt = convert_messages_to_prompt(messages)

    assert "User: Hello" in prompt


def test_convert_messages_with_system():
    """Test message conversion with system message"""
    messages = [
        ChatMessage(role="system", content="You are helpful"),
        ChatMessage(role="user", content="Hello"),
        ChatMessage(role="assistant", content="Hi there!"),
        ChatMessage(role="user", content="How are you?")
    ]

    prompt = convert_messages_to_prompt(messages)

    assert "System: You are helpful" in prompt
    assert "User: Hello" in prompt
    assert "Assistant: Hi there!" in prompt
    assert "User: How are you?" in prompt


def test_extract_images_no_images():
    """Test extracting images when there are none"""
    messages = [
        ChatMessage(role="user", content="Hello")
    ]

    images, total_size = extract_images_from_messages(messages)

    assert images == []
    assert total_size == 0


def test_extract_images_with_image():
    """Test extracting images from multimodal content"""
    messages = [
        ChatMessage(
            role="user",
            content=[
                {"type": "text", "text": "What's in this image?"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": "data:image/jpeg;base64,/9j/4AAQSkZJRg=="
                    }
                }
            ]
        )
    ]

    images, total_size = extract_images_from_messages(messages)

    assert len(images) == 1
    assert images[0] == "/9j/4AAQSkZJRg=="
    assert total_size > 0


def test_estimate_tokens():
    """Test token estimation"""
    # 4 characters per token heuristic
    text = "Hello world this is a test"  # 26 chars = ~6 tokens

    tokens = estimate_tokens(text)

    assert tokens == 6


def test_build_ollama_options():
    """Test building Ollama options from OpenAI params"""
    options = build_ollama_options(
        temperature=0.8,
        top_p=0.9,
        max_tokens=1024
    )

    assert options["temperature"] == 0.8
    assert options["top_p"] == 0.9
    assert options["num_predict"] == 1024  # Note: Ollama uses num_predict


def test_build_ollama_options_empty():
    """Test building Ollama options with no params"""
    options = build_ollama_options()

    assert options == {}
