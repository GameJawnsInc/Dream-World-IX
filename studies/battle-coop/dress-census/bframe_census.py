"""THE B_FRAME THRESHOLD CENSUS (battle co-op s140; R3-FIELD-MODEL-AUDIT.md 2.3 amendment 1, "an offline oracle test:
for every stock GetAnimDuration / GetEntryAnimFrame threshold site in a 98+CC entry, evaluate the bound against every
rig's frame counts read from p0data5, and assert that each bound is reachable").

READ-ONLY. Re-derives the audit's census instead of trusting it:
  * every THRESHOLD site: a `while` / `if` condition comparing GetEntryAnimFrame(uid) -- the `<`, `<=`, `==`, `!=`, `>=`,
    `>` and bare-truth forms -- against a literal or GetAnimDuration(id) +/- k, whose target is the PLAYER BODY: uid 255
    inside a 98+CC entry (SetModel(98) + DefinePlayerCharacter in one entry), or 250 / 251-254 / the 98+CC entry's own
    uid from any other entry (a conductor);
  * the clip the body is RUNNING there (the loop body's replayed op, else the last play op before the site in the same
    function -- RunAnimation / RunAnimationEx(self) / a jump / a walk / a turn / an arrival on the idle -- with the
    SetAnimationInOut window, SetAnimationFlags hold/loop, MakeAnimationLoop and SetAnimationSpeed in force) and that
    clip's loco CLASS by NAME from loco_table.json;
  * every DURATION site: a GetAnimDuration(id) the body itself evaluates (B_FRAME reads gCur.go, so only a 98+CC
    entry's own functions reach the s140 hook), with its use (window, variable, timed wait, footstep frame, counter
    loop, turn interpolation) -- the domain of the hook, checked for timeline CONSISTENCY.

Body context: 255 in a 98+CC entry, AND in a shared script that entry starts (RunSharedScript runs with gCur = the
caller: EBin's objV0 = FindObjByUID(seq.uid - cSeqOfs)), so both its frame reads and its B_FRAME are the body's.

Each threshold site is then EVALUATED against all 13 rigs under four laws by simulating Memoria's ProcessAnime
(NextFrame's 1/16-frame stepping, the forward cap min(outFrame, frameN - 1), AnimLoop / AnimStop / DefaultAnim, the
slot wrap at frameN, the stand slot's per-cycle idleAnimSpeed draw from SetAnimationStandSpeed) -- pure functions
below, importable with no install, so the pytest is their twin:
  stock        an undressed Zidane: every clip on its own timeline, B_FRAME = the clip's own length (CALIBRATION:
               every stock site must be reachable here, or the instrument is wrong);
  s140         the dressed body under the s140 laws: a LOCO-family clip (IDLE/WALK/RUN/TURN_L/TURN_R, and INACTIVE
               iff the rig has an inactive clip) runs the rig's NATIVE clip and B_FRAME answers its native length
               (the hook); a GESTURE (OTHER, JUMP_LADDER, INACTIVE on a rig without one) RunAnimation keeps the SOURCE
               timeline (KeepSourceTimeline: frameN = the source clip's frames) and B_FRAME answers stock; a stand /
               walk / run / turn SLOT holding a gesture clip stores the rig's IDLE (SiteFallback) and plays it
               natively; AJUMP's jump SLOT stores the idle ALIAS, but KeepJumpTimeline (after PREJUMP / POSTJUMP /
               SETVY3's ExecAnim(actor.jump)) puts the SOURCE clip's frame count back for a gesture -- every jump /
               land runs on the source timeline, exactly as a RunAnimation gesture (a loco-class jump id: native);
  bframe_off   `selfdress law bframe off`: the slots still play native, B_FRAME answers the RAW clip (the s139 engine
               plus the s140 slot mapping -- leg T3's red); KeepSourceTimeline / KeepJumpTimeline gate on the TIMELINE
               law only, so a gesture and the jump slot still run on the source timeline;
  timeline_off `selfdress law timeline off`: a gesture plays the idle ALIAS at its own native length -- the jump slot
               too (KeepJumpTimeline is KeepSourceTimeline, the same lever).
Rig 0 (Zidane) is stock under every law: a Zidane dress disarms (s139) and every ZDN clip is its own.

REACHABILITY CANNOT SEE THE JUMP HOOK: every stock jump / land window is reachable on the alias as well as on the source
clip (the alias is at least as long as every ladder window), so the verdicts agree with KeepJumpTimeline on or off. The
jump slot's TICK law -- a mount / dismount lasts exactly stock's ticks on every rig -- is pinned by test_dress_census.py's
test_every_stock_jump_window_keeps_stocks_ticks_on_every_rig, and this module's jump timeline by its pin against
battlewire.jump_frame_n (the engine's twin), never by reachability.

Which clip a site reads (site_candidates): a wait's own loop body when it replays a play op; else the last play op
DOMINATING the site (on its block path) plus later ones in closed sibling if-branches; the nearest preceding switch
case's end state when the site's own path played nothing (a looping function's previous pass); loop-carried ops after
the site in an enclosing loop; a WaitAnimation ends a clip (held -> frozen on its last frame, else the stand slot), and
so does a later SetAnimationFlags (AMODE writes animFlag, clearing afExec / afFreeze). State (window, flags, speed) is
read from dominating ops only; a window a sibling branch sets is an extra 'alt' candidate. A WAIT is judged on the
WORST of its primary candidates, a TEST on the BEST of all (a test must be able to fire; it cannot wedge). Function-
start state is the engine default (window 0..255, flags 0, aspeed 16) -- inherited state is the census's known limit,
and the stock calibration is what vouches for these rules.

Frame counts come from p0data5 through the kit's readers (rigs_8_11.Install.frames: catalog.locate_animation +
_gltf_io.read_clip, frames = round(length x rate) + 1, GetCharAnimFrame's formula). Output: numbers and open-source
names only (field ids, HW indices / line numbers / HW function labels, AnimationDB names, frame counts) -> bframe_sites.json.

    py -X utf8 studies/battle-coop/dress-census/bframe_census.py [--game <FF9>] [--exports <dir>] [--memoria <clone>]
    py -X utf8 studies/battle-coop/dress-census/bframe_census.py --check      # rebuild in memory, diff the frozen JSON
    py -X utf8 studies/battle-coop/dress-census/bframe_census.py --evaluate   # re-evaluate the FROZEN sites (no install)

The frozen verdicts are one 13-character string per law per site (rig 0..12): '.' reachable, 'L' only after the clip
stopped, 'W' a wait that wedges, 'N' a test that never fires.
"""
from __future__ import annotations

import argparse
import collections
import functools
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
DEFAULT_EXPORTS = Path(r"C:\gd\FFIX\reference\test2")
DEFAULT_MEMORIA = Path(r"C:\gd\FFIX\Memoria")
DEFAULT_GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
OUT = HERE / "bframe_sites.json"
RIGS_JSON = HERE / "rigs_8_11.json"
LOCO_JSON = HERE / "loco_table.json"

# ================================================================================================ THE PURE EVALUATOR
# Everything in this section is stdlib-only and reads no install: the pytest imports it (or re-implements it) and runs
# it over the FROZEN sites + frame table in bframe_sites.json.

LAWS = ("stock", "s140", "bframe_off", "timeline_off")
SLOT_OF_CLASS = {"IDLE": "idle", "WALK": "walk", "RUN": "run", "TURN_L": "turn_l", "TURN_R": "turn_r",
                 "INACTIVE": "inactive"}
AF_HOLD, AF_LOOP, AF_PAL = 1, 2, 4          # SetAnimationFlags arg << 3 & (afHold|afLoop|afPalindrome), as arg bits


def is_loco(cls: str, rig: dict) -> bool:
    """The s140 loco-family test (loco_table.json `rules`): IDLE/WALK/RUN/TURN_L/TURN_R always; INACTIVE only when the
    rig has an inactive clip (rig.Inactive != 0) -- otherwise a BREAK1_* RunAnimation takes the gesture path."""
    if cls == "INACTIVE":
        return bool(rig["ids"].get("inactive"))
    return cls in SLOT_OF_CLASS


def native_frames(cls: str, rig: dict) -> int:
    return int(rig["frames"][SLOT_OF_CLASS[cls]])


def timeline_frames(cand: dict, rig: dict, law: str) -> int:
    """frameN of the timeline the body runs ``cand`` on (ExecAnim/SetAnim: frameN = GetCharAnimFrame(go, anim)), as the
    s140 DLL ships it:
      * a LOCO-family clip -> the rig's native slot clip (RunAnimation, a slot, or the jump slot: MapRigAnim's map);
      * AJUMP's jump / land (the jump SLOT): the slot holds the idle ALIAS (AtJumpSlot keeps the raw id in netJumpSrc),
        and KeepJumpTimeline -> KeepSourceTimeline puts the SOURCE clip's frame count back for a gesture under s140 and
        bframe_off (it gates on the timeline law only); `law timeline off` leaves the alias's own count;
      * a stand / walk / run / turn SLOT holding a gesture clip -> the rig's IDLE (SiteFallback; the same clip's frames
        as the alias, never the alias id), native, under every dressed law;
      * a RunAnimation GESTURE -> the SOURCE timeline (KeepSourceTimeline), the idle alias under `law timeline off`."""
    src = int(cand["src_frames"])
    if law == "stock" or rig["rig"] == 0:
        return src
    cls = cand["class"]
    if is_loco(cls, rig):
        return native_frames(cls, rig)
    if cand["how"] in ("jump", "land"):                   # the jump slot: the alias, then KeepJumpTimeline
        return int(rig["frames"]["idle_alias"]) if law == "timeline_off" else src
    if cand.get("slot_clip"):
        return int(rig["frames"]["idle"])                 # SiteFallback: a slot stores the rig's idle, native
    if law == "timeline_off":
        return int(rig["frames"]["idle_alias"])
    return src                                            # KeepSourceTimeline


def bframe(dur_id: int, dur: dict, rig: dict, law: str, gcur_is_body: bool) -> int:
    """What GetAnimDuration(dur_id) answers. B_FRAME reads GetCharAnimFrame(gCur.go, id), so only a site the BODY
    evaluates reaches the hook; a conductor's read is stock on the conductor's own go (taken as the clip's length)."""
    src = int(dur["src_frames"])
    if not gcur_is_body or law in ("stock", "bframe_off") or rig["rig"] == 0:
        return src
    cls = dur["class"]
    return native_frames(cls, rig) if is_loco(cls, rig) else src


class _Unknown:
    """A non-frame term of a condition (VAR_..., GetEntryPosZ(...), IsButtonDown(...)): comparisons answer ``val``."""
    def __init__(self, val: bool):
        self.val = val

    def _cmp(self, _o):
        return self.val
    __lt__ = __le__ = __gt__ = __ge__ = __eq__ = __ne__ = _cmp

    def _ar(self, _o):
        return self
    __add__ = __radd__ = __sub__ = __rsub__ = __mul__ = __rmul__ = __floordiv__ = __rfloordiv__ = __mod__ = _ar
    __truediv__ = __rtruediv__ = __rmod__ = _ar

    def __bool__(self):
        return self.val

    __hash__ = object.__hash__


@functools.lru_cache(maxsize=None)
def _code(py: str):
    """Compile a transformed condition / window expression once (our own text: F, D(i), U, ints, operators)."""
    return compile(py, "<bframe-cond>", "eval")


def cond_holds(py: str, frame: int, dvals: dict, unknown: bool) -> bool:
    env = {"F": frame, "D": lambda i: dvals[int(i)], "U": _Unknown(unknown)}
    return bool(eval(_code(py), {"__builtins__": {}}, env))     # noqa: S307 - our own transformed condition text


def _next_frame(st: dict) -> int:
    """EventEngine.NextFrame, verbatim: 1/16-frame stepping with frameDif carry; reverse adds 15 and biases -15."""
    rev = st["dir"]
    n1 = (st["frame"] << 4) + st["dif"] + (-st["speed"] if rev else st["speed"])
    if rev:
        n1 += 15
    dif = n1 & 15
    if rev:
        dif -= 15
    st["dif"] = dif
    st["last"] = st["frame"]
    n2 = n1 >> 4
    st["frame"] = n2 & 0xFF
    return n2


@functools.lru_cache(maxsize=None)
def frames_visited(frame_n: int, *, exec_: bool, in_: int = 0, out: int = 255, flags: int = 0, loops: int = 0,
                   speed: int = 16, after_n: int | None = None, ticks: int | None = None) -> tuple:
    """(clip_frames, after_frames, ended_how, sequence): the animFrame values the body shows while ``cand`` runs
    (ProcessAnime + AnimLoop/AnimStop, verbatim), the values on the idle that DefaultAnim switches to when the clip
    stops (no afHold), and the per-tick sequence of both. A slot (exec_=False) wraps at frameN forever."""
    frame_n = max(1, int(frame_n))
    st = {"frame": (in_ if exec_ else 0) & 0xFF, "dif": 0, "speed": int(speed) or 16, "dir": exec_ and in_ > out,
          "last": 0, "in": in_, "out": out, "loops": loops}
    seen, after, phase, how = {st["frame"]}, set(), "exec" if exec_ else "slot", "loops"
    seq = [st["frame"]]
    n = ticks or (frame_n + 2) * 16 * 3 // max(1, st["speed"]) + 64
    a_n = max(1, int(after_n or 1))
    for _ in range(n):
        if phase == "slot":
            if _next_frame(st) >= frame_n:
                st["frame"] = 0
            seen.add(st["frame"])
            seq.append(st["frame"])
            continue
        if phase in ("frozen",):
            break
        if phase == "after":
            if _next_frame(st) >= a_n:
                st["frame"] = 0
            after.add(st["frame"])
            seq.append(st["frame"])
            continue
        if not st["dir"]:
            cap = min(st["out"], frame_n - 1)
            hit = _next_frame(st) > cap
        else:
            hit = _next_frame(st) < st["out"]
        if hit:                                            # AnimLoop
            stop = False
            if flags & (AF_LOOP | AF_PAL):
                if st["loops"] != 0:
                    st["loops"] -= 1
                    stop = st["loops"] == 0
                if not stop:
                    if flags & AF_PAL:
                        st["frame"] = (st["frame"] + (2 if st["dir"] else 254)) & 0xFF
                        st["dir"] = not st["dir"]
                        st["in"], st["out"] = st["out"], st["in"]
                    else:
                        st["frame"] = st["in"] & 0xFF
            else:
                stop = True
            if stop:                                       # AnimStop
                if flags & AF_HOLD:
                    st["frame"] = st["last"]
                    phase, how = "frozen", "held"
                    seen.add(st["frame"])
                    seq.append(st["frame"])
                    break
                phase, how = "after", "stopped"            # DefaultAnim: SetAnim(idle), frame 0, idle speed 16
                st.update(frame=0, dif=0, speed=16, dir=False)
                after.add(0)
                seq.append(0)
                continue
        seen.add(st["frame"])
        seq.append(st["frame"])
    if phase == "slot":
        how = "slot"
    return frozenset(seen), frozenset(after), how, tuple(seq)


def window_values(win: dict, rig: dict, law: str, durs: dict, gcur_is_body: bool) -> tuple:
    """(in, out, scripted_set): a literal window, a GetAnimDuration window evaluated per rig/law, or a SCRIPTED window
    (an expression of GetEntryAnimFrame: the script steps the frame itself, the ladder's (F + 1) % 12)."""
    if win is None:
        return 0, 255, None
    if win["kind"] == "lit":
        return int(win["in"]) & 0xFF, int(win["out"]) & 0xFF, None
    dv = tuple((int(i), bframe(int(i), durs[str(i)], rig, law, gcur_is_body)) for i in win.get("dur_ids", []))
    return _expr_window(win["in_py"], win["out_py"], dv)


@functools.lru_cache(maxsize=None)
def _expr_window(in_py: str, out_py: str, dv: tuple) -> tuple:
    d = dict(dv)
    vals = []
    for py in (in_py, out_py):
        if "F" in py:
            vals.append(None)
        else:
            try:
                vals.append(int(eval(_code(py), {"__builtins__": {}}, {"D": lambda i: d[int(i)]})) & 0xFF)  # noqa: S307
            except Exception:                              # noqa: BLE001 - an unparsable window is reported, not fatal
                vals.append(None)
    if None in vals:
        scripted = set()
        for f in range(256):
            try:
                v = eval(_code(in_py), {"__builtins__": {}}, {"F": f, "D": lambda i: d[int(i)]})  # noqa: S307
                scripted.add(int(v) & 0xFF)
            except Exception:                              # noqa: BLE001
                pass
        return 0, 255, frozenset(scripted)
    return vals[0], vals[1], None


def evaluate_candidate(site: dict, cand: dict, rig: dict, law: str, durs: dict) -> dict:
    """One site x one candidate timeline x one rig x one law -> {verdict, frame_n, bound, max_frame}.
    verdict: 'ok' (satisfied on the clip's own timeline), 'ok_after_clip' (only once the clip has stopped and the idle
    runs -- a late completion), 'wedge' / 'never' (a wait that cannot end / a test that cannot fire)."""
    g = site["gcur_is_body"]
    dv = {int(i): bframe(int(i), durs[str(i)], rig, law, g) for i in site["dur_ids"]}
    fn = timeline_frames(cand, rig, law)
    after = cand.get("after")                              # the stand slot DefaultAnim falls back to
    after_n = timeline_frames(dict(after, how="slot", slot_clip=True), rig, law) if after else fn
    in_, out, scripted = window_values(cand.get("window"), rig, law, durs, g)
    stand_speeds = tuple(site.get("stand_speeds") or (16,))
    if scripted is not None:
        seen, after_seen, how, seq = set(scripted), set(), "scripted", sorted(scripted)
    elif cand.get("stand"):                                # a stand slot: one cycle per idleAnimSpeed draw
        seen, seq = set(), []
        for sp in stand_speeds:
            sv, _a, how, sq = frames_visited(fn, exec_=False, speed=sp)
            seen |= sv
            seq.extend(sq)
        after_seen = set()
    else:
        seen, after_seen, how, seq = frames_visited(fn, exec_=cand["exec"], in_=in_, out=out,
                                                    flags=cand.get("flags", 0), loops=cand.get("loops", 0),
                                                    speed=cand.get("speed", 16), after_n=after_n)
        if after_seen and stand_speeds != (16,):
            after_seen = set(after_seen)
            for sp in stand_speeds:
                after_seen |= frames_visited(after_n, exec_=False, speed=sp)[0]
    if cand.get("ended") == "held":                        # WaitAnimation returned on a HELD clip: frozen on its end
        end = min(out, fn - 1) if in_ <= out else out
        seen, after_seen, how = ({max(seen)} if in_ <= out else {end}), set(), "held_after_wait"
        seq = sorted(seen)
    after = after_seen
    wait = site["form"] == "wait"
    # a wait ENDS when its condition is false; a test FIRES when it is true. Non-frame terms are neutral: they keep a
    # wait running (and let a test fire), so the verdict is the FRAME term's alone.
    unk = True

    def satisfied(f):
        c = cond_holds(site["cond_py"], f, dv, unk)
        return (not c) if wait else c
    if any(satisfied(f) for f in sorted(seen)):
        verdict = "ok"
    elif after and any(satisfied(f) for f in sorted(after)):
        verdict = "ok_after_clip"
    else:
        verdict = "wedge" if wait else "never"
    tick = next((t for t, f in enumerate(seq) if satisfied(f)), None) \
        if how != "scripted" and not cand.get("stand") else None
    bound = None
    if site.get("rhs") and site["rhs"]["kind"] == "dur":
        bound = dv[int(site["rhs"]["id"])] + int(site["rhs"]["k"])
    elif site.get("rhs") and site["rhs"]["kind"] == "lit":
        bound = int(site["rhs"]["value"])
    return {"verdict": verdict, "frame_n": fn, "bound": bound, "max_frame": max(seen) if seen else None,
            "ended": how, "first_tick": tick}


def evaluate_site(site: dict, rigs: list, durs: dict) -> dict:
    """{law: {rig: verdict}} plus the per-candidate detail. A WAIT takes the WORST of its PRIMARY candidates (its own
    body's replayed clip, or the dominating / sibling-branch clip before it: any timeline the body may be on that
    cannot end it is a wedge risk); loop-carried clips judge a wait only when it has no primary one. A TEST takes the
    BEST of all (it is a test, not a wait: it must be able to fire on some timeline the body can be on -- the ladder
    climb's loop-carried clip with its sibling-branch scripted window, typically)."""
    rank = {"ok": 0, "ok_after_clip": 1, "never": 2, "wedge": 2}
    wait = site["form"] == "wait"
    pick = max if wait else min
    judged = [n for n, c in enumerate(site["candidates"]) if not wait or c.get("tier", "primary") == "primary"]
    if not judged:
        judged = list(range(len(site["candidates"])))
    out, detail = {}, {}
    for law in LAWS:
        out[law], detail[law] = {}, {}
        for rig in rigs:
            per = [evaluate_candidate(site, c, rig, law, durs) for c in site["candidates"]]
            pool = [per[n] for n in judged]
            best = pick(pool, key=lambda r: rank[r["verdict"]]) if pool else {"verdict": "unresolved"}
            out[law][str(rig["rig"])] = best["verdict"]
            detail[law][str(rig["rig"])] = per
    return {"verdicts": out, "detail": detail}


def duration_consistency(dsite: dict, rigs: list, durs: dict) -> dict:
    """A body-evaluated GetAnimDuration(id): under each law, does B_FRAME(id) equal the frameN of the timeline id would
    RUN on if the body played it (the law's whole claim: "B_FRAME(id) equals the frame count of the timeline that id
    actually runs on")? {law: {rig: [bframe, timeline]}} and the rigs where they differ."""
    d = durs[str(dsite["id"])]
    cand = {"how": "anim", "class": d["class"], "src_frames": d["src_frames"]}
    res, bad = {}, {}
    for law in LAWS:
        res[law], bad[law] = {}, []
        for rig in rigs:
            b = bframe(int(dsite["id"]), d, rig, law, True)
            t = timeline_frames(cand, rig, law)
            res[law][str(rig["rig"])] = [b, t]
            if b != t:
                bad[law].append(rig["rig"])
    return {"pairs": res, "mismatch": bad}


VERDICT_CODE = {"ok": ".", "ok_after_clip": "L", "wedge": "W", "never": "N", "unresolved": "?"}


def verdict_codes(verdicts: dict) -> dict:
    """{law: 13-char string, one code per rig in rig order}: '.' reachable, 'L' late (only after the clip stopped),
    'W' a wait that wedges, 'N' a test that never fires, '?' unresolved -- the FROZEN form of evaluate_site."""
    return {law: "".join(VERDICT_CODE[v[str(r)]] for r in range(len(v))) for law, v in verdicts.items()}


def evaluate_all(doc: dict) -> dict:
    rigs, durs = doc["frame_table"]["rigs"], doc["frame_table"]["clips"]
    return {"sites": {s["key"]: evaluate_site(s, rigs, durs)["verdicts"] for s in doc["threshold_sites"]},
            "durations": {s["key"]: duration_consistency(s, rigs, durs)["mismatch"] for s in doc["duration_sites"]
                          if str(s["id"]) in durs}}


# ================================================================================================ THE EXPORT PARSER
LANG_RE = re.compile(r"^#HW language \S+\s*$")
ENTRY_RE = re.compile(r"^#HW newentry (\d+)")
NEWFUNC_RE = re.compile(r"^#HW newfunction (\d+)")
FUNC_RE = re.compile(r"^Function (\S+)")
FILEID_RE = re.compile(r"^#HW fileid (\d+)")
CALL_RE = re.compile(r"\b([A-Z][A-Za-z0-9]*)\(\s*(.*?)\s*\)\s*$")
GEAF_RE = re.compile(r"GetEntryAnimFrame\((\d+)\)")
GAD_RE = re.compile(r"GetAnimDuration\((\d+)\)")
INT_RE = re.compile(r"^-?\d+$")
COND_RE = re.compile(r"^\s*(while|if)\s*\((.*)\)\s*\{\s*$")
ATOM_RE = re.compile(r"GetEntryAnimFrame\((\d+)\)\s*(<=|>=|==|!=|<|>)\s*(\(\s*GetAnimDuration\((\d+)\)\s*([+-])\s*(\d+)\s*\)"
                     r"|GetAnimDuration\((\d+)\)|-?\d+)")
MOVE_OPS = ("Walk", "WalkXZY", "WalkTowardObject", "SideWalkXZY")
TURN_OPS = ("TimedTurn", "TurnTowardObject", "TurnTowardPosition")
SLOT_SETTERS = {"SetStandAnimation": "idle", "SetWalkAnimation": "walk", "SetRunAnimation": "run",
                "SetLeftAnimation": "turn_l", "SetRightAnimation": "turn_r", "SetInactiveAnimation": "inactive"}


def first_block(lines: list) -> list:
    """The export's FIRST language block (the audit's census convention): up to the second `#HW language` header."""
    seen = 0
    for i, line in enumerate(lines):
        if LANG_RE.match(line):
            seen += 1
            if seen == 2:
                return lines[:i]
    return lines


def ival(s):
    return int(s) if isinstance(s, str) and INT_RE.match(s.strip()) else None


def split_args(s: str) -> list:
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def parse_export(path: Path) -> dict:
    """{field, hw, entries: [{idx, funcs: [{num, label, lines: [(lineno, depth_path, code)]}]}]} -- comments cut, brace
    blocks tracked so a site knows which earlier ops DOMINATE it (lie on its block path) and which sit in a closed
    sibling branch; `case` labels open a pseudo-block of their own."""
    raw = path.read_text(encoding="utf-8", errors="replace").splitlines()
    lines = first_block(raw)
    field, entries, cur, fn, newfunc = None, [], None, None, None
    stack, nid = [], [0]

    kinds = {}

    def new_block(kind):
        nid[0] += 1
        stack.append((nid[0], kind))
        kinds[nid[0]] = kind
    for i, line in enumerate(lines, 1):
        m = FILEID_RE.match(line)
        if m and field is None:
            field = int(m.group(1))
            continue
        m = ENTRY_RE.match(line)
        if m:
            cur = {"idx": int(m.group(1)), "funcs": []}
            entries.append(cur)
            fn = None
            continue
        m = NEWFUNC_RE.match(line)
        if m:
            newfunc = int(m.group(1))
            continue
        m = FUNC_RE.match(line)
        if m and cur is not None:
            fn = {"num": newfunc, "label": m.group(1), "lines": [], "kinds": kinds}
            cur["funcs"].append(fn)
            stack.clear()
            continue
        if fn is None or line.startswith("#HW"):
            continue
        code = line.split("//", 1)[0].rstrip()
        s = code.strip()
        if not s:
            continue
        if s.startswith("}"):
            while stack and stack[-1][1] == "case":
                stack.pop()
            if stack:
                stack.pop()
        if re.match(r"^(case\b|default\b)", s):
            if stack and stack[-1][1] == "case":
                stack.pop()
            new_block("case")
        path_now = tuple(b for b, _k in stack)
        fn["lines"].append((i, path_now, s))
        if s.endswith("{"):
            new_block("block")
    return {"field": field, "hw": int(path.stem.split("_")[1]), "entries": entries}


def entry_facts(exp: dict) -> dict:
    """Per entry: models it SetModels, whether it runs DefinePlayerCharacter (and in which function), its uid (InitObject
    arg2, defaulting to the entry id), the slot setters it holds, and the SetAnimationStandSpeed ops it runs."""
    facts = {}
    uid_of = {}
    for e in exp["entries"]:
        models, cc_funcs, slots, idle_speed, shared = set(), [], collections.defaultdict(list), [], set()
        for fn in e["funcs"]:
            for _ln, _p, s in fn["lines"]:
                m = CALL_RE.search(s)
                if not m:
                    continue
                op, args = m.group(1), split_args(m.group(2))
                if op == "SetModel" and args and ival(args[0]) is not None:
                    models.add(ival(args[0]))
                elif op == "DefinePlayerCharacter":
                    cc_funcs.append(fn["num"])
                elif op in SLOT_SETTERS and args and ival(args[0]) is not None:
                    slots[SLOT_SETTERS[op]].append(ival(args[0]))
                elif op == "SetJumpAnimation" and args and ival(args[0]) is not None:
                    slots["jump"].append(ival(args[0]))
                elif op == "SetAnimationStandSpeed":
                    idle_speed.append([ival(a) for a in args])
                elif op == "InitObject" and len(args) >= 2 and ival(args[0]) is not None:
                    uid_of[ival(args[0])] = ival(args[1]) or ival(args[0])
                elif op == "RunSharedScript" and args and ival(args[0]) is not None:
                    shared.add(ival(args[0]))
        facts[e["idx"]] = {"models": sorted(models), "cc_funcs": cc_funcs, "slots": {k: v for k, v in slots.items()},
                           "idle_speed": idle_speed, "shared": sorted(shared)}
    for idx, f in facts.items():
        f["uid"] = uid_of.get(idx, idx)
        f["player"] = 98 in f["models"] and bool(f["cc_funcs"])
    return facts


def cond_to_py(cond: str, body_uids: set, self_is_body: bool) -> tuple:
    """(python, dur_ids, frame_atoms, foreign_frames): GetEntryAnimFrame(<body>) -> F, GetAnimDuration(i) -> D(i), every
    other call / variable -> U (a neutral unknown), && / || / ! -> and / or / not."""
    s = cond
    dur_ids = [int(x) for x in GAD_RE.findall(s)]
    foreign = []

    def geaf(m):
        uid = int(m.group(1))
        if (uid == 255 and self_is_body) or uid in body_uids:
            return " F "
        foreign.append(uid)
        return " U "
    s = GEAF_RE.sub(geaf, s)
    s = GAD_RE.sub(lambda m: f" D({m.group(1)}) ", s)
    prev = None
    while prev != s:                                       # innermost calls first: Foo(...) -> U
        prev = s
        s = re.sub(r"\b(?!D\b)[A-Za-z_][A-Za-z0-9_]*\(([^()]*)\)", " U ", s)
    s = re.sub(r"\b(?!F\b|D\b|U\b)[A-Za-z_][A-Za-z0-9_]*\b", " U ", s)
    s = s.replace("&&", " and ").replace("||", " or ")
    s = re.sub(r"!(?!=)", " not ", s)
    atoms = ATOM_RE.findall(cond)
    return " ".join(s.split()), dur_ids, atoms, foreign


def window_of(args: list, body_uids: set, self_is_body: bool) -> dict:
    if len(args) < 2:
        return None
    a, b = ival(args[0]), ival(args[1])
    if a is not None and b is not None:
        return {"kind": "lit", "in": a, "out": b}
    ins = [cond_to_py(x, body_uids, self_is_body) for x in args[:2]]
    return {"kind": "expr", "in_py": ins[0][0], "out_py": ins[1][0],
            "dur_ids": sorted({d for p in ins for d in p[1]})}


def scan_function(fn: dict, body_uids: set, self_is_body: bool, self_uids: set) -> list:
    """The play/state events of one function, in source order: [(index, kind, payload)]."""
    ev = []
    sync = False
    for k, (_ln, _p, s) in enumerate(fn["lines"]):
        m = CALL_RE.search(s)
        if not m or COND_RE.match(s):
            continue
        op, args = m.group(1), split_args(m.group(2))
        if op == "RunAnimation" and args and ival(args[0]) is not None:
            ev.append((k, "anim", {"id": ival(args[0])}))
        elif op == "RunAnimationEx" and len(args) >= 2 and ival(args[1]) is not None:
            tgt = ival(args[0])
            if tgt is not None and (tgt in self_uids or (tgt == 255 and self_is_body) or tgt in body_uids):
                ev.append((k, "anim", {"id": ival(args[1]), "ex_uid": tgt}))
        elif op == "SetJumpAnimation" and args and ival(args[0]) is not None:
            ev.append((k, "set_jump", {"id": ival(args[0]), "j0": ival(args[1]) if len(args) > 1 else None,
                                       "j1": ival(args[2]) if len(args) > 2 else None}))
        elif op == "RunJumpAnimation":
            ev.append((k, "jump", {}))
        elif op == "RunLandAnimation":
            ev.append((k, "land", {}))
        elif op in MOVE_OPS:
            ev.append((k, "move", {"op": op, "sync": sync, "args": args}))
            sync = False
        elif op == "InitWalk":
            sync = True
        elif op in TURN_OPS:
            ev.append((k, "turn", {"op": op}))
        elif op in SLOT_SETTERS and args and ival(args[0]) is not None:
            ev.append((k, "slot", {"slot": SLOT_SETTERS[op], "id": ival(args[0])}))
        elif op == "SetAnimationInOut":
            ev.append((k, "window", {"win": window_of(args, body_uids, self_is_body)}))
        elif op == "SetAnimationFlags" and args:
            ev.append((k, "flags", {"flags": ival(args[0]), "loops": ival(args[1]) if len(args) > 1 else 0}))
        elif op == "MakeAnimationLoop" and args:
            ev.append((k, "loops", {"loops": ival(args[0])}))
        elif op == "SetAnimationSpeed" and args:
            ev.append((k, "speed", {"speed": ival(args[0])}))
        elif op == "WaitAnimation":
            ev.append((k, "waitanim", {}))
        elif op == "StopAnimation":
            ev.append((k, "stopanim", {}))
    return ev


PLAY_KINDS = ("anim", "jump", "land", "move", "turn")


def state_at(fn: dict, ev: list, upto: int, include_self: bool = False) -> dict:
    """The animation state just before line index ``upto`` (or just after it, ``include_self``): window, flags, loops,
    speed, the jump clip and the in-function slot setters -- from the events that DOMINATE it only (a setter in a
    closed sibling branch / another switch case is not on its path; the engine state such a branch leaves when it ran
    in an earlier pass is the 'inherited' uncertainty the site notes record)."""
    st = {"window": None, "window_set": False, "flags": 0, "flags_set": False, "loops": 0, "speed": 16,
          "speed_set": False, "jump": None, "slots": {}, "alt_windows": []}
    lines = fn["lines"]
    for k, kind, p in ev:
        if k > upto or (k == upto and not include_self):
            break
        if not dominates(lines, k, upto):
            if kind == "window" and p["win"] is not None:     # a sibling branch's window: it may have run
                st["alt_windows"].append(p["win"])
            continue
        if kind == "window":
            st["alt_windows"] = []
        if kind == "window":
            st["window"], st["window_set"] = p["win"], True
        elif kind == "flags":
            st["flags"], st["loops"], st["flags_set"] = (p["flags"] or 0), (p["loops"] or 0), True
        elif kind == "loops":
            st["loops"] = p["loops"] or 0
        elif kind == "speed":
            st["speed"], st["speed_set"] = (p["speed"] or 16), True
        elif kind == "set_jump":
            st["jump"] = p
        elif kind == "slot":
            st["slots"][p["slot"]] = p["id"]
        elif kind == "jump":
            st["flags"], st["loops"] = AF_HOLD, 0                  # PREJUMP: animFlag = afHold
            st["window"] = {"kind": "lit", "in": 0, "out": ((st["jump"] or {}).get("j0") or 1) - 1}
        elif kind == "land":
            st["flags"], st["loops"] = 0, 0                        # POSTJUMP: animFlag = 0
            st["window"] = {"kind": "lit", "in": ((st["jump"] or {}).get("j1") or 0) + 1, "out": 255}
        elif kind == "turn":
            st["flags"], st["loops"] = 0, 0                        # TURN: animFlag = 0, window 0..255
            st["window"] = {"kind": "lit", "in": 0, "out": 255}
    return st


def dominates(lines: list, j: int, i: int) -> bool:
    pj, pi = lines[j][1], lines[i][1]
    return len(pj) <= len(pi) and pi[:len(pj)] == pj


def matching_close(lines: list, i: int) -> int:
    """Index of the line that closes the block opened on line ``i`` (a `while (...) {`)."""
    depth = 0
    for k in range(i, len(lines)):
        s = lines[k][2]
        if k > i and s.startswith("}"):
            depth -= 1
            if depth < 0:
                return k
        if s.endswith("{") and k > i:
            depth += 1
        if k == i:
            depth = 0
    return len(lines) - 1


def slot_candidates(slot: str, st: dict, entry_slots: dict) -> list:
    if slot in st["slots"]:
        return [st["slots"][slot]]
    return sorted(set(entry_slots.get(slot, []))) or [None]


def enclosing_loops(lines: list, i: int) -> list:
    """(open, close) of every `while` block that contains line ``i`` (not the site's own), plus the whole function when
    it ends in HW's `loop` (the function restarts: everything after the site ran in the previous pass)."""
    out = []
    path_i = lines[i][1]
    for L in range(i):
        if not lines[L][2].startswith("while") or not lines[L][2].endswith("{"):
            continue
        if L + 1 < len(lines) and len(lines[L + 1][1]) == len(lines[L][1]) + 1 and lines[L + 1][1][-1] in path_i:
            out.append((L, matching_close(lines, L)))
    if lines and lines[-1][2] == "loop":
        out.append((-1, len(lines)))
    return out


def diverges_at_case(fn: dict, k: int, i: int) -> bool:
    """True when line ``k`` sits in a different `case` of a switch the site at ``i`` also sits in (a switch sibling ran
    in an EARLIER pass of a looping function, not on the way to this site)."""
    pk, pi = fn["lines"][k][1], fn["lines"][i][1]
    for d in range(min(len(pk), len(pi))):
        if pk[d] != pi[d]:
            return fn["kinds"].get(pk[d]) == "case"
    return False


def case_block(fn: dict, k: int, i: int):
    """The `case` pseudo-block line ``k`` sits in where its path leaves the site's (None when it does not)."""
    pk, pi = fn["lines"][k][1], fn["lines"][i][1]
    for d in range(min(len(pk), len(pi))):
        if pk[d] != pi[d]:
            return pk[d] if fn["kinds"].get(pk[d]) == "case" else None
    return None


def superseded(lines: list, pre: list, k: int, i: int) -> bool:
    """A play at ``k`` is superseded when a later play before the site lies on every path from it to the site: same
    branch at the same or a shallower depth (its block path a prefix of k's)."""
    pk = lines[k][1]
    return any(k < k2 < i and lines[k2][1] == pk[:len(lines[k2][1])] for k2, _kd, _p in pre)


def slot_cand(base: dict, how: str, sid, after_id) -> dict:
    """A slot candidate. Every one but the walk is the STAND slot (its speed is idleAnimSpeed's draw, not aspeed0)."""
    return dict(base, how=how, id=sid, exec=False, window=None, flags=0, loops=0, speed=16, slot_clip=True,
                after_id=after_id, stand=how != "move:walk")


def site_candidates(fn: dict, ev: list, i: int, form: str, entry_slots: dict, prefer_dur: list) -> tuple:
    """The candidate timelines F reads at line ``i``.
      * a WAIT whose own body replays a play op reads that op's timeline (every iteration re-runs it);
      * otherwise the last DOMINATING play op before the site, plus every play op after it in a closed sibling branch
        (it may or may not have run), plus every LOOP-CARRIED play op (after the site inside an enclosing loop: it ran
        in the previous iteration -- the ladder climb's RunAnimation(LADDER_1_2) after its footstep test);
      * a WaitAnimation between a pre-site clip and the site means the clip has ENDED: a non-held clip has fallen to
        the stand slot (DefaultAnim), a held one is frozen on its last frame;
      * a synchronous walk (InitWalk) has ARRIVED by the site: the body stands; a walk in a wait's own body walks (the
        walk slot) or, at its target, stands (the stand slot): both are candidates -- the bracket;
      * no play op at all: 'inherited' (the stand slot, flagged)."""
    lines = fn["lines"]
    notes = []
    plays = []
    if form == "wait":
        close = matching_close(lines, i)
        plays = [(k, kind, p, "body") for k, kind, p in ev if i < k < close and kind in PLAY_KINDS]
    if not plays:
        pre = [(k, kind, p) for k, kind, p in ev if k < i and kind in PLAY_KINDS]
        dom = [x for x in pre if dominates(lines, x[0], i)]
        last_dom = dom[-1][0] if dom else -1
        plays = [(k, kind, p, "dominating" if dominates(lines, k, i) else
                  ("case_sibling" if diverges_at_case(fn, k, i) else "sibling"))
                 for k, kind, p in pre if k >= last_dom and (k == last_dom or not dominates(lines, k, i))
                 and not superseded(lines, pre, k, i)]
        # the NEAREST preceding switch case is the plausible previous pass (the case that hands over to this one):
        # its end state judges the wait when nothing on the site's own path played; earlier cases stay context
        cs = [x for x in plays if x[3] == "case_sibling"]
        if cs and not any(x[3] in ("dominating", "sibling") for x in plays):
            near = case_block(fn, max(x[0] for x in cs), i)
            plays = [(k, kind, p, "case_prev" if case_block(fn, k, i) == near else w) for k, kind, p, w in plays]
        seen_k = {x[0] for x in plays}
        for lo, hi in enclosing_loops(lines, i):
            if last_dom > lo:                              # this iteration's own play supersedes the previous pass
                continue
            for k, kind, p in ev:
                if lo < k < hi and k > i and kind in PLAY_KINDS and k not in seen_k:
                    plays.append((k, kind, p, "loop_carried"))
                    seen_k.add(k)
    st_site = state_at(fn, ev, i)
    stand_ids = slot_candidates("idle", st_site, entry_slots)
    cands = []
    for k, kind, p, where in plays:
        tier = "carried" if where in ("loop_carried", "case_sibling") else "primary"
        st = state_at(fn, ev, k, include_self=kind in ("jump", "land", "turn"))
        stand_k = slot_candidates("idle", state_at(fn, ev, k), entry_slots)
        base = {"line": lines[k][0], "where": where, "tier": tier, "speed": st["speed"], "speed_set": st["speed_set"],
                "flags": st["flags"], "flags_set": st["flags_set"], "loops": st["loops"],
                "window": st["window"], "window_set": st["window_set"], "after_id": stand_k[0]}
        def after_on_path(kd_want):
            """an event of kind ``kd_want`` after the play on its way to the site: in the play's own branch, or on the
            site's path"""
            return [(kk, pp) for kk, kd, pp in ev if k < kk < i and kd == kd_want
                    and (dominates(lines, kk, i) or dominates(lines, k, kk))]
        pre_site = where in ("dominating", "sibling", "case_sibling", "case_prev")
        ended = pre_site and bool(after_on_path("waitanim"))
        # SetAnimationFlags (AMODE) WRITES animFlag: after the clip it clears afExec / afFreeze, so a stationary body
        # falls to its stand slot (ProcessEvents' SetAnim(idle)) -- 2260 / 2510's held mirror, then (0, 0)
        cleared = pre_site and bool(after_on_path("flags"))
        stand_after = [pp["id"] for kk, pp in after_on_path("slot") if pp["slot"] == "idle"]
        stand_end = [stand_after[-1]] if stand_after else stand_ids
        if kind == "move":
            st_i = state_at(fn, ev, i) if where != "loop_carried" else state_at(fn, ev, k)
            moving = where in ("body", "loop_carried") or not p["sync"]
            if moving:
                ids = slot_candidates("walk", st_i, entry_slots)
                pick = [x for x in ids if x in prefer_dur] or ids
                if len(pick) < len(ids):
                    notes.append(f"walk slot {pick} chosen over {sorted(set(ids) - set(pick))}: the bound names it")
                for sid in pick:
                    cands.append(slot_cand(base, "move:walk", sid, stand_k[0]))
            for sid in slot_candidates("idle", st_i, entry_slots):
                cands.append(slot_cand(base, "move:arrived_idle" if moving else "arrived_idle", sid, sid))
            continue
        if cleared and kind != "move":
            for sid in stand_end:
                cands.append(slot_cand(base, f"{kind}:flags_cleared_stand", sid, sid))
            continue
        if kind == "anim":
            clips = [(p["id"], None)]
        elif kind in ("jump", "land"):
            jid = (st["jump"] or {}).get("id")
            clips = [(j, None) for j in ([jid] if jid else slot_candidates("jump", st, entry_slots))]
        else:                                                  # turn
            clips = [(sid, slot) for slot in ("turn_l", "turn_r") for sid in slot_candidates(slot, st, entry_slots)]
            notes.append("a turn runs at aspeed = frames x 16 / its tick span: frames may skip")
        for cid, slot in clips:
            c = dict(base, how=kind, id=cid, exec=True)
            if slot:
                c.update(slot=slot, speed=16, slot_clip=True)
            if ended:
                if c["flags"] & AF_HOLD and not c["flags"] & (AF_LOOP | AF_PAL):
                    c["ended"] = "held"
                elif c["flags"] & (AF_LOOP | AF_PAL) and not c["loops"]:
                    notes.append("WaitAnimation on an endless loop before the site: the site is unreachable code")
                else:
                    for sid in stand_end:
                        cands.append(slot_cand(base, f"{kind}:ended_stand", sid, sid))
                    continue
            cands.append(c)
            if kind == "anim":                              # a window a sibling branch may have set instead
                for w in st["alt_windows"]:
                    cands.append(dict(c, window=w, window_alt=True, tier="alt"))
    if not cands:
        for sid in stand_ids:
            cands.append(slot_cand({"line": None, "where": "inherited", "tier": "primary", "speed_set": False,
                                    "flags_set": False, "window_set": False}, "inherited_idle", sid, sid))
        notes.append("no play op in the function before the site: the body is on whatever its caller left (idle taken)")
    return cands, notes


EVAL_FIELDS_IGNORED = ("line", "where")


def dedupe_candidates(cands: list) -> list:
    """Merge candidates that evaluate identically (same timeline, window, flags, speed, stand, tier): the first keeps
    its fields, `lines` / `wheres` list every source line that produced it."""
    out, index = [], {}
    for c in cands:
        key = json.dumps({k: v for k, v in c.items() if k not in EVAL_FIELDS_IGNORED}, sort_keys=True)
        if key in index:
            d = index[key]
            if c.get("line") not in d["lines"]:
                d["lines"].append(c.get("line"))
            if c.get("where") not in d["wheres"]:
                d["wheres"].append(c.get("where"))
            continue
        d = {k: v for k, v in c.items() if k not in EVAL_FIELDS_IGNORED}
        d["lines"], d["wheres"] = [c.get("line")], [c.get("where")]
        index[key] = d
        out.append(d)
    return out


def classify_line(s: str) -> str:
    m = COND_RE.match(s)
    if m:
        return m.group(1)
    if s.startswith("SetAnimationInOut("):
        return "window"
    if s.startswith("set "):
        return "set"
    if s.startswith("RunModelCode("):
        return "footstep" if re.match(r"RunModelCode\(\s*1[678]\s*,", s) else "modelcode"
    if s.startswith("Wait("):
        return "timed_wait"
    if s.startswith("TurnInstant("):
        return "turn_interp"
    if s.startswith("MoveInstantXZY("):
        return "move_interp"
    return "other"


# ================================================================================================ THE CENSUS
def census(exports: Path) -> dict:
    """One pass over every export: threshold sites on the player body, duration sites the body evaluates, every other
    frame read, and the counts the summary quotes."""
    files = sorted(exports.glob("test2_*.txt"), key=lambda p: int(p.stem.split("_")[1]))
    thresholds, durations, reads = [], [], collections.Counter()
    shared_hits, conductor_dur, foreign_sites = [], [], []
    fields_98cc, multi_binder = set(), set()
    for f in files:
        exp = parse_export(f)
        facts = entry_facts(exp)
        players = [i for i, x in facts.items() if x["player"]]
        if not players:
            continue
        fields_98cc.add(exp["field"])
        others_cc = [i for i, x in facts.items() if x["cc_funcs"] and not x["player"]]
        if others_cc:
            multi_binder.add(exp["field"])
        body_uids = {facts[i]["uid"] for i in players} | {250}
        body_slots = collections.defaultdict(list)            # a shared script / a conductor reads the BODY's slots
        for i in players:
            for k, v in facts[i]["slots"].items():
                body_slots[k].extend(v)
        shared_of_player = {s for i in players for s in facts[i]["shared"]}
        for e in exp["entries"]:
            ef = facts[e["idx"]]
            # a SHARED script the body starts (RunSharedScript) runs with gCur = the body (EBin: objV0 =
            # FindObjByUID(seq.uid - cSeqOfs)): its 255 and its B_FRAME are the body's
            via_shared = (not ef["player"]) and e["idx"] in shared_of_player
            self_is_body = ef["player"] or via_shared
            for fn in e["funcs"]:
                ev = None
                for i, (ln, _p, s) in enumerate(fn["lines"]):
                    has_f, has_d = "GetEntryAnimFrame(" in s, "GetAnimDuration(" in s
                    if not (has_f or has_d):
                        continue
                    kind = classify_line(s)
                    uids = [int(x) for x in GEAF_RE.findall(s)]
                    on_body = [u for u in uids if (u == 255 and self_is_body) or u in body_uids or 251 <= u <= 254]
                    if via_shared:
                        shared_hits.append({"field": exp["field"], "hw": exp["hw"], "line": ln, "entry": e["idx"],
                                            "kind": kind})
                    if has_d and not self_is_body:
                        if any(u in body_uids for u in uids):
                            conductor_dur.append({"field": exp["field"], "hw": exp["hw"], "line": ln,
                                                  "entry": e["idx"], "kind": kind})
                    if has_d and self_is_body:
                        for j, d in enumerate(GAD_RE.findall(s)):
                            durations.append({"key": f"{exp['field']}:{ln}:{d}:{j}", "field": exp["field"],
                                              "via_shared": via_shared,
                                              "hw": exp["hw"], "line": ln, "entry": e["idx"], "func": fn["num"],
                                              "func_label": fn["label"], "id": int(d), "use": kind,
                                              "frame_threshold": has_f})
                    if not has_f:
                        continue
                    if not on_body:
                        if kind in ("while", "if") and self_is_body:
                            foreign_sites.append({"field": exp["field"], "line": ln, "uids": uids})
                        continue
                    if kind not in ("while", "if"):
                        reads[kind] += 1
                        continue
                    cond = COND_RE.match(s).group(2)
                    py, dur_ids, atoms, foreign = cond_to_py(cond, body_uids, self_is_body)
                    if ev is None:
                        ev = scan_function(fn, body_uids, self_is_body, {ef["uid"]} if self_is_body else set())
                    form = "wait" if kind == "while" else "test"
                    rhs = None
                    if len(atoms) >= 1:
                        a = atoms[0]
                        if a[3]:
                            rhs = {"kind": "dur", "id": int(a[3]), "k": int(a[5]) * (-1 if a[4] == "-" else 1)}
                        elif a[6]:
                            rhs = {"kind": "dur", "id": int(a[6]), "k": 0}
                        else:
                            rhs = {"kind": "lit", "value": int(a[2])}
                    target_kind = ("self" if (255 in uids and self_is_body) else
                                   "control" if 250 in uids else
                                   "party" if any(251 <= u <= 254 for u in uids) else "uid")
                    slots = ef["slots"] if ef["player"] else dict(body_slots)
                    cands, notes = site_candidates(fn, ev, i, form, slots, dur_ids)
                    if foreign:
                        notes.append(f"the condition also reads non-body frames {sorted(set(foreign))} (neutral)")
                    mixed = bool(re.search(r"\bU\b", py))
                    if mixed:
                        notes.append("non-frame terms in the condition are taken as neutral (keep a wait / let a test)")
                    if not self_is_body:
                        notes.append("a CONDUCTOR site: B_FRAME reads the conductor's go (stock), not the body")
                    speeds_src = ef["idle_speed"] if ef["player"] else [v for i in players
                                                                        for v in facts[i]["idle_speed"]]
                    stand_speeds = sorted({v for row in speeds_src for v in row if v}) or [16]
                    thresholds.append({
                        "key": f"{exp['field']}:{ln}", "field": exp["field"], "hw": exp["hw"], "line": ln,
                        "stand_speeds": stand_speeds,
                        "entry": e["idx"], "entry_uid": ef["uid"], "func": fn["num"], "func_label": fn["label"],
                        "form": form, "op": atoms[0][1] if atoms else ("truth" if not mixed else "expr"),
                        "atoms": [[x[1], x[2]] for x in atoms], "cond_py": py, "rhs": rhs, "dur_ids": dur_ids,
                        "target": {"uids": sorted(set(uids)), "kind": target_kind}, "gcur_is_body": self_is_body,
                        "via_shared": via_shared,
                        "multi_binder": exp["field"] in multi_binder, "candidates": cands,
                        "notes": list(dict.fromkeys(notes))})
    return {"files": len(files), "thresholds": thresholds, "durations": durations, "reads": dict(reads),
            "fields_98cc": sorted(fields_98cc), "multi_binder": sorted(multi_binder), "shared_hits": shared_hits,
            "conductor_dur": conductor_dur, "foreign_sites": foreign_sites}


# ================================================================================================ THE FRAME TABLE
RIG_NAMES = ("zidane", "vivi", "garnet", "steiner", "freya", "quina", "eiko", "amarant", "moogle",
             "cinna", "marcus", "blank", "beatrix")
COLS = ("model", "idle", "walk", "run", "turn_l", "turn_r", "eye", "inactive", "walk_step_a", "walk_step_b",
        "run_step_a", "run_step_b", "step_sound", "idle_alias", "hand_bone", "hand_bone_end")


def rig_rows() -> list:
    """The 13 rig rows: 0-8 = s139's NetSyncVisitor.Rigs (rigs_8_11.S139_ROWS, the shipped table), 9-12 = the census
    rows of rigs_8_11.json (orchestrator O1: rig 9 Cinna, 10 Marcus, 11 Blank, 12 Beatrix)."""
    sys.path.insert(0, str(HERE))
    import rigs_8_11 as R                                  # noqa: E402 - the sibling census (pins this tree's kit)
    rows = [dict(zip(COLS, r)) for r in R.S139_ROWS]
    rj = json.loads(RIGS_JSON.read_text(encoding="utf-8"))
    for k in ("9", "10", "11", "12"):
        rows.append(dict(zip(COLS, rj["rows"][k]["row"])))
    return rows


def frame_table(game: Path, memoria: Path, clip_ids: set) -> dict:
    sys.path.insert(0, str(HERE))
    import rigs_8_11 as R                                  # noqa: E402
    tables = R.load_tables(memoria)
    loco = json.loads(LOCO_JSON.read_text(encoding="utf-8"))
    inst = R.Install(game)
    rigs = []
    for n, row in enumerate(rig_rows()):
        ids = {s: row[s] for s in ("idle", "walk", "run", "turn_l", "turn_r", "inactive", "idle_alias")}
        frames = {s: (inst.frames(row["model"], v)["frames"] if v else None) for s, v in ids.items()}
        rigs.append({"rig": n, "name": RIG_NAMES[n], "model": row["model"], "ids": ids, "frames": frames})
    engine_map = {row[0]: row[1] for row in loco["engine_map"]}     # the engine's CLOSED full-name map, default OTHER
    clips = {}
    for cid in sorted(i for i in clip_ids if i):
        name = tables["anim"].get(cid)
        cls = engine_map.get(name, "OTHER") if name else "OTHER"
        fr = inst.frames(98, cid)
        clips[str(cid)] = {"name": name, "class": cls, "src_frames": fr["frames"],
                           "located": fr.get("located")}
    rj = json.loads(RIGS_JSON.read_text(encoding="utf-8"))
    cross = {}
    for r in rigs:
        want = rj["frames_13"][str(r["rig"])]
        diff = {s: [r["frames"].get(s), want.get(s)] for s in ("idle", "walk", "run", "turn_l", "turn_r", "inactive",
                                                                 "idle_alias") if r["frames"].get(s) != want.get(s)}
        if diff:
            cross[str(r["rig"])] = diff
    return {"rigs": rigs, "clips": clips, "cross_check_rigs_8_11": cross or "every rig x slot equals frames_13",
            "kit_anim_table_vs_memoria": f"{tables['kit_anim_mismatch_n']} differing ids"}


# ================================================================================================ BUILD + SUMMARY
def judged_candidates(site: dict) -> list:
    """The candidates evaluate_site judges a site on (waits: the primary tier, else all; tests: all)."""
    if site["form"] != "wait":
        return list(site["candidates"])
    j = [c for c in site["candidates"] if c.get("tier", "primary") == "primary"]
    return j or list(site["candidates"])


def path_family(c: dict) -> str:
    """Which s140 path a candidate takes: 'loco' (a loco-family clip -> the rig's native clip), 'inactive' (BREAK1_*:
    native on a rig with an inactive clip, else the gesture path), 'slot_gesture' (a stand / walk / run / turn slot
    holding a gesture clip -> the rig's idle, native), 'gesture' (a RunAnimation gesture -> KeepSourceTimeline), 'jump'
    (AJUMP's slot: the idle alias, its frame count put back to the SOURCE clip's by KeepJumpTimeline -- the source
    timeline, as a gesture; every stock jump / land id is a gesture class)."""
    if c["how"] in ("jump", "land"):
        return "jump"
    if c["class"] in SLOT_OF_CLASS:
        return "loco" if c["class"] != "INACTIVE" else "inactive"
    return "slot_gesture" if c.get("slot_clip") else "gesture"


def summarize(doc: dict, ev: dict) -> dict:
    sites = {s["key"]: s for s in doc["threshold_sites"]}
    rigs = doc["frame_table"]["rigs"]
    clips = doc["frame_table"]["clips"]

    def nm(cid):
        return (clips.get(str(cid), {}).get("name") or "?").replace("ANH_MAIN_F0_ZDN_", "ZDN_")

    def res_row(x):
        return [x["verdict"], x["bound"], x["frame_n"], x["max_frame"], x["first_tick"]]
    forms = collections.Counter()
    by_family = collections.Counter()
    for s in sites.values():
        b = (s["rhs"] or {}).get("kind")
        forms[f"{s['form']} {s['op']} {b}" + (" (via shared script)" if s.get("via_shared") else "")
              + ("" if s["gcur_is_body"] else " (conductor)")] += 1
        fams = "+".join(sorted({path_family(c) for c in judged_candidates(s)}))
        by_family[f"{s['form']}: {fams}"] += 1
    bad = {law: sorted(k for k, v in ev["sites"].items() if any(x in ("wedge", "never") for x in v[law].values()))
           for law in LAWS}
    late = {law: sorted(k for k, v in ev["sites"].items() if any(x == "ok_after_clip" for x in v[law].values()))
            for law in LAWS}
    wedge_rigs = {law: {k: sorted(int(r) for r, x in ev["sites"][k][law].items() if x in ("wedge", "never"))
                        for k in bad[law]} for law in LAWS}
    # the BOUNDED waits (every wait form but `!= 0`): the audit's 18, with the clip, its s140 path and per rig
    # [verdict, bound, frameN, max frame, first tick the wait ends]
    bounded = []
    for k, s in sites.items():
        if s["form"] != "wait" or (s["op"] == "!=" and (s["rhs"] or {}).get("value") == 0):
            continue
        det = evaluate_site(s, rigs, clips)["detail"]
        js = judged_candidates(s)
        idx = [s["candidates"].index(c) for c in js]
        row = {"key": k, "func": s["func_label"], "cond": s["cond_py"],
               "clips": sorted({f"{nm(c['id'])} ({c['class']}, {path_family(c)}, src {c['src_frames']})"
                                for c in js}),
               "bound_kind": s["rhs"]["kind"]}
        for law in LAWS:
            row[law] = {}
            for r in rigs:
                res = [res_row(det[law][str(r["rig"])][n]) for n in idx]
                uniq = []
                for x in res:
                    if x not in uniq:
                        uniq.append(x)
                row[law][str(r["rig"])] = uniq[0] if len(uniq) == 1 else uniq
        bounded.append(row)
    # field 2705: the BRACKET -- which rigs wedge on the walk branch (the body moving) vs the stand branch (arrived)
    f2705 = {}
    for k, s in sites.items():
        if s["field"] != 2705 or not s["rhs"] or s["rhs"]["kind"] != "dur":
            continue
        det = evaluate_site(s, rigs, clips)["detail"]
        per = {}
        for law in LAWS:
            per[law] = {}
            for branch in ("move:walk", "move:arrived_idle"):
                idx = [n for n, c in enumerate(s["candidates"]) if c["how"] == branch]
                per_rig = {}
                for r in rigs:
                    rows = []
                    for n in idx:
                        x = res_row(det[law][str(r["rig"])][n])
                        if x not in rows:
                            rows.append(x)
                    per_rig[str(r["rig"])] = rows
                per[law][branch] = {"wedge_rigs": sorted({r["rig"] for r in rigs for n in idx
                                                          if det[law][str(r["rig"])][n]["verdict"] == "wedge"}),
                                    "per_rig": per_rig}
        f2705[k] = per
    # waits whose bound is a LITERAL on a timeline the dress runs natively (loco / a slot -- never the jump slot, which
    # KeepJumpTimeline keeps on the source timeline): the hook cannot remap them, so only the frame margin keeps them
    # reachable
    loco_literal = []
    for k, s in sites.items():
        js = judged_candidates(s)
        if s["form"] == "wait" and s["rhs"] and s["rhs"]["kind"] == "lit" \
                and not (s["op"] == "!=" and s["rhs"]["value"] == 0) \
                and any(path_family(c) in ("loco", "slot_gesture", "inactive") for c in js):
            loco_literal.append({"key": k, "func": s["func_label"], "cond": s["cond_py"],
                                 "clips": sorted({f"{nm(c['id'])} ({c['class']}, {path_family(c)})" for c in js}),
                                 "min_s140_frame_n": min(timeline_frames(c, r, "s140") for c in js for r in rigs)})
    dur = collections.defaultdict(dict)
    for d in doc["duration_sites"]:
        mm = ev["durations"].get(d["key"], {})
        for law in LAWS:
            if mm.get(law):
                dur[law][f"{d['key']} {nm(d['id'])} ({clips[str(d['id'])]['class']}, {d['use']})"] = mm[law]
    return {"threshold_sites": len(sites), "waits": sum(1 for s in sites.values() if s["form"] == "wait"),
            "tests": sum(1 for s in sites.values() if s["form"] == "test"),
            "forms": dict(forms.most_common()), "judged_path_families": dict(by_family.most_common()),
            "unreachable_by_law": bad, "unreachable_rigs_by_law": wedge_rigs, "late_by_law": late,
            "bounded_waits": bounded, "field_2705": f2705, "loco_family_literal_waits": loco_literal,
            "duration_reads": len(doc["duration_sites"]),
            "duration_mismatch_by_law": {law: dur[law] for law in LAWS}}


def build(exports: Path, game: Path, memoria: Path) -> dict:
    cen = census(exports)
    clip_ids = set()
    for s in cen["thresholds"]:
        clip_ids.update(int(d) for d in s["dur_ids"])
        for c in s["candidates"]:
            for key in ("id", "after_id"):
                if c.get(key):
                    clip_ids.add(int(c[key]))
            w = c.get("window")
            if w and w.get("kind") == "expr":
                clip_ids.update(int(d) for d in w["dur_ids"])
    for d in cen["durations"]:
        clip_ids.add(int(d["id"]))
    ft = frame_table(game, memoria, clip_ids)

    def clip_of(cid):
        return ft["clips"].get(str(cid), {}) if cid else {}
    for s in cen["thresholds"]:
        for c in s["candidates"]:
            c["class"] = clip_of(c.get("id")).get("class", "OTHER")
            c["src_frames"] = clip_of(c.get("id")).get("src_frames") or 1
            a = c.pop("after_id", None)                      # the stand slot DefaultAnim falls back to
            c["after"] = ({"id": a, "class": clip_of(a).get("class", "OTHER"),
                           "src_frames": clip_of(a).get("src_frames") or 1} if a else None)
            for k in ("speed_set", "flags_set", "window_set"):  # provenance flags: kept only when True
                if not c.get(k):
                    c.pop(k, None)
        s["candidates"] = dedupe_candidates(s["candidates"])
    doc = {
        "tool": "studies/battle-coop/dress-census/bframe_census.py",
        "sources": {"exports": f"{cen['files']} HW exports, first language block", "game_p0data5": str(game),
                    "memoria_tables": "FF9DBAll.Animation.cs (AnimationDB names)",
                    "loco_classes": "loco_table.json `table` (class by NAME)",
                    "rig_rows": "s139 Rigs 0-8 (rigs_8_11.S139_ROWS) + rigs_8_11.json rows 9-12",
                    "frame_formula": "round(length x rate) + 1 (EventEngineUtils.GetCharAnimFrame)"},
        "laws": {"stock": "undressed: every clip on its own timeline, B_FRAME = its own length (the calibration)",
                 "s140": "loco family -> the rig's NATIVE clip + B_FRAME native (the hook); gesture -> SOURCE timeline "
                         "(KeepSourceTimeline) + B_FRAME stock; the jump slot -> the idle alias on the SOURCE timeline "
                         "(KeepJumpTimeline); a stand/walk/run/turn slot's gesture -> the rig's idle, native; rig 0 stock",
                 "bframe_off": "slots native, B_FRAME = the raw clip (leg T3's red, `selfdress law bframe off`); a "
                               "gesture and the jump slot still on the SOURCE timeline (the timeline law is on)",
                 "timeline_off": "gesture and the jump slot -> the idle alias at its own native length (`selfdress law "
                                 "timeline off`: KeepSourceTimeline and KeepJumpTimeline both off)"},
        "engine_model": ["ProcessAnime exec forward: NextFrame (aspeed/16 per tick, frameDif carry) > min(outFrame, "
                         "frameN - 1) -> AnimLoop (loop/palindrome, loopCount) else AnimStop (afHold freezes at the "
                         "last frame; otherwise DefaultAnim -> the idle at frame 0)",
                         "ProcessAnime slot (non-exec): NextFrame >= frameN -> frame 0",
                         "ExecAnim: animFrame = inFrame (uncapped), frameN = GetCharAnimFrame(go, anim)",
                         "B_FRAME = GetCharAnimFrame(gCur.go, id): gCur is the object running the function",
                         "GetObjUID: 255 = gCur, 250 = controlUID, 251-254 = partyUID; InitObject uid 0 = the entry id",
                         "RunJumpAnimation: animFlag = afHold, window 0..jump0-1; RunLandAnimation: animFlag = 0, "
                         "window jump1+1..255",
                         "dressed jump slot: ExecAnim(actor.jump = the idle alias), then KeepJumpTimeline: frameN = "
                         "GetCharAnimFrame(go, netJumpSrc) for a gesture while the timeline law is on",
                         "reachability cannot tell KeepJumpTimeline on from off (the alias covers every stock jump "
                         "window): its tick law is pinned against battlewire.jump_frame_n, not by these verdicts"],
        "counts": {"fields_with_98cc": len(cen["fields_98cc"]), "multi_binder_fields": len(cen["multi_binder"]),
                   "frame_reads_not_thresholds": cen["reads"],
                   "shared_script_frame_or_duration_lines": len(cen["shared_hits"]),
                   "conductor_duration_lines_on_body": len(cen["conductor_dur"]),
                   "player_entry_conditions_on_other_bodies": len(cen["foreign_sites"])},
        "frame_table": ft,
        "threshold_sites": cen["thresholds"],
        "duration_sites": cen["durations"],
        "shared_hits": cen["shared_hits"],
        "conductor_duration_lines": cen["conductor_dur"],
    }
    ev = evaluate_all(doc)
    doc["verdict_legend"] = {"order": "rig 0..12 (frame_table.rigs)", "codes": VERDICT_CODE}
    doc["verdicts"] = {k: verdict_codes(v) for k, v in ev["sites"].items()}
    doc["duration_mismatch"] = ev["durations"]
    doc["summary"] = summarize(doc, ev)
    return doc


ONE_LINE_LISTS = ("threshold_sites", "duration_sites", "shared_hits", "conductor_duration_lines")


def dumps(doc: dict) -> str:
    """Readable but compact: the big site lists hold one record per line; everything else is indented."""
    def one(v):
        return json.dumps(v, ensure_ascii=False, separators=(",", ":"))
    out = ["{"]
    keys = list(doc)
    for n, k in enumerate(keys):
        tail = "," if n < len(keys) - 1 else ""
        v = doc[k]
        if k in ONE_LINE_LISTS:
            out.append(f" {json.dumps(k)}: [")
            out.extend(f"  {one(x)}" + ("," if j < len(v) - 1 else "") for j, x in enumerate(v))
            out.append(" ]" + tail)
        elif k == "verdicts":
            out.append(f" {json.dumps(k)}: {{")
            items = list(v.items())
            out.extend(f"  {json.dumps(sk)}: {one(sv)}" + ("," if j < len(items) - 1 else "")
                       for j, (sk, sv) in enumerate(items))
            out.append(" }" + tail)
        else:
            body = json.dumps(v, indent=1, ensure_ascii=False)
            out.append(f" {json.dumps(k)}: " + body.replace("\n", "\n ") + tail)
    out.append("}")
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--exports", type=Path, default=DEFAULT_EXPORTS)
    ap.add_argument("--game", type=Path, default=DEFAULT_GAME)
    ap.add_argument("--memoria", type=Path, default=DEFAULT_MEMORIA)
    ap.add_argument("--out", type=Path, default=OUT)
    ap.add_argument("--check", action="store_true", help="rebuild in memory and diff the frozen JSON (exit 1 on drift)")
    ap.add_argument("--evaluate", action="store_true", help="re-evaluate the FROZEN sites only (no install, no exports)")
    a = ap.parse_args(argv)
    if a.evaluate:
        doc = json.loads(a.out.read_text(encoding="utf-8"))
        ev = evaluate_all(doc)
        drift = [k for k in ev["sites"] if verdict_codes(ev["sites"][k]) != doc["verdicts"].get(k)]
        print(f"re-evaluated {len(ev['sites'])} frozen sites: {len(drift)} differ from the frozen verdicts")
        for k in drift[:20]:
            print("  ", k)
        return 1 if drift else 0
    doc = build(a.exports, a.game, a.memoria)
    text = dumps(doc)
    if a.check:
        old = a.out.read_text(encoding="utf-8") if a.out.exists() else ""
        if old != text:
            print(f"DRIFT: {a.out} differs from a fresh build")
            return 1
        print(f"OK: {a.out} equals a fresh build")
        return 0
    a.out.write_text(text, encoding="utf-8", newline="\n")       # LF on every platform
    sm = doc["summary"]
    print(f"wrote {a.out}: {sm['threshold_sites']} threshold sites ({sm['waits']} waits, {sm['tests']} tests), "
          f"{sm['duration_reads']} body duration reads")
    for law in LAWS:
        print(f"  {law:12s} unreachable: {sm['unreachable_rigs_by_law'][law]}  late: {sm['late_by_law'][law]}")
    for k, v in sm["field_2705"].items():
        print(f"  {k} bframe_off wedges: walk branch {v['bframe_off']['move:walk']['wedge_rigs']}, "
              f"stand branch {v['bframe_off']['move:arrived_idle']['wedge_rigs']}")
    print("  literal-bound waits on a native timeline:",
          [(r["key"], r["min_s140_frame_n"]) for r in sm["loco_family_literal_waits"]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
