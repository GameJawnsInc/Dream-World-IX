"""THE SINE KIT, RUNG 0 -- the bench builder (field 30945, SINE0).

Board entry #7 (studies/eb-uses-board/BOARD.md): motion you COMPUTE, not keyframe. Rung 0 is study-local: the bench
is a plain kit field with two [[prop]]s (bench/sine0.field.toml); after deploy_field this script seats ONE code-entry
DAEMON into every language's live .eb (the seqbrain-bench pattern -- the deploy's own revert script still restores the
field). No kit code changes; rung 1 turns what this proves into `[[prop]] motion`.

THE MECHANISM, engine-read (Memoria Assembly-CSharp):
  B_SIN(v)  = ff9.rsin(v << 4)   B_COS(v) = ff9.rcos(v << 4)     (EBin.cs:1175-1190)  256 units a turn
  B_SIN2(v) = ff9.rsin(v)        B_COS2(v) = ff9.rcos(v)          (EBin.cs:1087-1100) 4096 units a turn
  rsin(a) = (Int32)(Mathf.Sin(a / 4096f * 360f * 0.0174532924f) * 4096f)   single precision, TRUNCATED (ff9.cs:2124)
  B_DIV truncates toward zero (EBin.cs:653-665, C# `/=`); B_CONST sign-extends (Int16 -> Int26, EBin.cs:1235/1682)
  0xAD MoveInstantXZYEx(uid, a, b, c): GetObjUID(uid); pos = (a, -b, c); BGI_charSetActive(0) first -- pathing OFF --
       then SetActorPosition OUTSIDE the null guard (DoEventCode.cs:2179-2245): an absent uid THROWS
  0x87 TurnInstantEx(uid, angle): null-guarded; rotAngle.y = (Int16)(angle << 4) as degrees  -> angle mod 256
       ("0 south, 64 west, 128 north, 192 east", DoEventCode.cs:1192-1213)
  obj(uid).f[0..3] (B_OBJSPECA -> getvobj, EBin.cs:1751-1810): pos[0], -pos[1] (== 0xAD's b operand), pos[2], and
       the facing byte (fixedpoint >> 4) & 255
So a per-tick read of f[0..3] BEFORE the tick's writes is an exact oracle of what the engine held after a full frame.

THE DAEMON (a seated type-0 code entry, one tag-0 loop; armed from the activate block like the gauge daemon):
  gate: poll (Wait 1) until PLAYER BOUND and IsMovementEnabled (B_SYSVAR[2]) and BOTH props READY -- the behavior
        ticker's staged latch plus a per-target ready bit. Run 1 used a bare Wait(45) and THREW at field entry (an
        InvalidCast in getvobj's unguarded f[3] cast, a NullReference in 0xAD) before any of that was true -- a fixed
        warm-up is not a gate. The bits: PBOUND set right after DefinePlayerCharacter (0x2C) in the player's Init,
        READY_A/B right after each prop's CreateObject (0x1D), all three CLEARED first thing in Main_Init (Global bits
        persist across visits); M_GATE counts the ticks spent at the gate, and M_F* record the gate tick each input
        first read true. (Engine-read by the probe review: the kit player's Init yields 48 frames of NOTHING before
        DefinePlayerCharacter, so the player binds at frame ~49; run 1's Wait(45) read obj(250).f[3] at ~46 while
        controlUID still named Main -- a non-actor -- and the unguarded (Actor) cast threw. The props were ready at 1.)
  Wait(SETTLE)
  top:  mirrors: M_T = T (the clock the previous writes used); M_A* / M_B* = obj(A|B).f[0..3];
        M_PR = obj(250).f[3] (the player's facing -- the angle convention, calibrated on the engine's own walk)
        T = T + 1
        0xAD(A, CX + sin(2T)*R/4096, -H, CZ + cos(2T)*R/4096)          0x87(A, 2T + 192)
        0xAD(B, CX + sin(2T+128)*R/4096, -H - sin2(16T)*BOB/4096, CZ + cos(2T+128)*R/4096)   0x87(B, 2T + 320)
        Wait(1); JMP top
  (the tangent: for x = cx + r sin(th), z = cz + r cos(th) with th rising, velocity (cos th, -sin th) == facing
   direction (-sin a, -cos a) at a = th + 192 -- the board said +64)

Usage (repo root):  py studies/sine-kit/sine0_bench.py probe | deploy
30945 is a NEW id -> the FIRST deploy needs a relaunch (a harness launch is one).
Revert: py tools/scroll_out/revert_deploy_30945.py
"""
from __future__ import annotations

import argparse
import math
import struct
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))

from ff9mapkit import eblint                                          # noqa: E402
from ff9mapkit.config import LANGS, ModLayout, find_game_path        # noqa: E402
from ff9mapkit.content import object as _object                      # noqa: E402
from ff9mapkit.eb import EbScript, disasm as D, edit as eb_edit, exprasm, opcodes  # noqa: E402
from ff9mapkit.eb.labelasm import JMP, JMP_IFNOT, asm, label         # noqa: E402
from ff9mapkit.fsutil import atomic_write_bytes                      # noqa: E402

FIELD_ID, FIELD_NAME, MOD_FOLDER = 30945, "SINE0", "FF9CustomMap"
BENCH_TOML = HERE / "bench" / "sine0.field.toml"
MODEL_A, MODEL_B = 226, 241          # balloon, cask (the bench's two [[prop]]s)
CX, CZ, R, H, BOB = 0, -800, 300, 150, 60
SETTLE = 15
PBOUND, READY_A, READY_B = 11440, 11441, 11442      # Global bits (byte 1430) -- the latch inputs
MOVE_EX, TURN_EX = 0xAD, 0x87
# Global Int16 byte offsets (gEventGlobal) -- the safe band (>= byte 1089 = flag 8712), clear of 2032-2047; this
# bench has no [behavior], so nothing else allocates here
T = 1400
M = {"t": 1402, "ax": 1404, "ay": 1406, "az": 1408, "ar": 1410,
     "bx": 1412, "by": 1414, "bz": 1416, "br": 1418,
     "pr": 1420,                     # the PLAYER's facing byte -- calibrates the angle convention on engine data
     "gate": 1422,                   # ticks the daemon spent at the latch before the field was safe
     # raw B_SIN2 at angles where float32 and float64 rsin DISAGREE -- no divide after them to absorb a +-1, so the
     # float32 claim can fail (the positions' *r/4096 hides every rsin difference for t < 771)
     "s1": 1424, "s2": 1426, "s3": 1428,
     # the latch inputs' SCHEDULE: the gate tick at which each first read true (0 = never)
     "fpb": 1432, "fra": 1434, "frb": 1436, "fuc": 1438}
SINE_PROBES = {"s1": 6684, "s2": 10684, "s3": 13892}


# ------------------------------------------------------------------- the predictor (the engine's arithmetic)
_F4096, _F360, _DEG2RAD = np.float32(4096.0), np.float32(360.0), np.float32(0.0174532924)


def _rtrig(fn, a: int) -> int:
    """ff9.rsin / rcos exactly: single-precision steps, Mathf.Sin = (float)Math.Sin(float), (Int32) truncation."""
    deg = np.float32(np.float32(a) / _F4096) * _F360
    rad = np.float32(np.float32(deg) * _DEG2RAD)
    s = np.float32(fn(float(rad)))
    return int(np.float32(s * _F4096))          # int() truncates toward zero, like the (Int32) cast


def rsin(a: int) -> int:
    return _rtrig(math.sin, a)


def rcos(a: int) -> int:
    return _rtrig(math.cos, a)


def cdiv(a: int, b: int) -> int:
    """C# integer division: truncate toward zero."""
    q = abs(a) // abs(b)
    return q if (a >= 0) == (b >= 0) else -q


def b_sin(v: int) -> int:
    return rsin(v << 4)


def b_cos(v: int) -> int:
    return rcos(v << 4)


def predict(t: int) -> dict:
    """The pose the daemon writes with clock value ``t`` (what the NEXT tick's mirrors read back)."""
    return {
        "ax": CX + cdiv(b_sin(2 * t) * R, 4096), "ay": -H, "az": CZ + cdiv(b_cos(2 * t) * R, 4096),
        "ar": (2 * t + 192) & 255,
        "bx": CX + cdiv(b_sin(2 * t + 128) * R, 4096),
        "by": -H - cdiv(rsin(16 * t) * BOB, 4096),
        "bz": CZ + cdiv(b_cos(2 * t + 128) * R, 4096),
        "br": (2 * t + 320) & 255,
    }


# ------------------------------------------------------------------- the daemon
def _stmt(text: str) -> bytes:
    return opcodes.encode(0x05, exprasm.assemble(text + " B_EXPR_END"), arg_flags=0b1)


def _x(e: str) -> bytes:
    return exprasm.assemble(e + " B_EXPR_END")


def _g(off: int) -> str:
    return f"Global.Int16[{off}]"


def _bit(i: int, v: int) -> bytes:
    return _stmt(f"Global.Bit[{i}] const({v}) B_LET")


def daemon_body(a_uid: int, b_uid: int) -> bytes:
    t = _g(T)
    firsts = (("fpb", f"Global.Bit[{PBOUND}]"), ("fra", f"Global.Bit[{READY_A}]"),
              ("frb", f"Global.Bit[{READY_B}]"), ("fuc", "B_SYSVAR[2] const(0) B_NE"))
    B: list = [_stmt(f"{_g(M['gate'])} const(0) B_LET"), _stmt(f"{t} const(0) B_LET")]
    B += [_stmt(f"{_g(M[k])} const(0) B_LET") for k, _src in firsts]
    B.append(label("gate"))
    # first-true ticks, branch-free: F = F + (F == 0) * input * (gate + 1)
    B += [_stmt(f"{_g(M[k])} {_g(M[k])} {_g(M[k])} const(0) B_EQ {src} B_MULT {_g(M['gate'])} const(1) B_PLUS "
                f"B_MULT B_PLUS B_LET") for k, src in firsts]
    B += [
          _stmt(f"Global.Bit[{PBOUND}] B_SYSVAR[2] B_ANDAND Global.Bit[{READY_A}] B_ANDAND "
                f"Global.Bit[{READY_B}] B_ANDAND"),
          (JMP_IFNOT, "hold"),
          (JMP, "go"),
          label("hold"),
          _stmt(f"{_g(M['gate'])} {_g(M['gate'])} const(1) B_PLUS B_LET"),
          opcodes.wait(1),
          (JMP, "gate"),
          label("go"),
          opcodes.wait(SETTLE), label("top"), _stmt(f"{_g(M['t'])} {t} B_LET")]
    B += [_stmt(f"{_g(M[k])} const({a}) B_SIN2 B_LET") for k, a in SINE_PROBES.items()]
    for who, uid in (("a", a_uid), ("b", b_uid)):
        for k, f in (("x", 0), ("y", 1), ("z", 2), ("r", 3)):
            B.append(_stmt(f"{_g(M[who + k])} obj(uid={uid}).f[{f}] B_LET"))
    B.append(_stmt(f"{_g(M['pr'])} obj(uid=250).f[3] B_LET"))     # after the warm-up the player exists
    B.append(_stmt(f"{t} {t} const(1) B_PLUS B_LET"))
    ang_a = f"{t} const(2) B_MULT"
    ang_b = f"{t} const(2) B_MULT const(128) B_PLUS"
    B.append(opcodes.encode(MOVE_EX, a_uid,
                            _x(f"const({CX}) {ang_a} B_SIN const({R}) B_MULT const(4096) B_DIV B_PLUS"),
                            _x(f"const({-H})"),
                            _x(f"const({CZ}) {ang_a} B_COS const({R}) B_MULT const(4096) B_DIV B_PLUS"),
                            arg_flags=0b1110))
    B.append(opcodes.encode(TURN_EX, a_uid, _x(f"{ang_a} const(192) B_PLUS"), arg_flags=0b10))
    B.append(opcodes.encode(MOVE_EX, b_uid,
                            _x(f"const({CX}) {ang_b} B_SIN const({R}) B_MULT const(4096) B_DIV B_PLUS"),
                            _x(f"const({-H}) {t} const(16) B_MULT B_SIN2 const({BOB}) B_MULT const(4096) B_DIV "
                               f"B_MINUS"),
                            _x(f"const({CZ}) {ang_b} B_COS const({R}) B_MULT const(4096) B_DIV B_PLUS"),
                            arg_flags=0b1110))
    B.append(opcodes.encode(TURN_EX, b_uid, _x(f"{ang_b} const(192) B_PLUS"), arg_flags=0b10))
    B += [opcodes.wait(1), (JMP, "top"), opcodes.RETURN]
    return asm(B)


def entry_bytes(a_uid: int, b_uid: int) -> bytes:
    """A seated code entry: type 0, ONE tag-0 function at fpos 4 (the gauge-daemon shape)."""
    return bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + daemon_body(a_uid, b_uid)


def prop_uids(eb: bytes) -> tuple:
    """(uid of A, uid of B) -- the entries whose Init sets MODEL_A / MODEL_B. A kit prop's uid IS its entry slot."""
    s = EbScript.from_bytes(eb)
    found = {}
    for e in s.entries:
        if e.size <= 0 or not e.funcs:
            continue
        f0 = e.funcs[0]
        for i in D.iter_code(eb, f0.abs_start, f0.abs_end):
            if i.op == 0x2F:                                  # SetModel(model, ...)
                found.setdefault(struct.unpack_from("<H", eb, i.off + 2)[0], []).append(e.index)
    a, b = found.get(MODEL_A, []), found.get(MODEL_B, [])
    if len(a) != 1 or len(b) != 1:
        raise SystemExit(f"expected ONE balloon ({MODEL_A}) and ONE cask ({MODEL_B}) prop, found {a} / {b}")
    return a[0], b[0]


def _after_op(eb: bytes, entry: int, op: int) -> int:
    """The body offset right AFTER the one ``op`` in entry ``entry``'s tag-0 Init (the blessed insert point)."""
    f0 = EbScript.from_bytes(eb).entries[entry].funcs[0]
    hits = [i for i in D.iter_code(eb, f0.abs_start, f0.abs_end) if i.op == op]
    if len(hits) != 1:
        raise SystemExit(f"entry {entry}: expected exactly one 0x{op:02X} in its Init, found {len(hits)}")
    return hits[0].end - f0.abs_start


def player_entry(eb: bytes) -> int:
    s = EbScript.from_bytes(eb)
    hits = [e.index for e in s.entries if e.size > 0 and e.funcs
            and any(i.op == 0x2C for i in D.iter_code(eb, e.funcs[0].abs_start, e.funcs[0].abs_end))]
    if len(hits) != 1:
        raise SystemExit(f"expected ONE DefinePlayerCharacter entry, found {hits}")
    return hits[0]


def patch_eb(eb0: bytes) -> tuple:
    """Seat + arm the daemon behind its latch. Returns (bytes, daemon slot, (a_uid, b_uid))."""
    a_uid, b_uid = prop_uids(eb0)
    pl = player_entry(eb0)
    baseline = {str(p) for p in eblint.lint_eb(eb0)}
    out = eb_edit.insert_in_function(eb0, pl, 0, _after_op(eb0, pl, 0x2C), _bit(PBOUND, 1))
    out = eb_edit.insert_in_function(out, a_uid, 0, _after_op(out, a_uid, 0x1D), _bit(READY_A, 1))
    out = eb_edit.insert_in_function(out, b_uid, 0, _after_op(out, b_uid, 0x1D), _bit(READY_B, 1))
    out, slot = _object.seat_entry(out, entry_bytes(a_uid, b_uid))
    out = eb_edit.activate_block(out, _bit(PBOUND, 0) + _bit(READY_A, 0) + _bit(READY_B, 0)
                                 + opcodes.init_code(slot, 0))
    fresh = [p for p in eblint.lint_eb(out)
             if getattr(p, "severity", "error") == "error" and str(p) not in baseline]
    if fresh:
        raise SystemExit("patch produced NEW lint errors:\n  " + "\n  ".join(map(str, fresh)))
    return out, slot, (a_uid, b_uid)


def is_patched(eb: bytes) -> bool:
    try:
        a, b = prop_uids(eb)
    except SystemExit:
        return False
    return daemon_body(a, b) in eb


# ------------------------------------------------------------------- verbs
def probe() -> None:
    """Offline: the predictor against a float64 reference, and the daemon decoded back."""
    worst = max(abs(rsin(a) - 4096 * math.sin(a * 2 * math.pi / 4096)) for a in range(4096))
    print(f"rsin predictor vs float64 sin*4096: worst |diff| {worst:.3f} over one turn (truncation < 1 expected)")
    for t in (0, 1, 32, 64, 96, 127, 128):
        print(f"  t={t:3d}  {predict(t)}")
    body = daemon_body(2, 3)
    ops = [(hex(i.op), i.end - i.off) for i in D.iter_code(body, 0, len(body))]
    print(f"daemon: {len(body)}B, {len(ops)} ops")
    for i in D.iter_code(body, 0, len(body)):
        if i.op == 0x05:                                   # SET: the expression follows the opcode byte
            print("   SET", D.pretty_expr(body, i.off + 1)[0][:150])
        elif i.op in (MOVE_EX, TURN_EX):                   # op, arg-flag byte, the uid byte, then the operands
            off, parts = i.off + 3, []
            while off < i.end:
                txt, off = D.pretty_expr(body, off)
                parts.append(txt)
            print(f"   {'MoveInstantXZYEx' if i.op == MOVE_EX else 'TurnInstantEx'}(uid={body[i.off + 2]},",
                  " | ".join(parts), ")")


def deploy() -> None:
    r = subprocess.run([sys.executable, str(REPO / "tools" / "deploy_field.py"), str(BENCH_TOML),
                        "--id", str(FIELD_ID), "--name", FIELD_NAME, "--text-block", str(FIELD_ID),
                        "--mod-folder", MOD_FOLDER])
    if r.returncode != 0:
        raise SystemExit("deploy_field failed")
    live = ModLayout(find_game_path() / MOD_FOLDER)
    n = 0
    for lang in LANGS:
        p = live.eb_path(lang, f"EVT_{FIELD_NAME}.eb.bytes")
        if p.exists():
            out, slot, uids = patch_eb(p.read_bytes())
            atomic_write_bytes(p, out)
            n += 1
    if not n:
        raise SystemExit(f"no live EVT_{FIELD_NAME}.eb.bytes found to patch")
    print(f"patched {n} language .eb file(s): daemon at slot {slot}, props A/B uids {uids}")
    print(f"  Revert: py tools/scroll_out/revert_deploy_{FIELD_ID}.py")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("verb", choices=["probe", "deploy"])
    {"probe": probe, "deploy": deploy}[ap.parse_args().verb]()
