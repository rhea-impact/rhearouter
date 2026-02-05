"""
LLM Agent for RheaRouter Ensemble

Wrapper around Ollama API for vision model inference.
"""

import base64
import time
import requests
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Union
from PIL import Image
from io import BytesIO


@dataclass
class OCRResult:
    """Result from an OCR extraction."""
    text: str
    model: str
    confidence: float
    time_seconds: float
    success: bool
    error: Optional[str] = None
    raw_response: Optional[dict] = field(default=None, repr=False)


class LLMAgent:
    """
    Vision LLM agent for OCR extraction.

    Wraps Ollama API for consistent interface across models.
    """

    # Default OCR prompt optimized for accuracy
    DEFAULT_OCR_PROMPT = """Read and transcribe ALL text in this image exactly as written.
Include every word, number, symbol, and preserve the layout structure.
Output only the transcribed text, nothing else."""

    # Historical accuracy weights from benchmarks
    MODEL_WEIGHTS = {
        'qwen2.5vl:7b': 0.50,   # 95% accuracy - best OCR
        'minicpm-v:8b': 0.35,   # 79% accuracy - good stability
        'llava:7b': 0.15,       # 32% accuracy - fast but weak OCR
    }

    def __init__(self,
                 model_name: str,
                 ollama_url: str = "http://localhost:11434",
                 timeout: int = 120):
        self.model_name = model_name
        self.ollama_url = ollama_url
        self.timeout = timeout
        self.weight = self.MODEL_WEIGHTS.get(model_name, 0.25)

    def _encode_image(self, image: Union[str, Path, Image.Image, bytes]) -> str:
        """Convert image to base64 string."""
        if isinstance(image, (str, Path)):
            with open(image, 'rb') as f:
                return base64.b64encode(f.read()).decode('utf-8')
        elif isinstance(image, Image.Image):
            buffer = BytesIO()
            image.save(buffer, format='PNG')
            return base64.b64encode(buffer.getvalue()).decode('utf-8')
        elif isinstance(image, bytes):
            return base64.b64encode(image).decode('utf-8')
        else:
            raise ValueError(f"Unsupported image type: {type(image)}")

    def extract_text(self,
                     image: Union[str, Path, Image.Image, bytes],
                     prompt: Optional[str] = None) -> OCRResult:
        """
        Extract text from an image using this model.

        Args:
            image: Path to image file, PIL Image, or bytes
            prompt: Custom prompt (uses default OCR prompt if None)

        Returns:
            OCRResult with extracted text and metadata
        """
        prompt = prompt or self.DEFAULT_OCR_PROMPT
        img_base64 = self._encode_image(image)

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "images": [img_base64],
            "stream": False
        }

        start_time = time.perf_counter()

        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )

            elapsed = time.perf_counter() - start_time

            if response.status_code == 200:
                data = response.json()
                text = data.get('response', '')

                # Estimate confidence based on response characteristics
                confidence = self._estimate_confidence(text, data)

                return OCRResult(
                    text=text,
                    model=self.model_name,
                    confidence=confidence,
                    time_seconds=elapsed,
                    success=True,
                    raw_response=data
                )
            else:
                return OCRResult(
                    text='',
                    model=self.model_name,
                    confidence=0.0,
                    time_seconds=elapsed,
                    success=False,
                    error=f"HTTP {response.status_code}: {response.text[:200]}"
                )

        except requests.Timeout:
            elapsed = time.perf_counter() - start_time
            return OCRResult(
                text='',
                model=self.model_name,
                confidence=0.0,
                time_seconds=elapsed,
                success=False,
                error="Request timeout"
            )
        except Exception as e:
            elapsed = time.perf_counter() - start_time
            return OCRResult(
                text='',
                model=self.model_name,
                confidence=0.0,
                time_seconds=elapsed,
                success=False,
                error=str(e)
            )

    def extract_with_context(self,
                             image: Union[str, Path, Image.Image, bytes],
                             context_prompt: str) -> OCRResult:
        """
        Extract text with additional context (e.g., other models' outputs).

        Used in debate/arbitration scenarios.
        """
        return self.extract_text(image, prompt=context_prompt)

    def _estimate_confidence(self, text: str, response_data: dict) -> float:
        """
        Estimate confidence in the OCR result.

        Based on:
        - Text length (very short = suspicious)
        - Model's historical accuracy weight
        - Response characteristics
        """
        base_confidence = self.weight

        # Penalize very short responses
        if len(text.strip()) < 10:
            base_confidence *= 0.5

        # Boost for reasonable length responses
        if 50 < len(text.strip()) < 500:
            base_confidence *= 1.1

        # Check for common failure patterns
        failure_phrases = [
            "i cannot", "i can't", "unable to",
            "no text", "cannot read", "unclear"
        ]
        if any(phrase in text.lower() for phrase in failure_phrases):
            base_confidence *= 0.3

        return min(max(base_confidence, 0.0), 1.0)

    def __repr__(self):
        return f"LLMAgent(model={self.model_name}, weight={self.weight})"
