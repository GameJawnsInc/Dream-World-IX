"""Scene ladder rung 1a: THE RIG PROOF -- the 9001 camera mechanism on our content, in-place in 9011.

The mechanism, byte-read from stock WORLD01 entries 1/2 + source (DoEventCode.cs:2463/2473,
ProcessEvents.cs:186-202):
  * op 0xB7 (EYE) / 0xB8 (AIM): the EXECUTING actor snaps to the CURRENT camera eye/aim ray
    (so arming never jumps the camera) and gets `actf |= actEye/actAim`. Every ProcessEvents
    pass re-scans flagged actors and pushes their positions into w_cameraSetEyePtr/AimPtr --
    the camera follows wherever the rig actors go. Model-less actors: the s49 smoother skips
    them (`actor.Animation == null`), stock-proven.
  * THE RESTORE (the piece stock never needed -- 9001 exits via Field()): nothing clears the
    flags; the designation lives exactly as long as a flagged actor is ACTIVE. op 0x1C
    (TerminateEntry / EBin `DELETE`, EBin.cs:1504) on a NON-self uid calls DisposeObj -> the
    actor leaves the active list -> next pass finds no actAim -> w_cameraSetEyeAim falls back
    to the chase cam on w_moveActorPtr. In the kit dialect: `op_1C(uid)`.
  * Stock's rig entries cache ship-relative offsets in Instance vars; an appended entry has
    varn=0 (NO Instance space -- the lane doc's append caveat), so ours inline constants: the
    rung-0 ship is static at (29,-1168) y=200fp.

The scene (repeatable, ~4s): stand on the shore within 12u of the anchored ship, press
Confirm (edge-gated, and only while the nameplate case machine is IDLE, Map.Byte[24]==100 --
the boat's proven arbitration gate, so a quay-plate confirm can never double-fire) ->
control+menu lock -> the rig arms: AIM pins on the ship, EYE starts low over the water SW of
it and dollies slowly toward it (speed 8, ~3s) -> hold -> rig TERMINATED (chase cam returns,
a hard cut -- the fade is rung 1c's job) -> control back.

WORLD11 changes (dispatcher 9011; rung 0 must already be deployed):
  entry 17 (new) -- THE EYE: tag 0 = 0xB7 + MoveInstant (12,-1182) y 6u + slow WalkXZY dolly
                    to (16,-1178); tag 1 = idle tick loop (stock rig entries carry a loop).
  entry 18 (new) -- THE AIM: tag 0 = 0xB8 + MoveInstant onto the ship; tag 1 = idle tick.
  entry 16 tag 1 -- the ship's loop becomes THE DIRECTOR: proximity+Confirm+idle-case gate ->
                    InitObject(17/18) -> op_22(240) -> op_1C(17/18) -> restore; the anim loop
                    (THE ANIMATION RULE) unchanged below the gate.
  Main_Init unchanged -- the rig is armed by the director only, never at world load.

While the rig is armed, actEye/actAim actors exist -> the s64 self-heal rig scan hard-gates
the heal (the exact protection built for custom scenes; without s64 the heal would seize the
rig -- the 9001 bug class).

Deploy: py rung1a_rig_proof.py --deploy     (7 languages, hot -- world re-entry reloads)
Revert: restore the printed backups (rung-0 state), or re-run rung0_quay_ship.py --deploy
        (rewrites the ship loop to the plain anim loop; entries 17/18 stay but unarmed).
Bench:  walk to the water's edge in front of the ship, Confirm -> the camera should cut low
        over the water, glide toward the ship for ~3s, then cut back; control returns.
"""
import argparse
import pathlib
import shutil
import struct
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

SHIP_UID = 16                        # rung 0's ship (must be deployed)
EYE_UID = 17
AIM_UID = 18
ANIM_ID = 5106

SHIP = (29, -1168, 200)              # rung 0's mooring: x, z world units; y fixed-point const
EYE_FROM = (12, -1182, 1536)         # scene open: low over the water SW of the ship (y 6u)
EYE_TO = (16, -1178)                 # the ~3s dolly target (speed 8 ~= 0.03u/frame)
HOLD_FRAMES = 240                    # scene length (the dolly runs inside it)

CONFIRM_ON = 131072                  # 0x20000 Confirm with B_KEYON (edge) -- the ring's proven gate
RADIUS_FP = 3072                     # fp(12) -- the on-land confirm strip is the shore in front of the ship


def fp(v: int) -> int:
    return (v * 256) & 0xFFFFFFFF


EYE_INIT = f"""
0xB7()
MoveInstantXZY({{const4({fp(EYE_FROM[0])}) B_EXPR_END}}, {{const({EYE_FROM[2]}) B_EXPR_END}}, {{const4({fp(EYE_FROM[1])}) B_EXPR_END}})
SetWalkSpeed(8)
SetWalkTurnSpeed(1)
InitWalk()
WalkXZY({{const4({fp(EYE_TO[0])}) B_EXPR_END}}, {EYE_FROM[2]}, {{const4({fp(EYE_TO[1])}) B_EXPR_END}})
RET()
"""

AIM_INIT = f"""
0xB8()
MoveInstantXZY({{const4({fp(SHIP[0])}) B_EXPR_END}}, {{const({SHIP[2]}) B_EXPR_END}}, {{const4({fp(SHIP[1])}) B_EXPR_END}})
SetWalkTurnSpeed(1)
RET()
"""

IDLE_LOOP = """
L0:
op_22(1)
JMP(L0)
"""

# The director: the boat's proven proximity shape (uid 16, radius fp 3072, on-foot [190]==0),
# Confirm edge, the case-machine idle gate (Byte[24]==100), then the scene body.
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
InitObject({EYE_UID}, 0)
InitObject({AIM_UID}, 0)
op_22({HOLD_FRAMES})
op_1C({EYE_UID})
op_1C({AIM_UID})
op_22(2)
EnableMenu()
EnableMove()
L900:
SetAnimationFlags(1, 1)
SetAnimationInOut(0, 0)
RunAnimation({ANIM_ID})
op_22(1)
JMP(L0)
"""


def build_entry(etype: int, funcs) -> bytes:
    fc = len(funcs)
    table, code, fpos = b"", b"", fc * 4
    for tag, body in funcs:
        table += struct.pack("<HH", tag, fpos)
        code += body
        fpos += len(body)
    out = bytes([etype, fc]) + table + code
    if len(out) % 4:
        out += bytes(4 - len(out) % 4)
    return out


def asm(text: str) -> bytes:
    body = assemble_block(text)
    rt = disassemble_block(body, 0, len(body))
    if assemble_block(rt) != body:
        raise SystemExit("text<->bytes round-trip mismatch -- refusing")
    return body


def patch_one(base: bytes) -> bytes:
    s = EbScript(base)
    ship = s.entry(SHIP_UID)
    if ship.empty or not ship.funcs:
        raise SystemExit(f"entry {SHIP_UID} (the rung-0 ship) is not deployed -- run rung0 first")
    etype = s.data[ship.abs_start]

    eye_init, aim_init, idle = asm(EYE_INIT), asm(AIM_INIT), asm(IDLE_LOOP)
    director = asm(DIRECTOR_LOOP)

    out = base
    for uid, init in ((EYE_UID, eye_init), (AIM_UID, aim_init)):
        have = None
        try:
            have = s.entry(uid)
        except Exception:
            pass
        if have is None or have.empty or not have.funcs:
            out = E.append_entry(out, uid, build_entry(etype, [(0, init), (1, idle)]))
        else:
            out = E.replace_function_body(out, uid, 0, init)
            out = E.replace_function_body(out, uid, 1, idle)
        s = EbScript(out)

    out = E.replace_function_body(out, SHIP_UID, 1, director)
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
            raise SystemExit(f"{mod_p} missing -- rung 0 not deployed for {lang}")
        base = mod_p.read_bytes()
        out = patch_one(base)
        patched[lang] = (mod_p, out)
        if lang == "us":
            s = EbScript(out)
            print(f"[us] eye {EYE_UID}: {[f.tag for f in s.entry(EYE_UID).funcs]}, "
                  f"aim {AIM_UID}: {[f.tag for f in s.entry(AIM_UID).funcs]}, "
                  f"ship loop -> director; {len(out) - len(base):+} bytes vs base")
    if not args.deploy:
        print("dry run OK (all 7 languages patched in memory) -- re-run with --deploy to write")
        return
    for lang in LANGS:
        mod_p, out = patched[lang]
        bkdir.mkdir(parents=True, exist_ok=True)
        bk = bkdir / f"{FNAME}.{lang}.{ts}"
        shutil.copy2(mod_p, bk)
        mod_p.write_bytes(out)
        print(f"  {lang}: backed up -> {bk.name}; wrote {len(out)} B")


if __name__ == "__main__":
    main()
