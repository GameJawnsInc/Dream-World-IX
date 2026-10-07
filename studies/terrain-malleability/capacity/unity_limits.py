"""CAPACITY lane, step 10 -- THE NATIVE MESH LIMITS of the Unity player FF9 actually runs (READ-ONLY scan of
the install's x64/x86 FF9.exe for the engine's own error strings; nothing executed).

Why: the s34 loader (WorldMeshOverride.cs:186, memoria-patches/s34-worldmap-mesh-override.patch:378) and the kit's
write seam (ff9mapkit/world/mesh.py:121) both accept vcount <= 65535 "because Unity 5.2.3 has 16-bit indices".
Index WIDTH is not the only gate: Unity <= 2017.2 ALSO caps Mesh.vertices at 65000 in native code. If the
player binary carries that message, the true per-mesh ceiling is 65000 verts -> 21666 tris under the
UNINDEXED CONTRACT (vcount == icount), and 65001..65535 is a window both checks wrongly admit.
REFUTED IN-GAME (ingame/RESULTS.md section 8): the string is in the binary, but 65001- and 65535-vert parts
render and walk. The binding ceiling is s34's 65535 (21845 tris); the kit matches it.

Calibration: the same scan must find the triangle-setter messages that every Unity 5.x player has
("Failed setting triangles...") -- if those are absent the instrument is blind, not the limit.

Writes out/unity_limits.json.  Run:  py studies/terrain-malleability/capacity/unity_limits.py
"""
import json
import re
from pathlib import Path

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
OUT = Path(__file__).resolve().parent / "out"
PATS = {
    "vertex_cap": re.compile(rb"Mesh\.vertices is too large\. A mesh may not have more than (\d+) vertices\."),
    "calib_tri_oob": re.compile(rb"Failed setting triangles\. Some indices are referencing out of bounds vertices\."),
    "calib_tri_mult3": re.compile(rb"Failed setting triangles\. The number of supplied triangle indices must be a multiple of 3\."),
}
# managed API surface: a 32-bit index buffer needs Mesh.indexFormat (Unity >= 2017.3). Calibrated by get_vertices.
MANAGED = {"set_indexFormat (32-bit index API)": rb"set_indexFormat", "calib_get_vertices": rb"get_vertices"}


def main():
    res = {}
    for arch in ("x64", "x86"):
        exe = GAME / arch / "FF9.exe"
        if not exe.is_file():
            continue
        data = exe.read_bytes()
        r = {}
        for k, p in PATS.items():
            hits = p.findall(data)
            r[k] = sorted({h.decode() if isinstance(h, bytes) else h for h in hits}) if hits and p.groups else len(p.findall(data))
        dll = GAME / arch / "FF9_Data" / "Managed" / "UnityEngine.dll"
        if dll.is_file():
            md = dll.read_bytes()
            r["managed_UnityEngine.dll"] = {k: md.count(v) for k, v in MANAGED.items()}
        res[arch] = r
    caps = {int(v) for a in res.values() for v in (a.get("vertex_cap") or [])}
    res["verdict"] = {"native_vertex_cap": sorted(caps),
                      "max_tris_unindexed": [c // 3 for c in sorted(caps)],
                      "kit_and_loader_accept_up_to": 65535,
                      "admitted_but_native_rejected_window": [min(caps) + 1, 65535] if caps else None}
    OUT.mkdir(exist_ok=True)
    (OUT / "unity_limits.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
