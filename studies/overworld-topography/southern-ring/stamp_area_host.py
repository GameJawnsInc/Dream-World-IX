"""THE HOST-AREA STAMP -- terrain study defects 15-17 on the live Southern Ring (REVERT.md section 32).

    py studies/overworld-topography/southern-ring/stamp_area_host.py            # dry run: report, write nothing
    py studies/overworld-topography/southern-ring/stamp_area_host.py --apply    # back up, then write both discs

The R4b safe-road stamp (REVERT section 26.2) set open Terrain ground to area 14 but skipped event tiles and every
non-Terrain part. Three things kept the wrong area (studies/terrain-malleability/gap_area_layer/NOTES.md C and E):

  T15  (19,18) Terrain: 45 carried stock Cleyra entrance tris, area 12 -> camera lock, spawn weather, zone-5 battles,
       "Vube Desert" labels (in-game proven, terrain study ingame/RESULTS.md section 1). Inert as an entrance.
  T16  the six quay trigger clusters (Ashvale, Eastbay, Tidefall, Larkspur, Grimhorn, Lamplight): area 0 -> zone 0,
       so the topograph-0 triggers can roll battles inside the safe road. Their cases 65-68 and the ferry dispatch
       through dispatcher cell tags, NOT tile area (world-locate CELL-TAG JOIN), so the area is free to fix.
  T17  Sandreach Beach1 (12,18)/(12,19): donor area 49 -> a beach-search arm and the "Palmnell Island" label.

Each target takes its block's HOST area: the dominant area of the block's own open Terrain ground (event 0, not the
36-38 canopy, not a walk-skip id). That is rule R2/R10 of the study's area policy. Only the six area bits of
tangent.x change (bits 8-13); event, topograph, flags, geometry, UVs and normals are byte-preserved. The script
refuses to write unless every host area is 14 and every target count matches the study's audit, and it verifies
after writing that nothing else in any file moved and Disc1 == Disc4.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / "ff9mapkit"))
from ff9mapkit.world import extract as X, mesh as M   # noqa: E402

GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
MOD = "FF9CustomMap-world"
SKIP_IDS = {4078, 4088, 2040}                 # engine walk-skip ids: their "area" is a decode artifact (AL7)
CANOPY = {36, 37, 38}                         # the canopy keeps area 0 by design (REVERT 26.2)
HOST_EXPECTED = 14                            # the safe road: zone 6, a record hole for every ground topograph (+ s60)
QUAYS = {"ashvale": (0, 18), "eastbay": (1, 6), "tidefall": (6, 19), "larkspur": (10, 9),
         "grimhorn": (18, 18), "lamplight": (22, 18)}
SANDREACH_BEACH = [(12, 18), (12, 19)]
CLEYRA_BLOCK, CLEYRA_TRIS = (19, 18), 45      # gap_area_layer lead_1918: 45 tris of IDALL 19620 per disc


def path_of(d, x, y, part):
    return GAME / MOD / M.override_relpath(d, x, y, "0_1", part)


def tri_ids(bm):
    """[(tri index, idall)] from each tri's first vertex, asserting all three agree."""
    tan = bm.tangents
    out = []
    for k, t in enumerate(bm.tris):
        ids = {int(round(tan[i][0])) for i in t}
        if len(ids) != 1:
            raise SystemExit(f"{bm.name}: tri {k} carries mixed IDALLs {ids} -- refusing to guess")
        out.append((k, ids.pop()))
    return out


def host_area(bm):
    c = collections.Counter()
    for _k, idall in tri_ids(bm):
        if idall in SKIP_IDS:
            continue
        d = X.decode_id(idall)
        if d["event"] == 0 and d["topograph"] not in CANOPY:
            c[d["area"]] += 1
    return c.most_common(1)[0][0] if c else None, dict(c)


def with_area(idall, area):
    return (idall & ~(0x3F << 8)) | ((area & 0x3F) << 8)


def plan_disc(d):
    """{(x, y, part): {"tris": [k...], "from": {area: n}, "to": area}} for one disc, plus the host areas."""
    plan, hosts = {}, {}

    def load(x, y, part):
        p = path_of(d, x, y, part)
        if not p.exists():
            raise SystemExit(f"missing live file {p}")
        return M.blockmesh_from_ff9mesh(p, disc=d, x=x, y=y, part=part.lower())

    def host_of(x, y):
        if (x, y) not in hosts:
            hosts[(x, y)] = host_area(load(x, y, "Terrain"))
        return hosts[(x, y)][0]

    # T15 -- area 12 anywhere in the live tree must be exactly the Cleyra set
    twelve = collections.Counter()
    for f in (GAME / MOD / f"FF9_Data/WorldMap/Disc{d}/0_1").rglob("*.ff9mesh"):
        name = f.stem                                          # "Block[x][y] Part"
        x, y = _xy(name)
        part = name.split("] ", 1)[1]
        bm = M.blockmesh_from_ff9mesh(f, disc=d, x=x, y=y, part=part.lower())
        for k, idall in tri_ids(bm):
            if idall not in SKIP_IDS and X.decode_id(idall)["area"] == 12:
                twelve[(x, y, part)] += 1
                plan.setdefault((x, y, part), {"tris": [], "why": "T15"})["tris"].append(k)
    if dict(twelve) != {(*CLEYRA_BLOCK, "Terrain"): CLEYRA_TRIS}:
        raise SystemExit(f"disc {d}: area-12 tris are {dict(twelve)}, expected only {CLEYRA_TRIS} at {CLEYRA_BLOCK}")

    # T16 -- quay triggers: event tiles whose area is not the host's
    for site, (x, y) in QUAYS.items():
        bm = load(x, y, "Terrain")
        host = host_of(x, y)
        ev = [(k, i) for k, i in tri_ids(bm) if i not in SKIP_IDS and X.decode_id(i)["event"] != 0]
        off = [k for k, i in ev if X.decode_id(i)["area"] != host]
        if not off:
            raise SystemExit(f"disc {d} {site} {(x, y)}: no off-host event tris (expected the trigger)")
        if len(off) != len(ev):
            raise SystemExit(f"disc {d} {site}: only {len(off)}/{len(ev)} event tris are off-host -- not one cluster")
        plan.setdefault((x, y, "Terrain"), {"tris": [], "why": f"T16 {site}"})["tris"].extend(off)

    # T17 -- Sandreach Beach1 donor area
    for (x, y) in SANDREACH_BEACH:
        bm = load(x, y, "Beach1")
        host = host_of(x, y)
        off = [k for k, i in tri_ids(bm) if i not in SKIP_IDS and X.decode_id(i)["area"] == 49]
        if not off:
            raise SystemExit(f"disc {d} Beach1 {(x, y)}: no area-49 tris")
        plan.setdefault((x, y, "Beach1"), {"tris": [], "why": "T17 sandreach"})["tris"].extend(off)

    for (x, y, part), row in plan.items():
        h = host_of(x, y)
        if h != HOST_EXPECTED:
            raise SystemExit(f"disc {d} {(x, y)}: host area {h} {hosts[(x, y)][1]}, expected {HOST_EXPECTED}")
        row["to"] = h
        bm = load(x, y, part)
        ids = dict(tri_ids(bm))
        row["from"] = dict(collections.Counter(X.decode_id(ids[k])["area"] for k in row["tris"]))
        row["n"] = len(row["tris"])
    return plan, {k: v[1] for k, v in hosts.items()}


def _xy(stem):
    a, b = stem.split("] ", 1)[0][len("Block["):].split("][")
    return int(a), int(b)


def stamped(bm, tris, area):
    tan = bm.tangents
    for k in tris:
        for i in bm.tris[k]:
            tan[i][0] = float(with_area(int(round(tan[i][0])), area))
    return bm


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    plans = {d: plan_disc(d) for d in (1, 4)}
    report = {"discs": {}}
    for d, (plan, hosts) in plans.items():
        print(f"== Disc{d}")
        for (x, y, part), row in sorted(plan.items()):
            print(f"  Block[{x}][{y}] {part:8} {row['why']:16} {row['n']:3} tris  area {row['from']} -> {row['to']}")
        report["discs"][d] = {f"{x},{y} {p}": dict(r) for (x, y, p), r in plan.items()}
    p1 = {k: (v["n"], v["to"]) for k, v in plans[1][0].items()}
    p4 = {k: (v["n"], v["to"]) for k, v in plans[4][0].items()}
    if p1 != p4:
        raise SystemExit(f"Disc1 and Disc4 plans differ: {p1} vs {p4}")
    if not a.apply:
        print("dry run: nothing written (pass --apply)")
        return 0

    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    bdir = REPO / "backups" / f"southern-ring-area-host.{stamp}"
    before = {}
    for d, (plan, _h) in plans.items():
        for (x, y, part) in plan:
            src = path_of(d, x, y, part)
            dst = bdir / src.relative_to(GAME / MOD)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            before[(d, x, y, part)] = src.read_bytes()
    print(f"backed up {len(before)} files to {bdir}")
    for d, (plan, _h) in plans.items():
        for (x, y, part), row in plan.items():
            bm = stamped(M.blockmesh_from_ff9mesh(path_of(d, x, y, part), disc=d, x=x, y=y, part=part.lower()),
                         row["tris"], row["to"])
            M.deploy_override(bm, mod_folder=MOD, disc=d, part=part, force_overwrite=True)
    # verify: only the targeted tangent.x floats changed; every targeted tri reads the new area; Disc1 == Disc4
    for (d, x, y, part), old in before.items():
        new = path_of(d, x, y, part).read_bytes()
        _v, vc, _ic, fl = M.read_ff9mesh_header(old)
        toff = 20 + vc * 12 + (vc * 12 if fl & 1 else 0) + (vc * 8 if fl & 2 else 0)
        allowed = set()
        row = plans[d][0][(x, y, part)]
        bm = M.blockmesh_from_ff9mesh(path_of(d, x, y, part), disc=d, x=x, y=y, part=part.lower())
        for k in row["tris"]:
            for i in bm.tris[k]:
                allowed.update(range(toff + i * 16, toff + i * 16 + 4))
        diff = [j for j in range(len(old)) if old[j] != new[j]]
        if len(old) != len(new) or any(j not in allowed for j in diff):
            raise SystemExit(f"Disc{d} Block[{x}][{y}] {part}: bytes outside the targeted tangent.x floats changed")
        ids = dict(tri_ids(bm))
        bad = [k for k in row["tris"] if X.decode_id(ids[k])["area"] != row["to"]]
        if bad:
            raise SystemExit(f"Disc{d} Block[{x}][{y}] {part}: {len(bad)} targeted tris did not land")
    for (x, y, part) in plans[1][0]:
        if path_of(1, x, y, part).read_bytes() != path_of(4, x, y, part).read_bytes():
            raise SystemExit(f"Block[{x}][{y}] {part}: Disc1 != Disc4 after the stamp")
    report["backup"] = str(bdir)
    report["after_sha256"] = {f"Disc{d} {x},{y} {p}": hashlib.sha256(path_of(d, x, y, p).read_bytes()).hexdigest()
                              for (d, x, y, p) in before}
    (HERE / "probe_r3" / "area_host_stamp.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"applied and verified: {len(before)} files, only area bits changed, Disc1 == Disc4; "
          f"report probe_r3/area_host_stamp.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
