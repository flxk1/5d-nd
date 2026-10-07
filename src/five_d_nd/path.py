# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""Typed PATHS over §21 Statements — spec/SPEC.md §22.

Path composition is a STRICT LEFT-FOLD along the path's own edge order
(§3's existing normative rule, ``dimensions.left_fold`` — this module adds
NOTHING new to the fold itself). There is no bracketing freedom: a path has
a natural edge order (the order its own Statements were traversed in), and
the fold is evaluated strictly left to right over that order — never
re-associated, never run right-fold.

The fold STATE is the current composed dimension, one of the five (§2).
Search therefore runs over the PRODUCT GRAPH ``V × 5`` (every node paired
with every possible composed-dimension-so-far state), not over an
unbounded space of bracketings — this is what keeps typed-path search
POLYNOMIAL (Dijkstra/BFS over ``V × 5`` states and ``E`` transitions is
``O((V + E) log V)`` at most, never exponential in path length).

The confidence-floor cut (§16's ``confidence_floor`` field) is a STAGE 2
item, same status as §16 itself already states for that field: this module
defines the HOOK (:func:`confidence_floor_cut`) and threads an OPTIONAL
``floor`` parameter through the search function, but nothing here APPLIES
it by default (``floor=None`` is a no-op, matching §16's own "stored and
validated, not yet applied" status).

Stdlib only.
"""
from __future__ import annotations

import heapq
import math
from collections.abc import Mapping, Sequence
from itertools import count as _counter
from typing import Any, Optional

from .dimensions import Dimension, compose, compose_weights, left_fold

__all__ = [
    "fold_statements",
    "product_graph_state_count",
    "confidence_floor_cut",
    "typed_path_search",
    "composition_law_report",
]


def fold_statements(statements: Sequence[Mapping]) -> dict:
    """Left-fold a PATH of 1+ §21 Statements, in the order given (the
    caller's own edge order — this function performs NO reordering; see
    ``statement.sort_statements`` for the unrelated CANONICAL storage
    order, which is not a traversal order).

    Returns ``{"dimension": <composed>, "weight": <product>}``. The
    dimension composes via §3's left-fold (``dimensions.left_fold``); the
    weight composes MULTIPLICATIVELY (§3/§11's normative
    ``compose_weights``), over EACH statement's own ``weight`` field
    (defaulting to 1.0 when absent, matching §11's triple convention) — NOT
    ``edge_confidence``, which is a separate, SEPARATELY-composed quantity a
    caller tracks on its own terms (§21: the two fields were split
    precisely so one of them, ``weight``, has a stated composition algebra
    and the other does not need one imposed on it).

    Raises ``ValueError`` on an empty path, or on any statement whose own
    ``weight`` field (when present) is not a finite number in ``[0, 1]`` —
    caught HERE, at the one place every caller's weight passes through,
    rather than silently propagating a NaN or an out-of-range product.
    """
    if not statements:
        raise ValueError("fold_statements() requires at least one statement")

    def _weight_of(s: Mapping) -> float:
        w = s.get("weight", 1.0)
        if isinstance(w, bool) or not isinstance(w, (int, float)) or not math.isfinite(w):
            raise ValueError(f"fold_statements(): statement weight must be a finite number, got {w!r}")
        if not (0.0 <= float(w) <= 1.0):
            raise ValueError(f"fold_statements(): statement weight must be in [0, 1], got {w!r}")
        return float(w)

    dims = [s["dimension"] for s in statements]
    composed_dim = left_fold(dims)
    weight = _weight_of(statements[0])
    for s in statements[1:]:
        weight = compose_weights(weight, _weight_of(s))
    return {"dimension": composed_dim.value, "weight": weight}


def product_graph_state_count(num_nodes: int) -> int:
    """The size of the product-graph state space a typed-path search runs
    over: every node paired with every one of the five composed-dimension
    states, ``|V| * 5`` — the bound that makes search POLYNOMIAL rather
    than exponential in path length (there is no per-length blow-up: the
    state space is fixed at ``5 * |V|`` regardless of how long a path
    gets).
    """
    if num_nodes < 0:
        raise ValueError("product_graph_state_count() requires num_nodes >= 0")
    return 5 * num_nodes


def confidence_floor_cut(weight: float, floor: Optional[float]) -> bool:
    """The §16/§21 confidence-floor HOOK — STAGE 2, defined but not applied
    by default. Returns ``True`` iff ``floor`` is given (not ``None``) AND
    ``weight`` falls strictly below it, i.e. the hop/path SHOULD be cut.
    ``floor=None`` always returns ``False`` (the no-op default, matching
    §16's own "stored and validated, never yet applied" status for
    ``confidence_floor``).
    """
    if floor is None:
        return False
    return float(weight) < float(floor)


def typed_path_search(
    adjacency: Mapping[str, Sequence[Mapping[str, Any]]],
    start: str,
    *,
    floor: Optional[float] = None,
) -> dict:
    """MAX-PRODUCT DIJKSTRA over the PRODUCT GRAPH ``V × 5`` from
    ``start``. A first-visit BFS is the WRONG algorithm here: it fixes a
    state's weight to whichever path reaches it FIRST in hop order, which
    is not necessarily the BEST-weight path to that state when edge
    weights differ; a lower-hop, lower-weight arrival could starve a
    higher-hop, higher-weight one that would otherwise clear a confidence
    floor. This function runs a Dijkstra instead, equivalent to a
    MIN-COST search where each edge's cost is ``-log(weight)`` (weights
    are in ``[0, 1]``, so every edge cost is non-negative — Dijkstra's own
    correctness precondition — and MULTIPLYING weights along a path is
    exactly ADDING their ``-log`` costs, so the max-weight path to a state
    is exactly the min-cost path to it).

    Takes an adjacency mapping ``{node_id: [{"target": node_id,
    "dimension": one-of-five, "weight": float}, ...]}``. Returns
    ``{(node_id, dimension): {"weight": <BEST, i.e. maximum, product
    weight to this state>, "hops": <edge count of that best path>}}`` for
    every state reached — a STATE is a ``(node, composed_dimension_so_far)``
    pair, never a bare node, because the SAME node reached via two
    different dimension histories is a DIFFERENT state for the purpose of
    this search (the fold state is exactly the composed dimension, §22).
    The starting state is ``(start, "relational")`` — ``relational`` is
    §3's own two-sided identity, so composing it with the FIRST real
    edge's dimension leaves that dimension unchanged, and the search needs
    no special "no dimension yet" sentinel.

    When a transition's OWN composed weight is cut by
    :func:`confidence_floor_cut`, that transition is never relaxed — the
    state it would have reached may still be reached via a DIFFERENT,
    un-cut path, but never via this one (the design decision: a boundary
    below the gate is left OUT, never given an invented weight — carried
    here as "an edge below the floor is not traversed on THIS path," not
    "an edge below the floor gets a smaller number" or "the state is
    unreachable by construction").
    """
    start_state = (start, Dimension.RELATIONAL.value)
    best: dict = {}
    finalized: set = set()
    tie = _counter()
    # heap item: (cost, tie_breaker, state, weight, hops) — cost = -log(weight),
    # so the heap pops the HIGHEST-weight (lowest-cost) frontier state first,
    # which is Dijkstra's own invariant: the first time a state is popped, its
    # weight is final (no better path to it remains in the heap).
    heap = [(0.0, next(tie), start_state, 1.0, 0)]
    while heap:
        cost, _, state, weight, hops = heapq.heappop(heap)
        if state in finalized:
            continue
        finalized.add(state)
        best[state] = {"weight": weight, "hops": hops}
        node, dim_so_far = state
        for edge in adjacency.get(node, ()):
            target = edge["target"]
            edge_dim = Dimension(edge["dimension"])
            edge_weight = float(edge.get("weight", 1.0))
            composed_dim = compose(Dimension(dim_so_far), edge_dim).value
            composed_weight = compose_weights(weight, edge_weight)
            if confidence_floor_cut(composed_weight, floor):
                continue
            new_state = (target, composed_dim)
            if new_state in finalized:
                continue
            new_cost = math.inf if composed_weight <= 0.0 else -math.log(composed_weight)
            heapq.heappush(heap, (new_cost, next(tie), new_state, composed_weight, hops + 1))
    return best


def composition_law_report() -> dict:
    """Verify, by exhaustive code (over every ordered triple/pair the
    5-dimension set admits), which algebraic laws §3's composition table
    ACTUALLY satisfies — spec/SPEC.md §22. This is the function
    ``conformance/vectors/composition-laws/``'s single vector is a frozen
    snapshot of; running it again against the SAME ``COMPOSITION_TABLE``
    MUST reproduce the identical report (the table is a fixed constant,
    §3 — this function has no randomness and no external input).

    Returns::

        {
          "identity_two_sided": bool,          # compose(d, R) == compose(R, d) == d, all d
          "idempotent": {dim: bool, ...},        # compose(d, d) == d
          "all_idempotent": bool,
          "commutative_failures": [[a, b], ...], # compose(a,b) != compose(b,a), ordered pairs
          "commutative_failure_count": int,      # len(commutative_failures); 25 - this = count agreeing
          "associative_failures": [[a, b, c, left, right], ...],
          "associative_failure_count": int,      # MUST be 2 per §3's own stated count
        }
    """
    dims = list(Dimension)
    identity_two_sided = all(
        compose(d, Dimension.RELATIONAL) == d and compose(Dimension.RELATIONAL, d) == d
        for d in dims
    )
    idempotent = {d.value: (compose(d, d) == d) for d in dims}

    commutative_failures = []
    for a in dims:
        for b in dims:
            if compose(a, b) != compose(b, a):
                commutative_failures.append([a.value, b.value])

    associative_failures = []
    for a in dims:
        for b in dims:
            for c in dims:
                left = compose(compose(a, b), c)
                right = compose(a, compose(b, c))
                if left != right:
                    associative_failures.append([a.value, b.value, c.value, left.value, right.value])

    return {
        "identity_two_sided": identity_two_sided,
        "idempotent": idempotent,
        "all_idempotent": all(idempotent.values()),
        "commutative_failures": commutative_failures,
        "commutative_failure_count": len(commutative_failures),
        "associative_failures": associative_failures,
        "associative_failure_count": len(associative_failures),
    }
