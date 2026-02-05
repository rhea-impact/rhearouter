"""
Consensus Techniques for RheaRouter Ensemble

Three ensemble techniques for OCR:
1. Weighted Character Voting - Maximum accuracy
2. Confidence-Escalation Chain - Balanced speed/accuracy
3. Socratic Debate - Highest accuracy on degraded images
"""

from .weighted_voting import WeightedVotingConsensus
from .escalation_chain import EscalationChainConsensus
from .socratic_debate import SocraticDebateConsensus

__all__ = [
    "WeightedVotingConsensus",
    "EscalationChainConsensus",
    "SocraticDebateConsensus",
]
