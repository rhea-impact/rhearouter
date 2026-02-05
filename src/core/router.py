"""
Intelligent Model Router

Handles model selection based on request characteristics:
- Vision vs text detection
- Reasoning task detection
- Fallback cascade (primary → backup → error)
- Model availability checking
"""

import re
from typing import Optional, List, Tuple
from enum import Enum

from src.core.config import get_settings
from src.backend.models import ChatMessage
from src.observability.logging import get_logger

logger = get_logger(__name__)


class RequestType(Enum):
    """Request type classification."""
    VISION = "vision"
    REASONING = "reasoning"
    CODING = "coding"
    MATH = "math"
    GENERAL = "general"


class ModelRouter:
    """
    Intelligent model router with fallback strategies.

    Routes requests to appropriate models based on:
    - Presence of images (vision models)
    - Keywords indicating reasoning tasks
    - Keywords indicating coding tasks
    - Keywords indicating math tasks
    - General fallback
    """

    # Keywords for request type detection
    REASONING_KEYWORDS = [
        "explain", "why", "how", "reason", "logic", "proof", "solve",
        "analyze", "deduce", "infer", "conclude", "therefore", "because",
        "step by step", "show your work", "think through"
    ]

    CODING_KEYWORDS = [
        "code", "function", "class", "debug", "implement", "algorithm",
        "programming", "python", "javascript", "java", "c++", "rust",
        "bug", "error", "compile", "syntax", "refactor"
    ]

    MATH_KEYWORDS = [
        "calculate", "equation", "formula", "solve", "integral", "derivative",
        "matrix", "vector", "probability", "statistics", "algebra", "geometry",
        "theorem", "proof", "x =", "y =", "f(x)", "√", "∫", "∑"
    ]

    @staticmethod
    def get_model_config():
        """Get model configuration (lazy load to avoid import issues)"""
        settings = get_settings()
        return {
            RequestType.VISION: {
                "primary": settings.default_vision_model,  # minicpm-v:8b
                "backup": "llava:7b"
            },
            RequestType.REASONING: {
                "primary": settings.reasoning_model,  # deepseek-r1:8b
                "backup": settings.default_text_model  # llama3.1:8b
            },
            RequestType.CODING: {
                "primary": settings.default_text_model,  # llama3.1:8b
                "backup": "qwen2.5:7b"
            },
            RequestType.MATH: {
                "primary": "qwen2.5:7b",
                "backup": settings.reasoning_model  # deepseek-r1:8b
            },
            RequestType.GENERAL: {
                "primary": settings.default_text_model,  # llama3.1:8b
                "backup": "qwen2.5:7b"
            }
        }

    def __init__(self, ollama_adapter=None):
        """
        Initialize router.

        Args:
            ollama_adapter: Optional OllamaAdapter for model validation
        """
        self.ollama_adapter = ollama_adapter
        self._available_models_cache = None

    async def select_model(
        self,
        messages: List[ChatMessage],
        requested_model: Optional[str] = None,
        has_images: bool = False
    ) -> Tuple[str, RequestType]:
        """
        Select appropriate model based on request characteristics.

        Args:
            messages: List of chat messages
            requested_model: User-specified model (takes precedence)
            has_images: Whether request contains images

        Returns:
            Tuple of (selected_model, request_type)

        Raises:
            ValueError: If requested model is not available
        """
        # User-specified model takes precedence
        if requested_model:
            if await self._is_model_available(requested_model):
                request_type = RequestType.VISION if has_images else RequestType.GENERAL
                logger.info(
                    "Using user-specified model",
                    extra={
                        "model": requested_model,
                        "request_type": request_type.value
                    }
                )
                return requested_model, request_type
            else:
                raise ValueError(f"Requested model not available: {requested_model}")

        # Detect request type
        request_type = self._classify_request(messages, has_images)

        # Get model configuration for this type
        model_config = self.get_model_config()
        config = model_config[request_type]
        primary_model = config["primary"]
        backup_model = config.get("backup")

        # Try primary model
        if await self._is_model_available(primary_model):
            logger.info(
                "Selected primary model",
                extra={
                    "model": primary_model,
                    "request_type": request_type.value
                }
            )
            return primary_model, request_type

        # Fallback to backup model
        if backup_model and await self._is_model_available(backup_model):
            logger.warning(
                "Primary model unavailable, using backup",
                extra={
                    "primary_model": primary_model,
                    "backup_model": backup_model,
                    "request_type": request_type.value
                }
            )
            return backup_model, request_type

        # No models available
        logger.error(
            "No models available for request type",
            extra={
                "request_type": request_type.value,
                "primary_model": primary_model,
                "backup_model": backup_model
            }
        )
        raise RuntimeError(f"No models available for {request_type.value} requests")

    def _classify_request(
        self,
        messages: List[ChatMessage],
        has_images: bool
    ) -> RequestType:
        """
        Classify request type based on content.

        Args:
            messages: List of chat messages
            has_images: Whether request contains images

        Returns:
            RequestType enum value
        """
        # Vision requests (highest priority)
        if has_images:
            return RequestType.VISION

        # Extract all text content
        all_text = " ".join(self._extract_text(msg) for msg in messages)
        all_text_lower = all_text.lower()

        # Count keyword matches
        reasoning_score = sum(1 for kw in self.REASONING_KEYWORDS if kw in all_text_lower)
        coding_score = sum(1 for kw in self.CODING_KEYWORDS if kw in all_text_lower)
        math_score = sum(1 for kw in self.MATH_KEYWORDS if kw in all_text_lower)

        # Math often contains symbolic notation
        if re.search(r'[x-z]\s*[=+\-*/]|[∫∑√]|\b\d+\s*[+\-*/÷]\s*\d+', all_text):
            math_score += 2

        # Code often contains specific patterns
        if re.search(r'def\s+\w+|function\s+\w+|class\s+\w+|import\s+\w+', all_text):
            coding_score += 2

        # Determine type by highest score
        if coding_score > reasoning_score and coding_score > math_score:
            return RequestType.CODING
        elif math_score > reasoning_score and math_score > coding_score:
            return RequestType.MATH
        elif reasoning_score >= 2:  # Threshold for reasoning
            return RequestType.REASONING
        else:
            return RequestType.GENERAL

    def _extract_text(self, message: ChatMessage) -> str:
        """
        Extract text content from message.

        Args:
            message: ChatMessage object

        Returns:
            Extracted text string
        """
        if isinstance(message.content, str):
            return message.content

        # Multimodal content - extract text parts
        text_parts = []
        for item in message.content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))

        return " ".join(text_parts)

    async def _is_model_available(self, model_name: str) -> bool:
        """
        Check if model is available in Ollama.

        Args:
            model_name: Model name to check

        Returns:
            True if available, False otherwise
        """
        if not self.ollama_adapter:
            # No adapter - assume model is available
            logger.warning("No Ollama adapter configured, assuming model is available")
            return True

        # Cache available models for performance
        if self._available_models_cache is None:
            try:
                self._available_models_cache = await self.ollama_adapter.list_models()
            except Exception as e:
                logger.error(f"Failed to list models: {e}")
                return False

        # Check if model is in list
        model_ids = [m.get("name", "") for m in self._available_models_cache]
        return model_name in model_ids

    def clear_cache(self):
        """Clear the available models cache."""
        self._available_models_cache = None
        logger.debug("Cleared model cache")


# Singleton instance
_router_instance = None


def get_router(ollama_adapter=None) -> ModelRouter:
    """
    Get singleton router instance.

    Args:
        ollama_adapter: Optional OllamaAdapter to set

    Returns:
        ModelRouter instance
    """
    global _router_instance

    if _router_instance is None:
        _router_instance = ModelRouter(ollama_adapter)
    elif ollama_adapter and _router_instance.ollama_adapter is None:
        _router_instance.ollama_adapter = ollama_adapter

    return _router_instance
