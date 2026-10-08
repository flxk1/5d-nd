# Evidence for the cross-reference resolver measurement

These files back the claims in `docs/xref-resolver-measurement.md`. They are copied **byte for byte** from the evaluation's record, so the sha256 values below can be checked with `shasum -a 256 <file>`. The report's own hashes for the split and the scoring rules match these files.

| File | sha256 | What it is |
|---|---|---|
| `split.json` | `c96e12133100db8cbb09de3cba736fd25b2f624fe02c72f56c83a2e341ab1010` | The dev/held-out split, locked before any resolver code existed. It holds item ids, the split rule and salt, and per-vertical gold and source hashes. It contains no annotation content. `split.sha256` records the same hash. |
| `SCORING.md` | `dade8ffc13f40451a584103bd301e8ae7497c9502ad71dfc0db6f5b147942a5e` | The scoring rules, locked before the first dev run: matching, normalisation, metrics and breakdowns. |
| `runlog.jsonl` | `ae2ec08d83090cdc814cc0832bc397f813a3114317a80b9f0a5d426f2e57ada5` | Every scorer invocation: part, commit, dirty flag, profile digest and time. It contains exactly two `held_out` lines: the single pre-registered held-out run. |
| `heldout-104.json` | `94ac3d410b5e7dd2ed8178dc419264bd586f696a6af09de42ecf27be311f23c0` | Held-out result, headline: 104 items, with the 8 exposed items excluded and listed in `excluded_ids`. |
| `heldout-112.json` | `a0161ee993657d9d44793669e15a98497b1033616fd012a0165b0c1e8b5471f2` | Held-out result on all 112 items, including the 8 exposed items. |
| `dev-report-d0ee57b.json` | `e4965c070e62bdfdc8e2c7712e607892891c9858ae9b89c077cdeca81ddc4736` | Dev result at the measured commit. The dev part was used for development, so it is not a held-out result. |
| `report-tables.md` | `b8d67242189ee093d047289f4591d890c1fed4cb05c92afba2ec6a8afcedfe04` | The report's tables, generated from the JSON results. Every value is computed exactly from tp/fp/fn and rounded once, half-up. |

The result files contain aggregate counts and metrics only. They carry no annotated sentences.

## Held privately

The following stay in the project's private data store:

- the gold annotations, including the dev extracts;
- the source texts;
- the contamination record, which names the exposed held-out items and the procedure for excluding them;
- the scorer and its wrapper.

The report gives the scorer's and the wrapper's sha256 values. The gold is not public, so readers cannot re-run the scoring, but they can check that these records match the hashes the report cites.

The measured commit, `d0ee57b`, is a pre-publication commit. It is not in this repository's history; the report explains how the published resolver relates to it.
