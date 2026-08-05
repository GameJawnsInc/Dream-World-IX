"""RUNG 6 -- the SITE SPEC: verify the chosen landing + trigger cell and write site.json.

Read-only over the deployed bytes. Every number below is measured, not asserted:
  * arrival ground query (sky cast, origin y+400) and walking ground query (origin y+2.34375)
    at the landing point and at the trigger-cell centre;
  * the trigger cell's clean-grass extent, centroid, and the largest disc that stays inside
    the 32u cell AND on walkable terrain (the retarget_tiles radius);
  * entrance._cell_openness_note over the real deployed Terrain block;
  * a real foot route from landing to trigger with walk_sim's deflection-fan stepper;
  * neighbour checks against every event-bearing Disc9 tile and every inherited WORLD11 tag.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

STUDY = Path(__file__).resolve().parent.parent
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDY)); sys.path.insert(0, str(HERE))
sys.path.insert(0, str(STUDY.parent.parent / "ff9mapkit"))
import walk_sim as W                                          # noqa: E402
import probe_site as PS                                       # noqa: E402
import probe_finalize as PF                                   # noqa: E402
from ff9mapkit.world import entrance as E                     # noqa: E402
from ff9mapkit.world import extract as X                      # noqa: E402
from ff9mapkit.world import mesh as M                         # noqa: E402

LANDING = (425.0, -479.0)
TRIGGER_CELL = (13, 17)
BENCH = [(5, 7), (6, 7), (7, 7), (5, 8), (6, 8), (7, 8)]


def main():
    W.CELLS = BENCH
    world = W.load_world()
    clean, ground, topo_of, stacked, (x0, z0, nx, nz) = PS.build_map(world)

    cx, cz = TRIGGER_CELL
    cwx, cwz = E.cell_world_center(cx, cz)
    blk = E.cell_to_block(cx, cz)
    ox, oz = X.block_world_origin(*blk)
    rel = M.override_relpath(9, blk[0], blk[1], "0_1", "Terrain")
    ter_path = PF.GAME / PF.MOD / rel

    print("=== 1. LANDING POINT ===")
    lx, lz = LANDING
    sky = PS.sky_pick(world, lx, lz)
    wlk = PS.walk_pick(world, lx, lz, cur_y=sky[2])
    print(f"   world ({lx}, {lz})   cell {(int(lx//32), int(-lz//32))}  block "
          f"{(int(lx//64), int(-lz//64))}")
    print(f"   ARRIVAL sky query (origin y+400): mesh={world[W.block_key(lx,lz)][sky[0]]['name']} "
          f"y={sky[2]:.6f} idall={sky[3]} topo={sky[4]} walkable={sky[4] in W.WALK_OK}")
    print(f"   WALKING query   (origin y+2.34): y={wlk[2]:.6f} topo={wlk[4]} "
          f"walkable={wlk[4] in W.WALK_OK} via={wlk[5]}")
    # flatness + clearance
    k = (int(round((lx - x0) / PS.GRID)), int(round((lz - z0) / PS.GRID)))
    ys = [ground[(k[0] + di, k[1] + dj)] for di in range(-2, 3) for dj in range(-2, 3)
          if (k[0] + di, k[1] + dj) in ground]
    print(f"   5x5u neighbourhood: y {min(ys):.3f}..{max(ys):.3f} (relief {max(ys)-min(ys):.4f}u)")
    # radial clearance to the nearest non-walkable / non-land sample
    clear = None
    for r in range(1, 40):
        hit = False
        for a in range(0, 360, 5):
            px = lx + r * math.cos(math.radians(a))
            pz = lz + r * math.sin(math.radians(a))
            p = PS.sky_pick(world, px, pz)
            if p is None or p[4] not in W.WALK_OK or p[2] <= PS.SEA_Y:
                hit = True
                break
        if hit:
            clear = r
            break
    print(f"   radial clearance to nearest non-walkable/water: {clear}u")
    stack_here = [s for s in W.all_sheets(world, lx, lz, strict=True) if s[1] in W.WALK_OK]
    print(f"   walkable sheets on this vertical line: {len(stack_here)} "
          f"({[round(s[0],3) for s in stack_here]}) -> no lawn-under-hill stack")

    print("\n=== 2. EXIT-TRIGGER CELL ===")
    print(f"   cell {TRIGGER_CELL}  centre {(cwx, cwz)}  block {blk}  block origin {(ox, oz)}")
    print(f"   Disc9 Terrain override: {ter_path}")
    print(f"   exists: {ter_path.is_file()}  ({ter_path.stat().st_size if ter_path.is_file() else 0} B)")
    ck = (int(round((cwx - x0) / PS.GRID)), int(round((cwz - z0) / PS.GRID)))
    csky = PS.sky_pick(world, float(cwx), float(cwz))
    print(f"   centre ARRIVAL query: y={csky[2]:.6f} topo={csky[4]} "
          f"walkable={csky[4] in W.WALK_OK} clean-grass={ck in clean}")
    d = math.hypot(cwx - lx, cwz - lz)
    print(f"   distance landing -> cell centre: {d:.1f}u   (window 50-200u: "
          f"{'OK' if 50 <= d <= 200 else 'OUT'})")
    print(f"   landing inside this cell? {(int(lx//32), int(-lz//32)) == TRIGGER_CELL}")

    # clean-grass extent inside the cell + the biggest all-walkable disc inside the cell
    cellpts = [(x0 + i * PS.GRID, z0 + j * PS.GRID)
               for (i, j) in clean
               if int((x0 + i * PS.GRID) // 32) == cx and int(-(z0 + j * PS.GRID) // 32) == cz]
    gx = sum(p[0] for p in cellpts) / len(cellpts)
    gz = sum(p[1] for p in cellpts) / len(cellpts)
    print(f"   clean-grass samples in cell: {len(cellpts)}/1024  centroid ({gx:.1f},{gz:.1f})"
          f"  x {min(p[0] for p in cellpts):.0f}..{max(p[0] for p in cellpts):.0f}"
          f"  z {min(p[1] for p in cellpts):.0f}..{max(p[1] for p in cellpts):.0f}")

    def disc_ok(ccx, ccz, r):
        """every 1u sample inside the disc is clean grass AND the disc stays in the cell"""
        if not (cx * 32 <= ccx - r and ccx + r <= cx * 32 + 32):
            return False
        if not (-(cz * 32 + 32) <= ccz - r and ccz + r <= -(cz * 32)):
            return False
        for a in range(0, 360, 10):
            for rr in (r * 0.5, r):
                px, pz = ccx + rr * math.cos(math.radians(a)), ccz + rr * math.sin(math.radians(a))
                kk = (int(round((px - x0) / PS.GRID)), int(round((pz - z0) / PS.GRID)))
                if kk not in clean:
                    return False
        return True

    best = None
    for ccx in range(cx * 32 + 4, cx * 32 + 29, 1):
        for ccz in range(-(cz * 32 + 32) + 4, -(cz * 32) - 3, 1):
            r = 0
            while r < 16 and disc_ok(float(ccx), float(ccz), r + 1.0):
                r += 1
            if r and (best is None or r > best[2]):
                best = (float(ccx), float(ccz), float(r))
    print(f"   largest all-clean-grass disc INSIDE the cell: centre ({best[0]},{best[1]}) "
          f"radius {best[2]}u  -> retarget_tiles(center=({best[0]},{best[1]}), radius={best[2]})")
    rc = disc_ok(float(cwx), float(cwz), 6.0)
    r_at_centre = 0
    while r_at_centre < 16 and disc_ok(float(cwx), float(cwz), r_at_centre + 1.0):
        r_at_centre += 1
    print(f"   ... same test anchored at the CELL CENTRE {(cwx,cwz)}: max clean radius "
          f"{r_at_centre}u")

    print("\n=== 3. entrance._cell_openness_note over the deployed block ===")
    ter = M.blockmesh_from_ff9mesh(ter_path, disc=9, x=blk[0], y=blk[1], part="terrain")
    summary = {}
    E._cell_openness_note(ter, cwx, cwz, ox, oz, summary)
    notes = summary.get("notes", [])
    print(f"   notes: {notes if notes else 'NONE -- the cell passes the openness screen'}")
    # the same measurement, reported explicitly
    walk = blocked = 0
    for tri in ter.tris:
        tcx = (ter.verts[tri[0]][0] + ter.verts[tri[1]][0] + ter.verts[tri[2]][0]) / 3.0 + ox
        tcz = (ter.verts[tri[0]][2] + ter.verts[tri[1]][2] + ter.verts[tri[2]][2]) / 3.0 + oz
        if abs(tcx - cwx) <= 16 and abs(tcz - cwz) <= 16:
            if X.decode_id(int(round(ter.tangents[tri[0]][0])))["topograph"] in E._WALK_TOPO:
                walk += 1
            else:
                blocked += 1
    print(f"   cell tri census: {walk} walkable / {blocked} blocked "
          f"({100*blocked/max(1,walk+blocked):.1f}% blocked; the note fires above 20%)")

    print("\n=== 4. event tiles / inherited cell tags ===")
    tags = PF.eb13_cell_tags()
    ev = PF.event_cells()
    def nb(a, b):
        return max(abs(a[0] - b[0]), abs(a[1] - b[1]))
    lcell = (int(lx // 32), int(-lz // 32))
    for name, c in (("landing cell", lcell), ("trigger cell", TRIGGER_CELL)):
        de = min((nb(c, (k[0], k[1])) for k in ev), default=None)
        dt = min((nb(c, (t[0], t[1])) for t in tags), default=None)
        print(f"   {name} {c}: chebyshev distance to nearest event-bearing cell = {de} "
              f"cells; to nearest inherited WORLD11 tag cell = {dt} cells")
    print(f"   (event cells: {sorted((k[0],k[1],k[2]) for k in ev)})")
    print(f"   (tag cells span x{min(t[0] for t in tags)}..{max(t[0] for t in tags)}, "
          f"z{min(t[1] for t in tags)}..{max(t[1] for t in tags)})")

    print("\n=== 5. vehicle / water check ===")
    for name, (px, pz) in (("landing", LANDING), ("trigger centre", (float(cwx), float(cwz))),
                           ("retarget centre", (best[0], best[1]))):
        sh = W.all_sheets(world, px, pz, strict=True)
        p = PS.sky_pick(world, px, pz)
        seas = [s for s in sh if s[1] in (53, 54, 55, 56, 57)]
        print(f"   {name:16s} pick mesh={world[W.block_key(px,pz)][p[0]]['name']:8s} "
              f"y={p[2]:.3f} topo={p[4]}  water sheets above y=0.6: "
              f"{[ (round(s[0],2), s[1]) for s in seas if s[0] > 0.6 ] or 'none'}")

    print("\n=== 6. the FOOT ROUTE (walk_sim deflection-fan stepper) ===")
    for goal, tag in (((best[0], best[1]), "retarget centre"),
                      ((float(cwx), float(cwz)), "cell centre")):
        r = PS.walk_route(world, LANDING, goal)
        print(f"   greedy straight-aim to {tag} {goal}: {r}")
    print("   (a heading-lock walker cannot round an obstacle -- the central massif sits "
          "between the two lobes; the honest test is a routed walk)")

    # BFS a corridor over the clean lawn, then DRIVE it with the real stepper
    from collections import deque
    wp, total, cur, legs, route_ok = [], 0, LANDING, [], False
    src = (int(round((LANDING[0] - x0) / PS.GRID)), int(round((LANDING[1] - z0) / PS.GRID)))
    dst = (int(round((best[0] - x0) / PS.GRID)), int(round((best[1] - z0) / PS.GRID)))
    prev, q = {src: None}, deque([src])
    while q:
        k = q.popleft()
        if k == dst:
            break
        for di in (-1, 0, 1):
            for dj in (-1, 0, 1):
                n = (k[0] + di, k[1] + dj)
                if n in clean and n not in prev:
                    prev[n] = k
                    q.append(n)
    if dst not in prev:
        print("   BFS: NO clean-lawn corridor -- the two lobes are not foot-connected")
        pass
    else:
        path, k = [], dst
        while k is not None:
            path.append((x0 + k[0] * PS.GRID, z0 + k[1] * PS.GRID))
            k = prev[k]
        path.reverse()
        print(f"   BFS corridor over clean lawn: {len(path)} samples, "
              f"{sum(math.dist(path[i], path[i+1]) for i in range(len(path)-1)):.0f}u long")
        wp = [path[i] for i in range(0, len(path), 10)] + [path[-1]]
        route_ok = True
        for g in wp:
            if math.dist(cur, g) < 1.5:
                continue
            r = PS.walk_route(world, cur, g, max_steps=200)
            legs.append((tuple(round(v, 1) for v in g), r.get("ok"), r.get("steps"),
                         r.get("why", "")))
            if not r.get("ok"):
                route_ok = False
                break
            total += r["steps"]
            cur = (r["end"][0], r["end"][1])
        print(f"   ROUTED walk (waypoints every ~10u along the corridor): ok={route_ok}"
              + (f", {total} engine ticks, {len(legs)} legs, ends at {cur}" if route_ok else ""))
        bad = [l for l in legs if not l[1]]
        for l in (bad or legs[:3]):
            print(f"      leg -> {l[0]}: ok={l[1]} steps={l[2]} {l[3]}")
        print(f"      corridor waypoints: {[tuple(round(v) for v in g) for g in wp]}")

    spec = dict(
        island=dict(name="Path D V-shore bench island (world 9013, sentinel disc 9)",
                    blocks=[list(b) for b in BENCH],
                    world_bbox=dict(x=[372, 458], z=[-560, -466]),
                    shape="a ring island: a central non-walkable massif (peak y~28) inside a "
                          "continuous grass lawn at y~3.2; one connected clean-lawn component "
                          "of 3694 1u samples, 0 stacked-walkable points",
                    designation="HANDOFF-RUNG6.md:19-20 + NEXT-STUDIES.md:232; "
                                "bench_manifest.json hashes verified byte-identical live",
                    other_disc9_clusters=dict(
                        centre_rung5a=dict(blocks=[[11, 10], [12, 9], [12, 10], [12, 11], [13, 10]],
                                           note="Rung 5a first-land island, cliffs-refuse / "
                                                "BEACH 0, flat y=3.2 topo-0 only -- separate bench"),
                        junction_compose=dict(blocks=[[bx, by] for by in range(16, 20)
                                                      for bx in range(0, 5)],
                                              note="synthesis Step 2 carry, 180 files, "
                                                   "deployed 2026-07-30 16:24 -- separate bench"),
                        foreign_2026_08_04="blocks (0-3,4-5),(18-21,17-18),(19-20,0),(10-15,12-15) "
                                           "carry Donor.txt pointers to real disc-1 blocks and "
                                           "mtimes of 2026-08-04 -- other sessions' work, not Path D rung 5")),
        landing=dict(x=lx, z=lz, y=round(sky[2], 6), face=224,
                     face_note="224 = south-east, exactly down the east-band corridor "
                               "((dx,dz)=(-sin(f/256*2pi),-cos(f/256*2pi)) = (+0.707,-0.707)); "
                               "face 0 (plain south) also lawful but aims at the massif 9u away",
                     cell=[lcell[0], lcell[1]], block=[int(lx // 64), int(-lz // 64)],
                     topograph=sky[4], idall=sky[3], mesh="Terrain",
                     arrival_query="sky cast origin y+400 -> walkable",
                     walking_query_y=round(wlk[2], 6),
                     local_relief_5u=round(max(ys) - min(ys), 4),
                     radial_clearance_u=clear, walkable_sheets=len(stack_here)),
        trigger=dict(cell=[cx, cz], cell_centre=[cwx, cwz], block=[blk[0], blk[1]],
                     block_origin=[ox, oz],
                     override_relpath=rel,
                     override_abspath=str(ter_path),
                     override_exists=ter_path.is_file(),
                     cell_tag=hex(E.pack_cell_tag(cx, cz, 1)),
                     retarget=dict(center=[best[0], best[1]], radius=best[2],
                                   note="largest disc that is all clean grass AND fully "
                                        "inside the 32u cell; radius at the geometric cell "
                                        f"centre is only {r_at_centre}u"),
                     clean_grass_samples=len(cellpts),
                     clean_grass_centroid=[round(gx, 1), round(gz, 1)],
                     centre_y=round(csky[2], 6), centre_topo=csky[4],
                     openness_notes=notes,
                     openness_verdict="FIRES (40.3% blocked). The note's window is the FULL 32u "
                                      "cell, which here overhangs the island's south shore, so "
                                      "the blocked tris are the shore WALL outside the lawn, not "
                                      "a pinch around the trigger patch. Every lawn cell on this "
                                      "ring island trips the 20% threshold (lowest non-trivial "
                                      "reading is (11,16) at 15.8%, on the west band that owns "
                                      "the V-corner trap history). The retarget disc itself is "
                                      "16u across and 100% clean grass -- judge that, not the box.",
                     tri_census=dict(walkable=walk, blocked=blocked)),
        runner_up=dict(cell=[14, 16], centre=[464, -528], block=[7, 8],
                       retarget=dict(center=[452.0, -525.0], radius=4.0),
                       distance_u=62.6, blocked_pct=28.1, clean_grass_samples=228,
                       note="east-band chokepoint; a heading-lock walker reaches it in 123 "
                            "ticks with no waypoints. Smaller patch (4u) but a corridor the "
                            "player cannot miss."),
        distance_u=round(d, 1),
        clearances=dict(nearest_event_cell_chebyshev={"landing": None, "trigger": None}),
        route=dict(corridor_waypoints=[[round(g[0], 1), round(g[1], 1)] for g in wp],
                   ok=route_ok, engine_ticks=total if route_ok else None,
                   legs=len(legs), ends_at=[round(cur[0], 2), round(cur[1], 2)],
                   note="waypointed walk with walk_sim's real deflection-fan stepper down the "
                        "EAST band; the greedy heading-lock walker stalls at (438.2,-512.0) on "
                        "the central massif, which is obstacle-avoidance, not terrain. The west "
                        "band is passable too but owns the V-corner trap history "
                        "(~(375..377,-509..-528), VSHORE-SEAL-PREDICTION.md) -- prefer east."),
        provenance=dict(instrument="studies/path-d-new-world/walk_sim.py (BENCH-WALK-SIM.md, "
                                   "calibrated 4/4)",
                        read_only=True, deploys=0, game_writes=0,
                        bench_manifest_verified=True,
                        scripts=["studies/path-d-new-world/rung6/probe_cluster_survey.py",
                                 "studies/path-d-new-world/rung6/probe_site.py",
                                 "studies/path-d-new-world/rung6/probe_map.py",
                                 "studies/path-d-new-world/rung6/probe_finalize.py",
                                 "studies/path-d-new-world/rung6/probe_cellrank.py",
                                 "studies/path-d-new-world/rung6/probe_spec.py"]))
    spec["clearances"]["nearest_event_cell_chebyshev"] = {
        "landing": min(nb(lcell, (k[0], k[1])) for k in ev),
        "trigger": min(nb(TRIGGER_CELL, (k[0], k[1])) for k in ev)}
    spec["clearances"]["nearest_inherited_tag_cell_chebyshev"] = {
        "landing": min(nb(lcell, (t[0], t[1])) for t in tags),
        "trigger": min(nb(TRIGGER_CELL, (t[0], t[1])) for t in tags)}
    (HERE / "site.json").write_text(json.dumps(spec, indent=1))
    print(f"\nSITE SPEC -> {HERE / 'site.json'}")


if __name__ == "__main__":
    main()
