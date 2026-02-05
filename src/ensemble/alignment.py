"""
Sequence Alignment for OCR Voting

Implements Needleman-Wunsch algorithm with OCR-specific scoring.
Used to align multiple OCR outputs for character-level voting.
"""

from typing import List, Tuple, Dict, Optional
from collections import defaultdict
import numpy as np


# OCR confusion matrix - common character confusions
# Pairs that look similar get reduced mismatch penalty
OCR_CONFUSIONS = {
    ('0', 'O'): 0, ('O', '0'): 0,
    ('0', 'o'): 0, ('o', '0'): 0,
    ('1', 'l'): 0, ('l', '1'): 0,
    ('1', 'I'): 0, ('I', '1'): 0,
    ('1', 'i'): 0, ('i', '1'): 0,
    ('l', 'I'): 0, ('I', 'l'): 0,
    ('5', 'S'): -0.5, ('S', '5'): -0.5,
    ('5', 's'): -0.5, ('s', '5'): -0.5,
    ('8', 'B'): -0.5, ('B', '8'): -0.5,
    ('6', 'G'): -0.5, ('G', '6'): -0.5,
    ('2', 'Z'): -0.5, ('Z', '2'): -0.5,
    ('9', 'g'): -0.5, ('g', '9'): -0.5,
    ('c', 'C'): 0, ('C', 'c'): 0,  # Case insensitive
    ('k', 'K'): 0, ('K', 'k'): 0,
    ('m', 'M'): 0, ('M', 'm'): 0,
    ('p', 'P'): 0, ('P', 'p'): 0,
    ('s', 'S'): 0, ('S', 's'): 0,
    ('u', 'U'): 0, ('U', 'u'): 0,
    ('v', 'V'): 0, ('V', 'v'): 0,
    ('w', 'W'): 0, ('W', 'w'): 0,
    ('x', 'X'): 0, ('X', 'x'): 0,
    ('z', 'Z'): 0, ('Z', 'z'): 0,
    ('.', ','): -0.3, (',', '.'): -0.3,  # Punctuation
    ("'", '"'): -0.3, ('"', "'"): -0.3,
    ('-', '_'): -0.3, ('_', '-'): -0.3,
    (' ', ''): -0.5, ('', ' '): -0.5,  # Space vs nothing
}


def needleman_wunsch(seq1: str, seq2: str,
                     match_score: float = 2.0,
                     mismatch_penalty: float = -1.0,
                     gap_penalty: float = -2.0,
                     use_ocr_matrix: bool = True) -> Tuple[str, str]:
    """
    Needleman-Wunsch global sequence alignment with OCR-specific scoring.

    Args:
        seq1: First sequence
        seq2: Second sequence
        match_score: Score for matching characters
        mismatch_penalty: Penalty for mismatched characters
        gap_penalty: Penalty for gaps (insertions/deletions)
        use_ocr_matrix: Whether to use OCR confusion matrix

    Returns:
        Tuple of aligned sequences (with '-' for gaps)
    """
    m, n = len(seq1), len(seq2)

    # Initialize scoring matrix
    dp = np.zeros((m + 1, n + 1))

    # Fill first row and column with gap penalties
    for i in range(m + 1):
        dp[i][0] = i * gap_penalty
    for j in range(n + 1):
        dp[0][j] = j * gap_penalty

    # Fill the matrix
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            char1, char2 = seq1[i - 1], seq2[j - 1]

            if char1 == char2:
                score = match_score
            elif use_ocr_matrix and (char1, char2) in OCR_CONFUSIONS:
                score = OCR_CONFUSIONS[(char1, char2)]
            else:
                score = mismatch_penalty

            dp[i][j] = max(
                dp[i - 1][j - 1] + score,      # Match/mismatch
                dp[i - 1][j] + gap_penalty,     # Gap in seq2
                dp[i][j - 1] + gap_penalty      # Gap in seq1
            )

    # Traceback to build aligned sequences
    aligned1, aligned2 = [], []
    i, j = m, n

    while i > 0 or j > 0:
        if i > 0 and j > 0:
            char1, char2 = seq1[i - 1], seq2[j - 1]

            if char1 == char2:
                score = match_score
            elif use_ocr_matrix and (char1, char2) in OCR_CONFUSIONS:
                score = OCR_CONFUSIONS[(char1, char2)]
            else:
                score = mismatch_penalty

            if dp[i][j] == dp[i - 1][j - 1] + score:
                aligned1.append(char1)
                aligned2.append(char2)
                i -= 1
                j -= 1
            elif i > 0 and dp[i][j] == dp[i - 1][j] + gap_penalty:
                aligned1.append(char1)
                aligned2.append('-')
                i -= 1
            else:
                aligned1.append('-')
                aligned2.append(char2)
                j -= 1
        elif i > 0:
            aligned1.append(seq1[i - 1])
            aligned2.append('-')
            i -= 1
        else:
            aligned1.append('-')
            aligned2.append(seq2[j - 1])
            j -= 1

    return ''.join(reversed(aligned1)), ''.join(reversed(aligned2))


def multi_sequence_align(sequences: List[str]) -> List[str]:
    """
    Align multiple sequences for voting.

    Uses progressive alignment: align first two, then add each subsequent
    sequence to the profile.

    Args:
        sequences: List of strings to align

    Returns:
        List of aligned sequences (same length, with gaps)
    """
    if not sequences:
        return []

    if len(sequences) == 1:
        return sequences.copy()

    # Start with first two sequences
    aligned = list(needleman_wunsch(sequences[0], sequences[1]))

    # Add remaining sequences one by one
    for seq in sequences[2:]:
        # Align new sequence against the "profile" (first aligned sequence)
        _, new_aligned = needleman_wunsch(aligned[0], seq)

        # Propagate gaps to all existing alignments
        new_alignments = []
        for existing in aligned:
            propagated = []
            existing_idx = 0
            for i, char in enumerate(aligned[0]):
                if char == '-':
                    propagated.append('-')
                else:
                    propagated.append(existing[existing_idx] if existing_idx < len(existing) else '-')
                    existing_idx += 1
            new_alignments.append(''.join(propagated))

        aligned = new_alignments + [new_aligned]

    # Ensure all alignments are same length
    max_len = max(len(a) for a in aligned)
    aligned = [a.ljust(max_len, '-') for a in aligned]

    return aligned


def weighted_consensus(aligned_sequences: List[str],
                       weights: List[float],
                       min_agreement: float = 0.5) -> Tuple[str, List[float]]:
    """
    Build consensus from aligned sequences using weighted voting.

    Args:
        aligned_sequences: List of aligned strings (same length)
        weights: Weight for each sequence (sum doesn't need to be 1)
        min_agreement: Minimum weighted agreement to accept a character

    Returns:
        Tuple of (consensus string, per-character confidence scores)
    """
    if not aligned_sequences:
        return "", []

    if len(aligned_sequences) != len(weights):
        raise ValueError("Number of sequences must match number of weights")

    consensus = []
    confidences = []

    # Normalize weights
    total_weight = sum(weights)
    norm_weights = [w / total_weight for w in weights]

    seq_len = len(aligned_sequences[0])

    for pos in range(seq_len):
        # Collect votes at this position
        votes: Dict[str, float] = defaultdict(float)

        for seq, weight in zip(aligned_sequences, norm_weights):
            char = seq[pos] if pos < len(seq) else '-'
            if char != '-':  # Don't vote for gaps
                votes[char] += weight

        if votes:
            # Find winner
            winner = max(votes.items(), key=lambda x: x[1])
            char, vote_share = winner

            if vote_share >= min_agreement:
                consensus.append(char)
                confidences.append(vote_share)
            else:
                # Low agreement - still use winner but mark low confidence
                consensus.append(char)
                confidences.append(vote_share)
        else:
            # All gaps - skip this position (don't add to consensus)
            pass

    return ''.join(consensus), confidences


def simple_majority_vote(texts: List[str]) -> Tuple[str, float]:
    """
    Simple majority voting without alignment.

    Best for texts that are very similar (just minor character differences).

    Args:
        texts: List of OCR outputs to vote on

    Returns:
        Tuple of (consensus text, agreement ratio)
    """
    if not texts:
        return "", 0.0

    if len(texts) == 1:
        return texts[0], 1.0

    # For very similar texts, use the most common one
    from collections import Counter
    normalized = [' '.join(t.split()) for t in texts]
    counts = Counter(normalized)
    winner, count = counts.most_common(1)[0]

    agreement = count / len(texts)

    return winner, agreement


def character_level_vote(texts: List[str], weights: Optional[List[float]] = None) -> str:
    """
    Character-level voting with automatic alignment.

    Convenience wrapper that combines alignment and voting.

    Args:
        texts: List of OCR outputs
        weights: Optional weights for each text (equal if None)

    Returns:
        Consensus string
    """
    if not texts:
        return ""

    if weights is None:
        weights = [1.0] * len(texts)

    # Align sequences
    aligned = multi_sequence_align(texts)

    # Vote
    consensus, _ = weighted_consensus(aligned, weights)

    return consensus


def find_disagreements(aligned_sequences: List[str],
                       source_names: List[str]) -> List[Dict]:
    """
    Find positions where sequences disagree.

    Useful for debate/arbitration to highlight conflicts.

    Args:
        aligned_sequences: Aligned OCR outputs
        source_names: Names of sources (e.g., ['tesseract', 'qwen', 'minicpm'])

    Returns:
        List of disagreement dicts with position, context, and candidates
    """
    disagreements = []

    if not aligned_sequences:
        return disagreements

    seq_len = len(aligned_sequences[0])

    for pos in range(seq_len):
        chars_at_pos = [seq[pos] for seq in aligned_sequences]

        # Filter out gaps for comparison
        non_gap_chars = [c for c in chars_at_pos if c != '-']

        # Check for disagreement
        if len(set(non_gap_chars)) > 1:
            # Get context (5 chars before and after)
            start = max(0, pos - 5)
            end = min(seq_len, pos + 6)

            context_samples = [seq[start:end] for seq in aligned_sequences]

            disagreements.append({
                'position': pos,
                'candidates': list(zip(source_names, chars_at_pos)),
                'context': context_samples,
            })

    return disagreements
