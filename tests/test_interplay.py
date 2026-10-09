# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""Conformance vector runner + behavioural tests for
``five_d_nd.grammars.interplay`` — SELF-CONTAINED, deliberately not merged
into ``tests/test_conformance.py``: that file's own ``FAMILIES``/``_load``
machinery is kept for the pre-existing families. Every vector under
``conformance/vectors/interplay-grammar/*.json`` is loaded and dispatched by
its own ``kind`` field (see the dispatch table in
:func:`test_interplay_vector`).

Also asserts §10-style determinism directly (the same input gives
byte-identical output) and runs the nine statute clauses named in the
grammar's own "Why" (see ``interplay.py``'s module docstring) as an
explicit, named regression (not merely via the generic vector loader), so a
reviewer can see each one pass without cross-referencing the vectors
directory.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from five_d_nd.grammars import interplay as ip

ROOT = Path(__file__).resolve().parents[1]
VECTORS_DIR = ROOT / "conformance" / "vectors" / "interplay-grammar"

MINIMUM_VECTORS = 40


def _load() -> list:
    return sorted(VECTORS_DIR.glob("*.json"))


def _case(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_interplay_grammar_meets_minimum_vector_count():
    n = len(_load())
    assert n >= MINIMUM_VECTORS, f"interplay-grammar has {n} vectors, needs >= {MINIMUM_VECTORS}"


@pytest.mark.parametrize("path", _load(), ids=lambda p: p.stem)
def test_interplay_vector(path):
    v = _case(path)
    assert v["family"] == "interplay-grammar"
    kind = v["kind"]
    inp = v["input"]
    expected = v["expected"]

    if kind == "find_relations":
        actual = ip.find_relations(inp["articles"])
        assert actual == expected["records"]

    elif kind == "citations":
        actual = [list(t) for t in ip.find_citations(inp["text"])]
        expected_citations = [list(t) for t in expected["citations"]]
        assert actual == expected_citations

    elif kind == "ruleset_shape":
        actual = ip.ruleset_violations(inp["doc"])
        assert actual == expected["violations"]

    elif kind == "authority_shape":
        actual = ip.authority_relation_violations(inp["doc"])
        assert actual == expected["violations"]

    elif kind == "triple":
        if expected["triple"]["provenance"].get("basis") == "authority":
            actual = ip.authority_relation_to_triple(inp["record"])
        else:
            actual = ip.relation_to_triple(inp["record"])
        assert actual == expected["triple"]

    elif kind == "triple_rejected":
        assert expected["raises"] == "ValueError"
        with pytest.raises(ValueError):
            ip.relation_to_triple(inp["record"])

    elif kind == "relation_vocabulary":
        assert ip.RELATIONS == expected["relations"]

    elif kind == "nd_system_shape":
        assert ip.build_nd_system() == expected["doc"]

    elif kind == "descriptor_shape":
        assert ip.build_descriptor() == expected["doc"]

    else:
        pytest.fail(f"unknown vector kind {kind!r} in {path.name}")


# ── determinism (§10) ────────────────────────────────────────────────────────

def test_find_relations_is_deterministic_byte_for_byte():
    articles = [
        {"instrument_id": "gdpr", "article_id": "gdpr:Art.95",
         "text": "This Regulation shall not impose additional obligations on natural or "
                 "legal persons in relation to processing for which they are subject to "
                 "specific obligations with the same objective set out in Directive "
                 "2002/58/EC."},
        {"instrument_id": "nis2", "article_id": "nis2:Art.35(2)",
         "text": "An authority shall not impose an administrative fine for the same "
                 "conduct as that which was the subject of a fine under Article 83 of "
                 "Regulation (EU) 2016/679."},
    ]
    first = ip.find_relations(articles)
    second = ip.find_relations(articles)
    assert first == second
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_find_relations_rejects_malformed_ruleset_before_scanning():
    bad = json.loads(json.dumps(ip.load_ruleset()))
    bad["cues"][0]["relation"] = "not_a_real_relation"
    with pytest.raises(ValueError):
        ip.find_relations([{"instrument_id": "gdpr", "article_id": "gdpr:Art.1", "text": "x"}],
                           ruleset=bad)


def test_find_relations_rejects_malformed_article():
    with pytest.raises(ValueError):
        ip.find_relations([{"instrument_id": "gdpr", "text": "x"}])  # missing article_id


# ── all ten relations have a defined 5D projection ──────────────────────────

def test_every_relation_binds_exactly_one_known_dimension():
    from five_d_nd.position import DIMENSIONS
    assert set(ip.RELATIONS) == {
        "same_definition", "cumulative", "complementary", "alternative",
        "substitutive", "separate_tracks", "non_cumulative", "no_presumption",
        "defers_to", "reference_redirect",
    }
    for relation_id, spec in ip.RELATIONS.items():
        assert spec["dimension"] in DIMENSIONS, relation_id
        assert isinstance(spec["meaning"], str) and spec["meaning"]
        assert isinstance(spec["reason"], str) and spec["reason"]


# ── the nine statute clauses from the grammar's own "Why" ──────────────────

_STATUTE_CASES = [
    ("statute-gdpr-art95-no-additional-obligations", "non_cumulative", "eprivacy"),
    ("statute-gdpr-art94-2-repealed-directive-redirect", "reference_redirect", "dpd95"),
    ("statute-dsa-art2-4g-without-prejudice", "defers_to", {"gdpr", "eprivacy"}),
    ("statute-dsa-art89-2-citation-redirect", "reference_redirect", "ecommerce"),
    ("statute-ai-act-art2-5-shall-not-affect", "defers_to", "dsa"),
    ("statute-ai-act-art2-7-shall-not-affect", "defers_to", {"gdpr", "eprivacy"}),
    ("statute-nis2-art35-2-no-fine-same-conduct", "non_cumulative", "gdpr"),
    ("statute-nis2-art35-1-inform-supervisory-authorities", "separate_tracks", "gdpr"),
    ("statute-nis2-art2-14-in-accordance-with-gdpr", "defers_to", "gdpr"),
]


@pytest.mark.parametrize("case,relation,target", _STATUTE_CASES, ids=[c for c, _, _ in _STATUTE_CASES])
def test_statute_clause_yields_defensible_relation(case, relation, target):
    v = _case(VECTORS_DIR / f"{case}.json")
    records = ip.find_relations(v["input"]["articles"])
    matching = [r for r in records if r["relation"] == relation]
    assert matching, f"{case}: expected at least one {relation!r} record, got {records!r}"
    targets_found = {r["target_instrument"] for r in matching if r["target_instrument"] is not None}
    expected_targets = target if isinstance(target, set) else {target}
    assert targets_found & expected_targets, (
        f"{case}: expected target(s) {expected_targets!r} among {matching!r}"
    )
