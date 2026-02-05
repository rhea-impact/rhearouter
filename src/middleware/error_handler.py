"""Error handler middleware for consistent error responses"""

import traceback
from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.backend.models import OllamaError
from src.observability.logging import get_logger

logger = get_logger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware that catches all unhandled exceptions and returns
    OpenAI-compatible error responses.
    
    Maps exceptions to appropriate HTTP status codes and includes
    request IDs for debugging.
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Process request with comprehensive error handling.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
            
        Returns:
            Response (or error response if exception caught)
        """
        try:
            response = await call_next(request)
            return response
            
        except HTTPException as e:
            # FastAPI HTTPException - pass through with status code
            request_id = getattr(request.state, "request_id", "unknown")
            
            logger.warning("HTTP exception", extra={
                "request_id": request_id,
                "status_code": e.status_code,
                "detail": e.detail,
                "path": request.url.path
            })
            
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": {
                        "message": e.detail,
                        "type": "http_error",
                        "code": e.status_code,
                        "request_id": request_id
                    }
                }
            )
        
        except OllamaError as e:
            # Ollama backend error
            request_id = getattr(request.state, "request_id", "unknown")
            
            logger.error("Ollama error", extra={
                "request_id": request_id,
                "error_code": e.error_code,
                "status_code": e.status_code,
                "error": e.error,
                "path": request.url.path
            })
            
            return JSONResponse(
                status_code=e.status_code,
                content={
                    "error": {
                        "message": e.error,
                        "type": "ollama_error",
                        "code": e.error_code,
                        "request_id": request_id
                    }
                },
                headers={"Retry-After": str(e.retry_after)} if e.retry_after else {}
            )
        
        except ConnectionError as e:
            # Connection to backend failed
            request_id = getattr(request.state, "request_id", "unknown")
            
            logger.error("Backend connection error", extra={
                "request_id": request_id,
                "error": str(e),
                "path": request.url.path
            })
            
            return JSONResponse(
                status_code=503,
                content={
                    "error": {
                        "message": "Service temporarily unavailable",
                        "type": "connection_error",
                        "code": "service_unavailable",
                        "request_id": request_id
                    }
                },
                headers={"Retry-After": "10"}
            )
        
        except TimeoutError as e:
            # Request timeout
            request_id = getattr(request.state, "request_id", "unknown")
            
            logger.error("Request timeout", extra={
                "request_id": request_id,
                "error": str(e),
                "path": request.url.path
            })
            
            return JSONResponse(
                status_code=504,
                content={
                    "error": {
                        "message": "Gateway timeout",
                        "type": "timeout_error",
                        "code": "gateway_timeout",
                        "request_id": request_id
                    }
                }
            )
        
        except Exception as e:
            # Unexpected error
            request_id = getattr(request.state, "request_id", "unknown")
            
            logger.error("Unhandled exception", extra={
                "request_id": request_id,
                "error": str(e),
                "error_type": type(e).__name__,
                "path": request.url.path,
                "traceback": traceback.format_exc()
            })
            
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "message": "Internal server error",
                        "type": "internal_error",
                        "code": "internal_server_error",
                        "request_id": request_id
                    }
                }
            )
