# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""The assertoric layer (D1) — lowering an already-bounded clause to a 5D link.

spec/SPEC.md §8. Rules VENDORED — not reinvented — from loomground-factual
@ ``ebf9fe1`` (release 0.2.0, the CURRENT GitHub head as of 2026-10-01;
read-only, cloned fresh from ``https://github.com/flxk1/loomground-factual``
— the local sibling clone under ``~/Documents/...`` was found to be 9
commits stale and is NO LONGER the reference source for this module):
``grammar.py``'s ``lower()``/``_clause()``/``_candidates()`` and
``artifacts/extraction.json``/``artifacts/binding.json``.

**This is a full re-derivation, not a patch.** Factual @ ebf9fe1 no longer
has a single ``_STRUCT`` regex (the whole-sentence scan this module once
vendored is gone upstream); it now recognises THREE cue kinds — a
copula, a temporal ORDERING cue, and a MODAL auxiliary — and looks up the
dimension from a fixed relation name via ``binding.json``, not from a
pattern match over the sentence text.

**Cue kinds, in the order ``_candidates()`` tries them** (earliest START
wins; a tie is broken by LONGEST match; a further tie by kind order
`ORDER (0) < COPULA (1) < MODAL (2)` — "maximal munch": "is required to"
beats the bare copula "is"; "is followed by" beats the copula "is"; "shall
be" beats the modal "shall"):

  * **COPULA** — ``predicate_cues.copula`` (``is``/``are``/``shall be``/
    ``means``/``include(s)``/``consist(s) of``/``refer(s) to``). The
    relation defaults to ``predication`` (RELATIONAL); THEN
    ``predicate_cues.relations`` (``is-a``, ``part-of``, ``has-part``) is
    searched over the WHOLE clause — if one matches, the relation becomes
    that name (STRUCTURAL, via ``binding.json``), and for ``part-of``/
    ``has-part`` (which carry a named group ``rel``) the PREDICATE itself
    becomes the matched relation phrase (e.g. "part of"), not the bare
    copula.
  * **ORDER** — ``ordering_cues`` (``precedes``/``comes before``/``takes
    place before``/``is followed by`` → relation ``precedes``;
    ``follows``/``comes after``/``takes place after``/``succeeds`` →
    relation ``follows``). The relation is the cue's OWN name — TEMPORAL
    via ``binding.json``. This is new since the stale snapshot: an ordering
    sentence (e.g. "Registration precedes processing.") now lowers
    TEMPORAL, something an earlier draft of this specification incorrectly
    claimed the assertoric layer "never produces" ("always structural or
    relational") — that claim has been corrected.
  * **MODAL** — ``modal_cues.modal`` (``must``/``shall``/``should``/
    ``may``/``can``/``could``/``might``/``will``/``would``/``(is|are)
    required to``/``(has|have) to``/``ought to``, with an optional
    ``not`` captured as negation): the auxiliary is stripped, the next bare
    verb token becomes the predicate, and the relation is ALWAYS
    ``predication`` (RELATIONAL) — regardless of what the clause's REST
    contains. This is the modal rule an earlier draft got wrong: "The
    controller must ensure that the system is a secure system." lowers
    RELATIONAL (the modal fires first and hard-codes ``predication``), even
    though the embedded "is a secure system" would, on its own, read as an
    is-a/STRUCTURAL copula — the modal cue's relation assignment does not
    re-scan the rest of the clause for a copula relation at all. A
    ``modal_cues.temporal_subordinate`` cue (``before``/``prior to``/
    ``until`` → ``precedes``; ``after``/``once``/``following`` →
    ``follows``) found in the remaining text after the verb trims the
    OBJECT boundary there (the dependent clause it introduces is a SEPARATE
    fact, out of scope for a single assertion's own object) but does not
    change THIS clause's own relation/dimension.

A ``complement_cues.clausal_complement`` cue (``knows``/``believes``/``is
aware``/... + ``that``) found ANYWHERE in the full sentence means the
sentence is NOT itself a fact about its own subject: only the clause AFTER
the complement cue's match is lowered (its own subject, predicate, object,
dimension) — the attitude verb and its subject are discarded, exactly as
factual's ``_analyse()`` does.

Negation and quantification, UNCHANGED from the prior round's cue-level
rules (vendored from ``polarity_cues``/``quantifier_cues``, same patterns
as before): ``empty`` quantification (``no``/``none of``/``neither`` over
the clause's own SUBJECT text) always forces ``negated`` true. For a COPULA
or ORDER clause, an additional object-side ``_NEG`` scan (over the first 24
characters of the object, BEFORE its leading determiner is stripped) also
forces negation; a MODAL clause instead ORs in the modal cue's own captured
``not`` group. (ORDER-kind clauses have NO object-side ``_NEG`` scan at
all — only ``empty`` quantification can negate one; this matches factual's
own code exactly, which is deliberately narrower there than the copula
path.)

A content clause (an infinitive/bare-verb clause with no subject of its
own, e.g. the action a norm's modal auxiliary and bearer have already been
peeled off elsewhere) lowers ONLY through factual's own
``plane.produce()``'s ``context`` parameter, NEVER through ``lower()`` —
and this module is the ``lower()`` equivalent, not the ``produce()`` one.
Subject-resolution machinery for that shape (a document-defined-terms
registry, pronoun/named-subject detection, an enclosing discourse frame
stack) is sentence/discourse-level reasoning this specification has always
kept OUT OF SCOPE (§1), and ``lower()`` itself never reaches any of it
either (it receives no ``context``) — so none of it is vendored here.

5D is neutral on is/ought (§7, N1 — owner design change, 2026-10-01): a 5D
link, including the ones this module produces, carries exactly one
dimension and nothing else. Whether a relation is normative is nD-grammar
knowledge (a co-dimension on that grammar's own NDSystem, §9), never a
concern of the assertoric layer or of 5D itself.

See ``tests/test_conformance.py``'s differential test, which compares this
module's output against loomground-factual's real ``lower()`` output,
sentence for sentence, on factual's own ``tests/test_extraction_quality.py``
CASES, its ``artifacts/examples.json`` examples, its cue-tiebreak/negated-
required/none-path pinning tests, AND ten additional cross-cutting
sentences, when that package is importable — 0 differences across all of
them (verified by hand before this module was written; see the commit
message for the count).

Stdlib only.
"""
from __future__ import annotations

import re
from typing import Optional

__all__ = [
    "QUANTIFIERS",
    "RELATIONS",
    "BINDING",
    "lower_assertion",
]

#: The three quantifier values an already-bounded clause may carry.
QUANTIFIERS = ("universal", "existential", "empty")

# ── vendored cues (loomground-factual @ ebf9fe1, artifacts/extraction.json) ──
_COP_RE = re.compile(
    r"\b(?:is|are|shall be|means|include[sd]?|consists? of|refers? to)\b", re.IGNORECASE)

# predicate_cues.relations — order matters only in that each is independently
# searched over the whole clause; the FIRST one (in this fixed order, matching
# the JSON's own key order) that matches wins, exactly as factual's own
# `for name, pat in _RELATIONS` loop (dict iteration order == JSON key order).
_RELATIONS = (
    ("is-a", re.compile(
        r"\b(?:is|are|shall be)\s+(?:not\s+)?(?:a|an|one of(?: the)?|a type of|a kind of|"
        r"a category of)\b", re.IGNORECASE)),
    ("part-of", re.compile(
        r"\b(?:is|are|shall be)\s+(?:not\s+)?(?P<rel>part of)\b", re.IGNORECASE)),
    ("has-part", re.compile(
        r"\b(?:is|are|shall be)\s+(?:not\s+)?(?P<rel>comprised of|composed of)\b",
        re.IGNORECASE)),
)
_DEFAULT_RELATION = "predication"

# ordering_cues — (name, pattern, canonical, converse) — vendored verbatim
# from artifacts/extraction.json's ordering_cues. "canonical"/"converse" are
# NOT the relation bound to a dimension (that is still `name` itself, via
# BINDING) — they are a SEPARATE piece of information factual's own
# `_clause()` carries (as the "canonical" field of its full record, visible
# through `_analyse()` though stripped out of the public `lower()`): which
# way the pair of entities relates once normalised onto a single reading.
# "follows" and "precedes" bind to the SAME dimension (temporal) but are
# OPPOSITE directions; without `canonical`/`converse`, an ordering fact's
# own direction is lost the moment two facts using different cues need to be
# compared or composed.
_ORDERING = (
    ("precedes", re.compile(
        r"\b(?:precedes?|comes? before|takes? place before|is followed by|"
        r"are followed by)\b", re.IGNORECASE), "precedes", False),
    ("follows", re.compile(
        r"\b(?:follows?|comes? after|takes? place after|succeeds?)\b",
        re.IGNORECASE), "precedes", True),
)

# modal_cues.modal — the auxiliary, with an optional captured "not".
_MODAL_RE = re.compile(
    r"\b(?:must|shall|should|may|can|could|might|will|would|(?:is|are) required to|"
    r"(?:has|have) to|ought to)(?:\s+|(?<=can)(?=not\s))(?P<neg>not\s+)?(?=[a-z])",
    re.IGNORECASE,
)
# modal_cues.temporal_subordinate — trims a MODAL clause's own object boundary
# only; never changes the clause's own relation (always predication).
_SUBORDINATE = (
    ("precedes", re.compile(r"\s+(?:before|prior to|until)\s+", re.IGNORECASE)),
    ("follows", re.compile(r"\s+(?:after|once|following)\s+", re.IGNORECASE)),
)

# complement_cues.clausal_complement — "X knows that P": only P is lowered.
_COMPLEMENT_RE = re.compile(
    r"\b(?:knows?|believes?|is aware|are aware|becomes? aware|considers?|finds?|states?|"
    r"establishe[sd]|holds?|is satisfied|are satisfied)\s+that\s+", re.IGNORECASE)

_NEG_RE = re.compile(r"\b(?:not|no|never|neither|without)\b", re.IGNORECASE)
_UNIV_RE = re.compile(r"\b(?:all|any|every|each)\b", re.IGNORECASE)
_EMPTY_RE = re.compile(r"\b(?:no|none of|neither)\b", re.IGNORECASE)

_MARKERS_RE = re.compile(
    r"^(?:[-–—•*]\s*|\(\s*[0-9a-z]{1,3}\s*\)\s*|[0-9]+(?:\.[0-9]+)*\.?\s+)+",
    re.IGNORECASE)
_LEAD_RE = re.compile(
    r"^(?:a|an|the|its|their|any|this|each|every|all|both|such|no|der|die|das|ein|eine|"
    r"jede[rs]?)\s+", re.IGNORECASE)
_TRAIL_RE = re.compile(
    r"\s+(?:which\b|who\b|whose\b|to which\b|as referred to\b|referred to in\b|"
    r"pursuant to\b|adopted by\b|involved in\b|of the (?:main|seconding)\b).*$",
    re.IGNORECASE)
_OBJ_LEAD_RE = re.compile(
    r"^(?:not\s+)?(?:a|an|the|one of(?: the)?|part of)\s+", re.IGNORECASE)
_VERB_RE = re.compile(r"\s*([A-Za-z][A-Za-z-]*)")
_TRIM = " .,;:"

# artifacts/binding.json — the ONE place factual writes its relation -> 5D map.
BINDING: "dict[str, str]" = {
    "is-a": "structural",
    "part-of": "structural",
    "has-part": "structural",
    "precedes": "temporal",
    "follows": "temporal",
    "predication": "relational",
}
#: The relation names :data:`BINDING` is keyed by, in ``binding.json``'s own order.
RELATIONS = tuple(BINDING)

_ORDER_KIND, _COPULA_KIND, _MODAL_KIND = 0, 1, 2


def _clean_entity(span: str) -> str:
    """Reduce a span to its addressee/entity NP head — vendored verbatim from
    factual's ``clean_entity()``."""
    s = _MARKERS_RE.sub("", (span or "").strip()).strip()
    if "," in s:
        s = s.rsplit(",", 1)[-1].strip()
    s = _LEAD_RE.sub("", s).strip()
    s = _TRAIL_RE.sub("", s).strip()
    return s.strip(_TRIM)


def _quantification(subj_raw: str) -> str:
    if _EMPTY_RE.search(subj_raw):
        return "empty"
    if _UNIV_RE.search(subj_raw):
        return "universal"
    return "existential"


def _candidates(text: str) -> list:
    """Every cue hit as ``(start, kind, hit, length)``, sorted earliest-start,
    then longest match, then kind order — vendored verbatim from factual's
    ``_candidates()``."""
    out = []
    m = _COP_RE.search(text)
    if m:
        out.append((m.start(), _COPULA_KIND, m, len(m.group(0).rstrip())))
    for name, pat, canonical, converse in _ORDERING:
        om = pat.search(text)
        if om:
            out.append((om.start(), _ORDER_KIND, (om, name, canonical, converse),
                        len(om.group(0).rstrip())))
    mm = _MODAL_RE.search(text)
    if mm:
        out.append((mm.start(), _MODAL_KIND, mm, len(mm.group(0).rstrip())))
    out.sort(key=lambda c: (c[0], -c[3], c[1]))
    return out


def _lower_clause(text: str) -> Optional[dict]:
    """Lower ``text`` (an already-bounded clause — see the module docstring
    for what "already bounded" excludes) — vendored verbatim from factual's
    ``_clause()``, minus the ``span``/``subordinate`` bookkeeping this module
    has no use for (``canonical`` IS kept — see
    :func:`lower_assertion`'s docstring — an ordering fact's own direction
    would otherwise be lost). Returns ``None`` on any of ``lower()``'s three
    documented abstention paths.
    """
    cands = _candidates(text)
    if not cands:
        return None
    _, kind, hit, _ = cands[0]
    canonical = None
    if kind == _COPULA_KIND:
        m = hit
        subj_raw = text[: m.start()]
        obj_raw = text[m.end():].strip()
        relation, predicate, obj_src = _DEFAULT_RELATION, m.group(0).strip().lower(), obj_raw
        for name, pat in _RELATIONS:
            rm = pat.search(text)
            if rm:
                relation = name
                if "rel" in pat.groupindex and rm.group("rel"):
                    predicate = rm.group("rel").lower()
                    obj_src = _OBJ_LEAD_RE.sub("", text[rm.end():].strip())
                break
        obj = _OBJ_LEAD_RE.sub("", obj_src).strip(_TRIM)
        quant = _quantification(subj_raw)
        negated = quant == "empty" or bool(_NEG_RE.search(obj_raw[:24]))
    elif kind == _ORDER_KIND:
        m, relation, ordering_canonical, converse = hit
        subj_raw = text[: m.start()]
        obj = _OBJ_LEAD_RE.sub("", text[m.end():].strip()).strip(_TRIM)
        predicate = m.group(0).strip().lower()
        quant = _quantification(subj_raw)
        negated = quant == "empty"
        canonical = (ordering_canonical, converse)
    else:  # MODAL: strip the auxiliary, keep the propositional content
        m = hit
        subj_raw = text[: m.start()]
        vm = _VERB_RE.match(text, m.end())
        if not vm:
            return None
        predicate = vm.group(1).lower()
        rest_start = vm.end()
        rest_end = len(text)
        for _name, pat in _SUBORDINATE:
            sm = pat.search(text, rest_start)
            if sm and sm.start() < rest_end:
                rest_end = sm.start()
        obj = _OBJ_LEAD_RE.sub("", text[rest_start:rest_end].strip()).strip(_TRIM)
        relation = _DEFAULT_RELATION
        quant = _quantification(subj_raw)
        negated = quant == "empty" or bool(m.group("neg"))
    subject = _clean_entity(subj_raw)
    if not subject or not obj:
        return None
    return {
        "subject": subject,
        "predicate": predicate,
        "object": obj,
        "dimension": BINDING[relation],
        "negated": negated,
        "quantification": quant,
        "relation": relation,
        "canonical": canonical,
    }


def lower_assertion(sentence: str) -> Optional[dict]:
    """Lower ``sentence`` into a 5D link, or ``None`` on one of ``lower()``'s
    three documented abstention paths (no cue fires at all; a modal cue
    fires with no verb following it; the extracted subject or object is
    empty once trimmed).

    ``sentence`` is the FULL already-bounded sentence/clause text — sentence
    boundary determination (splitting a paragraph into sentences) is OUT OF
    SCOPE (§1), but a clausal complement (``"X knows that P"``) IS handled
    here (it is a single, bounded, data-driven cue, not open-ended
    discourse parsing): when ``complement_cues.clausal_complement`` matches
    anywhere in ``sentence``, only the clause AFTER that match is lowered.

    Returns ``{"subject", "predicate", "object", "dimension", "negated",
    "quantification", "relation", "canonical"}`` on success — these are
    EXACTLY factual's own ``lower()`` fields (``subject``/``predicate``/
    ``object``/``dimension``/``negated``/``quantification``), PLUS the two
    fields factual's own ``_analyse()``/``_clause()`` carries but its public
    ``lower()`` drops (``lower()`` returns only the inner ``"fact"``
    sub-dict; this module keeps the two fields from the OUTER record it
    would otherwise lose): ``relation`` (the exact relation name bound via
    :data:`BINDING` — ``is-a``/``part-of``/``has-part``/``precedes``/
    ``follows``/``predication``) and ``canonical`` (``None`` for a COPULA or
    MODAL clause; for an ORDER clause, ``(canonical_name, converse)`` —
    e.g. a ``"follows"`` clause carries ``("precedes", True)``, meaning its
    direction is the CONVERSE of ``precedes``, so an ordering fact's own
    direction is never lost even though ``precedes`` and ``follows`` share
    one dimension, ``temporal``). ``dimension`` is one of ``structural``
    (is-a/part-of/has-part), ``temporal`` (precedes/follows — an ORDERING
    clause) or ``relational`` (predication — the 5D floor, including every
    MODAL clause); ``causal``/``intentional`` are reached only through an
    nD grammar's own binding (§9), never through this layer. Raises
    ``ValueError`` if ``sentence`` is not a non-empty string (fail closed).
    """
    if not isinstance(sentence, str) or not sentence.strip():
        raise ValueError("lower_assertion() requires a non-empty sentence string")
    cm = _COMPLEMENT_RE.search(sentence)
    clause = sentence[cm.end():] if cm else sentence
    return _lower_clause(clause)
