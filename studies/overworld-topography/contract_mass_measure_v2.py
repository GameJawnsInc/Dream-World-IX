"""MEASUREMENT for the gates round-2 fix (2026-07-24, READ-ONLY).

Measures on the STOCK ecotone the numbers the three new gate fixes need a ceiling/floor for, so the
constants are set from real bytes with margin (never knife-edged):
  * R2 pure-UV body population vs the old fam-gated one (old vs new saturation).
  * R2 dressed-cell BFS band histogram -> fringe concentration + the NEW penetration fraction (band>=2).
  * R3 ecotone-reachable backing: flood 8-conn from the boundary-desert skin through mass cells
    {16,17,19,20,41}; count reachable backing-topo {17,19,20,41} cells + largest component.

No game writes. Output -> out/contract_mass/measure_v2.json.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
sys.path.insert(0, str(REPO_ROOT / "ff9mapkit"))
sys.path.insert(0, str(HERE))

import contract_mass_gates as GT       # noqa: E402
import seam_null_recon as SNR          # noqa: E402

OUT = HERE / "out" / "contract_mass" / "measure_v2.json"
DESERT_TOPOS = frozenset({16, 17, 19, 20})
BACKING_TOPOS = frozenset({17, 19, 20, 41})
MASS_TOPOS = frozenset({16, 17, 19, 20, 41})


def uv_desert_body_class(uv3):
    """Pure-UV desert-body class, INDEPENDENT of fam/topo. Returns ('dressed_gd',k)/('dressed_dd',k)/
    ('desert_mains',None) or None. A tri is in the desert body iff this is not None."""
    k = SNR.classify_strip_pair(uv3, SNR.GD_DU, SNR.GD_DV)
    if k is not None:
        return ("dressed_gd", k)
    k2 = SNR.classify_strip_pair(uv3, SNR.DD_DU, SNR.DD_DV)
    if k2 is not None:
        return ("dressed_dd", k2)
    if SNR.in_rect(uv3, SNR.RECTS["desert"]):
        return ("desert_mains", None)
    return None


def corrected_body(core_tris):
    """UV-driven desert body, EXCLUDING only the legit OPPOSITE-side decals (gd-decal on fam grass,
    dd-decal on fam dunes -- stock's transition tiles' non-desert half). Everything else UV-dressed or
    desert-mains lands in the body; fam/topo is a reported cross-check. Reproduces stock 422/0.5024."""
    body = []
    n_topo_not16 = 0
    n_fam_not_desert = 0
    excl_grass_gd = 0
    excl_dunes_dd = 0
    for t in core_tris:
        k_gd = SNR.classify_strip_pair(t["uv"], SNR.GD_DU, SNR.GD_DV)
        k_dd = SNR.classify_strip_pair(t["uv"], SNR.DD_DU, SNR.DD_DV)
        if k_gd is not None:
            if t["fam"] == "grass":
                excl_grass_gd += 1
                continue
            body.append((t, "strip_grass_desert", k_gd))
        elif k_dd is not None:
            if t["fam"] == "dunes":
                excl_dunes_dd += 1
                continue
            body.append((t, "strip_desert_dunes", k_dd))
        elif SNR.in_rect(t["uv"], SNR.RECTS["desert"]):
            body.append((t, "mains_own", "desert"))
        else:
            continue
        if t["topo"] != 16:
            n_topo_not16 += 1
        if t["fam"] != "desert":
            n_fam_not_desert += 1
    return body, dict(n_topo_not16=n_topo_not16, n_fam_not_desert=n_fam_not_desert,
                      excluded_grass_side_gd=excl_grass_gd, excluded_dunes_side_dd=excl_dunes_dd)


def measure_body(core_tris):
    # OLD fam-gated body (v2 current)
    old_body, _ = GT.label_blind_desert_body(core_tris)
    old_total = len(old_body)
    old_gd = sum(1 for (_t, c, _d) in old_body if c == "strip_grass_desert")
    old_dd = sum(1 for (_t, c, _d) in old_body if c == "strip_desert_dunes")
    # NEW pure-UV body
    new_body = []
    fam_disagree = Counter()
    topo_disagree = Counter()
    for t in core_tris:
        cl = uv_desert_body_class(t["uv"])
        if cl is None:
            continue
        new_body.append((t, cl))
        if t["fam"] != "desert":
            fam_disagree[str(t["fam"])] += 1
        if t["topo"] != 16:
            topo_disagree[t["topo"]] += 1
    new_total = len(new_body)
    new_gd = sum(1 for (_t, (k, _)) in new_body if k == "dressed_gd")
    new_dd = sum(1 for (_t, (k, _)) in new_body if k == "dressed_dd")
    return dict(
        old=dict(total=old_total, gd=old_gd, dd=old_dd,
                 sat_grass=round(old_gd / old_total, 4), sat_any=round((old_gd + old_dd) / old_total, 4)),
        new=dict(total=new_total, gd=new_gd, dd=new_dd,
                 sat_grass=round(new_gd / new_total, 4), sat_any=round((new_gd + new_dd) / new_total, 4),
                 fam_disagreement=dict(fam_disagree), topo_disagreement=dict(topo_disagree)),
    )


def measure_arrangement(cand):
    core = cand["core_tris"]
    boundary_cells = cand["boundary_cells"]
    body, _x = corrected_body(core)
    body_cells = {t["cell"] for (t, _c, _d) in body}
    dressed = [t for (t, c, _d) in body if c in ("strip_grass_desert", "strip_desert_dunes")]
    dist = SNR.cell_distance_bfs(body_cells, boundary_cells)
    band_hist = Counter()
    unreached = 0
    for t in dressed:
        d = dist.get(t["cell"])
        if d is None:
            unreached += 1
        else:
            band_hist[d] += 1
    n = len(dressed)
    band0 = band_hist.get(0, 0)
    ge2 = sum(v for b, v in band_hist.items() if b >= 2) + unreached
    return dict(
        n_dressed=n, band_hist={str(k): v for k, v in sorted(band_hist.items())},
        unreached=unreached,
        fringe_concentration=round(band0 / n, 4) if n else None,
        penetration_ge2_fraction=round(ge2 / n, 4) if n else None,
    )


def measure_r3_adjacency(cand):
    tris = cand["tris"]
    by_gid = cand["by_gid"]
    eo = SNR.edge_index(tris)
    boundary_desert = set()
    for e, owners in eo.items():
        fams = {by_gid[g]["fam"] for g in owners}
        if "grass" in fams and "desert" in fams:
            for g in owners:
                t = by_gid[g]
                if t["fam"] == "desert" and t["block"] in cand["core_set"]:
                    boundary_desert.add(t["cell"])
    mass_cells = set()
    backing_cells = set()
    for t in tris:
        if t["topo"] in MASS_TOPOS:
            mass_cells.add(t["cell"])
        if t["topo"] in BACKING_TOPOS:
            backing_cells.add(t["cell"])
    # flood 8-conn from boundary_desert through mass_cells
    seed = boundary_desert & mass_cells
    reachable = set(seed)
    q = deque(seed)
    while q:
        u = q.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nb = (u[0] + dx, u[1] + dy)
                if nb in mass_cells and nb not in reachable:
                    reachable.add(nb)
                    q.append(nb)
    backing_reachable = reachable & backing_cells
    # largest 8-conn component within backing_reachable
    seen = set()
    comps = []
    for s in backing_reachable:
        if s in seen:
            continue
        comp = [s]
        seen.add(s)
        qq = deque([s])
        while qq:
            u = qq.popleft()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nb = (u[0] + dx, u[1] + dy)
                    if nb in backing_reachable and nb not in seen:
                        seen.add(nb)
                        comp.append(nb)
                        qq.append(nb)
        comps.append(len(comp))
    comps.sort(reverse=True)
    # also the OLD whole-region backing largest (v2 current)
    all_backing = backing_cells
    seen2 = set()
    allcomps = []
    for s in all_backing:
        if s in seen2:
            continue
        comp = [s]
        seen2.add(s)
        qq = deque([s])
        while qq:
            u = qq.popleft()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == 0 and dy == 0:
                        continue
                    nb = (u[0] + dx, u[1] + dy)
                    if nb in all_backing and nb not in seen2:
                        seen2.add(nb)
                        comp.append(nb)
                        qq.append(nb)
        allcomps.append(len(comp))
    allcomps.sort(reverse=True)
    return dict(
        n_boundary_desert=len(boundary_desert), n_mass_cells=len(mass_cells),
        n_backing_cells=len(backing_cells),
        n_reachable_mass=len(reachable), n_backing_reachable=len(backing_reachable),
        reachable_backing_components=comps[:8],
        largest_reachable_backing=comps[0] if comps else 0,
        old_wholeregion_backing_components=allcomps[:8],
        old_wholeregion_largest=allcomps[0] if allcomps else 0,
    )


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    stock = GT.load_candidate("stock", None, core_blocks=GT.ECOTONE_CORE)
    body = measure_body(stock["core_tris"])
    cbody, cx = corrected_body(stock["core_tris"])
    cgd = sum(1 for (_t, c, _d) in cbody if c == "strip_grass_desert")
    cdd = sum(1 for (_t, c, _d) in cbody if c == "strip_desert_dunes")
    ct = len(cbody)
    corrected = dict(total=ct, gd=cgd, dd=cdd,
                     sat_grass=round(cgd / ct, 4), sat_any=round((cgd + cdd) / ct, 4), xcheck=cx)
    arr = measure_arrangement(stock)
    r3 = measure_r3_adjacency(stock)
    out = dict(body=body, corrected_body=corrected, arrangement=arr, r3_adjacency=r3)
    print(json.dumps(out, indent=1))
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"-> {OUT}")


if __name__ == "__main__":
    main()
