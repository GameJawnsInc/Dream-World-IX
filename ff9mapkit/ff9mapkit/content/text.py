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

# THE SPEAKER CONVENTION (census 2026-07-18: 12,711 stock entries across 33 field blocks). FF9 has no
# name-box; attribution is authored INTO the text, and the real game's form is NOT "Name: line" -- it is
#
#     Name\n“line”        (the name on its own line, then the dialogue in literal curly quotes)
#
# 9,009/12,711 sampled entries (70.9%) use exactly this; ZERO stock entries use a colon join. The
# quotes are ordinary UTF-8 glyphs (U+201C/U+201D -- the engine has no speaker/quote concept at all;
# FFIXTextTagCode/Dialog render them like any letter), opening once on the first dialogue line and
# closing once on the last (wrapped interior lines carry neither). The name may be a literal string
# ("Dali Villager", "Black Waltz No. 1"), a renameable-character tag ([ZDNE]/[VIVI]/... -> the player's
# chosen name), or a variable ([TEXT=0,0] -- the save moogles' own roster identity). Unattributed text
# (28.9% -- system windows, signs, narration) has NO name line and NO quotes. The one stock sibling
# convention: a SILENT THOUGHT is Name\n(line) -- parentheses, no quotes ([ZDNE]\n(Hmm?  She sure is
# dressed funny...)); with_speaker auto-detects a fully-parenthesized line and emits that form.
QUOTE_OPEN = "“"      # “ -- a literal glyph in the entry bytes, not a tag
QUOTE_CLOSE = "”"     # ”

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

# --- the save-moogle MENU window shape (stock field 300 txids 3/4/5/6, read from the install) --------
# A save moogle's own windows are not plain dialogue. Stock's menu head is, byte for byte:
#
#     [PCHM=7,6][WDTH=0,2,6,0,-1][IMME][FEED=2][TEXT=0,0]\n[FEED=4]“Can I help you, kupo?”\n[CHOO]...
#
# Three things beyond the ordinary dialogue shape, all decoded from Memoria:
#   * [IMME]  -- the window pops instantly (a selector, not speech). EVERY stock moogle window has it.
#   * [FEED=n] -- DialogBoxSymbols.OnFeed: ``modifiers.extraOffset.x += n * ResourceXMultipier``, i.e. a
#     HORIZONTAL indent, and it is skipped inside the [CHOO] rows (``if (!modifiers.choice)``). Stock
#     indents the name line by 2 and every dialogue line by 4. A PLAIN moogle line (txid 6, the
#     no-tents window) carries [IMME] but NO feed -- feeds ride the CHOICE windows only.
#   * [WDTH=...] -- OnWidths: repeating ``lineIndex, lineWidth, <sub-params...>, -1`` groups, where each
#     ``6,<var>`` sub-param adds the RENDERED width of ``[TEXT=0,<var>]`` and the total feeds
#     ``dialog.WidthHint``. It exists so a window whose speaker is a runtime VARIABLE still reserves the
#     right frame width -- which is exactly what a moogle's roster-name speaker needs.
MENU_FEED_NAME = 2         # [FEED=2] on the speaker line
MENU_FEED_LINE = 4         # [FEED=4] on each dialogue line
_TEXTVAR_RE = re.compile(r"\[TEXT=0,(\d+)\]")
# [MPOS=x,y] -- DialogBoxSymbols.OnDialogPosition: `dialog.Position = new Vector2(x, y)`. Decoded from
# `Dialog.InitializeDialogTransition` (2026-07-18):
#   * setting Position **nulls `this.Po`**, so the window leaves auto-position-near-the-speaker mode
#     and takes the ABSOLUTE branch;
#   * there, `(x, y)` is the window's **TOP-LEFT corner**, y measured DOWN from the top of the content
#     area (`posY = UIContentSize.y - posY - size.y/2` re-centres it), scaled by ResourceYMultipier;
#   * the absolute branch never calls `setTailAutoPosition`, so a pinned window draws NO tail -- which
#     is why stock's own pinned entries (field 300 txids 3/4/5) carry no `[TAIL]` at all, while its
#     unpinned plain lines (6/7) do.
# Stock pins every moogle menu: the option list at (20, 16), the sub-windows at (30, 26). That 16-unit
# headroom is what the MOGNET caption (drawn ABOVE the frame) needs -- an unpinned menu grew a line
# with the faithful speaker form and clipped its caption off the top (in-game 2026-07-18), which is
# exactly the bug the pin prevents. So `[[savepoint]]` pins by DEFAULT; `menu_pos` overrides.
MENU_POS_STOCK = ((20, 16), (30, 26))      # (main option list, sub-windows) -- field 300 txids 3 / 4,5


def menu_pos_tag(pos) -> str:
    """``[MPOS=x,y]`` for a ``(x, y)`` pair, or ``""`` for ``None`` (the engine's own placement)."""
    if not pos:
        return ""
    x, y = (int(v) for v in pos)
    return f"[MPOS={x},{y}]"


def width_hint(speaker, base: int = MENU_FEED_NAME) -> str:
    """The ``[WDTH]`` frame-width hint for a window whose SPEAKER is a runtime variable
    (``[TEXT=0,n]``) -- ``""`` for a literal name (the engine measures those itself). ``base`` is the
    line's fixed width; stock uses its own feed indent (2) for the name line."""
    m = _TEXTVAR_RE.fullmatch(str(speaker or "").strip())
    return f"[WDTH=0,{int(base)},6,{m.group(1)},-1]" if m else ""


def menu_style(text: str, *, speaker=None, feeds: bool = True) -> str:
    """Dress an already-attributed (and already-wrapped) line as a save moogle's OWN window: the
    ``[WDTH]`` hint when the speaker is a variable, ``[IMME]``, and -- for a CHOICE window
    (``feeds=True``) -- stock's per-line ``[FEED]`` indents (the name line 2, every other line 4).

    Runs AFTER :func:`wrap_text` so each wrapped line gets its own indent, exactly as stock's own
    multi-line moogle windows do (field 300 txid 5 feeds both lines of its tent prompt). Stock's tag
    order is ``[MPOS][PCHC/PCHM][WDTH][IMME][FEED]``; the caller composes the leading two (see
    :func:`menu_pos_tag`) and this supplies everything from ``[WDTH]`` on."""
    lines = str(text).split("\n")
    if feeds:
        named = bool(speaker) and len(lines) > 1
        lines = [f"[FEED={MENU_FEED_NAME if (named and i == 0) else MENU_FEED_LINE}]{ln}"
                 for i, ln in enumerate(lines)]
    return width_hint(speaker) + CHOICE_IMME + "\n".join(lines)


def with_speaker(speaker, text: str) -> str:
    """Attribute a dialogue line the way the real game does (see the SPEAKER CONVENTION note above)::

        with_speaker("Vivi", "Hello.")   -> "Vivi\\n“Hello.”"      the spoken form
        with_speaker("Vivi", "(Hmm...)") -> "Vivi\\n(Hmm...)"      a fully-parenthesized line = a
                                                                    silent thought -- parens, no quotes
        with_speaker(None, anything)     -> unchanged               narration/system: no name, no quotes

    ``speaker`` may be a literal name, a renameable-character tag (``[ZDNE]``/``[VIVI]``/...), or a
    variable like ``[TEXT=0,0]``. Auto-wrap composes cleanly: the ``\\n`` makes the name its own
    segment, and the quotes glue to the first/last words so a wrapped body keeps ONE quote pair
    spanning all its lines -- exactly the stock shape. (An audible hushed aside -- stock's rare
    ``“(Kupo!)”`` -- is unattributed in the wild; author it as literal text with your own quotes.)"""
    if not speaker:
        return text
    t = str(text)
    if t.startswith("(") and t.endswith(")"):
        return f"{speaker}\n{t}"                        # the silent-thought convention
    return f"{speaker}\n{QUOTE_OPEN}{t}{QUOTE_CLOSE}"


def mes_entry(text: str, txid: int, *, strt: tuple = (10, 1), tail: str = DEFAULT_TAIL) -> str:
    """One ``.mes`` entry line that ADDS dialogue at ``txid`` without touching base text. A falsy ``tail``
    (``""``/``None``) emits NO ``[TAIL]`` tag -- matching FF9's CENTERED system windows (a real grey-ATE title
    window has no tail; a ``[TAIL]`` like ``DEFT``/``UPR`` would nudge it off the true centre)."""
    strt_s = ",".join(str(v) for v in strt)
    tail_s = f"[TAIL={tail}]" if tail else ""
    return f"_[TXID={txid}][STRT={strt_s}]{tail_s}{text}[ENDN]"


def build_mes(lines, *, start_txid: int = DEFAULT_BASE_TXID, tails=None, strts=None) -> tuple[str, dict]:
    """Build a ``.mes`` file body from an ordered list of dialogue strings.

    Returns ``(text, mapping)`` where ``mapping[i]`` is the TXID assigned to ``lines[i]`` (so a
    caller can point each NPC's WindowSync at the right id). TXIDs are ``start_txid + i``.
    ``tails`` (optional) is a per-line list of TAIL codes; ``None``/missing entries use
    :data:`DEFAULT_TAIL`. ``strts`` (optional) is a per-line ``(x, y)`` window geometry; ``None``/missing
    entries use ``mes_entry``'s default ``(10, 1)`` -- so existing callers stay byte-identical. (A FF9
    *system* window like the chest's item-get box auto-CENTERS from its ``[STRT=width,lines]``, so it must
    pass its real geometry, not the dialogue default.)
    """
    entries = []
    mapping = {}
    for i, line in enumerate(lines):
        txid = start_txid + i
        mapping[i] = txid
        _t = tails[i] if (tails and i < len(tails)) else None
        tail = DEFAULT_TAIL if _t is None else _t          # None = unspecified -> default; "" = explicit NO tail
        strt = (strts[i] if strts and i < len(strts) and strts[i] else (10, 1))
        entries.append(mes_entry(line, txid, strt=strt, tail=tail))
    return "\n".join(entries) + "\n", mapping


def build_mes_fixed(fixed, *, tails=None, strts=None) -> str:
    """Build ``.mes`` entries at EXPLICIT txids, from ``[(txid, text), ...]``.

    :func:`build_mes` assigns ``start_txid + i`` -- fine for authored dialogue, which lives at 500+ to
    stay clear of a base block. But FF9's own save-Moogle windows reference **low, fixed** ids: the
    moogle-name roster is text entry **0**, the option menu **3**, the save confirm **4**, the Mognet
    submenu **8**, the mail list **11-18**. Reproducing that menu means emitting those exact ids, which
    sequential assignment cannot express.

    **Only legal in a field's OWN minted text block** (``[field] text_block = <fresh id>`` +
    ``register_text_block = true``). A fresh mesID has no base ``.mes`` at all -- ``FF9TextTool.
    GetFieldTextFileName`` is just ``mesID.ToString()`` and ``FieldImporter.LoadInternal`` clears the
    table and reads only that one file -- so txid 0 is as safe as txid 500 there. Writing low ids into a
    SHARED base block (1073, 8, 22, ...) would shadow the base game's text for every field that uses it.
    :func:`build.validate` enforces the minted-block rule; do not bypass it.

    ``tails``/``strts`` are keyed by TXID here (not by position), since there is no positional index.
    """
    tails, strts = tails or {}, strts or {}
    out = []
    for txid, text in sorted(fixed, key=lambda kv: kv[0]):
        _t = tails.get(txid)
        out.append(mes_entry(text, int(txid), strt=(strts.get(txid) or (10, 1)),
                             tail=(DEFAULT_TAIL if _t is None else _t)))
    return ("\n".join(out) + "\n") if out else ""


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
    # the curly quote/apostrophe glyphs the speaker convention now emits (match their straight kin)
    "“": 0.6, "”": 0.6, "‘": 0.3, "’": 0.3,
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
