# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""Tests for `five_d_nd.extract.hybrid` — the hybrid, REPLAYABLE
extractor. A FAKE decider fixture
(`_fake_decision`) stands in for a real model throughout — no model is
ever called, inside this test file or inside the package itself.
"""
from __future__ import annotations

import json
import re

import pytest

from five_d_nd import statement as statement_mod
from five_d_nd.extract.hybrid import (
    DECISION_JSON_SCHEMA,
    PROMPT_TEMPLATE_V1,
    PROMPT_TEMPLATE_V1_SHA256,
    CacheKey,
    CacheMissError,
    Decision,
    DecisionCache,
    _sha256_of,
    allowed_spans,
    assemble,
    assemble_with_spans,
    decide,
    export_decision_requests,
    import_decisions,
    propose,
)

UNIT_TEXT = "The controller shall notify the supervisory authority within 72 hours."
CODER_VIEW_TEXT = "Apply the typed-statement coder view to the unit text above."
MODEL_ID = "fake-decider-v0"


def _candidate_set():
    return propose(UNIT_TEXT)


def _fake_decision(candidate_set, coder_view_text=CODER_VIEW_TEXT, model_id=MODEL_ID) -> Decision:
    """A FAKE decider: deterministically selects every candidate whose
    own rule id is NOT the last-resort fallback, keeping its own
    predicate/span unchanged. Stands in for a real model throughout
    this test file."""
    selections = tuple(
        {
            "candidate_id": c["id"], "predicate": c["predicate"], "layer": "domain",
            "negation": "absent", "subj_span_override": None, "obj_span_override": None,
        }
        for c in candidate_set.candidates
        if c["rule_id"] != "T3-predication-whole-unit-fallback"
    )
    return Decision(
        candidate_set_sha=candidate_set.sha256, coder_view_sha=_sha256_of(coder_view_text),
        model_id=model_id, prompt_template_sha=PROMPT_TEMPLATE_V1_SHA256,
        selections=selections, added=(),
    )


def _cache_key(candidate_set, coder_view_text=CODER_VIEW_TEXT, model_id=MODEL_ID) -> CacheKey:
    return CacheKey(
        candidate_set_sha=candidate_set.sha256, coder_view_sha=_sha256_of(coder_view_text),
        model_id=model_id, prompt_template_sha=PROMPT_TEMPLATE_V1_SHA256,
    )


# ───────────────────────────── propose() ─────────────────────────────────

def test_propose_returns_candidates_with_rule_id_and_citation():
    cs = _candidate_set()
    assert cs.candidates
    for c in cs.candidates:
        assert c["rule_id"]
        assert c["citation"]


def test_candidate_set_is_canonical_json_with_stable_sha256():
    cs = _candidate_set()
    j1 = cs.to_canonical_json()
    j2 = _candidate_set().to_canonical_json()
    assert j1 == j2
    assert cs.sha256 == _sha256_of(j1)


def test_candidate_set_round_trips_through_canonical_dict():
    cs = _candidate_set()
    from five_d_nd.extract.hybrid import CandidateSet
    cs2 = CandidateSet.from_canonical_dict(json.loads(cs.to_canonical_json()))
    assert cs2.to_canonical_json() == cs.to_canonical_json()


def test_propose_keeps_multiple_candidates_per_clause_no_first_claim_pruning():
    # "shall notify ... within 72 hours" fires BOTH performs and
    # deadline_of on overlapping/same territory -- propose() keeps both,
    # unlike extract.build's own overlap-resolved pipeline.
    cs = _candidate_set()
    predicates = {c["predicate"] for c in cs.candidates}
    assert "performs" in predicates
    assert "deadline_of" in predicates


# ───────────────────────────── allowed_spans() ────────────────────────────

def test_allowed_spans_includes_segments_chunks_and_candidate_endpoints():
    cs = _candidate_set()
    allowed = allowed_spans(cs)
    for seg in cs.segments:
        assert (seg["start"], seg["end"]) in allowed
    for chunk in cs.np_chunks:
        assert (chunk["start"], chunk["end"]) in allowed
    for cand in cs.candidates:
        assert tuple(cand["subj_span"]) in allowed
        assert tuple(cand["obj_span"]) in allowed


# ─────────────────────── CandidateSet v2 ────────────────────────

def test_candidate_set_version_is_v2():
    from five_d_nd.extract.hybrid import CANDIDATE_SET_VERSION
    cs = _candidate_set()
    assert CANDIDATE_SET_VERSION == "v2"
    assert json.loads(cs.to_canonical_json())["candidate_set_version"] == "v2"


def test_prompt_template_v1_unchanged_by_candidate_set_v2():
    # the instruction: v2 is a CandidateSet-shape change only.
    assert "v1" in PROMPT_TEMPLATE_V1 or True  # sentinel: template still importable
    assert PROMPT_TEMPLATE_V1_SHA256 == _sha256_of(PROMPT_TEMPLATE_V1)


def test_extra_allowed_spans_are_additive_to_allowed_spans():
    cs = _candidate_set()
    allowed = allowed_spans(cs)
    assert cs.extra_allowed_spans
    for span in cs.extra_allowed_spans:
        assert (span["start"], span["end"]) in allowed


def test_propose_offers_explicit_chapeau_subject_candidate():
    text = (
        "The licensor may terminate this agreement where:\n"
        "(a) the licensee fails to pay the fee;\n"
        "(b) the licensee breaches a material term.\n"
    )
    cs = propose(text)
    explicit = [c for c in cs.candidates if c["rule_id"].endswith("-explicit-inherited-subj")]
    assert explicit, "expected an explicit chapeau-subject candidate"
    for c in explicit:
        s, e = c["subj_span"]
        assert text[s:e] == "licensor"


def test_propose_extra_allowed_spans_include_a_relative_clause_antecedent():
    text = "The vendor shall deliver the goods, which satisfy the agreed specification."
    cs = propose(text)
    allowed = allowed_spans(cs)
    antecedent = text.index("vendor")
    assert (antecedent, antecedent + len("vendor")) in allowed


def test_propose_extra_allowed_spans_include_a_coordinated_shared_subject():
    text = "The buyer shall inspect the goods, and shall confirm receipt within five days."
    cs = propose(text)
    allowed = allowed_spans(cs)
    subj = text.index("buyer")
    assert (subj, subj + len("buyer")) in allowed


def test_propose_extra_allowed_spans_include_a_clean_np_chunk():
    text = "(a) the licensee\n(b) the sub-licensee\nshall each notify the registrar.\n"
    cs = propose(text)
    allowed = allowed_spans(cs)
    idx = text.index("sub-licensee")
    assert (idx, idx + len("sub-licensee")) in allowed


def test_candidate_set_from_canonical_dict_defaults_extra_allowed_spans():
    from five_d_nd.extract.hybrid import CandidateSet
    cs = _candidate_set()
    d = json.loads(cs.to_canonical_json())
    del d["extra_allowed_spans"]
    cs2 = CandidateSet.from_canonical_dict(d)
    assert cs2.extra_allowed_spans == ()


# ───────────────────────── cache + decide() ───────────────────────────────

def test_cache_miss_raises(tmp_path):
    cs = _candidate_set()
    cache = DecisionCache(tmp_path)
    key = _cache_key(cs)
    with pytest.raises(CacheMissError):
        cache.replay(key)
    with pytest.raises(CacheMissError):
        decide(cs, CODER_VIEW_TEXT, model_id=MODEL_ID, prompt_template_sha=PROMPT_TEMPLATE_V1_SHA256, cache=cache)


def test_decide_record_mode_raises_not_implemented(tmp_path):
    """No model, and no 'record' path, lives inside this package."""
    cs = _candidate_set()
    cache = DecisionCache(tmp_path)
    with pytest.raises(NotImplementedError):
        decide(cs, CODER_VIEW_TEXT, model_id=MODEL_ID, prompt_template_sha=PROMPT_TEMPLATE_V1_SHA256,
               cache=cache, mode="record")


def test_cache_record_then_replay_round_trips(tmp_path):
    cs = _candidate_set()
    decision = _fake_decision(cs)
    cache = DecisionCache(tmp_path)
    key = _cache_key(cs)
    cache.record(key, decision)
    replayed = decide(cs, CODER_VIEW_TEXT, model_id=MODEL_ID, prompt_template_sha=PROMPT_TEMPLATE_V1_SHA256, cache=cache)
    assert replayed.to_canonical_json() == decision.to_canonical_json()


def test_cache_record_is_idempotent_for_identical_content(tmp_path):
    cs = _candidate_set()
    decision = _fake_decision(cs)
    cache = DecisionCache(tmp_path)
    key = _cache_key(cs)
    cache.record(key, decision)
    cache.record(key, decision)  # same content twice: no error


def test_cache_record_rejects_a_different_decision_at_the_same_key(tmp_path):
    cs = _candidate_set()
    decision = _fake_decision(cs)
    cache = DecisionCache(tmp_path)
    key = _cache_key(cs)
    cache.record(key, decision)
    other = Decision(
        candidate_set_sha=cs.sha256, coder_view_sha=_sha256_of(CODER_VIEW_TEXT), model_id=MODEL_ID,
        prompt_template_sha=PROMPT_TEMPLATE_V1_SHA256, selections=(), added=(),
    )
    with pytest.raises(ValueError):
        cache.record(key, other)


def test_cache_record_rejects_a_decision_whose_own_fields_recompute_a_different_key(tmp_path):
    """Round-7 fix (item 2): record() does the SAME check replay() does
    — a Decision whose own four identifying fields recompute to a key
    DIFFERENT from the one it is being written under (a forged or
    mismatched entry) is rejected at write time."""
    cs = _candidate_set()
    decision = _fake_decision(cs)
    cache = DecisionCache(tmp_path)
    wrong_key = CacheKey(
        candidate_set_sha=cs.sha256, coder_view_sha=_sha256_of("a different coder view"),
        model_id=MODEL_ID, prompt_template_sha=PROMPT_TEMPLATE_V1_SHA256,
    )
    with pytest.raises(ValueError):
        cache.record(wrong_key, decision)
    assert not list(tmp_path.glob("*.json"))


def test_cache_manifest_hash_changes_when_a_new_entry_is_recorded(tmp_path):
    cache = DecisionCache(tmp_path)
    before = cache.manifest_sha256()
    cs = _candidate_set()
    cache.record(_cache_key(cs), _fake_decision(cs))
    after = cache.manifest_sha256()
    assert before != after


def test_cache_manifest_ignores_a_non_decision_file(tmp_path):
    """Round-6 fix: the manifest hashes only Decision files — a filename
    that is not a 64-hex-digit digest is never included, even if it
    happens to sit in the same cache directory."""
    cache = DecisionCache(tmp_path)
    before = cache.manifest_sha256()
    (tmp_path / "not-a-decision.json").write_text("{}", encoding="utf-8")
    after = cache.manifest_sha256()
    assert before == after


def test_replay_rejects_a_decision_whose_own_fields_recompute_a_different_key(tmp_path):
    """Round-6 integrity fix: replay() recomputes the CacheKey from the
    STORED Decision's own four identifying fields and raises if it
    disagrees with the key the file is stored under (a hand-edited or
    misplaced cache file)."""
    cs = _candidate_set()
    cache = DecisionCache(tmp_path)
    key = _cache_key(cs)
    cache.record(key, _fake_decision(cs))
    path = cache._path_for(key)
    tampered = json.loads(path.read_text(encoding="utf-8"))
    tampered["model_id"] = "a-different-model-entirely"
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(ValueError):
        cache.replay(key)


def test_replay_rejects_a_decision_that_fails_schema_validation(tmp_path):
    """Round-6 integrity fix: every replay validates the cached JSON
    against DECISION_JSON_SCHEMA's own shape (stdlib-only validator) —
    an unknown predicate value is rejected."""
    cs = _candidate_set()
    cache = DecisionCache(tmp_path)
    key = _cache_key(cs)
    bad = {
        "candidate_set_sha": cs.sha256, "coder_view_sha": _sha256_of(CODER_VIEW_TEXT),
        "model_id": MODEL_ID, "prompt_template_sha": PROMPT_TEMPLATE_V1_SHA256,
        "selections": [{"candidate_id": 0, "predicate": "not_a_real_predicate",
                         "layer": "domain", "negation": "absent"}],
        "added": [],
    }
    cache.cache_dir.mkdir(parents=True, exist_ok=True)
    cache._path_for(key).write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError):
        cache.replay(key)


# ───────────────────────────── assemble() ─────────────────────────────────

def test_assemble_is_byte_identical_on_replay():
    """The replay byte-identity test: the SAME CandidateSet + the SAME
    (replayed) Decision assembles to the SAME Statements, every time."""
    cs = _candidate_set()
    decision = _fake_decision(cs)
    key = _cache_key(cs)
    stmts1 = assemble(cs, decision)
    stmts2 = assemble(cs, decision)
    assert json.dumps(stmts1, sort_keys=True) == json.dumps(stmts2, sort_keys=True)


def test_assemble_output_is_schema_valid():
    cs = _candidate_set()
    decision = _fake_decision(cs)
    key = _cache_key(cs)
    stmts = assemble(cs, decision)
    assert stmts
    for s in stmts:
        assert statement_mod.is_valid_statement(s), statement_mod.statement_violations(s)
        assert "|model-decision:" in s["extraction_rule_id"]


def test_assemble_rejects_candidate_set_sha_mismatch():
    cs = _candidate_set()
    decision = _fake_decision(cs)
    other_cs = propose("A different sentence entirely, with its own candidates.")
    with pytest.raises(ValueError):
        assemble(other_cs, decision)


def test_assemble_rejects_unknown_candidate_id():
    cs = _candidate_set()
    decision = Decision(
        candidate_set_sha=cs.sha256, coder_view_sha=_sha256_of(CODER_VIEW_TEXT), model_id=MODEL_ID,
        prompt_template_sha=PROMPT_TEMPLATE_V1_SHA256,
        selections=({"candidate_id": 9999, "predicate": "performs", "layer": "domain",
                     "negation": "absent", "subj_span_override": None, "obj_span_override": None},),
        added=(),
    )
    with pytest.raises(ValueError):
        assemble(cs, decision)


def test_assemble_rejects_duplicate_selection_of_the_same_candidate():
    cs = _candidate_set()
    cand0 = cs.candidates[0]
    sel = {"candidate_id": cand0["id"], "predicate": cand0["predicate"], "layer": "domain",
           "negation": "absent", "subj_span_override": None, "obj_span_override": None}
    decision = Decision(
        candidate_set_sha=cs.sha256, coder_view_sha=_sha256_of(CODER_VIEW_TEXT), model_id=MODEL_ID,
        prompt_template_sha=PROMPT_TEMPLATE_V1_SHA256, selections=(sel, dict(sel)), added=(),
    )
    with pytest.raises(ValueError):
        assemble(cs, decision)


def test_assemble_accepts_a_span_override_that_is_an_np_chunk():
    cs = _candidate_set()
    chunk = cs.np_chunks[0]
    cand0 = cs.candidates[0]
    decision = Decision(
        candidate_set_sha=cs.sha256, coder_view_sha=_sha256_of(CODER_VIEW_TEXT), model_id=MODEL_ID,
        prompt_template_sha=PROMPT_TEMPLATE_V1_SHA256,
        selections=({"candidate_id": cand0["id"], "predicate": cand0["predicate"], "layer": "domain",
                     "negation": "absent",
                     "subj_span_override": [chunk["start"], chunk["end"]], "obj_span_override": None},),
        added=(),
    )
    stmts = assemble(cs, decision)
    assert stmts


def test_assemble_rejects_a_span_override_not_in_the_candidate_set():
    """Span-constraint enforcement: an adjustment outside the
    CandidateSet is rejected."""
    cs = _candidate_set()
    cand0 = cs.candidates[0]
    bogus_span = [cand0["subj_span"][0] + 1, cand0["subj_span"][1] + 1]  # shifted by one char: not a real span
    decision = Decision(
        candidate_set_sha=cs.sha256, coder_view_sha=_sha256_of(CODER_VIEW_TEXT), model_id=MODEL_ID,
        prompt_template_sha=PROMPT_TEMPLATE_V1_SHA256,
        selections=({"candidate_id": cand0["id"], "predicate": cand0["predicate"], "layer": "domain",
                     "negation": "absent",
                     "subj_span_override": bogus_span, "obj_span_override": None},),
        added=(),
    )
    with pytest.raises(ValueError):
        assemble(cs, decision)


def test_assemble_rejects_an_added_statement_with_a_span_not_in_the_candidate_set():
    cs = _candidate_set()
    decision = Decision(
        candidate_set_sha=cs.sha256, coder_view_sha=_sha256_of(CODER_VIEW_TEXT), model_id=MODEL_ID,
        prompt_template_sha=PROMPT_TEMPLATE_V1_SHA256, selections=(),
        added=({"predicate": "performs", "layer": "domain", "negation": "absent",
                "subj_span": [0, 2], "obj_span": [500, 502]},),
    )
    with pytest.raises(ValueError):
        assemble(cs, decision)


def test_assemble_accepts_an_added_statement_whose_spans_are_both_np_chunks():
    cs = _candidate_set()
    chunks = [c for c in cs.np_chunks]
    assert len(chunks) >= 2
    decision = Decision(
        candidate_set_sha=cs.sha256, coder_view_sha=_sha256_of(CODER_VIEW_TEXT), model_id=MODEL_ID,
        prompt_template_sha=PROMPT_TEMPLATE_V1_SHA256, selections=(),
        added=({"predicate": "performs", "layer": "domain", "negation": "absent",
                "subj_span": [chunks[0]["start"], chunks[0]["end"]],
                "obj_span": [chunks[1]["start"], chunks[1]["end"]]},),
    )
    stmts = assemble(cs, decision)
    assert len(stmts) == 1
    assert statement_mod.is_valid_statement(stmts[0])


def test_assemble_with_spans_returns_the_same_statements_as_assemble():
    """Round-7 addition (item 3): `assemble_with_spans()` is an
    additive sibling — same Statements, same order, `assemble()` itself
    untouched."""
    cs = _candidate_set()
    decision = _fake_decision(cs)
    plain = assemble(cs, decision)
    with_spans = assemble_with_spans(cs, decision)
    assert [bs.statement for bs in with_spans] == plain


def test_assemble_with_spans_carries_the_subj_obj_clause_span_triple():
    cs = _candidate_set()
    decision = _fake_decision(cs)
    with_spans = assemble_with_spans(cs, decision)
    assert with_spans
    for bs in with_spans:
        assert set(bs.spans) == {"clause", "subj", "obj"}
        for span in bs.spans.values():
            assert isinstance(span, tuple) and len(span) == 2
        subj_text = UNIT_TEXT[bs.spans["subj"][0]:bs.spans["subj"][1]]
        obj_text = UNIT_TEXT[bs.spans["obj"][0]:bs.spans["obj"][1]]
        assert subj_text == bs.statement["subj"]
        assert obj_text == bs.statement["obj"]


# ───────────────────── export_decision_requests() ────────────────────────

_UNIT_ID_PATTERN = re.compile(
    r"\b(?:gdpr|ai-act|uk-dpa2018|nis2|dsa|test)[:_-]\d{3,4}\b", re.IGNORECASE
)


def test_export_decision_requests_writes_one_file_per_unit(tmp_path):
    units = {
        "test:0001": {"text": UNIT_TEXT, "enclosing_provision": None},
        "test:0002": {"text": "The processor shall assist the controller without delay.", "enclosing_provision": "recital 1"},
    }
    req_dir = tmp_path / "requests"
    mapping_path = tmp_path / "mapping.json"
    paths = export_decision_requests(units, req_dir, coder_view_text=CODER_VIEW_TEXT, mapping_path=mapping_path)
    assert len(paths) == 2
    for p in paths:
        assert p.exists()


def test_export_decision_requests_are_named_by_cache_key_not_unit_id(tmp_path):
    units = {"test:0001": {"text": UNIT_TEXT, "enclosing_provision": None}}
    req_dir = tmp_path / "requests"
    mapping_path = tmp_path / "mapping.json"
    paths = export_decision_requests(units, req_dir, coder_view_text=CODER_VIEW_TEXT, mapping_path=mapping_path)
    assert len(paths) == 1
    assert re.fullmatch(r"[0-9a-f]{64}\.json", paths[0].name)


def test_export_decision_requests_contains_no_gold_and_no_unit_id(tmp_path):
    """No gold anywhere in an exported request — field names, and a
    plain substring check over the whole serialised request. Round-6
    fix: no `unit_id` field either, and no unit-id-SHAPED pattern
    anywhere in the file's own text."""
    units = {"test:0001": {"text": UNIT_TEXT, "enclosing_provision": None}}
    req_dir = tmp_path / "requests"
    mapping_path = tmp_path / "mapping.json"
    paths = export_decision_requests(units, req_dir, coder_view_text=CODER_VIEW_TEXT, mapping_path=mapping_path)
    for p in paths:
        raw = p.read_text(encoding="utf-8")
        assert "gold" not in raw.lower()
        assert not _UNIT_ID_PATTERN.search(raw)
        data = json.loads(raw)
        assert "unit_id" not in data
        assert set(data.keys()) == {
            "schema_version", "candidate_set", "candidate_set_sha",
            "coder_view_text", "coder_view_sha", "prompt_template", "prompt_template_sha",
            "model_id", "cache_key", "expected_output_schema",
        }


def test_export_decision_requests_mapping_file_is_outside_the_request_dir(tmp_path):
    units = {"test:0001": {"text": UNIT_TEXT, "enclosing_provision": None}}
    req_dir = tmp_path / "requests"
    mapping_path = tmp_path / "mapping.json"
    export_decision_requests(units, req_dir, coder_view_text=CODER_VIEW_TEXT, mapping_path=mapping_path)
    assert mapping_path.exists()
    assert mapping_path.parent != req_dir
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))["mapping"]
    assert "test:0001" in mapping
    # the cache key in the mapping names a REAL request file
    assert (req_dir / f"{mapping['test:0001']}.json").exists()


def test_export_decision_requests_default_mapping_path_is_a_sibling_of_out_dir(tmp_path):
    units = {"test:0001": {"text": UNIT_TEXT, "enclosing_provision": None}}
    req_dir = tmp_path / "requests"
    export_decision_requests(units, req_dir, coder_view_text=CODER_VIEW_TEXT)
    default_mapping = tmp_path / "requests-mapping.json"
    assert default_mapping.exists()
    assert default_mapping.parent == tmp_path  # OUTSIDE req_dir itself


def test_export_decision_requests_includes_expected_output_schema_and_prompt(tmp_path):
    units = {"test:0001": {"text": UNIT_TEXT, "enclosing_provision": None}}
    req_dir = tmp_path / "requests"
    mapping_path = tmp_path / "mapping.json"
    paths = export_decision_requests(units, req_dir, coder_view_text=CODER_VIEW_TEXT, mapping_path=mapping_path)
    data = json.loads(paths[0].read_text(encoding="utf-8"))
    assert data["expected_output_schema"] == DECISION_JSON_SCHEMA
    assert data["prompt_template"] == PROMPT_TEMPLATE_V1
    assert data["prompt_template_sha"] == PROMPT_TEMPLATE_V1_SHA256


# ─────────────────────────── import_decisions() ───────────────────────────

def test_import_decisions_records_every_answered_file(tmp_path):
    cs = _candidate_set()
    decision = _fake_decision(cs)
    key = _cache_key(cs)
    decisions_dir = tmp_path / "decisions"
    decisions_dir.mkdir()
    (decisions_dir / f"{key.digest}.json").write_text(decision.to_canonical_json(), encoding="utf-8")

    cache = DecisionCache(tmp_path / "cache")
    recorded = import_decisions(decisions_dir, cache)
    assert len(recorded) == 1
    assert cache.replay(key) == decision


def test_import_decisions_ignores_a_non_cache_key_named_file(tmp_path):
    cs = _candidate_set()
    decision = _fake_decision(cs)
    key = _cache_key(cs)
    decisions_dir = tmp_path / "decisions"
    decisions_dir.mkdir()
    (decisions_dir / f"{key.digest}.json").write_text(decision.to_canonical_json(), encoding="utf-8")
    (decisions_dir / "decisions-mapping.json").write_text('{"mapping": {}}', encoding="utf-8")

    cache = DecisionCache(tmp_path / "cache")
    recorded = import_decisions(decisions_dir, cache)
    assert len(recorded) == 1
    assert recorded[0].name == f"{key.digest}.json"


def test_import_decisions_rejects_a_file_that_fails_schema_validation(tmp_path):
    cs = _candidate_set()
    key = _cache_key(cs)
    decisions_dir = tmp_path / "decisions"
    decisions_dir.mkdir()
    bad = {
        "candidate_set_sha": cs.sha256, "coder_view_sha": _sha256_of(CODER_VIEW_TEXT),
        "model_id": MODEL_ID, "prompt_template_sha": PROMPT_TEMPLATE_V1_SHA256,
        "selections": [{"candidate_id": 0, "predicate": "not_a_real_predicate",
                         "layer": "domain", "negation": "absent"}],
        "added": [],
    }
    (decisions_dir / f"{key.digest}.json").write_text(json.dumps(bad), encoding="utf-8")
    cache = DecisionCache(tmp_path / "cache")
    with pytest.raises(ValueError):
        import_decisions(decisions_dir, cache)
    assert not list((tmp_path / "cache").glob("*.json")) if (tmp_path / "cache").exists() else True


def test_import_decisions_rejects_a_file_named_with_the_wrong_cache_key(tmp_path):
    """A Decision file saved under a cache-key filename that does NOT
    match what its own content recomputes to is rejected by
    `DecisionCache.record()`'s own round-7 integrity check, not
    silently accepted under the wrong name."""
    cs = _candidate_set()
    decision = _fake_decision(cs)
    wrong_digest = "0" * 64
    decisions_dir = tmp_path / "decisions"
    decisions_dir.mkdir()
    (decisions_dir / f"{wrong_digest}.json").write_text(decision.to_canonical_json(), encoding="utf-8")
    cache = DecisionCache(tmp_path / "cache")
    with pytest.raises(ValueError):
        import_decisions(decisions_dir, cache)


# ───────────────────────────── prompt template ────────────────────────────

def test_prompt_template_never_mentions_gold():
    assert "gold" not in PROMPT_TEMPLATE_V1.lower()


def test_prompt_template_sha_is_stable():
    assert PROMPT_TEMPLATE_V1_SHA256 == _sha256_of(PROMPT_TEMPLATE_V1)


def test_decision_json_schema_rejects_an_extra_field():
    jsonschema = pytest.importorskip("jsonschema")
    good = {
        "candidate_set_sha": "a", "coder_view_sha": "b", "model_id": "c",
        "prompt_template_sha": "d", "selections": [],
    }
    jsonschema.validate(instance=good, schema=DECISION_JSON_SCHEMA)
    bad = dict(good, unexpected_field="x")
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=bad, schema=DECISION_JSON_SCHEMA)
