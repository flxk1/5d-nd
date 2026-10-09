# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""EXAMPLE nD grammar — "penalty", structured penalty clauses read from EU
digital-law text (§25).

**Why this grammar exists.** A fine cap routinely sits inside a long
Statement endpoint — "subject to administrative fines up to 10 000 000
EUR, or in the case of an undertaking, up to 2 % of the total worldwide
annual turnover of the preceding financial year, whichever is higher" —
and nothing in the typed-statements layer (§21-§23) or the `interplay`
grammar (§24) answers "what is the cap, and is it a ceiling or a floor?"
This grammar reads a penalty clause into a closed, versioned record: the
infringed provisions, the EXCLUDED provisions (a stated "other than"
carve-out, never an infringement), the penalty kind, the fixed amount,
the turnover percentage and its basis, how the two combine, whether the
stated figure is a ceiling or a floor, and a per-day flag for a periodic
penalty payment.

**Rules are DATA, not code** — exactly the discipline `interplay.py`
(§24) and `requirement.py` (§18) already establish: the cue table
(trigger phrase, penalty kind, span bounds, an addressee-phrase table,
and a confidence) lives in ``penalty_rules.json``, loaded by
:func:`load_ruleset` and PINNED BY A SHA-256 DIGEST (:func:`ruleset_digest`,
via ``five_d_nd.grounding.digest``, same machinery as `interplay.py`).
Two further small tables are ALSO data, shared across every cue rather
than duplicated per cue: ``bound_type_phrases`` (the phrase that marks a
stated figure as a ceiling, a floor-of-a-maximum, or a minimum) and
``combination_phrases`` (the phrase that marks how two stated figures
combine — "whichever is higher"/"whichever is lower"). :func:`find_penalties`
branches on nothing but the loaded ruleset document plus a small set of
STRUCTURAL regexes this module owns in code because they parse a NUMBER
or a closed grammatical shape (an infringement/exclusion anchor phrase),
never a legal phrase specific to one instrument.

**The penalty-kind vocabulary is CLOSED and EXTERNAL to 5D itself** — it
is this grammar's own nD axis (§9's `NDSystem.axes`), never a sixth 5D
dimension. The four kinds:

* ``administrative_fine`` — a fine imposed by a supervisory/market
  authority or the Commission (GDPR Art. 83, AI Act Art. 99/100/101, DSA
  Art. 52(3)/74, NIS2 Art. 34).
* ``periodic_penalty_payment`` — a per-day payment compelling compliance
  (DSA Art. 52(4)/76).
* ``penalty`` — the Member-State "effective, proportionate and
  dissuasive" rules a directive/regulation leaves to national law (GDPR
  Art. 84, NIS2 Art. 36, DSA Art. 52(1), AI Act Art. 99(1)); no amount or
  percentage is ever expected for this kind.
* ``criminal_sanction`` — a criminal, rather than administrative, penalty;
  no real-corpus occurrence fires this kind in the five instruments this
  grammar was built against, so this kind is exercised only by a
  synthetic conformance vector; see the module's own LIMITS note.

**The 5D projection — one dimension for the WHOLE grammar, not one per
kind.** Unlike `interplay.py` (whose ten relations project onto three
different dimensions), every one of this grammar's four penalty kinds
binds the SAME dimension, `causal`: the edge is (infringement of a cited
provision) -> (the penalty that attaches to it) — a clause stating a fine
or a periodic penalty always states it as a CONSEQUENCE triggered BY an
infringement ("infringements of the following provisions shall... be
subject to...", "where they infringe Article 21 or 23..., entities are
subject to...", "non-compliance with... shall be subject to..."), never a
structural containment, a plain relational co-application, a temporal
ordering, or an intentional stance. See :data:`EDGE_DIMENSION` and §25's
own restatement of this reasoning.

**Edge identity — one edge PER infringed provision, never a bundle.**
:func:`penalty_to_triples` (plural) emits ONE triple per infringed
provision a record names, after RANGE EXPANSION ("25 to 39" ->
`Art.25`..`Art.39`, each its own edge) — never a single triple bundling
several provisions into one `s`. `s` is `"<instrument>:Art.<N>[(<p>)]"`
(a Chapter reference is `"<instrument>:Chapter.<roman>"`) — the SAME
`<instrument>:Art.N` shape this package already uses elsewhere for a
provision id, carrying no paragraph detail (paragraph detail of the
INFRINGED provision was never captured in the first place — only the
PENALTY clause's own paragraph is tracked, in `o`). `o` is
`"<source_article>(<paragraph>):<penalty_kind>"` when the penalty
clause's own paragraph is known, else `"<source_article>:<penalty_kind>"`
— UNIQUE per penalty CLAUSE (not merely per article), so GDPR Art.
83(4)/(5)/(6) and NIS2 Art. 34(4)/(5) and AI Act Art. 100(2)/(3) each get
their own distinct `o`, never colliding. No doubled instrument prefix:
`source_article` already carries the instrument (`"gdpr:Art.83"`), so
`s`/`o` are built from it directly, never re-prefixed.

**Negation and exclusion — two SEPARATE, never-conflated conditions.**
(1) `excluded_provisions` — text following "other than", "except(ing)",
"excluding", or "with the exception of" NAMES provisions the clause
explicitly carves OUT of its own scope (AI Act Art. 99(4)/100(3): "...
other than those laid down in Article[s] 5..."); these are masked out of
the working text BEFORE infringement scanning runs, so they can never
also appear in `infringed_provisions` — reading an excluded provision as
infringed would REVERSE the clause's own meaning. (2) `unresolved` — the
clause's own AMOUNT or BOUND could not be parsed (unrelated to
provisions at all). A record may be `unresolved` with no exclusion, have
an exclusion with no provisions left at all once masked (AI Act Art.
100(3): the infringed set is "requirements or obligations under this
Regulation" IN GENERAL, other than Art. 5 — no SPECIFIC provision survives
masking, so `infringed_provisions` is `[]` and `scope` instead records
"the instrument, other than Art. 5"; no edge is built, since there is no
specific provision to name), or carry both independently.

**Infringement-anchored extraction — never a bare "any Article mention
in the window".** A plain scan for "Article(s) <N>" anywhere nearby
reads a PROCEDURAL cross-reference (the decision that EMPOWERS a fine,
the clause naming WHO it targets) as if it were the infringed provision
itself — DSA Art. 74(1)'s own "In the decision referred to in Article
73, the Commission may impose..." names Art. 73 as the empowering
decision, not an infringed provision; DSA Art. 74(2)/76(1)'s own "...or
on another natural or legal person referred to in Article 67(1)..."
names Art. 67(1) only to identify WHO the clause addresses. Capture is
therefore gated on an INFRINGEMENT-ANCHOR phrase (:data:`_BROAD_ANCHOR_RE`,
:data:`_NARROW_ANCHOR_RE`) — "infringements? of ... provisions",
"non-compliance (?:of|with)", "infringe(s/d)", "fail(s/ed) to", "in
breach of" — never a connector word ("pursuant to"/"referred to in"/
"under") alone. A BROAD anchor ("infringements of the following
provisions", "non-compliance with ... the following provisions") scans
the WHOLE remainder of the clause (the bulleted list that follows is
that anchor's own enumeration — GDPR Art. 83(4)/(5), AI Act Art. 99(4));
a NARROW anchor ("fails to comply with", "infringe Article", "in breach
of", a bare "non-compliance (?:of|with)") scans only a bounded window
AFTER its own occurrence (GDPR Art. 83(6), AI Act Art. 100(2)/101(1), DSA
Art. 74(1)/(2), NIS2 Art. 34(4)/(5)). A clause with NO anchor at all —
DSA Art. 52(3)'s own two percentage-only sentences, DSA Art. 76(1)'s own
"compel them to: (a) supply...; (b) submit...; (c)/(d)/(e) comply
with..." list (every item describes a FUTURE compelled act, never a past
infringement) — never names an infringed provision at all, by design:
`infringed_provisions` stays `[]`, no edge is built, and the record is
still kept.

**A Chapter reference is captured alongside an Article one.** GDPR Art.
83(5)(d)'s own "any obligations pursuant to Member State law adopted
under Chapter IX" names a CHAPTER, not an Article — the same
anchor-gated walk (:func:`_walk_provisions_in_range`) recognises
"Chapter <roman-numeral>" exactly like "Article(s) <N>", storing it as
`"Chapter IX"` (never expanded into individual articles; it carries no
article number to expand).

**Number formats.** The EU corpus this grammar was built against uses
THREE amount-separator conventions for the SAME "EUR 10 000 000" shape of
number — plain space (GDPR, NIS2: "10 000 000 EUR"), and NO-BREAK space
(AI Act: "EUR 35 000 000") — plus a plain comma-decimal
percentage (NIS2: "1,4 %") alongside the far more common integer
percentage. :func:`_find_amount` and :func:`_find_percentage` both
normalise these before parsing. A THIRD form — an amount written in
words ("ten million euros") — is handled by :func:`_parse_word_amount`
(a small, closed ones/teens/tens/hundred/thousand/million lexicon), used
as a fallback ONLY when neither digit-amount regex matches; no clause in
the five-instrument corpus this grammar runs against ever spells an
amount out, so this path is exercised only by a synthetic conformance
vector.

**The clause span runs to the real sentence end, or raises — it never
silently truncates.** A clause's own `max_span_chars` is an UPPER SAFETY
BOUND, set generously per cue (every real clause in the five-instrument
corpus ends within a few hundred to ~1500 chars of its own trigger); if
no clause-ending character is found within that bound, :func:`_clause_span`
raises `ValueError` rather than cutting the span mid-sentence or
mid-word. A period is NOT treated as a clause end when immediately
followed by a comma (AI Act Art. 101(1)'s own stray "...whichever is
higher., when the Commission finds..." — a typeset error in the source
text itself, not a real sentence boundary) — :data:`_clause_span` skips
such a period and keeps searching for the NEXT one.

**Infringed provisions and the paragraph boundary.** A penalty clause's
own trigger phrase routinely sits in the MIDDLE of its own numbered
paragraph. :func:`_paragraph_marker_before` finds the nearest preceding
numbered-paragraph marker, and :func:`find_penalties` scans for
infringed/excluded provisions and for the addressee phrase over the SAME
window — from that marker through the clause's own end — so a citation
or an addressee phrase belonging to the PRECEDING numbered paragraph is
never pulled into the wrong record (GDPR Art. 83(5)'s own boundary
against Art. 83(4)'s trailing "Article 41(4)."). When no addressee
phrase is found in that window at all (AI Act Art. 100(2)/(3), whose
addressee is named only in Art. 100(1)), the SAME cue's own
`addressee_patterns` are tried a second time against the whole article
text up to the clause's own end.

**`unresolved` — amount/bound only, never the provisions lists.** A
cue's own `expects_amount` flag (`False` only for the `penalty` kind and
the SME whichever-is-lower modifier) decides whether `find_penalties`
requires EITHER a fixed amount OR a turnover percentage to have been
found, AND a bound type other than `unspecified`; failing either, the
record comes back `unresolved: True` with confidence multiplied by 0.6,
but the record is still emitted. `infringed_provisions`/
`excluded_provisions` are extracted UNIFORMLY for every cue (the
anchor-gating itself is what keeps a formula-only clause's own
incidental cross-references — GDPR Art. 84(1)'s own "pursuant to Article
83", AI Act Art. 99(1)'s own "pursuant to Article 96" — from ever being
read as infringed at all; no cue-level gate is needed).

**No data is seeded into the authority-sourced path** — `penalty.py`
ships :func:`authority_penalty_violations`/:func:`authority_penalty_to_triples`
as an API/validation surface only, mirroring `interplay.py`'s own
identical, deliberately-empty authority path.

Stdlib only.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from ..grounding import digest as _grounding_digest

__all__ = [
    "PENALTY_KINDS",
    "EDGE_DIMENSION",
    "load_ruleset",
    "ruleset_violations",
    "cue_table_digest",
    "ruleset_digest",
    "find_penalties",
    "penalty_to_triples",
    "penalties_to_triples",
    "authority_penalty_violations",
    "authority_penalty_to_triples",
    "build_nd_system",
    "build_descriptor",
]

_RULES_PATH = Path(__file__).with_name("penalty_rules.json")

# ── §1 of this module's own contract: the closed penalty-kind vocabulary ────
#: The CLOSED set of penalty-kind ids this grammar ever emits — a new kind
#: is a spec-level decision, never something `find_penalties` infers from an
#: unrecognised cue.
PENALTY_KINDS: "dict[str, str]" = {
    "administrative_fine": "a fine imposed by a supervisory/market authority or the Commission",
    "periodic_penalty_payment": "a per-day payment compelling compliance",
    "penalty": "the Member-State 'effective, proportionate and dissuasive' rules a directive/regulation leaves to national law",
    "criminal_sanction": "a criminal, rather than administrative, penalty",
}

#: Every penalty kind projects onto the SAME 5D dimension — see the module
#: docstring's own "The 5D projection" section for the justification.
EDGE_DIMENSION = "causal"


# ── ruleset loading / validation / digest ───────────────────────────────────

def load_ruleset(source: "str | Path | dict | None" = None) -> dict:
    """Load a penalty ruleset DOCUMENT — the cue-table DATA
    :func:`find_penalties` checks against. `source` is a ruleset dict
    already in memory, a path to a JSON file, or `None` (loads the packaged
    default, `penalty_rules.json`). Never parses or infers cues from code;
    the ruleset is always data, read verbatim."""
    if source is None:
        source = _RULES_PATH
    if isinstance(source, dict):
        return source
    return json.loads(Path(source).read_text(encoding="utf-8"))


_BOUND_TYPES = frozenset({"ceiling", "floor_of_maximum", "minimum", "unspecified"})
_COMBINATION_RULES = frozenset({"whichever_is_higher", "whichever_is_lower", "none"})


def _phrase_table_violations(table: Any, field_name: str, value_key: str, allowed: "frozenset[str] | None") -> list:
    out = []
    if not isinstance(table, list) or not table:
        return [f"penalty ruleset field {field_name!r} must be a non-empty list"]
    for i, entry in enumerate(table):
        if not isinstance(entry, dict):
            out.append(f"{field_name}[{i}] must be a mapping")
            continue
        pattern = entry.get("pattern")
        if not isinstance(pattern, str) or not pattern:
            out.append(f"{field_name}[{i}].pattern must be a non-empty string")
        else:
            try:
                re.compile(pattern)
            except re.error as exc:
                out.append(f"{field_name}[{i}].pattern does not compile: {exc}")
        value = entry.get(value_key)
        if allowed is not None and value not in allowed:
            out.append(f"{field_name}[{i}].{value_key} {value!r} must be one of {sorted(allowed)!r}")
    return out


def ruleset_violations(doc: Any) -> list:
    """Shape violations of a penalty ruleset document: a mapping with a
    non-empty string `ruleset_id`, a non-empty list `bound_type_phrases`
    (each entry a compiling `pattern` and a `bound_type` in
    :data:`_BOUND_TYPES` minus `unspecified`), a non-empty list
    `combination_phrases` (each entry a compiling `pattern` and a
    `combination_rule` in :data:`_COMBINATION_RULES` minus `none`), and a
    non-empty list `cues`, each cue a mapping with non-empty string
    `cue_id`/`trigger_pattern`, a `penalty_kind` that MUST be a known key
    of :data:`PENALTY_KINDS`, a list (possibly empty) of string
    `require_all_patterns`, a positive integer `max_span_chars`, a
    non-empty string `clause_end_chars` when present (default `"."`), a
    boolean `expects_amount`, a `confidence` number in `[0, 1]`, and a
    list (possibly empty) `addressee_patterns`, each entry a compiling
    string `pattern` and a non-empty string `label`. Every
    `trigger_pattern` and `require_all_patterns` entry MUST compile as a
    regex. Returns `[]` when the document validates."""
    if not isinstance(doc, dict):
        return ["penalty ruleset must be a mapping"]
    out = []
    ruleset_id = doc.get("ruleset_id")
    if not isinstance(ruleset_id, str) or not ruleset_id:
        out.append("penalty ruleset field 'ruleset_id' must be a non-empty string")

    out.extend(_phrase_table_violations(
        doc.get("bound_type_phrases"), "bound_type_phrases", "bound_type",
        _BOUND_TYPES - {"unspecified"}))
    out.extend(_phrase_table_violations(
        doc.get("combination_phrases"), "combination_phrases", "combination_rule",
        _COMBINATION_RULES - {"none"}))

    cues = doc.get("cues")
    if not isinstance(cues, list) or not cues:
        out.append("penalty ruleset field 'cues' must be a non-empty list")
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
        penalty_kind = cue.get("penalty_kind")
        if penalty_kind not in PENALTY_KINDS:
            out.append(f"cues[{i}].penalty_kind {penalty_kind!r} is not a known PENALTY_KINDS key {sorted(PENALTY_KINDS)!r}")
        patterns = cue.get("require_all_patterns", [])
        if not isinstance(patterns, list) or not all(isinstance(p, str) and p for p in patterns):
            out.append(f"cues[{i}].require_all_patterns must be a list of non-empty strings")
        else:
            for p in patterns:
                try:
                    re.compile(p)
                except re.error as exc:
                    out.append(f"cues[{i}].require_all_patterns entry does not compile: {exc}")
        clause_end_chars = cue.get("clause_end_chars", ".")
        if not isinstance(clause_end_chars, str) or not clause_end_chars:
            out.append(f"cues[{i}].clause_end_chars must be a non-empty string when present")
        max_span = cue.get("max_span_chars")
        if not isinstance(max_span, int) or isinstance(max_span, bool) or max_span <= 0:
            out.append(f"cues[{i}].max_span_chars must be a positive integer")
        expects_amount = cue.get("expects_amount")
        if not isinstance(expects_amount, bool):
            out.append(f"cues[{i}].expects_amount must be a boolean")
        confidence = cue.get("confidence")
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not (0.0 <= float(confidence) <= 1.0):
            out.append(f"cues[{i}].confidence must be a number in [0, 1]")
        addressee_patterns = cue.get("addressee_patterns", [])
        if not isinstance(addressee_patterns, list):
            out.append(f"cues[{i}].addressee_patterns must be a list when present")
        else:
            for j, entry in enumerate(addressee_patterns):
                if not isinstance(entry, dict):
                    out.append(f"cues[{i}].addressee_patterns[{j}] must be a mapping")
                    continue
                pattern = entry.get("pattern")
                if not isinstance(pattern, str) or not pattern:
                    out.append(f"cues[{i}].addressee_patterns[{j}].pattern must be a non-empty string")
                else:
                    try:
                        re.compile(pattern)
                    except re.error as exc:
                        out.append(f"cues[{i}].addressee_patterns[{j}].pattern does not compile: {exc}")
                label = entry.get("label")
                if not isinstance(label, str) or not label:
                    out.append(f"cues[{i}].addressee_patterns[{j}].label must be a non-empty string")
    return out


def cue_table_digest() -> str:
    """Sha256 digest over the CODE-side fixtures that affect every
    `find_penalties` call regardless of the ruleset — folded into
    :func:`ruleset_digest` so a code edit to any of these is pinned
    exactly like a ruleset edit."""
    doc = {
        "penalty_kinds": sorted(PENALTY_KINDS),
        "edge_dimension": EDGE_DIMENSION,
        "eur_amount_pattern": _EUR_AMOUNT_RE.pattern,
        "percentage_pattern": _PERCENTAGE_RE.pattern,
        "paragraph_marker_pattern": _PARA_MARKER_RE.pattern,
        "provision_word_pattern": _PROVISION_WORD_RE.pattern,
        "number_token_pattern": _NUMBER_TOKEN_RE.pattern,
        "roman_token_pattern": _ROMAN_TOKEN_RE.pattern,
        "exclusion_anchor_pattern": _EXCLUSION_ANCHOR_RE.pattern,
        "broad_anchor_pattern": _BROAD_ANCHOR_RE.pattern,
        "narrow_anchor_pattern": _NARROW_ANCHOR_RE.pattern,
        "narrow_window_chars": _NARROW_WINDOW_CHARS,
    }
    return _grounding_digest(doc)["sha256"]


def ruleset_digest(doc: dict) -> str:
    """Sha256 digest (`five_d_nd.grounding.digest`) over the ruleset
    document AND the code-side cue table (:func:`cue_table_digest`) — pins
    exactly which cues AND which number/citation fixtures a given
    `find_penalties` call ran against."""
    return _grounding_digest({"ruleset": doc, "cue_table_digest": cue_table_digest()})["sha256"]


# ── the deterministic clause reader ──────────────────────────────────────────

_DEFAULT_CLAUSE_END_CHARS = "."


def _clause_span(text: str, start: int, max_span_chars: int, clause_end_chars: str = _DEFAULT_CLAUSE_END_CHARS) -> "tuple[int, int]":
    """The `(start, end)` span of the clause beginning at `start`, ending
    at the FIRST character in `clause_end_chars` found within
    `max_span_chars` — except a period immediately followed by a comma
    (`(?!\\s*,)`), which is a typeset error in the source text (AI Act
    Art. 101(1)'s own "...whichever is higher., when..."), never a real
    sentence boundary, and is skipped. `max_span_chars` is an UPPER SAFETY
    BOUND, not a working limit: when NO such character is found within
    it, raises `ValueError` rather than truncating the span — a clause
    that overruns its own cue's bound is a ruleset-tuning defect to fix,
    never something to paper over with a silently cut-off span."""
    window_end = min(len(text), start + max_span_chars)
    parts = []
    for ch in clause_end_chars:
        parts.append(r"\.(?!\s*,)" if ch == "." else re.escape(ch))
    end_re = re.compile("(?:" + "|".join(parts) + ")")
    m = end_re.search(text, start, window_end)
    if not m:
        raise ValueError(
            f"no clause-ending character found within {max_span_chars} chars of "
            f"position {start} (clause_end_chars={clause_end_chars!r}) — "
            "increase max_span_chars for this cue rather than truncate silently")
    return start, m.end()


#: A numbered-paragraph marker — "4. " at a line start, or the AI Act's own
#: "\n 3.\xa0\xa0\xa0" (space/no-break-space run after the dot). `\s` matches a
#: no-break space under Python's default Unicode regex semantics, so ONE
#: pattern covers both corpus styles.
_PARA_MARKER_RE = re.compile(r"(?:^|\n)\s*(?P<para>\d{1,2})\.\s")


def _paragraph_marker_before(text: str, pos: int, window: int = 500) -> "tuple[str | None, int]":
    """The paragraph NUMBER and the character offset of the nearest
    numbered-paragraph marker found within `window` chars before `pos`, or
    `(None, pos)` when none is found."""
    window_start = max(0, pos - window)
    matches = list(_PARA_MARKER_RE.finditer(text, window_start, pos))
    if not matches:
        return None, pos
    m = matches[-1]
    return m.group("para"), m.start()


# ── provision tokens: "Article(s) <N>" and "Chapter <roman>" ───────────────

#: Matches the WORD only ("Article"/"Articles"/"Chapter"/"Chapters"),
#: captured so the caller knows which token grammar to apply next.
_PROVISION_WORD_RE = re.compile(r"\b(Articles?|Chapters?)\s+", re.IGNORECASE)

#: An Article token: a bare number, an optional parenthesised sub-point
#: ("58(2)"), a "to"-range ("25 to 39" — `to` only matches here between
#: two digit groups, so the connector word "to" inside an unrelated phrase
#: never becomes a token), or a BARE parenthesised continuation ("(3)",
#: "(4)") that carries no article number of its own — AI Act Art. 99(4)(f)
#: "Article 31, Article 33(1), (3) and (4) or Article 34" states THREE
#: sub-points of Article 33 this way; :func:`_walk_provisions_in_range`
#: reattaches a bare continuation to the MOST RECENT full article number
#: it saw, rather than losing it or storing it unattached.
_NUMBER_TOKEN_RE = re.compile(r"\d+(?:\(\d+\))?(?:\s+to\s+\d+(?:\(\d+\))?)?|\(\d+\)")

#: A Chapter token: a roman numeral ("IX").
_ROMAN_TOKEN_RE = re.compile(r"[IVXLCDM]+\b")

_LIST_SEP_RE = re.compile(r"\s*(?:,|and|or)\s*", re.IGNORECASE)


def _walk_one_provision_run(text: str, pos: int) -> "tuple[list[str], int]":
    """Starting EXACTLY at `pos`, consume one `Article(s)/Chapter(s)
    <token>[, <token>]...` run if `pos` is immediately the start of one;
    returns `([], pos)` otherwise. Used by the exclusion-phrase reader,
    which only recognises a provision list that follows its own connector
    phrase with no other text in between."""
    m = _PROVISION_WORD_RE.match(text, pos)
    if not m:
        return [], pos
    is_chapter = m.group(1).lower().startswith("chapter")
    token_re = _ROMAN_TOKEN_RE if is_chapter else _NUMBER_TOKEN_RE
    prefix = "Chapter " if is_chapter else ""
    cur = m.end()
    tokens: "list[str]" = []
    last_base = None
    while True:
        tm = token_re.match(text, cur)
        if not tm:
            break
        raw = tm.group()
        if raw.startswith("(") and last_base is not None:
            token = f"{prefix}{last_base}{raw}"
        else:
            token = prefix + raw
            base_m = re.match(r"\d+", raw)
            if base_m:
                last_base = base_m.group()
        if token not in tokens:
            tokens.append(token)
        cur = tm.end()
        sm = _LIST_SEP_RE.match(text, cur)
        if not sm or sm.end() == cur:
            break
        cur = sm.end()
    return tokens, cur


def _walk_provisions_in_range(text: str, start: int, end: int) -> "list[str]":
    """Every `Article(s)/Chapter(s) <token>[, <token>]...` run found
    ANYWHERE in `text[start:end]` (via `finditer`, not anchored to
    `start`), flattened and de-duplicated, in order."""
    tokens: "list[str]" = []
    for m in _PROVISION_WORD_RE.finditer(text, start, end):
        run_tokens, _ = _walk_one_provision_run(text, m.start())
        for t in run_tokens:
            if t not in tokens:
                tokens.append(t)
    return tokens


#: An exclusion connector: "other than", "with the exception of",
#: "except(ing)", "excluding" — the text AFTER this phrase (optionally
#: through "those laid down in"/"referred to in"/"set out in") names
#: provisions the clause explicitly carves OUT of its own scope, never an
#: infringement (see module docstring's own "Negation and exclusion"
#: section).
_EXCLUSION_ANCHOR_RE = re.compile(
    r"\b(?:other\s+than|with\s+the\s+exception\s+of|except(?:ing)?|excluding)\b\s*"
    r"(?:those\s+)?(?:laid\s+down\s+in\s+|referred\s+to\s+in\s+|set\s+out\s+in\s+)?",
    re.IGNORECASE,
)

#: A BROAD infringement anchor — "infringements of the following
#: provisions", "non-compliance with ... the following provisions" —
#: whose own bulleted enumeration IS the clause's infringed-provision
#: list; capture scans the WHOLE remainder of the clause after it.
_BROAD_ANCHOR_RE = re.compile(
    r"\b(?:infringements?\s+of|non[- ]compliance\s+with)\s+"
    r"(?:any\s+of\s+)?(?:the\s+following\s+)?provisions?\b",
    re.IGNORECASE,
)

#: A NARROW infringement anchor — each occurrence is scoped to a short
#: window immediately AFTER it, never the whole clause, since a clause
#: using this form (GDPR Art. 83(6); AI Act Art. 100(2)/101(1); DSA Art.
#: 74(1)/(2); NIS2 Art. 34(4)/(5)) routinely ALSO names a procedural
#: cross-reference elsewhere that this anchor's own window must never
#: reach. `refuse(s/d) to` is the SAME shape of infringement verb as
#: `fail(s/ed) to` (DSA Art. 74(2)(d): "refuse to submit to an
#: inspection pursuant to Article 69"). "supply incorrect, incomplete
#: or misleading information" is its own anchor for the identical reason
#: AI Act Art. 101(1)(b)'s own "failed to comply with a request for a
#: document or for information pursuant to Article 91" already captures
#: Art. 91 — a REQUEST (as opposed to a DECISION or a PERSON) the clause
#: asks for, and then is not properly answered, IS the infringement, not
#: a merely-procedural reference (DSA Art. 74(2)(a): "supply incorrect,
#: incomplete or misleading information in response to a simple request
#: or request by a decision pursuant to Article 67").
_NARROW_ANCHOR_RE = re.compile(
    r"\bfail(?:s|ed)?\s+to\b|\binfringe(?:s|d)?\b|"
    r"\bnon[- ]compliance\s+(?:of|with)\b|\bin\s+breach\s+of\b|"
    r"\brefuse(?:s|d)?\s+to\b|"
    r"\bsupply\s+incorrect,\s+incomplete\s+or\s+misleading\s+information\b",
    re.IGNORECASE,
)

_NARROW_WINDOW_CHARS = 300


def _extract_provisions(window_text: str) -> "tuple[list[str], list[str]]":
    """`(infringed, excluded)` for ONE bounded context window (see module
    docstring's own "Infringement-anchored extraction" section).
    Exclusion phrases are read and MASKED (replaced with spaces, so their
    own length/offsets are preserved for the broad/narrow anchor scan that
    follows) before infringement scanning ever runs — an excluded
    provision therefore can never also surface as infringed."""
    excluded: "list[str]" = []
    chars = list(window_text)
    for m in _EXCLUSION_ANCHOR_RE.finditer(window_text):
        tokens, run_end = _walk_one_provision_run(window_text, m.end())
        if not tokens:
            continue
        for t in tokens:
            if t not in excluded:
                excluded.append(t)
        for i in range(m.start(), run_end):
            chars[i] = " "
    masked = "".join(chars)

    infringed: "list[str]" = []
    broad = _BROAD_ANCHOR_RE.search(masked)
    if broad:
        infringed = _walk_provisions_in_range(masked, broad.end(), len(masked))
    else:
        for nm in _NARROW_ANCHOR_RE.finditer(masked):
            window_end = min(len(masked), nm.end() + _NARROW_WINDOW_CHARS)
            for tok in _walk_provisions_in_range(masked, nm.end(), window_end):
                if tok not in infringed:
                    infringed.append(tok)
    infringed = [t for t in infringed if t not in excluded]
    return infringed, excluded


_RANGE_RE = re.compile(r"^(\d+)\s+to\s+(\d+)$")
_BASE_ARTICLE_NUMBER_RE = re.compile(r"^(\d+)")


def _provision_to_edge_subjects(instrument: str, token: str) -> "list[str]":
    """ONE infringed-provision token -> one or more edge-subject ids,
    `"<instrument>:Art.<N>"` (or `"<instrument>:Chapter.<roman>"`) — the
    ARTICLE NODE ONLY, never a sub-point/paragraph. A "<N> to <M>" range
    expands into EVERY article in it — "25 to 39" -> `Art.25`, `Art.26`,
    ..., `Art.39` — each its own edge, never one bundled `s`. A
    parenthesised sub-point is DROPPED from the subject id itself —
    `"33(1)"`, `"33(3)"`, `"33(4)"` all resolve to the SAME subject,
    `"<instrument>:Art.33"` — the article is what joins the article-node
    graph; the sub-point detail is carried in the TRIPLE's own
    `provenance.provisions_detail` instead (see :func:`penalty_to_triples`),
    never folded into the subject id, where it would create one node per
    sub-point instead of one node per article (`ai-act:Art.33(1)` and
    `ai-act:Art.33(3)` would never join `ai-act:Art.33`).
    `penalty_to_triples`'s own
    de-duplication (`if subject not in edge_subjects`) collapses the
    THREE tokens into the ONE `Art.33` edge automatically once the
    sub-point is stripped here."""
    if token.startswith("Chapter "):
        return [f"{instrument}:Chapter.{token[len('Chapter '):]}"]
    m = _RANGE_RE.match(token)
    if m:
        lo, hi = int(m.group(1)), int(m.group(2))
        return [f"{instrument}:Art.{n}" for n in range(lo, hi + 1)]
    base_m = _BASE_ARTICLE_NUMBER_RE.match(token)
    base = base_m.group(1) if base_m else token
    return [f"{instrument}:Art.{base}"]


# ── number parsing: EUR amounts, percentages, bound type, combination ───────

#: An EUR amount with plain-space OR no-break-space thousands separators,
#: in EITHER surface order: "10 000 000 EUR" (amount before the unit,
#: GDPR/NIS2's own style) or "EUR 35\xa0000\xa0000" (unit before the
#: amount, the AI Act's own style).
_EUR_AMOUNT_RE = re.compile(
    r"\bEUR\s*(?P<amount_after_eur>\d[\d\s ]*\d)\b"
    r"|"
    r"\b(?P<amount_before_eur>\d[\d\s ]*\d)\s*EUR\b",
    re.IGNORECASE,
)

#: A percentage with either a plain decimal point or a decimal COMMA (NIS2
#: Art. 34(5): "1,4 %").
_PERCENTAGE_RE = re.compile(r"(?P<value>\d+(?:[.,]\d+)?)\s*%")

#: A turnover-basis phrase: whatever follows the matched percentage's own
#: "of ..." up to the next clause-level boundary — a comma before
#: "whichever"/"or", a semicolon, a period, a colon, "where", "in order
#: to", or "or EUR" (AI Act Art. 101(1)'s own "...or EUR 15 000 000,
#: whichever is higher" — the alternative FIXED amount is not part of the
#: percentage's own turnover basis).
_TURNOVER_BASIS_RE = re.compile(
    r"%\s*of\s+(?P<basis>.+?)"
    r"(?=,\s*whichever\b|,\s*or\b|\bor\s+EUR\b|;|\.|:|\bwhere\b|\bin\s+order\s+to\b|$)",
    re.IGNORECASE | re.DOTALL,
)

_LEADING_ARTICLE_RE = re.compile(r"^(?:the|a|an)\s+", re.IGNORECASE)
_TRAILING_PER_DAY_RE = re.compile(r"\s*per\s+day\s*$", re.IGNORECASE)


def _find_amount(text: str) -> "int | None":
    m = _EUR_AMOUNT_RE.search(text)
    if not m:
        return _parse_word_amount(text)
    raw = m.group("amount_after_eur") or m.group("amount_before_eur")
    digits = re.sub(r"[\s ]", "", raw)
    return int(digits)


def _find_percentage(text: str) -> "tuple[float | None, str | None]":
    m = _PERCENTAGE_RE.search(text)
    if not m:
        return None, None
    value = float(m.group("value").replace(",", "."))
    basis_m = _TURNOVER_BASIS_RE.search(text, m.start())
    basis = None
    if basis_m:
        basis = basis_m.group("basis").strip()
        basis = _TRAILING_PER_DAY_RE.sub("", basis)
        basis = _LEADING_ARTICLE_RE.sub("", basis).strip()
        basis = basis.rstrip(" ,;").strip()
    return value, basis or None


#: A small, closed ones/teens/tens/hundred/thousand/million lexicon —
#: handles an amount written out in words ("ten million euros", "seven
#: hundred fifty thousand euros"). No clause in the five-instrument corpus
#: this grammar runs against ever spells an amount out; this function is
#: exercised only by a synthetic conformance vector.
_WORD_ONES = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19,
}
_WORD_TENS = {
    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
}
_WORD_MULTIPLIERS = {"hundred": 100, "thousand": 1_000, "million": 1_000_000}
_WORD_TOKEN_RE = re.compile(
    r"\b(" + "|".join(sorted(
        list(_WORD_ONES) + list(_WORD_TENS) + list(_WORD_MULTIPLIERS) + ["and"],
        key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)
_WORD_AMOUNT_EUROS_RE = re.compile(
    r"\b((?:(?:" + "|".join(list(_WORD_ONES) + list(_WORD_TENS) + list(_WORD_MULTIPLIERS) + ["and"]) + r")\s+)"
    r"*(?:" + "|".join(list(_WORD_ONES) + list(_WORD_TENS) + list(_WORD_MULTIPLIERS)) + r"))\s+euros?\b",
    re.IGNORECASE,
)


def _words_to_int(phrase: str) -> "int | None":
    total = 0
    current = 0
    saw_token = False
    for tok in _WORD_TOKEN_RE.findall(phrase):
        word = tok.lower()
        if word == "and":
            continue
        saw_token = True
        if word in _WORD_ONES:
            current += _WORD_ONES[word]
        elif word in _WORD_TENS:
            current += _WORD_TENS[word]
        elif word == "hundred":
            current = (current or 1) * 100
        elif word in ("thousand", "million"):
            multiplier = _WORD_MULTIPLIERS[word]
            total += (current or 1) * multiplier
            current = 0
    total += current
    return total if saw_token else None


def _parse_word_amount(text: str) -> "int | None":
    m = _WORD_AMOUNT_EUROS_RE.search(text)
    if not m:
        return None
    return _words_to_int(m.group(1))


def _match_phrase_table(text: str, table: "list[dict]", value_key: str, default: str) -> str:
    for entry in table:
        if re.search(entry["pattern"], text, re.IGNORECASE):
            return entry[value_key]
    return default


def _find_addressee(cue: dict, context_window: str, article_prefix: str) -> "str | None":
    patterns = cue.get("addressee_patterns", [])
    for entry in patterns:
        if re.search(entry["pattern"], context_window, re.IGNORECASE):
            return entry["label"]
    for entry in patterns:
        if re.search(entry["pattern"], article_prefix, re.IGNORECASE):
            return entry["label"]
    return None


def find_penalties(
    articles: "Iterable[dict]",
    ruleset: "dict | None" = None,
) -> "list[dict]":
    """Deterministically find penalty records across a collection of
    ARTICLE-SEGMENTED instrument text.

    `articles` is an iterable of mappings, each with non-empty string keys
    `instrument_id`, `article_id`, and `text`. `ruleset` defaults to the
    packaged default (:func:`load_ruleset`) when omitted, and is VALIDATED
    FIRST (:func:`ruleset_violations`), raising `ValueError` before any
    article is scanned.

    Returns a list of penalty records, each a mapping with:
    `source_instrument`, `source_article`, `paragraph`, `penalty_kind`,
    `addressee`, `infringed_provisions` (possibly `[]`),
    `excluded_provisions` (possibly `[]`; see the module docstring's own
    "Negation and exclusion" section), `scope` (a short human-readable
    note, e.g. `"the instrument, other than Art. 5"`, set ONLY when
    `infringed_provisions` is empty AND `excluded_provisions` is not —
    `None` otherwise), `fixed_amount_eur`, `turnover_percentage`,
    `turnover_basis`, `combination_rule`, `bound_type`, `per_day`,
    `verbatim_span`, `match_start`, `cue_id`, `confidence`, `unresolved`,
    `basis` (always `"statute"` for this function), and `ruleset_digest`.

    Deterministic: the SAME `articles`/`ruleset` input always produces the
    SAME output, byte-for-byte once serialised — cues are applied in the
    ruleset's own list order, and the final list is sorted by
    `(source_instrument, source_article, cue_id, match_start)`.

    Raises `ValueError` on a malformed ruleset, on a malformed article
    mapping, or when a matched clause overruns its own cue's
    `max_span_chars` without reaching a clause-ending character (see
    :func:`_clause_span`).
    """
    if ruleset is None:
        ruleset = load_ruleset()
    violations = ruleset_violations(ruleset)
    if violations:
        raise ValueError(f"malformed penalty ruleset: {violations!r}")

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

    bound_type_phrases = ruleset["bound_type_phrases"]
    combination_phrases = ruleset["combination_phrases"]
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

                paragraph, para_start = _paragraph_marker_before(text, start)
                context_window = text[para_start:end]

                infringed_provisions, excluded_provisions = _extract_provisions(context_window)
                scope = None
                if not infringed_provisions and excluded_provisions:
                    scope = "the instrument, other than " + ", ".join(
                        f"Art. {t}" for t in excluded_provisions)

                addressee = _find_addressee(cue, context_window, text[:end])

                fixed_amount_eur = _find_amount(clause_text)
                turnover_percentage, turnover_basis = _find_percentage(clause_text)
                bound_type = _match_phrase_table(clause_text, bound_type_phrases, "bound_type", "unspecified")
                combination_rule = _match_phrase_table(clause_text, combination_phrases, "combination_rule", "none")

                expects_amount = cue["expects_amount"]
                unresolved = False
                if expects_amount:
                    if fixed_amount_eur is None and turnover_percentage is None:
                        unresolved = True
                    if bound_type == "unspecified":
                        unresolved = True

                confidence = float(cue["confidence"])
                if unresolved:
                    confidence = round(confidence * 0.6, 6)

                penalty_kind = cue["penalty_kind"]
                per_day = penalty_kind == "periodic_penalty_payment"

                verbatim = clause_text.strip()
                key = (source_instrument, source_article, cue["cue_id"], start)
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                records.append({
                    "source_instrument": source_instrument,
                    "source_article": source_article,
                    "paragraph": paragraph,
                    "penalty_kind": penalty_kind,
                    "addressee": addressee,
                    "infringed_provisions": infringed_provisions,
                    "excluded_provisions": excluded_provisions,
                    "scope": scope,
                    "fixed_amount_eur": fixed_amount_eur,
                    "turnover_percentage": turnover_percentage,
                    "turnover_basis": turnover_basis,
                    "combination_rule": combination_rule,
                    "bound_type": bound_type,
                    "per_day": per_day,
                    "verbatim_span": verbatim,
                    "match_start": start,
                    "cue_id": cue["cue_id"],
                    "confidence": confidence,
                    "unresolved": unresolved,
                    "basis": "statute",
                    "ruleset_digest": rs_digest,
                })
    records.sort(key=lambda r: (r["source_instrument"], r["source_article"], r["cue_id"], r["match_start"]))
    return records


# ── 5D triples ────────────────────────────────────────────────────────────────

def _penalty_node_id(record: dict) -> str:
    """The `o` node for ONE penalty record — `"<source_article>(<paragraph>):<penalty_kind>"`
    when the paragraph is known, else `"<source_article>:<penalty_kind>"`
    — UNIQUE per penalty CLAUSE, never per article (see module docstring's
    own "Edge identity" section: GDPR Art. 83(4)/(5)/(6), NIS2 Art.
    34(4)/(5), and AI Act Art. 100(2)/(3) each get their own distinct
    node)."""
    paragraph = record.get("paragraph")
    source_article = record["source_article"]
    penalty_kind = record["penalty_kind"]
    if paragraph:
        return f"{source_article}({paragraph}):{penalty_kind}"
    return f"{source_article}:{penalty_kind}"


def penalty_to_triples(record: dict, grammar_id: str = "penalty-grammar") -> "list[dict]":
    """The §11-shaped 5D triples for ONE penalty record (statute- or
    authority-sourced — both shapes carry the same fields) — ONE triple
    PER infringed provision, after range expansion (see module
    docstring's own "Edge identity" section and
    :func:`_provision_to_edge_subjects`). Returns `[]`, never an edge,
    for a record naming NO infringed provision at all (DSA Art. 52(3)'s
    own two percentage-only sentences, AI Act Art. 100(3)'s own
    instrument-wide "other than Art. 5" scope) — there is nothing to name
    as any edge's own `s`; the record itself is still perfectly
    well-formed, so this is NOT an error. **Raises `ValueError` for an
    `unresolved` record** (its own amount or bound could not be parsed) —
    there is nothing well-formed to attach a causal edge to, regardless
    of how many provisions it names.

    Once resolved: EACH `s` is `"<instrument>:Art.<N>"` (or
    `"<instrument>:Chapter.<roman>"`) — the ARTICLE NODE ONLY, with any
    parenthesised sub-point STRIPPED (`"33(1)"`/`"33(3)"`/`"33(4)"` all
    resolve to the SAME `s`, `"<instrument>:Art.33"`, de-duplicated by
    the loop above into ONE edge, not three) — `o` is
    :func:`_penalty_node_id`'s own result, the SAME for every triple built
    from this one record. `dimension` is always :data:`EDGE_DIMENSION`.
    `weight` is `record["confidence"]`, clamped into `[0, 1]`.
    `provenance` carries `basis`, `cue_id`, `verbatim_span`,
    `excluded_provisions`, `provisions_detail` (the record's own
    `infringed_provisions` VERBATIM, sub-points and ranges intact — e.g.
    `["33(1)", "33(3)", "33(4)"]` — so the sub-point/paragraph detail a
    stripped `s` no longer carries is never actually lost, just moved),
    and the record's own structured fields."""
    penalty_kind = record["penalty_kind"]
    if penalty_kind not in PENALTY_KINDS:
        raise ValueError(f"unknown penalty_kind {penalty_kind!r}; not one of {sorted(PENALTY_KINDS)!r}")
    if record.get("unresolved"):
        raise ValueError(
            "cannot convert an unresolved penalty record to a triple — "
            "its own amount or bound could not be parsed; see the record's "
            "own 'unresolved' field")
    infringed_provisions = record.get("infringed_provisions") or []
    instrument = record["source_instrument"]
    edge_subjects: "list[str]" = []
    for token in infringed_provisions:
        for subject in _provision_to_edge_subjects(instrument, token):
            if subject not in edge_subjects:
                edge_subjects.append(subject)
    if not edge_subjects:
        return []

    o = _penalty_node_id(record)
    weight = round(max(0.0, min(1.0, float(record.get("confidence", 1.0)))), 6)
    provenance = {
        "basis": record.get("basis", "statute"),
        "verbatim_span": record.get("verbatim_span"),
        "paragraph": record.get("paragraph"),
        "addressee": record.get("addressee"),
        "excluded_provisions": record.get("excluded_provisions", []),
        "provisions_detail": record.get("infringed_provisions", []),
        "scope": record.get("scope"),
        "fixed_amount_eur": record.get("fixed_amount_eur"),
        "turnover_percentage": record.get("turnover_percentage"),
        "turnover_basis": record.get("turnover_basis"),
        "combination_rule": record.get("combination_rule", "none"),
        "bound_type": record.get("bound_type", "unspecified"),
        "per_day": bool(record.get("per_day", False)),
    }
    if record.get("cue_id") is not None:
        provenance["cue_id"] = record["cue_id"]
    if record.get("authority") is not None:
        provenance["authority"] = record["authority"]
    return [
        {
            "s": s,
            "p": penalty_kind,
            "o": o,
            "dimension": EDGE_DIMENSION,
            "weight": weight,
            "provenance": provenance,
            "grammar_id": grammar_id,
        }
        for s in edge_subjects
    ]


def penalties_to_triples(records: "Iterable[dict]", grammar_id: str = "penalty-grammar") -> "list[dict]":
    """Every triple :func:`penalty_to_triples` builds across ALL
    `records`, flattened in the SAME record order (a record producing no
    edge simply contributes nothing) — this function performs no
    additional filtering or sorting of its own."""
    out: "list[dict]" = []
    for record in records:
        out.extend(penalty_to_triples(record, grammar_id))
    return out


# ── authority-sourced penalties: API and validation only, never populated ───

def authority_penalty_violations(doc: Any) -> list:
    """Shape violations of an AUTHORITY-SOURCED penalty record (a court
    ruling or a regulator's guidance that types a penalty clause not
    stated in the statute itself). A mapping with: non-empty string
    `source_instrument`/`source_article`; a `penalty_kind` that MUST be a
    known key of :data:`PENALTY_KINDS`; a list `infringed_provisions` of
    non-empty strings (possibly empty); a list `excluded_provisions` of
    non-empty strings (possibly empty) when present; optional string
    `paragraph`/`addressee`/`scope`/`turnover_basis`/`verbatim_span`;
    optional integer `fixed_amount_eur`; optional number
    `turnover_percentage`; a `combination_rule` in
    :data:`_COMBINATION_RULES` when present; a `bound_type` in
    :data:`_BOUND_TYPES` when present; a boolean `per_day` when present; a
    `basis` that MUST be the literal string `"authority"`; an `authority`
    mapping with non-empty string `name`/`locator`; and, when present, a
    `confidence` number in `[0, 1]`, and an `unresolved` boolean. Returns
    `[]` when the document validates.

    **This function validates; it does not create.** No caller in this
    package ever constructs a document that passes this check with real
    data — this ingestion path ships as an API/validation surface only,
    seeded with nothing."""
    if not isinstance(doc, dict):
        return ["authority penalty record must be a mapping"]
    out = []
    for field in ("source_instrument", "source_article"):
        value = doc.get(field)
        if not isinstance(value, str) or not value:
            out.append(f"authority penalty field {field!r} must be a non-empty string")
    penalty_kind = doc.get("penalty_kind")
    if penalty_kind not in PENALTY_KINDS:
        out.append(f"authority penalty field 'penalty_kind' {penalty_kind!r} is not a known "
                    f"PENALTY_KINDS key {sorted(PENALTY_KINDS)!r}")
    infringed_provisions = doc.get("infringed_provisions", [])
    if not isinstance(infringed_provisions, list) or not all(isinstance(p, str) and p for p in infringed_provisions):
        out.append("authority penalty field 'infringed_provisions' must be a list of non-empty strings")
    excluded_provisions = doc.get("excluded_provisions", [])
    if not isinstance(excluded_provisions, list) or not all(isinstance(p, str) and p for p in excluded_provisions):
        out.append("authority penalty field 'excluded_provisions' must be a list of non-empty strings")
    for field in ("paragraph", "addressee", "scope", "turnover_basis", "verbatim_span"):
        if field in doc and doc[field] is not None and not isinstance(doc[field], str):
            out.append(f"authority penalty field {field!r} must be a string or null when present")
    if "fixed_amount_eur" in doc and doc["fixed_amount_eur"] is not None:
        value = doc["fixed_amount_eur"]
        if isinstance(value, bool) or not isinstance(value, int):
            out.append("authority penalty field 'fixed_amount_eur' must be an integer or null when present")
    if "turnover_percentage" in doc and doc["turnover_percentage"] is not None:
        value = doc["turnover_percentage"]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            out.append("authority penalty field 'turnover_percentage' must be a number or null when present")
    if "combination_rule" in doc and doc["combination_rule"] not in _COMBINATION_RULES:
        out.append(f"authority penalty field 'combination_rule' must be one of {sorted(_COMBINATION_RULES)!r} when present")
    if "bound_type" in doc and doc["bound_type"] not in _BOUND_TYPES:
        out.append(f"authority penalty field 'bound_type' must be one of {sorted(_BOUND_TYPES)!r} when present")
    if "per_day" in doc and not isinstance(doc["per_day"], bool):
        out.append("authority penalty field 'per_day' must be a boolean when present")
    if "unresolved" in doc and not isinstance(doc["unresolved"], bool):
        out.append("authority penalty field 'unresolved' must be a boolean when present")
    basis = doc.get("basis")
    if basis != "authority":
        out.append(f"authority penalty field 'basis' must be the literal string 'authority', got {basis!r}")
    authority = doc.get("authority")
    if not isinstance(authority, dict):
        out.append("authority penalty field 'authority' must be a mapping")
    else:
        for field in ("name", "locator"):
            value = authority.get(field)
            if not isinstance(value, str) or not value:
                out.append(f"authority penalty field 'authority.{field}' must be a non-empty string")
    if "confidence" in doc:
        confidence = doc["confidence"]
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)) or not (0.0 <= float(confidence) <= 1.0):
            out.append("authority penalty field 'confidence' must be a number in [0, 1] when present")
    return out


def authority_penalty_to_triples(doc: dict, grammar_id: str = "penalty-grammar") -> "list[dict]":
    """The 5D triples for ONE authority-sourced penalty record, after
    validating it (:func:`authority_penalty_violations`) — raises
    `ValueError` on any violation BEFORE building a triple, exactly like
    `find_penalties` validates its ruleset first. Delegates to
    :func:`penalty_to_triples` once validated."""
    violations = authority_penalty_violations(doc)
    if violations:
        raise ValueError(f"malformed authority penalty record: {violations!r}")
    return penalty_to_triples(doc, grammar_id)


# ── §9 nD contract attachment ─────────────────────────────────────────────────

def build_nd_system() -> dict:
    """The `NDSystem` document this grammar publishes to attach to 5D
    (§9). One axis, `penalty_kind`: a CLOSED-vocabulary axis over this
    grammar's own four penalty-kind ids (:data:`PENALTY_KINDS`)."""
    return {
        "id": "penalty-grammar",
        "namespace": "org.loomground.nd.penalty",
        "version": "1.0.0",
        "version_5d": "1.0-draft",
        "axes": {
            "penalty_kind": {
                "value_type": "controlled_identifier",
                "cardinality": "one",
                "vocabulary_mode": "closed",
                "vocabulary": sorted(PENALTY_KINDS),
            }
        },
        "bindings": [
            {"form_slot": "penalty_kind", "allowed_axes": ["penalty_kind"], "required": True},
        ],
        "ontology_relations": [],
        "validation": {
            "unknown_values": "reject",
            "missing_coordinates": "reject",
            "provenance_required": True,
        },
    }


def build_descriptor() -> dict:
    """The JSON-interchange grammar descriptor (§9) for this grammar.
    Binds EVERY penalty-kind id to the SAME 5D dimension, `causal`
    (:data:`EDGE_DIMENSION`; see :data:`PENALTY_KINDS` and the module
    docstring's own "The 5D projection" section for why a single dimension
    covers all four kinds). `produce` is OMITTED here (the interchange
    form); a runtime host wires :func:`find_penalties` +
    :func:`penalties_to_triples` in as the callable pair separately."""
    nd_system = build_nd_system()
    binding = {kind: EDGE_DIMENSION for kind in PENALTY_KINDS}
    return {
        "plane": "penalty-grammar",
        "language_version": nd_system["version"],
        "nd_system": nd_system,
        "binding": binding,
        "examples": [],
        "contract_version": "1.0-draft",
    }
