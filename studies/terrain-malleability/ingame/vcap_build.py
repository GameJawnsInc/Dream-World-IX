"""BUILD the two meshes for in-game experiment 8 (the VERTEX-CAP WINDOW, capacity CAP-1).

The claim under test: Unity 5.2.3p2 refuses a Mesh with more than 65000 vertices natively ("Mesh.vertices is too
large"), while the s34 loader admits up to 65535 (WorldMeshOverride.cs:186). At build time the kit refused > 65000
(master b68e1c6b), so the 'over' mesh had to be hand-packed. RESULT (RESULTS.md section 8): REFUTED -- 65001 and
65535 verts both render and walk. The kit is back to 65535 (mesh.MAX_MESH_VERTS), so it now accepts 'over' too.

Two Terrain overrides for the isolated open-ocean cell (21,1) (IsSea, all 8 neighbours sea, no live content):
  under  64998 verts (21666 tris) -- written through the kit (ff9mesh_bytes validates it)
  over   65001 verts (21667 tris) -- HAND-PACKED, bypassing the kit's validator on purpose; the packer is first
         CALIBRATED by reproducing ff9mesh_bytes() byte-for-byte on the 'under' mesh
A flat walkable plane at y 6, topograph 0, up-wound, fresh verts per tri. Written to the session scratchpad only.

Rerun:  py studies/terrain-malleability/ingame/vcap_build.py
"""
import os
import struct
import sys
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import mesh as M                # noqa: E402
from ff9mapkit.world.extract import encode_id        # noqa: E402

BX, BY = 21, 1
H = 6.0
SCRATCH = Path(os.environ.get("VCAP_SCRATCH", r"C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX"
                                              r"\8b61f6d3-b0c2-4ade-9f22-b2bc267b1c8d\scratchpad\vcap"))


def plane(ntris):
    """ntris up-facing tris tiling the block (a 104x104 quad grid = 21632 tris, then the remainder as halves of
    sub-quads in the first row) -- every tri strictly inside the block, all at y = H."""
    tris = []
    n = 104
    s = 64.0 / n
    for i in range(n):
        for j in range(n):
            x0, x1 = i * s, (i + 1) * s
            z0, z1 = -j * s, -(j + 1) * s
            tris.append([((x0, H, z0), (0.1, 0.8)), ((x1, H, z0), (0.1, 0.8)), ((x0, H, z1), (0.1, 0.8))])
            tris.append([((x1, H, z0), (0.1, 0.8)), ((x1, H, z1), (0.1, 0.8)), ((x0, H, z1), (0.1, 0.8))])
    extra = ntris - len(tris)
    for k in range(extra):                             # tiny duplicates in the first cell, same plane
        x0, x1, z0, z1 = 0.1 * k / max(extra, 1), 0.1 * k / max(extra, 1) + 0.05, -0.1, -0.15
        tris.append([((x0, H, z0), (0.1, 0.8)), ((x1, H, z0), (0.1, 0.8)), ((x0, H, z1), (0.1, 0.8))])
    tris = tris[:ntris]
    bm = M.tri_soup_block_mesh(tris, name=f"Block[{BX}][{BY}] Terrain", disc=1, x=BX, y=BY)
    idall = float(encode_id(topograph=0))
    for t in bm.tangents:
        t[0] = idall
    # orient every tri UP by its geometric normal (cross(v1-v0, v2-v0).y > 0)
    V = bm.verts
    for k in range(ntris):
        a, b, c = V[3 * k], V[3 * k + 1], V[3 * k + 2]
        ny = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
        if ny < 0:
            V[3 * k + 1], V[3 * k + 2] = c, b
    return bm


def pack(bm) -> bytes:
    """The .ff9mesh layout of mesh.ff9mesh_bytes, WITHOUT validate_blockmesh."""
    verts, normals, uvs, tangents, idx = bm.verts, bm.normals, bm.uvs, bm.tangents, bm.flat_index
    flags = (1 if normals else 0) | (2 if uvs else 0) | (4 if tangents else 0)
    out = bytearray(M.MAGIC) + struct.pack("<iiii", M.VERSION, bm.vcount, len(idx), flags)
    for v in verts:
        out += struct.pack("<3f", *v)
    for n in normals or []:
        out += struct.pack("<3f", *n)
    for u in uvs or []:
        out += struct.pack("<2f", *u)
    for t in tangents or []:
        out += struct.pack("<4f", *t)
    out += struct.pack("<%di" % len(idx), *idx)
    return bytes(out)


def main():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    under = plane(21666)
    kit = M.ff9mesh_bytes(under)                       # validates: must pass at 64998
    mine = pack(under)
    assert kit == mine, "packer calibration failed: hand-packed bytes differ from ff9mesh_bytes"
    over = plane(21667)
    try:
        M.ff9mesh_bytes(over)
        refused = None
    except ValueError as err:
        refused = str(err)[:120]
    (SCRATCH / "under.ff9mesh").write_bytes(kit)
    (SCRATCH / "over.ff9mesh").write_bytes(pack(over))
    print(f"under: vcount {under.vcount} (kit-written, validated); over: vcount {over.vcount} "
          f"(hand-packed; kit verdict: {refused or 'accepted'!r}); calibration: hand packer == kit bytes")


if __name__ == "__main__":
    main()
