"""RUNG 0 of the roll-stream arc -- calibrate the instruments before any kit code. One harness launch.

    py tools/play.py studies/roll-stream/rung0_roll.py --label rs-rung0

Bench studies/roll-stream/bench/roll0.field.toml (30890): HUD rows that evaluate the generator's arithmetic as
PURE expressions, and one STOCK wander unit (B_SYSVAR[0]) whose rolled targets live in Global.Int16 blackboard
slots the harness watches bit for bit. It establishes, in-game:

  1. the arithmetic: 237*65536 mod 65537, one advance from 12345, the largest intermediate, the 26-bit WRAP,
     the byte split -- exactly as the offline recurrence computes them;
  2. the slot map: the watched mirror slots (mx/mz) agree with the NPC's live position read through the HUD,
     and the watched target slots (wtx/wtz) hold in-box targets the NPC actually walks to;
  3. the control: two ~Reloads of the stock wander give DIFFERENT target sequences -- so a rung-1 "identical"
     verdict means the seed, not the instrument.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "studies" / "persistent-tables"))
import rung0_persist as R0  # noqa: E402  (the calibrated HUD reader + sentinel)

FIELD = 30890
CX, CZ, R = 0, -1100, 400
SLOTS = {"wtx": 1894, "wtz": 1896, "mx": 1884, "mz": 1886}      # Global.Int16 byte index (dry compile of the bench)
_s = R0.sentinel
ROWS = {"MULREM": _s(5), "STEP": _s(5), "BIG": _s(7), "WRAP": _s(7), "HIBYTE": _s(3), "NPCX": _s(5), "NPCZ": _s(5)}
EXPECT = {"MULREM": 237 * 65536 % 65537, "STEP": 237 * 12345 % 65537, "BIG": 65536 * 237, "WRAP": -(1 << 25),
          "HIBYTE": 65535 // 256}


def _bits(name: str) -> list:
    b = SLOTS[name] * 8
    return list(range(b, b + 16))


def _i16(st, name: str) -> int:
    v = sum(1 << i for i, bit in enumerate(_bits(name)) if st.flag(bit))
    return v - 0x10000 if v & 0x8000 else v


def _targets(g, seconds: float) -> list:
    """The sequence of DISTINCT wander targets seen over ``seconds`` (sampled from the watched Int16s)."""
    seq, deadline = [], time.time() + seconds
    while time.time() < deadline:
        st = g.state
        t = (_i16(st, "wtx"), _i16(st, "wtz"))
        if not seq or seq[-1] != t:
            seq.append(t)
        g.wait_frames(4)
    return seq


def run(g) -> None:
    g.newgame()
    g.watch(*[b for n in SLOTS for b in _bits(n)])
    g.warp(FIELD)
    hud = R0._hud(g, ROWS, want_header="ROLL 0 30890")
    g.shot("1-roll0")
    got = {k: hud.get(k) for k in EXPECT} if hud else None
    g.check(got == EXPECT, "the generator's arithmetic is exact in-game (B_MULT / B_REM / B_DIV, const4 operands)",
            f"{got} vs {EXPECT}")
    g.check(hud is not None and hud["WRAP"] == -(1 << 25),
            "CalcStack overflow WRAPS mod 2^26 (2^25 - 1 + 1 reads back -2^25) -- it does not change class", str(hud))

    # the slot map: the watched mirror equals the NPC's live position read through obj(uid).f[]
    g.wait_frames(20)
    hud = R0._hud(g, ROWS, want_header="ROLL 0 30890")
    st = g.state
    mx, mz = _i16(st, "mx"), _i16(st, "mz")
    g.check(hud is not None and abs((hud["NPCX"] - 10000) - mx) <= 60 and abs((hud["NPCZ"] - 10000) - mz) <= 60,
            "the watched mirror slots (mx/mz) are the strider's live position (the dry-compile slot map holds)",
            f"mirror ({mx}, {mz}) vs HUD ({hud and hud['NPCX'] - 10000}, {hud and hud['NPCZ'] - 10000})")

    first = _targets(g, 16.0)
    print(f"[rs-rung0] reload 1 targets: {first}")
    rolled = [t for t in first if t != (CX, CZ)]
    g.check(len(rolled) >= 5, "the stock wander re-rolled several targets", f"{len(rolled)} targets")
    g.check(all(abs(x - CX) <= R and abs(z - CZ) <= R for x, z in rolled),
            f"every watched target lies in the wander box ({CX}+-{R}, {CZ}+-{R})", str(rolled))
    st = g.state
    last = first[-1]
    g.wait_frames(30)
    st = g.state
    near = ((_i16(st, "mx") - last[0]) ** 2 + (_i16(st, "mz") - last[1]) ** 2) ** 0.5
    g.shot("2-wandering")

    g.warp(FIELD)                                    # ~Reload: the same deferred Warp(fldMapNo) the menu uses
    R0._hud(g, ROWS, want_header="ROLL 0 30890")
    second = _targets(g, 16.0)
    print(f"[rs-rung0] reload 2 targets: {second}")
    a = [t for t in first if t != (CX, CZ)][:5]
    b = [t for t in second if t != (CX, CZ)][:5]
    g.check(len(b) >= 5 and a != b,
            "CONTROL: the STOCK wander rolls a different target sequence after a ~Reload (B_SYSVAR[0] is unseeded) -- "
            "the instrument can tell a seeded stream from an unseeded one", f"{a} vs {b}")
    print(f"[rs-rung0] strider distance to its latest target after 30 frames: {near:.0f}u")
    g.quit()
