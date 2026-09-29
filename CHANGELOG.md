# Changelog

## [0.2.2](https://github.com/flxk1/5d-nd/compare/v0.2.1...v0.2.2) (2026-09-29)


### Documentation

* neutralize Federation wording in dimensions adapter note ([c12eae7](https://github.com/flxk1/5d-nd/commit/c12eae7a1edfc0e9f14445257f96d4b93b2ec18a))

## [0.2.1](https://github.com/flxk1/5d-nd/compare/v0.2.0...v0.2.1) (2026-09-28)


### Documentation

* correct stale claims; add How this is made ([21c3772](https://github.com/flxk1/5d-nd/commit/21c3772ddd23834ff3f784fe267d477daca1f5ee))
* fix stale version, add How this is made section ([f2ebce2](https://github.com/flxk1/5d-nd/commit/f2ebce2d26675e9847feb41a8792a8ad2b06281b))

## [0.2.0](https://github.com/flxk1/5d-nd/compare/v0.1.0...v0.2.0) (2026-09-11)


### Features

* 5d+nd reference grounding resolver (one scheme, composes on the dimension algebra) ([32bc8c6](https://github.com/flxk1/5d-nd/commit/32bc8c6738691ef29c5ba19adc6d6e3ffa1d8a4f))


### Bug Fixes

* **release:** extra-files + version marker, not version-file ([62c390c](https://github.com/flxk1/5d-nd/commit/62c390c73235f646e3cb45c942b7bff9a7ff52a2))


### Documentation

* decouple README from sibling repos ([c9ec51f](https://github.com/flxk1/5d-nd/commit/c9ec51f73ff78dd8b1ddd7081d53c0313531ca70))
* llms.txt generated from README ([a26cdd3](https://github.com/flxk1/5d-nd/commit/a26cdd37916c084f620b2b6715b4644514a6bb66))
* README Problem + executed Example (186 words) ([5d71a78](https://github.com/flxk1/5d-nd/commit/5d71a78e34ebba1abaedf79165098ffa44bb92aa))
* README to canon (148 words), description, Family ([72aa89e](https://github.com/flxk1/5d-nd/commit/72aa89eee1cffa647135784a1a9a1937e0b998e6))

## Changelog

## Unreleased

- `resolve()`: same-length content tampering (e.g. a store's recorded span
  text edited so its length is unchanged but its content changes) is no
  longer invisible to the span check. New optional `source_text` /
  `expected_content_digest` keyword arguments let a caller supply an
  independent ground of truth; `resolve()` fails closed
  (`SpanMismatchError`) against either when supplied. The prior length-only
  check is unchanged when neither is supplied.
- `resolve()`: the `MissingStoreError` contract is now literal and tested —
  `store=None`, `store=42`, `store=""`, and `versum` not importable all raise
  `MissingStoreError` (previously the "versum not importable" case raised the
  more general `ResolutionError`).
- `pyproject.toml`: the `grounding` extra no longer pins a `loomground-versum`
  tag that lacks `versum.coordinates.entry_coordinates` (the newest tag,
  `loomground-versum-v0.14.0`, predates that commit) — left unpinned, with a
  documented local-development path/branch install note in the same file,
  README.md, llms.txt and docs/model.md.
- Tests needing the `versum` `coordinates` module now SKIP (with a stated
  reason) rather than error when it is unavailable or lacks
  `entry_coordinates`, and when the versum fixture folder is unreachable.
- docs/model.md: corrected the description of `dimensions` in a `5d+nd`
  reference — `resolve()` does not read, filter, or select by `dimensions`;
  only `anchor` decides what span is returned. `dimensions` is validated and
  canonicalized/digested, nothing more, in this module.
- Removed two "mutation probe" tests that exercised inline stand-in functions
  rather than the shipped `resolve()`/`canonicalize()` code paths.
- Repository laid out on the measure skeleton: flat `five_d_nd/` → `src/five_d_nd/` (import path unchanged); `LICENSE` → `LICENSES/MIT.txt` (+ `LICENSES/Apache-2.0.txt` for the vendored `dimensions.py`) + `NOTICE` + `REUSE.toml`; version single-sourced from `src/five_d_nd/_version.py`.
- `resolve()` wired: replaces the documented stub. One canonical span-reference syntax `<source_urn>#<start>-<end>` (over versum's own cleaned-text span offsets), plus `normalize_reference()` accepting it and two READ-ONLY legacy forms (`versum://...#span-a-b`, `{urn}#{unit}:{a}-{b}`), fail-closed (`MalformedReferenceError`) on anything else. `resolve(ref, *, store)` resolves through versum's public API only (`versum.planes.entry_id`, `versum.coordinates.entry_coordinates`) — no private readers, no direct CSV parsing — returning `{entry_id, span, dimension, nd, source_urn, content_digest}`; fails closed with a specific exception (`MissingStoreError` / `UnknownReferenceError` / `SpanMismatchError`) rather than fabricating a result. `versum` is an optional runtime dependency, imported lazily inside `resolve()` only (new `grounding` extra); importing this package otherwise remains stdlib-only.
- Additive content-bound digest: `content_digest(ref, span_text)` — sha256 over `canonicalize(ref)` AND the resolved span text, domain-separated from `digest(ref)`. `digest(ref)` itself is byte-for-byte unchanged (literal regression test against HEAD `3ac16be`).
- Docs (`docs/model.md`, `README.md`, `llms.txt`) updated: canonical span-reference syntax, `resolve`/`normalize_reference`/`content_digest`, and the is/ought note (5D is what IS; a deontic operator O/P/F carries no 5D dimension).
