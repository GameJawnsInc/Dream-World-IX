"""Eyeball check: print the patched WORLD11's new/changed functions as disasm text."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ff9mapkit"))
sys.path.insert(0, str(ROOT / "studies" / "custom-vehicle"))

import build_boat_world11 as B                                        # noqa: E402
from ff9mapkit.world.entrance import load_all_dispatchers             # noqa: E402
from ff9mapkit.eb.model import EbScript                               # noqa: E402
from ff9mapkit.eb.cmdasm import disassemble_block                     # noqa: E402

alld = load_all_dispatchers()[B.NAME]
out = B.patch_one(alld["us"], 2)
s = EbScript(out)
for ei, tags in ((15, (0, 1)), (14, (B.SNAP_TAG,)), (0, (0,))):
    for f in s.entry(ei).funcs:
        if f.tag in tags:
            print(f"===== entry {ei} tag {f.tag} =====")
            print(disassemble_block(s.data, f.abs_start, f.abs_end))
            print()
