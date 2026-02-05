"""Tests for Ollama adapter"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from src.backend.ollama_adapter import OllamaAdapter
from src.backend.models import OllamaError, OllamaGenerateResponse


@pytest.fixture
def mock_client():
    """Create a mock httpx.AsyncClient"""
    client = AsyncMock()
    client.get = AsyncMock()
    client.request = AsyncMock()
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def adapter(mock_client):
    """Create OllamaAdapter with mocked client"""
    with patch('src.backend.ollama_adapter.httpx.AsyncClient', return_value=mock_client):
        adapter = OllamaAdapter(base_url="http://localhost:11434", timeout=30)
        yield adapter


@pytest.mark.asyncio
async def test_health_check_success(adapter, mock_client):
    """Test successful health check"""
    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_client.get.return_value = mock_response

    result = await adapter.health_check()

    assert result is True
    mock_client.get.assert_called_once_with("/api/tags", timeout=5.0)


@pytest.mark.asyncio
async def test_health_check_failure(adapter, mock_client):
    """Test health check when Ollama is down"""
    # Mock connection error
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")

    result = await adapter.health_check()

    assert result is False


@pytest.mark.asyncio
async def test_list_models_success(adapter, mock_client):
    """Test listing available models"""
    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "models": [
            {"name": "llama3.1:8b"},
            {"name": "minicpm-v:8b"},
            {"name": "qwen2.5:7b"}
        ]
    }
    mock_client.get.return_value = mock_response
    mock_response.raise_for_status = MagicMock()

    models = await adapter.list_models()

    assert len(models) == 3
    assert "llama3.1:8b" in models
    assert "minicpm-v:8b" in models
    assert "qwen2.5:7b" in models


@pytest.mark.asyncio
async def test_validate_model_exists(adapter, mock_client):
    """Test model validation when model exists"""
    # Setup model cache
    adapter._model_cache = ["llama3.1:8b", "qwen2.5:7b"]

    result = await adapter.validate_model("llama3.1:8b")

    assert result is True


@pytest.mark.asyncio
async def test_validate_model_not_exists(adapter, mock_client):
    """Test model validation when model doesn't exist"""
    # Setup model cache
    adapter._model_cache = ["llama3.1:8b", "qwen2.5:7b"]

    result = await adapter.validate_model("nonexistent:7b")

    assert result is False


@pytest.mark.asyncio
async def test_generate_success(adapter, mock_client):
    """Test successful generation request"""
    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "model": "llama3.1:8b",
        "created_at": "2026-02-04T00:00:00Z",
        "response": "Hello! How can I help you?",
        "done": True
    }
    mock_client.request.return_value = mock_response
    mock_response.raise_for_status = MagicMock()

    result = await adapter.generate(
        model="llama3.1:8b",
        prompt="Hello"
    )

    assert isinstance(result, OllamaGenerateResponse)
    assert result.model == "llama3.1:8b"
    assert result.response == "Hello! How can I help you?"
    assert result.done is True


@pytest.mark.asyncio
async def test_generate_with_images(adapter, mock_client):
    """Test generation with images"""
    # Mock successful response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "model": "minicpm-v:8b",
        "created_at": "2026-02-04T00:00:00Z",
        "response": "This image shows a cat.",
        "done": True
    }
    mock_client.request.return_value = mock_response
    mock_response.raise_for_status = MagicMock()

    result = await adapter.generate(
        model="minicpm-v:8b",
        prompt="What's in this image?",
        images=["/9j/4AAQSkZJRg=="]
    )

    assert isinstance(result, OllamaGenerateResponse)
    assert result.response == "This image shows a cat."

    # Verify images were included in request
    call_kwargs = mock_client.request.call_args[1]
    assert "images" in call_kwargs["json"]
    assert call_kwargs["json"]["images"] == ["/9j/4AAQSkZJRg=="]


@pytest.mark.asyncio
async def test_generate_timeout(adapter, mock_client):
    """Test generation timeout error"""
    # Mock timeout exception
    mock_client.request.side_effect = httpx.TimeoutException("Request timeout")

    with pytest.raises(OllamaError) as exc_info:
        await adapter.generate(
            model="llama3.1:8b",
            prompt="Hello"
        )

    assert exc_info.value.status_code == 504
    assert exc_info.value.error_code == "timeout"


@pytest.mark.asyncio
async def test_generate_model_not_found(adapter, mock_client):
    """Test generation with non-existent model"""
    # Mock 404 response
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.text = "Model not found"
    mock_client.request.return_value = mock_response
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404", request=MagicMock(), response=mock_response
    )

    with pytest.raises(OllamaError) as exc_info:
        await adapter.generate(
            model="nonexistent:7b",
            prompt="Hello"
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.error_code == "model_not_found"
    assert "nonexistent:7b" in exc_info.value.error


@pytest.mark.asyncio
async def test_retry_on_503(adapter, mock_client):
    """Test retry logic on 503 error"""
    # First two attempts return 503, third succeeds
    mock_response_503 = MagicMock()
    mock_response_503.status_code = 503

    mock_response_200 = MagicMock()
    mock_response_200.status_code = 200
    mock_response_200.json.return_value = {
        "model": "llama3.1:8b",
        "created_at": "2026-02-04T00:00:00Z",
        "response": "Success after retry",
        "done": True
    }
    mock_response_200.raise_for_status = MagicMock()

    mock_client.request.side_effect = [
        mock_response_503,
        mock_response_503,
        mock_response_200
    ]

    # Should succeed after retries
    result = await adapter.generate(
        model="llama3.1:8b",
        prompt="Hello"
    )

    assert result.response == "Success after retry"
    # Verify it retried 3 times total
    assert mock_client.request.call_count == 3


@pytest.mark.asyncio
async def test_retry_exhausted(adapter, mock_client):
    """Test when all retries are exhausted"""
    # All attempts fail with connection error
    mock_client.request.side_effect = httpx.ConnectError("Connection refused")

    with pytest.raises(httpx.ConnectError):
        await adapter.generate(
            model="llama3.1:8b",
            prompt="Hello"
        )

    # Verify it attempted MAX_RETRIES times
    assert mock_client.request.call_count == adapter.MAX_RETRIES


@pytest.mark.asyncio
async def test_context_manager(mock_client):
    """Test using adapter as async context manager"""
    with patch('src.backend.ollama_adapter.httpx.AsyncClient', return_value=mock_client):
        async with OllamaAdapter("http://localhost:11434", 30) as adapter:
            assert adapter is not None

    # Verify close was called
    mock_client.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_close(adapter, mock_client):
    """Test explicit close"""
    await adapter.close()

    mock_client.aclose.assert_called_once()
