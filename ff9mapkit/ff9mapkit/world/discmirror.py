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

:func:`auto_mirror` is the AUTO-RUN post-step every world-deploy writer calls after itself (island/
transplant/fuse/terrain/interior/water/entrance/mesh-build) so this can no longer be a forgotten manual
step -- ``skip_mirror=True`` (CLI ``--skip-mirror``) is the escape hatch; :func:`mirror` itself (and the
standalone ``world-mirror`` verb) is unchanged.

**THE EVIDENCE CONTRACT (2026-07-19 hardening):** :func:`auto_mirror` takes ``written`` -- the actual
return values of THIS invocation's real deploy calls (:func:`~ff9mapkit.world.mesh.deploy_override` /
:func:`~ff9mapkit.world.mesh.deploy_donor_sidecar` both return the written ``Path`` -- that is the
contract every writer relies on). It derives EVERYTHING it needs (the game root, the source disc, the
lod, the cell set to restrict the mirror to) by parsing those paths -- it never calls
:func:`ff9mapkit.config.find_game_path` itself and never globs a tree it wasn't literally handed evidence
of. Two defects this closes:

* **hermeticity (P1):** the old ``auto_mirror(mod_folder, *, disc, game=None, ...)`` re-resolved the REAL
  game install on its own, so a test that mocks only the deploy calls (not ``config.find_game_path``)
  could still trigger a genuine mirror pass against the developer's live install. A ``MagicMock`` return
  value fails ``isinstance(p, (str, Path))`` and is silently dropped -- nothing survives, nothing runs.
* **blast radius (P2):** :func:`mirror` itself re-syncs the WHOLE source-disc tree by default (the
  standalone ``world-mirror`` verb's job). Every writer now hands :func:`auto_mirror` only the CELLS it
  actually just wrote, and :func:`auto_mirror` passes that set through as :func:`mirror`'s ``cells``
  filter -- so an unrelated write to cell B can never re-mirror (and silently clobber a hand-diverged
  Disc4 variant of) cell A. The standalone verb still calls :func:`mirror` directly with ``cells=None``
  (mirror everything) -- that whole-tree behavior is unchanged.
"""
from __future__ import annotations

import dataclasses
import re
from collections import defaultdict
from pathlib import Path

from . import extract as X
from . import mesh as M

_BLOCK_RE = re.compile(r"^Block\[(\d+)\]\[(\d+)\] (.+?)\.(ff9mesh|txt)$")
_DISC_SEG_RE = re.compile(r"^Disc(\d+)$")


def _real_parts(disc: int, lod: str = "0_1", *, game=None) -> dict:
    """{(bx, by): {part, ...}} of the REAL map's per-block mesh assets on ``disc`` at ``lod``."""
    env = X._worldmap_env(disc, game=game)
    pat = re.compile(rf"worldmap/disc{disc}/{re.escape(lod.lower())}/r\d+/block\[(\d+)\]\[(\d+)\] ([a-z0-9]+)(?:\.asset)?$")
    parts = defaultdict(set)
    for k in env.container:
        m = pat.search((k or "").lower())
        if m:
            parts[(int(m.group(1)), int(m.group(2)))].add(m.group(3))
    return parts


def _parts_identical(blk, part: str, src_disc: int, dst_disc: int, lod: str = "0_1", *, game=None) -> bool:
    a = X.read_block(blk[0], blk[1], disc=src_disc, lod=lod, part=part, game=game)
    b = X.read_block(blk[0], blk[1], disc=dst_disc, lod=lod, part=part, game=game)
    return (a.vcount == b.vcount and a.verts == b.verts and a.flat_index == b.flat_index
            and a.uvs == b.uvs and a.tangents == b.tangents and a.normals == b.normals)


def _cell_of(path: Path):
    """``(bx, by)`` parsed from a deployed override's OWN filename (``Block[x][y] <Part>.ff9mesh`` or the
    ``Block[x][y] Donor.txt`` sidecar -- :data:`_BLOCK_RE` matches both extensions). ``None`` if the
    filename doesn't match (defensive -- every real writer path does)."""
    m = _BLOCK_RE.match(path.name)
    return (int(m.group(1)), int(m.group(2))) if m else None


def auto_mirror(written, *, mod_folder: str, skip_mirror: bool = False, dst_disc: int = 4, log=print):
    """Automatic POST-STEP for every world-deploy writer: pass it ``written`` -- the list/iterable of
    return values of THIS call's own real :func:`~ff9mapkit.world.mesh.deploy_override` /
    :func:`~ff9mapkit.world.mesh.deploy_donor_sidecar` calls -- right after a verb finishes writing, to
    close THE DISC-4 GAP (module docstring) without the operator having to remember a separate
    ``world-mirror`` run.

    Never touches ``config.find_game_path`` or the filesystem itself except through :func:`mirror` (and
    even then, only once real evidence of a write survives filtering) -- see the module docstring's
    EVIDENCE CONTRACT. In order:

    1. ``skip_mirror=True`` (CLI ``--skip-mirror``) opts out explicitly -- logs one line, does nothing.
    2. Every entry of ``written`` that is not a real, existing ``str``/``Path`` under a ``WorldMap/Disc{n}``
       tree (``n != dst_disc``) is dropped. A ``MagicMock`` (a hermetic test that mocked the deploy calls
       out) fails the ``isinstance`` check -- if NOTHING survives (a dry run, a mocked writer, or a writer
       that deployed straight to ``dst_disc`` already), this is a silent no-op.
    3. The game root, source disc, lod, and cell set are derived purely by parsing the surviving paths
       (the ``Disc{n}`` segment + the segment after it + each filename's ``Block[x][y]``) -- grouped per
       source disc (a single writer call touches one disc in practice; a mixed set is handled by looping).
    4. :func:`mirror` runs once per source-disc group, scoped to exactly that group's cells via its
       ``cells=`` filter -- an unrelated write elsewhere in the tree is never touched. A ``ValueError`` out
       of :func:`mirror` itself (e.g. the derived game root has no real StreamingAssets bundle data to
       compare cells against -- a hermetic caller exercising just the writer, not a real install) is
       swallowed per group: this is a best-effort POST-step, not a new hard requirement on every deploy call.

    Returns the last :func:`mirror` summary dict, or ``None`` when it never ran. The standalone
    ``world-mirror`` verb (a direct :func:`mirror` call, ``cells=None``) is unaffected either way."""
    if skip_mirror:
        log(f"disc-{dst_disc} mirror: skipped (--skip-mirror)")
        return None

    hits = []                                                # (path, disc_idx, src_disc)
    for p in written:
        if not isinstance(p, (str, Path)):
            continue                                         # a MagicMock (mocked deploy call) -- no evidence
        try:
            pp = Path(p)
            exists = pp.exists()
        except (OSError, TypeError):
            continue
        if not exists:
            continue
        parts = pp.parts
        if "WorldMap" not in parts:
            continue
        disc_idx = disc_n = None
        for i, seg in enumerate(parts):
            m = _DISC_SEG_RE.match(seg)
            if m:
                disc_idx, disc_n = i, int(m.group(1))
                break
        if disc_n is None or disc_n == dst_disc:
            continue                                         # not under a Disc{n} segment, or already dst_disc
        hits.append((pp, disc_idx, disc_n))
    if not hits:
        return None                                          # nothing survived -- see EVIDENCE CONTRACT above

    # ---- derive the game root (must agree across every surviving path -- there is only one install) ----
    game_root = None
    for pp, _disc_idx, _src_disc in hits:
        parts = pp.parts
        if mod_folder not in parts:
            continue
        root = Path(*parts[:parts.index(mod_folder)])
        if game_root is None:
            game_root = root
        elif root != game_root:
            raise ValueError(f"auto_mirror: written paths disagree on the game root ({game_root} vs "
                             f"{root}) -- refusing to guess which is right")
    if game_root is None:
        return None                                          # no surviving path actually carries mod_folder

    # ---- group per source disc: lod (the segment right after Disc{n}) + the cell set actually written ----
    by_disc = defaultdict(lambda: {"lod": None, "cells": set()})
    for pp, disc_idx, src_disc in hits:
        cell = _cell_of(pp)
        if cell is None:
            continue
        grp = by_disc[src_disc]
        parts = pp.parts
        if grp["lod"] is None and disc_idx + 1 < len(parts):
            grp["lod"] = parts[disc_idx + 1]
        grp["cells"].add(cell)

    out = None
    for src_disc, grp in sorted(by_disc.items()):
        if not grp["cells"]:
            continue
        try:
            out = mirror(mod_folder, src_disc=src_disc, dst_disc=dst_disc, lod=grp["lod"] or "0_1",
                         game=game_root, cells=grp["cells"], log=log)
        except ValueError as e:               # defensive -- mirror() re-validates the same tree (e.g. the
            log(f"disc-{dst_disc} mirror: skipped ({e})")  # derived game_root has no real StreamingAssets
            continue                                       # bundle data -- a best-effort post-step, not a new
                                                           # hard requirement on every deploy call
    return out


def mirror(mod_folder: str, *, src_disc: int = 1, dst_disc: int = 4, lod: str = "0_1",
           game=None, dry_run: bool = False, cells: set | None = None, log=print) -> dict:
    """Mirror ``mod_folder``'s ``Disc{src}`` WorldMap overrides into ``Disc{dst}``. ``cells`` (a
    ``{(x, y), ...}`` set, default ``None``) restricts the mirror to exactly those cells -- the scoping
    :func:`auto_mirror` uses so a write to one cell can never re-mirror (and potentially clobber a
    hand-diverged Disc4 variant of) an unrelated cell elsewhere in the same tree. ``None`` mirrors every
    deployed cell under the source tree -- the standalone ``world-mirror`` CLI verb's always-runs,
    whole-tree behavior, unchanged.
    Returns ``{"mirrored": [paths], "pinned": [paths], "skipped": [(cell, why)]}``."""
    from .. import config
    gp = Path(config.find_game_path(game))
    src_root = gp / mod_folder / "FF9_Data" / "WorldMap" / f"Disc{src_disc}" / lod
    dst_root = gp / mod_folder / "FF9_Data" / "WorldMap" / f"Disc{dst_disc}" / lod
    if not src_root.is_dir():
        raise ValueError(f"no Disc{src_disc} WorldMap overrides in {mod_folder}")

    # inventory the deployed cells + their overridden parts
    by_cell = defaultdict(dict)                               # (bx,by) -> {filename: Path}
    for p in sorted(src_root.rglob("Block[[]*")):
        m = _BLOCK_RE.match(p.name)
        if m:
            by_cell[(int(m.group(1)), int(m.group(2)))][p.name] = p
    if not by_cell:
        raise ValueError(f"no deployed Block overrides under {src_root}")
    if cells is not None:
        by_cell = {k: v for k, v in by_cell.items() if k in cells}

    real_src = _real_parts(src_disc, lod, game=game)
    real_dst = _real_parts(dst_disc, lod, game=game)

    out = {"mirrored": [], "pinned": [], "skipped": []}
    for blk in sorted(by_cell):
        files = by_cell[blk]
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
                    if not _parts_identical(blk, pt, src_disc, dst_disc, lod, game=game)]
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
            bm = X.read_block(dx, dy, disc=src_disc, lod=lod, part=part, game=game)
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
