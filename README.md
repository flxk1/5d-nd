# 5d-nd

Reference resolver for the `5d+nd` grounding scheme: canonicalises, digests and validates a dimensioned reference to a versum span.

## Problem

"Grounded in span X" cannot be verified after the fact. Canonical reference and digest of a span.

## Install

`pip install "5d-nd @ git+https://github.com/flxk1/5d-nd"`

## Usage

```python
from five_d_nd import digest, validate
ref = {"dimensions": ["causal", "structural"], "anchor": "versum://research/note-7#span-42"}
digest(ref)     # {"sha256": "<hex>"}
```

## Example

```
in : ref = {"dimensions": ["temporal", "relational"], "anchor": "versum://policy/p1#span-150-240"}; canonicalize(ref); digest(ref)
out: b'{"anchor":"versum://policy/p1#span-150-240","dimensions":["temporal","relational"]}'
     {'sha256': '4da8b3468ad57b8a4e6c6d2a741876e1b3f00eb8c974df29e540c9517e2a88d2'}
```

## Interface

- input `ref`: `dimensions` ⊆ {structural, causal, intentional, temporal, relational}, `anchor` (store-span or URI)
- `canonicalize(ref) -> bytes`, keys sorted recursively
- `digest(ref) -> {"sha256": hex}`
- `validate(ref) -> bool`, fails closed on an unknown dimension
- `resolve(ref, *, store=None)`: stub, raises without an injected store
- output shape for a `grounded` pillar: `{"scheme": "5d+nd", "ref", "digest"}`

## Family

Assurance artifact, pillar "grounding" of [governance-certification](https://github.com/flxk1/governance-certification). Consumes: the `Dimension` algebra vendored from [loomground-solver](https://github.com/flxk1/loomground-solver); a [loomground-versum](https://github.com/flxk1/loomground-versum) store, injected. Peers: `7d+nd`, `prov-o`. Docs: [docs/](docs/).

## Status

0.1.0 · 11 tests · Python ≥ 3.9

## License

MIT — [LICENSES/MIT.txt](LICENSES/MIT.txt); `src/five_d_nd/dimensions.py` Apache-2.0 (vendored)
