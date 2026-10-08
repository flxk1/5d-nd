# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""Containers (cubes) — spec/SPEC.md §13-14 (build list items 3-4).

A container has a stable id and a VERSIONED member set, digested
(:func:`member_set_digest`) — any edit to the member set is a new version, so
a view's own ``position_digest`` (``five_d_nd.views``) can cite this digest
as one of its contributing inputs. Nesting (a container embedding another
container) is an OPEN DAG: any container MAY nest any container, with no
depth cap (bounded only by compute).

**Cycle rejection, REPLACING this module's earlier
full-reachability-per-write guard.** The spec
REQUIRES, and this module now implements, an INCREMENTALLY MAINTAINED
topological order (Pearce-Kelly class), not a full-graph reachability check
on every write. The DAG is carried as ``{"children": {node: {child, ...}},
"order": {node: int}, "reverse": {node: {parent, ...}}, "next_order": int,
"prev_order": int}`` (:func:`empty_dag`; ``reverse`` is a persistently
maintained reverse-adjacency index; ``next_order``/``prev_order`` are the
next free order slot ABOVE/BELOW every value assigned so far, letting a
brand-new node's order be assigned in O(1) regardless of whether it plays
the parent or the child role — see :func:`add_nesting_edge` — so nothing
here is ever recomputed from scratch on a write).

**IN-PLACE, for the 1M-document scale target, REPLACING an earlier
structural-sharing-but-still-allocating version.** :func:`add_nesting_edge` now mutates the CALLER-OWNED
``dag`` record DIRECTLY — ``children``, ``reverse``, ``order`` and
``next_order`` are all updated in place, with NO top-level dict copy of
any kind. This makes the fast path TRULY O(1) bookkeeping (no allocation
at all, not even a cheap one), and a forced reorder costs exactly
O(affected region), never more. A caller who needs an ISOLATED, unaffected
COPY of a dag at some point in time — for comparison, for a test, or to
version/persist it — MUST take one explicitly via :func:`snapshot_dag`;
versioning and persistence are the CALLER's job (via snapshots or via
:func:`member_set_digest`-style content digests), never this module's own
concern. :func:`add_nesting_edge`:

  1. **Fast path** — if ``order[parent] < order[child]`` already, the edge
     is consistent with the existing order; add it, O(1), no traversal, no
     allocation.
  2. **Slow path** — otherwise, a BOUNDED forward DFS from ``child``
     (never past ``order[parent]``) finds the "reachable forward" set RF;
     if ``parent in RF``, the edge would CLOSE A CYCLE (``child`` already
     reaches ``parent``) — rejected, :class:`CycleError`, with the record
     LEFT UNCHANGED (the cycle check runs strictly BEFORE any mutation —
     see below). Otherwise a BOUNDED backward DFS from ``parent`` (never
     past ``order[child]``) finds the "reachable backward" set RB. The
     order VALUES already occupied by ``RB union RF`` are reassigned —
     RB's nodes first (each keeping ITS OWN relative order), then RF's
     nodes (same) — so the order stays a valid topological order with the
     new edge included.

Both traversals are bounded to the AFFECTED region between the two
endpoints' current order values — never the whole graph — which is what
makes this "incremental" rather than a global reachability check.

**Rejection leaves the record byte-for-byte unchanged — including for a
brand-new self-loop.** A cycle can only ever be CLOSED between two nodes
that BOTH already exist in ``order`` (a brand-new node has no edges yet,
so nothing can already reach it, and it cannot already reach anything) —
so :func:`add_nesting_edge` checks for a cycle, INCLUDING the
``parent == child`` self-loop case, BEFORE ensuring either node exists in
the record at all. A node is only inserted into ``children``/``reverse``/
``order`` once the write is known to succeed. This is what makes "a
rejected write must leave the record unchanged" true even for
``add_nesting_edge(dag, "X", "X")`` where ``"X"`` has never been seen
before — the record remains EXACTLY as it was, not merely unchanged in
its edges while gaining a now-orphaned node entry.

Container POSITION (§14) is the fixed-point average of its members' points
(``five_d_nd.fixedpoint``) — individual member points are KEPT, never
discarded. The MATCH KEY is a trimmed top-k over
OPERATIVE members (:func:`trimmed_top_k_match`): rank operative members by
weight descending, take the top ``k`` (a resolution-profile setting,
default 5, ``five_d_nd.profile``), average their points the same fixed-point
way, and break a rank tie by :func:`five_d_nd.fixedpoint.canonical_tiebreak_key`.
Below the small-n floor ``n_min`` (``n < n_min``, strict:
the boundary ``n == n_min`` DOES trim), trimming is skipped — EVERY
operative member counts, ranked the SAME way (so the result is
permutation-invariant in ``members``' own input order, not merely in
which members get selected).

A reverse membership/embeds index (:func:`reverse_index`) is the structure
``five_d_nd.views`` walks to propagate staleness to every container that
(directly or transitively) embeds a changed node.

Stdlib only.
"""
from __future__ import annotations

import json
import math
from collections.abc import Iterable, Mapping, Sequence
from hashlib import sha256
from typing import Any

from . import fixedpoint
from . import profile as _profile
from .position import DIMENSIONS

__all__ = [
    "CycleError",
    "member_set_digest",
    "empty_dag",
    "snapshot_dag",
    "reachable",
    "would_cycle",
    "add_nesting_edge",
    "reverse_index",
    "container_position",
    "trimmed_top_k_match",
    "trimmed_top_k_match_from_profile",
]


class CycleError(ValueError):
    """Raised when a nesting edge would close a cycle in the containment DAG."""


def member_set_digest(member_ids: Iterable[str], version: int) -> str:
    """The stable digest of a container's VERSIONED member set: sha256 over
    canonical JSON of the SORTED member ids plus the version number (BOTH
    inputs feed the digest — two member sets differing only in id content,
    at the SAME version, digest differently; the same member set at two
    DIFFERENT version numbers also digests differently). Any change to the
    member set (an id added or removed) MUST bump ``version`` — two
    different member sets at the same version number is a caller error
    this function has no way to detect by itself.
    """
    canon = json.dumps(
        {"members": sorted(member_ids), "version": version},
        sort_keys=True, separators=(",", ":"), ensure_ascii=True,
    )
    return sha256(canon.encode("utf-8")).hexdigest()


def empty_dag() -> dict:
    """A fresh, empty containment DAG: ``{"children": {}, "order": {},
    "reverse": {}, "next_order": 0}`` — the shape :func:`add_nesting_edge`
    MUTATES IN PLACE (this record is
    CALLER-OWNED, and every write lands directly in it). ``reverse`` is the
    PERSISTENTLY MAINTAINED reverse-adjacency index (``reverse[child] =
    {every parent that directly embeds child}``), updated incrementally
    alongside ``children`` so :func:`add_nesting_edge`'s slow path never
    rebuilds it from scratch (an O(E) scan) on every forced reorder;
    ``next_order`` is the next free order slot, tracked explicitly so
    assigning a new node's order never scans ``max(order.values())`` (an
    O(V) scan) either. A caller that already has a ``{"children",
    "order"}``-only dag (an earlier shape) can still pass it in —
    :func:`add_nesting_edge` derives ``reverse``/``next_order`` the first
    time it sees a dag missing them.

    A caller that needs an ISOLATED copy — unaffected by later writes to
    THIS dag — must take one explicitly via :func:`snapshot_dag`; this
    function's own return value is NOT such a copy of anything (it is a
    fresh, empty record), and no function in this module hands back an
    implicit snapshot as a side effect any more.
    """
    return {"children": {}, "order": {}, "reverse": {}, "next_order": 0, "prev_order": -1}


def snapshot_dag(dag: Mapping[str, Any]) -> dict:
    """An ISOLATED, deep-enough copy of a dag record: every one of
    ``children``'s and ``reverse``'s member SETS is copied
    (not merely the top-level mapping), so a later IN-PLACE write to the
    ORIGINAL ``dag`` (:func:`add_nesting_edge` now always mutates in
    place) can never be observed through a snapshot taken before that
    write. ``order`` and ``next_order`` are plain ints/a plain dict of
    ints, already immutable value types, so a shallow copy of ``order``
    is sufficient there.

    Versioning and persistence are the CALLER's job — via a snapshot
    taken at a point in time, or via
    :func:`member_set_digest`-style content digests over a container's own
    member set — never a concern this module's own write path carries.
    """
    return {
        "children": {k: set(v) for k, v in dag.get("children", {}).items()},
        "order": dict(dag.get("order", {})),
        "reverse": {k: set(v) for k, v in dag.get("reverse", {}).items()},
        "next_order": dag.get("next_order", 0),
        "prev_order": dag.get("prev_order", -1),
    }


def reachable(children: Mapping[str, Iterable[str]], start: str) -> set:
    """The set of nodes reachable from ``start`` by following ``children``'s
    edges (``children[node]`` = the set/iterable of ``node``'s children —
    the containers/entries it directly embeds), including ``start`` itself.
    Plain DFS over the WHOLE reachable region; ``children`` is never
    mutated. A general-purpose utility — NOT the function
    :func:`add_nesting_edge` itself uses for cycle rejection (that uses the
    bounded, order-aware traversal described in this module's own
    docstring); useful for cross-checking a DAG's own consistency in a
    test or conformance vector.
    """
    seen: set = set()
    stack = [start]
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        stack.extend(children.get(node, ()))
    return seen


def would_cycle(children: Mapping[str, Iterable[str]], parent: str, child: str) -> bool:
    """True iff adding the edge ``parent -> child`` (parent embeds child) to
    the PLAIN children-only graph ``children`` would close a cycle: either
    they are the same node (a self-loop), or ``parent`` is already
    reachable FROM ``child``. A full-reachability utility, independent of
    the order-aware incremental algorithm :func:`add_nesting_edge` itself
    uses — kept for cross-checking.
    """
    if parent == child:
        return True
    return parent in reachable(children, child)


def _bounded_forward(children: Mapping[str, Iterable[str]], order: Mapping[str, int],
                      start: str, ceiling: int) -> set:
    """DFS forward from ``start``, over ``children``, never visiting a node
    whose CURRENT order value exceeds ``ceiling`` — the affected region a
    Pearce-Kelly-class incremental update is bounded to. Includes
    ``start`` itself (its own order value is, by construction, always
    ``<= ceiling`` at every call site below).
    """
    seen: set = set()
    stack = [start]
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        for nxt in children.get(node, ()):
            if order.get(nxt, 0) <= ceiling and nxt not in seen:
                stack.append(nxt)
    return seen


def _bounded_backward(reverse: Mapping[str, Iterable[str]], order: Mapping[str, int],
                       start: str, floor: int) -> set:
    """DFS backward from ``start`` over the PERSISTENTLY MAINTAINED
    ``reverse`` adjacency (this does not rebuild a reverse index from
    ``children`` on every call, which would be an O(E) scan
    per forced reorder; ``reverse`` is now carried in the dag record
    itself and updated incrementally, see :func:`empty_dag`), never
    visiting a node whose CURRENT order value is below ``floor``. Includes
    ``start`` itself.
    """
    seen: set = set()
    stack = [start]
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        for prev in reverse.get(node, ()):
            if order.get(prev, 0) >= floor and prev not in seen:
                stack.append(prev)
    return seen


def add_nesting_edge(dag: dict, parent: str, child: str) -> dict:
    """Add the nesting edge ``parent -> child`` (parent embeds/nests child)
    to ``dag`` (the shape :func:`empty_dag` returns), maintaining a valid
    topological order INCREMENTALLY (this module's own docstring has the
    full algorithm).

    **MUTATES ``dag`` IN PLACE and returns the SAME object** — ``children``, ``reverse``, ``order`` and
    ``next_order`` are all updated directly, with NO top-level copy of any
    kind. A caller who needs an UNAFFECTED copy of ``dag`` from before this
    call — for a test, a comparison, or to version/persist a point in time
    — must take one explicitly, BEFORE calling this function, via
    :func:`snapshot_dag`.

    On REJECTION (:class:`CycleError`, naming both nodes), ``dag`` is left
    EXACTLY as it was — nothing is mutated, not even a brand-new node
    entry for a self-loop like ``add_nesting_edge(dag, "X", "X")`` where
    ``"X"`` was never seen before. This holds because a cycle can only
    ever be closed between two nodes that BOTH already exist (a brand-new
    node has no edges yet, so nothing can already reach it and it cannot
    already reach anything) — the cycle check therefore always runs
    BEFORE either node is inserted into the record, never after.

    Re-adding an edge that already exists is a no-op (idempotent),
    consistent with the existing order.

    **NOT thread-safe.** Two concurrent callers writing to the SAME ``dag``
    record may observe or produce an inconsistent order — a direct
    consequence of the in-place, no-copy design (§13). Serialising
    concurrent writers to the same record is the CALLER's responsibility.
    """
    # EVERY check (the self-loop check, and — below — the cycle check)
    # runs BEFORE any write to ``dag`` of any kind,
    # including a ``setdefault``-style key creation. Reads use ``.get()``
    # with a fallback, NEVER ``setdefault`` (which itself writes the key
    # into ``dag`` on a miss, even for a call that goes on to raise). A
    # rejected write — including ``add_nesting_edge({}, "x", "x")`` — must
    # therefore leave ``dag`` BYTE-IDENTICAL, never gaining an empty
    # "children"/"order"/"reverse" entry or a freshly initialised counter
    # it then never uses.
    if parent == child:
        raise CycleError(f"self-loop {parent!r} -> {child!r} would create a cycle")

    children: dict = dag.get("children", {})
    order: dict = dag.get("order", {})
    reverse: dict = dag.get("reverse", {})

    parent_exists = parent in order
    child_exists = child in order

    if parent_exists and child_exists:
        if child in children.get(parent, ()):
            return dag  # idempotent re-add; nothing to do, nothing to commit
        ub, lb = order[parent], order[child]
        if ub >= lb:
            rf = _bounded_forward(children, order, child, ub)
            if parent in rf:
                raise CycleError(
                    f"adding nesting edge {parent!r} -> {child!r} would create a cycle "
                    f"({child!r} already reaches {parent!r})")
            rb = _bounded_backward(reverse, order, parent, lb)
            affected = rb | rf
            slots = sorted(order[n] for n in affected)
            rb_sorted = sorted(rb, key=lambda n: order[n])
            rf_sorted = sorted(rf, key=lambda n: order[n])
            for slot, node in zip(slots, rb_sorted + rf_sorted):
                order[node] = slot
        # ub < lb: fast path, nothing to reorder. Either way, both nodes
        # already existed, so `order`/`children`/`reverse` are already the
        # REAL objects attached to `dag` — nothing further to commit.
    else:
        # At least one endpoint is brand new. A cycle is IMPOSSIBLE here (a
        # node with no prior edges can neither already reach anything nor
        # already be reachable), so no traversal is needed — this stays
        # O(1) by construction, never a bounded reorder, via two
        # monotonic counters instead of one: a brand-new CHILD (whether or
        # not its parent is also new) gets the NEXT-order slot, always
        # greater than every order value assigned so far, so it is
        # trivially AFTER any existing (or simultaneously newly assigned)
        # parent; a brand-new PARENT of an ALREADY-EXISTING child gets the
        # PREV-order slot, always LESS than every order value assigned so
        # far, so it is trivially BEFORE that child without needing to
        # know the child's own order value at all.
        # NOTE: deliberately NOT `dag.get("next_order", <fallback
        # expression>)` — a dict's own `.get()` evaluates its SECOND
        # argument EAGERLY, every single call, even when the key is
        # already present; that would silently reintroduce the O(V)
        # `max(order.values())`/`min(order.values())` scan on EVERY write
        # this module's own cost section promises is gone. The explicit
        # `if`/`else` below only ever evaluates the scan the ONE time the
        # key is genuinely absent.
        next_order = dag["next_order"] if "next_order" in dag else (
            (max(order.values()) + 1) if order else 0)
        prev_order = dag["prev_order"] if "prev_order" in dag else (
            (min(order.values()) - 1) if order else -1)
        if parent not in order:
            if child in order:
                order[parent] = prev_order
                prev_order -= 1
            else:
                order[parent] = next_order
                next_order += 1
        if child not in order:
            order[child] = next_order
            next_order += 1
        dag["next_order"] = next_order
        dag["prev_order"] = prev_order

    # The write is now known to succeed — only past this point does
    # anything else get committed into `dag`. Re-assigning an already-
    # identical object back onto its own key is a harmless no-op; this is
    # what attaches a FRESH `children`/`order`/`reverse` (one that started
    # life as `.get()`'s own fallback `{}`, never yet linked to `dag`)
    # when this call is the first write `dag` has ever seen.
    dag["children"] = children
    dag["order"] = order
    dag["reverse"] = reverse
    for node in (parent, child):
        if node not in children:
            children[node] = set()
        if node not in reverse:
            reverse[node] = set()
    children[parent].add(child)
    reverse[child].add(parent)
    return dag


def reverse_index(dag: Mapping[str, Any]) -> dict:
    """The reverse membership/embeds index: ``index[child] = {every parent
    that directly embeds child}`` — the structure staleness propagation
    (``five_d_nd.views.propagate_staleness``) walks outward from a changed
    node to every ancestor on every branch.

    When ``dag`` already carries a PERSISTED ``"reverse"`` key (the shape
    :func:`empty_dag`/:func:`add_nesting_edge` maintain), this is a cheap
    shallow copy of it, NOT an O(E) recomputation from
    ``children``. Falls back to a full ``children``-driven computation only
    for a dag that does not carry the persisted field (a plain children-only
    mapping, or the earlier ``{"children", "order"}``-only shape).
    """
    if isinstance(dag, Mapping) and "reverse" in dag:
        return {k: set(v) for k, v in dag["reverse"].items()}
    children = dag.get("children", dag) if isinstance(dag, Mapping) and "children" in dag else dag
    out: dict = {}
    for parent, kids in children.items():
        out.setdefault(parent, set())
        for child in kids:
            out.setdefault(child, set()).add(parent)
    return out


def container_position(member_points: Sequence[Mapping[str, float]]) -> dict:
    """The container's POSITION (§14): the fixed-point average of its
    members' points, one value per dimension, each rounded to 6 decimal
    places at THIS single materialisation step (``fixedpoint.fixed_mean``).
    Individual member points are not altered or discarded by this function
    — it returns only the derived average; a caller that wants "individual
    points kept" keeps ``member_points`` itself
    alongside this result.

    Raises ``ValueError`` on an EMPTY container (the named hard case: an
    empty container has no position, not an all-zero or all-neutral one —
    a caller must not invent a position for a container with zero members),
    on any member point that is not a mapping carrying a numeric,
    FINITE value for every one of the five dimensions (NaN/±inf are
    REJECTED — never silently folded into the mean), and
    goes through ``fixedpoint`` for the fold itself (NOT plain float
    summation) so the result does not depend on fold order even when the
    member points themselves are adversarially ordered to maximise float
    rounding drift.
    """
    n = len(member_points)
    if n == 0:
        raise ValueError("an empty container has no position (§14)")
    for i, p in enumerate(member_points):
        if not isinstance(p, Mapping):
            raise ValueError(f"member point at index {i} must be a mapping, got {p!r}")
        for d in DIMENSIONS:
            v = p.get(d)
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
                raise ValueError(
                    f"member point at index {i} is missing a finite numeric {d!r} value, got {v!r}")
    out = {}
    for d in DIMENSIONS:
        total = fixedpoint.fixed_sum(fixedpoint.to_fixed(float(p[d])) for p in member_points)
        out[d] = round(fixedpoint.from_fixed(fixedpoint.fixed_mean(total, n)), fixedpoint.PLACES)
    return out


def _rank_key(m: Mapping, salt: str) -> tuple:
    return (-float(m.get("weight", 0.0)), fixedpoint.canonical_tiebreak_key(str(m["claim_id"]), salt))


def trimmed_top_k_match(
    members: Sequence[Mapping[str, Any]], *, k: int, n_min: int, salt: str,
) -> dict:
    """The container's MATCH KEY (§14): a trimmed top-``k`` average over
    OPERATIVE members, ``k`` and ``n_min`` from the resolution profile
    (§16; ``k`` default 5).

    ``members`` is a sequence of ``{"claim_id": str, "weight": number,
    "point": {dim: value, ...}, "operative": bool}`` (``operative`` defaults
    ``True`` when absent — every member counts as operative unless marked
    otherwise; when PRESENT it MUST be an actual boolean). Operative
    members are ALWAYS rank-sorted by ``weight`` DESCENDING, ties broken by
    :func:`five_d_nd.fixedpoint.canonical_tiebreak_key` (ascending,
    salted) — this applies BELOW ``n_min`` too (the
    whole-set branch), so the result (``selected_claim_ids``' own ORDER) is
    permutation-invariant in ``members``' own input order, not merely which
    members are included. When the operative count ``n`` is STRICTLY BELOW
    ``n_min`` (``n < n_min`` — the boundary ``n == n_min`` DOES trim),
    trimming itself is skipped and EVERY operative member
    contributes (``effective_k = n``).

    Returns ``{"match_statistic": {dim: value, ...}, "selected_claim_ids":
    [str, ...]}`` — ``selected_claim_ids`` in rank order (ties broken as
    above), so a caller can audit exactly which members fed the statistic.

    Raises ``ValueError`` when there are no operative members at all (same
    "no position for an empty set" rule :func:`container_position` applies,
    specialised to the operative subset), when ``k`` or ``n_min`` is not a
    positive integer, when any member is not a mapping carrying a
    non-empty string ``claim_id``, a FINITE numeric ``weight`` (never a
    boolean, never NaN/±inf), and an ``operative`` value that is a plain
    ``bool`` when present — a malformed member is ALWAYS a ``ValueError``
    here, never an uncaught ``KeyError``/``TypeError``.
    """
    if not isinstance(k, int) or isinstance(k, bool) or k <= 0:
        raise ValueError(f"k must be a positive integer, got {k!r}")
    if not isinstance(n_min, int) or isinstance(n_min, bool) or n_min <= 0:
        raise ValueError(f"n_min must be a positive integer, got {n_min!r}")
    for i, m in enumerate(members):
        if not isinstance(m, Mapping):
            raise ValueError(f"member at index {i} must be a mapping, got {m!r}")
        claim_id = m.get("claim_id")
        if not isinstance(claim_id, str) or not claim_id:
            raise ValueError(f"member at index {i} must carry a non-empty string claim_id, got {claim_id!r}")
        weight = m.get("weight", 0.0)
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not math.isfinite(weight):
            raise ValueError(f"member {claim_id!r} weight must be a finite number, got {weight!r}")
        if "operative" in m and not isinstance(m["operative"], bool):
            raise ValueError(
                f"member {claim_id!r} 'operative' must be a bool when present, got {m['operative']!r}")
    operative = [m for m in members if m.get("operative", True)]
    n = len(operative)
    if n == 0:
        raise ValueError("no operative members; a container's match key needs at least one (§14)")
    ranked = sorted(operative, key=lambda m: _rank_key(m, salt))
    effective_k = n if n < n_min else min(k, n)
    selected = ranked[:effective_k]
    return {
        "match_statistic": container_position([m.get("point") for m in selected]),
        "selected_claim_ids": [m["claim_id"] for m in selected],
    }


def trimmed_top_k_match_from_profile(members: Sequence[Mapping[str, Any]], profile_doc: Mapping) -> dict:
    """Wires the RESOLUTION PROFILE (§16) directly into
    :func:`trimmed_top_k_match` — accepts a profile DOCUMENT (validated or
    not; call ``five_d_nd.profile.profile_violations`` first) rather than
    requiring every caller to unpack ``k``/``n_min``/``tiebreak_salt`` by
    hand. Resolves ``profile_doc`` against :data:`five_d_nd.profile.DEFAULTS`
    and calls :func:`trimmed_top_k_match` with the resolved fields.
    """
    resolved = _profile.resolve_profile(profile_doc)
    return trimmed_top_k_match(
        members, k=resolved["k"], n_min=resolved["n_min"], salt=resolved["tiebreak_salt"])
