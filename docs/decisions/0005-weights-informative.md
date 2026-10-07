# 0005 — Weight composition is informative, OPEN (2026-09-30)

## Status

**SUPERSEDED by [0006](0006-weights-normative.md), 2026-10-01.** A
fixed decision (2026-10-01) makes weight composition
NORMATIVE and multiplicative — the OPEN marker this ADR recorded is
removed. Kept here, unedited below, as the historical record of why it was
left open in the first place.

## Context

Brain (2026-03-20) composes edge-confidence weights with per-dimension rules
(structural: MIN, causal: MULTIPLY, intentional: MIN, temporal: mean,
relational: product/interference). The cell kernel (2026-03-21) onward drops
all of that in favour of one multiplicative rule, `w1 * w2`, which is what
every later repository — including this one's existing
`src/five_d_nd/dimensions.py` `compose_weights` — implements. The two
approaches were never reconciled; the multiplicative rule simply won by
being copied forward unexamined.

## Decision

`compose_weights` stays in the reference implementation, unchanged, but is
marked **INFORMATIVE**, not normative, in `spec/SPEC.md` §3. This
specification does not require an implementation to reproduce any particular
weight-composition rule to conform (§10 lists dimension composition,
left-fold, position, reference syntax, is/ought, assertoric lowering, and
the nD contract as the conformance surface — weight composition is not among
them).

## Consequences

- An implementation MAY use `w1 * w2`, per-dimension rules, or no weight
  composition at all, and still conform to this specification.
- This is recorded as an OPEN owner decision in `spec/SPEC.md` Annex B:
  whether weight composition becomes normative in a future draft, and if
  so, which rule, is still to be decided.
