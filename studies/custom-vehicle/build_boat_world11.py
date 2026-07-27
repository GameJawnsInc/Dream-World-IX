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
  entry 14 tag 60 -- the shore-snap: MoveInstantXZY(SYSVAR[195..197]) -- the ENGINE's getoff
                     landing point (runs ON the anchor; v2, stock entry-12 tag-22's own read)
  entry 0 tag 0   -- Main_Init gains InitObject(15, 0) (unconditional spawn -- the 9009 pattern)

v2 (2026-07-26, R5c) = THE STOCK BOARDING UX, decoded from WORLD03 entry 3 tag 1 + entry 2's
Byte[37] machine + ff9.w_movementGetGetoff:
  * approach on foot (40u) -> the boat summons its OWN nameplate case (69, "Crimson Narciss"
    via block-68 split[69]) -- the same self-summon lane as the ring's quays; board = Confirm
    while THAT plate is armed (Byte[24]==169), so the case machine arbitrates every confirm
    (no quay race by construction).
  * dismount (Confirm or Cancel while sailing) = RunWorldCode(28,0) -- the engine's getoff
    service: mode-7 gates on the tile AHEAD reading topograph 53 (beach-front), sweeps a
    FOOT-walkable landing around the hull, answers in SYSVAR[195..197] (y==10000 = the refuse
    sentinel -> silently no, stock's own behavior). Player lands at the engine's point; THE
    BOAT PARKS WHERE IT FLOATS (stock semantics; v1.1's moor-home is retired -- it existed
    only to kill the quay race the case machine now kills properly).
Persistence gap (known): Init still re-moors at BOAT_SPAWN on every world (re)load -- the
parked spot survives the session, not a save/field round-trip. Stock persists via
Global[74..82]; ours needs kit-allocated storage (a later rung).

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
from ff9mapkit.world.entrance import (load_all_dispatchers, _WORLD_EB_SUBDIR,   # noqa: E402
                                      explored_set_expr)
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
MODEL_ID = 6321                      # the minted crimson hull (mint_boat.py). Requires the s51 engine
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
# (The v1 fixed DOCK snap at the islet centroid (493, -1114) is retired: the landing point now
#  comes from the ENGINE's getoff sweep, read back through SYSVAR[195..197] -- stock's own channel,
#  see WORLD03 entry 12 tag 22.)

CONFIRM_ON = 131072                  # 0x20000 logical Confirm with B_KEYON (press-edge) -- the exact
                                     # gate the ring's quay entrances use, in-game proven. (The old
                                     # held-key CONFIRM=0x24000 B_KEY form is retired with the bare-
                                     # radius board; the 2026-07-22 input-bit law applied to B_KEY.)
DISMOUNT_ON = 196608                 # 0x30000 = Confirm|Cancel with B_KEYON. Stock's boat dismount
                                     # key is Cancel (0x10000, WORLD03 entry 3 tag 1 @L185); Confirm
                                     # is accepted too (nothing else reads Confirm at sea).


def fp(v: int) -> int:
    """World units -> 26-bit fixed-point as the unsigned const4 literal the .eb dialect wants."""
    return (v * 256) & 0xFFFFFFFF


def wu(v: int) -> int:
    """World units, UNSCALED, as the unsigned const4 literal.

    ⚠⚠ THE FALSE LAW THAT KILLED THE BOAT (kept as a warning -- do NOT compare f[] against this on
    the WORLD MAP). The §20-era claim "f[] returns plain world units" followed getvobj case 0/2
    (`CastFloatToIntWithChecking(((PosObj)obj).pos[i])`, no scaling in the CAST) but never checked
    WHAT WRITES `PosObj.pos[]` on the world: `WMActor.pos`'s setter (WMActor.cs:17-19) stores
    `RealPosition * 256f` -- **the world map's eb-visible pos[] is ×256 FIXED POINT**, so f[] reads
    are fp()-domain there. The "corrected" absolute window in world units could therefore NEVER be
    true (f[0] at the mooring reads 492*256 = 125952, not 492) -- the dormant-boat symptom. The
    ORIGINAL relative gate compared f[]-f[] differences against fp(100) = 25600 and was CORRECT all
    along; the §19-era quay boarding was the v1 float-parked boat legitimately inside its 100u
    radius, which MOOR-HOME alone fixed. THE LAW: on the world map, anything compared against an
    f[] read uses fp(); an offline eval must trace the WRITER of a var, not just its reader."""
    return v & 0xFFFFFFFF


# THE BOARD GATE (restored 2026-07-26, R5; tightened R5c): the ORIGINAL stock-shaped relative
# test -- both actors' f[] reads share the ×256 domain AND any world-wrap epoch, so the differences
# cancel. R5c tightens 100u -> 40u (hull-scale; stock boards on model CONTACT) because the boat now
# parks where it floats: the radius must stay comfortably smaller than the boat-to-quay distances
# the getoff sweep can produce. Within it, the boat's OWN plate (case 69) claims the confirm.
BOARD_RADIUS_FP = 10240            # fp(40) -- the ×256 domain, per the law above

# The boat's nameplate case: the next free VIRGIN case after the ring's quays (65-68). The plate
# reads block-68 split[69] (locid 68, registered as "Crimson Narciss" in the ring's
# marker_renames.toml); its explored bit lives in the kit's reserved word 2006 (bit 4).
BOAT_CASE = 69


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

# v2 -- THE STOCK BOARDING UX (2026-07-26, R5c). Three branches, all decoded from stock:
#
# ON-FOOT + within 40u of the hull:
#   * Confirm pressed AND the boat's plate armed (Byte[24]==BOAT_CASE+100) -> BOARD. The gate rides
#     the case machine, so a quay plate and the boat plate can never both take one press (the R5
#     quay race is dead by construction, not by mooring policy). The Byte[24]=100 settle write on
#     the confirm frame is the ring entrances' proven single-fade guard (disarm the native confirm
#     path); the explored-bit write upgrades the plate "?" -> "Crimson Narciss" (the entrance warp
#     branch's own pattern).
#   * otherwise, machine idle (Byte[24]==100) -> SELF-SUMMON the plate: Byte[39]=BOAT_CASE +
#     RunScriptAsync(6,1,11) -- byte-shape of stock's own boat summoner (WORLD03 tag 38809, case
#     92) and of the ring's quay triggers; re-fires each approach frame, the idle loop reclaims it
#     when the player leaves. This is the "bubble": the native plate + "Enter with (X)" HUD.
#
# SAILING (Byte[190]==7) + Confirm|Cancel pressed -> THE ENGINE GETOFF SERVICE (stock's dismount,
#   WORLD03 entry 3 tag 1 @L185): RunWorldCode(28,0) runs ff9.w_movementGetGetoff -- for mode 7 it
#   demands the tile AHEAD of the hull read topograph 53 (beach-front water), then raycast-sweeps
#   around the hull for FOOT-walkable ground -- and answers in SYSVAR[195..197] (w_frameScriptParam;
#   y == 10000 is the refuse sentinel: open sea / no shore -> silently do nothing, stock behavior).
#   On success: detach, snap the anchor to the ENGINE's landing point (entry 14 tag 60), back to
#   foot mode. THE BOAT STAYS WHERE IT FLOATS -- no moor-home, no fixed dock snap.
BOAT_LOOP = f"""
L0:
SET({{Global.Byte[190] B_NOT obj(uid=250).f[0] obj(uid={BOAT_UID}).f[0] B_MINUS const4({BOARD_RADIUS_FP}) B_LT obj(uid={BOAT_UID}).f[0] obj(uid=250).f[0] B_MINUS const4({BOARD_RADIUS_FP}) B_LT B_ANDAND obj(uid=250).f[2] obj(uid={BOAT_UID}).f[2] B_MINUS const4({BOARD_RADIUS_FP}) B_LT obj(uid={BOAT_UID}).f[2] obj(uid=250).f[2] B_MINUS const4({BOARD_RADIUS_FP}) B_LT B_ANDAND B_ANDAND B_ANDAND B_EXPR_END}})
JMP_IFNOT(L500)
SET({{const4({CONFIRM_ON}) B_KEYON B_EXPR_END}})
JMP_IFNOT(L300)
SET({{Map.Byte[24] const({BOAT_CASE + 100}) B_EQ B_EXPR_END}})
JMP_IFNOT(L900)
SET({{Map.Byte[24] const(100) B_LET B_EXPR_END}})
{{EXPLORED_TEXT}}
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
L300:
SET({{Map.Byte[24] const(100) B_EQ B_EXPR_END}})
JMP_IFNOT(L900)
SET({{Map.Byte[39] const({BOAT_CASE}) B_LET B_EXPR_END}})
RunScriptAsync(6, 1, 11)
JMP(L900)
L500:
SET({{Global.Byte[190] const(7) B_EQ const4({DISMOUNT_ON}) B_KEYON B_ANDAND B_EXPR_END}})
JMP_IFNOT(L900)
RunWorldCode(28, 0)
SET({{B_SYSVAR[196] const(10000) B_EQ B_EXPR_END}})
JMP_IF(L900)
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

# The explored-bit write for BOAT_CASE, as canonical disassembly text (the entrance module owns the
# byte form; disasm->asm round-trips byte-identically through this script's own asm()).
_expl = explored_set_expr(BOAT_CASE)
BOAT_LOOP = BOAT_LOOP.replace("{EXPLORED_TEXT}",
                              disassemble_block(_expl, 0, len(_expl)).strip())

# v2: the anchor lands at the ENGINE's getoff point -- SYSVAR[195..197] read w_frameScriptParam
# exactly as stock's landing func does (WORLD03 entry 12 tag 22 stages them through Map[49/47/52];
# ours reads them direct -- same values, same frame, nothing writes the params in between). SYSVAR
# 196 already carries the eb-domain (negated) y. No TurnInstant: stock keeps the facing.
ANCHOR_SNAP = f"""
MoveInstantXZY({{B_SYSVAR[195] B_EXPR_END}}, {{B_SYSVAR[196] B_EXPR_END}}, {{B_SYSVAR[197] B_EXPR_END}})
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
