# Measurement report: the shared cross-reference resolver (5d-nd §8a)

## 1. Purpose

The cross-reference resolver reads a sentence from a legal source and
reports the cross-references it contains: whether each one points inside
the same instrument (INTERNAL) or to another instrument (EXTERNAL), and
which provision or instrument it names. The 5d-nd benchmark needs this
resolver because several of its cross-tradition comparisons count
structural cross-references per provision, and a resolver that only
recognised EU-style "Article N" citations could not count US-style
`section N` / `§ N` / U.S.C. citations on the other arm. One resolver,
applied identically to both arms, removes that asymmetry. The resolver
itself takes no side: it is the same code, run under the same profile
logic, regardless of which arm's provision it is reading.

## 2. What changed in 5d-nd

- A new profile field, `xref_resolver`, selects the resolver behaviour.
  `"article-v1"` is the old behaviour (EU "Article N" citations only,
  unchanged) and is the default when the field is omitted. `"shared-v2"`
  selects the new resolver measured in this report.
- The benchmark run uses a fixed bench profile,
  `{"profile_id":"xref-bench-v2","xref_resolver":"shared-v2"}`, digest
  `888f219701d54ab5c592b803fd11d06cb145ad60f5fda26d05949ea3ec3256c3`.
- With `xref_resolver` set to `"article-v1"`, or omitted, the output is
  unchanged from before this addition: the old path is unaffected.
- The numbers below are measured against the pre-publication commit
  `d0ee57b606641494b6a6a414aa8f778c82a4be4a`. The published commit
  carries the same resolver behaviour, cleaned of development history,
  with that equivalence checked by comparing outputs over every
  sentence of all 12 source texts (the 8 measured verticals plus 4
  further sources used for robustness checks).
- This commit was accepted against a fixed bar ("freeze with limits"):
  known defects that do not meet the bar are recorded in §6 rather than
  fixed, and not hidden.

## 3. Method

### Yardstick

The yardstick is cross-reference gold, `xref-v2.json`, for 8 verticals:
gdpr, ai-act, dsa, nis2, us-coppa, us-s230, uk-dpa2018 and uk-osa2023.
Each gold file's annotations are agent-produced and then independently
verified; they are not hand-checked by a human annotator from scratch.
See the gold-integrity note below for how the verification step itself
was checked for this report.

The benchmark's EU side names five EU instruments: GDPR, the AI Act, the
DSA, NIS2 and ePrivacy (Directive 2002/58/EC). ePrivacy is not part of
this yardstick: it is absent from the locked split, so no number in
this report covers it, and the resolver is unvalidated on it.
(Separately accepted xref gold for ePrivacy exists in the data folder,
but it was not part of this pre-registered split and was not used.)

### Split

The dev/held-out split was locked before any resolver code existed
(`split.json`, sha256
`c96e12133100db8cbb09de3cba736fd25b2f624fe02c72f56c83a2e341ab1010`). The
split rule: per vertical, order items by `sha256(SALT + sentence_id)`
ascending; the first `ceil(n/2)` are held-out, the rest dev.

There are 222 items in total: 110 dev and 112 held-out. An earlier status
note misstated the held-out total as 120; that was corrected, before any
held-out run, in `CONTAMINATION.md`'s erratum. The counts below are the
corrected ones.

| vertical | n | dev | held-out |
|---|---|---|---|
| gdpr | 30 | 15 | 15 |
| ai-act | 34 | 17 | 17 |
| dsa | 30 | 15 | 15 |
| nis2 | 30 | 15 | 15 |
| us-coppa | 31 | 15 | 16 |
| us-s230 | 7 | 3 | 4 |
| uk-dpa2018 | 30 | 15 | 15 |
| uk-osa2023 | 30 | 15 | 15 |

### Scoring rules

The scoring rules are locked in `SCORING.md`, sha256
`dade8ffc13f40451a584103bd301e8ae7497c9502ad71dfc0db6f5b147942a5e`. They
cover matching (greedy largest-overlap, one-to-one), normalisation (NFC,
NBSP-to-space, whitespace collapse, casefold and leading-"the" drop for
instrument names only), and the metrics reported below.

### Gold-integrity note

Two of the eight gold files, `dsa/gold/xref-v2.json` and
`nis2/gold/xref-v2.json`, were rewritten after the split lock, removing a
redundant `id` key from each item. The scorer verifies that re-adding that
key and re-serialising reproduces the originally locked file byte for
byte, which shows every other field — sentences, offsets, references,
kinds, instruments, targets, tags and notes — is unchanged, including in
the held-out items. The gold-integrity branch recorded for each vertical
in this run is "exact" for ai-act, gdpr, uk-dpa2018, uk-osa2023, us-coppa
and us-s230, and "reconstructed" for dsa and nis2 (see `GOLD-DRIFT.md`).
No annotation content was altered.

### Held-out exposure

During development, 8 held-out items were exposed: corpus sweeps read
the full source text and fix instructions were written against offsets
in that text, and some of those offsets fell inside or near held-out
sentences. No held-out label was ever seen during development, and
`runlog.jsonl` carried no held-out line until the run reported here.
One of the 8, `us-coppa-xref-026`, was not only looked at but
reproduced near-verbatim in a conformance vector; that vector has since
been rewritten. The other 7 fell within ±300 characters of a
contract-named offset, not inside the named sentence itself. All 8
exposed items are excluded from the headline number; the full 112-item
figure is reported alongside it, labelled.

The 8 excluded items: `us-coppa-xref-026`, `us-coppa-xref-009`,
`us-coppa-xref-010`, `us-coppa-xref-012`, `us-coppa-xref-024`,
`us-coppa-xref-029`, `uk-osa2023-xref-006`, `uk-osa2023-xref-025`.

### Held-out discipline

The held-out part was scored exactly once, as two pre-registered
invocations run back to back in one sitting, with no code, profile or
file change between them:

1. `harness/heldout_excluding.py` (sha256
   `a3dcf03d6d2ca30962113e975f99cf7b7637b590e01a5e0c945a7d34442e4f75`)
   over the 104 unexposed held-out items — the headline.
2. `harness/score.py` (sha256
   `0474dce5eac109328ab5bdcc3af917fc89e27487ae7de113486000ba5df7bdac`,
   unchanged) over the full 112 held-out items.

Both ran on a clean, detached git worktree at commit
`d0ee57b606641494b6a6a414aa8f778c82a4be4a`, `dirty=false`. `runlog.jsonl`
records exactly these two `held_out` lines, both at commit
`d0ee57b606641494b6a6a414aa8f778c82a4be4a`, profile digest
`888f219701d54ab5c592b803fd11d06cb145ad60f5fda26d05949ea3ec3256c3`,
timestamped 2026-10-07T21:55:31Z and 2026-10-07T21:55:32Z.

Dev numbers are reported for reference only. The resolver was tuned
against the dev split, so a dev number is not a held-out result.

## 4. Results

All tables in this section are copied unchanged from `report-tables.md`
(sha256
`b8d67242189ee093d047289f4591d890c1fed4cb05c92afba2ec6a8afcedfe04`).
Cells are P / R / **F1** with raw counts (tp/fp/fn) unless stated
otherwise. Every cell is computed exactly from tp/fp/fn and rounded once,
half-up, to 3 decimals.

### 4.1 Pooled (micro), accepted commit d0ee57b

| metric | held-out 104 (HEADLINE) | held-out 112 (incl. 8 exposed) | dev 110 (tuned-on) |
|---|---|---|---|
| e2e (PRIMARY) | 0.700 / 0.704 / **0.702** (133/57/56) | 0.714 / 0.707 / **0.711** (145/58/60) | 0.749 / 0.749 / **0.749** (152/51/51) |
| detection | 0.916 / 0.921 / **0.918** (174/16/15) | 0.921 / 0.912 / **0.917** (187/16/18) | 0.961 / 0.961 / **0.961** (195/8/8) |
| internal_target_level | 0.819 / 0.713 / **0.762** (149/33/60) | 0.828 / 0.726 / **0.774** (159/33/60) | 0.790 / 0.693 / **0.739** (147/39/65) |
| external_instrument_level | 0.857 / 0.720 / **0.783** (36/6/14) | 0.848 / 0.722 / **0.780** (39/7/15) | 0.929 / 0.886 / **0.907** (39/3/5) |
| kind accuracy | 0.966 | 0.968 | 0.964 |
| OLD resolver (article-v1) e2e | 0.164 / 0.058 / **0.086** (11/56/178) | 0.164 / 0.054 / **0.081** (11/56/194) | 0.160 / 0.059 / **0.086** (12/63/191) |
| OLD resolver (article-v1) detection | 0.552 / 0.196 / **0.289** (37/30/152) | 0.552 / 0.180 / **0.272** (37/30/168) | 0.613 / 0.227 / **0.331** (46/29/157) |

The old resolver row is the pre-existing `cross_reference_targets` path
("Article N" only), scored by the same scorer, for reference only; it is
not a baseline the new resolver is compared against for acceptance.

### 4.2 Per vertical: end-to-end (PRIMARY), held-out 104 vs dev

| vertical | n held-out (104) | held-out e2e | dev e2e |
|---|---|---|---|
| gdpr | 15 | 0.909 / 0.870 / **0.889** (20/2/3) | 0.944 / 0.944 / **0.944** (17/1/1) |
| ai-act | 17 | 0.684 / 0.722 / **0.703** (26/12/10) | 0.742 / 0.742 / **0.742** (23/8/8) |
| dsa | 15 | 0.909 / 0.769 / **0.833** (20/2/6) | 0.657 / 0.676 / **0.667** (23/12/11) |
| nis2 | 15 | 0.760 / 0.731 / **0.745** (19/6/7) | 0.852 / 0.821 / **0.836** (23/4/5) |
| us-coppa | 10 | 0.786 / 0.733 / **0.759** (11/3/4) | 0.889 / 0.762 / **0.821** (16/2/5) |
| us-s230 | 4 | 0.600 / 0.600 / **0.600** (3/2/2) | 1.000 / 1.000 / **1.000** (5/0/0) |
| uk-dpa2018 | 15 | 0.649 / 0.706 / **0.676** (24/13/10) | 0.579 / 0.611 / **0.595** (22/16/14) |
| uk-osa2023 | 13 | 0.370 / 0.417 / **0.392** (10/17/14) | 0.742 / 0.767 / **0.754** (23/8/7) |

The us-coppa row above is the vertical's 10 unexposed held-out items
(16 held-out items minus the 6 excluded); the uk-osa2023 row is its 13
unexposed items (15 minus the 2 excluded).

**Observation on the 2 excluded uk-osa2023 items.** uk-osa2023's held-out
e2e F1 is 0.392 on its 13 unexposed items (the HEADLINE row in §4.2
above) and 0.475 on its full 15 held-out items (the 13 unexposed plus
the 2 excluded). Excluding the 2 exposed items therefore lowers this
vertical's own e2e F1; the exposed items scored better than the
unexposed ones. That is consistent with the exposure having helped the
resolver on those two sentences specifically; it is not proof of it, and
no further inference is drawn here. The exclusion of the 8 exposed
items from the headline stands regardless of the direction of this
effect.

### 4.3 Per vertical: detection, held-out 104

| vertical | detection | kind acc |
|---|---|---|
| gdpr | 1.000 / 0.957 / **0.978** (22/0/1) | 1.000 |
| ai-act | 0.895 / 0.944 / **0.919** (34/4/2) | 1.000 |
| dsa | 1.000 / 0.846 / **0.917** (22/0/4) | 1.000 |
| nis2 | 0.920 / 0.885 / **0.902** (23/2/3) | 0.957 |
| us-coppa | 0.929 / 0.867 / **0.897** (13/1/2) | 1.000 |
| us-s230 | 0.800 / 0.800 / **0.800** (4/1/1) | 0.750 |
| uk-dpa2018 | 0.892 / 0.971 / **0.930** (33/4/1) | 0.909 |
| uk-osa2023 | 0.852 / 0.958 / **0.902** (23/4/1) | 0.957 |

### 4.4 Per kind, pooled held-out 104

Detection split by kind (score.py `by_kind`: a matched span counts for
the gold kind; unmatched gold → fn by gold kind; unmatched prediction →
fp by predicted kind). **This is detection, not end-to-end.**

| kind | detection by kind |
|---|---|
| EXTERNAL | 0.946 / 0.869 / **0.906** (53/3/8) |
| INTERNAL | 0.903 / 0.945 / **0.924** (121/13/7) |

### 4.5 Per reference type (sentence-level gold tag), pooled held-out 104

Cells P / R / F1 (tp/fp/fn); "n<5" = fewer than 5 gold refs. The tag is
assigned at the sentence level. Plural and or-list references cannot be
told apart in the gold and are scored under one tag, `plural_or_list`.
Anaphoric "that Regulation" is scored under `anaphoric_external`.
`savings_clause` has no gold label and is checked by conformance vectors
only (n/a below).

| type (tag) | detection | e2e | flag |
|---|---|---|---|
| ambiguous_reference | 0.889 / 0.800 / **0.842** (8/1/2) | 0.222 / 0.200 / **0.211** (2/7/8) |  |
| anaphoric_external | 0.931 / 0.931 / **0.931** (27/2/2) | 0.655 / 0.655 / **0.655** (19/10/10) |  |
| anaphoric_internal | 0.839 / 0.929 / **0.881** (26/5/2) | 0.516 / 0.571 / **0.542** (16/15/12) |  |
| annex | 0.769 / 0.952 / **0.851** (20/6/1) | 0.385 / 0.476 / **0.426** (10/16/11) |  |
| article | 0.970 / 0.970 / **0.970** (32/1/1) | 0.818 / 0.818 / **0.818** (27/6/6) |  |
| chapter_section | 0.902 / 0.979 / **0.939** (46/5/1) | 0.706 / 0.766 / **0.735** (36/15/11) |  |
| external_instrument | 0.892 / 0.892 / **0.892** (66/8/8) | 0.622 / 0.622 / **0.622** (46/28/28) |  |
| hard_negative | 0.826 / 1.000 / **0.905** (19/4/0) | 0.609 / 0.737 / **0.667** (14/9/5) |  |
| paragraph_same_article | 0.939 / 0.939 / **0.939** (31/2/2) | 0.727 / 0.727 / **0.727** (24/9/9) |  |
| plural_or_list | 0.871 / 0.884 / **0.878** (61/9/8) | 0.557 / 0.565 / **0.561** (39/31/30) |  |
| point | 0.867 / 0.813 / **0.839** (13/2/3) | 0.400 / 0.375 / **0.387** (6/9/10) |  |
| quoted_amending_text | 0.700 / 1.000 / **0.824** (7/3/0) | 0.400 / 0.571 / **0.471** (4/6/3) |  |
| range | 0.926 / 0.962 / **0.943** (25/2/1) | 0.741 / 0.769 / **0.755** (20/7/6) |  |
| savings_clause | n/a (no gold label) | n/a | |

## 5. What the numbers do not show

- **External target provisions are not gold-scored.** Per `SCORING.md`'s
  R7, gold `targets` are kept empty for EXTERNAL references. The
  resolver's `(instrument, provision)` output for EXTERNAL references is
  checked by conformance vectors only; no P/R/F1 in this report covers
  it.
- **German `§ Abs. Satz` citations have no gold among these 8
  verticals.** That citation form is exercised by conformance vectors
  only; this report makes no accuracy claim about it.
- **Plural and or-list references cannot be told apart in the gold.**
  Both are scored under the single tag `plural_or_list`; no breakdown
  between them is possible from this data.
- **Several cells are small.** us-s230 held-out has 4 sentences on the
  headline; us-coppa's headline held-out n is 10. No significance claims
  are made or implied anywhere in this report: differences between rows,
  verticals, or against the old resolver are point estimates only.
- **The gold is agent-annotated and independently verified, not hand-
  checked from scratch by a human.** The gold-integrity note in §3
  describes a mechanical check (byte-exact reconstruction) confirming
  two files' annotation content was unchanged after a key was removed;
  it is not a substitute for a full human audit of the underlying
  annotations.
- **Dev numbers are tuned-on.** They describe the split the resolver was
  developed against and are not reported as a result.

## 6. Known limits

The items below are the KNOWN LIMITS recorded in `spec/SPEC.md` §8a.1 at
the accepted commit. Each is stated as it stands at that commit; see the
cited section for the worked example and exact condition.

- **The narrow "and" stop.** A Title-Case continuation after "and" is
  absorbed into the first treaty's own name unless the next word is one
  of a fixed short list ("Article"/"Articles"/"Section"/"Annex"/
  "Chapter"/"Part"). This condition is narrowed, not closed.
  *Touches the EU instruments*: the acceptance bar required fixing the
  cases that affect the five EU benchmark
  instruments (GDPR, the AI Act, the DSA, NIS2 and ePrivacy) before
  freezing; the residual, open case is names stopping before a word
  outside that short list, which can still occur in and outside those
  instruments.
- **The dropped sub-unit "thereof."** A chain-attached "thereof" (as in
  "<pinpoint> thereof") is recognised only inside a fixed pinpoint-chain
  grammar; outside it, "thereof" is silently dropped and the chain
  resolves bare INTERNAL to the host, with no indication the dropped
  word named anything. *Touches the EU instruments*: this can occur
  wherever a sentence nests a pinpoint reference with a trailing
  "thereof" outside the recognised chain grammar, including in any of
  the five EU benchmark instruments; it is not reported as fixed for
  them specifically.
- **The TFEU or-list tail.** A multi-level TFEU reference does not
  propagate EXTERNAL to every member of a preceding plural/"or" list;
  each list member resolves INTERNAL on its own, and a separate bare
  "TFEU" reference is emitted instead of attaching to each member.
  *Touches the EU instruments directly*: TFEU is a named EU treaty cited
  in the GDPR, the AI Act, the DSA and NIS2 (the ePrivacy Directive
  cites the earlier Treaties instead), and this limit is recorded as
  pre-existing and open.
- **"Article N GDPR" without "of the."** A bare "Article N GDPR"
  citation (no "of") is treated as no item at all, rather than as a
  wrong-kind INTERNAL pinpoint. *Touches the EU instruments directly*:
  it names GDPR explicitly, and mainly affects OTHER hosts that cite
  GDPR in this bare form (it is an under-recall gap on that citation
  shape wherever it occurs); within the GDPR text itself, the gap
  applies only where GDPR's own drafting uses that same bare form.
- **Plural/range external_target truncated to the first member.** A
  plural or range EXTERNAL citation's `external_target` is a single
  string holding only the first expanded member; later members are
  dropped from that field (though not from the literal span). This is
  stated as applying to both the US form and, explicitly, the EU form
  the spec's own worked example gives an EU Directive article range
  truncated the same way. *Touches the EU instruments directly.*
- **Short names unresolved.** A recognised instrument's short name
  (e.g. bare "GDPR", as distinct from "UK GDPR", which is a recognised
  shape) used inside a different host that does not itself carry that
  short name resolves INTERNAL instead of to the named instrument; the
  external reference is dropped entirely rather than flagged. *Touches
  the EU instruments directly*: the spec's own worked example is a bare
  GDPR citation read from inside a different host instrument.

## 7. Reproducibility

The locked split, the scoring rules, the run log and the result files are
published byte for byte in `docs/xref-resolver-evidence/`, with their sha256
values. Its README lists what stays private: the gold, the contamination
record, and the scorer.

Scorer commands (held-out part, run once; see `CONTAMINATION.md`'s
"Exact run procedure" note for the full preconditions):

```
python3 harness/heldout_excluding.py \
  --part held_out \
  --repo <detached worktree at d0ee57b606641494b6a6a414aa8f778c82a4be4a> \
  --profile harness/bench-profile.json \
  --out heldout-104.json

python3 harness/score.py \
  --part held_out \
  --repo <same worktree> \
  --profile harness/bench-profile.json \
  --out heldout-112.json
```

Each results file records:

| field | value | source |
|---|---|---|
| 5d-nd commit | `d0ee57b606641494b6a6a414aa8f778c82a4be4a` | `commit` |
| profile digest | `888f219701d54ab5c592b803fd11d06cb145ad60f5fda26d05949ea3ec3256c3` | `profile_digest` |
| split sha256 | `c96e12133100db8cbb09de3cba736fd25b2f624fe02c72f56c83a2e341ab1010` | `split_sha256` |
| SCORING.md sha256 | `dade8ffc13f40451a584103bd301e8ae7497c9502ad71dfc0db6f5b147942a5e` | `scoring_sha256` |
| scorer sha256 | `0474dce5eac109328ab5bdcc3af917fc89e27487ae7de113486000ba5df7bdac` | `scorer_sha256` |
| wrapper sha256 (104-item run only) | `a3dcf03d6d2ca30962113e975f99cf7b7637b590e01a5e0c945a7d34442e4f75` | `CONTAMINATION.md`, "Exact run procedure" |
| gold sha256, per vertical | ai-act `a6a7f835…`, dsa `d64d3aec…`, gdpr `9021facc…`, nis2 `c549ebd4…`, uk-dpa2018 `8fe556ab…`, uk-osa2023 `c52d627f…`, us-coppa `d5553881…`, us-s230 `ca148ef7…` | `gold_sha256` |
| gold-integrity branch, per vertical | ai-act "exact", dsa "reconstructed:id+indent=1", gdpr "exact", nis2 "reconstructed:id+indent=2", uk-dpa2018 "exact", uk-osa2023 "exact", us-coppa "exact", us-s230 "exact" | `gold_integrity_branch` |
| excluded ids (104-item run only) | `us-coppa-xref-026`, `us-coppa-xref-009`, `us-coppa-xref-010`, `us-coppa-xref-012`, `us-coppa-xref-024`, `us-coppa-xref-029`, `uk-osa2023-xref-006`, `uk-osa2023-xref-025` | `excluded_ids` |

All three result files (`heldout-104.json`, `heldout-112.json`,
`dev-report-d0ee57b.json`) record identical commit, profile digest,
split sha256, SCORING.md sha256, scorer sha256, gold sha256 and
gold-integrity branch values; only `part`, the metric values, and (for
the 104-item run) `excluded_ids` differ between them.
