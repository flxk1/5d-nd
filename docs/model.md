# The three layers, reference shape, operations

## Is / ought

5D is what **IS**: `resolve`'s `dimension` field is versum's own 5D
dominant-dimension classification of a *factual* entry. A deontic operator
(O/P/F — obligation/permission/prohibition) is a normative FORCE, never a
fact on the 5D manifold — an OUGHT/norm entry's `dimension` is always `None`,
never fabricated from a structural artefact its own indexing happens to leave
behind. Norm content reaches a reference only through the factual entry the
norm's own nD assignment points at (its `action` coordinate) — deontic only,
never 5D.

## The three layers

```
versum            the STORE.  Dimension-agnostic: it holds content and takes a
                  `dimension` STRING; it does not know what the dimensions mean.

5D algebra        the ADDRESSING SCHEME over the store.  The `Dimension` enum
                  (structural / causal / intentional / temporal / relational)
                  + the composition table that says which dimension governs a
                  two-step inference.  Vendored from loomground-solver.

5d+nd  (this repo) packages that addressing scheme as a GROUNDING RESOLVER:
                  canonicalize + digest + validate + normalize a reference,
                  and resolve its anchor into a versum span (through versum's
                  public API only).
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
  "anchor": "urn:dls:sha256:defa9705...#11-88"
}
```

- `dimensions` — one or more known `Dimension` values (the base-5 vocabulary,
  extensible via `+nD`), declaring which reasoning dimension(s) this reference
  is addressed under. `validate(ref)` requires every entry to be a known
  `Dimension` value (fails closed otherwise); this is the only role `dimensions`
  plays in THIS module. `resolve(ref, *, store=...)` does not read, filter, or
  select by `dimensions` at all — it resolves purely from `anchor`, so two refs
  that differ only in `dimensions` resolve to the identical span (and differ
  only in `digest(ref)`, since `dimensions` is part of what gets canonicalized).
  Elsewhere in the family, a dimension-aware retrieval/traversal layer (the
  algebra in `five_d_nd.dimensions`, or versum's own dimensioned queries) is
  what actually selects or traverses edges by dimension.
- `anchor` — a **span-reference string** addressing a location in versum (see
  "Canonical span-reference syntax" below); this is the ONLY field `resolve()`
  uses to find and return a span.

Wrapped with its scheme and a content digest, for use in a `grounded` pillar:

```json
{
  "scheme": "5d+nd",
  "ref":    { "dimensions": ["causal", "structural"], "anchor": "urn:dls:sha256:defa9705...#11-88" },
  "digest": { "sha256": "<hex over canonicalize(ref)>" }
}
```

## Canonical span-reference syntax

ONE canonical syntax, over the cleaned-text offsets versum itself records —
confirmed against the `span` field of `versum.coordinates.entry_coordinates`,
a `(start, end, text)` triple where `text` is the exact source slice at those
offsets (`versum.store.index.index_folder`'s own invariant):

```
<source_urn>#<start>-<end>
```

e.g. `urn:dls:sha256:defa970572b4d201a900ee509861d597bc206a7d21916082a43aa56af377e1f4#11-88`.

`normalize_reference(ref)` accepts this canonical form plus two **READ-ONLY**
legacy forms and returns the canonical string; anything else is rejected —
fail closed, never guessed:

- legacy — `versum://<path>#span-<start>-<end>`
- legacy — `{urn}#{unit}:{start}-{end}` (the unit token is dropped on
  normalization; the canonical form carries no unit)

This module never *emits* a legacy form — only accepts one, for backward
compatibility, and normalizes it away.

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
  production interop, swap in a full **RFC 8785** canonicalizer so the `grounded`
  digest matches across implementations. **Unchanged** by everything below —
  a certification's existing `grounded.digest` still verifies exactly as
  before.
- **`digest(ref) -> {"sha256": hex}`** — sha256 over `canonicalize(ref)`; the
  same digest shape a certification stores in `grounded.digest`. **Unchanged**,
  reference-only: it never depends on the resolved span text.
- **`validate(ref) -> bool`** — well-formed iff every entry in `dimensions` is a
  known `Dimension` value and the reference carries an `anchor`. Fails closed on
  anything it does not recognise.
- **`normalize_reference(ref) -> str`** — the ONE canonical span-reference
  syntax (see above); accepts the canonical form and both READ-ONLY legacy
  forms, rejecting anything else with `MalformedReferenceError`.

## Resolve

```python
from five_d_nd import resolve

ref = {
    "dimensions": ["intentional"],
    "anchor": "urn:dls:sha256:defa970572b4d201a900ee509861d597bc206a7d21916082a43aa56af377e1f4#11-88",
}
result = resolve(ref, store=an_indexed_versum_store_path)
# {
#   "entry_id": "ent-33b8bdf7229b64c8",
#   "span": {"start": 11, "end": 88,
#             "text": "The lender must not make a solely automated decision on a credit application."},
#   "dimension": None,          # OUGHT/norm entry: 5D is what IS, never a deontic operator
#   "nd": {"loomground-deontic": {"operator": "F", "bearer": "lender", ...}},
#   "source_urn": "urn:dls:sha256:defa970572b4d201a900ee509861d597bc206a7d21916082a43aa56af377e1f4",
#   "content_digest": {"sha256": "…64 hex chars…"},
# }
```

`resolve(ref, *, store)` normalizes `ref["anchor"]`, then resolves through
versum's **public API only**:

- `versum.planes.entry_id(source_urn, start, end)` — the same deterministic id
  versum's own indexer stamps on the entry at those exact offsets (a pure
  function of values already in hand — no private reader, no CSV parsing);
- `versum.coordinates.entry_coordinates(store, entry_id)` — the entry's span,
  its 5D `dimension`, and its nD coordinate assignments.

It fails closed with a specific exception, never a fabricated result:

- `MissingStoreError` — `store` is `None`, an empty string, or anything that
  is not a path (e.g. `store=42`); or the optional `versum` dependency itself
  is not importable. Tested literally for all four cases.
- `UnknownReferenceError` — no entry in `store` matches the reference's source
  URN + span;
- `SpanMismatchError` — the store's own record for that entry id disagrees
  with the reference (a different source URN, different bounds, or a
  recorded span text whose length does not match the declared `end - start`),
  OR the resolved span text disagrees with an independently supplied
  `source_text`/`expected_content_digest` — see below.

**Same-length content tampering.** A length-only check cannot see a store
row edited so its recorded text keeps the same length but different content
(e.g. "must not" swapped for "shall do" — both 8 characters). Nothing in a
single `entry_coordinates` result lets `resolve` re-derive the entry's
original text independently (its entry id is `hash(source_urn, start, end)`
only — content-free). To close this, `resolve` accepts two optional,
independent grounds of truth:

- `source_text` — the caller's own copy of the cleaned source text; `resolve`
  slices `source_text[start:end]` and raises `SpanMismatchError` on any
  disagreement with the store's recorded text, length-preserving or not;
- `expected_content_digest` — a previously recorded
  `content_digest(ref, known_good_text)` (e.g. carried by a certification from
  an earlier, trusted resolution); `resolve` recomputes the digest over what
  it just read and raises `SpanMismatchError` on any mismatch.

Neither is required — a caller with neither still gets the length-only check,
unchanged.

`resolve` is the **only** function here with a runtime dependency on `versum`;
it is imported lazily, inside `resolve()` itself, so importing this package at
all still needs nothing beyond the standard library. Install the extra to use
it:

```
pip install '5d-nd[grounding]'
```

As of this writing no tagged `loomground-versum` release carries
`versum.coordinates.entry_coordinates` yet — the `grounding` extra is
deliberately left unpinned rather than pinned to a tag that would import but
lack the module `resolve()` needs. For local development, install the
sibling repo directly (`pip install -e ../loomground-versum`, or a git ref
known to have `coordinates`). Any test that needs `versum.coordinates`
skips, with a stated reason, rather than erroring, when it is not importable.

## Content-bound digest (additive)

`digest(ref)` stays reference-only and byte-for-byte unchanged. `resolve`
additionally surfaces `content_digest(ref, span_text) -> {"sha256": hex}`,
bound to BOTH `canonicalize(ref)` **and** the resolved span text — a
verifier who wants a hash that changes if the text under the reference is
edited gets it for free, without disturbing what a certification's existing
`grounded.digest` already checks. Domain-separated with a fixed prefix and a
length-prefixed `canonicalize(ref)`, so it can never collide with `digest`.

## The vendored dimension algebra

`src/five_d_nd/dimensions.py` is a **faithful copy** of
`loomground_solver.dimensions` — the `Dimension` enum, `DEFAULT_DIMENSION`,
`COMPOSITION_TABLE`, `compose`, `compose_weights`, `classify_predicate`, and
`classify_query_dimension`. Its original Apache-2.0 header is preserved.

**The authoritative table lives upstream in `loomground-solver`**, not here.
Install the extra to depend on the real module instead of the vendored copy:

```
pip install '5d-nd[solver]'
```

Do not fork or extend the algebra in this repo — changes belong upstream.

## Install & test

```
pip install -e .
python3 -m pytest tests -q
```

`canonicalize`/`digest`/`validate`/`normalize_reference` are stdlib-only.
`resolve` additionally needs `versum` (`pip install '5d-nd[grounding]'`); its
own tests are skipped, not failed, when that extra is not installed. `pytest`
is needed only to run the tests.
