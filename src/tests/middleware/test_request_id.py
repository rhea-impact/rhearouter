"""Tests for Request ID middleware"""

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from src.middleware.request_id import RequestIDMiddleware


@pytest.fixture
def app():
    """Create FastAPI app with Request ID middleware"""
    app = FastAPI()
    app.add_middleware(RequestIDMiddleware)

    @app.get("/test")
    def test_endpoint(request: Request):
        # Return request ID from state
        return {"request_id": request.state.request_id}

    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


def test_request_id_generated(client):
    """Test that request ID is generated"""
    response = client.get("/test")
    
    assert response.status_code == 200
    data = response.json()
    
    # Request ID should be in response body (from endpoint)
    assert "request_id" in data
    assert len(data["request_id"]) == 36  # UUID4 length
    assert data["request_id"].count("-") == 4  # UUID4 format


def test_request_id_in_header(client):
    """Test that X-Request-ID header is added"""
    response = client.get("/test")
    
    assert "X-Request-ID" in response.headers
    request_id = response.headers["X-Request-ID"]
    
    # Should be valid UUID4
    assert len(request_id) == 36
    assert request_id.count("-") == 4


def test_request_id_matches(client):
    """Test that header and state request IDs match"""
    response = client.get("/test")
    
    header_id = response.headers["X-Request-ID"]
    body_id = response.json()["request_id"]
    
    assert header_id == body_id


def test_request_id_unique(client):
    """Test that each request gets a unique ID"""
    response1 = client.get("/test")
    response2 = client.get("/test")
    
    id1 = response1.headers["X-Request-ID"]
    id2 = response2.headers["X-Request-ID"]
    
    assert id1 != id2
