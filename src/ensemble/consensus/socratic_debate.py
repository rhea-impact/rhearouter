"""
Technique 3: Socratic Debate with King Decoder

Multi-round debate where models see each other's outputs and
are challenged to verify/correct. Qwen2.5-VL (King) arbitrates.

Best for: Critical documents, highest accuracy on severe degradation.
"""

from typing import List, Dict, Optional, Union
from pathlib import Path
from dataclasses import dataclass, field
from PIL import Image

from ..llm_agent import LLMAgent, OCRResult
from ..ocr_wrappers import TesseractOCR
from ..alignment import find_disagreements, multi_sequence_align
from ..model_manager import ModelManager


@dataclass
class DebateRound:
    """A single round of debate."""
    round_number: int
    model: str
    input_prompt: str
    output: str
    confidence: float


@dataclass
class DebateResult:
    """Result from Socratic debate consensus."""
    text: str
    confidence: float
    time_seconds: float
    king_model: str
    models_participated: List[str]
    num_rounds: int
    debate_history: List[DebateRound] = field(default_factory=list)
    disagreements_resolved: List[Dict] = field(default_factory=list)
    initial_results: Dict[str, str] = field(default_factory=dict)


class SocraticDebateConsensus:
    """
    Multi-round Socratic debate with King Decoder arbitration.

    Phase 1: All models extract independently
    Phase 2: Models see others' outputs and revise (up to max_rounds)
    Phase 3: King decoder (Qwen2.5-VL) makes final judgment
    """

    # Debate prompt template
    DEBATE_PROMPT = """Multiple OCR systems analyzed this image. Here are their readings:

{candidates}

DISAGREEMENTS FOUND:
{disagreements}

Your task:
1. Examine the image carefully
2. For each disagreement, determine the correct reading by looking at the actual image
3. Consider:
   - Visual evidence (what do you see?)
   - Semantic plausibility (does it make sense in context?)
   - Common OCR errors (0/O, 1/l/I, 5/S)

Output your corrected transcription. For any corrections, note: [CORRECTED: X -> Y]
Then provide the FINAL complete text."""

    # King arbitration prompt
    KING_PROMPT = """As the final arbiter, you must resolve the remaining disagreements between OCR systems.

CANDIDATE READINGS:
{candidates}

UNRESOLVED DISAGREEMENTS:
{disagreements}

DEBATE HISTORY:
{debate_history}

Your final task:
1. Look at the image one more time
2. For each unresolved disagreement, make the final call
3. Prioritize accuracy over speed - every character matters
4. For numbers, codes, and serial numbers, verify each character individually

Output the FINAL, AUTHORITATIVE transcription.
Mark any corrections: [FINAL: X -> Y, reason]"""

    def __init__(self,
                 model_manager: Optional[ModelManager] = None,
                 king_model: str = 'qwen2.5vl:7b',
                 debate_models: Optional[List[str]] = None,
                 max_rounds: int = 2,
                 use_traditional_ocr: bool = True):
        """
        Initialize Socratic debate consensus.

        Args:
            model_manager: Model manager for VRAM-aware loading
            king_model: Model to use for final arbitration
            debate_models: Models to participate in debate
            max_rounds: Maximum debate rounds (1-3 recommended)
            use_traditional_ocr: Include Tesseract/EasyOCR in initial extraction
        """
        self.model_manager = model_manager or ModelManager()
        self.king_model = king_model
        self.debate_models = debate_models or ['minicpm-v:8b', 'llava:7b']
        self.max_rounds = max_rounds
        self.use_traditional_ocr = use_traditional_ocr

        # Ensure king is not in debate models (it arbitrates, doesn't debate)
        self.debate_models = [m for m in self.debate_models if m != king_model]

        # Initialize all agents
        all_models = set([king_model] + self.debate_models)
        self.llm_agents = {m: LLMAgent(m) for m in all_models}

        if use_traditional_ocr:
            self.tesseract = TesseractOCR()

    def extract(self, image: Union[str, Path, Image.Image]) -> DebateResult:
        """
        Extract text using multi-round Socratic debate.

        Args:
            image: Image to extract text from

        Returns:
            DebateResult with final consensus and debate history
        """
        import time
        start_time = time.perf_counter()

        # Phase 1: Initial extraction from all sources
        initial_results = self._initial_extraction(image)

        if not initial_results:
            return DebateResult(
                text="",
                confidence=0.0,
                time_seconds=time.perf_counter() - start_time,
                king_model=self.king_model,
                models_participated=[],
                num_rounds=0
            )

        # Find initial disagreements
        texts = list(initial_results.values())
        sources = list(initial_results.keys())
        aligned = multi_sequence_align(texts)
        disagreements = find_disagreements(aligned, sources)

        debate_history = []
        current_results = initial_results.copy()

        # Phase 2: Debate rounds
        for round_num in range(self.max_rounds):
            if not disagreements:
                break  # Consensus reached

            # Each debate model reviews and revises
            for model_name in self.debate_models:
                if model_name not in self.llm_agents:
                    continue

                if not self.model_manager.ensure_loaded(model_name):
                    continue

                # Build debate prompt
                prompt = self._build_debate_prompt(current_results, disagreements)

                agent = self.llm_agents[model_name]
                result = agent.extract_with_context(image, prompt)

                if result.success:
                    debate_history.append(DebateRound(
                        round_number=round_num + 1,
                        model=model_name,
                        input_prompt=prompt[:500] + "...",  # Truncate for storage
                        output=result.text,
                        confidence=result.confidence
                    ))

                    current_results[model_name] = result.text

            # Recalculate disagreements
            texts = list(current_results.values())
            sources = list(current_results.keys())
            aligned = multi_sequence_align(texts)
            disagreements = find_disagreements(aligned, sources)

        # Phase 3: King arbitration
        if not self.model_manager.ensure_loaded(self.king_model):
            # Fallback: return best result without king
            best_text = current_results.get(self.debate_models[0], list(current_results.values())[0])
            return DebateResult(
                text=best_text,
                confidence=0.7,
                time_seconds=time.perf_counter() - start_time,
                king_model=self.king_model,
                models_participated=list(current_results.keys()),
                num_rounds=len(set(d.round_number for d in debate_history)),
                debate_history=debate_history,
                disagreements_resolved=disagreements,
                initial_results=initial_results
            )

        # King makes final judgment
        king_prompt = self._build_king_prompt(current_results, disagreements, debate_history)
        king_agent = self.llm_agents[self.king_model]
        king_result = king_agent.extract_with_context(image, king_prompt)

        elapsed = time.perf_counter() - start_time

        return DebateResult(
            text=king_result.text if king_result.success else "",
            confidence=king_result.confidence if king_result.success else 0.0,
            time_seconds=elapsed,
            king_model=self.king_model,
            models_participated=list(current_results.keys()) + [self.king_model],
            num_rounds=len(set(d.round_number for d in debate_history)),
            debate_history=debate_history,
            disagreements_resolved=disagreements,
            initial_results=initial_results
        )

    def _initial_extraction(self, image: Union[str, Path, Image.Image]) -> Dict[str, str]:
        """Run initial extraction from all sources."""
        results = {}

        # Traditional OCR
        if self.use_traditional_ocr:
            try:
                tess_result = self.tesseract.extract_text(image)
                if tess_result.success:
                    results['tesseract'] = tess_result.text
            except Exception:
                pass


        # LLM models
        for model_name in self.debate_models:
            if not self.model_manager.ensure_loaded(model_name):
                continue

            agent = self.llm_agents[model_name]
            try:
                result = agent.extract_text(image)
                if result.success:
                    results[model_name] = result.text
            except Exception:
                pass

        return results

    def _build_debate_prompt(self, results: Dict[str, str], disagreements: List[Dict]) -> str:
        """Build prompt for debate round."""
        candidates = "\n".join([
            f"[{source}]: {text[:500]}..." if len(text) > 500 else f"[{source}]: {text}"
            for source, text in results.items()
        ])

        if disagreements:
            disagreement_text = "\n".join([
                f"Position {d['position']}: {', '.join([f'{src}={char}' for src, char in d['candidates']])}"
                for d in disagreements[:10]  # Limit to 10 most important
            ])
        else:
            disagreement_text = "No major disagreements found."

        return self.DEBATE_PROMPT.format(
            candidates=candidates,
            disagreements=disagreement_text
        )

    def _build_king_prompt(self,
                           results: Dict[str, str],
                           disagreements: List[Dict],
                           debate_history: List[DebateRound]) -> str:
        """Build prompt for king arbitration."""
        candidates = "\n".join([
            f"[{source}]: {text[:300]}..."
            for source, text in results.items()
        ])

        if disagreements:
            disagreement_text = "\n".join([
                f"Position {d['position']}: {', '.join([f'{src}={char}' for src, char in d['candidates']])}"
                for d in disagreements[:10]
            ])
        else:
            disagreement_text = "All sources now agree."

        history_text = "\n".join([
            f"Round {r.round_number}, {r.model}: {r.output[:200]}..."
            for r in debate_history[-6:]  # Last 6 entries
        ]) if debate_history else "No debate history."

        return self.KING_PROMPT.format(
            candidates=candidates,
            disagreements=disagreement_text,
            debate_history=history_text
        )
