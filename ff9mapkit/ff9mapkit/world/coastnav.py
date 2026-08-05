"""THE COAST NAVIGATION STAMP -- vehicle legality classes on a synthetic coast.

Productized from ``studies/overworld-topography/southern-ring/stamp_coast_nav.py`` (Southern Ring
R5d ``9520b0a3`` THE SAIL-THROUGH SEAL + R5e ``3aef6cab`` THE STANDOFF BELT, owner-confirmed in
game ``105c39a8``). It lived as a one-off study script for five days and was re-derived from
scratch in the meantime, which is why it is a kit module now.

THE PROBLEM. A synthetic landmass ships a full-cell ocean plane under its land. The engine's
movement gate ``w_movementRoundCheck`` (``ff9.cs:5682``) raycasts the next position via
``w_cellHit`` **using the actor's triangle cache**, then bit-tests the hit triangle's topograph
against the vehicle's mask. Sailing, that cache is full of water triangles, so at an under-land
position the probe hits the ocean underneath the terrain (topo 57, in the Narciss mask) and the
move is LEGAL -- the hull crosses the cliff. Stock never has water under land.

THE FIX is navigation-only: re-derive every water triangle's topograph class in every deployed sea
override. **Topograph bits only** (IDALL mask ``0xFC`` in ``tangent.x``) -- geometry, UV, material,
event, area and flags are byte-preserved, so nothing about the look changes.

    class            topo   rule
    KEEL-BLOCK        56    any of centroid+3 corners under HIGH-LOCALE ground   (the seal)
    STANDOFF BELT     55    open water within BELT_R of a HIGH-locale front      (the padding)
    CLIFF-FRONT       54    open water fronting HIGH ground, beyond the belt     (policy)
    BEACH-FRONT       53    other water within FRINGE_R of ground                (landable)
    open sea          57    unchanged

The Narciss-class legality mask is exactly ``{53, 54, 57}`` (``limit0`` 0x02600000). 55 and 56 are
water-class but outside it, so the hull is refused while every triangle still exists and renders.
**53 is additionally the class the get-off gate demands** -- a coast with no 53 can be sailed to and
not landed on.

RELATION TO THE SEA4 CUT (``island._cut_plane``'s ``under``). For the SEAL the two are SUBSTITUTES,
not complements: two exits from the same gate. The cut exits via "no hit at all, mask never
consulted"; the stamp exits via "hit succeeded, topo not in mask". The cut is stronger where it
applies -- a miss short-circuits before any mask test, so it walls off EVERY vehicle, whereas topo
55 is legal for the Light Blue and Red Chocobos. The cut has no belt and no landability, which is
what this module adds. Running both is intended: the keel rule is an OR over centroid+3 corners
while the cut's test is an AND over 3 corners, so the stamp also closes the straddling-triangle
leak the conservative cut leaves behind.

⚠ THE ORIGIN CONVENTION (the instrument bug that cost the Southern Ring three rounds):
``block_world_origin`` returns the cell's WEST,NORTH corner and a cell spans z **downward**, from
``oz`` to ``oz - 64``. Scanning ``oz .. oz + 64`` reads the NEIGHBOUR ROW, and a seal measured that
way passed its own probe with zero leaks and still failed the owner's playtest.
"""
from __future__ import annotations

import math
import re
import shutil
import struct
import time
from pathlib import Path

from .. import config

BLOCK = 64.0
WORLD_W = 1536.0
WATER = {53, 54, 55, 56, 57}
SEA_PARTS = ("Sea1", "Sea2", "Sea3", "Sea4", "Sea5")
# the loader scans placement.REGISTRATION_ORDER (audit rec 11) -- the local PARTS_ORDER copy it
# replaced had drifted (Sea5 before Sea4, no Beach2/Stream/River/RiverJoint/Falls at all).

KEEL, BEACH, BELT, CLIFF = 56, 53, 55, 54

HIGH_Y = 1.5            #: a single ground sample at/above this is high...
LOCALE_R = 3.0          #: ...but a sample's CLASS is its LOCALE: low only if no ground within
LOCALE_HIGH_Y = 2.0     #: LOCALE_R rises to LOCALE_HIGH_Y. A cliff-BASE vertex sits at the
                        #: waterline (y < 1.5) and is emphatically not a beach.
STEP_G = 2.0            #: the ground scan's step -- must be finer than LOCALE_R or a sample has
                        #: no neighbours to be classified against.
FRINGE_R = 16.0         #: how far from ground the near-shore classes reach
BELT_R = 3.5            #: THE STANDOFF BELT width. In-game proven at 3.5. The study derives a
                        #: 4.375u ceiling from the get-off sweep (Narciss radius 560, ff9.S=/256);
                        #: that derivation is disputed (the sweep is a conjunction over eight radii
                        #: probed on-foot), but the VALUE is playtest-confirmed either way.

#: Shared-vertex resolution. A triangle's class is read from its FIRST vertex's tangent.x, so a
#: vertex shared across a class boundary decides whole triangles. KEEL first -- beach-claimed verts
#: once left 23 first-vert holes in the seal. BEACH above CLIFF and BELT: the get-off gate reads the
#: tile under the hull, so erring landable at a seam preserves a landing, and losing the last
#: half-triangle of standoff costs nothing.
PRIORITY = {KEEL: 0, BEACH: 1, CLIFF: 2, BELT: 3}

#: Landability policies. ``land-anywhere`` is the Southern Ring's owner-confirmed property (every
#: near-shore triangle is landable 53). ``cliffs-refuse`` restores the stock grammar the R5d survey
#: measured -- "topo 53 fronts BEACHES ONLY; cliff-front water is 54/55/56/57" -- so a cliff-ringed
#: island can be sailed to but not disembarked on, and needs a genuine low shore to be a
#: destination.
POLICIES = ("land-anywhere", "cliffs-refuse")


def _worldmap_root(mod_folder: str, game=None) -> Path:
    return config.find_game_path(game) / mod_folder / "FF9_Data" / "WorldMap"


def _part_path(root: Path, disc: int, bx: int, by: int, part: str) -> Path:
    return root / f"Disc{disc}" / "0_1" / f"r{by}" / f"Block[{bx}][{by}] {part}.ff9mesh"


def deployed_sea_cells(mod_folder: str, disc: int, game=None):
    """Every cell with at least one deployed Sea1..Sea5 override in this disc's namespace."""
    root = _worldmap_root(mod_folder, game) / f"Disc{disc}" / "0_1"
    cells = set()
    if not root.is_dir():
        return []
    for p in root.rglob("*.ff9mesh"):
        m = re.match(r"Block\[(\d+)\]\[(\d+)\] (Sea[1-5])\.ff9mesh$", p.name)
        if m:
            cells.add((int(m.group(1)), int(m.group(2))))
    return sorted(cells)


# the spatial index was promoted to placement.build_index (2026-08-04, audit rec 2) so a
# calibration fix lands ONCE; these aliases keep every call site and the measured semantics
# (the un-indexed pass was the ~hour-per-pass cost measured on 2026-07-30).
from .placement import INDEX_GRID as _GRID               # noqa: E402
from .placement import build_index as _build_grid        # noqa: E402
from .placement import REGISTRATION_ORDER                # noqa: E402  (audit rec 11: one order)


class _Loader:
    """Stacked block-part reader, cached. Reads this disc's deployed override, falling back to the
    stock tree when the disc is a real one (a synthetic namespace has no stock tree, so only what we
    deployed exists -- which is correct)."""

    def __init__(self, mod_folder, disc, game=None):
        self.mod_folder, self.disc, self.game, self._c = mod_folder, disc, game, {}

    def parts(self, bx, by):
        key = (bx, by)
        if key not in self._c:
            out = []
            if self.disc in (1, 4):
                from .entrance import read_block_stacked
                for part in REGISTRATION_ORDER:
                    try:
                        bm = read_block_stacked(self.mod_folder, bx, by, disc=self.disc,
                                                part=part.lower(), game=self.game, missing_ok=True)
                    except (ValueError, FileNotFoundError):
                        bm = None
                    if bm is not None and bm.tris:
                        out.append((part, bm, _build_grid(bm)))
            else:
                # a SYNTHETIC namespace: only deployed overrides exist -- read them directly and
                # never consult the stock fallback. The stacked read's fallback rescans every
                # p0data bundle per missing part on a disc no bundle serves (928 UnityPy loads for
                # ONE cell, 97% of a stamp's profiled runtime).
                from . import mesh as M
                root = _worldmap_root(self.mod_folder, self.game)
                for part in REGISTRATION_ORDER:
                    p = _part_path(root, self.disc, bx, by, part)
                    if p.is_file():
                        bm = M.blockmesh_from_ff9mesh(p, disc=self.disc, x=bx, y=by,
                                                      part=part.lower())
                        if bm.tris:
                            out.append((part, bm, _build_grid(bm)))
            self._c[key] = out
        return self._c[key]


def _query_top(loader, wx, wz, parts=None):
    """First part in registration order covering ``(wx, wz)`` -> ``(part, topo, y)`` or None.

    Matches the engine's own ground query on the two filters that decide whether a triangle is
    ground at all (:mod:`ff9mapkit.world.placement` rules 4): the IDALL skip set, and UP-FACING by
    the GEOMETRIC winding normal. The study script this was ported from omitted both, which let a
    downward-facing sub-sea skirt register as "ground" -- on the Path D cliff island that surfaced
    as one or two phantom samples at y=-80 per cell, and because they classified LOW they painted
    228 verts of landable 53 onto a coast that has no shore at all.

    ``parts`` optionally restricts the query to a set/tuple of part names (e.g. the seas only --
    what the boat's cache-favoured ``w_cellHit`` effectively reads under land); None = the full
    stack."""
    from . import extract as W
    from .frames import wrap_world_xz
    from .placement import IDALL_SKIP
    # the one toroidal fold (audit rec 12) -- this site used to wrap X only, so an
    # off-window z silently addressed a nonexistent row instead of the wrapped block
    wx, wz = wrap_world_xz(wx, wz)
    bx, by = math.floor(wx / BLOCK), math.floor(-wz / BLOCK)
    ox, oz = W.block_world_origin(bx, by)
    for nm, bm, grid in loader.parts(bx, by):
        if parts is not None and nm not in parts:
            continue
        cands = grid.get((math.floor((wx - ox) / _GRID), math.floor((wz - oz) / _GRID)))
        if not cands:
            continue
        for t in cands:
            tri = bm.tris[t]
            if int(round(bm.tangents[tri[0]][0])) in IDALL_SKIP:
                continue
            a, b, c = [(bm.verts[k][0] + ox, bm.verts[k][1], bm.verts[k][2] + oz) for k in tri]
            # cheap rejector first (most triangles fail the point test); the facing test only
            # decides among triangles that actually cover the point, so order is a pure speedup.
            d = (b[0] - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (b[2] - a[2])
            if abs(d) < 1e-12:
                continue
            w1 = ((wx - a[0]) * (c[2] - a[2]) - (c[0] - a[0]) * (wz - a[2])) / d
            w2 = ((b[0] - a[0]) * (wz - a[2]) - (wx - a[0]) * (b[2] - a[2])) / d
            if w1 < -1e-9 or w2 < -1e-9 or w1 + w2 > 1 + 1e-9:
                continue
            ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
            ny = uz * vx - ux * vz
            if ny <= 0.0:                              # not up-facing -> the engine never grounds here
                continue
            L2 = (uy * vz - uz * vy) ** 2 + ny * ny + (ux * vy - uy * vx) ** 2
            if ny * ny <= 0.01 * L2:                   # ny/|n| <= 0.1, without the sqrt
                continue
            y = a[1] + w1 * (b[1] - a[1]) + w2 * (c[1] - a[1])
            topo = W.decode_id(int(round(bm.tangents[tri[0]][0])))["topograph"]
            return (nm, topo, y)
    return None


def _cell_grounds(loader, bx, by):
    """Ground samples over the cell plus an 18u margin, split into LOW and HIGH by LOCALE."""
    from . import extract as W
    ox, oz = W.block_world_origin(bx, by)
    raw = []
    x = ox - 18.0
    while x <= ox + BLOCK + 18.0:
        z = oz + 18.0
        while z >= oz - BLOCK - 18.0:                 # ⚠ DOWNWARD -- see the origin convention
            g = _query_top(loader, x, z)
            if g is not None and g[1] not in WATER:
                raw.append((x % WORLD_W, z, g[2]))
            z -= STEP_G
        x += STEP_G
    lows, highs = [], []
    for gx, gz, gy in raw:
        near_hi = any(abs(gx - px) <= LOCALE_R and abs(gz - pz) <= LOCALE_R
                      and math.hypot(gx - px, gz - pz) <= LOCALE_R and py >= LOCALE_HIGH_Y
                      for px, pz, py in raw)
        (highs if near_hi else lows).append((gx, gz))
    return lows, highs


def _tri_dist2d(px, pz, a, b, c):
    """Exact 2D point-to-triangle distance (0 inside). Corner/centroid probing misses a mid-EDGE
    approach to a wall, which reads sailable."""
    d = (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])
    if abs(d) > 1e-12:
        w1 = ((px - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (pz - a[1])) / d
        w2 = ((b[0] - a[0]) * (pz - a[1]) - (px - a[0]) * (b[1] - a[1])) / d
        if w1 >= 0 and w2 >= 0 and w1 + w2 <= 1:
            return 0.0
    best = float("inf")
    for p, q in ((a, b), (b, c), (c, a)):
        vx, vz = q[0] - p[0], q[1] - p[1]
        L2 = vx * vx + vz * vz
        t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((px - p[0]) * vx + (pz - p[1]) * vz) / L2))
        best = min(best, math.hypot(px - (p[0] + t * vx), pz - (p[1] + t * vz)))
    return best


def _locale_of(px, pz, lows, highs):
    """LOCALE of the ground nearest a probe point: True=high / False=low / None if none near."""
    px %= WORLD_W
    best_d, best_cls = 7.0, None
    for cls, pts in ((True, highs), (False, lows)):
        for gx, gz in pts:
            if abs(px - gx) >= best_d or abs(pz - gz) >= best_d:
                continue
            d = math.hypot(px - gx, pz - gz)
            if d < best_d:
                best_d, best_cls = d, cls
    return best_cls


def _parse_header(data):
    from .mesh import read_ff9mesh_header             # THE one header parser (audit rec 10)
    version, vcount, icount, flags = read_ff9mesh_header(data)
    off = 20 + vcount * 12
    if flags & 1:
        off += vcount * 12
    if flags & 2:
        off += vcount * 8
    assert flags & 4, "sea override without tangents?!"
    return vcount, icount, off, off + vcount * 16


def stamp(mod_folder: str, *, disc: int = 1, cells=None, policy: str = "land-anywhere",
          deploy: bool = False, game=None, backup_dir: Path | None = None,
          mirror_disc: int | None = None, backup: bool = True) -> dict:
    """Stamp navigation classes onto every deployed sea override in ``disc``'s namespace.

    ``cells`` restricts to an iterable of ``(bx, by)``; default is every cell with a sea override.
    ``policy`` is one of :data:`POLICIES`. ``mirror_disc`` writes an identical copy to that disc too
    (the real-disc Disc1/Disc4 parity pair); leave None for a synthetic namespace.
    ``backup=False`` skips the pre-write file backups -- for an EMITTER calling this over sea files
    it deployed moments earlier in the same run, where the pre-stamp state is the emitter's own
    output and re-running the emitter reproduces it. Keep the default for standalone stamping.
    Read-only unless ``deploy``."""
    if policy not in POLICIES:
        raise ValueError(f"policy must be one of {POLICIES}, got {policy!r}")
    root = _worldmap_root(mod_folder, game)
    loader = _Loader(mod_folder, disc, game)
    todo = sorted(cells) if cells is not None else deployed_sea_cells(mod_folder, disc, game)
    if backup_dir is None:
        # the repo's own backups/ (this file is <repo>/ff9mapkit/ff9mapkit/world/coastnav.py);
        # falls back to CWD when the kit is installed rather than run from a checkout.
        repo = Path(__file__).resolve().parents[3]
        base = repo if (repo / ".git").exists() or (repo / "ff9mapkit").is_dir() else Path.cwd()
        backup_dir = base / "backups" / f"coastnav-disc{disc}-{time.strftime('%Y%m%d-%H%M%S')}"
    summary = {"disc": disc, "policy": policy, "deploy": deploy, "cells": [], "totals": {},
               "backup_dir": str(backup_dir) if (deploy and backup) else None}
    from . import extract as W
    for bx, by in todo:
        lows = highs = None
        cell_out = []
        for part in SEA_PARTS:
            p = _part_path(root, disc, bx, by, part)
            if not p.is_file():
                continue
            data = bytearray(p.read_bytes())
            pm = _part_path(root, mirror_disc, bx, by, part) if mirror_disc is not None else None
            if pm is not None and pm.is_file():
                assert pm.read_bytes() == bytes(data), \
                    f"disc parity ALREADY broken for {p.name} -- refusing to stamp"
            vcount, icount, tan_off, idx_off = _parse_header(bytes(data))
            if icount == 0:
                continue
            if lows is None:
                lows, highs = _cell_grounds(loader, bx, by)
            verts = [struct.unpack_from("<3f", data, 20 + i * 12) for i in range(vcount)]
            idx = struct.unpack_from(f"<{icount}i", data, idx_off)
            ox, oz = W.block_world_origin(bx, by)

            def topo_of(vi):
                return (int(round(struct.unpack_from("<f", data, tan_off + vi * 16)[0])) & 0xFC) >> 2

            want = {}
            for t in range(icount // 3):
                tri = idx[t * 3:t * 3 + 3]
                if any(topo_of(vi) not in WATER for vi in tri):
                    continue
                cx = sum(verts[vi][0] for vi in tri) / 3 + ox
                cz = sum(verts[vi][2] for vi in tri) / 3 + oz
                # centroid AND all three corners: a big straddling tri whose centroid sits over
                # open water can still reach under the cliff. ANY probe under high-locale ground
                # keels the whole triangle.
                probes = [(cx, cz)] + [(verts[vi][0] + ox, verts[vi][2] + oz) for vi in tri]
                tops = [_query_top(loader, px, pz) for px, pz in probes]
                grounded = [(px, pz, g) for (px, pz), g in zip(probes, tops)
                            if g is not None and g[1] not in WATER]
                if grounded:
                    def is_high(px, pz, g):
                        # raw height OR locale: raw alone misses a thin wall trim at the waterline,
                        # locale alone misses a mid-height bank between the two thresholds.
                        return True if g[2] >= HIGH_Y else bool(_locale_of(px, pz, lows, highs))
                    cls = KEEL if any(is_high(*gr) for gr in grounded) else BEACH
                else:
                    ta, tb, tc = [((verts[vi][0] + ox) % WORLD_W, verts[vi][2] + oz) for vi in tri]
                    cxm = cx % WORLD_W
                    reach = BELT_R + max(math.hypot(cxm - p[0], cz - p[1]) for p in (ta, tb, tc))
                    hug = any(math.hypot(cxm - gx, cz - gz) <= reach
                              and _tri_dist2d(gx, gz, ta, tb, tc) <= BELT_R for gx, gz in highs)
                    near_low = any(math.hypot(cxm - gx, cz - gz) <= FRINGE_R for gx, gz in lows)
                    near_high = any(math.hypot(cxm - gx, cz - gz) <= FRINGE_R for gx, gz in highs)
                    if hug:
                        cls = BELT
                    elif policy == "cliffs-refuse" and near_high and not near_low:
                        # the stock grammar R5d measured: 53 fronts BEACHES ONLY, never cliffs.
                        # Boat-legal (54 is in the mask) so you can sail up to it, but the get-off
                        # gate demands 53, so a cliff-ringed island cannot be disembarked on.
                        cls = CLIFF
                    elif near_low or near_high:
                        cls = BEACH
                    else:
                        continue
                for vi in tri:
                    if vi not in want or PRIORITY[cls] < PRIORITY[want[vi]]:
                        want[vi] = cls
            changed = {vi: cls for vi, cls in want.items() if topo_of(vi) != cls}
            if not changed:
                continue
            if deploy:
                if backup:
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    for src, tag in ((p, f"disc{disc}"), (pm, f"disc{mirror_disc}")):
                        if src is not None and src.is_file():
                            bk = backup_dir / f"{src.name}.{tag}"
                            if not bk.exists():
                                shutil.copy2(src, bk)
                for vi, cls in changed.items():
                    o = tan_off + vi * 16
                    old = int(round(struct.unpack_from("<f", data, o)[0]))
                    struct.pack_into("<f", data, o, float((old & ~0xFC) | (cls << 2)))
                p.write_bytes(bytes(data))
                # the stamp is a legitimate in-place rewrite of a DEPLOYED override -- ledger
                # it, or the next deploy_override at this cell+part refuses our own bytes as
                # foreign (the rec-16 compose smoke's live find)
                from . import mesh as M
                M.record_ledger_write(p, cell=(bx, by), part=part, write_disc=disc)
                if pm is not None and pm.is_file():
                    pm.write_bytes(bytes(data))
                    M.record_ledger_write(pm, cell=(bx, by), part=part,
                                          write_disc=mirror_disc)
            by_cls = {}
            for cls in changed.values():
                by_cls[cls] = by_cls.get(cls, 0) + 1
                summary["totals"][cls] = summary["totals"].get(cls, 0) + 1
            cell_out.append({"part": part, "verts": len(changed), "classes": by_cls})
        if cell_out:
            summary["cells"].append({"block": [bx, by], "parts": cell_out})
    return summary
