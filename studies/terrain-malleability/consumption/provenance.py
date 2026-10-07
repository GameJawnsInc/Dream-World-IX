"""PROVENANCE ORACLE -- is a cited engine line STOCK Memoria or added by our patch stack?

The Memoria clone (C:/gd/FFIX/Memoria) is the PATCHED working tree on top of the pinned upstream
commit (memoria-patches/BASE_COMMIT = 6b8bb2d5 = the clone's HEAD). So a line is patch-added iff it
appears as an added line in `git diff -U0 HEAD -- <file>` (tracked file) or the file is untracked
(wholly patch-added, e.g. Memoria/World/WorldMeshOverride.cs). Attribution to a specific patch =
the patch files in memoria-patches/ whose '+' lines contain the line's text.

READ-ONLY: uses `git --no-optional-locks` (no index refresh write) and only reads files.

CALIBRATION (run with no args): three known cases must classify correctly or the script exits 1:
  * WMBlock.cs:159 'All vertices, triangles, tangents' warning      -> STOCK (file unmodified)
  * WMWorld.cs line containing 'HasLandOverride(this.overrideDiscTag, initialX' -> PATCH (s34/s74)
  * WMWorld.cs line containing 'RegisterBlockComponent(block, prefab.Sea3, true, true)' -> STOCK
  * WorldMeshOverride.cs:82 (HasLandOverride body)                  -> PATCH (untracked file)

Usage:
  py provenance.py                       # calibrate + print the verdict for every cite in CITES below
  py provenance.py <relpath>:<line> ...  # ad-hoc lines (relpath under Assembly-CSharp/)
"""
import json
import re
import subprocess
import sys
from pathlib import Path

MEMORIA = Path(r"C:\gd\FFIX\Memoria")
ACS = MEMORIA / "Assembly-CSharp"
PATCHES = Path(r"C:\gd\Dream-World-IX\memoria-patches")
OUT = Path(__file__).resolve().parent / "out"

_DIFF_CACHE = {}
_UNTRACKED = None


def _git(*args):
    return subprocess.run(["git", "--no-optional-locks", "-C", str(MEMORIA), *args],
                          capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


def _untracked():
    global _UNTRACKED
    if _UNTRACKED is None:
        _UNTRACKED = set(_git("ls-files", "--others", "--exclude-standard", "Assembly-CSharp").split("\n"))
    return _UNTRACKED


def added_lines(rel):
    """Set of 1-based line numbers in the WORKING file that the patch stack added (vs HEAD)."""
    if rel in _DIFF_CACHE:
        return _DIFF_CACHE[rel]
    full = "Assembly-CSharp/" + rel
    if full in _untracked():
        n = len((ACS / rel).read_text(encoding="utf-8", errors="replace").split("\n"))
        _DIFF_CACHE[rel] = set(range(1, n + 1))
        return _DIFF_CACHE[rel]
    added = set()
    for m in re.finditer(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", _git("diff", "-U0", "HEAD", "--", full), re.M):
        start, cnt = int(m.group(1)), int(m.group(2) if m.group(2) is not None else 1)
        added.update(range(start, start + cnt))
    _DIFF_CACHE[rel] = added
    return added


_PATCH_TEXT = None


def _patch_plus_lines():
    global _PATCH_TEXT
    if _PATCH_TEXT is None:
        _PATCH_TEXT = {}
        for p in sorted(PATCHES.glob("*.patch")):
            plus = [ln[1:].strip() for ln in p.read_text(encoding="utf-8", errors="replace").split("\n")
                    if ln.startswith("+") and not ln.startswith("+++")]
            _PATCH_TEXT[p.name] = set(x for x in plus if x)
    return _PATCH_TEXT


def classify(rel, line):
    text = (ACS / rel).read_text(encoding="utf-8", errors="replace").split("\n")[line - 1].strip()
    is_patch = line in added_lines(rel)
    who = []
    if is_patch and text:
        who = [name for name, s in _patch_plus_lines().items() if text in s]
    return {"cite": f"{rel}:{line}", "verdict": "PATCH" if is_patch else "STOCK", "patches": who, "text": text[:140]}


def find_line(rel, needle, nth=1):
    lines = (ACS / rel).read_text(encoding="utf-8", errors="replace").split("\n")
    hits = [i + 1 for i, ln in enumerate(lines) if needle in ln]
    if len(hits) < nth:
        raise SystemExit(f"needle not found: {rel} :: {needle!r}")
    return hits[nth - 1]


def calibrate():
    cases = [
        ("Global/WM/WMBlock/WMBlock.cs", find_line("Global/WM/WMBlock/WMBlock.cs", "All vertices, triangles, tangents"), "STOCK"),
        ("Global/WM/WMWorld/WMWorld.cs", find_line("Global/WM/WMWorld/WMWorld.cs", "HasLandOverride(this.overrideDiscTag, initialX"), "PATCH"),
        ("Global/WM/WMWorld/WMWorld.cs", find_line("Global/WM/WMWorld/WMWorld.cs", "RegisterBlockComponent(block, prefab.Sea3, true, true)"), "STOCK"),
        ("Memoria/World/WorldMeshOverride.cs", 82, "PATCH"),
    ]
    ok = True
    for rel, ln, want in cases:
        r = classify(rel, ln)
        good = r["verdict"] == want
        ok &= good
        print(f"  calib {'OK ' if good else 'BAD'} {r['cite']:<45} want={want} got={r['verdict']} {r['patches']}")
    return ok


# Every engine line the consumption NOTES.md cites, located by a unique needle so the verdict survives
# line drift (the patch stack shifts numbers every rebuild). (relpath, needle, nth)
CITES = [
    ("Global/WM/WMBlock/WMBlock.cs", "private void AddWalkMesh(List<WMMesh> walkMeshes, Mesh mesh)", 1),
    ("Global/WM/WMBlock/WMBlock.cs", "Vector3 item = Vector3.Cross(a - b, a2 - b);", 1),
    ("Global/WM/WMBlock/WMBlock.cs", "mapid = (Int32)tangents[triangles[hit.triangleIndex * 3]].x;", 1),
    ("Global/WM/WMBlock/WMBlock.cs", "if (MaterialDatabase.TryGetValue(renderer.gameObject.name, out Material material))", 1),
    ("Global/WM/WMBlock/WMBlock.cs", "{ \"Terrain\", [\"WorldMap/Materials/Terrain\"", 1),
    ("Global/WM/WMPhysics.cs", "Int32 num = (Int32)tangents[triangles[i * 3]].x;", 1),
    ("Global/WM/WMPhysics.cs", "Single num2 = Vector3.Dot(Vector3.up, mesh.TriangleNormals[i]);", 1),
    ("Global/WM/WMWorld/WMWorld.cs", "if (block.IsSea)", 1),
    ("Global/WM/WMWorld/WMWorld.cs", "&& Memoria.World.WorldMeshOverride.HasLandOverride(this.overrideDiscTag, initialX, initialY))", 1),
    ("Global/WM/WMWorld/WMWorld.cs", "this.LoadBlock(this.SeaBlockPrefab, block);", 1),
    ("Global/WM/WMWorld/WMWorld.cs", "String.Format(\"WorldMap/Prefabs/WorldDisc{0}/r{1}/{2}\", disc, initialY, arg);", 1),
    ("Global/WM/WMWorld/WMWorld.cs", "String donorPath = Memoria.World.WorldMeshOverride.TryReadDonorPath(", 1),
    ("Global/WM/WMWorld/WMWorld.cs", "if (prefab.ObjectForm1)", 1),
    ("Global/WM/WMWorld/WMWorld.cs", "if (prefab.TerrainForm1)", 1),
    ("Global/WM/WMWorld/WMWorld.cs", "RegisterBareObjectOverride(block, prefab.TerrainForm1);", 1),
    ("Global/WM/WMWorld/WMWorld.cs", "if (block.Number == 219 && !Memoria.World.WorldDiscSpike.SuppressStockLandmarks)", 1),
    ("Global/WM/WMWorld/WMWorld.cs", "RegisterBlockComponent(block, prefab.Beach1, true, true);", 1),
    ("Global/WM/WMWorld/WMWorld.cs", "RegisterBlockComponent(block, prefab.Sea4, true, true);", 1),
    ("Global/WM/WMWorld/WMWorld.cs", "Mesh ff9Override = Memoria.World.WorldMeshOverride.TryLoad(String.Format(", 1),
    ("Global/WM/WMWorld/WMWorld.cs", "block.AddWalkMeshForm1(mesh);", 1),
    ("Global/WM/WMWorld/WMWorld.cs", "Texture2D custTex = Memoria.World.WorldMeshOverride.TryLoadTexture(", 1),
    ("Global/WM/WMWorld/WMWorld.cs", "String arg = String.Format(\"Block[{0}][{1}]f\", 12, 0);", 1),
    ("Global/WM/WMWorld/WMWorld.cs", "String landDonorName = String.Format(", 1),
    ("Global/WM/WMWorld/WMWorld.cs", "&& Memoria.World.WorldMeshOverride.HasLandOverride(this.overrideDiscTag, wmblock.InitialX, wmblock.InitialY))", 1),
    ("Global/WM/WMWorld/WMWorld.cs", "String prefabName = String.Format(\"WorldMap/Prefabs/WorldDisc{0}/r{1}/{2}\", disc, y, blockName);", 1),
    ("Memoria/World/WorldMeshOverride.cs", "return Exists(String.Format(\"WorldMap/Disc{0}/0_1/r{1}/Block[{2}][{3}] Terrain\"", 1),
    ("Memoria/World/WorldMeshOverride.cs", "mesh.triangles = indices;", 1),
    ("Memoria/World/WorldMeshOverride.cs", "mesh.RecalculateBounds();", 1),
    ("Global/ff9/ff9.cs", "public static Int32 m_GetIDArea(Int32 IDALL)", 1),
    ("Global/ff9/ff9.cs", "if (ff9.w_frameScenePtr < 4990 && ff9.m_GetIDArea(ff9.m_moveActorID) == 12)", 1),
    ("Global/ff9/ff9.cs", "if (!ff9.w_cameraSysDataCamera.upperCounterForce && (ff9.w_frameScenePtr >= 4990 || ff9.m_GetIDArea(ff9.m_moveActorID) != 12))", 1),
    ("Global/ff9/ff9.cs", "if (ff9.m_GetIDArea(idall) != 0 || ff9.m_GetIDTopograph(idall) == 0 || ff9.m_GetIDTopograph(idall) == 37)", 1),
    ("Global/ff9/ff9.cs", "Int32 area = ff9.m_GetIDArea(idall);", 1),
    ("Global/ff9/ff9.cs", "switch (ff9.m_GetIDArea(ff9.m_moveActorID))", 1),
    ("Global/ff9/ff9.cs", "Int32 zoneId = ff9.w_worldArea2Zone(ff9.m_GetIDArea(ff9.m_moveActorID));", 1),
    ("Global/ff9/ff9.cs", "// s60: a (zone, topograph, fog) TABLE HOLE means NO ENCOUNTER.", 1),
]


def main(argv):
    OUT.mkdir(exist_ok=True)
    print("CALIBRATION")
    if not calibrate():
        print("calibration FAILED -- the instrument is not trustworthy; aborting")
        return 1
    rows = []
    if argv:
        for a in argv:
            rel, ln = a.rsplit(":", 1)
            rows.append(classify(rel, int(ln)))
    else:
        for rel, needle, nth in CITES:
            rows.append(classify(rel, find_line(rel, needle, nth)))
    print("\nVERDICTS")
    for r in rows:
        print(f"  {r['verdict']:<5} {r['cite']:<42} {','.join(r['patches']) or '-':<46} {r['text'][:70]}")
    if not argv:
        (OUT / "provenance.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
        print(f"\nwrote {OUT / 'provenance.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
