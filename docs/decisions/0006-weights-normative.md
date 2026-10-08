# 0006 — Weight composition is normative, multiplicative (2026-10-01)

## Status

Accepted. Supersedes 0005 (which recorded this as OPEN).

## Context

0005 left weight composition INFORMATIVE because the lineage records two
incompatible rules (Brain's per-dimension MIN/mean/product rules vs. the
cell-kernel-onward single multiplicative rule, `w1 * w2`) and the owner had
not yet chosen between them.

## Decision

The owner's fixed decision, 2026-10-01: "Weights multiply along a path. This becomes
normative, and the Annex B OPEN marker is removed." `compose_weights(w1,
w2) = w1 * w2` is now NORMATIVE — an implementation MUST compose weights
multiplicatively along a path to conform. This is a FIXED, verbatim owner
decision; it is implemented, not re-litigated.

## Consequences

- `spec/SPEC.md` §3's "Weight composition" subsection is now titled
  NORMATIVE, not INFORMATIVE/OPEN; Annex B's corresponding entry is marked
  RESOLVED.
- §11 (the coordinate round's own triple) and §12 (fixed-point arithmetic)
  build directly on this: a triple's `weight` composes along a path by this
  same multiplicative rule, and the fixed-point quantisation (§12) is what
  makes that composition's accumulation well-defined and bit-identical at
  scale (the erasure bit-identity claim of §15 would not otherwise hold).
- Per-dimension weight-composition rules (Brain's own model) are no longer a
  conforming alternative.
