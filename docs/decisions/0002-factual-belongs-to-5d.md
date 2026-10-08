# 0002 — The factual/assertoric grammar belongs to 5D (D1) (2026-09-30)

## Status

Accepted.

## Context

`loomground-factual` lowers a free-text assertion into a fixed 5D edge
(pinned to factual @ `ebf9fe1`, release 0.2.0: `is-a`/`part-of`/`has-part` →
structural, `precedes`/`follows` → temporal, `predication` (the default) →
relational; see `src/loomground_factual/grammar.py` and
`src/loomground_factual/artifacts/binding.json`). It could be modelled
either as (a) an
nD grammar like deontic or governance, attaching to 5D through the §9
contract, or (b) part of the 5D language itself — the mechanism by which an
assertion GETS a 5D fingerprint in the first place.

## Decision

Owner-approved default, 2026-09-30 (D1): the factual/assertoric grammar
belongs to the 5D language. It is HOW an assertion gets its 5D fingerprint;
it is not a domain-specific nD grammar. `spec/SPEC.md` §8 specifies it as
part of 5D (the "assertoric layer"), and `src/five_d_nd/assertoric.py` lives
in this repository's core, not behind an nD-contract seam.

## Consequences

- An nD grammar (deontic, governance, ...) that names a bearer and content
  reaches 5D by having its content LOWERED through the factual/assertoric
  layer (§7, §8) — it does not need its own 5D-binding logic for that
  content; it only needs `spans.content` + `bearer` coordinates (see
  versum's `planes.py` lowering step, which this specification's §7/§8
  reproduce the rules of).
- `assertoric.py`'s rules (`is-a`/`part-of`/`has-part` → structural,
  `precedes`/`follows` → temporal, `predication` (the default) → relational,
  pinned to factual @ `ebf9fe1`) are NORMATIVE for this specification, unlike
  an nD grammar's own axes, which are entirely grammar-specific and out of
  this specification's scope.
