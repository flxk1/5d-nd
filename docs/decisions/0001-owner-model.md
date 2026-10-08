# 0001 — Owner model (2026-09-30)

## Status

Accepted.

## Context

The relationship between "5D", "nD", "algebra", "deontic", "governance", and
"mathematics" had drifted across the lineage (see the lineage digest this
decision is grounded in, carried in this branch's own session notes, not
reproduced here) into at least five incompatible readings of what an nD
even is. Before
drafting a specification, the owner fixed the model this repository builds
to.

## Decision

The owner's decision, 2026-09-30:

> "5D = the 5 Dimensions as the key fingerprint/coordinate system. We started
> to call it an algebra. nD is the extra grammar system for domain specific
> fingerprints. deontic is the grammar for deontic languages. Governance is
> the grammar for governance languages. It is also a small declarative
> language. Mathematics is a collection of nD grammars."

The 5D language lives in this repository (`5d-nd`). nD grammars — deontic,
governance, mathematics, and others — are separate languages that attach to
5D through the contract in `spec/SPEC.md` §9; they are not extra dimensions
added to the base five.

## Consequences

- `spec/SPEC.md` §1 scopes this repository to the 5D layer only; no nD
  grammar's own vocabulary is specified here.
- The previous reading in this repository's own `docs/model.md` ("+nD is the
  forward-compatibility axis for custom dimensions beyond the base five") is
  corrected (see `README.md`, `llms.txt`, `docs/model.md` updates in this
  same change) to: nD = grammars for domain-specific fingerprints that attach
  through §9.
- No claim is made that versum, solver, or any nD grammar repository already
  conforms to this specification; they are PLANNED consumers (§9's
  contract is what they are meant to implement against).
