"""Reset Block[12][18]'s Sea4 override to the STRIPPED real carried mesh (184 tris).

One-shot recovery step for the FLAT-MESH INVARIANT incident (2026-07-20): the deployed
v3 sea patch carried 30 orphan verts (verts != idx) and crashed the engine's s34 loader
(`WMWorld.RegisterBlockComponent` IndexOutOfRange -> LoadBlocks aborts -> unregistered
pale/unnavigable sea map-wide + spawn relocation). This script strips the bad patch back
to the pristine carried Sea4 so `beach_island_sea_patch.py --deploy` can rebuild the
patch through the now-FLATTENING merge from a clean baseline.

Run: py studies/overworld-topography/sea_patch_reset.py
"""
import importlib.util
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))

from ff9mapkit.world import mesh as M                            # noqa: E402
from ff9mapkit.world import discmirror as DM                     # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "beach_island_sea_patch", Path(__file__).with_name("beach_island_sea_patch.py"))
bsp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bsp)

pre_bm, patch_tris, verified = bsp.split_v1_patch(12, 18)
n_pre = len(pre_bm.flat_index) // 3
print(f"strip: pre={n_pre} tris, removed={len(patch_tris)}, verified={verified}")
if n_pre != 184:
    raise SystemExit(f"expected the pristine carried 184 tris, got {n_pre} -- refusing")

p = M.deploy_override(pre_bm, mod_folder="FF9CustomMap-world", game=None, lod="0_1", part="Sea4")
print("reset wrote:", p)
print("mirror:", DM.auto_mirror([str(p)], mod_folder="FF9CustomMap-world"))
print("Block[12][18] Sea4 is back to the pristine carried mesh -- now run "
      "beach_island_sea_patch.py --deploy to rebuild the patch FLAT.")
