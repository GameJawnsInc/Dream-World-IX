"""RUNG F -- THE ROOTS RE-CLOTHE (FIXED4) CODE-DISJOINT FALSIFIER (2026-07-24).

Round-4 verifier. Extends MY OWN falsifier lineage (uvf_fix_falsify -> uvf_fix2_falsify ->
uvf_fix3_falsify). Does NOT import uvf_fix4.py / uvf_gates*.py / uvf_fix*.py / uvf_forensics.py.
Reuses ONLY the loaders (ff9mapkit.world.extract, .mesh) + the KIT's ground language
(grassland.ground_uv / GROUNDS / FAM_REGION / TOPO_FAMILY) -- which is the very thing the build
claims to have used, so it is the correct oracle, not shared build code. Every classifier,
diff, nearest-family derivation and gate is reimplemented here.

CENTRAL CLAIMS TESTED INDEPENDENTLY FROM RAW BYTES:
 (1) 0 degenerate / collapsed UV tris anywhere in FIXED4 Terrain (own classifier).
 (2) RIGIDITY vs FIXED3A: positions/normals/tangents/indices byte-identical on ALL files;
     UV changes ONLY on tris I myself identify as SYNTHESIZED (= UV-degenerate in the
     pre-fix specimen tree FF9CustomMap-world); grass-family synthesized tris byte-identical;
     carried-core (donor byte-match, my own re-identification) byte-identical;
     Sea4 + every non-Terrain file byte-identical.
 (3) FAMILY CORRECTNESS: each re-clothed tri reconstructs from the KIT's own family emission
     grassland.ground_uv(x,z,cell,quad,ori,family) for ONE lawful (quad,ori) window; the
     family translation constants are re-read from the grassland SOURCE TEXT (not just the
     imported symbol); and the tri's family is re-derived independently as the nearest kept
     content's family (two independent nearest metrics: cell-lattice and continuous tri-centroid).
 (4) REFUTATION HUNT: a tri wearing a family whose nearest kept member is NOT nearest;
     any grass-lobe fill changed; any UV outside its own family's mains rect.

READ-ONLY vs the game install. Writes only out/rung_f/uvf_fix4_falsify.json + this script.
"""
from __future__ import annotations
import json, math, re, struct, sys, hashlib
from collections import Counter, defaultdict
from itertools import product
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

from ff9mapkit.world import extract as X      # noqa: E402
from ff9mapkit.world import mesh as M         # noqa: E402
from ff9mapkit.world import grassland as G    # noqa: E402

CELL = 4.0
RUNG = HERE / "out" / "rung_f"
SPEC = RUNG / "FF9CustomMap-world"                 # the pre-fix specimen (defines the synthesized set)
FIXED3A = RUNG / "FF9CustomMap-world-FIXED3A"      # the deployed base
FIXED4 = RUNG / "FF9CustomMap-world-FIXED4"        # the candidate
OUT = RUNG / "uvf_fix4_falsify.json"
FOOTPRINT = [(bx, by) for bx in range(0, 5) for by in range(16, 20)]
MAGIC = b"F9WM"
UV_ZERO = 1e-6
QUADS = [(0, 0), (0, 1), (1, 0), (1, 1)]
ORIS = (0, 90, 180, 270)
WIN_TOL = 2e-5
FAMILIES = ("grass", "desert", "dunes")


def log(m): print(m, flush=True)


# ---------- raw .ff9mesh parse (MY code, lineage-carried) ----------
def parse_raw(path):
    data = Path(path).read_bytes()
    assert data[:4] == MAGIC, f"bad magic {path}"
    version, vcount, icount, flags = struct.unpack_from("<iiii", data, 4)
    off = 20
    off_pos = off
    sz_pos = vcount * 3 * 4
    off_nrm = off_pos + sz_pos
    sz_nrm = vcount * 3 * 4 if (flags & 1) else 0
    off_uv = off_nrm + sz_nrm
    sz_uv = vcount * 2 * 4 if (flags & 2) else 0
    off_tan = off_uv + sz_uv
    sz_tan = vcount * 4 * 4 if (flags & 4) else 0
    off_idx = off_tan + sz_tan
    sz_idx = icount * 4
    return dict(data=data, version=version, vcount=vcount, icount=icount, flags=flags,
                off_pos=off_pos, sz_pos=sz_pos, off_nrm=off_nrm, sz_nrm=sz_nrm,
                off_uv=off_uv, sz_uv=sz_uv, off_tan=off_tan, sz_tan=sz_tan,
                off_idx=off_idx, sz_idx=sz_idx, total=len(data))


def sl(r, off, sz): return r["data"][off:off + sz]
def verts_of(r):
    d = r["data"]; return [struct.unpack_from("<3f", d, r["off_pos"] + j * 12) for j in range(r["vcount"])]
def nrms_of(r):
    d = r["data"]; return [struct.unpack_from("<3f", d, r["off_nrm"] + j * 12) for j in range(r["vcount"])]
def uvs_of(r):
    d = r["data"]; return [struct.unpack_from("<2f", d, r["off_uv"] + j * 8) for j in range(r["vcount"])]
def tans_of(r):
    d = r["data"]; return [struct.unpack_from("<4f", d, r["off_tan"] + j * 16) for j in range(r["vcount"])]
def idx_of(r):
    d = r["data"]; return list(struct.unpack_from("<%di" % r["icount"], d, r["off_idx"]))


def f32(x): return struct.unpack("<f", struct.pack("<f", x))[0]


def uv_area(uv0, uv1, uv2):
    return abs((uv1[0] - uv0[0]) * (uv2[1] - uv0[1]) - (uv2[0] - uv0[0]) * (uv1[1] - uv0[1]))
def uv_collapsed(uv0, uv1, uv2):
    ds = [math.hypot(a[0] - b[0], a[1] - b[1]) for a, b in ((uv0, uv1), (uv0, uv2), (uv1, uv2))]
    return max(ds) < UV_ZERO
def is_degenerate(uv0, uv1, uv2):
    return uv_area(uv0, uv1, uv2) < UV_ZERO or uv_collapsed(uv0, uv1, uv2)


def terr_path(root, bx, by): return root / M.override_relpath(1, bx, by, part="Terrain")
def sea4_path(root, bx, by): return root / M.override_relpath(1, bx, by, part="Sea4")
def sha(b): return hashlib.sha256(b).hexdigest()


# ---------- family rects, straight from the kit ----------
FAM_RECT = {f: tuple(G.ground_main_region(f)) for f in FAMILIES}
FAM_DELTA = {f: (G.GROUNDS[f]["mains_du"], G.GROUNDS[f]["mains_dv"]) for f in FAMILIES}


def in_rect(uv, rect, pad=1e-4):
    return (rect[0] - pad <= uv[0] <= rect[2] + pad) and (rect[1] - pad <= uv[1] <= rect[3] + pad)


def family_of_uvs(obs):
    """Classify a tri's family purely by which family mains rect holds all 3 UVs (rects are disjoint)."""
    hits = [f for f in FAMILIES if all(in_rect(uv, FAM_RECT[f]) for uv in obs)]
    if len(hits) == 1:
        return hits[0]
    return None if not hits else "AMBIGUOUS:" + "+".join(hits)


# =====================================================================================================
# Source-text verification of the translation constants (do not trust the imported symbol alone)
def constants_from_source():
    src = (REPO_ROOT / "ff9mapkit" / "ff9mapkit" / "world" / "grassland.py").read_text(encoding="utf-8")
    found = {}
    for fam in FAMILIES:
        m = re.search(r'"%s":\s*dict\(topo=(\d+),\s*mains_du=([-\d.]+),\s*mains_dv=([-\d.]+)' % fam, src)
        if m:
            found[fam] = dict(topo=int(m.group(1)), mains_du=float(m.group(2)), mains_dv=float(m.group(3)))
    # the grass entry is written topo=0, mains_du=0.0 -- regex above handles it
    gr = re.search(r'GRASS_U_HALF\s*=\s*\[\(([-\d.]+),\s*([-\d.]+)\),\s*\(([-\d.]+),\s*([-\d.]+)\)\]', src)
    gv = re.search(r'GRASS_V_HALF\s*=\s*\[\(([-\d.]+),\s*([-\d.]+)\),\s*\(([-\d.]+),\s*([-\d.]+)\)\]', src)
    res = dict(parsed=found,
               grass_u_half=[float(x) for x in gr.groups()] if gr else None,
               grass_v_half=[float(x) for x in gv.groups()] if gv else None,
               imported={f: dict(topo=G.GROUNDS[f]["topo"], mains_du=G.GROUNDS[f]["mains_du"],
                                 mains_dv=G.GROUNDS[f]["mains_dv"]) for f in FAMILIES},
               fam_rect={f: [round(v, 6) for v in FAM_RECT[f]] for f in FAMILIES})
    res["source_matches_import"] = all(
        f in found and abs(found[f]["mains_du"] - G.GROUNDS[f]["mains_du"]) < 1e-12
        and abs(found[f]["mains_dv"] - G.GROUNDS[f]["mains_dv"]) < 1e-12 for f in FAMILIES)
    return res


# =====================================================================================================
# STAGE A -- MY identification of the synthesized set + the per-tri tables
def load_tree_tris():
    """Per block: parallel SPEC/FIXED3A/FIXED4 tri tables keyed on tri index (validated identical geometry)."""
    tables = {}
    geom_bad = []
    for (bx, by) in FOOTPRINT:
        ps, p3, p4 = terr_path(SPEC, bx, by), terr_path(FIXED3A, bx, by), terr_path(FIXED4, bx, by)
        if not (ps.exists() and p3.exists() and p4.exists()):
            geom_bad.append([bx, by, "missing"]); continue
        rs, r3, r4 = parse_raw(ps), parse_raw(p3), parse_raw(p4)
        for nm, ra in (("spec", rs), ("f3a", r3)):
            if (ra["vcount"], ra["icount"], ra["flags"]) != (r4["vcount"], r4["icount"], r4["flags"]):
                geom_bad.append([bx, by, "header", nm]); break
        else:
            if sl(rs, rs["off_idx"], rs["sz_idx"]) != sl(r4, r4["off_idx"], r4["sz_idx"]):
                geom_bad.append([bx, by, "idx-spec"])
            if sl(rs, rs["off_pos"], rs["sz_pos"]) != sl(r4, r4["off_pos"], r4["sz_pos"]):
                geom_bad.append([bx, by, "pos-spec"])
        tables[(bx, by)] = dict(rs=rs, r3=r3, r4=r4,
                                us=uvs_of(rs), u3=uvs_of(r3), u4=uvs_of(r4),
                                v4=verts_of(r4), t4=tans_of(r4), idx=idx_of(r4),
                                org=X.block_world_origin(bx, by))
    return tables, geom_bad


def build_tri_records(tables):
    """Every Terrain tri: world verts, centroid cell, spec/f3a/f4 UVs, topo, synthesized flag."""
    recs = []
    for (bx, by), T in tables.items():
        ox, oz = T["org"]; idx = T["idx"]
        for t in range(len(idx) // 3):
            tri = (idx[3 * t], idx[3 * t + 1], idx[3 * t + 2])
            w = [(T["v4"][j][0] + ox, T["v4"][j][1], T["v4"][j][2] + oz) for j in tri]
            cx = sum(p[0] for p in w) / 3.0; cz = sum(p[2] for p in w) / 3.0
            cell = (math.floor(cx / CELL), math.floor(cz / CELL))
            uv_s = [T["us"][j] for j in tri]
            uv_3 = [T["u3"][j] for j in tri]
            uv_4 = [T["u4"][j] for j in tri]
            topo = X.decode_id(int(round(T["t4"][tri[0]][0])))["topograph"]
            recs.append(dict(b=(bx, by), t=t, tri=tri, w=w, c=(cx, cz), cell=cell,
                             uv_s=uv_s, uv_3=uv_3, uv_4=uv_4, topo=topo,
                             synth=is_degenerate(*uv_s),
                             changed=any(a != b for a, b in zip(uv_3, uv_4))))
    return recs


# =====================================================================================================
# (2) file-level rigidity FIXED3A -> FIXED4
def tree_rigidity():
    def rel(root): return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())
    a, b = rel(FIXED3A), rel(FIXED4)
    only3 = sorted(set(a) - set(b)); only4 = sorted(set(b) - set(a))
    changed = []
    for rp in sorted(set(a) & set(b)):
        if (FIXED3A / rp).read_bytes() != (FIXED4 / rp).read_bytes():
            changed.append(rp)
    non_terrain = [rp for rp in changed if not rp.endswith("Terrain.ff9mesh")]
    sea4 = [rp for rp in changed if rp.endswith("Sea4.ff9mesh")]
    return dict(n_fixed3a=len(a), n_fixed4=len(b), only_fixed3a=only3, only_fixed4=only4,
                n_changed=len(changed), changed=changed,
                changed_non_terrain=non_terrain, changed_sea4=sea4)


def channel_rigidity(tables):
    res = dict(pos_bad=[], nrm_bad=[], tan_bad=[], idx_bad=[], header_bad=[],
               uv_changed_verts=0, per_block={})
    for (bx, by), T in tables.items():
        r3, r4 = T["r3"], T["r4"]
        if (r3["vcount"], r3["icount"], r3["flags"]) != (r4["vcount"], r4["icount"], r4["flags"]):
            res["header_bad"].append([bx, by]); continue
        if sl(r3, r3["off_pos"], r3["sz_pos"]) != sl(r4, r4["off_pos"], r4["sz_pos"]): res["pos_bad"].append([bx, by])
        if sl(r3, r3["off_nrm"], r3["sz_nrm"]) != sl(r4, r4["off_nrm"], r4["sz_nrm"]): res["nrm_bad"].append([bx, by])
        if sl(r3, r3["off_tan"], r3["sz_tan"]) != sl(r4, r4["off_tan"], r4["sz_tan"]): res["tan_bad"].append([bx, by])
        if sl(r3, r3["off_idx"], r3["sz_idx"]) != sl(r4, r4["off_idx"], r4["sz_idx"]): res["idx_bad"].append([bx, by])
        d3, d4 = r3["data"], r4["data"]
        n = sum(1 for j in range(r3["vcount"])
                if d3[r3["off_uv"] + j * 8: r3["off_uv"] + j * 8 + 8] != d4[r4["off_uv"] + j * 8: r4["off_uv"] + j * 8 + 8])
        res["uv_changed_verts"] += n
        if n: res["per_block"][f"{bx},{by}"] = n
    return res


# =====================================================================================================
# (2) carried-core identity via donor byte-match (MY re-identification, lineage-carried)
def carried_core_identity(tables):
    SHIFT = (-768.0, -384.0)
    donor = defaultdict(list)
    donor_blocks = 0
    for bx in (13, 14, 15):
        for by in (11, 12):
            try:
                bm = X.read_block(bx, by, disc=1, part="terrain")
            except (ValueError, FileNotFoundError, OSError):
                continue
            donor_blocks += 1
            ox, oz = X.block_world_origin(bx, by)
            for tri in bm.tris:
                w = [(bm.verts[j][0] + ox + SHIFT[0], bm.verts[j][1], bm.verts[j][2] + oz + SHIFT[1]) for j in tri]
                key = tuple(sorted((round(p[0], 2), round(p[2], 2)) for p in w))
                uv = tuple(sorted((round(float(bm.uvs[j][0]), 6), round(float(bm.uvs[j][1]), 6)) for j in tri))
                donor[key].append(uv)
    matched_xz = verbatim = changed_bad = 0
    for (bx, by), T in tables.items():
        ox, oz = T["org"]; idx = T["idx"]
        for t in range(len(idx) // 3):
            tri = (idx[3 * t], idx[3 * t + 1], idx[3 * t + 2])
            w = [(T["v4"][j][0] + ox, T["v4"][j][1], T["v4"][j][2] + oz) for j in tri]
            key = tuple(sorted((round(p[0], 2), round(p[2], 2)) for p in w))
            cands = donor.get(key)
            if not cands: continue
            matched_xz += 1
            uv4 = tuple(sorted((round(T["u4"][j][0], 6), round(T["u4"][j][1], 6)) for j in tri))
            if any(c == uv4 for c in cands):
                verbatim += 1
                if any(T["u3"][j] != T["u4"][j] for j in tri): changed_bad += 1
    return dict(donor_blocks=donor_blocks, matched_xz=matched_xz,
                carried_core_verbatim=verbatim, carried_core_changed=changed_bad)


# =====================================================================================================
# (3) window reconstruction through the KIT's own family emission
def _candidate_cells(w, centroid_cell):
    cells = {centroid_cell}
    for i in range(3):
        cells.add((math.floor(w[i][0] / CELL), math.floor(w[i][2] / CELL)))
    for di in (-1, 0, 1):
        for dj in (-1, 0, 1):
            cells.add((centroid_cell[0] + di, centroid_cell[1] + dj))
    return cells


def single_window(w, obs, family, centroid_cell, tol=WIN_TOL):
    """Return (cell,quad,ori,resid) if ONE kit family window reproduces all 3 UVs; else None."""
    best = None
    for cell in _candidate_cells(w, centroid_cell):
        for (q, o) in product(QUADS, ORIS):
            resid = 0.0; ok = True
            for i in range(3):
                cu, cv = G.ground_uv(w[i][0], w[i][2], cell, q, o, family)
                d = max(abs(cu - obs[i][0]), abs(cv - obs[i][1]))
                if d >= tol:
                    ok = False; break
                resid = max(resid, d)
            if ok and (best is None or resid < best[3]):
                best = (cell, q, o, resid)
    return best


# =====================================================================================================
# (3)/(4) independent nearest-kept-family derivation
def nearest_family_field(recs):
    """Kept (non-synthesized) GROUND tris vote TOPO_FAMILY into their centroid cell (majority);
    non-ground topos abstain. Two independent nearest metrics per fill tri."""
    cell_votes = defaultdict(Counter)
    kept_tris_by_fam = defaultdict(list)   # continuous metric: (cx,cz)
    kept_topo = Counter(); abstain = Counter()
    for r in recs:
        if r["synth"]: continue
        fam = G.TOPO_FAMILY.get(r["topo"])
        kept_topo[r["topo"]] += 1
        if fam is None:
            abstain[r["topo"]] += 1; continue
        cell_votes[r["cell"]][fam] += 1
        kept_tris_by_fam[fam].append(r["c"])
    cell_fam = {}
    for c, ctr in cell_votes.items():
        top = ctr.most_common()
        # majority; deterministic tie-break by family name
        best = max(top, key=lambda kv: (kv[1], kv[0]))
        cell_fam[c] = best[0]
    by_fam_cells = defaultdict(list)
    for c, f in cell_fam.items(): by_fam_cells[f].append(c)
    # PRESENCE metric: a family "occupies" every cell where it has ANY kept tri (no majority collapse).
    # This is the more literal reading of "the nearest KEPT CONTENT's family" and is tie-honest.
    present_cells = defaultdict(list)
    for c, ctr in cell_votes.items():
        for f in ctr: present_cells[f].append(c)
    return dict(cell_fam=cell_fam, by_fam_cells=dict(by_fam_cells),
                present_cells=dict(present_cells), cell_votes=dict(cell_votes),
                kept_tris_by_fam=dict(kept_tris_by_fam),
                kept_topo=dict(kept_topo), abstain=dict(abstain),
                n_source_cells=len(cell_fam),
                source_cells_by_family=dict(Counter(cell_fam.values())),
                present_cells_by_family={f: len(v) for f, v in present_cells.items()})


def nearest_by_cell(field, cell):
    """min squared cell distance to a source cell, per family; returns dict fam->d2 and the global min."""
    best = {}
    for fam, cells in field["by_fam_cells"].items():
        d2 = min((cell[0] - c[0]) ** 2 + (cell[1] - c[1]) ** 2 for c in cells)
        best[fam] = d2
    gmin = min(best.values()) if best else None
    return best, gmin


def nearest_by_presence(field, cell):
    """min squared cell distance to a cell CONTAINING any kept tri of that family (no majority collapse)."""
    best = {}
    for fam, cells in field["present_cells"].items():
        best[fam] = min((cell[0] - c[0]) ** 2 + (cell[1] - c[1]) ** 2 for c in cells)
    gmin = min(best.values()) if best else None
    return best, gmin


def nearest_by_tri(field, c):
    best = {}
    for fam, pts in field["kept_tris_by_fam"].items():
        d2 = min((c[0] - p[0]) ** 2 + (c[1] - p[1]) ** 2 for p in pts)
        best[fam] = d2
    gmin = min(best.values()) if best else None
    return best, gmin


# =====================================================================================================
def main():
    findings = []; R = {}

    R["constants"] = constants_from_source()
    log(f"[0] constants source==import: {R['constants']['source_matches_import']} "
        f"desert={R['constants']['parsed'].get('desert')} dunes={R['constants']['parsed'].get('dunes')}")
    if not R["constants"]["source_matches_import"]:
        findings.append("REFUTE (3): grassland.py SOURCE translation constants disagree with the imported GROUNDS.")

    tables, geom_bad = load_tree_tris()
    R["geometry_parity"] = dict(blocks=len(tables), bad=geom_bad)
    if geom_bad:
        findings.append(f"REFUTE (2): SPEC/FIXED3A/FIXED4 geometry or header parity broken: {geom_bad}.")
    recs = build_tri_records(tables)
    log(f"[A] tris={len(recs)} blocks={len(tables)}")

    # ---- (1) degenerate = 0 in FIXED4
    deg4 = [r for r in recs if is_degenerate(*r["uv_4"])]
    deg3 = [r for r in recs if is_degenerate(*r["uv_3"])]
    degs = [r for r in recs if r["synth"]]
    zero_area4 = sum(1 for r in recs if uv_area(*r["uv_4"]) < 5e-4)
    R["degenerate"] = dict(fixed4=len(deg4), fixed3a=len(deg3), spec=len(degs),
                           fixed4_examples=[[r["b"], r["t"]] for r in deg4[:5]],
                           fixed4_zero_uv_area_below_5e4=zero_area4)
    log(f"[1] degenerate: SPEC={len(degs)} FIXED3A={len(deg3)} FIXED4={len(deg4)} (zero-area<5e-4: {zero_area4})")
    if deg4: findings.append(f"REFUTE (1): FIXED4 has {len(deg4)} degenerate/collapsed-UV tris.")
    if len(degs) != 2305:
        findings.append(f"MISMATCH (1): my synthesized-set size {len(degs)} != the reported 2305.")

    # ---- (2) rigidity
    tree = tree_rigidity(); R["tree_rigidity"] = tree
    log(f"[2] tree: files {tree['n_fixed3a']}/{tree['n_fixed4']} changed={tree['n_changed']} "
        f"non_terrain={tree['changed_non_terrain']} sea4={tree['changed_sea4']}")
    if tree["only_fixed3a"] or tree["only_fixed4"]:
        findings.append(f"REFUTE (2): file set differs only3A={tree['only_fixed3a']} only4={tree['only_fixed4']}.")
    if tree["changed_non_terrain"]:
        findings.append(f"REFUTE (2): non-Terrain files changed: {tree['changed_non_terrain']}.")
    if tree["changed_sea4"]:
        findings.append(f"REFUTE (2): Sea4 files changed: {tree['changed_sea4']}.")
    if tree["n_changed"] != 4:
        findings.append(f"MISMATCH (2): {tree['n_changed']} files changed, report says 4.")

    ch = channel_rigidity(tables); R["channel_rigidity"] = ch
    log(f"[2] channels: pos_bad={ch['pos_bad']} nrm_bad={ch['nrm_bad']} tan_bad={ch['tan_bad']} "
        f"idx_bad={ch['idx_bad']} uv_verts={ch['uv_changed_verts']} per_block={ch['per_block']}")
    for k, lbl in (("pos_bad", "positions"), ("nrm_bad", "normals"), ("tan_bad", "tangents/IDALL"),
                   ("idx_bad", "indices"), ("header_bad", "headers")):
        if ch[k]: findings.append(f"REFUTE (2): {lbl} changed FIXED3A->FIXED4 in {ch[k]}.")
    if ch["uv_changed_verts"] != 306:
        findings.append(f"MISMATCH (2): {ch['uv_changed_verts']} UV verts changed, report says 306.")

    changed = [r for r in recs if r["changed"]]
    changed_nonsynth = [r for r in changed if not r["synth"]]
    R["uv_change_confinement"] = dict(changed_tris=len(changed),
                                      changed_but_not_synthesized=len(changed_nonsynth),
                                      examples=[[r["b"], r["t"], r["topo"]] for r in changed_nonsynth[:10]])
    log(f"[2] changed tris={len(changed)} outside-synthesized={len(changed_nonsynth)}")
    if changed_nonsynth:
        findings.append(f"REFUTE (2): {len(changed_nonsynth)} UV-changed tris are NOT in my synthesized set.")

    core = carried_core_identity(tables); R["carried_core"] = core
    log(f"[2] carried-core: donor_blocks={core['donor_blocks']} matched_xz={core['matched_xz']} "
        f"verbatim={core['carried_core_verbatim']} changed={core['carried_core_changed']}")
    if core["carried_core_changed"]:
        findings.append(f"REFUTE (2): {core['carried_core_changed']} carried-core (donor-verbatim) tris changed.")
    if core["donor_blocks"] == 0:
        findings.append("NOTE (2): donor blocks unreadable -- carried-core re-identification did not run.")
    elif core["carried_core_verbatim"] == 0:
        findings.append("NOTE (2): 0 carried-core verbatim tris matched (re-identification empty).")

    # ---- family classification of the WHOLE synthesized set (own rect classifier)
    fam4 = Counter(); fam3 = Counter(); unclass = []
    per_tri_fam = {}
    for r in degs:
        f4 = family_of_uvs(r["uv_4"]); f3 = family_of_uvs(r["uv_3"])
        per_tri_fam[(r["b"], r["t"])] = (f3, f4)
        fam4[str(f4)] += 1; fam3[str(f3)] += 1
        if f4 is None or str(f4).startswith("AMBIGUOUS"):
            unclass.append([r["b"], r["t"], str(f4), [[round(u, 6) for u in uv] for uv in r["uv_4"]]])
    R["synthesized_family_hist"] = dict(fixed4=dict(fam4), fixed3a=dict(fam3),
                                        unclassified=len(unclass), unclassified_examples=unclass[:8])
    log(f"[3] synthesized family hist FIXED4={dict(fam4)} (FIXED3A={dict(fam3)}) unclassified={len(unclass)}")
    if unclass:
        findings.append(f"REFUTE (4): {len(unclass)} synthesized tris' UVs fall outside every family mains rect "
                        f"(or straddle two): {unclass[:3]}.")
    if fam3.get("grass") != len(degs):
        findings.append(f"MISMATCH (3): FIXED3A synthesized set is not 100% grass ({dict(fam3)}).")

    reclothed = [r for r in degs if r["changed"]]
    grass_unchanged = [r for r in degs if not r["changed"]]
    R["reclothed"] = dict(n=len(reclothed),
                          by_family=dict(Counter(str(per_tri_fam[(r['b'], r['t'])][1]) for r in reclothed)),
                          n_left_grass=len(grass_unchanged))
    log(f"[3] re-clothed={len(reclothed)} by family={R['reclothed']['by_family']} left-grass={len(grass_unchanged)}")

    # grass-family synthesized tris must be byte-identical
    grass_changed = [r for r in reclothed if per_tri_fam[(r["b"], r["t"])][1] == "grass"]
    if grass_changed:
        findings.append(f"REFUTE (2): {len(grass_changed)} grass-family synthesized tris changed vs FIXED3A.")
    nongrass_unchanged = [r for r in grass_unchanged if per_tri_fam[(r["b"], r["t"])][1] != "grass"]
    if nongrass_unchanged:
        findings.append(f"REFUTE (2): {len(nongrass_unchanged)} non-grass-family synthesized tris are unchanged "
                        f"(family classification inconsistent with the diff).")

    # ---- translation-only proof: FIXED4 uv == float32(FIXED3A uv + family delta)
    trans_bad = []; max_dev = 0.0
    for r in reclothed:
        fam = per_tri_fam[(r["b"], r["t"])][1]
        if fam not in FAM_DELTA: continue
        du, dv = FAM_DELTA[fam]
        for a, b in zip(r["uv_3"], r["uv_4"]):
            d = max(abs(b[0] - (a[0] + du)), abs(b[1] - (a[1] + dv)))
            max_dev = max(max_dev, d)
            if d > 1e-6: trans_bad.append([r["b"], r["t"], fam, round(d, 9)])
    R["translation_only"] = dict(max_abs_deviation=max_dev, bad=len(trans_bad), examples=trans_bad[:5])
    log(f"[3] translation-only: max_dev={max_dev:.3e} bad={len(trans_bad)}")
    if trans_bad:
        findings.append(f"REFUTE (3): {len(trans_bad)} re-clothed vert deltas are NOT the kit family translation.")

    # ---- window reconstruction: ALL re-clothed + a 30-sample deep check, + all-synthesized coherence
    win_all = dict(n=0, single=0, multi=[], qo_hist=Counter(), resid_max=0.0)
    for r in reclothed:
        fam = per_tri_fam[(r["b"], r["t"])][1]
        win_all["n"] += 1
        w = single_window(r["w"], r["uv_4"], fam, r["cell"])
        if w is None:
            win_all["multi"].append([r["b"], r["t"], fam])
        else:
            win_all["single"] += 1
            win_all["qo_hist"][f"{w[1]}|{w[2]}"] += 1
            win_all["resid_max"] = max(win_all["resid_max"], w[3])
    R["window_reclothed"] = dict(n=win_all["n"], single_window=win_all["single"],
                                 multi_window=len(win_all["multi"]), multi_examples=win_all["multi"][:8],
                                 quad_ori_hist=dict(win_all["qo_hist"]),
                                 resid_max=round(win_all["resid_max"], 9))
    log(f"[3] re-clothed window: {win_all['single']}/{win_all['n']} single-window resid_max={win_all['resid_max']:.2e} "
        f"qo={dict(win_all['qo_hist'])}")
    if win_all["multi"]:
        findings.append(f"REFUTE (3): {len(win_all['multi'])} re-clothed tris do NOT reconstruct from ONE lawful "
                        f"kit family (quad,ori) window: {win_all['multi'][:5]}.")

    # whole synthesized set coherence (family-aware) -- FIXED4
    coh_single = 0; coh_multi = []
    for r in degs:
        fam = per_tri_fam[(r["b"], r["t"])][1]
        if fam not in FAM_DELTA:
            coh_multi.append([r["b"], r["t"], str(fam)]); continue
        w = single_window(r["w"], r["uv_4"], fam, r["cell"])
        if w is None: coh_multi.append([r["b"], r["t"], fam])
        else: coh_single += 1
    R["window_all_synthesized"] = dict(n=len(degs), single_window=coh_single, multi_window=len(coh_multi),
                                       pct_single=round(100.0 * coh_single / len(degs), 4) if degs else None,
                                       multi_examples=coh_multi[:8])
    log(f"[3] all-synthesized coherence FIXED4: {coh_single}/{len(degs)} "
        f"({R['window_all_synthesized']['pct_single']}%) multi={len(coh_multi)}")
    if len(coh_multi) > 1:
        findings.append(f"REFUTE (3): {len(coh_multi)} synthesized tris are cross-window in FIXED4 "
                        f"(>1 documented per-vertex last-resort sliver): {coh_multi[:5]}.")

    # 30-sample explicit deep check (evenly spread across the re-clothed set)
    step = max(1, len(reclothed) // 30)
    sample = reclothed[::step][:30]
    smp_rows = []; smp_bad = 0
    for r in sample:
        fam = per_tri_fam[(r["b"], r["t"])][1]
        w = single_window(r["w"], r["uv_4"], fam, r["cell"])
        row = dict(block=list(r["b"]), tri=r["t"], family=fam, cell=list(r["cell"]),
                   topo=r["topo"],
                   window=None if w is None else dict(cell=list(w[0]), quad=list(w[1]), ori=w[2],
                                                      resid=round(w[3], 9)),
                   centroid_window=(w is not None and tuple(w[0]) == tuple(r["cell"])))
        if w is None or not row["centroid_window"]: smp_bad += 1
        smp_rows.append(row)
    R["sample30"] = dict(n=len(sample), bad=smp_bad, rows=smp_rows)
    log(f"[3] sample30: n={len(sample)} bad(no-window-or-not-centroid)={smp_bad}")
    if smp_bad:
        findings.append(f"REFUTE (3): {smp_bad}/{len(sample)} sampled re-clothed tris fail the lawful "
                        f"centroid-window family reconstruction.")

    # ---- independent nearest-kept-family derivation
    field = nearest_family_field(recs)
    R["nearest_field"] = dict(n_source_cells=field["n_source_cells"],
                              source_cells_by_family=field["source_cells_by_family"],
                              kept_topo_hist=field["kept_topo"], abstaining_topo=field["abstain"],
                              kept_tris_by_family={f: len(v) for f, v in field["kept_tris_by_fam"].items()})
    log(f"[3] nearest field: source_cells={field['n_source_cells']} by_fam={field['source_cells_by_family']} "
        f"kept_tris={R['nearest_field']['kept_tris_by_family']} abstain={field['abstain']}")

    agree_cell = agree_tri = agree_pres = 0
    disagree_majority = []; violations = []; no_member = []
    per_reclothed = []
    for r in reclothed:
        fam = per_tri_fam[(r["b"], r["t"])][1]
        dcell, gmin_c = nearest_by_cell(field, r["cell"])
        dpre, gmin_p = nearest_by_presence(field, r["cell"])
        dtri, gmin_t = nearest_by_tri(field, r["c"])
        ok_c = fam in dcell and abs(dcell[fam] - gmin_c) < 1e-9
        ok_p = fam in dpre and abs(dpre[fam] - gmin_p) < 1e-9
        ok_t = fam in dtri and abs(dtri[fam] - gmin_t) < 1e-9
        agree_cell += ok_c; agree_pres += ok_p; agree_tri += ok_t
        row = dict(block=list(r["b"]), tri=r["t"], family=fam, cell=list(r["cell"]),
                   d_majority={k: round(math.sqrt(v), 3) for k, v in dcell.items()},
                   d_presence={k: round(math.sqrt(v), 3) for k, v in dpre.items()},
                   d_tri={k: round(math.sqrt(v), 2) for k, v in dtri.items()},
                   own_cell_votes=dict(field["cell_votes"].get(tuple(r["cell"]), {})),
                   nearest_majority_ok=ok_c, nearest_presence_ok=ok_p, nearest_tri_ok=ok_t)
        if not ok_c: disagree_majority.append(row)
        if not ok_p: violations.append(row)          # strictly farther than another family = a real violation
        if fam not in dpre: no_member.append([r["b"], r["t"], fam])
        per_reclothed.append(row)
    R["nearest_agreement"] = dict(n=len(reclothed), agree_majority_metric=agree_cell,
                                  agree_presence_metric=agree_pres, agree_tri_metric=agree_tri,
                                  n_disagree_majority=len(disagree_majority),
                                  disagreements_majority=disagree_majority[:12],
                                  n_violations_presence=len(violations), violations=violations[:12],
                                  family_with_no_kept_member=no_member,
                                  metric_note="MAJORITY collapses each source cell to one family (the build's "
                                              "stated construction); PRESENCE keeps every family that has any kept "
                                              "tri in the cell (the literal 'nearest kept content' reading). A tri "
                                              "failing MAJORITY but passing PRESENCE sits on an exact TIE, where the "
                                              "law is silent -- not a violation.")
    R["reclothed_detail"] = per_reclothed
    log(f"[3/4] nearest agreement: majority {agree_cell}/{len(reclothed)} presence {agree_pres}/{len(reclothed)} "
        f"tri {agree_tri}/{len(reclothed)}")
    if no_member:
        findings.append(f"REFUTE (4): {len(no_member)} re-clothed tris wear a family with NO kept member anywhere: "
                        f"{no_member[:5]}.")
    if violations:
        findings.append(f"REFUTE (4): {len(violations)} re-clothed tris wear a family that is STRICTLY FARTHER than "
                        f"another kept family (a real nearest-wins violation): {violations[:3]}.")
    if disagree_majority and not violations:
        findings.append(f"NOTE (4): {len(disagree_majority)} re-clothed tri(s) sit on an exact nearest-distance TIE "
                        f"(assigned family present in the SAME cell as another family; my majority tie-break says "
                        f"otherwise, the build's next-ring tie-break says its family). The law is silent on ties -- "
                        f"evidence: {disagree_majority[:2]}.")
    if agree_tri != len(reclothed):
        findings.append(f"NOTE (4): {len(reclothed) - agree_tri} re-clothed tris disagree under the CONTINUOUS "
                        f"tri-centroid nearest metric (a third, independent metric).")

    # ---- (4) grass-lobe fill untouched: a fill tri whose nearest kept content is UNAMBIGUOUSLY grass
    grass_lobe_changed = []; tie_changed = []
    fill_nearest = Counter()
    for r in degs:
        dpre, gmin_p = nearest_by_presence(field, r["cell"])
        win = sorted(k for k, v in dpre.items() if abs(v - gmin_p) < 1e-9)
        lab = win[0] if len(win) == 1 else "tie:" + "+".join(win)
        fill_nearest[lab] += 1
        if r["changed"]:
            if win == ["grass"]: grass_lobe_changed.append([r["b"], r["t"]])
            elif len(win) > 1: tie_changed.append([r["b"], r["t"], lab])
    R["grass_lobe"] = dict(fill_nearest_hist=dict(fill_nearest), grass_lobe_changed=len(grass_lobe_changed),
                           examples=grass_lobe_changed[:8], changed_on_a_tie=tie_changed[:8],
                           n_changed_on_a_tie=len(tie_changed))
    log(f"[4] fill-by-nearest-family(presence) {dict(fill_nearest)} grass_lobe_changed={len(grass_lobe_changed)} "
        f"changed_on_tie={len(tie_changed)}")
    if grass_lobe_changed:
        findings.append(f"REFUTE (4): {len(grass_lobe_changed)} fill tris whose nearest kept content is "
                        f"UNAMBIGUOUSLY GRASS were re-clothed: {grass_lobe_changed[:5]}.")

    # ---- edge-adjacency evidence: does each re-clothed tri actually TOUCH kept content of its family?
    kept_edges = defaultdict(set)   # family -> set of rounded world edges
    for r in recs:
        if r["synth"]: continue
        fam = G.TOPO_FAMILY.get(r["topo"])
        if fam is None: continue
        for a, b in ((0, 1), (1, 2), (2, 0)):
            e = tuple(sorted(((round(r["w"][a][0], 2), round(r["w"][a][2], 2)),
                              (round(r["w"][b][0], 2), round(r["w"][b][2], 2)))))
            kept_edges[fam].add(e)
    adj_hist = Counter(); adj_bad = []
    for r in reclothed:
        fam = per_tri_fam[(r["b"], r["t"])][1]
        es = [tuple(sorted(((round(r["w"][a][0], 2), round(r["w"][a][2], 2)),
                            (round(r["w"][b][0], 2), round(r["w"][b][2], 2)))))
              for a, b in ((0, 1), (1, 2), (2, 0))]
        touch = {f for f in FAMILIES if any(e in kept_edges.get(f, ()) for e in es)}
        adj_hist["own-family" if fam in touch else ("other-only:" + "+".join(sorted(touch)) if touch
                                                   else "no-kept-edge")] += 1
        if touch and fam not in touch:
            adj_bad.append([r["b"], r["t"], fam, sorted(touch)])
    R["edge_adjacency"] = dict(hist=dict(adj_hist), touching_other_family_only=adj_bad[:10],
                               n_touching_other_family_only=len(adj_bad),
                               note="edge-sharing with KEPT content is stronger evidence than cell distance; "
                                    "'no-kept-edge' fill tris are interior to the hole and judged by distance only.")
    log(f"[4] edge adjacency {dict(adj_hist)} other-family-only={len(adj_bad)}")
    if adj_bad:
        findings.append(f"NOTE (4): {len(adj_bad)} re-clothed tris share an edge with kept content of a DIFFERENT "
                        f"family than the one they wear (and none of their own): {adj_bad[:4]}.")

    # ---- spatial footprint of the change + the crater cross-check
    if reclothed:
        xs = [r["cell"][0] for r in reclothed]; zs = [r["cell"][1] for r in reclothed]
        bbox = [min(xs), min(zs), max(xs), max(zs)]
        # kept dunes/desert extent for context
        dun = field["by_fam_cells"].get("dunes", []); des = field["by_fam_cells"].get("desert", [])
        def bb(cells):
            return None if not cells else [min(c[0] for c in cells), min(c[1] for c in cells),
                                           max(c[0] for c in cells), max(c[1] for c in cells)]
        R["footprint"] = dict(reclothed_cell_bbox=bbox, kept_dunes_cell_bbox=bb(dun),
                              kept_desert_cell_bbox=bb(des),
                              reclothed_cells=len({tuple(r["cell"]) for r in reclothed}),
                              blocks=sorted({str(r["b"]) for r in reclothed}))
        log(f"[4] re-clothed cell bbox={bbox} dunes_bbox={bb(dun)} desert_bbox={bb(des)} "
            f"cells={R['footprint']['reclothed_cells']} blocks={R['footprint']['blocks']}")

    # ---- (4) out-of-family-rect UV over the WHOLE tree (not just synthesized)
    out_rect = 0; out_examples = []
    for r in recs:
        fam = G.TOPO_FAMILY.get(r["topo"])
        if fam not in FAM_DELTA: continue
        if r["synth"]:
            fam = per_tri_fam[(r["b"], r["t"])][1]
            if fam not in FAM_DELTA: continue
        # only judge tris whose UVs sit inside SOME family mains rect (decals/strips/walls exempt)
        cls = family_of_uvs(r["uv_4"])
        if cls is None or str(cls).startswith("AMBIGUOUS"): continue
        if cls != fam and r["synth"]:
            out_rect += 1
            if len(out_examples) < 8: out_examples.append([r["b"], r["t"], fam, cls])
    R["out_of_family_rect"] = dict(n=out_rect, examples=out_examples)
    if out_rect:
        findings.append(f"REFUTE (4): {out_rect} synthesized tris' UVs sit in a different family's rect than the "
                        f"family they were assigned: {out_examples[:4]}.")

    # ---- report-number reconciliation
    rep = RUNG / "uvf_fix4_report.json"
    recon = {}
    if rep.exists():
        rj = json.loads(rep.read_text(encoding="utf-8"))
        claims = dict(tris_rewritten=rj["stage4_apply"]["tris_rewritten"],
                      dunes=rj["stage4_apply"]["tris_by_family"].get("dunes"),
                      desert=rj["stage4_apply"]["tris_by_family"].get("desert"),
                      grass=rj["stage4_apply"]["tris_by_family"].get("grass"),
                      uv_changed_verts=rj["stage4_apply"]["uv_changed_verts"],
                      files_changed=rj["stage5_verify"]["tree_diff_vs_fixed3a"]["n_files_changed"],
                      synthesized=rj["stage1_synthesized_set"]["n_synthesized_tris"])
        mine = dict(tris_rewritten=len(reclothed),
                    dunes=R["reclothed"]["by_family"].get("dunes", 0),
                    desert=R["reclothed"]["by_family"].get("desert", 0),
                    grass=len(grass_unchanged) + R["reclothed"]["by_family"].get("grass", 0),
                    uv_changed_verts=ch["uv_changed_verts"],
                    files_changed=tree["n_changed"], synthesized=len(degs))
        mismatches = {k: [claims[k], mine[k]] for k in claims if claims[k] != mine[k]}
        recon = dict(claimed=claims, measured=mine, mismatches=mismatches)
        if mismatches:
            findings.append(f"MISMATCH (report): {mismatches} (claimed vs measured).")
    R["report_reconciliation"] = recon
    log(f"[R] reconciliation mismatches={recon.get('mismatches')}")

    hard = [f for f in findings if f.startswith("REFUTE") or f.startswith("MISMATCH")]
    R["findings"] = findings
    R["notes"] = [f for f in findings if f.startswith("NOTE")]
    R["verdict"] = "REFUTED" if hard else "CONFIRMED"
    R["meta"] = dict(script="uvf_fix4_falsify.py", spec=str(SPEC), base=str(FIXED3A), target=str(FIXED4),
                     win_tol=WIN_TOL, uv_zero=UV_ZERO,
                     families=FAMILIES, fam_rects={f: [round(v, 6) for v in FAM_RECT[f]] for f in FAMILIES})
    OUT.write_text(json.dumps(R, indent=1), encoding="utf-8")
    log("\n" + "=" * 80)
    log(f"VERDICT: {R['verdict']}")
    for f in findings: log("  - " + f)
    log(f"-> {OUT}")
    return R


if __name__ == "__main__":
    main()
