# 5D — the fingerprint and coordinate language (draft 1.0)

Status: draft 1.0. The key words "MUST", "MUST NOT", "REQUIRED", "SHALL",
"SHALL NOT", "SHOULD", "SHOULD NOT", "RECOMMENDED", "MAY", and "OPTIONAL" in
this document are to be interpreted as described in RFC 2119.

## §1 Scope

5D is the base coordinate/fingerprint system of the Loomground family. It
gives every entry — a span-grounded unit of text — a five-value fingerprint
and one dominant dimension, and gives every typed link between two entries
exactly one of those five dimensions. Domain-specific "nD" grammars (deontic,
epistemic, governance, mathematics, and others) attach to 5D through the
contract in §9; they never add a sixth dimension.

Out of scope: storage format, execution/runtime, sentence parsing (splitting
free text into a subject/predicate/object triple), and any concrete nD
grammar's own vocabulary or reasoning rules. This specification describes the
5D layer and the contract an nD grammar must satisfy to attach to it; it does
not itself define any nD grammar's content.

This is a **specification of an existing, evolving design**, not a novel
invention: §2 draws its meanings from the original 2026-03-21 source (see
Annex A); §5 reproduces versum's `position5d.py` rules; §9 lifts its schema
from versum's `nd.py`/`planes.py`. Where the sources disagree with each
other, an explicit owner decision is recorded (Annex B, and the ADRs under
`docs/decisions/`).

## §2 The five dimensions

5D is a **closed set** of exactly five dimensions, in this canonical order.
Their normative meanings are the **original glosses, quoted verbatim**, from
the first document that treats the five as a closed set (`idea5` commit
`d8a7a93`, 2026-03-21, `cell_algebra.py:13-17`; see Annex A):

```
Structural   — HOW is it built?       (parts, containment, dependency)
Causal       — WHY does it happen?     (triggers, enables, prevents)
Intentional  — WHAT is it FOR?         (goals, justification, telos)
Temporal     — WHEN does it occur?     (sequence, duration, rhythm)
Relational   — WHO/WHAT is connected?  (similarity, contrast, association)
```

| Order | Dimension | Question | Gloss (verbatim) |
|---|---|---|---|
| 1 | `structural` | HOW is it built? | parts, containment, dependency |
| 2 | `causal` | WHY does it happen? | triggers, enables, prevents |
| 3 | `intentional` | WHAT is it FOR? | goals, justification, telos |
| 4 | `temporal` | WHEN does it occur? | sequence, duration, rhythm |
| 5 | `relational` | WHO/WHAT is connected? | similarity, contrast, association |

An implementation MUST NOT add a sixth dimension under any name, and MUST NOT
rename, reorder, or redefine these five. `relational` is the DEFAULT
dimension (§3).

**"Why" maps to causal or intentional — never to a new dimension.** A "why"
question asks either: WHY does it happen (the originals' causal gloss,
verbatim above) — what makes it happen, always an IS question, about
mechanism; or WHAT is it FOR — purpose or justification (the originals'
intentional gloss, "goals, justification, telos", verbatim above) — which
MAY be an is question (a descriptive purpose, e.g. "this valve is for
pressure relief") or an ought question (a normative justification, e.g.
"this rule is justified by..."). Either way the question maps to `causal` or
`intentional`, never to a new dimension; 5D itself does not need to know
which of is or ought is in play (§7, N1) — that distinction, when it
matters, is nD-grammar knowledge (a co-dimension, §7 N3/§9).

**"Justification" under N2-N3 (§7).** The original intentional gloss names
"justification" alongside "goals" and "telos" as part of what INTENTIONAL
means. §7's N2 keeps this literally: a claim that X justifies a norm, a
verdict, or an obligation uses `justifies`, which binds to `intentional`
(the owner-confirmed default for a normative relation, N3) exactly like any
other purpose relation — 5D does not special-case it. What makes `justifies`
NORMATIVE is tracked entirely outside 5D, as a co-dimension on the owning
grammar's own `NDSystem` (N3). See
`docs/decisions/0003-is-ought-in-nd-grammars.md`.

An nD grammar MAY publish its own axes (§9) with any number of values; those
axes are never themselves a sixth 5D dimension, even when an nD grammar's own
document happens to declare exactly five axes (a documented confusion in the
lineage — Annex A, point 9 — that this specification does not repeat).

## §3 The algebra

### The composition table

The 5×5 **composition table** answers: "if A relates to B under dimension X,
and B relates to C under dimension Y, which dimension governs the A→C
inference?" It is reproduced here **exactly** as implemented in
`src/five_d_nd/dimensions.py`'s `COMPOSITION_TABLE` (which is in turn
byte-identical to every copy in the lineage from `idea5 d8a7a93` onward,
including versum's) and in `vocabulary/composition.json`. An implementation
MUST reproduce this table byte-for-byte; no cell may be changed.

| a ＼ b | structural | causal | intentional | temporal | relational |
|---|---|---|---|---|---|
| **structural** | structural | causal | intentional | temporal | structural |
| **causal** | causal | causal | intentional | temporal | causal |
| **intentional** | structural | causal | intentional | temporal | intentional |
| **temporal** | structural | causal | intentional | temporal | temporal |
| **relational** | structural | causal | intentional | temporal | relational |

Read as `table[a][b]`.

### Identity

`relational` is a **two-sided identity**: `compose(d, relational) == d` and
`compose(relational, d) == d` for every dimension `d`. It is also the
**default** dimension (§2): an edge, entry, or claim with no information
otherwise assigned MUST use `relational`.

### Non-commutative, non-associative

The table is **NOT commutative** in general — e.g. `compose(causal,
intentional) == intentional` but `compose(intentional, causal) == causal`.

The table is **NOT associative**. Of the 125 ordered triples `(a, b, c)`,
exactly two disagree by grouping:

- `(causal, intentional, structural)`
- `(causal, temporal, structural)`

For both, `compose(compose(a, b), c) != compose(a, compose(b, c))` (verified
against `COMPOSITION_TABLE`; see `conformance/vectors/fold-left/`).

### Left-fold is the normative evaluation order

Because the table is not associative, a path of three or more dimensions has
no single answer without a fixed evaluation order. This specification adopts
**left-fold** — `compose(compose(compose(a, b), c), ...)`, evaluated strictly
left to right along the path — as the NORMATIVE evaluation order. An
implementation MUST evaluate a path of dimensions left-fold, and MUST NOT
silently evaluate right-fold or any other grouping. See
`docs/decisions/0004-left-fold.md`.

### Weight composition — NORMATIVE (resolved 2026-10-01)

`compose_weights(w1, w2) = w1 * w2` (multiplicative) is **NORMATIVE**:
weights MUST compose multiplicatively along a path. The owner's fixed
decision (2026-10-01): "Weights multiply along a path. This becomes
normative, and the Annex B OPEN marker is removed." This resolves the
lineage conflict this
section previously left open (Brain's per-dimension MIN/mean/product rules,
Annex A point 1, vs. the cell-kernel-onward single multiplicative rule) in
favour of the single multiplicative rule, matching every copy of the
lineage from the cell kernel onward and this repository's own
`compose_weights`. The corresponding Annex B entry and
`docs/decisions/0005-weights-informative.md` are superseded — see
`docs/decisions/0006-weights-normative.md`. §11/§12 build directly on this:
a triple's `weight` (§11) composes along a path by this same rule, and
§12's fixed-point arithmetic is what makes that composition's accumulation
well-defined at scale.

## §4 Entries and references

An **entry** is a span-grounded unit: `{source_urn, start, end, text}`, where
`text` is the EXACT slice of the cleaned source text at `[start, end)`. See
`schema/entry.schema.json`.

The **canonical reference syntax** addresses an entry:

```
<source_urn>#<start>-<end>
```

e.g. `urn:dls:sha256:defa9705...#11-88`. Two READ-ONLY legacy forms
normalize to it and are never emitted:

- `versum://<path>#span-<start>-<end>`
- `<urn>#<unit>:<start>-<end>` (the unit token is a hint, dropped on
  normalization)

Canonicalisation (`canonicalize(ref) -> bytes`) is deterministic JSON — keys
sorted recursively, compact separators, UTF-8; a JCS-style approximation, not
full RFC 8785. The **digest** (`digest(ref) -> {"sha256": hex}`) is sha256
over `canonicalize(ref)`. These rules are specified exactly as implemented in
`src/five_d_nd/grounding.py`; an implementation MUST reproduce them
byte-for-byte (see `conformance/vectors/reference/` for literal regression
vectors, reused from this repository's own existing test expectations). This
specification does not change `grounding.py`'s existing behaviour.

## §5 The 5D fingerprint (coordinate) of an entry

Every entry carries exactly **ONE position**: one value on each of the five
dimensions, computed deterministically from the entry's typed relations and
the installed nD grammars' bindings (no neural vectoriser). 5D is neutral on
is/ought (§7, N1): this computation does not look at, or branch on, whether
a contribution came from a normative relation. These rules are taken exactly
from versum's `position5d.py` (`git -C loomground-versum show
origin/main:src/versum/position5d.py`, read 2026-09-30) and specified — not
reimplemented differently — here and in `src/five_d_nd/position.py`:

1. Each claim an nD grammar makes on the entry contributes 1 to the
   dimension its grammar's binding maps the claim's `relation` to.
2. Each coordinate field of that claim whose axis id the grammar's binding
   maps contributes 1 to that dimension.
3. **Containment.** For EVERY other entry this entry structurally embeds
   (an outgoing structural `embeds` link, §6) — regardless of which plane
   produced the embedded entry, and regardless of whether THIS entry's own
   claims contribute anything at all — this entry's OWN position gets `+1`
   structural, ONE per outgoing `embeds` link. This is versum's own rule
   (`src/versum/planes.py` `build_source_entries`:
   `contrib[parent["item_id"]][EMBED_LINK_DIMENSION] += 1`), not a claim
   contribution: it is purely positional, derived from span containment,
   computed by versum's indexer for every embedded entry. An implementation
   MUST reproduce it — `src/five_d_nd/position.py`'s `with_embeds()` is the
   seam that applies it. A normative entry that binds nothing at all (e.g.
   a deontic norm, whose plane's own binding is `{}`) still gets a
   NON-ZERO, NON-DEFAULT position through this rule alone, from its
   `embeds` link to its own lowered content (§7 N4) — this is the ONLY
   contribution such an entry has, and it is enough to make its position's
   `basis` `"planes"`, not `"default"`.
4. Contributions come from the assertoric (factual) layer (§8) AND from
   relations bound by an nD grammar (§9), normative or not.

The five raw contributions — the SUM of rules 1-4 above — are **normalised
to sum to 1**, rounded to **six decimal places**. The **dominant** dimension
is the `argmax` of the RAW (pre-normalisation) contributions; ties are
broken by the canonical order — `structural, causal, intentional, temporal,
relational` — the earliest wins. An entry with **no contribution at all**
(basis `"default"`) gets the all-zero position and dominant dimension
`relational` (§2's default). Otherwise, basis is `"planes"`.

See `schema/position.schema.json` and `conformance/vectors/position/`.

## §6 5D links

A **link** is a typed relation between two entries. Every link carries
**exactly one** of the five dimensions (§2) — never zero, never more than
one — **and nothing else that 5D itself requires** (§7, N1: no mode, no
is/ought marker). See `schema/link.schema.json`; an nD grammar MAY attach
its own additional fields to a link it emits (e.g. its own normative
marker), and 5D simply ignores what it does not itself define.

`embeds` is the one link relation this specification names: it is **always**
dimension `structural`, matched case- and separator-insensitively (§7, N4).
It is the mechanism §7 uses to bring a norm's content onto the 5D manifold.
It is ALSO the one relation that feeds §5's containment rule (rule 3): the
SOURCE entry of every `embeds` link gets `+1` structural in its own
position, regardless of what else it contributes.

## §7 Is and ought live in nD grammars, as co-dimensions

**Settled, owner design change, 2026-10-01 (N1-N4; supersedes BOTH of this
branch's earlier designs — D2, "no dimension for ought at all", and R1-R5,
"every link carries a mode" — see
`docs/decisions/0003-is-ought-in-nd-grammars.md` for the full history
with both of the owner's dated statements):**

> The owner's decision (first statement, 2026-10-01): "Is/ought can be a
> part of 5D, but needs to make sure the normative/deontic parts stay in
> 5D differentiated."
>
> The owner's decision (second statement, same day — this is the one
> that stands): "'Every 5D link is marked is or ought.' This is
> over-engineered. 5D doesn't need to know that. ND-Grammar can know
> this as co-dimension(s)."

- **N1 — 5D knows nothing about is/ought.** A 5D link carries exactly one
  dimension, nothing else. There is ONE 5D fingerprint per entry (§5, the
  unchanged versum-parity rules). Fold is the plain left-fold through the
  table (§3) — unaffected by anything in this section.
- **N2 — a normative relation binds like any other.** Normative relations
  MAY bind to a 5D dimension exactly like any other relation. 5D does not
  special-case them, does not require them to carry any particular mode (it
  has none), and does not reject a binding for being normative.
- **N3 — co-dimension: whose knowledge, where it lives (final, OPTIONAL —
  owner decision, 2026-10-01).** Whether a relation is normative is the
  OWNING nD grammar's own knowledge — never 5D's. It MAY be carried as a
  **co-dimension**: an ordinary axis a grammar declares in its own
  `NDSystem` (§9) ALONGSIDE a binding, using nothing beyond what `NDSystem`
  already offers (e.g. the deontic plane's existing `operator` axis, closed
  vocabulary `{O, P, F}`, already does this — no new machinery is
  introduced). A grammar that binds a normative relation SHOULD default its
  dimension to `intentional` (owner-confirmed default, matching the original
  `idea5` intentional gloss's "goals, justification, telos"); declaring a
  co-dimension axis to mark the normative character is NOT required — a
  grammar MAY bind a normative relation with no co-dimension at all and
  still conform. The owner's decision, 2026-10-01: "co-dimension rule is
  final, optional."
- **N4 — kept from both earlier designs.** No verdict or decision of an nD
  language reads a composed 5D weight or position (§9's invariant,
  unchanged throughout all three designs on this branch). A norm's
  regulated content MAY still enter 5D as its own entry, linked by a
  structural `embeds` link (§6) — the relation name is matched case- and
  separator-insensitively (`Embeds`, `EMBEDS`, ` embeds ` all recognised;
  `src/five_d_nd/contract.py`'s `normalise_relation_key()`/
  `is_embeds_relation()`).

**What replaced the two earlier "declared dimension"/"mode" rules.** D2
required a normative entry's declared `dimension` to be `null`; R1-R5
required every link to carry an explicit `mode`. N1-N4 replace BOTH: there
is no declared-dimension-null rule and no link mode. A normative relation
binds a dimension exactly like any other (N2); what distinguishes it is
entirely outside 5D, on the grammar's own co-dimension axis (N3).

## §8 The assertoric layer (D1)

**Decision D1** (owner-approved default, 2026-09-30; see
`docs/decisions/0002-factual-belongs-to-5d.md`): the factual/assertoric
grammar belongs to the 5D language itself — it is HOW an assertion gets its
5D fingerprint, not a domain nD grammar.

**Source correction (2026-10-01).** This section was previously vendored
against a LOCAL clone of loomground-factual that had fallen 9 commits
behind GitHub. It is now re-derived, in full, from a FRESH clone of
`https://github.com/flxk1/loomground-factual` at `ebf9fe1` (release 0.2.0,
the GitHub head as of this correction). This is a FULL re-derivation, not a
patch: factual's grammar changed shape entirely — the whole-sentence
`_STRUCT` regex an earlier draft of this section vendored NO LONGER EXISTS
upstream. **Going forward, factual MUST be read from a fresh clone of its
GitHub head, never from the stale local sibling clone this branch
previously relied on.**

The assertoric layer lowers an ALREADY-BOUNDED sentence/clause — a single
string, `lower_assertion(sentence)` — to a 5D link, or `None` on one of
three documented abstention paths (D1: a plain link, carrying one
dimension and nothing else — 5D is neutral on is/ought, §7 N1). "Already
bounded" means: sentence-BOUNDARY determination (splitting a paragraph into
sentences) is OUT OF SCOPE — but the clause-internal cues below (copula,
ordering, modal, clausal-complement) ARE in scope, because they are fixed,
data-driven regex cues, not open-ended discourse parsing.

These rules are VENDORED — not reinvented — from loomground-factual's
`grammar.py` (`lower()`, `_clause()`, `_candidates()`, `_analyse()`) and
`artifacts/extraction.json`/`artifacts/binding.json`, and specified
exactly, not reimplemented differently, in `src/five_d_nd/assertoric.py`:

**Three cue kinds**, found by `_candidates()`: a **copula**
(`predicate_cues.copula` — `is`/`are`/`shall be`/`means`/`include(s)`/
`consist(s) of`/`refer(s) to`), a temporal **ordering** cue
(`ordering_cues` — `precedes`/`comes before`/`takes place before`/`is
followed by` → relation `precedes`; `follows`/`comes after`/`takes place
after`/`succeeds` → relation `follows`), or a **modal** auxiliary
(`modal_cues.modal` — `must`/`shall`/`should`/`may`/`can`/`could`/`might`/
`will`/`would`/`(is|are) required to`/`(has|have) to`/`ought to`, with an
optional captured `not`). The WINNING candidate is the EARLIEST-starting
match; a tie is broken by the LONGEST match; a further tie by kind order
`ordering (0) < copula (1) < modal (2)` — "maximal munch": `"is required
to"` beats the bare copula `"is"`; `"is followed by"` beats the copula
`"is"`; `"shall be"` beats the modal `"shall"`.

**Relation and dimension, per winning kind** — the relation name is looked
up in `binding.json`'s fixed map (`is-a`/`part-of`/`has-part` →
**structural**; `precedes`/`follows` → **temporal**; `predication`
(the default) → **relational**):

- **copula**: the relation defaults to `predication` (relational); THEN
  `predicate_cues.relations` (`is-a`, `part-of`, `has-part`) is searched
  over the WHOLE clause — if one matches, the relation becomes that name
  (structural), and for `part-of`/`has-part` the PREDICATE itself becomes
  the matched relation phrase (e.g. `"part of"`), not the bare copula.
- **ordering**: the relation is the cue's OWN name (`precedes`/`follows`)
  — **temporal**. This is NEW since the stale source: "Registration
  precedes processing." now lowers TEMPORAL — a dimension an earlier draft
  of this section incorrectly claimed the assertoric layer "never
  produces" ("always structural or relational"); that claim is corrected.
- **modal**: the auxiliary is stripped, the next bare verb token becomes
  the predicate, and the relation is **ALWAYS** `predication` (relational)
  — regardless of what the REST of the clause contains. "The controller
  must ensure that the system is a secure system." lowers **RELATIONAL**
  (the modal fires first and hard-codes `predication`), even though the
  embedded "is a secure system" would, on its own, read as a structural
  is-a copula — the modal branch does NOT re-scan the rest of the clause
  for a copula relation. This is the modal rule an earlier draft of this
  section got wrong (it scanned the WHOLE sentence for a structural cue
  regardless of which kind won). A `modal_cues.temporal_subordinate` cue
  (`before`/`prior to`/`until` → `precedes`; `after`/`once`/`following` →
  `follows`) found in the text after the verb trims the OBJECT boundary
  there (the dependent clause it introduces is a separate fact, out of
  scope for this single assertion) but never changes the modal clause's
  own relation.

**A clausal complement** (`complement_cues.clausal_complement` —
`knows`/`believes`/`is aware`/`are aware`/`becomes aware`/`considers`/
`finds`/`states`/`establishes(d)`/`holds`/`is satisfied`/`are satisfied` +
`that`), found ANYWHERE in the sentence, means the sentence is NOT itself a
fact about its own subject: only the clause AFTER the complement cue's
match is lowered — the attitude verb and its subject are discarded.

**Object, negation, quantification** — the object is stripped of its
leading determiner (`a`/`an`/`the`/`one of (the)`/`part of` —
factual's `_OBJ_LEAD`). `empty` quantification (`no`/`none of`/`neither`
over the clause's own SUBJECT text) ALWAYS forces `negated` true, for
every kind. ON TOP OF that floor, negation differs by kind — an
implementation MUST reproduce each exactly, not generalise one to the
others:

- **copula**: ALSO negated when `polarity_cues.negation`
  (`\b(?:not|no|never|neither|without)\b`) matches the first 24 characters
  of the RAW object text (before its leading determiner is stripped).
- **ordering**: has NO object-side negation scan at all — ONLY `empty`
  quantification can negate an ordering clause. This is deliberately
  NARROWER than the copula path and MUST be reproduced narrower, not
  generalised (an implementation that also scans an ordering clause's
  object for `not`/`no`/etc. does NOT match factual).
- **modal**: ALSO negated when the modal cue's own captured `not` group is
  present (e.g. "cannot", "can not", "must not").

**A content clause** (an infinitive/bare-verb clause with no subject of its
own — the action a norm's modal auxiliary and bearer have already been
peeled off elsewhere) lowers ONLY through factual's own `plane.produce()`'s
`context` parameter, **NEVER through `lower()`** — and `lower_assertion()`
is the `lower()` equivalent, not the `produce()` one. Subject-resolution
machinery for that shape (a document-defined-terms registry, pronoun/
named-subject detection, a discourse frame stack) is sentence/discourse-
level reasoning this specification has always kept OUT OF SCOPE (§1), and
`lower()` itself never reaches any of it either (it receives no `context`)
— so NONE of it is vendored, and an implementation MUST NOT attempt to.

An implementation MUST NOT invent additional cue surface variants beyond
factual's exact patterns (e.g. "subclass of", "instance of", "member of"
are NOT in factual's `is-a` cue and MUST NOT classify structural).

**Output shape.** `lower_assertion(sentence)` returns,
on success, EXACTLY these eight fields — no more, no fewer — matching
factual's OWN internal record field for field (`_analyse()`/`_clause()`'s
full record, not the narrower public `lower()`, which drops two of them):

```
{
  "subject": str, "predicate": str, "object": str,       # factual's "fact"
  "dimension": "structural"|"temporal"|"relational",     # sub-dict, all 6
  "negated": bool, "quantification": "universal"|"existential"|"empty",
  "relation": "is-a"|"part-of"|"has-part"|"precedes"|"follows"|"predication",
  "canonical": null | [canonical_name, converse: bool]   # ORDER kind only
}
```

`relation` and `canonical` are NOT part of factual's public `lower()`
return value — `lower()` returns only the inner `"fact"` sub-dict of
`_analyse()`'s full record, discarding `relation`/`canonical`/`span`/
`subordinate`. This specification's `lower_assertion()` keeps `relation`
(the exact name :data:`BINDING`/`binding.json` was keyed by to produce
`dimension`) and `canonical` (`null` for a COPULA or MODAL clause; for an
ORDER clause, the pair `[canonical_name, converse]` from
`ordering_cues` — e.g. a `"follows"` clause carries `["precedes", true]`,
meaning its direction is the CONVERSE of `precedes`) because `precedes` and
`follows` bind to the SAME dimension (`temporal`) but are OPPOSITE
directions: without `canonical`, an ordering fact's own direction is lost
the moment it needs to be compared against another ordering fact. `span`
and `subordinate` are NOT carried — they describe POSITION within the
original sentence text, information `lower_assertion(sentence)`'s
single-clause contract has no use for (an implementation MAY compute them
itself from `sentence` if it needs them; this specification does not
require it).

See `tests/test_conformance.py`'s differential test, which compares this
module's full output — ALL EIGHT FIELDS — against loomground-factual's own
`_analyse()` record (flattened the same way), sentence for sentence, on:
factual's own `tests/test_extraction_quality.py` CASES; ten additional
cross-cutting sentences (ordering, has-part, a modal with an embedded
copula-looking rest, a clausal complement); and factual's own
cue-tiebreak/negated-required/none-path pinning tests — **0 differences**
across all of them, when `loomground_factual` is importable.

## §8a The clause-cue layer (D2) — additive richer lowering

**Status: owner-approved integration step, 2026-10-02** —
integrating the winning build's own grafts (candidate C) onto
the frozen reference implementation, specifically the "richer multi-
relation clause lowering" graft (see
``docs/decisions/0007-clause-cue-layer-and-example-grammars.md``).
This section is **ADDITIVE ONLY**: §8 (D1, the assertoric layer) above is
UNCHANGED — every factual-parity guarantee that section states, and every
`assertoric-lowering` conformance vector, stays exactly as it was. §8a
defines a SECOND layer that sits alongside §8, never inside it, in
`src/five_d_nd/clause_cues.py`.

**Important — this is NOT a claim about loomground-factual.** §8 states,
correctly, that the assertoric layer matches loomground-factual @
`ebf9fe1` exactly, and that remains true: factual's own `lower()` has no
counterpart to this section's cue table at all. §8a's own cue table is
this specification's own addition, with no upstream implementation to be
faithful to. Migrating it upstream (or not) is an OPEN item, recorded in
Annex B — never stated here as something factual already does.

**The problem this section answers.** Measured against the GDPR's
operative text, §8's own
single-cue-kind lowering sends most sentence entries to
`predication` → `relational` alone — EVERY modal sentence ("shall",
"may", "must"), because the modal branch (§8) never re-scans a clause's
rest for any other cue. The resulting points collapse: retrieval quality
against a same-article/cross-reference ground truth sits at chance
across every 5D-only variant tried. A clause's OWN surface form usually
carries more than one kind of content — a condition, a purpose, a
deadline, a containment relation, a cross-reference — and §8's single-cue
contract cannot see any of it once the modal cue has already fired.

**The rule.** A clause is scanned, independently of §8's own cue match,
against FIVE closed, deterministic, case-insensitive regex cue tables —
one per 5D dimension (`five_d_nd.clause_cues.CUE_TABLE`):

| content cue | dimension | example surface forms |
|---|---|---|
| conditions/causes | `causal` | `if`, `where`, `because`, `unless`, `results in`, `due to`, `risk(s)` |
| purposes | `intentional` | `for the purpose(s) of`, `in order to`, `aimed at`, `to ensure` |
| deadlines/sequence | `temporal` | `within <n> days/months`, `without undue delay`, `before`/`after`, `no later than` |
| containment/definitions/cross-reference wording | `structural` | `part of`, `consists of`, `'X' means any/a/an/the ...` (or a GENUINE opening-then-closing quoted term within 40 characters of `means` — a bare possessive apostrophe does not count — never a bare `means`), `referred to in paragraph`, `Annex` |
| entity/obligation vocabulary | `relational` | `controller`, `processor`, `data subject`, `right to`, `obligation` — ALWAYS counted, then DOWN-WEIGHTED (see below) |

EVERY matching cue in `causal`/`intentional`/`temporal`/`structural` adds
`+1` to its own dimension's raw count, and a clause may (and typically
does, in regulatory text) hit more than one table at once — a modal
sentence is NO LONGER reduced to a single `predication` → `relational`
contribution by THIS layer; it contributes the dimensions of its own
content cues.

**`relational` is DOWN-WEIGHTED by how many other cues fire — DECIDED
2026-10-03, replacing the earlier all-or-nothing gate.** The PREVIOUS
design counted `relational` ONLY when NONE of the other four dimensions
hit at all — a deliberate choice avoiding GDPR's relational vocabulary
(`controller`/`processor`/`data subject`) re-creating the same collapse
this layer exists to fix, one layer up — but that gate was DISCONTINUOUS
by construction: GDPR Art. 65(5)'s own sentence ("The lead supervisory
authority... shall inform the Board of the date when its final decision
is notified...") scored `relational: 5`; inserting one clause-initial
"Where applicable, " flipped it straight to `relational: 0`, a jump on a
single added word. **The owner decided, 2026-10-03, to REPLACE the gate
with down-weighting instead of keeping it** (a previously open owner
decision, now resolved): `relational` is ALWAYS
counted from its own cue table, then run through

```
relational_eff = relational_count * s / (s + n_other)
```

where `n_other` is the sum of the OTHER four dimensions' own
de-duplicated hit counts and `s` is a new resolution-profile field,
`relational_suppression_scale` (§16; default `1`) — the SAME `x/(x+s)`
monotone family §14's own nesting signal (`five_d_nd.depth`) already
uses. **The FORMULA itself, and its default scale, are a separate
design choice** (the owner's decision was the DIRECTION — replace the gate —
never this specific formula; see
`src/five_d_nd/clause_cues.py`'s `relational_effective()` and
`docs/decisions/0007-clause-cue-layer-and-example-grammars.md`). Three
properties hold and are tested directly: `n_other == 0` leaves
`relational` COMPLETELY UNCHANGED (GDPR Art. 65(5)'s own sentence still
scores `5`); the result is MONOTONE NON-INCREASING in `n_other`; at the
DEFAULT scale, one extra non-relational cue AT MOST HALVES the value
(Art. 65(5) with one added causal cue: `5 -> 2.5`, never the old gate's
jump straight to `0`). It is the
RESULT of the division that is QUANTISED the SAME way §11's point
formula is — `s` itself is an input parameter, never rounded — one
division, rounded ONCE to 6 decimal places at this single
materialisation point. **§8's own frozen base `+1 relational`
contribution on a modal sentence is deliberately NOT given the same
down-weighting treatment** — it is produced by the UNCHANGED,
loomground-factual-parity-critical assertoric layer (§8) and only SUMMED
by `combined_contributions()`, never re-graded; applying down-weighting
there would mean touching §8's own frozen output, which this
specification's own repeated "§8 is unchanged" rule forbids.

**Cross-references become explicit links, not only a count.** An
`Article N` / `Article N(M)` citation contributes `+1 structural` PER
DISTINCT target article (`five_d_nd.clause_cues.cross_reference_targets`)
AND an explicit directed §11 triple-shaped link, `source_id ->
"Article N"`, relation `cross_references`, dimension `structural`
(`cross_reference_links`) — "cross-references → explicit links between
entries" (see ADR 0007). The link records a fact
about the citing sentence's own surface form; it is never itself
normative (§7 N1 is unaffected).

**A citation naming the HOST instrument's own number is INTERNAL, not
external.** A bare "of this/the Regulation" is
already treated as internal (it is GDPR referring to itself); a citation
that instead gives the host's own NUMBER explicitly — "Article 45 of
Regulation (EU) 2016/679" — names the SAME instrument the text is part
of, and must resolve the same way: `[45]`, internal, not excluded by the
external-instrument check. `cross_reference_targets` takes an optional
`host_instrument_number` (e.g. `"2016/679"`). Without it supplied, such
a citation is (correctly, conservatively) still excluded as external,
since the module cannot know its own host number on its own. The
qualifying-word slot before "Regulation" (e.g. "Council", "Commission
Implementing", "European Parliament") now accepts MULTIPLE words, not
only one — "Article 6 of Commission Implementing Regulation (EU)
2021/1372" is external, the same as the single-word "Article 4 of
Council Regulation (EC) No 1/2003" always was.

**`host_instrument_number` is CALLER-SUPPLIED DOCUMENT METADATA, NEVER a
resolution-profile field.** A resolution profile
(§16) is shared across many documents; the host instrument's own
number is a property of ONE document (which Regulation this text IS),
not a tunable a whole profile should carry. It is threaded as an
optional keyword, defaulting to `None` (unchanged behaviour), through
`cross_reference_targets` -> `cross_reference_links`,
`clause_cue_contributions`, `combined_contributions`, and
`clause_cue_point` — every caller of the clause-cue layer that wants
the self-reference behaviour supplies it directly, at call time, from
whatever document metadata it already has.

**Points keep the UNCHANGED §11 formula.** `five_d_nd.clause_cues` never
touches `point_from_contributions` — it supplies a RICHER raw
contribution vector (`combined_contributions`: §8's own `+1` on its
single dimension, PLUS this layer's own cue counts, summed per
dimension), which the unmodified §11 formula then saturates and rounds
exactly as before. The default saturation for THIS layer's own counts is
a resolution-profile field, `clause_cue_saturation` (§16; default 3,
separate from §11's own `point_saturation`, because a clause's own cue
hits are typically 1-4 per dimension, not an entry-level aggregate).

**Explicit field types.** The raw-contribution mapping this layer
produces and consumes has the SAME shape §11 already validates for a
point's own raw input: a mapping over the five dimension keys (§2).
`causal`/`intentional`/`temporal`/`structural` are each a non-negative
INTEGER count (one `+1` per de-duplicated cue hit). **`relational` is
now a non-negative NUMBER, fixed-point, not an integer count**
(`relational_effective()`'s own
down-weighting formula, §8a above, produces a fraction whenever
`n_other > 0`, e.g. `2.5`, rounded to 6 decimal places at its own
materialisation point — never re-rounded here).
`five_d_nd.point.point_from_contributions` itself rejects an unknown
dimension key or a negative contribution on ANY dimension (unchanged);
it was never actually integer-only even for the other four dimensions —
only this module's own cue-counting discipline makes them integers in
practice. This section introduces no new document shape of its own to
validate.

See `src/five_d_nd/clause_cues.py`,
`conformance/vectors/clause-cues/`.

### §8a.1 The shared cross-reference resolver

**Status: ships as ONE versioned 5d-nd change** (this spec text,
`conformance/vectors/clause-cues/xref-v2-*.json` and
`conformance/vectors/resolution-profile/xref-resolver-field-*.json`, and a
new resolution-profile field/digest below) — a precondition of the signed
5D benchmark (benchmark protocol §8), applied identically to both arms.
**ADDITIVE ONLY**: `cross_reference_targets`/`cross_reference_links`
("article-v1" below) are UNCHANGED, forever, for exact replay of every
pre-existing vector and digest. This section adds a NEW entry point,
`five_d_nd.clause_cues.resolve_references()` ("shared-v2"), selected by a
NEW resolution-profile field, never a silent change to the old one.

**Scope.** `article-v1` matches only `Article N` (and its plural/ranged/
listed form) and DROPS every other instrument's citation outright.
`shared-v2` resolves (a) EXTERNAL citations — of ANY jurisdiction's
instrument the text names, not only EU ones — to `(instrument,
provision)`, and (b) INTERNAL references in the numbering families
listed below, including ranges, plurals, or-lists (one target per
expanded member) and reference resolved against the ENCLOSING unit. It
is built against a hand-annotation contract's rulings R1-R7 — mapped
below — and is a PURE, deterministic function of the clause text plus
caller-supplied document metadata; it never reads gold, never reads
anything the caller did not pass in.

**Input/output contract.** `resolve_references(text, enclosing_unit=None,
numbering_family="eu", host_instrument_name=None,
host_instrument_number=None, whole_host_unit=None, preceding_text="",
quoted_amending_target=None)` returns a list of reference dicts, each:

```
{
  "literal": str,              # the exact cited substring, as written
  "literal_start": int,        # offsets into TEXT (caller adds its own
  "literal_end": int,          #   document-level base offset itself)
  "kind": "INTERNAL" | "EXTERNAL",
  "external_instrument": str | None,   # R7's exact-as-named string on
                                        # EXTERNAL; None on INTERNAL
  "targets": [ {"pinpoint": str, "expanded_from": str | None}, ... ],
                                # [] on EXTERNAL (R7); one entry per
                                # expanded range/plural/or-list member
                                # on INTERNAL
  "hard_case_tags": [str, ...] # OPTIONAL — currently only
                                # ["ambiguous_reference"] (R6, or a
                                # relative reference resolved with no
                                # enclosing_unit)
}
```

Every metadata parameter is document-level, caller-supplied, exactly
like `host_instrument_number` already was for `article-v1` (§8a above) —
never a resolution-profile field:

* `enclosing_unit` — the pinpoint prefix ("Article 7", "§ 230") a
  RELATIVE reference ("paragraph 1", "point (a)", "subsection (b)")
  resolves against. The CALLER derives it from the source text (e.g. the
  nearest preceding numbered-heading before the clause's own offset) —
  this module never reads it from gold and never guesses past what is
  passed in; with none given, a relative reference resolves to its own
  bare suffix, flagged `ambiguous_reference`.
* `numbering_family` — `"eu"`/`"uk"`/`"us"`/`"de"`: which family's
  absolute-pinpoint grammar is tried first (every family's EXTERNAL and
  anaphora rules apply regardless, since any host document can still
  cite another family's instrument).
* `host_instrument_name` / `host_instrument_number` — the host's own
  name/number, for R1 (self-naming is INTERNAL) and R2 (a quoted-
  amending pinpoint that NAMES the host designates the host).
* `whole_host_unit` — the unit TYPE the file equals IN FULL, if any (R5).
* `preceding_text` / `quoted_amending_target` — anaphora antecedents and
  R2's "amended instrument" name for a bare pinpoint inside quoted text.

**R1-R7, mapped to behaviour:**

* **R1** (bare self-reference). "this Regulation/Act/Directive" is
  dropped — NOT an item. "this Article/paragraph/subparagraph", used
  deictically, is also dropped. "Article 6 of this Regulation" IS an
  item, INTERNAL, pinpoint `"Article 6"`. A citation giving the HOST's
  OWN number ("Article 45 of Regulation (EU) 2016/679", with
  `host_instrument_number="2016/679"`) is INTERNAL to the pinpoint, not
  external — the whole chain+host-name span is consumed as ONE
  reference so the host's own name is never ALSO reported as a second,
  standalone EXTERNAL mention.
* **R2** (quoted amending text, classified by what it DESIGNATES). A
  bare pinpoint inside quoted text that names NEITHER the host nor any
  other instrument is EXTERNAL to `quoted_amending_target` (the amended
  instrument the caller names). A pinpoint-bearing mention that NAMES
  the host (`host_instrument_name`) is INTERNAL, pinpoint `"Instrument"`
  (the host-instrument pinpoint format) — and a following "..., of that
  Regulation" chain stays INTERNAL to ITS OWN (more specific) pinpoint,
  never falling back to `"Instrument"` again. An EXPLICIT naming at the
  span itself — a pinpoint chain immediately followed by "of"/"to
  <instrument name>", optionally past one short, length-capped,
  one-level parenthetical gloss ("section 52B (data-sharing code) of
  the Example Statute 1990") — ALWAYS wins over whatever instrument a
  surrounding quote or unquoted chapeau context would otherwise supply;
  the mention list never overrides an explicit naming the text carries
  at that exact point FOR A SINGULAR chain ("section N of <name>"). A
  PLURAL/RANGED chain naming the host this same way ("Parts N to M of
  <host name>") does NOT yet get this same protection — see this
  section's own KNOWN LIMITS. An amendment's OLD (struck) quoted span — the
  quoted text immediately preceded by "for"/"omit" before the opening
  quote mark, the SAME quote-span machinery this paragraph already uses
  — excludes its own mentions as an antecedent for anaphora whose OWN
  POSITION lies OUTSIDE that span (the exclusion is position-relative,
  not global): the span is being
  replaced, not cited, from outside it. An anaphor found INSIDE the
  same OLD span instead resolves against the ordinary
  nearest-preceding-mention rule over mentions inside that span (and
  before it) — the struck text is read as ordinary prose from inside
  itself, even though it is never reachable as a live antecedent from
  outside it. A BARE mention (no pinpoint of its own) found inside
  that OLD span is not a reference item at all, while a pinpoint-bearing
  mention inside it still is. **Consequence for recall:** a BARE
  instrument mention inside struck (OLD) text is dropped silently — no
  EXTERNAL item is ever emitted for it — which LOWERS recall wherever a
  human annotator would mark that bare mention EXTERNAL in its own
  right; the rule trades that recall loss for never promoting a
  replaced span into a live citation.
* **R4** ("this Section/Chapter/Title/Part"). INTERNAL to the
  caller-derived `enclosing_unit` naming that larger unit (e.g. `"Part
  7, Chapter 2"`); with no `enclosing_unit` given, a bare capitalised
  word, flagged `ambiguous_reference`. "that Schedule"/"that Part"/
  "that Chapter" (a sub-unit word, not an instrument-level word)
  resolves against the NEAREST preceding mention of the SAME sub-unit
  word — never the nearest INTERNAL pinpoint of any kind. A trailing
  "of that Schedule" on a plural/ranged Part chain ("Parts 1 and 2 of
  that Schedule") is ONE reference, each member combined with the
  named Schedule's own number ("Schedule 3, Part 1"). **Known limit:**
  "Part 3" and "Schedule 3" in "See Part 3 of Schedule 3 and Parts 1
  and 2 of that Schedule." read as TWO separate pinpoints (no "<Part>
  of <Schedule>" combining chain for this word order); only the SECOND
  citation, via the sub-unit anaphora above, combines "Schedule 3" with
  "Part 1"/"Part 2".
* **R5** ("this <unit>" naming the WHOLE host). When `whole_host_unit`
  names the SAME unit type, R1 wins over R4 — dropped, not an item.
* **R6** ("So in original" footnotes). Resolved LITERALLY; every
  reference inside the footnote's own nearby span is flagged
  `ambiguous_reference` — never silently "corrected" to a probably
  -intended target.
* **R7** (EXTERNAL shape). `targets` is always `[]`. `external_instrument`
  is the instrument exactly as the text names it — no pinpoint, no
  gloss; the pinpoint stays in `literal`. "title N" (US Code) is mapped
  to its instrument name, `"N U.S.C."` (e.g. `"title 5"` ->
  `"5 U.S.C."`) — the ONE mapping this module performs on an
  otherwise-verbatim name.

**Numbering families covered:** EU (`Article N(M)`, `point (x)`,
subparagraph, `Annex`, `Chapter`/`Section`); generic `section N`/`s.
N`/`§ N`; DE `§ N Abs. M Satz K` (and `Nr. J`) — **vector-only: no
vertical's gold carries a DE item**, so these vectors are the ONLY
conformance check this family has; UK `Schedule M, paragraph N` /
`paragraph N of Schedule M` (reformatted outer-unit-first, per the
contract's own pinpoint-order rule), `Part N`, `Chapter N`; US
`subsection (a)(1)(A)`, `§ 6502(b)(1)`, `section 230(c)`, `this title`
(EXTERNAL, per the contract). Ranges ("Articles 15 to 20", "sections 3
to 5"), plurals and or-lists expand to one target per member, each
carrying `expanded_from` set to the citation's own literal. A bare
"Article N" (or any family's absolute chain) immediately followed by a
time-duration word ("Article 5 days") is a hard-negative decoy, never a
citation — matching `article-v1`'s own treatment of a continuation-list
decoy, now applied to the first number too. A named treaty's Title-Case
continuation stops before "and Article", "and Articles", "and Section",
"and Annex", "and Chapter", or "and Part" — "and" continues the treaty's
own name only when the following capitalised word is not itself one of
these pinpoint keywords, so a second, separate citation right after it
("... Article 5 of the Example Convention and Article 6 of the Example
Protocol ...") is never merged into the first treaty's own name.

**Anaphora — ONE ordered mention list.**
"that Regulation"/"that Directive"/"that Act"/"that title"/"such Act"/
"thereof" resolves through a SINGLE ordered list of instrument
MENTIONS, built over `preceding_text + text` (never scanned
separately per pass, never filtered). Each mention records its own
POSITION, its KIND (`_classify_instrument_kind`, the name's own HEAD
noun — "regulation"/"directive"/"act"/"title"/"treaty"/"other", the
FIRST instrument keyword not itself inside an "of"/"on"/"to"/
"implementing …" complement (see this section's own KNOWN LIMITS for
the one "<kind> YEAR" exception and five worked
examples) — never a caller-supplied type word matched by substring),
and whether it IS THE HOST:

* by NAME — a whitespace/NBSP-tolerant, word-boundaried match against
  `host_instrument_name`, exact (never a bare substring: a shorter
  host name is never treated as a PREFIX match of a longer, different
  instrument's name); or
* by NUMBER — `host_instrument_number` found in the mention's own name
  on TOKEN boundaries ("2016/6790" is never "2016/679") AND the
  mention's own KIND equals the host's KIND ("Directive 2016/679" is
  never "Regulation (EU) 2016/679", even sharing the number).

Host mentions are NEVER removed from the list — they compete on
RECENCY exactly like any other mention. An anaphor takes the NEAREST
PRECEDING mention of the matching KIND (or any kind, for the untyped
"thereof"): the host -> INTERNAL, with the pinpoint resolved IN the
host (the chain's own pinpoint when the anaphor carries one — "section
5 of that Act" — or, for a BARE anaphor with no pinpoint of its own,
NO ITEM AT ALL, R1's bare-self-reference rule, never an INTERNAL echo
of an unrelated earlier pinpoint); another instrument -> EXTERNAL to
that instrument; no mention of the matching kind at all -> EXTERNAL
"unnamed (see note)". A PINPOINT-BEARING anaphora ("Parts 5 to 7 of
that Act") is never the BARE, no-pinpoint-of-its-own case R1 drops
entirely — it is consumed into the same reference and always emitted
as an item (INTERNAL to the host, or EXTERNAL "unnamed (see note)"
when the nearest same-kind mention is not the host), whether or not
the nearest mention of that type is the host. The untyped "thereof"/
"thereto" lookup additionally scans, as a mention, an EXTERNAL
reference this SAME call has already emitted into its own output —
not only a bare instrument name in `preceding_text + text` — so a
treaty only reachable through a pinpoint-gated chain match ("Article
12 of the Example Convention on Cybercrime") still serves as "thereof"'s
antecedent later in the same text; a TYPED lookup ("that Directive")
is unaffected by this widening. The EU preamble convention "Having
regard to <Treaty NAME>, and in particular Article N thereof," names
the treaty with no pinpoint of its own; "thereof" resolves to that
SAME recital's named treaty, never to the host, even though the bare
mention carries no pinpoint by itself — this is narrower than the
general bare-treaty-name exclusion below (gated on the fixed phrase
"Having regard to", not a general relaxation of it). A nested "Chapter
M of Part N" chain claims a trailing named external instrument ("...
of the Example Companies Act 2015") the same way the bare Part/Chapter
form already does, as one EXTERNAL reference spanning the whole
nested chain plus the instrument's name.

This REPLACES an earlier approach that filtered host self-namings OUT
of a separate "external candidate" list before an anaphor's lookup
ran. That mechanism only ever relabelled the HOST's own filtered-out
occurrence; every OTHER anaphor that fell back PAST a removed host
mention still landed on whichever OTHER instrument happened to be
named earlier in the text — a sweep over the 12-source corpus found 61
references relabelled to a wrong, unrelated instrument, and 20 given
the wrong KIND (EXTERNAL where INTERNAL was correct, or vice versa).
The ONE ordered mention list has no separate "candidate list" to
filter at all, closing this class of bug at the mechanism level
rather than patching each symptom.

**`+1 structural` and `cross_references` links — THROUGH THE PIPELINE,
on BOTH arms.** `clause_cue_contributions` and
`cross_reference_links` both dispatch on a `xref_resolver` keyword
(`"article-v1"` default) via one shared seam, `_xref_count_and_objects`.
`"article-v1"` calls `cross_reference_targets` exactly as before —
BYTE-IDENTICAL `+1 structural`-per-target count and link objects for
every existing document/vector, regardless of whether a resolution
profile even carries the new field. `"shared-v2"` calls
`resolve_references` instead and derives the SAME two things from its
richer output: an INTERNAL reference contributes `+1 structural` AND one
`cross_references` link PER target pinpoint (`o = "Article 7(1), point
(b)"`, etc., same shape as `article-v1`'s own `"Article <n>"` link); an
EXTERNAL reference contributes `+1 structural` and ONE link whose object
is `"<instrument>|<external_target>"` — e.g., for "Article 9, paragraph
4, of Directive 2011/83/EU", `"Directive 2011/83/EU|Article 9(4)"` (the
PARSED pinpoint, R7's own `external_target`, not the raw literal) — so
an external citation is now visible as a link AND as a structural count
too. `article-v1` does NOT recognise this comma-pinpoint-chain shape as
EXTERNAL at all: it emits `{"o": "Article 9", ...}`, treating the
citation as if it were an internal "Article 9" of its own numbering,
losing both the external instrument and the sub-pinpoint. This
reaches `combined_contributions`/`clause_cue_point` as well (they thread
the same `xref_resolver` keyword straight through to
`clause_cue_contributions`), so the §11 POINT itself differs between the
two resolvers on a document that carries citations `article-v1` cannot
see — this is the INTENDED effect of the profile field selecting a
resolver, not a side channel around it. `xref_resolver` ITSELF is
CALLER-THREADED from the resolved profile (exactly like
`relational_suppression_scale` already is) — two convenience wrappers,
`clause_cue_point_from_profile`/`cross_reference_links_from_profile`,
unpack a profile DOCUMENT directly, mirroring
`five_d_nd.match.combine_scores_from_profile`'s own shape. The
pinpoint-free `external_instrument` string alone (R7) remains what is
GOLD-SCORED; the link's own object string is checked by conformance
vectors and a spot-check only, never reported as a gold P/R.

**Enclosing-unit derivation is PART of this module** —
`enclosing_unit_at(source_text, offset, numbering_family)`. A
pure function of exactly those three inputs: the nearest preceding
numbered-unit heading in `source_text` strictly BEFORE `offset`, or
`None` when none is found. `"eu"`: the nearest preceding standalone
`"Article N"` heading LINE. `"us"`: the nearest preceding `"§N."`
marker. `"uk"`: the nearest preceding ALL-CAPS `"SCHEDULE N"`/`"PART
N"`/`"CHAPTER N"` heading — a GENERAL pattern verified directly against
the UK verticals' own source text (legislation.gov.uk plain-text dumps
reliably distinguish an outer-unit HEADING, all-caps, from an ordinary
mixed-case body-text REFERENCE to the same unit, "SCHEDULE 1" vs.
"Schedule 1"); an ORDINARY SECTION-level heading is NOT detected (the
UK layout sandwiches the bare section number between a repeated
section-title phrase and the section's own first substantive word —
e.g., in a flattened dump, a running header repeats a section's own
title immediately before its bare number, which then runs straight
into the section's first substantive sentence with no separating
markup — no general, low-false-positive pattern for "the digit run
that IS this marker, not a date or a cross-reference" was found over
that flattened layout; left `None` rather than guessed at). `"de"`: not
attempted (no DE gold; vector-only). The benchmark harness now calls
THIS function (both arms share the identical implementation) rather than
carrying its own copy, closing the earlier "lives outside the versioned
change" finding.

**R2's quoted-amending-text span is SELF-DETECTED.**
`resolve_references` finds quote SPANS in `text` itself — EU
drafting's single curly quotes (`‘…’`, straight `'` as a fallback);
UK/US drafting's double curly quotes (`"…"`, straight `"` as a
fallback) — and classifies a bare pinpoint found STRICTLY INSIDE one of
these spans by DESIGNATION, per R2: if it names the host
(`host_instrument_name`, passes 0-2, unaffected by quoting at all) it
stays INTERNAL; otherwise it is EXTERNAL to whichever instrument was
named most recently BEFORE the quote's own opening mark (reusing the
SAME nearest-antecedent lookup "thereof" already uses) — covering BOTH
directions the contract names (a quoted pinpoint naming the host stays
internal; a quoted BARE pinpoint, naming neither the host nor anything
else, goes external to the amended instrument named in the surrounding
chapeau). `quoted_amending_target` is kept ONLY as an explicit override
for a caller that wants to force the designation on text with no actual
quote marks (e.g. a pre-segmented clause that already had its quotes
stripped) — the PRIMARY mechanism is the resolver's own quote-span
detection, never a caller flag nobody is obliged to supply.

**KNOWN LIMITS** (stated, not hidden):

* **Beyond the ONE-ordered-mention-list anaphora mechanism above**:
  the host's own flexible NAME match now
  carries a trailing word-boundary assertion (a host number is never
  matched as a bare prefix of a longer, different number); "Article N
  GDPR" (bare, no "of") is no item at all rather than a wrong-kind
  INTERNAL pinpoint (bare "GDPR" stays an under-recall gap, per the
  bullet below); a short-year-only Act name ("the 1998 Act") is
  pinpoint-gated EXTERNAL, UNLESS the year equals
  `host_instrument_number` ("Section 5 of the 2018 Act" resolves
  INTERNAL with its own pinpoint when the host's own number is "2018";
  a different year stays EXTERNAL as before) — or equals the host's
  own short year DERIVED from `host_instrument_name` when the caller
  passes no `host_instrument_number` at all: when `host_instrument_name`
  ends "... Act YYYY",
  the resolver derives YYYY as the host's short year for THIS rule
  ONLY; that derived value is never written back into
  `host_instrument_number` itself, which keeps its own narrower
  meaning (gating the EU NUMBER-shaped host-mention match elsewhere in
  this section); "Treaty
  establishing …" joined the NAMED-
  treaty keyword set; a trailing ordinal suffix ("second sentence") and
  the EU "Article N, paragraph M[, subparagraph][, point]" comma-chain
  each resolve as ONE reference with their own "of <host/other>" wrap;
  "Parts N to M" (previously singular-only) and sibling-subsection
  or-lists ("section N(x) or (y)") each expand to one target per
  member; a statutory instrument whose own name EXTENDS the host's
  name ("the <host Act> (Commencement No. M) Regulations <year>") is
  EXTERNAL, never INTERNAL merely because it starts with the host's
  own name; and a BARE anaphor with no pinpoint of its own, resolving
  to the host, is R1's bare self-reference (no item), never an
  INTERNAL echo of an unrelated earlier pinpoint.
* The comma-year drafting allowance
  ("Act, 1921") is attested ONLY for "Act" — `_EXT_ACT_WITH_YEAR`
  restricted it to that one keyword, so a page-header line such as
  "United States Code, 2022 Edition" is no longer read as naming an
  EXTERNAL "Code"; every other statute-kind word (Code/Ordinance/
  Statute/Law/Convention/Treaty) keeps only the pre-existing "of YYYY"
  convention. `_section_plural_range_groups` now walks EVERY written
  token (list member or range) and fully expands EVERY range token to
  its implied members before grouping into contiguous same-status
  runs — any number of in-file/out-of-file switches inside one range
  ("sections 6501 through 6504" against `{6501, 6503}` splits into
  four runs: 6501 in, 6502 out, 6503 in, 6504 out), and a range member
  INSIDE a list ("sections 6501 to 6505 and 45") is expanded the same
  way rather than collapsed to its two written endpoints. A run that
  is its own token's one-and-only run, or that token's LAST run, keeps
  that token's own written literal span; an INTERIOR run with no
  written anchor of its own (a second-or-later status flip strictly
  inside one range token) is reported at a SYNTHETIC ZERO-WIDTH
  position — its token's own start offset, `literal: ""` — carrying
  every member that run holds in its own `targets`/`external_target`
  either way; no member is ever dropped, only its `literal` span is
  synthetic. "through" now works as BOTH the `SECTION_PLURAL` list
  connector (so "section 100 through 105" is recognised as one plural
  match at all) and a range word (so 101-104 are fully expanded, not
  dropped) — the same keyword in two different roles, each checked by
  its own constant. `_classify_instrument_kind`'s head-noun rule: the
  head is the FIRST instrument keyword in the name that is not itself inside an "of"/"on"/"to"/
  "implementing …" complement, with ONE narrow exception — an "of"
  complement that is ITSELF shaped like a complete title ending in
  "<kind> YEAR" promotes that trailing keyword instead (the real UK
  convention a name like this follows: "Regulation of Investigatory
  Powers" is the Act's own subject-matter title, not a second,
  competing instrument name). Five examples, each run through
  `_classify_instrument_kind` directly: "Convention on the Law of the
  Sea" -> `treaty` (the LATER "of" belongs to "the Law of the Sea", a
  complement of "Convention", never a second keyword occurrence that
  wins); "Protocol to the Children Act 1989" -> `treaty` (the "to"
  complement ends in "Act 1989", but a `to` complement never overrides
  the first keyword); "Regulation (EU) 2016/679 implementing Directive
  95/46/EC" -> `regulation` (an "implementing" complement never
  overrides the first keyword either); "Recommendation on the
  Protocol" -> `recommendation` (an "on" complement, same rule);
  "Regulation of Investigatory Powers Act 2000" -> `act` (the ONE
  exception: the "of" complement "Investigatory Powers Act 2000" is
  itself a complete "<kind> YEAR" title, so its trailing "Act" is
  promoted over the leading "Regulation").
* `enclosing_unit_at`'s own UK section-level heading gap, above — the
  biggest remaining lever for held-out recall on `uk-dpa2018`/
  `uk-osa2023`.
* External-instrument NAME recognition is a closed set of drafting
  SHAPES (EU Regulation/Directive/Recommendation numbers, TFEU/TEU/
  Charter, a NAMED Convention/Protocol/Accord — "European Convention
  for the Protection of Human Rights and Fundamental Freedoms",
  "Protocol No 21" — "the X Act YYYY" and its sibling statute-kind
  words, "title N" U.S.C., "UK GDPR", the German statute/EU-act
  shapes) — an instrument named in a shape outside this set is USUALLY
  not recognised as EXTERNAL at all (under-recall, not a wrong name),
  but **this is not a universal guarantee.** A WRONG external name (as
  opposed to a merely MISSED one) is known to occur under these
  conditions — the first still open, the others documented separately
  below in their own bullets: (a) a German qualifying-phrase
  continuation absorbing a following finite-verb predicate into the
  name, this bullet; (b) a "Protocol to the <Act Name> <year>"
  continuation losing its own trailing year (the run-on-names bullet
  further below). Beyond (a)/(b), measured directly against the
  current HEAD: (ii) a name beginning with a lower-case or connector
  word gets truncated to the portion after it, with the chain's own
  leading pinpoint reported as a separate, disconnected bare INTERNAL
  reference. Constructed: `resolve_references("Section 4 of the
  Representation of the Example Act 1983 applies.")` at HEAD returns
  TWO references — "Section 4" bare INTERNAL (no instrument attached)
  and a separate EXTERNAL reference, `external_instrument: "the
  Example Act 1983"` — "Representation of" is dropped from the name
  entirely (the same truncation occurs, run directly, for "the
  Promotion of the Example Act 1983" and "the Prevention of the
  Example Act 1983"). (iii) the Title-Case continuation's "and" stop
  (see below) is a NARROW, closed list — only "and
  Article"/"and Articles"/"and Section"/"and Annex"/"and Chapter"/"and
  Part" stop it; every OTHER capitalised continuation word after "and"
  is still absorbed into the first treaty's own name — this condition
  is narrowed, not closed. Constructed, each
  run directly: `resolve_references("Article 5 of the Example
  Convention and Title II of the Example Protocol apply.")` at HEAD
  resolves ONE EXTERNAL reference, `external_instrument: "Example
  Convention and Title II of the Example Protocol"` ("and Title" is
  absorbed); "and Annexes II of the Example Protocol" gives "Example
  Convention and Annexes II of the Example Protocol"; "and Regulation
  2020/1 of the Example Protocol" gives "Example Convention and
  Regulation"; "and Member States of the Example Protocol" gives
  "Example Convention and Member States of the Example Protocol" — all
  four absorbed into one wrong, merged name rather than split into two
  references. (iv) a bare pinpoint naming a RECOGNISED external shape
  ("Article 82 of the GDPR") found INSIDE a quoted substitution's NEW
  text takes the surrounding chapeau's own Act instead of the name it
  actually carries. Constructed: `resolve_references('In section 5 of
  the Example Other Act 1990, for "x" substitute "see Article 82 of
  the GDPR for further detail.".', host_instrument_name="Example
  Protection Act 2020", numbering_family="uk")` at HEAD resolves
  "Article 82" EXTERNAL to `"the Example Other Act 1990"` (the
  chapeau's Act) — "of the GDPR" is dropped from both the literal and
  the resolution entirely. (v) a bare pinpoint in the amendment's
  INSERTED (NEW) quoted text takes the Act named in the amendment's own
  OLD (struck) text, when no `quoted_amending_target` is passed — R2
  expects the NEW text's bare pinpoint to resolve against the amended
  instrument, not the OLD text's own Act. Constructed:
  `resolve_references('for "section 9 of the Example Data Act 1990"
  substitute "section 9".', numbering_family="uk")` at HEAD resolves
  the NEW text's "section 9" EXTERNAL to `"Example Data Act 1990"` —
  the OLD (struck) span's own Act — because the self-detected
  antecedent lookup finds the nearest PRECEDING named instrument before
  the NEW quote's own opening mark, which is the OLD span's Act;
  passing `quoted_amending_target="Example Protection Act 2020"`
  explicitly overrides this and resolves the NEW text's "section 9"
  correctly, to that target. (vi) an INLINE-DEFINED short form of a
  NON-HOST Act gets the truncated label instead of the FULL name the
  surrounding text just defined it as — this happens WHETHER OR NOT
  host metadata reaches the derivation at all, as long as the short
  form's own year differs from the host's own derived/supplied short
  year. Constructed, host metadata present:
  `resolve_references('The Example Data Act 1990 (the "1990 Act")
  governs retention. Section 4 of the 1990 Act applies.',
  host_instrument_name="Example Protection Act 2020",
  numbering_family="uk")` at HEAD resolves the first mention EXTERNAL
  to `"The Example Data Act 1990"` (correct) and "Section 4 of the
  1990 Act" EXTERNAL to `"1990 Act"` — the truncated short form, not
  the full name the text defined three words earlier; the identical
  truncation occurs with NO host metadata passed at all. **Opposite
  risk: a NON-host Act whose short form shares the SAME year as the
  host resolves INTERNAL instead.** Constructed: `resolve_references('The
  Example Other Act 2020 (the "2020 Act") governs retention. Section 4
  of the 2020 Act applies.', host_instrument_name="Example Protection
  Act 2020", numbering_family="uk")` at HEAD resolves the first mention
  EXTERNAL to `"The Example Other Act 2020"` (correct), but "Section 4
  of the 2020 Act" resolves INTERNAL with pinpoint `"section 4"` — the
  short-year rule matches the host's own derived year against ANY Act
  sharing that year, not only the host itself. **A host name written
  with a comma ("Example Protection Act, 2020") or a trailing chapter
  citation ("Example Protection Act 2020 (c. 12)") derives NO year at
  all** — the derivation anchors on "... Act YYYY" at the EXACT end of
  `host_instrument_name`; either suffix breaks that anchor, so a
  short-year Act reference against such a host always stays EXTERNAL,
  truncated, under neither risk above. Constructed, each run directly:
  `resolve_references("Section 4 of the 2020 Act applies.",
  host_instrument_name="Example Protection Act, 2020",
  numbering_family="uk")` and the same text with
  `host_instrument_name="Example Protection Act 2020 (c. 12)"` both
  resolve EXTERNAL to `"2020 Act"` at HEAD — the NAME alone derives no
  year in either case. **This is a NAME-derivation gap only, not a gap
  in the short-year rule itself:** when the CALLER
  passes `host_instrument_number` explicitly, the short-year rule reads
  that value directly and never attempts the name-ending derivation at
  all, so the short form DOES resolve INTERNAL — for BOTH host-name
  shapes above. Constructed, each run directly: `resolve_references(
  "Section 4 of the 2020 Act applies.", host_instrument_name="Example
  Protection Act, 2020", host_instrument_number="2020",
  numbering_family="uk")` and the same text with `host_instrument_name
  ="Example Protection Act 2020 (c. 12)"` and the same
  `host_instrument_number="2020"` both resolve INTERNAL with pinpoint
  `"section 4"` at HEAD. This claim is false as stated, under a
  condition NARROWED, not closed — see (iii) above. **German name
  over-extension through a finite verb.** The
  qualifying-phrase continuation after "über"/"gegen" (`_DE_PHRASE_WORD`)
  accepts up to 3 lower-case words immediately followed by a
  capitalised (German-noun) word, to admit genuine adjective/genitive
  runs ("öffentlicher Aufträge") — but German also capitalises every
  common noun, so a finite verb plus a pronoun immediately followed by
  a capitalised noun OBJECT fits the same shape. "Artikel 101 des
  Vertrags über die Arbeitsweise der Europäischen Union finden keine
  Anwendung." (constructed) resolves `external_instrument: "Vertrag
  über die Arbeitsweise der Europäischen Union finden keine
  Anwendung"` at HEAD — the predicate "finden keine Anwendung" ("do not
  apply") is absorbed into the name, a WRONG name, not under-recall.
  **The second, previously-open condition (item (iii) above) is
  narrowed, but not closed** — a treaty name's Title-Case continuation
  now stops before "and
  Article", "and Articles", "and Section", "and Annex", "and Chapter",
  or "and Part" (see the numbering-families paragraph above): "Article
  6 of the Example Cooperation Convention and Article 7 of the Example
  Transit Convention apply." (constructed) resolves at HEAD to TWO
  separate EXTERNAL references, one per treaty, rather than merging the
  second citation into the first treaty's own name. An earlier,
  different breach of this claim is also corrected: a bare, UNNAMED
  "Convention"/"Protocol"/"Accord" — added (§20a.2 item 80) on the
  theory that ANY bare
  occurrence of these words was a citation — fired on ordinary prose
  ("Convention rights", "Transmission Control Protocol/Internet
  Protocol", "Refugee Convention") and truncated genuinely named
  treaties ("European Convention for the Protection of Human Rights
  and Fundamental Freedoms" -> "Convention"; "Protocol No 21" ->
  "Protocol") to their bare generic type word — a WRONG name, not
  under-recall. That alternative is REMOVED; a treaty-type word is now
  EXTERNAL only when (a) it is part of a genuinely NAMED instrument —
  a Title-Case qualifying phrase attached to the keyword — (b) it is
  "Protocol No N" (the EU drafting convention's own numbered-instance
  form), or (c) it is "Article N of this/the Convention/Protocol/
  Treaty/Accord" with a pinpoint EXPLICITLY attached, resolved R1
  -style against the host when the host genuinely IS that treaty type,
  else `external_instrument: "unnamed (see note)"` (R7) — never a bare
  truncated type word. Measured directly over all 12 benchmark source
  texts (`_results/xref-resolver/harness/`, the 8 signed verticals plus
  eprivacy/us-cfaa/de-bdsg/de-tdddg): 0 EXTERNAL names are a single
  generic word ("Act"/"Convention"/"Protocol"/"Gesetz"/"Verordnung"/
  "Ordnung"/"Vertrag") after this fix, down from 94 before it (80
  bare "Convention"/"Protocol" hits across gdpr (3), ai-act (5),
  us-coppa (5), uk-dpa2018 (57), uk-osa2023 (6) and eprivacy (4) that
  the bare alternative introduced, plus 14 bare German
  "des Gesetzes"/"der Ordnung" false fires (de-bdsg 7, de-tdddg 7)
  that the German naming patterns' own missing word-boundary and
  empty-stem guards let through — the ordinary-prose false fires
  were present independently of the Convention/Protocol/Accord
  breach above and are fixed by the SAME change; measured directly,
  before and after, over all 12 source texts).
* The quote-span detector (F3c) is a SIMPLE matching-quote-mark scan —
  it does not track NESTED quotes of the same style, and a
  quotation spanning MULTIPLE sentences (rare; amending text is usually
  one paragraph) would need `text` to include all of it.
* A relative reference combining a NUMBER list AND a point/letter list
  in the SAME citation ("Article 5(3), points (c) to (f)") resolves to
  the number only, ONE target — the cross-product expansion (one target
  per `(number, point)` pair) is not implemented.
* **A Schedule's own Chapter level is NOT reset when a new PART starts
  inside that Schedule** (`enclosing_units_at`'s "uk" branch: a new
  top-level PART resets `main` to a fresh dict, but a PART heading
  found WHILE `in_schedule` only adds/overwrites the `"part"` key of
  `schedule_state`, never clearing a stale `"chapter"` carried over
  from an earlier Part of the SAME Schedule). Constructed source text
  `"SCHEDULE 3\nPART 1\nCHAPTER 2\n...\nPART 2\n..."`, offset inside
  "PART 2"'s own body: `enclosing_units_at(text, offset, "uk")` returns
  `{"schedule": "Schedule 3", "part": "Part 2", "chapter": "Chapter
  2"}` at HEAD — "Chapter 2" belongs to "Part 1", not "Part 2", and is
  stale.
* **"such Directive"/"that Protocol"/"that Treaty" with NO antecedent
  instrument of the matching kind in the text** do not fail the same
  way. Constructed: `resolve_references("Article 4 of such Directive
  applies.")` at HEAD returns TWO references — "Article 4" wrongly
  INTERNAL (split off from its own "of such Directive"), plus a
  separate "such Directive" EXTERNAL `"unnamed (see note)"`, tagged
  `ambiguous_reference`. `resolve_references("Article 4 of that
  Protocol applies.")` at HEAD returns only ONE reference, "Article 4"
  INTERNAL — the "of that Protocol" external reference is DROPPED
  entirely, not even emitted as ambiguous; "that Treaty" behaves the
  same way as "that Protocol" (the "of that Treaty" tail is dropped,
  not even with an earlier same-kind antecedent present, since "Treaty"
  is not one of the typed anaphora keywords this mechanism recognises
  at all — only "that Regulation"/"that Directive"/"that Act"/"that
  title"/"such Act"/"thereof" are). Neither shape has a dedicated
  antecedent-free path. **"the said Act"** (the traditional
  UK drafting synonym for "that Act") is not a recognised anaphora
  keyword at all: `resolve_references("The Example Act 1990 governs
  this. Section 4 of the said Act applies.", host_instrument_name="Other
  Act 2000", numbering_family="uk")` at HEAD returns "Section 4" bare
  INTERNAL with its own pinpoint — the "of the said Act" tail is not
  parsed as an anaphoric trailer at all, so the citation never picks up
  any instrument affiliation, right or wrong.
* **A plain "N U.S.C. M" citation does not count as a designation
  event for a LATER "that title".** Constructed:
  `resolve_references("Nothing in 15 U.S.C. 45 limits the authority
  under that title.", numbering_family="us")` at HEAD resolves "that
  title" to `external_instrument: "unnamed (see note)"`
  (`ambiguous_reference`) rather than to "15 U.S.C." — the bare
  "N U.S.C. M" shape is not tracked as an antecedent the way a named
  EU/UK instrument is.
* **List markers are kept verbatim in the reference's own `literal`
  span, by design (R7)** — only `external_instrument` strips a leading
  list marker. `resolve_references("This is amended by (b) The
  Consumer Rights Act 2015.", numbering_family="uk")` at HEAD returns
  `literal: "(b) The Consumer Rights Act 2015"` (marker kept) but
  `external_instrument: "The Consumer Rights Act 2015"` (marker
  stripped) — see
  `conformance/vectors/clause-cues/xref-v2-minor-leading-list-marker-stripped-from-name.json`.
* **Super-linear time on thousands of repeated host-name/heading
  citations.** `enclosing_unit_at`/`enclosing_units_at` each re-scan
  `source_text` from its own start on EVERY call (no memoised
  heading-position index) — each call is O(n) in the LENGTH of
  `source_text`, so a caller invoking either once per citation over a
  file with n characters and k citations pays O(n·k) total. Measured
  directly: a synthetic EU source of n "Article N" headings, called
  once at the LAST heading's own offset, scales roughly LINEARLY in n
  (n=1000: ~0.28 ms/call; n=2000: ~0.54 ms/call; n=4000: ~1.0 ms/call;
  n=8000: ~1.9 ms/call) — confirming the O(n·k) bound stated in
  §20a.2's own KNOWN LIMIT; not optimised (no caching/bisect index
  added).
* **Pre-existing: a recognised instrument's SHORT NAME, used inside a
  DIFFERENT host that does not itself carry that short name, resolves
  INTERNAL.** Constructed: `resolve_references("Article 4 of the GDPR
  applies for the purposes of this Act.", host_instrument_name="Data
  Protection Act 2018", numbering_family="uk")` at HEAD returns ONE
  reference, "Article 4" INTERNAL, `external_instrument: null` — "of
  the GDPR" is dropped from the literal and from the resolution
  entirely; "UK GDPR" is a recognised external shape, but bare "GDPR"
  on its own (as distinct from "UK GDPR") is not.
* **Pre-existing: a multi-level TFEU tail does not propagate EXTERNAL
  to every member of a preceding plural/"or" list.** Constructed:
  `resolve_references("Chapter 4 or Chapter 5 of Title V of Part Three
  of the TFEU applies.")` at HEAD returns THREE references — "Chapter
  4" INTERNAL, "Chapter 5" INTERNAL, and a separate bare "TFEU"
  EXTERNAL mention with no pinpoint — rather than two EXTERNAL
  references to TFEU with "Chapter 4"/"Chapter 5" as their own
  `external_target`s.
* **Pre-existing: a bare self-naming of the host OUTSIDE any quote
  span, with no further pinpoint chain, emits `pinpoint: "Instrument"`**
  rather than omitting a target. See
  `conformance/vectors/clause-cues/xref-v2-r2-quoted-host-name-is-internal.json`
  for a worked example (`"Regulation (EU) <n> of the European
  Parliament and of the Council"`, no pinpoint chain attached, resolves
  INTERNAL with `targets: [{"pinpoint": "Instrument", ...}]`).
* **"that section" after an absolute "section N of the <year> Act"
  chain does not inherit the named Act — it is read as a RELATIVE
  reference against `enclosing_unit` instead.** Constructed:
  `resolve_references("Section 12 of the 1990 Act applies. That section
  is further explained below.", numbering_family="uk")` at HEAD returns
  "Section 12 of the 1990 Act" EXTERNAL (correct), then "That section"
  INTERNAL with `pinpoint: "Section"`, tagged `ambiguous_reference` —
  the wrong KIND (should be EXTERNAL to "1990 Act") and the wrong
  pinpoint (bare "Section", not "section 12"); R4's relative-reference
  path, not the typed-anaphora mechanism, claims "that section" first.
* **A pinpoint chain immediately before a statutory instrument whose
  own name extends the host's name loses its own pinpoint.** Constructed:
  `resolve_references("Regulation 2 of the Example Act 2023
  (Commencement No. 2) Regulations 2024 applies.",
  host_instrument_name="Example Act 2023", numbering_family="uk")` at
  HEAD returns ONE reference, EXTERNAL to "the Example Act 2023
  (Commencement No. 2) Regulations 2024" (the instrument name itself is
  correctly recognised, per the addition above), but
  `external_target: null` and `literal` starting only at "the Example
  Act..." — the leading "Regulation 2 of" pinpoint is dropped from both
  the literal span and the resolution entirely.
* **A PLURAL/RANGED chain explicitly naming the host inside amending
  text does not get the EXPLICIT-naming-wins protection R2 gives a
  SINGULAR chain ("section N of <name>") — it falls back to some OTHER
  instrument instead of the host, but NOT always the SAME other
  instrument.** Measured directly over the UK DPA 2018 benchmark source
  (`_results/xref-resolver/harness/`): the "host-literal-but-other-
  label" count — an EXTERNAL reference whose `literal` names the host
  by its own full name, but whose `external_instrument` is some OTHER
  instrument — is 7, every one inside a consequential-amendment
  schedule's REPLACEMENT quoted text naming the host by a plural/ranged
  chain. The chapeau before that quoted text MAY OR MAY NOT itself name
  an Act — an earlier wording's "immediately after a chapeau naming
  the Act being amended" overstated this: four of the 7 rows have a
  chapeau that names no Act at all; in
  those rows, the Act in play instead comes from an earlier sentence
  announcing that an Act is being amended, or from whichever Act was
  last named before that point). Of the 7 rows, the chapeau names an
  Act in 3 and names none in the other 4. By label: 3 rows carry the
  nearest earlier non-struck Act — in 2 of them that is the Act the
  chapeau names, in 1 it is the Act announced by an earlier sentence
  stating that an Act is amended as follows, because that row's
  chapeau names none — and 4 rows carry the struck text's own Act. (The
  struck-text-labelled rows are 4 in total either way: 2 reach it
  through (b) alone, 1 through (b)+(c) together, 1 through (c) alone.)
  (a) BARE-mention exclusion (nearest-earlier-Act label). A BARE Act mention in
  the struck (OLD) text — no pinpoint chain of its own — is excluded
  from the anaphora lookup entirely (R2, above), so the plural
  host-chain falls through to the nearest EARLIER non-struck Act
  mention instead. That is usually the chapeau's own Act, when the
  chapeau names one; when it does not, it is whatever Act was named
  before the struck span, by ordinary position. Constructed, the
  a struck text that is itself a BARE Act
  mention: `resolve_references('In section 5 of the Example Other Act
  1990, for "the Example Data Act 1990" substitute "Parts 5 to 7 of the
  Example Protection Act 2020".', host_instrument_name="Example
  Protection Act 2020", numbering_family="uk")` at HEAD returns the
  plural chain EXTERNAL to `"the Example Other Act 1990"` — the
  CHAPEAU's own Act, not the host the chain's own literal explicitly
  names, and not the struck text's own Act ("the Example Data Act
  1990") either, since that struck mention is bare — while the SAME
  construct with a SINGULAR chain ("section 7 of the Example Protection
  Act 2020") correctly resolves INTERNAL. A trailing pinpoint-carried
  anaphora on the SAME struck text still resolves to the host
  correctly: `resolve_references('In section 5 of the Example Other Act
  1990, for "the Example Data Act 1990" substitute "Parts 5 to 7 of the
  Example Protection Act 2020 (see paragraph 9 of that Act)".',
  host_instrument_name="Example Protection Act 2020",
  numbering_family="uk")` at HEAD resolves "paragraph 9 of that Act"
  INTERNAL with pinpoint `"paragraph 9"`. (b) PINPOINT-carried struck
  Act (struck-text-labelled). A struck Act carried by a PINPOINT chain
  is NOT excluded from the anaphora lookup — only a BARE mention is,
  per (a) above — so the plural host-chain picks up the STRUCK TEXT's
  own Act instead of the host it actually names. Constructed: `resolve_
  references('for "section 1 of the Example Data Act 1990" substitute
  "Parts 5 to 7 of the Example Protection Act 2020 apply.".',
  host_instrument_name="Example Protection Act 2020",
  numbering_family="uk")` at HEAD returns the plural chain EXTERNAL to
  `"Example Data Act 1990"` — the OLD (struck) text's own Act, a
  DIFFERENT wrong label from (a)'s. (c) Sentence-splitting (a
  CALLER-segmentation effect, not a resolver defect). When the struck
  text is immediately followed by a chapter citation such as "(c.
  29)", a caller's sentence splitter that breaks the text right after
  "(c." (misreading the abbreviation period as a sentence boundary)
  pushes the struck quote's own opening AND closing marks entirely into
  the half the caller passes as `preceding_text`. `resolve_references`'s
  own OLD-span detector scans ONLY `text`, never `preceding_text` — so
  from inside THIS call the struck quote is not recognised as struck AT
  ALL, and its Act becomes an ordinary, unexcluded mention: the
  nearest-antecedent lookup picks it up as if it had never been struck,
  and the row gets the struck text's own label even though the struck
  mention is itself BARE (mechanism (a)'s own exclusion never runs,
  because there is no complete quote left in `text` to classify as
  struck in the first place). This depends on the CALLER's own
  segmentation, not on anything `resolve_references` does differently —
  the same underlying sentence resolves two different ways depending on
  where the caller cuts it. Constructed, run directly, both halves of
  the SAME sentence: UNDIVIDED — `resolve_references('In section 9 of
  the Example Other Act 1990, for "the Example Data Act 1990" (c. 29)
  substitute "Parts 5 to 7 of the Example Protection Act 2020".',
  host_instrument_name="Example Protection Act 2020",
  numbering_family="uk")` at HEAD resolves the plural chain EXTERNAL to
  `"the Example Other Act 1990"` — the chapeau's own Act, mechanism (a),
  since the struck mention is bare and no split has happened. SPLIT —
  calling `resolve_references` on the SECOND half as `text`, with the
  FIRST half (ending in "(c.") as `preceding_text`: `resolve_references(
  ' 29) substitute "Parts 5 to 7 of the Example Protection Act 2020".',
  preceding_text='In section 9 of the Example Other Act 1990, for "the
  Example Data Act 1990" (c.', host_instrument_name="Example Protection
  Act 2020", numbering_family="uk")` at HEAD resolves the SAME plural
  chain EXTERNAL to `"the Example Data Act 1990"` instead — the STRUCK
  TEXT's own Act, mechanism (c) — purely because the caller split the
  sentence at that point; nothing in `resolve_references` itself
  changed between the two calls. (d) A related bug fires on the
  "paragraphs N and M of Schedule K to <host>" shape, not only "Parts N
  to M of <host>" — here the struck text names no Act at all, yet the
  output still carries the chapeau's own label, and it additionally
  SPLITS the pinpoint from the host-naming "to <host>" tail into two
  separate references rather than keeping them together. Constructed: `resolve_
  references('In section 9 of the Example Other Act 1990, for "x"
  substitute "paragraphs 3 and 4 of Schedule 2 to the Example
  Protection Act 2020 apply.".', host_instrument_name="Example
  Protection Act 2020", numbering_family="uk")` at HEAD returns TWO
  EXTERNAL references, both labelled `"the Example Other Act 1990"`
  (the chapeau's Act): "paragraphs 3 and 4" and, separately, "Schedule 2
  to the Example Protection Act 2020" — the "paragraph ... of Schedule
  ... to <host>" chain is never recognised as ONE reference the way
  "Parts N to M of <host>" is. (e) A quoted multi-member OR-LIST whose
  members each carry their OWN sub-pinpoint, found inside a
  substitution whose struck text names a DIFFERENT Act by a pinpoint
  chain, keeps only the FIRST member AND takes the STRUCK TEXT's Act for
  it (the (b)-shaped bug) — the or-list's own under-recall limit
  (further below) combines with the struck-text mislabelling above.
  Constructed: `resolve_references('for "section 1 of the Example Data
  Act 1990" substitute "section 27(3) or (5), 79(5) of the Example
  Protection Act 2020 apply.".', host_instrument_name="Example
  Protection Act 2020", numbering_family="uk")` at HEAD returns ONE
  reference for the or-list, "section 27(3)" EXTERNAL to `"Example Data
  Act 1990"` — the struck text's own Act — with every other member
  ("(5)", "79(5)") lost.
* **A treaty name followed directly by a different instrument's
  "<kind> YEAR" tail is silently dropped rather than split into two
  references.** Constructed: `resolve_references("Treaty on European
  Union Act 2011 applies.", numbering_family="uk")` at HEAD returns ONE
  reference, `external_instrument: "Treaty on European Union"` — "Act
  2011" is absorbed into neither the treaty's own name nor a second,
  separate reference; it is simply lost. **A "Protocol to the <Act
  Name>" name loses its own year.** Constructed:
  `resolve_references("Section 4 of the Protocol to the Example Act
  1989 applies.", numbering_family="uk")` at HEAD returns
  `external_instrument: "Protocol to the Example Act"` — "1989" is
  dropped from the name. (The sibling shapes "Human Rights Act 1998
  Commencement Order" and "the <host Act> (Commencement No. M)
  Regulations <year>" are UNAFFECTED — each resolves with its own full,
  correct name at HEAD, the latter per the addition above.)
* **A multi-section or-list with a descriptive parenthetical on each
  member loses every member but the first, and the trailing external
  instrument.** Constructed: `resolve_references("Section 12 (false
  statements) or 14 (threats) of the Example Act 2020 applies.",
  host_instrument_name="Other Act 1990", numbering_family="uk")` at
  HEAD returns TWO references — "Section 12" bare INTERNAL (its own
  parenthetical gloss and the "or 14 (threats)" member both lost, and
  the trailing "of the Example Act 2020" never attaches to it at all)
  and a separate, disconnected EXTERNAL "the Example Act 2020" with no
  pinpoint — rather than one EXTERNAL reference with two targets.
* **A plural/range EXTERNAL citation's `external_target` is a SINGLE
  string, truncated to the FIRST expanded member, unlike `targets` on
  the INTERNAL side (which carries one entry per member).** Constructed:
  `resolve_references("Sections 6501 and 6502a of the Example Commerce
  Act 1990 apply.", numbering_family="us")` at HEAD returns ONE
  reference, `external_target: "§ 6501"` — "6502a" (itself correctly
  resolved when it is the ONLY member, letter suffix and all) is
  dropped from the output entirely once it is the second member of a
  plural/range citation. The same truncation applies to a written range
  ("Sections 10 to 12 of the Example Commerce Act 1990 apply." resolves
  `external_target: "§ 10"`, dropping "11" and "12"). **The EU form is
  covered by the same limit, explicitly.**
  Constructed: `resolve_references("Articles 12 to 15 of Directive
  2031/58/EU apply.")` at HEAD returns ONE EXTERNAL reference,
  `external_target: "Article 12"` only — "13" through "15" are
  dropped. `resolve_references("Articles 12 and 14 of Directive
  2031/58/EU apply.")` at HEAD likewise returns ONE EXTERNAL
  reference, `external_target: "Article 12"` only — "14" is dropped.
  A consumer that rolls an EXTERNAL reference up to the article level
  using `external_target` alone therefore loses every member but the
  first of a plural/ranged EU citation too, not only the US form
  above.
* **A multi-member or-list whose members each carry their OWN
  sub-pinpoint drops every member but the first, and mislabels even
  that one.** Constructed: `resolve_references("Section 27(3) or (5),
  79(5) or (7) of the Example Act 1990 applies.",
  host_instrument_name="Other Act 2000", numbering_family="uk")` at
  HEAD returns TWO references — "Section 27(3)" bare INTERNAL (its own
  "or (5)" sibling, the second member "79(5) or (7)", and the trailing
  "of the Example Act 1990" are all lost) and a separate, disconnected
  EXTERNAL "the Example Act 1990" with no pinpoint — the same failure
  mode the descriptive-parenthetical or-list limit above documents,
  confirmed here for a sub-pinpoint-bearing or-list too.
* **A bare relative "paragraph N", resolved against an `enclosing_unit`
  that is itself a bare "Part M" (not a Schedule), is formatted with
  the EU comma-chain's own "(N)" sub-pinpoint convention instead of a
  UK "Schedule, paragraph" convention** — `_resolve_relative`'s
  `label == "paragraph"` branch applies regardless of
  `numbering_family`. Constructed: `resolve_references('for "x"
  substitute "paragraph 9".', enclosing_unit="Part 1",
  numbering_family="uk")` at HEAD resolves "paragraph 9" INTERNAL with
  `pinpoint: "Part 1(9)"` — a malformed UK pinpoint (no such form
  exists in UK drafting); the EU reading treats "Part 1" as if it were
  an EU Article and "paragraph 9" as its own numbered paragraph.
* **Once a "Schedule" mention has itself been swallowed into a
  WRONGLY-labelled EXTERNAL reference (the plural/ranged
  host-naming-chain limit above), a LATER "that Schedule" no longer
  finds it as an antecedent at all** — R4's sub-unit anaphora looks for
  the nearest preceding mention of the SAME sub-unit word among the
  mentions this module tracks for that purpose, and a mention already
  consumed into another reference's own `literal` is not among them.
  Constructed, compare the two runs directly: with no chapeau,
  `resolve_references("Schedule 2 to the Example Protection Act 2020
  applies. Paragraph 9 of that Schedule also applies.",
  host_instrument_name="Example Protection Act 2020",
  numbering_family="uk")` at HEAD resolves "that Schedule" correctly,
  `pinpoint: "Schedule 2"`; the SAME two sentences placed inside a
  chapeau'd amendment — `resolve_references('In section 9 of the
  Example Other Act 1990, for "x" substitute "Schedule 2 to the
  Example Protection Act 2020 applies. Paragraph 9 of that Schedule
  also applies.".', host_instrument_name="Example Protection Act 2020",
  numbering_family="uk")` — resolves "that Schedule" to a bare,
  disconnected `pinpoint: "Schedule"`, tagged `ambiguous_reference`,
  because the host-literal-but-other-label bug above has already
  pulled "Schedule 2" into a separate EXTERNAL reference's own literal
  rather than leaving it as a trackable INTERNAL "Schedule" mention.
* **A chain-attached "thereof" ("<pinpoint> thereof", as distinct from
  the bare, untyped "thereof" on its own) is recognised ONLY inside the
  gated EU preamble convention ("Having regard to <Treaty>, ...
  Article N thereof") — everywhere else, the chain resolves on its own
  (bare INTERNAL to the host, ignoring whatever instrument "thereof"
  was meant to name) and "thereof" itself is silently dropped, never
  emitted as its own item or attached to the chain's own reference.**
  Constructed, each run directly: `resolve_references("The Example
  Regulation applies. The second subparagraph thereof governs
  enforcement.")` at HEAD returns NO reference at all for the second
  sentence (empty list) — "subparagraph" alone carries no recognised
  numbering keyword, so nothing matches and "thereof" is lost with it.
  `resolve_references("The Example Regulation applies. Point (h)(iii)
  thereof governs enforcement.")` at HEAD returns ONE reference, "Point
  (h)" bare INTERNAL tagged `ambiguous_reference` — the "(iii) thereof"
  tail is dropped entirely, never attached. `resolve_references("The
  Example Regulation applies. Section 5 thereof governs
  enforcement.")` at HEAD returns ONE reference, "Section 5" bare
  INTERNAL with its own pinpoint — "thereof" is simply ignored, the
  reference is never made EXTERNAL to "The Example Regulation" the way
  "that Act"/"thereof" anaphora elsewhere in this section is.

See `src/five_d_nd/clause_cues.py` (`resolve_references`,
`enclosing_unit_at`, `_xref_count_and_objects`,
`clause_cue_point_from_profile`, `cross_reference_links_from_profile`),
`conformance/vectors/clause-cues/xref-v2-*.json`,
`conformance/vectors/resolution-profile/xref-resolver-field-*.json`.

## §9 The nD grammar contract

An nD grammar publishes, to attach to 5D:

### The `NDSystem` document

Ported field-for-field, rule-for-rule from versum's `src/versum/nd.py`
`NDSystem`/`AxisSpec` (`AxisSpec.violations()`, `NDSystem.violations()`),
INCLUDING versum's own leniency rules — an implementation MUST reproduce
these too, not just the strict checks:

```
{
  "id": str,             # STRING ONLY — MUST match
                          # ^[A-Za-z][A-Za-z0-9_.:-]*$
  "namespace": str,      # STRING ONLY — MUST match the same pattern
  "version": str | number,   # a STRING, or a JSON NUMBER accepted via str()
                              # coercion — MUST be
                              # non-empty once coerced
  "version_5d": str,     # informative — not itself validated beyond being a string
  "axes": {
    axis_id: {           # axis_id MUST match the same id pattern; a null/falsy axis
                          # value is treated as {} (versum's own "v or {}"), NEVER a
                          # violation by itself
      "value_type": "string"|"controlled_identifier"|"concept_reference"|
                     "entity_reference"|"integer"|"non_negative_integer"|
                     "number"|"boolean"|"date"|"interval"|"quantity",  # default "string"
      "cardinality": "one"|"many",                       # default "many"
      "vocabulary_mode": "closed"|"open"|"external",      # default "closed" iff the KEY
                                                           # "vocabulary" is PRESENT at all
                                                           # (even an empty list) — NOT iff
                                                           # a non-empty vocabulary is given
      "vocabulary": scalar | [scalar, ...] | null,   # a JSON SCALAR (string/number/
                                              # boolean), an array of JSON scalars, or
                                              # null — MUST be
                                              # non-empty when vocabulary_mode ==
                                              # "closed"; a bare scalar means the same as a
                                              # one-element list (versum's "_tuple()")
      "primitives": [...] | scalar | null,   # each MUST be one of equal/contains/
                                              # contained_by/overlaps/disjoint/precedes/
                                              # succeeds; a BARE SCALAR (e.g. "equal", not
                                              # ["equal"]) means the same as a one-element
                                              # list, and MUST NOT be iterated
                                              # character-by-character; null coerces to an
                                              # empty list (zero primitives, never a
                                              # violation); default [equal] when the key is
                                              # ABSENT entirely
      "ontology_id": str, "ontology_version": str   # (or nested {"ontology": {"id","version"}})
                                                     # — BOTH MUST be present when
                                                     # vocabulary_mode == "external"
    }
  },
  "bindings": [{"form_slot": str,
                "allowed_axes": [...] | scalar | null,   # same scalar/list/null
                                                          # coercion as primitives/
                                                          # vocabulary above
                "required": bool}],
                          # form_slot MUST be non-empty; every allowed_axes entry
                          # MUST name a declared axis
  "ontology_relations": [...],   # ARRAY ONLY
  "validation": {"unknown_values": "reject", "missing_coordinates": str,
                 "provenance_required": bool}
}
```

**Explicit field types, one line per field — this
table is the single authority code, the schema, the fuzz's own malformed-
field classifier, and the strictness lists all follow exactly, replacing
any earlier case-by-case inference about which fields the table "annotates"
with an alternate shape:**

- **`id`, `namespace`**: STRING ONLY. Any other JSON kind is a malformed
  shape — including a value (e.g. `true`) that versum's own `str()`
  coercion would otherwise swallow into something matching the id pattern
  (`str(True) == "True"`). The reference validator REJECTS a non-string
  outright here (no coercion at all) — a NAMED P2 divergence class
  (`conformance/vectors/nd-system/invalid-namespace-true-malformed-
  despite-versum-accepting.json`).
- **`version`**: STRING, or a JSON NUMBER (`int`/`float` — NEVER a JSON
  BOOLEAN, which is its own type, not "a number") accepted via the SAME
  str() coercion versum uses. A boolean, `null`, an array, or an object
  are all malformed shapes — the reference validator rejects all four
  outright, even though versum's own `str()` coercion would swallow them
  too (another NAMED P2 class).
- **`ontology_relations`**: ARRAY ONLY (`list`/`tuple`). A non-iterable
  (P1-unsafe for versum too — it crashes `tuple()`) is rejected by both
  sides; a non-array ITERABLE (a string, a dict, a set) is additionally
  malformed under this explicit type, even though versum accepts any
  iterable by tupling it (a NAMED P2 class).
- **`vocabulary`**: a JSON SCALAR (string/number/boolean), an array of
  JSON scalars, or `null`. A `null`, array, or object ITEM inside the
  array is malformed, and so is an object `vocabulary` itself — the
  reference validator and versum both still ACCEPT these shapes (neither
  crashes, `_tuple()` never filters item types), so this is P3-only
  schema strictness, not a code divergence.
- **`primitives`, `allowed_axes`**: `[...] | scalar | null` — unchanged
  from the field table above; a bare scalar means the same as a
  one-element list (versum's own `_tuple()`), and `null` coerces to an
  empty list.

A document MAY ALSO be wrapped as `{"nd_system": {...the fields above...}}`;
an implementation MUST unwrap one level first (versum's own `root =
raw.get("nd_system", raw)`) before applying the rules above — both the bare
and the wrapped form validate identically.

**`validation.unknown_values` is NOT checked at the `NDSystem` level** — in
versum, that check lives one layer up, in the descriptor validator
(`planes.py`), not inside `NDSystem.violations()` itself. This specification
reproduces that exact layering (`src/five_d_nd/contract.py`
`nd_system_violations()` vs. `descriptor_violations()`): an `NDSystem`
document whose `validation.unknown_values` is anything other than `"reject"`
is, by itself, still a VALID `NDSystem` document — it is the DESCRIPTOR that
embeds it which MUST reject it (see below). `version_5d`,
`missing_coordinates`, and `provenance_required` are documented, carried
fields with no additional NDSystem-level validation rule beyond their basic
types.

### The grammar descriptor — TWO forms

This specification defines TWO forms of the grammar descriptor, because JSON
(the interchange format conformance vectors and a `.lg`-style document use)
cannot carry a callable:

- the **RUNTIME descriptor** — used when an nD grammar is loaded as live
  code (matching versum's `src/versum/planes.py`
  `DescriptorPlane.from_descriptor` exactly): `produce` is **REQUIRED** and
  MUST be callable;
- the **JSON INTERCHANGE form** — used for a descriptor document (e.g. a
  conformance vector, a registry entry): `produce` is **OMITTED**; every
  other check is identical.

```
{
  "plane": str, "language_version": str,
  "nd_system": {...},          # an NDSystem document; version == language_version;
                                # its validation.unknown_values MUST be "reject"
                                # (checked HERE, at the descriptor layer — see above)
  "binding": {relation_or_field: <one of the five dimensions>},   # may be {}
  "produce": produce(sentence, context=None) -> [claim, ...],   # RUNTIME form only
  "examples": [{"sentence": str, "expected": [claim, ...],
                 "context": {...}}],       # optional; "context" optional per example
  "contract_version": str,      # REQUIRED — the conformance marker, see §10
  "co_dimensions": [axis_id, ...]   # OPTIONAL, see §9 below
}
```

A `binding` value is a BARE DIMENSION STRING, one of the five dimensions
(§2) — exactly versum's own `p5.is_dimension(dim)` check, with no object
form and no mode (§7, N1-N2: 5D is neutral on is/ought, so a normative
relation binds exactly like any other — see `src/five_d_nd/contract.py` and
`conformance/vectors/descriptor-binding/`). `contract_version` is THIS
specification's own addition beyond versum's own descriptor contract (its
`_REQUIRED_KEYS` has no `contract_version`).

**How a grammar declares conformance.** `contract_version` MUST equal, EXACTLY,
the 5D spec version string the grammar was written against — compared by
exact string equality, NEVER a range, a prefix, or a semver comparison. For
this draft that value is `"1.0-draft"` (`src/five_d_nd/contract.py`
`SPEC_VERSION`). A grammar that targets a later draft publishes THAT draft's
version string once this specification is revised; there is no forward- or
backward-compatibility claim across versions — a descriptor whose
`contract_version` names a different draft is simply not conformant to THIS
draft, whether or not its shape happens to validate (see
`conformance/vectors/descriptor-binding/contract-version-wrong-value-rejected.json`).

**`examples[].context`** is an OPTIONAL object on an individual example,
passed through to `produce(sentence, context)` when present. Most grammars
never need it (their `produce` reads no context); a context-dependent
grammar — topos is the motivating case — needs it to reproduce its own
packaged examples. Absent is the common case and is always valid; an
implementation MUST NOT require it (see
`conformance/vectors/descriptor-binding/examples-context-passthrough-accepted.json`).

**`co_dimensions`** is an OPTIONAL list of axis ids drawn from the SAME
descriptor's own `nd_system.axes` (see "Co-dimension" below) — a grammar's
explicit declaration of which of its axes it is using as a co-dimension. Each
listed id MUST name a declared axis of this descriptor's own `nd_system`;
that cross-reference is the ONLY check performed (code-only — no JSON Schema
can express it generically; see `src/five_d_nd/contract.py`
`descriptor_violations()`). Keep this minimal: `co_dimensions` is a
bookkeeping convenience, not a new validation surface — it adds no dimension,
no weight, and no verdict-readable signal of its own (§7 N1, §9 "Invariant
for consuming languages" below).

### Co-dimension (§7, N3) — final, OPTIONAL

A **co-dimension** is an ordinary axis a grammar declares in its own
`NDSystem` (above) ALONGSIDE a binding, used to carry information 5D itself
does not track — most importantly, whether a relation is normative. It is
NOT a new mechanism: it is exactly an `NDSystem` axis, nothing more. The
deontic plane's existing `operator` axis (closed vocabulary `{O, P, F}`) IS
a co-dimension in this sense — it already distinguishes a normative
declaration from a descriptive one, entirely within nD, without 5D ever
needing a mode field.

Declaring a co-dimension is **OPTIONAL** (owner decision, 2026-10-01, final:
"co-dimension rule is final, optional"). A grammar MAY bind a normative
relation to a dimension — SHOULD default it to `intentional` when it does
not bind one explicitly (§7 N3) — with NO co-dimension axis at all, and
still conform to this specification; nothing about the binding itself
requires one. A descriptor whose `NDSystem` has no axis marking any
relation as normative is just as valid as one that declares such an axis
(see `conformance/vectors/descriptor-binding/`).

### Invariant for consuming languages

**No verdict or decision of an nD language may read a composed 5D weight or
position.** A verdict is a normative act (§7); 5D composition (§3, §5) is
descriptive. Reading a 5D weight or position to DECIDE a verdict would smuggle
an is into an ought. An nD grammar MAY read 5D to describe what it is
grounded in (citation, provenance), never to derive its normative force.

This invariant is a NORMATIVE CONSTRAINT ON CONSUMING LANGUAGES (nD grammars
and whatever hosts them) — it governs how an nD grammar's OWN verdict logic
may use 5D, which lives entirely outside this specification's own reference
implementation. It is NOT, and cannot be, machine-checked by anything in this
repository: `src/five_d_nd/` has no verdict logic of its own to check, and
checking an arbitrary downstream nD grammar's implementation for whether its
verdict function reads a 5D value is outside 5D's own contract (§1's scope).
Conformance (§10) does not include this invariant among its machine-checked
criteria.

### Validator parity policy (P1-P3)

The reference validator (`src/five_d_nd/contract.py`, functions named
`*_violations`/`is_valid_*`) is **NORMATIVE and FAIL-CLOSED**. This section
states, ONCE, its exact relationship to versum (the implementation §9's
`NDSystem`/descriptor contract is ported from) and to the JSON Schemas under
`schema/` — replacing any earlier case-by-case justification for an
individual field's divergence with a single named policy a new divergence
is checked against.

**Malformed shape, defined precisely.** A document is MALFORMED AT A GIVEN
FIELD when the JSON value occupying that field's position has a
fundamentally different JSON kind (string / number / boolean / null / array
/ object) than the type this specification's own field table (§9) declares
for that position, AND no rule this section itself documents for that field
— a `_tuple()`-style bare-scalar-means-one-element-list coercion, an
`or {}`/`or ()` falsy-value coercion, a `str()` coercion, the
`{"nd_system": {...}}` wrapper-unwrap rule — covers the given shape. A value
is NEVER malformed merely because its CONTENT is wrong while its SHAPE still
matches the declared type (an unknown enum string, a pattern mismatch, a
missing-but-optional key, a cross-field inconsistency) — that is an ordinary
violation, not a malformed shape, and both the reference validator and
versum MUST reject it identically (no P2/P3 exception applies to it).

- **P1 — the reference validator is never more lenient than versum.** It
  MUST NEVER accept (report zero violations for) a document versum rejects
  (by raising, or by itself reporting a violation). A document the code
  accepts and versum rejects is ALWAYS a defect in the code, with NO
  exception — this is the floor every other rule in this policy sits on.
- **P2 — the reference validator MAY be stricter than versum on a malformed
  shape.** It MAY reject a document versum would otherwise accept WHEN the
  rejection is keyed to a field that is MALFORMED (the definition above) at
  the point the violation is reported. This is a documented CLASS of
  allowed strictness, decided once here, not something each individual
  divergence needs its own case-by-case justification for — but every
  INSTANCE of it MUST still be named explicitly (a vector, an exception set
  entry, a mutation-generator tag) so it is never silent.
- **P3 — a JSON Schema defines the WELL-FORMED AUTHORING subset, and MAY be
  stricter than the reference validator (or versum) on a malformed shape,**
  for the identical reason P2 permits the code to be stricter than versum: a
  hand-authored document should not be invited to exploit a coercion rule
  `str()`/`_tuple()`/`or {}` happens to tolerate. Each schema states, in its
  own `description`, that it is stricter than code/versum in this one
  documented way. A schema MUST accept every WELL-FORMED document (no
  malformed shape anywhere in it) that BOTH the reference validator AND
  versum accept — a schema rejecting a well-formed, code-and-versum-valid
  document is a schema DEFECT, never allowed strictness.

`tests/test_conformance.py` and `tests/test_fuzz.py` encode P1-P3 directly:
a versum-rejects/code-accepts disagreement is a hard, unconditional test
failure (P1); a code-rejects/versum-accepts disagreement is a test failure
UNLESS the specific vector (by name) or mutation (by generator tag) is
named in a documented exception set that classifies it malformed (P2); the
schema-vs-code differential applies the identical rule at the schema/code
boundary (P3).

**The classifier is PER FIELD, not per document.** An
implementation's own malformed-shape classifier MUST return the SET of
malformed field paths a document carries (e.g. `{"axes.a.vocabulary"}`,
`{"version"}`, `{"bindings"}`) — never a single whole-document boolean. A
P2 or P3 disagreement is excused ONLY when EVERY violation the stricter
side reports (the reference validator's own `(field_path, message)` pairs
for P2 — see `nd_system_violations_with_paths()`/
`descriptor_violations_with_paths()`; a JSON Schema error's own
`absolute_path` for P3) is located at one of those malformed paths. A
whole-document boolean classifier is a MASKING BUG, not a simplification:
if ANY field anywhere in a document is malformed, it would wrongly excuse
EVERY disagreement in that document, including one at a completely
different, well-formed field — exactly the defect an earlier fuzz
rewrite (`tests/test_fuzz.py`) fixed and proved fixed (see that file's own
module docstring and its two masking-regression proofs).

## §10 Conformance

An implementation conforms to this specification when it:

1. Reproduces the closed set of five dimensions and their canonical order
   (§2, `vocabulary/dimensions.json`);
2. Reproduces the composition table byte-for-byte (§3,
   `vocabulary/composition.json`);
3. Evaluates a path of 3+ dimensions by left-fold (§3);
4. Computes an entry's 5D fingerprint per §5's rules;
5. Reproduces the canonical reference syntax, canonicalisation and digest
   rules of §4;
6. Keeps 5D neutral on is/ought (§7, N1-N4) — a link carries exactly one
   dimension and nothing else; a normative relation binds a dimension
   exactly like any other; an `embeds` link (matched case- and
   separator-insensitively) is always dimension `structural`;
7. Lowers an already-parsed assertion per §8's rules;
8. Validates an `NDSystem` document and a grammar descriptor per §9,
   fail-closed, and publishes its own `contract_version`;
9. Honours §9's validator parity policy (P1-P3): never accepts a document
   versum rejects; is stricter than versum (or than the code, for a schema)
   only on a MALFORMED shape, named explicitly, never silently;

AND passes every vector under `conformance/vectors/<family>/*.json` — see
`tests/test_conformance.py` for the reference runner. The minimum vector
counts per family are listed in that test file's family list; this
repository's own counts are reported in its evidence (see the repository's
CHANGELOG and commit history for the count at any given release).

## §11 The coordinate data model: points and triples

Status: this round's additions (2026-10-01) are ADDITIVE ONLY — §5's shares
view, §9's contract, and every other existing section are UNCHANGED. Nothing
in the existing public API is renamed or removed.

**Point; FORMULA REPLACED by a later decision.** An entry or node's POINT is five INDEPENDENT
values, each in `[0, 1]`, compared by COSINE — unlike §5's shares view, a
point's five values are NOT constrained to sum to 1. The existing sum-to-1
§5 position becomes a documented DERIVED VIEW of the same underlying raw
contributions (`src/five_d_nd/point.py`'s `shares_view()`, a thin
re-export of `five_d_nd.position.normalise()` — `position.py` itself is
untouched).

**Derivation formula, REPLACING this specification's
earlier max-normalised formula.** Each dimension is INDEPENDENT and
SATURATING:

```
point[d] = round(min(raw[d] / saturation[d], 1.0), 6)
```

`saturation` is a resolution-profile field (§16, `point_saturation`) — ONE
SHARED scalar across all five dimensions by default. Shared-vs-per-dimension
is not fixed by the base formula ("point dimension =
min(count/saturation,1), independent (not max-normalised)") — it is
THIS SPECIFICATION's own
implementation choice; a caller MAY instead supply a PER-DIMENSION mapping,
since the formula is already per-dimension. The shared default (5) is the
SAME value `depth.py`'s own `link_saturation` already uses.

**The no-contribution case needs NO special branch.** The EARLIER "neutral
all-0.5" rule — and its "equidistant from both poles" justification — are
WITHDRAWN (that justification was WRONG: there is no pole-equidistant
point for a saturating, not bounded-on-both-sides, formula). With zero raw
contributions on every dimension, the formula above naturally returns the
ALL-ZERO point (`min(0/s, 1) == 0` for every `d`) — no special-casing
needed. Distinguishability from a UNIFORM-BUT-NONZERO point (e.g. one hit
on every dimension) is carried entirely by cosine's existing
degenerate-zero-norm rule (below): `cosine(zero, zero) == 0.0` (never
self-similar to 1.0), while `cosine(uniform, uniform) == 1.0` — the
all-zero point and a uniform-but-nonzero point are NEVER confused.

**Cosine.** `cosine(p, q) = dot(p, q) / (|p| * |q|)`, rounded to 6 decimal
places; the degenerate all-zero-norm case (the no-contribution point this
formula produces) is defined as `0.0`, never an exception.

**Distinctness.** Because `min(x/s, 1)` is STRICTLY MONOTONE (injective)
below the ceiling `s`, two DIFFERENT raw counts on the same dimension
produce two DIFFERENT point values whenever both are below `s`; the
formula still clamps the final OUTPUT to `[0, 1]` (a point itself must stay
bounded) — `conformance/vectors/point/` exercises this directly (the
`distinctness-*` vectors).

An nD grammar or host MAY supply an alternative encoder (a learned model, an
LLM-scored point) in place of this formula; such an encoder is NEVER
normative — this is the ONE formula every conformant implementation MUST
reproduce when no override is supplied. **Explicit field types**: a
POINT document is a mapping with EXACTLY the five
dimension keys (§2), each a JSON number (never a boolean) in `[0, 1]` — no
extra keys, no missing keys (`point_violations()`/`is_valid_point()`). See
`src/five_d_nd/point.py`, `schema/point.schema.json`.

**Triple.** A triple is `(s, p, o, dimension,
weight, provenance)` plus an OPTIONAL `grammar_id` — one edge record, in
the originals' own ConceptGraph-edge style, not RDF-star
reification. EVERY triple carries EXACTLY ONE dimension (§6 already states
this for a "link"; a triple is a link with its endpoints named `s`/`o` and
its relation named `p`). **Explicit field types** (mirroring
`triple.py`'s `triple_violations()` exactly): `s`, `p`, `o` —
non-empty STRING; `dimension` — one of the five (§2), never absent;
`weight` — a JSON number (never a boolean) in `[0, 1]` (the composition
algebra's own multiplicative range, §3), defaulting to `1.0` when absent;
`provenance` — MUST be PRESENT (any JSON value; its shape is an nD
grammar's own concern, matching §6's own looseness about additional link
fields); `grammar_id` — OPTIONAL, a non-empty string naming which nD
grammar's `produce()` (§9) emitted this triple (an
assertoric-layer triple, §8, has no owning nD grammar and omits it).
`enables`/`requires` bind to `causal` (resolving
a four-way lineage conflict among the originating designs) — this
is an nD grammar's `binding` concern (§9), not something this module itself
classifies. **Weight composition along a path is normative**:
`compose_weights(w1, w2) = w1 * w2`, multiplicative — this
REPLACES §3's own "Weight composition — INFORMATIVE, OPEN" marker and Annex
B's corresponding OPEN entry; both are now CLOSED. See
`src/five_d_nd/triple.py`, `schema/point.schema.json`,
`schema/triple.schema.json`, `conformance/vectors/triple/`.

## §12 Fixed-point arithmetic

Status: build list item 2. Every leaf value a derived view folds over (a
member point's component, a weight) is quantised EXACTLY ONCE, at the point
it enters the fold, to a scaled integer: `SCALE = 1_000_000` (1e-6
precision), comfortably within an int64. From there every SUM is plain
integer addition — associative and commutative by construction, so fold
order over already-quantised values stops mattering (this touches only the
point/weight arithmetic; it never changes §3's own left-fold rule for the
DIMENSION algebra, which stays normative and unrelated). Exactly ONE
division, and ONE rounding, happen — at VIEW MATERIALISATION (a container's
mean position, §14; a trimmed top-k's match statistic, §14) — never
mid-fold:

```
to_fixed(x)       = round_half_away_from_zero(x * 1_000_000)
fixed_sum(values) = sum(values)                                 # int addition
fixed_mean(total, n) = round_half_up(total / n)                 # ONE division point
                      = (total + n // 2) // n    for total >= 0
```

`to_fixed`'s multiplication `x * 1_000_000` is performed in IEEE-754
binary64 (fix round item 12): `x`'s own binary64 representation times the
binary64 value `1_000_000.0`, producing the nearest binary64 result per
IEEE-754's default rounding rule, and ONLY THEN rounded to the nearest
integer, half away from zero. Stated explicitly so another language
reproduces the SAME scaled integer for the SAME input `x`: an
implementation that multiplies in a wider or narrower float type, or in a
decimal/rational type, before rounding to the nearest integer is not
guaranteed to agree with this specification's own reference on every
input, even though both satisfy "round half away from zero" as an
abstract description.

Ties in a trimmed top-k (§14) are broken by CANONICAL SALTED claim-id
order: `canonical_tiebreak_key(claim_id, salt) = sha256(salt + "|" +
claim_id)`, sorted ascending — never insertion order, and never an
UNSALTED id (which would leak a stable, guessable ordering across
containers). `salt` is a resolution-profile field (§16,
`tiebreak_salt`), so the tiebreak order itself is pinned by the profile
digest. See `src/five_d_nd/fixedpoint.py`.

## §13 Containers (cubes): identity, nesting, and the reverse index

Status: build list item 3. A container has a STABLE id and a VERSIONED
member set, digested: `member_set_digest(member_ids, version) =
sha256(canonical_json({"members": sorted(member_ids), "version":
version}))` — any edit to the member set MUST bump `version`.

**Nesting is an OPEN DAG.** Any container MAY
nest any container, with NO depth cap, bounded only by compute.

**Cycle rejection, REPLACING this specification's earlier
full-reachability-per-write guard.** A CYCLE
IS REJECTED AT WRITE TIME via an INCREMENTALLY MAINTAINED topological
order (Pearce-Kelly class) — this is now REQUIRED, not
implementation-defined: the reference implementation
(`src/five_d_nd/container.py`'s `add_nesting_edge()`) carries the DAG as
`{"children": {...}, "order": {node: int}, "reverse": {...}, "next_order":
int, "prev_order": int}` and, on adding `parent -> child`:

1. **Fast path** — if `order[parent] < order[child]` already, the edge is
   consistent with the existing order; add it, O(1), no traversal.
2. **Slow path** — otherwise, a BOUNDED forward DFS from `child` (never
   past `order[parent]`) finds the "reachable forward" set RF; if `parent
   in RF`, the edge would CLOSE A CYCLE — rejected (`CycleError`).
   Otherwise a BOUNDED backward DFS from `parent` (never past
   `order[child]`) finds the "reachable backward" set RB, and the order
   VALUES already occupied by `RB union RF` are reassigned — RB's own
   nodes first (keeping their own relative order), then RF's (same) — so
   the order stays valid with the new edge included.
3. **New-node path** — when EITHER endpoint is brand new, NO cycle is
   possible (a node with no prior edges can neither already reach
   anything nor already be reachable) and NO traversal happens: a
   brand-new CHILD gets the `next_order` slot (always above every value
   assigned so far, trivially after any parent); a brand-new PARENT of an
   ALREADY-EXISTING child gets the `prev_order` slot (always below every
   value assigned so far, trivially before that child, with NO need to
   even read the child's own order value). This is what keeps every
   "at least one endpoint new" write O(1) too, not only the already-
   consistent pair case.

Both traversals are bounded to the AFFECTED region between the two
endpoints' current order values, never the whole graph — this is what
makes the maintenance "incremental". A self-loop (`parent == child`) is
rejected UNCONDITIONALLY, BEFORE either node is looked up or inserted —
including when the node has never been seen before, so a rejected
self-loop on a brand-new id leaves the record with NO trace of that id at
all. `conformance/vectors/cycle-rejection/` includes a dedicated case that
FORCES a real reassignment (two separate chains joined by an edge
inconsistent with their existing order), not merely rejection cases.

**Reverse membership/embeds index** (`reverse_index()`): `index[child] =
{every parent that directly embeds child}` — the structure §15's staleness
propagation walks outward from a changed node to every ancestor on every
branch. `reverse_index()` is now ALSO maintained INSIDE the DAG record
itself (`dag["reverse"]`, below), so reading it is a cheap copy, not an
O(E) recomputation.

**Cost — IN PLACE, for the 1M-document scale target, REPLACING an
earlier structural-sharing-but-still-allocating version.** `add_nesting_edge()` mutates the CALLER-OWNED dag
record DIRECTLY — `children`, `reverse`, `order`, `next_order` and
`prev_order` are all updated IN PLACE, with NO top-level copy of any kind
on ANY path. Every §13 cost sentence is now LITERALLY true of the
reference implementation, not merely "true up to one shallow dict
allocation per call":

- **Fast path: O(1), zero allocation.** No dict/set is created; the
  existing `children[parent]`/`reverse[child]` sets are mutated with a
  plain `.add()`.
- **New-node path (at least one endpoint brand new): O(1), zero
  traversal.** The two-counter scheme above assigns the new node's order
  without ever reading the other endpoint's position.
- **Slow path (a forced reorder): O(affected region)**, bounded exactly as
  before — never the whole graph.
- **No O(E) reverse-index rebuild, no O(V) `max(order.values())` scan**,
  unchanged from the fix above.

**Versioning/persistence is the CALLER's job.** Since `add_nesting_edge()`
now mutates the record a caller owns, THIS module no longer hands back an
implicit, isolated copy as a side effect of writing. A caller that needs
one — to compare a before/after state, to persist a point in time, or to
keep multiple independent versions alive at once — MUST take one
explicitly via `snapshot_dag(dag)`, a DEEP-ENOUGH copy (every member SET
in `children`/`reverse` is copied, not merely the top-level mapping) that
stays unaffected by any later write to the ORIGINAL record. A container's
own VERSIONED member set (`member_set_digest()`, above) is the OTHER tool
available for the same purpose at the content level, when a full
structural snapshot is more than a caller needs.

**Rejection leaves the record byte-for-byte unchanged.** Because a cycle
can only close between two PRE-EXISTING nodes, the cycle check always runs
BEFORE any insertion or mutation — never partially applying part of a
write (a new node, a partial reorder) before discovering the rejection.
`tests/test_conformance.py`'s
`test_rejected_write_leaves_the_record_byte_identical_deep_compare` checks
this via a full `snapshot_dag()` comparison, for both a real cycle between
two existing nodes and a self-loop on a node never seen before.

**A SUCCESSFUL write on a raw, non-canonical `{}` record attaches the
complete shape.**
`test_add_nesting_edge_on_a_raw_empty_dict_attaches_children_order_reverse`
asserts `add_nesting_edge({}, "a", "b")` ends with `children == {"a":
{"b"}, "b": set()}` and the matching `reverse`/`order`/`next_order`/
`prev_order` — not merely "no crash". Confirmed directly (mutation
testing, scratch copies): `no-attach-children` (dropping the
`dag["children"] = children` commit line) is KILLED by this test.

**Timing — INFORMATIVE ONLY.**
The table below is a measurement of this ONE reference implementation on
ONE machine at ONE point in time — never a conformance requirement, and
never asserted by any test. The actual O(1)/O(1)/O(affected-region) COST
claims are proven by a DETERMINISTIC, scan-COUNTING test (below), never by
wall-clock timing, which this table remains for exactly that reason.
Measured directly against this reference implementation, mean
microseconds per call over 500 calls at each N, on a chain of N nodes
(the column labels below correct an earlier draft, which mislabelled two
NEW-NODE-path measurements as "fast path", and never actually measured
the TRUE fast path, an already-ordered PRE-EXISTING pair, at all):

| N | fast path (existing pair, already ordered) | new-node path (new child of existing parent) | new-node path (new parent of existing child) | local forced reorder |
|---|---|---|---|---|
| 1,000 | 0.76 us | 0.87 us | 0.84 us | 2.86 us |
| 10,000 | 0.52 us | 0.85 us | 0.80 us | 3.15 us |
| 50,000 | 0.73 us | 1.01 us | 0.98 us | 3.30 us |
| 100,000 | 0.82 us | 1.42 us | 1.13 us | 3.70 us |

The fast path and both new-node paths stay FLAT (sub-microsecond to
~1.4 microseconds) across two orders of magnitude of N, confirming the
O(1) claim in practice, not only on paper (the small upward drift from 1k
to 100k is consistent with ordinary Python dict/set hashing overhead at
scale, not a scan over the graph). The local forced reorder — performed
on 500 independent, always-4-node-sized local components SHARING a dag
record with the N-node chain — also stays flat and small (2.9-3.7 us),
confirming that a reorder's cost tracks the AFFECTED REGION's own size,
never the total graph size N it happens to share a record with.

**A real regression was found and fixed while re-measuring this table.**
The new-node path's own counter lookup was written as
`dag.get("next_order", (max(order.values()) + 1) if order else 0)` —
which LOOKS like a cheap default-on-miss read, but a Python dict's
`.get()` evaluates its SECOND argument EAGERLY, on every call, whether or
not the key is present. This silently reintroduced the O(V)
`max(order.values())`/`min(order.values())` scan on every single write
(measured: a 10,000-node chain build went from ~10ms to ~650ms). Fixed to
an explicit `if "next_order" in dag: ... else: ...`, which only ever
evaluates the scan the one time the key is genuinely absent.

**The regression guard is a deterministic CALL COUNTER, not a wall-clock
timer, replacing an earlier flaky version: 23%
failures under CPU load, and under enough load it could even pass BROKEN
code, since a loaded machine can shrink a timing ratio below any fixed
threshold.** `tests/test_conformance.py`'s
`test_add_nesting_edge_new_node_path_does_not_rescan_order_per_call`
monkeypatches `container.max`/`container.min` with counting wrappers —
Python resolves a bare `max`/`min` call inside `container.py` through the
MODULE's own global namespace before falling back to builtins, so
assigning `container.max`/`container.min` shadows the builtin for every
call made from inside that module, with no change to `container.py`
itself — builds a 5,000-node chain on a fresh `empty_dag()` (asserting
EXACTLY ZERO `max`/`min` calls, since both counters are already present
from the start), and separately on a counter-less record (asserting AT
MOST ONE lazy-initialisation call to each, on the first write only, and
NONE after). Confirmed directly (mutation testing, scratch copies): both
`eager-get` (reintroducing the eager `.get()` fallback) and `always-scan`
(unconditionally rescanning `max`/`min` on every write) are KILLED by this
test.

**Concurrency.** The in-place API is NOT thread-safe: two concurrent
writers calling `add_nesting_edge()` on the SAME dag record MAY observe
or produce an inconsistent order (a direct, intended consequence of the
"in place, no top-level copies" decision — a copy-on-write
design would have given isolation at the cost of the allocation that
decision exists to remove). Serialising concurrent writers to the same
record is the CALLER's responsibility, not this module's.

`conformance/vectors/cycle-rejection/`'s cost test
(`test_cycle_rejection_cost_fast_path_visits_nothing_and_reorder_stays_bounded`,
`tests/test_conformance.py`) instruments both bounded traversals directly
and asserts: the fast path calls NEITHER; the slow path's visited nodes
all have an order value within `[lb, ub]` at the time of the call; a
separate test (`test_new_parent_of_existing_child_is_order_consistent_
without_reorder`) confirms the new-node path needs no reorder at all.

See `src/five_d_nd/container.py`, `conformance/vectors/cycle-rejection/`.

## §14 Container position, match statistic, and depth

**Container POSITION** is the fixed-point
AVERAGE of its members' points (§12), one value per dimension — individual
member points are KEPT, never discarded. An EMPTY container has NO position
(not an all-zero or all-neutral one) — `container_position([])` MUST raise,
never invent a value.

**MATCH KEY**: a TRIMMED TOP-K over OPERATIVE members (`operative` defaults
`True`), `k` and the small-n floor `n_min` from the resolution profile
(§16; `k` default 5). Operative members are ranked by `weight` DESCENDING;
a rank tie breaks on §12's canonical salted tiebreak order. When the
operative count `n` is BELOW `n_min`, trimming is SKIPPED entirely —
EVERY operative member contributes (`effective_k = n`); a top-`k` subset of
a tiny container is not a more robust statistic than the whole set, only an
arbitrarily truncated one. Zero operative members MUST raise, same as an
empty container.

**Conceptual depth `d` ∈ [0, 1]** (FORMULA
REWRITTEN after a review finding): a BLEND of (a) the
original LINK signals (incoming links from other concepts push toward
DEEP; plain-language/sense anchor links push toward SURFACE, damping the
deep pull) and (b) the entry's RELATIVE position in the NESTING (§13).
Computed from an ACTUAL GRAPH neighbourhood — the signal functions take a
graph (or the containment DAG), an entry id, and `r` ITSELF as input, not
pre-computed counts a caller could supply without ever consulting `r` (the
earlier version's defect: `r` was accepted but had no effect on anything).

**Link signals, graph-based.** `concept_link_signal(graph, entry_id, r)`
and `anchor_link_signal(graph, entry_id, r)` are each the SIZE of the
radius-`r` BACKWARD-reachable neighbourhood of `entry_id` over
`graph["concept_links"]`/`graph["anchor_links"]` (`{target: [direct
predecessor id, ...]}`) — the count of DISTINCT predecessor nodes reached
by following that kind of edge backward, up to `r` hops, excluding the
entry itself. This is what makes `r` OPERATIVE: a predecessor more than
`r` hops away is never counted, so an edit STRICTLY OUTSIDE the
radius-`r` neighbourhood leaves the signal — and so `d` — UNCHANGED; an
edit INSIDE it changes the count (`conformance/vectors/depth/`'s
`locality-*` vectors).

**Nesting signal, RELATIVE position, LOCAL to radius `r`,
replacing the earlier, UNBOUNDED version.**
`nesting_relative_position(dag, entry_id, r) = ancestors_within_r /
(ancestors_within_r + descendants_within_r)` over the containment DAG
(§13), counting ancestors and descendants ONLY within `r` hops — the
design requires d to be "computed only from the neighbourhood within
radius r", which the earlier, unbounded ancestor/descendant count did
not honour (an edit beyond `r` hops away in the containment DAG could
still change it). The range is `[0, 1]` INCLUSIVE, corrected from an
earlier, wrong "strictly between 0 and 1" claim: `0.0`
for a root-like node within the radius (descendants only, or no
ancestors/descendants within `r` hops at all); `1.0` for a leaf-like node
within the radius (ancestors only, no descendants within `r` hops). An edit
STRICTLY OUTSIDE the radius-`r` containment neighbourhood leaves this
signal unchanged; an edit INSIDE it changes the count
(`conformance/vectors/depth/`'s `locality-*` vectors cover both the link
signals and this nesting signal).

**Formula.** The earlier `min(count/saturation, 1)` squash is replaced
with `x/(x+s)` — a separate design choice (an earlier draft wrongly
called this "the owner's explicit fallback instruction"; it carries no
universal distinctness guarantee and is never attributed to the owner)
— STRICTLY MONOTONE on `x >= 0` for any fixed positive `s`:

```
deep_pull    = incoming_concept_links / (incoming_concept_links + link_scale)
surface_pull = anchor_links           / (anchor_links + anchor_scale)
raw_depth    = deep_pull * (1 - surface_pull)
nest_signal  = nesting_relative_position(dag, entry_id, r)      # already in [0, 1]
d = clamp01(round(
      (w_links * raw_depth + w_nesting * nest_signal) / (w_links + w_nesting),
      6))
```

`link_scale`, `anchor_scale`, `w_links`, `w_nesting` and `r` are ALL
resolution-profile fields (§16; the profile's own field NAMES,
`link_saturation`/`anchor_saturation`, are UNCHANGED — only their ROLE
changes, from a saturation cutoff to the monotone map's scale constant.
Defaults: 5, 2, 0.5, 0.5, 2 — unchanged from before. Grounded in the
originals' own saturating-ratio shape (`topo_depth =
min(bridge_in_degree/5, 1)`), specified as this
specification's own closed form.

**The four properties `d` actually has, REPLACING the earlier
"non-automorphic entries get different d" rule.**
That earlier rule came from an earlier design concept's own red-team
concession (Candidate B(5)), and a count-based `d` cannot satisfy it in
general: d carries NO universal distinctness guarantee; d is
deterministic in the radius-r signal tuple, equal tuples give equal d,
and d is monotone per signal. The automorphism-proxy machinery that
tried to approximate
the withdrawn rule (`neighbourhood_digest()`/`automorphic()`) is REMOVED.
`d` instead has exactly these four PROPERTIES:

  (i)   **Deterministic** in the radius-`r` signal tuple
        `(incoming_concept_links, anchor_links, ancestors_within_r,
        descendants_within_r)` plus the profile parameters.
  (ii)  **Equal tuples give equal `d`** (trivial for a deterministic
        function, stated because the withdrawn rule conflated it with
        (iv)).
  (iii) **Monotone per signal**: non-decreasing in `incoming_concept_links`,
        non-increasing in `anchor_links`, non-decreasing in `nest_signal`
        (and hence in the entry's relative nesting position).
  (iv)  **NO INJECTIVITY GUARANTEE ACROSS DIFFERENT TUPLES — a stated
        limitation, not a defect.** Two DIFFERENT signal tuples, or two
        genuinely different graph shapes, MAY produce the SAME `d`.
        `conformance/vectors/depth/` includes vectors that EXHIBIT this
        directly (two different anchor counts at zero incoming links
        giving equal `d`; two differently-shaped containment chains
        giving equal `d`), alongside the locality and monotonicity
        vectors for (i)/(iii).

**Depth quantiles inside a cube — IMPLEMENTED (fix round item 9,
replacing an earlier unimplemented normative sentence).**
`depth_quantiles(member_depths)` reports each member's own `d`'s quantile
RANK within its container's member set (`0.0` shallowest, `1.0` deepest;
ties share the lowest rank in the tied group) — a pure REPORTING
transform over already-computed `d` values, never a redefinition of `d`
itself. `nesting_level` and `d` remain SEPARATE fields.

See `src/five_d_nd/container.py` (position, match key),
`src/five_d_nd/depth.py` (d, depth_quantiles), `src/five_d_nd/profile.py`
(the resolution-profile wiring — `conceptual_depth_from_profile()`,
`trimmed_top_k_match_from_profile()`, `point_from_contributions_from_profile()`,
fix round residual), `conformance/vectors/container-average/`,
`conformance/vectors/trimmed-topk/`, `conformance/vectors/depth/`.

## §15 Derived views and staleness

Status: build list items 1 and 3. `position` (§11/§5), `match_statistic`
(§14), `d` (§14) and `nesting_level` (§13) are ALL VIEWS, named by a
`kind` field (fix round item 7: `kind` IN `{position, match_statistic, d,
nesting_level}`, a CLOSED enum, `VIEW_KINDS`) — each view carries a
`position_digest` (sha256 over the SORTED contributing claim-ids, the
SORTED embeds edges that fed it, and the resolution-profile digest, §16),
a `basis`, and a `stale` flag (`make_view()`/`view_violations()`). See
`schema/view.schema.json`, `src/five_d_nd/views.py`.

**Staleness propagation — an ORDERED list, TRUE topological order,
replacing an earlier unordered `set`.** A changed leaf claim or embeds edge marks its own view
stale, and every ANCESTOR on EVERY branch of the containment DAG (§13)
goes stale too — `propagate_staleness()` runs a full Kahn's-algorithm pass
restricted to the "affected" sub-DAG (every node reachable from the
changed set via the reverse embeds index, §13): a node is emitted only
once EVERY ONE of its own affected children has already been emitted
(never merely "at least one"), with ties among simultaneously-ready nodes
broken on lexicographic node-id order. A DIAMOND DAG (two paths converging
on one ancestor) marks that ancestor EXACTLY ONCE, strictly AFTER both
converging branches. **Re-derivation order is SPECIFIED**: a re-deriver
MUST process the returned list front-to-back — every node is preceded by
all of its own affected children, so a node's contributors are already
re-derived (or were never stale) by the time it is itself re-derived.

**Two staleness tiers** — a CLOSED enum, `vocabulary/staleness-tiers.json`:

- `"erasure"` is a HARD FENCE: a view fenced this way MUST NOT be served
  (beyond placement routing) until re-derived. Re-derivation MUST be
  BIT-IDENTICAL to a baseline that never contained the erased leaf — this
  specification states the BIT-IDENTITY REQUIREMENT itself and the fence
  it gates (`is_erasure_fenced()`, `erasure_bit_identical()`; the
  dedicated conformance vector ACTUALLY RE-DERIVES — it
  calls `container_position()` with and without the erased member and
  compares the two real results, not two hand-written float literals); the
  FULL erasure MECHANICS (the hash-chained serving log over salted
  digests, salt shredding, the ANN/cache erasure sweep) are a LATER
  stage of this build and are NOT specified here.
- `"ingest"` is a BOUNDED WINDOW: the last good view may be served WITH
  its digest and age attached, for as long as `age <=
  staleness_window_seconds` (a resolution-profile field, §16; the boundary
  `age == staleness_window_seconds` IS servable — a closed, inclusive
  window); past the window it is no longer servable and
  MUST be re-derived before being served again (`ingest_stale_window()`,
  which raises `ValueError` — never `KeyError` — on a malformed
  `view`).

**Hub fan-out debounce — TRAILING-EDGE FLUSH, replacing an earlier
silent drop.** A hub entry whose
incoming staleness-triggering events arrive faster than they can be
re-derived is COALESCED into bounded-rate propagation events — at most one
fired per `threshold` arrivals inside a rolling `window_seconds` — but
EVERY window segment now flushes exactly once when it CLOSES, whether by
reaching `threshold` (a coalesced burst) or by a gap/end-of-stream (a
TRAILING REMAINDER): a SLOW stream (every arrival more than
`window_seconds` apart) propagates ONCE PER EVENT, and a stream that never
reaches `threshold` still propagates its one remaining partial window
exactly once (`debounce()`) — never silently absorbed into a single
whole-node "at least 1" fallback, which is what the earlier version did.

See `conformance/vectors/staleness/`.

## §16 The resolution profile

Status: build list item 6. A DIGEST-PINNED JSON document holding every
tunable this round's formulas read as a parameter: `k` and `n_min` (§14),
`r` and the depth blend weights/scale constants (§14), `point_saturation`
(§11, owner decision D-a), `confidence_floor`, and
`staleness_window_seconds` (§15). Only `profile_id` (a non-empty string) is
REQUIRED; every other field is OPTIONAL and, when absent, takes the SAME
default the formula modules themselves use (`five_d_nd.profile.DEFAULTS` —
one named source of truth). `profile_digest(doc) = sha256(canonical_json(
resolve_profile(doc)))`, computed over the FULLY RESOLVED document, so two
profile documents that differ only in which fields they leave to default
produce the SAME digest when their resolved values are identical —
INCLUDING a field given as a zero-fractional float instead of a bare
integer, for EVERY numeric field this document has, not only the ones
declared "integer": `resolve_profile()` canonicalises EVERY numeric field
— `k`, `n_min`, `r`, the saturation constants, AND `confidence_floor`/
`staleness_window_seconds` (declared "a number", not "an integer", but
still subject to the exact same `0` vs `0.0` divergence), PLUS
`d_blend_weights`'s own two NESTED numeric fields (`links`, `nesting`) —
to a plain `int` whenever zero-fractional, before digesting. So
`{"k": 5}`/`{"k": 5.0}`, `{"confidence_floor": 0}`/`{"confidence_floor":
0.0}`, and `{"d_blend_weights": {"links": 1, "nesting": 0}}`/
`{"d_blend_weights": {"links": 1.0, "nesting": 0.0}}` each produce the
IDENTICAL digest within their own pair, not merely the identical validity
verdict. A genuinely fractional value (`0.05`) is, correctly, left
untouched. See `conformance/vectors/resolution-profile/*-int-vs-float-
same-digest.json` for the three pairs.

**`nesting_saturation` is REMOVED.** It was a
leftover from the earlier, absolute `nesting_level` signal; the current
nesting signal (§14's `nesting_relative_position()`) is an
`ancestors_within_r/(ancestors_within_r+descendants_within_r)` RATIO,
already bounded to `[0, 1]` by construction, and has never read any
saturation constant — the field was dead on arrival once the ratio-based
signal replaced the absolute one. Removed from `DEFAULTS`,
`KNOWN_FIELDS`, the schema, and the digest.

**Explicit field types** (same discipline as §9's own field-type table;
two things are tightened further, below):

- `profile_id`, `tiebreak_salt`, `schema_version`, `segmenter_digest`,
  `table_digest`: non-empty STRING.
- `k`, `n_min`, `r`, `link_saturation`, `anchor_saturation`,
  `point_saturation`: POSITIVE INTEGER (never a
  boolean) — **agreeing with the schema's own `"type": "integer"`
  semantics exactly**: a JSON NUMBER with zero fractional part (e.g. `5.0`)
  is ACCEPTED, same as the bare integer `5` (an earlier version of the
  code was Python-`int`-only and disagreed with the schema, which
  (per the JSON Schema spec) already accepts a zero-fractional float; both
  now agree. `5.5` and any boolean remain rejected by both).
- `d_blend_weights`: a mapping with EXACTLY `links` and `nesting` keys,
  both non-negative numbers, summing strictly positive (§14).
- `relational_suppression_scale`: a POSITIVE, FINITE number (never a
  boolean; NOT required to be an integer, unlike the saturation fields
  above) — the `s` in §8a's `relational_eff = relational_count * s /
  (s + n_other)` down-weighting formula, decided 2026-10-03. Default `1`.
- `confidence_floor`: a number in `[0, 1]`.
- `staleness_window_seconds`: a non-negative number. **A deliberate
  fail-closed TIGHTENING of a baseline-accepted value, recorded here
  explicitly:** NaN and `+-infinity` are JSON
  NUMBERS by this field's own declared type, and the code accepted both
  before a non-finite-weight check (`d_blend_weights`/
  `match_blend_weights`, §19) was extended to every bare numeric field
  this check shares logic with — `value < 0` alone never rejects either
  (every IEEE-754 comparison with NaN is False, and a lower bound alone
  never catches `+inf`). An earlier baseline accepted a NaN/infinite
  `staleness_window_seconds` is now rejected; see
  `docs/decisions/0007-clause-cue-layer-and-example-grammars.md` and
  `CHANGELOG.md` for the same note.
- **No OTHER field name is permitted**: an unknown
  field — a typo such as `"K"` for `"k"` — is now REJECTED outright, by
  both the code (`KNOWN_FIELDS`) and the schema
  (`"additionalProperties": false`), never silently ignored. A typo'd key
  would otherwise both (a) leave the intended field at its default,
  silently, and (b) pollute `profile_digest()`'s own canonical JSON with
  an unresolved extra key — rejecting it outright avoids both failure
  modes.
- `xref_resolver` (§8a.1): one of the two
  closed string values `"article-v1"` / `"shared-v2"`, selecting which
  cross-reference resolver a consumer dispatches to. **Deliberately NOT
  added to `DEFAULTS`** (unlike every field above): `resolve_profile()`
  merges a document onto `DEFAULTS` and digests the FULLY RESOLVED
  result, so widening `DEFAULTS` itself would change EVERY existing
  profile's own resolved document — and therefore its digest — even for
  a document that never mentions the new field at all. Added instead to
  `KNOWN_FIELDS` (so the field validates, round-trips through
  `resolve_profile()`'s generic top-level overlay, and is rejected on an
  unrecognised value) but left ABSENT from `DEFAULTS`: a profile
  document that never sets it resolves to the IDENTICAL dict, and
  therefore the IDENTICAL digest, it always had (verified directly:
  `minimal-valid-profile-id-only.json`'s own pinned digest is
  UNCHANGED). "Absent means `article-v1`" is asserted exactly ONCE, by
  the CONSUMING code's own dispatch (`resolved.get("xref_resolver",
  "article-v1")`), never by this module silently defaulting it. A
  profile that DOES set `"xref_resolver": "shared-v2"` gets a NEW,
  DISTINCT digest (its resolved document is now wider by one key) —
  exactly the `article-v1`/`shared-v2` split §8a.1 and the benchmark
  protocol need. This is a DELIBERATE DEPARTURE from the precedent set by
  `relational_suppression_scale`, which WAS added to `DEFAULTS` and
  did recompute every pre-existing
  resolution-profile vector's own pinned digest — that precedent is
  valid for a field whose DEFAULT value changes every resolved document's
  behaviour anyway (a new formula parameter with a real default), but is
  the WRONG precedent for a field selecting between TWO ALREADY-EXISTING
  code paths where one path (`article-v1`) must stay byte-identical,
  digest included, for every document that never opts in.

**The §16 "omitted means default" invariant, made explicit, and
EXPLICIT-default canonicalisation.** §16 has always
meant: two profile documents differing ONLY in whether a field is
present at its own default value, or absent altogether, MUST resolve —
and therefore digest — IDENTICALLY (`resolve_profile()`'s own docstring:
"two profile documents that differ only in which fields they leave to
default still produce the SAME digest"). Every field already in
`DEFAULTS` gets this for free, because `resolve_profile()` starts from
`DEFAULTS` and overlays `doc` on top — an explicit value equal to the
default overlays onto itself, a no-op. `xref_resolver` is deliberately
NOT in `DEFAULTS` (above), so it does NOT get this for free: without a
further step, `{"profile_id": "x"}` and `{"profile_id": "x",
"xref_resolver": "article-v1"}` would resolve to DIFFERENT dicts (one
lacking the key, one carrying it) and therefore digest differently,
breaking the invariant for this one field. `resolve_profile()` closes
this explicitly: AFTER the overlay, if the resolved document's own
`xref_resolver` equals its field default (`"article-v1"`), the key is
DELETED from the resolved document before canonicalisation/digesting —
so "never set" and "set to its own default" converge on the identical
resolved dict, and therefore the identical digest, while "set to
`shared-v2`" still diverges (verified directly:
`xref-resolver-explicit-article-v1-equals-omitted-digest.json`).

**`confidence_floor` is STAGE 2 (a residual item).** This profile
document carries the FIELD (a number in `[0, 1]`, validated the same as
any other field above) and the reference implementation stores
and digests it like any other profile value, but NEITHER the function that
APPLIES the floor (cutting a hop/path below it — "Hops are short and cut
by a confidence floor...") NOR a dedicated
conformance-vector family for that cut are built in this stage. Nothing in
`src/five_d_nd/` or `conformance/vectors/` reads `confidence_floor` for any
purpose beyond validating its own shape; it is a Stage 2 build list item
(§17's own "Stage 2 of this round" note has the full list).

Several profiles MAY coexist (build list item 5: an extraction-profile
upgrade — the segmenter/table digests this profile pins — is a
RE-DERIVATION event under a new profile digest, never a silent edit to an
existing one); profile VERSIONING/coexistence POLICY (which profile a
given corpus is served under, how a migration window works) is a hosting
concern this module does not itself specify.

This document has NO FIXED ENUM of its own (every field is numeric or a
free string) — recorded explicitly rather than silently omitted, per this
round's own "every new fixed enum needs a coverage test" rule: there is
nothing here for a generic coverage test to cover.

See `src/five_d_nd/profile.py`, `schema/resolution-profile.schema.json`,
`conformance/vectors/resolution-profile/`.

## §17 Conformance (coordinate round, stage 1)

An implementation conforms to THIS round's additions when it, IN ADDITION
to §10's existing criteria (all of which remain unchanged and still
apply):

10. Derives a point from an entry's raw contributions per §11's formula,
    and compares two points by cosine (§11);
11. Validates a triple's shape per §11, with exactly one dimension, and
    composes two edge weights multiplicatively (§11 — now NORMATIVE, not
    open);
12. Quantises leaf values to fixed point, sums as integers, and performs
    exactly one division/rounding at view materialisation, with ties
    broken by canonical salted claim-id order (§12);
13. Computes a container's member-set digest, rejects a nesting-edge
    write that would close a cycle, and maintains a reverse embeds index
    (§13);
14. Computes a container's position as the fixed-point average of its
    members (rank-sorted, permutation-invariant, below `n_min` too), its
    match key as a trimmed top-k over operative members (the `n < n_min`
    boundary, STRICT, is where trimming is skipped — `n == n_min` DOES
    trim), and an entry's conceptual depth `d` from an actual graph
    neighbourhood, LOCAL to radius `r` on BOTH the link signals and the
    nesting signal, per §14's blend formula, satisfying properties
    (i)-(iv) (deterministic in the signal tuple, equal tuples give equal
    `d`, monotone per signal, no injectivity guarantee across different
    tuples — a stated limitation);
15. Builds every derived view with a `kind`/`position_digest`/`basis`/
    `stale` flag, propagates staleness through the reverse index as a
    TRUE topological order (every node after all of its own affected
    children) without double counting on a diamond DAG, and honours the
    two staleness tiers (the ingest window's `age == window` boundary is
    servable) and the hub fan-out debounce contract's trailing-edge flush
    (§15);
16. Validates a resolution profile document per §16's field table
    (rejecting an unknown field; agreeing with the schema on a
    zero-fractional float) and computes its digest over the resolved
    (default-filled) document;

AND passes every vector under the FAMILIES this round adds:
`point`, `triple`, `fixedpoint`, `container-average`, `trimmed-topk`,
`depth`, `staleness`, `cycle-rejection`, `resolution-profile` — see
`tests/test_conformance.py`'s `FAMILIES` dict for the minimum count per
family, and `tests/test_fuzz_coordinates.py` for this round's own seeded,
mutation-based crash-safety fuzz over the profile/triple/point validators
(each checked against an independent ORACLE and, when `jsonschema` is
importable, the matching schema — fix round item 3) and the
container/depth/fixedpoint functions (no exception type is excused any
more).

**Two further owner decisions, fix round, 2026-10-01 (FIXED, implemented
verbatim):**

- **D-a — the point formula** (§11): replaces the earlier max-normalised
  formula with an independent, saturating `min(count/saturation, 1)` per
  dimension, with no special no-contribution branch (the all-zero point
  falls out of the formula itself) — see §11.
- **D-b — cycle rejection** (§13): requires an INCREMENTALLY MAINTAINED
  topological order (Pearce-Kelly class), not a full-graph reachability
  check per write, and the reference implementation now carries it — see
  §13.

**A misattribution, corrected here explicitly:** `d`'s distinctness
properties (i)-(iv), §14 — the earlier "non-automorphic entries get
different d" rule and the `x/(x+s)` squash were both previously,
WRONGLY, attributed to the owner in this document and in
`src/five_d_nd/depth.py`. Both are corrected: see §14's own "The four
properties `d` actually has" and "Formula" subsections.

**No P1-P3 (versum/schema PARITY) differential for this new
vocabulary — but an ORACLE/schema DIFFERENTIAL is still required and now
present.** §9's validator parity policy (P1-P3)
compares this specification's reference validator against VERSUM and
against a JSON Schema. Versum (`e416c81`) and loomground-factual
(`ebf9fe1`) have NO counterpart for a point, a triple, a container, a
trimmed top-k match statistic, conceptual depth, a derived view's
staleness tier, or a resolution profile — none of these concepts exist
upstream yet, so there is no P1-P3 VERSUM comparison to run. What IS
required, and now present: `tests/test_fuzz_coordinates.py` checks every
mutated profile/triple document against an INDEPENDENT ORACLE (a
from-scratch re-implementation of the same field-type table, written
without calling the module under test) and, when `jsonschema` is
importable, against `resolution-profile.schema.json`/`triple.schema.json`/
`point.schema.json` — a disagreement on either axis is a hard test
failure. This is this round's own single-implementation analogue of P1's
"never silently accept the wrong thing" (code vs. independent oracle, code
vs. schema), not a cross-REPOSITORY comparison, which genuinely has
nothing to compare against for this round's new vocabulary.

**Stage 2 of this round** (not built here) covers: erasure HYGIENE
mechanics (the hash-chained serving log, salt shredding, the ANN/cache
erasure sweep — §15 names only the bit-identity requirement and the fence
it gates); fingerprint MIGRATION (`fp_version`, the dual-read of the legacy
shape and `{index_key, match_key}`); the CONFIDENCE-FLOOR CUT FUNCTION
(§16 — the profile field exists and validates, but nothing applies it to
cut a hop/path yet, and there is no dedicated floor conformance family);
and the resolve-order/recall/cost-vector conformance family (nD filter,
nesting descent gated by `d` and the confidence floor, path-weight
ranking, the exact quantised stage).

## §18 EXAMPLE nD grammars (term, requirement)

**Status: owner-approved integration step, 2026-10-02.**
`src/five_d_nd/grammars/` ships TWO worked EXAMPLE nD grammars,
demonstrating §9's contract end to end — they are **NOT part of 5D**
(§1's scope is unchanged); either could be deleted without this
specification's own normative content changing at all. Both are ported
from a build comparison's own winning design (see ``docs/decisions/
0007-clause-cue-layer-and-example-grammars.md``): the winning candidate's own
lexical grammar, and its grafted requirement grammar.

**The term grammar** (`grammars/term.py`, candidate C). A deterministic,
domain-neutral lexical axis over entry spans: BM25 term weights
(standard Robertson/Sparck-Jones constants, never tuned against the GDPR
ground truth used to measure AUC). The vocabulary, document-frequency
table, and tokenizer are PINNED by a sha256 digest
(`build_term_profile`, via `five_d_nd.grounding.digest` — consumed, not
reimplemented) inside a resolution-profile-shaped document; the
published `NDSystem`'s `term_weight` axis names that digest as its
`ontology_version` (§9's own external-vocabulary field pair). The
grammar's descriptor (`build_descriptor`) binds `term_weight` →
`relational` — 5D's own algebraic identity and default (§3/§2) — so
attaching this grammar never perturbs 5D's existing structural signal;
the grammar's own topical axis lives entirely in its own
`axes`/`bindings` (§9), never in a sixth dimension.

**The requirement grammar** (`grammars/requirement.py`, graft D+). Some
obligations are a LIST of required elements, not a single predicate —
GDPR Art. 22(3) is the worked example (`requirement_rules.json`, pinned
by digest, `ruleset_digest`): once a trigger concept fires
(`automated_decision_making`), a use case is checked by LEXICAL ABSENCE
against every required concept (`human_intervention`,
`right_to_express_view`, `right_to_contest`). **The (trigger → required)
mapping is DATA, never code** — `check()` branches on nothing but the
loaded ruleset document; a new obligation is added by editing the JSON,
never by adding an `if`. A ruleset carries a **positive control**:
running the detector over the SOURCE PROVISION's own text (Art.
22(1)/(2)'s trigger language plus Art. 22(3)'s own safeguard language)
MUST return `all_present: True` — proving the detector can find what it
is supposed to find, not only report its absence
(`conformance/vectors/requirement-grammar/probe-old-positive-control.json`).

**THREE-STATE semantics, a design decision to stop the
negation arms race — `all_present` is a LEXICAL presence report, never
a compliance verdict.** Tightening clause-wide negation's
own exemption rules trades one class of false positive for a class of
false negative (an earlier clause-wide negation measured FN
11/30, FP 8/96 on a fresh probe set, against FN 6/30, FP 23/96 before
it — fewer false positives, more false negatives, not a net
improvement). Rather than another tightening pass, each required/trigger
concept's own state is now THREE-VALUED: `present` (some occurrence
fires with no negator in scope), `uncertain` (every occurrence that
fires IS negated — never silently collapsed to `present` or `absent`),
or `absent` (no occurrence fires anywhere). `check()` returns
`present`/`uncertain`/`missing` (the three states, over the rule's own
`required_concepts`), `triggered` (a trigger concept is `present`, never
merely `uncertain`), `trigger_uncertain` (the trigger's ONLY occurrences
were negated — routes to review rather than silently skipping the
check), `all_present` (`True` iff triggered, every required concept
`present`, and none `uncertain`), and `needs_review` (any required
concept `uncertain`, or `trigger_uncertain`). **A conforming consumer of
this grammar MUST NOT present `all_present: true` as a finding of legal
compliance** — see `src/five_d_nd/grammars/requirement.py`'s own module
docstring for the full scope note and its LIMITS list (paraphrases
outside the cue table, cross-sentence negation, a KNOWN, DOCUMENTED
lexical false positive this grammar does NOT chase — a server-log audit,
a customer survey, and ordinary litigation all lexically match the three
safeguard cues without describing an Art. 22(3) safeguard at all —
`conformance/vectors/requirement-grammar/
false-positive-lexical-paraphrase-documented.json`).

**Negation is CONSERVATIVE and SENTENCE-SCOPED — a further
design decision, replacing an earlier clause-scoped design (soft
boundaries, affirming double-negative overrides, forward-only
"without") after a held-out probe set showed those mechanisms
produced MORE confidently-wrong flips (20/45), not fewer, than an even
earlier all-or-nothing design (16/45) — every one of
them only ever moved a result TOWARD `present`. They are REMOVED, with
no replacement.** `present` requires a SENTENCE with NO token from the
digested negation lexicon after exact-phrase exemptions. **A
confidently-wrong `present` is possible ONLY when a negation is
expressed with words outside the lexicon, or across sentences** — any
negation-ish token ANYWHERE in the sentence makes EVERY cue in it
`uncertain`, never `absent`, never `present`; double negatives and
"cannot be refused" are `uncertain`, an accepted cost. The trigger
follows the SAME rule.

**A "sentence", replacing an earlier `.`/`;`/`:`
boundary.** `:`/`;` are NO LONGER boundaries at all (a held-out probe
showed either wrongly isolating an earlier-clause cue from a
later-clause negator, e.g. "Human intervention: none." and "The
following safeguards are not provided; human intervention, ..." —
removing them only WIDENS the negation scope, the conservative
direction). A sentence is now bounded ONLY by a `.`/`?`/`!` that is
ITSELF followed by whitespace then a capital letter or an opening
quote, or a line break — and a `.` that is an ABBREVIATION'S OWN period
is never that boundary.

**The abbreviation rule is CONSERVATIVE, not a closed word list,
relaxed further over successive checks.** A `.` is NOT a
boundary when the token immediately before it: (a) contains ANOTHER `.`
("U.S", "C.F.R", "e.g", "i.e" — their own internal periods); or (b) is a
token of at most 4 letters, CASE-INSENSITIVELY ("etc", "lit", "sec"),
OR a CAPITALISED token of at most 5 letters
("Corp", "Inc", "Ltd", "Dr", "Mr", "Mrs", "Ms", "St", "Art", "Arts",
"No", "Nos", "Co", "Admin", "Assoc" are the named examples — this cap
was raised from 4; the rule itself is GENERAL: any short
token qualifies, not only these); or (c) is on the pre-existing, closed
stem list (the fallback for a short, LOWERCASE stem longer than 4
letters rule (b) would miss — "para.", "cf.", "p."). Every one of these
only WIDENS the negation scope (fewer sentence boundaries, not more),
the conservative direction. **Two residual cases:**
- a TRUE sentence end right after a short capitalised token gets
  wrongly MERGED with the next sentence ("The firm is Acme Corp. Prices
  rose sharply." reads as one sentence) — ACCEPTED, because merging
  only ever widens a negator's own reach, never narrows it, so it
  cannot by itself produce a confidently-wrong `present`;
- a capitalised abbreviation of 6 OR MORE letters followed by a capital
  letter is NOT caught by rule (b) at all and, if also absent from the
  stem list, is treated as a REAL boundary, wrongly SPLITTING what
  should stay one sentence — this is NOT automatically safe (a wrong
  split can separate a cue from its own negator), the same class of
  risk as "a word outside the lexicon"; this narrows the gap
  (6+ letters, was 5+) but does not close it.

**The negation lexicon is broad, closed, digested, and now carries
FULL inflection groups, including
nominalisations** (den(y|ies|ied|ying|ial|ials), refus(e|es|ed|ing|al
|als), exclu(de|des|ded|ding|sion), and so on — see
`src/five_d_nd/grammars/requirement.py`'s own module docstring for the
complete list and the exact-phrase exemptions) — an earlier version of the
lexicon claimed "WITH inflections" but was missing most of them; a
held-out set of 51 fresh probes found 20 genuine defects from that gap.
Additional words OUTSIDE the original lexicon (decline, preclude,
reject, "in the absence of"/absent/absence, "dispense with", "phase
out", "out of the question") are added too — every addition only widens
a result toward `uncertain`, never toward `present`. Idioms ("hardly
ever") are deliberately excluded, named in LIMITS; "restrict(ion)" was
measured on the real GDPR corpus and deliberately NOT added — it
overwhelmingly names Art. 18/19's own "right to restriction of
processing", a legitimate safeguard, not a negation.

**Every group's bare form, audited.** A THIRD
held-out set (46 probes) found 11 defects in BARE forms the "full
inflection group" claim still missed — the suffix is now OPTIONAL on
exactly the four groups that lacked it (`abolish`, `prohibit`, `fail
...to`, `reject`; every OTHER group was audited and already had its
bare form). Four nominalisations were added: `unavailability`,
`impossibility`, `cessation` (all named explicitly), plus `abolition`
(found during the audit of `exclusion`/`prohibition`/`revocation`/
`suspension`/`denial`/`refusal`/`waiver`/`withholding` — the other eight
were already present).

Held-out flips: 0/45 on set 1 (2026-10-03); 4/51 on set 2;
8/46 on set 3; 0/45 on set 4 (2026-10-03 — every one of
set 4's 12 confidently-wrong flips is FIXED, zero remaining)
— not a guarantee against a FRESH held-out set,
which a later check may write. On the real 546-sentence GDPR
corpus: this example ruleset's cues occur in 11 sentences, 6 of them
negated, so `uncertain` fired 6 times (163/546 sentences, 29.9%,
contain an un-exempted negation token at all — up by exactly one
sentence from an earlier 162/546, from these lexicon additions);
6/99 GDPR articles get `needs_review: True` when checked
article-by-article. **This is stated as the measured number, not as an
unquantified "frequent"** — `uncertain`
fires on a SMALL minority of the corpus overall (11/546 sentences even
have a cue to begin with), but on OVER HALF of the sentences where this
ruleset's own cue DOES fire (6 of 11). Over-firing to `uncertain` is the
accepted cost of the conservative design — `needs_review` routes those
cases to a human — but the measured rate itself is what is stated here,
not a characterisation of it.

**CORRECTING a BROKEN earlier claim — "abolition" is NOT
`abolish` + `ion`.** `abolish(?:...|ion)?` spells
the non-word "abolishion", never the real word "abolition"; an earlier
claim that this covered "abolition" was simply wrong. "abolition"
is now its OWN lexicon alternative, independent of the `abolish` group.
Five more forms were added: `inability`, `discontinuance` (alongside
"discontinuation"), `prevention` (alongside "prevent"), `preclusion`
(alongside "preclude"), and a hyphen as an accepted "phase ... out"
separator (`phase-out`/`phased-out`). "failure of X to" is handled by
treating a BARE "failure" noun as its own negation-ish alternative,
rather than counting an arbitrary number of intervening words before
"to" — the chosen option between the two considered.

**PERFORMANCE — the run time grew SUPERLINEARLY on
long texts.** Every cue occurrence recomputed every sentence boundary
for the WHOLE text from scratch, and the abbreviation check scanned
from position 0 of the text every time. Measured: 31k chars took
3,723s before this fix (0.19s before the abbreviation
rule existed at all); the whole GDPR corpus as one text took ~400s.
Fix: `_sentence_boundaries` is cached (`functools.lru_cache`) so it is
computed ONCE per DISTINCT text, reused for every occurrence that text
contains; `_sentence_span` uses `bisect` for an O(log n) lookup instead
of a linear scan; the abbreviation token/stem search is anchored to a
40-character look-back window instead of scanning from position 0;
`_sentence_is_negated` is ALSO cached, so a sentence shared by many cue
occurrences (the accepted abbreviation-merge residual above) is scanned
once, not once per occurrence. Timing table after the fix (GDPR-corpus
-derived text at each size):

| chars | before | after |
|---|---|---|
| 8,000 | — | ~0.007-0.02s |
| 31,000 | 3,723s | ~0.02-0.03s |
| 183,000 (whole GDPR corpus, one text) | ~400s | ~0.08-0.16s |
| 200,000 | — | ~0.15s (performance-test bound: 2.0s) |

A deterministic test (`test_requirement_sentence_boundaries_computed_once_per_text_not_per_occurrence`)
guards the fix independently of wall-clock timing, by asserting
`_sentence_boundaries`'s own `cache_info()` records exactly ONE miss
for a fresh text regardless of how many cue occurrences it contains.

**41 distinct probe sentences are copied VERBATIM into
`conformance/vectors/requirement-grammar/probe-*.json`, PLUS 45
held-out probes into `heldout1-*.json` (provenance "Held-out set 1"),
PLUS 51 held-out probes into `heldout2-*.json` (provenance "Held-out
set 2"), PLUS 46 held-out probes into `heldout3-*.json` (provenance
"Held-out set 3"), PLUS 45 held-out probes into `heldout4-*.json`
(provenance "Held-out set 4")** — truth
judged independently of this grammar's own output, not merely
regenerated from it, each carrying a `truth` field (per-concept/trigger
ground truth, A/N/absent/not-mentioned). A trigger truth of "not
mentioned" is scored too: a false `triggered`
there is just as confidently wrong as one on a negated trigger. A
dedicated test
(`test_requirement_confusion_table_zero_confidently_wrong_flips`) asserts
the bar across ALL FIVE sets: zero confidently-wrong flips
beyond the documented, accepted exceptions named above — set 4 adds
NONE to that exception list; every one of its own flips is fixed. `uncertain`
against an affirmed truth, a lexical miss (reported `absent` because its
paraphrase is outside the cue table), or `uncertain` against a
negated/unmentioned truth, is acceptable and documented, never silently
"fixed" by chasing one more exception.

**One behavioural vector per `_NEGATION_RE` alternative** (corrected
in a follow-up). A mutation measurement found only 47 of 99 single-inflection alternatives
killed by BEHAVIOUR (the rest only by a DIGEST comparison, which
trivially changes whenever any lexicon text changes, proving nothing
about whether that specific word is actually checked anywhere).
`conformance/vectors/requirement-grammar/inflection-*.json` (130
vectors, generated from the regex structure, each a REAL English
sentence using the exact surface form) now give 127/130 alternatives a
vector that flips from negated to affirmed when THAT ONE alternative —
and no other — is removed, verified by a mutation run with the ruleset
digest PINNED to its original value and the dedicated digest-change
test deselected (so a kill can only come from a check() FIELD other
than the digest actually changing). **`can\s+not` IS individually
load-bearing — the original claim that it was structurally redundant
with `not` was FALSE.** It is isolated through the "not only ... but
also" exemption: "The data subject can not only obtain human
intervention but also contest the decision." — the exemption span is
anchored at the WORD "not", but the `can\s+not` alternative's own match
starts one word EARLIER, at "can", so it falls OUTSIDE the exemption
span while the bare `\bnot\b` alternative's match (starting at "not"
itself) falls inside it and is exempted; removing `can\s+not` alone
flips this exact sentence from `uncertain` to `present`
(`conformance/vectors/requirement-grammar/
inflection-single-can-not-via-not-only-exemption.json`). Only TWO
alternatives remain genuinely un-isolable: `under\s+no\s+circumstances`
and `in\s+the\s+absence\s+of`, STRUCTURALLY redundant with a shorter
alternative already in the lexicon (`no`, `absen(?:t|ce)` respectively)
— any sentence containing the longer phrase necessarily contains the
shorter word too, so no sentence can isolate the longer one's own
removal; this is stated here rather than silently papered over with a
sentence that does not actually prove what it claims to.

See `src/five_d_nd/grammars/term.py`, `src/five_d_nd/grammars/requirement.py`,
`src/five_d_nd/grammars/requirement_rules.json`,
`conformance/vectors/term-grammar/`, `conformance/vectors/requirement-grammar/`.

## §19 Matching: combining an nD term score and a 5D structural score

**Status: owner-approved integration step, 2026-10-02 — this
rule is NORMATIVE** (stated explicitly: this specification decides and
documents, rather than merely observes, the combination rule). The
underlying finding (``docs/decisions/
0007-clause-cue-layer-and-example-grammars.md``): 5D does NOT add measurable
retrieval signal on its own — it is the coordinate frame the nD grammars
attach to. This section is the rule for combining ONE artifact-match
score out of the term grammar's own score (§18) and a 5D structural
cosine (§11):

```
combined = (term_weight * term_score + structural_weight * structural_score)
           / (term_weight + structural_weight)
```

`term_weight`/`structural_weight` are a resolution-profile field (§16,
`match_blend_weights`), default `{"term": 0.7, "structural": 0.3}` — see
`five_d_nd.match.DEFAULT_MATCH_BLEND_WEIGHTS`.

**These weights are fixed A PRIORI and MUST NOT be tuned against the
GDPR ground truth** used to measure retrieval quality —
a named defect in a prior candidate design ("D+'s grid search leaked")
this rule deliberately avoids. The 0.7/0.3 split follows from a role
difference, independent of any corpus: the term grammar's BM25 score is
a direct lexical-overlap ranking function, the signal standard
information-retrieval practice (BM25/TF-IDF) treats as the primary
relevance signal for a text query; the 5D structural cosine is, by §9's
own "invariant for consuming languages", a DESCRIPTIVE coordinate-frame
signal — grounding/provenance information, never itself a ranking
function. Weighting the descriptive signal lower than the direct ranking
signal is this role difference, not a corpus fit. This realises the
"nD-first" design ADR 0007 calls for as a fixed
WEIGHT skew, not as a conditional branch or an evaluation order (a weighted
average has no evaluation order). Any re-measurement after this section
ships is a validation of the chosen defaults, not a search for better
ones.

**Explicit field types.** `term_score`/`structural_score`: a JSON number
in `[0, 1]` (never a boolean) — `five_d_nd.match.combine_scores` rejects
both out of range and raises `ValueError`, fail closed. `weights`, when
given, MUST be a mapping with exactly `term`/`structural` keys, both
non-negative numbers, summing strictly positive — the SAME shape §16's
`match_blend_weights` profile field validates.

See `src/five_d_nd/match.py`, `conformance/vectors/match-blend/`.

## §20 Conformance (fix round, integration step, stage 1)

An implementation conforms to THIS fix round's additions (§8a, §18,
§19) when it, IN ADDITION to §10's and §17's existing criteria (all of
which remain unchanged and still apply, including every
`assertoric-lowering` vector and the factual/versum differentials — this
round touches none of them):

17. Computes the clause-cue layer's own raw contribution counts (§8a),
    sums them with the UNCHANGED §8 assertoric contribution, and feeds
    the result through the UNCHANGED §11 point formula — `relational`
    counted only on the all-others-silent path;
18. Derives `+1 structural` per distinct cross-reference target AND an
    explicit `cross_references` link (§8a);
19. Validates and resolves the two new resolution-profile fields
    (`clause_cue_saturation`, `match_blend_weights`) per §16's field-type
    discipline — rejecting an unknown field, agreeing with the schema,
    and digesting the resolved document identically whether a weight is
    given as a zero-fractional float or a bare integer;
20. Combines a term score and a structural score per §19's fixed
    weighted-average formula, fail-closed on an out-of-range score or a
    malformed weights mapping;

AND passes every vector under the FAMILIES this fix round adds:
`clause-cues`, `match-blend`, `term-grammar`, `requirement-grammar` —
see `tests/test_conformance.py`'s `FAMILIES` dict for the minimum count
per family, and `tests/test_fuzz_coordinates.py` for this round's own
seeded, mutation-based crash-safety fuzz over `clause_cues` and `match`
(each checked against an independent ORACLE, same method as the
coordinate round's own profile/triple/point fuzz).

**No new fixed enum this round** (recorded explicitly, per the
coordinate round's own §16 precedent of stating this rather than
silently omitting it): `clause_cue_saturation` and `match_blend_weights`
are plain numeric/mapping fields with no closed vocabulary of their own;
the term grammar's `NDSystem` axis uses `value_type: "number"`, already
a member of §9's existing `_VALUE_TYPES` set; the requirement ruleset's
`obligation_id`/concept names are open strings, not enums. There is
nothing here for a generic enum-coverage test to cover.

**No P1-P3 (versum/schema parity) differential for §8a/§18/§19's own new
vocabulary, for the SAME reason §17 already states for the coordinate
round's own additions:** neither versum (`e416c81`) nor loomground-
factual (`ebf9fe1`) has a counterpart for a clause-cue raw-contribution
vector, a term-grammar profile, a requirement ruleset, or a matching
blend — none of these concepts exist upstream yet. §16's profile-document
P1-P3 differential (code vs. schema vs. oracle) DOES apply to the two new
profile fields, and is exercised exactly as it is for every other
profile field (`tests/test_fuzz_coordinates.py`).

**Corrections folded into §8a/§18/§19 above, listed here for
conformance:**

21. **§8a cue soundness.** `cross_reference_targets` now matches plural
    and ranged citations (`Articles 15, 16 and 17`; `Articles 15 to 20`,
    expanded inclusively, capped), and EXCLUDES a citation to ANOTHER
    instrument (`Article 8 of Regulation (EU) No 182/2011`, including the
    back-reference form `Article 5 thereof`) from ever becoming a GDPR
    cross-reference link. `within` counts as `temporal` only alongside an
    actual time expression; `means` counts as `structural` only in
    definitional form. Overlapping cue matches within one dimension are
    de-duplicated (one surface phrase counts once).
22. **Requirement grammar negation and paraphrase (§18).**
    `tag_concepts()` is negation-aware (a closed negator list, a bounded
    token window, the same clause) — a negated required concept counts
    as ABSENT and a negated trigger does not fire, from ONE shared
    mechanism. Paraphrase cues: human intervention ("human review", "a
    person reviews"), contest ("challenge the outcome/decision"), and the
    trigger ("fully automated").
23. **Requirement grammar fail-closed (§18).** `check()`/
    `concepts_present()` reject a bare string or other non-iterable
    `texts` with `ValueError`; `check()` validates its `ruleset` argument
    FIRST; `ruleset_violations()` cross-checks every concept name against
    the known concept cue ids. The concept cue table and negator list are
    now part of `ruleset_digest()` (via `cue_table_digest()`) — a cue
    edit changes the digest, exactly like a ruleset edit already did.
24. **§19/§16 fail-closed on non-finite values.** `combine_scores()` and
    the resolution profile's weight-mapping validator (shared by
    `d_blend_weights` AND `match_blend_weights`) now reject NaN/+-infinity
    explicitly — a bare `< 0` check does not catch either (every IEEE-754
    comparison with NaN is False, and a lower bound alone never catches
    `+inf`).
25. **Term grammar tokenizer pinning and weight normalisation (§18).**
    `build_term_profile()`'s own document now carries the tokenizer's
    pattern and stopword list, so a tokenizer edit changes
    `profile_digest` — closing a gap where an earlier draft of §18 CLAIMED
    this without a digested field to back it. `produce_term_claims()` no
    longer clamps a raw BM25 weight to `1.0` (measured on the real GDPR
    corpus: the clamp collapsed 11,150 of 12,115 claims, over 92%, to the
    identical value) — weights are normalised per document (divided by
    that span's own maximum raw weight) instead, preserving relative
    rank while staying in `[0, 1]`.

AND passes the EXTENDED vectors/tests under the SAME families (`clause-cues`,
`match-blend`, `term-grammar`, `requirement-grammar` — no family renamed
or added) plus a real, independently-typed cue-table oracle for the
`clause_cues` crash-safety fuzz (`tests/test_fuzz_coordinates.py`'s
`_clause_cues_fires_oracle` — a correction: an earlier draft of this
section claimed such an oracle existed before one actually did).

**Further corrections:**

26. **Requirement grammar: the field is `all_present`, not `satisfied`
    (§18, item 1(a)).** No deprecated alias is kept; every vector and
    every caller uses `all_present`. The module docstring states the
    normative bound explicitly: a conforming consumer MUST NOT present
    `all_present: true` as legal compliance.
27. **Requirement grammar: clause-scoped negation (§18, item 1(b)).**
    `tag_concepts()` scans the WHOLE clause (before AND after a cue,
    bounded by `;`/`.`/`:`) for a negator, replacing a previous
    6-token BEFORE-only window — verified against
    probe sentences (a negator several
    tokens away; a negator stated AFTER a long comma-list; new predicate
    negators with no "not"/"no"/"never" surface form at all). Three
    closed exemptions ("not only... but also", "without prejudice to",
    GDPR Art. 22(1)'s own "right not to be subject to" framing) and one
    double-negation override ("it is not true that there is no X"
    affirms X) keep this from over-negating.
28. **§8a cross-reference precision (item 2).** "of this/the Regulation"
    (bare) is the HOST instrument and stays internal; an external
    -instrument phrase must follow a citation DIRECTLY (an intervening
    relative clause no longer excludes it); "or" is accepted as a list
    connector; a trailing time-duration ("Article 12 to 30 days") no
    longer expands as a phantom article range.
29. **§8a `means` definitional precision (item 3).** Re-keyed on a
    preceding closing quote within 30 characters of `means` (covers a
    short qualifier between the quoted term and `means`) — verified
    against the real GDPR Art. 4 text: all 26 definitional uses fire, all
    4 non-definitional uses stay excluded.
30. **§18 term grammar: the pinned tokenizer is ENFORCED (item 5).**
    `bm25_vector()` rejects, with `ValueError`, a profile whose own
    `token_pattern`/`stopwords` do not match this module's CURRENT
    tokenizer — digesting the tokenizer (the previous round's own fix) is
    only useful if a consumer actually checks it.
31. **§16 resolution profile: a non-finite WEIGHT SUM is rejected (item
    6).** Two individually-finite weights (e.g. `1e308` + `1e308`) can
    still overflow to a non-finite sum; `profile_violations` now agrees
    with `match.combine_scores`, which already rejected this.

AND the match/clause-cue fuzz oracles are now INDEPENDENT of the module
constants they check (the match-weight oracle uses its own literal
default pair rather than reading `match.DEFAULT_MATCH_BLEND_WEIGHTS`; the
clause-cue oracle's fragment pool now includes one host-instrument and
one external-instrument citation, independently re-deriving the same
exclusion items 2/3 above add).

**Further corrections:**

32. **Requirement grammar: THREE-STATE semantics (§18, item 1).**
    `present`/`uncertain`/`missing` replace a binary present/absent;
    `triggered`/`trigger_uncertain`/`all_present`/`needs_review` as
    described in §18 above. Clause-scoped negation gains soft
    boundaries (`, but`, `although`, `, whereas`, `and there is`/`and
    there are`, a bare `if`/`where`), new negators (`neither`/`nor`,
    a generic `n't` contraction, `unavailable`, `abolished`, `lack of`,
    `prohibited`), a tightened Art. 22(1) exemption (requires "the
    right" to literally precede "not to be subject to"), new affirming
    double-negative overrides ("in no case... denied", "cannot be
    refused", "it is not the case that no..."), and a FORWARD-ONLY rule
    for "without" (negates what follows it, never what precedes it,
    within the same clause) — fixing both of this round's own named
    verbatim failures. Dead negator phrases already covered by a
    shorter pattern are removed from the digest.
33. **§8a cross-reference precision, widened (item 4).** Trailing
    bracketed sub-groups ("(1)(b)") are skipped before the
    external-instrument check; "Council"/"Delegated"/etc.-qualified
    Regulations, "TFEU"/"TEU", and "of the Charter" are recognised as
    external; a "to"-range is a range ONLY for the plural "Articles"
    form (singular "Article 12 to 30" is NOT a range — `[12]`).
34. **§8a quote-means precision (item 6).** Requires a GENUINE
    opening-then-closing quoted term, not a bare possessive apostrophe
    ("the data subject's rights", "the processor's means" no longer
    falsely fire).
35. **§8a relational down-weighting — DECIDED 2026-10-03,
    resolving the previously flagged OPEN OWNER
    DECISION.** `relational_eff = relational_count * s / (s +
    n_other)`, `s` = the new resolution-profile field
    `relational_suppression_scale` (default `1`) — see the §8a table's
    own full account above.

**Further corrections:**

36. **Requirement grammar: CONSERVATIVE, SENTENCE-SCOPED negation,
    replacing an earlier clause-scoped design entirely (§18).** An
    earlier design's soft boundaries, affirming double-negative overrides, and
    forward-only "without" are ALL REMOVED, with no replacement — a
    held-out probe set (45 fresh sentences) showed they produced
    MORE confidently-wrong flips (20/45) than the ORIGINAL all-or-nothing
    design two rounds earlier (16/45), because every one of them only
    ever moved a result TOWARD `present`. `present` now requires a
    SENTENCE (bounded only by `.`/`;`/`:`/a line break) with no token
    from a broadened, digested negation lexicon after exact-phrase
    exemptions; any negation-ish token anywhere in the sentence makes
    EVERY cue in it `uncertain`, never `absent`, never `present`. Held
    -out flips: 0/45 (2026-10-03).
37. **§8a cross-reference precision, widened again (item 11).** The
    qualifying-word slot before "Regulation" now accepts MULTIPLE words
    ("Commission Implementing Regulation", "European Parliament
    Regulation"), not only one; `cross_reference_targets` takes an
    optional `host_instrument_number` so a citation naming the HOST
    instrument's own number ("Article 45 of Regulation (EU) 2016/679")
    resolves internally, `[45]`, rather than being excluded as external.
38. **RL6: `relational_effective` scale validation, confirmed and
    directly tested (item 8).** The existing `scale <= 0` check already
    rejected zero, negative, non-finite, and bool values; a direct test
    (`test_relational_effective_rejects_bad_scale`) now pins this rather
    than relying only on the resolution-profile layer above it.
39. **Spec drift fixes (item 9).** §8a's "Explicit field types" now
    states `relational` is a non-negative NUMBER (fixed-point), not an
    integer count, matching `relational_effective()`'s own fractional
    output; the sentence describing `relational_eff`'s rounding now says
    the RESULT is quantised, not `s` (the scale parameter itself is never
    rounded).

**Further corrections:**

40. **Requirement grammar: full inflection groups + new outside words.**
    A held-out set of 51 fresh probes found 20
    confidently-wrong flips caused by missing inflections (an earlier
    lexicon claimed "WITH inflections" but mostly lacked them); every
    stem is now a full group including nominalisations, and six new
    words are added. "hardly ever" (idiom) and "restrict(ion)"
    (measured on the real corpus, overwhelmingly Art. 18/19's own
    legitimate "right to restriction of processing") are deliberately
    NOT added.
41. **Requirement grammar: `:`/`;` removed as sentence boundaries.**
    Replaced by a `.`/`?`/`!` followed by whitespace plus a
    capital letter or opening quote, or a line break — with a known
    -abbreviation exception ("Art.", "No.", "Nos.", "e.g.", "i.e.",
    "para.", "cf.", "p.") so an abbreviation's own period is never that
    boundary.
42. **Requirement grammar: claims now match the measurement.**
    The module docstring and this section both state the measured
    numbers (11 sentences with a cue, 6 negated, 161/546 with an
    un-exempted negation token, 6/99 articles `needs_review`) rather
    than an unquantified "frequent".
43. **§8a `host_instrument_number` is caller-supplied document metadata,
    never a profile field.** Threaded as an optional keyword
    through `cross_reference_links`, `clause_cue_contributions`,
    `combined_contributions`, and `clause_cue_point`.

**Further corrections:**

44. **Requirement grammar: every lexicon group's bare form, audited.**
    A THIRD held-out set (46 probes) found 11 defects in
    bare forms the "full inflection group" claim still missed. Every
    group in `_NEGATION_RE` was audited for the gap; exactly four had
    it (`abolish`, `prohibit`, `fail ... to`, `reject`) and are fixed by
    making their suffix optional.
45. **Requirement grammar: four more nominalisations.**
    `unavailability`, `impossibility`, `cessation` (named explicitly),
    plus `abolition` (found during the audit of `exclusion`/
    `prohibition`/`revocation`/`suspension`/`denial`/`refusal`/
    `waiver`/`withholding` — the other eight nominalisations were
    already present).
46. **Requirement grammar: the abbreviation rule is CONSERVATIVE, not a
    closed stem list.** A `.` is not a boundary when the
    preceding token (a) contains another `.`, or (b) is a capitalised
    token of at most 4 letters (a GENERAL rule, not an enumerated
    list), or (c) is on the pre-existing stem list (the fallback for a
    short lowercase stem). The residual, accepted cost: a true sentence
    end right after a short capitalised token gets wrongly merged with
    the next sentence — acceptable, since merging only ever widens.
47. **§8a: a vector + direct test for `cross_reference_links`'s own
    `host_instrument_number` forwarding.** Kills a mutation test (the
    mutant that silently dropped the keyword before calling
    `cross_reference_targets`).
48. **Requirement grammar: trigger truth "not mentioned" is now scored
    too.** The confusion-table test previously only checked a
    negated ("N") trigger truth for a false `triggered`; a truly
    unmentioned ("-") trigger truth gets the same check now.
49. **Spec drift fix.** The "uncertain is frequent on real
    legal text" claim next to the corpus measurement is replaced with
    the measured numbers stated plainly, with no unquantified
    characterisation attached.

**Further corrections:**

50. **PERFORMANCE: superlinear run time fixed.** Sentence
    boundaries are now cached per text (`functools.lru_cache`) and
    looked up with `bisect` rather than recomputed and linearly
    rescanned per cue occurrence; the abbreviation token/stem search is
    anchored to a 40-character look-back window instead of scanning
    from position 0; `_sentence_is_negated` is also cached. 31k chars:
    3,723s before, ~0.02-0.03s after; the whole 183k-char GDPR corpus
    as one text: ~400s before, ~0.08-0.16s after. A wall-clock
    performance test (200k chars under 2s) and a deterministic
    cache-hit-count test both guard the fix.
51. **A BROKEN earlier claim is corrected.** "abolition"
    is its own lexicon alternative — `abolish(?:...|ion)?` spelled the
    non-word "abolishion", never "abolition". Five more forms added:
    `inability`, `discontinuance`, `prevention`, `preclusion`, and a
    hyphen-separated "phase-out"/"phased-out"; "failure of X to" is
    handled by treating a bare "failure" as negation-ish on its own.
52. **Abbreviation rule (b) relaxed (item A).** Case-insensitive for a
    token of at most 4 letters ("etc.", "lit.", "sec."); the
    capitalised-only cap raised to 5 letters ("Admin.", "Assoc.").
    LIMITS now names the residual: a capitalised abbreviation of 6+
    letters followed by a capital letter is not caught by either cap.
53. **130 behavioural vectors, one per `_NEGATION_RE` alternative**
    (corrected in a follow-up). Closes a measurement gap:
    only 47 of 99 single-inflection alternatives were previously killed
    by BEHAVIOUR rather than by a digest comparison alone. 127/130
    confirmed individually load-bearing via a digest-pinned mutation
    run. The original claim that `can\s+not` was structurally redundant
    with `not` was FALSE — it is isolated through the "not only ... but
    also" exemption (the exemption span is anchored at "not", one word
    AFTER where `can\s+not`'s own match starts); only 2 alternatives
    (`under\s+no\s+circumstances`, `in\s+the\s+absence\s+of`) remain
    genuinely structurally redundant with a shorter alternative already
    in the lexicon, un-isolable by any sentence.
54. Held-out set 4 (45 probes, `heldout4-*`, provenance "Held-out
    set 4") copied verbatim; all 12 of its own confidently
    -wrong flips are fixed, zero remaining, and NONE are added to the
    accepted-exception list.

AND passes the probe-* vectors — 41
distinct probe sentences, copied verbatim, PLUS 45
held-out probes (`heldout1-*`, provenance "Held-out
set 1"), PLUS 51 held-out probes (`heldout2-*`, provenance
"Held-out set 2"), PLUS 46 held-out probes
(`heldout3-*`, provenance "Held-out set 3"), PLUS 45
held-out probes (`heldout4-*`, provenance "Held-out
set 4") — via a dedicated confusion-table test
(`test_requirement_confusion_table_zero_confidently_wrong_flips`,
scored by CONFIDENTLY-WRONG, not by a naive false-negative count,
against zero UNEXPECTED flips beyond the documented, accepted
exceptions — the "hardly ever" idiom, six out-of-lexicon synonyms, and
the cross-sentence pattern) and a property/oracle test for
`relational_effective`
(`test_relational_effective_agrees_with_an_independent_oracle_and_properties`).

## §20a Conformance

An implementation conforms to this addition (§8a.1 — the shared
cross-reference resolver) when it, IN ADDITION to §10/§17/§20's existing
criteria (all unchanged, including every `clause-cues` vector built for
`article-v1`):

55. Keeps `cross_reference_targets`/`cross_reference_links`
    (`article-v1`) byte-identical for every existing caller and vector —
    this addition adds a NEW function, `resolve_references`, never edits
    the old one.
56. Resolves EXTERNAL citations to `(instrument, pinpoint)` per R7 (§8a.1)
    across EU/UK/US/DE drafting shapes, and INTERNAL references across
    every numbering family §8a.1 lists, including ranges/plurals/or-lists
    (one target per expanded member, `expanded_from` set) and relative
    references resolved against a caller-derived `enclosing_unit`.
57. Implements R1-R7, exactly as mapped in §8a.1 — a bare self-reference is never an item
    (R1); a quoted-amending pinpoint is classified by what it designates
    (R2); "this Section/Chapter/Title/Part" is internal to that unit
    unless it IS the whole host (R4/R5); a "So in original" footnote is
    read literally and flagged `ambiguous_reference` (R6); an EXTERNAL
    reference's `targets` is always `[]` and `external_instrument` is
    never null (R7).
58. Validates and resolves the new resolution-profile field
    (`xref_resolver`, `"article-v1"` | `"shared-v2"`) per §16's
    field-type discipline, WITHOUT changing the resolved document (and
    therefore the digest) of any profile document that does not set it —
    checked directly by `two-profiles-same-resolved-fields-same-digest`
    -style vectors and by comparing `minimal-valid-profile-id-only.json`'s
    own pinned digest before and after this addition (unchanged).

AND passes every vector added here:
`conformance/vectors/clause-cues/xref-v2-*.json` (every numbering family,
external-with-pinpoint, anaphora including "that Regulation"/"thereof",
R1/R2/R4/R5/R6, ranges, or-lists, plurals, NBSP, hard negatives, and a
savings-clause example), plus
`conformance/vectors/resolution-profile/xref-resolver-field-*.json`.

**No P1-P3 (versum/schema parity) differential, for the same reason
§20's own note gives:** neither versum nor loomground-factual has a
cross-reference-resolver counterpart. The resolution-profile schema
(`schema/resolution-profile.schema.json`) DOES gain the new field's
enum, checked by the existing differential test exactly as every other
profile field is.

**Benchmark pinning.** The signed 5D benchmark (benchmark protocol §8)
pins a resolution profile with `"xref_resolver": "shared-v2"`
(`888f219701d54ab5c592b803fd11d06cb145ad60f5fda26d05949ea3ec3256c3`) for
BOTH arms — see `_results/xref-resolver/harness/bench-profile.json` (the
benchmark harness's own copy; not part of this package) and
`conformance/vectors/resolution-profile/xref-resolver-field-shared-v2-accepted.json`
for the same digest, recorded as a conformance vector too.

### §20a.1 Resolver naming and anaphora corrections

Folded into §8a.1/§16 above; listed here for conformance, per the same
discipline §20's own conformance items use:

59. **Dispatch now fails CLOSED and counts DISTINCT targets only.**
    `_xref_count_and_objects` raises `ValueError` on an unrecognised
    `xref_resolver` value; `shared-v2` counts distinct target
    pinpoints/instrument-pairs only — a repeated identical citation
    contributes `+1 structural` and ONE link, never one per occurrence.
60. **R1 by NAME, not only by EU number.** "`<chain> of/to the <host's
    own name>`" (e.g. UK "paragraph N of Schedule M to the Data
    Protection Act 2018" inside that Act's own file) resolves INTERNAL
    the SAME way the EU "Article N of Regulation (EU) `<host number>`"
    case already did (`_loose_name_match`, casefolded, a leading "the "
    stripped). A LATER anaphoric "of/to that Act"/standalone "that Act"
    is resolved INTERNAL too whenever the host was named MORE
    RECENTLY, BY POSITION, than any genuinely external instrument —
    never defaulting to EXTERNAL merely because the surface word is
    "Act"/"Regulation". Verified by a property test over EVERY sentence
    of all 8 source texts: ZERO overlapping output spans
    (`_results/xref-resolver/harness/test_no_overlap.py`).
61. **R4 resolves to the ANCESTOR AT THE NAMED LEVEL**, not the
    Article/Section-level `enclosing_unit` — `enclosing_units_at`
    returns an independent ancestor chain (`chapter`/`section` for EU;
    `part`/`chapter`/`schedule` for UK), and "this Chapter"/"this
    Section"/"this Part" builds an outer-first pinpoint from it. "this
    title" is EXTERNAL (R1/the contract's own US Code example), never
    R4-internal; R5 (the named unit IS the whole host) still wins first.
62. **Outer-first nested chains** written inner-first in the text
    ("Section 3 of Chapter IV", "Chapter 4 of Part 5", "paragraph 9 of
    Part 3 of Schedule 3") are reformatted outer-unit-first.
63. **Plurals/ranges beyond EU Articles**: "sections 3 to 5", "sections
    14 and 15", "paragraphs 1 and 2"/"1 to 3", "§§ 3 bis 5"/"§§ 3 und 4"
    (German plural sign, "bis"/"und" connectors) — one target per
    member, `expanded_from` set, via a shared generic list/range
    expander (`_expand_generic_list`).
64. **Anaphoric EXTERNAL with its own pinpoint** — "Article 5 of that
    Regulation", "Articles 55 or 56 of that Regulation", "section 406 of
    that Act" — is ONE EXTERNAL reference per listed member (never an
    INTERNAL pinpoint plus a separate EXTERNAL mention), instrument the
    antecedent, `external_target` the member's own pinpoint.
65. **R2 extended to UNQUOTED amending chapeaux**: "In Regulation (EU)
    2018/1139, Article 17 is replaced by the following:" designates
    Article 17 to 2018/1139 even with no quote marks at all, via a
    chapeau-span detector parallel to the quote-span one (and deferring
    to R1 when the chapeau names the host itself).
66. **The quote-span detector excludes apostrophes**: a straight `'` is
    an opening/closing quote mark only when NOT adjacent to a letter on
    the quote side (never a possessive/contraction apostrophe);
    typographic quotes (`'…'`/`"…"`) are unambiguous and always count.
67. **TFEU/TEU's spelled-out names**, German statute names (genitive
    "der"/"des" plus a compound or multi-word Title-Case run ending in
    "-gesetz(es)"/"-gesetzbuch(es/s)"/"-ordnung"/a standalone capitalised
    suffix word), and a wider closed set of statute-KIND words beyond
    "Act" (Code/Ordinance/Statute/Law/Convention/Treaty, each with a
    trailing year) are EXTERNAL — closing the §8a.1 KNOWN LIMIT that
    previously stated (incorrectly) that an unrecognised shape was
    "under-recall only, never a wrong name": for every shape added here,
    that claim is now true; shapes outside even this widened set
    remain the stated, narrower limit. **Accuracy note:** an earlier,
    wider German statute pattern, together with an unrelated bare
    "Convention"/"Protocol"/"Accord" alternative (§20a.2 item 80), had
    reopened the "never a wrong name" claim — the bare alternative
    produced WRONG names on ordinary prose, and the German pattern's own
    missing word-boundary/empty-stem guards produced wrong names on "im
    Sinne des Gesetzes"-shaped prose too. Both are removed/tightened:
    the bare alternative is gone, the German pattern is tightened, and
    the count is re-measured at 0 generic-single-word EXTERNAL names
    over all 12 sources (§8a.1's own KNOWN LIMIT paragraph has the
    count). This item's claim holds for item 67's own shapes.
68. Several formatting bugs, fixed with their own vectors: the pinpoint
    PREFIX now follows the numbering FAMILY, not the literal keyword
    ("section 6502(b)(1)(A)" in the US family -> `"§ 6502(b)(1)(A)"`);
    `_format_schedule_paragraph`'s number extraction no longer scrapes
    digits out of a sub-pinpoint bracket; `_format_annex_pinpoint` keeps
    "point" lower-case; the DE chain pattern requires "Abs."/"Absatz" so
    it never mis-claims a bare US "§ N" chain first.
69. **`external_target`** — a PARSED pinpoint field on every EXTERNAL
    reference (the "(instrument, target provision)" requirement),
    `None` when no pinpoint chain could be parsed. The `cross_references`
    link object for an EXTERNAL reference is now `"<instrument>|
    <external_target or literal>"`, not `"<instrument>|<literal>"`.
70. **R6's editorial-note bracket** ("`[So in original. Probably should
    be section 5(a)(3).]`") is excluded ENTIRELY — any reference whose
    span falls inside the bracket is dropped, never emitted (never `+1
    structural`); only the REAL literal reference in the operative
    sentence, outside the bracket, is an item, flagged
    `ambiguous_reference`.
71. `profile_violations()` REPORTS (never raises) on a non-string
    `xref_resolver` value (an unhashable value no longer hits a bare
    frozenset membership test unguarded).

AND passes every vector added here
(`conformance/vectors/clause-cues/xref-v2-*.json`, covering all three
resolver corrections passes, plus the pre-existing `clause-cues/` family)
plus the harness's own
`test_no_overlap.py` (zero violations over all 8 sources) and
`test_score.py` (the scorer's own self-test, synthetic fixtures only).

### §20a.2 German supplement and naming corrections

**German supplement.** The resolver's DE-family naming rules (R7-DE's
nominative-form rule, "der/des/dem" article handling, the
EU-act-literal-ends-at-its-number cross-vertical rule applied in
German, the statute-kind word set) follow the German-supplement
contract (sha256
`6c4bf7232367169c71cf34baf13bca4deabe916f4c297de2fac966eb4f831709`)
§1/§2 (external naming, nominative conversion) only — §0
(non-operative-zone detection), §3-§8 (literal extent, pinpoint
depth/Satz-counting, elided-parent expansion, list-splitting) and
R-DE1-5 are NOT implemented (no DE gold exists to score against; the
supplement's own deep structural rules are a KNOWN LIMIT, stated
rather than silently assumed).

72. **R1 by-name/by-number are INDEPENDENT checks**: a chain followed
    by ", of"/"of" + the host's own
    name OR number resolves INTERNAL either way, never only when the
    FIRST-tried check happens to match; tolerant of a comma before
    "of" ("Chapter IV, Section 3, of Regulation (EU) <host number>").
73. **Anaphora resolves to the most recent INSTRUMENT-DESIGNATION
    event**: "that X"/"thereof" never resolve to a plain internal
    citation (e.g. "Article 7") that
    designates no instrument at all — only an EXTERNAL reference
    already in `out`, or an INTERNAL reference whose own literal
    contains the host's name, counts as a designation.
74. **R4's ancestor chain is THREADED through the whole pipeline**
    (`resolve_references`, `_xref_count_and_objects`,
    `clause_cue_contributions`, `combined_contributions`,
    `clause_cue_point`, `cross_reference_links`, both `_from_profile`
    wrappers, and the benchmark harness's own `predict_v2`), and
    `enclosing_units_at` now RESETS every lower level when a higher
    one opens (a new CHAPTER clears Section; a new PART clears Chapter
    and Section; entering a SCHEDULE clears the main-body Part/Chapter
    and starts the Schedule's OWN Part/Chapter afresh). When a level
    cannot be derived, R4 emits NO item (never a wrong/bare guess).
75. **A plural/ranged/
    anaphoric chain followed by one instrument (EXTERNAL) or the host's
    own name/number (INTERNAL) is ONE reference — "Articles 55 to 58
    of that Regulation", "sections 61 to 66 of the Example Security Act
    2001", "§§ 3 bis 5 des Strafgesetzbuches" are each ONE EXTERNAL
    reference; "sections 121 and 122 of the Data Protection Act 2018"
    (host) is ONE INTERNAL reference with every member as its own
    target. Plural Schedules/Annexes ("Schedules 9, 10 and 11",
    "Annexes III and IV") now expand the same way. KNOWN LIMIT:
    "Sections 7, 8 and 9 of Chapter III" still resolves as TWO
    references (the plural section list, and
    a separate bare "Chapter III" mention) rather than ONE nested
    reference with targets "Chapter III, Section 7/8/9" — the
    outer-first nested-PLURAL case is not implemented.
76. **"section N of this title"** (M8) is ONE reference: INTERNAL (no
    separate "this title" item) when `host_section_numbers` says N is
    in this file; otherwise EXTERNAL to `host_title_instrument` (or the
    literal "this title" when the title number is not known).
77. **The amending chapeau span ends at ";" too** (not only "."), and
    an EXPLICIT "of this Regulation/Directive/Act" immediately after a
    citation overrides BOTH the chapeau and the quote-span reroute —
    the text's own, more specific self-naming always wins (M9).
78. **"this section" (lower-case) is R1-style deictic, not an item** —
    distinct from "this Section" (capitalised, the EU/UK "group of
    Articles" sense, R4) by the ORIGINAL case of the matched word.
79. German nominative conversion (`_de_nominative`) undoes the head
    noun's case inflection only ("des Bürgerlichen Gesetzbuchs" ->
    "Bürgerliches Gesetzbuch", "des BSI-Gesetzes" -> "BSI-Gesetz"); a
    "der/des/dem Verordnung/Richtlinie (EU) …" keeps the EU act's own
    literal number, per the cross-vertical "ends at the last character
    of its number" rule, with only the leading German article dropped.
80. **A bare capitalised "the Convention"/"the Protocol"/"the
    Accord" is NOT recognised as EXTERNAL** — an earlier version of
    this item claimed it was; that was wrong on the benchmark's own
    sources: the bare alternative fired on
    ordinary prose with no citation at all ("Convention rights",
    "Transmission Control Protocol/Internet Protocol", "non-Convention
    countries", "Refugee Convention" — 57 spurious hits on uk-dpa2018
    alone) and truncated genuinely NAMED treaties to their bare generic
    type word — "European Convention for the Protection of Human
    Rights and Fundamental Freedoms" (gdpr) -> "Convention"; "Protocol
    No 21" (ai-act) -> "Protocol" — a WRONG name, not the claimed
    narrower recognition. The bare alternative is REMOVED; a
    treaty-type word is EXTERNAL only when genuinely NAMED (a
    Title-Case qualifying phrase attached), cited as "Protocol No N",
    or pinpoint-attached ("Article N of this/the Convention/Protocol/
    Treaty/Accord", resolved per R1/R7 — see §8a.1's own KNOWN LIMIT
    paragraph for the corrected rule and the measured count). The
    US-style "the X Act (N U.S.C. … et seq.)" parenthetical-
    codification half of this item is UNAFFECTED by this correction and
    remains as originally stated.
81. **US host metadata root-cause fix**: the benchmark harness no
    longer sets `host_instrument_name` to the US TITLE number
    ("15 U.S.C.") for `us-coppa`/`us-s230` — the host is the one
    chapter/section set actually in the file, not the whole title; the
    title number is kept ONLY as `host_title_instrument`, used solely
    for "this title"'s own EXTERNAL naming (item 76).
82. `profile_violations()` is unaffected here (already fixed
    earlier); a dedicated resolution-profile vector now exercises a
    non-string `xref_resolver` value directly.

**KNOWN LIMIT (stated, not optimized): quadratic-ish time on repeated
large-file calls.** `enclosing_unit_at`/`enclosing_units_at` each
re-scan `source_text` from its own start on EVERY call; a caller
invoking either once per sentence over one large file (as the
benchmark harness and `test_no_overlap.py` both do) pays O(n) per call,
O(n·k) total for k sentences — on a ~1.1MB source with several thousand
sentences this is measured at several minutes for the full 8-source
no-overlap property test. Not optimised (no caching/bisect
index added); a caller with its own performance budget should memoise
the heading-position lists per source text itself.

See `src/five_d_nd/clause_cues.py`,
`conformance/vectors/clause-cues/xref-v2-*.json`,
`_results/xref-resolver/harness/test_no_overlap.py`,
`_results/xref-resolver/harness/test_score.py`.

## §21 Typed Statements (typed-triple layer)

**Status: the codebook and gold come FIRST, the deterministic extractor
SECOND.** This section defines the DATA MODEL and the codebook's own
worked example; it defines NO extractor — `src/five_d_nd/statement.py`
validates and canonically orders an ALREADY-PRODUCED Statement document,
exactly as `triple.py` already does for §11's plain triple (this section
does not change §11, which remains a distinct, simpler shape a caller MAY
still use when a Statement's extra fields are not needed).

### The Statement node

A **Statement** is a reified edge, richer than §11's plain triple:

```
{
  "id": str,                 # stable instrument URI (ELI where one exists)
                              # + consolidation date + a pinned text hash
  "subj": str, "obj": str,   # a unit or entity id (§21's own unitisation rules,
                              # docs/codebook/typed-statements-v1.md)
  "predicate": str,          # one of the CLOSED, VERSIONED enum below
  "dimension": str,          # one of the five (§2); MUST equal the
                              # predicate's own fixed dimension
  "layer": "surface" | "domain" | "deep",   # computed from the text's own
                                              # position and function,
                                              # independent of predicate
  "weight": number,          # [0,1], default 1.0 -- composes multiplicatively
                              # along a path (§3/§11, UNCHANGED)
  "edge_confidence": number, # [0,1], REQUIRED, SEPARATE from weight -- how
                              # strongly the text supports this asserted edge
  "provenance": {"start": int, "end": int},  # a span, 0 <= start < end
  "negation": "present" | "uncertain" | "absent",  # reuses §18's own
                                                      # three-state machinery
  "extraction_rule_id": str | null   # OPTIONAL; null for a GOLD statement
}
```

**`id` — content-addressed, version-stable, with a fully pinned hash.** A
bare clause offset breaks across a corrigendum or a re-consolidation
(EUR-Lex consolidations, DE vs EN paragraph numbering) — the id is
instead the instrument's own stable URI (an ELI URI where one exists),
the consolidation date, and a hash of the NORMALIZED clause text, joined
as `<instrument_uri>#<consolidation_date>#<hash>` (`statement.
statement_id()`), with each of the three segments required to contain no
`#` of its own. Every segment of the pinning is now explicit:

- **Text normalisation** (`statement.normalize_statement_text()`):
  Unicode NFC (never NFKC/NFKD — this is a whitespace/encoding
  normalisation only, never a semantic one; case is preserved), every
  U+00A0 (non-breaking space — present in both the GDPR's and the AI
  Act's own source text) replaced with an ordinary U+0020 space, then
  every run of ASCII whitespace collapsed to one space, stripped at both
  ends. The NBSP replacement and the whitespace collapse are two
  INDEPENDENT steps (the collapse is deliberately ASCII-only, never
  Python's own Unicode-aware whitespace class, so dropping either step
  changes the result on its own, never masked by the other).
  - **Hash** (`statement.text_hash()`): lowercase hexadecimal sha256 of
  the normalised text (UTF-8 encoded), truncated to 16 hex digits
  (`statement.ID_HASH_HEX_LENGTH`). Two callers hashing the SAME
  normalised text MUST produce the SAME 16-hex-digit segment.
- **Validator** (`statement.ID_SHAPE_RE`, `schema/statement.schema.json`'s
  own `id` pattern): exactly three non-empty `#`-separated segments, the
  third matching `^[0-9a-f]{16}$`. The validator checks this exact shape;
  it does not, and cannot, recompute the hash itself (that needs the
  caller's own source text).

Two Statements drawn from the EXACT SAME clause (e.g. a `requires`
reading and a `compliance_purpose_of` reading of one sentence) correctly
share the SAME id — the id names the CLAUSE's identity, not the
individual Statement's; `subj`/`predicate`/`obj` already distinguish the
Statements drawn from one clause from each other.

**`predicate` — CLOSED and VERSIONED, one dimension each.** Unlike §9's
`binding` (an nD grammar's OWN, open-ended relation-to-dimension map), the
typed-statement predicate enum is 5D's OWN closed vocabulary, pinned by
version string (`"typed-statements-v3"`,
`vocabulary/statement-predicates.json`, byte-identical to
`statement.PREDICATE_DIMENSION`). An implementation MUST reject an unknown
predicate outright, and MUST reject a `dimension` that disagrees with the
predicate's own fixed assignment — a Statement's dimension is NEVER
independent of its predicate. **MODAL FORCE IS NEVER A STATEMENT
PREDICATE** — an obligation, a permission, or a prohibition (O/P/F) is nD
deontic knowledge (§7, §9's co-dimension), and no predicate below names
one; `requires`'s own object is the ACT a trigger causes, never "an
obligation" framed as such.

| predicate | dimension | one-line gloss |
|---|---|---|
| `is_a` | structural | a legal/legislative definition |
| `part_of` | structural | structural containment / sub-unit, part-to-whole |
| `applies_to` | structural | scope: the instrument's applicability, including a concession |
| `cross_references` | structural | a citation to another provision |
| `except_when` | structural | a true exception/derogation from a rule |
| `enables` | causal | makes something possible or produces it, no stated purpose |
| `requires` | causal | trigger/condition → a consequence ACT |
| `legislative_purpose_of` | intentional | recital-position purpose, no modal |
| `compliance_purpose_of` | intentional | operative-article purpose, with a modal |
| `based_on` | intentional | the stated legal basis (justification) of the subject |
| `precedes` | temporal | an explicit ordering relation |
| `deadline_of` | temporal | a bounded-duration relation |
| `predication` | relational | the DEFAULT — an ordinary copula/modal assertion |
| `competence_of` | relational | an institutional actor's own mandate |
| `performs` | relational | any other actor performing a non-deontic act |

Full definitions, and the hard-boundary decision rules between
neighbouring predicates (causal vs intentional, temporal vs causal,
structural vs relational, recital vs article, competence_of vs performs),
are in `docs/codebook/typed-statements-v1.md` — this table is the closed
set and each predicate's one dimension, not the full codebook. The
coverage measurement this enum was checked against is
`docs/codebook/coverage-measurement.md`.

`part_of` is the SOLE containment predicate: a clause surfacing the
relation whole-first ("X includes Y") is coded `part_of` with `subj` and
`obj` SWAPPED (part-to-whole), never as a second predicate — there is no
separate `includes` predicate. `except_when`'s own cues are restricted to
expressions of true non-application (`unless`, `except`, `by way of
derogation from`, `save where`), PLUS `notwithstanding`/`irrespective of`
WHEN their own object's HEAD NOUN is itself a PROVISION REFERENCE (a
paragraph, an Article, a point, a subparagraph, or a named act —
`notwithstanding paragraph 2`); a thing merely QUALIFIED by "referred to
in..." or "pursuant to..." does NOT count ("the terms of the
arrangement referred to in paragraph 1" has head noun "terms", not
"paragraph"). The SAME two cues with an object whose head noun is a FACT
OR CIRCUMSTANCE instead are concessive and belong to `applies_to` — the
routing test is the object's own head noun, not which cue word appears.
A SAVINGS CLAUSE ("without prejudice to X", "shall not affect X") is
NEITHER of these — it is `cross_references`, a non-overriding link from
the host provision to X; the "not" in "shall not affect X" is part of
the savings cue, never a negator (`negation: "absent"` unless a separate
negator applies).
`based_on` names a legal basis (a JUSTIFICATION) only —
intentional, never causal or structural; a clause describing HOW an act
or decision is PRODUCED (a mechanism) is `enables`, never `based_on`,
even when the surface words "based on" appear in it. `competence_of` is
restricted to an institutional actor (a supervisory authority, a board, a
notified body, a market surveillance authority, the Commission, a Member
State, the AI Office) assigned a task or power from an enumerated list;
every other actor performing a non-deontic act (once its own modal is
stripped) uses `performs`.

### The layer — surface, domain, deep

The triple tensor is computed from
triples, not from Statements directly. Every Statement carries a `layer` ∈ {`surface`, `domain`,
`deep`} — the three layers the original lineage's per-concept triple
tensor named. This
specification does not revive that per-concept tensor as a separate,
directly-assigned structure; instead, a layer's own point is COMPUTED,
for a given entry, as the UNCHANGED §11 `point_from_contributions`
formula applied to ONLY that layer's own Statements naming the entry
(`statement.layer_tensor()`) — the tensor comes from the Statements, never
from a second, independently-maintained per-concept field.

**The layer rule is INDEPENDENT of the predicate** — it comes from the
clause's own TEXT POSITION and FUNCTION, never from which predicate was
assigned to it (the same predicate, e.g. `is_a`, can in principle appear
at any layer; layer and predicate are coded separately). An explicit
PRECEDENCE order resolves every clause, applied top to bottom — the
FIRST matching rule decides, and a later rule is never consulted once an
earlier one matches:

1. A definition article, or a definitional clause within an otherwise
   operative article → `deep`.
2. A principle stated AS a principle (e.g. a GDPR Art. 5-style principle
   heading, independent of which predicate codes its own operative
   content) → `deep`.
3. A recital → `surface`, UNLESS rule 1 or rule 2 already applies to that
   recital's own content (a recital that restates a definition or a
   principle is `deep` by rule 1/2, not `surface` by position alone).
4. Everything else that is operative (an ordinary article clause, not a
   definition and not a principle statement) → `domain`.

This ordered list is the full rule; there is no residual "else" beyond
rule 4, and no clause is layer-ambiguous once the four rules are applied
in order. Full examples are in `docs/codebook/typed-statements-v1.md`'s
own "Layer" section.

### Canonical serialisation and sort order

A set of Statements sorts by `(dimension, subj, pred, obj, span)` —
`statement.canonical_sort_key()` / `statement.sort_statements()`. `span`
is the `(start, end)` integer pair from `provenance`, compared as a tuple
of ints (never as a string) and INCLUDED in the key — two statements that
agree on dimension/subj/pred/obj but differ only in span are not
interchangeable for sort purposes. Canonical BYTES, when a digest over a
Statement or a sorted Statement list is needed, reuse
`grounding.canonicalize()` unchanged (§4) — this section adds no second
canonicalisation rule.

**`negation` reuses §18's three-state machinery, applied to the
Statement's own relation.** `present` — the relation IS negated, with no
negator ambiguity in scope; `uncertain` — every occurrence that could
negate the relation is itself ambiguous (never silently collapsed to
`present` or `absent` — §18's own conservative design, carried over
unchanged); `absent` — no negation found. A Statement whose own relation
is negated is still a Statement ABOUT that relation (it is not omitted) —
the field records what the text says about the relation, not whether the
Statement itself should be discarded.

### The entity/actor vocabulary

A CLOSED list of the roles a `subj`/`obj` entity id may name, plus one
documented escape (`vocabulary/actor-roles.json`,
`statement.ACTOR_ROLES`/`statement.is_known_actor()`): `controller`,
`joint_controller`, `processor`, `sub_processor`, `provider`, `deployer`,
`importer`, `distributor`, `authorised_representative`, `data_subject`,
`data_protection_officer`, `supervisory_authority`, `notified_body`,
`market_surveillance_authority`, `commission`, `member_state`,
`european_data_protection_board`, `ai_office`, `third_party`, `recipient`,
`operator`. A role this list does not yet name is carried as
`other(label)` (`statement.ACTOR_OTHER_RE`) — never silently dropped, and
never a permanent substitute for extending the closed list (the gold
protocol logs every `other(...)` use as a candidate addition to the next
version, `docs/codebook/gold-protocol-v1.md`). The SUBSET that is an
institutional body — `supervisory_authority`, `notified_body`,
`market_surveillance_authority`, `commission`, `member_state`,
`european_data_protection_board`, `ai_office`
(`statement.INSTITUTIONAL_ACTOR_ROLES`) — is the set `competence_of`'s own
cue test restricts its `subj` to; every other role uses `performs`.

### The dual-coded split — an ANNOTATION rule, not grammar precedence

One clause that reads as BOTH causal and intentional at once is coded as
TWO Statements — a causal Statement and an intentional Statement —
SHARING THE MIDDLE SEGMENT: the causal Statement's `obj` equals the
intentional Statement's `subj`, so the pair reads as one chain `A
--causal--> B --intentional--> C` from a single clause
(`statement.dual_split_violations()` / `is_valid_dual_split()`). Both
halves MUST individually validate as ordinary Statements, and their
provenance spans MUST NOT be disjoint (a dual split describes ONE clause,
never two unrelated ones). This exists so a clause whose causal/
intentional boundary is genuinely contested is CODED both ways and
TESTED for agreement (gold protocol, below), rather than forced into one
predicate before the question of whether the boundary is even real has
been asked.

### How Statements feed points, containers, depth, and the tensor — worked example

A Statement feeds the EXISTING §11/§14 machinery exactly as an nD claim
already does (§5, rule 1): for every entry a Statement names as `subj` or
`obj`, that entry's raw contributions get `+1` on the Statement's own
closed-enum dimension (`statement.raw_contributions()`). Nothing in §11's
`point_from_contributions`, §14's `container_position`, or §14's
`conceptual_depth` changes — this section supplies a RICHER source of raw
contributions, the same shape §11 already validates. The 3×5 tensor
(above) restricts that same derivation to one `layer` at a time
(`statement.layer_tensor()`).

**Worked example — GDPR Art. 22 and recital 71 / Art. 4, numbers
recomputable by hand** (`conformance/vectors/worked-example-typed/gdpr-
art22-statements-to-point-container-depth.json`). Nine real Statements,
with real offsets into GDPR's own source text and real `statement_id`
values (`http://data.europa.eu/eli/reg/2016/679/oj`, consolidation date
`2016-05-04`, `statement.text_hash()` over each clause's
`normalize_statement_text()`-normalised text). NO Statement below is a
right, an obligation, or a permission: Art. 22(1)'s own decision is coded
via its PRODUCTION mechanism (processing enables the decision, never a
legal-basis claim — see `based_on`'s own definition, above), and Art.
22(3)'s own safeguards are coded as MEASURES the controller performs or
that are part of the measures the trigger requires, never as the rights
themselves:

1. `automated_processing --enables--> automated_decision` (causal,
   domain) — Art. 22(1): "a decision based solely on automated
   processing, including profiling" describes how the decision is
   produced, not its legal basis.
2. `art22_3_applicability_condition --requires--> implement_safeguard_measures`
   (causal, domain) — Art. 22(3)'s own trigger clause; the object is the
   ACT of implementing measures.
3. `implement_safeguard_measures --compliance_purpose_of--> protect_data_subject_rights_and_freedoms`
   (intentional, domain) — the SAME sentence's own purpose clause.
4. `human_intervention_measure --part_of--> implement_safeguard_measures`
   (structural, domain) — one listed measure, part of the whole.
5. `art22_3_applicability_condition --requires--> view_expression_measure`
   (causal, domain) — the list-unitisation rule: the SAME trigger `subj`
   as Statement 2, a DIFFERENT `obj`.
6. `art22_3_applicability_condition --requires--> decision_contest_measure`
   (causal, domain) — same rule, a third listed measure.
7. `controller --performs--> human_intervention_measure` (relational,
   domain) — the non-deontic actor→act relation `performs` names.
   Statements 5 and 6 get NO `performs` parallel: expressing a view and
   contesting the decision are the DATA SUBJECT's own acts, not the
   controller's — a `performs` Statement naming the controller as the
   one performing them would misattribute the actor. Only
   `human_intervention_measure`, which the controller itself provides,
   gets its own `performs` Statement.
8. `profiling --part_of--> automated_processing` (structural, **surface**)
   — recital 71's own plain-language sentence, direction normalised
   part-to-whole.
9. `personal_data --is_a--> information_relating_to_identified_or_identifiable_natural_person`
   (structural, **deep**) — Art. 4(1)'s own definition: personal data IS
   information RELATING TO a person, never the person themselves.

- Entry `automated_decision` is named by ONLY Statement 1 (as its
  object) → raw `{causal: 1}` → point `{causal: min(1/5,1) = 0.2}` →
  dominant `causal`.
- Entry `implement_safeguard_measures` is named by Statements 2 (obj,
  causal), 3 (subj, intentional), and 4 (obj, structural) → raw
  `{structural: 1, causal: 1, intentional: 1}` → point `{structural: 0.2,
  causal: 0.2, intentional: 0.2}` → dominant `structural` (a three-way
  tie on raw value `1`, broken by canonical order). Statements 5, 6, and
  7 deliberately do NOT name this entry (their own objects are different
  measures), so they add nothing further to this count.
- A container `Article_22` with these two entries as its members:
  position = the fixed-point MEAN of the two points — `structural:
  (0.0+0.2)/2 = 0.1`, `causal: (0.2+0.2)/2 = 0.2`, `intentional:
  (0.0+0.2)/2 = 0.1`, `temporal: 0.0`, `relational: 0.0` (§14,
  `container_position`, unchanged).
- Depth `d` for `Article_22`, nested one level under `GDPR`
  (`GDPR -> Article_22`), with NO concept/anchor links in this minimal
  example: `deep_pull = 0`, `surface_pull = 0` → `raw_depth = 0`;
  `nesting_relative_position = 1 ancestor / (1 ancestor + 0 descendants)
  = 1.0` (within `r=2`); `d = (0.5*0 + 0.5*1.0) / (0.5+0.5) = 0.5` (§14,
  `conceptual_depth`, unchanged formula).
- The 3×5 tensor for entry `automated_processing` (named by Statement 1,
  layer `domain`, as subj; and Statement 8, layer `surface`, as obj):
  `surface = {structural: 0.2}` (from Statement 8 alone), `domain =
  {causal: 0.2}` (from Statement 1 alone), `deep` = the all-zero point
  (no Statement at this layer names `automated_processing` in this
  example — genuinely zero, not contrived into a
  third non-zero layer).

See `docs/codebook/typed-statements-v1.md`'s own "Layer" section for the
surface/domain/deep coding rules these nine Statements apply.

## §22 Typed paths

**Path composition is a STRICT LEFT-FOLD along the path's own edge
order** — §3's existing normative rule (`dimensions.left_fold`), applied
here to a path of §21 Statements rather than to a bare list of dimension
labels. There is NO bracketing freedom: a path has a natural edge order
(the order its own Statements were traversed in, e.g. by provenance
adjacency or by an explicit caller-supplied sequence), and the fold is
evaluated strictly left to right over THAT order — never re-associated,
never evaluated right-fold (`path.fold_statements()`). The WEIGHT composes
multiplicatively over the SAME order (§3/§11, `compose_weights`, UNCHANGED)
— `edge_confidence` does NOT compose by this rule; it is a separate
per-edge quantity this section imposes no composition algebra on.
`fold_statements()` validates every statement's own `weight` (finite, in
`[0, 1]`) before folding it, raising on a malformed one rather than
propagating it silently.

**The fold state is the current composed dimension** — one of the five
(§2) — so a typed-path SEARCH (not merely evaluating one already-chosen
path) runs over the PRODUCT GRAPH `V × 5`: every node paired with every
possible composed-dimension-so-far state (`path.typed_path_search()`,
`path.product_graph_state_count()`). This is what keeps search POLYNOMIAL:
the state space is `5 * |V|` regardless of path length, so a Dijkstra
walk over it is `O((V + E) log V)` at most, never exponential in path
length.

**`typed_path_search()` runs a MAX-PRODUCT DIJKSTRA over the product
graph.** A first-visit breadth-first search is the wrong algorithm: it
fixes a state's own weight to whichever path reaches it FIRST in hop
order — not necessarily the path of GREATEST weight to that state, when
parallel edges carry different weights, which can wrongly starve a
higher-weight arrival that would otherwise clear a confidence floor
(`conformance/vectors/path-search/` includes a vector exercising exactly
this). Since edge weights are in `[0, 1]` and compose MULTIPLICATIVELY,
each edge's own cost `-log(weight)` is non-negative, and multiplying
weights along a path is exactly ADDING their `-log` costs — so a
standard min-cost Dijkstra over `-log(weight)` is EXACTLY a max-product
search over `weight`, and Dijkstra's own correctness precondition
(non-negative edge costs) holds.

### The laws the table actually satisfies — verified by code over all 125 triples

`path.composition_law_report()` iterates EVERY ordered pair and EVERY
ordered triple the five-dimension set admits and reports, as data (never
as prose asserted without a check):

- **Identity — two-sided.** `compose(d, relational) == compose(relational,
  d) == d` for all five `d` (§3's existing claim) — **holds**.
- **Idempotence.** `compose(d, d) == d` for all five `d` — **holds for
  every one of the five dimensions** (recorded here because §3's prose
  never states this property by name, even though the table satisfies it;
  an implementation MUST NOT assume idempotence failed merely because §3
  does not mention it).
- **Associativity.** `compose(compose(a,b),c) == compose(a,compose(b,c))`
  for all 125 ordered triples — **fails on EXACTLY 2 of the 125**:
  `(causal, intentional, structural)` and `(causal, temporal,
  structural)` (§3's existing claim, reproduced here by exhaustive code
  rather than by citation alone — see
  `conformance/vectors/composition-laws/125-triple-law-check.json`, the
  frozen output of this exact function).
- **Commutativity.** `compose(a,b) == compose(b,a)` for all 25 ordered
  pairs — **fails on 10 of the 25** (5 unordered pairs: `{structural,
  intentional}`, `{structural, temporal}`, `{causal, intentional}`,
  `{causal, temporal}`, `{intentional, temporal}`), confirming §3's
  existing "NOT commutative in general" claim with an exact count, not
  only an example pair.

No other algebra-of-a-monoid property (associativity holding everywhere,
hence a true monoid; a group; cancellation) holds — the table is a
**magma with a two-sided identity**, idempotent, and associative except on
the two named triples. This is the exact shape left-fold's own
normativity (§3) exists to resolve: a structure this close to a monoid,
but not quite one, has no single "the" composed dimension for a path of
length 3+ without a FIXED evaluation order.

### Cost bound

Search over the product graph is bounded by its own state count
(`product_graph_state_count(|V|) = 5 * |V|`) and the edge set `E`
(each of a node's own outgoing edges is explored once per state it is
reached from, so the walk visits at most `5 * |E|` transitions): a
Dijkstra-shaped search is therefore `O((|V| + |E|) log(5|V|))` with a
priority queue — POLYNOMIAL in the graph size and INDEPENDENT of path
length.

### The confidence-floor cut — STAGE 2, hook only

`path.confidence_floor_cut(weight, floor)` is the SAME status §16 already
gives `confidence_floor` itself: the FIELD, the HOOK function, and an
OPTIONAL `floor` parameter threaded through `path.typed_path_search()` all
exist and are exercised by conformance vectors
(`conformance/vectors/path-search/`, including a floor-EQUALITY vector —
the cut is a STRICT less-than, so a weight exactly equal to the floor is
never cut), but NOTHING in this specification APPLIES the floor by
default (`floor=None` is a no-op). When a floor IS supplied and a
transition's composed weight falls below it, that transition is simply
NOT relaxed — the state it would have reached MAY still be reached via a
different, un-cut path, but never via this one: a boundary below the
gate is left OUT of a result, never assigned a weight nobody measured.

## §23 Conformance (typed-triple layer)

An implementation conforms to §21/§22's additions when it, IN ADDITION to
§10's, §17's, and §20's existing criteria (all UNCHANGED):

25. Reproduces the CLOSED, VERSIONED §21 predicate enum
    (`vocabulary/statement-predicates.json`, `statement.PREDICATE_DIMENSION`)
    and rejects any `dimension` disagreeing with a predicate's own fixed
    assignment;
26. Validates a Statement's full shape per §21
    (`statement.statement_violations()`/`is_valid_statement()`), including
    the SEPARATE, REQUIRED `edge_confidence` field, the three-state
    `negation` field, the `layer` field, and the pinned id shape
    (`statement.ID_SHAPE_RE`, a 16-hex-digit lowercase hash segment);
27. Reproduces §21's canonical sort order `(dimension, subj, pred, obj,
    span)`, with `span` itself load-bearing in the comparison
    (`statement.canonical_sort_key()`);
28. Validates the dual-coded-split annotation rule's shared-middle-segment
    requirement (`statement.dual_split_violations()`);
29. Evaluates a path of 1+ Statements by STRICT LEFT-FOLD over BOTH the
    dimension (§3, unchanged) and the weight (multiplicative, §3/§11,
    unchanged), validating every statement's own weight first
    (`path.fold_statements()`);
30. Reproduces, by exhaustive code over all 125 ordered triples and all 25
    ordered pairs, the EXACT law report §22 states (identity holds,
    idempotence holds, associativity fails on exactly 2, commutativity
    fails on exactly 10) (`path.composition_law_report()`);
31. Validates the `layer` field and computes the 3×5 tensor from a
    layer-filtered application of §11's UNCHANGED point formula
    (`statement.layer_tensor()`);
32. Runs `typed_path_search()` as a max-product Dijkstra, never a
    first-visit breadth-first search, and cuts a transition on the
    confidence floor with a STRICT less-than (an equal-to-floor weight is
    never cut);
33. Computes and checks the id hash exactly as §21 pins it: Unicode NFC,
    NBSP replaced, ASCII whitespace collapsed, stripped, then lowercase
    hex sha256 truncated to 16 digits (`statement.text_hash()`).

AND passes every vector under the FAMILIES this layer adds: `statement`,
`path`, `composition-laws`, `worked-example-typed`, `path-search`,
`actor-role`, `dual-split` — see `tests/test_conformance.py`'s `FAMILIES`
dict for the minimum count per family (the `composition-laws` family's
own minimum is 1, by design: its single vector is an EXHAUSTIVE check
over all 125 triples and 25 pairs, not a sample a larger count would make
more convincing).

**The extractor is a later build step, validated against gold, never the
other way round.** This layer's own normative core (§21/§22, this
section) defines the DATA MODEL and the codebook's own worked example,
not an extractor — the codebook (`docs/codebook/typed-statements-v1.md`)
and the gold protocol (`docs/codebook/gold-protocol-v1.md`) are its own
deliverables for THAT problem. `src/five_d_nd/extract/` is one such later
build step (a deterministic candidate-proposal pipeline composed, per
§23a below, with a model-assisted decision stage) — its own conformance
is to the codebook and to §23a, not an additional requirement on §21-§23
themselves.

## §23a Determinism by replay (the hybrid extractor)

An implementation MAY compose the deterministic extraction pipeline
(§21-§23) with a MODEL-ASSISTED decision stage, PROVIDED the following
hold:

1. The deterministic stage (candidate proposal: clause/list-item
   segmentation, NP-chunk proposal, candidate-Statement proposal from a
   closed cue-rule table) MUST remain pure recomputation, exactly as §23
   already requires of the non-hybrid pipeline — the SAME unit text
   MUST give the SAME candidate set, byte-identically, with no model
   involved at this stage.
2. The candidate set MUST be serialised as CANONICAL JSON and
   content-addressed by its own SHA-256 digest.
3. The model-assisted decision stage MUST be content-addressed by a key
   deriving from (at minimum) the candidate set's own digest, the
   coder-view/instructions text's own digest, the model identifier, and
   the prompt template's own digest. The model's own answer (the
   "Decision") to a given key MUST be recorded exactly once and
   thereafter REPLAYED from that record — an implementation MUST NOT
   call the model again for a key it has already recorded, and MUST
   raise an error (never silently recompute, never silently fall back
   to an unassisted result) on a key it has NOT recorded.
4. The assembly stage (Decision + candidate set -> schema-valid
   Statements, §21) MUST remain pure recomputation. Any span
   adjustment, or any added Statement's own endpoint span, that the
   Decision specifies MUST be constrained to a span ALREADY PRESENT in
   the candidate set (a clause span, an NP-chunk span, a candidate
   Statement's own endpoint, or an inherited/antecedent span the
   candidate set separately names) — an implementation MUST reject, not
   silently clamp or ignore, a span outside that set.
5. **Determinism, restated:** under §23's own pure-recomputation regime,
   the SAME input gives the SAME output because the SAME code runs on
   it. Under this subsection's own replay regime, the SAME input AND
   THE SAME content-addressed decision cache give the SAME output —
   determinism is a property of the (input, cache) PAIR, not of the
   input alone. Any report of a hybrid extractor's own output MUST
   state the cache's own content hash (a manifest digest over every
   recorded key) alongside the result, so a reader can verify EXACTLY
   which recorded decisions produced it.

A pipeline conforming to §23 alone (no model-assisted stage) trivially
satisfies this subsection too (an empty decision cache, with every
Decision being the identity — "keep every candidate's own predicate/span
unchanged" — recomputed, never replayed, is one valid instance). This
subsection is therefore ADDITIVE: it does not change what a non-hybrid,
§23-only implementation must do, and does not retract §23's own
requirement that the DETERMINISTIC portions of a hybrid pipeline
(candidate proposal, assembly) remain pure recomputation.

(`src/five_d_nd/extract/hybrid.py` implements this subsection;
`src/five_d_nd/extract/{rules,segment,spans,negation,build}.py`
implement the deterministic, non-hybrid §23 pipeline it composes with.
See ADR 0012 for the implementation decision record.)

## Annex A — Lineage (informative)

Dated sources (see the lineage digest this annex summarises, carried
in this branch's own session notes, not reproduced here):

- **2026-03-20** — Brain (`Brain/brain/cell_algebra.py`): first 5D, as sets of
  edge relation types; normative verbs (`violates`, `justifies`) sit inside
  5D (INTENTIONAL); per-dimension weight-composition rules (MIN/mean/product).
- **2026-03-21** — the cell kernel (`idea5` commit `d8a7a93`): the five
  become "mental models" with question-form meanings (§2's source); the 5×5
  composition table appears and has been byte-identical ever since;
  multiplicative weight composition replaces Brain's per-dimension rules;
  non-associativity is a property of this table, though not documented as
  such until later.
- **2026-04-07 → 04-20** — the bridge archive: the table is imported
  unchanged; nD is invented (04-10/11) as an independent characterisation
  module orthogonal to 5D, then (04-11, Protocol 30) redefined as a learned
  projection FROM the 5D vector; normative verbs remain on 5D edges.
- **2026-05 → 06** — Circle/Cubes: 5D is ported back as graph-typed edges
  only ("vector 5D is deferred"/"not built"); left-fold is fixed as the
  canonical evaluation order for the non-associative table; a rule nD puts
  norm content directly on 5D edges (e.g. `governs` as INTENTIONAL).
- **2026-07 → 09-29** — versum, solver, and this repository: the composition
  table is vendored verbatim; `position5d.py` (2026-09-28) adds the
  count-derived, per-entry position this specification's §5 reproduces; the
  deontic plane's binding becomes `{}` ("operators are *ought*, not *is*"),
  reversing the earlier placement of normative verbs on 5D.

This specification's decisions (D1, left-fold, N1-N4) are OWNER decisions
made 2026-09-30/10-01, not attested verbatim in any single original source;
each is recorded as an ADR under `docs/decisions/`. The is/ought placement
went through THREE designs on this branch in two days — D2 (2026-09-30,
excluded ought from 5D entirely), R1-R5 (2026-10-01 morning, "every link
carries a mode"), and N1-N4 (2026-10-01, same day, the SETTLED design: "5D
doesn't need to know that... ND-Grammar can know this as co-dimension(s)")
— see `docs/decisions/0003-is-ought-in-nd-grammars.md` for the full
history with all of the owner's dated statements. N1-N4 restores something
close to what the ORIGINALS did (Brain's `violates`/`justifies` on
INTENTIONAL, Cubes 1.1's `governs` on INTENTIONAL) while keeping the
distinction the originals lacked — but that distinction now lives entirely
in nD (a co-dimension), never in 5D itself.

## Annex B — Open owner decisions (informative)

- **MIGRATION ITEM — §8a's clause-cue layer has no upstream
  implementation.** loomground-factual @ `ebf9fe1` (the same GitHub head
  §8 is re-derived from) implements ONLY §8's single-cue-kind lowering —
  it has no counterpart to §8a's five-table cue scan, no cross-reference
  link extraction, and no `relational`-suppression rule. This is an OPEN
  migration item (whether, and how, §8a's cue table should move upstream
  into loomground-factual itself, or stay a 5D-only addition) — NOT a
  claim that factual already implements it, and NOT a conformance claim
  about factual. §8's own "matches loomground-factual @ ebf9fe1 exactly"
  statement is UNCHANGED and still true; it describes §8 only.
- **Weight composition** (§3): RESOLVED, 2026-10-01 (coordinate round) —
  multiplicative composition is NORMATIVE; see §3's own "Weight
  composition — NORMATIVE" subsection and
  `docs/decisions/0006-weights-normative.md`. No longer open.
- **Scope of 5D beyond edges/entries**: the originals apply 5D to edges AND
  concept vectors/routing; this specification, like recent Loomground repos,
  scopes 5D to entries and links only. Whether a future version extends 5D
  to whole-document or whole-graph vectors is OPEN.
- **Is/ought placement**: RESOLVED, 2026-10-01 — see N1-N4 (§7) and
  `docs/decisions/0003-is-ought-in-nd-grammars.md`. No longer open.
- **MIGRATION NOTE — versum's indexer actively REFUSES a non-empty binding
  from the plane named `deontic`, not merely "has not chosen" one.**
  Verified 2026-10-01 against versum origin/main `e416c81`
  (`src/versum/planes.py:462`):

  ```python
  if pid == "deontic" and bind:
      raise PlaneIndexError(
          f"the deontic plane published a non-empty binding {dict(bind)!r}; "
          "an operator (O/P/F) is OUGHT, not a fact on the 5D manifold (D1) — "
          "refusing to let any operator contribute to 5D under any name",
          plane=pid, source=source_urn)
  ```

  This is a HARD-CODED, plane-ID-keyed guard in versum's indexer itself —
  not a leniency the deontic plane's own package controls. Under N2 (a
  normative relation MAY bind to a 5D dimension exactly like any other),
  a deontic descriptor that binds O/P/F → `intentional` VALIDATES under
  this specification's own `descriptor_violations()` (verified: `[]`) —
  but versum's `build_source_entries` REJECTS it at index time with a
  `PlaneIndexError`, unconditionally, the moment ANY plane registered under
  the id `"deontic"` publishes a non-empty binding. This is a REAL
  versum-side blocker for any grammar that wants to exercise N2's "MAY
  bind", not merely an unexercised option: migrating versum (removing or
  relaxing this hard-coded `pid == "deontic"` check) is OPEN — a decision
  for the owner on timing and the versum maintainers on implementation.
  **This specification does NOT claim versum conforms to N2 for the
  deontic plane today; it does the opposite — it names the exact guard
  that would need to change.**
