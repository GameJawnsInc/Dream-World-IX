"""Phase-3: the field event-script (.eb) structural linter (eblint.py).

Pure synthetic tests (hand-built minimal .eb, no install) prove each check FIRES on a real fault and PASSES
clean code; the install-gated sweep proves SOUNDNESS -- every shipping field lints with zero errors (the
ailint-style proof). ``clean`` == zero errors; the dangling-call check is a warning by design (25 real fields
trip it), so soundness is asserted on errors only.
"""
from __future__ import annotations

import struct

import pytest

from ff9mapkit import eblint


def _eb(body: bytes) -> bytes:
    """A valid 1-entry / 1-func (tag 0) .eb wrapping ``body`` as Main_Init's bytecode."""
    head = bytearray(0x80)
    head[0:2] = b"EV"
    head[3] = 1                                          # entryCount
    funcbody = bytes([0, 1]) + struct.pack("<HH", 0, 4) + body   # type=0, fc=1, (tag=0, fpos=4), then code
    slot = struct.pack("<HHBBH", 8, len(funcbody), 0, 0, 0)      # off=8 (body @0x88)
    return bytes(head) + slot + funcbody


def _eb2(body0: bytes, body1: bytes, etype1: int = 0) -> bytes:
    """A 2-entry .eb: entry0 (Main) + entry1, each a single tag-0 function wrapping its body."""
    head = bytearray(0x80)
    head[0:2] = b"EV"
    head[3] = 2                                          # entryCount
    def _entry(body, et=0):
        return bytes([et, 1]) + struct.pack("<HH", 0, 4) + body   # type, fc=1, (tag=0, fpos=4), code
    e0, e1 = _entry(body0), _entry(body1, etype1)
    off0 = 16                                            # 2 slots * 8 bytes = the table; first body right after
    off1 = off0 + len(e0)
    slot0 = struct.pack("<HHBBH", off0, len(e0), 0, 0, 0)
    slot1 = struct.pack("<HHBBH", off1, len(e1), 0, 0, 0)
    return bytes(head) + slot0 + slot1 + e0 + e1


def _errs(eb_bytes):
    return eblint.errors(eblint.lint_eb(eb_bytes))


def test_clean_function_no_issues():
    assert eblint.lint_eb(_eb(bytes([0x04]))) == []          # a bare RET -> structurally clean


def test_malformed_eb_is_an_error():
    iss = eblint.lint_eb(b"xx")                                # bad magic
    assert len(iss) == 1 and iss[0].severity == "error"


def test_fall_off_end_without_terminator():
    """A path that reaches the function end with no terminator -> the engine runs the IP into adjacent bytecode."""
    errs = _errs(_eb(bytes([0x00])))                          # a lone NOP, no RET
    assert any("runs off the end" in e.message for e in errs)


def test_jump_out_of_bounds():
    errs = _errs(_eb(bytes([0x01, 0xE8, 0x03, 0x04])))        # JMP +1000 (far past the func) then RET
    assert any("instruction boundary" in e.message and "1145" in e.message for e in errs)


def test_switch_case_target_out_of_bounds():
    # 0x0B: count=1, base=0, default reloff=7 (-> the RET, valid), case0 reloff=1000 (OOB), then RET
    errs = _errs(_eb(bytes([0x0B, 0x01, 0, 0, 7, 0, 0xE8, 0x03, 0x04])))
    assert any("switch" in e.message and "case 0" in e.message and "boundary" in e.message for e in errs)


def test_clean_switch_no_error():
    # both default + the one case point at the RET (a valid in-function boundary) -> no error
    eb = _eb(bytes([0x0B, 0x01, 0, 0, 7, 0, 7, 0, 0x04]))
    assert _errs(eb) == []


def test_dangling_self_runscript_is_a_warning_not_error():
    """RunScript(self, tag=99) where this entry has no tag 99 -> a warning (dangling call), never an error."""
    eb = _eb(bytes([0x12, 0x00, 0x00, 0xFF, 0x63, 0x04]))     # RunScript(level=0, uid=255=self, tag=99) ; RET
    iss = eblint.lint_eb(eb)
    assert _errs(eb) == []                                    # never an error
    assert any(w.severity == "warning" and "dangling" in w.message for w in iss)


def test_malformed_bytecode_overrun_is_a_clean_error_not_a_crash():
    """A valid-header .eb whose bytecode overruns the buffer (the linter's whole purpose -- vetting corrupt /
    mid-edit forks) must return a decode ERROR, not crash. Regression for the unguarded player-entry pre-pass."""
    errs = _errs(_eb(bytes([0xFF])))                          # a lone extended-opcode prefix at EOF
    assert len(errs) == 1 and "decode" in errs[0].message
    assert eblint.lint_eb(None)[0].severity == "error"        # None/empty data -> graceful error, no crash


def test_dangling_object_runscript_is_a_warning():
    """RunScript(uid=1=a sibling object, tag=99) where entry 1 lacks tag 99 -> a dangling-call warning; the
    non-dangling twin (tag the entry defines) is clean."""
    dangling = _eb2(bytes([0x12, 0x00, 0x00, 0x01, 0x63, 0x04]), bytes([0x04]))   # entry0 -> entry1 tag 99; entry1 = RET(tag0)
    iss = eblint.lint_eb(dangling)
    assert _errs(dangling) == []
    assert any(w.severity == "warning" and "entry 1 tag 99" in w.message and "dangling" in w.message for w in iss)
    ok = _eb2(bytes([0x12, 0x00, 0x00, 0x01, 0x00, 0x04]), bytes([0x04]))         # entry0 -> entry1 tag 0 (exists)
    assert not any("dangling" in w.message for w in eblint.lint_eb(ok))


def test_dangling_player_tag_is_a_warning():
    """RunScript(uid=250=player, tag=99) where no player entry defines tag 99 -> a warning."""
    eb = _eb2(bytes([0x12, 0x00, 0x00, 0xFA, 0x63, 0x04]),    # entry0: RunScript(player, tag 99)
              bytes([0x2C, 0x04]))                            # entry1: DefinePlayerCharacter + RET (the player entry)
    iss = eblint.lint_eb(eb)
    assert _errs(eb) == []
    assert any(w.severity == "warning" and "player" in w.message and "99" in w.message for w in iss)


# ---- reachability walk: prove it does real reachability, not a trivial last-instr check ----
def test_unreachable_trailing_nop_is_clean():
    """Dead code after a RET is correctly UNREACHABLE -> clean (proves the walk, not a last-instruction check)."""
    assert _errs(_eb(bytes([0x04, 0x00]))) == []              # RET then a dead NOP


def test_unconditional_jump_follows_target_not_skipped_bytes():
    """A JMP over a NOP to a RET is clean -- the skipped NOP isn't a run-off (the walk follows the target)."""
    assert _errs(_eb(bytes([0x01, 0x01, 0x00, 0x00, 0x04]))) == []   # JMP +1 (skip the NOP) -> RET


def test_conditional_both_arms_explored_and_terminate():
    """A JMP_IF whose taken target AND fall-through both reach a RET is clean (the walk follows both arms)."""
    assert _errs(_eb(bytes([0x03, 0x01, 0x00, 0x00, 0x04]))) == []   # JMP_IF +1, NOP, RET


def test_switch_default_target_out_of_bounds():
    # 0x0B: base=0, default reloff=1000 (OOB), case0 reloff=7 (-> the RET, valid)
    errs = _errs(_eb(bytes([0x0B, 0x01, 0, 0, 0xE8, 0x03, 7, 0, 0x04])))
    assert any("switch" in e.message and "default" in e.message and "boundary" in e.message for e in errs)


def test_switchex_06_form_bounds():
    # 0x06 explicit form: default reloff=4 (-> RET, valid), one case (value=5, reloff=1000 OOB)
    bad = _eb(bytes([0x06, 0x01, 4, 0, 5, 0, 0xE8, 0x03, 0x04]))
    assert any("switch" in e.message and "case 5" in e.message for e in _errs(bad))
    good = _eb(bytes([0x06, 0x01, 4, 0, 5, 0, 4, 0, 0x04]))   # both default + case -> the RET
    assert _errs(good) == []


# ---- soundness: every shipping field lints with ZERO errors (the ailint-style proof) ----
def test_eblint_soundness_sweep_real_fields():
    """A sample of real fields lints with zero ERRORS (the full 676-field / 0-error sweep runs out-of-band)."""
    try:
        from ff9mapkit.extract import EventBundle
        bundle = EventBundle()
    except Exception:                                         # noqa: BLE001 -- no install -> skip
        pytest.skip("no game install for the eblint sweep")
    seen = 0
    for fid in (50, 51, 100, 257, 300, 301, 2803):
        data = bundle.eb_for_id(fid)
        if not data:
            continue
        seen += 1
        errs = eblint.errors(eblint.lint_eb(data))
        assert errs == [], (fid, [str(e) for e in errs[:5]])
    assert seen > 0, "the sample must actually load fields"
