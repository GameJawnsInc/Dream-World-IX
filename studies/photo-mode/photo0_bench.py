"""PHOTO MODE, RUNG 0 -- the bench builder (field 30955, PHOTO0).

Board entry #8 (studies/eb-uses-board/BOARD.md), reframed as the kit's first CAMERA-PAN PRIMITIVE: a field script
takes the view from the player, pans it where the player's held buttons say, keeps it on the painting, and hands it
back. Rung 0 is study-local: the bench is a plain kit field (bench/photo0.field.toml, a 768x448 canvas); after
deploy_field this script seats ONE code-entry DAEMON into every language's live .eb (the sine-kit pattern -- the
deploy's own revert script still restores the field). No kit code changes.

THE MECHANISM, engine-read (Memoria Assembly-CSharp; the research + judge reports behind studies/photo-mode/PLAN.md):
  0x6F MoveCamera(destX, destY, dur, type)   [2,2,1,1]; every operand may be an expression. Starts from the current
       curVRP, ends in HOLD (flags&7 == 4) where BOTH scroll services return early -- so a MoveCamera already takes
       the camera from the player, and follow never resumes on its own (FieldMap.cs:1461-1484, 1839-1900, 1963).
       Dropped outright when the Active bit is clear (1463). Y is NEVER clamped; X only at issue, only under the
       RUNTIME WidescreenSupport flag, to the narrowed window (1470-1473). dur 0 = NaN / a per-tick throw: never.
  0x70 ReleaseCamera(dur, type)  [1,1]: glide to the player's CLAMPED follow aim (computed once), then follow.
  0x71 EnableCameraServices(active, frames, type): active=0 clears Active -> every later 0x6F is a no-op (the
       board's recipe). Emitted here ONLY as the stage-2 negative control (CMD 5) and its recovery (CMD 6).
  0xEA CalculateScreenOrigin: sSysX/Y = (Int16)(curVRP + co + (HFW, HFH)) -- MoveCamera's own space, read back as
       B_SYSVAR[12]/[13]. 0xA9 CalculateScreenPosition(obj) writes the SAME two registers (copy before calling it).
  B_KEY(mask) = 1 iff the held inputs & mask (EBin.cs B_KEY); B_KEYON the edge (and it arms
       scriptRequestedButtonPress). B_CONST is a signed Int16: masks >= 0x8000 go through const4 (the kit does not
       refuse const(32768) -- it emits 7d 00 80, which the engine reads as -32768).
  0x2D DisableMove: usercontrol 0 (the walk is gated on GetUserControl, except under Field.isDebug).

THE DAEMON (a seated type-0 code entry, one tag-0 loop), one STAGE per in-game run -- each stage is the previous one
plus one block, so a run changes one thing:
  1  mirrors only: every tick copy the engine's view (0xEA) and the player's screen position (0xA9), usercontrol,
     the camera index, the held keys. No camera op anywhere -- the calibration of the instrument.
  2  + a command DISPATCHER the harness drives by poking CMD (MOVE, glide, relative move, release, the 0x71 negative
     control and its recovery, lock/unlock movement).
  3  + the PAN: while MODE is 1 (relative, the stock 507/606 form) or 3 (absolute), the d-pad moves the view STEP px a
     tick, clamped in the script to the 4:3 box.

Usage (repo root):  py studies/photo-mode/photo0_bench.py art | probe [--stage N] | predict | deploy --stage N
30955 is a NEW id -> the FIRST deploy needs a relaunch (a harness launch is one).
Revert: py tools/scroll_out/revert_deploy_30955.py
"""
from __future__ import annotations

import argparse
import json
import math
import re
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

FIELD_ID, FIELD_NAME, MOD_FOLDER = 30955, "PHOTO0", "FF9CustomMap"
BENCH_TOML = HERE / "bench" / "photo0.field.toml"
ART = HERE / "bench" / "art" / "back.png"
PREDICTIONS = HERE / "rung0_predictions.json"
STAGES = (1, 2, 3)
MODEL = 226                          # balloon (the bench's three [[prop]]s)
RANGE = (768, 448)
BOX43 = (160, 608, 112, 336)         # scroll_bounds(RANGE): the vrp window (view-centre limits), what the script clamps to
HFH = 112                            # HalfFieldHeight
STEP = 4                             # pan px per tick
SETTLE = 15
PBOUND, READY_L, READY_C, READY_R = 12416, 12417, 12418, 12419      # Global bits (byte 1552)
# Global byte offsets -- the safe band (>= byte 1089 = flag 8712), clear of 2032-2047 and of the sine kit's 1400-1439
G16 = {"t": 1500, "vx": 1502, "vy": 1504, "psx": 1506, "psy": 1508, "tx": 1510, "ty": 1512, "uc": 1514,
       "cam": 1516, "keys": 1518, "nr": 1520, "nl": 1522, "nd": 1524, "nu": 1526, "ack": 1528, "last": 1530,
       "gate": 1532, "fpb": 1534, "fuc": 1536, "nmc": 1538, "rt": 1540, "flags": 1542, "edges": 1544,
       "txp": 1546, "typ": 1548, "issp": 1550, "ackt": 1554}
WATCHED = tuple(G16)                 # 1500-1555: the published mirrors
CMD, MODE, AD, AT = 1560, 1561, 1566, 1567                          # Global.Byte, harness-poked (CMD last)
AX, AY = 1562, 1564                                                 # Global.Int16, harness-poked (lo, hi)
S16 = {"dx": 1570, "dy": 1572, "iss": 1580, "pmode": 1582}          # scratch, not watched
# B_KEY masks (EventInput.cs:537-562) and the KEYS mirror bit each one sets
KEYS = (("up", 0x10, 1), ("right", 0x20, 2), ("down", 0x40, 4), ("left", 0x80, 8), ("select", 0x1, 16),
        ("cancel", 0x10000, 32), ("r1", 0x200000, 64), ("l1", 0x100000, 128))
KEYMASK = {n: m for n, m, _b in KEYS}
CMDS = {"MOVE1": 1, "MOVEN": 2, "REL": 3, "RELEASE": 4, "SVC_OFF": 5, "SVC_ON": 6, "LOCK": 7, "UNLOCK": 8}


# ------------------------------------------------------------------- the art (a registration target, zero SE bytes)
PALETTE = np.array([(40, 90, 200), (60, 170, 80), (230, 210, 60), (70, 200, 210), (235, 235, 235),
                    (120, 120, 130), (150, 90, 200)], dtype=np.int32)
CELL = 16                            # canvas px per cell
ART_SCALE = 4                        # the kit's layer PNGs are 4x the canvas


def _red(rgb) -> bool:
    r, g, b = (int(v) for v in rgb)
    return r > 140 and r - g > 90 and r - b > 80


def cells() -> np.ndarray:
    """The (28, 48) palette index of every 16-px cell -- seeded, no two 4-neighbours alike."""
    rng = np.random.default_rng(FIELD_ID)
    h, w = RANGE[1] // CELL, RANGE[0] // CELL
    out = np.zeros((h, w), dtype=np.int8)
    for j in range(h):
        for i in range(w):
            banned = {int(out[j, i - 1])} if i else set()
            if j:
                banned.add(int(out[j - 1, i]))
            choice = [k for k in range(len(PALETTE)) if k not in banned]
            out[j, i] = choice[int(rng.integers(len(choice)))]
    return out


def canvas_labels() -> np.ndarray:
    """The (448, 768) palette index of every canvas pixel."""
    return np.kron(cells(), np.ones((CELL, CELL), dtype=np.int8))


def make_art() -> None:
    from PIL import Image
    assert not any(_red(c) for c in PALETTE), "a palette colour passes the red-balloon mask"
    lab = np.kron(cells(), np.ones((CELL * ART_SCALE, CELL * ART_SCALE), dtype=np.int8))
    img = PALETTE[lab].astype(np.uint8)
    ART.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(img, "RGB").save(ART)
    print(f"wrote {ART} {img.shape[1]}x{img.shape[0]}")


# ------------------------------------------------------------------- the frame instruments
PAL_TOL = 60                         # max RGB distance for a sampled pixel to count as a palette colour
PADX, PADY = 64, 160                 # how far off the canvas a view may be searched (the Y negative control leaves it)


def classify(png) -> np.ndarray:
    """The frame sampled at every canvas-pixel centre of the VIEW (224 rows, H/224 screen px per canvas px, square),
    as a palette index, -1 where the pixel is no palette colour (actors, the player, anything off the painting)."""
    from PIL import Image
    a = np.asarray(Image.open(png).convert("RGB")).astype(np.int32)
    H, W = a.shape[:2]
    s = H / 224.0
    vw = int(W / s)
    ys = ((np.arange(224) + 0.5) * s).astype(int)
    xs = ((np.arange(vw) + 0.5) * s).astype(int)
    sub = a[ys][:, xs]
    d = ((sub[:, :, None, :] - PALETTE[None, None]) ** 2).sum(-1)
    lab = d.argmin(-1).astype(np.int8)
    lab[d.min(-1) > PAL_TOL ** 2] = -1
    return lab


def tmpl(png, ref: np.ndarray | None = None) -> dict:
    """Register a frame against the regenerated canvas: the integer canvas offset (ox, oy) of the view's top-left
    that maximises the palette agreement, found by FFT correlation over every offset -- never seeded from the
    script's readback. ``score`` = the fraction of the view's palette pixels that agree there; ``second`` = the best
    score at least one cell away (the peak's uniqueness)."""
    ref = canvas_labels() if ref is None else ref
    lab = classify(png)
    vh, vw = lab.shape
    Hh, Ww = ref.shape[0] + 2 * PADY, ref.shape[1] + 2 * PADX
    R = np.full((Hh, Ww), -1, dtype=np.int8)
    R[PADY:PADY + ref.shape[0], PADX:PADX + ref.shape[1]] = ref
    total = np.zeros((Hh, Ww))
    for c in range(len(PALETTE)):
        rc = (R == c).astype(np.float64)
        vc = np.zeros((Hh, Ww))
        vc[:vh, :vw] = (lab == c)
        total += np.real(np.fft.ifft2(np.fft.fft2(rc) * np.conj(np.fft.fft2(vc))))
    valid = int((lab >= 0).sum())
    total = total[: Hh - vh + 1, : Ww - vw + 1]            # offsets whose view window lies inside the padded canvas
    oy, ox = np.unravel_index(int(np.argmax(total)), total.shape)
    best = float(total[oy, ox])
    t2 = total.copy()
    t2[max(0, oy - CELL):oy + CELL + 1, max(0, ox - CELL):ox + CELL + 1] = -1
    return {"ox": int(ox) - PADX, "oy": int(oy) - PADY, "score": best / max(1, valid),
            "second": float(t2.max()) / max(1, valid), "valid": valid, "vw": vw,
            "offart_top": _band(lab, top=True), "offart_bottom": _band(lab, top=False)}


def _band(lab: np.ndarray, *, top: bool) -> int:
    """How many view rows at the top (bottom) are >= 95% non-palette -- the view past the painting."""
    rows = lab if top else lab[::-1]
    n = 0
    for r in rows:
        if (r < 0).mean() < 0.95:
            break
        n += 1
    return n


def red_blobs(png, min_blob: int = 60) -> list:
    """[(x, y, n)] red-balloon blobs, left to right (studies/sine-kit/rung1_render.py's idiom)."""
    from PIL import Image
    a = np.asarray(Image.open(png).convert("RGB")).astype(np.int16)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    ys, xs = np.nonzero((r > 140) & (r - g > 90) & (r - b > 80))
    if xs.size == 0:
        return []
    order = np.argsort(xs)
    xs, ys = xs[order], ys[order]
    cuts = np.nonzero(np.diff(xs) > 40)[0] + 1
    return [(float(gx.mean()), float(gy.mean()), int(gx.size))
            for gx, gy in zip(np.split(xs, cuts), np.split(ys, cuts)) if gx.size >= min_blob]


# ------------------------------------------------------------------- predictions (from the BUILT camera)
def _camera():
    from ff9mapkit import build
    return build.resolve_camera(build.FieldProject.load(BENCH_TOML))


def predict_numbers(hfw: int = 199) -> dict:
    """The frozen predictions (1280x720: PsxFieldWidth 398, HFW 199; runtime widescreen on; CameraStabilizer 0).
    Follow = the player's projected aim (y + charAimHeight 324), clamped to the EFFECTIVE window, truncated."""
    from ff9mapkit.scene import cam as C
    c = _camera()
    assert tuple(int(v) for v in c.range) == RANGE, c.range
    assert tuple(C.scroll_bounds(RANGE)) == BOX43, C.scroll_bounds(RANGE)
    delta = min(2 * hfw - 320, BOX43[1] - BOX43[0]) // 2
    boxw = (BOX43[0] + delta, BOX43[1] - delta, BOX43[2], BOX43[3])

    def follow(x, z, aim=324):
        u, v = C.to_canvas((x, aim, z), c)
        return (int(min(max(u, boxw[0]), boxw[1])), int(min(max(v, boxw[2]), boxw[3])))

    return {"hfw": hfw, "delta": delta, "box_widescreen": boxw, "box43": BOX43,
            "spawn": follow(0, -1102), "spawn_flipped_aim": follow(0, -1102, aim=-324),
            "spawn_raw": C.to_canvas((0, 324, -1102), c),
            "walk": {f"{x},{z}": follow(x, z) for x, z in ((1600, -1102), (-1600, -1102), (0, -400), (0, -1900))},
            "tmpl_of": "(VX - hfw, VY - 112)"}


def follow_model(x: float, z: float, hfw: int = 199) -> tuple:
    from ff9mapkit.scene import cam as C
    delta = min(2 * hfw - 320, BOX43[1] - BOX43[0]) // 2
    u, v = C.to_canvas((x, 324, z), _camera())
    return (int(min(max(u, BOX43[0] + delta), BOX43[1] - delta)), int(min(max(v, BOX43[2]), BOX43[3])))


# ------------------------------------------------------------------- the daemon
def _x(e: str) -> bytes:
    return exprasm.assemble(e + " B_EXPR_END")


def _stmt(text: str) -> bytes:
    return opcodes.encode(0x05, _x(text), arg_flags=0b1)


def g(name: str) -> str:
    off = G16.get(name) or S16[name]
    return f"Global.Int16[{off}]"


def _bit(i: int, v: int) -> bytes:
    return _stmt(f"Global.Bit[{i}] const({v}) B_LET")


def _const(v: int) -> str:
    return f"const({v})" if -0x8000 <= v <= 0x7FFF else f"const4({v})"


def key(name: str) -> str:
    return f"{_const(KEYMASK[name])} B_KEY"


def keys_expr() -> str:
    """KEYS = sum of B_KEY(mask) * bit, accumulated left to right so the CalcStack never holds more than three."""
    parts = [f"{key(n)} const({bit}) B_MULT" for n, _m, bit in KEYS]
    return parts[0] + "".join(f" {p} B_PLUS" for p in parts[1:])


def _set(name: str, expr: str) -> bytes:
    return _stmt(f"{g(name)} {expr} B_LET")


def _inc(name: str, by: str = "const(1)") -> bytes:
    return _stmt(f"{g(name)} {g(name)} {by} B_PLUS B_LET")


def move_camera(x: str, y: str, dur: str | int = 1, typ: int = 0) -> bytes:
    """0x6F with expression X/Y; a literal dur (never 0) or an expression dur; type always a literal."""
    if isinstance(dur, int):
        assert dur > 0, "a literal MoveCamera duration of 0 is a NaN / per-tick throw"
        return opcodes.encode(0x6F, _x(x), _x(y), dur, typ, arg_flags=0b0011)
    return opcodes.encode(0x6F, _x(x), _x(y), _x(dur), typ, arg_flags=0b0111)


def _issued(dur: int = 1) -> list:
    """ISS = the duration class of the move issued THIS tick (1 = a one-tick move, 2 = a glide); the next tick's
    top mirrors it into ISSP beside TXP/TYP, so every sample carries the command its view answers to."""
    return [_set("iss", f"const({dur})"), _inc("nmc")]


def _clamp(name: str, lo: int, hi: int) -> list:
    v = g(name)
    return [_stmt(f"{v} {v} {v} const({hi}) B_GT {v} const({hi}) B_MINUS B_MULT B_MINUS B_LET"),
            _stmt(f"{v} {v} {v} const({lo}) B_LT const({lo}) {v} B_MINUS B_MULT B_PLUS B_LET")]


def _dispatcher() -> list:
    """Stage 2: one command per poke of CMD (the harness pokes the args first, CMD last). Each accepted command ends
    LAST = CMD, ACK += 1, ACKT = T (the tick it ran in -- its samples' VX is still the pre-command view), CMD = 0; an
    unknown or refused one (a zero duration) LAST = -CMD."""
    cmd, ad = f"Global.Byte[{CMD}]", f"Global.Byte[{AD}]"
    ax, ay = f"Global.Int16[{AX}]", f"Global.Int16[{AY}]"
    guard = [_stmt(f"{ad} const(0) B_GT"), (JMP_IFNOT, "c_bad")]
    bodies = {
        1: [_set("tx", ax), _set("ty", ay), move_camera(g("tx"), g("ty")), *_issued()],
        2: [*guard, _set("tx", ax), _set("ty", ay), move_camera(g("tx"), g("ty"), ad), *_issued(2)],
        3: [_set("tx", f"{g('vx')} {ax} B_PLUS"), _set("ty", f"{g('vy')} {ay} B_PLUS"),
            move_camera(g("tx"), g("ty")), *_issued()],
        4: [*guard, opcodes.encode(0x70, _x(ad), _x(f"Global.Byte[{AT}]"), arg_flags=0b11), _set("rt", "const(1)")],
        5: [opcodes.encode(0x71, 0, 0, 0)],
        6: [opcodes.encode(0x71, 1, 0, 0)],
        7: [opcodes.encode(0x2D)],
        8: [opcodes.encode(0x2E)],
    }
    B: list = [_stmt(f"{cmd} const(0) B_NE"), (JMP_IFNOT, "c_done")]
    for k, body in bodies.items():
        B += [_stmt(f"{cmd} const({k}) B_EQ"), (JMP_IFNOT, f"c_not{k}"), *body, (JMP, "c_ok"), label(f"c_not{k}")]
    B += [label("c_bad"), _set("last", f"const(0) {cmd} B_MINUS"), (JMP, "c_fin"),
          label("c_ok"), _set("last", cmd),
          label("c_fin"), _inc("ack"), _set("ackt", g("t")), _stmt(f"{cmd} const(0) B_LET"),
          label("c_done")]
    return B


def _pan() -> list:
    """Stage 3: while MODE is 1 (relative: target = the engine's view + STEP * the held direction -- the stock
    CalculateScreenOrigin + MoveCamera(X+-k, Y+-k, 1, 0) stepper) or 3 (absolute: target += STEP * direction, seeded
    from the view when the mode is entered), move the view, clamped in the SCRIPT to the 4:3 box."""
    mode = f"Global.Byte[{MODE}]"
    B = [_stmt(f"{mode} const(1) B_EQ {mode} const(3) B_EQ B_OROR"), (JMP_IFNOT, "p_done"),
         _set("dx", f"{key('right')} {key('left')} B_MINUS"),
         _set("dy", f"{key('down')} {key('up')} B_MINUS"),
         _inc("nr", key("right")), _inc("nl", key("left")), _inc("nd", key("down")), _inc("nu", key("up")),
         _stmt(f"{mode} const(3) B_EQ {g('pmode')} const(3) B_NE B_ANDAND"), (JMP_IFNOT, "p_seeded"),
         _set("tx", g("vx")), _set("ty", g("vy")),
         label("p_seeded"),
         # nothing held -> write no target: a dispatcher move issued this same tick keeps its TX/TY (the review's
         # latent C-CORE false-off: a MODE-1 idle pass used to overwrite them with VX + 0)
         _stmt(f"{g('dx')} {g('dy')} B_OROR"), (JMP_IFNOT, "p_done"),
         _stmt(f"{mode} const(1) B_EQ"), (JMP_IFNOT, "p_abs"),
         _set("tx", f"{g('vx')} {g('dx')} const({STEP}) B_MULT B_PLUS"),
         _set("ty", f"{g('vy')} {g('dy')} const({STEP}) B_MULT B_PLUS"),
         (JMP, "p_clamp"),
         label("p_abs"),
         _set("tx", f"{g('tx')} {g('dx')} const({STEP}) B_MULT B_PLUS"),
         _set("ty", f"{g('ty')} {g('dy')} const({STEP}) B_MULT B_PLUS"),
         label("p_clamp"),
         *_clamp("tx", BOX43[0], BOX43[1]), *_clamp("ty", BOX43[2], BOX43[3]),
         move_camera(g("tx"), g("ty")), *_issued(),
         label("p_done"),
         _set("pmode", mode)]
    return B


def daemon_body(stage: int) -> bytes:
    if stage not in STAGES:
        raise SystemExit(f"stage {stage} is not built yet (have {STAGES})")
    zero = ("t", "ackt", "gate", "fpb", "fuc", "nmc", "rt", "ack", "last", "nr", "nl", "nd", "nu", "edges", "tx", "ty",
            "txp", "typ", "issp", "flags", "keys", "iss", "pmode", "dx", "dy")
    B: list = [_set(n, "const(0)") for n in zero]
    B += [_stmt(f"Global.Byte[{b}] const(0) B_LET") for b in (CMD, MODE)]
    B.append(label("gate"))
    firsts = (("fpb", f"Global.Bit[{PBOUND}]"), ("fuc", "B_SYSVAR[2] const(0) B_NE"))
    B += [_stmt(f"{g(k)} {g(k)} {g(k)} const(0) B_EQ {src} B_MULT {g('gate')} const(1) B_PLUS B_MULT B_PLUS B_LET")
          for k, src in firsts]
    B += [_stmt(f"Global.Bit[{PBOUND}] B_SYSVAR[2] B_ANDAND"), (JMP_IFNOT, "hold"), (JMP, "go"),
          label("hold"), _inc("gate"), opcodes.wait(1), (JMP, "gate"),
          label("go"), opcodes.wait(SETTLE),
          label("top"),
          opcodes.encode(0xEA), _set("vx", "B_SYSVAR[12]"), _set("vy", "B_SYSVAR[13]"),    # nothing in between
          opcodes.encode(0xA9, 250), _set("psx", "B_SYSVAR[12]"), _set("psy", "B_SYSVAR[13]"),
          _set("txp", g("tx")), _set("typ", g("ty")), _set("issp", g("iss")), _set("iss", "const(0)"),
          _inc("t"), _set("uc", "B_SYSVAR[2]"), _set("cam", "B_SYSVAR[1]"),
          _set("keys", keys_expr()),
          _stmt(f"{g('rt')} {g('rt')} {g('rt')} const(0) B_GT {g('rt')} const(999) B_LT B_MULT B_PLUS B_LET")]
    if stage >= 2:
        B += _dispatcher()
    if stage >= 3:
        B += _pan()
    B += [opcodes.wait(1), (JMP, "top"), opcodes.RETURN]
    return asm(B)


def entry_bytes(stage: int) -> bytes:
    """A seated code entry: type 0, ONE tag-0 function at fpos 4 (the sine-kit / gauge-daemon shape)."""
    return bytes([0x00, 0x01]) + struct.pack("<HH", 0, 4) + daemon_body(stage)


def prop_uids(eb: bytes) -> dict:
    """{"L": uid, "C": uid, "R": uid} -- the balloon entries, told apart by their x. A kit prop's Init sets its
    position into entry locals first (``05 d9 00 7d <x> 2c 7f`` = loc Int16[0] := x) and CreateObject (0x1D)
    reads them back as expressions. A kit prop's uid IS its entry slot."""
    s = EbScript.from_bytes(eb)
    found = []
    for e in s.entries:
        if e.size <= 0 or not e.funcs:
            continue
        f0 = e.funcs[0]
        ins = list(D.iter_code(eb, f0.abs_start, f0.abs_end))
        if not any(i.op == 0x2F and struct.unpack_from("<H", eb, i.off + 2)[0] == MODEL for i in ins):
            continue
        made = [i for i in ins if i.op == 0x1D]
        xs = [i for i in ins if i.op == 0x05 and eb[i.off + 1:i.off + 4] == b"\xd9\x00\x7d"
              and eb[i.off + 6:i.end] == b"\x2c\x7f"]
        if len(made) != 1 or eb[made[0].off:made[0].end] != bytes.fromhex("1d03d9007fd9047f") or len(xs) != 1:
            raise SystemExit(f"entry {e.index}: not the kit prop shape (CreateObject {len(made)}, x sets {len(xs)})")
        found.append((struct.unpack_from("<h", eb, xs[0].off + 4)[0], e.index))
    if len(found) != 3:
        raise SystemExit(f"expected THREE balloon ({MODEL}) props, found {found}")
    xs = sorted(found)
    return {"L": xs[0][1], "C": xs[1][1], "R": xs[2][1], "x": [x for x, _e in xs]}


def _after_op(eb: bytes, entry: int, op: int) -> int:
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


def patch_eb(eb0: bytes, stage: int) -> tuple:
    """Seat + arm the stage's daemon behind its latch. Returns (bytes, daemon slot, prop uids)."""
    uids = prop_uids(eb0)
    pl = player_entry(eb0)
    baseline = {str(p) for p in eblint.lint_eb(eb0)}
    out = eb_edit.insert_in_function(eb0, pl, 0, _after_op(eb0, pl, 0x2C), _bit(PBOUND, 1))
    for tag, bit in (("L", READY_L), ("C", READY_C), ("R", READY_R)):
        out = eb_edit.insert_in_function(out, uids[tag], 0, _after_op(out, uids[tag], 0x1D), _bit(bit, 1))
    out, slot = _object.seat_entry(out, entry_bytes(stage))
    out = eb_edit.activate_block(out, _bit(PBOUND, 0) + _bit(READY_L, 0) + _bit(READY_C, 0) + _bit(READY_R, 0)
                                 + opcodes.init_code(slot, 0))
    fresh = [p for p in eblint.lint_eb(out)
             if getattr(p, "severity", "error") == "error" and str(p) not in baseline]
    if fresh:
        raise SystemExit("patch produced NEW lint errors:\n  " + "\n  ".join(map(str, fresh)))
    return out, slot, uids


def deployed_stage(eb: bytes) -> int | None:
    for st in sorted(STAGES, reverse=True):
        if daemon_body(st) in eb:
            return st
    return None


# ------------------------------------------------------------------- the offline audit (P-BYTES)
def audit(body: bytes, stage: int) -> list:
    """Every rule the daemon's bytes must keep, as a list of violations (empty = clean)."""
    bad = []
    ops = list(D.iter_code(body, 0, len(body)))
    for i in ops:
        if i.op == 0x6F:
            if body[i.off + 1] not in (0x03, 0x07):
                bad.append(f"0x6F @{i.off}: arg flags {body[i.off + 1]:#04x} (want 0x03/0x07)")
            if body[i.end - 1] != 0x00:
                bad.append(f"0x6F @{i.off}: type byte {body[i.end - 1]} (want 0, linear)")
            if body[i.off + 1] == 0x03 and body[i.end - 2] == 0:
                bad.append(f"0x6F @{i.off}: a literal duration 0")
        if i.op == 0x70 and not body[i.off + 1] & 0b01 and body[i.off + 2] == 0:
            bad.append(f"0x70 @{i.off}: a literal duration 0")
        if i.op in (0x73, 0x74, 0x1E, 0xAB, 0xB9):
            bad.append(f"0x{i.op:02X} @{i.off}: never emitted by this bench")
        if i.op == 0x14 and body[i.off + 1] & 0b100:
            bad.append(f"0x14 @{i.off}: its tag operand is geti(), never an expression")
    n71 = sum(i.op == 0x71 for i in ops)
    if n71 != (2 if stage >= 2 else 0):
        bad.append(f"0x71 appears {n71}x (want exactly the CMD 5/6 pair from stage 2)")
    if re.search(rb"\x7d[\x00-\xff][\x80-\xff]\x59|\x7d[\x00-\xff][\x80-\xff]\x4f", body):
        bad.append("a const(>= 0x8000) key mask (the engine reads it negative) -- use const4")
    if sum(i.op == 0xEA for i in ops) != 1:
        bad.append("expected exactly one 0xEA")
    return bad


# ------------------------------------------------------------------- verbs
def probe(stage: int) -> None:
    body = daemon_body(stage)
    ops = list(D.iter_code(body, 0, len(body)))
    print(f"stage {stage} daemon: {len(body)}B, {len(ops)} ops")
    for i in ops:
        if i.op in (0x6F, 0x70, 0x71, 0xEA, 0xA9, 0x2D, 0x2E):
            print(f"   @{i.off:4d} {opcodes.OP_NAMES[i.op]:24s} {body[i.off:i.end].hex(' ')}")
    bad = audit(body, stage)
    print("P-BYTES:", "clean" if not bad else bad)
    eb = _blank_build()
    if eb is not None:
        out, slot, uids = patch_eb(eb, stage)
        print(f"patched an offline build: daemon at slot {slot}, props {uids}, {len(out)}B, "
              f"deployed_stage -> {deployed_stage(out)}")


def _blank_build() -> bytes | None:
    """The bench's own .eb from an offline build (the templates must be extracted), or None."""
    import tempfile
    out = Path(tempfile.mkdtemp(prefix="photo0-"))
    r = subprocess.run([sys.executable, "-m", "ff9mapkit", "build", str(BENCH_TOML), "--out", str(out)],
                       cwd=REPO / "ff9mapkit", capture_output=True, text=True)
    hits = list(out.rglob(f"EVT_{FIELD_NAME}.eb.bytes")) or list(out.rglob("*.eb.bytes"))
    if r.returncode != 0 or not hits:
        print(f"(offline build unavailable: {r.stderr.strip().splitlines()[-1:] or r.stdout.strip()[-200:]})")
        return None
    return hits[0].read_bytes()


def predict() -> None:
    p = predict_numbers()
    p["art_cells"] = cells().tolist()
    PREDICTIONS.write_text(json.dumps(p, indent=1), encoding="utf-8")
    q = {k: v for k, v in p.items() if k != "art_cells"}
    print(json.dumps(q, indent=1))
    print(f"wrote {PREDICTIONS}")


def deploy(stage: int) -> None:
    daemon_body(stage)                                          # refuse an unbuilt stage before deploying anything
    if not ART.exists():
        make_art()
    r = subprocess.run([sys.executable, str(REPO / "tools" / "deploy_field.py"), str(BENCH_TOML),
                        "--id", str(FIELD_ID), "--name", FIELD_NAME, "--text-block", str(FIELD_ID),
                        "--mod-folder", MOD_FOLDER])
    if r.returncode != 0:
        raise SystemExit("deploy_field failed")
    live = ModLayout(find_game_path() / MOD_FOLDER)
    n, slot, uids = 0, None, None
    for lang in LANGS:
        p = live.eb_path(lang, f"EVT_{FIELD_NAME}.eb.bytes")
        if p.exists():
            out, slot, uids = patch_eb(p.read_bytes(), stage)
            atomic_write_bytes(p, out)
            n += 1
    if not n:
        raise SystemExit(f"no live EVT_{FIELD_NAME}.eb.bytes found to patch")
    print(f"patched {n} language .eb file(s) with STAGE {stage}: daemon at slot {slot}, props {uids}")
    print(f"  Revert: py tools/scroll_out/revert_deploy_{FIELD_ID}.py")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("verb", choices=["art", "probe", "predict", "deploy"])
    ap.add_argument("--stage", type=int, default=1)
    a = ap.parse_args()
    if a.verb == "art":
        make_art()
    elif a.verb == "probe":
        probe(a.stage)
    elif a.verb == "predict":
        predict()
    else:
        deploy(a.stage)
