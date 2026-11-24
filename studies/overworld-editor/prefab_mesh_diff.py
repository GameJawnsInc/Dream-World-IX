"""PREFAB FEASIBILITY probe 3: what differs between two Terrain meshes (A at its block, B at the shifted block).

usage: py studies/overworld-editor/prefab_mesh_diff.py A.ff9mesh B.ff9mesh
Compares the triangle MULTISET (vertex order ignored): position + uv + tangent exactly, normals to 1e-9 (the engine
binds no normal for WorldMap Terrain, so normal float noise is not a look difference)."""
import collections
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit.world import mesh as M  # noqa: E402


def tris(m, normals):
    V, U, T, N, I = m["verts"], m["uvs"], m["tangents"], m["normals"], m["indices"]
    def key(i):
        k = tuple(V[i]) + tuple(U[i]) + tuple(T[i])
        return k + (tuple(round(c, 9) for c in N[i]) if normals else ())
    return collections.Counter(tuple(sorted(key(i) for i in I[k:k + 3])) for k in range(0, len(I), 3))


A, B = M.read_ff9mesh(sys.argv[1]), M.read_ff9mesh(sys.argv[2])
for normals in (False, True):
    ta, tb = tris(A, normals), tris(B, normals)
    print(f"{'with' if normals else 'without'} normals: tris {sum(ta.values())}/{sum(tb.values())}  "
          f"A-only {sum((ta - tb).values())}  B-only {sum((tb - ta).values())}")
