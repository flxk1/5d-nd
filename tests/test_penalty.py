# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""Conformance vector runner + behavioural tests for
``five_d_nd.grammars.penalty`` — SELF-CONTAINED, deliberately not merged
into ``tests/test_conformance.py``: that file's own ``FAMILIES``/``_load``
machinery is kept for the pre-existing families (mirrors
``tests/test_interplay.py``'s own identical choice). Every vector under
``conformance/vectors/penalty-grammar/*.json`` is loaded and dispatched by
its own ``kind`` field (see the dispatch table in
:func:`test_penalty_vector`).

Also asserts §10-style determinism directly (the same input gives
byte-identical output) and runs the ten real statute articles this
grammar was built against as an explicit, named regression, plus a
dedicated edge-identity check (one edge per infringed provision, no two
distinct clauses sharing an `o`).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from five_d_nd.grammars import penalty as pen

ROOT = Path(__file__).resolve().parents[1]
VECTORS_DIR = ROOT / "conformance" / "vectors" / "penalty-grammar"

MINIMUM_VECTORS = 30


def _load() -> list:
    return sorted(VECTORS_DIR.glob("*.json"))


def _case(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_penalty_grammar_meets_minimum_vector_count():
    n = len(_load())
    assert n >= MINIMUM_VECTORS, f"penalty-grammar has {n} vectors, needs >= {MINIMUM_VECTORS}"


@pytest.mark.parametrize("path", _load(), ids=lambda p: p.stem)
def test_penalty_vector(path):
    v = _case(path)
    assert v["family"] == "penalty-grammar"
    kind = v["kind"]
    inp = v["input"]
    expected = v["expected"]

    if kind == "find_penalties":
        ruleset = inp.get("ruleset")
        actual = pen.find_penalties(inp["articles"], ruleset=ruleset)
        assert actual == expected["records"]

    elif kind == "find_penalties_rejected":
        assert expected["raises"] == "ValueError"
        ruleset = inp.get("ruleset")
        with pytest.raises(ValueError):
            pen.find_penalties(inp["articles"], ruleset=ruleset)

    elif kind == "ruleset_shape":
        actual = pen.ruleset_violations(inp["doc"])
        assert actual == expected["violations"]

    elif kind == "authority_shape":
        actual = pen.authority_penalty_violations(inp["doc"])
        assert actual == expected["violations"]

    elif kind == "triples":
        if expected["triples"] and expected["triples"][0]["provenance"].get("basis") == "authority":
            actual = pen.authority_penalty_to_triples(inp["record"])
        else:
            actual = pen.penalty_to_triples(inp["record"])
        assert actual == expected["triples"]

    elif kind == "triples_rejected":
        assert expected["raises"] == "ValueError"
        with pytest.raises(ValueError):
            pen.penalty_to_triples(inp["record"])

    elif kind == "penalty_vocabulary":
        assert pen.PENALTY_KINDS == expected["kinds"]

    elif kind == "nd_system_shape":
        assert pen.build_nd_system() == expected["doc"]

    elif kind == "descriptor_shape":
        assert pen.build_descriptor() == expected["doc"]

    else:
        pytest.fail(f"unknown vector kind {kind!r} in {path.name}")


# ── determinism (§10) ────────────────────────────────────────────────────────

def test_find_penalties_is_deterministic_byte_for_byte():
    articles = [
        {"instrument_id": "gdpr", "article_id": "gdpr:Art.83",
         "text": "4. Infringements of the following provisions shall, in accordance with "
                 "paragraph 2, be subject to administrative fines up to 10 000 000 EUR, or in "
                 "the case of an undertaking, up to 2 % of the total worldwide annual turnover "
                 "of the preceding financial year, whichever is higher: (a) the obligations of "
                 "the controller and the processor pursuant to Articles 8, 11, 25 to 39 and 42 "
                 "and 43."},
        {"instrument_id": "nis2", "article_id": "nis2:Art.34",
         "text": "4. Member States shall ensure that where they infringe Article 21 or 23, "
                 "essential entities are subject, in accordance with paragraphs 2 and 3 of this "
                 "Article, to administrative fines of a maximum of at least EUR 10 000 000 or of "
                 "a maximum of at least 2 % of the total worldwide annual turnover in the "
                 "preceding financial year of the undertaking to which the essential entity "
                 "belongs, whichever is higher."},
    ]
    first = pen.find_penalties(articles)
    second = pen.find_penalties(articles)
    assert first == second
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_find_penalties_rejects_malformed_ruleset_before_scanning():
    bad = json.loads(json.dumps(pen.load_ruleset()))
    bad["cues"][0]["penalty_kind"] = "not_a_real_kind"
    with pytest.raises(ValueError):
        pen.find_penalties([{"instrument_id": "gdpr", "article_id": "gdpr:Art.1", "text": "x"}],
                            ruleset=bad)


def test_find_penalties_rejects_malformed_article():
    with pytest.raises(ValueError):
        pen.find_penalties([{"instrument_id": "gdpr", "text": "x"}])  # missing article_id


# ── all four penalty kinds bind the SAME, single 5D dimension ──────────────

def test_every_penalty_kind_binds_the_same_known_dimension():
    from five_d_nd.position import DIMENSIONS
    assert set(pen.PENALTY_KINDS) == {
        "administrative_fine", "periodic_penalty_payment", "penalty", "criminal_sanction",
    }
    assert pen.EDGE_DIMENSION in DIMENSIONS
    descriptor = pen.build_descriptor()
    assert set(descriptor["binding"].values()) == {pen.EDGE_DIMENSION}


# ── the real statute articles this grammar was built against ───────────────

_STATUTE_CASES = [
    ("statute-gdpr-art83-administrative-fines", "administrative_fine"),
    ("statute-gdpr-art84-penalties", "penalty"),
    ("statute-ai-act-art99-penalties", "administrative_fine"),
    ("statute-ai-act-art100-fines-union-institutions", "administrative_fine"),
    ("statute-ai-act-art101-fines-gpai-providers", "administrative_fine"),
    ("statute-dsa-art52-penalties", "administrative_fine"),
    ("statute-dsa-art74-fines", "administrative_fine"),
    ("statute-dsa-art76-periodic-penalty-payments", "periodic_penalty_payment"),
    ("statute-nis2-art34-administrative-fines", "administrative_fine"),
    ("statute-nis2-art36-penalties", "penalty"),
]


@pytest.mark.parametrize("case,dominant_kind", _STATUTE_CASES, ids=[c for c, _ in _STATUTE_CASES])
def test_statute_article_yields_expected_penalty_records(case, dominant_kind):
    v = _case(VECTORS_DIR / f"{case}.json")
    records = pen.find_penalties(v["input"]["articles"])
    assert records, case
    assert any(r["penalty_kind"] == dominant_kind for r in records), (
        f"{case}: expected at least one {dominant_kind!r} record, got {records!r}"
    )


def test_statute_records_round_trip_into_well_formed_triples():
    """Every resolved record from the real statute vectors converts into
    shape-valid §11 triples (dimension `causal`), one per infringed
    provision (after range expansion)."""
    from five_d_nd.triple import is_valid_triple

    for case, _ in _STATUTE_CASES:
        v = _case(VECTORS_DIR / f"{case}.json")
        records = pen.find_penalties(v["input"]["articles"])
        for r in records:
            if r["unresolved"]:
                continue
            triples = pen.penalty_to_triples(r)
            for t in triples:
                assert is_valid_triple(t), (case, r, t)
                assert t["dimension"] == "causal"


def test_no_two_distinct_clauses_share_an_edge_subject_node():
    """GDPR Art. 83(4)/(5)/(6), AI Act Art. 100(2)/(3), and NIS2 Art.
    34(4)/(5) must each resolve to a distinct `o` node — the edge id is
    built per penalty CLAUSE, never merely per article (see
    `_penalty_node_id`'s own docstring)."""
    all_articles = []
    for case, _ in _STATUTE_CASES:
        v = _case(VECTORS_DIR / f"{case}.json")
        all_articles.extend(v["input"]["articles"])
    records = pen.find_penalties(all_articles)
    o_to_clauses = {}
    for r in records:
        for t in pen.penalty_to_triples(r):
            clause_key = (r["source_instrument"], r["source_article"], r.get("paragraph"))
            o_to_clauses.setdefault(t["o"], set()).add(clause_key)
    collisions = {o: clauses for o, clauses in o_to_clauses.items() if len(clauses) > 1}
    assert collisions == {}, f"two distinct clauses share an edge subject node: {collisions!r}"


def test_excluded_provisions_never_also_appear_as_infringed():
    """A provision named by an 'other than'/'except'/'excluding' carve-out
    must never ALSO surface in the same record's own infringed_provisions
    — reading an exclusion as an infringement would reverse the clause's
    own meaning."""
    all_articles = []
    for case, _ in _STATUTE_CASES:
        v = _case(VECTORS_DIR / f"{case}.json")
        all_articles.extend(v["input"]["articles"])
    records = pen.find_penalties(all_articles)
    for r in records:
        overlap = set(r["infringed_provisions"]) & set(r["excluded_provisions"])
        assert not overlap, (r["source_article"], r.get("paragraph"), overlap)
