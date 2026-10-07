"""EVIDENCE LAW instrument -- verify every engine line this lane cites, and classify it STOCK vs PATCHED.

For each citation (file under C:\\gd\\FFIX\\Memoria\\Assembly-CSharp, working-copy line range, anchor text):
  * the anchor must occur inside the cited working-copy range (else the cite is WRONG);
  * PATCHED iff the range intersects a `git diff -U0 HEAD` hunk (+side) of the shared clone's working copy
    (read-only `git diff`/`git show`; nothing is built or modified), and then the memoria-patches/*.patch files
    whose text carries the anchor are named; STOCK iff it intersects no hunk -- the stock line number in HEAD
    (6b8bb2d5, memoria-patches/BASE_COMMIT) is reported by locating the anchor there.
Calibration: one known-PATCHED cite (WMWorld.cs RegisterBlockComponent's WorldMeshOverride.TryLoad, s34/s74) must
classify PATCHED with s34 named; a known-STOCK cite (WMPhysics.cs, no diff at all) must classify STOCK.
Writes out/engine_cites.json.
Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_inplace_stitch_composition/engine_cites.py
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import stitchlib as S                                  # noqa: E402

REPO = Path(r"C:\gd\FFIX\Memoria")
AC = "Assembly-CSharp"
PATCHES = Path(r"C:\gd\Dream-World-IX\memoria-patches")
CITES = [
    # id, file (under Assembly-CSharp), (lo, hi) working-copy lines, anchor, claim
    ("CAL-PATCHED", "Global/WM/WMWorld/WMWorld.cs", (820, 826), "WorldMeshOverride.TryLoad",
     "calibration: the s34 loose override hook (must classify PATCHED, s34)"),
    ("CAL-STOCK", "Global/WM/WMPhysics.cs", (6, 45), "num2 <= 0.1f", "calibration: the up-facing filter (STOCK)"),
    ("E1", "Global/ff9/ff9.cs", (1326, 1331), "ff9.rayStartOffsetY = 2.34375f",
     "walk ray origin = actor y + 2.34375 (sky 400; rayDistance 2.8; defaultHeight 0)"),
    ("E2", "Global/ff9/ff9.cs", (1469, 1491), "0xD8FF3CFFu", "on-foot control 0: limit mask {0x0010667F, 0xD8FF3CFF}, flg_gake 0"),
    ("E3", "Global/ff9/ff9.cs", (5476, 5510), "wmActor.pos1 = s_moveCHRStatus.ground_height + s_moveCHRStatus.slice_height",
     "actor y = ground + slice (non-flyer)"),
    ("E4", "Global/ff9/ff9.cs", (5550, 5600), "status.ground_height = pos2.y",
     "walk: a heading fan, the step commits only when w_movementRoundCheck succeeds"),
    ("E5", "Global/ff9/ff9.cs", (5622, 5666), "imd = (num2 <= 0);",
     "slice class 0 = topo 36/37/38 (canopy sink, immediate)"),
    ("E6a", "Global/ff9/ff9.cs", (5687, 5700), "(num2 == 52 || num2 == 49) && ff9.w_moveCHRControlPtr.type != 1",
     "no hit-cache when standing on topo 49/52"),
    ("E6b", "Global/ff9/ff9.cs", (5695, 5702), "if (num3 >= 0)", "a ray MISS (pno -1) refuses the step"),
    ("E7a", "Global/ff9/ff9.cs", (3304, 3314), "height = ff9.w_nwpHit(ref vector, out id, out pno, cache);",
     "w_cellHit -> w_nwpHit"),
    ("E7b", "Global/ff9/ff9.cs", (7296, 7324), "pno = 1000;", "w_nwpHit: pno -1 unless a hit; result 0 on a miss"),
    ("E8", "Global/WM/WMBlock/WMBlock.cs", (137, 180), "for (Int32 i = 0; i < 10; i++)",
     "10-slot hit cache tested BEFORE the scan"),
    ("E9", "Global/WM/WMBlock/WMBlock.cs", (196, 212), "mapid = (Int32)tangents[triangles[hit.triangleIndex * 3]].x;",
     "mapid = tangent.x of the hit tri's first corner; 0x31EE veto"),
    ("E10a", "Global/WM/WMPhysics.cs", (6, 45), "if (num != 4078 || WMPhysics.IgnoreExceptions)",
     "scan skips idall 4078/4088/2040 and non-up-facing tris; first hit in buffer order"),
    ("E10b", "Global/WM/WMPhysics.cs", (47, 66), "public static Boolean RaycastOnSpecifiedTriangle",
     "the CACHE path tests a tri with NO up-facing / idall filter"),
    ("E11a", "Global/WM/WMWorld/WMWorld.cs", (588, 591), "RegisterBlockComponent(block, prefab.ObjectForm1, true, false);",
     "registration order: Object before Terrain"),
    ("E11b", "Global/WM/WMWorld/WMWorld.cs", (748, 807), "RegisterBlockComponent(block, prefab.Sea6, true, true);",
     "then Beach1, Beach2, Stream, River, RiverJoint, Falls, Sea1..Sea6"),
    ("E11c", "Global/WM/WMWorld/WMWorld.cs", (848, 852), "block.AddWalkMeshForm1(mesh);",
     "every form-1 registered part (override or stock) joins the walk scan"),
]


def git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", check=True).stdout


def hunks(rel):
    out = []
    for line in git("diff", "-U0", "HEAD", "--", f"{AC}/{rel}").splitlines():
        m = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", line)
        if m:
            s, n = int(m.group(1)), int(m.group(2) or 1)
            if n:
                out.append((s, s + n - 1))
    return out


res = []
base = next(l.split()[0] for l in (PATCHES / "BASE_COMMIT").read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.lstrip().startswith("#"))
for cid, rel, (lo, hi), anchor, claim in CITES:
    wc = (REPO / AC / rel).read_text(encoding="utf-8-sig", errors="replace").splitlines()
    found = [i + 1 for i, l in enumerate(wc) if anchor in l]
    in_range = [n for n in found if lo <= n <= hi]
    hk = hunks(rel)
    patched = any(not (hi < a or lo > b) for a, b in hk)
    head = git("show", f"HEAD:{AC}/{rel}").splitlines()
    head_lines = [i + 1 for i, l in enumerate(head) if anchor in l]
    in_patches = sorted(p.name for p in PATCHES.glob("*.patch")
                        if anchor in p.read_text(encoding="utf-8", errors="replace"))
    rec = {"id": cid, "file": rel, "cited": [lo, hi], "anchor": anchor, "claim": claim,
           "anchor_at_working_lines": found, "cite_ok": bool(in_range),
           "origin": "PATCHED" if patched else "STOCK", "stock_HEAD_lines": head_lines,
           "patches_carrying_anchor": in_patches}
    res.append(rec)
    print(f"{cid:11s} {rel}:{lo}-{hi}  cite_ok={rec['cite_ok']}  {rec['origin']:7s}  "
          f"HEAD lines {head_lines[:3]}  patches {in_patches[:3]}  -- {claim}")
cal = {r["id"]: r for r in res}
assert cal["CAL-PATCHED"]["origin"] == "PATCHED" and "s34-worldmap-mesh-override.patch" in cal["CAL-PATCHED"]["patches_carrying_anchor"]
assert cal["CAL-STOCK"]["origin"] == "STOCK"
print(f"calibration PASS; HEAD = BASE_COMMIT {base}: {git('rev-parse', 'HEAD').strip().startswith(base[:8])}")
p = S.save_json("engine_cites.json", {"base_commit": base, "cites": res})
print("->", p)
