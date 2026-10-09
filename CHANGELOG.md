# Changelog

## Unreleased

### Added

- A 5D fingerprint/coordinate specification (draft 1.0, `spec/SPEC.md`):
  the closed five-dimension set and canonical order, the composition algebra,
  the 5D fingerprint of an entry, 5D's neutrality on is/ought (is and
  ought live in nD grammars, as an optional co-dimension), the assertoric
  (factual) lowering layer, and the nD grammar contract. No Loomground
  repository conforms to this spec yet; versum, solver, and the grammar
  planes are its planned consumers.
- A stdlib reference implementation for the specification
  (`src/five_d_nd/`): the dimension algebra, the 5D fingerprint, the
  assertoric lowering layer, and `NDSystem`/grammar-descriptor validation.
- Machine-readable vocabulary (`vocabulary/`) and JSON Schemas (`schema/`)
  for the 5D layer, plus a conformance vector suite and runner
  (`conformance/`, `tests/test_conformance.py`).
- Typed Statements (spec §21-§23): a richer, reified edge on top of the
  plain triple, with its own codebook (`docs/codebook/typed-statements-v1.md`,
  v3.5) and gold-annotation protocol (`docs/codebook/gold-protocol-v1.md`).
- A typed-Statement extractor (`src/five_d_nd/extract/`): a deterministic
  clause/list-item segmenter and a closed cue-rule table that propose
  candidate Statements from legal text (pure stdlib, no ML, no network —
  the same input always gives the same candidate set). It composes with a
  model-assisted decision stage (spec §23a): a model's answer for a given
  candidate set is recorded once, content-addressed, and thereafter only
  replayed — never recomputed or re-queried. A cache miss raises rather
  than silently falling back to an unassisted result.
- Actor-role and typed-Statement predicate vocabularies (the latter now
  at v3.5).
- A benchmark result (`docs/benchmark-2026-10.md`): a pre-registered
  cross-law provision-matching gate on the typed 5D signal against a
  structural baseline, plus a second pre-registered round on a
  concept-typed, rarity-weighted signal. Both rounds are a loss. 5D
  stays a labelled structural index with no role in the migration (the
  dim5 → 5D migration), and no claim is made.
- A new typed-Statement predicate, `addressed_to` (relational, spec
  §21, `typed-statements-v3.6`): the recipient of an act or
  communication, as its OWN endpoint, cued by a notify/report/inform/
  communicate/submit/transmit verb followed by its own recipient
  (either via an explicit "to" or as a direct object). Before this,
  "to WHOM" an act ran had no edge of its own — GDPR Art. 33(1)'s own
  "notify the personal data breach to the supervisory authority" gave
  the supervisory authority no endpoint; it was text buried inside
  `performs`'s own object. The recipient NP is TYPED: the closed
  `ACTOR_ROLES` token where it matches, otherwise the documented
  `other(label)` escape.
- A deterministic deadline SPLIT for `deadline_of`, for TWO NEW cues
  only: a spelled-out-number duration ("not later than N days/weeks/
  months", "two days", "one month") and a qualitative cue ("without
  undue delay", "promptly", "immediately", excluding the adjectival
  "immediately applicable"). Either cue is split out into its own
  `deadline_of` Statement, co-existing with whatever predicate already
  claims the host clause (`performs`, `competence_of`, `requires`,
  `except_when`, ...) rather than one silently dropping the other.
  `rules.Candidate`/`build.BuiltStatement` gain a `never_conflicts`
  field (`extract.build.resolve_overlaps_built`) so `addressed_to` and
  ONLY these two NEW deadline cues are exempt from first-claimed-
  span-wins overlap resolution — a pure addition that never blocks,
  and is never blocked by, anything (a scan span's own last-resort
  fallback included: before either cue existed, nothing stopped that
  fallback from surviving there either, so nothing now does). **The
  pre-existing, pre-v3.6 DIGIT-based "within N" cue keeps its
  pre-v3.6 conflict setting (`never_conflicts=False`) — it still
  blocks, and is blocked by, a real predicate as before.** One
  observable consequence of the new subject binding: in AI Act Art.
  73(2) the digit cue's `deadline_of` ("The report referred to in
  paragraph 1 shall be made" -> "15 days") now survives where a
  last-resort copula-fallback `predication` ("report referred to in
  paragraph 1" -> "made immediately after ... not later than 15 days",
  negation `present`) previously survived instead. The fallback was a
  low-confidence reading with a wrong negation state; the time limit it
  is replaced by is correct. This is the only removed non-`deadline_of`
  Statement observed in the four reference articles and a seeded
  28-article sample.
  The hybrid/DecisionCache path (`extract.hybrid`) is UNCHANGED: a
  human/model decider's own final span choice there is still
  reconstructed via `spans.span_text` alone, the same as every other
  predicate, by design — only this deterministic rule-layer pipeline's
  own `build_statement()` types/normalises an `addressed_to`/
  `deadline_of` obj, as a per-predicate post-processing step on the
  already span-derived text. `deadline_of`'s own obj (every cue,
  including the pre-existing digit one) is now the NORMALISED limit
  ("72 hours after having become aware of it" -> "72 hours").
- `deadline_of`'s own SUBJECT is now the GOVERNED ACT, never a clause
  subject, a sentence fragment, a connective, or a pronoun
  (`build._rebind_deadline_subjects`), applied to EVERY `deadline_of`
  Statement (every cue, including the pre-existing digit one) after
  overlap resolution: rebound to the nearest companion Statement
  (`addressed_to`'s own act; `performs`/`competence_of`'s own act; a
  TRUSTED `requires` consequence ACT — excluding a one-word
  antecedent misfire and the "subject to [condition]" cue — but ONLY
  when the time limit sits in the CONSEQUENCE, never the antecedent;
  a TRUSTED `except_when` exception condition from its "unless"/
  "except where" cue family only, excluding its "notwithstanding/
  subject to [provision]" cue family, whose own obj is a bare
  provision reference, never an act) that shares its clause, falling
  back to a chapeau's own governing act or a passive construction
  ("the report ... shall be made") in the same sentence. **A time
  limit sitting INSIDE a conditional ANTECEDENT ("Where the request
  is not answered within 30 days, ...") is bound to the antecedent's
  own act, NEVER the consequence** — detected by literal span overlap
  with the `requires` candidate's own antecedent (`subj`) half rather
  than its consequence (`obj`) half; since this extractor has no
  separately-extracted "just the antecedent's own trimmed act" text,
  the Statement's ORIGINAL, pre-rebind subj (already reading as the
  antecedent clause, e.g. "Where the notification ... is not made")
  is kept UNCHANGED rather than guessed at or replaced. When NO
  companion, antecedent, chapeau act, or passive construction can be
  found: a NEW deadline cue (`never_conflicts=True`) is DROPPED
  outright (main never produced this Statement, so there is nothing
  to preserve); the pre-existing digit-based cue (`never_conflicts=
  False`) instead keeps its ORIGINAL, pre-rebind subj UNCHANGED — main
  already produced this exact Statement, and finding no governed act
  to rebind it to is never a licence to remove or alter what main
  already had.
- The `addressed_to` recipient-typing fixes (`type_recipient_actor`,
  `rules._RECIPIENT_HEAD_RE`): a possessor NP ("the findings OF the
  market surveillance authority", "the decision submitted BY the lead
  supervisory authority") is never a recipient — "of"/"by" are
  excluded from the head check's own filler words, and "by X" is
  rejected outright as a passive-voice AGENT, never a recipient,
  regardless of context. "national market surveillance authority"
  types as `market_surveillance_authority` (a single leading modifier
  word no longer blocks the role match). A leading discourse/
  quantifier word ("those", "other", "first", ...) is stripped
  iteratively before typing, fixing a mislabelled `other(...)` escape
  that used to carry one through (`other(first_the_provider)` ->
  `provider`). An `other(...)` label is now truncated at the nearest
  `_`, never mid-word.
- `rules.collect_segmented_candidates`'s own chapeau-subject-
  inheritance decision ("did this scan span produce nothing but the
  last-resort fallback?") now IGNORES a `never_conflicts` candidate
  (`addressed_to`, a NEW deadline cue) when answering that question —
  without this, a chapeau list item whose own text ALSO happens to
  carry a "notify ... to X" cue would silently lose its own
  chapeau-inherited subject/predicate and fall back to the raw,
  un-inherited fallback instead, producing a Statement main never
  produced.
- 18 new conformance vectors (`conformance/vectors/extractor/`) and new
  unit tests (`tests/test_extract.py`) covering `addressed_to`'s
  positive cues (a "to"-form and a direct-object recipient, GDPR Art.
  33(2)/NIS2/AI Act/DSA-shaped sentences), its required negative
  "to"-idioms and possessor-NP/passive-agent negatives, the two NEW
  `deadline_of` cues and their co-existence with `performs`, the
  antecedent-vs-consequence and `except_when`-exception-condition
  subject-binding rules (AI Act 73(8)/DSA Art. 87-shaped
  reproductions), and the pre-existing digit-based cue's own
  unchanged conflict/no-governed-act behaviour. 5 pre-existing
  extractor vectors changed, each only by the new Statements or the
  subject binding above: `deadline_of-within-n` (obj normalised from
  "72 hours after becoming aware of it" to "72 hours", hence a new id;
  its statement count is unchanged), `performs-actor-roles-with-modal-
  interruption` and `requires-in-the-case-of` (each gains the new
  `addressed_to`/`deadline_of` Statements), and
  `performs-and-deadline-of-coordination-no-comma` and
  `requires-and-deadline-of-co-coded` (the `deadline_of` subject is now
  the governed act instead of the actor). No pre-existing Statement in
  any of them was removed.
- `deadline_of` (relational — temporal, spec §21, `typed-statements-
  v3.7`) emits a DATED or PERIODIC time limit, in addition to the
  pre-existing bounded-duration and qualitative cues: a DATED limit
  anchored to a calendar date rather than a count ("by 25 May 2018",
  "by the date of application"), and a PERIODIC, recurring duty
  ("annually", "at least once a year"/"at least once every year",
  "every six months"/"every two years", "on a regular basis",
  "periodically"). Both cue families are `never_conflicts` pure
  additions, the same v3.6 convention. Subject binding is the
  IDENTICAL v3.6 rule, unmodified: the governed act, never a clause
  subject/fragment/pronoun/connective; with no governed act in the
  clause, a v3.7 cue emits nothing. obj normalises to `"by <date>"`
  for the dated cue, `"annually"`/`"every N months"`/`"every N
  years"`/`"periodically"`/`"regularly"` for the periodic cue — see
  `vocabulary/statement-predicates.json`'s own `deadline_of` definition
  for the full table. EXCLUDED, denied before a candidate is even
  built: a SCOPE/eligibility date describing which instances a
  provision covers ("AI systems ... that HAVE BEEN placed on the
  market ... before 2 August 2027"); a retrospective retention/
  look-back window ("in the 12 months' period before the beginning of
  the audit", "for a period of six months"); an entry-into-force/
  application-date clause in a final provision; and a periodic adverb
  modifying a past/perfect participle that describes report CONTENT
  rather than a duty ("the number of disputes ... has received
  annually" names a count, never a duty). A GENUINE transitional duty
  right next to an excluded scope date in the SAME sentence ("...
  before 2 August 2027 shall be brought into compliance ... by 31
  December 2030") still gets its own clean edge. A bare number or
  date-shaped scrap ("2025") is never itself a governed act — where no
  other act text can be found (e.g. "Codes of practice shall be
  ready ... by 2 May 2025", "ready" an adjective, never a participle),
  the Statement is dropped rather than keep a subj known to be wrong.
  `build._rebind_deadline_subjects` gains an OPTIONAL `all_built`
  parameter (the pre-overlap-resolution candidate list): the dated/
  periodic cues' own companion search uses it instead of the narrow,
  post-overlap `built` pool, since a fronted cue's own trigger word can
  collide with `precedes`'s own unbounded-greedy obj capture, and a
  pronoun-subject or elided-subject clause ("They shall carry out ...",
  "... and shall encourage ... on a regular basis") has no companion
  `performs`'s own closed actor-NP shape could ever fire on — the
  pre-existing digit-based and qualitative cues keep searching the
  narrow pool only, completely unchanged. The last-resort act fallback,
  v3.7-only, is split into an ACTIVE-voice search (the nearest
  "shall/may/must <act>", regardless of the preceding actor NP's own
  shape or absence, bounded so it never reaches backward across a
  conditional subordinator or a coordinated "and/or shall" clause
  boundary into an UNRELATED earlier clause's own act) and a STRICT
  passive-voice search (a genuine past participle after "shall/may/
  must be", never a bare adjective like "lawful"/"ready", and never a
  bare adverb with the real participle one word further on; the
  calendar month "May" is excluded from ever matching the modal "may").
  `except_when`'s own exception condition is never a trusted companion
  for these two cues at all (the pre-existing digit-based cue's own R-n
  binding to that same condition is unaffected). A v3.7 act text found
  via any source has a trailing deadline_of cue of its own stripped
  back out of it ("report annually" companion-bound unchanged ->
  "report") — `strip_trailing_deadline_cue`. A companion ending in a
  dangling coordinating conjunction (", and"/", or" — a span-boundary
  misfire) is never trusted, restricted to the two v3.7 cues only; the
  pre-existing digit-based cue's own exact main-branch behaviour,
  dangling companion included, is reproduced byte-for-byte.
  No pre-existing Statement is removed or altered by any of the above;
  no new Statement of a predicate other than `deadline_of` is added.
- New conformance vectors (`conformance/vectors/extractor/`) and unit
  tests (`tests/test_extract.py`) covering the dated and periodic
  `deadline_of` cues' positive cue families (literal calendar date,
  every periodic normalisation shape, a dated cue and a periodic cue
  co-existing in one modal interruption) and their required negatives
  (the scope-date exclusion paired with a genuine transitional duty in
  the same sentence, the retrospective-window exclusion, the
  entry-into-force exclusion, the content-description exclusion, the
  numeric-scrap-subject guard, a periodic cue in a coordinated second
  clause binding to its own act, and the no-governed-act drop rule).
  2 pre-existing extractor vectors (`precedes-fronted`, `precedes-
  prior-to`) are unchanged from main. No pre-existing Statement was
  removed or altered; no new Statement of a predicate other than
  `deadline_of` was added.
- A THIRD EXAMPLE nD grammar, `src/five_d_nd/grammars/interplay.py`
  + `interplay_rules.json`: a closed, ten-relation vocabulary of typed
  relations BETWEEN legal instruments (`same_definition`, `cumulative`,
  `complementary`, `alternative`, `substitutive`, `separate_tracks`,
  `non_cumulative`, `no_presumption`, `defers_to`, `reference_redirect`),
  each with a stated 5D projection and reason, read deterministically from
  scope clauses by a cue-rule table (rules are data, not code — the same
  discipline `requirement.py` already establishes). A citation resolver for
  the seven instrument-citation forms the GDPR/ePrivacy/e-Commerce/DSA/
  NIS2/AI-Act/Directive-95-46 corpus uses, including an elided-list
  continuation that carries no kind word of its own; unknown instruments are
  kept as `external:<kind>-<year>-<number>`, never dropped. A clause that
  names only the citing instrument itself (a self-citation or a bare "this
  Regulation"/"this Directive") produces no record; a clause that names
  nothing at all produces an `unresolved: True` record (or none, for a cue
  that opts out via `suppress_if_unresolved`) — `relation_to_triple` refuses
  to convert an unresolved record. An authority-sourced ingestion path
  (court rulings/regulator guidance that type a relation not stated in the
  statute) ships as API + validation only, seeded with no data. New spec
  section (`spec/SPEC.md`), 48 conformance vectors
  (`conformance/vectors/interplay-grammar/`), and a self-contained test
  module (`tests/test_interplay.py`). The citation resolver also accepts
  a PLURAL kind word ("Regulations (EU) 2016/679 and (EU) 2018/1725") and
  the older "Regulation (EU) No 1025/2012" number-then-year form, both
  normalised into the same `<kind>-<year>-<number>` id order; the
  article-lookback also captures a trailing "Article N, point (x)"
  reference; and every record carries its own `match_start` offset so two
  records whose text happens to be byte-identical are still told apart.
- A FOURTH EXAMPLE nD grammar, `src/five_d_nd/grammars/penalty.py`
  + `penalty_rules.json`: a closed, versioned record for a penalty clause
  (`administrative_fine`, `periodic_penalty_payment`, `penalty` — the
  Member-State "effective, proportionate and dissuasive" rules a
  directive/regulation leaves to national law — or `criminal_sanction`),
  read deterministically from statute text by a cue-rule table (rules are
  data, not code). A single stated 5D projection, `causal`, covers EVERY
  penalty kind: the edge is (infringement of ONE cited provision) -> (the
  penalty) — `penalty_to_triples` (plural) emits one edge PER infringed
  ARTICLE, a "<N> to <M>" range expanded into each article, `s` shaped
  `"<instrument>:Art.<N>"` with any parenthesised sub-point STRIPPED and
  the three tokens de-duplicated into one edge ("33(1)"/"33(3)"/"33(4)"
  all resolve to the SAME `ai-act:Art.33`, never three separate,
  non-joining nodes — the sub-point detail moves to the triple's own
  `provenance.provisions_detail` instead), and `o` UNIQUE per penalty
  clause (never merely per article, so e.g. GDPR Art. 83(4)/(5)/(6) each
  get their own node). Capture of an infringed provision is GATED on an
  infringement-anchor phrase ("infringements of ... provisions",
  "non-compliance (?:of|with)", "infringe(s/d)", "fail(s/ed) to",
  "refuse(s/d) to", "in breach of", "supply incorrect, incomplete or
  misleading information") — never a bare "Article N" mention nearby a
  procedural cross-reference ("the decision referred to in Article 73",
  "the person referred to in Article 67(1)"), which is never captured at
  all. Text following "other than"/"except(ing)"/"excluding"/"with the
  exception of" is read as `excluded_provisions`, masked out BEFORE
  infringement scanning so it can never also surface as infringed; an
  instrument-wide clause with no specific provision left once masked
  carries a `scope` note instead of an edge. A Chapter reference
  ("Chapter IX") is captured alongside an Article one; a bare
  parenthesised sub-point continuation ("(3)", "(4)") reattaches to the
  most recently seen article number. Reads a fixed EUR
  amount (plain-space, no-break-space, or spelled-out-in-words
  separators) and a turnover percentage (plain or decimal-comma), a
  combination rule (`whichever_is_higher`/`whichever_is_lower`/`none`),
  and a bound type (`ceiling`/`floor_of_maximum`/`minimum`/`unspecified`)
  from two further small phrase tables, also data. The clause span runs
  to the real sentence end (skipping a stray period-then-comma typeset
  error) or RAISES rather than silently truncating. An `unresolved`
  record (its own amount or bound could not be parsed) refuses to become
  a triple; a record naming no infringed provision converts to an EMPTY
  triple list instead — never an error, for a DIFFERENT, documented
  reason. An authority-sourced ingestion path ships as API + validation
  only, seeded with no data. New spec section (`spec/SPEC.md` §25), 49
  conformance vectors (`conformance/vectors/penalty-grammar/`) — ten of
  them the real GDPR/AI-Act/DSA/NIS2 fine/penalty articles this grammar
  was built against, verbatim — and a self-contained test module
  (`tests/test_penalty.py`), including a regression asserting no two
  distinct clauses ever share an edge subject node.

### Fixed

- `resolve()`: same-length content tampering (a stored span edited so its
  length is unchanged but its content differs) is no longer invisible to
  the span check. New optional `source_text` / `expected_content_digest`
  arguments let a caller supply independent ground truth; `resolve()`
  fails closed (`SpanMismatchError`) against either when supplied.
- `resolve()`: the `MissingStoreError` contract is now literal — an
  absent, non-path, or empty `store`, and `versum` not being importable,
  all raise `MissingStoreError`.
- `pyproject.toml`: the `grounding` extra no longer pins a
  `loomground-versum` tag that lacks a function this package needs; it is
  left unpinned, with a documented local-development install path.
- Tests needing the optional `versum` dependency now skip, with a stated
  reason, when it is unavailable, rather than erroring.

### Changed

- Repository layout: `five_d_nd/` moved under `src/`; licensing moved to
  `LICENSES/` + `NOTICE` + `REUSE.toml`; the version is single-sourced
  from `src/five_d_nd/_version.py`.
- `docs/model.md`, `README.md`, `llms.txt`: corrected the description of
  `dimensions` in a `5d+nd` reference, and of `resolve()`'s own return
  shape.


## [0.2.2](https://github.com/flxk1/5d-nd/compare/v0.2.1...v0.2.2) (2026-09-29)


### Documentation

* neutralize Federation wording in dimensions adapter note ([c12eae7](https://github.com/flxk1/5d-nd/commit/c12eae7a1edfc0e9f14445257f96d4b93b2ec18a))

## [0.2.1](https://github.com/flxk1/5d-nd/compare/v0.2.0...v0.2.1) (2026-09-28)


### Documentation

* correct stale claims; add How this is made ([21c3772](https://github.com/flxk1/5d-nd/commit/21c3772ddd23834ff3f784fe267d477daca1f5ee))
* fix stale version, add How this is made section ([f2ebce2](https://github.com/flxk1/5d-nd/commit/f2ebce2d26675e9847feb41a8792a8ad2b06281b))

## [0.2.0](https://github.com/flxk1/5d-nd/compare/v0.1.0...v0.2.0) (2026-09-11)


### Features

* 5d+nd reference grounding resolver (one scheme, composes on the dimension algebra) ([32bc8c6](https://github.com/flxk1/5d-nd/commit/32bc8c6738691ef29c5ba19adc6d6e3ffa1d8a4f))


### Bug Fixes

* **release:** extra-files + version marker, not version-file ([62c390c](https://github.com/flxk1/5d-nd/commit/62c390c73235f646e3cb45c942b7bff9a7ff52a2))


### Documentation

* decouple README from sibling repos ([c9ec51f](https://github.com/flxk1/5d-nd/commit/c9ec51f73ff78dd8b1ddd7081d53c0313531ca70))
* llms.txt generated from README ([a26cdd3](https://github.com/flxk1/5d-nd/commit/a26cdd37916c084f620b2b6715b4644514a6bb66))
* README Problem + executed Example (186 words) ([5d71a78](https://github.com/flxk1/5d-nd/commit/5d71a78e34ebba1abaedf79165098ffa44bb92aa))
* README to canon (148 words), description, Family ([72aa89e](https://github.com/flxk1/5d-nd/commit/72aa89eee1cffa647135784a1a9a1937e0b998e6))

