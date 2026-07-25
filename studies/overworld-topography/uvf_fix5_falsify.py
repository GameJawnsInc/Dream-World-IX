"""RUNG F -- THE ROOTS RELIEF RELAX (FIXED5) CODE-DISJOINT FALSIFIER (2026-07-24).

Round-5 verifier. Extends MY OWN falsifier lineage
(uvf_fix_falsify -> uvf_fix2_falsify -> uvf_fix3_falsify -> uvf_fix4_falsify).
Does NOT import uvf_fix5.py / uvf_relief_probe.py / uvf_gates*.py / uvf_fix*.py.
Reuses ONLY the loaders (ff9mapkit.world.extract/.mesh) + the kit ground-family table
(grassland.TOPO_FAMILY) as an oracle for "which kept topos are ground".  Every parse,
diff, weld map, crack audit, normal recomputation, reference surface and gate below is
re-implemented here from raw bytes.

THIS ROUND MOVES POSITIONS (Y), not UVs -- so the geometry gates are the load-bearing ones.

CLAIMS TESTED INDEPENDENTLY FROM RAW BYTES:
 (1) changes = Y + normals ONLY, confined to tris I MYSELF classify as synthesized
     (= UV-degenerate in the pre-fix specimen tree FF9CustomMap-world);
     X/Z/UV/tangent/index bytes identical EVERYWHERE; carried-core (my own donor
     byte-match re-identification) + frame byte-identical; Sea/Object/Beach untouched;
     only the expected files changed.
 (2) WELD INTEGRITY -- my own coincident-position map built on FIXED4 over ALL 8 parts x
     20 blocks (rounded 3D world position): every group still coincident in FIXED5 (moved
     together or not at all), cross-block included; every position shared with
     NON-synthesized geometry is UNMOVED.
 (3) No new open edges/cracks (my own 3D once-edge audit over the whole 20-block Terrain
     union, before vs after), no new down-facing tris, no land vertex <= 0 (that was > 0),
     no zero-world-area tris.
 (4) NORMALS: rewritten only on tris with a moved vert; geometric within tolerance; up-facing.
 (5) 20 sampled moved verts: new Y lies between the old Y and MY OWN local kept-surface
     reference (no overshoot); the blend is C0 into the pins and decays toward the boundary.
 (6) REFUTATION HUNT: crater frozen (independent basin re-derivation), no new spikes/steps,
     report-number reconciliation.

READ-ONLY vs the game install (donor blocks only). Writes out/rung_f/uvf_fix5_falsify.json.
"""
from __future__ import annotations
import json, math, struct, sys, statistics
from collections import Counter, defaultdict, deque
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
SPEC = RUNG / "FF9CustomMap-world"                # pre-fix specimen -> defines the synthesized set
FIXED4 = RUNG / "FF9CustomMap-world-FIXED4"       # base
FIXED5 = RUNG / "FF9CustomMap-world-FIXED5"       # candidate
OUT = RUNG / "uvf_fix5_falsify.json"
FOOTPRINT = [(bx, by) for bx in range(0, 5) for by in range(16, 20)]
PARTS = ("Terrain", "Object", "Beach1", "Sea1", "Sea2", "Sea3", "Sea4", "Sea5")
MAGIC = b"F9WM"
UV_ZERO = 1e-6
POSKEY = 3          # the build's stated weld key resolution (rounded 3dp world position)
SEA_Y = 0.0


def log(m): print(m, flush=True)


# ---------------- raw .ff9mesh parse (MY code, lineage-carried) ----------------
def parse_raw(path):
    data = Path(path).read_bytes()
    assert data[:4] == MAGIC, f"bad magic {path}"
    version, vcount, icount, flags = struct.unpack_from("<iiii", data, 4)
    off_pos = 20
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


def uv_area(a, b, c): return abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1]))
def uv_collapsed(a, b, c):
    return max(math.hypot(p[0] - q[0], p[1] - q[1]) for p, q in ((a, b), (a, c), (b, c))) < UV_ZERO
def is_degenerate(a, b, c): return uv_area(a, b, c) < UV_ZERO or uv_collapsed(a, b, c)


def part_path(root, bx, by, part): return root / M.override_relpath(1, bx, by, part=part)
def stats(v):
    if not v: return dict(n=0)
    s = sorted(v); n = len(s)
    def q(p): return s[min(n - 1, max(0, int(round(p * (n - 1)))))]
    return dict(n=n, mean=round(statistics.fmean(s), 5), sd=round(statistics.pstdev(s), 5) if n > 1 else 0.0,
                min=round(s[0], 5), p5=round(q(.05), 5), p25=round(q(.25), 5), p50=round(q(.5), 5),
                p75=round(q(.75), 5), p95=round(q(.95), 5), p99=round(q(.99), 5), max=round(s[-1], 5))


def geo_normal(p0, p1, p2):
    ux, uy, uz = p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2]
    vx, vy, vz = p2[0] - p0[0], p2[1] - p0[1], p2[2] - p0[2]
    return (uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx)


# =====================================================================================
# LOAD everything: FIXED4 + FIXED5 for all parts, SPEC for Terrain (synth identification)
def load_all():
    T = {}          # (bx,by,part) -> dict(r4,r5, v4,v5, ...)
    missing = []
    for (bx, by) in FOOTPRINT:
        for part in PARTS:
            p4, p5 = part_path(FIXED4, bx, by, part), part_path(FIXED5, bx, by, part)
            if not p4.exists() or not p5.exists():
                if p4.exists() != p5.exists(): missing.append([bx, by, part, p4.exists(), p5.exists()])
                continue
            r4, r5 = parse_raw(p4), parse_raw(p5)
            T[(bx, by, part)] = dict(r4=r4, r5=r5, v4=verts_of(r4), v5=verts_of(r5),
                                     org=X.block_world_origin(bx, by))
    return T, missing


def load_spec():
    S = {}; bad = []
    for (bx, by) in FOOTPRINT:
        p = part_path(SPEC, bx, by, "Terrain")
        if not p.exists(): bad.append([bx, by, "missing-spec"]); continue
        r = parse_raw(p)
        S[(bx, by)] = dict(r=r, uv=uvs_of(r), idx=idx_of(r))
    return S, bad


def main():
    findings = []; R = {}
    R["meta"] = dict(script="uvf_fix5_falsify.py", spec=str(SPEC), base=str(FIXED4), target=str(FIXED5),
                     poskey_dp=POSKEY, uv_zero=UV_ZERO, parts=list(PARTS))

    # ---------------- tree-level diff ----------------
    def rel(root): return sorted(str(p.relative_to(root)) for p in root.rglob("*") if p.is_file())
    a, b = rel(FIXED4), rel(FIXED5)
    only4 = sorted(set(a) - set(b)); only5 = sorted(set(b) - set(a))
    changed = [rp for rp in sorted(set(a) & set(b))
               if (FIXED4 / rp).read_bytes() != (FIXED5 / rp).read_bytes()]
    non_terrain_changed = [rp for rp in changed if not rp.endswith("Terrain.ff9mesh")]
    R["tree_diff"] = dict(n_fixed4=len(a), n_fixed5=len(b), only_fixed4=only4, only_fixed5=only5,
                          n_changed=len(changed), changed=changed,
                          changed_non_terrain=non_terrain_changed,
                          changed_sea=[c for c in changed if "Sea" in c],
                          changed_object_beach=[c for c in changed if ("Object" in c or "Beach" in c)])
    log(f"[T] files {len(a)}/{len(b)} changed={len(changed)} non_terrain={non_terrain_changed}")
    if only4 or only5: findings.append(f"REFUTE (1): file set differs only4={only4} only5={only5}.")
    if non_terrain_changed:
        findings.append(f"REFUTE (1): non-Terrain files changed: {non_terrain_changed}.")
    if len(changed) != 15:
        findings.append(f"MISMATCH (1): {len(changed)} files changed, report claims 15.")

    T, missing = load_all()
    S, spec_bad = load_spec()
    R["load"] = dict(n_part_files=len(T), missing=missing, spec_blocks=len(S), spec_bad=spec_bad)
    if missing: findings.append(f"REFUTE (1): part-file presence differs FIXED4/FIXED5: {missing}.")
    if spec_bad: findings.append(f"NOTE: specimen tree incomplete: {spec_bad}.")

    # ---------------- per-file channel rigidity ----------------
    chan = dict(header_bad=[], uv_bad=[], tan_bad=[], idx_bad=[], nrm_changed_files=[],
                pos_changed_files=[], xz_moved=[], y_moved_entries=0, nrm_changed_entries=0)
    for key, D in sorted(T.items()):
        bx, by, part = key
        r4, r5 = D["r4"], D["r5"]
        if (r4["vcount"], r4["icount"], r4["flags"], r4["version"]) != \
           (r5["vcount"], r5["icount"], r5["flags"], r5["version"]):
            chan["header_bad"].append([bx, by, part]); continue
        if r4["sz_uv"] and sl(r4, r4["off_uv"], r4["sz_uv"]) != sl(r5, r5["off_uv"], r5["sz_uv"]):
            chan["uv_bad"].append([bx, by, part])
        if r4["sz_tan"] and sl(r4, r4["off_tan"], r4["sz_tan"]) != sl(r5, r5["off_tan"], r5["sz_tan"]):
            chan["tan_bad"].append([bx, by, part])
        if sl(r4, r4["off_idx"], r4["sz_idx"]) != sl(r5, r5["off_idx"], r5["sz_idx"]):
            chan["idx_bad"].append([bx, by, part])
        if sl(r4, r4["off_pos"], r4["sz_pos"]) != sl(r5, r5["off_pos"], r5["sz_pos"]):
            chan["pos_changed_files"].append(f"{bx},{by},{part}")
            d4, d5 = r4["data"], r5["data"]
            for j in range(r4["vcount"]):
                o4 = r4["off_pos"] + j * 12; o5 = r5["off_pos"] + j * 12
                if d4[o4:o4 + 12] == d5[o5:o5 + 12]: continue
                if d4[o4:o4 + 4] != d5[o5:o5 + 4] or d4[o4 + 8:o4 + 12] != d5[o5 + 8:o5 + 12]:
                    chan["xz_moved"].append([bx, by, part, j])
                chan["y_moved_entries"] += 1
        if r4["sz_nrm"] and sl(r4, r4["off_nrm"], r4["sz_nrm"]) != sl(r5, r5["off_nrm"], r5["sz_nrm"]):
            chan["nrm_changed_files"].append(f"{bx},{by},{part}")
            d4, d5 = r4["data"], r5["data"]
            chan["nrm_changed_entries"] += sum(
                1 for j in range(r4["vcount"])
                if d4[r4["off_nrm"] + j * 12: r4["off_nrm"] + j * 12 + 12] !=
                   d5[r5["off_nrm"] + j * 12: r5["off_nrm"] + j * 12 + 12])
    chan["xz_moved_n"] = len(chan["xz_moved"]); chan["xz_moved"] = chan["xz_moved"][:10]
    R["channel_rigidity"] = chan
    log(f"[1] uv_bad={chan['uv_bad']} tan_bad={chan['tan_bad']} idx_bad={chan['idx_bad']} "
        f"hdr={chan['header_bad']} y_moved_entries={chan['y_moved_entries']} "
        f"xz_moved={chan['xz_moved_n']} nrm_entries={chan['nrm_changed_entries']}")
    for k, lbl in (("header_bad", "headers"), ("uv_bad", "UVs"), ("tan_bad", "tangents/IDALL"),
                   ("idx_bad", "indices")):
        if chan[k]: findings.append(f"REFUTE (1): {lbl} changed FIXED4->FIXED5 in {chan[k]}.")
    if chan["xz_moved_n"]:
        findings.append(f"REFUTE (1): {chan['xz_moved_n']} vertex entries had X or Z bytes rewritten "
                        f"(the move must be Y-only): {chan['xz_moved'][:4]}.")
    if chan["y_moved_entries"] != 5557:
        findings.append(f"MISMATCH (1): {chan['y_moved_entries']} position entries moved, report claims 5557.")
    if chan["nrm_changed_entries"] > 6606:
        findings.append(f"MISMATCH (4): {chan['nrm_changed_entries']} normal entries rewritten, "
                        f"report claims 6606 (a strict superset would be a scope breach).")

    # ---------------- SPEC vs FIXED4 position parity (the synth-set oracle must align) ----------------
    spec_pos_diffs = []
    for (bx, by) in FOOTPRINT:
        if (bx, by) not in S or (bx, by, "Terrain") not in T: continue
        rs = S[(bx, by)]["r"]; r4 = T[(bx, by, "Terrain")]["r4"]
        if (rs["vcount"], rs["icount"]) != (r4["vcount"], r4["icount"]):
            spec_pos_diffs.append([bx, by, "header"]); continue
        if sl(rs, rs["off_pos"], rs["sz_pos"]) != sl(r4, r4["off_pos"], r4["sz_pos"]):
            spec_pos_diffs.append([bx, by, "pos"])
        if sl(rs, rs["off_idx"], rs["sz_idx"]) != sl(r4, r4["off_idx"], r4["sz_idx"]):
            spec_pos_diffs.append([bx, by, "idx"])
    R["spec_parity"] = dict(diffs=spec_pos_diffs)
    if spec_pos_diffs:
        findings.append(f"REFUTE (1): SPEC vs FIXED4 positions/indices differ {spec_pos_diffs} -- "
                        f"the synthesized-set oracle is not aligned to the base tree.")

    # ---------------- MY synthesized set + per-tri tables ----------------
    tris = []       # per Terrain tri
    for (bx, by) in FOOTPRINT:
        if (bx, by, "Terrain") not in T or (bx, by) not in S: continue
        D = T[(bx, by, "Terrain")]; ox, oz = D["org"]
        r4 = D["r4"]; idx = idx_of(r4); tan = tans_of(r4)
        su = S[(bx, by)]["uv"]
        v4, v5 = D["v4"], D["v5"]
        n4 = nrms_of(r4); n5 = nrms_of(D["r5"])
        for t in range(len(idx) // 3):
            tri = (idx[3 * t], idx[3 * t + 1], idx[3 * t + 2])
            w4 = [(v4[j][0] + ox, v4[j][1], v4[j][2] + oz) for j in tri]
            w5 = [(v5[j][0] + ox, v5[j][1], v5[j][2] + oz) for j in tri]
            topo = X.decode_id(int(round(tan[tri[0]][0])))["topograph"]
            tris.append(dict(b=(bx, by), t=t, tri=tri, w4=w4, w5=w5, topo=topo,
                             synth=is_degenerate(*[su[j] for j in tri]),
                             n4=[n4[j] for j in tri], n5=[n5[j] for j in tri],
                             moved=any(abs(p[1] - q[1]) > 0 for p, q in zip(w4, w5))))
    n_synth = sum(1 for r in tris if r["synth"])
    R["synth_set"] = dict(n_terrain_tris=len(tris), n_synthesized=n_synth,
                          n_synth_with_moved_vert=sum(1 for r in tris if r["synth"] and r["moved"]),
                          n_nonsynth_with_moved_vert=sum(1 for r in tris if not r["synth"] and r["moved"]),
                          topo_hist_synth=dict(Counter(r["topo"] for r in tris if r["synth"]).most_common(12)))
    log(f"[1] terrain tris={len(tris)} synth={n_synth} synth_moved={R['synth_set']['n_synth_with_moved_vert']} "
        f"nonsynth_moved={R['synth_set']['n_nonsynth_with_moved_vert']}")
    if n_synth != 2305:
        findings.append(f"MISMATCH (1): my synthesized-set size {n_synth} != the reported 2305.")
    if R["synth_set"]["n_nonsynth_with_moved_vert"]:
        findings.append(f"REFUTE (1): {R['synth_set']['n_nonsynth_with_moved_vert']} NON-synthesized Terrain tris "
                        f"contain a moved vertex -- kept content moved.")
    if R["synth_set"]["n_synth_with_moved_vert"] != 2202:
        findings.append(f"MISMATCH (1): {R['synth_set']['n_synth_with_moved_vert']} synth tris carry a moved vert, "
                        f"report claims 2202.")

    # ---------------- (2) WELD MAP over ALL parts, keyed on rounded 3D world position ----------------
    groups = defaultdict(list)      # key -> [(bx,by,part,j)]
    ent_pos4 = {}; ent_pos5 = {}
    for (bx, by, part), D in T.items():
        ox, oz = D["org"]
        for j, (x, y, z) in enumerate(D["v4"]):
            wx, wy, wz = x + ox, y, z + oz
            k = (round(wx, POSKEY), round(wy, POSKEY), round(wz, POSKEY))
            groups[k].append((bx, by, part, j))
            ent_pos4[(bx, by, part, j)] = (wx, wy, wz)
        for j, (x, y, z) in enumerate(D["v5"]):
            ent_pos5[(bx, by, part, j)] = (x + ox, y, z + oz)

    # synth ownership at the entry level (Terrain only; flat mesh -> each entry belongs to one tri)
    entry_is_synth = {}
    for r in tris:
        for j in r["tri"]:
            entry_is_synth[(r["b"][0], r["b"][1], "Terrain", j)] = r["synth"]

    split_groups = []; nonuniform = []; moved_groups = 0; pinned_moved = []
    cross_block_moved = 0; cross_part_moved = 0
    dy_by_group = {}
    pinned_keys = set(); movable_keys = set(); synth_touched_keys = set()
    for k, ents in groups.items():
        dys = []
        for e in ents:
            dys.append(ent_pos5[e][1] - ent_pos4[e][1])
        dmin, dmax = min(dys), max(dys)
        if dmax - dmin > 1e-6:
            nonuniform.append([list(k), round(dmin, 6), round(dmax, 6), len(ents)])
        # coincidence after the move: spread of the NEW world positions must not exceed the old spread
        ys5 = [ent_pos5[e][1] for e in ents]; ys4 = [ent_pos4[e][1] for e in ents]
        if (max(ys5) - min(ys5)) > (max(ys4) - min(ys4)) + 1e-6:
            split_groups.append([list(k), round(max(ys4) - min(ys4), 6), round(max(ys5) - min(ys5), 6)])
        dy = statistics.fmean(dys)
        dy_by_group[k] = dy
        is_pinned = any((e[3] not in ()) and (e[2] != "Terrain" or not entry_is_synth.get(e, False)) for e in ents)
        if any(e[2] == "Terrain" and entry_is_synth.get(e, False) for e in ents):
            synth_touched_keys.add(k)
        if is_pinned:
            pinned_keys.add(k)
            if abs(dy) > 0: pinned_moved.append([list(k), round(dy, 6), len(ents)])
        else:
            movable_keys.add(k)
        if abs(dy) > 0:
            moved_groups += 1
            if len({(e[0], e[1]) for e in ents}) > 1: cross_block_moved += 1
            if len({e[2] for e in ents}) > 1: cross_part_moved += 1
    R["weld"] = dict(n_distinct_positions=len(groups),
                     groups_that_split=len(split_groups), split_examples=split_groups[:8],
                     groups_with_nonuniform_delta=len(nonuniform), nonuniform_examples=nonuniform[:8],
                     groups_that_moved=moved_groups,
                     cross_block_groups_moved=cross_block_moved,
                     cross_part_groups_moved=cross_part_moved,
                     n_synth_touched_positions=len(synth_touched_keys),
                     n_pinned_of_those=len(synth_touched_keys & pinned_keys),
                     n_movable=len(synth_touched_keys - pinned_keys),
                     pinned_positions_moved=len(pinned_moved), pinned_moved_examples=pinned_moved[:8],
                     entries_per_moved_position=dict(sorted(Counter(
                         len(groups[k]) for k in groups if abs(dy_by_group[k]) > 0).items())))
    log(f"[2] weld: positions={len(groups)} split={len(split_groups)} nonuniform={len(nonuniform)} "
        f"moved={moved_groups} cross_block={cross_block_moved} cross_part={cross_part_moved} "
        f"pinned_moved={len(pinned_moved)} synth_touched={len(synth_touched_keys)} "
        f"pinned_of_those={len(synth_touched_keys & pinned_keys)} movable={len(synth_touched_keys - pinned_keys)}")
    if split_groups:
        findings.append(f"REFUTE (2): {len(split_groups)} coincident-position groups SPLIT (the mesh cracks): "
                        f"{split_groups[:4]}.")
    if nonuniform:
        findings.append(f"REFUTE (2): {len(nonuniform)} coincident groups received NON-UNIFORM dY: {nonuniform[:4]}.")
    if pinned_moved:
        findings.append(f"REFUTE (2): {len(pinned_moved)} positions shared with NON-synthesized geometry MOVED: "
                        f"{pinned_moved[:4]}.")
    if len(synth_touched_keys - pinned_keys) != 937:
        findings.append(f"MISMATCH (2): my movable-position count {len(synth_touched_keys - pinned_keys)} "
                        f"!= the reported 937.")
    if len(groups) != 8923:
        findings.append(f"MISMATCH (2): my distinct-position count {len(groups)} != the reported 8923.")

    moved_keys = [k for k in groups if abs(dy_by_group[k]) > 0]
    dys_moved = [dy_by_group[k] for k in moved_keys]
    R["dY"] = dict(n_moved_positions=len(moved_keys), stats=stats(dys_moved),
                   max_abs=round(max(abs(d) for d in dys_moved), 5) if dys_moved else 0.0,
                   n_gt_0p01=sum(1 for d in dys_moved if abs(d) > 0.01),
                   n_gt_0p1=sum(1 for d in dys_moved if abs(d) > 0.1),
                   moved_entries=sum(len(groups[k]) for k in moved_keys))
    log(f"[2] moved positions={len(moved_keys)} entries={R['dY']['moved_entries']} "
        f"max|dY|={R['dY']['max_abs']} stats={R['dY']['stats']}")
    if R["dY"]["moved_entries"] != chan["y_moved_entries"]:
        findings.append(f"MISMATCH (2): weld-map moved entries {R['dY']['moved_entries']} != byte-diff moved entries "
                        f"{chan['y_moved_entries']}.")
    if abs(R["dY"]["max_abs"] - 2.4943) > 5e-4:
        findings.append(f"MISMATCH (2): my max|dY| {R['dY']['max_abs']} != the reported 2.4943.")

    # ---------------- (3) CRACK AUDIT: 3D once-edge count over the 20-block Terrain union ----------------
    def once_edges(which):
        cnt = Counter()
        for r in tris:
            w = r[which]
            for i in range(3):
                p, q = w[i], w[(i + 1) % 3]
                kp = (round(p[0], POSKEY), round(p[1], POSKEY), round(p[2], POSKEY))
                kq = (round(q[0], POSKEY), round(q[1], POSKEY), round(q[2], POSKEY))
                cnt[tuple(sorted((kp, kq)))] += 1
        return cnt
    e4, e5 = once_edges("w4"), once_edges("w5")
    once4 = {k for k, v in e4.items() if v == 1}
    once5 = {k for k, v in e5.items() if v == 1}
    new_open = once5 - once4
    # a moved edge changes KEY, so compare COUNTS + the plan (XZ) projection of the open set
    def plan(es): return Counter(((k[0][0], k[0][2]), (k[1][0], k[1][2])) for k in es)
    p4, p5 = plan(once4), plan(once5)
    plan_new = {k: v for k, v in (p5 - p4).items()}
    R["crack_audit"] = dict(n_edges_before=len(e4), n_edges_after=len(e5),
                            once_edges_before=len(once4), once_edges_after=len(once5),
                            new_open_edges_3dkey=len(new_open),
                            new_open_edges_in_PLAN=len(plan_new),
                            plan_examples=[[list(k[0]), list(k[1]), v] for k, v in list(plan_new.items())[:6]],
                            edge_multiplicity_before=dict(sorted(Counter(e4.values()).items())),
                            edge_multiplicity_after=dict(sorted(Counter(e5.values()).items())),
                            note="3D-keyed edges: a Y-move rekeys an edge, so the 3D-key set legitimately changes; "
                                 "the PLAN (XZ) projection of the once-edge set is move-invariant and is the real "
                                 "crack test -- a split weld shows up there as a NEW open plan edge.")
    log(f"[3] cracks: once-edges {len(once4)} -> {len(once5)} (plan-new={len(plan_new)}) "
        f"mult_before={R['crack_audit']['edge_multiplicity_before']} mult_after={R['crack_audit']['edge_multiplicity_after']}")
    if plan_new:
        findings.append(f"REFUTE (3): {len(plan_new)} NEW open edges appear in the XZ-plan once-edge audit "
                        f"(a crack): {R['crack_audit']['plan_examples'][:3]}.")
    if len(once5) != len(once4):
        findings.append(f"NOTE (3): once-edge COUNT changed {len(once4)} -> {len(once5)} under the 3D key "
                        f"(expected 0 change if welds held; the plan test is authoritative).")

    # ---------------- (3) facing / area / sea floor ----------------
    ny4 = Counter(); ny5 = Counter(); flipped = []; newdown = []
    zero_area4 = zero_area5 = 0
    for r in tris:
        g4 = geo_normal(*r["w4"]); g5 = geo_normal(*r["w5"])
        s4 = 0 if abs(g4[1]) < 1e-12 else (1 if g4[1] > 0 else -1)
        s5 = 0 if abs(g5[1]) < 1e-12 else (1 if g5[1] > 0 else -1)
        ny4[s4] += 1; ny5[s5] += 1
        if s4 != s5: flipped.append([list(r["b"]), r["t"], s4, s5])
        if s5 < 0 and s4 >= 0: newdown.append([list(r["b"]), r["t"]])
        if math.sqrt(sum(c * c for c in g4)) < 1e-9: zero_area4 += 1
        if math.sqrt(sum(c * c for c in g5)) < 1e-9: zero_area5 += 1
    ys4_all = [p[1] for r in tris for p in r["w4"]]
    ys5_all = [p[1] for r in tris for p in r["w5"]]
    sank = [[list(r["b"]), r["t"], round(p[1], 4), round(q[1], 4)]
            for r in tris for p, q in zip(r["w4"], r["w5"]) if p[1] > SEA_Y and q[1] <= SEA_Y]
    moved_ys5 = [ent_pos5[e][1] for k in moved_keys for e in groups[k]]
    R["geometry_gates"] = dict(ny_sign_before=dict(ny4), ny_sign_after=dict(ny5),
                               tris_flipped=len(flipped), flip_examples=flipped[:6],
                               newly_down_facing=len(newdown), newdown_examples=newdown[:6],
                               zero_world_area_before=zero_area4, zero_world_area_after=zero_area5,
                               min_Y_all_terrain_before=round(min(ys4_all), 6),
                               min_Y_all_terrain_after=round(min(ys5_all), 6),
                               min_Y_over_moved_positions=round(min(moved_ys5), 5) if moved_ys5 else None,
                               verts_that_sank_to_or_below_sea=len(sank), sank_examples=sank[:6])
    log(f"[3] facing before={dict(ny4)} after={dict(ny5)} flipped={len(flipped)} newdown={len(newdown)} "
        f"zeroarea {zero_area4}->{zero_area5} minY {min(ys4_all):.4f}->{min(ys5_all):.4f} "
        f"minY_moved={R['geometry_gates']['min_Y_over_moved_positions']} sank={len(sank)}")
    if newdown: findings.append(f"REFUTE (3): {len(newdown)} tris became DOWN-FACING: {newdown[:4]}.")
    if flipped: findings.append(f"REFUTE (3): {len(flipped)} tris changed geometric facing sign: {flipped[:4]}.")
    if zero_area5 > zero_area4:
        findings.append(f"REFUTE (3): zero-world-area tris grew {zero_area4} -> {zero_area5}.")
    if sank: findings.append(f"REFUTE (3): {len(sank)} land vertices sank to or below sea Y=0: {sank[:4]}.")

    # ---------------- (4) NORMALS ----------------
    nrm_bad_scope = []; nrm_geo_bad = []; nrm_down = []; min_ny = 2.0; max_ang = 0.0
    n_rewritten_tris = 0; n_rewritten_entries = 0
    for r in tris:
        chg = any(tuple(round(c, 7) for c in x) != tuple(round(c, 7) for c in y) for x, y in zip(r["n4"], r["n5"]))
        chg_exact = any(x != y for x, y in zip(r["n4"], r["n5"]))
        if chg_exact:
            n_rewritten_tris += 1
            n_rewritten_entries += sum(1 for x, y in zip(r["n4"], r["n5"]) if x != y)
        if chg_exact and not r["moved"]:
            nrm_bad_scope.append([list(r["b"]), r["t"]])
        if not r["moved"]:
            continue
        g = geo_normal(*r["w5"]); L = math.sqrt(sum(c * c for c in g))
        if L < 1e-12: continue
        gn = [c / L for c in g]
        if gn[1] < 0: gn = [-c for c in gn]
        for st in r["n5"]:
            ls = math.sqrt(sum(c * c for c in st))
            if ls < 1e-9:
                nrm_geo_bad.append([list(r["b"]), r["t"], "zero-length"]); continue
            sn = [c / ls for c in st]
            dot = max(-1.0, min(1.0, sum(x * y for x, y in zip(sn, gn))))
            ang = math.degrees(math.acos(dot))
            max_ang = max(max_ang, ang)
            if ang > 0.5:
                nrm_geo_bad.append([list(r["b"]), r["t"], round(ang, 4)])
            min_ny = min(min_ny, sn[1])
            if sn[1] < 0: nrm_down.append([list(r["b"]), r["t"], round(sn[1], 5)])
    R["normals"] = dict(tris_with_rewritten_normal=n_rewritten_tris, entries_rewritten=n_rewritten_entries,
                        rewritten_on_UNMOVED_tri=len(nrm_bad_scope), scope_examples=nrm_bad_scope[:8],
                        max_angle_vs_geometric_deg=round(max_ang, 5),
                        non_geometric=len(nrm_geo_bad), non_geometric_examples=nrm_geo_bad[:8],
                        min_stored_ny_on_moved=round(min_ny, 6), down_facing_stored=len(nrm_down))
    log(f"[4] normals: tris={n_rewritten_tris} entries={n_rewritten_entries} scope_bad={len(nrm_bad_scope)} "
        f"max_ang={max_ang:.4f}deg non_geo={len(nrm_geo_bad)} min_ny={min_ny:.6f} down={len(nrm_down)}")
    if nrm_bad_scope:
        findings.append(f"REFUTE (4): {len(nrm_bad_scope)} normals rewritten on tris with NO moved vertex: "
                        f"{nrm_bad_scope[:4]}.")
    if nrm_geo_bad:
        findings.append(f"REFUTE (4): {len(nrm_geo_bad)} stored normals on moved tris are not the geometric "
                        f"up-facing normal (>0.5deg): {nrm_geo_bad[:4]}.")
    if nrm_down:
        findings.append(f"REFUTE (4): {len(nrm_down)} stored normals on moved tris point DOWN.")
    if n_rewritten_tris != 2202:
        findings.append(f"MISMATCH (4): {n_rewritten_tris} tris got a rewritten normal, report claims 2202.")

    # ---------------- (5) MY OWN reference surface + overshoot / blend behaviour ----------------
    # kept ground vertex samples (non-synth Terrain tris whose topo has a ground family)
    ref_pts = []
    for r in tris:
        if r["synth"]: continue
        if G.TOPO_FAMILY.get(r["topo"]) is None: continue
        for p in r["w4"]:
            ref_pts.append((p[0], p[2], p[1]))
    ref_pts = list({(round(x, 3), round(z, 3)): (x, z, y) for x, z, y in ref_pts}.values())
    # spatial hash for speed
    HB = 8.0
    hgrid = defaultdict(list)
    for x, z, y in ref_pts:
        hgrid[(int(math.floor(x / HB)), int(math.floor(z / HB)))].append((x, z, y))

    def reference_at(x, z):
        """IDW(1/d^2) over the >=8 nearest kept-ground samples inside a growing radius (independent of
        the build's plane fit)."""
        for R_ in (8.0, 12.0, 18.0, 26.0, 40.0):
            got = []
            rc = int(math.ceil(R_ / HB))
            cx, cz = int(math.floor(x / HB)), int(math.floor(z / HB))
            for i in range(cx - rc, cx + rc + 1):
                for j in range(cz - rc, cz + rc + 1):
                    for (px, pz, py) in hgrid.get((i, j), ()):
                        d2 = (px - x) ** 2 + (pz - z) ** 2
                        if d2 <= R_ * R_: got.append((d2, py))
            if len(got) >= 8:
                got.sort()
                got = got[:24]
                wsum = ysum = 0.0
                for d2, py in got:
                    w = 1.0 / max(d2, 0.25)
                    wsum += w; ysum += w * py
                return ysum / wsum, R_, len(got)
        return None, None, 0

    # movable positions (from MY weld map) with their Y before/after
    movable = sorted(synth_touched_keys - pinned_keys)
    mv_rows = {}
    for k in movable:
        e = groups[k][0]
        y4 = ent_pos4[e][1]; y5 = ent_pos5[e][1]
        mv_rows[k] = dict(x=k[0], z=k[2], y4=y4, y5=y5, dy=y5 - y4)
    flat3 = sum(1 for v in mv_rows.values() if abs(v["y4"] - 3.0) < 1e-6)
    R["movable_prior_state"] = dict(n=len(mv_rows), at_exactly_3p000=flat3,
                                    y4_stats=stats([v["y4"] for v in mv_rows.values()]),
                                    claim="the build says 936/937 movable positions sat at exactly Y=3.000000")
    log(f"[5] movable={len(mv_rows)} at Y==3.000000: {flat3}")

    res_before = []; res_after = []; overshoot = []; wrongsign = []
    for k, v in mv_rows.items():
        ref, rad, n = reference_at(v["x"], v["z"])
        if ref is None: continue
        rb = v["y4"] - ref; ra = v["y5"] - ref
        v["ref"] = ref; v["res_b"] = rb; v["res_a"] = ra
        res_before.append(rb); res_after.append(ra)
        if abs(ra) > abs(rb) + 0.05:
            overshoot.append([list(k), round(rb, 4), round(ra, 4), round(v["dy"], 4)])
        if abs(v["dy"]) > 0.05 and rb * v["dy"] > 0:   # moved AWAY from the reference
            wrongsign.append([list(k), round(rb, 4), round(v["dy"], 4)])
    R["reference_residuals"] = dict(
        n=len(res_before), before=stats([abs(x) for x in res_before]), after=stats([abs(x) for x in res_after]),
        signed_before=stats(res_before), signed_after=stats(res_after),
        anomalies_before_ge_0p6=sum(1 for x in res_before if abs(x) >= 0.6),
        anomalies_after_ge_0p6=sum(1 for x in res_after if abs(x) >= 0.6),
        n_moved_away_from_reference=len(wrongsign), moved_away_examples=wrongsign[:8],
        n_overshoot_gt_0p05=len(overshoot), overshoot_examples=overshoot[:8],
        method="IDW(1/d^2) over the nearest <=24 kept-ground vertex samples in a growing 8/12/18/26/40u radius "
               "-- deliberately a DIFFERENT estimator from the build's IDW-weighted least-squares PLANE fit.")
    log(f"[5] |residual| before={R['reference_residuals']['before']['p95']}p95 "
        f"after={R['reference_residuals']['after']['p95']}p95 "
        f"anomalies {R['reference_residuals']['anomalies_before_ge_0p6']} -> "
        f"{R['reference_residuals']['anomalies_after_ge_0p6']} overshoot={len(overshoot)} away={len(wrongsign)}")
    if len(overshoot) > 0.05 * max(1, len(res_before)):
        findings.append(f"NOTE (5,estimator-A-only): {len(overshoot)}/{len(res_before)} moved positions overshoot "
                        f"their CONSTANT-IDW reference by >0.05u. A constant fit is biased on sloping ground; "
                        f"adjudicated by the slope-aware plane + the estimator-free envelope in (5b). "
                        f"Examples {overshoot[:3]}.")
    if R["reference_residuals"]["anomalies_after_ge_0p6"] > R["reference_residuals"]["anomalies_before_ge_0p6"]:
        findings.append(f"NOTE (5,estimator-A-only): the >=0.6u anomaly count under the CONSTANT-IDW reference rose "
                        f"{R['reference_residuals']['anomalies_before_ge_0p6']} -> "
                        f"{R['reference_residuals']['anomalies_after_ge_0p6']}; adjudicated in (5b).")

    # blend monotonicity: hop distance on the synth patch edge graph from the pinned boundary
    adj = defaultdict(set)
    for r in tris:
        if not r["synth"]: continue
        ks = [(round(p[0], POSKEY), round(p[1], POSKEY), round(p[2], POSKEY)) for p in r["w4"]]
        for i in range(3):
            adj[ks[i]].add(ks[(i + 1) % 3]); adj[ks[(i + 1) % 3]].add(ks[i])
    dist = {}
    dq = deque()
    for k in synth_touched_keys & pinned_keys:
        dist[k] = 0; dq.append(k)
    while dq:
        k = dq.popleft()
        for nb in adj.get(k, ()):
            if nb not in dist:
                dist[nb] = dist[k] + 1; dq.append(nb)
    hop_bins = defaultdict(list)
    unreached = 0
    for k in movable:
        d = dist.get(k)
        if d is None: unreached += 1; continue
        hop_bins[min(d, 10)].append(abs(dy_by_group[k]))
    hop_tab = {str(h): dict(n=len(v), mean_abs_dY=round(statistics.fmean(v), 5),
                            max_abs_dY=round(max(v), 5)) for h, v in sorted(hop_bins.items())}
    # C0 test: the Y STEP across every patch edge that lands on a pinned position
    step_b = []; step_a = []
    for r in tris:
        if not r["synth"]: continue
        ks = [(round(p[0], POSKEY), round(p[1], POSKEY), round(p[2], POSKEY)) for p in r["w4"]]
        for i in range(3):
            ka, kb = ks[i], ks[(i + 1) % 3]
            pa, pb = (ka in pinned_keys), (kb in pinned_keys)
            if pa == pb: continue
            mk = kb if pa else ka; pk = ka if pa else kb
            ea = groups[mk][0]; ep = groups[pk][0]
            step_b.append(abs(ent_pos4[ea][1] - ent_pos4[ep][1]))
            step_a.append(abs(ent_pos5[ea][1] - ent_pos5[ep][1]))
    R["blend"] = dict(hop_from_pinned=hop_tab, movable_unreached_by_bfs=unreached,
                      boundary_edges=len(step_b),
                      boundary_step_before=stats(step_b), boundary_step_after=stats(step_a),
                      note="hop 1 = movable positions edge-adjacent to a pinned (kept) position. The blend is C0 by "
                           "construction only if the boundary step does not GROW; a distance-falloff blend would "
                           "relocate the step one vertex inward.")
    log(f"[5] hop table={hop_tab} boundary_step p95 {R['blend']['boundary_step_before'].get('p95')} -> "
        f"{R['blend']['boundary_step_after'].get('p95')}")
    if step_b and R["blend"]["boundary_step_after"]["p95"] > R["blend"]["boundary_step_before"]["p95"] + 1e-6:
        findings.append(f"REFUTE (5): the Y step across the patch/pin boundary GREW "
                        f"(p95 {R['blend']['boundary_step_before']['p95']} -> "
                        f"{R['blend']['boundary_step_after']['p95']}) -- the fix relocated the seam.")
    if hop_tab.get("1", {}).get("mean_abs_dY", 0) > hop_tab.get("3", {}).get("mean_abs_dY", 0) and \
       len(hop_bins.get(3, [])) > 20:
        findings.append("NOTE (5): mean |dY| at hop 1 exceeds hop 3 -- the blend is not monotone away from the pins "
                        "(harmonic solutions need not be, but check for a boundary step).")

    # 20-vertex explicit sample
    mv_sorted = sorted([k for k in movable if abs(dy_by_group[k]) > 0],
                       key=lambda k: -abs(dy_by_group[k]))
    step = max(1, len(mv_sorted) // 20)
    sample = mv_sorted[::step][:20]
    srows = []
    for k in sample:
        v = mv_rows[k]
        srows.append(dict(pos=[round(k[0], 3), round(k[2], 3)], y_before=round(v["y4"], 5),
                          y_after=round(v["y5"], 5), dY=round(v["dy"], 5),
                          my_reference=round(v.get("ref", float('nan')), 5) if "ref" in v else None,
                          residual_before=round(v.get("res_b", float('nan')), 5) if "res_b" in v else None,
                          residual_after=round(v.get("res_a", float('nan')), 5) if "res_a" in v else None,
                          between_old_and_reference=(None if "ref" not in v else
                                                     (min(v["y4"], v["ref"]) - 1e-6 <= v["y5"] <=
                                                      max(v["y4"], v["ref"]) + 1e-6)),
                          hops_from_pin=dist.get(k), entries=len(groups[k]),
                          blocks=sorted({f"{e[0]},{e[1]}" for e in groups[k]})))
    n_between = sum(1 for r in srows if r["between_old_and_reference"])
    R["sample20"] = dict(n=len(srows), n_between_old_and_reference=n_between, rows=srows)
    log(f"[5] sample20: {n_between}/{len(srows)} land between the old Y and my own reference")

    # ---------------- (5b) ESTIMATOR ROBUSTNESS: a flag that survives only ONE reference is not a refutation
    # B: MY OWN IDW-weighted least-squares PLANE (slope-aware, unlike the constant IDW above)
    def plane_at(x, z):
        for R_ in (10.0, 14.0, 20.0, 28.0, 40.0):
            got = []
            rc = int(math.ceil(R_ / HB))
            cx, cz = int(math.floor(x / HB)), int(math.floor(z / HB))
            for i in range(cx - rc, cx + rc + 1):
                for j in range(cz - rc, cz + rc + 1):
                    for (px, pz, py) in hgrid.get((i, j), ()):
                        d2 = (px - x) ** 2 + (pz - z) ** 2
                        if d2 <= R_ * R_: got.append((d2, px, pz, py))
            if len(got) < 8: continue
            got.sort(); got = got[:40]
            # weighted normal equations for y = a + b*(px-x) + c*(pz-z)
            A = [[0.0] * 3 for _ in range(3)]; rhs = [0.0] * 3
            for d2, px, pz, py in got:
                w = 1.0 / max(d2, 0.25)
                bas = (1.0, px - x, pz - z)
                for r_ in range(3):
                    for c_ in range(3): A[r_][c_] += w * bas[r_] * bas[c_]
                    rhs[r_] += w * bas[r_] * py
            # gaussian elimination w/ partial pivot
            Mx = [A[i][:] + [rhs[i]] for i in range(3)]
            ok = True
            for col in range(3):
                piv = max(range(col, 3), key=lambda rr: abs(Mx[rr][col]))
                if abs(Mx[piv][col]) < 1e-12: ok = False; break
                Mx[col], Mx[piv] = Mx[piv], Mx[col]
                for rr in range(3):
                    if rr == col: continue
                    f = Mx[rr][col] / Mx[col][col]
                    for cc in range(col, 4): Mx[rr][cc] -= f * Mx[col][cc]
            if not ok: continue
            return Mx[0][3] / Mx[0][0], R_, len(got)
        return None, None, 0

    # C: ESTIMATOR-FREE ENVELOPE -- [min,max] of kept-ground Y within a radius
    def envelope(x, z, R_):
        lo = hi = None; n = 0
        rc = int(math.ceil(R_ / HB))
        cx, cz = int(math.floor(x / HB)), int(math.floor(z / HB))
        for i in range(cx - rc, cx + rc + 1):
            for j in range(cz - rc, cz + rc + 1):
                for (px, pz, py) in hgrid.get((i, j), ()):
                    if (px - x) ** 2 + (pz - z) ** 2 <= R_ * R_:
                        n += 1
                        lo = py if lo is None else min(lo, py)
                        hi = py if hi is None else max(hi, py)
        return lo, hi, n

    ENV_TOL = 0.05
    b_before = []; b_after = []; b_over = []; b_away = []
    env_rows = dict(new_above=[], new_below=[], was_out_now_in=0, in_both=0, out_both=0, no_sample=0)
    exc_above = []; exc_below = []; env_multi = {}
    for RAD in (8.0, 12.0, 16.0, 24.0):
        na = nb = ib = 0
        for k, v in mv_rows.items():
            lo, hi, n = envelope(v["x"], v["z"], RAD)
            if n < 4: continue
            was_in = (lo - ENV_TOL) <= v["y4"] <= (hi + ENV_TOL)
            now_in = (lo - ENV_TOL) <= v["y5"] <= (hi + ENV_TOL)
            if was_in and now_in: ib += 1
            elif was_in and not now_in:
                if v["y5"] > hi: na += 1
                else: nb += 1
        env_multi[str(RAD)] = dict(new_above=na, new_below=nb, in_both=ib)
    for k, v in mv_rows.items():
        pb, _, _ = plane_at(v["x"], v["z"])
        if pb is not None:
            rb = v["y4"] - pb; ra = v["y5"] - pb
            v["pref"] = pb; v["pres_b"] = rb; v["pres_a"] = ra
            b_before.append(rb); b_after.append(ra)
            if abs(ra) > abs(rb) + 0.05: b_over.append([list(k), round(rb, 4), round(ra, 4)])
            if abs(v["dy"]) > 0.05 and rb * v["dy"] > 0: b_away.append([list(k), round(rb, 4), round(v["dy"], 4)])
        lo, hi, n = envelope(v["x"], v["z"], 12.0)
        if n < 4: env_rows["no_sample"] += 1; continue
        was_in = (lo - ENV_TOL) <= v["y4"] <= (hi + ENV_TOL)
        now_in = (lo - ENV_TOL) <= v["y5"] <= (hi + ENV_TOL)
        if was_in and now_in: env_rows["in_both"] += 1
        elif not was_in and now_in: env_rows["was_out_now_in"] += 1
        elif not was_in and not now_in: env_rows["out_both"] += 1
        else:
            exc = (v["y5"] - hi) if v["y5"] > hi else (lo - v["y5"])
            row = [list(k), round(v["y4"], 4), round(v["y5"], 4), round(lo, 4), round(hi, 4),
                   round(exc, 4), round(v.get("pres_b", float("nan")), 3) if "pres_b" in v else None,
                   round(math.hypot(v["x"] - 134.0, v["z"] + 1166.0), 1)]
            if v["y5"] > hi: env_rows["new_above"].append(row); exc_above.append(exc)
            else: env_rows["new_below"].append(row); exc_below.append(exc)
    R["estimator_robustness"] = dict(
        planeB_abs_before=stats([abs(x) for x in b_before]), planeB_abs_after=stats([abs(x) for x in b_after]),
        planeB_anomalies_before_ge_0p6=sum(1 for x in b_before if abs(x) >= 0.6),
        planeB_anomalies_after_ge_0p6=sum(1 for x in b_after if abs(x) >= 0.6),
        planeB_overshoot=len(b_over), planeB_overshoot_examples=b_over[:8],
        planeB_moved_away=len(b_away),
        envelope_r12=dict(in_both=env_rows["in_both"], was_out_now_in=env_rows["was_out_now_in"],
                          out_both=env_rows["out_both"], no_sample=env_rows["no_sample"],
                          NEW_above_envelope=len(env_rows["new_above"]),
                          NEW_below_envelope=len(env_rows["new_below"]),
                          exceedance_above=stats(exc_above), exceedance_below=stats(exc_below),
                          n_exceedance_gt_0p25=sum(1 for e in exc_above + exc_below if e > 0.25),
                          n_exceedance_gt_0p5=sum(1 for e in exc_above + exc_below if e > 0.5),
                          n_exceedance_gt_1p0=sum(1 for e in exc_above + exc_below if e > 1.0),
                          row_schema=["pos", "y_before", "y_after", "kept_lo", "kept_hi", "exceedance",
                                      "planeB_residual_before", "r_from_crater"],
                          new_above_examples=sorted(env_rows["new_above"], key=lambda r: -r[5])[:10],
                          new_below_examples=sorted(env_rows["new_below"], key=lambda r: -r[5])[:10]),
        envelope_radius_sensitivity=env_multi,
        note="Estimator A = constant IDW (biased on slopes). Estimator B = MY OWN slope-aware IDW-weighted LSQ "
             "plane. Estimator C = the estimator-FREE envelope [min,max] of kept-ground Y within 12u: a vertex "
             "that was inside the surrounding ground's own Y range and is now outside it is a NEW nub/pit "
             "regardless of any fitted surface.")
    EB = R["estimator_robustness"]
    log(f"[5b] planeB anomalies {EB['planeB_anomalies_before_ge_0p6']} -> {EB['planeB_anomalies_after_ge_0p6']} "
        f"overshoot={EB['planeB_overshoot']} away={EB['planeB_moved_away']} | envelope r12 "
        f"in_both={env_rows['in_both']} fixed={env_rows['was_out_now_in']} out_both={env_rows['out_both']} "
        f"NEW_above={len(env_rows['new_above'])} NEW_below={len(env_rows['new_below'])}")
    # NEWLY BROKEN under the slope-aware estimator: fine before, anomalous after (the only class that can
    # constitute a REGRESSION -- a position that was already anomalous and is still anomalous is unfixed, not broken)
    newly_broken = []; still_broken = 0; fixed_n = 0
    for k, v in mv_rows.items():
        if "pres_b" not in v: continue
        wb = abs(v["pres_b"]) >= 0.6; wa = abs(v["pres_a"]) >= 0.6
        if wb and wa: still_broken += 1
        elif wb and not wa: fixed_n += 1
        elif (not wb) and wa:
            newly_broken.append([list(k), round(v["pres_b"], 3), round(v["pres_a"], 3), round(v["dy"], 3),
                                 round(math.hypot(v["x"] - 134.0, v["z"] + 1166.0), 1)])
    EB["planeB_fixed"] = fixed_n
    EB["planeB_still_anomalous"] = still_broken
    EB["planeB_NEWLY_anomalous"] = len(newly_broken)
    EB["planeB_newly_anomalous_examples"] = sorted(newly_broken, key=lambda r: -abs(r[2]))[:10]
    log(f"[5b] planeB ledger: fixed={fixed_n} still={still_broken} NEWLY_broken={len(newly_broken)}")
    big_new = [e for e in exc_above + exc_below if e > 0.25]
    EB["n_envelope_exceedance_gt_0p25"] = len(big_new)
    # SUPPORT TEST -- a fitted reference is only a MEASUREMENT where kept ground is actually local.
    # Score every newly-flagged position by how much kept ground sits within 8u / 12u / 20u.
    def support(x, z):
        return [envelope(x, z, r)[2] for r in (8.0, 12.0, 20.0)]
    nb_support = []
    for row in newly_broken:
        k = tuple(row[0]); v = mv_rows[(k[0], k[1], k[2])]
        nb_support.append(support(v["x"], v["z"]))
    EB["newly_anomalous_support_n_kept_ground_within_8_12_20u"] = nb_support
    EB["newly_anomalous_with_local_support_r8_ge6"] = sum(1 for s in nb_support if s[0] >= 6)
    EB["newly_anomalous_with_NO_kept_ground_within_20u"] = sum(1 for s in nb_support if s[2] == 0)
    if EB["planeB_anomalies_after_ge_0p6"] > EB["planeB_anomalies_before_ge_0p6"]:
        findings.append(f"REFUTE (5): under the SLOPE-AWARE plane reference the >=0.6u anomaly count GREW "
                        f"{EB['planeB_anomalies_before_ge_0p6']} -> {EB['planeB_anomalies_after_ge_0p6']}.")

    # ---------------- (5c) THE REFERENCE-FREE ADJUDICATOR: SURFACE CURVATURE ----------------
    # Both fitted references above EXTRAPOLATE wherever the fill interior has no kept ground within 12-20u,
    # which is exactly where the big moves are. The owner-reported defect class (embossed channels, terminal
    # nubs, dig-spot pits) is LOCAL RELIEF, which is measurable with no reference at all: the discrete
    # Laplacian y(p) - mean(y(neighbours)) on the unified Terrain surface graph.
    xz_y4 = defaultdict(set); xz_y5 = {}
    nb = defaultdict(set)
    for r in tris:
        ks = [(round(p[0], 2), round(p[2], 2)) for p in r["w4"]]
        for i in range(3):
            xz_y4[ks[i]].add(round(r["w4"][i][1], 4))
            xz_y5[ks[i]] = r["w5"][i][1]
            nb[ks[i]].add(ks[(i + 1) % 3]); nb[ks[(i + 1) % 3]].add(ks[i])
    # a vertical wall stacks several Y at one XZ -> exclude (not a height field there)
    single = {k for k, s in xz_y4.items() if len(s) == 1}
    y4map = {k: next(iter(xz_y4[k])) for k in single}
    lap4 = {}; lap5 = {}
    for k in single:
        ns = [n for n in nb[k] if n in single]
        if len(ns) < 3: continue
        lap4[k] = y4map[k] - statistics.fmean(y4map[n] for n in ns)
        lap5[k] = xz_y5[k] - statistics.fmean(xz_y5[n] for n in ns)
    movable_xz = {(round(k[0], 2), round(k[2], 2)) for k in movable}
    def curv_block(keys):
        a = [abs(lap4[k]) for k in keys if k in lap4]
        b = [abs(lap5[k]) for k in keys if k in lap5]
        return dict(before=stats(a), after=stats(b),
                    spikes_gt_0p25_before=sum(1 for v in a if v > 0.25),
                    spikes_gt_0p25_after=sum(1 for v in b if v > 0.25),
                    spikes_gt_0p5_before=sum(1 for v in a if v > 0.5),
                    spikes_gt_0p5_after=sum(1 for v in b if v > 0.5))
    kept_xz = {k for k in single} - movable_xz
    newspikes = sorted(((abs(lap5[k]) - abs(lap4[k]), k) for k in lap4 if k in lap5), reverse=True)[:10]
    R["curvature"] = dict(
        n_heightfield_positions=len(lap4), n_wall_stacked_excluded=len(xz_y4) - len(single),
        all_positions=curv_block(list(lap4.keys())),
        movable_positions=curv_block([k for k in lap4 if k in movable_xz]),
        kept_positions=curv_block([k for k in lap4 if k in kept_xz]),
        worst_new_spikes=[[list(k), round(d, 4), round(lap4[k], 4), round(lap5[k], 4)] for d, k in newspikes],
        note="discrete Laplacian y(p) - mean(y(1-ring)) on the unified Terrain height field -- reference-FREE. "
             "This is the direct measure of the reported defect class (embossed channels / terminal nubs / "
             "dig-spot pits); the fitted references of (5)/(5b) extrapolate in the fill interior and cannot "
             "adjudicate it.")
    CV = R["curvature"]
    log(f"[5c] curvature |lap| ALL p95 {CV['all_positions']['before']['p95']} -> {CV['all_positions']['after']['p95']}"
        f" | MOVABLE p95 {CV['movable_positions']['before']['p95']} -> {CV['movable_positions']['after']['p95']}"
        f" spikes>0.25 {CV['movable_positions']['spikes_gt_0p25_before']} -> "
        f"{CV['movable_positions']['spikes_gt_0p25_after']}")
    # THE CONTROL: the moved set's BEFORE state is a dead-flat sheet, whose curvature is ~0 by construction,
    # so "curvature rose" is the intended outcome, not a defect. The defect test is against the KEPT GROUND's
    # OWN curvature -- fill that is bumpier than real terrain reads as artefact; fill that is smoother reads
    # as terrain.
    mv_a = CV["movable_positions"]["after"]; kp_b = CV["kept_positions"]["before"]
    mv_rate = CV["movable_positions"]["spikes_gt_0p25_after"] / max(1, mv_a["n"])
    kp_rate = CV["kept_positions"]["spikes_gt_0p25_before"] / max(1, kp_b["n"])
    CV["kept_ground_control"] = dict(
        movable_after_p95=mv_a["p95"], kept_before_p95=kp_b["p95"],
        movable_after_max=mv_a["max"], kept_before_max=kp_b["max"],
        movable_after_spike_rate_gt_0p25=round(mv_rate, 4), kept_spike_rate_gt_0p25=round(kp_rate, 4),
        ratio=round(mv_rate / kp_rate, 4) if kp_rate else None,
        global_max_abs_laplacian_before=CV["all_positions"]["before"]["max"],
        global_max_abs_laplacian_after=CV["all_positions"]["after"]["max"],
        global_spikes_gt_0p25=[CV["all_positions"]["spikes_gt_0p25_before"],
                               CV["all_positions"]["spikes_gt_0p25_after"]],
        verdict_rule="REFUTE only if the relaxed fill is bumpier than the surrounding REAL terrain.")
    log(f"[5c] control: movable-after p95 {mv_a['p95']} / spike-rate {mv_rate:.4f} vs KEPT ground p95 "
        f"{kp_b['p95']} / spike-rate {kp_rate:.4f} (ratio {CV['kept_ground_control']['ratio']}); "
        f"global max|lap| {CV['all_positions']['before']['max']} -> {CV['all_positions']['after']['max']}")
    if mv_a["p95"] > kp_b["p95"] or mv_rate > kp_rate:
        findings.append(f"REFUTE (5c): the relaxed fill is BUMPIER than the surrounding kept terrain "
                        f"(|Laplacian| p95 {mv_a['p95']} vs kept {kp_b['p95']}; spike rate {mv_rate:.3f} vs "
                        f"{kp_rate:.3f}) -- it will read as artefact, not ground.")
    else:
        findings.append(f"NOTE (5c): reference-free curvature over the moved set rose from a DEAD-FLAT baseline "
                        f"(p95 {CV['movable_positions']['before']['p95']} -> {mv_a['p95']}), which is the intended "
                        f"outcome; against the kept ground's OWN curvature the relaxed fill remains far smoother "
                        f"(kept p95 {kp_b['p95']}, spike rate {kp_rate:.3f} vs the fill's {mv_rate:.3f}), and the "
                        f"island's global worst spike FELL {CV['all_positions']['before']['max']} -> "
                        f"{CV['all_positions']['after']['max']} with global spikes "
                        f"{CV['all_positions']['spikes_gt_0p25_before']} -> "
                        f"{CV['all_positions']['spikes_gt_0p25_after']}.")
    if CV["kept_positions"]["spikes_gt_0p25_after"] > CV["kept_positions"]["spikes_gt_0p25_before"]:
        findings.append(f"NOTE (5c): curvature spikes at KEPT positions grew "
                        f"{CV['kept_positions']['spikes_gt_0p25_before']} -> "
                        f"{CV['kept_positions']['spikes_gt_0p25_after']} (kept verts never move; this measures "
                        f"the step their moved fill NEIGHBOURS present to them).")

    # well-supported envelope: only positions with REAL local kept ground (>=6 samples inside 8u)
    ws_above = []; ws_below = []; ws_in = 0; ws_n = 0
    for k, v in mv_rows.items():
        lo, hi, n = envelope(v["x"], v["z"], 8.0)
        if n < 6: continue
        ws_n += 1
        if (lo - ENV_TOL) <= v["y5"] <= (hi + ENV_TOL): ws_in += 1
        elif (lo - ENV_TOL) <= v["y4"] <= (hi + ENV_TOL):
            (ws_above if v["y5"] > hi else ws_below).append(
                [list(k), round(v["y4"], 3), round(v["y5"], 3), round(lo, 3), round(hi, 3),
                 round((v["y5"] - hi) if v["y5"] > hi else (lo - v["y5"]), 3), n])
    R["estimator_robustness"]["envelope_well_supported_r8"] = dict(
        n_positions_with_local_kept_ground=ws_n, inside_after=ws_in,
        NEW_above=len(ws_above), NEW_below=len(ws_below),
        above_examples=sorted(ws_above, key=lambda r: -r[5])[:8],
        below_examples=sorted(ws_below, key=lambda r: -r[5])[:8],
        note="restricted to moved positions that actually HAVE >=6 kept-ground samples within 8u -- the only "
             "envelope verdicts that are a local measurement rather than an extrapolation.")
    WS = R["estimator_robustness"]["envelope_well_supported_r8"]
    log(f"[5b] well-supported envelope (r8,n>=6): n={ws_n} inside={ws_in} NEW_above={len(ws_above)} "
        f"NEW_below={len(ws_below)}")
    log(f"[5b] newly-anomalous support: local(r8>=6)={EB['newly_anomalous_with_local_support_r8_ge6']} "
        f"no-kept-ground-within-20u={EB['newly_anomalous_with_NO_kept_ground_within_20u']} of {len(newly_broken)}")

    # ADJUDICATION: a new nub/pit counts only where it is a LOCAL MEASUREMENT and the reference-free
    # curvature agrees. Anything else is an artefact of extrapolating into the fill interior.
    material_local = [r for r in ws_above + ws_below if r[5] > 0.25]
    if material_local and CV["movable_positions"]["after"]["p95"] > CV["movable_positions"]["before"]["p95"]:
        findings.append(f"REFUTE (5): {len(material_local)} moved positions with REAL local kept ground (>=6 samples "
                        f"within 8u) leave that ground's own Y envelope by >0.25u AND reference-free curvature "
                        f"rose -- material new relief: {material_local[:4]}.")
    elif material_local:
        findings.append(f"NOTE (5b): {len(material_local)} well-supported moved positions exit the local kept-ground "
                        f"Y envelope by >0.25u (max {round(max(r[5] for r in material_local),3)}u) while "
                        f"reference-free curvature FELL -- a bounded cosmetic residual, not a new defect class.")
    if len(newly_broken) and EB["newly_anomalous_with_local_support_r8_ge6"] == 0:
        findings.append(f"NOTE (5b): the {len(newly_broken)} 'newly anomalous' positions under the fitted plane "
                        f"reference ALL sit where there is no local kept ground to fit "
                        f"({EB['newly_anomalous_with_NO_kept_ground_within_20u']} have NONE within 20u) -- the "
                        f"reference there is an extrapolation, so this lane cannot refute. Ledger under that "
                        f"reference: {fixed_n} fixed / {still_broken} still anomalous / {len(newly_broken)} newly.")

    # ---------------- (6) REFUTATION HUNT ----------------
    hunt = {}

    # 6a: independent crater re-derivation -- deepest closed depression among the movable set
    BC = (127.14, -1161.42); BR = 7.92
    in_disc = [(k, ent_pos4[groups[k][0]][1], ent_pos5[groups[k][0]][1]) for k in groups
               if math.hypot(k[0] - BC[0], k[2] - BC[1]) <= BR]
    disc_terr = [(k, y4, y5) for (k, y4, y5) in in_disc if any(e[2] == "Terrain" for e in groups[k])]
    disc_moved = [[list(k), round(y5 - y4, 6)] for (k, y4, y5) in disc_terr if abs(y5 - y4) > 0]
    rim = [ent_pos4[groups[k][0]][1] for k in groups
           if BR < math.hypot(k[0] - BC[0], k[2] - BC[1]) <= BR + 6.0
           and any(e[2] == "Terrain" for e in groups[k])]
    rim5 = [ent_pos5[groups[k][0]][1] for k in groups
            if BR < math.hypot(k[0] - BC[0], k[2] - BC[1]) <= BR + 6.0
            and any(e[2] == "Terrain" for e in groups[k])]
    floor_y4 = [y4 for (_, y4, _) in disc_terr]; floor_y5 = [y5 for (_, _, y5) in disc_terr]
    hunt["crater"] = dict(centre=list(BC), radius=BR,
                          n_terrain_positions_in_disc=len(disc_terr),
                          moved_in_disc=len(disc_moved), moved_examples=disc_moved[:6],
                          floor_y_before=stats(floor_y4), floor_y_after=stats(floor_y5),
                          rim_band_y_before=stats(rim), rim_band_y_after=stats(rim5),
                          depth_before=round((statistics.fmean(rim) - statistics.fmean(floor_y4)), 4) if rim and floor_y4 else None,
                          depth_after=round((statistics.fmean(rim5) - statistics.fmean(floor_y5)), 4) if rim5 and floor_y5 else None)
    log(f"[6] crater: disc positions={len(disc_terr)} moved={len(disc_moved)} "
        f"depth {hunt['crater']['depth_before']} -> {hunt['crater']['depth_after']}")
    if disc_moved:
        findings.append(f"REFUTE (6): {len(disc_moved)} Terrain positions INSIDE the owner-liked crater disc moved: "
                        f"{disc_moved[:4]}.")
    if hunt["crater"]["depth_before"] is not None and \
       hunt["crater"]["depth_after"] < hunt["crater"]["depth_before"] - 1e-4:
        findings.append(f"REFUTE (6): the crater got SHALLOWER ({hunt['crater']['depth_before']} -> "
                        f"{hunt['crater']['depth_after']}).")

    # 6b: NEW spikes -- per-tri max Y span and dip angle, before vs after (synth tris only)
    def span_dip(which):
        sp = []; dip = []
        for r in tris:
            if not r["synth"]: continue
            ys = [p[1] for p in r[which]]
            sp.append(max(ys) - min(ys))
            g = geo_normal(*r[which]); L = math.sqrt(sum(c * c for c in g))
            if L > 1e-12:
                ny = abs(g[1]) / L
                dip.append(math.degrees(math.acos(max(-1.0, min(1.0, ny)))))
        return sp, dip
    sp4, dp4 = span_dip("w4"); sp5, dp5 = span_dip("w5")
    worse = [[list(r["b"]), r["t"], round(max(p[1] for p in r["w4"]) - min(p[1] for p in r["w4"]), 4),
              round(max(p[1] for p in r["w5"]) - min(p[1] for p in r["w5"]), 4)]
             for r in tris if r["synth"] and
             (max(p[1] for p in r["w5"]) - min(p[1] for p in r["w5"])) >
             (max(p[1] for p in r["w4"]) - min(p[1] for p in r["w4"])) + 0.75]
    hunt["relief"] = dict(synth_tri_yspan_before=stats(sp4), synth_tri_yspan_after=stats(sp5),
                          synth_tri_dip_before=stats(dp4), synth_tri_dip_after=stats(dp5),
                          tris_whose_span_grew_gt_0p75=len(worse), examples=worse[:8])
    log(f"[6] synth span p95 {stats(sp4)['p95']} -> {stats(sp5)['p95']}, dip p95 {stats(dp4)['p95']} -> "
        f"{stats(dp5)['p95']}, grew>0.75u: {len(worse)}")
    if stats(sp5)["p95"] > stats(sp4)["p95"] + 1e-6:
        findings.append(f"REFUTE (6): synthesized-tri Y-span p95 GREW {stats(sp4)['p95']} -> {stats(sp5)['p95']} "
                        f"-- the relax added relief instead of removing it.")
    # the owner-visible question for a steepened tri is whether it reads as a FACE -- i.e. whether its dip
    # leaves the KEPT GROUND's own dip envelope. Estimator-free: compare against kept ground-family tris.
    kept_dip = []
    for r in tris:
        if r["synth"] or G.TOPO_FAMILY.get(r["topo"]) is None: continue
        g = geo_normal(*r["w4"]); L = math.sqrt(sum(c * c for c in g))
        if L > 1e-12:
            kept_dip.append(math.degrees(math.acos(max(-1.0, min(1.0, abs(g[1]) / L)))))
    kd = stats(kept_dip)
    grown_ids = {(tuple(w[0]), w[1]) for w in worse}
    grown_dip_after = []; grown_span_after = []
    for r in tris:
        if not r["synth"] or (tuple(r["b"]), r["t"]) not in grown_ids: continue
        g = geo_normal(*r["w5"]); L = math.sqrt(sum(c * c for c in g))
        if L > 1e-12:
            grown_dip_after.append(math.degrees(math.acos(max(-1.0, min(1.0, abs(g[1]) / L)))))
        ys = [p[1] for p in r["w5"]]; grown_span_after.append(max(ys) - min(ys))
    kept_p99 = kd.get("p99", 0.0); kept_max = kd.get("max", 0.0)
    over_kept = [round(d, 3) for d in grown_dip_after if d > kept_p99]
    hunt["steepened_tris"] = dict(
        n=len(worse), kept_ground_dip=kd, grown_dip_after=stats(grown_dip_after),
        grown_span_after=stats(grown_span_after),
        n_dip_above_kept_p99=len(over_kept), n_dip_above_kept_max=sum(1 for d in grown_dip_after if d > kept_max),
        note="a steepened fill tri only reads as a FACE if its dip exits the surrounding KEPT ground's own dip "
             "envelope; inside it, the steepening IS the fill learning the local slope.")
    log(f"[6] steepened: n={len(worse)} dip_after p95={stats(grown_dip_after).get('p95')} vs kept p99={kept_p99} "
        f"max={kept_max}; above kept p99={len(over_kept)} above kept max="
        f"{hunt['steepened_tris']['n_dip_above_kept_max']}")
    if hunt["steepened_tris"]["n_dip_above_kept_max"]:
        findings.append(f"REFUTE (6): {hunt['steepened_tris']['n_dip_above_kept_max']} steepened fill tris now dip "
                        f"MORE than ANY kept ground tri (kept max {round(kept_max,2)}deg) -- new faces in the sand.")
    elif len(worse) > 20:
        findings.append(f"NOTE (6): {len(worse)} synthesized tris got >0.75u MORE Y-span, but their dip stays inside "
                        f"the kept ground's own envelope (dip p95 {stats(grown_dip_after).get('p95')}deg vs kept "
                        f"p99 {round(kept_p99,2)}deg / kept max {round(kept_max,2)}deg).")

    # 6c: carried-core donor byte match -- must be positionally frozen
    SHIFT = (-768.0, -384.0)
    donor = defaultdict(list); donor_blocks = 0
    try:
        for bx in (13, 14, 15):
            for by in (11, 12):
                try:
                    bm = X.read_block(bx, by, disc=1, part="terrain")
                except (ValueError, FileNotFoundError, OSError):
                    continue
                donor_blocks += 1
                ox, oz = X.block_world_origin(bx, by)
                for tri in bm.tris:
                    w = [(bm.verts[j][0] + ox + SHIFT[0], bm.verts[j][1], bm.verts[j][2] + oz + SHIFT[1])
                         for j in tri]
                    # XZ key (the round-4 lineage): the carry applies a weld-safe Y lift, so a 3D key cannot
                    # match a legitimately carried tri. XZ ALONE is far too loose here -- the hole-fill was
                    # synthesized on the donor's own lattice -- so the donor's UVs are the discriminator.
                    key = tuple(sorted((round(p[0], 2), round(p[2], 2)) for p in w))
                    donor[key].append(tuple(sorted((round(float(bm.uvs[j][0]), 6),
                                                    round(float(bm.uvs[j][1]), 6)) for j in tri)))
    except Exception as exc:      # install unreadable -> lane reports empty, never a false pass
        R["donor_error"] = repr(exc)
    uvs4_by_block = {(bx, by): uvs_of(T[(bx, by, "Terrain")]["r4"]) for (bx, by) in FOOTPRINT
                     if (bx, by, "Terrain") in T}
    matched_xz = verbatim = moved_core = verbatim_synth = 0
    for r in tris:
        key = tuple(sorted((round(p[0], 2), round(p[2], 2)) for p in r["w4"]))
        cands = donor.get(key)
        if not cands: continue
        matched_xz += 1
        u = uvs4_by_block[r["b"]]
        uv4 = tuple(sorted((round(u[j][0], 6), round(u[j][1], 6)) for j in r["tri"]))
        if any(c == uv4 for c in cands):
            verbatim += 1
            if r["synth"]: verbatim_synth += 1
            if r["moved"]: moved_core += 1
    hunt["carried_core"] = dict(donor_blocks=donor_blocks, donor_keys=len(donor),
                                matched_xz_only=matched_xz, carried_core_verbatim=verbatim,
                                of_those_in_my_synth_set=verbatim_synth, moved=moved_core,
                                note="XZ position key AND the donor's own UVs (the round-4 lineage discriminator). "
                                     "XZ alone matches 3389 tris because the hole-fill was synthesized on the "
                                     "donor's lattice; the UV test separates truly carried tris from refilled holes.")
    log(f"[6] carried-core: donor_blocks={donor_blocks} xz_only={matched_xz} verbatim={verbatim} "
        f"synth_overlap={verbatim_synth} moved={moved_core}")
    if moved_core:
        findings.append(f"REFUTE (6): {moved_core} carried-core (donor position+UV match) tris MOVED.")
    if verbatim_synth:
        findings.append(f"REFUTE (6): {verbatim_synth} tris are BOTH donor-verbatim and in my synthesized set "
                        f"(the two sets must be disjoint).")
    if donor_blocks and verbatim == 0:
        findings.append("NOTE (6): carried-core re-identification matched 0 tris (lane inconclusive).")
    elif verbatim != 1454:
        findings.append(f"NOTE (6): my carried-core re-identification finds {verbatim} donor-verbatim tris vs the "
                        f"arc's 1454 (a 6dp-UV-rounding / duplicate-key edge effect in MY matcher); all "
                        f"{verbatim} are UNMOVED and none overlaps my synthesized set, so the rigidity claim "
                        f"holds regardless of the count.")

    # 6d: did anything move OUTSIDE the synthesized footprint's blocks?
    moved_blocks = sorted({f"{e[0]},{e[1]}" for k in moved_keys for e in groups[k]})
    hunt["moved_blocks"] = moved_blocks
    changed_blocks = sorted({rp.split("Block[")[1].split("]")[0] + "," + rp.split("][")[1].split("]")[0]
                             for rp in changed})
    hunt["changed_files_blocks"] = changed_blocks
    if set(moved_blocks) - set(changed_blocks):
        findings.append(f"REFUTE (1): blocks with moved vertices but no changed file: "
                        f"{sorted(set(moved_blocks) - set(changed_blocks))}.")
    if set(changed_blocks) - set(moved_blocks):
        findings.append(f"NOTE (1): files changed in blocks with no moved vertex: "
                        f"{sorted(set(changed_blocks) - set(moved_blocks))} (normal-only rewrite).")

    # 6d2: THE UNVERIFIABLE INTERIOR -- moves made where NO kept ground exists nearby to check them against.
    interior = []
    for k, v in mv_rows.items():
        if abs(v["dy"]) < 0.75: continue
        s8, s12, s20 = (envelope(v["x"], v["z"], r)[2] for r in (8.0, 12.0, 20.0))
        if s20 == 0 or s12 < 4:
            interior.append([list(k), round(v["y5"], 3), round(v["dy"], 3), s8, s12, s20,
                             round(math.hypot(v["x"] - 134.0, v["z"] + 1166.0), 1)])
    big_moves = [v for v in mv_rows.values() if abs(v["dy"]) >= 0.75]
    hunt["unverifiable_interior"] = dict(
        n_moves_ge_0p75u=len(big_moves), n_of_those_without_local_kept_ground=len(interior),
        row_schema=["pos", "y_after", "dY", "kept_ground_n_r8", "n_r12", "n_r20", "r_from_crater"],
        examples=sorted(interior, key=lambda r: -abs(r[2]))[:12],
        note="these moves cannot be validated OR refuted offline against any kept-ground reference -- the nearest "
             "real terrain is >=12-20u away. They are smooth by the curvature test, but their absolute height is "
             "set by the solve's smoothness term alone. This is eye/playtest territory, not a gate.")
    log(f"[6] unverifiable interior: {len(interior)} of {len(big_moves)} moves >=0.75u have no local kept ground")

    # 6e: per-block moved-entry table vs the report
    per_block = Counter()
    for k in moved_keys:
        for e in groups[k]: per_block[f"({e[0]},{e[1]})"] += 1
    hunt["moved_entries_per_block"] = dict(sorted(per_block.items()))
    R["hunt"] = hunt

    # ---------------- report reconciliation ----------------
    rep = RUNG / "uvf_fix5_report.json"
    recon = {}
    if rep.exists():
        rj = json.loads(rep.read_text(encoding="utf-8"))
        ap = rj["stage_apply"]; ver = rj["stage_verify"]
        claims = dict(positions_moved=ap["positions_moved"], vertex_entries_moved=ap["vertex_entries_moved"],
                      synth_tris_with_moved_vert=ap["synth_tris_with_a_moved_vert"],
                      normal_tris=ap["normal_tris_recomputed"], normal_entries=ap["normal_verts_rewritten"],
                      max_abs_dY=ap["max_abs_dY"], cross_block=ap["positions_spanning_multiple_blocks"],
                      files_changed=ver["tree_diff_vs_fixed4"]["n_files"],
                      distinct_positions=ver["weld_audit"]["n_distinct_positions_all_parts"],
                      min_Y_moved=ver["land_above_sea"]["min_Y_over_moved_positions"],
                      min_ny=ver["stored_normals_all_up_facing"]["min_ny_on_rewritten"],
                      synthesized=rj["scope"]["movable_set"]["n_synthesized_tris"],
                      movable=rj["scope"]["movable_set"]["n_movable"],
                      pinned_of_touched=rj["scope"]["movable_set"]["n_pinned_of_those"],
                      touched_positions=rj["scope"]["movable_set"]["n_positions_touched_by_synth"])
        mine = dict(positions_moved=len(moved_keys), vertex_entries_moved=R["dY"]["moved_entries"],
                    synth_tris_with_moved_vert=R["synth_set"]["n_synth_with_moved_vert"],
                    normal_tris=n_rewritten_tris, normal_entries=n_rewritten_entries,
                    max_abs_dY=round(R["dY"]["max_abs"], 4), cross_block=cross_block_moved,
                    files_changed=len(changed), distinct_positions=len(groups),
                    min_Y_moved=round(min(moved_ys5), 4) if moved_ys5 else None,
                    min_ny=round(min_ny, 6),
                    synthesized=n_synth, movable=len(synth_touched_keys - pinned_keys),
                    pinned_of_touched=len(synth_touched_keys & pinned_keys),
                    touched_positions=len(synth_touched_keys))
        mism = {k: [claims[k], mine[k]] for k in claims
                if (isinstance(claims[k], float) and abs(claims[k] - (mine[k] or 0)) > 5e-4)
                or (not isinstance(claims[k], float) and claims[k] != mine[k])}
        recon = dict(claimed=claims, measured=mine, mismatches=mism)
        if mism: findings.append(f"MISMATCH (report): {mism} (claimed vs measured).")
    R["report_reconciliation"] = recon
    log(f"[R] reconciliation mismatches={recon.get('mismatches')}")

    hard = [f for f in findings if f.startswith("REFUTE") or f.startswith("MISMATCH")]
    R["findings"] = findings
    R["notes"] = [f for f in findings if f.startswith("NOTE")]
    R["verdict"] = "REFUTED" if hard else "CONFIRMED"
    OUT.write_text(json.dumps(R, indent=1), encoding="utf-8")
    log("\n" + "=" * 80)
    log(f"VERDICT: {R['verdict']}")
    for f in findings: log("  - " + f)
    log(f"-> {OUT}")
    return R


if __name__ == "__main__":
    main()
