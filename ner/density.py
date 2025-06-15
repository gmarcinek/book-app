# density.py
"""
Utility functions for estimating local text density and mapping it
to a target chunk size for TextChunker.

The module exposes small, self‑contained helpers that keep the main
chunker.py lean:

• ``estimate_density(tokens)`` – returns (entropy_ratio, lexical_diversity).
• ``is_legalese(tokens)`` – heuristic flag for Polish legal language.
• ``target_chunk_tokens(...)`` – maps density → desired chunk size
  in the 2 k–10 k token band, with optional legal boost.
• ``sliding_densities(...)`` – generator over a token list producing
  local density snapshots for a sliding window.

All calculations are intentionally lightweight (gzip + set()) so they
can run on thousands of windows without noticeable overhead.
"""
from __future__ import annotations

import gzip
import re
from typing import Iterable, List, Tuple

# ---------------------------------------------------------------------------
#  Regular expressions & constants
# ---------------------------------------------------------------------------

LEGAL_RE = re.compile(
    r"\b(art\.|§|ust\.|paragraf|w\s+brzmieniu|na\s+podstawie|pkt\.)\b",
    re.IGNORECASE,
)

__all__ = [
    "estimate_density",
    "is_legalese",
    "target_chunk_tokens",
    "sliding_densities",
]

# ---------------------------------------------------------------------------
#  Low‑level density metrics
# ---------------------------------------------------------------------------

def _entropy_ratio(tokens: List[str]) -> float:
    """Approximate compression entropy ratio for the token window."""
    if not tokens:
        return 0.0
    raw = " ".join(tokens).encode("utf-8", "ignore")
    if not raw:
        return 0.0
    comp = gzip.compress(raw)
    return len(comp) / len(raw) if raw else 0.0


def _lexical_diversity(tokens: List[str]) -> float:
    """Return unique_tokens / total_tokens for the window."""
    if not tokens:
        return 0.0
    return len(set(tokens)) / len(tokens)


# ---------------------------------------------------------------------------
#  Public helpers
# ---------------------------------------------------------------------------

def estimate_density(tokens: List[str]) -> Tuple[float, float]:
    """Return (entropy_ratio, lexical_diversity) for the given token window."""
    return _entropy_ratio(tokens), _lexical_diversity(tokens)


def is_legalese(tokens: List[str], threshold: float = 0.02) -> bool:
    """Heuristically decide whether the window looks like legal language."""
    if not tokens:
        return False
    matches = sum(1 for t in tokens if LEGAL_RE.search(t))
    return (matches / len(tokens)) >= threshold


def target_chunk_tokens(
    entropy: float,
    lex_div: float,
    legal: bool = False,
    *,
    min_tokens: int = 2000,
    max_tokens: int = 10000,
    d_low: float = 0.45,
    d_high: float = 0.60,
    dense_size: int = 3000,
    loose_size: int = 10000,
    legal_multiplier: float = 0.7,
) -> int:
    """Map density metrics to a desired chunk size in tokens.

    • Low density  → ``loose_size``
    • High density → ``dense_size``
    • Everything in between is interpolated linearly.
    • ``legal`` flag contracts the size by ``legal_multiplier``.
    """
    # Pick the strongest density indicator to drive interpolation
    dens_val = max(entropy, lex_div)

    if entropy <= d_low and lex_div <= 0.30:
        base = loose_size
    elif entropy >= d_high or lex_div >= 0.40:
        base = dense_size
    else:
        # Linear interpolation between loose_size ↔ dense_size
        norm = (dens_val - d_low) / (d_high - d_low)
        base = int(loose_size - norm * (loose_size - dense_size))

    if legal:
        base = int(base * legal_multiplier)

    # Clamp to safe band
    return max(min_tokens, min(base, max_tokens))


def sliding_densities(
    tokens: List[str],
    window_size: int = 80,
    step: int = 40,
) -> Iterable[Tuple[int, float, float, bool]]:
    """Yield ``(start_idx, entropy, lex_div, legal_flag)`` for every window."""
    n = len(tokens)
    for start in range(0, n, step):
        window = tokens[start : start + window_size]
        if not window:
            break
        entropy, lex_div = estimate_density(window)
        legal_flag = is_legalese(window)
        yield start, entropy, lex_div, legal_flag
