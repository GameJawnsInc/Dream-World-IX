"""THE UNINDEXED RE-PACK — every emitted mesh must satisfy the engine's contract.

WMBlock.AddWalkMesh (WMBlock.cs:60-73) iterates vertices.Length/3 and indexes
triangles[i*3] — the engine expects FULLY UNINDEXED meshes (vcount == icount, 3 fresh
verts per tri; it even warns "All vertices, triangles, tangents .Length must be
equal"). vcount > icount OVERRUNS the index buffer at block registration (the brick);
vcount < icount builds TriangleNormals SHORT (a latent query-time hazard).

This tool re-packs any .ff9mesh to the contract layout: per triangle, 3 fresh verts
carrying their channels; orphaned verts dropped; geometry (the tri soup) identical.

  py vcorner_repack.py check <file...>      report vcount/icount contract state
  py vcorner_repack.py repack <in> <out>    write the unindexed re-pack
  py vcorner_repack.py verify <a> <b>       assert identical tri soups (order + channels)
"""
from __future__ import annotations

import dataclasses
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import walk_sim as W                                        # noqa: E402
from ff9mapkit.world.extract import CH_POS, CH_NRM, CH_UV, CH_TAN  # noqa: E402


def soup(path):
    """The mesh as an ordered list of tris, each 3 verts of (pos, nrm, uv, tan)."""
    d = W.M.read_ff9mesh(path)
    idx = d["indices"]
    out = []
    for t0 in range(0, len(idx), 3):
        tri = []
        for k in range(3):
            j = idx[t0 + k]
            tri.append((tuple(d["verts"][j]),
                        tuple(d["normals"][j]) if d["normals"] else None,
                        tuple(d["uvs"][j]) if d["uvs"] else None,
                        tuple(d["tangents"][j]) if d["tangents"] else None))
        out.append(tuple(tri))
    return out, d


def repack(src, dst):
    tris, d = soup(src)
    verts, nrms, uvs, tans, idx = [], [], [], [], []
    for tri in tris:
        for (p, n, u, t) in tri:
            idx.append(len(verts))
            verts.append(list(p))
            if n is not None:
                nrms.append(list(n))
            if u is not None:
                uvs.append(list(u))
            if t is not None:
                tans.append(list(t))
    bm = W.M.blockmesh_from_ff9mesh(src, disc=W.DISC, x=0, y=0, part="x")
    chan = {CH_POS: verts}
    if nrms:
        chan[CH_NRM] = nrms
    if uvs:
        chan[CH_UV] = uvs
    if tans:
        chan[CH_TAN] = tans
    out = dataclasses.replace(bm, vcount=len(verts), chan_arrays=chan, flat_index=idx,
                              tris=[[idx[k], idx[k + 1], idx[k + 2]] for k in range(0, len(idx), 3)])
    W.M.write_ff9mesh(out, dst)
    d2 = W.M.read_ff9mesh(dst)
    assert d2["vcount"] == len(d2["indices"]), "re-pack failed the contract?!"
    assert d2["vcount"] <= 65535, f"vcount {d2['vcount']} exceeds the 16-bit mesh limit"
    s2, _ = soup(dst)
    assert s2 == tris, "re-pack changed the tri soup?!"
    print(f"   {Path(src).name}: {d['vcount']}v/{len(d['indices'])}i -> "
          f"{d2['vcount']}v/{len(d2['indices'])}i CONTRACT-OK, soup identical")


def check(paths):
    for p in paths:
        d = W.M.read_ff9mesh(p)
        v, i = d["vcount"], len(d["indices"])
        state = "OK (unindexed)" if v == i else (
            f"BRICK (v>i: loop overrun by {(v // 3) - i // 3} tris)" if v > i
            else f"LATENT (v<i: TriangleNormals short {v // 3}/{i // 3})")
        print(f"   {Path(p).name:38s} v={v:6d} i={i:6d}  {state}")


def verify(a, b):
    sa, _ = soup(a)
    sb, _ = soup(b)
    assert sa == sb, f"tri soups differ: {len(sa)} vs {len(sb)} tris"
    print(f"   identical tri soups ({len(sa)} tris)")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "check":
        check(sys.argv[2:])
    elif cmd == "repack":
        repack(sys.argv[2], sys.argv[3])
    elif cmd == "verify":
        verify(sys.argv[2], sys.argv[3])
