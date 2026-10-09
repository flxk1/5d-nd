# Coder view: typed statements (dimension-blind), v3.6

v3.6 ADDS ONE new predicate, `addressed_to` (see the
table below), and a deterministic deadline SPLIT for `deadline_of`
(also below). Every other predicate is UNCHANGED from v3.5. v3.1 and
v3.2 state the
`performs`/`competence_of` test (including its "responsible for"
conferral rule), the "subject to" routing, the span rules, and the
coordinated-NP rule (R-i); v3.3 and v3.4 state five further rules
(R-k through R-o): no modal inside an endpoint span, power as a
never-endpoint, the right-as-endpoint rule extended to "exercise the
right to X", negation scope for a conditional antecedent, and the
"part of" determiner fix (including "form(s) part of" as its own verb
cue, and "references to X include Y" as `applies_to`); v3.5 rewrites
the negation procedure (R-p, below), states the closed determiner-strip
list and keep list explicitly (R-q), states the pronoun-referent rule
(R-r), and states the disjunctive-type-list-under-one-determiner rule
(R-s) — all below. See
`docs/decisions/0008-typed-statement-v3-rulings.md` for these
rulings and their history.

This is the document a CODER works from. It names every predicate's own
fact pattern — the thing to look for in the text — with no mention of
which coordinate axis it will later be filed under. Pick a predicate
from its fact pattern alone. The coordinate is looked up automatically
afterward, from a closed mapping a coder never consults while coding —
a coder never reasons from "which axis should this be" toward a
predicate.

**Modal force is never one of these.** An obligation, a permission, or a
prohibition is coded separately (a different concern entirely, never one
of the fact patterns below). If the ONLY thing a clause does is state a
modal obligation with no further content, use `predication` — do not
invent a reading to avoid it.

**No right, obligation, permission, or POWER is ever a Statement
endpoint.** A power, like a right, is a NORMATIVE POSITION (a
competence). Where the text names a RIGHT or a POWER ("power(s) under
X", "power to X", "exercise the right to X"), code the underlying act
or measure instead (who provides it, what it consists of), never the
right or the power itself — see "Span granularity", below, for both
worked examples.

**No MODAL verb is ever inside an endpoint span.** `shall`, `may`,
`must`, `should`, `is to be`, and the fixed phrases `shall be deemed`/
`shall be held` never appear inside an endpoint — strip the modal, keep
only the residual noun phrase or predicate complement it governs; the
modal itself is coded separately, never part of the fact pattern below.

| predicate | fact pattern — what to look for |
|---|---|
| `is_a` | `'X' means ...` — a legal/legislative definition |
| `part_of` | X is a component or named sub-unit of Y (part-to-whole — if the text names the WHOLE first, "X includes Y", swap: code `Y part_of X`). `form(s) part of` is a `part_of` VERB CUE. "part of" is NOT a determiner to strip — "part of Z" names a distinct entity, kept WHOLE as X, `part_of` the separate named whole Y, where the relation is a GENUINE containment (or kept WHOLE as an endpoint of a DIFFERENT predicate entirely — never stripped either way). "References to Z include Y" is a DIFFERENT pattern — Y falls within the scope of the TERM Z — coded `applies_to`, never `is_a`, never this |
| `applies_to` | the instrument's own applicability is fixed onto X, including a clause that keeps the rule in force DESPITE a named FACT OR CIRCUMSTANCE (`notwithstanding the fact that...`) OR a thing merely QUALIFIED by a provision ("the terms...referred to in paragraph 1" — head noun "terms", not "paragraph"). "References to X include Y" is ALSO this: Y falls within the scope of the TERM X, never `is_a`, never `part_of` |
| `cross_references` | a citation to another article/section, including a savings clause (`without prejudice to X`, `shall not affect X`) — a non-overriding link, never a derogation and never a negated scope claim; the "not" in "shall not affect X" is part of the cue, never a negator |
| `except_when` | X's own general rule does NOT apply under condition Y — cues: `unless`, `except`, `by way of derogation from` (or `by derogation from`), `save where`, PLUS `notwithstanding`/`irrespective of`/`subject to` ONLY when Y's own HEAD NOUN is itself a provision reference (a paragraph, Article, section, subsection, point, subparagraph, or named act: `notwithstanding paragraph 2`, `subject to subsection (2)`) |
| `enables` | X makes Y possible or PRODUCES Y as a mechanism, with no stated purpose and no legal-ground claim |
| `requires` | when X happens, Y (an ACT, no modal inside its own span) follows as its consequence; also covers `subject to [a condition or requirement]` whose own head noun is NOT a provision reference (e.g. `subject to appropriate safeguards`). A negator INSIDE THE ANTECEDENT ("cannot", "unable", "no") stays INSIDE X, as part of what the antecedent SAYS — `negation: "present"` means the RELATION ITSELF is negated, which this never does, so the Statement is `negation: "absent"` (see `deadline_of`, below, for the companion rule) |
| `legislative_purpose_of` | X (an instrument/provision) is intended to / aims to bring about Y — NO modal, usually a recital |
| `compliance_purpose_of` | X is done FOR Y, inside a binding obligation (a modal + "for the purpose of") |
| `based_on` | Y is the stated LEGAL GROUND that justifies X — never the mechanism that PRODUCES X (that is `enables`), and never a "where X is based on Y, [modal] Z" trigger clause (that is `requires`) |
| `precedes` | X happens BEFORE Y (`prior to`, `before`) |
| `deadline_of` | Y names a fixed time window or deadline for X. A negator about meeting this deadline ("where/if... cannot be achieved... within Y") stays INSIDE the antecedent of the SEPARATE `requires` Statement it is part of; it negates the RELATION of neither Statement, so THIS one, naming Y itself, stays `negation: "absent"` — the SAME as its own companion `requires` Statement |
| `predication` | an ordinary statement/obligation that fits none of the above |
| `competence_of` | X is an institutional body (an authority, a board, a notified body, a coordinator, a CSIRT — never a controller/processor/provider/deployer/data subject) AND the text CONFERS or ESTABLISHES a task or power on X — "shall be competent", "is responsible for", "shall have the task/power to", OR Y is one item of X's own enumerated task/power list. An institution EXERCISING an already-granted power ("shall exercise its powers...", "may request...") is `performs`, not this — even when the word "powers" appears. "Responsible for" counts as conferral ONLY in a clause that ASSIGNS the responsibility (a finite "is/are responsible for" main verb, with X as its own grammatical subject) — NEVER in a reduced relative that merely IDENTIFIES X ("...authorities responsible for the enforcement of..."); such a relative stays INSIDE the maximal NP (see Span granularity, below), never a separate Statement. A power, like a right, is a NORMATIVE POSITION (a competence) — NEVER Y here — use this predicate only when the text CONFERS the power; where it merely DESCRIBES an existing power, code the act it covers as `performs` instead. An act's own HOLDER is inherited only from a chapeau or subject NAMED WITHIN THE SAME UNIT, never a different one. |
| `performs` | X (any actor) does Y, once the modal is stripped, and `competence_of`'s own CONFERS/ESTABLISHES test does not hold (including an institution merely EXERCISING an already-granted power). Y is the ACT a POWER or a RIGHT covers, when the power/right is merely DESCRIBED — a power, like a right, is a NORMATIVE POSITION (a competence); "power(s) under Z" / "power to Z" and "the right to Z" / "exercise the right to Z" are NEVER themselves Y. A Statement id may add a light verb (e.g. "seek_Z" for a Y span naming only "Z") to read as an act, where this predicate needs one |
| `addressed_to` (NEW v3.6) | X (the act or communication itself — the SAME act a companion `performs`/`competence_of`/`requires` Statement already names) runs TO Y, the recipient — cue: notify/report/inform/communicate/submit/transmit + Y, either via an explicit "to" ("notify ... to Y") or as a direct object ("notify Y", "inform Y"). Y must itself read as a recipient (a closed `ACTOR_ROLES` surface form, or a generic authority/body/Member-State/recipient-shaped NP) — a bare infinitive or scope phrase riding the SAME word "to" ("to the extent that", "to ensure", "in relation to", "to be") is NEVER this. Y is TYPED: the closed `ACTOR_ROLES` token where it matches, otherwise `other(label)`. LAYERED on top of whatever predicate already claims the host clause — never competes for, never blocks, that clause's own span. `negation: "absent"` by construction, the SAME reason as `deadline_of` |

**If a clause genuinely fits two patterns at once** (most often `requires`
plus a purpose/legal-ground pattern, or `requires` plus `precedes`/
`deadline_of`): code it as MULTIPLE Statements, one per pattern, from the
SAME clause. Do not force a single predicate onto a clause that
genuinely carries two distinct facts.

**v3.6's own deadline SPLIT.** A time limit FUSED into an action phrase,
in a spelled-out-number duration ("not later than N days/weeks/months")
or a qualitative cue ("without undue delay", "promptly", "immediately")
— the TWO cues v3.6 adds — is its OWN `deadline_of` Statement,
co-existing with whatever predicate already claims the host clause, the
SAME way `addressed_to` does above — never forcing a choice between
naming the act and naming its own deadline. The pre-existing, digit-
based "within N" cue keeps its own original conflict behaviour
unchanged. `deadline_of`'s own Y, for every cue, is the NORMALISED limit
("72 hours after having become aware of it" becomes "72 hours"), never
a raw, untrimmed span. X is the GOVERNED ACT the time limit times —
NEVER a clause subject, a fragment, a connective, or a pronoun — bound
to a companion `addressed_to`/`performs`/`competence_of` Statement from
the SAME clause, or a TRUSTED `requires`/`except_when` reading (never
a one-word antecedent misfire, a "subject to [condition]" cue, or a
provision-reference cue) — and, for `requires`, only when the time
limit sits in the CONSEQUENCE, never the antecedent (an antecedent-
embedded time limit keeps the Statement's own ORIGINAL X unchanged
instead). When none of these exist: a NEW cue's own Statement is
DROPPED; the pre-existing digit cue's own Statement keeps its ORIGINAL
X unchanged rather than being dropped or coded with a wrong X.

**The one pair you may be asked to code BOTH ways, as two separate
Statements sharing a middle term:** a clause that genuinely reads as
both a trigger-makes-it-happen fact AND a goal/justification fact at
once. Code it as two Statements — one of each pattern — with the first
Statement's own Y set equal to the second Statement's own X (so the two
chain together: X1 → Y1=X2 → Y2).

**If nothing fits and the clause has a resolvable subject**: use
`predication`. **If the clause has no resolvable subject at all** (a bare
heading, a dropped-subject list fragment): code NO Statement at all —
this is out of scope, not `predication`.

**Pronouns (R-r, v3.5).** A pronoun ("it", "they", "which", "who") is
NOT automatically out of scope. If the pronoun's referent is NAMED
INSIDE THE SAME UNIT (the same sentence or the same chapeau+list unit),
the Statement uses the REFERENT's own span as the endpoint, never the
pronoun itself — worked example: GDPR Art. 2(1)'s own "which form part
of a filing system" (quoted in full below, "Span granularity", `part of`
is NOT a determiner, Example 1) — the relative pronoun "which" has its
own antecedent, "personal data", named earlier in the SAME sentence;
the Statement's X span is "personal data" (the antecedent), never
"which". If NO referent is named ANYWHERE in the unit, there is no
Statement at all for that clause — record the unit out of scope if it
has no other Statement (the SAME "no Statement" outcome the
bare-heading/dropped-subject case above already uses, now extended
explicitly to a pronoun with no in-unit referent).

## Span granularity (what counts as a clause span and a subj/obj span)

- ONE clause per Statement — never a whole sentence with multiple
  clauses coded as one Statement, and never a sub-clause phrase coded
  alone, EXCEPT a chapeau list item, whose own clause span IS the item
  (below).
- The clause span is the SMALLEST COMPLETE clause that carries the
  relation — not the whole sentence it sits in, and not a fragment that
  drops part of the relation's own content.
- `subj`/`obj` spans are MAXIMAL noun phrases, INCLUDING their own
  modifiers, EXCLUDING a leading determiner — **the closed strip list
  (R-q, v3.5) is EXACTLY**: "a", "an", "the", "one of (the)". Nothing
  else is stripped: "part of" is NOT on this list (see `part_of`'s own
  row, above — "part of Z" is kept WHOLE), and neither is a demonstrative
  or a quantifier. **The explicit keep list (R-q)**: "this", "that",
  "these", "those", "such", "each", "every", "any", "all", "some" all
  stay INSIDE the span when they appear — these are not determiners this
  codebook strips, they carry their own quantificational content. Keep
  the WHOLE descriptive phrase together — "appropriate technical and
  organisational measures" is one span, never trimmed to "measures"
  alone. A REDUCED RELATIVE inside the NP that merely IDENTIFIES the
  entity ("...authorities responsible for the enforcement of...") stays
  INSIDE the maximal NP, never split out into its own Statement.
- **A disjunctive list of types under ONE determiner is ONE noun
  phrase (R-s, v3.5).** A shared determiner governing a disjunction of
  TYPES names ONE (disjunctively typed) kind of entity, never split
  into one Statement per type — this is NOT the coordinated-DISTINCT-
  entities rule (above), which splits a bare "X and Y" naming two
  different NAMED things sharing a role (contrast: "employees and
  persons providing services through platforms" names two DIFFERENT
  things and IS split). The test is the SAME whole/part test the
  coordinated-NP rule already uses: does the construction name DISTINCT
  things sharing a role, or ONE type-disjunctive kind under a single
  determiner? R-s ALSO composes with the ordinary MAXIMAL-NP rule
  (below, "Span granularity"): the disjunction's own span is the WHOLE
  noun phrase, modifiers included, not merely the disjunction's own
  head nouns. Worked example — GDPR Art. 4(7)'s own definition of
  "controller". The `is_a` Statement's own `obj` span is the WHOLE
  maximal NP, `gdpr/source-32016R0679.txt#159830-159999` (EXCLUDING
  the leading "the" per R-q), spanning from "natural or legal person"
  (`#159830-159853`) through "public authority, agency or other body"
  (`#159855-159893`) and on through the relative clause that follows
  (`#159894-159999`, quoted in the two short fragments below, under
  "the relative clause ALSO yields its own Statement"). This is ONE
  noun phrase under the single determiner "the": the disjunction of
  types stays inside it, never split by type, AND the relative clause
  that follows stays inside it too, per the ordinary MAXIMAL-NP rule —
  the SAME span, not merely the disjunction's own head nouns, is what
  the `is_a` Statement's own `obj` names.

  **The relative clause ALSO yields its own Statement (R-r, R-p.1).**
  The relative clause spanning `gdpr/source-32016R0679.txt#159894-159999`
  is a FINITE relative clause (R-p.1: a relative clause with a finite
  verb IS a clause). Its own subject, the relative pronoun "which",
  resolves to its antecedent NAMED EARLIER IN THE SAME SENTENCE — the
  disjunctive NP itself — exactly the SAME treatment R-r already gives
  a relative pronoun, and the SAME treatment the Span-granularity bullet
  "'part of' is NOT a determiner" already gives "which form part of a filing system" (GDPR
  Art. 2(1)), below. Coded `performs`: X is the antecedent, the
  disjunctive NP, `#159830-159893` (the SAME span the `is_a` Statement
  above already names — NOT the relative pronoun "which" itself, which
  has no span of its own); Y is "purposes and means of the
  processing of personal data" (`#159946-159999`, leading "the" stripped per R-q); the verb
  "determines" (the act itself; a light verb in the Statement id may
  restore it) sits in between, within `#159894-159941`
  ("which, alone or jointly with others, determines"), EXCLUDED from
  both endpoints.
- No MODAL verb is ever inside an endpoint span: `shall`, `may`, `must`,
  `should`, `is to be`, `shall be deemed`/`shall be held` never appear
  inside X or Y — strip the modal, keep only the residual noun phrase or
  predicate complement. Example 1: "Regarding the draft decision
  referred to in paragraph 1 circulated to the members of the Board in
  accordance with paragraph 5, a member which has not objected within a
  reasonable period indicated by the Chair, shall be deemed to be in
  agreement with the draft decision." — Y is "in agreement with the
  draft decision", EXCLUDING "shall be deemed to be". Example 2: "Where, within 15 calendar days of receipt of the information referred to in paragraph 3, no objection has been raised by either a Member State or the Commission in respect of an authorisation issued by a market surveillance authority of a Member State in accordance with paragraph 1, that authorisation shall be deemed justified." — X includes "no" (a negator INSIDE the antecedent stays inside X,
  see "Negation", below, `absent` case 2), Y is "justified", EXCLUDING "shall be
  deemed"; Y = "shall be deemed justified" (INCLUDING the modal) is the
  forbidden, WRONG span.
- No right, obligation, permission, or POWER is ever X or Y. A power,
  like a right, is a NORMATIVE POSITION (a competence), the SAME
  category as a right: "power(s) under Z" / "power to Z" is never
  itself an endpoint. Code the ACT the power covers instead — the
  holder `performs` the act, or, when the text itself CONFERS the power
  on an institutional actor, `competence_of` with that actor and the
  act. An act's own HOLDER is inherited only from a chapeau or a
  subject named WITHIN THE SAME UNIT, never a different one. Example:
  "The Commissioner's power under Article 58(1)(a) of the UK GDPR
  (power to require a controller or processor to provide information
  that the Commissioner requires for the performance of the
  Commissioner's tasks under the UK GDPR ) is exercisable only by
  giving an information notice under section 142." — X is
  `commissioner`, Y is "require a controller or processor to provide
  information that the Commissioner requires for the performance of
  the Commissioner's tasks under the UK GDPR" (`performs`, since the
  power is DESCRIBED, not conferred); never Y = "The Commissioner's
  power under Article 58(1)(a) of the UK GDPR" (the power's own name).
  The exercisability condition is a SEPARATE Statement whose OWN X is
  the SAME act, never the power's own name either: X = "require a
  controller or processor to provide information that the Commissioner
  requires for the performance of the Commissioner's tasks under the UK
  GDPR", Y = "giving an information notice under section 142" (a
  gerund-headed noun phrase, no finite verb). The same rule covers "the
  right to Z" / "exercise the right to Z": "Without prejudice to any
  other administrative or non-judicial remedy, each natural or legal
  person shall have the right to an effective judicial remedy against a
  legally binding decision of a supervisory authority concerning
  them." — Y is "an effective judicial remedy against a legally binding
  decision of a supervisory authority concerning them", EXCLUDING "the
  right to"; never Y = "the right to an effective judicial remedy
  against a legally binding decision of a supervisory authority
  concerning them" (the right itself).
- A coordination of DISTINCT entities ("X and Y" naming two different
  things) gives ONE Statement per conjunct, with the shared remainder
  of the clause INHERITED across all of them — the same inheritance a
  chapeau list uses (below). Example: "employees and persons providing
  services through platforms" is TWO Statements, sharing the SAME X, a
  DIFFERENT Y per conjunct ("employees" / "persons providing services
  through platforms"), never one Statement naming both together. A
  coordination of MODIFIERS within ONE entity stays ONE maximal NP:
  "systematic and extensive evaluation of personal aspects relating to
  natural persons" is ONE span — "systematic" and "extensive" both
  modify the same "evaluation", never split in two.
- List items under a chapeau: code ONE Statement per item, and the
  clause span is the ITEM, not the whole chapeau+list sentence. The
  SUBJECT is INHERITED from the chapeau — the chapeau's own named actor
  or trigger becomes the shared X of every item Statement; each item
  supplies only the differing Y. Example: "The definition of
  “controller” in Article 4(1)(7) of the UK GDPR has effect subject
  to— a subsection (2), b section 209, and c section 210." is THREE
  Statements — `definition_of_controller_in_article_4_1_7_uk_gdpr
  except_when subsection_2`,
  `definition_of_controller_in_article_4_1_7_uk_gdpr except_when
  section_209`, `definition_of_controller_in_article_4_1_7_uk_gdpr
  except_when section_210` — the SAME X (MAXIMAL-NP span: "definition
  of “controller” in Article 4(1)(7) of the UK GDPR", EXCLUDING the
  determiner "The" and EXCLUDING the chapeau's own verb phrase "has
  effect subject to—"), a DIFFERENT Y per item, never one Statement
  naming all three provisions together.
- A WHOLE-naming chapeau works the SAME rule in the other direction:
  the differing element per item is X, and the chapeau's own entity is
  the shared Y (the `part_of` variant, since `part_of`'s own direction
  is always part-to-whole). The coordination rule above applies WITHIN
  a chapeau item, too: a chapeau item that itself coordinates distinct
  entities yields one Statement per conjunct, exactly like a bare
  coordinated clause. Example: "appropriate technical and
  organisational measures to ensure a level of security appropriate to
  the risk" is the WHOLE, named by a chapeau followed by a lettered
  list; item (a), "the pseudonymisation and encryption of personal
  data", itself coordinates TWO distinct measures sharing the
  complement "of personal data", and is TWO Statements, the shared
  complement distributed to each: `pseudonymisation_of_personal_data
  part_of appropriate_technical_and_organisational_measures...` and
  `encryption_of_personal_data part_of
  appropriate_technical_and_organisational_measures...` — the SAME Y
  (the whole) in both, a DIFFERENT X per conjunct. Item (b), by
  contrast, "the ability to ensure the ongoing confidentiality,
  integrity, availability and resilience of processing systems and
  services", coordinates four QUALITIES of the SAME "ability", not four
  distinct measures — ONE maximal X span, ONE Statement, never split.
- "part of" is NOT a determiner — never stripped, whether the "part
  of Z" span is itself coded `part_of` (example 1) or kept whole as an
  endpoint of a DIFFERENT predicate entirely (example 2). `form(s)
  part of` is a `part_of` VERB CUE. Example 1: "which form part of a
  filing system" — the relative pronoun "which" has its own antecedent
  earlier in the SAME sentence, "personal data"; X is the ANTECEDENT
  "personal data" (never "which" itself), `part_of` Y ("filing
  system" — an ORDINARY `obj` span here, not a "part of Z" span in its
  own right, so its own leading "a" IS stripped per the determiner-strip
  list, R-q). Example 2: "It is an offence for the person— a to destroy
  or otherwise dispose of, conceal, block or (where relevant) falsify
  all or part of the information, document, equipment or material" —
  coded `performs`, NOT `part_of`: Y is "all or part of the
  information, document, equipment or material", kept WHOLE, as the
  object of the person's own act — never the vacuous
  `part_of_the_information part_of the_information` pattern this rule
  exists to rule out. "X include(s) Y" chapeau text is NOT
  automatically `part_of`: "references to a relevant record include—
  a part of such a record, and a copy of, or of part of, such a
  record." EXTENDS the TERM "relevant record"'s own meaning to also
  cover "a part of such a record" — Y FALLS WITHIN THE SCOPE of the
  term "relevant record", coded `applies_to`, never `is_a`, never
  `part_of`, even though "a part of such a record" is, read alone, a
  genuine physical component. The span "a part of such a record"
  still stays WHOLE either way ("part of" is never stripped) — only
  the PREDICATE differs.

## Layer

Every Statement also gets a `layer`, decided from the clause's own text
POSITION and FUNCTION — never from which predicate you just picked.
Apply these four checks IN ORDER; stop at the first one that matches:

1. Is the clause a definition, or part of a definitional sentence (an
   article that says "'X' means ...", wherever it sits)? → `deep`.
2. Is the clause stating a PRINCIPLE as a principle (a foundational
   statement, not a specific operative rule)? → `deep`.
3. Is the clause in a recital (an unenacted "whereas" paragraph, not an
   operative article)? → `surface` — UNLESS check 1 or 2 already
   matched its own content, in which case that earlier answer stands.
4. Anything else (an ordinary operative article clause) → `domain`.

## Negation (v3.5)

`negation` answers ONE question, and only one: does a negator take
scope over THIS Statement's own relation (the X-predicate-Y triple as a
WHOLE)? Every Statement gets a `negation`, one of three values —
`present`, `absent`, `uncertain`.

**R-p.1 — what counts as a clause.** A clause is a FINITE clause: a
subject plus a finite verb, INCLUDING a subordinate finite clause
("unless...", "where...", "if...", a relative clause with a finite
verb, a clausal complement such as a "that..." clause following a verb
like "demonstrates"). A prepositional phrase, a reduced relative, and a
participial phrase are NOT clauses — they belong to the clause they sit
in. Worked example — GDPR Art. 12(2)'s own
"In the cases referred to in Article 11(2)" is a PREPOSITIONAL PHRASE
(headed by "In"), not a clause — it belongs to the finite clause it
introduces, "the controller shall not refuse to act...", never a clause
of its own. This does NOT mean the phrase gets no Statement at all: it
still yields its own `cross_references` Statement (citing "Article
11(2)"), whose own `negation` is `absent` under R-p.2: the clause's
negator "shall not" scopes only the refuse-relation, never the
citation relation → `absent` (R-p.2).

**R-p.2 — closing the gap.** When a negator sits in the Statement's OWN
clause but clearly scopes only over an ADJUNCT, an endpoint — never the relation
itself — the value is `negation: "absent"`. `uncertain` remains ONLY
for a negator in the Statement's own clause whose scope over the
relation GENUINELY cannot be decided from the text. There is NO "when
in doubt" default: `uncertain` is a POSITIVE finding that the text
itself is ambiguous, never a fallback for a coder's own indecision.
Worked example (adjunct scope → absent; constructed, not quoted
statute text): "The authority shall publish the register, not in
draft form, within fourteen days." — the negator "not" scopes only
the adjunct "in draft form" (the MANNER of publication), never the
main relation "the authority publishes the register within fourteen
days" — `negation: "absent"`. Worked example (genuinely undecidable
scope → uncertain; constructed, not quoted statute text): "The board
may not necessarily act." — two readings are both available and the
text does not decide between them: (i) "not" scopes "may" itself, so
the board IS NOT PERMITTED to act (a prohibition); (ii) "not" scopes
only "necessarily", so the board IS permitted to act, but IS NOT
REQUIRED TO (a permission, merely not a mandatory one) — `negation:
"uncertain"`.

**The negator lexicon.** "not", "no", "never", "nothing", "none",
"neither ... nor", or one of their inflected forms (a closed,
pre-digested list; do not invent new negators). "Neither ... nor" is ON
this list (v3.5): it is a negator the same way "not"/"no"/"never" are,
never treated as a plain coordinator. An `except_when` cue ("unless",
"except", "by way of derogation from", "save where") is never itself a
negator — it routes a clause to a DIFFERENT predicate (`except_when`),
never to `negation: "present"`. The "not" in a savings clause ("shall
not affect X", "does not affect X") is part of the savings cue, never a
negator: a savings `cross_references` is `negation: "absent"` unless a
separate negator applies.

**`present`.** A negator is in the Statement's OWN clause and it scopes
over the predicate linking X and Y. The closed CUE list for this case:
"shall not", "may not", "does not apply", "No X shall...", "Nothing in
X prevents Y" (and the structurally identical "Nobody"/"None of X"/
"Neither X nor Y" forms). Worked example — GDPR Art. 11(2)'s own
"Articles 15 to 20 shall not apply except where the data subject, for
the purpose of exercising his or her rights under those articles,
provides additional information enabling his or her identification.":
the `applies_to` Statement on "Articles 15 to 20 shall not apply" is
`negation: "present"` — "not" is in the Statement's own clause and
negates the applicability relation itself. (The SEPARATE `except_when`
Statement built from the SAME sentence's "except where..." clause is
`negation: "absent"` — see the dedicated rule below.)

**`absent`.** Any of the following:

1. **No negator at all in the Statement's own clause.** Worked example —
   GDPR Art. 2(1)'s own "This Regulation applies to the processing of
   personal data wholly or partly by automated means": no negator
   anywhere in the clause → `negation: "absent"`.
2. **The negator lies wholly inside an endpoint span or inside an
   antecedent.** This is the SAME rule stated above for `requires`'s
   own "A negator INSIDE THE ANTECEDENT..." row (R-n), extended to
   cover an endpoint span generally, not only an antecedent. Worked
   example (endpoint span) — AI Act Art. 46(4)'s own "no objection has
   been raised by either a Member State or the Commission..." (quoted
   in full above, under "Span granularity", the no-modal rule, Example
   2): the `requires` Statement's own X span INCLUDES "no" as part of
   what the antecedent SAYS; the RELATION itself (this antecedent, as
   stated, produces the consequence) is not negated by anything, so
   `negation: "absent"`.
3. **A fixed idiom.** "not later than", "no later than", "not less
   than", "no less than", "not exceeding", "whether or not", "not
   only ... but also" — these never count as negators. Worked example —
   GDPR Art. 4(2)'s own "whether or not by automated means": "or not"
   is part of the fixed idiom "whether or not", never a negator —
   `negation: "absent"`.
4. **The negator is in ANOTHER finite clause of the same sentence** (a
   clause per R-p.1, above — never a prepositional phrase, a reduced
   relative, or a participial phrase). This replaces the old rule that
   put this case in `uncertain`: every Statement is clause-scoped, so a
   negator sitting in a DIFFERENT finite clause of the same
   multi-clause sentence does not reach THIS Statement's own relation
   at all, and is simply irrelevant to it — `negation: "absent"`, never
   `uncertain`. Worked example, GDPR Art. 12(2)'s own sentence (not
   quoted here in full; see the two short fragments below for its own
   negator-bearing clauses). The main finite clause opens "the
   controller shall not refuse to act on the request" — this clause HAS
   the negator "not", scoping its own refuse-relation. The
   `except_when` Statement built from the subordinate finite clause
   that opens "unless the controller demonstrates that it is not in" is
   the Statement "whose own clause lacks the negator": at its OWN top
   level ("the controller demonstrates that [complement]"), this clause
   carries no negator; "not" sits inside the NESTED, FURTHER-
   SUBORDINATE finite complement clause "it is not in a position to
   identify the data subject" (its own subject "it", its own finite
   verb "is") — a DIFFERENT finite clause under R-p.1, not the
   except_when Statement's own top clause. The except_when Statement's
   own relation (the general rule does not apply when the controller so
   demonstrates) is therefore `negation: "absent"`.

**`uncertain`.** Used ONLY when the negator is in the Statement's OWN
clause and its scope over the relation GENUINELY cannot be decided from
the text (see R-p.2, above, for the worked example). There is NO "when
in doubt" default — `uncertain` is a POSITIVE finding that the text
itself is ambiguous, never a fallback for a coder's own indecision. A
negator outside the Statement's own clause is `absent`, never
`uncertain` (case 4, above); a negator inside the Statement's own
clause that clearly scopes only an adjunct is ALSO `absent`, never
`uncertain` (R-p.2).

**Exceptions carved from a negated rule.** Where a general rule is
stated negated and an `except_when` clause carves an exception from it
("X shall not apply except where Y..."), the MAIN RULE Statement (the
negated general rule, e.g. the `applies_to` Statement above) is
`negation: "present"`; the SEPARATE `except_when` Statement, built from
the "except where Y" clause, is `negation: "absent"` — the exception
clause's own relation (the carve-out condition Y) carries no negator of
its own. Worked example — the SAME GDPR Art. 11(2) sentence used for
the `present` case above: the main-rule `applies_to` Statement is
X = "Articles 15 to 20", Y = "such cases" (the demonstrative "such" KEPT
per R-q — a cross-sentence reference back to the controller's own
inability to identify the data subject, described in the PRECEDING
sentence of the same paragraph), `negation: "present"`; the
`except_when` Statement built from "except where the data subject...
provides additional information enabling his or her identification" is
`negation: "absent"`.

A Statement with `negation: "uncertain"` is still coded and submitted —
it is not dropped.
