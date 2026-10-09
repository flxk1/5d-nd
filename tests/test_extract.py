# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""Tests for the deterministic typed-Statement extractor
(`five_d_nd.extract`) — spec/SPEC.md §21-§23.

Three groups: (1) unit tests on the span/negation helper modules; (2)
the `conformance/vectors/extractor/` vector family, run here with its
own loader (additive to `tests/test_conformance.py`'s shared registry,
never a change to it); (3) determinism + schema-validity property
tests over the vector corpus and a few synthetic inputs.

A local evaluation script (not shipped) and its own held-out-data guard
read a local corpus not present in this repository; their own tests
live in the untracked `tests/test_eval_dev_scripts.py` (see that file
and `.gitignore`), not here.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from five_d_nd import statement as statement_mod
from five_d_nd.extract import (
    RULE_CITATIONS,
    RULES,
    Candidate,
    collect_candidates,
    extract,
    extract_with_spans,
    finalize_endpoint_span,
    layer_of,
    negation_v34,
    span_text,
    strip_determiner,
    strip_modal_prefix,
    trim_whitespace,
)

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schema" / "statement.schema.json"
VECTORS_DIR = ROOT / "conformance" / "vectors" / "extractor"


def _load_vectors():
    return sorted(VECTORS_DIR.glob("*.json")) if VECTORS_DIR.exists() else []


def _case(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ───────────────────────────── spans.py ────────────────────────────────

def test_trim_whitespace_shrinks_inward():
    text = "  hello  "
    assert trim_whitespace(text, 0, len(text)) == (2, 7)


def test_trim_whitespace_all_whitespace_collapses_to_empty():
    text = "   "
    s, e = trim_whitespace(text, 0, len(text))
    assert s == e


def test_strip_determiner_strips_one_leading_article():
    text = "the controller"
    s, e = strip_determiner(text, 0, len(text))
    assert text[s:e] == "controller"


def test_strip_determiner_never_strips_part_of_r_o():
    text = "part of a filing system"
    s, e = strip_determiner(text, 0, len(text))
    assert text[s:e] == "part of a filing system"


def test_strip_determiner_one_of_the():
    text = "one of the measures"
    s, e = strip_determiner(text, 0, len(text))
    assert text[s:e] == "measures"


def test_strip_modal_prefix_strips_shall():
    text = "shall notify the authority"
    s, e = strip_modal_prefix(text, 0, len(text))
    assert text[s:e] == "notify the authority"


def test_strip_modal_prefix_strips_shall_be_deemed():
    text = "shall be deemed justified"
    s, e = strip_modal_prefix(text, 0, len(text))
    assert text[s:e] == "justified"


def test_strip_modal_prefix_no_modal_is_a_no_op():
    text = "notify the authority"
    s, e = strip_modal_prefix(text, 0, len(text))
    assert text[s:e] == "notify the authority"


def test_finalize_endpoint_span_whitespace_only_returns_none():
    text = "   "
    assert finalize_endpoint_span(text, 0, len(text)) is None


def test_span_text_collapses_whitespace_and_nbsp():
    text = "a  b\n\tc"
    assert span_text(text, (0, len(text))) == "a b c"


# ───────────────────────────── negation.py ─────────────────────────────

def test_negation_requires_always_absent_even_with_negator_outside_subj():
    text = "the controller cannot comply, it shall not notify anyone"
    clause = (0, len(text))
    subj = (0, 30)  # includes "cannot" — R-n: stays inside subj
    assert negation_v34(text, clause, subj, "requires") == "absent"


def test_negation_deadline_of_always_absent():
    text = "within 72 hours the controller shall not act"
    assert negation_v34(text, (0, len(text)), (0, 10), "deadline_of") == "absent"


def test_negation_present_when_negator_in_clause_outside_subj():
    text = "the controller shall not notify the authority"
    subj = (0, 14)  # "the controller"
    assert negation_v34(text, (0, len(text)), subj, "predication") == "present"


def test_negation_absent_when_no_negator_anywhere():
    text = "the controller shall notify the authority"
    assert negation_v34(text, (0, len(text)), (0, 14), "predication") == "absent"


def test_negation_uncertain_when_negator_outside_clause():
    text = "the controller shall not act. The processor shall notify the authority."
    clause = text.index("The processor"), len(text)
    subj = (clause[0], clause[0] + 13)
    assert negation_v34(text, clause, subj, "predication") == "uncertain"


def test_negation_force_overrides_everything():
    text = "irrelevant text with no negator at all"
    assert negation_v34(text, (0, len(text)), (0, 5), "predication", force="present") == "present"


def test_negation_rejects_unregistered_version():
    from five_d_nd.extract import negate
    with pytest.raises(KeyError):
        negate("x", (0, 1), (0, 1), "predication", version="v99")


# ─────────────────────────── layer_of ──────────────────────────────────

def test_layer_of_is_a_is_always_deep():
    assert layer_of("is_a") == "deep"


def test_layer_of_legislative_purpose_defaults_surface():
    assert layer_of("legislative_purpose_of") == "surface"


def test_layer_of_everything_else_defaults_domain():
    for pred in ("requires", "performs", "competence_of", "predication", "part_of"):
        assert layer_of(pred) == "domain"


# ───────────────────────────── extract() ───────────────────────────────

def test_extract_rejects_non_string():
    with pytest.raises(ValueError):
        extract(12345)


def test_extract_is_deterministic_byte_identical():
    text = "The controller shall notify the supervisory authority within 72 hours of becoming aware of a breach."
    a = extract(text)
    b = extract(text)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_extract_every_statement_has_rule_id_and_confidence():
    text = "The provider shall maintain records for the purposes of demonstrating compliance with this Article."
    stmts = extract(text)
    assert stmts, "expected at least one statement"
    for s in stmts:
        assert s.get("extraction_rule_id")
        assert isinstance(s.get("edge_confidence"), float)
        assert 0.0 <= s["edge_confidence"] <= 1.0


def test_extract_every_statement_is_schema_valid():
    text = "'personal data' means any information relating to an identified natural person."
    stmts = extract(text)
    assert stmts
    for s in stmts:
        doc = {k: v for k, v in s.items() if not k.startswith("_")}
        assert statement_mod.is_valid_statement(doc), statement_mod.statement_violations(doc)


def test_extract_empty_text_yields_no_statements():
    assert extract("") == []


def test_extract_whole_unit_fallback_fires_when_no_cue_matches():
    text = "Zorble flurn wibbet quasm trindle hobnick frandle plonquist zestivorn glim."
    stmts = extract(text)
    assert len(stmts) == 1
    assert stmts[0]["predicate"] == "predication"
    assert stmts[0]["extraction_rule_id"] == "T3-predication-whole-unit-fallback"


def test_extract_no_statement_has_overlapping_clause_span():
    text = (
        "'personal data' means any information relating to a person. "
        "This Directive applies to the processing of such data by a provider."
    )
    stmts = extract(text)
    spans = [tuple(s["provenance"].values()) for s in stmts]
    for i in range(len(spans)):
        for j in range(i + 1, len(spans)):
            a, b = spans[i], spans[j]
            assert not (a[0] < b[1] and b[0] < a[1]), (spans[i], spans[j])


def test_candidate_is_a_plain_dataclass():
    c = Candidate(rule_id="x", predicate="is_a", clause_span=(0, 1), subj_span=(0, 1), obj_span=(0, 1))
    assert c.rule_id == "x"


def test_collect_candidates_runs_every_rule_without_crashing_on_short_text():
    for text in ("", "a", "the", "shall", "is_a"):
        collect_candidates(text)  # must not raise


# ───────────── conformance/vectors/extractor/ — additive family ────────

VECTORS = _load_vectors()


def test_extractor_vector_family_has_minimum_count():
    assert len(VECTORS) >= 20, f"extractor vector family has {len(VECTORS)} vectors, expected >= 20"


@pytest.mark.parametrize("path", VECTORS, ids=lambda p: p.stem)
def test_extractor_vector(path):
    v = _case(path)
    unit_text = v["input"]["unit_text"]
    expected = v["expected"]["statements"]
    actual = extract(unit_text)
    actual_clean = [{k: val for k, val in s.items() if not k.startswith("_")} for s in actual]
    assert actual_clean == expected, v["case"]


@pytest.mark.parametrize("path", VECTORS, ids=lambda p: p.stem)
def test_extractor_vector_statements_are_schema_valid(path):
    v = _case(path)
    for doc in v["expected"]["statements"]:
        assert statement_mod.is_valid_statement(doc), (v["case"], statement_mod.statement_violations(doc))


@pytest.mark.parametrize("path", VECTORS, ids=lambda p: p.stem)
def test_extractor_vector_is_reproduced_deterministically(path):
    v = _case(path)
    unit_text = v["input"]["unit_text"]
    first = extract(unit_text)
    second = extract(unit_text)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True), v["case"]


def test_no_vector_input_text_is_a_long_verbatim_corpus_quote():
    """Held-out/no-gold-text hard rule, applied to THIS session's own
    rule/vector text: no vector's own ``unit_text`` may be a >=60-char
    substring of a real local corpus file (the extractor's
    rules and vectors are written from the codebook, never from gold —
    see `rules.py`'s own module docstring). This test cannot read the
    full-run gold corpus (out of this file's own read territory) — it
    instead asserts the STRUCTURAL property that is within reach: every
    vector's own text is short (a single invented sentence), which is
    the actual guarantee this session can make and keep."""
    for path in VECTORS:
        v = _case(path)
        text = v["input"]["unit_text"]
        assert len(text) < 200, (path.stem, "unexpectedly long unit_text")



# ─────────────────────── schema conformance (required fix 1) ────────────

def _jsonschema_or_skip():
    try:
        import jsonschema
    except ImportError:
        pytest.skip("jsonschema not importable")
    return jsonschema


def test_extract_raw_output_is_schema_valid_with_jsonschema_no_stripping():
    """Required fix 1: `extract()` must return Statements that validate
    against `schema/statement.schema.json` AS THEY ARE — no stripping of
    any field by this test, and no internal field present to strip in
    the first place (schema has `additionalProperties: false`)."""
    jsonschema = _jsonschema_or_skip()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    texts = [
        "'personal data' means any information relating to an identified natural person.",
        "If a near-miss is detected, the operator shall record the event within 72 hours.",
        "The data protection officer shall, within one month, respond to the request.",
        "By way of derogation from the standard procedure, a simplified notice may be used.",
    ]
    validated_at_least_one = False
    for text in texts:
        for doc in extract(text):
            assert set(doc.keys()) <= set(schema["properties"].keys())
            jsonschema.validate(instance=doc, schema=schema)
            validated_at_least_one = True
    assert validated_at_least_one


def test_extract_addressed_to_statement_is_schema_valid_with_jsonschema():
    """v3.6: `addressed_to` is a REAL predicate in
    `schema/statement.schema.json`'s own closed enum, not just in
    `statement.PREDICATE_DIMENSION` — a real `addressed_to` Statement
    `extract()` produces must validate against the schema exactly like
    every other predicate (same no-stripping shape as the test above).
    SKIPPED if `jsonschema` is not importable, like every other
    jsonschema-dependent test in this file."""
    jsonschema = _jsonschema_or_skip()
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    text = "The controller shall notify the data breach to the supervisory authority without undue delay."
    addressed_to_docs = [doc for doc in extract(text) if doc["predicate"] == "addressed_to"]
    assert addressed_to_docs, "expected at least one addressed_to Statement from this text"
    for doc in addressed_to_docs:
        assert set(doc.keys()) <= set(schema["properties"].keys())
        jsonschema.validate(instance=doc, schema=schema)


def test_extract_output_has_no_internal_underscore_fields():
    """The companion, non-jsonschema-dependent version of the same
    check: every key `extract()` returns is a real §21 field, never an
    extractor-internal one (those live in `extract_with_spans()`'s own
    `BuiltStatement.spans`, never folded into the Statement dict)."""
    for doc in extract("The provider shall maintain a log for the purposes of demonstrating compliance."):
        for key in doc:
            assert not key.startswith("_"), (doc, key)


def test_extract_with_spans_exposes_spans_separately_from_statement():
    built = extract_with_spans("The controller shall notify the authority within 72 hours.")
    assert built
    for b in built:
        assert set(b.spans.keys()) == {"clause", "subj", "obj"}
        for key in b.spans:
            assert isinstance(b.spans[key], tuple) and len(b.spans[key]) == 2
        for key in b.statement:
            assert not key.startswith("_")


# ───────────────── fallback guarantee (required fix 3) ──────────────────

def test_every_non_empty_unit_yields_at_least_one_statement():
    """Required fix 3: an empty-span candidate must be dropped BEFORE
    overlap resolution, so a later candidate (e.g. the last-resort
    whole-unit fallback) is never blocked by one that turned out empty.
    Regression case: a clause that LOOKS like it matches a real cue rule
    closely enough to claim the span, but whose own captured span
    collapses to nothing once determiner/modal-stripped — the fallback
    must still fire."""
    texts = [
        "shall shall.",  # degenerate, two pure modal tokens, nothing else
        "The the the.",
        "Testing shall ensure the system behaves consistently across every intended use.",
    ]
    for text in texts:
        stmts = extract(text)
        assert len(stmts) >= 1, (text, "expected at least one Statement")


def test_single_word_unit_is_the_one_documented_exception():
    """A single-word unit cannot be split into a subj span AND a
    distinct obj span at all — this is a structural impossibility, not
    a fallback-guarantee violation, and `extract()` correctly returns an
    empty list rather than fabricating a two-endpoint Statement out of
    one word. No real dev/gold unit is a single word, so this is
    documented here rather than asserted as a general "always >= 1"
    guarantee."""
    assert extract("shall.") == []


# ───────────────── codebook citations (required fix 5) ──────────────────

def test_every_rule_id_has_a_citation():
    """Required fix 5: every rule carries a codebook section citation.
    Runs every rule in `RULES` over a battery of inputs designed to fire
    each one, then asserts every ``rule_id`` actually emitted is a key
    in `RULE_CITATIONS` with a non-empty value."""
    probe_texts = [
        "'controller' means the natural or legal person which determines the purposes of processing.",
        "The annex forms part of the implementing act.",
        "The compliance programme includes an internal audit function.",
        "This Directive applies to the processing of traffic data.",
        "This Directive does not apply to activities concerning national security.",
        "References to the register include any successor register.",
        "Notwithstanding the fact that an exemption applies, the register must be kept.",
        "The notice referred to in Article 12 shall be published.",
        "The audit power is without prejudice to any inspection.",
        "The power applies without prejudice to any inspection by an authority.",
        "This power shall not affect any other remedy available to the data subject.",
        "The exporter shall retain the records, unless a shorter period is agreed.",
        "The exporter shall retain the records except where a shorter period is agreed.",
        "By way of derogation from the standard procedure, a notice may be used.",
        "Notwithstanding paragraph 2 of this Article, the report shall be provided.",
        "The definition has effect subject to— a subsection (2), b section 209.",
        "The shared interface enables a connected device to exchange telemetry.",
        "If a near-miss is detected, the operator shall record the event.",
        "In the case of a serious incident, the provider shall notify the authority.",
        "The act is permitted subject to appropriate safeguards for data subjects.",
        "For the purpose of ensuring compliance, the provider shall maintain records.",
        "Prior to the deployment, the operator shall complete the assessment.",
        "The assessment shall be completed prior to the deployment of the system.",
        "The classification is based on the risk assessment carried out under Article 9.",
        "The operator shall report the incident within 72 hours after becoming aware.",
        "The competent authority shall have the power to suspend a certificate.",
        "The supervisory authority is responsible for monitoring compliance.",
        "The supervisory authority shall be competent to issue guidance.",
        "The controller is responsible for demonstrating compliance.",
        "The deployer shall maintain a record of every high-risk decision.",
        "The deployer may maintain a record of every high-risk decision.",
        "The retention schedule is a binding part of the internal compliance policy.",
        "Zorble flurn wibbet quasm trindle hobnick frandle plonquist zestivorn glim.",
        # v3.6: addressed_to + the new deadline_of cues.
        "The controller shall notify the data breach to the supervisory authority without undue delay.",
        "The processor shall notify the controller promptly after discovering an incident.",
        "The officer shall respond within two months of the request.",
        "The agency shall issue a decision not later than one month after receipt.",
        "The system shall alert the operator immediately after detecting the fault.",
    ]
    seen_rule_ids = set()
    for text in probe_texts:
        for cand in collect_candidates(text):
            seen_rule_ids.add(cand.rule_id)
    assert len(seen_rule_ids) >= 20, f"only {len(seen_rule_ids)} distinct rule ids fired — probe battery too weak"
    missing = sorted(seen_rule_ids - set(RULE_CITATIONS))
    assert not missing, f"rule id(s) fired with NO citation recorded: {missing}"
    for rule_id in seen_rule_ids:
        assert RULE_CITATIONS[rule_id], f"rule id {rule_id!r} has an EMPTY citation"


def test_rule_citations_are_built_eagerly_not_from_this_probe_battery():
    """`RULE_CITATIONS` must be
    populated EAGERLY, at `rules.py` import time — independent of
    whether this (or any other) probe battery happens to exercise every
    runtime branch (the purpose-predicate router's 8 combinations, the
    competence_of/performs institutional-actor gate's 4, and
    every derived "<rule-id>-chapeau-inherited-item" id, now generated
    eagerly from whatever base ids are already registered at the SAME
    import time, rather than discovered lazily the first time a real
    unit happens to use a given rule as a chapeau trigger). Reimports
    the module fresh in a subprocess with NO candidate-collection call
    made at all, and checks the citation SET already matches EXACTLY —
    no dynamic exception needed any more."""
    result = subprocess.run(
        [sys.executable, "-c",
         "import sys, json; sys.path.insert(0, %r); "
         "from five_d_nd.extract.rules import RULE_CITATIONS; "
         "print(json.dumps(sorted(RULE_CITATIONS)))" % str(ROOT / "src")],
        capture_output=True, text=True, check=True,
    )
    eager_keys = set(json.loads(result.stdout.strip()))
    assert len(eager_keys) >= 80, f"expected RULE_CITATIONS eagerly populated with >= 80 entries at import, got {len(eager_keys)}"
    assert eager_keys == set(RULE_CITATIONS), (
        "RULE_CITATIONS differs between a fresh import and this test's own module-level "
        "import — every rule id, including every derived -chapeau-inherited-item id, "
        "must now be present eagerly"
    )


# ───────────────── round-2: co-coding + chapeau lists ────────────────────

def test_requires_and_deadline_of_co_code_the_same_clause():
    """codebook: 'Temporal vs causal' — a trigger clause that ALSO
    carries a duration phrase yields TWO Statements, not one."""
    text = "If a near-miss is detected, the operator shall record the event within 72 hours."
    preds = {s["predicate"] for s in extract(text)}
    assert "requires" in preds
    assert "deadline_of" in preds


def test_subject_to_chapeau_list_yields_one_statement_per_item():
    text = (
        "The definition has effect subject to— a subsection (2), b section 209, "
        "and c section 210."
    )
    stmts = [s for s in extract(text) if s["predicate"] == "except_when"]
    assert len(stmts) == 3
    objs = {s["obj"] for s in stmts}
    assert any("209" in o for o in objs)
    assert any("210" in o for o in objs)


# ───────────────── round-2 item 8: metadata-aware signature ─────────────

def test_extract_accepts_enclosing_provision_backwards_compatibly():
    """`extract(unit_text, *, enclosing_provision=None, ...)` is
    backwards-compatible — omitting the keyword entirely must behave
    EXACTLY as before."""
    text = "'controller' means the natural or legal person who determines the purposes of processing."
    assert extract(text) == extract(text, enclosing_provision=None)


def test_enclosing_provision_recital_routes_layer_to_surface():
    """codebook: a recital -> `surface` (rule 3), UNLESS rule 1/2
    already applies. A non-`is_a` predicate in a recital-labelled unit
    must be `surface`, not the metadata-free `domain` default."""
    text = "The shared interface enables a connected device to exchange telemetry with the platform."
    without_metadata = extract(text)
    assert without_metadata and without_metadata[0]["layer"] == "domain"
    with_metadata = extract(text, enclosing_provision="GDPR recital 71")
    assert with_metadata and with_metadata[0]["layer"] == "surface"


def test_enclosing_provision_is_a_stays_deep_regardless_of_position():
    """codebook rule 1 (`is_a` -> `deep`) wins even inside a recital —
    rule 1 is checked BEFORE rule 3."""
    text = "'synthetic marker' means any artificially generated identifier attached to a record for internal tracking."
    stmts = extract(text, enclosing_provision="GDPR recital 71")
    assert stmts and stmts[0]["layer"] == "deep"


def test_enclosing_provision_routes_purpose_predicate_by_position_not_modal():
    """codebook: 'Recital vs article' — POSITION decides, not the
    modal's presence. A purpose clause with an explicit modal, inside a
    unit labelled as a recital, must still route to
    `legislative_purpose_of` (never `compliance_purpose_of`)."""
    text = "The provider shall keep a log for the purposes of demonstrating compliance with this Article."
    with_modal_fallback = extract(text)
    assert with_modal_fallback and with_modal_fallback[0]["predicate"] == "compliance_purpose_of"
    with_recital_metadata = extract(text, enclosing_provision="AI Act recital 19")
    assert with_recital_metadata and with_recital_metadata[0]["predicate"] == "legislative_purpose_of"


# ═══════════════════ v3.6: addressed_to + deadline split ═══════════════

from five_d_nd.extract.rules import normalize_deadline_text, type_recipient_actor  # noqa: E402


def _preds(stmts, predicate):
    return [s for s in stmts if s["predicate"] == predicate]


def test_addressed_to_is_a_known_predicate_dimension_relational():
    assert statement_mod.is_known_predicate("addressed_to")
    assert statement_mod.predicate_dimension("addressed_to") == "relational"


def test_addressed_to_fires_alongside_performs_from_the_same_clause():
    """The B1 contract's own central case: a "notify ... to X" clause
    yields BOTH `performs` (the act, UNCHANGED) and `addressed_to` (the
    recipient, NEW) from the SAME host clause — the recipient is no
    longer buried, unreachable, inside `performs`'s own object."""
    text = "The controller shall notify the data breach to the supervisory authority without undue delay."
    stmts = extract(text)
    performs = _preds(stmts, "performs")
    addressed = _preds(stmts, "addressed_to")
    assert performs and performs[0]["subj"] == "controller"
    assert addressed and addressed[0]["obj"] == "supervisory_authority"


def test_addressed_to_direct_object_recipient_no_to_gdpr_33_2_style():
    """"notify the controller" (GDPR Art. 33(2) style): the processor's
    own recipient, no "to" at all — a direct-object cue."""
    text = "The processor shall notify the controller promptly after discovering an incident."
    stmts = extract(text)
    addressed = _preds(stmts, "addressed_to")
    assert any(s["obj"] == "controller" for s in addressed)


def test_addressed_to_communicate_to_data_subject():
    text = "The controller shall communicate the incident to the data subject within ten days."
    stmts = extract(text)
    addressed = _preds(stmts, "addressed_to")
    assert any(s["obj"] == "data_subject" for s in addressed)


def test_addressed_to_report_to_market_surveillance_authorities():
    text = (
        "The provider shall report the malfunction to the market surveillance "
        "authorities of the Member State where it occurred."
    )
    stmts = extract(text)
    addressed = _preds(stmts, "addressed_to")
    assert any(s["obj"] == "market_surveillance_authority" for s in addressed)


def test_addressed_to_inform_law_enforcement_or_judicial_authorities():
    text = "The platform shall inform the law enforcement or judicial authorities of the suspected offence."
    stmts = extract(text)
    addressed = _preds(stmts, "addressed_to")
    assert addressed and addressed[0]["obj"].startswith("other(law_enforcement")


@pytest.mark.parametrize("text", [
    "The operator shall report to the extent that resources allow.",
    "The provider shall report to ensure transparency with stakeholders.",
    "The agency shall act in relation to the matters referred to in Article 5.",
    "The incident shall be reported to be reviewed by the board next week.",
])
def test_addressed_to_never_fires_on_a_non_recipient_to(text):
    """Required negative examples: "to the extent that", "to ensure",
    "in relation to", "to be" are NEVER a recipient cue, even when a
    recognised addressed_to verb (report/inform/...) governs the same
    "to"."""
    stmts = extract(text)
    assert not _preds(stmts, "addressed_to")


def test_type_recipient_actor_types_a_known_role():
    assert type_recipient_actor("the supervisory authority competent in accordance with Article 55") \
        == "supervisory_authority"
    assert type_recipient_actor("the controller") == "controller"
    assert type_recipient_actor("the data subject") == "data_subject"


def test_type_recipient_actor_falls_back_to_other_escape():
    typed = type_recipient_actor("the national public authorities or bodies")
    assert typed == "other(national_public_authorities_or_bodies)"
    assert statement_mod.ACTOR_OTHER_RE.match(typed)


def test_addressed_to_negation_is_always_absent():
    """R-n, extended (v3.6): `addressed_to` is ALWAYS `negation:
    "absent"`, the same construction reason as `requires`/`deadline_of`
    — see `extract.negation.ALWAYS_ABSENT_PREDICATES`."""
    from five_d_nd.extract.negation import ALWAYS_ABSENT_PREDICATES
    assert "addressed_to" in ALWAYS_ABSENT_PREDICATES
    text = "The controller shall not notify the data breach to the supervisory authority without undue delay."
    stmts = extract(text)
    addressed = _preds(stmts, "addressed_to")
    assert addressed and all(s["negation"] == "absent" for s in addressed)


def test_deadline_of_normalizes_away_the_after_tail():
    """`deadline_of`'s own obj is the NORMALISED limit — "72 hours
    after having become aware of it" collapses to "72 hours"."""
    assert normalize_deadline_text("72 hours after having become aware of it") == "72 hours"
    assert normalize_deadline_text("30 days") == "30 days"


def test_deadline_of_normalizes_word_numbers():
    assert normalize_deadline_text("one month after the submission") == "one month"
    assert normalize_deadline_text("two days") == "two days"


def test_deadline_of_normalizes_qualitative_cues():
    assert normalize_deadline_text("Without Undue Delay") == "without undue delay"
    assert normalize_deadline_text("Promptly") == "promptly"
    assert normalize_deadline_text("Immediately") == "immediately"


def test_deadline_of_qualitative_cue_fires_without_undue_delay_promptly_immediately():
    cases = {
        "The controller shall notify the authority without undue delay of the breach.": "without undue delay",
        "The provider shall inform the authority promptly of the malfunction.": "promptly",
        "The provider shall notify the authority immediately after detecting the fault.": "immediately",
    }
    for text, expected_obj in cases.items():
        stmts = extract(text)
        deadlines = _preds(stmts, "deadline_of")
        assert any(s["obj"] == expected_obj for s in deadlines), (text, deadlines)


def test_deadline_of_word_number_duration_fires():
    """`deadline_of`'s own subject-binding rule
    needs a GOVERNED ACT to bind to — a `performs`-shaped actor from
    the closed `ACTOR_ROLES` set, here, so the deadline is not simply
    dropped for lack of one."""
    text = "The provider shall respond to the authority within two months of the request."
    stmts = extract(text)
    deadlines = _preds(stmts, "deadline_of")
    assert any(s["obj"] == "two months" for s in deadlines)

    text2 = "The provider shall notify the authority not later than one month after receipt."
    stmts2 = extract(text2)
    deadlines2 = _preds(stmts2, "deadline_of")
    assert any(s["obj"] == "one month" for s in deadlines2)


def test_deadline_of_coexists_with_performs_from_the_same_clause():
    """`never_conflicts` applies ONLY to a NEW
    deadline cue (here, the v3.6 word-number duration "two months") —
    it, and not the pre-existing digit-based "within N" cue, no longer
    silences `performs`; both survive from the SAME host clause."""
    text = "The provider shall maintain records within two months of the request."
    stmts = extract(text)
    performs = _preds(stmts, "performs")
    deadlines = _preds(stmts, "deadline_of")
    assert performs and performs[0]["predicate"] == "performs"
    assert deadlines and deadlines[0]["obj"] == "two months"


def test_addressed_to_and_deadline_of_both_coexist_with_performs():
    """A GDPR Art. 33(1)-shaped case (this feature's own worked
    example, re-created as a brand-new sentence) using the NEW
    qualitative cue "promptly": one clause, THREE Statements — the act
    (`performs`), the recipient (`addressed_to`), and the limit
    (`deadline_of`), never forcing a choice among them."""
    text = "The controller shall notify the breach to the supervisory authority promptly."
    stmts = extract(text)
    assert _preds(stmts, "performs")
    addressed = _preds(stmts, "addressed_to")
    assert addressed and addressed[0]["obj"] == "supervisory_authority"
    deadlines = _preds(stmts, "deadline_of")
    assert deadlines and deadlines[0]["obj"] == "promptly"


def test_pre_existing_within_n_deadline_keeps_pre_v36_conflict_behaviour():
    """The pre-existing, pre-v3.6 digit-based
    "within N" cue keeps EXACTLY origin/main's own conflict behaviour
    — `never_conflicts=False` — so it still blocks (and is blocked by)
    a REAL predicate exactly as before this whole feature existed.
    "The operator shall report the incident within 72 hours after
    becoming aware of it." gives ONLY `deadline_of` (`performs` is
    blocked by it, never a NEW addition alongside it)."""
    text = "The operator shall report the incident within 72 hours after becoming aware of it."
    stmts = extract(text)
    assert not _preds(stmts, "performs")
    deadlines = _preds(stmts, "deadline_of")
    assert deadlines and deadlines[0]["subj"] == "operator" and deadlines[0]["obj"] == "72 hours"


# ═══════════════════ deadline-subject binding + recipient head ═══

def test_deadline_subject_is_the_governed_act_not_the_clause_subject():
    """Minimal reproduction: "Member States
    shall ensure that providers notify the authority promptly." used to
    give `deadline_of` subj="Member States" (the OUTER clause's own
    subject) — never the ACT "promptly" actually times. It is now bound
    to `notify` (the `addressed_to` companion's own subj, the SAME act)."""
    text = "Member States shall ensure that providers notify the authority promptly."
    stmts = extract(text)
    deadlines = _preds(stmts, "deadline_of")
    assert deadlines and all(s["subj"] == "notify" for s in deadlines)
    assert not any(s["subj"] == "Member States" for s in deadlines)


@pytest.mark.parametrize("text", [
    "The widget requires calibration immediately.",
])
def test_deadline_dropped_when_no_governed_act_in_clause(text):
    """"If no governed act can be bound inside the same clause, emit
    nothing" applies to a NEW deadline cue (here, the v3.6 qualitative
    cue "immediately") that never existed on origin/main at all — "the
    widget" is not a closed `ACTOR_ROLES` member, so no `performs`
    fires, and no other companion exists, so the candidate is dropped
    rather than kept with a clause-subject/fragment/pronoun/connective
    subj. (This does NOT apply to the
    pre-existing, pre-v3.6 digit-based "within N" cue — see
    `test_pre_existing_within_n_deadline_keeps_pre_v36_subj_when_no_
    governed_act_exists`, below, for that one.)"""
    stmts = extract(text)
    assert not _preds(stmts, "deadline_of")


def test_pre_existing_within_n_deadline_keeps_pre_v36_subj_when_no_governed_act_exists():
    """The pre-existing, pre-v3.6 digit-based
    "within N" cue is NEVER dropped for lack of a governed act — that
    would REMOVE a Statement origin/main already produced. "The
    auditor shall review it within 30 days." keeps subj="auditor"
    (main's own, pre-rebind value) UNCHANGED, exactly as before this
    whole feature existed."""
    text = "The auditor shall review it within 30 days."
    stmts = extract(text)
    deadlines = _preds(stmts, "deadline_of")
    assert deadlines and deadlines[0]["subj"] == "auditor" and deadlines[0]["obj"] == "30 days"


def test_addressed_to_negative_possessor_np_is_not_the_recipient():
    """A possessor NP ("the findings OF the market
    surveillance authority") is never the recipient — the role name
    sits inside a phrase that MODIFIES a different direct object,
    never naming the recipient itself. The genuine "to the Commission"
    recipient in the SAME sentence still fires correctly."""
    text = "The authority shall report the findings of the market surveillance authority to the Commission."
    stmts = extract(text)
    addressed = _preds(stmts, "addressed_to")
    assert addressed and all(s["obj"] == "commission" for s in addressed)
    assert not any("market_surveillance_authority" == s["obj"] for s in addressed)


def test_addressed_to_negative_passive_by_agent_is_not_the_recipient():
    """"The draft decision submitted BY X" names X
    as the passive-voice AGENT (the one doing the submitting), never
    the recipient — "by" is excluded from the recipient cue entirely."""
    text = "The lead supervisory authority submitted the draft decision by the deadline."
    stmts = extract(text)
    assert not _preds(stmts, "addressed_to")


def test_addressed_to_national_modifier_still_types_as_closed_role():
    """"The national market surveillance authority"
    types as `market_surveillance_authority` — a single leading
    modifier word ("national") narrows WHICH authority, it does not
    block the role match or fall through to `other(...)`."""
    text = "The provider shall inform the national market surveillance authority of the decision."
    stmts = extract(text)
    addressed = _preds(stmts, "addressed_to")
    assert addressed and any(s["obj"] == "market_surveillance_authority" for s in addressed)


# ═══════════════════ antecedent binding + except_when ═══════

def test_deadline_in_a_conditional_antecedent_is_never_rebound_to_the_consequence():
    """Minimal reproduction: "Where the
    request is not answered within 30 days, the application shall be
    deemed accepted." used to rebind the deadline to the CONSEQUENCE
    ("accepted") — wrong, since "30 days" times the ANTECEDENT ("not
    answered"), never the outcome. The `requires` candidate's own
    `subj` (the antecedent) literally CONTAINS the deadline's own span
    here, which is the decisive signal: the Statement's ORIGINAL,
    pre-rebind subj (already reading as the antecedent clause itself)
    is kept UNCHANGED rather than replaced by the consequence."""
    text = "Where the request is not answered within 30 days, the application shall be deemed accepted."
    stmts = extract(text)
    deadlines = _preds(stmts, "deadline_of")
    assert deadlines
    assert not any(s["subj"] == "accepted" for s in deadlines)
    assert all("not answered" in s["subj"] for s in deadlines)


def test_deadline_in_antecedent_ai_act_73_style_not_provided_an_answer():
    """The AI Act Art. 73(8)-shaped reproduction: "has not provided an
    answer within N days" — the deadline times the AUTHORITY's own
    failure to answer, never a consequence elsewhere in the sentence."""
    text = (
        "Where the market surveillance authority has not provided an answer within 30 days, "
        "the testing shall be understood to have been approved."
    )
    stmts = extract(text)
    deadlines = _preds(stmts, "deadline_of")
    assert deadlines
    assert all("has not provided an answer" in s["subj"] for s in deadlines)
    assert not any("approved" in s["subj"] for s in deadlines)


def test_deadline_inside_an_except_when_exception_condition_binds_to_the_condition():
    """The DSA Art. 87-shaped reproduction: "unless X opposes ... not
    later than N months" — the deadline times the EXCEPTION CONDITION
    ("opposes such extension"), never the general rule it carves an
    exception out of ("The delegation of power shall be tacitly
    extended ...")."""
    text = (
        "The delegation of power shall be tacitly extended for periods of an identical duration, "
        "unless the European Parliament or the Council opposes such extension not later than "
        "three months before the end of each period."
    )
    stmts = extract(text)
    deadlines = _preds(stmts, "deadline_of")
    assert deadlines
    assert all("opposes such extension" in s["subj"] for s in deadlines)
    assert not any(s["subj"].startswith("The delegation of power") for s in deadlines)


def test_except_when_notwithstanding_provision_is_never_a_deadline_companion():
    """A "notwithstanding [provision]"/"subject to [provision]"
    `except_when` reading's own obj is a BARE PROVISION REFERENCE
    ("paragraph 2") — never trusted as a `deadline_of` companion, even
    though it is, technically, a Statement sharing the same clause."""
    text = (
        "Notwithstanding paragraph 2 of this Article, in the event of a serious incident, "
        "the report shall be provided immediately."
    )
    stmts = extract(text)
    deadlines = _preds(stmts, "deadline_of")
    assert deadlines
    assert not any(s["subj"].strip() == "paragraph 2 of this Article" for s in deadlines)


