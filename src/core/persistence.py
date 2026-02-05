"""
SQLite Persistence Layer

Handles request/response logging for analytics and debugging.
"""

import sqlite3
import json
import time
from typing import Optional, List, Dict, Any
from pathlib import Path
from contextlib import contextmanager

from src.core.config import get_settings
from src.observability.logging import get_logger

logger = get_logger(__name__)


class RequestLogger:
    """
    SQLite-based request logger for analytics and debugging.

    Stores request metadata (not full bodies for privacy).
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize request logger.

        Args:
            db_path: Path to SQLite database (defaults to data/requests.db)
        """
        settings = get_settings()
        if db_path is None:
            db_path = str(Path.home() / "repos/rhearouter/data/requests.db")

        self.db_path = db_path
        self.retention_days = 30  # Keep 30 days of history

        # Ensure data directory exists
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_db()

        logger.info(f"Request logger initialized at {db_path}")

    def _init_db(self):
        """Create database schema if not exists"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS requests (
                    id TEXT PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    endpoint TEXT NOT NULL,
                    model_requested TEXT,
                    model_used TEXT NOT NULL,
                    request_type TEXT,
                    technique_used TEXT,
                    duration_ms REAL,
                    tokens_prompt INTEGER,
                    tokens_completion INTEGER,
                    tokens_total INTEGER,
                    has_images BOOLEAN,
                    error_type TEXT,
                    error_message TEXT,
                    client_ip TEXT,
                    user_agent TEXT
                )
            """)

            # Create indexes for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON requests(timestamp)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_model_used
                ON requests(model_used)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_request_type
                ON requests(request_type)
            """)

            conn.commit()
            logger.debug("Database schema initialized")

    @contextmanager
    def _get_connection(self):
        """Get database connection with context manager"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Return rows as dicts
        try:
            yield conn
        finally:
            conn.close()

    def log_request(
        self,
        request_id: str,
        endpoint: str,
        model_requested: Optional[str],
        model_used: str,
        request_type: Optional[str] = None,
        technique_used: Optional[str] = None,
        duration_ms: Optional[float] = None,
        tokens_prompt: Optional[int] = None,
        tokens_completion: Optional[int] = None,
        tokens_total: Optional[int] = None,
        has_images: bool = False,
        error_type: Optional[str] = None,
        error_message: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Log a request to the database.

        Args:
            request_id: Unique request ID (UUID)
            endpoint: API endpoint called
            model_requested: Model requested by user (None if auto-selected)
            model_used: Actual model used for inference
            request_type: Type of request (vision, reasoning, etc.)
            technique_used: Technique used (single, moa, ensemble)
            duration_ms: Request duration in milliseconds
            tokens_prompt: Prompt tokens
            tokens_completion: Completion tokens
            tokens_total: Total tokens
            has_images: Whether request had images
            error_type: Error type if failed
            error_message: Error message if failed
            client_ip: Client IP address
            user_agent: Client user agent
        """
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO requests (
                        id, timestamp, endpoint, model_requested, model_used,
                        request_type, technique_used, duration_ms,
                        tokens_prompt, tokens_completion, tokens_total,
                        has_images, error_type, error_message,
                        client_ip, user_agent
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    request_id,
                    time.time(),
                    endpoint,
                    model_requested,
                    model_used,
                    request_type,
                    technique_used or "single",
                    duration_ms,
                    tokens_prompt,
                    tokens_completion,
                    tokens_total,
                    has_images,
                    error_type,
                    error_message,
                    client_ip,
                    user_agent
                ))
                conn.commit()

                logger.debug(f"Logged request {request_id}", extra={
                    "request_id": request_id,
                    "model": model_used,
                    "duration_ms": duration_ms
                })
        except Exception as e:
            logger.error(f"Failed to log request: {e}", extra={
                "request_id": request_id,
                "error": str(e)
            })

    def get_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a single request by ID.

        Args:
            request_id: Request ID to retrieve

        Returns:
            Request data as dict, or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM requests WHERE id = ?",
                (request_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_recent_requests(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get recent requests.

        Args:
            limit: Max number of requests to return

        Returns:
            List of request dicts, newest first
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM requests
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get usage statistics for the last N days.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with statistics
        """
        cutoff = time.time() - (days * 86400)

        with self._get_connection() as conn:
            # Total requests
            total = conn.execute(
                "SELECT COUNT(*) FROM requests WHERE timestamp >= ?",
                (cutoff,)
            ).fetchone()[0]

            # Success vs errors
            errors = conn.execute(
                "SELECT COUNT(*) FROM requests WHERE timestamp >= ? AND error_type IS NOT NULL",
                (cutoff,)
            ).fetchone()[0]
            success = total - errors

            # Model usage
            model_usage = conn.execute("""
                SELECT model_used, COUNT(*) as count, AVG(duration_ms) as avg_duration
                FROM requests
                WHERE timestamp >= ? AND error_type IS NULL
                GROUP BY model_used
                ORDER BY count DESC
            """, (cutoff,)).fetchall()

            # Request types
            request_types = conn.execute("""
                SELECT request_type, COUNT(*) as count
                FROM requests
                WHERE timestamp >= ?
                GROUP BY request_type
                ORDER BY count DESC
            """, (cutoff,)).fetchall()

            # Token usage
            tokens = conn.execute("""
                SELECT
                    SUM(tokens_total) as total,
                    AVG(tokens_total) as avg_per_request,
                    SUM(tokens_prompt) as prompt,
                    SUM(tokens_completion) as completion
                FROM requests
                WHERE timestamp >= ? AND error_type IS NULL
            """, (cutoff,)).fetchone()

            # Average duration
            avg_duration = conn.execute("""
                SELECT AVG(duration_ms)
                FROM requests
                WHERE timestamp >= ? AND error_type IS NULL
            """, (cutoff,)).fetchone()[0]

            return {
                "period_days": days,
                "total_requests": total,
                "successful_requests": success,
                "failed_requests": errors,
                "success_rate": round(success / total * 100, 2) if total > 0 else 0,
                "avg_duration_ms": round(avg_duration, 2) if avg_duration else 0,
                "model_usage": [
                    {
                        "model": row[0],
                        "count": row[1],
                        "avg_duration_ms": round(row[2], 2) if row[2] else 0
                    }
                    for row in model_usage
                ],
                "request_types": [
                    {"type": row[0], "count": row[1]}
                    for row in request_types
                ],
                "tokens": {
                    "total": tokens[0] or 0,
                    "avg_per_request": round(tokens[1], 2) if tokens[1] else 0,
                    "prompt": tokens[2] or 0,
                    "completion": tokens[3] or 0
                }
            }

    def cleanup_old_requests(self, days: Optional[int] = None):
        """
        Delete requests older than N days.

        Args:
            days: Number of days to keep (defaults to retention_days)
        """
        if days is None:
            days = self.retention_days

        cutoff = time.time() - (days * 86400)

        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM requests WHERE timestamp < ?",
                (cutoff,)
            )
            deleted = cursor.rowcount
            conn.commit()

            if deleted > 0:
                logger.info(f"Cleaned up {deleted} old requests (>{days} days)")

            return deleted

    def get_error_summary(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get summary of errors in the last N days.

        Args:
            days: Number of days to analyze

        Returns:
            List of error summaries
        """
        cutoff = time.time() - (days * 86400)

        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT
                    error_type,
                    COUNT(*) as count,
                    error_message
                FROM requests
                WHERE timestamp >= ? AND error_type IS NOT NULL
                GROUP BY error_type, error_message
                ORDER BY count DESC
            """, (cutoff,))

            return [
                {
                    "error_type": row[0],
                    "count": row[1],
                    "message": row[2]
                }
                for row in cursor.fetchall()
            ]

    def get_model_performance(self, model: str, days: int = 7) -> Dict[str, Any]:
        """
        Get performance metrics for a specific model.

        Args:
            model: Model name
            days: Number of days to analyze

        Returns:
            Performance metrics dict
        """
        cutoff = time.time() - (days * 86400)

        with self._get_connection() as conn:
            # Request count and success rate
            total = conn.execute(
                "SELECT COUNT(*) FROM requests WHERE timestamp >= ? AND model_used = ?",
                (cutoff, model)
            ).fetchone()[0]

            errors = conn.execute(
                "SELECT COUNT(*) FROM requests WHERE timestamp >= ? AND model_used = ? AND error_type IS NOT NULL",
                (cutoff, model)
            ).fetchone()[0]

            # Duration stats
            duration_stats = conn.execute("""
                SELECT
                    AVG(duration_ms) as avg,
                    MIN(duration_ms) as min,
                    MAX(duration_ms) as max
                FROM requests
                WHERE timestamp >= ? AND model_used = ? AND error_type IS NULL
            """, (cutoff, model)).fetchone()

            # Token stats
            token_stats = conn.execute("""
                SELECT
                    AVG(tokens_total) as avg_total,
                    AVG(tokens_prompt) as avg_prompt,
                    AVG(tokens_completion) as avg_completion
                FROM requests
                WHERE timestamp >= ? AND model_used = ? AND error_type IS NULL
            """, (cutoff, model)).fetchone()

            return {
                "model": model,
                "period_days": days,
                "total_requests": total,
                "successful_requests": total - errors,
                "failed_requests": errors,
                "success_rate": round((total - errors) / total * 100, 2) if total > 0 else 0,
                "duration_ms": {
                    "avg": round(duration_stats[0], 2) if duration_stats[0] else 0,
                    "min": round(duration_stats[1], 2) if duration_stats[1] else 0,
                    "max": round(duration_stats[2], 2) if duration_stats[2] else 0
                },
                "tokens": {
                    "avg_total": round(token_stats[0], 2) if token_stats[0] else 0,
                    "avg_prompt": round(token_stats[1], 2) if token_stats[1] else 0,
                    "avg_completion": round(token_stats[2], 2) if token_stats[2] else 0
                }
            }


# Singleton instance
_request_logger_instance = None


def get_request_logger(db_path: Optional[str] = None) -> RequestLogger:
    """
    Get singleton request logger instance.

    Args:
        db_path: Optional database path (only used on first call)

    Returns:
        RequestLogger instance
    """
    global _request_logger_instance

    if _request_logger_instance is None:
        _request_logger_instance = RequestLogger(db_path)

    return _request_logger_instance
