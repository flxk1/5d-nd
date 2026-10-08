# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""Every repo path a conformance vector's string fields, or spec/SPEC.md's
own §8a.1/§20a* text, CITES as evidence must actually exist. This test
makes that class of error permanently checkable: it extracts every
path-SHAPED token (``tests/…``,
``conformance/…``, ``src/…``, ``schema/…``, ``docs/…``, each ending in a
file extension) from every vector JSON file's string values and from
spec/SPEC.md's §8a.1/§20a/§20a.1/§20a.2 sections, and asserts each one
resolves to a real file — EXCEPT a glob pattern (containing ``*``), which
names a FAMILY of files, not one specific path, and is checked separately
(the family's own directory must exist and be non-empty).

Stdlib + pytest only.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
VECTORS_DIR = ROOT / "conformance" / "vectors"
SPEC_PATH = ROOT / "spec" / "SPEC.md"

#: a path-shaped token: one of these five top-level dirs, then path
#: segments, ending in a file extension. Deliberately does NOT match a
#: bare directory ("conformance/vectors/clause-cues/") with no filename.
#: The character class also admits ``*`` so a glob-shaped citation (e.g.
#: ``conformance/vectors/clause-cues/xref-v2-*.json``) is EXTRACTED as a
#: token at all; the glob-checking branch in
#: ``test_every_cited_provenance_path_exists`` below (lines checking
#: ``"*" in cited_path``) depends on it.
_PATH_TOKEN_RE = re.compile(
    r"\b(?:tests|conformance|src|schema|docs)/[A-Za-z0-9_\-./*]*\.[A-Za-z0-9]+\b"
)


def _collect_path_tokens_from_text(text: str) -> "set[str]":
    return set(_PATH_TOKEN_RE.findall(text))


def _collect_path_tokens_from_json_strings(obj) -> "set[str]":
    found: "set[str]" = set()
    if isinstance(obj, str):
        found |= _collect_path_tokens_from_text(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            found |= _collect_path_tokens_from_json_strings(v)
    elif isinstance(obj, list):
        for v in obj:
            found |= _collect_path_tokens_from_json_strings(v)
    return found


#: §8a.1 is its own subsection, ending at the next "## " or "### "
#: heading; §20a/§20a.1/§20a.2 are a CONTIGUOUS cluster ending at §21.
#: Deliberately NOT the whole span between §8a.1 and §21 (§9's own nD
#: grammar section sits in between and cites an unrelated repo,
#: versum's own ``src/versum/...`` paths — those are a different
#: codebase's paths, never claims THIS repo makes about itself).
_SPEC_SECTION_MARKERS = (
    ("### §8a.1", ("## §", "### §")),
    ("## §20a ", ("## §21",)),
)


def _extract_spec_xref_sections(spec_text: str) -> str:
    chunks = []
    for start_marker, end_markers in _SPEC_SECTION_MARKERS:
        start = spec_text.find(start_marker)
        if start == -1:
            continue
        search_from = start + len(start_marker)
        end = len(spec_text)
        for em in end_markers:
            pos = spec_text.find(em, search_from)
            if pos != -1:
                end = min(end, pos)
        chunks.append(spec_text[start:end])
    return "\n".join(chunks) if chunks else spec_text


def _all_cited_paths() -> "set[str]":
    paths: "set[str]" = set()
    for vector_path in VECTORS_DIR.rglob("*.json"):
        doc = json.loads(vector_path.read_text(encoding="utf-8"))
        paths |= _collect_path_tokens_from_json_strings(doc)
    spec_text = SPEC_PATH.read_text(encoding="utf-8")
    paths |= _collect_path_tokens_from_text(_extract_spec_xref_sections(spec_text))
    return paths


@pytest.mark.parametrize("cited_path", sorted(_all_cited_paths()))
def test_every_cited_provenance_path_exists(cited_path):
    if "*" in cited_path:
        # a glob-shaped citation (e.g. "conformance/vectors/clause-cues/
        # xref-v2-*.json") names a FAMILY, not one file — the family's
        # own directory must exist and contain at least one matching file.
        glob_dir = Path(cited_path).parent
        pattern = Path(cited_path).name
        assert (ROOT / glob_dir).is_dir(), f"cited glob directory missing: {glob_dir}"
        assert list((ROOT / glob_dir).glob(pattern)), f"cited glob matches nothing: {cited_path}"
        return
    assert (ROOT / cited_path).exists(), f"cited provenance path does not exist: {cited_path}"


def test_at_least_one_cited_path_was_found():
    """A sanity check on the extractor itself — if this ever returns zero,
    the regex (or the spec-section slice) is broken, not "nothing to
    check"."""
    assert len(_all_cited_paths()) >= 2
