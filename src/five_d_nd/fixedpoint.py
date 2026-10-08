# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""Fixed-point arithmetic for derived 5D views — spec/SPEC.md §12.

Stage 1 of the coordinate round (build list item 2): every leaf value a
derived view folds over (a member point's component, a weight) is quantised
EXACTLY ONCE, at the point it enters the fold, to a scaled integer —
``SCALE = 1_000_000`` (1e-6 precision), fitting comfortably in an int64. From
there every SUM is plain integer addition, which is associative and
commutative, so fold order stops mattering for anything downstream of
quantisation (it still matters for the dimension algebra itself, §3 — this
module touches only the five-value point/weight arithmetic, never the
composition table). Exactly ONE division, and ONE rounding, happen — at VIEW
MATERIALISATION (a container's mean position, a trimmed top-k's match
statistic) — never mid-fold. Ties in a trimmed top-k (§14) are broken by
canonical SALTED claim-id order (:func:`canonical_tiebreak_key`), never by
insertion order or an unsalted id (which would leak a stable, guessable
ordering across containers).

Stdlib only.
"""
from __future__ import annotations

import hashlib
from collections.abc import Iterable

__all__ = [
    "SCALE",
    "PLACES",
    "to_fixed",
    "from_fixed",
    "fixed_sum",
    "fixed_mean",
    "canonical_tiebreak_key",
]

#: Quantisation scale: 1e-6 precision, scaled integers fit an int64.
SCALE = 1_000_000
#: Decimal places a materialised (post-division) value is rounded to — kept
#: identical to §5's own six-decimal-place rounding for consistency.
PLACES = 6


def to_fixed(x: float) -> int:
    """Quantise a float leaf value, ONCE, to a scaled integer.

    ``x * SCALE`` is computed in IEEE-754 binary64 (fix round item 12,
    spec/SPEC.md §12) — Python's native ``float`` already IS binary64, so
    this is simply the ordinary ``*`` operator here; the point is
    normative for a REIMPLEMENTATION in another language, which MUST
    perform the SAME binary64 multiplication (not a wider/narrower float,
    not a decimal/rational multiply) before rounding — two multiplication
    semantics can both satisfy "round half away from zero" in the
    abstract while disagreeing on the exact scaled integer for some input
    ``x``, because they disagree on the PRODUCT before rounding is ever
    applied. The rounding itself is round-half-away-from-zero (the common
    "round half up" rule, applied symmetrically for negative values too,
    though every value this specification's own callers pass is
    non-negative) — deterministic and independent of the platform's
    float-ROUNDING mode (distinct from the float REPRESENTATION this
    docstring's first sentence pins to binary64). ``to_fixed(0.1) ==
    100000``; ``to_fixed(1.0) == 1_000_000``.
    """
    scaled = x * SCALE
    if scaled >= 0:
        return int(scaled + 0.5)
    return -int(-scaled + 0.5)


def from_fixed(n: int) -> float:
    """Convert a scaled integer back to a float, for display/comparison only
    — never fed back into a further fold (§12: quantise once)."""
    return n / SCALE


def fixed_sum(values: Iterable[int]) -> int:
    """Integer sum of scaled-integer leaf values. Associative and
    commutative by construction (plain ``int`` addition) — fold order over
    already-quantised values never changes the result."""
    return sum(values)


def fixed_mean(total: int, n: int) -> int:
    """THE single division-and-rounding point (§12): the scaled-integer mean
    of ``n`` scaled-integer values whose sum is ``total``. Round-half-up on
    the integer division (``(total + n // 2) // n`` for a non-negative
    total; the symmetric form for a negative total), applied exactly once,
    here, at view materialisation — never earlier in a fold.

    Raises ``ValueError`` if ``n <= 0`` (an empty container has no mean —
    callers MUST reject an empty member set before calling this, §14).
    """
    if n <= 0:
        raise ValueError(f"fixed_mean() requires n > 0, got {n!r}")
    if total >= 0:
        return (total + n // 2) // n
    neg = -total
    return -((neg + n // 2) // n)


def canonical_tiebreak_key(claim_id: str, salt: str) -> str:
    """The canonical SALTED order used to break a trimmed top-k tie (§14):
    sha256 of ``salt + "|" + claim_id``, hex-encoded. Two members with equal
    rank weight sort by this key, ascending — deterministic, and not a bare
    claim-id compare (which would expose claim-id ordering directly; the
    salt is a resolution-profile field, §16, so the tiebreak order itself is
    pinned by the profile digest).
    """
    return hashlib.sha256(f"{salt}|{claim_id}".encode("utf-8")).hexdigest()
