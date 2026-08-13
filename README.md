# `5d+nd`

**`5d+nd` is the reference resolver for ONE grounding scheme used by governance
certifications — not a standard, one interchangeable option (peers: `7d+nd`,
`prov-o`).**

A `GovernanceCertification` (predicateType
`https://loomground.org/attestations/GovernanceCertification/v1`) carries a
`grounded` pillar: the claim that a verdict rests on a cited span. That
pillar names a `scheme` (a URI/short name), a `ref`, and a `digest`. `5d+nd` is
one value that `scheme` may take. There is **no bespoke registry and no privileged
default** — whatever verifier understands a scheme's vocabulary resolves its
references; a certification could just as well say `7d+nd` or `prov-o`. This repo
exists so that when the scheme *is* `5d+nd`, any verifier can canonicalize,
digest, and (optionally) resolve the reference.

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

## The three layers

```
versum            the STORE.  Dimension-agnostic: it holds content and takes a
                  `dimension` STRING; it does not know what the dimensions mean.

5D algebra        the ADDRESSING SCHEME over the store.  The `Dimension` enum
                  (structural / causal / intentional / temporal / relational)
                  + the composition table that says which dimension governs a
                  two-step inference.  Vendored from loomground-solver.

5d+nd  (this repo) packages that addressing scheme as a GROUNDING RESOLVER:
                  canonicalize + digest + validate a reference, and (stub)
                  resolve its anchor into a versum span.
```

`versum` stores; the 5D algebra *addresses* what versum stores; `5d+nd` makes
that addressing citable from a certification. The `+nD` is the
forward-compatibility axis for custom dimensions beyond the base five — the
reference resolver validates strictly against the base vocabulary it vendors.

## Shape of a reference

A `5d+nd` reference is dimensioned addressing over the store:

```json
{
  "dimensions": ["causal", "structural"],
  "anchor": "versum://research/note-7#span-42"
}
```

- `dimensions` — one or more known `Dimension` values (the base-5 vocabulary,
  extensible via `+nD`); they select the edges along which the span is retrieved
  or traversed.
- `anchor` — a **store-span** (e.g. `{"folder": ..., "note": ..., "span": ...}`)
  or a **URI** that addresses a location in versum.

As it appears inside a certification's `grounded` pillar, it is wrapped with its
scheme and a content digest:

```json
{
  "scheme": "5d+nd",
  "ref":    { "dimensions": ["causal", "structural"], "anchor": "versum://research/note-7#span-42" },
  "digest": { "sha256": "<hex over canonicalize(ref)>" }
}
```

## Canonicalize · digest · verify

```python
from five_d_nd import canonicalize, digest, validate, SCHEME

ref = {
    "dimensions": ["causal", "structural"],
    "anchor": "versum://research/note-7#span-42",
}

assert validate(ref)                     # well-formed 5d+nd reference?
canonicalize(ref)                        # b'{"anchor":"versum://...","dimensions":["causal","structural"]}'
digest(ref)                              # {'sha256': '…64 hex chars…'}

# A verifier re-derives the digest and compares it to grounded.digest:
grounded = {"scheme": SCHEME, "ref": ref, "digest": digest(ref)}
assert digest(grounded["ref"]) == grounded["digest"]
```

- **`canonicalize(ref) -> bytes`** — deterministic JSON, keys sorted
  **recursively**, compact separators, UTF-8. Two references differing only in
  key order canonicalize to identical bytes and therefore digest identically.
  This is a **JCS-style** approximation built on the standard library; for
  production interop (to match the **RFC 8785** digest a certification computes
  over its `grounded` pillar) swap in a full RFC 8785 canonicalizer.
- **`digest(ref) -> {"sha256": hex}`** — sha256 over `canonicalize(ref)`; the
  same digest shape a certification stores in `grounded.digest`.
- **`validate(ref) -> bool`** — well-formed iff every entry in `dimensions` is a
  known `Dimension` value and the reference carries an `anchor`. Fails closed on
  anything it does not recognise.
- **`resolve(ref, *, store=None)`** — a **documented stub**. It validates, then
  describes how an anchor becomes a concrete versum span (parse anchor → read the
  span from an injected `store` handle → return content + provenance). The store
  read is an **extension point**: this repo does not depend on versum, and
  `resolve` raises rather than fabricating a result.

## The vendored dimension algebra

`five_d_nd/dimensions.py` is a **faithful copy** of
`loomground_solver.dimensions` — the `Dimension` enum, `DEFAULT_DIMENSION`,
`COMPOSITION_TABLE`, `compose`, `compose_weights`, `classify_predicate`, and
`classify_query_dimension`. Its original Apache-2.0 header is preserved.

**The authoritative table lives upstream in `loomground-solver`**, not here.
Install the extra to depend on the real module instead of the vendored copy:

```
pip install '5d-nd[solver]'
```

Do not fork or extend the algebra in this repo — changes belong upstream.

## Status

A thin, standalone resolver with no runtime dependency on any consumer — what a
verifier reaches for when a certification's `grounded.scheme` is `5d+nd`.

## Install & test

```
pip install -e .
python3 -m pytest tests -q
```

No hard dependencies; the resolver seam is stdlib-only. `pytest` is needed only
to run the tests.

## License

MIT (`LICENSE`). Exception: `five_d_nd/dimensions.py` is vendored from
`loomground-solver` and remains **Apache-2.0** under its preserved header.
