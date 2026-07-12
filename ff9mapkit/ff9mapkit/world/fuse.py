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

from .. import config
from . import transplant as TR
from .transplant import OPEN_WATER_PARTS


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


def _existing_overrides(cells, mod_folder: str, *, disc: int, lod: str, game=None) -> list:
    """Override files already deployed at any of ``cells`` (block ``(x, y)`` tuples)."""
    game_path = config.find_game_path(game)
    hits = []
    for (x, y) in cells:
        d = game_path / mod_folder / "FF9_Data" / "WorldMap" / f"Disc{disc}" / lod / f"r{y}"
        if not d.is_dir():
            continue
        prefix = f"Block[{x}][{y}] "
        hits.extend(str(p) for p in sorted(d.iterdir()) if p.name.startswith(prefix))
    return hits


def fuse_layout(mod_folder: str, placements, *, disc: int = 1, lod: str = "0_1", game=None,
                allow_overwrite: bool = False, dry_run: bool = False) -> dict:
    """Validate + deploy a multi-placement LAYOUT. Each placement is a dict of
    :func:`ff9mapkit.world.transplant.transplant_region` kwargs (``cell``, ``donor``,
    ``size``; optional ``rot``, ``shift``, ``tweaks``, ``strips``, ``land_margin``,
    ``extra``, ``census_samples``). Every placement must gate clean on its own; target
    rects must not overlap; every shared border must certify per the fuse law (each 4u
    row: prefab or pure on-lattice open water on BOTH sides); target cells must not
    collide with overrides already on disk (unless ``allow_overwrite`` -- re-deploying
    the same layout is the normal iteration flow). ``dry_run`` stops after validation.

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
    summaries = []
    for pl in placements:
        summaries.append(TR.transplant_region("UNUSED", disc=disc, lod=lod, game=game,
                                              dry_run=True, **_kw(pl)))
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
            if sa not in ("prefab", "water") or sb not in ("prefab", "water"):
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
    existing = _existing_overrides(tcells, mod_folder, disc=disc, lod=lod, game=game) \
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
                                 dry_run=False, **_kw(pl))
        out["deployed"].extend(s["deployed"])
    return out
