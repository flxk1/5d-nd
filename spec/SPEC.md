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
