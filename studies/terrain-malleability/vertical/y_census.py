"""THE VERTICAL ENVELOPE -- STOCK Y census of every overworld sub-mesh part, both discs.

What it measures (all from the user's own install, read-only):
  1. per PART x DISC: tri count, vertex-Y min / p1 / p5 / p50 / p95 / p99 / max, plus plan-AREA-weighted
     centroid-Y percentiles (area weighting = "how much of the map sits at this height", vertex
     percentiles over-weight dense rock).
  2. TERRAIN top peaks (one row per block: the block's max vertex, its world x/z, the topo of that tri),
     and the same for the OBJECT part (baked towns/landmarks -- the tallest geometry on the map).
  3. LAND BELOW Y=0: terrain tris with any vertex < 0 -- count, plan area, topo histogram, min y, blocks;
     and whether ANY sea/beach part covers those plan positions (sampled with the calibrated kit
     simulator `placement.all_sheets`).
  4. SEA LAYERS: for every sea*/beach* part, the fraction of verts at exactly y == 0.0 and max |y|.
  5. PER-TOPO terrain height ranges (up-facing tris only, area-weighted), the foot-legal maximum, and
     plan area above the engine thresholds 29 (mist height-fog base), 33.2 / 37.1 (camera ride clamps),
     42.1875 (flight ceiling).

Per-tri arrays are cached OUTSIDE the repo (scratchpad -- they are a near-raw re-encoding of the
meshes, so they never enter the repo; provenance gate). Only aggregates go to out/y_census.json.

CALIBRATION (asserted below, against numbers recorded in project memory before this lane existed):
  * sea4 is a flat plane at y == 0.000 (project-ff9-sea-sheet-laws)
  * topo 49 rock reaches ~37u (project-ff9-overworld-interior-topography, "h to 37u")
  * scrub topo 5 dips to about -3.6u (same memory, LOOK FAMILIES)
  * Uaho's centre peak is topo 49 @ y 7.68 (project-ff9-overworld-placement-rules) -- checked as
    "a topo-49 vertex within 0.05 of 7.68 exists in Uaho's blocks" is too weak, so instead we only
    use the first three as the calibration gate.

Run:  py studies/terrain-malleability/vertical/y_census.py           (first run ~2-4 min, then cached)
      py studies/terrain-malleability/vertical/y_census.py --rebuild (re-extract)
"""
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
import numpy as np                                   # noqa: E402
from ff9mapkit.world import extract as X             # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
CACHE = Path(r"C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX"
             r"\8b61f6d3-b0c2-4ade-9f22-b2bc267b1c8d\scratchpad\vertical_cache")
CACHE.mkdir(parents=True, exist_ok=True)
REBUILD = "--rebuild" in sys.argv

FOOT_OK = set(list(range(0, 8)) + list(range(10, 14)) + list(range(16, 24)) + [27, 28, 30, 31]
              + list(range(32, 39)) + [41, 42, 45, 46, 52])       # engine_bounds.py mode 0 decode
THRESH = {"mist_heightfog_base_29": 29.0, "flyer_cam_clamp_33.2": 33.2,
          "cam_ride_clamp_37.1": 37.1, "flight_ceiling_42.1875": 42.1875}


def part_blocks(disc, lod="0_1"):
    env = X._worldmap_env(disc)
    pat = re.compile(rf"worldmap/disc{disc}/{lod}/r\d+/block\[(\d+)\]\[(\d+)\] ([a-z0-9_]+)(?:\.asset)?$")
    per = defaultdict(set)
    for k in env.container:
        m = pat.search((k or "").lower())
        if m:
            per[m.group(3)].add((int(m.group(1)), int(m.group(2))))
    return {p: sorted(b) for p, b in per.items()}


def extract(disc):
    f = CACHE / f"tris_disc{disc}.npz"
    if f.exists() and not REBUILD:
        z = np.load(f, allow_pickle=True)
        return {k: z[k] for k in z.files}
    pb = part_blocks(disc)
    parts = sorted(pb)
    cols = defaultdict(list)
    vstats = []   # per (part, block): vertex y list summary for exact-zero tests
    for pi, part in enumerate(parts):
        for (bx, by) in pb[part]:
            try:
                bm = X.read_block(bx, by, disc=disc, part=part)
            except Exception as e:                         # noqa: BLE001
                print(f"  skip disc{disc} {part} ({bx},{by}): {e}")
                continue
            V = np.asarray(bm.verts, dtype=np.float64)
            if V.size == 0:
                continue
            F = np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3)
            T = bm.tangents
            idall = (np.array([int(round(T[i][0])) for i in F[:, 0]], dtype=np.int64)
                     if T is not None else np.zeros(len(F), dtype=np.int64))
            a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
            cr = np.cross(b - a, c - a)
            L = np.linalg.norm(cr, axis=1)
            ny = np.where(L > 0, cr[:, 1] / np.where(L > 0, L, 1), 0.0)
            plan = 0.5 * np.abs((b[:, 0] - a[:, 0]) * (c[:, 2] - a[:, 2]) - (b[:, 2] - a[:, 2]) * (c[:, 0] - a[:, 0]))
            ys = np.stack([a[:, 1], b[:, 1], c[:, 1]], axis=1)
            am = ys.argmax(axis=1)
            tri_pts = np.stack([a, b, c], axis=1)
            top = tri_pts[np.arange(len(F)), am]
            ox, oz = X.block_world_origin(bx, by)
            n = len(F)
            cols["part"].append(np.full(n, pi, np.int16))
            cols["bx"].append(np.full(n, bx, np.int16))
            cols["by"].append(np.full(n, by, np.int16))
            cols["ymin"].append(ys.min(axis=1))
            cols["ymax"].append(ys.max(axis=1))
            cols["yc"].append(ys.mean(axis=1))
            cols["plan"].append(plan)
            cols["ny"].append(ny)
            cols["idall"].append(idall)
            cols["topx"].append(top[:, 0] + ox)
            cols["topz"].append(top[:, 2] + oz)
            cols["cx"].append(tri_pts[:, :, 0].mean(axis=1) + ox)
            cols["cz"].append(tri_pts[:, :, 2].mean(axis=1) + oz)
            vy = V[:, 1]
            vstats.append((pi, bx, by, len(vy), int((vy == 0.0).sum()), float(np.abs(vy).max()),
                           float(vy.min()), float(vy.max())))
        print(f"  disc{disc} {part}: {len(pb[part])} blocks")
    data = {k: np.concatenate(v) for k, v in cols.items()}
    data["parts"] = np.array(parts, dtype=object)
    data["vstats"] = np.array(vstats, dtype=np.float64)
    np.savez_compressed(f, **data)
    return data


def wpct(y, w, qs):
    o = np.argsort(y)
    y, w = y[o], w[o]
    cw = np.cumsum(w)
    if cw[-1] <= 0:
        return [float("nan")] * len(qs)
    return [float(np.interp(q / 100 * cw[-1], cw, y)) for q in qs]


R = {}
for disc in (1, 4):
    print(f"== disc {disc}: extracting/loading")
    d = extract(disc)
    parts = list(d["parts"])
    topo = (d["idall"] & 0xFC) >> 2
    R[disc] = rd = {}
    # 1. per-part table ------------------------------------------------------------------------------
    rd["parts"] = {}
    vst = d["vstats"]
    for pi, part in enumerate(parts):
        m = d["part"] == pi
        if not m.any():
            continue
        vs = vst[vst[:, 0] == pi]
        allv = np.concatenate([d["ymin"][m], d["ymax"][m], d["yc"][m]])
        rd["parts"][part] = {
            "blocks": int(len(vs)), "tris": int(m.sum()),
            "vert_y_min": float(vs[:, 6].min()), "vert_y_max": float(vs[:, 7].max()),
            "tri_ymax_pcts_1_5_50_95_99": [float(np.percentile(d["ymax"][m], q)) for q in (1, 5, 50, 95, 99)],
            "area_w_centroid_pcts_1_5_50_95_99": wpct(d["yc"][m], d["plan"][m], (1, 5, 50, 95, 99)),
            "frac_verts_exact_zero": float(vs[:, 4].sum() / vs[:, 3].sum()),
            "max_abs_y": float(vs[:, 5].max()),
            "plan_area": float(d["plan"][m].sum()),
        }
    # 2. tallest terrain / object, one row per block ------------------------------------------------
    for part in ("terrain", "object"):
        if part not in parts:
            continue
        pi = parts.index(part)
        m = np.where(d["part"] == pi)[0]
        best = {}
        for i in m:
            k = (int(d["bx"][i]), int(d["by"][i]))
            if k not in best or d["ymax"][i] > d["ymax"][best[k]]:
                best[k] = i
        rows = sorted(best.items(), key=lambda kv: -d["ymax"][kv[1]])
        rd[f"tallest_{part}"] = [
            {"block": list(k), "ymax": round(float(d["ymax"][i]), 3),
             "world_xz": [round(float(d["topx"][i]), 2), round(float(d["topz"][i]), 2)],
             "topo": int(topo[i]), "idall": int(d["idall"][i]), "ny": round(float(d["ny"][i]), 3)}
            for k, i in rows[:25]]
        rd[f"{part}_blocks_ymax_hist"] = Counter(int(math.floor(d["ymax"][i] / 5) * 5) for _, i in rows)
    # 3. land below zero ---------------------------------------------------------------------------
    pi = parts.index("terrain")
    mt = d["part"] == pi
    below = mt & (d["ymin"] < 0)
    rd["terrain_below_zero"] = {
        "tris": int(below.sum()), "plan_area": float(d["plan"][below].sum()),
        "min_y": float(d["ymin"][below].min()) if below.any() else None,
        "topo_hist": dict(Counter(int(t) for t in topo[below]).most_common()),
        "topo_hist_centroid_below_minus_0p5": dict(Counter(int(t) for t in topo[below & (d["yc"] < -0.5)]).most_common()),
        "blocks": sorted({(int(x), int(y)) for x, y in zip(d["bx"][below], d["by"][below])}),
        "up_facing_footlegal_tris": int((below & (d["ny"] > 0.1) & np.isin(topo, list(FOOT_OK))).sum()),
    }
    # 5. per-topo + thresholds (terrain, up-facing) ----------------------------------------------------
    up = mt & (d["ny"] > 0.1)
    rd["topo_heights"] = {}
    for t in sorted(set(int(x) for x in topo[up])):
        m = up & (topo == t)
        rd["topo_heights"][t] = {
            "tris": int(m.sum()), "plan_area": round(float(d["plan"][m].sum()), 1),
            "ymin": round(float(d["ymin"][m].min()), 3), "ymax": round(float(d["ymax"][m].max()), 3),
            "area_w_p5_p50_p95": [round(v, 2) for v in wpct(d["yc"][m], d["plan"][m], (5, 50, 95))],
            "foot_legal": t in FOOT_OK}
    fl = up & np.isin(topo, list(FOOT_OK))
    i = np.where(fl)[0][np.argmax(d["ymax"][fl])]
    rd["foot_legal_highest"] = {"ymax": float(d["ymax"][i]), "block": [int(d["bx"][i]), int(d["by"][i])],
                                "topo": int(topo[i]), "world_xz": [float(d["topx"][i]), float(d["topz"][i])]}
    j = np.where(fl)[0][np.argmin(d["ymin"][fl])]
    rd["foot_legal_lowest"] = {"ymin": float(d["ymin"][j]), "block": [int(d["bx"][j]), int(d["by"][j])],
                               "topo": int(topo[j]), "world_xz": [float(d["cx"][j]), float(d["cz"][j])]}
    rd["terrain_plan_area_above"] = {}
    for name, th in THRESH.items():
        m_all = mt & (d["ymax"] > th)
        m_up = up & (d["yc"] > th)
        rd["terrain_plan_area_above"][name] = {
            "tris_any_vertex_above": int(m_all.sum()), "upfacing_centroid_above_plan_area": round(float(d["plan"][m_up].sum()), 1),
            "blocks": sorted({(int(x), int(y)) for x, y in zip(d["bx"][m_all], d["by"][m_all])})}
    # object vs thresholds
    if "object" in parts:
        po = d["part"] == parts.index("object")
        rd["object_above"] = {name: sorted({(int(x), int(y)) for x, y in zip(d["bx"][po & (d["ymax"] > th)],
                                                                           d["by"][po & (d["ymax"] > th)])})
                              for name, th in THRESH.items()}
    # all-part global max
    rd["global_max_any_part"] = {p: v["vert_y_max"] for p, v in rd["parts"].items()}
    # topo presence over EVERY walkmesh part (flight/camera casts see all of them) vs the engine's
    # flight-blocked set (engine_bounds.py: topos absent from the airship limit mask)
    eb = json.loads((OUT / "engine_bounds.json").read_text())["derived"]
    present = Counter(int(t) for t in topo)
    rd["topo_presence_all_parts"] = dict(sorted(present.items()))
    rd["flight_blocked_topos_present"] = {t: present[t] for t in eb["flight_blocked_topos"] if present.get(t)}

# ---- CALIBRATION gate (prior recorded values) ------------------------------------------------------------
# The recorded figures come from studies/overworld-topography/census.py, whose per-topo "h_lo/h_hi" are the
# UNWEIGHTED p2 / p98 of TRI-CENTROID y over ALL terrain tris of the topo (census.py:118-121), disc 1. We
# reproduce THAT statistic from our own cache first (instrument agreement), and only then report the
# vertex extremes, which are a different (stricter) measure.
cal = {}
d1 = extract(1)
p1 = list(d1["parts"])
mt1 = d1["part"] == p1.index("terrain")
topo1 = (d1["idall"] & 0xFC) >> 2
for t, lo_hi, want, tol in ((49, "p98", 37.0, 1.0), (5, "p2", -3.6, 0.5)):
    m = mt1 & (topo1 == t)
    v = float(np.percentile(d1["yc"][m], 98 if lo_hi == "p98" else 2))
    cal[f"census.py-equivalent topo{t} {lo_hi} (recorded ~{want})"] = (abs(v - want) <= tol, round(v, 2))
# terrace law (recorded: plateau grass 10/11/12 h~27; terrace shelf 13 h~17) -- median centroid
for t, want in ((10, 27.0), (13, 17.0)):
    m = mt1 & (topo1 == t)
    v = float(np.median(d1["yc"][m]))
    cal[f"topo{t} median centroid (recorded ~{want})"] = (abs(v - want) <= 1.5, round(v, 2))
# sea4 flat: the recorded claim was measured on donor rect (6,6)+2x2 (sea-sheet laws) -- reproduce locally
vs1 = d1["vstats"]
pi4 = p1.index("sea4")
rect = [(x, y) for x in (6, 7) for y in (6, 7)]
loc = vs1[(vs1[:, 0] == pi4) & np.isin(vs1[:, 1] * 100 + vs1[:, 2], [x * 100 + y for x, y in rect])]
cal["sea4 rect (6,6)+2x2 all y==0 (recorded: 3075 verts at 0.000)"] = (
    bool(loc[:, 4].sum() == loc[:, 3].sum()), f"{int(loc[:, 4].sum())}/{int(loc[:, 3].sum())} verts")
print("\nCALIBRATION vs recorded memory values (instrument agreement on the SAME statistic):")
for k, (ok, v) in cal.items():
    print(f"  {'PASS' if ok else 'FAIL'}  {k}: measured {v}")

# ---- print -------------------------------------------------------------------------------------------------
for disc in (1, 4):
    rd = R[disc]
    print(f"\n================ DISC {disc} ================")
    print(f"{'part':14s} {'blk':>4s} {'tris':>7s} {'vmin':>8s} {'vmax':>8s} | tri-ymax p1/p50/p99 | area-w centroid p1/p50/p99 | %y==0")
    for p, v in sorted(rd["parts"].items(), key=lambda kv: -kv[1]["vert_y_max"]):
        a = v["tri_ymax_pcts_1_5_50_95_99"]
        w = v["area_w_centroid_pcts_1_5_50_95_99"]
        print(f"{p:14s} {v['blocks']:4d} {v['tris']:7d} {v['vert_y_min']:8.3f} {v['vert_y_max']:8.3f} |"
              f" {a[0]:6.2f} {a[2]:6.2f} {a[4]:6.2f} | {w[0]:6.2f} {w[2]:6.2f} {w[4]:6.2f} | {100 * v['frac_verts_exact_zero']:5.1f}")
    print("tallest TERRAIN blocks (block ymax topo world_xz):")
    for r in rd["tallest_terrain"][:12]:
        print(f"   {r['block']} {r['ymax']:7.3f} topo {r['topo']:2d} ny {r['ny']:+.2f} at {r['world_xz']}")
    if "tallest_object" in rd:
        print("tallest OBJECT blocks:")
        for r in rd["tallest_object"][:10]:
            print(f"   {r['block']} {r['ymax']:7.3f} topo {r['topo']:2d} at {r['world_xz']}")
    print("terrain block-max histogram (5u bins):", dict(sorted(rd["terrain_blocks_ymax_hist"].items())))
    print("foot-legal highest:", rd["foot_legal_highest"])
    print("foot-legal lowest:", rd["foot_legal_lowest"])
    print("terrain below zero:", {k: v for k, v in rd["terrain_below_zero"].items() if k != "blocks"})
    print("   blocks:", rd["terrain_below_zero"]["blocks"])
    print("above thresholds:")
    for k, v in rd["terrain_plan_area_above"].items():
        print(f"   {k}: tris(any vertex) {v['tris_any_vertex_above']}, up-facing plan area {v['upfacing_centroid_above_plan_area']}, blocks {v['blocks'][:12]}")
    if "object_above" in rd:
        print("object blocks above thresholds:", rd["object_above"])
    print("topo presence (all parts):", rd["topo_presence_all_parts"])
    print("FLIGHT-BLOCKED topos present anywhere:", rd["flight_blocked_topos_present"] or "NONE")
    print("per-topo (up-facing terrain): topo tris area ymin ymax p5/p50/p95 foot")
    for t, v in rd["topo_heights"].items():
        print(f"   {t:2d} {v['tris']:6d} {v['plan_area']:9.1f} {v['ymin']:7.2f} {v['ymax']:7.2f} {v['area_w_p5_p50_p95']} {'F' if v['foot_legal'] else '-'}")


def _js(o):
    if isinstance(o, dict):
        return {str(k): _js(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_js(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    return o


(OUT / "y_census.json").write_text(json.dumps(_js({"calibration": cal, "discs": R}), indent=1))
print("\nwrote", OUT / "y_census.json")
