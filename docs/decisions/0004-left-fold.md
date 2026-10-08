# 0004 — Left-fold is the normative evaluation order (2026-09-30)

## Status

Accepted.

## Context

`COMPOSITION_TABLE` is not associative: of the 125 ordered triples, exactly
two — `(causal, intentional, structural)` and `(causal, temporal,
structural)` — give a different result depending on grouping (verified
against `src/five_d_nd/dimensions.py`; see `conformance/vectors/fold-left/`).
None of the originals from 2026-03-20 through the bridge archive (2026-04)
document a fold order or even note the non-associativity. It is first named
explicitly in a later design note: "NOT fully
associative (2 of 125 triples) ... canonical **left-fold**", and repeated in
Cubes 1.1's `reasoning.py`. versum's own `dimensions.py` states no fold order
at all.

## Decision

Left-fold — `compose(compose(compose(a, b), c), ...)`, evaluated strictly
left to right along a path — is the NORMATIVE evaluation order for this
specification (`spec/SPEC.md` §3). `src/five_d_nd/dimensions.py` gains a
`left_fold()` function; an implementation MUST use it (or an equivalent
left-to-right evaluation) for any path of three or more dimensions.

## Consequences

- `conformance/vectors/fold-left/` includes both failing triples, each
  showing the left-fold result against the right-fold result so a verifier
  can see they differ (and that most triples are unaffected — associativity
  holds for 123 of 125).
- Any future change to the composition table must re-run the associativity
  check (`python -m pytest -q -k fold_left`) since a table edit could change
  which triples fail, or how many.
