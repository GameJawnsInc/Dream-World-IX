"""Landmass PREFABS (rung P1, studies/overworld-editor/PREFABS.md): a frozen composition stamped anywhere it is lawful.

A prefab is a ``world-fuse`` recipe written RELATIVE to an anchor block: one plain ``[[island]]`` mint plus carried
relief (``[[mountain]]`` / ``[[forest]]`` / ``[[hill]]``), every centre an offset from the anchor block's frame origin
(the corner the prefab frame measures from: ``(64 * bx, -64 * (by + 1))``, i.e. ``64 * floor(x / 64)`` and
``64 * floor(z / 64)``). Placing it on block ``(BX, BY)`` shifts every row by whole blocks and turns on the prefab
frame (rung P0) for the rows that take it, so the land written is the land that was walked, shifted.

THE IDENTITY IS THE CONTRACT. Each catalog entry carries the FINGERPRINT of its disc-1 files, block-relative, taken by
:func:`fingerprint` on a clean staging folder. :func:`place` composes the prefab in a staging folder first and
refuses unless that fingerprint matches the catalog, so a regression in any verb it rides refuses at the call site
instead of shipping different land under a walked name. Only then does it compose into the target -- through the
verbs' own gates, never by copying staged files (THE LEDGER TRAVELS WITH THE BYTES) -- and fingerprints what it
wrote there too.

THE CLEAR WINDOW. The staged bytes stand for the target's only if the target gives the verbs the same inputs: stock
open ocean (the island's own gate) and NO deployed land the relief verbs would read. So the target folder must hold
no override in the prefab's footprint or in any relief row's read window, and no folder in the install's FolderNames
stack may hold one in the footprint (it would stand over, or under, the new land).

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
#: The tables a prefab may hold: the mint and the carries measured under a shift (PREFABS.md).
PREFAB_TABLES = ("island", "transplant", "mountain", "forest", "hill")
#: The BASE a prefab stands on (exactly one, the first row): a minted island, or a walked stock carry unit placed by
#: ``cell`` (its rect's anchor block, as an offset from the prefab's anchor). A transplant carries its stock sea WITH
#: its stock navigation classes (nothing re-stamps them), so its fingerprint keeps them and no nav check runs.
BASE_TABLES = ("island", "transplant")
#: The tables whose rows take the prefab frame (P0); the forest and the hill measured identical without it.
FRAMED_TABLES = ("island", "mountain")
STATUSES = ("candidate", "qualified")
BLOCK = 64.0
_DEFAULT_REACH = 96.0
#: THE NAV MARGIN (measured 2026-11-08): the coast-nav stamp classes a sea triangle by the ground within
#: ``coastnav.FRINGE_R`` (16u) of its CENTROID, and every centroid of the prefab's sea lies inside the footprint, so
#: STOCK ground within 16u outside the footprint changes the prefab's own sea bytes (anchored at (0,12), 9 Sea4 tris
#: in the footprint's corner became near-shore 53 beside the stock land of (22,13)/(22,14); the fingerprint caught
#: it). The stamp samples an 18u margin, but only ground within 16u of a centroid decides a class. Placement refuses
#: such a site.
NAV_MARGIN = 16.0
#: The staging compose is the EXACT oracle for it (the stamp reads stock neighbours there too); a centroid sits a little
#: inside the footprint, so ground near the margin's edge may change nothing (the (21,1) placement measured identical
#: beside stock ground 15u out). :func:`stock_land_near` is therefore the DIAGNOSIS of a staged mismatch, not a gate.
_FILE = re.compile(r"^Block\[(\d+)\]\[(\d+)\] (\w+)\.(ff9mesh|txt)$")


class PrefabRefused(ValueError):
    """A place or check that refuses; ``where`` = the blocks (wrapped labels) it refuses over, if any."""

    def __init__(self, msg: str, where=()):
        super().__init__(msg)
        self.where = sorted(where)


# ---------------------------------------------------------------- the catalog
def load_catalog(path=None) -> list:
    """Every ``[[prefab]]`` in the catalog TOML, validated: unique names, a known status, a first ``[[island]]`` row
    with an explicit seed (the frame refuses without one), only :data:`PREFAB_TABLES`, a relative ``center`` on every
    row, and no ``prefab_frame`` written by hand (placement sets it)."""
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
        out.append(p)
    return out


def get(name: str, path=None) -> dict:
    for p in load_catalog(path):
        if p["name"] == name:
            return p
    raise PrefabRefused(f"no prefab named {name!r} (have: {', '.join(p['name'] for p in load_catalog(path))})")


# ---------------------------------------------------------------- the frame
def origin(cell) -> tuple:
    """The frame origin of anchor block ``cell = (bx, by)``: its corner at the lowest x and z."""
    bx, by = int(cell[0]), int(cell[1])
    return BLOCK * bx, -BLOCK * (by + 1)


def expand(prefab: dict, cell) -> list:
    """The prefab's rows placed on anchor block ``cell``: absolute centres, ``step = N`` in catalog order, and the
    prefab frame on the rows that take it. Each row keeps its ``table`` key (``recipe.dumps`` / ``doc_for``)."""
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


# ---------------------------------------------------------------- the fingerprint
def _f32(v) -> float:
    import struct
    return struct.unpack("<f", struct.pack("<f", float(v)))[0]


#: The parts the coast-nav stamp classes (``coastnav.SEA_PARTS``) and the classes it writes (``coastnav.WATER``).
_NAV_PARTS = ("Sea1", "Sea2", "Sea3", "Sea4", "Sea5")
_NAV_WATER = {53, 54, 55, 56, 57}


def mesh_digest(path, *, mask_nav: bool = False) -> str:
    """The triangles of one ``.ff9mesh``, order-free and winding-kept (see the module docstring). ``mask_nav`` blanks
    the navigation class of every water vertex (tangent.x bits 2-7 when they hold a water topograph): THE NAV MARGIN
    makes those classes a function of the SITE (stock land within 16u), so the catalog names the land without them and
    :func:`nav_settled` checks them against the stamp at each site instead."""
    from .mesh import read_ff9mesh
    m = read_ff9mesh(path)
    V, U, T, N, I = m["verts"], m["uvs"], m["tangents"], m["normals"], m["indices"]

    def tan(i):
        t = [_f32(c) for c in T[i]]
        if mask_nav:
            ix = int(round(t[0]))
            if ((ix & 0xFC) >> 2) in _NAV_WATER:
                t[0] = float(ix & ~0xFC)
        return tuple(t)

    def corner(i):
        return (tuple(_f32(c) for c in V[i]) + tuple(_f32(c) for c in U[i]) + tan(i)
                + tuple(round(_f32(c), 6) + 0.0 for c in N[i]))
    tris = []
    for k in range(0, len(I) - len(I) % 3, 3):
        c = [corner(i) for i in I[k:k + 3]]
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


def fingerprint(mod_root, cell, blocks, *, disc: int = 1, mask_nav: bool = True) -> str:
    """One hash over every override file of disc ``disc`` at ``blocks`` (wrapped labels), keyed by the block's offset
    from ``cell`` and the part: meshes by :func:`mesh_digest` (the sea parts with their navigation classes masked),
    sidecars (``Donor.txt``) by their bytes. The catalog names disc 1's; a placement's disc-4 copy must hash the same
    (the mirror copies open-ocean cells verbatim)."""
    rows = []
    for label in sorted(blocks):
        rel = rel_block(label, cell)
        for p in _block_files(mod_root, label, disc):
            name = _FILE.match(p.name)[3]
            part = name + "." + _FILE.match(p.name)[4]
            dig = (mesh_digest(p, mask_nav=mask_nav and name in _NAV_PARTS) if p.suffix == ".ff9mesh"
                   else hashlib.sha256(p.read_bytes()).hexdigest())
            rows.append(f"{rel[0]},{rel[1]}|{part}|{dig}")
    return hashlib.sha256("\n".join(sorted(rows)).encode()).hexdigest()


def nav_settled(mod_folder, blocks, *, disc: int = 1, policy: str = "land-anywhere", game=None) -> dict:
    """The coast-nav stamp's own verdict on ``blocks``' sea, read-only: ``{}`` when every water vertex already holds
    the class the stamp would write AT THIS SITE (its stock neighbours included), else ``{class: vertex count}``
    still to change. The fingerprint masks these classes; this is what keeps them honest."""
    from . import coastnav as CN
    out = CN.stamp(str(mod_folder), disc=disc, cells=sorted(blocks), policy=policy, deploy=False, game=game)
    return dict(out.get("totals") or {})


# ---------------------------------------------------------------- the clear window
def window_blockers(prefab: dict, cell, mod_root, *, stack=None) -> dict:
    """Why the target cannot stand for the staging folder: ``{"target": {label, ...}, "stack": {folder: {label}}}``,
    empty sets when the window is clear. ``stack`` = the install's FolderNames roots (other folders are judged on
    the footprint only: the relief verbs read the target folder alone). Both disc trees count: a placement writes
    disc 4 too (the auto-mirror), so land already there is as much in the way as disc 1's."""
    rows = expand(prefab, cell)
    foot = {label_of(r, cell) for r in prefab.get("footprint") or ()}
    want = foot | _ring(foot) | read_windows(rows)          # the ring: the nav stamp reads 34u past the footprint
    have = written_blocks(mod_root, 1) | written_blocks(mod_root, 4)
    out = {"target": want & have, "stack": {}}
    for root in stack or ():
        if Path(root).resolve() == Path(mod_root).resolve():
            continue
        hit = foot & (written_blocks(root, 1) | written_blocks(root, 4))
        if hit:
            out["stack"][Path(root).name] = hit
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
        dx = abs((x - (x0 + BLOCK / 2) + 768.0) % 1536.0 - 768.0) - BLOCK / 2
        dz = abs(z - (z1 - BLOCK / 2)) - BLOCK / 2
        best = min(best, math.hypot(max(dx, 0.0), max(dz, 0.0)))
    return best


def stock_land_near(prefab: dict, cell, *, game=None, discs=(1, 4)) -> set:
    """The ring blocks (wrapped labels) holding STOCK ground within :data:`NAV_MARGIN` of the footprint, on any of
    ``discs`` (disc 4 receives disc 1's stamped sea as a copy, so its own nearby land must not differ either).

    It asks the coast-nav stamp's OWN ground query (``coastnav._query_top`` over a stock-only loader: the engine's
    up-facing filter and IDALL skip set) at the stamp's own 2u sample grid, so it sees exactly the ground the stamp
    would. A first version counted every non-water triangle and refused sites whose identity measured clean."""
    from . import coastnav as CN
    foot = {label_of(r, cell) for r in prefab.get("footprint") or ()}
    hit = set()
    for disc in discs:
        loader = CN._Loader("__ff9mapkit_stock_only__", disc, game)
        for label in sorted(_ring(foot) - hit):
            x0, z1 = BLOCK * label[0], -BLOCK * label[1]
            found = False
            for i in range(int(BLOCK / CN.STEP_G) + 1):
                x = x0 + i * CN.STEP_G
                for j in range(int(BLOCK / CN.STEP_G) + 1):
                    z = z1 - j * CN.STEP_G
                    if _dist_to_blocks(x, z, foot) > NAV_MARGIN:
                        continue
                    g = CN._query_top(loader, x, z)
                    if g is not None and g[1] not in CN.WATER:
                        found = True
                        break
                if found:
                    break
            if found:
                hit.add(label)
    return hit


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


def stamped_nav(prefab: dict) -> bool:
    """Whether the prefab's sea navigation is STAMPED at placement (a minted island: site-dependent, masked in the
    fingerprint and checked by :func:`nav_settled`) rather than carried (a transplant: stock bytes, fingerprinted)."""
    return prefab["rows"][0]["table"] == "island" and prefab["rows"][0].get("coastnav", True) is not False


def nav_policy(prefab: dict) -> str:
    """The landability policy the prefab's island row stamps its sea with."""
    return str(prefab["rows"][0].get("coastnav_policy", "land-anywhere"))


def stage(prefab: dict, cell, *, game=None) -> dict:
    """Compose the prefab on ``cell`` in a fresh staging folder (outside the install, nothing mirrored) and return
    ``{"fingerprint", "footprint" (relative, sorted), "blocks" (labels)}``. The folder is removed afterwards."""
    tmp = Path(tempfile.mkdtemp(prefix="ff9-prefab-"))
    try:
        _compose(tmp, expand(prefab, cell), game=game, skip_mirror=True)
        labels = written_blocks(tmp)
        stamped = stamped_nav(prefab)
        return {"fingerprint": fingerprint(tmp, cell, labels, mask_nav=stamped),
                "footprint": sorted(rel_block(b, cell) for b in labels), "blocks": sorted(labels),
                "nav": nav_settled(tmp, labels, policy=nav_policy(prefab), game=game) if stamped else {}}
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def place(name: str, cell, mod_folder, *, game=None, dry_run: bool = False, skip_mirror: bool = False,
          catalog=None, stack=None, log=print) -> dict:
    """Place prefab ``name`` with its anchor on block ``cell``: the row check, the clear window, the staging
    identity, then (unless ``dry_run``) the compose into ``mod_folder`` and the identity of what it wrote.
    Raises :class:`PrefabRefused` before writing anything on any of the first three. ``stack`` = the FolderNames
    roots judged on the footprint (default: the install's own -- pass ``()`` only for a folder that will never be
    promoted into the live map, such as a test's)."""
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
        raise PrefabRefused(f"the target folder already holds land the prefab would read or cover at "
                            f"{sorted(blockers['target'])}: the staged bytes could not stand for these",
                            blockers["target"])
    for folder, hit in blockers["stack"].items():
        raise PrefabRefused(f"{folder} (in the FolderNames stack) holds overrides in the prefab's footprint at "
                            f"{sorted(hit)}", hit)
    if prefab["status"] != "qualified":
        log(f"CANDIDATE: {name!r} has not been walked in game yet -- walk its rim and every carry, then mark it "
            f"qualified in the catalog.")
    staged = stage(prefab, cell, game=game)
    report = {"name": name, "cell": list(cell), "status": prefab["status"], "staged": staged["fingerprint"],
              "footprint": staged["footprint"], "dry_run": dry_run, "written": None}
    if staged["footprint"] != sorted(tuple(b) for b in prefab["footprint"]):
        raise PrefabRefused(f"prefab {name!r} staged on {cell} covers {staged['footprint']}, the catalog says "
                            f"{sorted(tuple(b) for b in prefab['footprint'])}: IDENTITY BROKEN, nothing written")
    if staged["fingerprint"] != prefab["fingerprint"]:
        near = stock_land_near(prefab, cell, game=game)
        why = (f"stock land within {NAV_MARGIN:g}u of the footprint at {sorted(near)} -- THE NAV MARGIN: the coast-nav "
               f"stamp classes the prefab's own sea against it, so this site cannot carry the walked bytes; pick a "
               f"site in open water" if near else
               "a verb it rides changed its bytes (no stock land is near, so this is a regression to find)")
        raise PrefabRefused(f"prefab {name!r} staged on {cell} is NOT the land its catalog entry names "
                            f"(fingerprint {staged['fingerprint'][:12]} vs {prefab['fingerprint'][:12]}): {why}; "
                            f"nothing written", near)
    if staged["nav"]:
        raise PrefabRefused(f"prefab {name!r} staged on {cell} leaves sea the coast-nav stamp would still re-class "
                            f"({staged['nav']}): its navigation is not settled for this site; nothing written")
    log(f"staged on {cell}: identical to the catalog ({len(staged['blocks'])} blocks), navigation settled")
    if dry_run:
        return report
    rows = expand(prefab, cell)
    _compose(mod_root, rows, game=game, skip_mirror=skip_mirror)
    stamped = stamped_nav(prefab)
    report["written"] = fingerprint(mod_root, cell, staged["blocks"], mask_nav=stamped)
    if report["written"] != prefab["fingerprint"]:
        raise PrefabRefused(f"prefab {name!r} was WRITTEN into {mod_folder} but its bytes there are not the staged "
                            f"ones (fingerprint {report['written'][:12]}): IDENTITY BROKEN after the write -- undo it "
                            f"through the draft (World tab) or the files' ledger, never by hand copy")
    left = nav_settled(mod_root, staged["blocks"], policy=nav_policy(prefab), game=game) if stamped else {}
    if left:
        raise PrefabRefused(f"prefab {name!r} was WRITTEN into {mod_folder} but the coast-nav stamp would still re-class "
                            f"its sea there ({left}) -- undo it through the draft or the ledger, never by hand copy")
    if not skip_mirror:
        # THE DISC-4 HALF (deep dive C14): the player sees disc 4's copy from scenario 11090 on. The mirror copies an
        # open-ocean cell verbatim, so the copy must name the same land; a held-back or replayed cell does not.
        report["written_disc4"] = fingerprint(mod_root, cell, staged["blocks"], disc=4, mask_nav=stamped)
        if report["written_disc4"] != prefab["fingerprint"]:
            raise PrefabRefused(f"prefab {name!r} was written on disc 1 as the catalog names it, but its DISC-4 copy "
                                f"in {mod_folder} is other land (fingerprint {report['written_disc4'][:12]}): the "
                                f"mirror held a cell back or replayed it on disc 4's own ground. Disc 4 (scenario "
                                f"11090+) would show a different or missing island -- undo through the draft or the "
                                f"ledger, never by hand copy")
    log(f"placed {name!r} on block {cell}: {len(staged['blocks'])} blocks, identical to the catalog"
        + ("" if skip_mirror else " on disc 1 and disc 4"))
    return report
