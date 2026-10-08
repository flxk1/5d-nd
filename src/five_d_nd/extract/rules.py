# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""The extractor's own closed, deterministic predicate-cue rule table.

Every rule below is written FROM THE CODEBOOK's own prose
(`docs/codebook/typed-statements-v1.md`, read-only — not edited by this
session). Each rule's own section comment cites the codebook heading it
was written from — see :data:`RULE_CITATIONS` for a machine-checkable
index (`tests/test_extract.py::test_every_rule_id_has_a_citation` asserts
every ``rule_id`` this module can emit has a non-empty entry there). Two
rules genuinely REUSE `five_d_nd.clause_cues` objects (read-only,
imported, never copied or re-derived) rather than merely being "modelled
after" its vocabulary: `cross_references`'s own "referred to in Article
N" rule matches the citation span with `clause_cues.ARTICLE_REF_RE`
itself (the exact compiled pattern object, not a re-typed copy), and
`performs`/`competence_of`'s own actor-NP fragment is built from
`five_d_nd.statement.ACTOR_ROLES` (also read-only, imported) rather than
a hand-typed actor list. No rule's own pattern text is, or was derived
by inspecting, any gold unit's surface wording; every example above 10
characters in a rule's own docstring, if any, is either the codebook's
own prose or a brand-new phrase typed by this session, never a
>=60-character verbatim quote from the local corpus (the held-out-data
hard rule).

Each rule is a plain Python object: a compiled regex searched directly
over the FULL unit text (this extractor does not run a separate
constituency-aware clause segmenter — the matched regex SPAN doubles as
the clause span; a handful of mechanical boundary signals — sentence end,
`;`, `:`, a leading list-item marker, a later clause's own leading modal —
bound a capture group's own run-on, but this is NOT the codebook's own
chapeau/coordination grammar; see `docs/decisions/
0010-deterministic-extractor.md` for what that trades away). A rule
names which of its own capture groups is `subj` and which is `obj`;
`None` on either side means a later processing step supplies that
endpoint from context (surrounding text) rather than from the regex
itself. Overlap between two candidate clause spans is resolved by RULE
ORDER, AFTER span finalisation (`extract.build.extract_with_spans`) — a
SPECIFIC, documented pair of predicates (`CO_CODABLE_PREDICATE_PAIRS`,
below) is explicitly allowed to co-code the SAME clause span, per the
codebook's own "Temporal vs causal" decision rule.

A rule function's own second parameter, ``context``, is a plain dict
(``{"enclosing_provision": <str or None>}`` today) — the metadata-aware
`extract()` signature's own channel into a rule that needs it (currently
only the purpose-predicate router); every other rule ignores it.

Stdlib only; imports `five_d_nd.statement` and `five_d_nd.clause_cues`
(both read-only).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Callable, Optional

from .. import clause_cues as _clause_cues
from .. import statement as _statement_mod
from . import segment as _segment

__all__ = [
    "Candidate",
    "Rule",
    "RULES",
    "RULE_CITATIONS",
    "CO_CODABLE_PREDICATE_PAIRS",
    "INSTITUTIONAL_ACTOR_SURFACE_RE",
    "ACTOR_NP_FRAGMENT",
    "MODAL_ANYWHERE_RE",
    "collect_candidates",
    "collect_segmented_candidates",
]


@dataclass(frozen=True)
class Candidate:
    """One candidate Statement, BEFORE span finalisation (determiner/modal
    stripping — `extract.spans`) and BEFORE negation is assigned. Spans
    are raw ``(start, end)`` character offsets into the unit text, or
    ``None`` when the rule that produced this candidate could not supply
    that endpoint (the candidate is then dropped — see
    `extract.build.extract_with_spans`)."""
    rule_id: str
    predicate: str
    clause_span: tuple
    subj_span: Optional[tuple]
    obj_span: Optional[tuple]
    strip_modal_subj: bool = False
    strip_modal_obj: bool = False
    #: R-k: strip a leading REPEATED-SUBJECT +
    #: MODAL prefix from the obj span (`extract.spans.
    #: strip_subject_and_modal_prefix`) — for a `requires` consequence
    #: captured as the clause's own full remainder ("the operator shall
    #: notify..."), leaving only the ACT. A no-op when the span never had
    #: such a prefix.
    strip_subject_and_modal_obj: bool = False
    negation_force: Optional[str] = None
    base_confidence: float = 0.5
    #: True for a predicate whose captured span should NEVER legitimately
    #: contain a modal verb at all — a modal found strictly inside such a
    #: span is almost always the NEXT clause's own leading modal bleeding
    #: into a bounded-but-greedy capture group, so `extract.build`
    #: truncates there (`spans.truncate_before_modal`). False for a
    #: predicate whose own regex can legitimately capture a REPEATED
    #: subject before the clause's own modal — this extractor's simple
    #: regex grammar does not strip that repeated subject (a documented
    #: limitation, not a bleed-over bug), so truncating there would
    #: destroy real content instead of fixing anything.
    truncate_midspan_modal: bool = True
    #: Non-``None`` only for a chapeau-list item (the "subject to—"
    #: multi-item rule, today): candidates sharing the SAME
    #: ``chapeau_group`` are, BY DESIGN, never a conflict for each other
    #: in `extract.build`'s own overlap resolution, even though their own
    #: finalised clause spans all share the SAME inherited `subj` prefix
    #: (and therefore all nominally "overlap" there) — the codebook's own
    #: chapeau-list rule explicitly produces MULTIPLE Statements, one per
    #: listed item, sharing one subject.
    chapeau_group: Optional[str] = None


@dataclass(frozen=True)
class Rule:
    """One entry in :data:`RULES`: ``finder(unit_text, context) ->
    list[Candidate]``. A rule is a FUNCTION, not just a pattern, so a
    rule needing context-dependent span logic (`deadline_of`'s own
    "whatever precedes the cue", `competence_of`'s own institutional-
    actor gate, `legislative_purpose_of`/`compliance_purpose_of`'s own
    enclosing-provision routing) can still live in this one closed
    table."""
    rule_id: str
    finder: Callable[[str, dict], "list[Candidate]"]


#: Predicate PAIRS the codebook explicitly permits to CO-CODE the SAME
#: clause span — "Temporal vs causal — a clause MAY need BOTH `requires`
#: and a temporal predicate... when the SAME clause ALSO carries a bare
#: ordering word OR a duration phrase, the coder produces TWO (or three)
#: Statements from the one clause: `requires` for the trigger->
#: consequence, PLUS `precedes` and/or `deadline_of` for whichever
#: temporal content is also present." (`docs/codebook/
#: typed-statements-v1.md`, "Decision rules for the hard boundaries").
#: `extract.build`'s own overlap resolution consults this set BEFORE
#: rejecting an overlapping candidate — an overlap between two
#: predicates named here is NOT a conflict.
CO_CODABLE_PREDICATE_PAIRS: "frozenset[frozenset]" = frozenset({
    frozenset({"requires", "deadline_of"}),
    frozenset({"requires", "precedes"}),
})


# ─────────────────────── actor vocabulary (performs/competence_of) ──────
#: codebook: "competence_of — relational" + "performs — relational"
#: (`docs/codebook/typed-statements-v1.md`). Built from
#: `five_d_nd.statement.ACTOR_ROLES` (the CLOSED §21 entity/actor
#: vocabulary, read-only, imported) rather than a hand-typed surface
#: list — every role this extractor can route to `performs`/
#: `competence_of` is drawn from that one closed set.
_IRREGULAR_LAST_TOKEN_PLURAL = {
    "authority": r"authorit(?:y|ies)", "party": r"part(?:y|ies)", "body": r"bod(?:y|ies)",
}


def _role_surface_pattern(role: str) -> str:
    tokens = role.split("_")
    last = _IRREGULAR_LAST_TOKEN_PLURAL.get(tokens[-1], re.escape(tokens[-1]) + "s?")
    return r"\s+".join([re.escape(t) for t in tokens[:-1]] + [last])


_ACTOR_ROLE_ALTERNATION = "|".join(
    _role_surface_pattern(r) for r in sorted(_statement_mod.ACTOR_ROLES, key=len, reverse=True)
)
#: An actor noun phrase: an optional determiner, 0-2 modifier words, then
#: one of the closed §21 actor roles' own surface form — "the national
#: competent authority", "a joint controller", "data subject".
ACTOR_NP_FRAGMENT = (
    r"(?:the\s+|a\s+|an\s+)?(?:[A-Za-z]+\s+){0,2}(?:" + _ACTOR_ROLE_ALTERNATION + r")"
)

#: Institutional-actor surface forms (`five_d_nd.statement.
#: INSTITUTIONAL_ACTOR_ROLES`'s own closed set, in ordinary English
#: surface wording) — `competence_of`'s own decisive first gate: an
#: institutional subject AND conferral wording. codebook: "competence_of
#: — relational", "The decisive test: CONFERS/ESTABLISHES versus
#: EXERCISES."
INSTITUTIONAL_ACTOR_SURFACE_RE = re.compile(
    "|".join(
        _role_surface_pattern(r) for r in sorted(_statement_mod.INSTITUTIONAL_ACTOR_ROLES, key=len, reverse=True)
    ).join((r"\b(?:", r")\b")),
    re.IGNORECASE,
)

#: Any modal token anywhere in the unit text — the FALLBACK purpose-
#: routing signal used only when no `enclosing_provision` metadata is
#: given to `extract()` (codebook: "Recital vs article (legislative
#: purpose vs compliance purpose)").
MODAL_ANYWHERE_RE = re.compile(r"\b(?:shall|may|must|should)\b", re.IGNORECASE)

_CLAUSE_BOUNDARY_RE = re.compile(r"[,;:]")


def _clause_start_before(unit_text: str, pos: int) -> int:
    """The nearest clause boundary (`,`/`;`/`:`) at or before ``pos``, or
    the start of the text — used to give a cue-anchored rule (one with
    no regex `subj` group of its own) a reasonable SUBJ span: "whatever
    this clause has said so far"."""
    idx = 0
    for m in _CLAUSE_BOUNDARY_RE.finditer(unit_text, 0, pos):
        idx = m.end()
    return idx


#: A quoted-term character class covering BOTH ASCII and the curly/smart
#: quote marks real legal corpora use — ‘ and "" are part of every
#: NP-boundary char class in this module, not just one rule, for
#: consistency).
_QUOTE_CHARS = "‘’“”'\""
_NP_CHARS = r"[\w\s,{q}-]".format(q=re.escape(_QUOTE_CHARS))
#: round-3 fix: the LEADING character of an NP span may itself be an
#: OPENING quote mark (‘, “, ' — a quoted term named whole, "'X' includes
#: Y" / "X includes 'Y'"), not just a bare letter — `[A-Za-z]` alone
#: (an earlier leading-char class) rejected a span that starts with
#: a quote mark outright, even though `_NP_CHARS` already allowed a
#: quote mark INSIDE the span. Used at the START of the `part_of`-family
#: groups named in the fix (form-part-of, is-part-of, the includes-swap
#: `part`/`whole` groups).
_NP_START = "[A-Za-z‘“']"


RULE_CITATIONS: "dict[str, str]" = {}


def _cite(rule_id: str, section: str) -> str:
    """Record ``rule_id``'s own codebook section citation in
    :data:`RULE_CITATIONS` and return ``rule_id`` unchanged — used
    inline at every ``Candidate(rule_id=_cite(...), ...)`` call site so
    the citation lives NEXT TO the rule that needs it, not in a
    separately-maintained list that can drift out of sync. IDEMPOTENT:
    calling this again with the SAME ``rule_id``/``section`` pair
    (e.g. once eagerly at import time via `_register_all_rule_citations`,
    below, and again at runtime when the owning rule actually fires) is
    a no-op; calling it with the SAME ``rule_id`` but a DIFFERENT
    ``section`` raises ``ValueError`` — two call sites claiming the same
    rule id with different citations is a bug in THIS module, caught
    immediately rather than silently resolved by whichever call
    happened to run last."""
    existing = RULE_CITATIONS.get(rule_id)
    if existing is not None and existing != section:
        raise ValueError(
            f"rule id {rule_id!r} already cited as {existing!r}, now cited differently as {section!r}"
        )
    RULE_CITATIONS[rule_id] = section
    return rule_id


# ─────────────────────────── is_a ──────────────────────────────────────
# codebook: "`is_a` — structural" — "'X' means ...", the definitional
# copula verb (never the ordinary noun "means").
_IS_A_RE = re.compile(
    r"[‘'“](?P<subj>[^’'”]{1,80})[’'”]\s+means\s+"
    r"(?P<obj>[^.;:]{1,400})"
    , re.IGNORECASE
)


def _find_is_a(text: str, context: dict) -> "list[Candidate]":
    out = []
    for m in _IS_A_RE.finditer(text):
        out.append(Candidate(
            rule_id=_cite("T3-is_a-quoted-means", "`is_a` — structural: \"'X' means ...\""),
            predicate="is_a",
            clause_span=m.span(0), subj_span=m.span("subj"), obj_span=m.span("obj"),
            base_confidence=0.75,
        ))
    return out


# ─────────────────────────── part_of ───────────────────────────────────
# codebook: "`part_of` — structural" — "form(s) part of" / "is/are part
# of" verb cues (part-to-whole), and the "X includes Y" whole-first
# direction-swap (subj/obj SWAPPED to keep the relation part-to-whole).
_PART_OF_FORM_RE = re.compile(
    r"(?P<subj>" + _NP_START + _NP_CHARS + r"{1,80}?)\s+(?:form|forms|formed)\s+part\s+of\s+"
    r"(?P<obj>" + _NP_START + _NP_CHARS + r"{1,100})"
    , re.IGNORECASE
)
_PART_OF_IS_RE = re.compile(
    r"(?P<subj>" + _NP_START + _NP_CHARS + r"{1,80}?)\s+(?:is|are)\s+part\s+of\s+"
    r"(?P<obj>" + _NP_START + _NP_CHARS + r"{1,100})"
    , re.IGNORECASE
)
#: "X includes Y" direction-swap — guarded against "references to X
#: include Y" (that is `applies_to`'s own R-o rule, handled separately).
_PART_OF_INCLUDES_RE = re.compile(
    r"(?P<whole>" + _NP_START + _NP_CHARS + r"{1,80}?)\s+includes?\s+"
    r"(?P<part>" + _NP_START + _NP_CHARS + r"{1,150})"
    , re.IGNORECASE
)
_REFERENCES_TO_RE = re.compile(r"\breferences?\s+to\b", re.IGNORECASE)


def _find_part_of(text: str, context: dict) -> "list[Candidate]":
    out = []
    for m in _PART_OF_FORM_RE.finditer(text):
        out.append(Candidate(
            rule_id=_cite("T3-part_of-form-part-of", "`part_of` — structural: \"form(s) part of\" verb cue"),
            predicate="part_of",
            clause_span=m.span(0), subj_span=m.span("subj"), obj_span=m.span("obj"),
            base_confidence=0.7,
        ))
    for m in _PART_OF_IS_RE.finditer(text):
        out.append(Candidate(
            rule_id=_cite("T3-part_of-is-part-of", "`part_of` — structural: part-to-whole containment"),
            predicate="part_of",
            clause_span=m.span(0), subj_span=m.span("subj"), obj_span=m.span("obj"),
            base_confidence=0.6,
        ))
    for m in _PART_OF_INCLUDES_RE.finditer(text):
        window_start = max(0, m.start() - 20)
        if _REFERENCES_TO_RE.search(text[window_start:m.start()]):
            continue  # "references to X include Y" -> applies_to, R-o
        out.append(Candidate(
            rule_id=_cite("T3-part_of-includes-swap", "`part_of` — structural: whole-first \"X includes Y\" direction-swap"),
            predicate="part_of",
            clause_span=m.span(0), subj_span=m.span("part"), obj_span=m.span("whole"),
            base_confidence=0.55,
        ))
    return out


# ─────────────────────────── except_when ───────────────────────────────
# codebook: "`except_when` — structural" — a closed cue set that
# actually expresses non-application: "unless", "except where", "by way
# of derogation from", PLUS "notwithstanding"/"subject to" ONLY when the
# object's own head noun is itself a PROVISION REFERENCE. Ordered BEFORE
# `applies_to`/`cross_references` in RULES (required fix 4: "'derogation
# from' goes before 'referred to in'") so a derogation clause that also
# happens to contain a "referred to in..." qualifier is claimed by
# `except_when` first.
_UNLESS_RE = re.compile(
    r"(?P<subj>[^.;:]{1,200}?),?\s*\bunless\b\s+(?P<obj>[^.;:]{1,200})", re.IGNORECASE
)
_EXCEPT_WHERE_RE = re.compile(
    r"(?P<subj>[^.;:]{1,200}?)\bexcept\s+where\b\s+(?P<obj>[^.;:]{1,200})", re.IGNORECASE
)
#: codebook's own UK DPA 2018 s. 6(1) worked example (`except_when`'s own
#: positive example 4) puts the GENERAL-RULE REMAINDER on `subj` and the
#: PROVISION/PROCEDURE being derogated from on `obj` — the SAME direction
#: this rule uses (see `docs/decisions/0010-deterministic-extractor.md`'s
#: own "the direction is confirmed correct" note). The
#: `obj` group used to stop at the FIRST comma, which truncated a
#: derogation object that is itself a LIST of provision references —
#: codebook `except_when` positive example 1 (GDPR Art. 65(5)) derogates
#: from "the consistency mechanism referred to in Articles 63, 64 and 65
#: or the procedure referred to in Article 60" as ONE object, where the
#: embedded ", 64" is part of the Article LIST, not the end of the
#: clause. The `obj` group now consumes a comma ONLY when it is
#: immediately followed by a digit (an Article-list comma, "63, 64");
#: any OTHER comma (the real clause boundary, ", immediately adopt...")
#: still ends the match.
_DEROGATION_RE = re.compile(
    r"by\s+(?:way\s+of\s+)?derogation\s+from\s+"
    r"(?P<obj>(?:[^,]|,(?=\s*\d)){1,250}),?\s*(?P<subj>[^.;:]{1,200})",
    re.IGNORECASE,
)
_PROVISION_WORD = r"(?:subsection|section|paragraph|Article|point)"
_NOTWITHSTANDING_PROVISION_RE = re.compile(
    r"notwithstanding\s+(?P<obj>" + _PROVISION_WORD + r"\s*\d*[^,]{0,80}),?\s*"
    r"(?P<subj>[^.;:]{1,200})",
    re.IGNORECASE,
)
#: required fix 4: "'subject to—' tolerates a list letter or 'a '" — an
#: optional single-letter list marker (`a `, `(a) `, `b.`...) between the
#: dash/colon and the provision word, the UK DPA 2018 s. 6(1) chapeau's
#: own surface form ("has effect subject to— a subsection (2), b section
#: 209, and c section 210").
_LIST_MARKER = r"(?:\(?[a-z]\)?[.)]?\s+)?"
_SUBJECT_TO_PROVISION_RE = re.compile(
    r"subject\s+to\s*[—\-:]?\s*" + _LIST_MARKER +
    r"(?P<obj>" + _PROVISION_WORD + r"s?\s*\(?\d*\)?[^.;,:]{0,80})",
    re.IGNORECASE,
)
#: codebook's own chapeau-list rule ("List items under a chapeau: ONE
#: Statement per item... the subject is INHERITED from the chapeau") —
#: applied here to a "subject to—" list specifically: every FURTHER
#: provision item in the SAME list (separated by `,`/`and`/a list
#: letter), sharing the chapeau's own `subj`.
_SUBJECT_TO_LIST_ITEM_RE = re.compile(
    r"(?:,|\band\b)\s*" + _LIST_MARKER +
    r"(?P<obj>" + _PROVISION_WORD + r"s?\s*\(?\d*\)?)",
    re.IGNORECASE,
)


def _find_except_when(text: str, context: dict) -> "list[Candidate]":
    out = []
    for m in _UNLESS_RE.finditer(text):
        out.append(Candidate(
            rule_id=_cite("T3-except_when-unless", "`except_when` — structural: \"unless\" cue"),
            predicate="except_when",
            clause_span=m.span(0), subj_span=m.span("subj"), obj_span=m.span("obj"),
            base_confidence=0.6,
        ))
    for m in _EXCEPT_WHERE_RE.finditer(text):
        out.append(Candidate(
            rule_id=_cite("T3-except_when-except-where", "`except_when` — structural: \"except where\" cue"),
            predicate="except_when",
            clause_span=m.span(0), subj_span=m.span("subj"), obj_span=m.span("obj"),
            base_confidence=0.6,
        ))
    for m in _DEROGATION_RE.finditer(text):
        out.append(Candidate(
            rule_id=_cite("T3-except_when-derogation-from", "`except_when` — structural: \"by way of derogation from\" cue"),
            predicate="except_when",
            clause_span=m.span(0), subj_span=m.span("subj"), obj_span=m.span("obj"),
            base_confidence=0.65,
        ))
    for m in _NOTWITHSTANDING_PROVISION_RE.finditer(text):
        out.append(Candidate(
            rule_id=_cite("T3-except_when-notwithstanding-provision",
                           "`except_when` — structural: \"notwithstanding [provision]\" routing test"),
            predicate="except_when",
            clause_span=m.span(0), subj_span=m.span("subj"), obj_span=m.span("obj"),
            base_confidence=0.55,
        ))
    for m in _SUBJECT_TO_PROVISION_RE.finditer(text):
        subj_start = _clause_start_before(text, m.start())
        if subj_start >= m.start():
            continue
        shared_subj = (subj_start, m.start())
        clause_end = m.end()
        chapeau_group = f"subject-to-{subj_start}"
        out.append(Candidate(
            rule_id=_cite("T3-except_when-subject-to-provision",
                           "`except_when` — structural: \"subject to [provision]\" routing test, "
                           "\"Unitisation rules\" chapeau-list (UK DPA 2018 s. 6(1))"),
            predicate="except_when",
            clause_span=(subj_start, clause_end), subj_span=shared_subj,
            obj_span=m.span("obj"), base_confidence=0.5, chapeau_group=chapeau_group,
        ))
        # codebook chapeau-list rule: every FURTHER listed provision in
        # the SAME "subject to—" list gets its own Statement, sharing
        # `shared_subj` — scanned forward from this match's own end.
        # Sharing `chapeau_group` means these never conflict with each
        # other, or with the chapeau's own first item, in overlap
        # resolution (`extract.build.resolve_overlaps_built`), even
        # though every one of them nominally "overlaps" at `shared_subj`.
        search_from = m.end()
        window_end = min(len(text), search_from + 200)
        for item in _SUBJECT_TO_LIST_ITEM_RE.finditer(text, search_from, window_end):
            out.append(Candidate(
                rule_id=_cite("T3-except_when-subject-to-provision-list-item",
                               "`except_when` — structural: \"Unitisation rules\" chapeau-list "
                               "(UK DPA 2018 s. 6(1), further listed items)"),
                predicate="except_when",
                clause_span=(shared_subj[0], item.end()), subj_span=shared_subj,
                obj_span=item.span("obj"), base_confidence=0.5, chapeau_group=chapeau_group,
            ))
    return out


# ─────────────────────────── applies_to ────────────────────────────────
# codebook: "`applies_to` — structural" — the instrument's own scope,
# INCLUDING a concessive clause ("notwithstanding the fact that...",
# "irrespective of..." — WHEN the object's own head noun is NOT a
# provision reference; routed away from `except_when` by the SAME
# negative lookahead `except_when`'s own provision-reference test uses,
# so order between the two rule groups cannot mis-route either way), and
# R-o's own "references to X include Y" -> `applies_to` (never `is_a`,
# never `part_of`).
_APPLIES_TO_RE = re.compile(
    r"(?P<subj>This [A-Z][\w\s]{1,40}?)\s+applies\s+to\s+(?P<obj>[^.;:]{1,300})"
)
_NOT_APPLY_TO_RE = re.compile(
    r"(?P<subj>This [A-Z][\w\s]{1,40}?)\s+(?:shall\s+not\s+apply\s+to|does\s+not\s+apply\s+to)\s+"
    r"(?P<obj>[^.;:]{1,300})"
)
_REFERENCES_INCLUDE_RE = re.compile(
    r"[Rr]eferences?\s+to\s+(?P<subj>[^,]{1,80})\s+includes?\s*[—\-:]?\s*"
    r"(?P<obj>[^.;:]{1,300})"
    , re.IGNORECASE
)
#: required fix 4: the concessive `applies_to` rule — a NEGATIVE
#: LOOKAHEAD excludes a provision-reference object (`except_when`'s own
#: job) regardless of rule order.
_CONCESSIVE_RE = re.compile(
    r"\b(?:notwithstanding|irrespective\s+of)\s+(?!" + _PROVISION_WORD + r"\b)"
    r"(?:the\s+fact\s+that\s+)?(?P<obj>[^,]{1,150}),\s*(?P<subj>[^.;:]{1,200})",
    re.IGNORECASE,
)


def _find_applies_to(text: str, context: dict) -> "list[Candidate]":
    out = []
    for m in _APPLIES_TO_RE.finditer(text):
        out.append(Candidate(
            rule_id=_cite("T3-applies_to-applies-to", "`applies_to` — structural: \"applies to\" cue"),
            predicate="applies_to",
            clause_span=m.span(0), subj_span=m.span("subj"), obj_span=m.span("obj"),
            base_confidence=0.7,
        ))
    for m in _NOT_APPLY_TO_RE.finditer(text):
        out.append(Candidate(
            rule_id=_cite("T3-applies_to-not-apply-to", "`applies_to` — structural: negated scope"),
            predicate="applies_to",
            clause_span=m.span(0), subj_span=m.span("subj"), obj_span=m.span("obj"),
            negation_force="present", base_confidence=0.65,
        ))
    for m in _REFERENCES_INCLUDE_RE.finditer(text):
        out.append(Candidate(
            rule_id=_cite("T3-applies_to-references-to-include",
                           "`applies_to` — structural: R-o \"references to X include Y\""),
            predicate="applies_to",
            clause_span=m.span(0), subj_span=m.span("subj"), obj_span=m.span("obj"),
            base_confidence=0.6,
        ))
    for m in _CONCESSIVE_RE.finditer(text):
        out.append(Candidate(
            rule_id=_cite("T3-applies_to-concessive",
                           "`applies_to` — structural: concessive \"notwithstanding the fact that\"/"
                           "\"irrespective of\" (non-provision head noun)"),
            predicate="applies_to",
            clause_span=m.span(0), subj_span=m.span("subj"), obj_span=m.span("obj"),
            base_confidence=0.55,
        ))
    return out


# ─────────────────────────── cross_references ──────────────────────────
# codebook: "`cross_references` — structural" and "Savings clauses —
# `cross_references`, never `except_when` or negated `applies_to`". The
# "referred to in Article N" rule REUSES `clause_cues.ARTICLE_REF_RE`
# itself (the verbatim compiled pattern, imported, not re-typed) to
# bound the citation span exactly — required fix 4: "the 'referred to
# in' obj stops at a comma" (ARTICLE_REF_RE's own citation grammar
# already stops at the right boundary; it does not run on past one).
_REFERRED_TO_IN_LEADIN_RE = re.compile(
    r"(?P<subj>[A-Za-z]" + _NP_CHARS + r"{1,80}?)\s+referred\s+to\s+in\s+",
    re.IGNORECASE,
)
_WITHOUT_PREJUDICE_RE = re.compile(
    r"(?P<subj>[^.;:]{1,150}?)\s+is\s+without\s+prejudice\s+to\s+(?P<obj>[^.;:]{1,200})"
    , re.IGNORECASE
)
#: required fix 4: a BARE "without prejudice to" rule (no leading "is"
#: copula required) — e.g. "...shall apply, without prejudice to Article
#: 5." `subj` is whatever the clause said so far (`_clause_start_before`).
_WITHOUT_PREJUDICE_BARE_RE = re.compile(
    r"\bwithout\s+prejudice\s+to\s+(?P<obj>[^.;:]{1,200})", re.IGNORECASE
)
_SHALL_NOT_AFFECT_RE = re.compile(
    r"(?P<subj>[A-Z][\w\s]{1,60}?)\s+shall\s+not\s+affect\s+(?P<obj>[^.;:]{1,200})"
)


def _find_cross_references(text: str, context: dict) -> "list[Candidate]":
    out = []
    for m in _REFERRED_TO_IN_LEADIN_RE.finditer(text):
        citation = _clause_cues.ARTICLE_REF_RE.match(text, m.end())
        if citation is None:
            continue
        out.append(Candidate(
            rule_id=_cite("T3-cross_references-referred-to-in",
                           "`cross_references` — structural: \"referred to in Article N\" "
                           "(citation span via clause_cues.ARTICLE_REF_RE)"),
            predicate="cross_references",
            clause_span=(m.start(0), citation.end()), subj_span=m.span("subj"),
            obj_span=citation.span(0), base_confidence=0.65,
        ))
    for m in _WITHOUT_PREJUDICE_RE.finditer(text):
        out.append(Candidate(
            rule_id=_cite("T3-cross_references-without-prejudice",
                           "Savings clauses — `cross_references`: \"is without prejudice to\""),
            predicate="cross_references",
            clause_span=m.span(0), subj_span=m.span("subj"), obj_span=m.span("obj"),
            negation_force="absent", base_confidence=0.7,
        ))
    for m in _WITHOUT_PREJUDICE_BARE_RE.finditer(text):
        subj_start = _clause_start_before(text, m.start())
        if subj_start >= m.start():
            continue
        out.append(Candidate(
            rule_id=_cite("T3-cross_references-without-prejudice-bare",
                           "Savings clauses — `cross_references`: bare \"without prejudice to\" "
                           "(no leading \"is\" copula required)"),
            predicate="cross_references",
            clause_span=(subj_start, m.end()), subj_span=(subj_start, m.start()),
            obj_span=m.span("obj"), negation_force="absent", base_confidence=0.6,
        ))
    for m in _SHALL_NOT_AFFECT_RE.finditer(text):
        out.append(Candidate(
            rule_id=_cite("T3-cross_references-shall-not-affect",
                           "Savings clauses — `cross_references`: \"shall not affect\""),
            predicate="cross_references",
            clause_span=m.span(0), subj_span=m.span("subj"), obj_span=m.span("obj"),
            negation_force="absent", base_confidence=0.7,
        ))
    return out


# ─────────────────────────── enables ───────────────────────────────────
# codebook: "`enables` — causal" — makes something possible, no stated
# purpose.
_ENABLES_RE = re.compile(r"(?P<subj>[^.;:]{1,150}?)\benables?\b\s+(?P<obj>[^.;:]{1,200})", re.IGNORECASE)


def _find_enables(text: str, context: dict) -> "list[Candidate]":
    out = []
    for m in _ENABLES_RE.finditer(text):
        out.append(Candidate(
            rule_id=_cite("T3-enables-enables", "`enables` — causal: \"enables\" cue"),
            predicate="enables",
            clause_span=m.span(0), subj_span=m.span("subj"), obj_span=m.span("obj"),
            base_confidence=0.5,
        ))
    return out


# ─────────────────────────── requires ──────────────────────────────────
# codebook: "`requires` — causal" — a trigger/condition -> consequence
# ACT relation ("where", "if", "in the case of"), PLUS "subject to [a
# condition or requirement]" whose own head noun is NOT a provision
# reference (`applies_to`'s own routing test, applied here too).
_WHERE_IF_RE = re.compile(
    r"\b(?:Where|If|where|if)\b\s+(?P<subj>[^,]{1,250}),\s*(?P<obj>[^.;:]{1,250})"
)
#: required fix 4 / round-2 item 7: "In the case of" as a `requires`
#: trigger, the SAME trigger->consequence shape as "Where"/"If".
_IN_CASE_OF_RE = re.compile(
    r"\b[Ii]n\s+the\s+case\s+of\s+(?P<subj>[^,]{1,250}),\s*(?P<obj>[^.;:]{1,250})"
)
_SUBJECT_TO_CONDITION_RE = re.compile(
    r"subject\s+to\s+(?!" + _PROVISION_WORD + r")(?P<obj>[^.;:]{1,150})"
    , re.IGNORECASE
)


def _find_requires(text: str, context: dict) -> "list[Candidate]":
    out = []
    for pattern, rule_id, section in (
        (_WHERE_IF_RE, "T3-requires-where-if",
         "`requires` — causal: \"where\"/\"if\" trigger -> consequence"),
        (_IN_CASE_OF_RE, "T3-requires-in-the-case-of",
         "`requires` — causal: \"in the case of\" trigger -> consequence"),
    ):
        for m in pattern.finditer(text):
            out.append(Candidate(
                rule_id=_cite(rule_id, section), predicate="requires",
                clause_span=m.span(0), subj_span=m.span("subj"), obj_span=m.span("obj"),
                strip_modal_obj=True, strip_subject_and_modal_obj=True, base_confidence=0.55,
                truncate_midspan_modal=False,
            ))
    for m in _SUBJECT_TO_CONDITION_RE.finditer(text):
        subj_start = _clause_start_before(text, m.start())
        if subj_start >= m.start():
            continue
        out.append(Candidate(
            rule_id=_cite("T3-requires-subject-to-condition",
                           "`requires` — causal: \"subject to [a condition]\" routing test"),
            predicate="requires",
            clause_span=(subj_start, m.end()), subj_span=(subj_start, m.start()),
            obj_span=m.span("obj"), base_confidence=0.5,
            truncate_midspan_modal=False,
        ))
    return out


# ──────────────────── legislative/compliance purpose ────────────────────
# codebook: "`legislative_purpose_of` — intentional", "`compliance_
# purpose_of` — intentional", and the "Recital vs article (legislative
# purpose vs compliance purpose)" decision rule: check POSITION first,
# then the modal, as a FALLBACK ONLY when position (`enclosing_
# provision`) is not known to this call.
_PURPOSE_CUE = r"(?:in order to|for the purposes? of|aims? to|is intended to|are intended to)"
_PURPOSE_RE = re.compile(
    r"(?P<subj>[^.;:]{1,200}?)\b" + _PURPOSE_CUE + r"\b\s+(?P<obj>[^.;:]{1,200})"
    , re.IGNORECASE
)
#: required fix 4: cues may appear at the START of a unit — "For the
#: purpose of X, Y" fronted form, no subj content before the cue for the
#: plain (non-fronted) regex above to capture.
_PURPOSE_FRONTED_RE = re.compile(
    r"^\s*" + _PURPOSE_CUE + r"\s+(?P<obj>[^,]{1,200}),\s*(?P<subj>[^.;:]{1,200})",
    re.IGNORECASE,
)


def _route_purpose_predicate(text: str, context: dict) -> tuple:
    """``(predicate, rule_id_suffix)`` for a purpose-cue match —
    POSITION first (`context["enclosing_provision"]`, when given: a
    recital -> `legislative_purpose_of`, anything else -> `compliance_
    purpose_of`, regardless of modal, per the codebook's own "coded by
    POSITION, not by the modal's presence" rule), falling back to the
    "any modal anywhere" heuristic ONLY when no metadata was given."""
    enclosing = context.get("enclosing_provision") if context else None
    if enclosing:
        is_recital = "recital" in enclosing.lower()
        return ("legislative_purpose_of" if is_recital else "compliance_purpose_of",
                "legislative-by-position" if is_recital else "compliance-by-position")
    has_modal = bool(MODAL_ANYWHERE_RE.search(text))
    return ("compliance_purpose_of" if has_modal else "legislative_purpose_of",
            "compliance-by-modal-fallback" if has_modal else "legislative-by-modal-fallback")


def _find_purpose(text: str, context: dict) -> "list[Candidate]":
    out = []
    for m in _PURPOSE_RE.finditer(text):
        predicate, suffix = _route_purpose_predicate(text, context)
        out.append(Candidate(
            rule_id=_cite(f"T3-purpose-cue-{suffix}",
                           "`legislative_purpose_of`/`compliance_purpose_of` — intentional: "
                           "\"Recital vs article\" decision rule"),
            predicate=predicate, clause_span=m.span(0),
            subj_span=m.span("subj"), obj_span=m.span("obj"), base_confidence=0.55,
            truncate_midspan_modal=False,
        ))
    for m in _PURPOSE_FRONTED_RE.finditer(text):
        predicate, suffix = _route_purpose_predicate(text, context)
        out.append(Candidate(
            rule_id=_cite(f"T3-purpose-cue-fronted-{suffix}",
                           "`legislative_purpose_of`/`compliance_purpose_of` — intentional: "
                           "fronted \"for the purpose of X, Y\""),
            predicate=predicate, clause_span=m.span(0),
            subj_span=m.span("subj"), obj_span=m.span("obj"), base_confidence=0.5,
            truncate_midspan_modal=False,
        ))
    return out


# ─────────────────────────── based_on ──────────────────────────────────
# codebook: "`based_on` — intentional" — the stated legal basis
# (justification), never a "Where X is based on Y, Z" trigger (that is
# `requires`).
_BASED_ON_RE = re.compile(r"(?P<subj>[^.;:]{1,200}?)\bis\s+based\s+on\b\s+(?P<obj>[^.;:]{1,200})", re.IGNORECASE)


def _find_based_on(text: str, context: dict) -> "list[Candidate]":
    out = []
    for m in _BASED_ON_RE.finditer(text):
        prefix = text[max(0, m.start() - 10):m.start()]
        if re.search(r"\b(?:where|if)\s*$", prefix, re.IGNORECASE):
            continue
        out.append(Candidate(
            rule_id=_cite("T3-based_on-is-based-on", "`based_on` — intentional: \"is based on\" (legal basis)"),
            predicate="based_on",
            clause_span=m.span(0), subj_span=m.span("subj"), obj_span=m.span("obj"),
            base_confidence=0.6,
        ))
    return out


# ─────────────────────────── deadline_of ───────────────────────────────
# codebook: "`deadline_of` — temporal" — a bounded-duration relation.
_DEADLINE_RE = re.compile(
    r"\b(?:within|not\s+later\s+than|no\s+later\s+than)\s+"
    r"(?P<obj>\d+\s*(?:hour|day|week|month|year)s?(?:\s+after\s+[^.;,:]{1,100})?)"
    , re.IGNORECASE
)


def _find_deadline_of(text: str, context: dict) -> "list[Candidate]":
    out = []
    for m in _DEADLINE_RE.finditer(text):
        subj_start = _clause_start_before(text, m.start())
        if subj_start >= m.start():
            continue
        out.append(Candidate(
            rule_id=_cite("T3-deadline_of-within-n", "`deadline_of` — temporal: \"within N days/...\""),
            predicate="deadline_of",
            clause_span=(subj_start, m.end()), subj_span=(subj_start, m.start()),
            obj_span=m.span("obj"), base_confidence=0.6,
        ))
    return out


# ─────────────────────────── precedes ──────────────────────────────────
# codebook: "`precedes` — temporal" — a bare ordering relation, no
# stated duration.
_PRECEDES_RE = re.compile(
    r"(?P<subj>[^.;:]{1,150}?)\b(?:prior\s+to|before)\b\s+(?P<obj>[^.;:]{1,150})"
    , re.IGNORECASE
)
#: required fix 4: "cues may appear at the start of a unit, e.g. ...
#: 'prior to'" — fronted "Prior to X, Y" form.
_PRECEDES_FRONTED_RE = re.compile(
    r"^\s*(?:prior\s+to|before)\s+(?P<obj>[^,]{1,150}),\s*(?P<subj>[^.;:]{1,150})",
    re.IGNORECASE,
)


def _find_precedes(text: str, context: dict) -> "list[Candidate]":
    out = []
    for m in _PRECEDES_RE.finditer(text):
        out.append(Candidate(
            rule_id=_cite("T3-precedes-prior-before", "`precedes` — temporal: \"prior to\"/\"before\""),
            predicate="precedes",
            clause_span=m.span(0), subj_span=m.span("subj"), obj_span=m.span("obj"),
            base_confidence=0.5,
        ))
    for m in _PRECEDES_FRONTED_RE.finditer(text):
        out.append(Candidate(
            rule_id=_cite("T3-precedes-fronted", "`precedes` — temporal: fronted \"Prior to X, Y\""),
            predicate="precedes",
            clause_span=m.span(0), subj_span=m.span("subj"), obj_span=m.span("obj"),
            base_confidence=0.45,
        ))
    return out


# ──────────────────── competence_of / performs ─────────────────────────
# codebook: "`competence_of` — relational" (CONFERS/ESTABLISHES, gated to
# an INSTITUTIONAL actor) and "`performs` — relational" (any other
# actor->act relation, and an institutional actor EXERCISING an
# already-granted power). Actor NPs draw on the
# closed §21 ACTOR_ROLES vocabulary (`ACTOR_NP_FRAGMENT`, above) rather
# than a hand-typed list, and the modal->verb gap tolerates ONE short
# comma-bounded adverbial interruption ("shall, within one month,
# notify...").
_SHALL_HAVE_POWER_RE = re.compile(
    r"(?P<subj>[A-Z][\w\s]{1,60}?)\s+shall\s+have\s+the\s+(?:task|power)\s+to\s+(?P<obj>[^.;:]{1,200})"
)
_RESPONSIBLE_FOR_RE = re.compile(
    r"(?P<subj>[A-Z][\w\s]{1,60}?)\s+(?:is|are)\s+responsible\s+for\s+(?P<obj>[^.;:]{1,200})"
)
_SHALL_BE_COMPETENT_RE = re.compile(
    r"(?P<subj>[A-Z][\w\s]{1,60}?)\s+shall\s+be\s+competent\s+(?P<obj>[^.;:]{1,200})"
)
#: an optional single short adverbial between the modal and its verb —
#: "shall, within one month, respond to the request".
_MODAL_INTERRUPTION = r"(?:,\s*[^,]{1,60},\s*)?"
_PERFORMS_SHALL_RE = re.compile(
    r"(?P<subj>" + ACTOR_NP_FRAGMENT + r")\s+shall\s*" + _MODAL_INTERRUPTION +
    r"(?P<obj>[^.;:]{1,200})", re.IGNORECASE
)
_PERFORMS_MODAL_RE = re.compile(
    r"(?P<subj>" + ACTOR_NP_FRAGMENT + r")\s+(?:may|must|should)\s*" + _MODAL_INTERRUPTION +
    r"(?P<obj>[^.;:]{1,200})", re.IGNORECASE
)


def _find_competence_and_performs(text: str, context: dict) -> "list[Candidate]":
    out = []
    for pattern, rule_id, section in (
        (_SHALL_HAVE_POWER_RE, "T3-competence_of-shall-have-power",
         "`competence_of` — relational: \"shall have the task/power to\" (conferral)"),
        (_RESPONSIBLE_FOR_RE, "T3-competence_of-responsible-for",
         "`competence_of` — relational: the \"responsible for\" conferral rule"),
        (_SHALL_BE_COMPETENT_RE, "T3-competence_of-shall-be-competent",
         "`competence_of` — relational: \"shall be competent\" (conferral)"),
    ):
        for m in pattern.finditer(text):
            subj_text = m.group("subj")
            is_institutional = bool(INSTITUTIONAL_ACTOR_SURFACE_RE.search(subj_text))
            predicate = "competence_of" if is_institutional else "performs"
            out.append(Candidate(
                rule_id=_cite(rule_id, section) if is_institutional else
                _cite("T3-performs-non-institutional-conferral-surface",
                      "`performs` — relational: a conferral-shaped clause on a NON-institutional actor"),
                predicate=predicate, clause_span=m.span(0),
                subj_span=m.span("subj"), obj_span=m.span("obj"),
                strip_modal_obj=True, base_confidence=0.55,
                truncate_midspan_modal=False,
            ))
    for m in _PERFORMS_SHALL_RE.finditer(text):
        out.append(Candidate(
            rule_id=_cite("T3-performs-actor-shall", "`performs` — relational: actor NP + \"shall\" + act"),
            predicate="performs",
            clause_span=m.span(0), subj_span=m.span("subj"), obj_span=m.span("obj"),
            strip_modal_obj=True, base_confidence=0.55,
            truncate_midspan_modal=False,
        ))
    for m in _PERFORMS_MODAL_RE.finditer(text):
        out.append(Candidate(
            rule_id=_cite("T3-performs-actor-modal", "`performs` — relational: actor NP + \"may\"/\"must\"/\"should\" + act"),
            predicate="performs",
            clause_span=m.span(0), subj_span=m.span("subj"), obj_span=m.span("obj"),
            strip_modal_obj=True, base_confidence=0.5,
            truncate_midspan_modal=False,
        ))
    return out


# ─────────────────────────── predication (default) ─────────────────────
# codebook: "`predication` — relational (the default)" — an ordinary
# copula or modal assertion that falls under none of the other fourteen
# predicates.
_COPULA_RE = re.compile(
    r"(?P<subj>[^.;:]{1,150}?)\s+(?:is|are|shall\s+be)\s+(?P<obj>[^.;:]{1,200})"
    , re.IGNORECASE
)


def _find_predication(text: str, context: dict) -> "list[Candidate]":
    out = []
    for m in _COPULA_RE.finditer(text):
        out.append(Candidate(
            rule_id=_cite("T3-predication-copula-fallback", "`predication` — relational (the default): ordinary copula"),
            predicate="predication",
            clause_span=m.span(0), subj_span=m.span("subj"), obj_span=m.span("obj"),
            strip_modal_subj=True, strip_modal_obj=True, base_confidence=0.35,
            truncate_midspan_modal=False,
        ))
    return out


def _find_predication_whole_unit(text: str, context: dict) -> "list[Candidate]":
    """The LAST-RESORT fallback: no other rule matched anything at all in
    this unit. Splits on the FIRST whitespace run after the first eight
    words, so every unit still gets exactly one low-confidence
    `predication` candidate rather than none — the codebook's own
    `predication` definition explicitly allows a clause whose subject is
    not even an actor ("Testing shall ensure..."). `extract.build`'s own
    pipeline now finalises spans BEFORE resolving overlap (required fix
    3), so this fallback survives whenever every other rule's own
    candidate collapsed to an empty span — it is no longer blocked by a
    since-emptied candidate's own raw (pre-finalisation) span."""
    stripped = text.strip()
    if not stripped:
        return []
    words = list(re.finditer(r"\S+", stripped))
    if len(words) < 2:
        return []
    split_idx = min(8, len(words) - 1)
    offset = text.index(stripped)
    subj_end = offset + words[split_idx - 1].end()
    obj_start = offset + words[split_idx].start()
    clause_end = offset + words[-1].end()
    return [Candidate(
        rule_id=_cite("T3-predication-whole-unit-fallback",
                       "`predication` — relational (the default): last-resort, no cue matched"),
        predicate="predication",
        clause_span=(offset, clause_end),
        subj_span=(offset, subj_end), obj_span=(obj_start, clause_end),
        strip_modal_subj=True, strip_modal_obj=True,
        base_confidence=0.2, truncate_midspan_modal=False,
    )]


def _register_all_rule_citations() -> None:
    """Builds :data:`RULE_CITATIONS` EAGERLY, at import
    time — independent of whether any rule ever actually FIRES on any
    given input. The inline `_cite(...)` calls scattered through every
    `_find_*` function above are each reached only when their own regex
    matches something; several rule ids are produced only on a RUNTIME
    BRANCH (the purpose-predicate router's 4 position/modal-fallback x
    recital/compliance combinations, times 2 for the fronted variant;
    the competence_of/performs institutional-actor gate's 4
    combinations) — a probe battery that fails to exercise every single
    branch would previously leave a real, reachable rule id with NO
    citation recorded. This function calls `_cite` once for EVERY rule
    id this module can ever produce, with the IDENTICAL literal section
    text its own runtime call site uses (`_cite`'s own idempotency check
    means a later runtime call with the same text is a safe no-op; a
    mismatch would raise immediately, catching drift between this list
    and the inline call sites). Called once, unconditionally, directly
    below this function's own definition."""
    for rule_id, section in (
        ("T3-is_a-quoted-means", "`is_a` — structural: \"'X' means ...\""),
        ("T3-part_of-form-part-of", "`part_of` — structural: \"form(s) part of\" verb cue"),
        ("T3-part_of-is-part-of", "`part_of` — structural: part-to-whole containment"),
        ("T3-part_of-includes-swap", "`part_of` — structural: whole-first \"X includes Y\" direction-swap"),
        ("T3-except_when-unless", "`except_when` — structural: \"unless\" cue"),
        ("T3-except_when-except-where", "`except_when` — structural: \"except where\" cue"),
        ("T3-except_when-derogation-from", "`except_when` — structural: \"by way of derogation from\" cue"),
        ("T3-except_when-notwithstanding-provision",
         "`except_when` — structural: \"notwithstanding [provision]\" routing test"),
        ("T3-except_when-subject-to-provision",
         "`except_when` — structural: \"subject to [provision]\" routing test, "
         "\"Unitisation rules\" chapeau-list (UK DPA 2018 s. 6(1))"),
        ("T3-except_when-subject-to-provision-list-item",
         "`except_when` — structural: \"Unitisation rules\" chapeau-list "
         "(UK DPA 2018 s. 6(1), further listed items)"),
        ("T3-applies_to-applies-to", "`applies_to` — structural: \"applies to\" cue"),
        ("T3-applies_to-not-apply-to", "`applies_to` — structural: negated scope"),
        ("T3-applies_to-references-to-include",
         "`applies_to` — structural: R-o \"references to X include Y\""),
        ("T3-applies_to-concessive",
         "`applies_to` — structural: concessive \"notwithstanding the fact that\"/"
         "\"irrespective of\" (non-provision head noun)"),
        ("T3-cross_references-referred-to-in",
         "`cross_references` — structural: \"referred to in Article N\" "
         "(citation span via clause_cues.ARTICLE_REF_RE)"),
        ("T3-cross_references-without-prejudice",
         "Savings clauses — `cross_references`: \"is without prejudice to\""),
        ("T3-cross_references-without-prejudice-bare",
         "Savings clauses — `cross_references`: bare \"without prejudice to\" "
         "(no leading \"is\" copula required)"),
        ("T3-cross_references-shall-not-affect",
         "Savings clauses — `cross_references`: \"shall not affect\""),
        ("T3-enables-enables", "`enables` — causal: \"enables\" cue"),
        ("T3-requires-where-if", "`requires` — causal: \"where\"/\"if\" trigger -> consequence"),
        ("T3-requires-in-the-case-of", "`requires` — causal: \"in the case of\" trigger -> consequence"),
        ("T3-requires-subject-to-condition",
         "`requires` — causal: \"subject to [a condition]\" routing test"),
        ("T3-purpose-cue-legislative-by-position",
         "`legislative_purpose_of`/`compliance_purpose_of` — intentional: "
         "\"Recital vs article\" decision rule"),
        ("T3-purpose-cue-compliance-by-position",
         "`legislative_purpose_of`/`compliance_purpose_of` — intentional: "
         "\"Recital vs article\" decision rule"),
        ("T3-purpose-cue-legislative-by-modal-fallback",
         "`legislative_purpose_of`/`compliance_purpose_of` — intentional: "
         "\"Recital vs article\" decision rule"),
        ("T3-purpose-cue-compliance-by-modal-fallback",
         "`legislative_purpose_of`/`compliance_purpose_of` — intentional: "
         "\"Recital vs article\" decision rule"),
        ("T3-purpose-cue-fronted-legislative-by-position",
         "`legislative_purpose_of`/`compliance_purpose_of` — intentional: "
         "fronted \"for the purpose of X, Y\""),
        ("T3-purpose-cue-fronted-compliance-by-position",
         "`legislative_purpose_of`/`compliance_purpose_of` — intentional: "
         "fronted \"for the purpose of X, Y\""),
        ("T3-purpose-cue-fronted-legislative-by-modal-fallback",
         "`legislative_purpose_of`/`compliance_purpose_of` — intentional: "
         "fronted \"for the purpose of X, Y\""),
        ("T3-purpose-cue-fronted-compliance-by-modal-fallback",
         "`legislative_purpose_of`/`compliance_purpose_of` — intentional: "
         "fronted \"for the purpose of X, Y\""),
        ("T3-based_on-is-based-on", "`based_on` — intentional: \"is based on\" (legal basis)"),
        ("T3-deadline_of-within-n", "`deadline_of` — temporal: \"within N days/...\""),
        ("T3-precedes-prior-before", "`precedes` — temporal: \"prior to\"/\"before\""),
        ("T3-precedes-fronted", "`precedes` — temporal: fronted \"Prior to X, Y\""),
        ("T3-competence_of-shall-have-power",
         "`competence_of` — relational: \"shall have the task/power to\" (conferral)"),
        ("T3-competence_of-responsible-for",
         "`competence_of` — relational: the \"responsible for\" conferral rule"),
        ("T3-competence_of-shall-be-competent",
         "`competence_of` — relational: \"shall be competent\" (conferral)"),
        ("T3-performs-non-institutional-conferral-surface",
         "`performs` — relational: a conferral-shaped clause on a NON-institutional actor"),
        ("T3-performs-actor-shall", "`performs` — relational: actor NP + \"shall\" + act"),
        ("T3-performs-actor-modal",
         "`performs` — relational: actor NP + \"may\"/\"must\"/\"should\" + act"),
        ("T3-predication-copula-fallback",
         "`predication` — relational (the default): ordinary copula"),
        ("T3-predication-whole-unit-fallback",
         "`predication` — relational (the default): last-resort, no cue matched"),
        # round-4 segmenter integration: chapeau-only triggers (the cue
        # ends the chapeau; the list items supply the objects) and the
        # generic chapeau-actor-plus-modal fallback.
        ("T3-except_when-subject-to-provision-chapeau-only",
         "`except_when` — structural: \"subject to [provision]\" routing test "
         "(chapeau-only: the cue ends the chapeau, the provision references are the list items)"),
        ("T3-except_when-unless-chapeau-only",
         "`except_when` — structural: \"unless\" cue (chapeau-only)"),
        ("T3-competence_of-shall-have-power-chapeau-only",
         "`competence_of` — relational: \"shall have the task/power to\" (conferral, chapeau-only)"),
        ("T3-competence_of-responsible-for-chapeau-only",
         "`competence_of` — relational: the \"responsible for\" conferral rule (chapeau-only)"),
        ("T3-performs-chapeau-generic-modal",
         "`performs` — relational: chapeau actor + modal, pointing at its own list"),
        ("T3-competence_of-chapeau-generic-modal",
         "`competence_of` — relational: chapeau actor + modal, pointing at its own list"),
    ):
        _cite(rule_id, section)

    # round-5 fix: a chapeau TRIGGER can be any already-registered rule
    # id above — register its own "-chapeau-inherited-item" derived
    # citation EAGERLY too, for every one of them, rather than letting
    # `collect_segmented_candidates` discover each one lazily the first
    # time a real unit happens to use it as a trigger. The literal
    # citation text template MUST match the one that function's own
    # runtime `_cite()` call uses, exactly, or `_cite`'s own mismatch
    # check would raise.
    for rule_id in list(RULE_CITATIONS):
        derived_id = f"{rule_id}-chapeau-inherited-item"
        _cite(derived_id, f"{RULE_CITATIONS[rule_id]} (inherited by a chapeau-list item with no cue of its own)")


_register_all_rule_citations()


#: Precedence order: EARLIER rules claim a span first; a LATER rule's
#: candidate is dropped if its own clause span overlaps one already
#: accepted AND the two predicates are not in
#: :data:`CO_CODABLE_PREDICATE_PAIRS` (`extract.build`'s own overlap
#: resolution — this list's order is itself a priority, never re-sorted
#: per input). `except_when` is ordered BEFORE `applies_to`/
#: `cross_references` (required fix 4).
RULES: "list[Rule]" = [
    Rule("is_a", _find_is_a),
    Rule("part_of", _find_part_of),
    Rule("except_when", _find_except_when),
    Rule("applies_to", _find_applies_to),
    Rule("cross_references", _find_cross_references),
    Rule("deadline_of", _find_deadline_of),
    Rule("requires", _find_requires),
    Rule("precedes", _find_precedes),
    Rule("based_on", _find_based_on),
    Rule("enables", _find_enables),
    Rule("purpose", _find_purpose),
    Rule("competence_and_performs", _find_competence_and_performs),
    Rule("predication", _find_predication),
    Rule("predication_whole_unit", _find_predication_whole_unit),
]


def collect_candidates(unit_text: str, *, enclosing_provision: Optional[str] = None) -> "list[Candidate]":
    """Run every rule in :data:`RULES`, in order, over ``unit_text``.
    Returns candidates UNFILTERED (span finalisation and overlap
    resolution are `extract.build.extract_with_spans`'s own job) — this
    function is pure cue-matching, nothing else. ``enclosing_provision``
    (round-2 item 8) is forwarded, inside a ``context`` dict, to every
    rule — only the purpose router reads it today."""
    context = {"enclosing_provision": enclosing_provision}
    out: "list[Candidate]" = []
    for rule in RULES:
        out.extend(rule.finder(unit_text, context))
    return out


#: round-4 item: the LAST-RESORT fallback's own rule id (`_find_
#: predication_whole_unit`) — the only rule id a chapeau-subject
#: inheritance override ever applies to (see
#: :func:`collect_segmented_candidates`'s own docstring).
_WHOLE_SPAN_FALLBACK_RULE_ID = "T3-predication-whole-unit-fallback"

#: A chapeau's own cue is often TRUNCATED right at the list boundary —
#: "The definition has effect subject to—" carries NO provision word of
#: its own (the provision references are the separate list items), so
#: none of the ordinary sentence-shaped rules above (which expect a cue
#: AND its own object in the SAME text) ever fire on the chapeau text
#: alone. These CHAPEAU-ONLY patterns match a cue at the very END of the
#: chapeau's own (trimmed) text, with everything BEFORE it as `subj` —
#: the predicate the trigger implies is then inherited by every list
#: item under this chapeau (`collect_segmented_candidates`'s own
#: "Chapeau TRIGGER inheritance").
_CHAPEAU_ONLY_SUBJECT_TO_RE = re.compile(r"^(?P<subj>.*?)\bsubject\s+to\s*$", re.IGNORECASE | re.DOTALL)
_CHAPEAU_ONLY_UNLESS_RE = re.compile(r"^(?P<subj>.*?)\bunless\s*$", re.IGNORECASE | re.DOTALL)
_CHAPEAU_ONLY_POWER_RE = re.compile(
    r"^(?P<subj>.*?)\bshall\s+have\s+the\s+(?:tasks?|powers?)\s+to\s*$", re.IGNORECASE | re.DOTALL
)
_CHAPEAU_ONLY_RESPONSIBLE_RE = re.compile(
    r"^(?P<subj>.*?)\b(?:is|are)\s+responsible\s+for\s*$", re.IGNORECASE | re.DOTALL
)
#: the generic case — a chapeau whose own text is an ordinary actor +
#: modal clause pointing forward to its own list ("Each supervisory
#: authority shall perform the following tasks:") — the actor NP is
#: `subj`; every item is one `performs`/`competence_of` act.
_CHAPEAU_ONLY_GENERIC_MODAL_RE = re.compile(
    r"^(?P<subj>" + ACTOR_NP_FRAGMENT + r")\b.*?\b(?:shall|may|must|should)\b", re.IGNORECASE | re.DOTALL
)


def _tighten_subj_with_np_chunks(text: str, subj_span: "tuple[int, int]") -> "tuple[int, int]":
    """A chapeau-only trigger's own `subj` regex group
    captures "whatever text came before the cue" — often more than the
    SUBJECT noun phrase itself ("The definition has effect" before
    "subject to—", when only "definition" is the actual subject; "has
    effect" is the verb phrase). `np_chunks` (R-k/R-q already applied)
    finds the real noun-phrase chunks inside that span; the FIRST one
    found (the subject position, read left to right) replaces the raw
    regex span. Falls back to the raw span, UNCHANGED, if `np_chunks`
    finds nothing inside it (never worse than before)."""
    s0, s1 = subj_span
    for cs, ce in _segment.np_chunks(text[s0:s1]):
        return (s0 + cs, s0 + ce)
    return subj_span


def _detect_chapeau_only_trigger(chapeau_text: str) -> Optional[Candidate]:
    """``subj_span`` on the returned `Candidate` is RELATIVE to
    ``chapeau_text`` itself (the caller translates it to an absolute
    offset) — `obj_span`/`clause_span` are meaningless placeholders here
    (the caller supplies the real ones, per list item). ``subj_span`` is
    the FIRST `np_chunks` chunk found inside the raw regex "subj" group
    (`_tighten_subj_with_np_chunks`), not that raw group itself."""
    for pattern, predicate, rule_id, section in (
        (_CHAPEAU_ONLY_SUBJECT_TO_RE, "except_when", "T3-except_when-subject-to-provision-chapeau-only",
         "`except_when` — structural: \"subject to [provision]\" routing test "
         "(chapeau-only: the cue ends the chapeau, the provision references are the list items)"),
        (_CHAPEAU_ONLY_UNLESS_RE, "except_when", "T3-except_when-unless-chapeau-only",
         "`except_when` — structural: \"unless\" cue (chapeau-only)"),
        (_CHAPEAU_ONLY_POWER_RE, "competence_of", "T3-competence_of-shall-have-power-chapeau-only",
         "`competence_of` — relational: \"shall have the task/power to\" (conferral, chapeau-only)"),
        (_CHAPEAU_ONLY_RESPONSIBLE_RE, "competence_of", "T3-competence_of-responsible-for-chapeau-only",
         "`competence_of` — relational: the \"responsible for\" conferral rule (chapeau-only)"),
    ):
        m = pattern.search(chapeau_text)
        if m:
            subj_text = m.group("subj").strip()
            is_institutional = bool(INSTITUTIONAL_ACTOR_SURFACE_RE.search(subj_text))
            final_predicate = predicate
            if predicate == "competence_of" and not is_institutional:
                final_predicate = "performs"
            return Candidate(
                rule_id=_cite(rule_id, section), predicate=final_predicate,
                clause_span=(0, len(chapeau_text)),
                subj_span=_tighten_subj_with_np_chunks(chapeau_text, m.span("subj")), obj_span=(0, 0),
                base_confidence=0.45,
            )
    m = _CHAPEAU_ONLY_GENERIC_MODAL_RE.search(chapeau_text)
    if m:
        subj_text = m.group("subj").strip()
        is_institutional = bool(INSTITUTIONAL_ACTOR_SURFACE_RE.search(subj_text))
        predicate = "competence_of" if is_institutional else "performs"
        return Candidate(
            rule_id=_cite(f"T3-{predicate}-chapeau-generic-modal",
                           f"`{predicate}` — relational: chapeau actor + modal, pointing at its own list"),
            predicate=predicate,
            clause_span=(0, len(chapeau_text)),
            subj_span=_tighten_subj_with_np_chunks(chapeau_text, m.span("subj")), obj_span=(0, 0),
            base_confidence=0.4,
        )
    return None


def _segment_scan_spans(segs: "list[dict]") -> "list[dict]":
    """A `clause` node can itself have CHILD
    `clause` nodes (`segment.py`'s own `clause_parts()` — a coordinated
    clause complex such as "X shall do A and Y shall do B" is emitted as
    ONE parent clause spanning the whole complex, PLUS two child clauses,
    one per conjunct). Scanning EVERY clause/list_item node, parent and
    child alike, cue-scans the SAME text twice (once per the parent's
    own full span, once per each child's own sub-span) — the two scans'
    own candidates then compete for overlapping territory in `extract.
    build`'s own overlap resolution, and the wrong one can win (a
    `deadline_of` candidate from the WHOLE parent span beating out the
    two per-conjunct `performs` candidates the children alone would have
    given). The fix: a `clause`/`list_item` node is a scan span ONLY
    when it is a LEAF — it has no `clause`/`list_item` child of its
    own — plus a childless `sentence`/`chapeau` container (the SAME
    convention the segmenter comparison's own dev scorer uses: "a
    childless container is kept")."""
    children_by_kind: "dict[int, set]" = {}
    for s in segs:
        parent = s.get("parent")
        if parent is not None:
            children_by_kind.setdefault(parent, set()).add(s["kind"])
    out = []
    for i, s in enumerate(segs):
        child_kinds = children_by_kind.get(i, set())
        if s["kind"] in ("clause", "list_item"):
            if not (child_kinds & {"clause", "list_item", "chapeau"}):
                out.append(s)
        elif s["kind"] in ("sentence", "chapeau") and not child_kinds:
            out.append(s)
    return out


def collect_segmented_candidates(
    unit_text: str, *, enclosing_provision: Optional[str] = None,
    segmenter_cfg=None,
) -> "list[Candidate]":
    """The pipeline's own entry point: segment
    ``unit_text`` first (`extract.segment.segment` — the comparison's
    winning recursive-descent grammar, grafted per the comparison's own
    decision), then run :func:`collect_candidates`'s own closed cue-rule
    table PER CLAUSE/LIST-ITEM SPAN rather than once over the whole unit.

    This is what lets a unit contribute MORE than one Statement where the
    codebook permits it (dev gold averages ~1.8 distinct clauses but ~2.8
    Statements per unit — several clauses each carrying more than one
    cue) — every clause/list-item span gets its OWN independent cue scan,
    with absolute offsets, and `extract.build`'s own overlap resolution
    (co-coding pairs, chapeau-group exemption) still runs over the
    combined result exactly as before.

    **Chapeau-subject inheritance** (``inherits_subject_from``): when a
    scan span is a list item (or a ';'-tail clause) under a chapeau, and
    cue-matching inside the item's OWN text produced NOTHING but the
    last-resort whole-span fallback (`_WHOLE_SPAN_FALLBACK_RULE_ID` — no
    real cue fired, so the fallback's own crude word-split subject is not
    a real actor), that fallback candidate's own ``subj_span`` is
    REPLACED with the chapeau's own absolute span — the codebook's own
    chapeau rule ("the subject is INHERITED from the chapeau"), applied
    at the one point this extractor's simple per-clause cue rules cannot
    already see the chapeau's own subject for themselves.

    **Chapeau TRIGGER inheritance**: the cue that governs a whole chapeau
    + list ("has effect subject to—", "shall have the power to—") very
    often sits in the CHAPEAU's own text, not in any one item's — a bare
    list item ("subsection (2)") carries no cue of its own at all. For
    EVERY chapeau node, this function also runs `collect_candidates` on
    the CHAPEAU's own text alone; the first (highest rule-priority) NON-
    fallback candidate found there, if any, is that chapeau's own
    "trigger". When an item's own scan found NOTHING but the whole-span
    fallback AND its chapeau has a discovered trigger, the item's
    fallback candidate is REPLACED by a new candidate carrying the
    trigger's own predicate/rule_id/dimension-relevant fields, with
    `subj` inherited from the trigger's own (translated) subj span and
    `obj` the item's own full span — e.g. "The definition ... has effect
    subject to— (a) subsection (2), (b) section 209" yields THREE
    `except_when` Statements, one per item, each sharing the chapeau
    trigger's own subj, never three copies of the generic predication
    fallback.

    Falls back to the OLD whole-unit scan (:func:`collect_candidates`
    over the ENTIRE text, unsegmented) when segmentation finds no scan
    span at all — a defensive fallback, not the common path."""
    if segmenter_cfg is None:
        segmenter_cfg = _segment.DEFAULT_CONFIG
    segs = _segment.segment(unit_text, enclosing_provision=enclosing_provision, cfg=segmenter_cfg)
    scan_spans = _segment_scan_spans(segs)
    if not scan_spans:
        return collect_candidates(unit_text, enclosing_provision=enclosing_provision)

    chapeau_triggers: "dict[int, Candidate]" = {}
    for idx, node in enumerate(segs):
        if node["kind"] != "chapeau":
            continue
        chapeau_text = unit_text[node["start"]:node["end"]]
        start = node["start"]
        # round-5 fix: try the SPECIFIC chapeau-only patterns FIRST — a
        # truncated cue like "...shall have the task to—" also happens
        # to match the GENERIC "actor NP + shall + obj" performs rule
        # (treating "have the task to" as an ordinary act), which would
        # otherwise win by rule order and route a genuine competence_of
        # conferral through performs instead. Only when NO chapeau-only
        # pattern matches does this fall back to the ordinary cue table.
        chapeau_only = _detect_chapeau_only_trigger(chapeau_text)
        if chapeau_only is not None:
            s0, s1 = chapeau_only.subj_span
            chapeau_triggers[idx] = replace(
                chapeau_only, subj_span=(s0 + start, s1 + start), clause_span=(start, node["end"]),
            )
            continue
        chapeau_cands = collect_candidates(chapeau_text, enclosing_provision=enclosing_provision)
        for cand in chapeau_cands:
            if cand.rule_id in (_WHOLE_SPAN_FALLBACK_RULE_ID, "T3-predication-copula-fallback"):
                continue
            chapeau_triggers[idx] = replace(
                cand,
                clause_span=(cand.clause_span[0] + start, cand.clause_span[1] + start),
                subj_span=(cand.subj_span[0] + start, cand.subj_span[1] + start) if cand.subj_span else None,
                obj_span=(cand.obj_span[0] + start, cand.obj_span[1] + start) if cand.obj_span else None,
            )
            break

    out: "list[Candidate]" = []
    for idx, span in enumerate(scan_spans):
        start, end = span["start"], span["end"]
        sub_text = unit_text[start:end]
        sub_candidates = collect_candidates(sub_text, enclosing_provision=enclosing_provision)

        chapeau_abs_span = None
        trigger = None
        inh = span.get("inherits_subject_from")
        if inh is not None and 0 <= inh < len(segs):
            chapeau_node = segs[inh]
            chapeau_abs_span = (chapeau_node["start"], chapeau_node["end"])
            trigger = chapeau_triggers.get(inh)

        only_fallback_fired = (
            len(sub_candidates) == 1 and sub_candidates[0].rule_id == _WHOLE_SPAN_FALLBACK_RULE_ID
        )
        for cand in sub_candidates:
            translated = replace(
                cand,
                clause_span=(cand.clause_span[0] + start, cand.clause_span[1] + start),
                subj_span=(cand.subj_span[0] + start, cand.subj_span[1] + start) if cand.subj_span else None,
                obj_span=(cand.obj_span[0] + start, cand.obj_span[1] + start) if cand.obj_span else None,
            )
            if only_fallback_fired and cand.rule_id == _WHOLE_SPAN_FALLBACK_RULE_ID:
                if trigger is not None:
                    translated = replace(
                        translated,
                        rule_id=_cite(f"{trigger.rule_id}-chapeau-inherited-item",
                                       f"{RULE_CITATIONS.get(trigger.rule_id, trigger.rule_id)} "
                                       "(inherited by a chapeau-list item with no cue of its own)"),
                        predicate=trigger.predicate,
                        subj_span=trigger.subj_span,
                        obj_span=(start, end),
                        negation_force=trigger.negation_force,
                        base_confidence=min(trigger.base_confidence, 0.5),
                        truncate_midspan_modal=False,
                        strip_modal_obj=False, strip_subject_and_modal_obj=False,
                        chapeau_group=f"chapeau-trigger-{inh}",
                    )
                elif chapeau_abs_span is not None:
                    translated = replace(
                        translated, subj_span=chapeau_abs_span, chapeau_group=f"chapeau-fallback-{inh}",
                    )
            out.append(translated)
    return out
