# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""The thin owned layer: ``5d+nd`` as a grounding *resolver*.

``5d+nd`` is the reference resolver for ONE grounding scheme used by governance
certifications — **not** a standard, and not privileged. It is one interchangeable
option; its peers are ``7d+nd`` and ``prov-o``. A ``GovernanceCertification``'s
``grounded.scheme`` may be any of them, and whatever understands the vocabulary
resolves the reference. There is no bespoke registry.

This module owns almost nothing. It composes on:

  * the **dimension algebra** — the ``Dimension`` enum + composition table,
    vendored from ``loomground-solver`` (see ``five_d_nd.dimensions``); and
  * **PROV-O / RDF-Data-Cube** for the modelling of a dimensioned reference,
    which in turn re-describes **BFO / CIDOC-CRM** modal knowledge representation.

What it *does* own is the thin, checkable seam that lets any verifier treat a
``5d+nd`` reference like any other grounding reference:

  * ``canonicalize(ref) -> bytes``  — deterministic JSON (JCS-style)
  * ``digest(ref) -> {"sha256": hex}`` — the content digest a cert carries
  * ``validate(ref) -> bool``       — is this a well-formed ``5d+nd`` reference?
  * ``resolve(ref, *, store=None)`` — STUB: how an anchor becomes a versum span

Shape of a ``5d+nd`` reference
------------------------------
A reference is dimensioned addressing over a dimension-agnostic store (versum):

    {
        "dimensions": ["causal", "structural"],      # base-5 (+nD) addressing
        "anchor": "versum://folder/note#span-42"      # a store-span or a URI
    }

It is well-formed when every entry in ``dimensions`` is a known ``Dimension``
value and it carries an ``anchor``. As it appears inside a certification's
``grounded`` pillar it is wrapped with its scheme + digest::

    {
        "scheme": "5d+nd",
        "ref": { "dimensions": [...], "anchor": ... },
        "digest": { "sha256": "<hex over canonicalize(ref)>" }
    }

Stdlib only. No dependency on versum, on the solver, or on any RDF toolkit.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Optional

from .dimensions import Dimension

# The scheme name this resolver answers to. One value among interchangeable
# peers ("7d+nd", "prov-o", ...) — NOT a privileged default.
SCHEME = "5d+nd"

__all__ = ["SCHEME", "canonicalize", "digest", "validate", "resolve"]


def canonicalize(ref: Any) -> bytes:
    """Return the canonical byte serialization of a grounding reference.

    Deterministic JSON — keys sorted **recursively**, compact separators, real
    UTF-8 — so two references that differ only in key order serialize to the
    same bytes and therefore digest identically. This is the property the digest
    (and any cross-implementation agreement on it) rests on.

    This is a **JCS-style** approximation using the standard library. It sorts
    object keys and strips insignificant whitespace, but it does NOT implement
    the full RFC 8785 (JSON Canonicalization Scheme) rules for number formatting
    (ECMAScript ``Number`` serialization) or Unicode string normalization. For
    production interop — matching the RFC 8785 digest a conforming host computes over its
    ``grounded`` pillar — swap this for a real RFC 8785 canonicalizer. Keep
    references to JSON scalars, objects, and arrays (no floats needing exponent
    normalization, no non-NFC strings) and the two agree.
    """
    return json.dumps(
        ref,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def digest(ref: Any) -> dict:
    """Return ``{"sha256": <hex>}`` — the content digest of a reference.

    Computed over :func:`canonicalize`, so it is stable across key ordering and
    matches the shape stored in a certification's ``grounded.digest``.
    """
    return {"sha256": hashlib.sha256(canonicalize(ref)).hexdigest()}


def _known_dimension(value: Any) -> bool:
    """True iff ``value`` names a known ``Dimension`` (enum member or its str)."""
    try:
        Dimension(value)
        return True
    except (ValueError, KeyError):
        return False


def _has_anchor(ref: dict) -> bool:
    """True iff ``ref`` carries a usable anchor — a non-empty URI/store-span
    string or a non-empty store-span mapping."""
    anchor = ref.get("anchor")
    if isinstance(anchor, str):
        return anchor.strip() != ""
    if isinstance(anchor, dict):
        return len(anchor) > 0
    return False


def validate(ref: Any) -> bool:
    """Return ``True`` iff ``ref`` is a well-formed ``5d+nd`` grounding reference.

    Well-formed means: ``ref`` is a mapping with a non-empty ``dimensions`` list
    whose every entry is a known :class:`~five_d_nd.dimensions.Dimension` value,
    and it carries an ``anchor`` (a store-span or a URI).

    The ``+nD`` in the scheme name is the forward-compatibility axis for custom
    dimensions beyond the base five; the *reference* resolver deliberately
    validates only against the base vocabulary it vendors. A downstream resolver
    that understands extra dimensions may accept more — this one is strict, and
    fails closed on anything it does not recognise.
    """
    if not isinstance(ref, dict):
        return False
    dimensions = ref.get("dimensions")
    if not isinstance(dimensions, list) or len(dimensions) == 0:
        return False
    if not all(_known_dimension(d) for d in dimensions):
        return False
    return _has_anchor(ref)


def resolve(ref: Any, *, store: Optional[Any] = None) -> Any:
    """Resolve a ``5d+nd`` reference into a concrete span in the versum store.

    STUB — this is the seam, documented but intentionally not wired. The intended
    contract:

      1. ``validate(ref)`` first; a malformed reference never resolves (fail
         closed).
      2. Interpret ``ref["anchor"]``:
           * a **store-span** (e.g. ``{"folder": ..., "note": ..., "span": ...}``)
             addresses a location in versum directly;
           * a **URI** (e.g. ``versum://folder/note#span-42``) is parsed into the
             same coordinates.
      3. Read that span from ``store`` — the versum store handle, passed in by the
         caller. versum is **dimension-agnostic**: it stores content and takes a
         ``dimension`` *string*; ``ref["dimensions"]`` selects/filters the edges
         along which the span is retrieved or traversed. The dimension algebra
         (``five_d_nd.dimensions.compose``) governs multi-step traversal.
      4. Return the resolved span (content + provenance) for the verifier to
         compare against the certification's ``grounded.digest``.

    ``store`` is dependency-injected precisely so this module needs no import of,
    and no dependency on, versum. When ``store is None`` there is nothing to read
    from.

    Extension point: to wire it, pass a store handle as ``store`` and replace the
    ``NotImplementedError`` below with the span lookup. It raises rather than
    fabricating a result.
    """
    if not validate(ref):
        raise ValueError("not a well-formed 5d+nd grounding reference")
    # Left unimplemented on purpose — this repo owns the resolver seam, not the
    # store: parse ref["anchor"] into store coordinates and read the anchored
    # span from the injected `store` handle.
    raise NotImplementedError(
        "5d+nd resolve() is a documented stub: wire a versum store handle to "
        "read the anchored span. See this function's docstring for the contract."
    )
