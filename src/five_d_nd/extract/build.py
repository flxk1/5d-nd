# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""The extractor's own orchestrator: ``extract(unit_text) -> list[Statement]``.

Pipeline, in order: (1) segment the unit text (`extract.segment.segment`
— a recursive-descent clause/list-item grammar) and run every rule in `extract.
rules.RULES` PER CLAUSE/LIST-ITEM SPAN (`extract.rules.
collect_segmented_candidates`), inheriting a list item's own subject
from its chapeau where the codebook's own chapeau rule applies; (2) finalise EVERY
candidate's own subj/obj spans FIRST (`extract.spans`: whitespace-trim,
strip ONE leading determiner, strip a leading modal where the rule says
to, truncate a mid-span-modal bleed-over) and drop any candidate that
collapses to an empty span or fails `five_d_nd.statement.
statement_violations()` — BEFORE any overlap check (required fix 3: a
candidate that turns out empty must never block a LATER candidate, e.g.
the last-resort whole-unit fallback, from claiming that same span); (3)
resolve overlap among the SURVIVING, already-finalised candidates, by
RULE ORDER, except for a pair of predicates `extract.rules.
CO_CODABLE_PREDICATE_PAIRS` explicitly allows to co-code the same clause
span (`requires`+`deadline_of`, `requires`+`precedes` — the codebook's
own "Temporal vs causal" rule); (4) sort the result by `five_d_nd.
statement.canonical_sort_key`.

``extract_with_spans()`` is this pipeline's own full output: one
`BuiltStatement` per surviving candidate, pairing the schema-valid
Statement dict with its own internal spans (clause/subj/obj) — kept
SEPARATE from the Statement dict itself, never folded into it (required
fix 1: a Statement `extract()` returns is schema-valid AS IS, with
`additionalProperties: false`, and carries no extractor-internal field).
``extract()`` is the thin, schema-only view: just the Statement dicts.

Determinism: every step above is pure stdlib `re` + arithmetic over a
fixed string; the SAME ``unit_text`` input always walks the SAME rules
in the SAME order and produces BYTE-IDENTICAL output.

Stdlib only; imports `five_d_nd.statement` (read-only) and this
package's own `rules`/`spans`/`negation` modules.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .. import statement as _statement
from . import negation as _negation
from . import spans as _spans
from .rules import Candidate, CO_CODABLE_PREDICATE_PAIRS, collect_segmented_candidates

__all__ = [
    "ExtractionDiagnostics",
    "BuiltStatement",
    "resolve_overlaps_built",
    "layer_of",
    "finalize_candidate_spans",
    "build_statement",
    "extract_with_spans",
    "extract",
]


class ExtractionDiagnostics:
    """Counters the eval harness (and this session's own report) reads
    back — never consulted by :func:`extract` itself to change
    behaviour, purely descriptive."""

    __slots__ = ("n_candidates", "n_finalize_dropped", "n_overlap_dropped")

    def __init__(self):
        self.n_candidates = 0
        self.n_finalize_dropped = 0
        self.n_overlap_dropped = 0


@dataclass(frozen=True)
class BuiltStatement:
    """One finalised Statement, paired with its OWN internal spans — kept
    separate from the schema-valid ``statement`` dict itself (required
    fix 1). ``spans`` is ``{"clause": (start, end), "subj": (start, end),
    "obj": (start, end)}``, every value a tuple of ints into the ORIGINAL
    ``unit_text`` `extract_with_spans()` was called with."""
    statement: dict
    spans: dict
    chapeau_group: Optional[str] = None


def _overlaps(a: tuple, b: tuple) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def resolve_overlaps_built(
    built: "list[BuiltStatement]", diagnostics: Optional[ExtractionDiagnostics] = None,
) -> "list[BuiltStatement]":
    """First-claimed-span-wins overlap resolution over ALREADY-FINALISED
    `BuiltStatement`s, in LIST order (the rule precedence `extract.rules.
    RULES` already encodes) — a statement whose own clause span overlaps
    one already accepted is dropped, UNLESS the two predicates are a
    `extract.rules.CO_CODABLE_PREDICATE_PAIRS` member (the codebook's own
    explicit co-coding allowance), in which case both are kept."""
    accepted: "list[BuiltStatement]" = []
    accepted_entries: "list[tuple]" = []  # (span, predicate, chapeau_group)
    for b in built:
        span = b.spans["clause"]
        pred = b.statement["predicate"]
        group = b.chapeau_group
        conflict = False
        for other_span, other_pred, other_group in accepted_entries:
            if group is not None and group == other_group:
                continue  # same chapeau list — never a conflict with its own siblings
            if _overlaps(span, other_span) and frozenset({pred, other_pred}) not in CO_CODABLE_PREDICATE_PAIRS:
                conflict = True
                break
        if conflict:
            if diagnostics is not None:
                diagnostics.n_overlap_dropped += 1
            continue
        accepted.append(b)
        accepted_entries.append((span, pred, group))
    return accepted


#: A clause carrying an EXPLICIT purpose cue with no `enclosing_
#: provision` metadata and no modal anywhere in the unit
#: (`rules.MODAL_ANYWHERE_RE`) is routed to `legislative_purpose_of` BY
#: THE RULE ITSELF — the FALLBACK-ONLY recital-position signature used
#: when no metadata is given. Reused here, fallback-only, for `layer`.
_SURFACE_DEFAULT_PREDICATES_FALLBACK = frozenset({"legislative_purpose_of"})


def layer_of(predicate: str, enclosing_provision: Optional[str] = None) -> str:
    """The codebook's own 4-step layer rule (`docs/codebook/
    typed-statements-v1.md`, "Layer — surface, domain, deep"), applied AS
    FAR AS ``enclosing_provision`` lets it be. Rule 1 ("a definition...
    -> deep") is reproduced exactly: `is_a` is always `"deep"`. Rule 3
    ("a recital -> surface, unless rule 1/2 already applies") is
    reproduced exactly WHEN ``enclosing_provision`` is given — a string
    whose own lowercase form contains ``"recital"`` routes to
    `"surface"`; anything else operative routes to rule 4, `"domain"`.
    Rule 2 ("a principle stated as a principle -> deep") has NO reliable
    text-only signal and is NOT attempted even with metadata (an open
    item — see `docs/decisions/0010-deterministic-extractor.md`).

    When ``enclosing_provision`` is `None` (the metadata-FREE call
    shape, round-2 item 8's own backwards-compatible default), this
    falls back to the PRE-metadata heuristic: `legislative_purpose_of`
    (itself already routed by the "no modal anywhere" fallback signal)
    defaults to `"surface"`; everything else defaults to `"domain"`
    (rule 4), which is the correct call for the large majority of real
    operative-article text."""
    if predicate == "is_a":
        return "deep"
    if enclosing_provision:
        return "surface" if "recital" in enclosing_provision.lower() else "domain"
    if predicate in _SURFACE_DEFAULT_PREDICATES_FALLBACK:
        return "surface"
    return "domain"


def finalize_candidate_spans(unit_text: str, cand: Candidate) -> "Optional[tuple]":
    """The span-finalisation pipeline a `Candidate`'s own raw subj/obj
    spans go through (mid-span-modal truncation, the subject+modal
    strip, determiner/modal stripping) — factored out of
    `build_statement` so `extract.hybrid.propose()` can apply the EXACT
    same finalisation to a candidate BEFORE it ever reaches the
    CandidateSet (R-k/R-q: a candidate the decider sees should already
    be modal- and determiner-free, the same as the non-hybrid pipeline's
    own Statements, not a raw regex capture). Returns ``(subj_span,
    obj_span)`` or ``None`` if either collapses to nothing."""
    if cand.truncate_midspan_modal:
        raw_subj_span = _spans.truncate_before_modal(unit_text, *cand.subj_span) if cand.subj_span else None
        raw_obj_span = _spans.truncate_before_modal(unit_text, *cand.obj_span) if cand.obj_span else None
    else:
        raw_subj_span = cand.subj_span
        raw_obj_span = cand.obj_span
    if cand.strip_subject_and_modal_obj and raw_obj_span is not None:
        raw_obj_span = _spans.strip_subject_and_modal_prefix(unit_text, *raw_obj_span)
    subj_span = _spans.finalize_endpoint_span(
        unit_text, *raw_subj_span, strip_det=True, strip_modal=cand.strip_modal_subj,
    ) if raw_subj_span else None
    obj_span = _spans.finalize_endpoint_span(
        unit_text, *raw_obj_span, strip_det=True, strip_modal=cand.strip_modal_obj,
    ) if raw_obj_span else None
    if subj_span is None or obj_span is None:
        return None
    return (subj_span, obj_span)


def build_statement(
    unit_text: str, cand: Candidate, *, instrument_uri: str = "extracted-unit",
    consolidation_date: str = "n/a", negation_version: str = _negation.DEFAULT_NEGATION_VERSION,
    enclosing_provision: Optional[str] = None,
) -> Optional[BuiltStatement]:
    """One finalised, schema-validated §21 Statement, paired with its own
    spans, from ``cand`` — or ``None`` if the candidate's own spans
    collapse to nothing once finalised, or the resulting Statement fails
    its own `statement_violations()` check (dropped, never emitted
    malformed)."""
    finalized = finalize_candidate_spans(unit_text, cand)
    if finalized is None:
        return None
    subj_span, obj_span = finalized

    subj_text = _spans.span_text(unit_text, subj_span)
    obj_text = _spans.span_text(unit_text, obj_span)
    if not subj_text or not obj_text:
        return None

    clause_start = min(cand.clause_span[0], subj_span[0], obj_span[0])
    clause_end = max(cand.clause_span[1], subj_span[1], obj_span[1])
    clause_span = (clause_start, clause_end)

    negation = _negation.negate(
        unit_text, clause_span, subj_span, cand.predicate,
        version=negation_version, force=cand.negation_force,
    )

    dimension = _statement.PREDICATE_DIMENSION[cand.predicate]
    layer = layer_of(cand.predicate, enclosing_provision)
    confidence = round(min(1.0, max(0.0, cand.base_confidence)), 6)

    id_source = _statement.normalize_statement_text(
        f"{cand.predicate}|{subj_text}|{obj_text}|{clause_span[0]}-{clause_span[1]}"
    )
    stmt_id = _statement.statement_id(
        instrument_uri, consolidation_date, _statement.text_hash(id_source)
    )

    doc = {
        "id": stmt_id,
        "subj": subj_text,
        "obj": obj_text,
        "predicate": cand.predicate,
        "dimension": dimension,
        "layer": layer,
        "weight": 1.0,
        "edge_confidence": confidence,
        "provenance": {"start": clause_span[0], "end": clause_span[1]},
        "negation": negation,
        "extraction_rule_id": cand.rule_id,
    }
    if not _statement.is_valid_statement(doc):
        return None
    return BuiltStatement(
        statement=doc, spans={"clause": clause_span, "subj": subj_span, "obj": obj_span},
        chapeau_group=cand.chapeau_group,
    )


def extract_with_spans(
    unit_text: str, *, instrument_uri: str = "extracted-unit", consolidation_date: str = "n/a",
    negation_version: str = _negation.DEFAULT_NEGATION_VERSION,
    enclosing_provision: Optional[str] = None,
    diagnostics: Optional[ExtractionDiagnostics] = None,
) -> "list[BuiltStatement]":
    """The full extraction pipeline, returning EVERY surviving `BuiltStatement`
    (Statement + its own internal spans) — the shape a caller that needs
    spans (the dev-eval harness's own pairing/scoring code) should use;
    `extract()`, below, is the schema-only view built from this.

    ``enclosing_provision`` (round-2 item 8, OPTIONAL, backwards-
    compatible — `None` preserves the pre-existing metadata-free
    behaviour exactly) is the unit's own enclosing-provision label (e.g.
    `"GDPR recital 71"`, `"GDPR Art 4"`) — forwarded to `extract.rules.
    collect_segmented_candidates` (segmentation, purpose-predicate
    routing) and to `layer_of` (the codebook's own recital/article layer
    rule)."""
    if not isinstance(unit_text, str):
        raise ValueError("extract_with_spans() requires a string")
    if diagnostics is None:
        diagnostics = ExtractionDiagnostics()

    candidates = collect_segmented_candidates(unit_text, enclosing_provision=enclosing_provision)
    diagnostics.n_candidates += len(candidates)

    built: "list[BuiltStatement]" = []
    for cand in candidates:
        b = build_statement(
            unit_text, cand, instrument_uri=instrument_uri,
            consolidation_date=consolidation_date, negation_version=negation_version,
            enclosing_provision=enclosing_provision,
        )
        if b is None:
            diagnostics.n_finalize_dropped += 1
            continue
        built.append(b)

    accepted = resolve_overlaps_built(built, diagnostics)
    accepted.sort(key=lambda b: _statement.canonical_sort_key(b.statement))
    return accepted


def extract(
    unit_text: str, *, instrument_uri: str = "extracted-unit", consolidation_date: str = "n/a",
    negation_version: str = _negation.DEFAULT_NEGATION_VERSION,
    enclosing_provision: Optional[str] = None,
    diagnostics: Optional[ExtractionDiagnostics] = None,
) -> "list[dict]":
    """The extractor's own contract function: deterministic, pure-stdlib, same input
    -> byte-identical output. Returns ONLY schema-valid §21 Statement
    dicts — exactly what `schema/statement.schema.json` accepts, with its
    own `additionalProperties: false`, and NO extractor-internal field
    (required fix 1). A caller that needs the underlying spans (e.g. for
    pairing against another coder's own spans) calls
    :func:`extract_with_spans` instead and reads `BuiltStatement.spans`.

    ``instrument_uri``/``consolidation_date`` are OPTIONAL — a caller
    outside a real instrument pipeline gets a valid, schema-conformant
    placeholder id instead of a `ValueError`. ``enclosing_provision`` is
    the OPTIONAL, backwards-compatible metadata-aware keyword (round-2
    item 8) — see :func:`extract_with_spans`'s own docstring.
    ``negation_version`` selects the registered `extract.negation` rule.

    Returns Statements SORTED by `five_d_nd.statement.canonical_sort_key`
    — never the raw rule-application order."""
    built = extract_with_spans(
        unit_text, instrument_uri=instrument_uri, consolidation_date=consolidation_date,
        negation_version=negation_version, enclosing_provision=enclosing_provision,
        diagnostics=diagnostics,
    )
    return [b.statement for b in built]
