"""A/B harness for the interior-seat fix: run carve_mountain IN MEMORY on fixed real inputs and write the
changed blocks' bytes, so the code before and after the fix can be compared byte for byte.

    py -X utf8 ab_carve.py <ff9mapkit pkg dir> <case: july|comp20|r5> <out dir>
"""
import hashlib
import sys
from pathlib import Path

pkg, case, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
sys.path.insert(0, str(pkg))
from ff9mapkit.world import interior as IN                # noqa: E402
from ff9mapkit.world import mesh as M                     # noqa: E402

SP = Path(r"C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX\4defe9bc-0f55-44e7-952d-bd74e20446f5\scratchpad")
R4PRE = Path(r"C:\gd\Dream-World-IX\backups\west-seam-continent\r4-pre.20260828-103332\Disc1")
LIVE = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap-world\FF9_Data\WorldMap\Disc1\0_1")


def load(root, blocks):
    got = {}
    for bx, by in blocks:
        p = root / f"r{by}" / f"Block[{bx}][{by}] Terrain.ff9mesh"
        if p.is_file():
            got[(bx, by)] = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
    return IN.soup_from_blocks(got)


CONT = [(bx, by) for bx in (21, 22, 23) for by in range(4, 10)]
if case == "july":
    soup = load(SP / "bench-uaho" / "FF9CustomMap-world" / "FF9_Data" / "WorldMap" / "Disc1" / "0_1", [(2, 19)])
    kw = dict(near=(160.0, -1246.0))
elif case == "comp20":
    soup = load(R4PRE, CONT)
    kw = dict(near=(1476.0, -376.0), donor=[(12, 16), (12, 17)])
elif case == "r5":
    soup = load(LIVE, CONT)
    kw = dict(near=(1452.0, -468.0), donor=(0, 0))
else:
    sys.exit(f"unknown case {case}")
logs = []
res = IN.carve_mountain(soup, log=lambda *a: logs.append(" ".join(str(x) for x in a)), **kw)
out.mkdir(parents=True, exist_ok=True)
for (bx, by), bm in sorted(res["changed"].items()):
    p = M.write_ff9mesh(bm, out / f"Block[{bx}][{by}] Terrain.ff9mesh")
    print(f"{case} ({bx},{by}) sha1 {hashlib.sha1(p.read_bytes()).hexdigest()}")
print(f"{case} centre {res['center']} rot {res['rot']}; " + next((l for l in logs if l.startswith("placement")), ""))
