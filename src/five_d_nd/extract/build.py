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

import re
from dataclasses import dataclass, replace
from typing import Optional

from .. import statement as _statement
from . import negation as _negation
from . import spans as _spans
from .rules import (
    Candidate,
    CO_CODABLE_PREDICATE_PAIRS,
    collect_segmented_candidates,
    normalize_deadline_text,
    type_recipient_actor,
)

#: v3.6: per-predicate obj-text POST-PROCESSING, applied
#: AFTER ordinary span finalisation (determiner/modal strip) and BEFORE
#: the Statement id is hashed — `addressed_to`'s own recipient TYPING
#: step (the closed ACTOR_ROLES token, or `other(label)`) and
#: `deadline_of`'s own deadline NORMALISATION step (the bare limit,
#: "after ..." dropped) are deterministic rewrites of the ALREADY
#: span-derived text, never a second, independent guess — every other
#: predicate's own obj is untouched (an empty dict lookup is a no-op).
#: `extract.hybrid`'s own decider-driven `assemble()` does NOT apply
#: this table — a human/model decider's final span choice there is
#: reconstructed via `spans.span_text` alone, the same as every other
#: predicate, by design (see `extract.hybrid`'s own module docstring);
#: only this deterministic rule-layer pipeline types/normalises.
_OBJ_TEXT_POSTPROCESS: "dict" = {
    "addressed_to": type_recipient_actor,
    "deadline_of": normalize_deadline_text,
}

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
    """Counters the eval harness (and a caller's own report) reads
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
    #: v3.6: carried from `rules.Candidate.never_conflicts`
    #: — see that field's own docstring. Read by
    #: :func:`resolve_overlaps_built` only; never written anywhere else.
    never_conflicts: bool = False


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
    explicit co-coding allowance), in which case both are kept.

    A `BuiltStatement` with its own ``never_conflicts`` set
    (`addressed_to`, every `deadline_of`) is EXEMPT from this check on
    BOTH sides, UNCONDITIONALLY: it is always accepted (never dropped
    for "overlapping" the very host clause it is a derived, layered
    reading OF), and it never counts as a conflict for ANY later
    candidate either — including a scan span's own last-resort
    fallback (`predication`), which must stay exactly as likely to
    survive as it always was: a `never_conflicts` candidate never
    existed before this predicate/cue was added, so a clause it is
    drawn from never had anything NEW blocking what used to survive
    there. Every pre-existing, non-`never_conflicts` predicate keeps
    its own ORIGINAL first-claimed-span-wins behaviour, completely
    unaffected — including its own ability to block, or be blocked by,
    another non-`never_conflicts` predicate exactly as before.
    ``never_conflicts`` is a PURE ADDITION to what a clause already
    produced; it is never a second reason an existing Statement stops
    being produced."""
    accepted: "list[BuiltStatement]" = []
    accepted_entries: "list[tuple]" = []  # (span, predicate, chapeau_group, never_conflicts)
    for b in built:
        span = b.spans["clause"]
        pred = b.statement["predicate"]
        group = b.chapeau_group
        exempt = b.never_conflicts
        conflict = False
        if not exempt:
            for other_span, other_pred, other_group, other_exempt in accepted_entries:
                if other_exempt:
                    continue  # an exempt entry never blocks anything else
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
        accepted_entries.append((span, pred, group, exempt))
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
    postprocess = _OBJ_TEXT_POSTPROCESS.get(cand.predicate)
    if postprocess is not None:
        obj_text = postprocess(obj_text)
        if not obj_text:
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
        chapeau_group=cand.chapeau_group, never_conflicts=cand.never_conflicts,
    )


#: v3.6: the predicates a `deadline_of` Statement's own subject is
#: REBOUND to (`_rebind_deadline_subjects`, below), in priority order.
#: `addressed_to`'s own ``subj`` (the act it is itself drawn from) is
#: tried FIRST — it is already the innermost, most specific act a
#: companion Statement from the SAME clause can name; `performs`/
#: `competence_of`'s own ``obj`` (the act they name) comes next;
#: `requires`'s own ``obj`` (the consequence ACT a trigger produces —
#: the pre-existing, pre-v3.6 "requires coordinates with deadline_of"
#: codebook rule, `CO_CODABLE_PREDICATE_PAIRS`) comes next, SUBJECT to
#: :func:`_is_trustworthy_requires_companion`'s own guard below (a
#: `requires` candidate whose own ``subj`` collapsed to a single word,
#: "applicable", is itself a MISFIRE on a parenthetical aside, never a
#: genuine trigger/consequence reading) AND to the ANTECEDENT-vs-
#: consequence check in `_rebind_deadline_subjects` itself — a time limit inside the antecedent is NEVER bound to
#: the consequence. `except_when`'s own ``obj`` (the exception
#: condition — "unless X opposes ... not later than N", where the
#: deadline sits INSIDE the exception condition itself, not the
#: general rule) is the last resort.
_DEADLINE_SUBJECT_SOURCE_PRIORITY: "tuple[str, ...]" = (
    "addressed_to", "performs", "competence_of", "requires", "except_when",
)


#: `T3-requires-subject-to-condition` ("subject to [a condition]")
#: routinely fires on a DESCRIPTIVE qualifier ("whose decision is
#: binding and subject to judicial review, for the use of that
#: system, except when...") that is not a genuine trigger/consequence
#: clause at all — its own ``obj`` in that case is whatever text
#: happens to follow the "subject to" phrase, never a real consequence
#: ACT. Never trusted as a `deadline_of` companion.
_UNTRUSTED_REQUIRES_RULE_IDS = frozenset({"T3-requires-subject-to-condition"})


def _is_trustworthy_requires_companion(statement: dict) -> bool:
    """A `requires` Statement is trusted as a `deadline_of` companion
    only when (1) its own ``subj`` (the antecedent) is more than a
    single word — a one-word antecedent ("applicable") is the
    signature of `_WHERE_IF_RE` firing on a short parenthetical aside
    rather than a genuine trigger/consequence clause, and its own
    ``obj`` in that case names the clause AFTER the aside, not a real
    consequence ACT — and (2) its own rule id is not one of
    :data:`_UNTRUSTED_REQUIRES_RULE_IDS`."""
    if statement["extraction_rule_id"] in _UNTRUSTED_REQUIRES_RULE_IDS:
        return False
    return len(statement["subj"].split()) > 1


#: `except_when`'s own "notwithstanding [provision]"/"subject to
#: [provision]" cue family (`T3-except_when-notwithstanding-provision`,
#: `T3-except_when-subject-to-provision`, and its own chapeau/list-item
#: variants) names a bare PROVISION REFERENCE as its own ``obj``
#: ("paragraph 2", "Article 9") — never an act, and a far WORSE
#: `deadline_of` companion than even the passive-act fallback. Only
#: the "unless"/"except where" cue family's own ``obj`` (a genuine
#: exception CONDITION, "the European Parliament or the Council
#: opposes such extension") is trusted.
_TRUSTED_EXCEPT_WHEN_RULE_IDS = frozenset({
    "T3-except_when-unless", "T3-except_when-except-where",
})


def _is_trustworthy_except_when_companion(statement: dict) -> bool:
    """An `except_when` Statement is trusted as a `deadline_of`
    companion only when its own rule id is one of
    :data:`_TRUSTED_EXCEPT_WHEN_RULE_IDS` — the "unless"/"except
    where" cue family, whose own ``obj`` is a genuine exception
    condition, never a bare provision reference."""
    return statement["extraction_rule_id"] in _TRUSTED_EXCEPT_WHEN_RULE_IDS


def _governed_act_text(statement: dict) -> str:
    """The ACT text a companion Statement (one of
    :data:`_DEADLINE_SUBJECT_SOURCE_PRIORITY`'s own members) itself
    names: `addressed_to`'s own ``subj`` (the act or communication it
    is drawn from), or ``obj`` for every other member (`performs`/
    `competence_of`'s own act)."""
    if statement["predicate"] == "addressed_to":
        return statement["subj"]
    return statement["obj"]


#: v3.6: the LAST-RESORT governed-act fallback, tried only when NO
#: `performs`/`competence_of`/`addressed_to` companion shares a clause
#: with a `deadline_of` candidate (`_find_passive_act_phrase`, below)
#: — a PASSIVE construction naming the act without a performs-style
#: actor subject at all ("the report ... shall be made", "a final
#: report ... shall be provided"): common in a chapeau's own numbered
#: paragraph ("2. The report referred to in paragraph 1 shall be made
#: ..., not later than 15 days after ...").
_PASSIVE_ACT_RE = re.compile(r"\bshall\s+be\s+[a-z]+\b", re.IGNORECASE)
_SENTENCE_START_RE = re.compile(r"[.]\s*")


def _find_passive_act_phrase(unit_text: str, near_span: tuple) -> Optional[str]:
    """The text from the nearest SENTENCE start at or before
    ``near_span`` through the end of a `_PASSIVE_ACT_RE` match found
    within that same sentence (searched over the WHOLE sentence, not
    just before ``near_span`` — the passive verb phrase is usually the
    sentence's own main verb, named once near its own start, with the
    deadline duration following much later in the same sentence).
    Returns ``None`` if no such sentence or no such passive verb
    phrase is found."""
    sent_start = 0
    for m in _SENTENCE_START_RE.finditer(unit_text, 0, near_span[0]):
        sent_start = m.end()
    sent_end_match = _SENTENCE_START_RE.search(unit_text, near_span[1])
    sent_end = sent_end_match.start() if sent_end_match else len(unit_text)
    sentence = unit_text[sent_start:sent_end]
    pm = _PASSIVE_ACT_RE.search(sentence)
    if pm is None:
        return None
    act_text = _spans.span_text(unit_text, (sent_start, sent_start + pm.end()))
    return act_text or None


#: v3.6: a SECOND companion search, tried when
#: :func:`_spans_share_a_clause` finds nothing — a chapeau + lettered-
#: list structure ("the entities concerned submit to the CSIRT or...:
#: (a) ...; (b) without undue delay ... within 72 hours ..., an
#: incident notification...; ...") names the governing act ONCE, in
#: the chapeau, before the colon that opens the list; every list
#: item's own deadline is still governed by THAT act, even though a
#: ``;``-separated sibling item sits in between (the general
#: :func:`_spans_share_a_clause` deliberately treats ``;`` as a hard
#: boundary everywhere else, so this is a NARROWLY SCOPED exception,
#: not a loosening of that rule). Finds the nearest ``:`` before
#: ``deadline_span`` (bounded by the nearest preceding PARAGRAPH start,
#: a sentence-ending ``.``, so this never reaches into a PRIOR
#: paragraph's own chapeau), then the first companion whose own clause
#: starts at or shortly after that colon.
_CHAPEAU_COLON_RE = re.compile(r":")
_CHAPEAU_TRIGGER_LOOKAHEAD = 80


def _chapeau_trigger_companion(
    unit_text: str, deadline_span: tuple, built: "list[BuiltStatement]",
) -> "Optional[BuiltStatement]":
    para_start = 0
    for m in _SENTENCE_START_RE.finditer(unit_text, 0, deadline_span[0]):
        para_start = m.end()
    colon_idx = None
    for m in _CHAPEAU_COLON_RE.finditer(unit_text, para_start, deadline_span[0]):
        colon_idx = m.start()
    if colon_idx is None:
        return None
    window_end = colon_idx + _CHAPEAU_TRIGGER_LOOKAHEAD
    for pred in _DEADLINE_SUBJECT_SOURCE_PRIORITY:
        for other in built:
            if other.statement["predicate"] != pred:
                continue
            if pred == "requires" and not _is_trustworthy_requires_companion(other.statement):
                continue
            start = other.spans["clause"][0]
            if para_start <= start <= window_end:
                return other
    return None


#: v3.6: the longest GAP (in characters) between a `deadline_of`
#: Statement's own clause span and a candidate companion's own clause
#: span that still counts as "the same clause" for
#: :func:`_spans_share_a_clause`, below — bounds how far the binding
#: search reaches so it never crosses into an unrelated, merely
#: nearby sentence.
_SAME_CLAUSE_MAX_GAP = 200
_SENTENCE_BOUNDARY_RE = re.compile(r"[.;:]")


def _spans_share_a_clause(unit_text: str, span_a: tuple, span_b: tuple) -> bool:
    """True when ``span_a``/``span_b`` belong to the SAME clause: they
    already overlap, OR the GAP between them (whichever one ends
    first to whichever one starts second) is both SHORT
    (:data:`_SAME_CLAUSE_MAX_GAP`) and crosses no sentence-ending
    punctuation (``.``/``;``/``:``) — the same boundary signal
    `rules._clause_start_before` already uses elsewhere. A deadline
    cue and the act it times routinely sit in the SAME grammatical
    clause but in DIFFERENT regex capture groups (the duration phrase
    before the verb, "not later than 72 hours ..., notify ..."; or
    after it, "notify ... to X ... within 72 hours") — adjacent,
    comma-separated, never literally overlapping spans."""
    if _overlaps(span_a, span_b):
        return True
    lo = min(span_a[1], span_b[1])
    hi = max(span_a[0], span_b[0])
    if hi <= lo:
        return True
    if hi - lo > _SAME_CLAUSE_MAX_GAP:
        return False
    return not _SENTENCE_BOUNDARY_RE.search(unit_text, lo, hi)


def _rebind_deadline_subjects(
    unit_text: str, built: "list[BuiltStatement]", *, instrument_uri: str, consolidation_date: str,
) -> "list[BuiltStatement]":
    """v3.6's own deadline-subject BINDING rule: a `deadline_of`
    Statement's own ``subj`` is NEVER a clause subject, a sentence
    fragment, a connective, or a pronoun (`_clause_start_before`'s own
    "whatever the clause said so far" convention, correct for naming
    an ACTOR but wrong for naming the ACT a time limit attaches to) —
    it is REBOUND here to the GOVERNED ACT: the first companion
    Statement, among :data:`_DEADLINE_SUBJECT_SOURCE_PRIORITY`'s own
    members, that SHARES A CLAUSE (:func:`_spans_share_a_clause`) with
    this `deadline_of` Statement — or, failing that, the passive-act
    phrase :func:`_find_passive_act_phrase` finds in the SAME
    sentence. When NEITHER exists — the deadline names no act this
    extractor can bind inside the same clause — the `deadline_of`
    Statement is DROPPED outright (emits nothing) rather than keep a
    `subj` known to be wrong. Every non-`deadline_of` Statement passes
    through UNCHANGED. Rebinding
    the `subj` changes the Statement's own id (the id hashes
    `predicate|subj|obj|span`), recomputed here the same way
    `build_statement` computes it the first time."""
    deadline_stmts = [b for b in built if b.statement["predicate"] == "deadline_of"]
    if not deadline_stmts:
        return built
    out: "list[BuiltStatement]" = []
    for b in built:
        if b.statement["predicate"] != "deadline_of":
            out.append(b)
            continue
        span = b.spans["clause"]
        companion = None
        antecedent_case = False
        for pred in _DEADLINE_SUBJECT_SOURCE_PRIORITY:
            if pred == "requires":
                for other in built:
                    if other is b or other.statement["predicate"] != "requires":
                        continue
                    if not _is_trustworthy_requires_companion(other.statement):
                        continue
                    # A `requires` reading has
                    # TWO halves — the antecedent (subj) and the
                    # consequence (obj) — and a time limit can sit in
                    # EITHER. "Where the request is not answered
                    # within 30 days, the application shall be deemed
                    # accepted" times the ANTECEDENT ("not answered"),
                    # never the consequence ("accepted") — binding to
                    # the consequence is WRONG even though it is a
                    # genuine governed act, because it is not the ONE
                    # this deadline actually times. Checked by LITERAL
                    # overlap first (the deadline's own span, from
                    # `_clause_start_before`, is typically CONTAINED
                    # inside whichever half it times), falling back to
                    # :func:`_spans_share_a_clause` only for the
                    # consequence side when neither half literally
                    # overlaps.
                    subj_hit = _overlaps(span, other.spans["subj"])
                    obj_hit = _overlaps(span, other.spans["obj"])
                    if subj_hit:
                        antecedent_case = True
                        break
                    if obj_hit:
                        companion = other
                        break
                    if _spans_share_a_clause(unit_text, span, other.spans["obj"]):
                        companion = other
                        break
                if companion is not None or antecedent_case:
                    break
                continue
            for other in built:
                if other is b or other.statement["predicate"] != pred:
                    continue
                if pred == "except_when" and not _is_trustworthy_except_when_companion(other.statement):
                    continue
                if _spans_share_a_clause(unit_text, span, other.spans["clause"]):
                    companion = other
                    break
            if companion is not None:
                break
        if antecedent_case:
            # The deadline times the antecedent,
            # but this extractor has no clean, separately-extracted
            # text for "just the antecedent's own act" (the `requires`
            # candidate's own `subj` is the WHOLE antecedent, deadline
            # phrase included) — rather than guess at trimming it,
            # keep this Statement's own ORIGINAL, pre-rebind `subj`
            # UNCHANGED (it already reads as "Where/If ... is not
            # made/answered ...", the antecedent clause itself, not a
            # fragment/connective/pronoun) and never replace it with
            # the WRONG consequence, and never drop it either.
            out.append(b)
            continue
        if companion is None:
            companion = _chapeau_trigger_companion(unit_text, span, built)
        if companion is not None:
            new_subj = _governed_act_text(companion.statement)
        else:
            new_subj = _find_passive_act_phrase(unit_text, span)
        if not new_subj:
            # The pre-existing, pre-v3.6 digit-
            # based "within N" cue (`b.never_conflicts` False — see
            # `rules._find_deadline_of`) already EXISTED, with this
            # exact subj, before v3.6; finding no governed act to
            # rebind it to is never a licence to REMOVE a Statement
            # main already had — keep it UNCHANGED, the same "keep any
            # pre-existing edge unchanged rather than replacing it"
            # principle the antecedent case above already applies.
            # Only a NEW cue (`never_conflicts` True — nothing on main
            # ever produced this Statement in the first place) is
            # dropped outright when no governed act can be bound.
            if not b.never_conflicts:
                out.append(b)
            continue
        new_statement = dict(b.statement)
        new_statement["subj"] = new_subj
        id_source = _statement.normalize_statement_text(
            f"{new_statement['predicate']}|{new_subj}|{new_statement['obj']}|{span[0]}-{span[1]}"
        )
        new_statement["id"] = _statement.statement_id(
            instrument_uri, consolidation_date, _statement.text_hash(id_source)
        )
        if not _statement.is_valid_statement(new_statement):
            continue
        out.append(replace(b, statement=new_statement))
    return out


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
    accepted = _rebind_deadline_subjects(
        unit_text, accepted, instrument_uri=instrument_uri, consolidation_date=consolidation_date,
    )
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
