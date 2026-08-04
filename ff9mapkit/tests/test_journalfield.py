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

import pytest

from ff9mapkit import journal as J
from ff9mapkit import journalfield as JF
from ff9mapkit.content import region as R, text as T
from ff9mapkit.eb import disasm as D, exprasm as EA, exprsem as ES, opcodes as OPC
from ff9mapkit.eb.opcodes import EXPR_VALUE_MAX, EXPR_VALUE_MIN

BANKS = {"th_rank": 600, "hunt": 601}


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
    kline = next(ln for ln in outs[0].split("\n") if ln.startswith("Key items"))
    assert kline.endswith(f"[NUMB=1]/{J.KEY_ITEM_EB_COUNT}"), kline


def test_every_catalog_row_is_placed_exactly_once():
    """Nothing is silently dropped and nothing is invented: the 48 rows and the 48 lines are the
    same set. A row with no in-game read still gets a labelled '--' / 'n/a' line."""
    placed = [ln.row for p in JF.PAGES for ln in p.lines]
    assert len(placed) == len(set(placed)) == len(J.ROWS)
    assert set(placed) == {s.id for s in J.ROWS}


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
    text, _exprs = JF.render_page(probe, BANKS)
    header = text.split("\n")[0]
    assert header.startswith("[IMME]== T ="), header          # the rule GREW past the bare "== T "
    assert T.measure(header) > JF._worst_case_width(probe.lines[0], BANKS)


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
    text, exprs = JF.render_page(JF.PAGES[1], BANKS)     # chocobo
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
    import re
    for p in JF.PAGES:
        text, _e = JF.render_page(p, BANKS)
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
    text, _ = JF.render_page(next(p for p in JF.PAGES if p.key == "cards"), BANKS)
    lines = {ln.split("[")[0].strip(): ln for ln in text.split("\n")}
    assert J.row_spec("minigame.collector_points").run_mode
    assert "/" not in lines["Coll. points"] and "/" not in lines["Coll. level"]
    assert "/100" in lines["Card kinds"]                  # ...but a plain engine max IS baked


def test_the_two_TBLE_banks_come_from_the_catalog_not_a_copy():
    assert JF.TABLES["th_rank"] == J.TH_RANKS
    assert JF.table_texts()["th_rank"].startswith("[TBLE]")
    assert JF.table_texts()["hunt"].split("\n")[2:3] == ["Vivi"]   # byte 313 == 2, EMinigame.cs:302


def test_the_bank_is_substituted_never_authored():
    """collect_text assigns txids by POSITION (build.py:7795-7834), so a hand-written [TEXT=600,2]
    bakes a txid that moves the moment a line is added above it. Every renderer takes the banks in."""
    text, _ = JF.render_page(JF.PAGES[0], {"th_rank": 4242, "hunt": 1})
    assert "[TEXT=4242,2]" in text
    with pytest.raises(KeyError):
        JF.render_page(JF.PAGES[0], {})


# ---- the emitted .eb ---------------------------------------------------------------------------
def test_a_page_publishes_every_value_BEFORE_the_window_opens():
    """Order is load-bearing: `Dialog.AutomaticSize` bakes the width over the values present at
    open, and never re-sizes afterwards."""
    p = next(p for p in JF.PAGES if p.key == "mognet")
    _text, exprs = JF.render_page(p, BANKS)
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
    _t, exprs = JF.render_page(p, BANKS)
    body = JF.page_body(exprs, 700, table_slots=JF.table_slots_of(p))
    ins = list(D.iter_code(body, 0, len(body)))
    clamped = EA.assemble(hud_row_index_clamp(exprs[2]) + " B_EXPR_END")
    assert clamped in body
    assert EA.assemble(exprs[2] + " B_EXPR_END") not in body   # the UNCLAMPED form is not emitted
    assert JF.pretty_listing(body)[2].count("B_MULT") == 1   # the clamp, and only the clamp


def test_every_table_slot_on_every_page_is_clamped():
    for p in JF.PAGES:
        from ff9mapkit.content.behavior import hud_row_index_clamp
        _t, exprs = JF.render_page(p, BANKS)
        body = JF.page_body(exprs, 700, table_slots=JF.table_slots_of(p))
        for slot in JF.table_slots_of(p):
            assert EA.assemble(hud_row_index_clamp(exprs[slot]) + " B_EXPR_END") in body


def test_the_talk_handler_uses_SWITCH_dispatch_never_per_arm_if_blocks():
    """Every arm opens a window and a window overwrites sysvar 9, so `choice.branch`'s per-arm
    re-read of GetChoose() would test the PAGE window's answer (content/choice.py:283-300).
    ⚠ build.py:6097 selects switch dispatch only for input/qte rows, so the generator must ask."""
    body = JF.talk_body({p.key: 700 + i for i, p in enumerate(JF.PAGES)}, 699, BANKS)
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
    body = JF.talk_body({p.key: 700 + i for i, p in enumerate(JF.PAGES)}, 699, BANKS)
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
    body = JF.talk_body({p.key: 700 + i for i, p in enumerate(JF.PAGES)}, 699, BANKS)
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
    assert used == len(JF.talk_body({p.key: 700 + i for i, p in enumerate(JF.PAGES)}, 699, BANKS))
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
    text, exprs = JF.render_page(JF.PAGES[-1], BANKS)
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
        text, _e = JF.render_page(p, BANKS)
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
    rows = [s.id for s in J.ROWS if s.eb_absent][:14]     # rows that legitimately render "n/a"
    probe = _page(*[JF.Line(r, "L", "na") for r in rows])
    bad = JF.lint_pages(pages=_all_but(set(rows)) + probe,
                        check_live_install=False)
    assert any("rendered lines >" in m for m in bad), bad


def test_a_too_wide_value_line_FAILS_the_gate():
    """THE RULE THAT DOES THE WORK on width. `render_page` grows the header past every value line BY
    CONSTRUCTION, so "header is widest" can never fail on page data -- but a value line wide enough
    to push that grown header past the 28.0 wrap makes the HEADER re-flow onto two lines at build.
    That is the failure this catches, and it is what bounds LINE_BUDGET."""
    probe = _page(JF.Line("meta.bestiary", "A label far too long to fit a window", "na"))
    bad = JF.lint_pages(pages=_all_but({"meta.bestiary"}) + probe,
                        check_live_install=False)
    assert any("units >" in m for m in bad), bad
    assert any("re-flow it onto two lines" in m for m in bad), bad


def test_a_DROPPED_row_FAILS_the_gate():
    assert any("on NO page" in m
               for m in JF.lint_pages(pages=_all_but({"party.gil"}),
                                      check_live_install=False))


def test_a_row_placed_TWICE_fails_the_gate():
    probe = _page(JF.Line("party.gil", "Gil", "num"))
    assert any("placed on 2 pages" in m
               for m in JF.lint_pages(pages=JF.PAGES + probe,
                                      check_live_install=False))


def test_rendering_a_number_for_an_eb_absent_row_FAILS_the_gate():
    probe = _page(JF.Line("party.thefts", "Steals", "num"))
    assert any("declares eb_absent" in m
               for m in JF.lint_pages(pages=_all_but({"party.thefts"}) + probe,
                                      check_live_install=False))


def test_rendering_a_number_for_a_DEAD_row_FAILS_the_gate():
    """meta.step_count HAS an .eb read (B_SYSVAR[7]) and the game never moves the counter. The page
    must render 'n/a', never 0 -- `eb` and `status` are orthogonal facts."""
    assert J.row_spec("meta.step_count").eb == "B_SYSVAR[7]"
    assert J.row_spec("meta.step_count").status == "dead"
    probe = _page(JF.Line("meta.step_count", "Steps", "num"))
    assert any("must render" in m
               for m in JF.lint_pages(pages=_all_but({"meta.step_count"}) + probe, check_live_install=False))


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
    text, _e = JF.render_page(next(p for p in JF.PAGES if p.key == "party"), BANKS)
    assert f"/{len(ids)}" in text


def test_a_bad_page_local_expression_FAILS_the_gate():
    probe = _page(JF.Line("meta.bestiary", "Q", "num", extra=("Global.Byte[1] B_PLUS",),
                          extra_source="EBin.cs:1866"))
    bad = JF.lint_pages(pages=_all_but({"meta.bestiary"}) + probe,
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
        assert o["reply"] == JF._bench_page_text(p)
        assert "[TEXT=" not in o["reply"]                   # the bank is a build-assigned txid
        assert not o["reply"].endswith(chr(10))            # a trailing blank line costs a window row


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
        _t, exprs = JF.render_page(p, BANKS)
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


@pytest.mark.skipif(not os.path.isfile(_BENCH), reason="the T1b bench toml is not in this checkout")
def test_the_BUILT_eb_carries_every_page_value_write_on_the_right_slot(built_bench_eb):
    """Per page, per slot: the exact `SetTextVariable(slot, <expr>)` blob the catalog expression
    assembles to is PRESENT in the built .eb, exactly once, and the blobs appear in page order and
    then slot order. Byte-exact, so a right-count/wrong-expression wiring fails too."""
    prev = -1
    for p in JF.PAGES:
        for slot, src in enumerate(JF.bench_page_values(p)):
            blob = OPC.set_text_variable_expr(
                slot, EA.assemble(src[len("expr:"):] + " B_EXPR_END"))
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
    Dialog.cs:1560-1591) and never re-sizes, so a publish after the WindowSync would render at a
    width measured over the previous field's numbers. Checked on the built stream: every page's LAST
    value write is followed by a WindowSync before the next page's FIRST value write."""
    from ff9mapkit.eb.model import EbScript
    eb = EbScript.from_bytes(built_bench_eb)
    stream = [i for e in eb.entries if not e.empty for f in e.funcs for i in eb.instrs(f)
              if i.name in ("SetTextVariable", "WindowSync")]
    # the talk handler's shape, in order: [prompt WindowSync] then per page N x 0x66 + 1 x WindowSync
    kinds = [i.name for i in stream]
    want = ["WindowSync"]
    for p in JF.PAGES:
        want += ["SetTextVariable"] * len(JF.bench_page_values(p)) + ["WindowSync"]
    assert kinds[:len(want)] == want, kinds[:len(want)]


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
