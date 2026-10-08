# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""The 5D POINT (coordinate) of an entry or node — spec/SPEC.md §11.

"Each dimension is 0-1 and independent, compared by cosine. The current
sum-to-1 shares become a derived view." This module is that independent
point — five values, each in [0, 1], NOT constrained to sum to 1 — and its
cosine comparison. ``five_d_nd.position`` is UNCHANGED (§5 still computes the
sum-to-1 SHARES view exactly as before); :func:`shares_view` here is a thin,
named re-export that makes the "shares is now a derived VIEW of the same raw
contributions, not the only view" relationship explicit, without touching
``position.py`` at all.

**Derivation formula, REPLACING this module's own earlier
max-normalised formula.** Each dimension is
INDEPENDENT and SATURATING:

    point[d] = round(min(raw[d] / saturation[d], 1.0), 6)

``saturation`` is a resolution-profile field (§16, ``point_saturation`` —
ONE SHARED scalar across all five dimensions by default; whether this is
shared or per-dimension is not fixed by the base formula ("point
dimension = min(count/saturation,1), independent (not max-normalised)")
— it is THIS SPECIFICATION's own implementation choice,
made here, documented here; a caller MAY instead pass a per-dimension
mapping, since the formula above is already written per-dimension and does
not care which). The shared default (5) is the SAME saturation `depth.py`'s
own ``link_saturation`` already uses, kept consistent rather than
inventing a second, unrelated constant.

**The no-contribution case needs NO special branch any more** (the earlier
"neutral all-0.5" rule, and its "equidistant from both poles" justification,
are WITHDRAWN — that justification was wrong: there is no pole-equidistant
point for a SATURATING, not bounded-on-both-sides, formula). With zero raw
contributions on every dimension, the formula above naturally returns the
ALL-ZERO point (``min(0/s, 1) == 0`` for every ``d``) — no special-casing
needed. Distinguishability from a UNIFORM-BUT-NONZERO point (e.g. one hit
on every dimension) is carried entirely by :func:`cosine`'s existing
degenerate-zero-norm rule: ``cosine(zero_point, zero_point) == 0.0`` (never
self-similar to 1.0, by the same "no information" logic as before), while
``cosine(uniform_point, uniform_point) == 1.0`` (a genuine non-zero
direction IS self-similar) — the all-zero point and a uniform-but-nonzero
point are therefore NEVER confused with each other — a CONSEQUENCE of
applying the formula above, achieved without an ``NEUTRAL``/0.5
floor of any kind (that floor was this specification's own earlier
invention). ``NEUTRAL`` is REMOVED from this module's public surface.

An nD grammar or host MAY supply an alternative encoder (a learned model, an
LLM-scored point) in place of this formula; such an encoder is NEVER
normative (§1's "no neural vectoriser" carries over unchanged) — this
module's own formula is the one EVERY conformant implementation MUST
reproduce when no override is supplied, and the one this specification's own
conformance vectors (``conformance/vectors/point/``) exercise.

**Explicit field types** (the same discipline as §9's own field-type
table and §16's profile table): a POINT document is a mapping with
EXACTLY the five dimension keys, each a JSON number (never a boolean) in
``[0, 1]`` — see :func:`point_violations` / ``schema/point.schema.json``.

Stdlib only.
"""
from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from . import profile as _profile
from .position import DIMENSIONS, normalise

__all__ = [
    "DIMENSIONS",
    "DEFAULT_POINT_SATURATION",
    "point_from_contributions",
    "cosine",
    "shares_view",
    "point_violations",
    "is_valid_point",
    "point_from_contributions_from_profile",
]

#: The shared default saturation every dimension's count is divided by
#: — the same value ``depth.py``'s own
#: ``link_saturation`` defaults to, and the same value
#: ``profile.DEFAULTS["point_saturation"]`` publishes.
DEFAULT_POINT_SATURATION = 5
_PLACES = 6


def point_from_contributions(raw: Mapping, saturation: Any = DEFAULT_POINT_SATURATION) -> dict:
    """The deterministic point derivation formula (this module's own
    docstring): ``point[d] = min(raw[d] / saturation[d],
    1.0)``, rounded to 6 decimal places, per dimension independently.

    ``saturation`` is EITHER a single positive number (shared across all
    five dimensions — the default) OR a mapping ``{dimension: positive
    number}`` giving a PER-DIMENSION saturation; either shape is accepted
    without changing the formula itself.

    Raises ``ValueError`` on an unknown dimension key in ``raw``, a
    negative contribution, or a non-positive saturation (shared or
    per-dimension).
    """
    unknown = set(raw) - set(DIMENSIONS)
    if unknown:
        raise ValueError(f"not a 5D dimension: {sorted(unknown)!r}")
    values = {d: float(raw.get(d, 0) or 0) for d in DIMENSIONS}
    if any(v < 0 for v in values.values()):
        raise ValueError("point contributions must be non-negative")
    if isinstance(saturation, Mapping):
        sat_unknown = set(saturation) - set(DIMENSIONS)
        if sat_unknown:
            raise ValueError(f"not a 5D dimension: {sorted(sat_unknown)!r}")
        sats = {d: float(saturation.get(d, DEFAULT_POINT_SATURATION)) for d in DIMENSIONS}
    else:
        sats = {d: float(saturation) for d in DIMENSIONS}
    if any(s <= 0 for s in sats.values()):
        raise ValueError(f"saturation must be positive on every dimension, got {sats!r}")
    return {d: round(min(values[d] / sats[d], 1.0), _PLACES) for d in DIMENSIONS}


def cosine(p: Mapping, q: Mapping) -> float:
    """Cosine similarity between two points, over the five dimensions in
    canonical order. Returns ``0.0`` for the degenerate all-zero-norm case
    (the no-contribution point this module's own formula produces, §11's
    "no special branch needed" rule — never self-similar to 1.0, which is
    exactly what keeps it distinguishable from a uniform-but-nonzero
    point). Rounded to 6 decimal places.
    """
    dot = sum(float(p.get(d, 0.0)) * float(q.get(d, 0.0)) for d in DIMENSIONS)
    norm_p = math.sqrt(sum(float(p.get(d, 0.0)) ** 2 for d in DIMENSIONS))
    norm_q = math.sqrt(sum(float(q.get(d, 0.0)) ** 2 for d in DIMENSIONS))
    if norm_p == 0.0 or norm_q == 0.0:
        return 0.0
    return round(dot / (norm_p * norm_q), _PLACES)


def shares_view(raw: Mapping) -> dict:
    """The "shares" view (spec/SPEC.md §11): §5's ORIGINAL sum-to-1 position,
    unchanged, named here as what it now is — a
    DERIVED VIEW of the same raw contributions the point (above) is also
    derived from, not the entry's only coordinate any more. A thin
    pass-through to :func:`five_d_nd.position.normalise` — ``position.py``
    itself is untouched (round's rule: additions only, existing public API
    unchanged).
    """
    return normalise(raw)


def point_violations(doc: Any) -> list:
    """Violations of a POINT document's shape: a
    mapping with EXACTLY the five dimension keys (§2), each a JSON number
    (never a boolean) in ``[0, 1]``. No extra keys; no missing keys.
    Returns ``[]`` when the document validates — mirrors
    ``schema/point.schema.json`` exactly (``additionalProperties: false``,
    all five required).
    """
    if not isinstance(doc, Mapping):
        return ["point must be a mapping"]
    out = []
    missing = [d for d in DIMENSIONS if d not in doc]
    if missing:
        out.append(f"point is missing dimension(s) {missing!r}")
    extra = sorted(set(doc) - set(DIMENSIONS))
    if extra:
        out.append(f"point has unknown key(s) {extra!r}")
    for d in DIMENSIONS:
        if d not in doc:
            continue
        v = doc[d]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not (0.0 <= v <= 1.0):
            out.append(f"point[{d!r}] must be a number in [0, 1], got {v!r}")
    return out


def is_valid_point(doc: Any) -> bool:
    return point_violations(doc) == []


def point_from_contributions_from_profile(raw: Mapping, profile_doc: Mapping) -> dict:
    """Wires the RESOLUTION PROFILE (§16) directly into
    :func:`point_from_contributions` — accepts a profile DOCUMENT
    (validated or not; call ``five_d_nd.profile.profile_violations``
    first) and reads its ``point_saturation`` field rather than requiring
    every caller to unpack it by hand.
    """
    resolved = _profile.resolve_profile(profile_doc)
    return point_from_contributions(raw, saturation=resolved["point_saturation"])
