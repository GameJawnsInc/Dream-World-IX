"""Tests for the MANAGED-ABI (callback-code) evidence class.

Same convention as R1/R2's tests: everything that can run without the game install and without
Memoria's source does; the rest skips loudly.  The managed-source parser tests run against a small
inline fixture rather than the real file wherever the SHAPE is what is under test, so a Memoria
update cannot quietly turn a parser regression into a skip.

    py -m pytest studies/custom-summons/tier-r/test_callback_ops.py -q
"""
from __future__ import annotations

import os
import sys
import textwrap

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import callback_ops as C         # noqa: E402
import tier_r_annot as A         # noqa: E402

try:
    import refkit                                     # noqa: F401
    have_dll = os.path.isfile(refkit.DLL_X64)
except Exception:                                     # pragma: no cover
    have_dll = False
have_src = os.path.isfile(C.SFX_CS)
have_ops = os.path.isfile(A.HLE_OPS_JSON)

needs_dll = pytest.mark.skipif(not have_dll, reason="needs the installed FF9SpecialEffectPlugin.dll")
needs_src = pytest.mark.skipif(not have_src, reason="needs the Memoria source clone")
needs_ops = pytest.mark.skipif(not have_ops, reason="needs a built hle_ops.json")


# ---------------------------------------------------------------- the managed-source parser
FIXTURE = textwrap.dedent("""\
    public static class SFX
    {
        public static unsafe Int32 BattleCallback(Int32 fullCode, Int32 arg0, Int32 arg1, Int32 arg2, Int32 arg3, void* p)
        {
            Int32 code = fullCode >> 24;
            if (code == 100) // the FAST PATH, not a case
            {
                PSXTextureMgr.LoadImage(arg0, arg1, arg2, arg3, (UInt16*)p);
                return 0;
            }
            switch (code)
            {
                case 125: // Set Sound Pitch
                    SFX.soundFPS = arg0;
                    return 0;
            }
            return BattleCallbackWithBtl(code, arg0, arg1, arg2, arg3, p, fullCode & 255);
        }

        private static unsafe Int32 BattleCallbackWithBtl(Int32 code, Int32 arg0, Int32 arg1, Int32 arg2, Int32 arg3, void* p, Int32 btlid)
        {
            switch (code)
            {
                case 14: // Get Bone Stance
                    switch (arg1)
                    {
                        case 0: // Get Bone Position
                            *(Int16*)p = 1;
                            break;
                        case 2: // Get Bone Orientation & Position
                            break;
                    }
                    break;
                case 22: // Is attached to another enemy
                    return next.bi.slave;
            }
            return 0;
        }

        public enum COMMAND
        {
            COMMAND_GET_MATRIX = 14,
            COMMAND_GET_SLAVE = 22,
            COMMAND_LOAD_IMAGE = 100,
            COMMAND_SET_FPS = 125
        }
    }
    """)


@pytest.fixture()
def fixture_path(tmp_path):
    p = tmp_path / "SFX.cs"
    p.write_text(FIXTURE, encoding="utf-8")
    return str(p)


def test_the_enum_is_parsed_not_transcribed(fixture_path):
    cmds = C.load_commands(fixture_path)
    assert cmds == {14: "GET_MATRIX", 22: "GET_SLAVE", 100: "LOAD_IMAGE", 125: "SET_FPS"}


def test_an_absent_enum_raises_rather_than_returning_a_stale_default(tmp_path):
    p = tmp_path / "empty.cs"
    p.write_text("class X {}", encoding="utf-8")
    with pytest.raises(RuntimeError):
        C.load_commands(str(p))


def test_the_load_image_fast_path_is_a_command_even_though_it_is_not_a_case(fixture_path):
    """`if (code == 100)` sits AHEAD of the switch; a case-only parser reports the round's
    best-attested name as having no managed handler at all."""
    sigs = C.managed_signatures(fixture_path)
    assert 100 in sigs
    assert sigs[100].uses_p and sigs[100].args == {0, 1, 2, 3}


def test_a_case_body_stops_at_the_switch_and_does_not_swallow_the_tail(fixture_path):
    """The regression that invented a `p` use and a return for SET_FPS: the old terminator tested
    a "    }" prefix, which never matches the switch's own 8-space "        }"."""
    sigs = C.managed_signatures(fixture_path)
    assert sigs[125].args == {0}
    assert not sigs[125].uses_p
    assert not sigs[125].returns_value


def test_nested_selector_cases_are_submodes_not_commands(fixture_path):
    sigs = C.managed_signatures(fixture_path)
    assert 0 not in sigs and 2 not in sigs           # not commands
    assert sigs[14].submodes == {0: "Get Bone Position", 2: "Get Bone Orientation & Position"}


def test_a_query_case_is_recorded_as_returning_a_value(fixture_path):
    sigs = C.managed_signatures(fixture_path)
    assert sigs[22].returns_value and not sigs[22].uses_p


def test_neither_callback_body_present_raises(tmp_path):
    p = tmp_path / "other.cs"
    p.write_text("class X { void f() { switch (c) { case 1: break; } } }", encoding="utf-8")
    with pytest.raises(RuntimeError):
        C.managed_signatures(str(p))


# ---------------------------------------------------------------- the cross-check
def test_the_crosscheck_flags_a_pointer_delivery_the_op_cannot_receive():
    sig = A.HandlerSig(op=7, stub=0, args={0: "int"}, ret="void")
    v = C.OpVerdict(op=7, codes={14}, depth=0, name="COMMAND_GET_MATRIX")
    ms = {14: C.ManagedSig(code=14, uses_p=True)}
    assert C.crosscheck(7, v, sig, ms).verdict == "FLAG"


def test_the_crosscheck_accepts_an_out_pointer_delivery():
    sig = A.HandlerSig(op=7, stub=0, args={0: "int", 1: "ptr"}, ret="void")
    v = C.OpVerdict(op=7, codes={14}, depth=0, name="COMMAND_GET_MATRIX")
    ms = {14: C.ManagedSig(code=14, uses_p=True, returns_value=True)}
    assert C.crosscheck(7, v, sig, ms).verdict == "AGREE"


def test_the_crosscheck_flags_a_code_with_no_managed_handler():
    sig = A.HandlerSig(op=7, stub=0, args={}, ret="void")
    v = C.OpVerdict(op=7, codes={99}, depth=0, name="COMMAND_NOPE")
    assert C.crosscheck(7, v, sig, {}).verdict == "FLAG"


# ---------------------------------------------------------------- the DLL lane
@needs_dll
@needs_src
def test_the_a1_calibration_reproduces():
    ok, _lines = C.calibrate()
    assert ok


@needs_dll
@needs_src
def test_every_callback_site_resolves_to_a_command():
    cb = C.CallbackMap()
    assert cb.sites
    assert [s for s in cb.sites if s.code is None] == []


@needs_dll
@needs_src
def test_all_three_encodings_of_the_command_word_are_exercised():
    """`mov`, `or` and `bts` all install the code.  A mov-only scan resolves ~70% of sites and
    silently drops the rest -- including the LoadImage site A1 published."""
    forms = {s.form for s in C.CallbackMap().sites}
    assert {"mov", "or", "bts"} <= forms


@needs_dll
@needs_src
def test_a_movzx_loaded_btlid_does_not_become_a_command_code():
    """`movzx ecx, word ptr [rbx+0x18]` is the btlid; only the OR/BTS that follows is the code.
    If the loaded value leaked through as a code, non-COMMAND bytes would appear."""
    cb = C.CallbackMap()
    assert all(s.code in cb.commands for s in cb.sites)


@needs_dll
@needs_src
@needs_ops
def test_the_two_evidence_lanes_are_disjoint():
    """The round's null result: a noisy method would collide with R2's debug-string names."""
    ops = A.load_hle_ops()
    named = {op for op, v in C.OpNamer().sweep().items() if v.name}
    dbg_high = {op for op, r in ops.items()
                if r.get("confidence") == "high" and C.MANAGED_ABI_MARKER not in r["evidence"]}
    assert not (dbg_high & named)


@needs_dll
@needs_src
def test_no_calibration_op_reaches_the_callback():
    sweep = C.OpNamer().sweep()
    assert [op for op in A.CALIBRATION_OPS if sweep[op].via] == []


@needs_dll
@needs_src
def test_a_multi_command_op_is_refused_rather_than_named():
    """op 128 crosses at four distinct commands; the round publishes it as a refusal."""
    v = C.OpNamer().verdict(128)
    assert len(v.codes) > 1 and v.name is None


@needs_dll
@needs_src
def test_a_submode_is_only_reported_when_every_site_agrees():
    namer = C.OpNamer()
    v = namer.verdict(32)
    assert C._submode_of(namer, v, next(iter(v.codes))) == 0
    mixed = C.OpVerdict(op=999, codes={14}, via=())
    assert C._submode_of(namer, mixed, 14) is None


# ---------------------------------------------------------------- the single-writer tripwire
def test_the_dictionary_has_exactly_one_builder():
    """``r2_gates`` rewrites ``hle_ops.json`` as part of its board.  When it called
    ``build_hle_ops`` directly, running that board silently reverted every callback name to null.
    Both writers must go through ``rebuild_hle_ops``; this pins it so the revert cannot come back."""
    here = os.path.dirname(os.path.abspath(__file__))
    for fname in ("r2_gates.py", "tier_r_annot.py"):
        src = open(os.path.join(here, fname), encoding="utf-8").read()
        writes = "write_hle_ops(" in src.replace("def write_hle_ops(", "")
        if writes:
            assert "rebuild_hle_ops(" in src, "%s writes the dictionary without the canonical builder" % fname


@needs_dll
@needs_src
@needs_ops
def test_the_dictionary_carries_the_round_and_the_contract_holds():
    ops = A.load_hle_ops()
    carried = [op for op, r in ops.items() if r.get("callback_command")]
    assert len(carried) == len({op for op, v in C.OpNamer().sweep().items() if v.name})
    assert A.check_confidence_rule(ops) == []
