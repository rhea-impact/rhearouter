"""Tests for VRAM flow valve middleware"""

import pytest
import asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.middleware.vram_flow_valve import VRAMFlowValve


@pytest.fixture
def app():
    """Create FastAPI app with VRAM flow valve"""
    app = FastAPI()
    app.add_middleware(VRAMFlowValve)
    
    @app.post("/v1/chat/completions")
    async def chat_endpoint():
        # Simulate inference delay
        await asyncio.sleep(0.1)
        return {"response": "ok"}
    
    @app.get("/health")
    def health_endpoint():
        return {"status": "healthy"}
    
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


def test_vision_model_detection():
    """Test vision model pattern detection"""
    middleware = VRAMFlowValve(app=None)
    
    # Should detect vision models
    assert middleware._is_vision_model("qwen2.5vl:7b") is True
    assert middleware._is_vision_model("minicpm-v:8b") is True
    assert middleware._is_vision_model("llava:7b") is True
    assert middleware._is_vision_model("some-vision-model") is True
    
    # Should not detect text models
    assert middleware._is_vision_model("llama3.1:8b") is False
    assert middleware._is_vision_model("qwen2.5:7b") is False
    assert middleware._is_vision_model("deepseek-r1:8b") is False


def test_text_request_allowed(client):
    """Test that text requests are allowed"""
    response = client.post(
        "/v1/chat/completions",
        json={"model": "llama3.1:8b", "messages": []}
    )
    assert response.status_code == 200


def test_vision_request_allowed(client):
    """Test that vision requests are allowed"""
    response = client.post(
        "/v1/chat/completions",
        json={"model": "qwen2.5vl:7b", "messages": []}
    )
    assert response.status_code == 200


def test_health_check_bypass(client):
    """Test that health checks bypass flow valve"""
    response = client.get("/health")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_concurrent_text_requests():
    """Test that multiple text requests can run concurrently"""
    from fastapi import FastAPI
    from httpx import AsyncClient, ASGITransport

    app = FastAPI()
    app.add_middleware(VRAMFlowValve)

    @app.post("/v1/chat/completions")
    async def chat_endpoint():
        await asyncio.sleep(0.2)  # Simulate slow inference
        return {"response": "ok"}

    # Make 2 concurrent text requests (should both succeed with 2 slots)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        tasks = [
            client.post("/v1/chat/completions", json={"model": "llama3.1:8b", "messages": []}),
            client.post("/v1/chat/completions", json={"model": "qwen2.5:7b", "messages": []})
        ]

        results = await asyncio.gather(*tasks)

        # Both should succeed
        assert all(r.status_code == 200 for r in results)


@pytest.mark.asyncio
async def test_vision_requests_queued():
    """Test that vision requests are queued (only 1 slot)"""
    from fastapi import FastAPI
    from httpx import AsyncClient, ASGITransport
    import time

    app = FastAPI()
    app.add_middleware(VRAMFlowValve)

    @app.post("/v1/chat/completions")
    async def chat_endpoint():
        await asyncio.sleep(0.3)  # Simulate slow vision inference
        return {"response": "ok"}

    # Make 2 concurrent vision requests
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        start = time.time()

        tasks = [
            client.post("/v1/chat/completions", json={"model": "qwen2.5vl:7b", "messages": []}),
            client.post("/v1/chat/completions", json={"model": "minicpm-v:8b", "messages": []})
        ]

        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start

        # Both should succeed
        assert all(r.status_code == 200 for r in results)

        # Should take >0.5s (queued, not parallel)
        # First request: 0.3s, second waits then 0.3s = 0.6s total
        assert elapsed >= 0.5
