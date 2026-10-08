# Cross-law provision matching: a 5D benchmark result

Dated 2026-10-07, independently recomputed and confirmed 2026-10-08
(0 of 104 ranks differ from the recomputation; every statistic matches
as an exact fraction).

## The question

Does adding a typed 5D signal improve cross-law provision matching
over a structural baseline? "Cross-law" means matching a provision in
one instrument to the corresponding provision in another instrument
that uses unrelated article numbering — for example, which AI Act
article corresponds to GDPR Article 35.

## Design

The design was pre-registered before any arm ran, in a signed protocol
and one signed amendment.

- **Scope.** Only cross-law matching (query class 4.4) was run, on 13
  of the 17 pre-registered clusters: the EU-only clusters. The 4
  cross-tradition clusters, and query classes 4.1-4.3 (navigation,
  absence, typed paths), are not reported here.
- **Clusters and queries.** 13 clusters, each anchored on one GDPR
  provision, with 26 ordered (source, target-instrument) queries
  against the AI Act, the DSA, NIS2 and ePrivacy. Clusters and queries
  were locked by provision ID (instrument plus article number), not by
  file offset.
- **Pool rule.** The candidate pool for each query is every operative
  article of the target instrument; recitals and annexes are excluded.
- **Labelling criterion.** Two provisions correspond when they share an
  analogous trigger, an analogous addressee role, and the same
  principal effect. For an institution-establishing provision, where a
  trigger does not apply, the criterion is addressee role and effect
  only. A shared topic without a shared trigger or effect does not
  qualify.
- **Gold labelling.** A blind model labelled the full query set without
  seeing any arm's output, working only from the pool rule and the
  labelling criterion, before any arm ran. The project owner spot-checked
  16 of the 26 queries by hand and found 0 disagreements. A second,
  independent labeller re-labelled the full set as a cross-check: mean
  Jaccard agreement 0.942, with 22 of 26 queries an exact match. The two
  labellers and the extractor's model-assisted decision stage share a
  model family; the owner's spot-check does not.
- **The structural-plus-lexical baseline.** A reciprocal-rank fusion
  (RRF, k=60) over four signals: direct citation, co-citation,
  bibliographic coupling, and BM25 (lexical) over provision text and
  heading.
- **The typed fourth signal.** The gated arm adds one further signal to
  the same structural RRF: a typed-graph similarity between the source
  provision and each candidate, built from two signatures per
  provision — `Sig1`, a set of (dimension, predicate, role, role,
  layer, negation) tuples, one per Statement; and `Sig2`, a set of
  2-hop directed paths between Statements sharing an endpoint. The
  similarity score is the average of the two signatures' Jaccard
  overlap. Two pre-registered controls isolate what the typed signal
  is actually contributing: a dimension-only variant (predicate
  removed, dimension kept) and an untyped-relation variant (both
  predicate and dimension removed, leaving only role structure). A
  secondary point-cosine variant (the earlier design's fourth signal,
  a cosine between two five-number provision points) was to be
  reported only; it was not computed in this run (see below).
- **The decision rule.** A win requires a mean reciprocal-rank gain of
  at least 0.10 over the structural baseline and an exact one-sided
  cluster sign-flip permutation test at p ≤ 0.05, both holding at once.
  Fewer than 8 non-zero clusters surviving means the benchmark cannot
  gate the migration at all; this is a stated possible outcome, not a
  third win condition. The gate (typed signal vs. structural baseline)
  and the typing claim (dimension-only vs. untyped) were tested in a
  fixed sequence: the typing claim is read only if the gate wins.
- **Statements.** Every Statement used by the typed arm and its
  controls comes from a hybrid extractor: a deterministic rule-based
  stage proposes candidates, and a model-assisted decision stage
  resolves them — each decision recorded once into a content-addressed
  cache and thereafter only replayed, never recomputed.
- **Citations.** The citation graph underlying the structural baseline
  comes from an accepted cross-reference resolver.

## Result

MRR per arm, averaged over the 13 clusters:

| Arm | MRR |
|---|---|
| Structural RRF (citation, co-citation, coupling, BM25) | 0.543 |
| Typed (structural + typed-graph similarity) | 0.403 |
| Dimension-only control | 0.403 |
| Untyped-relation control | 0.308 |

**The gate: a loss.** Mean reciprocal-rank gain −0.140, against the
required +0.10. The exact one-sided cluster sign-flip test gives
p = 477/512 = 0.932, far above the required p ≤ 0.05, over 12
non-zero clusters (one of the 13 clusters tied exactly and drops out of
the significance test by the pre-registered tie rule, though it still
counts toward the mean gain).

Because the gate lost, the typing claim (dimension-only vs. untyped) is
not tested; the fixed-sequence design specifies that it is read only
after a gate win.

**Per query** (26 queries, typed arm vs. structural baseline): 3 wins,
5 ties, 18 losses.

**Sensitivity.** Amendment 1 fixed the RRF's k at 60 and its tie-break
(the canonical-id rule, among candidates tied at a positive score); it
left open citation direction, within-signal tie ranking, and the BM25
parameters (k1, b). The sensitivity check tried one alternative for
citation direction, for within-signal tie ranking, and for BM25 k1
(b and the RRF k were not varied), in 5 combinations, giving a mean
gain between −0.11 and −0.14 and a p-value between 0.89 and 0.93 across
those 5 combinations.

## Why the typed signal lost

- **Coverage and sparsity.** The typed signal returns a non-zero
  similarity for nearly the whole candidate pool: AI Act 98–112 of 113
  articles, DSA 74–92 of 93, NIS2 42–45 of 46, ePrivacy 19 of 21,
  depending on the query. The signatures themselves are short and
  coarse: a median of 4 to 6 `Sig1` tuples per target provision. Every
  one of the 1,639 target `Sig1` tuples has at least one `non_actor`
  endpoint (a concept or an act, rather than a named actor), and 97.1%
  have two. Used alone, the typed signal scores MRR 0.107, against
  0.667 for BM25 alone.
- **It dilutes the fusion rather than adding to it.** As a post-hoc
  diagnostic (not a pre-registered control), a random fourth signal
  was added to the same structural RRF over 300 draws, seed 20261003,
  scoring 0.307 ± 0.054. The untyped control (0.308) sits within the
  spread of those random draws, about 0.02 standard deviations from
  their mean. The typed and dimension-only arms (0.403 each) sit about
  1.8 standard deviations above the random draws' mean, so they do
  carry some information, but well short of the structural baseline.
- **The structural lead is lexical, not citation-based.** Of the 26
  gold query-target pairs, only 3 have any citation link between them
  at all, and one of those 3 runs from the AI Act to GDPR Art. 35, a
  direction the direct-citation signal does not count. The citation
  graph has 927 edges in total, but only 14 of them run between
  instruments, and all 14 point into the GDPR (none point out of it
  toward the AI Act, the DSA, NIS2 or ePrivacy). BM25 alone, with no
  citation signal at all, scores 0.667 — higher than the full
  four-signal structural RRF (0.543). This is consistent with the
  lexical ceiling the pre-registration named in advance for
  GDPR-anchored clusters sharing drafting vocabulary with their
  targets, rather than a citation-graph effect.
- **The point-cosine variant was not computed.** An earlier design used
  a cosine between two five-number provision points as the fourth
  signal, rather than the typed-graph similarity above. Amendment 1
  kept it as a reported, descriptive variant (Sec. 3(a), Sec. 6). That
  variant's own parameters (a clause-cue saturation value and a
  relational suppression scale) were never fixed before the gate ran;
  they were still marked proposed, not accepted, at run time. Choosing
  them now, after seeing the result, would be exactly the look-then-pick
  bias the pre-registration exists to prevent. Omitting it departs from
  Amendment 1's own listing of it as a reported variant; no
  point-cosine number is reported here, deliberately, for this reason.

## Consequence

5D stays a labelled structural index with no role in the migration
(the dim5 → 5D migration), and no claim is made.

## Limitations

- **Shared model family.** The two labellers and the extractor's
  model-assisted decision stage all draw on the same model family; the
  owner's spot-check was done by hand, not by a model. The structural
  baseline, the hash lock on the gold set before any arm ran, and the
  owner's own hand spot-check are the available countermeasures for the
  labellers and extractor; they reduce but do not remove the
  dependency among those three.
- **Labeller temperature.** The pre-registration called for a pinned
  labelling temperature of 0. The runtime did not expose a way to set
  it; this is recorded as an accepted deviation from the signed
  protocol, not a silent gap.
- **Gold provenance.** The gold set is model-labelled, with an owner
  spot-check of 16 of 26 queries by hand (0 disagreements) and a second
  labeller's full-set cross-check (mean Jaccard 0.942), rather than a
  full independent legal review of every query. The signed protocol
  states explicitly that this judge is weaker evidence than a lawyer's
  judgement.
- **The resolver's known limits on EU text.** The cross-reference
  resolver underlying the citation graph has several known failure
  modes on this kind of text: its stop list for a citation list's
  trailing "and" is narrow, so an external instrument name can run on
  past it, absorb surrounding text, and then fail its alias lookup;
  NIS2 is matched by its name only; it drops a trailing "thereof"
  pointing at a sub-unit; it mishandles the or-list tail used in TFEU
  citations; it does not recognise the "Article N GDPR" citation form;
  a plural external-instrument target list is truncated to its first
  member; short instrument names are left unresolved; and ePrivacy
  citations are unvalidated against this resolver altogether.
- **Unit of analysis.** The extraction unit is every segment node —
  sentence, chapeau, list item, or clause — with exact, not
  approximate, deduplication of repeated Statements.
- **Self-references excluded.** The citation graph excludes only a
  provision citing itself; citations within the same instrument, to a
  different provision, are kept. Of 1,140 mapped references, the 213
  self-references are excluded, leaving 927 edges; 913 of these are
  citations within one instrument and are kept.
- **RRF parameters the pre-registration left open.** Amendment 1 fixed
  the RRF's k at 60 and its tie-break rule; it left citation direction,
  within-signal tie ranking, and the BM25 parameters (k1, b) open. The
  benchmark harness filled these in. The sensitivity check above tried
  one alternative for citation direction, within-signal tie ranking and
  BM25 k1; BM25 b was not varied.
- **Unmapped references.** Of the resolver's own citation references,
  1,315 do not map to a provision in this benchmark's pool. Most are
  section, chapter and annex references, or references to instruments
  outside this benchmark's five-instrument universe; 72 are ePrivacy
  references of the form "paragraph N". This affects every arm equally.

## Provenance

The benchmark harness and its underlying data are not part of this
repository. The run that produced the results above is identified by:

- **Harness commit:** `59801d7600e4c846012d9c4ecd53364349f4b506`.
- **Resolver commit:** `d0ee57b606641494b6a6a414aa8f778c82a4be4a`, `src/`
  tree `7ddb0ede4f5f24bfb856728041553429a09dc08d`.
- **Extractor commit (pinned):** `d3fb466f132a67c7aa1aae85c1b456c06cb7ecf4`.
- **Coder-view commit:** `b2b3da5`, coder-view digest (sha256):
  `5b2914076fbc94b7fe360f8a5bf4615462a5af7248084b2a8c45a0be8e17d56d`.
- **Labelling-contract lock (sha256):**
  `216c240741ad8c6c5fd1cd12b0c0e54d07f9fc75e2648835c853a26830787c07`.
- **Decision-cache manifest (sha256):**
  `9edfdd2999974048d76ee39b88f891ddfdef096f3ece0b68a78b6d336853384c`.
- **Lock hashes (sha256), one per run input/output:**
  - judged answers (gold, labeller A): `ad80fc044f8ac1a618d10f76b4ea7ce5d61d3b51c5cb355190996f6512566b28`
  - judged answers (second labeller, B): `3a66de1d84ad1590e562e4f9c5effe83e0e2e37eb8c4b3176b2107a6a157d8e3`
  - candidate pools: `67fdee76525044e80a82285fdabe69e9835954f8914a40327492523384e5a7af`
  - Statements: `d14fc410e0b769fdb8e732ac20221b4edd81b806f3ce34a3d8e2a8dc58ec8a7b`
  - cross-reference resolver input: `7c34264b1928e0f6d8cd1759358521dadfa156e69fa3c5f3d65607ae09b4a8fc`
  - cross-reference resolver output: `23322e8b5c7bb6c443ee991f0de874ff5414c4e6dbce859246c03e510c045072`
  - cross-reference resolver raw output: `3dba40903c26fafb308f6250d37b26a1e75ab497c80b4d086318656c4e2c465a`

The `src/` tree id above identifies the resolver's source content
independent of any later commit-message change on that line of
history; the claim is narrowed to that subtree, not the commit's full
root tree.
