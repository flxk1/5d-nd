# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""``5d+nd`` — the reference resolver for ONE grounding scheme.

Not a standard. One interchangeable option among a certification's grounding
schemes (peers: ``7d+nd``, ``prov-o``). This package packages the vendored
dimension algebra as a grounding resolver: canonicalize + digest + validate a
``5d+nd`` reference, and (stub) resolve its anchor into a versum span.

Public surface:

  * the dimension vocabulary (vendored from ``loomground-solver``) —
    ``Dimension``, ``DEFAULT_DIMENSION``, ``COMPOSITION_TABLE``, ``compose``,
    ``compose_weights``, ``classify_predicate``, ``classify_query_dimension``,
    ``left_fold``
  * the owned resolver seam — ``SCHEME``, ``canonicalize``, ``digest``,
    ``validate``, ``normalize_reference``, ``resolve``, ``content_digest``
  * the clause-cue layer (§8a, additive to §8) and matching (§19) —
    ``clause_cues``, ``match`` submodules (fix round, owner-approved
    integration step, 2026-10-02); two EXAMPLE nD grammars demonstrating
    §9 live under ``five_d_nd.grammars`` (imported separately — NOT 5D)

5D is neutral on is/ought (spec/SPEC.md §7, N1 — owner design change,
2026-10-01): there is no link mode and no second fingerprint here. A
normative relation's identity is nD-grammar knowledge, carried as a
co-dimension on that grammar's own ``NDSystem`` (§9) — never something this
package inspects.
"""

from __future__ import annotations

from .assertoric import BINDING, QUANTIFIERS, RELATIONS, lower_assertion
from .contract import (
    axis_violations,
    descriptor_violations,
    embeds_link_violations,
    is_embeds_relation,
    is_valid_descriptor,
    is_valid_nd_system,
    link_violations,
    nd_system_violations,
    normalise_relation_key,
)
from .dimensions import (
    COMPOSITION_TABLE,
    DEFAULT_DIMENSION,
    Dimension,
    classify_predicate,
    classify_query_dimension,
    compose,
    compose_weights,
    left_fold,
)
from .grounding import (
    SCHEME,
    MalformedReferenceError,
    MissingStoreError,
    ResolutionError,
    SpanMismatchError,
    SpanReferenceError,
    UnknownReferenceError,
    canonicalize,
    content_digest,
    digest,
    normalize_reference,
    resolve,
    validate,
)
from .position import (
    DIMENSIONS,
    EMBEDS_DIMENSION,
    basis,
    dominant,
    fingerprint,
    is_dimension,
    normalise,
    with_embeds,
)
from . import (
    clause_cues,
    container,
    depth,
    fixedpoint,
    match,
    path,
    point,
    profile,
    replay,
    statement,
    triple,
    views,
)

__version__ = "0.1.0"

__all__ = [
    # owned resolver seam
    "SCHEME",
    "canonicalize",
    "digest",
    "validate",
    "normalize_reference",
    "resolve",
    "content_digest",
    "SpanReferenceError",
    "MalformedReferenceError",
    "ResolutionError",
    "MissingStoreError",
    "UnknownReferenceError",
    "SpanMismatchError",
    # vendored dimension vocabulary (authoritative copy lives upstream)
    "Dimension",
    "DEFAULT_DIMENSION",
    "COMPOSITION_TABLE",
    "compose",
    "compose_weights",
    "classify_predicate",
    "classify_query_dimension",
    "left_fold",
    # the 5D fingerprint (position) — ONE per entry (N1)
    "DIMENSIONS",
    "is_dimension",
    "normalise",
    "dominant",
    "basis",
    "fingerprint",
    "with_embeds",
    "EMBEDS_DIMENSION",
    # the assertoric layer (D1)
    "QUANTIFIERS",
    "RELATIONS",
    "BINDING",
    "lower_assertion",
    # the nD grammar contract (§9); 5D is neutral on is/ought (§7, N1-N4)
    "normalise_relation_key",
    "is_embeds_relation",
    "axis_violations",
    "nd_system_violations",
    "is_valid_nd_system",
    "descriptor_violations",
    "is_valid_descriptor",
    "link_violations",
    "embeds_link_violations",
    # coordinate round (stage 1) submodules — spec/SPEC.md §11-§17
    "container",
    "depth",
    "fixedpoint",
    "point",
    "profile",
    "triple",
    "views",
    # fix round (owner-approved integration step, 2026-10-02) — spec/SPEC.md
    # §8a (clause-cue layer, additive to §8) and §19 (matching); EXAMPLE nD
    # grammars live under five_d_nd.grammars, imported separately (not
    # re-exported here — they are NOT 5D, see that subpackage's own docstring)
    "clause_cues",
    "match",
    "replay",
    # typed-triple layer (T1) — spec/SPEC.md §21-§22
    "statement",
    "path",
    "__version__",
]
