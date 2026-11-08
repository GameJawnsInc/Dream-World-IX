"""Landmass PREFABS (rung P1, studies/overworld-editor/PREFABS.md): a frozen composition stamped anywhere it is lawful.

A prefab is a ``world-fuse`` recipe written RELATIVE to an anchor block. Its BASE is one minted ``[[island]]`` or one
walked stock carry unit (``[[transplant]]``, placed by ``cell``), plus carried relief (``[[mountain]]`` /
``[[forest]]`` / ``[[hill]]``), every centre an offset from the anchor block's frame origin (its corner,
``(64 * bx, -64 * (by + 1))``, i.e. ``64 * floor(x / 64)`` and ``64 * floor(z / 64)``). Placing it on block
``(BX, BY)`` shifts every row by whole blocks and turns on the prefab frame (rung P0) for the rows that take it, so
the land written is the land that was walked, shifted.

THE IDENTITY IS THE CONTRACT. Each catalog entry carries the FINGERPRINT of its disc-1 files, block-relative, taken
by :func:`fingerprint` on a staging folder at a CLEAN site (``fingerprint_cell``). :func:`place` composes the prefab
in a staging folder first and refuses unless that land is the catalog's, so a regression in any verb it rides refuses
at the call site instead of shipping different land under a walked name. Only then does it compose into the target --
through the verbs' own gates, never by copying staged files (THE LEDGER TRAVELS WITH THE BYTES) -- and requires what
it wrote, on disc 1 and on the disc-4 copy, to be exactly the staged land.

THE NAV MARGIN (measured 2026-11-08): a minted island's sea is CLASSED by the coast-nav stamp against the ground
within ``coastnav.FRINGE_R`` (16u) of each sea triangle's centroid -- so stock land within 16u outside the footprint
re-classes a few of the prefab's own sea triangles (anchored at (0,12), 9 Sea4 tris beside (22,13)/(22,14) went from
open sea 57 to landable 53). Those classes are the stamp's job at that site, not the walked bytes. So identity has two
tiers (the adversarial review of the first version, which masked EVERY water class, showed that blind to any change
in the sea's navigation, the walked boat behaviour):

- a CLEAN site (no stamp-visible stock ground within 16u of the footprint): the full fingerprint, classes included,
  must equal the catalog's;
- a site BESIDE stock land: a reference copy is staged at ``fingerprint_cell`` and must equal the catalog; the target
  must then equal the reference triangle for triangle, the class masked ONLY on water triangles whose centroid lies
  within 16u of that stock ground, and the stamp must have settled exactly those (:func:`nav_settled`).

A transplant base carries its stock sea WITH its stock classes (nothing re-stamps them): always the full fingerprint.

THE CLEAR WINDOW. The staged bytes stand for the target's only if the target gives the verbs the same inputs. The
target folder must hold no override in the footprint, its one-block ring (the nav stamp reads 16u past the footprint,
and an existing neighbour's own sea would go stale beside new land), or any relief row's read window; no other
FolderNames folder may hold one in the footprint or its ring (the stamp's loader reads only the target folder and
stock, so another folder's land there would be invisible to it).

The fingerprint hashes TRIANGLES, not files: the plain mint writes the same triangles at every site but not always
in the same vertex order (measured, P1), and the engine draws triangles. Each triangle is its three corners at the
file's float32 precision -- position, uv, tangent and the normal rounded to 1e-6 (the mint's normals carry ~1e-14
noise from absolute positions; WorldMap Terrain binds no normal) -- rotated to start at its smallest corner, so the
winding is kept.

Status follows ``donors.toml``: a ``candidate`` places with a banner and is walked in game before it is ``qualified``;
the fingerprint does not change when it is (the walk qualifies the bytes the fingerprint names).
"""
from __future__ import annotations

import hashlib
import math
import re
import shutil
import tempfile
import tomllib
from pathlib import Path

#: The catalog shipped with the kit.
CATALOG = Path(__file__).resolve().parent / "data" / "prefabs.toml"
#: The tables a prefab may hold: the bases and the carries measured under a shift (PREFABS.md).
PREFAB_TABLES = ("island", "transplant", "mountain", "forest", "hill")
#: The BASE a prefab stands on (exactly one, the first row): a minted island, or a walked stock carry unit placed by
#: ``cell`` (its rect's anchor block, as an offset from the prefab's anchor).
BASE_TABLES = ("island", "transplant")
#: The tables whose rows take the prefab frame (P0); the forest and the hill measured identical without it.
FRAMED_TABLES = ("island", "mountain")
STATUSES = ("candidate", "qualified")
BLOCK = 64.0
WORLD_W = 1536.0
_DEFAULT_REACH = 96.0
#: THE NAV MARGIN: ``coastnav.FRINGE_R``, the reach of the stamp's near-shore classes from a sea centroid.
NAV_MARGIN = 16.0
_FILE = re.compile(r"^Block\[(\d+)\]\[(\d+)\] (\w+)\.(ff9mesh|txt)$")
#: The parts the coast-nav stamp classes (``coastnav.SEA_PARTS``) and the classes it writes (``coastnav.WATER``).
_NAV_PARTS = ("Sea1", "Sea2", "Sea3", "Sea4", "Sea5")
_NAV_WATER = {53, 54, 55, 56, 57}


class PrefabRefused(ValueError):
    """A place or check that refuses; ``where`` = the blocks (wrapped labels) it refuses over, if any."""

    def __init__(self, msg: str, where=()):
        super().__init__(msg)
        self.where = sorted(where)


# ---------------------------------------------------------------- the catalog
def load_catalog(path=None) -> list:
    """Every ``[[prefab]]`` in the catalog TOML, validated: unique names, a known status, exactly one BASE row first
    (an island with an explicit seed -- the frame refuses without one -- or a transplant with ``cell`` and ``donor``),
    only :data:`PREFAB_TABLES`, a relative ``center`` on every other row, no ``near`` / ``prefab_frame`` / ``step``
    written by hand (placement sets them), and a ``fingerprint_cell`` beside any island prefab's fingerprint."""
    doc = tomllib.loads(Path(path or CATALOG).read_text(encoding="utf-8"))
    out, seen = [], set()
    for i, p in enumerate(doc.get("prefab", ())):
        name = p.get("name")
        where = f"[[prefab]] #{i} ({name!r})"
        if not name or name in seen:
            raise ValueError(f"{where}: needs a unique name")
        seen.add(name)
        if p.get("status") not in STATUSES:
            raise ValueError(f"{where}: status must be one of {STATUSES}")
        rows = p.get("rows") or []
        if not rows or rows[0].get("table") not in BASE_TABLES:
            raise ValueError(f"{where}: the first row is the base the relief stands on: one of {BASE_TABLES}")
        if sum(1 for r in rows if r.get("table") in BASE_TABLES) != 1:
            raise ValueError(f"{where}: one base (island or transplant) per prefab")
        if rows[0]["table"] == "island" and "seed" not in rows[0]:
            raise ValueError(f"{where}: the island row needs its seed (the prefab frame refuses a centre-derived one)")
        for r in rows:
            if r.get("table") not in PREFAB_TABLES:
                raise ValueError(f"{where}: table {r.get('table')!r} has not been measured under a shift; "
                                 f"a prefab holds {PREFAB_TABLES}")
            if r["table"] == "transplant":
                if "cell" not in r or len(r["cell"]) != 2 or "donor" not in r:
                    raise ValueError(f"{where}: a transplant row names cell = [dx, dy] (blocks from the anchor) and "
                                     f"its donor")
            elif "center" not in r or len(r["center"]) != 2:
                raise ValueError(f"{where}: every row is an exact placement: center = [dx, dz] from the frame origin")
            if "near" in r or "prefab_frame" in r or "step" in r:
                raise ValueError(f"{where}: near / prefab_frame / step are set by placement, not the catalog")
        foot = p.get("footprint")
        if foot is not None and not all(len(b) == 2 for b in foot):
            raise ValueError(f"{where}: footprint = [[dx, dy], ...] blocks relative to the anchor")
        fc = p.get("fingerprint_cell")
        if p.get("fingerprint") and stamped_nav(p) and (fc is None or len(fc) != 2):
            raise ValueError(f"{where}: an island prefab's fingerprint names the CLEAN site it was taken at: "
                             f"fingerprint_cell = [bx, by]")
        out.append(p)
    return out


def get(name: str, path=None) -> dict:
    for p in load_catalog(path):
        if p["name"] == name:
            return p
    raise PrefabRefused(f"no prefab named {name!r} (have: {', '.join(p['name'] for p in load_catalog(path))})")


def stamped_nav(prefab: dict) -> bool:
    """Whether the prefab's sea navigation is STAMPED at placement (a minted island: site-dependent within the nav
    margin) rather than carried (a transplant: stock bytes, fingerprinted in full everywhere)."""
    return prefab["rows"][0]["table"] == "island" and prefab["rows"][0].get("coastnav", True) is not False


def nav_policy(prefab: dict) -> str:
    """The landability policy the prefab's island row stamps its sea with."""
    return str(prefab["rows"][0].get("coastnav_policy", "land-anywhere"))


# ---------------------------------------------------------------- the frame
def origin(cell) -> tuple:
    """The frame origin of anchor block ``cell = (bx, by)``: its corner at the lowest x and z."""
    bx, by = int(cell[0]), int(cell[1])
    return BLOCK * bx, -BLOCK * (by + 1)


def expand(prefab: dict, cell) -> list:
    """The prefab's rows placed on anchor block ``cell``: absolute centres (a transplant's ``cell`` as a wrapped
    label), ``step = N`` in catalog order, and the prefab frame on the rows that take it. Each row keeps its ``table``
    key (``recipe.dumps`` / ``doc_for``)."""
    ox, oz = origin(cell)
    out = []
    for n, r in enumerate(prefab["rows"], start=1):
        row = {k: v for k, v in r.items()}
        if r["table"] == "transplant":
            row["cell"] = list(label_of(r["cell"], cell))
        else:
            dx, dz = (float(v) for v in r["center"])
            row["center"] = [ox + dx, oz + dz]
        row["step"] = n
        if row["table"] in FRAMED_TABLES:
            row["prefab_frame"] = True
        out.append(row)
    return out


def doc_for(rows) -> dict:
    """A ``world-fuse`` document (``{table: [row, ...]}``) for expanded rows."""
    doc: dict = {}
    for r in rows:
        doc.setdefault(r["table"], []).append({k: v for k, v in r.items() if k != "table"})
    return doc


def rel_block(label, cell) -> tuple:
    """A wrapped block label as an offset from anchor ``cell`` (the x torus folded into [-12, 12))."""
    dx = (int(label[0]) - int(cell[0]) + 12) % 24 - 12
    return dx, int(label[1]) - int(cell[1])


def label_of(rel, cell) -> tuple:
    """The wrapped block label at offset ``rel`` from anchor ``cell``."""
    from .mesh import wrap_block_col
    return wrap_block_col(int(cell[0]) + int(rel[0])), int(cell[1]) + int(rel[1])


def rel_point(x: float, z: float, cell) -> tuple:
    """World ``(x, z)`` relative to the frame origin of anchor ``cell``, x folded into [-768, 768) on the torus."""
    ox, oz = origin(cell)
    return (x - ox + WORLD_W / 2) % WORLD_W - WORLD_W / 2, z - oz


def read_windows(rows) -> set:
    """Every block (wrapped label) a relief row reads: its centre +- its reach (the hill's own rule:
    ``max(96, radius + 10)``), clipped to the map's rows."""
    from .mesh import GRID_ROWS, wrap_block_col
    out = set()
    for r in rows:
        if r["table"] in BASE_TABLES:
            continue
        cx, cz = (float(v) for v in r["center"])
        if r["table"] == "hill":
            reach = max(_DEFAULT_REACH, float(r.get("radius", 20.0)) + 10.0)
        else:
            reach = float(r.get("reach", _DEFAULT_REACH))
        for bx in range(math.floor((cx - reach) / BLOCK), math.floor((cx + reach) / BLOCK) + 1):
            for by in range(math.floor(-(cz + reach) / BLOCK), math.floor(-(cz - reach) / BLOCK) + 1):
                if 0 <= by < GRID_ROWS:
                    out.add((wrap_block_col(bx), by))
    return out


def _ring(labels) -> set:
    """The blocks touching ``labels`` (8-neighbourhood, x wrapped, rows kept on the map), minus ``labels``."""
    from .mesh import GRID_ROWS, wrap_block_col
    out = set()
    for bx, by in labels:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if 0 <= by + dy < GRID_ROWS:
                    out.add((wrap_block_col(bx + dx), by + dy))
    return out - set(labels)


def _dist_to_blocks(x: float, z: float, labels) -> float:
    """Plan distance from world ``(x, z)`` to the nearest block square of ``labels`` (x on the torus)."""
    best = math.inf
    for bx, by in labels:
        x0, z1 = BLOCK * bx, -BLOCK * by                      # the square is x0..x0+64, z1-64..z1
        dx = abs((x - (x0 + BLOCK / 2) + WORLD_W / 2) % WORLD_W - WORLD_W / 2) - BLOCK / 2
        dz = abs(z - (z1 - BLOCK / 2)) - BLOCK / 2
        best = min(best, math.hypot(max(dx, 0.0), max(dz, 0.0)))
    return best


# ---------------------------------------------------------------- the fingerprint
def _f32(v) -> float:
    import struct
    return struct.unpack("<f", struct.pack("<f", float(v)))[0]


def mesh_digest(path, *, mask_tri=None, label=None, cell=None) -> str:
    """The triangles of one ``.ff9mesh``, order-free and winding-kept (see the module docstring). ``mask_tri`` (with
    the file's block ``label`` and the anchor ``cell``) is a predicate on a triangle's centroid relative to the frame
    origin (:func:`rel_point`): where it holds, the navigation class of the triangle's WATER vertices is blanked
    (tangent.x bits 2-7 when they hold a water topograph) -- the nav-margin triangles a site's stamp decides."""
    from .extract import block_world_origin
    from .mesh import read_ff9mesh
    m = read_ff9mesh(path)
    V, U, T, N, I = m["verts"], m["uvs"], m["tangents"], m["normals"], m["indices"]
    ox, oz = block_world_origin(*label) if mask_tri is not None else (0.0, 0.0)

    def corner(i, masked):
        t = [_f32(c) for c in T[i]]
        if masked:
            ix = int(round(t[0]))
            if ((ix & 0xFC) >> 2) in _NAV_WATER:
                t[0] = float(ix & ~0xFC)
        return (tuple(_f32(c) for c in V[i]) + tuple(_f32(c) for c in U[i]) + tuple(t)
                + tuple(round(_f32(c), 6) + 0.0 for c in N[i]))
    tris = []
    for k in range(0, len(I) - len(I) % 3, 3):
        idx = I[k:k + 3]
        masked = False
        if mask_tri is not None:
            cx = sum(V[i][0] for i in idx) / 3.0 + ox
            cz = sum(V[i][2] for i in idx) / 3.0 + oz
            masked = bool(mask_tri(*rel_point(cx, cz, cell)))
        c = [corner(i, masked) for i in idx]
        s = c.index(min(c))
        tris.append(tuple(c[s:] + c[:s]))
    tris.sort()
    return hashlib.sha256(repr(tris).encode()).hexdigest()


def _block_files(mod_root, label, disc: int = 1) -> list:
    """The override files at one wrapped block label (write-seam backups excluded)."""
    bx, by = label
    d = Path(mod_root) / "FF9_Data" / "WorldMap" / f"Disc{disc}" / "0_1" / f"r{by}"
    if not d.is_dir():
        return []
    return sorted(p for p in d.glob(f"Block[[]{bx}[]][[]{by}[]] *") if _FILE.match(p.name))


def written_blocks(mod_root, disc: int = 1) -> set:
    """Every block label holding an override file in a folder's disc tree."""
    out = set()
    root = Path(mod_root) / "FF9_Data" / "WorldMap" / f"Disc{disc}" / "0_1"
    for p in root.glob("r*/Block*") if root.is_dir() else ():
        m = _FILE.match(p.name)
        if m:
            out.add((int(m[1]), int(m[2])))
    return out


def fingerprint(mod_root, cell, blocks, *, disc: int = 1, mask_tri=None) -> str:
    """One hash over every override file of disc ``disc`` at ``blocks`` (wrapped labels), keyed by the block's offset
    from ``cell`` and the part: meshes by :func:`mesh_digest`, sidecars (``Donor.txt``) by their bytes. ``mask_tri``
    blanks the class of the nav-margin triangles of the SEA parts only (see :func:`mesh_digest`)."""
    rows = []
    for label in sorted(blocks):
        rel = rel_block(label, cell)
        for p in _block_files(mod_root, label, disc):
            name = _FILE.match(p.name)[3]
            part = name + "." + _FILE.match(p.name)[4]
            if p.suffix == ".ff9mesh":
                mask = mask_tri if name in _NAV_PARTS else None
                dig = mesh_digest(p, mask_tri=mask, label=label, cell=cell)
            else:
                dig = hashlib.sha256(p.read_bytes()).hexdigest()
            rows.append(f"{rel[0]},{rel[1]}|{part}|{dig}")
    return hashlib.sha256("\n".join(sorted(rows)).encode()).hexdigest()


def nav_settled(mod_folder, blocks, *, disc: int = 1, policy: str = "land-anywhere", game=None) -> dict:
    """The coast-nav stamp's own verdict on ``blocks``' sea, read-only: ``{}`` when every vertex it classes already
    holds the class it would write AT THIS SITE (its stock neighbours included), else ``{class: vertex count}`` still
    to change. It judges only what the stamp classes (near ground); everything else stays in the fingerprint."""
    from . import coastnav as CN
    out = CN.stamp(str(mod_folder), disc=disc, cells=sorted(blocks), policy=policy, deploy=False, game=game)
    return dict(out.get("totals") or {})


# ---------------------------------------------------------------- the nav margin
def stock_ground(prefab: dict, cell, *, game=None, discs=(1, 4)) -> dict:
    """``{ring label: [(x, z), ...]}``: the STOCK ground points within :data:`NAV_MARGIN` of the footprint, on any of
    ``discs``, as the coast-nav stamp would see them -- its own ground query (``coastnav._query_top`` over a
    stock-only loader: the engine's up-facing filter and IDALL skip set) at its own 2u sample grid. Disc 4 counts
    because its copy carries disc 1's stamped classes."""
    from . import coastnav as CN
    foot = {label_of(r, cell) for r in prefab.get("footprint") or ()}
    found: dict = {}
    for disc in discs:
        loader = CN._Loader("__ff9mapkit_stock_only__", disc, game)
        for label in sorted(_ring(foot)):
            x0, z1 = BLOCK * label[0], -BLOCK * label[1]
            for i in range(int(BLOCK / CN.STEP_G) + 1):
                x = x0 + i * CN.STEP_G
                for j in range(int(BLOCK / CN.STEP_G) + 1):
                    z = z1 - j * CN.STEP_G
                    if _dist_to_blocks(x, z, foot) > NAV_MARGIN:
                        continue
                    g = CN._query_top(loader, x, z)
                    if g is not None and g[1] not in CN.WATER:
                        found.setdefault(label, set()).add((x % WORLD_W, z))
    return {k: sorted(v) for k, v in found.items()}


def stock_land_near(prefab: dict, cell, *, game=None, discs=(1, 4)) -> set:
    """The ring blocks (wrapped labels) holding stamp-visible STOCK ground within the nav margin of the footprint."""
    return set(stock_ground(prefab, cell, game=game, discs=discs))


def margin_mask(points, cell):
    """The mask predicate (on frame-relative centroids) for the triangles within :data:`NAV_MARGIN` of ``points``
    (world, x folded), so the same triangles mask in the target and in a reference staged elsewhere."""
    rel = [rel_point(x, z, cell) for x, z in points]

    def near(rx: float, rz: float) -> bool:
        return any(abs(rx - px) <= NAV_MARGIN and abs(rz - pz) <= NAV_MARGIN
                   and math.hypot(rx - px, rz - pz) <= NAV_MARGIN + 1e-6 for px, pz in rel)
    return near


# ---------------------------------------------------------------- the clear window
def window_blockers(prefab: dict, cell, mod_root, *, stack=None) -> dict:
    """Why the target cannot stand for the staging folder: ``{"target": {label, ...}, "stack": {folder: {label}}}``,
    empty sets when the window is clear. The target: the footprint, its ring and every relief row's read window.
    ``stack`` = the install's FolderNames roots: the footprint and its ring (the nav stamp's loader cannot see another
    folder's land). Both disc trees count: a placement writes disc 4 too (the auto-mirror)."""
    rows = expand(prefab, cell)
    foot = {label_of(r, cell) for r in prefab.get("footprint") or ()}
    near = foot | _ring(foot)
    want = near | read_windows(rows)
    have = written_blocks(mod_root, 1) | written_blocks(mod_root, 4)
    out = {"target": want & have, "stack": {}}
    for root in stack or ():
        if Path(root).resolve() == Path(mod_root).resolve():
            continue
        hit = near & (written_blocks(root, 1) | written_blocks(root, 4))
        if hit:
            out["stack"][Path(root).name] = hit
    return out


def check_rows_on_map(prefab: dict, cell) -> None:
    """The footprint must sit on the map's rows (rows do not wrap for writes: the kit's edged-row policy)."""
    from .mesh import GRID_ROWS
    for rel in prefab.get("footprint") or ():
        by = int(cell[1]) + int(rel[1])
        if not 0 <= by < GRID_ROWS:
            raise PrefabRefused(f"prefab {prefab['name']!r} on block {tuple(cell)} reaches row {by}, off the map "
                                f"(rows 0..{GRID_ROWS - 1})")


# ---------------------------------------------------------------- compose + place
def _compose(mod_folder, rows, *, game, skip_mirror: bool, dry_run: bool = False) -> dict:
    from . import fuse as FU
    out = FU.compose_layout(str(mod_folder), doc_for(rows), game=game, skip_mirror=skip_mirror, dry_run=dry_run)
    if not out["clean"]:
        bad = [g for g in out["gates"] if not g.get("ok")]
        raise PrefabRefused("a prefab row refused: " + "; ".join(
            f"{g['gate']}: {g.get('error') or g.get('skipped') or g}" for g in bad))
    return out


def stage(prefab: dict, cell, *, game=None, keep: bool = False) -> dict:
    """Compose the prefab on ``cell`` in a fresh staging folder (outside the install, nothing mirrored) and return
    ``{"fingerprint" (full), "footprint" (relative, sorted), "blocks" (labels), "nav" (the stamp's verdict),
    "root"}``. The folder is removed unless ``keep`` (the caller then removes ``root``)."""
    tmp = Path(tempfile.mkdtemp(prefix="ff9-prefab-"))
    try:
        _compose(tmp, expand(prefab, cell), game=game, skip_mirror=True)
        labels = written_blocks(tmp)
        return {"fingerprint": fingerprint(tmp, cell, labels),
                "footprint": sorted(rel_block(b, cell) for b in labels), "blocks": sorted(labels),
                "nav": nav_settled(tmp, labels, policy=nav_policy(prefab), game=game) if stamped_nav(prefab) else {},
                "root": tmp if keep else None}
    finally:
        if not keep:
            shutil.rmtree(tmp, ignore_errors=True)


def _identity(prefab: dict, name: str, cell, staged: dict, *, game, log) -> str:
    """Judge the staged target against the catalog (the two tiers of the module docstring). Returns the tier."""
    if staged["footprint"] != sorted(tuple(b) for b in prefab["footprint"]):
        raise PrefabRefused(f"prefab {name!r} staged on {cell} covers {staged['footprint']}, the catalog says "
                            f"{sorted(tuple(b) for b in prefab['footprint'])}: IDENTITY BROKEN, nothing written")
    ground = stock_ground(prefab, cell, game=game) if stamped_nav(prefab) else {}
    if not ground:
        if staged["fingerprint"] != prefab["fingerprint"]:
            raise PrefabRefused(f"prefab {name!r} staged on {cell} is NOT the land its catalog entry names "
                                f"(fingerprint {staged['fingerprint'][:12]} vs {prefab['fingerprint'][:12]}): a verb "
                                f"it rides changed its bytes -- a regression to find; nothing written")
        if staged["nav"]:
            raise PrefabRefused(f"prefab {name!r} staged on {cell} leaves sea the coast-nav stamp would still re-class "
                                f"({staged['nav']}): a regression in the stamp or the mint; nothing written")
        return "clean site: the full fingerprint"
    # THE NAV MARGIN: the reference copy at the catalog's clean site, then the target against it triangle for triangle
    points = [pt for pts in ground.values() for pt in pts]
    ref_cell = tuple(int(v) for v in prefab["fingerprint_cell"])
    ref = stage(prefab, ref_cell, game=game, keep=True)
    try:
        if ref["fingerprint"] != prefab["fingerprint"]:
            raise PrefabRefused(f"prefab {name!r}'s reference copy at its catalog site {ref_cell} is NOT the catalog's "
                                f"land: a verb it rides changed its bytes -- a regression to find; nothing written")
        mask = margin_mask(points, cell)
        tgt = fingerprint(staged["root"], cell, staged["blocks"], mask_tri=mask)
        want = fingerprint(ref["root"], ref_cell, ref["blocks"], mask_tri=mask)
    finally:
        if ref.get("root"):
            shutil.rmtree(ref["root"], ignore_errors=True)
    if tgt != want:
        raise PrefabRefused(f"prefab {name!r} staged on {cell} differs from the catalog's land OUTSIDE the nav margin "
                            f"of the stock land at {sorted(ground)}: a regression to find; nothing written")
    if staged["nav"]:
        raise PrefabRefused(f"prefab {name!r} staged on {cell} leaves sea the coast-nav stamp would still re-class "
                            f"({staged['nav']}) beside the stock land at {sorted(ground)}; nothing written", ground)
    log(f"site beside stock land {sorted(ground)}: the catalog's land, its sea within {NAV_MARGIN:g}u of that land "
        f"re-classed by the coast-nav stamp")
    return "nav margin: the catalog's land, the margin's classes settled by the stamp"


def place(name: str, cell, mod_folder, *, game=None, dry_run: bool = False, skip_mirror: bool = False,
          catalog=None, stack=None, log=print) -> dict:
    """Place prefab ``name`` with its anchor on block ``cell``: the row check, the clear window, the staging
    identity, then (unless ``dry_run``) the compose into ``mod_folder`` and the identity of what it wrote on both
    discs. Raises :class:`PrefabRefused` before writing anything on any of the first three. ``stack`` = the FolderNames
    roots (default: the install's own -- pass ``()`` only for a folder that will never be promoted into the live map,
    such as a test's)."""
    from .. import config
    from .render import game_stack
    prefab = get(name, catalog)
    cell = (int(cell[0]) % 24, int(cell[1]))
    if not prefab.get("fingerprint") or not prefab.get("footprint"):
        raise PrefabRefused(f"prefab {name!r} has no fingerprint/footprint yet: take them with "
                            f"`world-prefab {name} --fingerprint --cell BX,BY` and write them into the catalog")
    check_rows_on_map(prefab, cell)
    game_path = config.find_game_path(game)
    mod_root = game_path / mod_folder
    blockers = window_blockers(prefab, cell, mod_root, stack=game_stack(game_path) if stack is None else stack)
    if blockers["target"]:
        raise PrefabRefused(f"the target folder already holds land the prefab would read, cover or border at "
                            f"{sorted(blockers['target'])}: the staged bytes could not stand for these",
                            blockers["target"])
    for folder, hit in blockers["stack"].items():
        raise PrefabRefused(f"{folder} (in the FolderNames stack) holds overrides in or beside the prefab's footprint "
                            f"at {sorted(hit)}", hit)
    if prefab["status"] != "qualified":
        log(f"CANDIDATE: {name!r} has not been walked in game yet -- walk its rim and every carry, then mark it "
            f"qualified in the catalog.")
    staged = stage(prefab, cell, game=game, keep=True)
    try:
        tier = _identity(prefab, name, cell, staged, game=game, log=log)
        report = {"name": name, "cell": list(cell), "status": prefab["status"], "staged": staged["fingerprint"],
                  "footprint": staged["footprint"], "identity": tier, "dry_run": dry_run, "written": None}
        log(f"staged on {cell}: {tier} ({len(staged['blocks'])} blocks)")
        if dry_run:
            return report
        _compose(mod_root, expand(prefab, cell), game=game, skip_mirror=skip_mirror)
        report["written"] = fingerprint(mod_root, cell, staged["blocks"])
        if report["written"] != staged["fingerprint"]:
            raise PrefabRefused(f"prefab {name!r} was WRITTEN into {mod_folder} but its bytes there are not the staged "
                                f"ones (fingerprint {report['written'][:12]}): IDENTITY BROKEN after the write -- undo "
                                f"it through the draft (World tab) or the files' ledger, never by hand copy")
        stamped = stamped_nav(prefab)
        left = nav_settled(mod_root, staged["blocks"], policy=nav_policy(prefab), game=game) if stamped else {}
        if left:
            raise PrefabRefused(f"prefab {name!r} was WRITTEN into {mod_folder} but the coast-nav stamp would still "
                                f"re-class its sea there ({left}) -- undo it through the draft or the ledger, never by "
                                f"hand copy")
        if not skip_mirror:
            # THE DISC-4 HALF (deep dive C14): the player sees disc 4's copy from scenario 11090 on. The mirror copies
            # an open-ocean cell verbatim, so the copy must be the staged land; a held-back or replayed cell is not.
            report["written_disc4"] = fingerprint(mod_root, cell, staged["blocks"], disc=4)
            left4 = nav_settled(mod_root, staged["blocks"], disc=4, policy=nav_policy(prefab),
                                game=game) if stamped else {}
            if report["written_disc4"] != staged["fingerprint"] or left4:
                raise PrefabRefused(f"prefab {name!r} was written on disc 1 as staged, but its DISC-4 copy in "
                                    f"{mod_folder} is other land (fingerprint {report['written_disc4'][:12]}"
                                    + (f", navigation unsettled {left4}" if left4 else "") + "): the mirror held a "
                                    f"cell back or replayed it on disc 4's own ground. Disc 4 (scenario 11090+) would "
                                    f"show a different or missing island -- undo through the draft or the ledger, "
                                    f"never by hand copy")
        log(f"placed {name!r} on block {cell}: {len(staged['blocks'])} blocks, the staged land"
            + ("" if skip_mirror else " on disc 1 and disc 4"))
        return report
    finally:
        if staged.get("root"):
            shutil.rmtree(staged["root"], ignore_errors=True)
