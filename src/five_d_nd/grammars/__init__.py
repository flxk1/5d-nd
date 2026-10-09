# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""EXAMPLE nD grammars demonstrating the §9 contract — NOT part of 5D itself.

The winning build's design
(candidate C, the lexical "term" grammar) and its grafted requirement
grammar (candidate D+), shipped as REFERENCE nD grammars so §9's contract
has a worked, runnable example beyond the deontic/topos planes this
specification already cites. Neither module here is 5D (§1's scope is
unchanged); both attach to 5D exactly the way any third-party nD grammar
would — through a published ``NDSystem``/descriptor (§9), never by adding
a sixth dimension or by this package privileging its own grammar over any
other's.

``interplay`` is a THIRD EXAMPLE nD grammar, added separately: a closed
vocabulary of typed relations BETWEEN legal
instruments (e.g. "GDPR Art. 95 bars a second, additional obligation with
the same objective as the ePrivacy Directive"), read deterministically
from scope clauses by a cue-rule table. See that module's own docstring
for the full account.
"""
from __future__ import annotations

from . import interplay, requirement, term

__all__ = ["term", "requirement", "interplay"]
