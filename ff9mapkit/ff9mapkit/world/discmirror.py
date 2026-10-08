"""Mirror a mod folder's WorldMap overrides across DISC TREES (``world-mirror``).

THE DISC-4 GAP (found in-game 2026-07-13, "the island no longer exists on disc 4"): the
overworld ships exactly TWO asset trees -- ``worldmap/disc1`` (used by discs 1-3) and
``worldmap/disc4`` (distinct art; only ``WorldDisc1``/``WorldDisc4`` prefabs exist) -- and
every s34 lookup (override files, ``Donor.txt`` sidecars, the reclaim fallback prefab) is
keyed on the engine's ``currentDisc``. A custom landmass deployed under ``Disc1/`` simply
does not exist once the scenario (or the debug-menu disc switch) crosses the disc-4 threshold.

``mirror(mod_folder)`` closes the gap:

* every deployed ``Block[x][y] *.ff9mesh`` + ``Donor.txt`` under the source tree copies
  byte-verbatim into the destination tree, gated per cell -- the destination's REAL cell
  must be open ocean (no real assets) or the same mesh as the source disc's, compared as a
  triangle multiset (an ``--in-place`` edit of a real block that DIFFERS across discs must
  not be transplanted between them -- those cells skip with a warning). The auto-run is
  EDIT-ATOMIC: a cell is never copied while an adjacent cell of the same write is refused
  (that left a step on disc 4), and a writer that hands in a ``replay`` gets its edit re-run
  on disc 4's own ground instead (terrain study defects 7-9, O2);
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
from collections import Counter, defaultdict
from pathlib import Path

from . import extract as X
from . import mesh as M

_BLOCK_RE = re.compile(r"^Block\[(\d+)\]\[(\d+)\] (.+?)\.(ff9mesh|txt)$")
_DISC_SEG_RE = re.compile(r"^Disc(\d+)$")

# The only discs FF9 actually ships a `worldmap/disc{N}/` bundle tree for. Anything else in a deployed override
# path is a SYNTHETIC namespace (Path D's sentinel, engine patch s74) and must never be mirrored into a real one.
_REAL_DISCS = (1, 4)

#: ``skip_mirror=DEFERRED`` -- what an ORCHESTRATOR hands its inner writers when it unions their written paths and
#: runs ONE :func:`auto_mirror` pass itself (the ``world-mountain`` CLI, ``fuse_layout``, ``author_entrance``).
#: Truthy, so the inner writer still skips; distinct from ``True`` so its log line says the mirror is DEFERRED
#: instead of claiming the operator passed ``--skip-mirror`` (which they never did).
DEFERRED = "deferred"
#: ``skip_mirror=REPLAY`` -- what a ``replay`` hands the writer call it re-runs on the destination disc: that call IS
#: the mirror, so it skips silently (it used to print "skipped (--skip-mirror)" in the middle of the replay's own log)
REPLAY = "replay"


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


def _tri_multiset(bm) -> Counter:
    """``bm``'s triangles as an ORDER-INVARIANT multiset: each triangle's three corner records (position, normal,
    uv, tangent -- every channel a ``.ff9mesh`` carries) rotated to the smallest start, which keeps the winding,
    plus the IDALL the engine reads (``tangent.x`` of the triangle's first buffer corner, ``WMBlock.cs:210``)."""
    pos, nrm, uvs, tan = bm.verts, bm.normals or (), bm.uvs or (), bm.tangents or ()

    def rec(i):
        return (tuple(pos[i]), tuple(nrm[i]) if nrm else (), tuple(uvs[i]) if uvs else (),
                tuple(tan[i]) if tan else ())
    fi, out = bm.flat_index, Counter()
    for t in range(len(fi) // 3):
        a, b, c = fi[3 * t:3 * t + 3]
        r = (rec(a), rec(b), rec(c))
        out[(min(r, r[1:] + r[:1], r[2:] + r[:2]), int(round(tan[a][0])) if tan else None)] += 1
    return out


def _parts_identical(blk, part: str, src_disc: int, dst_disc: int, lod: str = "0_1", *, game=None) -> bool:
    """Is the REAL ``part`` of ``blk`` the same mesh on both discs? Compared as a triangle MULTISET
    (:func:`_tri_multiset`), not as ordered arrays (terrain study defect 9): 10 real land cells hold the same
    triangles in a different buffer order on disc 4, and the ordered compare refused them. The ground the engine
    finds differs only on exact shared edges, a set of measure zero (the study's G2: 0 of 163,840 jittered samples)."""
    a = X.read_block(blk[0], blk[1], disc=src_disc, lod=lod, part=part, game=game)
    b = X.read_block(blk[0], blk[1], disc=dst_disc, lod=lod, part=part, game=game)
    return (a.vcount == b.vcount and len(a.flat_index) == len(b.flat_index)
            and _tri_multiset(a) == _tri_multiset(b))


def _cell_refusal(blk, real_src: dict, real_dst: dict, src_disc: int, dst_disc: int, lod: str, *, game=None):
    """Why ``blk``'s deployed overrides may not be COPIED across discs, or ``None`` when they may: the
    destination's real cell must be open ocean, or carry the same real parts as the source disc, each the same
    mesh (an edit of real ground built from one disc's bytes does not fit the other's)."""
    dst_real = real_dst.get(blk, set())
    if not dst_real:
        return None
    src_real = real_src.get(blk, set())
    if src_real != dst_real:
        return f"real cell part sets differ across discs ({sorted(src_real)} vs {sorted(dst_real)})"
    diff = [pt for pt in sorted(dst_real) if not _parts_identical(blk, pt, src_disc, dst_disc, lod, game=game)]
    if diff:
        return f"real cell differs across discs in {diff}"
    return None


def _neighbours(blk):
    """The 4 neighbours of a block on the 24x20 torus."""
    x, y = blk
    gx, gy = M.GRID_COLS, M.GRID_ROWS
    return {((x + 1) % gx, y), ((x - 1) % gx, y), (x, (y + 1) % gy), (x, (y - 1) % gy)}


def _components(cells) -> list:
    """``cells`` split into 4-connected groups (torus-aware): the units an edit can tear apart at a shared border."""
    left, out = set(cells), []
    while left:
        seed = left.pop()
        comp, todo = {seed}, [seed]
        while todo:
            for n in _neighbours(todo.pop()):
                if n in left:
                    left.discard(n)
                    comp.add(n)
                    todo.append(n)
        out.append(comp)
    return sorted(out, key=lambda c: min(c))


def _cell_of(path: Path):
    """``(bx, by)`` parsed from a deployed override's OWN filename (``Block[x][y] <Part>.ff9mesh`` or the
    ``Block[x][y] Donor.txt`` sidecar -- :data:`_BLOCK_RE` matches both extensions). ``None`` if the
    filename doesn't match (defensive -- every real writer path does)."""
    m = _BLOCK_RE.match(path.name)
    return (int(m.group(1)), int(m.group(2))) if m else None


def _game_root_of(path: Path, mod_folder):
    """The game root ``path`` was deployed under, or ``None`` when ``path`` does not lie under ``mod_folder``.

    Every writer joins ``<game> / mod_folder``, so the two spellings land differently: a RELATIVE ``mod_folder``
    (the usual bare ``FF9CustomMap-world``) appears as a run of whole segments and the root is everything before
    it; an ABSOLUTE one (a bench / scratch tree) replaces ``<game>`` outright, so it matches as a path PREFIX and
    the root is its parent -- no segment of the written path ever equals the whole absolute string."""
    mf = Path(mod_folder)
    if mf.is_absolute():
        try:
            mf, path = mf.resolve(), path.resolve()
        except OSError:
            return None
        return mf.parent if path.is_relative_to(mf) else None
    seg, parts = mf.parts, path.parts
    for i in range(len(parts) - len(seg) + 1):
        if parts[i:i + len(seg)] == seg:
            return Path(*parts[:i])
    return None


def auto_mirror(written, *, mod_folder: str, skip_mirror: bool = False, dst_disc: int = 4, replay=None,
                log=print):
    """Automatic POST-STEP for every world-deploy writer: pass it ``written`` -- the list/iterable of
    return values of THIS call's own real :func:`~ff9mapkit.world.mesh.deploy_override` /
    :func:`~ff9mapkit.world.mesh.deploy_donor_sidecar` calls -- right after a verb finishes writing, to
    close THE DISC-4 GAP (module docstring) without the operator having to remember a separate
    ``world-mirror`` run.

    Never touches ``config.find_game_path`` or the filesystem itself except through :func:`mirror` (and
    even then, only once real evidence of a write survives filtering) -- see the module docstring's
    EVIDENCE CONTRACT. In order:

    1. ``skip_mirror=True`` (CLI ``--skip-mirror``) opts out explicitly -- logs one line, does nothing.
       ``skip_mirror=DEFERRED`` is the same no-op for an inner writer whose orchestrator runs the one pass
       itself; its line says so instead of blaming a ``--skip-mirror`` nobody passed. ``skip_mirror=REPLAY`` is the
       silent no-op for the writer call a ``replay`` re-runs on the destination disc.
    2. Every entry of ``written`` that is not a real, existing ``str``/``Path`` under a ``WorldMap/Disc{n}``
       tree (``n != dst_disc``) is dropped. A ``MagicMock`` (a hermetic test that mocked the deploy calls
       out) fails the ``isinstance`` check -- if NOTHING survives (a dry run, a mocked writer, or a writer
       that deployed straight to ``dst_disc`` already), this is a silent no-op.
    3. The game root, source disc, lod, and cell set are derived purely by parsing the surviving paths
       (:func:`_game_root_of` -- ``mod_folder`` as whole segments, or as a path prefix when it is absolute --
       then the ``Disc{n}`` segment + the segment after it + each filename's ``Block[x][y]``) -- grouped per
       source disc (a single writer call touches one disc in practice; a mixed set is handled by looping).
       Real writes that survived but sit under no ``mod_folder`` log one ``NOT RUN`` line and return.
    4. :func:`mirror` runs once per source-disc group, scoped to exactly that group's cells via its
       ``cells=`` filter -- an unrelated write elsewhere in the tree is never touched -- and EDIT-ATOMIC
       (``atomic=True``): a group of adjacent written cells reaches disc 4 whole or not at all (terrain study
       defect 8). ``replay`` (``replay(dst_disc)``, the writer's own call re-run on the destination disc) edits
       disc 4's own ground when a written cell cannot be copied; writers without one leave such an edit
       un-mirrored and say so. A ``ValueError`` out
       of :func:`mirror` itself (e.g. the derived game root has no real StreamingAssets bundle data to
       compare cells against -- a bench tree, or a hermetic caller exercising just the writer) is logged
       as ``NOT RUN`` and swallowed per group: this is a best-effort POST-step, not a new hard requirement
       on every deploy call -- but never a silent one.

    Returns the last :func:`mirror` summary dict, or ``None`` when it never ran. The standalone
    ``world-mirror`` verb (a direct :func:`mirror` call, ``cells=None``) is unaffected either way."""
    if skip_mirror == DEFERRED:
        log(f"disc-{dst_disc} mirror: deferred to the calling verb's single pass over all of its writes")
        return None
    if skip_mirror == REPLAY:
        return None
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
        root = _game_root_of(pp, mod_folder)
        if root is None:
            continue
        if game_root is None:
            game_root = root
        elif root != game_root:
            raise ValueError(f"auto_mirror: written paths disagree on the game root ({game_root} vs "
                             f"{root}) -- refusing to guess which is right")
    if game_root is None:                                    # real writes, but none under mod_folder -- say so
        log(f"disc-{dst_disc} mirror: NOT RUN -- could not derive the game root from --mod-folder "
            f"{mod_folder!r} (none of the {len(hits)} written override(s) lies under it); "
            f"Disc{dst_disc} is NOT mirrored -- run world-mirror by hand")
        return None

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
        # THE FOREIGN-NAMESPACE REFUSAL (Path D). The disc-1<->disc-4 mirror exists to close THE DISC-4 GAP for
        # the two REAL discs. A synthetic world (engine patch s74) resolves its overrides against a SENTINEL disc
        # whose whole purpose is to be disjoint from the real trees -- mirroring those cells into the real Disc4
        # namespace would recreate exactly the collision s74 was built to prevent, and would do it silently.
        # Today this is stopped only by ACCIDENT: mirror() -> _real_parts(src_disc) -> _worldmap_env(9) rescans
        # ~50 p0data bundles, finds no `worldmap/disc9/` container, and raises ValueError, which the handler
        # below swallows as a benign "no bundle data" skip. That is a slow, misleadingly-logged near-miss rather
        # than a guard, and it would stop working the moment a disc-9 read path were ever cached or stubbed.
        # Refuse explicitly, before the rescan.
        if src_disc not in _REAL_DISCS:
            log(f"disc-{dst_disc} mirror: refused for Disc{src_disc} "
                f"(not a real disc -- a synthetic override namespace is deliberately unmirrored)")
            continue
        try:
            out = mirror(mod_folder, src_disc=src_disc, dst_disc=dst_disc, lod=grp["lod"] or "0_1",
                         game=game_root, cells=grp["cells"], atomic=True, replay=replay, log=log)
        except ValueError as e:
            # defensive -- mirror() re-validates the same tree (e.g. the derived game_root has no real
            # StreamingAssets bundle data: a bench tree) -- a best-effort post-step, not a new hard requirement
            # on every deploy call, but never a silent one
            log(f"disc-{dst_disc} mirror: NOT RUN for Disc{src_disc} ({e}) -- run world-mirror by hand")
            continue
    return out


def mirror(mod_folder: str, *, src_disc: int = 1, dst_disc: int = 4, lod: str = "0_1",
           game=None, dry_run: bool = False, cells: set | None = None, atomic: bool = False,
           replay=None, log=print) -> dict:
    """Mirror ``mod_folder``'s ``Disc{src}`` WorldMap overrides into ``Disc{dst}``. ``cells`` (a
    ``{(x, y), ...}`` set, default ``None``) restricts the mirror to exactly those cells -- the scoping
    :func:`auto_mirror` uses so a write to one cell can never re-mirror (and potentially clobber a
    hand-diverged Disc4 variant of) an unrelated cell elsewhere in the same tree. ``None`` mirrors every
    deployed cell under the source tree -- the standalone ``world-mirror`` CLI verb's always-runs,
    whole-tree behavior.

    THE EDIT-ATOMIC MIRROR (terrain study defect 8). A cell whose real ground differs across discs is never
    copied (:func:`_cell_refusal`). Copying its NEIGHBOURS anyway cracked disc 4: a +4 hill across an eligible
    and a refused cell left a 4.0u step at their border (study G3; 7.5% of random multi-cell reshapes).
    ``atomic=True`` (what :func:`auto_mirror` passes) holds back every cell 4-connected to a refused one within the
    scope, so a group of written cells reaches disc 4 whole or not at all. Then, when the writer handed in a
    ``replay`` (``replay(dst_disc)`` = the same edit run again on the destination disc's own stock, through the
    verb's own gates), nothing is copied: the replay edits disc 4's ground itself (a copy of an identical cell and
    its replay are byte-equal, study K1/K2 71/71). A replay that refuses (``ValueError``) leaves disc 4 untouched.
    Without ``atomic`` (the standalone verb) each cell is gated alone, as before, and a refused cell next to a
    copied one is named, since disc 4 may show a step along their border.
    Returns ``{"mirrored": [paths], "pinned": [paths], "skipped": [(cell, why)], "held": [cells], "replay":
    None | {"cells", "differs"} | {"refused"}}``."""
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

    out = {"mirrored": [], "pinned": [], "skipped": [], "held": [], "replay": None}
    verdict = {blk: _cell_refusal(blk, real_src, real_dst, src_disc, dst_disc, lod, game=game) for blk in by_cell}
    refused = {blk: why for blk, why in verdict.items() if why}
    held = {}                                                 # blk -> the refused cells its group carries
    if atomic:
        for comp in _components(by_cell):
            bad = sorted(c for c in comp if c in refused)
            if bad:
                held.update({c: bad for c in comp if c not in refused})
    # ---- THE REPLAY: the edit run again on the destination disc's own ground ----------------
    if atomic and replay is not None and refused:
        out["skipped"] = sorted(refused.items())
        log(f"  disc {dst_disc} differs from disc {src_disc} at {sorted(refused)} -- REPLAYING the edit on "
            f"Disc{dst_disc}'s own ground instead of copying it")
        if dry_run:
            out["replay"] = {"cells": sorted(by_cell), "differs": dict(sorted(refused.items())), "dry_run": True}
            return out
        try:
            replay(dst_disc)
        except ValueError as e:
            out["replay"] = {"refused": str(e)}
            log(f"  !! NOT MIRRORED: the replay on Disc{dst_disc} refused ({str(e).splitlines()[0][:200]}) -- "
                f"disc {dst_disc} keeps its own ground there, without this edit")
            return out
        out["replay"] = {"cells": sorted(by_cell), "differs": dict(sorted(refused.items()))}
        for blk, why in sorted(refused.items()):
            log(f"  REPLAYED {blk} on Disc{dst_disc} ({why}): disc {dst_disc}'s own ground there was edited -- "
                f"check it on disc {dst_disc} in game (ridges, objects and entrances differ there)")
        return out
    for blk in sorted(by_cell):
        files = by_cell[blk]
        # ---- the per-cell gate (+ the atomic hold) ---------------------------------------
        if blk in refused:
            out["skipped"].append((blk, refused[blk]))
            log(f"  SKIP {blk}: {refused[blk]}")
            continue
        if blk in held:
            out["held"].append(blk)
            out["skipped"].append((blk, f"held back: its edit spans refused cell(s) {held[blk]}"))
            continue
        # ---- copy the deployed files ----------------------------------------------------
        for name, p in sorted(files.items()):
            dst = dst_root / f"r{blk[1]}" / name
            if not dry_run:
                dst.parent.mkdir(parents=True, exist_ok=True)
                dst.write_bytes(p.read_bytes())
                # A mirrored file is a DEPLOYED override we own, but it is written HERE rather
                # than through the deploy seam -- so without this it never enters the ledger and
                # THE OWNERSHIP REFUSAL stays in its permissive `if shas` branch for the whole
                # destination disc, permanently. Same reasoning as the coastnav stamp's own
                # mirror ledger call (coastnav.py:398). Covers BOTH the meshes (deploy_override's
                # refusal) and the Donor.txt sidecar (deploy_donor_sidecar's refusal, part
                # "Donor" -- _BLOCK_RE group(3) already reads "Donor" for the .txt form); the
                # sidecar picks the s34 divert's render prefab, so it is as load-bearing as any
                # mesh beside it.
                m = _BLOCK_RE.match(name)
                if m:
                    M.record_ledger_write(dst, cell=blk, part=m.group(3),
                                          write_disc=dst_disc, read_disc=src_disc)
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
                # the pinned free-ride part is equally ours and equally invisible to the ledger
                M.record_ledger_write(dst, cell=blk, part=part_name,
                                      write_disc=dst_disc, read_disc=src_disc)
            out["pinned"].append(dst)
            log(f"  PIN {blk} <- donor ({dx},{dy}) {part_name} "
                f"({len(bm.tris)} tris, source-disc bytes)")
    if out["held"]:
        log(f"  !! NOT MIRRORED: {sorted(out['held'])} -- their edit also covers {sorted({c for blk in out['held'] for c in held[blk]})}, "
            f"which differ(s) on disc {dst_disc}; copying the rest would leave a step at the shared border. Disc "
            f"{dst_disc} keeps its own ground there; re-run the edit with --disc {dst_disc} to edit it on purpose")
    if not atomic:
        copied = {blk for blk in by_cell if blk not in refused}
        risk = sorted((a, b) for b in refused for a in _neighbours(b) if a in copied)
        if risk:
            log(f"  !! WARNING: a refused cell borders a mirrored one at {risk[:8]}{' ...' if len(risk) > 8 else ''}: "
                f"if one edit covers both, disc {dst_disc} shows a step along that border")
    log(f"mirrored {len(out['mirrored'])} file(s), pinned {len(out['pinned'])} free-ride "
        f"part(s), skipped {len(out['skipped'])} cell(s) -> Disc{dst_disc}")
    return out
