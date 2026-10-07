# SPDX-License-Identifier: MIT
# Copyright 2026 flxk1
"""The clause/list-item segmenter — spec/SPEC.md §21-§23, codebook
`typed-statements` v3.5's own Unitisation rules.

This design was chosen through a comparison of three independently
built segmenters, each scored against the same development-set
clause-span metric. The recursive-descent grammar won. This module is
that winning design, ported into this package — the architecture,
lexicon and grammar below are copied, with attribution, from the
comparison's own `candidate-2/segmenter.py` (a local, un-shipped
results directory, not part of this repository) — and then grafted per
the comparison's own decision with pieces from the two runners-up:

* **(a)** layout-independent list detection (`candidate-1`'s own
  `_BLOCK_MARK_RE`/`_block_markers`/`_marker_type`, with roman/letter
  disambiguation and em-dash/colon + newline chapeau handling), wired in
  as a FALLBACK after the blank-line vertical-list path finds nothing.
* **(b)** the inline-list reference filter (`candidate-3`'s own
  `_find_list`): a parenthesised marker counts as a list START only
  right after a newline or one of `: ; — ,` (never a bare mid-sentence
  reference, "points (a) and (b) of Article 6"); candidate-2's own
  `find_inline_list` already required a run of >= 2 SEQUENTIAL labels
  and a DASH lead-in — this graft widens the lead-in to also accept `:`
  and `;`, keeping the sequential/>=2 guard unchanged.
* **(c)** coordination WITHOUT a comma before "and" (`candidate-3`'s own
  `_coordination_cuts`/`_subject_then_finite`), behind
  `Config.coord_clause_no_comma` — defaults ON (codebook R-i: a
  coordinated clause with its own subject is a sibling clause whether or
  not a comma precedes the coordinator).
* **(d)** `np_chunks()` (`candidate-3`'s own), ported onto THIS module's
  own tokenizer: a maximal noun-phrase chunk, modals/auxiliaries/
  subordinators/relative-pronouns excluded (R-k — a modal is never
  inside an endpoint span), the leading `a`/`an`/`the` stripped (R-q).
* **(e)** a LINGUISTIC chapeau-completeness test (`candidate-1`'s own
  `_chapeau_is_complete`), run ALONGSIDE (never replacing) the 140-
  character threshold — `Config.chapeau_linguistic_complete`. BUILT and
  available, but MEASURED to cost 0.0051 mean dev F1 on its own (0.8769
  -> 0.8718) — outside the competition's own "~0.002" adoption
  tolerance — so it defaults OFF (never silently dropped; the measured
  number is what decided it, recorded in `docs/decisions/
  0011-segmenter-integration.md`).
* **(f)** an IMMUTABLE `Config` dataclass with `with_overrides()`
  (`candidate-1`'s own pattern), replacing the base design's global
  mutable `CONFIG` dict — every parsing method takes `cfg` explicitly.

Public interface (UNCHANGED from the competition winner):

    segment(unit_text, *, enclosing_provision=None, cfg=DEFAULT_CONFIG) -> list[dict]

Each dict is ``{"start", "end", "kind", "parent", "inherits_subject_from"}``
with CHARACTER offsets into ``unit_text``; ``kind`` is one of
``sentence``, ``clause``, ``list_item``, ``chapeau``. Output is a pure
function of the input text (stdlib only, no randomness, no I/O).
``enclosing_provision`` is accepted for interface compatibility; the
grammar does not need it (it is not used to change any span).

Stdlib only.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Optional

__all__ = [
    "segment", "tokenize", "Token", "Config", "DEFAULT_CONFIG", "with_overrides",
    "np_chunks",
    "coordinated_subject_conjuncts", "clean_np_chunks",
    "smallest_complete_clause_span", "smallest_complete_clause_spans",
    "inherited_subject_spans", "relative_clause_antecedent_spans",
    "coordinated_shared_subject_spans",
]

# --------------------------------------------------------------------------
# Lexicon (candidate-2's own, verbatim)
# --------------------------------------------------------------------------
MODALS = frozenset(
    "shall may must should could would will can might cannot".split())
BE_HAVE = frozenset("is are was were has have had does do did".split())

# Verb stems whose third-person-singular (and, after a plural subject, bare)
# form marks a finite verb. General legal-English vocabulary, hand-listed.
_VERB_STEMS = """
apply mean include require determine consider find fall take enter cease
relate refer constitute concern exceed contain provide set lay specify
remain become seem appear involve affect allow enable ensure establish
exist give grant hold intend lead make need occur operate pose present
produce prove receive reflect result satisfy serve show state submit
suffer support undertake use carry comply act amount arise belong cover
decide demonstrate depend designate entail express face form fulfil
govern identify imply indicate inform keep know limit meet own perform
permit possess prevail process propose put reach recognise regard rely
replace represent request supply transfer treat continue differ benefit
believe expect wish want plan seek fail obtain lack share publish adopt
assess bear confer derive maintain oblige notify place prohibit
""".split()


def _third_singular(stem: str) -> str:
    if stem.endswith("y") and stem[-2:-1] not in ("a", "e", "o", "u"):
        return stem[:-1] + "ies"
    if stem.endswith(("s", "sh", "ch", "x", "z", "o")):
        return stem + "es"
    return stem + "s"


VERB_3SG = frozenset(_third_singular(s) for s in _VERB_STEMS) | {"has", "does"}
VERB_BARE = frozenset(_VERB_STEMS)

DETERMINERS = frozenset(
    "a an the this that these those such each every any all some no its their "
    "his her our your other another both either neither".split())
PREPOSITIONS = frozenset(
    "of in on at by for with without to from into onto upon under over "
    "between among through during within against about after before "
    "pursuant regarding concerning including via per than as".split())
SUBORDINATORS = frozenset(
    "where if when unless whereas while once until since although though "
    "whether because insofar".split())
RELATIVES = frozenset("who which whom whose".split())
CONJ = frozenset(("and", "or"))
# parenthetical openers that sit between a subject and its verb
PARENTHETICAL_HEADS = frozenset(
    "where if when having taking in as subject without notwithstanding "
    "unless after before following inter particular".split())

# Abbreviations after which "." does not end a sentence.
_ABBREV = frozenset(
    "no art arts p pp e.g i.e etc para paras cf ibid op vol ch s ss sch "
    "reg regs mr mrs dr st co ltd inc oj".split())

# --------------------------------------------------------------------------
# Tokens (candidate-2's own, verbatim)
# --------------------------------------------------------------------------
_TOKEN_RE = re.compile(
    r"""
    (?P<BLANK>[ \t ]*\n[ \t ]*\n\s*)     # blank line = block break
  | (?P<WS>\s+)
  | (?P<PLABEL>\((?:[a-z]{1,2}|[ivxlc]+|\d{1,3}[a-z]?)\))   # (a) (iv) (12)
  | (?P<NUM>\d+(?:[.,/]\d+)*(?:\.(?=[ \t ]*\n))?(?:\([0-9a-z]+\))*[A-Z]?)
                                                    # 12  6(4)  2016/679  "1." label
  | (?P<WORD>[^\W\d_][\w'’\-]*)
  | (?P<DASH>[—–])
  | (?P<PUNCT>[^\s\w])
    """,
    re.VERBOSE,
)


@dataclass(frozen=True)
class Token:
    kind: str      # WORD NUM PLABEL DASH PUNCT BLANK
    text: str
    start: int
    end: int

    @property
    def low(self) -> str:
        return self.text.lower()


def tokenize(text: str) -> "list[Token]":
    toks: "list[Token]" = []
    for m in _TOKEN_RE.finditer(text):
        k = m.lastgroup
        if k == "WS":
            continue
        toks.append(Token(k, m.group(), m.start(), m.end()))
    return toks


# --------------------------------------------------------------------------
# Parse tree (candidate-2's own, verbatim)
# --------------------------------------------------------------------------
@dataclass
class Node:
    kind: str                       # sentence | clause | list_item | chapeau
    start: int
    end: int
    children: "list[Node]" = field(default_factory=list)
    inherits: "Optional[Node]" = None
    finite: bool = False            # does the node's own text hold a finite verb
    tail: "list[Node]" = field(default_factory=list)   # ';'-continuations of an item
    semi: bool = False              # clause produced by a ';' split


# --------------------------------------------------------------------------
# Label sequences (lists) (candidate-2's own, verbatim)
# --------------------------------------------------------------------------
_LETTERS = [chr(c) for c in range(ord("a"), ord("z") + 1)]
_ROMAN = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
          "xi", "xii", "xiii", "xiv", "xv"]
_DIGITS = [str(n) for n in range(1, 60)]
_STYLES = {"letter": _LETTERS, "roman": _ROMAN, "digit": _DIGITS}


def _label_value(tok: Token) -> "Optional[str]":
    """Bare label value of a token that could be a list label."""
    if tok.kind == "PLABEL":
        return tok.text[1:-1]
    if tok.kind == "NUM" and re.fullmatch(r"\d{1,2}\.", tok.text):
        return tok.text[:-1]
    if tok.kind == "WORD" and re.fullmatch(r"[a-z]{1,4}", tok.text):
        return tok.text
    if tok.kind == "NUM" and re.fullmatch(r"\d{1,2}", tok.text):
        return tok.text
    return None


def _label_next(style: str, value: str) -> "Optional[str]":
    seq = _STYLES[style]
    try:
        i = seq.index(value)
    except ValueError:
        return None
    return seq[i + 1] if i + 1 < len(seq) else None


def _label_successors(style: str, value: str) -> "tuple[str, ...]":
    """Labels that may follow ``value``: the next in sequence, or a UK
    inserted label ("la" after "l", "za" before "a", "1A" after "1")."""
    if style == "letter":
        if value == "za":
            return ("a",)
        base = value[0]
        nxt = _label_next(style, base)
        ins = base + "a" if len(value) == 1 else None
        if len(value) == 2 and value[1] < "z":
            ins = base + chr(ord(value[1]) + 1)
        return tuple(x for x in (nxt, ins) if x)
    nxt = _label_next(style, value)
    return (nxt,) if nxt else ()


_SEPARATORS = (",", ";", ":", ".", "—", "–")


# --------------------------------------------------------------------------
# graft (a): layout-independent list markers — candidate-1's own
# ``_BLOCK_MARK_RE``/``_block_markers``/``_marker_type``, operated on raw
# TEXT (candidate-1's own data model) rather than this module's own token
# stream — used as a FALLBACK, below, when the blank-line vertical-list
# path (candidate-2's own `parse_blocks`) finds nothing.
# --------------------------------------------------------------------------
_BLOCK_MARK_RE = re.compile(
    r"(?m)^[ \t\xa0]*(?:\((?P<p>[a-z]{1,4}|\d{1,3}[a-z]?)\)|(?P<n>\d{1,3})\.)[ \t\xa0]*(?:$|(?=\S))")


def _marker_type(label: str, prev_alpha: "Optional[str]", paren: bool) -> str:
    """Disambiguates a roman-looking label ("i", "v", "x") from the SAME
    letter in an alphabetic sequence — "i" right after letter "h" is the
    letter "i", not the start of a roman-numeral list, and likewise for
    "v" after "u" and "x" after "w"."""
    if label[0].isdigit():
        return "num-p" if paren else "num-d"
    if label in _ROMAN:
        if len(label) == 1:
            expect = {"i": "h", "v": "u", "x": "w"}[label]
            if prev_alpha == expect:
                return "alpha"
        return "roman"
    return "alpha"


def _block_markers(text: str, s: int, e: int) -> "list[tuple[int, int, str, str]]":
    """Every list-item marker in ``text[s:e]`` that starts its own LINE
    (preceded by a newline, or at ``s`` itself) — independent of whether a
    BLANK line separates items (the layout candidate-2's own blank-line
    path alone requires)."""
    marks = []
    prev_alpha = None
    for m in _BLOCK_MARK_RE.finditer(text, s, e):
        if m.group("p") is not None:
            label, paren = m.group("p"), True
        else:
            label, paren = m.group("n"), False
        ls = m.start()
        if ls > 0 and text[ls - 1] != "\n" and ls != s:
            continue
        t = _marker_type(label, prev_alpha, paren)
        if t == "alpha":
            prev_alpha = label
        mstart = text.index("(" if paren else label, m.start())
        marks.append((mstart, m.end(), label, t))
    return marks


# --------------------------------------------------------------------------
# graft (e): linguistic chapeau-completeness (candidate-1's own
# ``_chapeau_is_complete``) — run ALONGSIDE the 140-character threshold,
# never replacing it (`Config.chapeau_linguistic_complete`).
# --------------------------------------------------------------------------
_OPEN_END_WORDS = frozenset(
    "to of for with by from in on at under against as include includes "
    "including contain contains shall may must should can will is are be "
    "means mean have has the a an following and or than such into upon "
    "about between".split()
)
_FOLLOWING_RE = re.compile(r"\b(?:the\s+following|as\s+follows)\b", re.IGNORECASE)
_FINITE_WORDS_FOR_COMPLETENESS = MODALS | BE_HAVE | VERB_3SG | VERB_BARE


def _chapeau_is_complete(text: str) -> bool:
    """A chapeau is a clause of its own only if it is COMPLETE without its
    items: it does not end on an open function word ("applies to", "shall
    include", "may") and does not point forward with "the following"."""
    t = text.strip(" \t\n\r\xa0:—–-,;")
    if not t:
        return False
    if _FOLLOWING_RE.search(t):
        return False
    words = [w.lower() for w in re.findall(r"[\w’'-]+", t)]
    if not words:
        return False
    lw = words[-1]
    if lw in _FINITE_WORDS_FOR_COMPLETENESS or lw in DETERMINERS:
        return False
    if lw in _OPEN_END_WORDS:
        prev = words[-2] if len(words) > 1 else ""
        return not (
            prev in _FINITE_WORDS_FOR_COMPLETENESS or prev in DETERMINERS
            or prev.endswith(("ed", "ing")) or prev in _OPEN_END_WORDS
        )
    return True


# --------------------------------------------------------------------------
# graft (d): np_chunks() — candidate-3's own algorithm, ported onto THIS
# module's own tokenizer/lexicon (R-k: no modal inside a chunk; R-q: a
# leading a/an/the is stripped from the span).
# --------------------------------------------------------------------------
_NP_STOP = MODALS | BE_HAVE | SUBORDINATORS | RELATIVES
_NP_VERB_WORDS = VERB_3SG | VERB_BARE


def np_chunks(text: str) -> "list[tuple[int, int]]":
    """Maximal noun-phrase chunks as ``(start, end)`` character offsets. A
    chunk starts at a determiner or an open-class word and runs over
    open-class words, determiners, "of"-phrases and in-chunk coordination
    of modifiers, stopping at any modal, auxiliary/finite verb,
    subordinator, relative pronoun, or clause punctuation. A modal is
    NEVER inside a chunk (R-k); a leading "a"/"an"/"the" is excluded from
    the span (R-q)."""
    toks = tokenize(text)
    stop_idx = set()
    for i, t in enumerate(toks):
        if t.kind == "WORD" and (t.low in _NP_STOP or t.low in _NP_VERB_WORDS):
            stop_idx.add(i)
    chunks: "list[tuple[int, int]]" = []
    i, n = 0, len(toks)
    while i < n:
        t = toks[i]
        is_word_like = t.kind in ("WORD", "NUM")
        if not is_word_like or i in stop_idx or t.low in PREPOSITIONS or t.low in CONJ:
            i += 1
            continue
        j = i
        while j < n:
            tj = toks[j]
            if j in stop_idx:
                break
            if tj.kind in ("WORD", "NUM") or tj.text in "’'-()":
                if tj.low in PREPOSITIONS and tj.low != "of":
                    break
                if tj.low == "of" and (j + 1 >= n or toks[j + 1].kind not in ("WORD", "NUM")):
                    break
                if tj.low in CONJ:
                    if j + 1 < n and (j + 1) not in stop_idx and toks[j + 1].kind in ("WORD", "NUM"):
                        j += 1
                        continue
                    break
                j += 1
                continue
            break
        while j > i and (toks[j - 1].low in CONJ | {"of"} | DETERMINERS or toks[j - 1].text in "(-"):
            j -= 1
        k = i
        if k < j and toks[k].low in ("a", "an", "the"):
            k += 1
        if k < j:
            chunks.append((toks[k].start, toks[j - 1].end))
        i = max(j, i + 1)
    return chunks


# --------------------------------------------------------------------------
# graft (f): immutable Config, replacing the base design's global mutable
# CONFIG dict — candidate-1's own pattern.
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class Config:
    chapeau_min_chars: int = 140
    emit_sub_clause: bool = False
    emit_main_after_sub: bool = False
    split_coordination: bool = True
    coord_first_from_sentence_start: bool = True
    coord_bare_and_modal: bool = True
    coord_clause: bool = True
    #: graft (c) — codebook R-i: a coordinated clause with its own
    #: subject is a sibling clause whether or not a comma precedes the
    #: coordinator ("...and the board shall..." as well as "..., and the
    #: board shall..."). Defaults ON.
    coord_clause_no_comma: bool = True
    coord_asyndetic_modal: bool = False
    coord_while: bool = True
    item_coord_clause: bool = True
    item_semicolon_tail: bool = True
    inline_nested: bool = True
    chapeau_two_finite: bool = False
    keep_whole_when_split: bool = True
    heading_numpair: bool = True
    relative_split: bool = True
    relative_emit_rel: bool = False
    subchapeau_clause: bool = False
    continuation_lists: bool = False
    #: graft (e) — the linguistic completeness test, alongside the
    #: character threshold. MEASURED on dev: alone, it moves mean F1
    #: 0.8769 -> 0.8718 (-0.0051) — OUTSIDE the "~0.002" adoption
    #: tolerance the competition's own decision set, so it defaults OFF
    #: here (available, measured, not silently dropped — see
    #: `docs/decisions/0011-segmenter-integration.md`).
    chapeau_linguistic_complete: bool = False
    #: graft (a) — layout-independent list detection as a fallback after
    #: the blank-line path.
    layout_independent_lists: bool = True
    #: graft (b) — an inline list may also start right after ":"/";", not
    #: only a dash.
    inline_list_colon_semicolon_lead_in: bool = True


DEFAULT_CONFIG = Config()


def with_overrides(**kw) -> Config:
    """``DEFAULT_CONFIG`` with some fields overridden — candidate-1's own
    convenience constructor."""
    return replace(DEFAULT_CONFIG, **kw)


# --------------------------------------------------------------------------
# The grammar (candidate-2's own, with the grafts folded in)
# --------------------------------------------------------------------------
class _Parser:
    def __init__(self, text: str, cfg: Config = DEFAULT_CONFIG):
        self.text = text
        self.cfg = cfg
        self.toks = tokenize(text)
        # finite-verb flags and their prefix sums: has_finite() is O(1)
        self._fin = [self._is_finite(k) for k in range(len(self.toks))]
        self._cum = [0]
        for f in self._fin:
            self._cum.append(self._cum[-1] + f)

    # ---- small helpers ---------------------------------------------------
    def low(self, i: int) -> str:
        return self.toks[i].low if 0 <= i < len(self.toks) else ""

    def kind(self, i: int) -> str:
        return self.toks[i].kind if 0 <= i < len(self.toks) else ""

    def span(self, i: int, j: int) -> "tuple[int, int]":
        """Char span of tokens [i, j), trimmed of edge separators and of
        a dangling coordinator — round-6 fix: UNCONDITIONALLY, whether
        or not a comma/semicolon precedes it ("...; or" AND the bare,
        no-comma coordination graft (c) now also produces, "...and").
        A trailing bare coordinator is never part of either span it
        would otherwise dangle off of; trimming it is a no-op when
        there was no comma to begin with, and exposes the comma for the
        SEPARATORS branch, above, to trim on the next pass when there
        was one."""
        changed = True
        while changed and j > i:
            changed = False
            if self.toks[j - 1].kind == "BLANK" or self.toks[j - 1].text in _SEPARATORS:
                j -= 1
                changed = True
            elif j - i >= 1 and self.low(j - 1) in CONJ:
                j -= 1
                changed = True
        while i < j and (self.toks[i].kind == "BLANK" or self.toks[i].text in _SEPARATORS):
            i += 1
        if i >= j:
            return (0, 0)
        return self.toks[i].start, self.toks[j - 1].end

    # ---- finite-verb recogniser ------------------------------------------
    def is_finite(self, i: int) -> bool:
        return 0 <= i < len(self._fin) and self._fin[i]

    def _is_finite(self, i: int) -> bool:
        if self.kind(i) != "WORD":
            return False
        w = self.low(i)
        prev = self.low(i - 1)
        if w in MODALS:
            # "May" in a date ("10 May 2023") is the month, not a modal
            if self.toks[i].text == "May" and (self.kind(i - 1) == "NUM" or self.kind(i + 1) == "NUM"):
                return False
            return True
        if w in BE_HAVE:
            return prev != "to" and prev not in MODALS
        if w in VERB_3SG:
            if i == 0 or prev in DETERMINERS or prev in PREPOSITIONS:
                return False
            if self.low(i + 1) == "of":
                return False
            return True
        if w in VERB_BARE:
            # bare present after a relative pronoun ("which apply") or a
            # plural subject noun directly after a determiner ("the providers use")
            if prev in RELATIVES:
                return True
            if prev.endswith("s") and self.kind(i - 1) == "WORD" and \
                    prev not in PREPOSITIONS and \
                    prev not in ("is", "was", "has", "this", "thus", "its", "as"):
                return self.low(i - 2) in DETERMINERS
        return False

    def has_finite(self, i: int, j: int) -> bool:
        i, j = max(i, 0), min(j, len(self._fin))
        return j > i and self._cum[j] - self._cum[i] > 0

    def first_finite(self, i: int, j: int) -> int:
        for k in range(i, j):
            if self.is_finite(k):
                return k
        return -1

    # ---- unit := heading? block+ ----------------------------------------
    def parse_unit(self) -> "list[Node]":
        n = len(self.toks)
        if n == 0:
            return []
        start = self.skip_heading(0, n)
        return self.parse_blocks(start, n)

    _REF_WORDS = frozenset(
        "article articles section sections chapter part schedule annex "
        "regulation regulations directive paragraph paragraphs point points "
        "act order rule rules title no subsection subsections recital".split())

    def skip_heading(self, i: int, j: int) -> int:
        body = self.skip_heading_simple(i, j)
        if body == i and self.cfg.heading_numpair:
            # "<title with a verb> 29 1 This Part applies ..." : a section
            # number directly followed by a subsection number
            limit = min(j, i + 60)
            for k in range(i + 1, limit - 2):
                if self.kind(k) == "NUM" and self.kind(k + 1) == "NUM" and \
                        re.fullmatch(r"\d+[A-Z]?", self.toks[k].text) and \
                        re.fullmatch(r"\d{1,2}[A-Z]?", self.toks[k + 1].text) and \
                        self.toks[k + 2].text[:1].isupper() and \
                        self.low(k - 1) not in self._REF_WORDS and \
                        not any(self.toks[x].text in (".", ";", ":") for x in range(i, k)):
                    return k + 2
        return body

    def skip_heading_simple(self, i: int, j: int) -> int:
        """heading := (WORD | NUM | PUNCT)* NUM+ before a capitalised sentence
        opening, provided the heading itself has no finite verb (UK-style
        "CHAPTER 5 <title> 109 1 A controller may ..."). Returns the token
        index where the body starts."""
        body = i
        k = i
        limit = min(j, i + 80)
        while k < limit:
            t = self.toks[k]
            if t.kind == "BLANK":
                break
            if self.is_finite(k):
                break
            if t.kind == "NUM" and re.fullmatch(r"\d+[A-Z]?", t.text) and \
                    self.low(k - 1) not in self._REF_WORDS:
                nxt = k + 1
                while nxt < j and self.kind(nxt) == "NUM" and \
                        re.fullmatch(r"\d+[A-Z]?", self.toks[nxt].text):
                    nxt += 1
                if nxt < j and self.kind(nxt) == "WORD" and self.toks[nxt].text[:1].isupper():
                    body = nxt
                    k = nxt
                    continue
            k += 1
        return body

    # ---- block := chapeau list | paragraph --------------------------------
    def parse_blocks(self, i: int, j: int) -> "list[Node]":
        """Split at blank lines; a vertical list is a run of blocks where a
        lone label ("(a)", "1.") alternates with item text. graft (a): for
        a BLOCK that is not itself part of that blank-line list shape
        (prose carrying its OWN markers at line-starts, with no blank line
        between a label and its own text), try the layout-independent
        marker scan (`parse_layout_independent_list`) on that one block
        BEFORE falling through to ordinary paragraph/sentence parsing —
        a fallback, tried once per block, never allowed to DISCARD a
        valid ordinary parse of a DIFFERENT block."""
        blocks = self.split_blocks(i, j)
        out: "list[Node]" = []
        b = 0
        found_any_list = False
        while b < len(blocks):
            bi, bj = blocks[b]
            if b + 1 < len(blocks) and self.is_lone_label(blocks[b + 1], first=True) \
                    and not self.is_lone_label(blocks[b]):
                consumed, items = self.parse_vertical_list(blocks, b + 1)
                if items:
                    out.extend(self.make_chapeau(bi, bj, items, own_sentence=True))
                    b = consumed
                    found_any_list = True
                    continue
            if self.is_lone_label(blocks[b], first=True):
                consumed, items = self.parse_vertical_list(blocks, b)
                if items:
                    out.extend(self.make_chapeau(None, None, items))
                    b = consumed
                    found_any_list = True
                    continue
            if self.is_lone_label(blocks[b]) and self.cfg.continuation_lists:
                # a list continued from a previous unit: "(k) ... (l) ..."
                consumed, items = self.parse_vertical_list(blocks, b)
                if items:
                    out.extend(self.make_chapeau(None, None, items))
                    b = consumed
                    found_any_list = True
                else:
                    b += 1
                continue
            if self.is_lone_label(blocks[b]):
                # an item of a list whose chapeau sits in another unit: its
                # subject cannot be inherited within this unit (codebook R-l,
                # R-r), so the label and its item text yield no span
                b += 1
                if b < len(blocks) and not self.is_lone_label(blocks[b]):
                    b += 1
                continue
            if self.cfg.layout_independent_lists:
                fallback = self.parse_layout_independent_list(bi, bj)
                if fallback:
                    out.extend(fallback)
                    found_any_list = True
                    b += 1
                    continue
            out.extend(self.parse_paragraph(bi, bj))
            b += 1
        return out

    # ---- graft (a): layout-independent vertical list, as a fallback -----
    def parse_layout_independent_list(self, i: int, j: int) -> "list[Node]":
        """A vertical list laid out WITHOUT a blank line between items —
        markers alone at the start of a (non-blank-separated) line, found
        by `_block_markers` directly over the raw text. Builds the SAME
        chapeau+item shape `parse_vertical_list` would, from character
        offsets instead of token "blocks"."""
        if i >= j:
            return []
        s0, s1 = (self.toks[i].start, self.toks[j - 1].end)
        marks = _block_markers(self.text, s0, s1)
        if len(marks) < 2:
            return []
        # keep only a STRICTLY sequential run starting at the first label
        # of its own style (a / i / 1), mirroring parse_vertical_list's
        # own "expected" walk.
        first_mark = marks[0]
        first_label = first_mark[2]
        if first_label.isdigit():
            style = "digit"
        elif first_label in _ROMAN:
            style = "roman"
        else:
            style = "letter"
        if first_label not in ("a", "i", "1"):
            return []
        kept = [first_mark]
        expected = _label_next(style, first_label[:1] if style == "letter" else first_label)
        for m in marks[1:]:
            if m[2] == expected:
                kept.append(m)
                expected = _label_next(style, m[2][:1] if style == "letter" else m[2])
        if len(kept) < 2:
            return []
        chapeau_end = kept[0][0]
        items: "list[Node]" = []
        for idx, (mstart, mend, label, _t) in enumerate(kept):
            content_end = kept[idx + 1][0] if idx + 1 < len(kept) else s1
            # trim trailing whitespace/separators from the item's own content
            ce = content_end
            while ce > mend and (self.text[ce - 1].isspace() or self.text[ce - 1] in _SEPARATORS):
                ce -= 1
            cs = mend
            while cs < ce and self.text[cs].isspace():
                cs += 1
            item = Node("list_item", cs, ce, finite=self._span_has_finite_text(cs, ce))
            items.append(item)
        if chapeau_end <= s0:
            return self.make_chapeau(None, None, items)
        # chapeau text sits before the first marker in THIS same range
        chapeau_tok_end = i
        for k in range(i, j):
            if self.toks[k].start >= chapeau_end:
                chapeau_tok_end = k
                break
        else:
            chapeau_tok_end = j
        return self.make_chapeau(i, chapeau_tok_end, items)

    def _span_has_finite_text(self, s: int, e: int) -> bool:
        sub_toks = tokenize(self.text[s:e])
        return any(self._sub_is_finite(sub_toks, k) for k in range(len(sub_toks)))

    def _sub_is_finite(self, toks: "list[Token]", i: int) -> bool:
        if toks[i].kind != "WORD":
            return False
        w = toks[i].low
        return w in MODALS or w in BE_HAVE or w in VERB_3SG or w in VERB_BARE

    def split_blocks(self, i: int, j: int) -> "list[tuple[int, int]]":
        blocks = []
        s = i
        for k in range(i, j):
            if self.toks[k].kind == "BLANK":
                if k > s:
                    blocks.append((s, k))
                s = k + 1
        if j > s:
            blocks.append((s, j))
        return blocks

    def lone_label_value(self, blk) -> "Optional[str]":
        bi, bj = blk
        if bj - bi != 1:
            return None
        t = self.toks[bi]
        if t.kind == "PLABEL" or (t.kind == "NUM" and re.fullmatch(r"\d{1,2}\.", t.text)):
            return _label_value(t)
        return None

    def is_lone_label(self, blk, first=False) -> bool:
        v = self.lone_label_value(blk)
        return v is not None and (not first or v in ("a", "i", "1"))

    def parse_vertical_list(self, blocks, b0):
        """list := (LONE_LABEL item_block+)+ with labels in strict sequence;
        a nested list (roman under letters) is parsed recursively."""
        first = self.lone_label_value(blocks[b0])
        if first.isdigit():
            style = "digit"
        elif first == "i" or (len(first) > 1 and set(first) <= set("ivx")):
            style = "roman"
        else:
            style = "letter"
        items: "list[Node]" = []
        expected = first
        b = b0
        while b < len(blocks) and expected is not None and \
                self.lone_label_value(blocks[b]) == expected:
            label_blk = blocks[b]
            b += 1
            nxt = _label_next(style, expected[:1] if style == "letter" else expected)
            content = []
            while b < len(blocks) and self.lone_label_value(blocks[b]) != nxt:
                if self.is_lone_label(blocks[b], first=True):
                    b2, sub_items = self.parse_vertical_list(blocks, b)
                    if sub_items:
                        content.append(("list", sub_items))
                        b = b2
                        continue
                if self.is_lone_label(blocks[b]):
                    break        # out-of-sequence label: list ends here
                content.append(("blk", blocks[b]))
                b += 1
            items.append(self.make_vertical_item(label_blk, content))
            expected = nxt
        return b, items

    def make_vertical_item(self, label_blk, content) -> Node:
        lab = self.toks[label_blk[0]]
        text_blocks = [c[1] for c in content if c[0] == "blk"]
        sub_lists = [c[1] for c in content if c[0] == "list"]
        if text_blocks:
            fi, fj = text_blocks[0]
            s, e = self.span(fi, fj)
        else:
            fi = fj = label_blk[1]
            s, e = lab.end, lab.end
        item = Node("list_item", s, e, finite=fj > fi and self.has_finite(fi, fj))
        if sub_lists:
            # the item's own text is the nested list's chapeau; its clause
            # span is the item span itself, so no second copy is emitted
            ch = Node("chapeau", s, e)
            for sub in sub_lists:
                for it in sub:
                    it.inherits = ch
                    ch.children.append(it)
            item.children = [ch]
        elif fj > fi:
            self.attach_item_clauses(item, fi, fj)
        # further plain blocks under the item: its own sentences
        for blk in text_blocks[1:]:
            item.children.extend(self.parse_paragraph(*blk))
        return item

    # ---- paragraph := sentence+ ------------------------------------------
    def parse_paragraph(self, i: int, j: int) -> "list[Node]":
        out = []
        for si, sj in self.split_sentences(i, j):
            node = self.parse_sentence(si, sj)
            if node is not None:
                out.append(node)
        return out

    def split_sentences(self, i: int, j: int) -> "list[tuple[int, int]]":
        sents = []
        s = i
        depth = 0
        for k in range(i, j):
            t = self.toks[k]
            if t.text == "(":
                depth += 1
            elif t.text == ")":
                depth = max(0, depth - 1)
            if t.text == "." and t.kind == "PUNCT" and depth == 0 and k + 1 < j:
                prev = self.low(k - 1)
                if prev in _ABBREV or (len(prev) == 1 and prev.isalpha()):
                    continue
                if self.toks[k - 1].end != t.start:
                    continue     # spaced dots: ". . . ." leaders
                nt = self.toks[k + 1]
                if nt.text[:1].isupper() or nt.kind == "NUM" or nt.text in ("“", "\"", "‘"):
                    sents.append((s, k + 1))
                    s = k + 1
        if j > s:
            sents.append((s, j))
        return sents

    # ---- sentence := chapeau list | clause_complex -----------------------
    def parse_sentence(self, i: int, j: int) -> "Optional[Node]":
        # strip a leading paragraph number ("2 The ...", "3. Where ...")
        while i + 1 < j and self.kind(i) == "NUM" and \
                (self.kind(i + 1) == "NUM" or self.toks[i + 1].text[:1].isupper()):
            i += 1
        if i + 2 < j and self.kind(i) == "NUM" and self.toks[i + 1].text == "." and \
                self.toks[i + 2].text[:1].isupper():
            i += 2               # "3. Where ..."
        if i >= j:
            return None
        lst = self.find_inline_list(i, j)
        if lst is not None:
            ch_end, items = lst
            chs = self.make_chapeau(i, ch_end, items)
            if not chs:
                return None
            s, e = self.span(i, j)
            sent = Node("sentence", s, e)
            sent.children.extend(chs)
            return sent
        if not self.has_finite(i, j):
            return None          # verbless heading / fragment: no clause
        s, e = self.span(i, j)
        sent = Node("sentence", s, e)
        sent.children.extend(self.clause_complex(i, j))
        return sent

    # ---- inline (UK style) list:  "— a ..., b ..., and c ..." -----------
    def find_inline_list(self, i: int, j: int):
        """graft (b): the lead-in that STARTS an inline list is a DASH
        (candidate-2's own base case) OR — widened — a `:`/`;` token
        (``Config.inline_list_colon_semicolon_lead_in``), matching
        candidate-3's own "after a newline or one of : ; —" filter. The
        sequential->=2-labels guard (`scan_inline_items`) is UNCHANGED —
        this only widens which token may OPEN the scan, never how many
        labels are needed to confirm it is a real list."""
        for k in range(i, j - 1):
            is_dash = self.toks[k].kind == "DASH"
            is_colon_semi = self.cfg.inline_list_colon_semicolon_lead_in and \
                self.toks[k].kind == "PUNCT" and self.toks[k].text in (":", ";")
            if not (is_dash or is_colon_semi):
                continue
            v = _label_value(self.toks[k + 1])
            if v not in ("a", "i", "1", "za"):
                continue
            style = "roman" if v == "i" else "digit" if v == "1" else "letter"
            bounds = self.scan_inline_items(k + 1, j, style)
            if len(bounds) >= 2:
                return k, [self.make_inline_item(a, b) for a, b in bounds]
        return None

    def scan_inline_items(self, k: int, j: int, style: str):
        """[(label_tok, end_tok)] for a label sequence starting at token k;
        a later label counts only after a separator (",", ";", "or", "and")."""
        bounds = [k]
        cur = _label_value(self.toks[k])
        depth = 0
        p = k + 1
        while p < j:
            allowed = _label_successors(style, cur)
            if not allowed:
                break
            t = self.toks[p]
            if t.text == "(":
                depth += 1
            elif t.text == ")":
                depth = max(0, depth - 1)
            elif depth == 0 and t.kind in ("WORD", "NUM", "PLABEL") and _label_value(t) in allowed:
                prev = self.toks[p - 1]
                if prev.text in (",", ";", ":") or prev.low in CONJ or prev.kind == "DASH":
                    bounds.append(p)
                    cur = _label_value(t)
            p += 1
        if len(bounds) < 2:
            return []
        out = [(b, bounds[n + 1] if n + 1 < len(bounds) else j)
               for n, b in enumerate(bounds)]
        # the last item ends at its first top-level ';' (trailing material
        # such as "...; (and the references in ...)" is not part of it)
        a, b = out[-1]
        depth = 0
        for q in range(a + 1, b):
            tq = self.toks[q].text
            depth += tq == "("
            depth -= tq == ")" and depth > 0
            if tq == ";" and depth == 0:
                out[-1] = (a, q)
                break
        return out

    def make_inline_item(self, a: int, b: int) -> Node:
        body_i = a + 1
        s, e = self.span(body_i, b)
        item = Node("list_item", s, e, finite=self.has_finite(body_i, b))
        # a nested inline list inside this item ("a ...— i ..., ii ...")
        for k in range(body_i, b - 1):
            if self.cfg.inline_nested and self.toks[k].kind == "DASH" and \
                    _label_value(self.toks[k + 1]) == "i":
                sub = self.scan_inline_items(k + 1, b, "roman")
                if len(sub) >= 2:
                    ch_s, ch_e = self.span(body_i, k)
                    ch = Node("chapeau", ch_s, ch_e)
                    if self.has_finite(body_i, k) and self.cfg.subchapeau_clause:
                        ch.children.append(Node("clause", ch_s, ch_e))
                    for x, y in sub:
                        it = self.make_inline_item(x, y)
                        it.inherits = ch
                        ch.children.append(it)
                    item.children = [ch]
                    return item
        self.attach_item_clauses(item, body_i, b)
        return item

    # ---- chapeau ---------------------------------------------------------
    def make_chapeau(self, ci, cj, items: "list[Node]", own_sentence=False) -> "list[Node]":
        if ci is None or cj is None or cj <= ci:
            return items
        s, e = self.span(ci, cj)
        if e <= s:
            return items
        if not self.has_finite(ci, cj) and not any(
                self.has_finite_node(it) for it in items):
            return []            # verbless heading over verbless items
        ch = Node("chapeau", s, e)
        if self.chapeau_is_clause(ci, cj):
            ch.children.append(Node("clause", s, e))
        for it in items:
            it.inherits = ch
            ch.children.append(it)
            for tl in it.tail:
                tl.inherits = ch
                ch.children.append(tl)
        if own_sentence:
            sent = Node("sentence", s, items[-1].end if items else e)
            sent.children.append(ch)
            return [sent]
        return [ch]

    def has_finite_node(self, node: Node) -> bool:
        return node.finite or any(c.finite or c.kind == "clause" for c in node.children)

    def chapeau_is_clause(self, ci: int, cj: int) -> bool:
        """A chapeau carries its own clause span only when it states more
        than 'X shall include the following:' — operationalised as a finite
        chapeau of at least ``cfg.chapeau_min_chars`` characters (a short
        chapeau's content lives in its items, which inherit its subject)
        AND, graft (e), when `cfg.chapeau_linguistic_complete` is on, ALSO
        passing `_chapeau_is_complete` — a chapeau long enough to clear the
        character threshold but still ending on an open function word
        ("...shall be entitled to request from the controller, in
        particular information on:") is NOT its own clause either."""
        if not self.has_finite(ci, cj):
            return False
        s, e = self.span(ci, cj)
        long_enough = e - s >= self.cfg.chapeau_min_chars
        if not long_enough and self.cfg.chapeau_two_finite:
            long_enough = sum(1 for k in range(ci, cj) if self.is_finite(k)) >= 2
        if not long_enough:
            return False
        if self.cfg.chapeau_linguistic_complete:
            return _chapeau_is_complete(self.text[s:e])
        return True

    # ---- item body -------------------------------------------------------
    def attach_item_clauses(self, item: Node, i: int, j: int) -> None:
        """An item made of ';'-separated independent clauses keeps the FIRST
        clause as its own span; each later clause becomes a sibling clause
        (``tail``) under the same chapeau, inheriting its subject."""
        clauses = self.item_clauses(i, j)
        if len(clauses) >= 2 and clauses[0].kind == "clause" and \
                clauses[0].semi and self.cfg.item_semicolon_tail:
            item.start, item.end = clauses[0].start, clauses[0].end
            item.tail = clauses[1:]
            return
        item.children.extend(clauses)

    def item_clauses(self, i: int, j: int) -> "list[Node]":
        """Inside a list item: ';'-coordinated independent clauses and
        ', and NP finite' coordinated clauses each get a clause span."""
        parts = self.split_semicolons(i, j)
        out = []
        if len(parts) >= 2:
            for a, b in parts:
                if self.has_finite(a, b):
                    s, e = self.span(a, b)
                    out.append(Node("clause", s, e, semi=True))
            if len(out) >= 2:
                return out
            out = []
        if self.cfg.item_coord_clause:
            cuts = [c for c in self.coordination_cuts(i, j) if self.low(c) not in MODALS]
            if cuts:
                bounds = [i] + cuts + [j]
                for n in range(len(bounds) - 1):
                    s, e = self.span(bounds[n], bounds[n + 1])
                    if e > s:
                        out.append(Node("clause", s, e))
        return out

    def split_semicolons(self, i: int, j: int) -> "list[tuple[int, int]]":
        parts = []
        s = i
        depth = 0
        for k in range(i, j):
            t = self.toks[k].text
            if t == "(":
                depth += 1
            elif t == ")":
                depth = max(0, depth - 1)
            elif t == ";" and depth == 0 and k + 1 < j and self.low(k + 1) not in CONJ:
                parts.append((s, k))
                s = k + 1
        parts.append((s, j))
        return [(a, b) for a, b in parts if b > a]

    # ---- clause_complex --------------------------------------------------
    def clause_complex(self, i: int, j: int) -> "list[Node]":
        """clause_complex := clause (";" clause)*  where each clause may
        carry an initial sub_clause and coordinated finite VPs."""
        parts = self.split_semicolons(i, j)
        fin_parts = [(a, b) for a, b in parts if self.has_finite(a, b)]
        if len(fin_parts) >= 2:
            nodes = []
            for a, b in fin_parts:
                s, e = self.span(a, b)
                nodes.append(Node("clause", s, e, children=self.clause_parts(a, b)))
            return nodes
        s, e = self.span(i, j)
        parts = self.clause_parts(i, j)
        if parts and not self.cfg.keep_whole_when_split and \
                all(p.start >= s and p.end <= e for p in parts) and len(parts) >= 2:
            return parts
        return [Node("clause", s, e, children=parts)]

    def clause_parts(self, i: int, j: int) -> "list[Node]":
        out: "list[Node]" = []
        main_i = i
        # [sub_clause ","] main_clause
        if self.low(i) in SUBORDINATORS:
            m = self.main_clause_start(i, j)
            if m is not None:
                main_i = m
                if self.cfg.emit_sub_clause:
                    s, e = self.span(i, m)
                    out.append(Node("clause", s, e))
                if self.cfg.emit_main_after_sub:
                    s, e = self.span(m, j)
                    out.append(Node("clause", s, e))
        # main clause followed by a non-restrictive finite relative clause:
        # "NP shall be set, which ... leads to ..." -> the main clause alone
        if self.cfg.relative_split:
            rel = self.nonrestrictive_relative(main_i, j)
            if rel is not None:
                s, e = self.span(i, rel)
                out.append(Node("clause", s, e))
                if self.cfg.relative_emit_rel:
                    s, e = self.span(rel + 1, j)
                    out.append(Node("clause", s, e))
        # coordinated finite VPs / clauses
        if self.cfg.split_coordination:
            cuts = self.coordination_cuts(main_i, j)
            if cuts:
                bounds = [main_i] + cuts + [j]
                for n in range(len(bounds) - 1):
                    a, b = bounds[n], bounds[n + 1]
                    if n == 0 and self.cfg.coord_first_from_sentence_start:
                        a = i
                    s, e = self.span(a, b)
                    if e > s:
                        out.append(Node("clause", s, e))
        return out

    def nonrestrictive_relative(self, i: int, j: int) -> "Optional[int]":
        """Index of the comma opening ", which/who <finite>" when the
        clause before it already holds its own finite verb."""
        depth = 0
        for k in range(i, j - 1):
            t = self.toks[k].text
            depth += t == "("
            depth -= t == ")" and depth > 0
            if depth == 0 and t == "," and self.low(k + 1) in ("which", "who") and \
                    self.has_finite(i, k) and self.has_finite(k + 2, j):
                return k
        return None

    def main_clause_start(self, i: int, j: int) -> "Optional[int]":
        """After an initial subordinate clause, the main clause's subject
        opens the first comma segment (after the subordinate clause's own
        finite verb) that is not a parenthetical and reaches a finite verb
        through parentheticals only."""
        f1 = self.first_finite(i + 1, j)
        if f1 < 0:
            return None
        commas = [k for k in range(f1, j) if self.toks[k].text == ","]
        for c in commas:
            seg = c + 1
            if seg >= j:
                break
            if self.is_parenthetical_head(seg) or self.low(seg) in CONJ:
                continue
            f = self.first_finite(seg, j)
            if f < 0:
                return None
            if f == seg:
                continue          # ", may ..." : a verb, not a subject
            inner = [k for k in commas if seg <= k < f]
            if all(self.is_parenthetical_head(k + 1) for k in inner):
                return seg
        return None

    def is_parenthetical_head(self, k: int) -> bool:
        w = self.low(k)
        return w in PARENTHETICAL_HEADS or (w.endswith("ing") and self.kind(k) == "WORD") \
            or w in ("where", "if", "as", "for", "on", "at", "by", "within", "pursuant",
                     "including", "with", "without", "under", "in", "after", "before")

    def coordination_cuts(self, i: int, j: int) -> "list[int]":
        """Token indices where a coordinated finite VP (", and shall ...")
        or a coordinated clause with its own subject (", and NP <finite>",
        or — graft (c), R-i — "and NP <finite>" with NO preceding comma at
        all when ``cfg.coord_clause_no_comma``) begins."""
        cuts = []
        first_f = self.first_finite(i, j)
        if first_f < 0:
            return cuts
        depth = 0
        for k in range(first_f + 1, j - 1):
            t = self.toks[k].text
            if t == "(":
                depth += 1
            elif t == ")":
                depth = max(0, depth - 1)
            if depth:
                continue
            w = self.low(k)
            if t == "," and self.low(k + 1) in MODALS and self.cfg.coord_asyndetic_modal:
                cuts.append(k + 1)        # "shall adopt X, shall notify Y"
                continue
            if t == "," and w == "," and self.low(k + 1) in ("while", "whereas") \
                    and self.cfg.coord_while and self.has_finite(k + 2, j):
                cuts.append(k + 1)
                continue
            if w not in CONJ and w != "but":
                continue
            nxt = k + 1
            comma = self.toks[k - 1].text == ","
            if self.low(nxt) in MODALS:
                if comma or self.cfg.coord_bare_and_modal:
                    cuts.append(nxt)
                continue
            if w == "but":
                continue
            if self.cfg.coord_clause and (comma or self.cfg.coord_clause_no_comma) and \
                    (self.low(nxt) in DETERMINERS or self.toks[nxt].text[:1].isupper()):
                f = self.first_finite(nxt, min(j, nxt + 12))
                if f > nxt and not any(self.toks[x].text == "," for x in range(nxt, f)) \
                        and self.low(f - 1) not in RELATIVES and self.low(f - 1) != "that":
                    cuts.append(nxt)
        return cuts


# --------------------------------------------------------------------------
# Emission (candidate-2's own, verbatim)
# --------------------------------------------------------------------------
def _emit(nodes: "list[Node]") -> "list[dict]":
    out: "list[dict]" = []
    index: "dict[int, int]" = {}

    def walk(node: Node, parent):
        if node.end <= node.start:
            return
        # a clause identical to its parent clause / item adds nothing
        if node.kind == "clause" and parent is not None:
            p = out[parent]
            if p["kind"] in ("clause", "list_item") and \
                    (p["start"], p["end"]) == (node.start, node.end):
                for c in node.children:
                    walk(c, parent)
                return
            # nor does a duplicate sibling
            if any(d["parent"] == parent and d["kind"] == "clause" and
                   (d["start"], d["end"]) == (node.start, node.end) for d in out):
                return
        idx = len(out)
        index[id(node)] = idx
        out.append({
            "start": node.start,
            "end": node.end,
            "kind": node.kind,
            "parent": parent,
            "inherits_subject_from": None,
            "_inh": id(node.inherits) if node.inherits is not None else None,
        })
        for c in node.children:
            walk(c, idx)

    for n in nodes:
        walk(n, None)
    for d in out:
        inh = d.pop("_inh")
        d["inherits_subject_from"] = index.get(inh) if inh is not None else None
    return out


def segment(unit_text: str, *, enclosing_provision: "Optional[str]" = None,
            cfg: Config = DEFAULT_CONFIG) -> "list[dict]":
    """Segment one legal unit into sentence / chapeau / list_item / clause
    spans (character offsets into ``unit_text``)."""
    if not isinstance(unit_text, str):
        raise TypeError("unit_text must be a str")
    if not unit_text.strip():
        return []
    return _emit(_Parser(unit_text, cfg).parse_unit())


# --------------------------------------------------------------------------
# Every function below is ADDITIVE: it widens the pool of spans
# `extract.hybrid.allowed_spans()` offers, never narrows or replaces
# `np_chunks()`/`segment()`'s own existing output.
# --------------------------------------------------------------------------

def coordinated_subject_conjuncts(text: str) -> "list[tuple[int, int]]":
    """The "antecedent for every coordinated
    clause" half. `np_chunks()` already returns "the controller and the
    processor" as ONE maximal chunk (coordination is absorbed INTO a
    chunk, never split); gold frequently codes each conjunct as its OWN
    Statement's own subject ("controller" alone, "processor" alone).
    For every maximal chunk `np_chunks()` returns that contains an
    internal top-level "and"/"or", this splits it into its own
    conjuncts (each R-q/R-k clean: leading determiner stripped, never a
    modal) — WITHOUT removing the original maximal chunk; a caller
    wanting both calls `np_chunks()` AND this."""
    out: "list[tuple[int, int]]" = []
    for (s, e) in np_chunks(text):
        sub_toks = tokenize(text[s:e])
        if not any(t.kind == "WORD" and t.low in CONJ for t in sub_toks):
            continue
        parts: "list[list[Token]]" = []
        start_i = 0
        for i, t in enumerate(sub_toks):
            if t.kind == "WORD" and t.low in CONJ:
                parts.append(sub_toks[start_i:i])
                start_i = i + 1
        parts.append(sub_toks[start_i:])
        for part in parts:
            part = [t for t in part if t.kind in ("WORD", "NUM")]
            if not part:
                continue
            k = 1 if part[0].low in ("a", "an", "the") else 0
            if k >= len(part):
                continue
            conj_start, conj_end = s + part[k].start, s + part[-1].end
            if conj_end > conj_start:
                out.append((conj_start, conj_end))
    return out


_LIST_LABEL_RE = re.compile(r"^(?:[ivxlc]{1,5}|[a-z]|\d{1,3}[a-z]?)[.)]?$", re.IGNORECASE)
_DANGLING_TRAILING_WORDS = frozenset({"to", "that", "of", "and", "or"})


def clean_np_chunks(text: str) -> "list[tuple[int, int]]":
    """CandidateSet v2, item (c) — a FILTERED view of `np_chunks()`'s
    own maximal chunks: never crosses a newline (dropped outright, not
    shrunk, if it would), never a bare list-label/heading token on its
    own (``"a"``, ``"(iv)"``, ``"12"``...), never a chunk that occupies
    an ENTIRE physical line in isolation between two paragraph breaks
    (a heading like "Interoperability" sitting alone before a list),
    and never ends on a dangling function word ("to", "that", "of",
    "and", "or" — trimmed token-by-token from the right). ADDITIVE:
    `propose()` offers BOTH this and the old maximal `np_chunks()` —
    "keep maximal-NP candidates as well" is the caller's job, not a
    behaviour change to `np_chunks()` itself."""
    out: "list[tuple[int, int]]" = []
    for (s, e) in np_chunks(text):
        if "\n" in text[s:e]:
            continue
        raw = text[s:e].strip()
        if not raw or _LIST_LABEL_RE.match(raw):
            continue
        line_start = text.rfind("\n", 0, s) + 1
        nl = text.find("\n", e)
        line_end = nl if nl != -1 else len(text)
        if text[line_start:line_end].strip() == raw:
            before_ok = line_start == 0 or text[:line_start].endswith("\n")
            after_tail = text[line_end:line_end + 2]
            after_ok = line_end == len(text) or after_tail == "\n\n" or text[line_end:].strip() == ""
            if before_ok and after_ok:
                continue
        toks = tokenize(text[s:e])
        while toks and toks[-1].kind == "WORD" and toks[-1].low in _DANGLING_TRAILING_WORDS:
            toks = toks[:-1]
        if not toks:
            continue
        new_s, new_e = s + toks[0].start, s + toks[-1].end
        if new_e > new_s:
            out.append((new_s, new_e))
    return out


#: CandidateSet v2, item (b) — the codebook's own R-p.1 ("the smallest
#: complete finite clause"): a trailing adverbial PP introduced by one
#: of these explicit, procedural/temporal cues marks the boundary a
#: "smallest complete" clause stops at (the clause's own main verb and
#: its direct complement are complete WITHOUT it). Deliberately a
#: small, explicit list — never a general preposition cut, which would
#: also wrongly truncate an ordinary prepositional OBJECT.
_TRAILING_ADVERBIAL_CUES = (
    "within", "no later than", "not later than", "pursuant to",
    "in accordance with", "without undue delay",
)


def smallest_complete_clause_span(text: str, span: "tuple[int, int]") -> "tuple[int, int]":
    """CandidateSet v2, item (b) — R-p.1: truncates ``span`` at the
    FIRST top-level `SUBORDINATORS` token, or the first
    `_TRAILING_ADVERBIAL_CUES` match, found strictly AFTER its own
    first token — never at position 0 (a clause's own leading
    subordinator, e.g. "Where the controller...", is part of the
    clause, not a trailing adverbial). Returns ``span`` UNCHANGED (never
    narrower, never wider) when no such boundary is found."""
    s, e = span
    sub = text[s:e]
    toks = tokenize(sub)
    if len(toks) < 2:
        return span
    cut = None
    for t in toks[1:]:
        if t.kind == "WORD" and t.low in SUBORDINATORS:
            cut = t.start
            break
        tail = sub[t.start:].lower()
        if any(tail.startswith(cue) for cue in _TRAILING_ADVERBIAL_CUES):
            cut = t.start
            break
    if cut is None:
        return span
    trimmed = sub[:cut].rstrip(" \t,;:")
    if not trimmed.strip():
        return span
    return (s, s + len(trimmed))


def smallest_complete_clause_spans(unit_text: str, segs: "list[dict]") -> "list[tuple[int, int]]":
    """CandidateSet v2, item (b) — `smallest_complete_clause_span()`
    applied to every LEAF clause/list_item node `segment()` already
    found. ADDITIVE alongside the segmenter's own (wider) clause spans,
    never a replacement."""
    return [
        smallest_complete_clause_span(unit_text, (node["start"], node["end"]))
        for node in segs if node["kind"] in ("clause", "list_item")
    ]


def inherited_subject_spans(unit_text: str, segs: "list[dict]") -> "dict[int, tuple[int, int]]":
    """CandidateSet v2, item (a) — the "chapeau subject for every list
    item" half: for every node `segment()` already marked as
    inheriting its subject from another (``inherits_subject_from``,
    today only a chapeau-list item inheriting its own chapeau's
    subject), the ANTECEDENT node's own tightened subject NP — its
    FIRST `np_chunks()` chunk (the codebook's own convention: a
    chapeau/sentence subject sits immediately before its own main
    verb — never simply "the first chunk", which a leading cue phrase
    like "Subject to—" would wrongly give). Returns ``{node_index:
    (start, end)}``, one entry per INHERITING node (so a caller can
    wire it onto that SPECIFIC node's own candidate, "appear as a
    candidate subj where a rule fires" — every list item under a
    chapeau gets its own entry, even where several share the identical
    span)."""
    verb_like = MODALS | BE_HAVE | VERB_3SG | VERB_BARE
    out: "dict[int, tuple[int, int]]" = {}
    for idx, node in enumerate(segs):
        anchor = node.get("inherits_subject_from")
        if anchor is None:
            continue
        anc = segs[anchor]
        anc_text = unit_text[anc["start"]:anc["end"]]
        chunks = np_chunks(anc_text)
        if not chunks:
            continue
        anc_toks = tokenize(anc_text)
        verb_start = next(
            (t.start for t in anc_toks if t.kind == "WORD" and t.low in verb_like), None,
        )
        if verb_start is not None:
            before_verb = [c for c in chunks if c[1] <= verb_start]
            chosen = before_verb[-1] if before_verb else chunks[0]
        else:
            chosen = chunks[0]
        cs, ce = chosen
        out[idx] = (anc["start"] + cs, anc["start"] + ce)
    return out


def relative_clause_antecedent_spans(
    unit_text: str, segs: "list[dict]",
) -> "dict[tuple[int, int], tuple[int, int]]":
    """CandidateSet v2, item (a) — the antecedent-NP half for a FINITE
    non-restrictive relative clause ("NP shall be set, which ... leads
    to ..."). Under `DEFAULT_CONFIG` (``relative_split=True``,
    ``relative_emit_rel=False``) `segment()` never emits the relative
    clause's own tail as a node of its own — only the main-clause-only
    child and its WHOLE parent (main clause + tail) appear in ``segs``.
    The antecedent is still needed as a candidate subj wherever a rule
    fires on that tail span. For every parent/child pair in ``segs``
    where the child is the main-clause-only node `nonrestrictive_relative()`
    produced (same start as its parent, ending strictly before it, with
    a ", which"/", who" tail), this returns ``{tail_span: antecedent}``
    — the tail's OWN span (the relative pronoun and everything after
    it, separators trimmed) mapped to the child's own tightened subject
    NP (first `np_chunks()` chunk before ITS main verb — the SAME
    antecedent-NP convention `inherited_subject_spans()` already uses)."""
    verb_like = MODALS | BE_HAVE | VERB_3SG | VERB_BARE
    out: "dict[tuple[int, int], tuple[int, int]]" = {}
    for node in segs:
        if node["kind"] != "clause":
            continue
        parent = node.get("parent")
        if parent is None:
            continue
        pnode = segs[parent]
        if pnode["start"] != node["start"] or pnode["end"] <= node["end"]:
            continue
        tail = unit_text[node["end"]:pnode["end"]]
        if not re.match(r"^[,;]?\s*(which|who)\b", tail):
            continue
        child_text = unit_text[node["start"]:node["end"]]
        chunks = np_chunks(child_text)
        if not chunks:
            continue
        child_toks = tokenize(child_text)
        verb_start = next(
            (t.start for t in child_toks if t.kind == "WORD" and t.low in verb_like), None,
        )
        if verb_start is not None:
            before_verb = [c for c in chunks if c[1] <= verb_start]
            chosen = before_verb[-1] if before_verb else chunks[0]
        else:
            chosen = chunks[0]
        cs, ce = chosen
        antecedent = (node["start"] + cs, node["start"] + ce)
        tail_start = node["end"]
        while tail_start < pnode["end"] and unit_text[tail_start] in " \t,;":
            tail_start += 1
        if tail_start >= pnode["end"]:
            continue
        out[(tail_start, pnode["end"])] = antecedent
    return out


def coordinated_shared_subject_spans(
    unit_text: str, segs: "list[dict]",
) -> "dict[int, tuple[int, int]]":
    """CandidateSet v2, item (a) — the shared-subject half for a bare
    coordinated finite clause ("X shall A, and shall B."):
    `coordination_cuts()` already yields the SECOND (and later)
    coordinated clause as its OWN sibling node — "shall B" alone, no
    subject text of its own (the subject is elided; it sits only in the
    FIRST coordinated sibling). For every sibling clause node (same
    ``parent``) whose own leading real token is verb-like (no NP
    precedes its own main verb — i.e. this sibling carries no subject
    of its own), this returns the FIRST sibling's own subject NP (first
    `np_chunks()` chunk before ITS verb) as the shared subject — keyed
    by the SUBJECTLESS sibling's own node index, the same ``{node_index:
    (start, end)}`` convention `inherited_subject_spans()` uses."""
    verb_like = MODALS | BE_HAVE | VERB_3SG | VERB_BARE
    by_parent: "dict[Optional[int], list[int]]" = {}
    for idx, node in enumerate(segs):
        if node["kind"] != "clause":
            continue
        by_parent.setdefault(node.get("parent"), []).append(idx)
    out: "dict[int, tuple[int, int]]" = {}
    for parent, idxs in by_parent.items():
        if parent is None or len(idxs) < 2:
            continue
        idxs = sorted(idxs, key=lambda i: segs[i]["start"])
        first = segs[idxs[0]]
        first_text = unit_text[first["start"]:first["end"]]
        first_chunks = np_chunks(first_text)
        if not first_chunks:
            continue
        first_toks = tokenize(first_text)
        v0 = next((t.start for t in first_toks if t.kind == "WORD" and t.low in verb_like), None)
        if v0 is None:
            continue
        before_v0 = [c for c in first_chunks if c[1] <= v0]
        if not before_v0:
            continue
        subj = before_v0[-1]
        shared = (first["start"] + subj[0], first["start"] + subj[1])
        for idx in idxs[1:]:
            node = segs[idx]
            node_text = unit_text[node["start"]:node["end"]]
            node_toks = [t for t in tokenize(node_text) if t.kind in ("WORD", "NUM")]
            if not node_toks or node_toks[0].low not in verb_like:
                continue   # this sibling already has its own subject
            out[idx] = shared
    return out
