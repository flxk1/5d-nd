# 0011 — Segmenter integration: a clause/list-item segmenter, grafted and wired in

## Status

Accepted (as a built deliverable). Additive to §21-§23 and to ADR 0010 —
changes none of their decisions.

## Context

Clause segmentation for the extractor was designed through a three-design
comparison: three independently built segmenters, each scored on the
same development-set clause-span metric. The winner was a
recursive-descent grammar; the runners-up (a rule cascade and an FSM
chunker) were read for grafting, per the decisions below.

The extractor's earlier cue-rule stage ran every rule over the whole
unit text at once, with no real clause boundary — the single largest
gap named in ADR 0010, resolved here.

## Decision

### The port and its grafts

`src/five_d_nd/extract/segment.py` is the winning recursive-descent
design, ported with attribution (its own module docstring names the
source) and grafted with:

- **(a) layout-independent list detection** — wired in as a fallback,
  tried per block (not once for the whole unit, which could discard a
  valid ordinary parse of an unrelated block), when a block carries its
  own markers at line-starts with no blank line separating a label from
  its own text.
- **(b) an inline-list reference filter** — `find_inline_list`'s own
  lead-in accepts `:`/`;` as well as a dash
  (`Config.inline_list_colon_semicolon_lead_in`, default ON); the
  sequential->=2-labels guard is unchanged. A continuation-marker kind
  check gap (a `PLABEL`-style continuation, "—(a) …, (b) …", not
  recognised by `scan_inline_items`) is fixed alongside it.
- **(c) coordination without a comma before "and"** —
  `Config.coord_clause_no_comma`, default ON per the codebook's own R-i
  rule, regardless of its measured cost on the development set (see
  "Measured results", below, for the qualitative note).
- **(d) `np_chunks()`** — ported onto this module's own tokenizer and
  lexicon. Modals are never inside a chunk (R-k); a leading
  `a`/`an`/`the` is stripped (R-q).
- **(e) a linguistic chapeau-completeness test** —
  `Config.chapeau_linguistic_complete`, built, measured, and left OFF
  by default (it measured a net negative on the development set).
- **(f) an immutable `Config` dataclass with `with_overrides()`** —
  replaces a global mutable config dict; every parsing method takes
  `cfg` explicitly.

### Wiring into the extractor

`extract.rules.collect_segmented_candidates` (called by
`extract.build.extract_with_spans`, replacing a whole-unit-only scan)
is the entry point:

1. Segment the unit (`segment()`).
2. The scan spans are every node of kind `clause`/`list_item`, plus a
   childless `sentence`/`chapeau`.
3. Run the existing closed cue-rule table (`collect_candidates`) on each
   scan span's own substring, independently — this is what lets a unit
   contribute more than one Statement where the codebook permits it.
4. **Chapeau-subject inheritance** (`inherits_subject_from`): for every
   chapeau node, run the same cue-rule table on the chapeau's own text
   alone first; the highest-priority non-fallback candidate found
   there, if any, is that chapeau's own "trigger" (predicate + subj). A
   bare list item whose own text carries no cue inherits the trigger's
   own predicate and subj, with the item's own full span as `obj`. When
   no trigger is found, the item falls back to its own generic
   `predication` with `subj` forcibly replaced by the chapeau's own
   span. `_detect_chapeau_only_trigger` is a small, separate cue table
   for a chapeau whose own cue is truncated right at the list boundary
   ("...has effect subject to—" names no provision of its own; "shall
   perform the following tasks:" names no act of its own).
5. A shared `chapeau_group` tag keeps sibling items under one chapeau
   from being treated as mutually overlapping by `extract.build`'s own
   overlap resolution.
6. Falls back to the old whole-unit scan when segmentation finds no
   scan span at all (defensive, not the common path).

`tests/test_segment.py` is the segmenter's own test suite, adapted into
`tests/` — every sentence is invented fresh, never a verbatim quote
from a real corpus unit.

## Measured results

Clause-span F1, Statements-per-unit, agreement figures (predicate,
dimension, layer, negation, unitisation), and the residual-modal count
are all measured on a development set and reported qualitatively here,
not as published figures: the integrated segmenter narrows the
extractor's own unitisation gap to the human-coder ceiling measurably,
without closing it; negation agreement improves alongside it (shorter,
cleaner clause spans give the negation module's own scope heuristic
less room to be wrong); predicate/dimension/layer agreement each ease
slightly, since more Statements now compete for the same gold pairing
slots and the new chapeau-inherited ones are lower-confidence by
construction. None of this is a claim of parity with a human coder.

## Known imperfections, carried over or new

- Known limits inherited from the ported design: coder disagreement on
  inline-list-vs-whole-sentence splitting and asyndetic-VP splitting; a
  list in subject position; verbless coordinated NP lists without
  labels; a mid-sentence "unless"/"if" clause; an unlisted lexical verb
  with no modal/auxiliary nearby. None of these are fixed here.
- `_detect_chapeau_only_trigger`'s own cue table is small (four specific
  endings plus one generic actor+modal pattern) — a chapeau trigger
  shaped any other way is not recognised, and its own item falls back
  to the generic chapeau-subject override instead of a more specific
  predicate.
- The chapeau-inherited `obj` span is always the item's own full span —
  `np_chunks()` (graft d) is available as a utility but is not yet
  wired into subj/obj endpoint construction generally (only used and
  tested directly in `segment.py`/`test_segment.py`).
- Past-tense finite-verb detection is not attempted by the ported
  grammar (only `BE_HAVE`'s own past forms, "was"/"were"/"had", are
  recognised) — an ordinary past-tense lexical verb with no modal or
  auxiliary nearby is invisible to `has_finite`.

## Requests to other territories

None — this work stayed inside `src/five_d_nd/extract/`, `tests/`,
`conformance/vectors/extractor/`, `docs/decisions/`, `CHANGELOG.md`.
Measurement against a development set used an un-shipped local
evaluation script, outside this package and outside version control.
