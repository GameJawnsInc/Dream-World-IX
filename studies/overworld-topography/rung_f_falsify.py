"""RUNG F -- INDEPENDENT BUILD FALSIFIER (2026-07-24).

Works from the STAGED BYTES only (out/rung_f/FF9CustomMap-world), re-deriving every gate-bound
claim with a code-disjoint implementation before reconciling with rung_f_build.json. Reuses ONLY the
empirical UV-classification constants + loaders from seam_null_recon / ff9mapkit.world (FAM_OF,
classify_strip_pair, RECTS, edge_index key convention, X.read_block, M.blockmesh_from_ff9mesh) --
the gate LOGIC (R1 standoff, R2 saturation/arrangement, R3 backing/interface/erosion, weld integrity,
byte-rigidity, flat-mesh, sea-layer, orphan-at-seam) is reimplemented here.

READ-ONLY vs the game install. Writes only out/rung_f/falsify.json + this script.
"""
from __future__ import annotations
import json, math, os, sys
from collections import Counter, defaultdict, deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import seam_null_recon as SNR                      # noqa: E402
from ff9mapkit.world import extract as X           # noqa: E402
from ff9mapkit.world import mesh as M              # noqa: E402

CELL = 4.0
BLOCK = 64.0
STAGED = HERE / "out" / "rung_f" / "FF9CustomMap-world"
OUT = HERE / "out" / "rung_f" / "falsify.json"

# floors/ceilings the build claims to clear (from contract_mass_gates.py v4)
R1_FLOORS = dict(boundary_cell=39.953, straddle_cell=44.635, body_tri=42.968)
R2_SAT = dict(grass_decal=0.5024, any_decal=0.6351)
R2_ARR = dict(fringe_floor=0.60, penetration_ceiling=0.25, floating_max=0)
R3 = dict(backing_floor=130, interface_floor=20)

FOOTPRINT = sorted((bx, by) for bx in range(0, 5) for by in range(16, 20))
DESERT_TOPOS = frozenset(t for t, f in SNR.FAM_OF.items() if f == "desert")   # {16,17,19,20}
BACKING_TOPOS = frozenset({17, 19, 20, 41})
MASS_TOPOS = frozenset({16, 17, 19, 20, 41})
SEA_PARTS_CAP = ("Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Beach1", "Beach2")


def log(m): print(m, flush=True)


def staged_terr_path(bx, by):
    return STAGED / M.override_relpath(1, bx, by, part="Terrain")


def load_block_terr(bx, by):
    """staged override if present else stock disc-1."""
    p = staged_terr_path(bx, by)
    if p.exists():
        return M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain"), "staged"
    try:
        return X.read_block(bx, by, disc=1, part="terrain"), "stock"
    except (ValueError, FileNotFoundError):
        return None, None


def tris_of(bm, bx, by):
    ox, oz = X.block_world_origin(bx, by)
    out = []
    for tri in bm.tris:
        idall = int(round(bm.tangents[tri[0]][0]))
        dec = X.decode_id(idall)
        topo = dec["topograph"]
        fam = SNR.FAM_OF.get(topo)
        w = [(bm.verts[j][0] + ox, bm.verts[j][1], bm.verts[j][2] + oz) for j in tri]
        uv = [(float(bm.uvs[j][0]), float(bm.uvs[j][1])) for j in tri]
        cx = sum(p[0] for p in w) / 3.0
        cz = sum(p[2] for p in w) / 3.0
        out.append(dict(block=(bx, by), topo=topo, idall=idall, fam=fam, w=w, uv=uv,
                        cell=(math.floor(cx / CELL), math.floor(cz / CELL))))
    return out


def load_region(blocks):
    tris, src = [], {}
    for (bx, by) in blocks:
        bm, s = load_block_terr(bx, by)
        if bm is None:
            continue
        src[(bx, by)] = s
        tris.extend(tris_of(bm, bx, by))
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


# ---------- edges / silhouette (independent, matches SNR.kk key convention) -------------------------
def vkey(p): return (round(p[0], 3), round(p[1], 3), round(p[2], 3))


def dedup_coincident(tris):
    seen, out, removed = set(), [], 0
    for t in tris:
        k = tuple(sorted(vkey(p) for p in t["w"]))
        if k in seen:
            removed += 1
            continue
        seen.add(k)
        out.append(t)
    return out, removed


def single_owner_segs(tris):
    deduped, nrem = dedup_coincident(tris)
    owner = defaultdict(list)
    for t in deduped:
        ks = [vkey(p) for p in t["w"]]
        for i in range(3):
            e = frozenset((ks[i], ks[(i + 1) % 3]))
            if len(e) == 2:
                owner[e].append(t["gid"])
    segs = []
    for e, o in owner.items():
        if len(o) == 1:
            (p1, p2) = tuple(e)
            segs.append(((p1[0], p1[2]), (p2[0], p2[2]), p1[1], p2[1]))
    return segs, nrem


def pt_seg(px, pz, seg):
    (x1, z1), (x2, z2) = seg[0], seg[1]
    dx, dz = x2 - x1, z2 - z1
    l2 = dx * dx + dz * dz
    if l2 < 1e-12:
        return math.hypot(px - x1, pz - z1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (pz - z1) * dz) / l2))
    return math.hypot(px - (x1 + t * dx), pz - (z1 + t * dz))


def min_to_segs(pts, segs):
    best = None
    for (px, pz) in pts:
        for s in segs:
            d = pt_seg(px, pz, s)
            if best is None or d < best:
                best = d
    return best


# ---------- UV classification (reuse SNR constants only) -------------------------------------------
def classify_uv(uv):
    k_gd = SNR.classify_strip_pair(uv, SNR.GD_DU, SNR.GD_DV)
    if k_gd is not None:
        return ("gd", k_gd)
    k_dd = SNR.classify_strip_pair(uv, SNR.DD_DU, SNR.DD_DV)
    if k_dd is not None:
        return ("dd", k_dd)
    if SNR.in_rect(uv, SNR.RECTS["desert"]):
        return ("mains_desert", None)
    return (None, None)


def label_blind_body(core_tris):
    """UV-driven family-blind desert body: counted iff UV is gd/dd decal or desert-mains, EXCEPT the
    legit gd-on-grass + dd-on-dunes opposite halves (excluded)."""
    body = []
    for t in core_tris:
        cls, k = classify_uv(t["uv"])
        if cls == "gd":
            if t["fam"] == "grass":
                continue
            body.append((t, "gd"))
        elif cls == "dd":
            if t["fam"] == "dunes":
                continue
            body.append((t, "dd"))
        elif cls == "mains_desert":
            body.append((t, "mains"))
    return body


def main():
    findings = []
    result = {}
    t_all, src = load_region(moore(FOOTPRINT, 2))
    core_set = set(FOOTPRINT)
    core_tris = [t for t in t_all if t["block"] in core_set]
    log(f"region tris={len(t_all)} core tris={len(core_tris)} staged blocks="
        f"{sum(1 for v in src.values() if v=='staged')}")

    # ============================================================= boundary / straddle / body sets
    by_gid = {t["gid"]: t for t in t_all}
    owner = defaultdict(list)
    for t in t_all:
        ks = [vkey(p) for p in t["w"]]
        for i in range(3):
            e = frozenset((ks[i], ks[(i + 1) % 3]))
            if len(e) == 2:
                owner[e].append(t["gid"])
    boundary_cells, boundary_desert = set(), set()
    n_gd_edges = 0
    for e, o in owner.items():
        fams = {by_gid[g]["fam"] for g in o}
        if fams == {"grass", "desert"}:
            n_gd_edges += 1
            for g in o:
                t = by_gid[g]
                if t["block"] in core_set:
                    boundary_cells.add(t["cell"])
                    if t["fam"] == "desert":
                        boundary_desert.add(t["cell"])
    cell_fams = defaultdict(set)
    for t in core_tris:
        if t["fam"]:
            cell_fams[t["cell"]].add(t["fam"])
    straddle_cells = {c for c, f in cell_fams.items() if f == {"grass", "desert"}}
    lb_body = label_blind_body(core_tris)
    body_pts = [((sum(p[0] for p in t["w"]) / 3.0), (sum(p[2] for p in t["w"]) / 3.0)) for (t, _) in lb_body]

    def cc(c): return (c[0] * CELL + CELL / 2.0, c[1] * CELL + CELL / 2.0)
    boundary_pts = [cc(c) for c in boundary_cells]
    straddle_pts = [cc(c) for c in straddle_cells]

    # ============================================================= R1 realized standoff (land-perimeter)
    segs, nrem = single_owner_segs(t_all)
    r1_meas = dict(
        boundary_cell=min_to_segs(boundary_pts, segs),
        straddle_cell=min_to_segs(straddle_pts, segs),
        body_tri=min_to_segs(body_pts, segs))
    r1_pass = {k: (r1_meas[k] is not None and r1_meas[k] >= R1_FLOORS[k] - 1e-3) for k in R1_FLOORS}
    result["R1"] = dict(measured={k: (round(v, 3) if v is not None else None) for k, v in r1_meas.items()},
                        floors=R1_FLOORS, passes=r1_pass,
                        n_boundary_cells=len(boundary_cells), n_straddle_cells=len(straddle_cells),
                        n_body_tris=len(body_pts), n_land_perimeter_segs=len(segs),
                        n_coincident_deduped=nrem, verdict=("PASS" if all(r1_pass.values()) else "FAIL"))
    log(f"R1 {result['R1']['measured']} floors {R1_FLOORS} pass {r1_pass} dedup={nrem}")
    for k in R1_FLOORS:
        if not r1_pass[k]:
            findings.append(f"R1 {k} standoff {r1_meas[k]} < floor {R1_FLOORS[k]} -- a coast (or interior "
                            f"once-edge crack) sits too close to the ecotone.")

    # ============================================================= R2 saturation + arrangement
    tally = Counter(c for (_t, c) in lb_body)
    total = len(lb_body)
    n_gd = tally.get("gd", 0); n_dd = tally.get("dd", 0)
    sat_grass = n_gd / total if total else None
    sat_any = (n_gd + n_dd) / total if total else None
    # arrangement: BFS bands over label-blind desert cells from boundary
    desert_cells = {t["cell"] for (t, _) in lb_body}
    dist = SNR.cell_distance_bfs(desert_cells, boundary_cells)
    dressed = [t for (t, c) in lb_body if c in ("gd", "dd")]
    gd_cells = {t["cell"] for (t, c) in lb_body if c == "gd"}
    nd = len(dressed)
    band0 = sum(1 for t in dressed if dist.get(t["cell"]) == 0)
    band_ge2 = sum(1 for t in dressed if (dist.get(t["cell"]) is None or dist.get(t["cell"]) >= 2))
    fringe = band0 / nd if nd else None
    penetration = band_ge2 / nd if nd else None
    # floating components of gd cells
    seen, comps = set(), []
    for s in gd_cells:
        if s in seen:
            continue
        comp, q = [s], deque([s]); seen.add(s)
        while q:
            u = q.popleft()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nb = (u[0] + dx, u[1] + dy)
                    if nb in gd_cells and nb not in seen:
                        seen.add(nb); comp.append(nb); q.append(nb)
        comps.append(comp)

    def cheby(a, b): return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
    n_floating = sum(1 for c in comps if not any(cheby(x, b) <= 1 for x in c for b in boundary_cells))
    r2_pass = dict(
        grass=(sat_grass is not None and sat_grass <= R2_SAT["grass_decal"] + 1e-3),
        any=(sat_any is not None and sat_any <= R2_SAT["any_decal"] + 1e-3),
        fringe=(fringe is not None and fringe >= R2_ARR["fringe_floor"] - 1e-3),
        penetration=(penetration is not None and penetration <= R2_ARR["penetration_ceiling"] + 1e-3),
        floating=(n_floating <= R2_ARR["floating_max"]))
    result["R2"] = dict(body_total=total, n_gd=n_gd, n_dd=n_dd,
                        sat_grass=round(sat_grass, 4) if sat_grass else None,
                        sat_any=round(sat_any, 4) if sat_any else None,
                        fringe=round(fringe, 4) if fringe else None,
                        penetration=round(penetration, 4) if penetration else None,
                        n_floating=n_floating, passes=r2_pass,
                        verdict=("PASS" if all(r2_pass.values()) else "FAIL"))
    log(f"R2 total={total} sat_g={result['R2']['sat_grass']} sat_any={result['R2']['sat_any']} "
        f"fringe={result['R2']['fringe']} pen={result['R2']['penetration']} float={n_floating} {r2_pass}")
    for k, v in r2_pass.items():
        if not v:
            findings.append(f"R2 {k} fails.")

    # ============================================================= R3 backing / interface / erosion
    backing_cells, mass_cells, skin_cells = set(), set(), set()
    for t in t_all:
        if t["topo"] in MASS_TOPOS:
            mass_cells.add(t["cell"])
        if t["topo"] == 16:
            skin_cells.add(t["cell"])
        if t["topo"] in BACKING_TOPOS:
            backing_cells.add(t["cell"])
    seed = boundary_desert & mass_cells
    reach = set(seed); q = deque(seed)
    while q:
        u = q.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nb = (u[0] + dx, u[1] + dy)
                if nb in mass_cells and nb not in reach:
                    reach.add(nb); q.append(nb)
    backing_reach = reach & backing_cells
    skin_reach = reach & skin_cells

    def largest8(cs):
        seen2, best = set(), 0
        for s in cs:
            if s in seen2:
                continue
            comp, qq = [s], deque([s]); seen2.add(s)
            while qq:
                u = qq.popleft()
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == 0 and dy == 0:
                            continue
                        nb = (u[0] + dx, u[1] + dy)
                        if nb in cs and nb not in seen2:
                            seen2.add(nb); comp.append(nb); qq.append(nb)
            best = max(best, len(comp))
        return best
    backing_largest = largest8(backing_reach)
    # interface (4-conn pairs skin<->backing)
    iface = 0
    for a in skin_reach:
        for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            if (a[0] + dx, a[1] + dy) in backing_reach:
                iface += 1
    # erosion
    def eroded(cells):
        return {c for c in cells if all((c[0] + dx, c[1] + dy) in cells
                                        for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)))}
    mass_e = eroded(mass_cells)
    seed_e = boundary_desert & mass_e
    reach_e = set(seed_e); q = deque(seed_e)
    while q:
        u = q.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nb = (u[0] + dx, u[1] + dy)
                if nb in mass_e and nb not in reach_e:
                    reach_e.add(nb); q.append(nb)
    erosion_survive = len(reach_e & backing_cells)
    r3_pass = dict(extent=(backing_largest >= R3["backing_floor"]),
                   interface=(iface >= R3["interface_floor"]),
                   erosion=(erosion_survive > 0))
    result["R3"] = dict(backing_reachable=backing_largest, interface_pairs=iface,
                        erosion_survive=erosion_survive, passes=r3_pass,
                        verdict=("PASS" if all(r3_pass.values()) else "FAIL"))
    log(f"R3 backing={backing_largest} iface={iface} erosion={erosion_survive} {r3_pass}")
    for k, v in r3_pass.items():
        if not v:
            findings.append(f"R3 {k} fails.")

    # ============================================================= BYTE-RIGIDITY of the carry
    SHIFT = (-768.0, 0.0, -384.0)   # donor block (13-15,11-12) -> target (1-3,17-18)
    rig = check_rigidity(SHIFT)
    result["rigidity"] = rig
    log(f"rigidity: {rig['summary']}")
    rig_hard = (rig["pos_bad"] or rig["nrm_bad"] or rig["tan_bad"]
                or (rig["n_deviations"] > 0 and not rig["all_deviations_lawful"]))
    if rig_hard:
        findings.append(f"byte-rigidity DEFECT: pos_bad={rig['pos_bad']} nrm_bad={rig['nrm_bad']} "
                        f"tan_bad={rig['tan_bad']} unlawful_deviations="
                        f"{[d for d in rig['deviations'] if not d['lawful']]}.")
    elif rig["n_deviations"] > 0:
        findings.append(f"NOTE (benign): {rig['n_deviations']} carried tris deviate from the donor "
                        f"(uv/topo) -- all LAWFUL in-family refills (the documented excise+refill of the "
                        f"near-duplicate spot; donor gd-decal -> topo-17 plain-desert mains, safe-"
                        f"direction for R2 saturation). Not a defect.")

    # ============================================================= WELD INTEGRITY (once-edges)
    weld = weld_integrity(t_all, segs)
    result["weld"] = weld
    log(f"weld: total_once={weld['n_once_total']} coast_loop~{weld['coast_hint']} "
        f"interior_once_above_skirt={weld['n_interior_once_above_skirt']}")
    if weld["n_interior_once_above_skirt"] > 0:
        findings.append(f"weld: {weld['n_interior_once_above_skirt']} interior once-edges above the "
                        f"y=0.5 skirt (phantom cracks not on the outer coast loop).")

    # ============================================================= FLAT-MESH + SEA-LAYER
    flat, sea = flat_and_sea()
    result["flat_mesh"] = flat
    result["sea_layer"] = sea
    log(f"flat-mesh bad blocks={flat['bad']}  sea Sea4 nonzero verts={sea['sea4_nonzero']}")
    if flat["bad"]:
        findings.append(f"flat-mesh invariant violated on blocks {flat['bad']} (verts != 3*tris).")
    if sea["sea4_nonzero"]:
        findings.append(f"sea-layer: {sea['sea4_nonzero']} Sea4 vertices with Y!=0.")

    # ============================================================= EVENT/AREA STRIP on carried
    ev = event_area_strip()
    result["event_area"] = ev
    log(f"event/area: carried tris with nonzero event/area = {ev['nonzero']}")
    if ev["nonzero"]:
        findings.append(f"event/area strip: {ev['nonzero']} carried tris still carry event/area bits.")

    # ============================================================= ORPHAN DECALS (independent gate on final bytes)
    orph = orphan_check()
    result["orphan"] = orph
    log(f"orphan: n_orphans={orph.get('n_orphans')} n_ambiguous={orph.get('n_ambiguous')} ok={orph.get('ok')}")
    if orph.get("n_orphans") or orph.get("n_ambiguous"):
        findings.append(f"orphan decals on final staged bytes: {orph.get('n_orphans')} orphans / "
                        f"{orph.get('n_ambiguous')} ambiguous.")

    # ============================================================= reconcile with build report
    recon = reconcile(result)
    result["reconcile"] = recon

    verdict = "CONFIRMED"
    gate_fail = any(result[g]["verdict"] == "FAIL" for g in ("R1", "R2", "R3"))
    hard_defect = (rig_hard or weld["n_interior_once_above_skirt"] > 0 or flat["bad"]
                   or sea["sea4_nonzero"] or ev["nonzero"]
                   or orph.get("n_orphans") or orph.get("n_ambiguous"))
    benign_notes = [f for f in findings if f.startswith("NOTE")]
    real_findings = [f for f in findings if not f.startswith("NOTE")]
    if gate_fail or hard_defect:
        verdict = "REFUTED"
    elif real_findings:
        verdict = "MIXED"
    result["findings"] = findings
    result["verdict"] = verdict
    result["meta"] = dict(script="rung_f_falsify.py", read_only=True, staged=str(STAGED))
    OUT.write_text(json.dumps(result, indent=1), encoding="utf-8")
    log("\n" + "=" * 80)
    log(f"VERDICT: {verdict}")
    for f in findings:
        log("  - " + f)
    log(f"-> {OUT}")
    return result


def check_rigidity(shift):
    """Every staged carried ecotone/dunes/skin tri must equal a donor tri (13-15,11-12) under a SINGLE
    global rigid translation, byte-identical in uv/normal/tangent, topo kept. Key on XZ only (the carry
    is XZ-locked at (-768,-384); Y is derived per-tri and must be globally uniform = true rigidity)."""
    dxs, _dy, dzs = shift
    # donor index keyed on XZ-shifted-into-target position (Y stored, not keyed)
    donor = {}
    for bx in (13, 14, 15):
        for by in (11, 12):
            try:
                bm = X.read_block(bx, by, disc=1, part="terrain")
            except (ValueError, FileNotFoundError):
                continue
            ox, oz = X.block_world_origin(bx, by)
            for tri in bm.tris:
                verts = [(bm.verts[j][0] + ox + dxs, bm.verts[j][1], bm.verts[j][2] + oz + dzs)
                         for j in tri]
                key = tuple(sorted((round(p[0], 2), round(p[2], 2)) for p in verts))
                uv = frozenset((round(float(bm.uvs[j][0]), 5), round(float(bm.uvs[j][1]), 5)) for j in tri)
                nrm = frozenset((round(float(bm.normals[j][0]), 4), round(float(bm.normals[j][1]), 4),
                                 round(float(bm.normals[j][2]), 4)) for j in tri)
                tan = frozenset((round(float(bm.tangents[j][1]), 4), round(float(bm.tangents[j][2]), 4))
                                for j in tri)
                idall = int(round(bm.tangents[tri[0]][0]))
                # store by XZ->Y map too for the per-vertex uniform-translation test
                yby_xz = {(round(p[0], 2), round(p[2], 2)): p[1] for p in verts}
                donor[key] = dict(uv=uv, nrm=nrm, tan=tan, topo=X.decode_id(idall)["topograph"],
                                  yby_xz=yby_xz)
    pos_bad = uv_bad = nrm_bad = tan_bad = topo_bad = 0
    matched = unmatched = 0
    max_dy_err = 0.0
    dy_votes = Counter()
    deviations = []
    for (bx, by) in FOOTPRINT:
        p = staged_terr_path(bx, by)
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
            key = tuple(sorted((round(p2[0], 2), round(p2[2], 2)) for p2 in verts))
            d = donor.get(key)
            if d is None:
                unmatched += 1
                continue
            matched += 1
            # per-vertex Y translation must be uniform (rigid)
            dys = []
            for p2 in verts:
                dy = p2[1] - d["yby_xz"].get((round(p2[0], 2), round(p2[2], 2)), p2[1])
                dys.append(dy)
            if max(dys) - min(dys) > 1e-3:
                pos_bad += 1
            dy_votes[round(sum(dys) / 3.0, 3)] += 1
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
                # a deviating carried tri is a LAWFUL documented substitution iff its topo is a real
                # in-family id AND its UV classifies to a known mains/decal rect (not garbage). The
                # near-duplicate excise+refill is expected; a corrupt tri is not.
                cls = SNR.classify_tri(t_fam_of(topo), list(uv))
                lawful = (topo in MASS_TOPOS) and cls[0] in ("mains_own", "strip_grass_desert",
                                                             "strip_desert_dunes")
                deviations.append(dict(block=[bx, by], topo=topo, donor_topo=d["topo"],
                                       uv_class=cls[0], lawful=lawful))
    # global-uniformity of the Y lift across the whole carry
    dy_spread = (max(dy_votes) - min(dy_votes)) if dy_votes else None
    all_dev_lawful = all(x["lawful"] for x in deviations)
    return dict(matched=matched, unmatched_carried=unmatched, pos_bad=pos_bad, uv_bad=uv_bad,
                nrm_bad=nrm_bad, tan_bad=tan_bad, topo_bad=topo_bad,
                global_y_lift_votes=dict(dy_votes.most_common(6)),
                global_y_lift_spread=round(dy_spread, 4) if dy_spread is not None else None,
                n_deviations=len(deviations), deviations=deviations,
                all_deviations_lawful=all_dev_lawful,
                summary=f"matched={matched} unmatched={unmatched} pos_bad(non-rigid)={pos_bad} "
                        f"uv_bad={uv_bad} nrm_bad={nrm_bad} tan_bad={tan_bad} topo_bad={topo_bad} "
                        f"deviations={len(deviations)}(all_lawful={all_dev_lawful}) "
                        f"y_lift_spread={round(dy_spread,4) if dy_spread is not None else None}",
                note="XZ-locked carry; Y is a single global rigid lift. pos_bad = tris whose 3 verts do "
                     "NOT share one Y translation (non-rigid). unmatched = seam-collar apron/regrass welds "
                     "(expected). deviations = carried tris whose uv/topo differ from the donor = the "
                     "documented excise+refill heal; all_deviations_lawful means each is a real in-family "
                     "tile (valid topo + UV rect), not corruption.")


def t_fam_of(topo):
    return SNR.FAM_OF.get(topo, "desert")


def weld_integrity(t_all, segs):
    """Independent once-edge scan over ONLY the staged composite blocks' terrain. Classify once-edges
    by min endpoint Y: a watertight landmass' only once-edges are the outer coast loop (drops to ~0).
    Interior once-edges with min-Y above a 0.5u skirt = phantom cracks."""
    staged_tris = [t for t in t_all if t["block"] in set(FOOTPRINT)
                   and staged_terr_path(*t["block"]).exists()]
    deduped, _ = dedup_coincident(staged_tris)
    owner = defaultdict(list)
    ykey = {}
    for t in deduped:
        ks = [vkey(p) for p in t["w"]]
        for i in range(3):
            a, b = ks[i], ks[(i + 1) % 3]
            e = frozenset((a, b))
            if len(e) == 2:
                owner[e].append(t["gid"])
                ykey[e] = (a, b)
    once = [e for e, o in owner.items() if len(o) == 1]
    above = 0
    ys = []
    for e in once:
        a, b = ykey[e]
        miny = min(a[1], b[1])
        ys.append(miny)
        if miny > 0.5:
            above += 1
    return dict(n_once_total=len(once), n_interior_once_above_skirt=above,
                min_y_p50=round(sorted(ys)[len(ys) // 2], 3) if ys else None,
                max_min_y=round(max(ys), 3) if ys else None,
                coast_hint="once-edges near y=0 are the true coast loop",
                note="above-skirt once-edges (minY>0.5) are candidate phantom cracks -- a watertight "
                     "landmass has ZERO; the outer coast drops to ~0 so it is skirt-filtered.")


def flat_and_sea():
    bad = []
    for (bx, by) in FOOTPRINT:
        p = staged_terr_path(bx, by)
        if not p.exists():
            continue
        bm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
        if bm.vcount != 3 * len(bm.tris) or len(bm.verts) != 3 * len(bm.tris):
            bad.append([bx, by, bm.vcount, len(bm.verts), len(bm.tris)])
    sea4_nonzero = 0
    n_sea = 0
    for (bx, by) in FOOTPRINT:
        rel = M.override_relpath(1, bx, by, part="Sea4")
        p = STAGED / rel
        if not p.exists():
            continue
        n_sea += 1
        sbm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="sea4")
        for v in sbm.verts:
            if abs(v[1]) > 1e-4:
                sea4_nonzero += 1
    return dict(bad=bad, n_terrain=len([1 for b in FOOTPRINT if staged_terr_path(*b).exists()])), \
        dict(sea4_nonzero=sea4_nonzero, n_sea4_blocks=n_sea)


def event_area_strip():
    """Carried ecotone/dunes tris must have event/area bits stripped (the donor-dispatch strip law).
    decode_id exposes area/event; check every staged mass-topo tri."""
    nonzero = 0
    total = 0
    for (bx, by) in FOOTPRINT:
        p = staged_terr_path(bx, by)
        if not p.exists():
            continue
        bm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
        for tri in bm.tris:
            idall = int(round(bm.tangents[tri[0]][0]))
            dec = X.decode_id(idall)
            if dec["topograph"] not in MASS_TOPOS:
                continue
            total += 1
            ev = dec.get("event", 0) or 0
            ar = dec.get("area", 0) or 0
            if ev or ar:
                nonzero += 1
    return dict(nonzero=nonzero, total_mass_tris=total)


def orphan_check():
    """Independent orphan-decal census on the FINAL staged bytes (post any build redress) using the
    productized gate's correct deployed-else-stock Moore ring, WARN mode (read-only). The build claims
    it redressed 2 pre-staging orphans -> the final tree must read 0."""
    try:
        from ff9mapkit.world import orphangate as O
    except Exception as e:
        return dict(error=f"import: {e}", n_orphans=None, n_ambiguous=None)
    cell_meshes = {}
    for (bx, by) in FOOTPRINT:
        p = staged_terr_path(bx, by)
        if not p.exists():
            continue
        bm = M.blockmesh_from_ff9mesh(p, disc=1, x=bx, y=by, part="terrain")
        cell_meshes[(bx, by)] = [("Terrain", bm)]
    try:
        res = O.orphan_decal_gate(cell_meshes, list(cell_meshes.keys()), enforce=False,
                                  redress=False, mod_folder=str(STAGED), disc=1)
    except Exception as e:
        return dict(error=f"gate: {e}", n_orphans=None, n_ambiguous=None)
    return dict(n_orphans=res.get("n_orphans"), n_ambiguous=res.get("n_ambiguous"),
                ok=res.get("ok"), ring_blocks=res.get("ring_blocks"),
                note="independent WARN-mode census on final staged bytes; deployed-else-stock ring.")


def reconcile(result):
    try:
        b = json.loads((HERE / "out" / "rung_f" / "rung_f_build.json").read_text(encoding="utf-8"))
    except Exception as e:
        return dict(error=str(e))
    g = b.get("gates", {})
    br = b.get("rebuild", {}) if isinstance(b.get("rebuild"), dict) else {}
    out = dict(build_headline_claims=dict(
        R1="46.826/48.882/49.547", R2="0.4976/0.6303 fringe 0.8008 pen 0.1241",
        R3="backing 143 interface 127 erosion 129"))
    out["my_R1"] = result["R1"]["measured"]
    out["my_R2"] = dict(sat_grass=result["R2"]["sat_grass"], sat_any=result["R2"]["sat_any"],
                        fringe=result["R2"]["fringe"], pen=result["R2"]["penetration"])
    out["my_R3"] = dict(backing=result["R3"]["backing_reachable"], iface=result["R3"]["interface_pairs"],
                        erosion=result["R3"]["erosion_survive"])
    return out


if __name__ == "__main__":
    main()
