"""Pydantic models for OpenAI and Ollama API formats"""

from pydantic import BaseModel, Field
from typing import List, Optional, Union, Literal
from datetime import datetime


# OpenAI-compatible request models

class ChatMessage(BaseModel):
    """Chat message with role and content"""
    role: Literal["system", "user", "assistant"]
    content: Union[str, List[dict]]  # String or multimodal content
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request"""
    model: Optional[str] = None  # Use default if not specified
    messages: List[ChatMessage]
    temperature: Optional[float] = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=2048, ge=1, le=32000)
    stream: bool = False
    top_p: Optional[float] = Field(default=1.0, ge=0.0, le=1.0)
    stop: Optional[List[str]] = None


# OpenAI-compatible response models

class ChatCompletionChoice(BaseModel):
    """Single completion choice"""
    index: int
    message: ChatMessage
    finish_reason: Literal["stop", "length", "error"]


class UsageInfo(BaseModel):
    """Token usage information"""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response"""
    id: str  # Generated: "chatcmpl-{uuid}"
    object: Literal["chat.completion"] = "chat.completion"
    created: int  # Unix timestamp
    model: str
    choices: List[ChatCompletionChoice]
    usage: UsageInfo


# Internal Ollama models

class OllamaGenerateRequest(BaseModel):
    """Request for Ollama /api/generate endpoint"""
    model: str
    prompt: str
    images: Optional[List[str]] = None  # Base64 encoded
    stream: bool = False
    options: Optional[dict] = None  # Temperature, etc.


class OllamaGenerateResponse(BaseModel):
    """Response from Ollama /api/generate endpoint"""
    model: str
    created_at: str
    response: str
    done: bool
    context: Optional[List[int]] = None
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_duration: Optional[int] = None


# Error models

class OllamaError(Exception):
    """Exception for Ollama API errors"""

    def __init__(self, error: str, error_code: str, status_code: int, retry_after: Optional[int] = None):
        self.error = error
        self.error_code = error_code
        self.status_code = status_code
        self.retry_after = retry_after
        super().__init__(error)


# Multimodal content models

class ImageContent(BaseModel):
    """Image content in multimodal message"""
    type: Literal["image_url"]
    image_url: dict  # {"url": "data:image/jpeg;base64,..."}


class TextContent(BaseModel):
    """Text content in multimodal message"""
    type: Literal["text"]
    text: str
