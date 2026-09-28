# 5d-nd

Reference resolver for the `5d+nd` grounding scheme: canonicalises, digests and validates a dimensioned reference to a versum span.

## Problem

"Grounded in span X" cannot be verified after the fact. Canonical reference and digest of a span.

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

## Family

Assurance artifact, pillar "grounding" of [governance-certification](https://github.com/flxk1/governance-certification). Consumes: the `Dimension` algebra vendored from [loomground-solver](https://github.com/flxk1/loomground-solver); a [loomground-versum](https://github.com/flxk1/loomground-versum) store, via its public API (`pip install '5d-nd[grounding]'`). Peers: `7d+nd`, `prov-o`. Docs: [docs/](docs/).

`resolve()` needs `versum.coordinates.entry_coordinates`, which no tagged `loomground-versum` release carries yet — the `grounding` extra is therefore left unpinned rather than pinned to a tag that lacks it. For local development, install the sibling repo directly instead: `pip install -e ../loomground-versum`, or a git ref that has `coordinates` (`pip install "loomground-versum @ git+https://github.com/flxk1/loomground-versum@<branch-or-commit>"`). Tests that need `versum.coordinates` skip, with a reason, when it is not importable.

## Status

0.2.0 · 35 tests · Python ≥ 3.9

## How this is made

The code and documentation are written with Loomground agents. The maintainer reads and corrects all of it.

## License

MIT — [LICENSES/MIT.txt](LICENSES/MIT.txt); `src/five_d_nd/dimensions.py` Apache-2.0 (vendored)
