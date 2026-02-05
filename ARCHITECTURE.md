# RheaRouter Architecture

Deep dive into RheaRouter's system design, component interactions, and data flow.

---

## Table of Contents

1. [System Overview](#system-overview)
2. [Request Lifecycle](#request-lifecycle)
3. [Component Architecture](#component-architecture)
4. [Middleware Stack](#middleware-stack)
5. [Backend Layer](#backend-layer)
6. [VRAM Management](#vram-management)
7. [Error Handling](#error-handling)
8. [Data Flow Diagrams](#data-flow-diagrams)
9. [Design Decisions](#design-decisions)
10. [Performance Considerations](#performance-considerations)

---

## System Overview

RheaRouter is a production-grade inference gateway that sits between clients and local Ollama models. It provides OpenAI-compatible API, intelligent request management, and observability.

```
┌──────────────────────────────────────────────────────────────┐
│                         Clients                              │
│  (OpenAI SDK, curl, custom apps)                             │
└────────────────────┬─────────────────────────────────────────┘
                     │ HTTP POST /v1/chat/completions
                     ▼
┌──────────────────────────────────────────────────────────────┐
│                    RheaRouter API Server                     │
│                  (FastAPI on port 8000)                      │
├──────────────────────────────────────────────────────────────┤
│  Middleware Stack (executed in order)                        │
│  1. Error Handler        - Catch all exceptions              │
│  2. Request ID           - UUID generation + tracking        │
│  3. Rate Limiter         - Token bucket (60/min, 20/min)     │
│  4. VRAM Flow Valve      - Queueing (1 vision, 2 text)       │
├──────────────────────────────────────────────────────────────┤
│  Chat Endpoint (/v1/chat/completions)                        │
│  - Auto model selection (vision vs text)                     │
│  - Message format conversion                                 │
│  - Token estimation                                          │
├──────────────────────────────────────────────────────────────┤
│  Ollama Adapter (Backend)                                    │
│  - Async HTTP client (httpx)                                 │
│  - Connection pooling (10 keepalive, 20 max)                 │
│  - Retry logic (exponential backoff)                         │
│  - Health checking                                           │
└────────────────────┬─────────────────────────────────────────┘
                     │ HTTP POST /api/generate
                     ▼
┌──────────────────────────────────────────────────────────────┐
│                    Ollama Server (port 11434)                │
│  - Model loading/unloading                                   │
│  - GPU inference                                             │
│  - Model management                                          │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
┌──────────────────────────────────────────────────────────────┐
│                    Local Models (VRAM)                       │
│  Vision: qwen2.5vl:7b, minicpm-v:8b, llava:7b                │
│  Text: llama3.1:8b, qwen3:8b, deepseek-r1:8b                 │
└──────────────────────────────────────────────────────────────┘
```

**Key architectural principles:**
1. **Middleware-driven** - Cross-cutting concerns handled in middleware
2. **Async-first** - Full async/await throughout the stack
3. **Type-safe** - Pydantic models for all data
4. **Resilient** - Retry logic, error handling, graceful degradation
5. **Observable** - Structured logging, request tracking

---

## Request Lifecycle

### Successful Request Flow

```
1. Client sends POST /v1/chat/completions
   ↓
2. ErrorHandlerMiddleware (wraps entire request)
   ↓
3. RequestIDMiddleware generates UUID4
   ↓
4. RateLimiterMiddleware checks tokens
   ├─ Allowed → continue
   └─ Denied → 429 (Retry-After header)
   ↓
5. VRAMFlowValveMiddleware checks slots
   ├─ Vision model → acquire vision semaphore (blocks if full)
   └─ Text model → acquire text semaphore (blocks if full)
   ↓
6. Chat endpoint receives request
   ├─ Validate model (or auto-select)
   ├─ Convert OpenAI messages → Ollama prompt
   └─ Extract images (if multimodal)
   ↓
7. OllamaAdapter sends request
   ├─ Build Ollama payload
   ├─ POST /api/generate with retry logic
   └─ Handle response
   ↓
8. Build OpenAI-compatible response
   ├─ Create ChatCompletionResponse
   ├─ Estimate token usage
   └─ Add metadata (id, created, model)
   ↓
9. Middleware cleanup (reverse order)
   ├─ Release VRAM slot
   ├─ Add X-Request-ID header
   └─ Log completion
   ↓
10. Return 200 OK with JSON response
```

**Timing breakdown** (typical 2s request):
- Middleware overhead: ~1ms
- Model selection: ~0.5ms
- Message conversion: ~0.5ms
- Ollama inference: ~2000ms (dominant)
- Response building: ~1ms
- **Total:** ~2003ms

---

### Error Request Flow

```
1. Client sends invalid request
   ↓
2. ErrorHandlerMiddleware (active)
   ↓
3-4. [Middleware executes normally]
   ↓
5. Chat endpoint raises exception
   Examples:
   - HTTPException(404) - Model not found
   - OllamaError(503) - Ollama unavailable
   - TimeoutError - Request timeout
   ↓
6. ErrorHandlerMiddleware catches exception
   ├─ Map to HTTP status code
   ├─ Build OpenAI error format
   ├─ Include request_id
   └─ Log error with full context
   ↓
7. Return 4xx/5xx with error JSON
```

**Error handling guarantees:**
- All exceptions caught (no 500 without error JSON)
- Request ID always present
- Full logging context
- Proper HTTP status codes

---

## Component Architecture

### File Structure

```
src/
├── api/                      # FastAPI application
│   ├── main.py              # App initialization, middleware registration
│   └── routes/
│       └── chat.py          # Chat completions endpoint
│
├── backend/                  # Ollama integration
│   ├── models.py            # Pydantic models (OpenAI + Ollama)
│   ├── message_utils.py     # Message format conversion
│   └── ollama_adapter.py    # HTTP client with retry logic
│
├── middleware/               # Request processing pipeline
│   ├── request_id.py        # UUID generation
│   ├── rate_limiter.py      # Token bucket algorithm
│   ├── vram_flow_valve.py   # VRAM-aware queueing
│   └── error_handler.py     # Global exception handling
│
├── core/                     # Configuration and utilities
│   └── config.py            # Settings (pydantic-settings)
│
└── observability/            # Logging and monitoring
    └── logging.py           # Structured JSON logging
```

**Dependency graph:**

```
main.py
  ├── routes/chat.py
  │   ├── backend/ollama_adapter.py
  │   │   └── backend/models.py
  │   └── backend/message_utils.py
  │       └── backend/models.py
  │
  ├── middleware/error_handler.py
  ├── middleware/request_id.py
  ├── middleware/rate_limiter.py
  └── middleware/vram_flow_valve.py
      └── backend/models.py

All import:
  ├── core/config.py
  └── observability/logging.py
```

**Key design patterns:**
1. **Dependency Injection** - OllamaAdapter injected into endpoints
2. **Middleware Chain** - Starlette BaseHTTPMiddleware
3. **Strategy Pattern** - Model selection logic
4. **Adapter Pattern** - OpenAI ↔ Ollama translation
5. **Singleton Pattern** - Settings via pydantic-settings

---

## Middleware Stack

### Execution Order

Middleware is registered in **reverse order** due to Starlette's stacking:

```python
# main.py registration order
app.add_middleware(ErrorHandlerMiddleware)    # Executed 1st (outermost)
app.add_middleware(RequestIDMiddleware)       # Executed 2nd
app.add_middleware(RateLimiterMiddleware)     # Executed 3rd
app.add_middleware(VRAMFlowValve)             # Executed 4th (innermost)

# Actual execution:
# Request:  Error → RequestID → RateLimiter → VRAM → Endpoint
# Response: Endpoint → VRAM → RateLimiter → RequestID → Error
```

**Why this order?**
1. **Error Handler** - Must wrap everything to catch all exceptions
2. **Request ID** - Generate early for logging context
3. **Rate Limiter** - Reject before heavy operations
4. **VRAM Flow Valve** - Queue closest to endpoint (after checks)

---

### 1. Error Handler Middleware

**Purpose:** Catch all unhandled exceptions and return OpenAI-compatible errors.

**Implementation:**
```python
class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        try:
            response = await call_next(request)
            return response
        except OllamaError as e:
            # Ollama-specific errors (503, custom codes)
            return self._build_error_response(
                status_code=e.status_code,
                message=e.error,
                error_type="ollama_error",
                error_code=e.error_code,
                request_id=request.state.request_id
            )
        except ConnectionError:
            # Ollama unavailable (503)
            return self._build_error_response(503, "Service unavailable", ...)
        except TimeoutError:
            # Request timeout (504)
            return self._build_error_response(504, "Request timed out", ...)
        except Exception as e:
            # Unexpected errors (500)
            logger.exception("Unhandled exception", extra={...})
            return self._build_error_response(500, "Internal server error", ...)
```

**Error response format:**
```json
{
  "error": {
    "message": "Human-readable message",
    "type": "error_type",
    "code": "error_code",
    "request_id": "uuid"
  }
}
```

**Note:** FastAPI's HTTPException is not caught here (handled by FastAPI before middleware).

---

### 2. Request ID Middleware

**Purpose:** Generate unique UUID4 for every request.

**Implementation:**
```python
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id  # Store for logging

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

**Benefits:**
- Track requests across logs
- Debug specific requests
- Correlation in distributed systems (future)

**Access in code:**
```python
request_id = request.state.request_id
logger.info("Processing request", extra={"request_id": request_id})
```

---

### 3. Rate Limiter Middleware

**Purpose:** Enforce two-tier token bucket rate limiting.

**Algorithm:** Token Bucket
- **Tokens:** Represent request quota
- **Capacity:** Max burst (10 global, 5 per-client)
- **Refill rate:** Tokens/second (1.0 global, 0.33 per-client)

**Implementation:**
```python
class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate
        self.last_refill = time.monotonic()
        self.lock = asyncio.Lock()

    async def consume(self, tokens: int = 1) -> Tuple[bool, float]:
        async with self.lock:
            # Refill tokens based on elapsed time
            now = time.monotonic()
            elapsed = now - self.last_refill
            self.tokens = min(
                self.capacity,
                self.tokens + (elapsed * self.refill_rate)
            )
            self.last_refill = now

            # Try to consume
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True, 0.0  # Allowed
            else:
                # Calculate retry-after
                retry_after = (tokens - self.tokens) / self.refill_rate
                return False, retry_after
```

**Two-tier enforcement:**
```python
class RateLimiterMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        self.global_bucket = TokenBucket(
            capacity=60 + 10,  # 60 req/min + 10 burst
            refill_rate=1.0    # 1 token/sec
        )
        self.client_buckets = {}  # IP → TokenBucket

    async def dispatch(self, request, call_next):
        # Check global limit
        allowed, retry = await self.global_bucket.consume()
        if not allowed:
            return self._rate_limit_response(retry)

        # Check per-client limit
        client_ip = self._get_client_ip(request)
        client_bucket = self._get_or_create_bucket(client_ip)
        allowed, retry = await client_bucket.consume()
        if not allowed:
            return self._rate_limit_response(retry)

        return await call_next(request)
```

**Rate limit response (429):**
```json
{
  "error": {
    "message": "Rate limit exceeded. Try again in 30 seconds.",
    "type": "rate_limit_error",
    "code": "rate_limit_exceeded"
  }
}
```
**Headers:** `Retry-After: 30`

---

### 4. VRAM Flow Valve Middleware

**Purpose:** Prevent VRAM exhaustion by queueing requests.

**Slot allocation:**
- **Vision models:** 1 concurrent slot (semaphore with value 1)
- **Text models:** 2 concurrent slots (semaphore with value 2)

**Implementation:**
```python
class VRAMFlowValve(BaseHTTPMiddleware):
    VISION_MODEL_PATTERNS = ['vl', 'llava', 'minicpm-v', 'vision']

    def __init__(self, app):
        self.vision_slots = asyncio.Semaphore(1)
        self.text_slots = asyncio.Semaphore(2)

    async def dispatch(self, request, call_next):
        # Determine model type
        model = await self._get_model_from_request(request)
        is_vision = self._is_vision_model(model)
        semaphore = self.vision_slots if is_vision else self.text_slots

        # Acquire slot (blocks if none available)
        async with semaphore:
            response = await call_next(request)
            return response  # Slot released automatically
```

**Vision model detection:**
```python
def _is_vision_model(self, model_name: str) -> bool:
    if not model_name:
        return False  # Default to text
    model_lower = model_name.lower()
    return any(pattern in model_lower
               for pattern in self.VISION_MODEL_PATTERNS)
```

**Request body caching:**
```python
async def _get_model_from_request(self, request: Request) -> Optional[str]:
    # Read body
    body_bytes = await request.body()

    # Re-attach for downstream
    async def receive():
        return {"type": "http.request", "body": body_bytes}
    request._receive = receive

    # Parse model
    try:
        data = json.loads(body_bytes)
        return data.get("model")
    except:
        return None  # Default to text
```

**Queueing behavior:**
- Requests **block** (not rejected)
- FIFO processing order
- No timeout (waits indefinitely)

**Example scenario:**
```
Time  Vision Slot  Text Slots  Action
----  -----------  ----------  ------
0s    [R1]         [R2, R3]    All processing
2s    [R4 waiting] [R2, R3]    R4 queued (vision slot full)
3s    [R4 waiting] [R3, R5]    R2 done, R5 starts (text slot)
5s    [R4]         [R3, R5]    R1 done, R4 starts
```

---

## Backend Layer

### Ollama Adapter

**Purpose:** Async HTTP client for Ollama API with retry logic.

**Connection pooling:**
```python
limits = httpx.Limits(
    max_keepalive_connections=10,  # Keep 10 connections alive
    max_connections=20,             # Max 20 total
    keepalive_expiry=30.0           # Keep alive for 30s
)

self.client = httpx.AsyncClient(
    base_url=self.base_url,
    timeout=httpx.Timeout(timeout),
    limits=limits
)
```

**Retry logic:**
```python
async def _request_with_retry(self, method, url, **kwargs):
    attempt = 0
    backoff = self.INITIAL_BACKOFF  # 1.0s

    while attempt < self.MAX_RETRIES:
        try:
            response = await self.client.request(method, url, **kwargs)

            # Check if retryable
            if response.status_code in self.RETRYABLE_CODES:
                raise httpx.HTTPStatusError(...)

            return response

        except (httpx.ConnectError, httpx.TimeoutException) as e:
            attempt += 1
            if attempt >= self.MAX_RETRIES:
                raise  # Exhausted retries

            # Exponential backoff
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, self.MAX_BACKOFF)
            logger.warning(f"Retry {attempt}/{self.MAX_RETRIES}", ...)
```

**Retryable conditions:**
- HTTP 500 (Internal Server Error)
- HTTP 503 (Service Unavailable)
- HTTP 504 (Gateway Timeout)
- `httpx.ConnectError` (connection failed)
- `httpx.TimeoutException` (request timeout)

**Backoff schedule:**
```
Attempt 1: 1.0s delay
Attempt 2: 2.0s delay
Attempt 3: 4.0s delay (max 10s)
```

---

### Message Format Conversion

**OpenAI → Ollama:**

OpenAI uses array of message objects:
```json
[
  {"role": "system", "content": "You are helpful"},
  {"role": "user", "content": "Hello"},
  {"role": "assistant", "content": "Hi there!"},
  {"role": "user", "content": "How are you?"}
]
```

Ollama uses single prompt string:
```
System: You are helpful

User: Hello
Assistant: Hi there!
User: How are you?
```

**Conversion logic:**
```python
def convert_messages_to_prompt(messages: List[ChatMessage]) -> str:
    prompt_parts = []

    # Separate system messages
    system_messages = [m for m in messages if m.role == "system"]
    conversation = [m for m in messages if m.role != "system"]

    # Add system context
    if system_messages:
        system_content = "\n".join(
            self._extract_text_content(m.content)
            for m in system_messages
        )
        prompt_parts.append(f"System: {system_content}\n")

    # Add conversation
    for message in conversation:
        content = self._extract_text_content(message.content)
        role = message.role.capitalize()
        prompt_parts.append(f"{role}: {content}")

    return "\n".join(prompt_parts)
```

**Multimodal content extraction:**
```python
def _extract_text_content(self, content: Union[str, List[dict]]) -> str:
    if isinstance(content, str):
        return content

    # Extract text from multimodal array
    text_parts = []
    for item in content:
        if item.get("type") == "text":
            text_parts.append(item["text"])

    return " ".join(text_parts)
```

---

### Image Handling

**Data URL parsing:**
```python
def extract_images_from_messages(messages: List[ChatMessage]) -> Tuple[List[str], int]:
    images = []

    for message in messages:
        if not isinstance(message.content, list):
            continue

        for item in message.content:
            if item.get("type") == "image_url":
                url = item["image_url"]["url"]

                # Parse data URL: data:image/jpeg;base64,<data>
                if url.startswith("data:"):
                    _, data = url.split(",", 1)
                    images.append(data)  # base64 string

    return images, len(images)
```

**Validation:**
```python
def _validate_image_format(url: str):
    # Extract MIME type
    if not url.startswith("data:image/"):
        raise ValueError("Invalid image URL format")

    mime_part = url.split(";")[0].replace("data:", "")
    image_type = mime_part.split("/")[1]

    if image_type not in ["jpeg", "jpg", "png", "webp", "gif"]:
        raise ValueError(f"Unsupported image format: {image_type}")
```

**Size limit:**
```python
MAX_IMAGE_SIZE_MB = 10

def _validate_image_size(base64_data: str):
    decoded = base64.b64decode(base64_data)
    size_mb = len(decoded) / (1024 * 1024)

    if size_mb > MAX_IMAGE_SIZE_MB:
        raise ValueError(f"Image too large: {size_mb:.1f}MB > {MAX_IMAGE_SIZE_MB}MB")
```

---

## VRAM Management

### Current Strategy (Phase 1)

**Slot-based queueing:**
- Vision: 1 slot (semaphore)
- Text: 2 slots (semaphore)

**Why this works:**
- Prevents VRAM thrashing
- Simple FIFO queueing
- No complex scheduling

**Limitations:**
- Doesn't track actual VRAM usage
- Assumes one model per request
- No preemption

---

### Future Strategy (Phase 2)

**VRAM-aware scheduling** (from existing `ensemble/model_manager.py`):

```python
class VRAMManager:
    def __init__(self):
        self.loaded_models = {}  # model_name → timestamp
        self.swap_cooldown = 5.0  # seconds

    async def acquire_model(self, model_name: str):
        # Check if already loaded
        if model_name in self.loaded_models:
            return

        # Check VRAM availability
        vram_free = self._get_vram_free()
        model_size = self._estimate_model_size(model_name)

        if vram_free < model_size:
            # Unload least-recently-used model
            await self._unload_lru_model()
            await asyncio.sleep(self.swap_cooldown)

        # Load model (Ollama handles this automatically)
        self.loaded_models[model_name] = time.monotonic()

    def _get_vram_free(self) -> int:
        # Query nvidia-smi
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
            capture_output=True, text=True
        )
        return int(result.stdout.strip())
```

**Benefits:**
- Dynamic VRAM tracking
- Smart model swapping
- Cooldown prevents thrashing

---

## Error Handling

### Error Hierarchy

```
Exception
├── HTTPException (FastAPI)
│   ├── 404 Not Found (model not found)
│   ├── 422 Unprocessable Entity (validation)
│   └── 500 Internal Server Error
│
├── OllamaError (custom)
│   ├── status_code
│   ├── error_code
│   ├── error (message)
│   └── retry_after (optional)
│
├── ConnectionError (httpx)
│   └── Ollama unreachable
│
└── TimeoutError (httpx)
    └── Request timeout
```

### Error Mapping

| Exception | HTTP Status | Error Type | Action |
|-----------|-------------|------------|--------|
| `HTTPException(404)` | 404 | `invalid_request_error` | Return error |
| `HTTPException(422)` | 422 | `validation_error` | Return error |
| `OllamaError` | variable | `ollama_error` | Return error |
| `ConnectionError` | 503 | `service_error` | Return error |
| `TimeoutError` | 504 | `timeout_error` | Return error |
| `Exception` | 500 | `internal_error` | Log + return error |

### Retry Strategy

**Automatic retries:**
```python
MAX_RETRIES = 3
RETRYABLE_CODES = {500, 503, 504}
RETRYABLE_EXCEPTIONS = (httpx.ConnectError, httpx.TimeoutException)
```

**Manual retries (client-side):**
```python
# Client should retry on:
# - 429 (Rate limit) → Wait Retry-After seconds
# - 503 (Service unavailable) → Exponential backoff
# - 504 (Timeout) → Exponential backoff
```

**Never retry:**
- 400 (Bad request)
- 404 (Not found)
- 422 (Validation error)

---

## Data Flow Diagrams

### 1. Text Completion Flow

```
Client
  │
  ├─ POST /v1/chat/completions
  │  {
  │    "messages": [{"role": "user", "content": "Hello"}]
  │  }
  │
  ▼
Middleware Stack
  │
  ├─ Generate UUID → request.state.request_id
  ├─ Check rate limit (global → per-client)
  └─ Acquire text slot (semaphore, blocks if full)
  │
  ▼
Chat Endpoint
  │
  ├─ Auto-select model → llama3.1:8b (no images)
  ├─ Validate model → Ollama /api/tags
  ├─ Convert messages → "User: Hello"
  ├─ Build Ollama options → {temperature: 0.7, num_predict: 2048}
  │
  ▼
Ollama Adapter
  │
  ├─ Build payload:
  │  {
  │    "model": "llama3.1:8b",
  │    "prompt": "User: Hello",
  │    "options": {...}
  │  }
  │
  ├─ POST /api/generate (with retry)
  │  ├─ Attempt 1 → Success
  │  └─ Return OllamaGenerateResponse
  │
  ▼
Chat Endpoint (response building)
  │
  ├─ Extract response text
  ├─ Estimate tokens (prompt: 3, completion: 5)
  ├─ Build ChatCompletionResponse
  │  {
  │    "id": "chatcmpl-uuid",
  │    "model": "llama3.1:8b",
  │    "choices": [{
  │      "message": {"role": "assistant", "content": "Hi there!"}
  │    }],
  │    "usage": {"prompt_tokens": 3, "completion_tokens": 5}
  │  }
  │
  ▼
Middleware Cleanup
  │
  ├─ Release text slot
  ├─ Add X-Request-ID header
  └─ Log completion (JSON)
  │
  ▼
Client (200 OK)
```

---

### 2. Vision Completion Flow

```
Client
  │
  ├─ POST /v1/chat/completions
  │  {
  │    "messages": [{
  │      "role": "user",
  │      "content": [
  │        {"type": "text", "text": "What's in this image?"},
  │        {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
  │      ]
  │    }]
  │  }
  │
  ▼
Middleware Stack
  │
  ├─ Generate UUID
  ├─ Check rate limit
  └─ Detect vision model → Acquire vision slot (blocks if busy)
  │
  ▼
Chat Endpoint
  │
  ├─ Extract images → ["<base64-data>"]
  ├─ Auto-select model → minicpm-v:8b (has images)
  ├─ Validate model
  ├─ Convert messages → "User: What's in this image?"
  │
  ▼
Ollama Adapter
  │
  ├─ Build payload:
  │  {
  │    "model": "minicpm-v:8b",
  │    "prompt": "User: What's in this image?",
  │    "images": ["<base64>"],
  │    "options": {...}
  │  }
  │
  ├─ POST /api/generate
  │  └─ Wait 3-5 seconds (vision inference)
  │
  ▼
[Same response building as text]
  │
  ▼
Client (200 OK)
```

**Key difference:** Vision requests queue separately (1 slot vs 2 text slots).

---

### 3. Error Flow

```
Client
  │
  ├─ POST /v1/chat/completions
  │  {"model": "nonexistent:model", "messages": [...]}
  │
  ▼
[Middleware stack processes normally]
  │
  ▼
Chat Endpoint
  │
  ├─ Validate model → Query Ollama /api/tags
  │                  → Model not found
  ├─ Raise HTTPException(404, "Model not found: nonexistent:model")
  │
  ▼
Error Handler Middleware (catches exception)
  │
  ├─ Detect HTTPException
  ├─ Extract request_id from request.state
  ├─ Log error with context
  ├─ Build error response:
  │  {
  │    "error": {
  │      "message": "Model not found: nonexistent:model",
  │      "type": "invalid_request_error",
  │      "code": "model_not_found",
  │      "request_id": "uuid"
  │    }
  │  }
  │
  ▼
Client (404 Not Found)
```

---

## Design Decisions

### 1. Why FastAPI?

**Pros:**
- Native async/await support
- Automatic OpenAPI docs
- Pydantic integration (type safety)
- High performance (Starlette + uvicorn)
- Mature ecosystem

**Alternatives considered:**
- Flask - No native async (would need gevent/eventlet)
- Django - Overkill for API server
- aiohttp - Lower-level, more boilerplate

**Decision:** FastAPI for productivity + performance.

---

### 2. Why httpx over requests?

**Pros:**
- Async-first (requests is sync-only)
- Connection pooling built-in
- HTTP/2 support (future)
- Similar API to requests (easy migration)

**Cons:**
- Slightly less mature than requests

**Decision:** httpx for async compatibility.

---

### 3. Why Token Bucket over Sliding Window?

**Token Bucket:**
- ✅ Allows bursts (important for UX)
- ✅ O(1) operations (just timestamp math)
- ✅ Simple to implement
- ❌ Slightly less precise than sliding window

**Sliding Window:**
- ✅ More precise rate limiting
- ❌ O(n) operations (track all requests)
- ❌ Higher memory (store request timestamps)

**Decision:** Token bucket for simplicity + burst support.

---

### 4. Why Semaphores for VRAM Management?

**Semaphores:**
- ✅ Built-in asyncio primitive
- ✅ Automatic queueing (FIFO)
- ✅ Clean async context manager
- ❌ Doesn't track actual VRAM

**Alternatives:**
- Custom queue + VRAM tracking → More complex, Phase 2

**Decision:** Semaphores for Phase 1 simplicity.

---

### 5. Why In-Memory Rate Limiting?

**In-Memory:**
- ✅ Zero external dependencies
- ✅ O(1) operations
- ✅ Sufficient for 100-500 req/day
- ❌ Doesn't survive restarts
- ❌ Doesn't work for multi-instance

**Redis:**
- ✅ Persistent across restarts
- ✅ Works for multi-instance
- ❌ Extra dependency + maintenance
- ❌ Overkill for personal use

**Decision:** In-memory for Phase 1, upgrade to Redis if traffic > 5K req/day.

---

### 6. Why Middleware Order?

**Chosen order:**
1. Error Handler - Must wrap everything
2. Request ID - Generate early for logging
3. Rate Limiter - Reject before heavy operations
4. VRAM Flow Valve - Queue closest to endpoint

**Why not VRAM → Rate Limiter?**
- Rate limiting is cheaper (just timestamp math)
- No point queueing requests that will be rate-limited

**Decision:** Rate limit before queueing.

---

## Performance Considerations

### Latency Breakdown

**Typical 2s text request:**
```
Request ID generation:     0.1ms
Rate limit check:          0.5ms
VRAM slot acquisition:     0.1ms (if available, else blocks)
Model validation:          0.5ms
Message conversion:        0.3ms
Ollama inference:       2000.0ms ← Dominant
Response building:         0.5ms
Token estimation:          0.2ms
JSON serialization:        0.3ms
-----------------------------------------
Total:                  2002.5ms
```

**Optimization targets:**
- ❌ Middleware overhead (~1.5ms) - Already optimized
- ❌ Message conversion (~0.3ms) - Already fast
- ✅ Ollama inference (~2000ms) - **Future: Speculative decoding (1.5-2x speedup)**

---

### Memory Usage

**Per request:**
- Request object: ~2KB
- Message data: ~1-5KB (text), ~1-10MB (vision)
- Response object: ~2KB
- Logging context: ~1KB

**Steady state (idle):**
- FastAPI app: ~50MB
- httpx client: ~10MB
- Rate limiter buckets: ~1KB per client (~100KB for 100 clients)
- **Total: ~60MB**

**Peak (10 concurrent requests):**
- Request data: 10 × 5KB = 50KB
- VRAM queue: 10 × 2KB = 20KB
- **Total: ~60MB + 70KB**

**VRAM (models):**
- Vision: 5-6GB
- Text: 4-7GB
- **Peak:** 7GB (single model at a time)

---

### Throughput

**Hardware:** Lenovo ThinkPad P16 (RTX A2000 8GB, i9-12950HX)

**Sequential (1 worker):**
- Text: 100-200 req/hour (~30-18s per request avg)
- Vision: 10-20 req/hour (~6-3min per request avg)

**Concurrent:**
- 2 text requests in parallel
- 1 vision request at a time

**Bottleneck:** GPU inference time (not middleware)

---

### Scalability Limits

**Current (Phase 1):**
- **Max:** ~500 req/day (fits within rate limits)
- **Concurrent:** 3 requests (1 vision + 2 text)
- **Clients:** Unlimited (rate limited per-IP)

**Future (Phase 2+):**
- **Multi-GPU:** Support multiple GPUs (model sharding)
- **Multi-Instance:** Redis rate limiting, shared queue
- **Caching:** Response caching for identical requests

---

## Future Architecture (Phase 2-4)

### Phase 2: Intelligent Routing

```
Chat Endpoint
  │
  ├─ Semantic Router (new)
  │  ├─ Analyze prompt semantics
  │  ├─ Classify: vision / reasoning / coding / general
  │  └─ Select best model
  │
  ├─ Fallback Cascade (new)
  │  ├─ Primary model fails → Retry
  │  ├─ Still failing → Try backup model
  │  └─ All fail → 503
  │
  └─ SQLite Logger (new)
     └─ Persist request/response for analytics
```

---

### Phase 3: Advanced Techniques

```
MoA Engine (new)
  ├─ Layer 1: Multi-model debate
  │  ├─ deepseek-r1:8b (reasoning)
  │  ├─ qwen3:8b (math)
  │  └─ nemotron-3-nano:30b (general)
  │
  └─ Layer 2: Aggregator
     └─ Synthesize best answer

Speculative Decoder (new)
  ├─ Draft model (llava:7b) → Fast generation
  └─ Verifier (nemotron:30b) → Acceptance/rejection
```

---

### Phase 4: Observability

```
Prometheus Exporter
  ├─ /metrics endpoint
  ├─ Request metrics (count, duration, errors)
  ├─ VRAM metrics (usage, swaps)
  └─ Model metrics (usage, latency)

Grafana Dashboards
  ├─ System Health
  ├─ Model Performance
  └─ GPU Monitoring
```

---

## Summary

RheaRouter's architecture is designed for:

1. **Production quality** - Middleware stack, error handling, observability
2. **Simplicity** - Minimal dependencies, clear data flow
3. **Extensibility** - Modular design, feature flags
4. **Performance** - Async throughout, connection pooling, VRAM management

**Core insight:** Most complexity is in the **middleware stack**, not the endpoint logic. By handling cross-cutting concerns (rate limiting, VRAM, errors) in middleware, the endpoint code stays clean and focused.

**Next steps:** Phase 2 will add intelligent routing and persistence, building on this solid foundation.

---

**Questions?**
- **API details:** See [API.md](API.md)
- **Setup:** See [QUICKSTART.md](QUICKSTART.md)
- **Code examples:** See [examples/](examples/)
- **General info:** See [README.md](README.md)
