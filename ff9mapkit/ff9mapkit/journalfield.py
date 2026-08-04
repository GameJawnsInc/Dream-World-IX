"""The IN-GAME completion dashboard (T1b) -- generated from :mod:`ff9mapkit.journal`'s ONE row catalog.

:mod:`journal` reads a save OFFLINE. This module renders the SAME 48 rows on a field screen: the player
talks to a lectern-tender, picks a category, and one modal window draws that category's live counters,
each read straight out of the save heap by an ``.eb`` expression. Stock Memoria, no engine patch.

THE SUBSTRATE, AND WHY IT IS NOT THE HUD LANE. ``[[behavior.hud]]`` looks like the obvious home and is
the wrong one: ``compile()`` hard-assigns slot ``i`` = value index ``i`` starting at 0 for EVERY strip
(content/behavior.py:2814-2822) and each strip opens its window once behind a ``shown`` latch, so two
strips both write ``gMesValue[0..n]`` every tick and overwrite each other. A two-page hud dashboard
would render plausible-but-WRONG numbers on at least one page with no error anywhere. The right
substrate is the SYNCHRONOUS PAGE: inside a ``[[choice]]`` arm, emit N x
:func:`~ff9mapkit.eb.opcodes.set_text_variable_expr` and THEN a ``WindowSync``. The window is modal
(MES 0x1F), so exactly one page is open at a time and all 8 slots are reusable per page -- the 8-slot
ceiling stops being "8 numbers globally" and becomes "8 numbers per page", which is what makes 7 pages
fit.

THE CEILINGS, all engine-cited, all enforced by :func:`lint_pages` rather than merely documented
(CLAUDE.md s7: a law in a docstring is a wish):

  * **8 live integer slots.** ``ETb.SetMesValue`` clamps scriptID to 0..7 against
    ``gMesValue = new Int32[8]`` (ETb.cs:230-234, EventEngine.Initialize.cs:30).
  * **Denominators are FREE.** ``/24`` is literal text after the tag, not a slot. That roughly halves
    slot pressure and it is the reason the widest page still fits in 7.
  * **Windows PAGE, they never scroll** -- ~13 lines at DialogLineHeight 68.
  * **Width is baked ONCE at open** from the widest RENDERED line (``Dialog.AutomaticSize``); a later
    value change re-parses but never re-sizes -- which is why :func:`page_body` publishes every value
    BEFORE ``WindowSync``. The header's ``=`` rule is then grown by :func:`render_page` until it
    out-measures every line, so the rule reaches the window edge. That last part is COSMETIC and it is
    a construction, not a gate: see :func:`lint_pages` for why no rule re-asserts it.
  * **26-bit signed expression envelope** -- owned by :func:`journal.eb_bounds`, checked by
    ``journal.lint_rows``; this module re-checks the page-local expressions it adds itself.

ONE NUMBER PER ROW, AND THE THREE THINGS THAT USED TO BE HAND-TYPED HERE. A page is a RENDERER of
:data:`journal.ROWS`, never a second catalog, so nothing a page draws may be authored twice:

  * the DENOMINATOR comes from ``RowSpec.denom`` (:func:`_denom_of`) -- there is no per-line override
    field to drift, which is what a hand-typed ``denom=64`` next to a catalog ``denom=64`` invites;
  * the UNIT comes from ``RowSpec.eb_unit`` (journal.EB_SCALE), so the one row whose expression
    publishes hours while its offline reader publishes seconds cannot render the number bare;
  * the EXPRESSION comes from ``RowSpec.eb``. A page-local ``extra`` is the single exception and it
    gets the identical validator (:func:`lint_pages`).

WIDTH, THE CORRECTION THE DESIGN BRIEF DID NOT HAVE. The rung-0 header that wrapped in-game measures
33.1 units under :func:`content.text.measure`, and the one that did not measures 19.45 -- and the kit
auto-wraps EVERY collected ``.mes`` line at ``DEFAULT_WRAP_WIDTH = 28.0`` (content/text.py:500,
build.py:7766-7774). So the "~27 chars" observation is fully explained at BUILD time and the in-game
window was never the binding constraint: engine-side ``Dialog.Width`` has only a MINIMUM clamp
(Dialog.cs:364-375) and the in-parse wrap happens at the SCREEN width. 28.0 units is the real budget
and it is tunable per field via ``[dialogue] wrap``. Every line here is designed <= 26 units so the
layout is correct under either reading; raising the budget is a lever, not a dependency.

Provenance: derived from the open-source Memoria C# and this kit's own emitters. No SE bytes.
"""
from __future__ import annotations

from dataclasses import dataclass, field as _field

from . import journal as _J
from .content import choice as _choice, region as _region, text as _text
from .eb import exprasm as _exprasm, exprsem as _exprsem, opcodes as _opcodes

# ============================ engine ceilings (TRANSCRIBED, with their file:line) ============================
MES_VALUE_SLOTS = 8      # ETb.SetMesValue clamps scriptID 0..7 (ETb.cs:230-234) against
                         # `gMesValue = new Int32[8]` (EventEngine.Initialize.cs:30). GLOBAL, but a modal
                         # window means one page owns them all at a time.
MAX_PAGE_LINES = 13      # ~13 rendered lines at DialogLineHeight 68 between kLimitTop and
                         # DialogLimitBottom (Dialog.cs:292-296, :1139-1146). Windows PAGE, never scroll.
MAX_CHOICE_ROWS = 16     # the kit packs choice availability into a UInt16 (content/choice.py:176-197,
                         # :228-230 -- `or_var(GLOB_UINT16, MASK_SCRATCH_IDX, 1 << i)`).
WRAP_BUDGET = _text.DEFAULT_WRAP_WIDTH        # 28.0 -- the kit's own build-time wrap (content/text.py:500)
LINE_BUDGET = 26.0       # what THIS layout designs to, so it is correct under the tighter reading too
VALUE_COLUMN = 15.0      # measured units at which every value tag starts (labels pad to it with 0.5u spaces)

#: The MAP bit the re-open loop latches on. MAP scope, not GLOB: per-field transient, no save write.
#: ``EventContext.mapvar = new Byte[80]`` (EventContext.cs:9) -> valid bit indices 0..639, and stock's
#: own MAP bools live low (region.STAY_LOCKED_IDX = 156), so the latch sits in the top byte.
LOOP_LATCH_BIT = 632

PAGE_WINDOW = 1          # ordinary field-dialogue window id (0..7; 255 is the no-window sentinel)
PAGE_FLAGS = 128         # the standard field dialogue flag, same as plain NPC dialogue


# ============================ the [TBLE] tables ============================
# `[TEXT=bank,slot]` -> ETb.GetStringFromTable(bank, slot) -> FF9TextTool.GetTableText(bank), where BANK
# is the TXID of an entry in THIS field's own .mes whose body starts with `[TBLE]` and whose rows are
# \n-separated (FF9TextTool.cs:650-659, NGUIText.cs:1536 `TableStart = "TBLE"`).
#
# ⚠ THE BANK IS NOT AUTHORABLE. collect_text assigns txids by POSITION (build.py:7795-7834), so a
# hand-written `[TEXT=600,2]` in a TOML bakes a txid that moves the moment a line is added above it.
# Every renderer here therefore takes the banks as a PARAMETER and substitutes them in a second pass.
TABLES = {
    # rank index 0-8 -> the ladder letters. Identical order to journal.TH_RANKS, asserted in lint_pages.
    "th_rank": _J.TH_RANKS,
    # Festival of the Hunt: byte 313, 1/2/3 = Zidane/Vivi/Freya (journal._HUNT_WINNERS, EMinigame.cs:302).
    # Row 0 is the undecided state, and it is ALSO where minigame.hunt_winner's upward clamp folds every
    # out-of-range byte -- GetStringFromTable's own upper guard returns String.Empty (ETb.cs:278), a BLANK
    # line, which reads as a bug.
    "hunt": ("---", "Zidane", "Vivi", "Freya"),
}


# ============================ the page schema ============================
@dataclass(frozen=True)
class Line:
    """One rendered line of one page. ``row`` is a :data:`journal.ROWS` id -- ALWAYS, including for a
    ``dash``/``na`` line, because the placement audit in :func:`lint_pages` is what makes "nothing is
    silently dropped" a checked property instead of a claim."""
    row: str
    label: str                        # the PAGE label. Often shorter than RowSpec.label: 26 units is
                                      # the whole line, and the header has to stay wider than it.
    kind: str                         # "num" | "table" | "dash" | "na"
    table: "str | None" = None        # kind == "table": which of TABLES
    extra: tuple = ()                 # page-local EXTRA expressions after the row's own (play time's
                                      # minutes remainder is the only one). Each costs another slot and
                                      # is gated exactly like a row expression.
    extra_source: str = ""            # file:line for `extra` (required iff extra is non-empty)
    # ⚠ THERE IS DELIBERATELY NO `denom` AND NO `sep`/unit FIELD. Both used to live here as hand-typed
    # literals beside the catalog's own (`denom=64` against RowSpec.denom 64), and a page CANNOT be a
    # second catalog: a drifted literal would ship "Variants out 37/999" in-game while `journal report`
    # printed 37/64, with nothing offline able to see the disagreement. Both now come from the RowSpec
    # (:func:`_denom_of`, `RowSpec.eb_unit`), so the divergence is unrepresentable rather than checked.


@dataclass(frozen=True)
class Page:
    key: str                          # stable id (the menu row's identity; never renumber)
    title: str                        # header text between the `==` rules
    menu: str                         # the menu row label
    lines: tuple = ()


#: THE LAYOUT. 7 pages, all 48 catalog rows placed exactly once, every line measured.
#:
#: `minigame` is the oversized category (11 rows, 10 numeric -- over the 8-slot ceiling), so it splits
#: along the engine's OWN seam: gEventGlobal minigames (P3) vs the `30000_MiniGame` deck (P4). `combat`
#: is a single row, so it rides with `meta` rather than costing a menu slot for one line.
PAGES = (
    Page("story", "STORY & TREASURE", "Story & treasure", (
        Line("story.scenario", "Scenario", "num"),
        Line("treasure.hunter_points", "T.Hunter pts", "num"),
        Line("treasure.hunter_rank", "T.Hunter rank", "table", table="th_rank"),
        Line("treasure.chest_atlas", "Chests opened", "na"),
    )),
    Page("chocobo", "CHOCOBO", "Chocobo", (
        Line("chocobo.chocographs_found", "Chocographs", "num"),
        Line("chocobo.chocographs_dug", "..dug up", "num"),
        Line("chocobo.beak_level", "Beak level", "num"),
        Line("chocobo.dig_ability", "Dig terrain", "num"),
        Line("chocobo.beaches", "Beaches", "num"),
    )),
    Page("minigame", "MINIGAMES", "Minigames", (
        Line("minigame.stellazzio", "Stellazzio", "num"),
        Line("minigame.ragtime_quiz", "Ragtime", "num"),
        Line("minigame.coin_toss", "Treno coins", "num"),
        Line("minigame.frogs", "Frogs", "num"),
        Line("minigame.hunt_winner", "Hunt winner", "table", table="hunt"),
    )),
    Page("cards", "TETRA MASTER", "Tetra Master", (
        Line("minigame.cards_held", "Cards held", "num"),
        Line("minigame.card_kinds", "Card kinds", "num"),
        Line("minigame.collector_points", "Coll. points", "num"),
        Line("minigame.collector_level", "Coll. level", "num"),
        Line("minigame.card_record", "Wins", "num"),
        Line("minigame.quadmist_opponents", "Opponents", "na"),
    )),
    Page("mognet", "MOGNET", "Mognet", (
        Line("mognet.delivered", "Delivered", "num"),
        Line("mognet.letters_carried", "In hand", "num"),
        Line("mognet.give_locks", "Variants out", "num"),
        Line("mognet.read_locks", "Variants read", "num"),
        Line("mognet.stiltzkin_tally", "Stiltzkin", "num"),
        Line("mognet.central_discovered", "Central", "num"),
        Line("mognet.paradise_discovered", "Paradise", "num"),
        Line("mognet.stiltzkin_purchases", "S. purchases", "na"),
    )),
    Page("party", "PARTY", "Party", (
        Line("party.gil", "Gil", "num"),
        # denominator = journal.KEY_ITEM_EB_COUNT, the SAME constant the .eb's B_HAVE_ITEM sum is
        # built from -- see `_denom_of` rule 3 and the live-install gate in `lint_pages`.
        Line("party.key_items", "Key items", "num"),
        Line("party.abilities_mastered", "Abil. mastered", "dash"),
        Line("party.thefts", "Steals", "dash"),
        Line("party.escapes", "Escapes", "dash"),
        Line("party.battles", "Battles", "dash"),
        Line("party.kills_total", "Kills", "dash"),
        Line("party.kills_by_category", "Kills by type", "dash"),
        Line("party.abilities_ever", "Abil. ever", "na"),
        Line("party.passive_abilities_ever", "Support ever", "na"),
    )),
    Page("meta", "COMBAT & META", "Combat & meta", (
        Line("combat.yan_blessing", "Yan blessing", "num"),
        # THE ONLY TWO-SLOT ROW. slot n = hours (the row's own eb, which journal.EB_SCALE declares as
        # seconds//3600 and renders with its own "h"), slot n+1 = the minutes remainder.
        Line("meta.play_time", "Play time", "num",
             extra=("B_SYSVAR[20] const(60) B_DIV const(60) B_REM",),
             extra_source="EventEngine.GetSysvar.cs:70-73"),
        Line("meta.field_entrance", "Last entrance", "num"),
        # An .eb read EXISTS (`B_SYSVAR[7]`) but the game never moves the counter, so the page renders
        # "n/a" and never 0. `eb` and `status` are orthogonal; collapsing them would show a dead
        # counter as 0% progress.
        Line("meta.step_count", "Steps", "na"),
        Line("meta.ates_seen", "ATEs seen", "na"),
        Line("meta.bestiary", "Bestiary", "na"),
        Line("meta.synthesis_recipes", "Synthesis", "na"),
        Line("meta.friendly_monsters", "Friendly mon.", "na"),
        Line("meta.achievement_keys", "Achievements", "na"),
        Line("meta.index", "Index", "dash"),
    )),
)

#: The menu's own text. "Close" is LAST because with no `[PCHC]`/`[PCHM]` the engine's CANCEL row is the
#: last one (content/choice.py:20-21) -- pressing B must close the journal, not open the last page.
MENU_PROMPT = "Read which page?"
MENU_LEGEND = "-- = offline only"
MENU_CLOSE = "Close"

DASH_TEXT = "--"     # the row exists and a save carries it, but no .eb expression can reach it
NA_TEXT = "n/a"      # the GAME keeps nothing to read (or keeps a counter it never moves)


# ============================ rendering ============================
def _pad_to(label: str, target: float) -> str:
    """Pad ``label`` with spaces (0.5 units each) until its measured width reaches ``target``. The font
    is proportional and per-install (content/text.py:490-498), so a monospace ``ljust`` would not line
    the values up; this lands them within half a space of each other."""
    out = label
    while _text.measure(out) < target:
        out += " "
    return out


def _value_text(line: "Line", banks: dict, slot: int) -> str:
    if line.kind == "num":
        return f"[NUMB={slot}]"
    if line.kind == "table":
        bank = banks.get(line.table)
        if bank is None:
            raise KeyError(f"page line {line.row}: no [TBLE] bank supplied for table {line.table!r}")
        return f"[TEXT={bank},{slot}]"
    return DASH_TEXT if line.kind == "dash" else NA_TEXT


def _denom_of(line: "Line") -> "int | None":
    """The literal denominator to bake after the tag, or None for a bare tag. FOUR RULES, and every
    one of them reads the CATALOG -- a page has no denominator of its own to disagree with:

      1. only a ``num`` line ever bakes one. A ``table`` line renders a NAME ("rank C"), and "/8"
         after a rank letter is nonsense; ``dash``/``na`` have no value at all;
      2. a ``run_mode`` or ``exclusive_group`` row -> bare tag EVEN IF the RowSpec has a ``denom``.
         Same exclusion :func:`journal.build_report` applies to the offline index (journal.py:1080-1084)
         -- a fraction that cannot legitimately fill reads as a bug;
      3. ``party.key_items`` -> :data:`journal.KEY_ITEM_EB_COUNT`, the SAME constant the row's
         ``B_HAVE_ITEM`` sum is generated from. It is the one place THE NAMES LAW is deliberately
         narrowed (a .mes is static and cannot resolve a live table), and taking numerator and
         denominator from one constant is what makes them span the same id window BY CONSTRUCTION.
         :func:`lint_pages` separately checks that constant against the live install;
      4. otherwise ``RowSpec.denom`` verbatim -- no engine maximum -> bare tag (never invent one).
    """
    spec = _J.row_spec(line.row)
    if line.kind != "num" or spec is None:
        return None
    if spec.run_mode or spec.exclusive_group:
        return None
    if line.row == "party.key_items":
        return _J.KEY_ITEM_EB_COUNT
    return spec.denom


def _unit_of(line: "Line") -> str:
    """The unit suffix rendered after the row's own value -- from ``RowSpec.eb_unit``, never authored
    on the page. The one scaled row (play time: seconds offline, hours in-game -- journal.EB_SCALE)
    therefore CANNOT render its number bare next to seven unscaled ones."""
    spec = _J.row_spec(line.row)
    return spec.eb_unit if (line.kind == "num" and spec is not None) else ""


def render_page(page: "Page", banks: dict) -> tuple:
    """``(text, exprs)`` for one page: the ``.mes`` entry body, and the RPN token strings to publish
    into slots 0..len(exprs)-1 IN ORDER, before the window opens."""
    exprs: list = []
    body: list = []
    for line in page.lines:
        if line.kind in ("num", "table"):
            spec = _J.row_spec(line.row)
            slot = len(exprs)
            exprs.append(spec.eb)
            val = _value_text(line, banks, slot) + _unit_of(line)
            for i, ex in enumerate(line.extra):
                exprs.append(ex)
                val += f"[NUMB={slot + 1 + i}]"
            den = _denom_of(line)
            if den is not None:
                val += f"/{den}"
        else:
            val = _value_text(line, banks, 0)
        body.append(_pad_to(line.label, VALUE_COLUMN) + val)
    # THE HEADER RULE, by construction: extend the `=` run until it out-measures every line, so the
    # rule reaches the window edge instead of stopping short of it. This is COSMETIC -- the engine
    # bakes Width from the real rendered strings at open (Dialog.AutomaticSize, Dialog.cs:1560-1591),
    # which is why `page_body` publishes the values FIRST and why `lint_pages` no longer re-asserts
    # the relation as if it were a gate on page data (it cannot fail for any Page input).
    widest = max(_worst_case_width(line, banks) for line in page.lines)
    header = f"== {page.title} "
    while _text.measure(header) <= widest:
        header += "="
    # ⚠ NO `[IMME]` HERE, AND NO `instant` ON THE OPTION -- THE BROADCAST-CONFIRM LAW.
    # DialogManager.OnKeyConfirm (DialogManager.cs:335-341) fans a confirm press out to EVERY active
    # window with no filter, and each Dialog.OnKeyConfirm closes itself if it has finished typing and
    # !ignoreInputFlag (Dialog.cs:789). `[IMME]` finishes the typing INSTANTLY, so an instant page
    # opened by a choice is already "finished" when the very press that SELECTED it fans out -- it
    # dismisses itself on arrival and the dispatch then falls off the end of the tree.
    # Owner playtest 30801 round 3: "it opens, and when it's finished with the opening animation and
    # the text shows, it immediately does the closing animation and exits the entire dialogue tree."
    # A typewriter page survives, because a press mid-type SKIPS to full text instead of closing.
    # The law's other remedies ([TIME=-1] / [NFOC], which set ignoreInputFlag) are wrong here: the
    # player must still be able to dismiss the page with a SECOND press.
    # → studies/messages/SURVEY.md §7a.
    return header + "\n" + "\n".join(body), tuple(exprs)


def _worst_case_width(line: "Line", banks: dict) -> float:
    """A line's width with every tag replaced by the WIDEST thing it can ever render. ``[NUMB]``'s
    modelled tag width is 4.0 units (content/text.py:527-529), which is only ~4 digits -- gil renders
    7 -- so the LINE_BUDGET rule has to be computed against real values, not against the tag."""
    spec = _J.row_spec(line.row)
    if line.kind == "num":
        _lo, hi = _J.eb_bounds(spec.eb)
        val = str(hi) + _unit_of(line)
        for ex in line.extra:
            _l2, h2 = _J.eb_bounds(ex)
            val += str(h2)
        den = _denom_of(line)
        if den is not None:
            val += f"/{den}"
    elif line.kind == "table":
        val = max(TABLES[line.table], key=_text.measure)
    else:
        val = DASH_TEXT if line.kind == "dash" else NA_TEXT
    return _text.measure(_pad_to(line.label, VALUE_COLUMN) + val)


def menu_text(pages=PAGES) -> str:
    """The ONE ``[CHOO]`` entry -- prompt, legend, then one row per page plus Close. The Black Mage
    shop shape (content/choice.py:7-13): prompt and rows are a single text entry."""
    rows = "\n".join(f"  {p.menu}" for p in pages) + f"\n  {MENU_CLOSE}"
    return f"[IMME]{MENU_PROMPT}\n{MENU_LEGEND}\n[CHOO]{rows}"


def page_texts(banks: dict, *, pages=PAGES) -> dict:
    """``{page.key: (text, exprs)}`` for every page."""
    return {p.key: render_page(p, banks) for p in pages}


def table_texts() -> dict:
    """``{name: entry_body}`` for the two ``[TBLE]`` banks -- the entries whose txids become the
    ``bank`` operand of every ``[TEXT=bank,slot]`` this dashboard emits."""
    return {name: "[TBLE]" + "\n".join(rows) for name, rows in TABLES.items()}


# ============================ the .eb side ============================
def page_body(exprs, page_txid: int, *, window: int = PAGE_WINDOW, flags: int = PAGE_FLAGS,
              table_slots=()) -> bytes:
    """ONE page arm: publish every value, THEN open the modal window.

    Order is load-bearing. Values are written BEFORE the window opens, so ``Dialog.AutomaticSize``
    (Dialog.cs:1560-1591) bakes the width over the REAL numbers -- and since it never re-sizes on a
    later value change, that is the only moment at which the width can be right.

    ``table_slots`` names the slots a ``[TEXT=]`` tag reads. Those get the non-negative clamp WRAPPED
    around them by this emitter, not by the author: ``ETb.GetStringFromTable`` (ETb.cs:270-284) bounds
    the slot and the upper row but has NO lower bound, and a negative indexes ``tableText[-n]`` and
    throws. The clamp spelling is imported from :func:`content.behavior.hud_row_index_clamp` rather
    than re-spelled here, so the "an unclamped publish is UNREPRESENTABLE" property transfers instead
    of being re-litigated (a three-token tail-match once certified a single-``E`` form as safe, which
    both defeats the clamp AND underflows the CalcStack)."""
    from .content.behavior import hud_row_index_clamp
    out = []
    for slot, ex in enumerate(exprs):
        toks = hud_row_index_clamp(ex) if slot in set(table_slots) else ex
        out.append(_opcodes.set_text_variable_expr(slot, _exprasm.assemble(toks + " B_EXPR_END")))
    out.append(_opcodes.window_sync(window, flags, page_txid))
    return b"".join(out)


def table_slots_of(page: "Page") -> tuple:
    """Which slots of ``page`` feed a ``[TEXT=]`` tag (so :func:`page_body` clamps them)."""
    out, slot = [], 0
    for line in page.lines:
        if line.kind not in ("num", "table"):
            continue
        if line.kind == "table":
            out.append(slot)
        slot += 1 + len(line.extra)
    return tuple(out)


def talk_body(page_txids: dict, menu_txid: int, banks: dict, *,
              pages=PAGES, latch_bit: int = LOOP_LATCH_BIT, window: int = PAGE_WINDOW,
              flags: int = PAGE_FLAGS) -> bytes:
    """The COMPLETE talk handler: lock control, then loop { menu -> one page } until Close, unlock,
    return.

    ``choice.switch_on_choice``, NEVER ``choice.branch``. Every arm opens a window and a window
    overwrites sysvar 9, so ``branch``'s per-arm re-read of ``GetChoose()`` would test the PAGE
    window's answer and fire the wrong arms from the second row on (content/choice.py:283-300).
    ⚠ build.py:6097 selects switch dispatch only when a row carries ``input``/``qte``, so a journal
    wired through the plain ``[[choice]]`` lane would silently get ``speak_body``. This generator
    calls ``switch_on_choice`` itself.

    THE LOOP, and why the latch is a MAP BIT. A dashboard you must re-talk for each page is bad, and
    the loop CANNOT test sysvar 9 after the page window (same clobber law). So: set ``Map.Bit[n]``
    before the menu, the Close arm clears it, and ``region.while_block`` re-runs while it holds. MAP
    scope means per-field transient with no save write (``EventContext.mapvar = new Byte[80]``,
    EventContext.cs:9, so ``n`` must be < 640). ``while_block`` is the kit's existing backward-jump
    construct -- the only genuinely new thing here is which condition it tests."""
    texts = page_texts(banks, pages=pages)
    arms = []
    for p in pages:
        _txt, exprs = texts[p.key]
        arms.append(page_body(exprs, int(page_txids[p.key]), window=window, flags=flags,
                              table_slots=table_slots_of(p)))
    # the Close row: clear the latch so while_block falls out. It is LAST -- the engine's cancel row.
    arms.append(_region.set_var(_region.MAP_BOOL, latch_bit, 0))
    loop = (_opcodes.window_sync(window, flags, int(menu_txid))
            + _choice.switch_on_choice(arms))
    return (_opcodes.DISABLE_MOVE
            + _region.set_var(_region.MAP_BOOL, latch_bit, 1)
            + _region.while_block(_region.cond_truthy(_region.MAP_BOOL, latch_bit), loop)
            + _opcodes.ENABLE_MOVE + _opcodes.RETURN)


# ============================ the gate ============================
def live_key_item_count() -> "int | None":
    """The install's key-item table size, or None when the install is unreachable (keyitems.py:30-48)."""
    try:
        from . import keyitems as _keyitems
        n = len(_keyitems.all_keyitems())
        return n or None
    except Exception:                                     # noqa: BLE001 -- an unreachable install is not an error
        return None


@dataclass
class PageReport:
    """What :func:`measure_pages` computes -- the numbers :func:`lint_pages` judges and the CLI prints."""
    key: str
    title: str
    lines: int
    slots: int
    eb_bytes: int
    header_width: float
    widest_value_line: float
    rows: list = _field(default_factory=list)             # [(row_id, kind, literal_w, worst_w)]


def measure_pages(*, banks: "dict | None" = None, pages=PAGES) -> list:
    """Per-page line counts, slot counts, emitted ``.eb`` bytes and measured widths."""
    banks = banks if banks is not None else {n: 600 + i for i, n in enumerate(TABLES)}
    out = []
    for p in pages:
        text, exprs = render_page(p, banks)
        body = page_body(exprs, 700, table_slots=table_slots_of(p))
        rendered = text.split("\n")
        rows = []
        for line, lit in zip(p.lines, rendered[1:]):
            rows.append((line.row, line.kind, _text.measure(lit), _worst_case_width(line, banks)))
        out.append(PageReport(p.key, p.title, len(rendered), len(exprs), len(body),
                              _text.measure(rendered[0]),
                              max(w for _r, _k, _l, w in rows) if rows else 0.0, rows))
    return out


def lint_pages(*, pages=PAGES, check_live_install: bool = True) -> list:
    """Validate the LAYOUT against every ceiling -- returns violation strings (empty == green).

    This is the half of the deliverable that turns the design's width/slot claims into enforced
    properties. A width claim that is not checked at the call site is a wish.

    ⚠ TWO CLAIMS THAT USED TO BE "RULES" HERE ARE NOT RULES, and saying so is the point.

    *The header/widest relation.* :func:`render_page` grows the ``=`` rule until it out-measures every
    line, so no Page input can violate it -- a rule re-asserting it could never fire, and a gate that
    cannot fail is not a gate (``feedback-a-check-that-cannot-fail``). It was measured: brute-forcing
    120 label widths through render_page/measure_pages never fired it, and widening a real page label
    kept the lint green while the header silently grew. It is a construction, and
    ``tests/test_journalfield.py`` tests it AS a construction (delete the ``while`` and that test goes
    red) rather than pretending it covers page data. The rule that DOES the work is the wrap rule
    below it: a value line wide enough to push the grown header past 28.0 makes the HEADER wrap, and
    that one fails on real page data. It is what bounds :data:`LINE_BUDGET`.

    *The denominator/unit agreement.* Both now come from the RowSpec (:func:`_denom_of`,
    :func:`_unit_of`), so a page cannot render a fraction or a unit the catalog disagrees with. No
    rule below re-checks it because there is no longer a second place for it to be written.

    ``check_live_install`` is the ONE thing here that reaches outside the process, and it is
    fail-loud in BOTH directions: an install whose key-item table disagrees with
    ``journal.KEY_ITEM_EB_COUNT`` is a violation, and so is an install this machine cannot read at
    all -- that is exactly the machine on which the one build-time bake is least verifiable, so it
    must not be the machine where the check silently passes. Pass ``False`` to state deliberately
    that this run is offline-only (every test in the suite does; ``journal lint --offline`` does)."""
    banks = {n: 600 + i for i, n in enumerate(TABLES)}
    bad: list = []

    # --- placement: every catalog row on EXACTLY one page, no invented rows -----------------------
    placed: dict = {}
    for p in pages:
        for line in p.lines:
            if _J.row_spec(line.row) is None:
                bad.append(f"page {p.key}: line {line.row!r} is not a journal row id")
            placed.setdefault(line.row, []).append(p.key)
    for rid, where in sorted(placed.items()):
        if len(where) > 1:
            bad.append(f"{rid}: placed on {len(where)} pages ({', '.join(where)}) -- exactly one")
    for spec in _J.ROWS:
        if spec.id not in placed:
            bad.append(f"{spec.id}: on NO page. Nothing is silently dropped -- give it a number, a "
                       f"'--' or an 'n/a' line")

    # --- the row/line agreement: a page may not render a number a row refuses --------------------
    for p in pages:
        for line in p.lines:
            spec = _J.row_spec(line.row)
            if spec is None:
                continue
            if line.kind in ("num", "table"):
                if spec.eb is None:
                    bad.append(f"page {p.key}: {line.row} renders a value but declares eb_absent")
                if spec.status in ("untracked", "dead"):
                    bad.append(f"page {p.key}: {line.row} is status={spec.status!r} -- it must render "
                               f"'{NA_TEXT}', never a number")
            elif spec.eb is not None and spec.status not in ("untracked", "dead"):
                bad.append(f"page {p.key}: {line.row} has a working eb expression but renders "
                           f"{line.kind!r}")
            if line.kind == "table" and line.table not in TABLES:
                bad.append(f"page {p.key}: {line.row} names unknown table {line.table!r}")
            if bool(line.extra) != bool(line.extra_source):
                bad.append(f"page {p.key}: {line.row} extra/extra_source must be set together")
            for ex in line.extra:
                # A page-local expression gets EXACTLY the gate a row expression gets. Same validator,
                # one owner -- otherwise the second slot of play time would be the unchecked one.
                try:
                    a = _exprsem.analyze(ex + " B_EXPR_END")
                    _exprasm.assemble(ex + " B_EXPR_END")
                except Exception as e:                    # noqa: BLE001
                    bad.append(f"page {p.key}: {line.row} extra {ex!r} does not evaluate: {e}")
                    continue
                if a.unsafe_to_repeat:
                    bad.append(f"page {p.key}: {line.row} extra carries "
                               f"{sorted({s.token for s in a.unsafe_to_repeat})} -- a journal row READS")
                try:
                    lo, hi = _J.eb_bounds(ex)
                except _J.EbBoundsError as e:
                    bad.append(f"page {p.key}: {line.row} extra is not bounded: {e}")
                else:
                    if not (_opcodes.EXPR_VALUE_MIN <= lo and hi <= _opcodes.EXPR_VALUE_MAX):
                        bad.append(f"page {p.key}: {line.row} extra can produce {lo}..{hi}, outside "
                                   f"the 26-bit envelope")

    # --- the ceilings ----------------------------------------------------------------------------
    # Only reachable once the page is structurally sound: a line that renders a number for a row with
    # no expression cannot be MEASURED (there is no value to take a worst case of), and its structural
    # message above is the actionable one. Reporting a measurement crash on top would bury it.
    if bad:
        return bad
    for rep in measure_pages(banks=banks, pages=pages):
        if rep.slots > MES_VALUE_SLOTS:
            bad.append(f"page {rep.key}: {rep.slots} value slots > the engine's {MES_VALUE_SLOTS} "
                       f"(ETb.SetMesValue clamps scriptID 0..7 against Int32[8])")
        if rep.lines > MAX_PAGE_LINES:
            bad.append(f"page {rep.key}: {rep.lines} rendered lines > the ~{MAX_PAGE_LINES}-line "
                       f"window (Dialog.cs:292-296) -- windows PAGE, they never scroll")
        for rid, _kind, lit_w, worst_w in rep.rows:
            if max(lit_w, worst_w) > LINE_BUDGET:
                bad.append(f"page {rep.key}: {rid} renders {max(lit_w, worst_w):.2f} units > the "
                           f"{LINE_BUDGET} budget (the kit wraps at {WRAP_BUDGET})")
        if rep.header_width > WRAP_BUDGET:
            bad.append(f"page {rep.key}: header renders {rep.header_width:.2f} units > the "
                       f"{WRAP_BUDGET} wrap -- the build would re-flow it onto two lines "
                       f"(content/text.py:500, build.py:7766-7774)")
        # NO header-vs-widest rule here, deliberately -- see the docstring. render_page constructs the
        # header to satisfy it, so the rule could not fail for any Page input.

    # --- the menu --------------------------------------------------------------------------------
    n_rows = len(pages) + 1
    if n_rows > MAX_CHOICE_ROWS:
        bad.append(f"menu: {n_rows} rows > the ~{MAX_CHOICE_ROWS} the UInt16 availability mask allows")
    for ln in menu_text(pages).split("\n"):
        if _text.measure(ln) > WRAP_BUDGET:
            bad.append(f"menu line {ln!r} renders {_text.measure(ln):.2f} units > the {WRAP_BUDGET} wrap")

    # --- the tables ------------------------------------------------------------------------------
    if TABLES["th_rank"] != _J.TH_RANKS:
        bad.append("TABLES['th_rank'] has drifted from journal.TH_RANKS -- the row index and the "
                   "letters must come from ONE ladder")
    if len(TABLES["hunt"]) != 4 or TABLES["hunt"][2] != "Vivi":
        bad.append("TABLES['hunt'] must be (undecided, Zidane, Vivi, Freya) -- EMinigame.cs:302 tests "
                   "byte 313 == 2 for Vivi")

    # --- the ONE build-time bake ------------------------------------------------------------------
    # The numerator/denominator agreement is NOT checked here: `_denom_of` rule 3 and the row's
    # `_have_item_sum` are generated from the one constant, so they cannot span different windows.
    # What CANNOT be made structural is whether that constant still describes the INSTALL -- a .mes
    # is static, so /80 is decided at build time and a Moguri-style table swap between generate and
    # play is invisible in-game. Hence a real read of the real install, and hence the None branch
    # being a VIOLATION: "I could not look" and "I looked and it agrees" must never be the same
    # result, least of all on the machine where nobody can look.
    if check_live_install:
        live = live_key_item_count()
        if live is None:
            bad.append(f"party.key_items: this machine cannot read the install's key-item table "
                       f"(keyitems.all_keyitems), so the ONE build-time bake -- /"
                       f"{_J.KEY_ITEM_EB_COUNT}, journal.KEY_ITEM_EB_COUNT -- is UNVERIFIED here. "
                       f"Re-run this gate on the deploy machine before shipping the .mes, or pass "
                       f"check_live_install=False (`journal lint --offline`) to say deliberately "
                       f"that this run checks the layout only")
        elif live != _J.KEY_ITEM_EB_COUNT:
            bad.append(f"party.key_items: the page bakes /{_J.KEY_ITEM_EB_COUNT} and the .eb sums "
                       f"{_J.KEY_ITEM_EB_COUNT} B_HAVE_ITEM terms, but this install's key-item table "
                       f"has {live} entries (keyitems.all_keyitems). A .mes is STATIC so the "
                       f"denominator cannot resolve at runtime -- re-bake journal.KEY_ITEM_EB_COUNT "
                       f"against this install and record it in the build doc")
    return bad


# ============================ the bench field ============================
# ⚠ READ THIS BEFORE READING THE GENERATED TOML.
#
# THE BENCH IS LIVE. It rides the ordinary `[[choice]]` lane end to end: each menu row is one option,
# the page text is that option's `reply`, and the option's `values` list publishes the SAME catalog
# expressions this module's :func:`page_body` emits, into gMesValue 0..N-1, immediately before the
# reply window opens (`content/choice.py:option_values_body`).
#
# IT SHIPPED ONCE AS A MOCKUP, AND THAT IS THE DEFECT THIS LANE CLOSES. The first cut had no value
# writes at all -- `[[logic_add]]` is refused without `[verbatim_eb]` (build.py:930-934) and
# `[behavior]` is refused ON a verbatim fork, so neither existing lane could attach a raw talk-handler
# body, and the bench went out with the tags reading whatever gMesValue already held. gMesValue is
# `Int32[8]` allocated once at engine init (EventEngine.Initialize.cs:30) and never cleared on a field
# load, so all seven pages rendered the PREVIOUS bench's slot vector -- plausible numbers, in the right
# columns, entirely stale ("Mognet: In hand 22/3"). An unwritten slot does not render blank.
#
# WHAT IS STILL DELIBERATELY UNLIKE THE SHIPPED DASHBOARD, and why that is not the same defect:
#   * the two `[TEXT=bank,slot]` rows render their WIDEST table string instead of the tag, because the
#     bank is a txid `collect_text` assigns by POSITION (build.py:7795-7834) and is not authorable in a
#     TOML at all. Their slot is still PUBLISHED (so every slot index below it matches the shipped
#     page exactly); nothing in the bench reads it, so nothing clamps it -- the clamp is emitted for
#     the slots an option's own reply actually indexes.
#   * the menu is a flat `[[choice]]`, not :func:`talk_body`'s re-open loop: one page per talk.
#
# The text AND the expressions are GENERATED, never hand-copied, so the bench cannot drift from the
# catalog; a test asserts the checked-in file equals this function's output byte for byte, and a second
# test asserts the BUILT `.eb` carries the value writes (a generator-only test cannot see an unwired
# field -- that is exactly how the mockup passed).
BENCH_FIELD_ID = 30801     # dev scratch. NOT 30800 -- that is the recorded rung-0/0b probe.
BENCH_PROMPT = "Which page? (BENCH 30801 --\nthe numbers are LIVE)"


def _bench_page_text(page: "Page") -> str:
    """A page rendered for the LAYOUT bench: identical to the shipped text except that a
    ``[TEXT=bank,slot]`` tag becomes its WIDEST literal row.

    Why substitute: the bank is a txid the build assigns by POSITION (build.py:7795-7834), so it is
    not authorable in a TOML at all. Using the widest row keeps the width measurement HONEST (it is
    the worst case the real tag can render) while making the bench self-contained."""
    banks = {n: 0 for n in TABLES}
    text, _exprs = render_page(page, banks)
    out = []
    tbl_lines = [ln for ln in page.lines if ln.kind == "table"]
    for row in text.split("\n"):
        if "[TEXT=" in row and tbl_lines:
            widest = max(TABLES[tbl_lines.pop(0).table], key=_text.measure)
            row = row[:row.index("[TEXT=")] + widest
        out.append(row)
    return "\n".join(out)


def bench_page_values(page: "Page") -> tuple:
    """The ``values`` list for one bench page: the page's own expressions in slot order, each carrying
    the ``expr:`` prefix ``content/choice.py``'s option lane accepts.

    Taken from :func:`render_page` -- the SAME tuple :func:`page_body` emits -- so the bench cannot
    publish a number the shipped dashboard would not. The banks are irrelevant here (they only affect
    the TEXT), which is why any dict does."""
    _text_unused, exprs = render_page(page, {n: 0 for n in TABLES})
    return tuple(f"expr:{e}" for e in exprs)


def bench_toml(*, pages=PAGES) -> str:
    """The T1b bench as a complete, lint-clean ``field.toml`` (id 30801). DO NOT DEPLOY from
    here -- the human deploys.

    HERMETIC BY CONSTRUCTION: every number in the emitted text comes from the catalog, nothing from
    the install. It used to take the key-item denominator from :func:`live_key_item_count`, so on a
    machine without the game this function emitted a DIFFERENT file (``Key items [NUMB=1]`` instead of
    ``Key items [NUMB=1]/80``) -- a silently install-dependent artifact, in the one file whose whole
    job is to be byte-identical to what the tests and the playtester see."""
    L = [
        "# " + "=" * 85,
        f"# COMPLETION-JOURNAL T1b -- LIVE DASHBOARD BENCH  --  field {BENCH_FIELD_ID}",
        "# " + "=" * 85,
        "# GENERATED by `ff9mapkit.journalfield.bench_toml()` from the ONE row catalog",
        "# (ff9mapkit/ff9mapkit/journal.py). DO NOT HAND-EDIT: tests/test_journalfield.py asserts this",
        "# file equals the generator's output byte for byte, so a hand edit fails the suite.",
        "#",
        "# WHAT THIS BENCH IS.",
        "#   The seven real dashboard pages, verbatim, at their real widths and line counts, in a real",
        "#   modal field window -- and THE NUMBERS ARE LIVE. Each option's `values` list publishes that",
        "#   page's catalog expressions into gMesValue 0..N-1 immediately before its reply window opens",
        "#   (content/choice.py:option_values_body -> eb/opcodes.py:set_text_variable_expr, the same",
        "#   0x66 encoding the behavior HUD and the Treno bid stepper already ship in-game).",
        "#",
        "# THE DEFECT THIS FILE ONCE CARRIED, kept written down because it is invisible in-game.",
        "#   The first cut of this bench had NO value writes -- `grep -c 'expr:'` returned 0 -- and it",
        "#   did not render blanks or zeros: ETb.gMesValue is Int32[8] allocated once at engine init",
        "#   (EventEngine.Initialize.cs:30) and is NEVER cleared on a field load, so all seven pages",
        "#   rendered the PREVIOUS bench's leftover slot vector. Plausible numbers, right columns,",
        "#   entirely stale. A generator-only test could not see it; the test that catches it now builds",
        "#   this file and reads the emitted .eb.",
        "#",
        "# The two [TEXT=bank,slot] rows show their WIDEST table string instead of the tag: the bank is",
        "# a txid the build assigns by POSITION (build.py:7795-7834) and is not authorable. Their slot",
        "# is still published, so every later slot index matches the shipped page exactly.",
        "#",
        "# The value reads are owner-confirmed in-game (rung 0, bench 30800): Null.SBit[5],",
        "# Global.UInt16/Byte/Bit, const(n) B_HAVE_ITEM, flex(), and composed B_DIV/B_GE/B_MULT.",
        "#",
        "# DEPLOY (the HUMAN does this -- the agent does not):",
        f"#   py tools/deploy_field.py studies/completion-journal/bench/journal_dash.field.toml --id {BENCH_FIELD_ID}",
        f"# FIRST deploy of {BENCH_FIELD_ID} needs a RELAUNCH (it registers a DictionaryPatch line); after",
        "# that, `~` -> Reload field. Re-read the live registrations first -- EventDB/SceneData are",
        "# GLOBAL across stacked mod folders and a collision is the null-.eb black screen.",
        "",
        "[field]",
        f"id = {BENCH_FIELD_ID}          # dev-scratch band (30000-32767; fldMapNo is Int16, max 32767)",
        'name = "JOURNALDASH"',
        "area = 11               # must be >= 10 (BG area 0-9 black-screens)",
        'title = "JOURNAL DASH"',
        "# text_block deliberately UNSET: the kit derives it from the field id and auto-registers it.",
        "# Pinning a real block would overwrite that location's dialogue -- the mesID namespace is ONE",
        "# FLAT GLOBAL space shared with the base game.",
        "",
        "# --- scene: the same flat bench room the rung-0 probe used ---------------------------------",
        "[camera]",
        "pitch = 48.0",
        "distance = 4500",
        "fov = 42.2",
        "[camera.frame]",
        "back = 205",
        "front = 432",
        "",
        "[walkmesh]",
        "quad = [[-1220, 257], [1220, 257], [1220, -1931], [-1220, -1931]]",
        'frame = "world"',
        "",
        "[[layers]]",
        'image = "art/back.png"   # PLACEHOLDER (solid slate) -- a bench needs no real art',
        "z = 4000",
        "[[layers]]",
        'image = "art/floor.png"  # PLACEHOLDER (perspective checkerboard)',
        "z = 3000",
        "",
        "[player]",
        "spawn = [0, -837]",
        "",
        "# --- the lectern-tender: talk -> menu -> one page ------------------------------------------",
        "# An NPC, not a walk-in zone: a `once=false` tread re-fires while the player stands in it",
        "# (feedback-bench-visible-landmarks). 400u from the spawn -- actors jam under ~192u.",
        "[[npc]]",
        'name = "keeper"',
        'model = "GEO_NPC_F0_CSO"',
        "pos = [400, -837]",
        "",
        "# --- the dummy behavior unit ---------------------------------------------------------------",
        "# content/behaviortoml.py table() is `return b if isinstance(b, dict) and b.get(\"unit\") else",
        "# None` (:147-150), so a [behavior] block carrying only a hud compiles to NOTHING, SILENTLY,",
        "# and validate() still returns []. The unit row below is what makes the block compile at all.",
        "# NOTE FOR THE NEXT RUNG: the dashboard itself needs NO [behavior] block -- it rides the",
        "# [[choice]] lane -- which is one fewer way to fail. The block is here because this bench is",
        "# also where that trap is kept live and visible.",
        "[[npc]]",
        'name = "scribe"',
        'model = "GEO_NPC_F0_CSO"',
        "pos = [-400, -837]",
        "",
        "[behavior]",
        "warmup = 30",
        "",
        "  [[behavior.unit]]",
        '  npc = "scribe"',
        "    [[behavior.unit.branch]]",
        "    do = { hold = [-400, -837] }   # stand still; the unit row is a compile gate",
        "",
        "# --- THE MENU + THE SEVEN PAGES ------------------------------------------------------------",
        "# `Close` is LAST: with no [PCHC]/[PCHM] the engine's CANCEL row is the last one",
        "# (content/choice.py:20-21), so pressing B must close the journal, not open the last page.",
        "[[choice]]",
        'npc = "keeper"',
        # THE SELECTOR IS INSTANT and that is correct -- an instant open is the normal shape for a
        # choice menu (owner), and studies/messages/bench/winstyle.field.toml:127 ships it on a
        # playtested [[choice]]. A selector is dismissed by a SELECTION, not by the broadcast
        # confirm, so [IMME] is safe here; it is the per-OPTION reply that must not be instant.
        "instant = true          # [IMME] -- the selector pops fully drawn",
        # the closing delimiter rides the LAST content line: a newline before it would ship a
        # trailing blank line into the .mes, costing a rendered line against the ~13-line ceiling.
        'prompt = """',
        BENCH_PROMPT + '"""',
        "",
    ]
    for p in pages:
        vals = bench_page_values(p)
        L += ["  [[choice.options]]",
              f'  text = "{p.menu}"',
              '  reply = """',
              _bench_page_text(p) + '"""',
              # NO `instant` -- THE BROADCAST-CONFIRM LAW kills an instant page (see render_page).
              # ⚠ A DIFFERENT WINDOW ID FROM THE SELECTOR. The choice block's own window is id 1,
              # and a reply defaults to id 1 too (content/choice.py:249, `opt.get("window", 1)`) --
              # so the page re-opened the SAME Dialog the selector was mid-CLOSE on. Reusing an id
              # across a close is the shape that renders a page and then plays the previous
              # window's close animation over it, which is exactly the reported symptom. Depth is
              # 68 - 2*id (Dialog.cs:1949-1959), so id 2 sits behind id 1 -- harmless, the selector
              # is gone by then.
              "  window = 2",
              # slot i is values[i] -- the [NUMB=i] indices in the reply above are render_page's own,
              # so the two orders are the same order by construction. Long lines are the catalog's
              # summed expressions (100 B_HAVE_ITEM terms for the card count), not formatting.
              "  values = ["]
        L += [f'    "{v}",' for v in vals]
        L += ["  ]", ""]
    L += ["  [[choice.options]]",
          f'  text = "{MENU_CLOSE}"',
          ""]
    return "\n".join(L)


def pretty_listing(body: bytes) -> list:
    """Disassemble ``body`` with expression operands rendered in NAMED form -- the reviewable listing.

    ``disasm.read_code`` calls the module-global ``read_expr``, which renders raw ``opXX(..)`` bytes;
    ``disasm.pretty_expr`` has the identical signature and byte-walk but names the operators and
    decodes ``Source.Type[index]`` (eb/disasm.py:173-238). Binding the pretty one for the duration of
    the walk is a read-only dev-tooling swap: it changes no emitted byte, and it is restored in a
    ``finally``. The alternative -- a second copy of ``read_code``'s operand loop here -- is exactly
    the kind of duplicated decoder that drifts."""
    from .eb import disasm as D
    orig = D.read_expr
    D.read_expr = D.pretty_expr
    try:
        return [str(ins) for ins in D.iter_code(body, 0, len(body))]
    finally:
        D.read_expr = orig


def eb_budget(*, pages=PAGES) -> tuple:
    """``(bytes, EB_FILE_BUDGET)`` for the whole dashboard body -- the real emitted stream, measured,
    never ``len()`` of something else. The .eb offset budget is 0xFFFF (binutils.EB_FILE_BUDGET)."""
    from .binutils import EB_FILE_BUDGET
    banks = {n: 600 + i for i, n in enumerate(TABLES)}
    txids = {p.key: 700 + i for i, p in enumerate(pages)}
    body = talk_body(txids, 699, banks, pages=pages)
    return len(body), EB_FILE_BUDGET
