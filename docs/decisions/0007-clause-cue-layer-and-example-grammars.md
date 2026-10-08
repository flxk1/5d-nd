# 0007 — The clause-cue layer, example nD grammars, and the matching rule (2026-10-02)

## Status

Accepted. Additive to the coordinate round (0001-0006); changes none of
their decisions.

## Context

Measuring the frozen 5D reference implementation against the GDPR's
operative text showed most sentence entries lowering to a single
dimension (`relational`), and every 5D-only variant tried (plain, nD
filter, depth window, centring, triple tensor) showing no measurable
retrieval signal against a same-article/cross-reference ground truth —
5D is the coordinate frame nD grammars attach to, not itself a
retrieval signal. A comparison of four candidate fixes selected
a deterministic lexical "term" nD grammar (BM25), ahead of a TF-IDF
reference, with four grafts named onto it: candidate D+'s requirement/
absence grammar (with a positive control), A's richer multi-relation
lowering cue-table form (merged with D+'s own, richer, cue set),
runtime kept out of results, and blend weights fixed a priori (never
tuned on the GDPR ground truth).

The owner approved integrating the winner plus its grafts as "step 1"
(2026-10-02).

## Decision

1. **§8a (clause-cue layer, D2)** — A's cue-table form + D+'s richer cue
   set, as a SECOND, ADDITIVE layer alongside the UNCHANGED §8
   assertoric layer. `relational` fires only when no other cue fires
   (an explicit design choice this ADR records, resolving the ambiguity
   in "it contributes the dimensions of its content cues": GDPR's
   relational vocabulary co-occurs with almost every other cue, so
   always counting it would re-create the same collapse one layer up).
2. **§18 term grammar** — candidate C, ported as an EXAMPLE nD grammar
   (`five_d_nd.grammars.term`), bound to `relational` (5D's own identity/
   default), never a sixth dimension.
3. **§18 requirement grammar** — candidate D+'s graft, ported as a second
   EXAMPLE nD grammar (`five_d_nd.grammars.requirement`), with its
   (trigger → required) rules as DATA (`requirement_rules.json`, pinned
   by digest) rather than code, and a positive control.
4. **§19 matching** — a NORMATIVE fixed weighted-average blend of the
   term score and the 5D structural cosine, weights `{"term": 0.7,
   "structural": 0.3}`, justified a priori (IR practice: BM25 as the
   primary ranking signal; 5D's cosine as a descriptive coordinate-frame
   signal per §9's own "invariant for consuming languages") — never
   tuned on the GDPR ground truth.
5. **Replay** (`five_d_nd.replay`) — runtime/timing is returned as a
   separate value (`timed_call`'s own 2-tuple), never folded into a
   digested or compared result.

## Consequences

- `spec/SPEC.md` gains §8a, §18, §19, §20, plus an Annex B migration item
  recording that loomground-factual does NOT implement §8a (an open item,
  not a claim).
- `five_d_nd.profile` gains two fields (`clause_cue_saturation`,
  `match_blend_weights`); every existing resolution-profile vector's own
  pinned `profile_digest` was recomputed against the new, wider resolved
  document (the digest is defined over the FULLY RESOLVED document,
  §16 — adding a field to `DEFAULTS` necessarily changes it for every
  profile, documented here rather than silently).
- §8 (D1), its conformance vectors, and the factual/versum differentials
  are UNCHANGED — this integration step touches none of them.
- Stage 2 scope (resolve order at scale, erasure mechanics, migration
  code) is untouched; this ADR does not reopen it.

## Correctness, provenance and test-power fixes (2026-10-02)

Correctness/provenance/test-power review findings against the
step 1 integration were addressed in a follow-up series of commits on the
SAME branch: requirement-grammar negation scope and paraphrase cues with
fail-closed validation; §19/§16 fail-closed on non-finite/negative/bool
weights and scores (shared by `d_blend_weights`); §8a cue soundness on the
real GDPR text (plural/ranged article citations, exclusion of citations to
ANOTHER instrument, `within`/`means` precision, overlapping-match
de-duplication); the term grammar's tokenizer now pinned into its own
digest, and its claim weights normalised per document instead of clamped
(the clamp had collapsed 92% of claims on the real GDPR corpus to the
same value); provenance corrections (no path into a non-existent test
file; a real independent oracle for the clause-cue fuzz, not merely a
claimed one). None of these change the FIVE decisions above; they fix
defects in how each was implemented or documented.

**OPEN OWNER DECISION, flagged not resolved.** §8a's
own `relational`-only-when-silent gate is DISCONTINUOUS by construction:
GDPR Art. 65(5)'s own sentence scores `relational: 5`; adding one
clause-initial "Where applicable, " flips it to `relational: 0` — a
jump, not a gradual shift, on a single added word. This design KEEPS
the gate AS INTEGRATED (the gate
itself was a design call made in drafting §8a, never something the owner
approved or was even asked about directly; only the integration step as
a whole was approved, 2026-10-02 — see §8a's own "OPEN OWNER DECISION"
paragraph for the two alternatives considered and why neither is adopted
here); moving from the current all-or-nothing gate to a down-weighted,
smooth alternative is the owner's own decision to make, not something a
maker decides unilaterally.

## Negation scope, clause-cue precision, and a ground-truth measurement artefact (2026-10-02)

A second round of review findings was addressed on the same
branch: the requirement grammar's `satisfied` field is renamed
`all_present` with an explicit normative scope note (it reports LEXICAL
presence, never a compliance verdict — a conforming consumer MUST NOT
treat `all_present: true` as a compliance finding); negation is now
CLAUSE-SCOPED (both before and after a cue, bounded by `;`/`.`/`:`) with
three closed exemptions and a double-negation override, verified against
every probe sentence named below as a conformance vector;
a KNOWN lexical false positive is documented, not chased; `clause_cues`
now treats "of this/the Regulation" as the HOST instrument (internal,
kept) while requiring an external-instrument phrase to follow a citation
DIRECTLY (an intervening relative clause no longer excludes it), accepts
"or" as a list connector, and no longer treats a trailing time-duration
("12 to 30 days") as a phantom article range; the `means` definitional
rule is re-keyed on a preceding closing quote, firing on all 26 of GDPR
Art. 4's own definitional uses; the term grammar's pinned tokenizer is
now ENFORCED by `bm25_vector`, not merely recorded; `profile_violations`
rejects a non-finite WEIGHT SUM (two individually-finite weights that
overflow when added), agreeing with `match.combine_scores`; the fuzz's
own match-weight oracle now uses its OWN literal default weights rather
than reading `match.DEFAULT_MATCH_BLEND_WEIGHTS` (independence); the
clause-cue oracle's fragment pool now includes one host-instrument and
one external-instrument citation.

**A ground-truth measurement artefact, recorded rather than "fixed"**
(the rule: do NOT edit the measurement harness). `bonus.py`'s own
`related()` ground-truth function reads
cross-references via its OWN regex (singular "Article N" only, predating
the plural/ranged citation fix) — it does NOT recognise "Articles 15, 16
and 17" or "Articles 15 to 20" as a same-article/cross-reference
relation. A PLURAL-AWARE ground truth
(`bonus_gt.py`, reading cross-references via
`five_d_nd.clause_cues.cross_reference_targets` itself instead of
`bonus.py`'s own narrower regex) gives the accurate comparison, and the
direction is MIXED, not uniformly an understatement as an earlier draft
of this ADR claimed: the article-level retrieval metric moves DOWN under
the plural-aware ground truth relative to the singular-only one, while
the paragraph- and entry-level metrics move UP. This artefact — and its
mixed direction — is not reproducible from this repository alone and is
not published here; the harness itself is intentionally left untouched.

## Three-state negation design and relational down-weighting

The requirement grammar's clause-wide negation (an earlier version) traded one
error class for another: a fresh 30-probe set measured FN 11/30, FP
8/96, against FN 6/30, FP 23/96 before it — fewer false positives, more
false negatives, not a net improvement. The design decision: stop the
negation arms race — each required/trigger concept's own state is now
THREE-VALUED (`present`/`uncertain`/`absent`), never silently collapsed
to a binary yes/no when the lexical evidence is genuinely ambiguous —
see `src/five_d_nd/grammars/requirement.py`'s own module docstring for
the full design and its LIMITS section. Measured against the SAME 42
-case probe set (30 fresh plus 12 earlier, now all 42 copied verbatim
into `conformance/vectors/requirement-grammar/probe-*.json`): FN 0/30,
FP 0/96, trigger errors 0 — the bar ("zero confidently-wrong
flips") is met, enforced by its own test
(`test_requirement_three_state_bar_zero_confidently_wrong_flips`).

Also in this round: `five_d_nd.clause_cues`'s cross-reference matching
now skips trailing bracketed sub-paragraph groups ("(1)(b)") before the
external-instrument check, recognises "Council"/"Delegated"/etc.
-qualified Regulations, "TFEU"/"TEU"/"of the Charter" as external, and
treats a "to"-range as a range ONLY for the plural "Articles" form (never
singular "Article"); the quote-means definitional rule now requires a
genuine OPENING-then-CLOSING quote pair, not a bare possessive apostrophe
("the data subject's rights", "the processor's means" no longer
falsely fire).

**OPEN OWNER DECISION (§8a, Annex B) — NOW DECIDED, 2026-10-03.** The
owner decided to REPLACE the all-or-nothing
relational-suppression gate with DOWN-WEIGHTING. The formula itself —
`relational_eff = relational_count * s / (s + n_other)`, the new
resolution-profile field `relational_suppression_scale` (default `1`),
and its default value are a separate design choice; the
owner's decision was only the DIRECTION (replace the gate), not this
specific formula. See `src/five_d_nd/clause_cues.py`'s
`relational_effective()` and spec/SPEC.md §8a/§16 for the full account,
including the stated and tested properties (no change at `n_other == 0`;
monotone non-increasing in `n_other`; at the default scale, one extra
cue at most halves the value — GDPR Art. 65(5)'s own sentence: `5 ->
2.5`, never the old gate's `5 -> 0`). §8's own frozen base `+1 relational`
contribution on a modal sentence is DELIBERATELY NOT given the same
treatment — it is produced by the UNCHANGED, loomground-factual-parity
-critical assertoric layer and only summed, never re-graded, by
`combined_contributions()`; applying down-weighting there would mean
touching §8's own frozen output, which this specification's own repeated
"§8 is unchanged" rule forbids.

## Conservative, sentence-scoped negation

An earlier clause-scoped negation design (soft boundaries, affirming
double-negative overrides, a forward-only "without") was itself not
adequate: a fresh, 45-sentence held-out probe set measured 20
confidently-wrong flips, WORSE than the 16/45 an even earlier
all-or-nothing design produced — negation got worse, not better, each
time it was "fixed" by adding another exception. Every one of its own
additions only ever moved a result TOWARD `present`, and
that is exactly where the flips came from.

**DESIGN DECISION, 2026-10-03 — stop trying to classify negation
correctly.** `present` requires a sentence (bounded only by
`.`/`;`/`:`/a line break) with no token from the digested negation
lexicon after exact-phrase exemptions. A confidently-wrong `present` is
possible ONLY when a negation is expressed with words outside the
lexicon, or across sentences. Any negation-ish token anywhere in the
sentence makes EVERY cue in that sentence `uncertain` — never `absent`,
never `present` — with no exception that can ever push a result back
toward `present`: the earlier soft clause boundaries and affirming
overrides are REMOVED, with no replacement; double negatives and "cannot
be refused" are now `uncertain`, an accepted cost. The negation lexicon
itself is broadened considerably (new inflections of `refuse`/`deny`/
`rule out`/`withhold`/`discontinue`/`suspend`/`waive`/`revoke`/`fail to`/
`cease`, among others) — see `src/five_d_nd/grammars/requirement.py`'s
own module docstring for the full list and the exact-phrase exemptions
(unchanged in kind: "no later than", "not later than", "without undue
delay", "without prejudice to", "not only … but also", and GDPR Art.
22(1)'s own "the right not to be subject to" framing — the last one
exempted only when the sentence has NO OTHER negation-ish token). The
trigger follows the SAME rule.

Held-out result, not tuned to: 0/45 confidently-wrong
flips against this held-out set (2026-10-03). A NEW held-out set is
written for each later check; this number is not a guarantee against a
fresh probe set, only against this one. All 45
held-out probes are copied into `conformance/vectors/requirement-grammar/
heldout1-*.json` (provenance "Held-out set 1"), each carrying a
`truth` field judged independently of this grammar's own output, scored
by a dedicated test
(`test_requirement_confusion_table_zero_confidently_wrong_flips`) against
BOTH that set and the 41 distinct probes from earlier checks, using a
CONFIDENTLY-WRONG definition (a flip is a wrong `present`/
`triggered`, never merely an `uncertain` or a lexical miss).

Also in this round: `five_d_nd.clause_cues`'s external-instrument
qualifier before "Regulation" now accepts MULTIPLE words ("Commission
Implementing Regulation", "European Parliament Regulation"), not only
one; `cross_reference_targets` takes an optional
`host_instrument_number` so a citation naming the HOST instrument's own
number ("Article 45 of Regulation (EU) 2016/679") resolves internally
rather than being excluded as external. Two spec-drift corrections:
§8a's "Explicit field types" now states `relational` is a non-negative
NUMBER (fixed-point), not an integer count; the sentence describing
`relational_eff`'s rounding now correctly says the RESULT is quantised,
never the scale parameter `s` itself.

## Full inflection groups, abbreviation-aware sentence boundaries, host-instrument-number as document metadata

The prior design was confirmed FAITHFULLY IMPLEMENTED and its
mutation strength HIGH (all 33 lexicon entries killed with the ruleset
digest pinned; the first held-out set's truth was copied exactly) — but
a SECOND, 51-probe held-out set found 34 confidently-wrong flips, 20 of
them genuine defects, not accepted limits:

1. **The lexicon was missing inflections (15 of the 20 defects), despite
   claiming "WITH inflections".** Every stem is now a FULL inflection
   group, including nominalisations — `deny` -> `den(y|ies|ied|ying
   |ial|ials)`, `refuse` -> `refus(e|es|ed|ing|al|als)`,
   `exclude` -> `exclu(de|des|ded|ding|sion)`, and so on for
   `prohibit`/`forbid`/`withhold`/`suspend`/`waive`/`revoke`/`fail to`/
   `cease`/`rule out`/`abolish`/`lack`/`discontinue`, plus a new
   `prevent(s|ed|ing)`. Six NEW words outside the original lexicon are
   added — `decline`, `preclude`, `reject`, "in
   the absence of"/`absent`/`absence`, "dispense with", "phase out",
   "out of the question" — every one widening a result toward
   `uncertain`, never toward `present`, the conservative direction.
   Idioms ("hardly ever") are deliberately kept OUT, named in LIMITS.
   `restrict(ion)` was MEASURED on the real 546-sentence GDPR corpus and
   deliberately NOT added: 12/546 sentences contain it, and it
   overwhelmingly names Art. 18/19's own "right to restriction of
   processing" — a legitimate safeguard, not a negation; adding it would
   risk driving THAT right's own sentences to `uncertain`.
2. **`:`/`;` removed as sentence boundaries entirely (5 of the 20
   defects).** The held-out set's own L6 ("Human intervention: none.")
   and L7 ("The following safeguards are not provided; human
   intervention, ...") showed a `:`/`;` wrongly WALLING a cue off from
   its own negator — removing them only WIDENS the negation scope, the
   conservative direction. A sentence is now bounded ONLY by a
   `.`/`?`/`!` that is itself followed by whitespace then a capital
   letter or an opening quote, or a line break — with a known
   -abbreviation exception ("Art.", "No.", "Nos.", "e.g.", "i.e.",
   "para.", "cf.", "p.") so "Art. 22(3)" is never wrongly split.
3. **Claims now match the measurement.** The module docstring and
   spec/SPEC.md §18 both state the re-measured numbers on the real
   corpus, rather than an unquantified "frequent": this example
   ruleset's cues occur in 11 sentences, 6 of them negated (`uncertain`
   fired 6 times); 161/546 sentences (29.5%) contain an un-exempted
   negation token at all; 6/99 GDPR articles get `needs_review: True`
   checked article-by-article.
4. **`host_instrument_number` moves to CALLER-SUPPLIED DOCUMENT
   METADATA, never a resolution-profile field** — a profile is shared
   across documents; the host instrument's own number is a property of
   ONE document. Threaded as an optional keyword, default `None`
   (unchanged behaviour), through `cross_reference_links`,
   `clause_cue_contributions`, `combined_contributions`, and
   `clause_cue_point`.
5. All 51 probes from this check are copied into
   `conformance/vectors/requirement-grammar/heldout2-*.json` (provenance
   "Held-out set 2"), truth copied verbatim from
   `heldout2.py`. The confusion-table test now runs over all three
   sets (probe-*/heldout1-*/heldout2-*) and asserts zero UNEXPECTED
   confidently-wrong flips — the two remaining flips (the "hardly ever"
   idiom, and the X1 cross-sentence pattern) are named, accepted
   exceptions, not silently tolerated: the test fails if either one
   disappears without the exception list being updated, or if any OTHER
   flip appears.

Held-out result after these fixes: 4/51
confidently-wrong flips against the SECOND held-out set — both
exception labels, zero new defects. A THIRD held-out set follows the
same protocol.

## Bare forms, nominalisations, conservative abbreviations

A THIRD held-out set (46 probes) found 19 confidently-wrong flips; 8
were already-named limits (six out-of-lexicon synonyms, two
cross-sentence cases), the other 11 genuine defects in three mechanical
classes:

1. **Bare forms, audited across every lexicon group.** Four groups had
   a stem whose BARE form (no suffix at all) silently failed to match,
   despite every inflected form of the same stem matching: `abolish`,
   `prohibit`, `fail ... to`, `reject`. Fixed by making each group's
   suffix optional (`abolish(?:es|ed|ing|ment|ion)?`,
   `prohibit(?:s|ed|ing|ion)?`, `fail(?:s|ed|ing|ure)?\s+to`,
   `reject(?:s|ed|ing|ion)?`). Every OTHER group in `_NEGATION_RE` was
   audited for the same gap and already had its bare form — these four
   are the complete set, matching the held-out findings exactly.
2. **Four nominalisations added.** `unavailability`, `impossibility`
   (alongside the existing bare adjectives), `cessation` (alongside
   `cease`/`ceasing`) — all three flagged by the held-out findings —
   plus `abolition` (found during an audit of the other eight
   nominalisations flagged for checking: `exclusion`,
   `prohibition`, `revocation`, `suspension`, `denial`, `refusal`,
   `waiver`, `withholding` — all eight already present).
3. **The abbreviation rule is CONSERVATIVE, replacing the closed stem
   list an earlier check relied on alone.** A `.` is not a sentence boundary
   when the token before it (a) contains ANOTHER `.` ("U.S", "C.F.R",
   "e.g", "i.e"); or (b) is a CAPITALISED token of at most 4 letters — a
   GENERAL rule (any short capitalised token, not an enumerated list),
   covering "Corp."/"Inc."/"Dr."/"Mr."/etc. without naming each one; or
   (c) is on the pre-existing stem list — the FALLBACK for a short,
   LOWERCASE stem rule (b) would miss ("para.", "cf.", "p."). Every one
   of these only WIDENS the negation scope. The accepted residual: a
   TRUE sentence end right after a short capitalised token gets wrongly
   merged with the next sentence — acceptable, since merging is the
   conservative direction and cannot by itself produce a
   confidently-wrong `present`.

Also here: a direct test (and a conformance vector) now exercises
`cross_reference_links`'s own `host_instrument_number` forwarding,
closing a gap a mutation test (HT1) found — the generic
clause-cues test threaded the keyword through
`clause_cue_contributions`/`combined_contributions`/`clause_cue_point`
already, but never through `cross_reference_links` itself. The
confusion-table test now also scores a trigger truth of "not mentioned"
(not only "negated") for a false `triggered` — the same
confidently-wrong bar, closing a scoring gap, not a grammar change. The
spec's "uncertain is frequent on real legal text" claim next to the
corpus measurement is replaced with the measured numbers stated
plainly.

All 46 probes from this check are copied into
`conformance/vectors/requirement-grammar/heldout3-*.json` (provenance
"Held-out set 3"). `_KNOWN_ACCEPTED_FLIPS` gains exactly the
eight flip labels named as accepted limits (six out-of-lexicon
synonyms, two cross-sentence cases) — never an F- or B-labelled case;
none of these fixes happened to resolve any of the eight, so none are
dropped.

Held-out result after these fixes: 8/46 confidently-wrong flips against
the THIRD held-out set — all eight already-named, accepted limits,
zero new defects, zero of the original eleven mechanical defects
remaining.

## Performance, a correction, and per-alternative behavioural coverage

Review found "most criteria pass" but flagged four remaining items:

**P — a superlinear run time, CRITICAL.** `_sentence_span` recomputed
every sentence boundary for the WHOLE text on EVERY cue occurrence, and
the abbreviation check scanned from position 0 of the text every time.
Measured: 31k chars took 3,723s (0.19s before the
abbreviation rule existed); the whole GDPR corpus as one text took
~400s. Fixed by caching `_sentence_boundaries` per text
(`functools.lru_cache`) and looking it up with `bisect` (O(log n)
instead of a linear rescan); anchoring the abbreviation token/stem
search to a 40-character look-back window instead of position 0; and
caching `_sentence_is_negated` too, since the accepted abbreviation
-merge residual (below) can make many occurrences share one large
merged "sentence" string, which would otherwise be rescanned from
scratch for each one. After the fix: 31k chars in ~0.02-0.03s; the
whole GDPR corpus as one 183k-char text in ~0.08-0.16s; 200k chars in
~0.15s (performance-test bound: 2.0s). A wall-clock test and a
deterministic cache-hit-count test (`cache_info()` before/after) both
guard the fix, so a future regression that reintroduces the
recomputation is caught even on a machine fast enough to still clear
the wall-clock bound.

**N — missing nominalisations (7 of 12 flips), including a
BROKEN earlier claim.** `abolish(?:...|ion)?` spells the non-word
"abolishion", never the real word "abolition" — an earlier
claim that this covered "abolition" was simply wrong, not merely
imprecise; "abolition" is now its own lexicon alternative. Five more
forms: `inability`, `discontinuance` (alongside "discontinuation"),
`prevention` (alongside "prevent"), `preclusion` (alongside
"preclude"), and a hyphen accepted as a "phase ... out" separator
("phase-out"/"phased-out"). "Failure of X to" — the task's own choice
between "allow up to 3 words between 'failure' and 'to'" or "treat a
bare 'failure' as negation-ish" — is handled by the SECOND option: a
bare "failure" noun is its own negation-ish alternative, needing no
gap-counting logic at all.

**A — abbreviations (5 of 12 flips).** Rule (b) is now
CASE-INSENSITIVE for a token of at most 4 letters ("etc.", "lit.",
"sec."), and the CAPITALISED-only cap is raised from 4 to 5 letters
("Admin.", "Assoc."). LIMITS now names the residual plainly: a
capitalised abbreviation of 6 OR MORE letters followed by a capital
letter is caught by neither cap, and — unlike the short-token MERGE
residual, which is always safe because it only ever widens — a wrong
SPLIT here can separate a cue from its own sentence's negator, the same
class of risk as "a word outside the lexicon"; this narrows the
gap but does not close it.

**M — test power: 130 behavioural vectors, one per `_NEGATION_RE`
alternative (corrected in a follow-up).** A mutation
measurement found only 47 of 99 single-inflection alternatives killed
by BEHAVIOUR — the rest were only killed by a DIGEST comparison, which
trivially changes whenever any lexicon text changes and proves nothing
about whether that SPECIFIC word is checked anywhere. 130 vectors were
generated programmatically from the regex structure (one real-English
sentence per alternative, using the exact surface form); a mutation run
with the ruleset digest PINNED to its original value and the dedicated
digest-change test deselected confirmed 127/130 flip from negated to
affirmed when ONLY that one alternative is removed.

**A follow-up corrected an initially FALSE claim: `can\s+not` is NOT
redundant with `not`.** It is isolated through the "not only ... but
also" exemption: "The data subject can not only obtain human
intervention but also contest the decision." reads `uncertain` at
HEAD. The exemption span is anchored at the WORD "not" (the start of
"not only"); `can\s+not`'s own match starts one word EARLIER, at "can",
so it falls OUTSIDE the exempt span, while the bare `\bnot\b`
alternative's own match (starting at "not" itself) falls INSIDE it and
is exempted — removing `can\s+not` alone flips this exact sentence to
`present`. Only the remaining 2 alternatives
(`under\s+no\s+circumstances`, `in\s+the\s+absence\s+of`) are
genuinely STRUCTURALLY redundant with a shorter alternative already in
the lexicon (`no`, `absen(?:t|ce)` respectively) — any sentence
containing the longer phrase necessarily contains the shorter word
too, so no sentence can isolate the longer phrase's own removal; this
is stated here rather than papered over with a sentence that would not
actually prove what it claims to. Vectors were also added for the
cap-at-5 rule, the case-insensitive short stems, and "cf./p. <Capital>".

All 45 probes from this check are copied into
`conformance/vectors/requirement-grammar/heldout4-*.json` (provenance
"Held-out set 4"). Held-out result after these fixes: 0/45
confidently-wrong flips — every one of set 4's own 12 flips is fixed;
none are added to `_KNOWN_ACCEPTED_FLIPS`.
