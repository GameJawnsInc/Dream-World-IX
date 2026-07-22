"""Rung 1: author a boardable Blue Narciss into WORLD11 (dispatcher 9011) -- the bench boat.

The verbatim grounding (studies/custom-vehicle/recon_world03.txt):
- WORLD03 entry 6 = the real boat actor. Its Init is carried near-verbatim: SetObjectIndex(8)
  (the Blue Narciss actor-index binding), SetModel(321), the anims (stand 5145 / sail 5143),
  THE MODE-7 LOAD ARM (if [190]==7 at dispatcher load: attach the player anchor + take control
  -- this closes THE LOAD LAW for mode 7 on WORLD11), and PARKED-POSITION PERSISTENCE at
  Global[74/77/79/82] (X/Y/Z/facing -- the same save record the real boat uses; concern-C's
  answer, read straight from the bytecode).
- WORLD03 entry 2's Map.Byte[37] machine = the real board protocol: Disable -> AttachObject
  (anchor, vehicle, bone) -> [190]=mode -> RunWorldCode(1,mode) -> DefinePlayerCharacter
  (control binds to gExec's object) -> Enable. Our board/dismount loop (the boat's tag 1)
  compresses that protocol into a Confirm-gated proximity trigger; the .eb owns policy.
- WORLD11's player anchor = entry 14. Its per-frame foot arm only runs while [190]==0, so a
  boarded boat is never fought for control, and setting [190]=0 at dismount makes the anchor
  re-bind + re-anim itself (its own stock code) -- the dismount self-heals.

WORLD11 additions:
  entry 15 (new)  -- the boat: Init (verbatim-adapted) + the board/dismount loop (ours)
  entry 14 tag 60 -- the shore-snap: DetachObject(14) + MoveInstantXZY(dock) (runs ON the anchor)
  entry 0 tag 0   -- Main_Init gains InitObject(15, 0) (unconditional spawn -- the 9009 pattern)

Seeding: Global.Bit[8712] (the kit's safe flag band) marks "boat record seeded"; first load
parks the boat at BOAT_SPAWN. Dismount = Confirm while sailing: parks the boat where it
floats, snaps the player to DOCK (v1 simplification -- no shore-legality check yet).

Deploy: py build_boat_world11.py --deploy   (per-language into FF9CustomMap-world)
Revert: restore the printed backups (or delete the .eb.bytes if none existed).
Bench:  ~ menu -> reload state 9011 -> teleport near island E -> walk to the boat -> Confirm.
"""
import argparse
import pathlib
import shutil
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))

from ff9mapkit import config                                          # noqa: E402
from ff9mapkit.world.entrance import load_all_dispatchers, _WORLD_EB_SUBDIR   # noqa: E402
from ff9mapkit.eb.model import EbScript                               # noqa: E402
from ff9mapkit.eb import edit as E                                    # noqa: E402
from ff9mapkit.eb.cmdasm import assemble_block, disassemble_block     # noqa: E402

MOD_FOLDER = "FF9CustomMap-world"
NAME = "evt_world_world11"
FNAME = "EVT_WORLD_WORLD11.eb.bytes"
LANGS = ("us", "uk", "jp", "es", "fr", "gr", "it")

BOAT_UID = 15
ANCHOR_UID = 14
SNAP_TAG = 60
# Rung 2: the minted hull -- GEO_SUB_W0_DWX (mint_boat.py; crimson-shift of the Narciss, same
# rig, clips 5143/5145 still resolve to folder 321 via their ANH name tokens). The 3DModel
# directive registers at LAUNCH -- deploying a SetModel(6321) .eb needs one relaunch first.
MODEL_ID = 6321                      # the minted crimson hull (mint_boat.py). Requires the s50 engine
                                     # guards: ff9.w_movementMapConstructor's index-8 block hardcodes the
                                     # clone names "GEO_SUB_W0_008(Clone)"/"321(Clone)" and dereferenced
                                     # the miss unguarded -> a minted hull ("6321(Clone)") black-screened
                                     # the world (in-game 2026-07-22). The Animation double-add warning in
                                     # the log was a red herring (non-fatal; the proven Zidane override
                                     # fires it too).
# Bench geometry (world units; fixed-point = u*256), measured from the STOCK mesh by find_dock2.py:
# the block-(7,17) islet's land spans z -1128..-1104 (centroid (493,-1115)); its sand (topo 31)
# runs x 478..502, z -1126..-1116 -- a southwest-facing beach. Neighbouring pure-ocean blocks
# carry NO terrain mesh (the missing-block law), so a MISS south of the sand is open sea.
#
# POSITION IS HARD-CODED for the bench -- NO gEventGlobal reads/writes. The first build parked
# via the stock boat record Global[74..82] gated on a safe-band seed bit, which is only sound in
# a fresh session: a real SAVE holds live gameplay state in both (kit content allocates flags
# from 8712 up; bytes 74-82 hold field flags off the overworld) -> the boat parked at garbage
# after relaunch (in-game 2026-07-22). Parked-position persistence returns in a later rung with
# properly kit-allocated storage. Stock knowledge (user): the Narciss beaches itself nose-on-
# the-sand -- that is the boarding model, not an offshore float.
BOAT_SPAWN = (492, -1130)            # beached at the sand line (sand reaches z -1126 here)
BOAT_Y = 200                         # sea-level fixed-point Y (the stock boat's own seed value)
BOAT_FACE = 0
DOCK = (493, -1114)                  # the islet's land centroid -- measured, walkable
DOCK_Y = 768                         # ~3u; the engine ground-snaps on the next frame
DOCK_FACE = 128
NEAR = 100 * 256                     # board proximity (generous for the bench)

CONFIRM = 147456                     # 0x24000 = logical Confirm (0x20000) | physical Cross (0x4000).
                                     # The button-word bisection (2026-07-22) proved the held button
                                     # lands in the LOW 16 (physical PSX) bits on this input path with
                                     # the logical bit unset -- accept BOTH (EventInput.cs:549/554).


def fp(v: int) -> int:
    """World units -> 26-bit fixed-point as the unsigned const4 literal the .eb dialect wants."""
    return (v * 256) & 0xFFFFFFFF


BOAT_INIT = f"""
SetObjectIndex(8)
SetModel({MODEL_ID}, 100)
SetObjectFlags(5)
SetObjectLogicalSize(0, 80, 90)
op_DF(100)
SetObjectSize({BOAT_UID}, 106, 106, 106)
SetStandAnimation(5145)
SetWalkAnimation(5143)
op_35(5143)
SET({{Global.Byte[190] const(7) B_EQ B_EXPR_END}})
JMP_IFNOT(L100)
op_22(1)
AttachObject({ANCHOR_UID}, {BOAT_UID}, 0)
SetAnimationFlags(1, 1)
SetAnimationInOut(19, 19)
RunAnimation(5143)
DisableMenu()
DefinePlayerCharacter()
EnableMove()
JMP(L200)
L100:
SetAnimationFlags(1, 1)
SetAnimationInOut(0, 0)
RunAnimation(5143)
L200:
MoveInstantXZY({{const4({fp(BOAT_SPAWN[0])}) B_EXPR_END}}, {{const({BOAT_Y}) B_EXPR_END}}, {{const4({fp(BOAT_SPAWN[1])}) B_EXPR_END}})
TurnInstant({{const({BOAT_FACE}) B_EXPR_END}})
RET()
"""

# The proven board/dismount loop (probe counters stripped after the rung-1 proof).
# Board = on foot + Confirm|Cross HELD (B_KEY -- THE INPUT-BIT LAW) + within NEAR of the boat.
BOAT_LOOP = f"""
L0:
SET({{Global.Byte[190] B_NOT const4({CONFIRM}) B_KEY B_ANDAND B_EXPR_END}})
JMP_IFNOT(L500)
SET({{obj(uid=250).f[0] obj(uid={BOAT_UID}).f[0] B_MINUS const4({NEAR}) B_LT obj(uid={BOAT_UID}).f[0] obj(uid=250).f[0] B_MINUS const4({NEAR}) B_LT B_ANDAND obj(uid=250).f[2] obj(uid={BOAT_UID}).f[2] B_MINUS const4({NEAR}) B_LT obj(uid={BOAT_UID}).f[2] obj(uid=250).f[2] B_MINUS const4({NEAR}) B_LT B_ANDAND B_ANDAND B_EXPR_END}})
JMP_IFNOT(L500)
DisableMove()
DisableMenu()
AttachObject({ANCHOR_UID}, {BOAT_UID}, 0)
SetAnimationFlags(1, 1)
SetAnimationInOut(19, 19)
RunAnimation(5143)
SET({{Global.Byte[190] const(7) B_LET B_EXPR_END}})
RunWorldCode(1, 7)
DefinePlayerCharacter()
op_22(8)
EnableMove()
JMP(L900)
L500:
SET({{Global.Byte[190] const(7) B_EQ const4({CONFIRM}) B_KEYON B_ANDAND B_EXPR_END}})
JMP_IFNOT(L900)
DisableMove()
DetachObject({ANCHOR_UID})
RunScriptSync(6, {ANCHOR_UID}, {SNAP_TAG})
SET({{Global.Byte[190] const(0) B_LET B_EXPR_END}})
RunWorldCode(1, 0)
op_22(8)
EnableMove()
EnableMenu()
L900:
op_22(1)
JMP(L0)
"""

ANCHOR_SNAP = f"""
MoveInstantXZY({{const4({fp(DOCK[0])}) B_EXPR_END}}, {{const({DOCK_Y}) B_EXPR_END}}, {{const4({fp(DOCK[1])}) B_EXPR_END}})
TurnInstant({{const({DOCK_FACE}) B_EXPR_END}})
SetObjectFlags(5)
RET()
"""


def build_entry(etype: int, funcs) -> bytes:
    """[etype, fc] + (tag u16, fpos u16)* + code; fpos measured from entryStart+2 (the table base)."""
    import struct
    fc = len(funcs)
    table, code, fpos = b"", b"", fc * 4
    for tag, body in funcs:
        table += struct.pack("<HH", tag, fpos)
        code += body
        fpos += len(body)
    out = bytes([etype, fc]) + table + code
    if len(out) % 4:                                  # stock entries are 4-byte padded (NOTHING = 0x00)
        out += bytes(4 - len(out) % 4)
    return out


def asm(text: str) -> bytes:
    body = assemble_block(text)
    # round-trip sanity: the assembled bytes must disassemble cleanly end to end
    disassemble_block(body, 0, len(body))
    return body


def patch_one(base: bytes, etype: int) -> bytes:
    s = EbScript(base)
    if len(s.entries) < 15:
        raise SystemExit(f"unexpected dispatcher shape: {len(s.entries)} entries (wanted >=15) -- refusing")
    boat_init, boat_loop, snap = asm(BOAT_INIT), asm(BOAT_LOOP), asm(ANCHOR_SNAP)

    out = base
    # (1) the boat entry -- fresh add, or replace-in-place on a re-run
    have = None
    try:
        have = s.entry(BOAT_UID)
    except Exception:
        pass
    if have is None or not have.funcs:
        out = E.append_entry(out, BOAT_UID, build_entry(etype, [(0, boat_init), (1, boat_loop)]))
    else:
        out = E.replace_function_body(out, BOAT_UID, 0, boat_init)
        out = E.replace_function_body(out, BOAT_UID, 1, boat_loop)

    # (2) the anchor's shore-snap func
    s2 = EbScript(out)
    if any(f.tag == SNAP_TAG for f in s2.entry(ANCHOR_UID).funcs):
        out = E.replace_function_body(out, ANCHOR_UID, SNAP_TAG, snap)
    else:
        out = E.add_function(out, ANCHOR_UID, SNAP_TAG, snap)

    # (3) Main_Init: InitObject(15, 0) before the final RET (text rebuild, round-trip asserted)
    s3 = EbScript(out)
    f0 = next(f for f in s3.entry(0).funcs if f.tag == 0)
    text = disassemble_block(s3.data, f0.abs_start, f0.abs_end)
    orig_body = s3.data[f0.abs_start:f0.abs_end]
    if assemble_block(text) != orig_body:
        raise SystemExit("Main_Init does not round-trip text<->bytes -- refusing to rebuild it")
    if f"InitObject({BOAT_UID}, 0)" not in text:
        lines = text.rstrip().splitlines()
        if lines[-1].strip() != "RET()":
            raise SystemExit(f"Main_Init does not end in RET() (got {lines[-1]!r}) -- refusing")
        lines.insert(len(lines) - 1, f"InitObject({BOAT_UID}, 0)")
        out = E.replace_function_body(out, 0, 0, assemble_block("\n".join(lines) + "\n"))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--deploy", action="store_true")
    args = ap.parse_args()

    alld = load_all_dispatchers()[NAME]
    # the boat entry's etype byte, read from the real WORLD03 boat (entry 6)
    w03 = EbScript(load_all_dispatchers()["evt_world_world03"]["us"])
    e6 = w03.entry(6)
    etype = w03.data[e6.abs_start] if hasattr(e6, "abs_start") else None
    if etype is None:
        # fall back: entry body offset from the table
        import struct
        off = struct.unpack_from("<H", w03.data, 128 + 6 * 8)[0]
        etype = w03.data[128 + off]
    print(f"WORLD03 boat entry etype = {etype}")

    game_path = config.find_game_path(None)
    eb_root = game_path / MOD_FOLDER / _WORLD_EB_SUBDIR
    bkdir = ROOT / "backups" / "custom-vehicle"
    ts = time.strftime("%Y%m%d-%H%M%S")

    # phase 1: patch EVERY language in memory (a JP-layout surprise aborts before anything is written)
    patched = {}
    for lang in LANGS:
        mod_p = eb_root / lang / FNAME
        base = mod_p.read_bytes() if mod_p.is_file() else alld.get(lang, alld["us"])
        out = patch_one(base, etype)
        patched[lang] = (mod_p, out)
        if lang == "us":
            s = EbScript(out)
            e = s.entry(BOAT_UID)
            print(f"[us] entry {BOAT_UID}: funcs {[f.tag for f in e.funcs]}, "
                  f"{len(out) - len(base):+} bytes vs base")
    # phase 2: write
    if not args.deploy:
        print("dry run OK (all languages patched in memory) -- re-run with --deploy to write")
        return
    for lang in LANGS:
        mod_p, out = patched[lang]
        if mod_p.is_file():
            bkdir.mkdir(parents=True, exist_ok=True)
            bk = bkdir / f"{FNAME}.{lang}.{ts}"
            shutil.copy2(mod_p, bk)
            print(f"  backed up {mod_p} -> {bk}")
        mod_p.parent.mkdir(parents=True, exist_ok=True)
        mod_p.write_bytes(out)
        print(f"  wrote {mod_p} ({len(out)} B)")


if __name__ == "__main__":
    main()
