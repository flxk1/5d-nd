# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""Coordinate round (2026-10-01; fix round) — a deterministic, seeded,
mutation-based fuzz over this round's own validators and arithmetic
functions: the resolution profile (``five_d_nd.profile``), a triple
(``five_d_nd.triple``), a point (``five_d_nd.point``), and the
crash-safety of the container/depth/views functions that are NOT
themselves boolean validators but MUST still never raise anything other
than the single documented ``ValueError`` on a malformed or adversarial
input.

Same method as ``test_fuzz.py``: start from a KNOWN-VALID
baseline, mutate 1-3 keys per case from a small tagged pool of mutation
operators, assert a healthy valid fraction, and assert no function ever
raises an UNDOCUMENTED exception type. Stdlib ``random`` only, fixed seed.

**Fix round, item 3: an ORACLE and a schema-vs-code DIFFERENTIAL, as
``test_fuzz.py`` has.** Every mutant this file generates for the profile
and triple validators is ALSO checked against an independent ORACLE
(:func:`_profile_oracle`/:func:`_triple_oracle` — a from-scratch
re-implementation of the SAME field-type table, deliberately written
without importing or calling the module under test) and, when
``jsonschema`` is importable, against the matching JSON Schema
(``resolution-profile.schema.json`` / ``triple.schema.json``) — a
disagreement on either axis is a hard test failure, not merely a silent
pass/skip.

**Fix round, item 3: no TypeError excuse.** The earlier version of this
file tolerated ``TypeError`` from ``trimmed_top_k_match`` on a
non-numeric ``weight``, on the theory that a malformed weight should be
rejected upstream. ``container.trimmed_top_k_match`` (and
``container_position``) now validate every member's shape BEFORE ranking
— a non-numeric/non-finite ``weight`` or point value is ALWAYS
``ValueError``, never a bare Python comparison ``TypeError`` leaking out
of the sort key. This file now asserts ONLY ``ValueError``, with no
excused exception type.

**P1-P3 (spec/SPEC.md §9's parity policy): NOT APPLICABLE to the
ORACLE/schema differential above — stated explicitly.** versum
(``e416c81``) and loomground-factual (``ebf9fe1``) have NO counterpart for
a resolution profile, a point, a container, a trimmed top-k match
statistic, conceptual depth, or a derived view's staleness tier: none of
these concepts exist upstream yet. The oracle/schema differential above is
THIS round's own single-implementation analogue (independent
re-derivation vs. the code, and schema vs. code), not a cross-repository
comparison.
"""
from __future__ import annotations

import math
import random
import re

import pytest

from five_d_nd import container, depth, fixedpoint, point, profile, triple

_SEED = 20261001
_N_PROFILE = 400
_N_TRIPLE = 400
_N_POINT = 300
# The floors below are exactly the ones this fuzz targets
# (profile/triple >= 20%, point >= 15%),
# reached via (a) a VALID-VALUE-POOL mutation operator (a mutated field is
# sometimes replaced by ANOTHER value this field legitimately accepts, not
# only garbage — a "near-miss" mutant that still exercises a different
# code path while staying valid), (b) an INVALID-BUT-WELL-TYPED pool —
# same JSON kind as a valid value, but out of
# range/fractional/negative/NaN-inf, so the fuzz exercises BOUND checks,
# not only basic-type checks), (c) key-insertion operators (unknown key,
# extra point key, empty tiebreak_salt), and (d) treating "delete an
# OPTIONAL field" as validity-preserving (it reverts to that field's own
# default). Measured with this file's own mutation pool (after adding the
# invalid-but-well-typed pool): profile ~38.75%, triple ~56.75%, point
# ~29.3% — well above the floors, which are the named targets themselves,
# not merely the measured value with margin.
_MIN_VALID_FRACTION_PROFILE = 0.20
_MIN_VALID_FRACTION_TRIPLE = 0.20
_MIN_VALID_FRACTION_POINT = 0.15

_VALID_PROFILE = {
    "profile_id": "fuzz-baseline",
    "k": 5,
    "n_min": 3,
    "r": 2,
    "d_blend_weights": {"links": 0.5, "nesting": 0.5},
    "link_saturation": 5,
    "anchor_saturation": 2,
    "point_saturation": 5,
    # fix round (owner-approved integration step, 2026-10-02) — §8a/§19
    "clause_cue_saturation": 3,
    "match_blend_weights": {"term": 0.7, "structural": 0.3},
    "relational_suppression_scale": 1,
    "confidence_floor": 0.05,
    "staleness_window_seconds": 3600,
    "tiebreak_salt": "fuzz-salt",
    "schema_version": "1.0",
    "segmenter_digest": "abc",
    "table_digest": "def",
}

_VALID_TRIPLE = {
    "s": "urn:example:subject",
    "p": "enables",
    "o": "urn:example:object",
    "dimension": "causal",
    "weight": 0.8,
    "provenance": {"origin": "human"},
    "grammar_id": "deontic",
}

_VALID_POINT = {"structural": 0.2, "causal": 0.4, "intentional": 0.0, "temporal": 1.0, "relational": 0.6}

_UNHASHABLE = [[1, 2], {"a": 1}]
_TYPE_SWAPS = [None, True, False, 0, 1, -1, 0.5, "", "x", [], {}, [1, 2], {"a": 1}]

# Per-field pools of OTHER VALID values (a "near-miss"
# mutation that stays valid while still changing the document) and
# key-insertion pools (unknown-key / extra-key operators), one set per
# baseline.
_PROFILE_VALID_VALUES = {
    "k": [1, 2, 10, 5.0], "n_min": [1, 2, 10, 3.0], "r": [0, 1, 5, 2.0],
    "link_saturation": [1, 3, 9], "anchor_saturation": [1, 3, 9],
    "point_saturation": [1, 3, 9], "confidence_floor": [0.0, 0.5, 1.0],
    "clause_cue_saturation": [1, 2, 9, 3.0],
    "relational_suppression_scale": [1, 2, 0.5, 5.0],
    "staleness_window_seconds": [0, 60, 999999],
    "tiebreak_salt": ["alt-salt", "another-one"],
    "d_blend_weights": [{"links": 1.0, "nesting": 0.0}, {"links": 0.1, "nesting": 0.9}],
    "match_blend_weights": [{"term": 1.0, "structural": 0.0}, {"term": 0.2, "structural": 0.8}],
}
_PROFILE_KEY_INSERTIONS = [("K", 7), ("extra_unknown_field", 1), ("Point_Saturation", 5)]
# INVALID-BUT-WELL-TYPED values — same JSON kind as a
# valid value for the field (never a type-swap to None/a list/a dict),
# but out of range, fractional where an integer is required, negative, or
# NaN/inf where a plain number is required. These are what let the fuzz
# ALONE (no dedicated vector) kill a mutant that only loosens a BOUND
# check without touching the field's basic type check.
_PROFILE_INVALID_WELL_TYPED = {
    "k": [5.5, -1, 0], "n_min": [3.5, -2, 0], "r": [1.5, -1],
    "link_saturation": [-1, 0, 4.4], "anchor_saturation": [-1, 0, 2.2],
    "point_saturation": [-1, 0, 7.7], "clause_cue_saturation": [-1, 0, 3.3],
    "relational_suppression_scale": [-1, 0, float("nan"), float("inf")],
    # kills "profile confidence_floor unbounded" alone:
    "confidence_floor": [1.5, -0.1, float("nan"), float("inf")],
    "staleness_window_seconds": [-100, float("nan"), float("-inf")],
    "tiebreak_salt": [""],
    # kills "d_blend_weights extra key" alone:
    "d_blend_weights": [
        {"links": 0.5, "nesting": 0.5, "extra": 1},
        {"links": -0.1, "nesting": 0.5},
        # fix round item 3: NaN/inf, independently fuzzed (not only a
        # hand-picked vector) -- `x < 0` alone does not reject either.
        {"links": float("nan"), "nesting": 0.5},
        {"links": float("inf"), "nesting": 0.5},
        # NOTE: "both zero" (links+nesting <= 0), and an individually-finite
        # pair whose SUM overflows to +inf
        # (e.g. 1e308+1e308), are deliberately NOT in this pool: both are
        # KNOWN, documented schema-inexpressible cross-field gaps (§16; no
        # JSON Schema keyword can constrain a SUM of two sibling fields)
        # — a dedicated test
        # (test_resolution_profile_rejects_a_non_finite_weight_sum)
        # already covers the overflow case against the code/oracle
        # directly, without conflating it with the schema-differential
        # leg this pool feeds.
    ],
    # same discipline as d_blend_weights, for match_blend_weights (§19):
    "match_blend_weights": [
        {"term": 0.7, "structural": 0.3, "extra": 1},
        {"term": -0.1, "structural": 0.3},
        {"term": float("nan"), "structural": 0.3},
        {"term": float("inf"), "structural": 0.3},
    ],
}

_TRIPLE_VALID_VALUES = {
    "dimension": ["structural", "causal", "intentional", "temporal", "relational"],
    # kills "triple strict-reject integer weight" alone: 1 (a plain int)
    # must stay VALID -- an over-strict mutant rejecting int weights fails here.
    "weight": [0.0, 0.5, 1.0, 1],
    "grammar_id": ["epistemic", "factual"],
    "s": ["urn:example:other-subject"], "p": ["requires", "justifies"],
    "o": ["urn:example:other-object"],
}
_TRIPLE_KEY_INSERTIONS = [("extra_unknown_field", 1), ("Weight", 1), ("GRAMMAR_ID", "x")]
# kills "triple weight unbounded" alone: a mutant that drops/loosens the
# weight <= 1.0 (or >= 0.0) bound check, with the basic number-type check
# left intact, still gets caught here.
_TRIPLE_INVALID_WELL_TYPED = {
    "weight": [1.5, -0.5, 2.0, float("nan"), float("inf")],
    "dimension": ["bogus"],
    "grammar_id": [""],
    "s": [""], "p": [""], "o": [""],
}

_POINT_VALID_VALUES = {d: [0.0, 0.5, 1.0] for d in _VALID_POINT}
_POINT_KEY_INSERTIONS = [("extra_point_key", 0.3), ("structural2", 0.1)]
_POINT_INVALID_WELL_TYPED = {d: [1.5, -0.5, float("nan"), float("inf")] for d in _VALID_POINT}


def _mutate(
    doc: dict, rng: random.Random, keys: list,
    valid_values: dict | None = None, key_insertions: list | None = None,
    invalid_well_typed: dict | None = None,
) -> dict:
    out = dict(doc)
    n = rng.randint(1, 2)  # fewer simultaneous mutations -> a higher valid fraction (item 6)
    for key in rng.sample(keys, min(n, len(keys))):
        choice = rng.random()
        if choice < 0.35 and valid_values and key in valid_values:
            out[key] = rng.choice(valid_values[key])  # near-miss: stays valid
        elif choice < 0.50 and invalid_well_typed and key in invalid_well_typed:
            # Same JSON kind as a valid value, but out
            # of range/fractional/negative/NaN-inf -- exercises a BOUND
            # check specifically, not merely a basic-type check.
            out[key] = rng.choice(invalid_well_typed[key])
        elif choice < 0.65 and key in out and key != "profile_id" and key != "s" \
                and key != "p" and key != "o" and key != "dimension" and key != "provenance":
            del out[key]  # safe for an OPTIONAL field (reverts to its default); stays valid
        elif choice < 0.75:
            out[key] = rng.choice(_TYPE_SWAPS)
        elif choice < 0.82:
            out[key] = rng.choice(_UNHASHABLE)
        elif choice < 0.90 and key == "tiebreak_salt":
            out[key] = ""  # empty tiebreak_salt — a named key-level mutation (item 6)
        elif key_insertions:
            k2, v2 = rng.choice(key_insertions)
            out[k2] = v2  # unknown/extra-key insertion
        else:
            out[key] = rng.choice(_TYPE_SWAPS)
    return out


def _generate(
    baseline: dict, n: int, seed: int,
    valid_values: dict | None = None, key_insertions: list | None = None,
    invalid_well_typed: dict | None = None,
) -> list:
    rng = random.Random(seed)
    keys = list(baseline.keys())
    cases = [dict(baseline)]
    for _ in range(n - 1):
        cases.append(_mutate(baseline, rng, keys, valid_values, key_insertions, invalid_well_typed))
    return cases


# ── oracles: independent re-implementations, never calling the module under test ──
_PROFILE_KNOWN = frozenset({
    "profile_id", "k", "n_min", "r", "d_blend_weights", "link_saturation",
    "anchor_saturation", "point_saturation",
    "clause_cue_saturation", "match_blend_weights", "relational_suppression_scale",
    "confidence_floor", "staleness_window_seconds", "tiebreak_salt",
    "schema_version", "segmenter_digest", "table_digest",
})
_PROFILE_POS_INT_FIELDS = (
    "k", "n_min", "r", "link_saturation", "anchor_saturation",
    "point_saturation", "clause_cue_saturation",
)
#: Positive, FINITE, but not required to be an integer — decided
#: 2026-10-03, just ``relational_suppression_scale``.
_PROFILE_POS_NUMBER_FIELDS = ("relational_suppression_scale",)


def _profile_oracle(doc) -> bool:
    """Independent re-derivation of ``profile.is_valid_profile`` — written
    from spec/SPEC.md §16's own field table, not by inspecting
    ``profile.py``'s source.
    """
    if not isinstance(doc, dict):
        return False
    if set(doc) - _PROFILE_KNOWN:
        return False
    pid = doc.get("profile_id")
    if not isinstance(pid, str) or not pid:
        return False
    for field in _PROFILE_POS_INT_FIELDS:
        if field not in doc:
            continue
        v = doc[field]
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return False
        if not math.isfinite(v) or v != int(v) or v <= 0:
            return False
    for field in _PROFILE_POS_NUMBER_FIELDS:
        if field not in doc:
            continue
        v = doc[field]
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return False
        if not math.isfinite(v) or v <= 0:
            return False
    # fix round, item 3: this oracle
    # must independently reject NaN/inf too — `x < 0` alone does NOT (every
    # comparison with NaN is False in IEEE-754), so a bare `x < 0` guard
    # here would silently disagree with the now-fixed real code.
    for field in ("d_blend_weights", "match_blend_weights"):
        if field not in doc:
            continue
        w = doc[field]
        key_a, key_b = ("links", "nesting") if field == "d_blend_weights" else ("term", "structural")
        if not isinstance(w, dict) or set(w) != {key_a, key_b}:
            return False
        a, b = w.get(key_a), w.get(key_b)
        for x in (a, b):
            if isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) or x < 0:
                return False
        total = (a or 0) + (b or 0)
        # Two individually finite weights can still
        # sum to a non-finite float (overflow) — the independent oracle
        # must reject that too, matching the now-fixed real code.
        if not math.isfinite(total) or total <= 0:
            return False
    if "confidence_floor" in doc:
        v = doc["confidence_floor"]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not (0.0 <= v <= 1.0):
            return False
    if "staleness_window_seconds" in doc:
        v = doc["staleness_window_seconds"]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            return False
    for field in ("tiebreak_salt", "schema_version", "segmenter_digest", "table_digest"):
        if field not in doc:
            continue
        v = doc[field]
        if not isinstance(v, str) or not v:
            return False
    return True


def _triple_oracle(doc) -> bool:
    """Independent re-derivation of ``triple.is_valid_triple``."""
    if not isinstance(doc, dict):
        return False
    for field in ("s", "p", "o"):
        v = doc.get(field)
        if not isinstance(v, str) or not v:
            return False
    dim = doc.get("dimension")
    if dim not in ("structural", "causal", "intentional", "temporal", "relational"):
        return False
    w = doc.get("weight", 1.0)
    if isinstance(w, bool) or not isinstance(w, (int, float)) or not (0.0 <= w <= 1.0):
        return False
    if "provenance" not in doc:
        return False
    if "grammar_id" in doc:
        g = doc["grammar_id"]
        if not isinstance(g, str) or not g:
            return False
    return True


try:
    import jsonschema
    import json
    from pathlib import Path
    _JSONSCHEMA_AVAILABLE = True
    _SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schema"

    def _schema(name: str) -> dict:
        return json.loads((_SCHEMA_DIR / name).read_text(encoding="utf-8"))

    def _schema_valid(schema_name: str, instance) -> bool:
        schema = _schema(schema_name)
        validator_cls = jsonschema.validators.validator_for(schema)
        return validator_cls(schema).is_valid(instance)
except ImportError:
    _JSONSCHEMA_AVAILABLE = False


def _contains_nan(value) -> bool:
    """True iff ``value`` (recursively, through a dict/list) contains a
    float NaN or +-infinity anywhere. JSON Schema's own range keywords
    (minimum/maximum) are a KNOWN, DOCUMENTED no-op against NaN (``nan < X``
    and ``nan > X`` are both False in IEEE-754, so a "number" field's range
    check never fires for it) and against +-infinity when no opposing
    bound is set (``inf >= 0`` is True, so a bare ``minimum`` alone never
    rejects it) — JSON itself has NEITHER a NaN NOR an Infinity literal at
    all (standard JSON numbers are always finite), so both are a
    pre-existing JSON Schema expressiveness gap, not a code defect (fix
    round, item 3, widened from NaN-only: the real code now independently
    rejects +-infinity too, the same gap this function already named for
    NaN) — used to EXCLUDE such cases from the schema leg of the
    differential below, never from the oracle leg (which correctly
    rejects both).
    """
    if isinstance(value, float) and (value != value or value in (float("inf"), float("-inf"))):
        return True
    if isinstance(value, dict):
        return any(_contains_nan(v) for v in value.values())
    if isinstance(value, (list, tuple)):
        return any(_contains_nan(v) for v in value)
    return False


def test_profile_violations_never_crashes_and_has_a_healthy_valid_fraction():
    cases = _generate(_VALID_PROFILE, _N_PROFILE, _SEED, _PROFILE_VALID_VALUES, _PROFILE_KEY_INSERTIONS, _PROFILE_INVALID_WELL_TYPED)
    valid = 0
    for doc in cases:
        try:
            violations = profile.profile_violations(doc)
        except Exception as exc:  # noqa: BLE001 - this IS the crash-safety assertion
            raise AssertionError(f"profile_violations() raised {exc!r} on {doc!r}") from exc
        assert isinstance(violations, list)
        ours = violations == []
        oracle = _profile_oracle(doc)
        assert ours == oracle, (doc, "code", ours, "oracle", oracle)
        if _JSONSCHEMA_AVAILABLE and isinstance(doc, dict) and not _contains_nan(doc):
            schema_says = _schema_valid("resolution-profile.schema.json", doc)
            assert ours == schema_says, (doc, "code", ours, "schema", schema_says)
        if ours:
            valid += 1
    fraction = valid / len(cases)
    assert fraction >= _MIN_VALID_FRACTION_PROFILE, (
        f"only {fraction:.2%} of {len(cases)} mutated profiles were valid, "
        f"expected >= {_MIN_VALID_FRACTION_PROFILE:.0%}")


def test_profile_digest_never_crashes_on_a_valid_mutant():
    """Every mutant :func:`profile.profile_violations` itself calls VALID
    must also survive :func:`profile.profile_digest` without raising."""
    cases = _generate(_VALID_PROFILE, _N_PROFILE, _SEED + 1, _PROFILE_VALID_VALUES, _PROFILE_KEY_INSERTIONS, _PROFILE_INVALID_WELL_TYPED)
    checked = 0
    for doc in cases:
        if profile.profile_violations(doc) != []:
            continue
        profile.profile_digest(doc)  # must not raise
        checked += 1
    assert checked > 0


def test_triple_violations_never_crashes_and_has_a_healthy_valid_fraction():
    cases = _generate(_VALID_TRIPLE, _N_TRIPLE, _SEED + 2, _TRIPLE_VALID_VALUES, _TRIPLE_KEY_INSERTIONS, _TRIPLE_INVALID_WELL_TYPED)
    valid = 0
    for doc in cases:
        try:
            violations = triple.triple_violations(doc)
        except Exception as exc:  # noqa: BLE001
            raise AssertionError(f"triple_violations() raised {exc!r} on {doc!r}") from exc
        assert isinstance(violations, list)
        ours = violations == []
        oracle = _triple_oracle(doc)
        assert ours == oracle, (doc, "code", ours, "oracle", oracle)
        if _JSONSCHEMA_AVAILABLE and isinstance(doc, dict) and not _contains_nan(doc):
            schema_says = _schema_valid("triple.schema.json", doc)
            assert ours == schema_says, (doc, "code", ours, "schema", schema_says)
        if ours:
            valid += 1
    fraction = valid / len(cases)
    assert fraction >= _MIN_VALID_FRACTION_TRIPLE, (
        f"only {fraction:.2%} of {len(cases)} mutated triples were valid, "
        f"expected >= {_MIN_VALID_FRACTION_TRIPLE:.0%}")


def test_point_violations_never_crashes_and_has_a_healthy_valid_fraction():
    cases = _generate(_VALID_POINT, _N_POINT, _SEED + 4, _POINT_VALID_VALUES, _POINT_KEY_INSERTIONS, _POINT_INVALID_WELL_TYPED)
    valid = 0
    for doc in cases:
        try:
            violations = point.point_violations(doc)
        except Exception as exc:  # noqa: BLE001
            raise AssertionError(f"point_violations() raised {exc!r} on {doc!r}") from exc
        assert isinstance(violations, list)
        ours = violations == []
        if _JSONSCHEMA_AVAILABLE and isinstance(doc, dict) and not _contains_nan(doc):
            schema_says = _schema_valid("point.schema.json", doc)
            assert ours == schema_says, (doc, "code", ours, "schema", schema_says)
        if ours:
            valid += 1
    fraction = valid / len(cases)
    assert fraction >= _MIN_VALID_FRACTION_POINT, (
        f"only {fraction:.2%} of {len(cases)} mutated points were valid, "
        f"expected >= {_MIN_VALID_FRACTION_POINT:.0%}")


# fix round, item 5 (SC2): a DEDICATED
# boundary-value differential — every positive-integer profile field at
# its own boundary (0, the smallest rejected value) must be rejected by
# BOTH the code and the schema, not left to a random fuzz draw that might
# never happen to isolate exactly this field on exactly this value.
@pytest.mark.skipif(not _JSONSCHEMA_AVAILABLE, reason="jsonschema not importable")
@pytest.mark.parametrize("field", sorted(set(_PROFILE_POS_INT_FIELDS) | {"clause_cue_saturation"}))
def test_resolution_profile_positive_integer_boundary_zero_rejected_by_code_and_schema(field):
    doc = {"profile_id": "boundary-fixture", field: 0}
    assert not profile.is_valid_profile(doc), field
    assert not _schema_valid("resolution-profile.schema.json", doc), field


# ══════════════════════════════════════════════════════════════════════════
# Fix round (owner-approved integration step, 2026-10-02): clause_cues
# (§8a) and match (§19) fuzz — same method (seeded, mutation-based,
# crash-safety + an independent oracle), applied to this round's own
# additions.
# ══════════════════════════════════════════════════════════════════════════
from five_d_nd import clause_cues, match  # noqa: E402

_N_CLAUSE_CUES = 300
_N_MATCH = 300
_MIN_VALID_FRACTION_MATCH = 0.20

_CLAUSE_CUE_FRAGMENTS = [
    "The controller shall", "the processor shall", "within one month",
    "for the purposes of compliance", "where processing is necessary",
    "referred to in paragraph 2", "Article 6(1)", "Article 9",
    "the data subject", "the supervisory authority", "", "   ", "!!",
    "because the system triggers an alert", "a risk results",
    "without undue delay", "notify the authority", "cooperate",
    "0123456789", "unicode café façade naïve",
    # One host-instrument and one external-instrument
    # citation, so the independent oracle is exercised on exactly that
    # distinction.
    "Article 6 of this Regulation",
    "Article 25(6) of Directive 95/46/EC",
]


def _random_sentence(rng: random.Random) -> str:
    n = rng.randint(0, 6)
    return " ".join(rng.choice(_CLAUSE_CUE_FRAGMENTS) for _ in range(n))


# fix round, item 4b: §20 claimed an
# independent oracle for the clause_cues fuzz that did not exist. This is a
# REAL one — a fresh, separately-typed transcription of §8a's own cue
# table (one combined alternation per dimension, written by reading the
# spec's table, never by importing or inspecting clause_cues.CUE_TABLE) —
# checked for AGREEMENT on which dimensions FIRE AT ALL (a boolean per
# dimension), not on the exact de-duplicated count (that finer-grained
# invariant is the vectors' own job, not this oracle's).
_ORACLE_CAUSAL_RE = re.compile(
    r"\b(?:if|where|because|unless|results?\s+(?:in|from)|resulting\s+in|enables?|"
    r"provided\s+that|in\s+the\s+event\s+(?:of|that)|owing\s+to|as\s+a\s+result\s+of|"
    r"given\s+that|due\s+to|causes?|caused|triggers?|triggered|triggering|"
    r"leads?\s+to|leading\s+to|give\s+rise\s+to|risks?|likely\s+to|prevents?|"
    r"prevented|preventing|affects?|affected|affecting)\b", re.IGNORECASE)
_ORACLE_INTENTIONAL_RE = re.compile(
    r"\b(?:for\s+the\s+purposes?\s+of|in\s+order\s+to|aimed\s+at|with\s+(?:a\s+)?view\s+to|"
    r"intended\s+to|so\s+as\s+to|to\s+(?:ensure|protect|enable|facilitate|safeguard|guarantee)|"
    r"necessary\s+for|objectives?|seeks?\s+to|seeking\s+to|in\s+order\s+that|purposes?\s+of)\b",
    re.IGNORECASE)
_ORACLE_TEMPORAL_RE = re.compile(
    r"\bwithin\s+\d+\s*(?:hour|day|week|month|year)s?\b|"
    r"\bwithin\s+(?:one|two|three|four|five|six|seven|eight|nine|ten)\s+"
    r"(?:hour|day|week|month|year)s?\b|"
    r"\bwithin\s+(?:a|the)\s+(?:period|time\s+limit|deadline)\b|"
    r"\bwithout\s+undue\s+delay\b|\bbefore\b|\bafter\b|\bprior\s+to\b|"
    r"\bno\s+later\s+than\b|\bat\s+the\s+latest\b|\bas\s+soon\s+as\s+possible\b|"
    r"\bonce\b|\bfollowing\b|\bduring\b|\bperiods?\b|\bdeadlines?\b|"
    r"\bsubsequently\b|\bat\s+the\s+time\s+of\b|\bby\s+\d\b", re.IGNORECASE)
#: Independently re-derives the SAME two
#: behaviours the real cue table adds — a quote-scoped
#: "means" definition, and an Article citation that is NOT immediately
#: followed by an external-instrument phrase (bare "of this/the
#: Regulation" stays internal and so STILL counts as firing; "of
#: Directive"/"of Regulation <name>"/"of the Treaty" directly after the
#: citation does NOT count).
_ORACLE_STRUCTURAL_RE = re.compile(
    r"\bpart\s+of\b|\bconsists?\s+of\b|\bconsisting\s+of\b|"
    r"\bmeans\s+(?:any|a|an|the)\b|"
    "[’']" r"[^’']{0,30}means\b|"
    r"\breferred\s+to\s+in(?:\s+paragraph)?\b|"
    r"\bcomprises?|\bcomprised\b|\bcomprising\b|\bis\s+composed\s+of\b|"
    r"\bcomposed\s+of\b|\bincludes?|\bincluded\b|"
    r"\bcategor(?:y|ies|ised|ized)\b|\bdefinitions?\b|\bpursuant\s+to\b|"
    r"\bin\s+accordance\s+with\b|\bChapter\s+[IVXLCDM]+\b|\bparagraph\s+\d+\b|"
    r"\bAnnex\b|\bset\s+out\s+in\b|"
    r"\bArticles?\s+\d+\b(?!\s*(?:\(\d+\))?\s*of\s+(?:(?:the|that|this)\s+)?Directive\b)"
    r"(?!\s*(?:\(\d+\))?\s*of\s+(?:the\s+)?Treaty\b)"
    r"(?!\s*(?:\(\d+\))?\s*of\s+Regulation\b)",
    re.IGNORECASE)
_ORACLE_RELATIONAL_RE = re.compile(
    r"\bcontrollers?\b|\bprocessors?\b|\bdata\s+subjects?\b|\bthird\s+part(?:y|ies)\b|"
    r"\bsupervisory\s+authorit(?:y|ies)\b|\bjoint\s+controllers?\b|\brepresentatives?\b|"
    r"\brecipients?\b|\bnatural\s+persons?\b|\bright\s+to\b|\bobligations?\b|\bbetween\b",
    re.IGNORECASE)


def _clause_cues_fires_oracle(text: str) -> dict:
    """Independent re-derivation of WHICH dimensions §8a's cue table fires
    on for ``text`` — a boolean per dimension, never calling into
    ``clause_cues`` at all. Fix round, decided 2026-10-03: `relational`'s
    own down-weighting formula (`relational_effective`) is `count * s /
    (s + n_other)`, which is exactly zero IFF `count == 0` (since `s /
    (s + n_other)` is always strictly positive for a finite `s > 0` and
    `n_other >= 0`) — so "fires" for `relational` is simply "the cue
    table itself matched", regardless of what else fired, unlike the
    PREVIOUS all-or-nothing gate this oracle used to model."""
    non_relational_fires = {
        "causal": bool(_ORACLE_CAUSAL_RE.search(text)),
        "intentional": bool(_ORACLE_INTENTIONAL_RE.search(text)),
        "temporal": bool(_ORACLE_TEMPORAL_RE.search(text)),
        "structural": bool(_ORACLE_STRUCTURAL_RE.search(text)),
    }
    relational_fires = bool(_ORACLE_RELATIONAL_RE.search(text))
    return {**non_relational_fires, "relational": relational_fires}


def _relational_effective_oracle(count, n_other, scale=1):
    """Independent re-derivation of ``clause_cues.relational_effective``,
    written from spec/SPEC.md §8a's own formula, not by inspecting
    ``clause_cues.py``'s source."""
    return round(count * scale / (scale + n_other), 6)


def test_relational_effective_agrees_with_an_independent_oracle_and_properties():
    rng = random.Random(_SEED + 13)
    for _ in range(200):
        count = rng.choice([0, 1, 2, 3, 5, 10])
        n_other = rng.choice([0, 1, 2, 3, 4, 10])
        scale = rng.choice([0.5, 1, 2, 5])
        got = clause_cues.relational_effective(count, n_other, scale)
        assert got == _relational_effective_oracle(count, n_other, scale)
        # property: n_other == 0 -> no change
        assert clause_cues.relational_effective(count, 0, scale) == count
        # property: monotone non-increasing in n_other
        got_more = clause_cues.relational_effective(count, n_other + 1, scale)
        assert got_more <= got
    # property: at the default scale (1), one extra cue at most halves the value
    assert clause_cues.relational_effective(5, 0) == 5
    assert clause_cues.relational_effective(5, 1) == 2.5
    for _ in range(20):
        count = rng.choice([1, 2, 3, 5, 10])
        n_other = rng.choice([0, 1, 2, 5])
        halved = clause_cues.relational_effective(count, n_other, 1)
        once_more = clause_cues.relational_effective(count, n_other + 1, 1)
        assert once_more >= halved / 2 - 1e-9


def test_relational_effective_rejects_bad_scale():
    """``relational_effective`` must reject ``scale``
    that is zero, negative, non-finite, or a bool — a mutant that weakens
    the ``<= 0`` check to ``< 0`` (silently accepting ``scale == 0``, a
    division by zero waiting to happen) must be caught here."""
    for bad_scale in (0, -1, -0.5, float("nan"), float("inf"), float("-inf"), True, False):
        with pytest.raises(ValueError):
            clause_cues.relational_effective(1, 0, bad_scale)
    # the boundary just above zero is accepted.
    clause_cues.relational_effective(1, 0, 1e-9)


def test_clause_cue_contributions_agrees_with_an_independent_fires_oracle():
    rng = random.Random(_SEED + 12)
    checked = 0
    for _ in range(_N_CLAUSE_CUES):
        text = _random_sentence(rng)
        raw = clause_cues.clause_cue_contributions(text)
        oracle_fires = _clause_cues_fires_oracle(text)
        for dim in ("causal", "intentional", "temporal", "structural", "relational"):
            assert (raw[dim] > 0) == oracle_fires[dim], (text, dim, raw, oracle_fires)
        checked += 1
    assert checked > 0


def test_clause_cue_contributions_never_crashes_on_arbitrary_text():
    """Crash-safety floor (round rule item 6): every clause, however
    degenerate (empty, whitespace-only, punctuation-only, unicode,
    cue-free), must return a well-shaped all-dimension raw-count mapping —
    never raise anything other than ``ValueError`` on a non-string input,
    which this fuzz never constructs (every generated case IS a string)."""
    rng = random.Random(_SEED + 10)
    n_with_hits = 0
    for _ in range(_N_CLAUSE_CUES):
        text = _random_sentence(rng)
        raw = clause_cues.clause_cue_contributions(text)
        assert set(raw) == set(clause_cues.DIMENSIONS)
        # `relational` is a down-weighted FLOAT (decided 2026-10-03); the
        # other four stay plain non-negative integer counts.
        for dim, v in raw.items():
            if dim == "relational":
                assert isinstance(v, (int, float)) and not isinstance(v, bool) and v >= 0
            else:
                assert isinstance(v, int) and v >= 0
        # decided 2026-10-03: `relational` is DOWN-WEIGHTED, not gated —
        # it MAY be nonzero even when other dimensions also fired, but it
        # must then be STRICTLY SMALLER than the undiminished count the
        # relational cue table alone would have produced (monotone
        # non-increasing in n_other, five_d_nd.clause_cues.relational_effective).
        n_other = raw["structural"] + raw["causal"] + raw["intentional"] + raw["temporal"]
        undiminished = clause_cues.count_cue_hits(text, "relational")
        if n_other == 0:
            assert raw["relational"] == undiminished, (text, raw)
        elif undiminished > 0:
            assert 0 < raw["relational"] < undiminished or undiminished == 0, (text, raw)
        if any(raw.values()):
            n_with_hits += 1
    assert n_with_hits > 0  # the fragment pool actually exercises the cue tables


_MATCH_VALID_VALUES = {
    "term_score": [0.0, 0.25, 0.5, 0.75, 1.0],
    "structural_score": [0.0, 0.25, 0.5, 0.75, 1.0],
}
_MATCH_INVALID_WELL_TYPED = {
    "term_score": [1.5, -0.5, float("nan"), float("inf")],
    "structural_score": [1.5, -0.5, float("nan"), float("inf")],
}


#: This oracle's
#: OWN literal default weights, written from spec/SPEC.md §19's own
#: stated pair — reading ``match.DEFAULT_MATCH_BLEND_WEIGHTS`` here would
#: make the oracle agree with the code BY CONSTRUCTION on a mutation to
#: that constant, defeating the point of an independent check.
_ORACLE_DEFAULT_MATCH_BLEND_WEIGHTS = {"term": 0.7, "structural": 0.3}


def _match_oracle(term_score, structural_score, weights) -> "float | None":
    """Independent re-derivation of ``match.combine_scores`` — written
    from spec/SPEC.md §19's own formula, not by inspecting ``match.py``'s
    source. Returns ``None`` when the oracle itself would reject the
    input (mirrors ``combine_scores`` raising ``ValueError``)."""
    for v in (term_score, structural_score):
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            return None
        if not math.isfinite(v) or not (0.0 <= v <= 1.0):
            return None
    w = weights if weights is not None else _ORACLE_DEFAULT_MATCH_BLEND_WEIGHTS
    if not isinstance(w, dict) or set(w) != {"term", "structural"}:
        return None
    tw, sw = w["term"], w["structural"]
    # fix round item 3: `v < 0` alone does not reject NaN/inf (IEEE-754);
    # `math.isfinite` closes that independently here too.
    for v in (tw, sw):
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0:
            return None
    total = float(tw) + float(sw)
    if not math.isfinite(total) or total <= 0:
        return None
    return round((float(tw) * term_score + float(sw) * structural_score) / total, 6)


def test_combine_scores_never_crashes_except_valueerror_and_matches_oracle():
    rng = random.Random(_SEED + 11)
    valid = 0
    n = 0
    for _ in range(_N_MATCH):
        n += 1
        term_score = rng.choice(
            _MATCH_VALID_VALUES["term_score"] + _MATCH_INVALID_WELL_TYPED["term_score"])
        structural_score = rng.choice(
            _MATCH_VALID_VALUES["structural_score"] + _MATCH_INVALID_WELL_TYPED["structural_score"])
        weights_choice = rng.random()
        if weights_choice < 0.6:
            weights = None
        elif weights_choice < 0.8:
            weights = {"term": rng.choice([0.0, 0.3, 0.7, 1.0]),
                       "structural": rng.choice([0.0, 0.3, 0.7, 1.0])}
        elif weights_choice < 0.88:
            weights = {"term": rng.choice([0.0, 0.3])}  # malformed: missing key
        else:
            # fix round item 3: NaN/inf/negative/bool weights, fuzzed
            # independently (not only exercised by a hand-picked vector).
            weights = {"term": rng.choice([float("nan"), float("inf"), float("-inf"), -0.5, True]),
                       "structural": rng.choice([0.3, 0.7, float("nan"), -0.2])}
        oracle = _match_oracle(term_score, structural_score, weights)
        try:
            got = match.combine_scores(term_score, structural_score, weights)
        except ValueError:
            assert oracle is None, (term_score, structural_score, weights, "oracle said", oracle)
            continue
        except Exception as exc:  # noqa: BLE001
            raise AssertionError(
                f"combine_scores() raised {exc!r} on "
                f"{(term_score, structural_score, weights)!r}") from exc
        assert oracle is not None, (term_score, structural_score, weights, "oracle said reject")
        assert got == oracle, (term_score, structural_score, weights, got, oracle)
        valid += 1
    fraction = valid / n
    assert fraction >= _MIN_VALID_FRACTION_MATCH, (
        f"only {fraction:.2%} of {n} mutated match calls were valid, "
        f"expected >= {_MIN_VALID_FRACTION_MATCH:.0%}")


def test_container_position_only_raises_value_error_on_garbage_member_points():
    garbage_points = [
        [], [{}], [{"structural": "not-a-number"}], [{"structural": None}],
        [{d: 2.0 for d in container.DIMENSIONS}],  # out of [0,1] — still a number, no crash expected
        [{"structural": float("nan")}],
        [{"structural": float("inf")}],
        [None], [1, 2, 3],
    ]
    for points in garbage_points:
        try:
            container.container_position(points)
        except ValueError:
            pass
        except Exception as exc:  # noqa: BLE001 — no exception type is excused any more
            raise AssertionError(
                f"container_position() raised undocumented {type(exc).__name__} on {points!r} "
                "— a malformed member point must surface as ValueError or succeed, never crash "
                "with any other exception type") from exc


def test_trimmed_top_k_match_only_raises_value_error_on_garbage_members():
    """Fix round item 3: NO exception type is excused any more — every
    member field (``claim_id``, ``weight``, ``operative``, ``point``) is
    now validated BEFORE ranking (``container.trimmed_top_k_match``'s own
    per-member loop), so a malformed shape is ALWAYS ``ValueError``, never
    a bare comparison ``TypeError`` leaking from the sort key.
    """
    garbage = [
        [], [{}], [{"claim_id": "a"}],
        [{"claim_id": "a", "weight": "x", "point": {d: 0.0 for d in container.DIMENSIONS}}],
        [{"claim_id": "a", "weight": None, "point": {d: 0.0 for d in container.DIMENSIONS}}],
        [{"claim_id": "a", "weight": float("nan"), "point": {d: 0.0 for d in container.DIMENSIONS}}],
        [{"claim_id": "a", "weight": 1.0, "operative": "yes", "point": {d: 0.0 for d in container.DIMENSIONS}}],
        [{"claim_id": "", "weight": 1.0, "point": {d: 0.0 for d in container.DIMENSIONS}}],
    ]
    for members in garbage:
        try:
            container.trimmed_top_k_match(members, k=5, n_min=3, salt="s")
        except ValueError:
            pass
        except Exception as exc:  # noqa: BLE001
            raise AssertionError(
                f"trimmed_top_k_match() raised undocumented {type(exc).__name__} "
                f"on {members!r} — fix round item 3: no exception type is excused") from exc


def test_conceptual_depth_only_raises_value_error_on_garbage_input():
    empty_graph = {"concept_links": {}, "anchor_links": {}}
    dag0 = container.empty_dag()
    garbage_kwargs = [
        {"r": -1}, {"r": 1.5}, {"link_saturation": 0}, {"anchor_saturation": -1},
        {"w_links": 0.0, "w_nesting": 0.0},
    ]
    for kwargs in garbage_kwargs:
        try:
            depth.conceptual_depth(empty_graph, dag0, "X", **kwargs)
        except ValueError:
            pass
        except Exception as exc:  # noqa: BLE001
            raise AssertionError(f"conceptual_depth() raised {exc!r} on {kwargs!r}") from exc
    # Large, non-negative counts must saturate smoothly, never overflow/crash.
    big_graph = {"concept_links": {"X": [f"p{i}" for i in range(10_000)]}, "anchor_links": {}}
    assert 0.0 <= depth.conceptual_depth(big_graph, dag0, "X") <= 1.0


def test_fixed_mean_only_raises_value_error_on_non_positive_n():
    for n in (0, -1, -100):
        try:
            fixedpoint.fixed_mean(1000, n)
        except ValueError:
            pass
        except Exception as exc:  # noqa: BLE001
            raise AssertionError(f"fixed_mean() raised {exc!r} on n={n!r}") from exc


def test_point_from_contributions_only_raises_value_error_on_malformed_contributions():
    garbage = [
        {"structural": -1}, {"bogus-dimension": 1}, {}, {"structural": 0},
    ]
    for raw in garbage:
        try:
            point.point_from_contributions(raw)
        except ValueError:
            pass
        except Exception as exc:  # noqa: BLE001
            raise AssertionError(f"point_from_contributions() raised {exc!r} on {raw!r}") from exc
    # saturation itself must be validated too (zero/negative is ValueError).
    for bad_saturation in (0, -1):
        try:
            point.point_from_contributions({"structural": 1}, bad_saturation)
        except ValueError:
            pass
        except Exception as exc:  # noqa: BLE001
            raise AssertionError(f"point_from_contributions() raised {exc!r} on saturation={bad_saturation!r}") from exc
