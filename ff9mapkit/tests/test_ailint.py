"""Phase-6c-iii tests: the enemy-AI LINTER. Each check is exercised on a hand-built minimal .eb (no install); the
load-bearing SOUNDNESS property -- a shipping scene must lint CLEAN -- is an install-gated sweep."""
from __future__ import annotations

import struct

import pytest

from ff9mapkit.battle import ailint
from ff9mapkit.eb import disasm, opcodes


def _minimal_eb(body: bytes) -> bytes:
    head = bytearray(0x80)
    head[0:2] = b"EV"
    head[3] = 1
    fb = bytes([0, 1]) + struct.pack("<HH", 0, 4) + body
    slot = struct.pack("<HHBBH", 8, len(fb), 0, 0, 0)
    return bytes(head) + slot + fb


def test_terminating_function_is_clean():
    assert ailint.lint_ai(_minimal_eb(opcodes.set_model(1, 2) + opcodes.RETURN)) == []


def test_no_terminator_flagged():
    issues = ailint.lint_ai(_minimal_eb(opcodes.set_model(1, 2)))   # no RET -> runs off the end
    assert any("runs off the end" in i.message for i in issues)


def test_jump_out_of_bounds_flagged():
    body = bytes((0x01,)) + (1000).to_bytes(2, "little") + opcodes.RETURN   # JMP to +1000 -> way past the function
    issues = ailint.lint_ai(_minimal_eb(body))
    assert any("outside the function" in i.message for i in issues)


def test_attack_index_range():
    sz = disasm.argsize(0x38, 0)
    body = bytes((0x38, 0x00)) + (5).to_bytes(sz, "little") + opcodes.RETURN   # Attack(idx=5), argFlag=0 (immediate)
    assert any("Attack index 5" in i.message for i in ailint.lint_ai(_minimal_eb(body), atk_count=3))   # 5 >= 3
    assert ailint.lint_ai(_minimal_eb(body), atk_count=6) == []                # 5 < 6 -> ok
    assert ailint.lint_ai(_minimal_eb(body)) == []                            # no atk_count -> check skipped


def test_backward_jmp_ifnot_flagged():
    # review HIGH fix: the engine reads JMP_IFNOT (0x02) offset UNSIGNED, so a BACKWARD target is a ~64KB forward
    # jump (crash). A signed decode hid it (target landed in-bounds); the unsigned decode now flags it.
    body = bytes((0, 0, 0, 0x02)) + (0xFFFA).to_bytes(2, "little") + opcodes.RETURN   # 3 NOPs, JMP_IFNOT(-6), RET
    assert any("outside the function" in i.message for i in ailint.lint_ai(_minimal_eb(body)))


def test_function_ending_in_high_terminator_is_clean():
    # review fix: GameOver (0xF5) / Battle / WorldMap / ... end dispatch via the engine's adFin() just like RET, so
    # a branch ending in one (no trailing RET) must NOT be false-flagged as running off the end
    assert ailint.lint_ai(_minimal_eb(opcodes.set_model(1, 2) + bytes((0xF5,)))) == []


def test_malformed_eb_flagged_not_crash():
    issues = ailint.lint_ai(b"not a real eb at all")
    assert issues and any("malformed" in i.message for i in issues)           # a clean issue, never a crash


def test_issue_str():
    i = ailint.AiIssue("error", "entry1/tag6", "boom")
    assert str(i) == "[error] entry1/tag6: boom"


def test_real_scenes_lint_clean():
    # SOUNDNESS: shipping AI must lint clean (0 issues) -- the linter never false-flags valid bytecode. A sample
    # here; the full 562-scene sweep is run out-of-band (see the build/commit notes).
    try:
        from ff9mapkit.battle import extract, scene_data
        scenes = extract.list_battle_scenes()
    except Exception:                                       # noqa: BLE001 -- no install / no UnityPy -> skip
        pytest.skip("needs the FF9 install + UnityPy")
    sample = scenes[:: max(1, len(scenes) // 24)][:24]
    bad = []
    for s in sample:
        assets = extract.read_scene_assets(s)
        eb = assets.get("eb", {}).get("us") or next((b for b in assets.get("eb", {}).values() if b), None)
        if not eb:
            continue
        atk = None
        try:
            atk = scene_data.parse_counts(assets["raw16"])[2] if assets.get("raw16") else None
        except Exception:                                   # noqa: BLE001
            atk = None
        issues = ailint.lint_ai(eb, atk_count=atk)
        if issues:
            bad.append((s, str(issues[0])))
    assert not bad, f"shipping scenes flagged (linter false positive): {bad[:5]}"
