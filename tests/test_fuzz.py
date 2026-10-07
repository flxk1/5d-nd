# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""A deterministic, seeded, MUTATION-based fuzz over NDSystem
documents, grammar descriptors (interchange AND runtime form), and links.

Every generated case starts from a KNOWN-VALID baseline document (verified
by hand against the real reference validator AND real versum before this
file was written — see the three ``_VALID_*`` constants below) and mutates
1-3 keys per case, drawn from a tagged pool of mutation operators (type
swaps, unhashables, falsy values, empty containers, wrapper forms, and
BENIGN mutations that keep the document valid). This gives a healthy
fraction of still-valid cases (asserted >= 25%, not merely hoped for) WHILE
still exercising the same crash surface the previous, from-scratch-garbage
fuzz covered — a mutation of a valid document reaches the SAME code paths
(and more reliably triggers the ones that only fire once the rest of the
document is otherwise coherent, e.g. ``nd_system.validation.unknown_values``
checks that never run at all if ``nd_system`` itself is already malformed).

Stdlib ``random`` only, fixed seed — no new dependency, fully reproducible.
Encodes spec/SPEC.md §9's validator parity policy (P1-P3) directly:

  - **P1** (hard, no exceptions): if versum rejects a (normalised) document,
    the code MUST reject it too. A code-accepts/versum-rejects disagreement
    FAILS the test unconditionally.
  - **P2/P3** (documented, PER FIELD): if versum (or code, for the schema
    leg) accepts a document but the stricter side rejects it, that is
    allowed ONLY when EVERY violation the stricter side reports is located
    at a field :func:`_malformed_nd_system_fields`/
    :func:`_malformed_descriptor_fields` (this file's own implementation of
    §9's EXPLICIT field-type table) classifies as
    malformed. This REPLACES an earlier WHOLE-DOCUMENT
    boolean classifier (``_is_malformed_nd_system_shape``) that the
    review proved could MASK a real bug — if ANY field anywhere in the
    document was malformed, EVERY divergence in that document was excused,
    including one at a completely different, well-formed field. The
    per-field set, matched against the stricter side's OWN violation
    paths (``nd_system_violations_with_paths()``/
    ``descriptor_violations_with_paths()`` for P2; a jsonschema error's
    own ``absolute_path`` for P3), closes that gap: a divergence is excused
    only when it is PROVABLY located at a field §9's own table
    actually declares malformed, never merely "somewhere in a document
    that also happens to have a malformed field elsewhere".
  - Also asserts (independent of P1-P3): no ``*_violations``/``is_valid_*``
    function in ``five_d_nd.contract`` ever raises, on ANY generated case.

A separate, DETERMINISTIC regression test
(``test_ontology_falsy_values_stay_valid_regression_guard``) pins the
"ontology falsy value" fix directly, independent of the stochastic
mutation draw — see that test's own docstring for the mutation-testing
proof that it actually catches a reversion of that fix.

Run directly (``pytest tests/test_fuzz.py -v``) to reproduce any failure;
the seed and per-category case count are both named constants below, so a
failure is always reproducible from this file alone. Keeps the whole file
well under ~20s even with the versum differential enabled.
"""
from __future__ import annotations

import copy
import json
import random
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from five_d_nd import contract

try:
    from versum.nd import NDSystem as _VersumNDSystem
    from versum.planes import (
        DescriptorPlane as _VersumDescriptorPlane,
        PlaneDescriptorError as _VersumPlaneDescriptorError,
    )
    _VERSUM_AVAILABLE = True
except ImportError:
    _VERSUM_AVAILABLE = False

try:
    import jsonschema
    _JSONSCHEMA_AVAILABLE = True
except ImportError:
    _JSONSCHEMA_AVAILABLE = False

# Fixed seed: every run of this file generates EXACTLY the same cases.
_SEED = 20261010
# Per-category case counts; comfortably over 2000 total with margin.
_N_ND_SYSTEM = 700
_N_DESCRIPTOR = 700
_N_LINK = 650
_MIN_VALID_FRACTION = 0.25

_SCHEMA_DIR = Path(__file__).resolve().parents[1] / "schema"
_ND_SYSTEM_SCHEMA = None


def _nd_system_schema_error_paths(doc: Any) -> list:
    """The DOTTED field paths (e.g. ``"axes.a.vocabulary"``) jsonschema's
    own errors report for ``doc`` against nd-system.schema.json — built
    from each error's own ``absolute_path`` (a deque of key/index
    segments), joined the SAME way this file's own violation paths are
    (the P3 leg: a schema rejection is excused only when
    EVERY one of these paths is itself malformed, via
    :func:`_paths_all_malformed`)."""
    global _ND_SYSTEM_SCHEMA
    if _ND_SYSTEM_SCHEMA is None:
        _ND_SYSTEM_SCHEMA = json.loads(
            (_SCHEMA_DIR / "nd-system.schema.json").read_text(encoding="utf-8"))
    validator_cls = jsonschema.validators.validator_for(_ND_SYSTEM_SCHEMA)
    validator = validator_cls(_ND_SYSTEM_SCHEMA)
    return [".".join(str(seg) for seg in error.absolute_path)
            for error in validator.iter_errors(doc)]


def _versum_nd_system_valid(doc: Any) -> bool:
    try:
        _VersumNDSystem.from_dict(doc).validate()
        return True
    except (ValueError, TypeError, AttributeError, KeyError):
        return False


def _versum_descriptor_valid(doc: Any) -> bool:
    if not isinstance(doc, Mapping):
        return False
    payload = dict(doc)
    payload.setdefault("produce", lambda *a, **k: [])
    try:
        _VersumDescriptorPlane.from_descriptor(payload)
        return True
    except _VersumPlaneDescriptorError:
        return False
    except (ValueError, TypeError, KeyError, AttributeError):
        return False


# ── §9's EXPLICIT field-type table, as code ─────────
# spec/SPEC.md §9's own field table: each of these has a PRECISE
# declared type, no longer inferred from "does the table annotate an
# alternate shape" — the decision was the types directly, so the classifier
# below just checks a value's JSON kind against that explicit table,
# field by field, returning the SET of malformed field paths rather than a
# single whole-document bool — see this module's own
# docstring for why the whole-document bool was a masking bug).

def _malformed_nd_system_fields(root: Any) -> frozenset:
    """The set of field paths (e.g. ``"version"``, ``"axes.a.vocabulary"``,
    ``"bindings"``) where ``root`` (an UNWRAPPED NDSystem root mapping)
    carries a malformed shape, per §9's explicit field-type table:

      * ``id``, ``namespace``: STRING ONLY.
      * ``version``: STRING, or a NUMBER (``int``/``float``, NEVER
        ``bool`` — a JSON boolean is its own type) via str() coercion;
        ``null``, an array, and an object are all malformed too.
      * ``ontology_relations``: ARRAY ONLY (a non-array iterable — a
        string, a dict, a set — is malformed, not only a non-iterable).
      * ``bindings``: ARRAY ONLY.
      * ``axes.<id>.vocabulary``: a JSON scalar, an array of JSON scalars
        (string/number/boolean), or null — a ``null``/array/object ITEM
        inside the array is malformed, and so is an object vocabulary
        itself.
      * ``axes.<id>.ontology``: a mapping, or any JSON-falsy value; a
        TRUTHY non-mapping is malformed EVEN WHEN versum's own
        ``ontology_id or ontology.get("id")``-style short-circuit happens
        to accept it because the flat ``ontology_id``/``ontology_version``
        are both already present — the field's own
        declared type does not change because of what some OTHER field
        happens to contain.

    This is NOT a generic "something about this shape looks wrong"
    classifier — an ORDINARY violation (an unknown enum value, a bad
    pattern, a missing axis, a closed vocabulary that is merely empty) is
    never malformed and MUST produce the identical verdict on both sides;
    only the EXPLICIT shapes above are classified here.
    """
    malformed = set()
    if not isinstance(root, Mapping):
        return frozenset(malformed)
    for label in ("id", "namespace"):
        if label in root and not isinstance(root[label], str):
            malformed.add(label)
    if "version" in root:
        version_raw = root["version"]
        if isinstance(version_raw, bool) or not isinstance(version_raw, (str, int, float)):
            malformed.add("version")
    if "ontology_relations" in root and not isinstance(root["ontology_relations"], (list, tuple)):
        malformed.add("ontology_relations")
    if "bindings" in root and not isinstance(root["bindings"], (list, tuple)):
        malformed.add("bindings")
    axes = root.get("axes")
    if isinstance(axes, Mapping):
        for axis_id, axis in axes.items():
            if not isinstance(axis, Mapping):
                continue
            prefix = f"axes.{axis_id}."
            vocabulary = axis.get("vocabulary")
            if isinstance(vocabulary, Mapping):
                malformed.add(prefix + "vocabulary")
            elif isinstance(vocabulary, (list, tuple)):
                if any(item is None or isinstance(item, (list, tuple, Mapping))
                       for item in vocabulary):
                    malformed.add(prefix + "vocabulary")
            ontology = axis.get("ontology")
            if ontology and not isinstance(ontology, Mapping):
                # versum's own `ontology_id = str(raw.get(
                # "ontology_id") or ontology.get("id") or "")` (same pattern
                # for ontology_version) SHORT-CIRCUITS: when the FLAT
                # ontology_id/ontology_version are both already truthy,
                # `ontology.get(...)` is NEVER EVEN CALLED, so versum
                # accepts a truthy non-mapping "ontology" there even though
                # the SAME value would crash it the moment either flat
                # field is absent. "ontology" is still declared type
                # "object" regardless — a truthy non-mapping remains
                # malformed at THIS field no matter what a sibling field
                # contains, so this is unconditional (not gated on the
                # flat fields being present, unlike the old whole-document
                # classifier which only needed ONE malformed field
                # anywhere to excuse everything).
                malformed.add(prefix + "ontology")
    return frozenset(malformed)


def _malformed_descriptor_fields(doc: Any) -> frozenset:
    """Same as :func:`_malformed_nd_system_fields`, applied to a
    descriptor's own ``nd_system`` field (unwrapped the same way
    ``descriptor_violations()`` itself does), with each path prefixed
    ``"nd_system."`` — the same rule applies to
    descriptors with the unwrapped nd_system paths."""
    if not isinstance(doc, Mapping):
        return frozenset()
    nd_system = doc.get("nd_system")
    if not isinstance(nd_system, Mapping):
        return frozenset()
    inner = nd_system.get("nd_system")
    root = inner if isinstance(inner, Mapping) else nd_system
    return frozenset(f"nd_system.{path}" for path in _malformed_nd_system_fields(root))


def _unwrap_nd_system_path(path: str, *, was_wrapped: bool) -> str:
    """jsonschema's own ``absolute_path`` for a WRAPPER-form nd_system doc
    (``{"nd_system": {...}}``) includes the leading ``"nd_system"`` segment
    (the instance location it actually validated), but
    :func:`_malformed_nd_system_fields` always operates on the UNWRAPPED
    root and so never has that prefix — strip it here so both path
    vocabularies line up before comparing (only when the doc given to the
    schema really WAS wrapper-form; an un-wrapped doc's paths are already
    bare)."""
    if was_wrapped and path == "nd_system":
        return ""
    if was_wrapped and path.startswith("nd_system."):
        return path[len("nd_system."):]
    return path


def _path_covers(path: str, malformed_field: str) -> bool:
    """True iff ``path`` and ``malformed_field`` name the SAME field, or
    one is an ancestor of the other on the same dotted branch (e.g.
    ``"axes.a"`` covers ``"axes.a.vocabulary"`` and vice versa) — needed
    because jsonschema's own error reporting for an ``anyOf``/``allOf``
    branch sometimes reports its ``absolute_path`` at a COARSER level
    than the leaf field itself (e.g. ``"axes.a"`` instead of
    ``"axes.a.vocabulary"`` when several sibling sub-schema candidates at
    that axis all fail together) — this module's own violation paths
    (from ``nd_system_violations_with_paths()``) are always leaf-precise,
    so the ancestor/descendant check only ever WIDENS what a schema error
    can match, never a code violation."""
    if path == malformed_field:
        return True
    return (malformed_field.startswith(path + ".")
            or path.startswith(malformed_field + "."))


def _paths_all_malformed(paths, malformed_fields: frozenset) -> bool:
    """True iff EVERY path in ``paths`` (an iterable of dotted field-path
    strings, e.g. from ``nd_system_violations_with_paths()`` or a
    jsonschema error's own ``absolute_path``) is COVERED (see
    :func:`_path_covers`) by at least one member of ``malformed_fields`` —
    this is the actual masking fix: a P2/P3 divergence is excused
    ONLY when EVERY violation the stricter side reports is located at an
    explicitly malformed field, never merely because SOME field somewhere
    in the document happens to be malformed."""
    paths = list(paths)
    if not paths:
        return False
    return all(any(_path_covers(p, m) for m in malformed_fields) for p in paths)


# ── known-valid baselines (verified by hand against code AND real versum
#    before this file was written) ──────────────

_VALID_ND_SYSTEM = {
    "id": "loomground-test",
    "namespace": "loomground.test",
    "version": "1",
    "axes": {
        "operator": {
            "value_type": "controlled_identifier",
            "cardinality": "one",
            "vocabulary_mode": "closed",
            "vocabulary": ["O", "P", "F"],
        },
        "bearer": {
            "value_type": "concept_reference",
        },
    },
    "bindings": [
        {"form_slot": "operator", "allowed_axes": ["operator"], "required": True},
    ],
    "ontology_relations": [],
    "validation": {"unknown_values": "reject"},
}

_VALID_DESCRIPTOR = {
    "plane": "loomground-test",
    "language_version": "1",
    "nd_system": _VALID_ND_SYSTEM,
    "binding": {"obliges": "intentional"},
    "contract_version": contract.SPEC_VERSION,
    "examples": [{"sentence": "x", "expected": []}],
    "co_dimensions": ["operator"],
}

_VALID_LINK = {"dimension": "structural", "relation": "embeds"}


# ── mutation operators ───────────────────────────────────────────────────────
# Each operator mutates its document IN PLACE and returns nothing; some are
# "benign" (keep the document valid on both sides — a documented coercion,
# an equally-valid alternative, deleting an optional key) and some are
# "breaking" (an unhashable value, a non-iterable, a wrong JSON kind with no
# applicable coercion). Mixing both kinds in one pool, 1-3 draws per case,
# is what produces the required valid fraction without hand-tuning weights.

_UNHASHABLE = [[], {}, [1], {"a": 1}]
_FALSY_NON_MAPPING = [0, False, "", []]
_TRUTHY_NON_MAPPING = ["x", [1], True, 3]
_NON_ITERABLE = [None, True, 0, -1, 3.14]


def _ensure_axis(nd: dict) -> dict:
    """Return ``nd["axes"]["a"]`` as a mutable dict, FORCING both levels
    into shape first if an earlier mutator in the same case already
    clobbered "axes" into a non-mapping (e.g. set_axes_garbage ran first in
    this draw) — ``dict.setdefault`` alone cannot repair that, since the
    KEY is already present with the wrong type."""
    if not isinstance(nd.get("axes"), dict):
        nd["axes"] = {}
    if not isinstance(nd["axes"].get("a"), dict):
        nd["axes"]["a"] = {}
    return nd["axes"]["a"]


def _nd_system_mutators():
    def set_axes_garbage(rng, nd):
        nd["axes"] = rng.choice([[], "x", 1, None, {}])

    def set_axes_axis_unhashable_value_type(rng, nd):
        _ensure_axis(nd)["value_type"] = rng.choice(_UNHASHABLE)

    def set_bindings_non_list_malformed(rng, nd):
        nd["bindings"] = rng.choice(["ab", [1], {"a": 1}])

    def set_bindings_empty_non_list(rng, nd):
        # The specific P2 case: versum ACCEPTS these
        # (empty-iterable accident), the code deliberately still rejects.
        nd["bindings"] = rng.choice(["", {}])

    def set_bindings_allowed_axes_unhashable(rng, nd):
        nd["bindings"] = [{"form_slot": "s", "allowed_axes": [rng.choice(_UNHASHABLE)]}]

    def set_ontology_relations_non_iterable(rng, nd):
        nd["ontology_relations"] = rng.choice(_NON_ITERABLE)

    def set_ontology_relations_array_benign(rng, nd):
        # ARRAY ONLY — [] and ["a", "b"] are the
        # well-formed shapes; a non-array iterable ("x", {}) is now
        # malformed, see set_ontology_relations_non_array_iterable_malformed.
        nd["ontology_relations"] = rng.choice([[], ["a", "b"]])

    def set_validation_truthy_non_mapping(rng, nd):
        nd["validation"] = rng.choice(_TRUTHY_NON_MAPPING)

    def set_validation_falsy_benign(rng, nd):
        nd["validation"] = rng.choice(_FALSY_NON_MAPPING)

    def set_axis_ontology_truthy_non_mapping(rng, nd):
        _ensure_axis(nd)["ontology"] = rng.choice(_TRUTHY_NON_MAPPING)

    def set_axis_ontology_truthy_with_flat_fields_present_p2(rng, nd):
        # The specific short-circuit shape — a truthy
        # non-mapping "ontology" PLUS both flat ontology_id/ontology_version
        # already present and truthy. versum accepts this (its own `or`
        # never reaches ontology.get(...)); the code still rejects it
        # (ontology's own shape is checked unconditionally); classified
        # malformed by _malformed_nd_system_fields() above.
        axis = _ensure_axis(nd)
        axis["vocabulary_mode"] = "external"
        axis["ontology_id"] = "o"
        axis["ontology_version"] = "v"
        axis["ontology"] = rng.choice(_TRUTHY_NON_MAPPING)

    def set_axis_ontology_falsy_benign(rng, nd):
        # A regression case: must stay VALID on both sides. If
        # contract.py's guard regresses to "is not None and not Mapping",
        # this mutation starts making the code reject while versum still
        # accepts -- a P1-governed disagreement NOT in the malformed set,
        # which fails test_fuzz_mutations_never_raise_and_honour_policy.
        axis = _ensure_axis(nd)
        axis["ontology"] = rng.choice(_FALSY_NON_MAPPING)
        axis.setdefault("vocabulary_mode", "open")

    def set_version_number_benign(rng, nd):
        # version is a STRING, or a NUMBER (int or
        # float, never bool) via str() coercion — 0/1/1.5 ALL stay valid
        # (str()-coerce to a non-empty string); "id"/"namespace" are
        # STRING ONLY (no coercion at all), so this operator is
        # scoped to "version" alone.
        nd["version"] = rng.choice([1, 0, 1.5, 3])

    def set_version_malformed(rng, nd):
        # A boolean, null, array, or object version
        # is malformed (code rejects it outright) even though versum's
        # own str() coercion would swallow all four — a NAMED P2 class
        # (_ND_SYSTEM_VERSUM_P2_MALFORMED); _malformed_nd_system_fields()
        # tags "version" for every one of these.
        nd["version"] = rng.choice([True, None, [1], {"a": 1}])

    def set_namespace_malformed(rng, nd):
        # id/namespace are STRING ONLY — even
        # str(True) == "True" (which WOULD match the id pattern, and which
        # versum itself therefore accepts) is now rejected outright by the
        # code. A NAMED P2 class (_ND_SYSTEM_VERSUM_P2_MALFORMED);
        # _malformed_nd_system_fields() tags "namespace"/"id" for any
        # non-string value here.
        key = rng.choice(["id", "namespace"])
        nd[key] = rng.choice([True, 1, [1], {"a": 1}])

    def set_ontology_relations_non_array_iterable_malformed(rng, nd):
        # ontology_relations is ARRAY ONLY — a
        # non-array iterable (a string, a dict, a set) is malformed too,
        # not only the non-iterable case P1 already covers. versum accepts
        # any iterable (tupling a string's
        # characters or a dict's keys); the code now rejects these.
        nd["ontology_relations"] = rng.choice(["ab", {"a": 1}])

    def set_vocabulary_malformed_item_despite_versum_accepting(rng, nd):
        # A null, array, or object ITEM inside
        # "vocabulary" is malformed, even though _tuple() never filters
        # items and both code and versum accept the document as-is
        # (confirmed directly against real versum). Exercises the SAME
        # class the 2 static vectors "valid-vocabulary-null-item-..."/
        # "valid-vocabulary-nested-array-item-..." pin by hand.
        axis = _ensure_axis(nd)
        axis["vocabulary_mode"] = "closed"
        axis["vocabulary"] = rng.choice([[None], [[1]], [{"a": 1}], ["x", None]])

    def wrap_once(rng, nd):
        wrapped = {"nd_system": copy.deepcopy(nd)}
        nd.clear()
        nd.update(wrapped)

    def set_vocabulary_bare_scalar_benign(rng, nd):
        axis = _ensure_axis(nd)
        axis["vocabulary_mode"] = "closed"
        axis["vocabulary"] = rng.choice(["solo-value", 1])

    def set_typed_non_string_vocabulary_benign(rng, nd):
        # P3: a TYPED closed vocabulary of non-string
        # JSON scalars is well-formed — code, versum AND the schema
        # all accept it. AxisSpec.
        # violations() never cross-checks a vocabulary ENTRY against the
        # axis's own value_type (that lives in the separate, never-called-
        # from-violations() validate_value() method) — so this mutation
        # must ALWAYS stay valid on every side; it is what makes the
        # fuzz's own P3 check (in the main test function) actually
        # exercise this class of document,
        # not just the 3 hand-written vectors.
        axis = _ensure_axis(nd)
        value_type, vocabulary = rng.choice([
            ("integer", [1, 2, 3]),
            ("boolean", [True, False]),
            ("number", [0.5, 1.0, 2]),
        ])
        axis["value_type"] = value_type
        axis["vocabulary_mode"] = "closed"
        axis["vocabulary"] = vocabulary

    def set_primitives_full_set_benign(rng, nd):
        # Draw from the FULL _PRIMITIVES set, not just
        # "equal" — the coverage gap review found (rejecting a valid
        # primitive other than "equal" passed the whole suite, because
        # nothing else ever exercised the rest of the enum). A bare
        # scalar OR a list of 1-3 primitives, either form well-formed.
        axis = _ensure_axis(nd)
        choices = rng.sample(sorted(contract._PRIMITIVES), rng.randint(1, 3))
        axis["primitives"] = choices[0] if len(choices) == 1 and rng.random() < 0.5 else choices

    def set_value_type_full_set_benign(rng, nd):
        # Draw from the FULL _VALUE_TYPES set (11
        # members), not just the 2-3 this file's other mutators happened
        # to use before.
        axis = _ensure_axis(nd)
        axis["value_type"] = rng.choice(sorted(contract._VALUE_TYPES))

    def set_cardinality_full_set_benign(rng, nd):
        # Draw from the FULL _CARDINALITIES set ("one"
        # and "many" both) rather than leaving cardinality untouched
        # (previously only the STATIC baseline's "operator" axis ever
        # carried "one", and no mutator varied it at all).
        axis = _ensure_axis(nd)
        axis["cardinality"] = rng.choice(sorted(contract._CARDINALITIES))

    def set_vocabulary_mode_full_set_benign(rng, nd):
        # Draw from the FULL _VOCAB_MODES set, each
        # with ITS OWN required fields set correctly so the mutation
        # always stays well-formed (closed needs a non-empty vocabulary;
        # external needs ontology_id+ontology_version; open needs
        # nothing extra).
        axis = _ensure_axis(nd)
        mode = rng.choice(sorted(contract._VOCAB_MODES))
        axis["vocabulary_mode"] = mode
        if mode == "closed":
            axis["vocabulary"] = ["a", "b"]
        elif mode == "external":
            axis["ontology_id"] = "o"
            axis["ontology_version"] = "v"

    def delete_optional_key_benign(rng, nd):
        for key in ("version_5d", "ontology_relations", "bindings", "validation"):
            if key in nd:
                del nd[key]
                return

    return [
        set_axes_garbage,
        set_axes_axis_unhashable_value_type,
        set_bindings_non_list_malformed,
        set_bindings_empty_non_list,
        set_bindings_allowed_axes_unhashable,
        set_ontology_relations_non_iterable,
        set_ontology_relations_array_benign,
        set_ontology_relations_non_array_iterable_malformed,
        set_validation_truthy_non_mapping,
        set_validation_falsy_benign,
        set_axis_ontology_truthy_non_mapping,
        set_axis_ontology_truthy_with_flat_fields_present_p2,
        set_axis_ontology_falsy_benign,
        set_version_number_benign,
        set_version_malformed,
        set_namespace_malformed,
        set_vocabulary_malformed_item_despite_versum_accepting,
        wrap_once,
        set_vocabulary_bare_scalar_benign,
        set_typed_non_string_vocabulary_benign,
        set_primitives_full_set_benign,
        set_value_type_full_set_benign,
        set_cardinality_full_set_benign,
        set_vocabulary_mode_full_set_benign,
        delete_optional_key_benign,
    ]


def _mutate_nd_system(rng: random.Random, base: dict) -> dict:
    nd = copy.deepcopy(base)
    mutators = _nd_system_mutators()
    rng.shuffle(mutators)
    for mutator in mutators[: rng.randint(1, 3)]:
        mutator(rng, nd)
    return nd


def _descriptor_mutators():
    def set_plane_wrong_type(rng, d):
        d["plane"] = rng.choice([1, [], None, True])

    def set_language_version_wrong_type(rng, d):
        d["language_version"] = rng.choice([1, [], None])

    def set_binding_value_junk(rng, d):
        d["binding"] = {"r": rng.choice(["junk", 1, None, []])}

    def set_binding_non_mapping(rng, d):
        d["binding"] = rng.choice(["x", [1], 1])

    def set_contract_version_wrong(rng, d):
        d["contract_version"] = rng.choice(["1.0.0", "", None, 1])

    def delete_contract_version(rng, d):
        d.pop("contract_version", None)

    def set_co_dimensions_garbage(rng, d):
        d["co_dimensions"] = rng.choice([1, "x", [1], [{}], None])

    def set_co_dimensions_valid_subset_benign(rng, d):
        d["co_dimensions"] = ["operator"]

    def set_examples_garbage(rng, d):
        d["examples"] = rng.choice([1, "x", [1], [{"sentence": 1}]])

    def set_examples_context_any_type_benign(rng, d):
        d["examples"] = [{"sentence": "s", "expected": [],
                           "context": rng.choice(["s", 1, None, [], {}])}]

    def mutate_nd_system_nested(rng, d):
        d["nd_system"] = _mutate_nd_system(rng, _VALID_ND_SYSTEM)

    def wrap_nd_system(rng, d):
        d["nd_system"] = {"nd_system": copy.deepcopy(d.get("nd_system", _VALID_ND_SYSTEM))}

    def set_nd_system_garbage(rng, d):
        d["nd_system"] = rng.choice(["x", 1, [], None])

    def delete_optional_key_benign(rng, d):
        for key in ("examples", "co_dimensions"):
            if key in d:
                del d[key]
                return

    def rename_plane_valid_benign(rng, d):
        d["plane"] = rng.choice(["loomground-test", "loomground-test-2", "a.b-c"])

    def add_extra_valid_binding_entry_benign(rng, d):
        existing = d.get("binding")
        d["binding"] = dict(existing) if isinstance(existing, Mapping) else {}
        d["binding"]["describes"] = rng.choice(
            ["structural", "causal", "intentional", "temporal", "relational"])

    def set_examples_empty_list_benign(rng, d):
        d["examples"] = []

    return [
        set_plane_wrong_type,
        set_language_version_wrong_type,
        set_binding_value_junk,
        set_binding_non_mapping,
        set_contract_version_wrong,
        delete_contract_version,
        set_co_dimensions_garbage,
        set_co_dimensions_valid_subset_benign,
        set_examples_garbage,
        set_examples_context_any_type_benign,
        mutate_nd_system_nested,
        wrap_nd_system,
        set_nd_system_garbage,
        delete_optional_key_benign,
        rename_plane_valid_benign,
        add_extra_valid_binding_entry_benign,
        set_examples_empty_list_benign,
    ]


def _mutate_descriptor(rng: random.Random, *, require_produce: bool) -> dict:
    d = copy.deepcopy(_VALID_DESCRIPTOR)
    if require_produce:
        d["produce"] = lambda *a, **k: []
    mutators = _descriptor_mutators()
    rng.shuffle(mutators)
    for mutator in mutators[: rng.randint(1, 3)]:
        mutator(rng, d)
    if require_produce and rng.random() < 0.15:
        d["produce"] = rng.choice([None, 1, "x", []])
    return d


def _normalise_descriptor_for_versum(doc: Any, *, require_produce: bool) -> Any:
    """Strip THIS specification's own additions beyond versum's own
    descriptor contract (contract_version, co_dimensions — §9) before
    comparing a verdict with versum, which has no concept of either; in the
    INTERCHANGE form, also drop a mutated ``produce`` key entirely (never
    required or checked there)."""
    if not isinstance(doc, Mapping):
        return doc
    out = dict(doc)
    out["contract_version"] = contract.SPEC_VERSION
    out.pop("co_dimensions", None)
    if not require_produce:
        out.pop("produce", None)
    return out


def _link_mutators():
    def set_dimension_wrong(rng, link):
        link["dimension"] = rng.choice(["junk", 1, [], {}, None, ""])

    def set_dimension_other_valid_benign(rng, link):
        link["relation"] = "describes"
        link["dimension"] = rng.choice(
            ["causal", "intentional", "temporal", "relational"])

    def set_relation_wrong(rng, link):
        link["relation"] = rng.choice([1, [], {}, None, ""])

    def set_relation_embeds_case_variant_benign(rng, link):
        link["relation"] = rng.choice(["Embeds", "EMBEDS", " embeds "])
        link["dimension"] = "structural"

    def delete_dimension(rng, link):
        link.pop("dimension", None)

    def delete_relation(rng, link):
        link.pop("relation", None)

    def add_extra_mode_field_benign(rng, link):
        link["mode"] = rng.choice(["ought", 1, None, []])

    return [
        set_dimension_wrong,
        set_dimension_other_valid_benign,
        set_relation_wrong,
        set_relation_embeds_case_variant_benign,
        delete_dimension,
        delete_relation,
        add_extra_mode_field_benign,
    ]


def _mutate_link(rng: random.Random) -> dict:
    link = copy.deepcopy(_VALID_LINK)
    mutators = _link_mutators()
    rng.shuffle(mutators)
    for mutator in mutators[: rng.randint(1, 3)]:
        mutator(rng, link)
    return link


def _run_safely(fn, *args, **kwargs):
    try:
        return False, fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 - this IS the crash we're hunting
        return True, exc


def test_fuzz_mutations_never_raise_and_honour_policy():
    rng = random.Random(_SEED)
    crashes = []
    p1_violations = []
    p2_violations = []
    p3_violations = []
    valid_count = 0
    malformed_count = 0
    total = 0

    # -- NDSystem docs --
    for _ in range(_N_ND_SYSTEM):
        doc = _mutate_nd_system(rng, _VALID_ND_SYSTEM)
        total += 1
        crashed, result = _run_safely(contract.nd_system_violations, doc)
        if crashed:
            crashes.append(("nd_system_violations", doc, result))
            continue
        ours = result == []
        if ours:
            valid_count += 1
        root = doc
        was_wrapped = isinstance(root, Mapping) and isinstance(root.get("nd_system"), Mapping)
        if was_wrapped:
            root = root["nd_system"]
        malformed_fields = _malformed_nd_system_fields(root)
        if malformed_fields:
            malformed_count += 1
        if _VERSUM_AVAILABLE:
            theirs = _versum_nd_system_valid(doc)
            if ours and not theirs:
                p1_violations.append(("nd_system", doc, result))
            elif not ours and theirs:
                # P2, PER FIELD: excused ONLY if EVERY
                # violation the code itself reports is located at a field
                # _malformed_nd_system_fields() names, not merely because
                # SOME field somewhere in the document is malformed.
                _, violation_paths = _run_safely(contract.nd_system_violations_with_paths, doc)
                code_paths = [p for p, _m in violation_paths] if not isinstance(
                    violation_paths, Exception) else []
                if not _paths_all_malformed(code_paths, malformed_fields):
                    p2_violations.append(("nd_system", doc, result, code_paths))
            # P3: when a document is WELL-FORMED (both code and versum
            # accept it), the schema MUST accept it too, UNLESS every
            # schema error it reports is located at an explicitly
            # malformed field — the
            # typed-vocabulary mutator above is what makes this check
            # actually exercise that class of document; the exclusion
            # is per-field here too).
            if ours and theirs and _JSONSCHEMA_AVAILABLE:
                schema_paths = [
                    _unwrap_nd_system_path(p, was_wrapped=was_wrapped)
                    for p in _nd_system_schema_error_paths(doc)
                ]
                schema_paths = [p for p in schema_paths if p]
                if schema_paths and not _paths_all_malformed(schema_paths, malformed_fields):
                    p3_violations.append(("nd_system", doc, result, schema_paths))

    # -- descriptors, interchange form --
    for _ in range(_N_DESCRIPTOR // 2):
        doc = _mutate_descriptor(rng, require_produce=False)
        total += 1
        crashed, violations = _run_safely(
            contract.descriptor_violations, doc, require_produce=False)
        if crashed:
            crashes.append(("descriptor-interchange", doc, violations))
            continue
        if violations == []:
            valid_count += 1
        if _VERSUM_AVAILABLE:
            # Compare NORMALISED verdicts on BOTH sides — contract_version
            # and co_dimensions are spec-only additions versum knows
            # nothing about (§9); comparing the RAW code verdict (which DOES
            # enforce them) against versum's own (which never can) would
            # manufacture a false P1/P2 disagreement out of an expected,
            # already-documented difference in scope, not an actual parity
            # bug. ours_raw/valid_count above still reflect the REAL,
            # unnormalised contract (crash-safety and the valid-fraction
            # metric must not be diluted by this normalisation).
            normalised = _normalise_descriptor_for_versum(doc, require_produce=False)
            malformed_fields = _malformed_descriptor_fields(normalised)
            if malformed_fields:
                malformed_count += 1
            ours_n = contract.is_valid_descriptor(normalised, require_produce=False)
            theirs = _versum_descriptor_valid(normalised)
            if ours_n and not theirs:
                p1_violations.append(("descriptor-interchange", doc, violations))
            elif not ours_n and theirs:
                _, violation_paths = _run_safely(
                    contract.descriptor_violations_with_paths, normalised, require_produce=False)
                code_paths = [p for p, _m in violation_paths] if not isinstance(
                    violation_paths, Exception) else []
                if not _paths_all_malformed(code_paths, malformed_fields):
                    p2_violations.append(("descriptor-interchange", doc, violations, code_paths))

    # -- descriptors, runtime form --
    for _ in range(_N_DESCRIPTOR // 2):
        doc = _mutate_descriptor(rng, require_produce=True)
        total += 1
        crashed, violations = _run_safely(
            contract.descriptor_violations, doc, require_produce=True)
        if crashed:
            crashes.append(("descriptor-runtime", doc, violations))
            continue
        if violations == []:
            valid_count += 1
        if _VERSUM_AVAILABLE:
            normalised = _normalise_descriptor_for_versum(doc, require_produce=True)
            malformed_fields = _malformed_descriptor_fields(normalised)
            if malformed_fields:
                malformed_count += 1
            ours_n = contract.is_valid_descriptor(normalised, require_produce=True)
            theirs = _versum_descriptor_valid(normalised)
            if ours_n and not theirs:
                p1_violations.append(("descriptor-runtime", doc, violations))
            elif not ours_n and theirs:
                _, violation_paths = _run_safely(
                    contract.descriptor_violations_with_paths, normalised, require_produce=True)
                code_paths = [p for p, _m in violation_paths] if not isinstance(
                    violation_paths, Exception) else []
                if not _paths_all_malformed(code_paths, malformed_fields):
                    p2_violations.append(("descriptor-runtime", doc, violations, code_paths))

    # -- links --
    for _ in range(_N_LINK):
        link = _mutate_link(rng)
        total += 1
        crashed, result = _run_safely(contract.link_violations, link)
        if crashed:
            crashes.append(("link_violations", link, result))
            continue
        crashed2, result2 = _run_safely(contract.embeds_link_violations, link)
        if crashed2:
            crashes.append(("embeds_link_violations", link, result2))
            continue
        if result == []:
            valid_count += 1
        # Links have no versum-side differential (5D's own link shape is
        # this specification's own invention, not ported from versum);
        # P1/P2 do not apply here, only the no-crash assertion does.

    assert total >= 2000, f"fuzz only generated {total} cases, need >= 2000"
    assert not crashes, (
        f"{len(crashes)} crash signature(s) found out of {total} cases "
        "(*_violations must return a list and never raise):\n"
        + "\n".join(f"  {label}: input={inp!r} raised {exc!r}"
                     for label, inp, exc in crashes[:20])
        + (f"\n  ... and {len(crashes) - 20} more" if len(crashes) > 20 else ""))

    # Reports the per-field classifier's own malformed
    # fraction (how many nd_system/descriptor cases carry >= 1 malformed
    # field) over the fuzz stream — informational, not a pass/fail gate.
    nd_and_descriptor_total = _N_ND_SYSTEM + _N_DESCRIPTOR
    print(f"\nmalformed_count={malformed_count} / {nd_and_descriptor_total} "
          f"nd_system+descriptor cases "
          f"({malformed_count / nd_and_descriptor_total:.1%})")

    valid_fraction = valid_count / total
    assert valid_fraction >= _MIN_VALID_FRACTION, (
        f"only {valid_fraction:.1%} of {total} mutated cases stayed valid "
        f"(need >= {_MIN_VALID_FRACTION:.0%}) — the mutation pool is biased "
        "too far toward always-breaking mutations; this check exists so the "
        "fuzz keeps exercising the ACCEPT path, not only the reject path")

    if _VERSUM_AVAILABLE:
        assert not p1_violations, (
            f"{len(p1_violations)} P1 VIOLATION(S) out of {total} cases — "
            "the code accepted a document versum rejects; ALWAYS a defect "
            "(§9), no exception:\n"
            + "\n".join(f"  {label}: doc={doc!r} violations={violations!r}"
                         for label, doc, violations in p1_violations[:20])
            + (f"\n  ... and {len(p1_violations) - 20} more"
               if len(p1_violations) > 20 else ""))
        assert not p2_violations, (
            f"{len(p2_violations)} unclassified code-stricter-than-versum "
            f"disagreement(s) out of {total} cases — the code rejected a "
            "document versum accepts, and at least one of the code's own "
            "violation paths was NOT in _malformed_*_fields()'s set (§9 "
            "P2: excused only per field, never because "
            "SOME other field in the document happens to be malformed); "
            "either fix the code to match versum, or extend the malformed-"
            "field classifier with a justified new case:\n"
            + "\n".join(f"  {label}: doc={doc!r} violations={violations!r} paths={paths!r}"
                         for label, doc, violations, paths in p2_violations[:20])
            + (f"\n  ... and {len(p2_violations) - 20} more"
               if len(p2_violations) > 20 else ""))
        if _JSONSCHEMA_AVAILABLE:
            assert not p3_violations, (
                f"{len(p3_violations)} P3 VIOLATION(S) out of {total} cases "
                "— a WELL-FORMED document (code AND versum both accept it) "
                "was rejected by nd-system.schema.json at a field NOT in "
                "_malformed_nd_system_fields()'s set; §9 P3 requires a "
                "schema to accept every well-formed document code and "
                "versum both accept — this is a genuine schema defect, "
                "never allowed strictness:\n"
                + "\n".join(f"  {label}: doc={doc!r} violations={violations!r} paths={paths!r}"
                             for label, doc, violations, paths in p3_violations[:20])
                + (f"\n  ... and {len(p3_violations) - 20} more"
                   if len(p3_violations) > 20 else ""))


def test_ontology_falsy_values_stay_valid_regression_guard():
    """Deterministic pin for the "ontology falsy value" fix
    (src/five_d_nd/contract.py axis_violations(): ``if ontology_raw and not
    isinstance(ontology_raw, Mapping)``), independent of the stochastic
    mutation draw in test_fuzz_mutations_never_raise_and_honour_policy.

    This test (and the fuzz's own "axis.ontology-falsy" mutation operator)
    catches a reversion of that fix: reverting the guard at that one line
    to the earlier bug (``ontology_raw is not None and not
    isinstance(ontology_raw, Mapping)`` — flags EVERY falsy
    non-mapping, not only a truthy one) makes both this test and
    ``test_fuzz_mutations_never_raise_and_honour_policy`` fail (this test
    directly; the fuzz test via a P2-unclassified disagreement, since
    falsy ontology is explicitly NOT a malformed shape); both pass again
    once the correct guard is restored.
    """
    for falsy in (0, False, "", []):
        doc = {
            "id": "x", "namespace": "x", "version": "1",
            "axes": {"a": {"vocabulary_mode": "open", "ontology": falsy}},
        }
        assert contract.is_valid_nd_system(doc), (
            falsy, contract.nd_system_violations(doc))
        if _VERSUM_AVAILABLE:
            assert _versum_nd_system_valid(doc), falsy


def test_nd_system_version_integer_matches_language_version_regression_guard():
    """Deterministic pin for the "nd_system.version str()
    coercion" fix (src/five_d_nd/contract.py descriptor_violations_with_paths():
    ``nd_system_version = str(nd_system_root.get("version", ""))`` compared
    against ``language_version``, not the raw value), independent of the
    stochastic mutation draw — a masking-regression
    proof target: the fuzz's OWN stochastic draw (fixed seed) does not
    reliably reconstruct "nd_system.version is a well-formed int,
    language_version is the matching string" on every run, so this
    dedicated test exists to guarantee the fuzz SUITE (this file) always
    catches a reversion of that fix, not merely "often".

    This test catches a reversion: reverting the coercion at that
    one line to the earlier bug (comparing the
    RAW ``nd_system_root.get("version", "")`` instead of its str()-coerced
    form) makes it fail (`nd_system version 1 != language_version '1'` — a
    false violation); it passes again once the correct coercion is
    restored.
    """
    doc = {
        "plane": "x", "language_version": "1",
        "nd_system": {
            "id": "x", "namespace": "x", "version": 1,
            "axes": {"a": {"vocabulary": ["O", "P", "F"]}},
        },
        "binding": {}, "contract_version": contract.SPEC_VERSION,
    }
    assert contract.is_valid_descriptor(doc), (
        doc, contract.descriptor_violations(doc))
    if _VERSUM_AVAILABLE:
        assert _versum_descriptor_valid(doc), doc
