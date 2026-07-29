"""Scene ladder rung 2a: THE DEPARTURE -- the pending-departure auto-scene (world side only).

The rung-2 diegesis (owner-ruled: DEPARTURE) split per house method; 2a is the world half,
bench-testable before any hall change:

  * THE SIGNAL: `Global.Byte[1872]` (= flags.py `FERRY_DEPART_BYTE`, the first byte of the
    sanctioned kit_world_flags band 14976-15007) carries the pending port code -- 0 none,
    1 Ashvale / 2 Tidefall / 3 Grimhorn / 4 Larkspur. GLOB = it survives the hall->world
    transition (Map vars reset on world load). The director CACHES it to Map.Byte[51] and
    CLEARS it FIRST inside the branch -- a mid-scene failure can never replay-loop a save.
  * THE AUTO-SCENE: the ship's director gains a branch BEFORE the confirm vignette: pending
    port + on foot -> fade to black -> HideObject(14, 65535) (mesh-hide the player: aboard,
    unseen; flags/collision untouched) -> rigs arm -> reveal the composed shot -> the ship
    casts off and sails 40u south (NO return leg -- a departure) -> fade to black -> rigs
    disposed + the ship re-moors + THE PORT SNAP: RunScriptSync(6, 14, 60+port) runs the
    anchor's per-port arrive tag (the boat's proven shore-snap shape) -> ShowObject ->
    chase settles at the new shore behind black -> reveal -> control back at the chosen
    port, facing inland.
  * Anchor entry 14 gains tags 61-64 (one per port, arrive coords + face from the hall's
    [[ferry.destination]] rows; y passes 200 -- the index-1 human class ground-snaps).

Bench (no hall changes needed): ~ Flags -> set bit 14976 (port 1 Ashvale; 14977 = port 2,
14976+14977 = 3, 14978 = 4) -> close the menu -> the departure plays and drops you at that
port's shore. 2b wires the hall's ferry arms to write the byte + land the world at Ashvale
waters instead of the destination.

Deploy: py rung2a_departure.py --deploy    (7 languages, hot)
Revert: re-run rung1c_handshake.py --deploy (the confirm vignette only; tags 61-64 stay,
        unarmed -- harmless).
"""
import argparse
import pathlib
import shutil
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "ff9mapkit"))

from ff9mapkit import config                                          # noqa: E402
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
PHASE = 50                           # Map.Byte[50] -- scene phase (1c)
PORT_CACHE = 51                      # Map.Byte[51] -- the cached port code for the switch
DEPART_BYTE = 1872                   # Global.Byte -- flags.py FERRY_DEPART_BYTE

# The four ports (arrive x/z/face from lantern-hall.field.toml [[ferry.destination]] rows;
# ground_y probed offline from the deployed blocks -- round 1 landed the player at pos[1] =
# -200 (-0.78u) under a 3u shore, "inside the ground": the arrival MoveInstant must place the
# player AT the ground height, arg2 = (-y*256) & 0xFFFF per THE ARG2 SIGN LAW -- the index-1
# ground snap does NOT rescue a wrong scripted y): tag, x, z, face, ground_y.
PORTS = [
    (61, 60.0, -1168.0, 192, 3.0),   # 1 Ashvale (the Lantern Quay)
    (62, 432.0, -1232.0, 192, 3.2),  # 2 Tidefall
    (63, 1214.0, -1192.0, 192, 3.2), # 3 Grimhorn (desert ground)
    (64, 688.0, -616.0, 64, 3.23),   # 4 Larkspur (west = inland)
]

CONFIRM_ON = 131072
RADIUS_FP = 3072

FADE_OUT = "FadeFilter(2, 24, 0, 255, 255, 255)\nop_22(25)"
FADE_IN = "FadeFilter(3, 16, 0, 0, 0, 0)\nop_22(17)"


def fp(v) -> int:
    return int(v * 256) & 0xFFFFFFFF


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


# --- unchanged 1c bodies (ship init, rigs) ---

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

# The eye frames by MODE: a DEPARTURE (Map.Byte[51] carries the port) looks SEAWARD from the
# shore side -- the spawn point is BEHIND the camera, so the deferred-model flash cannot be in
# frame; the confirm vignette keeps the proven west-side composition.
EYE_INIT = f"""
0xB7()
SetObjectLogicalSize(0, 0, 0)
SET({{Map.Byte[{PORT_CACHE}] B_EXPR_END}})
JMP_IFNOT(L50)
MoveInstantXZY({ship_rel(0, lateral=14)}, {ship_rel(1, up_units=6)}, {ship_rel(2, lateral=4)})
JMP(L90)
L50:
MoveInstantXZY({ship_rel(0, lateral=-17)}, {ship_rel(1, up_units=7)}, {ship_rel(2, lateral=-14)})
L90:
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

# --- the port-snap tags on the anchor (the boat tag-60 shape) ---

def port_tag_body(x: float, z: float, face: int, ground_y: float) -> str:
    y_arg = (-int(ground_y * 256)) & 0xFFFF
    return f"""
MoveInstantXZY({{const4({fp(x)}) B_EXPR_END}}, {{const({y_arg}) B_EXPR_END}}, {{const4({fp(z)}) B_EXPR_END}})
TurnInstant({{const({face}) B_EXPR_END}})
RET()
"""


# --- the director: departure branch + the 1c confirm vignette ---

def _port_switch() -> str:
    lines = []
    for i, (tag, _x, _z, _f, _gy) in enumerate(PORTS[:-1], start=1):
        lines.append(f"SET({{Map.Byte[{PORT_CACHE}] const({i}) B_EQ B_EXPR_END}})")
        lines.append(f"JMP_IFNOT(LP{i})")
        lines.append(f"RunScriptSync(6, {ANCHOR_UID}, {tag})")
        lines.append("JMP(LPD)")
        lines.append(f"LP{i}:")
    lines.append(f"RunScriptSync(6, {ANCHOR_UID}, {PORTS[-1][0]})")
    lines.append("LPD:")
    return "\n".join(lines)


DIRECTOR_LOOP = f"""
L0:
SET({{Map.Byte[{PORT_CACHE}] Global.Byte[190] B_NOT B_ANDAND B_EXPR_END}})
JMP_IFNOT(L100)
HideObject({ANCHOR_UID}, 255)
{FADE_IN}
op_22(30)
SetWalkSpeed({SAIL_SPEED})
SetWalkTurnSpeed(6)
InitWalk()
WalkXZY({{const4({fp(SHIP[0])}) B_EXPR_END}}, {SHIP[2]}, {{const4({fp(SAIL_TO_Z + 12)}) B_EXPR_END}})
FadeFilter(2, 24, 0, 255, 255, 255)
InitWalk()
WalkXZY({{const4({fp(SHIP[0])}) B_EXPR_END}}, {SHIP[2]}, {{const4({fp(SAIL_TO_Z)}) B_EXPR_END}})
op_22(4)
SET({{Map.Byte[{PHASE}] const(2) B_LET B_EXPR_END}})
op_1C({EYE_UID})
op_1C({AIM_UID})
MoveInstantXZY({{const4({fp(SHIP[0])}) B_EXPR_END}}, {{const({SHIP[2]}) B_EXPR_END}}, {{const4({fp(SHIP[1])}) B_EXPR_END}})
TurnInstant({{const({SHIP_FACE}) B_EXPR_END}})
{_port_switch()}
ShowObject({ANCHOR_UID}, 255)
op_22(24)
SET({{Map.Byte[{PHASE}] const(0) B_LET B_EXPR_END}})
SET({{Map.Byte[{PORT_CACHE}] const(0) B_LET B_EXPR_END}})
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


# THE MAIN-INIT PROLOGUE (v4 -- owner: "like stock, the character doesn't show"): stock
# departures are DEDICATED cutscene worlds (9001-class) where no controlled player ever
# spawns; an in-place 9011 scene cannot avoid the spawn, but Main_Init runs at WORLD
# CONSTRUCTION, before the first rendered frame -- an instant black + mesh-hide there means
# the free-roam entry is never seen, and the director's own fade-out composes black-on-black.
DEPART_PROLOGUE = f"""SET({{Global.Byte[{DEPART_BYTE}] B_EXPR_END}})
JMP_IFNOT(LDEPQ)
SET({{Map.Byte[{PORT_CACHE}] Global.Byte[{DEPART_BYTE}] B_LET B_EXPR_END}})
SET({{Global.Byte[{DEPART_BYTE}] const(0) B_LET B_EXPR_END}})
SET({{Map.Byte[{PHASE}] const(1) B_LET B_EXPR_END}})
InitObject({EYE_UID}, 0)
InitObject({AIM_UID}, 0)
HideObject({ANCHOR_UID}, 255)
DisableMove()
DisableMenu()
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
            raise SystemExit(f"entry {uid} missing -- deploy rungs 0-1c first")
    out = base
    out = E.replace_function_body(out, SHIP_UID, 0, asm(SHIP_INIT))
    out = E.replace_function_body(out, EYE_UID, 0, asm(EYE_INIT))
    out = E.replace_function_body(out, EYE_UID, 1, asm(EYE_LOOP))
    out = E.replace_function_body(out, AIM_UID, 0, asm(AIM_INIT))
    out = E.replace_function_body(out, AIM_UID, 1, asm(AIM_LOOP))
    for tag, x, z, face, gy in PORTS:
        body = asm(port_tag_body(x, z, face, gy))
        s2 = EbScript(out)
        if any(f.tag == tag for f in s2.entry(ANCHOR_UID).funcs):
            out = E.replace_function_body(out, ANCHOR_UID, tag, body)
        else:
            out = E.add_function(out, ANCHOR_UID, tag, body)
    out = E.replace_function_body(out, SHIP_UID, 1, asm(DIRECTOR_LOOP))

    # Main_Init gains the departure prologue before its final RET. Re-runs REPLACE any prior
    # prologue version (v4's skip-if-present guard left a stale v4 prologue deployed under a
    # v5 director -- an inconsistent pair that would softlock a departure; strip then insert).
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
            raise SystemExit(f"{mod_p} missing -- rungs 0-1c not deployed for {lang}")
        base = mod_p.read_bytes()
        out = patch_one(base)
        patched[lang] = (mod_p, out)
        if lang == "us":
            s = EbScript(out)
            print(f"[us] departure in; anchor tags {sorted(f.tag for f in s.entry(ANCHOR_UID).funcs)}; "
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
