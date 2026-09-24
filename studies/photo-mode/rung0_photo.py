"""PHOTO MODE, RUNG 0 -- a script-driven camera pan, in-game, measured two independent ways.

    py studies/photo-mode/photo0_bench.py deploy --stage N
    py tools/play.py studies/photo-mode/rung0_photo.py --label photo-rung0-sN

The scenario reads which STAGE the deployed .eb carries (photo0_bench.deployed_stage) and runs the calibration plus that
stage's phases -- one stage per in-game run, so each run changes one thing.

INSTRUMENTS
  mirrors  the daemon copies, at the TOP of every tick and before anything it commands: the engine's view (0xEA ->
           VX/VY, MoveCamera's own space), the player's screen position (0xA9 -> PSX/PSY), usercontrol, the camera
           index, the held keys, and the target + duration class the PREVIOUS tick commanded (TXP/TYP/ISSP). So every
           sample carries the command its view answers to. A published state is a tick-boundary snapshot.
  tmpl     every rest shot registered against the regenerated 768x448 canvas by FFT over EVERY offset -- never seeded
           from the readback -- giving the canvas offset of the drawn view's top-left and the rows past the painting.
  blobs    the red balloons L / C / R (registration of actors against the art).

CALIBRATION (every run)
  P0 30955 served by FF9CustomMap alone; P1 every language carries the same stage, aimed at the balloons L/C/R;
  P-BYTES the daemon's bytes keep the bench's rules; P2 the frozen predictions still equal the built camera + art;
  P-ART the art on disk is the seeded pattern; P-INI Memoria.ini's widescreen + stabilizer (the predictions assume 0)
  LATCH  the daemon opened no earlier than the player's bind and control
  C1-SPAWN  under follow the view reads the kit's predicted canvas point of the player's aim (to_canvas(x, +324, z))
  C1-NOISE  two rest shots register to one offset;  C1-PIX  the drawn view's top-left is (VX - HFW, VY - 112)
  C1-A9     the player's screen x reads the UI centre at spawn
  C1-FOLLOW four walks: every rest view == the follow model of where the player stands (clamped to the EFFECTIVE
            window, which follows PsxFieldWidth -- the INI + aspect; MoveCamera's own clamp reads the RUNTIME flag,
            measured directly by 2.5) and the frame agrees
  NC-KEYS   KEYS is 0 at idle; a harness hold reaches B_KEY and walks the player
STAGE 2 (the dispatcher)  2.1 LOCK .. 2.10 the 0x71 negative control -- see run_stage2
STAGE 3 (the pan)         3.1 .. 3.8 -- see run_stage3
STAGE 4 (hides + grade)   4.0 .. 4.6 -- every hide AND every show measured on the frame; see run_stage4
STAGE 5 (the modal loop)  5.0 .. 5.7 -- Select opens, R1 hides, L1 grades, the d-pad pans, Cancel restores; buttons only
C-CORE (stages 2-3)  over EVERY sample whose previous tick issued a one-tick move: VX == clamp(TXP, the widescreen X
          window) and VY == TYP -- the engine applies the command exactly, next tick, X clamped at issue, Y never
NC-THROW  no NullReference / InvalidCast / IndexOutOfRange / DivideByZero through EventEngine, EBin or FieldMap
"""
from __future__ import annotations

import json
import math
import re
import sys
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
sys.path.insert(0, str(HERE))
import photo0_bench as P  # noqa: E402
from ff9mapkit.config import LANGS, ModLayout  # noqa: E402
try:                                   # play.py puts tools/ on sys.path and imports the package as `harness`: catch
    from harness import HarnessError   # THAT class (a `tools.harness` import would be a second, never-raised copy)
except ImportError:                    # offline import checks
    from tools.harness import HarnessError  # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
THROWS = {"NullReferenceException", "InvalidCastException", "IndexOutOfRangeException", "DivideByZeroException",
          "ArgumentOutOfRangeException", "OverflowException"}   # a List indexer (cameraList[curCamIdx]) throws the 5th
WHERE = ("EventEngine", "EBin", "FieldMap")


class Stop(Exception):
    """A phase whose premise failed: later phases would measure nothing."""


def _i16(st, off: int) -> int:
    v = sum(1 << i for i in range(16) if st.flag(off * 8 + i))
    return v - 0x10000 if v & 0x8000 else v


class Rec:
    """Every distinct daemon tick seen, with its mirrors."""

    def __init__(self, g):
        self.g, self.s, self.exclude = g, {}, []
        self.one_tick = []           # the ack tick of every one-tick move (MOVE1 / REL): C-CORE expects a sample after
        self.log = []                # every command, with its args and ack tick
        self.notes = {}              # fits, registration rows, sanity values -- written to photo_run.json

    def poll(self) -> dict:
        st = self.g.state
        if st.armed is False or (st.raw or {}).get("faulted"):
            raise Stop(f"the harness agent stopped publishing (armed {st.armed}, faulted {(st.raw or {}).get('faulted')})")
        m = {k: _i16(st, P.G16[k]) for k in P.WATCHED}
        m.update(frame=st.frame, px=st.player_x, pz=st.player_z, control=st.control, fading=st.fading)
        if m["t"] > 0:
            self.s.setdefault(m["t"], m)
        return m

    def until(self, pred, timeout: float, what: str) -> dict:
        deadline = time.time() + timeout
        while time.time() < deadline:
            m = self.poll()
            if pred(m):
                return m
            time.sleep(0.004)
        raise Stop(f"timed out ({timeout:.0f}s) waiting for {what}")

    def ticks(self, n: int, timeout: float = 15) -> dict:
        t0 = self.poll()["t"]
        return self.until(lambda m: m["t"] >= t0 + n, timeout, f"{n} daemon ticks")

    def frames(self, n: int, timeout: float = 30) -> dict:
        f0 = self.poll()["frame"]
        return self.until(lambda m: m["frame"] >= f0 + n, timeout, f"{n} frames")

    def between(self, a: int, b: int = 1 << 30) -> list:
        return [self.s[k] for k in sorted(self.s) if a < k <= b]


def settle(rec: Rec, n: int = 4, timeout: float = 20) -> dict:
    hist = []

    def ok(m):
        if not hist or hist[-1]["t"] != m["t"]:
            hist.append(m)
        tail = hist[-n:]
        return len(tail) == n and not m["fading"] and len({(x["vx"], x["vy"]) for x in tail}) == 1

    return rec.until(ok, timeout, "the view at rest")


def rest_shot(g, rec: Rec, name: str, ref) -> tuple:
    for _attempt in range(3):
        m0 = settle(rec)
        png = g.shot(name)
        m1 = settle(rec, n=2)
        if (m1["vx"], m1["vy"]) == (m0["vx"], m0["vy"]):
            return png, m1, P.tmpl(png, ref)
    raise Stop(f"{name}: the view would not hold still for a shot")


def cmd(g, rec: Rec, name: str, ax: int = 0, ay: int = 0, ad: int = 0, at: int = 0, timeout: float = 5) -> tuple:
    """Poke the args, then CMD (one request = one frame), and wait for the daemon's ack. Returns (the tick it ran in,
    that tick's sample -- whose VX is still the pre-command view)."""
    a = rec.poll()["ack"]
    g.send(f"byte {P.AX} {ax & 0xFF}", f"byte {P.AX + 1} {(ax >> 8) & 0xFF}",
           f"byte {P.AY} {ay & 0xFF}", f"byte {P.AY + 1} {(ay >> 8) & 0xFF}",
           f"byte {P.AD} {ad & 0xFF}", f"byte {P.AT} {at & 0xFF}", f"byte {P.CMD} {P.CMDS[name]}")
    m = rec.until(lambda m: m["ack"] == a + 1, timeout, f"the daemon to ack {name}")
    rec.log.append({"cmd": name, "ax": ax, "ay": ay, "ad": ad, "at": at, "ackt": m["ackt"], "last": m["last"]})
    if m["last"] != P.CMDS[name]:
        raise Stop(f"{name}: the daemon refused it (LAST {m['last']})")
    if name in ("MOVE1", "REL"):
        rec.one_tick.append(m["ackt"])
    return m["ackt"], m


def hold_and_watch(g, rec: Rec, button: str, frames: int) -> dict:
    """Hold a button without blocking, keep sampling until the hold is over, then return the settled view."""
    f0 = rec.poll()["frame"]
    g.hold(button, frames)
    rec.until(lambda m: m["frame"] >= f0 + frames + 6, frames / 20 + 20, f"the {button} hold to end")
    return settle(rec)


def poke(g, index: int, value: int) -> None:
    g.send(f"byte {index} {value & 0xFF}")


# ------------------------------------------------------------------- preflight
def _ini() -> dict:
    text = (GAME / "Memoria.ini").read_text(encoding="utf-8", errors="replace")
    out = {}
    for k in ("WidescreenSupport", "CameraStabilizer"):
        m = re.search(rf"^\s*{k}\s*=\s*(-?\d+)", text, re.M)
        out[k] = int(m.group(1)) if m else None
    return out


def preflight(g) -> tuple:
    folders = [p.parent.name for p in GAME.glob("*/DictionaryPatch.txt")
               if re.search(rf"FieldScene {P.FIELD_ID}\b", p.read_text(encoding="utf-8", errors="replace"))]
    g.check(folders == ["FF9CustomMap"], "P0: 30955 is served by FF9CustomMap alone", str(folders))
    live = ModLayout(GAME / P.MOD_FOLDER)
    paths = {L: live.eb_path(L, f"EVT_{P.FIELD_NAME}.eb.bytes") for L in LANGS}
    ebs = {L: p.read_bytes() for L, p in paths.items() if p.exists()}
    stages = {L: P.deployed_stage(b) for L, b in ebs.items()}
    try:
        uids = P.prop_uids(next(iter(ebs.values()))) if ebs else {}
    except SystemExit as e:
        uids = {"error": str(e)}
    ok = bool(ebs) and len(set(stages.values())) == 1 and None not in stages.values()
    g.check(ok, "P1: every deployed language .eb carries the SAME stage's daemon", str(stages))
    if not ok:
        raise Stop("no single deployed stage")
    stage = next(iter(stages.values()))
    g.check((uids.get("L"), uids.get("C"), uids.get("R")) == (2, 3, 4) and uids.get("x") == [-1000, 0, 1000],
            "P1: the balloons L / C / R are the kit props at x -1000 / 0 / 1000", str(uids))
    bad = P.audit(P.daemon_body(stage), stage)
    g.check(not bad, f"P-BYTES: the stage-{stage} daemon keeps the bench's byte rules (0x6F type 0 + a non-zero "
            "duration, 0x71 only as the CMD 5/6 pair, no 0x73/0x74/0x1E/0xAB/0xB9, const4 key masks)", str(bad))
    frozen = json.loads(P.PREDICTIONS.read_text(encoding="utf-8"))
    now = P.predict_numbers()
    same = all(json.dumps(frozen[k]) == json.dumps(v if not isinstance(v, tuple) else list(v))
               for k, v in now.items() if k != "spawn_raw") and frozen["art_cells"] == P.cells().tolist()
    g.check(same, "P2: the frozen predictions (rung0_predictions.json) equal the built camera and the seeded art",
            f"frozen spawn {frozen['spawn']} now {now['spawn']}")
    from PIL import Image
    art = np.asarray(Image.open(P.ART).convert("RGB"))[::P.ART_SCALE, ::P.ART_SCALE].astype(np.int32)
    want = P.PALETTE[P.canvas_labels()]
    g.check(art.shape[:2] == (448, 768) and bool((art == want).all()),
            "P-ART: the bench's back.png is the seeded pattern the instrument regenerates", str(art.shape))
    ini = _ini()
    print(f"[photo-rung0] Memoria.ini: {ini}")
    g.check(ini == {"WidescreenSupport": 1, "CameraStabilizer": 0},
            "P-INI: widescreen on and no camera stabilizer -- the conditions the predictions were frozen for", str(ini))
    return stage, frozen


# ------------------------------------------------------------------- the calibration
def _watch(g) -> None:
    bits = []
    for k in P.WATCHED:
        bits += [P.G16[k] * 8 + i for i in range(16)]
    g.watch(*bits)


def calibrate(g, rec: Rec, pred: dict, ref, *, walks: bool = True) -> dict:
    m = rec.until(lambda m: m["t"] > 5, 40, "the daemon's clock running")
    print(f"[photo-rung0] latch: gate {m['gate']}, player bound at gate tick {m['fpb']}, control at {m['fuc']}")
    g.check(m["gate"] >= 1, "LATCH: the daemon was seated and waiting before the player and control came up (it "
            "held at least one tick) -- first-true ticks are printed above", f"gate {m['gate']}")
    m = settle(rec)
    sp, flip = tuple(pred["spawn"]), tuple(pred["spawn_flipped_aim"])
    note = " -- the FLIPPED aim sign" if (m["vx"], m["vy"]) == flip else ""
    g.check(abs(m["vx"] - sp[0]) <= 1 and abs(m["vy"] - sp[1]) <= 1,
            "C1-SPAWN: under follow the view reads the kit's canvas point of the player's aim (to_canvas(0,+324,-1102) "
            "clamped) -- the MoveCamera space IS the canvas, the aim is 324 up", f"read ({m['vx']},{m['vy']}) predicted "
            f"{sp}{note}")
    g.check(m["uc"] == 1, "C1-STATE: usercontrol on at rest", f"uc {m['uc']} cam {m['cam']}")
    png0, m0, t0 = rest_shot(g, rec, "c-i0", ref)
    from PIL import Image
    W, H = Image.open(png0).size
    hfw = int(224 * W / H) // 2
    print(f"[photo-rung0] shot {W}x{H}: PsxFieldWidth {int(224 * W / H)}, HFW {hfw}; tmpl {t0}")
    g.check((W, H) == (1280, 720), "C1-SCREEN: the frame is 1280x720 (HFW 199 -- what the predictions assume)",
            f"{W}x{H}")
    png1, m1, t1 = rest_shot(g, rec, "c-i0b", ref)
    g.check((t0["ox"], t0["oy"]) == (t1["ox"], t1["oy"]) and min(t0["score"], t1["score"]) >= 0.8,
            "C1-NOISE: two rest shots register to the same canvas offset, both well (the instrument's floor)",
            f"{t0['ox'], t0['oy'], round(t0['score'], 3)} vs {t1['ox'], t1['oy'], round(t1['score'], 3)}")
    g.check(abs(t0["ox"] - (m0["vx"] - hfw)) <= 1 and abs(t0["oy"] - (m0["vy"] - P.HFH)) <= 1
            and t0["second"] < 0.6 * t0["score"],
            "C1-PIX: the DRAWN view's top-left is (VX - HFW, VY - 112) on the canvas -- the readback is the view's "
            "centre in canvas px, and the registration peak is unique",
            f"tmpl ({t0['ox']},{t0['oy']}) score {t0['score']:.3f} second {t0['second']:.3f}; VX,VY ({m0['vx']},"
            f"{m0['vy']})")
    g.check(abs(m0["psx"] - 960) <= 2, "C1-A9: the player (at the view's centre column) reads screen x 960 through "
            "0xA9 -- the UI is 1920 wide", f"PSX {m0['psx']} PSY {m0['psy']}")
    blobs0 = P.red_blobs(png0)
    print(f"[photo-rung0] spawn blobs {[(round(x), round(y), n) for x, y, n in blobs0]}")
    out = {"hfw": hfw, "i0": (png0, m0, t0, blobs0)}
    if walks:
        rows = []
        for x, z in ((1600, -1102), (-1600, -1102), (0, -400), (0, -1900)):
            g.walk_to(x, z)
            png, mw, tw = rest_shot(g, rec, f"c-walk_{x}_{-z}", ref)
            model = P.follow_model(mw["px"], mw["pz"], hfw)
            rows.append({"to": (x, z), "at": (round(mw["px"]), round(mw["pz"])), "v": (mw["vx"], mw["vy"]),
                         "model": model, "tmpl": (tw["ox"], tw["oy"]), "score": round(tw["score"], 3)})
        for r in rows:
            print(f"[photo-rung0] C1-FOLLOW {r}")
        ok = all(abs(r["v"][0] - r["model"][0]) <= 1 and abs(r["v"][1] - r["model"][1]) <= 1
                 and abs(r["tmpl"][0] - (r["v"][0] - hfw)) <= 1 and abs(r["tmpl"][1] - (r["v"][1] - P.HFH)) <= 1
                 for r in rows)
        pinned = [r for r in rows if r["v"][0] in (P.BOX43[0], P.BOX43[1])]
        g.check(ok, "C1-FOLLOW: at every walk's rest the view == the follow model of where the player stands, "
                "clamped to the widescreen window [199,569] x [112,336], and the frame agrees", json.dumps(rows))
        if pinned:
            print("[photo-rung0] !! VX reached the 4:3 edge (160/608): follow is NOT narrowed -- every X prediction "
                  "below is wrong; re-derive before reading them")
            rec.notes["follow_not_narrowed"] = pinned
    # NC-KEYS: idle KEYS is 0; a hold reaches B_KEY and walks the player
    t0_ = rec.poll()["t"]
    rec.ticks(30)
    idle = rec.between(t0_)
    x0 = rec.poll()["px"]
    f0 = rec.poll()["frame"]
    g.hold("right", 20)
    rec.until(lambda m: m["frame"] >= f0 + 26, 20, "the right hold")
    saw = [m for m in rec.between(t0_ + 30) if m["keys"] & 2]
    moved = rec.poll()["px"] - x0
    settle(rec)
    g.check(len(idle) >= 20 and all(m["keys"] == 0 for m in idle) and len(saw) >= 1 and abs(moved) >= 100,
            "NC-KEYS: KEYS reads 0 while nothing is held, and a harness 'hold right' reaches the script's B_KEY poll "
            "(bit 2) while it walks the player", f"idle {len(idle)} (non-zero {[m['keys'] for m in idle if m['keys']]}),"
            f" right seen in {len(saw)} ticks, player moved {moved:.0f}")
    return out


# ------------------------------------------------------------------- stage 2: the dispatcher
def _rcos(a: int) -> int:
    deg = np.float32(np.float32(a) / np.float32(4096.0)) * np.float32(360.0)
    rad = np.float32(np.float32(deg) * np.float32(0.0174532924))
    return int(np.float32(np.float32(math.cos(float(rad))) * np.float32(4096.0)))


def _glide_fit(samples: list, t_ack: int, vs: tuple, end: tuple, n: int, cosine: bool) -> dict:
    """How well the samples after t_ack follow the engine's interpolation (k = T - t_ack service frames), for a
    service per LOGIC tick (scale 1) and per render frame (scale 2)."""
    out = {}
    for scale in (1, 2):
        worst, rows = 0, []
        for m in samples:
            k = min(n, (m["t"] - t_ack) * scale)
            if k <= 0:
                continue
            if cosine:
                f = (_rcos(2048 * k // n + 2048) + 4096) / 8192
            else:
                f = k / n
            want = (int(vs[0] + (end[0] - vs[0]) * f), int(vs[1] + (end[1] - vs[1]) * f))
            err = max(abs(m["vx"] - want[0]), abs(m["vy"] - want[1]))
            worst = max(worst, err)
            rows.append((m["t"] - t_ack, (m["vx"], m["vy"]), want))
        out[scale] = {"worst": worst, "n": len(rows), "rows": rows[:6]}
    return out


def run_stage2(g, rec: Rec, cal: dict, ref) -> None:
    hfw = cal["hfw"]
    shots = {"spawn": cal["i0"]}

    # 2.1 LOCK
    ta, _ = cmd(g, rec, "LOCK")
    rec.ticks(6)
    after = rec.between(ta)
    g.check(after and all(m["uc"] == 0 for m in after) and not rec.poll()["control"],
            "2.1 LOCK: DisableMove zeroes usercontrol from the next tick on, and the harness sees control off",
            f"uc {[m['uc'] for m in after][:8]}")

    # 2.2 TAKE: one MoveCamera from follow
    before = settle(rec)
    ta, _ma = cmd(g, rec, "MOVE1", 300, 200)
    rec.ticks(8)
    after = rec.between(ta)
    pre = rec.s.get(ta)                                 # the ack tick's own sample (mirrored before the command)
    landed = (after[-1]["vx"], after[-1]["vy"]) if after else None
    nxt = rec.s.get(ta + 1)
    g.check(bool(after) and (pre is None or (pre["vx"], pre["vy"]) == (before["vx"], before["vy"]))
            and all((m["vx"], m["vy"]) == landed for m in after) and landed == (300, 200),
            "2.2 TAKE: MoveCamera(300, 200, 1, 0) from follow reads back EXACTLY on the next tick and holds",
            f"before {(before['vx'], before['vy'])}, ack tick {'unobserved' if pre is None else (pre['vx'], pre['vy'])}"
            f", next tick {'unobserved' if nxt is None else (nxt['vx'], nxt['vy'])}, after "
            f"{sorted({(m['vx'], m['vy']) for m in after})}")
    exact = [m for m in after if (m["vx"], m["vy"]) == (300, 200)]
    png, m, t = rest_shot(g, rec, "s2-take", ref)
    shots["take"] = (png, m, t, P.red_blobs(png))
    g.check(abs(t["ox"] - (300 - hfw)) <= 1 and abs(t["oy"] - (200 - P.HFH)) <= 1,
            "2.2 TAKE: the frame shows it -- tmpl == (101, 88)", f"tmpl ({t['ox']},{t['oy']}) score {t['score']:.3f}")
    if not exact:
        raise Stop("the take-over move did not land -- every later phase would measure nothing")

    # 2.3 HOLD: the camera stays put while the player walks
    n0 = rec.poll()["nmc"]
    ta, _ = cmd(g, rec, "UNLOCK")
    x0 = rec.poll()["px"]
    t_h = rec.poll()["t"]
    hold_and_watch(g, rec, "right", 30)
    during = rec.between(t_h)
    moved = rec.poll()["px"] - x0
    cmd(g, rec, "LOCK")
    g.check(abs(moved) >= 300 and all((m["vx"], m["vy"]) == (300, 200) for m in during)
            and all(m["nmc"] == n0 for m in during),
            "2.3 HOLD: after one MoveCamera the view stays put -- a 300u+ walk under it moves nothing (follow is off "
            "until a release, and no MoveCamera was re-issued)",
            f"player moved {moved:.0f}, views {sorted({(m['vx'], m['vy']) for m in during})[:5]}, nmc {n0}")

    # 2.4 REL
    ta, _ = cmd(g, rec, "REL", 40, -24)
    m = settle(rec)
    png, m, t = rest_shot(g, rec, "s2-rel", ref)
    shots["rel"] = (png, m, t, P.red_blobs(png))
    g.check((m["vx"], m["vy"]) == (340, 176) and abs(t["ox"] - (340 - hfw)) <= 1 and abs(t["oy"] - 64) <= 1,
            "2.4 REL: a move relative to the mirrored view (the stock read-then-nudge) lands at (340, 176) and is drawn "
            "there", f"({m['vx']},{m['vy']}) tmpl ({t['ox']},{t['oy']})")

    # 2.5 X-CLAMP at issue (widescreen)
    rows = []
    for x, want in ((100, 199), (700, 569)):
        cmd(g, rec, "MOVE1", x, 176)
        png, m, t = rest_shot(g, rec, f"s2-x{x}", ref)
        shots[f"x{x}"] = (png, m, t, P.red_blobs(png))
        rows.append((x, m["vx"], m["tx"], t["ox"], want))
    g.check(all(vx == want and abs(ox - (want - hfw)) <= 1 for x, vx, tx, ox, want in rows),
            "2.5 X-CLAMP: MoveCamera's X is clamped AT ISSUE to the widescreen window -- 100 -> 199, 700 -> 569 -- and "
            "the frame sits at the canvas edges (0, 370)", str(rows))

    # 2.6 NC-Y: Y is never clamped (so the script's clamp is load-bearing)
    rows = []
    for y in (40, 400):
        cmd(g, rec, "MOVE1", 384, y)
        png, m, t = rest_shot(g, rec, f"s2-y{y}", ref)
        shots[f"y{y}"] = (png, m, t, P.red_blobs(png))
        rows.append((y, m["vy"], t["oy"], t["offart_top"], t["offart_bottom"]))
    rel_t = shots["rel"][2]
    g.check(rows[0][1] == 40 and rows[1][1] == 400 and abs(rows[0][2] - (40 - P.HFH)) <= 1
            and abs(rows[1][2] - (400 - P.HFH)) <= 1 and abs(rows[0][3] - 72) <= 3 and abs(rows[1][4] - 64) <= 3
            and rel_t["offart_top"] <= 1 and rel_t["offart_bottom"] <= 1,
            "2.6 NC-Y: MoveCamera's Y is NEVER clamped -- 40 and 400 read back and draw 72 / 64 canvas rows past the "
            "painting (the same detector finds none on an in-window view)",
            f"{rows}; in-window view top/bottom {rel_t['offart_top']}/{rel_t['offart_bottom']}")

    # 2.7 GLIDE: a 30-tick linear move
    vs = (rec.poll()["vx"], rec.poll()["vy"])
    ta, _ = cmd(g, rec, "MOVEN", 250, 150, ad=30)
    rec.ticks(55)
    fit = _glide_fit(rec.between(ta, ta + 30), ta, vs, (250, 150), 30, cosine=False)
    tail = rec.between(ta + 31, ta + 55)
    print(f"[photo-rung0] 2.7 glide fit: {json.dumps(fit)}")
    rec.notes["2.7 fit"] = fit
    g.check(fit[1]["worst"] <= 1 and fit[1]["n"] >= 10 and tail and all((m["vx"], m["vy"]) == (250, 150) for m in tail),
            "2.7 GLIDE: MoveCamera(250, 150, 30, 0) glides linearly, one service per logic tick, and holds at the end",
            f"worst {fit[1]['worst']} over {fit[1]['n']} samples (per-render-frame fit worst {fit[2]['worst']}); "
            f"tail {sorted({(m['vx'], m['vy']) for m in tail})}")

    # 2.8 GIVE-BACK, linear: ReleaseCamera glides to the follow target and follow resumes
    here = rec.poll()
    end = P.follow_model(here["px"], here["pz"], hfw)
    vs = (here["vx"], here["vy"])
    ta, _ = cmd(g, rec, "RELEASE", ad=20, at=0)
    rec.ticks(40)
    fit = _glide_fit(rec.between(ta, ta + 20), ta, vs, end, 20, cosine=False)
    tail = rec.between(ta + 21, ta + 40)
    print(f"[photo-rung0] 2.8 release fit to {end}: {json.dumps(fit)}")
    rec.notes["2.8 fit"] = fit
    g.check(fit[1]["worst"] <= 1 and fit[1]["n"] >= 8 and tail
            and all(abs(m["vx"] - end[0]) <= 1 and abs(m["vy"] - end[1]) <= 1 for m in tail),
            "2.8 GIVE-BACK: ReleaseCamera(20, 0) glides linearly to the player's follow point and stays there",
            f"from {vs} to {end}: worst {fit[1]['worst']}, tail {sorted({(m['vx'], m['vy']) for m in tail})}")
    cmd(g, rec, "UNLOCK")
    g.walk_to(0, -1102)                                  # far from the X edge: the model moves ~185 px from `end`
    m = settle(rec)
    model = P.follow_model(m["px"], m["pz"], hfw)
    g.check(max(abs(model[0] - end[0]), abs(model[1] - end[1])) >= 50 and abs(m["vx"] - model[0]) <= 1
            and abs(m["vy"] - model[1]) <= 1,
            "2.8 FOLLOW RESUMES: after the release a walk moves the view again, onto the follow model",
            f"view ({m['vx']},{m['vy']}) model {model}, was {end}")

    # 2.9 GIVE-BACK, cosine
    cmd(g, rec, "LOCK")
    here = settle(rec)
    end = P.follow_model(here["px"], here["pz"], hfw)
    away = (end[0] + 120 if end[0] < 384 else end[0] - 120, 200)
    cmd(g, rec, "MOVE1", *away)
    vs = (settle(rec)["vx"], rec.poll()["vy"])
    ta, _ = cmd(g, rec, "RELEASE", ad=16, at=8)
    rec.ticks(30)
    fit = _glide_fit(rec.between(ta, ta + 16), ta, vs, end, 16, cosine=True)
    print(f"[photo-rung0] 2.9 cosine release fit {vs} -> {end}: {json.dumps(fit)}")
    rec.notes["2.9 fit"] = fit
    tail = rec.between(ta + 17, ta + 30)
    g.check(fit[1]["worst"] <= 1 and fit[1]["n"] >= 6 and tail
            and all(abs(m["vx"] - end[0]) <= 1 and abs(m["vy"] - end[1]) <= 1 for m in tail),
            "2.9 GIVE-BACK (type 8): the release follows the engine's cosine ease over 16 ticks and ends on the follow "
            "point", f"worst {fit[1]['worst']} (per-render-frame {fit[2]['worst']}), rows {fit[1]['rows']}")

    # 2.10 NC-SVC: the board's recipe -- EnableCameraServices(0) first -- moves nothing; (1) recovers
    t_off, _ = cmd(g, rec, "SVC_OFF")
    v0 = settle(rec)
    png_a, _m, ta_ = rest_shot(g, rec, "s2-svcoff-a", ref)
    t_s, _ = cmd(g, rec, "MOVE1", 300, 200)
    rec.ticks(12)
    after = rec.between(t_s)
    png_b, _m, tb_ = rest_shot(g, rec, "s2-svcoff-b", ref)
    rec.notes["2.10 commanded tx (sanity)"] = rec.poll()["tx"]
    g.check(after and all((m["vx"], m["vy"]) == (v0["vx"], v0["vy"]) for m in after)
            and (ta_["ox"], ta_["oy"]) == (tb_["ox"], tb_["oy"]),
            "2.10 NC-SVC: after EnableCameraServices(0) the same MoveCamera(300, 200) is dropped -- the target is "
            "commanded but neither the readback nor the frame moves (the board's recipe is a no-op pan)",
            f"view {(v0['vx'], v0['vy'])}, after {sorted({(m['vx'], m['vy']) for m in after})}, frame "
            f"{(ta_['ox'], ta_['oy'])} -> {(tb_['ox'], tb_['oy'])}")
    t_on, _ = cmd(g, rec, "SVC_ON")
    rec.exclude.append((t_off, t_on))                    # the dropped move is 2.10's own check, not C-CORE's
    cmd(g, rec, "MOVE1", 300, 200)
    m = settle(rec)
    g.check((m["vx"], m["vy"]) == (300, 200), "2.10 RECOVERY: EnableCameraServices(1) and the same move lands",
            f"({m['vx']},{m['vy']})")
    cmd(g, rec, "RELEASE", ad=10, at=0)
    cmd(g, rec, "UNLOCK")
    settle(rec)
    registration(g, shots, hfw)


def registration(g, shots: dict, hfw: int) -> None:
    """C2-REG: between rest shots the balloons move by exactly the view's move, scaled to the screen: actors stay
    registered to the art during a scripted pan."""
    s = 720 / 224
    rows, bad = [], []
    pairs = [("spawn", "take"), ("take", "rel"), ("rel", "x100"), ("rel", "x700")]
    for a, b in pairs:
        if a not in shots or b not in shots:
            continue
        (_pa, ma, ta, ba), (_pb, mb, tb, bb) = shots[a], shots[b]
        dvx, dvy = mb["vx"] - ma["vx"], mb["vy"] - ma["vy"]
        dtx, dty = tb["ox"] - ta["ox"], tb["oy"] - ta["oy"]
        for x, y, _n in ba:
            px, py = x - s * dvx, y - s * dvy
            if not (40 < px < 1240 and 40 < py < 680):
                continue
            near = min(bb, key=lambda q: math.hypot(q[0] - px, q[1] - py), default=None)
            d = math.hypot(near[0] - px, near[1] - py) if near else 1e9
            rows.append((a, b, round(x), round(y), round(px), round(py), round(d, 1)))
            if d > 20:
                bad.append(rows[-1])
        if abs(dtx - dvx) > 1 or abs(dty - dvy) > 1:
            bad.append((a, b, "art", dtx, dty, dvx, dvy))
    print(f"[photo-rung0] C2-REG rows {rows}")
    g.check(len(rows) >= 3 and not bad, "C2-REG: across the pan the balloons move exactly with the view (within 20 px "
            "of the scaled move) and the art's registration moves by the same canvas px -- actors stay on the painting",
            f"{len(rows)} blob pairs; bad {bad}")


# ------------------------------------------------------------------- stage 3: the pan
def run_stage3(g, rec: Rec, cal: dict, ref) -> None:
    hfw = cal["hfw"]
    lo, hi = 160 + (2 * hfw - 320) // 2, 608 - (2 * hfw - 320) // 2        # the widescreen X window
    # 3.1 K0 (MODE 0, control on)
    t0 = rec.poll()["t"]
    m = hold_and_watch(g, rec, "right", 20)
    saw = [x for x in rec.between(t0) if x["keys"] & 2]
    rec.notes["3.1 nmc (sanity)"] = m["nmc"]
    g.check(bool(saw) and m["keys"] == 0, "3.1 K0: MODE 0 -- the hold reaches B_KEY and KEYS clears after",
            f"seen {len(saw)}, keys after {m['keys']}")
    g.walk_to(0, -1102)                                  # mid-window on both axes: every pan below starts unsaturated
    settle(rec)

    # 3.2 idle
    cmd(g, rec, "LOCK")
    poke(g, P.MODE, 1)
    b = settle(rec)
    rec.ticks(10)
    m = rec.poll()
    g.check(m["nmc"] == b["nmc"] and (m["vx"], m["vy"]) == (b["vx"], b["vy"])
            and (m["nr"], m["nl"], m["nd"], m["nu"]) == (0, 0, 0, 0),
            "3.2 IDLE: MODE 1 with nothing held issues no MoveCamera and the view stays put",
            f"nmc {b['nmc']} -> {m['nmc']}")

    # 3.3 PAN right
    b = settle(rec)
    png_a, _ma, ta = rest_shot(g, rec, "s3-pan-a", ref)
    m = hold_and_watch(g, rec, "right", 20)
    png_b, m, tb = rest_shot(g, rec, "s3-pan-b", ref)
    dn = m["nr"] - b["nr"]
    want = min(hi, b["vx"] + P.STEP * dn)
    g.check(dn >= 5 and m["vx"] == want and m["vx"] < hi and m["vx"] - b["vx"] == P.STEP * dn
            and m["vy"] == b["vy"] and abs(m["px"] - b["px"]) <= 1
            and abs(m["pz"] - b["pz"]) <= 1 and not m["control"] and abs((tb["ox"] - ta["ox"]) - (m["vx"] - b["vx"])) <= 1,
            "3.3 PAN: holding right pans the view exactly 4 px per polled tick, the locked player does not move, and "
            "the frame moves by the same canvas px",
            f"VX {b['vx']} -> {m['vx']} (want {want}, {dn} ticks), VY {b['vy']} -> {m['vy']}, player "
            f"({b['px']:.0f},{b['pz']:.0f}) -> ({m['px']:.0f},{m['pz']:.0f}), frame dx {tb['ox'] - ta['ox']}")

    # 3.4 X edge
    t0 = rec.poll()["t"]
    hold_and_watch(g, rec, "right", 200)
    during = rec.between(t0)
    png, m, t = rest_shot(g, rec, "s3-xedge", ref)
    edge = [x for x in during if x["vx"] == hi and x["txp"] == hi + P.STEP]
    g.check(max(x["vx"] for x in during) == hi and edge and abs(t["ox"] - (hi - hfw)) <= 1,
            "3.4 X-EDGE: held right the view stops at the widescreen edge 569 while the relative target reads 573 "
            "(the engine's issue clamp holds it; the frame sits at the canvas edge)",
            f"max VX {max(x['vx'] for x in during)}, edge samples {len(edge)}, tmpl.x {t['ox']}")
    nl0 = rec.poll()["nl"]
    m = hold_and_watch(g, rec, "left", 4)
    dn = m["nl"] - nl0
    g.check(dn >= 1 and m["vx"] == hi - P.STEP * dn, "3.4 NO WIND-UP: the relative pan leaves the edge on the first "
            "left tick", f"VX {m['vx']} after {dn} left ticks")

    # 3.5 Y edges
    t0 = rec.poll()["t"]
    hold_and_watch(g, rec, "down", 150)
    during = rec.between(t0)
    png, m, t = rest_shot(g, rec, "s3-ybottom", ref)
    rec.notes["3.5 ty at the bottom (sanity)"] = m["ty"]
    ok_b = max(x["vy"] for x in during) == 336 and m["vy"] == 336 and abs(t["oy"] - 224) <= 1 \
        and t["offart_bottom"] <= 1
    t0 = rec.poll()["t"]
    hold_and_watch(g, rec, "up", 200)
    during = rec.between(t0)
    png, m2, t2 = rest_shot(g, rec, "s3-ytop", ref)
    ok_t = min(x["vy"] for x in during) == 112 and m2["vy"] == 112 and abs(t2["oy"]) <= 1 and t2["offart_top"] <= 1
    g.check(ok_b and ok_t, "3.5 Y-EDGES: the SCRIPT's clamp stops the view at 336 and 112 (the engine clamps nothing "
            "in Y, 2.6) -- the frame reaches the painting's bottom and top edges and never past them",
            f"bottom VY {m['vy']} TY {m['ty']} tmpl.y {t['oy']} off {t['offart_bottom']}; top VY {m2['vy']} tmpl.y "
            f"{t2['oy']} off {t2['offart_top']}")

    # 3.6 NC-LOCK: the same pan with the player unlocked walks the player too
    cmd(g, rec, "UNLOCK")
    b = settle(rec)
    m = hold_and_watch(g, rec, "left", 20)
    dn = m["nl"] - b["nl"]
    cmd(g, rec, "LOCK")
    g.check(b["px"] - m["px"] >= 150 and m["vx"] == max(lo, b["vx"] - P.STEP * dn),
            "3.6 NC-LOCK: unlocked, the same hold walks the player AND pans -- so in 3.3 it was the lock, not the poll, "
            "that kept the player still", f"player x {b['px']:.0f} -> {m['px']:.0f}, VX {b['vx']} -> {m['vx']} "
            f"({dn} ticks)")

    # 3.7 wind-up of the absolute form
    poke(g, P.MODE, 3)
    hold_and_watch(g, rec, "right", 200)
    m = settle(rec)
    t0 = rec.poll()["t"]
    rec.notes["3.7 tx at the edge (sanity)"] = m["tx"]
    ok0 = m["vx"] == hi
    hold_and_watch(g, rec, "left", 40)
    during = [x for x in rec.between(t0) if x["issp"] == 1]
    pinned = [x for x in during if hi < x["txp"] < 608 and x["vx"] == hi]
    first = [x for x in during if x["txp"] < hi]
    g.check(ok0 and len(pinned) >= 5 and bool(first) and first[0]["vx"] == first[0]["txp"]
            and first[0]["txp"] >= hi - 2 * P.STEP,
            "3.7 WIND-UP: the absolute form's target runs to the script clamp 608 behind the engine's 569, so the first "
            "left presses move nothing until the target comes back under the edge",
            f"TX/VX at the edge {(m['tx'], m['vx'])}, pinned samples {len(pinned)}, first under "
            f"{[(x['txp'], x['vx']) for x in first[:1]]}")

    # 3.8 exit
    poke(g, P.MODE, 0)
    cmd(g, rec, "RELEASE", ad=20, at=0)
    rec.ticks(25)
    cmd(g, rec, "UNLOCK")
    g.walk_to(0, -1102)
    m = settle(rec)
    model = P.follow_model(m["px"], m["pz"], hfw)
    g.check(abs(m["vx"] - model[0]) <= 1 and abs(m["vy"] - model[1]) <= 1 and m["control"],
            "3.8 EXIT: release + unlock hands the view back -- follow tracks the walking player again",
            f"view ({m['vx']},{m['vy']}) model {model}")

# ------------------------------------------------------------------- stage 4: hides and the grade
def _look(png, m) -> dict:
    """Which balloons are drawn (by screen x at the spawn view: L ~143, C ~621, R ~1095) and how much of the player."""
    cls = set()
    for x, _y, _n in P.red_bodies(png):
        cls.add("L" if x < 380 else "C" if x < 860 else "R")
    return {"cls": cls, "player": P.player_px(png, m["psx"], m["psy"])}


def run_stage4(g, rec: Rec, cal: dict, ref) -> None:
    g.walk_to(0, -1102)                                  # the spawn view: all three balloons and the player on screen
    settle(rec)
    cmd(g, rec, "LOCK")
    png, m0, t0 = rest_shot(g, rec, "s4-base", ref)
    base = _look(png, m0)
    view = (m0["vx"], m0["vy"])
    print(f"[photo-rung0] 4 base: view {view}, FLAGS {m0['flags']}, look {base}")
    g.check(m0["flags"] == 15 and base["cls"] == {"L", "C", "R"} and base["player"] >= 200,
            "4.0 BASE: FLAGS reads all four show bits, the three balloons and the player are drawn",
            f"FLAGS {m0['flags']}, {base}")
    vis, pvis, flags = set(base["cls"]), True, m0["flags"]
    saved = None
    rows = []
    # (label, command, the flags it should leave, what it should leave drawn) -- expectations follow the MEASURED state
    # before each step, so a show that fails is reported once and does not poison the steps after it
    steps = [
        ("4.4 FLAG HIDE C", "FLAG_HIDE_C", lambda f: f & ~2, lambda v, p: (v - {"C"}, p)),
        ("4.4 FLAG SHOW C", "FLAG_SHOW_C", lambda f: f | 2, lambda v, p: (v | {"C"}, p)),
        ("4.3 MESH HIDE L", "MESH_HIDE_L", lambda f: f, lambda v, p: (v - {"L"}, p)),
        ("4.3 MESH SHOW L", "MESH_SHOW_L", lambda f: f, lambda v, p: (v | {"L"}, p)),
        ("4.5 FLAG HIDE PLAYER", "FLAG_HIDE_P", lambda f: f & ~1, lambda v, p: (v, False)),
        ("4.5 FLAG SHOW PLAYER", "FLAG_SHOW_P", lambda f: f | 1, lambda v, p: (v, True)),
        ("4.1 HIDE ALL", "HIDEALL", lambda f: 0, lambda v, p: (set(), False)),
        ("4.2 SHOW ALL", "SHOWALL", None, None),
    ]
    for label, name, fl, dr in steps:
        if name == "HIDEALL":
            saved = (flags, set(vis), pvis)
        want_f = saved[0] if name == "SHOWALL" else fl(flags)
        want_v, want_p = (saved[1], saved[2]) if name == "SHOWALL" else dr(vis, pvis)
        t_a, _ = cmd(g, rec, name)
        try:
            mf = rec.until(lambda m: m["t"] > t_a and m["flags"] == want_f, 4, f"FLAGS {want_f} after {name}")
        except Stop:
            mf = rec.poll()
        png, m, _t = rest_shot(g, rec, f"s4-{name.lower()}", ref)
        look = _look(png, m)
        pdrawn = look["player"] >= 200 if want_p else look["player"] <= 60
        ok = mf["flags"] == want_f and look["cls"] == want_v and pdrawn and (m["vx"], m["vy"]) == view
        rows.append((label, m["flags"], sorted(look["cls"]), look["player"]))
        g.check(ok, f"{label}: FLAGS {want_f}, balloons drawn {sorted(want_v)}, player "
                f"{'drawn' if want_p else 'hidden'} -- measured on the frame, the daemon kept running (it acked)",
                f"FLAGS {mf['flags']}, balloons {sorted(look['cls'])}, player px {look['player']}, view "
                f"{(m['vx'], m['vy'])}")
        flags, vis, pvis = mf["flags"], look["cls"], look["player"] >= 200
    rec.notes["stage 4 hides"] = rows
    r_rows = [r for r in rows if r[0] != "4.1 HIDE ALL"]
    g.check(all("R" in r[2] and r[1] & 8 for r in r_rows),
            "NC-HIDE: balloon R, never a target, stays drawn with its show bit set through every step but hide-all",
            str(rows))

    # 4.6 the held grade
    w0, th0 = P.white_median(png, t0["ox"], t0["oy"], thirds=True)
    cmd(g, rec, "GRADE")
    rec.ticks(12)
    png1, m1, _t = rest_shot(g, rec, "s4-grade", ref)
    w1, th1 = P.white_median(png1, t0["ox"], t0["oy"], thirds=True)
    rec.frames(120)
    png2, _m2, _t = rest_shot(g, rec, "s4-grade-held", ref)
    w2 = P.white_median(png2, t0["ox"], t0["oy"])
    cmd(g, rec, "GRADE_CLEAR")
    rec.ticks(12)
    png3, _m3, t3 = rest_shot(g, rec, "s4-grade-clear", ref)
    w3 = P.white_median(png3, t0["ox"], t0["oy"])
    d = [w1[i] - w0[i] for i in range(3)]
    rec.notes["4.6 grade"] = {"white before": w0, "graded": w1, "thirds": th1, "held 120f": w2, "cleared": w3,
                              "gamma-space prediction": (235, 171, 107), "linear-space prediction": "~(235,228,206)"}
    print(f"[photo-rung0] 4.6 grade: white {w0} -> {w1} (thirds {th1}) -> held {w2} -> cleared {w3}")
    g.check(abs(d[0]) <= 3 and d[1] <= -5 and d[2] <= -20 and d[2] < d[1]
            and all(max(abs(a - b) for a, b in zip(t, w1)) <= 3 for t in th1),
            "4.6 GRADE: a SUB FadeFilter (0, 64, 128) holds a warm tint over the whole frame -- red untouched, blue "
            "cut deepest, the same in every third", f"white {w0} -> {w1} (d {d}), thirds {th1}")
    g.check(max(abs(a - b) for a, b in zip(w1, w2)) <= 2,
            "4.6 HELD: the grade does not drift over 120 frames (FadeFilter latches its colour)", f"{w1} -> {w2}")
    g.check(max(abs(a - b) for a, b in zip(w3, w0)) <= 3 and (t3["ox"], t3["oy"]) == (t0["ox"], t0["oy"]),
            "4.6 CLEAR: the same channel at (0, 0, 0) restores the frame, which registers where it was",
            f"{w0} -> {w3}, frame {(t3['ox'], t3['oy'])}")
    cmd(g, rec, "UNLOCK")


# ------------------------------------------------------------------- stage 5: the modal loop, driven by buttons only
def _press(g, rec: Rec, button: str) -> dict:
    """One edge: press for 2 frames, then let a few ticks pass so the next press is a new edge."""
    g.press(button, 2)
    return rec.ticks(4)


def run_stage5(g, rec: Rec, cal: dict, ref) -> None:
    hfw = cal["hfw"]
    hi = 608 - (2 * hfw - 320) // 2
    g.walk_to(0, -1102)                                  # the last walk: walk_to may hold Cancel (its walk modifier)
    png0, m0, t0 = rest_shot(g, rec, "s5-base", ref)
    base, w0, e0 = _look(png0, m0), P.white_median(png0, t0["ox"], t0["oy"]), m0["edges"]
    v0 = (m0["vx"], m0["vy"])
    print(f"[photo-rung0] 5 base: view {v0}, look {base}, white {w0}, edges {e0}")

    # CLOSED: the photo buttons do nothing until Select opens it
    for b in ("r1", "l1", "cancel"):
        _press(g, rec, b)
    png, m, t = rest_shot(g, rec, "s5-closed", ref)
    look = _look(png, m)
    g.check(m["modal"] == 0 and m["flags"] == 15 and look["cls"] == {"L", "C", "R"} and look["player"] >= 200
            and max(abs(a - b) for a, b in zip(P.white_median(png, t0["ox"], t0["oy"]), w0)) <= 3 and m["uc"] == 1
            and (m["vx"], m["vy"]) == v0 and m["edges"] - e0 == 256 + 4096 + 16,
            "5.0 CLOSED: R1 / L1 / Cancel edges reach the poll (EDGES counts them) but change nothing until Select",
            f"modal {m['modal']}, FLAGS {m['flags']}, look {look}, uc {m['uc']}, edges +{m['edges'] - e0}")

    # OPEN on a Select edge: lock, take the view it is already on -- no jump
    t_o = rec.poll()["t"]
    g.press("select", 2)
    mo = rec.until(lambda m: m["modal"] & 1, 4, "photo mode to open")
    rec.ticks(6)
    png, m, t = rest_shot(g, rec, "s5-open", ref)
    after = rec.between(mo["t"])
    g.check(m["uc"] == 0 and not rec.poll()["control"] and all((x["vx"], x["vy"]) == v0 for x in after)
            and (t["ox"], t["oy"]) == (t0["ox"], t0["oy"]) and m["edges"] - e0 == 256 + 4096 + 16 + 1,
            "5.1 OPEN: one Select edge locks the player and takes the camera where it already is -- no jump on the "
            "readback or the frame", f"uc {m['uc']}, views {sorted({(x['vx'], x['vy']) for x in after})}, frame "
            f"{(t['ox'], t['oy'])} vs {(t0['ox'], t0['oy'])}, opened at tick {mo['t']} (pressed after {t_o})")

    # HIDE cycle: L by mesh, C by flags, the player by flags, a 4th press nothing
    want = [({"C", "R"}, True, 15, 1 + 4), ({"R"}, True, 13, 1 + 8), ({"R"}, False, 12, 1 + 12),
            ({"R"}, False, 12, 1 + 12)]
    rows = []
    for i, (cls, pdr, fl, md) in enumerate(want, 1):
        _press(g, rec, "r1")
        try:
            rec.until(lambda m: m["modal"] == md and m["flags"] == fl, 3, f"R1 #{i}")
        except Stop:
            pass
        png, m, t = rest_shot(g, rec, f"s5-r1-{i}", ref)
        look = _look(png, m)
        ok = look["cls"] == cls and (look["player"] >= 200) == pdr and m["flags"] == fl and m["modal"] == md
        rows.append((i, sorted(look["cls"]), look["player"], m["flags"], m["modal"], ok))
    print(f"[photo-rung0] 5.2 hide cycle {rows}")
    g.check(all(r[-1] for r in rows), "5.2 HIDE CYCLE: R1 hides balloon L (mesh), then C (flags), then the player "
            "(flags); a 4th R1 changes nothing", str(rows))

    # PAN while open (grade off): exact 4 px a polled tick, the hidden player does not move
    b = settle(rec)
    _p, _m, ta = rest_shot(g, rec, "s5-pan-a", ref)
    m = hold_and_watch(g, rec, "right", 20)
    _p, m, tb = rest_shot(g, rec, "s5-pan-b", ref)
    dn = m["nr"] - b["nr"]
    g.check(dn >= 5 and m["vx"] == min(hi, b["vx"] + P.STEP * dn) and m["vx"] < hi and m["vy"] == b["vy"]
            and abs(m["px"] - b["px"]) <= 1 and abs(m["pz"] - b["pz"]) <= 1
            and abs((tb["ox"] - ta["ox"]) - (m["vx"] - b["vx"])) <= 1,
            "5.3 PAN: the d-pad pans the open view 4 px a polled tick, the frame follows, the player stays put",
            f"VX {b['vx']} -> {m['vx']} ({dn} ticks), frame dx {tb['ox'] - ta['ox']}, player "
            f"({b['px']:.0f},{b['pz']:.0f}) -> ({m['px']:.0f},{m['pz']:.0f})")

    # GRADE toggles on L1, at the panned view (registered on its ungraded shot)
    grades = []
    for i, on in enumerate((True, False, True), 1):
        _press(g, rec, "l1")
        try:
            rec.until(lambda m: bool(m["modal"] & 2) == on, 3, f"L1 #{i}")
        except Stop:
            pass
        rec.ticks(12)
        png, m, _t = rest_shot(g, rec, f"s5-l1-{i}", ref)
        w = P.white_median(png, tb["ox"], tb["oy"])
        good = (abs(w[0] - 235) <= 3 and w[1] <= 235 - 40 and w[2] <= 235 - 90) if on \
            else max(abs(a - b) for a, b in zip(w, w0)) <= 3
        grades.append((i, on, w, bool(m["modal"] & 2), good))
    print(f"[photo-rung0] 5.4 grade toggles {grades}")
    g.check(all(r[-1] and r[1] == r[3] for r in grades), "5.4 GRADE: L1 toggles the held warm grade on, off, on",
            str(grades))

    # EXIT on Cancel: show all, clear the grade, cosine release to the follow point, unlock
    here = settle(rec)
    vs = (here["vx"], here["vy"])
    end = P.follow_model(here["px"], here["pz"], hfw)
    g.press("cancel", 2)
    mx = rec.until(lambda m: m["modal"] == 0 and m["rt"] >= 1, 4, "photo mode to close")
    rec.ticks(30)
    t_r = mx["t"] - (mx["rt"] - 1)                        # the tick the release was issued in
    fit = _glide_fit(rec.between(t_r, t_r + 16), t_r, vs, end, 16, cosine=True)
    rec.notes["5.5 release fit"] = fit
    png, m, t = rest_shot(g, rec, "s5-exit", ref)
    look = _look(png, m)
    w = P.white_median(png, t["ox"], t["oy"])
    print(f"[photo-rung0] 5.5 exit: release {vs} -> {end} fit worst {fit[1]['worst']} (n {fit[1]['n']}); view "
          f"{(m['vx'], m['vy'])}, look {look}, white {w}")
    g.check(m["flags"] == 15 and look["cls"] == {"L", "C", "R"} and look["player"] >= 200
            and max(abs(a - b) for a, b in zip(w, w0)) <= 3 and m["uc"] == 1 and rec.poll()["control"]
            and fit[1]["worst"] <= 1 and fit[1]["n"] >= 6 and abs(m["vx"] - end[0]) <= 1 and abs(m["vy"] - end[1]) <= 1
            and abs(t["ox"] - t0["ox"]) <= 1 and abs(t["oy"] - t0["oy"]) <= 1,
            "5.5 EXIT: one Cancel edge shows everything it hid, clears the grade, eases the camera back to the player "
            "(ReleaseCamera 16, type 8) and hands control back -- the frame is where photo mode found it",
            f"FLAGS {m['flags']}, look {look}, white {w}, uc {m['uc']}, release worst {fit[1]['worst']} over "
            f"{fit[1]['n']}, view {(m['vx'], m['vy'])} vs {end}, frame {(t['ox'], t['oy'])} vs {(t0['ox'], t0['oy'])}")
    edges = m["edges"] - e0
    want_e = (256 + 4096 + 16) + 1 + 4 * 256 + 3 * 4096 + 16
    g.check(edges == want_e, "5.6 EDGES: every photo-button press was exactly one edge, open or closed",
            f"+{edges} (want +{want_e})")
    g.walk_to(600, -1102)
    m = settle(rec)
    model = P.follow_model(m["px"], m["pz"], hfw)
    g.check(abs(m["vx"] - model[0]) <= 1 and abs(m["vy"] - model[1]) <= 1 and abs(m["vx"] - end[0]) >= 50,
            "5.7 FOLLOW: after photo mode the camera follows the walking player again", f"view ({m['vx']},{m['vy']}) "
            f"model {model}")


def core(g, rec: Rec, hfw: int, min_rows: int) -> None:
    lo, hi = 160 + (2 * hfw - 320) // 2, 608 - (2 * hfw - 320) // 2
    inside = lambda t: any(a < t <= b for a, b in rec.exclude)          # noqa: E731
    rows = [m for m in rec.s.values() if m["issp"] == 1 and not inside(m["t"])]
    want = {t + 1 for t in rec.one_tick if not inside(t + 1)}
    missing = sorted(want - {m["t"] for m in rows})
    min_rows = max(min_rows, len(want) - 2)
    rec.notes["C-CORE"] = {"rows": len(rows), "dispatched one-tick moves": len(want), "unobserved": missing}
    off = [(m["t"], (m["txp"], m["typ"]), (m["vx"], m["vy"])) for m in rows
           if (m["vx"], m["vy"]) != (min(max(m["txp"], lo), hi), m["typ"])]
    near = [r for r in off if abs(r[2][0] - min(max(r[1][0], lo), hi)) <= 1 and abs(r[2][1] - r[1][1]) <= 1]
    g.check(len(rows) >= min_rows and len(off) == len(near) and len(off) <= 4,
            "C-CORE: on EVERY sample whose previous tick issued a one-tick MoveCamera, the view == that target with X "
            "clamped to the widescreen window and Y untouched (at most a few take-over -1s)",
            f"{len(rows)} samples ({len(want)} dispatched one-tick moves, unobserved by poll gaps {missing}), "
            f"{len(off)} off by <= 1: {off[:6]}")


def run(g) -> None:
    try:
        stage, pred = preflight(g)
    except (Stop, SystemExit) as e:
        g.check(False, "PREFLIGHT", str(e))
        return
    g.note(f"photo mode rung 0, stage {stage}")
    ref = P.canvas_labels()
    g.newgame()
    mark = g.log_mark()
    g.warp(P.FIELD_ID)
    g.wait_for(lambda s: s.field_id == P.FIELD_ID, timeout=60, what="field 30955")
    g.state_every(1)
    _watch(g)
    rec = Rec(g)
    try:
        cal = calibrate(g, rec, pred, ref, walks=True)
        if stage == 2:
            run_stage2(g, rec, cal, ref)
        elif stage == 3:
            run_stage3(g, rec, cal, ref)
        elif stage == 4:
            run_stage4(g, rec, cal, ref)
        elif stage == 5:
            run_stage5(g, rec, cal, ref)
        if stage in (2, 3, 5):
            core(g, rec, cal["hfw"], min_rows={2: 6, 3: 30, 5: 5}[stage])
    except (Stop, HarnessError) as e:
        g.check(False, "STOPPED", f"{type(e).__name__}: {e}")
    finally:
        (g.run_dir / "photo_samples.json").write_text(json.dumps(rec.s, default=str), encoding="utf-8")
        (g.run_dir / "photo_run.json").write_text(json.dumps({"stage": stage, "cmds": rec.log, "exclude": rec.exclude,
                                                              "notes": rec.notes}, default=str, indent=1),
                                                  encoding="utf-8")
        every = g.exceptions_since(mark)
        ours = [e for e in every if e.name in THROWS
                and (not e.trace or any(k in fr for fr in e.trace for k in WHERE))]
        print(f"[photo-rung0] exceptions since the mark: {len(every)}")
        g.check(not ours, "NC-THROW: no NullReference / InvalidCast / IndexOutOfRange / DivideByZero through the "
                "event engine, the evaluator or FieldMap", str([(e.name, e.where) for e in ours[:5]]))
        # no g.quit(): Session.stop quits a game it launched and never one it attached to
