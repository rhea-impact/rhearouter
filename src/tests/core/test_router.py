"""Tests for intelligent model router"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.core.router import ModelRouter, RequestType, get_router
from src.backend.models import ChatMessage


@pytest.fixture
def mock_ollama_adapter():
    """Mock OllamaAdapter"""
    adapter = AsyncMock()
    adapter.list_models = AsyncMock(return_value=[
        {"name": "llama3.1:8b"},
        {"name": "minicpm-v:8b"},
        {"name": "deepseek-r1:8b"},
        {"name": "qwen2.5:7b"},
        {"name": "llava:7b"}
    ])
    adapter.validate_model = AsyncMock(return_value=True)
    return adapter


@pytest.fixture
def router(mock_ollama_adapter):
    """Create router with mocked adapter"""
    router = ModelRouter(mock_ollama_adapter)
    # Clear singleton for clean tests
    import src.core.router
    src.core.router._router_instance = None
    return router


class TestRequestClassification:
    """Test request type classification"""

    def test_classify_vision_request(self, router):
        """Should classify requests with images as VISION"""
        messages = [
            ChatMessage(role="user", content="What's in this image?")
        ]
        request_type = router._classify_request(messages, has_images=True)
        assert request_type == RequestType.VISION

    def test_classify_reasoning_request(self, router):
        """Should classify reasoning tasks"""
        messages = [
            ChatMessage(role="user", content="Explain why water boils at 100°C. Show your reasoning step by step.")
        ]
        request_type = router._classify_request(messages, has_images=False)
        assert request_type == RequestType.REASONING

    def test_classify_coding_request(self, router):
        """Should classify coding tasks"""
        messages = [
            ChatMessage(role="user", content="Write a Python function to sort a list")
        ]
        request_type = router._classify_request(messages, has_images=False)
        assert request_type == RequestType.CODING

    def test_classify_math_request(self, router):
        """Should classify math tasks"""
        messages = [
            ChatMessage(role="user", content="Solve the equation: x^2 + 5x + 6 = 0")
        ]
        request_type = router._classify_request(messages, has_images=False)
        assert request_type == RequestType.MATH

    def test_classify_general_request(self, router):
        """Should classify general requests"""
        messages = [
            ChatMessage(role="user", content="What is the weather like today?")
        ]
        request_type = router._classify_request(messages, has_images=False)
        assert request_type == RequestType.GENERAL

    def test_classify_with_code_patterns(self, router):
        """Should detect code patterns"""
        messages = [
            ChatMessage(role="user", content="What does this do: def factorial(n): return 1 if n == 0 else n * factorial(n-1)")
        ]
        request_type = router._classify_request(messages, has_images=False)
        assert request_type == RequestType.CODING

    def test_classify_with_math_symbols(self, router):
        """Should detect math symbols"""
        messages = [
            ChatMessage(role="user", content="What is ∫ x² dx?")
        ]
        request_type = router._classify_request(messages, has_images=False)
        assert request_type == RequestType.MATH


class TestModelSelection:
    """Test model selection logic"""

    @pytest.mark.asyncio
    async def test_select_user_specified_model(self, router):
        """Should use user-specified model if available"""
        messages = [ChatMessage(role="user", content="Hello")]

        model, request_type = await router.select_model(
            messages=messages,
            requested_model="llama3.1:8b",
            has_images=False
        )

        assert model == "llama3.1:8b"
        assert request_type == RequestType.GENERAL

    @pytest.mark.asyncio
    async def test_select_vision_model(self, router):
        """Should select vision model for images"""
        messages = [ChatMessage(role="user", content="Describe this image")]

        model, request_type = await router.select_model(
            messages=messages,
            requested_model=None,
            has_images=True
        )

        assert model == "minicpm-v:8b"
        assert request_type == RequestType.VISION

    @pytest.mark.asyncio
    async def test_select_reasoning_model(self, router):
        """Should select reasoning model for reasoning tasks"""
        messages = [ChatMessage(role="user", content="Explain why the sky is blue, step by step")]

        model, request_type = await router.select_model(
            messages=messages,
            requested_model=None,
            has_images=False
        )

        assert model == "deepseek-r1:8b"
        assert request_type == RequestType.REASONING

    @pytest.mark.asyncio
    async def test_select_coding_model(self, router):
        """Should select coding model for code tasks"""
        messages = [ChatMessage(role="user", content="Debug this Python function: def add(a, b): return a - b")]

        model, request_type = await router.select_model(
            messages=messages,
            requested_model=None,
            has_images=False
        )

        assert model == "llama3.1:8b"
        assert request_type == RequestType.CODING

    @pytest.mark.asyncio
    async def test_select_math_model(self, router):
        """Should select math model for math tasks"""
        messages = [ChatMessage(role="user", content="Calculate the derivative of x^3 + 2x")]

        model, request_type = await router.select_model(
            messages=messages,
            requested_model=None,
            has_images=False
        )

        assert model == "qwen2.5:7b"
        assert request_type == RequestType.MATH

    @pytest.mark.asyncio
    async def test_select_general_model(self, router):
        """Should select general model for general tasks"""
        messages = [ChatMessage(role="user", content="Tell me a joke")]

        model, request_type = await router.select_model(
            messages=messages,
            requested_model=None,
            has_images=False
        )

        assert model == "llama3.1:8b"
        assert request_type == RequestType.GENERAL


class TestFallbackBehavior:
    """Test fallback cascade"""

    @pytest.mark.asyncio
    async def test_fallback_to_backup_model(self, router):
        """Should fallback to backup if primary unavailable"""
        # Mock primary model unavailable
        router.ollama_adapter.list_models = AsyncMock(return_value=[
            {"name": "llava:7b"},  # Only backup vision model
            {"name": "llama3.1:8b"}
        ])
        router.clear_cache()  # Clear cache to force re-fetch

        messages = [ChatMessage(role="user", content="What's in this?")]

        model, request_type = await router.select_model(
            messages=messages,
            requested_model=None,
            has_images=True
        )

        # Should fallback to llava:7b (backup vision model)
        assert model == "llava:7b"
        assert request_type == RequestType.VISION

    @pytest.mark.asyncio
    async def test_error_when_no_models_available(self, router):
        """Should raise error if no models available"""
        # Mock no models available
        router.ollama_adapter.list_models = AsyncMock(return_value=[])
        router.clear_cache()

        messages = [ChatMessage(role="user", content="Hello")]

        with pytest.raises(RuntimeError, match="No models available"):
            await router.select_model(
                messages=messages,
                requested_model=None,
                has_images=False
            )

    @pytest.mark.asyncio
    async def test_error_when_requested_model_unavailable(self, router):
        """Should raise ValueError for unavailable requested model"""
        router.ollama_adapter.list_models = AsyncMock(return_value=[
            {"name": "llama3.1:8b"}
        ])
        router.clear_cache()

        messages = [ChatMessage(role="user", content="Hello")]

        with pytest.raises(ValueError, match="not available"):
            await router.select_model(
                messages=messages,
                requested_model="nonexistent:model",
                has_images=False
            )


class TestMultimodalContent:
    """Test multimodal content handling"""

    def test_extract_text_from_string_content(self, router):
        """Should extract text from string content"""
        message = ChatMessage(role="user", content="Hello world")
        text = router._extract_text(message)
        assert text == "Hello world"

    def test_extract_text_from_multimodal_content(self, router):
        """Should extract text from multimodal content"""
        message = ChatMessage(
            role="user",
            content=[
                {"type": "text", "text": "What's in"},
                {"type": "text", "text": "this image?"},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
            ]
        )
        text = router._extract_text(message)
        assert text == "What's in this image?"


class TestCaching:
    """Test model availability caching"""

    @pytest.mark.asyncio
    async def test_caches_available_models(self, router):
        """Should cache available models"""
        messages = [ChatMessage(role="user", content="Hello")]

        # First call
        await router.select_model(messages, None, False)
        assert router.ollama_adapter.list_models.call_count == 1

        # Second call - should use cache
        await router.select_model(messages, None, False)
        assert router.ollama_adapter.list_models.call_count == 1  # Not called again

    @pytest.mark.asyncio
    async def test_clear_cache(self, router):
        """Should clear cache on demand"""
        messages = [ChatMessage(role="user", content="Hello")]

        # Populate cache
        await router.select_model(messages, None, False)
        assert router._available_models_cache is not None

        # Clear cache
        router.clear_cache()
        assert router._available_models_cache is None

        # Next call should fetch again
        await router.select_model(messages, None, False)
        assert router.ollama_adapter.list_models.call_count == 2


class TestSingletonPattern:
    """Test singleton router instance"""

    def test_get_router_returns_singleton(self, mock_ollama_adapter):
        """Should return same instance"""
        # Clear singleton
        import src.core.router
        src.core.router._router_instance = None

        router1 = get_router(mock_ollama_adapter)
        router2 = get_router(mock_ollama_adapter)

        assert router1 is router2

    def test_get_router_sets_adapter(self, mock_ollama_adapter):
        """Should set adapter on first call"""
        import src.core.router
        src.core.router._router_instance = None

        router = get_router(mock_ollama_adapter)
        assert router.ollama_adapter is mock_ollama_adapter
