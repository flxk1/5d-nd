# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""Artifact matching: combining an nD term score and a 5D structural score.

The owner approved integrating the winning build's design and grafts
(2026-10-02; see ``docs/decisions/0007-clause-cue-layer-and-example-grammars.md``).
That comparison's own finding: 5D does NOT add measurable
retrieval signal on its own — it is the coordinate frame the lexical and
requirement nD grammars attach to. This module is
the NORMATIVE (so stated explicitly — see below) rule for how a single
artifact-match score is built out of those two signals:

  * a **term score** — the nD "term" grammar's own BM25 cosine
    (``five_d_nd.grammars.term``), a topical/lexical signal, computed over
    an nD grammar's own axis, never over 5D itself;
  * a **structural score** — a 5D cosine (``five_d_nd.point.cosine``)
    between two points, the coordinate-frame signal §9's own "invariant for
    consuming languages" already scopes narrowly (a verdict may never READ
    a composed 5D weight/position to decide itself — this module does not
    violate that: it blends a plain 5D DESCRIPTIVE similarity score into
    its own output number, it does not treat that output as a §7 verdict).

**The blend is a fixed-a-priori weighted average, never tuned on the GDPR
ground truth** used to measure retrieval quality:

    combined = (term_weight * term_score + structural_weight * structural_score)
               / (term_weight + structural_weight)

``term_weight``/``structural_weight`` are a resolution-profile field
(§16, ``match_blend_weights``), default ``{"term": 0.7, "structural": 0.3}``.

**Why 0.7/0.3, a priori, not fit to GDPR AUC.** The term grammar's BM25
score is a direct lexical-overlap ranking function — exactly the signal
standard information-retrieval practice (BM25/TF-IDF as the baseline
ranker) treats as the primary relevance signal for a text query. The 5D
structural cosine is, by §9's own invariant above, a DESCRIPTIVE
coordinate-frame signal — grounding/provenance information, not itself a
ranking function (§9: "an nD grammar MAY read 5D to describe what it is
grounded in... never to derive its normative force"). Weighting the
descriptive coordinate signal LOWER than the direct lexical ranking signal
follows from that role difference alone, independent of any corpus; this is
the "nD-first" design ADR 0007 calls for — realised here as a
fixed WEIGHT skew (0.7 vs 0.3), not as a conditional branch or an ordering
of evaluation (a weighted average has no evaluation order to begin with).
These two numbers were chosen and documented BEFORE this module was run
against the GDPR corpus, and are never adjusted by that run — any
re-measurement after this module ships is a validation of the chosen
defaults, not a search for better ones.

Stdlib only.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from . import profile as _profile

__all__ = [
    "DEFAULT_MATCH_BLEND_WEIGHTS",
    "combine_scores",
    "combine_scores_from_profile",
]

#: Fixed a priori (never tuned on GDPR ground truth) — see module docstring.
#: Derived from
#: ``five_d_nd.profile.DEFAULTS`` — ONE named source, never a second
#: literal copy of the same pair that could silently drift from it.
DEFAULT_MATCH_BLEND_WEIGHTS: dict = dict(_profile.DEFAULTS["match_blend_weights"])

_PLACES = 6


def _validate_score(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a number, got {value!r}")
    v = float(value)
    # `0.0 <= v <= 1.0` already rejects NaN (every
    # comparison with NaN is False in IEEE-754) and +-inf, so this check
    # alone is already fail-closed on non-finite scores — `math.isfinite`
    # is asserted explicitly anyway, stated rather than left implicit.
    if not math.isfinite(v) or not (0.0 <= v <= 1.0):
        raise ValueError(f"{name} must be a finite number in [0, 1], got {value!r}")
    return v


def combine_scores(term_score: Any, structural_score: Any, weights: "Mapping | None" = None) -> float:
    """The fixed weighted-average blend (module docstring). ``weights``,
    when given, MUST be a mapping with non-negative ``term``/``structural``
    keys summing strictly positive — the SAME shape §16's
    ``match_blend_weights`` profile field validates
    (``five_d_nd.profile.profile_violations``); defaults to
    :data:`DEFAULT_MATCH_BLEND_WEIGHTS` when omitted. Raises ``ValueError``
    on an out-of-range score or a malformed weights mapping (fail closed).
    """
    term_score = _validate_score("term_score", term_score)
    structural_score = _validate_score("structural_score", structural_score)
    w = weights if weights is not None else DEFAULT_MATCH_BLEND_WEIGHTS
    if not isinstance(w, Mapping) or set(w) != {"term", "structural"}:
        raise ValueError(f"weights must be a mapping with exactly 'term'/'structural' keys, got {w!r}")
    term_w, structural_w = w["term"], w["structural"]
    for label, value in (("term", term_w), ("structural", structural_w)):
        # `math.isfinite` closes the same NaN/inf gap
        # profile.py's own weight-mapping check closes (shared concern,
        # separate code paths — `match.py` validates a bare weights
        # mapping passed directly, not only one read from a profile).
        if isinstance(value, bool) or not isinstance(value, (int, float)) \
                or not math.isfinite(value) or value < 0:
            raise ValueError(f"weights[{label!r}] must be a finite, non-negative number, got {value!r}")
    total = float(term_w) + float(structural_w)
    if not math.isfinite(total) or total <= 0:
        raise ValueError(
            "weights['term'] + weights['structural'] must be a finite, strictly positive sum")
    combined = (float(term_w) * term_score + float(structural_w) * structural_score) / total
    return round(combined, _PLACES)


def combine_scores_from_profile(term_score: Any, structural_score: Any, profile_doc: Mapping) -> float:
    """Residual convenience, mirroring
    ``five_d_nd.point.point_from_contributions_from_profile``: wire the
    resolution profile's ``match_blend_weights`` field (§16) directly into
    :func:`combine_scores` without requiring every caller to unpack it by
    hand. ``profile_doc`` is NOT validated here — call
    ``five_d_nd.profile.profile_violations`` first.
    """
    resolved = _profile.resolve_profile(profile_doc)
    return combine_scores(term_score, structural_score, weights=resolved["match_blend_weights"])
