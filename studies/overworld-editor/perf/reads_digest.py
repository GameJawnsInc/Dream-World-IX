"""reads_digest: the floor of a bytes-keyed soup memo's "has anything changed?" pass -- read + sha1 every deployed
Terrain file of the whole-map window (126 files, 4.8 MB) -- against the 576 exists() probes read_deployed_blocks makes.
    py studies/overworld-editor/perf/reads_digest.py"""
import hashlib, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from reads_common import dump, lane_draft, stat, timeit  # noqa: E402
d = lane_draft()
root = d / "FF9_Data" / "WorldMap" / "Disc1" / "0_1"
paths = [root / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh" for bx in range(24) for by in range(-2, 22)]
def digest_pass():
    out = {}
    for p in paths:
        try:
            out[p] = hashlib.sha1(p.read_bytes()).digest()
        except OSError:
            pass
    return out
ts, out = timeit(digest_pass, 7, 1)
res = {"files": len(out), "digest_pass": stat(ts)}
print(res); dump("reads_digest.json", res)
