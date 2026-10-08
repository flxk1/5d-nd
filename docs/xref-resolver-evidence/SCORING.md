# Pre-registered scoring for the shared cross-reference resolver (5d-nd §8a)

Fixed by the PO on 2026-10-04, after the dev/held-out split was locked
(`split.json`, sha256 in `split.sha256`) and before any resolver code
existed. The maker implements the scorer to THIS text, and the verifier
checks the scorer against it. Neither the rules nor the split change after
the first dev run. If they had to change, the change would be recorded here
with its date and reason, and all held-out numbers would be re-labelled
"post-hoc".

## Yardstick
- `<vertical>/gold/xref-v2.json` for the 8 verticals gdpr, ai-act, dsa,
  nis2, us-coppa, us-s230, uk-dpa2018 and uk-osa2023, loaded by the logic of
  `_tools/xref-check/all8.py`. Each gold file's sha256 is checked against
  `split.json` before scoring, and the run aborts on a mismatch.
- DEV part: the `dev` ids in `split.json` (extracts in `dev/`). HELD-OUT
  part: the `held_out` ids. The maker develops ONLY against DEV. The maker
  never opens held-out items or full gold files, and never runs the scorer
  on HELD-OUT.
- HELD-OUT is scored exactly once, by the PO, on a frozen resolver commit
  named in the run record. Every scorer run (part, 5d-nd commit, profile
  digest, UTC time) is appended to `runlog.jsonl`. A held-out run before the
  freeze voids the held-out numbers.

## Resolver input per gold sentence
The resolver sees the sentence text, its offsets in the source file, and
document context it could have without the gold:
- the source file text (for preceding-sentence context such as anaphora,
  and for heading and existence lookups);
- the host-instrument metadata the caller supplies (name/number, numbering
  family).

It NEVER sees `references`, `hard_case_tags`, `enclosing_unit` or notes from
the gold. The enclosing unit must be derived from the source text.

## Matching (one-to-one)
A predicted reference matches a gold reference in the same sentence when
their literal spans `[literal_start, literal_end)` overlap. Pairs are taken
greedily by largest character overlap, with ties broken by the earliest gold
start and then the earliest predicted start. Each gold reference and each
prediction is used at most once.

## Normalisation (comparison only)
Comparisons apply NFC, U+00A0 → space, whitespace runs collapsed to one
space, and stripping. Instrument names are also casefolded, and a leading
"the " is dropped. No other aliasing: "GDPR" ≠ "Regulation (EU) 2016/679".

## Metrics (each reported as P, R, F1 and the raw counts tp/fp/fn)
1. **Detection.** tp = matched pairs; fp = unmatched predictions; fn =
   unmatched gold references. Per R1 and R4, a prediction of a bare
   self-reference is an fp.
2. **End-to-end (PRIMARY).** A matched pair is correct when the kind is
   equal AND:
   - INTERNAL: the normalised target pinpoint SET is equal;
   - EXTERNAL: the normalised `external_instrument` is equal.

   e2e P = correct / predictions; e2e R = correct / gold references.
3. **Kind accuracy** over matched pairs.
4. **INTERNAL target level.** Units are (sentence_id, normalised pinpoint)
   over INTERNAL refs, pred vs gold, set semantics. This counts range, plural
   and or-list expansion member by member.
5. **EXTERNAL instrument level.** Units are (sentence_id, normalised
   instrument) over EXTERNAL refs, set semantics.
6. **EXTERNAL target provision: NOT gold-scored.** R7 keeps gold `targets`
   empty for EXTERNAL refs. The resolver's (instrument, provision) output is
   checked by conformance vectors and a PO/verifier spot-check, never
   reported as a gold P/R.

## Breakdowns
- Per vertical, and pooled across all 8 (micro).
- Per kind: INTERNAL / EXTERNAL (per reference, from the gold kind for
  recall and the predicted kind for precision).
- Per reference type, by the gold SENTENCE tag (`hard_case_tags` is
  sentence-level): metrics over the references in sentences carrying that
  tag. Mapping for the requested types:
  - plural / or-list → `plural_or_list` (one tag; the two are not separable
    in the gold);
  - range → `range`;
  - anaphoric "that Regulation" → `anaphoric_external`;
  - also reported: `quoted_amending_text`, `ambiguous_reference` (R6),
    `hard_negative`, `annex`, `chapter_section`, `point`,
    `paragraph_same_article`, `article`, `anaphoric_internal`,
    `external_instrument`;
  - **savings clause → NOT MEASURABLE**: no gold tag exists. Reported as
    "n/a (no gold label)". Never inferred by code.
- Cells with fewer than 5 gold references are printed with their counts and
  flagged "n<5". No significance claims.

## Report
- Held-out numbers are the headline. Dev numbers are shown next to them,
  labelled "dev (tuned-on)".
- The old resolver (`cross_reference_targets` at 5706452, "Article N" only)
  is scored by the same scorer as a reference row.
- Each results file records: the 5d-nd commit, the profile digest, the split
  sha256, this file's sha256, the gold sha256s, and the scorer's own sha256.
