"""Scene ladder rung 1b: THE SAIL -- the rig camera tracks a moving subject.

Builds directly on rung 1a's proven machinery (same entries, same trigger, same restore) and
the law set in README.md; every shape below is the STOCK shape (the recurring 1a lesson --
deviations cost playtests):

  * THE SUBJECT IS THE DIRECTOR: the sail choreography runs INLINE in the ship's own tag-1
    (stock's flight ship runs its own waypoint chain); WalkXZY blocks the ship's script, and
    control is locked meanwhile.
  * WALKS LIVE IN TAG-1, never tag-0: InitObject is synchronous, so a blocking walk in a rig's
    Init would stall the director mid-arm (stock entry 1 keeps its glide in the tag-1 phase
    machine). The eye's dolly is a one-shot walk at the top of its loop func.
  * THE AIM RIDES THE SHIP: per-frame MoveInstant re-pin onto obj(16).f[] (stock entry 2's L20
    shape); the y pass-through cancels (THE ARG2 Y-DOMAIN).
  * SELF-RELATIVE LEGS: the ship sails west 40u and back via obj(uid=255).f[] +/- deltas
    (epoch-safe by construction), then an EXACT re-moor via the canonical constants --
    SetActorPosition -> WMActor.SetPosition -> SetAbsolutePositionOf re-bases the transform
    into the live epoch (s68 reads the transform, the s67 probe is still live to verify).

The scene (~8s): Confirm at the ship -> composed shot (1a) -> a beat -> the ship gets underway,
sails ~40u west at speed 60 while the camera's aim rides it and the eye drifts gently in ->
the ship comes about and returns -> re-moors, re-faces east -> a settle beat -> rigs disposed,
control back. Repeatable.

Deploy: py rung1b_sail.py --deploy      (7 languages, hot -- no DLL change, no relaunch)
Revert: re-run rung1a_rig_proof.py --deploy (restores the static-shot bodies).
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

SHIP_UID, EYE_UID, AIM_UID = 16, 17, 18
ANIM_ID = 5106
SHIP = (29, -1168, 200)              # the mooring: x, z world units; y fp const (rung 0)
SHIP_FACE = 192                      # east, toward the quay

# ★ v2 after the first sail SOFTLOCKED (ship turned, never moved, control never returned;
# probe trace = the ship oscillating +/- one step around the mooring forever). TWO laws:
#   * THE CARROT LAW: a blocking WalkXZY RE-READS its argument expressions EVERY frame -- a
#     self-relative target (obj(255).f[0] - N) recedes with each step and the walk can never
#     terminate. THAT is why stock caches ship-relative targets into Instance vars before
#     walking. Walk targets must be CONSTANTS (canonical constants are frame-correct: the
#     probe shows pos[] stays canonical -- RealPosition is the engine's absolute tracker).
#   * THE RIG-RADIUS LAW: EventCollision.Collision in mode 0 (MoveToward's call) BYPASSES the
#     tag-2/3 candidacy gate -- EVERY cid-4 actor is a candidate by radius alone. The AIM,
#     re-pinned exactly onto the hull, collided at distance ~0 every frame; MoveToward
#     reverted the transform and the per-frame writeback mirrored the revert into pos[]:
#     step -> revert -> re-mirror, net zero (the eye's dolly 17u away completed fine -- the
#     probe proved walks work). Camera rigs are hardware, not bodies: SetObjectLogicalSize
#     (0,0,0) on the rigs AND the scenery ship (its trigger is expression math, not collRad).
SAIL_TO_Z = -1208                    # the leg: due SOUTH 40u (away from the x=0 wrap seam)
SAIL_SPEED = 60                      # ~0.23 u/frame -> ~170 frames per leg
OPEN_BEAT = 30                       # composed-shot hold before getting underway
SETTLE_BEAT = 30                     # after re-mooring, before the rigs dispose

CONFIRM_ON = 131072
RADIUS_FP = 3072


def fp(v: int) -> int:
    return (v * 256) & 0xFFFFFFFF


def ship_rel(axis: int, up_units: float = 0.0, lateral: float = 0.0) -> str:
    """obj(16).f[axis] +/- delta. Axis 1 uses THE ARG2 Y-DOMAIN (minus = up); 0/2 are plain."""
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

EYE_LOOP = f"""
L0:
InitWalk()
WalkXZY({ship_rel(0, lateral=-10)}, {ship_rel(1, up_units=6)}, {ship_rel(2, lateral=-10)})
L100:
op_22(1)
JMP(L100)
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
InitObject({EYE_UID}, 0)
InitObject({AIM_UID}, 0)
op_22({OPEN_BEAT})
SetWalkSpeed({SAIL_SPEED})
SetWalkTurnSpeed(6)
InitWalk()
WalkXZY({{const4({fp(SHIP[0])}) B_EXPR_END}}, {SHIP[2]}, {{const4({fp(SAIL_TO_Z)}) B_EXPR_END}})
InitWalk()
WalkXZY({{const4({fp(SHIP[0])}) B_EXPR_END}}, {SHIP[2]}, {{const4({fp(SHIP[1])}) B_EXPR_END}})
MoveInstantXZY({{const4({fp(SHIP[0])}) B_EXPR_END}}, {{const({SHIP[2]}) B_EXPR_END}}, {{const4({fp(SHIP[1])}) B_EXPR_END}})
TurnInstant({{const({SHIP_FACE}) B_EXPR_END}})
op_22({SETTLE_BEAT})
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
            raise SystemExit(f"entry {uid} missing -- deploy rung 0 + 1a first")
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
            raise SystemExit(f"{mod_p} missing -- rung 0/1a not deployed for {lang}")
        base = mod_p.read_bytes()
        out = patch_one(base)
        patched[lang] = (mod_p, out)
        if lang == "us":
            print(f"[us] sail bodies in; {len(out) - len(base):+} bytes vs base")
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
