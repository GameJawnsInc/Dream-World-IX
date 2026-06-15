"""Phase 4a: length-changing ADDITIONS to a verbatim fork's .eb (logic_add.py) -- a guarded PREPEND of an
effect (set_flag / give_item / give_gil) into an existing routine via the always-safe rel_off=0 prepend.

Synthetic tests (hand-built minimal .eb) prove each kind prepends correctly (set_flag ungated, the cumulative
kinds once-guarded), guards are disjoint + safe-band, the policy refuses unsafe shapes, and the composed .eb
stays structurally clean (eblint) + byte-round-trips. An install-gated sweep proves it on real field bytecode.
"""
from __future__ import annotations

import struct

import pytest

from ff9mapkit import eblint
from ff9mapkit import flags as _flags
from ff9mapkit import logic_add as LA
from ff9mapkit.eb.model import EbScript
from ff9mapkit.eventscan import _glob_var_token

RET = bytes([0x04])


def _eb(*funcs) -> bytes:
    """A valid 1-entry .eb with the given ``(tag, body)`` functions. fpos is relative to fbase (es+2) and the
    bodies follow the fc-slot func table -- mirrors EbScript's layout (see eb.edit)."""
    fc = len(funcs)
    table, bodies, fpos = b"", b"", fc * 4
    for tag, body in funcs:
        table += struct.pack("<HH", tag, fpos)
        bodies += body
        fpos += len(body)
    entry = bytes([0, fc]) + table + bodies
    head = bytearray(0x80)
    head[0:2] = b"EV"
    head[3] = 1
    return bytes(head) + struct.pack("<HHBBH", 8, len(entry), 0, 0, 0) + entry


def _instrs(out, tag=0):
    eb = EbScript.from_bytes(out)
    f = eb.entry(0).func_by_tag(tag)
    return eb, list(eb.instrs(f))


def _clean(out) -> bool:
    return eblint.errors(eblint.lint_eb(out)) == [] and EbScript.from_bytes(out).to_bytes() == out


def _first_glob(out, tag=0):
    """The index of the first GLOB var token in entry0/tag's function (the guard/flag)."""
    eb, ins = _instrs(out, tag)
    for i in ins:
        if i.op == 0x05:
            tok = _glob_var_token(eb.data, i.off + 1)
            if tok:
                return tok[0]
    return None


# ---- set_flag: idempotent -> ungated prepend ----
def test_set_flag_prepended_ungated():
    out = LA.apply_logic_adds(_eb((0, RET)), [{"kind": "set_flag", "entry": 0, "tag": 0, "flag": 8520, "value": 1}])
    _eb_, ins = _instrs(out)
    assert ins[0].op == 0x05 and not any(i.op == 0x02 for i in ins)     # a set, NO if-guard
    assert _first_glob(out) == 8520 and _clean(out)


# ---- give_item / give_gil: cumulative -> once-guarded ----
def test_give_item_prepended_once_guarded():
    out = LA.apply_logic_adds(_eb((0, RET)), [{"kind": "give_item", "entry": 0, "tag": 0, "item": 236}])
    _eb_, ins = _instrs(out)
    assert any(i.op == 0x02 for i in ins), "cumulative give is wrapped in an if(!guard) jump"
    assert [i.imm(0) for i in ins if i.op == 0x48] == [236]
    assert _first_glob(out) == _flags.FIRST_SAFE_FLAG and _clean(out)    # auto guard from the safe band


def test_give_gil_guarded_and_clean():
    out = LA.apply_logic_adds(_eb((0, RET)), [{"kind": "give_gil", "entry": 0, "tag": 0, "amount": 5000}])
    _eb_, ins = _instrs(out)
    assert any(i.op == 0x02 for i in ins) and any(i.op == 0xCE for i in ins) and _clean(out)


# ---- repeat=true: only on a tag-3 talk handler (else it would fire every frame) ----
def test_repeat_true_only_on_talk_tag():
    with pytest.raises(LA.LogicAddError):
        LA.apply_logic_adds(_eb((0, RET)), [{"kind": "give_item", "entry": 0, "tag": 0, "item": 236, "repeat": True}])
    out = LA.apply_logic_adds(_eb((3, RET)), [{"kind": "give_item", "entry": 0, "tag": 3, "item": 236, "repeat": True}])
    _eb_, ins = _instrs(out, tag=3)
    assert not any(i.op == 0x02 for i in ins) and [i.imm(0) for i in ins if i.op == 0x48] == [236]   # ungated
    assert _clean(out)


# ---- guard allocation: disjoint + avoids authored flags ----
def test_guards_are_disjoint_and_avoid_authored_flags():
    out = LA.apply_logic_adds(_eb((0, RET)), [
        {"kind": "set_flag", "entry": 0, "tag": 0, "flag": _flags.FIRST_SAFE_FLAG},     # claims 8512
        {"kind": "give_item", "entry": 0, "tag": 0, "item": 236},                       # guard must skip 8512
        {"kind": "give_gil", "entry": 0, "tag": 0, "amount": 100}])                      # a third, distinct guard
    eb, ins = _instrs(out)
    guards = sorted({_glob_var_token(eb.data, i.off + 1)[0] for i in ins
                     if i.op == 0x05 and _glob_var_token(eb.data, i.off + 1)})
    assert _flags.FIRST_SAFE_FLAG in guards                                              # the authored set_flag
    give_guards = [g for g in guards if g != _flags.FIRST_SAFE_FLAG]
    assert len(give_guards) == 2 and len(set(give_guards)) == 2                          # two distinct give-guards
    assert all(_flags.is_safe_custom(g) for g in guards) and _clean(out)


def test_explicit_guard_used_and_band_checked():
    out = LA.apply_logic_adds(_eb((0, RET)),
                              [{"kind": "give_item", "entry": 0, "tag": 0, "item": 236, "guard": 8530}])
    assert _first_glob(out) == 8530
    with pytest.raises(LA.LogicAddError):                                                # out of the safe band
        LA.apply_logic_adds(_eb((0, RET)), [{"kind": "give_item", "entry": 0, "tag": 0, "item": 236, "guard": 100}])


# ---- Phase 4b: where="after" (mid-function insert via the keystone rebuild) ----
def test_after_insert_relocates_surrounding_jump():
    """Inserting an effect AFTER an anchor instruction mid-function rebuilds the function via the keystone, so a
    jump that spans the insert point relocates and still hits its target."""
    from ff9mapkit.eb import cmdasm, disasm
    body = cmdasm.assemble_block("SetTriangleFlagMask(1)\nJMP(d)\nSetTriangleFlagMask(2)\nd:\nRET()")
    out = LA.apply_logic_adds(_eb((0, body)), [{"kind": "set_flag", "entry": 0, "tag": 0, "flag": 8520,
                                               "where": "after", "after_op": 0x27, "after_nth": 0}])
    assert _clean(out)
    eb, ins = _instrs(out)
    assert [i.op for i in ins][:2] == [0x27, 0x05]              # the set_flag landed right after the anchor
    jmp = next(i for i in ins if i.op == 0x01)
    ret = [i for i in ins if i.op == 0x04][-1]
    assert disasm.jump_target(jmp) == ret.off                  # the JMP relocated past the inserted bytes


def test_after_insert_guarded_give_lands():
    """A cumulative give inserted mid-function is once-guarded (cond_not + JMP_IFNOT skip + set + AddItem) and
    the composed function stays eblint-clean + byte-round-trips."""
    from ff9mapkit.eb import cmdasm
    body = cmdasm.assemble_block("SetTriangleFlagMask(1)\nSetTriangleFlagMask(2)\nRET()")
    out = LA.apply_logic_adds(_eb((0, body)), [{"kind": "give_item", "entry": 0, "tag": 0, "item": 236,
                                               "where": "after", "after_op": 0x27, "after_nth": 1}])
    assert _clean(out)
    eb, ins = _instrs(out)
    assert any(i.op == 0x48 and i.imm(0) == 236 for i in ins) and any(i.op == 0x02 for i in ins)   # give + guard
    # the give sits after the 2nd anchor (idx 1), not the 1st
    op27 = [k for k, i in enumerate(ins) if i.op == 0x27]
    give = next(k for k, i in enumerate(ins) if i.op == 0x48)
    assert give > op27[1]


def test_after_insert_warns_on_unreachable_anchor():
    """Anchoring on a terminator (RET) OR an unconditional JMP makes the effect dead (control never falls
    through to it) -> an advisory warning."""
    from ff9mapkit.eb import cmdasm
    jmp_body = cmdasm.assemble_block("SetTriangleFlagMask(1)\nJMP(d)\nd:\nRET()")
    warns = []
    LA.apply_logic_adds(_eb((0, jmp_body)), [{"kind": "set_flag", "entry": 0, "tag": 0, "flag": 8520,
                                             "where": "after", "after_op": 0x01, "after_nth": 0}], warnings=warns)
    assert any("unreachable" in w for w in warns)
    warns2 = []
    LA.apply_logic_adds(_eb((0, bytes([0x04]))), [{"kind": "set_flag", "entry": 0, "tag": 0, "flag": 8520,
                                                  "where": "after", "after_op": 0x04, "after_nth": 0}], warnings=warns2)
    assert any("unreachable" in w for w in warns2)


def test_after_insert_bad_anchor_refused():
    body = bytes([0x04])                                       # just RET (op 0x04)
    with pytest.raises(LA.LogicAddError):                      # no AddItem (0x48) to anchor on
        LA.apply_logic_adds(_eb((0, body)), [{"kind": "set_flag", "entry": 0, "tag": 0, "flag": 8520,
                                             "where": "after", "after_op": 0x48, "after_nth": 0}])


WINDOW_SYNC = 0x1F


# ---- show_line / message=: announce an effect via an appended .mes line ----
def test_show_line_emits_guarded_window():
    """show_line opens a WindowSync at the build-allocated txid, once-guarded (a window in a tread zone would
    re-open every frame)."""
    out = LA.apply_logic_adds(_eb((0, RET)), [{"kind": "show_line", "entry": 0, "tag": 0,
                                              "message": "Hi!"}], message_txids={0: 1001})
    _eb_, ins = _instrs(out)
    win = [i for i in ins if i.op == WINDOW_SYNC]
    assert len(win) == 1 and win[0].imm(2) == 1001              # WindowSync -> the appended txid
    assert any(i.op == 0x02 for i in ins) and _clean(out)       # once-guarded


def test_show_line_needs_allocated_txid():
    """A message with no allocated txid is a clean error (the build/Check plan always provides one)."""
    with pytest.raises(LA.LogicAddError):
        LA.apply_logic_adds(_eb((0, RET)), [{"kind": "show_line", "entry": 0, "tag": 0, "message": "Hi!"}])


def test_message_on_give_announces_after_give():
    """give_item + message= gives THEN shows, inside ONE guard (atomic): AddItem before WindowSync."""
    out = LA.apply_logic_adds(_eb((0, RET)), [{"kind": "give_item", "entry": 0, "tag": 0, "item": 236,
                                              "message": "Received a Potion!"}], message_txids={0: 1005})
    _eb_, ins = _instrs(out)
    add_i = next(k for k, i in enumerate(ins) if i.op == 0x48)
    win_i = next(k for k, i in enumerate(ins) if i.op == WINDOW_SYNC)
    assert add_i < win_i                                        # give then announce
    assert sum(i.op == 0x02 for i in ins) == 1 and _clean(out)  # a SINGLE shared once-guard


def test_set_flag_with_message_is_guarded():
    """A bare set_flag is ungated, but set_flag + message= must guard (else the window spams every frame)."""
    plain = LA.apply_logic_adds(_eb((0, RET)), [{"kind": "set_flag", "entry": 0, "tag": 0, "flag": 8520}])
    assert not any(i.op == 0x02 for i in _instrs(plain)[1])
    withmsg = LA.apply_logic_adds(_eb((0, RET)), [{"kind": "set_flag", "entry": 0, "tag": 0, "flag": 8520,
                                                  "message": "The path opens."}], message_txids={0: 1001})
    _eb_, ins = _instrs(withmsg)
    assert any(i.op == 0x02 for i in ins) and any(i.op == WINDOW_SYNC for i in ins) and _clean(withmsg)


def test_plan_messages_indexes_match_apply_order():
    """plan_messages keys by the NORMALIZED add index -- so a txid keyed by it lines up with the add
    apply_logic_adds enumerates (even with a falsy element filtered out)."""
    adds = [None,                                                          # filtered out
            {"kind": "set_flag", "entry": 0, "tag": 0, "flag": 8520},      # no message -> not in the plan
            {"kind": "show_line", "entry": 0, "tag": 0, "message": "A"},   # normalized idx 1
            {"kind": "give_gil", "entry": 0, "tag": 0, "amount": 5, "message": "B"}]  # normalized idx 2
    plan = LA.plan_messages(adds)
    assert [(idx, msg) for idx, msg, _s, _t in plan] == [(1, "A"), (2, "B")]
    # the txids the plan implies apply correctly (the show_line at idx 1, the give at idx 2)
    out = LA.apply_logic_adds(_eb((0, RET)), adds, message_txids={1: 2001, 2: 2002})
    _eb_, ins = _instrs(out)
    assert sorted(i.imm(2) for i in ins if i.op == WINDOW_SYNC) == [2001, 2002] and _clean(out)


def test_show_line_after_insert():
    """show_line works with where="after" -- the WindowSync is spliced mid-function via the keystone."""
    from ff9mapkit.eb import cmdasm
    body = cmdasm.assemble_block("SetTriangleFlagMask(1)\nSetTriangleFlagMask(2)\nRET()")
    out = LA.apply_logic_adds(_eb((0, body)), [{"kind": "show_line", "entry": 0, "tag": 0, "message": "Hi!",
                                               "where": "after", "after_op": 0x27, "after_nth": 0}],
                              message_txids={0: 1001})
    _eb_, ins = _instrs(out)
    assert any(i.op == WINDOW_SYNC and i.imm(2) == 1001 for i in ins) and _clean(out)


def test_show_line_malformed_message_refused():
    base = _eb((0, RET))
    for bad in ({"kind": "show_line", "entry": 0, "tag": 0},                       # missing message
                {"kind": "show_line", "entry": 0, "tag": 0, "message": ""},        # empty
                {"kind": "show_line", "entry": 0, "tag": 0, "message": 5},         # non-string
                {"kind": "give_item", "entry": 0, "tag": 0, "item": 236, "message": ""}):  # bad msg on a give
        with pytest.raises(LA.LogicAddError):
            LA.apply_logic_adds(base, [bad], message_txids={0: 1001})


# ---- guards / refusals ----
def test_refusals():
    base = _eb((0, RET))
    for bad in (
        {"kind": "set_flag", "entry": 0, "tag": 0, "flag": 100},                         # out-of-band flag
        {"kind": "give_item", "entry": 0, "tag": 0, "item": 236, "count": 999},          # count > 255
        {"kind": "give_gil", "entry": 0, "tag": 0, "amount": 0},                          # zero gil
        {"kind": "frobnicate", "entry": 0, "tag": 0},                                     # unknown kind
        {"kind": "give_item", "entry": 9, "tag": 0, "item": 236},                         # no such entry
        {"kind": "give_item", "entry": 0, "tag": 7, "item": 236},                         # no such tag
        {"kind": "give_item", "entry": 0, "tag": 0, "item": "Notanitem"},                 # bad item name
        {"kind": "give_item", "entry": 0, "tag": 0, "item": 236, "where": "mid"}):        # mid = Phase 4b
        with pytest.raises(LA.LogicAddError):
            LA.apply_logic_adds(base, [bad])


def test_auto_guard_avoids_reserved_project_flags():
    """A once-guard must not alias the field's OWN authored flags ([startup]/[[flag]]/...): with 8512 reserved,
    the auto guard skips to the next free safe bit (else the guard pre-fires and the give never happens)."""
    out = LA.apply_logic_adds(_eb((0, RET)), [{"kind": "give_item", "entry": 0, "tag": 0, "item": 236}],
                              reserved_flags={_flags.FIRST_SAFE_FLAG})
    assert _first_glob(out) == _flags.FIRST_SAFE_FLAG + 1 and _clean(out)


def test_auto_guard_confined_to_campaign_window():
    """In a campaign, auto guards stay inside the member's [base, base+window) block (never overflow a sibling)
    and exhaustion raises cleanly."""
    eb = _eb((0, RET))
    two = [{"kind": "give_item", "entry": 0, "tag": 0, "item": 236},
           {"kind": "give_gil", "entry": 0, "tag": 0, "amount": 100}]
    out = LA.apply_logic_adds(eb, two, guard_base=8600, guard_window=2)   # exactly two slots: 8600, 8601
    eb2, ins = _instrs(out)
    guards = {_glob_var_token(eb2.data, i.off + 1)[0] for i in ins if i.op == 0x05 and _glob_var_token(eb2.data, i.off + 1)}
    assert guards == {8600, 8601} and _clean(out)
    with pytest.raises(LA.LogicAddError):                                 # a third exhausts the window
        LA.apply_logic_adds(eb, two + [{"kind": "give_gil", "entry": 0, "tag": 0, "amount": 5}],
                            guard_base=8600, guard_window=2)


def test_explicit_guard_collision_refused():
    eb = _eb((0, RET))
    with pytest.raises(LA.LogicAddError):                                 # two adds, same explicit guard
        LA.apply_logic_adds(eb, [{"kind": "give_item", "entry": 0, "tag": 0, "item": 236, "guard": 8530},
                                 {"kind": "give_gil", "entry": 0, "tag": 0, "amount": 100, "guard": 8530}])
    with pytest.raises(LA.LogicAddError):                                 # explicit guard == an authored set_flag
        LA.apply_logic_adds(eb, [{"kind": "set_flag", "entry": 0, "tag": 0, "flag": 8530},
                                 {"kind": "give_item", "entry": 0, "tag": 0, "item": 236, "guard": 8530}])


def test_malformed_container_or_element_is_clean_error():
    """`[logic_add]` (a single table) / junk -> a clean LogicAddError, not a raw AttributeError at build."""
    eb = _eb((0, RET))
    for bad in ("foo", [1, 2], {"kind": "set_flag", "entry": 0, "tag": 0, "flag": 8512}):
        with pytest.raises(LA.LogicAddError):
            LA.apply_logic_adds(eb, bad)


def test_repeat_true_emits_advisory():
    warns = []
    LA.apply_logic_adds(_eb((3, RET)), [{"kind": "give_item", "entry": 0, "tag": 3, "item": 236, "repeat": True}],
                        warnings=warns)
    assert any("re-fires" in w for w in warns)


def test_empty_is_byte_identical():
    eb = _eb((0, RET))
    assert LA.apply_logic_adds(eb, []) == eb
    assert LA.apply_logic_adds(eb, None) == eb


def test_logic_add_message_plan_sits_above_on_entry():
    """build._logic_add_message_plan allocates each show_line / message= a txid ABOVE the donor `.mes`
    (CARRY_BASE_TXID floor with no donor text) AND above the [[on_entry]] message block, keyed by the
    normalized add index, with the appended lines present in every language's suffix."""
    from ff9mapkit import build, dialogue
    from ff9mapkit.config import LANGS

    class _P:
        def __init__(self, raw):
            self.raw = raw

        def logic_adds(self):
            return self.raw.get("logic_add", [])

    p = _P({"on_entry": [{"message": "a"}, {"message": "b"}],          # 2 on-entry lines -> [1000,1002)
            "logic_add": [{"kind": "show_line", "entry": 0, "tag": 0, "message": "First"},
                          None,                                         # filtered out (index alignment check)
                          {"kind": "give_item", "entry": 0, "tag": 0, "item": 236, "message": "Second"}]})
    txids, suffix = build._logic_add_message_plan(p, LANGS)
    assert txids == {0: 1002, 1: 1003}                                 # above the 2 on-entry lines; idx 1 = the give
    assert set(suffix) == set(LANGS)
    parsed = dialogue.parse_mes(suffix["us"])
    assert set(parsed) == {1002, 1003} and "First" in parsed[1002].text and "Second" in parsed[1003].text
    assert suffix["us"] == suffix[LANGS[-1]]                            # single-block: same text every language

    # a malformed (non-dict) on_entry element is SKIPPED, not crashed-on, by both message planners (validate()
    # is the layer that loudly rejects it) -- _on_entry_message_count and _verbatim_on_entry_messages agree.
    bad = _P({"on_entry": ["junk", {"message": "a"}],
              "logic_add": [{"kind": "show_line", "entry": 0, "tag": 0, "message": "X"}]})
    assert build._on_entry_message_count(bad) == 1                      # the lone dict-with-message
    txids2, _suffix2 = build._logic_add_message_plan(bad, LANGS)
    assert txids2 == {0: 1001}                                          # sits above the 1 on-entry line
    assert build._verbatim_on_entry_messages(bad, LANGS)[0] == {1: 1000}  # non-dict at idx 0 skipped cleanly


def test_dry_run_logic_adds_returns_clean_strings():
    """build.dry_run_logic_adds (the GUI 'Add effect' gate) returns a STRING on any failure (never a raw
    traceback) and None when there's nothing to apply."""
    from ff9mapkit import build

    class _P:
        def __init__(self, raw):
            self.raw = raw

        def logic_adds(self):
            return self.raw.get("logic_add", [])

        def logic_edits(self):
            return self.raw.get("logic_edit", [])

    assert build.dry_run_logic_adds(_P({})) is None                       # no adds -> None
    out = build.dry_run_logic_adds(_P({"logic_add": [{"kind": "set_flag", "entry": 0, "tag": 0, "flag": 8512}]}))
    assert isinstance(out, str) and "VERBATIM" in out                     # adds on a non-verbatim field


def test_validate_flags_logic_add_on_synthesized_field():
    """[[logic_add]] on a non-verbatim field is surfaced as a problem (offline, via validate)."""
    from ff9mapkit import build

    class _P:
        raw = {"logic_add": [{"kind": "set_flag", "entry": 0, "tag": 0, "flag": 8512}]}

        def logic_adds(self):
            return self.raw.get("logic_add", [])

    problems = []
    build._validate_logic_adds(_P(), problems)
    assert any("only applies to a VERBATIM" in p for p in problems)


# ---- real game bytecode: the safe prepend on actual field .eb (install-gated) ----
def test_logic_add_on_real_fields():
    """Each kind, prepended into a real field's Main_Init, stays eblint-clean + byte-round-trips -- proves the
    length-changing prepend on actual bytecode (incl. switch-bearing Main_Inits), not just synthetic."""
    try:
        from ff9mapkit.extract import EventBundle
        bundle = EventBundle()
    except Exception:                                                    # noqa: BLE001
        pytest.skip("no game install")
    ids = [351, 300, 302, 2803, 70]                                      # Dali Inn / Ice Cavern / Daguerreo / opening
    tested = 0
    for fid in ids:
        try:
            data = bundle.eb_for_id(fid)
        except Exception:                                               # noqa: BLE001
            continue
        if not data or EbScript.from_bytes(data).entry(0).func_by_tag(0) is None:
            continue
        for add in ({"kind": "set_flag", "entry": 0, "tag": 0, "flag": 8520},
                    {"kind": "give_item", "entry": 0, "tag": 0, "item": "Potion"},
                    {"kind": "give_gil", "entry": 0, "tag": 0, "amount": 500}):
            out = LA.apply_logic_adds(data, [add])
            assert len(out) > len(data) and _clean(out), f"field {fid} {add['kind']}"
        tested += 1
    if not tested:
        pytest.skip("none of the sample fields were present in this install")
