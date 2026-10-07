# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""The resolution profile — spec/SPEC.md §16 (build list item 6).

A digest-pinned JSON document holding every tunable this round's formulas
read as a parameter: the trimmed top-k's ``k`` and the small-n floor
``n_min`` (§14), the depth neighbourhood radius ``r`` and blend weights
(§14), a confidence floor (stage 2 — see §16/§17's own note below), and
the ingest-stale window (§15). Several
profiles MAY coexist (an extraction-profile upgrade, build list item 5, is
a RE-DERIVATION event under one profile digest, never a silent edit to an
existing one) — this module validates ONE profile document's shape and
computes its digest; profile VERSIONING/coexistence policy is a hosting
concern outside this module.

Stdlib only.
"""
from __future__ import annotations

import json
import math
from collections.abc import Mapping
from hashlib import sha256
from typing import Any

__all__ = [
    "DEFAULTS",
    "KNOWN_FIELDS",
    "profile_violations",
    "is_valid_profile",
    "resolve_profile",
    "profile_digest",
]

#: Every default this specification's own formulas (``container.py``,
#: ``depth.py``, ``views.py``) also use when no profile overrides them —
#: kept as ONE named source of truth so the profile schema, this module, and
#: the formula modules' own docstrings never drift apart. ``point_saturation``
#: is the point formula's own shared saturation constant
#: (``five_d_nd.point.DEFAULT_POINT_SATURATION``). ``nesting_saturation`` is
#: REMOVED — the nesting signal (``depth.py``'s
#: ``nesting_relative_position()``) is an ``ancestors/(ancestors+
#: descendants)`` RATIO, already bounded to ``[0, 1]`` by construction, and
#: has never read a saturation constant of any kind; the field was dead
#: from the moment the ratio-based nesting signal replaced the earlier
#: absolute ``nesting_level``.
#: spec/SPEC.md §8a (clause-cue layer) / §19 (matching) — see
#: ``docs/decisions/0007-clause-cue-layer-and-example-grammars.md``.
#: ``clause_cue_saturation`` is
#: ``five_d_nd.clause_cues``'s own per-clause saturation default (3);
#: ``match_blend_weights`` is ``five_d_nd.match``'s fixed-a-priori blend
#: between the nD term score and the 5D structural score (0.7/0.3 — see
#: that module's own docstring for why these are NOT tuned on the GDPR
#: ground truth used to measure AUC).
#: ``relational_suppression_scale`` (decided 2026-10-03 — see
#: ``five_d_nd.clause_cues.relational_effective``): the ``s`` in the
#: ``relational_count * s / (s + n_other)`` down-weighting formula that
#: REPLACES §8a's earlier all-or-nothing relational gate. Default `1`,
#: POSITIVE, FINITE — unlike the other saturation fields, deliberately
#: NOT constrained to be an integer (the formula's own ``s`` is a scale,
#: not a count).
DEFAULTS: dict = {
    "k": 5,
    "n_min": 3,
    "r": 2,
    "d_blend_weights": {"links": 0.5, "nesting": 0.5},
    "link_saturation": 5,
    "anchor_saturation": 2,
    "point_saturation": 5,
    "clause_cue_saturation": 3,
    "match_blend_weights": {"term": 0.7, "structural": 0.3},
    "confidence_floor": 0.05,
    "staleness_window_seconds": 3600,
    "relational_suppression_scale": 1,
    "tiebreak_salt": "5d-nd-coordinate-round-2026-10-01",
}

_REQUIRED = ("profile_id",)
_POSITIVE_NUMBERS_INTEGRAL = (
    "k", "n_min", "r", "link_saturation", "anchor_saturation",
    "point_saturation", "clause_cue_saturation",
)
#: Positive, FINITE, but NOT required to be an integer (unlike
#: :data:`_POSITIVE_NUMBERS_INTEGRAL`) — currently just
#: ``relational_suppression_scale``.
_POSITIVE_NUMBERS = ("relational_suppression_scale",)
_UNIT_FLOATS = ("confidence_floor",)
_NON_NEGATIVE_NUMBERS = ("staleness_window_seconds",)
_PLAIN_STRINGS = ("tiebreak_salt", "schema_version", "segmenter_digest", "table_digest")
#: Mapping fields shaped like ``d_blend_weights``: a 2-key mapping of
#: non-negative numbers summing strictly positive. ``field -> (key_a, key_b)``.
_WEIGHT_MAPPING_FIELDS: "dict[str, tuple[str, str]]" = {
    "d_blend_weights": ("links", "nesting"),
    "match_blend_weights": ("term", "structural"),
}

#: The COMPLETE, closed set of field names this document may carry (fix
#: round item 7; widened fix round, 2026-10-02, item for
#: ``clause_cue_saturation``/``match_blend_weights``): ``profile_id``,
#: every field in :data:`_POSITIVE_NUMBERS_INTEGRAL`, every field in
#: :data:`_WEIGHT_MAPPING_FIELDS`, every field in :data:`_UNIT_FLOATS` and
#: :data:`_NON_NEGATIVE_NUMBERS`, and every field in :data:`_PLAIN_STRINGS`.
#: An unknown key (e.g. a typo like ``"K"`` for ``"k"``) is now a
#: VIOLATION, not silently ignored — silently ignoring it would let a typo
#: pass validation while never actually overriding the default it looked
#: like it was setting, corrupting :func:`profile_digest` only by omission
#: (the typo'd key would also, nonsensically, leak into the digest as an
#: unresolved extra key — rejecting it outright is simpler and safer than
#: either silently dropping or silently digesting an unknown key).
KNOWN_FIELDS: frozenset = frozenset(
    _REQUIRED + _POSITIVE_NUMBERS_INTEGRAL + _POSITIVE_NUMBERS + tuple(_WEIGHT_MAPPING_FIELDS)
    + _UNIT_FLOATS + _NON_NEGATIVE_NUMBERS + _PLAIN_STRINGS
)


def _is_positive_integral(value: Any) -> bool:
    """True iff ``value`` is a positive NUMBER with NO fractional part —
    fix round item 7: the profile schema's own ``"type": "integer"``
    keyword (per the JSON Schema spec) already accepts a JSON number with a
    zero fractional part, such as ``5.0`` — this function now agrees with
    the schema exactly (``5`` and ``5.0`` both valid; ``5.5`` and any
    ``bool`` are not), instead of the earlier, schema-disagreeing
    Python-``int``-only check.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if not math.isfinite(value):
        return False
    return value == int(value) and value > 0


def profile_violations(doc: Any) -> list:
    """Violations of a resolution profile document. ``profile_id`` is
    REQUIRED (a non-empty string). Every other field is OPTIONAL — absent
    means :data:`DEFAULTS`' own value (see :func:`resolve_profile`) — but
    when PRESENT, it MUST have the type the field table below declares:

      * ``k``, ``n_min``, ``r``, ``link_saturation``, ``anchor_saturation``,
        ``point_saturation``: POSITIVE INTEGER (never a bool — a JSON
        boolean is its own type, not an integer, matching this
        specification's own §9 field-typing discipline).
      * ``d_blend_weights``: a mapping ``{"links": number, "nesting":
        number}``, BOTH keys required when the field is present at all,
        both non-negative, and their sum strictly positive (§14 — a
        profile that zeroes both blend weights cannot define a depth at
        all).
      * ``clause_cue_saturation``: POSITIVE INTEGER (same discipline as
        ``point_saturation`` — §8a, ``five_d_nd.clause_cues``).
      * ``match_blend_weights``: a mapping ``{"term": number, "structural":
        number}``, same two-key/non-negative/strictly-positive-sum
        discipline as ``d_blend_weights`` — §19, ``five_d_nd.match``'s
        fixed-a-priori blend between the nD term score and the 5D
        structural score.
      * ``relational_suppression_scale``: a POSITIVE FINITE number
        (never a bool; NOT required to be an integer, unlike
        ``clause_cue_saturation``) — the ``s`` in §8a's
        ``relational_effective`` down-weighting formula (decided
        2026-10-03, ``five_d_nd.clause_cues``).
      * ``confidence_floor``: a number in ``[0, 1]``.
      * ``staleness_window_seconds``: a non-negative number.
      * ``tiebreak_salt``: a non-empty string.
      * ``schema_version``, ``segmenter_digest``, ``table_digest``:
        non-empty strings when present (informative — carried fields with
        no further validation rule beyond their basic type, same pattern
        §9 already applies to ``version_5d``).

    Returns ``[]`` when the document validates.
    """
    if not isinstance(doc, Mapping):
        return ["resolution profile must be a mapping"]
    out = []
    unknown = sorted(set(doc) - KNOWN_FIELDS)
    if unknown:
        out.append(
            f"resolution profile has unknown field(s) {unknown!r} — a typo must not silently "
            "leave a default in place while also polluting the digest (§16, fix round item 7)")
    for field in _REQUIRED:
        value = doc.get(field)
        if not isinstance(value, str) or not value:
            out.append(f"resolution profile field {field!r} must be a non-empty string")
    for field in _POSITIVE_NUMBERS_INTEGRAL:
        if field not in doc:
            continue
        value = doc[field]
        if not _is_positive_integral(value):
            out.append(f"resolution profile field {field!r} must be a positive integer, got {value!r}")
    for field in _POSITIVE_NUMBERS:
        if field not in doc:
            continue
        value = doc[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)) \
                or not math.isfinite(value) or value <= 0:
            out.append(
                f"resolution profile field {field!r} must be a positive finite number, got {value!r}")
    for field_name, (key_a, key_b) in _WEIGHT_MAPPING_FIELDS.items():
        if field_name not in doc:
            continue
        weights = doc[field_name]
        if not isinstance(weights, Mapping) or set(weights) != {key_a, key_b}:
            out.append(
                f"resolution profile field {field_name!r} must be a mapping with "
                f"exactly {key_a!r} and {key_b!r} keys, got {weights!r}")
            continue
        value_a, value_b = weights.get(key_a), weights.get(key_b)
        # NaN/inf weights MUST be rejected too — `nan < 0` and `inf < 0` are both
        # False in IEEE-754, so the bare `value < 0` check alone silently
        # ACCEPTED a non-finite weight (and the sum>0 check below could
        # not catch it either: `nan <= 0` is ALSO False). `math.isfinite`
        # closes both gaps at once, shared by d_blend_weights AND
        # match_blend_weights (this loop is the one place both validate).
        both_well_typed = True
        for name, value in ((key_a, value_a), (key_b, value_b)):
            if isinstance(value, bool) or not isinstance(value, (int, float)) \
                    or not math.isfinite(value) or value < 0:
                out.append(
                    f"resolution profile field '{field_name}.{name}' must be a "
                    f"finite, non-negative number, got {value!r}")
                both_well_typed = False
        if both_well_typed:
            total = (value_a or 0) + (value_b or 0)
            # Two individually finite weights (e.g. 1e308 + 1e308) can still
            # sum to a non-finite float (IEEE-754 overflow to +inf) —
            # `combine_scores` (match.py) already rejects a non-finite
            # SUM; `profile_violations` must agree, or a profile the code
            # calls "valid" could make `combine_scores` raise regardless.
            if not math.isfinite(total) or total <= 0:
                out.append(
                    f"resolution profile field {field_name!r}: {key_a} + {key_b} "
                    "must be a finite, strictly positive sum")
    for field in _UNIT_FLOATS:
        if field not in doc:
            continue
        value = doc[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not (0.0 <= value <= 1.0):
            out.append(f"resolution profile field {field!r} must be a number in [0, 1], got {value!r}")
    for field in _NON_NEGATIVE_NUMBERS:
        if field not in doc:
            continue
        value = doc[field]
        # fix round item 3: `value < 0` alone does not reject NaN (`nan < 0`
        # is False in IEEE-754) — `math.isfinite` closes that gap here too.
        if isinstance(value, bool) or not isinstance(value, (int, float)) \
                or not math.isfinite(value) or value < 0:
            out.append(f"resolution profile field {field!r} must be a non-negative number, got {value!r}")
    for field in _PLAIN_STRINGS:
        if field not in doc:
            continue
        value = doc[field]
        if not isinstance(value, str) or not value:
            out.append(f"resolution profile field {field!r} must be a non-empty string, got {value!r}")
    return out


def is_valid_profile(doc: Any) -> bool:
    return profile_violations(doc) == []


#: EVERY top-level numeric field, not only the
#: explicitly-integer ones — ``confidence_floor``/``staleness_window_seconds``
#: are declared as "a number", and ``0`` vs ``0.0`` is exactly the same
#: digest-divergence bug as ``k: 5`` vs ``k: 5.0``, just on a field whose
#: VALID range also includes genuinely fractional values.
_ALL_NUMERIC_FIELDS = _POSITIVE_NUMBERS_INTEGRAL + _POSITIVE_NUMBERS + _UNIT_FLOATS + _NON_NEGATIVE_NUMBERS


def _canonicalize_numeric_value(value: Any) -> Any:
    """A single numeric value, canonicalised to a plain ``int`` when it is
    a zero-fractional number (``5``, ``5.0``, and ``5`` all become the
    SAME Python ``int`` ``5``) — so ``json.dumps`` serialises them
    IDENTICALLY (``"5"``, never ``"5.0"``). Non-numeric values, booleans,
    non-finite floats, and genuinely fractional floats pass through
    UNCHANGED (callers MUST validate first; this function does not itself
    re-validate).
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return value
    if not math.isfinite(value):
        return value
    if value == int(value):
        return int(value)
    return value


def _canonicalize_integral_fields(doc: Mapping) -> dict:
    """Canonicalises EVERY numeric field this document can carry —
    EVERY top-level field in :data:`_ALL_NUMERIC_FIELDS` (the integer
    fields AND ``confidence_floor``/``staleness_window_seconds``), PLUS
    every :data:`_WEIGHT_MAPPING_FIELDS` mapping's own two NESTED numeric
    fields (``d_blend_weights``'s ``links``/``nesting``;
    ``match_blend_weights``'s ``term``/``structural``) — to a plain
    Python ``int`` whenever the value is
    zero-fractional (e.g. ``5.0`` -> ``5``, ``0.0`` -> ``0``). This closes
    the digest-divergence bug for EVERY numeric field this document has,
    not only the handful that were always declared "integer": two
    profiles whose RESOLVED values are equal (``confidence_floor: 0`` vs
    ``confidence_floor: 0.0``; ``d_blend_weights.links: 1`` vs ``1.0``)
    now produce the IDENTICAL digest, never merely the identical validity
    verdict. Leaves booleans, non-numeric values, and genuinely fractional
    floats untouched.
    """
    out = dict(doc)
    for field in _ALL_NUMERIC_FIELDS:
        if field in out:
            out[field] = _canonicalize_numeric_value(out[field])
    for field_name in _WEIGHT_MAPPING_FIELDS:
        if field_name in out and isinstance(out[field_name], Mapping):
            out[field_name] = {
                k: _canonicalize_numeric_value(v) for k, v in out[field_name].items()
            }
    return out


def resolve_profile(doc: Mapping) -> dict:
    """``doc`` overlaid onto :data:`DEFAULTS` — every field a formula module
    reads gets a concrete value, present or not in ``doc`` itself. Does NOT
    validate ``doc`` (call :func:`profile_violations` first); merges
    ``d_blend_weights`` as a nested overlay, every other field as a plain
    top-level overlay, and canonicalises every integral field
    (:func:`_canonicalize_integral_fields`) so a zero-fractional
    float and the equivalent bare integer resolve, and therefore digest,
    identically.
    """
    out = dict(DEFAULTS)
    out.update({k: v for k, v in doc.items() if k not in _WEIGHT_MAPPING_FIELDS})
    for field_name in _WEIGHT_MAPPING_FIELDS:
        if field_name in doc:
            out[field_name] = {**DEFAULTS[field_name], **doc[field_name]}
    return _canonicalize_integral_fields(out)


def profile_digest(doc: Mapping) -> str:
    """The profile's own digest: sha256 over canonical JSON of the FULLY
    RESOLVED document (:func:`resolve_profile`) — so two profile documents
    that differ only in which fields they leave to default still produce
    the SAME digest when their resolved values are identical (the digest
    pins the EFFECTIVE profile, not its literal on-disk shape).
    """
    resolved = resolve_profile(doc)
    canon = json.dumps(resolved, sort_keys=True, separators=(",", ":"))
    return sha256(canon.encode("utf-8")).hexdigest()
