"""Tests for SQLite persistence layer"""

import pytest
import tempfile
import time
from pathlib import Path

from src.core.persistence import RequestLogger


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    # Cleanup
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def logger(temp_db):
    """Create request logger with temp database"""
    return RequestLogger(db_path=temp_db)


def test_init_creates_database(temp_db):
    """Should create database and schema"""
    logger = RequestLogger(db_path=temp_db)
    assert Path(temp_db).exists()


def test_log_request_success(logger):
    """Should log successful request"""
    logger.log_request(
        request_id="test-123",
        endpoint="/v1/chat/completions",
        model_requested="llama3.1:8b",
        model_used="llama3.1:8b",
        request_type="general",
        duration_ms=1500.0,
        tokens_prompt=10,
        tokens_completion=20,
        tokens_total=30,
        has_images=False
    )

    # Retrieve and verify
    request = logger.get_request("test-123")
    assert request is not None
    assert request["id"] == "test-123"
    assert request["model_used"] == "llama3.1:8b"
    assert request["duration_ms"] == 1500.0
    assert request["tokens_total"] == 30


def test_log_request_with_error(logger):
    """Should log failed request"""
    logger.log_request(
        request_id="test-error",
        endpoint="/v1/chat/completions",
        model_requested="llama3.1:8b",
        model_used="llama3.1:8b",
        error_type="timeout_error",
        error_message="Request timed out"
    )

    request = logger.get_request("test-error")
    assert request["error_type"] == "timeout_error"
    assert request["error_message"] == "Request timed out"


def test_get_request_not_found(logger):
    """Should return None for non-existent request"""
    request = logger.get_request("nonexistent")
    assert request is None


def test_get_recent_requests(logger):
    """Should return recent requests newest first"""
    # Log multiple requests
    for i in range(5):
        logger.log_request(
            request_id=f"test-{i}",
            endpoint="/v1/chat/completions",
            model_requested=None,
            model_used="llama3.1:8b"
        )
        time.sleep(0.01)  # Ensure different timestamps

    requests = logger.get_recent_requests(limit=3)
    assert len(requests) == 3
    # Should be newest first
    assert requests[0]["id"] == "test-4"
    assert requests[1]["id"] == "test-3"
    assert requests[2]["id"] == "test-2"


def test_get_stats(logger):
    """Should calculate statistics correctly"""
    # Log successful requests
    for i in range(3):
        logger.log_request(
            request_id=f"success-{i}",
            endpoint="/v1/chat/completions",
            model_requested=None,
            model_used="llama3.1:8b",
            duration_ms=1000.0,
            tokens_total=30
        )

    # Log failed request
    logger.log_request(
        request_id="failed-1",
        endpoint="/v1/chat/completions",
        model_requested=None,
        model_used="llama3.1:8b",
        error_type="error"
    )

    stats = logger.get_stats(days=1)

    assert stats["total_requests"] == 4
    assert stats["successful_requests"] == 3
    assert stats["failed_requests"] == 1
    assert stats["success_rate"] == 75.0
    assert stats["avg_duration_ms"] == 1000.0


def test_get_stats_model_usage(logger):
    """Should track model usage"""
    logger.log_request(
        request_id="req-1",
        endpoint="/v1/chat/completions",
        model_requested=None,
        model_used="llama3.1:8b",
        duration_ms=1000.0
    )

    logger.log_request(
        request_id="req-2",
        endpoint="/v1/chat/completions",
        model_requested=None,
        model_used="llama3.1:8b",
        duration_ms=2000.0
    )

    logger.log_request(
        request_id="req-3",
        endpoint="/v1/chat/completions",
        model_requested=None,
        model_used="deepseek-r1:8b",
        duration_ms=3000.0
    )

    stats = logger.get_stats(days=1)

    assert len(stats["model_usage"]) == 2
    assert stats["model_usage"][0]["model"] == "llama3.1:8b"
    assert stats["model_usage"][0]["count"] == 2
    assert stats["model_usage"][0]["avg_duration_ms"] == 1500.0


def test_cleanup_old_requests(logger):
    """Should delete old requests"""
    # Insert old request (fake old timestamp)
    import sqlite3
    conn = sqlite3.connect(logger.db_path)
    old_timestamp = time.time() - (31 * 86400)  # 31 days ago
    conn.execute("""
        INSERT INTO requests (id, timestamp, endpoint, model_used)
        VALUES (?, ?, ?, ?)
    """, ("old-request", old_timestamp, "/v1/chat/completions", "llama3.1:8b"))
    conn.commit()
    conn.close()

    # Insert recent request
    logger.log_request(
        request_id="recent-request",
        endpoint="/v1/chat/completions",
        model_requested=None,
        model_used="llama3.1:8b"
    )

    # Cleanup (30 day retention)
    deleted = logger.cleanup_old_requests(days=30)
    assert deleted == 1

    # Verify old request deleted, recent kept
    assert logger.get_request("old-request") is None
    assert logger.get_request("recent-request") is not None


def test_get_error_summary(logger):
    """Should summarize errors"""
    # Log errors
    logger.log_request(
        request_id="err-1",
        endpoint="/v1/chat/completions",
        model_requested=None,
        model_used="llama3.1:8b",
        error_type="timeout",
        error_message="Request timeout"
    )

    logger.log_request(
        request_id="err-2",
        endpoint="/v1/chat/completions",
        model_requested=None,
        model_used="llama3.1:8b",
        error_type="timeout",
        error_message="Request timeout"
    )

    logger.log_request(
        request_id="err-3",
        endpoint="/v1/chat/completions",
        model_requested=None,
        model_used="llama3.1:8b",
        error_type="connection",
        error_message="Connection failed"
    )

    errors = logger.get_error_summary(days=1)

    assert len(errors) == 2
    assert errors[0]["error_type"] == "timeout"
    assert errors[0]["count"] == 2


def test_get_model_performance(logger):
    """Should get performance metrics for specific model"""
    # Log requests for llama
    for i in range(2):
        logger.log_request(
            request_id=f"llama-{i}",
            endpoint="/v1/chat/completions",
            model_requested=None,
            model_used="llama3.1:8b",
            duration_ms=1000.0 + (i * 1000),
            tokens_total=30
        )

    # Log request for deepseek
    logger.log_request(
        request_id="deepseek-1",
        endpoint="/v1/chat/completions",
        model_requested=None,
        model_used="deepseek-r1:8b",
        duration_ms=2000.0,
        tokens_total=40
    )

    perf = logger.get_model_performance("llama3.1:8b", days=1)

    assert perf["model"] == "llama3.1:8b"
    assert perf["total_requests"] == 2
    assert perf["successful_requests"] == 2
    assert perf["duration_ms"]["avg"] == 1500.0
    assert perf["tokens"]["avg_total"] == 30.0


def test_singleton_pattern():
    """Should return same instance"""
    from src.core.persistence import get_request_logger

    with tempfile.NamedTemporaryFile(suffix=".db") as f:
        logger1 = get_request_logger(f.name)
        logger2 = get_request_logger()

        assert logger1 is logger2
