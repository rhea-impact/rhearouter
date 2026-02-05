"""Token bucket rate limiter middleware"""

import time
import asyncio
from collections import defaultdict
from typing import Dict, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from src.core.config import get_settings
from src.observability.logging import get_logger

logger = get_logger(__name__)


class TokenBucket:
    """
    Token bucket algorithm for rate limiting.
    
    Tokens are added at a constant rate (refill_rate).
    Each request consumes one token.
    Burst capacity allows temporary spikes.
    """
    
    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.
        
        Args:
            capacity: Maximum tokens (burst allowance)
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate
        self.last_refill = time.monotonic()
        self.lock = asyncio.Lock()
    
    async def consume(self, tokens: int = 1) -> Tuple[bool, float]:
        """
        Try to consume tokens from bucket.
        
        Args:
            tokens: Number of tokens to consume
            
        Returns:
            Tuple of (success: bool, retry_after: float seconds)
        """
        async with self.lock:
            # Refill tokens based on time elapsed
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(
                self.capacity,
                self.tokens + (elapsed * self.refill_rate)
            )
            self.last_refill = now
            
            # Check if enough tokens available
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True, 0.0
            else:
                # Calculate retry-after time
                tokens_needed = tokens - self.tokens
                retry_after = tokens_needed / self.refill_rate
                return False, retry_after


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Two-tier rate limiting middleware.
    
    - Global: 60 requests/minute (1 req/sec) with 10 token burst
    - Per-client: 20 requests/minute (0.33 req/sec) with 5 token burst
    """
    
    def __init__(self, app):
        super().__init__(app)
        settings = get_settings()
        
        # Global rate limiter (shared across all clients)
        global_capacity = settings.rate_limit_burst
        global_rate = settings.global_rate_limit / 60.0  # Convert to per-second
        self.global_bucket = TokenBucket(global_capacity, global_rate)
        
        # Per-client rate limiters (dict of IP -> TokenBucket)
        self.client_buckets: Dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(
                capacity=5,  # Per-client burst
                refill_rate=settings.per_client_rate_limit / 60.0
            )
        )
        
        logger.info("RateLimiterMiddleware initialized", extra={
            "global_limit": settings.global_rate_limit,
            "client_limit": settings.per_client_rate_limit,
            "burst": settings.rate_limit_burst
        })
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP from request.
        
        Handles X-Forwarded-For header from reverse proxies.
        
        Args:
            request: HTTP request
            
        Returns:
            Client IP address
        """
        # Check X-Forwarded-For header (reverse proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take first IP in chain
            return forwarded.split(",")[0].strip()
        
        # Fall back to direct connection
        return request.client.host if request.client else "unknown"
    
    async def dispatch(self, request: Request, call_next):
        """
        Check rate limits and process request.
        
        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain
            
        Returns:
            Response (or 429 if rate limited)
        """
        # Skip rate limiting for health checks
        if request.url.path.startswith("/health"):
            return await call_next(request)
        
        client_ip = self._get_client_ip(request)
        
        # Check global rate limit
        allowed, retry_after = await self.global_bucket.consume()
        if not allowed:
            logger.warning("Global rate limit exceeded", extra={
                "client_ip": client_ip,
                "path": request.url.path,
                "retry_after": round(retry_after, 2)
            })
            return JSONResponse(
                status_code=429,
                content={"error": "Too many requests (global limit)"},
                headers={"Retry-After": str(int(retry_after) + 1)}
            )
        
        # Check per-client rate limit
        client_bucket = self.client_buckets[client_ip]
        allowed, retry_after = await client_bucket.consume()
        if not allowed:
            logger.warning("Client rate limit exceeded", extra={
                "client_ip": client_ip,
                "path": request.url.path,
                "retry_after": round(retry_after, 2)
            })
            return JSONResponse(
                status_code=429,
                content={"error": "Too many requests (per-client limit)"},
                headers={"Retry-After": str(int(retry_after) + 1)}
            )
        
        # Rate limits passed, process request
        return await call_next(request)
