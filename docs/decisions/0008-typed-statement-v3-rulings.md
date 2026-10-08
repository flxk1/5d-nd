# 0008 — Typed-statement enum v3: design rulings (2026-10-05)

## Status

Accepted. These are delegated design choices, distinct from the
owner's own explicit decisions on the typed-statement layer — the
codebook/gold-first sequencing (2026-10-03), the pinned-blind-model
coder (2026-10-03), the alpha/n gate thresholds (2026-10-04), the
tensor-from-triples decision (2026-10-04), and the DSA/NIS2 role
additions (2026-10-04) — each cited at its own point in spec/SPEC.md
§21 and docs/codebook/.

## Context

Independent coding of real GDPR and AI Act text against the v2 enum
(`typed-statements-v2`) surfaced four problems the enum itself could not
resolve without a design ruling:

1. An actor performing a concrete, non-deontic act (`the controller
   shall document the assessment`) had no predicate of its own — only
   `competence_of`, scoped to an institutional actor's enumerated
   mandate, existed for an actor→act relation at all. Every other
   actor's act was forced into `predication`.
2. `based_on`, introduced as causal, overlapped uncomfortably with the
   causal gloss ("triggers, enables, prevents" — mechanism verbs) while
   its own worked example used "based on" to describe a PRODUCTION
   mechanism, not a legal ground.
3. `except_when`'s own cue list mixed two opposite polarities:
   `unless`/`except` (the rule does NOT apply under the condition) and
   `notwithstanding`/`irrespective of` (the rule applies DESPITE the
   condition) — merging two directions of the same word "exception" into
   one predicate.
4. `includes` and `part_of` coded the identical containment relation,
   split only by which end the surface text named first — a split with
   no dimension-level payoff, since both ends are structural.

## Decision

**R-a. Add `performs` (relational); restrict `competence_of`.** `performs`
names any actor's non-deontic act once its own modal is stripped
(`controller performs document_the_assessment`). `competence_of` is
restricted to an INSTITUTIONAL actor (`supervisory_authority`,
`notified_body`, `market_surveillance_authority`, `commission`,
`member_state`, `european_data_protection_board`, `ai_office`,
`competent_authority`, `digital_services_coordinator`, `csirt`) named in
an enumerated task/power list OR explicit competence/mandate wording
("shall be competent to...", "shall have the power/task to..."). An
institutional actor's act that satisfies neither condition, and every
act by any other actor, is `performs`.

**R-b. `based_on` is LEGAL BASIS ONLY, and moves to INTENTIONAL.**
Argued against both alternatives this ADR is required to address:

- *Against causal.* The causal gloss is "triggers, enables, prevents" —
  mechanism verbs for what MAKES something happen. A legal basis does
  not mechanically cause an act; it JUSTIFIES an act whose own trigger
  or mechanism (if any) is coded separately, as `requires` or `enables`.
  A clause describing HOW a decision is PRODUCED ("a decision based
  solely on automated processing") is a mechanism claim — `enables` —
  never a legal-basis claim, even though the surface words "based on"
  appear in it.
- *Against structural.* A legal basis is not a containment or scope
  relation. The provision cited AS the basis may separately be the
  object of a `cross_references` Statement (a fact about the citing
  sentence's surface form); `based_on` names the JUSTIFICATION role that
  citation plays, which `cross_references` itself does not capture.
- *For intentional.* The ORIGINAL five-dimension intentional gloss
  names "goals, justification, telos" explicitly, and a legal basis IS a
  justification offered for an act or provision — the same role
  `legislative_purpose_of`/`compliance_purpose_of` already occupy for a
  stated goal, extended to a stated legal ground.
- A "Where X is based on Y, [modal] Z" clause is `requires` (its own
  PRINCIPAL relation is the trigger→consequence), never `based_on`, even
  though the words "based on" appear inside it.

**R-c. `except_when`'s cues are restricted to true non-application; the
`notwithstanding`/`irrespective of` routing test is the OBJECT's OWN
HEAD NOUN, not the cue word; savings clauses are `cross_references`
with `negation: "absent"`.** Closed cue set: `unless`, `except`, `by way
of derogation from` (or `by derogation from`), `save where`, PLUS
`notwithstanding`/`irrespective of` WHEN their own object's HEAD NOUN is
itself a PROVISION REFERENCE — a paragraph, an Article, a point, a
subparagraph, or a named act ("notwithstanding paragraph 2") — a
derogation. A thing merely QUALIFIED by "referred to in..." or "pursuant
to..." does NOT count: "the terms of the arrangement referred to in
paragraph 1" has head noun "terms", not "paragraph" — paragraph 1 is
identified, not set aside. The SAME two cues with an object whose head
noun is a FACT OR CIRCUMSTANCE instead are concessive and belong to
`applies_to`: the test is the object's own head noun, never which cue
word fired. GDPR Art. 26(3)'s own "Irrespective of the terms of the
arrangement referred to in paragraph 1..." is `applies_to` under this
test (head noun "terms"); the AI Act's own Art. 73(3) "Notwithstanding
paragraph 2 of this Article..." is `except_when` (head noun
"paragraph"). "X does not apply to Y" is `except_when` only when Y is a
scope carve-out defining the rule's own boundary; otherwise it is
`applies_to` with `negation: "present"`. A SAVINGS CLAUSE ("without
prejudice to X", "shall not affect X", "is without prejudice to X") is
NEITHER `except_when` NOR negated `applies_to` — it is
`cross_references`, a non-overriding link from the host provision to X;
the codebook states this as its own rule, with positive examples (GDPR
Art. 45(7), AI Act Art. 2(7)). The "not" in "shall not affect X" is part
of the savings cue itself, never a negator: a savings `cross_references`
is `negation: "absent"` unless a separate negator applies — stated
identically in the coder view's own Negation step and the full
codebook's negation procedure. The Statement schema has no note field,
and this ADR does not instruct adding one — the earlier "concession
noted on the Statement" phrasing is withdrawn.

**R-d. `includes` is MERGED into `part_of`.** One relation, direction
normalised part-to-whole: a whole-first surface form ("X includes Y") is
coded `part_of` with `subj` and `obj` SWAPPED (`Y part_of X`), never as a
second predicate. The enum drops from 15 (v2: +4 over v1, −0) to 15 (v3:
−`includes`, +`performs`) — the net count is unchanged, but the
composition differs.

**R-e. Layer rules are INDEPENDENT of the predicate.** The layer comes
from the clause's own TEXT POSITION and FUNCTION, with an explicit
precedence applied top to bottom: (1) a definition article or
definitional clause → `deep`; (2) a principle stated as a principle →
`deep`; (3) a recital → `surface`, UNLESS (1) or (2) already applies to
that recital's own content; (4) everything else operative → `domain`. No
predicate-to-layer lookup exists or should be built — the same predicate
can appear at different layers in different clauses.

## Consequences

- `vocabulary/statement-predicates.json` is now `typed-statements-v3`:
  `is_a`, `part_of`, `applies_to`, `cross_references`, `except_when`,
  `enables`, `requires`, `legislative_purpose_of`, `compliance_purpose_of`,
  `based_on`, `precedes`, `deadline_of`, `predication`, `competence_of`,
  `performs` — 15 predicates.
- `statement.INSTITUTIONAL_ACTOR_ROLES` names the closed set
  `competence_of`'s own cue test restricts its subject to.
- The GDPR worked example (spec/SPEC.md §21) is rebuilt: Art. 22(1)'s
  decision is coded via its production mechanism (`enables`, R-b), and
  Art. 22(3)'s safeguards are coded via `performs`/`part_of`/`requires`
  on the measures themselves, never on the rights.
- `docs/codebook/coverage-measurement.md` re-measures the enum's own
  main-relation-predication rate under v3, on two independent samples;
  `performs` resolves every actor→act clause previously forced into
  `predication`, leaving one documented residual (a separation-of-duties
  constraint between two role-sets that no predicate, including
  `performs`, names).

## Addendum A — codebook clarification round, v3.1 (2026-10-04)

### Status

Accepted. These are delegated rulings on a blind pilot's own
disagreements, recorded here as such and distinct from the owner's own
decisions — same convention as the body of this ADR. The predicate set and
`PREDICATE_DIMENSION` mapping are UNCHANGED from v3; this addendum
clarifies three decision rules only.

### Context

A blind pilot (two pinned Opus coders, 50 units, run against the v3
codebook) measured dimension alpha 0.765 (0.725 without the AI Act
Art. 3 definitions unit), predicate alpha 0.753, layer alpha 0.977,
and no causal-vs-intentional confusion (n = 28). The disagreements
clustered at exactly three codebook gaps, each ruled on below.

### Decision

**R-f. `performs` vs `competence_of` — the decisive test is CONFERS/
ESTABLISHES versus EXERCISES.** Pilot unit ai-act:0435 (AI Act Art.
57(11)'s own sandbox-supervision sentence, "National competent
authorities shall exercise their supervisory powers..."): one coder
read "national competent authorities" EXERCISING its own powers as
`performs`, the other as `competence_of`. Pilot unit ai-act:0503 (AI
Act Art. 74(3)'s own market-surveillance sentence, "...provided they
ensure coordination with the relevant sectoral market surveillance
authorities responsible for the enforcement of the Union harmonisation
legislation listed in Annex I."): one coder read "Annex I" as the
object of an `applies_to` Statement on "Union harmonisation
legislation", the other coded "sectoral market surveillance
authorities" as the `competence_of`'s own subject of "enforcement of
the Union harmonisation legislation" — the second coder's own reading
is the REDUCED-RELATIVE error Addendum B's own R-j corrects (a
"responsible for" phrase that merely IDENTIFIES an actor inside a
different clause's own object confers nothing; see "Addendum B,"
R-j). `competence_of` applies ONLY when the text CONFERS or
ESTABLISHES a task or power on the actor — "shall have the task/power
to...", "shall be competent...", "is responsible for...", or the
object is one item of the actor's own enumerated task/power list. An
institution EXERCISING an already-granted power in a specific clause
("shall exercise its powers...", "may request...", "shall adopt...")
is `performs` — exercising a power is a different act from the text
that conferred it, even where the surface vocabulary ("powers")
repeats.

**R-g. "subject to [provision]" — the SAME head-noun test as
`notwithstanding`/`irrespective of` (R-c).** The two coders split on
UK DPA 2018 s. 6(1) ("has effect subject to— (a) subsection (2), (b)
section 209, (c) section 210"): one coded all three items
`except_when`, the other `cross_references`. "Subject to [a provision
reference]" (a paragraph, Article, section, subsection, point,
subparagraph, or named act) makes the host provision's own
application CONDITIONAL on that provision prevailing — a
derogation-type limitation, `except_when`, under the identical
head-noun test R-c already states for `notwithstanding`/`irrespective
of`. "Subject to [a non-provision]" (a condition or requirement, e.g.
"subject to appropriate safeguards") is `requires` — the condition is
something the act must satisfy, not a provision setting the rule
aside, so it belongs to neither `applies_to` nor `except_when`.

**R-h. Span granularity — explicit unitisation rules.** Neither coder
had an explicit rule to apply, and the earlier codebook text itself
said the opposite of what this ruling now rules:

- The clause span is the SMALLEST COMPLETE clause that carries the
  relation — not the whole sentence it sits in, and not a fragment
  that drops part of the relation's own content.
- `subj`/`obj` spans are MAXIMAL noun phrases, INCLUDING their own
  modifiers, EXCLUDING a leading determiner. This REVERSES the
  codebook's earlier "shortest noun phrase" wording, which this ruling
  rules was simply wrong.
- List items under a chapeau: code ONE Statement per item, with the
  clause span being the ITEM, not the whole chapeau+list sentence.
- The SUBJECT is INHERITED from the chapeau across every item
  Statement — the chapeau's own named actor or trigger is the shared
  subject, each item supplies only the differing object.

### Consequences (Addendum A)

- `vocabulary/statement-predicates.json` bumps its own `version` field
  to `typed-statements-v3.1`, matched by
  `statement.PREDICATE_VOCABULARY_VERSION`; the predicate set and
  `PREDICATE_DIMENSION` mapping are UNCHANGED — only the predicates'
  own definition text is clarified (R-f, R-g).
- `docs/codebook/typed-statements-v1.md` and
  `docs/codebook/typed-statements-v1-coder-view.md` state R-f, R-g, and
  R-h identically, each with a worked example at a verbatim source
  offset.
- `vocabulary/actor-roles.json` and
  `statement.ACTOR_VOCABULARY_VERSION` are UNCHANGED
  (`typed-statements-v3`) — this addendum adds, removes, or
  reclassifies no actor role.

## Addendum B — codebook revision v3.2 (2026-10-04)

### Status

Accepted. Two of Addendum A's own teaching examples contradicted the
rules they were meant to illustrate. These fixes, and one further design
ruling (R-i, below), are recorded here as design choices, distinct from
the owner's own decisions, on the same convention this ADR already uses.

### Decision

**Corrected example 1 — `competence_of`'s own positive example 2.**
Pilot unit ai-act:0503's own text (AI Act Art. 74(3)) was cited as Art.
70(3) and used as a CONFERRAL example, but "...authorities responsible
for the enforcement of the Union harmonisation legislation..." is a
REDUCED RELATIVE identifying which authorities a different clause's
own subject ("Member States") must coordinate with — it confers
nothing, and the article citation was wrong. It is now
`competence_of`'s own negative example 3, correctly cited (Art. 74(3)),
illustrating the new R-j rule below; the true conferral clause AI Act
Art. 57(11) (the SAME paragraph as `performs`'s own positive example 2,
"National competent authorities shall have the power to temporarily or
permanently suspend the testing process...") replaces it as positive
example 2.

**R-j. The "responsible for" rule.** "Responsible for" counts as
conferral ONLY in a clause that ASSIGNS the responsibility — a finite
"is/are responsible for" main verb, with the institutional actor as
its own grammatical subject. A REDUCED RELATIVE that merely IDENTIFIES
which actor a different clause's own subject concerns ("...authorities
responsible for the enforcement of...", modifying "authorities", never
asserting a mandate ON them) does NOT confer anything — it stays
INSIDE the maximal NP (R-h), never a separate `competence_of`
Statement.

**Corrected example 2 — the UK DPA 2018 s. 6(1) worked example's own
`subj` span.** R-h's own worked example gave the chapeau's `subj` span
as the WHOLE chapeau sentence ("The definition of... has effect
subject to—"), including the leading determiner "The" and the
chapeau's own verb phrase — directly contradicting R-h's own
MAXIMAL-NP rule, which excludes a leading determiner and keeps the
span to the noun phrase itself. The corrected span is the byte-exact
maximal NP alone: `uk-dpa2018/source-ukpga-2018-12.txt#62386-62450`
("definition of "controller" in Article 4(1)(7) of the UK GDPR"), id
`definition_of_controller_in_article_4_1_7_uk_gdpr`.

**R-i. Coordinated NPs.** A coordination of DISTINCT entities ("X and
Y" naming two different things sharing a role, e.g. AI Act recital
text's own "employees and persons providing services through
platforms") gives ONE Statement per conjunct, with the shared
remainder of the clause INHERITED across all of them — the SAME
inheritance rule a chapeau list already uses (R-h). A coordination of
MODIFIERS within ONE entity ("systematic and extensive evaluation of
personal aspects relating to natural persons", GDPR Recital 91)
stays ONE maximal NP — "systematic" and "extensive" both modify the
SAME "evaluation", never two Statements. The test is the same
whole/part test `part_of`'s own direction-swap rule and the chapeau
rule already apply: does the coordination name DISTINCT things sharing
a role, or ONE thing with distinct qualities? The AI Act recital
example's own host clause ("should... involve") is `predication`, not
`applies_to` as first drafted — both pilot coders agreed on
`predication` for that clause; the conjunct split, not the predicate,
is the teaching point, and the example is corrected accordingly.

**R-i applies WITHIN a chapeau item, too.** A chapeau item that itself
coordinates distinct entities yields one Statement per conjunct, the
same way a bare coordinated clause does. GDPR Art. 32(1)'s own item
(a), "the pseudonymisation and encryption of personal data", drafted
in Addendum A as the `part_of` chapeau-list example, itself coordinates
TWO distinct measures ("pseudonymisation" and "encryption") sharing the
complement "of personal data" — under R-i it is corrected to TWO
Statements, `pseudonymisation_of_personal_data part_of
<the_chapeau's_whole>` and `encryption_of_personal_data part_of
<the_chapeau's_whole>`, the shared complement distributed to each,
rather than the single combined Statement Addendum A first gave. Item
(b) of the SAME list, "the ability to ensure the ongoing
confidentiality, integrity, availability and resilience of processing
systems and services", is kept as the contrasting case: it coordinates
four QUALITIES of the SAME "ability", not four distinct measures — ONE
maximal `subj` span, ONE Statement, never split.

### Consequences (Addendum B)

- `vocabulary/statement-predicates.json` bumps its own `version` field
  to `typed-statements-v3.2`, matched by
  `statement.PREDICATE_VOCABULARY_VERSION`; the predicate set and
  `PREDICATE_DIMENSION` mapping remain UNCHANGED — only
  `competence_of`'s own definition text gains R-j.
- `docs/codebook/typed-statements-v1.md` and
  `docs/codebook/typed-statements-v1-coder-view.md` state R-i and R-j
  identically, with both corrected examples and R-i's own two worked
  examples (the AI Act recital's coordination of distinct entities, the
  GDPR Recital 91 coordination of modifiers), each at a verified
  byte-exact source offset.
- `vocabulary/actor-roles.json` and
  `statement.ACTOR_VOCABULARY_VERSION` remain UNCHANGED
  (`typed-statements-v3`).

## Addendum C — codebook round, v3.3 (2026-10-04)

### Status

The owner approved this round of work (2026-10-04), ahead of the full
gold run. The five rulings below (R-k through R-o) are design choices, recorded here
as such and distinct from the owner's own decisions, on the same
convention this ADR already uses — only the approval decision above is
the owner's.

### Context

A blind re-pilot (two pinned Opus coders, v3.2 codebook) reached alpha
0.99 on both predicate and derived dimension (`repilot-scoring.md`
§3), far above the v3.2 pilot's own 0.753/0.765. Section 7b of that
same report records a separate finding: alpha
measures RELIABILITY (do the two coders agree), not CORRECTNESS (is
the shared answer right) — roughly 8 percent of paired statements
(range 5-15 percent) are agreement on a WRONG or ARGUABLE answer, a
SHARED blind spot neither coder's own disagreement rate would ever
surface. Five such patterns are named in `repilot-scoring.md` §7b,
grounded in `repilot-spotcheck.md`'s own unit-by-unit evidence; each is
ruled on below, with its own codebook examples drawn from OTHER
sentences in the same instruments — never the re-pilot units
themselves, so the next coding run is not taught its own answers.

### Decision

**R-k. No modal phrasing inside an endpoint span.** Pilot units
ai-act:0510 ("...that measure shall be deemed justified"), gdpr:0414
("...the decision shall by adopted by the vote of its Chair"), and
gdpr:0459 ("...each controller or processor shall be held liable for
the entire damage...") each show a shared blind spot: both coders left
a modal verb INSIDE the `obj` span. An endpoint span never contains
`shall`, `may`, `must`, `should`, `is to be`, or the fixed phrases
`shall be deemed`/`shall be held` — the endpoint is the NOUN PHRASE (or
residual predicate complement) the modal governs, stripped of the
modal itself; the modal is nD, never part of the Statement. This
extends the SAME principle `requires`'s and `performs`'s own
definitions already state for the word "obligation" to the MODAL VERB
ITSELF, wherever it sits inside what would otherwise be the span.

**R-l. "power(s) under X" / "power to..." is never an endpoint.** Pilot
unit uk-dpa2018:0206 codes a "powers under subsection (1)" clause as a
whole, not split by its own lettered list. A power is a deontic
permission — the SAME category as a right, already excluded from
endpoints — so it is never itself coded as a Statement's `subj`/`obj`.
Code the ACT the power COVERS instead: the holder `performs` the act,
or, when the text itself CONFERS the power on an institutional actor,
`competence_of` with that actor and the act (`competence_of`'s own
decisive test, R-f, already states which). A lettered list under
"powers under [provision] include power— (a)... (b)..." follows the
SAME chapeau rule (R-h) as any other chapeau: each item becomes an ACT
of the power's own holder, never a list of powers named as such.

**R-m. "exercise the right to X" is never an endpoint.** Pilot unit
gdpr:0138 ("...he or she should have the right to mandate a
not-for-profit body...") risks the right itself becoming an endpoint.
This is NOT a new rule — `performs`'s own positive example 1 already
states that a right is never an endpoint ("the right to obtain human
intervention" is coded as the controller's own act, never the right) —
R-m records the SAME rule applying to the "exercise the right to X"
surface form specifically, since a verb ("exercise") in front of
"right" makes it easy to mistake the verb's own object (the right) for
the endpoint, rather than X, the ACT the right concerns.

**R-n. Negation scope for a deadline.** Pilot unit gdpr:0082 ("Where
such notification cannot be achieved within 72 hours...") shows both
coders uncertain whether the deadline itself is negated. It is not: the
sentence states a CONDITION about meeting a deadline, never a denial of
the deadline. Rule: a negator attaching to the ACHIEVABILITY of a
deadline inside a conditional clause ("where/if... cannot be... within
N") makes the CONDITION Statement (`requires`, trigger -> consequence)
`negation: "present"`; the `deadline_of` Statement for the period N
itself stays `negation: "absent"` — N is not itself being denied, only
the achieving of something within it.

**R-o. "part of" is not a determiner to strip.** Both coders' own
agreement on pilot unit uk-dpa2018:0203 ("...include a part of a
record and a copy of all or part of a record") already does the RIGHT
thing — both kept "part of a record" whole and coded it `part_of`
against "references...to a record" — but the codebook's own
determiner-strip list (`a`, `an`, `the`, `one of (the)`, `part of`)
told the NEXT run to do the WRONG thing by stripping it. Ruling: REMOVE
`part of` from the determiner-strip list. Where the text names "part of
X" as a distinct entity (a component/portion of X), the span "part of
X" is kept WHOLE; where the text relates that component to a SEPARATE
named whole (as in uk-dpa2018:0203's own pattern, "references to Y
include a part of X"), it is coded as a `part_of` Statement, subj the
component ("part of X"), obj the whole — never silently collapsed by
stripping "part of" as if it were equivalent to "a"/"the".

### Consequences (Addendum C)

- `vocabulary/statement-predicates.json` bumps its own `version` field
  to `typed-statements-v3.3`, matched by
  `statement.PREDICATE_VOCABULARY_VERSION`; the predicate set and
  `PREDICATE_DIMENSION` mapping remain UNCHANGED — `competence_of`,
  `performs`, `requires`, `deadline_of`, and `part_of` each gain a short
  clarifying clause (R-l, R-m, R-n, R-o); `applies_to`, `cross_references`,
  `except_when`, `legislative_purpose_of`, `compliance_purpose_of`,
  `based_on`, `precedes`, `predication`, `is_a` are untouched.
- `docs/codebook/typed-statements-v1.md` and
  `docs/codebook/typed-statements-v1-coder-view.md` state R-k through
  R-o identically, each with its own worked example at a verified
  byte-exact offset, drawn from a sentence OTHER than the pilot unit
  that motivated the rule.
- `vocabulary/actor-roles.json` and
  `statement.ACTOR_VOCABULARY_VERSION` remain UNCHANGED
  (`typed-statements-v3`) — this addendum adds, removes, or
  reclassifies no actor role.
- §8 deliberately strips `part of` for parity with factual ebf9fe1;
  R-o applies to the typed-statement codebook only.

## Addendum D — codebook corrections, v3.4 (2026-10-04)

### Status

Accepted. Two blocking problems surfaced in Addendum C's own text.
**The first is an error in R-n's own ruling, not a correctness slip by
anyone else:** R-n's own ruling was WRONG about what `negation:
"present"` means. The corrected R-n below REPLACES the earlier R-n
wording in Addendum C. R-l and R-o are each refined,
without reversing their own core rulings. All as design choices,
recorded here and distinct from the owner's own decisions, on the same
convention this ADR already uses.

### Decision

**R-n (corrected — replaces Addendum C's own R-n).** The design's own
earlier wording said a negator attaching to a deadline's own
achievability makes the CONDITION Statement `negation: "present"`.
That is WRONG. Under §21, `negation: "present"` means the RELATION
ITSELF — the subj-predicate-obj triple — is negated, never merely that
a negator appears somewhere inside the antecedent's own descriptive
content. Corrected rule: a negator in an ANTECEDENT stays INSIDE the
`subj` span of the `requires` Statement it belongs to, and that
Statement's own RELATION is `negation: "absent"` — the antecedent, AS
STATED (with its own "cannot"/"unable"/"no" built in), genuinely
produces the consequence; nothing negates THAT fact. The companion
`deadline_of` Statement for a period N named in the consequence is
ALSO `negation: "absent"`, for the identical reason. Worked example:
"Where such notification cannot be achieved within 72 hours, [the
reasons for the delay should accompany the notification]" is `subj` =
"such notification cannot be achieved within 72 hours" (the FULL
antecedent, "cannot" INCLUDED), predicate `requires`, `negation:
"absent"`. For GDPR Art. 65(3), `subj` = "the Board has been unable to
adopt a decision within the periods referred to in paragraph 2" (full
antecedent, "unable" included), `negation: "absent"`; the companion
`deadline_of` for "two weeks following the expiration of the second
month referred to in paragraph 2" is ALSO `negation: "absent"`. R-k's
own positive example 2 (AI Act Art. 46(4), "no objection has been
raised...") follows the IDENTICAL pattern — `subj` includes "no",
`negation: "absent"` — so a coder meets ONE pattern for a
negator-in-the-antecedent, never two.

**R-l (refined) — rationale.** Rephrased: a power, like a right, is a
NORMATIVE POSITION (a competence), never an endpoint — not "a deontic
permission", this ruling's own earlier, less precise phrasing.

**R-l (refined) — the companion Statement.** The exercisability
condition illustrating R-l (UK DPA 2018 s. 115(5)) must NOT use the
power's own name as `subj` — doing so repeats R-l's own forbidden
pattern one level up, exactly the mistake R-l itself rules out. The
companion Statement's own `subj` is the ACT the power covers (the SAME
act the `performs` Statement already names: "require a controller or
processor to provide information that the Commissioner requires for
the performance of the Commissioner's tasks under the UK GDPR"),
predicate `requires`, `obj` = "giving an information notice under
section 142" — a GERUND-headed NOUN PHRASE, no finite verb phrase —
at the verified byte-exact span
`uk-dpa2018/source-ukpga-2018-12.txt#230081-230127` (the earlier
`#230075`-based figure was an approximation; `230081` is the real
byte-exact start of "giving").

**R-l — holders outside the unit.** An act's HOLDER is inherited ONLY
from a chapeau or a subject NAMED WITHIN THE SAME UNIT. Where a
chapeau's own holder is named only in a DIFFERENT unit — the exact
pattern behind pilot unit uk-dpa2018:0206's own "powers under
subsection (1)", where "subsection (1)" sits in a separate unit from
the list itself — the holder is NOT imported across the unit boundary.
The existing "pronoun or elided subject... is OUT OF SCOPE" rule
applies instead, and the clause gets NO Statement, never a guessed or
cross-unit holder.

**R-o (corrected example; new rule).** The example Addendum C gave (UK
DPA 2018 s. 184(6), "references to a relevant record include— a part
of such a record...") is NOT a genuine `part_of` case. Ruling:
"references to X include Y" is an INTERPRETIVE/DEFINITIONAL extension
clause — it stipulates that the TERM X, wherever referenced elsewhere
in the instrument, is to be READ as covering Y too. R-o's own worked
example is replaced with a genuine containment case drawn from
`part_of`'s own PRE-EXISTING positive example 1
(`gdpr/source-32016R0679.txt#155546-155580`, GDPR Art. 2(1), "which
form part of a filing system") — a true "X forms part of Y" relation,
RECODED as `personal_data part_of filing_system`: `subj` is the
relative pronoun's own ANTECEDENT in the same sentence, "personal
data" (`#155532-155545`), quoted at its own verified offset — never
the pronoun "which" itself, which has no span of its own; `form(s)
part of` is stated as a `part_of` VERB CUE in its own right. A SECOND
positive example is added, `uk-dpa2018/source-ukpga-2018-12.txt#288885-289064`
(UK DPA 2018 s. 148(2)(a)), in which a "part of Z" noun phrase ("all
or part of the information, document, equipment or material") is
itself an ENDPOINT of a DIFFERENT predicate (`performs`, naming the
person's own act), never the vacuous `part_of_Z part_of Z` pattern
this rule exists to rule out. The UK DPA 2018 s. 184(6) text is KEPT,
relabelled as a NEGATIVE example illustrating the new "references to
X include..." rule, below. "part of" REMAINS un-stripped from the
determiner list — R-o's own core ruling is UNCHANGED. Both new
examples are verified byte-exact and checked, by byte range, against
all four pilot packets (`pilot-packet-coder-a.json`,
`pilot-packet-coder-b.json`, `repilot-packet-coder-a.json`,
`repilot-packet-coder-b.json`) for non-overlap with any unit.

**R-o — design ruling: "references to X include Y" is `applies_to`.**
Refines the route stated just above: this surface form is coded
`applies_to` specifically — Y FALLS WITHIN THE SCOPE of the term X —
never `is_a` (it is not a fresh definition of a new term) and never
`part_of` (even where Y is, physically, a part of X's own referent).
`part_of`'s own definition, `applies_to`'s own definition, the
codebook, and the coder view all state this identically.

**R-m — id convention (cosmetic).** A Statement id is an invented
snake_case label, never a literal copy of the span text. R-m's own
worked example (GDPR Art. 78(1)) now uses an id that matches its own
span exactly, with no added verb ("an_effective_judicial_remedy...",
not "seek_an_effective_judicial_remedy..."); an id MAY instead add a
light verb where the predicate itself needs one to read as an act —
BOTH conventions are acceptable, stated explicitly so a coder is not
left guessing which one this codebook itself follows.

### Consequences (Addendum D)

- `vocabulary/statement-predicates.json` bumps its own `version` field
  to `typed-statements-v3.4`, matched by
  `statement.PREDICATE_VOCABULARY_VERSION`; the predicate set and
  `PREDICATE_DIMENSION` mapping remain UNCHANGED. `requires` and
  `deadline_of` restate the negation rule correctly; `competence_of`
  and `performs` restate the power/right rationale and the
  holder-inheritance rule; `part_of` adds the `form(s) part of` verb
  cue; `part_of` and `applies_to` both state the "references to X
  include Y" rule — `applies_to`, never `is_a`, never `part_of`.
- `docs/codebook/typed-statements-v1.md` and
  `docs/codebook/typed-statements-v1-coder-view.md` state the
  corrected R-n and the refined R-l and R-o identically, each with its
  own worked example re-verified byte-exact and checked, by byte
  range, against all four pilot packets (pilot-1 and re-pilot, coder A
  and coder B) for non-overlap with any unit.
- `vocabulary/actor-roles.json` and
  `statement.ACTOR_VOCABULARY_VERSION` remain UNCHANGED
  (`typed-statements-v3`).
- The codebook's own "R-n, corrected" / "replaces this ruling's own
  earlier wording" narration is REMOVED from its body text (it stated
  a fact about this ADR's own editing history, not a coding rule); that
  history lives here, in this ADR, only.

## Addendum E — codebook round, v3.5 (2026-10-05)

### Status

Accepted. These four rulings (R-p through R-s) are design (product-owner)
design choices, drafted from the T2 full-run negation recheck, recorded
here as such and distinct from the owner's own decisions — same
convention as the rest of this ADR. The predicate set and
`PREDICATE_DIMENSION` mapping
are UNCHANGED from v3; this addendum rewrites the negation procedure
and clarifies three unitisation rules. R-p.1 and R-p.2 (below) are a
same-day correction to R-p, made after a first review pass found the
initial R-p text still left a gap and the worked
examples carried wrong article labels, a dead cross-reference, and one
non-type example for R-s — all corrected below, as design choices, on the
same convention.

### Context

The T2 full run's model-model agreement measured negation alpha 0.774,
below the owner's own ≥ 0.80 bar. Present-vs-absent disagreement occurred
once in 3625 pairs; almost every disagreement involved `uncertain`
(absent↔uncertain 130 times, present↔uncertain 23 times). The coders
split along four gaps logged during the run.

### Decision

**R-p. Negation is rewritten around clause scoping.** `negation`
answers ONE question: does a negator take scope over THIS Statement's
own relation? `present` requires the negator to be in the Statement's
OWN clause and to scope over the relation. `absent` covers: no negator
in the Statement's own clause; a negator wholly inside an endpoint span
or an antecedent (R-n, generalised from the antecedent case to endpoint
spans generally); a fixed idiom ("not later than", "no later than",
"not less than", "no less than", "not exceeding", "whether or not",
"not only ... but also"); and — REPLACING the earlier procedure's own
step 4 — a negator in ANOTHER clause of the same sentence, which no
longer routes to `uncertain`: every Statement is clause-scoped, so a
negator elsewhere does not reach it. `uncertain` is used ONLY when the
negator is in the Statement's OWN clause and its scope over the
relation cannot be decided from the text. "Neither ... nor" joins the
closed negator list explicitly (it was already in §18's own digested
lexicon, but the codebook text did not previously name it), alongside
"nothing"/"none" (also already in §18's own lexicon, now also named
explicitly). The closed CUE list for `present`: "shall not", "may
not", "does not apply", "No X shall...", "Nothing in X prevents Y"
(and the structurally identical "Nobody"/"None of X"/"Neither X nor
Y" forms). For an exception carved from a negated rule ("X shall not
apply except where Y..."), the main-rule Statement is `present`; the
`except_when` Statement built from the carve-out clause is `absent`.

**R-p.1 — what counts as a clause.** A clause is a FINITE clause: a
subject plus a finite verb, INCLUDING a subordinate finite clause
("unless...", "where...", "if...", a relative clause with a finite
verb, a clausal complement such as a "that..." clause following a verb
like "demonstrates"). A prepositional phrase, a reduced relative, and a
participial phrase are NOT clauses — they belong to the clause they sit
in. This is the threshold question R-p's own "another clause" case
depends on: without it, a coder could not tell a citation PHRASE
("In the cases referred to in Article 11(2)") apart from the finite
clause it introduces.

**R-p.2 — closing the gap.** A first review pass found R-p's own
initial text left exactly the gap the T2 recheck exists to close: it
said what `absent` covers and what `uncertain` is "used ONLY" for, but
never said what happens when a negator sits in the Statement's OWN
clause yet plainly scopes something OTHER than the relation (an
adjunct, an endpoint) — a coder reading the first version could read
"in the Statement's own clause" alone as grounds for `uncertain`,
reintroducing exactly the "when in doubt" reflex the T2 recheck was
commissioned to remove. Ruling: when a negator sits in the Statement's
own clause but clearly scopes only over an adjunct or an endpoint, the
value is `absent` (a second review pass dropped "or a non-relational
part" from this sentence — it named no distinct case the "adjunct"/
"endpoint" wording did not already cover, and risked reading as its
own open-ended catch-all). `uncertain` remains ONLY for a negator in
the Statement's own
clause whose scope over the relation GENUINELY cannot be decided. There
is NO "when in doubt" default — `uncertain` is a POSITIVE finding that
the text itself is ambiguous, never a fallback for a coder's own
indecision; the codebook's own earlier "when in doubt... choose this
one" sentence is DELETED, in both documents, as the thing this ruling
exists to correct.

**R-q. The determiner strip/keep lists are stated explicitly.** The
`subj`/`obj` span's own leading-determiner strip list is EXACTLY `a`,
`an`, `the`, `one of (the)` — nothing else. The explicit keep list:
`this`, `that`, `these`, `those`, `such`, `each`, `every`, `any`,
`all`, `some` all stay INSIDE a span when they appear; they are
demonstratives and quantifiers, not determiners this codebook strips,
and most coders already treated them this way — R-q states it
explicitly rather than leaving it implicit.

**R-r. Pronouns.** This aligns the packet instruction with the coder
view; the coder view wins. If a pronoun's referent is named INSIDE THE
SAME UNIT, the Statement uses the referent's own span as the endpoint,
never the pronoun's own text. If no referent is named anywhere in the
unit, there is no Statement — record the unit out of scope if it has
no other Statement. This is not a reversal of the existing "pronoun or
elided subject is out of scope" rule; it refines it: a pronoun with a
resolvable IN-UNIT referent was never meant to be out of scope, and the
codebook's own pre-existing `part_of` worked example (GDPR Art. 2(1)'s
"which form part of a filing system", resolving "which" to its own
antecedent "personal data" in the same sentence) already did the RIGHT
thing — R-r simply states the general rule that example was already
following.

**R-s. Disjunctive type lists.** A disjunctive list of TYPES under one
determiner (GDPR Art. 4(7)'s own "natural or legal person, public
authority, agency or other body", the opening of the "controller"
definition) is ONE noun phrase, never split into one Statement per
type — this is distinct from the coordinated-DISTINCT-entities rule
(R-i), which splits a bare "X and Y" naming two different NAMED things
sharing a role. The test is the SAME whole/part test R-i and the
chapeau rule already use: does the construction name distinct things
sharing a role, or one disjunctively-typed kind under a single
determiner? R-s composes with the ordinary MAXIMAL-NP rule: the Art.
4(7) example's own `obj` span is the WHOLE relative-clause-including
NP (`gdpr/source-32016R0679.txt#159830-159999`), not merely the
disjunction's own head nouns — a second review pass caught the first
Art. 4(7) worked example stopping short at "other body" instead of
extending through the relative clause the maximal-NP rule already
requires. (The codebook's own FIRST worked example for this rule used
"an identified or identifiable natural person" — two ADJECTIVES
modifying one noun, not a disjunctive TYPE list at all; an earlier
review pass caught this, and both documents now use the Art. 4(7)
example instead.)

**C. New source text in worked examples, and the check.** New
source text in a worked example IS allowed, provided the check has
VERIFIED that it overlaps no T2 full-run unit — this is in addition
to, never a substitute for, the separate dev-gold-300 overlap check a
maker runs by script. The This check verified the byte ranges
`gdpr/source-32016R0679.txt#159803-159893` (the Art. 4(7) "controller"
definition's own opening), `#181710-182071` (GDPR Art. 12(2)'s own
FIRST AND SECOND sentences together), `#180650-180660` ("such
cases"), `#155532-155580`
(the `part_of` worked example's own antecedent-through-obj span), and
`#157742-157840` (the Art. 4(1) "personal data" definition, already in
use before this round) against all 1,477 full-run units' own
`source_span` fields. None of the five overlaps any full-run unit.
**Extended check (design, 2026-10-05):** R-s's worked example extends the
Art. 4(7) span to `#159830-159999` (through the relative clause, per the
maximal-NP rule). The This check was re-run the same check over `#159803-159999`
against all 1,477 full-run units' `source_span` fields: no overlap.

### Consequences (Addendum E)

- `vocabulary/statement-predicates.json` bumps its own `version` field
  to `typed-statements-v3.5`; the predicate set and `PREDICATE_DIMENSION`
  mapping remain UNCHANGED.
- `docs/codebook/typed-statements-v1.md` and
  `docs/codebook/typed-statements-v1-coder-view.md` restate the
  negation procedure identically around R-p (including R-p.1 and
  R-p.2), and state R-q, R-r, and R-s identically, each with its own
  worked example drawn from a sentence already quoted elsewhere in the
  codebook, from new source text that the this check verified against all T2
  full-run units (no byte overlap), or from a constructed/schematic
  example.
- `vocabulary/actor-roles.json` and `statement.ACTOR_VOCABULARY_VERSION`
  remain UNCHANGED (`typed-statements-v3`) — this addendum adds,
  removes, or reclassifies no actor role.
- The T2 full run's own 1177 held-out units keep their v3.4 negation
  labels, flagged as such — re-labelling negation on them is a separate
  decision, out of scope for this addendum.
- **Same-day corrections to the FIRST pass of this
  addendum, caught by a later review, all recorded here as design
  choices:** (1) three article labels corrected against
  the local corpus's own `gdpr/source-32016R0679.txt` at their own byte
  offsets — the "Articles 15 to 20 shall not apply..." Statement is
  GDPR Art. 11(2), never "Art. 23(1)"; the "In the cases referred to in
  Article 11(2)..." sentence is GDPR Art. 12(2), never "Art. 11(2)"
  itself; "whether or not by automated means" is GDPR Art. 4(2) (the
  "processing" definition), never "Art. 4(1)" (the "personal data"
  definition the quote sits next to); (2) the "negator in another
  clause" worked example is replaced with a genuine two-FINITE-clause
  pair from GDPR Art. 12(2) (the main clause and its own "unless..."
  clause), quoted to 59 characters or fewer per fragment, with
  byte-exact offsets; the carved-exception example now names the
  `applies_to` Statement's own `obj` ("such cases",
  `gdpr/source-32016R0679.txt#180650-180660`) explicitly; (3) the
  coder view's dead cross-references (pointers to quotes the coder
  view itself does not contain) are either inlined or repointed to
  where the quote actually sits in that document; the full codebook's
  "extends step 5" phrasing, which named a step number that no longer
  exists under this round's renumbering, now names `requires`'s own
  R-n rule instead; (4) `part_of`'s own positive example 1 (GDPR Art.
  2(1), "which form part of a filing system") corrects its own `obj`
  span to "filing system" (`#155567-155580`), stripping the leading
  "a" per R-q — the span had kept "a filing system" whole by mistake,
  confusing an ORDINARY `obj` span (which strips a leading "a"/"the")
  with a "part of Z" span (which R-o says never to strip); the R-r
  pronoun example that reuses this same sentence only cites the
  `subj` span and is unaffected.
- `tests/test_conformance.py`'s own literal
  `assert doc["version"] == "typed-statements-v3.5"` (added in this
  addendum's first pass, before the code constant itself was bumped)
  is removed now that the code constant and the JSON vocabulary are
  both `typed-statements-v3.5` and the ordinary parity assertion
  (`doc["version"] == statement.PREDICATE_VOCABULARY_VERSION`) covers
  the same ground without pinning a second, redundant literal.
