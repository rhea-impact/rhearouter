"""Request ID middleware for tracking requests through the system"""

import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from src.observability.logging import get_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that generates a unique request ID for each request.
    
    The request ID is:
    - Stored in request.state.request_id for use by other components
    - Added to response headers as X-Request-ID
    - Available for structured logging
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Generate request ID and process request.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
            
        Returns:
            Response with X-Request-ID header
        """
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        
        # Store in request state for access by handlers
        request.state.request_id = request_id
        
        # Process request
        response: Response = await call_next(request)
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = request_id
        
        return response
