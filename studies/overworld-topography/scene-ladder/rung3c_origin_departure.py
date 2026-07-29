"""Scene ladder rung 3c: ORIGIN-PORT DEPARTURES -- sail out from the port the player boarded at.

Supersedes rung3_arrival's director + prologue (deploy ON TOP of the rung-3 world; ship init,
rigs, anchor tags, port snaps, the confirm vignette all carried verbatim). Until now every
voyage staged its sail-OUT at Ashvale (the ship's home mooring); this rung classifies the
ORIGIN port and stages the departure theater THERE, using the rung-3 ARRIVE lanes reversed --
fully symmetric voyages: leave from where you boarded, arrive where you booked.

THE CLASSIFIER -- and the flaw found in the banked design: the design said to read the
anchor's saved world position (Global.Int24[64]/Int24[69]) in the departure prologue. But the
ferry arm's STAGE PRESET (worldexit arrive_writes -> the Lantern Quay) overwrites those vars
in the hall, BEFORE the world loads -- the prologue would always read (60,-1168) and classify
Ashvale: a silent no-op. The repair is hall-side: the kit's depart arm now caches
Global.Int24[64] (the mirror's record of where the player STOOD when they entered the hall,
intact all through the hall visit) into Global.Int24[flags.FERRY_ORIGIN_X_INT24] (=1873)
BEFORE the preset clobbers it (content/choice.py; requires the 6601 hall redeploy). The
prologue box-tests that cached X against the quay trigger positions -- X alone separates all
four quays (48/420/1204/700, boxes +-64u) -- and 0/garbage/stale-non-quay values default to
Ashvale, today's exact behavior (the canonical New-Game hub->hall path, never on the world,
cache = 0 -> Ashvale). Dropping the stage preset instead was REJECTED: a never-on-world
player would spawn at garbage coords -- the actor-brick class.

Signed-compare verdict (the design's flagged risk): SOUND. EBin.cs:1858-1861 reads Int24 with
the top byte cast SByte before <<16 (sign-extends into Int32), and B_MINUS/B_LT are signed
Int32 (THE TWO-DOMAIN POSITION LAW). Moot for the classifier anyway -- X is always positive.

THE DEPARTURE THEATER (probe_departure_lanes.py, all out-lanes + eyes WET):
  behind the prologue's held black: ship -> ORIGIN dock at its moor face (docked, bow
  inland -- the diegetic "the ferry that brought you"), hidden anchor -> ORIGIN shore
  (tags 61-64; the theater must not play ~1100u from the anchor -- rung 3 always had the
  anchor snapped near its theater, streaming/epoch discipline), rigs disposed + re-armed
  (their ship-relative init lands at the new dock; op_22(2) first so the prologue-armed
  rigs finish constructing before disposal), eye overridden per port (MoveInstantXZYEx
  after an op_22 settle -- THE ORDER LAW), reveal, hold, then the ship comes about and
  sails dock -> far_pre (28u), rides THROUGH the closing fade to far (40u) -- the proven
  Ashvale departure geometry generalized to every port. The arrival half is rung 3
  verbatim. Origin 1 reproduces today's Ashvale departure (same dock, legs, speed; the
  eye now sits at the probed (15,-1180) instead of ship-relative).

  port 1 Ashvale : dock (29,-1168)   moor 192  far (29,-1208)    eye (15,-1180)
  port 2 Tidefall: dock (394,-1232)  moor 192  far (354,-1232)   eye (382,-1218)
  port 3 Grimhorn: dock (1182,-1192) moor 192  far (1142,-1192)  eye (1170,-1178)
  port 4 Larkspur: dock (726.5,-616) moor 64   far (766.5,-616)  eye (738.5,-630)

Booking passage to the port you are at plays out-and-back-in at one quay -- no special case.

Deploy: py rung3c_origin_departure.py --deploy   (7 languages, hot; requires rungs 0-3
        deployed AND the 3c hall redeploy -- without the hall, the cache byte stays 0 and
        every departure classifies Ashvale, exactly the pre-3c behavior)
Revert: py rung3_arrival.py --deploy (the always-Ashvale departure, rung 3 v2)
"""
import argparse
import pathlib
import shutil
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ff9mapkit"))

from ff9mapkit import config                                          # noqa: E402
from ff9mapkit import flags as FLAGS                                  # noqa: E402
from ff9mapkit.world.entrance import _WORLD_EB_SUBDIR                 # noqa: E402
from ff9mapkit.eb.model import EbScript                               # noqa: E402
from ff9mapkit.eb import edit as E                                    # noqa: E402
from ff9mapkit.eb.cmdasm import assemble_block, disassemble_block     # noqa: E402

MOD_FOLDER = "FF9CustomMap-world"
FNAME = "EVT_WORLD_WORLD11.eb.bytes"
LANGS = ("us", "uk", "jp", "es", "fr", "gr", "it")

SHIP_UID, EYE_UID, AIM_UID, ANCHOR_UID = 16, 17, 18, 14
ANIM_ID = 5106
SHIP = (29, -1168, 200)
SHIP_FACE = 192
SAIL_TO_Z = -1208
SAIL_SPEED = 60
ARRIVE_SPEED = 36                    # statelier than the departure's 60 (v2: shorter lane)
PHASE = 50                           # Map.Byte[50] -- scene phase (1c)
PORT_CACHE = 51                      # Map.Byte[51] -- the cached destination code
ORIGIN_CACHE = 52                    # Map.Byte[52] -- the classified ORIGIN port (free: stock
                                     # census 24-42; ours 50/51)
DEPART_BYTE = 1872                   # Global.Byte -- flags.py FERRY_DEPART_BYTE
ORIGIN_X = FLAGS.FERRY_ORIGIN_X_INT24  # Global.Int24 -- the hall-entry X cache (x256)

SHIP_Y = 200                         # the proven at-sea y arg (draft), all waters
EYE_UP = 7.0

# The origin classifier: quay trigger X per port code (mint_quay_beacon.SITES trigger_at --
# where the player STANDS when the hall entrance fires), box +-64u. Port 1 is the default,
# so only 2-4 are tested; the boxes are disjoint (48/420/1204/700).
QUAY_X = {2: 420.0, 3: 1204.0, 4: 700.0}
ORIGIN_BOX = 64.0

# Per-port shore snap (rung 2a, probed ground heights -- unchanged, tags live on the anchor).
PORTS = [
    (61, 60.0, -1168.0, 192, 3.0),   # 1 Ashvale (the Lantern Quay)
    (62, 432.0, -1232.0, 192, 3.2),  # 2 Tidefall
    (63, 1214.0, -1192.0, 192, 3.2), # 3 Grimhorn (desert ground)
    (64, 688.0, -616.0, 64, 3.23),   # 4 Larkspur (west = inland)
]

# Per-port ARRIVAL theater (rung 3 v2, unchanged): anchor tag, approach(x,z), dock(x,z),
# sail heading, moor face, eye(x,z) at +EYE_UP. Close-in per THE FOG-FRAMING LAW.
ARRIVE = [
    (61, (29.0, -1188.0), (29.0, -1168.0), 128, 192, (21.0, -1196.0)),
    (62, (374.0, -1232.0), (394.0, -1232.0), 192, 192, (366.0, -1224.0)),
    (63, (1162.0, -1192.0), (1182.0, -1192.0), 192, 192, (1154.0, -1184.0)),
    (64, (746.5, -616.0), (726.5, -616.0), 64, 64, (754.5, -624.0)),
]

# Per-port DEPARTURE theater (3c, probe_departure_lanes.py all-wet): anchor tag, dock(x,z),
# moor face, far_pre(x,z) = dock+28u out (the fade starts), far(x,z) = dock+40u out (the
# leg ridden through the closing fade), eye(x,z) = dock + 12u out + 14u abeam on the
# arrival eye's proven-wet side. Outbound = the ARRIVE lane reversed.
DEPART = [
    (61, (29.0, -1168.0), 192, (29.0, -1196.0), (29.0, -1208.0), (15.0, -1180.0)),
    (62, (394.0, -1232.0), 192, (366.0, -1232.0), (354.0, -1232.0), (382.0, -1218.0)),
    (63, (1182.0, -1192.0), 192, (1154.0, -1192.0), (1142.0, -1192.0), (1170.0, -1178.0)),
    (64, (726.5, -616.0), 64, (754.5, -616.0), (766.5, -616.0), (738.5, -630.0)),
]

CONFIRM_ON = 131072
RADIUS_FP = 3072

FADE_OUT = "FadeFilter(2, 24, 0, 255, 255, 255)\nop_22(25)"
FADE_IN = "FadeFilter(3, 16, 0, 0, 0, 0)\nop_22(17)"


def fp(v) -> int:
    return int(v * 256) & 0xFFFFFFFF


def up_arg(h: float) -> int:
    return (-int(h * 256)) & 0xFFFF


def ship_rel(axis: int, up_units: float = 0.0, lateral: float = 0.0) -> str:
    if axis == 1:
        n = int(abs(up_units) * 256)
        op = "B_MINUS" if up_units > 0 else "B_PLUS"
    else:
        n = int(abs(lateral) * 256)
        op = "B_PLUS" if lateral > 0 else "B_MINUS"
    base = f"obj(uid={SHIP_UID}).f[{axis}]"
    if n == 0:
        return f"{{{base} B_EXPR_END}}"
    return f"{{{base} const4({n}) {op} B_EXPR_END}}"


# --- rung2a v11 bodies, carried verbatim (ship init, rigs, anchor hide/show, port snaps) ---

SHIP_INIT = f"""
SetObjectIndex(0)
SetModel(313, 100)
SetObjectFlags(1)
SetObjectLogicalSize(0, 0, 0)
SetObjectSize({SHIP_UID}, 100, 100, 100)
SetStandAnimation({ANIM_ID})
SetWalkAnimation({ANIM_ID})
op_35({ANIM_ID})
MoveInstantXZY({{const4({fp(SHIP[0])}) B_EXPR_END}}, {{const({SHIP[2]}) B_EXPR_END}}, {{const4({fp(SHIP[1])}) B_EXPR_END}})
TurnInstant({{const({SHIP_FACE}) B_EXPR_END}})
RET()
"""

EYE_INIT = f"""
0xB7()
SetObjectLogicalSize(0, 0, 0)
MoveInstantXZY({ship_rel(0, lateral=-17)}, {ship_rel(1, up_units=7)}, {ship_rel(2, lateral=-14)})
SetWalkSpeed(8)
SetWalkTurnSpeed(1)
RET()
"""

EYE_LOOP = f"""
L0:
SET({{Map.Byte[{PHASE}] const(1) B_EQ Map.Byte[{PORT_CACHE}] B_NOT B_ANDAND B_EXPR_END}})
JMP_IFNOT(L60)
InitWalk()
WalkXZY({ship_rel(0, lateral=-10)}, {ship_rel(1, up_units=6)}, {ship_rel(2, lateral=-10)})
L40:
op_22(1)
JMP(L40)
L60:
op_22(1)
JMP(L0)
"""

AIM_INIT = f"""
0xB8()
SetObjectLogicalSize(0, 0, 0)
MoveInstantXZY({ship_rel(0)}, {ship_rel(1)}, {ship_rel(2)})
SetWalkTurnSpeed(1)
RET()
"""

AIM_LOOP = f"""
L0:
MoveInstantXZY({ship_rel(0)}, {ship_rel(1)}, {ship_rel(2)})
op_22(1)
JMP(L0)
"""

HIDE_TAG, SHOW_TAG = 65, 66

ANCHOR_HIDE = """
SetObjectFlags(4)
RET()
"""

ANCHOR_SHOW = """
SetObjectFlags(5)
RET()
"""


def port_tag_body(x: float, z: float, face: int, ground_y: float) -> str:
    y_arg = (-int(ground_y * 256)) & 0xFFFF
    return f"""
MoveInstantXZY({{const4({fp(x)}) B_EXPR_END}}, {{const({y_arg}) B_EXPR_END}}, {{const4({fp(z)}) B_EXPR_END}})
TurnInstant({{const({face}) B_EXPR_END}})
RET()
"""


# --- the director: THE ORIGIN DEPARTURE + the arrival theater + the 1c confirm vignette ---

def _switch(bodies: list, tagpfx: str, byte_idx: int = PORT_CACHE) -> str:
    """Emit a Map.Byte[byte_idx] switch: bodies[0..3] for ports 1..4 (last = default)."""
    lines = []
    for i, body in enumerate(bodies[:-1], start=1):
        lines.append(f"SET({{Map.Byte[{byte_idx}] const({i}) B_EQ B_EXPR_END}})")
        lines.append(f"JMP_IFNOT(L{tagpfx}{i})")
        lines.append(body.strip())
        lines.append(f"JMP(L{tagpfx}D)")
        lines.append(f"L{tagpfx}{i}:")
    lines.append(bodies[-1].strip())
    lines.append(f"L{tagpfx}D:")
    return "\n".join(lines)


def _relocate_body(entry) -> str:
    tag, (apx, apz), _dock, heading, _moor, _eye = entry
    return f"""
MoveInstantXZY({{const4({fp(apx)}) B_EXPR_END}}, {{const({SHIP_Y}) B_EXPR_END}}, {{const4({fp(apz)}) B_EXPR_END}})
TurnInstant({{const({heading}) B_EXPR_END}})
RunScriptSync(6, {ANCHOR_UID}, {tag})
"""


def _eye_body(entry) -> str:
    _tag, _ap, _dock, _h, _m, (ex, ez) = entry
    return f"""
MoveInstantXZYEx({EYE_UID}, {{const4({fp(ex)}) B_EXPR_END}}, {{const({up_arg(EYE_UP)}) B_EXPR_END}}, {{const4({fp(ez)}) B_EXPR_END}})
"""


def _sail_in_body(entry) -> str:
    _tag, _ap, (dx, dz), _h, _m, _eye = entry
    return f"""
InitWalk()
WalkXZY({{const4({fp(dx)}) B_EXPR_END}}, {SHIP_Y}, {{const4({fp(dz)}) B_EXPR_END}})
"""


def _moor_body(entry) -> str:
    _tag, _ap, _dock, _h, moor, _eye = entry
    return f"""
TurnInstant({{const({moor}) B_EXPR_END}})
"""


# 3c: the origin-staging bodies (keyed on Map.Byte[ORIGIN_CACHE]).

def _origin_stage_body(entry) -> str:
    """Ship (self) to the origin DOCK at its moor face -- docked, the ferry that brought you --
    and the hidden anchor to the origin shore (the theater plays around the anchor)."""
    tag, (dx, dz), moor, _fp_, _far, _eye = entry
    return f"""
MoveInstantXZY({{const4({fp(dx)}) B_EXPR_END}}, {{const({SHIP_Y}) B_EXPR_END}}, {{const4({fp(dz)}) B_EXPR_END}})
TurnInstant({{const({moor}) B_EXPR_END}})
RunScriptSync(6, {ANCHOR_UID}, {tag})
"""


def _origin_eye_body(entry) -> str:
    _tag, _dock, _moor, _fp_, _far, (ex, ez) = entry
    return f"""
MoveInstantXZYEx({EYE_UID}, {{const4({fp(ex)}) B_EXPR_END}}, {{const({up_arg(EYE_UP)}) B_EXPR_END}}, {{const4({fp(ez)}) B_EXPR_END}})
"""


def _origin_leg1_body(entry) -> str:
    _tag, _dock, _moor, (px, pz), _far, _eye = entry
    return f"""
InitWalk()
WalkXZY({{const4({fp(px)}) B_EXPR_END}}, {SHIP_Y}, {{const4({fp(pz)}) B_EXPR_END}})
"""


def _origin_leg2_body(entry) -> str:
    _tag, _dock, _moor, _fp_, (fx, fz), _eye = entry
    return f"""
InitWalk()
WalkXZY({{const4({fp(fx)}) B_EXPR_END}}, {SHIP_Y}, {{const4({fp(fz)}) B_EXPR_END}})
"""


DIRECTOR_LOOP = f"""
L0:
SET({{Map.Byte[{PORT_CACHE}] B_EXPR_END}})
JMP_IFNOT(L100)
DisableMove()
DisableMenu()
RunScriptSync(6, {ANCHOR_UID}, {HIDE_TAG})
op_22(2)
{_switch([_origin_stage_body(e) for e in DEPART], "O", ORIGIN_CACHE)}
op_1C({EYE_UID})
op_1C({AIM_UID})
InitObject({EYE_UID}, 0)
InitObject({AIM_UID}, 0)
op_22(4)
{_switch([_origin_eye_body(e) for e in DEPART], "F", ORIGIN_CACHE)}
op_22(6)
{FADE_IN}
op_22(30)
SetWalkSpeed({SAIL_SPEED})
SetWalkTurnSpeed(6)
{_switch([_origin_leg1_body(e) for e in DEPART], "G", ORIGIN_CACHE)}
FadeFilter(2, 24, 0, 255, 255, 255)
{_switch([_origin_leg2_body(e) for e in DEPART], "H", ORIGIN_CACHE)}
op_22(8)
op_1C({EYE_UID})
op_1C({AIM_UID})
{_switch([_relocate_body(e) for e in ARRIVE], "R")}
InitObject({EYE_UID}, 0)
InitObject({AIM_UID}, 0)
op_22(4)
{_switch([_eye_body(e) for e in ARRIVE], "E")}
op_22(6)
FadeFilter(3, 16, 0, 0, 0, 0)
SetWalkSpeed({ARRIVE_SPEED})
SetWalkTurnSpeed(6)
{_switch([_sail_in_body(e) for e in ARRIVE], "S")}
op_22(24)
{FADE_OUT}
{_switch([_moor_body(e) for e in ARRIVE], "M")}
SET({{Map.Byte[{PHASE}] const(2) B_LET B_EXPR_END}})
op_1C({EYE_UID})
op_1C({AIM_UID})
RunScriptSync(6, {ANCHOR_UID}, {SHOW_TAG})
SET({{Map.Byte[37] const(0) B_LET B_EXPR_END}})
op_22(24)
SET({{Map.Byte[{PHASE}] const(0) B_LET B_EXPR_END}})
SET({{Map.Byte[{PORT_CACHE}] const(0) B_LET B_EXPR_END}})
SET({{Map.Byte[{ORIGIN_CACHE}] const(0) B_LET B_EXPR_END}})
RunWorldCode(2, 1)
{FADE_IN}
EnableMenu()
EnableMove()
JMP(L900)
L100:
SET({{Global.Byte[190] B_NOT obj(uid=250).f[0] obj(uid={SHIP_UID}).f[0] B_MINUS const4({RADIUS_FP}) B_LT obj(uid={SHIP_UID}).f[0] obj(uid=250).f[0] B_MINUS const4({RADIUS_FP}) B_LT B_ANDAND obj(uid=250).f[2] obj(uid={SHIP_UID}).f[2] B_MINUS const4({RADIUS_FP}) B_LT obj(uid={SHIP_UID}).f[2] obj(uid=250).f[2] B_MINUS const4({RADIUS_FP}) B_LT B_ANDAND B_ANDAND B_ANDAND B_EXPR_END}})
JMP_IFNOT(L900)
SET({{const4({CONFIRM_ON}) B_KEYON B_EXPR_END}})
JMP_IFNOT(L900)
SET({{Map.Byte[24] const(100) B_EQ B_EXPR_END}})
JMP_IFNOT(L900)
DisableMove()
DisableMenu()
{FADE_OUT}
SET({{Map.Byte[{PHASE}] const(1) B_LET B_EXPR_END}})
InitObject({EYE_UID}, 0)
InitObject({AIM_UID}, 0)
op_22(4)
{FADE_IN}
op_22(30)
SetWalkSpeed({SAIL_SPEED})
SetWalkTurnSpeed(6)
InitWalk()
WalkXZY({{const4({fp(SHIP[0])}) B_EXPR_END}}, {SHIP[2]}, {{const4({fp(SAIL_TO_Z)}) B_EXPR_END}})
InitWalk()
WalkXZY({{const4({fp(SHIP[0])}) B_EXPR_END}}, {SHIP[2]}, {{const4({fp(SHIP[1])}) B_EXPR_END}})
op_22(10)
{FADE_OUT}
SET({{Map.Byte[{PHASE}] const(2) B_LET B_EXPR_END}})
MoveInstantXZY({{const4({fp(SHIP[0])}) B_EXPR_END}}, {{const({SHIP[2]}) B_EXPR_END}}, {{const4({fp(SHIP[1])}) B_EXPR_END}})
TurnInstant({{const({SHIP_FACE}) B_EXPR_END}})
op_1C({EYE_UID})
op_1C({AIM_UID})
op_22(24)
SET({{Map.Byte[{PHASE}] const(0) B_LET B_EXPR_END}})
{FADE_IN}
EnableMenu()
EnableMove()
L900:
SetAnimationFlags(1, 1)
SetAnimationInOut(0, 0)
RunAnimation({ANIM_ID})
op_22(1)
JMP(L0)
"""


def _origin_box_test(qx: float) -> str:
    """(X - qx < BOX) AND (qx - X < BOX) -- the two-sided subtract idiom, signed throughout
    (EBin Int24 reads sign-extend; B_MINUS/B_LT are signed Int32). X is x256 fixed-point."""
    q, box = fp(qx), int(ORIGIN_BOX * 256)
    return (f"{{Global.Int24[{ORIGIN_X}] const4({q}) B_MINUS const4({box}) B_LT "
            f"const4({q}) Global.Int24[{ORIGIN_X}] B_MINUS const4({box}) B_LT "
            f"B_ANDAND B_EXPR_END}}")


def _classifier() -> str:
    lines = [f"SET({{Map.Byte[{ORIGIN_CACHE}] const(1) B_LET B_EXPR_END}})"]
    for code, qx in sorted(QUAY_X.items()):
        lines.append(f"SET({_origin_box_test(qx)})")
        lines.append(f"JMP_IFNOT(LORG{code})")
        lines.append(f"SET({{Map.Byte[{ORIGIN_CACHE}] const({code}) B_LET B_EXPR_END}})")
        lines.append(f"LORG{code}:")
    return "\n".join(lines)


# THE MAIN-INIT PROLOGUE -- rung2a v11 verbatim + THE ORIGIN CLASSIFIER (3c). The [37] latch
# park and the [190] DISPATCH LAW record live in rung2a.
DEPART_PROLOGUE = f"""SET({{Global.Byte[{DEPART_BYTE}] B_EXPR_END}})
JMP_IFNOT(LDEPQ)
SET({{Map.Byte[{PORT_CACHE}] Global.Byte[{DEPART_BYTE}] B_LET B_EXPR_END}})
SET({{Global.Byte[{DEPART_BYTE}] const(0) B_LET B_EXPR_END}})
{_classifier()}
SET({{Map.Byte[{PHASE}] const(1) B_LET B_EXPR_END}})
InitObject({EYE_UID}, 0)
InitObject({AIM_UID}, 0)
SET({{Map.Byte[37] const(1) B_LET B_EXPR_END}})
RunScriptSync(6, {ANCHOR_UID}, {HIDE_TAG})
DisableMove()
DisableMenu()
RunWorldCode(2, 0)
FadeFilter(2, 1, 0, 255, 255, 255)
LDEPQ:"""


def asm(text: str) -> bytes:
    body = assemble_block(text)
    rt = disassemble_block(body, 0, len(body))
    if assemble_block(rt) != body:
        raise SystemExit("text<->bytes round-trip mismatch -- refusing")
    return body


def patch_one(base: bytes) -> bytes:
    s = EbScript(base)
    for uid in (SHIP_UID, EYE_UID, AIM_UID, ANCHOR_UID):
        e = s.entry(uid)
        if e.empty or not e.funcs:
            raise SystemExit(f"entry {uid} missing -- deploy rungs 0-2a first")
    out = base
    out = E.replace_function_body(out, SHIP_UID, 0, asm(SHIP_INIT))
    out = E.replace_function_body(out, EYE_UID, 0, asm(EYE_INIT))
    out = E.replace_function_body(out, EYE_UID, 1, asm(EYE_LOOP))
    out = E.replace_function_body(out, AIM_UID, 0, asm(AIM_INIT))
    out = E.replace_function_body(out, AIM_UID, 1, asm(AIM_LOOP))
    for tag, body_text in ((HIDE_TAG, ANCHOR_HIDE), (SHOW_TAG, ANCHOR_SHOW)):
        body = asm(body_text)
        s2 = EbScript(out)
        if any(f.tag == tag for f in s2.entry(ANCHOR_UID).funcs):
            out = E.replace_function_body(out, ANCHOR_UID, tag, body)
        else:
            out = E.add_function(out, ANCHOR_UID, tag, body)
    for tag, x, z, face, gy in PORTS:
        body = asm(port_tag_body(x, z, face, gy))
        s2 = EbScript(out)
        if any(f.tag == tag for f in s2.entry(ANCHOR_UID).funcs):
            out = E.replace_function_body(out, ANCHOR_UID, tag, body)
        else:
            out = E.add_function(out, ANCHOR_UID, tag, body)
    out = E.replace_function_body(out, SHIP_UID, 1, asm(DIRECTOR_LOOP))

    # Main_Init prologue: strip-and-replace (the v5b lesson).
    import re as _re
    s3 = EbScript(out)
    f0 = next(f for f in s3.entry(0).funcs if f.tag == 0)
    text = disassemble_block(s3.data, f0.abs_start, f0.abs_end)
    if assemble_block(text) != s3.data[f0.abs_start:f0.abs_end]:
        raise SystemExit("Main_Init does not round-trip text<->bytes -- refusing to rebuild it")
    lines = text.rstrip().splitlines()
    if f"Global.Byte[{DEPART_BYTE}]" in text:
        i = next(k for k, l in enumerate(lines) if f"Global.Byte[{DEPART_BYTE}]" in l)
        m = _re.match(r"JMP_IFNOT\((\w+)\)", lines[i + 1].strip())
        if not m:
            raise SystemExit("existing prologue shape unrecognized -- refusing to strip")
        lbl = m.group(1) + ":"
        j = next(k for k in range(i + 2, len(lines)) if lines[k].strip() == lbl)
        del lines[i:j + 1]
    if lines[-1].strip() != "RET()":
        raise SystemExit(f"Main_Init does not end in RET() (got {lines[-1]!r}) -- refusing")
    lines[-1:-1] = DEPART_PROLOGUE.splitlines()
    out = E.replace_function_body(out, 0, 0, assemble_block("\n".join(lines) + "\n"))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deploy", action="store_true")
    args = ap.parse_args()

    game_path = config.find_game_path(None)
    eb_root = game_path / MOD_FOLDER / _WORLD_EB_SUBDIR
    bkdir = ROOT / "backups" / "scene-ladder"
    ts = time.strftime("%Y%m%d-%H%M%S")

    patched = {}
    for lang in LANGS:
        mod_p = eb_root / lang / FNAME
        if not mod_p.is_file():
            raise SystemExit(f"{mod_p} missing -- rungs 0-2a not deployed for {lang}")
        base = mod_p.read_bytes()
        out = patch_one(base)
        patched[lang] = (mod_p, out)
        if lang == "us":
            s = EbScript(out)
            print(f"[us] origin-port departures in; anchor tags "
                  f"{sorted(f.tag for f in s.entry(ANCHOR_UID).funcs)}; "
                  f"{len(out) - len(base):+} bytes vs base")
    if not args.deploy:
        print("dry run OK (all 7 languages patched in memory) -- re-run with --deploy to write")
        return
    for lang in LANGS:
        mod_p, out = patched[lang]
        bkdir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(mod_p, bkdir / f"{FNAME}.{lang}.{ts}")
        mod_p.write_bytes(out)
        print(f"  {lang}: backed up + wrote {len(out)} B")


if __name__ == "__main__":
    main()
