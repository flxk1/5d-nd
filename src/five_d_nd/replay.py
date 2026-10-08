# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""Replay: runtime/timing NEVER enters a hashed result.

Runtime is kept out of results.json. Every function in
`five_d_nd.clause_cues`, `five_d_nd.match`, `five_d_nd.grammars.term` and
`five_d_nd.grammars.requirement` returns ONLY deterministic, content
-derived values — no wall-clock time, no monotonic counter, no process id,
anywhere in a return value that is itself digested, compared across runs,
or stored as a conformance vector's own ``expected`` field. This module is
the ONE place timing information is allowed to live, kept structurally
separate from every hashed/compared value.

**Why this matters for replay.** A conformance vector's own `expected`
field, a profile's `profile_digest` (§16), a term grammar's own
`profile_digest` (§18), and a requirement ruleset's own `ruleset_digest`
(§18) are all BYTE-REPRODUCIBLE — the same input produces the same digest
on every machine, forever (§8a/§18/§19's own module docstrings each state
this). Mixing a runtime measurement into any of those values would make
them machine- and load-dependent, breaking that guarantee silently — the
finding that drove this rule.

``timed_call`` is the one helper this module offers: it runs a callable
and returns `(result, elapsed_seconds)` as a 2-TUPLE, never merged into a
single mapping — a caller that wants to log or report timing reads
`elapsed_seconds` separately and keeps `result` the only thing that ever
reaches a digest, a conformance vector, or a cross-run comparison.

Stdlib only.
"""
from __future__ import annotations

import time
from typing import Any, Callable, TypeVar

__all__ = ["timed_call"]

_T = TypeVar("_T")


def timed_call(fn: "Callable[..., _T]", *args: Any, **kwargs: Any) -> "tuple[_T, float]":
    """Run ``fn(*args, **kwargs)`` and return ``(result, elapsed_seconds)``
    — a 2-tuple, never a merged mapping. ``result`` is EXACTLY what ``fn``
    returned, untouched; ``elapsed_seconds`` (``time.perf_counter()``
    delta) is for logging/reporting ONLY — a caller MUST NOT fold it into
    ``result`` before digesting, comparing, or recording it as a
    conformance vector's own expected value.
    """
    start = time.perf_counter()
    result = fn(*args, **kwargs)
    elapsed = time.perf_counter() - start
    return result, elapsed
