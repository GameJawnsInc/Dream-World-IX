"""PHOTO MODE, RUNG 1 -- the KIT feature (`[photo]`) in-game, measured on bench 30956.

    py studies/photo-mode/photo1_bench.py deploy
    py tools/play.py studies/photo-mode/rung1_photo.py --label photo-rung1

The field is authored only through `[photo]`; the kit's daemon is what runs. A study-local observer (photo1_bench) mirrors
the view, control, keys, d-pad tick counts and every hide target's show bit, and plays foreign events. Rest shots are
registered against the seeded canvas (rung 0's `tmpl`), balloons found as red bodies, the grade read on white cells.

PRE   P0 30956 served by FF9CustomMap alone; P-BYTES every language's photo entry == photo.entry_bytes over the parts read
      back off the live bytes, and the observer is seated; P-INI widescreen on, no stabilizer
C1    the spawn view (384, 286) and its frame (185, 174)
K1    THE SETTLE: control back for 10 ticks -> Select does not open; after 40 -> it opens, with no jump
K2    THE HIDE CYCLE: R1 steps balloon L, balloon C, the guard NPC (the first NPC flags-hide in-game), the player, "all";
      a 6th R1 changes nothing -- show bits and the frame agree
K3    THE GRADE: L1 on (235,171,107), L1 off (235,235,235)
K4    THE PAN: exactly 4 px per polled tick with the player locked, the frame moving the same
K5    THE CLOSE: everything back (show bits and frame), the grade clear, control back, the camera eased onto the player
K6    THE WALKING EXIT: running through the glide, no snap (largest step <= 30 px), resting on the follow point
Y1    A DIALOGUE: while it is open, and for the settle after it, Select does nothing; then it opens
Y2    A FOREIGN EnableMove while open: photo mode closes itself with a full restore
Y3    THE SCENE BIT (MAP 110) while open: it closes; while the bit is up Select does nothing
Y4    A TARGET HIDDEN BEFORE photo mode opened stays hidden after the close (the exact restore)
Y5    RE-OPEN MID-GLIDE: the camera holds
NC-THROW
"""
from __future__ import annotations

import json
import math
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
sys.path.insert(0, str(HERE))
import photo0_bench as P0  # noqa: E402  (the instruments: tmpl, red_bodies, player_px, white_median, follow_model)
import photo1_bench as B  # noqa: E402
from ff9mapkit.config import LANGS, ModLayout  # noqa: E402
from ff9mapkit.content import photo  # noqa: E402
try:
    from harness import HarnessError
except ImportError:
    from tools.harness import HarnessError  # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
THROWS = {"NullReferenceException", "InvalidCastException", "IndexOutOfRangeException", "DivideByZeroException",
          "ArgumentOutOfRangeException", "OverflowException"}
WHERE = ("EventEngine", "EBin", "FieldMap")
ALL = sum(B.FLAG_BIT.values())                    # 63: every target shown


class Stop(Exception):
    pass


def _i16(st, off: int) -> int:
    v = sum(1 << i for i in range(16) if st.flag(off * 8 + i))
    return v - 0x10000 if v & 0x8000 else v


class Rec:
    def __init__(self, g):
        self.g, self.s, self.notes = g, {}, {}

    def poll(self) -> dict:
        st = self.g.state
        if st.armed is False:
            raise Stop("the harness agent stopped publishing")
        m = {k: _i16(st, B.O16[k]) for k in B.WATCHED}
        m.update(frame=st.frame, px=st.player_x, pz=st.player_z, control=st.control, fading=st.fading,
                 dialog=st.dialog_open)
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

    def ticks(self, n: int, timeout: float = 20) -> dict:
        t0 = self.poll()["t"]
        return self.until(lambda m: m["t"] >= t0 + n, timeout, f"{n} ticks")

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


def shot(g, rec: Rec, name: str, ref):
    for _ in range(3):
        m0 = settle(rec)
        png = g.shot(name)
        m1 = settle(rec, n=2)
        if (m1["vx"], m1["vy"]) == (m0["vx"], m0["vy"]):
            return png, m1, P0.tmpl(png, ref)
    raise Stop(f"{name}: the view would not hold still")


def cmd(g, rec: Rec, name: str, timeout: float = 5) -> dict:
    a = rec.poll()["ack"]
    g.send(f"byte {B.CMD} {B.CMDS[name]}")
    m = rec.until(lambda m: m["ack"] == a + 1, timeout, f"the observer to ack {name}")
    if m["last"] != B.CMDS[name]:
        raise Stop(f"{name}: the observer refused it ({m['last']})")
    return m


def press(g, rec: Rec, button: str, frames: int = 2) -> dict:
    g.press(button, frames)
    return rec.ticks(3)


def hold(g, rec: Rec, button: str, frames: int) -> dict:
    f0 = rec.poll()["frame"]
    g.hold(button, frames)
    rec.until(lambda m: m["frame"] >= f0 + frames + 6, frames / 20 + 20, f"the {button} hold")
    return settle(rec)


def is_open(m) -> bool:
    return m["uc"] == 0


def opened(g, rec: Rec) -> dict:
    """Press Select and wait for photo mode's lock."""
    press(g, rec, "select")
    return rec.until(is_open, 3, "photo mode to open")


def closed(g, rec: Rec) -> dict:
    press(g, rec, "cancel")
    m = rec.until(lambda m: m["uc"] == 1 and m["flags"] == ALL, 4, "photo mode to close with a full restore")
    rec.ticks(25)
    return m


BALLOONS: dict = {}                               # name -> (x, y) on screen at the spawn view, measured in C1
BALLOON_PX = 600                                  # a balloon body is 771-1158 px here; the talker's ribbon 288-300


def _cls(png, ox: int = 0) -> set:
    """Which balloons are drawn: a red body within 45 px of where C1 measured that balloon (the spawn view -- every
    shot that asks is taken there). By position, not by an x band: the talker's red boots and hat ribbon make a red
    body of their own, around 300 px, as she idles."""
    out = set()
    for x, y, _n in P0.red_bodies(png, min_px=BALLOON_PX):
        for name, (bx, by) in BALLOONS.items():
            if math.hypot(x - bx, y - by) <= 45:
                out.add(name)
    return out


# ------------------------------------------------------------------- preflight
def preflight(g) -> None:
    folders = [p.parent.name for p in GAME.glob("*/DictionaryPatch.txt")
               if re.search(rf"FieldScene {B.FIELD_ID}\b", p.read_text(encoding="utf-8", errors="replace"))]
    g.check(folders == ["FF9CustomMap"], "P0: 30956 is served by FF9CustomMap alone", str(folders))
    live = ModLayout(GAME / B.MOD_FOLDER)
    raw = B.raw()
    rows = {}
    for lang in LANGS:
        p = live.eb_path(lang, f"EVT_{B.FIELD_NAME}.eb.bytes")
        if p.exists():
            eb = p.read_bytes()
            try:
                rows[lang] = (B.photo_slot(eb, raw, lang), B.is_patched(eb, raw))
            except SystemExit as e:
                rows[lang] = (str(e), False)
    ok = bool(rows) and len({r[0] for r in rows.values()}) == 1 and all(isinstance(r[0], int) and r[1]
                                                                          for r in rows.values())
    g.check(ok, "P-BYTES: every language runs the KIT's photo daemon (== its language's photo.entry_bytes over the parts "
            "read back off the live bytes) and carries the observer", str(rows))
    text = (GAME / "Memoria.ini").read_text(encoding="utf-8", errors="replace")
    ini = {k: int(re.search(rf"^\s*{k}\s*=\s*(-?\d+)", text, re.M).group(1)) for k in ("WidescreenSupport",
                                                                                     "CameraStabilizer")}
    g.check(ini == {"WidescreenSupport": 1, "CameraStabilizer": 0}, "P-INI: widescreen on, no stabilizer", str(ini))


def _watch(g) -> None:
    bits = []
    for k in B.WATCHED:
        bits += [B.O16[k] * 8 + i for i in range(16)]
    g.watch(*bits)


# ------------------------------------------------------------------- the kit phases
def kit_phases(g, rec: Rec, ref) -> None:
    rec.until(lambda m: m["t"] > 5 and m["uc"] == 1 and m["control"], 60, "the field's entry to finish")
    rec.ticks(45)                                  # the kit's entry fade-in is a SUB FadeFilter ramp the harness's
    m = settle(rec)                                # `fading` does not report: a shot before it ends is darkened
    png0, m0, t0 = shot(g, rec, "k-spawn", ref)
    w0 = P0.white_median(png0, t0["ox"], t0["oy"])
    red = sorted(P0.red_bodies(png0, min_px=BALLOON_PX))
    BALLOONS.update({n: (x, y) for n, (x, y, _k) in zip(("L", "C", "R"), sorted(red, key=lambda b: b[0]))
                     if len(red) >= 3})
    g.check((m0["vx"], m0["vy"]) == (384, 286) and (t0["ox"], t0["oy"]) == (185, 174) and m0["flags"] == ALL
            and max(abs(v - 235) for v in w0) <= 3 and len(red) == 3,
            "C1: the spawn view (384, 286), drawn at (185, 174), undimmed (white cells 235); every hide target shown "
            "and the three balloons found", f"view ({m0['vx']},{m0['vy']}) frame ({t0['ox']},{t0['oy']}) white {w0} "
            f"flags {m0['flags']} balloons {BALLOONS}")

    # K1 the settle
    cmd(g, rec, "DISABLEMOVE")
    rec.ticks(60)
    cmd(g, rec, "ENABLEMOVE")
    rec.ticks(10)
    press(g, rec, "select")
    early = rec.ticks(8)
    rec.ticks(40)
    mo = opened(g, rec)
    rec.ticks(6)
    png, m, t = shot(g, rec, "k1-open", ref)
    after = rec.between(mo["t"])
    g.check(early["uc"] == 1 and all((x["vx"], x["vy"]) == (m0["vx"], m0["vy"]) for x in after)
            and (t["ox"], t["oy"]) == (t0["ox"], t0["oy"]) and not rec.poll()["control"],
            "K1 THE SETTLE: 10 ticks after control came back Select did nothing; 40 ticks later it opened photo mode, "
            "locking the player with no jump on the readback or the frame",
            f"early uc {early['uc']}; views after open {sorted({(x['vx'], x['vy']) for x in after})}; frame "
            f"{(t['ox'], t['oy'])}")

    # K2 the hide cycle
    want = [(ALL - 2, {"C", "R"}, True), (ALL - 2 - 4, {"R"}, True), (ALL - 2 - 4 - 16, {"R"}, True),
            (ALL - 2 - 4 - 16 - 1, {"R"}, False), (0, set(), False), (0, set(), False)]
    rows = []
    for i, (fl, cls, pdrawn) in enumerate(want, 1):
        press(g, rec, "r1")
        try:
            rec.until(lambda m, fl=fl: m["flags"] == fl, 3, f"R1 #{i}")
        except Stop:
            pass
        png, m, t = shot(g, rec, f"k2-r1-{i}", ref)
        look = _cls(png, t0["ox"])
        pp = P0.player_px(png, m["psx"], m["psy"])
        rows.append((i, m["flags"], sorted(look), pp, m["flags"] == fl and look == cls and (pp >= 200) == pdrawn))
    print(f"[photo-rung1] K2 {rows}")
    g.check(all(r[-1] for r in rows), "K2 THE HIDE CYCLE: R1 hid balloon L, balloon C, the guard NPC, the player, then "
            "\"all\" (balloon R and the talker); a 6th R1 changed nothing -- the show bits and the frame agree", str(rows))

    # K3 the grade
    press(g, rec, "l1")
    rec.ticks(12)
    png, _m, _t = shot(g, rec, "k3-grade-on", ref)
    won = P0.white_median(png, t0["ox"], t0["oy"])
    press(g, rec, "l1")
    rec.ticks(12)
    png, _m, _t = shot(g, rec, "k3-grade-off", ref)
    woff = P0.white_median(png, t0["ox"], t0["oy"])
    g.check(max(abs(a - b) for a, b in zip(won, (235, 171, 107))) <= 3 and max(abs(a - b) for a, b in zip(woff, w0)) <= 3,
            "K3 THE GRADE: L1 lays the warm tint (white -> 235,171,107) and L1 lifts it", f"{w0} -> {won} -> {woff}")

    # K4 the pan (everything hidden: the frame is pure art)
    b = settle(rec)
    _p, _m, ta = shot(g, rec, "k4-a", ref)
    hold(g, rec, "right", 20)
    _p, m, tb = shot(g, rec, "k4-b", ref)
    dn = m["nr"] - b["nr"]
    g.check(dn >= 5 and m["vx"] == b["vx"] + photo.STEP * dn and m["vy"] == b["vy"] and m["vx"] < 569
            and abs((tb["ox"] - ta["ox"]) - (m["vx"] - b["vx"])) <= 1 and abs(m["px"] - b["px"]) <= 1,
            "K4 THE PAN: exactly 4 px per polled tick, the player locked, the frame moving the same",
            f"VX {b['vx']} -> {m['vx']} over {dn} ticks, frame dx {tb['ox'] - ta['ox']}, player dx {m['px'] - b['px']:.0f}")

    # K5 the close
    vs = (m["vx"], m["vy"])
    t_c = rec.poll()["t"]
    closed(g, rec)
    png, m, t = shot(g, rec, "k5-closed", ref)
    trace = [(x["t"] - t_c, x["vx"]) for x in rec.between(t_c, t_c + 25)]
    g.check(m["flags"] == ALL and _cls(png, t["ox"]) == {"L", "C", "R"} and P0.player_px(png, m["psx"], m["psy"]) >= 200
            and max(abs(a - b) for a, b in zip(P0.white_median(png, t["ox"], t["oy"]), w0)) <= 3 and m["uc"] == 1
            and (m["vx"], m["vy"]) == (m0["vx"], m0["vy"]) and (t["ox"], t["oy"]) == (t0["ox"], t0["oy"]),
            "K5 THE CLOSE: everything hidden is back, the tint is gone, control is back and the camera has eased from "
            "the panned view onto the player -- the frame is where photo mode found it",
            f"from {vs}: trace {trace[:18]}; flags {m['flags']} view ({m['vx']},{m['vy']}) frame {(t['ox'], t['oy'])}")
    rec.notes["K5 trace"] = trace

    # K6 the walking exit
    g.walk_to(600, -1102)
    settle(rec)
    opened(g, rec)
    hold(g, rec, "left", 20)
    here = settle(rec)
    x0 = here["px"]
    t_c = rec.poll()["t"]
    g.press("cancel", 2)
    g.hold("left", 36)
    rec.until(lambda m: m["uc"] == 1, 4, "the close")
    rec.ticks(40)
    end = settle(rec, n=6)
    tr = rec.between(t_c - 1, t_c + 40)
    steps = [abs(b["vx"] - a["vx"]) / max(1, b["t"] - a["t"]) for a, b in zip(tr, tr[1:])]
    model = P0.follow_model(end["px"], end["pz"], 199)
    rec.notes["K6 trace"] = [(x["t"] - t_c, x["vx"]) for x in tr]
    g.check(x0 - end["px"] >= 300 and steps and max(steps) <= 30 and abs(end["vx"] - model[0]) <= 1
            and abs(end["vy"] - model[1]) <= 1,
            "K6 THE WALKING EXIT: running through the glide, the camera chases the player in with no snap and rests on "
            "the follow point", f"walked {x0 - end['px']:.0f}u, largest step {max(steps) if steps else None}, end "
            f"({end['vx']},{end['vy']}) model {model}")


# ------------------------------------------------------------------- gates and yields
def yield_phases(g, rec: Rec, ref) -> None:
    # Y1 a dialogue: talk to the talker, try Select during it and right after
    g.walk_to(-600, -1000)
    settle(rec)
    g.hold("up", 4)
    rec.ticks(6)
    st = g.interact()
    if st is None or not rec.poll()["dialog"]:
        g.check(False, "Y1 A DIALOGUE: could not open the talker's dialogue (harness positioning) -- not a photo "
                "verdict", str(rec.poll()))
    else:
        press(g, rec, "select")
        during = rec.poll()
        g.advance()
        rec.until(lambda m: m["uc"] == 1 and not m["dialog"], 6, "the dialogue to end")
        rec.ticks(4)
        press(g, rec, "select")
        right_after = rec.ticks(6)
        rec.ticks(40)
        m = opened(g, rec)
        g.check(during["flags"] == ALL and right_after["uc"] == 1 and is_open(m),
                "Y1 A DIALOGUE: Select during the dialogue and right after it does nothing; after the settle it opens",
                f"during flags {during['flags']}, right after uc {right_after['uc']}")
        closed(g, rec)

    # Y2 a foreign EnableMove while open
    g.walk_to(0, -1102)
    settle(rec)
    opened(g, rec)
    press(g, rec, "r1")
    press(g, rec, "r1")
    press(g, rec, "l1")
    rec.ticks(12)
    before = rec.poll()
    cmd(g, rec, "ENABLEMOVE")
    m = rec.until(lambda m: m["flags"] == ALL, 3, "the yield's restore")
    rec.ticks(25)
    png, m2, t = shot(g, rec, "y2-yield", ref)
    g.check(before["flags"] == ALL - 2 - 4 and m2["uc"] == 1 and m2["flags"] == ALL
            and max(abs(a - b) for a, b in zip(P0.white_median(png, t["ox"], t["oy"]), (235, 235, 235))) <= 3,
            "Y2 A FOREIGN EnableMove: photo mode closes itself -- the hidden balloons back, the tint gone",
            f"flags {before['flags']} -> {m2['flags']}")

    # Y3 the scene bit
    rec.ticks(35)
    opened(g, rec)
    cmd(g, rec, "SCENE_ON")
    m = rec.until(lambda m: m["uc"] == 1, 3, "the scene-bit yield")
    rec.ticks(35)
    press(g, rec, "select")
    blocked = rec.ticks(6)
    cmd(g, rec, "SCENE_OFF")
    rec.ticks(5)
    m2 = opened(g, rec)
    g.check(m["uc"] == 1 and blocked["uc"] == 1 and is_open(m2),
            "Y3 THE SCENE BIT: raised while open, photo mode closes; while it is up Select does nothing; cleared, "
            "Select opens again", f"blocked uc {blocked['uc']}")
    closed(g, rec)

    # Y4 a target hidden before photo mode opened stays hidden
    rec.ticks(35)
    cmd(g, rec, "PREHIDE_C")
    pre = rec.until(lambda m: m["flags"] == ALL - 4, 3, "balloon C pre-hidden")
    opened(g, rec)
    press(g, rec, "r1")
    press(g, rec, "r1")
    press(g, rec, "cancel")
    m = rec.until(lambda m: m["uc"] == 1, 4, "the close")
    rec.ticks(20)
    m = rec.poll()
    g.check(pre["flags"] == ALL - 4 and m["flags"] == ALL - 4,
            "Y4 THE EXACT RESTORE: balloon C, hidden before photo mode opened, stays hidden after it closes; balloon L "
            "it hid comes back", f"flags before {pre['flags']} after {m['flags']}")
    cmd(g, rec, "RESHOW_C")
    rec.until(lambda m: m["flags"] == ALL, 3, "balloon C re-shown")

    # Y5 re-open mid-glide holds
    rec.ticks(35)
    opened(g, rec)
    hold(g, rec, "right", 20)
    g.press("cancel", 2)
    rec.until(lambda m: m["uc"] == 1, 3, "the close")
    rec.ticks(3)
    mo = opened(g, rec)
    rec.ticks(25)
    after = rec.between(mo["t"] + 2)
    g.check(after and len({(x["vx"], x["vy"]) for x in after}) == 1,
            "Y5 RE-OPEN MID-GLIDE: the camera holds where it is", str(sorted({(x['vx'], x['vy']) for x in after})))
    closed(g, rec)


def run(g) -> None:
    try:
        preflight(g)
    except (Stop, SystemExit) as e:
        g.check(False, "PREFLIGHT", str(e))
        return
    ref = P0.canvas_labels()
    g.newgame()
    mark = g.log_mark()
    g.warp(B.FIELD_ID)
    g.wait_for(lambda s: s.field_id == B.FIELD_ID, timeout=60, what="field 30956")
    g.state_every(1)
    _watch(g)
    rec = Rec(g)
    try:
        kit_phases(g, rec, ref)
        yield_phases(g, rec, ref)
    except (Stop, HarnessError) as e:
        g.check(False, "STOPPED", f"{type(e).__name__}: {e}")
    finally:
        (g.run_dir / "photo1_samples.json").write_text(json.dumps(rec.s, default=str), encoding="utf-8")
        (g.run_dir / "photo1_notes.json").write_text(json.dumps(rec.notes, default=str, indent=1), encoding="utf-8")
        every = g.exceptions_since(mark)
        ours = [e for e in every if e.name in THROWS and (not e.trace or any(k in fr for fr in e.trace for k in WHERE))]
        print(f"[photo-rung1] exceptions since the mark: {len(every)}")
        g.check(not ours, "NC-THROW: nothing thrown through the event engine, the evaluator or FieldMap",
                str([(e.name, e.where) for e in ours[:5]]))
