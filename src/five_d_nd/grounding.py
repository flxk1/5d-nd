# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""The thin owned layer: ``5d+nd`` as a grounding *resolver*.

Is / ought
----------
5D is what **IS**: the ``dimension`` this module reports for a resolved span is
versum's own 5D dominant-dimension classification of a factual entry. A deontic
operator (O/P/F — obligation/permission/prohibition) is a normative FORCE, never
a fact on the 5D manifold: an OUGHT/norm entry's ``dimension`` is always ``None``
(never fabricated as a structural artefact its own indexing happens to leave
behind). Norm content reaches this module only through the factual entry the
norm's own nD assignment references (the ``action`` coordinate) — deontic only,
never 5D.

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
  * ``normalize_reference(ref)``   — the ONE canonical span-reference syntax
  * ``resolve(ref, *, store)``     — an anchor resolved into a concrete versum span
  * ``content_digest(ref, span_text)`` — additive: a digest bound to the
    resolved span text, on top of (never instead of) ``digest(ref)``

Shape of a ``5d+nd`` reference
------------------------------
A reference is dimensioned addressing over a dimension-agnostic store (versum):

    {
        "dimensions": ["causal", "structural"],      # base-5 (+nD) addressing
        "anchor": "urn:dls:sha256:<hex>#11-88"        # the canonical span reference
    }

It is well-formed when every entry in ``dimensions`` is a known ``Dimension``
value and it carries an ``anchor``. As it appears inside a certification's
``grounded`` pillar it is wrapped with its scheme + digest::

    {
        "scheme": "5d+nd",
        "ref": { "dimensions": [...], "anchor": ... },
        "digest": { "sha256": "<hex over canonicalize(ref)>" }
    }

Canonical span-reference syntax
--------------------------------
ONE canonical syntax, over the cleaned-text offsets versum itself records (the
``span`` field of :func:`versum.coordinates.entry_coordinates` — a
``(start, end, text)`` triple where ``text`` is the exact source slice at those
offsets, per ``versum.store.index.index_folder``)::

    <source_urn>#<start>-<end>

e.g. ``urn:dls:sha256:defa9705...#11-88``. :func:`normalize_reference` accepts
this form plus two READ-ONLY legacy forms and returns the canonical string;
anything else is rejected (fail closed, never guessed):

  * legacy — ``versum://<path>#span-<start>-<end>``
  * legacy — ``{urn}#{unit}:{start}-{end}`` (the unit token is a hint, dropped
    on normalization — the canonical form carries no unit)

``canonicalize``/``digest``/``validate`` are stdlib only, as before. ``resolve``
is the one function in this module with an optional runtime dependency on
``versum`` (the ``grounding`` extra); it imports it lazily so importing this
module never requires versum to be installed.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Optional

from .dimensions import Dimension

# The scheme name this resolver answers to. One value among interchangeable
# peers ("7d+nd", "prov-o", ...) — NOT a privileged default.
SCHEME = "5d+nd"

__all__ = [
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
]


# ── fail-closed exceptions ──────────────────────────────────────────────────
class SpanReferenceError(ValueError):
    """Base for every ``5d+nd`` span-reference failure. Fails closed — never
    fabricates a normalized string or a resolved span."""


class MalformedReferenceError(SpanReferenceError):
    """``ref`` is neither the canonical span-reference syntax nor either
    documented legacy form."""


class ResolutionError(SpanReferenceError):
    """Base for :func:`resolve` failures once a reference has normalized."""


class MissingStoreError(ResolutionError):
    """``store`` is ``None``, or does not point at a readable versum store."""


class UnknownReferenceError(ResolutionError):
    """No entry in ``store`` matches this reference's source URN + span."""


class SpanMismatchError(ResolutionError):
    """The store's recorded span is inconsistent with the referenced offsets
    (wrong source URN, wrong bounds, or a span whose recorded text does not
    match the length the offsets declare)."""


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


# ── canonical span-reference syntax ─────────────────────────────────────────
# Canonical: <source_urn>#<start>-<end> — no unit token, digits immediately
# after the (only) "#" that ends the reference.
_CANONICAL_RE = re.compile(r"^(?P<urn>.+)#(?P<start>\d+)-(?P<end>\d+)$")

# Legacy (READ-ONLY) 1: versum://<path>#span-<start>-<end>
_LEGACY_VERSUM_URI_RE = re.compile(
    r"^(?P<urn>versum://.+)#span-(?P<start>\d+)-(?P<end>\d+)$"
)

# Legacy (READ-ONLY) 2: {urn}#{unit}:{start}-{end} — the unit token (e.g.
# "sentence") is a hint the canonical form does not carry; dropped here.
_LEGACY_UNIT_RE = re.compile(
    r"^(?P<urn>.+)#(?P<unit>[^:#]+):(?P<start>\d+)-(?P<end>\d+)$"
)


def normalize_reference(ref: Any) -> str:
    """Normalize a span reference to the ONE canonical syntax
    ``<source_urn>#<start>-<end>``.

    Accepts:

      * the canonical form itself (returned as-is, after bounds validation);
      * legacy 1 — ``versum://<path>#span-<start>-<end>``;
      * legacy 2 — ``{urn}#{unit}:{start}-{end}`` (unit dropped).

    Both legacy forms are READ-ONLY: this module never emits them. Anything
    else — a non-string, an unrecognised shape, or a reference whose bounds are
    negative or inverted (``end < start``) — raises
    :class:`MalformedReferenceError`. Fails closed: it never guesses a
    canonical string for input it does not recognise.
    """
    if not isinstance(ref, str) or not ref:
        raise MalformedReferenceError(f"not a string span reference: {ref!r}")

    for pattern in (_LEGACY_VERSUM_URI_RE, _LEGACY_UNIT_RE, _CANONICAL_RE):
        m = pattern.match(ref)
        if m:
            start, end = int(m.group("start")), int(m.group("end"))
            if start < 0 or end < start:
                raise MalformedReferenceError(
                    f"invalid span bounds in reference: {ref!r}"
                )
            return f"{m.group('urn')}#{start}-{end}"

    raise MalformedReferenceError(
        f"not a recognised 5d+nd span reference (canonical or legacy): {ref!r}"
    )


def _parse_canonical(canonical: str) -> tuple[str, int, int]:
    """Split an already-canonical ``<source_urn>#<start>-<end>`` string."""
    urn, _, rest = canonical.rpartition("#")
    start_str, _, end_str = rest.partition("-")
    return urn, int(start_str), int(end_str)


# ── content-bound digest (additive; digest() above is unchanged) ───────────
# Domain separation prefix so a content_digest can never collide with digest()
# even in a pathological case where canonicalize(ref) + span_text happened to
# equal some other canonicalize(ref') bytestring.
_CONTENT_DIGEST_DOMAIN = b"5d+nd:content-digest:v1\x00"


def content_digest(ref: Any, span_text: str) -> dict:
    """Return ``{"sha256": <hex>}`` bound to BOTH ``canonicalize(ref)`` and the
    resolved ``span_text`` — additive on top of :func:`digest`, which stays
    byte-for-byte unchanged and reference-only.

    Domain-separated (a fixed prefix, then a length-prefixed ``canonicalize(ref)``,
    then the UTF-8 span text) so this digest changes if EITHER the reference OR
    the text at its span changes, and can never collide with :func:`digest`.
    Length-prefixing ``canonicalize(ref)`` removes any ambiguity from where the
    reference bytes end and the span text begins.
    """
    if not isinstance(span_text, str):
        raise TypeError(f"span_text must be a str, got {type(span_text).__name__}")
    ref_bytes = canonicalize(ref)
    h = hashlib.sha256()
    h.update(_CONTENT_DIGEST_DOMAIN)
    h.update(len(ref_bytes).to_bytes(8, "big"))
    h.update(ref_bytes)
    h.update(span_text.encode("utf-8"))
    return {"sha256": h.hexdigest()}


def resolve(
    ref: Any,
    *,
    store: Optional[Any] = None,
    source_text: Optional[str] = None,
    expected_content_digest: Optional[dict] = None,
) -> dict:
    """Resolve a ``5d+nd`` reference into a concrete span in the versum store.

    1. ``validate(ref)`` first; a malformed dimensioned reference never resolves
       (fail closed — raises ``ValueError``, as before).
    2. ``ref["anchor"]`` must be a span-reference string; it is normalized via
       :func:`normalize_reference` (canonical or either legacy form; anything
       else raises :class:`MalformedReferenceError`).
    3. The normalized ``<source_urn>#<start>-<end>`` is resolved through
       versum's PUBLIC API only:

         * ``versum.planes.entry_id(source_urn, start, end)`` — the same
           deterministic id versum's own indexer stamps on the entry at those
           exact offsets (no private reader, no CSV parsing: this is a pure
           function of the three values already in hand);
         * ``versum.coordinates.entry_coordinates(store, entry_id)`` — the
           entry's span, its 5D ``dimension`` (``None`` for an OUGHT/norm
           entry — see the is/ought note in this module's docstring), and its
           nD coordinate assignments.

    4. Fails closed with a specific exception, never a fabricated result:

         * :class:`MissingStoreError` — ``store`` is ``None``, or versum
           cannot read anything at ``store``;
         * :class:`UnknownReferenceError` — no entry in ``store`` matches the
           reference's source URN + span;
         * :class:`SpanMismatchError` — the store's own record for that entry
           id disagrees with the reference (a different source URN, different
           bounds, or a recorded span text whose length does not match the
           declared ``end - start``); OR the resolved span text disagrees
           with an independently supplied ``source_text``/
           ``expected_content_digest`` (see below) — never silently trusted.

    Same-length tampering (the store's own ``entries.csv`` row edited so its
    ``text`` keeps the declared length but its CONTENT changes — e.g. "must
    not" swapped for "shall do") is invisible to a length-only check: nothing
    in ``versum.coordinates.entry_coordinates``'s single-entry result lets
    ``resolve`` independently re-derive the entry's original text (an
    entry id is ``hash(source_urn, start, end)`` only — content-free — and
    ``entries.csv`` carries no separate per-entry content hash). Fail-closed
    verification of CONTENT therefore requires the caller to supply one of:

      * ``source_text`` — the independently-held cleaned source text (the
        same cleaning versum's own indexer applies before computing offsets,
        e.g. via ``versum.io.extract.clean_text``); ``resolve`` slices
        ``source_text[start:end]`` and raises :class:`SpanMismatchError` if it
        disagrees with the store's recorded span text, REGARDLESS of whether
        the two are the same length;
      * ``expected_content_digest`` — a previously recorded
        ``content_digest(ref, known_good_span_text)`` (e.g. one a certification
        already carries from an earlier, trusted resolution); ``resolve``
        recomputes ``content_digest(ref, span_text)`` over what it just read
        and raises :class:`SpanMismatchError` on any mismatch.

    Neither is required (a caller with no independent text/digest still gets
    the length-only check, unchanged); either closes the same-length gap.

    Returns ``{"entry_id", "span": {"start", "end", "text"}, "dimension",
    "nd", "source_urn", "content_digest"}``. ``content_digest`` is the
    additive digest from :func:`content_digest`, bound to this ``ref`` AND the
    resolved span text — surfaced here so a verifier gets it for free; it is
    never a substitute for the reference-only ``digest(ref)`` a certification
    already carries.

    ``versum`` is imported lazily, only inside this function: importing
    ``five_d_nd.grounding`` itself still requires no dependency beyond the
    standard library. Install the ``grounding`` extra
    (``pip install '5d-nd[grounding]'``) to use ``resolve``.
    """
    if not validate(ref):
        raise ValueError("not a well-formed 5d+nd grounding reference")

    anchor = ref["anchor"]
    if not isinstance(anchor, str):
        raise MalformedReferenceError(
            "resolve() requires a string span-reference anchor (canonical or "
            f"legacy); got {type(anchor).__name__}"
        )
    canonical = normalize_reference(anchor)
    source_urn, start, end = _parse_canonical(canonical)

    if store is None or store == "":
        raise MissingStoreError(
            f"resolve() requires a readable store handle; got {store!r}"
        )
    if not isinstance(store, (str, bytes)) and not hasattr(store, "__fspath__"):
        raise MissingStoreError(
            "resolve() requires a store handle that is a path (str/bytes/"
            f"os.PathLike); got {type(store).__name__} ({store!r})"
        )

    try:
        from versum import coordinates as _versum_coordinates
        from versum import planes as _versum_planes
    except ImportError as exc:
        raise MissingStoreError(
            "resolve() requires the optional 'versum' dependency; install the "
            "'grounding' extra (`pip install '5d-nd[grounding]'`)"
        ) from exc

    entry_id = _versum_planes.entry_id(source_urn, start, end)
    try:
        coords = _versum_coordinates.entry_coordinates(store, entry_id)
    except _versum_coordinates.UnknownEntryError as exc:
        raise UnknownReferenceError(
            f"no entry in the store matches {canonical!r}"
        ) from exc
    except (FileNotFoundError, NotADirectoryError) as exc:
        raise MissingStoreError(f"store not found or unreadable: {store!r}") from exc

    span_start, span_end, span_text = coords["span"]
    if (
        coords.get("source_urn") != source_urn
        or span_start != start
        or span_end != end
        or len(span_text) != end - start
    ):
        raise SpanMismatchError(
            f"recorded span for {canonical!r} does not match the referenced "
            "offsets (source URN, bounds, or span-text length mismatch)"
        )

    # Content check, additive on top of the length-only check above: catches
    # same-length tampering that a length comparison alone cannot (see the
    # docstring section above). Only runs when the caller supplies one of the
    # two independent grounds of truth; a caller with neither still gets the
    # length-only check unchanged.
    if source_text is not None:
        source_slice = source_text[start:end]
        if span_text != source_slice:
            raise SpanMismatchError(
                f"recorded span text for {canonical!r} does not match the "
                "independently supplied source_text at these offsets — "
                "content tampering (same-length or otherwise)"
            )
    if expected_content_digest is not None:
        actual = content_digest(ref, span_text)
        if actual != expected_content_digest:
            raise SpanMismatchError(
                f"resolved content_digest for {canonical!r} does not match "
                "the supplied expected_content_digest — content tampering "
                "(same-length or otherwise)"
            )

    result = {
        "entry_id": coords["entry_id"],
        "span": {"start": span_start, "end": span_end, "text": span_text},
        "dimension": coords["dimension"],
        "nd": coords["nd"],
        "source_urn": coords["source_urn"],
    }
    result["content_digest"] = content_digest(ref, span_text)
    return result
