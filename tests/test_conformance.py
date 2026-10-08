# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""Conformance vector runner — spec/SPEC.md §10.

Loads every vector under ``conformance/vectors/<family>/*.json`` and checks the
reference implementation reproduces its ``expected`` value. Stdlib + pytest only
for the core runner. Two OPTIONAL differential suites at the bottom of this file
compare the reference implementation against the real upstream it is ported
from — loomground-factual (§8, D1) and versum (§9) — and SKIP (never fail) when
that optional dependency is not importable. A third optional suite validates
every vector's input against its JSON Schema (``schema/``) when ``jsonschema``
is importable, and checks that EVERY descriptor-binding/is-ought vector gets
the SAME verdict from the schema as from the code (§7, N1: 5D is neutral on
is/ought, so code and schema should now agree on every such vector — no
documented divergence is expected or needed any more).

**§9's validator parity policy (P1-P3), encoded here.** The
versum differential tests below (``test_nd_system_matches_versum``,
``test_descriptor_binding_matches_versum``) no longer assert plain equality
between the code's verdict and versum's: they assert the POLICY. P1 (hard,
no exceptions): if versum REJECTS a document, the code MUST reject it too —
a code-accepts/versum-rejects disagreement always FAILS the test, for every
vector, with no excluded case. P2 (documented, named per family): the code
MAY reject a document versum accepts, but ONLY for a vector named in that
family's own ``_*_VERSUM_P2_MALFORMED`` frozenset below — each one a
MALFORMED SHAPE by §9's own definition, with its own file:line rationale in
``src/five_d_nd/contract.py``. A code-reject/versum-accept disagreement on
any OTHER vector still FAILS the test. The schema's own differential tests
(``test_every_nd_system_vector_schema_matches_code``,
``test_every_descriptor_binding_vector_schema_matches_code``) encode P3 the
same way via ``_ND_SYSTEM_SCHEMA_INTENTIONALLY_STRICTER`` (P3: a schema MAY
be stricter than code/versum on a malformed shape — same §9 definition,
applied to the schema/code boundary instead of the code/versum boundary).
"""
from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path

import pytest

from five_d_nd import assertoric, clause_cues, contract, match, position
from five_d_nd import container, depth, fixedpoint, point, profile, statement, triple, views
from five_d_nd import path as typed_path
from five_d_nd.dimensions import Dimension, compose, left_fold
from five_d_nd.grammars import requirement, term
from five_d_nd.grounding import (
    MalformedReferenceError,
    canonicalize,
    digest,
    normalize_reference,
)

ROOT = Path(__file__).resolve().parents[1]
VECTORS_DIR = ROOT / "conformance" / "vectors"
SCHEMA_DIR = ROOT / "schema"

# §10: minimum vector count required per family.
FAMILIES = {
    "dim-closed-set": 6,
    "compose-table": 25,
    "compose-identity": 5,
    "fold-left": 6,
    "position": 6,
    "reference": 6,
    "nd-system": 6,
    "descriptor-binding": 6,
    "is-ought": 3,
    "assertoric-lowering": 6,
    # coordinate round (stage 1, 2026-10-01; fix round) — spec/SPEC.md §11-§17
    "point": 18,
    "fixedpoint": 8,
    "container-average": 6,
    "trimmed-topk": 10,
    "depth": 15,
    "staleness": 20,
    "cycle-rejection": 8,
    "resolution-profile": 15,
    "triple": 8,
    # fix round (owner-approved integration step, 2026-10-02) — spec/SPEC.md
    # §8a (clause cues), §19 (matching), and the two EXAMPLE nD grammars
    "clause-cues": 10,
    "match-blend": 8,
    "term-grammar": 6,
    "requirement-grammar": 6,
    # typed-triple layer — spec/SPEC.md §21-§23
    "statement": 30,
    "path": 8,
    # composition-laws is a SINGLE, EXHAUSTIVE vector (all 125 triples and
    # all 25 pairs) — a larger count would not make it more convincing (§23).
    "composition-laws": 1,
    "worked-example-typed": 1,
    "actor-role": 20,
    "dual-split": 5,
    "path-search": 8,
    "institutional-actor": 13,
}


def _load(family: str) -> list:
    d = VECTORS_DIR / family
    return sorted(d.glob("*.json")) if d.exists() else []


def _case(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("family,minimum", sorted(FAMILIES.items()))
def test_family_meets_minimum_vector_count(family, minimum):
    n = len(_load(family))
    assert n >= minimum, f"family {family!r} has {n} vectors, needs >= {minimum} (§10)"


# ── dim-closed-set ───────────────────────────────────────────────────────────
@pytest.mark.parametrize("path", _load("dim-closed-set"), ids=lambda p: p.stem)
def test_dim_closed_set(path):
    v = _case(path)
    value = v["input"]["value"]
    valid = position.is_dimension(value)
    assert valid == v["expected"]["valid"], v["case"]


# ── compose-table ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize("path", _load("compose-table"), ids=lambda p: p.stem)
def test_compose_table(path):
    v = _case(path)
    a, b = v["input"]["a"], v["input"]["b"]
    result = compose(Dimension(a), Dimension(b)).value
    assert result == v["expected"]["result"], v["case"]


# ── compose-identity ──────────────────────────────────────────────────────────
@pytest.mark.parametrize("path", _load("compose-identity"), ids=lambda p: p.stem)
def test_compose_identity(path):
    v = _case(path)
    d = v["input"]["d"]
    left = compose(Dimension(d), Dimension("relational")).value
    right = compose(Dimension("relational"), Dimension(d)).value
    assert left == v["expected"]["left_with_identity"] == v["expected"]["expected_both"]
    assert right == v["expected"]["identity_with_right"] == v["expected"]["expected_both"]


# ── fold-left ──────────────────────────────────────────────────────────────────
def _fold(dims, left: bool) -> str:
    dims = [Dimension(d) for d in dims]
    if left:
        acc = dims[0]
        for d in dims[1:]:
            acc = compose(acc, d)
        return acc.value
    acc = dims[-1]
    for d in reversed(dims[:-1]):
        acc = compose(d, acc)
    return acc.value


@pytest.mark.parametrize("path", _load("fold-left"), ids=lambda p: p.stem)
def test_fold_left(path):
    v = _case(path)
    dims = v["input"]["path"]
    got_left = left_fold(dims).value
    got_right = _fold(dims, left=False)
    assert got_left == v["expected"]["left_fold"], v["case"]
    assert got_right == v["expected"]["right_fold"], v["case"]
    assert (got_left == got_right) == v["expected"]["associative"], v["case"]


def test_fold_left_includes_both_failing_triples():
    cases = _load("fold-left")
    stems = {p.stem for p in cases}
    assert any("causal-intentional-structural" in s for s in stems)
    assert any("causal-temporal-structural" in s for s in stems)
    non_assoc = [_case(p) for p in cases if not _case(p)["expected"]["associative"]]
    assert len(non_assoc) == 2


# ── position ───────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("path", _load("position"), ids=lambda p: p.stem)
def test_position(path):
    v = _case(path)
    contributions = v["input"]["contributions"]
    if "embeds_count" in v["input"]:
        # §5 rule 3 (versum's containment rule): the SOURCE entry of every
        # outgoing 'embeds' link gets +1 structural, on top of whatever its
        # own claims already contribute.
        contributions = position.with_embeds(contributions, v["input"]["embeds_count"])
    if "error" in v["expected"]:
        error_cls = {"ValueError": ValueError}[v["expected"]["error"]]
        with pytest.raises(error_cls):
            position.fingerprint(contributions)
    else:
        got = position.fingerprint(contributions)
        assert got == v["expected"], v["case"]


# ── reference ──────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("path", _load("reference"), ids=lambda p: p.stem)
def test_reference(path):
    v = _case(path)
    inp = v["input"]
    if "ref" in inp and "canonical" in v["expected"]:
        assert normalize_reference(inp["ref"]) == v["expected"]["canonical"], v["case"]
    elif "ref" in inp and "error" in v["expected"]:
        error_cls = {"MalformedReferenceError": MalformedReferenceError}[v["expected"]["error"]]
        with pytest.raises(error_cls):
            normalize_reference(inp["ref"])
    elif "ref" in inp and "sha256" in v["expected"]:
        assert digest(inp["ref"]) == {"sha256": v["expected"]["sha256"]}, v["case"]
    elif "ref" in inp and "canonicalize_utf8" in v["expected"]:
        assert canonicalize(inp["ref"]).decode("utf-8") == v["expected"]["canonicalize_utf8"], \
            v["case"]
    else:
        raise AssertionError(f"unrecognised reference vector shape: {v}")


# ── nd-system ──────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("path", _load("nd-system"), ids=lambda p: p.stem)
def test_nd_system(path):
    v = _case(path)
    got = contract.is_valid_nd_system(v["input"]["doc"])
    assert got == v["expected"]["valid"], v["case"]


def _nd_system_root_for_coverage(doc):
    """Unwrap a possibly-wrapped NDSystem doc the SAME way
    nd_system_violations() itself does, for the sole purpose of walking
    its OWN axes below — never a validity check (the vector's own
    "expected" already covers that)."""
    if not isinstance(doc, Mapping):
        return {}
    if "nd_system" in doc:
        inner = doc["nd_system"]
        return inner if isinstance(inner, Mapping) else {}
    return doc


def _scalar_or_list_items(value):
    """versum's own _tuple() coercion, inlined here (not imported from
    contract.py, to keep this coverage test independent of contract.py's
    own internals) — a bare scalar means the same as a one-element list."""
    if value is None:
        return ()
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(value)
    return (value,)


def test_nd_system_enum_vectors_cover_every_member():
    """For each FIXED enum in contract.py
    (_VALUE_TYPES, _VOCAB_MODES, _CARDINALITIES, _PRIMITIVES), assert
    every member appears EXPLICITLY in at least one valid nd-system
    vector's own axis fields. Catches exactly the coverage gap where
    rejecting a valid primitive other than "equal" (or
    any value_type/vocabulary_mode/cardinality other than the handful
    already exercised) would pass the whole suite, because
    nothing exercised the REST of each enum. A future enum member added
    to contract.py without an accompanying vector fails this test too —
    see the "all members present" assertions below, one per enum.
    """
    seen_value_types = set()
    seen_cardinalities = set()
    seen_vocabulary_modes = set()
    seen_primitives = set()
    for path in _load("nd-system"):
        v = _case(path)
        if not v["expected"].get("valid"):
            continue
        root = _nd_system_root_for_coverage(v["input"]["doc"])
        axes = root.get("axes")
        if not isinstance(axes, Mapping):
            continue
        for axis in axes.values():
            if not isinstance(axis, Mapping):
                continue
            if "value_type" in axis:
                seen_value_types.add(axis["value_type"])
            if "cardinality" in axis:
                seen_cardinalities.add(axis["cardinality"])
            if "vocabulary_mode" in axis:
                seen_vocabulary_modes.add(axis["vocabulary_mode"])
            if "primitives" in axis:
                seen_primitives.update(_scalar_or_list_items(axis["primitives"]))

    missing_value_types = contract._VALUE_TYPES - seen_value_types
    assert not missing_value_types, (
        f"no VALID nd-system vector exercises value_type(s) {missing_value_types!r} "
        "— add one (§9)")
    missing_cardinalities = contract._CARDINALITIES - seen_cardinalities
    assert not missing_cardinalities, (
        f"no VALID nd-system vector exercises cardinality(ies) {missing_cardinalities!r} "
        "— add one (§9)")
    missing_vocabulary_modes = contract._VOCAB_MODES - seen_vocabulary_modes
    assert not missing_vocabulary_modes, (
        f"no VALID nd-system vector exercises vocabulary_mode(s) "
        f"{missing_vocabulary_modes!r} — add one (§9)")
    missing_primitives = contract._PRIMITIVES - seen_primitives
    assert not missing_primitives, (
        f"no VALID nd-system vector exercises primitive(s) {missing_primitives!r} "
        "— add one (§9)")


# ── descriptor-binding ───────────────────────────────────────────────────────
# 5D is neutral on is/ought (§7, N1-N2 — owner design change, 2026-10-01): a
# normative relation binds to a dimension exactly like any other relation, so
# every descriptor-binding vector now matches versum's own contract exactly
# (see the versum differential suite below, which no longer excludes anything
# for is/ought reasons).
@pytest.mark.parametrize("path", _load("descriptor-binding"), ids=lambda p: p.stem)
def test_descriptor_binding(path):
    v = _case(path)
    require_produce = bool(v["input"].get("require_produce", False))
    got = contract.is_valid_descriptor(v["input"]["descriptor"], require_produce=require_produce)
    assert got == v["expected"]["valid"], v["case"]


def test_descriptor_binding_runtime_form_valid_with_callable_produce():
    # JSON cannot carry a callable, so this one case (the positive side of the
    # runtime-form/produce-required rule) is a plain test, not a vector.
    descriptor = {
        "plane": "x", "language_version": "1",
        "nd_system": {"id": "x", "namespace": "x", "version": "1",
                       "axes": {"subject": {"value_type": "concept_reference"}}},
        "binding": {}, "contract_version": contract.SPEC_VERSION,
        "produce": lambda sentence, context=None: [],
    }
    assert contract.descriptor_violations(descriptor, require_produce=True) == []


# ── is-ought ───────────────────────────────────────────────────────────────────
# 5D is neutral on is/ought (§7, N1): a link carries exactly one dimension and
# nothing else. This family stays focused on §6 (a link carries exactly one
# dimension, never zero or two; an extra field like a grammar's own "mode" is
# simply ignored) and §7/N4 (an embeds link — matched case/separator-
# insensitively — is always dimension structural; a content entry's position
# actually carries a contribution).
@pytest.mark.parametrize("path", _load("is-ought"), ids=lambda p: p.stem)
def test_is_ought(path):
    v = _case(path)
    kind = v["input"]["kind"]
    if kind == "embeds_link":
        got = contract.embeds_link_violations(v["input"]["link"]) == []
        # link_violations() applies the N4 embeds rule itself whenever it
        # RECOGNISES the relation as embeds (which every embeds_link vector's
        # relation is, by construction) — so the general validator must agree
        # with the embeds-specific one here, not just be consistent with it
        # by coincidence.
        general = contract.link_violations(v["input"]["link"]) == []
        assert general == got, (v["case"], "link_violations", general, "embeds_link_violations", got)
    elif kind == "link":
        got = contract.link_violations(v["input"]["link"]) == []
    elif kind == "content_entry":
        # Calls the implementation (position.basis), not a value baked into the
        # vector: a content entry "carries a dimension" iff its computed
        # position actually got a contribution (basis "planes"), not the
        # all-zero default.
        got = position.basis(v["input"]["contributions"]) == "planes"
    else:
        raise AssertionError(f"unknown is-ought vector kind: {kind}")
    assert got == v["expected"]["valid"], v["case"]


# ── assertoric-lowering ────────────────────────────────────────────────────────
@pytest.mark.parametrize("path", _load("assertoric-lowering"), ids=lambda p: p.stem)
def test_assertoric_lowering(path):
    v = _case(path)
    got = assertoric.lower_assertion(v["input"]["sentence"])
    if got is not None and isinstance(got.get("canonical"), tuple):
        # JSON has no tuple type — a vector's own "canonical" is necessarily
        # a 2-element LIST on disk; normalise lower_assertion()'s tuple the
        # same way before comparing (no other field needs this).
        got = {**got, "canonical": list(got["canonical"])}
    assert got == v["expected"], v["case"]


# ── point (§11) ──────────────────────────────────────────────────────────
@pytest.mark.parametrize("path", _load("point"), ids=lambda p: p.stem)
def test_point(path):
    v = _case(path)
    inp = v["input"]
    if inp["kind"] == "derive":
        saturation = inp.get("saturation", point.DEFAULT_POINT_SATURATION)
        if "error" in v["expected"]:
            with pytest.raises(ValueError):
                point.point_from_contributions(inp["contributions"], saturation)
        else:
            assert point.point_from_contributions(inp["contributions"], saturation) == v["expected"], v["case"]
    elif inp["kind"] == "cosine":
        assert point.cosine(inp["a"], inp["b"]) == v["expected"]["cosine"], v["case"]
    elif inp["kind"] == "validate":
        assert point.is_valid_point(inp["doc"]) == v["expected"]["valid"], v["case"]
    else:
        raise AssertionError(f"unrecognised point vector kind: {inp}")


def test_point_distinctness_is_not_lost_to_saturation():
    """D-a: the earlier max-normalised point
    formula could let two DIFFERENT raw counts collapse to the SAME point
    value (whichever dimension held the max always saturated to 1.0,
    hiding any further increase). §11's current formula still clamps the
    per-dimension OUTPUT to [0, 1] (a point itself must stay in range), but
    below that ceiling two different raw counts on the same dimension MUST
    still produce two different values — checked directly here, well below
    any saturation ceiling.
    """
    import five_d_nd.position as _position
    low = point.point_from_contributions({d: 0 for d in _position.DIMENSIONS} | {"structural": 1})
    high = point.point_from_contributions({d: 0 for d in _position.DIMENSIONS} | {"structural": 3})
    assert low != high


# ── fixedpoint (§12) ─────────────────────────────────────────────────────
@pytest.mark.parametrize("path", _load("fixedpoint"), ids=lambda p: p.stem)
def test_fixedpoint(path):
    v = _case(path)
    inp, exp = v["input"], v["expected"]
    op = inp["op"]
    if op == "to_fixed":
        assert fixedpoint.to_fixed(inp["x"]) == exp["result"], v["case"]
    elif op == "fixed_sum":
        assert fixedpoint.fixed_sum(inp["values"]) == exp["result"], v["case"]
    elif op == "fixed_mean":
        if "error" in exp:
            with pytest.raises(ValueError):
                fixedpoint.fixed_mean(inp["total"], inp["n"])
        else:
            assert fixedpoint.fixed_mean(inp["total"], inp["n"]) == exp["result"], v["case"]
    elif op == "tiebreak_order":
        ordered = sorted(
            inp["claim_ids"],
            key=lambda i: fixedpoint.canonical_tiebreak_key(i, inp["salt"]))
        assert ordered == exp["ordered"], v["case"]
    else:
        raise AssertionError(f"unrecognised fixedpoint op: {op}")


# ── triple (§11) ─────────────────────────────────────────────────────────
@pytest.mark.parametrize("path", _load("triple"), ids=lambda p: p.stem)
def test_triple(path):
    v = _case(path)
    got = triple.is_valid_triple(v["input"]["doc"])
    assert got == v["expected"]["valid"], v["case"]


# ── statement (§21, typed-triple layer) ──────────────────────────────────
@pytest.mark.parametrize("path", _load("statement"), ids=lambda p: p.stem)
def test_statement(path):
    v = _case(path)
    got = statement.is_valid_statement(v["input"]["doc"])
    assert got == v["expected"]["valid"], v["case"]


@pytest.mark.parametrize(
    "path", [p for p in _load("statement") if p.stem.startswith("invalid-")], ids=lambda p: p.stem
)
def test_every_invalid_statement_vector_has_exactly_one_violation(path):
    """Each invalid vector names ONE malformed field; it must produce
    EXACTLY one violation. A vector that, through a masking regression
    (e.g. a second required field also missing), produces two or more
    violations no longer tests the field it is named for — removing the
    check for THAT field would leave the vector invalid for an unrelated
    reason and the mutant would survive undetected."""
    v = _case(path)
    violations = statement.statement_violations(v["input"]["doc"])
    assert len(violations) == 1, (v["case"], violations)


# ── path (§22, typed-triple round T1) ────────────────────────────────────
@pytest.mark.parametrize("path", _load("path"), ids=lambda p: p.stem)
def test_typed_path_fold(path):
    v = _case(path)
    edges = v["input"]["edges"]
    got = typed_path.fold_statements(edges)
    assert got["dimension"] == v["expected"]["dimension"], v["case"]
    assert got["weight"] == pytest.approx(v["expected"]["weight"], abs=1e-9), v["case"]


def test_typed_path_includes_both_nonassociative_triples():
    cases = _load("path")
    stems = {p.stem for p in cases}
    assert any("nonassoc-causal-intentional-structural" in s for s in stems)
    assert any("nonassoc-causal-temporal-structural" in s for s in stems)


def test_typed_path_product_graph_state_count_is_five_times_v():
    assert typed_path.product_graph_state_count(0) == 0
    assert typed_path.product_graph_state_count(7) == 35


def test_typed_path_confidence_floor_cut_is_a_stage2_noop_by_default():
    assert typed_path.confidence_floor_cut(0.01, None) is False
    assert typed_path.confidence_floor_cut(0.01, 0.5) is True
    assert typed_path.confidence_floor_cut(0.9, 0.5) is False


def test_typed_path_search_over_a_small_adjacency():
    adjacency = {
        "a": [{"target": "b", "dimension": "causal", "weight": 0.9}],
        "b": [{"target": "c", "dimension": "intentional", "weight": 0.8}],
    }
    reached = typed_path.typed_path_search(adjacency, "a")
    assert ("a", "relational") in reached
    assert ("b", "causal") in reached
    # left-fold: compose(causal, intentional) == intentional (§3 table)
    assert ("c", "intentional") in reached
    assert reached[("c", "intentional")]["weight"] == pytest.approx(0.9 * 0.8)
    assert reached[("c", "intentional")]["hops"] == 2


def test_typed_path_search_respects_the_confidence_floor_hook():
    adjacency = {
        "a": [{"target": "b", "dimension": "causal", "weight": 0.3}],
    }
    reached = typed_path.typed_path_search(adjacency, "a", floor=0.5)
    assert ("b", "causal") not in reached


# ── composition-laws (§22) ───────────────────────────────────────────────
@pytest.mark.parametrize("path", _load("composition-laws"), ids=lambda p: p.stem)
def test_composition_laws(path):
    v = _case(path)
    got = typed_path.composition_law_report()
    assert got == v["expected"], v["case"]


def test_composition_law_report_matches_spec_prose_exactly():
    report = typed_path.composition_law_report()
    assert report["identity_two_sided"] is True
    assert report["all_idempotent"] is True
    assert report["associative_failure_count"] == 2
    assert report["commutative_failure_count"] == 10


# ── worked-example-typed (§21) ───────────────────────────────────────────
@pytest.mark.parametrize("path", _load("worked-example-typed"), ids=lambda p: p.stem)
def test_worked_example_typed(path):
    """Every raw count and the tensor are DERIVED here from
    ``inp["statements"]`` via ``statement.raw_contributions()``/
    ``layer_tensor()`` — nothing is read as a hand-typed field from the
    vector's own ``input``. The vector's ``expected`` is the only place
    these numbers are written down, and only as the target this test
    checks the DERIVED values against.
    """
    v = _case(path)
    inp = v["input"]
    exp = v["expected"]

    for s in inp["statements"]:
        assert statement.is_valid_statement(s), (v["case"], s.get("id"))

    raw_a = statement.raw_contributions(inp["statements"], inp["entry_A_id"])
    assert raw_a == exp["entry_A_raw"], v["case"]
    point_a = point.point_from_contributions(raw_a)
    assert point_a == exp["entry_A_point"], v["case"]
    fp_a = position.fingerprint(raw_a)
    assert fp_a["dominant"] == exp["entry_A_fingerprint_dominant"], v["case"]

    raw_b = statement.raw_contributions(inp["statements"], inp["entry_B_id"])
    assert raw_b == exp["entry_B_raw"], v["case"]
    point_b = point.point_from_contributions(raw_b)
    assert point_b == exp["entry_B_point"], v["case"]
    fp_b = position.fingerprint(raw_b)
    assert fp_b["dominant"] == exp["entry_B_fingerprint_dominant"], v["case"]

    pos = container.container_position([point_a, point_b])
    assert pos == exp["container_position"], v["case"]

    dag = container.add_nesting_edge({}, *inp["nesting_dag_edge"])
    graph = {"concept_links": {}, "anchor_links": {}}
    d = depth.conceptual_depth(graph, dag, inp["nesting_dag_edge"][1], r=inp["depth_radius_r"])
    assert d == exp["depth_d"], v["case"]

    tensor_c = statement.layer_tensor(inp["statements"], inp["entry_C_id"])
    assert tensor_c == exp["entry_C_tensor"], v["case"]

    # No deontic predicate anywhere in this example: the closed §21 enum
    # has no O/P/F predicate to begin with, so this is really just
    # re-confirming every predicate used is a member of the closed,
    # non-deontic enum.
    for s in inp["statements"]:
        assert statement.is_known_predicate(s["predicate"]), (v["case"], s["id"])


# ── path-search (§22) ───────────────────────────────────────────────────
@pytest.mark.parametrize("path", _load("path-search"), ids=lambda p: p.stem)
def test_path_search_vectors(path):
    v = _case(path)
    inp = v["input"]
    reached = typed_path.typed_path_search(inp["adjacency"], inp["start"], floor=inp["floor"])
    got = sorted(
        [list(state) + [val["weight"], val["hops"]] for state, val in reached.items()],
        key=lambda r: (r[0], r[1]),
    )
    assert got == v["expected"]["reached"], v["case"]


# ── actor-role (§21) ────────────────────────────────────────────────────
@pytest.mark.parametrize("path", _load("actor-role"), ids=lambda p: p.stem)
def test_actor_role(path):
    v = _case(path)
    got = statement.is_known_actor(v["input"]["value"])
    assert got == v["expected"]["known"], v["case"]


def test_actor_role_other_escape_regex_rejects_nested_parens():
    assert statement.ACTOR_OTHER_RE.match("other(a(b))") is None


def test_actor_role_vectors_cover_every_closed_role():
    stems = {p.stem for p in _load("actor-role")}
    for role in statement.ACTOR_ROLES:
        assert f"valid-role-{role}" in stems, f"missing an actor-role vector for {role!r}"


# ── institutional-actor (§21) ─────────────────────────────────────────────
@pytest.mark.parametrize("path", _load("institutional-actor"), ids=lambda p: p.stem)
def test_institutional_actor_role(path):
    v = _case(path)
    got = v["input"]["role"] in statement.INSTITUTIONAL_ACTOR_ROLES
    assert got == v["expected"]["institutional"], v["case"]


def test_institutional_actor_roles_matches_the_adr_and_codebook_literal_list():
    """Parity test: the SET below is transcribed literally from ADR 0008
    and the codebook's own competence_of table — NOT derived from
    statement.py itself. Dropping (or adding) a member of
    INSTITUTIONAL_ACTOR_ROLES without updating ADR 0008/the codebook in
    lockstep fails here."""
    adr_and_codebook_literal = frozenset({
        "supervisory_authority", "notified_body", "market_surveillance_authority",
        "commission", "member_state", "european_data_protection_board", "ai_office",
        "competent_authority", "digital_services_coordinator", "csirt",
    })
    assert statement.INSTITUTIONAL_ACTOR_ROLES == adr_and_codebook_literal
    assert len(statement.INSTITUTIONAL_ACTOR_ROLES) == 10


def test_institutional_actor_role_vectors_cover_every_member_and_three_non_members():
    stems = {p.stem for p in _load("institutional-actor")}
    for role in statement.INSTITUTIONAL_ACTOR_ROLES:
        assert f"member-{role}" in stems, f"missing an institutional-actor vector for {role!r}"
    for role in ("controller", "provider", "data_subject"):
        assert f"non-member-{role}" in stems


# ── dual-split (§21) ────────────────────────────────────────────────────
@pytest.mark.parametrize("path", _load("dual-split"), ids=lambda p: p.stem)
def test_dual_split(path):
    v = _case(path)
    got = statement.is_valid_dual_split(v["input"]["causal"], v["input"]["intentional"])
    assert got == v["expected"]["valid"], v["case"]


# ── vocabulary JSON-vs-code parity ──────────────────────────────────────
def test_statement_predicate_vocabulary_json_matches_code():
    doc = json.loads((ROOT / "vocabulary" / "statement-predicates.json").read_text(encoding="utf-8"))
    assert doc["version"] == statement.PREDICATE_VOCABULARY_VERSION
    json_mapping = {name: entry["dimension"] for name, entry in doc["predicates"].items()}
    assert json_mapping == statement.PREDICATE_DIMENSION


def test_typed_statement_codebook_docs_pin_v3_5_content():
    """Pins the v3.5 codebook round's own content in both documents: the version
    header, the four new rule labels (R-p through R-s), and the "neither ... nor"
    negator addition — so a later edit that silently reverts the round is caught
    here rather than only in the ADR's own prose."""
    full = (ROOT / "docs" / "codebook" / "typed-statements-v1.md").read_text(encoding="utf-8")
    coder = (ROOT / "docs" / "codebook" / "typed-statements-v1-coder-view.md").read_text(encoding="utf-8")
    for doc in (full, coder):
        assert "v3.5" in doc
        for rule in ("R-p", "R-q", "R-r", "R-s"):
            assert rule in doc, f"{rule} missing"
        assert "neither ... nor" in doc
        assert "disjunctive" in doc.lower()


def test_actor_role_vocabulary_json_matches_code():
    doc = json.loads((ROOT / "vocabulary" / "actor-roles.json").read_text(encoding="utf-8"))
    assert doc["version"] == statement.ACTOR_VOCABULARY_VERSION
    assert set(doc["roles"]) == statement.ACTOR_ROLES
    assert doc["escape"]["pattern"] == statement.ACTOR_OTHER_RE.pattern


# ── sort order, statement_id, raw_contributions/layer_tensor ───────────
def test_canonical_sort_order_is_dimension_subj_pred_obj_span():
    a = {"dimension": "relational", "subj": "b", "predicate": "predication", "obj": "c",
         "provenance": {"start": 0, "end": 1}}
    b = {"dimension": "causal", "subj": "a", "predicate": "requires", "obj": "z",
         "provenance": {"start": 5, "end": 9}}
    c = {"dimension": "causal", "subj": "a", "predicate": "requires", "obj": "a",
         "provenance": {"start": 1, "end": 2}}
    ordered = statement.sort_statements([a, b, c])
    assert ordered == [c, b, a]
    # reversing sort_statements' own result must NOT equal a fresh sort.
    assert list(reversed(ordered)) != statement.sort_statements([a, b, c])


def test_canonical_sort_key_uses_span_when_everything_else_ties():
    """dimension/subj/predicate/obj are IDENTICAL on both statements below
    — only their provenance span differs. Dropping span from the sort key
    would make these two statements compare EQUAL (and sort unstably);
    this test fails if span is removed from the key."""
    early = {"dimension": "causal", "subj": "a", "predicate": "requires", "obj": "b",
             "provenance": {"start": 0, "end": 5}}
    late = {"dimension": "causal", "subj": "a", "predicate": "requires", "obj": "b",
            "provenance": {"start": 10, "end": 20}}
    assert statement.sort_statements([late, early]) == [early, late]
    assert statement.canonical_sort_key(early) < statement.canonical_sort_key(late)


def test_statement_id_shape_and_join_character():
    h = "deadbeefdeadbeef"  # 16 lowercase hex digits
    sid = statement.statement_id("urn:x", "2016-05-04", h)
    assert sid == f"urn:x#2016-05-04#{h}"
    assert statement.ID_SHAPE_RE.match(sid)
    # a different join character must NOT satisfy the pinned 3-part shape
    assert not statement.ID_SHAPE_RE.match(f"urn:x|2016-05-04|{h}")
    with pytest.raises(ValueError):
        statement.statement_id("", "2016-05-04", h)
    with pytest.raises(ValueError):
        statement.statement_id("urn:x#y", "2016-05-04", h)
    with pytest.raises(ValueError):
        statement.statement_id("urn:x", "2016-05-04", "not-hex")
    with pytest.raises(ValueError):
        statement.statement_id("urn:x", "2016-05-04", "abcd")  # too short


def test_text_hash_is_sha256_truncated_to_16_lowercase_hex():
    import hashlib
    normalized = "a machine-based system"
    h = statement.text_hash(normalized)
    assert h == hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]
    assert len(h) == statement.ID_HASH_HEX_LENGTH == 16
    assert h == h.lower()
    assert statement.ID_SHAPE_RE.match(f"urn:x#2016-05-04#{h}")


def test_normalize_statement_text_nfc_nbsp_whitespace():
    raw = "a  machine-based\n\nsystem  "
    assert statement.normalize_statement_text(raw) == "a machine-based system"


def test_normalize_statement_text_nfc_composes_a_decomposed_sequence():
    """"cafe" + a combining acute accent (NFD-shaped: e, U+0301) MUST
    compose to the single precomposed "é" (U+00E9) under NFC. Dropping the
    NFC step entirely leaves the decomposed sequence untouched — a
    DIFFERENT string, catching that specific mutant."""
    decomposed = "café"
    assert statement.normalize_statement_text(decomposed) == "café"
    assert decomposed != "café"  # the two byte-for-byte forms really do differ


def test_normalize_statement_text_nfc_not_nfkc():
    """The "fi" ligature (U+FB01) is UNCHANGED under NFC but decomposed to
    plain "f"+"i" under NFKC (a compatibility decomposition) — this
    distinguishes NFC from NFKC directly; swapping one for the other
    flips the result."""
    assert statement.normalize_statement_text("ﬁle") == "ﬁle"


def test_normalize_statement_text_preserves_case():
    assert statement.normalize_statement_text("Controller SHALL") == "Controller SHALL"


def test_normalize_statement_text_nbsp_replaced_independently_of_collapse():
    """The whitespace-collapse step is ASCII-only (never Python's
    Unicode-aware \\s, which would already treat NBSP as whitespace and
    mask this check): a lone NBSP between two non-space characters, with
    NO adjacent ASCII whitespace, is replaced ONLY by the explicit NBSP
    step. Dropping that step leaves the NBSP character in the output."""
    assert statement.normalize_statement_text("a b") == "a b"


def test_normalize_statement_text_whitespace_collapse_is_ascii_only():
    """Proves the collapse class is ASCII-only, not Python's broader
    Unicode \\s: U+2003 (EM SPACE) and U+2028 (LINE SEPARATOR) are both
    Unicode whitespace that Python's \\s WOULD match, but neither is in
    [ \\t\\n\\r\\f\\v] -- both must survive untouched (NFC does not
    normalise them away, and neither is U+00A0, so the NBSP step does not
    touch them either)."""
    raw = "a b c"
    assert statement.normalize_statement_text(raw) == raw


def test_statement_rejects_nan_and_infinite_weight_and_confidence():
    """NaN/inf are JSON numbers by type but never valid here — not
    expressible as a standard-JSON vector (Python's own json module
    accepts NaN/Infinity as a non-standard extension; a plain unit test
    avoids relying on that extension in a committed vector file)."""
    base = {
        "id": "u#d#0123456789abcdef", "subj": "a", "obj": "b", "predicate": "enables",
        "dimension": "causal", "layer": "domain", "edge_confidence": 0.5,
        "provenance": {"start": 0, "end": 1}, "negation": "absent",
    }
    for bad in (float("nan"), float("inf"), float("-inf")):
        assert not statement.is_valid_statement({**base, "weight": bad})
        assert not statement.is_valid_statement({**base, "edge_confidence": bad})


def test_fold_statements_validates_weight():
    good = {"dimension": "causal", "weight": 0.5}
    bad_bool = {"dimension": "causal", "weight": True}
    bad_range = {"dimension": "causal", "weight": 1.5}
    bad_nan = {"dimension": "causal", "weight": float("nan")}
    assert typed_path.fold_statements([good])["weight"] == 0.5
    for bad in (bad_bool, bad_range, bad_nan):
        with pytest.raises(ValueError):
            typed_path.fold_statements([bad])


def test_raw_contributions_and_layer_tensor_derive_from_statements():
    stmts = [
        {"id": "u#d#0123456789abcdef", "subj": "x", "obj": "y", "predicate": "requires",
         "dimension": "causal", "layer": "domain", "weight": 1.0, "edge_confidence": 0.9,
         "provenance": {"start": 0, "end": 5}, "negation": "absent"},
        {"id": "u#d#fedcba9876543210", "subj": "y", "obj": "z", "predicate": "is_a",
         "dimension": "structural", "layer": "deep", "weight": 1.0, "edge_confidence": 0.9,
         "provenance": {"start": 6, "end": 10}, "negation": "absent"},
    ]
    raw = statement.raw_contributions(stmts, "y")
    assert raw == {"structural": 1, "causal": 1, "intentional": 0, "temporal": 0, "relational": 0}
    tensor = statement.layer_tensor(stmts, "y")
    assert tensor["domain"]["causal"] == pytest.approx(0.2)
    assert tensor["deep"]["structural"] == pytest.approx(0.2)
    assert tensor["surface"] == {d: 0.0 for d in position.DIMENSIONS}
    # a malformed statement in the list must be SKIPPED, never counted
    malformed = dict(stmts[0])
    del malformed["edge_confidence"]
    raw_with_malformed = statement.raw_contributions([malformed, stmts[1]], "y")
    assert raw_with_malformed == {"structural": 1, "causal": 0, "intentional": 0, "temporal": 0, "relational": 0}


# ── container-average (§14) ──────────────────────────────────────────────
@pytest.mark.parametrize("path", _load("container-average"), ids=lambda p: p.stem)
def test_container_average(path):
    v = _case(path)
    if "error" in v["expected"]:
        with pytest.raises(ValueError):
            container.container_position(v["input"]["member_points"])
    else:
        got = container.container_position(v["input"]["member_points"])
        assert got == v["expected"]["position"], v["case"]


# ── trimmed-topk (§14) ───────────────────────────────────────────────────
@pytest.mark.parametrize("path", _load("trimmed-topk"), ids=lambda p: p.stem)
def test_trimmed_topk(path):
    v = _case(path)
    inp = v["input"]
    if "error" in v["expected"]:
        with pytest.raises(ValueError):
            container.trimmed_top_k_match(
                inp["members"], k=inp["k"], n_min=inp["n_min"], salt=inp["salt"])
    else:
        got = container.trimmed_top_k_match(
            inp["members"], k=inp["k"], n_min=inp["n_min"], salt=inp["salt"])
        assert got == v["expected"], v["case"]


# ── depth (§15) ──────────────────────────────────────────────────────────
def _as_dag(raw):
    return {"children": {k: set(v) for k, v in raw.get("children", {}).items()},
            "order": dict(raw.get("order", {}))}


@pytest.mark.parametrize("path", _load("depth"), ids=lambda p: p.stem)
def test_depth(path):
    v = _case(path)
    inp = v["input"]
    kind = inp.get("kind")
    if kind == "distinct-pair-check":
        assert (inp["d_low"] != inp["d_high"]) == v["expected"]["differ"], v["case"]
        return
    if kind == "quantiles":
        if "error" in v["expected"]:
            with pytest.raises(ValueError):
                depth.depth_quantiles(inp["member_depths"])
        else:
            assert depth.depth_quantiles(inp["member_depths"]) == v["expected"]["quantiles"], v["case"]
        return
    # the graph-based conceptual_depth() vectors
    graph = inp["graph"]
    dag = _as_dag(inp["dag"])
    kwargs = {k: val for k, val in inp.items() if k not in ("graph", "dag", "entry_id")}
    if "error" in v["expected"]:
        with pytest.raises(ValueError):
            depth.conceptual_depth(graph, dag, inp["entry_id"], **kwargs)
    else:
        got = depth.conceptual_depth(graph, dag, inp["entry_id"], **kwargs)
        assert got == v["expected"]["d"], v["case"]


def test_depth_locality_edit_outside_radius_leaves_d_unchanged():
    """r must be OPERATIVE — an edit to the
    graph strictly OUTSIDE the radius-r neighbourhood of the entry must
    leave d unchanged; an edit INSIDE it must change d. Cross-checks the
    two dedicated vectors directly against each other (not merely each
    against its own stored expectation) so a future change that breaks
    locality fails here even if the stored expectations were edited to
    match a regression.
    """
    chain = {"concept_links": {"X": ["A"], "A": ["B"], "B": ["C"]}, "anchor_links": {}}
    chain_extended = {"concept_links": {"X": ["A"], "A": ["B"], "B": ["C"], "C": ["D"]},
                       "anchor_links": {}}
    dag0 = container.empty_dag()
    # Extending the graph at D (4 hops from X) must not change d at r=1,
    # since D sits strictly outside X's radius-1 neighbourhood.
    assert depth.conceptual_depth(chain, dag0, "X", r=1) == \
        depth.conceptual_depth(chain_extended, dag0, "X", r=1)
    # The SAME extension, now INSIDE a radius wide enough to reach it,
    # must actually matter for the count (hop 4 is still outside r=2 here;
    # confirm the signal itself grows strictly with r on this fixture).
    assert depth.concept_link_signal(chain_extended, "X", 2) == \
        depth.concept_link_signal(chain, "X", 2)
    assert depth.concept_link_signal(chain_extended, "X", 4) > \
        depth.concept_link_signal(chain_extended, "X", 2)


def test_depth_property_ii_equal_tuples_give_equal_d():
    """Property (ii): equal radius-r
    signal tuples give equal d (trivial for a deterministic function, but
    checked directly: two structurally IDENTICAL graphs, built separately,
    must produce bit-identical d).
    """
    g = {"concept_links": {"X": ["p0", "p1"]}, "anchor_links": {"X": ["a0"]}}
    g2 = {"concept_links": {"X": ["p0", "p1"]}, "anchor_links": {"X": ["a0"]}}
    dag = container.empty_dag()
    dag = container.add_nesting_edge(dag, "root", "X")
    dag2 = container.empty_dag()
    dag2 = container.add_nesting_edge(dag2, "root", "X")
    assert depth.conceptual_depth(g, dag, "X") == depth.conceptual_depth(g2, dag2, "X")


def test_depth_property_iv_no_injectivity_guarantee_counterexamples():
    """Property (iv), a STATED
    limitation, not a defect: two genuinely DIFFERENT signal tuples MAY
    produce the SAME d. Cross-checks the two design counterexamples directly
    (not merely each against its own stored vector): (a) anchor counts 1
    vs 3 at zero incoming links give equal d (the deep_pull factor is zero
    either way, so the surface_pull difference is multiplied away); (b) a
    short containment chain r->x->l and a longer one r->q->x->l->m give the
    entry x the SAME ancestors-within-r/descendants-within-r ratio at r=1
    despite very different overall shapes.
    """
    dag0 = container.empty_dag()
    g_a1 = {"concept_links": {}, "anchor_links": {"X": ["a0"]}}
    g_a3 = {"concept_links": {}, "anchor_links": {"X": ["a0", "a1", "a2"]}}
    assert depth.conceptual_depth(g_a1, dag0, "X", r=2) == depth.conceptual_depth(g_a3, dag0, "X", r=2)

    empty_graph = {"concept_links": {}, "anchor_links": {}}
    dag_short = container.empty_dag()
    dag_short = container.add_nesting_edge(dag_short, "r", "x")
    dag_short = container.add_nesting_edge(dag_short, "x", "l")
    dag_long = container.empty_dag()
    dag_long = container.add_nesting_edge(dag_long, "r", "q")
    dag_long = container.add_nesting_edge(dag_long, "q", "x")
    dag_long = container.add_nesting_edge(dag_long, "x", "l")
    dag_long = container.add_nesting_edge(dag_long, "l", "m")
    kwargs = {"r": 1, "w_links": 1e-9, "w_nesting": 1.0}
    assert depth.conceptual_depth(empty_graph, dag_short, "x", **kwargs) == \
        depth.conceptual_depth(empty_graph, dag_long, "x", **kwargs)


# ── staleness (§16) ──────────────────────────────────────────────────────
@pytest.mark.parametrize("path", _load("staleness"), ids=lambda p: p.stem)
def test_staleness(path):
    v = _case(path)
    inp, exp = v["input"], v["expected"]
    kind = inp["kind"]
    if kind == "propagate":
        got = views.propagate_staleness(inp["reverse_embeds"], inp["changed"])
        assert got == exp["stale_order"], v["case"]
        assert len(got) == len(set(got)), (v["case"], "duplicate in propagation order")
    elif kind == "erasure_fence":
        assert views.is_erasure_fenced(inp["view"]) == exp["fenced"], v["case"]
    elif kind == "erasure_bit_identity":
        r = {"value": inp["rederived_value"]}
        b = {"value": inp["baseline_value"]}
        assert views.erasure_bit_identical(r, b) == exp["bit_identical"], v["case"]
    elif kind == "ingest_window":
        got = views.ingest_stale_window(
            {"as_of": inp["as_of"], "value": 1}, now=inp["now"], window_seconds=inp["window_seconds"])
        assert got["servable"] == exp["servable"], v["case"]
        assert got["age"] == exp["age"], v["case"]
    elif kind == "ingest_window_malformed":
        with pytest.raises(ValueError):
            views.ingest_stale_window(inp["view"], now=inp["now"], window_seconds=inp["window_seconds"])
    elif kind == "debounce":
        got = sorted(views.debounce(
            [tuple(e) for e in inp["events"]],
            window_seconds=inp["window_seconds"], threshold=inp["threshold"]))
        assert [list(x) for x in got] == exp["coalesced"], v["case"]
    elif kind == "make_view":
        got = views.make_view(
            0.5, kind=inp["view_kind"], contributing_claim_ids=["c1"], embeds_edges=[],
            profile_digest="d", basis="planes", stale=inp["stale"], staleness_tier=inp["staleness_tier"])
        assert got["kind"] == exp["kind"], v["case"]
        assert got["staleness_tier"] == exp["staleness_tier"], v["case"]
    elif kind == "validate_view":
        assert views.is_valid_view(inp["doc"]) == exp["valid"], v["case"]
    else:
        raise AssertionError(f"unrecognised staleness vector kind: {kind}")


def test_position_digest_is_order_invariant_over_claim_ids_and_embeds_edges():
    """Mutation-testing gap (fix round item 3): a ``position_digest`` MUST
    be the SAME regardless of the ORDER ``contributing_claim_ids``/
    ``embeds_edges`` are supplied in — the function sorts them internally
    specifically so the digest reflects the SET, not an incidental
    iteration order. Directly exercises both input lists reversed.
    """
    a = views.position_digest(["c1", "c2", "c3"], ["e1", "e2"], "profile-digest")
    b = views.position_digest(["c3", "c1", "c2"], ["e2", "e1"], "profile-digest")
    assert a == b
    c = views.position_digest(["c1", "c2"], ["e1", "e2"], "profile-digest")
    assert a != c  # a genuinely different claim-id set must still differ


def test_member_set_digest_depends_on_version_not_only_membership():
    """Mutation-testing gap (fix round item 3): the SAME member set at two
    DIFFERENT version numbers MUST digest differently — version is part of
    the digest input, not merely bookkeeping alongside it.
    """
    d1 = container.member_set_digest(["a", "b", "c"], 1)
    d2 = container.member_set_digest(["a", "b", "c"], 2)
    assert d1 != d2
    # order of the member ids themselves must NOT matter (sorted internally)
    d3 = container.member_set_digest(["c", "b", "a"], 1)
    assert d1 == d3


def test_staleness_propagation_is_a_true_topological_order():
    """propagate_staleness() must return an ORDERED
    list in a TRUE topological order (every node strictly after ALL of its
    own affected children), not merely a dedup-ed unordered set. Directly
    asserts the order on the diamond fixture (A changed; B, C its direct
    parents; D the common grandparent) — D must come after BOTH B and C.
    """
    order = views.propagate_staleness({"A": ["B", "C"], "B": ["D"], "C": ["D"], "D": []}, ["A"])
    assert order == ["A", "B", "C", "D"]
    assert order.index("D") > order.index("B")
    assert order.index("D") > order.index("C")


def test_staleness_enum_vectors_cover_both_tiers():
    """Fix round item 3: compare against a LITERAL expected set (not merely
    the live ``views.STALENESS_TIERS`` value), so a mutant that silently
    REMOVES a tier from the live enum AND from this test's own comparison
    target at the same time cannot slip through — the literal frozenset
    below is this test's own independent ground truth. Also requires at
    least one vector that calls ``make_view`` for EACH tier (fix round item
    3), not merely one that happens to carry the tier string somewhere.
    """
    EXPECTED_TIERS = frozenset({"erasure", "ingest"})
    assert set(views.STALENESS_TIERS) == EXPECTED_TIERS, (
        "views.STALENESS_TIERS no longer matches the literal expected set "
        f"{EXPECTED_TIERS!r} — got {set(views.STALENESS_TIERS)!r}")
    seen_fence_or_window = set()
    seen_make_view = set()
    for path in _load("staleness"):
        v = _case(path)
        inp = v["input"]
        tier = inp.get("view", {}).get("staleness_tier") if isinstance(inp.get("view"), dict) else None
        if tier:
            seen_fence_or_window.add(tier)
        if inp.get("kind") == "make_view" and inp.get("stale"):
            seen_make_view.add(inp.get("staleness_tier"))
    missing_fence = EXPECTED_TIERS - seen_fence_or_window
    assert not missing_fence, f"no staleness vector exercises tier(s) {missing_fence!r} via a view"
    missing_make_view = EXPECTED_TIERS - seen_make_view
    assert not missing_make_view, (
        f"no staleness vector calls make_view() for tier(s) {missing_make_view!r}")


# ── cycle-rejection (§13) ────────────────────────────────────────────────
def _assert_dag_order_invariants(dag, case):
    """After EVERY successful write, the order must
    stay INJECTIVE (no two nodes share an order value — a real defect,
    ``prev-order-stuck``, lets two different brand-new parents collide on
    the same value), and the two counters must stay strictly outside the
    range of every assigned value: ``prev_order < min(order)`` and
    ``next_order > max(order)``.
    """
    values = list(dag["order"].values())
    assert len(values) == len(set(values)), (case, "order is not injective", dag["order"])
    if values:
        assert dag["prev_order"] < min(values), (case, "prev_order not below every order value", dag)
        assert dag["next_order"] > max(values), (case, "next_order not above every order value", dag)


@pytest.mark.parametrize("path", _load("cycle-rejection"), ids=lambda p: p.stem)
def test_cycle_rejection(path):
    v = _case(path)
    inp, exp = v["input"], v["expected"]
    dag = container.empty_dag()
    for parent, child in inp["existing_edges"]:
        dag = container.add_nesting_edge(dag, parent, child)
        _assert_dag_order_invariants(dag, v["case"])
    parent, child = inp["add_edge"]
    if "error" in exp:
        with pytest.raises(container.CycleError):
            container.add_nesting_edge(dag, parent, child)
        _assert_dag_order_invariants(dag, v["case"])
    else:
        dag2 = container.add_nesting_edge(dag, parent, child)
        _assert_dag_order_invariants(dag2, v["case"])
        assert sorted(dag2["children"][parent]) == exp["children_of_parent"], v["case"]
        # the order must stay a genuinely valid topological order: every
        # edge u -> v in the resulting graph must satisfy order[u] < order[v]
        for p2, children in dag2["children"].items():
            for c2 in children:
                assert dag2["order"][p2] < dag2["order"][c2], (
                    v["case"], "post-condition: order is not topologically valid", p2, c2)


def test_cycle_rejection_forces_a_real_reorder():
    """D-b (owner decision) / review finding: the reference MUST be an
    incrementally maintained topological order (Pearce-Kelly class), not a
    full reachability check per write. Directly exercises the forced
    reordering worked example from ``container.py``'s own docstring: two
    separate chains (C->D, A->B) joined by B->C, which is inconsistent
    with the EXISTING order (order[B] > order[C] at the time of insertion)
    and must trigger a real reassignment, not merely a rejection.
    """
    dag = container.empty_dag()
    dag = container.add_nesting_edge(dag, "C", "D")
    dag = container.add_nesting_edge(dag, "A", "B")
    before = dict(dag["order"])
    assert before["B"] > before["C"]  # pre-condition: B->C would be inconsistent with the order as-is
    dag = container.add_nesting_edge(dag, "B", "C")
    after = dag["order"]
    assert after["A"] < after["B"] < after["C"] < after["D"]
    assert after != before, "a forced reorder must actually reassign order values"


def test_add_nesting_edge_new_node_path_does_not_rescan_order_per_call():
    """Replaces a flaky wall-clock guard: a real
    defect was found and fixed while re-measuring a timing
    table -- ``dag["next_order"] if "next_order" in dag else (...)`` reads
    the already-present counter directly; the BROKEN version this
    replaced, ``dag.get("next_order", (max(order.values()) + 1) if order
    else 0)``, looks equivalent but is NOT: a dict's own ``.get()``
    evaluates its SECOND argument EAGERLY on every call, present or not,
    silently reintroducing an O(V) ``max(order.values())``/
    ``min(order.values())`` scan on every single write.

    The EARLIER version of this test measured WALL-CLOCK time and
    compared ratios — flaky by design (23% failures under CPU load in
    practice, and under enough load it could even pass BROKEN code, since
    a loaded machine can make the "fast" run slow enough to shrink the
    ratio below the threshold). This version counts ``max``/``min`` CALLS
    directly and deterministically: monkeypatches ``container.max`` and
    ``container.min`` with counting wrappers (Python resolves a bare
    ``max``/``min`` call inside ``container.py`` through the MODULE's own
    global namespace before falling back to builtins, so assigning
    ``container.max``/``container.min`` shadows the builtin for every call
    made from inside that module, with no change to ``container.py``
    itself), builds a 5,000-node chain on a FRESH ``empty_dag()`` (which
    already carries both counters, so NEITHER ``max`` NOR ``min`` should
    ever be called, not even once), and separately builds a chain
    starting from a COUNTER-LESS record (where exactly one lazy
    initialisation call to each is expected, on the very first write, and
    NONE after).
    """
    import builtins

    orig_max, orig_min = builtins.max, builtins.min
    calls = {"max": 0, "min": 0}

    def counting_max(*args, **kwargs):
        calls["max"] += 1
        return orig_max(*args, **kwargs)

    def counting_min(*args, **kwargs):
        calls["min"] += 1
        return orig_min(*args, **kwargs)

    # Setting these as module-level attributes on `container` itself adds
    # them to the MODULE's own global namespace, which Python's bare
    # `max`/`min` lookups inside container.py's functions resolve BEFORE
    # falling through to builtins -- this shadows the builtin for every
    # call made from inside that module, with no change to container.py
    # itself, and without needing `container` to already define `max`/
    # `min` as its own attributes beforehand.
    container.max = counting_max
    container.min = counting_min
    try:
        # Case A: empty_dag() already carries both counters -- max/min
        # must NEVER be called, not even on the very first write.
        dag = container.empty_dag()
        for i in range(5000):
            container.add_nesting_edge(dag, f"n{i}", f"n{i + 1}")
        assert calls["max"] == 0, f"max() called {calls['max']} times building a chain from empty_dag()"
        assert calls["min"] == 0, f"min() called {calls['min']} times building a chain from empty_dag()"

        # Case B: a COUNTER-LESS record -- exactly one lazy-init call to
        # each counter is expected, on the FIRST write only; zero more
        # across every subsequent write.
        calls["max"] = calls["min"] = 0
        counterless = {"children": {}, "order": {}, "reverse": {}}
        for i in range(5000):
            container.add_nesting_edge(counterless, f"n{i}", f"n{i + 1}")
        assert calls["max"] <= 1, (
            f"max() called {calls['max']} times building a chain from a counter-less "
            "record -- expected at most one lazy-init call, on the first write only")
        assert calls["min"] <= 1, (
            f"min() called {calls['min']} times building a chain from a counter-less "
            "record -- expected at most one lazy-init call, on the first write only")
    finally:
        del container.max
        del container.min


def test_cycle_rejection_cost_fast_path_visits_nothing_and_reorder_stays_bounded():
    """The FAST path (order already
    consistent) must call NEITHER ``_bounded_forward`` NOR
    ``_bounded_backward`` at all — O(1), no traversal. The SLOW path (a
    forced reorder) must visit ONLY nodes whose CURRENT order value lies
    within ``[lb, ub]`` (the two endpoints' own order values at the time of
    the call) — never the whole graph. Wraps both functions to record every
    node visited, restoring the originals afterwards regardless of outcome.
    """
    visited_forward: list = []
    visited_backward: list = []
    orig_forward = container._bounded_forward
    orig_backward = container._bounded_backward

    def spy_forward(children, order, start, ceiling):
        result = orig_forward(children, order, start, ceiling)
        visited_forward.append((ceiling, set(result)))
        return result

    def spy_backward(reverse, order, start, floor):
        result = orig_backward(reverse, order, start, floor)
        visited_backward.append((floor, set(result)))
        return result

    container._bounded_forward = spy_forward
    container._bounded_backward = spy_backward
    try:
        dag = container.empty_dag()
        dag = container.add_nesting_edge(dag, "C", "D")
        dag = container.add_nesting_edge(dag, "A", "B")
        # Fast path: E -> F is a brand-new pair, consistent with any order
        # assignment by construction (both nodes are new) -- must not
        # trigger either bounded traversal at all.
        visited_forward.clear()
        visited_backward.clear()
        dag = container.add_nesting_edge(dag, "E", "F")
        assert visited_forward == [], "fast path must not call _bounded_forward"
        assert visited_backward == [], "fast path must not call _bounded_backward"

        # The OTHER fast path (kills mutant pk-no-fastpath directly) —
        # BOTH endpoints already pre-existing, with order
        # ALREADY consistent (order[A] < order[D], both from the earlier
        # chains) — must ALSO call neither bounded traversal at all. The
        # brand-new-pair case above never exercises the `ub >= lb` branch
        # at all, so it alone cannot catch a mutant that always takes the
        # slow path for this specific, already-consistent-pair case.
        visited_forward.clear()
        visited_backward.clear()
        assert dag["order"]["A"] < dag["order"]["F"]
        dag = container.add_nesting_edge(dag, "A", "F")
        assert visited_forward == [], "already-consistent pre-existing pair must not call _bounded_forward"
        assert visited_backward == [], "already-consistent pre-existing pair must not call _bounded_backward"

        # Slow path: B -> C forces a reorder (order[B] > order[C] already).
        ub_before, lb_before = dag["order"]["B"], dag["order"]["C"]
        visited_forward.clear()
        visited_backward.clear()
        dag = container.add_nesting_edge(dag, "B", "C")
        assert len(visited_forward) == 1 and len(visited_backward) == 1
        ceiling, rf_nodes = visited_forward[0]
        floor, rb_nodes = visited_backward[0]
        assert ceiling == ub_before
        assert floor == lb_before
        # every node the bounded traversals actually visited had an order
        # value within [lb_before, ub_before] AT THE TIME OF THE CALL --
        # i.e. the traversal never escaped the affected region.
        order_before_reorder = {"C": 0, "D": 1, "A": 2, "B": 3}
        for node in rf_nodes:
            assert order_before_reorder[node] <= ub_before, (node, "forward escaped ceiling")
        for node in rb_nodes:
            assert order_before_reorder[node] >= lb_before, (node, "backward escaped floor")
        # the untouched E/F nodes must never be visited by either traversal
        assert "E" not in rf_nodes and "E" not in rb_nodes
        assert "F" not in rf_nodes and "F" not in rb_nodes
    finally:
        container._bounded_forward = orig_forward
        container._bounded_backward = orig_backward


def test_cycle_rejection_reverse_index_is_persisted_not_rebuilt():
    """``reverse_index()`` on a dag that already
    carries a ``"reverse"`` key must be a cheap shallow copy of it, not an
    O(E) recomputation from ``children`` -- directly checked by poisoning
    ``children`` with a value that would produce a WRONG reverse index if
    ``reverse_index()`` ever recomputed from it, then confirming the
    PERSISTED reverse field is what gets returned instead.
    """
    dag = container.empty_dag()
    dag = container.add_nesting_edge(dag, "P", "Q")
    tampered = dict(dag)
    tampered["children"] = {"P": {"BOGUS"}}  # would mislead a from-scratch recompute
    rev = container.reverse_index(tampered)
    assert rev == {k: set(v) for k, v in dag["reverse"].items()}


def test_add_nesting_edge_mutates_in_place_and_returns_the_same_object():
    """add_nesting_edge() mutates the
    caller-owned dag record directly and returns the SAME object (never a
    copy) -- replaces the earlier "dag itself is never mutated" claim,
    which an earlier structural-sharing version still satisfied but
    this in-place version deliberately does not.
    """
    dag = container.empty_dag()
    result = container.add_nesting_edge(dag, "A", "B")
    assert result is dag
    assert dag["children"]["A"] == {"B"}


def test_rejected_write_leaves_the_record_byte_identical_deep_compare():
    """A REJECTED write (a cycle, including a
    brand-new self-loop) must leave the record BYTE-IDENTICAL to a deep
    SNAPSHOT taken immediately before the call -- not merely "logically
    equivalent", a literal deep compare via snapshot_dag(). This is also
    the test designed to kill a mutant that partially applies a write
    (e.g. inserts the new nodes, or reassigns part of the order) BEFORE
    detecting the cycle: any such partial application changes the record
    relative to the pre-call snapshot and fails this assertion.
    """
    # Case A: a real cycle between two pre-existing nodes.
    dag = container.empty_dag()
    container.add_nesting_edge(dag, "P", "Q")
    container.add_nesting_edge(dag, "Q", "R")
    before = container.snapshot_dag(dag)
    with pytest.raises(container.CycleError):
        container.add_nesting_edge(dag, "R", "P")
    assert dag == before, "a rejected real cycle must leave the record unchanged"

    # Case B: a self-loop on a BRAND-NEW node -- the record must not even
    # gain the new node's entry.
    dag2 = container.empty_dag()
    container.add_nesting_edge(dag2, "X", "Y")
    before2 = container.snapshot_dag(dag2)
    with pytest.raises(container.CycleError):
        container.add_nesting_edge(dag2, "NEVER-SEEN", "NEVER-SEEN")
    assert dag2 == before2, "a rejected brand-new self-loop must leave the record unchanged"
    assert "NEVER-SEEN" not in dag2["order"]
    assert "NEVER-SEEN" not in dag2["children"]
    assert "NEVER-SEEN" not in dag2["reverse"]

    # Case C: a rejected write on a bare, NON-CANONICAL
    # {} record must leave it an EMPTY dict -- no "children"/"order"/
    # "reverse"/"next_order"/"prev_order" key gained as a side effect of a
    # setdefault-style read that runs before the rejection.
    empty = {}
    with pytest.raises(container.CycleError):
        container.add_nesting_edge(empty, "x", "x")
    assert empty == {}, f"a rejected write on {{}} must leave it empty, got {empty!r}"

    # Case D: a rejected write on a hand-built,
    # COUNTER-LESS record (no "next_order"/"prev_order" keys at all) must
    # not gain them either.
    counterless = {
        "children": {"p": {"q"}}, "order": {"p": 0, "q": 1},
        "reverse": {"q": {"p"}, "p": set()},
    }
    before_counterless = {k: (dict(v) if isinstance(v, dict) else v) for k, v in counterless.items()}
    before_counterless["children"] = {k: set(v) for k, v in counterless["children"].items()}
    before_counterless["reverse"] = {k: set(v) for k, v in counterless["reverse"].items()}
    with pytest.raises(container.CycleError):
        container.add_nesting_edge(counterless, "q", "p")  # would close p -> q -> p
    assert counterless == before_counterless, (
        "a rejected write on a counter-less record must leave it unchanged "
        "(and MUST NOT gain next_order/prev_order)")
    assert "next_order" not in counterless
    assert "prev_order" not in counterless


def test_snapshot_dag_is_unaffected_by_later_writes():
    """snapshot_dag() returns a version of the record
    that stays unaffected by writes made to the ORIGINAL dag after the
    snapshot was taken -- directly exercised on children/reverse (sets,
    mutated in place by add_nesting_edge) and order (new keys added in
    place), not merely on scalars that would trivially survive a shallow
    copy.
    """
    dag = container.empty_dag()
    container.add_nesting_edge(dag, "A", "B")
    snap = container.snapshot_dag(dag)
    container.add_nesting_edge(dag, "B", "C")
    container.add_nesting_edge(dag, "A", "D")
    assert snap["children"] == {"A": {"B"}, "B": set()}
    assert snap["order"] == {"A": 0, "B": 1}
    assert snap["reverse"] == {"A": set(), "B": {"A"}}
    # the live dag, meanwhile, has moved on
    assert dag["children"]["B"] == {"C"}
    assert dag["children"]["A"] == {"B", "D"}
    assert "C" in dag["order"] and "D" in dag["order"]


def test_add_nesting_edge_on_a_raw_empty_dict_attaches_children_order_reverse():
    """A successful add_nesting_edge({}, "a", "b") on
    a RAW, non-canonical {} record must end with children == {"a": {"b"},
    "b": set()} and the matching reverse/order -- not merely "no crash".
    Kills a mutant that drops the `dag["children"] = children` commit
    line (no-attach-children): without it, the freshly created `children`
    local dict (container.py's own `.get("children", {})` fallback, never
    yet linked to `dag`) would be mutated correctly in memory but never
    actually attached to the `{}` the caller passed in, leaving
    `dag["children"]` absent entirely despite the call succeeding.
    """
    dag = {}
    result = container.add_nesting_edge(dag, "a", "b")
    assert result is dag
    assert dag["children"] == {"a": {"b"}, "b": set()}
    assert dag["reverse"] == {"a": set(), "b": {"a"}}
    assert dag["order"] == {"a": 0, "b": 1}
    assert dag["next_order"] == 2
    assert dag["prev_order"] == -1


def test_new_parent_of_existing_child_is_order_consistent_without_reorder():
    """A BRAND-NEW parent of an ALREADY-EXISTING child
    must get an order value strictly below the child's, in O(1) (via the
    prev_order counter), never requiring a bounded reorder of anything
    else. Exercises the specific combination the two-counter scheme
    (next_order going up, prev_order going down) exists for.
    """
    dag = container.empty_dag()
    container.add_nesting_edge(dag, "child", "grandchild")
    order_before = dict(dag["order"])
    container.add_nesting_edge(dag, "new_parent", "child")
    assert dag["order"]["new_parent"] < dag["order"]["child"] < dag["order"]["grandchild"]
    # the pre-existing nodes' own order values must be untouched -- no
    # reorder was needed for this case.
    assert dag["order"]["child"] == order_before["child"]
    assert dag["order"]["grandchild"] == order_before["grandchild"]


def test_cycle_rejection_cost_bounded_traversal_excludes_out_of_range_nodes():
    """Kills mutants pk-unbounded-forward and
    pk-unbounded-backward: a hand-built dag where the forward/backward
    traversals, if they ignored their own ceiling/floor bound, would visit
    nodes STRICTLY OUTSIDE the affected ``[lb, ub]`` region — ``W`` (a
    descendant of ``D`` with an order value ABOVE ``ub``) and ``Y`` (an
    ancestor of ``B`` with an order value BELOW ``lb``). The conformant
    bounded traversal must visit NEITHER.
    """
    children = {"Y": {"B"}, "A": {"B"}, "C": {"D"}, "D": {"W"}, "B": set(), "W": set()}
    order = {"C": 0, "D": 1, "W": 15, "A": 10, "B": 11, "Y": -5}
    reverse = container.reverse_index({"children": children})
    dag = {"children": children, "order": order, "reverse": reverse, "next_order": 20}

    visited_forward: list = []
    visited_backward: list = []
    orig_forward = container._bounded_forward
    orig_backward = container._bounded_backward

    def spy_forward(children_, order_, start, ceiling):
        result = orig_forward(children_, order_, start, ceiling)
        visited_forward.append(set(result))
        return result

    def spy_backward(reverse_, order_, start, floor):
        result = orig_backward(reverse_, order_, start, floor)
        visited_backward.append(set(result))
        return result

    container._bounded_forward = spy_forward
    container._bounded_backward = spy_backward
    try:
        container.add_nesting_edge(dag, "B", "C")
    finally:
        container._bounded_forward = orig_forward
        container._bounded_backward = orig_backward

    assert visited_forward == [{"C", "D"}], (
        "forward traversal must exclude W (order 15 > ub 11)", visited_forward)
    assert visited_backward == [{"B", "A"}], (
        "backward traversal must exclude Y (order -5 < lb 0)", visited_backward)


# ── resolution-profile (§16) ─────────────────────────────────────────────
@pytest.mark.parametrize("path", _load("resolution-profile"), ids=lambda p: p.stem)
def test_resolution_profile(path):
    v = _case(path)
    if "doc_a" in v["input"]:
        # A PAIR of documents,
        # asserting both validate and digest IDENTICALLY despite one
        # using an int and the other the equal-valued float.
        doc_a, doc_b = v["input"]["doc_a"], v["input"]["doc_b"]
        assert profile.is_valid_profile(doc_a) == v["expected"]["valid_a"], v["case"]
        assert profile.is_valid_profile(doc_b) == v["expected"]["valid_b"], v["case"]
        same = profile.profile_digest(doc_a) == profile.profile_digest(doc_b)
        assert same == v["expected"]["same_digest"], v["case"]
        return
    doc = v["input"]["doc"]
    got_valid = profile.is_valid_profile(doc)
    assert got_valid == v["expected"]["valid"], v["case"]
    if got_valid and "profile_digest" in v["expected"]:
        assert profile.profile_digest(doc) == v["expected"]["profile_digest"], v["case"]


def test_resolution_profile_unknown_field_is_rejected_and_never_changes_the_digest():
    """Fix round item 7 (replaces the earlier ``assert True`` stub): a typo
    field (e.g. ``"K"`` instead of ``"k"``) MUST be a violation — never
    silently ignored, and never silently absorbed into the digest as an
    unresolved extra key. Mirrors the dedicated vectors directly against
    the live code, not only via the generic vector runner above.
    """
    assert not profile.is_valid_profile({"profile_id": "x", "K": 7})
    typo_digest = profile.profile_violations({"profile_id": "default", "K": 999})
    assert typo_digest != []  # rejected outright — profile_digest() must never be called on it


def test_resolution_profile_float_and_int_agree_with_the_schema():
    """Fix round item 7: ``k: 5.0`` (a JSON number with zero fractional
    part) must get the SAME verdict from the code as from
    ``resolution-profile.schema.json``'s own ``"type": "integer"`` keyword
    (which, per the JSON Schema spec, already accepts a zero-fractional
    float) — both now agree: valid. A genuinely fractional float (``5.5``)
    is rejected by both.
    """
    assert profile.is_valid_profile({"profile_id": "x", "k": 5.0})
    assert not profile.is_valid_profile({"profile_id": "x", "k": 5.5})
    assert not profile.is_valid_profile({"profile_id": "x", "k": True})


# fix round, item 3 + item 5 (PR4):
def test_resolution_profile_weight_mappings_reject_bool_nan_inf_negative():
    for field, pair in (("d_blend_weights", ("links", "nesting")),
                        ("match_blend_weights", ("term", "structural"))):
        key_a, key_b = pair
        assert not profile.is_valid_profile({"profile_id": "x", field: {key_a: True, key_b: 0.5}})
        assert not profile.is_valid_profile({"profile_id": "x", field: {key_a: float("nan"), key_b: 0.5}})
        assert not profile.is_valid_profile({"profile_id": "x", field: {key_a: float("inf"), key_b: 0.5}})
        assert not profile.is_valid_profile({"profile_id": "x", field: {key_a: -0.1, key_b: 0.5}})
        assert profile.is_valid_profile({"profile_id": "x", field: {key_a: 0.3, key_b: 0.7}})


def test_resolution_profile_relational_suppression_scale_boundaries():
    """§8a's down-weighting scale (decided 2026-10-03) — positive, finite,
    never a bool; not required to be an integer."""
    assert profile.is_valid_profile({"profile_id": "x", "relational_suppression_scale": 1})
    assert profile.is_valid_profile({"profile_id": "x", "relational_suppression_scale": 2.5})
    assert not profile.is_valid_profile({"profile_id": "x", "relational_suppression_scale": 0})
    assert not profile.is_valid_profile({"profile_id": "x", "relational_suppression_scale": -1})
    assert not profile.is_valid_profile({"profile_id": "x", "relational_suppression_scale": True})
    assert not profile.is_valid_profile(
        {"profile_id": "x", "relational_suppression_scale": float("nan")})
    assert not profile.is_valid_profile(
        {"profile_id": "x", "relational_suppression_scale": float("inf")})
    assert profile.resolve_profile({"profile_id": "x"})["relational_suppression_scale"] == 1


def test_resolve_profile_merges_a_partial_weight_mapping_with_the_default():
    """A profile that overrides only ONE key of a weight mapping must
    still resolve the OTHER key from DEFAULTS, not drop it (a resolver
    that replaces the mapping wholesale instead of merging it would
    silently lose the missing key — there is no field-level rejection for
    this, since a partially-specified weight dict is not itself a
    validation violation; it is :func:`profile.resolve_profile`'s own
    merge contract)."""
    resolved = profile.resolve_profile({"profile_id": "x", "match_blend_weights": {"term": 0.9}})
    assert resolved["match_blend_weights"] == {"term": 0.9, "structural": 0.3}
    resolved = profile.resolve_profile({"profile_id": "x", "d_blend_weights": {"nesting": 0.9}})
    assert resolved["d_blend_weights"] == {"links": 0.5, "nesting": 0.9}


# A non-finite
# WEIGHT SUM (two individually finite weights that overflow when added)
# must be rejected by profile_violations, agreeing with combine_scores().
def test_resolution_profile_rejects_a_non_finite_weight_sum():
    overflow = {"profile_id": "x", "match_blend_weights": {"term": 1e308, "structural": 1e308}}
    assert not profile.is_valid_profile(overflow)
    overflow_d = {"profile_id": "x", "d_blend_weights": {"links": 1e308, "nesting": 1e308}}
    assert not profile.is_valid_profile(overflow_d)
    with pytest.raises(ValueError):
        match.combine_scores(0.5, 0.5, {"term": 1e308, "structural": 1e308})


def test_resolution_profile_non_negative_number_fields_reject_nan():
    assert not profile.is_valid_profile({"profile_id": "x", "staleness_window_seconds": float("nan")})
    assert not profile.is_valid_profile({"profile_id": "x", "staleness_window_seconds": float("-inf")})


# ── clause-cues (§8a) ───────────────────────────────────────────────────────
#: resolve_references()'s own keyword set — a "raw"/"point"/"links"/
#: "combined" vector MAY carry any of these — the dispatch reaches
#: these entry points — to exercise
#: ``xref_resolver="shared-v2"`` through the pipeline, not only through
#: ``resolve_references`` directly.
_XREF_DISPATCH_KEYS = (
    "xref_resolver", "enclosing_unit", "numbering_family",
    "host_instrument_name", "whole_host_unit", "preceding_text",
    "enclosing_units", "host_title_instrument", "host_section_numbers",
)


@pytest.mark.parametrize("path", _load("clause-cues"), ids=lambda p: p.stem)
def test_clause_cues(path):
    v = _case(path)
    inp = v["input"]
    host = inp.get("host_instrument_number")
    xref_kwargs = {k: inp[k] for k in _XREF_DISPATCH_KEYS if k in inp}
    if "raw" in v["expected"]:
        raw = clause_cues.clause_cue_contributions(
            inp["text"], inp.get("self_article_number"),
            host_instrument_number=host, **xref_kwargs)
        assert raw == v["expected"]["raw"], v["case"]
        if "cross_reference_targets" in v["expected"]:
            cross = clause_cues.cross_reference_targets(
                inp["text"], inp.get("self_article_number"), host_instrument_number=host)
            assert cross == v["expected"]["cross_reference_targets"], v["case"]
    elif "point" in v["expected"]:
        point = clause_cues.clause_cue_point(
            inp["text"], inp.get("base_fact"), self_article_number=inp.get("self_article_number"),
            host_instrument_number=host, **xref_kwargs)
        assert point == v["expected"]["point"], v["case"]
    elif "links" in v["expected"]:
        links = clause_cues.cross_reference_links(
            inp["text"], inp["source_id"], inp.get("self_article_number"),
            host_instrument_number=host, **xref_kwargs)
        assert links == v["expected"]["links"], v["case"]
    elif "references" in v["expected"]:
        # the SHARED cross-reference resolver (spec/SPEC.md §8a.1,
        # profile field "xref_resolver": "shared-v2") —
        # :func:`clause_cues.resolve_references`. ``inp`` carries every
        # keyword :func:`resolve_references` accepts besides ``text``.
        kwargs = {k: v for k, v in inp.items() if k != "text"}
        refs = clause_cues.resolve_references(inp["text"], **kwargs)
        assert refs == v["expected"]["references"], v["case"]
    elif "enclosing_units" in v["expected"]:
        # The ancestor-chain derivation.
        got = clause_cues.enclosing_units_at(
            inp["source_text"], inp["offset"], inp.get("numbering_family", "eu"))
        assert got == v["expected"]["enclosing_units"], v["case"]
    elif "enclosing_unit" in v["expected"]:
        # Enclosing-unit derivation, moved INTO 5d-nd.
        got = clause_cues.enclosing_unit_at(
            inp["source_text"], inp["offset"], inp.get("numbering_family", "eu"))
        assert got == v["expected"]["enclosing_unit"], v["case"]
    else:
        combined = clause_cues.combined_contributions(
            inp["text"], inp.get("base_fact"), inp.get("self_article_number"),
            host_instrument_number=host, **xref_kwargs)
        assert combined == v["expected"]["combined"], v["case"]


# Dispatch fails CLOSED on every direct entry point an unrecognised
# xref_resolver value can reach — not just
# resolve_references()/_xref_count_and_objects() in isolation.
def test_clause_cues_xref_resolver_fails_closed_on_every_entry_point():
    bad_text = "Article 5 applies."
    for fn, kwargs in (
        (clause_cues.cross_reference_links,
         dict(text=bad_text, source_id="s1", xref_resolver="bogus")),
        (clause_cues.clause_cue_contributions, dict(text=bad_text, xref_resolver="bogus")),
        (clause_cues.combined_contributions, dict(sentence=bad_text, xref_resolver="bogus")),
        (clause_cues.clause_cue_point, dict(sentence=bad_text, xref_resolver="bogus")),
    ):
        with pytest.raises(ValueError):
            fn(**kwargs)


# The two *_from_profile wrappers must thread enclosing_units through to
# resolve_references() exactly the same way their own underlying
# function does — a DIRECT test, since the generic vector runner above
# has no "..._from_profile" dispatch branch.
def test_clause_cue_point_from_profile_threads_enclosing_units():
    profile_doc = {"profile_id": "x", "xref_resolver": "shared-v2"}
    text = "This Chapter applies."
    with_units = clause_cues.clause_cue_point_from_profile(
        text, profile_doc=profile_doc, numbering_family="uk",
        enclosing_units={"part": "Part 7"})
    without_units = clause_cues.clause_cue_point_from_profile(
        text, profile_doc=profile_doc, numbering_family="uk")
    assert with_units["structural"] == 0.0
    assert without_units["structural"] == pytest.approx(0.333333)
    assert with_units != without_units


def test_cross_reference_links_from_profile_threads_enclosing_units():
    profile_doc = {"profile_id": "x", "xref_resolver": "shared-v2"}
    text = "This Chapter applies."
    with_units = clause_cues.cross_reference_links_from_profile(
        text, "sid-from-profile", profile_doc=profile_doc, numbering_family="uk",
        enclosing_units={"part": "Part 7"})
    without_units = clause_cues.cross_reference_links_from_profile(
        text, "sid-from-profile", profile_doc=profile_doc, numbering_family="uk")
    assert with_units == []
    assert without_units and without_units[0]["o"] == "Chapter"


# A DIRECT test of host_section_numbers_in() itself — kills a mutant
# that always returns set() (never derives anything), and one that
# returns a kind of non-US family's own section numbers.
def test_host_section_numbers_in_derives_us_section_headings():
    source = "§ 9815. Scope.\n(a) In general.\nSomething.\n§ 9816. Other.\nText.\n"
    assert clause_cues.host_section_numbers_in(source, "us") == {"9815", "9816"}
    # A non-"us" family is NOT attempted — always empty, never a wrong
    # guess.
    assert clause_cues.host_section_numbers_in(source, "eu") == set()
    assert clause_cues.host_section_numbers_in("", "us") == set()


# fix round, item 5: kill CC6/CC7/CC8 directly.
def test_clause_cues_cross_reference_link_dimension_is_structural():
    links = clause_cues.cross_reference_links(
        "This measure is referred to in Article 6(1).", "entry-x")
    assert links, "fixture must actually produce a link"
    assert all(link["dimension"] == "structural" for link in links)


# A DIRECT test that cross_reference_links forwards
# host_instrument_number — kills a mutant that silently drops it
# before calling cross_reference_targets).
def test_clause_cues_cross_reference_links_forwards_host_instrument_number():
    text = "Article 45 of Regulation (EU) 2016/679 lays down the adequacy mechanism."
    without_host = clause_cues.cross_reference_links(text, "entry-x")
    assert without_host == [], "without the host number this citation must stay EXTERNAL (no link)"
    with_host = clause_cues.cross_reference_links(
        text, "entry-x", host_instrument_number="2016/679")
    assert len(with_host) == 1
    assert with_host[0]["o"] == "Article 45"


def test_clause_cues_default_saturation_constant_is_three():
    assert clause_cues.DEFAULT_CLAUSE_CUE_SATURATION == 3


def test_clause_cue_point_honours_a_custom_saturation():
    # three independent causal hits -> raw causal = 3
    text = "If the system fails, because a risk results, the controller shall notify where required."
    raw = clause_cues.clause_cue_contributions(text)
    assert raw["causal"] >= 3, raw
    default_point = clause_cues.clause_cue_point(text, None)
    custom_point = clause_cues.clause_cue_point(text, None, saturation=6)
    assert default_point["causal"] == 1.0  # saturated at the default (3)
    assert custom_point["causal"] == round(raw["causal"] / 6, 6)
    assert default_point["causal"] != custom_point["causal"]


# Cross-reference
# precision — direct tests for behaviours a single pinned vector cannot
# exercise generically (the Treaty exclusion, the range cap boundary).
def test_clause_cues_treaty_citation_excluded():
    assert clause_cues.cross_reference_targets(
        "This measure derives from Article 16 of the Treaty on the "
        "Functioning of the European Union.") == []


# Cross
# -reference edge cases and the quote-means possessive false positive.
def test_clause_cues_tfeu_teu_charter_excluded():
    assert clause_cues.cross_reference_targets("This provision derives from Article 16 TFEU.") == []
    assert clause_cues.cross_reference_targets("This provision derives from Article 16 TEU.") == []
    assert clause_cues.cross_reference_targets(
        "This right is protected by Article 16 of the Charter.") == []


def test_clause_cues_council_regulation_excluded():
    assert clause_cues.cross_reference_targets(
        "This matter is governed by Article 4 of Council Regulation (EC) No 1/2003.") == []


# A MULTI-word qualifier before "Regulation" ("Commission
# Implementing Regulation", "European Parliament Regulation") also counts as
# external — not only a single qualifying word.
def test_clause_cues_multi_word_regulation_qualifier_excluded():
    assert clause_cues.cross_reference_targets(
        "This matter is governed by Article 6 of Commission Implementing "
        "Regulation (EU) 2021/1372.") == []
    assert clause_cues.cross_reference_targets(
        "This matter is governed by Article 7 of European Parliament "
        "Regulation (EU) 2019/817.") == []


# "Regulation (EU) 2016/679" NAMES the HOST instrument
# (GDPR's own number) — "Article 45 of Regulation (EU) 2016/679" resolves to
# [45], INTERNAL, when the host's own number is supplied; without it, the
# bare "of ... Regulation" pattern still (correctly, conservatively) excludes
# it, since this module cannot know its own host number on its own.
def test_clause_cues_host_instrument_number_overrides_external_exclusion():
    text = "Article 45 of Regulation (EU) 2016/679 lays down the adequacy mechanism."
    assert clause_cues.cross_reference_targets(text) == []
    assert clause_cues.cross_reference_targets(
        text, host_instrument_number="2016/679") == [45]
    # a DIFFERENT instrument number is not the host -> still excluded.
    assert clause_cues.cross_reference_targets(
        text, host_instrument_number="2016/680") == []


def test_clause_cues_double_trailing_group_citation_excluded():
    assert clause_cues.cross_reference_targets(
        "As set out in point (b) of Article 1(1)(b) of Directive (EU) 2015/1535.") == []


def test_clause_cues_singular_to_is_never_a_range():
    assert clause_cues.cross_reference_targets("See Article 12 to 30 for details.") == [12]
    assert clause_cues.cross_reference_targets(
        "In such cases, Articles 15 to 20 shall not apply.") == [15, 16, 17, 18, 19, 20]


def test_clause_cues_plural_to_days_is_also_not_a_range():
    """X4: the time-duration lookahead protects the PLURAL branch too,
    not only the singular one."""
    assert clause_cues.cross_reference_targets(
        "See Articles 12 to 30 days for the retention period.") == [12]


def test_clause_cues_range_connector_number_word_boundary():
    """X5: the plural connector's own number must be matched in FULL
    (word-boundary-terminated), the same digit-backtracking fix as the
    base number — a regex missing the trailing \\b could backtrack a
    two-digit connector number down to one digit to dodge the
    day/week/... lookahead."""
    assert clause_cues.cross_reference_targets(
        "See Articles 1 to 30 days for the retention period.") == [1]


def test_clause_cues_quote_means_requires_a_quoted_term_not_a_possessive():
    """Q1/finding 6: a bare possessive apostrophe ("the data subject's
    rights", "the processor's means") is NOT a quoted term — the pattern
    requires an OPENING quote before the closing one."""
    assert clause_cues.count_cue_hits(
        "The controller shall protect the data subject's rights by means "
        "of appropriate safeguards.", "structural") == 0
    assert clause_cues.count_cue_hits(
        "The processor's means shall be documented.", "structural") == 0


def test_clause_cues_quote_means_window_covers_a_real_intervening_qualifier():
    """Q1: the gap between the closing quote and "means" must be allowed
    up to the documented 30 characters — this fixture's own "means:" is
    NOT followed by any/a/an/the, so only the quote-scoped pattern (not
    the separate "means any/a/an/the" cue) can be responsible for the
    hit; a window narrowed to 3 characters would miss it."""
    assert clause_cues.count_cue_hits(
        "'consent' of the data subject means: see paragraph 4.", "structural") == 2
    assert clause_cues.count_cue_hits(
        "'consent' of the data subject means any freely given indication.",
        "structural") == 1


def test_clause_cues_range_cap_boundary():
    """EXT4: a range exactly AT the cap (50) still fully expands; one
    MORE than the cap does not — falls back to the two endpoints only,
    never raising and never silently expanding an unbounded range."""
    at_cap = clause_cues.cross_reference_targets("See Articles 1 to 51 inclusive.")
    assert at_cap == list(range(1, 52))
    over_cap = clause_cues.cross_reference_targets("See Articles 1 to 52 inclusive.")
    assert over_cap == [1, 52]


def test_clause_cues_dedup_does_not_merge_two_adjacent_non_overlapping_spans():
    """DD2: two spans that TOUCH exactly (one ends where the next begins,
    zero gap) are still TWO distinct occurrences, not merged into one —
    only a genuinely OVERLAPPING span (start before the previous end)
    collapses."""
    assert clause_cues._dedup_hit_count([(0, 5), (5, 10)]) == 2
    assert clause_cues._dedup_hit_count([(0, 5), (3, 10)]) == 1  # genuinely overlapping
    assert clause_cues._dedup_hit_count([]) == 0


def test_requirement_without_negates_without_the_prejudice_exemption():
    """NEG3-equivalent: 'without' (outside the 'without prejudice to'
    exemption) still negates — e.g. 'without human intervention'."""
    assert "human_intervention" not in requirement.tag_concepts(
        "The decision is made without human intervention.")


def test_requirement_never_negator_still_fires():
    """NEG7-equivalent: 'never' still negates ('we never use profiling')."""
    assert requirement.tag_concepts("We never use profiling.") == set()


# ── match-blend (§19) ────────────────────────────────────────────────────────
@pytest.mark.parametrize("path", _load("match-blend"), ids=lambda p: p.stem)
def test_match_blend(path):
    v = _case(path)
    inp = v["input"]
    result = match.combine_scores(inp["term_score"], inp["structural_score"], inp.get("weights"))
    assert result == v["expected"]["combined"], v["case"]


def test_match_blend_rejects_malformed_weights():
    with pytest.raises(ValueError):
        match.combine_scores(0.5, 0.5, {"term": 1.0})  # missing 'structural' key
    with pytest.raises(ValueError):
        match.combine_scores(0.5, 0.5, {"term": 0.0, "structural": 0.0})  # sum not > 0
    with pytest.raises(ValueError):
        match.combine_scores(1.5, 0.5)  # out of [0, 1]


def test_match_blend_default_weights_are_fixed_a_priori():
    assert match.DEFAULT_MATCH_BLEND_WEIGHTS == {"term": 0.7, "structural": 0.3}
    assert profile.DEFAULTS["match_blend_weights"] == match.DEFAULT_MATCH_BLEND_WEIGHTS
    assert match.DEFAULT_MATCH_BLEND_WEIGHTS is not profile.DEFAULTS["match_blend_weights"]


# fix round, item 3 + item 5 (MA2/MA5/MA6):
def test_match_blend_rejects_negative_weight():
    with pytest.raises(ValueError):
        match.combine_scores(0.5, 0.5, {"term": -0.1, "structural": 0.3})


def test_match_blend_rejects_non_finite_weight_and_sum():
    with pytest.raises(ValueError):
        match.combine_scores(0.5, 0.5, {"term": float("nan"), "structural": 0.3})
    with pytest.raises(ValueError):
        match.combine_scores(0.5, 0.5, {"term": float("inf"), "structural": 0.3})
    with pytest.raises(ValueError):
        match.combine_scores(0.5, 0.5, {"term": float("inf"), "structural": float("-inf")})


def test_match_blend_rejects_bool_score():
    with pytest.raises(ValueError):
        match.combine_scores(True, 0.5)
    with pytest.raises(ValueError):
        match.combine_scores(0.5, False)


def test_match_blend_rejects_non_finite_score():
    with pytest.raises(ValueError):
        match.combine_scores(float("nan"), 0.5)
    with pytest.raises(ValueError):
        match.combine_scores(0.5, float("inf"))


def test_combine_scores_from_profile_actually_uses_the_profile_weights():
    custom = match.combine_scores_from_profile(
        0.9, 0.1, {"profile_id": "x", "match_blend_weights": {"term": 0.0, "structural": 1.0}})
    default = match.combine_scores_from_profile(0.9, 0.1, {"profile_id": "x"})
    assert custom != default
    assert custom == match.combine_scores(0.9, 0.1, {"term": 0.0, "structural": 1.0})


# ── replay: runtime never enters a hashed result (fix round, item 5) ────────
def test_timed_call_keeps_runtime_out_of_the_result():
    from five_d_nd import replay

    result, elapsed = replay.timed_call(match.combine_scores, 0.8, 0.2)
    assert result == match.combine_scores(0.8, 0.2)
    assert isinstance(elapsed, float) and elapsed >= 0.0
    # the result itself carries nothing timing-shaped
    assert isinstance(result, float)


# ── term-grammar (§9 EXAMPLE) ────────────────────────────────────────────────
_TERM_CORPUS = {
    "a": "The controller shall notify the supervisory authority without undue delay.",
    "b": "The processor shall assist the controller in responding to requests.",
    "c": "The data subject has the right to obtain a copy of personal data.",
}
_TERM_PROFILE = term.build_term_profile(_TERM_CORPUS, profile_id="term-nd-conformance-fixture")


@pytest.mark.parametrize("path", _load("term-grammar"), ids=lambda p: p.stem)
def test_term_grammar(path):
    v = _case(path)
    case, inp, expected = v["case"], v["input"], v["expected"]
    if case == "profile-digest-deterministic":
        rebuilt = term.build_term_profile(inp["doc_texts"], profile_id=inp["profile_id"])
        assert rebuilt["profile_digest"] == expected["profile_digest"]
    elif case in ("bm25-vector-known-terms", "unpinned-term-dropped-not-crashed"):
        got = term.bm25_vector(inp["text"], _TERM_PROFILE)
        assert got == expected["vector"]
    elif case == "nd-system-validates-under-section-9":
        assert contract.nd_system_violations(inp["nd_system"]) == expected["violations"]
    elif case == "descriptor-validates-under-section-9":
        assert contract.descriptor_violations(inp["descriptor"]) == expected["violations"]
    elif case == "claims-bind-relational-not-a-sixth-dimension":
        claims = term.produce_term_claims(inp["entry_id"], inp["text"], _TERM_PROFILE)
        assert all(c["dimension"] == "relational" for c in claims) == expected["all_relational"]
        assert len(claims) == expected["n_claims"]
    elif case == "cosine-self-similarity-is-one":
        vec = term.l2_normalize(term.bm25_vector(inp["text"], _TERM_PROFILE))
        assert term.sparse_cosine(vec, vec) == expected["cosine"]
    elif case == "cosine-differing-spans-below-one":
        vec_a = term.l2_normalize(term.bm25_vector(inp["text_a"], _TERM_PROFILE))
        vec_b = term.l2_normalize(term.bm25_vector(inp["text_b"], _TERM_PROFILE))
        got = term.sparse_cosine(vec_a, vec_b)
        assert got == expected["cosine"]
        assert (got < 1.0) == expected["below_one"]
    else:
        pytest.fail(f"unhandled term-grammar case {case!r}")


# fix round, items 4c/5/9 (TM3/TM5/TM6):
def test_term_grammar_descriptor_binds_relational_not_structural():
    """TM3: the published binding must be exactly relational — both
    'relational' and 'structural' independently pass §9's own shape
    validator (both are valid dimensions), so the shape-only vectors
    cannot by themselves catch a mutant that swaps the bound dimension."""
    desc = term.build_descriptor("digest-fixture")
    assert desc["binding"]["term_weight"] == "relational"


def test_term_grammar_claim_weights_are_normalised_not_collapsed_to_one():
    """TM5 + item 9: a multi-term span must NOT have every claim weight
    collapse to 1.0 (the WITHDRAWN clamp's own defect, measured on the
    real GDPR corpus at over 92% of all claims) — the top term is 1.0,
    every other term's weight stays strictly below it and proportional."""
    corpus = {
        "a": "The controller shall notify the supervisory authority without undue delay.",
        "b": "The processor shall assist the controller in responding to requests.",
    }
    profile = term.build_term_profile(corpus)
    claims = term.produce_term_claims("a", corpus["a"], profile)
    weights = {c["weight"] for c in claims}
    assert len(weights) > 1, "a real multi-term span must not collapse to one weight value"
    assert max(weights) == 1.0
    assert all(0.0 <= w <= 1.0 for w in weights)


def test_term_grammar_tokenizer_is_actually_pinned_in_the_digest():
    """TM6: the profile document must carry the tokenizer's OWN pattern
    and stopword list, so a tokenizer edit (e.g. accepting one-letter
    tokens) changes profile_digest — proving the module docstring's
    'pinned by digest' claim about the tokenizer, not merely stating it."""
    corpus = {"a": "The controller shall notify the authority.", "b": "A processor assists."}
    profile = term.build_term_profile(corpus)
    assert profile["token_pattern"] == term.TOKEN_RE.pattern
    assert profile["stopwords"] == sorted(term.STOPWORDS)
    # an independently-reconstructed profile with a DIFFERENT tokenizer
    # pattern recorded must digest DIFFERENTLY, even over the identical
    # vocabulary/df/avgdl/k1/b — proving the field actually participates.
    tampered = dict(profile)
    del tampered["profile_digest"]
    tampered["token_pattern"] = r"[a-zA-Z]{1,}"
    from five_d_nd.grounding import digest as _digest
    assert _digest(tampered)["sha256"] != profile["profile_digest"]


# The pinned
# tokenizer must be ENFORCED by every consumer of an already-built
# profile, not merely recorded.
def test_term_grammar_bm25_vector_rejects_a_mismatched_tokenizer_profile():
    corpus = {"a": "The controller shall notify the authority.", "b": "A processor assists."}
    profile = term.build_term_profile(corpus)
    tampered = dict(profile)
    tampered["token_pattern"] = r"[a-zA-Z]{1,}"  # a DIFFERENT tokenizer than the module's current one
    with pytest.raises(ValueError):
        term.bm25_vector("The controller shall notify.", tampered)
    tampered2 = dict(profile)
    tampered2["stopwords"] = []
    with pytest.raises(ValueError):
        term.bm25_vector("The controller shall notify.", tampered2)
    # an OLD profile from before this fix round, missing the fields entirely,
    # is ALSO rejected — never silently treated as a match.
    old_shape = {k: v for k, v in profile.items() if k not in ("token_pattern", "stopwords")}
    with pytest.raises(ValueError):
        term.bm25_vector("The controller shall notify.", old_shape)
    # the UNMODIFIED profile (same module, same tokenizer) still works.
    term.bm25_vector("The controller shall notify.", profile)


# ── requirement-grammar (§9 EXAMPLE, graft D+) ───────────────────────────────
_REQUIREMENT_RULESET = requirement.load_ruleset()


@pytest.mark.parametrize("path", _load("requirement-grammar"), ids=lambda p: p.stem)
def test_requirement_grammar(path):
    v = _case(path)
    case, inp, expected = v["case"], v["input"], v["expected"]
    if "violations" in expected:
        assert requirement.ruleset_violations(inp["ruleset"]) == expected["violations"], v["case"]
    elif case == "ruleset-digest-is-deterministic":
        assert requirement.ruleset_digest(inp["ruleset"]) == expected["digest"]
    else:
        got = requirement.check(inp["obligation_id"], inp["texts"], _REQUIREMENT_RULESET)
        assert got == expected, v["case"]


# fix round, items 1/2/5: direct unit
# tests for behaviours a single pinned vector cannot exercise generically.
def test_requirement_grammar_rejects_malformed_texts():
    with pytest.raises(ValueError):
        requirement.check("GDPR:Art22(3)", "not a list of sentences")
    with pytest.raises(ValueError):
        requirement.check("GDPR:Art22(3)", 12345)
    with pytest.raises(ValueError):
        requirement.concepts_present("not a list")


def test_requirement_grammar_check_validates_ruleset_first():
    with pytest.raises(ValueError):
        requirement.check("X:1", ["some text"], {"ruleset_id": "bad"})  # no 'rules'


def test_requirement_grammar_trigger_uses_any_not_all():
    """RQ2: a rule with TWO trigger concepts fires on EITHER, not only when
    BOTH are present — any(), not all()."""
    ruleset = {
        "ruleset_id": "rq2-fixture",
        "rules": [{
            "obligation_id": "RQ2:1", "citation": "fixture",
            "trigger_concepts": ["automated_decision_making", "human_intervention"],
            "required_concepts": ["right_to_contest"],
        }],
    }
    got = requirement.check("RQ2:1", ["There is human intervention on the part of the controller."], ruleset)
    assert got["triggered"] is True


def test_requirement_grammar_scans_every_text_not_only_the_first():
    """RQ4: a required concept present only in the SECOND text of a
    multi-text collection must still be found."""
    texts = [
        "A decision based solely on automated processing determines the outcome.",
        "The data subject may obtain human intervention on the part of the controller, "
        "may express his or her point of view, and may contest the decision.",
    ]
    got = requirement.check("GDPR:Art22(3)", texts, _REQUIREMENT_RULESET)
    assert got["all_present"] is True, got


def test_requirement_grammar_contest_cue_is_precise():
    """RQ5: a bare 'contest' with no 'the outcome'/'the decision' object
    must NOT tag right_to_contest — the cue is deliberately narrow."""
    assert "right_to_contest" not in requirement.tag_concepts(
        "The parties may contest other matters in court.")
    assert "right_to_contest" in requirement.tag_concepts(
        "The data subject may contest the decision.")


def test_requirement_grammar_positive_control_is_satisfied():
    """A PRINCIPLED requirement
    grammar's own positive-control criterion: the source provision itself
    (here, GDPR Art. 22 end to end —
    its own (1)/(2) trigger language plus its own (3) safeguard language)
    must satisfy its own rule when run through the SAME detector a use
    case is checked against — proving the detector can find what it is
    supposed to find, not only report its absence.
    """
    path = ROOT / "conformance" / "vectors" / "requirement-grammar" / \
        "probe-old-positive-control.json"
    v = _case(path)
    got = requirement.check(v["input"]["obligation_id"], v["input"]["texts"], _REQUIREMENT_RULESET)
    assert got["triggered"] is True
    assert got["all_present"] is True
    assert got["missing"] == []


# Negation
# clause-scope (both before/after the cue), exemptions, double negation,
# the semicolon/colon clause boundary (NEG4), and mixed negated+affirmed
# occurrences (NEG6) — each tested directly, not only via a vector.
#
# The negation
# architecture is a conservative, SENTENCE-scoped rule (see the
# module docstring). The tests below exercise it in place: cases whose
# negator and cue share one sentence with no internal '.'/';'/':' still
# behave as before (a sentence-wide negation call), while cases that
# depend on the now-REMOVED soft clause boundaries, affirming
# double-negative overrides, or forward-only "without" assert
# the new, conservative result (``uncertain``, never a silent flip).


def test_requirement_negation_semicolon_is_no_longer_a_boundary():
    """';' is REMOVED as a sentence boundary — the
    held-out set's own L6/L7 showed a ';' wrongly isolating an
    EARLIER-clause cue from a LATER-clause negator ("Human intervention:
    none." / "The following safeguards are not provided; human
    intervention, ..."), a confidently-wrong flip. Widening the scope to
    the whole ';'-joined sentence is the conservative fix: a negator
    before a ';' now DOES reach a cue after it, in EITHER direction."""
    text = ("There is no human intervention available; the data subject may "
            "express his or her point of view freely.")
    assert requirement.tag_concepts(text) == set()
    states = requirement.concept_states([text])
    assert states["human_intervention"] == "uncertain"
    assert states["right_to_express_view"] == "uncertain"


def test_requirement_negation_colon_is_no_longer_a_boundary():
    """':' is REMOVED as a sentence boundary too
    (held-out L6: "Human intervention: none." — the colon must NOT wall
    the cue off from the negator that follows it)."""
    text = "Available safeguards: no human intervention."
    assert requirement.tag_concepts(text) == set()
    assert requirement.concept_states([text])["human_intervention"] == "uncertain"


def test_requirement_negation_mixed_occurrences_count_as_present():
    """NEG6: ONE negated occurrence plus ONE affirmed occurrence (in
    different sentences) must still report the concept PRESENT —
    presence needs only one affirmed occurrence anywhere, never ALL
    occurrences simultaneously un-negated."""
    text = ("There is no human intervention when the system works correctly. "
            "However, human intervention is available for all contested decisions.")
    assert "human_intervention" in requirement.tag_concepts(text)


def test_requirement_negation_scans_the_whole_sentence():
    for text in (
        "Human intervention is not offered.",
        "A chance to express their views is not provided.",
        "The option to contest the decision is not available.",
    ):
        assert requirement.tag_concepts(text) == set(), text


def test_requirement_negation_trailing_excluded_covers_a_comma_list():
    text = ("The right to obtain human intervention, the chance to express his or "
            "her point of view and the possibility to contest the decision are all excluded.")
    assert requirement.tag_concepts(text) == set()


def test_requirement_negation_long_distance_quantifier_scope():
    text = ("There is absolutely no realistic possibility at any stage of the "
            "process to obtain human intervention, to express his or her point "
            "of view or to contest the decision.")
    assert requirement.tag_concepts(text) == set()


def test_requirement_negation_new_predicate_negators():
    text = ("The controller refuses human intervention, denies data subjects "
            "the opportunity to express their views and rules out any way to "
            "contest the decision.")
    assert requirement.tag_concepts(text) == set()


def test_requirement_negation_double_negation_is_uncertain_not_present():
    """Double negatives no longer flip to ``present`` — the
    old affirming-override machinery that produced that flip was exactly
    the source of a held-out set's confidently-wrong flips, and is
    removed with no replacement. ``uncertain`` is the accepted result."""
    text = ("It is not true that there is no human intervention, no chance to "
            "express his or her point of view, and no possibility to contest "
            "the decision.")
    assert requirement.tag_concepts(text) == set()
    states = requirement.concept_states([text])
    for concept in ("human_intervention", "right_to_express_view", "right_to_contest"):
        assert states[concept] == "uncertain", (concept, states)


def test_requirement_negation_not_only_but_also_is_not_negation():
    text = ("The data subject may not only obtain human intervention but also "
            "express his or her point of view and contest the decision.")
    assert requirement.tag_concepts(text) == {
        "human_intervention", "right_to_contest", "right_to_express_view"}
    assert "automated_decision_making" in requirement.tag_concepts(
        "The controller uses not only profiling but also manual checks.")


def test_requirement_negation_without_prejudice_is_not_negation():
    text = ("Without prejudice to Article 21, human intervention, the chance to "
            "express his or her point of view and the possibility to contest "
            "the decision are guaranteed.")
    assert requirement.tag_concepts(text) == {
        "human_intervention", "right_to_contest", "right_to_express_view"}


def test_requirement_negation_without_undue_delay_is_still_uncertain():
    """"Human intervention is refused without undue delay" stays
    uncertain — "refused" is its own, un-exempted
    negation-ish token, even though "without undue delay" itself is
    exempted."""
    text = "Human intervention is refused without undue delay."
    assert requirement.tag_concepts(text) == set()
    assert requirement.concept_states([text])["human_intervention"] == "uncertain"


def test_requirement_negation_without_undue_delay_sentence_initial():
    """Item 7: a sentence-initial 'Without undue delay,' must not, by
    itself, make the sentence's own cue uncertain — the exemption removes
    only its own tokens regardless of position in the sentence."""
    text = "Without undue delay, human intervention is provided to the data subject."
    assert "human_intervention" in requirement.tag_concepts(text)


def test_requirement_negation_under_no_circumstances_suppresses_trigger():
    assert requirement.tag_concepts(
        "Under no circumstances whatsoever will the bank use profiling.") == set()


def test_requirement_trigger_algorithm_decides_paraphrase():
    assert "automated_decision_making" in requirement.tag_concepts(
        "An algorithm decides on every application.")
    assert "automated_decision_making" in requirement.tag_concepts(
        "The outcome is decided by an algorithm.")


def test_requirement_known_lexical_false_positive_is_documented():
    """A deliberately NOT-chased false positive (module docstring, item
    1(a)'s scope note): a server-log audit, a customer survey, and
    ordinary litigation all lexically match the safeguard cues without
    describing an Art. 22(3) safeguard at all."""
    text = ("Human review of the server logs takes place weekly. Users may "
            "express their views in a survey and contest the decision via court.")
    tagged = requirement.tag_concepts(text)
    assert tagged == {"human_intervention", "right_to_contest", "right_to_express_view"}


# Three-state design,
# the design's decision to stop the negation arms race.
def test_requirement_concept_states_is_three_valued():
    states = requirement.concept_states(["There is no human intervention."])
    assert states["human_intervention"] == "uncertain"
    assert states["right_to_contest"] == "absent"
    states2 = requirement.concept_states(["The data subject may obtain human intervention."])
    assert states2["human_intervention"] == "present"


def test_requirement_trigger_uncertain_flag():
    """A trigger concept whose ONLY occurrence is negated sets
    trigger_uncertain, while triggered itself stays False (triggered
    means AFFIRMED, trigger_uncertain is the separate routing
    flag for a host that should not silently skip the check)."""
    got = requirement.check(
        "GDPR:Art22(3)",
        ["Under no circumstances whatsoever will the bank use profiling."],
        _REQUIREMENT_RULESET)
    assert got["triggered"] is False
    assert got["trigger_uncertain"] is True
    assert got["needs_review"] is True
    assert got["all_present"] is None


def test_requirement_needs_review_set_when_a_required_concept_is_uncertain():
    got = requirement.check(
        "GDPR:Art22(3)",
        ["A decision based solely on automated processing is taken.",
         "There is no human intervention."],
        _REQUIREMENT_RULESET)
    assert "human_intervention" in got["uncertain"]
    assert got["needs_review"] is True
    assert got["all_present"] is False


def test_requirement_without_is_sentence_scoped_not_forward_only():
    """A negation-ish token anywhere in the sentence makes the WHOLE
    sentence's cues uncertain, including a trigger stated earlier in the
    same sentence — this is the correct, conservative behaviour: the
    forward-only "without" exception no longer applies."""
    got1 = requirement.check(
        "GDPR:Art22(3)",
        ["An algorithm decides on every application without any person involved."],
        _REQUIREMENT_RULESET)
    assert got1["triggered"] is False
    assert got1["trigger_uncertain"] is True
    got2 = requirement.check(
        "GDPR:Art22(3)",
        ["A decision based solely on automated processing is taken.",
         "A staff member re-examines each case; applicants can give their opinion and appeal."],
        _REQUIREMENT_RULESET)
    assert got2["present"] == ["human_intervention", "right_to_express_view"]
    assert got2["missing"] == ["right_to_contest"]  # documented lexical miss: bare "appeal"


def test_requirement_appeal_cue_fires_present_with_an_object():
    """Item 7: the appeal cue DOES fire ``present`` when it has the
    required object ("the decision") — the bare-"appeal" lexical miss
    documented elsewhere is about a DIFFERENT sentence, not a claim that
    the cue can never fire."""
    got = requirement.check(
        "GDPR:Art22(3)",
        ["A decision based solely on automated processing is taken.",
         "A staff member re-examines each case; applicants can give their opinion "
         "and appeal the decision."],
        _REQUIREMENT_RULESET)
    assert got["present"] == ["human_intervention", "right_to_contest", "right_to_express_view"]
    assert got["all_present"] is True


def test_requirement_new_negators():
    assert requirement.tag_concepts("Neither human intervention nor the decision is offered.") == set()
    assert requirement.tag_concepts("Human intervention isn't available.") == set()
    assert requirement.tag_concepts("Human intervention is unavailable.") == set()
    assert requirement.tag_concepts("Human intervention has been abolished.") == set()
    assert requirement.tag_concepts("There is a lack of human intervention.") == set()


def test_requirement_new_negators_single_word_refuses():
    assert requirement.tag_concepts("The controller refuses human intervention.") == set()
    assert requirement.concept_states(
        ["The controller refuses human intervention."])["human_intervention"] == "uncertain"


def test_requirement_new_negators_single_word_denies():
    assert requirement.tag_concepts("The controller denies human intervention.") == set()
    assert requirement.concept_states(
        ["The controller denies human intervention."])["human_intervention"] == "uncertain"
    assert requirement.tag_concepts("The controller denied human intervention.") == set()


def test_requirement_new_negators_single_word_rules_out():
    assert requirement.tag_concepts("The controller rules out human intervention.") == set()
    assert requirement.tag_concepts("The controller ruled out human intervention.") == set()


def test_requirement_new_negators_further_inflections():
    assert requirement.tag_concepts("Human intervention is withheld.") == set()
    assert requirement.tag_concepts("Human intervention has been discontinued.") == set()
    assert requirement.tag_concepts("Human intervention is suspended.") == set()
    assert requirement.tag_concepts("The data subject waives human intervention.") == set()
    assert requirement.tag_concepts("The right to human intervention has been revoked.") == set()
    assert requirement.tag_concepts("The controller fails to offer human intervention.") == set()
    assert requirement.tag_concepts("Human intervention has ceased.") == set()


# Full inflection groups (the lexicon previously
# claimed "WITH inflections" but was missing the -ing/-al/nominalisation
# forms the held-out set's own I1-I18 probes exercised).
def test_requirement_lexicon_full_inflection_groups():
    for text in (
        "The controller is denying human intervention to applicants.",
        "The controller keeps refusing human intervention.",
        "The refusal of human intervention is final.",
        "The policy, excluding human intervention, applies to all applicants.",
        "The terms, prohibiting any attempt to contest the decision, are binding.",
        "The contract forbids applicants to express their views.",
        "The bank withholds human intervention.",
        "The bank is discontinuing human intervention.",
        "The bank suspends human intervention during peak periods.",
        "By waiving human intervention, applicants accept the outcome.",
        "The bank is revoking human intervention.",
        "The controller is failing to provide human intervention.",
        "The bank is ceasing human intervention.",
        "The bank is ruling out human intervention.",
        "The new policy abolishes human intervention.",
        "The procedure lacks human intervention.",
        "Denial of human intervention is standard practice.",
    ):
        assert requirement.tag_concepts(text) == set(), text


def test_requirement_lexicon_in_the_absence_of_and_prevent():
    assert requirement.tag_concepts(
        "In the absence of human intervention, the decision is final.") == set()
    assert requirement.tag_concepts(
        "The policy prevents human intervention in every case.") == set()


# Additional words OUTSIDE the original lexicon —
# every addition only widens toward `uncertain`.
def test_requirement_lexicon_additional_outside_words():
    for text in (
        "Requests for human intervention are declined.",
        "Human intervention is precluded.",
        "Every request to contest the decision is rejected.",
        "Human intervention has been dispensed with.",
        "Human intervention is out of the question.",
        "Automated processing has been phased out; all decisions are taken by staff.",
    ):
        assert requirement.tag_concepts(text) == set(), text


def test_requirement_lexicon_idioms_not_chased():
    """Item 1's explicit instruction: keep idioms like "hardly ever" OUT
    of the lexicon — named in LIMITS, not chased. "Human intervention is
    hardly ever granted." still reads PRESENT (a documented, accepted
    gap, not a bug)."""
    assert "human_intervention" in requirement.tag_concepts(
        "Human intervention is hardly ever granted.")


def test_requirement_lexicon_restrict_deliberately_not_added():
    """Item 1's "measure it, record the decision" instruction for
    "restrict(ion)": on the real 546-sentence GDPR corpus, "restrict*"
    overwhelmingly names Art. 18/19's own "right to restriction of
    processing" — a LEGITIMATE safeguard, not a negation — so it is
    DELIBERATELY NOT added to the lexicon; a sentence naming that right
    must not be driven to `uncertain` by this word alone."""
    assert "human_intervention" in requirement.tag_concepts(
        "Human intervention is available even where processing is restricted under Article 18.")


def test_requirement_affirming_double_negative_now_uncertain_not_present():
    """Double negatives and "cannot be refused" no
    longer flip to ``present`` — the affirming-override
    machinery that produced this flip is removed entirely. ``uncertain``
    is the accepted, documented result."""
    for text in (
        "In no case will human intervention be denied.",
        "Human intervention cannot be refused.",
        "It is not the case that no human intervention exists.",
    ):
        assert "human_intervention" not in requirement.tag_concepts(text), text
        assert requirement.concept_states([text])["human_intervention"] == "uncertain", text


def test_requirement_right_not_to_be_subject_to_exemption_needs_no_other_negator():
    """Item 2/3's worked examples: GDPR Art. 22(1)'s own framing is
    exempted only when the sentence has NO OTHER negation-ish token. E3:
    "waive the right not to be subject to" stays uncertain because of
    "waive"."""
    exempt = "The data subject has the right not to be subject to a decision based solely on automated processing."
    assert "automated_decision_making" in requirement.tag_concepts(exempt)
    negated = "The data subject may waive the right not to be subject to automated decision-making."
    assert "automated_decision_making" not in requirement.tag_concepts(negated)
    assert requirement.concept_states([negated])["automated_decision_making"] == "uncertain"


def test_requirement_no_soft_clause_boundaries_left():
    """The earlier soft clause boundaries
    (", but"/"although"/", whereas"/"and there is") are REMOVED — a
    negator anywhere in the sentence now reaches every cue in it, with no
    narrowing. ", whereas" is no longer a boundary and is replaced below
    by a plain sentence with a negator and an affirmed cue, which is now
    ``uncertain``, not ``present``."""
    for text in (
        "No human intervention is required for low-risk cases, "
        "but every rejection is reviewed by a person.",
        "Applicants may express their views, although not in writing.",
        "The data subject can express his or her point of view and "
        "there is no human intervention.",
    ):
        assert requirement.tag_concepts(text) == set(), text


def test_requirement_sentence_boundary_colon_is_never_a_boundary():
    """':' is NEVER a sentence
    boundary any more — a cue AFTER a ':' with no negator anywhere in the
    whole (now unbroken) sentence still reads clean."""
    text = "Safeguards offered: human intervention is available on request."
    assert "human_intervention" in requirement.tag_concepts(text)


def test_requirement_sentence_boundary_abbreviation_period_is_not_a_boundary():
    """A '.' inside a known abbreviation ("Art.",
    "No.", "Nos.", "e.g.", "i.e.", "para.", "cf.", "p.") is never a
    sentence boundary — held-out L4 ("There is no right under Art.
    22(3) to obtain human intervention.") must stay ONE sentence, so the
    leading "no" reaches the cue across the "Art." abbreviation."""
    text = "There is no right under Art. 22(3) to obtain human intervention."
    assert requirement.tag_concepts(text) == set()
    assert requirement.concept_states([text])["human_intervention"] == "uncertain"
    # a genuine sentence end (period + whitespace + capital) still IS one.
    two = "Human intervention is guaranteed. No further condition applies."
    assert "human_intervention" in requirement.tag_concepts(two)


def test_requirement_sentence_boundary_real_period_still_a_boundary():
    """A genuine full stop (followed by whitespace + a capital letter)
    stays a boundary — a negator in the SECOND sentence must not reach a
    cue in the FIRST."""
    text = "Human intervention is available on request. No further step is needed."
    assert "human_intervention" in requirement.tag_concepts(text)


def test_requirement_sentence_boundary_newline_is_a_boundary():
    text = "Human intervention is not offered.\nThe data subject may contest the decision."
    assert requirement.tag_concepts(text) == {"right_to_contest"}


def test_requirement_sentence_boundary_bare_newline_no_period_is_still_a_boundary():
    """A newline is its OWN boundary, independent of the '.'/'?'/'!'
    rule — no period precedes it here, so a mutant that collapses the
    newline case into the ordinary followed-by-capital check (rather
    than returning True unconditionally) must still be caught."""
    text = "Human intervention is not offered\nThe data subject may contest the decision."
    assert requirement.tag_concepts(text) == {"right_to_contest"}


def test_requirement_sentence_boundary_period_not_followed_by_capital_is_not_a_boundary():
    """A '.' followed by whitespace and a LOWERCASE letter is never a
    boundary — the negator after it still reaches the cue before it."""
    text = "Human intervention is available. no further condition applies anywhere in this scheme."
    assert requirement.tag_concepts(text) == set()
    assert requirement.concept_states([text])["human_intervention"] == "uncertain"


def test_requirement_sentence_boundary_abbreviation_followed_by_a_real_capital():
    """The abbreviation check is only reachable when the text AFTER the
    abbreviation's own period actually matches the followed-by-capital
    rule — exercise that path directly (most real sentences, like "Art.
    22(3)", are already excluded by the digit after the period, which is
    not itself a capital letter; this uses a capitalised word right after
    the abbreviation so the abbreviation check itself is load-bearing)."""
    text = "Human intervention is available under Art. Never will it be withheld from an applicant."
    assert requirement.tag_concepts(text) == set()
    assert requirement.concept_states([text])["human_intervention"] == "uncertain"


def test_requirement_sentence_boundary_lowercase_stem_fallback_followed_by_a_real_capital():
    """Rule (c) — the pre-existing stem list is the
    FALLBACK for a short, LOWERCASE stem rule (b) (capitalised, <=4
    letters) would miss: "para" is lowercase, so only rule (c) catches
    it. Exercised the same way as the capitalised case above — a real
    capital letter right after "para." so the abbreviation check is
    actually load-bearing, not merely irrelevant because of a digit."""
    text = "Human intervention is offered under para. Never is it withheld in practice."
    assert requirement.tag_concepts(text) == set()
    assert requirement.concept_states([text])["human_intervention"] == "uncertain"


def test_requirement_trigger_follows_the_same_sentence_rule():
    """Item 4: a negation-ish token in the TRIGGER's own sentence makes it
    ``trigger_uncertain``, following exactly the same rule as any other
    concept — no separate trigger-specific negation logic exists."""
    got = requirement.check(
        "GDPR:Art22(3)",
        ["The controller refuses to rely on an algorithm that decides without human input."],
        _REQUIREMENT_RULESET)
    assert got["triggered"] is False


def test_requirement_cue_table_digest_folds_in_negation_machinery():
    """The sentence-boundary pattern is the only boundary
    concept that survives the current redesign (the soft boundaries and
    leading-conditional rule are both fully removed, so
    there is nothing left of either to fold into the digest) — this test
    pins that :func:`cue_table_digest` still changes when the negation
    lexicon changes, which is the property that matters."""
    import re as _re
    original = requirement._NEGATION_RE
    try:
        before = requirement.cue_table_digest()
        requirement._NEGATION_RE = _re.compile(original.pattern + r"|\bfoobarbaz\b", _re.IGNORECASE)
        after = requirement.cue_table_digest()
        assert before != after
    finally:
        requirement._NEGATION_RE = original


# The confusion table is scored by
# CONFIDENTLY-WRONG (CONF-WRONG): a flip occurs ONLY when the code
# reports a concept/trigger
# "present"/"triggered" while the TRUTH says it is negated ("N") or not
# mentioned ("-"/"X"). ``uncertain`` against an affirmed truth, or
# ``absent``/``missing`` against a negated/unmentioned truth, is NEVER a
# flip — only a wrong ``present`` is. Runs over BOTH probe sets: the 42
# (41 distinct, one exact duplicate removed) probes
# (``probe-*``, truth re-derived from the ORIGINAL
# expected-present sets, lumping "negated" and "not mentioned"
# into one non-affirmed bucket "X") and the 45 fresh
# held-out probes (``heldout1-*``, truth copied verbatim from an
# independent held-out annotation, provenance "Held-out set 1").
#: Documented, accepted exceptions to the
#: confidently-wrong bar — named in the module docstring's LIMITS list,
#: not silently tolerated. O7 is the "hardly ever" IDIOM,
#: deliberately kept out of the lexicon; X1 is CROSS-SENTENCE negation,
#: out of scope by design. Held-out set 3 adds O1-O6, SIX
#: MORE out-of-lexicon synonyms ("cancelled"/"eliminated"/"unobtainable"/
#: "exempt from"/"instead of"/"seldom") and X1/X2, two more
#: cross-sentence cases — all named explicitly as
#: ACCEPTED, not defects; none were fixed by later lexicon/
#: boundary changes, so none are dropped from this set. A NEW flip anywhere
#: else still fails this test.
_KNOWN_ACCEPTED_FLIPS = frozenset({
    ("heldout2-o7-hardly-ever", "human_intervention"),
    ("heldout2-x1-cross-sentence-neg", "human_intervention"),
    ("heldout2-x1-cross-sentence-neg", "right_to_express_view"),
    ("heldout2-x1-cross-sentence-neg", "right_to_contest"),
    ("heldout3-o1-cancelled", "human_intervention"),
    ("heldout3-o2-eliminated", "human_intervention"),
    ("heldout3-o3-unobtainable", "human_intervention"),
    ("heldout3-o4-exempt-from", "human_intervention"),
    ("heldout3-o5-instead-of", "human_intervention"),
    ("heldout3-o6-seldom", "human_intervention"),
    ("heldout3-x1-question-then-no", "human_intervention"),
    ("heldout3-x2-mentioned-then-never", "human_intervention"),
})


def test_requirement_confusion_table_zero_confidently_wrong_flips():
    HI, EV, CO = "human_intervention", "right_to_express_view", "right_to_contest"
    concepts = (HI, EV, CO)
    conf_wrong = []
    uncertain_n = 0
    lexical_miss_n = 0
    checked = {"probe": 0, "heldout1": 0, "heldout2": 0, "heldout3": 0, "heldout4": 0}
    for path in _load("requirement-grammar"):
        v = _case(path)
        truth = v.get("truth")
        if truth is None:
            continue
        if path.stem.startswith("heldout1-"):
            bucket = "heldout1"
        elif path.stem.startswith("heldout2-"):
            bucket = "heldout2"
        elif path.stem.startswith("heldout3-"):
            bucket = "heldout3"
        elif path.stem.startswith("heldout4-"):
            bucket = "heldout4"
        else:
            bucket = "probe"
        checked[bucket] += 1
        got = requirement.check(
            v["input"]["obligation_id"], v["input"]["texts"], _REQUIREMENT_RULESET)
        present, uncertain = set(got["present"]), set(got["uncertain"])
        for c in concepts:
            t = truth[c]
            o = "P" if c in present else "U" if c in uncertain else "-"
            if t == "A":
                if o == "U":
                    uncertain_n += 1
                elif o == "-":
                    lexical_miss_n += 1
            else:  # "N" or "X" (lumped negated/not-mentioned for the probe set)
                if o == "P":
                    conf_wrong.append((path.stem, c))
                elif o == "U":
                    uncertain_n += 1
        tt = truth["trigger"]
        to = "T" if got["triggered"] else "U" if got["trigger_uncertain"] else "-"
        if tt == "A":
            if to == "U":
                uncertain_n += 1
            elif to == "-":
                lexical_miss_n += 1
        elif tt in ("N", "X"):
            if to == "T":
                conf_wrong.append((path.stem, "trigger"))
            elif to == "U":
                uncertain_n += 1
        elif tt == "-":
            # A trigger truly NOT MENTIONED must not
            # read `triggered` either — a false `triggered` here is just
            # as confidently wrong as a false one on a negated trigger.
            if to == "T":
                conf_wrong.append((path.stem, "trigger"))
            elif to == "U":
                uncertain_n += 1
    assert checked["probe"] >= 40, checked
    assert checked["heldout1"] == 45, checked
    assert checked["heldout2"] == 51, checked
    assert checked["heldout3"] == 46, checked
    assert checked["heldout4"] == 45, checked
    unexpected = [f for f in conf_wrong if f not in _KNOWN_ACCEPTED_FLIPS]
    assert unexpected == [], (
        f"{len(unexpected)} UNEXPECTED confidently-wrong flip(s): {unexpected!r} "
        f"(uncertain: {uncertain_n}, lexical-miss: {lexical_miss_n})")
    assert set(conf_wrong) == _KNOWN_ACCEPTED_FLIPS, (
        "a previously-accepted flip disappeared — update _KNOWN_ACCEPTED_FLIPS "
        f"if it was genuinely fixed: {set(conf_wrong)!r}")


# The run time once grew SUPERLINEARLY — every cue
# occurrence recomputed every sentence boundary for the WHOLE text from
# scratch, and the abbreviation check scanned from position 0 every
# time. 31k chars took 3,723s before the fix below; the whole GDPR corpus as
# ONE text took ~400s. Two tests: a WALL-CLOCK bound (generous, so it is
# not flaky) and a DETERMINISTIC one that counts the actual boundary
# -computation calls, so a future regression that reintroduces the
# recomputation is caught even if the machine running the test happens
# to be fast enough to still clear the wall-clock bound.
def test_requirement_check_on_a_200k_char_text_is_fast():
    import time
    text = ("The data subject may obtain human intervention, express his or her point of view "
             "and contest the decision in accordance with Article 22(3). ") * 2500
    text = text[:200_000]
    assert len(text) == 200_000
    t0 = time.perf_counter()
    requirement.check("GDPR:Art22(3)", [text], _REQUIREMENT_RULESET)
    elapsed = time.perf_counter() - t0
    assert elapsed < 2.0, f"check() on a 200k-char text took {elapsed:.3f}s (bound: 2.0s)"


def test_requirement_sentence_boundaries_computed_once_per_text_not_per_occurrence():
    """Deterministic guard (no flaky timing as the ONLY one) — fix round
    7 item P: :func:`requirement._sentence_boundaries` is
    ``functools.lru_cache``-d; this asserts the cache records exactly
    ONE miss (one real computation) for a FRESH text no matter how many
    cue occurrences that text contains, by comparing cache_info() before
    and after. A regression that recomputes boundaries per occurrence
    (the original bug) would show additional misses here, independent of
    how fast or slow the machine running the suite happens to be."""
    text = (
        "Human intervention is offered. Human intervention is offered again. "
        "Human intervention is offered once more. Human intervention is offered a "
        "fourth time. Human intervention is offered a fifth time, for good measure."
    )
    before = requirement._sentence_boundaries.cache_info()
    requirement.tag_concepts(text)
    after = requirement._sentence_boundaries.cache_info()
    assert after.misses == before.misses + 1, (
        f"expected exactly one cache MISS (one real computation) for this fresh "
        f"text, got {after.misses - before.misses} — boundaries are being "
        f"recomputed per occurrence again")
    # calling it again with the SAME text must be a pure cache hit — zero
    # additional misses, confirming the cache is actually being consulted
    # (not merely present but bypassed).
    requirement.tag_concepts(text)
    final = requirement._sentence_boundaries.cache_info()
    assert final.misses == after.misses, "a second call on the same text caused a new miss"
    assert final.hits > after.hits


def test_every_family_has_vectors():
    for family in FAMILIES:
        assert _load(family), f"family {family!r} has no vectors"


# ══════════════════════════════════════════════════════════════════════════
# Differential suite 1: this module's assertoric lowering vs. the real
# loomground-factual it is ported from (§8, D1). Skipped, never failed, when
# loomground-factual is not importable.
# ══════════════════════════════════════════════════════════════════════════
try:
    from loomground_factual import grammar as _factual_grammar
    _FACTUAL_AVAILABLE = True
    _FACTUAL_UNAVAILABLE_REASON = ""
except ImportError as _factual_import_exc:
    _FACTUAL_AVAILABLE = False
    _FACTUAL_UNAVAILABLE_REASON = f"loomground_factual not installed: {_factual_import_exc}"

_factual_required = pytest.mark.skipif(not _FACTUAL_AVAILABLE, reason=_FACTUAL_UNAVAILABLE_REASON)

# The exact CASES from loomground-factual's own
# tests/test_extraction_quality.py (real definitional/assertoric provisions;
# read-only, reproduced verbatim here as differential-test fixtures — NOT a
# copy of factual's source code, just the same sentences). Unchanged across
# factual's grammar rewrite (ebf9fe1) — these six sentences never exercised
# ordering/modal/complement cues, only the copula path.
_FACTUAL_EXTRACTION_QUALITY_CASES = [
    "Biometric data is a special category of personal data.",
    "A processor is a natural or legal person which processes personal data "
    "on behalf of the controller.",
    "The AI system is not a high-risk AI system.",
    "Personal data includes any information relating to an identified natural person.",
    "All controllers are subject to this Regulation.",
    "No provider is exempt from the transparency obligations.",
]

# Ten additional cross-cutting sentences: exercise is-a, part-of,
# has-part, precedes, follows, a modal with an embedded copula-looking
# rest, predication via includes/refers-to/means, empty-quantifier
# negation, and a clausal complement.
_EXTRA_CROSS_CUTTING_SENTENCES = [
    "The record is part of the archive.",
    "Registration precedes processing.",
    "The controller must ensure that the system is a secure system.",
    "The term includes anything that is a loan.",
    "All data refers to a record that is a kind of file.",
    "The board is comprised of five members.",
    "Audit follows the review.",
    "No processor is without a contract.",
    "Personal data means any information relating to a person.",
    "The supervisor knows that the report is a draft.",
]

# factual's own cue-tiebreak / negated-required / none-path pinning tests
# (tests/test_cue_tiebreak.py, test_negated_required.py,
# test_lower_none_paths.py @ ebf9fe1) — sentences only, reproduced here as
# fixtures, not a copy of factual's test code.
_FACTUAL_PINNING_SENTENCES = [
    "A controller is required to notify the authority.",
    "All controllers are required to keep records.",
    "The provider cannot refuse access.",
    "The provider can not refuse access.",
    "The controller shall be liable.",
    "The review is followed by a decision.",
    "The canopy is green.",
    "The cannon is loaded.",
    "Every controller keeps a record.",
    "The provider is required to comply with the code.",
    "The provider is not required to comply with the code.",
    "The provider is required not to comply with the code.",
    "The controller is.",
    "The provider cannot.",
    "Must comply.",
]


def _factual_full_record(sentence: str):
    """factual's PUBLIC ``lower()`` drops ``relation``/``canonical``/``span``/
    ``subordinate``, returning only the inner ``"fact"`` sub-dict. This
    module's own ``lower_assertion()`` keeps ``relation`` and
    ``canonical`` (an ordering fact's own direction would otherwise be
    lost), so the differential compares against factual's OWN full record —
    ``_analyse()``, which ``lower()`` itself calls — flattened the same way:
    the inner ``fact`` fields plus the outer ``relation``/``canonical``
    (``span``/``subordinate`` are NOT part of this module's output and are
    dropped here too, matching ``lower_assertion()``'s own documented
    field set exactly, field for field)."""
    rec = _factual_grammar._analyse(sentence)
    if rec is None:
        return None
    out = dict(rec["fact"])
    out["relation"] = rec["relation"]
    out["canonical"] = rec["canonical"]
    return out


@_factual_required
@pytest.mark.parametrize(
    "sentence",
    _FACTUAL_EXTRACTION_QUALITY_CASES + _EXTRA_CROSS_CUTTING_SENTENCES
    + _FACTUAL_PINNING_SENTENCES,
)
def test_assertoric_lowering_matches_factual_sentence_for_sentence(sentence):
    expected = _factual_full_record(sentence)
    got = assertoric.lower_assertion(sentence)
    if expected is None:
        assert got is None, (sentence, got)
        return
    assert got == expected, (sentence, got, expected)


# ══════════════════════════════════════════════════════════════════════════
# Differential suite 2: this module's NDSystem/descriptor validation vs. the
# real versum it is ported from (§9). Skipped, never failed, when versum is
# not importable.
# ══════════════════════════════════════════════════════════════════════════
try:
    from versum.nd import NDSystem as _VersumNDSystem
    from versum.planes import (
        DescriptorPlane as _VersumDescriptorPlane,
        PlaneDescriptorError as _VersumPlaneDescriptorError,
    )
    _VERSUM_AVAILABLE = True
    _VERSUM_UNAVAILABLE_REASON = ""
except ImportError as _versum_import_exc:
    _VERSUM_AVAILABLE = False
    _VERSUM_UNAVAILABLE_REASON = f"versum not installed: {_versum_import_exc}"

_versum_required = pytest.mark.skipif(not _VERSUM_AVAILABLE, reason=_VERSUM_UNAVAILABLE_REASON)


def _versum_nd_system_valid(doc) -> bool:
    try:
        _VersumNDSystem.from_dict(doc).validate()
        return True
    except (ValueError, TypeError, AttributeError, KeyError):
        return False


# §9 P2: nd-system vectors where the code is DELIBERATELY stricter than
# versum on a malformed shape — "bindings" declared
# type is "a list of binding rule objects"; a string or a mapping is a
# malformed shape at that position regardless of how many elements it
# happens to iterate to, even though versum's own `for x in ...` tolerates
# the EMPTY "" / {} special case by accident of Python's duck-typed
# iteration — see src/five_d_nd/contract.py's own comment at the
# "bindings" check for the full rationale).
_ND_SYSTEM_VERSUM_P2_MALFORMED = frozenset({
    "invalid-bindings-empty-string-malformed-despite-versum-accepting",
    "invalid-bindings-empty-object-malformed-despite-versum-accepting",
    # versum's own `ontology_id = str(raw.get(
    # "ontology_id") or ontology.get("id") or "")` (same for
    # ontology_version) SHORT-CIRCUITS past `ontology.get(...)` entirely
    # when the FLAT ontology_id/ontology_version are both already truthy —
    # so a TRUTHY non-mapping "ontology" is accepted by versum in that one
    # combination, even though the identical "ontology" value would crash
    # versum the moment either flat field is absent (an earlier
    # established case, "invalid-axis-ontology-true-not-a-mapping"). The
    # code checks "ontology"'s own shape unconditionally (never
    # short-circuited by a sibling field) — "ontology" stays declared type
    # "object" regardless, so this remains a malformed shape at THAT field
    # (§9 P2), not a parity bug.
    "invalid-ontology-truthy-short-circuited-by-flat-fields-malformed-despite-versum-accepting",
    # §9 explicit field types — id/namespace are
    # STRING ONLY (contract.py now rejects a non-string outright, no str()
    # coercion, even str(True) == "True" which WOULD match the id pattern
    # and which versum itself therefore accepts):
    "invalid-namespace-true-malformed-despite-versum-accepting",
    # The SAME explicit type applies to "id", not only
    # "namespace" — true (str(True) == "True", matches the id pattern) and
    # null (str(None) == "None", also matches) are both still accepted by
    # versum, confirmed directly against real versum; the code rejects
    # both outright here too.
    "invalid-id-true-malformed-despite-versum-accepting",
    "invalid-id-null-malformed-despite-versum-accepting",
    # version is a STRING, or a NUMBER (never a bool) accepted via str()
    # coercion — a boolean, null, array, or object is now malformed here
    # too, even though versum's own str() coercion swallows all four:
    "invalid-version-true-malformed-despite-versum-accepting",
    "invalid-version-null-malformed-despite-versum-accepting",
    "invalid-version-empty-array-malformed-despite-versum-accepting",
    "invalid-version-array-malformed-despite-versum-accepting",
    "invalid-version-empty-object-malformed-despite-versum-accepting",
    "invalid-version-object-malformed-despite-versum-accepting",
    # ontology_relations is ARRAY ONLY — a non-array iterable (a string, a
    # dict, a set) is now malformed too, not only the non-iterable case P1
    # already covered:
    "invalid-ontology-relations-string-malformed-despite-versum-accepting",
})


@_versum_required
@pytest.mark.parametrize("path", _load("nd-system"), ids=lambda p: p.stem)
def test_nd_system_matches_versum(path):
    """§9's validator parity policy (P1, P2) — see this module's own
    docstring for the full statement."""
    v = _case(path)
    doc = v["input"]["doc"]
    ours = contract.is_valid_nd_system(doc)
    theirs = _versum_nd_system_valid(doc)
    if not theirs:
        # P1, hard, no exceptions: versum rejects => code MUST reject too.
        assert not ours, (
            v["case"], "P1 VIOLATION: versum rejects this document but the "
            "code accepts it — this is ALWAYS a defect (§9)", "ours", ours)
        return
    if not ours:
        # theirs is True here: versum accepts, but the code rejects. P2
        # permits this ONLY for a named, documented malformed-shape case.
        assert path.stem in _ND_SYSTEM_VERSUM_P2_MALFORMED, (
            v["case"], "code rejects a document versum accepts, and this "
            "case is NOT in the documented _ND_SYSTEM_VERSUM_P2_MALFORMED "
            "exception set (§9 P2) — either fix the code to match versum, "
            "or justify and name this case there")
        return
    assert ours == theirs


def _versum_descriptor_valid(doc) -> bool:
    if not isinstance(doc, Mapping):
        return False
    payload = dict(doc)
    payload.setdefault("produce", lambda *a, **k: [])
    try:
        _VersumDescriptorPlane.from_descriptor(payload)
        return True
    except _VersumPlaneDescriptorError:
        return False
    except (ValueError, TypeError, KeyError, AttributeError):
        return False


# This specification's additions beyond versum's own descriptor contract are
# the required contract_version conformance marker (§9/§10), the OPTIONAL
# co_dimensions cross-reference (§9 N3), and the runtime-vs-interchange
# produce distinction (versum's descriptor concept has no interchange form —
# it always requires produce). 5D is neutral on is/ought (N1), so binding
# values are bare dimension strings exactly like versum's own
# p5.is_dimension(dim) check — EVERY other descriptor-binding vector,
# including every normative-relation one, now agrees with versum.
# This set is intentionally small and counted plainly after the N1-N4
# redesign (it was 6 under the earlier, now-superseded, R1 mode design).
_DESCRIPTOR_VERSUM_PARITY_EXCLUDED = frozenset({
    "missing-contract-version-rejected",
    "contract-version-wrong-value-rejected",
    "co-dimensions-unknown-axis-rejected",
    "nd-system-wrapper-form-co-dimensions-undeclared-axis-rejected",
    "runtime-form-requires-produce-callable",
    "interchange-form-omits-produce-ok",
})

# §9 P2: descriptor-binding vectors (not already excluded above for being a
# spec-only addition) where the code is deliberately stricter than versum
# on a malformed shape. Empty today — every remaining divergence this
# specification knows of was fixed in later checks — but named here (not
# silently absent) so a future one has a place to go without re-litigating
# the policy, exactly like _ND_SYSTEM_VERSUM_P2_MALFORMED above.
_DESCRIPTOR_VERSUM_P2_MALFORMED = frozenset()


@_versum_required
@pytest.mark.parametrize(
    "path",
    [p for p in _load("descriptor-binding") if p.stem not in _DESCRIPTOR_VERSUM_PARITY_EXCLUDED],
    ids=lambda p: p.stem,
)
def test_descriptor_binding_matches_versum(path):
    """§9's validator parity policy (P1, P2) — see this module's own
    docstring for the full statement."""
    v = _case(path)
    doc = v["input"]["descriptor"]
    ours = contract.is_valid_descriptor(doc)
    theirs = _versum_descriptor_valid(doc)
    if not theirs:
        assert not ours, (
            v["case"], "P1 VIOLATION: versum rejects this document but the "
            "code accepts it — this is ALWAYS a defect (§9)", "ours", ours)
        return
    if not ours:
        assert path.stem in _DESCRIPTOR_VERSUM_P2_MALFORMED, (
            v["case"], "code rejects a document versum accepts, and this "
            "case is NOT in the documented _DESCRIPTOR_VERSUM_P2_MALFORMED "
            "exception set (§9 P2) — either fix the code to match versum, "
            "or justify and name this case there")
        return
    assert ours == theirs


def test_descriptor_parity_exclusions_are_all_real_vectors():
    stems = {p.stem for p in _load("descriptor-binding")}
    missing = (_DESCRIPTOR_VERSUM_PARITY_EXCLUDED | _DESCRIPTOR_VERSUM_P2_MALFORMED) - stems
    assert not missing, f"excluded vector(s) no longer exist: {missing}"


def test_nd_system_p2_malformed_exclusions_are_all_real_vectors():
    stems = {p.stem for p in _load("nd-system")}
    missing = _ND_SYSTEM_VERSUM_P2_MALFORMED - stems
    assert not missing, f"excluded vector(s) no longer exist: {missing}"


# ══════════════════════════════════════════════════════════════════════════
# Differential suite 3: every vector's INPUT validates against its family's
# JSON Schema, when jsonschema is importable. Skipped, never failed, otherwise.
# ══════════════════════════════════════════════════════════════════════════
try:
    import jsonschema
    _JSONSCHEMA_AVAILABLE = True
except ImportError:
    _JSONSCHEMA_AVAILABLE = False

try:
    from referencing import Registry, Resource
    _REFERENCING_AVAILABLE = True
except ImportError:
    _REFERENCING_AVAILABLE = False

_jsonschema_required = pytest.mark.skipif(
    not _JSONSCHEMA_AVAILABLE, reason="jsonschema not installed")

# Only families whose vectors carry a shape one of the schemas under schema/
# actually describes (dim-closed-set/compose-*/fold-left/reference-error
# vectors carry ad hoc scalars or deliberately malformed input that no schema
# is meant to accept — see schema/*.json's own scope). Each entry:
# (schema file, extractor(vector) -> instance-or-None, is_positive(vector)).
_SCHEMA_FAMILIES = {
    "nd-system": (
        "nd-system.schema.json",
        lambda v: v["input"]["doc"],
        lambda v: v["expected"]["valid"] is True,
    ),
    "descriptor-binding": (
        "grammar-descriptor.schema.json",
        lambda v: v["input"]["descriptor"],
        lambda v: v["expected"]["valid"] is True,
    ),
    "position": (
        "position.schema.json",
        lambda v: v["expected"],
        lambda v: "error" not in v["expected"],
    ),
    "point": (
        "point.schema.json",
        lambda v: v["expected"],
        lambda v: v["input"]["kind"] == "derive" and "error" not in v["expected"],
    ),
    "resolution-profile": (
        "resolution-profile.schema.json",
        lambda v: v["input"].get("doc", v["input"].get("doc_a")),
        lambda v: (
            v["expected"].get("valid") is True and isinstance(v["input"].get("doc"), Mapping)
            if "doc" in v["input"]
            else v["expected"].get("valid_a") is True and isinstance(v["input"].get("doc_a"), Mapping)
        ),
    ),
    "statement": (
        "statement.schema.json",
        lambda v: v["input"]["doc"],
        lambda v: v["expected"]["valid"] is True,
    ),
}


def _schema(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def _local_validator(schema: dict):
    """A validator for ``schema`` that resolves local $refs (e.g.
    "nd-system.schema.json", "#/$defs/...") from disk, never over the
    network.

    Prefers the modern ``referencing`` registry (what ``jsonschema`` itself
    has recommended since 4.18, and the only mechanism that correctly
    resolves a LOCAL ``#/$defs/...`` fragment inside an explicitly-supplied
    schema — the deprecated ``RefResolver`` path below does not). Falls back
    to the deprecated ``jsonschema.validators.RefResolver`` only when
    ``referencing`` itself is not installed (:data:`_REFERENCING_AVAILABLE`).
    """
    if _REFERENCING_AVAILABLE:
        resources = []
        for path in SCHEMA_DIR.glob("*.json"):
            doc = _schema(path.name)
            if "$id" in doc:
                resources.append((doc["$id"], Resource.from_contents(doc)))
        registry = Registry().with_resources(resources)
        validator_cls = jsonschema.validators.validator_for(schema)
        return validator_cls(schema, registry=registry)
    store = {}
    for path in SCHEMA_DIR.glob("*.json"):
        doc = _schema(path.name)
        if "$id" in doc:
            store[doc["$id"]] = doc
        store[path.name] = doc
    resolver = jsonschema.validators.RefResolver(
        base_uri=SCHEMA_DIR.as_uri() + "/", referrer=schema, store=store)
    validator_cls = jsonschema.validators.validator_for(schema)
    return validator_cls(schema, resolver=resolver)


def _schema_errors(schema: dict, instance) -> list:
    return list(_local_validator(schema).iter_errors(instance))


@_jsonschema_required
@pytest.mark.parametrize("family", sorted(_SCHEMA_FAMILIES))
def test_valid_vectors_satisfy_their_schema(family):
    schema_name, extractor, is_positive = _SCHEMA_FAMILIES[family]
    schema = _schema(schema_name)
    checked = 0
    for path in _load(family):
        v = _case(path)
        if not is_positive(v):
            continue  # only instances the schema is meant to ACCEPT are checked here
        if family == "nd-system" and path.stem in _ND_SYSTEM_SCHEMA_INTENTIONALLY_STRICTER:
            continue  # schema is deliberately stricter than code/versum here
        instance = extractor(v)
        if instance is None or (isinstance(instance, Mapping) and not isinstance(instance, dict)):
            continue
        errors = _schema_errors(schema, instance)
        assert not errors, (v["case"], [e.message for e in errors])
        checked += 1
    assert checked > 0, f"no valid-shaped vectors found for family {family!r}"


@_jsonschema_required
def test_is_ought_link_vectors_satisfy_link_schema():
    schema = _schema("link.schema.json")
    checked = 0
    for path in _load("is-ought"):
        v = _case(path)
        kind = v["input"]["kind"]
        if kind not in ("embeds_link", "link"):
            continue
        if not v["expected"].get("valid", True):
            continue
        errors = _schema_errors(schema, v["input"]["link"])
        assert not errors, (v["case"], [e.message for e in errors])
        checked += 1
    assert checked > 0, "no valid-shaped is-ought link vectors found"


# Individually documented, genuinely schema-inexpressible rules (NOT an
# is/ought divergence — these exist independently of N1-N4): a JSON Schema
# cannot compare two string VALUES for equality across different locations in
# a document (nd_system.version vs. language_version) without naming every
# possible value; this is a semantic, code-only check (the same category of
# gap reference.schema.json already documents for canonical span bounds).
_DESCRIPTOR_SCHEMA_INEXPRESSIBLE = frozenset({
    "nd-system-version-mismatch-rejected",
    # Item E (§9 N3): co_dimensions -> declared nd_system.axes is a
    # cross-reference a JSON Schema cannot express generically, same
    # reasoning as allowed_axes -> declared axes below (code-only).
    "co-dimensions-unknown-axis-rejected",
    # The same cross-reference, exercised through the
    # {"nd_system": {"nd_system": {...}}} wrapper form.
    "nd-system-wrapper-form-co-dimensions-undeclared-axis-rejected",
})


@_jsonschema_required
@pytest.mark.parametrize("path", _load("descriptor-binding"), ids=lambda p: p.stem)
def test_every_descriptor_binding_vector_schema_matches_code(path):
    """5D is neutral on is/ought (N1): code and schema should now agree on
    EVERY descriptor-binding vector that does not hit one of the two
    independently-documented exceptions above (the runtime-form produce
    check, and the schema-inexpressible nd_system/language_version
    cross-field equality) — no is/ought-related divergence is expected any
    more.
    """
    v = _case(path)
    if bool(v["input"].get("require_produce", False)):
        pytest.skip("runtime-form produce-callable check has no schema equivalent")
    if path.stem in _DESCRIPTOR_SCHEMA_INEXPRESSIBLE:
        pytest.skip("nd_system.version != language_version is a cross-field semantic "
                    "check a JSON Schema cannot express generically (code-only)")
    schema = _schema("grammar-descriptor.schema.json")
    schema_errors = _schema_errors(schema, v["input"]["descriptor"])
    schema_says_valid = not schema_errors
    code_says_valid = contract.is_valid_descriptor(v["input"]["descriptor"])
    assert schema_says_valid == code_says_valid == v["expected"]["valid"], (
        v["case"], "schema", schema_says_valid, "code", code_says_valid,
        "expected", v["expected"]["valid"], [e.message for e in schema_errors])


# Individually documented, genuinely schema-inexpressible rules: a JSON
# Schema cannot check that a VALUE (an allowed_axes entry) is a MEMBER OF THE
# KEY SET of another part of the same document (the declared axes) — that is
# a cross-reference, not a static shape constraint, and JSON Schema has no
# standard mechanism for it. Both vectors below fail for exactly this reason
# — the referenced axis is simply absent from `axes` — and nothing else.
_ND_SYSTEM_SCHEMA_INEXPRESSIBLE = frozenset({
    "invalid-binding-rule-unknown-axis",
    "invalid-allowed-axes-bare-string-but-unknown-axis",
})

# §9's P3: the EXPLICIT §9 field-type table
# (spec/SPEC.md §9, "The NDSystem document"): id/namespace/version now
# have an EXACT declared type (string-only for the first two; string or
# number, never bool/null/array/object, for version) instead of the
# earlier "no `| scalar | null` annotation" inference — and
# src/five_d_nd/contract.py now REJECTS a non-string id/namespace and a
# bool/null/array/object version OUTRIGHT, so those 5 cases MOVED to
# _ND_SYSTEM_VERSUM_P2_MALFORMED above
# (code now agrees with the schema; only versum remains more lenient) —
# they are NO LONGER listed here. What remains here is the strictness
# that is STILL schema-only (code AND versum both still accept these; the
# schema alone is stricter, per the design's explicit "vocabulary" type:
# "a JSON scalar, an array of JSON scalars (string/number/boolean), or
# null" — a null/array/object ITEM inside the array, or an object
# vocabulary itself, are all malformed per that same explicit decision).
_ND_SYSTEM_SCHEMA_INTENTIONALLY_STRICTER = frozenset({
    "valid-vocabulary-empty-object-coerced-nonempty-tuple",
    "valid-vocabulary-null-item-malformed-despite-versum-accepting",
    "valid-vocabulary-nested-array-item-malformed-despite-versum-accepting",
})


@_jsonschema_required
@pytest.mark.parametrize("path", _load("nd-system"), ids=lambda p: p.stem)
def test_every_nd_system_vector_schema_matches_code(path):
    """Code and schema should agree on EVERY nd-system vector except: the two
    individually-documented axis-cross-reference cases above, which no JSON
    Schema can express; and the odd-value cases below, where the schema is
    DELIBERATELY stricter than versum/the code.
    """
    v = _case(path)
    if path.stem in _ND_SYSTEM_SCHEMA_INEXPRESSIBLE:
        pytest.skip("allowed_axes -> declared axes is a cross-reference a JSON "
                    "Schema cannot express generically (code-only)")
    schema = _schema("nd-system.schema.json")
    schema_errors = _schema_errors(schema, v["input"]["doc"])
    schema_says_valid = not schema_errors
    code_says_valid = contract.is_valid_nd_system(v["input"]["doc"])
    if path.stem in _ND_SYSTEM_SCHEMA_INTENTIONALLY_STRICTER:
        # Assert the EXACT three-way verdict instead of
        # skipping, so an accidental schema relaxation (the schema starting
        # to accept one of these odd values again) fails this test rather
        # than passing silently. The schema is DELIBERATELY stricter than
        # versum/the code here: schema invalid, code
        # valid, and — when versum is importable — versum ALSO valid.
        assert not schema_says_valid, (
            v["case"], "expected schema to REJECT this intentionally-stricter "
            "case, but it validated")
        assert code_says_valid is True, (v["case"], "expected code to accept this")
        if _VERSUM_AVAILABLE:
            assert _versum_nd_system_valid(v["input"]["doc"]) is True, (
                v["case"], "expected versum to accept this")
        return
    assert schema_says_valid == code_says_valid == v["expected"]["valid"], (
        v["case"], "schema", schema_says_valid, "code", code_says_valid,
        "expected", v["expected"]["valid"], [e.message for e in schema_errors])


@_jsonschema_required
@pytest.mark.parametrize("path", _load("is-ought"), ids=lambda p: p.stem)
def test_every_is_ought_link_vector_schema_matches_code(path):
    v = _case(path)
    kind = v["input"]["kind"]
    if kind not in ("embeds_link", "link"):
        pytest.skip(f"kind {kind!r} has no link.schema.json equivalent")
    schema = _schema("link.schema.json")
    schema_errors = _schema_errors(schema, v["input"]["link"])
    schema_says_valid = not schema_errors
    code_says_valid = (
        contract.embeds_link_violations(v["input"]["link"]) == []
        if kind == "embeds_link" else
        contract.link_violations(v["input"]["link"]) == []
    )
    assert schema_says_valid == code_says_valid == v["expected"]["valid"], (
        v["case"], "schema", schema_says_valid, "code", code_says_valid,
        "expected", v["expected"]["valid"], [e.message for e in schema_errors])
