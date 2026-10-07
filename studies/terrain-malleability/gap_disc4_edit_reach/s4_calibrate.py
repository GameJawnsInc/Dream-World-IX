"""STEP 4 -- calibrate strategies (ii) REPLAY and (iii) DELTA before any verdict.

  K1 IDENTITY on all 71 gate-eligible land cells: byte mirror (ff9mesh_bytes(S1)), replay (identity(S4)) and
     delta (delta_transfer(S1, S1, S4)) must be byte-identical .ff9mesh payloads.
  K2 REAL RAISE (+2u, r=16 at the cell centre, so it touches only that cell) on all 71: byte mirror
     (ff9mesh_bytes(deform(S1))), replay (deform(S4)) and delta (delta_transfer(S1, deform(S1), S4), ring 1)
     must be byte-identical.
  K3 END-TO-END on 3 eligible cells through the SHIPPED code paths into SCRATCH mod folders (outside the repo
     and the install): terrain.reshape(disc=1) -> discmirror.mirror (real copy, scratch tree) vs
     terrain.reshape(disc=4) into a second scratch tree vs delta from the deployed Disc1 file. Bytes must agree.
     Also world-retarget's library call (mesh.retarget_tiles) the same way (direct).
  K4 REFUSAL: a raise r=8 on the Iifa re-cut (11,4) and on a D4-08 ridge (disc4/out/rock_ribbons.json[0]) must be
     REFUSED by delta (ring 0 and ring 1); replay still produces a mesh there (it is a hazard, not a failure).
  K5 DELTA == REPLAY on REFUSED cells where the edit misses the footprint: for a deterministic sample of
     single-cell raises on gate-refused cells, whenever delta (ring 0) is lawful its bytes must equal replay's.
Writes out/s4_calibrate.json.
Run (from C:\\gd\\Dream-World-IX\\ff9mapkit):  py C:/gd/Dream-World-IX/studies/terrain-malleability/gap_disc4_edit_reach/s4_calibrate.py
"""
import copy
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
s1 = json.loads((L.OUT / "s1_gate.json").read_text(encoding="utf-8"))
rows = s1["rows"]
eligible = sorted(tuple(map(int, k.split(","))) for k, r in rows.items() if r["land"] and r["shipped"].startswith("PASS"))
refused = sorted(tuple(map(int, k.split(","))) for k, r in rows.items() if r["land"] and r["shipped"].startswith("SKIP"))
print(f"eligible land cells {len(eligible)}, refused {len(refused)}")
assert len(eligible) == 71 and len(refused) == 189


def ter(d, x, y):
    return L.decode(objs[(d, "0_1", x, y, "terrain")], d, x, y)


def raise_(bm, x, y, amount=2.0, radius=16.0, at=None):
    e = copy.deepcopy(bm)
    wo = (64 * x, -64 * y)
    at = at or (64 * x + 32, -(64 * y + 32))
    n = M.deform_radial(e, amount=amount, radius=radius, center=at, world_origin=wo)
    return e, n


res = {"K1": 0, "K2": 0, "K2_moved_cells": 0}
for (x, y) in eligible:
    S1, S4 = ter(1, x, y), ter(4, x, y)
    ok, why, D, _ = L.delta_transfer(S1, copy.deepcopy(S1), S4)
    b = {M.ff9mesh_bytes(S1), M.ff9mesh_bytes(S4), M.ff9mesh_bytes(D)}
    assert ok and len(b) == 1, f"K1 failed at {(x, y)}"
    res["K1"] += 1
    E1, n1 = raise_(S1, x, y)
    R4, n4 = raise_(S4, x, y)
    okd, why, D, st = L.delta_transfer(S1, E1, S4, ring=1)
    assert okd, f"K2 delta refused an eligible cell {(x, y)}: {why}"
    b = {M.ff9mesh_bytes(E1), M.ff9mesh_bytes(R4), M.ff9mesh_bytes(D)}
    assert len(b) == 1, f"K2 bytes differ at {(x, y)}"
    res["K2"] += 1
    res["K2_moved_cells"] += n1 > 0
print("K1 identity byte-identical:", res["K1"], "/ 71;  K2 raise byte-identical:", res["K2"], "/ 71 (", res["K2_moved_cells"], "actually moved )")

# ---- K3 end-to-end through the shipped code paths, scratch trees only
k3 = []
scratch = L.CACHE_DIR / "k3"
if scratch.exists():
    shutil.rmtree(scratch)
done = 0
for (x, y) in eligible:
    if done == 3:
        break
    A, B = scratch / f"A_{x}_{y}", scratch / f"B_{x}_{y}"
    at = (64 * x + 32, -(64 * y + 32))
    try:
        sa = TER.reshape(str(A), radius=16, at=at, amount=2.0, disc=1, game=G, skip_mirror=True)
    except ValueError as e:                     # the operator's own one-way-wall gate refused it on disc 1
        k3.append({"cell": [x, y], "skipped": f"disc-1 gate: {str(e)[:60]}"})
        continue
    if not sa["blocks"]:
        k3.append({"cell": [x, y], "skipped": "nothing moved"})
        continue
    sb = TER.reshape(str(B), radius=16, at=at, amount=2.0, disc=4, game=G, skip_mirror=True)
    done += 1
    mr = DM.mirror(str(A), src_disc=1, dst_disc=4, lod="0_1", game=G, cells={(x, y)}, log=lambda *_: None)
    rel4 = M.override_relpath(4, x, y, "0_1", "Terrain")
    rel1 = M.override_relpath(1, x, y, "0_1", "Terrain")
    mirrored = (A / rel4).read_bytes()
    replayed = (B / rel4).read_bytes()
    E1 = M.blockmesh_from_ff9mesh(A / rel1, disc=1, x=x, y=y)
    ok, why, D, _ = L.delta_transfer(ter(1, x, y), E1, ter(4, x, y), ring=1)
    same = ok and mirrored == replayed == M.ff9mesh_bytes(D)
    k3.append({"cell": [x, y], "blocks_written_d1": [b["block"] for b in sa["blocks"]],
               "blocks_written_d4": [b["block"] for b in sb["blocks"]], "mirror_skipped": mr["skipped"],
               "mirror_eq_replay_eq_delta": same})
    assert same, f"K3 end-to-end mismatch at {(x, y)}"
    # retarget (library call of world-retarget), direct
    S1, S4 = ter(1, x, y), ter(4, x, y)
    e1, r4 = copy.deepcopy(S1), copy.deepcopy(S4)
    n1 = M.retarget_tiles(e1, topograph=59, center=at, radius=12, world_origin=(64 * x, -64 * y))
    n4 = M.retarget_tiles(r4, topograph=59, center=at, radius=12, world_origin=(64 * x, -64 * y))
    ok, why, D, _ = L.delta_transfer(S1, e1, S4, ring=1)
    assert n1 == n4 and ok and M.ff9mesh_bytes(e1) == M.ff9mesh_bytes(r4) == M.ff9mesh_bytes(D), "K3 retarget"
    k3[-1]["retarget_tris"] = n1
print("K3 end-to-end:", k3)
assert done == 3, "K3 needs 3 end-to-end cells"

# ---- K4 refusal on re-cut / ridge
rib = json.loads((L.D4OUT / "rock_ribbons.json").read_text(encoding="utf-8"))[0]
k4 = []
for name, (x, y), at in (("iifa", (11, 4), (11 * 64 + 32, -(4 * 64 + 32))),
                         ("ridge", tuple(rib["block"]), tuple(rib["centroid_world"]))):
    S1, S4 = ter(1, x, y), ter(4, x, y)
    E1, n1 = raise_(S1, x, y, amount=2.0, radius=8.0, at=at)
    R4, n4 = raise_(S4, x, y, amount=2.0, radius=8.0, at=at)
    r0 = L.delta_transfer(S1, E1, S4, ring=0)
    r1_ = L.delta_transfer(S1, E1, S4, ring=1)
    k4.append({"site": name, "cell": [x, y], "at": list(at), "moved_d1": n1, "moved_d4": n4,
               "delta_ring0": [r0[0], r0[1]], "delta_ring1": [r1_[0], r1_[1]]})
    assert not r0[0] and not r1_[0], f"K4: delta must refuse {name}"
    assert n4 > 0, "replay must still move disc-4 verts there"
print("K4 refusals:", k4)

# ---- K5 delta(ring 0) lawful => bytes == replay, on refused cells
k5 = {"edits": 0, "delta_lawful": 0, "equal": 0, "ring1_lawful": 0,
      "vertex_only_lawful": 0, "vertex_only_equal": 0, "vertex_only_wrong": []}
for (x, y) in refused[::3]:
    S1, S4 = ter(1, x, y), ter(4, x, y)
    for i in range(1, 4):
        for j in range(1, 4):
            at = (64 * x + 16 * i, -(64 * y + 16 * j))
            E1, n1 = raise_(S1, x, y, amount=2.0, radius=8.0, at=at)
            if n1 == 0:
                continue
            R4, _ = raise_(S4, x, y, amount=2.0, radius=8.0, at=at)
            k5["edits"] += 1
            # vertex-sharing closure only (no geometric support): the instrument that K5 first caught out
            okv, _, Dv, _ = L.delta_transfer(S1, E1, S4, ring=0)
            if okv:
                k5["vertex_only_lawful"] += 1
                eq = M.ff9mesh_bytes(Dv) == M.ff9mesh_bytes(R4)
                k5["vertex_only_equal"] += eq
                if not eq:
                    k5["vertex_only_wrong"].append({"cell": [x, y], "at": list(at)})
            sup = (at[0] - 64 * x, at[1] + 64 * y, 8.0)
            ok, why, D, _ = L.delta_transfer(S1, E1, S4, ring=0, support=sup)
            if ok:
                k5["delta_lawful"] += 1
                k5["equal"] += M.ff9mesh_bytes(D) == M.ff9mesh_bytes(R4)
            k5["ring1_lawful"] += L.delta_transfer(S1, E1, S4, ring=1, support=sup)[0]
print("K5:", k5)
assert k5["equal"] == k5["delta_lawful"], "K5: a lawful ring-0 delta must equal replay byte-for-byte"
(L.OUT / "s4_calibrate.json").write_text(json.dumps({"counts": res, "K3": k3, "K4": k4, "K5": k5}, indent=1, default=str),
                                         encoding="utf-8")
print("ALL CALIBRATIONS PASS")
