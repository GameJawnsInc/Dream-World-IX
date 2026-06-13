"""Author field dialogue text (``.mes``).

Memoria loads field text cumulatively across mods: a mod's
``FF9_Data/embeddedasset/text/<lang>/field/<mesId>.mes`` is merged over the base block, and
explicit ``[TXID=n]`` indices let a mod *add* entries without disturbing the base text — as
long as you use indices the base block doesn't occupy (a high TXID like 500+). That is the
trick proven in Session 9: drop a ``<mesId>.mes`` with our line at a high index; the base
text is untouched, our entry is added, and an NPC's WindowSync(... , txid) resolves to it.

Format of one entry::

    _[TXID=500][STRT=10,1][TAIL=UPR]I miss you Zidane[ENDN]

The leading ``_`` (any non-``[STRT=`` character) is required so the parser treats ``[TXID=]``
as a re-index rather than the start of entry 0.
"""

from __future__ import annotations

import re

# A safe starting index for mod-added dialogue (base field blocks don't use these).
DEFAULT_BASE_TXID = 500

# The dialogue window's TAIL — the little pointer that aims at the speaker (FF9's "who's talking"
# cue; there's no separate name-box). Codes map to Dialog.TailPosition (FFIXTextTag.GetTailPosition):
#   UPR/UPL upper-right/left · LOR/LOL lower-right/left · UPC/LOC upper/lower-center
#   ...F variants force that corner · DEFT = engine default/auto-position
TAIL_CODES = {"UPR", "UPL", "LOR", "LOL", "UPC", "LOC",
              "UPRF", "UPLF", "LORF", "LOLF", "DEFT"}
DEFAULT_TAIL = "UPR"

# How a `speaker` name is prefixed onto a line. FF9 has no name-box, so a name is just part of the
# text; ": " is the common readable form. Use a name-variable tag in the speaker for a renameable
# party member, e.g. speaker = "[VIVI]" -> renders the player's chosen name for Vivi.
SPEAKER_SEP = ": "

# Dialogue CHOICE text (one entry holds the prompt + the selectable rows). After the prompt, [CHOO]
# starts the option list and each subsequent newline is one selectable row; [MOVE=18,0] indents each
# row so the selection cursor has room (FF9's exact convention -- see Memoria FFIXTextTagCode). So a
# choice entry's text is:  prompt + CHOICE_OPEN + ("\n" + CHOICE_INDENT).join(options).
CHOICE_INDENT = "[MOVE=18,0]"
CHOICE_OPEN = "\n[CHOO]" + CHOICE_INDENT
# [IMME] = IMMEDIATE display: the window pops fully drawn with NO character-by-character type-on. FF9's own
# shop/menu choices use it (e.g. the Treno Weapon Shop's "What can I do for you?" Buy/Sell menu ends in
# [IMME]) so a SELECTOR feels instant, while story dialogue types out. Appended to a choice entry when the
# [[choice]] sets `instant = true` (the World Hub journey menu turns it on).
CHOICE_IMME = "[IMME]"


def with_speaker(speaker, text: str) -> str:
    """Prefix ``speaker`` onto a dialogue line (``"Vivi: ...">``), or return ``text`` unchanged when no
    speaker. ``speaker`` may be a plain name or an FF9 name tag like ``[ZDNE]`` / ``[VIVI]``."""
    return f"{speaker}{SPEAKER_SEP}{text}" if speaker else text


def mes_entry(text: str, txid: int, *, strt: tuple = (10, 1), tail: str = DEFAULT_TAIL) -> str:
    """One ``.mes`` entry line that ADDS dialogue at ``txid`` without touching base text."""
    strt_s = ",".join(str(v) for v in strt)
    return f"_[TXID={txid}][STRT={strt_s}][TAIL={tail}]{text}[ENDN]"


def build_mes(lines, *, start_txid: int = DEFAULT_BASE_TXID, tails=None) -> tuple[str, dict]:
    """Build a ``.mes`` file body from an ordered list of dialogue strings.

    Returns ``(text, mapping)`` where ``mapping[i]`` is the TXID assigned to ``lines[i]`` (so a
    caller can point each NPC's WindowSync at the right id). TXIDs are ``start_txid + i``.
    ``tails`` (optional) is a per-line list of TAIL codes; ``None``/missing entries use
    :data:`DEFAULT_TAIL`, so existing callers stay byte-identical.
    """
    entries = []
    mapping = {}
    for i, line in enumerate(lines):
        txid = start_txid + i
        mapping[i] = txid
        tail = (tails[i] if tails and i < len(tails) and tails[i] else DEFAULT_TAIL)
        entries.append(mes_entry(line, txid, tail=tail))
    return "\n".join(entries) + "\n", mapping


# --------------------------------------------------------------------------- proportional auto-wrap
# FF9 field dialogue does NOT auto-wrap: the window grows to fit the widest line, so an un-broken long
# line runs off the screen. The original game hand-breaks every line; we reproduce that at build time.
#
# Why this is PROPORTIONAL and not pixel-exact (from Memoria source): the field dialogue font is a
# *runtime dynamic TrueType* font -- EncryptFontManager.InitializeFont ->
# Font.CreateDynamicFontFromOSFont(Configuration.Font.Names, ...), default the bundled "TBUDGoStd-Bold",
# overridable in Memoria.ini [Font]. Glyph widths come from Unity's TTF rasterizer at a configurable
# size, per language (NGUIText.GetGlyphWidth -> mTempChar.advance). So there is NO fixed pixel-width
# table to ship and exact-per-install wrapping is impossible offline. Instead we model RELATIVE glyph
# widths for a bold proportional sans ('W'/'m' ~3x 'i'/'l') and wrap at a conservative width budget --
# accurate where it matters (it respects glyph widths) and erring toward wrapping a hair early so it
# never overflows. Tune `wrap` per field for fuller lines (one in-game check finds your true max).

# max rendered line width, in "width units" (~ average characters). Conservative by default.
DEFAULT_WRAP_WIDTH = 28.0
_DEFAULT_GLYPH_W = 1.0

# relative advances for a bold proportional sans (em-ish; a typical letter ~0.9). Approximate by design.
_GLYPH_W = {
    " ": 0.5,
    "'": 0.3, "|": 0.3, "`": 0.3, ".": 0.4, ",": 0.4, ";": 0.4, ":": 0.4,
    "!": 0.45, "i": 0.45, "j": 0.45, "l": 0.45, "I": 0.5,
    "(": 0.5, ")": 0.5, "[": 0.5, "]": 0.5, "/": 0.5, "\\": 0.5,
    "f": 0.55, "t": 0.55, '"': 0.6, "-": 0.6, "r": 0.6,
    "s": 0.75, "J": 0.75, "?": 0.9,
    "m": 1.45, "w": 1.4, "M": 1.6, "W": 1.6, "@": 1.6, "&": 1.25,
}
for _c in "abcdeghknopquvxyz":
    _GLYPH_W.setdefault(_c, 0.9)
for _c in "ABCDEFGHKLNOPQRSTUVXYZ":
    _GLYPH_W.setdefault(_c, 1.15)
for _c in "0123456789":
    _GLYPH_W.setdefault(_c, 0.95)

_TAG_RE = re.compile(r"\[[^\]]*\]")
# tags render nothing (color/format/control) EXCEPT name/variable tags, which render text at runtime.
_NAME_TAGS = {"ZDNE", "VIVI", "DGGR", "STNR", "FRYA", "QUIN", "EIKO", "AMRT",
              "PTY1", "PTY2", "PTY3", "PTY4"}


def _tag_render_width(tag: str) -> float:
    code = tag[1:-1].split("=", 1)[0].strip().upper()      # "[VIVI]" -> "VIVI"; "[ICON=5]" -> "ICON"
    if code in _NAME_TAGS:
        return 6.0          # a (renameable) party name; ~6 characters
    if code in ("TEXT", "NUMB", "ITEM", "ICON"):
        return 4.0          # an inserted variable / item name / icon; rough
    return 0.0              # color / format / page / control tag -> no glyphs


def measure(text: str) -> float:
    """Approximate rendered width of a dialogue line in width units (~average characters). Literal
    ``[...]`` tag brackets are not counted; their *rendered* content is (a name tag ~ a name, a color
    tag ~ nothing). Approximate by design -- see the module note on why pixel-exact is impossible."""
    total, i = 0.0, 0
    for m in _TAG_RE.finditer(text):
        total += sum(_GLYPH_W.get(c, _DEFAULT_GLYPH_W) for c in text[i:m.start()])
        total += _tag_render_width(m.group())
        i = m.end()
    total += sum(_GLYPH_W.get(c, _DEFAULT_GLYPH_W) for c in text[i:])
    return total


def wrap_text(text: str, width: float = DEFAULT_WRAP_WIDTH):
    """Break ``text`` into lines that each fit within ``width`` units, reproducing FF9's hand-broken
    dialogue. Existing ``\\n`` and ``[PAGE]`` breaks are respected (each page/line wrapped on its own),
    and a segment that already fits is kept BYTE-IDENTICAL (so short lines never change). Returns
    ``(wrapped, overflow)`` where ``overflow`` lists single words too wide to fit on a line alone."""
    overflow = []
    out_pages = []
    for page in text.split("[PAGE]"):
        out_lines = []
        for seg in page.split("\n"):
            if measure(seg) <= width:
                out_lines.append(seg)                      # already fits -> verbatim
                continue
            cur = ""
            for word in seg.split(" "):
                if measure(word) > width:
                    overflow.append(word)                  # an unbreakable, over-wide single word
                cand = f"{cur} {word}" if cur else word
                if cur and measure(cand) > width:
                    out_lines.append(cur)
                    cur = word
                else:
                    cur = cand
            out_lines.append(cur)
        out_pages.append("\n".join(out_lines))
    return "[PAGE]".join(out_pages), overflow


def overflow_lines(text: str, width: float = DEFAULT_WRAP_WIDTH):
    """Final wrapped lines that STILL exceed ``width`` -- i.e. an unbreakable over-wide word (a long
    name/URL). Empty list = everything fits after wrapping. Used to warn at build time."""
    wrapped, _ = wrap_text(text, width)
    bad = []
    for page in wrapped.split("[PAGE]"):
        bad.extend(ln for ln in page.split("\n") if measure(ln) > width)
    return bad
