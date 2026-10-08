# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""EXAMPLE nD grammars demonstrating the §9 contract — NOT part of 5D itself.

Owner-approved integration step (2026-10-02): the winning build's design
(candidate C, the lexical "term" grammar) and its grafted requirement
grammar (candidate D+), shipped as REFERENCE nD grammars so §9's contract
has a worked, runnable example beyond the deontic/topos planes this
specification already cites. Neither module here is 5D (§1's scope is
unchanged); both attach to 5D exactly the way any third-party nD grammar
would — through a published ``NDSystem``/descriptor (§9), never by adding
a sixth dimension or by this package privileging its own grammar over any
other's.
"""
from __future__ import annotations

from . import requirement, term

__all__ = ["term", "requirement"]
