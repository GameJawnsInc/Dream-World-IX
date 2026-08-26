"""The IN-GAME completion dashboard (:mod:`ff9mapkit.journalfield`) -- T1b.

Nothing here needs game data, extracted templates or the install: the layout is measured with the
kit's own proportional text model and the ``.eb`` is assembled + disassembled in memory. So this
module runs fully in a fresh worktree (``project-ff9-test-suite-perf``'s WORKTREE SKIP TRAP).
⚠ That claim is now TRUE rather than aspirational: the green-path test used to leave
``check_live_install`` at its default and therefore went red on any install whose key-item table was
not exactly 80 (a Moguri swap). Every test here passes ``check_live_install=False``; the live read
has its own test, with all three of its branches stubbed.

THE POINT OF THIS FILE. The design's ceilings -- 8 value slots, ~13 lines, the 28.0-unit wrap, every
catalog row placed exactly once -- were arithmetic in a document. Here they are checked at the call
site, and every ceiling test has a NEGATIVE twin that builds a page violating it and asserts the lint
FAILS. A gate that cannot fail is not a gate (``feedback-a-check-that-cannot-fail``), which is also
why two former "rules" are no longer tested as gates: the header/widest relation is a CONSTRUCTION of
``render_page`` (tested as one), and the page-vs-catalog denominator and unit agreements are
arithmetic now that ``Line`` carries neither -- a test proves the property, nothing pretends to
police a second catalog that no longer exists.
"""
from __future__ import annotations

import io
import os
import re

import pytest

from ff9mapkit import journal as J
from ff9mapkit import journalfield as JF
from ff9mapkit.content import region as R, text as T
from ff9mapkit.eb import disasm as D, exprasm as EA, exprsem as ES, opcodes as OPC
from ff9mapkit.eb.opcodes import EXPR_VALUE_MAX, EXPR_VALUE_MIN

# ⚠ THERE IS NO `BANKS` FIXTURE ANY MORE, and its absence is the fix. `render_page` used to take
# {table name: txid} and every caller invented one -- the CLI, the lint, the budget probe and these
# tests each spelled their own, and the BENCH could not spell a real one at all, which is how the
# widest-literal placeholder ("T.Hunter rank  H", frozen) shipped and reached a playtest. A bank now
# has exactly one spelling: the [[text_table]] NAME, resolved to a txid by the build.


# ---- the shipped layout ------------------------------------------------------------------------
def test_the_shipped_layout_is_green():
    """`check_live_install=False` is NOT a convenience here, it is the whole point of this file: the
    live read is the ONE thing in lint_pages that touches the game install, and this module claims
    (docstring) to run in a fresh worktree with no install at all. The green path used to leave it on
    and therefore went RED on any machine whose key-item table was not exactly 80 -- a Moguri swap,
    which the owner stacks. The live read has its own test below, with all three branches stubbed."""
    assert JF.lint_pages(check_live_install=False) == []


def test_the_live_install_read_is_LOUD_in_BOTH_directions(monkeypatch):
    """The one build-time bake, and the ONLY thing in this module that reads the install.

    The failure this replaces: with the install unreachable, `live_key_item_count()` returned None,
    the rule read `if live is not None and ...`, and the gate reported ZERO violations -- on exactly
    the machine where the bake is least verifiable. "I could not look" and "I looked and it agrees"
    must not be the same result."""
    monkeypatch.setattr(JF, "live_key_item_count", lambda: None)          # unreachable install
    assert any("UNVERIFIED here" in m for m in JF.lint_pages()), "an unreadable install went silent"
    monkeypatch.setattr(JF, "live_key_item_count", lambda: J.KEY_ITEM_EB_COUNT + 1)   # Moguri swap
    assert any("key-item table has 81 entries" in m for m in JF.lint_pages())
    monkeypatch.setattr(JF, "live_key_item_count", lambda: J.KEY_ITEM_EB_COUNT)
    assert JF.lint_pages() == []                                          # ...agreement is green


def test_NOTHING_ELSE_depends_on_the_install(monkeypatch):
    """`bench_toml` used to take the key-item denominator from the live table, so a machine without
    the game emitted a DIFFERENT file -- `Key items  [NUMB=1]` where the checked-in one has
    `Key items  [NUMB=1]/80` -- and `lint_pages` reported 0 violations on it. The denominator now
    comes from the same constant the .eb sum is generated from, so the artifact is identical on every
    machine and the numerator/denominator window agreement is not a rule at all, it is arithmetic."""
    outs = []
    for live in (None, 81, J.KEY_ITEM_EB_COUNT):
        monkeypatch.setattr(JF, "live_key_item_count", lambda live=live: live)
        outs.append(JF.bench_toml())
        assert JF.lint_pages(check_live_install=False) == []
    assert outs[0] == outs[1] == outs[2]
    # `Key items` is now the LAST line of the Party page, so the closing """ rides it (a newline
    # before the delimiter would ship a trailing blank line and cost a rendered window row).
    kline = next(ln for ln in outs[0].split("\n") if ln.startswith("Key items")).rstrip('"')
    assert kline.endswith(f"[NUMB=1]/{J.KEY_ITEM_EB_COUNT}"), kline


def test_every_catalog_row_is_placed_exactly_once_OR_is_declared_unrenderable():
    """THE PLACEMENT AUDIT, both arms, over the whole catalog -- no third state.

    It used to read "the 48 rows and the 48 lines are the same set", which was only expressible while
    a page carried a line for rows that can never hold a value and rendered '--' or 'n/a' there. The
    owner's verdict on bench 30801 killed that ("party is full of blank values, as is combat"), so a
    page now renders values only -- and the audit gained an arm rather than losing one: a renderable
    row must be placed, an unrenderable row must NOT be. Every row is still accounted for on every
    run, which is the property the single-arm rule bought."""
    placed = [ln.row for p in JF.PAGES for ln in p.lines]
    assert len(placed) == len(set(placed))                    # nothing placed twice
    want = {s.id for s in J.ROWS if JF.renderable(s.id)}
    assert set(placed) == want
    assert len(want) == 30 and len(J.ROWS) == 48              # 30 renderable, 18 declared, pinned
    # ...and every one of the 18 has a WRITTEN reason, so nothing is merely absent
    for s in J.ROWS:
        if not JF.renderable(s.id):
            assert s.eb_absent or s.status in JF.UNRENDERABLE_STATUS, s.id
            assert JF.unrenderable_reason(s.id).strip(), s.id


def test_the_ONE_row_with_an_eb_that_is_still_unrenderable():
    """meta.step_count is why `renderable` is not simply `eb is not None`. `B_SYSVAR[7]` is a real
    read of a real counter the GAME NEVER MOVES, so rendering it would print a permanent 'Steps 0' --
    a number that reads as 0% progress and as a bug. `eb` and `status` are orthogonal."""
    dead = [s.id for s in J.ROWS if s.eb is not None and not JF.renderable(s.id)]
    assert dead == ["meta.step_count"]
    assert J.row_spec("meta.step_count").eb == "B_SYSVAR[7]"
    assert J.row_spec("meta.step_count").status == "dead"
    assert "meta.step_count" not in {ln.row for p in JF.PAGES for ln in p.lines}


def test_no_page_renders_a_PLACEHOLDER_string():
    """The owner could not tell '--' (offline only) from 'n/a' (not tracked anywhere) -- both read as
    a broken row -- and 'S. purchases' was an unexplained abbreviation for a row that can never show
    anything. Checked on the rendered text, not on the Line kinds."""
    for p in JF.PAGES:
        text, _e = JF.render_page(p)
        for ln in text.split("\n")[1:]:
            assert not ln.rstrip().endswith("--"), (p.key, ln)
            assert "n/a" not in ln, (p.key, ln)
            assert "[NUMB=" in ln or "[TEXT=" in ln, (p.key, ln)
    # ...and the label the owner could not decode is on no page (the generated bench COMMENTARY
    # still quotes the verdict, which is why this reads the RENDERED replies, not the whole file).
    assert not any("S. purchases" in JF.render_page(p)[0] for p in JF.PAGES)
    assert "= offline only" not in JF.menu_text()             # the legend for a gone placeholder


def test_no_page_assigns_more_than_eight_slots():
    """ETb.SetMesValue clamps scriptID to 0..7 against `gMesValue = new Int32[8]`
    (ETb.cs:230-234 / EventEngine.Initialize.cs:30). A 9th write would land in slot 7."""
    for rep in JF.measure_pages():
        assert rep.slots <= JF.MES_VALUE_SLOTS, f"{rep.key}: {rep.slots}"


def test_no_page_exceeds_the_window_line_ceiling():
    for rep in JF.measure_pages():
        assert rep.lines <= JF.MAX_PAGE_LINES, f"{rep.key}: {rep.lines}"


def test_render_page_GROWS_the_header_rule_to_the_widest_line():
    """A CONSTRUCTION test, and labelled as one. `render_page` extends the `=` run until it
    out-measures every line, so "the header is the widest line" holds for EVERY Page input -- which
    means a lint rule or a per-page assertion over the shipped PAGES could never fail, and lint_pages
    no longer carries one (measured: 120 label widths brute-forced through render_page/measure_pages
    never fired it, and widening a real page label kept the lint green while the header silently
    grew). What CAN fail is the construction: delete the `while` in render_page and this goes red.

    It is also only COSMETIC -- the rule reaching the window edge. The engine bakes Width from the
    real rendered strings at open (Dialog.AutomaticSize; CanAutoResize() is `!UseSizeHint` and
    UseSizeHint is never set true, Dialog.cs:1196), which is what `page_body`'s publish-then-
    WindowSync ordering exists for. The shipped margins are as small as 0.05u under a model
    content/text.py:487-497 calls approximate, so this property is NOT an in-game width guarantee and
    must not be cited as one."""
    probe = JF.Page("probe", "T", "T", (JF.Line("party.gil", "Gil", "num"),))   # 7-digit worst case
    text, _exprs = JF.render_page(probe)
    header = text.split("\n")[0]
    assert header.startswith("== T ="), header                # the rule GREW past the bare "== T "
    # and NO [IMME]: an instant reply is dismissed by the very press that opened it
    # (THE BROADCAST-CONFIRM LAW, studies/messages/SURVEY.md §7a -- see render_page).
    assert "[IMME]" not in text, text[:120]
    assert T.measure(header) > JF._worst_case_width(probe.lines[0])


def test_no_page_header_reaches_the_build_time_wrap():
    """THE RULE THAT DOES THE WORK on the same quantity: the grown header still has to fit 28.0
    units, or the build re-flows it onto two lines and the page ships a broken-looking title."""
    for rep in JF.measure_pages():
        assert rep.header_width <= JF.WRAP_BUDGET, rep.key


def test_every_line_fits_the_build_time_wrap():
    """The 28.0-unit budget is the KIT's (content/text.py:500), applied to every collected .mes line
    at build (build.py:7766-7774) -- which is what actually explains the rung-0 header that wrapped
    in-game (33.10 units) versus the one that did not (19.45)."""
    assert T.measure("=== COMPLETION PROBE / RUNG 0 ====") > JF.WRAP_BUDGET
    assert T.measure("== FLEX PROBE / 0B ==") < JF.WRAP_BUDGET
    for rep in JF.measure_pages():
        for rid, _kind, lit, worst in rep.rows:
            assert max(lit, worst) <= JF.LINE_BUDGET, f"{rep.key}/{rid}: {lit:.2f}/{worst:.2f}"
    for ln in JF.menu_text().split("\n"):
        assert T.measure(ln) <= JF.WRAP_BUDGET, ln


def test_the_menu_fits_the_choice_row_cap_and_cancel_is_last():
    """With no [PCHC]/[PCHM] the engine's CANCEL row is the LAST one (content/choice.py:20-21), so
    pressing B must close the journal rather than open the last page."""
    rows = [ln.strip() for ln in JF.menu_text().split("[CHOO]")[1].split("\n")]
    assert len(rows) == len(JF.PAGES) + 1 <= JF.MAX_CHOICE_ROWS
    assert rows[-1] == JF.MENU_CLOSE
    assert rows[:-1] == [p.menu for p in JF.PAGES]


def test_denominators_are_literal_text_never_a_slot():
    """A baked '/24' costs zero slots and zero opcodes -- which is what makes 7 pages fit inside the
    8-slot ceiling. The number is checkable in the rendered text against denom_source."""
    text, exprs = JF.render_page(JF.PAGES[1])     # chocobo
    assert len(exprs) == 5
    assert f"/{J.CHOCOGRAPH_MAX}" in text and "/21" in text and "/99" in text


def test_every_rendered_fraction_IS_the_catalog_denominator():
    """ONE catalog, two renderers -- over every line of every page, not a sample.

    The defect this closes: page denominators were hand-typed literals sitting beside the catalog's
    own (`denom=64` for mognet.give_locks, whose RowSpec.denom is also 64), and NOTHING compared
    them. A one-character drift would have shipped 'Variants out 37/999' in-game while
    `journal report` printed 37/64, with no offline signal anywhere. `Line` no longer HAS a
    denominator field, so the two cannot disagree -- this test is the proof of that, and it also
    pins the exclusions (a table/dash/na line and a run-mode row render no fraction at all)."""
    for p in JF.PAGES:
        text, _e = JF.render_page(p)
        for line, rendered in zip(p.lines, text.split("\n")[1:]):
            spec = J.row_spec(line.row)
            got = re.search(r"/(\d+)$", rendered)             # "n/a" is not a fraction
            if line.kind != "num" or spec.run_mode or spec.exclusive_group:
                assert got is None, (p.key, line.row, rendered)
                continue
            want = J.KEY_ITEM_EB_COUNT if line.row == "party.key_items" else spec.denom
            assert (got.group(1) if got else None) == (None if want is None else str(want)), \
                (p.key, line.row, rendered, want)


def test_a_run_mode_or_exclusive_row_gets_NO_denominator():
    """Same exclusion the offline index applies (journal.py:1080-1084): a fraction that cannot
    legitimately fill reads as a bug."""
    text, _ = JF.render_page(next(p for p in JF.PAGES if p.key == "cards"))
    lines = {ln.split("[")[0].strip(): ln for ln in text.split("\n")}
    assert J.row_spec("minigame.collector_points").run_mode
    assert "/" not in lines["Coll. points"] and "/" not in lines["Coll. level"]
    assert "/100" in lines["Card kinds"]                  # ...but a plain engine max IS baked


def test_the_two_TBLE_banks_come_from_the_catalog_not_a_copy():
    assert JF.TABLES["th_rank"] == J.TH_RANKS
    assert JF.table_texts()["th_rank"].startswith("[TBLE=9,]")     # stock's form: row count first
    assert JF.table_texts()["hunt"].split("\n")[2:3] == ["Vivi"]   # byte 313 == 2, EMinigame.cs:302
    # the preview and the build's own emitter are ONE function, never two spellings of the tag
    from ff9mapkit.content import texttable as TT
    assert JF.table_texts() == {n: TT.entry_text(r) for n, r in JF.TABLES.items()}
    assert JF.text_table_blocks() == [{"name": "th_rank", "rows": list(J.TH_RANKS)},
                                      {"name": "hunt", "rows": ["---", "Zidane", "Vivi", "Freya"]}]


def test_a_page_emits_the_BANK_NAME_and_never_a_NUMBER():
    """collect_text assigns txids BY POSITION (content.text.txid_map), so a hand-written [TEXT=600,2]
    bakes an id that moves the moment a line is added above it -- and the failure is silent (a wrong
    bank renders another table's row; a bank with no entry renders String.Empty, i.e. a BLANK line,
    which a player reads as a bug). This module therefore has no number it could get wrong: it emits
    the [[text_table]] NAME and the build substitutes. An unknown table is refused, not emitted."""
    text, _ = JF.render_page(JF.PAGES[0])
    assert "[TEXT=th_rank,2]" in text
    assert re.search(r"\[TEXT=\d", text) is None, text
    for p in JF.PAGES:
        assert re.search(r"\[TEXT=\d", JF.render_page(p)[0]) is None, p.key
    with pytest.raises(KeyError):
        JF.render_page(JF.Page("p", "T", "T",
                               (JF.Line("treasure.hunter_rank", "R", "table", table="nope"),)))


# ---- the emitted .eb ---------------------------------------------------------------------------
def test_a_page_publishes_every_value_BEFORE_the_window_opens():
    """Order is load-bearing: `Dialog.AutomaticSize` bakes the width over the values present at
    open, and never re-sizes afterwards."""
    p = next(p for p in JF.PAGES if p.key == "mognet")
    _text, exprs = JF.render_page(p)
    body = JF.page_body(exprs, 704, table_slots=JF.table_slots_of(p))
    ins = list(D.iter_code(body, 0, len(body)))
    assert [i.op for i in ins] == [0x66] * len(exprs) + [0x1F]
    assert [i.args[0] for i in ins[:-1]] == list(range(len(exprs)))
    assert ins[-1].args == [JF.PAGE_WINDOW, JF.PAGE_FLAGS, 704]


def test_a_TEXT_slot_is_clamped_by_the_EMITTER_not_by_the_author():
    """ETb.GetStringFromTable bounds the slot and the UPPER row but has NO lower bound (ETb.cs:270-284),
    so a negative indexes tableText[-n] and throws. The clamp is `E E const(0) B_GE B_MULT` -- E is
    DUPLICATED; the single-E spelling both defeats the clamp and underflows the CalcStack."""
    from ff9mapkit.content.behavior import hud_row_index_clamp
    p = JF.PAGES[0]                                       # story: slot 2 feeds [TEXT=]
    assert JF.table_slots_of(p) == (2,)
    _t, exprs = JF.render_page(p)
    body = JF.page_body(exprs, 700, table_slots=JF.table_slots_of(p))
    ins = list(D.iter_code(body, 0, len(body)))
    clamped = EA.assemble(hud_row_index_clamp(exprs[2]) + " B_EXPR_END")
    assert clamped in body
    assert EA.assemble(exprs[2] + " B_EXPR_END") not in body   # the UNCLAMPED form is not emitted
    assert JF.pretty_listing(body)[2].count("B_MULT") == 1   # the clamp, and only the clamp


def test_every_table_slot_on_every_page_is_clamped():
    for p in JF.PAGES:
        from ff9mapkit.content.behavior import hud_row_index_clamp
        _t, exprs = JF.render_page(p)
        body = JF.page_body(exprs, 700, table_slots=JF.table_slots_of(p))
        for slot in JF.table_slots_of(p):
            assert EA.assemble(hud_row_index_clamp(exprs[slot]) + " B_EXPR_END") in body


def test_the_talk_handler_uses_SWITCH_dispatch_never_per_arm_if_blocks():
    """Every arm opens a window and a window overwrites sysvar 9, so `choice.branch`'s per-arm
    re-read of GetChoose() would test the PAGE window's answer (content/choice.py:283-300).
    ⚠ build.py:6097 selects switch dispatch only for input/qte rows, so the generator must ask."""
    body = JF.talk_body({p.key: 700 + i for i, p in enumerate(JF.PAGES)}, 699)
    ops = [i.op for i in D.iter_code(body, 0, len(body))]
    assert ops.count(R.SETREGION_OP) == 0
    assert ops.count(0x0B) == 1                           # exactly ONE switch, read once
    # the selector push that must immediately precede it: op_05 { B_SYSVAR(9) B_EXPR_END }
    assert bytes([R.EXPR_OP, R.T_SYSVAR, R.SYSVAR_CHOICE, R.T_END, 0x0B]) in body
    sw = next(i for i in D.iter_code(body, 0, len(body)) if i.op == 0x0B)
    edges = D.decode_switch(sw).edges
    assert len([e for e in edges if not e.is_default]) == len(JF.PAGES) + 1  # a page each, + Close


def test_the_loop_latch_is_a_MAP_bit_and_the_close_arm_clears_it():
    """MAP scope, not GLOB: per-field transient, no save write. `EventContext.mapvar = new Byte[80]`
    (EventContext.cs:9) -> bit indices 0..639, so the latch must be inside that."""
    assert 0 <= JF.LOOP_LATCH_BIT < 80 * 8
    body = JF.talk_body({p.key: 700 + i for i, p in enumerate(JF.PAGES)}, 699)
    assert R.set_var(R.MAP_BOOL, JF.LOOP_LATCH_BIT, 1) in body
    assert R.set_var(R.MAP_BOOL, JF.LOOP_LATCH_BIT, 0) in body
    from ff9mapkit.eb import opcodes as OPC
    assert body.startswith(OPC.DISABLE_MOVE)              # lock control FIRST
    assert body.endswith(OPC.ENABLE_MOVE + OPC.RETURN)    # ...restore it, then return


def test_the_loop_jumps_BACKWARD_to_the_condition():
    """`while_block` is the kit's only backward-jumping construct and the two jump ops differ in
    SIGNEDNESS: 0x02 (JMP_IFNOT) reads its operand UNSIGNED and can only go forward, 0x01 (JMP)
    reads a SIGNED int16. The disassembler prints the operand unsigned, so 62434 IS -3102."""
    import struct
    body = JF.talk_body({p.key: 700 + i for i, p in enumerate(JF.PAGES)}, 699)
    ins = list(D.iter_code(body, 0, len(body)))
    hop = ins[-3]                                         # ... back-hop, EnableMove, RETURN
    assert hop.op == R.JMP_UNCOND
    skip = struct.unpack("<h", struct.pack("<H", hop.args[0]))[0]
    assert skip < 0
    cond_at = hop.off + hop.length + skip
    assert cond_at == 1 + len(R.set_var(R.MAP_BOOL, JF.LOOP_LATCH_BIT, 1))   # the loop condition


def test_the_whole_dashboard_fits_the_eb_offset_budget():
    """Measured on the REAL emitted stream against binutils.EB_FILE_BUDGET -- never len() of
    something else."""
    used, budget = JF.eb_budget()
    assert used == len(JF.talk_body({p.key: 700 + i for i, p in enumerate(JF.PAGES)}, 699))
    assert used < budget // 4, f"{used} of {budget}"


def test_page_local_expressions_get_the_same_gate_as_row_expressions():
    """Play time's minutes remainder is the ONLY page-local expression, and it must not be the one
    slot nobody checks."""
    extras = [(p.key, ln.row, ex) for p in JF.PAGES for ln in p.lines for ex in ln.extra]
    assert extras == [("meta", "meta.play_time", "B_SYSVAR[20] const(60) B_DIV const(60) B_REM")]
    for _k, _r, ex in extras:
        assert ES.analyze(ex + " B_EXPR_END").unsafe_to_repeat == ()
        EA.assemble(ex + " B_EXPR_END")
        lo, hi = J.eb_bounds(ex)
        assert EXPR_VALUE_MIN <= lo and hi <= EXPR_VALUE_MAX
        assert (lo, hi) == (0, 59)                        # minutes, not seconds


def test_play_time_renders_as_hours_h_minutes():
    text, exprs = JF.render_page(JF.PAGES[-1])
    assert "[NUMB=1]h[NUMB=2]" in text
    assert exprs[1] == J.row_spec("meta.play_time").eb
    assert J.eb_eval(exprs[1], lambda t: 3600 * 7 + 60 * 42) == 7
    assert J.eb_eval(exprs[2], lambda t: 3600 * 7 + 60 * 42) == 42


def test_the_UNIT_comes_from_the_catalog_so_a_SCALED_value_cannot_print_BARE():
    """meta.play_time is the one row whose expression publishes a different unit from its offline
    reader (hours vs the 95000_Setting seconds -- journal.EB_SCALE declares it, and lint_rows +
    the cross-validation enforce it). The 'h' the page prints is READ FROM THAT DECLARATION, not
    typed on the Line, so the row cannot render `Play time  7` -- indistinguishable in-game from
    7 seconds -- and no other row can grow a stray unit."""
    assert J.row_spec("meta.play_time").eb_scale == 3600
    assert J.row_spec("meta.play_time").eb_unit == "h"
    for p in JF.PAGES:
        text, _e = JF.render_page(p)
        for line, rendered in zip(p.lines, text.split("\n")[1:]):
            spec = J.row_spec(line.row)
            if line.kind == "num" and spec.eb_scale != 1:
                assert f"]{spec.eb_unit}" in rendered, (line.row, rendered)
            else:
                assert "]h" not in rendered, (line.row, rendered)


def test_pretty_listing_restores_the_disassembler():
    before = D.read_expr
    out = JF.pretty_listing(JF.page_body(("B_SYSVAR[6]",), 700))
    assert D.read_expr is before
    assert "B_SYSVAR[6]" in out[0] and "SetTextVariable" in out[0]


# ---- THE NEGATIVE TWINS: every ceiling above must be able to FAIL -------------------------------
def _page(*lines, title="X"):
    return (JF.Page("probe", title, "Probe", tuple(lines)),)


#: rows that CAN be probed with a `num` line without tripping the placement audit's second arm
_LIVE = [s.id for s in J.ROWS if JF.renderable(s.id)]


def _all_but(rows):
    """The shipped pages minus the rows a probe page re-uses, so the placement rule stays green and
    only the rule under test can fire."""
    keep = []
    for p in JF.PAGES:
        kept = tuple(ln for ln in p.lines if ln.row not in rows)
        if kept:
            keep.append(JF.Page(p.key, p.title, p.menu, kept))
    return tuple(keep)


def test_a_ninth_slot_FAILS_the_gate():
    rows = [s.id for s in J.ROWS if s.eb and s.status == "tracked"][:9]
    probe = _page(*[JF.Line(r, "L", "num") for r in rows])
    bad = JF.lint_pages(pages=_all_but(set(rows)) + probe,
                        check_live_install=False)
    assert any("value slots >" in m for m in bad), bad


def test_a_fourteenth_line_FAILS_the_gate():
    rows = _LIVE[:14]
    probe = _page(*[JF.Line(r, "L", "num") for r in rows])
    bad = JF.lint_pages(pages=_all_but(set(rows)) + probe,
                        check_live_install=False)
    assert any("rendered lines >" in m for m in bad), bad


def test_a_too_wide_value_line_FAILS_the_gate():
    """THE RULE THAT DOES THE WORK on width. `render_page` grows the header past every value line BY
    CONSTRUCTION, so "header is widest" can never fail on page data -- but a value line wide enough
    to push that grown header past the 28.0 wrap makes the HEADER re-flow onto two lines at build.
    That is the failure this catches, and it is what bounds LINE_BUDGET."""
    probe = _page(JF.Line("combat.yan_blessing", "A label far too long to fit a window", "num"))
    bad = JF.lint_pages(pages=_all_but({"combat.yan_blessing"}) + probe,
                        check_live_install=False)
    assert any("units >" in m for m in bad), bad
    assert any("re-flow it onto two lines" in m for m in bad), bad


def test_a_DROPPED_row_FAILS_the_gate():
    """ARM ONE of the placement audit: a row that CAN carry a value must be on a page."""
    assert any("is on NO " in m
               for m in JF.lint_pages(pages=_all_but({"party.gil"}),
                                      check_live_install=False))


def test_a_row_placed_TWICE_fails_the_gate():
    probe = _page(JF.Line("party.gil", "Gil", "num"))
    assert any("placed on 2 pages" in m
               for m in JF.lint_pages(pages=JF.PAGES + probe,
                                      check_live_install=False))


def test_PLACING_an_eb_absent_row_FAILS_the_gate():
    """ARM TWO of the placement audit, and the arm the old single-arm rule did not have: a row with
    NO .eb expression cannot be on a page at all. It used to be legal there as a '--'/'n/a' line, and
    the owner reported those as broken values."""
    probe = _page(JF.Line("party.thefts", "Steals", "num"))
    bad = JF.lint_pages(pages=_all_but({"party.thefts"}) + probe, check_live_install=False)
    assert any("can never carry a value" in m and "eb_absent" in m for m in bad), bad


def test_PLACING_a_DEAD_row_FAILS_the_gate():
    """meta.step_count HAS an .eb read (B_SYSVAR[7]) and the game never moves the counter, so a page
    that rendered it would print a permanent 'Steps 0'. `eb` and `status` are orthogonal facts, and
    the same arm catches both -- that is why `renderable` is not `eb is not None`."""
    assert J.row_spec("meta.step_count").eb == "B_SYSVAR[7]"
    assert J.row_spec("meta.step_count").status == "dead"
    probe = _page(JF.Line("meta.step_count", "Steps", "num"))
    bad = JF.lint_pages(pages=_all_but({"meta.step_count"}) + probe, check_live_install=False)
    assert any("can never carry a value" in m and "status='dead'" in m for m in bad), bad


def test_a_PLACEHOLDER_kind_FAILS_the_gate():
    """There is no 'dash'/'na' kind any more, and a Page that invents one must not render anything
    silently -- the audit's second arm catches the row, and the kind rule catches the line."""
    probe = _page(JF.Line("party.thefts", "Steals", "na"))
    bad = JF.lint_pages(pages=_all_but({"party.thefts"}) + probe, check_live_install=False)
    assert any("has kind 'na'" in m for m in bad), bad


def test_the_key_item_numerator_and_denominator_CANNOT_disagree():
    """THE ONE BUILD-TIME BAKE, and the one rule here with no negative twin -- on purpose.

    A .mes is static, so /80 cannot resolve at runtime; the numerator (the B_HAVE_ITEM term count)
    and the denominator must span the SAME id window. That used to be a lint rule fed by a
    `key_item_count` parameter, i.e. a disagreement was REPRESENTABLE and merely detected -- and its
    detection was skipped on exactly the machines that could not read the install. Both now come from
    `journal.KEY_ITEM_EB_COUNT`, so there is no second number to drift. What is still checked at
    runtime is the thing arithmetic cannot settle -- whether that constant matches this INSTALL --
    and that check is `test_the_live_install_read_is_LOUD_in_BOTH_directions`."""
    ids = [int(t[len("const("):-1]) for t in J.row_spec("party.key_items").eb.split()
           if t.startswith("const(")]
    assert len(ids) == J.KEY_ITEM_EB_COUNT
    text, _e = JF.render_page(next(p for p in JF.PAGES if p.key == "party"))
    assert f"/{len(ids)}" in text


def test_a_bad_page_local_expression_FAILS_the_gate():
    probe = _page(JF.Line("combat.yan_blessing", "Q", "num", extra=("Global.Byte[1] B_PLUS",),
                          extra_source="EBin.cs:1866"))
    bad = JF.lint_pages(pages=_all_but({"combat.yan_blessing"}) + probe,
                        check_live_install=False)
    assert any("does not evaluate" in m for m in bad), bad


# ---- the bench field ---------------------------------------------------------------------------
_BENCH = os.path.join(os.path.dirname(__file__), "..", "..", "studies", "completion-journal",
                      "bench", "journal_dash.field.toml")


@pytest.mark.skipif(not os.path.isfile(_BENCH), reason="the T1b bench toml is not in this checkout")
def test_the_checked_in_bench_toml_is_exactly_what_the_generator_emits():
    """The bench ships the REAL page text, so it must not be hand-editable: a drifted bench would
    playtest a layout the catalog no longer describes and the verdict would be attributed to the
    wrong thing."""
    # universal newlines: autocrlf rewrites the checkout's EOLs, and the drift this guards
    # against is CONTENT drift, not line endings (project-ff9-autocrlf-byte-assets).
    on_disk = io.open(_BENCH, encoding="utf-8").read()
    assert on_disk == JF.bench_toml()


@pytest.mark.skipif(not os.path.isfile(_BENCH), reason="the T1b bench toml is not in this checkout")
def test_the_bench_toml_parses_and_carries_the_load_bearing_pieces():
    import tomllib
    d = tomllib.loads(io.open(_BENCH, encoding="utf-8").read())
    assert d["field"]["id"] == JF.BENCH_FIELD_ID == 30801   # NOT 30800 -- that is the rung-0/0b probe
    assert "text_block" not in d["field"]                   # the kit derives + auto-registers it
    # THE SILENT-DROP TRAP: behaviortoml.table() returns None unless [[behavior.unit]] exists
    # (content/behaviortoml.py:147-150), so a [behavior] block without one compiles to NOTHING.
    assert d["behavior"]["unit"] and d["behavior"]["unit"][0]["npc"]
    from ff9mapkit.content import behaviortoml as BT
    assert BT.table(d) is not None
    ch = d["choice"][0]
    assert [o["text"] for o in ch["options"]] == [p.menu for p in JF.PAGES] + [JF.MENU_CLOSE]
    assert "reply" not in ch["options"][-1]                 # Close does nothing but close
    for p, o in zip(JF.PAGES, ch["options"]):
        assert o["reply"] == JF.bench_page_text(p) == JF.render_page(p)[0]
        assert not o["reply"].endswith(chr(10))            # a trailing blank line costs a window row
    # THE BENCH DECLARES ITS OWN [TBLE] BANKS, and its page text carries the real tag rather than the
    # widest literal row it used to freeze in (owner: "T hunter rank and chests opened are wrong").
    assert d["text_table"] == JF.text_table_blocks()
    names = {t["name"] for t in d["text_table"]}
    refs = [(t, s) for o in ch["options"] for t, s in
            re.findall(r"\[TEXT=([^,\]]+),(\d+)\]", o.get("reply", ""))]
    assert refs == [("th_rank", "2"), ("hunt", "4")]
    assert {t for t, _s in refs} <= names                   # every reference resolves in this field


@pytest.mark.skipif(not os.path.isfile(_BENCH), reason="the T1b bench toml is not in this checkout")
def test_every_bench_page_carries_its_own_value_list():
    """Slot i is values[i], and the [NUMB=i] indices in the reply are `render_page`'s own numbering,
    so the two orders are the same order by construction. This is the GENERATOR half only -- it is
    exactly the assertion that passed while the bench shipped unwired, which is why it is followed by
    a test that reads the BUILT .eb."""
    import tomllib
    d = tomllib.loads(io.open(_BENCH, encoding="utf-8").read())
    opts = d["choice"][0]["options"]
    for p, o in zip(JF.PAGES, opts):
        assert o["values"] == list(JF.bench_page_values(p)), p.key
        assert all(v.startswith("expr:") for v in o["values"])
        _t, exprs = JF.render_page(p)
        assert [v[len("expr:"):] for v in o["values"]] == list(exprs)   # the catalog's, not a copy
    assert "values" not in opts[-1]                       # Close publishes nothing and opens nothing


# ---- THE BUILT ARTIFACT: the test that would have caught the mockup -----------------------------
@pytest.fixture(scope="module")
def built_bench_eb(tmp_path_factory):
    """BUILD the checked-in bench and hand back its emitted ``.eb`` bytes.

    THE POINT, stated plainly. T1b shipped as a layout mockup: `journalfield` generated 3114 bytes of
    correct, reviewed value writes and NOTHING carried them into a field, because `[[logic_add]]` is
    refused without `[verbatim_eb]` (build.py:930-934) and `[behavior]` is refused on a verbatim fork.
    Every offline test in this module stayed green, because every one of them tested the GENERATOR.
    In-game all seven pages then rendered the previous bench's leftover gMesValue vector -- ETb's
    `Int32[8]` is allocated once at engine init (EventEngine.Initialize.cs:30) and never cleared on a
    field load, so an unwritten slot renders stale, not blank.

    A test that only asks `journalfield` what it would emit cannot see an unwired field. This one
    asks the .eb the build actually wrote."""
    from pathlib import Path
    from ff9mapkit.build import FieldProject, build_mod
    from ff9mapkit.config import ModLayout
    out = tmp_path_factory.mktemp("journal_bench_mod")
    build_mod([FieldProject.load(Path(_BENCH))], out, mod_name="FF9CustomMap")
    return ModLayout(out).eb_path("us", "EVT_JOURNALDASH.eb.bytes").read_bytes()


@pytest.fixture(scope="module")
def built_bench_mes(tmp_path_factory):
    """BUILD the checked-in bench and hand back ``{txid: entry body}`` from its emitted ``.mes``.

    The .eb half of the dashboard was already read from the artifact; the STRING half was not, and
    that is where the frozen-rank defect lived. `journalfield` can only be asked what tag it would
    write -- whether the build turned that tag's NAME into the txid the [TBLE] entry actually landed
    on is a property of the emitted file and nothing else. An off-by-one there renders another
    table's row or a blank line, in-game, with no error anywhere."""
    from pathlib import Path
    from ff9mapkit.build import FieldProject, build_mod
    out = tmp_path_factory.mktemp("journal_bench_text")
    build_mod([FieldProject.load(Path(_BENCH))], out, mod_name="FF9CustomMap")
    raw = (out / "FF9_Data/embeddedasset/text/us/field"
           / f"{JF.BENCH_FIELD_ID}.mes").read_text(encoding="utf-8")
    pat = re.compile(r"_\[TXID=(\d+)\](?:\[STRT=[^\]]*\])?(?:\[TAIL=[^\]]*\])?(.*?)\[ENDN\]", re.S)
    return {int(m.group(1)): m.group(2) for m in pat.finditer(raw)}


@pytest.mark.skipif(not os.path.isfile(_BENCH), reason="the T1b bench toml is not in this checkout")
def test_the_BUILT_mes_CONTAINS_a_TBLE_entry_per_declared_bank(built_bench_mes):
    """The emitted .mes used to contain ZERO [TBLE] entries -- `grep -c TBLE` returned 0 -- because
    the kit had no general emitter and the bench froze each tag to a literal row instead."""
    from ff9mapkit.content import texttable as TT
    banks = {t: b for t, b in built_bench_mes.items() if TT.TABLE_OPEN in b}
    assert len(banks) == len(JF.TABLES) == 2
    assert sorted(banks.values()) == sorted(JF.table_texts().values())
    # rows survive the text pipeline verbatim: the engine splits the body on '\n' after the tag
    # (DialogBoxSymbols.cs:35-38), so a re-flow or an escaped newline would silently re-number them
    for name, rows in JF.TABLES.items():
        body = next(b for b in banks.values() if b == TT.entry_text(rows))
        assert body.split("]", 1)[1].split("\n") == list(rows), name


@pytest.mark.skipif(not os.path.isfile(_BENCH), reason="the T1b bench toml is not in this checkout")
def test_the_BUILT_mes_TAG_BANK_IS_the_txid_the_build_assigned(built_bench_mes):
    """THE OFF-BY-ONE GATE, on the artifact. Every `[TEXT=bank,slot]` in the shipped .mes must carry
    a NUMBER (a surviving name would be parsed as bank 0 by the engine's Single.TryParse) and that
    number must be the txid of the entry holding THAT table's rows -- not the one before or after it.
    `ETb.GetStringFromTable` returns String.Empty for an unknown bank: a blank line, no error."""
    from ff9mapkit.content import texttable as TT
    by_body = {b: t for t, b in built_bench_mes.items()}
    want = {name: by_body[TT.entry_text(rows)] for name, rows in JF.TABLES.items()}
    # what the pages ASK for, by name + slot, straight off the generator
    asked = [(ln.table, slot) for p in JF.PAGES
             for slot, ln in zip(_slots_of(p), p.lines) if ln.kind == "table"]
    assert asked == [("th_rank", 2), ("hunt", 4)]
    got = sorted((int(m.group(1)), int(m.group(2)))
                 for b in built_bench_mes.values()
                 for m in re.finditer(r"\[TEXT=([^,\]]+),(\d+)\]", b))
    assert got == sorted((want[t], s) for t, s in asked), (got, want)
    # ...and no tag kept a NAME: the substitution ran on every line, not just the ones we looked at
    assert not [m.group(0) for b in built_bench_mes.values()
                for m in re.finditer(r"\[TEXT=([^,\]]+),(\d+)\]", b)
                if not m.group(1).isdigit()]


def _slots_of(page):
    """The gMesValue slot each of ``page``'s lines publishes into -- the same walk `render_page` and
    `table_slots_of` do, spelled once for the tests that need the pairing."""
    out, slot = [], 0
    for ln in page.lines:
        out.append(slot)
        slot += 1 + len(ln.extra)
    return out


@pytest.mark.skipif(not os.path.isfile(_BENCH), reason="the T1b bench toml is not in this checkout")
def test_the_BUILT_mes_carries_NO_frozen_table_literal(built_bench_mes):
    """The defect in its own words: the rank line shipped as `T.Hunter rank          H`, a literal,
    on every save. A page line naming a table must end in the tag."""
    from ff9mapkit.content import texttable as TT
    pages = [b for b in built_bench_mes.values() if TT.TABLE_OPEN not in b]
    rank = [ln for b in pages for ln in b.split("\n") if ln.startswith("T.Hunter rank")]
    hunt = [ln for b in pages for ln in b.split("\n") if ln.startswith("Hunt winner")]
    assert len(rank) == len(hunt) == 1
    assert re.search(r"\[TEXT=\d+,2\]$", rank[0]), rank
    assert re.search(r"\[TEXT=\d+,4\]$", hunt[0]), hunt
    for row in list(JF.TABLES["th_rank"]) + list(JF.TABLES["hunt"]):
        assert not rank[0].endswith(row) and not hunt[0].endswith(row)


@pytest.mark.skipif(not os.path.isfile(_BENCH), reason="the T1b bench toml is not in this checkout")
def test_the_BUILT_eb_carries_every_page_value_write_on_the_right_slot(built_bench_eb):
    """Per page, per slot: the exact `SetTextVariable(slot, <expr>)` blob the catalog expression
    assembles to is PRESENT in the built .eb, exactly once, and the blobs appear in page order and
    then slot order. Byte-exact, so a right-count/wrong-expression wiring fails too.

    ⚠ A SLOT A `[TEXT=]` TAG READS IS EXPECTED IN ITS CLAMPED FORM, and that is new: the bench's page
    text now carries the real tag, so `content/choice.py:option_values_body` reads the reply with
    `hud_text_table_slots` and wraps `hud_row_index_clamp` around exactly those slots. While the bench
    substituted the widest literal row, nothing in the reply indexed the table and nothing clamped --
    an unclamped negative row index throws in `ETb.GetStringFromTable` once per rendered frame."""
    from ff9mapkit.content.behavior import hud_row_index_clamp
    prev = -1
    for p in JF.PAGES:
        clamped_slots = set(JF.table_slots_of(p))
        for slot, src in enumerate(JF.bench_page_values(p)):
            toks = src[len("expr:"):]
            if slot in clamped_slots:
                toks = hud_row_index_clamp(toks)
            blob = OPC.set_text_variable_expr(slot, EA.assemble(toks + " B_EXPR_END"))
            assert built_bench_eb.count(blob) == 1, f"{p.key} slot {slot}: {built_bench_eb.count(blob)}"
            off = built_bench_eb.index(blob)
            assert off > prev, f"{p.key} slot {slot} is emitted out of order ({off} after {prev})"
            prev = off


@pytest.mark.skipif(not os.path.isfile(_BENCH), reason="the T1b bench toml is not in this checkout")
def test_the_BUILT_eb_has_EXACTLY_the_expected_number_of_value_writes(built_bench_eb):
    """The count rule, which is the half that catches BOTH failure directions: zero writes (the
    mockup) and a stray extra publish nobody asked for. Counted by DECODING the .eb, not by
    substring-searching it, so an 0x66 byte inside an expression operand cannot inflate it."""
    from ff9mapkit.eb.model import EbScript
    eb = EbScript.from_bytes(built_bench_eb)
    got = [i for e in eb.entries if not e.empty for f in e.funcs
           for i in eb.instrs(f) if i.name == "SetTextVariable"]
    want = sum(len(JF.bench_page_values(p)) for p in JF.PAGES)
    assert want == 31                                     # 3+5+5+5+7+2+4 -- pinned, not derived twice
    assert len(got) == want, f"{len(got)} SetTextVariable ops in the built .eb, expected {want}"
    assert [i.imm(0) for i in got] == [s for p in JF.PAGES
                                       for s in range(len(JF.bench_page_values(p)))]


@pytest.mark.skipif(not os.path.isfile(_BENCH), reason="the T1b bench toml is not in this checkout")
def test_the_BUILT_eb_publishes_each_page_BEFORE_that_pages_window_opens(built_bench_eb):
    """Dialog bakes its width ONCE at open over the values present (Dialog.AutomaticSize,
    Dialog.cs:1560-1591) and never re-sizes, so a publish after the window would render at a width
    measured over the previous field's numbers. Checked on the built stream: every page's LAST value
    write is followed by that page's OPEN before the next page's FIRST value write.

    ⚠ The open is per-page now: `WindowAsync` for a POLLED page, `WindowSync` for the rest. The
    publish-then-open ordering is the invariant; the opcode is the page's shape."""
    from ff9mapkit.eb.model import EbScript
    eb = EbScript.from_bytes(built_bench_eb)
    opens = ("WindowSync", "WindowAsync")
    stream = [i for e in eb.entries if not e.empty for f in e.funcs for i in eb.instrs(f)
              if i.name in ("SetTextVariable",) + opens]
    kinds = [i.name for i in stream]
    want = ["WindowSync"]                                 # the selector prompt
    for p in JF.PAGES:
        want += ["SetTextVariable"] * len(JF.bench_page_values(p))
        want += ["WindowAsync" if p.polled else "WindowSync"]
    assert kinds[:len(want)] == want, kinds[:len(want)]


# ---- ★ THE POLLED PAGE: the turbo-proof primitive, and every gate it owes -----------------------
# The design, its engine citations and its bench plan are in studies/completion-journal/PLAN.md
# ("THE TURBO-PROOF PAGE"). One page converts this round -- the shortest one, menu row 0 -- and the
# other six are the same-field control, which is the whole reason the in-game verdict will be
# readable. Everything below is the OFFLINE half: the exact op sequence, the exact .mes tags, and
# the flags split that makes the A/B real in the bytes.

def test_exactly_ONE_page_is_polled_this_round():
    """One change per in-game test. If a later round converts the rest, this number moves WITH the
    playtest that justified it -- it is pinned so that cannot happen by drift."""
    polled = [p.key for p in JF.PAGES if p.polled]
    assert polled == ["story"], polled
    assert JF.PAGES[0].key == "story" and len(JF.PAGES[0].lines) == 3   # row 0, the shortest page


def test_the_polled_page_flags_are_OUTSIDE_the_turbo_injection_predicate():
    """The STRUCTURAL guard. ShouldTurboDialog arm B (UIKeyTrigger.cs:984) tests
    `Style == WindowStyleAuto || Style == WindowStyleTransparent`, and the styles are derived from
    the flags byte by ETb.FlagsToStyles -- so this is a property of the number, not of a name."""
    assert JF.POLLED_PAGE_FLAGS == 0
    assert not T.turbo_injectable(JF.POLLED_PAGE_FLAGS)
    assert T.turbo_injectable(JF.PAGE_FLAGS)              # ...and the SYNC pages are exposed, which
    #                                                      is exactly why they still need [NTUR]
    # the full exposure table, transcribed from ETb.cs:167-186 + Dialog.cs:1921-1927
    assert {f for f in (0, 4, 8, 16, 64, 128, 132, 144, 160) if T.turbo_injectable(f)} == \
        {16, 128, 144, 160}


def test_a_polled_page_emits_the_EXACT_op_sequence():
    """The 32-byte primitive, byte for byte, disassembled -- not a shape assertion.

    WindowAsync(win, 0, txid) ; Wait(8) ; 05{const4(720896) B_KEYON} ; JMP_IF ; Wait(1) ; JMP ;
    CloseWindow(win) ; Wait(4). The back-hop MUST be 0x01 (signed): JMP_IFNOT (0x02) reads its
    operand UNSIGNED and can only go forward, so a loop built on it would jump into the weeds."""
    import struct
    p = JF.PAGES[0]
    _t, exprs = JF.render_page(p)
    body = JF.page_body_async(exprs, 700, window=2, table_slots=JF.table_slots_of(p))
    pub = JF._publish(exprs, JF.table_slots_of(p))
    assert body.startswith(pub)                           # values FIRST -- AutomaticSize bakes once
    tail = body[len(pub):]
    assert len(tail) == 32
    assert tail == bytes.fromhex("20000200bc02"          # WindowAsync(2, 0, 700)
                                 "220008"                # Wait(8)          -- the debounce
                                 "057e00000b004f7f"      # 05{ const4(0xB0000) B_KEYON }
                                 "030600"                # JMP_IF done
                                 "220001"                # Wait(1)
                                 "01efff"                # JMP poll         -- signed, -17
                                 "210002"                # CloseWindow(2)
                                 "220004")               # Wait(4)          -- the settle
    ins = list(D.iter_code(tail, 0, len(tail)))
    assert [i.op for i in ins] == [0x20, 0x22, 0x05, 0x03, 0x22, 0x01, 0x21, 0x22]
    assert ins[0].args == [2, JF.POLLED_PAGE_FLAGS, 700]  # WindowAsync(win, plain, txid)
    assert ins[1].args == [8] and ins[4].args == [1] and ins[7].args == [4]
    assert ins[6].args == [2]                             # CloseWindow(win)
    assert "B_KEYON" in JF.pretty_listing(tail)[2]
    assert struct.unpack("<h", struct.pack("<H", ins[5].args[0]))[0] < 0   # the back-hop is SIGNED


def test_the_poll_mask_is_stocks_own_dismissal_mask():
    """720896 = Confirm|Cancel|Special -- the mask on 1,710 of the 2,034 stock poll-adjacent async
    window sites. The bits come from EventInput.cs:537-562, not from a magic number."""
    from ff9mapkit.content import event as EV
    assert (EV.KEY_CONFIRM, EV.KEY_CANCEL, EV.KEY_SPECIAL) == (0x20000, 0x10000, 0x80000)
    assert EV.KEY_DISMISS == 0xB0000 == 720896


def test_the_polled_emitter_REFUSES_an_arm_B_style():
    """BREAK IT TO PROVE IT. The poll's own B_KEYON sets VoicePlayer.scriptRequestedButtonPress
    (EBin.cs:1080), so an Auto/Transparent polled window has the ENGINE press Confirm for it -- the
    same symptom as the broadcast bug, through a different mechanism. This is the one guard that can
    be structural, so it raises rather than lints."""
    p = JF.PAGES[0]
    _t, exprs = JF.render_page(p)
    for bad_flags in (128, 16, 144, 160):
        with pytest.raises(ValueError, match="arm B"):
            JF.page_body_async(exprs, 700, flags=bad_flags, table_slots=JF.table_slots_of(p))
    for ok_flags in (0, 4, 8, 64, 132):
        JF.page_body_async(exprs, 700, flags=ok_flags, table_slots=JF.table_slots_of(p))


def test_an_empty_poll_mask_is_REFUSED():
    """A mask of 0 never exits the loop: the field hangs with a window nobody can close and control
    locked -- offline it looks like a perfectly ordinary 32-byte block."""
    from ff9mapkit.content import event as EV
    for bad in (0, -1, 1 << 27):
        with pytest.raises(ValueError, match="26-bit"):
            EV.polled_window(700, window=2, flags=0, mask=bad)


def test_the_talk_handler_uses_the_ASYNC_shape_for_the_POLLED_page_ONLY():
    """The A/B in the .eb the shipped dashboard would emit: one WindowAsync, six WindowSyncs, and
    the async one carries the plain flags while the sync ones carry the bubble flags."""
    body = JF.talk_body({p.key: 700 + i for i, p in enumerate(JF.PAGES)}, 699)
    ins = list(D.iter_code(body, 0, len(body)))
    asyncs = [i for i in ins if i.op == 0x20]
    syncs = [i for i in ins if i.op == 0x1F]
    assert len(asyncs) == 1 and len(syncs) == 1 + len(JF.PAGES) - 1   # menu + the 6 sync pages
    assert asyncs[0].args == [JF.PAGE_WINDOW, JF.POLLED_PAGE_FLAGS, 700]
    assert all(i.args[1] == JF.PAGE_FLAGS for i in syncs)
    assert sum(1 for i in ins if i.op == 0x21) == 1                   # exactly one CloseWindow
    # ...and the byte cost of the conversion, MEASURED on the real stream rather than predicted:
    # the 32-byte polled block replaces a 6-byte WindowSync, so +26 per page, not the +27 the design
    # note carried (it costed WindowSync at 5 bytes and forgot the argFlag byte every opcode >= 0x10
    # with operands carries -- eb/opcodes.encode:57-58).
    sync_only = JF.talk_body({p.key: 700 + i for i, p in enumerate(JF.PAGES)}, 699,
                             pages=tuple(JF.Page(p.key, p.title, p.menu, p.lines) for p in JF.PAGES))
    assert len(OPC.window_sync(1, 0, 700)) == 6
    assert len(body) - len(sync_only) == 32 - 6 == 26
    used, budget = JF.eb_budget()
    assert used == len(body) and used < budget // 4


def test_retuning_POLLED_PAGE_FLAGS_to_a_BUBBLE_FAILS_the_gate(monkeypatch):
    """BREAK IT TO PROVE IT -- the lint arm that guards the constant itself. 128 looks like the
    right "field dialogue" number and it is WindowStyleAuto, i.e. arm B's predicate. The page would
    build, open, and hold with turbo OFF; only a latched F9 would show it."""
    assert JF.lint_pages(check_live_install=False) == []
    monkeypatch.setattr(JF, "POLLED_PAGE_FLAGS", 128)
    bad = JF.lint_pages(check_live_install=False)
    assert any("arm B's predicate" in m for m in bad), bad
    # ...and it does NOT fire when no page is polled (nothing arms the injector)
    plain = tuple(JF.Page(p.key, p.title, p.menu, p.lines) for p in JF.PAGES)
    assert JF.lint_pages(pages=plain, check_live_install=False) == []


@pytest.mark.skipif(not os.path.isfile(_BENCH), reason="the T1b bench toml is not in this checkout")
@pytest.mark.skipif(not os.path.isfile(_BENCH), reason="the T1b bench toml is not in this checkout")
def test_the_bench_declares_the_polled_page_and_ONLY_it():
    """The three keys are ONE decision (polled + a poll-safe style + the two hold/turbo tags), so
    they are asserted together; and the control pages must carry NONE of them or the A/B is not an
    A/B."""
    import tomllib
    d = tomllib.loads(io.open(_BENCH, encoding="utf-8").read())
    opts = d["choice"][0]["options"]
    for p, o in zip(JF.PAGES, opts):
        if p.polled:
            assert o["polled"] is True and o["style"] == "plain"
            assert o["no_focus"] is True and o["no_turbo"] is True
            assert T.resolve_style(o["style"]) == JF.POLLED_PAGE_FLAGS == 0
        else:
            assert not any(k in o for k in ("polled", "style", "no_focus", "no_turbo")), p.key


def _bank(mes: dict, name: str) -> int:
    """The txid the build allocated for ``[[text_table]] name`` -- read off the emitted entries, the
    same way `test_the_BUILT_mes_TAG_BANK_IS_the_txid_the_build_assigned` does."""
    from ff9mapkit.content import texttable as TT
    return {b: t for t, b in mes.items()}[TT.entry_text(JF.TABLES[name])]


@pytest.mark.skipif(not os.path.isfile(_BENCH), reason="the T1b bench toml is not in this checkout")
def test_the_BUILT_mes_gives_the_polled_page_NTUR_and_NFOC_and_nothing_forbidden(built_bench_mes):
    """THE .mes HALF OF THE GATE, on the artifact. The tags are emitted by `dress_window` from the
    option's keys, so nothing in `journalfield` can be asked whether they landed -- only the file
    can. Each forbidden tag breaks the primitive a different way (content/text.POLL_FORBIDDEN_TAGS):
    [IMME] hands the selecting press a finished window, [PAGE] turns CloseWindow into a page turn
    and leaves a live window behind, [WDTH=...] is a DUMMIED tag standing where the real sizing
    mechanism is (SURVEY.md:144), and any [TIME=n>=0] either races the poll or clears the very
    FlagButtonInh the page depends on.

    The forbidden list is READ FROM THE RULEBOOK, not retyped: this assertion used to spell a
    valueless "[WDTH]" -- the same form that made the rulebook's own arm unfirable -- so it passed
    vacuously against an entry that could never have contained one."""
    story = JF.render_page(JF.PAGES[0])[0]
    body = next(b for b in built_bench_mes.values() if story.split("\n", 1)[0] in b)
    assert body == "[NTUR][NFOC]" + re.sub(r"\[TEXT=[^,\]]+,", "[TEXT=%d," % _bank(built_bench_mes,
                                                                                  "th_rank"), story)
    for tag in tuple(T.POLL_FORBIDDEN_TAGS) + ("[TIME=",):
        assert tag not in body, (tag, body[:120])
    # ...and the SIX CONTROL pages keep the owner-confirmed sync shape: auto-[NTUR], never [NFOC]
    for p in JF.PAGES[1:]:
        b = next(x for x in built_bench_mes.values() if JF.render_page(p)[0].split("\n", 1)[0] in x)
        assert b.startswith("[NTUR]") and "[NFOC]" not in b, (p.key, b[:60])


@pytest.mark.skipif(not os.path.isfile(_BENCH), reason="the T1b bench toml is not in this checkout")
def test_the_BUILT_eb_splits_the_window_FLAGS_0_vs_128(built_bench_eb):
    """The A/B has to be real IN THE BYTES, not only in the toml. One WindowAsync at flags 0 (plain
    -- outside arm B) and six WindowSyncs at flags 128 (bubble -- WindowStyleAuto, inside it), each
    on window id 2, plus the selector's own prompt on id 1."""
    from ff9mapkit.eb.model import EbScript
    eb = EbScript.from_bytes(built_bench_eb)
    ins = [i for e in eb.entries if not e.empty for f in e.funcs for i in eb.instrs(f)
           if i.name in ("WindowSync", "WindowAsync")]
    got = [(i.name, i.imm(0), i.imm(1)) for i in ins]
    want = [("WindowSync", 1, 128)]                       # the selector prompt, window 1
    for p in JF.PAGES:
        want.append(("WindowAsync", 2, 0) if p.polled else ("WindowSync", 2, 128))
    assert got[:len(want)] == want, got[:len(want)]
    assert sum(1 for _n, _w, f in want if f == 0) == 1    # exactly one page left the exposed class


@pytest.mark.skipif(not os.path.isfile(_BENCH), reason="the T1b bench toml is not in this checkout")
def test_the_BUILT_eb_closes_the_polled_window_exactly_once(built_bench_eb):
    """An async window nobody closes outlives its arm and sits on top of the re-opened selector.
    The emitter always pairs the open with a close, so this is the artifact proving the pairing
    survived the choice lane -- and the count is exact, because a SECOND close on a dead id is how
    a blind close-sweep would look."""
    from ff9mapkit.eb.model import EbScript
    eb = EbScript.from_bytes(built_bench_eb)
    closes = [i for e in eb.entries if not e.empty for f in e.funcs for i in eb.instrs(f)
              if i.name == "CloseWindow"]
    assert len(closes) == 1 and closes[0].imm(0) == 2


@pytest.mark.skipif(not os.path.isfile(_BENCH), reason="the T1b bench toml is not in this checkout")
def test_the_bench_page_text_survives_the_build_text_pipeline_byte_identical():
    """THE PROPERTY THAT MAKES THE BENCH A VALID WIDTH TEST. A choice `reply` goes through
    `apply_markup` + `wrap_text(wrap)` on the way into the .mes (build.py:7766-7774, :7877). If the
    build re-flowed a page, the playtest would be judging a layout this module never generated --
    and it would look like an in-game wrap when it was a build-time one."""
    import tomllib
    d = tomllib.loads(io.open(_BENCH, encoding="utf-8").read())
    for o in d["choice"][0]["options"]:
        r = o.get("reply")
        if r is None:
            continue
        wrapped, overflow = T.wrap_text(r, T.DEFAULT_WRAP_WIDTH)
        assert overflow == [], (o["text"], overflow)
        assert wrapped == r, o["text"]
        assert T.apply_markup(r) == r, o["text"]
