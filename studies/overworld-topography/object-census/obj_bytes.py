"""Byte-level verification of stock Object meshes: channels, stride, index format, submeshes, roundtrip."""
import sys, json
from collections import Counter
from pathlib import Path
sys.path.insert(0, r"C:/gd/Dream-World-IX/.claude/worktrees/gui-workspace-improvements-277c74/ff9mapkit")
from ff9mapkit.world import extract as X

blocks = X.list_object_blocks(disc=1)
chset = Counter(); strides = Counter(); subs = Counter(); u32 = Counter(); rt = Counter(); flatok = Counter()
tanw = Counter(); nrmlen = []
for (bx,by) in blocks:
    bm = X.read_block(bx,by,disc=1,part="object")
    chset[tuple(sorted((ci, bm.channels[ci]) for ci in bm.channels))] += 1
    strides[bm.stride] += 1
    subs[(len(bm.submeshes), tuple(bm.submeshes) if len(bm.submeshes)<2 else "multi")] += 1
    u32[bm.use32] += 1
    rt[X.roundtrip_ok(bm)] += 1
    flatok[(bm.vcount == len(bm.flat_index) == 3*len(bm.tris), bm.flat_index == list(range(bm.vcount)))] += 1
    for t in bm.tangents:
        tanw[round(t[3],4)] += 1
    # tangent y,z distribution (are they real tangents or padding?)
print("channel layouts:", {str(k):v for k,v in chset.items()})
print("strides:", dict(strides))
print("submeshes:", {str(k):v for k,v in subs.items()})
print("use32:", dict(u32))
print("roundtrip_ok:", dict(rt))
print("(vcount==icount==3*tri, flat_index is identity):", {str(k):v for k,v in flatok.items()})
print("tangent.w histogram (top):", tanw.most_common(8))

# per-triangle: do all 3 corners share the same IDALL?
same = Counter()
for (bx,by) in blocks:
    bm = X.read_block(bx,by,disc=1,part="object")
    tan = bm.tangents
    for t in bm.tris:
        vals = {int(round(tan[i][0])) for i in t}
        same[len(vals)] += 1
print("corners-per-tri sharing one IDALL (1 == uniform):", dict(same))

# tangent.y/z content
b = X.read_block(22,14,disc=1,part="object")
print("\nsample (22,14) first 6 verts:")
for i in range(6):
    print("  pos", [round(c,3) for c in b.verts[i]], "nrm", [round(c,3) for c in b.normals[i]],
          "uv", [round(c,5) for c in b.uvs[i]], "tan", [round(c,4) for c in b.tangents[i]])
print("  raw vbuf len", len(b.raw_vbuf), "ibuf len", len(b.raw_ibuf), "stride", b.stride, "vcount", b.vcount)
print("  first 48 bytes:", b.raw_vbuf[:48].hex(" "))
print("  first 12 index bytes:", b.raw_ibuf[:12].hex(" "))
