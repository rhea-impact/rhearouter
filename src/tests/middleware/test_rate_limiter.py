"""Tests for rate limiter middleware"""

import pytest
import time
from unittest.mock import patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.middleware.rate_limiter import RateLimiterMiddleware, TokenBucket


@pytest.fixture
def app():
    """Create FastAPI app with rate limiter"""
    app = FastAPI()
    app.add_middleware(RateLimiterMiddleware)
    
    @app.get("/test")
    def test_endpoint():
        return {"status": "ok"}
    
    @app.get("/health")
    def health_endpoint():
        return {"status": "healthy"}
    
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.mark.asyncio
async def test_token_bucket_consume_success():
    """Test successful token consumption"""
    bucket = TokenBucket(capacity=10, refill_rate=1.0)
    
    allowed, retry_after = await bucket.consume(1)
    
    assert allowed is True
    assert retry_after == 0.0
    assert bucket.tokens == 9.0


@pytest.mark.asyncio
async def test_token_bucket_consume_failure():
    """Test token consumption when bucket empty"""
    bucket = TokenBucket(capacity=1, refill_rate=1.0)
    
    # Consume all tokens
    await bucket.consume(1)
    
    # Try to consume again (should fail)
    allowed, retry_after = await bucket.consume(1)
    
    assert allowed is False
    assert retry_after > 0.0


@pytest.mark.asyncio
async def test_token_bucket_refill():
    """Test that tokens refill over time"""
    bucket = TokenBucket(capacity=10, refill_rate=10.0)  # 10 tokens/sec

    # Consume all tokens
    await bucket.consume(10)
    assert bucket.tokens == 0.0

    # Mock time advancing by 0.5 seconds
    base_time = bucket.last_refill
    with patch('src.middleware.rate_limiter.time.monotonic', side_effect=[base_time + 0.5]):
        allowed, retry_after = await bucket.consume(1)

    # Should have 5 tokens refilled (10 tokens/sec * 0.5 sec = 5 tokens)
    # 5 tokens - 1 consumed = 4 tokens remaining
    assert allowed is True


def test_rate_limiter_allows_requests(client):
    """Test that requests are allowed under limit"""
    # First few requests should succeed
    for i in range(5):
        response = client.get("/test")
        assert response.status_code == 200


def test_rate_limiter_enforces_limit(client):
    """Test that rate limit is enforced"""
    # Make many requests to hit limit
    responses = []
    for i in range(15):  # Burst is 10, so should hit limit
        response = client.get("/test")
        responses.append(response.status_code)
    
    # Should have at least one 429
    assert 429 in responses


def test_rate_limiter_retry_after_header(client):
    """Test that Retry-After header is included in 429 response"""
    # Make many requests to hit limit
    for i in range(15):
        response = client.get("/test")
        if response.status_code == 429:
            assert "Retry-After" in response.headers
            retry_after = int(response.headers["Retry-After"])
            assert retry_after > 0
            break


def test_rate_limiter_health_check_bypass(client):
    """Test that health checks bypass rate limiting"""
    # Health checks should never be rate limited
    for i in range(100):
        response = client.get("/health")
        assert response.status_code == 200


def test_rate_limiter_error_message(client):
    """Test that 429 response has proper error message"""
    # Make many requests to hit limit
    for i in range(15):
        response = client.get("/test")
        if response.status_code == 429:
            data = response.json()
            assert "error" in data
            assert "Too many requests" in data["error"]
            break
