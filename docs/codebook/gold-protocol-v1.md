# Gold protocol: typed statements, v3 enum

This protocol produces GOLD data under a project-local, un-shipped
corpus root's own `<v>/gold/triples/` directory — a later build step (T2)
owns that write path; this document specifies the PROCEDURE, not the
writer. Grounded in an earlier reconciliation of the typed-triple
design and the decisions reached there, carried forward here without
relitigating them.

## Coders

**Two blind coders. Decision (2026-10-03): at least one of them
is a BLIND, PINNED MODEL — a specific model id and version, recorded
alongside every gold batch this protocol produces, never "whichever
model happened to be available that day."** Neither coder sees the
other's output, and neither sees any extractor's output (there is no
extractor at this build step — §21/§23). A SECOND qualified EN/DE legal
annotator is not available on this solo project — a STATED LIMITATION,
consistent with the separate benchmark-judge decision that the second
coder MAY also be a (different, independently pinned) model instance.
Every report
produced from this protocol's own output MUST state, explicitly: **this
is weaker than human-human inter-annotator agreement; no human-human
agreement figure exists for this gold set.**

**Owner spot-check.** 10% of the coded set, chosen at random, PLUS every
item the two coders disagreed on. Disagreement above the gate (below)
routes to the owner's own arbitration; agreement within the spot-check sample
is itself a datum this protocol reports (never silently assumed).

## Unitisation agreement, gated BEFORE label agreement

Agreeing on a PREDICATE label is meaningless if the two coders first
disagree on what the clause even IS — which span is `subj`, which is
`obj`, where the clause starts and ends. This protocol therefore runs TWO
GATES, in order, and does NOT proceed to the second until the first
clears:

1. **Unitisation agreement — `alpha_u` (Krippendorff's unitized alpha),
   gated FIRST.** Each coder independently marks clause boundaries and
   `subj`/`obj` spans over the SAME source text, before either sees the
   other's predicate labels. `alpha_u` is computed over the resulting
   unit boundaries (not over label values at all). **Gate: `alpha_u >=
   0.67`, PROPOSED, and STATED SEPARATELY from the label gate below** —
   this threshold is a SEPARATE choice from the label gate; the owner
   MAY set a different unitisation threshold without touching the label
   gate. A cell whose unitisation agreement falls below this gate is NOT
   advanced to label coding at all — its Statements, however coded, are
   excluded from this version's gold set and the cell is reported
   "insufficient unitisation agreement," a DIFFERENT outcome than
   "insufficient data" (below).
2. **Label (predicate) agreement — `alpha`, gated SECOND, only for cells
   that cleared gate 1.** Computed per BOUNDARY — EVERY predicate pair in
   the fifteen-predicate enum, via the FULL confusion matrix (every
   predicate × every predicate a coder could have assigned, not a
   judgement call about which pairs are "plausibly" confusable), PLUS the
   surface/domain/deep LAYER boundary — not as one pooled figure across
   all fifteen predicates. A boundary's own alpha is what matters, since
   a GOOD boundary and a GENUINELY HARD one should never be averaged into
   a single number that hides which is which.

## Minimum n per cell, with bootstrap CIs

**A cell is (dimension × predicate × language).** **Decision: the
minimum is 30 per cell.** A cell below `n = 30` reports
**"insufficient data"** — neither a pass nor a fail, and NEVER forced to
a gate verdict by borrowing items from a neighbouring cell.

For every cell at or above the minimum, `alpha`'s own 95% bootstrap
confidence interval is reported alongside the point estimate (resample
items WITH replacement within the cell, `B = 2000` resamples, PROPOSED —
a specific resample count the owner may revise without touching the
minimum-n rule itself). A cell whose point estimate clears the gate but
whose CI lower bound does not is reported with BOTH numbers, never
rounded up to a bare "passed."

## Gate thresholds

**Decision: label alpha per boundary must be `>= 0.80`.** A
boundary at or above `0.80` is marked **ADOPTED** for this version; a
boundary below it is marked **UNSUPPORTED** and is:

- reported explicitly, by name, as not clearing the gate;
- EXCLUDED from any downstream benchmark that would otherwise score it;
- NEVER given an invented weight or a forced resolution in favour of
  either side of the boundary.

**EVERY predicate pair is gated via the full confusion matrix — no
judgement-based exemption.** The full fifteen-by-fifteen confusion
matrix is computed for every cell that clears the unitisation gate;
there is no step where a human or a model decides in advance which pairs
are worth gating and which are "uncontested" — the matrix itself is what
shows which pairs turn out to be hard, rather than that judgement being
assumed going in. The surface/domain/deep layer boundary is gated the
same way, alongside the predicate matrix.

## Sampling order

**EN first.** GDPR, the AI Act, the DSA, NIS2, and the UK DPA 2018's own
OPERATIVE text are coded before any German text. **Recitals are
INCLUDED, in their own stratum** — `legislative_purpose_of` is BY
DEFINITION recital-position, so excluding recitals entirely would leave
that predicate's own cell, and the recital/article boundary itself,
EMPTY by construction. The sampling frame for the EN pass is therefore
TWO strata per instrument — operative articles, and recitals — each
sampled and reported separately, so a cell's own count never silently
depends on which stratum happened to be drawn more from. **DE later,
with its own codebook supplement** — German's own syntax (verb-final
obligation forms, `hat ... zu`, `ist ... zu gewährleisten`, passive
constructions) is NOT covered by this v3 codebook's own cue language
(which is EN-oriented); a DE supplement is a SEPARATE codebook document,
not a silent extension of this one.

## Layer is a gated boundary

The surface/domain/deep `layer` field (spec/SPEC.md §21) is coded by BOTH
blind coders, independently, exactly like a predicate — and its own
agreement is gated by the SAME two-stage mechanism (unitisation first,
then label agreement, `>= 0.80`, `n >= 30` per cell) as every predicate
boundary. A layer disagreement routes to the owner's own arbitration
the same way a predicate disagreement does.

## Dual coding in the gold set

A dual-coded pair (§21, causal + intentional sharing the middle segment)
is coded as TWO separate gold Statements, submitted to the SAME
blind-coding process as any single-predicate Statement. Agreement on dual
coding is measured at the PAIR level: do BOTH coders independently decide
this clause needs a split (as opposed to one predicate)? Disagreement on
"split or not" is itself a datum the causal/intentional boundary's own
confusion matrix includes — a coder who forces a single predicate where
the other splits counts as a disagreement on THAT boundary, not as a
separate, uncounted event.

## Output location

T2 (a later build step) writes the resulting gold Statements under a
project-local, un-shipped corpus root's own `<v>/gold/triples/`
directory — this protocol does not own that write path and does not specify its on-disk
layout beyond naming it; the Statement SHAPE itself (§21,
`schema/statement.schema.json`) is the one piece of that future layout
this build step already fixes.

## Every report's required disclosure

Every report produced under this protocol states, verbatim or in
substance: **"At least one blind coder is a pinned model (id and version
recorded); no human-human agreement figure exists for this gold set;
the owner's own spot-check covers 10% at random plus all disagreements; this
is weaker evidence than a human legal annotator's own judgement."** This
is the SAME disclosure discipline the separate benchmark-judge protocol
already requires of its own judge, reused here with the
pinned-model requirement above.
