"""Integration tests for chat completions endpoint"""

import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.routes import chat
from src.backend.models import OllamaGenerateResponse
from src.middleware.request_id import RequestIDMiddleware


@pytest.fixture
def mock_adapter():
    """Create mock Ollama adapter"""
    adapter = AsyncMock()

    # Mock health check
    adapter.health_check.return_value = True

    # Mock model validation
    adapter.validate_model.return_value = True

    # Mock list_models (for router)
    adapter.list_models = AsyncMock(return_value=[
        {"name": "llama3.1:8b"},
        {"name": "minicpm-v:8b"},
        {"name": "deepseek-r1:8b"},
        {"name": "qwen2.5:7b"},
        {"name": "llava:7b"}
    ])

    # Mock generate
    adapter.generate.return_value = OllamaGenerateResponse(
        model="llama3.1:8b",
        created_at="2026-02-04T00:00:00Z",
        response="Hello! How can I help you today?",
        done=True
    )

    adapter.close = AsyncMock()

    return adapter


@pytest.fixture
def app():
    """Create test app with minimal middleware"""
    test_app = FastAPI()

    # Only add Request ID middleware for testing
    # (skip rate limiter, VRAM valve, error handler to avoid interference)
    test_app.add_middleware(RequestIDMiddleware)

    # Include chat router
    test_app.include_router(chat.router)

    return test_app


@pytest.fixture
def client(app, mock_adapter):
    """Create test client with mocked adapter"""
    # Set mock adapter
    chat.set_ollama_adapter(mock_adapter)

    return TestClient(app)


def test_text_completion_success(client, mock_adapter):
    """Test successful text completion"""
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "llama3.1:8b",
            "messages": [
                {"role": "user", "content": "Hello"}
            ]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Check OpenAI-compatible structure
    assert "id" in data
    assert data["object"] == "chat.completion"
    assert "created" in data
    assert data["model"] == "llama3.1:8b"
    
    # Check choices
    assert len(data["choices"]) == 1
    choice = data["choices"][0]
    assert choice["index"] == 0
    assert choice["message"]["role"] == "assistant"
    assert choice["message"]["content"] == "Hello! How can I help you today?"
    assert choice["finish_reason"] == "stop"
    
    # Check usage
    assert "usage" in data
    assert data["usage"]["prompt_tokens"] > 0
    assert data["usage"]["completion_tokens"] > 0
    assert data["usage"]["total_tokens"] > 0


def test_text_completion_auto_model_selection(client, mock_adapter):
    """Test auto model selection for text"""
    response = client.post(
        "/v1/chat/completions",
        json={
            # No model specified
            "messages": [
                {"role": "user", "content": "Hello"}
            ]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should auto-select default text model
    assert data["model"] == "llama3.1:8b"  # From settings


def test_vision_completion_with_image(client, mock_adapter):
    """Test completion with image"""
    # Update mock to return vision model response
    mock_adapter.generate.return_value = OllamaGenerateResponse(
        model="minicpm-v:8b",
        created_at="2026-02-04T00:00:00Z",
        response="This image shows a cat.",
        done=True
    )
    
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "minicpm-v:8b",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What's in this image?"},
                        {
                            "type": "image_url",
                            "image_url": {"url": "data:image/jpeg;base64,/9j/4AAQSkZJRg=="}
                        }
                    ]
                }
            ]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["model"] == "minicpm-v:8b"
    assert data["choices"][0]["message"]["content"] == "This image shows a cat."
    
    # Verify generate was called with images
    call_kwargs = mock_adapter.generate.call_args[1]
    assert "images" in call_kwargs
    assert len(call_kwargs["images"]) == 1


def test_vision_auto_model_selection(client, mock_adapter):
    """Test auto model selection for vision"""
    # Update mock for vision model
    mock_adapter.generate.return_value = OllamaGenerateResponse(
        model="minicpm-v:8b",
        created_at="2026-02-04T00:00:00Z",
        response="Image description",
        done=True
    )
    
    response = client.post(
        "/v1/chat/completions",
        json={
            # No model specified
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this"},
                        {
                            "type": "image_url",
                            "image_url": {"url": "data:image/png;base64,iVBORw=="}
                        }
                    ]
                }
            ]
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Should auto-select vision model due to image
    assert data["model"] == "minicpm-v:8b"


def test_model_not_found(client, mock_adapter):
    """Test 404 when model doesn't exist"""
    # Mock list_models to not include the requested model
    mock_adapter.list_models = AsyncMock(return_value=[
        {"name": "llama3.1:8b"},  # Only include valid models
        {"name": "minicpm-v:8b"}
    ])

    # Clear router cache to force re-fetch
    from src.core.router import get_router
    router = get_router(mock_adapter)
    router.clear_cache()

    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "nonexistent:7b",
            "messages": [
                {"role": "user", "content": "Hello"}
            ]
        }
    )

    assert response.status_code == 404
    data = response.json()
    assert "not available" in data["detail"]


def test_request_id_in_response(client, mock_adapter):
    """Test that request ID is included"""
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "llama3.1:8b",
            "messages": [
                {"role": "user", "content": "Hello"}
            ]
        }
    )
    
    assert response.status_code == 200
    
    # Check X-Request-ID header (from RequestIDMiddleware)
    assert "X-Request-ID" in response.headers
    request_id = response.headers["X-Request-ID"]
    
    # Check that completion ID includes request ID
    data = response.json()
    assert request_id in data["id"]


def test_temperature_and_max_tokens(client, mock_adapter):
    """Test that options are passed to adapter"""
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "llama3.1:8b",
            "messages": [
                {"role": "user", "content": "Hello"}
            ],
            "temperature": 0.5,
            "max_tokens": 100
        }
    )
    
    assert response.status_code == 200
    
    # Verify generate was called with options
    call_kwargs = mock_adapter.generate.call_args[1]
    assert "options" in call_kwargs
    options = call_kwargs["options"]
    assert options["temperature"] == 0.5
    assert options["num_predict"] == 100


def test_system_message_included(client, mock_adapter):
    """Test that system messages are included in prompt"""
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "llama3.1:8b",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Hello"}
            ]
        }
    )
    
    assert response.status_code == 200
    
    # Verify prompt includes system message
    call_kwargs = mock_adapter.generate.call_args[1]
    prompt = call_kwargs["prompt"]
    assert "You are a helpful assistant" in prompt


def test_multi_turn_conversation(client, mock_adapter):
    """Test multi-turn conversation"""
    response = client.post(
        "/v1/chat/completions",
        json={
            "model": "llama3.1:8b",
            "messages": [
                {"role": "user", "content": "What is 2+2?"},
                {"role": "assistant", "content": "2+2 equals 4."},
                {"role": "user", "content": "And 3+3?"}
            ]
        }
    )
    
    assert response.status_code == 200
    
    # Verify prompt includes conversation history
    call_kwargs = mock_adapter.generate.call_args[1]
    prompt = call_kwargs["prompt"]
    assert "2+2" in prompt
    assert "4" in prompt
    assert "3+3" in prompt
