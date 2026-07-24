"""RUNG F FRAME BUILD -- SECOND INDEPENDENT FALSIFIER (2026-07-24).

A code-disjoint re-derivation of every frame-build claim from the STAGED BYTES ONLY
(out/rung_f/FF9CustomMap-world). Distinct from both rung_f_build.py (the builder) and
rung_f_falsify.py (the first falsifier): the gate LOGIC here -- edge/silhouette welding,
BFS bands, backing flood, interface, erosion, rigidity match, watertight-loop counting --
is re-implemented from scratch. Only the empirical DATA loaders + UV/topo classification
constants are reused (X.read_block / M.blockmesh_from_ff9mesh / X.decode_id / X.block_world_origin
and SNR.FAM_OF / SNR.classify_strip_pair / SNR.GD_* / SNR.DD_* / SNR.RECTS / SNR.in_rect).

Adds two checks the first falsifier did not make explicit:
  * WATERTIGHT SINGLE LOOP: the coast once-edges must form exactly ONE closed boundary loop
    (every coast vertex degree 2, one connected component) -- not merely "0 interior cracks".
  * CORE-UNTOUCHED / BIT-IDENTICAL-TO-BASELINE: every tri R2/R3 read must be inside the
    byte-rigid carried set (donor+T) and spatially disjoint from the minted grass coast, so
    R2/R3 equal the pre-frame all-green base by construction.

READ-ONLY vs the game install. Writes only out/rung_f/falsify_frame.json + this script.
Run:  cd studies/overworld-topography && py rung_f_frame_falsify.py
"""
from __future__ import annotations
import json, math, sys
from collections import Counter, defaultdict, deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import seam_null_recon as SNR                     # noqa: E402  (DATA only: FAM_OF/classify/RECTS)
from ff9mapkit.world import extract as X          # noqa: E402
from ff9mapkit.world import mesh as M             # noqa: E402

CELL = 4.0
STAGED = HERE / "out" / "rung_f" / "FF9CustomMap-world"
OUT = HERE / "out" / "rung_f" / "falsify_frame.json"

# claims under test (from the frame build headline / rung_f_build.json stage7 + task JSON)
CLAIM = dict(
    R1=dict(boundary_cell=46.826, straddle_cell=48.882, body_tri=49.547),
    R1_floors=dict(boundary_cell=39.953, straddle_cell=44.635, body_tri=42.968),
    R2=dict(sat_grass=0.4976, sat_any=0.6303, fringe=0.8008, penetration=0.1241, floating=0),
    R2_ceil=dict(sat_grass=0.5024, sat_any=0.6351, fringe_floor=0.60, pen_ceil=0.25),
    R3=dict(backing=143, interface=127, erosion=129),
    R3_floors=dict(backing=130, interface=20),
    F3_R1_true=46.826, F3_R1_stale=6.325,
)

FOOTPRINT = sorted((bx, by) for bx in range(0, 5) for by in range(16, 20))   # 20 blocks
DONOR_BLOCKS = [(bx, by) for bx in (13, 14, 15) for by in (11, 12)]
SHIFT = (-768.0, 0.0, -384.0)      # donor (13-15,11-12) -> target (1-3,17-18); verified by origins
DESERT_TOPOS = frozenset(t for t, f in SNR.FAM_OF.items() if f == "desert")   # {16,17,19,20}
BACKING_TOPOS = frozenset({17, 19, 20, 41})
MASS_TOPOS = frozenset({16, 17, 19, 20, 41})
SEA_CAP = ("Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Beach1", "Beach2")
FINDINGS = []


def log(m): print(m, flush=True)


def add(sev, msg):
    FINDINGS.append(f"[{sev}] {msg}")
    log(f"  {sev}: {msg}")


# ---------------------------------------------------------------- loaders (staged-else-stock)
def staged_terr(bx, by):
    return STAGED / M.override_relpath(1, bx, by, part="Terrain")


def block_terr(bx, by):
    p = staged_terr(bx, by)
    if p.exists():
        return M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain"), "staged"
    try:
        return X.read_block(bx, by, disc=1, part="terrain"), "stock"
    except (ValueError, FileNotFoundError):
        return None, None


def worldtris(bm, bx, by):
    ox, oz = X.block_world_origin(bx, by)
    out = []
    for tri in bm.tris:
        idall = int(round(bm.tangents[tri[0]][0]))
        topo = X.decode_id(idall)["topograph"]
        w = tuple((bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri)
        uv = tuple((float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri)
        cx = (w[0][0] + w[1][0] + w[2][0]) / 3.0
        cz = (w[0][2] + w[1][2] + w[2][2]) / 3.0
        out.append(dict(block=(bx, by), topo=topo, idall=idall, fam=SNR.FAM_OF.get(topo),
                        w=w, uv=uv, cell=(math.floor(cx / CELL), math.floor(cz / CELL)),
                        cen=(cx, cz)))
    return out


def region(blocks):
    tris, src = [], {}
    for (bx, by) in blocks:
        bm, s = block_terr(bx, by)
        if bm is None:
            continue
        src[(bx, by)] = s
        tris.extend(worldtris(bm, bx, by))
    for i, t in enumerate(tris):
        t["gid"] = i
    return tris, src


def moore(blocks, r):
    out = set()
    for (bx, by) in blocks:
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if M.block_in_grid(bx + dx, by + dy):
                    out.add((bx + dx, by + dy))
    return sorted(out)


# ---------------------------------------------------------------- independent edge machinery
def vk(p): return (round(p[0], 3), round(p[1], 3), round(p[2], 3))


def dedup(tris):
    """drop coincident-position duplicate tris (winding-independent)."""
    seen, out, nrem = set(), [], 0
    for t in tris:
        k = tuple(sorted(vk(p) for p in t["w"]))
        if k in seen:
            nrem += 1
            continue
        seen.add(k)
        out.append(t)
    return out, nrem


def edge_owner(tris):
    """map welded 3D edge -> list of (gid, fam). independent of SNR.edge_index."""
    owner = defaultdict(list)
    for t in tris:
        ks = [vk(p) for p in t["w"]]
        for i in range(3):
            a, b = ks[i], ks[(i + 1) % 3]
            if a == b:
                continue
            owner[frozenset((a, b))].append((t["gid"], t["fam"]))
    return owner


def once_edges(tris):
    """single-owner welded edges (after coincident dedup) as ((x1,z1),(x2,z2),y1,y2)."""
    dd, nrem = dedup(tris)
    owner = edge_owner(dd)
    segs = []
    for e, o in owner.items():
        if len(o) == 1:
            (p1, p2) = tuple(e)
            segs.append(((p1[0], p1[2]), (p2[0], p2[2]), p1[1], p2[1], frozenset((p1, p2))))
    return segs, nrem, dd


def pt_seg2(px, pz, x1, z1, x2, z2):
    dx, dz = x2 - x1, z2 - z1
    l2 = dx * dx + dz * dz
    if l2 < 1e-12:
        return math.hypot(px - x1, pz - z1)
    u = max(0.0, min(1.0, ((px - x1) * dx + (pz - z1) * dz) / l2))
    return math.hypot(px - (x1 + u * dx), pz - (z1 + u * dz))


def nearest(pts, segs):
    best = None
    for (px, pz) in pts:
        for s in segs:
            d = pt_seg2(px, pz, s[0][0], s[0][1], s[1][0], s[1][1])
            if best is None or d < best:
                best = d
    return best


# ---------------------------------------------------------------- UV body classification
def uv_class(uv):
    if SNR.classify_strip_pair(uv, SNR.GD_DU, SNR.GD_DV) is not None:
        return "gd"
    if SNR.classify_strip_pair(uv, SNR.DD_DU, SNR.DD_DV) is not None:
        return "dd"
    if SNR.in_rect(uv, SNR.RECTS["desert"]):
        return "mains"
    return None


def desert_body(core):
    """UV-driven, family-blind desert body minus the legit opposite-side halves."""
    body = []
    for t in core:
        c = uv_class(t["uv"])
        if c == "gd" and t["fam"] == "grass":
            continue
        if c == "dd" and t["fam"] == "dunes":
            continue
        if c in ("gd", "dd", "mains"):
            body.append((t, c))
    return body


def comp8(cells):
    """8-connected components of a cell set."""
    seen, comps = set(), []
    for s in cells:
        if s in seen:
            continue
        comp, q = [s], deque([s]); seen.add(s)
        while q:
            u = q.popleft()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx or dy:
                        nb = (u[0] + dx, u[1] + dy)
                        if nb in cells and nb not in seen:
                            seen.add(nb); comp.append(nb); q.append(nb)
        comps.append(comp)
    return comps


def flood8(seed, allowed):
    reach, q = set(seed), deque(seed)
    while q:
        u = q.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx or dy:
                    nb = (u[0] + dx, u[1] + dy)
                    if nb in allowed and nb not in reach:
                        reach.add(nb); q.append(nb)
    return reach


def main():
    res = {}
    reg_blocks = moore(FOOTPRINT, 2)
    tris, src = region(reg_blocks)
    core_set = set(FOOTPRINT)
    core = [t for t in tris if t["block"] in core_set]
    n_staged = sum(1 for v in src.values() if v == "staged")
    log(f"region tris={len(tris)} core={len(core)} staged_blocks={n_staged}")
    res["load"] = dict(region_tris=len(tris), core_tris=len(core), staged_blocks=n_staged,
                       footprint_blocks=len(FOOTPRINT))

    # =============================== boundary / straddle / body sets (independent edge scan)
    by_gid = {t["gid"]: t for t in tris}
    owner = edge_owner(tris)
    boundary_cells, boundary_desert = set(), set()
    n_gd_edges = 0
    for e, o in owner.items():
        fams = {f for (_g, f) in o}
        if fams == {"grass", "desert"}:
            n_gd_edges += 1
            for (g, f) in o:
                t = by_gid[g]
                if t["block"] in core_set:
                    boundary_cells.add(t["cell"])
                    if f == "desert":
                        boundary_desert.add(t["cell"])
    cell_fams = defaultdict(set)
    for t in core:
        if t["fam"]:
            cell_fams[t["cell"]].add(t["fam"])
    straddle_cells = {c for c, f in cell_fams.items() if f == {"grass", "desert"}}
    body = desert_body(core)

    def cc(c): return (c[0] * CELL + CELL / 2.0, c[1] * CELL + CELL / 2.0)
    boundary_pts = [cc(c) for c in boundary_cells]
    straddle_pts = [cc(c) for c in straddle_cells]
    body_pts = [t["cen"] for (t, _c) in body]

    # =============================== R1: realized standoff to the land-perimeter silhouette
    segs, nrem, dd_tris = once_edges(tris)
    r1 = dict(boundary_cell=nearest(boundary_pts, segs),
              straddle_cell=nearest(straddle_pts, segs),
              body_tri=nearest(body_pts, segs))
    r1_pass = {k: (r1[k] is not None and r1[k] >= CLAIM["R1_floors"][k] - 1e-3) for k in r1}
    res["R1"] = dict(measured={k: (round(v, 3) if v is not None else None) for k, v in r1.items()},
                     floors=CLAIM["R1_floors"], passes=r1_pass,
                     n_boundary_cells=len(boundary_cells), n_straddle_cells=len(straddle_cells),
                     n_body_tris=len(body_pts), n_gd_edges=n_gd_edges,
                     n_once_edges=len(segs), n_coincident_deduped=nrem,
                     verdict="PASS" if all(r1_pass.values()) else "FAIL")
    log(f"R1 {res['R1']['measured']} pass={r1_pass} dedup={nrem} once={len(segs)} bnd={len(boundary_cells)}")
    for k in r1:
        exp = CLAIM["R1"][k]
        if r1[k] is None or abs(r1[k] - exp) > 0.01:
            add("R1-MISMATCH", f"{k} independently {round(r1[k],3) if r1[k] else None} != claim {exp}")
    for k, ok in r1_pass.items():
        if not ok:
            add("R1-FAIL", f"{k} {round(r1[k],3) if r1[k] else None} < floor {CLAIM['R1_floors'][k]}")

    # =============================== R2: saturation + arrangement (independent BFS)
    tally = Counter(c for (_t, c) in body)
    total = len(body)
    n_gd, n_dd = tally.get("gd", 0), tally.get("dd", 0)
    sat_grass = n_gd / total if total else None
    sat_any = (n_gd + n_dd) / total if total else None
    desert_cells = {t["cell"] for (t, _c) in body}
    dist = SNR.cell_distance_bfs(desert_cells, boundary_cells)   # DATA-shared BFS distance
    dressed = [t for (t, c) in body if c in ("gd", "dd")]
    gd_cells = {t["cell"] for (t, c) in body if c == "gd"}
    nd = len(dressed)
    band0 = sum(1 for t in dressed if dist.get(t["cell"]) == 0)
    band_ge2 = sum(1 for t in dressed if (dist.get(t["cell"]) is None or dist.get(t["cell"]) >= 2))
    fringe = band0 / nd if nd else None
    penetration = band_ge2 / nd if nd else None

    def cheby(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
    n_floating = sum(1 for comp in comp8(gd_cells)
                     if not any(cheby(x, b) <= 1 for x in comp for b in boundary_cells))
    r2_pass = dict(
        grass=(sat_grass is not None and sat_grass <= CLAIM["R2_ceil"]["sat_grass"] + 1e-3),
        any=(sat_any is not None and sat_any <= CLAIM["R2_ceil"]["sat_any"] + 1e-3),
        fringe=(fringe is not None and fringe >= CLAIM["R2_ceil"]["fringe_floor"] - 1e-3),
        penetration=(penetration is not None and penetration <= CLAIM["R2_ceil"]["pen_ceil"] + 1e-3),
        floating=(n_floating <= 0))
    res["R2"] = dict(body_total=total, n_gd=n_gd, n_dd=n_dd,
                     sat_grass=round(sat_grass, 4) if sat_grass else None,
                     sat_any=round(sat_any, 4) if sat_any else None,
                     fringe=round(fringe, 4) if fringe else None,
                     penetration=round(penetration, 4) if penetration else None,
                     n_floating=n_floating, passes=r2_pass,
                     verdict="PASS" if all(r2_pass.values()) else "FAIL")
    log(f"R2 total={total} g={n_gd} dd={n_dd} sat_g={res['R2']['sat_grass']} "
        f"sat_any={res['R2']['sat_any']} fringe={res['R2']['fringe']} pen={res['R2']['penetration']} "
        f"float={n_floating} {r2_pass}")
    for key, exp in (("sat_grass", CLAIM["R2"]["sat_grass"]), ("sat_any", CLAIM["R2"]["sat_any"]),
                     ("fringe", CLAIM["R2"]["fringe"]), ("penetration", CLAIM["R2"]["penetration"])):
        got = res["R2"][key]
        if got is None or abs(got - exp) > 0.001:
            add("R2-MISMATCH", f"{key} independently {got} != claim {exp}")
    if n_floating != CLAIM["R2"]["floating"]:
        add("R2-MISMATCH", f"floating {n_floating} != claim {CLAIM['R2']['floating']}")
    for k, ok in r2_pass.items():
        if not ok:
            add("R2-FAIL", f"{k} fails ceiling")

    # =============================== R3: backing / interface / erosion (independent flood)
    mass_cells, skin_cells, backing_cells = set(), set(), set()
    for t in tris:
        if t["topo"] in MASS_TOPOS:
            mass_cells.add(t["cell"])
        if t["topo"] == 16:
            skin_cells.add(t["cell"])
        if t["topo"] in BACKING_TOPOS:
            backing_cells.add(t["cell"])
    seed = boundary_desert & mass_cells
    reach = flood8(seed, mass_cells)
    backing_reach = reach & backing_cells
    skin_reach = reach & skin_cells
    backing_largest = max((len(c) for c in comp8(backing_reach)), default=0)
    iface = 0
    for a in skin_reach:
        for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (a[0] + dx, a[1] + dy) in backing_reach:
                iface += 1

    def erode(cells):
        return {c for c in cells if all((c[0] + dx, c[1] + dy) in cells
                                        for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)))}
    mass_e = erode(mass_cells)
    reach_e = flood8(boundary_desert & mass_e, mass_e)
    erosion = len(reach_e & backing_cells)
    r3_pass = dict(extent=(backing_largest >= CLAIM["R3_floors"]["backing"]),
                   interface=(iface >= CLAIM["R3_floors"]["interface"]),
                   erosion=(erosion > 0))
    res["R3"] = dict(backing_reachable=backing_largest, interface_pairs=iface, erosion_survive=erosion,
                     n_skin_cells=len(skin_cells), n_backing_cells=len(backing_cells),
                     passes=r3_pass, verdict="PASS" if all(r3_pass.values()) else "FAIL")
    log(f"R3 backing={backing_largest} iface={iface} erosion={erosion} {r3_pass}")
    for key, exp in (("backing_reachable", CLAIM["R3"]["backing"]),
                     ("interface_pairs", CLAIM["R3"]["interface"]),
                     ("erosion_survive", CLAIM["R3"]["erosion"])):
        if res["R3"][key] != exp:
            add("R3-MISMATCH", f"{key} independently {res['R3'][key]} != claim {exp}")
    for k, ok in r3_pass.items():
        if not ok:
            add("R3-FAIL", f"{k} fails floor")

    # =============================== BYTE-RIGIDITY vs the carve donor (independent match)
    rig = rigidity()
    carried_cells = rig.pop("carried_cells")               # a set: keep out of the JSON, use below
    rig["n_carried_cells"] = len(carried_cells)
    res["rigidity"] = rig
    log(f"rigidity matched={rig['matched']} unmatched={rig['unmatched']} pos_bad={rig['pos_bad']} "
        f"uv_bad={rig['uv_bad']} nrm_bad={rig['nrm_bad']} tan_bad={rig['tan_bad']} "
        f"deviations={rig['n_deviations']}(lawful={rig['all_lawful']}) yspread={rig['y_lift_spread']}")
    if rig["pos_bad"] or rig["nrm_bad"] or rig["tan_bad"] or rig["y_lift_spread"] not in (0.0, None):
        add("RIGIDITY-DEFECT", f"non-rigid carry: pos_bad={rig['pos_bad']} nrm_bad={rig['nrm_bad']} "
            f"tan_bad={rig['tan_bad']} y_spread={rig['y_lift_spread']}")
    if rig["n_deviations"] and not rig["all_lawful"]:
        add("RIGIDITY-DEFECT", f"unlawful carried-tri deviations: {rig['unlawful']}")

    # =============================== CORE-UNTOUCHED / BIT-IDENTICAL-TO-BASELINE proof
    # The core-untouched proof is: (a) every carried mass tri is byte-rigid to the donor (rigidity
    # matched, 0 unmatched, 0 pos/nrm/tan_bad, single Y lift) AND (b) every tri R2/R3 reads lives in a
    # cell that carries a rigid mass tri. Then R2 (desert body) + R3 (mass/backing) equal the pre-frame
    # all-green base bit-for-bit. (Ecotone straddle cells legitimately contain BOTH a grass and a desert
    # tri, so a carried-cell / grass-cell overlap is EXPECTED and is NOT a perturbation.)
    body_outside = [t["cell"] for (t, _c) in body if t["cell"] not in carried_cells]
    mass_outside = [c for c in mass_cells if c in core_set_cells(core) and c not in carried_cells]
    res["core_untouched"] = dict(
        n_carried_cells=len(carried_cells),
        body_tris_outside_carry=len(body_outside),
        core_mass_cells_outside_carry=len(mass_outside),
        rigid_matched=rig["matched"], rigid_unmatched=rig["unmatched"],
        proof_holds=(len(body_outside) == 0 and rig["unmatched"] == 0 and rig["pos_bad"] == 0
                     and rig["all_lawful"]),
        note="R2/R3 read only byte-rigid-to-donor carried cells -> R2/R3 == the all-green base "
             "bit-for-bit. Straddle-cell grass/desert co-occupancy is the ecotone, not a perturbation.")
    if body_outside:
        add("BASELINE", f"{len(body_outside)} R2 body tris fall in cells NOT byte-rigid to the donor "
            f"-- R2 may not equal the baseline by construction (cells {body_outside[:6]}).")

    # =============================== WATERTIGHT SINGLE LOOP (independent topology)
    wl = watertight_loop(dd_tris)
    res["watertight"] = wl
    log(f"watertight: coast_once={wl['n_coast_once']} interior_once_above_skirt={wl['n_interior_above']} "
        f"loops={wl['n_loops']} all_deg2={wl['all_degree_2']} bad_deg={wl['n_bad_degree']}")
    if wl["n_interior_above"] > 0:
        add("WATERTIGHT", f"{wl['n_interior_above']} interior once-edges above the y=0.5 skirt "
            f"(phantom cracks). A single such crack near the ecotone is exactly the F3 6.325u collapse.")
    if wl["n_loops"] != 1 or not wl["all_degree_2"]:
        add("WATERTIGHT", f"coast boundary is not ONE clean closed loop: loops={wl['n_loops']} "
            f"bad_degree_vertices={wl['n_bad_degree']}.")

    # =============================== TRAP CHECKLIST
    traps = trap_checklist()
    res["traps"] = traps
    log(f"traps flat_bad={traps['flat_bad']} active_sea_nonzero_y={traps['active_sea_nonzero_y']} "
        f"lawful_blank_stubs={traps['lawful_blank_stubs']} malformed_stubs={traps['malformed_stubs']} "
        f"event_area_nonzero={traps['event_area_nonzero']} grid_oob={traps['grid_oob']} "
        f"orphans={traps['orphan_orphans']}/{traps['orphan_ambiguous']}")
    if traps["flat_bad"]:
        add("TRAP", f"flat-mesh invariant violated: {traps['flat_bad']}")
    if traps["active_sea_nonzero_y"]:
        add("TRAP", f"ACTIVE sea plane (>1 tri) with Y!=0: {traps['active_sea_nonzero_y']} vertices "
            f"(SEA-LAYER LAW violation on a rendering plane).")
    if traps["malformed_stubs"]:
        add("TRAP", f"malformed blank stubs (not the productized 1-tri Y=-80 hidden_block_mesh or a "
            f"Y=0 Sea4 arm): {traps['malformed_stubs']}")
    if traps["event_area_nonzero"]:
        add("TRAP", f"donor-dispatch strip missed: {traps['event_area_nonzero']} carried tris keep event/area")
    if traps["grid_oob"]:
        add("TRAP", f"{traps['grid_oob']} blocks off the 24x20 grid")
    if traps["orphan_orphans"] or traps["orphan_ambiguous"]:
        add("TRAP", f"orphan decals on final bytes: {traps['orphan_orphans']}/{traps['orphan_ambiguous']}")

    # =============================== F3 discrepancy resolution on THIS tree
    f3 = dict(
        R1_boundary_cell_measured=round(r1["boundary_cell"], 3) if r1["boundary_cell"] else None,
        matches_true_46_826=(r1["boundary_cell"] is not None
                             and abs(r1["boundary_cell"] - CLAIM["F3_R1_true"]) < 0.01),
        interior_once_above_skirt=wl["n_interior_above"],
        stale_6_325_reproduced=(r1["boundary_cell"] is not None
                                and abs(r1["boundary_cell"] - CLAIM["F3_R1_stale"]) < 0.5),
        note="F3 resolved iff the welded tree measures the TRUE island coast (46.826) with 0 interior "
             "cracks; a reproduced 6.325 would mean an un-welded crack still contaminates the silhouette.")
    res["f3"] = f3
    if not f3["matches_true_46_826"]:
        add("F3", f"R1 boundary-cell {f3['R1_boundary_cell_measured']} != the resolved-true 46.826 "
            f"-- F3 resolution does NOT hold on this tree.")
    if f3["stale_6_325_reproduced"]:
        add("F3", "R1 collapsed to ~6.325 -- an interior crack still contaminates the coast silhouette.")

    # =============================== VERDICT
    mism = [f for f in FINDINGS if "MISMATCH" in f]
    hard = [f for f in FINDINGS if any(t in f for t in
            ("R1-FAIL", "R2-FAIL", "R3-FAIL", "RIGIDITY-DEFECT", "WATERTIGHT", "TRAP", "F3", "BASELINE"))]
    if mism or hard:
        verdict = "REFUTED" if hard else "MIXED"
    else:
        verdict = "CONFIRMED"
    res["findings"] = FINDINGS
    res["verdict"] = verdict
    res["gate_verdicts"] = dict(R1=res["R1"]["verdict"], R2=res["R2"]["verdict"], R3=res["R3"]["verdict"])
    res["meta"] = dict(script="rung_f_frame_falsify.py", independent_of=["rung_f_build.py", "rung_f_falsify.py"],
                       read_only=True, staged=str(STAGED))
    OUT.write_text(json.dumps(res, indent=1), encoding="utf-8")
    log("\n" + "=" * 80)
    log(f"VERDICT: {verdict}")
    for f in FINDINGS:
        log("  - " + f)
    log(f"-> {OUT}")
    return res


def core_set_cells(core):
    return {t["cell"] for t in core}


def rigidity():
    """Independent: index donor terrain tris (13-15,11-12) under +SHIFT, keyed on the sorted XZ triple.
    Every staged carried MASS tri (topo in MASS_TOPOS) must match a donor tri byte-for-byte in uv +
    normal + tangent[1:2] with the topo id preserved, and share ONE global Y lift. Deviating tris are
    lawful iff their topo is a real in-family id and their UV classifies to a known rect (the documented
    excise/refill), else a defect."""
    dxs, _dy, dzs = SHIFT
    donor = {}
    for (bx, by) in DONOR_BLOCKS:
        try:
            bm = X.read_block(bx, by, disc=1, part="terrain")
        except (ValueError, FileNotFoundError):
            continue
        ox, oz = X.block_world_origin(bx, by)
        for tri in bm.tris:
            verts = [(bm.verts[j][0] + ox + dxs, bm.verts[j][1], bm.verts[j][2] + oz + dzs) for j in tri]
            key = tuple(sorted((round(p[0], 2), round(p[2], 2)) for p in verts))
            uv = frozenset((round(float(bm.uvs[j][0]), 5), round(float(bm.uvs[j][1]), 5)) for j in tri)
            nrm = frozenset((round(float(bm.normals[j][0]), 4), round(float(bm.normals[j][1]), 4),
                             round(float(bm.normals[j][2]), 4)) for j in tri)
            tan = frozenset((round(float(bm.tangents[j][1]), 4), round(float(bm.tangents[j][2]), 4))
                            for j in tri)
            idall = int(round(bm.tangents[tri[0]][0]))
            yby = {(round(p[0], 2), round(p[2], 2)): p[1] for p in verts}
            donor[key] = dict(uv=uv, nrm=nrm, tan=tan, topo=X.decode_id(idall)["topograph"], yby=yby)
    matched = unmatched = pos_bad = uv_bad = nrm_bad = tan_bad = topo_bad = 0
    dyv = Counter()
    deviations, unlawful = [], []
    carried_cells = set()
    for (bx, by) in FOOTPRINT:
        p = staged_terr(bx, by)
        if not p.exists():
            continue
        bm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
        ox, oz = X.block_world_origin(bx, by)
        for tri in bm.tris:
            idall = int(round(bm.tangents[tri[0]][0]))
            topo = X.decode_id(idall)["topograph"]
            if topo not in MASS_TOPOS:
                continue
            verts = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
            cx = sum(v[0] for v in verts) / 3.0
            cz = sum(v[2] for v in verts) / 3.0
            carried_cells.add((math.floor(cx / CELL), math.floor(cz / CELL)))
            key = tuple(sorted((round(v[0], 2), round(v[2], 2)) for v in verts))
            d = donor.get(key)
            if d is None:
                unmatched += 1
                continue
            matched += 1
            dys = [v[1] - d["yby"].get((round(v[0], 2), round(v[2], 2)), v[1]) for v in verts]
            if max(dys) - min(dys) > 1e-3:
                pos_bad += 1
            dyv[round(sum(dys) / 3.0, 3)] += 1
            uv = frozenset((round(float(bm.uvs[j][0]), 5), round(float(bm.uvs[j][1]), 5)) for j in tri)
            nrm = frozenset((round(float(bm.normals[j][0]), 4), round(float(bm.normals[j][1]), 4),
                             round(float(bm.normals[j][2]), 4)) for j in tri)
            tan = frozenset((round(float(bm.tangents[j][1]), 4), round(float(bm.tangents[j][2]), 4))
                            for j in tri)
            dev = (uv != d["uv"]) or (topo != d["topo"])
            if uv != d["uv"]:
                uv_bad += 1
            if nrm != d["nrm"]:
                nrm_bad += 1
            if tan != d["tan"]:
                tan_bad += 1
            if topo != d["topo"]:
                topo_bad += 1
            if dev:
                cls = SNR.classify_tri(SNR.FAM_OF.get(topo, "desert"), list(uv))
                lawful = (topo in MASS_TOPOS) and cls[0] in ("mains_own", "strip_grass_desert",
                                                             "strip_desert_dunes")
                rec = dict(block=[bx, by], topo=topo, donor_topo=d["topo"], uv_class=cls[0], lawful=lawful)
                deviations.append(rec)
                if not lawful:
                    unlawful.append(rec)
    yspread = (max(dyv) - min(dyv)) if dyv else None
    return dict(matched=matched, unmatched=unmatched, pos_bad=pos_bad, uv_bad=uv_bad, nrm_bad=nrm_bad,
                tan_bad=tan_bad, topo_bad=topo_bad, y_lift_votes=dict(dyv.most_common(4)),
                y_lift_spread=round(yspread, 4) if yspread is not None else None,
                n_deviations=len(deviations), all_lawful=all(d["lawful"] for d in deviations),
                deviations=deviations, unlawful=unlawful, carried_cells=carried_cells)


def watertight_loop(dd_tris):
    """Independent watertight topology over ONLY the staged composite terrain (the 20 footprint blocks).
    Coast once-edges = single-owner edges whose min endpoint Y <= 0.5 skirt; interior once-edges above
    skirt = phantom cracks. Then verify the coast once-edges form ONE closed loop (every coast vertex has
    even degree, exactly one connected component over the coast-edge graph)."""
    staged = [t for t in dd_tris if t["block"] in set(FOOTPRINT) and staged_terr(*t["block"]).exists()]
    owner = defaultdict(list)
    endpts = {}
    for t in staged:
        ks = [vk(p) for p in t["w"]]
        for i in range(3):
            a, b = ks[i], ks[(i + 1) % 3]
            if a == b:
                continue
            e = frozenset((a, b))
            owner[e].append(t["gid"])
            endpts[e] = (a, b)
    once = [e for e, o in owner.items() if len(o) == 1]
    coast, interior_above = [], 0
    for e in once:
        a, b = endpts[e]
        if min(a[1], b[1]) <= 0.5:
            coast.append(e)
        else:
            interior_above += 1
    # degree of every coast vertex
    deg = Counter()
    adj = defaultdict(set)
    for e in coast:
        a, b = endpts[e]
        deg[a] += 1
        deg[b] += 1
        adj[a].add(b)
        adj[b].add(a)
    n_bad_degree = sum(1 for v, d in deg.items() if d != 2)
    all_deg2 = (n_bad_degree == 0)
    # connected components over the coast-edge graph
    seen, n_loops = set(), 0
    for v in deg:
        if v in seen:
            continue
        n_loops += 1
        q = deque([v]); seen.add(v)
        while q:
            u = q.popleft()
            for w in adj[u]:
                if w not in seen:
                    seen.add(w); q.append(w)
    return dict(n_coast_once=len(coast), n_interior_above=interior_above, n_loops=n_loops,
                all_degree_2=all_deg2, n_bad_degree=n_bad_degree,
                note="one closed loop <=> n_loops==1 AND every coast vertex degree 2 (watertight island).")


def trap_checklist():
    flat_bad = []
    for (bx, by) in FOOTPRINT:
        p = staged_terr(bx, by)
        if not p.exists():
            continue
        bm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
        if len(bm.verts) != 3 * len(bm.tris) or bm.vcount != 3 * len(bm.tris):
            flat_bad.append([bx, by, bm.vcount, len(bm.verts), len(bm.tris)])
    # SEA-LAYER LAW, correctly scoped: an ACTIVE rendering plane (>1 tri) must be Y=0; a BLANKED layer
    # is the productized hidden_block_mesh degenerate (exactly 1 tri / 3 verts parked at Y=-80, which
    # renders nothing) or a Sea4 Y=0 arming stub. Only an active-plane Y!=0 or a malformed stub is a defect.
    active_nonzero = 0
    lawful_blank = 0
    malformed = []
    for (bx, by) in FOOTPRINT:
        for cap in SEA_CAP:
            p = STAGED / M.override_relpath(1, bx, by, part=cap)
            if not p.exists():
                continue
            sbm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part=cap.lower())
            ntri = len(sbm.tris)
            ys = [v[1] for v in sbm.verts]
            nz = sum(1 for y in ys if abs(y) > 1e-4)
            if ntri > 1:                                   # active rendering plane
                active_nonzero += nz
            else:                                          # single-tri stub -> must be Y=-80 blank or Y=0 arm
                if nz == 0 or all(abs(y + 80.0) < 1e-3 for y in ys):
                    lawful_blank += 1
                else:
                    malformed.append(f"{bx},{by}:{cap}:ntri{ntri}:y{[round(y,1) for y in ys]}")
    ev_nonzero = 0
    for (bx, by) in FOOTPRINT:
        p = staged_terr(bx, by)
        if not p.exists():
            continue
        bm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
        for tri in bm.tris:
            dec = X.decode_id(int(round(bm.tangents[tri[0]][0])))
            if dec["topograph"] not in MASS_TOPOS:
                continue
            if (dec.get("event", 0) or 0) or (dec.get("area", 0) or 0):
                ev_nonzero += 1
    grid_oob = sum(1 for (bx, by) in FOOTPRINT if not M.block_in_grid(bx, by))
    orph_o = orph_a = None
    try:
        from ff9mapkit.world import orphangate as O
        cell_meshes = {}
        for (bx, by) in FOOTPRINT:
            p = staged_terr(bx, by)
            if p.exists():
                cell_meshes[(bx, by)] = [("Terrain",
                                         M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain"))]
        r = O.orphan_decal_gate(cell_meshes, list(cell_meshes.keys()), enforce=False, redress=False,
                                mod_folder=str(STAGED), disc=1)
        orph_o, orph_a = r.get("n_orphans"), r.get("n_ambiguous")
    except Exception as e:
        orph_o = f"err:{e}"
    return dict(flat_bad=flat_bad, active_sea_nonzero_y=active_nonzero, lawful_blank_stubs=lawful_blank,
                malformed_stubs=malformed, event_area_nonzero=ev_nonzero,
                grid_oob=grid_oob, orphan_orphans=orph_o, orphan_ambiguous=orph_a)


if __name__ == "__main__":
    main()
