# Changelog

## Unreleased

### Added

- A 5D fingerprint/coordinate specification (draft 1.0, `spec/SPEC.md`):
  the closed five-dimension set and canonical order, the composition algebra,
  the 5D fingerprint of an entry, 5D's neutrality on is/ought (is and
  ought live in nD grammars, as an optional co-dimension), the assertoric
  (factual) lowering layer, and the nD grammar contract. No Loomground
  repository conforms to this spec yet; versum, solver, and the grammar
  planes are its planned consumers.
- A stdlib reference implementation for the specification
  (`src/five_d_nd/`): the dimension algebra, the 5D fingerprint, the
  assertoric lowering layer, and `NDSystem`/grammar-descriptor validation.
- Machine-readable vocabulary (`vocabulary/`) and JSON Schemas (`schema/`)
  for the 5D layer, plus a conformance vector suite and runner
  (`conformance/`, `tests/test_conformance.py`).
- Typed Statements (spec §21-§23): a richer, reified edge on top of the
  plain triple, with its own codebook (`docs/codebook/typed-statements-v1.md`,
  v3.5) and gold-annotation protocol (`docs/codebook/gold-protocol-v1.md`).
- A typed-Statement extractor (`src/five_d_nd/extract/`): a deterministic
  clause/list-item segmenter and a closed cue-rule table that propose
  candidate Statements from legal text (pure stdlib, no ML, no network —
  the same input always gives the same candidate set). It composes with a
  model-assisted decision stage (spec §23a): a model's answer for a given
  candidate set is recorded once, content-addressed, and thereafter only
  replayed — never recomputed or re-queried. A cache miss raises rather
  than silently falling back to an unassisted result.
- Actor-role and typed-Statement predicate vocabularies (the latter now
  at v3.5).

### Fixed

- `resolve()`: same-length content tampering (a stored span edited so its
  length is unchanged but its content differs) is no longer invisible to
  the span check. New optional `source_text` / `expected_content_digest`
  arguments let a caller supply independent ground truth; `resolve()`
  fails closed (`SpanMismatchError`) against either when supplied.
- `resolve()`: the `MissingStoreError` contract is now literal — an
  absent, non-path, or empty `store`, and `versum` not being importable,
  all raise `MissingStoreError`.
- `pyproject.toml`: the `grounding` extra no longer pins a
  `loomground-versum` tag that lacks a function this package needs; it is
  left unpinned, with a documented local-development install path.
- Tests needing the optional `versum` dependency now skip, with a stated
  reason, when it is unavailable, rather than erroring.

### Changed

- Repository layout: `five_d_nd/` moved under `src/`; licensing moved to
  `LICENSES/` + `NOTICE` + `REUSE.toml`; the version is single-sourced
  from `src/five_d_nd/_version.py`.
- `docs/model.md`, `README.md`, `llms.txt`: corrected the description of
  `dimensions` in a `5d+nd` reference, and of `resolve()`'s own return
  shape.


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

