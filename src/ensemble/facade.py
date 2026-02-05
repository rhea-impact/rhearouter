"""
EnsembleOCR Facade - Main Entry Point

The "Queen" ensemble system that beats individual vision models
through intelligent multi-agent debate and consensus.
"""

from typing import Union, Optional, Dict, Any
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from PIL import Image

from .model_manager import ModelManager
from .consensus.weighted_voting import WeightedVotingConsensus, VotingResult
from .consensus.escalation_chain import EscalationChainConsensus, EscalationResult
from .consensus.socratic_debate import SocraticDebateConsensus, DebateResult


class EnsembleTechnique(Enum):
    """Available ensemble techniques."""
    WEIGHTED_VOTING = "weighted_voting"
    ESCALATION_CHAIN = "escalation_chain"
    SOCRATIC_DEBATE = "socratic_debate"
    AUTO = "auto"


@dataclass
class EnsembleResult:
    """Unified result from any ensemble technique."""
    text: str
    confidence: float
    time_seconds: float
    technique_used: str
    models_used: list
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)


class EnsembleOCR:
    """
    Main entry point for RheaRouter Ensemble OCR.

    The "Queen" that orchestrates multiple vision models to achieve
    superior accuracy through teamwork.

    Usage:
        ensemble = EnsembleOCR()

        # Auto-select best technique
        result = ensemble.extract("image.png")

        # Or specify technique
        result = ensemble.extract("image.png", technique="socratic_debate")
    """

    def __init__(self,
                 default_technique: EnsembleTechnique = EnsembleTechnique.AUTO,
                 king_model: str = 'qwen2.5vl:7b',
                 use_traditional_ocr: bool = True):
        """
        Initialize EnsembleOCR.

        Args:
            default_technique: Default ensemble technique to use
            king_model: Model for final arbitration in Socratic debate
            use_traditional_ocr: Include Tesseract/EasyOCR in ensemble
        """
        self.default_technique = default_technique
        self.king_model = king_model
        self.use_traditional_ocr = use_traditional_ocr

        # Shared model manager
        self.model_manager = ModelManager()

        # Initialize techniques
        self.weighted_voting = WeightedVotingConsensus(
            model_manager=self.model_manager,
            use_traditional_ocr=use_traditional_ocr
        )

        self.escalation_chain = EscalationChainConsensus(
            model_manager=self.model_manager,
            use_traditional_ocr_boost=use_traditional_ocr
        )

        self.socratic_debate = SocraticDebateConsensus(
            model_manager=self.model_manager,
            king_model=king_model,
            use_traditional_ocr=use_traditional_ocr
        )

    def extract(self,
                image: Union[str, Path, Image.Image],
                technique: Optional[Union[EnsembleTechnique, str]] = None) -> EnsembleResult:
        """
        Extract text from image using ensemble methods.

        Args:
            image: Path to image, PIL Image, or image bytes
            technique: Ensemble technique to use (default: auto-select)

        Returns:
            EnsembleResult with extracted text and metadata
        """
        # Normalize technique
        if technique is None:
            technique = self.default_technique
        elif isinstance(technique, str):
            technique = EnsembleTechnique(technique)

        # Auto-select based on image characteristics (placeholder - could analyze image)
        if technique == EnsembleTechnique.AUTO:
            technique = self._auto_select_technique(image)

        # Run selected technique
        if technique == EnsembleTechnique.WEIGHTED_VOTING:
            result = self._run_weighted_voting(image)
        elif technique == EnsembleTechnique.ESCALATION_CHAIN:
            result = self._run_escalation_chain(image)
        elif technique == EnsembleTechnique.SOCRATIC_DEBATE:
            result = self._run_socratic_debate(image)
        else:
            raise ValueError(f"Unknown technique: {technique}")

        return result

    def _auto_select_technique(self, image: Union[str, Path, Image.Image]) -> EnsembleTechnique:
        """
        Auto-select best technique based on context.

        Future: Could analyze image quality to choose technique.
        For now, defaults to balanced escalation chain.
        """
        # Default to escalation chain for balance of speed/accuracy
        return EnsembleTechnique.ESCALATION_CHAIN

    def _run_weighted_voting(self, image: Union[str, Path, Image.Image]) -> EnsembleResult:
        """Run weighted voting technique."""
        result: VotingResult = self.weighted_voting.extract(image)

        return EnsembleResult(
            text=result.text,
            confidence=result.confidence,
            time_seconds=result.time_seconds,
            technique_used="weighted_voting",
            models_used=result.models_used,
            success=len(result.text) > 0,
            metadata={
                "per_char_confidence": result.per_char_confidence,
                "disagreements": result.disagreements,
                "individual_results": result.individual_results,
            }
        )

    def _run_escalation_chain(self, image: Union[str, Path, Image.Image]) -> EnsembleResult:
        """Run escalation chain technique."""
        result: EscalationResult = self.escalation_chain.extract(image)

        return EnsembleResult(
            text=result.text,
            confidence=result.confidence,
            time_seconds=result.time_seconds,
            technique_used="escalation_chain",
            models_used=result.models_consulted,
            success=len(result.text) > 0,
            metadata={
                "escalation_reason": result.escalation_reason,
                "agreement_achieved": result.agreement_achieved,
            }
        )

    def _run_socratic_debate(self, image: Union[str, Path, Image.Image]) -> EnsembleResult:
        """Run Socratic debate technique."""
        result: DebateResult = self.socratic_debate.extract(image)

        return EnsembleResult(
            text=result.text,
            confidence=result.confidence,
            time_seconds=result.time_seconds,
            technique_used="socratic_debate",
            models_used=result.models_participated,
            success=len(result.text) > 0,
            metadata={
                "king_model": result.king_model,
                "num_rounds": result.num_rounds,
                "debate_history": [
                    {"round": r.round_number, "model": r.model, "confidence": r.confidence}
                    for r in result.debate_history
                ],
                "disagreements_resolved": result.disagreements_resolved,
                "initial_results": result.initial_results,
            }
        )

    def compare_techniques(self, image: Union[str, Path, Image.Image]) -> Dict[str, EnsembleResult]:
        """
        Run all techniques and compare results.

        Useful for benchmarking and analysis.

        Args:
            image: Image to process

        Returns:
            Dict mapping technique name to result
        """
        results = {}

        for technique in [
            EnsembleTechnique.WEIGHTED_VOTING,
            EnsembleTechnique.ESCALATION_CHAIN,
            EnsembleTechnique.SOCRATIC_DEBATE
        ]:
            results[technique.value] = self.extract(image, technique)

        return results

    def get_status(self) -> Dict[str, Any]:
        """Get current ensemble status."""
        return {
            "model_manager": self.model_manager.get_status(),
            "default_technique": self.default_technique.value,
            "king_model": self.king_model,
            "use_traditional_ocr": self.use_traditional_ocr,
        }


# Convenience function for quick use
def extract_text(image: Union[str, Path, Image.Image],
                 technique: str = "auto") -> str:
    """
    Quick extraction using default ensemble settings.

    Args:
        image: Path to image or PIL Image
        technique: "weighted_voting", "escalation_chain", "socratic_debate", or "auto"

    Returns:
        Extracted text string
    """
    ensemble = EnsembleOCR()
    result = ensemble.extract(image, technique)
    return result.text
