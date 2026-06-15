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
