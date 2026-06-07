#!/usr/bin/env python3
"""LADDER Phase 1 (truth-check): can a region trigger a scripted PLAYER reposition?

Patches the live EVT_TRENO_RES (all 7 langs) so that:
  - a TREAD region on floor 2 (a few steps left of the spawn) sets a transient MAP flag, and
  - the PLAYER entry's tag-1 loop (runs in the player's own context, so MoveInstantXZY moves the
    PLAYER) reads the flag -> teleports the player up to floor 1 (the exit floor) + re-enables pathing.

If the player teleports to floor 1 (and can then walk to the exit), the core mechanism the whole
ladder needs -- region -> scripted player move -- is proven. Phase 2 then adds the climb animation +
the ladder control-attribute for a real climb feel, and finally a generic [[ladder]] kit primitive.

Reversible: backs up each lang's EVT_TRENO_RES first. Re-enter Treno (or press F6 in it) to reload.
Run:  py tools/ladder_proof.py
"""
import datetime
import os
import shutil
import sys
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.config import LANGS, ModLayout, find_game_path  # noqa: E402
from ff9mapkit.eb import EbScript, disasm, edit, opcodes        # noqa: E402
from ff9mapkit.content import region                            # noqa: E402
from ff9mapkit.scene import bgi                                 # noqa: E402

REPO = Path(__file__).resolve().parent.parent
WALK = REPO / "tworoom" / "treno" / "walkmesh.bgi"
MAP_FLAG = 100                     # MAP bit, clear of the player init's bits 144-159


def _centroid(wv, t):
    return tuple(sum(wv[i][k] for i in t.vtx) / 3.0 for k in range(3))


def _nearest_on_floor(wm, wv, floor, target_xz):
    cands = [_centroid(wv, t) for t in wm.tris if t.floor_ndx == floor]
    return min(cands, key=lambda c: (c[0] - target_xz[0]) ** 2 + (c[2] - target_xz[1]) ** 2)


def main():
    wm = bgi.BgiWalkmesh.from_file(WALK)
    wv = wm.world_verts()
    # DIAGNOSTIC: big zone covering floor 2 LEFT of the spawn column (x<12000), so no warp-on-spawn but
    # walking left crosses it -> we watch the on-screen flag flip to 1 (region fires on walk?) and whether
    # the teleport follows (loop reads it?). Resolves region-fires-on-walk vs loop-teleports.
    zone = [[7600, -19350], [12000, -19350], [12000, -15350], [7600, -15350]]
    land = _nearest_on_floor(wm, wv, 1, (7200, -14000))      # floor-1 landing, clear of the exit zone
    lx, ly, lz = (round(c) for c in land)
    print(f"trigger (ladder base) zone x[7700,8950] z[-16400,-15250] ; landing (floor 1) ({lx},{lz},y={ly})")

    # player-loop block: if MAP[flag] -> clear it, teleport player to floor 1, re-enable pathing
    # player loop: when flag set (region disabled control), teleport + re-enable control.
    climb = region.if_block(
        region.cond_truthy(region.MAP_BOOL, MAP_FLAG),
        region.set_var(region.MAP_BOOL, MAP_FLAG, 0)
        + opcodes.move_instant_xzy(lx, lz, ly)
        + opcodes.set_pathing(1)
        + opcodes.ENABLE_MOVE,
    )
    # region tread body: DisableMove FIRST (the controlled player's script is suspended while
    # usercontrol==1; DisableMove -> usercontrol=0 -> the player's loop runs + reads the flag), then set it.
    range_body = opcodes.DISABLE_MOVE + region.set_var(region.MAP_BOOL, MAP_FLAG, 1) + opcodes.RETURN

    live = ModLayout(find_game_path() / "FF9CustomMap")
    bk = REPO / "backups"
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    for L in LANGS:
        p = live.eb_path(L, "EVT_TRENO_RES.eb.bytes")
        data = p.read_bytes()
        shutil.copyfile(p, bk / f"{L}-EVT_TRENO_RES.eb.bytes.preladder.{stamp}")
        data, slot = region.inject_region(data, zone, range_body, tag=region.RANGE_TAG)
        eb = EbScript.from_bytes(data)
        loop = eb.entry(1).func_by_tag(1)                   # player entry tag-1 loop
        data = edit.insert_bytes(data, loop.abs_start, climb)
        p.write_bytes(data)
        if L == "us":
            s = EbScript.from_bytes(data)
            f = s.entry(1).func_by_tag(1)
            print(f"  region slot {slot}; player loop now:")
            for ins in s.instrs(f):
                print("    ", ins)
        print(f"  {L}: -> {len(data)} bytes")

    rev = REPO / "tools" / "scroll_out" / "revert_ladder_proof.py"
    rev.parent.mkdir(parents=True, exist_ok=True)
    lines = ['"""Revert the ladder Phase-1 patch on EVT_TRENO_RES."""', "import shutil",
             "from pathlib import Path",
             f"live = Path(r{str(find_game_path() / 'FF9CustomMap')!r})",
             f"bk = Path(r{str(bk)!r}); stamp = {stamp!r}",
             "base = 'StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/field'",
             f"for L in {LANGS!r}:",
             "    shutil.copyfile(bk / f'{L}-EVT_TRENO_RES.eb.bytes.preladder.{stamp}',",
             "                    live / base / L / 'EVT_TRENO_RES.eb.bytes')",
             "print('reverted ladder proof')", ""]
    rev.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"\nTEST: enter Treno (or F6 in it). Walk LEFT a few steps onto the trigger -> you should")
    print(f"      teleport up to floor 1, then be able to walk to the exit back to the grotto.")
    print(f"revert: py {rev.relative_to(REPO).as_posix()}")


if __name__ == "__main__":
    main()
