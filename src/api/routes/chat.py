"""OpenAI-compatible chat completions endpoint"""

import time
from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Depends

from src.core.config import get_settings
from src.backend.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatCompletionChoice,
    ChatMessage,
    UsageInfo,
    OllamaError
)
from src.backend.message_utils import (
    convert_messages_to_prompt,
    extract_images_from_messages,
    estimate_tokens,
    build_ollama_options
)
from src.backend.ollama_adapter import OllamaAdapter
from src.core.router import get_router
from src.core.persistence import get_request_logger
from src.observability.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["chat"])

# Global OllamaAdapter instance (initialized in lifespan)
_ollama_adapter: Optional[OllamaAdapter] = None


def get_ollama_adapter() -> OllamaAdapter:
    """Dependency to get OllamaAdapter instance"""
    if _ollama_adapter is None:
        raise HTTPException(
            status_code=503,
            detail="Ollama adapter not initialized"
        )
    return _ollama_adapter


def set_ollama_adapter(adapter: OllamaAdapter):
    """Set global OllamaAdapter instance (called from lifespan)"""
    global _ollama_adapter
    _ollama_adapter = adapter


@router.post("/chat/completions", response_model=ChatCompletionResponse)
async def create_chat_completion(
    request: Request,
    body: ChatCompletionRequest,
    adapter: OllamaAdapter = Depends(get_ollama_adapter)
):
    """
    Create a chat completion (OpenAI-compatible endpoint).
    
    Args:
        request: FastAPI request (for request ID)
        body: Chat completion request
        adapter: Ollama backend adapter
        
    Returns:
        ChatCompletionResponse with generated message
        
    Raises:
        HTTPException: On validation or backend errors
    """
    request_id = getattr(request.state, "request_id", "unknown")
    start_time = time.time()
    
    try:
        # Extract images from messages
        images, image_count = extract_images_from_messages(body.messages)

        # Use intelligent router for model selection
        router = get_router(adapter)
        try:
            model, request_type = await router.select_model(
                messages=body.messages,
                requested_model=body.model,
                has_images=bool(images)
            )
            logger.info("Router selected model", extra={
                "request_id": request_id,
                "model": model,
                "request_type": request_type.value,
                "has_images": bool(images),
                "user_specified": bool(body.model)
            })
        except ValueError as e:
            # User requested unavailable model
            logger.warning("Model selection failed", extra={
                "request_id": request_id,
                "error": str(e)
            })
            raise HTTPException(status_code=404, detail=str(e))
        except RuntimeError as e:
            # No models available for request type
            logger.error("No models available", extra={
                "request_id": request_id,
                "error": str(e)
            })
            raise HTTPException(status_code=503, detail=str(e))
        
        # Convert messages to Ollama format
        prompt = convert_messages_to_prompt(body.messages)
        
        # Build Ollama options
        options = build_ollama_options(
            temperature=body.temperature,
            top_p=body.top_p,
            stop=body.stop,
            max_tokens=body.max_tokens
        )
        
        logger.info("Generating completion", extra={
            "request_id": request_id,
            "model": model,
            "has_images": bool(images),
            "message_count": len(body.messages)
        })
        
        # Call Ollama backend
        ollama_response = await adapter.generate(
            model=model,
            prompt=prompt,
            images=images if images else None,
            options=options
        )
        
        elapsed = time.time() - start_time
        
        # Estimate token usage
        prompt_tokens = estimate_tokens(prompt)
        completion_tokens = estimate_tokens(ollama_response.response)
        total_tokens = prompt_tokens + completion_tokens
        
        # Build OpenAI-compatible response
        response = ChatCompletionResponse(
            id=f"chatcmpl-{request_id}",
            object="chat.completion",
            created=int(time.time()),
            model=model,
            choices=[
                ChatCompletionChoice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content=ollama_response.response
                    ),
                    finish_reason="stop" if ollama_response.done else "length"
                )
            ],
            usage=UsageInfo(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens
            )
        )
        
        logger.info("Completion successful", extra={
            "request_id": request_id,
            "model": model,
            "elapsed_seconds": round(elapsed, 3),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens
        })

        # Log request to database
        request_logger = get_request_logger()
        request_logger.log_request(
            request_id=request_id,
            endpoint="/v1/chat/completions",
            model_requested=body.model,
            model_used=model,
            request_type=request_type.value,
            duration_ms=elapsed * 1000,
            tokens_prompt=prompt_tokens,
            tokens_completion=completion_tokens,
            tokens_total=total_tokens,
            has_images=bool(images)
        )

        return response
        
    except OllamaError as e:
        # Log error to database
        elapsed = time.time() - start_time
        request_logger = get_request_logger()
        request_logger.log_request(
            request_id=request_id,
            endpoint="/v1/chat/completions",
            model_requested=body.model,
            model_used=model if 'model' in locals() else "unknown",
            duration_ms=elapsed * 1000,
            error_type="ollama_error",
            error_message=str(e.error)
        )

        # OllamaError will be caught by ErrorHandlerMiddleware
        logger.error("Ollama backend error", extra={
            "request_id": request_id,
            "error": e.error,
            "error_code": e.error_code,
            "status_code": e.status_code
        })
        raise
        
    except HTTPException:
        # Re-raise HTTPExceptions (like 404 model not found)
        raise
        
    except Exception as e:
        # Unexpected errors will be caught by ErrorHandlerMiddleware
        logger.error("Unexpected error in chat completion", extra={
            "request_id": request_id,
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise
