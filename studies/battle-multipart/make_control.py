"""Turn the deployed 30911 MPBOSSX into the negative control: the PRE-FIX kit's bytes for the same battle.toml.

    py studies/battle-multipart/make_control.py

The pre-fix kit wrote SB2_PUT Flags = 1 on every `type` row. For bench/scene_ctl/battle.toml its output differs
from the fixed kit's in exactly one byte (measured by running both kits on the forked raw16): slot 0's Flags at
offset 17, 3 -> 1. Refuses unless that byte holds the fixed kit's 3 (and slot 0 is type 0), so it can neither
double-apply nor patch the wrong scene. Undo = redeploy, or tools/scroll_out/revert_battle_BBG_B256.py.
"""
from pathlib import Path

RAW16 = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap\StreamingAssets"
             r"\assets\resources\BattleMap\BattleScene\EVT_BATTLE_MPBOSSX\dbfile0000.raw16.bytes")
TYPE0, FLAGS0 = 16, 17                               # header 8 + pattern head 8 + SB2_PUT slot 0 (TypeNo, Flags)

b = bytearray(RAW16.read_bytes())
if (b[TYPE0], b[FLAGS0]) != (0, 3):
    raise SystemExit(f"slot 0 is (type {b[TYPE0]}, flags {b[FLAGS0]}), not the fixed kit's (0, 3) -- not touching it")
b[FLAGS0] = 1
RAW16.write_bytes(bytes(b))
print(f"{RAW16.name}: slot 0 flags 3 -> 1 (the pre-fix kit's master-stripped bytes)")
