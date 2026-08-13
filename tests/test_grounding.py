# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""Self-contained tests for the thin ``5d+nd`` resolver seam. Stdlib + pytest."""

from __future__ import annotations

from five_d_nd.dimensions import Dimension
from five_d_nd.grounding import SCHEME, canonicalize, digest, resolve, validate


def _wellformed_ref() -> dict:
    return {
        "dimensions": [Dimension.CAUSAL.value, Dimension.STRUCTURAL.value],
        "anchor": "versum://research/note-7#span-42",
    }


def test_scheme_name():
    # One value among interchangeable peers — not privileged.
    assert SCHEME == "5d+nd"


def test_wellformed_ref_validates_and_digests_stably():
    ref = _wellformed_ref()
    assert validate(ref) is True

    # Same reference (independently constructed) -> identical digest.
    d1 = digest(ref)
    d2 = digest(_wellformed_ref())
    assert d1 == d2
    assert set(d1) == {"sha256"}
    assert len(d1["sha256"]) == 64          # sha256 hex is 64 chars
    int(d1["sha256"], 16)                    # ... and valid hex


def test_enum_members_and_str_values_are_interchangeable():
    # Dimension is a str-enum, so a ref built from enum members canonicalizes to
    # the exact same bytes as one built from the raw strings.
    ref_members = {"dimensions": [Dimension.CAUSAL], "anchor": "u://x"}
    ref_strings = {"dimensions": ["causal"], "anchor": "u://x"}
    assert validate(ref_members) is True
    assert canonicalize(ref_members) == canonicalize(ref_strings)
    assert digest(ref_members) == digest(ref_strings)


def test_unknown_dimension_fails_validate():
    ref = {"dimensions": ["causal", "hyperbolic"], "anchor": "versum://x"}
    assert validate(ref) is False


def test_missing_or_empty_anchor_fails_validate():
    assert validate({"dimensions": ["causal"]}) is False
    assert validate({"dimensions": ["causal"], "anchor": ""}) is False
    assert validate({"dimensions": ["causal"], "anchor": "   "}) is False


def test_empty_or_missing_dimensions_fails_validate():
    assert validate({"dimensions": [], "anchor": "u://x"}) is False
    assert validate({"anchor": "u://x"}) is False


def test_non_mapping_ref_fails_validate():
    assert validate("not a ref") is False
    assert validate(None) is False
    assert validate(["causal"]) is False


def test_canonicalize_is_order_independent():
    a = {"dimensions": ["causal"], "anchor": "u://x"}
    b = {"anchor": "u://x", "dimensions": ["causal"]}  # keys reversed
    assert canonicalize(a) == canonicalize(b)
    assert digest(a) == digest(b)


def test_canonicalize_is_order_independent_nested():
    # Sorting is recursive: a store-span mapping anchor sorts too.
    a = {"dimensions": ["causal"], "anchor": {"folder": "f", "start": 1, "end": 9}}
    b = {"anchor": {"end": 9, "start": 1, "folder": "f"}, "dimensions": ["causal"]}
    assert canonicalize(a) == canonicalize(b)
    assert digest(a) == digest(b)


def test_canonicalize_distinguishes_different_content():
    # List order IS significant (arrays are ordered); different content -> different digest.
    a = {"dimensions": ["causal", "structural"], "anchor": "u://x"}
    b = {"dimensions": ["structural", "causal"], "anchor": "u://x"}
    assert digest(a) != digest(b)


def test_resolve_is_a_documented_stub():
    # Valid ref: the seam is not wired -> NotImplementedError (never fabricates).
    try:
        resolve(_wellformed_ref())
    except NotImplementedError:
        pass
    else:
        raise AssertionError("resolve() should raise NotImplementedError (stub)")

    # Invalid ref: fails closed before it would ever touch a store.
    try:
        resolve({"dimensions": ["nope"], "anchor": "u://x"})
    except ValueError:
        pass
    else:
        raise AssertionError("resolve() should reject a malformed reference")
