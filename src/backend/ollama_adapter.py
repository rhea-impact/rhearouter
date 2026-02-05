"""Async adapter for Ollama API with retry logic and connection pooling"""

import httpx
import asyncio
import time
from typing import List, Optional

from src.core.config import get_settings
from src.observability.logging import get_logger
from src.backend.models import (
    OllamaGenerateRequest,
    OllamaGenerateResponse,
    OllamaError,
)

logger = get_logger(__name__)


class OllamaAdapter:
    """
    Async adapter for Ollama API.

    Provides connection pooling, retry logic, and error handling
    for inference requests to local Ollama instance.
    """

    # Retry configuration
    MAX_RETRIES = 3
    INITIAL_BACKOFF = 1.0
    MAX_BACKOFF = 10.0
    BACKOFF_MULTIPLIER = 2.0

    # Retryable HTTP status codes
    RETRYABLE_CODES = {500, 503, 504}

    def __init__(self, base_url: str, timeout: int):
        """
        Initialize Ollama adapter.

        Args:
            base_url: Ollama API base URL (e.g., http://localhost:11434)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

        # Connection pooling configuration
        limits = httpx.Limits(
            max_keepalive_connections=10,
            max_connections=20,
            keepalive_expiry=30.0
        )

        # Create persistent async client
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=httpx.Timeout(timeout),
            limits=limits,
            follow_redirects=True
        )

        # Model cache for validation
        self._model_cache: Optional[List[str]] = None

        logger.info("OllamaAdapter initialized", extra={
            "base_url": base_url,
            "timeout": timeout
        })

    async def health_check(self) -> bool:
        """
        Check if Ollama is running and responsive.

        Returns:
            True if Ollama is healthy, False otherwise
        """
        try:
            response = await self.client.get("/api/tags", timeout=5.0)
            return response.status_code == 200
        except Exception as e:
            logger.error("Ollama health check failed", extra={"error": str(e)})
            return False

    async def list_models(self) -> List[str]:
        """
        Get list of available models from Ollama.

        Returns:
            List of model names
        """
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            models = [m["name"] for m in data.get("models", [])]
            self._model_cache = models
            logger.debug("Listed models", extra={"count": len(models)})
            return models
        except Exception as e:
            logger.error("Failed to list models", extra={"error": str(e)})
            return []

    async def validate_model(self, model_name: str) -> bool:
        """
        Check if model exists in Ollama.

        Args:
            model_name: Name of model to validate

        Returns:
            True if model exists, False otherwise
        """
        if self._model_cache is None:
            await self.list_models()
        return model_name in (self._model_cache or [])

    async def generate(
        self,
        model: str,
        prompt: str,
        images: Optional[List[str]] = None,
        options: Optional[dict] = None
    ) -> OllamaGenerateResponse:
        """
        Call Ollama /api/generate endpoint.

        Args:
            model: Model name (e.g., "llama3.1:8b")
            prompt: Text prompt
            images: Optional list of base64-encoded images
            options: Optional generation parameters (temperature, etc.)

        Returns:
            OllamaGenerateResponse with generated text

        Raises:
            OllamaError: On API errors
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }

        if images:
            payload["images"] = images

        if options:
            payload["options"] = options

        start_time = time.time()

        try:
            response = await self._request_with_retry(
                "POST",
                "/api/generate",
                json=payload
            )

            elapsed = time.time() - start_time
            data = response.json()

            logger.info("Generate request successful", extra={
                "model": model,
                "elapsed_seconds": round(elapsed, 3),
                "has_images": bool(images)
            })

            return OllamaGenerateResponse(**data)

        except httpx.TimeoutException as e:
            elapsed = time.time() - start_time
            logger.error("Ollama request timeout", extra={
                "model": model,
                "timeout": self.timeout,
                "elapsed_seconds": round(elapsed, 3)
            })
            raise OllamaError(
                error=f"Request timeout after {self.timeout}s",
                error_code="timeout",
                status_code=504
            )

        except httpx.HTTPStatusError as e:
            logger.error("Ollama HTTP error", extra={
                "status_code": e.response.status_code,
                "response": e.response.text[:500],
                "model": model
            })

            # Map to appropriate error
            if e.response.status_code == 404:
                raise OllamaError(
                    error=f"Model not found: {model}",
                    error_code="model_not_found",
                    status_code=404
                )
            else:
                raise OllamaError(
                    error=f"Ollama error: {e.response.text[:200]}",
                    error_code="ollama_error",
                    status_code=e.response.status_code
                )

        except httpx.ConnectError:
            # Re-raise connection errors after retry exhaustion
            # Already logged in _request_with_retry
            raise

        except Exception as e:
            logger.error("Unexpected error in generate", extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "model": model
            })
            raise OllamaError(
                error=f"Unexpected error: {str(e)}",
                error_code="internal_error",
                status_code=500
            )

    async def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> httpx.Response:
        """
        Make HTTP request with exponential backoff retry.

        Retries on connection errors, timeouts, and 5xx errors.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL path
            **kwargs: Additional request parameters

        Returns:
            HTTP response

        Raises:
            httpx exceptions on final failure
        """
        last_exception = None
        backoff = self.INITIAL_BACKOFF

        for attempt in range(self.MAX_RETRIES):
            try:
                response = await self.client.request(method, url, **kwargs)

                # Check if retryable status code
                if response.status_code in self.RETRYABLE_CODES:
                    if attempt < self.MAX_RETRIES - 1:
                        logger.warning(
                            "Retryable error, backing off",
                            extra={
                                "attempt": attempt + 1,
                                "status_code": response.status_code,
                                "backoff_seconds": backoff
                            }
                        )
                        await asyncio.sleep(backoff)
                        backoff = min(backoff * self.BACKOFF_MULTIPLIER, self.MAX_BACKOFF)
                        continue

                response.raise_for_status()
                return response

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_exception = e
                if attempt < self.MAX_RETRIES - 1:
                    logger.warning(
                        "Connection error, retrying",
                        extra={
                            "attempt": attempt + 1,
                            "error": str(e),
                            "backoff_seconds": backoff
                        }
                    )
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * self.BACKOFF_MULTIPLIER, self.MAX_BACKOFF)
                else:
                    logger.error(
                        "All retry attempts exhausted",
                        extra={
                            "attempts": self.MAX_RETRIES,
                            "error": str(e)
                        }
                    )
                    raise

        # All retries exhausted
        if last_exception:
            raise last_exception

        # Should not reach here, but just in case
        raise RuntimeError("Retry logic error: no exception but no response")

    async def close(self):
        """Close HTTP client and clean up resources."""
        await self.client.aclose()
        logger.info("OllamaAdapter closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
