# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""EXAMPLE nD grammar — "interplay", typed relations between legal
instruments (§9).

**Why this grammar exists.** 5D's own typed-statements enum (§21) has a
predicate for a plain, untyped `cross_references` edge between two
provisions, but nothing that TYPES the relation between two different
INSTRUMENTS. An EU digital-law corpus (GDPR, the ePrivacy Directive, the
DSA, NIS2, the AI Act, plus the GDPR's own repealed predecessor, Directive
95/46/EC, and the e-Commerce Directive) routinely states, IN THE TEXT
ITSELF, exactly what KIND of relation holds between two instruments on a
given matter: GDPR Art. 95 bars a second, additional obligation with the
"same objective"; GDPR Art. 94(2) redirects every reference to its own
repealed predecessor; the DSA and the AI Act both say, in so many words,
that they do not affect the GDPR; NIS2 Art. 35(2) bars a second fine for
the "same conduct" already fined under the GDPR; NIS2 Art. 35(1) requires
its own competent authorities to notify the GDPR's supervisory
authorities; NIS2 Art. 2(14) requires personal-data processing under this
instrument to proceed "in accordance with" the GDPR. None of this is
`cross_references` — this grammar supplies a CLOSED, NAMED vocabulary of
relation types (below), each with its own 5D projection.

**Rules are DATA, not code** — exactly the discipline
`five_d_nd.grammars.requirement` already establishes (see that module's
own docstring): the cue table (trigger phrase, required co-occurring
phrase, target-resolution mode, confidence) lives in
``interplay_rules.json``, loaded by :func:`load_ruleset` and PINNED BY A
SHA-256 DIGEST (:func:`ruleset_digest`, via ``five_d_nd.grounding.digest`
— the same canonical-JSON/sha256 machinery every other digest in this
package uses). :func:`find_relations` branches on nothing but the loaded
ruleset document; a new cue is added by editing the JSON, never by adding
an `if`.

**The relation vocabulary is CLOSED and EXTERNAL to 5D itself** — it is
this grammar's own nD axis (§9's `NDSystem.axes`), never a sixth 5D
dimension. Each of the ten relations below declares EXACTLY ONE of the
five 5D dimensions it projects onto, with a stated reason (also recorded
machine-readably in :func:`build_descriptor`'s `binding`):

* ``same_definition`` -> **structural** — a definitional cross-reference
  is a structural "is-defined-as"/part-of-like link between two concepts
  (§2: "structural for is-a, part-of and has-part"), not a causal or
  temporal one.
* ``cumulative`` -> **relational** — both regimes simply co-apply to the
  same conduct; a plain co-application link with no causal, structural,
  or temporal content of its own.
* ``complementary`` -> **relational** — B adds obligations within the
  same matter as A; still a co-application relation, not a cause/effect
  or a structural containment.
* ``alternative`` -> **causal** — WHICH instrument governs is determined
  by a triggering/scope condition stated in the clause; selecting between
  two alternatives by a condition is a conditional (causal) gate.
* ``substitutive`` -> **causal** — compliance with A is stated to CAUSE
  (discharge, satisfy) B's own obligation; a causal "satisfies" effect.
* ``separate_tracks`` -> **relational** — two independent regimes relate
  to the same act without either one causing or structurally containing
  the other; a coordination duty (e.g. "inform the other authority") is
  the SURFACE FORM the clause uses to state the coexistence, not itself
  the relation being typed.
* ``non_cumulative`` -> **causal** — an express bar PREVENTS a second
  legal consequence (a second obligation, a second fine) from arising at
  all; a causal prevention edge.
* ``no_presumption`` -> **causal** — compliance with A is stated NOT to
  CAUSE (give rise to, create) a presumption of compliance under B; a
  causal non-effect statement.
* ``defers_to`` -> **structural** — "without prejudice to" / "shall not
  affect" restates which instrument's provisions control on the matter —
  a structural subordination of this instrument's own force to another's.
  §21's own typed-statement predicate table binds a SAVINGS CLAUSE of
  exactly this shape to `cross_references` (structural): "A SAVINGS
  CLAUSE ('without prejudice to X', 'shall not affect X') is ... a
  non-overriding link from the host provision to X" — the same structural
  reading this relation gives it, one level up (between INSTRUMENTS
  rather than between provisions).
* ``reference_redirect`` -> **structural** — the clause literally rewires
  a textual reference from one instrument's identity to another's; a
  structural identity-redirect, the same dimension §21 assigns
  `cross_references` (a citation to another provision) for the identical
  reason — the relation is about WHICH TEXT an identifier now resolves
  to, not about a cause, a purpose, or an ordering.

**Negation / absence are OUT OF SCOPE for this grammar.** Unlike
`requirement.py`'s three-state lexical-absence design, this grammar
reports ONLY what a clause POSITIVELY states (a cue fired, with its
required co-occurring phrase present) — there is no "this relation is
absent" claim to make, because the grammar's own job is to TYPE a stated
relation, never to certify one is missing.

**Clause extraction is a bounded, deterministic window, not full sentence
segmentation.** Each cue's `trigger_pattern` marks where a candidate
clause STARTS; the clause's own text runs from there to the first
sentence-ending punctuation (`.`/`;`) found within `max_span_chars`, or to
`max_span_chars` itself if none is found first (see
:func:`_clause_span`). This is deliberately simpler than
`requirement.py`'s own sentence-boundary machinery (negation lexicon,
abbreviation detection) — a scope clause of the kind this grammar reads is
reliably self-contained within one bounded window, and the verbatim span
recorded is always the EXACT source text of that window, never a
paraphrase.

**Target resolution — three modes, named per cue, never inferred.**
`target_mode == "cited"` searches the EXTRACTED CLAUSE TEXT (widened by
the cue's own `target_lookback_chars` when set — some clauses, e.g. NIS2
Art. 35(2), name the OTHER instrument BEFORE the trigger phrase, not
after) for one of the seven known instrument-citation forms
(:func:`find_citations`, which also resolves an ELIDED continuation in a
list — "Regulation (EU) 2016/679 or (EU) 2018/1725" names the second
citation's kind by inheriting the nearest preceding FULL citation's own
kind, left to right; see that function's own docstring).

A citation is excluded from the target list when it resolves to the
CITING instrument ITSELF, and a bare "this Regulation"/"this Directive"
phrase is ALSO treated as a self-reference (:data:`_SELF_REFERENCE_RE`) —
neither is a cross-instrument relation. This matters in two distinct
ways: a clause may cite ONLY itself (e.g. the AI Act's own Art. 102-109,
each citing "Regulation (EU) 2024/1689" — itself), or may cite OTHER
instruments ALONGSIDE a self-reference (e.g. "... without prejudice to
Article 10(5) and Article 59 of this Regulation", where "this Regulation"
is the ONLY thing named). **When the ONLY thing a clause names is itself,
no record is emitted at all** — a self-reference is not a relation
between two instruments, so there is nothing to type, and `find_relations`
does not fabricate one (see :func:`_resolve_targets`'s own three-way
return). A clause that names neither a citation nor a self-reference at
all (the cue fired on the trigger phrase alone, with nothing after it
identifying ANY instrument) still produces a record, but with
`target_instrument: None`, `unresolved: True`, and a reduced confidence
(×0.6) — a cue may opt out of this fallback entirely via its own
`suppress_if_unresolved` flag (see `find_relations`), for a trigger
phrase broad enough that an unresolved hit is pure noise rather than a
useful, reviewable signal.

`target_mode == "repealed_alias"` (used only by GDPR Art. 94(2)'s own
"the repealed Directive" phrasing, which names no instrument by number at
all) resolves the target through the ruleset's own
`repealed_instrument_by_source` table, keyed by the CITING instrument's
own id — this is the one mode that is NOT a generic citation search,
because the clause's own alias is instrument-specific knowledge the
ruleset document carries explicitly, never a guess; when the table has no
entry for the citing instrument, no record is emitted.

**Unknown instruments are kept, not dropped — `external:<kind>-<year>-<number>[-ec]`.**
:func:`find_citations` resolves exactly the seven named citation forms
(Regulation (EU) 2016/679, Directive 2002/58/EC, Directive 2000/31/EC,
Regulation (EU) 2022/2065, Directive (EU) 2022/2555, Regulation (EU)
2024/1689, Directive 95/46/EC) to this grammar's own closed instrument-id
vocabulary (`gdpr`, `eprivacy`, `ecommerce`, `dsa`, `nis2`, `ai-act`,
`dpd95`); any OTHER "Regulation (EU) .../..." / "Directive (EU) .../..." /
"Directive .../.../EC" citation — including an ELIDED one carrying no
kind word of its own (e.g. "... or (EU) 2018/1725") — is kept as
`external:<kind>-<year>-<number>[-ec]` (e.g.
`external:regulation-eu-2018-1725`) rather than silently discarded or
raising.

**Authority-sourced relations — API and validation only, never
populated.** :func:`authority_relation_violations` validates the SHAPE of
a relation record a court ruling or regulator's guidance TYPES (never
derives from statute text); :func:`authority_relation_to_triple` converts
a validated one into a 5D triple exactly like a statute-derived record
(:func:`relation_to_triple`, refusing an unresolved record exactly as
that function does). Both carry `basis: "authority"` so a consumer can
always tell the two provenances apart. **No data is seeded into this
path by this module** — it ships as an API/validation surface only; a
conforming consumer supplies its own authority-sourced records, one at a
time, each validated before it is trusted.

Stdlib only.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from ..grounding import digest as _grounding_digest

__all__ = [
    "RELATIONS",
    "KNOWN_INSTRUMENTS",
    "find_citations",
    "resolve_instrument_citation",
    "load_ruleset",
    "ruleset_violations",
    "cue_table_digest",
    "ruleset_digest",
    "find_relations",
    "relation_to_triple",
    "relations_to_triples",
    "authority_relation_violations",
    "authority_relation_to_triple",
    "build_nd_system",
    "build_descriptor",
]

_RULES_PATH = Path(__file__).with_name("interplay_rules.json")

# ── §1 of this module's own contract: the closed relation vocabulary ────────
#: The CLOSED set of relation ids this grammar ever emits — a new relation is
#: a spec-level decision (editing this dict AND the spec section it mirrors),
#: never something `find_relations` infers from an unrecognised cue. Each
#: entry's `dimension` is the ONE 5D dimension (§2) the relation projects
#: onto; `reason` restates, in one line, the module docstring's own
#: justification for that choice.
RELATIONS: "dict[str, dict]" = {
    "same_definition": {
        "meaning": "B's term is defined by A's",
        "dimension": "structural",
        "reason": "a definitional cross-reference is structural (is-a/part-of-like), not causal or temporal",
    },
    "cumulative": {
        "meaning": "both apply",
        "dimension": "relational",
        "reason": "plain co-application to the same conduct, with no causal or structural content of its own",
    },
    "complementary": {
        "meaning": "B adds to A within the same matter",
        "dimension": "relational",
        "reason": "a co-application relation (B supplements A's own matter), not a cause/effect or containment",
    },
    "alternative": {
        "meaning": "one or the other applies, by scope",
        "dimension": "causal",
        "reason": "which instrument governs is determined by a scope/triggering condition — a conditional gate",
    },
    "substitutive": {
        "meaning": "compliance with A discharges B",
        "dimension": "causal",
        "reason": "compliance with A is stated to CAUSE (discharge) B's own obligation",
    },
    "separate_tracks": {
        "meaning": "independent regimes on one act",
        "dimension": "relational",
        "reason": "two regimes relate to the same act without one causing or structurally containing the other",
    },
    "non_cumulative": {
        "meaning": "an express bar on double application, e.g. fines",
        "dimension": "causal",
        "reason": "an express bar PREVENTS a second legal consequence from arising at all",
    },
    "no_presumption": {
        "meaning": "compliance with A gives no presumption under B",
        "dimension": "causal",
        "reason": "compliance with A is stated NOT to CAUSE a presumption of compliance under B",
    },
    "defers_to": {
        "meaning": "A states it is without prejudice to / does not affect B",
        "dimension": "structural",
        "reason": "restates which instrument's provisions control — a structural subordination, matching spec §21's own cross_references/savings-clause binding",
    },
    "reference_redirect": {
        "meaning": "references to X are read as references to Y",
        "dimension": "structural",
        "reason": "rewires a textual reference from one instrument's identity to another's, matching spec §21's own cross_references binding",
    },
}

# ── instrument-citation resolver ─────────────────────────────────────────────
#: The CLOSED table of the seven named citation forms, each keyed by the
#: exact (kind, eu_flag, year, number, ec_flag) tuple :func:`find_citations`
#: extracts. Resolving through ONE shared numeric regex (rather than seven
#: separate literal-string patterns) means a citation typeset with
#: different internal whitespace, or any OTHER "Regulation (EU) .../..."
#: citation not in this table, is still FOUND — just resolved to
#: `external:...` (:func:`resolve_instrument_citation`) instead of
#: silently missed.
KNOWN_INSTRUMENTS: "dict[tuple, str]" = {
    ("regulation", True, "2016", "679", False): "gdpr",
    ("directive", False, "2002", "58", True): "eprivacy",
    ("directive", False, "2000", "31", True): "ecommerce",
    ("regulation", True, "2022", "2065", False): "dsa",
    ("directive", True, "2022", "2555", False): "nis2",
    ("regulation", True, "2024", "1689", False): "ai-act",
    ("directive", False, "95", "46", True): "dpd95",
}

#: Matches "Regulation (EU) 2016/679", "Directive 2002/58/EC",
#: "Directive (EU) 2022/2555", "Directive 95/46/EC" (the FULL form, kind
#: word + optional "(EU)" + year/number + optional "/EC" — named group
#: `kind` always present); "Regulation (EU) No 1025/2012" (the "No" form —
#: the OLDER EU citation style, NUMBER then YEAR, the reverse order of the
#: full form above — named group `kindno` always present); and an ELIDED
#: continuation inside a list of citations that share one kind word —
#: "Regulation (EU) 2016/679 or (EU) 2018/1725" names the second
#: instrument with no kind word of its own at all (the third alternative
#: below, named group `kind`/`kindno` always absent;
#: :func:`find_citations` resolves its kind from the nearest preceding
#: FULL or "No"-form citation, left to right). The kind word itself may be
#: PLURAL ("Regulations (EU) 2016/679 and (EU) 2018/1725", "Directives
#: (EU) 2016/2102 and (EU) 2019/882" — both real corpus forms) —
#: :func:`find_citations` normalises a trailing "s" away before using the
#: kind, so "regulations"/"regulation" and "directives"/"directive" key
#: identically. Deliberately does NOT match a bare "Regulation
#: 679/2016"-style reversed form (without "No"), a citation with no "/",
#: or an elided continuation with no "(EU)" marker at all (e.g. "Directive
#: 2002/58/EC or 2016/680" — a bare "2016/680" with neither a kind word
#: nor an "(EU)" marker is indistinguishable from an ordinary number and
#: is OUT OF SCOPE, a documented limit): an instrument named only by a
#: short title ("the GDPR", "the DSA") is likewise out of scope.
_CITATION_RE = re.compile(
    r"\b(?P<kind>Regulations?|Directives?)\s+(?:\((?P<eu>EU)\)\s+)?"
    r"(?P<year>\d{2,4})/(?P<number>\d{1,4})(?P<ec>/EC)?\b"
    r"|"
    r"\b(?P<kindno>Regulations?|Directives?)\s+(?:\((?P<euno>EU)\)\s+)?"
    r"No\.?\s*(?P<numberno>\d{1,4})/(?P<yearno>\d{2,4})\b"
    r"|"
    r"\((?P<eu2>EU)\)\s*(?P<year2>\d{2,4})/(?P<number2>\d{1,4})(?P<ec2>/EC)?\b",
    re.IGNORECASE,
)


def _normalise_kind(raw: str) -> str:
    """"regulation"/"regulations" -> "regulation";
    "directive"/"directives" -> "directive" — the plural kind word used in
    e.g. "Regulations (EU) 2016/679 and (EU) 2018/1725" names the SAME
    kind as the singular form, never a different citation shape."""
    lowered = raw.lower()
    return lowered[:-1] if lowered.endswith("s") else lowered


def resolve_instrument_citation(key: tuple) -> str:
    """The instrument id (or `external:...`) for ONE
    `(kind, eu_flag, year, number, ec_flag)` key. Looks the exact tuple up
    in :data:`KNOWN_INSTRUMENTS` first; falls through to a deterministic
    `external:<kind>-[eu-]<year>-<number>[-ec]` id — never raises, never
    drops a citation it is given. `year`/`number` are always given in
    THIS order regardless of which surface order ("Regulation (EU)
    2016/679" vs "Regulation (EU) No 1025/2012") the citation used —
    :func:`find_citations` normalises the "No" form's reversed
    number/year before building this key, so the external id is always
    `<kind>-<year>-<number>`, never ambiguous about which digit string is
    which."""
    known = KNOWN_INSTRUMENTS.get(key)
    if known is not None:
        return known
    kind, eu, year, number, ec = key
    parts = [kind]
    if eu:
        parts.append("eu")
    parts.append(year)
    parts.append(number)
    if ec:
        parts.append("ec")
    return "external:" + "-".join(parts)


def find_citations(text: str) -> "list[tuple[int, int, str, str]]":
    """Every instrument citation in `text`, as
    `(start, end, instrument_id, matched_text)`, in the order it appears.
    `text` is scanned exactly once with :data:`_CITATION_RE`, which
    matches a FULL citation (its own `kind` group), a "No"-form citation
    (its own `kindno` group, NUMBER then YEAR — reversed from the full
    form), or an ELIDED continuation (neither group — e.g. the second item
    of "Regulation (EU) 2016/679 or (EU) 2018/1725"). The scan carries the
    MOST RECENTLY SEEN full-or-"No"-form citation's own (normalised, see
    :func:`_normalise_kind`) kind, left to right, and uses it to resolve
    every elided continuation that follows, until the next full/"No"-form
    citation updates it; an elided continuation that appears before ANY
    such citation has been seen resolves with `kind: "unknown"` (kept,
    never dropped, as `external:unknown-eu-<year>-<number>[-ec]`) — a
    documented limit, since nothing in the text yet states what kind of
    instrument it is. A citation resolves to a known instrument id
    (:data:`KNOWN_INSTRUMENTS`) or to a deterministic `external:...` id
    (:func:`resolve_instrument_citation`) — never silently dropped."""
    if not isinstance(text, str):
        raise ValueError("find_citations() requires a string")
    out = []
    carried_kind = None
    for m in _CITATION_RE.finditer(text):
        if m.group("kind") is not None:
            kind = _normalise_kind(m.group("kind"))
            carried_kind = kind
            key = (kind, bool(m.group("eu")), m.group("year"), m.group("number"), bool(m.group("ec")))
        elif m.group("kindno") is not None:
            kind = _normalise_kind(m.group("kindno"))
            carried_kind = kind
            key = (kind, bool(m.group("euno")), m.group("yearno"), m.group("numberno"), False)
        else:
            kind = carried_kind if carried_kind is not None else "unknown"
            key = (kind, True, m.group("year2"), m.group("number2"), bool(m.group("ec2")))
        out.append((m.start(), m.end(), resolve_instrument_citation(key), m.group(0)))
    return out


#: Best-effort article-number lookback immediately before a citation (e.g.
#: "Article 83 of Regulation (EU) 2016/679" -> "83"; "Article 4, point
#: (12), of Regulation (EU) 2016/679" -> "4, point (12)"). Bounded to a
#: short trailing window so it never scans the whole clause; returns
#: `None`, never guesses, when no such "Article(s) ... of" phrase ends
#: exactly at the citation's own start. A DOCUMENTED, ACCEPTED limit (see
#: module docstring and LIMITS below): a multi-article list ("Articles 12
#: to 15") captures only the FIRST number token, never the full span, and
#: only a SINGLE trailing ", point (x)" is recognised (never a list of
#: points, e.g. "points (a) and (b)").
_ARTICLE_LOOKBACK_WINDOW = 80
_ARTICLE_BEFORE_CITATION_RE = re.compile(
    r"Articles?\s+(?P<article>\d+(?:\(\d+\))?)"
    r"(?:\s*,\s*points?\s+\((?P<point>[^)]+)\)\s*,)?"
    r"(?:\s+(?:to|and)\s+\d+(?:\(\d+\))?)*"
    r"\s+of\s*$",
    re.IGNORECASE,
)


def _target_article_before(clause_text: str, citation_start: int) -> "str | None":
    window_start = max(0, citation_start - _ARTICLE_LOOKBACK_WINDOW)
    m = _ARTICLE_BEFORE_CITATION_RE.search(clause_text[window_start:citation_start])
    if not m:
        return None
    article = m.group("article")
    point = m.group("point")
    return f"{article}, point ({point})" if point else article


#: A bare "this Regulation"/"this Directive" (and the plural-sounding "the
#: repealed Directive" is handled separately, via `target_mode ==
#: "repealed_alias"` — never by this pattern) is a SELF-reference: the
#: clause is talking about the instrument it is itself part of, not a
#: different one. No digits accompany it, so :data:`_CITATION_RE` never
#: matches it; this pattern is what lets :func:`_resolve_targets` recognise
#: the self-reference anyway, so a clause that names ONLY itself — e.g.
#: "without prejudice to Article 10(5) and Article 59 of this Regulation" —
#: resolves to "nothing else is named here", not to "nothing was found at
#: all" (the two are kept distinct; see that function's own docstring).
_SELF_REFERENCE_RE = re.compile(r"\bthis\s+(?:Regulation|Directive)\b", re.IGNORECASE)


# ── ruleset loading / validation / digest ───────────────────────────────────

def load_ruleset(source: "str | Path | dict | None" = None) -> dict:
    """Load an interplay ruleset DOCUMENT — the cue-table DATA
    :func:`find_relations` checks against. `source` is a ruleset dict
    already in memory, a path to a JSON file, or `None` (loads the packaged
    default, `interplay_rules.json`). Never parses or infers cues from
    code; the ruleset is always data, read verbatim."""
    if source is None:
        source = _RULES_PATH
    if isinstance(source, dict):
        return source
    return json.loads(Path(source).read_text(encoding="utf-8"))


_TARGET_MODES = frozenset({"cited", "repealed_alias", "none"})


def ruleset_violations(doc: Any) -> list:
    """Shape violations of an interplay ruleset document: a mapping with a
    non-empty string `ruleset_id`, a mapping `repealed_instrument_by_source`
    (string keys/values), and a non-empty list `cues`, each cue a mapping
    with non-empty string `cue_id`/`trigger_pattern`, a `relation` that MUST
    be a known key of :data:`RELATIONS`, a `target_mode` that MUST be one of
    :data:`_TARGET_MODES`, a list (possibly empty) of string
    `require_all_patterns`, a positive integer `max_span_chars`, a
    non-empty string `clause_end_chars` when present (default `".;"`), a
    non-negative integer `target_lookback_chars` when present (default
    `0`), a boolean `suppress_if_unresolved` when present (default
    `False` — see :func:`find_relations`), and a `confidence` number in
    `[0, 1]`. Every `trigger_pattern` and `require_all_patterns` entry MUST
    compile as a regex. Returns `[]` when the document validates."""
    if not isinstance(doc, dict):
        return ["interplay ruleset must be a mapping"]
    out = []
    ruleset_id = doc.get("ruleset_id")
    if not isinstance(ruleset_id, str) or not ruleset_id:
        out.append("interplay ruleset field 'ruleset_id' must be a non-empty string")
    aliases = doc.get("repealed_instrument_by_source", {})
    if not isinstance(aliases, dict) or not all(
            isinstance(k, str) and isinstance(v, str) and k and v for k, v in aliases.items()):
        out.append("interplay ruleset field 'repealed_instrument_by_source' must be a "
                    "mapping of non-empty strings to non-empty strings")
    cues = doc.get("cues")
    if not isinstance(cues, list) or not cues:
        out.append("interplay ruleset field 'cues' must be a non-empty list")
        cues = []
    for i, cue in enumerate(cues):
        if not isinstance(cue, dict):
            out.append(f"cues[{i}] must be a mapping")
            continue
        for field in ("cue_id", "trigger_pattern"):
            value = cue.get(field)
            if not isinstance(value, str) or not value:
                out.append(f"cues[{i}].{field} must be a non-empty string")
            elif field == "trigger_pattern":
                try:
                    re.compile(value)
                except re.error as exc:
                    out.append(f"cues[{i}].trigger_pattern does not compile: {exc}")
        relation = cue.get("relation")
        if relation not in RELATIONS:
            out.append(f"cues[{i}].relation {relation!r} is not a known RELATIONS key {sorted(RELATIONS)!r}")
        target_mode = cue.get("target_mode")
        if target_mode not in _TARGET_MODES:
            out.append(f"cues[{i}].target_mode {target_mode!r} must be one of {sorted(_TARGET_MODES)!r}")
        patterns = cue.get("require_all_patterns", [])
        if not isinstance(patterns, list) or not all(isinstance(p, str) and p for p in patterns):
            out.append(f"cues[{i}].require_all_patterns must be a list of non-empty strings")
        else:
            for p in patterns:
                try:
                    re.compile(p)
                except re.error as exc:
                    out.append(f"cues[{i}].require_all_patterns entry does not compile: {exc}")
        clause_end_chars = cue.get("clause_end_chars", ".;")
        if not isinstance(clause_end_chars, str) or not clause_end_chars:
            out.append(f"cues[{i}].clause_end_chars must be a non-empty string when present")
        max_span = cue.get("max_span_chars")
        if not isinstance(max_span, int) or isinstance(max_span, bool) or max_span <= 0:
            out.append(f"cues[{i}].max_span_chars must be a positive integer")
        lookback = cue.get("target_lookback_chars", 0)
        if not isinstance(lookback, int) or isinstance(lookback, bool) or lookback < 0:
            out.append(f"cues[{i}].target_lookback_chars must be a non-negative integer when present")
        suppress_if_unresolved = cue.get("suppress_if_unresolved", False)
        if not isinstance(suppress_if_unresolved, bool):
            out.append(f"cues[{i}].suppress_if_unresolved must be a boolean when present")
        confidence = cue.get("confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not (0.0 <= float(confidence) <= 1.0):
            out.append(f"cues[{i}].confidence must be a number in [0, 1]")
    return out


def cue_table_digest() -> str:
    """Sha256 digest over the CODE-side fixtures that affect every
    `find_relations` call regardless of the ruleset — the citation table
    (:data:`KNOWN_INSTRUMENTS`), the citation regex source, and the article
    -lookback regex source — folded into :func:`ruleset_digest` so a code
    edit to any of these is pinned exactly like a ruleset edit."""
    doc = {
        "known_instruments": sorted(
            [list(k) + [v] for k, v in KNOWN_INSTRUMENTS.items()]
        ),
        "citation_pattern": _CITATION_RE.pattern,
        "article_lookback_pattern": _ARTICLE_BEFORE_CITATION_RE.pattern,
        "relations": {rid: {"dimension": r["dimension"]} for rid, r in sorted(RELATIONS.items())},
    }
    return _grounding_digest(doc)["sha256"]


def ruleset_digest(doc: dict) -> str:
    """Sha256 digest (`five_d_nd.grounding.digest`) over the ruleset
    document AND the code-side cue table (:func:`cue_table_digest`) — pins
    exactly which cues AND which citation/relation fixtures a given
    `find_relations` call ran against."""
    return _grounding_digest({"ruleset": doc, "cue_table_digest": cue_table_digest()})["sha256"]


# ── the deterministic clause reader ──────────────────────────────────────────

#: A clause ends at the first character in the cue's own `clause_end_chars`
#: (default `".;"`) found inside the cue's own `max_span_chars` window —
#: never at a `,` (a scope clause routinely lists several commas before
#: its own terminating punctuation; stopping at a comma would truncate
#: the very "same objective"/"same conduct" phrase `require_all_patterns`
#: checks for). Falls back to the full window when none is found inside
#: it (an ACCEPTED, documented limit: a clause longer than
#: `max_span_chars` with no ending character before that point has its
#: own verbatim span cut off, never silently extended past the configured
#: bound).
#:
#: **Why `clause_end_chars` is PER CUE, not a single global rule.** A
#: "without prejudice to ... the following: (a) ...; (b) ...; ... (g)
#: Regulation (EU) 2016/679 ...; (h) ..." clause (DSA Art. 2(4)(g)'s own
#: real corpus text) is a single legal sentence that uses `;` to separate
#: its own lettered list items — treating `;` as a clause boundary there
#: would truncate the clause at item (a), well before the named
#: instrument in item (g) is ever reached. The default stays `".;"` for
#: every other cue (a clause whose own `;` really is a boundary, e.g.
#: NIS2 Art. 35(1)'s own multi-clause sentence); `without-prejudice-to`
#: and `shall-not-affect` set `clause_end_chars: "."` in the ruleset
#: because their own clauses are the ones that name an instrument inside
#: an enumerated, `;`-separated list.
_DEFAULT_CLAUSE_END_CHARS = ".;"


def _clause_span(text: str, start: int, max_span_chars: int, clause_end_chars: str = _DEFAULT_CLAUSE_END_CHARS) -> "tuple[int, int]":
    window_end = min(len(text), start + max_span_chars)
    end_re = re.compile("[" + re.escape(clause_end_chars) + "]")
    m = end_re.search(text, start, window_end)
    end = m.end() if m else window_end
    return start, end


def _resolve_targets(
    cue: dict,
    clause_text: str,
    source_instrument: str,
    ruleset: dict,
    citation_search_text: "str | None" = None,
) -> "list[tuple] | None":
    """Resolves ONE matched clause's target(s), per `cue["target_mode"]`
    (see the module docstring's own "Target resolution" section). Returns
    one of THREE distinct shapes, never conflated:

    * a NON-EMPTY list of `(target_instrument, target_article | None)`
      pairs — one or more OTHER instruments were found;
    * `None` — the clause names ONLY the citing instrument itself (a
      numeric self-citation, a bare "this Regulation"/"this Directive"
      phrase, or both), or a `repealed_alias` cue whose ruleset carries no
      alias for this source — in either case there is nothing to type a
      relation TO, so `find_relations` emits no record at all;
    * an EMPTY list `[]` — the clause names NEITHER a citation NOR a
      self-reference at all; `find_relations` decides, per the cue's own
      `suppress_if_unresolved` flag, whether to emit a reduced-confidence,
      `unresolved: True` record or nothing.

    `citation_search_text` — when given — is searched INSTEAD OF
    `clause_text` for the `cited` mode only (:func:`find_relations`'s own
    `target_lookback_chars` widening; see that function and the module
    docstring's own "A clause ends at..." note); `clause_text` itself is
    unaffected, and remains the text recorded as `verbatim_span`.
    """
    mode = cue["target_mode"]
    if mode == "repealed_alias":
        target = ruleset.get("repealed_instrument_by_source", {}).get(source_instrument)
        return [(target, None)] if target is not None else None
    if mode == "none":
        return []
    if mode == "cited":
        search_text = citation_search_text if citation_search_text is not None else clause_text
        all_cites = find_citations(search_text)
        other_cites = [c for c in all_cites if c[2] != source_instrument]
        if other_cites:
            out = []
            seen = set()
            for (cstart, _cend, instrument_id, _txt) in other_cites:
                if instrument_id in seen:
                    continue
                seen.add(instrument_id)
                out.append((instrument_id, _target_article_before(search_text, cstart)))
            return out
        self_numeric_cited = any(c[2] == source_instrument for c in all_cites)
        self_referenced_by_phrase = bool(_SELF_REFERENCE_RE.search(search_text))
        if self_numeric_cited or self_referenced_by_phrase:
            return None
        return []
    raise ValueError(f"unknown target_mode {mode!r}")


def find_relations(
    articles: "Iterable[dict]",
    ruleset: "dict | None" = None,
) -> "list[dict]":
    """Deterministically find interplay relation records across a
    collection of ARTICLE-SEGMENTED instrument text.

    `articles` is an iterable of mappings, each with non-empty string keys
    `instrument_id` (e.g. `"gdpr"`), `article_id` (e.g. `"Art. 95"`), and
    `text` (the article's own text — paragraph breaks and all; no sentence
    pre-segmentation is required of the caller). `ruleset` defaults to the
    packaged default (:func:`load_ruleset`) when omitted, and is VALIDATED
    FIRST (:func:`ruleset_violations`), raising `ValueError` before any
    article is scanned.

    A clause whose ONLY named instrument is the citing one (a numeric
    self-citation, or a bare "this Regulation"/"this Directive" phrase) —
    or a `repealed_alias` cue with no ruleset entry for the citing
    instrument — produces NO RECORD AT ALL (see :func:`_resolve_targets`):
    a self-reference is not a relation between two instruments, so there
    is nothing to type. A clause that names NEITHER another instrument
    NOR itself produces a record with `target_instrument: None` and
    `unresolved: True`, UNLESS the cue's own `suppress_if_unresolved` flag
    is set, in which case it too produces no record (reserved for a
    trigger phrase broad enough — e.g. a bare "in accordance with" with
    nothing further — that an unresolved hit is noise, not signal).

    Returns a list of relation records, each a mapping with:
    `source_instrument`, `source_article`, `relation`, `target_instrument`
    (`None` only when `unresolved` is `True`), `target_article` (`None`
    when not found or not applicable), `cue_id`, `verbatim_span` (the
    EXACT source text of the matched clause, stripped of leading/trailing
    whitespace only — never paraphrased), `match_start` (the character
    offset, within THIS article's own `text`, where the matched clause
    begins — a STABLE span offset that tells two records with otherwise
    byte-identical fields apart, e.g. two distinct list items in the same
    article that happen to cite the same provision in the same words; see
    AI Act Art. 3's own two near-identical "as defined in Article 4,
    point (1), of Regulation (EU) 2016/679;" occurrences), `unresolved`
    (`True` iff no other instrument was named and the cue did not
    suppress the record; `False` otherwise), `confidence` (the cue's own
    confidence, multiplied by 0.6 when `unresolved` is `True`), `basis`
    (always `"statute"` for this function — see
    :func:`authority_relation_to_triple` for the other provenance), and
    `ruleset_digest`.

    Deterministic: the SAME `articles`/`ruleset` input always produces the
    SAME output, byte-for-byte once serialised — every match comes from a
    single left-to-right scan per cue per article, cues are applied in the
    ruleset's own list order, and the final list is sorted by
    `(source_instrument, source_article, cue_id, match_start,
    target_instrument or "", target_article or "")` — `match_start` is
    itself what makes this sort key TOTAL (never relying on Python's
    merely-stable sort to break a tie between two otherwise-identical
    records) — so dict/set iteration order elsewhere in this module can
    never leak into the output order.

    Raises `ValueError` on a malformed ruleset, or if any article mapping
    is missing `instrument_id`/`article_id`/`text`, or if any of those
    three is not a non-empty string (`text` MAY be an empty string — an
    article with no text simply yields no records from it).
    """
    if ruleset is None:
        ruleset = load_ruleset()
    violations = ruleset_violations(ruleset)
    if violations:
        raise ValueError(f"malformed interplay ruleset: {violations!r}")

    materialised = list(articles)
    for i, article in enumerate(materialised):
        if not isinstance(article, dict):
            raise ValueError(f"articles[{i}] must be a mapping")
        for field in ("instrument_id", "article_id"):
            value = article.get(field)
            if not isinstance(value, str) or not value:
                raise ValueError(f"articles[{i}].{field} must be a non-empty string")
        if not isinstance(article.get("text"), str):
            raise ValueError(f"articles[{i}].text must be a string")

    compiled_cues = [
        (cue, re.compile(cue["trigger_pattern"], re.IGNORECASE | re.DOTALL),
         [re.compile(p, re.IGNORECASE | re.DOTALL) for p in cue.get("require_all_patterns", [])])
        for cue in ruleset["cues"]
    ]
    rs_digest = ruleset_digest(ruleset)

    records = []
    seen_keys = set()
    for article in materialised:
        source_instrument = article["instrument_id"]
        source_article = article["article_id"]
        text = article["text"]
        for cue, trigger_re, require_res in compiled_cues:
            for m in trigger_re.finditer(text):
                start, end = _clause_span(
                    text, m.start(), cue["max_span_chars"],
                    cue.get("clause_end_chars", _DEFAULT_CLAUSE_END_CHARS))
                clause_text = text[start:end]
                if not all(req.search(clause_text) for req in require_res):
                    continue
                lookback = cue.get("target_lookback_chars", 0)
                citation_search_text = (
                    text[max(0, start - lookback):end] if lookback else clause_text
                )
                targets = _resolve_targets(
                    cue, clause_text, source_instrument, ruleset,
                    citation_search_text=citation_search_text)
                if targets is None:
                    continue  # the clause names only the citing instrument itself
                if not targets:
                    if cue.get("suppress_if_unresolved", False):
                        continue  # a broad trigger with nothing named at all: noise, not signal
                    targets = [(None, None)]
                for target_instrument, target_article in targets:
                    unresolved = target_instrument is None
                    confidence = float(cue["confidence"])
                    if unresolved:
                        confidence = round(confidence * 0.6, 6)
                    verbatim = clause_text.strip()
                    key = (source_instrument, source_article, cue["cue_id"],
                           start, target_instrument, target_article)
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    records.append({
                        "source_instrument": source_instrument,
                        "source_article": source_article,
                        "relation": cue["relation"],
                        "target_instrument": target_instrument,
                        "target_article": target_article,
                        "cue_id": cue["cue_id"],
                        "verbatim_span": verbatim,
                        "match_start": start,
                        "unresolved": unresolved,
                        "confidence": confidence,
                        "basis": "statute",
                        "ruleset_digest": rs_digest,
                    })
    records.sort(key=lambda r: (
        r["source_instrument"], r["source_article"], r["cue_id"], r["match_start"],
        r["target_instrument"] or "", r["target_article"] or "",
    ))
    return records


# ── 5D triples ────────────────────────────────────────────────────────────────

def relation_to_triple(record: dict, grammar_id: str = "interplay-grammar") -> dict:
    """The §11-shaped 5D triple for ONE relation record (statute- or
    authority-sourced — both shapes carry the same fields). **Refuses an
    UNRESOLVED record outright, raising `ValueError`** — a triple's `o`
    (§11) names a real entity; there is no instrument called "unknown" to
    name, so an unresolved record (`record.get("unresolved")` true, or
    `target_instrument` missing/`None`) is never converted at all. A
    caller that wants an unresolved finding surfaced for human review
    reads the relation record directly (`find_relations`'s own
    `unresolved: True` field); it is not this function's job to invent an
    edge for it. Once resolved: `s` is
    `"<source_instrument>:<source_article>"`; `o` is
    `"<target_instrument>[:<target_article>]"`. `dimension` is looked up
    from :data:`RELATIONS` by `record["relation"]`; `weight` is
    `record["confidence"]`, clamped into `[0, 1]`. `provenance` carries
    `basis`, `cue_id` (when present — an authority record may have none),
    and `verbatim_span`."""
    relation = record["relation"]
    if relation not in RELATIONS:
        raise ValueError(f"unknown relation {relation!r}; not one of {sorted(RELATIONS)!r}")
    target_instrument = record.get("target_instrument")
    if record.get("unresolved") or target_instrument is None:
        raise ValueError(
            "cannot convert an unresolved relation record to a triple — "
            "no instrument was named as the target; see the record's own "
            "'unresolved' field")
    s = f"{record['source_instrument']}:{record['source_article']}"
    if record.get("target_article"):
        o = f"{target_instrument}:{record['target_article']}"
    else:
        o = target_instrument
    weight = max(0.0, min(1.0, float(record.get("confidence", 1.0))))
    provenance = {
        "basis": record.get("basis", "statute"),
        "verbatim_span": record.get("verbatim_span"),
    }
    if record.get("cue_id") is not None:
        provenance["cue_id"] = record["cue_id"]
    if record.get("authority") is not None:
        provenance["authority"] = record["authority"]
    return {
        "s": s,
        "p": relation,
        "o": o,
        "dimension": RELATIONS[relation]["dimension"],
        "weight": round(weight, 6),
        "provenance": provenance,
        "grammar_id": grammar_id,
    }


def relations_to_triples(records: "Iterable[dict]", grammar_id: str = "interplay-grammar") -> "list[dict]":
    """`[relation_to_triple(r, grammar_id) for r in records]`, in the
    SAME order as `records` (this function performs no sorting or
    deduplication of its own — `find_relations` already produces a
    deterministically ordered, deduplicated list; an authority-sourced
    caller controls its own record order)."""
    return [relation_to_triple(r, grammar_id) for r in records]


# ── authority-sourced relations: API and validation only, never populated ───

def authority_relation_violations(doc: Any) -> list:
    """Shape violations of an AUTHORITY-SOURCED relation record (a court
    ruling or a regulator's guidance that types a relation not stated in
    the statute itself). A mapping with: non-empty string
    `source_instrument`/`target_instrument`; a `relation` that MUST be a
    known key of :data:`RELATIONS`; optional string
    `source_article`/`target_article`/`verbatim_span`; a `basis` that MUST
    be the literal string `"authority"` (never `"statute"` — this is
    exactly the field :func:`relation_to_triple`'s provenance uses to keep
    the two kinds distinct downstream); an `authority` mapping with
    non-empty string `name` and `locator` (a citation, docket number, or
    URL identifying the ruling/guidance); and, when present, a `confidence`
    number in `[0, 1]`. Returns `[]` when the document validates.

    **This function validates; it does not create.** No caller in this
    package ever constructs a document that passes this check with real
    data — this ingestion path ships as an API/validation surface only,
    seeded with nothing.
    """
    if not isinstance(doc, dict):
        return ["authority relation record must be a mapping"]
    out = []
    for field in ("source_instrument", "target_instrument"):
        value = doc.get(field)
        if not isinstance(value, str) or not value:
            out.append(f"authority relation field {field!r} must be a non-empty string")
    relation = doc.get("relation")
    if relation not in RELATIONS:
        out.append(f"authority relation field 'relation' {relation!r} is not a known "
                    f"RELATIONS key {sorted(RELATIONS)!r}")
    for field in ("source_article", "target_article", "verbatim_span"):
        if field in doc and doc[field] is not None and not isinstance(doc[field], str):
            out.append(f"authority relation field {field!r} must be a string or null when present")
    basis = doc.get("basis")
    if basis != "authority":
        out.append(f"authority relation field 'basis' must be the literal string 'authority', got {basis!r}")
    authority = doc.get("authority")
    if not isinstance(authority, dict):
        out.append("authority relation field 'authority' must be a mapping")
    else:
        for field in ("name", "locator"):
            value = authority.get(field)
            if not isinstance(value, str) or not value:
                out.append(f"authority relation field 'authority.{field}' must be a non-empty string")
    if "confidence" in doc:
        confidence = doc["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not (0.0 <= float(confidence) <= 1.0):
            out.append("authority relation field 'confidence' must be a number in [0, 1] when present")
    return out


def authority_relation_to_triple(doc: dict, grammar_id: str = "interplay-grammar") -> dict:
    """The 5D triple for ONE authority-sourced relation record, after
    validating it (:func:`authority_relation_violations`) — raises
    `ValueError` on any violation BEFORE building a triple, exactly like
    `find_relations` validates its ruleset first. Delegates to
    :func:`relation_to_triple` once validated (both shapes carry the same
    fields; `basis: "authority"` is what the resulting triple's
    `provenance` carries to distinguish it from a statute-derived one)."""
    violations = authority_relation_violations(doc)
    if violations:
        raise ValueError(f"malformed authority relation record: {violations!r}")
    return relation_to_triple(doc, grammar_id)


# ── §9 nD contract attachment ─────────────────────────────────────────────────

def build_nd_system() -> dict:
    """The `NDSystem` document this grammar publishes to attach to 5D
    (§9). One axis, `relation`: a CLOSED-vocabulary axis over this
    grammar's own ten relation ids (:data:`RELATIONS`)."""
    return {
        "id": "interplay-grammar",
        "namespace": "org.loomground.nd.interplay",
        "version": "1.0.0",
        "version_5d": "1.0-draft",
        "axes": {
            "relation": {
                "value_type": "controlled_identifier",
                "cardinality": "one",
                "vocabulary_mode": "closed",
                "vocabulary": sorted(RELATIONS),
            }
        },
        "bindings": [
            {"form_slot": "relation", "allowed_axes": ["relation"], "required": True},
        ],
        "ontology_relations": [],
        "validation": {
            "unknown_values": "reject",
            "missing_coordinates": "reject",
            "provenance_required": True,
        },
    }


def build_descriptor() -> dict:
    """The JSON-interchange grammar descriptor (§9) for this grammar. Binds
    EACH of the ten relation ids to its own 5D dimension (see
    :data:`RELATIONS` and the module docstring's own justification table)
    — not a single `relation -> dimension` binding, because this grammar's
    ten relations do NOT all project onto the same dimension. `produce` is
    OMITTED here (the interchange form); a runtime host wires
    :func:`find_relations` + :func:`relations_to_triples` in as the
    callable pair separately."""
    nd_system = build_nd_system()
    binding = {relation_id: spec["dimension"] for relation_id, spec in RELATIONS.items()}
    return {
        "plane": "interplay-grammar",
        "language_version": nd_system["version"],
        "nd_system": nd_system,
        "binding": binding,
        "examples": [],
        "contract_version": "1.0-draft",
    }
