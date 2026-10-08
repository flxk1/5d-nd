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

import ast
import json
import os
import re
import subprocess
import sys
import unicodedata
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
# Local, un-shipped corpus root. No default path: the tests below that
# use it SKIP cleanly unless the LOOMGROUND_DATA_ROOT environment
# variable is set (a fresh clone, and any run that does not set this
# variable, has neither a directory nor a fixture here).
_LOCAL_CORPUS_ROOT_ENV = os.environ.get("LOOMGROUND_DATA_ROOT")
TOOLS_DIR = Path(_LOCAL_CORPUS_ROOT_ENV) / "_tools" / "triple-gold" if _LOCAL_CORPUS_ROOT_ENV else Path("/nonexistent-unless-LOOMGROUND_DATA_ROOT-is-set")
DEV_GOLD_PATH = TOOLS_DIR / "dev-set" / "dev-gold-300.json"


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
    full-run gold corpus (out of this session's own read territory) — it
    instead asserts the STRUCTURAL property that is within reach: every
    vector's own text is short (a single invented sentence), which is
    the actual guarantee this session can make and keep."""
    for path in VECTORS:
        v = _case(path)
        text = v["input"]["unit_text"]
        assert len(text) < 200, (path.stem, "unexpectedly long unit_text")


def _normalize_for_overlap(s: str) -> str:
    """NFKC-normalise, case-fold, fold EVERY quote mark/punctuation
    character to a space, then collapse whitespace — round-4 fix: the
    round-3 version (case-fold + whitespace-collapse only) missed a
    near-verbatim quote that differs only in QUOTE STYLE (curly ‘’/“”
    vs straight ''/\"\") or other punctuation, since those characters
    were left untouched and therefore broke the substring match even
    though the underlying WORDS were identical. `[^\\w\\s]` (Unicode-
    aware: underscore/digits/letters survive, everything else — every
    quote mark, dash, comma, full stop — becomes a space) closes that
    gap; NFKC additionally folds compatibility variants (full-width
    forms, etc.) before the punctuation fold runs. Not
    `statement.normalize_statement_text` (which deliberately preserves
    case and does NOT fold punctuation — a different, §21 id-hashing
    concern, not a leak-detection one)."""
    t = unicodedata.normalize("NFKC", s)
    t = t.lower()
    t = re.sub(r"[^\w\s]", " ", t, flags=re.UNICODE)
    return re.sub(r"\s+", " ", t).strip()


def _collect_source_string_literals(path: Path, *, exclude_functions: frozenset = frozenset()) -> "list[tuple]":
    """Every string literal in ``path``'s own source, via `ast` — a
    mechanical, exhaustive alternative to a human re-reading every
    string for an accidentally-copied quote. Returns ``(label, text)``
    pairs; ``label`` is ``"<path.name>:<lineno>"`` for traceability.
    ``exclude_functions`` (by name) skips a function's own subtree
    entirely — for THIS module's own self-test, below, whose own
    literal is DELIBERATELY a near-verbatim quote (it exists to prove
    the overlap check catches it), not an accidental leak."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    excluded_nodes = set()
    if exclude_functions:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in exclude_functions:
                excluded_nodes.update(ast.walk(node))
    out = []
    for node in ast.walk(tree):
        if node in excluded_nodes:
            continue
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            out.append((f"{path.name}:{node.lineno}", node.value))
    return out


def _overlap_offenders(candidates: "list[tuple]", gold_texts: "list[str]", window: int = 60) -> "list[tuple]":
    """``candidates``: ``(label, text)`` pairs. ``gold_texts``: already
    `_normalize_for_overlap`-normalised real unit texts. Returns every
    ``(label, chunk)`` where ``text``, normalised, shares a run of at
    least ``window`` characters with ANY ``gold_texts`` entry."""
    offenders = []
    for label, text in candidates:
        norm = _normalize_for_overlap(text)
        if len(norm) < window:
            continue
        for start in range(0, len(norm) - window + 1):
            chunk = norm[start:start + window]
            if any(chunk in gold_text for gold_text in gold_texts):
                offenders.append((label, chunk))
                break
    return offenders


#: This scan covers the extractor's OWN source, the
#: segmenter's own test file, and the local evaluation scripts (not
#: shipped) that score the segmenter and the candidate-recall stage
#: — not only THIS test file and the vector corpus. A rule's own
#: docstring or comment, a segmenter test's own invented sentence, or a
#: scoring script's own docstring example could just as easily carry an
#: accidental near-verbatim quote.
_EXTRACT_SRC_FILES = sorted((ROOT / "src" / "five_d_nd" / "extract").glob("*.py"))
_OTHER_SCANNED_FILES = (
    ROOT / "tests" / "test_segment.py",
    ROOT / "score_segmenter_dev.py",
    ROOT / "tests" / "test_hybrid.py",
    ROOT / "score_candidate_recall_dev.py",
)


def test_no_vector_or_test_string_overlaps_dev_gold_60_chars():
    """Held-out/no-gold-text hard rule, checked MECHANICALLY rather than
    by eye: no vector's own ``unit_text``, no string literal anywhere in
    THIS test file, `tests/test_segment.py`, the local evaluation script
    (not shipped) that scores the segmenter, or
    `src/five_d_nd/extract/*.py`, shares a 60-NORMALISED-character (or
    longer) run with any real dev-gold unit text (`dev-set/
    dev-gold-300.json`) — normalisation now folds quote-mark/punctuation
    STYLE differences too (`_normalize_for_overlap`), not just case and
    whitespace, so a near-verbatim quote using different quote glyphs is
    still caught. SKIPPED if the local corpus is absent (another
    operator's checkout may not have it) — this check can only run WITH
    the real corpus in hand; see `test_no_vector_input_text_is_a_long_
    verbatim_corpus_quote`, above, for the length-only property that
    holds even without it."""
    if not DEV_GOLD_PATH.exists():
        pytest.skip("triple-gold dev-gold file not present on this machine")
    data = json.loads(DEV_GOLD_PATH.read_text(encoding="utf-8"))
    gold_texts = [_normalize_for_overlap(u["text"]) for u in data["units"].values()]

    candidates = [(p.stem, _case(p)["input"]["unit_text"]) for p in VECTORS]
    candidates += _collect_source_string_literals(Path(__file__))
    for src_path in _EXTRACT_SRC_FILES:
        candidates += _collect_source_string_literals(src_path)
    for other_path in _OTHER_SCANNED_FILES:
        if other_path.exists():
            candidates += _collect_source_string_literals(other_path)

    offenders = _overlap_offenders(candidates, gold_texts)
    assert not offenders, f"{len(offenders)} string(s) overlap a real dev-gold unit by >= 60 chars: {offenders[:5]}"


def test_normalize_for_overlap_flags_a_dev_unit_with_folded_quotes():
    """Self-test (round-4 fix, round-5 fix: the fixture is now built AT
    RUNTIME from the real dev unit text, never hand-typed as a static
    literal in this file — a hand-typed near-copy of real corpus text is
    itself exactly the kind of accidental leak this whole check exists
    to catch, even when excluded from the general scan by name).
    Takes a real dev unit's own opening text, re-renders its curly
    quotes as straight ones (simulating the quote-STYLE difference that
    let a round-2 test string through the round-3 normalisation
    unnoticed), and asserts the FIXED normalisation (`_normalize_for_
    overlap`, which folds quote-mark/punctuation style, not just case
    and whitespace) still finds the overlap against the ORIGINAL
    (curly-quoted) unit text. SKIPPED if the local corpus is absent."""
    if not DEV_GOLD_PATH.exists():
        pytest.skip("triple-gold dev-gold file not present on this machine")
    data = json.loads(DEV_GOLD_PATH.read_text(encoding="utf-8"))
    gold_texts = [_normalize_for_overlap(u["text"]) for u in data["units"].values()]

    # Any dev unit whose own opening text is long enough and carries a
    # curly quote mark will do — pick the first one found, so this test
    # does not depend on one specific unit id continuing to exist.
    source_unit = None
    for u in data["units"].values():
        text = u["text"]
        if len(text) >= 70 and ("‘" in text[:70] or "“" in text[:70]):
            source_unit = text
            break
    assert source_unit is not None, "expected at least one dev unit with a curly quote in its opening text"

    fixture = source_unit[:70].replace("‘", "'").replace("’", "'") \
        .replace("“", '"').replace("”", '"')
    assert fixture != source_unit[:70], "fixture must actually differ in quote style from the source"

    offenders = _overlap_offenders([("runtime-built fixture", fixture)], gold_texts)
    assert offenders, "expected the quote-folded fixture to be flagged against its own source dev unit"



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


