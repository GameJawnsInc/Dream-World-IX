"""CALIBRATE the lane's instruments on KNOWN cases before judging disc 4 with them.

Part A (synthetic, no census needed): take a real disc-1 terrain block, apply a known edit, and
assert d4lib.compare / raw_sig / ground_grid report EXACTLY that edit -- each check can fail.
  A0 self vs self                  -> raw identical
  A1 one tri lifted +1.5 in Y      -> SAME_TOPO pos=3 verts, 1 re-heighted tri, dy=+1.5
  A2 one tri's IDALL re-typed      -> tan.x changed, 1 shared id change, the exact topo transition
  A3 one vertex UV nudged          -> uv=1, 1 shared uv change, no geometry change
  A4 triangle order reversed       -> index differs, but 0 only/rh/attr  (=> REORDERED, not RETOPO)
  A5 one tri deleted + one moved in XZ -> only1 = 2, only4 = 1
  A6 whole block lifted +1 (ground_grid) -> every grounded sample dy == +1, same topograph
  A7 frame check: local verts of the calibration block lie in x[0,64], z[-64,0]
Part B (known cases, needs out/census.json): the project memory records that the Daguerreo donors
  (5,15)/(5,16)/(6,16)/(6,15)/(7,16) differ across discs and (9,17) differs in object+terrain
  (project-ff9-overworld-worlds.md, THE TWO-TREE LAW). The census must re-find every one of them.

Run:  py C:/gd/Dream-World-IX/studies/terrain-malleability/disc4/calibrate.py
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4lib as L                                    # noqa: E402
from d4lib import X                                  # noqa: E402

fails = []


def check(cond, msg):
    print(("  PASS " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


print("PART A -- synthetic edits on a real disc-1 block")
blocks = X.list_blocks(disc=1)
cal = None
for b in blocks:
    bm = X.read_block(*b, disc=1)
    if len(bm.tris) > 600:
        cal = bm
        break
print(f"  calibration block {cal.x, cal.y}: {len(cal.tris)} tris, vcount {cal.vcount}, "
      f"unindexed={cal.vcount == len(cal.flat_index)}")

objs = L.mesh_objects()
o = objs[(1, "0_1", cal.x, cal.y, "terrain")]
check(L.sig_identical(L.raw_sig(o), L.raw_sig(o)), "A0 raw_sig(self) == raw_sig(self)")
other = next(b for b in blocks if b != (cal.x, cal.y))
check(not L.sig_identical(L.raw_sig(o), L.raw_sig(objs[(1, "0_1", other[0], other[1], "terrain")])),
      f"A0' raw_sig differs for a different block {other}")
c = L.compare(cal, X._copy_blockmesh(cal))
check(c["same_topology"] and not any(c["chan_diff"].values()) and c["tri_shared_exact"] == len(cal.tris),
      "A0'' compare(copy) -> no change at all")

# A1 lift one triangle (pick a tri whose 3 verts are used by no other tri)
use = {}
for t, tri in enumerate(cal.tris):
    for k in tri:
        use[k] = use.get(k, 0) + 1
t1 = next(t for t, tri in enumerate(cal.tris) if all(use[k] == 1 for k in tri))
m = X._copy_blockmesh(cal)
for k in m.tris[t1]:
    m.chan_arrays[X.CH_POS][k][1] += 1.5
c = L.compare(cal, m)
check(c["same_topology"] and c["chan_diff"].get("pos") == 3 and c["tri_reheighted"] == 1
      and c["tri_only1"] == 0 and c["tri_only4"] == 0 and c["reheight_dy"]["min"] == 1.5
      and c["reheight_dy"]["max"] == 1.5, f"A1 lift tri {t1} +1.5 -> pos=3, rh=1, dy=1.5  ({c['chan_diff']}, rh {c['tri_reheighted']})")

# A2 retype one tri's IDALL (all 3 corners) to topograph 63
m = X._copy_blockmesh(cal)
old = int(round(m.tangents[m.tris[t1][0]][0]))
d = X.decode_id(old)
new = X.encode_id(d["event"], d["area"], 63 if d["topograph"] != 63 else 62, d["flags"])
for k in m.tris[t1]:
    m.chan_arrays[X.CH_TAN][k][0] = float(new)
c = L.compare(cal, m)
check(c["chan_diff"].get("tan.x") == 3 and c["shared_id_changed"] == 1 and c["tri_reheighted"] == 0
      and c["id_transitions"][0][2] == d["topograph"] and c["id_transitions"][0][5] == X.decode_id(new)["topograph"],
      f"A2 retype tri {t1}: topo {d['topograph']} -> {X.decode_id(new)['topograph']}  ({c['id_transitions']})")

# A3 nudge one uv
m = X._copy_blockmesh(cal)
m.chan_arrays[X.CH_UV][m.tris[t1][0]][0] += 0.01
c = L.compare(cal, m)
check(c["chan_diff"].get("uv") == 1 and c["shared_uv_changed"] == 1 and c["tri_reheighted"] == 0
      and c["chan_diff"].get("pos") == 0, f"A3 uv nudge -> uv=1, shared_uv_changed=1 ({c['chan_diff']})")

# A3b nudge one vertex normal (re-lit, same geometry)
m = X._copy_blockmesh(cal)
m.chan_arrays[X.CH_NRM][m.tris[t1][0]][1] += 0.05
c = L.compare(cal, m)
check(c["shared_nrm_changed"] == 1 and c["shared_uv_changed"] == 0 and c["tri_reheighted"] == 0
      and c["tri_only1"] == 0, f"A3b normal nudge -> shared_nrm_changed=1 ({c['chan_diff']})")

# A4 reverse triangle order
m = X._copy_blockmesh(cal)
m.tris = list(reversed(m.tris))
m.flat_index = [k for tri in m.tris for k in tri]
c = L.compare(cal, m)
check((not c["same_topology"]) and c["tri_only1"] == 0 and c["tri_only4"] == 0 and c["tri_reheighted"] == 0
      and c["shared_id_changed"] == 0 and c["shared_uv_changed"] == 0 and c["tri_reordered_in_shared"] > 0,
      f"A4 reversed order -> REORDERED (reordered {c['tri_reordered_in_shared']})")

# A4b the REAL unindexed form of a shuffle: identity index, vertex DATA re-ordered tri-by-tri
m = X._copy_blockmesh(cal)
order = [k for tri in reversed(cal.tris) for k in tri]
for ci in m.chan_arrays:
    m.chan_arrays[ci] = [cal.chan_arrays[ci][k][:] for k in order]
c = L.compare(cal, m)
check(c["chan_diff"].get("pos", 0) > 0 and c["tri_only1"] == 0 and c["tri_only4"] == 0
      and c["tri_reheighted"] == 0 and c["shared_id_changed"] == 0 and c["shared_uv_changed"] == 0
      and c["shared_nrm_changed"] == 0,
      f"A4b vertex-data shuffle -> channels 'differ' ({c['chan_diff']}) yet geometric match is perfect")

# A5 delete one tri, move one vertex of another tri in XZ
m = X._copy_blockmesh(cal)
t2 = next(t for t, tri in enumerate(cal.tris) if t != t1 and all(use[k] == 1 for k in tri))
m.chan_arrays[X.CH_POS][m.tris[t2][0]][0] += 0.37
m.tris = [tri for t, tri in enumerate(m.tris) if t != t1]
m.flat_index = [k for tri in m.tris for k in tri]
c = L.compare(cal, m)
check(c["tri_only1"] == 2 and c["tri_only4"] == 1 and c["tri_reheighted"] == 0,
      f"A5 delete+xz-move -> only1=2 only4=1 (got only1={c['tri_only1']} only4={c['tri_only4']} rh={c['tri_reheighted']})")

# A6 ground_grid on a +1 whole-block lift
m = X._copy_blockmesh(cal)
for v in m.chan_arrays[X.CH_POS]:
    v[1] += 1.0
g1 = L.ground_grid([("Terrain", cal)], pitch=2.0)
g4 = L.ground_grid([("Terrain", m)], pitch=2.0)
grounded = [k for k in g1 if g1[k][1] != "MISS"]
dys = [g4[k][0] - g1[k][0] for k in grounded]
check(len(grounded) > 0 and all(abs(dy - 1.0) < 1e-5 for dy in dys)
      and all(g1[k][3] == g4[k][3] for k in grounded),
      f"A6 ground_grid +1 lift: {len(grounded)}/{len(g1)} grounded, dy all 1.0, topo unchanged")

# A7 local frame
xs = [v[0] for v in cal.verts]; zs = [v[2] for v in cal.verts]
check(min(xs) >= -1e-3 and max(xs) <= 64 + 1e-3 and min(zs) >= -64 - 1e-3 and max(zs) <= 1e-3,
      f"A7 local frame x[{min(xs):.2f},{max(xs):.2f}] z[{min(zs):.2f},{max(zs):.2f}]")

print("\nPART B -- known cross-disc differences from project memory must be re-found")
cj = Path(__file__).resolve().parent / "out" / "census.json"
if not cj.is_file():
    print("  (out/census.json absent -- run census.py, then re-run this)")
    fails.append("PART B not run")
else:
    rows = json.loads(cj.read_text(encoding="utf-8"))
    ch = {(r["x"], r["y"]) for r in rows if r["lod"] == "0_1" and r["cls"] != "IDENTICAL"}
    for b in [(5, 15), (5, 16), (6, 16), (6, 15), (7, 16), (9, 17)]:
        parts = sorted(r["part"] for r in rows if r["lod"] == "0_1" and (r["x"], r["y"]) == b and r["cls"] != "IDENTICAL")
        check(b in ch, f"B {b} found changed: {parts}")
    p917 = {r["part"] for r in rows if r["lod"] == "0_1" and (r["x"], r["y"]) == (9, 17) and r["cls"] != "IDENTICAL"}
    check({"object", "terrain"} <= p917, f"B (9,17) differs in object+terrain (got {sorted(p917)})")

print(f"\n{'ALL CALIBRATION CHECKS PASS' if not fails else 'FAILURES: ' + repr(fails)}")
sys.exit(1 if fails else 0)
