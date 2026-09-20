#!/usr/bin/env python3
"""LADDER (faithful): replicate FF9's REAL ladder mechanism, decoded from Treno/Residence.

Real pattern (entry 15 = the ladder region; entry 19 = the player):
  - region tag 2 (tread)   : ifnot(usercontrol) return ; Bubble(1)            -> shows the "!" prompt
  - region tag 3 (action)  : ifnot(usercontrol) return ; DisableMove ;
                             RunScriptSync(2, 250, 17) ; EnableMove           -> run the PLAYER's climb
  - player tag 17 (climb)  : <moves the player up>                            -> runs in the player's
                             context (UID 250), so its moves move the PLAYER; RunScriptSync waits for it.

This sidesteps the suspended-player-loop problem entirely: the region calls the player's climb function
directly. The real climb is bespoke multi-jump; here the climb is a simple teleport up to floor 1 (the
exit floor) -- faithful TRIGGER, simplified climb body (add jumps/animation later).

Reversible (backs up EVT_TRENO_RES per lang). Re-enter Treno / ~ to reload. Run: py tools/ladder_real.py
"""
import datetime
import os
import sys
import shutil
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.config import LANGS, ModLayout, find_game_path   # noqa: E402
from ff9mapkit.eb import EbScript, edit, opcodes                # noqa: E402
from ff9mapkit.content import region                            # noqa: E402

REPO = Path(__file__).resolve().parent.parent
PLAYER_UID = 250
CLIMB_TAG = 17
PLAYER_ENTRY = 1
LADDER_ZONE = [(9016, -16722), (9574, -17758), (9791, -17674)]   # entry-15's real ladder triangle
LANDING = (7053, -14226, -6003)                                  # floor 1 near the exit (x, z, y)
RUNSCRIPTSYNC = 0x14
BUBBLE = 0x68


def build_ladder_region(zone):
    """A 3-function region: init(SetRegion), tread(Bubble prompt), interact(DisableMove+RunScriptSync climb)."""
    init = region.set_region(zone) + opcodes.RETURN
    tread = region.MOVEMENT_GATE + opcodes.encode(BUBBLE, 1) + opcodes.RETURN
    interact = (region.MOVEMENT_GATE + opcodes.DISABLE_MOVE
                + opcodes.encode(RUNSCRIPTSYNC, 2, PLAYER_UID, CLIMB_TAG)
                + opcodes.ENABLE_MOVE + opcodes.RETURN)
    return region.pack_entry_funcs([(0, init), (2, tread), (3, interact)])   # type 1 = region


def main():
    climb = (opcodes.move_instant_xzy(LANDING[0], LANDING[1], LANDING[2])
             + opcodes.set_pathing(1) + opcodes.RETURN)
    live = ModLayout(find_game_path() / "FF9CustomMap")
    bk = REPO / "backups"
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    for L in LANGS:
        p = live.eb_path(L, "EVT_TRENO_RES.eb.bytes")
        data = p.read_bytes()
        shutil.copyfile(p, bk / f"{L}-EVT_TRENO_RES.eb.bytes.preladderreal.{stamp}")
        data = edit.add_function(data, PLAYER_ENTRY, CLIMB_TAG, climb)   # player climb tag 17
        eb = EbScript.from_bytes(data)
        rslot = eb.first_free_slot()
        data = edit.append_entry(data, rslot, build_ladder_region(LADDER_ZONE))
        data = edit.activate(data, opcodes.init_region(rslot, 0))
        p.write_bytes(data)
        if L == "us":
            s = EbScript.from_bytes(data)
            print(f"player entry now tags: {[f.tag for f in s.entry(PLAYER_ENTRY).funcs]}")
            print(f"ladder region slot {rslot}, tags: {[f.tag for f in s.entry(rslot).funcs]}")
        print(f"  {L}: -> {len(data)} bytes")

    rev = REPO / "tools" / "scroll_out" / "revert_ladder_real.py"
    rev.parent.mkdir(parents=True, exist_ok=True)
    rev.write_text(
        '"""Revert the faithful ladder patch on EVT_TRENO_RES."""\nimport shutil\nfrom pathlib import Path\n'
        f"live = Path(r{str(find_game_path() / 'FF9CustomMap')!r})\nbk = Path(r{str(bk)!r}); stamp={stamp!r}\n"
        "base='StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/field'\n"
        f"for L in {LANGS!r}:\n"
        "    shutil.copyfile(bk/f'{L}-EVT_TRENO_RES.eb.bytes.preladderreal.{stamp}', live/base/L/'EVT_TRENO_RES.eb.bytes')\n"
        "print('reverted faithful ladder')\n", encoding="utf-8", newline="\n")
    print("\nTEST: enter Treno / ~. Walk down-left to the ladder base -> a \"!\" prompt should appear ->")
    print("      press the action button -> you climb (teleport) up to floor 1 -> walk to the exit.")
    print(f"revert: py {rev.relative_to(REPO).as_posix()}")


if __name__ == "__main__":
    main()
