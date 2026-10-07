# Coverage measurement: typed-statements-v3 enum

This document measures how often the closed, versioned predicate enum
(`vocabulary/statement-predicates.json`, `typed-statements-v3`) fails to
name the relation a real operative sentence actually expresses, against
two independently drawn samples of GDPR and AI Act operative text. It
describes method and results only.

## Method

Operative text: GDPR and the AI Act, each from "HAVE ADOPTED THIS
REGULATION" to "Done at Brussels" (the articles, excluding the preamble/
recitals and the closing formula). Two samples are reported, drawn by two
independent sentence splitters and two independent random seeds, each 15
sentences per instrument, coded by hand against the v3 enum:

- **Sample A** (seed `20261005`): a plain regex splitter (a boundary
  after `.`/`;` followed by whitespace and a capital letter or `(`),
  applied to 879 GDPR sentences and 1,310 AI Act sentences.
- **Sample B** (seed `91817`): an independently written splitter
  (paragraph-aware, dropping headings by a leading `Article`/`CHAPTER`/
  `SECTION` token and a minimum length of 70 characters), applied to 836
  GDPR sentences and 1,271 AI Act sentences.

**Classification buckets**, distinguishing WHY a sentence does or does
not land in a specific, non-default predicate:

- **FITS** — a specific (non-`predication`) predicate from the v3 enum
  applies to the sentence's own PRINCIPAL relation.
- **OUT OF SCOPE** — no Statement at all is coded (a heading/title
  artifact of a sentence splitter, or a content-clause list-item
  fragment with no resolvable subject of its own — the codebook's own,
  pre-existing unitisation exclusion). Never counted as `predication`.
- **FORCED-BY-DESIGN** — a PURE modal clause with no further codable
  content, or a clause whose own subject is not an actor (a process, a
  period, a requirement) correctly, by design, lands in `predication` —
  not an enum gap; 5D is categorically neutral on modal force.
- **CORRECT-DEFAULT** — an ordinary relational fact with genuinely no
  structural/causal/intentional/temporal content, and no actor→act
  relation either; `predication` is simply the right call.
- **FORCED-BY-GAP** — none of the above; a genuine coverage gap.

Two rates are reported per instrument per sample:

- **Main-relation predication rate** — the share of sentences whose
  PRINCIPAL relation is coded only as `predication` (FORCED-BY-DESIGN +
  FORCED-BY-GAP + CORRECT-DEFAULT, over sentences that get a Statement at
  all; a sentence with at least one FIT counts as a fit even if a
  secondary relation in the same sentence is left uncoded).
- **Forced-by-gap rate** — the share whose principal relation fits no
  predicate for a reason other than by-design modal neutrality or a
  genuinely correct default. This is the number closest to "the enum is
  missing a predicate for this."

`performs` (an actor performing a non-deontic act, any actor other than
an institutional body acting under its own enumerated mandate) and the
restriction of `competence_of` to an institutional actor named in an
enumerated task/power list OR explicit competence/mandate wording (`shall
be competent to...`, `shall have the power/task to...`) are both part of
the v3 enum measured here — the actor→act relation that the v2 enum left
uncoded is now coded wherever a concrete act and a nameable actor are
both present in the sentence.

## Sample A (seed 20261005)

### GDPR

| # | Sentence (abbreviated) | Classification |
|---|---|---|
| 1 | "(8) 'processor' means a natural or legal person..." | FITS — `is_a` |
| 2 | "(i) processing is necessary for reasons of public interest...on the basis of Union or Member State law..." | FITS — `based_on` |
| 3 | "Processing...based on Article 6(1) shall be carried out only under the control of official authority..." | FITS — `based_on` |
| 4 | "Information provided under Articles 13 and 14...shall be provided free of charge." | FITS — `cross_references` |
| 5 | "The data subject shall have the right to obtain...confirmation...and...access...and the following information: (a) the purposes..." | FITS — `part_of` (the listed information items are part of the disclosure content; the deontic right itself is never coded) |
| 6 | "(c) where applicable, transfers...including the identification of that third country..." | FITS — `part_of` (swapped from the former `includes`) |
| 7 | "(b) the ability to ensure the ongoing confidentiality, integrity, availability and resilience..." | FITS — `part_of` (one listed measure) |
| 8 | "In assessing the appropriate level of security account shall be taken...of the risks...from accidental or unlawful destruction..." | FITS — `based_on` (weak: the risk is based on the listed causes) |
| 9 | "(c) describe the likely consequences of the personal data breach;" | OUT OF SCOPE — bare infinitive fragment, no subject |
| 10 | "Such controllers or processors shall make binding and enforceable commitments...to apply those appropriate safeguards..." | FITS — `performs` (controller/processor performs making the commitments) |
| 11 | "Section 2 Competence, tasks and powers Article 55 Competence 1." | OUT OF SCOPE — heading, a splitter artifact |
| 12 | "The lead supervisory authority shall be the sole interlocutor..." | FORCED-BY-DESIGN — a status/role copula, no act to extract |
| 13 | "(i) monitor relevant developments...development of information and communication technologies..." | FITS — `competence_of` (an enumerated Art. 57(1) task) |
| 14 | "(q) conduct the accreditation of a body..." | FITS — `competence_of` |
| 15 | "(u) promote the cooperation...between the supervisory authorities;" | FITS — `competence_of` |

FITS 12/15; OUT OF SCOPE 2/15; FORCED-BY-DESIGN 1/15; CORRECT-DEFAULT
0/15; FORCED-BY-GAP 0/15. **Main-relation predication: 1/13 = 7.7%.
Forced-by-gap: 0/13 = 0%.**

### AI Act

| # | Sentence (abbreviated) | Classification |
|---|---|---|
| 1 | "(12) 'intended purpose' means the use for which an AI system is intended..." | FITS — `is_a` |
| 2 | "The risk management measures referred to in paragraph 2, point (d), shall give due consideration...with a view to minimising risks..." | FITS — `cross_references` |
| 3 | "Testing shall ensure that high-risk AI systems perform consistently for their intended purpose..." | FORCED-BY-DESIGN — a pure modal; "for their intended purpose" modifies a performance STANDARD, not a purpose clause attached to the main verb, and the subject ("Testing") is not an actor |
| 4 | "Notified bodies shall accept the form for the purposes of the conformity assessment." | FITS — `compliance_purpose_of` |
| 5 | "...the logs shall be kept for a period...of at least six months, unless provided otherwise..." | FITS — `deadline_of` (also dual-codable `except_when` for "unless") |
| 6 | "(b) any refusal...issued in accordance with the requirements of Annex VII;" | FITS — `based_on` |
| 7 | "This obligation shall not cover sensitive operational data..." | FITS — `applies_to`, negated |
| 8 | "Where the Commission considers the authorisation unjustified, it shall be withdrawn..." | FITS — `requires` |
| 9 | "The identification number of the notified body shall be affixed by the body itself or...by the provider..." | FITS — `performs` (the acting body/provider affixes the number; no enumerated-list/mandate wording, so not `competence_of`) |
| 10 | "The provider...shall be liable under applicable Union and national liability law..." | FITS — `based_on` (weak) |
| 11 | "The Commission...shall determine the number of experts...and shall ensure fair gender and geographical representation." | FITS — `performs` |
| 12 | "Article 80 Procedure for dealing with AI systems..." | OUT OF SCOPE — heading |
| 13 | "(f) where applicable, no authorised representative has been appointed;" | CORRECT-DEFAULT — a bare negated existential, no actor named in the span itself |
| 14 | "(b) a description of the relevant facts...the reason why the downstream provider considers that..." | OUT OF SCOPE — noun-phrase fragment, no resolvable subject |
| 15 | "Lawyers duly authorised to act may supply information on behalf of their clients." | FITS — `performs` |

FITS 11/15; OUT OF SCOPE 2/15; FORCED-BY-DESIGN 1/15; CORRECT-DEFAULT
1/15; FORCED-BY-GAP 0/15. **Main-relation predication: 2/13 = 15.4%.
Forced-by-gap: 0/13 = 0%.**

## Sample B (seed 91817)

### GDPR (of 836 sentences)

| # | Sentence (abbreviated) | Classification |
|---|---|---|
| 1 | "When consulting the supervisory authority pursuant to paragraph 1, the controller shall provide..." | FITS — `requires` + `cross_references` |
| 2 | "from which source the personal data originate..." | OUT OF SCOPE — relative-clause fragment |
| 3 | "Where a controller...paid full compensation...shall be entitled to claim back..." | FITS — `requires` |
| 4 | "The controller or processor shall document the assessment...in the records referred to in Article 30." | FITS — `performs` + `cross_references` |
| 5 | "The controller shall implement...measures for ensuring that, by default, only personal data...are processed." | FITS — `compliance_purpose_of` |
| 6 | "the existence of automated decision-making, including profiling, referred to in Article 22(1) and (4)..." | FITS — `part_of` (swapped) + `cross_references` |
| 7 | "is necessary for entering into, or performance of, a contract..." | OUT OF SCOPE — elided-subject fragment |
| 8 | "By derogation from paragraph 1, each supervisory authority shall be competent to handle a complaint..." | FITS — `except_when` + `competence_of` (explicit "shall be competent" wording) + `requires` |
| 9 | "The Commission shall enter into consultations...with a view to remedying the situation..." | FITS — `compliance_purpose_of` |
| 10 | "Such controllers or processors shall make binding and enforceable commitments...to apply those appropriate safeguards..." | FITS — `performs` |
| 11 | "the existence of the right to request from the controller access to and rectification..." | OUT OF SCOPE — fragment naming a right, not a resolvable act |
| 12 | "a process for regularly testing, assessing and evaluating the effectiveness of technical and organisational measures..." | FITS — `part_of` |
| 13 | "The Member States, the supervisory authorities, the Board and the Commission shall encourage...for the purpose of demonstrating compliance..." | FITS — `compliance_purpose_of` |
| 14 | "where the processing is based on point (f) of Article 6(1), the legitimate interests pursued..." | FITS — `based_on` + `cross_references` |
| 15 | "...assists the controller...for the fulfilment of the controller's obligation to respond to requests..." | FITS — `compliance_purpose_of` |

FITS 12/15; OUT OF SCOPE 3/15; FORCED-BY-DESIGN 0/15; CORRECT-DEFAULT
0/15; FORCED-BY-GAP 0/15. **Main-relation predication: 0/12 = 0%.
Forced-by-gap: 0/12 = 0%.**

### AI Act (of 1,271 sentences)

| # | Sentence (abbreviated) | Classification |
|---|---|---|
| 1 | "Providers of general-purpose AI models who do not adhere...shall demonstrate alternative adequate means of compliance for assessment by the Commission." | FITS — `requires` + `compliance_purpose_of` |
| 2 | "an accountability framework setting out the responsibilities of the management and other staff..." | FITS — `part_of` (swapped) |
| 3 | "National market surveillance authorities...should report, without delay, to the European Central Bank any information..." | FITS — `performs` (no enumerated-list/mandate wording, so not `competence_of`) |
| 4 | "Notified bodies shall be capable of carrying out all their tasks under this Regulation with the highest degree of professional integrity..." | CORRECT-DEFAULT — a general capability qualification, no single concrete act to extract |
| 5 | "The robustness of high-risk AI systems may be achieved through technical redundancy solutions, which may include backup or fail-safe plans." | FITS — `enables` + `part_of` (swapped) |
| 6 | "Notifying authorities shall be organised in such a way that decisions...are taken by competent persons different from those who carried out the assessment..." | FORCED-BY-GAP — a separation-of-duties constraint between two role-sets; no predicate, including `performs`, names the distinctness relation itself |
| 7 | "The three-month period...shall be reduced to 30 days in the event of non-compliance..." | FITS — `requires` + `deadline_of` + `cross_references` |
| 8 | "An advisory forum shall be established to provide technical expertise and advise the Board..." | FITS — `compliance_purpose_of` |
| 9 | "fostering innovation and competitiveness and facilitating the development of an AI ecosystem;" | FITS — `compliance_purpose_of` (via chapeau) |
| 10 | "to intervene in the operation of the high-risk AI system or interrupt the system through a 'stop' button..." | FITS — `enables` |
| 11 | "Notified bodies shall safeguard the confidentiality of the information...in accordance with Article 78." | FITS — `performs` + `cross_references` |
| 12 | "there are effective monitoring mechanisms to identify if any high risks...may arise...as referred to in Article 35...and Article 39..." | FITS — `enables` + `cross_references` |
| 13 | "systems and procedures for data management, including data acquisition...performed before and for the purpose of the placing on the market..." | FITS — `part_of` (swapped) + `precedes` + `compliance_purpose_of` |
| 14 | "Where the Member State fails to take the necessary corrective measures, the Commission may...suspend, restrict or withdraw the designation." | FITS — `requires` |
| 15 | "When adopting delegated acts pursuant to the first subparagraph...the requirements...shall be taken into account." | FITS — `requires` + `cross_references` |

FITS 12/15; OUT OF SCOPE 0/15; FORCED-BY-DESIGN 0/15; CORRECT-DEFAULT
1/15; FORCED-BY-GAP 1/15. **Main-relation predication: 2/15 = 13.3%.
Forced-by-gap: 1/15 = 6.7%.**

## Result

| Sample | Main-relation predication | Forced-by-gap |
|---|---|---|
| A, GDPR (seed 20261005) | 1/13 = 7.7% | 0/13 = 0% |
| A, AI Act (seed 20261005) | 2/13 = 15.4% | 0/13 = 0% |
| B, GDPR (seed 91817) | 0/12 = 0% | 0/12 = 0% |
| B, AI Act (seed 91817) | 2/15 = 13.3% | 1/15 = 6.7% |

Adding `performs` (an actor performing a non-deontic act, restricted away
from `competence_of`'s own institutional-mandate cases) resolves every
actor→act clause that was previously forced into `predication` for lack
of a predicate, across both samples, with one exception that is not an
actor→act clause at all: Sample B AI Act item 6, a separation-of-duties
constraint between two role-sets, which no predicate in this enum names
and which is reported here as a genuine residual (forced-by-gap
1/15 = 6.7% on that one sample) rather than resolved by stretching
`performs` to cover it. `competence_of` is restricted to an institutional
actor named in an enumerated task/power list or explicit competence/
mandate wording — several FITS classifications above are marked "weak"
(a plausible but contestable reading of a loosely worded basis or cause
clause); none of them is load-bearing for either sample's own
forced-by-gap result.
