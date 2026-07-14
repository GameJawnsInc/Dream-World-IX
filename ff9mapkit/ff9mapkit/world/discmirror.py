"""Mirror a mod folder's WorldMap overrides across DISC TREES (``world-mirror``).

THE DISC-4 GAP (found in-game 2026-07-13, "the island no longer exists on disc 4"): the
overworld ships exactly TWO asset trees -- ``worldmap/disc1`` (used by discs 1-3) and
``worldmap/disc4`` (distinct art; only ``WorldDisc1``/``WorldDisc4`` prefabs exist) -- and
every s34 lookup (override files, ``Donor.txt`` sidecars, the reclaim fallback prefab) is
keyed on the engine's ``currentDisc``. A custom landmass deployed under ``Disc1/`` simply
does not exist once the scenario (or the F6 disc switch) crosses the disc-4 threshold.

``mirror(mod_folder)`` closes the gap:

* every deployed ``Block[x][y] *.ff9mesh`` + ``Donor.txt`` under the source tree copies
  byte-verbatim into the destination tree, gated per cell -- the destination's REAL cell
  must be open ocean (no real assets) or byte-identical to the source disc's (an
  ``--in-place`` edit of a real block that DIFFERS across discs must not be transplanted
  between them -- those cells skip with a warning);
* THE FREE-RIDE PIN: a sidecar cell's un-overridden donor-prefab parts (falls, rivers,
  objects -- the parts that ride the prefab verbatim) would load the DESTINATION disc's
  variants, which can differ from the source disc's (the Daguerreo donors do). Every such
  extra part is pinned as an EXPLICIT override carrying the SOURCE disc's bytes, so the
  mirrored cell renders identically on both trees.
"""
from __future__ import annotations

import dataclasses
import re
from collections import defaultdict
from pathlib import Path

from . import extract as X
from . import mesh as M

_BLOCK_RE = re.compile(r"^Block\[(\d+)\]\[(\d+)\] (.+?)\.(ff9mesh|txt)$")


def _real_parts(disc: int, game=None) -> dict:
    """{(bx, by): {part, ...}} of the REAL map's per-block mesh assets on ``disc``."""
    env = X._worldmap_env(disc, game=game)
    pat = re.compile(rf"worldmap/disc{disc}/0_1/r\d+/block\[(\d+)\]\[(\d+)\] ([a-z0-9]+)(?:\.asset)?$")
    parts = defaultdict(set)
    for k in env.container:
        m = pat.search((k or "").lower())
        if m:
            parts[(int(m.group(1)), int(m.group(2)))].add(m.group(3))
    return parts


def _parts_identical(blk, part: str, src_disc: int, dst_disc: int, game=None) -> bool:
    a = X.read_block(blk[0], blk[1], disc=src_disc, part=part, game=game)
    b = X.read_block(blk[0], blk[1], disc=dst_disc, part=part, game=game)
    return (a.vcount == b.vcount and a.verts == b.verts and a.flat_index == b.flat_index
            and a.uvs == b.uvs and a.tangents == b.tangents and a.normals == b.normals)


def mirror(mod_folder: str, *, src_disc: int = 1, dst_disc: int = 4, lod: str = "0_1",
           game=None, dry_run: bool = False, log=print) -> dict:
    """Mirror ``mod_folder``'s ``Disc{src}`` WorldMap overrides into ``Disc{dst}``.
    Returns ``{"mirrored": [paths], "pinned": [paths], "skipped": [(cell, why)]}``."""
    from .. import config
    gp = Path(config.find_game_path(game))
    src_root = gp / mod_folder / "FF9_Data" / "WorldMap" / f"Disc{src_disc}" / lod
    dst_root = gp / mod_folder / "FF9_Data" / "WorldMap" / f"Disc{dst_disc}" / lod
    if not src_root.is_dir():
        raise ValueError(f"no Disc{src_disc} WorldMap overrides in {mod_folder}")

    # inventory the deployed cells + their overridden parts
    cells = defaultdict(dict)                               # (bx,by) -> {filename: Path}
    for p in sorted(src_root.rglob("Block[[]*")):
        m = _BLOCK_RE.match(p.name)
        if m:
            cells[(int(m.group(1)), int(m.group(2)))][p.name] = p
    if not cells:
        raise ValueError(f"no deployed Block overrides under {src_root}")

    real_src = _real_parts(src_disc, game=game)
    real_dst = _real_parts(dst_disc, game=game)

    out = {"mirrored": [], "pinned": [], "skipped": []}
    for blk in sorted(cells):
        files = cells[blk]
        # ---- the per-cell gate ----------------------------------------------------------
        dst_real = real_dst.get(blk, set())
        if dst_real:
            src_real = real_src.get(blk, set())
            if src_real != dst_real:
                out["skipped"].append((blk, f"real cell part sets differ across discs "
                                            f"({sorted(src_real)} vs {sorted(dst_real)})"))
                log(f"  SKIP {blk}: real part sets differ across discs")
                continue
            diff = [pt for pt in sorted(dst_real)
                    if not _parts_identical(blk, pt, src_disc, dst_disc, game=game)]
            if diff:
                out["skipped"].append((blk, f"real cell differs across discs in {diff}"))
                log(f"  SKIP {blk}: real cell differs across discs in {diff}")
                continue
        # ---- copy the deployed files ----------------------------------------------------
        for name, p in sorted(files.items()):
            dst = dst_root / f"r{blk[1]}" / name
            if not dry_run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(p.read_bytes())
            out["mirrored"].append(dst)
        # ---- THE FREE-RIDE PIN ----------------------------------------------------------
        sidecar = files.get(f"Block[{blk[0]}][{blk[1]}] Donor.txt")
        if sidecar is None:
            continue
        try:
            dx, dy = (int(v) for v in sidecar.read_text().strip().split(","))
        except ValueError:
            out["skipped"].append((blk, "bad Donor.txt"))
            continue
        overridden = {_BLOCK_RE.match(n).group(3).lower() for n in files
                      if n.endswith(".ff9mesh")}
        extras = sorted(real_src.get((dx, dy), set()) - overridden)
        for part in extras:
            bm = X.read_block(dx, dy, disc=src_disc, part=part, game=game)
            part_name = bm.name.split("] ", 1)[1]           # exact case, e.g. "RiverJoint"
            pinned = dataclasses.replace(
                bm, disc=dst_disc, x=blk[0], y=blk[1],
                name=f"Block[{blk[0]}][{blk[1]}] {part_name}")
            dst = dst_root / f"r{blk[1]}" / f"{pinned.name}.ff9mesh"
            if not dry_run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                M.write_ff9mesh(pinned, dst)
            out["pinned"].append(dst)
            log(f"  PIN {blk} <- donor ({dx},{dy}) {part_name} "
                f"({len(bm.tris)} tris, source-disc bytes)")
    log(f"mirrored {len(out['mirrored'])} file(s), pinned {len(out['pinned'])} free-ride "
        f"part(s), skipped {len(out['skipped'])} cell(s) -> Disc{dst_disc}")
    return out
