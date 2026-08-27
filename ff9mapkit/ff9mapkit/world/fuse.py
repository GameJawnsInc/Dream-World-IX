"""Cross-donor FUSE: compose several verbatim transplants into ONE contiguous custom region.

THE FUSE LAW (2026-07-09): two carried landmasses may not be knitted at the LAND -- a
coastline is a component (beach welds, shore systems, painted washes are all copy-only), so
re-drawing two coasts into each other is forbidden by every proven edit law. What CAN knit is
the WATER: sea4 is the anti-tiling quadrant band (interchangeable tiles, not directional
Wang), so a sea4-vs-sea4 block border is always legal -- it is exactly why a carried island
already sits clean next to prefab ocean. A "continent" is therefore a LAYOUT: several
complete donors in adjacent target rects, each keeping its own verbatim coast, every shared
border certified open water.

What was missing: two adjacent deploys' shared border was audited by NOTHING -- each
transplant's gates stop at its own frame (`_split_frame_pairs` deliberately treats
frame-plane pairs as benign because the frame is expected to face prefab). `fuse_layout`
closes that: it dry-runs every placement, reads the `frame_profile` each summary now emits
(per frame edge, per 4u row: the parts reaching the plane + an on-lattice flag + which
border cells deploy), and certifies every shared border row-by-row. A row passes iff EACH
side is either PREFAB (its border cell deploys nothing -- the engine renders sea prefab, the
proven configuration) or pure OPEN WATER on the lattice reaching the plane. Land, beach, a
shallow system, an off-lattice conforming vert, or a deployed cell whose content stops short
of the frame (a gap) all refuse -- e.g. the (10,17) donor's WEST frame carries its live
sea1/sea3/sea5 shore system to the border (it continues into the real neighbour in situ), so
that edge can only face prefab, never another placement.
"""
from __future__ import annotations

import math
from pathlib import Path

from .. import config
from . import transplant as TR
from .transplant import OPEN_WATER_PARTS
from . import mesh as M


def _rect(summary) -> tuple:
    (bx, by), (tw, th) = summary["cell"], summary["tsize"]
    return (int(bx), int(by), int(tw), int(th))


#: Open-water grade ranks along the real ladder shore->sea3->sea5->sea4->deep. Two fused
#: rows whose ranks sit >=2 apart (sea3 directly facing sea4, skipping the sea5 blend) form
#: an adjacency that never occurs in real data -- REPORTED per border as ``grade_jumps``,
#: not failed (prefab sea counts as deep/rank 2).
_GRADE = {"sea3": 0, "sea5": 1, "sea4": 2}


def _side_row(summary, edge: str, w: int) -> tuple:
    """Classify one side of a shared border at world 4u row/column ``w`` ->
    ``(state, parts)``: ``prefab`` (border cell deploys nothing), ``water`` (pure open
    water on-lattice reaching the plane), ``gap`` (a deployed cell whose content stops
    short of the frame), ``off-lattice``, or ``blocked:<parts>`` (land/beach/shallows
    at the frame)."""
    (bx, by, tw, th) = _rect(summary)
    fp = summary["frame_profile"][edge]
    if edge in ("E", "W"):
        block = (-(w + 1)) // 16 - by         # world z row -> edge-local block row j
        region_row = w + 16 * by
    else:
        block = w // 16 - bx                  # world x col -> edge-local block col i
        region_row = w - 16 * bx
    if block not in fp["deployed"]:
        return ("prefab", ())
    row = fp["rows"].get(str(region_row))
    if row is None:
        return ("gap", ())
    if not row["lattice"]:
        # THE STRAIT UNLOCK (study 3): an off-lattice vert on a PURE open-water row
        # cannot tear land -- it is a conforming water vert of the donor's own sheet,
        # lawful against another placement's water or prefab (the pair rule still
        # refuses it against anything else). Land/beach/shallow off-lattice stays a
        # hard refusal.
        if set(row["parts"]) <= OPEN_WATER_PARTS:
            return ("water-offlat", tuple(row["parts"]))
        return ("off-lattice", tuple(row["parts"]))
    if set(row["parts"]) <= OPEN_WATER_PARTS:
        return ("water", tuple(row["parts"]))
    return ("blocked:" + ",".join(p for p in row["parts"] if p not in OPEN_WATER_PARTS),
            tuple(row["parts"]))


def _side_state(summary, edge: str, w: int) -> str:
    return _side_row(summary, edge, w)[0]


def _shared_borders(summaries) -> list:
    """Every shared border between two placements' target rects: ``(ia, ib, edge_a,
    world_plane, [world 4u rows/cols across the overlap])`` -- ``edge_a`` is placement
    ``ia``'s facing edge (E or S; the W/N cases emit with the pair swapped)."""
    out = []
    for ia in range(len(summaries)):
        (abx, aby, atw, ath) = _rect(summaries[ia])
        for ib in range(len(summaries)):
            if ib == ia:
                continue
            (bbx, bby, btw, bth) = _rect(summaries[ib])
            if abx + atw == bbx:              # A.E touches B.W
                jlo, jhi = max(aby, bby), min(aby + ath, bby + bth)
                if jlo < jhi:
                    rows = [w for j in range(jlo, jhi)
                            for w in range(-16 * (j + 1), -16 * j)]
                    out.append((ia, ib, "E", 64.0 * bbx, rows))
            if aby + ath == bby:              # A.S touches B.N
                ilo, ihi = max(abx, bbx), min(abx + atw, bbx + btw)
                if ilo < ihi:
                    cols = [c for i in range(ilo, ihi)
                            for c in range(16 * i, 16 * (i + 1))]
                    out.append((ia, ib, "S", -64.0 * bby, cols))
    return out


_OPPOSITE = {"E": "W", "S": "N"}


#: THE MOD-TREE OCCUPANCY READ now lives beside the write seam so every world writer shares
#: ONE reader (see :func:`ff9mapkit.world.mesh.existing_overrides`). Kept as a module-local
#: name so this file's call site and its tests read unchanged.
_existing_overrides = M.existing_overrides

def fuse_layout(mod_folder: str, placements, *, disc: int = 1, lod: str = "0_1", game=None,
                allow_overwrite: bool = False, dry_run: bool = False,
                skip_mirror: bool = False,
                target_disc: int | None = None, all_sea_target: bool = False) -> dict:
    """Validate + deploy a multi-placement LAYOUT. Each placement is a dict of
    :func:`ff9mapkit.world.transplant.transplant_region` kwargs (``cell``, ``donor``,
    ``size``; optional ``rot``, ``shift``, ``tweaks``, ``strips``, ``land_margin``,
    ``extra``, ``census_samples``). Every placement must gate clean on its own; target
    rects must not overlap; every shared border must certify per the fuse law (each 4u
    row: prefab or pure on-lattice open water on BOTH sides); target cells must not
    collide with overrides already on disk (unless ``allow_overwrite`` -- re-deploying
    the same layout is the normal iteration flow). ``dry_run`` stops after validation.
    A real deploy auto-mirrors the WHOLE layout's written overrides to Disc4 in ONE pass
    after every placement lands (``skip_mirror=True`` opts out; each per-placement
    :func:`~ff9mapkit.world.transplant.transplant_region` call defers its own mirror to this).

    TWEAKED placements pass ``tweaks_factory`` (a zero-arg callable returning a FRESH
    tweak list), not ``tweaks``: tweak objects are STATEFUL (gate counters, the mint's
    pre-reconciliation mutation), and a layout run applies each placement TWICE -- the
    per-placement gate pass and then the deploy pass -- so the factory rebuilds
    between them (deterministic builders make both passes byte-identical). Plain
    ``tweaks`` stay legal for ``dry_run`` (one apply) and refuse a real deploy
    actionably. Returns ``{placements, fuse_gates, clean, deployed}``."""
    if not dry_run:
        for i, pl in enumerate(placements):
            if pl.get("tweaks") and not pl.get("tweaks_factory"):
                raise ValueError(
                    f"placement #{i} carries plain 'tweaks' on a REAL deploy -- tweak "
                    f"objects are stateful and a layout run applies each placement "
                    f"twice (gates + deploy); pass 'tweaks_factory' (a zero-arg "
                    f"builder returning a fresh list) instead")

    def _kw(pl):
        kw = dict(pl)
        kw.setdefault("shift", (0.0, 0.0))
        fac = kw.pop("tweaks_factory", None)
        if fac is not None:
            kw["tweaks"] = list(fac()) + list(kw.pop("tweaks", ()) or ())
        return kw
    # THE READ/WRITE DISC SPLIT: `disc` stays the STOCK read disc for every donor byte; `rtarget`
    # is the namespace the layout deploys into AND the one the collision pre-check must scan --
    # checking Disc1 while writing Disc9 would miss every real collision and flag phantom ones.
    rtarget = disc if target_disc is None else int(target_disc)
    summaries = []
    for pl in placements:
        summaries.append(TR.transplant_region("UNUSED", disc=disc, lod=lod, game=game,
                                              dry_run=True, target_disc=rtarget,
                                              all_sea_target=all_sea_target, **_kw(pl)))
    gates = []
    for i, s in enumerate(summaries):
        gates.append({"gate": f"placement[{i}]", "donor": s["donor"], "cell": s["cell"],
                      "ok": s["clean"],
                      "bad": [g["gate"] for g in s["gates"] if not g["ok"]]})
    rects = [_rect(s) for s in summaries]
    overlaps = []
    for a in range(len(rects)):
        (abx, aby, atw, ath) = rects[a]
        for b in range(a + 1, len(rects)):
            (bbx, bby, btw, bth) = rects[b]
            if abx < bbx + btw and bbx < abx + atw and aby < bby + bth and bby < aby + ath:
                overlaps.append([a, b])
    gates.append({"gate": "rect-overlap", "pairs": overlaps, "ok": not overlaps})
    for (ia, ib, edge, plane, rows) in _shared_borders(summaries):
        bad = []
        jumps = []
        for w in rows:
            (sa, pa) = _side_row(summaries[ia], edge, w)
            (sb, pb) = _side_row(summaries[ib], _OPPOSITE[edge], w)
            if sa not in ("prefab", "water", "water-offlat") \
                    or sb not in ("prefab", "water", "water-offlat"):
                bad.append({"row": w, "a": sa, "b": sb})
                continue
            ra = {2} if sa == "prefab" else {_GRADE[p] for p in pa}
            rb = {2} if sb == "prefab" else {_GRADE[p] for p in pb}
            if ra and rb and min(abs(x - y) for x in ra for y in rb) >= 2:
                jumps.append(w)
        gates.append({"gate": f"fuse[{ia}.{edge}|{ib}.{_OPPOSITE[edge]}]", "plane": plane,
                      "rows": len(rows), "bad": bad[:8], "n_bad": len(bad),
                      "grade_jumps": len(jumps), "ok": not bad})
    tcells = [(bx + i, by + j) for (bx, by, tw, th) in rects
              for i in range(tw) for j in range(th)]
    existing = _existing_overrides(tcells, mod_folder, disc=rtarget, lod=lod, game=game) \
        if mod_folder != "UNUSED" else []
    gates.append({"gate": "existing-overrides", "files": existing[:8],
                  "n_files": len(existing), "ok": allow_overwrite or not existing})
    clean = all(g["ok"] for g in gates)
    out = {"op": "fuse-layout", "placements": summaries, "fuse_gates": gates,
           "clean": clean, "dry_run": dry_run, "deployed": []}
    if dry_run or not clean:
        return out
    for pl in placements:
        s = TR.transplant_region(mod_folder, disc=disc, lod=lod, game=game,
                                 dry_run=False, skip_mirror=True, target_disc=rtarget,
                                 all_sea_target=all_sea_target, **_kw(pl))
        out["deployed"].extend(s["deployed"])
    from . import discmirror as DM
    DM.auto_mirror(out["deployed"], mod_folder=mod_folder, skip_mirror=skip_mirror)
    return out


# ------------------------------------------------------------- composition (audit rec 16)
#
# THE COMPOSED WORLD, one toml: the Southern Ring was built base-mint -> relief -> nav-stamp
# across many sessions of hand-ordered verbs; nothing recorded the order or refused a foreign
# overwrite. `compose_layout` extends the world-fuse toml with one table per EXISTING verb --
# each handler calls that verb's shipped Python entry point unchanged (the productized-builder
# pattern; NO new geometry code) -- runs them in the fixed three-tier order below (a literal
# ordered list, not a topological solver), and writes `world_manifest.json` beside the deploys
# (per-file md5 + the spec table that produced it, the bench_pipeline manifest pattern). A
# later compose REFUSES when a manifest-recorded file's on-disk md5 has diverged (a hand edit,
# a foreign session) unless allow_overwrite -- the per-write ownership refusal at the seam
# (audit rec 6) guards single writes; this guards the COMPOSITION.

#: The fixed execution order: base mint (placement layouts + synthetic islands) -> interior
#: relief (reads the DEPLOYED bytes the base tier wrote) -> navigation stamps (reclassify the
#: deployed water). Within a tier, rows run in document order.
COMPOSE_TIERS = (("placement", "island"), ("mountain", "forest", "hill"),
                 ("coastnav", "rim_retile"))
COMPOSE_TABLES = tuple(t for tier in COMPOSE_TIERS for t in tier)

_MANIFEST_NAME = "world_manifest.json"
_SKIP_MARKERS = (".bak-", ".prerim")         # write-seam backups, never composition output


def _world_tree_md5(mod_root: Path) -> dict:
    """``relpath -> md5`` over the mod folder's WorldMap tree (backups + the manifest and
    ledger excluded) -- the before/after snapshot that attributes files to compose steps."""
    import hashlib
    root = mod_root / "FF9_Data" / "WorldMap"
    out = {}
    if not root.is_dir():
        return out
    from .mesh import LEDGER_NAME
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.name in (_MANIFEST_NAME, LEDGER_NAME) \
                or any(m in p.name for m in _SKIP_MARKERS):
            continue
        out[p.relative_to(mod_root).as_posix()] = hashlib.md5(p.read_bytes()).hexdigest()
    return out


def _parse_block_rect(spec) -> list:
    """``"BX,BY"`` / ``"BX0-BX1,BY0-BY1"`` (either axis a range) or an explicit list of
    ``[x, y]`` pairs -> block tuples (the world-mountain --donor grammar)."""
    if not isinstance(spec, str):
        return [tuple(int(v) for v in c) for c in spec]

    def rng(s):
        if "-" in s:
            a, b = s.split("-")
            return list(range(int(a), int(b) + 1))
        return [int(s)]
    xs, ys = spec.split(",")
    return [(x, y) for x in rng(xs) for y in rng(ys)]


def _row_point(table: str, row: dict) -> tuple:
    """``(wx, wz), exact`` from a row's ``center`` (exact) or ``near`` (snap) key."""
    if "center" in row:
        wx, wz = (float(v) for v in row["center"])
        return (wx, wz), True
    if "near" in row:
        wx, wz = (float(v) for v in row["near"])
        return (wx, wz), False
    raise ValueError(f"[[{table}]] needs center=[wx,wz] or near=[wx,wz]")


def _strict_keys(table: str, row: dict, allowed: set) -> None:
    bad = sorted(set(row) - allowed)
    if bad:
        raise ValueError(f"[[{table}]]: unknown key(s) {bad} -- allowed: {sorted(allowed)}")


def compose_layout(mod_folder: str, doc: dict, *, placements=(), disc: int = 1,
                   lod: str = "0_1", game=None, allow_overwrite: bool = False,
                   dry_run: bool = False, skip_mirror: bool = False,
                   target_disc: int | None = None, all_sea_target: bool = False) -> dict:
    """Run a composed layout ``doc`` (parsed toml) through the fixed tier order. Each table
    row calls its verb's existing entry point with the kwargs it already accepts; unknown
    keys refuse (typo protection). ``placements`` is the CLI-parsed ``[[placement]]`` list
    (tweak factories attached) and runs through :func:`fuse_layout` as tier 0's first step.

    A REAL run stops at the first failing step (later tiers read the deployed bytes the
    earlier tiers wrote; there is nothing sound to continue onto) -- already-deployed
    earlier steps stay, and every remaining step is reported ``skipped``. A DRY run reports
    every step against the CURRENT on-disk state: a relief row aimed at an island the same
    doc has not deployed yet will honestly fail its read (a stack that does not exist
    cannot be dry-run).

    LAYERED OVERWRITE DEFENSE (deliberate, measured live): ``allow_overwrite`` waives THIS
    function's manifest-drift gate only. The per-write ownership refusal at the seam
    (:func:`ff9mapkit.world.mesh.deploy_override`, audit rec 6) still fires on a file whose
    bytes match no ledger sha -- that law guards OTHER SESSIONS' work and has its own lever
    (``FF9_WORLD_FORCE_OVERWRITE``). A compose flag that silently forced the seam would let
    one reflexive ``--allow-overwrite`` steamroll a concurrent session's deploys.

    Returns ``{op, gates, clean, dry_run, manifest}`` -- ``gates`` carries the drift gate
    plus one gate per step (with the files each real step wrote)."""
    import json
    rtarget = disc if target_disc is None else int(target_disc)
    game_path = config.find_game_path(game)
    mod_root = game_path / mod_folder
    man_path = mod_root / "FF9_Data" / "WorldMap" / _MANIFEST_NAME

    # ---- THE MANIFEST DRIFT GATE: refuse to build over diverged bytes -------------------
    old_manifest = json.loads(man_path.read_text(encoding="utf-8")) if man_path.is_file() \
        else None
    pre = _world_tree_md5(mod_root)
    recorded: dict = {}
    for e in (old_manifest or {}).get("entries", ()):        # later entries win
        recorded.update(e.get("files", {}))
    drift = sorted(p for p, h in recorded.items() if p in pre and pre[p] != h)
    gates = [{"gate": "manifest-drift", "diverged": drift[:8], "n_diverged": len(drift),
              "recorded": len(recorded), "ok": allow_overwrite or not drift}]
    if drift and not allow_overwrite and not dry_run:
        return {"op": "compose", "gates": gates, "clean": False, "dry_run": dry_run,
                "manifest": str(man_path)}

    # ---- the per-table runners (each calls the verb's shipped entry point) --------------
    def _island_runner(row):
        from . import island as I
        _strict_keys("island", row, {"center", "cell", "radius", "height", "patches",
                                     "seed", "lobes", "rim_run", "flat", "ground",
                                     "relief_amp", "relief_seed", "coastnav",
                                     "coastnav_policy"})
        ren = {"radius": "base_radius", "height": "land_height", "patches": "n_patches"}
        kw = {ren.get(k, k): v for k, v in row.items() if k not in ("center", "cell")}
        if "center" in row:
            kw["center"] = tuple(float(v) for v in row["center"])
        elif "cell" in row:
            kw["cell"] = tuple(int(v) for v in row["cell"])
        else:
            raise ValueError("[[island]] needs center=[wx,wz] or cell=[bx,by]")
        # allow_overwrite must reach the mint too: compose's own existing-overrides check
        # (:func:`_existing_overrides`, called from `fuse_layout`) covers the TRANSPLANT tier
        # only, so without this an [[island]] row bypassed the occupancy gate entirely.
        return I.landmass(mod_folder, disc=disc, lod=lod, game=game, dry_run=dry_run,
                          skip_mirror=skip_mirror, target_disc=target_disc,
                          all_sea_target=all_sea_target, allow_overwrite=allow_overwrite, **kw)

    def _relief_runner(table, row):
        from . import interior as IN
        pt, exact = _row_point(table, row)
        loc = dict(center=pt if exact else None, near=None if exact else pt)
        if table == "hill":
            _strict_keys(table, row, {"center", "near", "height", "radius"})
            radius = float(row.get("radius", 18.0))
            reach = max(96.0, radius + 10.0)
        else:
            _strict_keys(table, row, {"center", "near", "donor", "reach", "ground"}
                         if table == "mountain" else {"center", "near", "donor", "reach"})
            reach = float(row.get("reach", 96.0))
        blocks = IN.read_deployed_blocks(mod_folder, near=pt, reach=reach, disc=disc,
                                         game=game, target_disc=target_disc)
        soup = IN.soup_from_blocks(blocks)
        if table == "forest":
            res = IN.carve_forest(soup, donor=tuple(int(v) for v in row["donor"]),
                                  disc=disc, game=game, **loc)
            IN.census_gate(res["changed"], disc=disc, game=game,
                           probe=(res["center"], 37), baseline=blocks)
        elif table == "hill":
            res = IN.build_hill(soup, height=float(row.get("height", 4.2)),
                                radius=radius, **loc)
            IN.census_gate(res["changed"], disc=disc, game=game, baseline=blocks)
        else:                                                # mountain
            extra = {"ground": row["ground"]} if "ground" in row else {}
            res = IN.carve_mountain(soup, donor=_parse_block_rect(row["donor"]),
                                    disc=disc, game=game, **loc, **extra)
            IN.census_gate(res["changed"], disc=disc, game=game, baseline=blocks,
                           parts=res.get("changed_parts"))
        if not dry_run:
            written = list(IN.deploy_changed(res["changed"], mod_folder=mod_folder,
                                             disc=disc, game=game, skip_mirror=True,
                                             target_disc=target_disc))
            if table == "mountain":
                written += list(IN.deploy_mountain_parts(res, mod_folder=mod_folder,
                                                         disc=disc, game=game,
                                                         skip_mirror=True,
                                                         target_disc=target_disc))
            from . import discmirror as DM
            DM.auto_mirror(written, mod_folder=mod_folder, skip_mirror=skip_mirror)
        return res

    def _coastnav_runner(row):
        from . import coastnav as CN
        _strict_keys("coastnav", row, {"cells", "policy", "disc"})
        cells = [tuple(int(v) for v in c) for c in row["cells"]] if "cells" in row else None
        return CN.stamp(mod_folder, disc=int(row.get("disc", rtarget)), cells=cells,
                        policy=row.get("policy", "land-anywhere"),
                        deploy=not dry_run, game=game)

    def _rim_runner(row):
        from . import rimretile as RR
        _strict_keys("rim_retile", row, {"cells", "donor", "size"})
        cells = [tuple(int(v) for v in c) for c in row["cells"]]
        dx, dy = (int(v) for v in row["donor"])
        size = row.get("size", "1x1")
        nx, ny = (tuple(int(v) for v in size.lower().split("x")) if isinstance(size, str)
                  else (int(size[0]), int(size[1])))
        donors = [(dx + i, dy + j) for j in range(ny) for i in range(nx)]
        rep = RR.rim_retile(mod_folder, cells, donors, disc=disc, target_disc=target_disc,
                            game=game, apply=not dry_run)
        if rep.get("refused"):
            raise ValueError(f"rim-retile refused: {rep['refused']}")
        return rep

    def _placement_runner(_row):
        out = fuse_layout(mod_folder, list(placements), disc=disc, lod=lod, game=game,
                          allow_overwrite=allow_overwrite, dry_run=dry_run,
                          skip_mirror=skip_mirror, target_disc=target_disc,
                          all_sea_target=all_sea_target)
        if not out["clean"]:
            bad = [g["gate"] for g in out["fuse_gates"] if not g["ok"]]
            raise ValueError(f"fuse layout refused: {', '.join(bad)}")
        return out

    runners = {"island": _island_runner, "coastnav": _coastnav_runner,
               "rim_retile": _rim_runner}

    steps = []                                               # (label, table, spec, runner)
    for tier in COMPOSE_TIERS:
        for table in tier:
            if table == "placement":
                if placements:
                    steps.append(("placement[]", table, {"count": len(placements)},
                                  _placement_runner))
                continue
            for i, row in enumerate(doc.get(table, ())):
                run = (runners[table] if table in runners
                       else (lambda row, table=table: _relief_runner(table, row)))
                steps.append((f"{table} #{i}", table, dict(row), run))

    # ---- run in order, attributing written files per step -------------------------------
    entries = []
    aborted = False
    for (label, table, spec, run) in steps:
        if aborted:
            gates.append({"gate": label, "ok": False,
                          "skipped": "an earlier step failed (later tiers read its deploys)"})
            continue
        try:
            run(spec)
            post = _world_tree_md5(mod_root) if not dry_run else pre
            changed = {p: h for p, h in post.items() if pre.get(p) != h}
            pre = post
            gates.append({"gate": label, "files": len(changed), "ok": True})
            entries.append({"table": label, "spec": spec, "files": changed})
        except (ValueError, FileNotFoundError) as e:
            gates.append({"gate": label, "ok": False, "error": str(e)})
            if not dry_run:
                aborted = True
    clean = all(g["ok"] for g in gates)
    if not dry_run and entries:
        from datetime import datetime, timezone
        doc_out = {"op": "compose",
                   "entries": list((old_manifest or {}).get("entries", ())) + [
                       {**e, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
                       for e in entries]}
        man_path.parent.mkdir(parents=True, exist_ok=True)
        man_path.write_text(json.dumps(doc_out, indent=1), encoding="utf-8")
    return {"op": "compose", "gates": gates, "clean": clean, "dry_run": dry_run,
            "manifest": str(man_path)}
