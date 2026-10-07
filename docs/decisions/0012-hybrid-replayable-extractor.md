# 0012 — The hybrid, replayable extractor

## Status

Accepted (as a built deliverable), and APPLIED to the specification.
Additive to §21-§23 and to ADRs 0010/0011 — changes none of their
decisions. The spec text below ("Applied spec text") is now live in
`spec/SPEC.md` as §23a.

## Context

A purely deterministic, rule-based extractor reaches a ceiling well
below human-coder agreement, because it has no way to use context
beyond regex matching. The chosen design: deterministic code proposes
(segmentation, NP chunks, candidate Statements); a pinned model
chooses among those candidates, and may add only a Statement built
from already-proposed spans; every model answer is cached and
replayed, never recomputed from the model at run time.

## Decision

`src/five_d_nd/extract/hybrid.py` implements three stages:

1. **`propose(unit_text, enclosing_provision=None) -> CandidateSet`**
   — deterministic, stdlib, recomputed every time. Segments the unit
   (`extract.segment.segment`), runs `extract.segment.np_chunks` over
   the whole unit, and runs the existing closed cue-rule table
   (`extract.rules.collect_candidates`) over every leaf clause/list-item
   span — without the overlap pruning the non-hybrid pipeline applies:
   every candidate a cue fires survives, multiple per clause, each
   carrying its own `rule_id` and codebook citation. Each candidate's
   own raw subj/obj span is finalised (determiner/modal-stripped, R-k/
   R-q) before it reaches the `CandidateSet` — `extract.build.
   finalize_candidate_spans()` is shared by both the hybrid and
   non-hybrid pipelines, so span finalisation never diverges between
   them. A `CandidateSet` is canonical JSON (sorted keys, no
   `ensure_ascii` escaping, compact separators) with its own sha256.
   `allowed_spans(candidate_set)` draws from four sources, pooled: every
   segmentation node's own span, every NP chunk, every candidate's own
   clause/subj/obj span, and `extra_allowed_spans` — inherited
   (chapeau) subject spans and finite-relative-clause antecedent spans
   that are not already one of a candidate's own endpoints.
2. **`decide(candidate_set, coder_view_text, ...) -> Decision`** — never
   calls a model inside this package. `mode="replay"` (the default)
   reads a `DecisionCache` entry keyed by `CacheKey(candidate_set_sha,
   coder_view_sha, model_id, prompt_template_sha)`; a miss raises
   `CacheMissError`. `mode="record"` raises `NotImplementedError` —
   recording a real Decision is external tooling (a blind reviewer
   process writing cache files; no API key is used inside the
   package), which this package does not implement.
3. **`assemble(candidate_set, decision, ...) -> list[dict]`** —
   deterministic. A Decision's own span adjustment, or an added
   Statement's own endpoint, is accepted only when it is a member of
   `allowed_spans(candidate_set)` — anything else raises `ValueError`,
   checked every time a cached Decision is assembled, not only once at
   record time. Every assembled Statement's own `extraction_rule_id` is
   `"<rule_id>|model-decision:<cache_key_digest>"`.

**`DecisionCache`** is a content-addressed, file-backed cache: one file
per key digest, idempotent re-record of identical content, `ValueError`
on a re-record with different content at the same key (immutable once
written). `manifest()`/`manifest_sha256()` give the cache's own
content-addressed summary — reported alongside any result, so a reader
can verify exactly which recorded decisions produced it.
`DecisionCache.record()` checks that the Decision given to it recomputes,
from its own four identifying fields, to the same key it is being
written under — a forged or mismatched entry is rejected at write time.

**`export_decision_requests(units, out_dir, coder_view_text=...)`**
writes one request file per unit — the `CandidateSet`, the coder-view
text (never gold), the prompt template (plus its own sha256), the model
id, the computed cache key, and the expected-output JSON Schema
(`DECISION_JSON_SCHEMA`). `units` is a plain caller-supplied mapping —
this function reads no hardcoded data path itself.
**`import_decisions(decisions_dir, cache)`** is the counterpart: it
reads every `<cache_key>.json` Decision file a reviewer has answered,
validates it against `DECISION_JSON_SCHEMA`, and records it into
`cache` — `record()`'s own integrity check catches a file saved under
the wrong cache-key filename.

**`PROMPT_TEMPLATE_V1`** (stored in the package, with its own sha256)
instructs the decider to apply the coder view to the unit text, choose
and label among the candidate set's own candidates, and add only a
span-constrained Statement — it never mentions or contains the word
"gold" anywhere in its own text (checked by a test), and the unit text
it is paired with carries no reference answer of any kind.

**`assemble_with_spans()`** is an additive sibling of `assemble()`
(itself unchanged — same signature, same checks, same return shape):
it returns each assembled Statement paired with its own `{"clause",
"subj", "obj"}` span triple (`extract.build.BuiltStatement`, the same
shape `extract_with_spans()` already uses for the non-hybrid pipeline),
since `assemble()`'s own final Statement shape keeps only a
clause-level `provenance`.

## Why a `CandidateSet`/`Decision` split, not one combined step

The deterministic stage must be recomputed every time (stdlib, pure,
auditable — the same property §23 already requires of the non-hybrid
pipeline); the model stage must never be recomputed at run time once
recorded (replay, not recomputation, is what makes a hybrid run
reproducible without an API key). Splitting `propose()`/`decide()`/
`assemble()` into three separate, independently testable functions is
what lets `assemble()` enforce the span constraint on every replay, not
only once, and lets a fake decider fixture exercise the full pipeline
in tests without ever calling a model (`tests/test_hybrid.py`).

## Measured results

Candidate recall, relabel-reachability, add-reachability, and the full
extractor agreement table are all measured on a development set and
are not published here — the measurement scripts live outside this
package, as un-shipped local evaluation tooling, not in version
control. The gold coders and a pinned decider used for that measurement
are drawn from the same model family; agreement between any stage of
this extractor and that gold therefore partly measures self-consistency
between same-family models, not independent agreement — noted here so
the caveat travels with the design, not only with one report of it.

No real Decision has been recorded inside this repository — recording
one calls a model externally, which is out of this package's own
scope. The replay-mode tests all use a fake decider fixture
(`tests/test_hybrid.py`), never a real cached answer.

## Held-out protocol

On a held-out set, this extractor's own decisions should be recorded
once with the frozen `PROMPT_TEMPLATE_V1` and the frozen `propose()`
candidate generator, then scored once. There is no tuning after that —
no re-recording a Decision because a score came out low, no editing the
prompt template or the cue-rule table after seeing a held-out score,
and no re-running `propose()` with a changed codebook rule once a
held-out Decision has been recorded against its own candidate set. Any
change to `propose()`, the prompt template, or the decider afterwards
requires a fresh record-then-score pass on a new held-out sample, never
a re-score of the same one.

## "Never invents"

`assemble()` never invents a *span* — every accepted span, selected or
added, must be a member of `allowed_spans(candidate_set)`, enforced on
every replay. It is not limited to the candidate set's own
rule-labelled predicates: the decider is free to relabel a selected
candidate and to add a Statement from a much larger pool of allowed
spans than one candidate's own pair. "Never invents a span" is the
accurate claim; the decider does assemble new Statement shapes, just
never from un-proposed text.

## Known imperfections / open items

- No real Decision has been recorded yet inside this repository; the
  scaffold here is what a reviewer process records against.
- Candidate recall for `based_on`/`enables`/`competence_of` is at or
  near zero on the development set measured — closing this needs new
  or widened cue rules in `extract.rules` (a `propose()`-stage change),
  not anything the Decision/assembly stages can fix.
- `CandidateSet.segments` stores the segmenter's full flat node list
  (containers included), so the decider can resolve chapeau inheritance
  itself — this is more data than the non-hybrid pipeline's own
  `extract_with_spans()` exposes; no attempt was made to reconcile the
  two shapes into one.

## Applied spec text

The following was applied to `spec/SPEC.md` as the new §23a (resolving
the open questions this ADR originally raised: the subsection is
numbered §23a; the cache-key inputs named below are required minimums;
no non-replay "record" mode is named in the spec — it stays external
tooling, per `decide(mode="record")`'s own `NotImplementedError`):

> **§23a. Determinism by replay (the hybrid extractor).** An
> implementation MAY compose the deterministic extraction pipeline
> (§21-§23) with a MODEL-ASSISTED decision stage, PROVIDED the
> following hold:
>
> 1. The deterministic stage (candidate proposal: clause/list-item
>    segmentation, NP-chunk proposal, candidate-Statement proposal from
>    a closed cue-rule table) MUST remain pure recomputation, exactly as
>    §23 already requires of the non-hybrid pipeline — the SAME unit
>    text MUST give the SAME candidate set, byte-identically, with no
>    model involved at this stage.
> 2. The candidate set MUST be serialised as CANONICAL JSON and
>    content-addressed by its own SHA-256 digest.
> 3. The model-assisted decision stage MUST be content-addressed by a
>    key deriving from (at minimum) the candidate set's own digest, the
>    coder-view/instructions text's own digest, the model identifier,
>    and the prompt template's own digest. The model's own answer
>    (the "Decision") to a given key MUST be recorded exactly once and
>    thereafter REPLAYED from that record — an implementation MUST NOT
>    call the model again for a key it has already recorded, and MUST
>    raise an error (never silently recompute, never silently fall back
>    to an unassisted result) on a key it has NOT recorded.
> 4. The assembly stage (Decision + candidate set → schema-valid
>    Statements, §21) MUST remain pure recomputation. Any span
>    adjustment, or any added Statement's own endpoint span, that the
>    Decision specifies MUST be constrained to a span ALREADY PRESENT
>    in the candidate set (a clause span, an NP-chunk span, a candidate
>    Statement's own endpoint, or an inherited/antecedent span the
>    candidate set separately names) — an implementation MUST reject,
>    not silently clamp or ignore, a span outside that set.
> 5. **Determinism, restated:** under §23's own pure-recomputation
>    regime, the SAME input gives the SAME output because the SAME code
>    runs on it. Under this subsection's own replay regime, the SAME
>    input AND THE SAME content-addressed decision cache give the SAME
>    output — determinism is a property of the (input, cache) PAIR, not
>    of the input alone. Any report of a hybrid extractor's own output
>    MUST state the cache's own content hash (a manifest digest over
>    every recorded key) alongside the result, so a reader can verify
>    EXACTLY which recorded decisions produced it.
>
> A pipeline conforming to §23 alone (no model-assisted stage) trivially
> satisfies this subsection too (an empty decision cache, with every
> Decision being the identity — "keep every candidate's own predicate/
> span unchanged" — recomputed, never replayed, is one valid instance).
> This subsection is therefore ADDITIVE: it does not change what a
> non-hybrid, §23-only implementation must do, and does not retract
> §23's own requirement that the DETERMINISTIC portions of a hybrid
> pipeline (candidate proposal, assembly) remain pure recomputation.

## Requests to other territories

None.
