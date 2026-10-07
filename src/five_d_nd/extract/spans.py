# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""Span post-processing helpers for the deterministic typed-Statement extractor.

These implement the span-trimming SIDE of the codebook's own Unitisation
rules (`docs/codebook/typed-statements-v1.md`, "Unitisation rules" —
read-only, this module does not edit it): a leading determiner is
stripped from an endpoint span (never "part of", R-o), a leading MODAL
VERB is stripped from an endpoint span (R-k), and surrounding whitespace
is trimmed. Every function here operates on ``(start, end)`` CHARACTER
offsets into one already-fixed ``text`` string and returns a NEW
``(start, end)`` pair — never a mutation, never a guess at content the
text does not contain.

Stdlib only.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Optional

__all__ = [
    "DETERMINERS",
    "MODAL_PREFIXES",
    "trim_whitespace",
    "strip_determiner",
    "strip_modal_prefix",
    "strip_subject_and_modal_prefix",
    "truncate_before_modal",
    "finalize_endpoint_span",
    "span_text",
]

#: Leading determiners stripped from an endpoint span — codebook's own
#: list, VERBATIM: "a", "an", "the", "one of (the)". "part of" is
#: DELIBERATELY absent (R-o: "part of" is not a determiner).
DETERMINERS = (
    "one of the", "one of", "the", "an", "a",
)
_DETERMINER_RE = re.compile(
    r"^(?:" + "|".join(re.escape(d) for d in DETERMINERS) + r")\s+",
    re.IGNORECASE,
)

#: Leading modal tokens stripped from an endpoint span — R-k: "shall",
#: "may", "must", "should", "is to be", and the fixed phrases "shall be
#: deemed"/"shall be held" never appear inside a subj/obj span. Longer
#: phrases are tried first so "shall be deemed" is consumed whole rather
#: than leaving a dangling "be deemed".
MODAL_PREFIXES = (
    "shall be deemed to be", "shall be deemed", "shall be held to be",
    "shall be held", "is to be", "shall", "may", "must", "should",
)
_MODAL_RE = re.compile(
    r"^(?:" + "|".join(re.escape(m) for m in MODAL_PREFIXES) + r")\s+",
    re.IGNORECASE,
)


def trim_whitespace(text: str, start: int, end: int) -> tuple:
    """Shrink ``(start, end)`` inward past any leading/trailing ASCII
    whitespace in ``text[start:end]`` — never past the original bounds,
    never into a NEGATIVE-length span (an all-whitespace input returns
    ``(start, start)``)."""
    s, e = start, end
    while s < e and text[s] in " \t\r\n\f\v":
        s += 1
    while e > s and text[e - 1] in " \t\r\n\f\v":
        e -= 1
    return (s, e)


def strip_determiner(text: str, start: int, end: int) -> tuple:
    """One leading determiner (:data:`DETERMINERS`) stripped from
    ``text[start:end]``, re-trimmed afterwards. Idempotent: calling this
    twice in a row on its own output is a no-op (there is at most one
    leading determiner to strip)."""
    s, e = trim_whitespace(text, start, end)
    m = _DETERMINER_RE.match(text[s:e])
    if m:
        s = s + m.end()
    return trim_whitespace(text, s, e)


def strip_modal_prefix(text: str, start: int, end: int) -> tuple:
    """Every LEADING modal token (:data:`MODAL_PREFIXES`) stripped from
    ``text[start:end]``, one at a time, re-trimmed between each strip —
    "shall may" (never real text, but defensive) strips both; ordinary
    single-modal text ("shall ensure...") strips exactly once."""
    s, e = trim_whitespace(text, start, end)
    while True:
        m = _MODAL_RE.match(text[s:e])
        if not m:
            break
        s = s + m.end()
        s, e = trim_whitespace(text, s, e)
    return (s, e)


#: R-k: a `requires` consequence object captured
#: as "the WHOLE remainder of the clause" (the only shape this
#: extractor's simple `requires` regexes can capture) still carries the
#: REPEATED SUBJECT in front of its own modal — "the operator SHALL
#: notify..." — which `strip_modal_prefix` alone cannot remove (it only
#: strips a modal that is ALREADY the first token). This strips BOTH: an
#: optional leading determiner, then a SHORT actor noun phrase (bounded,
#: non-greedy so it matches as LITTLE as possible before the modal),
#: then the modal itself — leaving only the ACT ("notify the
#: authority..."), never framed as "an obligation" or kept with its own
#: holder, per `requires`'s own codebook definition ("the object is the
#: ACT ITSELF").
_SUBJECT_AND_MODAL_RE = re.compile(
    r"^(?:the\s+|a\s+|an\s+)?[A-Za-z][\w\s,'-]{0,60}?\s+"
    r"(?:shall be deemed to be|shall be deemed|shall be held to be|shall be held|"
    r"is to be|shall|may|must|should)\b,?\s*",
    re.IGNORECASE,
)


def strip_subject_and_modal_prefix(text: str, start: int, end: int) -> tuple:
    """Strip a leading "SUBJECT MODAL" prefix (:data:`_SUBJECT_AND_MODAL_RE`)
    from ``text[start:end]`` — a no-op (returns the input unchanged, after
    whitespace-trimming) if no such prefix is found, so this is SAFE to
    call on a span that never had a repeated subject in front of its own
    modal in the first place."""
    s, e = trim_whitespace(text, start, end)
    m = _SUBJECT_AND_MODAL_RE.match(text[s:e])
    if m:
        s = s + m.end()
    return trim_whitespace(text, s, e)


#: A MID-SPAN modal (not necessarily leading) — a rule's own obj/subj
#: capture group is a bounded character class, not a real parser, and
#: can run past the end of ITS OWN clause into the START of the next
#: one; the next clause's own leading modal ("...filing system SHALL be
#: processed...") is the single most reliable boundary signal available
#: without one. :func:`truncate_before_modal` cuts the span there —
#: never inside a LEADING modal (R-k's own :func:`strip_modal_prefix`
#: handles that separately), only a modal appearing STRICTLY AFTER the
#: span's own start.
_MODAL_MIDSPAN_RE = re.compile(r"\b(?:shall|may|must|should)\b", re.IGNORECASE)


def truncate_before_modal(text: str, start: int, end: int) -> tuple:
    """Shrink ``end`` to just before the FIRST modal token
    (:data:`MODAL_PREFIXES`'s own single-word members) found strictly
    after ``start`` within ``text[start:end]`` — a defensive clean-up for
    a cue-regex's own obj/subj capture group bleeding past its clause's
    true boundary into a NEXT clause's leading modal. A no-op if no such
    modal is found."""
    m = _MODAL_MIDSPAN_RE.search(text, start + 1, end)
    if m is None:
        return (start, end)
    return (start, m.start())


def finalize_endpoint_span(
    text: str, start: int, end: int, *, strip_det: bool = True, strip_modal: bool = False,
) -> Optional[tuple]:
    """The full endpoint-span pipeline: whitespace-trim, then (optionally)
    strip ONE leading determiner, then (optionally) strip every leading
    modal token, then re-trim. Returns ``None`` if the result is empty
    (nothing left to name an entity with) — the caller drops the
    candidate Statement rather than emit a vacuous span."""
    s, e = trim_whitespace(text, start, end)
    if strip_det:
        s, e = strip_determiner(text, s, e)
    if strip_modal:
        s, e = strip_modal_prefix(text, s, e)
    if e <= s:
        return None
    return (s, e)


def span_text(text: str, span: tuple) -> str:
    """The NFC-normalised, whitespace-collapsed surface text of ``span``
    — never the raw slice (a provenance span's own raw slice may carry a
    stray embedded newline from the source corpus; the Statement's own
    ``subj``/``obj`` string is the readable form)."""
    raw = text[span[0]:span[1]]
    t = unicodedata.normalize("NFC", raw)
    t = t.replace(" ", " ")
    t = re.sub(r"[ \t\n\r\f\v]+", " ", t).strip()
    return t
