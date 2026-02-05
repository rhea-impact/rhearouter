"""Utilities for converting between OpenAI and Ollama message formats"""

import base64
import re
from typing import List, Tuple, Optional

from src.backend.models import ChatMessage
from src.observability.logging import get_logger

logger = get_logger(__name__)

# Image size limit: 10MB
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024

# Supported image formats
SUPPORTED_FORMATS = {"image/jpeg", "image/png", "image/webp", "image/gif"}


def convert_messages_to_prompt(messages: List[ChatMessage]) -> str:
    """
    Convert OpenAI message format to Ollama prompt string.

    Preserves conversation structure with role markers.
    System messages are placed at the start.

    Args:
        messages: List of chat messages in OpenAI format

    Returns:
        Single prompt string for Ollama
    """
    parts = []

    # Extract system message if present
    system_msgs = [m for m in messages if m.role == "system"]
    other_msgs = [m for m in messages if m.role != "system"]

    # Add system context first
    if system_msgs:
        system_content = "\n".join(
            _extract_text_from_message(m) for m in system_msgs
        )
        parts.append(f"System: {system_content}")

    # Add conversation history
    for msg in other_msgs:
        role = msg.role.capitalize()
        content = _extract_text_from_message(msg)
        parts.append(f"{role}: {content}")

    return "\n\n".join(parts)


def _extract_text_from_message(message: ChatMessage) -> str:
    """
    Extract text content from message, handling multimodal content.

    Args:
        message: Chat message (may contain text and/or images)

    Returns:
        Text content only
    """
    if isinstance(message.content, str):
        return message.content

    # Multimodal content - extract text parts
    text_parts = []
    for item in message.content:
        if isinstance(item, dict):
            if item.get("type") == "text":
                text_parts.append(item.get("text", ""))
        elif hasattr(item, "type") and item.type == "text":
            text_parts.append(item.text)

    return " ".join(text_parts)


def extract_images_from_messages(
    messages: List[ChatMessage]
) -> Tuple[List[str], int]:
    """
    Extract base64 images from OpenAI message format.

    Args:
        messages: List of chat messages

    Returns:
        Tuple of (list of base64 strings, total_size_bytes)

    Raises:
        ValueError: If image format unsupported or size exceeds limit
    """
    images = []
    total_size = 0

    for message in messages:
        if isinstance(message.content, list):
            for item in message.content:
                if isinstance(item, dict) and item.get("type") == "image_url":
                    image_url = item.get("image_url", {}).get("url", "")
                    base64_data = _parse_data_url(image_url)

                    # Validate size
                    image_bytes = len(base64_data)
                    if image_bytes > MAX_IMAGE_SIZE_BYTES:
                        raise ValueError(
                            f"Image exceeds {MAX_IMAGE_SIZE_BYTES} byte limit"
                        )

                    images.append(base64_data)
                    total_size += image_bytes

    logger.debug("Extracted images from messages", extra={
        "image_count": len(images),
        "total_size_bytes": total_size
    })

    return images, total_size


def _parse_data_url(data_url: str) -> str:
    """
    Parse data URL and extract base64 content.

    Expected format: "data:image/jpeg;base64,/9j/4AAQ..."

    Args:
        data_url: Data URL string

    Returns:
        Base64 string (without data URL prefix)

    Raises:
        ValueError: If format is invalid
    """
    if not data_url.startswith("data:"):
        raise ValueError("Image URL must be a data URL")

    # Extract media type and base64 data
    match = re.match(r'data:([^;]+);base64,(.+)', data_url)
    if not match:
        raise ValueError("Invalid data URL format")

    media_type = match.group(1)
    base64_data = match.group(2)

    # Validate media type
    if media_type not in SUPPORTED_FORMATS:
        raise ValueError(
            f"Unsupported image format: {media_type}. "
            f"Supported: {SUPPORTED_FORMATS}"
        )

    return base64_data


def estimate_tokens(text: str) -> int:
    """
    Estimate token count using character-based heuristic.

    Uses 4 characters per token approximation (standard for English).
    This is an estimate; actual tokenization varies by model.

    Args:
        text: Input text

    Returns:
        Estimated token count
    """
    return max(1, len(text) // 4)


def build_ollama_options(
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
    stop: Optional[List[str]] = None,
    max_tokens: Optional[int] = None
) -> dict:
    """
    Build Ollama options dict from OpenAI parameters.

    Args:
        temperature: Sampling temperature
        top_p: Nucleus sampling threshold
        stop: Stop sequences
        max_tokens: Maximum tokens to generate

    Returns:
        Ollama options dictionary
    """
    options = {}

    if temperature is not None:
        options["temperature"] = temperature

    if top_p is not None:
        options["top_p"] = top_p

    if stop:
        options["stop"] = stop

    if max_tokens:
        # Ollama uses num_predict instead of max_tokens
        options["num_predict"] = max_tokens

    return options
