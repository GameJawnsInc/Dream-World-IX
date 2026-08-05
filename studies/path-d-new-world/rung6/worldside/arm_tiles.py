r"""Path D Rung 6, WORLD-SIDE half (2/2): ARM the trigger tiles on the 9013 V-shore bench.

The ``.eb`` function splice_exit.py adds is inert until some tile makes the engine FIRE
``ff9.WorldEvent`` for that cell. This script sets the per-triangle IDALL ``event`` bits on the
clean-grass patch inside trigger cell (13,17) of block (6,8), on the SENTINEL disc 9, and deploys
the edited ``Terrain.ff9mesh`` back into ``FF9CustomMap-world``.

GEOMETRY (site.json, measured -- do not re-derive by hand):
  cell (13,17) spans world x [416, 448) and z (-576, -544]; ``cell_world_center`` = (432, -560).
  The cell's GEOMETRIC centre is 1u from the shore -- its all-clean radius is 0u -- so the retarget
  disc is centred on the clean-grass lobe at (424, -553) instead. Max all-clean radius there is
  8.0u, which exactly touches the cell edges at x=416 / z=-545; the default 6.0u keeps a 2u margin
  inside them, so no armed triangle can straddle out of the cell (an armed tile outside the cell
  fires WorldEvent with a DIFFERENT cell tag that matches no function -- a silent dead tile the
  player stands on).

WHAT IS NOT TOUCHED: geometry. ``retarget_tiles`` rewrites ``tangent.x`` only; verts / normals /
uvs are byte-identical, and this script asserts that, because bad geometry under an overworld actor
bricks the save silently.

THE DISC-4 MIRROR: ``mesh.deploy_override`` does **not** call ``discmirror.auto_mirror`` -- the
mirror is an explicit post-step each CLI verb runs for itself, and this script deliberately does not
run it. Even if it did, ``auto_mirror`` refuses any source disc outside ``_REAL_DISCS = (1, 4)``
(discmirror.py:189-192): a synthetic sentinel namespace exists precisely to be disjoint from the
real trees, and mirroring disc 9 into Disc4 would recreate the collision s74 was built to prevent.
So there is no mirror to suppress on this path -- verified both ways.

  py arm_tiles.py --dry-run
  py arm_tiles.py
  py arm_tiles.py --target-root <scratch>       # offline verification against a copy
"""
from __future__ import annotations

import argparse
import hashlib
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _common as C  # noqa: E402


def parse_pair(s, cast=float):
    a, b = (cast(v) for v in str(s).replace(" ", "").split(","))
    return a, b


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="arm the Path-D 9013 exit trigger tiles (disc 9)")
    ap.add_argument("--game", default=str(C.DEFAULT_GAME),
                    help="the REAL install (unused for reads on this path -- kept so both scripts "
                         "take the same flags)")
    ap.add_argument("--target-root", default=None,
                    help="root that CONTAINS the mod folder to patch (default: --game)")
    ap.add_argument("--mod-folder", default=C.MOD_FOLDER)
    ap.add_argument("--cell", default="%d,%d" % C.TRIGGER_CELL, help="trigger cell 'cx,cz'")
    ap.add_argument("--event", type=int, default=C.TRIGGER_EVENT, help="event bits 1..3")
    ap.add_argument("--center", default="%s,%s" % C.TRIGGER_CENTER,
                    help="world XZ centre of the retarget disc, or the literal 'cell' to use the "
                         "cell's geometric centre (site survey: the cell centre's all-clean radius "
                         "is 0u -- do not)")
    ap.add_argument("--radius", type=float, default=C.TRIGGER_RADIUS)
    ap.add_argument("--disarm-stale", action="store_true",
                    help="clear the event bits on triangles inside the trigger cell that a PREVIOUS "
                         "run armed but this one does not target. Without it, a moved/shrunk region "
                         "is refused rather than silently leaving two live trigger patches.")
    ap.add_argument("--no-walkable-only", action="store_true",
                    help="keep the event bits on NON-walkable triangles the retarget disc caught "
                         "(the cell's shore-wall skirt). Default is to restore them: the player can "
                         "never stand on a non-walkable triangle, so arming it is inert surface.")
    ap.add_argument("--disc", type=int, default=C.SENTINEL_DISC)
    ap.add_argument("--lod", default="0_1")
    ap.add_argument("--bench-manifest",
                    default=str(Path(__file__).resolve().parents[2] / "bench_manifest.json"),
                    help="the owner-accepted Disc9 bench md5 manifest. The block we edit MUST be "
                         "either the accepted bytes or this script's own prior output -- 5 of the 7 "
                         "Disc9 clusters were rewritten by other sessions on 2026-08-04.")
    ap.add_argument("--skip-manifest-check", action="store_true")
    ap.add_argument("--armed-record",
                    default=str(Path(__file__).resolve().parent / "armed_manifest.json"),
                    help="where this script RECORDS the md5 it produced from the accepted bench, so "
                         "a later re-run can recognise its own output as evidence instead of "
                         "inferring it. Not a backup -- install backups go to the main repo.")
    ap.add_argument("--backup-dir", default=None)
    ap.add_argument("--dry-run", action="store_true", help="verify everything, write nothing")
    ap.add_argument("--force", action="store_true",
                    help="pass force_overwrite=True to deploy_override -- ONLY after checking who "
                         "owns the current bytes (the .ff9world.jsonl ledger refusal exists because "
                         "18+ sessions share this install)")
    ap.add_argument("--report", default=None)
    ap.add_argument("--log", default=None)
    args = ap.parse_args(argv)

    C.import_kit()
    from ff9mapkit.world import entrance as EN, extract as W, mesh as M
    from ff9mapkit.world.extract import decode_id

    log = C.Log()
    target_root = Path(args.target_root) if args.target_root else Path(args.game)
    cx, cz = parse_pair(args.cell, int)
    bx, by = EN.cell_to_block(cx, cz)
    cwx, cwz = EN.cell_world_center(cx, cz)
    ox, oz = W.block_world_origin(bx, by)
    center = (float(cwx), float(cwz)) if str(args.center).strip().lower() == "cell" \
        else parse_pair(args.center)
    tag = EN.pack_cell_tag(cx, cz, args.event)
    backup_dir = C.resolve_backup_dir(args.backup_dir, label="mesh")
    relpath = M.override_relpath(args.disc, bx, by, args.lod, "Terrain")
    dest = target_root / args.mod_folder / relpath
    # the cell's world footprint: x [cx*32, cx*32+32), z -(cz*32+32) .. -(cz*32)
    cell_box = (cx * EN.CELL_SIZE, cx * EN.CELL_SIZE + EN.CELL_SIZE,
                -(cz * EN.CELL_SIZE + EN.CELL_SIZE), -(cz * EN.CELL_SIZE))

    rep: dict = {"script": "arm_tiles.py", "dry_run": bool(args.dry_run),
                 "target_root": str(target_root), "mod_folder": args.mod_folder,
                 "cell": [cx, cz], "block": [bx, by], "event": args.event,
                 "cell_tag": f"0x{tag:04X}", "cell_center": [cwx, cwz],
                 "block_origin": [ox, oz], "retarget_center": list(center),
                 "retarget_radius": args.radius, "disc": args.disc, "lod": args.lod,
                 "override_relpath": relpath, "override_abspath": str(dest),
                 "cell_box": list(cell_box), "backup_dir": str(backup_dir), "ok": False}

    log.rule("Path D Rung 6 -- WORLD-SIDE (2/2): arm the exit-trigger tiles")
    log(f"  target root      : {target_root}")
    log(f"  cell             : ({cx},{cz})  tag 0x{tag:04X}  centre ({cwx},{cwz})")
    log(f"  cell world box   : x [{cell_box[0]}, {cell_box[1]})  z ({cell_box[2]}, {cell_box[3]}]")
    log(f"  block            : ({bx},{by})  origin ({ox},{oz})  disc {args.disc}  lod {args.lod}")
    log(f"  retarget         : centre {center}  radius {args.radius}  event={args.event}")
    log(f"  override         : {dest}")
    log(f"  MODE             : {'DRY RUN (no writes)' if args.dry_run else 'WRITE'}")

    # ---------------------------------------------------------------- pre-flight
    log.rule("(1) pre-flight -- the write path IS the sentinel-disc one, and the block exists")
    parts = Path(relpath).parts
    checks = {
        "path_is_disc9": (f"Disc{args.disc}" in parts,
                          f"relpath segments {parts}"),
        "path_not_disc1": ("Disc1" not in parts and "Disc4" not in parts,
                           "no real-disc segment anywhere in the write path"),
        "under_mod_folder": (args.mod_folder in dest.parts, f"writing under {args.mod_folder}"),
        "block_on_grid": (_grid_ok(bx, by), f"block ({bx},{by}) inside the 24x20 WMBlock grid"),
        "override_exists": (dest.is_file(),
                            "the block already has a deployed Path-D override -- this script EDITS "
                            "it, it never mints a block from nothing"),
        "cell_in_block": (EN.cell_to_block(cx, cz) == (bx, by), f"cell ({cx},{cz}) -> block ({bx},{by})"),
        "disc_between_center_and_cell": (
            center[0] - args.radius >= cell_box[0] and center[0] + args.radius <= cell_box[1]
            and center[1] - args.radius >= cell_box[2] and center[1] + args.radius <= cell_box[3],
            f"the retarget disc {center} r={args.radius} lies inside the cell's own 32u footprint"),
    }
    pre_ok = True
    for k, (v, detail) in checks.items():
        log(f"  {'ok  ' if v else 'FAIL'} {k}: {detail}")
        pre_ok &= bool(v)
    rep["preflight"] = {k: {"ok": bool(v), "detail": d} for k, (v, d) in checks.items()}
    if not pre_ok:
        rep["error"] = "pre-flight failed"
        C.write_report(args.report, rep)
        log.save(args.log)
        return 2

    on_disk = dest.read_bytes()
    rep["pre_sha256"] = C.sha(on_disk)
    rep["pre_bytes"] = len(on_disk)
    pre_md5 = hashlib.md5(on_disk).hexdigest()
    rep["pre_md5"] = pre_md5

    # THE BENCH FRESHNESS GATE. The owner-accepted V-shore bench blocks are pinned by md5 in
    # bench_manifest.json ("a rebuild that does not reproduce these is a regression"). Disc9 is a
    # shared, actively-written tree, so the ONE thing that must be true before we edit block (6,8)
    # is that it still holds the accepted bytes -- or, on a re-run, the bytes THIS script last
    # produced from them. Any third value means another session moved the ground under us, and the
    # right move is to stop, not to stack an edit on unknown geometry. Resolved after the retarget
    # (stage 2 below) because "our own prior output" is only knowable once we have recomputed it.
    accepted_md5 = None
    if not args.skip_manifest_check and args.bench_manifest and Path(args.bench_manifest).is_file():
        import json as _json
        man = _json.loads(Path(args.bench_manifest).read_text(encoding="utf-8"))
        accepted_md5 = (man.get("accepted") or {}).get(f"{bx},{by}")
        log(f"  bench manifest   : {args.bench_manifest}")
        log(f"  accepted md5 for block ({bx},{by}): {accepted_md5}")
        log(f"  on-disk md5      : {pre_md5}  -> "
            f"{'MATCHES the accepted bench' if pre_md5 == accepted_md5 else 'DIFFERS from the accepted bench'}")
    else:
        log("  bench manifest   : skipped")
    rep["bench_manifest"] = {"path": str(args.bench_manifest), "accepted_md5": accepted_md5,
                             "on_disk_md5": pre_md5,
                             "matches_accepted": accepted_md5 is not None and pre_md5 == accepted_md5}
    ver, vcount, icount, flags = M.read_ff9mesh_header(on_disk)
    log(f"  on-disk header   : version {ver}  vcount {vcount}  icount {icount}  flags {flags}  "
        f"({len(on_disk)} B, sha {C.sha(on_disk)[:16]})")

    # who owns the current bytes? (deploy_override REFUSES bytes that match no ledger entry)
    try:
        shas, last = M._ledger_shas(target_root / args.mod_folder, args.disc, bx, by, "Terrain")
        owned = (not shas) or (C.sha(on_disk) in shas)
        log(f"  ledger           : {len(shas)} recorded sha(s) for this cell+part; current bytes "
            f"{'MATCH a ledger entry' if C.sha(on_disk) in shas else ('no ledger yet' if not shas else 'MATCH NONE')}")
        if last:
            log(f"                     last write: {last.get('utc')} argv={last.get('argv')}")
        if not owned and not args.force:
            log("  NOTE: deploy_override will REFUSE this write (another session or a hand edit owns "
                "these bytes). Re-verify with bench_manifest.json, then re-run with --force if the "
                "bytes are legitimately ours.")
        rep["ledger"] = {"recorded_shas": len(shas), "current_owned": bool(owned),
                         "last": last}
    except Exception as ex:                                # noqa: BLE001 -- private helper, be soft
        log(f"  ledger           : precheck unavailable ({type(ex).__name__}: {ex})")

    # ---------------------------------------------------------------- read + census
    log.rule("(2) read the deployed override (stacked read) and census it")
    bm = EN.read_block_stacked(args.mod_folder, bx, by, disc=args.disc, lod=args.lod,
                               part="terrain", game=str(target_root))
    log(f"  loaded: {len(bm.verts)} verts, {len(bm.tris)} tris, vcount={bm.vcount}, "
        f"bm.disc={bm.disc}, name={bm.name!r}")
    if bm.vcount != vcount:
        log(f"  FATAL: read_block_stacked returned vcount {bm.vcount} but the file header says "
            f"{vcount} -- it did NOT read the override we backed up")
        rep["error"] = "stacked read did not return the deployed override"
        C.write_report(args.report, rep)
        log.save(args.log)
        return 2

    pre_tangents = [list(t) for t in bm.tangents]
    pre_verts = [tuple(v) for v in bm.verts]
    pre_normals = [tuple(v) for v in (bm.normals or [])]
    pre_uvs = [tuple(v) for v in (bm.uvs or [])]

    def tri_world_centroid(tri):
        return ((bm.verts[tri[0]][0] + bm.verts[tri[1]][0] + bm.verts[tri[2]][0]) / 3.0 + ox,
                (bm.verts[tri[0]][2] + bm.verts[tri[1]][2] + bm.verts[tri[2]][2]) / 3.0 + oz)

    block_events_before = [i for i, tri in enumerate(bm.tris)
                           if decode_id(int(round(bm.tangents[tri[0]][0])))["event"]]
    in_cell = [i for i, tri in enumerate(bm.tris)
               if cell_box[0] <= tri_world_centroid(tri)[0] < cell_box[1]
               and cell_box[2] < tri_world_centroid(tri)[1] <= cell_box[3]]
    hist: dict = {}
    for i in in_cell:
        d = decode_id(int(round(bm.tangents[bm.tris[i][0]][0])))
        k = (d["event"], d["topograph"])
        hist[k] = hist.get(k, 0) + 1
    log(f"  block-wide triangles already carrying event bits: {len(block_events_before)}")
    log(f"  triangles whose centroid is inside cell ({cx},{cz}): {len(in_cell)}")
    log(f"  (event, topograph) histogram in that cell: "
        f"{sorted(((k, v) for k, v in hist.items()), key=lambda kv: -kv[1])}")
    rep["census_before"] = {"block_event_tris": len(block_events_before),
                            "cell_tris": len(in_cell),
                            "cell_event_topo_hist": {f"{k[0]},{k[1]}": v for k, v in hist.items()}}

    # ---------------------------------------------------------------- retarget
    log.rule("(3) retarget_tiles -- IDALL event bits only, geometry untouched")
    n = M.retarget_tiles(bm, event=args.event, center=center, radius=args.radius,
                         world_origin=(ox, oz))
    log(f"  retarget_tiles(event={args.event}, center={center}, radius={args.radius}, "
        f"world_origin=({ox},{oz})) -> {n} triangles ARMED")
    rep["armed_tris"] = n
    if n == 0:
        log("  FATAL: 0 triangles armed -- the disc missed the mesh; nothing to deploy")
        rep["error"] = "0 triangles armed"
        C.write_report(args.report, rep)
        log.save(args.log)
        return 2

    # THE TARGET SET, recomputed independently of what actually CHANGED. ``armed`` must NOT be
    # "triangles whose bytes differ" -- on an idempotent re-run nothing differs and every downstream
    # check would silently evaluate over an empty set (found by the re-run in the offline harness).
    # This is retarget_tiles' own predicate (mesh.py:1277-1279), re-derived here as the oracle.
    targeted = [i for i, tri in enumerate(bm.tris)
                if math.hypot(tri_world_centroid(tri)[0] - center[0],
                              tri_world_centroid(tri)[1] - center[1]) <= args.radius]
    if len(targeted) != n:
        log(f"  FATAL: independent target-set recount {len(targeted)} != retarget_tiles' {n} -- the "
            f"predicate this script verifies against is not the one the kit applied")
        rep["error"] = f"target set recount {len(targeted)} != {n}"
        C.write_report(args.report, rep)
        log.save(args.log)
        return 2

    # every targeted triangle's FULL extent (all 3 corners), in world XZ
    xs = [bm.verts[v][0] + ox for i in targeted for v in bm.tris[i]]
    zs = [bm.verts[v][2] + oz for i in targeted for v in bm.tris[i]]
    bbox = (min(xs), max(xs), min(zs), max(zs))
    inside = (bbox[0] >= cell_box[0] and bbox[1] <= cell_box[1]
              and bbox[2] >= cell_box[2] and bbox[3] <= cell_box[3])
    log(f"  armed-triangle world bbox (all 3 corners): x [{bbox[0]:.2f}, {bbox[1]:.2f}]  "
        f"z [{bbox[2]:.2f}, {bbox[3]:.2f}]")
    log(f"  {'ok  ' if inside else 'WARN'} armed geometry lies fully inside cell ({cx},{cz})'s 32u "
        f"footprint -- an armed corner outside it fires a cell tag no function matches")
    rep["armed_bbox"] = list(bbox)
    rep["armed_inside_cell"] = bool(inside)

    # ---- THE WALKABLE-ONLY REFINEMENT -------------------------------------------------------
    # The 6u disc is 100% clean grass by the site survey's 1u GROUND-QUERY sampling, but a
    # TRIANGLE-centroid predicate also catches the cell's shore-wall skirt (topo 58/59), which
    # shares this XZ footprint underneath/behind the lawn. Arming those is inert -- the player can
    # never stand on a non-walkable triangle, so its IDALL is never the hit triangle -- but it is
    # surface we would be minting for no reason, and the cheapest way to not mint a defect is to
    # not mint the surface. Default ON: restore the pre-edit IDALL of every non-walkable targeted
    # triangle, so exactly the grass carries the event bits.
    walk = M_WALK()
    nonwalk = [i for i in targeted
               if decode_id(int(round(bm.tangents[bm.tris[i][0]][0])))["topograph"] not in walk]
    rep["targeted_tris"] = len(targeted)
    rep["targeted_nonwalkable"] = len(nonwalk)
    if nonwalk and not args.no_walkable_only:
        for i in nonwalk:
            for v in bm.tris[i]:
                bm.tangents[v][0] = pre_tangents[v][0]
        log(f"  walkable-only: restored {len(nonwalk)} non-walkable targeted triangles "
            f"(topo {sorted({decode_id(int(round(bm.tangents[bm.tris[i][0]][0])))['topograph'] for i in nonwalk})})"
            f" -> {len(targeted) - len(nonwalk)} grass triangles carry the event bits")
    elif nonwalk:
        log(f"  --no-walkable-only: {len(nonwalk)} of {len(targeted)} targeted triangles are NOT "
            f"on-foot walkable and stay armed (inert, but armed)")
    armed = [i for i in targeted if i not in set(nonwalk)] if not args.no_walkable_only else targeted
    rep["armed_effective"] = len(armed)
    log(f"  {'ok  ' if armed else 'FAIL'} effective armed set: {len(armed)} on-foot-walkable "
        f"triangles inside cell ({cx},{cz})")
    if not armed:
        log("  FATAL: nothing walkable left to arm")
        rep["error"] = "no walkable triangle in the retarget disc"
        C.write_report(args.report, rep)
        log.save(args.log)
        return 2
    axs = [bm.verts[v][0] + ox for i in armed for v in bm.tris[i]]
    azs = [bm.verts[v][2] + oz for i in armed for v in bm.tris[i]]
    log(f"  effective armed bbox: x [{min(axs):.2f}, {max(axs):.2f}]  "
        f"z [{min(azs):.2f}, {max(azs):.2f}]")
    rep["armed_effective_bbox"] = [min(axs), max(axs), min(azs), max(azs)]

    # ---- THE STALE-ARMING GUARD -------------------------------------------------------------
    # retarget_tiles only ever SETS bits inside its disc; it cannot clear a tile outside it. So
    # re-running with a MOVED or SHRUNK region silently leaves the previous run's tiles armed, and
    # the block ends up with two live trigger patches -- one of them at coordinates nobody measured
    # and nobody remembers. (Reproduced: --center 440,-550 --radius 5 over an already-armed block
    # yields 14 stale + 13 new.) The bench-freshness gate cannot catch this: it correctly reports
    # the block as OUR OWN output. This is its own, precise check.
    disarmed: list = []
    stale = [i for i in block_events_before if i not in set(armed)]
    stale_in_cell = [i for i in stale if i in set(in_cell)]
    stale_outside = [i for i in stale if i not in set(in_cell)]
    rep["stale_event_tris"] = {"total": len(stale), "in_trigger_cell": len(stale_in_cell),
                               "elsewhere_in_block": len(stale_outside)}
    if stale:
        log(f"  STALE ARMING: {len(stale)} triangle(s) already carry event bits but are NOT in this "
            f"run's target set ({len(stale_in_cell)} inside cell ({cx},{cz}), "
            f"{len(stale_outside)} elsewhere in block ({bx},{by}))")
        if stale_outside:
            log("  REFUSING: event tiles outside the trigger cell belong to some OTHER feature -- "
                "this script will not touch them. Resolve by hand.")
            rep["error"] = "stale event tiles outside the trigger cell"
            C.write_report(args.report, rep)
            log.save(args.log)
            return 2
        if args.disarm_stale:
            from ff9mapkit.world.extract import encode_id
            for i in stale_in_cell:
                d = decode_id(int(round(bm.tangents[bm.tris[i][0]][0])))
                idall = encode_id(0, d["area"], d["topograph"], d["flags"])
                for v in bm.tris[i]:
                    bm.tangents[v][0] = float(idall)
                disarmed.append(i)
            log(f"  --disarm-stale: cleared the event bits on {len(disarmed)} stale triangle(s) "
                f"inside the trigger cell")
        elif not args.force:
            log("  REFUSING to deploy: this would leave a SECOND live trigger patch at the previous "
                "region's coordinates. Re-run with --disarm-stale to clear them first (or --force "
                "if you genuinely want two patches).")
            rep["error"] = "stale arming from a previous, differently-parameterised run"
            C.write_report(args.report, rep)
            log.save(args.log)
            return 2
    rep["disarmed_tris"] = len(disarmed)

    # ---------------------------------------------------------------- geometry-untouched proof
    log.rule("(4) prove nothing but the IDALL changed")
    geo = {
        "verts_identical": [tuple(v) for v in bm.verts] == pre_verts,
        "normals_identical": [tuple(v) for v in (bm.normals or [])] == pre_normals,
        "uvs_identical": [tuple(v) for v in (bm.uvs or [])] == pre_uvs,
        "vcount_stable": bm.vcount == vcount,
        "tangent_rows_changed_only_x": all(
            pre_tangents[i][1:] == list(bm.tangents[i])[1:] for i in range(len(bm.tangents))),
    }
    changed_rows = sum(1 for i in range(len(bm.tangents)) if pre_tangents[i] != list(bm.tangents[i]))
    changed_tris = [i for i, tri in enumerate(bm.tris)
                    if any(pre_tangents[v][0] != bm.tangents[v][0] for v in tri)]
    geo["tangent_rows_changed"] = changed_rows
    geo["tangent_tris_changed"] = len(changed_tris)
    # verts are fully unindexed (vcount == icount), so each triangle owns 3 private vertex rows
    geo["rows_eq_3x_changed_tris"] = changed_rows == 3 * len(changed_tris)
    # every changed triangle must be one we deliberately armed -- nothing outside the disc moved
    geo["changed_subset_of_armed"] = set(changed_tris) <= (set(armed) | set(disarmed))
    for k, v in geo.items():
        if isinstance(v, bool):
            log(f"  {'ok  ' if v else 'FAIL'} {k}")
        else:
            log(f"       {k}: {v}")
    rep["geometry_checks"] = geo
    geo_ok = all(v for k, v in geo.items() if isinstance(v, bool))

    try:
        M.validate_blockmesh(bm)
        log("  ok   validate_blockmesh: the engine's own loader predicates + the UNINDEXED CONTRACT")
        rep["validate_blockmesh"] = True
    except ValueError as ex:
        log(f"  FAIL validate_blockmesh: {ex}")
        rep["validate_blockmesh"] = False
        rep["error"] = f"validate_blockmesh: {ex}"
        C.write_report(args.report, rep)
        log.save(args.log)
        return 2

    if not geo_ok or not inside:
        log("  REFUSING to deploy: a geometry/containment check failed above")
        rep["error"] = "geometry or containment check failed"
        C.write_report(args.report, rep)
        log.save(args.log)
        return 2

    # ---------------------------------------------------------------- backup + deploy
    log.rule("(5) back up, then deploy")
    new_bytes = M.ff9mesh_bytes(bm)
    post_md5 = hashlib.md5(new_bytes).hexdigest()
    log(f"  serialized: {len(new_bytes)} B (was {len(on_disk)} B, delta "
        f"{len(new_bytes) - len(on_disk):+d})  sha {C.sha(new_bytes)[:16]}  md5 {post_md5}")
    rep["post_bytes"] = len(new_bytes)
    rep["post_sha256"] = C.sha(new_bytes)
    rep["post_md5"] = post_md5

    # ---- bench freshness gate, stage 2 (see stage 1 above) ----
    # Three verdicts, in descending strength of EVIDENCE -- named honestly, because "this is
    # probably our own output" is an inference, not a record, and the two should not read alike:
    #   RECORDED  the on-disk md5 appears in armed_manifest.json, written by a previous successful
    #             run of THIS script that started from the accepted bench. Positive evidence.
    #   ACCEPTED  the on-disk md5 IS the owner-accepted bench block. Positive evidence.
    #   INFERRED  arming it changes nothing, so it already carries exactly this arming -- consistent
    #             with our own prior output, but a foreign block could look the same. Allowed (a
    #             fresh worktree has no record) and logged as the weak case it is.
    # Anything else = another session moved the ground under us -> refuse.
    if accepted_md5 is not None:
        recorded = _load_armed_record(args.armed_record).get(f"{bx},{by}", [])
        rec_md5s = {r.get("armed_md5") for r in recorded}
        if pre_md5 == accepted_md5:
            verdict, evidence, gate_ok = "the owner-accepted bench block", "ACCEPTED", True
        elif pre_md5 in rec_md5s:
            verdict, evidence, gate_ok = ("a recorded output of a previous arm_tiles run",
                                          "RECORDED", True)
        elif pre_md5 == post_md5:
            verdict, evidence, gate_ok = ("already carrying exactly this arming (consistent with "
                                          "our own prior output, but unrecorded)", "INFERRED", True)
        else:
            verdict, evidence, gate_ok = ("NEITHER the accepted bench, NOR a recorded output, NOR "
                                          "already-armed-identically", "NONE", False)
        log(f"  {'ok  ' if gate_ok else 'FAIL'} bench freshness [{evidence}]: the on-disk block is "
            f"{verdict}")
        rep["bench_manifest"].update({"verdict": verdict, "evidence": evidence, "gate_ok": gate_ok,
                                      "recorded_md5s": sorted(m for m in rec_md5s if m)})
        if not gate_ok and not args.force:
            log("  REFUSING to deploy: this block is not the bench we measured the site on. Either "
                "another session rewrote it, or you are stacking a SECOND arming region onto an "
                "already-armed block (the first region would stay armed). Diff it against the "
                "bench first. (--force overrides, --skip-manifest-check disables the gate.)")
            rep["error"] = "bench freshness gate failed"
            C.write_report(args.report, rep)
            log.save(args.log)
            return 2
    rep["backup"] = C.backup_file(dest, backup_dir, f"mesh/{Path(relpath).name}",
                                  dry_run=args.dry_run)
    if args.dry_run:
        log(f"  DRY RUN: would back up -> {rep['backup']['backup']}")
        log(f"  DRY RUN: would write   -> {dest}")
        log("  DRY RUN: would append one line to "
            f"{target_root / args.mod_folder / M.LEDGER_NAME}")
        rep["ok"] = True
        rep["written"] = False
    else:
        M.set_deploy_argv(["arm_tiles.py"] + list(sys.argv[1:]))
        out = M.deploy_override(bm, mod_folder=args.mod_folder, game=str(target_root),
                                lod=args.lod, part="Terrain", disc=args.disc,
                                backup=True, force_overwrite=bool(args.force))
        log(f"  deploy_override -> {out}")
        log("  NOTE: discmirror.auto_mirror was NOT called -- deploy_override never calls it, and "
            "auto_mirror refuses any non-real disc (discmirror.py:189) anyway.")
        rep["written_path"] = str(out)
        rep["written"] = True
        ledger = target_root / args.mod_folder / M.LEDGER_NAME
        log(f"  ledger {'appended' if ledger.is_file() else 'MISSING?'}: {ledger}")

        # ---- read-back verification ----
        back = Path(out).read_bytes()
        rep["readback_sha256"] = C.sha(back)
        same = back == new_bytes
        log(f"  read-back identical to what we serialized: {same}")
        rb = M.blockmesh_from_ff9mesh(out, disc=args.disc, x=bx, y=by, lod=args.lod, part="terrain")
        rb_events = [i for i, tri in enumerate(rb.tris)
                     if decode_id(int(round(rb.tangents[tri[0]][0])))["event"] == args.event]
        # what the block SHOULD carry afterwards = the triangles we deliberately armed, UNION any
        # that already carried this event id before (elsewhere in the block, or here from a prior
        # identical run -- which is exactly why `armed` is the TARGET set and not the DIFF set).
        already = {i for i in block_events_before
                   if decode_id(int(round(pre_tangents[bm.tris[i][0]][0])))["event"] == args.event}
        want = len(set(armed) | already)
        log(f"  read-back census: {len(rb_events)} triangles carry event={args.event} "
            f"(expected {want} = {len(armed)} armed by this run | "
            f"{len(already - set(armed))} pre-existing elsewhere in the block)")
        rep["readback_event_tris"] = len(rb_events)
        rep["ok"] = bool(same and len(rb_events) == want)

        # record what we produced, so a later re-run recognises its own output as EVIDENCE rather
        # than inferring it from "arming changes nothing" (see the freshness gate above)
        if rep["ok"] and args.armed_record:
            _append_armed_record(args.armed_record, f"{bx},{by}", {
                "armed_md5": post_md5, "from_md5": pre_md5,
                "from_accepted_bench": accepted_md5 is not None and pre_md5 == accepted_md5,
                "utc": __import__("datetime").datetime.now(
                    __import__("datetime").timezone.utc).isoformat(timespec="seconds"),
                "cell": [cx, cz], "event": args.event, "center": list(center),
                "radius": args.radius, "walkable_only": not args.no_walkable_only,
                "armed_tris": len(armed)})
            log(f"  armed record -> {args.armed_record}")

    if not args.dry_run and rep.get("backup", {}).get("written"):
        C.write_report(backup_dir / "manifest-mesh.json", rep)
        log(f"  backup manifest -> {backup_dir / 'manifest-mesh.json'}")

    log.rule("RESULT: " + ("PASS" if rep["ok"] else "FAIL"))
    log(f"  {len(armed)} walkable triangles armed with event={args.event} ({n} in the disc, "
        f"{len(armed)} kept) in cell ({cx},{cz}) -> tag 0x{tag:04X}; "
        f"{'nothing written (dry run)' if args.dry_run else 'deployed'}")
    C.write_report(args.report, rep)
    log.save(args.log)
    return 0 if rep["ok"] else 1


def _load_armed_record(path) -> dict:
    """``{"bx,by": [{"armed_md5", "from_md5", "utc", ...}, ...]}`` -- the positive record of what
    this script has produced. Missing/corrupt file reads as empty (it is evidence, never a gate we
    can be locked out by)."""
    import json
    p = Path(path) if path else None
    if not p or not p.is_file():
        return {}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except ValueError:
        return {}


def _append_armed_record(path, key: str, row: dict) -> None:
    import json
    p = Path(path)
    d = _load_armed_record(p)
    rows = d.setdefault(key, [])
    if not any(r.get("armed_md5") == row.get("armed_md5") for r in rows):
        rows.append(row)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, indent=1), encoding="utf-8")


def M_WALK():
    """The engine's on-foot walkable topograph set, decoded by the kit from Memoria's own
    ``w_movementCheckTopographID`` mask (``entrance._WALK_TOPO``)."""
    from ff9mapkit.world.entrance import _WALK_TOPO
    return _WALK_TOPO


def _grid_ok(x, y) -> bool:
    from ff9mapkit.world.mesh import block_in_grid
    return block_in_grid(x, y)


if __name__ == "__main__":
    raise SystemExit(main())
