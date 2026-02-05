"""
Technique 1: Weighted Character Voting

All models vote on each character position.
Weights based on historical accuracy.
Best for: Maximum accuracy when time doesn't matter.
"""

from typing import List, Dict, Optional, Union
from pathlib import Path
from dataclasses import dataclass
from PIL import Image

from ..llm_agent import LLMAgent, OCRResult
from ..ocr_wrappers import TesseractOCR, TraditionalOCRResult
from ..alignment import multi_sequence_align, weighted_consensus, find_disagreements
from ..model_manager import ModelManager


@dataclass
class VotingResult:
    """Result from weighted voting consensus."""
    text: str
    confidence: float
    per_char_confidence: List[float]
    time_seconds: float
    models_used: List[str]
    individual_results: Dict[str, str]
    disagreements: List[Dict]


class WeightedVotingConsensus:
    """
    Weighted character-level voting ensemble.

    Runs all extractors (traditional OCR + LLMs), aligns outputs,
    and votes on each character position with historical accuracy weights.
    """

    # Default weights based on benchmark results
    DEFAULT_WEIGHTS = {
        'tesseract': 0.15,
        'easyocr': 0.15,
        'qwen2.5vl:7b': 0.50,
        'minicpm-v:8b': 0.35,
        'llava:7b': 0.15,
    }

    def __init__(self,
                 model_manager: Optional[ModelManager] = None,
                 weights: Optional[Dict[str, float]] = None,
                 use_traditional_ocr: bool = True):
        """
        Initialize weighted voting consensus.

        Args:
            model_manager: Model manager for VRAM-aware loading
            weights: Custom weights for each extractor
            use_traditional_ocr: Whether to include Tesseract/EasyOCR
        """
        self.model_manager = model_manager or ModelManager()
        self.weights = weights or self.DEFAULT_WEIGHTS.copy()
        self.use_traditional_ocr = use_traditional_ocr

        # Initialize extractors
        self.llm_agents = {
            'qwen2.5vl:7b': LLMAgent('qwen2.5vl:7b'),
            'minicpm-v:8b': LLMAgent('minicpm-v:8b'),
            'llava:7b': LLMAgent('llava:7b'),
        }

        if use_traditional_ocr:
            self.tesseract = TesseractOCR()

    def extract(self,
                image: Union[str, Path, Image.Image],
                llm_models: Optional[List[str]] = None) -> VotingResult:
        """
        Extract text using weighted voting across all extractors.

        Args:
            image: Image to extract text from
            llm_models: Which LLM models to use (default: all)

        Returns:
            VotingResult with consensus text and metadata
        """
        import time
        start_time = time.perf_counter()

        results = {}
        used_weights = {}

        # Run traditional OCR (fast, no model swapping needed)
        if self.use_traditional_ocr:
            try:
                tess_result = self.tesseract.extract_text(image)
                if tess_result.success:
                    results['tesseract'] = tess_result.text
                    used_weights['tesseract'] = self.weights.get('tesseract', 0.15)
            except Exception as e:
                print(f"Tesseract failed: {e}")


        # Run LLM models (sequential due to VRAM constraint)
        models_to_run = llm_models or list(self.llm_agents.keys())

        for model_name in models_to_run:
            if model_name not in self.llm_agents:
                continue

            agent = self.llm_agents[model_name]

            # Ensure model is loaded
            if self.model_manager.ensure_loaded(model_name):
                try:
                    result = agent.extract_text(image)
                    if result.success:
                        results[model_name] = result.text
                        used_weights[model_name] = self.weights.get(model_name, 0.25)
                except Exception as e:
                    print(f"{model_name} failed: {e}")

        # Build consensus
        if not results:
            return VotingResult(
                text="",
                confidence=0.0,
                per_char_confidence=[],
                time_seconds=time.perf_counter() - start_time,
                models_used=[],
                individual_results={},
                disagreements=[]
            )

        # Align all texts
        texts = list(results.values())
        sources = list(results.keys())
        weights_list = [used_weights[s] for s in sources]

        aligned = multi_sequence_align(texts)

        # Vote
        consensus_text, char_confidences = weighted_consensus(aligned, weights_list)

        # Find disagreements for analysis
        disagreements = find_disagreements(aligned, sources)

        elapsed = time.perf_counter() - start_time

        return VotingResult(
            text=consensus_text,
            confidence=sum(char_confidences) / len(char_confidences) if char_confidences else 0.0,
            per_char_confidence=char_confidences,
            time_seconds=elapsed,
            models_used=sources,
            individual_results=results,
            disagreements=disagreements
        )

    def set_weight(self, extractor: str, weight: float):
        """Update weight for a specific extractor."""
        self.weights[extractor] = weight

    def get_weights(self) -> Dict[str, float]:
        """Get current weights."""
        return self.weights.copy()
