"""review2 (rest slice, 49e719f0): the census precompute judges every triangle of every mesh up front; the fix
leaves only a TANGENTLESS mesh to the per-sample code. A mesh WITH tangents whose IDALL (tangent.x) is NaN/inf on a
triangle no sample touches still raises under the precompute, where the per-sample census (index-bucketed) never
asks that triangle."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve()
PKG = HERE.parents[3] / "ff9mapkit"
sys.path.insert(0, str(PKG))
import ff9mapkit
assert Path(ff9mapkit.__file__).resolve().is_relative_to(PKG), ff9mapkit.__file__
sys.path.insert(0, str(PKG))
from ff9mapkit.world import placement as P
from ff9mapkit.world.extract import CH_TAN
from tests.test_world_placement_census import _stack
from tests.test_world_placement_order import GRASS, _bm

for bad in (float("nan"), float("inf")):
    stack = _stack()
    far = _bm([(((200.0, 5.0, -200.0), (210.0, 5.0, -200.0), (200.0, 5.0, -210.0)), GRASS)], name="Block[0][0] Object")
    for row in far.chan_arrays[CH_TAN]:
        row[0] = bad                                     # an IDALL no sample ever reads (off the sampled span)
    stack = [("Object", far), stack[1]]
    real = P._prepare
    P._prepare = lambda meshlist: None
    try:
        slow = P.census(stack, samples=12)
        print(f"IDALL={bad}: per-sample census OK, {sum(slow['counts'].values())} samples")
    except Exception as e:
        print(f"IDALL={bad}: per-sample census raised {type(e).__name__}: {e}")
    P._prepare = real
    try:
        fast = P.census(stack, samples=12)
        print(f"IDALL={bad}: precomputed census OK, same={fast == slow}")
    except Exception as e:
        print(f"IDALL={bad}: precomputed census raised {type(e).__name__}: {e}")
