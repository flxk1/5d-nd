# Codebook: typed statements, v3.6 (`typed-statements-v3.6`)

v3.6 ADDS ONE new predicate, `addressed_to` (relational —
see that predicate's own section, below), and a deterministic deadline
SPLIT for `deadline_of` (see that predicate's own section). Every other
v3.5 predicate, and the v3.5 dimension mapping, is UNCHANGED. v3.1
through v3.4 state ten further decision rules (R-f through R-o,
see "Rules motivated by the blind pilot", below): the
`performs`/`competence_of` test (including its "responsible for"
conferral rule), the "subject to [provision]" routing, the unitisation
span rules, the coordinated-NP rule (R-i), no modal inside an endpoint
span, power as a never-endpoint, the right-as-endpoint rule extended to
"exercise the right to X", negation scope for a conditional antecedent,
and the "part of" determiner fix (including "form(s) part of" as its
own verb cue, and "references to X include Y" as `applies_to`). v3.5
states four further rules (R-p through R-s, see "Rules motivated by the
v3.5 recheck", below): the negation procedure is rewritten around
clause-scoping (R-p), the determiner strip/keep lists are stated
explicitly (R-q), the pronoun-referent rule (R-r), and the
disjunctive-type-list-under-one-determiner rule (R-s). No predicate is
added, removed, or reassigned — see
`docs/decisions/0008-typed-statement-v3-rulings.md` for these
rulings and their history.

This codebook is a deliverable in its own right — the codebook and gold
come FIRST, the deterministic extractor SECOND. Nothing here is code;
the closed enum this codebook describes is pinned in
`vocabulary/statement-predicates.json` and `src/five_d_nd/statement.py`
(`PREDICATE_DIMENSION`). A DIMENSION-BLIND, SELF-CONTAINED view of this
same codebook — the predicate names and fact patterns only, with no
dimension rationale, plus its own copy of the layer and negation rules —
is `docs/codebook/typed-statements-v1-coder-view.md`; a coder works from
THAT document, never from this one.

**Modal force is never a Statement predicate.** An obligation, a
permission, or a prohibition (O/P/F) is nD deontic knowledge — a separate
grammar's own co-dimension (spec/SPEC.md §7, §9) — never one of the
predicates below. Every predicate below names a FACT or an ACT; none of
them is, or stands in for, the deontic force that may separately attach
to that fact or act. `requires`'s own object, in particular, is the ACT a
trigger causes — never framed as "an obligation."

Every quote below is copied VERBATIM from this project's own
the local corpus (`gdpr/source-32016R0679.txt`,
`ai-act/source-32024R1689.txt`, `dsa/source-32022R2065.txt`,
`nis2/source-32022L2555.txt`), with the exact byte offset into that file
(`<file>#<start>-<end>`, matching spec/SPEC.md §4's own canonical
reference convention). No statute text is invented, paraphrased, or
shortened with an ellipsis — every quote is the complete span at the
stated offset.

## The predicate table (v3 — 15 predicates)

| predicate | dimension | one-line gloss |
|---|---|---|
| `is_a` | structural | a legal/legislative definition |
| `part_of` | structural | containment, part-to-whole |
| `applies_to` | structural | scope: the instrument's applicability, including a concession |
| `cross_references` | structural | a citation to another provision |
| `except_when` | structural | a TRUE exception/derogation from a rule |
| `enables` | causal | makes something possible or produces it, no stated purpose |
| `requires` | causal | trigger/condition → a consequence ACT |
| `legislative_purpose_of` | intentional | recital-position purpose, no modal |
| `compliance_purpose_of` | intentional | operative-article purpose, with a modal |
| `based_on` | intentional | the stated legal basis (justification) |
| `precedes` | temporal | an explicit ordering relation |
| `deadline_of` | temporal | a bounded-duration relation |
| `predication` | relational | the DEFAULT — an ordinary copula/modal assertion |
| `competence_of` | relational | an institutional actor's own mandate |
| `performs` | relational | any other actor performing a non-deontic act |

`part_of` MERGES what an earlier enum version split into two predicates
(`part_of` and `includes`): the SAME containment relation, named from
either end, is ALWAYS coded part-to-whole — a clause surfacing it
whole-first ("X includes Y") is coded `part_of` with `subj` and `obj`
SWAPPED, never as a second predicate. Splitting the relation by surface
direction depressed predicate-level agreement for no dimension-level
gain (both ends are structural); merging it removes that depression
without losing anything the dimension distinction needs.

---

## `is_a` — structural

**Definition.** A legal/legislative definition: the subject span IS the
thing the object span defines (`'X' means ...`). Structural because a
definition fixes what a term is an instance of / made of, never a causal
or temporal claim.

**Positive examples**

1. `gdpr/source-32016R0679.txt#157742-157840`
   > ‘personal data’ means any information relating to an identified or identifiable natural person
2. `ai-act/source-32024R1689.txt#236420-236576`
   > ‘AI system’ means a machine-based system that is designed to operate with varying levels of autonomy and that may exhibit adaptiveness after deployment
   >
   (the source text's own space between "a" and "machine-based" is U+00A0,
   a non-breaking space, not U+0020 — reproduced verbatim at the given
   offset; it renders as an ordinary space in this document)

**Negative examples** (text that superficially resembles a definition but
is NOT coded `is_a`)

1. `gdpr/source-32016R0679.txt#166596-166680`
   > Personal data shall be:
   >
   > (a)
   >
   > processed lawfully, fairly and in a transparent manner
   >
   A modal obligation (`shall be ... processed`), not a definition — this
   is `predication` (relational, the default), never `is_a`.
2. `gdpr/source-32016R0679.txt#158345-158378`
   > whether or not by automated means
   >
   `means` here is the ordinary noun ("by X means"), not the definitional
   copula verb — a lexical trap for a naive `means`-keyword cue.

**A worked correction.** `personal data` IS information relating to a
person, never the person themselves — a definition's own `obj` MUST be
the thing actually defined, not a loosely paraphrased shorter noun
phrase: the full `obj` for the Art. 4(1) definition above is
`information_relating_to_identified_or_identifiable_natural_person`, not
`identified_or_identifiable_natural_person` (which would assert the
false definition "personal data IS a person").

---

## `part_of` — structural

**Definition.** The subject is a structural component, or named sub-unit,
of the object (a filing system, a group of undertakings, a listed
measure within a broader set of measures). Direction is ALWAYS
part-to-whole: the smaller unit is `subj`, the larger unit is `obj`. A
clause surfacing the SAME relation whole-first ("X includes Y") is coded
with `subj` and `obj` SWAPPED (`Y part_of X`), never as a second
predicate. `form(s) part of` is a `part_of` VERB CUE in its own right
("X form(s) part of Y" — X is `subj`, Y is `obj`), the same way
`unless`/`except` are `except_when` cues.

**"part of" is not a determiner (R-o).** `part of` is NOT on the
subj/obj span's own leading-determiner strip list (see "Unitisation
rules", below) — "part of X" names a distinct entity (a component or
portion of X), kept WHOLE in its own span, never trimmed to bare "X" as
if "part of" meant nothing. This holds whether the "part of X" span is
itself coded as a `part_of` Statement (see positive example 1) OR as an
endpoint of a DIFFERENT predicate entirely (see positive example 2) —
"part of" is never stripped either way.

**"References to X include Y" is NOT this predicate.** That surface
form is an INTERPRETIVE/DEFINITIONAL extension clause: it stipulates
that the TERM X, wherever referenced elsewhere in the instrument, is to
be READ as covering Y too — Y FALLS WITHIN THE SCOPE of the term X,
coded as `applies_to` (never `is_a`, never `part_of`), even where Y is
ALSO, physically, a part of X's own referent. See negative example 3.

**Positive examples**

1. `gdpr/source-32016R0679.txt#155546-155580` (GDPR Art. 2(1); the
   relative pronoun "which" has its own antecedent earlier in the SAME
   sentence)
   > which form part of a filing system
   >
   Antecedent (the `subj`), `gdpr/source-32016R0679.txt#155532-155545`:
   > personal data
   >
   Coded `personal_data part_of filing_system` — `subj` is the
   antecedent "personal data" (NOT the relative pronoun "which" itself,
   which has no span of its own), `obj` is "filing system"
   (`#155567-155580`, R-q's own leading-determiner "a" stripped — this
   is an ordinary `subj`/`obj` span, never a "part of Z" span in its own
   right, so R-o's "'part of' is not a determiner" rule does not apply
   to it); "form part of" is the VERB CUE. The clause's own second
   disjunct, "or are intended to form part of a filing system"
   (`#155581-155628`), names the SAME `obj` under the SAME antecedent.
2. `uk-dpa2018/source-ukpga-2018-12.txt#288885-289064` (UK DPA 2018 s.
   148(2)(a) — a DIFFERENT instrument and predicate, illustrating R-o's
   own core point on an endpoint that is NOT itself a `part_of`
   Statement)
   > It is an offence for the person— a to destroy or otherwise dispose of, conceal, block or (where relevant) falsify all or part of the information, document, equipment or material
   >
   Coded `the_person performs destroy_or_dispose_of_all_or_part_of_the_
   information_document_equipment_or_material` — the `obj` span is "all
   or part of the information, document, equipment or material"
   (`#289001-289064`), kept WHOLE (never stripped to bare "the
   information, document, equipment or material"), as the object of a
   `performs` Statement, NOT a `part_of` Statement relating it back to
   "the information" itself — never the vacuous
   `part_of_the_information part_of the_information` pattern R-o exists
   to rule out.
3. `gdpr/source-32016R0679.txt#38632-38717`
   > that are part of a group of undertakings or institutions affiliated to a central body
4. `gdpr/source-32016R0679.txt#63124-63292` (whole-first surface form, direction SWAPPED when coded)
   > Such processing includes ‘profiling’ that consists of any form of automated processing of personal data evaluating the personal aspects relating to a natural person
   >
   Coded `profiling part_of automated_processing` — the whole ("such
   processing") names the part ("profiling") in the surface text; the
   Statement's own `subj`/`obj` are swapped to keep the relation
   part-to-whole.

**Negative examples**

1. `gdpr/source-32016R0679.txt#86870-86958`
   > As part of that consultation process, the outcome of a data protection impact assessment
   >
   Idiomatic "as part of" names a PROCEDURAL STEP, not a structural
   containment relation between two named entities — coded as
   `predication` unless a clearer sequencing cue is also present.
2. `gdpr/source-32016R0679.txt#173261-173365`
   > Any part of such a declaration which constitutes an infringement of this Regulation shall not be binding
   >
   "Part" here names an arbitrary PORTION OF TEXT (a declaration), not a
   structural unit of the regulatory scheme — out of scope for `part_of`.
3. `uk-dpa2018/source-ukpga-2018-12.txt#366970-367082` (UK DPA 2018 s.
   184(6) — a DIFFERENT "part of" clause from the one that motivated
   R-o, same instrument; a chapeau+list, R-h)
   > references to a relevant record include— a part of such a record, and a copy of, or of part of, such a record.
   >
   "References to a relevant record include..." EXTENDS the TERM
   "relevant record"'s own meaning to also cover "a part of such a
   record" and "a copy... of such a record" — "a part of such a
   record" FALLS WITHIN THE SCOPE of the term "relevant record", coded
   `applies_to`, never `is_a`, never `part_of`, even though "a part of
   such a record" is, read in isolation, a genuine physical component
   of "such a record". The span "a part of such a record" itself stays
   WHOLE either way ("part of" is never stripped as a determiner) —
   only the PREDICATE differs from positive example 1, above.

---

## `applies_to` — structural

**Definition.** A scope provision: the subject instrument's own
applicability is fixed onto the object (a kind of processing, an actor
category, a territory), INCLUDING a CONCESSIVE clause that keeps the
rule in force DESPITE a named FACT OR CIRCUMSTANCE (`notwithstanding the
fact that...`, `irrespective of whether...`). **The `notwithstanding`/
`irrespective of`/`subject to` routing test is whether the OBJECT's own
HEAD NOUN is itself a PROVISION REFERENCE or a FACT/CIRCUMSTANCE/
CONDITION.** "Notwithstanding [paragraph N / Article N / point N /
subparagraph N / a named act]" (`notwithstanding paragraph 2`,
`notwithstanding Article 5`) names a DEROGATION and is `except_when`,
below — the object's own head noun IS another part of the instrument's
own structure being set aside. A thing merely QUALIFIED by "referred to
in..." or "pursuant to..." does NOT count as a provision reference for
this test — "the terms of the arrangement referred to in paragraph 1"
has the head noun "terms", not "paragraph"; "referred to in paragraph
1" only identifies WHICH arrangement, and paragraph 1 itself is not
being set aside. Such a clause is CONCESSIVE and stays `applies_to` —
the object is a state of the world (the terms of an arrangement),
merely cross-referenced to a provision, not itself one. The SAME test
applies to `irrespective of` AND to `subject to`: "subject to [a
provision reference]" — illustrated by UK DPA 2018 s. 6(1)'s own
chapeau, quoted in full under "Unitisation", below — is a DEROGATION,
`except_when`; "subject to [a condition or requirement]" (AI Act Art.
10(5)'s own "subject to appropriate safeguards" wording, quoted verbatim
in `requires`'s own positive example, below) has a non-provision head
noun and is `requires` instead — the condition is something the act
must satisfy, not a provision setting the rule aside, so it does not
belong to either `applies_to` or `except_when` at all. See
`except_when`'s own positive example 4 and `requires`'s own positive
example 3 for the worked contrast.

**"References to X include Y" (R-o).** This surface form is coded
`applies_to`: Y FALLS WITHIN THE SCOPE of the TERM X, wherever X is
referenced elsewhere in the instrument — never `is_a` (this is not a
fresh definition of a new term), and never `part_of` (even where Y is
physically a part of X's own referent) — see `part_of`'s own negative
example 3, above, for the worked case.

**Positive examples**

1. `gdpr/source-32016R0679.txt#155382-155476`
   > This Regulation applies to the processing of personal data wholly or partly by automated means
2. `gdpr/source-32016R0679.txt#156802-156957`
   > This Regulation applies to the processing of personal data in the context of the activities of an establishment of a controller or a processor in the Union
3. `gdpr/source-32016R0679.txt#57547-57607` (concessive — the object's head noun is "the fact", not a provision reference)
   > notwithstanding the fact that he or she is no longer a child
4. `gdpr/source-32016R0679.txt#210119-210311` (concessive — the object's own head noun is "the terms", merely QUALIFIED by "referred to in paragraph 1", which only identifies which arrangement; paragraph 1 itself is not set aside)
   > Irrespective of the terms of the arrangement referred to in paragraph 1, the data subject may exercise his or her rights under this Regulation in respect of and against each of the controllers

**Negative examples** (NEGATED scope — the instrument does NOT apply;
coded with `negation: "present"` if coded as `applies_to` at all, or left
out of the Statement layer entirely at this codebook's own discretion —
see "Negation", below)

1. `gdpr/source-32016R0679.txt#10718-10807`
   > This Regulation does not apply to issues of protection of fundamental rights and freedoms
2. `gdpr/source-32016R0679.txt#11814-11956`
   > This Regulation does not apply to the processing of personal data by a natural person in the course of a purely personal or household activity
3. `ai-act/source-32024R1689.txt#455365-455717` (the object's own head noun IS "paragraph" — a provision reference — so this is `except_when`, a derogation, never `applies_to`, despite starting with "Notwithstanding")
   > Notwithstanding paragraph 2 of this Article, in the event of a widespread infringement or a serious incident as defined in Article 3, point (49)(b), the report referred to in paragraph 1 of this Article shall be provided immediately, and not later than two days after the provider or, where applicable, the deployer becomes aware of that incident.
   >
   (the source text's own spaces between "paragraph"/"2", "a"/"widespread",
   "a"/"serious", and "Article"/"3" are U+00A0, non-breaking spaces,
   reproduced verbatim at the given offset; AI Act Art. 73(3))

---

## Savings clauses — `cross_references`, never `except_when` or negated `applies_to`

**Definition.** A savings clause ("without prejudice to X", "shall not
affect X", "is without prejudice to X") records a NON-OVERRIDING LINK
between the host provision and X: the host provision's own force is
EXPLICITLY left undisturbed with respect to X — this is neither a
derogation (`except_when`, which REMOVES an exclusion) nor a negated
scope claim (`applies_to` with `negation: "present"`, which says the
host provision itself does NOT cover something). It is coded
`cross_references`, from the host provision to X.

**Positive examples**

1. `gdpr/source-32016R0679.txt#258409-258681` (GDPR Art. 45(7))
   > A decision pursuant to paragraph 5 of this Article is without prejudice to transfers of personal data to the third country, a territory or one or more specified sectors within that third country, or the international organisation in question pursuant to Articles 46 to 49.
2. `ai-act/source-32024R1689.txt#234832-235023` (AI Act Art. 2(7))
   > This Regulation shall not affect Regulation (EU) 2016/679 or (EU) 2018/1725, or Directive 2002/58/EC or (EU) 2016/680, without prejudice to Article 10(5) and Article 59 of this Regulation.
   >
   (the source text's own spaces between "(EU)"/"2016/679" and between
   "Article"/"10(5)" and "Article"/"59" are U+00A0, non-breaking spaces,
   reproduced verbatim at the given offset). Coded `negation: "absent"`
   (`conformance/vectors/statement/valid-savings-clause-negation-absent.json`):
   the "not" in "shall not affect" is part of the savings cue itself,
   never a negator — see "Negation", below.

---

## `cross_references` — structural

**Definition.** A citation from one provision to another (`referred to in
Article N`). Carried over unchanged from §8a's own `cross_reference_links`
— a fact about the citing sentence's own surface form, never itself
normative. Kept in THIS enum so a cross-reference is addressable as an
ordinary Statement.

**Positive examples**

1. `gdpr/source-32016R0679.txt#181126-181271`
   > any information referred to in Articles 13 and 14 and any communication under Articles 15 to 22 and 34 relating to processing to the data subject
2. `gdpr/source-32016R0679.txt#181803-181919`
   > In the cases referred to in Article 11(2), the controller shall not refuse to act on the request of the data subject

**Negative examples**

1. `gdpr/source-32016R0679.txt#155546-155628`
   > which form part of a filing system or are intended to form part of a filing system
   >
   Structural containment, no citation to another provision — `part_of`,
   never `cross_references`.
2. `gdpr/source-32016R0679.txt#82648-82746`
   > prior to the processing in order to assess the particular likelihood and severity of the high risk
   >
   Temporal ordering, no citation — `precedes`, never `cross_references`.

---

## `except_when` — structural

**Definition.** A TRUE exception or derogation: the subject's own
general rule does NOT apply under the condition named by the object. Cues
are a CLOSED set that actually express non-application — `unless`,
`except`, `by way of derogation from` (or the shorter `by derogation
from`), `save where` — PLUS `notwithstanding`/`irrespective of`/`subject
to` WHEN their own object's HEAD NOUN is itself a PROVISION REFERENCE (a
paragraph, an Article, a section, a subsection, a point, a subparagraph,
or a named act — see `applies_to`'s own routing test, above, including
the "merely qualified by 'referred to in...'" exclusion): "notwithstanding
paragraph 2" and "subject to subsection (2)" both name a provision being
set aside, a derogation, even though "subject to" is the same surface
word that routes to `requires` (below) when its own object's head noun
is a condition or requirement instead of a provision — or merely
QUALIFIED by a provision reference without being one itself ("the
terms... referred to in paragraph 1" has head noun "terms", not
"paragraph"). "X does not apply to Y" is `except_when` only when Y is a
scope CARVE-OUT stated as part of defining the rule's own boundary;
otherwise it is `applies_to` with `negation: "present"`. A SAVINGS
CLAUSE ("without prejudice to X", "shall not affect X") is NEITHER
`except_when` NOR negated `applies_to` — see "Savings clauses", above.

**Positive examples**

1. `gdpr/source-32016R0679.txt#308790-308970`
   > it may, by way of derogation from the consistency mechanism referred to in Articles 63, 64 and 65 or the procedure referred to in Article 60, immediately adopt provisional measures
2. `gdpr/source-32016R0679.txt#180662-180864`
   > Articles 15 to 20 shall not apply except where the data subject, for the purpose of exercising his or her rights under those articles, provides additional information enabling his or her identification.
3. `ai-act/source-32024R1689.txt#455365-455717` (AI Act Art. 73(3) — the object's own head noun IS "paragraph 2", a provision reference, so this is a genuine derogation)
   > Notwithstanding paragraph 2 of this Article, in the event of a widespread infringement or a serious incident as defined in Article 3, point (49)(b), the report referred to in paragraph 1 of this Article shall be provided immediately, and not later than two days after the provider or, where applicable, the deployer becomes aware of that incident.
   >
   (the source text's own spaces between "paragraph"/"2", "a"/"widespread",
   "a"/"serious", and "Article"/"3" are U+00A0, non-breaking spaces,
   reproduced verbatim at the given offset)
4. `uk-dpa2018/source-ukpga-2018-12.txt#62382-62527` (UK DPA 2018 s. 6(1) — "subject to" with THREE provision-reference head nouns: "subsection (2)", "section 209", "section 210". The chapeau+list unitisation rule applies: THREE Statements, one per listed provision, sharing the SAME subj — see "Unitisation", below)
   > The definition of “controller” in Article 4(1)(7) of the UK GDPR has effect subject to— a subsection (2), b section 209, and c section 210.
   >
   (the source text's own quotation marks around "controller" are U+201C/
   U+201D, curly double quotes, reproduced verbatim; the em dash after
   "subject to" is U+2014)

**Negative examples**

1. `gdpr/source-32016R0679.txt#57547-57607` (the object's own head noun is "the fact", not a provision reference, so this is concessive)
   > notwithstanding the fact that he or she is no longer a child
   >
   `applies_to`, never `except_when` — see the routing test above.
2. `gdpr/source-32016R0679.txt#210119-210311` (the object's own head noun is "the terms", merely QUALIFIED by "referred to in paragraph 1" — the arrangement is identified, not set aside)
   > Irrespective of the terms of the arrangement referred to in paragraph 1, the data subject may exercise his or her rights under this Regulation in respect of and against each of the controllers
   >
   `applies_to`, never `except_when` — a thing merely qualified by
   "referred to in..." is not itself a provision reference.
3. `ai-act/source-32024R1689.txt#282556-282742` (AI Act Art. 10(5) — "subject to" with a non-provision head noun — "appropriate safeguards")
   > the providers of such systems may exceptionally process special categories of personal data, subject to appropriate safeguards for the fundamental rights and freedoms of natural persons.
   >
   `requires`, never `except_when` — "appropriate safeguards" is a
   condition the processing must satisfy, not a provision being set
   aside; see `requires`'s own positive example for the full reasoning.
3. `gdpr/source-32016R0679.txt#226533-226738`
   > is likely to result in a high risk to the rights and freedoms of natural persons, the controller shall, prior to the processing, carry out an assessment of the impact of the envisaged processing operations
   >
   A trigger that ADDS a consequence, not a carve-out that REMOVES an
   exclusion — `requires`, never `except_when`.

---

## `enables` — causal

**Definition.** The subject makes the object POSSIBLE or PRODUCES it as
a mechanism — a precondition/capability/production relation, with NO
stated purpose and no deontic modal of its own.

**Positive examples**

1. `gdpr/source-32016R0679.txt#59846-59882`
   > formats that enable data portability
2. `gdpr/source-32016R0679.txt#240847-240946`
   > mechanisms which enable the body referred to in Article 41(1) to carry out the mandatory monitoring
3. `gdpr/source-32016R0679.txt#203053-203121` (production, not a legal basis — see `based_on`'s own definition)
   > a decision based solely on automated processing, including profiling
   >
   Coded `automated_processing enables automated_decision` — this
   describes HOW the decision is PRODUCED (its mechanism), not its legal
   ground; `based_on` would be the WRONG predicate here even though the
   words "based on" appear in the text.

**Negative examples** (the causal/intentional hard boundary — see
"Decision rules" below)

1. `ai-act/source-32024R1689.txt#10237-10380`
   > this Regulation aims to strengthen the effectiveness of such existing rights and remedies by establishing specific requirements and obligations
   >
   "Aims to" is a stated PURPOSE, not a bare capability — `legislative_purpose_of`
   (intentional), never `enables` (causal).
2. `gdpr/source-32016R0679.txt#246054-246173`
   > for the purpose of demonstrating compliance with this Regulation of processing operations by controllers and processors
   >
   An explicit `for the purpose of` phrase — `compliance_purpose_of`
   (intentional), never `enables`.

---

## `requires` — causal

**Definition.** A trigger/condition relation: when the subject's own
antecedent fires (a breach, a high-risk processing type, or "subject to
[a condition or requirement]" whose own head noun is NOT a provision
reference — see `except_when`'s own routing test), the object ACT
follows as its consequence. The object is the ACT ITSELF (`notify the
supervisory authority`, `implement a safeguard`) — NEVER framed as "an
obligation" or any other deontic wrapper; whether the act is ALSO owed as
a deontic duty is separate, nD knowledge this predicate does not encode.
No MODAL verb (`shall`, `may`, `must`, `should`, `is to be`, `shall be
deemed`/`shall be held`) is ever inside the object span either (R-k) —
see "Unitisation rules", below, for the worked example. A negator
INSIDE the ANTECEDENT (`cannot`, `unable`, `no`) stays INSIDE the
`subj` span, as part of what the antecedent SAYS (R-n): under §21,
`negation: "present"` means the RELATION ITSELF is negated, which a
negator confined to the antecedent's own content never does; such a
Statement is `negation: "absent"`. See `deadline_of`'s own section,
below, for the worked example and the companion rule about a deadline
N named in the consequence.

**Positive examples**

1. `gdpr/source-32016R0679.txt#222809-223027`
   > In the case of a personal data breach, the controller shall without undue delay and, where feasible, not later than 72 hours after having become aware of it, notify the personal data breach to the supervisory authority
2. `gdpr/source-32016R0679.txt#226533-226738`
   > is likely to result in a high risk to the rights and freedoms of natural persons, the controller shall, prior to the processing, carry out an assessment of the impact of the envisaged processing operations
3. `ai-act/source-32024R1689.txt#282556-282742` (AI Act Art. 10(5) — "subject to" with a non-provision head noun — "appropriate safeguards" is a condition, not a provision reference)
   > the providers of such systems may exceptionally process special categories of personal data, subject to appropriate safeguards for the fundamental rights and freedoms of natural persons.

**Negative examples**

1. `gdpr/source-32016R0679.txt#950-1054`
   > The protection of natural persons in relation to the processing of personal data is a fundamental right.
   >
   Descriptive, no antecedent/consequence structure at all — `predication`
   (or `legislative_purpose_of` where a purpose phrase is present
   elsewhere in the same recital), never `requires`.
2. `gdpr/source-32016R0679.txt#157742-157840`
   > ‘personal data’ means any information relating to an identified or identifiable natural person
   >
   A definition, not a trigger — `is_a`, never `requires`.

---

## `legislative_purpose_of` — intentional

**Definition.** A recital-position purpose statement: the subject
(instrument or provision) IS INTENDED TO / AIMS TO bring about the object,
stated descriptively, with NO deontic modal of its own.

**Positive examples**

1. `gdpr/source-32016R0679.txt#1604-1736`
   > This Regulation is intended to contribute to the accomplishment of an area of freedom, security and justice and of an economic union
2. `ai-act/source-32024R1689.txt#10237-10380`
   > this Regulation aims to strengthen the effectiveness of such existing rights and remedies by establishing specific requirements and obligations

**Negative examples** (the recital-vs-article hard boundary — see
"Decision rules" below)

1. `gdpr/source-32016R0679.txt#226615-226773`
   > the controller shall, prior to the processing, carry out an assessment of the impact of the envisaged processing operations on the protection of personal data
   >
   Operative article, modal (`shall`) — `requires` (causal, and also
   `precedes`, temporal), never `legislative_purpose_of`.
2. `gdpr/source-32016R0679.txt#166596-166680`
   > Personal data shall be:
   >
   > (a)
   >
   > processed lawfully, fairly and in a transparent manner
   >
   A binding principle with no purpose language at all — `predication`,
   never `legislative_purpose_of`.

---

## `compliance_purpose_of` — intentional

**Definition.** An operative-article purpose clause carrying a modal
(`shall ... for the purpose of ...`): the subject act is undertaken FOR
the stated object, inside a binding obligation.

**Positive examples**

1. `gdpr/source-32016R0679.txt#246054-246173`
   > for the purpose of demonstrating compliance with this Regulation of processing operations by controllers and processors
2. `gdpr/source-32016R0679.txt#246479-246808`
   > for the purpose of demonstrating the existence of appropriate safeguards provided by controllers or processors that are not subject to this Regulation pursuant to Article 3 within the framework of personal data transfers to third countries or international organisations under the terms referred to in point (f) of Article 46(2).

**Negative examples**

1. `gdpr/source-32016R0679.txt#1604-1736`
   > This Regulation is intended to contribute to the accomplishment of an area of freedom, security and justice and of an economic union
   >
   Recital position, no modal — `legislative_purpose_of`, never
   `compliance_purpose_of`.
2. `gdpr/source-32016R0679.txt#222809-223027`
   > In the case of a personal data breach, the controller shall without undue delay and, where feasible, not later than 72 hours after having become aware of it, notify the personal data breach to the supervisory authority
   >
   A modal trigger/consequence with NO `for the purpose of` phrase —
   `requires` (causal), never `compliance_purpose_of`.

---

## `based_on` — intentional

**Definition.** LEGAL BASIS ONLY: the object names the legal ground that
JUSTIFIES the subject act or provision. Intentional, never causal or
structural, and the boundary against each is worth stating explicitly:

- **Against causal.** The originals' own causal gloss is "triggers,
  enables, prevents" — mechanism verbs describing what MAKES something
  happen. A legal basis does not mechanically cause an act; it
  JUSTIFIES it after the fact of the act's own trigger or mechanism
  (which may be coded separately, as `requires` or `enables`). The
  originals' own intentional gloss — "goals, justification, telos" —
  names "justification" explicitly, and a legal basis IS a
  justification. A clause describing HOW an act or decision is PRODUCED
  (its mechanism) is `enables`, never `based_on`, even when the surface
  words "based on" appear in it (see `enables`'s own positive example 3).
- **Against structural.** A legal basis is not a containment or scope
  relation. The instrument's own provision MAY itself be cited as the
  ground, and that citation is `cross_references`; but `based_on` names
  the JUSTIFICATION role the citation plays (why the act is lawful),
  never the citation act itself. The two predicates commonly co-occur on
  the same clause (`requires`'s own positive example 2 pairs with a
  `cross_references` Statement when it names the provision it rests on)
  without collapsing into one.
- **Against `requires`.** A "Where X is based on Y, [modal] Z"
  trigger/consequence clause is `requires`, never `based_on`, even
  though the words "based on" appear inside it — the clause's own
  PRINCIPAL relation is the trigger→consequence, and the "based on"
  phrase there names the TRIGGER's own condition, not a separate
  justification claim about an already-named act.

**Positive examples**

1. `gdpr/source-32016R0679.txt#203600-203647`
   > is based on the data subject's explicit consent
2. `gdpr/source-32016R0679.txt#177155-177487`
   > processing is necessary for reasons of substantial public interest, on the basis of Union or Member State law which shall be proportionate to the aim pursued, respect the essence of the right to data protection and provide for suitable and specific measures to safeguard the fundamental rights and the interests of the data subject;
   >
   A TRUE legal-basis clause (GDPR Art. 9(2)(g)): the processing's own
   lawfulness rests on the named Union or Member State law as its ground
   — coded `processing based_on union_or_member_state_law`.

**Negative examples** (the trap this predicate's own definition names
explicitly)

1. `gdpr/source-32016R0679.txt#172791-172950`
   > Where processing is based on consent, the controller shall be able to demonstrate that the data subject has consented to processing of his or her personal data
   >
   `Where X, [modal] Y` is a TRIGGER/CONSEQUENCE clause — `requires`
   (causal), even though the words "based on consent" appear inside it.
2. `gdpr/source-32016R0679.txt#203053-203121`
   > a decision based solely on automated processing, including profiling
   >
   Describes the decision's own PRODUCTION mechanism — `enables`, never
   `based_on` (see `enables`'s own positive example 3, above, for the
   full reasoning).

---

## `precedes` — temporal

**Definition.** An explicit ordering relation: the subject event/act
happens BEFORE the object event/act (`prior to`, `before`).

**Positive examples**

1. `gdpr/source-32016R0679.txt#226615-226773`
   > the controller shall, prior to the processing, carry out an assessment of the impact of the envisaged processing operations on the protection of personal data
2. `gdpr/source-32016R0679.txt#82648-82746`
   > prior to the processing in order to assess the particular likelihood and severity of the high risk

**Negative examples** (the temporal-vs-causal hard boundary — see
"Decision rules" below)

1. `gdpr/source-32016R0679.txt#222809-223027`
   > In the case of a personal data breach, the controller shall without undue delay and, where feasible, not later than 72 hours after having become aware of it, notify the personal data breach to the supervisory authority
   >
   A trigger/condition ("in the case of"), with no explicit BEFORE/AFTER
   ordering word of its own — `requires` (causal) and `deadline_of` (the
   72-hour window), never `precedes`.
2. `gdpr/source-32016R0679.txt#155546-155628`
   > which form part of a filing system or are intended to form part of a filing system
   >
   Structural containment, no sequencing at all — `part_of`, never
   `precedes`.

---

## `deadline_of` — temporal

**Definition.** A bounded-duration relation: the object names a fixed
time window or deadline within which the subject act must occur.
Distinguished from `requires` (the TRIGGER itself) and from `precedes`
(bare ordering, no duration).

**Negation scope for a CONDITIONAL antecedent (R-n).** "Where/if...
cannot be achieved/adopted/completed... within N" states the
ANTECEDENT of a `requires`
Statement; the negator (`cannot`, `unable`, `no`) stays INSIDE that
Statement's own `subj` span, as part of what the antecedent SAYS. Under
§21, `negation: "present"` means the RELATION ITSELF — the
subj-predicate-obj triple — is negated; a negator confined to the
antecedent's own content never does that, so the `requires` Statement
is `negation: "absent"`. The companion `deadline_of` Statement, naming
the period N itself, is ALSO `negation: "absent"` — for the identical
reason: nothing negates the RELATION naming N either.

**Positive examples**

1. `gdpr/source-32016R0679.txt#78921-79061`
   > not later than 72 hours after having become aware of it, unless the controller is able to demonstrate, in accordance with the accountability
2. `gdpr/source-32016R0679.txt#222910-223027`
   > not later than 72 hours after having become aware of it, notify the personal data breach to the supervisory authority
3. (R-n, worked) `gdpr/source-32016R0679.txt#306629-306887` (GDPR Art.
   65(3) — a DIFFERENT deadline-negation clause from the one that
   motivated R-n, same instrument)
   > the Board has been unable to adopt a decision within the periods referred to in paragraph 2, it shall adopt its decision within two weeks following the expiration of the second month referred to in paragraph 2 by a simple majority of the members of the Board
   >
   TWO Statements, BOTH `negation: "absent"`: the CONDITION —
   `the_board_has_been_unable_to_adopt_a_decision_within_the_periods_
   referred_to_in_paragraph_2 requires
   adopt_its_decision_within_two_weeks_following_the_expiration_of_the_
   second_month_referred_to_in_paragraph_2_by_a_simple_majority_of_the_
   members_of_the_board` (`subj` span `#306629-306720`, "unable"
   INCLUDED, never stripped out; `obj` span `#306731-306887`, modal "it
   shall" EXCLUDED per R-k) — the RELATION itself (this antecedent, AS
   STATED, produces this consequence) is not negated by anything.
   Separately, the NEW deadline itself —
   `adopt_its_decision deadline_of
   two_weeks_following_the_expiration_of_the_second_month_referred_to_
   in_paragraph_2` (`obj` span `#306757-306838`) — is ALSO `negation:
   "absent"`, the identical reasoning applied to its own RELATION.
   R-k's own positive example 2 (AI Act Art. 46(4)) follows the IDENTICAL
   pattern — see "Unitisation rules", below — so a coder meets ONE
   pattern for a negator confined to an antecedent, never two.

**Negative examples**

1. `gdpr/source-32016R0679.txt#82648-82746`
   > prior to the processing in order to assess the particular likelihood and severity of the high risk
   >
   Bare ordering with no stated DURATION — `precedes`, never `deadline_of`.
2. `gdpr/source-32016R0679.txt#157742-157840`
   > ‘personal data’ means any information relating to an identified or identifiable natural person
   >
   No temporal content at all — `is_a`, never `deadline_of`.

---

## `predication` — relational (the default)

**Definition.** An ordinary copula or modal assertion (`X is Y`, `the
controller shall ensure that...`) that does not fall under any of the
other fifteen predicates (v3.6 adds `addressed_to`, below — see that
predicate's own definition). Relational because `relational` is 5D's own
two-sided identity and default dimension. A PURE modal clause with no
further codable content — INCLUDING a clause whose own subject is not an
actor at all (a process, a period, a requirement) — is correctly, BY
DESIGN, `predication`; this is not an enum gap. An actor performing a
concrete, nameable act is `performs` or `competence_of`, never
`predication` by default — see "Decision rules", below, for the test.

**Positive examples**

1. `gdpr/source-32016R0679.txt#166596-166680`
   > Personal data shall be:
   >
   > (a)
   >
   > processed lawfully, fairly and in a transparent manner
2. `ai-act/source-32024R1689.txt` (a pure modal whose own subject, "Testing", is not an actor, so `performs` does not apply either)
   > Testing shall ensure that high-risk AI systems perform consistently for their intended purpose and that they are in compliance with the requirements set out in this Section.

**Negative examples**

1. `gdpr/source-32016R0679.txt#157742-157840`
   > ‘personal data’ means any information relating to an identified or identifiable natural person
   >
   A definition — `is_a` (structural), never the relational default.
2. `gdpr/source-32016R0679.txt#222809-223027`
   > In the case of a personal data breach, the controller shall without undue delay and, where feasible, not later than 72 hours after having become aware of it, notify the personal data breach to the supervisory authority
   >
   A trigger/condition — `requires` (causal), never the relational
   default.

---

## `competence_of` — relational

**Definition.** An INSTITUTIONAL actor's own task, power, or mandate
includes the object act. Restricted to an INSTITUTIONAL body —
`supervisory_authority`, `notified_body`, `market_surveillance_authority`,
`commission`, `member_state`, `european_data_protection_board`,
`ai_office`, `competent_authority`, `digital_services_coordinator`,
`csirt` — never a regulated private or individual actor (a controller, a
processor, a provider, a deployer, a data subject).

**The decisive test: CONFERS/ESTABLISHES versus EXERCISES.**
`competence_of` applies ONLY when the text CONFERS or ESTABLISHES a task
or power on the institutional actor: an explicit phrase ("shall have the
task/power to...", "shall be competent...", "is responsible for...") OR
an enumerated list of tasks or powers (a chapeau + lettered items, e.g.
"each supervisory authority shall ... (a) monitor ... (b) promote
..."). An institution EXERCISING an already-granted power in a SPECIFIC
clause ("The Commission shall adopt...", "may request...", "shall
exercise its powers...") is `performs` — exercising a power is a
DIFFERENT act from the text that conferred it, even when the clause's
own subject is the same institutional actor and the surface vocabulary
("powers") is similar. "Shall exercise their supervisory powers" is
EXERCISE wording, not CONFERRAL wording, even though it mentions
"powers" — it is `performs`.

**Positive examples**

1. `gdpr/source-32016R0679.txt#280609-280663`
   > monitor and enforce the application of this Regulation
   >
   (GDPR Art. 57(1)(a), an enumerated task list item — CONFERS a task)
2. `ai-act/source-32024R1689.txt#405846-406081`
   > National competent authorities shall have the power to temporarily or permanently suspend the testing process, or the participation in the sandbox if no effective mitigation is possible, and shall inform the AI Office of such decision.
   >
   (AI Act Art. 57(11) — a FINITE "shall have the power to..." clause
   CONFERS the suspension power on the institutional actor directly,
   outside an enumerated list)

**The "responsible for" rule.** "Responsible for" counts as conferral
ONLY in a clause that ASSIGNS the responsibility — a finite "is/are
responsible for" main verb, with the institutional actor as its own
grammatical subject. A REDUCED RELATIVE that merely IDENTIFIES which
actor a different clause's own subject must coordinate with ("...
authorities responsible for the enforcement of...", modifying
"authorities", not asserting a mandate ON them) does NOT confer
anything — it stays INSIDE the maximal NP as one of that NP's own
modifiers (see the Unitisation rules, below), never a separate
`competence_of` Statement. See negative example 3.

**A power is never an endpoint, CONFERRED or not (R-l).** A power,
like a right, is a NORMATIVE POSITION (a competence) — the SAME
category as a right (see "Unitisation rules", below, and `performs`'s
own positive example 1) — it is never itself a `subj`/`obj`. Use
`competence_of` ONLY when the text CONFERS the power itself (this
predicate's own decisive test, above); where the text merely
DESCRIBES an existing power (naming it, qualifying its exercise), code
the ACT it covers as `performs` instead — see "Unitisation rules",
below, for the worked example. The act's own HOLDER (for a chapeau's
own lettered list of powers/tasks, or otherwise) is inherited ONLY
from a chapeau or subject NAMED WITHIN THE SAME UNIT, never imported
from a different unit — see "Unitisation rules", below.

**Negative examples**

1. `ai-act/source-32024R1689.txt#406082-406380`
   > National competent authorities shall exercise their supervisory powers within the limits of the relevant law, using their discretionary powers when implementing legal provisions in respect of a specific AI regulatory sandbox project, with the objective of supporting innovation in AI in the Union.
   >
   (AI Act Art. 57(11) — "shall EXERCISE their supervisory powers" is
   exercising an already-granted power, not conferring one — `performs`,
   never `competence_of`, despite the word "powers")
2. `nis2/source-32022L2555.txt#161452-161518`
   > Each Member State shall designate or establish one or more CSIRTs.
   >
   An institutional actor (`member_state`) performing an act with NO
   conferral/establishment wording — `performs`, never `competence_of`.
3. `ai-act/source-32024R1689.txt#460484-460629`
   > the relevant sectoral market surveillance authorities responsible for the enforcement of the Union harmonisation legislation listed in Annex I.
   >
   (AI Act Art. 74(3) — "responsible for the enforcement..." is a
   REDUCED RELATIVE identifying which authorities the host clause's own
   subject, "Member States", must coordinate with; it CONFERS nothing on
   those authorities — the whole phrase stays ONE maximal NP, never
   split into a separate `competence_of` Statement on "responsible for".
   The host clause itself is `performs` on `member_state`, not
   `competence_of`, since "Member States" is not CONFERRED a task or
   power here.)

---

## `performs` — relational

**Definition.** An actor performs an act — the non-deontic relation that
remains once a modal is stripped from a clause naming any actor OTHER
than an institutional body CONFERRING or ESTABLISHING a task/power under
`competence_of`'s own decisive test above (`the controller shall
document the assessment` becomes `controller performs
document_the_assessment`; the modal force itself is nD, never part of
this Statement). `performs` closes the gap an earlier enum version
left: an actor→act clause with NO purpose/trigger/duration/containment
content used to be forced into `predication` purely for lack of a
predicate naming the actor-act relation itself. `performs` is ALSO the
correct predicate for an institutional actor EXERCISING an
already-granted power, even when the surface vocabulary mentions
"powers" — see `competence_of`'s own CONFERS/ESTABLISHES-versus-EXERCISES
test. `performs` is ALSO the correct predicate for the ACT a POWER or a
RIGHT covers, when the power/right itself is merely DESCRIBED (not
newly conferred): a power, like a right, is a NORMATIVE POSITION (a
competence), never an endpoint — "power(s) under X" / "power to X"
(R-l) and "the right to X" / "exercise the right to X" (R-m) are NEVER
themselves an endpoint; see "Unitisation rules", below, for both
worked examples.

**Positive examples**

1. `gdpr/source-32016R0679.txt#203848-203925`
   > at least the right to obtain human intervention on the part of the controller
   >
   Coded `controller performs human_intervention_measure` — the deontic
   RIGHT itself is never a Statement endpoint; only the controller's own
   non-deontic act of providing the measure is.
2. `ai-act/source-32024R1689.txt#406082-406380`
   > National competent authorities shall exercise their supervisory powers within the limits of the relevant law, using their discretionary powers when implementing legal provisions in respect of a specific AI regulatory sandbox project, with the objective of supporting innovation in AI in the Union.
   >
   (AI Act Art. 57(11), the sentence immediately following
   `competence_of`'s own positive example 2 above) EXERCISING an
   already-granted power — `performs`, never `competence_of`, despite
   the word "powers".

**Negative examples**

1. `gdpr/source-32016R0679.txt#280609-280663`
   > monitor and enforce the application of this Regulation
   >
   An enumerated Art. 57(1) task of an institutional actor, CONFERRING
   it — `competence_of`, never `performs`.
2. `gdpr/source-32016R0679.txt#226533-226738`
   > is likely to result in a high risk to the rights and freedoms of natural persons, the controller shall, prior to the processing, carry out an assessment of the impact of the envisaged processing operations
   >
   A trigger/condition governs this clause's own PRINCIPAL relation —
   `requires` (and `precedes`), never `performs`, even though the
   controller is also the one carrying out the act (a trigger-governed
   act is coded by the trigger relation, not duplicated as `performs`).

---

## `addressed_to` — relational (NEW in v3.6)

**Definition.** The RECIPIENT of an act or communication, as its OWN
endpoint. `subj` is the act or communication itself (the SAME act a
companion `performs`/`competence_of`/`requires` Statement, drawn from
the IDENTICAL clause, already names); `obj` is the party the act runs
TO. Before v3.6, "to WHOM" an act ran had no edge of its own: GDPR Art.
33(1)'s own "the controller shall ... notify the personal data breach
to the supervisory authority ..." gave `performs` the WHOLE remainder
as its object, with the supervisory authority buried, unreachable,
INSIDE that one object string — no path could ever end there. This
predicate closes that gap WITHOUT taking anything away from `performs`:
the SAME clause legitimately carries BOTH
`controller performs notify_the_personal_data_breach` AND
`notify_the_personal_data_breach addressed_to supervisory_authority`,
from the one "notify ... to ..." cue — `addressed_to` is LAYERED on top
of whatever predicate already claims the host clause; it never competes
for, and never blocks, that clause's own span.

**Cue.** A notify/report/inform/communicate/submit/transmit verb (any
inflection), followed by its own recipient — either via an explicit "to"
("notify ... to the supervisory authority", "communicate ... to the
data subject", "report ... to the market surveillance authorities of
the Member States where...") or as a DIRECT OBJECT with no "to" at all
("notify the controller" — the processor's own duty, GDPR Art. 33(2)
style — "inform the law enforcement or judicial authorities"). The
candidate recipient NP must ITSELF read as a recipient — one of the
closed `ACTOR_ROLES` surface forms, or a generic authority/body/
Member-State/recipient-shaped NP — before this predicate fires at all;
a bare infinitive or scope phrase riding the SAME word "to" ("to the
extent that", "to ensure", "in relation to", "to be") never even reaches
the cue test, let alone fires it.

**Typing.** `obj` is the closed `ACTOR_ROLES` token when the recipient
NP's own head matches one of that enum's surface forms (e.g. "the
supervisory authority competent in accordance with Article 55" types
as `supervisory_authority`, the trailing qualifier dropped; "the
controller" types as `controller`), otherwise the documented
`other(label)` escape (`statement.ACTOR_OTHER_RE`) — never a silent,
untyped copy of the source span.

**Negation.** `negation: "absent"` by construction, the SAME R-n
reasoning `deadline_of` already uses: a negator about whether the host
act happened at all is that OTHER Statement's own negation concern,
never a re-negation of "and it runs to X".

**Positive examples** (brand-new, invented sentences — never
a verbatim quote from gold)

1. "The processor shall notify the controller promptly after
   discovering an incident." (GDPR Art. 33(2) style — direct object,
   no "to")
   >
   Coded `notify addressed_to controller` — alongside
   `processor performs notify_the_controller`.
2. "The controller shall communicate the incident to the data subject
   within ten days."
   >
   Coded `communicate_the_incident addressed_to data_subject`.
3. "The provider shall report the malfunction to the market
   surveillance authorities of the Member State where it occurred."
   >
   Coded `report_the_malfunction addressed_to market_surveillance_
   authority` — the trailing "of the Member State where it occurred"
   is part of the source span, but types through the closed role at
   its own head.
4. "The platform shall inform the law enforcement or judicial
   authorities of the suspected offence."
   >
   Coded `inform addressed_to other(law_enforcement_or_judicial_
   authorities_of_the_suspected_off)` — not a closed `ACTOR_ROLES`
   member, so the documented escape, never silently dropped.

**Negative examples**

1. "The operator shall report to the extent that resources allow."
   >
   "to the extent that" is a SCOPE phrase, never a recipient — no
   `addressed_to` Statement at all (`performs` alone covers the act).
2. "The provider shall report to ensure transparency with
   stakeholders."
   >
   "to ensure" is a bare infinitive, never a recipient.
3. "The agency shall act in relation to the matters referred to in
   Article 5."
   >
   "in relation to" never names a recipient — `cross_references`
   covers the citation itself, never this predicate.
4. "The incident shall be reported to be reviewed by the board next
   week."
   >
   "to be reviewed" is a bare passive infinitive, never a recipient.

---

## `deadline_of`'s own v3.6 deadline SPLIT

A time limit FUSED into an action phrase, in TWO NEW cues only — a
spelled-out-number duration ("not later than N days/weeks/months": "two
days", "one month") and a qualitative cue ("without undue delay",
"promptly", "immediately") — is now split OUT into its own
`deadline_of` Statement, co-existing with whatever predicate already
claims the host clause, the SAME way `addressed_to` does (above): never
forcing a choice between naming the act and naming its own deadline.
The PRE-EXISTING, digit-based "within N" cue keeps its own ORIGINAL
conflict behaviour unchanged — only these two new cues, and
`addressed_to`, are exempt from first-claimed-span-wins overlap
resolution. `deadline_of`'s own `obj`, for EVERY cue (including the
pre-existing digit one), is the NORMALISED limit — "72 hours after
having become aware of it" becomes "72 hours"; a qualitative cue is
returned lower-cased, unchanged otherwise — never a raw, untrimmed copy
of the matched span. A clause naming BOTH a qualitative cue and a
counted duration ("without undue delay and ... within 24 hours")
legitimately yields TWO `deadline_of` Statements from the one clause,
never a forced choice between them.

**Subject binding.** Applied to EVERY `deadline_of` Statement (every
cue, including the pre-existing digit one). `deadline_of`'s own `subj`
is the GOVERNED ACT — the act or communication the time limit times —
NEVER a clause subject, a sentence fragment, a connective, or a
pronoun. "Member States shall ensure that providers notify the
authority promptly" is `notify deadline_of promptly`, never
`Member_States deadline_of promptly`. The governed act is the SAME act
a companion `addressed_to`/`performs`/`competence_of` Statement from
the SAME clause already names (preferred in that order); or — absent
one — a TRUSTED `requires` consequence ACT (excluded when the
`requires` reading is itself a misfire on a short parenthetical aside,
e.g. "where applicable", or on a "subject to [condition]" qualifier
that is not a genuine trigger) — but ONLY when the time limit sits in
the CONSEQUENCE, never the antecedent (see below); or a TRUSTED
`except_when` exception condition (its "unless"/"except where" cue
family only — "notwithstanding [provision]"/"subject to [provision]"
names a bare provision reference, never trusted as an act); or — absent
THAT — a chapeau's own governing act (a lettered list under one colon:
the whole list shares the chapeau's own act, even across a
`;`-separated sibling item) or a passive construction ("the report ...
shall be made") named earlier in the SAME sentence. An adjectival use
of a qualitative cue ("immediately applicable") is excluded at the cue
itself — it never reaches this binding step at all.

**Antecedent vs consequence.** A time limit sitting INSIDE a
conditional ANTECEDENT ("Where the request is not answered within 30
days, the application shall be deemed accepted") is bound to the
ANTECEDENT's own act ("not answered"), NEVER the consequence
("accepted") — detected by literal span overlap with the `requires`
candidate's own antecedent half rather than its consequence half. There
is no separately-trimmed "just the antecedent's own act" text available
here, so the Statement's ORIGINAL subject (already reading as the
antecedent clause, e.g. "Where the notification ... is not made") is
kept UNCHANGED rather than guessed at or replaced.

**When no governed act can be found.** A NEW deadline cue (word-number
or qualitative) is DROPPED outright — no pre-v3.6 Statement named this
cue, so there is nothing to preserve. The PRE-EXISTING digit-based cue
instead keeps its ORIGINAL subject UNCHANGED — this Statement already
existed before `addressed_to`/the deadline split; finding no governed
act to rebind it to is never a licence to remove or alter it.

---

## Layer — surface, domain, deep

The triple tensor is computed from triples, not from Statements
directly. Every Statement carries a `layer`. The layer rule is
**INDEPENDENT of the predicate** — it comes from the clause's own TEXT
POSITION and FUNCTION, never from which predicate was assigned to it (the
same predicate, e.g. `is_a`, can in principle appear at any layer; a
coder never looks up layer from a predicate-to-layer table). An explicit
PRECEDENCE order resolves every clause, applied top to bottom — the
FIRST matching rule decides:

1. **A definition article, or a definitional clause within an otherwise
   operative article → `deep`.** Example: `gdpr/source-32016R0679.txt
   #157742-157840` (Art. 4(1)'s own "'personal data' means..." —
   structural `is_a`, layer `deep` by this rule).
2. **A principle stated AS a principle → `deep`.** Example: a GDPR
   Art. 5-style principle heading, whatever predicate codes its own
   operative content, is layer `deep` by this rule, never by which
   predicate was used.
3. **A recital → `surface`, UNLESS rule 1 or rule 2 already applies to
   that recital's own content.** Example: `gdpr/source-32016R0679.txt
   #63124-63292` (recital 71's own plain-language "Such processing
   includes 'profiling'..." — `part_of`, layer `surface` by this rule,
   since it is neither a definition nor a principle). A recital that
   RESTATES a definition or a principle is `deep` by rule 1/2, never
   `surface` by position alone — e.g. GDPR recital 1 ("The protection of
   natural persons... is a fundamental right.") restates a FOUNDATIONAL
   PRINCIPLE and is `deep`, despite being a recital.
4. **Everything else operative → `domain`.** Example:
   `gdpr/source-32016R0679.txt#203653-203846` (Art. 22(3)'s own
   trigger-and-safeguard sentence — `requires`, layer `domain`).

This ordered list is the full rule; there is no residual "else" beyond
rule 4, and no clause is layer-ambiguous once the four rules are applied
in order.

---

## Decision rules for the hard boundaries

These are AIDS for a coder's own judgement, never a precedence grammar.
When a clause genuinely satisfies two predicates at once, see "Dual
coding", below — these rules are for the ordinary case where one
predicate clearly dominates.

**Causal vs intentional.** Ask: does the clause name an ANTECEDENT that
MAKES the consequence happen (a breach, a risk threshold) — code
`requires`/`enables` (causal)? Or does the clause name a GOAL the act
SERVES, or a legal GROUND that JUSTIFIES it (`in order to`, `for the
purpose of`, `aims to`, `is intended to`, `based on`) — code
`legislative_purpose_of`/`compliance_purpose_of`/`based_on` (intentional)?
A clause with BOTH a trigger AND a stated purpose is a DUAL-CODING
candidate, not a forced choice (see below).

**Temporal vs causal — a clause MAY need BOTH `requires` and a temporal
predicate.** A bare ordering word (`prior to`, `before`, `after`) with NO
antecedent/consequence logic of its own is `precedes`; a bounded-duration
phrase (`within 30 days`, `not later than 72 hours`) with no
antecedent/consequence logic is `deadline_of`. A trigger/condition word
(`where`, `in the case of`, `if`) introducing a CONSEQUENCE is `requires`
— and when the SAME clause ALSO carries a bare ordering word OR a
duration phrase, the coder produces TWO (or three) Statements from the
one clause: `requires` for the trigger→consequence, PLUS `precedes`
and/or `deadline_of` for whichever temporal content is also present. This
is NOT the dual-coded SPLIT (reserved for causal/intentional, below) — it
is simply MULTIPLE Statements from one clause, each naming a different
part of its own content.

**Structural vs relational.** A named containment/definition/scope/
citation/exception relation is one of the structural predicates (`is_a`,
`part_of`, `applies_to`, `cross_references`, `except_when`). An ordinary
copula or modal assertion that names NONE of these is `predication`
(relational, the default) — never force a structural predicate onto a
clause that merely happens to contain a noun that COULD be read as a
part-whole relation in isolation.

**Recital vs article (legislative purpose vs compliance purpose).** Check
POSITION first (recital or operative article?), then check for a MODAL.
A recital-position purpose clause with no modal is `legislative_purpose_of`;
an operative-article purpose clause WITH a modal is `compliance_purpose_of`.
A recital-position clause that ALSO carries a modal is coded by POSITION,
not by the modal's presence — `legislative_purpose_of` — recording the
modal as a spot-check note, never as a reclassification rule.

**`competence_of` vs `performs`.** Apply `competence_of`'s own cue test
(above) first: an institutional subject AND (an enumerated list item OR
explicit competence/mandate wording). If BOTH hold, `competence_of`;
otherwise, if the clause names any actor performing a concrete act,
`performs`. A clause with no nameable actor and no concrete act is
`predication` by design, not a residual `performs`.

**`based_on` vs `requires` vs `enables`.** See `based_on`'s own
definition, above, which states this boundary directly with the three
comparisons it needs.

## Unitisation rules — what counts as a clause span and a subj/obj span

- **Unit of coding**: ONE clause (the same granularity §8's assertoric
  layer and §18's requirement grammar already use) — never a whole
  sentence with multiple clauses coded as one Statement, and never a
  sub-clause phrase coded alone, EXCEPT a chapeau list item, whose own
  clause span IS the item (below).
- **The clause span is the SMALLEST COMPLETE clause that carries the
  relation** — not the whole sentence it sits in, and not a fragment
  that drops part of the relation's own content. "Smallest" and
  "complete" both matter: a span that is merely short but omits part of
  the relation (e.g. the trigger without its own consequence) is not
  this rule; a span that includes a second, unrelated clause from the
  same sentence is not this rule either.
- **`subj`/`obj` span: the MAXIMAL noun phrase that names the entity or
  concept playing that role, INCLUDING its own modifiers, EXCLUDING a
  leading determiner.** **The closed strip list is EXACTLY (R-q, v3.5)**:
  `a`, `an`, `the`, `one of (the)` — `part of` is NOT on this list; see
  `part_of`'s own "'part of' is not a determiner" rule, R-o, above.
  **The explicit keep list (R-q)**: a demonstrative or a quantifier
  stays INSIDE the span — `this`, `that`, `these`, `those`, `such`,
  `each`, `every`, `any`, `all`, `some` are never stripped; each carries
  its own quantificational content and is not treated as equivalent to
  `a`/`an`/`the`. "Maximal, including modifiers" means the WHOLE
  descriptive phrase is kept together — "appropriate technical and
  organisational measures" is one span, never trimmed to "measures"
  alone — while the determiner itself is stripped. An ACTOR role
  (`controller`, `processor`, ...) is normalised to its closed-vocabulary
  id (`vocabulary/actor-roles.json`) rather than kept as its raw surface
  text, so two Statements naming "the controller" and "a controller" in
  different clauses resolve to the SAME `subj`/`obj` id. A REDUCED
  RELATIVE inside the NP that merely IDENTIFIES the entity ("...
  authorities responsible for the enforcement of...") stays INSIDE the
  maximal NP, never split out into its own Statement — see
  `competence_of`'s own "responsible for" rule, above, for the worked
  case.
- **A disjunctive list of types under ONE determiner is ONE noun
  phrase (R-s, v3.5).** A shared determiner governing a disjunction of
  TYPES names ONE (disjunctively typed) kind of entity, never two (or
  more) Statements split by type — this is NOT the coordinated-DISTINCT-
  entities rule (below), which splits a bare "X and Y" naming two
  different NAMED things sharing a role. The test is the SAME whole/part
  test the coordinated-NP rule and the chapeau rule already use: does
  the disjunction name DISTINCT things sharing a role, or ONE
  type-disjunctive kind under a single determiner? R-s ALSO composes
  with the ordinary MAXIMAL-NP rule (above): the disjunction's own
  `obj` span is the WHOLE noun phrase, modifiers included, not merely
  the disjunction's own head nouns. Worked example — GDPR Art. 4(7)'s
  own definition of "controller". The `is_a` Statement's own `obj`
  span is the WHOLE maximal NP,
  `gdpr/source-32016R0679.txt#159830-159999` (EXCLUDING the leading
  "the" per R-q), spanning from "natural or legal person"
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
  a relative pronoun, and the SAME treatment `part_of`'s own positive
  example 1 already gives "which form part of a filing system" (GDPR
  Art. 2(1)), above. Coded `performs`: `subj` is the antecedent, the
  disjunctive NP, `#159830-159893` (the SAME span the `is_a` Statement
  above already names — NOT the relative pronoun "which" itself, which
  has no span of its own); `obj` is "purposes and means of the
  processing of personal data" (`#159946-159999`, leading "the" stripped per R-q); the verb
  "determines" (the act itself; a light verb in the Statement id may
  restore it) sits in between, within `#159894-159941`
  ("which, alone or jointly with others, determines"), EXCLUDED from
  both endpoints.
- **No MODAL verb is ever inside an endpoint span (R-k).** `shall`,
  `may`, `must`, `should`, `is to be`, and the fixed phrases `shall be
  deemed`/`shall be held` never appear inside a `subj` or `obj` span —
  the endpoint is the residual NOUN PHRASE or predicate complement once
  the modal is stripped; the modal itself is nD, never part of the
  Statement (the SAME principle `requires`'s and `performs`'s own
  definitions already state for the word "obligation", extended here to
  the MODAL VERB ITSELF).
  Positive example 1, `gdpr/source-32016R0679.txt#303197-303466` (GDPR
  Art. 64(3))
  > Regarding the draft decision referred to in paragraph 1 circulated to the members of the Board in accordance with paragraph 5, a member which has not objected within a reasonable period indicated by the Chair, shall be deemed to be in agreement with the draft decision.
  >
  Coded `a_member_which_has_not_objected_within_a_reasonable_period_
  indicated_by_the_chair predication in_agreement_with_the_draft_
  decision` — the `obj` span is `#303429-303465` ("in agreement with the
  draft decision"), EXCLUDING "shall be deemed to be".
  Positive example 2, `ai-act/source-32024R1689.txt#370465-370799` (AI
  Act Art. 46(4) — a DIFFERENT "shall be deemed justified" clause from
  the one that motivated R-k, same instrument)
  > Where, within 15 calendar days of receipt of the information referred to in paragraph 3, no objection has been raised by either a Member State or the Commission in respect of an authorisation issued by a market surveillance authority of a Member State in accordance with paragraph 1, that authorisation shall be deemed justified.
  >

  >
  Coded `no_objection_has_been_raised_by_either_a_member_state_or_the_
  commission_in_respect_of_an_authorisation_issued_by_a_market_
  surveillance_authority_of_a_member_state_in_accordance_with_
  paragraph_1 requires authorisation_justified` — the `subj` span
  INCLUDES "no" (R-n, below — the negator stays INSIDE the antecedent);
  the `obj` span is `#370789-370798` ("justified"), EXCLUDING "shall be
  deemed". The RELATION itself is not negated by anything — `negation:
  "absent"`, the SAME pattern R-n states for `deadline_of`'s own worked
  example, below, so a coder meets ONE pattern for an antecedent
  negator, never two.
  Negative example — the SAME AI Act clause, coded WRONG: `obj` span
  `#370773-370799` ("shall be deemed justified"), INCLUDING the modal —
  forbidden.
- **No right, obligation, permission, or POWER is ever a Statement
  endpoint (R-l, R-m).** A power, like a right, is a NORMATIVE POSITION
  (a competence) — never an endpoint, whatever CONFERS or merely
  DESCRIBES it. "Power(s) under [provision]", "power to X" is coded the
  SAME way a right already is (`performs`'s own positive example 1,
  above): never itself the endpoint. Code the ACT the power or right
  COVERS instead — the holder `performs` the act, or, where the text
  itself CONFERS the power on an institutional actor, `competence_of`
  with that actor and the act (`competence_of`'s own decisive test,
  above). A lettered list under "powers under [provision] include
  power— (a)... (b)..." follows the SAME chapeau rule (below) as any
  other chapeau: each item becomes an ACT of the power's own holder,
  never a list of powers named as such — PROVIDED the holder is named
  WITHIN THE SAME UNIT (a chapeau or a subject in the same clause). An
  act's holder is NEVER imported from a DIFFERENT unit: where a
  chapeau's own holder is named only in a separate subsection outside
  this unit's own clause (the pattern behind the pilot unit that
  motivated this rule, "powers under subsection (1)", where "subsection
  (1)" names its own holder elsewhere), the existing "pronoun or elided
  subject... is OUT OF SCOPE" rule applies instead (above) — the clause
  gets NO Statement, never a guessed or cross-unit holder.
  Positive example 1 (R-l — a power DESCRIBED, not conferred, so
  `performs`), `uk-dpa2018/source-ukpga-2018-12.txt#229829-230128` (UK
  DPA 2018 s. 115(5) — a DIFFERENT "power(s) under" clause from the one
  that motivated R-l, same instrument)
  > The Commissioner's power under Article 58(1)(a) of the UK GDPR (power to require a controller or processor to provide information that the Commissioner requires for the performance of the Commissioner's tasks under the UK GDPR ) is exercisable only by giving an information notice under section 142.
  >
  Coded `commissioner performs require_a_controller_or_processor_to_
  provide_information_for_the_performance_of_the_commissioners_
  tasks_under_the_uk_gdpr` — the ACT span is `#229902-230055`
  ("require a controller or processor to provide information that the
  Commissioner requires for the performance of the Commissioner's
  tasks under the UK GDPR"). The exercisability condition itself is a
  SEPARATE `requires` Statement — its OWN `subj` is the SAME act, never
  the power's own name (the power is an endpoint here too, one level
  up, if it were used as `subj`):
  `require_a_controller_or_processor_to_provide_information_for_the_
  performance_of_the_commissioners_tasks_under_the_uk_gdpr requires
  giving_an_information_notice_under_section_142`, `obj` span
  `#230081-230127` ("giving an information notice under section 142" —
  a GERUND-headed noun phrase, no finite verb phrase).
  Negative example — the SAME clause, coded WRONG:
  `commissioner competence_of
  the_commissioners_power_under_article_58_1_a_of_the_uk_gdpr` (`obj`
  span `#229829-229891`, the power's own NAME as the endpoint) —
  forbidden; a power is never an endpoint, CONFERRED or not.
  Positive example 2 (R-m — the right itself never an endpoint),
  `gdpr/source-32016R0679.txt#323115-323345` (GDPR Art. 78(1) — a
  DIFFERENT "the right to X" clause from the one that motivated R-m,
  same instrument)
  > Without prejudice to any other administrative or non-judicial remedy, each natural or legal person shall have the right to an effective judicial remedy against a legally binding decision of a supervisory authority concerning them.
  >
  Coded `natural_or_legal_person performs
  an_effective_judicial_remedy_against_a_legally_binding_decision_of_
  a_supervisory_authority_concerning_them` (`obj` span `#323238-323344`,
  "an effective judicial remedy against a legally binding decision of a
  supervisory authority concerning them", EXCLUDING "the right to") —
  never `natural_or_legal_person performs
  right_to_an_effective_judicial_remedy...` (`obj` span
  `#323225-323344`, INCLUDING "the right to") — the SAME rule
  `performs`'s own positive example 1 already states for "the right to
  obtain human intervention". A Statement id is an invented
  snake_case label, never a literal copy of the span text — here it
  matches the span exactly, with no added verb; an id MAY instead add a
  light verb where the predicate itself needs one to read as an act
  (e.g. "seek_X" for an `obj` span naming only "X") — either convention
  is acceptable, but a SINGLE unit is coded consistently.
- **Pronouns (R-r, v3.5).** A pronoun ("it", "they", "which", "who") or
  an elided subject is NOT automatically out of scope. If the pronoun's
  referent is NAMED INSIDE THE SAME UNIT (the same sentence, or the
  same chapeau+list unit), the Statement uses the REFERENT's OWN span
  as the endpoint, never the pronoun's own text — worked example,
  `gdpr/source-32016R0679.txt#155546-155580` (already quoted in this
  codebook's `part_of` positive example 1, GDPR Art. 2(1)): "which form
  part of a filing system" — the relative pronoun "which" has its own
  antecedent, "personal data" (`#155532-155545`), named earlier in the
  SAME sentence; the Statement's `subj` span is the antecedent "personal
  data", never "which" itself (which has no span of its own). If NO
  referent is named ANYWHERE in the unit (a dropped subject in a modal
  clause referring back to an earlier SENTENCE'S subject, outside the
  unit), there is no Statement at all — such a clause gets NO Statement,
  never a guessed subject and never silently folded into `predication`;
  record the unit out of scope if it has no other Statement.
- **A coordination of DISTINCT entities gives ONE Statement per
  conjunct, with the shared remainder of the clause INHERITED across
  all of them** — the same inheritance already used for a chapeau list
  (below), applied to an "X and Y" surface form naming two different
  things rather than two listed items. `ai-act/source-32024R1689.txt#78545-78603`
  > employees and persons providing services through platforms
  >
  (an AI Act recital, on work-related relationships in the Annex III
  employment context — the host clause, "should... involve", is
  `predication`, not `applies_to`; the conjunct split is the only
  teaching point here) is coded as TWO Statements —
  `relevant_work-related_contractual_relationships predication employees`
  and `relevant_work-related_contractual_relationships predication
  persons_providing_services_through_platforms` — the SAME `subj`,
  inherited from the shared clause, a DIFFERENT `obj` per conjunct,
  never one Statement whose `obj` names both together. A coordination
  of MODIFIERS within a single entity, by contrast, stays ONE maximal
  NP: `gdpr/source-32016R0679.txt#83900-83983`
  > systematic and extensive evaluation of personal aspects relating to natural persons
  >
  is ONE span — "systematic" and "extensive" both modify the SAME
  "evaluation", naming one entity, not two — never split into a
  "systematic evaluation" Statement and an "extensive evaluation"
  Statement. The test is the SAME one `part_of`'s own "X includes Y"
  direction-swap and the chapeau-list rule already apply: does the
  coordination name DISTINCT things sharing a role, or ONE thing with
  distinct qualities?
- **List items under a chapeau: ONE Statement per item, and the clause
  span is the ITEM, not the chapeau+list sentence as a whole. The
  subject is INHERITED from the chapeau** — the chapeau's own named
  actor or trigger becomes the SHARED `subj` of every item Statement;
  each item supplies only the differing `obj`. This is the SAME rule
  already applied to GDPR Art. 22(3)'s own safeguards list and Art.
  57(1)'s own task list (one `requires`/`competence_of` Statement per
  listed element, sharing the trigger/actor `subj`); UK DPA 2018 s. 6(1)
  applies it to `except_when`:
  `uk-dpa2018/source-ukpga-2018-12.txt#62382-62527`
  > The definition of “controller” in Article 4(1)(7) of the UK GDPR has effect subject to— a subsection (2), b section 209, and c section 210.
  >
  is coded as THREE Statements, each
  `definition_of_controller_in_article_4_1_7_uk_gdpr except_when
  <provision>` — the SAME `subj` (id
  `definition_of_controller_in_article_4_1_7_uk_gdpr`, inherited from
  the chapeau, MAXIMAL-NP span `#62386-62450` — "definition of
  'controller' in Article 4(1)(7) of the UK GDPR", EXCLUDING the
  determiner "The" and EXCLUDING the chapeau's own verb phrase "has
  effect subject to—", per the subj/obj span rule above), a DIFFERENT
  `obj` per lettered item: `subsection_2` (clause span `#62478-62492`),
  `section_209` (clause span `#62496-62507`), `section_210` (clause span
  `#62515-62526`) — never one Statement whose `obj` names all three
  provisions together, and never the whole chapeau+list sentence as one
  clause span.
- **A WHOLE-naming chapeau works the same rule in the other direction:
  the differing element per item is the `subj`, and the chapeau's own
  entity is the SHARED `obj`** (the `part_of` variant — `part_of`'s own
  direction is always part-to-whole, so a chapeau that names the WHOLE
  puts each item on the `subj` side, never the `obj` side).
  **The coordination rule above applies WITHIN a chapeau item, too: a
  chapeau item that itself coordinates distinct entities yields one
  Statement per conjunct**, the SAME way a bare coordinated clause does.
  `gdpr/source-32016R0679.txt#221195-221298`
  > appropriate technical and organisational measures to ensure a level of security appropriate to the risk
  >
  is the WHOLE (GDPR Art. 32(1)'s own chapeau: the controller and
  processor shall implement this phrase, "including inter alia as
  appropriate", followed by a lettered list); item (a),
  `gdpr/source-32016R0679.txt#221343-221395`
  > the pseudonymisation and encryption of personal data
  >
  itself coordinates TWO distinct measures — "pseudonymisation" and
  "encryption" — sharing the complement "of personal data", and is
  coded as TWO Statements, the shared complement distributed to each:
  `pseudonymisation_of_personal_data part_of
  appropriate_technical_and_organisational_measures_to_ensure_a_level_of_security_appropriate_to_the_risk`
  and `encryption_of_personal_data part_of
  appropriate_technical_and_organisational_measures_to_ensure_a_level_of_security_appropriate_to_the_risk`
  — the SAME `obj` (the chapeau's own whole) in both, a DIFFERENT `subj`
  per conjunct, never one Statement naming both measures together. Item
  (b), by contrast, `gdpr/source-32016R0679.txt#221403-221527`
  > the ability to ensure the ongoing confidentiality, integrity, availability and resilience of processing systems and services
  >
  coordinates "confidentiality, integrity, availability and resilience"
  as FOUR qualities of the SAME "ability", not four distinct measures —
  ONE maximal `subj` span, ONE `part_of` Statement, never split; item
  (c) and onward follow whichever of the two patterns their own surface
  form matches, never collapsed into one Statement naming every item
  together.
- **No right, obligation, or permission is ever a Statement endpoint.**
  Where Art. 22(1)/(3)-style text names a RIGHT, the Statement names the
  underlying non-deontic act or measure instead (e.g. the controller
  PERFORMS the measure the right concerns), never the right itself.

## Dimension-blind coding

A coder works from `docs/codebook/typed-statements-v1-coder-view.md` —
the SAME predicate table with every "structural because.../relational
because..." rationale removed, so a coder chooses a predicate purely
from its FACT PATTERN, never by reasoning toward a dimension first and
backfilling a predicate that happens to match it. The dimension itself
is then looked up automatically, after coding, from `vocabulary/
statement-predicates.json`'s own closed mapping — a coder never assigns
`dimension` directly.

## The procedure for negation (R-p, v3.5)

`negation` answers ONE question, and only one: does a negator take
SCOPE over THIS Statement's own relation (the subj-predicate-obj triple
as a WHOLE)? This REPLACES the earlier procedure's own fourth step
(which put a negator in another clause into `uncertain`) and
generalises `requires`'s/`deadline_of`'s own antecedent carve-out
(R-n, above) to endpoint spans generally. It still reuses §18's own
digested negation lexicon (`requirement.py`'s `_NEGATION_RE`) — this
codebook does not define a second lexicon — now explicitly including
"neither ... nor" as a negator (v3.5; it was already in §18's own
lexicon, but the codebook text did not previously name it).

**R-p.1 — what counts as a clause.** A clause is a FINITE clause: a
subject plus a finite verb, INCLUDING a subordinate finite clause
("unless...", "where...", "if...", a relative clause with a finite
verb, a clausal complement such as a "that..." clause following a verb
like "demonstrates"). A prepositional phrase, a reduced relative, and a
participial phrase are NOT clauses — they belong to the clause they sit
in. Worked example — GDPR Art. 12(2)'s own
`gdpr/source-32016R0679.txt#181803-181844`:
> In the cases referred to in Article 11(2)
is a PREPOSITIONAL PHRASE (headed by "In"), not a clause — it belongs
to the finite clause it introduces,
`gdpr/source-32016R0679.txt#181846-181976` ("the controller shall not
refuse to act..."), never a clause of its own. This does NOT mean the
phrase gets no Statement at all: it still yields its own
`cross_references` Statement (citing "Article 11(2)"), whose own
`negation` is `absent` under R-p.2: the clause's negator "shall not"
scopes only the refuse-relation, never the citation relation →
`absent` (R-p.2).

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
scope → uncertain; constructed, not quoted statute text, 35
characters): "The board may not necessarily act." — two readings are
both available and the text does not decide between them: (i) "not"
scopes "may" itself, so the board IS NOT PERMITTED to act (a
prohibition); (ii) "not" scopes only "necessarily", so the board IS
permitted to act, but IS NOT REQUIRED TO (a permission, merely not a
mandatory one) — `negation: "uncertain"`.

1. Scan the SENTENCE containing the clause (§18's own sentence-boundary
   rule, including its abbreviation handling) for a negator: "not",
   "no", "never", "nothing", "none", "neither ... nor", or one of their
   inflected forms — the SAME digested lexicon §18's `requirement.py`
   already carries, with "neither ... nor" now named explicitly as a
   negator, never a plain coordinator. An `except_when` cue ("unless", "except", "by way
   of derogation from", "save where") is never itself a negator — it
   routes a clause to a DIFFERENT predicate (`except_when`), never to
   `negation: "present"`. The "not" in a savings clause ("shall not
   affect X", "does not affect X") is part of the savings cue, never a
   negator: a savings `cross_references` is `negation: "absent"` unless
   a separate negator applies.
2. If the negator lies wholly INSIDE an endpoint span (`subj` or `obj`)
   or INSIDE an antecedent, it stays there, as part of what that span or
   antecedent SAYS — the Statement's own RELATION is not negated by it:
   `negation: "absent"`. (This is R-n's own rule, generalised: R-n
   covered the antecedent of a `requires` Statement specifically; v3.5
   states the SAME outcome for any endpoint span a negator sits wholly
   inside.) Worked example — `ai-act/source-32024R1689.txt#370465-370799`
   (AI Act Art. 46(4), already quoted in this codebook's R-k positive
   example 2): the `requires` Statement's `subj` span includes "no" (as
   part of "no objection has been raised..."); the RELATION itself is
   not negated by anything — `negation: "absent"`.
3. If the negator is a FIXED IDIOM — "not later than", "no later than",
   "not less than", "no less than", "not exceeding", "whether or not",
   "not only ... but also" — it is never a negator at all:
   `negation: "absent"`. Worked example —
   `gdpr/source-32016R0679.txt#158345-158378` (GDPR Art. 4(2), already
   quoted in this codebook's `is_a` negative example 2): "whether or
   not by automated means" — "or not" is part of the fixed idiom, never
   a negator.
4. If the negator is in ANOTHER clause of the same sentence — a
   DIFFERENT FINITE clause (R-p.1) from the Statement's own — it does
   not reach THIS Statement's relation at all: `negation: "absent"`.
   This REPLACES the earlier procedure's own fourth step, which put
   this case into `uncertain`; every Statement is clause-scoped, so a
   negator confined to a different finite clause simply never negates
   THIS clause's relation, and there is no genuine uncertainty to flag.
   Worked example, GDPR Art. 12(2)'s own second sentence
   (`gdpr/source-32016R0679.txt#181803-182071`, not quoted here in
   full — see the two short fragments below for its own negator-bearing
   clauses). The main finite clause,
   `gdpr/source-32016R0679.txt#181846-181976`, opens:
   > the controller shall not refuse to act on the request
   >
   (quoted to `#181899` only; the clause continues unquoted to
   `#181976`) — this clause HAS the negator "not", scoping its own
   refuse-relation. The `except_when` Statement built from the
   subordinate finite clause `gdpr/source-32016R0679.txt#181978-182070`
   opens:
   > unless the controller demonstrates that it is not in
   >
   (quoted to `#182030` only; the clause continues unquoted to
   `#182070`) — this is the Statement "whose own clause lacks the
   negator": at its OWN top level ("the controller demonstrates that
   [complement]"), this clause carries no negator; "not" sits inside
   the NESTED, FURTHER-SUBORDINATE finite complement clause
   `gdpr/source-32016R0679.txt#182018-182070` ("it is not in a position
   to identify the data subject" — its own subject "it", its own finite
   verb "is") — a DIFFERENT finite clause under R-p.1, not the
   except_when Statement's own top clause. The except_when Statement's
   own relation (the general rule does not apply when the controller so
   demonstrates) is therefore `negation: "absent"`.
5. If NONE of steps 2-4 applies and there is no negator anywhere in the
   Statement's own clause: `negation: "absent"`.
6. If a negator IS in the Statement's OWN clause and it unambiguously
   negates THIS clause's own relation: `negation: "present"`. The
   closed CUE list for this case: "shall not", "may not", "does not
   apply", "No X shall...", "Nothing in X prevents Y" (and the
   structurally identical "Nobody"/"None of X"/"Neither X nor Y"
   forms) — each a negator IN the Statement's own clause, scoping the
   relation itself. Worked example — `gdpr/source-32016R0679.txt
   #180662-180864` (GDPR Art. 11(2), already quoted in this codebook's
   `except_when` positive example 2): "Articles 15 to 20 shall not
   apply except where the data subject, for the purpose of exercising
   his or her rights under those articles, provides additional
   information enabling his or her identification." — the `applies_to`
   Statement on "Articles 15 to 20 shall not apply" is `negation:
   "present"`: the negator is in the Statement's own clause and negates
   the applicability relation itself.
7. If a negator IS in the Statement's OWN clause but its scope over
   THIS clause's own relation GENUINELY cannot be decided from the text
   (see R-p.2, above, for the worked example and the rule that there is
   NO "when in doubt" default): `negation: "uncertain"` — NEVER
   silently resolved to `present` or `absent`. Under v3.5, `uncertain`
   is reserved for THIS case only — a negator outside the Statement's
   own clause is `absent` per step 4, never `uncertain`; a negator
   inside the Statement's own clause that clearly scopes only an
   adjunct (not the relation) is ALSO `absent` per R-p.2, never
   `uncertain`.
8. A Statement with `negation: "uncertain"` is still coded and stored
   (it is not omitted) — gold-protocol agreement is measured on it like
   any other Statement.
9. **Exceptions carved from a negated rule.** Where a general rule is
   stated negated and an `except_when` clause carves an exception from
   it ("X shall not apply except where Y..."), the MAIN RULE Statement
   (the negated general rule) is `negation: "present"` (step 6); the
   SEPARATE `except_when` Statement, built from the "except where Y"
   clause, is `negation: "absent"` (step 5) — the exception clause's
   own relation (the carve-out condition Y) carries no negator of its
   own. Worked example — the SAME sentence as step 6's example,
   `gdpr/source-32016R0679.txt#180662-180864`: the main-rule
   `applies_to` Statement is `subj` = "Articles 15 to 20", `obj` =
   "such cases" (`#180650-180660`, the demonstrative "such" KEPT per
   R-q — a cross-sentence reference back to the controller's own
   inability to identify the data subject, described in the PRECEDING
   sentence of the same paragraph), `negation: "present"`; the
   `except_when` Statement
   built from "except where the data subject... provides additional
   information enabling his or her identification" is `negation:
   "absent"`.

## The procedure for dual coding

1. A coder first tries ONE predicate per clause, using the decision rules
   above.
2. If a clause genuinely reads as BOTH causal and intentional at once
   (the ONLY pair this codebook's dual-coded split applies to), the
   coder produces TWO Statements: a `causal` one (`enables`/`requires`)
   and an `intentional` one (`legislative_purpose_of`/
   `compliance_purpose_of`/`based_on`), with the causal Statement's `obj`
   set equal to the intentional Statement's `subj` (the shared middle
   segment, `statement.dual_split_violations()`).
3. Both Statements are submitted to the SAME blind-coding and spot-check
   process as any other Statement (`docs/codebook/gold-protocol-v1.md`).
   If inter-coder agreement on WHETHER a given clause needed the split
   falls below the gold protocol's own gate, that specific boundary is
   reported as unsupported and excluded from the benchmark.

## The entity/actor vocabulary

A CLOSED list of the roles a `subj`/`obj` entity id may name
(`vocabulary/actor-roles.json`, `statement.ACTOR_ROLES`), plus one
documented escape (`other(label)`). The following EU-instrument roles
were added to the closed vocabulary before the freeze.

| role | one-line definition | verbatim example |
|---|---|---|
| `competent_authority` | an authority a Member State designates to supervise and enforce an instrument | `dsa/source-32022R2065.txt#327097-327302`: "Member States shall designate one or more competent authorities to be responsible for the supervision of providers of intermediary services and enforcement of this Regulation (‘competent authorities’)." |
| `digital_services_coordinator` | the DSA's own lead competent authority in a Member State | `dsa/source-32022R2065.txt#327307-327408`: "Member States shall designate one of the competent authorities as their Digital Services Coordinator." |
| `csirt` | a computer security incident response team a Member State designates or establishes under NIS2 | `nis2/source-32022L2555.txt#161452-161518`: "Each Member State shall designate or establish one or more CSIRTs." |
| `essential_entity` | an NIS2 entity classified essential by type, size, or specific designation | `nis2/source-32022L2555.txt#135927-136096`: "entities of a type referred to in Annex I which exceed the ceilings for medium-sized enterprises provided for in Article 2(1) of the Annex to Recommendation 2003/361/EC;" |
| `important_entity` | an NIS2 entity of a type in Annex I/II that does not qualify as essential | `nis2/source-32022L2555.txt#137038-137250`: "For the purposes of this Directive, entities of a type referred to in Annex I or II which do not qualify as essential entities pursuant to paragraph 1 of this Article shall be considered to be important entities." |
| `provider_of_online_platform` | the DSA actor operating a hosting service that disseminates information to the public at a recipient's request | `dsa/source-32022R2065.txt#198408-198636`: "‘online platform’ means a hosting service that, at the request of a recipient of the service, stores and disseminates information to the public, unless that activity is a minor and purely ancillary feature of another service" |
| `very_large_online_platform` | a DSA online platform at or above the 45-million-average-monthly-active-recipients threshold | `dsa/source-32022R2065.txt#268550-268858`: "This Section shall apply to online platforms and online search engines which have a number of average monthly active recipients of the service in the Union equal to or higher than 45 million, and which are designated as very large online platforms or very large online search engines pursuant to paragraph 4." |

A role this list does not yet name is carried as `other(label)`
(`statement.ACTOR_OTHER_RE`) — never silently dropped, and never a
permanent substitute for extending the closed list (the gold protocol
logs every `other(...)` use as a candidate addition to the next
version). The SUBSET that is an institutional body —
`supervisory_authority`, `notified_body`, `market_surveillance_authority`,
`commission`, `member_state`, `european_data_protection_board`,
`ai_office`, `competent_authority`, `digital_services_coordinator`,
`csirt` (`statement.INSTITUTIONAL_ACTOR_ROLES`) — is the set
`competence_of`'s own cue test restricts its `subj` to; every other role
uses `performs`.

## Coverage measurement

The predicate enum's own coverage against real operative text — how
often a sentence's principal relation fits no predicate — is measured in
`docs/codebook/coverage-measurement.md`, against two independent samples.

## Rules motivated by the blind pilot (v3.1, v3.2, v3.3, v3.4, v3.5)

A blind pilot (two pinned model coders, 50 units) found disagreements
clustering at a small number of codebook gaps. The resulting rulings
are recorded in full, with their own history, in
`docs/decisions/0008-typed-statement-v3-rulings.md`'s own addenda.
None of them changes the predicate set or any predicate's dimension.
This section states each resulting RULE only —
see the ADR for why each one was needed.

1. **`performs` vs `competence_of`** — `competence_of`'s own definition
   above states the decisive test: CONFERRING/ESTABLISHING a task or
   power is `competence_of`; EXERCISING an already-granted one is
   `performs`, even when the surface wording mentions "powers"; "is/are
   responsible for" confers only as a FINITE assigning clause, never as
   a reduced relative that merely identifies the actor.
2. **"subject to [provision]"** — `except_when`'s and `applies_to`'s own
   definitions above extend the "notwithstanding"/"irrespective of"
   head-noun routing test to "subject to": a provision-reference head
   noun is a derogation (`except_when`); a condition/requirement head
   noun is `requires`, not `cross_references` and not `except_when`.
3. **Span granularity** — the "Unitisation rules" section above states
   that the clause span is the smallest COMPLETE clause (not the whole
   sentence, not a fragment), that `subj`/`obj` spans are MAXIMAL noun
   phrases including their own modifiers (never trimmed to a bare head
   noun), and that a chapeau+list clause's own span is the ITEM, with
   the subject inherited from the chapeau.
4. **R-i: coordinated NPs** (recorded in ADR 0008's own
   addendum) — a coordination of DISTINCT entities ("X and Y") gives one
   Statement per conjunct, sharing the clause's remainder, the same as a
   chapeau list — INCLUDING within a single chapeau item, which yields
   one Statement per conjunct exactly like a bare coordinated clause; a
   coordination of MODIFIERS or QUALITIES within one entity stays one
   maximal NP. See "Unitisation rules", above, for the worked examples.
5. **R-k, R-l, R-m, R-o** (recorded in ADR 0008's own
   Addendum C, refined by Addendum D) — no MODAL verb is ever inside an
   endpoint span (R-k); a power, like a right, is a NORMATIVE POSITION
   (a competence), never an endpoint, and its act's own HOLDER is
   inherited only from a chapeau or subject WITHIN THE SAME UNIT (R-l);
   "exercise the right to X" is the SAME never-an-endpoint rule as any
   other right (R-m); "part of" is not a determiner to strip, "form(s)
   part of" is a `part_of` VERB CUE, and "references to X include Y" is
   `applies_to` (Y falls within the scope of the term X), never `is_a`,
   never `part_of` (R-o). See `competence_of`'s, `performs`'s,
   `applies_to`'s, and `part_of`'s own sections, and "Unitisation
   rules",
   above, for every worked example.
6. **R-n** (recorded in ADR 0008's own Addendum D) — a
   negator INSIDE an ANTECEDENT stays INSIDE the `requires` Statement's
   own `subj` span; under §21, `negation: "present"` means the RELATION
   ITSELF is negated, which a negator confined to the antecedent's own
   content never does, so such a Statement is `negation: "absent"` —
   and so is the companion `deadline_of` Statement for a period named
   in the consequence. See `requires`'s and `deadline_of`'s own
   sections, and "The procedure for negation", above, for the worked
   examples.
7. **R-p, R-q, R-r, R-s** (recorded in ADR 0008's own
   Addendum E) — the negation procedure is rewritten around CLAUSE
   SCOPING, where a clause is a FINITE clause (a subject plus a finite
   verb, including a subordinate finite clause; never a prepositional
   phrase, a reduced relative, or a participial phrase — R-p.1): a
   negator in ANOTHER finite clause, or wholly inside an endpoint
   span/antecedent, or part of a fixed idiom, or scoping only an
   adjunct within the Statement's own clause, is `negation: "absent"`;
   `uncertain` is reserved for a negator in the Statement's OWN clause
   whose scope over the relation GENUINELY cannot be decided, with NO
   "when in doubt" default (R-p.2); "neither ... nor" joins the closed
   negator list; an exception carved from a negated rule gives the main
   rule `present` and the `except_when` Statement `absent` (R-p). The
   determiner strip list is EXACTLY `a`/`an`/`the`/`one of (the)`, and
   demonstratives/quantifiers (`this`, `that`, `these`, `those`,
   `such`, `each`, `every`, `any`, `all`, `some`) are an explicit keep
   list, never stripped (R-q). A pronoun with an in-unit referent takes
   the referent's own span; a pronoun with no in-unit referent gets no
   Statement (R-r). A disjunctive list of types under one determiner
   (GDPR Art. 4(7)'s own "natural or legal person, public authority,
   agency or other body") is ONE noun phrase, never split by type
   (R-s). See "The procedure for
   negation", "Unitisation rules", above, for every worked example.
