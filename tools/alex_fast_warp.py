#!/usr/bin/env python3
"""DEBUG shortcut: make Alexandria (field 100) warp straight to the test field 4003.
  1) repoint field 100's hut DOOR  Field(4000) -> Field(4003)  (skips the 2 hut hops)
  2) move the New-Game spawn (block B / entrance 231) onto the door  (0,332) -> (-250,2100)
Both are reversible (backups + tools/scroll_out/revert_alex_fast_warp.py). Door repoint is robust
(located via disasm); spawn move is assert-guarded -- if the offsets shifted it skips the spawn move
and only the door repoint applies (you'd just walk up the street once). NOT for release.
"""
import os, sys, struct, datetime
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.config import find_game_path, ModLayout, LANGS
from ff9mapkit.eb import EbScript, edit, disasm

EB = "evt_alex1_at_street_a.eb.bytes"
OLD_TARGET, NEW_TARGET = 4000, 4003
# block B (entrance 231) player-init coords (located by byte-stride signature in the live file):
# X@10904 Z@10912 dir@10920 -- shifted +6 from alex_newgame_spawn's original offsets (later edits).
SPAWN = {10904: (struct.pack("<h", 0),   struct.pack("<h", -250)),   # X 0 -> -250
         10912: (struct.pack("<h", 332), struct.pack("<h", 2100))}   # Z 332 -> 2100 (at the door)

live = ModLayout(find_game_path() / "FF9CustomMap")
BK = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backups")))
OUT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "scroll_out"))); OUT.mkdir(exist_ok=True)
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

door_ok = spawn_ok = 0
for L in LANGS:
    p = live.eb_path(L, EB)
    eb = bytearray(p.read_bytes())
    (BK / f"{L}-{EB}.preFASTWARP.{STAMP}").write_bytes(eb)
    # 1) door repoint: the single Field(4000) -> Field(4003)
    s = EbScript.from_bytes(bytes(eb))
    for ent in s.entries:
        for fn in ent.funcs:
            for ins in disasm.iter_code(bytes(eb), fn.abs_start, fn.abs_end):
                if ins.op == 0x2B and ins.imm(0) == OLD_TARGET:
                    off = (ins.end - ins.length) + 2
                    assert bytes(eb[off:off+2]) == struct.pack("<H", OLD_TARGET)
                    eb[off:off+2] = struct.pack("<H", NEW_TARGET); door_ok += 1
    # 2) spawn move (assert-guarded)
    if all(bytes(eb[o:o+2]) == old for o, (old, _new) in SPAWN.items()):
        for o, (_old, new) in SPAWN.items():
            eb[o:o+2] = new
        spawn_ok += 1
    p.write_bytes(bytes(eb))
    print(f"{L}: door->{NEW_TARGET} {'ok' if door_ok else 'MISS'}; "
          f"spawn {'moved' if spawn_ok else 'SKIPPED (offsets shifted)'}")

revert = f'''#!/usr/bin/env python3
import sys, shutil
from pathlib import Path
sys.path.insert(0, r"{KIT}")
from ff9mapkit.config import find_game_path, ModLayout, LANGS
BK=Path(r"{BK}"); live=ModLayout(find_game_path()/"FF9CustomMap")
for L in LANGS:
    shutil.copyfile(BK/f"{{L}}-{EB}.preFASTWARP.{STAMP}", live.eb_path(L,"{EB}"))
print("reverted Alexandria fast-warp: door + New-Game spawn restored.")
'''
(OUT / "revert_alex_fast_warp.py").write_text(revert, encoding="utf-8", newline="\n")
print(f"\ndoor repointed in {door_ok}/7 ; spawn moved in {spawn_ok}/7")
print(f"revert: {OUT/'revert_alex_fast_warp.py'}")
print("Now: New Game -> Alexandria (at the door) -> step into it -> field 4003.")
