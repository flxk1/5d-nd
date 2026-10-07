# 0010 — The deterministic typed-Statement extractor

## Status

Accepted (as a built deliverable). Additive to §21-§23 (the typed-Statement
layer, `statement.py`, `schema/statement.schema.json`, the codebook) —
changes none of their decisions, and edits none of their owning files.
This ADR records the design choices made inside this extractor's own
territory (`src/five_d_nd/extract/`, `tests/`,
`conformance/vectors/extractor/`).

## Context

The codebook and gold come first (`statement.py`'s own module docstring);
a deterministic extractor is the second deliverable, built against an
already-fixed schema (§21) and codebook (`docs/codebook/
typed-statements-v1.md`). A rule-based extractor with no clause parser is
not expected to reach human-coder agreement on a first pass; the gap to
that ceiling is measured on a development set, not published here.

## Decision

1. **No clause segmenter in this stage.** The codebook's own unitisation
   rules (clause span = "the smallest complete clause that carries the
   relation"; chapeau+list items; coordinated-conjunct splitting; whole-
   naming chapeaus) describe a real constituency-aware segmentation this
   module does not attempt on its own — `src/five_d_nd/extract/segment.py`
   (a separate module) supplies that. Each predicate rule here is a regex
   searched directly over a clause/list-item span; the matched span
   doubles as the clause span.
2. **Rules are written from the codebook's own prose and from
   `clause_cues.py`'s own (read-only, imported) cue vocabulary — never
   from gold text.** Every regex's own comment cites which codebook
   section motivated it. No rule's own pattern was derived by inspecting
   a gold unit's surface wording, and no vector's own `unit_text` is a
   60-character-or-longer verbatim quote from a real development-set
   unit (checked by
   `tests/test_extract.py::test_no_vector_input_text_is_a_long_verbatim_corpus_quote`).
3. **Span finalisation is a small, composable pipeline
   (`extract/spans.py`)**: whitespace-trim, strip one leading determiner
   (R-o's own exemption for "part of" is in the determiner list's own
   exclusion, never stripped), strip a leading modal (R-k) where the
   owning rule says to, and truncate a span at a mid-span modal token for
   the predicates whose own captured text should never legitimately
   contain one at all (`truncate_midspan_modal`, a `Candidate` field; off
   for `requires`/`performs`/`competence_of`/`predication`/the purpose
   predicates, whose own simple regex grammar can legitimately capture a
   repeated subject before the clause's own modal — a documented
   limitation, see that field's own docstring).
4. **`layer_of()` is a documented approximation**, not a full
   reproduction. The codebook's own layer rule needs the clause's own
   text position (recital vs operative article) — metadata this module
   only has when `extract(unit_text, *, enclosing_provision=None)` is
   given it. Rule 1 (`is_a` -> `deep`) is reproduced exactly; rule 3 (a
   recital, unless rule 1/2 already applies) is reproduced when
   `enclosing_provision` is given (`"recital"` found, case-insensitively
   -> `surface`); rule 2 (a principle stated as a principle -> `deep`)
   has no reliable text-only signal and is not attempted;
   `legislative_purpose_of` defaults to `surface` as a documented
   stand-in when no metadata is given; every other predicate defaults to
   `domain` (rule 4, "everything else operative").
5. **Negation is a named, versioned, pluggable module
   (`extract/negation.py`)**, not hardwired. `negation_v34` is a
   deterministic proxy for the codebook's own sentence-level procedure
   (R-n's own `requires`/`deadline_of` -> always `"absent"` reproduced
   exactly; the remaining states approximated by "a negator inside the
   clause but outside the subj span" -> `"present"`, "a negator
   elsewhere in the unit text" -> `"uncertain"`, "no negator anywhere" ->
   `"absent"`) — a proxy, not a claim of equivalence.
   `register_negation_rule()` is the single drop-in point for a later
   negation version — no other file in this package needs to change.
6. **Every Statement carries `extraction_rule_id` and `edge_confidence`.**
   `edge_confidence` is a per-rule, hand-set base value (never tuned
   against gold), roughly tracking how distinctive each rule's own cue is
   (a quoted-term "means" definition is high; the last-resort whole-unit
   fallback is low).
7. **`extract()` is pure stdlib, no ML, no network, and deterministic by
   construction**: every step is `re` plus arithmetic over a fixed
   string, walked through a fixed list (`extract.rules.RULES`), with the
   one final sort (`statement.sort_statements`) using a stable,
   documented key —
   `tests/test_extract.py::test_extract_is_deterministic_byte_identical`
   and the per-vector determinism test both check this directly.

## Known imperfections (named rather than hidden)

- No general coordination/chapeau mechanism beyond the cases this module
  and the segmenter it composes with already handle (a `:`/`;` clause
  boundary, `requires`+`deadline_of`/`precedes` co-coding on the same
  trigger-with-duration clause, and the "subject to—" chapeau+list
  expansion).
- No real NP parser: a relative pronoun ("personal data WHICH form part
  of...") or a reduced relative is not folded into the maximal NP the way
  the codebook's own unitisation rules require; it is captured verbatim
  as part of whichever span the regex happened to bound.
- A residual leading-modal token still appears inside a captured span on
  a measurable minority of development-set Statements, concentrated in
  the two `predication` fallback rules and in `requires` consequences
  that carry a second modal deeper in the sentence — the leading-prefix
  strip (decision 3, above) removes only the leading subject+modal, by
  design; a later modal in the same consequence is untouched. This is
  the actual shape of what a leading-prefix strip can and cannot do
  without a full parser.
- `except_when`'s own definition prose ("the subject's own general rule
  does not apply under the condition named by the object") is, read in
  isolation and without its own worked examples, ambiguous about which
  side of a "by way of derogation from X, Y"/"subject to [provision]"
  clause is `subj` and which is `obj`. The codebook's own UK DPA 2018
  s. 6(1) worked example resolves it (general-rule remainder on `subj`,
  provision on `obj`), and this module's rule follows that direction; a
  reader who stops at the definition sentence alone could reasonably
  code it the other way. Worth a one-line addition to the definition
  itself (naming which side the provision goes on).

## Requests to other territories

- **`statement.py` / `schema/statement.schema.json`**: no change
  requested — the extractor builds against the current schema cleanly.
- **`tests/test_conformance.py`'s own `FAMILIES` registry**: not edited
  here — the `extractor` vector family is run by `tests/test_extract.py`
  instead. A future change could fold `"extractor"` into `FAMILIES` if a
  single shared runner is preferred; this ADR records that the family
  exists either way.

## Consequences

Figures measured against this module's own development set (predicate,
dimension, layer, and negation agreement; Statements-per-unit) are not
published in this repository — they live in an un-shipped local
evaluation script's own output, outside this package and outside
version control, and are not a claim of parity with a human coder.
