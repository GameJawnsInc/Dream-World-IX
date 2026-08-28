"""THE FOOT-COURSE GROUND STRIP (owner's mockup, R4 knoll stretch): re-tile the lawn
tris along the wall base (bend-to-bend, s 52-82) with r10 foot-course tiles -- rock edge
at the wall, painted fringe blending into the lawn. UV-only, block (22,7), both discs.

Backs up both Terrain files to the MAIN repo's backups/, writes the uv floats in place,
ledgers each write, verifies byte-parity and that ONLY the intended uv bytes changed."""
import datetime
import json
import math
import shutil
import struct
import sys
from collections import defaultdict
from pathlib import Path

import rechart_lab as L

REPO = Path(r"C:\gd\Dream-World-IX")
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit.world import mesh as M                      # noqa: E402

kk = lambda p: (round(p[0], 3), round(p[1], 3), round(p[2], 3))
BLK = (22, 7)
S0, S1, DEPTH, WIN = 52.0, 82.5, 4.4, 4.6
MAX_EDGE = 7.5

tris = L.load_all()
chain, S = L.foot_chain(tris)


def foot_at(px, pz):
    best, bs, by_ = 1e9, 0, 0
    for i in range(len(chain)):
        dd = (chain[i][0] - px) ** 2 + (chain[i][2] - pz) ** 2
        if dd < best:
            best, bs, by_ = dd, S[i], chain[i][1]
    return math.sqrt(best), bs, by_


# r10 exemplars from the wall's own foot course
e2t = defaultdict(list)
for ti, t in enumerate(tris):
    if t["topo"] != 49:
        continue
    ps = [kk(v) for v in t["w"]]
    for a, b in ((0, 1), (1, 2), (2, 0)):
        e2t[tuple(sorted((ps[a], ps[b])))].append(ti)
ex, seenq = {}, set()
for e, ts in e2t.items():
    if len(ts) != 2 or ts[0] in seenq or ts[1] in seenq:
        continue
    vs4 = {kk(v) for t2 in ts for v in tris[t2]["w"]}
    if len(vs4) != 4:
        continue
    uvm = {}
    for t2 in ts:
        for k in range(3):
            uvm[kk(tris[t2]["w"][k])] = tris[t2]["uv"][k]
    us = [u[0] for u in uvm.values()]
    vs2 = [u[1] for u in uvm.values()]
    du, dv = max(us) - min(us), max(vs2) - min(vs2)
    if not (0.8 * L.TILE_U < du <= L.TILE_U + 1e-4 and 0.8 * L.TILE_V < dv <= L.TILE_V + 1e-4):
        continue
    row = round((min(vs2) - L.PV) / L.TILE_V)
    col = round((min(us) - L.PU) / L.TILE_U)
    if row != 10 or col not in (6, 7, 8, 9) or col in ex:
        continue
    pts4 = sorted(vs4, key=lambda p: p[1])
    ex[col] = dict(u0=min(us), u1=max(us),
                   v_bot=sum(uvm[p][1] for p in pts4[:2]) / 2,
                   v_top=sum(uvm[p][1] for p in pts4[2:]) / 2)
    seenq.update(ts)
cols_avail = sorted(ex)
assert len(cols_avail) == 4, cols_avail

# selection: lawn tris along the foot, slivers and bend-overhangs excluded
edits = {}                                                 # local tri index -> [[u,v]x3]
for t in tris:
    if t["topo"] != 0 or t["blk"] != BLK:
        continue
    ds = [foot_at(v[0], v[2]) for v in t["w"]]
    cd, cs, _ = foot_at(sum(v[0] for v in t["w"]) / 3, sum(v[2] for v in t["w"]) / 3)
    if not (cd <= DEPTH and S0 <= cs <= S1):
        continue
    if sum(1 for d, s, f in ds if d <= DEPTH + 0.6) < 2:
        continue
    if any(s < S0 - 0.5 or s > S1 + 0.5 for d, s, f in ds):
        continue
    emax = max(math.dist(t["w"][a], t["w"][b]) for a, b in ((0, 1), (1, 2), (2, 0)))
    if emax > MAX_EDGE:
        continue
    new = []
    for v in t["w"]:
        d, s, fy = foot_at(v[0], v[2])
        w = int(s / WIN)
        e2 = ex[cols_avail[w % len(cols_avail)]]
        su = max(0.0, min(1.0, (s - w * WIN) / WIN))
        h = max(0.0, min(1.0, d / DEPTH))
        new.append((e2["u0"] + su * (e2["u1"] - e2["u0"]),
                    e2["v_top"] + h * (e2["v_bot"] - e2["v_top"])))
    edits[t["tri"]] = new
print(f"strip tris: {len(edits)}")
assert 10 <= len(edits) <= 20, "selection count out of expected range"

DRY = "--apply" not in sys.argv
G = L.G
paths = {d: G / f"Disc{d}" / "0_1" / f"r{BLK[1]}" / f"Block[{BLK[0]}][{BLK[1]}] Terrain.ff9mesh"
         for d in (1, 4)}
raw = {d: p.read_bytes() for d, p in paths.items()}
assert raw[1] == raw[4], "Disc1/Disc4 not identical -- investigate before writing"

data = raw[1]
_, vcount, _, flags = struct.unpack_from("<iiii", data, 4)
uv_off = 20 + vcount * 12 + (vcount * 12 if flags & 1 else 0)
assert flags & 2

new = bytearray(data)
nbytes = 0
for tri_i, uvs in edits.items():
    for k in range(3):
        o = uv_off + (tri_i * 3 + k) * 8
        struct.pack_into("<ff", new, o, uvs[k][0], uvs[k][1])
        nbytes += 8
diff = sum(1 for a, b in zip(data, new) if a != b)
print(f"uv bytes targeted: {nbytes}; bytes actually differing: {diff}")

if DRY:
    print("DRY RUN (pass --apply to write)")
    sys.exit(0)

stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
bak = REPO / "backups" / "west-seam-continent" / f"footstrip-pre.{stamp}"
for d, p in paths.items():
    dd = bak / f"Disc{d}"
    dd.mkdir(parents=True, exist_ok=True)
    shutil.copy2(p, dd / p.name)
print(f"backup -> {bak}")

for d, p in paths.items():
    p.write_bytes(bytes(new))
    M.record_ledger_write(p, cell=BLK, part="Terrain", write_disc=d)
    print(f"wrote Disc{d} + ledger")

# verify
for d, p in paths.items():
    cur = p.read_bytes()
    assert cur == bytes(new), f"Disc{d} readback mismatch"
    outside = [i for i, (a, b) in enumerate(zip(raw[d], cur)) if a != b
               if not (uv_off <= i < uv_off + vcount * 8)]
    assert not outside, f"bytes changed outside the uv channel: {outside[:5]}"
print("VERIFIED: discs identical, only uv-channel bytes changed")
json.dump({f"{BLK[0]},{BLK[1]},{k}": v for k, v in edits.items()},
          open(Path(__file__).parent / "footstrip_deployed_edits.json", "w"), indent=0)
