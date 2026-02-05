"""
RheaRouter Ensemble - Multi-Agent Debate System for OCR

A "Queen" ensemble system that beats individual vision models through
intelligent multi-agent debate and consensus mechanisms.
"""

from .facade import EnsembleOCR
from .model_manager import ModelManager
from .llm_agent import LLMAgent

__version__ = "0.1.0"
__all__ = ["EnsembleOCR", "ModelManager", "LLMAgent"]
