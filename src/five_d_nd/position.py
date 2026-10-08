# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""The 5D fingerprint (position) of an entry — spec/SPEC.md §5.

Rules taken from versum's ``position5d.py`` (git -C loomground-versum show
origin/main:src/versum/position5d.py, read 2026-09-30) and specified here, not
reimplemented differently: five values normalised to sum 1 (six decimal places),
dominant = argmax of raw (pre-normalisation) contributions, ties broken in
canonical dimension order (structural, causal, intentional, temporal, relational —
the earliest wins), and the all-zero position (basis ``"default"``, dominant
``relational``) when nothing contributes.

5D is neutral on is/ought (spec/SPEC.md §7, N1 — owner design change,
2026-10-01): there is exactly ONE fingerprint per entry, computed by these
rules alone. Whether a contribution is "normative" is nD-grammar knowledge
(a co-dimension on that grammar's own NDSystem, §9), never a concern of this
module or of the position it computes.

**Containment contribution (§5, rule 3 — versum ``src/versum/planes.py``
``build_source_entries``, read 2026-10-01).** versum's own indexer adds
``+1 structural`` to an entry's contributions for EVERY outgoing structural
``embeds`` link — i.e. for every OTHER entry it structurally contains —
``contrib[parent["item_id"]][EMBED_LINK_DIMENSION] += 1``, on top of
whatever that entry's own claims already contribute (rules 1-2). This is
NOT a claim contribution; it is purely positional (derived from span
containment), computed by versum's indexer for every embedded entry,
regardless of which plane produced it. :func:`with_embeds` is the thin
seam that applies this exact rule to a contributions dict before
:func:`fingerprint` is called on it.

Stdlib only.
"""
from __future__ import annotations

from collections.abc import Mapping

from .dimensions import DEFAULT_DIMENSION, Dimension

#: The five dimensions, in their canonical (and tie-breaking) order.
DIMENSIONS: tuple = tuple(d.value for d in Dimension)
TIE_ORDER: tuple = DIMENSIONS
#: The dominant dimension of an entry with no contribution at all.
NO_CONTRIBUTION_DOMINANT: str = DEFAULT_DIMENSION.value
BASIS_CONTRIBUTIONS = "planes"
BASIS_DEFAULT = "default"
_PLACES = 6
#: versum's own EMBED_LINK_DIMENSION — the containment contribution always
#: lands on this dimension (see :func:`with_embeds`).
EMBEDS_DIMENSION = Dimension.STRUCTURAL.value

__all__ = [
    "DIMENSIONS",
    "TIE_ORDER",
    "NO_CONTRIBUTION_DOMINANT",
    "BASIS_CONTRIBUTIONS",
    "BASIS_DEFAULT",
    "EMBEDS_DIMENSION",
    "is_dimension",
    "zero_contributions",
    "normalise",
    "dominant",
    "basis",
    "fingerprint",
    "with_embeds",
]


def is_dimension(value) -> bool:
    """True iff ``value`` is one of the five canonical dimension strings."""
    return isinstance(value, str) and value in DIMENSIONS


def zero_contributions() -> dict:
    return {d: 0 for d in DIMENSIONS}


def normalise(contributions: Mapping) -> dict:
    """The normalised five-value position; all zeros when nothing contributed.

    Raises ``ValueError`` on an unknown dimension key or a negative contribution.
    """
    unknown = set(contributions) - set(DIMENSIONS)
    if unknown:
        raise ValueError(f"not a 5D dimension: {sorted(unknown)!r}")
    raw = {d: float(contributions.get(d, 0) or 0) for d in DIMENSIONS}
    if any(v < 0 for v in raw.values()):
        raise ValueError("5D contributions must be non-negative")
    total = sum(raw.values())
    if total == 0:
        return {d: 0.0 for d in DIMENSIONS}
    return {d: round(raw[d] / total, _PLACES) for d in DIMENSIONS}


def dominant(contributions: Mapping) -> str:
    """Exactly one dominant dimension: argmax of RAW contributions, ties broken by
    :data:`TIE_ORDER` (canonical order; the earliest wins)."""
    best, best_value = NO_CONTRIBUTION_DOMINANT, 0.0
    for d in TIE_ORDER:
        v = float(contributions.get(d, 0) or 0)
        if v > best_value:
            best, best_value = d, v
    return best


def basis(contributions: Mapping) -> str:
    """``"planes"`` iff at least one contribution is positive, else ``"default"``."""
    return BASIS_CONTRIBUTIONS if any(float(v or 0) > 0 for v in contributions.values()) \
        else BASIS_DEFAULT


def fingerprint(contributions: Mapping) -> dict:
    """The full 5D fingerprint of an entry: the five normalised values plus
    ``dominant`` and ``basis``, matching ``schema/position.schema.json``."""
    pos = normalise(contributions)
    out = dict(pos)
    out["dominant"] = dominant(contributions)
    out["basis"] = basis(contributions)
    return out


def with_embeds(contributions: Mapping, count: int = 1) -> dict:
    """Merge versum's own containment rule (see this module's docstring, §5
    rule 3) into ``contributions``: ``count`` more structural, on top of
    whatever ``contributions`` already holds from the entry's own claims
    (rules 1-2). Returns a NEW dict; ``contributions`` itself is never
    mutated. ``count`` is the number of OUTGOING ``embeds`` links this entry
    has (how many other entries it structurally contains) — most entries
    have 0 or 1, but versum's own rule has no upper bound.

    Raises ``ValueError`` if ``count`` is negative (an entry cannot embed a
    negative number of other entries).
    """
    if count < 0:
        raise ValueError(f"count must be non-negative, got {count!r}")
    out = dict(contributions)
    out[EMBEDS_DIMENSION] = float(out.get(EMBEDS_DIMENSION, 0) or 0) + count
    return out
