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
    ``compose_weights``, ``classify_predicate``, ``classify_query_dimension``
  * the owned resolver seam — ``SCHEME``, ``canonicalize``, ``digest``,
    ``validate``, ``resolve``
"""

from __future__ import annotations

from .dimensions import (
    COMPOSITION_TABLE,
    DEFAULT_DIMENSION,
    Dimension,
    classify_predicate,
    classify_query_dimension,
    compose,
    compose_weights,
)
from .grounding import SCHEME, canonicalize, digest, resolve, validate

__version__ = "0.1.0"

__all__ = [
    # owned resolver seam
    "SCHEME",
    "canonicalize",
    "digest",
    "validate",
    "resolve",
    # vendored dimension vocabulary (authoritative copy lives upstream)
    "Dimension",
    "DEFAULT_DIMENSION",
    "COMPOSITION_TABLE",
    "compose",
    "compose_weights",
    "classify_predicate",
    "classify_query_dimension",
    "__version__",
]
