# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""The hybrid, REPLAYABLE extractor: deterministic stdlib code proposes;
a pinned model DECIDES; every model answer is cached and replayed,
never recomputed from the model at run time.

Three stages, matching the brief exactly:

1. **`propose(unit_text, enclosing_provision=None) -> CandidateSet`**
   (deterministic, stdlib, RECOMPUTED every time, recall-oriented): the
   segmenter's own clause/list-item spans with chapeau inheritance, the
   segmenter's own `np_chunks`, and EVERY candidate Statement the closed
   cue-rule table (`extract.rules.collect_candidates`) produces per
   LEAF clause/list-item span — with NO first-claim pruning (unlike
   `extract.build`'s own pipeline, which resolves overlap; a
   `CandidateSet` keeps every candidate, multiple per clause, each
   carrying its own `rule_id` and codebook citation). Canonical JSON,
   sha256-addressed.
2. **`decide(...) -> Decision`** (recorded once externally, replayed
   here): NEVER calls a model inside this package — `mode="replay"`
   (the default) reads a `DecisionCache` entry keyed by
   `CacheKey(candidate_set_sha, coder_view_sha, model_id,
   prompt_template_sha)`; a cache miss raises `CacheMissError`, never a
   silent fallback. `mode="record"` raises `NotImplementedError` here —
   recording a real Decision is external tooling (reviewers answering
   `export_decision_requests`' own output files), deliberately kept OUT
   of this package (no API key lives here).
3. **`assemble(candidate_set, decision, ...) -> list[dict]`**
   (deterministic): a Decision's own span adjustment, or an ADDED
   Statement's own span, is accepted ONLY when it is a span ALREADY
   PRESENT in the `CandidateSet` (a clause span, an NP chunk, or a
   candidate's own subj/obj endpoint) — `allowed_spans()` is the
   enforced set; anything else raises `ValueError`. Every assembled
   Statement's own `extraction_rule_id` records BOTH the candidate's
   own rule and the Decision's own cache key:
   `"<rule_id>|model-decision:<cache_key>"`.

Determinism (the spec change this round drafts, in
`docs/decisions/0012-hybrid-replayable-extractor.md` and its own sibling
spec-text-patch file — NEVER applied to `spec/SPEC.md` itself by this
session): extraction is deterministic BY REPLAY, not by recomputation
alone — the SAME inputs AND the SAME cache give byte-identical output;
`propose()`/`assemble()` alone are still pure recomputation, exactly as
§23 already requires.

Stdlib only. Imports `five_d_nd.statement` and this package's own
`rules`/`segment`/`spans` (all read-only).
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .. import statement as _statement
from . import build as _build
from . import rules as _rules
from . import segment as _segment
from . import spans as _spans

__all__ = [
    "SCHEMA_VERSION",
    "CandidateSet",
    "propose",
    "allowed_spans",
    "Decision",
    "assemble",
    "assemble_with_spans",
    "CacheKey",
    "CacheMissError",
    "DecisionCache",
    "decide",
    "import_decisions",
    "export_decision_requests",
    "PROMPT_TEMPLATE_V1",
    "PROMPT_TEMPLATE_V1_SHA256",
    "DECISION_JSON_SCHEMA",
    "decision_schema_violations",
]

SCHEMA_VERSION = "t3-hybrid-v1"

#: Bumped because `CandidateSet`'s own payload shape changes
#: (a new `extra_allowed_spans` field, and candidates with an explicit
#: inherited subject span now appear alongside the originals): a
#: Decision recorded against a v1 `CandidateSet` would otherwise be
#: silently replayed against a DIFFERENT v2 `CandidateSet` whose own
#: sha256 happens to collide in no practical scenario, but whose own
#: CONTENT differs — this field makes the version explicit in the
#: payload itself, not only implied by the sha256 changing. Recorded
#: Decisions are expected to be RE-RECORDED against the new
#: CandidateSets.
CANDIDATE_SET_VERSION = "v2"


def _canonical_json(obj) -> str:
    """Canonical JSON: sorted keys, `','`/`': '` separators, no
    surrounding whitespace, UTF-8 text (never ``ensure_ascii`` — a
    curly quote or em dash stays itself, not a `\\uXXXX` escape, so the
    hash is stable across an `ensure_ascii` default change)."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ": "))


def _sha256_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ─────────────────────────── stage 1: propose() ──────────────────────────

@dataclass(frozen=True)
class CandidateSet:
    """The deterministic stage's own full output — RECALL-oriented, no
    pruning. ``segments`` is `extract.segment.segment`'s own FULL flat
    list (every `sentence`/`chapeau`/`clause`/`list_item` node, with its
    own `parent`/`inherits_subject_from` index — the decider needs the
    containers, not only the leaves, to resolve chapeau inheritance
    itself). ``np_chunks`` is `extract.segment.np_chunks`'s own list of
    ``{"start", "end"}`` spans. ``candidates`` is one dict per candidate
    Statement `extract.rules.collect_segmented_candidates` produced
    (the SAME function the non-hybrid pipeline uses — round-6 fix:
    this now INCLUDES chapeau-inherited candidates, not only each leaf
    span's own direct cue matches), UNRESOLVED (no overlap pruning,
    multiple per clause): ``{"id", "rule_id", "citation", "predicate",
    "clause_span", "subj_span", "obj_span", "base_confidence",
    "negation_force", "chapeau_group"}`` — ``chapeau_group``, when not
    ``None``, marks a set of candidates that share ONE inherited
    chapeau subject and should never be treated as mutually
    conflicting (the same mechanism `extract.build`'s own overlap
    resolution uses).

    ``extra_allowed_spans`` is a FOURTH source
    `allowed_spans()` draws from, alongside ``segments``/``np_chunks``/
    each candidate's own spans — `extract.segment.clean_np_chunks()`,
    `coordinated_subject_conjuncts()`, `smallest_complete_clause_spans()`
    and `inherited_subject_spans()`'s own values, pooled. ADDITIVE ONLY:
    every v1 allowed span is still an allowed span; this only widens the
    pool — existing allowed spans are never removed."""
    unit_text: str
    enclosing_provision: "Optional[str]"
    segments: "tuple[dict, ...]"
    np_chunks: "tuple[dict, ...]"
    candidates: "tuple[dict, ...]"
    extra_allowed_spans: "tuple[dict, ...]" = ()

    def to_canonical_dict(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "candidate_set_version": CANDIDATE_SET_VERSION,
            "unit_text": self.unit_text,
            "enclosing_provision": self.enclosing_provision,
            "segments": list(self.segments),
            "np_chunks": list(self.np_chunks),
            "candidates": list(self.candidates),
            "extra_allowed_spans": list(self.extra_allowed_spans),
        }

    def to_canonical_json(self) -> str:
        return _canonical_json(self.to_canonical_dict())

    @property
    def sha256(self) -> str:
        return _sha256_of(self.to_canonical_json())

    @classmethod
    def from_canonical_dict(cls, d: dict) -> "CandidateSet":
        return cls(
            unit_text=d["unit_text"], enclosing_provision=d.get("enclosing_provision"),
            segments=tuple(d["segments"]), np_chunks=tuple(d["np_chunks"]),
            candidates=tuple(d["candidates"]),
            extra_allowed_spans=tuple(d.get("extra_allowed_spans", ())),
        )


def propose(unit_text: str, *, enclosing_provision: "Optional[str]" = None) -> CandidateSet:
    """The hybrid extractor's own deterministic, recall-oriented first
    stage. Recomputed every time — never cached, never model-dependent.

    Candidates come from `extract.rules.
    collect_segmented_candidates` — the SAME function `extract.build`'s
    own non-hybrid pipeline uses — rather than a hand-rolled per-span
    loop calling `collect_candidates` directly. The earlier hand-rolled
    version silently DROPPED the chapeau-inheritance override
    (`collect_segmented_candidates`'s own "Chapeau TRIGGER inheritance":
    a bare list item with no cue of its own, e.g. "subsection (2)",
    inherits its chapeau's own predicate/subj) — `propose()` now carries
    those chapeau-inherited candidates too, exactly as the non-hybrid
    pipeline already does, just without ITS OWN overlap pruning (kept
    here, recall-oriented, on purpose)."""
    if not isinstance(unit_text, str):
        raise ValueError("propose() requires a string")
    segs = _segment.segment(unit_text, enclosing_provision=enclosing_provision)
    chunk_spans = [{"start": s, "end": e} for s, e in _segment.np_chunks(unit_text)]

    # A node's own exact (start, end) ->
    # its index in `segs`, used below to find, for a candidate whose
    # own clause_span matches a node EXACTLY, whether that node carries
    # an explicit inherited-subject span (item a).
    node_by_span = {(node["start"], node["end"]): idx for idx, node in enumerate(segs)}
    inherited_subj = _segment.inherited_subject_spans(unit_text, segs)
    # The other two explicit-subject
    # sources: a finite relative clause's own antecedent (keyed by the
    # relative tail's OWN span, since `relative_emit_rel` is False and
    # the tail is never its own `segs` node) and a bare coordinated
    # finite clause's shared subject (keyed by the subjectless sibling's
    # own node index, same convention as `inherited_subj`).
    relative_antecedent_by_span = _segment.relative_clause_antecedent_spans(unit_text, segs)
    coordinated_shared_subj = _segment.coordinated_shared_subject_spans(unit_text, segs)

    candidates = []
    for cand in _rules.collect_segmented_candidates(unit_text, enclosing_provision=enclosing_provision):
        # R-k/R-q: finalise (determiner/modal-strip) the candidate's own
        # ALREADY-ABSOLUTE spans before it reaches the CandidateSet — a
        # candidate the decider sees should already be as clean as the
        # non-hybrid pipeline's own Statements, never a raw regex
        # capture. Dropped (never offered to the decider) if its span
        # collapses to nothing once finalised.
        finalized = _build.finalize_candidate_spans(unit_text, cand)
        if finalized is None:
            continue
        subj_span, obj_span = finalized
        candidates.append({
            "id": len(candidates),
            "rule_id": cand.rule_id,
            "citation": _rules.RULE_CITATIONS.get(cand.rule_id, ""),
            "predicate": cand.predicate,
            "clause_span": list(cand.clause_span),
            "subj_span": list(subj_span),
            "obj_span": list(obj_span),
            "base_confidence": cand.base_confidence,
            "negation_force": cand.negation_force,
            "chapeau_group": cand.chapeau_group,
        })
        # "Appear as a candidate
        # subj where a rule fires": when this candidate's own
        # clause_span is EXACTLY one node of `segs` that itself inherits
        # an explicit subject (a chapeau-list item inheriting its
        # chapeau's subject, a bare coordinated clause sharing its first
        # sibling's subject) OR is a relative clause's own tail span
        # (an antecedent NAMED EARLIER in the same sentence), and the
        # explicit antecedent span differs from what this rule found on
        # its own, offer a SECOND candidate — same predicate/obj/
        # confidence, the explicit antecedent as subj — ADDITIVE, never
        # replacing the rule's own original candidate.
        node_idx = node_by_span.get(tuple(cand.clause_span))
        explicit_subj = inherited_subj.get(node_idx) if node_idx is not None else None
        if explicit_subj is None:
            explicit_subj = relative_antecedent_by_span.get(tuple(cand.clause_span))
        if explicit_subj is None and node_idx is not None:
            explicit_subj = coordinated_shared_subj.get(node_idx)
        if explicit_subj is not None and explicit_subj != tuple(subj_span):
            candidates.append({
                "id": len(candidates),
                "rule_id": f"{cand.rule_id}-explicit-inherited-subj",
                "citation": _rules.RULE_CITATIONS.get(cand.rule_id, ""),
                "predicate": cand.predicate,
                "clause_span": list(cand.clause_span),
                "subj_span": list(explicit_subj),
                "obj_span": list(obj_span),
                "base_confidence": cand.base_confidence,
                "negation_force": cand.negation_force,
                "chapeau_group": cand.chapeau_group,
            })

    # The extra allowed-span pool: clean
    # (list-label/heading/newline/dangling-word filtered) NP chunks,
    # coordinated-subject conjuncts, R-p.1 smallest-complete-clause
    # spans, every inherited/antecedent/shared-subject span (chapeau,
    # relative-clause antecedent, coordinated-clause shared subject),
    # and every relative clause's own tail span. ADDITIVE to
    # `segments`/`np_chunks`/candidate spans, never a replacement.
    extra_spans: "set[tuple[int, int]]" = set()
    extra_spans.update(_segment.clean_np_chunks(unit_text))
    extra_spans.update(_segment.coordinated_subject_conjuncts(unit_text))
    extra_spans.update(_segment.smallest_complete_clause_spans(unit_text, segs))
    extra_spans.update(inherited_subj.values())
    extra_spans.update(relative_antecedent_by_span.keys())
    extra_spans.update(relative_antecedent_by_span.values())
    extra_spans.update(coordinated_shared_subj.values())
    extra_allowed = [{"start": s, "end": e} for (s, e) in sorted(extra_spans)]

    return CandidateSet(
        unit_text=unit_text, enclosing_provision=enclosing_provision,
        segments=tuple(segs), np_chunks=tuple(chunk_spans), candidates=tuple(candidates),
        extra_allowed_spans=tuple(extra_allowed),
    )


def allowed_spans(candidate_set: CandidateSet) -> "set[tuple[int, int]]":
    """Every span a Decision is allowed to adjust TO, or build an added
    Statement's own endpoint FROM: every segmentation node's own span,
    every NP chunk, and every candidate's own `clause_span`/`subj_span`/
    `obj_span`. A span NOT in this set is rejected by `assemble()`."""
    out: "set[tuple[int, int]]" = set()
    for seg in candidate_set.segments:
        out.add((seg["start"], seg["end"]))
    for chunk in candidate_set.np_chunks:
        out.add((chunk["start"], chunk["end"]))
    for cand in candidate_set.candidates:
        out.add(tuple(cand["clause_span"]))
        if cand["subj_span"]:
            out.add(tuple(cand["subj_span"]))
        if cand["obj_span"]:
            out.add(tuple(cand["obj_span"]))
    # The fourth source: clean NP chunks,
    # coordinated-subject conjuncts, R-p.1 smallest-complete-clause
    # spans and every inherited/antecedent/shared subject span. Without
    # this, `extra_allowed_spans` would be carried in the payload but
    # never actually usable by a Decision — ADDITIVE to the three
    # sources above.
    for span in candidate_set.extra_allowed_spans:
        out.add((span["start"], span["end"]))
    return out


# ─────────────────────────── stage 2: decide() ───────────────────────────

@dataclass(frozen=True)
class Decision:
    """The model stage's own recorded answer. ``selections`` is one dict
    per CHOSEN candidate: ``{"candidate_id", "predicate", "layer",
    "negation", "subj_span_override", "obj_span_override"}`` (the two
    overrides are ``None`` when the candidate's own span is kept
    unchanged). ``added`` is zero or more NEW Statements the model
    introduced on its own: ``{"predicate", "layer", "negation",
    "subj_span", "obj_span"}`` — both spans MUST already be members of
    `allowed_spans()`, enforced by `assemble()`, never by this dataclass
    itself (a Decision is just data; the enforcement is the assembly
    step's own job, so a replayed cache entry is checked EVERY time it
    is assembled, not only once at record time)."""
    candidate_set_sha: str
    coder_view_sha: str
    model_id: str
    prompt_template_sha: str
    selections: "tuple[dict, ...]"
    added: "tuple[dict, ...]" = field(default_factory=tuple)

    def to_canonical_dict(self) -> dict:
        return {
            "schema_version": SCHEMA_VERSION,
            "candidate_set_sha": self.candidate_set_sha,
            "coder_view_sha": self.coder_view_sha,
            "model_id": self.model_id,
            "prompt_template_sha": self.prompt_template_sha,
            "selections": list(self.selections),
            "added": list(self.added),
        }

    def to_canonical_json(self) -> str:
        return _canonical_json(self.to_canonical_dict())

    @classmethod
    def from_canonical_dict(cls, d: dict) -> "Decision":
        return cls(
            candidate_set_sha=d["candidate_set_sha"], coder_view_sha=d["coder_view_sha"],
            model_id=d["model_id"], prompt_template_sha=d["prompt_template_sha"],
            selections=tuple(d["selections"]), added=tuple(d.get("added", [])),
        )


@dataclass(frozen=True)
class CacheKey:
    """``sha256(candidate_set_sha + coder_view_sha + model_id +
    prompt_template_sha)`` — a plain ``"|"``-joined concatenation, SHA-
    256'd once. The four own inputs are kept separately in the key's own
    repr/str for traceability; ``str(key)`` is the hex digest ITSELF
    (the thing actually used as a cache filename)."""
    candidate_set_sha: str
    coder_view_sha: str
    model_id: str
    prompt_template_sha: str

    @property
    def digest(self) -> str:
        joined = "|".join((
            self.candidate_set_sha, self.coder_view_sha, self.model_id, self.prompt_template_sha,
        ))
        return _sha256_of(joined)

    def __str__(self) -> str:
        return self.digest


class CacheMissError(KeyError):
    """Raised by `DecisionCache.replay()`/`decide(mode="replay")` on a
    cache key with no recorded entry — NEVER a silent fallback to
    recomputation (there is no "recompute the model" path inside this
    package at all)."""


class DecisionCache:
    """A content-addressed, file-backed cache of recorded Decisions.
    One file per key, named `<digest>.json`, holding the Decision's own
    canonical JSON. `manifest()` is a sorted `{digest: file-sha256}`
    mapping, itself hashed (`manifest_sha256()`) — ANY reported hybrid
    result states this one hash, so a reader can verify EXACTLY which
    recorded Decisions produced it."""

    def __init__(self, cache_dir: "Path"):
        self.cache_dir = Path(cache_dir)

    def _path_for(self, key: "CacheKey | str") -> Path:
        digest = key.digest if isinstance(key, CacheKey) else key
        return self.cache_dir / f"{digest}.json"

    def record(self, key: "CacheKey | str", decision: Decision) -> Path:
        """Write ``decision`` under ``key``. IDEMPOTENT for the identical
        content (a re-record of the SAME decision is a no-op); raises
        `ValueError` if the key already holds a DIFFERENT decision (a
        cache entry is immutable once written, never silently
        overwritten).

        The SAME check `replay()` already does on
        every READ is now also done on every WRITE — ``decision``'s own
        four identifying fields are used to recompute a `CacheKey`,
        which MUST match ``key``. A forged or mismatched entry (e.g. a
        Decision answered against one candidate set, written under
        another's key) is rejected at record time, not merely caught
        later by a replay somewhere else."""
        requested_digest = key.digest if isinstance(key, CacheKey) else key
        recomputed_digest = CacheKey(
            candidate_set_sha=decision.candidate_set_sha, coder_view_sha=decision.coder_view_sha,
            model_id=decision.model_id, prompt_template_sha=decision.prompt_template_sha,
        ).digest
        if recomputed_digest != requested_digest:
            raise ValueError(
                f"cache integrity error: the Decision given to record() under key "
                f"{requested_digest!r} recomputes to a DIFFERENT key ({recomputed_digest!r}) "
                f"from its own fields — refusing to write a forged or mismatched entry"
            )
        path = self._path_for(key)
        new_text = decision.to_canonical_json()
        if path.exists():
            existing = path.read_text(encoding="utf-8")
            if existing != new_text:
                raise ValueError(f"cache key {path.stem!r} already holds a DIFFERENT decision")
            return path
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(new_text, encoding="utf-8")
        return path

    def replay(self, key: "CacheKey | str") -> Decision:
        """Read the Decision recorded at ``key`` — round-6 integrity
        fixes, both checked on EVERY replay, not only once at record
        time: (1) the file's own JSON is validated against
        `DECISION_JSON_SCHEMA` (`decision_schema_violations`,
        stdlib-only); (2) the Decision's OWN four identifying fields
        (`candidate_set_sha`/`coder_view_sha`/`model_id`/
        `prompt_template_sha`) are used to RECOMPUTE a `CacheKey`,
        which MUST match the ``key`` this file is stored under — a cache
        file that was somehow moved, copied under the wrong name, or
        hand-edited to disagree with its own filename is rejected, never
        silently trusted."""
        path = self._path_for(key)
        if not path.exists():
            digest = key.digest if isinstance(key, CacheKey) else key
            raise CacheMissError(
                f"no recorded Decision for cache key {digest!r} at {path} — "
                f"replay mode never falls back to recomputation"
            )
        raw = json.loads(path.read_text(encoding="utf-8"))
        violations = decision_schema_violations(raw)
        if violations:
            raise ValueError(f"cached Decision at {path} fails schema validation: {violations}")
        decision = Decision.from_canonical_dict(raw)
        requested_digest = key.digest if isinstance(key, CacheKey) else key
        recomputed_digest = CacheKey(
            candidate_set_sha=decision.candidate_set_sha, coder_view_sha=decision.coder_view_sha,
            model_id=decision.model_id, prompt_template_sha=decision.prompt_template_sha,
        ).digest
        if recomputed_digest != requested_digest:
            raise ValueError(
                f"cache integrity error: the Decision stored at {path} (requested key "
                f"{requested_digest!r}) recomputes to a DIFFERENT key ({recomputed_digest!r}) "
                f"from its own fields — the file does not match the key it is stored under"
            )
        return decision

    def manifest(self) -> dict:
        """A sorted ``{digest: file-sha256}`` mapping over ONLY the
        cache's own Decision files — a filename matching the 64-hex-
        digit digest pattern exactly (round-6 fix: `*.json` alone would
        also hash a stray non-Decision file dropped into the same
        directory)."""
        entries = {}
        if self.cache_dir.exists():
            for p in sorted(self.cache_dir.glob("*.json")):
                if re.fullmatch(r"[0-9a-f]{64}", p.stem):
                    entries[p.stem] = _sha256_of(p.read_text(encoding="utf-8"))
        return entries

    def manifest_sha256(self) -> str:
        return _sha256_of(_canonical_json(self.manifest()))


DEFAULT_MODE = "replay"


def decide(
    candidate_set: CandidateSet, coder_view_text: str, *, model_id: str,
    prompt_template_sha: str, cache: DecisionCache, mode: str = DEFAULT_MODE,
) -> Decision:
    """Dispatch to the recorded Decision for this exact
    ``(candidate_set, coder_view_text, model_id, prompt_template_sha)``
    combination. ``mode="replay"`` (the default) is the ONLY mode this
    package implements — a cache miss raises `CacheMissError`.
    ``mode="record"`` raises `NotImplementedError`: recording a REAL
    Decision calls a model, which is external tooling (reviewers
    answering `export_decision_requests`' own output files), deliberately
    kept out of this package — no API key lives
    here."""
    if mode == "record":
        raise NotImplementedError(
            "decide(mode='record') is not implemented inside this package — recording a real "
            "Decision is external tooling; write the cache file directly with DecisionCache.record()"
        )
    if mode != "replay":
        raise ValueError(f"decide() mode must be 'replay' or 'record', got {mode!r}")
    key = CacheKey(
        candidate_set_sha=candidate_set.sha256, coder_view_sha=_sha256_of(coder_view_text),
        model_id=model_id, prompt_template_sha=prompt_template_sha,
    )
    return cache.replay(key)


# ─────────────────────────── stage 3: assemble() ─────────────────────────

def _span_tuple(span) -> "Optional[tuple]":
    return tuple(span) if span else None


def _build_statement_from_spans(
    unit_text: str, predicate: str, layer: str, negation: str,
    clause_span: tuple, subj_span: tuple, obj_span: tuple,
    rule_id: str, cache_key_digest: str, *, instrument_uri: str, consolidation_date: str,
) -> dict:
    subj_text = _spans.span_text(unit_text, subj_span)
    obj_text = _spans.span_text(unit_text, obj_span)
    if not subj_text or not obj_text:
        raise ValueError(f"assemble(): empty subj/obj text for predicate {predicate!r}")
    dimension = _statement.PREDICATE_DIMENSION[predicate]
    id_source = _statement.normalize_statement_text(
        f"{predicate}|{subj_text}|{obj_text}|{clause_span[0]}-{clause_span[1]}|{cache_key_digest}"
    )
    stmt_id = _statement.statement_id(
        instrument_uri, consolidation_date, _statement.text_hash(id_source)
    )
    doc = {
        "id": stmt_id,
        "subj": subj_text,
        "obj": obj_text,
        "predicate": predicate,
        "dimension": dimension,
        "layer": layer,
        "weight": 1.0,
        "edge_confidence": 1.0,
        "provenance": {"start": clause_span[0], "end": clause_span[1]},
        "negation": negation,
        "extraction_rule_id": f"{rule_id}|model-decision:{cache_key_digest}",
    }
    return doc


def _assemble_built_statements(
    candidate_set: CandidateSet, decision: Decision, *,
    instrument_uri: str, consolidation_date: str,
) -> "list[_build.BuiltStatement]":
    """Shared implementation for `assemble()` and `assemble_with_spans()`
    (round-7 addition, item 3) — builds the SAME Statements either one
    returns, each paired with its OWN ``{"clause", "subj", "obj"}`` span
    triple (`extract.build.BuiltStatement`'s own shape, reused rather
    than a second, diverging container), so a caller that needs spans
    (the hybrid dev-eval path, which scores via span Jaccard, never
    rendered text) does not have to re-derive them from the Decision by
    hand. `assemble()` itself discards the span triple; this function
    is the only place that computes it."""
    if decision.candidate_set_sha != candidate_set.sha256:
        raise ValueError(
            f"assemble(): decision.candidate_set_sha {decision.candidate_set_sha!r} does not "
            f"match the given CandidateSet's own sha256 {candidate_set.sha256!r}"
        )
    for field_name in ("candidate_set_sha", "coder_view_sha", "model_id", "prompt_template_sha"):
        if not getattr(decision, field_name):
            raise ValueError(f"assemble(): decision.{field_name} must be non-empty")
    cache_key_digest = CacheKey(
        candidate_set_sha=decision.candidate_set_sha, coder_view_sha=decision.coder_view_sha,
        model_id=decision.model_id, prompt_template_sha=decision.prompt_template_sha,
    ).digest

    allowed = allowed_spans(candidate_set)
    candidates_by_id = {c["id"]: c for c in candidate_set.candidates}
    unit_text = candidate_set.unit_text
    out = []

    seen_candidate_ids = set()
    for sel in decision.selections:
        if sel["candidate_id"] in seen_candidate_ids:
            raise ValueError(f"assemble(): candidate id {sel['candidate_id']!r} is selected more than once")
        seen_candidate_ids.add(sel["candidate_id"])
        cand = candidates_by_id.get(sel["candidate_id"])
        if cand is None:
            raise ValueError(f"assemble(): selection references unknown candidate id {sel['candidate_id']!r}")
        subj_span = _span_tuple(sel.get("subj_span_override")) or _span_tuple(cand["subj_span"])
        obj_span = _span_tuple(sel.get("obj_span_override")) or _span_tuple(cand["obj_span"])
        for label, span in (("subj", subj_span), ("obj", obj_span)):
            if span not in allowed:
                raise ValueError(
                    f"assemble(): selection for candidate {cand['id']} adjusts its own {label} "
                    f"span to {span}, which is NOT a member of this CandidateSet's own allowed_spans()"
                )
        clause_span = _span_tuple(cand["clause_span"])
        clause_span = (
            min(clause_span[0], subj_span[0], obj_span[0]),
            max(clause_span[1], subj_span[1], obj_span[1]),
        )
        doc = _build_statement_from_spans(
            unit_text, sel["predicate"], sel["layer"], sel["negation"],
            clause_span, subj_span, obj_span, cand["rule_id"], cache_key_digest,
            instrument_uri=instrument_uri, consolidation_date=consolidation_date,
        )
        if not _statement.is_valid_statement(doc):
            raise ValueError(f"assemble(): assembled Statement failed schema validation: "
                              f"{_statement.statement_violations(doc)}")
        out.append(_build.BuiltStatement(
            statement=doc, spans={"clause": clause_span, "subj": subj_span, "obj": obj_span},
            chapeau_group=cand.get("chapeau_group"),
        ))

    for added in decision.added:
        subj_span = _span_tuple(added["subj_span"])
        obj_span = _span_tuple(added["obj_span"])
        for label, span in (("subj", subj_span), ("obj", obj_span)):
            if span not in allowed:
                raise ValueError(
                    f"assemble(): an added Statement's own {label} span {span} is NOT a member "
                    f"of this CandidateSet's own allowed_spans()"
                )
        clause_span = (min(subj_span[0], obj_span[0]), max(subj_span[1], obj_span[1]))
        doc = _build_statement_from_spans(
            unit_text, added["predicate"], added["layer"], added["negation"],
            clause_span, subj_span, obj_span, "model-added", cache_key_digest,
            instrument_uri=instrument_uri, consolidation_date=consolidation_date,
        )
        if not _statement.is_valid_statement(doc):
            raise ValueError(f"assemble(): an added Statement failed schema validation: "
                              f"{_statement.statement_violations(doc)}")
        out.append(_build.BuiltStatement(
            statement=doc, spans={"clause": clause_span, "subj": subj_span, "obj": obj_span},
            chapeau_group=None,
        ))

    return sorted(out, key=lambda bs: _statement.canonical_sort_key(bs.statement))


def assemble(
    candidate_set: CandidateSet, decision: Decision, *,
    instrument_uri: str = "extracted-unit", consolidation_date: str = "n/a",
) -> "list[dict]":
    """Decision + CandidateSet -> schema-valid §21 Statements.
    `ValueError` on ANY span (an override, or an added Statement's own
    endpoint) that is not already a member of `allowed_spans
    (candidate_set)` — the enforcement this stage exists for; also on a
    DUPLICATE selection of the same candidate id (round-6 fix: a
    Decision selecting candidate 3 twice, even with different labels,
    is rejected rather than silently emitting it twice). Every returned
    Statement passes `statement.is_valid_statement()` (asserted before
    return — fail LOUD, never emit malformed).

    The cache-key digest recorded on every
    assembled Statement's own `extraction_rule_id` is DERIVED from
    ``decision``'s own four identifying fields — never a separately
    passed-in argument (the earlier ``cache_key_digest`` parameter is
    REMOVED; a caller cannot assemble against a digest that disagrees
    with the Decision actually being assembled)."""
    built = _assemble_built_statements(
        candidate_set, decision,
        instrument_uri=instrument_uri, consolidation_date=consolidation_date,
    )
    return [bs.statement for bs in built]


def assemble_with_spans(
    candidate_set: CandidateSet, decision: Decision, *,
    instrument_uri: str = "extracted-unit", consolidation_date: str = "n/a",
) -> "list[_build.BuiltStatement]":
    """The SAME assembly `assemble()` does,
    but returning each Statement paired with its own ``spans`` triple
    (`extract.build.BuiltStatement`, the SAME shape `extract_with_spans`
    already uses for the non-hybrid pipeline), for a caller that scores
    by span Jaccard rather than rendered text — a local evaluation
    script (not shipped) is that caller. `assemble()` itself is
    UNCHANGED (same signature, same return shape, same checks); this is
    an additive sibling, not a replacement."""
    return _assemble_built_statements(
        candidate_set, decision,
        instrument_uri=instrument_uri, consolidation_date=consolidation_date,
    )


# ───────────────────────── prompt template v1 ────────────────────────────

PROMPT_TEMPLATE_V1 = """\
You are coding ONE legal text unit under the typed-statement codebook \
(the coder view below). You are given: the unit's own text, the coder \
view, and a CANDIDATE SET — a deterministic, recall-oriented list of \
clause spans, noun-phrase chunks, and candidate Statements a closed \
cue-rule table already proposed for this unit, each with its own \
rule id and codebook citation.

Your task:
1. Read the coder view and apply it to the unit text.
2. From the candidate set, SELECT the candidates that correctly state a \
Statement under the coder view. For each selected candidate, set its \
predicate, layer and negation per the coder view's own rules — you MAY \
keep the candidate's own predicate or change it to a different one the \
coder view supports; you MAY leave its subj/obj span unchanged or \
adjust it, but ONLY to another span already present in the candidate \
set (a clause span, an NP chunk, or another candidate's own subj/obj \
span) — never a span of your own invention.
3. You MAY add a Statement the candidate set did not propose, but ONLY \
if both its subj and obj spans are spans already present in the \
candidate set (a clause span, an NP chunk, or a candidate's own \
subj/obj span).
4. Return your answer in the exact JSON shape described by the \
expected-output schema provided alongside this prompt. Do not invent \
fields; do not omit a required one.

You are not given, and must not assume, any reference answer for this \
unit. Code only from the coder view and the candidate set above.
"""
PROMPT_TEMPLATE_V1_SHA256 = _sha256_of(PROMPT_TEMPLATE_V1)

DECISION_JSON_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "Hybrid extractor Decision v1",
    "type": "object",
    "additionalProperties": False,
    "required": ["candidate_set_sha", "coder_view_sha", "model_id", "prompt_template_sha", "selections"],
    "properties": {
        "schema_version": {"type": "string"},
        "candidate_set_sha": {"type": "string"},
        "coder_view_sha": {"type": "string"},
        "model_id": {"type": "string"},
        "prompt_template_sha": {"type": "string"},
        "selections": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["candidate_id", "predicate", "layer", "negation"],
                "properties": {
                    "candidate_id": {"type": "integer"},
                    "predicate": {"type": "string", "enum": list(_statement.PREDICATE_DIMENSION)},
                    "layer": {"type": "string", "enum": ["surface", "domain", "deep"]},
                    "negation": {"type": "string", "enum": ["present", "uncertain", "absent"]},
                    "subj_span_override": {"type": ["array", "null"]},
                    "obj_span_override": {"type": ["array", "null"]},
                },
            },
        },
        "added": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["predicate", "layer", "negation", "subj_span", "obj_span"],
                "properties": {
                    "predicate": {"type": "string", "enum": list(_statement.PREDICATE_DIMENSION)},
                    "layer": {"type": "string", "enum": ["surface", "domain", "deep"]},
                    "negation": {"type": "string", "enum": ["present", "uncertain", "absent"]},
                    "subj_span": {"type": "array"},
                    "obj_span": {"type": "array"},
                },
            },
        },
    },
}


def decision_schema_violations(d: dict) -> "list[str]":
    """A small, STDLIB-ONLY validator against `DECISION_JSON_SCHEMA`'s
    own shape (this package carries no `jsonschema` dependency — the
    same stdlib-only discipline `five_d_nd.statement.statement_
    violations` already applies to the §21 Statement schema). Checked
    at `DecisionCache.replay()`'s own call, on EVERY replay, not only
    once at record time. Returns `[]` only when every required field is
    present and well-typed, every enum value is one of its own closed
    set, and no unknown top-level/item field is present."""
    out: "list[str]" = []
    if not isinstance(d, dict):
        return ["decision must be a mapping"]
    allowed_top = {"schema_version", "candidate_set_sha", "coder_view_sha", "model_id",
                   "prompt_template_sha", "selections", "added"}
    unknown = set(d) - allowed_top
    if unknown:
        out.append(f"decision has unknown top-level field(s): {sorted(unknown)}")
    for field in ("candidate_set_sha", "coder_view_sha", "model_id", "prompt_template_sha"):
        if not isinstance(d.get(field), str) or not d.get(field):
            out.append(f"decision field {field!r} must be a non-empty string")
    selections = d.get("selections")
    if not isinstance(selections, list):
        out.append("decision 'selections' must be a list")
        selections = []
    allowed_sel = {"candidate_id", "predicate", "layer", "negation", "subj_span_override", "obj_span_override"}
    for i, sel in enumerate(selections):
        if not isinstance(sel, dict):
            out.append(f"selections[{i}] must be a mapping")
            continue
        unknown_sel = set(sel) - allowed_sel
        if unknown_sel:
            out.append(f"selections[{i}] has unknown field(s): {sorted(unknown_sel)}")
        if not isinstance(sel.get("candidate_id"), int) or isinstance(sel.get("candidate_id"), bool):
            out.append(f"selections[{i}]['candidate_id'] must be an int")
        if sel.get("predicate") not in _statement.PREDICATE_DIMENSION:
            out.append(f"selections[{i}]['predicate'] {sel.get('predicate')!r} is not one of the 15 closed predicates")
        if sel.get("layer") not in ("surface", "domain", "deep"):
            out.append(f"selections[{i}]['layer'] must be one of surface/domain/deep")
        if sel.get("negation") not in ("present", "uncertain", "absent"):
            out.append(f"selections[{i}]['negation'] must be one of present/uncertain/absent")
    added = d.get("added", [])
    if not isinstance(added, list):
        out.append("decision 'added' must be a list")
        added = []
    allowed_add = {"predicate", "layer", "negation", "subj_span", "obj_span"}
    for i, item in enumerate(added):
        if not isinstance(item, dict):
            out.append(f"added[{i}] must be a mapping")
            continue
        unknown_add = set(item) - allowed_add
        if unknown_add:
            out.append(f"added[{i}] has unknown field(s): {sorted(unknown_add)}")
        if item.get("predicate") not in _statement.PREDICATE_DIMENSION:
            out.append(f"added[{i}]['predicate'] {item.get('predicate')!r} is not one of the 15 closed predicates")
        if item.get("layer") not in ("surface", "domain", "deep"):
            out.append(f"added[{i}]['layer'] must be one of surface/domain/deep")
        if item.get("negation") not in ("present", "uncertain", "absent"):
            out.append(f"added[{i}]['negation'] must be one of present/uncertain/absent")
        if not isinstance(item.get("subj_span"), list) or not isinstance(item.get("obj_span"), list):
            out.append(f"added[{i}] must carry a 'subj_span' and an 'obj_span', each a list")
    return out


# ─────────────────────── decision-request export ────────────────────────

def export_decision_requests(
    units: "dict[str, dict]", out_dir: "Path", *, coder_view_text: str,
    model_id: str = "claude-opus-5-5", prompt_template: str = PROMPT_TEMPLATE_V1,
    mapping_path: "Optional[Path]" = None,
) -> "list[Path]":
    """Write ONE OPAQUE request file per unit, for external reviewers
    to answer (outside this package — no model is ever
    called here). ``units`` is a plain ``{unit_id: {"text": ...,
    "enclosing_provision": ...}}`` mapping the CALLER supplies (never
    read from a hardcoded path inside this package — the caller's own
    data-access discipline, e.g. "dev data only", is enforced at the
    call site, not here).

    A request file is named by its own CACHE KEY (the
    opaque digest the Decision will eventually be recorded under), NOT
    by the unit id, and its own CONTENT carries no `unit_id` field
    either — a blind subagent answering a request never sees which real
    unit it is coding, only the candidate set, the coder view, the
    prompt, and the expected-output schema. The unit_id<->cache_key
    mapping is written to a SEPARATE file, OUTSIDE ``out_dir`` (default:
    a sibling file named ``<out_dir name>-mapping.json``, next to
    ``out_dir`` itself) — needed to re-attach a recorded Decision back
    to its own unit later, but never shipped alongside the opaque
    requests themselves.

    Each request file contains: the unit's own CandidateSet (canonical
    dict + its own sha256), the coder-view TEXT (never gold), the prompt
    template (+ its own sha256), the model id, the computed cache key,
    and the expected-output JSON Schema (`DECISION_JSON_SCHEMA`) — NEVER
    a gold Statement, NEVER another coder's own output, NEVER held-out
    text, and NEVER the unit id (the caller's own ``units`` argument is
    the only text source). Returns the list of written request paths,
    one per unit, in `units`' own iteration order."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if mapping_path is None:
        mapping_path = out_dir.parent / f"{out_dir.name}-mapping.json"
    mapping_path = Path(mapping_path)
    coder_view_sha = _sha256_of(coder_view_text)
    prompt_template_sha = _sha256_of(prompt_template)

    paths = []
    mapping = {}
    for unit_id, unit in units.items():
        candidate_set = propose(unit["text"], enclosing_provision=unit.get("enclosing_provision"))
        key = CacheKey(
            candidate_set_sha=candidate_set.sha256, coder_view_sha=coder_view_sha,
            model_id=model_id, prompt_template_sha=prompt_template_sha,
        )
        request = {
            "schema_version": SCHEMA_VERSION,
            "candidate_set": candidate_set.to_canonical_dict(),
            "candidate_set_sha": candidate_set.sha256,
            "coder_view_text": coder_view_text,
            "coder_view_sha": coder_view_sha,
            "prompt_template": prompt_template,
            "prompt_template_sha": prompt_template_sha,
            "model_id": model_id,
            "cache_key": key.digest,
            "expected_output_schema": DECISION_JSON_SCHEMA,
        }
        path = out_dir / f"{key.digest}.json"
        path.write_text(_canonical_json(request) + "\n", encoding="utf-8")
        paths.append(path)
        mapping[unit_id] = key.digest

    mapping_path.write_text(_canonical_json({"mapping": mapping}) + "\n", encoding="utf-8")
    return paths


def import_decisions(decisions_dir: "Path", cache: DecisionCache) -> "list[Path]":
    """The counterpart to
    `export_decision_requests()`: reads every answered Decision file a
    reviewer has dropped into ``decisions_dir``, named
    ``<cache_key>.json`` (the SAME opaque naming `export_decision_
    requests()` used for its own request files), and records each one
    into ``cache``.

    Only a filename matching the 64-hex-digit cache-key pattern is read
    as a Decision (round-6's own `manifest()` convention, reused here so
    a stray non-Decision file dropped into the same directory — a
    `-mapping.json` sibling copied in by mistake, say — is silently
    skipped rather than misread). Each file's own JSON is validated
    against `DECISION_JSON_SCHEMA` (`decision_schema_violations`) BEFORE
    it is recorded — a malformed answer raises `ValueError` naming the
    file and the violations, rather than being written into the cache
    and only failing later at replay. `DecisionCache.record()`'s own
    round-7 integrity check (item 2) additionally verifies each file's
    OWN content recomputes to the SAME key as its own filename, so an
    answer saved under the wrong cache-key filename is also rejected
    here, not silently accepted.

    Returns the list of file paths actually recorded, in sorted
    (filename) order."""
    recorded = []
    for path in sorted(Path(decisions_dir).glob("*.json")):
        if not re.fullmatch(r"[0-9a-f]{64}", path.stem):
            continue
        raw = json.loads(path.read_text(encoding="utf-8"))
        violations = decision_schema_violations(raw)
        if violations:
            raise ValueError(f"import_decisions(): {path} fails schema validation: {violations}")
        decision = Decision.from_canonical_dict(raw)
        cache.record(path.stem, decision)
        recorded.append(path)
    return recorded
