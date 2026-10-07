"""STEP 5b -- END-TO-END proof of THE PARTIAL-MIRROR CRACK the current per-cell gate creates on disc 4.

A world-terrain raise whose radius spans a gate-ELIGIBLE cell A and a gate-REFUSED cell B: terrain.reshape writes
both Disc1 overrides; discmirror.mirror (the auto_mirror post-step) copies A to Disc4 and SKIPs B. On disc 4, A's
border verts are raised while B shows stock disc-4 -> a step at the shared border.

Everything runs through the SHIPPED code (terrain.reshape, discmirror.mirror -- real copies) into a SCRATCH mod
folder outside the repo and the install. Measured: the Y step between coincident border vertices of the two
cells' effective disc-4 meshes (A = mirrored override, B = stock disc 4), with two controls that must read 0:
  C1 the same border on DISC 1 (both cells carry the deployed edit);
  C2 strategy (ii): terrain.reshape(disc=4) into a second scratch folder -> both disc-4 cells replayed.
Writes out/s5b_crack_demo.json.
Run (from C:\\gd\\Dream-World-IX\\ff9mapkit):  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_disc4_edit_reach/s5b_crack_demo.py
"""
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib as L                                       # noqa: E402
from ff9mapkit.world import discmirror as DM         # noqa: E402
from ff9mapkit.world import mesh as M                # noqa: E402
from ff9mapkit.world import terrain as TER           # noqa: E402

G = L.GAME
objs = L.mesh_objects()
rows = {tuple(map(int, k.split(","))): r for k, r in json.loads((L.OUT / "s1_gate.json").read_text(encoding="utf-8"))["rows"].items()}
elig = {c for c, r in rows.items() if r["land"] and r["shipped"].startswith("PASS")}
refd = {c for c, r in rows.items() if r["land"] and r["shipped"].startswith("SKIP")}


def border(bm_or_path, cell, side, disc):
    bm = M.blockmesh_from_ff9mesh(bm_or_path, disc=disc, x=cell[0], y=cell[1]) if isinstance(bm_or_path, Path) else bm_or_path
    out = {}
    for v in bm.verts:
        if side == "E" and abs(v[0] - 64) < 1e-3:
            out[(round(64 * cell[0] + 64, 3), round(v[2] - 64 * cell[1], 3))] = v[1]
        if side == "W" and abs(v[0]) < 1e-3:
            out[(round(64 * cell[0], 3), round(v[2] - 64 * cell[1], 3))] = v[1]
    return out


def step(a, b):
    common = set(a) & set(b)
    return (max(abs(a[k] - b[k]) for k in common) if common else None), len(common)


found = None
for A in sorted(elig):
    B = (A[0] + 1, A[1])                                 # A's EAST neighbour
    if B not in refd:
        continue
    for zz in (16, 24, 32, 40, 48):
        at = (64 * B[0], -(64 * A[1] + zz))             # on the shared border
        try:
            s = TER.reshape(str(L.CACHE_DIR / "crack_dry"), radius=16, at=at, amount=4.0, disc=1, game=G, dry_run=True)
        except ValueError:
            continue
        cells = {tuple(b["block"]) for b in s["blocks"]}
        if cells == {A, B}:
            found = (A, B, at)
            break
    if found:
        break
assert found, "no eligible|refused border edit found"
A, B, at = found
print("demo edit: raise +4 r16 at", at, "spanning eligible", A, "and refused", B)
scratch = L.CACHE_DIR / "crack"
if scratch.exists():
    shutil.rmtree(scratch)
S, R = scratch / "shipped", scratch / "replay"
TER.reshape(str(S), radius=16, at=at, amount=4.0, disc=1, game=G, skip_mirror=True)
log = []
mr = DM.mirror(str(S), src_disc=1, dst_disc=4, lod="0_1", game=G, cells={A, B}, log=log.append)
print("mirror log:", log)
TER.reshape(str(R), radius=16, at=at, amount=4.0, disc=4, game=G, skip_mirror=True)
rel = lambda d, c: M.override_relpath(d, c[0], c[1], "0_1", "Terrain")
d4A = S / rel(4, A)
assert d4A.is_file() and not (S / rel(4, B)).exists(), "expected A mirrored, B skipped"
stockB4 = L.decode(objs[(4, "0_1", B[0], B[1], "terrain")], 4, B[0], B[1])
st_crack, n_crack = step(border(d4A, A, "E", 4), border(stockB4, B, "W", 4))
st_c1, n_c1 = step(border(S / rel(1, A), A, "E", 1), border(S / rel(1, B), B, "W", 1))
st_c2, n_c2 = step(border(R / rel(4, A), A, "E", 4), border(R / rel(4, B), B, "W", 4))
stockA4 = L.decode(objs[(4, "0_1", A[0], A[1], "terrain")], 4, A[0], A[1])
st_stock, n_stock = step(border(stockA4, A, "E", 4), border(stockB4, B, "W", 4))
res = {"edit": {"at": list(at), "radius": 16, "amount": 4.0, "A_eligible": list(A), "B_refused": list(B)},
       "mirror_log": log,
       "disc4_shipped_step_max": st_crack, "coincident_border_verts": n_crack,
       "control_stock_disc4_step": st_stock, "control_C1_disc1_step": st_c1, "control_C2_replay_disc4_step": st_c2}
print(json.dumps(res, indent=1))
assert st_stock == 0 and st_c1 == 0 and st_c2 == 0, "controls must weld exactly"
assert st_crack and st_crack > 0.1, "the shipped path must show the crack"
(L.OUT / "s5b_crack_demo.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
