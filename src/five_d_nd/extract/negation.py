# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""The extractor's PLUGGABLE negation module.

The codebook's own negation procedure (`docs/codebook/typed-statements-v1.md`
"The procedure for 'uncertain'" / the coder-view's own "Negation" section,
read-only) is a 5-step read of the WHOLE SENTENCE a clause sits in. Model-
model agreement on it FAILED (α 0.774) under v3.4, which a v3.5
redefinition addresses — so this module is a NAMED,
VERSIONED, swappable implementation, never hardwired into the rest of the
extractor: :func:`negate` dispatches by ``version`` to a registered
callable, so ``negation_v35`` can be registered and selected the moment it
lands, with ``negation_v34`` staying available (and the extractor's own
default) until a future decision switches it.

Every negation function has the SAME signature: ``(unit_text, clause_span,
subj_span, predicate, *, force=None) -> one of NEGATION_STATES``. ``force``,
when given, is returned UNCHANGED — some extraction rules (a savings
clause, a negated-scope cue) already know the answer from their own cue
match and do not need the generic scan re-run over it.

Stdlib only.
"""
from __future__ import annotations

import re
from typing import Callable, Optional

__all__ = [
    "NEGATION_STATES",
    "ALWAYS_ABSENT_PREDICATES",
    "NEGATOR_RE",
    "negation_v34",
    "NEGATION_RULES",
    "DEFAULT_NEGATION_VERSION",
    "negate",
    "register_negation_rule",
]

NEGATION_STATES = frozenset({"present", "uncertain", "absent"})

#: R-n (`requires`, `deadline_of`): a negator confined to an antecedent's
#: own content never negates the Statement's own RELATION — both
#: predicates are ALWAYS `negation: "absent"`, by construction, never by
#: a generic scan (see each predicate's own codebook definition).
ALWAYS_ABSENT_PREDICATES = frozenset({"requires", "deadline_of"})

#: Step 1's own closed, pre-digested negator lexicon: "not", "no",
#: "never", "cannot"/"can't", "unable" — and NOTHING else (the codebook
#: is explicit: "a closed, pre-digested list; do not invent new
#: negators"). An `except_when` cue word ("unless", "except", "by way of
#: derogation from", "save where") is NEVER itself a negator — none of
#: those words match this pattern, so no separate exclusion is needed.
NEGATOR_RE = re.compile(r"\b(?:not|never|no|cannot|can't|unable)\b", re.IGNORECASE)


def negation_v34(
    unit_text: str, clause_span: Optional[tuple], subj_span: Optional[tuple],
    predicate: str, *, force: Optional[str] = None,
) -> str:
    """A deterministic APPROXIMATION of the codebook's 5-step procedure
    (v3.4's own negation rule — unchanged by the v3.1-3.4 codebook
    revisions, which touched ten OTHER rules, never this one):

    1. `requires`/`deadline_of` are ALWAYS `"absent"` (R-n) — checked
       first, before any scan.
    2. A negator (:data:`NEGATOR_RE`) found INSIDE the clause span but
       OUTSIDE the subj span → `"present"` (step 3: a negator in the
       same clause, with no doubt what it negates — this module treats
       "outside the antecedent/subj span" as the operational proxy for
       "no doubt", since R-n's own worked examples are exactly this
       shape: the negator sits INSIDE subj, never negating the relation).
    3. No such negator, but one found ELSEWHERE in `unit_text` (outside
       the clause span) → `"uncertain"` (step 4 — a negator whose scope
       relative to THIS clause is unclear; "when in doubt, choose this
       one").
    4. No negator anywhere → `"absent"` (step 2).

    This is a PROXY for the codebook's own sentence-level reasoning, not
    a reproduction of it — it has no parser and cannot tell a double
    negative from an unrelated negator in a neighbouring clause of the
    same unit; where the codebook asks a human coder to judge scope,
    this function asks only "inside this clause, outside the subj span,
    or not". Documented here, not claimed as equivalent.
    """
    if force is not None:
        return force
    if predicate in ALWAYS_ABSENT_PREDICATES:
        return "absent"
    if clause_span is None:
        return "uncertain"
    c_start, c_end = clause_span
    s_start, s_end = subj_span if subj_span else (c_start, c_start)

    in_clause_outside_subj = False
    for m in NEGATOR_RE.finditer(unit_text[c_start:c_end]):
        a, b = c_start + m.start(), c_start + m.end()
        if not (a >= s_start and b <= s_end):
            in_clause_outside_subj = True
            break
    if in_clause_outside_subj:
        return "present"

    for m in NEGATOR_RE.finditer(unit_text):
        if not (c_start <= m.start() < c_end):
            return "uncertain"
    return "absent"


#: version name -> callable, same signature as :func:`negation_v34`. The
#: extractor's own default is :data:`DEFAULT_NEGATION_VERSION` — "v35"
#: is NOT registered here (it does not exist yet); a future session
#: registers it via :func:`register_negation_rule`, this module's own
#: drop-in point, without editing anything else in the extractor.
NEGATION_RULES: "dict[str, Callable]" = {
    "v34": negation_v34,
}
DEFAULT_NEGATION_VERSION = "v34"


def register_negation_rule(version: str, fn: Callable) -> None:
    """Register a new negation implementation under ``version`` (e.g.
    ``"v35"``) — the ONE place a future session wires in the codebook's
    v3.5 redefinition. Raises ``ValueError`` on an empty version name or
    a re-registration of an EXISTING version (never a silent overwrite)."""
    if not isinstance(version, str) or not version:
        raise ValueError("register_negation_rule() requires a non-empty version name")
    if version in NEGATION_RULES:
        raise ValueError(f"negation rule version {version!r} is already registered")
    NEGATION_RULES[version] = fn


def negate(
    unit_text: str, clause_span: Optional[tuple], subj_span: Optional[tuple],
    predicate: str, *, version: str = DEFAULT_NEGATION_VERSION, force: Optional[str] = None,
) -> str:
    """Dispatch to the registered negation rule named ``version``. Raises
    ``KeyError`` for an unregistered version (fail closed — never falls
    back to a different version silently)."""
    fn = NEGATION_RULES[version]
    result = fn(unit_text, clause_span, subj_span, predicate, force=force)
    if result not in NEGATION_STATES:
        raise ValueError(f"negation rule {version!r} returned {result!r}, not one of {sorted(NEGATION_STATES)}")
    return result
