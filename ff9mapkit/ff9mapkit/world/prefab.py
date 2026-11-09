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

THE QUARTER TURN (rung P5, PREFABS.md). ``turn = 90 | 180 | 270`` places the prefab's WALKED land turned, never a
re-mint: the prefab is composed at turn 0 at its catalog site (``fingerprint_cell``) and held to its catalog
fingerprint, then every file of it is turned block by block -- each block moves to its turned place and its
block-local content turns about the block centre (``transplant._rot_xz``), so whole blocks map onto whole blocks, the
4u lattice onto itself, and every tile into its own rotation variant (transplant's in-game-proven law: the mains
anti-tiling and the Wang strips already use all four). Positions turn; normals turn except the sea's (a uniform
constant every sea tile shares, ``transplant.LAND_PARTS``); uvs and tangents (the IDALL) are kept. The turned files
are written through the kit's ledgered writers (``mesh.deploy_override`` / ``deploy_donor_sidecar``), then the
coast-nav stamp and the disc-4 mirror run as for every world writer. IDENTITY, TURNED: the written land must be the
catalog's land with exactly that turn applied (:func:`fingerprint` ``turn=``) -- the two tiers above, unchanged --
so one walked fingerprint names all four turns. Rotation is proper (no mirror), so winding and the mains' handedness
are kept. A turn refuses when a block's ``Donor.txt`` prefab would render a part the prefab does not override (that
part would ride the donor prefab UNTURNED), and the catalog's ``turns`` lists the turns a prefab allows
(default ``[0]``).
"""
from __future__ import annotations

import hashlib
import math
import re
import shutil
import tempfile
import time
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
#: The quarter turns (degrees); 0 is the walked land as it is.
TURNS = (0, 90, 180, 270)


class PrefabRefused(ValueError):
    """A place or check that refuses; ``where`` = the blocks (wrapped labels) it refuses over, if any; ``gate`` = which
    law refused (the World tab's card names it): catalog, rows, window, identity, nav, written, disc4, compose."""

    def __init__(self, msg: str, where=(), gate: str = "prefab"):
        super().__init__(msg)
        self.where = sorted(where)
        self.gate = gate


# ---------------------------------------------------------------- the catalog
def user_catalog() -> Path:
    """The USER's catalog (rung P6, Save as prefab): ``prefabs.toml`` in the kit's per-user config folder, beside the
    prefs -- never the package's own data (read-only on some installs, wiped on upgrade). Read after the kit's."""
    from .. import provision
    return provision._user_dir("config") / "prefabs.toml"


def catalog_paths(path=None) -> list:
    """The catalog files :func:`load_catalog` reads: ``path`` alone when given, else the kit's and then the user's
    (when it exists)."""
    if path is not None:
        return [Path(path)]
    user = user_catalog()
    return [CATALOG] + ([user] if user.is_file() else [])


_USER_PROBLEMS: list = []


def load_catalog(path=None) -> list:
    """Every ``[[prefab]]`` in the catalog TOML(s), validated: unique names (across the kit's catalog and the user's),
    a known status, exactly one BASE row first (an island with an explicit seed -- the frame refuses without one -- or
    a transplant with ``cell`` and ``donor``), only :data:`PREFAB_TABLES`, a relative ``center`` on every other row,
    no ``near`` / ``prefab_frame`` / ``step`` written by hand (placement sets them), and a ``fingerprint_cell`` beside
    any island prefab's fingerprint. ``path`` reads that one file, strictly; ``None`` reads the kit's catalog strictly
    and then the USER's leniently (:func:`catalog_problems`).

    THE USER'S CATALOG NEVER TAKES DOWN THE KIT'S (review P6): a user file that does not parse, an entry that breaks a
    rule, or a name the kit's catalog (or an earlier user entry) already holds is SKIPPED and named in
    :func:`catalog_problems` -- never raised -- so a hand edit, a BOM, or a later kit prefab of the same name costs that
    one entry, not every prefab. The kit's names win."""
    seen: set = set()
    if path is not None:
        return _load_one(Path(path), seen)
    out = _load_one(CATALOG, seen)
    problems: list = []
    user = user_catalog()
    if user.is_file():
        out += _load_one(user, seen, problems=problems)
    _USER_PROBLEMS[:] = problems
    return out


def catalog_problems() -> list:
    """What the last read of the USER's catalog skipped, in words (empty: every entry loaded)."""
    load_catalog()
    return list(_USER_PROBLEMS)


def _load_one(cat: Path, seen: set, *, problems=None) -> list:
    """One catalog file. ``problems`` given = LENIENT (the user's): what breaks a rule is skipped and appended there."""
    try:
        doc = tomllib.loads(Path(cat).read_text(encoding="utf-8-sig"))   # (a BOM from a hand edit is not an error)
    except (tomllib.TOMLDecodeError, UnicodeDecodeError) as e:
        if problems is None:
            raise ValueError(f"{cat}: not a readable prefab catalog ({e})") from e
        problems.append(f"{cat}: not a readable prefab catalog ({e}); none of its prefabs are offered")
        return []
    out = []
    for i, p in enumerate(doc.get("prefab", ())):
        try:
            _check_entry(cat, i, p, seen)
        except ValueError as e:
            if problems is None:
                raise
            problems.append(f"{e} -- skipped")
            continue
        seen.add(p["name"])
        out.append(p)
    return out


def _check_entry(cat, i: int, p: dict, seen: set) -> None:
    """One ``[[prefab]]`` table's rules (:func:`load_catalog`); raises ValueError naming the entry."""
    name = p.get("name")
    where = f"{Path(cat).name} [[prefab]] #{i} ({name!r})"
    if not name or name in seen:
        raise ValueError(f"{where}: needs a unique name" + (" (the kit's catalog or an earlier entry has it)"
                                                            if name else ""))
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
    turns = p.get("turns", [0])
    if not turns or any(t not in TURNS for t in turns) or 0 not in turns or len(set(turns)) != len(turns):
        raise ValueError(f"{where}: turns = a list of distinct quarter turns from {TURNS}, 0 among them")
    if set(turns) != {0} and (fc is None or len(fc) != 2):
        raise ValueError(f"{where}: a turned placement is the land composed at its catalog site and turned, so a "
                         f"prefab that turns names that site: fingerprint_cell = [bx, by]")
    if any(t not in turns or t == 0 for t in p.get("walked_turns", ())):
        raise ValueError(f"{where}: walked_turns lists turns other than 0 that the prefab allows ({turns})")


def get(name: str, path=None) -> dict:
    for p in load_catalog(path):
        if p["name"] == name:
            return p
    raise PrefabRefused(f"no prefab named {name!r} (have: {', '.join(p['name'] for p in load_catalog(path))})",
                        gate="catalog")


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


def read_windows(rows, *, clip: bool = True) -> set:
    """Every block (wrapped label) a relief row reads: its centre +- its reach (the hill's own rule:
    ``max(96, radius + 10)``), clipped to the map's rows (``clip=False`` keeps off-map rows, for a turn to map)."""
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
                if 0 <= by < GRID_ROWS or not clip:
                    out.add((wrap_block_col(bx), by))
    return out


def reads(prefab: dict, cell) -> set:
    """The relief rows' read windows for the prefab on anchor ``cell`` -- for a TURNED view (:func:`turned`), the walked
    land's windows turned with it (its clear window is the turn of the walked one's), clipped to the map's rows."""
    from .mesh import GRID_ROWS
    win = read_windows(expand(prefab, cell), clip=not turn_of(prefab))
    if turn_of(prefab):
        win = {label_of(turn_rel(prefab, rel_block(b, cell), turn_of(prefab)), cell) for b in win}
    return {b for b in win if 0 <= b[1] < GRID_ROWS}


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


# ---------------------------------------------------------------- the quarter turn
def turns_of(prefab: dict) -> tuple:
    """The quarter turns the catalog allows the prefab (default turn 0 only: a prefab turns once its entry says so,
    measured at its catalog site)."""
    return tuple(int(t) for t in prefab.get("turns", (0,)))


def _steps(turn) -> int:
    t = int(turn)
    if t not in TURNS:
        raise PrefabRefused(f"turn must be one of {TURNS} (quarter turns keep the 4u lattice and every tile lawful; "
                            f"other angles do not), not {turn!r}", gate="turn")
    return t // 90


def _rot_block(d, n: int) -> tuple:
    """Block offset ``d`` turned ``n`` quarter turns about the frame origin (the block-index form of
    ``(x, z) -> (-z, x)``; z grows as the row index falls)."""
    dx, dy = int(d[0]), int(d[1])
    for _ in range(n % 4):
        dx, dy = dy, -dx
    return dx, dy


def _source_foot(prefab: dict) -> list:
    return [tuple(int(v) for v in b) for b in (prefab.get("source_footprint") or prefab.get("footprint") or [(0, 0)])]


def _turn_shift(prefab: dict, n: int) -> tuple:
    """The whole-block shift that puts the turned footprint's bounding rect where the walked one's starts."""
    foot = _source_foot(prefab)
    rot = [_rot_block(b, n) for b in foot]
    return (min(b[0] for b in foot) - min(b[0] for b in rot), min(b[1] for b in foot) - min(b[1] for b in rot))


def turn_rel(prefab: dict, rel, turn) -> tuple:
    """Where the block at offset ``rel`` (from the anchor, in the walked land) lands in the land turned ``turn``:
    turned about the anchor, then shifted so the footprint's bounding rect starts at the same offset."""
    n = _steps(turn)
    if n == 0:
        return int(rel[0]), int(rel[1])
    r = _rot_block(rel, n)
    s = _turn_shift(prefab, n)
    return r[0] + s[0], r[1] + s[1]


def turned(prefab: dict, turn) -> dict:
    """The prefab as it lands turned ``turn``: the same rows (they compose the walked land at its catalog site), the
    turned ``footprint``, and ``turn`` / ``source_footprint`` for every frame read. Turn 0 is the entry itself."""
    n = _steps(turn)
    if n == 0:
        return prefab
    out = dict(prefab)
    out["source_footprint"] = [list(b) for b in _source_foot(prefab)]
    out["footprint"] = sorted([list(turn_rel(prefab, b, turn)) for b in _source_foot(prefab)])
    out["turn"] = int(turn)
    return out


def turn_of(prefab: dict) -> int:
    return int(prefab.get("turn", 0))


def view_for(name: str, turn=0, catalog=None) -> dict:
    """The catalog entry ``name`` as it lands turned ``turn`` (:func:`turned`): what a ``[[prefab]]`` row's footprint,
    centre and clear window are read from."""
    return turned(get(name, catalog), int(turn or 0))


def _local_turn(x: float, z: float, n: int) -> tuple:
    """A block-LOCAL point (x 0..64, z -64..0) turned ``n`` quarter turns about the block centre -- exactly
    ``transplant._rot_xz``, one step ``(x, z) -> (-z, x - 64)``, in ITS arithmetic (about the centre, so a 0 comes out
    0.0 and never -0.0: the bytes are transplant's bit for bit, and the identity's digest -- which turns by
    ``_rot_xz`` itself -- hashes the exact floats the writer wrote; measured: the bare ``-z`` form wrote -0.0 there)."""
    dx, dz = x - 32.0, z + 32.0
    for _ in range(n % 4):
        dx, dz = -dz, dx
    return 32.0 + dx, -32.0 + dz


def _dir_turn(nx: float, nz: float, n: int) -> tuple:
    for _ in range(n % 4):
        nx, nz = -nz, nx
    return nx, nz


def _turns_normals(part: str) -> bool:
    """Whether ``part``'s normals turn: the sea's are one uniform constant every tile shares (transplant's law)."""
    return not part.lower().startswith("sea")


def turn_point(x: float, z: float, prefab: dict, cell, turn) -> tuple:
    """World ``(x, z)`` in the walked land anchored on ``cell`` -> where it lands turned ``turn`` (the same rigid map
    the files take; unwrapped, for the ghost and the words)."""
    n = _steps(turn)
    if n == 0:
        return float(x), float(z)
    ox, oz = origin(cell)
    d0 = _source_foot(prefab)[0]
    d1 = turn_rel(prefab, d0, turn)

    def mid(d):                                          # a block's centre, frame-relative
        return BLOCK * d[0] + 32.0, 32.0 - BLOCK * d[1]
    c0, c1 = mid(d0), mid(d1)
    rx, rz = x - ox - c0[0], z - oz - c0[1]
    for _ in range(n):
        rx, rz = -rz, rx
    return ox + c1[0] + rx, oz + c1[1] + rz


# ---------------------------------------------------------------- the fingerprint
def _f32(v) -> float:
    import struct
    return struct.unpack("<f", struct.pack("<f", float(v)))[0]


def mesh_digest(path, *, mask_tri=None, label=None, cell=None, steps: int = 0, part: str = "") -> str:
    """The triangles of one ``.ff9mesh``, order-free and winding-kept (see the module docstring). ``mask_tri`` (with
    the file's block ``label`` and the anchor ``cell``) is a predicate on a triangle's centroid relative to the frame
    origin (:func:`rel_point`): where it holds, the navigation class of the triangle's WATER vertices is blanked
    (tangent.x bits 2-7 when they hold a water topograph) -- the nav-margin triangles a site's stamp decides.
    ``steps`` digests the triangles as they are TURNED that many quarter turns (THE QUARTER TURN: positions about the
    block centre, the normals unless ``part`` is a sea) -- then ``label`` is the block the turned file lands on. The
    turn here is TRANSPLANT'S OWN (``transplant._rot_xz`` / ``_rot_dir``), not the writer's helpers, so the identity
    is not the writer checking itself (review P5)."""
    from .extract import block_world_origin
    from .mesh import read_ff9mesh
    m = read_ff9mesh(path)
    V, U, T, N, I = m["verts"], m["uvs"], m["tangents"], m["normals"], m["indices"]
    if steps % 4:
        from .transplant import LAND_PARTS, _rot_dir, _rot_xz
        V = [(lambda x, z, y: (x, y, z))(*_rot_xz(v[0], v[2], steps % 4), v[1]) for v in V]
        if N and (part.lower() in LAND_PARTS or not part.lower().startswith("sea")):
            N = [(lambda nx, nz, ny: (nx, ny, nz))(*_rot_dir(n[0], n[2], steps % 4), n[1]) for n in N]
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


def fingerprint(mod_root, cell, blocks, *, disc: int = 1, mask_tri=None, turn: int = 0, prefab=None,
                to_cell=None) -> str:
    """One hash over every override file of disc ``disc`` at ``blocks`` (wrapped labels), keyed by the block's offset
    from ``cell`` and the part: meshes by :func:`mesh_digest`, sidecars (``Donor.txt``) by their bytes. ``mask_tri``
    blanks the class of the nav-margin triangles of the SEA parts only (see :func:`mesh_digest`).

    ``turn`` (with the ``prefab`` and the anchor ``to_cell`` it lands on) hashes the land as it would be TURNED and
    placed there: each block keyed by its turned offset, its triangles turned (THE QUARTER TURN), ``mask_tri`` judged
    on the turned centroids -- so it equals the plain fingerprint of a correctly turned placement on ``to_cell``."""
    n = _steps(turn)
    if n and prefab is None:
        raise ValueError("a turned fingerprint needs the prefab (its footprint fixes the turn's shift)")
    rows = []
    for label in sorted(blocks):
        rel = rel_block(label, cell)
        out_cell = cell
        if n:
            # the block's turned place by the RIGID point map (its centre through turn_point), not the writer's
            # block map (turn_rel): a block map that is not one rigid motion with the content's turn refuses
            out_cell = (int(to_cell[0]) % 24, int(to_cell[1])) if to_cell is not None else cell
            cx, cz = BLOCK * (out_cell[0] + rel[0]) + 32.0, -BLOCK * (out_cell[1] + rel[1]) - 32.0
            tx, tz = turn_point(cx, cz, prefab, out_cell, turn)
            rel = rel_block((math.floor(tx / BLOCK) % 24, math.floor(-tz / BLOCK)), out_cell)
        out_label = label_of(rel, out_cell) if n else label
        for p in _block_files(mod_root, label, disc):
            name = _FILE.match(p.name)[3]
            part = name + "." + _FILE.match(p.name)[4]
            if p.suffix == ".ff9mesh":
                mask = mask_tri if name in _NAV_PARTS else None
                dig = mesh_digest(p, mask_tri=mask, label=out_label, cell=out_cell, steps=n, part=name)
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
    foot = {label_of(r, cell) for r in prefab.get("footprint") or ()}
    near = foot | _ring(foot)
    want = near | reads(prefab, cell)
    have = written_blocks(mod_root, 1) | written_blocks(mod_root, 4)
    out = {"target": want & have, "stack": {}}
    for root in stack or ():
        if Path(root).resolve() == Path(mod_root).resolve():
            continue
        hit = near & (written_blocks(root, 1) | written_blocks(root, 4))
        if hit:
            out["stack"][Path(root).name] = hit
    return out


def footprint_labels(prefab: dict, cell) -> list:
    """The footprint's wrapped block labels on anchor ``cell``, sorted."""
    return sorted(label_of(r, cell) for r in prefab.get("footprint") or ())


def footprint_center(prefab: dict, cell) -> tuple:
    """The world ``(x, z)`` middle of the footprint's bounding rect on anchor ``cell`` (x folded into [0, 1536))."""
    foot = prefab.get("footprint") or [(0, 0)]
    dx0, dx1 = min(int(b[0]) for b in foot), max(int(b[0]) for b in foot) + 1
    dy0, dy1 = min(int(b[1]) for b in foot), max(int(b[1]) for b in foot) + 1
    x = BLOCK * (int(cell[0]) + (dx0 + dx1) / 2.0)
    z = -BLOCK * (int(cell[1]) + (dy0 + dy1) / 2.0)
    return (x % WORLD_W, z)


def check_rows_on_map(prefab: dict, cell) -> None:
    """The footprint must sit on the map's rows (rows do not wrap for writes: the kit's edged-row policy)."""
    from .mesh import GRID_ROWS
    for rel in prefab.get("footprint") or ():
        by = int(cell[1]) + int(rel[1])
        if not 0 <= by < GRID_ROWS:
            raise PrefabRefused(f"prefab {prefab['name']!r} on block {tuple(cell)} reaches row {by}, off the map "
                                f"(rows 0..{GRID_ROWS - 1})", gate="rows")


# ---------------------------------------------------------------- compose + place
def _compose(mod_folder, rows, *, game, skip_mirror: bool, dry_run: bool = False, allow_overwrite: bool = False) -> dict:
    from . import fuse as FU
    out = FU.compose_layout(str(mod_folder), doc_for(rows), game=game, skip_mirror=skip_mirror, dry_run=dry_run,
                            allow_overwrite=allow_overwrite)
    if not out["clean"]:
        bad = [g for g in out["gates"] if not g.get("ok")]
        raise PrefabRefused("a prefab row refused: " + "; ".join(
            f"{g['gate']}: {g.get('error') or g.get('skipped') or g}" for g in bad), gate="compose")
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


def source_cell(prefab: dict) -> tuple:
    """Where a TURNED placement composes the walked land before turning it: the catalog's fingerprint site."""
    fc = prefab.get("fingerprint_cell")
    if fc is None:
        raise PrefabRefused(f"prefab {prefab['name']!r} names no fingerprint_cell: a turned placement composes the "
                            f"walked land at that catalog site first", gate="catalog")
    return int(fc[0]) % 24, int(fc[1])


def _donor_parts(donor, *, game=None) -> set:
    """Every sub-mesh a stock block's prefab carries, on EITHER disc (lower-case bundle names; empty = open ocean):
    the bundle's own list (``extract.block_parts``), never a list of names kept here -- review P5: a hand list missed
    Beach2, Stream, VolcanoCrater/VolcanoLava and disc 4's Sea4f. Both discs, because the mirror copies the Donor.txt
    to disc 4, where the engine resolves it against disc 4's own prefab."""
    from .extract import block_parts
    d = (int(donor[0]), int(donor[1]))
    return set(block_parts(disc=1, game=game).get(d, ())) | set(block_parts(disc=4, game=game).get(d, ()))


def turn_blockers(root, *, game=None) -> dict:
    """``{block: [part, ...]}``: the blocks of a staged folder whose ``Donor.txt`` prefab carries a part (on disc 1 or
    disc 4) the folder does not override. Turned, that part would ride the donor prefab UNTURNED beside the turned land
    (a stock Object, a stream, a sea layer), so a turn refuses there; at turn 0 the verbs chose that donor for exactly
    what it draws."""
    out = {}
    for label in sorted(written_blocks(root)):
        files = _block_files(root, label)
        have = {_FILE.match(p.name)[3].lower() for p in files if p.suffix == ".ff9mesh"}
        for p in files:
            if _FILE.match(p.name)[3] == "Donor":
                donor = tuple(int(v) for v in p.read_text(encoding="utf-8").strip().split(","))
                left = sorted(_donor_parts(donor, game=game) - have)
                if left:
                    out[label] = left
    return out


def _turned_mesh(path, part: str, n: int, label):
    """One staged ``.ff9mesh`` turned ``n`` quarter turns (THE QUARTER TURN), as a BlockMesh on block ``label``."""
    import dataclasses
    from .extract import CH_NRM, CH_POS
    from .mesh import blockmesh_from_ff9mesh
    bm = blockmesh_from_ff9mesh(path, disc=1, x=label[0], y=label[1], part=part)
    chan = dict(bm.chan_arrays)
    out = []
    for v in chan.get(CH_POS) or ():
        x, z = _local_turn(v[0], v[2], n)
        out.append([x, v[1], z])
    chan[CH_POS] = out
    if chan.get(CH_NRM) and _turns_normals(part):
        nr = []
        for v in chan[CH_NRM]:
            nx, nz = _dir_turn(v[0], v[2], n)
            nr.append([nx, v[1], nz])
        chan[CH_NRM] = nr
    return dataclasses.replace(bm, name=f"Block[{label[0]}][{label[1]}] {part}", chan_arrays=chan)


def write_turned(src_root, src_cell, prefab: dict, turn, mod_folder, cell, *, game=None, skip_mirror=False) -> list:
    """Write the walked land staged in ``src_root`` (anchored on ``src_cell``) into ``mod_folder``, TURNED ``turn`` and
    anchored on ``cell``: every file through the kit's ledgered writers, then the coast-nav stamp over the turned sea
    (it decides the classes beside stock land, as for the mint) and the disc-4 mirror. Returns the written paths."""
    from . import discmirror as DM
    from . import mesh as M
    n = _steps(turn)
    written = []
    labels = []
    for label in sorted(written_blocks(src_root)):
        tl = label_of(turn_rel(prefab, rel_block(label, src_cell), turn), cell)
        labels.append(tl)
        for p in _block_files(src_root, label):
            m = _FILE.match(p.name)
            part, ext = m[3], m[4]
            if ext == "txt":
                if part != "Donor":
                    raise PrefabRefused(f"a staged {p.name} is a sidecar the turn does not know how to carry", [label],
                                        gate="turn")
                dx, dy = (int(v) for v in p.read_text(encoding="utf-8").strip().split(","))
                written.append(M.deploy_donor_sidecar(dx, dy, mod_folder=str(mod_folder), disc=1, x=tl[0], y=tl[1],
                                                      game=game))
            else:
                written.append(M.deploy_override(_turned_mesh(p, part, n, tl), mod_folder=str(mod_folder), game=game,
                                                 disc=1, part=part))
    if stamped_nav(prefab):
        from . import coastnav as CN
        CN.stamp(str(mod_folder), disc=1, cells=sorted(labels), policy=nav_policy(prefab), deploy=True, game=game,
                 backup=False, skip_mirror=DM.DEFERRED)
    DM.auto_mirror(written, mod_folder=str(mod_folder), skip_mirror=skip_mirror)
    return written


def stage_turned(prefab: dict, turn, cell, *, game=None) -> dict:
    """A TURNED placement staged: the walked land composed at its catalog site (``source``, kept) and written turned
    onto ``cell`` in a second staging folder. Returns :func:`stage`'s shape plus ``source`` (its own stage dict).
    Both folders are kept; the caller removes them (:func:`_drop`)."""
    src = stage(prefab, source_cell(prefab), game=game, keep=True)
    tmp = Path(tempfile.mkdtemp(prefix="ff9-prefab-turn-"))
    out = {"root": tmp, "source": src}
    try:
        if src["fingerprint"] != prefab["fingerprint"]:
            raise PrefabRefused(f"prefab {prefab['name']!r} composed at its catalog site {source_cell(prefab)} is NOT "
                                f"the land its catalog entry names (fingerprint {src['fingerprint'][:12]} vs "
                                f"{prefab['fingerprint'][:12]}): a verb it rides changed its bytes -- a regression to "
                                f"find; nothing turned, nothing written", gate="identity")
        left = turn_blockers(src["root"], game=game)
        if left:
            raise PrefabRefused(f"prefab {prefab['name']!r} cannot turn: on {sorted(left)} its donor prefab draws "
                                f"{sorted({p for ps in left.values() for p in ps})}, which the prefab does not override, "
                                f"so the engine would draw it UNTURNED beside the turned land", gate="turn")
        write_turned(src["root"], source_cell(prefab), prefab, turn, tmp, cell, game=game, skip_mirror=True)
        labels = written_blocks(tmp)
        out.update({"fingerprint": fingerprint(tmp, cell, labels), "blocks": sorted(labels),
                    "footprint": sorted(rel_block(b, cell) for b in labels),
                    "nav": nav_settled(tmp, labels, policy=nav_policy(prefab), game=game) if stamped_nav(prefab)
                    else {}})
        return out
    except BaseException:
        _drop(out)
        raise


def _drop(staged) -> None:
    """Remove a stage's folders (a turned stage's source too)."""
    if not staged:
        return
    for st in (staged, staged.get("source") or {}):
        if st.get("root"):
            shutil.rmtree(st["root"], ignore_errors=True)


def _identity_turned(view: dict, name: str, cell, staged: dict, *, game, log) -> str:
    """Judge a TURNED staging: the walked land (already held to the catalog at its own site) turned is the want --
    the full fingerprint at a clean site, the nav-margin tier beside stock land (the module docstring)."""
    turn = turn_of(view)
    if staged["footprint"] != sorted(tuple(b) for b in view["footprint"]):
        raise PrefabRefused(f"prefab {name!r} turned {turn} on {cell} covers {staged['footprint']}, the turn of the "
                            f"catalog's footprint is {sorted(tuple(b) for b in view['footprint'])}: IDENTITY BROKEN, "
                            f"nothing written", gate="identity")
    src = staged["source"]
    scell = source_cell(view)
    ground = stock_ground(view, cell, game=game) if stamped_nav(view) else {}
    points = [pt for pts in ground.values() for pt in pts]
    mask = margin_mask(points, cell) if ground else None
    want = fingerprint(src["root"], scell, src["blocks"], turn=turn, prefab=view, to_cell=cell, mask_tri=mask)
    got = fingerprint(staged["root"], cell, staged["blocks"], mask_tri=mask)
    if got != want:
        where = (f"OUTSIDE the nav margin of the stock land at {sorted(ground)}" if ground else "")
        raise PrefabRefused(f"prefab {name!r} turned {turn} on {cell} is NOT the catalog's land turned {where}: the "
                            f"turn moved something it must not -- a regression to find; nothing written",
                            gate="identity")
    if staged["nav"]:
        raise PrefabRefused(f"prefab {name!r} turned {turn} on {cell} leaves sea the coast-nav stamp would still "
                            f"re-class ({staged['nav']}); nothing written", ground, gate="nav")
    if not ground:
        return f"clean site: the catalog's land turned {turn}, the full fingerprint"
    log(f"site beside stock land {sorted(ground)}: the catalog's land turned {turn}, its sea within {NAV_MARGIN:g}u of "
        f"that land re-classed by the coast-nav stamp")
    return f"nav margin: the catalog's land turned {turn}, the margin's classes settled by the stamp"


def _identity(prefab: dict, name: str, cell, staged: dict, *, game, log) -> str:
    """Judge the staged target against the catalog (the two tiers of the module docstring). Returns the tier."""
    if staged["footprint"] != sorted(tuple(b) for b in prefab["footprint"]):
        raise PrefabRefused(f"prefab {name!r} staged on {cell} covers {staged['footprint']}, the catalog says "
                            f"{sorted(tuple(b) for b in prefab['footprint'])}: IDENTITY BROKEN, nothing written",
                            gate="identity")
    ground = stock_ground(prefab, cell, game=game) if stamped_nav(prefab) else {}
    if not ground:
        if staged["fingerprint"] != prefab["fingerprint"]:
            raise PrefabRefused(f"prefab {name!r} staged on {cell} is NOT the land its catalog entry names "
                                f"(fingerprint {staged['fingerprint'][:12]} vs {prefab['fingerprint'][:12]}): a verb "
                                f"it rides changed its bytes -- a regression to find; nothing written",
                                gate="identity")
        if staged["nav"]:
            raise PrefabRefused(f"prefab {name!r} staged on {cell} leaves sea the coast-nav stamp would still re-class "
                                f"({staged['nav']}): a regression in the stamp or the mint; nothing written",
                                gate="nav")
        return "clean site: the full fingerprint"
    # THE NAV MARGIN: the reference copy at the catalog's clean site, then the target against it triangle for triangle
    points = [pt for pts in ground.values() for pt in pts]
    ref_cell = tuple(int(v) for v in prefab["fingerprint_cell"])
    ref = stage(prefab, ref_cell, game=game, keep=True)
    try:
        if ref["fingerprint"] != prefab["fingerprint"]:
            raise PrefabRefused(f"prefab {name!r}'s reference copy at its catalog site {ref_cell} is NOT the catalog's "
                                f"land: a verb it rides changed its bytes -- a regression to find; nothing written",
                                gate="identity")
        mask = margin_mask(points, cell)
        tgt = fingerprint(staged["root"], cell, staged["blocks"], mask_tri=mask)
        want = fingerprint(ref["root"], ref_cell, ref["blocks"], mask_tri=mask)
    finally:
        if ref.get("root"):
            shutil.rmtree(ref["root"], ignore_errors=True)
    if tgt != want:
        raise PrefabRefused(f"prefab {name!r} staged on {cell} differs from the catalog's land OUTSIDE the nav margin "
                            f"of the stock land at {sorted(ground)}: a regression to find; nothing written",
                            gate="identity")
    if staged["nav"]:
        raise PrefabRefused(f"prefab {name!r} staged on {cell} leaves sea the coast-nav stamp would still re-class "
                            f"({staged['nav']}) beside the stock land at {sorted(ground)}; nothing written", ground,
                            gate="nav")
    log(f"site beside stock land {sorted(ground)}: the catalog's land, its sea within {NAV_MARGIN:g}u of that land "
        f"re-classed by the coast-nav stamp")
    return "nav margin: the catalog's land, the margin's classes settled by the stamp"


def _stale_labels(draft) -> set:
    """The block labels of the files the draft's SOURCE changed since the draft was copied (``draft.stale``)."""
    from .draft import stale
    out = set()
    for rel in stale(Path(draft)):
        m = re.search(r"Disc[14]/0_1/r\d+/Block\[(\d+)\]\[(\d+)\] ", str(rel).replace("\\", "/"))
        if m:
            out.add((int(m[1]), int(m[2])))
    return out


def _draft_laws(prefab: dict, name: str, cell, draft, source: str, *, game=None) -> None:
    """The two laws a DRAFT target adds (:func:`place`'s docstring), refused before anything is staged."""
    from .island import _real_block_parts
    foot = set(footprint_labels(prefab, cell))
    near = foot | _ring(foot)
    moved = sorted(_stale_labels(draft) & near)
    if moved:
        raise PrefabRefused(f"{source} changed in or beside the prefab's footprint at {moved} since the draft was made: "
                            f"the draft cannot see that land; make a new draft (Discard) or place it elsewhere",
                            moved, gate="window")
    d4 = sorted(b for b in foot if _real_block_parts(b, disc=4, game=game))
    if d4:
        raise PrefabRefused(f"disc 4 has land or coast of its own at {d4}: Promote's mirror would not copy the checked "
                            f"bytes there (the disc-4 world, scenario 11090+, would differ); place it elsewhere",
                            d4, gate="disc4")
    if stamped_nav(prefab):
        g1 = stock_ground(prefab, cell, game=game, discs=(1,))
        g4 = stock_ground(prefab, cell, game=game, discs=(4,))
        if g1 != g4:
            diff = sorted(set(g1) ^ set(g4) | {k for k in set(g1) & set(g4) if g1[k] != g4[k]})
            raise PrefabRefused(f"the stock land within {NAV_MARGIN:g}u of the footprint differs between disc 1 and "
                                f"disc 4 at {diff}: the disc-4 copy would carry disc 1's sea classes beside other land; "
                                f"place it elsewhere", diff, gate="disc4")


def _undo_words(draft_of) -> str:
    """How a refused write is taken back: a draft's step comes back out with it (the card aborts the step)."""
    return ("the World tab takes the step back out of the draft" if draft_of is not None else
            "undo it through the draft (World tab) or the files' ledger, never by hand copy")


def place(name: str, cell, mod_folder, *, game=None, dry_run: bool = False, skip_mirror: bool = False,
          catalog=None, stack=None, allow_overwrite: bool = False, turn: int = 0, log=print) -> dict:
    """Place prefab ``name`` with its anchor on block ``cell``: the row check, the clear window, the staging
    identity, then (unless ``dry_run``) the compose into ``mod_folder`` and the identity of what it wrote on both
    discs. Raises :class:`PrefabRefused` before writing anything on any of the first three. ``stack`` = the FolderNames
    roots (default: the install's own -- pass ``()`` only for a folder that will never be promoted into the live map,
    such as a test's). ``allow_overwrite`` waives the compose's manifest-drift gate (``fuse.compose_layout``); a DRAFT
    always waives it, as every editor job does -- a draft's files change by design (rung C11).

    A DRAFT target (the World tab's card) is held to two more laws, because it is promoted later: a live edit to its
    source since it was copied must not lie in or beside the footprint (the stack read skips the source the draft
    stands in for), and Promote's disc-4 copy must be predictable now -- every footprint block open ocean on disc 4 too
    and the same stock ground near it on both discs, so the mirror copies the checked bytes verbatim.

    ``turn`` (90 / 180 / 270) places the walked land TURNED (THE QUARTER TURN, module docstring): every law above runs
    on the turned footprint and clear window, and identity is the catalog's land with that turn applied."""
    from .. import config
    from .render import game_stack
    entry = get(name, catalog)
    turn = int(turn)
    _steps(turn)
    if turn not in turns_of(entry):
        raise PrefabRefused(f"prefab {name!r} does not turn {turn}: its catalog entry allows {list(turns_of(entry))}"
                            + (f" ({entry['turns_note']})" if entry.get("turns_note") else ""), gate="turn")
    if not entry.get("fingerprint") or not entry.get("footprint"):
        raise PrefabRefused(f"prefab {name!r} has no fingerprint/footprint yet: take them with "
                            f"`world-prefab {name} --fingerprint --cell BX,BY` and write them into the catalog",
                            gate="catalog")
    prefab = turned(entry, turn)
    cell = (int(cell[0]) % 24, int(cell[1]))
    check_rows_on_map(prefab, cell)
    game_path = config.find_game_path(game)
    mod_root = game_path / mod_folder
    from .draft import stands_in_for
    draft_of = stands_in_for(mod_root)                   # the live folder this target is a DRAFT of, else None
    if stack is None:
        # a DRAFT stands in for its source (world/draft.py): the stack read skips the folder it was copied from, as
        # every World-tab card's occupancy read does -- the draft holds what it copied from there
        stack = tuple(r for r in (game_stack(game_path) or ()) if Path(r).name != draft_of)
    blockers = window_blockers(prefab, cell, mod_root, stack=stack)
    if draft_of is not None:
        _draft_laws(prefab, name, cell, mod_root, draft_of, game=game)
    if blockers["target"]:
        raise PrefabRefused(f"the target folder already holds land the prefab would read, cover or border at "
                            f"{sorted(blockers['target'])}: the staged bytes could not stand for these",
                            blockers["target"], gate="window")
    for folder, hit in blockers["stack"].items():
        raise PrefabRefused(f"{folder} (in the FolderNames stack) holds overrides in or beside the prefab's footprint "
                            f"at {sorted(hit)}", hit, gate="window")
    if turn:
        # THE OPEN-OCEAN TARGET LAW. At turn 0 the composing verbs refuse stock land under the footprint themselves; a
        # turn composes at the catalog site and writes the turned files here, so the law is checked here
        from .island import _real_block_parts
        real = sorted(b for b in footprint_labels(prefab, cell) if _real_block_parts(b, disc=1, game=game))
        if real:
            raise PrefabRefused(f"prefab {name!r} turned {turn} on {cell} would cover stock land or coast at {real}: a "
                                f"prefab goes onto open ocean", real, gate="window")
    if prefab["status"] != "qualified":
        log(f"CANDIDATE: {name!r} has not been walked in game yet -- walk its rim and every carry, then mark it "
            f"qualified in the catalog.")
    elif turn and turn not in (entry.get("walked_turns") or ()):
        log(f"TURNED {turn}: the walked land, turned by transplant's in-game-proven quarter-turn law; this turn has "
            f"not itself been walked -- walk its rim once, then add {turn} to walked_turns in the catalog.")
    staged = stage(prefab, cell, game=game, keep=True) if not turn else stage_turned(entry, turn, cell, game=game)
    try:
        tier = (_identity(prefab, name, cell, staged, game=game, log=log) if not turn else
                _identity_turned(prefab, name, cell, staged, game=game, log=log))
        report = {"name": name, "cell": list(cell), "turn": turn, "status": prefab["status"],
                  "staged": staged["fingerprint"],
                  "footprint": staged["footprint"], "identity": tier, "dry_run": dry_run, "written_fingerprint": None,
                  "blocks": [list(b) for b in staged["blocks"]], "center": list(footprint_center(prefab, cell))}
        log(f"staged on {cell}" + (f", turned {turn}" if turn else "") + f": {tier} ({len(staged['blocks'])} blocks)")
        if dry_run:
            return report
        if turn:
            # the turned files through the kit's ledgered writers (never a copy of staged files: each row names this
            # write), from the source the identity above was judged on, under the compose's manifest law (its drift
            # gate, then one manifest entry -- review P5: a turn is not a fuse row, and the turn-0 path gets both)
            from . import fuse as FU
            try:
                FU.manifest_step(str(mod_root), f"prefab {name} turn {turn}",
                                 {"name": name, "cell": list(cell), "turn": turn},
                                 lambda: write_turned(staged["source"]["root"], source_cell(entry), entry, turn,
                                                      str(mod_root), cell, game=game, skip_mirror=skip_mirror),
                                 game=game, allow_overwrite=allow_overwrite or draft_of is not None)
            except ValueError as e:
                if not str(e).startswith("manifest-drift"):
                    raise
                raise PrefabRefused(f"a prefab row refused: {e}", gate="compose") from e
        else:
            _compose(mod_root, expand(prefab, cell), game=game, skip_mirror=skip_mirror,
                     allow_overwrite=allow_overwrite or draft_of is not None)
        # (``written`` is the cards' list of written files: the land's identity goes under its own key -- review P3)
        report["written_fingerprint"] = fingerprint(mod_root, cell, staged["blocks"])
        if report["written_fingerprint"] != staged["fingerprint"]:
            raise PrefabRefused(f"prefab {name!r} was WRITTEN into {mod_folder} but its bytes there are not the staged "
                                f"ones (fingerprint {report['written_fingerprint'][:12]}): IDENTITY BROKEN after the "
                                f"write -- {_undo_words(draft_of)}", gate="written")
        stamped = stamped_nav(prefab)
        left = nav_settled(mod_root, staged["blocks"], policy=nav_policy(prefab), game=game) if stamped else {}
        if left:
            raise PrefabRefused(f"prefab {name!r} was WRITTEN into {mod_folder} but the coast-nav stamp would still "
                                f"re-class its sea there ({left}) -- {_undo_words(draft_of)}", gate="written")
        if draft_of is not None:
            # a DRAFT gets no disc-4 copy (the auto-mirror needs the install's bundles): Promote makes it in the live
            # folder (world/draft.py promote). Measured: the card's Accept into a draft refused here on an empty disc 4
            report["written_disc4"] = ("deferred: Promote makes a draft's disc-4 copy in the live folder, a verbatim "
                                       "copy (disc 4 is open ocean there, with the same stock land near it)")
        elif not skip_mirror:
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
                                    f"never by hand copy", gate="disc4")
        log(f"placed {name!r} on block {cell}" + (f", turned {turn}" if turn else "")
            + f": {len(staged['blocks'])} blocks, the staged land"
            + (" (a draft: Promote makes its disc-4 copy)" if draft_of is not None
               else "" if skip_mirror else " on disc 1 and disc 4"))
        return report
    finally:
        _drop(staged)


# ---------------------------------------------------------------- Save as prefab (rung P6)
#: A saved prefab's name: lower-case words joined by hyphens (it is a catalog key, a CLI argument and a recipe value).
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,47}$")
#: The relief tables a saved prefab may carry on its base (PREFAB_TABLES less the bases).
RELIEF_TABLES = tuple(t for t in PREFAB_TABLES if t not in BASE_TABLES)
#: The keys a composition row never brings into the catalog (placement sets them; ``load_catalog`` refuses them).
_PLACEMENT_KEYS = ("step", "prefab_frame", "near")
#: How far a relief row may stand from the base's anchor frame (a sanity bound: a carry reads 96u round its centre).
_MAX_REL = 4 * BLOCK


def entry_from_rows(name: str, rows) -> tuple:
    """A composition's absolute rows (a draft's or a recipe's: one BASE row first, then relief) as a catalog entry
    RELATIVE to its anchor -- the block holding the island's centre, or the transplant's own ``cell`` -- with
    ``(entry, anchor)``. Refuses what a prefab cannot hold, with gate ``rows``."""
    if not NAME_RE.match(str(name or "")):
        raise PrefabRefused(f"a prefab name is lower-case letters, digits and hyphens (2-48), not {name!r}",
                            gate="catalog")
    rows = [{k: v for k, v in dict(r).items() if k not in _PLACEMENT_KEYS} for r in rows]
    if not rows or rows[0].get("table") not in BASE_TABLES:
        raise PrefabRefused(f"a prefab starts with its base -- an island or a carried coast ({BASE_TABLES}) -- and the "
                            f"relief stands on it; the first row is {rows[0].get('table') if rows else 'missing'}",
                            gate="rows")
    for r in rows[1:]:
        if r.get("table") not in RELIEF_TABLES:
            raise PrefabRefused(f"a prefab holds one base and its relief ({RELIEF_TABLES}); "
                                f"{r.get('table')!r} cannot ride along", gate="rows")
    base = rows[0]
    if base["table"] == "island":
        if "seed" not in base or "center" not in base:
            raise PrefabRefused("the island row needs its center and seed (an editor row always has both)",
                                gate="rows")
        cx, cz = (float(v) for v in base["center"])
        anchor = (math.floor(cx / BLOCK) % 24, math.floor(-cz / BLOCK))
    else:
        anchor = (int(base["cell"][0]) % 24, int(base["cell"][1]))
    out = []
    for r in rows:
        row = dict(r)
        if row["table"] == "transplant":
            row["cell"] = [0, 0]
        else:
            if "center" not in row:
                raise PrefabRefused(f"a {row['table']} row needs its exact center (an editor row always has it)",
                                    gate="rows")
            dx, dz = rel_point(float(row["center"][0]), float(row["center"][1]), anchor)
            if abs(dx) > _MAX_REL or abs(dz) > _MAX_REL:
                raise PrefabRefused(f"the {row['table']} row at {row['center']} stands {math.hypot(dx, dz):.0f}u from "
                                    f"the base's block: it is not part of this landmass", gate="rows")
            row["center"] = [dx, dz]
        out.append(row)
    return {"name": str(name), "status": "candidate", "rows": out}, anchor


def target_rel(entry: dict) -> set:
    """Every block (offset from the anchor) the entry's verbs need OPEN OCEAN: its footprint, and for a transplant base
    its whole target rect -- the carry refuses a real block anywhere in it, written or not (measured: the comma's rect
    is 3x2, its footprint 5 blocks, and a site whose sixth block is real sea refused the carry)."""
    need = {tuple(int(v) for v in b) for b in entry.get("footprint") or ()}
    base = (entry.get("rows") or [{}])[0]
    if base.get("table") == "transplant":
        from .transplantedit import tsize
        tw, th = tsize(tuple(base.get("size") or (1, 1)), int(base.get("rot") or 0))
        cx, cy = (int(v) for v in base.get("cell") or (0, 0))
        need |= {(cx + i, cy + j) for i in range(tw) for j in range(th)}
    return need


def clean_sites(entry: dict, *, game=None, first=None, limit=None) -> list:
    """Anchors where the entry's footprint is stock OPEN OCEAN on both discs (no block prefab of its own:
    ``extract.block_parts``) and no stock ground lies within the nav margin of it (:func:`stock_ground`): the sites a
    fingerprint may be taken at (for a transplant base, its whole target rect too: :func:`target_rel`). ``first`` is
    tried before the map's row-major order; ``limit`` stops the search once
    that many are found (the stock-ground read is the slow part). A site whose whole footprint ring is open ocean holds
    no stock ground near by construction, so it is never read."""
    from .extract import block_parts
    from .mesh import GRID_ROWS
    occupied = set(block_parts(disc=1, game=game)) | set(block_parts(disc=4, game=game))
    need = target_rel(entry)

    def is_real(b):
        return (int(b[0]), int(b[1])) in occupied
    order = ([tuple(first)] if first is not None else []) + [
        (bx, by) for by in range(GRID_ROWS) for bx in range(24) if (bx, by) != (tuple(first) if first else None)]
    out = []
    for cell in order:
        try:
            check_rows_on_map(entry, cell)
        except PrefabRefused:
            continue
        if any(not 0 <= int(cell[1]) + r[1] < GRID_ROWS for r in need):
            continue
        if any(is_real(label_of(r, cell)) for r in need):
            continue
        foot = set(footprint_labels(entry, cell))
        if any(is_real(b) for b in _ring(foot)) and stock_ground(entry, cell, game=game):
            continue
        out.append(cell)
        if limit is not None and len(out) >= limit:
            break
    return out


def entry_toml(entry: dict) -> str:
    """One ``[[prefab]]`` table (and its ``[[prefab.rows]]``) as the catalog writes it."""
    from .recipe import _value
    head = ("name", "status", "walked", "ground", "note", "saved", "fingerprint", "fingerprint_cell", "footprint",
            "turns", "turns_note")
    lines = ["", "[[prefab]]"]
    for k in head:
        if k in entry:
            v = entry[k]
            if isinstance(v, str):
                v = " ".join(v.split())                   # one line: a note never breaks the TOML
            lines.append(f"{k} = {_value(v)}")
    for r in entry["rows"]:
        lines += ["", "[[prefab.rows]]", f"table = {_value(r['table'])}"]
        lines += [f"{k} = {_value(v)}" for k, v in r.items() if k != "table"]
    return "\n".join(lines) + "\n"


_USER_HEADER = ("# Your landmass PREFABS (the World tab's Save as prefab / world-prefab --save), read after the kit's own\n"
                "# catalog (world/data/prefabs.toml): the same rules, one namespace. A saved prefab is a CANDIDATE until\n"
                "# you walk it in game; then set status = \"qualified\" and note the walk.\n")


def save(name: str, rows, *, catalog=None, game=None, note: str = "", turns: bool = True, source: str = "",
         log=print) -> dict:
    """SAVE AS PREFAB (rung P6): freeze a composition -- a base island or carried coast and the relief on it, as a
    draft or a recipe holds them -- into a catalog entry, appended to ``catalog`` (default :func:`user_catalog`).

    It is composed with the prefab frame on (P0), never copied: the entry is the land the frame writes, which can differ
    from an unframed draft's in its meadow stamps, rolling relief and a mountain's fallback tiles. The steps, each
    refusing before anything is written:

    1. the rows as an entry relative to their anchor (:func:`entry_from_rows`); the name unique in every catalog read;
    2. staged at its own anchor to learn its footprint (the verbs held that site to open ocean when it was made);
    3. a CLEAN site (:func:`clean_sites`; the anchor itself when it is one): staged there, its navigation settled --
       the fingerprint and ``fingerprint_cell``;
    4. THE COMPOSITION MOVES AS ONE: staged at a second clean site, the same fingerprint, or it refuses (a verb that
       read something outside the frame);
    5. with ``turns``, each quarter turn placed at that second site and held to the land turned
       (:func:`stage_turned`); the turns that pass open, a riding part keeps it at 0 (``turns_note``).

    Returns the report (the entry, its sites, the turns measured)."""
    path = Path(catalog) if catalog is not None else user_catalog()
    entry, anchor = entry_from_rows(name, rows)
    if entry["name"] in _taken_names(path):
        raise PrefabRefused(f"a prefab named {name!r} is in the catalog already: pick another name", gate="catalog")
    log(f"anchor block {anchor}: staging the composition there to learn its footprint")
    first = stage(entry, anchor, game=game)
    if not first["footprint"]:
        raise PrefabRefused("the composition wrote no land", gate="rows")
    entry["footprint"] = [list(b) for b in first["footprint"]]
    sites = clean_sites(entry, game=game, first=anchor, limit=2)
    if len(sites) < 2:
        raise PrefabRefused(f"the map has {len(sites)} clean site(s) for a footprint of {len(first['footprint'])} "
                            f"blocks: a prefab is fingerprinted at one and proved at a second", gate="window")
    fc = anchor if anchor in sites else sites[0]
    st1 = first if fc == anchor else stage(entry, fc, game=game)
    if st1["nav"]:
        raise PrefabRefused(f"staged at the clean site {fc}, the coast-nav stamp would still re-class its sea "
                            f"({st1['nav']}): a regression in the stamp or a verb", gate="nav")
    entry.update({"fingerprint": st1["fingerprint"], "fingerprint_cell": list(fc)})
    second = next(s for s in sites if s != fc)
    log(f"fingerprinted at {fc}; staging again at {second} (the composition must move as one)")
    st2 = stage(entry, second, game=game)
    if st2["fingerprint"] != st1["fingerprint"] or st2["footprint"] != st1["footprint"]:
        raise PrefabRefused(f"staged at {fc} and at {second} the composition is NOT the same land: a row reads "
                            f"something the prefab frame does not move with it (it cannot be a prefab)", gate="identity")
    turned_ok, why = [0], ""
    if turns:
        for t in (90, 180, 270):
            st = None
            try:
                view = turned(entry, t)
                st = stage_turned(entry, t, second, game=game)
                _identity_turned(view, entry["name"], second, st, game=game, log=lambda *a: None)
                turned_ok.append(t)
            except PrefabRefused as e:
                why = why or f"turn {t}: {e}"
                if e.gate == "turn":                     # a riding part: no turn can pass
                    break
            finally:
                _drop(st)
    entry["turns"] = turned_ok
    if why and turned_ok == [0]:
        entry["turns_note"] = why[:300]
    stamp = time.strftime("%Y-%m-%d")
    entry["saved"] = f"{stamp}" + (f" from {source}" if source else "")
    if note:
        entry["note"] = note
    load_check = _load_one_text(entry_toml(entry))
    _append_entry(path, entry)
    log(f"saved {entry['name']!r} to {path}: {len(entry['footprint'])} blocks, turns {entry['turns']}, a candidate "
        f"until you walk it")
    return {"ok": True, "name": entry["name"], "catalog": str(path), "anchor": list(anchor),
            "fingerprint": entry["fingerprint"], "fingerprint_cell": list(fc), "second_site": list(second),
            "footprint": entry["footprint"], "turns": entry["turns"], "turns_note": entry.get("turns_note", ""),
            "rows": len(entry["rows"]), "checked": load_check}


def _taken_names(path: Path) -> set:
    """Every name a new entry for ``path`` must not take: the kit's catalog and that file's own entries, even ones
    that break a rule (their names are still spoken for)."""
    names = {p["name"] for p in _load_one(CATALOG, set())} if Path(path).resolve() != CATALOG.resolve() else set()
    if Path(path).is_file():
        try:
            doc = tomllib.loads(Path(path).read_text(encoding="utf-8-sig"))
            names |= {str(p.get("name")) for p in doc.get("prefab", ()) if p.get("name")}
        except (tomllib.TOMLDecodeError, UnicodeDecodeError):
            pass
    return names


def _append_entry(path: Path, entry: dict) -> None:
    """Append one entry under a LOCK, its name checked again against the file as it is now (another save may have
    finished during this one's minutes of staging), written ATOMICALLY (a temp file beside it, then a rename: a kill
    mid-write leaves the old file whole) -- review P6: a read-modify-write with neither lost saves and doubled names."""
    import os
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + ".lock")
    fd = None
    for _ in range(200):                                 # ~10 s: another save's append is milliseconds
        try:
            fd = os.open(str(lock), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            if time.time() - lock.stat().st_mtime > 60:  # a lock a killed save left behind
                lock.unlink(missing_ok=True)
                continue
            time.sleep(0.05)
    if fd is None:
        raise PrefabRefused(f"{path} is locked by another save (remove {lock.name} if no save is running)",
                            gate="catalog")
    try:
        if entry["name"] in _taken_names(path):
            raise PrefabRefused(f"a prefab named {entry['name']!r} was saved while this one was being checked: "
                                f"save it again under another name", gate="catalog")
        text = path.read_text(encoding="utf-8-sig") if path.is_file() else _USER_HEADER
        tmp = path.with_name(path.name + f".tmp-{os.getpid()}")
        tmp.write_text(text.rstrip("\n") + "\n" + entry_toml(entry), encoding="utf-8")
        os.replace(tmp, path)
    finally:
        os.close(fd)
        lock.unlink(missing_ok=True)


def _load_one_text(text: str) -> str:
    """Validate an entry's TOML through the catalog's own reader before it is written (a law in a docstring is a
    wish: what is appended must load)."""
    tmp = Path(tempfile.mkdtemp(prefix="ff9-prefab-save-"))
    try:
        (tmp / "c.toml").write_text(text, encoding="utf-8")
        _load_one(tmp / "c.toml", set())
        return "loads"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
