# Scope and prior art


**`5d+nd` is a reference resolver for ONE grounding scheme — not a standard, one
interchangeable option (peers: `7d+nd`, `prov-o`).**

A **grounding reference** is the claim that a verdict rests on a cited span. It
names a `scheme` (a URI/short name), a `ref`, and a `digest`. `5d+nd` is one value
that `scheme` may take. There is **no bespoke registry and no privileged default**
— whatever verifier understands a scheme's vocabulary resolves its references; a
grounding could just as well say `7d+nd` or `prov-o`. This repo exists so that
when the scheme *is* `5d+nd`, any verifier can canonicalize, digest, and
(optionally) resolve the reference.

## What this is not

The `5D+nD` dimensional model is **not a novel invention**. A prior-art audit
found it re-describes established modal knowledge representation:

- **BFO** (Basic Formal Ontology) — the upper-ontology carving of reality;
- **CIDOC-CRM** — event-centric cultural-heritage modelling;
- **RDF-Data-Cube** / **PROV-O** — dimensioned observations and provenance.

So this repo claims none of the theory. It owns only a thin resolver and honest
packaging. The dimension algebra it addresses with is **vendored** from
[`loomground-solver`](#the-vendored-dimension-algebra); the reference-modelling it
leans on is **PROV-O / RDF-Data-Cube**; the conceptual carving is **BFO /
CIDOC-CRM**. `5d+nd` composes on all of these and invents no dimensional theory.

## Status

A thin, standalone resolver with no runtime dependency on any consumer — what a
verifier reaches for when a grounding scheme is `5d+nd`.
