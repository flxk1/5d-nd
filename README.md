# 5d-nd

A 5D fingerprint/coordinate specification (draft 1.0) and reference implementation — the base coordinate system domain-specific nD grammars attach to — plus the `5d+nd` grounding-scheme resolver built on it: canonicalises, digests and validates a dimensioned reference to a versum span.

## Problem

"Grounded in span X" cannot be verified after the fact. Canonical reference and digest of a span.

## The spec

[`spec/SPEC.md`](spec/SPEC.md) — the normative 5D specification: the closed set of five dimensions (structural, causal, intentional, temporal, relational), the composition algebra (non-commutative, non-associative, left-fold is the normative evaluation order), the 5D fingerprint of an entry, 5D's neutrality on is/ought (§7, N1-N4: a 5D link carries exactly one dimension and nothing else — no mode, one fingerprint per entry; a normative relation binds a dimension exactly like any other relation; whether a relation is normative is the owning nD grammar's own knowledge, OPTIONALLY carried as a "co-dimension" — an ordinary axis on that grammar's own NDSystem, e.g. the deontic plane's `operator` axis — never something 5D itself inspects; a norm's content still enters 5D as its own entry via a structural `embeds` link), and the contract an nD grammar (deontic, governance, mathematics, ...) publishes to attach to 5D. **5D is not "5D+nD" as extra dimensions** — nD is a separate, domain-specific grammar that attaches through that contract; it never adds a sixth dimension. No Loomground repository conforms to this spec yet — versum, solver, and the grammar planes are its PLANNED consumers.

Machine-readable vocabulary: [`vocabulary/`](vocabulary/) (dimensions, composition table); schemas: [`schema/`](schema/); conformance vectors + runner: [`conformance/`](conformance/), [`tests/test_conformance.py`](tests/test_conformance.py); design decisions: [`docs/decisions/`](docs/decisions/).

## Typed Statements and the extractor

Spec §21-§23 adds a richer, reified edge — a **Statement** — on top of the plain triple, plus a codebook (`docs/codebook/typed-statements-v1.md`, v3.5) that defines how one is read off legal text. `src/five_d_nd/extract/` implements that codebook: a deterministic stage (`extract.segment` + `extract.rules`) segments a unit into clauses and list items and proposes candidate Statements from a closed cue-rule table — pure stdlib, no ML, same input always gives the same candidate set. `extract.hybrid` composes that with a model-assisted decision stage, per spec §23a: a model's answer for a given candidate set is recorded once into a content-addressed cache and thereafter only replayed — a cache miss raises (`CacheMissError`) rather than recomputing or calling the model again. This package ships no model and records no Decision itself. No accuracy or performance figures are published here; see `docs/decisions/` for the development-set measurements behind the design.

## Install

`pip install "5d-nd @ git+https://github.com/flxk1/5d-nd"`

## Usage

```python
from five_d_nd import digest, validate, resolve
ref = {"dimensions": ["causal", "structural"], "anchor": "versum://research/note-7#span-42"}
digest(ref)     # {"sha256": "<hex>"}

# resolve() through versum's public API — canonical span syntax <urn>#<start>-<end>:
ref2 = {"dimensions": ["intentional"], "anchor": "urn:dls:sha256:defa9705...#11-88"}
resolve(ref2, store=an_indexed_versum_store_path)
# {"entry_id": ..., "span": {"start": 11, "end": 88, "text": "..."},
#  "dimension": None, "nd": {...}, "source_urn": "...", "content_digest": {"sha256": "..."}}
```

## Example

```
in : ref = {"dimensions": ["temporal", "relational"], "anchor": "versum://policy/p1#span-150-240"}; canonicalize(ref); digest(ref)
out: b'{"anchor":"versum://policy/p1#span-150-240","dimensions":["temporal","relational"]}'
     {'sha256': '4da8b3468ad57b8a4e6c6d2a741876e1b3f00eb8c974df29e540c9517e2a88d2'}
```

## Interface

- input `ref`: `dimensions` ⊆ {structural, causal, intentional, temporal, relational}, `anchor` (canonical span reference or URI)
- **canonical span-reference syntax**: `<source_urn>#<start>-<end>`, over the cleaned-text offsets versum records; two READ-ONLY legacy forms (`versum://...#span-a-b`, `{urn}#{unit}:{a}-{b}`) normalize to it
- `canonicalize(ref) -> bytes`, keys sorted recursively
- `digest(ref) -> {"sha256": hex}` — reference-only, unchanged by resolution
- `validate(ref) -> bool`, fails closed on an unknown dimension
- `normalize_reference(ref) -> str`, canonical or legacy in, canonical string out; fails closed (`MalformedReferenceError`) on anything else
- `resolve(ref, *, store, source_text=None, expected_content_digest=None)`: resolves through versum's public API (`versum.planes.entry_id`, `versum.coordinates.entry_coordinates`) only; fails closed (`MissingStoreError` / `UnknownReferenceError` / `SpanMismatchError`) — never fabricates a span. `MissingStoreError` is raised literally for `store=None`, a non-path `store` (e.g. `store=42`), an empty-string `store`, and when `versum` itself is not importable. A length-only span check cannot catch same-length content tampering (e.g. "must not" swapped for "shall do"); pass `source_text` (an independently-held copy of the cleaned source) or `expected_content_digest` (a previously-recorded `content_digest(ref, ...)`) to fail closed on that too.
- `content_digest(ref, span_text) -> {"sha256": hex}` — additive, content-bound (`canonicalize(ref)` + the resolved span text); `digest(ref)` above is untouched
- is/ought: 5D is what **IS** — `resolve`'s `dimension` is `None` for an OUGHT/norm (O/P/F) entry, never a fabricated 5D value
- output shape for a `grounded` pillar: `{"scheme": "5d+nd", "ref", "digest"}`

## Evaluation

[`docs/benchmark-2026-10.md`](docs/benchmark-2026-10.md) — two pre-registered
rounds on cross-law provision matching (does a typed, then a concept-typed,
5D signal improve matching a provision across EU instruments over a
structural baseline?). Both rounds are a loss against their pre-registered
gate. 5D stays a labelled structural index with no role in the migration
(the dim5 → 5D migration), and no claim is made.

## Family

Assurance artifact, pillar "grounding" of [governance-certification](https://github.com/flxk1/governance-certification). Consumes: the `Dimension` algebra vendored from [loomground-solver](https://github.com/flxk1/loomground-solver); a [loomground-versum](https://github.com/flxk1/loomground-versum) store, via its public API (`pip install '5d-nd[grounding]'`). Peers: `7d+nd`, `prov-o`. Docs: [docs/](docs/).

`resolve()` needs `versum.coordinates.entry_coordinates`, which no tagged `loomground-versum` release carries yet, so the `grounding` extra pins versum at a main commit that has it, together with the `loomground-factual` plane that contributes the action-type entries. Tests that need `versum.coordinates` skip, with a reason, when it is not importable; the `grounding` CI job installs it so they run.

## Status

Spec draft 1.0 + resolver 0.2.0 · Python ≥ 3.9

## How this is made

The code and documentation are written with Loomground agents. The maintainer reads and corrects all of it.

## License

MIT — [LICENSES/MIT.txt](LICENSES/MIT.txt); `src/five_d_nd/dimensions.py` Apache-2.0 (vendored)
