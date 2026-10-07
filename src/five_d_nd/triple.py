# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""The 5D TRIPLE — spec/SPEC.md §11 ("Each edge has one dimension.
Points carry the five values.").

A triple is ``(s, p, o, dimension, weight, provenance)`` plus an OPTIONAL
``grammar_id`` — one edge record, in the originals' own ConceptGraph-edge
style (not RDF-star reification; the original "ConceptGraph Edge"
shape: "source, kind, target, dimension, weight, hypothetical, source_tag";
``grammar_id`` is added here, grounded in the SAME source's own concept data model, which carries a
``grammar_id`` on EVERY claim a grammar's own ``produce()`` emits — §9).
Every triple carries EXACTLY ONE dimension (§6 already states this for a
"link"; a triple IS a link with its endpoints named ``s``/``o`` and its
relation named ``p``, plus the weight and provenance fields §6 leaves to an
nD grammar to attach — this module gives those two fields an explicit,
checked shape instead of leaving them as "whatever a grammar attaches").
``grammar_id``, when present, names WHICH nD grammar's ``produce()``
emitted this triple (§9's own ``plane`` id) — OPTIONAL, since a triple
produced by the assertoric layer itself (§8, D1) has no separate owning nD
grammar to name.

``enables``/``requires`` bind to ``causal`` (resolving a lineage conflict
between the four prior sources) — this module does
not itself classify predicates (that is an nD grammar's ``binding``, §9);
it validates the SHAPE of an already-dimensioned triple.

Stdlib only.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .position import is_dimension

__all__ = ["triple_violations", "is_valid_triple"]


def triple_violations(triple: Any) -> list:
    """Violations of a triple's shape. A triple MUST be a mapping with
    non-empty string ``s``, ``p``, ``o``; EXACTLY one of the five dimensions
    (§2) under ``dimension`` — never absent, never an unknown value; a
    ``weight`` that is a JSON number (never a boolean) in ``[0, 1]``
    (the composition algebra's own multiplicative range, §3) — defaulting to
    ``1.0`` when the key is absent; and a ``provenance`` value that is
    PRESENT (any JSON value — this module does not constrain its shape
    beyond requiring the key, matching §6's own "an nD grammar MAY attach
    its own additional fields" looseness; a grammar's own provenance model,
    e.g. factual's ``SourceTag``, is out of this module's scope).

    Returns ``[]`` when the triple validates.
    """
    if not isinstance(triple, Mapping):
        return ["triple must be a mapping"]
    out = []
    for field in ("s", "p", "o"):
        value = triple.get(field)
        if not isinstance(value, str) or not value:
            out.append(f"triple field {field!r} must be a non-empty string, got {value!r}")
    dimension = triple.get("dimension")
    if "dimension" not in triple or dimension in (None, ""):
        out.append("triple carries no dimension; a triple MUST carry exactly one (§11)")
    elif not is_dimension(dimension):
        out.append(f"triple dimension {dimension!r} is not one of the five")
    weight = triple.get("weight", 1.0)
    if isinstance(weight, bool) or not isinstance(weight, (int, float)):
        out.append(f"triple weight must be a number, got {weight!r}")
    elif not (0.0 <= float(weight) <= 1.0):
        out.append(f"triple weight must be in [0, 1], got {weight!r}")
    if "provenance" not in triple:
        out.append("triple has no provenance")
    if "grammar_id" in triple:
        grammar_id = triple["grammar_id"]
        if not isinstance(grammar_id, str) or not grammar_id:
            out.append(f"triple 'grammar_id' must be a non-empty string when present, got {grammar_id!r}")
    return out


def is_valid_triple(triple: Any) -> bool:
    return triple_violations(triple) == []
