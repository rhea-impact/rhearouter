"""Tests for error handler middleware"""

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from src.middleware.error_handler import ErrorHandlerMiddleware
from src.middleware.request_id import RequestIDMiddleware
from src.backend.models import OllamaError


@pytest.fixture
def app():
    """Create FastAPI app with error handler and request ID middleware"""
    app = FastAPI()
    # Add error handler first (outermost)
    app.add_middleware(ErrorHandlerMiddleware)
    # Add request ID (innermost)
    app.add_middleware(RequestIDMiddleware)
    
    @app.get("/http_error")
    def http_error_endpoint():
        raise HTTPException(status_code=404, detail="Not found")
    
    @app.get("/ollama_error")
    def ollama_error_endpoint():
        raise OllamaError(
            error="Model not found: test:7b",
            error_code="model_not_found",
            status_code=404
        )
    
    @app.get("/connection_error")
    def connection_error_endpoint():
        raise ConnectionError("Connection refused")
    
    @app.get("/timeout_error")
    def timeout_error_endpoint():
        raise TimeoutError("Request timeout")
    
    @app.get("/unexpected_error")
    def unexpected_error_endpoint():
        raise ValueError("Unexpected error")
    
    @app.get("/success")
    def success_endpoint():
        return {"status": "ok"}
    
    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


def test_success_passthrough(client):
    """Test that successful requests pass through"""
    response = client.get("/success")
    assert response.status_code == 200


def test_http_exception_handling(client):
    """Test HTTPException handling - FastAPI handles this internally"""
    response = client.get("/http_error")

    assert response.status_code == 404
    data = response.json()

    # FastAPI's default HTTPException handler returns this format
    assert "detail" in data
    assert data["detail"] == "Not found"

    # Note: HTTPException is handled by FastAPI's built-in handler,
    # not our middleware. This is expected behavior.


def test_ollama_error_handling(client):
    """Test OllamaError handling"""
    response = client.get("/ollama_error")
    
    assert response.status_code == 404
    data = response.json()
    
    # Should have error structure
    assert "error" in data
    assert "Model not found" in data["error"]["message"]
    assert data["error"]["type"] == "ollama_error"
    assert data["error"]["code"] == "model_not_found"
    assert "request_id" in data["error"]


def test_connection_error_handling(client):
    """Test ConnectionError handling"""
    response = client.get("/connection_error")
    
    assert response.status_code == 503
    data = response.json()
    
    # Should have error structure
    assert "error" in data
    assert "Service temporarily unavailable" in data["error"]["message"]
    assert data["error"]["type"] == "connection_error"
    assert data["error"]["code"] == "service_unavailable"
    
    # Should have Retry-After header
    assert "Retry-After" in response.headers
    assert response.headers["Retry-After"] == "10"


def test_timeout_error_handling(client):
    """Test TimeoutError handling"""
    response = client.get("/timeout_error")
    
    assert response.status_code == 504
    data = response.json()
    
    # Should have error structure
    assert "error" in data
    assert "Gateway timeout" in data["error"]["message"]
    assert data["error"]["type"] == "timeout_error"
    assert data["error"]["code"] == "gateway_timeout"


def test_unexpected_error_handling(client):
    """Test unexpected exception handling"""
    response = client.get("/unexpected_error")
    
    assert response.status_code == 500
    data = response.json()
    
    # Should have error structure
    assert "error" in data
    assert "Internal server error" in data["error"]["message"]
    assert data["error"]["type"] == "internal_error"
    assert data["error"]["code"] == "internal_server_error"
    assert "request_id" in data["error"]


def test_request_id_in_all_errors(client):
    """Test that all middleware-handled errors include request ID"""
    endpoints = [
        "/ollama_error",
        "/connection_error",
        "/timeout_error",
        "/unexpected_error"
    ]

    for endpoint in endpoints:
        response = client.get(endpoint)
        data = response.json()

        # All should have request ID in error
        assert "request_id" in data["error"], f"No request_id in {endpoint}"
        request_id = data["error"]["request_id"]
        assert len(request_id) == 36, f"Invalid request_id in {endpoint}"
