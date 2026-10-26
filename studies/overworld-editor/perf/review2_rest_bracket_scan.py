"""review2 (rest slice, 73f89a00): the no-bundles CHECK now lists StreamingAssets, but the SCAN behind it still globs
(ff9mapkit.extract._bundles), and the hint is only ever written by that scan. So an install under a path holding
'[...]' with no hint yet still refuses as having no worldmap meshes -- and can never get a hint."""
import sys
import tempfile
import types
from pathlib import Path

HERE = Path(__file__).resolve()
PKG = HERE.parents[3] / "ff9mapkit"
sys.path.insert(0, str(PKG))
import ff9mapkit
assert Path(ff9mapkit.__file__).resolve().is_relative_to(PKG), ff9mapkit.__file__
from ff9mapkit.world import extract as X

fake = types.SimpleNamespace(container={"assets/worldmap/disc1/0_1/r0/block[0][0] terrain.asset": None})
X._load_env = lambda path: fake                      # any bundle file "holds" the disc-1 terrain (no real bytes read)
X._unitypy = lambda: None
root = Path(tempfile.mkdtemp())
for name in ("Games Steam", "Games [Steam]"):
    game = root / name
    (game / "StreamingAssets").mkdir(parents=True)
    (game / "StreamingAssets" / "p0data3.bin").write_bytes(b"a bundle")
    X._WM_ENV_MEMO.clear()
    print(f"{name!r}: _bundles -> {[Path(p).name for p in X._bundles(game)]}", end="; ")
    try:
        X._worldmap_env(1, game=game)
        print("env found; hint written:", (game / "StreamingAssets" / X._WM_BUNDLE_HINT).is_file())
    except ValueError as e:
        print("REFUSED:", str(e)[:60], "| hint written:", (game / "StreamingAssets" / X._WM_BUNDLE_HINT).is_file())
