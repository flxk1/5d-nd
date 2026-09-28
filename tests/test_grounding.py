# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""Self-contained tests for the thin ``5d+nd`` resolver seam.

``canonicalize``/``digest``/``validate`` tests are stdlib-only. The
``resolve``/``normalize_reference``/``content_digest`` tests below need the
``versum`` package (the ``grounding`` extra) and are skipped, not failed, when
it is not importable.
"""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import pytest

from five_d_nd.dimensions import Dimension
from five_d_nd.grounding import (
    SCHEME,
    MalformedReferenceError,
    MissingStoreError,
    SpanMismatchError,
    UnknownReferenceError,
    canonicalize,
    content_digest,
    digest,
    normalize_reference,
    resolve,
    validate,
)


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


def test_digest_unchanged_vs_head_3ac16be():
    # LITERAL regression: digest(ref) for this exact ref, byte-for-byte, as it
    # was at HEAD 3ac16be (before resolve()/normalize_reference()/
    # content_digest() were added) — canonicalize()/digest() were NOT touched.
    ref = {
        "dimensions": ["causal", "structural"],
        "anchor": "versum://research/note-7#span-42",
    }
    assert canonicalize(ref) == (
        b'{"anchor":"versum://research/note-7#span-42",'
        b'"dimensions":["causal","structural"]}'
    )
    assert digest(ref) == {
        "sha256": "7cb2f366178369f31776d5855a369d23b792bd7e9bf00cc5f8312894a0d17c37"
    }


def test_resolve_rejects_malformed_dimensioned_ref_before_touching_a_store():
    # Invalid dimensioned ref: fails closed before it would ever touch a store
    # or even look at the anchor string (unchanged pre-existing contract).
    try:
        resolve({"dimensions": ["nope"], "anchor": "u://x"})
    except ValueError:
        pass
    else:
        raise AssertionError("resolve() should reject a malformed reference")


def test_resolve_requires_store_and_fails_closed_when_missing():
    ref = {
        "dimensions": [Dimension.RELATIONAL.value],
        "anchor": "urn:example:doc#0-10",
    }
    try:
        resolve(ref, store=None)
    except MissingStoreError:
        pass
    else:
        raise AssertionError("resolve() should fail closed when store is None")


# ── normalize_reference: canonical + both legacy forms ──────────────────────
def test_normalize_reference_canonical_is_returned_as_is():
    assert normalize_reference("urn:dls:sha256:abc123#11-88") == "urn:dls:sha256:abc123#11-88"


def test_normalize_reference_legacy_versum_uri_normalises_to_canonical():
    got = normalize_reference("versum://policy/p1#span-150-240")
    assert got == "versum://policy/p1#150-240"


def test_normalize_reference_legacy_unit_form_normalises_to_canonical_dropping_unit():
    got = normalize_reference("urn:dls:sha256:abc123#sentence:11-88")
    assert got == "urn:dls:sha256:abc123#11-88"


def test_normalize_reference_rejects_malformed_forms():
    for bad in (
        "not-a-reference-at-all",
        "urn:x#not-a-span",
        "urn:x#12",              # no end offset
        "urn:x#-5-10",           # negative-looking / malformed
        "",
        None,
        42,
        {"anchor": "urn:x#1-2"},
    ):
        try:
            normalize_reference(bad)
        except MalformedReferenceError:
            pass
        else:
            raise AssertionError(f"normalize_reference should reject {bad!r}")


def test_normalize_reference_rejects_inverted_bounds():
    try:
        normalize_reference("urn:x#10-1")
    except MalformedReferenceError:
        pass
    else:
        raise AssertionError("normalize_reference should reject end < start")


# ── resolve() against the real credit_policy_nd fixture (versum public API) ─
try:
    import versum as _versum  # noqa: F401
    from versum import coordinates as _versum_coordinates_mod
    from versum import planes as _planes
    from versum.store.index import index_folder as _index_folder

    if not hasattr(_versum_coordinates_mod, "entry_coordinates"):
        raise ImportError(
            "versum.coordinates has no entry_coordinates (installed versum "
            "is older than the 'coordinates' feature)"
        )
    _VERSUM_AVAILABLE = True
    _VERSUM_UNAVAILABLE_REASON = ""
except ImportError as _versum_import_exc:
    _VERSUM_AVAILABLE = False
    _VERSUM_UNAVAILABLE_REASON = (
        "versum (the 'grounding' extra) is not installed, or lacks "
        f"versum.coordinates.entry_coordinates: {_versum_import_exc}"
    )

_versum_required = pytest.mark.skipif(
    not _VERSUM_AVAILABLE,
    reason=_VERSUM_UNAVAILABLE_REASON or "versum grounding extra unavailable",
)

# Article -> (operator, bearer, content_text) — same fixture, same articles as
# versum's own tests/test_coordinates.py (read-only: never written to).
_ARTICLES = [
    ("F", "lender", "make a solely automated decision on a credit application"),
    ("P", "lender", "use the score to prepare a decision"),
    ("O", "reviewer", "examine every rejection"),
    ("O", "controller", "inform the applicant of the main factors of the score"),
]


def _versum_repo_root() -> Path:
    # versum is editable-installed; its __file__ resolves to the real source
    # tree, so the sibling repo's committed fixtures are reachable from it —
    # read-only, never written to (this is a 5d-nd territory test file, not a
    # versum one).
    return Path(_versum.__file__).resolve().parents[2]


def _rows(path: Path) -> list:
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


@pytest.fixture(scope="module")
def indexed_store(tmp_path_factory):
    if not _VERSUM_AVAILABLE:
        pytest.skip(_VERSUM_UNAVAILABLE_REASON)
    fixture = _versum_repo_root() / "tests" / "fixtures" / "credit_policy_nd"
    policy_path = fixture / "policy.txt"
    if not policy_path.exists():
        pytest.skip(f"versum fixture unreachable: {policy_path} does not exist")
    policy_text = policy_path.read_text(encoding="utf-8")

    root = tmp_path_factory.mktemp("fivednd-resolve")
    src = root / "src"
    src.mkdir()
    (src / "policy.txt").write_text(policy_text, encoding="utf-8")
    out = root / "out"
    _index_folder(src, "law-eu", out, planes=_planes.DISCOVER)

    entries = _rows(out / "entries.csv")
    claims = [
        json.loads(line)
        for line in (out / "entry_claims.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    deontic_ids = {c["item_id"] for c in claims if c["plane"] == "deontic"}
    norms = sorted(
        (e for e in entries if e["item_id"] in deontic_ids and e["entry_kind"] == "sentence"),
        key=lambda e: int(e["span_start"]),
    )
    return {"out": out, "entries": entries, "norms": norms}


def _norm_ref(norm: dict, dims=(Dimension.INTENTIONAL.value,)) -> dict:
    anchor = f"{norm['source_urn']}#{norm['span_start']}-{norm['span_end']}"
    return {"dimensions": list(dims), "anchor": anchor}


@_versum_required
def test_resolve_returns_literal_nd_norm_span_for_each_article(indexed_store):
    norms = indexed_store["norms"]
    assert len(norms) == 4
    for idx, (operator, bearer, _content_text) in enumerate(_ARTICLES):
        norm = norms[idx]
        ref = _norm_ref(norm)
        result = resolve(ref, store=indexed_store["out"])
        assert result["entry_id"] == norm["item_id"]
        assert result["source_urn"] == norm["source_urn"]
        # OUGHT/norm entry: is/ought — never a 5D dimension.
        assert result["dimension"] is None, (idx, result)
        assert result["span"] == {
            "start": int(norm["span_start"]),
            "end": int(norm["span_end"]),
            "text": norm["text"],
        }
        nd = result["nd"]["loomground-deontic"]
        assert nd["operator"] == operator, (idx, nd)
        assert nd["bearer"] == bearer, (idx, nd)
        assert set(result["content_digest"]) == {"sha256"}
        assert len(result["content_digest"]["sha256"]) == 64


@_versum_required
def test_resolve_returns_literal_5d_action_span(indexed_store):
    # The action-type (5D, factual) entry embedded under the first norm.
    norms = indexed_store["norms"]
    norm = norms[0]
    action = next(
        e
        for e in indexed_store["entries"]
        if e["parent_id"] == norm["item_id"]
        and e["text"] == "make a solely automated decision on a credit application"
    )
    anchor = f"{action['source_urn']}#{action['span_start']}-{action['span_end']}"
    ref = {"dimensions": [Dimension.RELATIONAL.value], "anchor": anchor}
    result = resolve(ref, store=indexed_store["out"])
    assert result["entry_id"] == action["item_id"]
    assert result["dimension"] == "relational"  # 5D: what IS
    assert result["span"]["text"] == action["text"]
    assert result["nd"]["loomground-factual"]["subject"] == "lender"


@_versum_required
def test_normalize_reference_legacy_forms_resolve_to_the_same_literal_span(indexed_store):
    norm = indexed_store["norms"][0]
    canonical_anchor = f"{norm['source_urn']}#{norm['span_start']}-{norm['span_end']}"
    legacy_anchor = f"{norm['source_urn']}#sentence:{norm['span_start']}-{norm['span_end']}"
    assert normalize_reference(legacy_anchor) == canonical_anchor

    ref_canonical = {"dimensions": [Dimension.CAUSAL.value], "anchor": canonical_anchor}
    ref_legacy = {"dimensions": [Dimension.CAUSAL.value], "anchor": legacy_anchor}
    r1 = resolve(ref_canonical, store=indexed_store["out"])
    r2 = resolve(ref_legacy, store=indexed_store["out"])
    assert r1["span"] == r2["span"]
    assert r1["entry_id"] == r2["entry_id"]


@_versum_required
def test_resolve_unknown_urn_fails_closed(indexed_store):
    ref = {
        "dimensions": [Dimension.CAUSAL.value],
        "anchor": "urn:dls:sha256:does-not-exist-at-all#0-5",
    }
    try:
        resolve(ref, store=indexed_store["out"])
    except UnknownReferenceError:
        pass
    else:
        raise AssertionError("resolve() should fail closed on an unknown source urn")


@_versum_required
def test_resolve_out_of_range_span_fails_closed(indexed_store):
    norm = indexed_store["norms"][0]
    # Same urn, wildly out-of-range span -> no entry with that id exists.
    ref = {
        "dimensions": [Dimension.CAUSAL.value],
        "anchor": f"{norm['source_urn']}#100000-100010",
    }
    try:
        resolve(ref, store=indexed_store["out"])
    except UnknownReferenceError:
        pass
    else:
        raise AssertionError("resolve() should fail closed on an out-of-range span")


@_versum_required
def test_resolve_wrong_store_fails_closed(indexed_store, tmp_path_factory):
    # A real, but DIFFERENT, indexed store: the entry id computed from this
    # reference's urn+span will not exist in it.
    other_root = tmp_path_factory.mktemp("fivednd-resolve-other")
    other_src = other_root / "src"
    other_src.mkdir()
    (other_src / "unrelated.txt").write_text("Nothing to see here.", encoding="utf-8")
    other_out = other_root / "out"
    _index_folder(other_src, "law-eu", other_out, planes=_planes.DISCOVER)

    norm = indexed_store["norms"][0]
    ref = _norm_ref(norm)
    try:
        resolve(ref, store=other_out)
    except UnknownReferenceError:
        pass
    else:
        raise AssertionError("resolve() should fail closed against the wrong store")


@_versum_required
def test_resolve_span_text_mismatch_fails_closed(indexed_store, tmp_path_factory, monkeypatch):
    # Simulate a corrupted store: the entry's recorded text no longer matches
    # the length its own recorded offsets declare. resolve() must not trust
    # entries.csv blindly.
    norm = indexed_store["norms"][0]
    corrupt_root = tmp_path_factory.mktemp("fivednd-resolve-corrupt")
    shutil.copytree(indexed_store["out"], corrupt_root / "out")
    corrupt_out = corrupt_root / "out"
    rows = _rows(corrupt_out / "entries.csv")
    for row in rows:
        if row["item_id"] == norm["item_id"]:
            row["text"] = "short"  # length no longer matches span_end - span_start
    with open(corrupt_out / "entries.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    ref = _norm_ref(norm)
    try:
        resolve(ref, store=corrupt_out)
    except SpanMismatchError:
        pass
    else:
        raise AssertionError("resolve() should fail closed on a span/text mismatch")


@_versum_required
def test_content_digest_changes_when_span_text_is_tampered_but_digest_does_not(indexed_store):
    norm = indexed_store["norms"][0]
    ref = _norm_ref(norm)
    result = resolve(ref, store=indexed_store["out"])

    real_digest = digest(ref)
    real_content_digest = result["content_digest"]
    assert real_content_digest == content_digest(ref, result["span"]["text"])

    tampered_text = result["span"]["text"] + " TAMPERED"
    tampered_content_digest = content_digest(ref, tampered_text)

    # digest(ref) is reference-only: unaffected by tampering the span text.
    assert digest(ref) == real_digest
    # content_digest is content-bound: it changes.
    assert tampered_content_digest != real_content_digest


# ── exception contract: MissingStoreError, tested literally ─────────────────
# These three run unconditionally (no versum-availability skip needed): the
# first two fail before resolve() ever tries to import versum, and the third
# forces the ImportError branch via sys.modules regardless of whether versum
# actually happens to be installed in this environment.


def test_resolve_store_none_raises_missing_store_error():
    ref = {"dimensions": [Dimension.CAUSAL.value], "anchor": "urn:x#0-5"}
    with pytest.raises(MissingStoreError):
        resolve(ref, store=None)


def test_resolve_store_int_raises_missing_store_error():
    ref = {"dimensions": [Dimension.CAUSAL.value], "anchor": "urn:x#0-5"}
    with pytest.raises(MissingStoreError):
        resolve(ref, store=42)


def test_resolve_store_empty_string_raises_missing_store_error():
    ref = {"dimensions": [Dimension.CAUSAL.value], "anchor": "urn:x#0-5"}
    with pytest.raises(MissingStoreError):
        resolve(ref, store="")


def test_resolve_versum_not_importable_raises_missing_store_error(monkeypatch):
    import sys

    ref = {"dimensions": [Dimension.CAUSAL.value], "anchor": "urn:x#0-5"}
    # sys.modules[name] = None forces `import name` / `from name import x` to
    # raise ImportError immediately, independent of whether versum is actually
    # installed in this environment — the literal "versum not importable" case.
    monkeypatch.setitem(sys.modules, "versum", None)
    monkeypatch.setitem(sys.modules, "versum.coordinates", None)
    monkeypatch.setitem(sys.modules, "versum.planes", None)
    with pytest.raises(MissingStoreError):
        resolve(ref, store="/some/store/path")


# ── same-length content tampering: length alone must not be trusted ─────────
@_versum_required
def test_resolve_same_length_content_tamper_fails_closed_via_source_text(
    indexed_store, tmp_path_factory
):
    # "must not" -> "shall do" is the SAME length (8 chars); a length-only
    # span check cannot see this. resolve() must fail closed anyway when an
    # independently-held source_text is supplied.
    norm = indexed_store["norms"][0]
    assert "must not" in norm["text"]
    ref = _norm_ref(norm)

    fixture = _versum_repo_root() / "tests" / "fixtures" / "credit_policy_nd"
    real_source_text = (fixture / "policy.txt").read_text(encoding="utf-8")

    corrupt_root = tmp_path_factory.mktemp("fivednd-resolve-same-length-text")
    shutil.copytree(indexed_store["out"], corrupt_root / "out")
    corrupt_out = corrupt_root / "out"
    rows = _rows(corrupt_out / "entries.csv")
    tampered_text = None
    for row in rows:
        if row["item_id"] == norm["item_id"]:
            tampered_text = row["text"].replace("must not", "shall do")
            assert len(tampered_text) == len(row["text"])
            assert len(tampered_text) == int(row["span_end"]) - int(row["span_start"])
            row["text"] = tampered_text
    assert tampered_text is not None
    with open(corrupt_out / "entries.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    # Without an independent ground truth, the length-only check alone cannot
    # see this tamper — demonstrating the exact gap the fix closes.
    unchecked = resolve(ref, store=corrupt_out)
    assert unchecked["span"]["text"] == tampered_text

    # WITH the real source text supplied, resolve() fails closed instead of
    # trusting the store's tampered record.
    with pytest.raises(SpanMismatchError):
        resolve(ref, store=corrupt_out, source_text=real_source_text)


@_versum_required
def test_resolve_same_length_content_tamper_fails_closed_via_expected_content_digest(
    indexed_store, tmp_path_factory
):
    norm = indexed_store["norms"][0]
    assert "must not" in norm["text"]
    ref = _norm_ref(norm)

    good_result = resolve(ref, store=indexed_store["out"])
    good_digest = good_result["content_digest"]

    corrupt_root = tmp_path_factory.mktemp("fivednd-resolve-same-length-digest")
    shutil.copytree(indexed_store["out"], corrupt_root / "out")
    corrupt_out = corrupt_root / "out"
    rows = _rows(corrupt_out / "entries.csv")
    for row in rows:
        if row["item_id"] == norm["item_id"]:
            tampered_text = row["text"].replace("must not", "shall do")
            assert len(tampered_text) == len(row["text"])
            row["text"] = tampered_text
    with open(corrupt_out / "entries.csv", "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    with pytest.raises(SpanMismatchError):
        resolve(ref, store=corrupt_out, expected_content_digest=good_digest)


# ── doc examples: verified against the code, not merely asserted in prose ───
def test_readme_and_llms_txt_digest_example_matches_code():
    # README.md / llms.txt "## Example" block, executed literally.
    ref = {"dimensions": ["temporal", "relational"], "anchor": "versum://policy/p1#span-150-240"}
    assert canonicalize(ref) == (
        b'{"anchor":"versum://policy/p1#span-150-240","dimensions":["temporal","relational"]}'
    )
    assert digest(ref) == {
        "sha256": "4da8b3468ad57b8a4e6c6d2a741876e1b3f00eb8c974df29e540c9517e2a88d2"
    }


@_versum_required
def test_docs_resolve_example_anchor_matches_the_code(indexed_store):
    # README.md / llms.txt / docs/model.md "resolve" examples all use this
    # exact anchor and dimensions list; confirm it resolves to precisely the
    # literal result the docs show (entry_id, dimension, span, operator).
    ref = {
        "dimensions": ["intentional"],
        "anchor": (
            "urn:dls:sha256:defa970572b4d201a900ee509861d597bc206a7d21916082a"
            "43aa56af377e1f4#11-88"
        ),
    }
    result = resolve(ref, store=indexed_store["out"])
    assert result["entry_id"] == "ent-33b8bdf7229b64c8"
    assert result["dimension"] is None  # OUGHT/norm entry: is/ought, as documented
    assert result["span"] == {
        "start": 11,
        "end": 88,
        "text": "The lender must not make a solely automated decision on a credit application.",
    }
    assert result["nd"]["loomground-deontic"]["operator"] == "F"
    assert set(result["content_digest"]) == {"sha256"}


def test_docs_model_dimensions_claim_matches_resolve_behavior():
    # docs/model.md states resolve() does not read/filter/select by
    # `dimensions` — only `anchor` decides what is returned. Two refs that
    # differ only in `dimensions` must canonicalize/digest differently (the
    # field IS part of what gets hashed) while validate() still requires every
    # entry to be a known Dimension.
    ref_a = {"dimensions": ["causal"], "anchor": "urn:x#0-5"}
    ref_b = {"dimensions": ["causal", "temporal"], "anchor": "urn:x#0-5"}
    assert validate(ref_a) is True
    assert validate(ref_b) is True
    assert digest(ref_a) != digest(ref_b)  # dimensions do change the digest...
    # ...but resolve() raises the same MissingStoreError for both regardless of
    # `dimensions` when store is absent — the field plays no role in resolution
    # (raised before `dimensions` could matter at all).
    with pytest.raises(MissingStoreError):
        resolve(ref_a, store=None)
    with pytest.raises(MissingStoreError):
        resolve(ref_b, store=None)
