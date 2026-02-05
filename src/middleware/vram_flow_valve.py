"""VRAM flow valve middleware for managing concurrent inference requests"""

import asyncio
import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from src.core.config import get_settings
from src.observability.logging import get_logger

logger = get_logger(__name__)


class VRAMFlowValve(BaseHTTPMiddleware):
    """
    VRAM-aware flow control middleware.
    
    Limits concurrent inference requests to prevent VRAM exhaustion:
    - Vision models: 1 concurrent request (high VRAM usage)
    - Text models: 2 concurrent requests (lower VRAM usage)
    
    Uses semaphores to queue requests when slots are full.
    """
    
    # Vision model patterns (case-insensitive)
    VISION_MODEL_PATTERNS = ['vl', 'llava', 'minicpm-v', 'vision', 'qwen2.5vl']
    
    def __init__(self, app):
        super().__init__(app)
        settings = get_settings()
        
        # Create semaphores for slot management
        self.vision_slots = asyncio.Semaphore(settings.vision_slots)
        self.text_slots = asyncio.Semaphore(settings.text_slots)
        
        logger.info("VRAMFlowValve initialized", extra={
            "vision_slots": settings.vision_slots,
            "text_slots": settings.text_slots
        })
    
    def _is_vision_model(self, model_name: str) -> bool:
        """
        Detect if model is a vision model.
        
        Args:
            model_name: Model name from request
            
        Returns:
            True if vision model, False otherwise
        """
        model_lower = model_name.lower()
        return any(pattern in model_lower for pattern in self.VISION_MODEL_PATTERNS)
    
    async def _get_model_from_request(self, request: Request) -> str:
        """
        Extract model name from request body.
        
        Args:
            request: HTTP request
            
        Returns:
            Model name (or "text" as fallback)
        """
        # Check if this is a chat completion request
        if not request.url.path.startswith("/v1/"):
            return "text"  # Non-inference requests use text slots
        
        try:
            # Read body (need to cache it for next handler)
            body = await request.body()
            
            # Re-attach body for downstream handlers
            async def receive():
                return {"type": "http.request", "body": body}
            request._receive = receive
            
            # Parse JSON
            if body:
                data = json.loads(body)
                model = data.get("model", "text")
                return model
            else:
                return "text"
                
        except Exception as e:
            logger.warning("Failed to parse model from request", extra={
                "error": str(e),
                "path": request.url.path
            })
            return "text"  # Default to text on parse error
    
    async def dispatch(self, request: Request, call_next):
        """
        Acquire VRAM slot, process request, release slot.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
            
        Returns:
            Response
        """
        # Skip flow valve for health checks and non-inference endpoints
        if request.url.path.startswith("/health") or request.url.path == "/":
            return await call_next(request)
        
        # Determine model type
        model_name = await self._get_model_from_request(request)
        is_vision = self._is_vision_model(model_name)
        
        # Select appropriate semaphore
        semaphore = self.vision_slots if is_vision else self.text_slots
        slot_type = "vision" if is_vision else "text"
        
        logger.debug("Acquiring VRAM slot", extra={
            "model": model_name,
            "slot_type": slot_type,
            "path": request.url.path
        })
        
        # Acquire slot (blocks if all slots busy)
        async with semaphore:
            logger.debug("VRAM slot acquired", extra={
                "model": model_name,
                "slot_type": slot_type
            })
            
            try:
                # Process request with slot
                response = await call_next(request)
                return response
            finally:
                logger.debug("VRAM slot released", extra={
                    "model": model_name,
                    "slot_type": slot_type
                })
