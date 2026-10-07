"""AREA LINT (prototype of the proposed kit lint) -- run over the live overworld overrides, after a CALIBRATION that
proves it fires where it must and stays silent where it must.

Each rule is tied to a measured consequence (NOTES.md section E). The lint judges only AUTHORED ground: samples of the
engine sky ground query (arealib.raster) whose IDALL differs from the cell's BACKGROUND -- the stock cell (disc 1/4) or
the BLANK sea4f cell (Path D, ns 9) -- whether the hit comes from an override file or a Donor.txt free rider.

  AL1 LOCK         ERROR  authored walkable area 12: chase camera forced to the default view + toggle refused while
                          ScenarioCounter < 4990 (ff9.cs:2771/3199), spawn weather (ff9.cs:8510), zone 5 battles
  AL2 PLACE-SEAM   ERROR  a walkable<->walkable 4-neighbour pair (either side authored) whose camera place differs
                          (w_cameraArea2Place, ff9.cs:81/3117; no easing) -- stock has ZERO such pairs on both discs
  AL3 EVENT-AREA   WARN   an authored EVENT tile whose area differs from the dominant area of the authored walkable
                          ground of its cell (it re-zones / re-labels / re-frames the trigger tiles); suffix INERT when
                          its packed cell tag matches no object-0 tag of any live dispatcher (not an entrance at all)
  AL4 WEATHER      WARN   authored walkable area 9/12/13 (spawn weather + clouds off, one-shot at world entry)
  AL5 ENCOUNTER    INFO   authored walkable u2 whose (zone, topo, fog 0) HAS a record (battles roll there); WARN when
                          the caller declares the cell `safe`
  AL6 BEACH        INFO   authored walkable area in EMinigame.BeachData (beach bubble + WORLD08 beach-visit bit)
  AL8 INERT-EVENT  INFO   authored event tiles whose packed cell tag (WorldEvent: 0x8000|z<<8|x<<2|id) matches no
                          object-0 tag of any live dispatcher -- a carried entrance that dispatches nothing
  AL7 SKIP-DECODE  INFO   override tris carrying a walk-skip IDALL (4078/4088/2040): their area bits are decode
                          artifacts (4078 = 0x0FEE reads as area 15) -- never a ground hit, never an area consumer

CALIBRATION (exit 1 on failure):
  must FIRE   AL1+AL4 on the live Disc1 Block[19][18] (the carried Cleyra area-12 tiles), and AL3 there
  must FIRE   AL2 on a SYNTHETIC area-40 stamp (half of a live area-14 cell's ground restamped to area 40, in memory)
  must be SILENT (no ERROR/WARN) on a stock-area island: stock disc-1 Block[0][0] (Uaho, areas 0/63) fed in as if
              authored (stock-identity exemption OFF) at its own position
Then it lints every live cell and reports per-rule counts.

Rerun:  py studies/terrain-malleability/gap_area_layer/area_lint.py   -> out/area_lint.json
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import arealib as A                                  # noqa: E402
import numpy as np                                   # noqa: E402
from ff9mapkit.world import placement as P           # noqa: E402

WALK_OK = np.array(sorted(P.WALK_OK))
RECORD_DISC = {1: 1, 4: 4, 9: 1}


def cell_layer(ns, x, y, meshes, kinds, stock_ids=None):
    """meshes [(name, V, ids)], kinds ['override'|'stock'] -> per-sample dict of 64x64 arrays."""
    ids, pi, _ = A.raster(meshes, 1.0)
    hit = ids >= 0
    names = [m[0] for m in meshes]
    land = np.array([(names[p] in A.LAND_PARTS) if p >= 0 else False for p in pi])
    ovr = np.array([(kinds[p] == "override") if p >= 0 else False for p in pi])
    area = np.where(hit, (ids & 0x3F00) >> 8, -1)
    topo = np.where(hit, (ids & 0xFC) >> 2, -1)
    event = np.where(hit, (ids & 0xC000) >> 14, -1)
    walk = hit & land & np.isin(topo, WALK_OK)
    # AUTHORED = differs from the cell's background (stock cell for ns 1/4, the BLANK sea4f cell for ns 9), whether it
    # came from an override file OR a Donor.txt free rider moved to a new position; with no background given (the
    # silent-case harness) every override-sourced hit counts.
    authored = (hit & (ids != stock_ids)) if stock_ids is not None else (ovr & hit)
    r = lambda a: a.reshape(64, 64)                   # noqa: E731  [i(x), j(row)]
    return {"ids": r(ids), "area": r(area), "topo": r(topo), "event": r(event), "walk": r(walk),
            "authored": r(authored), "land": r(land)}


def stock_ids_of(d, x, y):
    walk = A.stock_walk_list(d, x, y)
    ids, _, _ = A.raster([(n, *A.stock_mesh(k)) for n, k in walk], 1.0)
    return ids


def lint(ns, layers, tags=None, safe_cells=(), base=None):
    """layers {(x,y): cell_layer}; base = stock mosaic dict (area/topo/land) for ns 1/4 or None (BLANK sea)."""
    t = A.tables()
    place_lut = np.array(t["w_cameraArea2Place"])
    recs, _ = A.record_set(RECORD_DISC[ns], live=True)
    findings = []
    W, H = 24 * 64, 20 * 64
    if base is not None:
        area = base["area"].copy()
        walk = base["land"] & (area >= 0) & np.isin(base["topo"], WALK_OK)
    else:
        area = np.zeros((W, H), np.int16)
        walk = np.zeros((W, H), bool)
    auth = np.zeros((W, H), bool)
    for (x, y), L in layers.items():
        sl = (slice(x * 64, x * 64 + 64), slice(y * 64, y * 64 + 64))
        area[sl], walk[sl], auth[sl] = L["area"], L["walk"], L["authored"]
    for (x, y), L in sorted(layers.items()):
        aw = L["authored"] & L["walk"]
        c = {"ns": ns, "cell": [x, y]}
        n12 = int((aw & (L["area"] == 12)).sum())
        if n12:
            findings.append({**c, "rule": "AL1", "level": "ERROR", "u2": n12})
        nwx = int((aw & np.isin(L["area"], (9, 12, 13))).sum())
        if nwx:
            findings.append({**c, "rule": "AL4", "level": "WARN", "u2": nwx,
                             "areas": sorted(set(L["area"][aw & np.isin(L["area"], (9, 12, 13))].tolist()))})
        # AL3: authored event tiles vs the dominant authored ground area
        ground = aw & (L["event"] == 0)
        dom = Counter(L["area"][ground].tolist()).most_common(1)
        evm = L["authored"] & (L["event"] > 0)
        if evm.any() and dom:
            dom_a = dom[0][0]
            bad = evm & (L["area"] != dom_a)
            if bad.any():
                cc, rr = np.nonzero(bad)
                cells = {(int((x * 64 + i + 0.37) // 32), int((y * 64 + j + 0.61) // 32), int(L["event"][i, j]))
                         for i, j in zip(cc, rr)}
                armed = sorted(f"{a},{b},e{e}" for (a, b, e) in cells if tags and (a, b, e) in tags)
                findings.append({**c, "rule": "AL3", "level": "WARN", "u2": int(bad.sum()),
                                 "event_areas": sorted(set(L["area"][bad].tolist())), "ground_area": dom_a,
                                 "armed_tags": armed, "inert": not armed})
        # AL8: every authored event tile cluster whose packed cell tag matches NO live dispatcher tag (inert)
        if evm.any() and tags is not None:
            cc, rr = np.nonzero(evm)
            cells_e = Counter((int((x * 64 + i + 0.37) // 32), int((y * 64 + j + 0.61) // 32), int(L["event"][i, j]),
                               int(L["area"][i, j])) for i, j in zip(cc, rr))
            inert = {k: n for k, n in cells_e.items() if (k[0], k[1], k[2]) not in tags}
            if inert:
                findings.append({**c, "rule": "AL8", "level": "INFO", "u2": int(sum(inert.values())),
                                 "inert_tags_area": sorted(f"{a},{b},e{e},area{ar}" for (a, b, e, ar) in inert)})
        # AL5 / AL6
        enc = 0
        for tp, n in Counter(zip(L["area"][aw].tolist(), L["topo"][aw].tolist())).items():
            z = t["w_worldAreaZone"][tp[0]]
            if (z, tp[1], 0) in recs:
                enc += n
        if enc:
            findings.append({**c, "rule": "AL5", "level": "WARN" if (x, y) in safe_cells else "INFO", "u2": enc})
        nb = int((aw & np.isin(L["area"], t["BeachData"])).sum())
        if nb:
            findings.append({**c, "rule": "AL6", "level": "INFO", "u2": nb,
                             "areas": sorted(set(L["area"][aw & np.isin(L["area"], t["BeachData"])].tolist()))})
    # AL2: place seams on the mosaic, any pair touching authored ground
    pl = np.where(area >= 0, place_lut[np.clip(area, 0, 63)], -1)
    seam_cells = Counter()
    for ax in (0, 1):
        nb_ = np.roll(pl, -1, axis=ax)
        d = walk & np.roll(walk, -1, axis=ax) & (auth | np.roll(auth, -1, axis=ax)) & (pl != nb_)
        cc, rr = np.nonzero(d)
        for i, j in zip(cc, rr):
            seam_cells[(int(i) // 64, int(j) // 64, int(area[i, j]), int(np.roll(area, -1, axis=ax)[i, j]))] += 1
    for (bx, by, a1, a2), n in seam_cells.items():
        findings.append({"ns": ns, "cell": [bx, by], "rule": "AL2", "level": "ERROR", "pairs": n,
                         "areas": [a1, a2], "places": [int(place_lut[a1]), int(place_lut[a2])]})
    return findings


def skip_decode(meshes, kinds):
    n = Counter()
    for (name, V, ids), k in zip(meshes, kinds):
        if k == "override":
            for v in np.unique(ids):
                if int(v) in A.IDALL_SKIP:
                    n[(name, int(v), A.decode(int(v))["area"])] += int((ids == v).sum())
    return n


def live_tags():
    import lead_1918 as LD
    tags = set()
    for n, (src, data) in LD.live_dispatchers().items():
        tags |= set(LD.tags_of(data))
    return tags


def live_layers(ns, cells_files, with_stock_exempt=True):
    layers, skips = {}, Counter()
    for (cns, x, y), files in cells_files.items():
        if cns != ns:
            continue
        pk, why, walk = A.live_walk_list(ns, x, y, files)
        meshes = A.load_walk_arrays(walk)
        kinds = [k for _, _, k in walk]
        if not with_stock_exempt:
            sids = None
        elif ns in (1, 4):
            sids = stock_ids_of(ns, x, y)
        else:                                         # s75 BLANK Path-D grid: every cell's background is sea4f
            sids = A.raster([("Sea4", *A.stock_mesh("d1/0_1/12,0/sea4f"))], 1.0)[0]
        layers[(x, y)] = cell_layer(ns, x, y, meshes, kinds, sids)
        skips.update(skip_decode(meshes, kinds))
    return layers, skips


def main():
    A.OUT.mkdir(exist_ok=True)
    z = np.load(A.OUT / "stock_atlas.npz")
    base = {d: {"area": z[f"area_d{d}"], "topo": z[f"topo_d{d}"], "land": z[f"land_d{d}"]} for d in (1, 4)}
    cells = A.live_cells()
    tags = live_tags()
    res = {"calibration": {}}
    # ---- C-a: Block[19][18] must fire AL1 + AL4 + AL3 ----
    L1, _ = live_layers(1, {k: v for k, v in cells.items() if k == (1, 19, 18)})
    f_a = lint(1, L1, tags, base=base[1])
    rules_a = {f["rule"] for f in f_a if f["level"] in ("ERROR", "WARN")}
    ok_a = {"AL1", "AL4", "AL3"} <= rules_a
    # ---- C-b: synthetic area-40 stamp on half of a live area-14 cell must fire AL2 ----
    Lb, _ = live_layers(1, {k: v for k, v in cells.items() if k == (1, 10, 9)})
    Lsyn = {k: dict(v) for k, v in Lb.items()}
    v = Lsyn[(10, 9)]
    a = v["area"].copy()
    half = np.zeros_like(a, bool)
    half[:32, :] = True
    stamp = half & v["walk"] & (a == 14)
    a[stamp] = 40
    v["area"] = a
    v["authored"] = v["authored"] | stamp
    f_b = lint(1, Lsyn, tags, base=base[1])
    ok_b = any(f["rule"] == "AL2" for f in f_b) and int(stamp.sum()) > 0
    f_b0 = lint(1, Lb, tags, base=base[1])                 # the same cell UNSTAMPED: no AL2
    ok_b0 = not any(f["rule"] == "AL2" for f in f_b0)
    # ---- C-c: stock Uaho island (0,0) fed as authored, exemption OFF: must be silent ----
    walk = A.stock_walk_list(1, 0, 0)
    meshes = [(n, *A.stock_mesh(k)) for n, k in walk]
    Lc = {(0, 0): cell_layer(1, 0, 0, meshes, ["override"] * len(meshes), None)}
    f_c = lint(1, Lc, tags, base=base[1])
    loud_c = [f for f in f_c if f["level"] in ("ERROR", "WARN")]
    ok_c = not loud_c and int(Lc[(0, 0)]["authored"].sum()) > 0
    res["calibration"] = {"fires_on_19_18": {"ok": ok_a, "rules": sorted(rules_a), "findings": f_a},
                          "fires_on_area40_stamp": {"ok": ok_b, "stamped_u2": int(stamp.sum()),
                                                    "AL2": [f for f in f_b if f["rule"] == "AL2"]},
                          "silent_unstamped_control": {"ok": ok_b0},
                          "silent_on_stock_uaho": {"ok": ok_c, "authored_u2": int(Lc[(0, 0)]["authored"].sum()),
                                                   "loud": loud_c, "info": [f for f in f_c if f["level"] == "INFO"]}}
    ok = ok_a and ok_b and ok_b0 and ok_c
    res["calibration_ok"] = ok
    print("CALIBRATION:", {k: v["ok"] for k, v in res["calibration"].items()}, "->", "PASS" if ok else "FAIL")
    if not ok:
        (A.OUT / "area_lint.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
        print(json.dumps(res["calibration"], indent=1, default=str)[:4000])
        return 1
    # ---- the live run ----
    res["live"] = {}
    for ns in (1, 4, 9):
        L, skips = live_layers(ns, cells)
        f = lint(ns, L, tags, base=base.get(ns))
        cnt = Counter((x["rule"], x["level"]) for x in f)
        res["live"][ns] = {"cells": len(L), "counts": {f"{r}/{lv}": n for (r, lv), n in sorted(cnt.items())},
                           "findings": f,
                           "skip_decode_tris": [[p, v_, a_, n] for (p, v_, a_), n in sorted(skips.items())]}
        print(f"\nDisc{ns}: {len(L)} cells  {res['live'][ns]['counts']}")
        for x in f:
            if x["level"] in ("ERROR", "WARN"):
                print("   ", {k: x[k] for k in x if k != "ns"})
        print("   skip-decode tris (part, idall, decoded area, n):", res["live"][ns]["skip_decode_tris"])
    (A.OUT / "area_lint.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
