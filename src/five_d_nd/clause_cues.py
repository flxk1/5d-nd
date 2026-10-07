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
    behaviour for ITS OWN number."""
    return re.compile(
        r"\A\s*of\s+(?:(?:(?!this\b|the\b)[A-Za-z]+\s+)*)Regulation\s*"
        r"(?:\(\s*EU\s*\)\s*)?(?:No\s*)?" + re.escape(host_instrument_number) + r"\b",
        re.IGNORECASE)
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


def cross_reference_links(
    text: str, source_id: str, self_article_number: "Optional[int]" = None,
    host_instrument_number: "Optional[str]" = None,
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
    """
    out = []
    for n in cross_reference_targets(text, self_article_number, host_instrument_number):
        out.append({
            "s": source_id,
            "p": "cross_references",
            "o": f"Article {n}",
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
    """
    if not isinstance(text, str):
        raise ValueError("clause_cue_contributions() requires a string")
    out = {d: 0 for d in DIMENSIONS}
    for dim in ("causal", "intentional", "temporal", "structural"):
        out[dim] = count_cue_hits(text, dim)
    cross_refs = cross_reference_targets(text, self_article_number, host_instrument_number)
    if cross_refs:
        out["structural"] += len(cross_refs)
    relational_count = count_cue_hits(text, "relational")
    n_other = out["causal"] + out["intentional"] + out["temporal"] + out["structural"]
    out["relational"] = relational_effective(relational_count, n_other, relational_suppression_scale)
    return out


def combined_contributions(
        sentence: str, base_fact: "Optional[Mapping]" = None,
        self_article_number: "Optional[int]" = None,
        relational_suppression_scale: "int | float" = DEFAULT_RELATIONAL_SUPPRESSION_SCALE,
        host_instrument_number: "Optional[str]" = None,
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
    document alone).
    """
    raw = clause_cue_contributions(sentence, self_article_number, relational_suppression_scale,
                                    host_instrument_number)
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
                      ) -> dict:
    """Convenience: :func:`combined_contributions` run straight through the
    UNCHANGED §11 point formula (``five_d_nd.point.point_from_contributions``),
    with this layer's own default saturation/relational-suppression-scale
    unless a caller (or a resolution profile, via ``clause_cue_saturation``/
    ``relational_suppression_scale``) overrides them. Imported lazily to
    avoid a module-load-time cycle with ``point.py``.

    ``host_instrument_number`` (e.g. ``"2016/679"``
    for GDPR) is CALLER-SUPPLIED DOCUMENT METADATA, forwarded to
    :func:`combined_contributions`/:func:`cross_reference_targets` —
    never a resolution-profile field, because it is a property of the
    one document being checked, not a tunable shared across documents.
    """
    from .point import point_from_contributions
    raw = combined_contributions(sentence, base_fact, self_article_number, relational_suppression_scale,
                                  host_instrument_number)
    return point_from_contributions(raw, saturation=saturation)
