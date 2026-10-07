# 0003 — Is and ought live in nD grammars, as co-dimensions (N1-N4) (2026-10-01)

## Status

Accepted. **This is the THIRD and SETTLED design on this branch in two
days.** It supersedes BOTH of this ADR's earlier decisions:

1. "Is/ought applies to every grammar" (D2, 2026-09-30) — a normative
   declaration carries NO 5D dimension at all (binding `{}`, declared
   `dimension` always `null`);
2. "Every 5D link carries a mode" (R1-R5, 2026-10-01, same morning) — is and
   ought both compose on 5D's dimensions, differentiated by an explicit
   `mode` field on every link.

Both are kept below as history (each explains why it was adopted, and why it
was then replaced); the final section, "Decision (N1-N4)", is the rule this
specification now follows.

## Context (D2, 2026-09-30 — superseded, kept for history)

The lineage is internally inconsistent about whether a normative verb
(`violates`, `justifies`, `governs`, `overseen-by`, ...) may sit directly on
a 5D edge:

- Brain (2026-03-20) puts `violates`/`justifies`/`protects` inside
  INTENTIONAL, and `conflicts_with` inside RELATIONAL.
- The bridge archive (2026-04) keeps `justifies` on the 5D edge vocabulary
  while also introducing a separate `hume_guard` inside the norm nD that
  blocks descriptive→prescriptive inference — i.e. the guard against
  conflating is/ought lived in the nD layer, not in 5D itself.
- Cubes 1.1 (2026-06) puts `governs` (INTENTIONAL) and `applies-when`
  (CAUSAL) directly on 5D-dimensioned edges emitted by its rule nD.
- versum (2026-09-28 onward) excludes deontic from 5D entirely: the deontic
  plane's `binding()` is contractually `{}` ("operators are *ought*, not
  *is*").

D2 (2026-09-30) generalised versum's narrower deontic-only exclusion into a
blanket rule for every grammar: an nD grammar could bind to 5D only
is-relations; any normative declaration got no dimension at all.

## Context (R1-R5, owner design change, 2026-10-01 morning — superseded same day, kept for history)

The owner's decision, 2026-10-01: **"Is/ought can be a part of 5D, but
needs to make sure the normative/deontic parts stay in 5D differentiated."** This REVERSES D2's
"no dimension for ought" rule and restores something closer to what the
ORIGINALS actually did (Brain's `violates`/`justifies` on INTENTIONAL,
Cubes 1.1's `governs` on INTENTIONAL) — but DIFFERENTIATED, not conflated:
is and ought both compose on the SAME five dimensions, but every link now
also carries a MODE, so an ought contribution is never mistaken for an is
one.

- **R1.** Every 5D link carries a mode, `is` or `ought`. A relation on the
  always-ought list (`vocabulary/ought-relations.json` — renamed from
  "deny_list" to `always_ought`; it no longer BANS these relations from 5D,
  it REQUIRES them to be mode `ought`) MAY bind to a dimension, but MUST do
  so as mode `ought`; binding it as mode `is` is rejected. An UNLISTED
  relation MAY also be declared mode `ought` by its own grammar — the list
  is a floor, not a ceiling.
- **R2.** An ought relation defaults to dimension `intentional` when its
  grammar does not bind one explicitly (a grammar MAY refine this).
- **R3.** Each entry has TWO fingerprints, `is` and `ought`, computed
  separately by the unchanged §5 rules; they are NEVER summed or mixed. The
  existing single-position behaviour (and versum's own `position5d.py`,
  unchanged) IS the `is` fingerprint.
- **R4.** Composition: the dimension composes through the SAME unchanged
  table (left-fold, §3); the MODE of a composed path is `ought` if ANY step
  is ought, and `is` only when EVERY step is `is` (the Hume guard — an
  all-descriptive path can never yield a prescriptive one).
- **R5.** Unchanged from D2: no verdict/decision of an nD language reads a
  composed 5D weight or position; a norm's regulated content still enters 5D
  as its own is-mode assertoric entry, linked by a structural, MODE-`is`
  `embeds` link.

This is CONSISTENT with the originals, which put `justifies` on INTENTIONAL
— now made safe by mode-differentiation rather than by excluding ought from
5D altogether. The REPLACED D2 rule ("a normative entry's declared dimension
must be null") is replaced by: **a normative entry's LINKS are mode ought**
— the entry itself may still carry a position (computed per-mode, R3), but
nothing about a normative entry's OWN fields needs to be null any more; what
must be differentiated is the MODE of each link, not the presence of a
dimension.

"Justification" under R1 (unchanged from D2's note): the original INTENTIONAL
gloss (`idea5 d8a7a93 cell_algebra.py:14`) names "goals, justification,
telos" together as what the intentional QUESTION ("what is it for?") covers.
`justifies` (a NORMATIVE relation) is on the always-ought list and therefore
MUST be mode `ought` when bound to a dimension (R1) — typically `intentional`
(R2's default) unless its own grammar refines it. The intentional QUESTION
itself is untouched and covers BOTH is and ought uses (`spec/SPEC.md` §2
quotes the original gloss verbatim and records this).

## Consequences of R1-R5 (historical; all reverted same day)

- `vocabulary/ought-relations.json`'s `$comment` and field name (`always_ought`,
  not `deny_list`) said what R1 meant.
- `src/five_d_nd/contract.py` had `relation_mode_violations()` (the core R1
  check, used by both binding validation and link validation) and
  `effective_dimension()` (R2); `link_violations()`/`embeds_link_violations()`
  required every link to carry a mode consistent with R1 and R5.
- `src/five_d_nd/position.py` had `entry_fingerprints()` (R3).
- `src/five_d_nd/dimensions.py` had `compose_mode()`/`left_fold_mode()`/
  `left_fold_with_mode()` (R4).
- `schema/grammar-descriptor.schema.json` had a binding value shape that was
  EITHER a bare dimension string (implies mode `is`) or an object
  `{dimension, mode}`; a relation on the always-ought list had to use the
  object form with `mode: "ought"` (enforced via `patternProperties`,
  case- and separator-insensitively, using ECMA-262-valid character-class
  patterns — no `(?i)` inline flag, which ECMA-262 `RegExp` does not
  support — this specific technique is STILL used under N1-N4, for the
  `embeds` relation name check, see below).
- The documented divergence from versum (its deontic plane's `binding()`
  still `{}`, `position5d.py` computing only one position) was real under
  R1-R5, since versum has no concept of a link mode at all. Under N1-N4
  (below) this divergence mostly DISSOLVES: a bare-dimension-string binding
  is versum's own shape exactly, so a normative relation bound to a
  dimension now agrees with versum fully.
- All of the above — `MODES`, `compose_mode`/`left_fold_mode`/
  `left_fold_with_mode`, `entry_fingerprints`, `effective_dimension(...,
  mode)`, the object-form binding value, and the `mode` conformance vector
  family — were REMOVED from code, schemas, and vectors the same day, in
  favour of N1-N4 below.

## Decision (N1-N4, owner design change, 2026-10-01, same day as R1-R5 — THE SETTLED RULE)

The owner's decision, 2026-10-01 (a second statement, same day as the
R1-R5 decision above): **"'Every 5D link is marked is or ought.' This is
over-engineered. 5D doesn't need to know that. ND-Grammar can know this
as co-dimension(s)."**

This REVERSES R1-R5's "mode on every link" design and replaces it with:

- **N1.** 5D knows nothing about is/ought. A 5D link carries exactly one
  dimension, nothing else. There is ONE 5D fingerprint per entry (the
  existing §5 rules, versum `position5d.py` parity — unchanged from before
  D2 was ever adopted). Fold is the plain left-fold through the table (§3).
- **N2.** Normative relations MAY bind to a 5D dimension like any relation.
  Whether a relation is normative is the nD grammar's knowledge, carried as
  a co-dimension: an ordinary axis in that grammar's `NDSystem` (e.g.
  deontic's existing `operator` axis, O/P/F). The 5D language does not
  inspect it.
- **N3** (amended below, 2026-10-01, same day — "final, optional"). §9's
  contract (grammar side, not 5D): a grammar that binds a normative relation
  SHOULD default its dimension to `intentional` (owner-confirmed default)
  and MAY mark the normative character on a co-dimension axis of its own
  `NDSystem`, so normative content stays distinguishable via nD without 5D
  knowing. A "co-dimension" is defined in `spec/SPEC.md` §9 — no new
  machinery beyond what `NDSystem` already offers.
- **N4.** Kept from both earlier designs: no verdict reads a 5D weight or
  position; a norm's regulated content may still enter as its own entry
  linked by a structural `embeds` link, with the relation name normalised
  (case/separator-insensitive) for that check; the §2 "why" paragraph is
  kept (routes to `causal` or `intentional`, never a new dimension).

## Amendment — N3 is final, optional (owner decision, 2026-10-01, same day)

The owner's decision, 2026-10-01: **"co-dimension rule is final, optional."**

N3's co-dimension axis is NOT required. A grammar MAY mark the normative
character of a relation on a co-dimension axis of its own `NDSystem`; it is
NOT required to. The "SHOULD default a normative relation's dimension to
`intentional`" half of N3 is UNCHANGED — only the "MUST mark the normative
character on a co-dimension axis" half is downgraded to MAY. A descriptor
whose `NDSystem` has no axis identifying any relation as normative is just
as valid as one that declares such an axis
(`conformance/vectors/descriptor-binding/`,
`descriptor-normative-relation-no-co-dimension-axis-valid`). This is the
FINAL word on N3 — no further revision to is/ought placement is expected.

This is the SETTLED design: two prior attempts at differentiating is/ought
within a two-day window (D2's exclusion, R1-R5's mode field) were both tried
and both found wanting by the owner — D2 for making ought inexpressible in
5D at all, R1-R5 for over-engineering a distinction 5D itself has no need to
make. N1-N4 (with N3 now explicitly optional) puts the distinction exactly
where it already naturally lives:
in the nD grammar that knows what a relation means.

## Consequences (current)

- `src/five_d_nd/contract.py`: no `OUGHT_RELATIONS`/always-ought list and no
  mode-enforcement functions remain — 5D's own validator (`axis_violations`,
  `nd_system_violations`, `descriptor_violations`, `link_violations`,
  `embeds_link_violations`) has no concept of a normative relation at all.
  `normalise_relation_key()`/`is_embeds_relation()` remain, now general-
  purpose (used only for the N4 `embeds` relation-name check, not for any
  5D-level ought list).
- `src/five_d_nd/position.py`/`dimensions.py`: back to ONE fingerprint per
  entry and the plain, mode-free `left_fold()` — the R1-R5 additions are
  gone.
- `vocabulary/ought-relations.json` is REMOVED: 5D keeps no always-ought
  list of its own (N1). A grammar's own vocabulary (e.g. the deontic plane's
  `operator` axis) is where normative relations are identified, per N2-N3.
- `schema/grammar-descriptor.schema.json`'s `binding` is back to a bare
  dimension string, exactly versum's own `p5.is_dimension(dim)` shape — full
  parity with versum restored for every normative-relation binding; the only
  remaining divergence from versum's own contract is the `contract_version`
  marker and the runtime-vs-interchange `produce` distinction, both
  unrelated to is/ought.
- `schema/link.schema.json` no longer requires `mode`; an extra field an nD
  grammar chooses to attach to a link (e.g. its own normative marker) is
  simply ignored by 5D (`additionalProperties: true`), never rejected.
- The Hume-guard idea from the bridge archive (blocking descriptive→
  prescriptive inference inside the norm nD) stays where it always
  effectively lived under N1-N4: inside the nD grammar's own reasoning, via
  its co-dimension — not inside 5D, which was never the right layer for it.
