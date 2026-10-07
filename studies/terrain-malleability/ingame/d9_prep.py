"""PREP for lane d9 -- README section 7.1 rank 1(b)/(c): the DISC9 (Path D world 9013) battle walk + bind receipts.

Everything here is OFFLINE and READ-ONLY on the install (live mod folders, Memoria clone source, p0data). It writes
only ingame/out/d9_prep.json and ingame/out/d9_grid.npz (both gitignored, derived numbers only, no game bytes).

What it computes, each item with the engine site that makes it the right number (cites = the patched clone at
C:\\gd\\FFIX\\Memoria\\Assembly-CSharp; s60/s74/s75 are BUILT + DEPLOYED per memoria-patches/README.md):

  1. THE CELLS. Disc9 (13,15) = the Uaho carry, and Disc9 (6,7) = the rung-6 landing lawn (the CONTROL cell). Each one's
     effective prefab and walk list come from the consumption lane's bind-oracle Engine (BLANK mode: every Path D cell
     IsSea, WorldDiscSpike.cs:80 `CloneStockWorld = false`; a Terrain.ff9mesh arms the divert and Donor.txt picks the
     prefab, WMWorld.cs:516-569, s34/s74), rastered with the engine's SKY ground query (gap_area_layer/arealib.raster,
     calibrated against world/placement.place) at 0.25u.
  2. THE HOMES. The sample with the largest clearance to anything that is NOT (wanted area, wanted topograph, event 0,
     foot-walkable) -- topograph 0 and topograph 37 on the carry, topograph 0 on the landing lawn -- nudged off the 4u
     lattice (RESULTS.md section 5: THE LATTICE-EDGE TELEPORT TRAP). The session teleports to its home before EVERY
     burst and holds each burst under BURST_MAX, so a burst cannot leave the disc (clearance >= CLEAR_MIN asserted).
     CONTROL grounds at each home: `no_divert` (the cell routed to SeaBlockPrefab Block[12][0]f: sea4f at y 0, topo
     56/57 -- he would be at sea, WMWorld.cs:516-544) and, on the carry, `donor_only` (the Donor.txt prefab's own stock
     Terrain). The carry is a VERBATIM (0,0) Terrain in the same local frame (override_equals_donor), so donor_only ==
     the override: a height cannot tell bound from free-riding -- part (c)'s log is the only receipt for that.
  3. THE ENCOUNTER PREDICTION.
       * zone   = w_worldAreaZone[area] (ff9.cs:9229-9232; table parsed from ff9.cs:1348 by engine_consumers)
       * record = the first (topograph, fog) match inside the zone's slice (ff9.cs:9234-9256); a miss -> null -> scene
                  0 -> no battle (s60, ff9.cs:9258-9264, EventEngine.cs:192-195)
       * fog    = 0 on Path D: UseMist() returns false when WorldDiscSpike.Engaged && SuppressMist (WorldConfiguration.cs
                  :223-236; Engaged latches for ids 9013-9099, WorldDiscSpike.cs:51-70; SuppressMist defaults true, :87)
       * table  = disc{w_frameDisc}/discmr.img (ff9.cs:3624-3627); w_frameDisc = GetDisc() = 1 below scenario 11090
                  (ff9.cs:3653, WorldConfiguration.cs:246-252); the live FF9CustomMap-world disc-1 override wins. The
                  slice rows are compared across live / stock disc 1 / stock disc 4, so the disc question cannot flip it.
       * scene  = SelectScene (EventEngine.cs:190-220): random8 against d[pattern & 3] (EventEngine.Static.cs:120-126)
                  over scene[0..3]; a repeat of _lastScene re-rolls once (EventEngine.ProcessEvents.cs:508-509).
       * rate   = WORLD13's own sysvar-207 ENCRATE ladder, decoded from the DEPLOYED us .eb with the kit's ebsrc (207 =
                  the zone under the actor, ff9.cs:4260-4264; ENCRATE sets encratio, EventEngine.DoEventCode.cs:992-997).
                  ProcessEncount (EventEngine.ProcessEvents.cs:496-518): a check every EncounterInterval (960 fixed =
                  3.75u) after EncounterInitial (-1440 -> the first check at 9.375u; InitEncount, EventEngine.Initialize.cs
                  :8-17), base += encratio, fire when random8() < base >> 3 -- certain once the threshold reaches 256.
                  Distance is the world actor's per-tick 3D delta x 256 (EventEngine.ProcessEvents.cs:241-249, :289-297),
                  counted only while _moveKey = w_frameEncountEnable (:72-74), set only while he moves on foot off topo 52
                  with no location title up (ff9.cs:5535-5538) -- so a TELEPORT never counts.
       * the Ragtime-Mouse arm (sysvar 205 -> Battle 941/942 in WORLD13) needs w_frameEventBattleProb, whose ONLY writer
         is RunWorldCode(26) (ff9.cs:3929-3930); checked here that the deployed WORLD13 never calls it -> the static stays
         0 -> x % 1 == 0 != 1 -> 205 never fires (ff9.cs:4254-4255).
  4. THE BIND PREDICTION (part c). For every Disc9 cell with a loose file in the live FolderNames stack, the oracle's
     ordered bound list = the exact "[WorldMeshOverride] loaded 'WorldMap/Disc9/...'" lines one 9013 load must log
     (WorldMeshOverride.cs:47; the Disc9 tag is s74's sentinel, WMWorld.cs:174-179, WorldDiscSpike.cs:43-48).

Rerun:  py studies/terrain-malleability/ingame/d9_prep.py
"""
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
TM = HERE.parent
sys.path.insert(0, str(TM / "gap_area_layer"))
sys.path.insert(0, str(TM / "consumption"))
import arealib as A                                   # noqa: E402  (also puts ff9mapkit on sys.path)
import numpy as np                                    # noqa: E402
from scipy import ndimage                             # noqa: E402
from ff9mapkit.world import worldpack as WP           # noqa: E402
from ff9mapkit.world.placement import WALK_OK         # noqa: E402

OUT = HERE / "out"
NS = 9
CARRY = (13, 15)            # the Uaho carry: Donor.txt -> 0,0, area 63
LANDING = (425.0, -479.0)   # inject_worldjump.py LANDING_X/Z -- where the bench's WorldMap(9013) sets him down
PITCH = 0.25
CELL_MARGIN = 6.0           # keep homes this far inside the cell (the walk query near a border may see the neighbour)
BURST_TARGET = 2.0          # the session sizes each "up" hold to cover ~this many units (speed measured per session)
BURST_MAX = 3.0             # the longest burst it accepts before shortening the hold
CLEAR_MIN = BURST_MAX + 1.0 # the Uaho grass ring is ~9u wide: its best topo-0 disc is ~4u, topo-37 ~4.9u
SINK = 1.171875             # vertical V3, in-game proven (RESULTS.md section 2)
CANOPY = (36, 37, 38)
INTERVAL_U = 960 / 256.0    # Memoria.ini [Battle] EncounterInterval (live 960) in world units
INITIAL_U = (1440 + 960) / 256.0
WORLD13 = A.GAME / ("FF9CustomMap-world/StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/world/us/"
                    "EVT_WORLD_WORLD13.eb.bytes")


def ini_battle():
    txt = (A.GAME / "Memoria.ini").read_text(encoding="utf-8", errors="replace")
    sec = re.search(r"^\[Battle\](.*?)(?=^\[)", txt, re.S | re.M)
    vals = dict(re.findall(r"^\s*(EncounterInterval|EncounterInitial|PSXEncounterMethod|PersistentDangerValue)\s*=\s*(-?\d+)",
                           sec.group(1), re.M)) if sec else {}
    ctl = re.search(r"^\[Control\](.*?)(?=^\[)", txt, re.S | re.M)
    soft = re.search(r"^\s*SoftReset\s*=\s*(\d+)", ctl.group(1), re.M) if ctl else None
    out = {k: int(v) for k, v in vals.items()}
    out["Control.SoftReset"] = int(soft.group(1)) if soft else None
    return out


def cell_grid(bx, by):
    cf = A.live_cells().get((NS, bx, by), {})
    if not cf:
        raise SystemExit(f"Disc9 ({bx},{by}) has no live override files -- the Path D content moved; re-plan")
    pk, why, walk = A.live_walk_list(NS, bx, by, cf)
    meshes = A.load_walk_arrays(walk)
    ids, pi, ys = A.raster(meshes, pitch=PITCH)
    px, pz, n = A.sample_grid(PITCH)
    ox, oz = bx * 64.0, -by * 64.0
    g = {"X": ox + px.reshape(n, n), "Z": oz + pz.reshape(n, n), "Y": ys.reshape(n, n), "ids": ids.reshape(n, n),
         "part": pi.reshape(n, n), "ox": ox, "oz": oz, "bx": bx, "by": by}
    g["area"] = np.where(g["ids"] >= 0, (g["ids"] & 0x3F00) >> 8, -1)
    g["topo"] = np.where(g["ids"] >= 0, (g["ids"] & 0xFC) >> 2, -1)
    g["event"] = np.where(g["ids"] >= 0, (g["ids"] & 0xC000) >> 14, -1)
    g["walk"] = np.isin(g["topo"], sorted(WALK_OK)) & (g["ids"] >= 0)
    return {"prefab": pk, "why": why, "walk": walk, "meshes": meshes, "g": g}


def exact_ground(meshes, x, z, ox, oz):
    """The engine's sky query at one point (same rule as session1_post.ground, on one cell's walk list)."""
    lx, lz = x - ox, z - oz
    for (name, V, ids) in meshes:
        if V.size == 0:
            continue
        a, b, c = V[:, 0], V[:, 1], V[:, 2]
        u, v = b - a, c - a
        cx = u[:, 1] * v[:, 2] - u[:, 2] * v[:, 1]
        cy = u[:, 2] * v[:, 0] - u[:, 0] * v[:, 2]
        cz = u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0]
        L = np.sqrt(cx * cx + cy * cy + cz * cz)
        L[L == 0] = 1.0
        d = (b[:, 2] - c[:, 2]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 2] - c[:, 2])
        ok = (cy / L > 0.1) & ~np.isin(ids, A.IDALL_SKIP) & (np.abs(d) >= 1e-12)
        dd = np.where(ok, d, 1.0)
        w0 = ((b[:, 2] - c[:, 2]) * (lx - c[:, 0]) + (c[:, 0] - b[:, 0]) * (lz - c[:, 2])) / dd
        w1 = ((c[:, 2] - a[:, 2]) * (lx - c[:, 0]) + (a[:, 0] - c[:, 0]) * (lz - c[:, 2])) / dd
        w2 = 1 - w0 - w1
        hits = np.nonzero(ok & (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9))[0]
        if hits.size == 0:
            continue
        t = hits[0]
        idv = int(ids[t])
        if idv == A.VETO:
            continue
        return {"ground": round(float(w0[t] * a[t, 1] + w1[t] * b[t, 1] + w2[t] * c[t, 1]), 4), "part": name,
                "id": idv, **A.decode(idv)}
    return {"ground": None, "part": "MISS"}


def pick_home(cell, area, topo):
    g = cell["g"]
    ok = (g["area"] == area) & (g["topo"] == topo) & (g["event"] == 0) & g["walk"]
    clear = ndimage.distance_transform_edt(np.pad(ok, 1, constant_values=False))[1:-1, 1:-1] * PITCH
    lx, lz = g["X"] - g["ox"], -(g["Z"] - g["oz"])
    inside = (lx > CELL_MARGIN) & (lx < 64 - CELL_MARGIN) & (lz > CELL_MARGIN) & (lz < 64 - CELL_MARGIN)
    score = np.where(ok & inside, clear, -1)
    i, j = np.unravel_index(np.argmax(score), score.shape)
    x, z = float(g["X"][i, j]), float(g["Z"][i, j])
    for _ in range(8):                              # off the 4u lattice by >= 0.3u on both axes
        if min(abs(x / 4 - round(x / 4)) * 4, abs(z / 4 - round(z / 4)) * 4) >= 0.3:
            break
        x, z = x + 0.13, z - 0.11
    bad = ~ok
    near = float(np.min(np.hypot(g["X"][bad] - x, g["Z"][bad] - z))) if bad.any() else 99.0
    ev, obj = g["event"] > 0, g["part"] == 0
    h = {"cell": [g["bx"], g["by"]], "world": [round(x, 3), round(z, 3)], "area": area, "topo": topo,
         "clearance": round(min(float(clear[i, j]), near), 2), "u2_of_class": round(float(ok.sum()) * PITCH ** 2, 1),
         "min_dist_event_tile": round(float(np.min(np.hypot(g["X"][ev] - x, g["Z"][ev] - z))), 2) if ev.any() else None,
         "min_dist_part0": round(float(np.min(np.hypot(g["X"][obj] - x, g["Z"][obj] - z))), 2) if obj.any() else None,
         "part0": cell["walk"][0][0] if cell["walk"] else None}
    h["exact"] = exact_ground(cell["meshes"], x, z, g["ox"], g["oz"])
    h["expect_world_y"] = (round(h["exact"]["ground"] - SINK, 4) if topo in CANOPY else h["exact"]["ground"])
    V, ids = A.stock_mesh("d1/0_1/12,0/sea4f")
    h["control_no_divert"] = exact_ground([("Sea4", V, ids)], x - g["ox"], z - g["oz"], 0.0, 0.0)
    assert h["clearance"] >= CLEAR_MIN, f"{h['cell']} area {area} topo {topo}: clearance {h['clearance']} < {CLEAR_MIN}"
    assert (h["exact"]["area"], h["exact"]["topo"], h["exact"]["event"]) == (area, topo, 0), h
    return h


def donor_only(x, z, cell):
    walk = [(nm, key, "stock") for nm, key in A.stock_walk_list(1, 0, 0)]
    r = exact_ground(A.load_walk_arrays(walk), x - cell["g"]["ox"], z - cell["g"]["oz"], 0.0, 0.0)
    r["walk"] = [w[0] for w in walk]
    return r


def override_equals_donor():
    """Is Disc9 (13,15) Terrain.ff9mesh the donor (0,0) stock Terrain verbatim (same local frame)?"""
    p = A.GAME / "FF9CustomMap-world/FF9_Data/WorldMap/Disc9/0_1/r15/Block[13][15] Terrain.ff9mesh"
    V, ids = A.read_ff9mesh_arrays(p)
    Vs, idss = A.stock_mesh("d1/0_1/0,0/terrain")
    a = {tuple(r) for r in np.round(V.reshape(-1, 3), 3)}
    b = {tuple(r) for r in np.round(Vs.reshape(-1, 3), 3)}
    return {"override_tris": int(len(V)), "donor_tris": int(len(Vs)), "vertex_overlap": len(a & b),
            "override_verts": len(a), "donor_verts": len(b),
            "idall_multiset_equal": sorted(ids.tolist()) == sorted(idss.tolist())}


def encounter_table(area):
    con = A.consequence(area)
    zone = con["zone"]
    live_p = A.GAME / "FF9CustomMap-world/StreamingAssets/assets/resources/worldmap/wmap/disc1/discmr.img.bytes"
    tabs = {"stock_disc1": WP.load_discmr(1), "stock_disc4": WP.load_discmr(4)}
    if live_p.is_file():
        tabs["live_disc1"] = WP.Discmr.from_bytes(live_p.read_bytes(), disc=1)
    rows = []
    for i in WP.zone_slice(zone):
        per = {k: {"scene": t.encounters[i].scene, "topo": t.encounters[i].topograph, "fog": t.encounters[i].fog,
                   "sel": t.encounters[i].pattern & 3} for k, t in tabs.items()}
        main_tab = per["live_disc1"] if "live_disc1" in per else per["stock_disc1"]
        rows.append({"index": i, **main_tab, "same_in_all_tables": all(v == main_tab for v in per.values())})
    by = {}
    for r in rows:
        by.setdefault(f"topo{r['topo']}_fog{r['fog']}", sorted(set(r["scene"])))
    sl = WP.zone_slice(zone)
    return {"area": area, "consequence": con, "zone": zone, "slice": [sl.start, sl.stop], "tables": sorted(tabs),
            "live_table": str(live_p) if live_p.is_file() else None, "rows": rows, "scene_by_topo_fog": by,
            "slice_scenes": sorted({s for r in rows for s in r["scene"]})}


def world13_facts():
    """Decode the DEPLOYED WORLD13 (us) with the kit's round-trip-verified ebsrc; pull the ENCRATE ladder and the
    Ragtime-Mouse prerequisites."""
    from ff9mapkit.eb import ebsrc
    src = ebsrc.write_source(WORLD13.read_bytes(), title="EVT_WORLD_WORLD13 (us, deployed)", enrich=False)
    lines = src.splitlines()
    k = next(i for i, ln in enumerate(lines) if "B_SYSVAR[207]" in ln)
    sw = lines[k + 1]
    m = re.match(r"\s*SWITCH\((\d+),\s*(L\d+),\s*(.*)\)", sw)
    base, default, arms = int(m.group(1)), m.group(2), [a.strip() for a in m.group(3).split(",")]
    lab = {}
    for i in range(k, min(len(lines), k + 200)):
        lm = re.match(r"\s*(L\d+):\s*$", lines[i])
        if lm and i + 1 < len(lines):
            cm = re.search(r"Instance\.Byte\[0\] const\((\d+)\) B_LET", lines[i + 1])
            if cm:
                lab[lm.group(1)] = int(cm.group(1))
    after = "\n".join(lines[k:k + 160])
    return {"file": str(WORLD13), "switch_line": sw.strip(), "base": base, "default": default,
            "encratio_by_zone": {base + j: lab.get(a) for j, a in enumerate(arms)},
            "ladder_feeds_SetRandomBattleFrequency": "SetRandomBattleFrequency({Instance.Byte[0]" in after,
            "reads_sysvar_205": "B_SYSVAR[205]" in src, "calls_RunWorldCode_26": bool(re.search(r"RunWorldCode\(26\b", src)),
            "scripted_battles": sorted(set(int(x) for x in re.findall(r"Battle\(0, (\d+)\)", src)))}


def battle_distance_model(encratio):
    surv, rows, base = 1.0, [], 0
    for k in range(1, 400):
        base += encratio
        thr = min(base >> 3, 256)
        p = thr / 256.0
        rows.append((k, surv * p))
        surv *= (1 - p)
        if thr >= 256:
            break
    P = np.array([r[1] for r in rows])
    ks = np.array([r[0] for r in rows])
    dist = INITIAL_U + (ks - 1) * INTERVAL_U
    cdf = np.cumsum(P)

    def q(x):
        return round(float(dist[min(len(dist) - 1, int(np.searchsorted(cdf, x)))]), 2)
    return {"encratio": encratio, "first_check_u": INITIAL_U, "check_every_u": INTERVAL_U,
            "mean_u": round(float((P * dist).sum()), 1), "median_u": q(0.5), "p90_u": q(0.9), "p99_u": q(0.99),
            "certain_by_u": round(float(dist[-1]), 2), "certain_at_check": int(ks[-1])}


def bind_prediction():
    import bind_oracle as BO
    E = BO.Engine(A.census())
    files = BO.scan_overrides(A.GAME, BO.folder_names(A.GAME))
    cells = {}
    for (ns, x, y), cf in sorted(files.items()):
        if ns != NS:
            continue
        pk, why, _ = E.effective(ns, x, y, cf)
        order, bound = E.bind_list(ns, x, y, pk, cf)
        cells[f"{x},{y}"] = {"effective": pk, "why": why, "bound": [nm for nm, _ in bound],
                             "free_riders": [nm for nm, s in order if s != "__bare_object__" and f"{nm}.ff9mesh" not in cf]}
    return {"folders": BO.folder_names(A.GAME), "disc9_cells_with_files": len(cells),
            "disc9_cells_binding": sum(1 for c in cells.values() if c["bound"]),
            "lines_per_9013_load": sum(len(c["bound"]) for c in cells.values()), "cells": cells}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    carry = cell_grid(*CARRY)
    lb = (int(LANDING[0] // 64), int(-LANDING[1] // 64))
    land = cell_grid(*lb)
    for nm, c in (("carry", carry), ("landing", land)):
        print(f"{nm}: Disc9 {c['g']['bx'], c['g']['by']} effective prefab {c['prefab']} ({c['why']})")
        for w in c["walk"]:
            print(f"   {w[0]:10s} {w[2]:8s} {Path(str(w[1])).name}")
    g = carry["g"]
    hist = {}
    for a, t in sorted({(int(a), int(t)) for a, t in zip(g["area"].ravel(), g["topo"].ravel())}):
        m = (g["area"] == a) & (g["topo"] == t)
        hist[f"area{a}_topo{t}"] = {"u2": round(float(m.sum()) * PITCH ** 2, 1), "walkable": t in WALK_OK}
    homes = {"topo0": pick_home(carry, 63, 0), "topo37": pick_home(carry, 63, 37)}
    for k in ("topo0", "topo37"):
        homes[k]["control_donor_only"] = donor_only(*homes[k]["world"], carry)
    land_exact = exact_ground(land["meshes"], *LANDING, land["g"]["ox"], land["g"]["oz"])
    homes["landing"] = pick_home(land, land_exact["area"], land_exact["topo"])
    for k, h in homes.items():
        print(f"home {k:7s} {h['world']} cell {h['cell']} area {h['area']} topo {h['topo']} clearance {h['clearance']}u "
              f"ground {h['exact']['ground']} expect world_y {h['expect_world_y']} | event tiles >= "
              f"{h['min_dist_event_tile']}u | no-divert control y {h['control_no_divert'].get('ground')} "
              f"topo {h['control_no_divert'].get('topo')}")
    enc = encounter_table(63)
    enc0 = encounter_table(land_exact["area"])
    w13 = world13_facts()
    rate = w13["encratio_by_zone"].get(enc["zone"])
    rate0 = w13["encratio_by_zone"].get(enc0["zone"])
    model = battle_distance_model(rate) if rate else None
    model0 = battle_distance_model(rate0) if rate0 else None
    print(f"area 63 -> zone {enc['zone']} (camera place {enc['consequence']['camera_place']}); records "
          f"{[(r['index'], r['topo'], r['fog'], r['scene']) for r in enc['rows']]}")
    print(f"landing area {land_exact['area']} -> zone {enc0['zone']}; topo-0 rows "
          f"{[(r['index'], r['fog'], r['scene']) for r in enc0['rows'] if r['topo'] == 0]}")
    print(f"WORLD13 ENCRATE zone {enc['zone']} = {rate} -> {model}")
    print(f"WORLD13 ENCRATE zone {enc0['zone']} = {rate0} -> {model0}")
    print(f"WORLD13 reads sysvar 205: {w13['reads_sysvar_205']}; calls RunWorldCode(26): {w13['calls_RunWorldCode_26']}")
    pred = {"topo0": enc["scene_by_topo_fog"].get("topo0_fog0"), "topo37": enc["scene_by_topo_fog"].get("topo37_fog0"),
            "fog1_alternative": {"topo0": enc["scene_by_topo_fog"].get("topo0_fog1"),
                                 "topo37": enc["scene_by_topo_fog"].get("topo37_fog1")},
            "zone24_slice": enc["slice_scenes"],
            "landing": enc0["scene_by_topo_fog"].get(f"topo{land_exact['topo']}_fog0"),
            "landing_zone_slice": enc0["slice_scenes"]}
    bind = bind_prediction()
    print(f"bind: {bind['disc9_cells_binding']} of {bind['disc9_cells_with_files']} Disc9 cells bind; "
          f"{bind['lines_per_9013_load']} 'loaded' lines per 9013 load; (13,15) -> {bind['cells'].get('13,15')}")
    grids = {}
    for tag, c in (("carry", carry), ("landing", land)):
        cg = c["g"]
        for key in ("X", "Z", "Y", "area", "topo", "event", "part"):
            grids[f"{tag}_{key}"] = cg[key]
        grids[f"{tag}_origin"] = np.array([cg["ox"], cg["oz"]])
    np.savez_compressed(OUT / "d9_grid.npz", pitch=PITCH, **grids)
    rec = {"carry_cell": {"ns": NS, "cell": list(CARRY), "effective_prefab": carry["prefab"], "why": carry["why"],
                          "walk": [[w[0], w[2], str(w[1])] for w in carry["walk"]], "area_topo_u2": hist,
                          "event_tile_u2": round(float((g["event"] > 0).sum()) * PITCH ** 2, 1),
                          "part0_object_u2": round(float((g["part"] == 0).sum()) * PITCH ** 2, 1)},
           "landing_cell": {"ns": NS, "cell": list(lb), "effective_prefab": land["prefab"], "why": land["why"],
                            "walk": [[w[0], w[2], str(w[1])] for w in land["walk"]], "at_landing": land_exact},
           "homes": homes, "encounter": enc, "encounter_landing": enc0, "world13": w13,
           "rate_model": model, "rate_model_landing": model0, "override_equals_donor": override_equals_donor(),
           "predicted_scenes": pred, "ini": ini_battle(), "bind": bind,
           "constants": {"sink": SINK, "burst_target": BURST_TARGET, "burst_max": BURST_MAX, "clear_min": CLEAR_MIN,
                         "pitch": PITCH, "landing": list(LANDING)}}
    (OUT / "d9_prep.json").write_text(json.dumps(rec, indent=1, default=str), encoding="utf-8")
    print(f"wrote {OUT / 'd9_prep.json'} and {OUT / 'd9_grid.npz'}")


if __name__ == "__main__":
    main()
