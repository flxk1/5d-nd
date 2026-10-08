# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""The deterministic typed-Statement extractor (spec/SPEC.md §21-§23).

``extract(unit_text) -> list[Statement dict]``: pure stdlib, no ML, no
network, same input -> byte-identical output. See `extract.build` for the
pipeline, `extract.rules` for the closed predicate-cue table (written
from the codebook, never from gold), `extract.spans` for endpoint-span
finalisation, and `extract.negation` for the pluggable negation module
(`negation_v34` today).

The codebook and gold come FIRST (`five_d_nd.statement`'s own module
docstring); this package is the deterministic extractor built AGAINST
that already-fixed schema and codebook — it does not define either one.
"""
from __future__ import annotations

from .build import (
    BuiltStatement,
    ExtractionDiagnostics,
    build_statement,
    extract,
    extract_with_spans,
    layer_of,
    resolve_overlaps_built,
)
from .hybrid import (
    CacheKey,
    CacheMissError,
    CandidateSet,
    Decision,
    DecisionCache,
    assemble,
    decide,
    export_decision_requests,
    propose,
)
from .negation import DEFAULT_NEGATION_VERSION, NEGATION_RULES, negate, negation_v34, register_negation_rule
from .rules import CO_CODABLE_PREDICATE_PAIRS, RULE_CITATIONS, RULES, Candidate, Rule, collect_candidates
from .spans import finalize_endpoint_span, span_text, strip_determiner, strip_modal_prefix, trim_whitespace

__all__ = [
    "extract",
    "extract_with_spans",
    "BuiltStatement",
    "build_statement",
    "resolve_overlaps_built",
    "layer_of",
    "ExtractionDiagnostics",
    "negate",
    "negation_v34",
    "NEGATION_RULES",
    "DEFAULT_NEGATION_VERSION",
    "register_negation_rule",
    "RULES",
    "RULE_CITATIONS",
    "CO_CODABLE_PREDICATE_PAIRS",
    "Rule",
    "Candidate",
    "collect_candidates",
    "trim_whitespace",
    "strip_determiner",
    "strip_modal_prefix",
    "finalize_endpoint_span",
    "span_text",
    "CandidateSet",
    "propose",
    "Decision",
    "assemble",
    "CacheKey",
    "CacheMissError",
    "DecisionCache",
    "decide",
    "export_decision_requests",
]
