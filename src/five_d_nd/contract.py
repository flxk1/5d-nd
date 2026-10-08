# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""The nD grammar contract (spec/SPEC.md §9).

Design change, superseding this branch's own earlier R1-R5 "mode on
every link" design — see
``docs/decisions/0003-is-ought-in-nd-grammars.md`` for the full
history): **5D knows nothing about is/ought (N1).** A 5D link carries
exactly one dimension and nothing else; there is no link ``mode``. A
normative relation MAY bind to a 5D dimension exactly like any other
relation (N2); whether a relation is normative is the OWNING nD grammar's
own knowledge, carried as a "co-dimension" — an ordinary axis in that
grammar's ``NDSystem`` (e.g. the deontic plane's existing ``operator`` axis,
O/P/F) — never something 5D itself inspects or enforces (N3).

Fail-closed validation of:

  * an ``NDSystem`` document — ported field-for-field, rule-for-rule from
    versum's ``src/versum/nd.py`` (``AxisSpec.violations()``,
    ``NDSystem.violations()``; read-only:
    ``git -C loomground-versum show origin/main:src/versum/nd.py``,
    2026-09-30), including versum's own leniency (a ``None``/absent axis
    value is treated as ``{}``; list-or-scalar fields are coerced via
    versum's own ``_tuple()`` pattern; a ``{"nd_system": {...}}`` wrapper is
    unwrapped one level) AND versum's own STRICTNESS where versum would
    reject or crash rather than coerce (a non-list ``bindings`` value, a
    non-mapping ``nd_system`` wrapper value, a non-mapping ``ontology``,
    or an unhashable ``primitives`` entry all become VIOLATIONS here —
    never a silent coercion, never an uncaught exception);
  * a grammar descriptor, in EITHER of two forms (spec/SPEC.md §9):

      - the RUNTIME descriptor — ``produce`` REQUIRED and callable, matching
        versum's ``src/versum/planes.py`` ``DescriptorPlane.from_descriptor``
        exactly (its ``_REQUIRED_KEYS`` includes ``"produce"``);
      - the JSON INTERCHANGE form — ``produce`` OMITTED (JSON cannot carry a
        callable); every other check is identical.

    A ``binding`` value is a BARE DIMENSION STRING, exactly matching
    versum's own ``p5.is_dimension(dim)`` check — no object form, no mode.
    This specification's own addition beyond versum's contract is narrow:
    only the required ``contract_version`` conformance marker (§9/§10).

Stdlib only.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .position import is_dimension

__all__ = [
    "SPEC_VERSION",
    "normalise_relation_key",
    "is_embeds_relation",
    "axis_violations",
    "axis_violations_with_paths",
    "nd_system_violations",
    "nd_system_violations_with_paths",
    "descriptor_violations",
    "descriptor_violations_with_paths",
    "is_valid_nd_system",
    "is_valid_descriptor",
    "link_violations",
    "embeds_link_violations",
]

#: §9: the value `contract_version` MUST equal, exactly, for this draft.
#: "How a grammar declares conformance" (§9): a descriptor's `contract_version`
#: MUST equal the 5D spec version string the grammar was written against —
#: compared by EXACT string equality, never a range or a semver comparison.
#: A grammar that targets a later draft publishes THAT draft's version string
#: once this specification is revised; there is no forward- or backward-
#: compatibility claim across versions.
SPEC_VERSION = "1.0-draft"

_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]*$")
_PLANE_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]*$")
_VALUE_TYPES = frozenset({
    "string", "controlled_identifier", "concept_reference", "entity_reference",
    "integer", "non_negative_integer", "number", "boolean", "date", "interval",
    "quantity",
})
_VOCAB_MODES = frozenset({"closed", "open", "external"})
_CARDINALITIES = frozenset({"one", "many"})
_PRIMITIVES = frozenset({
    "equal", "contains", "contained_by", "overlaps", "disjoint", "precedes", "succeeds",
})
# versum's DescriptorPlane._REQUIRED_KEYS, split into the two forms this module
# validates (see the module docstring): the runtime form additionally requires
# "produce"; the JSON interchange form does not (JSON cannot carry a callable).
_REQUIRED_DESCRIPTOR_KEYS = ("plane", "language_version", "nd_system", "binding")
_RUNTIME_ONLY_REQUIRED_KEYS = ("produce",)


def _tuple(value: Any) -> tuple:
    """Coerce ``value`` to a tuple exactly as versum's own ``_tuple()`` helper
    does (``src/versum/nd.py``): ``None`` -> ``()``; a list/tuple/set/
    frozenset -> ``tuple(value)``; anything else (including a bare string, or
    a single non-string scalar) -> a one-element tuple ``(value,)``. This is
    what lets a scalar ``"primitives": "equal"`` mean the SAME as
    ``"primitives": ["equal"]`` instead of being iterated character-by-
    character as ``"e", "q", "u", "a", "l"``.
    """
    if value is None:
        return ()
    if isinstance(value, (list, tuple, set, frozenset)):
        return tuple(value)
    return (value,)


def normalise_relation_key(key: Any) -> str:
    """Fold case and separator variation out of a relation name so
    ``"Embeds"``, ``"EMBEDS"`` and ``" embeds "`` all compare equal to
    ``"embeds"``. Non-strings normalise to ``""``. General-purpose name
    folding — not tied to any 5D-level list of relations (5D keeps none,
    N1); used by :func:`embeds_link_violations` (§6/§7 N4) and available to
    any caller (e.g. an nD grammar) that wants the same normalisation for
    its own co-dimension bookkeeping.
    """
    if not isinstance(key, str):
        return ""
    return re.sub(r"[\s_-]+", "", key.strip().lower())


def is_embeds_relation(relation: Any) -> bool:
    """True iff ``relation`` names the ``embeds`` relation, after case- and
    separator-insensitive normalisation (:func:`normalise_relation_key`) —
    so ``"Embeds"``, ``"EMBEDS"`` and ``" embeds"`` are all recognised, not
    only the exact literal string ``"embeds"``."""
    return normalise_relation_key(relation) == "embeds"


# ── NDSystem: ported from versum's src/versum/nd.py ──────────────────────────
def axis_violations(axis_id: Any, axis: Any) -> list:
    """Violations of one axis spec — ported from versum's ``AxisSpec.violations()``.

    ``axis`` is the raw axis mapping (as it appears under ``nd_system.axes[axis_id]``),
    not a constructed dataclass; defaults mirror ``AxisSpec.from_dict``, including
    versum's own leniency: a ``None``/falsy ``axis`` is treated as ``{}`` (versum's
    ``v or {}``), never a violation by itself. Where versum itself would crash
    (a non-mapping ``ontology``, an unhashable ``primitives`` entry), this
    function reports a VIOLATION instead of raising.

    Backward-compatible string view of :func:`axis_violations_with_paths` —
    see that function for the machine-readable ``(field_path, message)``
    form (§9's validator parity policy).
    """
    return [msg for _path, msg in axis_violations_with_paths(axis_id, axis)]


def axis_violations_with_paths(axis_id: Any, axis: Any) -> list:
    """Same checks as :func:`axis_violations`, returned as ``(field_path,
    message)`` pairs instead of bare strings — ``field_path`` is relative to
    THIS axis (e.g. ``"vocabulary"``, ``"value_type"``), never prefixed with
    ``"axes.<axis_id>."``; :func:`nd_system_violations_with_paths` adds that
    prefix when aggregating. This is what lets a P2/P3 divergence be
    excused ONLY at the exact field it is located at —
    see spec/SPEC.md §9's validator parity policy and this module's own
    docstring.
    """
    out = []
    if not isinstance(axis_id, str) or not _ID_RE.match(axis_id):
        out.append(("$axis_id", f"invalid axis_id {axis_id!r}"))
    if not axis:
        axis = {}
    if not isinstance(axis, Mapping):
        out.append(("$axis", f"axis {axis_id}: must be a mapping"))
        return out
    # versum's AxisSpec.from_dict str()-COERCES value_type/
    # cardinality/vocabulary_mode BEFORE AxisSpec.violations() ever compares
    # them against a fixed set (`value_type=str(raw.get("value_type",
    # "string"))`, etc.) — so a raw value that is itself unhashable (a list
    # or dict, e.g. value_type: [] or {}) becomes a STRING (str([]) == "[]",
    # a valid dict key) and is simply reported as an unknown value_type, not
    # a crash. An earlier version of this function compared the RAW value
    # directly against a set/frozenset (`value_type not in _VALUE_TYPES`),
    # which raises TypeError for an unhashable raw value — mirrored exactly
    # now: coerce through str() first, exactly where versum does, then
    # compare the coerced string.
    value_type = str(axis.get("value_type", "string"))
    if value_type not in _VALUE_TYPES:
        out.append(("value_type", f"axis {axis_id}: unknown value_type {value_type!r}"))
    cardinality = str(axis.get("cardinality", "many"))
    if cardinality not in _CARDINALITIES:
        out.append(("cardinality", f"axis {axis_id}: cardinality must be 'one' or 'many'"))
    # versum's own default: "closed" iff the KEY "vocabulary" is present at all
    # (even an empty list) — NOT "iff a non-empty vocabulary is given".
    has_vocab_key = "vocabulary" in axis
    mode = str(axis.get("vocabulary_mode", "closed" if has_vocab_key else "open"))
    if mode not in _VOCAB_MODES:
        out.append(("vocabulary_mode", f"axis {axis_id}: unknown vocabulary_mode {mode!r}"))
        mode = None
    vocabulary = _tuple(axis.get("vocabulary"))
    if mode == "closed" and not vocabulary:
        out.append(("vocabulary", f"axis {axis_id}: closed vocabulary is empty"))
    # versum's own `ontology = raw.get("ontology") or {}` replaces a
    # FALSY ontology (None, 0, False, "", []) with {} and never looks at
    # it again — so those falsy shapes are ALWAYS valid, exactly like
    # "validation" below. Only a TRUTHY non-mapping (a
    # non-empty string/list, True, a number) reaches `ontology.get(...)` in
    # versum and crashes with AttributeError there — THAT shape is the
    # violation, not every non-None non-Mapping value (an earlier version
    # of this check was too strict: it flagged 0/False/""/[] as violations
    # even though versum accepts all of them as "no ontology given").
    ontology_raw = axis.get("ontology")
    if ontology_raw and not isinstance(ontology_raw, Mapping):
        out.append(("ontology", f"axis {axis_id}: ontology must be a mapping, got {ontology_raw!r}"))
        ontology_raw = None
    ontology = ontology_raw or {}
    ontology_id = axis.get("ontology_id") or ontology.get("id") or ""
    ontology_version = axis.get("ontology_version") or ontology.get("version") or ""
    if mode == "external" and not (ontology_id and ontology_version):
        out.append(("ontology", f"axis {axis_id}: external ontology requires id and version"))
    for rel in _tuple(axis.get("primitives", ("equal",))):
        try:
            known = rel in _PRIMITIVES
        except TypeError:
            out.append(("primitives", f"axis {axis_id}: unhashable primitive {rel!r}"))
            continue
        if not known:
            out.append(("primitives", f"axis {axis_id}: unknown primitive {rel!r}"))
    return out


def nd_system_violations(doc: Any) -> list:
    """Violations of an NDSystem document — ported from versum's
    ``NDSystem.violations()``: id/namespace/version must be non-empty
    (id/namespace must additionally match :data:`_ID_RE`); at least one axis
    must be declared and each axis must satisfy :func:`axis_violations`;
    every binding rule must name a non-empty ``form_slot`` and every one of
    its ``allowed_axes`` must be a declared axis. Returns ``[]`` when the
    document validates.

    Backward-compatible string view of :func:`nd_system_violations_with_paths`
    — see that function for the machine-readable ``(field_path, message)``
    form (§9's validator parity policy), and spec/SPEC.md
    §9's own explicit field-type table for exactly
    what counts as a malformed shape at each field below.
    """
    return [msg for _path, msg in nd_system_violations_with_paths(doc)]


def nd_system_violations_with_paths(doc: Any) -> list:
    """Same checks as :func:`nd_system_violations`, returned as
    ``(field_path, message)`` pairs — ``field_path`` is relative to THIS
    NDSystem document's own (unwrapped) root, e.g. ``"version"``,
    ``"axes.a.vocabulary"``, ``"bindings"``.

    Mirrors versum's own ``NDSystem.from_dict``: a ``{"nd_system": {...}}``
    wrapper is unwrapped one level first (``root = raw.get("nd_system",
    raw)``) — a caller may pass either the bare NDSystem fields OR a document
    wrapping them under an ``"nd_system"`` key, and both validate
    identically. A ``"nd_system"`` key present with a NON-MAPPING value
    (versum would then try ``None.get(...)``/a scalar's ``.get(...)`` and
    crash) is a VIOLATION here, not a silent fall-through to the outer
    document. Likewise a ``bindings`` value that is present but NOT a list
    (versum iterates it directly — e.g. a dict would yield its keys as
    strings, which then crash inside ``BindingRule.from_dict``) is a
    VIOLATION here, not silently coerced via ``_tuple()`` (unlike
    ``allowed_axes``, which versum DOES coerce per-item).

    NOTE: ``validation.unknown_values == "reject"`` is NOT checked here —
    in versum, that check lives in ``planes.py``'s descriptor validation,
    not in ``NDSystem.violations()`` itself; see :func:`descriptor_violations`.

    §9's EXPLICIT field types, enforced here exactly (spec/SPEC.md §9's
    own field table states these the same way):

      * ``id``, ``namespace``: STRING ONLY. versum itself str()-coerces
        both (so e.g. ``namespace: true`` validates there, ``str(True) ==
        "True"`` matching the id pattern) — this code rejects any
        non-string instead (P2, a NAMED class: §9 P2 permits
        the reference validator to be stricter than versum on a malformed
        shape, and a non-string value at a field §9 declares "string
        only" is exactly that).
      * ``version``: STRING, or a JSON NUMBER (``int``/``float``, NOT
        ``bool`` — a JSON boolean is its own type, never "a number" by
        §9's own field table) accepted via the SAME str() coercion
        versum uses. ``null``, an array, an object, or a boolean are all
        malformed (P2 for the two versum itself still accepts — ``null``
        and a boolean; P1-safe already for an array/object, which crash
        versum's own ``str()`` call... no, ``str([])``/``str({})`` do NOT
        crash versum either, so those two are ALSO P2 now, not P1-driven
        — this function rejects all four alike).
      * ``ontology_relations``: ARRAY ONLY (``list``/``tuple``). versum's
        own ``tuple(root.get("ontology_relations", ()))`` accepts ANY
        iterable — a non-array iterable (a string, a dict, a set) is P2
        malformed-shape strictness under this explicit table, not merely
        the non-iterable case P1 already
        covered.
    """
    if not isinstance(doc, Mapping):
        return [("$doc", "nd_system document must be a mapping")]
    out = []
    root = doc
    if "nd_system" in doc:
        inner = doc["nd_system"]
        if not isinstance(inner, Mapping):
            out.append(
                ("nd_system", f"nd_system wrapper value must be a mapping, got {inner!r}"))
            return out
        root = inner
    # id, namespace: STRING ONLY — no str() coercion;
    # a non-string is rejected outright, even one (e.g. True) versum would
    # itself str()-coerce into something that matches the id pattern. This
    # is a NAMED P2 divergence class — see
    # conformance/vectors/nd-system/invalid-namespace-true-malformed-
    # despite-versum-accepting.json.
    for label in ("id", "namespace"):
        value = root.get(label, "")
        if not isinstance(value, str) or not value or not _ID_RE.match(value):
            out.append((label, f"invalid or missing nD system {label}: {value!r}"))
    # version: STRING, or a NUMBER (never a bool) accepted via str()
    # coercion — see this function's own docstring.
    version_raw = root.get("version", "")
    if isinstance(version_raw, bool) or not isinstance(version_raw, (str, int, float)):
        out.append(("version", f"invalid or missing nD system version: {version_raw!r}"))
    else:
        version_value = str(version_raw)
        if not version_value:
            out.append(("version", f"invalid or missing nD system version: {version_raw!r}"))
    axes = root.get("axes")
    if not isinstance(axes, Mapping) or not axes:
        out.append(("axes", "nD system must declare at least one axis"))
        axes = {}
    for axis_id, axis in axes.items():
        for sub_path, msg in axis_violations_with_paths(axis_id, axis):
            out.append((f"axes.{axis_id}.{sub_path}", msg))
    bindings_raw = ()
    if "bindings" in root:
        bindings_raw = root["bindings"]
        if not isinstance(bindings_raw, (list, tuple)):
            # versum iterates `root.get("bindings", ())` directly (the
            # default `()` applies only when the KEY IS ABSENT): a NON-EMPTY
            # non-list value crashes versum's own `for x in ...` loop body
            # (confirmed directly against real versum: a non-empty string
            # raises AttributeError inside BindingRule.from_dict, None/0/
            # False raise TypeError for not being iterable at all). An EMPTY
            # non-list iterable — "" or {} specifically — does NOT crash:
            # Python's `for x in ...` simply iterates zero times, so versum
            # silently treats "" and {} as "no binding rules" and ACCEPTS
            # them (confirmed directly against real versum too).
            #
            # P2 (§9 validator parity policy): this
            # function keeps REJECTING every non-list "bindings" value,
            # including the empty "" and {} cases versum happens to accept
            # as a side effect of Python's duck-typed iteration. This is a
            # DELIBERATE, DOCUMENTED P2 divergence, not an oversight: the
            # declared type for "bindings" is "a list of binding rule
            # objects" (§9) — a string or a mapping is a MALFORMED SHAPE at
            # that position regardless of how many elements it happens to
            # iterate to, and §9's validator parity policy explicitly
            # permits the reference validator to be stricter than versum on
            # a malformed shape. See conformance/vectors/nd-system/
            # invalid-bindings-empty-string-malformed-despite-versum-
            # accepting.json and its empty-object sibling.
            out.append(("bindings", f"nD system 'bindings' must be a list, got {bindings_raw!r}"))
            bindings_raw = ()
    for binding in bindings_raw:
        if not isinstance(binding, Mapping):
            out.append(("bindings", "binding rule must be a mapping"))
            continue
        form_slot = binding.get("form_slot")
        if not form_slot:
            out.append(("bindings", "binding rule has no form_slot"))
        for axis_id in _tuple(binding.get("allowed_axes")):
            # versum's own `allowed_axes` is NOT coerced
            # per-item (BindingRule.from_dict only wraps the whole field in
            # _tuple(); each ELEMENT is passed through raw) — so `axis_id
            # not in self.axes` (a dict) raises TypeError when axis_id is
            # itself unhashable (a list or dict, e.g. allowed_axes: [[1]] or
            # [{}]). versum's own differential verdict for that shape is
            # "invalid" (the crash propagates, never caught as a pass).
            # Guard the SAME way this module already guards every other
            # dict-membership test on an untrusted value: a non-string
            # axis_id can never equal a declared (string) axis id anyway, so
            # report it as unknown without attempting the `in` test at all.
            if not isinstance(axis_id, str):
                out.append(("bindings.allowed_axes", f"binding {form_slot}: unknown axis {axis_id!r}"))
                continue
            if axis_id not in axes:
                out.append(("bindings.allowed_axes", f"binding {form_slot}: unknown axis {axis_id!r}"))
    # versum's own NDSystem.from_dict does
    # `validation = root.get("validation") or {}` then `validation.get(...)`
    # — a TRUTHY non-mapping "validation" (e.g. "x", [1]) is NOT replaced by
    # `or {}` (truthy), so `.get(...)` on a str/list CRASHES with
    # AttributeError. A FALSY non-mapping ("validation": null, [], 0) IS
    # replaced by `or {}` and never crashes. This function does not itself
    # read validation.unknown_values (see the docstring note above — that
    # lives in descriptor_violations()), but it DOES need to reject the same
    # shapes versum would crash on, as a VIOLATION rather than silently
    # accepting them (versum "accepting" null/[]/0 here means treating them
    # as {} and not raising, so those three remain valid).
    if root.get("validation") and not isinstance(root.get("validation"), Mapping):
        out.append(
            ("validation", f"nD system 'validation' must be a mapping, got {root.get('validation')!r}"))
    # ontology_relations: ARRAY ONLY — see this function's own docstring.
    # A single isinstance() check now covers BOTH the P1-safe non-iterable
    # rejection (None/bool/int/float — these also crash versum's own
    # tuple() constructor) AND
    # the NEW P2 iterable-but-not-an-array rejection (a string/dict/set —
    # versum accepts any of these, tupling a string's characters or a
    # dict's keys, but §9's own table declares this field "array only").
    ontology_relations_raw = root.get("ontology_relations", ())
    if not isinstance(ontology_relations_raw, (list, tuple)):
        out.append(
            ("ontology_relations",
             f"nD system 'ontology_relations' must be a list, got {ontology_relations_raw!r}"))
    return out


def is_valid_nd_system(doc: Any) -> bool:
    return nd_system_violations(doc) == []


# ── grammar descriptor: ported from versum's src/versum/planes.py ───────────
def descriptor_violations(doc: Any, *, require_produce: bool = False) -> list:
    """Violations of an nD grammar descriptor.

    ``require_produce=True`` validates the RUNTIME descriptor form (matching
    versum's ``DescriptorPlane.from_descriptor`` exactly: ``produce`` is
    REQUIRED and must be callable). ``require_produce=False`` (the default)
    validates the JSON INTERCHANGE form (§9): ``produce`` is OMITTED, since
    JSON cannot carry a callable — every other check is identical.

    Checks, in order: required keys present (``produce`` additionally
    required in the runtime form); ``plane``/``language_version`` well-formed;
    ``nd_system`` itself validates (:func:`nd_system_violations`) and its
    ``version`` matches ``language_version``; ``nd_system.validation.
    unknown_values`` must be ``"reject"`` (versum: checked here, in the
    descriptor layer, not inside ``NDSystem.violations()``); every
    ``binding`` value must be a bare dimension string (exactly versum's
    ``p5.is_dimension(dim)`` check — 5D has no concept of a normative
    relation to special-case, N1); in the runtime form, ``produce`` must be
    callable; ``examples`` — if present — must be a list of ``{sentence:
    str, expected: list}`` (an item MAY also carry an optional ``context``
    value, §9, passed through to ``produce(sentence, context)`` for a
    context-dependent grammar; ``context`` itself is passed through
    UNCHECKED — matching versum, which accepts a non-mapping context, e.g. a
    bare string or ``null``, and never validates its shape);
    ``contract_version`` is present and EQUALS :data:`SPEC_VERSION`
    exactly (THIS specification's own conformance marker, §9/§10, not part
    of versum's contract); ``co_dimensions`` — if present — is a list of
    strings, each one a declared axis id of this descriptor's OWN
    ``nd_system.axes`` (§9 N3; OPTIONAL, never required — a grammar MAY mark
    a relation's normative character this way, but 5D itself stays neutral,
    N1).

    Backward-compatible string view of :func:`descriptor_violations_with_paths`
    — see that function for the machine-readable ``(field_path, message)``
    form (§9's validator parity policy).
    """
    return [msg for _path, msg in
            descriptor_violations_with_paths(doc, require_produce=require_produce)]


def descriptor_violations_with_paths(doc: Any, *, require_produce: bool = False) -> list:
    """Same checks as :func:`descriptor_violations`, returned as
    ``(field_path, message)`` pairs — ``field_path`` is relative to the
    descriptor itself, e.g. ``"plane"``, ``"contract_version"``, or (for a
    violation :func:`nd_system_violations_with_paths` found inside the
    descriptor's OWN ``nd_system`` field) ``"nd_system.<path>"`` — ALWAYS
    the UNWRAPPED path (the same rule applies to descriptors with the
    unwrapped nd_system paths), so e.g.
    ``nd_system: {"nd_system": {"axes": {"a": {"vocabulary": ...}}}}``
    (the wrapper form) still reports ``"nd_system.axes.a.vocabulary"``, not
    ``"nd_system.nd_system.axes.a.vocabulary"``.
    """
    if not isinstance(doc, Mapping):
        return [("$doc", "descriptor must be a mapping")]
    out = []
    required = _REQUIRED_DESCRIPTOR_KEYS + (_RUNTIME_ONLY_REQUIRED_KEYS if require_produce else ())
    missing = [k for k in required if k not in doc]
    if missing:
        out.append(("$required", f"descriptor lacks {missing!r}"))
    plane = doc.get("plane")
    # P1, §9: a `plane is not None` guard alone
    # SKIPS this check when "plane" is explicitly present with value
    # None — a descriptor like {"plane": None, ...} was wrongly accepted
    # here even though versum's own `if not isinstance(plane, str) or not
    # _PLANE_ID_RE.match(plane): raise` has NO such carve-out (it checks
    # unconditionally; the separate "key entirely absent" case is instead
    # caught by versum's own required-keys check, which runs first and
    # raises before this one is ever reached — the SAME two-violation
    # outcome this function already produces for a key entirely absent,
    # just via two checks firing instead of versum's one). Guard on
    # "plane" in doc (same pattern as "language_version" just below, which
    # never had this bug) instead of `plane is not None`.
    if "plane" in doc and (not isinstance(plane, str) or not _PLANE_ID_RE.match(plane)):
        out.append(("plane", f"invalid plane id {plane!r}"))
    version = doc.get("language_version")
    if "language_version" in doc and (not isinstance(version, str) or not version):
        out.append(("language_version", f"invalid language_version {version!r}"))
    nd_system = doc.get("nd_system")
    nd_system_root = nd_system
    if "nd_system" in doc:
        if not isinstance(nd_system, Mapping):
            out.append(("nd_system", "nd_system must be a mapping"))
        else:
            sub = nd_system_violations_with_paths(nd_system)
            out.extend((f"nd_system.{sub_path}", msg) for sub_path, msg in sub)
            # nd_system MAY itself be wrapped one more
            # level ({"nd_system": {"nd_system": {...}}}) — versum's own
            # NDSystem.from_dict unwraps ("root = raw.get('nd_system', raw)")
            # before reading version/validation/axes, and nd_system_violations()
            # above already performs the SAME unwrap internally when checking
            # the NDSystem document's OWN shape. The checks below previously
            # read version/validation/axes straight off `nd_system` instead
            # of through that unwrap, so a wrapper-form nd_system was
            # silently read at the WRONG (outer) level — fixed by unwrapping
            # the same way here.
            inner = nd_system.get("nd_system")
            if isinstance(inner, Mapping):
                nd_system_root = inner
            # P1, §9: versum's own NDSystem.from_dict
            # stores `version=str(root.get("version", ""))` — the
            # STRINGIFIED value, not the raw one — and `DescriptorPlane.
            # from_descriptor` then compares THAT (`system.version`)
            # against `language_version`. A raw nd_system.version of 1 (an
            # int) therefore compares EQUAL to language_version: "1" in
            # versum (str(1) == "1"), but this check previously compared
            # the RAW, uncoerced value (`nd_system_root.get("version")`,
            # i.e. the int 1) against the string "1" directly — ALWAYS
            # unequal for any non-string version, a disagreement with
            # versum that is not a malformed shape (str() coercion for
            # "version" is a documented rule, applied everywhere ELSE in
            # this function already — see nd_system_violations()'s own
            # `str(root.get(label, ""))` a few lines above). Coerce the
            # SAME way here before comparing.
            nd_system_version = str(nd_system_root.get("version", ""))
            if not sub and isinstance(version, str) and nd_system_version != version:
                out.append(
                    ("nd_system.version",
                     f"nd_system version {nd_system_version!r} != "
                     f"language_version {version!r}"))
            # versum's own
            # `validation = root.get("validation") or {}` then
            # `validation.get("unknown_values", ...)` CRASHES with
            # AttributeError when "validation" is a TRUTHY non-mapping
            # (e.g. "x", [1] — `or {}` only replaces FALSY values, so a
            # truthy string/list is passed straight to `.get(...)`, which
            # str/list do not have). `*_violations` functions MUST return a
            # list and never raise — report this as a violation instead of
            # crashing, exactly mirroring the `or {}` guard versum uses (a
            # FALSY non-mapping — null, [], 0 — is still accepted, same as
            # versum silently treating it as {}).
            validation_raw = nd_system_root.get("validation")
            if validation_raw and not isinstance(validation_raw, Mapping):
                out.append(
                    ("nd_system.validation",
                     f"nd_system 'validation' must be a mapping, got {validation_raw!r}"))
            else:
                unknown_values = (validation_raw or {}).get("unknown_values", "reject")
                if unknown_values != "reject":
                    out.append(
                        ("nd_system.validation",
                         "nd_system validation.unknown_values must be 'reject', "
                         f"got {unknown_values!r}"))
    co_dimensions = doc.get("co_dimensions")
    if "co_dimensions" in doc:
        if not isinstance(co_dimensions, list) or not all(
                isinstance(c, str) for c in co_dimensions):
            out.append(("co_dimensions", "co_dimensions must be a list of axis id strings"))
        elif isinstance(nd_system_root, Mapping):
            axes = nd_system_root.get("axes")
            known_axes = set(axes) if isinstance(axes, Mapping) else set()
            unknown = [c for c in co_dimensions if c not in known_axes]
            if unknown:
                out.append(
                    ("co_dimensions",
                     f"co_dimensions {unknown!r} are not declared axes of this "
                     "descriptor's own nd_system (§9 N3)"))
    binding = doc.get("binding")
    if "binding" in doc:
        if not isinstance(binding, Mapping):
            out.append(("binding", "binding must be a mapping"))
        else:
            for key, value in binding.items():
                if not isinstance(key, str) or not key:
                    out.append(("binding", f"binding key {key!r} is not a name"))
                    continue
                if not is_dimension(value):
                    out.append(
                        ("binding", f"binding {key!r} -> {value!r} is not one of the five dimensions"))
    if require_produce and "produce" in doc and not callable(doc.get("produce")):
        out.append(("produce", "produce is not callable"))
    examples = doc.get("examples", [])
    if examples is None:
        examples = []
    if not isinstance(examples, list) or not all(
            isinstance(e, Mapping) and isinstance(e.get("sentence"), str)
            and isinstance(e.get("expected"), list) for e in examples):
        out.append(("examples", "examples must be a list of {sentence: str, expected: [claim]}"))
    contract_version = doc.get("contract_version")
    if "contract_version" not in doc or not isinstance(contract_version, str) \
            or not contract_version:
        out.append(("contract_version", "descriptor lacks a non-empty contract_version (conformance marker)"))
    elif contract_version != SPEC_VERSION:
        out.append(
            ("contract_version",
             f"contract_version {contract_version!r} != {SPEC_VERSION!r} — a descriptor's "
             "contract_version MUST equal, exactly, the 5D spec version it targets (§9)"))
    return out


def is_valid_descriptor(doc: Any, *, require_produce: bool = False) -> bool:
    return descriptor_violations(doc, require_produce=require_produce) == []


# ── links (§6) ─────────────────────────────────────────────────────────────
def link_violations(link: Any) -> list:
    """A link MUST carry EXACTLY ONE of the five dimensions (§6) — never zero,
    never more than one. 5D is neutral on is/ought (N1): a link's ``relation``
    is otherwise unconstrained here, and an extra field (e.g. a ``mode`` an
    nD grammar chooses to attach) is simply IGNORED — 5D does not reject a
    link for carrying additional information it does not itself interpret.
    The ONE exception is the N4 ``embeds`` rule, applied here directly (not
    only via :func:`embeds_link_violations`): a link whose relation IS
    ``embeds`` (matched case- and separator-insensitively,
    :func:`is_embeds_relation`) MUST carry dimension ``structural`` — this
    applies to ANY link recognised as embeds, whether or not the caller
    specifically asked for the embeds-only check. Returns violations, or
    ``[]`` when the link satisfies the rule.
    """
    if not isinstance(link, Mapping):
        return ["link must be a mapping"]
    out = []
    dimension = link.get("dimension")
    if "dimension" not in link or dimension in (None, ""):
        out.append("link carries no dimension; a link MUST carry exactly one (§6)")
    elif not is_dimension(dimension):
        out.append(f"link dimension {dimension!r} is not one of the five")
    relation = link.get("relation")
    if "relation" not in link or not relation:
        out.append("link has no relation")
    elif is_embeds_relation(relation) and dimension != "structural":
        out.append(
            f"'embeds' link must be dimension 'structural' (§7 N4), got {dimension!r}")
    return out


def embeds_link_violations(link: Any) -> list:
    """An ``embeds`` link MUST carry ``dimension: structural`` (§6, §7 N4 — a
    norm's regulated content enters 5D as its own entry, linked from the
    norm's own entry by a structural ``embeds`` link). The relation name is
    matched case- and separator-insensitively (:func:`is_embeds_relation`),
    so ``"Embeds"``/``"EMBEDS"``/``" embeds"`` are all recognised as the
    SAME relation this rule governs — not only the exact literal string
    ``"embeds"``. Returns violations, or ``[]`` when the link satisfies the
    rule.
    """
    out = link_violations(link)
    if not isinstance(link, Mapping):
        return out
    relation = link.get("relation")
    if not is_embeds_relation(relation):
        out.append(f"expected relation 'embeds' (case/separator-insensitive), got {relation!r}")
        # link_violations() only applies the structural-dimension rule when it
        # itself RECOGNISES the relation as embeds; since this relation isn't
        # recognised as embeds, that check did not fire above — apply it
        # here too, so a non-embeds-named link is still caught on dimension.
        dimension = link.get("dimension")
        if dimension != "structural":
            out.append(f"'embeds' link must be dimension 'structural', got {dimension!r}")
    return out
