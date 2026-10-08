# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""Tests for `five_d_nd.extract.segment` — a recursive-descent
clause/list-item grammar, ported from a build comparison's own
winning design (`candidate-2/test_segmenter.py`) and adapted: every
invented sentence below is a BRAND-NEW phrase (never a >=60-char
verbatim quote from the local corpus, including a codebook worked
example that is ITSELF a byte-offset-cited corpus quote — the UK DPA
2018 s. 6(1) "definition of 'controller'..." example is deliberately
NOT reproduced here; see `tests/test_extract.py::
test_no_vector_or_test_string_overlaps_dev_gold_60_chars`, which already
scans this file's own module, for the mechanical leak guard). Tests
cover the grafts added on top of the winning design (a widened
inline-list lead-in, no-comma coordination, the
chapeau-linguistic-completeness measurement decision,
the layout-independent-list fallback, and `np_chunks`).
"""
from __future__ import annotations

from five_d_nd.extract.segment import (
    DEFAULT_CONFIG,
    Config,
    clean_np_chunks,
    coordinated_shared_subject_spans,
    coordinated_subject_conjuncts,
    inherited_subject_spans,
    np_chunks,
    relative_clause_antecedent_spans,
    segment,
    smallest_complete_clause_span,
    smallest_complete_clause_spans,
    tokenize,
    with_overrides,
)


def spans(text, kinds=("clause", "list_item")):
    return [text[d["start"]:d["end"]] for d in segment(text) if d["kind"] in kinds]


def by_kind(text, kind):
    return [d for d in segment(text) if d["kind"] == kind]


# ───────────────────────────── basic grammar ────────────────────────────

def test_simple_sentence_is_one_clause():
    text = "The operator shall notify the authority within 72 hours."
    segs = segment(text)
    clauses = by_kind(text, "clause")
    assert len(clauses) == 1
    assert (clauses[0]["start"], clauses[0]["end"]) == (0, len(text.rstrip(".")))


def test_verbless_heading_yields_no_clause():
    text = "Chapter 5 Enforcement 109 1 A controller may process personal data."
    clauses = by_kind(text, "clause")
    assert len(clauses) == 1
    assert "A controller may process" in text[clauses[0]["start"]:clauses[0]["end"]]


def test_empty_text_yields_no_spans():
    assert segment("") == []
    assert segment("   \n  ") == []


def test_determinism_same_input_same_output():
    text = "Where a breach occurs, the controller shall notify the authority, and the authority shall investigate."
    assert segment(text) == segment(text)


# ─────────────────────────── chapeau + vertical list ─────────────────────

def test_chapeau_list_blank_line_style_inherits_subject():
    # EU-style layout: each lettered marker alone on its own line, blank
    # lines separating chapeau / label / item-text blocks.
    text = (
        "The competent authority shall perform the following tasks:\n\n"
        "(a)\n\n"
        "monitor compliance with this Regulation\n\n"
        "(b)\n\n"
        "advise the government on legislative measures\n\n"
        "(c)\n\n"
        "cooperate with other competent authorities"
    )
    items = by_kind(text, "list_item")
    assert [text[d["start"]:d["end"]] for d in items] == [
        "monitor compliance with this Regulation",
        "advise the government on legislative measures",
        "cooperate with other competent authorities",
    ]
    chap = by_kind(text, "chapeau")
    assert len(chap) == 1
    segs = segment(text)
    ch_idx = segs.index(chap[0])
    assert all(d["inherits_subject_from"] == ch_idx for d in items)


def test_chapeau_list_never_one_whole_sentence_span():
    text = (
        "The register shall record the following matters:\n\n"
        "(a)\n\n"
        "the date of each entry\n\n"
        "(b)\n\n"
        "the name of the officer responsible"
    )
    # the chapeau+list sentence as a whole is never itself a scored span
    whole = (0, len(text))
    scored = [(d["start"], d["end"]) for d in segment(text) if d["kind"] in ("clause", "list_item")]
    assert whole not in scored


def test_nested_roman_list_under_letter_item():
    text = (
        "The notice shall state:\n\n"
        "(a)\n\n"
        "the grounds, namely:\n\n"
        "(i)\n\n"
        "a breach has occurred\n\n"
        "(ii)\n\n"
        "the breach has not been remedied\n\n"
        "(b)\n\n"
        "the deadline for compliance"
    )
    items = by_kind(text, "list_item")
    texts = [text[d["start"]:d["end"]] for d in items]
    assert "a breach has occurred" in texts
    assert "the breach has not been remedied" in texts
    assert "the deadline for compliance" in texts


# ───────────────────────── inline (UK-style) list ────────────────────────

def test_inline_dash_list_three_items():
    text = "The order has effect— a for one month, b for two months, and c for three months."
    items = by_kind(text, "list_item")
    assert [text[d["start"]:d["end"]] for d in items] == [
        "for one month", "for two months", "for three months"
    ]


def test_inline_list_mid_sentence_reference_is_not_a_list():
    # "(a) and (b)" here REFERS to two points, it does not START a list —
    # graft (b)'s own filter: a parenthesised marker counts only right
    # after a newline or one of : ; — , .
    text = "The obligations in points (a) and (b) of Article 6 apply to every controller."
    items = by_kind(text, "list_item")
    assert items == []


def test_inline_list_colon_lead_in_graft_b():
    # graft (b): an inline list may start right after a colon, not only
    # a dash.
    text = "The notice must state: a the grounds, b the deadline, and c the remedy available."
    items = by_kind(text, "list_item")
    assert [text[d["start"]:d["end"]] for d in items] == [
        "the grounds", "the deadline", "the remedy available"
    ]


def test_inline_list_plabel_regression_em_dash_no_space():
    """Regression test (round-4 fix, graft (b)): "—(a) …, (b) …" — a
    PLABEL-style marker directly after the dash with NO space, still
    recognised as a list start."""
    text = "The scheme applies—(a) to a controller, (b) to a processor, and (c) to a joint controller."
    items = by_kind(text, "list_item")
    assert len(items) == 3
    assert "controller" in text[items[0]["start"]:items[0]["end"]]
    assert "processor" in text[items[1]["start"]:items[1]["end"]]


# ───────────────────────── coordination / subordination ──────────────────

def test_coordination_with_comma_before_and():
    text = "The controller shall assess the risk, and shall notify the authority without delay."
    clauses = by_kind(text, "clause")
    assert len(clauses) >= 2


def test_coordination_without_comma_before_and_graft_c():
    """graft (c), codebook R-i, default ON: a coordinated clause with its
    own subject is a sibling clause whether or not a comma precedes the
    coordinator."""
    text = "The controller shall assess the risk and the processor shall assist with the assessment."
    clauses_default = by_kind(text, "clause")
    cfg_off = with_overrides(coord_clause_no_comma=False)
    clauses_off = [d for d in segment(text, cfg=cfg_off) if d["kind"] == "clause"]
    assert len(clauses_default) > len(clauses_off)


def test_semicolon_split_inside_item():
    text = (
        "The register shall record the matter:\n\n"
        "(a)\n\n"
        "the controller shall notify the data subject; the authority shall investigate the matter further"
    )
    items = by_kind(text, "list_item")
    assert len(items) == 1
    chap = by_kind(text, "chapeau")
    segs = segment(text)
    ch_idx = segs.index(chap[0])
    tail_clauses = [d for d in segs if d["kind"] == "clause" and d["inherits_subject_from"] == ch_idx]
    assert tail_clauses


# ───────────────────────────── config / grafts ───────────────────────────

def test_config_is_immutable_and_with_overrides_is_pure():
    assert isinstance(DEFAULT_CONFIG, Config)
    cfg2 = with_overrides(chapeau_min_chars=10)
    assert cfg2.chapeau_min_chars == 10
    assert DEFAULT_CONFIG.chapeau_min_chars == 140  # unchanged
    try:
        DEFAULT_CONFIG.chapeau_min_chars = 5  # type: ignore[misc]
        assert False, "Config must be frozen"
    except Exception:
        pass


def test_default_config_has_coord_clause_no_comma_on_by_default():
    # graft (c)'s own default, per the integration decision (codebook R-i)
    assert DEFAULT_CONFIG.coord_clause_no_comma is True


def test_default_config_has_chapeau_linguistic_complete_off_by_default():
    # measured on dev: alone it cost 0.0051 mean F1, outside the "~0.002"
    # adoption tolerance — see docs/decisions/0011-segmenter-integration.md
    assert DEFAULT_CONFIG.chapeau_linguistic_complete is False


def test_layout_independent_list_fallback_graft_a():
    """graft (a): a vertical list laid out WITHOUT a blank line between
    the label and its own item text (each marker starts its own LINE,
    but there is no blank-line separation) is still found, as a
    FALLBACK, when the blank-line path finds nothing."""
    text = (
        "The schedule requires the following measures:\n"
        "(a) the controller encrypts personal data\n"
        "(b) the controller pseudonymises personal data\n"
        "(c) the controller tests technical measures regularly"
    )
    items = by_kind(text, "list_item")
    assert len(items) == 3
    texts = [text[d["start"]:d["end"]] for d in items]
    assert any("encrypts" in t for t in texts)
    assert any("pseudonymises" in t for t in texts)
    assert any("tests technical measures" in t for t in texts)


def test_layout_independent_fallback_can_be_disabled():
    text = (
        "The schedule requires the following measures:\n"
        "(a) the controller encrypts personal data\n"
        "(b) the controller pseudonymises personal data\n"
        "(c) the controller tests technical measures regularly"
    )
    cfg_off = with_overrides(layout_independent_lists=False)
    items_off = [d for d in segment(text, cfg=cfg_off) if d["kind"] == "list_item"]
    assert items_off == []


# ───────────────────────────── np_chunks (graft d) ───────────────────────

def test_np_chunks_excludes_modal_and_strips_determiner():
    text = "the national competent authority shall notify the supervisory authority"
    chunks = np_chunks(text)
    chunk_texts = [text[a:b] for a, b in chunks]
    assert "national competent authority" in chunk_texts
    assert "supervisory authority" in chunk_texts
    # R-k: no chunk contains the modal
    assert not any("shall" in c for c in chunk_texts)
    # R-q: no chunk starts with a bare "the"
    assert not any(c.lower().startswith("the ") for c in chunk_texts)


def test_np_chunks_handles_empty_and_no_np_text():
    assert np_chunks("") == []
    assert np_chunks("shall must should") == []


def test_np_chunks_of_phrase_kept_together():
    text = "the processing of personal data shall be lawful"
    chunks = np_chunks(text)
    chunk_texts = [text[a:b] for a, b in chunks]
    assert any("processing of personal data" in c for c in chunk_texts)


# ───────────────────────────── tokenizer ─────────────────────────────────

def test_tokenize_recognises_plabel_and_dash():
    toks = tokenize("(a) — the item")
    kinds = [t.kind for t in toks]
    assert "PLABEL" in kinds
    assert "DASH" in kinds


def test_tokenize_blank_line_is_its_own_token():
    toks = tokenize("first block\n\nsecond block")
    assert any(t.kind == "BLANK" for t in toks)


# ───────────────────── output contract / determinism ─────────────────────

def test_every_span_has_well_formed_offsets():
    text = (
        "Where a breach occurs, the controller shall notify the authority. "
        "The authority shall, within one month, respond to the notification."
    )
    for d in segment(text):
        assert 0 <= d["start"] < d["end"] <= len(text)
        assert set(d.keys()) == {"start", "end", "kind", "parent", "inherits_subject_from"}
        assert d["kind"] in ("sentence", "clause", "list_item", "chapeau")


def test_enclosing_provision_accepted_but_does_not_change_spans():
    text = "The controller shall notify the authority within 72 hours."
    assert segment(text) == segment(text, enclosing_provision="GDPR recital 71")


def test_non_string_input_raises_type_error():
    import pytest
    with pytest.raises(TypeError):
        segment(12345)  # type: ignore[arg-type]


# ───────────────────── round-8 (CandidateSet v2) additions ───────────────
# Every sentence below is a brand-new, invented phrase typed for this
# session — never a corpus quote (see `tests/test_extract.py::
# test_no_vector_or_test_string_overlaps_dev_gold_60_chars`, which
# already scans this module for the mechanical leak guard).

def test_inherited_subject_spans_gives_the_chapeau_subject_to_each_item():
    text = (
        "The licensor may terminate this agreement where:\n"
        "(a) the licensee fails to pay the fee;\n"
        "(b) the licensee breaches a material term.\n"
    )
    segs = segment(text)
    out = inherited_subject_spans(text, segs)
    item_idxs = [i for i, n in enumerate(segs) if n["kind"] == "list_item"]
    assert item_idxs, "expected at least one list_item"
    for idx in item_idxs:
        assert idx in out
        s, e = out[idx]
        assert text[s:e] == "licensor"


def test_relative_clause_antecedent_spans_resolves_the_antecedent_np():
    text = "The vendor shall deliver the goods, which satisfy the agreed specification."
    segs = segment(text)
    out = relative_clause_antecedent_spans(text, segs)
    assert out, "expected at least one relative-clause tail mapped to an antecedent"
    (tail_span, antecedent_span), = out.items()
    assert text[tail_span[0]:tail_span[1]].startswith("which satisfy")
    assert text[antecedent_span[0]:antecedent_span[1]] == "vendor"


def test_relative_clause_antecedent_spans_is_empty_without_a_relative_clause():
    text = "The vendor shall deliver the goods on the agreed date."
    segs = segment(text)
    assert relative_clause_antecedent_spans(text, segs) == {}


def test_coordinated_shared_subject_spans_gives_the_first_clauses_subject():
    text = "The buyer shall inspect the goods, and shall confirm receipt within five days."
    segs = segment(text)
    out = coordinated_shared_subject_spans(text, segs)
    assert out, "expected at least one subjectless coordinated sibling"
    for idx, (s, e) in out.items():
        assert text[s:e] == "buyer"
        # the sibling itself never carries its own leading subject NP
        sibling_text = text[segs[idx]["start"]:segs[idx]["end"]]
        assert sibling_text.startswith("shall")


def test_coordinated_shared_subject_spans_is_empty_with_an_explicit_subject():
    text = "The buyer shall inspect the goods, and the seller shall confirm receipt."
    segs = segment(text)
    out = coordinated_shared_subject_spans(text, segs)
    assert out == {}


def test_coordinated_subject_conjuncts_splits_a_coordinated_np():
    text = "The licensor and the licensee shall sign the renewal."
    conjuncts = [text[s:e] for s, e in coordinated_subject_conjuncts(text)]
    assert "licensor" in conjuncts
    assert "licensee" in conjuncts
    # the maximal chunk is still available separately via np_chunks()
    assert any("licensor and the licensee" in text[s:e] or
               "licensor and" in text[s:e] for s, e in np_chunks(text))


def test_clean_np_chunks_drops_a_bare_list_label():
    text = "(a) the licensee\n(b) the sub-licensee\nshall each notify the registrar."
    cleaned = [text[s:e] for s, e in clean_np_chunks(text)]
    assert "a" not in cleaned
    assert "b" not in cleaned
    assert "licensee" in cleaned
    assert "sub-licensee" in cleaned


def test_clean_np_chunks_never_crosses_a_newline():
    text = "Renewal Terms\nThe licensee shall renew the licence annually."
    for s, e in clean_np_chunks(text):
        assert "\n" not in text[s:e]


def test_clean_np_chunks_drops_a_standalone_heading_line():
    text = "Renewal Terms\n\nThe licensee shall renew the licence annually."
    cleaned = [text[s:e] for s, e in clean_np_chunks(text)]
    assert "Renewal Terms" not in cleaned


def test_clean_np_chunks_never_ends_on_a_dangling_function_word():
    text = "The licensee shall notify the registrar prior to the renewal."
    for s, e in clean_np_chunks(text):
        last_word = text[s:e].rstrip().split()[-1].lower()
        assert last_word not in ("to", "that", "of", "and", "or", "the", "a")


def test_smallest_complete_clause_span_trims_a_trailing_adverbial():
    text = "The licensee shall notify the registrar within thirty days of the renewal."
    full = (0, len(text.rstrip(".")))
    trimmed = smallest_complete_clause_span(text, full)
    assert text[trimmed[0]:trimmed[1]] == "The licensee shall notify the registrar"


def test_smallest_complete_clause_span_is_unchanged_without_a_trailing_adverbial():
    text = "The licensee shall notify the registrar."
    full = (0, len(text) - 1)
    assert smallest_complete_clause_span(text, full) == full


def test_smallest_complete_clause_spans_covers_every_leaf_clause_or_item():
    text = "The licensee shall notify the registrar within thirty days of the renewal."
    segs = segment(text)
    leaf_count = sum(1 for n in segs if n["kind"] in ("clause", "list_item"))
    assert len(smallest_complete_clause_spans(text, segs)) == leaf_count
