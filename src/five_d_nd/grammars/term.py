# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""EXAMPLE nD grammar — a deterministic lexical "term" grammar (§9).

Ported from the winning design of a build comparison, candidate C
(approach "a deterministic lexical/term nD grammar for topical
discrimination"; the owner approved integrating the winner and
grafts, 2026-10-02 — see
``docs/decisions/0007-clause-cue-layer-and-example-grammars.md``). This module is NOT 5D — it is a
worked EXAMPLE of §9's nD grammar contract: a domain-neutral BM25 term
axis over entry spans, attached to 5D through an ordinary ``NDSystem`` +
descriptor, bound to ``relational`` (5D's own identity/default, §3/§2) —
never a sixth dimension, and never privileged over any other nD grammar.

**Why `relational`, not a new dimension.** `relational` is 5D's two-sided
algebraic IDENTITY (§3: `compose(relational, x) == x`) and its DEFAULT
binding (§2, the assertoric layer's own `predication` -> `relational`,
§8). Binding this grammar's lexical axis there means attaching it never
perturbs 5D's own existing structural signal (containment, assertoric
lowering, §8/§8a) the way a `structural`/`causal`/`temporal` binding
would — the grammar's own TOPICAL axis lives entirely in its own
`axes`/`bindings` (below), not in a 5D dimension at all.

**Deterministic, not neural.** Every number here is a pure function of
(a) the corpus text and (b) the fixed BM25 constants (`BM25_K1`,
`BM25_B` — standard textbook defaults, never tuned against the GDPR
ground truth used to measure retrieval quality); the
SAME surface tokenizer shape as the measurement harness's own TF-IDF
baseline is used here too, so an AUC difference is attributable to the
weighting scheme (BM25 saturation vs plain TF-IDF) and to this module's
own profile-pinning/claims machinery, never to a silently different
tokenizer. Re-running on the same corpus text byte-for-byte reproduces the
same vocabulary, IDF table, digest, and term vectors.

**Pinned by digest.** The vocabulary and IDF table (`df`, `avgdl`,
`k1`, `b`) — AND the TOKENIZER ITSELF (`TOKEN_RE`'s own pattern, `STOPWORDS`, and the
minimum token length the pattern encodes) — are built once,
deterministically, into a resolution-profile-shaped document
(:func:`build_term_profile`) and digested with ``five_d_nd.grounding.digest``
(the SAME canonical-JSON/sha256 machinery every other digest in this
package uses — consumed, not reimplemented) — ``profile_digest`` is what
the published ``NDSystem``'s `term_weight` axis names as its
`ontology_version` (§9's "external vocabulary" field pair). Pinning the
tokenizer closes a real gap this module's own earlier draft only
CLAIMED: a module docstring saying "the tokenizer is pinned" with no
tokenizer field anywhere in the digested document was not actually true —
a silent tokenizer edit (e.g. accepting one-letter tokens) would have
changed every downstream vocabulary/vector WITHOUT changing
`profile_digest`, breaking the very reproducibility claim this module
makes. It is now true: a `build_term_profile()` call records
`token_pattern`/`stopwords` alongside `vocabulary`/`df`, so the SAME
corpus text under a DIFFERENT tokenizer digests differently.

Stdlib only.
"""
from __future__ import annotations

import math
import re
from collections import Counter

from ..grounding import digest as _grounding_digest

__all__ = [
    "BM25_K1", "BM25_B",
    "tokenize",
    "build_term_profile",
    "bm25_vector",
    "l2_normalize",
    "sparse_cosine",
    "build_nd_system",
    "build_descriptor",
    "produce_term_claims",
]

# ----------------------------- tokenisation -----------------------------
TOKEN_RE = re.compile(r"[a-zA-Z]{2,}")
STOPWORDS = frozenset({
    "the", "of", "to", "in", "and", "or", "a", "an", "for", "by", "with", "is", "are",
    "shall", "be", "this", "that", "which", "as", "on", "at", "it", "its", "their",
    "has", "have", "not", "such", "any", "other", "where", "who", "may", "if",
})

#: BM25 constants — fixed, documented, never tuned on ground-truth labels
#: (standard Robertson/Sparck-Jones defaults).
BM25_K1 = 1.5
BM25_B = 0.75


def tokenize(text: str) -> list:
    return [t.lower() for t in TOKEN_RE.findall(text) if t.lower() not in STOPWORDS]


def build_term_profile(doc_texts: "dict[str, str]", profile_id: str = "term-nd-default") -> dict:
    """Build the pinned vocabulary/IDF document — deterministic: the
    vocabulary is the SORTED set of surviving tokens; document order does
    not affect anything (df/avgdl are order-independent sums). Returns the
    profile WITH its own ``profile_digest`` field (sha256, via
    ``five_d_nd.grounding.digest``, computed over the document MINUS the
    digest field itself).
    """
    docs = {did: tokenize(text) for did, text in doc_texts.items()}
    df = Counter()
    doclens = {}
    for did, toks in docs.items():
        doclens[did] = len(toks)
        for t in set(toks):
            df[t] += 1
    n_docs = len(docs)
    vocabulary = sorted(df.keys())
    avgdl = (sum(doclens.values()) / n_docs) if n_docs else 0.0
    profile = {
        "profile_id": profile_id,
        "n_docs": n_docs,
        "avgdl": round(avgdl, 6),
        "k1": BM25_K1,
        "b": BM25_B,
        "vocabulary": vocabulary,
        "df": {t: df[t] for t in vocabulary},
        # fix round item 4c: the tokenizer itself is now part of what gets
        # pinned/digested, not merely claimed in the module docstring.
        "token_pattern": TOKEN_RE.pattern,
        "stopwords": sorted(STOPWORDS),
    }
    profile["profile_digest"] = _grounding_digest(profile)["sha256"]
    return profile


def _bm25_idf(df_t: int, n_docs: int) -> float:
    return max(0.0, math.log(((n_docs - df_t + 0.5) / (df_t + 0.5)) + 1.0))


def _check_tokenizer_matches(profile: dict) -> None:
    """Pinning the tokenizer into the profile document (``build_term_profile``) is
    only useful if a CONSUMER actually enforces it — a digest a caller
    never checks is just a longer document. Every consumer of an
    ALREADY-BUILT profile (:func:`bm25_vector`, and transitively
    :func:`produce_term_claims`) calls this first: the profile's own
    ``token_pattern``/``stopwords`` fields MUST match this module's
    CURRENT ``TOKEN_RE``/``STOPWORDS`` exactly, or the profile was built
    under a different tokenizer than the one about to tokenize ``text`` —
    scoring against a mismatched vocabulary/IDF table silently, rather
    than raising, would be the digest-pinning claim's own failure mode.
    Raises ``ValueError`` on any mismatch or on a profile missing either
    field entirely (an old profile built before this check existed never
    had them — treated as a mismatch, not silently accepted).
    """
    if profile.get("token_pattern") != TOKEN_RE.pattern:
        raise ValueError(
            f"profile token_pattern {profile.get('token_pattern')!r} does not match "
            f"this module's current TOKEN_RE.pattern {TOKEN_RE.pattern!r} — the profile "
            "was built under a different tokenizer")
    if profile.get("stopwords") != sorted(STOPWORDS):
        raise ValueError(
            "profile stopwords do not match this module's current STOPWORDS — "
            "the profile was built under a different tokenizer")


def bm25_vector(text: str, profile: dict) -> "dict[str, float]":
    """Sparse BM25 weight vector for one span under the PINNED profile —
    terms outside the pinned vocabulary are dropped (never classified
    against an unknown value, §9's own validation posture: an unpinned
    term is simply out of scope, not a silent crash). Fail-closed:
    :func:`_check_tokenizer_matches` runs first,
    raising ``ValueError`` if ``profile`` was built under a different
    tokenizer than this module's CURRENT one."""
    _check_tokenizer_matches(profile)
    toks = tokenize(text)
    tf = Counter(toks)
    dl = len(toks)
    n_docs = profile["n_docs"]
    avgdl = profile["avgdl"] or 1.0
    k1, b = profile["k1"], profile["b"]
    vec = {}
    for t, f in tf.items():
        if t not in profile["df"]:
            continue
        idf = _bm25_idf(profile["df"][t], n_docs)
        denom = f + k1 * (1 - b + b * (dl / avgdl))
        w = idf * (f * (k1 + 1)) / denom if denom else 0.0
        if w > 0:
            vec[t] = round(w, 6)
    return vec


def l2_normalize(vec: "dict[str, float]") -> "dict[str, float]":
    norm = math.sqrt(sum(v * v for v in vec.values()))
    if norm == 0.0:
        return {}
    return {t: v / norm for t, v in vec.items()}


def sparse_cosine(a: "dict[str, float]", b: "dict[str, float]") -> float:
    """Cosine over two SPARSE BM25 vectors (already weighted — callers that
    want a normalised cosine should L2-normalise first via
    :func:`l2_normalize`). ``0.0`` when either side is empty."""
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    return round(sum(v * b.get(k, 0.0) for k, v in a.items()), 6)


# ----------------------------- §9 nD contract attachment -----------------------------

def build_nd_system(profile_digest: str) -> dict:
    """The ``NDSystem`` document this grammar publishes to attach to 5D
    (§9). One axis, ``term_weight``: an OPEN-vocabulary number axis (the
    vocabulary itself is pinned EXTERNALLY by ``profile_digest`, hence
    ``vocabulary_mode: external`` with the ontology id/version pair naming
    the pinned term profile — §9's own external-vocabulary field pair).
    """
    return {
        "id": "term-grammar",
        "namespace": "org.loomground.nd.term",
        "version": "1.0.0",
        "version_5d": "1.0-draft",
        "axes": {
            "term_weight": {
                "value_type": "number",
                "cardinality": "many",
                "vocabulary_mode": "external",
                "ontology_id": "term-vocabulary",
                "ontology_version": profile_digest,
            }
        },
        "bindings": [
            {"form_slot": "term_weight", "allowed_axes": ["term_weight"], "required": False},
        ],
        "ontology_relations": [],
        "validation": {
            "unknown_values": "reject",
            "missing_coordinates": "ignore",
            "provenance_required": False,
        },
    }


def build_descriptor(profile_digest: str) -> dict:
    """The JSON-interchange grammar descriptor (§9) for this grammar,
    binding ``term_weight`` -> ``relational`` (see module docstring for
    why). ``produce`` is OMITTED here (the interchange form); a runtime
    host wires :func:`produce_term_claims` in as the callable separately.
    """
    nd_system = build_nd_system(profile_digest)
    return {
        "plane": "term-grammar",
        "language_version": nd_system["version"],
        "nd_system": nd_system,
        "binding": {"term_weight": "relational"},
        "examples": [],
        "contract_version": "1.0-draft",
    }


def produce_term_claims(entry_id: str, text: str, profile: dict, grammar_id: str = "term-grammar") -> list:
    """Emit one §9/§11-shaped triple-claim per nonzero term in `text`'s
    BM25 vector under `profile`. Every claim binds dimension `relational`
    (see module docstring) and carries the `term_weight` axis value as its
    `o` (the term) with `weight` the BM25 weight, NORMALISED per DOCUMENT
    (fix round, item 9 — divided by the span's own MAXIMUM raw BM25
    weight, so the top term is always 1.0 and every other term's weight
    stays PROPORTIONAL to it), rounded to 6dp (§12's single-rounding-point
    discipline). `provenance` names the profile digest so the claim is
    reproducible and auditable back to the pinned vocabulary/IDF table.

    **Why normalise, not clamp (the earlier, WITHDRAWN design).** A raw
    BM25 weight routinely exceeds 1.0 for a common term, repeated or in a
    short span — `min(raw, 1.0)` (this function's earlier formula)
    therefore clamped the OVERWHELMING MAJORITY of claims straight to
    1.0 (measured on the GDPR corpus: 11,150 of 12,115 claims, over 92%),
    collapsing exactly the per-term signal §9's own claims exist to
    carry. Dividing by the document's own maximum weight instead keeps
    every claim's weight in `[0, 1]` (still triple-shaped, §11) while
    PRESERVING the term's relative rank within its own span — the
    property the clamp destroyed. A document with no term above zero
    (`vec` empty) emits no claims at all, exactly as before.
    """
    vec = bm25_vector(text, profile)
    if not vec:
        return []
    max_weight = max(vec.values())
    claims = []
    for term in sorted(vec):
        normalised = (vec[term] / max_weight) if max_weight > 0 else 0.0
        claims.append({
            "s": entry_id,
            "p": "has_term",
            "o": term,
            "dimension": "relational",
            "weight": round(normalised, 6),
            "provenance": {"profile_digest": profile["profile_digest"], "grammar_id": grammar_id},
            "grammar_id": grammar_id,
        })
    return claims
