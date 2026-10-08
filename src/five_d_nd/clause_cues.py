# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""The clause-cue layer (D2) — spec/SPEC.md §8a, an ADDITIVE richer lowering.

Integrates the winning build's design and grafts (see
``docs/decisions/0007-clause-cue-layer-and-example-grammars.md``). Grafted here
is the "richer lowering" cue table (approach A's closed, regex-based cue
vocabulary, enriched with D+'s relational cue set), re-cast as a SECOND,
ADDITIVE layer that sits ALONGSIDE §8's assertoric layer — never
replacing it.

**Cue soundness on real GDPR text** (measured against a real corpus
before and after): four precision fixes, each documented at its own cue
table below — plural/ranged article citations now matched; a citation of
ANOTHER instrument ("Article 8 of Regulation (EU) No 182/2011", "Article
25(6) of Directive 95/46/EC") is now EXCLUDED from a GDPR cross-reference
link; `within` counts as temporal only with an actual time expression,
never for "within the Union"/"within the scope"; `means` counts as a
definition only in definitional form ("'X' means any/a/an/the ..."),
never for "automated means"/"by other means". Overlapping cue matches
within one dimension are now de-duplicated (one phrase counts once, not
once per overlapping pattern).

**§8 (D1, the assertoric layer) is UNCHANGED.** `five_d_nd.assertoric.
lower_assertion()` still lowers a clause to EXACTLY one relation, one
dimension, via the three-cue-kind (copula/order/modal) match it vendors
verbatim from loomground-factual @ ebf9fe1 — every factual-parity
conformance vector (`conformance/vectors/assertoric-lowering/`) and the
optional differential test against a real `loomground_factual` import stay
green, unmodified, forever. **loomground-factual itself does not implement
this module's own cue table** — that is an OPEN migration item, recorded in
Annex B, not a claim this specification makes about any other repository.

**What this module adds.** A clause is scanned, independently, against
FIVE closed, deterministic, regex cue tables — one per 5D dimension. EVERY
matching cue in a non-relational table (`causal`, `intentional`,
`temporal`, `structural`) adds `+1` to that dimension's own RAW
contribution count, and a clause may (and typically does, in a regulatory
text) hit more than one table at once — "the controller shall, within one
month and for the purposes of compliance, inform the data subject" hits
`temporal` (within one month) AND `intentional` (for the purposes of).
This is the "deterministic multi-relation clause lowering" ADR 0007
calls for: a modal sentence is no longer reduced to a
single `predication` -> relational contribution by THIS layer — it
contributes the dimensions of its own content cues.

**`relational` is DOWN-WEIGHTED by how many other cues fire**, replacing
an earlier all-or-nothing gate. The `relational` cue table here
(entity/obligation vocabulary: "controller", "processor", "data subject",
"right to", "obligation", ...) is ALWAYS counted (never gated to "only
when the others are silent"); its raw count is then run through
:func:`relational_effective` (`relational_count * s / (s + n_other)`, the
SAME `x/(x+s)` monotone family `five_d_nd.depth`'s own nesting signal
already uses) against `n_other`, the sum of the OTHER four dimensions'
own de-duplicated hit counts. The earlier design (an all-or-nothing gate:
`relational` counted ONLY when none of the other four hit at all) was
discontinuous by construction — GDPR Art. 65(5)'s own sentence
(`relational: 5`) flipped to `relational: 0` on a single added "Where
applicable, " — so this smooth down-weighting replaces the jump (the
FORMULA and its default scale are a design choice, as
`relational_effective`'s own docstring states explicitly). GDPR's
relational vocabulary still co-occurs with almost every sentence that
ALSO carries another cue, so `n_other > 0` routinely shrinks the
relational value substantially — but never discontinuously to exactly
zero from a nonzero count, and never at all when `n_other == 0`. A
clause with no cue hit at all still contributes nothing from this layer
(all-zero), exactly as §11's point formula already expects.

**Cross-references become explicit structural links, not just a count.**
An `Article N` / `Article N(M)` citation is BOTH a `+1 structural`
contribution PER DISTINCT TARGET (the citing sentence is, itself,
containment-adjacent to what it cites) AND an explicit directed link
`source_id -> target_id` (:func:`cross_reference_links`), dimension
`structural`, relation `cross_references` — "cross-references → explicit
links between entries" (see ADR 0007). The link is a §11
triple-shaped record; nothing here makes it normative (§7 N1 is
unaffected: a citation is a fact about a sentence's own surface form, not
an ought).

**Points keep the UNCHANGED §11 formula.** This module only supplies a
RICHER raw-contribution vector; `point[d] = round(min(raw[d]/saturation,
1.0), 6)` (§11) is untouched, and the contribution this module adds is
ADDED to whatever the assertoric layer (§8) already contributed on its
own single dimension — :func:`combined_contributions` does that
addition, the caller then calls
`five_d_nd.point.point_from_contributions` on the sum exactly as before.

Every cue list is closed, case-insensitive, stdlib `re` only — no learned
model, no stemming, no embeddings. Determinism and byte-reproducible
replay follow directly: the same clause text produces the same regex
matches on every machine, forever. Runtime is NEVER part of any value
this module returns (see `five_d_nd.replay` for where timing goes).

Stdlib only.
"""
from __future__ import annotations

import bisect
import math
import re
from collections.abc import Mapping
from typing import Any, Optional

__all__ = [
    "DIMENSIONS",
    "DEFAULT_CLAUSE_CUE_SATURATION",
    "CUE_TABLE",
    "ARTICLE_REF_RE",
    "count_cue_hits",
    "cross_reference_targets",
    "cross_reference_links",
    "DEFAULT_RELATIONAL_SUPPRESSION_SCALE",
    "relational_effective",
    "clause_cue_contributions",
    "combined_contributions",
    "clause_cue_point",
    "REFERENCE_KINDS",
    "resolve_references",
    "DEFAULT_XREF_RESOLVER",
    "clause_cue_point_from_profile",
    "cross_reference_links_from_profile",
    "enclosing_unit_at",
    "enclosing_units_at",
    "host_section_numbers_in",
]

#: §2's five dimensions, canonical order — this module never adds a sixth.
DIMENSIONS = ("structural", "causal", "intentional", "temporal", "relational")

#: The default saturation THIS layer's own raw counts are divided by when
#: materialising a point from them (§16, profile field
#: ``clause_cue_saturation``) — kept separate from §11's
#: ``point_saturation`` (the assertoric layer's own default, 5) because this
#: layer's raw counts are per-CLAUSE cue hits, typically 1-4, not per-ENTRY
#: aggregate contributions; a GDPR sentence rarely carries more than 2-4
#: independent cue hits on any one dimension, so 3 keeps the derived point
#: genuinely graded instead of pinned at the extremes for almost every
#: clause. Chosen, documented, overridable via the resolution profile —
#: never tuned against the GDPR ground truth used to measure AUC.
DEFAULT_CLAUSE_CUE_SATURATION = 3

# ── closed cue vocabularies (A's cue-table form, enriched with D+'s set) ──
# conditions/causes -> causal
_CAUSAL_CUES = [
    r"\bif\b", r"\bwhere\b", r"\bbecause\b", r"\bunless\b",
    r"\bresulting in\b", r"\bresult(?:s|ed|ing)?\s+(?:in|from)\b",
    r"\benables?\b", r"\bprovided that\b", r"\bin the event (?:of|that)\b",
    r"\bowing to\b", r"\bas a result of\b", r"\bgiven that\b",
    r"\bdue to\b", r"\bcause[sd]?\b", r"\btrigger(?:s|ed|ing)?\b",
    r"\blead(?:s|ing)?\s+to\b", r"\bgive\s+rise\s+to\b", r"\brisk[s]?\b",
    r"\blikely\s+to\b", r"\bprevent(?:s|ed|ing)?\b", r"\baffect(?:s|ed|ing)?\b",
]
# purposes -> intentional
_INTENTIONAL_CUES = [
    r"\bfor the purposes? of\b", r"\bin order to\b", r"\baimed at\b",
    r"\bwith (?:a )?view to\b", r"\bintended to\b", r"\bso as to\b",
    r"\bto (?:ensure|protect|enable|facilitate|safeguard|guarantee)\b",
    r"\bnecessary for\b", r"\bobjective[s]?\b", r"\bseek(?:s|ing)?\s+to\b",
    r"\bin order that\b", r"\bpurpose[s]?\s+of\b",
]
# deadlines/sequence -> temporal. Fix round item 6: a bare `\bwithin\b` cue
# matched "within the Union"/"within the scope" (spatial, not temporal) —
# `within` now counts ONLY alongside an actual time expression.
_TEMPORAL_CUES = [
    r"\bwithin\s+\d+\s*(?:hour|day|week|month|year)s?\b",
    r"\bwithin\s+(?:one|two|three|four|five|six|seven|eight|nine|ten)\s+"
    r"(?:hour|day|week|month|year)s?\b",
    r"\bwithin\s+(?:a|the)\s+(?:period|time\s+limit|deadline)\b",
    r"\bwithout undue delay\b", r"\bbefore\b", r"\bafter\b", r"\bprior to\b",
    r"\bno later than\b", r"\bat the latest\b", r"\bas soon as possible\b",
    r"\bonce\b", r"\bfollowing\b", r"\bduring\b", r"\bperiod[s]?\b",
    r"\bdeadline[s]?\b", r"\bsubsequently\b", r"\bat the time of\b",
    r"\bby\s+\d\b",
]
# containment/definitions/"referred to in paragraph" -> structural. Fix
# round item 6: a bare `\bmeans\b` cue matched "automated means"/"by other
# means" (the noun "means", not a definition) — `means` now counts ONLY in
# definitional form. "means any/a/an/the" alone MISSED
# 6 real GDPR Art. 4 definitions whose own phrasing has no article after
# "means" at all ("'main establishment' means:", "'cross-border processing'
# means either:") — keyed instead on a PRECEDING closing quote (<E2><80><99>
# or a straight ') within 30 characters of "means" (covers a short
# qualifier between the quoted term and "means", e.g. "'consent' OF THE
# DATA SUBJECT means"). Verified against the real GDPR Art. 4 text: 26 of
# 26 definitional uses fire; all 4 non-definitional uses ("automated
# means", "the purposes and means", twice) stay excluded.
_STRUCTURAL_CUES = [
    r"\bpart of\b", r"\bconsists? of\b", r"\bconsisting of\b",
    r"\bmeans\s+(?:any|a|an|the)\b",
    # A BARE apostrophe (a possessive, "the data
    # subject's rights", "the processor's means") is NOT a quoted term —
    # require an OPENING quote mark BEFORE the closing one, within 40
    # characters, so a genuine quoted-term pair ('consent'/'personal
    # data') is what fires, never a stray possessive apostrophe.
    "[‘']" r"[^‘’']{1,40}[’']" r"[^’']{0,30}means\b",
    r"\breferred to in paragraph\b", r"\breferred\s+to\s+in\b",
    r"\bcomprise[sd]?\b", r"\bcomprising\b", r"\bis composed of\b",
    r"\bcomposed of\b", r"\binclude[sd]?\b", r"\bcategor(?:y|ies|ised|ized)\b",
    r"\bdefinition[s]?\b", r"\bpursuant to\b", r"\bin accordance with\b",
    r"\bChapter\s+[IVXLCDM]+\b", r"\bparagraph\s+\d+\b", r"\bAnnex\b",
    r"\bset out in\b",
]
# relational entity/obligation vocabulary — counted only when NOTHING else fires
_RELATIONAL_CUES = [
    r"\bcontroller[s]?\b", r"\bprocessor[s]?\b", r"\bdata\s+subject[s]?\b",
    r"\bthird\s+part(?:y|ies)\b", r"\bsupervisory\s+authorit(?:y|ies)\b",
    r"\bjoint\s+controller[s]?\b", r"\brepresentative[s]?\b",
    r"\brecipient[s]?\b", r"\bnatural\s+person[s]?\b",
    r"\bright\s+to\b", r"\bobligation[s]?\b", r"\bbetween\b",
]

#: dimension -> list of compiled, case-insensitive patterns. `relational`'s
#: own table is checked last and only counted on the all-others-silent path
#: (see :func:`clause_cue_contributions`'s own docstring/module docstring).
CUE_TABLE: "dict[str, list[re.Pattern]]" = {
    "causal": [re.compile(p, re.IGNORECASE) for p in _CAUSAL_CUES],
    "intentional": [re.compile(p, re.IGNORECASE) for p in _INTENTIONAL_CUES],
    "temporal": [re.compile(p, re.IGNORECASE) for p in _TEMPORAL_CUES],
    "structural": [re.compile(p, re.IGNORECASE) for p in _STRUCTURAL_CUES],
    "relational": [re.compile(p, re.IGNORECASE) for p in _RELATIONAL_CUES],
}

#: "Article 22", "Article 6(1)", "Articles 15 and 16", "Articles 9 or 10",
#: "Articles 15 to 20", "Article 1(1)(b)" style cross-references — a
#: generic entry-id citation surface. TWO top-level alternatives, in a
#: fixed order (plural tried first): the PLURAL form ("Articles") gets
#: the full connector set INCLUDING "to"-ranges; the SINGULAR form
#: ("Article") gets only ","/"and"/"or" lists, NEVER a "to"-range (fix
#: "Article 12 to 30" is NOT a range at all; GDPR's own
#: drafting convention ranges only ever use the plural "Articles N to
#: M"). Each number may be followed by ANY NUMBER of trailing bracketed
#: groups ("(1)", "(1)(b)", ...), alphanumeric, consumed before the
#: external-instrument anchor check runs. A "to"-range whose right-hand
#: number is immediately followed by a TIME-DURATION unit ("Articles 12
#: to 30 days") is not a citation boundary at all — the negative lookahead
#: stops the span before that connector.
_TRAILING_GROUPS = r"(?:\s*\(\s*[0-9A-Za-z]{1,4}\s*\))*"
ARTICLE_REF_RE = re.compile(
    r"\bArticles\s+\d{1,3}\b" + _TRAILING_GROUPS +
    r"(?:\s*(?:,|and|or|to)\s*\d{1,3}\b" + _TRAILING_GROUPS +
    r"(?!\s*(?:day|days|week|weeks|month|months|year|years|hour|hours)\b))*"
    r"|"
    r"\bArticle\s+\d{1,3}\b" + _TRAILING_GROUPS +
    r"(?:\s*(?:,|and|or)\s*\d{1,3}\b" + _TRAILING_GROUPS +
    r"(?!\s*(?:day|days|week|weeks|month|months|year|years|hour|hours)\b))*",
    re.IGNORECASE)
#: A citation of ANOTHER
#: instrument ("Article 8 of Regulation (EU) No 182/2011", "Article
#: 25(6) of Directive 95/46/EC", "Articles 12 to 15 of that Directive",
#: "Article 4 of Council Regulation (EC) No 1/2003", "Article 6 of
#: Commission Implementing Regulation (EU) 2021/1372", "Article 7 of the
#: European Parliament Regulation (EU) 2019/817", "Article 16 TFEU"/
#: "TEU", "Article 16 of the Charter") names an article NUMBER that is
#: NOT a GDPR article at all. Anchored (``.match``, not ``.search`` over
#: a window) DIRECTLY at the end of an :data:`ARTICLE_REF_RE` match, so
#: an intervening relative clause ("Article 6(1), WHICH IS SUBJECT TO THE
#: RULES OF Regulation (EU) No 182/2011") does NOT exclude the citation.
#: "of this/the Regulation" (bare, no further qualifying word before
#: "Regulation") are deliberately NOT matched here — GDPR is ITSELF
#: "this Regulation"/"the Regulation"; that is the HOST instrument, kept
#: internal. The qualifying-word slot before "Regulation" now accepts
#: MULTIPLE words ("Commission Implementing", "European
#: Parliament" — a `*` repetition, not only one `?` word), each
#: individually excluding "this"/"the" via its own negative lookahead, so
#: "of this Regulation" still falls through to no match (stays internal)
#: while "of Commission Implementing Regulation..." matches (external) —
#: UNLESS :func:`cross_reference_targets`'s own ``host_instrument_number``
#: override applies (see below): "Article 45 of Regulation (EU)
#: 2016/679" names GDPR's OWN instrument number, so it is the HOST, not
#: an external instrument, even though the bare qualifier pattern here
#: alone would flag it as one.
_EXTERNAL_INSTRUMENT_RE = re.compile(
    r"\A\s*of\s+(?:the\s+|that\s+|this\s+)?Directive\b|"
    r"\A\s*of\s+(?:the\s+)?Treaty\b|"
    r"\A\s*of\s+(?:the\s+)?Charter\b|"
    r"\A\s*(?:TFEU|TEU)\b|"
    r"\A\s*of\s+(?:(?:(?!this\b|the\b)[A-Za-z]+\s+)*)Regulation\b",
    re.IGNORECASE)
#: Same external-instrument phrase, WITHOUT the anchor — used only to
#: check whether an external instrument was named EARLIER in the
#: sentence (the "Article N thereof" back-reference case below), where
#: "anywhere before this citation" is exactly what is wanted, unlike the
#: anchored, directly-following check above.
_EXTERNAL_INSTRUMENT_ANYWHERE_RE = re.compile(
    r"\bof\s+(?:the\s+|that\s+|this\s+)?Directive\b|"
    r"\bof\s+(?:the\s+)?Treaty\b|"
    r"\bof\s+(?:the\s+)?Charter\b|"
    r"\b(?:TFEU|TEU)\b|"
    r"\bof\s+(?:(?:(?!this\b|the\b)[A-Za-z]+\s+)*)Regulation\b",
    re.IGNORECASE)


def _host_instrument_re(host_instrument_number: str) -> "re.Pattern":
    """``"Regulation (EU) 2016/679"`` NAMES the HOST
    instrument (GDPR's own number) — a citation of the form "Article 45
    of Regulation (EU) 2016/679" must resolve to ``[45]``, INTERNAL, not
    be excluded by :data:`_EXTERNAL_INSTRUMENT_RE`'s bare "of ...
    Regulation" match. ``host_instrument_number`` is the host's own
    number (e.g. ``"2016/679"``), taken from the resolution profile or
    document metadata — never hardcoded in this module, so a consumer
    checking a DIFFERENT host instrument gets the correct self-reference
    behaviour for ITS OWN number.

    a comma directly before "of" ("Chapter III, Section
    2, of Regulation (EU) <num>", "Article 6(1), point (a), of
    Regulation (EU) <num>") is now tolerated — the comma is ordinary
    EU-drafting punctuation between a nested pinpoint and its
    instrument, not a signal that breaks the self-naming match.
    """
    return re.compile(
        r"\A[\s\xa0]*,?[\s\xa0]*of\s+(?:(?:(?!this\b|the\b)[A-Za-z]+\s+)*)Regulation\s*"
        r"(?:\(\s*EU\s*\)\s*)?(?:No\s*)?" + re.escape(host_instrument_number) + r"\b",
        re.IGNORECASE)


def _flexible_name_pattern(name: str) -> str:
    """a whitespace/NBSP-tolerant regex PATTERN (not yet
    compiled) for an exact instrument name — splits on any run of
    ordinary/NBSP whitespace and rejoins with :data:`_WS`, so
    ``host_instrument_name`` (always given with ordinary spaces) still
    matches a drafting source's own NBSP-separated surface form
    ("Regulation\\xa0(EU)\\xa02024/1689")."""
    # a trailing WORD
    # BOUNDARY is mandatory — without it, "2016/679" (the host's own
    # number, as the LAST escaped token) matches as a bare PREFIX of
    # "2016/6790", a DIFFERENT instrument's number, with nothing after
    # it to reject the extra trailing digit. The contract's own rule
    # ("2016/6790" != "2016/679") applies to the flexible NAME match
    # exactly as it already does to the separate BY-NUMBER check below.
    tokens = [t for t in re.split(r"[\s\xa0]+", name.strip()) if t]
    return r"(?<!\w)" + _WS.join(re.escape(t) for t in tokens) + r"(?!\w)"


def _consume_trailing_host_name(text: str, end: int,
                                 host_instrument_name: "Optional[str]") -> int:
    """a chain whose own pinpoint pattern does NOT itself
    wrap "<chain> of <host name>" (e.g. the UK "Chapter N of Part M"
    outer-first pattern) must still CONSUME a bare host naming left over
    right after it ("Chapter 2 of Part 2 of the Data Protection Act
    2018") — the host naming is R1's OWN bare self-reference, not a
    second, separate EXTERNAL mention. Returns ``end`` unchanged when no
    such trailing host naming immediately follows (optionally after a
    comma and "of"/"to"/"of the"/"to the", whitespace/NBSP-tolerant)."""
    if not host_instrument_name:
        return end
    m = re.match(r"[\s\xa0]*,?[\s\xa0]*(?:of|to)(?:" + _WS + r"the)?" + _WS,
                 text[end:], re.IGNORECASE)
    if not m:
        return end
    rest = text[end + m.end():]
    nm = re.match(_flexible_name_pattern(host_instrument_name), rest, re.IGNORECASE)
    if not nm:
        return end
    return end + m.end() + nm.end()


#: "Article 8 of Regulation (EU) No 182/2011, in conjunction with Article 5
#: thereof" — the SECOND citation has no "of Regulation/Directive" of its
#: own; "thereof" refers back to the instrument named earlier in the SAME
#: sentence. Excluded too when an external-instrument mention already
#: precedes it and this match is immediately followed by "thereof".
_THEREOF_RE = re.compile(r"^\s*,?\s*thereof\b", re.IGNORECASE)
_THEREOF_WINDOW = 20
#: A "to"-range ("Articles 15 to 20") is expanded inclusively; capped so a
#: malformed or adversarial span (e.g. "Articles 1 to 999") cannot blow up
#: the target set unboundedly.
_MAX_RANGE_SPAN = 50
_ARTICLE_LIST_TOKEN_RE = re.compile(
    r"(to|and|or|,)?\s*(\d{1,3})\b" + _TRAILING_GROUPS, re.IGNORECASE)


def _dedup_hit_count(matches: list) -> int:
    """Fix round item 6: de-duplicate OVERLAPPING match spans so one
    surface phrase counts once, never once per overlapping pattern (e.g.
    "referred to in paragraph" and "referred to in" both matching the same
    text previously double-counted it). ``matches`` is a list of ``(start,
    end)`` tuples from one or more patterns over the SAME text. Counts
    maximal merged intervals, sorted by start."""
    if not matches:
        return 0
    spans = sorted(matches)
    count = 0
    cur_end = -1
    for start, end in spans:
        if start >= cur_end:
            count += 1
            cur_end = end
        elif end > cur_end:
            cur_end = end
    return count


def count_cue_hits(text: str, dimension: str) -> int:
    """De-duplicated hit count (fix round item 6 — see
    :func:`_dedup_hit_count`) for ``dimension``'s own closed cue table over
    ``text``: every pattern's matches are pooled, then overlapping spans
    (across patterns, or repeated by one pattern) are merged before
    counting. Raises ``KeyError`` for an unknown dimension name (fail
    closed — this module never silently treats an unrecognised dimension
    as zero)."""
    spans = []
    for pat in CUE_TABLE[dimension]:
        spans.extend((m.start(), m.end()) for m in pat.finditer(text))
    return _dedup_hit_count(spans)


def _expand_article_span(span_text: str) -> list:
    """Every article number an :data:`ARTICLE_REF_RE` match's own text
    names — singular, listed (``,``/``and``), or ranged (``to``,
    inclusive of both ends, capped at :data:`_MAX_RANGE_SPAN`)."""
    nums = []
    prev = None
    for connector, numstr in _ARTICLE_LIST_TOKEN_RE.findall(span_text):
        n = int(numstr)
        if connector.lower() == "to" and prev is not None and 0 < n - prev <= _MAX_RANGE_SPAN:
            nums.extend(range(prev + 1, n))
        nums.append(n)
        prev = n
    return nums


def _expand_generic_list(span_text: str) -> list:
    """B3 — like :func:`_expand_article_span`, but for
    sections/paragraphs/§§ plural forms: every member number (as a
    STRING, carrying any trailing letter suffix — "6a" — and its own
    sub-pinpoint suffix), singular, listed (``,``/``and``/``or``/
    German ``und``/``oder``), or ranged (``to``/German ``bis``,
    inclusive, capped at :data:`_MAX_RANGE_SPAN`; a range whose
    endpoint carries a letter suffix is NOT expanded — only the two
    WRITTEN endpoints become members)."""
    members = []
    prev_n = None
    for connector, numstr, suffix, subs in _GENERIC_LIST_TOKEN_RE.findall(span_text):
        n = int(numstr)
        subs = subs.replace(" ", "")
        if connector.lower() in _RANGE_CONNECTOR_WORDS and prev_n is not None \
                and not suffix and 0 < n - prev_n <= _MAX_RANGE_SPAN:
            members.extend(str(k) for k in range(prev_n + 1, n))
        members.append(f"{numstr}{suffix}{subs}")
        prev_n = n if not suffix else None
    return members


def _section_plural_range_groups(m: "re.Match", suffix_end: int,
                                  host_section_numbers: "Optional[set]") -> "Optional[list]":
    """items 3 & 4 : every
    WRITTEN token of a plural section match — a plain list member
    ("45"), or a RANGE token ("to 6510"/"through 6510", fully EXPANDED
    to every IMPLIED member, not only its own two endpoints) — is
    classified member-by-member and grouped into contiguous same
    -status runs. A run that IS its token's one-and-only run, or that
    token's LAST run when the token holds more than one, keeps that
    token's own WRITTEN literal span (mirrors :func:`_section_plural_
    member_spans`'s own per-token spans). A range with MORE than one
    in-file/out-of-file switch — any number of them — gets every
    contiguous run, not just the first two. One limit remains: an
    INTERIOR run with no written anchor of
    its own (a second-or-later flip strictly INSIDE one range token,
    with no WRITTEN number of its own anywhere near it) has no textual
    span to point at — it is reported at a synthetic ZERO-WIDTH
    position, its token's own start, carrying every member that run
    holds in its own ``targets``/``external_target`` either way (no
    member of it is ever DROPPED, only its ``literal`` span is
    synthetic). See spec/SPEC.md §8a.1, KNOWN LIMITS.

    Returns ``None`` (the existing single-reference path handles it
    unchanged) when ``host_section_numbers`` is ``None``, or every
    member this match actually expands to — across EVERY token, range
    or plain — shares ONE status (nothing to split)."""
    if host_section_numbers is None:
        return None
    tokens = list(_GENERIC_LIST_TOKEN_RE.finditer(m.group(0)))
    spans = _section_plural_member_spans(m, suffix_end)
    runs = []
    #: the trailing run not yet emitted — ``(status, nums, start, end)``.
    #: Carried forward across a token boundary ONLY while the NEXT
    #: token is itself a RANGE whose own leading run shares the
    #: carry's status (the ONE cross-token merge the legacy two
    #: -endpoint-only function already relied on — M3 —
    #: generalised here to any number of tokens): the carry then keeps
    #: its OWN original span, never extended to cover the range
    #: token's text.
    carry = None
    prev_n = None
    for tok, (numstr, t_start, t_end) in zip(tokens, spans):
        connector = (tok.group(1) or "").strip().lower()
        n = int(tok.group(2))
        suffix = tok.group(3)
        subs = tok.group(4).replace(" ", "")
        last_member = f"{tok.group(2)}{suffix}{subs}"
        is_range_token = bool(connector in _RANGE_CONNECTOR_WORDS and prev_n is not None
                               and not suffix and 0 < n - prev_n <= _MAX_RANGE_SPAN)
        if is_range_token:
            members = [str(k) for k in range(prev_n + 1, n)] + [last_member]
        else:
            members = [last_member]
        statuses = [re.sub(r"\([^()]*\)", "", mem) in host_section_numbers for mem in members]
        i = 0
        tok_runs = []
        while i < len(members):
            j = i
            while j + 1 < len(members) and statuses[j + 1] == statuses[i]:
                j += 1
            tok_runs.append([statuses[i], members[i:j + 1], t_start, t_end])
            i = j + 1
        for run in tok_runs[:-1]:
            run[2] = run[3] = t_start  # interior run: synthetic zero-width span
        if carry is not None and is_range_token and carry[0] == tok_runs[0][0]:
            tok_runs[0] = [carry[0], carry[1] + tok_runs[0][1], carry[2], carry[3]]
        elif carry is not None:
            runs.append(tuple(carry))
        for run in tok_runs[:-1]:
            runs.append(tuple(run))
        carry = tok_runs[-1]
        prev_n = n if not suffix else None
    if carry is not None:
        runs.append(tuple(carry))
    if len({r[0] for r in runs}) <= 1:
        return None
    return runs


def _format_pinpoint_range(prefix: str, numbers: list) -> str:
    """one bare pinpoint (a single-member group), or
    an inclusive "<prefix> A to <prefix> B" range string (a multi
    -member group with no written span of its own to carry a
    ``targets`` list — EXTERNAL carries no ``targets`` either way,
    R7)."""
    if len(numbers) == 1:
        return f"{prefix} {numbers[0]}"
    return f"{prefix} {numbers[0]} to {prefix} {numbers[-1]}"


def _section_plural_member_spans(m: "re.Match", suffix_end: int) -> list:
    """every
    WRITTEN member of a :data:`_SECTION_PLURAL_RE` match, as its own
    ``(number_string, absolute_start, absolute_end)`` span — the FIRST
    member's span starts at the match's own start (covering the
    "sections" keyword); every later LISTED member's span starts at its
    own connector token (mirrors :func:`_chain_member_spans`'s EU
    -chain technique). A "to"-RANGE's own IMPLIED intermediate members
    have no span of their own; only the two WRITTEN endpoints become
    members here (same documented, narrower scope as the EU chain
    case). The LAST member's span is extended to ``suffix_end``
    (covering the shared "of this title" suffix, which trails the
    whole list, not any one member)."""
    spans = []
    for i, tm in enumerate(_GENERIC_LIST_TOKEN_RE.finditer(m.group(0))):
        numstr, suffix, subs = tm.group(2), tm.group(3), tm.group(4)
        abs_start = m.start() if i == 0 else m.start() + tm.start()
        abs_end = m.start() + tm.end()
        spans.append((f"{numstr}{suffix}{subs.replace(' ', '')}", abs_start, abs_end))
    if spans:
        last_num, last_start, _ = spans[-1]
        spans[-1] = (last_num, last_start, suffix_end)
    return spans


def cross_reference_targets(text: str, self_article_number: "Optional[int]" = None,
                             host_instrument_number: "Optional[str]" = None) -> list:
    """Distinct target article numbers ``text`` explicitly cites
    (``Article N``/``Article N(M)``, or a plural/listed/ranged form —
    ``Articles 15, 16 and 17``, ``Articles 15 to 20``), excluding a
    self-reference and excluding any citation that is itself to ANOTHER
    instrument (fix round item 6 — see :data:`_EXTERNAL_INSTRUMENT_RE`).
    ``host_instrument_number`` (e.g. ``"2016/679"``
    for GDPR, from the resolution profile or document metadata) names the
    HOST instrument's own number: "Article 45 of Regulation (EU)
    2016/679" is then treated as INTERNAL (``[45]``), not excluded, even
    though the bare "of ... Regulation" pattern alone would flag it as an
    external-instrument citation — because it names the SAME instrument
    the text is itself part of. Sorted ascending ints."""
    host_re = _host_instrument_re(host_instrument_number) if host_instrument_number else None
    targets = set()
    for m in ARTICLE_REF_RE.finditer(text):
        tail = text[m.end():]
        if host_re is not None and host_re.match(tail):
            pass  # names the HOST instrument's own number -> stays internal
        elif _EXTERNAL_INSTRUMENT_RE.match(tail):
            continue
        after = text[m.end(): m.end() + _THEREOF_WINDOW]
        before = text[: m.start()]
        if _THEREOF_RE.search(after) and _EXTERNAL_INSTRUMENT_ANYWHERE_RE.search(before):
            continue
        for n in _expand_article_span(m.group(0)):
            if self_article_number is not None and n == self_article_number:
                continue
            targets.add(n)
    return sorted(targets)


#: §8a.1's own dispatch default — ``"article-v1"`` NEVER changes the
#: pre-existing call path of :func:`cross_reference_links` /
#: :func:`clause_cue_contributions` (the profile field
#: must actually REACH these two entry points, not sit inert next to
#: them). Mirrors ``DEFAULT_RELATIONAL_SUPPRESSION_SCALE``'s own role —
#: a plain kwarg default, threaded by the caller from the resolved
#: profile exactly the same way.
DEFAULT_XREF_RESOLVER = "article-v1"


def _xref_count_and_objects(
        text: str, self_article_number: "Optional[int]" = None,
        host_instrument_number: "Optional[str]" = None,
        xref_resolver: str = DEFAULT_XREF_RESOLVER,
        enclosing_unit: "Optional[str]" = None, numbering_family: str = "eu",
        host_instrument_name: "Optional[str]" = None,
        whole_host_unit: "Optional[str]" = None, preceding_text: str = "",
        enclosing_units: "Optional[dict]" = None, host_title_instrument: "Optional[str]" = None,
        host_section_numbers: "Optional[set]" = None,
) -> "tuple[int, list]":
    """The ONE dispatch point both :func:`cross_reference_links` and
    :func:`clause_cue_contributions` go through . ``"article-v1"``
    (the default) calls :func:`cross_reference_targets` EXACTLY as
    before — BYTE-IDENTICAL count and link objects for every existing
    caller/vector. ``"shared-v2"`` calls :func:`resolve_references`
    instead and derives the SAME two things (a structural count, and a
    list of link-object strings) from its richer output: one object per
    INTERNAL target pinpoint (``"Article 7(1), point (b)"``), and one
    object per EXTERNAL reference, ``"<instrument>|<pinpoint>"`` — the
    PARSED ``external_target`` field (R2/R7's "(instrument, target
    provision)" requirement) when one was parsed, else the literal
    citation text as a fallback (e.g.
    ``"Directive 2011/83/EU|Article 2, point (7)"`` when the pinpoint
    parsed cleanly). ``shared-v2`` counts DISTINCT targets/instruments
    only — "Article 6 and Article 6" (the SAME
    target cited twice) contributes `+1` structural and ONE link, not
    two, matching this module's own docstring claim ("PER DISTINCT
    TARGET"). Returns ``(structural_count, [object_string, ...])``.

    Raises ``ValueError`` for an unrecognised ``xref_resolver`` value —
    dispatch fails CLOSED, never silently falling
    back to ``article-v1`` behaviour on a typo'd profile value.
    """
    if xref_resolver not in (DEFAULT_XREF_RESOLVER, "shared-v2"):
        raise ValueError(
            f"_xref_count_and_objects() xref_resolver must be 'article-v1' or 'shared-v2', "
            f"got {xref_resolver!r}")
    if xref_resolver == "shared-v2":
        refs = resolve_references(
            text, enclosing_unit=enclosing_unit, numbering_family=numbering_family,
            host_instrument_name=host_instrument_name,
            host_instrument_number=host_instrument_number,
            whole_host_unit=whole_host_unit, preceding_text=preceding_text,
            enclosing_units=enclosing_units, host_title_instrument=host_title_instrument,
            host_section_numbers=host_section_numbers,
        )
        distinct_targets = set()
        distinct_external = set()
        objects = []
        for ref in refs:
            if ref["kind"] == "INTERNAL":
                for t in ref["targets"]:
                    if t["pinpoint"] not in distinct_targets:
                        distinct_targets.add(t["pinpoint"])
                        objects.append(t["pinpoint"])
            else:
                key = (ref["external_instrument"], ref.get("external_target") or ref["literal"])
                if key not in distinct_external:
                    distinct_external.add(key)
                    objects.append(f"{key[0]}|{key[1]}")
        return len(distinct_targets) + len(distinct_external), objects
    targets = cross_reference_targets(text, self_article_number, host_instrument_number)
    return len(targets), [f"Article {n}" for n in targets]


def cross_reference_links(
    text: str, source_id: str, self_article_number: "Optional[int]" = None,
    host_instrument_number: "Optional[str]" = None,
    xref_resolver: str = DEFAULT_XREF_RESOLVER,
    enclosing_unit: "Optional[str]" = None, numbering_family: str = "eu",
    host_instrument_name: "Optional[str]" = None,
    whole_host_unit: "Optional[str]" = None, preceding_text: str = "",
    enclosing_units: "Optional[dict]" = None, host_title_instrument: "Optional[str]" = None,
    host_section_numbers: "Optional[set]" = None,
) -> list:
    """Every cross-reference in ``text`` as an explicit §11 triple-shaped
    link: ``{s: source_id, p: "cross_references", o: "Article <n>",
    dimension: "structural", weight: 1.0, provenance: {...}}`` — one per
    DISTINCT target (see :func:`cross_reference_targets`). This is the
    "explicit link between entries" ADR 0007 calls for,
    separate from (in addition to) the `+1 structural` raw contribution
    :func:`clause_cue_contributions` also derives from the same citations.

    ``host_instrument_number`` is forwarded verbatim
    to :func:`cross_reference_targets` — CALLER-SUPPLIED DOCUMENT
    METADATA, never a resolution-profile field (a profile is shared
    across documents; the host instrument's own number is a property of
    THIS document alone).

    §8a.1 adds a SECOND resolver, selected by the ``xref_resolver``
    keyword (``"article-v1"`` default, unchanged above; ``"shared-v2"``
    dispatches instead to :func:`resolve_references` via
    :func:`_xref_count_and_objects`, ``o`` then one entry per INTERNAL
    target pinpoint or EXTERNAL reference, not only ``"Article <n>"``).
    Every ``shared-v2``-only keyword below is forwarded verbatim, the
    same CALLER-SUPPLIED DOCUMENT METADATA rule as ``host_instrument_number``
    above. ``xref_resolver`` IS threaded from the resolved resolution
    profile (§16's own ``xref_resolver`` field), by the caller, the same
    way ``relational_suppression_scale`` already is.
    """
    _, objects = _xref_count_and_objects(
        text, self_article_number, host_instrument_number, xref_resolver,
        enclosing_unit, numbering_family, host_instrument_name, whole_host_unit, preceding_text,
        enclosing_units, host_title_instrument, host_section_numbers)
    out = []
    for o in objects:
        out.append({
            "s": source_id,
            "p": "cross_references",
            "o": o,
            "dimension": "structural",
            "weight": 1.0,
            "provenance": {"layer": "clause_cues", "source_text": text},
        })
    return out


#: §8a's own relational-suppression scale — replaces the all-or-nothing
#: relational gate with down-weighting; this constant's own VALUE and
#: FORMULA are a design choice. Default 1, positive, finite —
#: a resolution-profile field, ``relational_suppression_scale`` (§16).
DEFAULT_RELATIONAL_SUPPRESSION_SCALE = 1


def relational_effective(relational_count: "int | float", n_other: "int | float",
                          scale: "int | float" = DEFAULT_RELATIONAL_SUPPRESSION_SCALE) -> float:
    """§8a's relational contribution, DOWN-WEIGHTED by how many OTHER
    (non-relational) de-duplicated cue hits the same clause carries —
    ``relational_count * scale / (scale + n_other)`` — the SAME ``x/(x+s)``
    monotone family ``five_d_nd.depth``'s own nesting signal already uses
    (a design choice there too; see that
    module's own docstring). Quantised the SAME way §11's point formula
    is: one division, rounded ONCE to 6 decimal places at this single
    materialisation point — never left unrounded, never rounded twice.

    Properties (stated and tested, not merely claimed):

    * ``n_other == 0`` -> no change at all: ``relational_count * scale /
      scale == relational_count`` exactly (the formula's own identity at
      zero, not a special-cased branch).
    * MONOTONE NON-INCREASING in ``n_other`` — adding one more
      non-relational cue hit never INCREASES the effective relational
      value, for any fixed ``relational_count``/``scale``.
    * at the DEFAULT scale (``1``), one extra non-relational cue AT MOST
      HALVES the value — GDPR Art. 65(5)'s own sentence (raw relational
      count 5, zero other cues) is unaffected (still `5`); adding ONE
      causal cue ("Where applicable, ...") takes it to `5 * 1/(1+1) =
      2.5`, a down-weighting, never the OLD all-or-nothing gate's jump
      straight to `0`.

    Raises ``ValueError`` if ``scale`` is not a positive finite number,
    or either count is negative (fail closed — mirrors
    ``five_d_nd.point.point_from_contributions``'s own validation style).
    """
    if isinstance(scale, bool) or not isinstance(scale, (int, float)) \
            or not math.isfinite(scale) or scale <= 0:
        raise ValueError(f"relational_effective() scale must be a positive finite number, got {scale!r}")
    for name, value in (("relational_count", relational_count), ("n_other", n_other)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) \
                or not math.isfinite(value) or value < 0:
            raise ValueError(f"relational_effective() {name} must be a non-negative finite number, got {value!r}")
    return round(relational_count * scale / (scale + n_other), 6)


def clause_cue_contributions(
        text: str, self_article_number: "Optional[int]" = None,
        relational_suppression_scale: "int | float" = DEFAULT_RELATIONAL_SUPPRESSION_SCALE,
        host_instrument_number: "Optional[str]" = None,
        xref_resolver: str = DEFAULT_XREF_RESOLVER,
        enclosing_unit: "Optional[str]" = None, numbering_family: str = "eu",
        host_instrument_name: "Optional[str]" = None,
        whole_host_unit: "Optional[str]" = None, preceding_text: str = "",
        enclosing_units: "Optional[dict]" = None, host_title_instrument: "Optional[str]" = None,
        host_section_numbers: "Optional[set]" = None,
) -> dict:
    """The clause-cue layer's OWN raw contribution counts for ``text`` —
    spec/SPEC.md §8a. Every matching cue in `causal`/`intentional`/
    `temporal`/`structural` adds `+1` to its own dimension's count
    (a clause may hit several); `+1 structural` is ALSO added per distinct
    cross-reference target (:func:`cross_reference_targets`). `relational`
    is ALWAYS computed from its own cue table, then DOWN-WEIGHTED via
    :func:`relational_effective` by how many of the other four dimensions
    fired (decided 2026-10-03 — REPLACES the earlier all-or-nothing gate;
    see that function's own docstring and the module docstring's own
    "`relational` is DOWN-WEIGHTED" paragraph). Never raises on a
    cue-free clause (returns all-zero); raises ``ValueError`` if ``text``
    is not a string.

    ``host_instrument_number`` is forwarded to
    :func:`cross_reference_targets` — CALLER-SUPPLIED DOCUMENT METADATA,
    never a resolution-profile field.

    §8a.1 adds ``xref_resolver``: under the default ``"article-v1"``,
    the `+1 structural` cross-reference count above is byte-identical to
    every pre-existing call; under ``"shared-v2"`` the SAME count is
    derived from :func:`resolve_references` instead, so the §16 profile
    field reaches this count, not only :func:`cross_reference_links`.
    ``xref_resolver`` IS a resolution-profile field (§16), threaded by
    the CALLER from the resolved profile — this function itself never
    reads a profile document. Every other ``shared-v2``-only keyword
    (``enclosing_unit``, ``numbering_family``, ``host_instrument_name``,
    ``whole_host_unit``, ``preceding_text``) is forwarded to
    :func:`_xref_count_and_objects`, the same CALLER-SUPPLIED DOCUMENT
    METADATA rule as ``host_instrument_number`` above.
    """
    if not isinstance(text, str):
        raise ValueError("clause_cue_contributions() requires a string")
    out = {d: 0 for d in DIMENSIONS}
    for dim in ("causal", "intentional", "temporal", "structural"):
        out[dim] = count_cue_hits(text, dim)
    xref_count, _ = _xref_count_and_objects(
        text, self_article_number, host_instrument_number, xref_resolver,
        enclosing_unit, numbering_family, host_instrument_name, whole_host_unit, preceding_text,
        enclosing_units, host_title_instrument, host_section_numbers)
    out["structural"] += xref_count
    relational_count = count_cue_hits(text, "relational")
    n_other = out["causal"] + out["intentional"] + out["temporal"] + out["structural"]
    out["relational"] = relational_effective(relational_count, n_other, relational_suppression_scale)
    return out


def combined_contributions(
        sentence: str, base_fact: "Optional[Mapping]" = None,
        self_article_number: "Optional[int]" = None,
        relational_suppression_scale: "int | float" = DEFAULT_RELATIONAL_SUPPRESSION_SCALE,
        host_instrument_number: "Optional[str]" = None,
        xref_resolver: str = DEFAULT_XREF_RESOLVER,
        enclosing_unit: "Optional[str]" = None, numbering_family: str = "eu",
        host_instrument_name: "Optional[str]" = None,
        whole_host_unit: "Optional[str]" = None, preceding_text: str = "",
        enclosing_units: "Optional[dict]" = None, host_title_instrument: "Optional[str]" = None,
        host_section_numbers: "Optional[set]" = None,
) -> dict:
    """§8 (unchanged, D1) PLUS §8a (this module, D2), summed into ONE raw
    contribution mapping ready for the UNCHANGED
    ``five_d_nd.point.point_from_contributions`` formula (§11).

    ``base_fact`` is the result of the UNMODIFIED
    ``five_d_nd.assertoric.lower_assertion(sentence)`` (or ``None`` on one
    of its own abstention paths) — its ``dimension`` field, when present,
    contributes `+1` exactly as it always has, UNCHANGED, NEVER
    down-weighted (see the module docstring's own note on why §8's base
    contribution is deliberately NOT given the same treatment — §8 is
    frozen, loomground-factual-parity-critical; this function only sums
    its own unmodified output with §8a's, it does not re-grade it). The
    clause-cue raw counts (:func:`clause_cue_contributions`, itself
    already down-weighted on `relational`) are added on top, dimension by
    dimension. The result MAY exceed any single layer's own saturation on
    a dimension that both layers hit — that is intended: the point formula
    (§11) is the one place saturation is applied, not this function.

    ``host_instrument_number`` is forwarded to
    :func:`clause_cue_contributions` — CALLER-SUPPLIED DOCUMENT METADATA,
    never a resolution-profile field (a profile is shared across
    documents; the host instrument's own number is a property of THIS
    document alone). ``xref_resolver`` and every ``shared-v2``-only
    keyword are forwarded there too — see that function's own
    docstring.
    """
    raw = clause_cue_contributions(
        sentence, self_article_number, relational_suppression_scale, host_instrument_number,
        xref_resolver, enclosing_unit, numbering_family, host_instrument_name,
        whole_host_unit, preceding_text, enclosing_units, host_title_instrument,
        host_section_numbers)
    if isinstance(base_fact, Mapping):
        base_dimension = base_fact.get("dimension")
        if base_dimension in DIMENSIONS:
            raw[base_dimension] = raw.get(base_dimension, 0) + 1
    return raw


def clause_cue_point(sentence: str, base_fact: "Optional[Mapping]" = None,
                      saturation: Any = DEFAULT_CLAUSE_CUE_SATURATION,
                      self_article_number: "Optional[int]" = None,
                      relational_suppression_scale: "int | float" = DEFAULT_RELATIONAL_SUPPRESSION_SCALE,
                      host_instrument_number: "Optional[str]" = None,
                      xref_resolver: str = DEFAULT_XREF_RESOLVER,
                      enclosing_unit: "Optional[str]" = None, numbering_family: str = "eu",
                      host_instrument_name: "Optional[str]" = None,
                      whole_host_unit: "Optional[str]" = None, preceding_text: str = "",
                      enclosing_units: "Optional[dict]" = None,
                      host_title_instrument: "Optional[str]" = None,
                      host_section_numbers: "Optional[set]" = None,
                      ) -> dict:
    """Convenience: :func:`combined_contributions` run straight through the
    UNCHANGED §11 point formula (``five_d_nd.point.point_from_contributions``),
    with this layer's own default saturation/relational-suppression-scale
    unless a caller (or a resolution profile, via ``clause_cue_saturation``/
    ``relational_suppression_scale``/``xref_resolver``) overrides them.
    Imported lazily to avoid a module-load-time cycle with ``point.py``.

    ``host_instrument_number`` (e.g. ``"2016/679"``
    for GDPR) is CALLER-SUPPLIED DOCUMENT METADATA, forwarded to
    :func:`combined_contributions`/:func:`cross_reference_targets` —
    never a resolution-profile field, because it is a property of the
    one document being checked, not a tunable shared across documents.
    ``xref_resolver`` and every ``shared-v2``-only keyword are
    CALLER-SUPPLIED too, forwarded to :func:`combined_contributions` —
    see that function's own docstring.
    """
    from .point import point_from_contributions
    raw = combined_contributions(
        sentence, base_fact, self_article_number, relational_suppression_scale, host_instrument_number,
        xref_resolver, enclosing_unit, numbering_family, host_instrument_name,
        whole_host_unit, preceding_text, enclosing_units, host_title_instrument,
        host_section_numbers)
    return point_from_contributions(raw, saturation=saturation)


# ═══════════════════════════════════════════════════════════════════════
# The SHARED cross-reference resolver — spec/SPEC.md §8a.1,
# profile field ``xref_resolver: "shared-v2"``. Precondition of the
# signed 5D benchmark (benchmark protocol §8): fixing cross-reference
# resolution as ONE versioned 5d-nd change (spec text + conformance
# vectors + a new resolution-profile digest) applied identically to both
# arms. Replaces nothing — :func:`cross_reference_targets` /
# :func:`cross_reference_links` ("article-v1") stay exactly as they were,
# forever, for replay. This is the NEW entry point, selected by the
# resolution-profile field, never by silently changing the old one.
#
# Built against a hand-annotation contract covering rulings R1-R7, and
# scored against the shared xref gold's DEV half only, never held-out.
# No dev-gold literal appears in any conformance vector; see
# ``conformance/vectors/clause-cues/xref-v2-*.json`` for each rule's own
# worked, hand-built example.
# ═══════════════════════════════════════════════════════════════════════

#: Every reference kind this resolver emits.
REFERENCE_KINDS = ("INTERNAL", "EXTERNAL")

_WS = r"[\s\xa0]+"          # NBSP rule: keyword<->number gap
_NUM = r"\d{1,4}"
_LETTER_PIN = r"[A-Za-z]"
_SUBPIN = r"(?:\(\s*[0-9A-Za-z]{1,4}\s*\))"  # "(1)", "(b)", "(iii)" ...
_SUBPINS = rf"(?:{_SUBPIN})*"

# ── external-instrument NAME surfaces — "named as the text names it", no
# pinpoint, no gloss (R7). Each is tried, in this order, against the text
# immediately following a pinpoint chain's own "of"/trailing anchor; the
# FULL matched instrument-name text is what :func:`_resolve_v2` records,
# verbatim, never normalised, never glossed.
_EXT_EU_REGULATION = (
    r"(?:(?:Commission\s+Implementing|Commission\s+Delegated|Commission|"
    r"Council|European\s+Parliament)" + _WS + r")*"
    r"Regulation" + _WS + r"\(\s*E[UC]\s*\)" + _WS + r"(?:No" + _WS + r")?"
    r"\d+/\d{2,4}"
)
_EXT_EU_DIRECTIVE = r"Directive" + _WS + r"(?:\(\s*EU\s*\)" + _WS + r")?\d{2,4}/\d+(?:/E[UC]{1,2})?"
#: "Recommendation YYYY/NNN/EC" — the same EU-act
#: numbering shape as Directive, just a different instrument-type word.
_EXT_EU_RECOMMENDATION = r"Recommendation" + _WS + r"(?:\(\s*EU\s*\)" + _WS + r")?\d{2,4}/\d+(?:/E[UC]{1,2})?"
#: the SPELLED-OUT treaty names ("the Treaty on the
#: Functioning of the European Union", "the Treaty on European Union")
#: are EXTERNAL exactly like their own abbreviations.
_EXT_TFEU_TEU_CHARTER = (
    r"TFEU\b|TEU\b|Charter(?:" + _WS + r"of" + _WS + r"Fundamental" + _WS + r"Rights"
    r"(?:" + _WS + r"of" + _WS + r"the" + _WS + r"European" + _WS + r"Union)?)?|"
    r"Treaty" + _WS + r"on" + _WS + r"the" + _WS + r"Functioning" + _WS + r"of" + _WS +
    r"the" + _WS + r"European" + _WS + r"Union|"
    r"Treaty" + _WS + r"on" + _WS + r"European" + _WS + r"Union"
)
#: X2 ?(Convention|
#: Protocol|Accord)" alternative from B4, is REMOVED here:
#: it fired on every bare occurrence of these generic instrument-TYPE
#: words ANYWHERE in a document — "Transmission Control Protocol/
#: Internet Protocol" (us-coppa), "the European Convention for the
#: Protection of Human Rights..." truncated to "Convention" (gdpr),
#: "Protocol No 21" truncated to "Protocol" (ai-act), and 54 spurious
#: hits across uk-dpa2018's "Convention rights"/"Refugee Convention"/
#: "non-Convention countries" prose. A treaty-type word is EXTERNAL
#: only when EXPLICITLY NAMED (a Title-Case run ending in the keyword,
#: continued by its own qualifying phrase — "European Convention for
#: the Protection of Human Rights and Fundamental Freedoms") or cited
#: by its own numbered-instance form ("Protocol No 21") — never as a
#: bare generic noun.
#: the earlier continuation
#: allowed ANY run of up to 14 arbitrary words after the first connector,
#: with no stop condition at all — it swallowed a finite verb ("applies",
#: "providing") and everything after it into the "name". Bounded
#: generally, as the German stop-list already is: each continuation UNIT
#: is an OPTIONAL run of TITLE-CONNECTOR words (never standing alone —
#: a connector with no capitalised word after it fails the WHOLE unit,
#: so the match never ends on a dangling preposition) followed by ONE
#: REQUIRED Title-Case word. The repetition naturally stops at the
#: first lower-case word that is NOT a connector (a finite verb, an
#: adverb, "signed", "applies", ...) and at any punctuation (a comma or
#: full stop is never part of any unit).
#: "establishing" (as in "Treaty
#: establishing the European Community") — the historic Treaty-naming
#: convention's own connector verb, alongside the ordinary
#: prepositions already here.
_TREATY_CONNECTOR_WORD = (
    r"(?:of|for|on|to|and|the|with|regard|concerning|under|in|within|pursuant|establishing)"
)
#: "and" is the one connector word that is ALSO a
#: genuine citation-chain connective ("Article 5 ... and Article 6
#: thereof", "... and Articles 7 and 8"). Without a guard, "and"
#: swallows the FOLLOWING pinpoint keyword as if it were one more
#: Title-Case word of the treaty's own name ("... Example Community and
#: Article"), merging a second, separate citation into the first
#: treaty's name and losing it. "and" continues the name ONLY when the
#: next word is a capitalised NOUN that is not itself one of the
#: pinpoint-unit keywords (Article/Articles/Section/Annex/Chapter/
#: Part) — a genuine title conjunction ("... Rights and Fundamental
#: Freedoms") is unaffected, since "Fundamental" is not in this closed
#: list.
_TREATY_CONNECTOR_WORD_GUARDED = (
    r"(?:(?:of|for|on|to|the|with|regard|concerning|under|in|within|pursuant|establishing)|"
    r"and(?!" + _WS + r"(?:Article|Articles|Section|Annex|Chapter|Part)\b))"
)
_TREATY_CONTINUATION_UNIT = (
    r"(?:" + _TREATY_CONNECTOR_WORD_GUARDED + _WS + r"){0,4}[A-Z][A-Za-z'\-]*"
)
_EXT_NAMED_TREATY = (
    # (a) preceded by >=1 Title-Case qualifying word ("European
    # Convention..."), a following continuation is OPTIONAL.
    r"(?:[A-Z][A-Za-z'\-]*" + _WS + r"){1,8}(?:Convention|Protocol|Accord|Treaty)\b"
    r"(?:" + _WS + _TREATY_CONTINUATION_UNIT + r"){0,14}"
    r"|"
    # (b) the bare keyword with NO preceding word at
    # all ("Convention for the Protection of Individuals...", "Protocol
    # on the Statute of the Court of Justice...") — these real treaty
    # titles do not put an adjective before the keyword; the mandatory
    # (>=1) FOLLOWING continuation is what distinguishes a genuinely
    # named instrument from ordinary bare prose ("Convention rights",
    # "the Convention" with nothing after it — see (a)'s own sibling,
    # the standalone bare-keyword exclusion, unaffected since this
    # alternative is reachable ONLY from the pinpoint-gated variant,
    # never Pass 3's unguarded standalone scan).
    r"(?:Convention|Protocol|Accord|Treaty)\b"
    r"(?:" + _WS + _TREATY_CONTINUATION_UNIT + r"){1,14}"
)
#: "Protocol No 21"/"Protocol No. 22" — the EU drafting convention's own
#: numbered-instance naming, never truncated to the bare word "Protocol".
_EXT_PROTOCOL_NO = r"Protocol" + _WS + r"No\.?" + _WS + r"\d{1,4}"
#: "Convention 108" — the Council of Europe's own
#: numbered-instance naming convention for some treaties (no "No"
#: word, just the bare number directly after the keyword), the SAME
#: self-identifying numbered-instance shape as "Protocol No 21".
_EXT_CONVENTION_NO = r"Convention" + _WS + r"\d{1,4}"
#: German statute names in the genitive, after "der"/
#: "des" ("des Bürgerlichen Gesetzbuchs", "der Abgabenordnung"), or by
#: their own typical ending ("-gesetzes", "-gesetzbuches", "-ordnung")
#: are EXTERNAL — a Title-Case German compound word ending in one of
#: the closed statute-name suffixes.
#: the "über"/"gegen" qualifying phrase
#: in :data:`_EXT_DE_STATUTE`'s (b1)/(b2) alternatives must stop BEFORE
#: a trailing verb/adverb such as "gilt"/"entsprechend"/"hat"/
#: "errichtet"/"wurden" — GENERALISED from a closed verb stop-list to the SAME
#: structure the English treaty continuation uses
#: (:data:`_TREATY_CONTINUATION_UNIT`) — each continuation WORD is
#: either one of a closed set of German ARTICLES/PREPOSITIONS/
#: CONJUNCTIONS (never a verb/adverb/participle, which German does not
#: capitalise) or a REQUIRED capitalised (German noun) word; a
#: continuation unit that is a lowercase word NOT in the connector set
#: fails the WHOLE unit, so the match stops there rather than
#: absorbing it. KNOWN LIMIT (documented, not solved): a genuinely
#: continuing German noun phrase in the SAME grammatical shape as a
#: real qualifying phrase ("über den Europäischen Wirtschaftsraum DEN
#: MITGLIEDSTAATEN DER EUROPÄISCHEN UNION gleich" — "to the Member
#: States of the European Union", part of the PREDICATE, not the
#: treaty's own title) cannot be told apart from a genuine multi-word
#: title by surface case/connector pattern alone, because German
#: capitalises every noun, not only proper nouns; this needs real
#: parsing to fix properly and is not attempted here.
#: a closed PREPOSITION/ARTICLE/CONJUNCTION
#: list alone still broke a genuine title ("Verordnung über die
#: Vergabe ÖFFENTLICHER Aufträge" — a lower-case GENITIVE ADJECTIVE,
#: "öffentlicher", modifying the following noun; German adjectives are
#: an OPEN class, unlike prepositions, so no closed list covers them).
#: Generalised once more: ANY lower-case word immediately followed by
#: a capitalised (German noun) word forms a valid unit — this still
#: stops at "hat"/"gleich"/"vor" (followed by punctuation or another
#: lower-case word, never a capitalised one) while now also accepting
#: "öffentlicher Aufträge". Up to 3 such lower-case-prefixed words may
#: stack (adjective runs).
_DE_PHRASE_WORD = (
    r"(?:[a-zäöüß][\wäöüß'\-]*\s+){0,3}[A-ZÄÖÜ][\wäöüß'\-]*"
)
_EXT_DE_STATUTE = (
    # (a) a FUSED compound word ending in the lower-case suffix
    # ("Abgabenordnung", "Strafgesetzbuches", dative "Telekommunikationsgesetz"),
    # OPTIONALLY preceded by up to 3 agreeing Title-Case adjective words
    # ("des Allgemeinen Gleichbehandlungsgesetzes"). A BARE suffix word
    # with NO stem of its own ("Gesetzes", "Ordnung") can never match
    # here EITHER WAY (``*`` or ``+`` on the stem group): the suffix
    # alternation's own first character (G/g, O/o) always coincides
    # with the character ``[A-ZÄÖÜ]`` already consumed, so there is no
    # valid split that lets both consume the SAME leading letter —
    # verified directly (reverting ``+`` to ``*``
    # changes NO test outcome in this module's own conformance suite).
    # The ordinary-prose exclusion ("im Sinne des Gesetzes"/"der
    # Ordnung halber") is carried entirely by alternatives (b1)/(b2)
    # below, not by this one. NO leading ``\b`` guard on this
    # alternative's own "der"/"des"/"dem": every reachable call site
    # (``_OF_EXTERNAL_RE``'s DE branch) already requires a literal
    # ``\A[\s\xa0]+`` immediately before it, which is itself always a
    # true word boundary (whitespace -> letter) — a bare ``\b`` here
    # would be redundant and is removed: a mutant adding it back changes
    # no test outcome, because the match position can never start
    # mid-word, e.g. inside "oder", when a mandatory whitespace run
    # already precedes it.
    # "dem" (dative) is a valid article too . The negative lookahead
    # excludes "Verordnung (EU) …"/"Richtlinie (EU) …" — an EU act
    # whose STEM happens to end in "-ordnung" is never a German
    # domestic statute (cross-vertical rule: an EU act's OWN
    # literal/number pattern governs instead). A hyphenated compound
    # capitalises EACH segment ("BSI-Gesetzes"), so the suffix itself
    # may start with either case.
    r"(?:der|des|dem)" + _WS +
    # "Verordnung" (and "Verordnungen") is the bare generic
    # word (German for "Regulation"/"Ordinance"), NOT a compound noun
    # that happens to END in "-ordnung" — its own "Ver" stem is not a
    # real qualifying prefix. Excluded here so it falls through to (b2)
    # below instead, where it is accepted ONLY alongside the SAME
    # mandatory über/gegen phrase every other bare suffix word needs.
    r"(?!(?:[A-ZÄÖÜ][\wäöüß'\-]*" + _WS + r"){0,3}[Vv]erordnung(?:en)?\b)"
    r"(?:[A-ZÄÖÜ][\wäöüß'\-]*" + _WS + r"){0,3}"
    r"[A-ZÄÖÜ][\wäöüß'\-]*(?:[Gg]esetzes|[Gg]esetzbuches|"
    r"[Gg]esetzbuchs|[Gg]esetz|[Oo]rdnung)\b"
    r"(?!" + _WS + r"\(\s*E[UC]\s*\))|"
    # (b1) a MULTI-WORD Title-Case run, WITH AT LEAST ONE agreeing
    # adjective word, ending in its OWN standalone capitalised suffix
    # word ("des Bürgerlichen Gesetzbuchs") — the Gesetz/Gesetzbuch/
    # Ordnung family only; ``Vertrag``/``Abkommen`` are common nouns far
    # too often ("des Deutschen Vertrags" is NOT a named instrument on
    # its own, ) to accept with just one bare adjective and
    # no further qualifier — see (b2) for THEIR own, stricter, path.
    r"\b(?:der|des|dem)" + _WS + r"(?:[A-ZÄÖÜ][\wäöüß'\-]*" + _WS + r"){1,}"
    r"(?:Gesetzes|Gesetz|Gesetzbuches|Gesetzbuchs|Ordnung)\b"
    r"(?:" + _WS + r"(?:über|gegen)" + _WS +
    r"(?:" + _DE_PHRASE_WORD + _WS + r"){0,14}" + _DE_PHRASE_WORD + r")?|"
    # (b2) a BARE standalone suffix word with NO preceding adjective at
    # all, confirmed as a genuine named instrument ONLY by a MANDATORY
    # trailing "über"/"gegen" + title-form phrase ("des Gesetzes über
    # Ordnungswidrigkeiten", "des Vertrags über die Arbeitsweise der
    # Europäischen Union", "des Abkommens über den Europäischen
    # Wirtschaftsraum") — German supplement §1; the
    # qualifying phrase is what distinguishes this from the ordinary
    # -prose "dem Vertrag entsprechend"/"der Ordnung halber" shape
    # , which has NO such phrase and is excluded.
    r"(?:der|des|dem)" + _WS +
    r"(?:Gesetzes|Gesetz|Gesetzbuches|Gesetzbuchs|Ordnung|Vertrags|Vertrag|Abkommens|Abkommen|"
    r"Verordnung|Richtlinie|Empfehlung)\b" +
    _WS + r"(?:über|gegen)" + _WS +
    r"(?:" + _DE_PHRASE_WORD + _WS + r"){0,14}" + _DE_PHRASE_WORD
)
#: "the X Act YYYY"/"X Act of YYYY" — a Title-Case run (optionally with a
#: parenthetical, e.g. "Criminal Procedure (Scotland) Act 1995") followed
#: by "Act" and a year. Generic drafting convention, not any one
#: jurisdiction's own named statute.
#: widened beyond "Act" alone — "Code"/"Ordinance"/
#: "Statute"/"Law"/"Convention"/"Treaty" with a trailing year are the
#: SAME generic drafting shape (a Title-Case run + a closed-class
#: instrument-type word + a year), not a jurisdiction-specific lexicon.
#: This makes the KNOWN LIMIT ("an unnamed shape is under-recall only,
#: never a wrong name") TRUE for every one of these shapes too, not only
#: "Act".
_EXT_STATUTE_KIND = r"(?:Act|Code|Ordinance|Statute|Law|Convention|Treaty)"
#: a STATUTE_KIND word followed by a YEAR allows an
#: OPTIONAL comma directly after it ("the Packers and Stockyards Act,
#: 1921") alongside the existing "of" convention ("the Farm Credit Act
#: of 1971") — both are ordinary drafting conventions for attaching a
#: year to a named Act, never two independent shapes.
#: a "<Act name> (<parenthetical>)
#: Regulations/Order/Rules/Scheme <year>" continuation right after an
#: ordinary "<name> Act <year>" is a DIFFERENT, SUBORDINATE instrument
#: MADE UNDER that Act (a UK commencement/amendment statutory
#: instrument) — part of THIS name, never the parent Act self-naming
#: on its own with unrelated trailing prose.
_EXT_SI_UNDER_ACT_TAIL = (
    r"(?:" + _WS + r"\(\s*[A-Za-z0-9 .,\-]{1,60}\)" + _WS +
    r"(?:Regulations|Order|Rules|Scheme)\b" + _WS + r"\d{4})?"
)
#: the comma-year allowance ("Act, 1921") is a
#: drafting convention attested ONLY for "Act" — applying it to every
#: _EXT_STATUTE_KIND word let a page-header line such as
#: "United States Code, 2022 Edition" (or "... 2019 Edition") be read
#: as naming an EXTERNAL "Code" instrument. Restricted to "Act" alone;
#: the other statute-kind words keep only the existing "of YYYY"
#: convention.
_EXT_STATUTE_KIND_NON_ACT = r"(?:Code|Ordinance|Statute|Law|Convention|Treaty)"
_EXT_ACT_WITH_YEAR = (
    r"(?:the" + _WS + r")?(?:[A-Z][A-Za-z'’\-]*|\([A-Za-z ]+\))"
    r"(?:" + _WS + r"(?:[A-Z][A-Za-z'’\-]*|\([A-Za-z ]+\)|of|and)){0,8}"
    r"" + _WS + r"(?:Act,?|" + _EXT_STATUTE_KIND_NON_ACT + r")" +
    r"(?:" + _WS + r"of)?" + _WS + r"\d{4}" +
    _EXT_SI_UNDER_ACT_TAIL +
    r"|"
    # "the Sherman Act (15 U.S.C. 1 et seq.)" — a
    # US-style Act name with NO trailing year, confirmed instead by an
    # immediately-following U.S.C. codification parenthetical. Decision
    # (documented in spec/SPEC.md §8a.1): the parenthetical is the SAME
    # instrument's codification reference, not a second, independent
    # EXTERNAL item — it is swallowed into this one literal/name match,
    # never separately annotated.
    r"(?:the" + _WS + r")?(?:[A-Z][A-Za-z'’\-]*" + _WS + r"){1,6}" + _EXT_STATUTE_KIND +
    r"(?=" + _WS + r"\(\s*\d+" + _WS + r"U\.S\.C\.)"
)
_EXT_UK_GDPR = r"UK" + _WS + r"GDPR"
#: "title N" (US Code) names instrument "N U.S.C." — captured separately
#: below so the mapped name, not the raw literal, is what is recorded.
_EXT_USC_TITLE_RE = re.compile(r"\btitle" + _WS + r"(" + _NUM + r")\b", re.IGNORECASE)

#: Deliberately CASE-SENSITIVE (no ``re.IGNORECASE``): under
#: ``IGNORECASE``, Python's ``[A-Z]`` character class ALSO matches
#: lower-case letters, which silently destroys the "Title-Case word"
#: requirement :data:`_EXT_ACT_WITH_YEAR` depends on to avoid swallowing
#: ordinary lower-case prose before the real instrument name. Real
#: drafting always capitalises "Regulation"/"Directive"/"Article"/"Act"/
#: "TFEU" etc., so this loses nothing on real text.
#: STANDALONE-eligible names only (Pass 3, the "mentioned on its own, no
#: pinpoint chain before it" case, and the antecedent/chapeau pre-scans
#: that look for ANY bare mention) — every alternative here is a
#: SELF-IDENTIFYING instrument name (an abbreviation, a full EU-act
#: number, a UK/US Act-with-year, "Protocol No N") that is unambiguous
#: on its own. :data:`_EXT_NAMED_TREATY` is DELIBERATELY excluded here
#: : "European Convention for the Protection of Human
#: Rights..." named with NO pinpoint attached anywhere nearby is NOT,
#: by itself, a reference item (the hand-annotation contract's own
#: traps list only ever shows a treaty name WITH an attached pinpoint);
#: a bare two-Title-Case-word run ending in "Convention"/"Protocol"
#: ("Internet Protocol", "UN Convention", "Additional Protocol") is
#: ordinary prose far more often than it is a citation, so standalone
#: matching on this shape alone is not safe. See
#: :data:`_EXTERNAL_NAME_WITH_NAMED_TREATY_RE` for the PINPOINT-GATED
#: use (:data:`_OF_EXTERNAL_RE` and the antecedent-for-"thereof" scans),
#: where a Named Convention/Protocol/Accord is reachable ONLY because an
#: explicit pinpoint ("Article N of ...", "... Article N thereof")
#: governs it.
#: #: :data:`_EXT_DE_STATUTE` is DELIBERATELY EXCLUDED from this
#: standalone-eligible set — the SAME "no pinpoint attached -> no
#: item" rule X2 already applies to Convention/Protocol/Accord. A bare
#: German statute-shaped mention with no pinpoint anywhere nearby
#: ("der Rechtsordnung des Mitgliedstaats", "im Sinne des Neuen
#: Gesetzes", "der Neuen Ordnung", "der Hausordnung") is ordinary
#: prose, not a citation. :data:`_EXT_DE_STATUTE` remains reachable
#: ONLY through the pinpoint-gated path (:data:`_OF_EXTERNAL_RE`'s own
#: DE-specific alternative, which fires exclusively right after a
#: "§ N Abs. M"/"Artikel N"-shaped chain).
_EXTERNAL_NAME_RE = re.compile(
    "(?:" + _EXT_PROTOCOL_NO + ")|(?:" + _EXT_CONVENTION_NO + ")|(?:" + _EXT_EU_REGULATION +
    ")|(?:" + _EXT_EU_DIRECTIVE + ")|(?:" +
    _EXT_EU_RECOMMENDATION + ")|(?:" + _EXT_TFEU_TEU_CHARTER +
    ")|(?:" + _EXT_UK_GDPR + ")|(?:" + _EXT_ACT_WITH_YEAR + ")")
#: PINPOINT-GATED names — adds :data:`_EXT_NAMED_TREATY` (a Named
#: Convention/Protocol/Accord) to :data:`_EXTERNAL_NAME_RE`'s own set,
#: used ONLY where an explicit pinpoint chain already governs the match
#: (:data:`_OF_EXTERNAL_RE`, and the "thereof"/anaphora antecedent
#: pre-scans, whose own result is only ever consulted when a PINPOINT
#: ("Article N thereof") is what triggered the lookup in the first
#: place).
_EXTERNAL_NAME_WITH_NAMED_TREATY_RE = re.compile(
    _EXTERNAL_NAME_RE.pattern + "|(?:" + _EXT_NAMED_TREATY + ")")
#: The EU preamble recital convention — "Having
#: regard to the Treaty establishing the European Community, and in
#: particular Article 95 thereof," — names the treaty with NO pinpoint
#: attached to IT (the pinpoint is on the LATER "Article N thereof"
#: clause instead), so :data:`_EXT_NAMED_TREATY` stays unreachable from
#: the standalone mention scan in the general case (X2, above) UNLESS
#: this specific, narrow recital phrasing governs. "Having regard to"
#: is the EU legislative preamble's own fixed opening formula — never
#: ordinary prose — so gating a bare Named Treaty mention on it carries
#: none of X2's generic-noun risk.
_RECITAL_HAVING_REGARD_TREATY_RE = re.compile(
    r"\bHaving" + _WS + r"regard" + _WS + r"to" + _WS + r"(?:the" + _WS + r")?"
    r"(" + _EXT_NAMED_TREATY + r")")

#: "of <instrument>" / "to <instrument>" (UK "Schedule N to the X Act
#: YYYY") immediately after a pinpoint chain — the span up to and
#: including the instrument name becomes ONE EXTERNAL reference, pinpoint
#: kept in ``literal``, never in ``targets`` (R7).
#: "Article 16 TFEU" / "Article 6 TEU" / "Article 52 Charter" — the
#: treaty/charter name directly after the pinpoint, NO "of" at all
#: (the EU drafting convention's own alternate citation form).
_BARE_TREATY_SUFFIX_RE = re.compile(r"\A" + _WS + r"(" + _EXT_TFEU_TEU_CHARTER + r")")
#: "des"/"der" (German genitive "of") introduce a
#: German statute name DIRECTLY — the German article is ALREADY part
#: of "des"/"der" itself, so (unlike "of the X") no separate "the" is
#: expected after it.
#: German "der/des/dem Verordnung (EU) …"/"Richtlinie (EU) …" — the SAME
#: EU-act number pattern, just introduced by a German article instead
#: of "of"/"to" (cross-vertical "an EU act's literal
#: ends at the last character of its number" rule, applied in German
#: too).
#: German keywords ("Verordnung"/"Richtlinie"/"Empfehlung"), not the
#: English ones — a SEPARATE pattern, same number shape.
_EXT_DE_EU_ACT_RE = (
    r"(?:der|des|dem)" + _WS +
    r"(?:Verordnung|Richtlinie|Empfehlung)" + _WS + r"(?:\(\s*EU\s*\)" + _WS + r")?\d{2,4}/\d+"
    r"(?:/E[UC]{1,2})?"
)
#: "section 5 of the 1998 Act" — a
#: SHORT-YEAR-ONLY Act name (no instrument name word of its own, just
#: "the <year> Act"), a real UK drafting shorthand for an Act other
#: than the host (a DIFFERENT year than the host's own) — PINPOINT-
#: GATED only (never Pass 3's unguarded standalone scan, for the same
#: reason a bare treaty keyword is not standalone-eligible: "the 1998
#: Act" with no "of"/"to" pinpoint before it is ordinary prose, not
#: self-identifying).
_EXT_SHORT_YEAR_ACT_TAIL = r"(?:the" + _WS + r")?\d{4}" + _WS + r"Act\b"
#: A short parenthetical GLOSS may sit between
#: the pinpoint chain and its trailing "of"/"to" ("section 52B
#: (data-sharing code) of the Example Registration Act 1990") — one
#: level, no nested parentheses, length-capped so a stray unmatched
#: "(" cannot run away across the rest of ``text``.
_OF_EXTERNAL_GLOSS = r"(?:\([^()]{1,80}\)[\s\xa0]*)?"
_OF_EXTERNAL_RE = re.compile(
    r"\A[\s\xa0]*" + _OF_EXTERNAL_GLOSS + r",?[\s\xa0]*(?:of|to)\b" + _WS + r"(?:the" + _WS + r")?(" +
    _EXTERNAL_NAME_WITH_NAMED_TREATY_RE.pattern + r"|title" + _WS + _NUM +
    r"|" + _EXT_SHORT_YEAR_ACT_TAIL + r")"
    r"|\A[\s\xa0]+(" + _EXT_DE_EU_ACT_RE + r"|" + _EXT_DE_STATUTE + r")")
#: R2: "... of that Regulation/Directive/Act" directly after a chain,
#: when the HOST was just self-named (R2's own host-instrument branch) —
#: the chain's pinpoint stays INTERNAL to the host, never re-wrapped as
#: EXTERNAL the way an ordinary "of <named other instrument>" would be.
#: "to" alongside "of" : UK drafting's own convention is
#: "Schedule N TO the X Act YYYY" (never "of"), so its anaphoric form is
#: "Schedule N to that Act", not "... of that Act".
_OF_THAT_HOST_RE = re.compile(
    r"\A[\s\xa0]*,?[\s\xa0]*(?:of|to)[\s\xa0]+that[\s\xa0]+(?:Regulation|Directive|Act)\b")
#: the GENERAL anaphoric-external-with-a-pinpoint case
#: — "Article 5 of that Regulation", "section 406 of that Act" — the
#: antecedent is whatever external instrument was named EARLIER (never
#: necessarily the host; contrast :data:`_OF_THAT_HOST_RE`, which only
#: fires after an R2 host self-naming).
_OF_THAT_ANAPHORA_RE = re.compile(
    r"\A[\s\xa0]*,?[\s\xa0]*(?:of|to)[\s\xa0]+that[\s\xa0]+(Regulation|Directive|Act|title)\b")
#: "section N of THIS title" — US Code's own
#: self-reference-by-title-number idiom.
_OF_THIS_TITLE_RE = re.compile(r"\A[\s\xa0]*,?[\s\xa0]*of[\s\xa0]+this[\s\xa0]+title\b", re.IGNORECASE)
#: "Article N of this Convention"/"...Protocol"/
#: "...Treaty"/"...Accord" — the generic-treaty-type analogue of
#: :data:`_OF_THIS_TITLE_RE`'s own US-Code "this title" idiom. Resolved
#: INTERNAL to the chain's own pinpoint ONLY when the host genuinely IS
#: that treaty type (``host_instrument_name`` names that type word,
#: R1); otherwise the text names no identifiable instrument at all — R7
#: — so the whole span becomes EXTERNAL "unnamed (see note)" rather
#: than a bare truncated type word.
#: "the" is accepted alongside "this" — "Article 5 of
#: the Convention", with no further Named qualifier, is the SAME
#: unnamed-instrument shape as "Article 5 of this Convention" (neither
#: names an identifiable instrument on its own); both resolve the same
#: way (R1-by-type when the host IS that type, else R7 "unnamed (see
#: note)").
_OF_THIS_GENERIC_TYPE_RE = re.compile(
    r"\A[\s\xa0]*,?[\s\xa0]*of[\s\xa0]+(?:this|the)[\s\xa0]+(Convention|Protocol|Treaty|Accord)\b",
    re.IGNORECASE)

# ── internal pinpoint-chain grammar, by numbering family ──────────────
# Each entry recognises ONE absolute, self-contained internal citation
# (its own article/section/paragraph number is IN the literal — no
# enclosing-unit lookup needed) and reports the matched text as its own
# pinpoint directly (after light reformatting into the schema's pinpoint
# format). "Article"/"Articles" reuses the EXISTING plural/range/list
# grammar (:data:`ARTICLE_REF_RE`) for its NUMBER list; the chain here
# only adds the OPTIONAL trailing ", point (x)"/"subparagraph" suffix
# that v1 never carried as a separate pinpoint component.
#: a bare number RIGHT AFTER "Article(s)" that is immediately followed by
#: a time-DURATION unit ("Article 5 days") is a hard-negative DECOY, not
#: a citation at all — the negative lookahead applies to every number in
#: the list/range, not only the first (parity with v1's own
#: :data:`ARTICLE_REF_RE`, which only guarded its continuation items).
_NOT_A_DURATION = r"(?!\s*(?:day|days|week|weeks|month|months|year|years|hour|hours)\b)"
#: "point(s)" takes a LIST too ("points (a) and (c)"),
#: not only a single letter — otherwise a chain like "Article 9(2),
#: points (a) and (c), of that Regulation" stops BEFORE the point list,
#: leaving the "of that Regulation" suffix unreachable by the
#: anaphora-with-pinpoint grammar.
#: "Articles 8, 9, and 10" has a
#: comma DIRECTLY before "and" on its last member — the OLD connector
#: alternation ``(?:,|and|or|to)`` only ever matches ONE of these per
#: continuation, so ", and" (comma immediately followed by "and") was
#: never consumed as a single connector and the chain match stopped
#: before the final member. ``,\s*(?:and|or)?`` added as its own
#: alternative (comma, with an OPTIONAL "and"/"or" right after it)
#: fixes this WITHOUT touching :data:`ARTICLE_REF_RE` (article-v1,
#: frozen forever).
_EU_CHAIN_CONNECTOR = r"(?:,\s*(?:and|or)?|and|or|to)"
_EU_CHAIN_RE = re.compile(
    r"\bArticles?" + _WS + r"\d{1,3}\b" + _NOT_A_DURATION + _SUBPINS +
    r"(?:\s*" + _EU_CHAIN_CONNECTOR + r"\s*\d{1,3}\b" + _NOT_A_DURATION + _SUBPINS + r")*"
    r"(?:\s*,?\s*points?" + _WS + r"\(\s*[0-9a-z]{1,3}\s*\)"
    r"(?:\s*(?:,|and|or)\s*\(\s*[0-9a-z]{1,3}\s*\))*)?"
    r"(?:\s*,?\s*(?:first|second|third|fourth|fifth)" + _WS + r"(?:subparagraph|sentence))?",
    re.IGNORECASE)
#: "Article 9,
#: paragraph 3, first subparagraph, point (b)" — the EU drafting
#: convention writing the paragraph as its OWN comma-separated unit
#: (rather than a bracketed "(3)" subpin of the Article), still
#: carrying the SAME optional trailing subparagraph/point suffix
#: :data:`_EU_CHAIN_RE` already has. Tried BEFORE :data:`_EU_CHAIN_RE`
#: in :data:`chain_patterns` so it claims the WHOLE comma-chain span.
_EU_ARTICLE_PARAGRAPH_RE = re.compile(
    r"\bArticles?" + _WS + r"\d{1,3}\b" + _NOT_A_DURATION +
    r"\s*,?\s*paragraph" + _WS + r"\d{1,3}[A-Za-z]?\b" +
    r"(?:\s*,?\s*(?:first|second|third|fourth|fifth)" + _WS + r"(?:subparagraph|sentence))?"
    r"(?:\s*,?\s*points?" + _WS + r"\(\s*[0-9a-z]{1,3}\s*\)"
    r"(?:\s*(?:,|and|or)\s*\(\s*[0-9a-z]{1,3}\s*\))*)?",
    re.IGNORECASE)
_EU_ANNEX_RE = re.compile(
    r"\bAnnex" + _WS + r"[IVXLCDM]+\b"
    r"(?:\s*,?\s*(?:Section|point)" + _WS + r"[0-9A-Za-z]{1,3}\b)*"
    r"(?:\s*,?\s*[a-z]+" + _WS + r"indent)?",
    re.IGNORECASE)
_EU_CHAPTER_SECTION_RE = re.compile(
    r"\bChapter" + _WS + r"[IVXLCDM]+\b(?:\s*,?\s*Section" + _WS + r"\d{1,3}\b)?",
    re.IGNORECASE)
#: generic "section N"/"s. N"/"§ N" + optional sub-pinpoints — used by the
#: UK/US/generic families. "section" alone (lower-case keyword) is
#: distinguished from the EU "Article" family entirely by keyword choice.
#: ``\b``
#: immediately before "§" never matches when § is preceded by
#: whitespace — BOTH neighbours of that boundary position are
#: non-word characters, so ``\b`` requires one of them to be a word
#: character and fails. The alternation is split so ``\b`` only guards
#: the WORD-based alternatives ("section"/"s."); "§" (a symbol, already
#: self-delimiting) carries no boundary assertion of its own.
_SECTION_CHAIN_RE = re.compile(
    r"(?:\b(?:[Ss]ection|[Ss]\.)|§)" + _WS + r"\d{1,4}[A-Za-z]?\b" + _SUBPINS,
    re.IGNORECASE)
#: a connector between LISTED members may be the
#: Oxford-comma form — a comma DIRECTLY followed by "and"/"or" on the
#: LAST member ("sections 45, 6502, or 57a", "sections 6501, 6502, and
#: 45") — alongside the plain single-token forms (bare ",", bare
#: "and"/"or"/"to"). "through" is accepted as a synonym for "to" (a
#: US-drafting range connector). Moved up here  so
#: :data:`_SECTION_SUBPIN_OR_RE`, below, can use it too.
_SECTION_LIST_CONNECTOR = r"(?:,\s*(?:and|or)?|and|or|to|through)"
#: "section 3(10), (11)
#: and (14)" — SIBLING subsection alternatives at the SAME level
#: (never nested, unlike :data:`_SUBPINS`'s own directly-concatenated
#: "(3)(a)" chain), joined by the SAME connector set a plural numbered
#: list already accepts (a BARE comma included — "(10), (11)" has no
#: "and"/"or" of its own until the LAST member). Tried BEFORE
#: :data:`_SECTION_CHAIN_RE` in :data:`chain_patterns` so it claims
#: the WHOLE or-list span, never just its first member.
_SECTION_SUBPIN_OR_RE = re.compile(
    r"(?:\b(?:[Ss]ection|[Ss]\.)|§)" + _WS + r"\d{1,4}[A-Za-z]?\b" + _SUBPIN +
    r"(?:\s*" + _SECTION_LIST_CONNECTOR + r"\s*" + _SUBPIN + r")+", re.IGNORECASE)
#: "section 149 of or Schedule 11 to
#: <host>" — the UK drafting idiom citing a section AND a Schedule of
#: the SAME instrument together ("section 149 of, or Schedule 11 to,
#: the Act"). Matched UP TO the Schedule's own number only — the
#: trailing "to <instrument>" is left for the SAME generic
#: :data:`_OF_EXTERNAL_RE` tail-matching every other chain_patterns
#: member already shares.
_UK_SECTION_OF_OR_SCHEDULE_RE = re.compile(
    r"\bsection" + _WS + r"\d{1,4}[A-Za-z]?\b" + _SUBPINS +
    r"\s+of\s*,?\s*or\s*,?\s*Schedule" + _WS + r"\d{1,3}\b" + _SUBPINS,
    re.IGNORECASE)
#: US "subsection (a)(1)(A)" — relative, no absolute section number of its
#: own; resolved against the enclosing section (see ``enclosing_unit``).
_SUBSECTION_RE = re.compile(r"\bsubsection" + _WS + _SUBPIN + _SUBPINS, re.IGNORECASE)
_SUBPARAGRAPH_ABS_RE = re.compile(r"\bSubparagraph" + _WS + r"\(" + r"[A-Za-z]" + r"\)" + _SUBPINS)
#: "paragraph N" OR "paragraph N, point (x)" — the trailing ", point
#: (x)" is OPTIONAL and, when present, is captured as ONE combined
#: relative reference (never split into two), matching real EU drafting
#: ("paragraph 1, point (b)" against enclosing "Article 7" ->
#: "Article 7(1), point (b)").
_PARAGRAPH_REL_RE = re.compile(
    r"\bparagraph" + _WS + r"\d{1,3}[A-Za-z]?\b" + _SUBPINS +
    r"(?:,?\s*point" + _WS + r"\(\s*[0-9a-z]{1,3}\s*\))?", re.IGNORECASE)
_POINT_REL_RE = re.compile(r"\bpoint" + _WS + _SUBPIN, re.IGNORECASE)
#: PLURAL/RANGED/OR-LISTED forms for sections,
#: paragraphs and the German "§§" plural sign — "sections 3 to 5",
#: "sections 14 and 15", "paragraphs 1 and 2", "paragraphs 1 to 3", "§§ 3
#: bis 5" ("bis" = "to"), "§§ 3 und 4" ("und" = "and"). Each expands to
#: one target PER member, ``expanded_from`` set, the SAME discipline the
#: EU "Articles N, M and K"/"Articles N to M" grammar already has.
#: (:data:`_SECTION_LIST_CONNECTOR` is now defined earlier, above
#: :data:`_SECTION_SUBPIN_OR_RE`, which needs it too.)
_SECTION_PLURAL_RE = re.compile(
    r"\b[Ss]ections?" + _WS + r"\d{1,4}[A-Za-z]?\b" + _SUBPINS +
    r"(?:\s*" + _SECTION_LIST_CONNECTOR + r"\s*\d{1,4}[A-Za-z]?\b" + _SUBPINS + r")+", re.IGNORECASE)
_PARAGRAPH_PLURAL_RE = re.compile(
    r"\bparagraphs" + _WS + r"\d{1,3}[A-Za-z]?\b" + _SUBPINS +
    r"(?:\s*" + _SECTION_LIST_CONNECTOR + r"\s*\d{1,3}[A-Za-z]?\b" + _SUBPINS + r")+", re.IGNORECASE)
_DE_SS_PLURAL_RE = re.compile(
    r"§§" + r"\s*\d{1,4}[a-z]?\b" +
    r"(?:\s*(?:,|und|oder|bis)\s*\d{1,4}[a-z]?\b)+", re.IGNORECASE)
#: generic list/range TOKEN scanner shared by all three plural patterns
#: above — connector words include both English and German "to"/"and"
#: forms (plus the Oxford-comma and "through" forms, #: M3); a "to"/"through"/"bis" connector expands the IMPLIED
#: intermediate members too (same inclusive-range, capped, discipline
#: as :data:`_ARTICLE_LIST_TOKEN_RE`).
_GENERIC_LIST_TOKEN_RE = re.compile(
    r"(,\s*(?:and|or)?|and|or|und|oder|to|through|bis)?\s*(\d{1,4})([A-Za-z]?)\b(" + _SUBPINS + r")",
    re.IGNORECASE)
_RANGE_CONNECTOR_WORDS = frozenset({"to", "bis", "through"})
#: UK "Schedule M, paragraph N" / "paragraph N of Schedule M" — both
#: orders accepted on input; the pinpoint format is ALWAYS outer-unit
#: first ("Schedule M, paragraph N" — the contract's own pinpoint-order
#: rule).
_UK_SCHEDULE_FIRST_RE = re.compile(
    r"\bSchedule" + _WS + r"\d{1,3}\b\s*,?\s*paragraph" + _WS + r"\d{1,3}[A-Za-z]?\b" + _SUBPINS,
    re.IGNORECASE)
_UK_PARAGRAPH_OF_SCHEDULE_RE = re.compile(
    r"\bparagraph" + _WS + r"\d{1,3}[A-Za-z]?\b" + _SUBPINS + r"\s+of\s+Schedule" + _WS + r"\d{1,3}\b",
    re.IGNORECASE)
_UK_SCHEDULE_BARE_RE = re.compile(r"\bSchedule" + _WS + r"\d{1,3}\b", re.IGNORECASE)
#: PLURAL/listed "Schedules 5, 6 and 7" — tried BEFORE
#: the singular bare form.
_UK_SCHEDULE_PLURAL_RE = re.compile(
    r"\bSchedules" + _WS + r"\d{1,3}\b(?:\s*(?:,|and|or)\s*\d{1,3}\b)+", re.IGNORECASE)
#: PLURAL/ranged "Parts 5 to 7"/
#: "Chapters 3 and 4" — :data:`_UK_PART_RE`/:data:`_UK_CHAPTER_RE` were
#: SINGULAR-only; a RANGE ("to") was not recognised at all for either
#: (unlike :data:`_SECTION_PLURAL_RE`, which already uses
#: :data:`_SECTION_LIST_CONNECTOR`, the SAME connector set used here).
_UK_PART_PLURAL_RE = re.compile(
    r"\bParts" + _WS + r"\d{1,3}\b(?:\s*" + _SECTION_LIST_CONNECTOR + r"\s*\d{1,3}\b)+",
    re.IGNORECASE)
_UK_CHAPTER_PLURAL_RE = re.compile(
    r"\bChapters" + _WS + r"\d{1,3}\b(?:\s*" + _SECTION_LIST_CONNECTOR + r"\s*\d{1,3}\b)+",
    re.IGNORECASE)
#: PLURAL/listed "Annexes I and II".
_EU_ANNEX_PLURAL_RE = re.compile(
    r"\bAnnexes" + _WS + r"[IVXLCDM]+\b(?:\s*(?:,|and|or)\s*[IVXLCDM]+\b)+", re.IGNORECASE)
_ROMAN_LIST_TOKEN_RE = re.compile(r"(?:,|and|or)?\s*([IVXLCDM]+)\b", re.IGNORECASE)
#: B3 — OUTER-FIRST nested chains written INNER-first in the
#: text ("Section 2 of Chapter III", "Chapter 2 of Part 7", "paragraph 9
#: of Part 3 of Schedule 3") are reformatted outer-unit-first per the
#: contract's own pinpoint-order rule. Each is tried BEFORE its own
#: simpler, non-nested sibling pattern, so it gets first claim on the
#: WHOLE nested span.
_EU_SECTION_OF_CHAPTER_RE = re.compile(
    r"\bSection" + _WS + r"\d{1,3}\b" + _WS + r"of" + _WS + r"Chapter" + _WS + r"[IVXLCDM]+\b",
    re.IGNORECASE)
_UK_CHAPTER_OF_PART_RE = re.compile(
    r"\bChapter" + _WS + r"\d{1,3}\b" + _WS + r"of" + _WS + r"Part" + _WS + r"\d{1,3}\b",
    re.IGNORECASE)
_UK_PARAGRAPH_OF_PART_OF_SCHEDULE_RE = re.compile(
    r"\bparagraph" + _WS + r"\d{1,3}[A-Za-z]?\b" + _SUBPINS + _WS + r"of" + _WS +
    r"Part" + _WS + r"\d{1,3}\b" + _WS + r"of" + _WS + r"Schedule" + _WS + r"\d{1,3}\b",
    re.IGNORECASE)
_UK_PART_RE = re.compile(r"\bPart" + _WS + r"\d{1,3}\b", re.IGNORECASE)
_UK_CHAPTER_RE = re.compile(r"\bChapter" + _WS + r"\d{1,3}\b", re.IGNORECASE)
#: DE "§ N Abs. M Satz K" (and "Nr. J") — always INTERNAL; DE has no gold,
#: vector-only (see the task note: "there is no DE gold, so vectors are
#: the only check").
#: "Abs."/"Absatz" is now MANDATORY — a bare "§ N" with
#: NEITHER word present is NOT this family's own chain at all (it is the
#: generic/US "§ N" shape, :data:`_SECTION_CHAIN_RE`'s job); without this,
#: this pattern silently claimed "§ 6502(b)(1)(A)" (US) down to its bare
#: "§ 6502" and left "(b)(1)(A)" unclaimed. "Absatz" (spelled out) is
#: accepted alongside "Abs." .
_DE_CHAIN_RE = re.compile(
    r"§+\s*\d{1,4}[a-z]?" +
    r"\s+(?:Abs\.|Absatz)" + _WS + r"\d{1,3}" +
    r"(?:\s+Satz" + _WS + r"\d{1,3})?" +
    r"(?:\s+Nr\." + _WS + r"\d{1,3})?",
    re.IGNORECASE)
#: German drafting cites an EU act's own
#: numbering with the German word "Artikel" (never "§") — "Artikel 9
#: Absatz 1 der Verordnung (EU) 2016/679". A bare "Article"-family
#: pattern (:data:`_EU_CHAIN_RE`) never matches this spelling; this
#: pattern recognises it so the trailing "der Verordnung/Richtlinie/
#: Empfehlung ..." (already handled by :data:`_OF_EXTERNAL_RE`'s own
#: DE-EU-act alternative) wraps the WHOLE span as one EXTERNAL
#: reference, instead of leaving the pinpoint unclaimed and the
#: instrument name floating on its own (Pass 3).
_DE_ARTIKEL_CHAIN_RE = re.compile(
    r"\bArtikel" + _WS + r"\d{1,3}[a-z]?\b" +
    r"(?:" + _WS + r"(?:Abs\.|Absatz)" + _WS + r"\d{1,3})?" +
    r"(?:" + _WS + r"Satz" + _WS + r"\d{1,3})?",
    re.IGNORECASE)

#: deictic bare self-reference (R1) — NOT an item.
_BARE_SELF_RE = re.compile(
    r"\bthis" + _WS + r"(Regulation|Act|Directive|Article|paragraph|subparagraph)\b",
    re.IGNORECASE)
#: "this Section/Chapter/Title/Part" (R4) — INTERNAL to that unit, UNLESS
#: the named unit type is the WHOLE host (R5), signalled by the caller via
#: ``whole_host_unit`` (document metadata: which unit type, if any, the
#: file itself equals in full — e.g. ``"chapter"`` for a single-chapter
#: US Code extract).
_THIS_UNIT_RE = re.compile(r"\bthis" + _WS + r"(Section|Chapter|Title|Part)\b", re.IGNORECASE)
#: anaphoric EXTERNAL — "that/such Regulation/Directive/Act/title".
_ANAPHORA_EXTERNAL_RE = re.compile(
    r"\b(?:that|such)" + _WS + r"(Regulation|Directive|Act|title)\b", re.IGNORECASE)
#: anaphoric INTERNAL — "that Article/Schedule/subparagraph/section".
_ANAPHORA_INTERNAL_RE = re.compile(
    r"\bthat" + _WS + r"(Article|Schedule|subparagraph|section)\b", re.IGNORECASE)
_THEREOF_HERE_RE = re.compile(r"\bthereof\b", re.IGNORECASE)
_SO_IN_ORIGINAL_RE = re.compile(r"so\s+in\s+original", re.IGNORECASE)


#: N4/M10 (German supplement, R7-DE — the NOMINATIVE rule):
#: ``external_instrument`` is the act's name in the nominative, the case
#: inflection on the head noun (and any directly-agreeing adjective)
#: undone, EVERYTHING ELSE unchanged (a prepositional-object phrase like
#: "über Ordnungswidrigkeiten" is itself not case-inflected by the
#: citation and stays as-is). Covers exactly the suffix shapes
#: :data:`_EXT_DE_STATUTE` can match.
_DE_DECLINED_HEAD_NOUN_RE = re.compile(
    r"\b([\w\-]*)(gesetzbuches|gesetzbuchs|gesetzes|vertrags|abkommens)\b", re.IGNORECASE)


_EXT_DE_STATUTE_FULL_RE = re.compile(r"\A(?:" + _EXT_DE_STATUTE + r")\Z")


_DE_LEADING_ARTICLE_RE = re.compile(r"\A(?:der|des|dem)" + _WS)


#: a UK list marker
#: ("(a)", "(i)", "(a) (b)" for a continued list) or a US plain-text
#: dump's own page/section-break artifact ("Text \n") sitting
#: IMMEDIATELY before the real instrument name — _EXT_ACT_WITH_YEAR's
#: own "optionally with a parenthetical" support (for "Criminal
#: Procedure (Scotland) Act 1995") ALSO matched a leading LIST marker
#: bracket, and a run's own leading Title-Case-word slot matched the
#: literal word "Text" when a line-break artifact placed it directly
#: before the real name. Neither is part of the instrument's own name.
_LEADING_LIST_MARKER_RE = re.compile(
    r"\A(?:\(\s*[0-9a-zA-Z]{1,4}\s*\)[\s\xa0]*)+")
_LEADING_TEXT_ARTIFACT_RE = re.compile(r"\A[\s\xa0]*Text\b[\s\xa0]*")


def _normalize_external_name(raw: str) -> str:
    """N4/M10: for a German-introduced match ("der"/"des"/
    "dem" + instrument), the leading article is ALWAYS stripped (it is
    not part of the instrument's own name, in EITHER the EU-act case —
    "der Verordnung (EU) 2016/679" -> "Verordnung (EU) 2016/679", NOT
    case-inflected by the article, per the supplement — or the domestic
    -statute case, where :func:`_de_nominative` ALSO un-inflects the
    head noun). Every OTHER instrument shape (EU/UK/US matched without a
    German article) is returned UNCHANGED, verbatim, per R7 — EXCEPT a
    leading list marker or text-dump artifact ,
    neither of which the text's own instrument name ever includes."""
    if _EXT_DE_STATUTE_FULL_RE.match(raw):
        return _de_nominative(raw)
    if _DE_LEADING_ARTICLE_RE.match(raw):
        return _DE_LEADING_ARTICLE_RE.sub("", raw, count=1)
    cleaned = _LEADING_LIST_MARKER_RE.sub("", raw)
    cleaned = _LEADING_TEXT_ARTIFACT_RE.sub("", cleaned)
    return cleaned or raw


def _de_nominative(name: str) -> str:
    words = name.split(" ")
    # drop the leading article ("der"/"des"/"dem") — R7-DE names the
    # ACT, not the article.
    if words and words[0].lower() in ("der", "des", "dem"):
        words = words[1:]
    changed_head = False
    for i, w in enumerate(words):
        m = _DE_DECLINED_HEAD_NOUN_RE.fullmatch(w)
        if not m:
            continue
        stem, suffix = m.group(1), m.group(2)
        nominative = {
            "gesetzbuches": "gesetzbuch", "gesetzbuchs": "gesetzbuch",
            "gesetzes": "gesetz", "vertrags": "vertrag", "abkommens": "abkommen",
        }[suffix.lower()]
        if suffix[:1].isupper():
            nominative = nominative[:1].upper() + nominative[1:]
        words[i] = stem + nominative
        changed_head = True
        # the directly agreeing adjective immediately BEFORE the head
        # noun ends "-en" in the genitive ("Bürgerlichen"), "-es" in the
        # nominative neuter ("Bürgerliches") — the one agreement pattern
        # the supplement's own grounded examples exercise.
        if i > 0 and words[i - 1].endswith("en"):
            words[i - 1] = words[i - 1][:-2] + "es"
        break
    return " ".join(words) if changed_head else " ".join(words)


def _loose_name_match(a: str, b: str) -> bool:
    """a CASEFOLDED, leading-"the "-stripped,
    whitespace-collapsed comparison — the SAME normalisation
    SCORING.md's own scorer applies for instrument-name comparison —
    used to detect R1 host self-naming BY NAME (as opposed to
    :func:`_host_instrument_re`'s EU-specific BY NUMBER check)."""
    def norm(s: str) -> str:
        s = re.sub(r"[\s\xa0]+", " ", s).strip().casefold()
        return s[4:] if s.startswith("the ") else s
    return norm(a) == norm(b)


def _usc_instrument_name(number_text: str) -> str:
    """``"5"`` -> ``"5 U.S.C."`` — the mapped external-instrument name for
    a bare "title N" mention (never the raw literal; R7's own worked
    example names the mapped form, e.g. ``"5 U.S.C."`` for "title 5")."""
    return f"{number_text} U.S.C."


def _eu_chain_pinpoint(literal: str) -> str:
    """Reformat an :data:`_EU_CHAIN_RE` match into the schema's pinpoint
    format for its FIRST article number only — callers needing every
    expanded member call :func:`_expand_article_span` on the number list
    separately and re-attach the same trailing point/subparagraph suffix
    to EACH expanded member (outer unit first, §-contract rule)."""
    m = re.search(r"point" + _WS + r"\(\s*([0-9a-z]{1,3})\s*\)", literal, re.IGNORECASE)
    suffix = ""
    if m:
        suffix = f", point ({m.group(1)})"
    sp = re.search(r"((?:first|second|third|fourth|fifth)" + _WS + r"(?:subparagraph|sentence))", literal, re.IGNORECASE)
    if sp:
        suffix += f", {sp.group(1)}"
    return suffix


def _format_eu_article_paragraph_pinpoint(literal: str) -> str:
    """Reformat an :data:`_EU_ARTICLE_PARAGRAPH_RE` match ("Article 9,
    paragraph 3, first subparagraph, point (b)") into the schema's
    pinpoint format ("Article 9(3), first subparagraph, point (b)") —
    the paragraph number becomes the Article's own bracketed subpin,
    the SAME convention a bracketed "(3)" subpin already has."""
    art_m = re.search(r"\d{1,3}", literal)
    para_m = re.search(r"paragraph" + _WS + r"(\d{1,3}[A-Za-z]?)", literal, re.IGNORECASE)
    base = f"Article {art_m.group(0)}"
    if para_m:
        base += f"({para_m.group(1)})"
    return base + _eu_chain_pinpoint(literal)


def _eu_number_pinpoint(n: int, sub: str, suffix: str) -> str:
    base = f"Article {n}"
    if sub:
        base += sub
    return base + suffix


def _article_subpin_suffix(literal: str) -> str:
    """The bracketed ``(1)(b)`` run attached directly to the FIRST article
    number in an :data:`_EU_CHAIN_RE` match (parity with v1's own
    :data:`_TRAILING_GROUPS`) — kept SEPARATE from the ``point (x)``/
    subparagraph suffix (:func:`_eu_chain_pinpoint`), which always trails
    the whole list, never a single member."""
    m = re.match(r"\bArticles?" + _WS + r"\d{1,3}\b(" + _SUBPINS + r")", literal, re.IGNORECASE)
    return m.group(1).replace(" ", "") if m else ""


def _reference(literal: str, start: int, end: int, kind: str,
                external_instrument: "Optional[str]" = None,
                targets: "Optional[list]" = None,
                hard_case_tags: "Optional[list]" = None,
                external_target: "Optional[str]" = None) -> dict:
    ref = {
        "literal": literal,
        "literal_start": start,
        "literal_end": end,
        "kind": kind,
        "external_instrument": external_instrument if kind == "EXTERNAL" else None,
        "targets": [] if kind == "EXTERNAL" else (targets or []),
    }
    if kind == "EXTERNAL":
        # the "(instrument, target provision)"
        # requirement — a PARSED pinpoint field, in the SAME contract
        # pinpoint format INTERNAL targets use, or ``None`` when no
        # pinpoint chain could be parsed out of ``literal`` (e.g. a bare
        # "thereof"/"that Regulation" with no chain of its own). NEVER
        # gold-scored (R7 keeps gold ``targets`` empty for EXTERNAL
        # refs) — checked by conformance vectors only.
        ref["external_target"] = external_target
    if hard_case_tags:
        ref["hard_case_tags"] = hard_case_tags
    return ref


def _target(pinpoint: str, expanded_from: "Optional[str]" = None) -> dict:
    return {"pinpoint": pinpoint, "expanded_from": expanded_from}


# ── enclosing-unit derivation — a PURE function of the
# source text, an offset and a numbering family. Both benchmark arms,
# and any other caller, share this ONE implementation; it is part of
# the §8a.1 resolver, with its own conformance vectors.
_EU_ARTICLE_HEADING_RE = re.compile(r"(?m)^[ \t\xa0]*Article[\s\xa0]+(\d{1,3})[ \t\xa0]*$")
#: US Code style: a standalone "§N." marker (no space before the dot) —
#: observed directly in the US source texts (e.g. "§230.", "§6502.").
_US_SECTION_HEADING_RE = re.compile(r"§\s*(\d{1,4}[A-Za-z]?)\.")
#: UK style (legislation.gov.uk plain-text dumps): the OUTER-UNIT
#: headings are ALL-CAPS keywords — "SCHEDULE 12", "PART 7" — reliably
#: distinct from an ordinary body-text REFERENCE to the same unit, which
#: is always mixed-case ("Schedule 12", "Part 7"). NBSP-aware
#: ([\s\xa0]+). This is a GENERAL pattern (no per-vertical constant):
#: verified directly against uk-dpa2018's own text (e.g. "... SCHEDULE 1
#: Special categories of personal data ...", "... SCHEDULE 2 Exemptions
#: etc from the UK GDPR \nSection 15 PART ...").
_UK_OUTER_HEADING_RE = re.compile(
    r"\b(SCHEDULE|PART|CHAPTER)[\s\xa0]+(\d{1,3})\b")
#: UK ordinary SECTION-number heading: NOT ALL-CAPS, no standalone
#: keyword at all — legislation.gov.uk's own flattened-text layout puts
#: the bare section number directly between a repeated section-title
#: phrase and the section's own first substantive sentence, with NO
#: separating punctuation or digit before it. A general, low-false-
#: positive pattern for "the digit run that is THIS marker, not a
#: cross-reference or a date" inside a flattened layout is not
#: detected — see §8a.1's own KNOWN LIMITS. Left UNDETECTED (returns
#: ``None``) rather than guessed at.
_UK_SECTION_HEADING_RE = None
#: EU CHAPTER/SECTION standalone headings  — verified directly
#: against the GDPR source text ("CHAPTER I" ... "CHAPTER V", each its
#: own standalone line; "Section 1" ... "Section 5" nested inside a
#: chapter, also standalone).
_EU_CHAPTER_HEADING_RE = re.compile(r"(?m)^[ \t\xa0]*CHAPTER[\s\xa0]+([IVXLCDM]+)[ \t\xa0]*$")
_EU_SECTION_HEADING_RE = re.compile(r"(?m)^[ \t\xa0]*Section[\s\xa0]+(\d{1,3})[ \t\xa0]*$", re.IGNORECASE)


def enclosing_unit_at(source_text: str, offset: int, numbering_family: str = "eu") -> "Optional[str]":
    """The nearest preceding numbered-unit heading in ``source_text``
    BEFORE ``offset`` — a PURE function of exactly these three inputs,
    used to derive ``resolve_references()``'s own ``enclosing_unit``
    keyword (R4; relative "paragraph 1"/"point (a)"/"subsection (b)"
    references) WITHOUT ever reading gold. Returns ``None`` when no
    reliable heading is found for ``numbering_family`` — a caller
    receiving ``None`` lets :func:`resolve_references` fall back to its
    own bare-suffix/``ambiguous_reference`` path, never a guess.

    * ``"eu"``: the nearest preceding standalone ``"Article N"`` heading
      line (:data:`_EU_ARTICLE_HEADING_RE`) -> ``"Article N"``.
    * ``"us"``: the nearest preceding ``"§N."`` marker
      (:data:`_US_SECTION_HEADING_RE`) -> ``"§ N"``.
    * ``"uk"``: the nearest preceding ALL-CAPS ``"SCHEDULE N"``/
      ``"PART N"``/``"CHAPTER N"`` heading (:data:`_UK_OUTER_HEADING_RE`)
      -> ``"Schedule N"``/``"Part N"``/``"Chapter N"``. An ordinary
      SECTION-level heading is NOT detected (see that
      pattern's own docstring note) — returns whichever outer-unit
      heading is nearest, or ``None`` if none precedes ``offset`` at all.
    * ``"de"``: not attempted (DE carries no gold; vector-only per the
      task) — always ``None``.
    """
    if not isinstance(source_text, str) or not isinstance(offset, int):
        raise ValueError("enclosing_unit_at() requires a string and an int offset")
    if numbering_family == "eu":
        last = None
        for m in _EU_ARTICLE_HEADING_RE.finditer(source_text):
            if m.start() >= offset:
                break
            last = m.group(1)
        return f"Article {last}" if last else None
    if numbering_family == "us":
        last = None
        for m in _US_SECTION_HEADING_RE.finditer(source_text):
            if m.start() >= offset:
                break
            last = m.group(1)
        return f"§ {last}" if last else None
    if numbering_family == "uk":
        last = None
        for m in _UK_OUTER_HEADING_RE.finditer(source_text):
            if m.start() >= offset:
                break
            last = (m.group(1).capitalize(), m.group(2))
        return f"{last[0]} {last[1]}" if last else None
    return None


def enclosing_units_at(source_text: str, offset: int, numbering_family: str = "eu") -> dict:
    """B3 — the ANCESTOR CHAIN (every containing unit, by
    LEVEL, independently) strictly BEFORE ``offset``, for R4's own
    "this <level>" resolution — distinct from :func:`enclosing_unit_at`
    (which returns only the single DEEPEST/most-specific heading, used
    for the ARTICLE/SECTION-level relative-reference anchor, and is left
    UNCHANGED for that purpose). Each LEVEL ("part", "chapter",
    "section", "title") is tracked SEPARATELY — the nearest preceding
    heading of THAT level, regardless of which other level's heading sits
    between it and ``offset`` — so a reference nested three levels deep
    still resolves its OUTER ancestors correctly, not just its immediate
    parent.

    * ``"eu"``: ``{"chapter": "Chapter <roman>", "section": "Section
      <N>"}`` from :data:`_EU_CHAPTER_HEADING_RE`/
      :data:`_EU_SECTION_HEADING_RE`.
    * ``"uk"``: ``{"part": "Part <N>", "chapter": "Chapter <N>"}`` from
      :data:`_UK_OUTER_HEADING_RE` (SCHEDULE is tracked too, under key
      ``"schedule"``, though R4's own ``_THIS_UNIT_RE`` has no "this
      Schedule" trigger word).
    * ``"us"``: ``{"section": "§ <N>"}`` from
      :data:`_US_SECTION_HEADING_RE` (no general TITLE/CHAPTER/PART
      heading detector — a caller wanting "this title"'s own
      instrument name uses ``host_title_instrument`` instead, never this
      function).

    A level with no preceding heading at all is simply ABSENT from the
    returned dict (never a wrong guess).
    """
    if not isinstance(source_text, str) or not isinstance(offset, int):
        raise ValueError("enclosing_units_at() requires a string and an int offset")
    # a SINGLE forward scan over every heading type,
    # in POSITION order — a new HIGHER-level heading RESETS every
    # LOWER level (a new CHAPTER clears Section; a new PART clears
    # Chapter and Section) by re-assigning a FRESH dict at that point,
    # rather than tracking each level's own "nearest preceding"
    # independently (which could stitch together ancestors from
    # DIFFERENT containing units that never actually nest together).
    if numbering_family == "eu":
        events = sorted(
            [(m.start(), "chapter", m.group(1)) for m in _EU_CHAPTER_HEADING_RE.finditer(source_text)] +
            [(m.start(), "section", m.group(1)) for m in _EU_SECTION_HEADING_RE.finditer(source_text)])
        cur: dict = {}
        for pos, level, val in events:
            if pos >= offset:
                break
            if level == "chapter":
                cur = {"chapter": f"Chapter {val}"}
            else:
                cur = dict(cur)
                cur["section"] = f"Section {val}"
        return cur
    if numbering_family == "uk":
        events = sorted((m.start(), m.group(1).upper(), m.group(2))
                         for m in _UK_OUTER_HEADING_RE.finditer(source_text))
        main: dict = {}
        schedule_state = None
        in_schedule = False
        for pos, kw, num in events:
            if pos >= offset:
                break
            if kw == "SCHEDULE":
                schedule_state = {"schedule": f"Schedule {num}"}
                in_schedule = True
            elif kw == "PART":
                if in_schedule:
                    schedule_state = dict(schedule_state)
                    schedule_state["part"] = f"Part {num}"
                else:
                    main = {"part": f"Part {num}"}
            elif kw == "CHAPTER":
                if in_schedule:
                    schedule_state = dict(schedule_state)
                    schedule_state["chapter"] = f"Chapter {num}"
                else:
                    main = dict(main)
                    main["chapter"] = f"Chapter {num}"
        return schedule_state if in_schedule and schedule_state else main
    if numbering_family == "us":
        last = None
        for m in _US_SECTION_HEADING_RE.finditer(source_text):
            if m.start() >= offset:
                break
            last = m.group(1)
        return {"section": f"§ {last}"} if last else {}
    return {}


def host_section_numbers_in(source_text: str, numbering_family: str = "us") -> set:
    """EVERY section number ``source_text`` itself
    DEFINES, as a PURE function of the source text and the numbering
    family — the missing derivation the M8 "section N of this title"
    fix  needed but never got: :func:`resolve_references`'s
    own ``host_section_numbers`` keyword was always threaded as
    ``None`` because nothing in 5d-nd (or the benchmark harness)
    computed it. Used exactly like :func:`enclosing_unit_at`/
    :func:`enclosing_units_at` — called ONCE per document by the
    caller, the result passed in, never guessed sentence-by-sentence.

    Only ``"us"`` is implemented (the US Code's "§N."
    heading marker, :data:`_US_SECTION_HEADING_RE`, already used by
    :func:`enclosing_unit_at`) — the ONLY numbering family whose own
    grammar has a "section N of this title" idiom at all (M8).
    Every other family returns an empty set (never a guess); a caller
    passing ``numbering_family="eu"/"uk"/"de"`` through to this
    function gets ``set()``, matching ``host_section_numbers=None``'s
    own "nothing known" behaviour in :func:`resolve_references`.

    Returns the BARE digit string of each ``§N.`` heading (no letter
    suffix, matching the plain ``\\d{1,4}`` extraction
    :func:`resolve_references`'s own M8 branch runs over the citing
    text — "§ 6502a." would contribute ``"6502"``, the same number a
    citing "section 6502 of this title" would look up; letter-suffixed
    sub-sections are not tracked separately here, only the SECTION
    number itself)."""
    if not isinstance(source_text, str):
        raise ValueError("host_section_numbers_in() requires a string")
    if numbering_family != "us":
        return set()
    out = set()
    for m in _US_SECTION_HEADING_RE.finditer(source_text):
        digits = re.match(r"\d{1,4}", m.group(1))
        if digits:
            out.add(digits.group(0))
    return out


#: B3 — the outer-first ANCESTOR LEVEL ORDER per family,
#: used to build an R4 "this <unit>" pinpoint from
#: :func:`enclosing_units_at`'s own ancestor chain. "title" is handled
#: separately (R1/R5/EXTERNAL, above) — never resolved through this
#: ordering.
_LEVEL_ORDER = {
    "eu": ("chapter", "section"),
    "uk": ("schedule", "part", "chapter"),
    "us": ("title", "chapter", "part", "section"),
}


def resolve_references(
    text: str,
    enclosing_unit: "Optional[str]" = None,
    numbering_family: str = "eu",
    host_instrument_name: "Optional[str]" = None,
    host_instrument_number: "Optional[str]" = None,
    whole_host_unit: "Optional[str]" = None,
    preceding_text: str = "",
    quoted_amending_target: "Optional[str]" = None,
    enclosing_units: "Optional[dict]" = None,
    host_title_instrument: "Optional[str]" = None,
    host_section_numbers: "Optional[set]" = None,
) -> list:
    """The SHARED cross-reference resolver (spec/SPEC.md §8a.1) — a
    PURE, deterministic function of ``text`` and the
    caller-supplied document metadata below. NEVER reads gold; NEVER
    reads ``references``/``hard_case_tags``/``enclosing_unit`` from
    anywhere but what the caller passes in.

    Parameters (ALL caller-supplied document metadata — never a
    resolution-profile field, exactly as ``host_instrument_number``
    already is for :func:`cross_reference_targets`):

    * ``enclosing_unit`` — the pinpoint prefix (e.g. ``"Article 7"``,
      ``"§ 230"``, ``"section 6502"``) a RELATIVE reference ("paragraph
      1", "point (a)", "subsection (b)") resolves against. The caller
      derives this from the source text (e.g. the nearest preceding
      numbered-unit heading); this function never guesses it from the
      sentence alone when it is not given, and a relative reference with
      no ``enclosing_unit`` resolves to the bare suffix only (best effort,
      flagged ``ambiguous_reference``).
    * ``numbering_family`` — ``"eu"``, ``"uk"``, ``"us"``, or ``"de"``:
      which of §8a's absolute pinpoint grammars is tried FIRST (all
      families' EXTERNAL-instrument and anaphora rules still apply
      regardless of family, since a host document can still cite another
      family's instrument).
    * ``host_instrument_name`` — the host's own full name as the text
      would name it (e.g. ``"Regulation (EU) 2024/1689"``) — used ONLY
      for R2 (quoted-amending-text): a pinpoint-bearing mention that
      NAMES the host resolves INTERNAL, pinpoint ``"Instrument"`` (the
      host-instrument pinpoint format, R4's addendum).
    * ``host_instrument_number`` — forwarded, unchanged, to the EXISTING
      v1 host-instrument-number override logic for the EU "Article N of
      Regulation (EU) <number>" self-naming case (R1).
    * ``whole_host_unit`` — the unit TYPE (``"section"``, ``"chapter"``,
      ``"title"``, ``"part"``) the host file equals in full, if any (R5);
      ``"this <that type>"`` is then NOT an item, exactly like R1's bare
      self-reference, instead of R4's "resolve to that larger unit".
    * ``preceding_text`` — text before ``text`` in the same provision, for
      anaphora ("that Regulation", "thereof") whose antecedent was named
      earlier than the sentence under scan.
    * ``quoted_amending_target`` — R2's "amended instrument" name, used
      for a bare pinpoint inside quoted amending text that does NOT name
      the host (designates the OTHER, amended instrument instead).

    Returns a list of reference dicts: ``literal``/``literal_start``/
    ``literal_end`` (offsets into ``text``), ``kind``
    (``"INTERNAL"``/``"EXTERNAL"``), ``external_instrument`` (``None`` on
    INTERNAL; R7's exact-as-named string, or ``"unnamed (see note)"``, on
    EXTERNAL), ``targets`` (``[]`` on EXTERNAL; a list of ``{"pinpoint",
    "expanded_from"}`` on INTERNAL — one member per expanded range/plural/
    or-list member), and an optional ``hard_case_tags`` list (currently
    only ``["ambiguous_reference"]``, R6/R-fallback cases).

    Deterministic, stdlib-only, no randomness, no network.
    """
    if not isinstance(text, str):
        raise ValueError("resolve_references() requires a string")

    full_preceding = (preceding_text or "")

    # UK drafting names an Act by its calendar YEAR
    # ("the 2018 Act"), which the short-year rule (below) already
    # matches against ``host_instrument_number`` — but a UK host is often
    # passed with NO ``host_instrument_number`` at all (its number IS a
    # chapter/regnal cite, never a bare year), so that rule never fired.
    # Derive the host's YEAR straight from ``host_instrument_name`` here,
    # IN THE RESOLVER (never the caller/harness), whenever the caller
    # supplied no number and the name itself ends "... Act YYYY" — used
    # ONLY by the short-year rule below, never written back into
    # ``host_instrument_number`` itself (which still gates the EU
    # NUMBER-shaped host-mention match above/below, a different thing).
    _host_short_year = host_instrument_number
    if _host_short_year is None and host_instrument_name:
        _year_m = re.search(r"\bAct" + _WS + r"(\d{4})\s*\Z", host_instrument_name,
                             re.IGNORECASE)
        if _year_m:
            _host_short_year = _year_m.group(1)

    # anaphora ("that Act/
    # Regulation/Directive/title/Treaty/Protocol", "thereof", "such X")
    # resolves through ONE ordered list of instrument MENTIONS built over
    # ``preceding_text + text`` (:data:`_mentions`, below) — never by
    # FILTERING host self-namings out of a separate "external candidate"
    # list — the ONE ordered mention list has no separate "candidate
    # list" to filter at all. Each mention records its position, its KIND
    # (:func:`_classify_instrument_kind`, the name's own HEAD noun), and
    # whether it IS THE HOST. A mention is the host when it matches the
    # host NUMBER on token boundaries AND is of the host's own instrument
    # KIND (never a bare substring — "2016/6790" is not "2016/679";
    # "Directive 2016/679" is not "Regulation (EU) 2016/679"), or when it
    # matches the host NAME (NBSP/whitespace-tolerant, via
    # :func:`_loose_name_match`). Host mentions are NEVER removed from
    # the list; they compete on recency like any other mention — the
    # anaphor resolves to the NEAREST preceding mention of the matching
    # kind, host or not (see :func:`_nearest_mention_before` below).
    _host_kind = _classify_instrument_kind(host_instrument_name) if host_instrument_name else None

    def _is_host_mention(name: "Optional[str]") -> bool:
        if not name:
            return False
        if host_instrument_name and _loose_name_match(name, host_instrument_name):
            return True
        if (host_instrument_number and _host_kind is not None and
                _classify_instrument_kind(name) == _host_kind and
                re.search(r"(?<!\w)" + re.escape(host_instrument_number) + r"(?!\w)", name)):
            return True
        return False

    last_internal_unit = None
    last_external = None

    occupied = []  # [(start, end)]
    out = []

    def _overlaps(s, e):
        return any(not (e <= os_ or s >= oe_) for os_, oe_ in occupied)

    def _claim(s, e):
        occupied.append((s, e))

    # Pass 0 — bare self-reference (R1) / "this Article/paragraph" (R1/R4
    # continuation) / "this Section|Chapter|Title|Part" (R4, or R5 drop).
    # Consumed FIRST and unconditionally so no later pattern re-reads the
    # same span as something else; produces NO reference for the R1/R5
    # branches.
    for m in _BARE_SELF_RE.finditer(text):
        _claim(m.start(), m.end())
    for m in _THIS_UNIT_RE.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        unit_word = m.group(1).lower()
        # "this title" preceded by "of" is part of a
        # LARGER "section N of this title" citation — leave it UNCLAIMED
        # here so Pass 2's own chain-aware ``_OF_THIS_TITLE_RE`` branch
        # claims the WHOLE span as ONE reference instead of this bare
        # match claiming just "this title" first (which would overlap).
        if unit_word == "title" and re.search(r"\bof[\s\xa0]*\Z", text[:m.start()], re.IGNORECASE):
            continue
        # "this section" (lower-case "section" —
        # UK/US drafting's own deictic idiom for the CURRENT enclosing
        # section itself) is R1-style deictic, NOT an item — distinct
        # from "this Section" (capitalised, the EU/UK "group of
        # Articles" sense, which DOES go through R4 below). The
        # original CASE of the matched word (not the pattern's own
        # case-insensitivity) is what distinguishes them.
        if m.group(1) == "section":
            _claim(m.start(), m.end())
            continue
        _claim(m.start(), m.end())
        if whole_host_unit and unit_word == whole_host_unit.lower():
            continue  # R5: the named unit IS the whole host -> not an item
        # "this title" (US Code convention) is EXTERNAL
        # — the Title is a LARGER unit than any one section's own file,
        # per the contract's own worked example ("this title" means the
        # whole title, e.g. "18 U.S.C.", EXTERNAL unless the target
        # section is in this file). R5 (above) already drops it when the
        # file itself equals the whole title.
        if unit_word == "title":
            # M6/R7: with NO host_title_instrument given,
            # the text names no identifiable instrument — R7 requires
            # "unnamed (see note)", never the bare GLOSS "this title"
            # (that string describes the resolver's OWN fallback, not
            # anything the text itself named).
            if host_title_instrument:
                instrument = host_title_instrument
                out.append(_reference(m.group(0), m.start(), m.end(), "EXTERNAL",
                                       external_instrument=instrument))
            else:
                instrument = "unnamed (see note)"
                out.append(_reference(m.group(0), m.start(), m.end(), "EXTERNAL",
                                       external_instrument=instrument,
                                       hard_case_tags=["ambiguous_reference"]))
            last_external = instrument
            continue
        # R4: resolve "this <Section/Chapter/Part>" against the ANCESTOR
        # at that exact level .
        # ``enclosing_units`` (:func:`enclosing_units_at`) carries the
        # outer-first ancestor chain; when it is given, the pinpoint is
        # built outer-first from every ancestor AT OR ABOVE the named
        # level ("this Section" inside "Part 7, Chapter 2, Section 3"
        # -> "Part 7, Chapter 2, Section 3"). Falls back to the simple
        # ``enclosing_unit`` value, then to a bare capitalised word
        # (flagged ``ambiguous_reference``), when no ancestor chain was
        # given or the level is missing from it.
        order = _LEVEL_ORDER.get(numbering_family, ())
        pin = None
        if enclosing_units is not None and unit_word in order:
            idx = order.index(unit_word)
            if unit_word in enclosing_units:
                parts = [enclosing_units[lv] for lv in order[:idx + 1] if lv in enclosing_units]
                pin = ", ".join(parts)
            else:
                # the caller DID attempt ancestor
                # derivation (``enclosing_units`` was given) and this
                # exact level is simply not open here — emit NO item
                # rather than a wrong/bare guess.
                continue
        tags_this = None
        if pin is None:
            if enclosing_unit:
                pin = enclosing_unit
            else:
                pin = m.group(1).capitalize()
                tags_this = ["ambiguous_reference"]
        out.append(_reference(m.group(0), m.start(), m.end(), "INTERNAL",
                               targets=[_target(pin)], hard_case_tags=tags_this))
        last_internal_unit = pin

    # Pass 1 — R2 quoted-amending bare pinpoint naming the HOST instrument
    # ("Regulation (EU) 2024/1689 of the European Parliament and of the
    # Council" naming the file's OWN instrument) -> INTERNAL, pinpoint
    # "Instrument" (the host-instrument pinpoint format).
    if host_instrument_name:
        # NBSP-tolerant (``_flexible_name_pattern``), not
        # a plain ``re.escape`` over a literal ordinary space — EU
        # drafting sources separate "Regulation (EU)" from its number
        # with an NBSP ("Regulation\xa0(EU)\xa02024/1689"), which never
        # matched ``host_instrument_name``'s own ordinary-space form,
        # silently falling through to Pass 3's bare EXTERNAL-name scan.
        host_re = re.compile(_flexible_name_pattern(host_instrument_name) + r"(?:" + _WS +
                              r"of" + _WS + r"the" + _WS + r"European" + _WS +
                              r"Parliament" + _WS + r"and" + _WS + r"of" + _WS +
                              r"the" + _WS + r"Council)?", re.IGNORECASE)
        for m in host_re.finditer(text):
            if _overlaps(m.start(), m.end()):
                continue
            # # a host-name occurrence immediately preceded by "of (the)"
            # is part of a LARGER "<chain> of <host name>" citation
            # ("section 121 of the Data Protection Act 2018") — leave it
            # UNCLAIMED here so Pass 2's own chain-aware R1-by-name
            # branch (``_loose_name_match``) claims the WHOLE span as
            # ONE reference instead of this narrower bare-name match
            # claiming only the instrument-name tail first.
            before = text[:m.start()]
            # require a PINPOINT-shaped ending right before
            # the "of (the)"/"to (the)" — a number (optionally with ONE
            # trailing letter, "153A") or a closing bracket — so "within
            # the MEANING OF Regulation (EU) 2024/9999" (ordinary bare
            # self-naming, R2 — "meaning" ends in an ordinary LETTER, not
            # a pinpoint) is NOT excluded; only a genuine "<number/chain>
            # of/to the <host name>" is.
            # GENERALISED beyond "ends in a digit/letter
            # or ')'" — a pinpoint chain may also end in one of the
            # named sub-unit WORDS a chain can trail with ("first
            # subparagraph", "second sentence"; "point (a)" already ends
            # in ")"), directly followed by ", of <host>"/" of <host>".
            # Without this, "Article 6(1), first subparagraph, of
            # Regulation (EU) 2024/1689" let Pass 1 claim the bare host
            # name FIRST (its own "before" ends in "subparagraph, ",
            # which the old digit/")"-only check did not recognise),
            # before Pass 2's chain-aware branch could claim the WHOLE
            # span — producing two OVERLAPPING references (B1).
            if re.search(r"(?:\d{1,4}[A-Za-z]?\b|\)|subparagraph|sentence|paragraph|point)"
                         r"[\s\xa0]*,?[\s\xa0]*(?:of|to)(?:" + _WS +
                         r"the)?[\s\xa0]*\Z", before, re.IGNORECASE):
                continue
            # the SAME deferral, for German — "§ 4
            # Absatz 1 DES Bundesdatenschutzgesetzes" introduces the host
            # name with a genitive article ("des"/"der"/"dem"), not
            # "of"/"to"; without this, Pass 1 claimed "Bundesdatenschutz-
            # gesetzes" bare FIRST (before Pass 2's own chain-aware
            # by-name branch could extend the chain's span to cover it),
            # producing two OVERLAPPING references — leave it unclaimed
            # here too.
            if re.search(r"(?:\d{1,4}[a-z]?\b|\))[\s\xa0]*,?[\s\xa0]*(?:des|der|dem)[\s\xa0]*\Z",
                         before, re.IGNORECASE):
                continue
            # a deictic "this <host name>"/"that <host
            # name>" (no pinpoint of its own) is R1's own bare
            # self-reference shape, NOT a second, separate "Instrument"
            # item — the "of this <type>" + pinpoint-chain branch below
            # (:data:`_OF_THIS_GENERIC_TYPE_RE`) is what resolves a
            # PINPOINT-bearing mention of this exact shape ("Article 5 of
            # this Convention"); this bare occurrence, with no pinpoint
            # attached to IT, stays unclaimed and produces no item at all
            # (R1), exactly like a bare "this Regulation" already does.
            if re.search(r"\b(?:this|that)[\s\xa0]*\Z", before, re.IGNORECASE):
                continue
            _claim(m.start(), m.end())
            out.append(_reference(m.group(0), m.start(), m.end(), "INTERNAL",
                                   targets=[_target("Instrument")]))
            last_internal_unit = "Instrument"
            last_external = None  # a host self-naming resets "that Regulation" to the host

    # ONE ordered list of instrument mentions, built over
    # ``preceding_text + text`` (never ``out``, never scanned separately
    # per pass) — each entry is ``(position, kind, is_host, name)``.
    # ``preceding_text`` positions map to a NEGATIVE "virtual" offset
    # (``position - len(preceding_text)``) so they sort strictly before
    # every position in ``text`` while preserving their own real
    # left-to-right order (``preceding_text`` immediately precedes
    # ``text``).
    _VPRE = len(full_preceding)

    def _vpos_pre(p: int) -> int:
        return p - _VPRE

    _host_name_flexible_re = (
        re.compile(_flexible_name_pattern(host_instrument_name), re.IGNORECASE)
        if host_instrument_name else None)

    def _scan_mentions(span: str, virtual: bool) -> list:
        to_pos = _vpos_pre if virtual else (lambda p: p)
        found = [(to_pos(m.start()), m.group(0)) for m in _EXTERNAL_NAME_RE.finditer(span)]
        found += [(to_pos(m.start()), _usc_instrument_name(m.group(1)))
                  for m in _EXT_USC_TITLE_RE.finditer(span)]
        found += [(to_pos(m.start(1)), m.group(1))
                  for m in _RECITAL_HAVING_REGARD_TREATY_RE.finditer(span)]
        if _host_name_flexible_re is not None:
            found += [(to_pos(m.start()), host_instrument_name)
                      for m in _host_name_flexible_re.finditer(span)]
        return found

    # ONE lightweight amendment-quote scan — "for
    # “X” substitute “Y”", "for “X” there is substituted “Y”", "omit
    # “X”" — classifies each QUOTED span (the same three quote styles
    # the later ``_quote_spans`` scan recognises) as the amendment's OLD
    # (struck) text by the single word immediately before it ("for"/
    # "omit"). A mention inside an OLD span is NEVER an antecedent for
    # anaphora elsewhere in the sentence (R2: that text is being
    # replaced, not cited) — excluded from ``_mentions`` below.
    _amend_quote_re = re.compile(
        r"[‘“]([^’”]{1,800})[’”]"
        r"|(?<![A-Za-z])'([^']{1,800})'(?![A-Za-z])"
        r'|"([^"]{1,800})"')
    _amend_old_spans = []
    for _qm in _amend_quote_re.finditer(text):
        _before = text[:_qm.start()]
        _word_m = re.search(r"([A-Za-z]+)[\s\xa0]*\Z", _before)
        _prev_word = _word_m.group(1).lower() if _word_m else None
        if _prev_word in ("for", "omit"):
            _amend_old_spans.append((_qm.start(), _qm.end()))

    def _inside_amend_old_span(pos: int) -> bool:
        return any(s <= pos < e for s, e in _amend_old_spans)

    # The filter above excludes an OLD
    # (struck) span's mentions GLOBALLY — right for an anaphor OUTSIDE
    # that span (R2: struck text is not a citation), but wrong for an
    # anaphor INSIDE the very same span, which must still resolve
    # against the mentions that precede it there (the struck text is
    # read as ordinary prose from inside itself). ``_all_mentions`` is
    # the UNFILTERED list; ``_mentions`` stays the FILTERED
    # list for lookups made from OUTSIDE any OLD span.
    _all_mentions = sorted(
        [(p, _classify_instrument_kind(n), _is_host_mention(n), n)
         for p, n in (_scan_mentions(full_preceding, True) + _scan_mentions(text, False))],
        key=lambda t: t[0])
    _mentions = sorted(
        [t for t in _all_mentions
         if not (t[0] >= 0 and _inside_amend_old_span(t[0]))],
        key=lambda t: t[0])

    def _nearest_mention_before(pos: int, type_word: "Optional[str]" = None):
        """``(position, kind, is_host, name)`` of the NEAREST mention
        strictly before ``pos`` whose own KIND matches ``type_word``
        (or ANY kind, when ``type_word`` is ``None`` — the untyped
        "thereof" case) — or ``None`` when there is no such mention.
        Host mentions are NEVER excluded — they compete on recency like
        any other.

        the ONE ordered mention list is
        :data:`_mentions` (the bare standalone-shape scan) WIDENED, at
        lookup time, with every EXTERNAL reference ALREADY emitted into
        ``out`` by an earlier pass in THIS SAME call — a named treaty
        only reachable through a pinpoint-gated chain match ("Article 95
        of the Treaty establishing the European Community") is a real
        instrument MENTION too, even though its bare name alone is
        deliberately excluded from the standalone scan. Never a
        ``last_external``-shaped STATEFUL fallback (that side channel is
        removed) — this is the SAME mention-list mechanism, just backed
        by a second source of mentions."""
        target_kind = _TYPE_WORD_KIND.get(type_word.casefold()) if type_word else None
        if type_word and target_kind is None:
            return None
        # the widening (below) applies ONLY to
        # the UNTYPED ("thereof"/"thereto") lookup — a TYPED lookup
        # ("that Directive") keeps resolving through the bare
        # standalone-shape scan alone, unchanged from /10.
        live = [
            (ref["literal_start"], _classify_instrument_kind(ref["external_instrument"]),
             False, ref["external_instrument"])
            for ref in out
            if type_word is None and ref["kind"] == "EXTERNAL" and ref.get("external_instrument")
            and ref["external_instrument"] != "unnamed (see note)"
        ]
        # an anaphor found INSIDE an amendment's
        # OLD (struck) quoted span resolves against the UNFILTERED
        # mention list (mentions inside that same span, and before it,
        # per the normal nearest rule) — only an anaphor OUTSIDE every
        # OLD span uses the FILTERED list.
        source = _all_mentions if (pos >= 0 and _inside_amend_old_span(pos)) else _mentions
        best = None
        best_pos = -(1 << 62)
        for p, k, is_host, n in source + live:
            if p >= pos or p < best_pos:
                continue
            if target_kind is not None and k != target_kind:
                continue
            best = (p, k, is_host, n)
            best_pos = p
        return best

    def _nearest_mention_is_host(pos: int, type_word: "Optional[str]" = None) -> bool:
        best = _nearest_mention_before(pos, type_word)
        return bool(best is not None and best[2])

    def _consume_trailing_host_name_or_anaphora(start: int, end: int) -> int:
        """Every Pass 6 bare-chain loop already
        consumes a trailing EXPLICIT host naming
        (:func:`_consume_trailing_host_name`) right after it, so the WHOLE
        span becomes ONE reference — but NOT a trailing ANAPHORIC "of/to
        that Act/Regulation/..." ("Parts 5 to 7 of that Act"), which fell
        through unclaimed (then, for a BARE anaphor with no pinpoint of
        its own, dropped entirely under R1 — correct for a GENUINELY bare
        mention, but this one DOES carry a pinpoint, the chain just
        matched here). Tries the explicit-name consumer FIRST; only when
        that finds nothing does it check the anaphoric form, and only
        when the nearest mention of the declared kind IS the host."""
        new_end = _consume_trailing_host_name(text, end, host_instrument_name)
        if new_end != end:
            return new_end
        anaph = _OF_THAT_ANAPHORA_RE.match(text[end:])
        if anaph and _nearest_mention_is_host(start, anaph.group(1)):
            return end + anaph.end()
        return end

    def _nearest_external_before(pos: int, type_word: "Optional[str]" = None) -> "Optional[str]":
        # looks up the SAME ordered mention list
        # (:func:`_nearest_mention_before`) every anaphora caller uses —
        # the nearest preceding mention of the matching KIND (or any
        # kind, for the untyped "thereof" case). A HOST mention is never
        # a genuinely EXTERNAL antecedent (R1 governs it instead,
        # resolved by the caller via :func:`_nearest_mention_is_host`).
        best = _nearest_mention_before(pos, type_word)
        if best is None:
            return None
        _, _, is_host, name = best
        return None if is_host else name

    # R2 : the resolver detects quoted-amending-text
    # SPANS itself — EU drafting uses single curly quotes (‘…’, also
    # straight ' as a fallback); UK/US drafting uses double curly quotes
    # (“…”, also straight "). A bare pinpoint found strictly INSIDE one
    # of these spans, that does not itself name the host (R2's own host
    # branch, passes 0-2 above, already claims and classifies those), is
    # classified EXTERNAL to whatever instrument was named most recently
    # BEFORE the quote's own opening mark — never relying on a
    # caller-supplied designation.
    # a straight ``'`` must NEVER be read as a quote mark
    # when it is really a possessive/contraction apostrophe ("the
    # Commissioner's duty", "the person's rights") — PREFER typographic
    # quotes (‘…’/“…”, always unambiguous); a straight ``'`` counts as an
    # OPENING quote only at a position NOT preceded by a letter (an
    # apostrophe-s is always preceded by one), closed by a ``'`` NOT
    # followed by a letter (same guard, symmetric).
    _quote_spans = [
        (m.start(), m.end()) for m in re.finditer(
            r"[‘“]([^’”]{1,800})[’”]"
            r"|(?<![A-Za-z])'([^']{1,800})'(?![A-Za-z])"
            r'|"([^"]{1,800})"',
            text)
    ]

    def _quote_start_containing(pos: int) -> "Optional[int]":
        for start, end in _quote_spans:
            if start < pos < end:
                return start
        return None

    # R2 : an UNQUOTED amending chapeau — "In Regulation
    # (EU) 2018/1139, Article 17 is replaced by the following:" — names
    # the AMENDED instrument directly, with NO quote marks at all; a bare
    # pinpoint naming no instrument of its own, appearing in the REST of
    # that same sentence, still designates the named instrument (R2:
    # classify by what it designates). Each span runs from just after
    # the "In <instrument>," comma to the next full stop (or the end of
    # ``text``), with its own KNOWN antecedent (no nearest-before lookup
    # needed — the chapeau names it directly).
    _chapeau_spans = []
    for m in re.finditer(r"\bIn[\s\xa0]+(" + _EXTERNAL_NAME_RE.pattern + r"),[\s\xa0]*", text):
        start = m.end()
        # the chapeau span ends at "." OR ";" (or the
        # end of ``text``), whichever comes first — not only ".".
        candidates = [i for i in (text.find(".", start), text.find(";", start)) if i != -1]
        end = min(candidates) if candidates else len(text)
        _chapeau_spans.append((start, end, m.group(1)))

    def _chapeau_instrument_containing(pos: int) -> "Optional[str]":
        for start, end, instrument in _chapeau_spans:
            if start <= pos < end:
                return instrument
        return None

    def _emit_internal(literal: str, start: int, end: int, targets: list,
                        tags: "Optional[list]" = None,
                        external_target_override: "Optional[str]" = None) -> None:
        """Claim+append an ordinary INTERNAL reference — UNLESS ``start``
        falls inside a quoted-amending-text span OR an unquoted amending
        CHAPEAU span with a detectable (or caller-overridden) EXTERNAL
        antecedent, in which case R2 reroutes it to EXTERNAL instead (see
        the module notes above). The rerouted EXTERNAL reference's own
        ``external_target`` is whatever pinpoint the INTERNAL path would
        have assigned — the SAME chain, just redesignated — UNLESS the
        caller passes ``external_target_override`` :
        a RELATIVE reference's own resolved pinpoint ("Article 9(2)")
        is built by combining the bare suffix with THIS HOST's own
        ``enclosing_unit`` — reusing it as the ``external_target`` of a
        reference that a chapeau/quote just redesignated to a DIFFERENT
        instrument would wrongly claim that instrument's Article 9 is
        the same as the host's. The override is the bare, instrument
        -agnostic literal text instead ("paragraph 2"), never ``None``
        silently either."""
        nonlocal last_internal_unit, last_external
        antecedent = None
        # an EXPLICIT "of this Regulation/Directive/Act"
        # immediately after THIS span overrides both the quote-span and
        # the chapeau reroute — it is the text's own, more specific,
        # self-naming, never designated to whatever surrounding context
        # might otherwise suggest.
        explicit_self = re.match(
            r"\A[\s\xa0]*of[\s\xa0]+this[\s\xa0]+(?:Regulation|Directive|Act)\b",
            text[end:end + 40], re.IGNORECASE)
        quote_start = None if explicit_self else _quote_start_containing(start)
        chapeau = None
        if antecedent is None and not explicit_self:
            chapeau = _chapeau_instrument_containing(start)
            # R1/R2: a chapeau that names the HOST itself ("In
            # Regulation (EU) 2024/1689, Article 17 ... applies") does
            # NOT redesignate anything external — the host's own
            # self-naming (R1) already governs, resolved as INTERNAL
            # the ordinary way below.
            if chapeau and host_instrument_name and chapeau.startswith(host_instrument_name):
                chapeau = None
        # An EXPLICIT naming immediately
        # trailing THIS span ("Schedule 1 OF THE EXAMPLE REGISTRATION
        # ACT 1990") always wins over whatever instrument the
        # surrounding quote/chapeau CONTEXT would otherwise supply —
        # the mention list (or a chapeau) never overrides an explicit
        # naming the text carries right here. Scoped to the
        # quote/chapeau-reroute path only (never fires outside it,
        # since ordinary chain_patterns already claim their own
        # trailing "of <name>" before reaching here).
        if (quote_start is not None or chapeau is not None) and not explicit_self:
            ext_tail = _OF_EXTERNAL_RE.match(text[end:])
            if ext_tail:
                ext_name_text = (ext_tail.group(1) if ext_tail.group(1) is not None
                                  else ext_tail.group(2))
                if ext_name_text is not None:
                    usc_m = _EXT_USC_TITLE_RE.match(ext_name_text)
                    candidate = (_usc_instrument_name(usc_m.group(1)) if usc_m
                                 else _normalize_external_name(ext_name_text))
                    if not (host_instrument_name and _loose_name_match(candidate, host_instrument_name)):
                        new_end = end + ext_tail.end()
                        _claim(start, new_end)
                        target_pin = (external_target_override if external_target_override is not None
                                       else (targets[0]["pinpoint"] if targets else None))
                        out.append(_reference(text[start:new_end], start, new_end, "EXTERNAL",
                                               external_instrument=candidate, external_target=target_pin))
                        last_external = candidate
                        return
        if quote_start is not None:
            antecedent = quoted_amending_target or _nearest_external_before(quote_start)
        if antecedent is None and chapeau is not None:
            antecedent = chapeau
        if antecedent:
            _claim(start, end)
            target_pin = (external_target_override if external_target_override is not None
                           else (targets[0]["pinpoint"] if targets else None))
            out.append(_reference(literal, start, end, "EXTERNAL", external_instrument=antecedent,
                                   external_target=target_pin))
            last_external = antecedent
            return
        _claim(start, end)
        out.append(_reference(literal, start, end, "INTERNAL", targets=targets, hard_case_tags=tags))
        if targets:
            last_internal_unit = targets[-1]["pinpoint"]

    # Pass 2 — pinpoint chains (family-ordered) immediately followed by
    # "of <EXTERNAL INSTRUMENT>"/"to <EXTERNAL INSTRUMENT>" -> ONE
    # EXTERNAL reference spanning chain+instrument, pinpoint kept in
    # literal only (R7).
    chain_patterns = [_EU_ARTICLE_PARAGRAPH_RE, _EU_CHAIN_RE, _EU_ANNEX_RE, _EU_CHAPTER_SECTION_RE,
                      _UK_SCHEDULE_FIRST_RE, _UK_PARAGRAPH_OF_SCHEDULE_RE,
                      # plural/ranged forms tried BEFORE
                      # their singular siblings, so a trailing "of
                      # <instrument>"/"of that X" wraps the WHOLE plural
                      # span as ONE reference, not just its first member.
                      _SECTION_PLURAL_RE, _PARAGRAPH_PLURAL_RE, _DE_SS_PLURAL_RE,
                      # tried BEFORE
                      # _SECTION_CHAIN_RE for the SAME "claim the
                      # longer span first" reason.
                      _UK_SECTION_OF_OR_SCHEDULE_RE, _SECTION_SUBPIN_OR_RE,
                      _SECTION_CHAIN_RE, _SUBPARAGRAPH_ABS_RE, _DE_CHAIN_RE,
                      _DE_ARTIKEL_CHAIN_RE,
                      _PARAGRAPH_REL_RE, _POINT_REL_RE, _SUBSECTION_RE]
    for pat in chain_patterns:
        for m in pat.finditer(text):
            if _overlaps(m.start(), m.end()):
                continue
            tail = text[m.end():]
            ext = _OF_EXTERNAL_RE.match(tail)
            # EU drafting convention: "Article 16 TFEU"/"Article 6 TEU"/
            # "Article 52 Charter" names the TREATY/CHARTER DIRECTLY
            # after the number, with NO "of" at all.
            bare_treaty = None if ext else _BARE_TREATY_SUFFIX_RE.match(tail)
            # "Article 6 thereof" — "thereof" refers to the nearest
            # EXTERNAL instrument already named earlier in the sentence
            # (or ``preceding_text``); the WHOLE "Article 6 thereof"
            # span is then EXTERNAL to that instrument.
            thereof_m = None if (ext or bare_treaty) else _THEREOF_HERE_RE.match(tail.lstrip())
            # "thereof" resolves ONLY through the
            # SAME ordered mention list every other anaphora caller
            # uses (:func:`_nearest_mention_before`) — the earlier
            # ``_nearest_external_before(...) or last_external`` side
            # channel is REMOVED; a HOST mention nearest in the list
            # makes the WHOLE "<chain> thereof" span INTERNAL, pinpoint
            # the chain's own (never the "unnamed"/stateful-fallback
            # shape a separate scan produced).
            thereof_mention = _nearest_mention_before(m.start()) if thereof_m else None
            if thereof_m and thereof_mention is not None:
                _, _, thereof_is_host, thereof_name = thereof_mention
                lead_ws = len(tail) - len(tail.lstrip())
                end = m.end() + lead_ws + thereof_m.end()
                pin = _format_any_chain_pinpoint(pat, m.group(0), numbering_family)
                _claim(m.start(), end)
                if thereof_is_host:
                    out.append(_reference(text[m.start():end], m.start(), end, "INTERNAL",
                                           targets=[_target(pin)]))
                    last_internal_unit = pin
                else:
                    out.append(_reference(text[m.start():end], m.start(), end, "EXTERNAL",
                                           external_instrument=thereof_name, external_target=pin))
                    last_external = thereof_name
                continue
            # R2: "Chapter III, Section 2, of THAT REGULATION" immediately
            # after a R2 host self-naming (``last_internal_unit ==
            # "Instrument"``) -> the WHOLE span is INTERNAL, pinpoint the
            # CHAIN's own (never "Instrument" again — that would lose the
            # more specific unit the chain itself names).
            of_that_host = (_OF_THAT_HOST_RE.match(tail)
                             if not (ext or bare_treaty) and last_internal_unit == "Instrument" else None)
            if of_that_host:
                end = m.end() + of_that_host.end()
                pin = _format_any_chain_pinpoint(pat, m.group(0), numbering_family)
                _claim(m.start(), end)
                out.append(_reference(text[m.start():end], m.start(), end, "INTERNAL",
                                       targets=[_target(pin)]))
                last_internal_unit = pin
                continue
            # "section N of this title" — ONE reference,
            # never a split "section N" plus a separate "this title".
            # INTERNAL (no item for "this title" at all) when ``N`` is
            # among this file's OWN known section numbers
            # (``host_section_numbers``); otherwise EXTERNAL to
            # ``host_title_instrument`` (or the literal "this title"
            # when the number is not known), per the contract's own
            # "EXTERNAL unless the target section is in this file".
            of_this_title = (_OF_THIS_TITLE_RE.match(tail) if not (ext or bare_treaty) else None)
            if of_this_title:
                end = m.end() + of_this_title.end()
                pin = _format_any_chain_pinpoint(pat, m.group(0), numbering_family)
                # a PLURAL/listed chain ("sections 6502
                # and 6503 of this title") must check EVERY member's own
                # section number against ``host_section_numbers``, not
                # only the first — ``all()`` over every number the chain
                # names (a mixed in-file/out-of-file plural is NOT
                # exercised by any vector or benchmark source;
                # treated conservatively as "not fully in file" ->
                # EXTERNAL, documented as a known limit).
                # a bracketed sub-pinpoint ("(b)",
                # "(1)", "(A)") carries its OWN digits ("1") that are
                # NOT a second section number — "section 6502(b)(1)(A)
                # of this title" must check ONLY "6502" against
                # ``host_section_numbers``, never also "1". Strip every
                # parenthesised group before extracting section
                # numbers.
                sec_nums = re.findall(r"\d{1,4}", re.sub(r"\([^()]*\)", "", m.group(0)))
                member_statuses = (
                    [n in host_section_numbers for n in sec_nums]
                    if host_section_numbers is not None else [])
                in_file = bool(sec_nums) and host_section_numbers is not None and all(member_statuses)
                all_out = bool(sec_nums) and host_section_numbers is not None and not any(member_statuses)
                _claim(m.start(), end)
                # "sections 7744 and
                # 7750 of this title", with 7744 in file and 7750 not,
                # must split into an INTERNAL member and an EXTERNAL
                # member — never silently truncate to one target or
                # treat the WHOLE list as one kind.
                if pat is _SECTION_PLURAL_RE and len(sec_nums) > 1 and host_section_numbers is None:
                    # unchanged: with no host section-number set at
                    # all, EVERY listed member is its own ambiguous
                    # EXTERNAL reference (never merged into one).
                    prefix = "§" if numbering_family in ("us", "de") else "section"
                    member_spans = _section_plural_member_spans(m, end)
                    for num, mem_start, mem_end in member_spans:
                        mem_pin = f"{prefix} {num}"
                        instrument = host_title_instrument or "unnamed (see note)"
                        tags = None if host_title_instrument else ["ambiguous_reference"]
                        out.append(_reference(text[mem_start:mem_end], mem_start, mem_end,
                                               "EXTERNAL", external_instrument=instrument,
                                               external_target=mem_pin, hard_case_tags=tags))
                        last_external = instrument
                    continue
                # items 3 & 4: the OLD guard here
                # ("not in_file and not all_out") decided mixed-vs
                # -homogeneous from the WRITTEN endpoints alone — for
                # a RANGE token, that is blind to any flip strictly
                # BETWEEN the two written endpoints ("sections 6501
                # through 6503" with only 6502 out of file reads as
                # fully in_file from its endpoints, wrongly skipping
                # the split entirely). Always ask
                # :func:`_section_plural_range_groups` first — it now
                # expands every RANGE token fully before deciding
                # homogeneity — and only fall through to the
                # endpoints-only ``in_file``/``all_out`` single
                # -reference path below when IT says there is nothing
                # to split.
                if pat is _SECTION_PLURAL_RE and len(sec_nums) > 1 and host_section_numbers is not None:
                    prefix = "§" if numbering_family in ("us", "de") else "section"
                    range_groups = _section_plural_range_groups(m, end, host_section_numbers)
                    if range_groups is not None:
                        for is_in, nums, g_start, g_end in range_groups:
                            if is_in:
                                # a RANGE-expanded
                                # INTERNAL member carries its own
                                # ``expanded_from`` (the matched range
                                # text) — the SAME convention the
                                # homogeneous all-INTERNAL range case
                                # already uses; distinct from a plain
                                # LISTED member's own single pinpoint,
                                # which carries none. # "carries more than one member" is
                                # now the test (a merged/expanded run,
                                # regardless of which token(s) it
                                # drew from), not "came from a range
                                # token" (a single-member run from a
                                # range token's own WRITTEN endpoint is
                                # not itself expanded from anything).
                                expanded_from = m.group(0) if len(nums) > 1 else None
                                targets = [_target(f"{prefix} {n}", expanded_from=expanded_from)
                                           for n in nums]
                                out.append(_reference(text[g_start:g_end], g_start, g_end,
                                                       "INTERNAL", targets=targets))
                                last_internal_unit = targets[-1]["pinpoint"]
                            else:
                                instrument = host_title_instrument or "unnamed (see note)"
                                tags = None if host_title_instrument else ["ambiguous_reference"]
                                out.append(_reference(
                                    text[g_start:g_end], g_start, g_end, "EXTERNAL",
                                    external_instrument=instrument,
                                    external_target=_format_pinpoint_range(prefix, nums),
                                    hard_case_tags=tags))
                                last_external = instrument
                        continue
                    # ``range_groups is None`` here means every member
                    # this match actually expands to — including every
                    # RANGE token's IMPLIED members — shares ONE
                    # status; fall through to the single-reference
                    # ``in_file``/``all_out`` path below, which the
                    # WRITTEN-endpoints-only ``in_file``/``all_out``
                    # computed above correctly agrees with (a subset
                    # of a homogeneous set is itself homogeneous).
                if in_file:
                    targets = _chain_targets_for_internal(pat, m.group(0), numbering_family)
                    out.append(_reference(text[m.start():end], m.start(), end, "INTERNAL",
                                           targets=targets))
                    last_internal_unit = targets[-1]["pinpoint"] if targets else pin
                else:
                    # M6/R7: no host_title_instrument ->
                    # the text names no identifiable instrument at all,
                    # never the bare GLOSS "this title".
                    if host_title_instrument:
                        instrument = host_title_instrument
                        out.append(_reference(text[m.start():end], m.start(), end, "EXTERNAL",
                                               external_instrument=instrument, external_target=pin))
                    else:
                        instrument = "unnamed (see note)"
                        out.append(_reference(text[m.start():end], m.start(), end, "EXTERNAL",
                                               external_instrument=instrument, external_target=pin,
                                               hard_case_tags=["ambiguous_reference"]))
                    last_external = instrument
                continue
            # "Article N of this Convention"/"Protocol"/
            # "Treaty"/"Accord" — the generic-treaty-type analogue of the
            # "this title" branch above.
            of_this_generic = (_OF_THIS_GENERIC_TYPE_RE.match(tail)
                                if not (ext or bare_treaty) else None)
            if of_this_generic:
                end = m.end() + of_this_generic.end()
                pin = _format_any_chain_pinpoint(pat, m.group(0), numbering_family)
                type_word = of_this_generic.group(1)
                host_is_that_type = bool(
                    host_instrument_name and
                    re.search(r"\b" + re.escape(type_word) + r"\b", host_instrument_name, re.IGNORECASE))
                _claim(m.start(), end)
                if host_is_that_type:
                    out.append(_reference(text[m.start():end], m.start(), end, "INTERNAL",
                                           targets=[_target(pin)]))
                    last_internal_unit = pin
                else:
                    # R7: the text names NO identifiable instrument (the
                    # host is not that treaty type) — never a bare,
                    # truncated type word.
                    out.append(_reference(text[m.start():end], m.start(), end, "EXTERNAL",
                                           external_instrument="unnamed (see note)",
                                           external_target=pin,
                                           hard_case_tags=["ambiguous_reference"]))
                    last_external = "unnamed (see note)"
                continue
            # "Article 5 of that Regulation"/"Article 55
            # or 56 of that Regulation"/"section 406 of that Act" — the
            # GENERAL anaphoric-external-WITH-a-pinpoint case (distinct
            # from ``_OF_THAT_HOST_RE`` above, which only fires when the
            # chain follows an R2 HOST self-naming). ONE EXTERNAL
            # reference per LISTED member (never an INTERNAL pinpoint
            # plus a separate bare EXTERNAL mention) — each member's own
            # span is just its own number/chain text; the shared "of
            # that X" suffix trails the LAST member's span only, so the
            # whole citation is covered with NO overlap between members.
            of_that_anaphora = (_OF_THAT_ANAPHORA_RE.match(tail)
                                 if not (ext or bare_treaty or of_that_host) else None)
            if of_that_anaphora and host_instrument_name and \
                    _nearest_mention_is_host(m.start(), of_that_anaphora.group(1)):
                # R1: the NEAREST mention of this kind is the HOST — "of
                # that Act" designates the HOST, stays INTERNAL (the
                # chain's own pinpoint(s)), never wrapped as external.
                # a PLURAL/listed chain ("sections 38 and
                # 39 of that Act") gives ALL its members, not only the
                # first (:func:`_chain_targets_for_internal`, the SAME
                # full expansion the R2 host-by-number branch already
                # uses below).
                end = m.end() + of_that_anaphora.end()
                targets = _chain_targets_for_internal(pat, m.group(0), numbering_family, enclosing_unit)
                _claim(m.start(), end)
                out.append(_reference(text[m.start():end], m.start(), end, "INTERNAL",
                                       targets=targets))
                last_internal_unit = targets[-1]["pinpoint"] if targets else None
                continue
            if of_that_anaphora:
                antecedent_anaph = _nearest_external_before(m.start(), of_that_anaphora.group(1))
                # "Articles 55 to 58 of that Regulation" /
                # "Article 55 or 56 of that Regulation" is ONE
                # EXTERNAL reference, never split member-by-member
                # — EXTERNAL carries no ``targets`` either way (R7),
                # so there is nothing to gain from, and the gold
                # itself keeps the whole plural/ranged chain as ONE
                # literal.
                suffix_end = m.end() + of_that_anaphora.end()
                pin = _format_any_chain_pinpoint(pat, m.group(0), numbering_family)
                _claim(m.start(), suffix_end)
                # M5/B1: NO antecedent of the DECLARED
                # kind was named anywhere ("of that Directive" after
                # only a Regulation was ever named) — the text itself
                # identifies no instrument; R7 requires "unnamed (see
                # note)", never silently decomposing the chain+anaphora
                # span back into two unrelated matches (a bare INTERNAL
                # pinpoint plus a second, independently-resolved
                # standalone anaphora elsewhere).
                instrument = antecedent_anaph or "unnamed (see note)"
                out.append(_reference(text[m.start():suffix_end], m.start(), suffix_end,
                                       "EXTERNAL", external_instrument=instrument,
                                       external_target=pin,
                                       hard_case_tags=(None if antecedent_anaph
                                                        else ["ambiguous_reference"])))
                last_external = instrument
                continue
            if not ext and not bare_treaty:
                continue
            if bare_treaty:
                instrument = bare_treaty.group(1)
                end = m.end() + bare_treaty.end()
            else:
                instr_text = ext.group(1) if ext.group(1) is not None else ext.group(2)
                usc_m = _EXT_USC_TITLE_RE.match(instr_text)
                instrument = _usc_instrument_name(usc_m.group(1)) if usc_m else _normalize_external_name(instr_text)
                # R1 parity: "of Regulation (EU)
                # <host number>" still designates the HOST, not an
                # external instrument, even when wrapped by this same
                # "of X" grammar — claim the WHOLE span (chain + host
                # name) as ONE INTERNAL reference (the chain's own
                # pinpoint), so the host's own name text is never left
                # for Pass 3 to independently mis-claim as a standalone
                # EXTERNAL mention.
                # number-match and name-match are now
                # INDEPENDENT checks (previously the name check was an
                # ``elif`` nested under ``if host_instrument_number``,
                # so it never even ran when a number WAS given but its
                # own regex happened not to match a particular surface
                # form) — either one alone is sufficient to designate
                # the host.
                host_number_hit = (_host_instrument_re(host_instrument_number).match(tail)
                                    if host_instrument_number else None)
                if host_number_hit:
                        end = m.end() + host_number_hit.end()
                        # "Articles 6 and 7 of
                        # Regulation (EU) <host number>" must give BOTH
                        # members, not only the first — reuses the SAME
                        # number-expansion + sub-pin/suffix formatting
                        # pass6's own EU_CHAIN_RE handling already does.
                        if pat is _EU_CHAIN_RE:
                            suffix = _eu_chain_pinpoint(m.group(0))
                            sub = _article_subpin_suffix(m.group(0))
                            article_list_text = re.split(
                                r",?\s*(?:point|(?:first|second|third|fourth|fifth)\s+subparagraph)\b",
                                m.group(0), maxsplit=1, flags=re.IGNORECASE)[0]
                            nums = _expand_article_span(article_list_text)
                            many = len(nums) > 1
                            targets = [
                                _target(_eu_number_pinpoint(n, sub if n == nums[0] else "", suffix),
                                        m.group(0) if many else None)
                                for n in nums] if nums else [_target(m.group(0))]
                        elif pat in (_PARAGRAPH_REL_RE, _POINT_REL_RE, _SUBSECTION_RE):
                            # a RELATIVE reference
                            # ("paragraph 2", "point (a)", "subsection
                            # (b)") followed by "of <host name/number>"
                            # must resolve against the caller-supplied
                            # ``enclosing_unit`` the SAME way it already
                            # does with no "of X" suffix at all (Pass 7)
                            # — "paragraph 2, of Regulation (EU)
                            # 2024/1689" inside Article 9 resolves to
                            # "Article 9(2)", never the bare "paragraph
                            # 2".
                            label = {_PARAGRAPH_REL_RE: "paragraph", _POINT_REL_RE: "point",
                                      _SUBSECTION_RE: "subsection"}[pat]
                            pin, _tags = _resolve_relative(m.group(0), label, enclosing_unit, numbering_family)
                            targets = [_target(pin)]
                        else:
                            targets = [_target(_format_any_chain_pinpoint(pat, m.group(0), numbering_family))]
                        _claim(m.start(), end)
                        out.append(_reference(text[m.start():end], m.start(), end, "INTERNAL",
                                               targets=targets))
                        last_internal_unit = targets[-1]["pinpoint"]
                        continue
                # # the SAME R1 self-naming rule, by NAME rather than by EU
                # number — "paragraph 5(2) of Schedule 2 to the Data
                # Protection Act 2018" inside the Data Protection Act
                # 2018's OWN file designates the HOST, not an external
                # instrument, even though the bare "to <Act YYYY>"
                # grammar alone would flag it as one. Without this, the
                # WHOLE span was claimed as ONE EXTERNAL reference here,
                # but Pass 3's OWN bare-name scan then ALSO (correctly,
                # for an UNCLAIMED mention) matched the SAME "Data
                # Protection Act 2018" text found via anaphora elsewhere
                # in the sentence, producing a SECOND, OVERLAPPING
                # reference — the no-overlap property test's own
                # violation.
                elif host_instrument_name and _loose_name_match(instrument, host_instrument_name):
                    end = m.end() + ext.end()
                    targets = _chain_targets_for_internal(pat, m.group(0), numbering_family, enclosing_unit)
                    _claim(m.start(), end)
                    out.append(_reference(text[m.start():end], m.start(), end, "INTERNAL",
                                           targets=targets))
                    last_internal_unit = targets[-1]["pinpoint"]
                    continue
                # "the 2018 Act" —
                # a SHORT-YEAR-ONLY Act name with no instrument name word
                # of its own (:data:`_EXT_SHORT_YEAR_ACT_TAIL`) — IS the
                # host when its year equals the host's own
                # ``host_instrument_number`` (UK drafting convention:
                # the host's own number IS its year, e.g. "2018"). A
                # DIFFERENT year is still a different, external Act
                # .
                elif (_host_short_year and
                      re.fullmatch(r"(?:the" + _WS + r")?(\d{4})" + _WS + r"Act",
                                   instr_text.strip(), re.IGNORECASE) and
                      re.fullmatch(r"(?:the" + _WS + r")?(\d{4})" + _WS + r"Act",
                                   instr_text.strip(), re.IGNORECASE).group(1) ==
                      _host_short_year):
                    end = m.end() + ext.end()
                    targets = _chain_targets_for_internal(pat, m.group(0), numbering_family, enclosing_unit)
                    _claim(m.start(), end)
                    out.append(_reference(text[m.start():end], m.start(), end, "INTERNAL",
                                           targets=targets))
                    last_internal_unit = targets[-1]["pinpoint"]
                    continue
                end = m.end() + ext.end()
            _claim(m.start(), end)
            # ``external_target`` — the "(instrument,
            # target provision)" requirement — is the chain's OWN
            # pinpoint, parsed the SAME way the INTERNAL path would have
            # formatted it (the bare-treaty case has no pinpoint chain of
            # its OWN pointing INTO the treaty, so it stays ``None``).
            ext_target = None if bare_treaty else _format_any_chain_pinpoint(pat, m.group(0), numbering_family)
            out.append(_reference(text[m.start():end], m.start(), end, "EXTERNAL",
                                   external_instrument=instrument, external_target=ext_target))
            last_external = instrument

    # Pass 3 — EXTERNAL instrument named on its own (no pinpoint chain
    # before it): "TFEU", "TEU", "Charter", "Regulation (EU).../Directive
    # ..." bare, "the X Act YYYY", "UK GDPR".
    for m in _EXTERNAL_NAME_RE.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        # the SAME deferral Pass 1 applies to a bare
        # HOST naming — a mention immediately preceded by a
        # pinpoint-chain-shaped ending ("Chapter 2 of Part 2 of the
        # <host name>") is left UNCLAIMED here when it names the HOST,
        # so a later chain-aware pass (the UK "Chapter N of Part M",
        # Part/Chapter, or Schedule patterns below) can claim the WHOLE
        # span as one INTERNAL reference instead of this bare scan
        # claiming just the instrument-name tail first and leaving an
        # orphaned, wrongly-EXTERNAL reference to the host's own name.
        # A second deferral — for when the host's own name is merely a
        # PREFIX of this LONGER match ("Online Safety Act 2023
        # (Commencement No. 2) Regulations 2024", :data:`_EXT_SI_UNDER_ACT_TAIL`)
        # — is unnecessary (a mutant removing it changes NO vector's
        # outcome, and no input could be constructed that makes it the
        # deciding factor): whenever a Part/Chapter chain precedes the
        # match, ``chain_is_part_or_chapter`` below already defers,
        # independent of the host's name; whenever no such chain
        # precedes it, the EARLIER host-self-naming pass (R1/R2, above)
        # always claims the SHORTER exact host name first regardless of
        # what follows it, so this bare scan's own (longer, overlapping)
        # match is already skipped by the ``_overlaps`` check at the top
        # of this loop before this condition is ever reached.
        host_is_match_or_prefix = host_instrument_name and _loose_name_match(
            m.group(0), host_instrument_name)
        # the SAME deferral is needed for a NON-host name
        # too, specifically right after a bare "Part N"/"Chapter N" —
        # the UK_PART_RE/UK_CHAPTER_RE loop (Pass 6) now claims its OWN
        # "of <OTHER instrument>" tail (the SI-under-Act case above),
        # which OVERLAPS this bare scan's otherwise-independent claim on
        # the SAME trailing name ("Part 16 of the Financial Services and
        # Markets Act 2000" claimed by BOTH passes) unless this scan
        # defers too. Narrowly scoped to "Part N"/"Chapter N" (never a
        # blanket defer for every chain ending) so the OTHER Pass 6 bare
        # loops — which have no such "of OTHER instrument" claim of
        # their own — are not affected.
        # The nested "Chapter M of Part N of" shape must ALSO defer
        # here: :data:`_UK_CHAPTER_OF_PART_RE`'s own Pass 6 loop claims
        # a trailing "of <NAMED instrument>" the same way the bare
        # Part/Chapter loop already does, so this chain is deferred
        # here exactly like any other "Part N of"/"Chapter N of"
        # ending, letting that loop claim the
        # WHOLE nested span as one EXTERNAL reference instead of a
        # bare, un-hosted name plus a stranded INTERNAL pinpoint.
        _before = text[:m.start()]
        chain_is_part_or_chapter = re.search(
            r"\b(?:Part|Chapter)" + _WS + r"\d{1,3}[\s\xa0]*,?[\s\xa0]*(?:of|to)(?:" +
            _WS + r"the)?[\s\xa0]*\Z", _before, re.IGNORECASE)
        if host_is_match_or_prefix or chain_is_part_or_chapter:
            before = text[:m.start()]
            if re.search(r"(?:\d{1,4}[A-Za-z]?\b|\)|subparagraph|sentence|paragraph|point)"
                         r"[\s\xa0]*,?[\s\xa0]*(?:of|to)(?:" + _WS +
                         r"the)?[\s\xa0]*\Z", before, re.IGNORECASE):
                continue
        # A BARE (no pinpoint of its own) naming
        # found entirely inside an amendment's OLD (struck) quoted span
        # carries no pinpoint and designates nothing being cited here —
        # no item (the OLD text's own mentions are not antecedents
        # either, per the ``_mentions`` filter above; this is the SAME
        # rule applied to the bare mention itself).
        if _inside_amend_old_span(m.start()):
            continue
        _claim(m.start(), m.end())
        instrument = _normalize_external_name(m.group(0))
        out.append(_reference(m.group(0), m.start(), m.end(), "EXTERNAL",
                               external_instrument=instrument))
        last_external = instrument

    # Pass 3b — "title N" (US Code) named on its own, mapped to "N U.S.C.".
    for m in _EXT_USC_TITLE_RE.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        _claim(m.start(), m.end())
        instrument = _usc_instrument_name(m.group(1))
        out.append(_reference(m.group(0), m.start(), m.end(), "EXTERNAL",
                               external_instrument=instrument))
        last_external = instrument

    # Pass 5 — R2 bare pinpoint inside quoted amending text, naming
    # neither the host nor any other external instrument explicitly
    # (e.g. "paragraph 3" alone, quoted from the amended instrument) is
    # now handled AUTOMATICALLY by :func:`_emit_internal`'s own quote
    # -span detection in Passes 6/7 below  — the
    # resolver detects the quote marks itself; ``quoted_amending_target``
    # is kept ONLY as an explicit override for a caller that wants to
    # force the designation without quote marks present in ``text``.

    # Pass 6 — absolute internal pinpoint chains with NO following "of
    # <instrument>" (the ordinary internal case): EU Article(s), Annex,
    # Chapter/Section, UK Schedule/Part/Chapter/section, DE § chain, US §
    # chain. Plurals/ranges/or-lists expand to one target PER member here.
    for m in (_EU_CHAIN_RE.finditer(text)):
        if _overlaps(m.start(), m.end()):
            continue
        # "Article 89 GDPR" — bare
        # "GDPR" (unlike "UK GDPR", :data:`_EXT_UK_GDPR`) names no
        # recognised EXTERNAL shape (KNOWN LIMITS); emitting the chain
        # as a wrong-kind INTERNAL pinpoint INTO the host would be
        # worse than no item at all, so this exact shape is left
        # UNCLAIMED — no reference at all (R7's own under-recall, never
        # a wrong kind).
        if re.match(r"[\s\xa0]*GDPR\b", text[m.end():], re.IGNORECASE):
            continue
        suffix = _eu_chain_pinpoint(m.group(0))
        sub = _article_subpin_suffix(m.group(0))
        # Only the "Article(s) N[, M][ to K]..." PREFIX feeds the number
        # expander — a trailing ", point (x)"/"subparagraph" suffix (held
        # separately in ``suffix``) must never be re-read as another
        # article number (e.g. "Article 2, point (7)" must not expand to
        # article 7 too).
        article_list_text = re.split(r",?\s*(?:point|(?:first|second|third|"
                                      r"fourth|fifth)\s+subparagraph)\b",
                                      m.group(0), maxsplit=1, flags=re.IGNORECASE)[0]
        nums = _expand_article_span(article_list_text)
        if not nums:
            continue
        targets = []
        many = len(nums) > 1
        for n in nums:
            expanded_from = m.group(0) if many else None
            targets.append(_target(_eu_number_pinpoint(n, sub if n == nums[0] else "", suffix),
                                    expanded_from))
        _emit_internal(m.group(0), m.start(), m.end(), targets)

    # PLURAL/listed "Annexes I and II" — tried BEFORE
    # the singular form.
    for m in _EU_ANNEX_PLURAL_RE.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        romans = _ROMAN_LIST_TOKEN_RE.findall(m.group(0))
        many = len(romans) > 1
        targets = [_target(f"Annex {r}", m.group(0) if many else None) for r in romans]
        _emit_internal(m.group(0), m.start(), m.end(), targets)

    for m in _EU_ANNEX_RE.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        pin = _format_annex_pinpoint(m.group(0))
        _emit_internal(m.group(0), m.start(), m.end(), [_target(pin)])

    # "Section 2 of Chapter III" (written inner-first)
    # -> outer-first pinpoint "Chapter III, Section 2" — tried BEFORE
    # the simpler "Chapter <roman>[, Section N]" pattern below, so it
    # claims the WHOLE nested span first.
    for m in _EU_SECTION_OF_CHAPTER_RE.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        sm = re.match(r"Section" + _WS + r"(\d{1,3})\b" + _WS + r"of" + _WS +
                       r"Chapter" + _WS + r"([IVXLCDM]+)\b", m.group(0), re.IGNORECASE)
        pin = f"Chapter {sm.group(2)}, Section {sm.group(1)}"
        _emit_internal(m.group(0), m.start(), m.end(), [_target(pin)])

    for m in _EU_CHAPTER_SECTION_RE.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        pin = _format_chapter_section_pinpoint(m.group(0))
        _emit_internal(m.group(0), m.start(), m.end(), [_target(pin)])

    # "paragraph 9 of Part 3 of Schedule 3" -> "Schedule 3, Part 3,
    # paragraph 9" — tried BEFORE the plain "paragraph N of Schedule M"
    # pattern, so it claims the longer, fully-nested span first.
    for m in _UK_PARAGRAPH_OF_PART_OF_SCHEDULE_RE.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        pm = re.match(
            r"paragraph" + _WS + r"(\d{1,3}[A-Za-z]?)\b(" + _SUBPINS + r")" + _WS + r"of" + _WS +
            r"Part" + _WS + r"(\d{1,3})\b" + _WS + r"of" + _WS + r"Schedule" + _WS + r"(\d{1,3})\b",
            m.group(0), re.IGNORECASE)
        para, subs, part_n, sched_n = pm.group(1), pm.group(2).replace(" ", ""), pm.group(3), pm.group(4)
        pin = f"Schedule {sched_n}, Part {part_n}, paragraph {para}{subs}"
        _emit_internal(m.group(0), m.start(), m.end(), [_target(pin)])

    for m in _UK_SCHEDULE_FIRST_RE.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        pin = _format_schedule_paragraph(m.group(0), first_form=True)
        # consume a bare trailing HOST naming
        # ("Schedule 12 to the Online Safety Act 2023") the same way
        # the Chapter-of-Part/Part/Chapter chains above do.
        end = _consume_trailing_host_name_or_anaphora(m.start(), m.end())
        _emit_internal(text[m.start():end], m.start(), end, [_target(pin)])

    for m in _UK_PARAGRAPH_OF_SCHEDULE_RE.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        pin = _format_schedule_paragraph(m.group(0), first_form=False)
        end = _consume_trailing_host_name_or_anaphora(m.start(), m.end())
        _emit_internal(text[m.start():end], m.start(), end, [_target(pin)])

    # PLURAL/listed "Schedules 5, 6 and 7" — tried
    # BEFORE the singular bare form.
    for m in _UK_SCHEDULE_PLURAL_RE.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        members = _expand_generic_list(m.group(0))
        many = len(members) > 1
        targets = [_target(f"Schedule {mem}", m.group(0) if many else None) for mem in members]
        # consume a bare trailing HOST
        # naming ("Schedules 5 and 6 to the Online Safety Act 2023")
        # the SAME way the bare Schedule/Part/Chapter loops already do
        # — without this, the host name after a PLURAL schedule list
        # was left unclaimed (silently dropped, no item of its own).
        end = _consume_trailing_host_name_or_anaphora(m.start(), m.end())
        _emit_internal(text[m.start():end], m.start(), end, targets)

    for m in _UK_SCHEDULE_BARE_RE.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        pin = re.sub(_WS, " ", m.group(0)).strip()
        end = _consume_trailing_host_name_or_anaphora(m.start(), m.end())
        _emit_internal(text[m.start():end], m.start(), end, [_target(pin)])

    # "Chapter 2 of Part 7" -> "Part 7, Chapter 2" — tried BEFORE the
    # bare Part/Chapter loop below.
    for m in _UK_CHAPTER_OF_PART_RE.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        cm = re.match(r"Chapter" + _WS + r"(\d{1,3})\b" + _WS + r"of" + _WS + r"Part" + _WS +
                      r"(\d{1,3})\b", m.group(0), re.IGNORECASE)
        pin = f"Part {cm.group(2)}, Chapter {cm.group(1)}"
        # A trailing "of <NAMED instrument>" ("Chapter 2 of Part 3 of
        # the Example Act 1996") names a DIFFERENT, EXTERNAL instrument
        # the SAME way the bare Part/Chapter loop below already checks
        # for — without this check, the trailing name falls through
        # unclaimed by this loop, Pass 3 claims it bare on its own, and
        # the Chapter-of-Part pinpoint is left stranded as a separate,
        # un-hosted INTERNAL reference.
        tail = text[m.end():]
        ext = _OF_EXTERNAL_RE.match(tail)
        ext_name = (ext.group(1) if ext and ext.group(1) is not None
                    else (ext.group(2) if ext else None))
        if ext and ext_name and not (
                host_instrument_name and _loose_name_match(ext_name, host_instrument_name)):
            end = m.end() + ext.end()
            instrument = _normalize_external_name(ext_name)
            _claim(m.start(), end)
            out.append(_reference(text[m.start():end], m.start(), end, "EXTERNAL",
                                   external_instrument=instrument, external_target=pin))
            last_external = instrument
            continue
        # consume a bare HOST naming trailing right
        # after this chain ("Chapter 2 of Part 2 of the Data Protection
        # Act 2018") as part of the SAME reference, rather than leaving
        # it for a later pass to mis-claim as a standalone EXTERNAL
        # mention of the host's own name.
        end = _consume_trailing_host_name_or_anaphora(m.start(), m.end())
        _emit_internal(text[m.start():end], m.start(), end, [_target(pin)])

    # PLURAL/ranged "Parts 5 to 7" —
    # tried BEFORE the singular Part/Chapter loop below, so it claims
    # the WHOLE plural span (one reference, one target PER member)
    # rather than the first member alone.
    for plural_re, label in ((_UK_PART_PLURAL_RE, "Part"), (_UK_CHAPTER_PLURAL_RE, "Chapter")):
        for m in plural_re.finditer(text):
            if _overlaps(m.start(), m.end()):
                continue
            members = _expand_generic_list(m.group(0))
            many = len(members) > 1
            # A trailing "of that Schedule"/
            # "of that Part" — a SUB-UNIT anaphor, never recognised by
            # the generic instrument-level trailing-anaphora consumer
            # above — resolves against the NEAREST preceding mention of
            # the SAME sub-unit word (never the nearest INTERNAL
            # pinpoint of ANY kind: "that Schedule" is never read as if
            # it were a "Part"). "Parts 1 and 2 of that Schedule" is
            # then ONE INTERNAL reference, each member combined with
            # the named Schedule's own number.
            outer_m = re.match(
                r"[\s\xa0]*,?[\s\xa0]*of[\s\xa0]+(?:that|such)[\s\xa0]+(Schedule|Part|Chapter)\b",
                text[m.end():], re.IGNORECASE)
            if outer_m and outer_m.group(1).lower() != label.lower():
                outer_word = outer_m.group(1).capitalize()
                outer_num = None
                best_at = -1
                for ref in out:
                    if ref["literal_start"] >= m.start() or ref["kind"] != "INTERNAL" or not ref["targets"]:
                        continue
                    cand = ref["targets"][-1]["pinpoint"]
                    cm = re.match(outer_word + r"\s+(\S+)", cand, re.IGNORECASE)
                    if cm and ref["literal_start"] > best_at:
                        outer_num, best_at = cm.group(1), ref["literal_start"]
                if outer_num is not None:
                    end = m.end() + outer_m.end()
                    targets = [_target(f"{outer_word} {outer_num}, {label} {mem}",
                                        m.group(0) if many else None) for mem in members]
                    _emit_internal(text[m.start():end], m.start(), end, targets)
                    continue
            targets = [_target(f"{label} {mem}", m.group(0) if many else None) for mem in members]
            end = _consume_trailing_host_name_or_anaphora(m.start(), m.end())
            # ``_consume_trailing_host_name_or_
            # anaphora`` only consumes a trailing "of/to that Act" when
            # the nearest mention of that type IS the host (so ``end``
            # is still unchanged here otherwise) — but a pinpoint-
            # bearing anaphora ("Parts 5 to 7 of that Act") is never a
            # BARE mention (R1's own "drop it" rule doesn't apply): it
            # must stay in the SAME reference as its own pinpoint chain,
            # never fall through unclaimed to the later bare-anaphora
            # pass, which has no pinpoint of its own to attach.
            if end == m.end():
                anaph = _OF_THAT_ANAPHORA_RE.match(text[end:])
                if anaph:
                    mention = _nearest_mention_before(m.start(), anaph.group(1))
                    instrument = mention[3] if mention is not None else "unnamed (see note)"
                    ext_end = end + anaph.end()
                    pin = ", ".join(f"{label} {mem}" for mem in members)
                    _claim(m.start(), ext_end)
                    out.append(_reference(
                        text[m.start():ext_end], m.start(), ext_end, "EXTERNAL",
                        external_instrument=instrument, external_target=pin,
                        hard_case_tags=(None if mention is not None else ["ambiguous_reference"])))
                    last_external = instrument
                    continue
            _emit_internal(text[m.start():end], m.start(), end, targets)

    for word_re, label in ((_UK_PART_RE, "Part"), (_UK_CHAPTER_RE, "Chapter")):
        for m in word_re.finditer(text):
            if _overlaps(m.start(), m.end()):
                continue
            num = re.search(_NUM, m.group(0)).group(0)
            pin = f"{label} {num}"
            # "Part 5 of the Online
            # Safety Act 2023 (Commencement No. 2) Regulations 2024" —
            # the "of <name>" tail names a DIFFERENT, SUBORDINATE
            # instrument (the host name plus an SI continuation,
            # :data:`_EXT_SI_UNDER_ACT_TAIL`), not the host itself.
            # Pass 3's own bare-name scan already DEFERS claiming this
            # combined name (its "before" guard, extended below, now
            # also covers "the host name used as a PREFIX of a longer
            # SI name" the same way it already covers an exact host
            # match) — so by the time this loop runs, the WHOLE name is
            # still unclaimed and safe to check and claim HERE, never a
            # second, overlapping match.
            tail = text[m.end():]
            ext = _OF_EXTERNAL_RE.match(tail)
            ext_name = (ext.group(1) if ext and ext.group(1) is not None
                        else (ext.group(2) if ext else None))
            if ext and ext_name and not (
                    host_instrument_name and _loose_name_match(ext_name, host_instrument_name)):
                end = m.end() + ext.end()
                instrument = _normalize_external_name(ext_name)
                _claim(m.start(), end)
                out.append(_reference(text[m.start():end], m.start(), end, "EXTERNAL",
                                       external_instrument=instrument, external_target=pin))
                last_external = instrument
                continue
            # consume a bare trailing HOST naming
            # ("Part 5 of the Online Safety Act 2023") the SAME way the
            # Chapter-of-Part chain above does.
            end = _consume_trailing_host_name_or_anaphora(m.start(), m.end())
            _emit_internal(text[m.start():end], m.start(), end, [_target(pin)])

    # PLURAL/ranged/or-listed §§ ("§§ 3 bis 5", "§§ 3
    # und 4") — tried BEFORE the singular DE chain below.
    for m in _DE_SS_PLURAL_RE.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        members = _expand_generic_list(m.group(0))
        many = len(members) > 1
        targets = [_target(f"§ {mem}", m.group(0) if many else None) for mem in members]
        _emit_internal(m.group(0), m.start(), m.end(), targets)

    for m in _DE_CHAIN_RE.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        pin = _format_de_pinpoint(m.group(0))
        _emit_internal(m.group(0), m.start(), m.end(), [_target(pin)])

    # PLURAL/ranged/or-listed "sections N, M and K"/"sections N to M" —
    # tried BEFORE the singular section chain below.
    for m in _SECTION_PLURAL_RE.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        members = _expand_generic_list(m.group(0))
        many = len(members) > 1
        prefix = "§" if numbering_family in ("us", "de") else "section"
        targets = [_target(f"{prefix} {mem}", m.group(0) if many else None) for mem in members]
        _emit_internal(m.group(0), m.start(), m.end(), targets)

    for m in _SECTION_CHAIN_RE.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        pin = _format_section_pinpoint(m.group(0), numbering_family)
        _emit_internal(m.group(0), m.start(), m.end(), [_target(pin)])

    for m in _SUBPARAGRAPH_ABS_RE.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        if enclosing_unit:
            pin = f"{enclosing_unit}{m.group(0)[len('Subparagraph'):].strip().replace(' ', '')}"
            tags = None
        else:
            pin = re.sub(_WS, " ", m.group(0)).strip()
            tags = ["ambiguous_reference"]
        _emit_internal(m.group(0), m.start(), m.end(), [_target(pin)], tags)

    # PLURAL/ranged/or-listed "paragraphs 1 and 2"/
    # "paragraphs 1 to 3" — RELATIVE, resolved against ``enclosing_unit``
    # the SAME way the singular form is, one target PER member. Tried
    # BEFORE the singular relative paragraph pass below.
    for m in _PARAGRAPH_PLURAL_RE.finditer(text):
        if _overlaps(m.start(), m.end()):
            continue
        members = _expand_generic_list(m.group(0))
        many = len(members) > 1
        if enclosing_unit:
            targets = [_target(f"{enclosing_unit}({mem})", m.group(0) if many else None)
                       for mem in members]
            tags = None
        else:
            targets = [_target(f"paragraph {mem}", m.group(0) if many else None) for mem in members]
            tags = ["ambiguous_reference"]
        _emit_internal(m.group(0), m.start(), m.end(), targets, tags)

    # Pass 7 — RELATIVE references (resolve against ``enclosing_unit``):
    # "paragraph N", "point (x)", "subsection (x)".
    for pat, label in ((_PARAGRAPH_REL_RE, "paragraph"), (_POINT_REL_RE, "point"),
                       (_SUBSECTION_RE, "subsection")):
        for m in pat.finditer(text):
            if _overlaps(m.start(), m.end()):
                continue
            pin, tags = _resolve_relative(m.group(0), label, enclosing_unit, numbering_family)
            bare_literal = re.sub(_WS, " ", m.group(0)).strip()
            _emit_internal(m.group(0), m.start(), m.end(), [_target(pin)], tags,
                           external_target_override=bare_literal)

    # Pass 4 (moved here, AFTER passes 5-7, deliberately — an anaphoric
    # "that Article"/"that Regulation"/"thereof" needs the ABSOLUTE
    # internal/relative references later in the SAME sentence to already
    # be in ``out`` so its antecedent lookup can see them) — anaphora:
    # "that/such Regulation/Directive/Act/title" (EXTERNAL, resolves to
    # the nearest NAMED external instrument before this point — in THIS
    # text or in ``preceding_text``); "thereof" (same); "that
    # Article/Schedule/subparagraph/section" (INTERNAL, resolves to the
    # nearest internal unit named so far).
    anaphora_hits = []
    for m in _ANAPHORA_EXTERNAL_RE.finditer(text):
        anaphora_hits.append((m.start(), m.end(), "EXT", m, m.group(1)))
    for m in _ANAPHORA_INTERNAL_RE.finditer(text):
        anaphora_hits.append((m.start(), m.end(), "INT", m, None))
    for m in _THEREOF_HERE_RE.finditer(text):
        # "thereof" carries NO type word of its own — the UNTYPED
        # lookup .
        anaphora_hits.append((m.start(), m.end(), "EXT", m, None))
    anaphora_hits.sort(key=lambda t: t[0])
    # "that X"/"thereof" resolve to
    # the most recent INSTRUMENT-DESIGNATION event, never to "whichever
    # INTERNAL reference happens to be nearest": a
    # plain "Article 7" citation — which designates NO instrument at
    # all — wrongly won against a genuinely later-named external
    # instrument). A designation is either (a) an EXTERNAL reference
    # already in ``out``, or (b) an INTERNAL reference whose OWN literal
    # text contains the host's name (an R1 host self-naming, by name or
    # by number) — built FRESH from ``out`` each time, since ``out``
    # keeps growing as later anaphora in the SAME sentence are resolved.
    def _nearest_designation(pos: int, type_word: "Optional[str]" = None) -> "tuple":
        # HOST-vs-EXTERNAL competition uses the SAME
        # ordered mention list every anaphora caller uses
        # (:func:`_nearest_mention_before`) — a bare host self-naming
        # competes on recency exactly like any other mention, never
        # filtered out. When the nearest mention of this kind IS the
        # host, the PINPOINT "that X"/"thereof" resolves TO is whichever
        # pinpoint the most recent INTERNAL reference naming the host
        # directly already carries (an explicit "Article 46 of
        # Regulation (EU) 2016/679"-shaped citation earlier in the same
        # sentence) — a bare host mention carries no pinpoint of its
        # own to adopt.
        target_kind = _TYPE_WORD_KIND.get(type_word.casefold()) if type_word else None
        _NEG_INF = -(1 << 62)
        best_host, best_host_at = None, _NEG_INF
        for ref in out:
            if ref["literal_start"] >= pos:
                continue
            if ref["kind"] == "INTERNAL" and ref["targets"] and host_instrument_name and \
                    host_instrument_name.casefold() in ref["literal"].casefold() and \
                    ref["literal_start"] > best_host_at:
                best_host, best_host_at = ref["targets"][-1]["pinpoint"], ref["literal_start"]
        if target_kind is not None and host_instrument_name and \
                _classify_instrument_kind(host_instrument_name) != target_kind:
            best_host, best_host_at = None, _NEG_INF
        mention = _nearest_mention_before(pos, type_word)
        if mention is None:
            return ("HOST", best_host) if best_host_at > _NEG_INF else (None, None)
        m_pos, _, is_host, name = mention
        if is_host:
            # the NEAREST
            # mention of the matching kind IS the host -> the bare
            # anaphor is a self-reference, R1's "no item" rule, even
            # when no earlier EXPLICIT host pinpoint exists to adopt
            # (``best_host`` stays ``None`` in that case; the caller's
            # ``kind == "HOST"`` check alone, never gated on
            # ``value is not None``, is what signals "no item").
            return "HOST", best_host
        if best_host_at > m_pos:
            return "HOST", best_host
        return "EXT", name

    for start, end, kind_hint, m, type_word in anaphora_hits:
        if _overlaps(start, end):
            continue
        antecedent_int = None  # for the "that Article/Schedule/..." INTERNAL branch only
        antecedent_int_at = -1
        # "that Article/Schedule/subparagraph/
        # section" resolves against the NEAREST INTERNAL pinpoint of
        # the SAME sub-unit word — never the nearest INTERNAL pinpoint
        # of ANY kind ("that Schedule" is never read as if it were a
        # "Part" just because a Part was the most recently cited unit).
        type_word_int = m.group(1).lower() if kind_hint == "INT" else None
        for ref in out:
            if ref["literal_start"] < start and ref["kind"] == "INTERNAL" and ref["targets"] \
                    and ref["literal_start"] > antecedent_int_at:
                cand_pin = ref["targets"][-1]["pinpoint"]
                if type_word_int is not None and not cand_pin.lower().startswith(type_word_int):
                    continue
                antecedent_int = cand_pin
                antecedent_int_at = ref["literal_start"]
        fallback_int = last_internal_unit
        if type_word_int is not None and fallback_int and not fallback_int.lower().startswith(type_word_int):
            fallback_int = None
        antecedent_int = antecedent_int or fallback_int
        _claim(start, end)
        if kind_hint == "EXT":
            # "that Regulation/Directive/Act/title" / "thereof": resolve
            # to the most recent DESIGNATION — EXTERNAL to a named
            # instrument, or INTERNAL when the host was named more
            # recently (R1) — falling back to ``last_external`` (seeded
            # from ``preceding_text``) only for the UNTYPED ("thereof")
            # case. M5/B1: a TYPED lookup ("that Directive")
            # NEVER falls back to the stateful, unfiltered
            # ``last_external`` — it checks ``preceding_text`` filtered
            # by the SAME kind, then R7's "unnamed (see note)".
            kind, value = _nearest_designation(start, type_word)
            if kind == "HOST":
                # A BARE "that Act" with NO pinpoint of its OWN
                # designates the host — R1's bare-self-reference rule
                # applies exactly as it already does for "this Act"/a
                # bare host self-naming: NO item at all, never an
                # INTERNAL echo of an UNRELATED earlier pinpoint
                # ("Part 2") that this mention never itself named, and
                # never an EXTERNAL "unnamed (see note)" either — the
                # kind alone (``"HOST"``), never gated on whether an
                # earlier explicit host pinpoint happened to exist,
                # is what signals "no item". The span stays claimed
                # (above) so nothing else re-reads it.
                continue
            elif type_word is None and kind is None:
                # a bare "thereof"/"thereto" with
                # NO mention of ANY kind before it (via the SAME
                # unified mention list) resolves to nothing — it is
                # ordinary prose ("the property and the proceeds
                # thereof"), not a citation, and is NOT an item. Only a
                # TYPED lookup ("that Directive") still falls through to
                # R7's "unnamed (see note)" when no antecedent of its
                # declared kind exists.
                continue
            else:
                # "value" is already the nearest mention
                # of the matching kind across ``preceding_text`` AND
                # ``text`` (:func:`_nearest_designation`, built on the
                # SAME unified mention list) — no separate fallback
                # scan needed. Covers the ``kind == "HOST"`` case with
                # no usable pinpoint too (a bare host self-naming — R6
                # fallback).
                instrument = value or "unnamed (see note)"
                out.append(_reference(m.group(0), start, end, "EXTERNAL", external_instrument=instrument,
                                       hard_case_tags=(None if instrument != "unnamed (see note)"
                                                        else ["ambiguous_reference"])))
                last_external = instrument
        else:
            pin = antecedent_int or m.group(1).capitalize()
            tags = None if antecedent_int else ["ambiguous_reference"]
            out.append(_reference(m.group(0), start, end, "INTERNAL",
                                   targets=[_target(pin)], hard_case_tags=tags))
            last_internal_unit = pin

    # Pass 8 — R6: "So in original" footnotes are read LITERALLY. The
    # footnote's own SUGGESTED target ("[So in original. Probably should
    # be section 5(a)(3).]") is NOT a
    # reference item at all — it is an editorial NOTE about what the
    # text probably should have said, not a citation the operative text
    # itself makes; only the REAL literal text reference in the
    # operative sentence (outside the brackets) is an item, flagged
    # ``ambiguous_reference``. Any reference whose span falls ENTIRELY
    # inside a "[... So in original ...]" bracket is DROPPED from the
    # output (never emitted, never counted toward ``+1 structural``);
    # one strictly OUTSIDE the brackets but nearby is flagged instead.
    bracket_spans = [(bm.start(), bm.end()) for bm in re.finditer(
        r"\[[^\[\]]*so\s+in\s+original[^\[\]]*\]", text, re.IGNORECASE)]
    if bracket_spans:
        out = [ref for ref in out
               if not any(bs <= ref["literal_start"] and ref["literal_end"] <= be
                          for bs, be in bracket_spans)]
    for m in _SO_IN_ORIGINAL_RE.finditer(text):
        window = (max(0, m.start() - 80), m.end())
        for ref in out:
            if window[0] <= ref["literal_start"] < window[1]:
                ref.setdefault("hard_case_tags", [])
                if "ambiguous_reference" not in ref["hard_case_tags"]:
                    ref["hard_case_tags"].append("ambiguous_reference")

    out.sort(key=lambda r: r["literal_start"])
    return out


def _format_any_chain_pinpoint(pat: "re.Pattern", literal: str, numbering_family: str = "uk") -> str:
    """Dispatches ``literal`` (one :data:`chain_patterns` member's own
    match text) to that family's own pinpoint formatter — used by the R2
    "of Regulation (EU) <host number>"/"of that Regulation" wraps, which
    need the chain's pinpoint regardless of WHICH family matched it."""
    if pat is _EU_ARTICLE_PARAGRAPH_RE:
        return _format_eu_article_paragraph_pinpoint(literal)
    if pat is _EU_CHAIN_RE:
        article_list_text = re.split(r",?\s*(?:point|(?:first|second|third|"
                                      r"fourth|fifth)\s+subparagraph)\b",
                                      literal, maxsplit=1, flags=re.IGNORECASE)[0]
        nums = _expand_article_span(article_list_text)
        if not nums:
            return re.sub(_WS, " ", literal).strip()
        return _eu_number_pinpoint(nums[0], _article_subpin_suffix(literal), _eu_chain_pinpoint(literal))
    if pat is _EU_ANNEX_RE:
        return _format_annex_pinpoint(literal)
    if pat is _EU_CHAPTER_SECTION_RE:
        return _format_chapter_section_pinpoint(literal)
    if pat is _UK_SCHEDULE_FIRST_RE:
        return _format_schedule_paragraph(literal, first_form=True)
    if pat is _UK_PARAGRAPH_OF_SCHEDULE_RE:
        return _format_schedule_paragraph(literal, first_form=False)
    if pat is _SECTION_SUBPIN_OR_RE:
        num = re.search(r"\d{1,4}[A-Za-z]?", literal).group(0)
        first_mem = re.search(_SUBPIN, literal).group(0)
        prefix = "§" if numbering_family in ("us", "de") else "section"
        return f"{prefix} {num}{first_mem}"
    if pat is _UK_SECTION_OF_OR_SCHEDULE_RE:
        sec_m = re.search(r"\d{1,4}[A-Za-z]?\b" + _SUBPINS, literal, re.IGNORECASE)
        prefix = "§" if numbering_family in ("us", "de") else "section"
        return f"{prefix} {sec_m.group(0)}" if sec_m else re.sub(_WS, " ", literal).strip()
    if pat in (_UK_PART_RE, _UK_CHAPTER_RE):
        label = "Part" if pat is _UK_PART_RE else "Chapter"
        num = re.search(_NUM, literal).group(0)
        return f"{label} {num}"
    if pat is _SECTION_CHAIN_RE:
        return _format_section_pinpoint(literal, numbering_family)
    if pat is _DE_CHAIN_RE:
        return _format_de_pinpoint(literal)
    if pat is _DE_ARTIKEL_CHAIN_RE:
        return _format_de_artikel_pinpoint(literal)
    if pat is _SECTION_PLURAL_RE:
        members = _expand_generic_list(literal)
        prefix = "§" if numbering_family in ("us", "de") else "section"
        return f"{prefix} {members[0]}" if members else re.sub(_WS, " ", literal).strip()
    if pat is _PARAGRAPH_PLURAL_RE:
        members = _expand_generic_list(literal)
        return f"paragraph {members[0]}" if members else re.sub(_WS, " ", literal).strip()
    if pat is _DE_SS_PLURAL_RE:
        members = _expand_generic_list(literal)
        return f"§ {members[0]}" if members else re.sub(_WS, " ", literal).strip()
    return re.sub(_WS, " ", literal).strip()


def _chain_targets_for_internal(pat: "re.Pattern", literal: str, numbering_family: str,
                                 enclosing_unit: "Optional[str]" = None) -> list:
    """the FULL multi-target expansion for a
    :data:`chain_patterns` member, used by the R1 host-match branches
    (which — unlike the EXTERNAL wraps, R7 — DO carry ``targets``) so a
    plural/ranged chain followed by the host's own name/number gives
    ALL its members, not only the first."""
    if pat is _SECTION_PLURAL_RE:
        prefix = "§" if numbering_family in ("us", "de") else "section"
        return [_target(f"{prefix} {mem}", literal) for mem in _expand_generic_list(literal)]
    if pat is _PARAGRAPH_PLURAL_RE:
        base = enclosing_unit
        if base:
            return [_target(f"{base}({mem})", literal) for mem in _expand_generic_list(literal)]
        return [_target(f"paragraph {mem}", literal) for mem in _expand_generic_list(literal)]
    if pat is _DE_SS_PLURAL_RE:
        return [_target(f"§ {mem}", literal) for mem in _expand_generic_list(literal)]
    if pat is _SECTION_SUBPIN_OR_RE:
        num = re.search(r"\d{1,4}[A-Za-z]?", literal).group(0)
        prefix = "§" if numbering_family in ("us", "de") else "section"
        members = [m.group(0) for m in re.finditer(r"(?:" + _SUBPIN + r")+", literal)]
        return [_target(f"{prefix} {num}{mem}", literal) for mem in members]
    if pat is _UK_SECTION_OF_OR_SCHEDULE_RE:
        prefix = "§" if numbering_family in ("us", "de") else "section"
        sec_m = re.search(r"\d{1,4}[A-Za-z]?\b" + _SUBPINS, literal, re.IGNORECASE)
        sched_m = re.search(r"Schedule" + _WS + r"\d{1,3}\b" + _SUBPINS, literal, re.IGNORECASE)
        targets = []
        if sec_m:
            targets.append(_target(f"{prefix} {sec_m.group(0)}", literal))
        if sched_m:
            targets.append(_target(re.sub(_WS, " ", sched_m.group(0)).strip(), literal))
        return targets or [_target(re.sub(_WS, " ", literal).strip())]
    return [_target(_format_any_chain_pinpoint(pat, literal, numbering_family))]


def _chain_member_spans(pat: "re.Pattern", text: str, m: "re.Match",
                         numbering_family: str = "uk") -> list:
    """B3 — the anaphoric-external-with-a-pinpoint case's
    own per-MEMBER spans: for :data:`_EU_CHAIN_RE`, one ``(member_text,
    abs_start, abs_end)`` tuple PER number in the list/range (never
    overlapping each other); for every other chain pattern, ONE member
    covering the whole match (no internal list to split)."""
    if pat is _EU_CHAIN_RE:
        # NOTE: a "to"-RANGE combined with an anaphoric external suffix
        # ("Articles 55 to 58 of that Regulation") is not expanded
        # member-by-member here — each LISTED (comma/and/or) member gets
        # its own span, in the real source text, but a range's own
        # IMPLIED intermediate members have no span of their own to
        # point at; only the two WRITTEN endpoints become members (a
        # documented, narrower scope than the comma/and/or list case).
        article_list_text = re.split(r",?\s*(?:point|(?:first|second|third|"
                                      r"fourth|fifth)\s+subparagraph)\b",
                                      m.group(0), maxsplit=1, flags=re.IGNORECASE)[0]
        members = []
        for i, tm in enumerate(_ARTICLE_LIST_TOKEN_RE.finditer(article_list_text)):
            n = int(tm.group(2))
            # the FIRST member's own span starts at the chain's own
            # start (covering the leading "Article(s)" keyword); every
            # later LISTED member's span starts at its own number token
            # (the keyword is not repeated per member in "Articles 55 or
            # 56").
            abs_start = m.start() if i == 0 else m.start() + tm.start(2)
            abs_end = m.start() + tm.end(0)
            members.append((f"Article {n}", abs_start, abs_end))
        return members or [(m.group(0), m.start(), m.end())]
    return [(_format_any_chain_pinpoint(pat, m.group(0), numbering_family), m.start(), m.end())]


#: the anaphora "that <Type>" surface word, mapped to
#: a TYPE-NEUTRAL "kind" — never compared by substring-in-name (a US
#: title's own mapped name, "18 U.S.C.", contains no "title" substring
#: at all; matching by name string silently found NOTHING for every
#: US-family antecedent and let the pinpoint fall through to the
#: wrong — or no — antecedent).
_TYPE_WORD_KIND = {"regulation": "regulation", "directive": "directive",
                   "act": "act", "title": "title"}


#: one (pattern, kind) entry per instrument keyword —
#: used to classify by the name's HEAD noun (the LAST/rightmost keyword
#: occurrence), never by "first keyword found anywhere in the string".
#: "Regulation of Investigatory Powers Act 2000" names an ACT (the head
#: noun at the end of the name) even though the word "Regulation" also
#: occurs, earlier, inside the name itself — checking "Regulation"
#: before "Act" (the OLD, order-of-checks behaviour) wrongly classified
#: every such name as a Regulation.
_KIND_WORD_PATTERNS = (
    (re.compile(r"U\.S\.C\.\s*\Z"), "title"),
    (re.compile(r"\bRegulation\b", re.IGNORECASE), "regulation"),
    (re.compile(r"\bDirective\b", re.IGNORECASE), "directive"),
    (re.compile(r"\bRecommendation\b", re.IGNORECASE), "recommendation"),
    (re.compile(r"\b(?:TFEU|TEU|Charter|Convention|Protocol|Treaty|Accord)\b", re.IGNORECASE), "treaty"),
    (re.compile(r"\b(?:Act|Code|Ordinance|Statute|Law)\b", re.IGNORECASE), "act"),
    (re.compile(r"(?:gesetz(?:es|buche?s?)?)\Z", re.IGNORECASE), "act"),
    (re.compile(r"(?:vertrags?|abkommens?)\Z", re.IGNORECASE), "treaty"),
    (re.compile(r"ordnung\Z", re.IGNORECASE), "act"),
)


def _classify_instrument_kind(name: "Optional[str]") -> "Optional[str]":
    """The KIND a named external instrument belongs to, derived from
    its OWN name text's STRUCTURAL shape — never from matching a
    caller-supplied type word against the name string. Used so "that
    Act"/"that Directive"/"that Regulation"/"that title" anaphora
    matches the antecedent of the SAME kind regardless of which
    family's drafting convention named it .

    the head
    is the FIRST instrument keyword in the name that is not ITSELF
    inside an "of/on/to/implementing ..." complement —
    "Convention on the Law of the Sea" is a treaty (the LATER "of"
    belongs to "the Law of the Sea", a complement of "Convention",
    not a second keyword occurrence that wins); "Protocol to the
    Children Act 1989" is a treaty, not an act, even though its own
    "to" complement ends in "Act 1989" — ``to``/``on``/
    ``implementing`` complements never override the first keyword.
    ONE narrow exception, spec/SPEC.md §8a.1: an ``of`` complement
    that is ITSELF shaped like a complete title ending in "<kind>
    YEAR" ("Regulation of Investigatory Powers Act 2000") promotes
    THAT trailing keyword to the head instead — the real UK
    convention this name actually follows, where "Regulation of
    Investigatory Powers" is the Act's own subject-matter title, not
    a second, competing instrument name."""
    if not name:
        return None
    matches = sorted(
        ((m.start(), m.end(), kind)
         for pattern, kind in _KIND_WORD_PATTERNS for m in pattern.finditer(name)),
        key=lambda t: t[0])
    if not matches:
        return "other"
    first_start, first_end, first_kind = matches[0]
    of_tail = re.match(r"\s+of\b", name[first_end:], re.IGNORECASE)
    if of_tail:
        complement = name[first_end + of_tail.end():]
        comp_matches = sorted(
            ((m.start(), m.end(), kind)
             for pattern, kind in _KIND_WORD_PATTERNS for m in pattern.finditer(complement)),
            key=lambda t: t[0])
        if comp_matches:
            c_start, c_end, c_kind = comp_matches[-1]
            if re.match(r"\s*\d{4}\s*\Z", complement[c_end:]):
                return c_kind
    return first_kind


def _last_external_instrument(text: str) -> "Optional[str]":
    """The LAST external-instrument-shaped name in ``text`` (used to seed
    anaphora when the antecedent was named in ``preceding_text``, not in
    the sentence under scan itself)."""
    last = None
    for m in _EXTERNAL_NAME_RE.finditer(text):
        last = m.group(0)
    for m in _EXT_USC_TITLE_RE.finditer(text):
        last = _usc_instrument_name(m.group(1))
    return last


def _format_annex_pinpoint(literal: str) -> str:
    parts = re.split(_WS, re.sub(r",", "", literal).strip())
    # "Annex I Section B" / "Annex I point 5 fifth indent" -> "Annex I,
    # Section B" / "Annex I, point 5, fifth indent".
    out = [f"Annex {parts[1]}"]
    i = 2
    while i < len(parts):
        if parts[i].lower() in ("section", "point"):
            # the contract's own pinpoint format keeps
            # "point" LOWER-case ("Annex III, point 5") but "Section"
            # capitalised — ``.capitalize()`` on EVERY word wrongly
            # produced "Point 5".
            word = "Section" if parts[i].lower() == "section" else "point"
            out.append(f"{word} {parts[i + 1]}")
            i += 2
        elif parts[i].lower().endswith("indent"):
            out.append(f"{parts[i - 1]} {parts[i]}")
            i += 1
        else:
            i += 1
    return ", ".join(out)


def _format_chapter_section_pinpoint(literal: str) -> str:
    m = re.match(r"Chapter" + _WS + r"([IVXLCDM]+)\b(?:\s*,?\s*Section" + _WS + r"(\d{1,3}))?",
                 literal, re.IGNORECASE)
    pin = f"Chapter {m.group(1)}"
    if m.group(2):
        pin += f", Section {m.group(2)}"
    return pin


def _format_schedule_paragraph(literal: str, first_form: bool) -> str:
    """the PREVIOUS version scraped every digit run in
    ``literal`` with a bare ``re.findall(_NUM, ...)`` — which also found
    the digits INSIDE a sub-pinpoint ("paragraph 8(1)(o) of Schedule 3"
    has digit runs 8, 1, 3; the old code took ``nums[1]`` == "1" as the
    Schedule number, not "3"). Anchored, position-specific regexes fix
    this: the paragraph number and its own sub-pinpoints are captured
    TOGETHER, immediately after "paragraph"; the Schedule number is
    captured separately, immediately after "Schedule"."""
    if first_form:
        m = re.match(
            r"Schedule" + _WS + r"(\d{1,3})\b\s*,?\s*paragraph" + _WS +
            r"(\d{1,3}[A-Za-z]?)\b(" + _SUBPINS + r")", literal, re.IGNORECASE)
        sched, para, subs = m.group(1), m.group(2), m.group(3)
    else:
        m = re.match(
            r"paragraph" + _WS + r"(\d{1,3}[A-Za-z]?)\b(" + _SUBPINS + r")\s+of\s+Schedule" +
            _WS + r"(\d{1,3})\b", literal, re.IGNORECASE)
        para, subs, sched = m.group(1), m.group(2), m.group(3)
    subs = subs.replace(" ", "")
    return f"Schedule {sched}, paragraph {para}{subs}"


def _format_de_pinpoint(literal: str) -> str:
    sec = re.search(r"§+\s*(\d{1,4}[a-z]?)", literal, re.IGNORECASE)
    # "Absatz" (spelled out) normalises to "Abs." — the
    # contract's own pinpoint format always abbreviates.
    abs_ = re.search(r"(?:Abs\.|\bAbsatz\b)" + _WS + r"(\d{1,3})", literal, re.IGNORECASE)
    # "\bSatz\b" (word boundary on BOTH sides): "Absatz" itself contains
    # the substring "satz" — without the leading boundary, re.search
    # would match THAT "satz" and steal "Absatz 1"'s own number as if it
    # were "Satz"'s .
    satz = re.search(r"\bSatz\b" + _WS + r"(\d{1,3})", literal, re.IGNORECASE)
    nr = re.search(r"Nr\." + _WS + r"(\d{1,3})", literal, re.IGNORECASE)
    pin = f"§ {sec.group(1)}"
    if abs_:
        pin += f" Abs. {abs_.group(1)}"
    if satz:
        pin += f" Satz {satz.group(1)}"
    if nr:
        pin += f" Nr. {nr.group(1)}"
    return pin


def _format_de_artikel_pinpoint(literal: str) -> str:
    """:data:`_DE_ARTIKEL_CHAIN_RE`'s own
    pinpoint — "Artikel 9 Absatz 1" -> "Artikel 9 Abs. 1" (the same
    Absatz->Abs. abbreviation :func:`_format_de_pinpoint` already
    applies, kept on the "Artikel" keyword rather than "§" since German
    drafting uses "Artikel", never "§", for an EU act's own numbering)."""
    art = re.search(r"\bArtikel" + _WS + r"(\d{1,3}[a-z]?)\b", literal, re.IGNORECASE)
    abs_ = re.search(r"(?:Abs\.|\bAbsatz\b)" + _WS + r"(\d{1,3})", literal, re.IGNORECASE)
    satz = re.search(r"\bSatz\b" + _WS + r"(\d{1,3})", literal, re.IGNORECASE)
    pin = f"Artikel {art.group(1)}" if art else re.sub(_WS, " ", literal).strip()
    if abs_:
        pin += f" Abs. {abs_.group(1)}"
    if satz:
        pin += f" Satz {satz.group(1)}"
    return pin


def _format_section_pinpoint(literal: str, numbering_family: str = "uk") -> str:
    """the pinpoint PREFIX follows the FAMILY, not the
    literal keyword the text happened to use — ``"section 6502(b)(1)(A)"``
    in the US family gives ``"§ 6502(b)(1)(A)"`` (the contract's own US
    pinpoint format), while the same literal in the UK/generic family
    keeps ``"section N(...)"``."""
    num = re.search(r"\d{1,4}[A-Za-z]?", literal).group(0)
    subs = "".join(re.findall(_SUBPIN, literal))
    prefix = "§" if numbering_family in ("us", "de") else "section"
    return f"{prefix} {num}{subs}"


def _resolve_relative(literal: str, label: str, enclosing_unit: "Optional[str]",
                       numbering_family: str) -> tuple:
    """A RELATIVE reference's own pinpoint, anchored to ``enclosing_unit``.
    EU: "paragraph 1, point (b)" against enclosing "Article 7" ->
    "Article 7(1), point (b)". US/UK "subsection (a)(1)" against
    enclosing "§ 230"/"section 6502" -> "§ 230(a)(1)"/"section 6502(a)(1)".
    No ``enclosing_unit`` -> best-effort bare pinpoint, flagged
    ``ambiguous_reference``."""
    nums = re.findall(_NUM, literal)
    letters = re.findall(_SUBPIN, literal)
    if not enclosing_unit:
        bare = re.sub(_WS, " ", literal).strip()
        return bare, ["ambiguous_reference"]
    if label == "paragraph":
        num = nums[0] if nums else ""
        point_suffix = ""
        pm = re.search(r"point" + _WS + r"(\(\s*[0-9a-z]{1,3}\s*\))", literal, re.IGNORECASE)
        if pm:
            point_suffix = f", point {pm.group(1).replace(' ', '')}"
        return f"{enclosing_unit}({num}){point_suffix}", None
    if label == "point":
        letter = letters[0] if letters else ""
        if numbering_family == "eu":
            return f"{enclosing_unit}, point {letter}", None
        return f"{enclosing_unit}{letter}", None
    if label == "subsection":
        subs = "".join(letters)
        return f"{enclosing_unit}{subs}", None
    bare = re.sub(_WS, " ", literal).strip()
    return bare, None


def clause_cue_point_from_profile(
        sentence: str, base_fact: "Optional[Mapping]" = None, profile_doc: "Optional[Mapping]" = None,
        self_article_number: "Optional[int]" = None, host_instrument_number: "Optional[str]" = None,
        enclosing_unit: "Optional[str]" = None, numbering_family: str = "eu",
        host_instrument_name: "Optional[str]" = None,
        whole_host_unit: "Optional[str]" = None, preceding_text: str = "",
        enclosing_units: "Optional[dict]" = None, host_title_instrument: "Optional[str]" = None,
        host_section_numbers: "Optional[set]" = None,
) -> dict:
    """Residual convenience, mirroring
    ``five_d_nd.match.combine_scores_from_profile`` /
    ``five_d_nd.point.point_from_contributions_from_profile`` — the §16
    ``xref_resolver`` field reaches :func:`clause_cue_contributions`/
    :func:`cross_reference_links` through the SAME convenience-wrapper
    shape those other modules already use, so a caller holding a
    resolution-profile DOCUMENT, not
    its already-unpacked fields, has one call to make). Wires
    ``clause_cue_saturation``, ``relational_suppression_scale`` AND
    ``xref_resolver`` straight from the resolved profile into
    :func:`clause_cue_point`. ``xref_resolver`` is read with
    ``.get(..., "article-v1")`` because the field is deliberately absent
    from :data:`five_d_nd.profile.DEFAULTS` (§16) — "absent means
    article-v1" is asserted HERE, the one consuming-code seam, never by
    ``profile.py`` itself. ``profile_doc`` is NOT validated here — call
    ``five_d_nd.profile.profile_violations`` first.
    """
    from . import profile as _profile
    resolved = _profile.resolve_profile(profile_doc or {"profile_id": "default"})
    return clause_cue_point(
        sentence, base_fact, saturation=resolved["clause_cue_saturation"],
        self_article_number=self_article_number,
        relational_suppression_scale=resolved["relational_suppression_scale"],
        host_instrument_number=host_instrument_number,
        xref_resolver=resolved.get("xref_resolver", DEFAULT_XREF_RESOLVER),
        enclosing_unit=enclosing_unit, numbering_family=numbering_family,
        host_instrument_name=host_instrument_name, whole_host_unit=whole_host_unit,
        preceding_text=preceding_text, enclosing_units=enclosing_units,
        host_title_instrument=host_title_instrument,
        host_section_numbers=host_section_numbers)


def cross_reference_links_from_profile(
        text: str, source_id: str, profile_doc: "Optional[Mapping]" = None,
        self_article_number: "Optional[int]" = None, host_instrument_number: "Optional[str]" = None,
        enclosing_unit: "Optional[str]" = None, numbering_family: str = "eu",
        host_instrument_name: "Optional[str]" = None,
        whole_host_unit: "Optional[str]" = None, preceding_text: str = "",
        enclosing_units: "Optional[dict]" = None, host_title_instrument: "Optional[str]" = None,
        host_section_numbers: "Optional[set]" = None,
) -> list:
    """Residual convenience, same shape as
    :func:`clause_cue_point_from_profile` — wires ``xref_resolver``
    straight from the resolved profile into :func:`cross_reference_links`.
    """
    from . import profile as _profile
    resolved = _profile.resolve_profile(profile_doc or {"profile_id": "default"})
    return cross_reference_links(
        text, source_id, self_article_number=self_article_number,
        host_instrument_number=host_instrument_number,
        xref_resolver=resolved.get("xref_resolver", DEFAULT_XREF_RESOLVER),
        enclosing_unit=enclosing_unit, numbering_family=numbering_family,
        host_instrument_name=host_instrument_name, whole_host_unit=whole_host_unit,
        preceding_text=preceding_text, enclosing_units=enclosing_units,
        host_title_instrument=host_title_instrument,
        host_section_numbers=host_section_numbers)
