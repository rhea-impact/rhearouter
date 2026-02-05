"""
Technique 2: Confidence-Escalation Chain

Start with best model (Qwen), escalate if confidence is low.
Best for: Balanced accuracy/speed.
"""

from typing import List, Dict, Optional, Union, Tuple
from pathlib import Path
from dataclasses import dataclass
from PIL import Image

from ..llm_agent import LLMAgent, OCRResult
from ..ocr_wrappers import TesseractOCR, TraditionalOCRResult
from ..alignment import simple_majority_vote
from ..model_manager import ModelManager


@dataclass
class EscalationResult:
    """Result from escalation chain consensus."""
    text: str
    confidence: float
    time_seconds: float
    models_consulted: List[str]
    escalation_reason: Optional[str]
    agreement_achieved: bool
    individual_results: Dict[str, OCRResult]


class EscalationChainConsensus:
    """
    Confidence-based escalation chain.

    Starts with the best model (Qwen). If confidence is below threshold,
    escalates to next model for second opinion. Returns early if high
    confidence or two models agree.
    """

    # Default escalation chain: accuracy order with thresholds
    DEFAULT_CHAIN = [
        ('qwen2.5vl:7b', 0.90),   # Exit if >= 90% confidence
        ('minicpm-v:8b', 0.85),   # Exit if >= 85% confidence
        ('llava:7b', 0.0),        # Always accept (final fallback)
    ]

    def __init__(self,
                 model_manager: Optional[ModelManager] = None,
                 chain: Optional[List[Tuple[str, float]]] = None,
                 use_traditional_ocr_boost: bool = True):
        """
        Initialize escalation chain consensus.

        Args:
            model_manager: Model manager for VRAM-aware loading
            chain: Custom escalation chain as [(model, threshold), ...]
            use_traditional_ocr_boost: Use Tesseract as pre-check
        """
        self.model_manager = model_manager or ModelManager()
        self.chain = chain or self.DEFAULT_CHAIN
        self.use_traditional_ocr_boost = use_traditional_ocr_boost

        # Initialize agents
        self.llm_agents = {}
        for model_name, _ in self.chain:
            self.llm_agents[model_name] = LLMAgent(model_name)

        if use_traditional_ocr_boost:
            self.tesseract = TesseractOCR()

    def extract(self, image: Union[str, Path, Image.Image]) -> EscalationResult:
        """
        Extract text using confidence-based escalation.

        Args:
            image: Image to extract text from

        Returns:
            EscalationResult with consensus text and escalation metadata
        """
        import time
        start_time = time.perf_counter()

        results = {}
        models_consulted = []
        escalation_reason = None

        # Optional: Quick Tesseract check for obvious cases
        tess_text = None
        if self.use_traditional_ocr_boost:
            try:
                tess_result = self.tesseract.extract_text(image)
                if tess_result.success and tess_result.confidence > 0.9:
                    tess_text = tess_result.text
            except Exception:
                pass

        # Run through escalation chain
        previous_result: Optional[OCRResult] = None

        for model_name, confidence_threshold in self.chain:
            # Ensure model is loaded
            if not self.model_manager.ensure_loaded(model_name):
                continue

            agent = self.llm_agents[model_name]
            models_consulted.append(model_name)

            try:
                result = agent.extract_text(image)
                results[model_name] = result

                if not result.success:
                    escalation_reason = f"{model_name} failed"
                    continue

                # Check for early exit conditions
                if result.confidence >= confidence_threshold:
                    # High confidence - return immediately
                    elapsed = time.perf_counter() - start_time
                    return EscalationResult(
                        text=result.text,
                        confidence=result.confidence,
                        time_seconds=elapsed,
                        models_consulted=models_consulted,
                        escalation_reason=None,
                        agreement_achieved=False,
                        individual_results=results
                    )

                # Check for agreement with previous model
                if previous_result is not None:
                    agreement = self._check_agreement(previous_result.text, result.text)
                    if agreement > 0.85:
                        # Two models agree - boost confidence and return
                        boosted_confidence = min(1.0, max(previous_result.confidence, result.confidence) * 1.1)
                        elapsed = time.perf_counter() - start_time
                        return EscalationResult(
                            text=result.text,  # Use latest result
                            confidence=boosted_confidence,
                            time_seconds=elapsed,
                            models_consulted=models_consulted,
                            escalation_reason=None,
                            agreement_achieved=True,
                            individual_results=results
                        )

                # Not confident enough, continue to next model
                escalation_reason = f"{model_name} confidence {result.confidence:.2f} < {confidence_threshold}"
                previous_result = result

            except Exception as e:
                escalation_reason = f"{model_name} error: {str(e)}"

        # Exhausted chain - return best result we have
        elapsed = time.perf_counter() - start_time

        best_result = self._select_best_result(results, tess_text)

        return EscalationResult(
            text=best_result.text if best_result else "",
            confidence=best_result.confidence if best_result else 0.0,
            time_seconds=elapsed,
            models_consulted=models_consulted,
            escalation_reason=escalation_reason,
            agreement_achieved=False,
            individual_results=results
        )

    def _check_agreement(self, text1: str, text2: str) -> float:
        """Check how much two texts agree (0-1)."""
        from difflib import SequenceMatcher

        # Normalize
        t1 = ' '.join(text1.lower().split())
        t2 = ' '.join(text2.lower().split())

        return SequenceMatcher(None, t1, t2).ratio()

    def _select_best_result(self,
                            results: Dict[str, OCRResult],
                            tess_text: Optional[str] = None) -> Optional[OCRResult]:
        """Select the best result from available options."""
        if not results:
            return None

        # Priority order based on chain
        for model_name, _ in self.chain:
            if model_name in results and results[model_name].success:
                result = results[model_name]

                # Boost confidence if Tesseract agrees
                if tess_text and self._check_agreement(result.text, tess_text) > 0.8:
                    result.confidence = min(1.0, result.confidence * 1.05)

                return result

        return None

    def set_threshold(self, model_name: str, threshold: float):
        """Update confidence threshold for a model."""
        self.chain = [
            (m, threshold if m == model_name else t)
            for m, t in self.chain
        ]
