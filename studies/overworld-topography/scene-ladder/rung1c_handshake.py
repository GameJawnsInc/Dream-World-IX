"""Scene ladder rung 1c: THE HANDSHAKE -- phases + fades = a complete self-contained mini-scene.

Adds the last two stock scene idioms to the proven 1b sail:

  * THE FADE BRACKET (byte-verbatim stock forms, censused across all 13 dispatchers:
    out = FadeFilter(2,24,0,255,255,255) x65, in = FadeFilter(0,24,0,255,255,255) x11,
    each followed by a plain op_22(25) wait): the scene opens and closes through white,
    masking BOTH camera cuts -- and the post-scene chase ease (the "camera crawls home"
    cosmetic from 1a) now settles entirely BEHIND the white before the fade-in.
  * THE PHASE HANDSHAKE (the Byte[26] idiom of stock 9001, on WORLD11's free Map.Byte[50] --
    used census: 24-30/33/35/37-39/41/42): the DIRECTOR writes 0 -> 1 (scene open) -> 2
    (closing) -> 0 (idle, repeatable); the EYE consumes phase 1 as its dolly authorization --
    a real cross-actor coordination, the shape rung-2 scenes will build on.

Scene (~12s): Confirm -> white -> [rigs arm + eye dollies, unseen] -> fade in on the composed
shot -> beat -> the ship sails 40u south and back, camera tracking -> white -> [exact re-moor,
rig disposal, chase settles, all unseen] -> fade in on normal play -> control back.

Deploy: py rung1c_handshake.py --deploy    (7 languages, hot -- no DLL change, no relaunch)
Revert: re-run rung1b_sail.py --deploy (the fade-less sail) or rung1a_rig_proof.py --deploy.
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

SHIP_UID, EYE_UID, AIM_UID = 16, 17, 18
ANIM_ID = 5106
SHIP = (29, -1168, 200)
SHIP_FACE = 192
SAIL_TO_Z = -1208
SAIL_SPEED = 60
PHASE = 50                           # Map.Byte[50] -- the scene phase (0 idle / 1 open / 2 closing)

CONFIRM_ON = 131072
RADIUS_FP = 3072

FADE_OUT = "FadeFilter(2, 24, 0, 255, 255, 255)\nop_22(25)"
FADE_IN = "FadeFilter(0, 24, 0, 255, 255, 255)\nop_22(25)"


def fp(v: int) -> int:
    return (v * 256) & 0xFFFFFFFF


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

# THE HANDSHAKE CONSUMER: the dolly waits for phase 1 (the director's "scene open" write).
EYE_LOOP = f"""
L0:
SET({{Map.Byte[{PHASE}] const(1) B_EQ B_EXPR_END}})
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

DIRECTOR_LOOP = f"""
L0:
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


def asm(text: str) -> bytes:
    body = assemble_block(text)
    rt = disassemble_block(body, 0, len(body))
    if assemble_block(rt) != body:
        raise SystemExit("text<->bytes round-trip mismatch -- refusing")
    return body


def patch_one(base: bytes) -> bytes:
    s = EbScript(base)
    for uid in (SHIP_UID, EYE_UID, AIM_UID):
        e = s.entry(uid)
        if e.empty or not e.funcs:
            raise SystemExit(f"entry {uid} missing -- deploy rungs 0-1b first")
    out = base
    out = E.replace_function_body(out, SHIP_UID, 0, asm(SHIP_INIT))
    out = E.replace_function_body(out, EYE_UID, 0, asm(EYE_INIT))
    out = E.replace_function_body(out, EYE_UID, 1, asm(EYE_LOOP))
    out = E.replace_function_body(out, AIM_UID, 0, asm(AIM_INIT))
    out = E.replace_function_body(out, AIM_UID, 1, asm(AIM_LOOP))
    out = E.replace_function_body(out, SHIP_UID, 1, asm(DIRECTOR_LOOP))
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
            raise SystemExit(f"{mod_p} missing -- rungs 0-1b not deployed for {lang}")
        base = mod_p.read_bytes()
        out = patch_one(base)
        patched[lang] = (mod_p, out)
        if lang == "us":
            print(f"[us] handshake+fade bodies in; {len(out) - len(base):+} bytes vs base")
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
