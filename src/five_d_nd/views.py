# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""Derived views and staleness — spec/SPEC.md §15 (build list item 1/3).

``position``, ``match_statistic``, ``d`` and ``nesting_level`` are all
VIEWS (the concept's own derivation-ledger model —
not itself part of this architecture; the container-average/trimmed-top-k
rule and "depth is derived from the graph" are two of the things these
views compute, not the "they are all views" architecture itself): each
carries a
``position_digest`` (:func:`position_digest` — over the contributing
claim-ids, the embeds edges that fed it, and the resolution-profile digest,
§15), a ``basis`` and a ``stale`` flag (:func:`make_view`).

**Staleness propagation.** When a leaf claim or embeds edge changes, every
node whose view was built FROM it goes stale, and so does every ANCESTOR of
that node on EVERY branch of the containment DAG — :func:`propagate_staleness`
returns an ORDERED LIST, in a TRUE topological order of the affected
sub-DAG (replacing an earlier unordered ``set``): a full Kahn's-algorithm
pass restricted to
the "affected" region (every node reachable from ``changed`` via the
reverse embeds index), where a node becomes ready only once EVERY ONE of
its OWN children that is itself affected has already been emitted — never
merely "at least one". Ties among simultaneously-ready nodes break on
lexicographic node-id order (a min-heap), so the result is fully
deterministic. A DIAMOND DAG (two paths from the changed node up to a
common ancestor) marks that ancestor exactly ONCE, and strictly AFTER both
of its converging branches — the function's own membership bookkeeping is
what prevents double counting, and the full Kahn pass is what proves the
"no double counting" property as part of a genuine topological order
rather than merely a dedup side effect.

**Re-derivation order, specified.** A re-deriver MUST
process :func:`propagate_staleness`'s own returned list IN ORDER,
front-to-back: by construction, every node in the list is preceded by ALL
of its own affected children, so re-deriving in list order guarantees a
node's own members/contributors are already re-derived (or were never
stale to begin with) by the time that node itself is re-derived — a
re-deriver MUST NOT re-derive a node before every element preceding it in
this list has been re-derived.

**Two staleness tiers** (the concept's own build list item 3; a separate
design choice, not a change to the derivation-ledger architecture above):

- ``"erasure"`` is a HARD FENCE (:func:`is_erasure_fenced`): a view fenced
  this way MUST NOT be served under any basis until re-derived, and that
  re-derivation MUST be BIT-IDENTICAL to a baseline that never contained the
  erased leaf — :func:`erasure_bit_identical` is the literal equality check
  a conformance vector exercises (full erasure MECHANICS — the hash-chained
  serving log, salt shredding — are STAGE 2 of this round's two-stage
  build, per the task; this module specifies only the bit-identity
  REQUIREMENT itself and the fence it gates).
- ``"ingest"`` is a BOUNDED WINDOW (:func:`ingest_stale_window`): the last
  good view may be served WITH its digest and age attached, for as long as
  ``age <= staleness_window_seconds`` (a resolution-profile field, §16);
  past the window it is no longer servable and MUST be re-derived before
  being served again.

**Hub fan-out debounce** (:func:`debounce`): a hub entry whose incoming
staleness-triggering events arrive faster than they can be re-derived is
COALESCED into bounded-rate propagation events (one fired per ``threshold``
events inside a rolling ``window_seconds``) rather than firing one
propagation per event — this is what keeps staleness from becoming
PERMANENT under a steady high-fanout ingest stream (the concept's own
red-team finding A(3)).

Stdlib only.
"""
from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from hashlib import sha256
from typing import Any

__all__ = [
    "STALENESS_TIERS",
    "VIEW_KINDS",
    "position_digest",
    "make_view",
    "view_violations",
    "is_valid_view",
    "propagate_staleness",
    "is_erasure_fenced",
    "erasure_bit_identical",
    "ingest_stale_window",
    "debounce",
]

#: The two staleness tiers (§15) — a CLOSED, fixed enum.
STALENESS_TIERS: tuple = ("erasure", "ingest")


def position_digest(
    contributing_claim_ids: Iterable[str],
    embeds_edges: Iterable[str],
    profile_digest: str,
) -> str:
    """A view's own ``position_digest`` (§15): sha256 over canonical JSON of
    the SORTED contributing claim-ids, the SORTED embeds edges that fed the
    view, and the resolution-profile digest (§16; ``five_d_nd.profile.
    profile_digest``) that pinned ``k``/``n_min``/``r``/the blend weights/
    the staleness window at the time this view was built. Any change to any
    one of the three inputs changes this digest — which is exactly what
    lets a caller detect staleness by comparing a stored digest against a
    freshly recomputed one, without re-deriving the view's VALUE itself.
    """
    canon = json.dumps(
        {
            "claims": sorted(contributing_claim_ids),
            "embeds": sorted(embeds_edges),
            "profile_digest": profile_digest,
        },
        sort_keys=True, separators=(",", ":"),
    )
    return sha256(canon.encode("utf-8")).hexdigest()


#: The closed set of the four derived view KINDS (§14/§15, fix round item 7)
#: — ``position``, ``match_statistic``, ``d`` and ``nesting_level`` are ALL
#: views; ``kind`` names WHICH one a given view record is.
VIEW_KINDS: tuple = ("position", "match_statistic", "d", "nesting_level")


def make_view(
    value: Any,
    *,
    kind: str,
    contributing_claim_ids: Iterable[str],
    embeds_edges: Iterable[str],
    profile_digest: str,
    basis: str,
    stale: bool = False,
    staleness_tier: str | None = None,
) -> dict:
    """Build one derived view record: ``{"value", "kind", "position_digest",
    "basis", "stale", "staleness_tier"}``. ``kind`` MUST be one of
    :data:`VIEW_KINDS` (fix round item 7 — every view now names which of
    the four view kinds it is). ``staleness_tier`` MUST be one of
    :data:`STALENESS_TIERS` when ``stale`` is True, and MUST be ``None``
    when ``stale`` is False (a view that isn't stale has no tier to report).
    """
    if kind not in VIEW_KINDS:
        raise ValueError(f"kind must be one of {VIEW_KINDS!r}, got {kind!r}")
    if stale and staleness_tier not in STALENESS_TIERS:
        raise ValueError(
            f"a stale view's staleness_tier must be one of {STALENESS_TIERS!r}, "
            f"got {staleness_tier!r}")
    if not stale and staleness_tier is not None:
        raise ValueError("a non-stale view must not carry a staleness_tier")
    return {
        "value": value,
        "kind": kind,
        "position_digest": position_digest(contributing_claim_ids, embeds_edges, profile_digest),
        "basis": basis,
        "stale": stale,
        "staleness_tier": staleness_tier,
    }


def view_violations(doc: Any) -> list:
    """Violations of a derived VIEW document's shape (fix round, item 7):
    mirrors :func:`make_view`'s own output shape and
    ``schema/view.schema.json``. ``kind`` MUST be one of :data:`VIEW_KINDS`;
    ``position_digest`` a non-empty string; ``basis`` a non-empty string;
    ``stale`` a plain bool; ``staleness_tier`` one of :data:`STALENESS_TIERS`
    when ``stale`` is true, else ``None``. ``value`` is unconstrained (its
    shape depends entirely on ``kind``). Returns ``[]`` when the document
    validates.
    """
    if not isinstance(doc, Mapping):
        return ["view must be a mapping"]
    out = []
    if "value" not in doc:
        out.append("view is missing 'value'")
    kind = doc.get("kind")
    if kind not in VIEW_KINDS:
        out.append(f"view 'kind' must be one of {VIEW_KINDS!r}, got {kind!r}")
    digest_value = doc.get("position_digest")
    if not isinstance(digest_value, str) or not digest_value:
        out.append(f"view 'position_digest' must be a non-empty string, got {digest_value!r}")
    basis_value = doc.get("basis")
    if not isinstance(basis_value, str) or not basis_value:
        out.append(f"view 'basis' must be a non-empty string, got {basis_value!r}")
    stale = doc.get("stale")
    if not isinstance(stale, bool):
        out.append(f"view 'stale' must be a bool, got {stale!r}")
        stale = None
    tier = doc.get("staleness_tier")
    if stale is True and tier not in STALENESS_TIERS:
        out.append(f"a stale view's staleness_tier must be one of {STALENESS_TIERS!r}, got {tier!r}")
    if stale is False and tier is not None:
        out.append("a non-stale view must not carry a staleness_tier")
    return out


def is_valid_view(doc: Any) -> bool:
    return view_violations(doc) == []


def propagate_staleness(
    reverse_embeds: Mapping[str, Iterable[str]], changed: Iterable[str],
) -> list:
    """Walk ``reverse_embeds`` (``reverse_embeds[node] = {every parent that
    directly embeds node}`` — ``five_d_nd.container.reverse_index``'s own
    output shape) outward from every node in ``changed``, returning an
    ORDERED LIST of every node id that becomes stale (every node in
    ``changed`` itself, plus every ancestor on every branch), in a TRUE
    topological order of the affected sub-DAG (module docstring).

    Algorithm: (1) find the full "affected" set — every node reachable
    from ``changed`` via ``reverse_embeds`` (a plain BFS, order
    irrelevant); (2) invert ``reverse_embeds`` within the affected set to
    get each affected node's own CHILDREN (its "embeds" targets) that are
    ALSO affected, and compute each node's in-degree as the COUNT of such
    children; (3) run Kahn's algorithm: every ``changed`` node starts at
    in-degree 0 (it has no affected children of its own — it IS the
    change); a node is emitted once ALL its affected children have been
    emitted; ties among simultaneously-ready nodes break on lexicographic
    node-id order (a min-heap), making the result fully deterministic.

    A node reachable via TWO OR MORE paths (a diamond DAG) is emitted
    EXACTLY ONCE — the "no double counting" guarantee (§15) — and strictly
    AFTER every one of its own affected children, which is what makes this
    a genuine topological order rather than merely a dedup side effect.
    """
    import heapq

    changed_list = list(dict.fromkeys(changed))  # dedup, preserve caller's own order
    affected: set = set(changed_list)
    frontier = list(changed_list)
    while frontier:
        nxt = []
        for node in frontier:
            for parent in reverse_embeds.get(node, ()):
                if parent not in affected:
                    affected.add(parent)
                    nxt.append(parent)
        frontier = nxt

    children_of: dict = defaultdict(set)
    for child, parents in reverse_embeds.items():
        for parent in parents:
            children_of[parent].add(child)

    remaining: dict = {
        node: len([c for c in children_of.get(node, ()) if c in affected])
        for node in affected
    }
    heap = [node for node in affected if remaining[node] == 0]
    heapq.heapify(heap)
    order: list = []
    while heap:
        node = heapq.heappop(heap)
        order.append(node)
        for parent in reverse_embeds.get(node, ()):
            if parent in affected:
                remaining[parent] -= 1
                if remaining[parent] == 0:
                    heapq.heappush(heap, parent)
    return order


def is_erasure_fenced(view: Mapping) -> bool:
    """True iff ``view`` is erasure-stale — a HARD FENCE: the view's own
    ``value`` MUST NOT be served (only placement-routing uses of a fenced
    node are permitted, per the concept's own serving-fence rule) until
    re-derived.
    """
    return bool(view.get("stale")) and view.get("staleness_tier") == "erasure"


def erasure_bit_identical(rederived_view: Mapping, never_contained_baseline: Mapping) -> bool:
    """The erasure hard fence's own NORMATIVE claim (§15): re-derivation
    after erasure MUST be bit-identical to a baseline that never contained
    the erased leaf. This function is the literal equality check — compares
    ONLY the ``"value"`` field (the position_digest of the two views will
    legitimately differ if their contributing-claim-id SETS differ in
    membership even though the folded VALUE is identical, e.g. a different
    claim-id was never-there vs. erased-then-gone; the bit-identity claim is
    about the materialised VALUE, not the bookkeeping digest around it).
    """
    return rederived_view.get("value") == never_contained_baseline.get("value")


def ingest_stale_window(view: Mapping, *, now: float, window_seconds: float) -> dict:
    """The ingest-stale bounded window (§15): returns ``view`` augmented
    with ``"age"`` (``now - view["as_of"]``) and ``"servable"`` (``age <=
    window_seconds`` — the boundary ``age == window_seconds`` IS servable,
    fix round item 6: the window is closed, inclusive, not open). ``view``
    MUST be a mapping carrying a numeric ``"as_of"`` timestamp (the time the
    last GOOD view was materialised); raises ``ValueError`` — never an
    uncaught ``KeyError``/``TypeError`` — when it is not (fix round item 6:
    ``ingest_stale_window({})`` must not crash).
    """
    if not isinstance(view, Mapping):
        raise ValueError(f"view must be a mapping, got {view!r}")
    as_of = view.get("as_of")
    if isinstance(as_of, bool) or not isinstance(as_of, (int, float)):
        raise ValueError(f"view must carry a numeric 'as_of' timestamp, got {as_of!r}")
    age = now - as_of
    return {**view, "age": age, "servable": age <= window_seconds}


def debounce(
    events: Sequence[tuple], *, window_seconds: float, threshold: int,
) -> list:
    """Hub fan-out debounce (§15): ``events`` is a sequence of ``(node_id,
    timestamp)`` pairs — one per staleness-triggering ingest event. Events
    for the SAME node are coalesced: within any rolling window of
    ``window_seconds``, at most one propagation event fires per
    ``threshold`` arrivals (a steady high-rate stream against one hub does
    not propagate once per arrival — only once per ``threshold``
    arrivals).

    **TRAILING-EDGE FLUSH, replacing an earlier silent drop.** An earlier
    implementation only counted a window that reached ``threshold``; any
    PARTIAL window — closed by a gap larger than ``window_seconds``, or
    simply the last window at the end of ``events`` — was discarded, except
    for a single whole-node fallback of "at least 1" regardless of how many
    separate partial windows actually occurred. Now EVERY window segment
    flushes exactly once when it CLOSES, whether it closed by reaching
    ``threshold`` (a coalesced burst) or by a gap/end-of-stream (a trailing
    remainder) — so a SLOW stream (every arrival more than
    ``window_seconds`` apart) propagates ONCE PER EVENT (each event is its
    own, immediately-closed window), and a stream that never reaches
    ``threshold`` at all still propagates its one remaining partial window
    exactly once, instead of being silently absorbed into a single
    whole-node fallback count.

    Returns ``[(node_id, coalesced_event_count), ...]`` — one entry per
    distinct node that had at least one event, with the number of
    propagation events it produced (always ``>= 1``).
    """
    if threshold <= 0:
        raise ValueError(f"threshold must be positive, got {threshold!r}")
    buckets: dict = defaultdict(list)
    for node_id, ts in events:
        buckets[node_id].append(ts)
    out = []
    for node_id, timestamps in buckets.items():
        timestamps = sorted(timestamps)
        window_start = None
        count_in_window = 0
        coalesced = 0
        for ts in timestamps:
            if window_start is None or (ts - window_start) > window_seconds:
                if count_in_window > 0:
                    coalesced += 1  # trailing-edge flush: the gap closed the old window
                window_start = ts
                count_in_window = 1
            else:
                count_in_window += 1
            if count_in_window >= threshold:
                coalesced += 1  # threshold reached: coalesced-burst flush
                window_start = None
                count_in_window = 0
        if count_in_window > 0:
            coalesced += 1  # trailing-edge flush: end of stream, flush the remainder
        out.append((node_id, coalesced))
    return out
