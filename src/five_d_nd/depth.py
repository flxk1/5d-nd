# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""Conceptual depth ``d`` — spec/SPEC.md §14.

**The design decision this module implements** (quoted): "Conceptual
depth d is continuous in [0,1]. It is a blend of: the original link
signals (incoming links from other concepts push towards deep;
plain-language/sense anchors push towards surface); the entry's
relative position in the nesting. d is computed only from the
neighbourhood within radius r (default 2). The blend weights and r are
resolution-profile settings."

``d`` carries NO universal distinctness guarantee — it is deterministic
in the radius-r signal tuple, equal tuples give equal d, and d is
monotone per signal. Nesting position is counted within r hops.
``x/(x+s)`` is the chosen monotone map (see "Formula", below). An
earlier version of this module enforced a universal-distinctness rule
("non-automorphic entries MUST get different d"), coming from an
earlier design concept's own red-team concession (Candidate B(5)) — a
count-based ``d`` cannot satisfy that rule in general, so it and the
automorphism machinery that tried to approximate it are REMOVED from
this module.

``d`` is continuous in ``[0, 1]``, a BLEND of two signals, computed from an
ACTUAL graph neighbourhood — the signal functions below take a graph (or
the containment DAG), an entry id, and ``r`` itself, not pre-computed
counts a caller could supply without ever consulting ``r``:

1. **Link signal** (``topo_depth = min(bridge_in_degree/5, 1)`` in an
   earlier design): incoming
   links FROM OTHER CONCEPTS push toward DEEP; plain-language/sense ANCHOR
   links push toward SURFACE, damping the deep pull. Both are counted as
   the SIZE of the radius-``r`` BACKWARD-reachable neighbourhood
   (:func:`concept_link_signal` / :func:`anchor_link_signal`) — the count
   of DISTINCT predecessor nodes reached by following that kind of edge
   backward from the entry, up to ``r`` hops, excluding the entry itself.
   This is what makes ``r`` OPERATIVE (a predecessor more than ``r`` hops
   away is never counted — an edit OUTSIDE the radius-``r`` neighbourhood
   therefore leaves the count, and so ``d``, UNCHANGED; an edit INSIDE it
   changes the count) and LOCAL (bounded strictly to the neighbourhood, not
   the whole graph).
2. **Nesting signal — LOCAL** (replacing an earlier, UNBOUNDED version).
   The entry's RELATIVE position in the containment
   nesting (§13/§14 — "the entry's relative
   position in the nesting... computed only from the neighbourhood within
   radius r"): :func:`nesting_relative_position` = ``ancestors_within_r /
   (ancestors_within_r + descendants_within_r)`` — counting ancestors and
   descendants ONLY within ``r`` hops of the entry in the containment DAG
   (an earlier version of this function counted the FULL, unbounded
   ancestor/descendant sets, which made the nesting signal — unlike the
   link signals above — insensitive to ``r`` entirely; an edit beyond
   ``r`` hops away in the containment DAG could still change it). ``0.0``
   when both counts are zero (an isolated node, or one with no
   ancestors/descendants within ``r`` hops at all — there is no "position"
   to report); the range is `[0, 1]` INCLUSIVE at both ends (corrected
   from an earlier, wrong "(0, 1)" open-interval
   claim): `1.0` for a leaf-like node within the radius (ancestors only,
   no descendants within `r` hops). Uncapped by any absolute depth
   constant.

**Formula.** The earlier ``min(count/saturation, 1)`` squash is replaced
with ``x/(x+s)``, STRICTLY MONOTONE on ``x >= 0`` for any fixed, positive ``s``
(property (iii) below):

    deep_pull    = incoming_concept_links / (incoming_concept_links + link_scale)
    surface_pull = anchor_links           / (anchor_links + anchor_scale)
    raw_depth    = deep_pull * (1 - surface_pull)
    nest_signal  = nesting_relative_position(dag, entry_id, r)     # already in [0, 1]
    d = clamp01(round(
          (w_links * raw_depth + w_nesting * nest_signal) / (w_links + w_nesting),
          6))

``link_scale``, ``anchor_scale``, ``w_links``, ``w_nesting`` and ``r`` are
ALL resolution-profile fields (§16; the profile's own field names,
``link_saturation``/``anchor_saturation``, are UNCHANGED — only their
ROLE changes, from a saturation cutoff to the monotone map's scale
constant ``s`` — so no profile document needs editing for this fix).
Defaults: 5, 2, 0.5, 0.5, 2 — the SAME values as before.

**The four properties ``d`` actually has**, REPLACING
the earlier "non-automorphic entries get different d" rule, which came
from an earlier design concept, and which a count-based ``d`` cannot
satisfy in general:

  (i)   ``d`` is a DETERMINISTIC function of the radius-``r`` signal tuple
        ``(incoming_concept_links, anchor_links, ancestors_within_r,
        descendants_within_r)`` (plus the profile parameters) — no hidden
        state, no randomness.
  (ii)  EQUAL signal tuples (at the same profile parameters) give EQUAL
        ``d`` — trivially true of any deterministic function, stated here
        because the OLD automorphism rule conflated this with something
        stronger (see (iv)).
  (iii) ``d`` is MONOTONE in each signal: non-decreasing in
        ``incoming_concept_links``, non-increasing in ``anchor_links``,
        and non-decreasing in ``nest_signal`` (hence in the entry's
        relative nesting position) — each holds because ``x/(x+s)`` is
        monotone non-decreasing in ``x`` for fixed positive ``s``, and the
        blend is a non-negative-weighted sum of monotone terms.
  (iv)  **NO INJECTIVITY GUARANTEE ACROSS DIFFERENT TUPLES — a KNOWN,
        STATED LIMITATION, not a defect.** Two DIFFERENT signal tuples MAY
        still produce the SAME ``d`` (the blend can let a change in one
        signal compensate a change in another, and the underlying counts
        are a many-to-one SUMMARY of a richer graph neighbourhood to begin
        with). This specification makes NO claim that ``d`` distinguishes
        every non-automorphic graph position — that claim, which an
        earlier design concept's own red-team already conceded could not hold in
        general (Candidate B(5)), is WITHDRAWN. `conformance/vectors/depth/`
        includes vectors that EXHIBIT two genuinely different signal
        tuples/graph shapes sharing the same ``d`` (properties (ii)/(iv))
        alongside the locality and monotonicity vectors ((i)/(iii)).

**Depth quantiles inside a cube** (IMPLEMENTED, not
merely asserted): :func:`depth_quantiles` reports the quantile rank of
each member's own ``d`` within its container's member set — `nesting_level`
and `d` stay SEPARATE fields (§14); this function is how a cube REPORTS
``d`` internally, never a redefinition of ``d`` itself.

Stdlib only.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping

from . import profile as _profile
from .container import reverse_index

__all__ = [
    "DEFAULT_LINK_SCALE",
    "DEFAULT_ANCHOR_SCALE",
    "DEFAULT_W_LINKS",
    "DEFAULT_W_NESTING",
    "DEFAULT_RADIUS",
    "concept_link_signal",
    "anchor_link_signal",
    "nesting_relative_position",
    "conceptual_depth",
    "conceptual_depth_from_profile",
    "depth_quantiles",
]

#: The monotone map's scale constants (the profile's own field names,
#: ``link_saturation``/``anchor_saturation``, are unchanged — see this
#: module's own docstring).
DEFAULT_LINK_SCALE = 5
DEFAULT_ANCHOR_SCALE = 2
DEFAULT_W_LINKS = 0.5
DEFAULT_W_NESTING = 0.5
DEFAULT_RADIUS = 2
_PLACES = 6


def _bfs_bounded_count(adjacency: Mapping[str, Iterable[str]], start: str, r: int) -> int:
    """The count of DISTINCT nodes reached by following ``adjacency``
    (``adjacency[node]`` = node's DIRECT neighbours in the traversal
    direction this call represents — predecessors for a backward walk,
    children for a forward walk) from ``start``, up to ``r`` hops,
    EXCLUDING ``start`` itself. This is what makes ``r`` operative: a node
    more than ``r`` hops away is never visited, so it never contributes to
    the count, and an edit made entirely outside this bounded walk cannot
    change the result.
    """
    if r <= 0:
        return 0
    seen = {start}
    frontier = [start]
    for _ in range(r):
        nxt = []
        for node in frontier:
            for nbr in adjacency.get(node, ()):
                if nbr not in seen:
                    seen.add(nbr)
                    nxt.append(nbr)
        frontier = nxt
        if not frontier:
            break
    return len(seen) - 1


def concept_link_signal(graph: Mapping, entry_id: str, r: int) -> int:
    """Incoming-concept-link signal (this module's own docstring, point 1):
    the size of the radius-``r`` backward neighbourhood of ``entry_id``
    over ``graph["concept_links"]`` (``concept_links[target] = [direct
    predecessor id, ...]`` — incoming links FROM OTHER CONCEPTS).
    """
    adjacency = graph.get("concept_links", {})
    return _bfs_bounded_count(adjacency, entry_id, r)


def anchor_link_signal(graph: Mapping, entry_id: str, r: int) -> int:
    """Anchor-link signal (plain-language/sense anchors): the size of the
    radius-``r`` backward neighbourhood of ``entry_id`` over
    ``graph["anchor_links"]`` (same shape as ``concept_links``).
    """
    adjacency = graph.get("anchor_links", {})
    return _bfs_bounded_count(adjacency, entry_id, r)


def nesting_relative_position(dag: Mapping, entry_id: str, r: int) -> float:
    """The entry's RELATIVE position in the containment nesting, counted
    ONLY within ``r`` hops (the design decision requires "computed only
    from the neighbourhood within radius r", which an EARLIER, unbounded
    version of this function did not honour):
    ``ancestors_within_r / (ancestors_within_r + descendants_within_r)``
    over ``dag``'s own ``"children"`` mapping
    (:func:`five_d_nd.container.empty_dag`'s shape). The range is
    ``[0, 1]`` INCLUSIVE at both ends (corrected from an earlier, wrong
    "strictly between 0 and 1" claim): ``0.0`` for
    a root-like node within the radius (descendants only, or no
    ancestors/descendants within ``r`` hops at all — an isolated node has
    no "position" to report, and also gets ``0.0``); ``1.0`` for a
    leaf-like node within the radius (ancestors only, no descendants
    within ``r`` hops). NEVER saturated by an absolute depth constant
    beyond the radius bound itself — the containment DAG's OWN nesting
    stays uncapped; only the NEIGHBOURHOOD this
    signal reads from ``r`` hops is bounded.
    """
    children = dag.get("children", dag) if isinstance(dag, Mapping) and "children" in dag else dag
    # Read the dag's own PERSISTED reverse index when
    # present (an O(1) shallow copy via reverse_index()), never an O(E)
    # from-scratch recomputation.
    rev = reverse_index(dag) if isinstance(dag, Mapping) and "children" in dag else reverse_index({"children": children})
    descendants_within_r = _bfs_bounded_count(children, entry_id, r)
    ancestors_within_r = _bfs_bounded_count(rev, entry_id, r)
    total = ancestors_within_r + descendants_within_r
    if total <= 0:
        return 0.0
    return ancestors_within_r / total


def _monotone(x: float, s: float) -> float:
    if s <= 0:
        raise ValueError(f"scale constant must be positive, got {s!r}")
    if x < 0:
        raise ValueError(f"signal count must be non-negative, got {x!r}")
    return x / (x + s)


def conceptual_depth(
    graph: Mapping,
    dag: Mapping,
    entry_id: str,
    *,
    r: int = DEFAULT_RADIUS,
    link_saturation: float = DEFAULT_LINK_SCALE,
    anchor_saturation: float = DEFAULT_ANCHOR_SCALE,
    w_links: float = DEFAULT_W_LINKS,
    w_nesting: float = DEFAULT_W_NESTING,
) -> float:
    """Conceptual depth, computed from an ACTUAL graph neighbourhood
    (``graph`` — ``concept_links``/``anchor_links``) and the containment
    DAG (``dag``), for ``entry_id``, within radius ``r`` (this module's own
    docstring has the full formula and the four properties (i)-(iv) it
    satisfies). ``link_saturation``/``anchor_saturation`` keep their
    PROFILE field names (§16) but are now the strictly monotone map's
    scale constants, not a saturation cutoff.

    Raises ``ValueError`` when ``r`` is not a non-negative integer, when
    either scale constant is not positive, or when ``w_links + w_nesting``
    is not positive (a profile with both blend weights at 0 cannot define
    a depth at all).
    """
    if not isinstance(r, int) or isinstance(r, bool) or r < 0:
        raise ValueError(f"r must be a non-negative integer, got {r!r}")
    total_w = w_links + w_nesting
    if total_w <= 0:
        raise ValueError("w_links + w_nesting must be positive")
    incoming = concept_link_signal(graph, entry_id, r)
    anchors = anchor_link_signal(graph, entry_id, r)
    deep_pull = _monotone(incoming, link_saturation)
    surface_pull = _monotone(anchors, anchor_saturation)
    raw_depth = deep_pull * (1.0 - surface_pull)
    nest_signal = nesting_relative_position(dag, entry_id, r)
    d = (w_links * raw_depth + w_nesting * nest_signal) / total_w
    return round(min(max(d, 0.0), 1.0), _PLACES)


def depth_quantiles(member_depths: Mapping[str, float]) -> dict:
    """Depth quantiles inside a cube: given
    ``{claim_id: d, ...}`` for a container's own members, returns
    ``{claim_id: quantile}`` where ``quantile`` is each member's own rank
    among the set, normalised to ``[0, 1]`` (``0.0`` for the shallowest
    member, ``1.0`` for the deepest; a single member gets ``0.0``). Ties in
    ``d`` share the SAME quantile (the LOWEST rank among the tied group —
    "at least this shallow"), computed deterministically by sorting on
    ``(d, claim_id)`` for a stable tie order before assigning ranks.
    ``nesting_level`` and ``d`` stay separate fields (§14) — this function
    is purely a REPORTING transform over already-computed ``d`` values,
    never a redefinition of ``d`` itself.

    Raises ``ValueError`` on an empty ``member_depths`` (no quantiles to
    report for an empty container, matching :func:`five_d_nd.container.
    container_position`'s own empty-container rule).
    """
    if not member_depths:
        raise ValueError("an empty container has no depth quantiles (§14)")
    items = sorted(member_depths.items(), key=lambda kv: (kv[1], kv[0]))
    n = len(items)
    if n == 1:
        return {items[0][0]: 0.0}
    rank_by_claim: dict = {}
    i = 0
    while i < n:
        j = i
        while j + 1 < n and items[j + 1][1] == items[i][1]:
            j += 1
        quantile = round(i / (n - 1), _PLACES)
        for k in range(i, j + 1):
            rank_by_claim[items[k][0]] = quantile
        i = j + 1
    return rank_by_claim


def conceptual_depth_from_profile(graph: Mapping, dag: Mapping, entry_id: str, profile_doc: Mapping) -> float:
    """Wires the RESOLUTION PROFILE (§16) directly into
    :func:`conceptual_depth` — accepts a profile DOCUMENT (validated or
    not; this function does not itself validate it, call
    ``five_d_nd.profile.profile_violations`` first) rather than requiring
    every caller to unpack ``r``/``link_saturation``/``anchor_saturation``/
    the blend weights by hand. Resolves ``profile_doc`` against
    :data:`five_d_nd.profile.DEFAULTS` (:func:`five_d_nd.profile.
    resolve_profile`) and calls :func:`conceptual_depth` with the resolved
    fields.
    """
    resolved = _profile.resolve_profile(profile_doc)
    return conceptual_depth(
        graph, dag, entry_id,
        r=resolved["r"],
        link_saturation=resolved["link_saturation"],
        anchor_saturation=resolved["anchor_saturation"],
        w_links=resolved["d_blend_weights"]["links"],
        w_nesting=resolved["d_blend_weights"]["nesting"],
    )
