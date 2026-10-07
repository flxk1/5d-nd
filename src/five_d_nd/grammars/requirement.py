# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""EXAMPLE nD grammar — a requirement/absence grammar (§9), graft D+.

Ported from a build comparison's own candidate D+ graft (integrating the
winning design and grafts — see
``docs/decisions/0007-clause-cue-layer-and-example-grammars.md``: "D+'s
requirement/absence grammar as an nD grammar"). NOT 5D (§1's scope is
unchanged) — a worked EXAMPLE of §9's contract for a DIFFERENT shape of
check than the term grammar (``five_d_nd.grammars.term``): some
obligations are a LIST of required elements, not a single predicate
(GDPR Art. 22(3) is the canonical example). A plain 5D point or a term-nD
tag-set can tell you a text IS ABOUT automated decision-making; neither
can, by itself, tell you a text is MISSING one of the three safeguards the
obligation requires — that needs a requirement grammar: a registry of
(trigger concept -> required concept set), checked by LEXICAL ABSENCE,
not presence.

**Rules are DATA, not code.** The (trigger -> required) mapping lives in
``requirement_rules.json`` (packaged alongside this module), loaded by
:func:`load_ruleset` and PINNED BY A SHA-256 DIGEST
(:func:`ruleset_digest`, via ``five_d_nd.grounding.digest`` — the same
canonical-JSON/sha256 machinery every other digest in this package uses).
Nothing in :func:`check` branches on an obligation id in Python code —
every rule is read from the pinned ruleset document, and a new obligation
is added by EDITING THE DATA, never by adding a new `if`.

**Negation is THREE-STATE, not binary — the design decision that stops
the negation arms race.** A deterministic lexical grammar cannot, in
general, DECIDE negation — tightening the negator/exemption rules trades
one class of false positive for a class of false negative (a clause-wide
negation design measured FN 11/30, FP 8/96 on a probe set, against FN
6/30, FP 23/96 before it: fewer false positives, more false negatives,
not a net improvement). The fix is NOT another round of tightening — it
is to stop pretending the lexical signal is always decisive. Each
concept's own state over a text collection is now THREE-VALUED:

* ``present`` — some occurrence of the concept's cue fires with NO
  negator in scope (after the exemptions below).
* ``uncertain`` — some occurrence fires, but EVERY occurrence has a
  negator (or a negating predicate, or "neither/nor") in scope. The
  concept is NEVER silently collapsed to either `present` or `absent`
  here — a human (or a further, non-lexical check) should look.
* ``absent`` — no occurrence of the concept's cue fires anywhere in the
  text collection at all (this is the ONLY state this grammar reports
  with any real confidence — a word that never appears cannot be
  present).

:func:`check` returns ``present``/``uncertain``/``missing`` (the sorted
lists for the three states, over the rule's own ``required_concepts``),
``triggered`` (a trigger concept fired AFFIRMATIVELY — i.e. ``present``,
never merely ``uncertain``), ``trigger_uncertain`` (a trigger concept's
ONLY occurrences were negated — the requirement MAY still apply; this
flag exists so a caller never silently skips the check on that basis),
``all_present`` (``True`` iff triggered, every required concept is
``present``, and NONE is ``uncertain``; ``False`` iff triggered with any
concept ``uncertain`` or ``missing``; ``None`` when not triggered at
all — the requirement does not apply, so absence is moot), and
``needs_review`` (``True`` iff any required concept is ``uncertain`` OR
``trigger_uncertain`` is set — this is the field a host should route to a
human).

**``all_present`` is LEXICAL PRESENCE ONLY, never a compliance verdict —
the three-state design does not relax this scope note.** This is a
deterministic scan over a closed cue table; it has no model of legal
sufficiency, of a safeguard offered in bad faith, or of a safeguard
lexically present but practically illusory. **A conforming consumer of
this grammar MUST NOT present ``all_present: true`` as a finding of
legal compliance** — at most, a first-pass filter or a prompt for human
review (``needs_review`` exists for exactly that routing).

**Negation is CONSERVATIVE and SENTENCE-SCOPED — the design decision to
stop trying to classify negation correctly at all.** An earlier
clause-scoped design (soft boundaries, affirming double-negative
overrides, a forward-only "without") traded one class of flip for
another: a held-out set of 45 probes showed 20 confidently-wrong flips,
worse than the 16/45 an even earlier all-or-nothing design produced.
Every one of those mechanisms only ever moved a result TOWARD
``present`` — that is exactly where the flips came from. They are
REMOVED, with no replacement:

* ``present`` requires a sentence with NO token from the digested
  negation lexicon (:data:`_NEGATION_RE`) after exact-phrase exemptions
  (:data:`_EXEMPT_SPAN_RES`, :data:`_RIGHT_NOT_TO_BE_SUBJECT_RE`). A
  confidently-wrong ``present`` is possible ONLY when a negation is
  expressed with words OUTSIDE the lexicon, or ACROSS sentences.
* Any negation-ish token ANYWHERE in the sentence (bounded only by
  ``.``/``;``/``:``/a line break — :data:`_SENTENCE_BOUNDARY_RE`) makes
  EVERY cue in that sentence ``uncertain`` — never ``absent``, never
  ``present``. There are no soft clause boundaries and no affirming
  overrides any more: double negatives ("it is not true that there is no
  human intervention") and "cannot be refused" are now ``uncertain``,
  not ``present`` — an intentional, accepted cost of the conservative
  rule, not a regression.
* Held-out result (not tuned to): held-out flips:
  0/45. This number is not a guarantee against a fresh probe set, only
  against this one.

**The lexicon gets full inflection groups; the exemption/abbreviation
period stops being a false boundary; ``host_instrument_number`` moves to
caller-supplied document metadata (``five_d_nd.clause_cues``, not this
module).** A second held-out set (51 probes) found 34 confidently-wrong
flips; 20 were genuine defects (a missing inflection — "denying"/
"refusal"/"excluding"/etc. — or a ``.``/``;``/``:`` wrongly walling a cue
off from its own negator), the rest already-documented, accepted
limits. Fixes:

* **Every lexicon stem is now a FULL inflection group**, including
  nominalisations (den(y|ies|ied|ying|ial|ials), refus(e|es|ed|ing|al
  |als), exclu(de|des|ded|ding|sion), and so on — see :data:`_NEGATION_RE`
  for the complete, closed list) — an earlier lexicon claimed "WITH
  inflections" but was missing most of them. Words OUTSIDE the original
  lexicon (decline, preclude, reject, "in the absence of"/absent/
  absence, "dispense with", "phase out", "out of the question") are
  added too — every addition only widens a result toward ``uncertain``,
  the conservative direction, never toward ``present``. Idioms ("hardly
  ever") are DELIBERATELY left out — see LIMITS. "restrict(ion)" was
  measured on the real GDPR corpus and DELIBERATELY NOT added: it
  overwhelmingly names Art. 18/19's own "right to restriction of
  processing", a legitimate safeguard, not a negation.
* **``:``/``;`` are NO LONGER sentence boundaries at all** — the held
  -out set showed either wrongly isolating an earlier cue from a later
  negator ("Human intervention: none.", "The following safeguards are
  not provided; human intervention, ..."). Removing them only WIDENS the
  negation scope, the conservative direction. A sentence is now bounded
  ONLY by a ``.``/``?``/``!`` that is ITSELF followed by whitespace then
  a capital letter or an opening quote, OR a line break — and a ``.``
  inside a known ABBREVIATION ("Art.", "No.", "Nos.", "e.g.", "i.e.",
  "para.", "cf.", "p." — :data:`_ABBREV_STEM_RE`) is never that boundary
  (an earlier held-out case, "Art. 22(3)", must not split).
* **Claims now match the measurement.** On the real 546-sentence GDPR
  corpus (``five_d_nd.grammars.requirement`` run sentence-by-sentence):
  this example ruleset's cues occur in 11 sentences, 6 of them negated
  (every occurrence in that sentence had an un-exempted negation token
  in scope), so ``uncertain`` fired 6 times; 161/546 sentences (29.5%)
  contain an un-exempted negation token at all (most with no cue of
  THIS narrow ruleset anywhere near them, hence no effect on this
  ruleset's own output). 6/99 GDPR articles get ``needs_review: True``
  when checked article-by-article. These numbers are a property of
  THIS EXAMPLE ruleset's own narrow Art. 22(3) cue table on THIS corpus,
  not a general claim about how often ``uncertain`` fires for every
  possible ruleset on every possible corpus.

**Bare forms, missing nominalisations, and a CONSERVATIVE abbreviation
rule replacing the closed stem list.** A third held-out set (46 probes)
found 19 confidently-wrong flips; 11 were genuine defects in three
mechanical classes, the rest already-documented, accepted limits
(expanded further here — see LIMITS). Fixes:

* **Every lexicon group's SUFFIX is now OPTIONAL where the bare verb was
  missing** — audited every group in :data:`_NEGATION_RE` for this exact
  gap; exactly four had it: ``abolish(?:es|ed|ing|ment|ion)?``,
  ``prohibit(?:s|ed|ing|ion)?``, ``fail(?:s|ed|ing|ure)?\\s+to``,
  ``reject(?:s|ed|ing|ion)?`` (the bare forms "abolish"/"prohibit"/"fail
  to"/"reject" were silently unmatched before this fix, despite every
  INFLECTED form of the same stem matching).
* **Four nominalisations were added**, two of them ``unavailabilit(?:y
  |ies)``/``impossibilit(?:y|ies)`` (alongside the existing bare
  adjectives "unavailable"/"impossible") and ``cessation`` (alongside
  "cease"/"ceasing"), plus ``abolition`` (alongside "abolish"/
  "abolishment", found during an audit of "exclusion"/"prohibition"/
  "revocation"/"suspension"/"denial"/"refusal"/"waiver"/"withholding" —
  all nine already present; only "abolition" was missing).
* **The abbreviation rule is now CONSERVATIVE, not a closed stem
  list** (:func:`_is_abbreviation_before`, replacing the single
  :data:`_ABBREV_STEM_RE` check an earlier version relied on alone) — a
  ``.`` is NOT a sentence boundary when the token before it (a) contains
  ANOTHER ``.`` ("U.S", "C.F.R", "e.g", "i.e" — their own internal
  periods), OR (b) is a CAPITALISED token of at most 4 letters ("Corp",
  "Inc", "Ltd", "Dr", "Mr", "Mrs", "Ms", "St", "Art", "Arts", "No",
  "Nos", "Co" — a GENERAL rule, not an enumerated word list), OR (c) is
  in the pre-existing stem list (the fallback for a short, LOWERCASE
  stem rule (b) would miss, e.g. "para."/"cf."/"p."). Every one of these
  rules only WIDENS the negation scope (fewer, not more, boundaries),
  the conservative direction. The residual, ACCEPTED cost: a TRUE
  sentence end right after a short capitalised token gets wrongly merged
  with the next sentence (see LIMITS) — acceptable because merging is
  conservative.
* Held-out result: 8/46 confidently-wrong flips remain, all eight
  already-named, accepted limits (six out-of-lexicon synonyms, two
  cross-sentence cases) — zero of the original eleven defects remain.

**Performance, a correction to a BROKEN earlier claim, more
nominalisations, and two abbreviation-rule relaxations.** A fourth
held-out set (45 probes) found 12 confidently-wrong flips, all missing
nominalisations/bare forms or abbreviation gaps; separately, the run
time was measured to grow SUPERLINEARLY on long texts (31k chars:
3,723s before this fix; the whole GDPR corpus as one text: ~400s).
Fixes:

* **PERFORMANCE: sentence boundaries are computed ONCE per text, not
  once per cue occurrence** (:func:`_sentence_boundaries` is now
  ``functools.lru_cache``-d; :func:`_sentence_span` uses ``bisect``
  for an O(log n) lookup instead of a linear scan). **The abbreviation
  token/stem search is now ANCHORED to a bounded look-back window**
  (:data:`_ABBREV_LOOKBACK_WINDOW`, 40 characters) instead of scanning
  from position 0 every time — a real abbreviation stem is never
  anywhere close to that many characters long. **``_sentence_is_negated``
  is ALSO cached**, closing a second O(n^2) channel: when the
  abbreviation rule merges many real sentences into one (the accepted
  LIMITS residual below), that one merged sentence string is shared by
  MANY cue occurrences, and without this cache each occurrence
  re-scanned the whole merged sentence from scratch. Measured after
  all three fixes: 31k chars in ~0.02s (previously 3,723s); the whole
  GDPR corpus as one 183k-char text in ~0.08-0.16s (previously ~400s);
  a 200k-char text stays well under the 2s performance-test bound.
* **CORRECTING A BROKEN earlier claim: "abolition" is NOT ``abolish`` +
  ``ion``.** ``abolish(?:...|ion)?`` spells the non-word "abolishion",
  never the real word "abolition" — an earlier claim that this
  combination covered "abolition" was simply wrong, not merely
  imprecise. "abolition" is now its OWN alternative, :data:`_NEGATION_RE`'s
  ``\\babolition\\b``, independent of the ``abolish`` group.
* **Five more nominalisations/forms added**: ``inability``,
  ``discontinuance`` (alongside the existing "discontinuation"),
  ``prevention`` (alongside "prevent"), ``preclusion`` (alongside
  "preclude"), and a HYPHEN accepted as a "phase ... out" separator
  (``phase-out``/``phased-out``, not only the space-separated forms).
  **"failure of X to":** rather than counting an arbitrary number of
  words between "failure" and "to", a BARE "failure" noun is its own
  negation-ish alternative — it strongly implies negation regardless of
  what, if anything, follows it, so "the failure of the controller to
  provide X" is caught without any gap-counting logic at all.
* **Abbreviation rule (b) is now CASE-INSENSITIVE for a token of at
  most 4 letters** (:data:`_ABBREV_CASE_INSENSITIVE_MAX_LEN` —
  "etc.", "lit.", "sec." are all lowercase, 3 letters), and **the
  CAPITALISED-only cap is raised to 5 letters**
  (:data:`_ABBREV_SHORT_CAP_MAX_LEN` — "Admin.", "Assoc." are 5
  letters). The residual, ACCEPTED case: a capitalised abbreviation of
  6 OR MORE letters, followed by a capital letter, is NOT caught by
  either cap and falls through to the pre-existing stem list — if it is
  not on that list either, the period is (wrongly, but conservatively)
  treated as a real sentence boundary.

**LIMITS (read before trusting this module's output) — not exhaustive,
but the known, documented ones:**

* **A negation-ish token OUTSIDE the digested lexicon is invisible to
  this grammar.** The lexicon (:data:`_NEGATION_RE`) is broad and closed,
  but closed: a paraphrase of negation not yet accounted for will not
  trip ``uncertain`` and can, in principle, still produce a
  confidently-wrong ``present``. Named examples, all deliberately
  EXCLUDED, all read ``present`` rather than ``uncertain``: the idiom
  "hardly ever" ("Human intervention is hardly ever granted."); the
  synonyms "cancelled" ("Human intervention has been cancelled."),
  "eliminated" ("...was eliminated in the last reform."), "unobtainable"
  ("...is unobtainable in practice."), "exempt from" ("Low-value loans
  are exempt from human intervention."), "instead of" ("A chatbot
  answers instead of human intervention."), and "seldom" ("Human
  intervention is seldom granted."); and a "?"-separated
  question-then-answer form ("Is human intervention available? No." —
  an earlier held-out case) where the negation sits in a SEPARATE
  sentence from the question that names the cue, so it is ALSO an
  instance of the cross-sentence limit below, not only a lexicon gap.
  Adding synonyms one at a time is exactly the arms race this design
  rejects; a closed, documented lexicon is the chosen trade-off.
* **Cross-sentence negation is out of scope.** A negator in one
  SENTENCE of a multi-sentence ``texts`` collection does not reach a cue
  in a DIFFERENT sentence even when the two are logically connected
  ("Human intervention, the right to express their views and the right
  to contest the decision are listed in the policy. None of these is
  actually offered." — the FIRST sentence's own cues read ``present``;
  the second sentence's negation never reaches them). This is also the
  other channel through which a confidently-wrong ``present`` remains
  possible.
* **A derivation/paraphrase outside the cue table is a lexical miss,
  reported ``absent``, not ``uncertain``.** "A staff member re-examines
  each case; applicants can give their opinion and appeal." tags
  ``human_intervention`` and ``right_to_express_view`` but NOT
  ``right_to_contest`` — "appeal" with no object ("the decision"/"the
  outcome") does not match this grammar's deliberately precise
  ``right_to_contest`` cue (see that cue's own comment for why the
  precision is deliberate, not an oversight) — see
  ``verbatim-failure-staff-member-re-examines-opinion-appeal`` in the
  conformance vectors.
* **A KNOWN, DOCUMENTED lexical false positive — not chased.** "Human
  review of the server logs takes place weekly. Users may express their
  views in a survey and contest the decision via court." tags all three
  safeguard concepts ``present`` even though none of them describes an
  Art. 22(3) safeguard (a server-log audit, a customer survey, and
  ordinary litigation). See
  ``false-positive-lexical-paraphrase-documented``.
* **The exact-phrase exemptions are a closed, finite list** (see
  :data:`_EXEMPT_SPAN_RES`/:data:`_RIGHT_NOT_TO_BE_SUBJECT_RE`) — a
  negation-adjacent phrase not on this list is NOT specially handled; it
  falls through to the plain sentence-scope rule (negation-ish token
  present in sentence -> ``uncertain``).
* **A TRUE sentence end right after a short capitalised token gets
  wrongly MERGED with the next sentence**
  (:func:`_is_abbreviation_before`'s own rule (b): "The firm is Acme
  Corp. Prices rose sharply." reads as ONE sentence, not two, because
  "Corp" is a short capitalised token exactly like "Corp." in "Acme
  Corp. Human Resources"). This is an ACCEPTED residual, not a defect:
  merging two sentences only ever WIDENS a negator's reach into the
  sentence that follows, the same conservative direction as every other
  choice in this design — it can never cause a confidently-wrong
  ``present`` by itself.
* **The SAME merge happens after an ordinary short LOWERCASE word, not
  only a capitalised abbreviation** (the case-insensitive ≤4-letter
  threshold): "Human intervention is required by law. No exceptions
  exist." reads as ONE sentence — "law" is an ordinary 3-letter word,
  not an abbreviation, but rule (b) does not know that. ALSO an
  accepted residual, for the same reason as the capitalised case above:
  merging only ever widens, never narrows.
* **A capitalised abbreviation of 6 OR MORE letters, followed by a
  capital letter, is NOT caught by rule (b) at all** (rule (b)'s cap is
  :data:`_ABBREV_SHORT_CAP_MAX_LEN`, 5 letters; "Administration."
  followed by a capitalised word falls through to the pre-existing stem
  list, and — if not on that list either — the period is treated as a
  REAL sentence boundary there, wrongly SPLITTING what should stay one
  sentence). Unlike the MERGE residual above, this is NOT automatically
  safe: a wrong split that separates a cue from its OWN sentence's
  negator is the SAME class of risk as "a word outside the lexicon" or
  "cross-sentence negation" — a genuine, if narrow, remaining channel
  for a confidently-wrong ``present``. This narrows the gap (now 6+
  letters, was 5+ before) but does not close it; a closed, finite
  capitalised-token cap can never cover every real abbreviation.
* **Over-firing to ``uncertain`` is the ACCEPTED COST of this design,
  not a defect to tune away.** Widening the lexicon, removing ``:``/
  ``;`` as boundaries, and the broad "hardly ever"-style idiom exclusion
  can all, individually and together, drive MORE sentences to
  ``uncertain`` than a narrower rule would — that is the conservative
  direction (toward review, never toward a silent wrong ``present``),
  and ``needs_review`` exists exactly so a human looks at those cases.

**Fail-closed.** :func:`concepts_present`/:func:`check` reject a bare
string or any other non-iterable ``texts`` with ``ValueError``;
:func:`check` validates its ``ruleset`` argument FIRST
(:func:`ruleset_violations`), raising before any text is scanned;
:func:`ruleset_violations` cross-checks every concept name against
:data:`CONCEPT_CUES`'s own known ids.

**The cue table is part of what gets digested.** :data:`CONCEPT_CUES`
and the negator/exemption/override pattern lists are folded into
:func:`ruleset_digest` via :func:`cue_table_digest` — a cue-table edit is
a visible, re-derivable event, exactly like a ruleset edit.

Stdlib only.
"""
from __future__ import annotations

import bisect
import functools
import json
import re
from pathlib import Path
from typing import Any, Iterable

from ..grounding import digest as _grounding_digest

__all__ = [
    "CONCEPT_CUES",
    "tag_concepts",
    "tag_concepts_matched",
    "concept_states",
    "concepts_present",
    "load_ruleset",
    "ruleset_digest",
    "ruleset_violations",
    "cue_table_digest",
    "check",
]

_RULES_PATH = Path(__file__).with_name("requirement_rules.json")

# ── negation: CONSERVATIVE, sentence-scoped (the design decision to
# stop trying to classify negation correctly) ──────────────

#: The broad, closed, digested negation-ish lexicon, WITH
#: inflections — deliberately wide, because the new rule's own safety
#: property depends on this list, not on scope precision: `present` is
#: possible ONLY when a sentence has NONE of these tokens (after the
#: exact-phrase exemptions below). An earlier "forward-only without"
#: rule, its soft clause boundaries, and its affirming double-negative
#: overrides are ALL REMOVED this round — they only ever moved a result
#: TOWARD `present`, and a held-out probe set (45 fresh sentences) showed
#: that is exactly where its own confidently-wrong flips came
#: from (20/45, against 16/45 for the ORIGINAL all-or-nothing design two
#: rounds earlier — negation got WORSE, not better, each time it was
#: "fixed" by adding another exception). The fix is not a better
#: exception; it is to stop granting exceptions that can only ever help
#: `present` win.
_NEGATION_RE = re.compile(
    r"\bno\b|\bnot\b|\bnever\b|\bneither\b|\bnor\b|\bnone\b|\bnobody\b|\bnothing\b|"
    r"n't\b|\bwithout\b|\bcannot\b|\bcan\s+not\b|\bunable\b|\binabilit(?:y|ies)\b|"
    # Nominalisations of the two bare adjectives.
    r"\bunavailable\b|\bunavailabilit(?:y|ies)\b|\bimpossible\b|\bimpossibilit(?:y|ies)\b|"
    # BARE "abolish" was missing (suffix made
    # optional). "abolition" is its OWN alternative,
    # NOT `abolish` + `ion` — that combination spells the non-word
    # "abolishion", never the real word "abolition"; an earlier
    # claim that `abolish(?:...|ion)?` covered "abolition" was WRONG.
    r"\babolish(?:es|ed|ing|ment)?\b|\babolition\b|\black(?:s|ed|ing)?\b|"
    r"\bexclu(?:de|des|ded|ding|sion)\b|"
    # BARE "prohibit" was missing.
    r"\bprohibit(?:s|ed|ing|ion)?\b|\bforb(?:id|ids|ade|idden|idding)\b|"
    r"\brefus(?:e|es|ed|ing|al|als)\b|\bden(?:y|ies|ied|ying|ial|ials)\b|\brul(?:e|es|ed|ing)\s+out\b|"
    r"\bwithh(?:old|olds|olding|eld)\b|"
    # "discontinuance" added alongside the existing
    # "discontinuation".
    r"\bdiscontinu(?:e|es|ed|ing|ation|ance)\b|\bsuspen(?:d|ds|ded|ding|sion)\b|"
    r"\bwaiv(?:e|es|ed|ing|er)\b|\brevo(?:ke|kes|ked|king|cation)\b|"
    # BARE "fail to" was missing. Also:
    # a BARE "failure" (no "to" required) is ALSO negation-ish on its
    # own — the choice between "allow a gap before 'to'" and
    # "treat bare 'failure' as negation-ish" (both options the task
    # named): a bare "failure" noun already strongly implies negation
    # regardless of what, if anything, follows it, so it needs no gap
    # -counting logic at all; "failure of the controller to provide X"
    # is caught by THIS alternative, not by stretching "fail ... to"
    # across an arbitrary number of intervening words.
    r"\bfail(?:s|ed|ing)?\s+to\b|\bfailure\b|"
    # "cessation" added alongside "cease"/"ceasing".
    # "prevention" added alongside "prevent".
    r"\bceas(?:e|es|ed|ing)\b|\bcessation\b|\bprevent(?:s|ed|ing|ion)?\b|"
    r"\bunder\s+no\s+circumstances\b|"
    # Additional words OUTSIDE the original lexicon —
    # every addition only widens a result toward `uncertain`, which is
    # the conservative direction, never toward `present`.
    r"\bdeclin(?:e|es|ed|ing)\b|"
    # "preclusion" added alongside "preclude".
    r"\bpreclud(?:e|es|ed|ing)\b|\bpreclusion\b|"
    # BARE "reject" was missing.
    r"\breject(?:s|ed|ing|ion)?\b|"
    r"\bin\s+the\s+absence\s+of\b|\babsen(?:t|ce)\b|"
    r"\bdispens(?:e|es|ed|ing)\s+with\b|"
    # A HYPHEN is now an accepted separator too, not
    # only whitespace — "phase-out" (noun) and "phased-out" (adjective)
    # are real surface forms "phase out"/"phased out" never covered.
    r"\bphas(?:e|es|ed|ing)[\s-]+out\b|"
    r"\bout\s+of\s+the\s+question\b",
    re.IGNORECASE)

#: EXACT-PHRASE exemptions — each removes ONLY ITS OWN TOKENS from the
#: negation scan (never the whole sentence, never anything else in it).
#: "not only ... but also" is the one variable-gap exemption (the
#: correlative construction itself, not a fixed string) — everything
#: else is a fixed phrase.
_EXEMPT_SPAN_RES = (
    re.compile(r"\bnot\s+only\b.{0,80}?\bbut\s+also\b", re.IGNORECASE),
    re.compile(r"\bwithout\s+prejudice\s+to\b", re.IGNORECASE),
    re.compile(r"\bwithout\s+undue\s+delay\b", re.IGNORECASE),
    re.compile(r"\bno\s+later\s+than\b", re.IGNORECASE),
    re.compile(r"\bnot\s+later\s+than\b", re.IGNORECASE),
)
#: GDPR Art. 22(1)'s own framing — "the right not to be subject to" —
#: exempted ONLY when the sentence has NO OTHER negation-ish token at
#: all (see :func:`_sentence_is_negated`); "Applicants waive the right
#: not to be subject to..." still negates, because of "waive", even
#: though this exact phrase is present too.
_RIGHT_NOT_TO_BE_SUBJECT_RE = re.compile(
    r"\bthe\s+right\s+not\s+to\s+be\s+subject\s+to\b", re.IGNORECASE)

#: ``:``/``;`` are NO LONGER sentence boundaries at
#: all (removed entirely — this only WIDENS the negation scope, the
#: conservative direction: held-out L6/L7 showed a ':'/';' wrongly
#: isolating a later-clause negator away from an earlier-clause cue). A
#: "sentence" is now bounded ONLY by a ``.``/``?``/``!`` that is ITSELF
#: followed by whitespace then a capital letter or an opening quote
#: (:data:`_SENTENCE_END_FOLLOWED_BY_RE`) — i.e. a period that is part of
#: an ABBREVIATION (:func:`_is_abbreviation_before`) or one not followed
#: by a new sentence's own capital/quote is NOT a boundary — OR a line
#: break. Candidate positions are found with :data:`_SENTENCE_CANDIDATE_RE`,
#: then filtered by :func:`_is_sentence_boundary`. Folded into
#: :func:`cue_table_digest`.
_SENTENCE_CANDIDATE_RE = re.compile(r"[.?!\n]")
_SENTENCE_END_FOLLOWED_BY_RE = re.compile(r"\s+[A-Z‘“\"']")
#: The CONSERVATIVE abbreviation rule — a trailing
#: run of letters (optionally dot-joined, e.g. "U.S"/"C.F.R") immediately
#: before the candidate ``.``, anchored at that position.
_ABBREV_TOKEN_RE = re.compile(r"[A-Za-z]+(?:\.[A-Za-z]+)*$")
#: The abbreviation-token/stem searches below are
#: ANCHORED to a bounded look-back window, never the whole text from
#: position 0 — a correctness-preserving performance fix (a real
#: abbreviation stem is a handful of letters, never anywhere close to
#: this many characters long), closing the O(n^2)/O(n^3) blow-up an
#: unanchored ``.search(text, 0, pos)`` produced on long texts (31k
#: chars: 3,723s before this fix, 0.19s after — see the module docstring
#: for the full timing table).
_ABBREV_LOOKBACK_WINDOW = 40
#: Rule (b)'s CASE-INSENSITIVE cap (inclusive) — a
#: token of at most this many letters qualifies regardless of case
#: ("etc", "lit", "sec" are all 3 letters).
_ABBREV_CASE_INSENSITIVE_MAX_LEN = 4
#: Rule (b)'s CAPITALISED-only cap (inclusive),
#: raised from 4 to 5 ("Admin", "Assoc" are 5 letters) — only reached
#: for a token LONGER than :data:`_ABBREV_CASE_INSENSITIVE_MAX_LEN`.
_ABBREV_SHORT_CAP_MAX_LEN = 5
#: A closed stem list, kept as rule (c)'s FALLBACK for a
#: stem that is neither multi-dot (rule a) nor a short CAPITALISED token
#: (rule b) — e.g. the lowercase "para."/"cf."/"p." forms, which are
#: short but not capitalised. Matched case-insensitively against the
#: text immediately BEFORE the candidate ``.``, anchored at that
#: position.
_ABBREV_STEM_RE = re.compile(r"\b(?:Art|Arts|Nos?|Co|para|cf|p)$", re.IGNORECASE)


def _is_abbreviation_before(text: str, pos: int) -> bool:
    """True iff the token immediately before
    ``text[pos]`` (a candidate ``.``) makes that ``.`` an ABBREVIATION'S
    OWN period, never a sentence boundary. Three rules, any one
    sufficient — each only WIDENS the negation scope, the conservative
    direction, since a non-boundary merges more text into one sentence:

    (a) the token itself contains another ``.`` ("U.S", "C.F.R", "e.g",
        "i.e" — their OWN internal periods already make
        :data:`_SENTENCE_END_FOLLOWED_BY_RE` fail for every period but
        the LAST one, so only the last one reaches this function, and
        this rule catches it);
    (b) the token is SHORT — this splits into two
        thresholds: ANY token of at most
        :data:`_ABBREV_CASE_INSENSITIVE_MAX_LEN` letters qualifies
        REGARDLESS OF CASE ("etc", "lit", "sec"), OR a token longer than
        that but CAPITALISED and at most
        :data:`_ABBREV_SHORT_CAP_MAX_LEN` letters qualifies ("Corp",
        "Inc", "Ltd", "Dr", "Mr", "Mrs", "Ms", "St", "Art", "Arts", "No",
        "Nos", "Co", "Admin", "Assoc") — a GENERAL rule, not a closed
        word list: ANY token meeting either threshold qualifies, which
        is deliberately broader than naming every possible abbreviation;
    (c) the token is in the EXISTING stem list (:data:`_ABBREV_STEM_RE`)
        — the fallback for a short, LOWERCASE stem LONGER than
        :data:`_ABBREV_CASE_INSENSITIVE_MAX_LEN` letters that rule (b)
        would otherwise miss ("para.", "cf.", "p.").

    Two residuals, both ACCEPTED trades, documented in full in the
    module docstring's own LIMITS section: a TRUE sentence end right
    after a short token (capitalised OR, if short enough, lowercase)
    gets WRONGLY merged with the next sentence — merging only ever
    WIDENS a negator's reach, never narrows it, so it is always safe;
    and a capitalised abbreviation of MORE than
    :data:`_ABBREV_SHORT_CAP_MAX_LEN` letters, followed by a capital
    letter, is caught by neither threshold and (unless on the stem
    list) is wrongly treated as a REAL boundary — this one is NOT
    automatically safe, since a wrong split can separate a cue from its
    own sentence's negator.
    """
    window_start = max(0, pos - _ABBREV_LOOKBACK_WINDOW)
    m = _ABBREV_TOKEN_RE.search(text, window_start, pos)
    if not m:
        return False
    token = m.group(0)
    if "." in token:
        return True
    # Rule (b) is CASE-INSENSITIVE for a token of at
    # most _ABBREV_CASE_INSENSITIVE_MAX_LEN letters (covers "etc.",
    # "lit.", "sec."); item A2: the CAPITALISED cap is raised to
    # _ABBREV_SHORT_CAP_MAX_LEN letters ("Admin.", "Assoc.").
    if len(token) <= _ABBREV_CASE_INSENSITIVE_MAX_LEN:
        return True
    if len(token) <= _ABBREV_SHORT_CAP_MAX_LEN and token[:1].isupper():
        return True
    return bool(_ABBREV_STEM_RE.search(text, window_start, pos))


def _is_sentence_boundary(text: str, pos: int) -> bool:
    """True iff ``text[pos]`` is an actual sentence boundary under fix
    this rule (see :data:`_SENTENCE_CANDIDATE_RE`'s own docstring
    for the full account)."""
    ch = text[pos]
    if ch == "\n":
        return True
    if not _SENTENCE_END_FOLLOWED_BY_RE.match(text, pos + 1):
        return False
    if ch == "." and _is_abbreviation_before(text, pos):
        return False
    return True


#: Computing every sentence boundary for a text is
#: O(n) (with the look-back window above); doing it ONCE per DISTINCT
#: text and reusing the result for EVERY cue occurrence that text
#: contains — rather than recomputing it from scratch for every single
#: occurrence, as every earlier round's own :func:`_sentence_span` did —
#: is what turns an O(n^2)/O(n^3) blow-up on a long text into O(n log n)
#: (the ``log n`` is :func:`_sentence_span`'s own bisect lookup, below).
#: A bounded cache (`maxsize`) rather than an unbounded one, so this
#: module never grows memory without limit across a long-running
#: process that checks many distinct texts.
@functools.lru_cache(maxsize=64)
def _sentence_boundaries(text: str) -> "tuple[int, ...]":
    return tuple(m.start() for m in _SENTENCE_CANDIDATE_RE.finditer(text)
                 if _is_sentence_boundary(text, m.start()))


def _sentence_span(text: str, pos: int) -> "tuple[int, int]":
    """The ``(start, end)`` character span of the SENTENCE containing
    ``pos`` — bounded only by :func:`_sentence_boundaries` (CACHED per
    ``text``). ``bisect`` finds the enclosing span in
    O(log n) rather than a linear scan over every boundary in ``text``."""
    boundaries = _sentence_boundaries(text)
    i = bisect.bisect_left(boundaries, pos)
    start = boundaries[i - 1] + 1 if i > 0 else 0
    end = boundaries[i] if i < len(boundaries) else len(text)
    return start, end


def _span_inside_any(abs_start: int, spans: "list[tuple[int, int]]") -> bool:
    return any(s <= abs_start < e for s, e in spans)


@functools.lru_cache(maxsize=256)
def _sentence_is_negated(sentence: str) -> bool:
    """True iff ``sentence`` contains an UN-exempted negation-ish token
    (:data:`_NEGATION_RE`) anywhere. CACHED — when
    the abbreviation rule merges many real sentences into one (the
    accepted LIMITS residual), that one SENTENCE string can be shared by
    MANY cue occurrences; without this cache, each occurrence re-scans
    the entire merged sentence, reproducing the same O(n^2) blow-up the
    boundary-computation cache alone does not fully close. The
    own conservative rule: a cue's own POSITION inside the sentence no
    longer matters at
    all (no more before/after, no more forward-only "without"); the
    WHOLE sentence is negated or it is not, and EVERY cue occurrence in
    it inherits that one verdict. The exact-phrase exemptions
    (:data:`_EXEMPT_SPAN_RES`) remove only their own matched tokens; the
    Art. 22(1) exemption (:data:`_RIGHT_NOT_TO_BE_SUBJECT_RE`) additionally
    requires that NO OTHER negation-ish token exists anywhere in the
    sentence.
    """
    exempt_spans = [
        (em.start(), em.end())
        for ex_re in _EXEMPT_SPAN_RES
        for em in ex_re.finditer(sentence)
    ]
    negator_hits = [
        m for m in _NEGATION_RE.finditer(sentence)
        if not _span_inside_any(m.start(), exempt_spans)
    ]
    rntbs_spans = [(m.start(), m.end()) for m in _RIGHT_NOT_TO_BE_SUBJECT_RE.finditer(sentence)]
    if rntbs_spans:
        other_hits = [m for m in negator_hits if not _span_inside_any(m.start(), rntbs_spans)]
        if not other_hits:
            # the Art. 22(1) phrase is the ONLY negation-ish material in
            # the sentence -> exempt it entirely (sentence not negated).
            return False
    return bool(negator_hits)


def _is_negated(text: str, match_start: int) -> bool:
    """True iff the SENTENCE (:func:`_sentence_span`) containing the cue
    occurrence starting at ``match_start`` is negated
    (:func:`_sentence_is_negated`) — the cue's own position within that
    sentence plays no further role."""
    start, end = _sentence_span(text, match_start)
    return _sentence_is_negated(text[start:end])


#: Closed, deterministic concept cue table (regex, case-insensitive) — the
#: tagging layer :func:`tag_concepts`/:func:`tag_concepts_matched` runs
#: text through. Every surface form is listed here, not inferred.
CONCEPT_CUES: "dict[str, list[re.Pattern]]" = {
    "automated_decision_making": [re.compile(p, re.IGNORECASE) for p in [
        r"\bdecision\s+based\s+solely\s+on\s+automated\s+processing\b",
        r"\bautomated\s+processing\b", r"\bautomated\s+decision[- ]making\b",
        r"\bsolely\s+on\s+automated\s+processing\b", r"\bprofiling\b",
        r"\bfully\s+automated\b",
        r"\ban\s+algorithm\s+decides\b",
        r"\bdecided\s+by\s+an\s+algorithm\b",
    ]],
    "human_intervention": [re.compile(p, re.IGNORECASE) for p in [
        r"\bhuman\s+intervention\b", r"\bobtain\s+human\s+intervention\b",
        r"\bintervention\s+on\s+the\s+part\s+of\s+the\s+controller\b",
        r"\bhuman\s+review\b",
        r"\ba\s+person\s+reviews?\b",
        r"\breview(?:ed)?\s+by\s+a\s+(?:human|person)\b",
        r"\bre-examine[sd]?\s+by\s+a\s+(?:staff\s+member|person|human)\b",
        r"\ba\s+(?:staff\s+member|person|human)\s+re-examines?\b",
    ]],
    "right_to_express_view": [re.compile(p, re.IGNORECASE) for p in [
        r"\bexpress\s+(?:his\s+or\s+her\s+|their\s+)?point\s+of\s+view\b",
        r"\bexpress\s+(?:his\s+or\s+her\s+|their\s+)?views?\b",
        r"\bgive\s+their\s+opinion\b",
    ]],
    "right_to_contest": [re.compile(p, re.IGNORECASE) for p in [
        r"\bcontest\s+the\s+decision\b",
        # deliberately scoped to "the outcome"/"the decision" (never a
        # bare "challenge"/"contest"/"appeal"): a precision requirement —
        # "the parties may contest other matters in court" must NOT tag
        # this, and a bare "appeal" with no object is a documented
        # lexical miss (module docstring LIMITS), not chased.
        r"\bchallenge\s+the\s+(?:outcome|decision)\b",
        r"\bappeal\s+(?:the|against\s+the)\s+decision\b",
    ]],
}


def _concept_occurrence_states(text: str, concept: str) -> "tuple[bool, bool]":
    """``(any_affirmed, any_matched)`` for ``concept``'s own cues over
    ``text`` — ``any_matched`` is True the moment ANY cue fires at all
    (negated or not); ``any_affirmed`` is True only if SOME occurrence is
    un-negated."""
    any_affirmed = False
    any_matched = False
    for pattern in CONCEPT_CUES[concept]:
        for m in pattern.finditer(text):
            any_matched = True
            if not _is_negated(text, m.start()):
                any_affirmed = True
    return any_affirmed, any_matched


def tag_concepts(text: str) -> set:
    """Which :data:`CONCEPT_CUES` keys fire AFFIRMATIVELY anywhere in
    ``text`` — a set. A concept with BOTH a negated and an affirmed
    occurrence is included: one affirmed occurrence anywhere is enough.
    Raises ``ValueError`` if ``text`` is not a string."""
    if not isinstance(text, str):
        raise ValueError("tag_concepts() requires a string")
    return {c for c in CONCEPT_CUES if _concept_occurrence_states(text, c)[0]}


def tag_concepts_matched(text: str) -> set:
    """Which :data:`CONCEPT_CUES` keys fire AT ALL in ``text`` — negated
    or not. ``tag_concepts_matched(text) - tag_concepts(text)`` is exactly
    the set of concepts whose ONLY occurrence(s) in ``text`` were negated.
    Raises ``ValueError`` if ``text`` is not a string."""
    if not isinstance(text, str):
        raise ValueError("tag_concepts_matched() requires a string")
    return {c for c in CONCEPT_CUES if _concept_occurrence_states(text, c)[1]}


def _validate_texts(texts: Any) -> list:
    """Fail closed on a malformed ``texts`` argument. A bare string is
    REJECTED outright (Python would otherwise iterate its CHARACTERS, not
    its SENTENCES); any other non-iterable is rejected too; every element
    must itself be a string. Returns the materialised list on success."""
    if isinstance(texts, str):
        raise ValueError(
            "texts must be an iterable of strings (e.g. a list of sentences), "
            "not a single string — iterating a string yields its characters")
    try:
        materialised = list(texts)
    except TypeError as exc:
        raise ValueError(f"texts must be an iterable of strings, got {texts!r}") from exc
    if not all(isinstance(t, str) for t in materialised):
        raise ValueError("every item in texts must be a string")
    return materialised


def concept_states(texts: "Iterable[str]") -> "dict[str, str]":
    """``{concept: "present" | "uncertain" | "absent"}`` for EVERY
    :data:`CONCEPT_CUES` key, aggregated over the WHOLE ``texts``
    collection (the three-state design — see the module
    docstring). ``present`` beats ``uncertain`` beats ``absent``: a
    concept affirmed anywhere in the collection is ``present`` even if
    negated elsewhere in it. Fail-closed via :func:`_validate_texts`."""
    texts = _validate_texts(texts)
    affirmed: set = set()
    matched: set = set()
    for t in texts:
        affirmed |= tag_concepts(t)
        matched |= tag_concepts_matched(t)
    out = {}
    for concept in CONCEPT_CUES:
        if concept in affirmed:
            out[concept] = "present"
        elif concept in matched:
            out[concept] = "uncertain"
        else:
            out[concept] = "absent"
    return out


def concepts_present(texts: "Iterable[str]") -> set:
    """Union of :func:`tag_concepts` across a collection of sentences —
    concepts in the ``present`` state only (backward-compatible helper;
    :func:`concept_states` is the full three-state view). Fail-closed via
    :func:`_validate_texts`."""
    present: set = set()
    for t in _validate_texts(texts):
        present |= tag_concepts(t)
    return present


def load_ruleset(source: "str | Path | dict | None" = None) -> dict:
    """Load a requirement ruleset DOCUMENT — the (trigger -> required)
    rule DATA this grammar checks against. ``source`` is a ruleset dict
    already in memory, a path to a JSON file, or ``None`` (loads the
    packaged default, ``requirement_rules.json``, this module's own
    EXAMPLE ruleset — GDPR Art. 22(3)). Never parses or infers rules from
    code; the ruleset is always data, read verbatim.
    """
    if source is None:
        source = _RULES_PATH
    if isinstance(source, dict):
        return source
    return json.loads(Path(source).read_text(encoding="utf-8"))


def ruleset_violations(doc: Any) -> list:
    """Shape violations of a requirement ruleset document: a mapping with
    a non-empty string ``ruleset_id`` and a list ``rules``, each rule a
    mapping with non-empty string ``obligation_id``/``citation``, a
    non-empty list of non-empty-string ``trigger_concepts``, and a
    non-empty list of non-empty-string ``required_concepts``. EVERY
    concept name in ``trigger_concepts``/``required_concepts`` MUST also
    be a known key of :data:`CONCEPT_CUES`. Returns ``[]`` when the
    document validates.
    """
    if not isinstance(doc, dict):
        return ["requirement ruleset must be a mapping"]
    out = []
    ruleset_id = doc.get("ruleset_id")
    if not isinstance(ruleset_id, str) or not ruleset_id:
        out.append("requirement ruleset field 'ruleset_id' must be a non-empty string")
    rules = doc.get("rules")
    if not isinstance(rules, list) or not rules:
        out.append("requirement ruleset field 'rules' must be a non-empty list")
        rules = []
    known_concepts = set(CONCEPT_CUES)
    for i, rule in enumerate(rules):
        if not isinstance(rule, dict):
            out.append(f"rules[{i}] must be a mapping")
            continue
        for field in ("obligation_id", "citation"):
            value = rule.get(field)
            if not isinstance(value, str) or not value:
                out.append(f"rules[{i}].{field} must be a non-empty string")
        for field in ("trigger_concepts", "required_concepts"):
            value = rule.get(field)
            if not isinstance(value, list) or not value or not all(
                    isinstance(c, str) and c for c in value):
                out.append(f"rules[{i}].{field} must be a non-empty list of non-empty strings")
                continue
            unknown = sorted(c for c in value if c not in known_concepts)
            if unknown:
                out.append(
                    f"rules[{i}].{field} names concept(s) {unknown!r} not in "
                    f"CONCEPT_CUES {sorted(known_concepts)!r}")
    return out


def cue_table_digest() -> str:
    """Sha256 digest over :data:`CONCEPT_CUES`'s own pattern SOURCE
    strings, plus the negation lexicon/exemption/sentence-boundary
    pattern sources (never the compiled ``re.Pattern`` objects) — so a
    cue-table EDIT (a new paraphrase, a widened negation lexicon, a new
    exemption, an abbreviation rule change) is pinned exactly like a
    ruleset edit. Also folds in :data:`_ABBREV_TOKEN_RE` and
    :data:`_ABBREV_SHORT_CAP_MAX_LEN` alongside
    :data:`_SENTENCE_END_FOLLOWED_BY_RE`/:data:`_ABBREV_STEM_RE`, so the
    new short-capitalised-token and multi-dot abbreviation rules are
    pinned too. Folded into :func:`ruleset_digest`.
    """
    doc = {
        "concepts": {concept: [p.pattern for p in patterns]
                     for concept, patterns in sorted(CONCEPT_CUES.items())},
        "negation_lexicon": _NEGATION_RE.pattern,
        "exempt_spans": [p.pattern for p in _EXEMPT_SPAN_RES],
        "right_not_to_be_subject": _RIGHT_NOT_TO_BE_SUBJECT_RE.pattern,
        "sentence_candidate": _SENTENCE_CANDIDATE_RE.pattern,
        "sentence_end_followed_by": _SENTENCE_END_FOLLOWED_BY_RE.pattern,
        "abbrev_token": _ABBREV_TOKEN_RE.pattern,
        "abbrev_short_cap_max_len": _ABBREV_SHORT_CAP_MAX_LEN,
        "abbrev_stem": _ABBREV_STEM_RE.pattern,
    }
    return _grounding_digest(doc)["sha256"]


def ruleset_digest(doc: dict) -> str:
    """Sha256 digest (``five_d_nd.grounding.digest``) over the ruleset
    document AND the concept cue table (:func:`cue_table_digest`) — pins
    exactly which trigger/required rules AND which cue surfaces a given
    ``check()`` call ran against."""
    return _grounding_digest({"ruleset": doc, "cue_table_digest": cue_table_digest()})["sha256"]


def _rule_for(ruleset: dict, obligation_id: str) -> dict:
    for rule in ruleset.get("rules", []):
        if rule.get("obligation_id") == obligation_id:
            return rule
    raise KeyError(f"no rule for obligation_id {obligation_id!r} in this ruleset")


def check(obligation_id: str, texts: "Iterable[str]", ruleset: "dict | None" = None) -> dict:
    """Deterministically check one obligation's requirement, by THREE
    -STATE lexical presence (see the module docstring — this is NOT a
    compliance verdict), against a text collection. ``ruleset`` defaults
    to the packaged example ruleset (:func:`load_ruleset`) when omitted,
    and is VALIDATED FIRST, raising ``ValueError`` on a malformed ruleset
    before any text is scanned. Returns a dict with ``obligation_id``,
    ``citation``, ``triggered`` (a trigger concept is ``present``,
    never merely ``uncertain``), ``trigger_uncertain`` (a
    trigger concept's ONLY occurrences were negated — the requirement MAY
    still apply; routes to review rather than silently skipping),
    ``required_concepts`` (sorted), ``present``/``uncertain``/``missing``
    (sorted lists over the three states), ``all_present`` (``True`` iff
    triggered, every required concept ``present``, and none
    ``uncertain``; ``False`` iff triggered with any gap; ``None`` when not
    triggered at all), ``needs_review`` (any required concept
    ``uncertain``, or ``trigger_uncertain``), and ``ruleset_digest``.
    """
    if ruleset is None:
        ruleset = load_ruleset()
    violations = ruleset_violations(ruleset)
    if violations:
        raise ValueError(f"malformed requirement ruleset: {violations!r}")
    spec = _rule_for(ruleset, obligation_id)
    texts = _validate_texts(texts)
    states = concept_states(texts)
    triggered = any(states[c] == "present" for c in spec["trigger_concepts"])
    trigger_uncertain = (not triggered) and any(
        states[c] == "uncertain" for c in spec["trigger_concepts"])
    required = spec["required_concepts"]
    present_req = sorted(c for c in required if states[c] == "present")
    uncertain_req = sorted(c for c in required if states[c] == "uncertain")
    missing_req = sorted(c for c in required if states[c] == "absent")
    all_present = (not uncertain_req and not missing_req) if triggered else None
    needs_review = bool(uncertain_req) or trigger_uncertain
    return {
        "obligation_id": obligation_id,
        "citation": spec["citation"],
        "triggered": triggered,
        "trigger_uncertain": trigger_uncertain,
        "required_concepts": sorted(required),
        "present": present_req,
        "uncertain": uncertain_req,
        "missing": missing_req,
        "all_present": all_present,
        "needs_review": needs_review,
        "ruleset_digest": ruleset_digest(ruleset),
    }
