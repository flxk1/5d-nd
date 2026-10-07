# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""The typed STATEMENT node — spec/SPEC.md §21 (typed-triple layer).

A Statement is a reified edge for the typed-path layer: unlike §11's plain
triple (``s, p, o, dimension, weight, provenance``), a Statement carries a
STABLE, content-addressed id, a CLOSED versioned predicate enum (one
dimension per predicate, never guessed), a SEPARATE edge_confidence (how
strongly the text supports the asserted edge — distinct from ``weight``,
§3's multiplicative path quantity), a provenance SPAN (start, end — not an
opaque value, §4's own span-grounding), a three-state NEGATION field
reusing §18's own present/uncertain/absent machinery, and a ``layer`` (one
of surface/domain/deep — the layer tensor is computed from triples,
not from Statements directly). ``extraction_rule_id`` is OPTIONAL and MUST be
absent (or null) for a GOLD statement — a hand- or model-coded Statement
with no owning extraction rule to name.

The codebook and gold come FIRST; this module has NO extractor of its
own. It validates and canonically orders an ALREADY-PRODUCED Statement
document; it does not produce one from free text.

Stdlib only.
"""
from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any, Optional

from .dimensions import Dimension
from .point import point_from_contributions
from .position import DIMENSIONS as _ALL_DIMENSIONS
from .position import is_dimension

__all__ = [
    "PREDICATE_VOCABULARY_VERSION",
    "PREDICATE_DIMENSION",
    "ACTOR_VOCABULARY_VERSION",
    "ACTOR_ROLES",
    "ACTOR_OTHER_RE",
    "INSTITUTIONAL_ACTOR_ROLES",
    "NEGATION_STATES",
    "LAYER_STATES",
    "ID_HASH_HEX_LENGTH",
    "ID_SHAPE_RE",
    "is_known_predicate",
    "predicate_dimension",
    "is_known_actor",
    "statement_violations",
    "is_valid_statement",
    "canonical_sort_key",
    "sort_statements",
    "normalize_statement_text",
    "text_hash",
    "statement_id",
    "dual_split_violations",
    "is_valid_dual_split",
    "raw_contributions",
    "layer_tensor",
]

# ── §21 predicate enum — byte-identical to vocabulary/statement-predicates.json.
# v3.1 clarifies the except_when/applies_to/requires ("subject to") and
# competence_of/performs ("confers" vs "exercises") routing tests in the
# predicate definitions' own text; v3.2 adds the "responsible for" rule to
# competence_of's own definition text (a finite assigning clause confers,
# a reduced relative that merely identifies the actor does not); v3.3 adds,
# from a separate blind re-pilot's own shared wrong/arguable answers: no
# modal verb inside an endpoint span (requires), a power is never an
# endpoint whether conferred or not (competence_of, performs), negation
# scope for a conditional deadline (requires, deadline_of), and "part of"
# is not a determiner to strip (part_of); v3.4 corrects v3.3's own R-n
# (a negator confined to a requires Statement's own antecedent stays
# INSIDE the subj span and never makes negation "present" on its own —
# requires, deadline_of), refines the power-as-never-an-endpoint
# rationale and holder-inheritance rule (competence_of, performs), adds
# "form(s) part of" as a part_of verb cue, and pins "references to X
# include Y" to applies_to specifically — Y falls within the scope of
# the term X, never is_a, never part_of (part_of, applies_to). The
# predicate set and PREDICATE_DIMENSION mapping are UNCHANGED from v3.
PREDICATE_VOCABULARY_VERSION = "typed-statements-v3.5"

PREDICATE_DIMENSION: dict = {
    "is_a": Dimension.STRUCTURAL.value,
    "part_of": Dimension.STRUCTURAL.value,
    "applies_to": Dimension.STRUCTURAL.value,
    "cross_references": Dimension.STRUCTURAL.value,
    "except_when": Dimension.STRUCTURAL.value,
    "enables": Dimension.CAUSAL.value,
    "requires": Dimension.CAUSAL.value,
    "legislative_purpose_of": Dimension.INTENTIONAL.value,
    "compliance_purpose_of": Dimension.INTENTIONAL.value,
    "based_on": Dimension.INTENTIONAL.value,
    "precedes": Dimension.TEMPORAL.value,
    "deadline_of": Dimension.TEMPORAL.value,
    "predication": Dimension.RELATIONAL.value,
    "competence_of": Dimension.RELATIONAL.value,
    "performs": Dimension.RELATIONAL.value,
}

# ── §21 entity/actor vocabulary — byte-identical to vocabulary/actor-roles.json
ACTOR_VOCABULARY_VERSION = "typed-statements-v3"

ACTOR_ROLES: frozenset = frozenset({
    "controller", "joint_controller", "processor", "sub_processor",
    "provider", "deployer", "importer", "distributor",
    "authorised_representative", "data_subject",
    "data_protection_officer", "supervisory_authority", "notified_body",
    "market_surveillance_authority", "commission", "member_state",
    "european_data_protection_board", "ai_office", "third_party",
    "recipient", "operator",
    # DSA/NIS2 roles (added to the closed vocabulary before the freeze).
    "competent_authority", "digital_services_coordinator", "csirt",
    "essential_entity", "important_entity", "provider_of_online_platform",
    "very_large_online_platform",
})

# The subset of ACTOR_ROLES that is an INSTITUTIONAL body (an authority, a
# board, an office) rather than a regulated private or individual actor —
# the cue test `competence_of` is restricted to (docs/codebook/
# typed-statements-v1.md's own "competence_of vs performs" rule). An actor
# OUTSIDE this set performing an act uses `performs`, never `competence_of`.
INSTITUTIONAL_ACTOR_ROLES: frozenset = frozenset({
    "supervisory_authority", "notified_body", "market_surveillance_authority",
    "commission", "member_state", "european_data_protection_board", "ai_office",
    "competent_authority", "digital_services_coordinator", "csirt",
})

ACTOR_OTHER_RE = re.compile(r"^other\([^()]+\)$")

# ── §21 negation — reuses §18's three-state machinery (present / uncertain /
# absent), applied to the STATEMENT's own relation rather than to a
# requirement-grammar concept.
NEGATION_STATES: frozenset = frozenset({"present", "uncertain", "absent"})

# ── §21 layer — surface / domain / deep. The coding rule (text position and
# function, independent of predicate) is docs/codebook/typed-statements-v1.md's
# own "Layer" section. The layer tensor is computed from triples, not
# from Statements directly; the layer rules themselves are a codebook/spec choice.
LAYER_STATES: frozenset = frozenset({"surface", "domain", "deep"})

# ── §21 id shape, pinned. An id is
# <instrument_uri>#<consolidation_date>#<text_hash>, where <text_hash> is
# the lowercase hex sha256 digest of normalize_statement_text()'s own
# output, truncated to ID_HASH_HEX_LENGTH hex digits (:func:`text_hash`).
# The validator checks this exact shape, including the hash segment's own
# length and alphabet — it does not, and cannot, recompute the hash itself
# (that needs the caller's own source text).
ID_HASH_HEX_LENGTH = 16
ID_SHAPE_RE = re.compile(
    r"^[^#]+#[^#]+#[0-9a-f]{%d}$" % ID_HASH_HEX_LENGTH
)


def is_known_predicate(predicate: Any) -> bool:
    """True iff ``predicate`` is a member of the CLOSED §21 enum."""
    return isinstance(predicate, str) and predicate in PREDICATE_DIMENSION


def predicate_dimension(predicate: str) -> str:
    """The ONE dimension §21's closed enum assigns ``predicate``.

    Raises ``KeyError`` on an unknown predicate — this module never guesses
    (that is an nD grammar's own ``binding`` concern, §9; this enum is 5D's
    own closed typed-statement vocabulary).
    """
    return PREDICATE_DIMENSION[predicate]


def is_known_actor(value: Any) -> bool:
    """True iff ``value`` names a closed §21 actor role, or matches the
    documented ``other(label)`` escape (a non-empty label, no nested
    parentheses)."""
    if not isinstance(value, str) or not value:
        return False
    return value in ACTOR_ROLES or bool(ACTOR_OTHER_RE.match(value))


def _is_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def statement_violations(doc: Any) -> list:
    """Violations of a Statement's shape (§21). Fail-closed: returns ``[]``
    only when every field below is present and well-typed.

    Required: ``id`` (non-empty string, matching the pinned 3-part shape
    ``ID_SHAPE_RE``, including a 16-hex-digit lowercase hash segment),
    ``subj``/``obj`` (non-empty string — a unit or entity id, §21's own
    unitisation rules), ``predicate`` (one of §21's closed enum),
    ``dimension`` (one of the five, §2, and MUST equal
    ``predicate_dimension(predicate)`` — a Statement's own dimension is
    NEVER independent of its predicate), ``layer`` (one of
    surface/domain/deep), ``weight`` (a JSON number, never a boolean,
    FINITE, in [0, 1] — §3's multiplicative range; defaults to 1.0 when
    absent, same convention as §11's plain triple), ``edge_confidence`` (a
    JSON number in [0, 1] — SEPARATE from ``weight``; REQUIRED, never
    defaulted, because unlike ``weight`` it has no composition-algebra
    identity to fall back on), ``provenance`` (a mapping with integer
    ``start``/``end``, ``0 <= start < end``), ``negation`` (one of
    present/uncertain/absent, §18's machinery). ``extraction_rule_id`` is
    OPTIONAL; when present it MUST be a non-empty string OR explicitly
    ``null`` (the gold convention: a gold Statement names no extraction
    rule).
    """
    if not isinstance(doc, Mapping):
        return ["statement must be a mapping"]
    out: list = []

    for field in ("id", "subj", "obj"):
        value = doc.get(field)
        if not isinstance(value, str) or not value:
            out.append(f"statement field {field!r} must be a non-empty string, got {value!r}")
    statement_id_value = doc.get("id")
    if isinstance(statement_id_value, str) and statement_id_value:
        if not ID_SHAPE_RE.match(statement_id_value):
            out.append(
                "statement 'id' must have exactly three non-empty '#'-separated segments, "
                f"the third a {ID_HASH_HEX_LENGTH}-digit lowercase hex hash "
                f"(<instrument_uri>#<consolidation_date>#<hash>), got {statement_id_value!r}"
            )

    predicate = doc.get("predicate")
    if not isinstance(predicate, str) or not predicate:
        out.append(f"statement 'predicate' must be a non-empty string, got {predicate!r}")
    elif not is_known_predicate(predicate):
        out.append(
            f"statement predicate {predicate!r} is not in the closed §21 enum "
            f"({PREDICATE_VOCABULARY_VERSION})"
        )

    dimension = doc.get("dimension")
    if "dimension" not in doc or dimension in (None, ""):
        out.append("statement carries no dimension; a statement MUST carry exactly one (§21)")
    elif not is_dimension(dimension):
        out.append(f"statement dimension {dimension!r} is not one of the five")
    elif is_known_predicate(predicate) and dimension != predicate_dimension(predicate):
        out.append(
            f"statement dimension {dimension!r} disagrees with predicate {predicate!r}'s "
            f"own closed-enum dimension {predicate_dimension(predicate)!r}"
        )

    layer = doc.get("layer")
    if layer not in LAYER_STATES:
        out.append(f"statement 'layer' must be one of {sorted(LAYER_STATES)}, got {layer!r}")

    weight = doc.get("weight", 1.0)
    if isinstance(weight, bool) or not _is_number(weight):
        out.append(f"statement weight must be a finite number, got {weight!r}")
    elif not (0.0 <= float(weight) <= 1.0):
        out.append(f"statement weight must be in [0, 1], got {weight!r}")

    if "edge_confidence" not in doc:
        out.append("statement has no edge_confidence (REQUIRED, separate from weight — §21)")
    else:
        conf = doc["edge_confidence"]
        if isinstance(conf, bool) or not _is_number(conf):
            out.append(f"statement edge_confidence must be a finite number, got {conf!r}")
        elif not (0.0 <= float(conf) <= 1.0):
            out.append(f"statement edge_confidence must be in [0, 1], got {conf!r}")

    provenance = doc.get("provenance")
    if not isinstance(provenance, Mapping):
        out.append(f"statement 'provenance' must be a mapping with start/end, got {provenance!r}")
    else:
        start, end = provenance.get("start"), provenance.get("end")
        start_ok = isinstance(start, int) and not isinstance(start, bool)
        end_ok = isinstance(end, int) and not isinstance(end, bool)
        start_nonneg = start_ok and start >= 0
        if not start_ok:
            out.append(f"statement provenance.start must be an integer, got {start!r}")
        elif not start_nonneg:
            out.append(f"statement provenance.start must be >= 0, got {start!r}")
        if not end_ok:
            out.append(f"statement provenance.end must be an integer, got {end!r}")
        # The span check only fires when start/end are ALREADY well-typed and
        # start is already non-negative — each of the three checks above is
        # therefore mutually exclusive with this one for any single malformed
        # field, so one malformed field produces exactly one violation here,
        # never two overlapping messages for the same root cause.
        if start_nonneg and end_ok and not (start < end):
            out.append(f"statement provenance span must satisfy 0 <= start < end, got {start}, {end}")

    negation = doc.get("negation")
    if negation not in NEGATION_STATES:
        out.append(f"statement 'negation' must be one of {sorted(NEGATION_STATES)}, got {negation!r}")

    if "extraction_rule_id" in doc:
        rule_id = doc["extraction_rule_id"]
        if rule_id is not None and (not isinstance(rule_id, str) or not rule_id):
            out.append(
                f"statement 'extraction_rule_id' must be null or a non-empty string, got {rule_id!r}"
            )

    return out


def is_valid_statement(doc: Any) -> bool:
    return statement_violations(doc) == []


def canonical_sort_key(statement: Mapping) -> tuple:
    """The §21 canonical sort key: ``(dimension, subj, pred, obj, span)``.

    ``span`` is the ``(start, end)`` pair from ``provenance`` — compared as
    a tuple of ints (so ``2`` sorts before ``10``) and INCLUDED in the key
    (two statements that agree on dimension/subj/pred/obj but not on their
    own span are NOT interchangeable for sort purposes). A statement
    missing one of these fields sorts last among its peers at that field's
    own position (an ordinary ``statement_violations()`` failure is the
    right way to catch a missing field; this key is for an ALREADY-VALID
    statement's canonical ORDER, not a second validity gate).
    """
    provenance = statement.get("provenance") or {}
    span = (provenance.get("start", 0), provenance.get("end", 0))
    return (
        statement.get("dimension", ""),
        statement.get("subj", ""),
        statement.get("predicate", ""),
        statement.get("obj", ""),
        span,
    )


def sort_statements(statements: Sequence[Mapping]) -> list:
    """Return ``statements`` in §21's canonical order — a NEW list, never a
    mutation of the input."""
    return sorted(statements, key=canonical_sort_key)


def normalize_statement_text(text: str) -> str:
    """Pin the text normalisation a Statement id's own hash is computed
    over: Unicode NFC, every U+00A0 (non-breaking space — present in both
    the GDPR's and the AI Act's own source text) replaced with an
    ordinary U+0020 space, then every run of ASCII whitespace
    (space/tab/newline/CR/form-feed/vertical-tab) collapsed to one space,
    stripped at both ends. The whitespace-collapse step is deliberately
    ASCII-only (never Python's Unicode-aware ``\\s``, which already
    treats U+00A0 as whitespace on its own) — the NBSP step and the
    collapse step are each independently load-bearing and independently
    testable; neither one's removal is masked by the other.

    No case-folding, and no compatibility (NFKC/NFKD) decomposition: this
    is a WHITESPACE/encoding normalisation only, never a semantic one —
    "Controller" and "controller" hash differently, by design.
    """
    t = unicodedata.normalize("NFC", text)
    t = t.replace(" ", " ")
    t = re.sub(r"[ \t\n\r\f\v]+", " ", t).strip()
    return t


def text_hash(normalized_text: str) -> str:
    """The pinned §21 id hash: lowercase hex sha256 of ``normalized_text``
    (already run through :func:`normalize_statement_text` by the caller —
    this function does not normalise its own input), truncated to
    :data:`ID_HASH_HEX_LENGTH` (16) hex digits. Two callers hashing the
    SAME normalized text MUST produce the SAME id segment; this is the one
    algorithm every conformant implementation reproduces.
    """
    return hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()[:ID_HASH_HEX_LENGTH]


def statement_id(instrument_uri: str, consolidation_date: str, hash_segment: str) -> str:
    """Build a §21 Statement id: the stable instrument URI (ELI where one
    exists), the consolidation date, and :func:`text_hash`'s own output,
    joined by ``#`` — stable across a clause-offset renumbering (a
    corrigendum, a re-consolidation) that would break a bare
    article+offset id. Raises ``ValueError`` if any segment is empty,
    contains ``#``, or if ``hash_segment`` does not match the pinned
    16-hex-digit lowercase shape — this function cannot build an id its
    own validator (``ID_SHAPE_RE``) would then reject.
    """
    for name, value in (
        ("instrument_uri", instrument_uri),
        ("consolidation_date", consolidation_date),
        ("hash_segment", hash_segment),
    ):
        if not isinstance(value, str) or not value:
            raise ValueError(f"statement_id() requires a non-empty {name}")
        if "#" in value:
            raise ValueError(f"statement_id() requires {name} to contain no '#', got {value!r}")
    if not re.match(r"^[0-9a-f]{%d}$" % ID_HASH_HEX_LENGTH, hash_segment):
        raise ValueError(
            f"statement_id() requires hash_segment to be {ID_HASH_HEX_LENGTH} lowercase hex "
            f"digits, got {hash_segment!r}"
        )
    return f"{instrument_uri}#{consolidation_date}#{hash_segment}"


def dual_split_violations(causal: Any, intentional: Any) -> list:
    """Violations of §21's dual-coded-split ANNOTATION rule: one clause →
    a causal Statement + an intentional Statement SHARING THE MIDDLE
    SEGMENT, as a codebook rule, never grammar precedence.

    The shared middle segment is the causal statement's OBJECT and the
    intentional statement's SUBJECT: ``A --causal--> B --intentional-->
    C`` from a single clause, so ``causal.obj == intentional.subj``. Both
    statements MUST individually validate (§21), MUST carry their own
    dimension pair (causal / intentional, in that role — this function
    does not accept the pair reversed, since the chain's own direction is
    causal-then-intentional), and their provenance spans MUST be adjacent
    or overlapping (never disjoint — a dual split describes ONE clause,
    not two unrelated ones).
    """
    out: list = []
    c_errs = statement_violations(causal)
    i_errs = statement_violations(intentional)
    out.extend(f"causal statement: {e}" for e in c_errs)
    out.extend(f"intentional statement: {e}" for e in i_errs)
    if c_errs or i_errs:
        return out

    if causal.get("dimension") != Dimension.CAUSAL.value:
        out.append("dual split's first statement must be dimension 'causal'")
    if intentional.get("dimension") != Dimension.INTENTIONAL.value:
        out.append("dual split's second statement must be dimension 'intentional'")
    if causal.get("obj") != intentional.get("subj"):
        out.append(
            "dual split requires a SHARED MIDDLE SEGMENT: "
            f"causal.obj ({causal.get('obj')!r}) must equal intentional.subj "
            f"({intentional.get('subj')!r})"
        )

    c_prov, i_prov = causal.get("provenance", {}), intentional.get("provenance", {})
    c_start, c_end = c_prov.get("start"), c_prov.get("end")
    i_start, i_end = i_prov.get("start"), i_prov.get("end")
    if None not in (c_start, c_end, i_start, i_end):
        # Adjacent or overlapping: neither span is strictly before the other
        # with a gap, i.e. the two spans together describe ONE clause.
        if c_end < i_start or i_end < c_start:
            out.append(
                "dual split's two provenance spans are disjoint (a gap between them); "
                "they must come from the SAME clause"
            )
    return out


def is_valid_dual_split(causal: Any, intentional: Any) -> bool:
    return dual_split_violations(causal, intentional) == []


def raw_contributions(
    statements: Sequence[Mapping], entry_id: str, *, layer: Optional[str] = None
) -> dict:
    """The raw §11 contribution vector for ``entry_id``, DERIVED from
    ``statements`` — never hand-typed.

    For every statement in ``statements`` that names ``entry_id`` as its
    ``subj`` OR its ``obj`` (and, when ``layer`` is given, whose own
    ``layer`` field equals it), this adds ``+1`` to the statement's own
    ``dimension`` — §5's rule 1, applied to a §21 Statement exactly as it
    is already applied to an nD claim. A statement that does not itself
    validate (§21) is SKIPPED, never counted (fail-closed: malformed input
    contributes nothing rather than an undefined amount).
    """
    out = {d: 0 for d in _ALL_DIMENSIONS}
    for s in statements:
        if not is_valid_statement(s):
            continue
        if layer is not None and s.get("layer") != layer:
            continue
        if s.get("subj") == entry_id or s.get("obj") == entry_id:
            out[s["dimension"]] += 1
    return out


def layer_tensor(statements: Sequence[Mapping], entry_id: str) -> dict:
    """The 3×5 triple tensor for ``entry_id``, computed from triples: each
    of the three layers (surface/domain/deep) is the UNCHANGED §11
    ``point_from_contributions`` formula, applied to the raw contributions
    of ONLY that layer's own Statements naming ``entry_id``
    (:func:`raw_contributions` with ``layer`` set) — this function
    introduces no new point formula of its own; it supplies §11's existing
    one with a layer-filtered raw vector, three times.

    Returns ``{"surface": <point>, "domain": <point>, "deep": <point>}``.
    A layer with zero matching Statements gets the all-zero point (§11's
    own "no special branch needed" rule) — never an error, and never
    confused with a populated layer (distinguishable by cosine's own
    degenerate-zero-norm rule, §11).
    """
    return {
        layer: point_from_contributions(raw_contributions(statements, entry_id, layer=layer))
        for layer in sorted(LAYER_STATES)
    }
