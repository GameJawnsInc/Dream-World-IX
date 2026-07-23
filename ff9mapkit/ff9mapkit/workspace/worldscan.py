"""A census of a DEPLOYED overworld override tree -- the Qt-free half of the Workspace's World tab.

The kit's world verbs (world-island / world-transplant / world-mountain / world-entrance) write loose
``Block[x][y] <Part>.ff9mesh`` overrides + ``Block[x][y] Donor.txt`` sidecars into a mod folder
(conventionally ``FF9CustomMap-world``), and :mod:`ff9mapkit.world.discmirror` mirrors Disc1 -> Disc4.
Until now the only way to see what a tree holds was Explorer. This module reads one back into a
structured :class:`WorldCensus`: which blocks carry overrides, what each part IS (real geometry vs the
blanking/divert-arm stubs), the coastal donor, and whether the Disc4 mirror is current.

Instrument notes (why the readings can be trusted):

- File names are parsed with :data:`ff9mapkit.world.discmirror._BLOCK_RE` -- the SAME regex the mirror
  uses -- so this census and the mirror agree on what counts as a cell file, and ``--in-place``'s
  ``*.ff9mesh.bak-<ts>`` siblings fall out exactly as they do there (counted, never listed as parts).
- Real-vs-blank is read from the ``.ff9mesh`` HEADER ONLY (20 bytes: magic + vcount/icount).
  :func:`ff9mapkit.world.mesh.hidden_block_mesh` (the part blanker) and
  :func:`ff9mapkit.world.mesh.stub_terrain_mesh` (the divert-arm) both emit EXACTLY 3 verts, while any
  real part is hundreds+ -- so ``vcount <= 3`` is calibrated against the writers, not a guess
  (test_worldscan re-derives it from the generators' own output).
- Disc4 mirror status BYTE-compares, never size-compares: a pure-Y terrain displacement (the hill
  language) changes bytes without changing length, which is precisely the edit a stale mirror hides.
  Disc4-ONLY part files are expected (the mirror's free-ride PINS for un-overridden donor parts) and
  are counted, not flagged.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass, field
from pathlib import Path

# Light imports only: this module sits on the Workspace's construction path (THE STARTUP SPEND law) --
# world.mesh / world.discmirror are struct+pathlib modules, verified import-light.
from ..world.discmirror import _BLOCK_RE as BLOCK_RE          # THE authoritative cell-file parser
from ..world.mesh import GRID_COLS, GRID_ROWS, block_in_grid

BLOCK_UNITS = 64.0                                 # one overworld block = 64 world units (engine-fixed)
PART_ORDER = ("Terrain", "Object", "Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Beach1")
_MAGIC = b"F9WM"                                   # world.mesh.write_ff9mesh's magic
_BLANK_VCOUNT = 3                                  # hidden_block_mesh / stub_terrain_mesh both emit 3 verts
_BAK_RE = re.compile(r"^Block\[(\d+)\]\[(\d+)\] .+\.bak\b")   # --in-place backups (never engine-read)
_DISC_RE = re.compile(r"^Disc(\d+)$")


def block_center(bx: int, by: int) -> tuple[float, float]:
    """Block ``(bx, by)``'s centre in WORLD coordinates ``(x, z)`` -- the debug menu's teleport frame.
    The island writer's own law: ``(64*bx + 32, -64*by - 32)`` (island.py's centre formula)."""
    return (BLOCK_UNITS * bx + BLOCK_UNITS / 2, -BLOCK_UNITS * by - BLOCK_UNITS / 2)


def block_span(bx: int, by: int) -> tuple[tuple[float, float], tuple[float, float]]:
    """The block's world-space extent ``((x0, x1), (z0, z1))`` (z runs negative with rows)."""
    return ((BLOCK_UNITS * bx, BLOCK_UNITS * (bx + 1)),
            (-BLOCK_UNITS * (by + 1), -BLOCK_UNITS * by))


@dataclass(frozen=True)
class PartInfo:
    """One deployed part file, read at the header only."""

    name: str                                      # "Terrain" / "Sea4" / ...
    size: int                                      # bytes on disk
    vcount: int | None = None                      # None = not a readable .ff9mesh (Donor.txt, corrupt)
    icount: int | None = None

    @property
    def tris(self) -> int | None:
        return None if self.icount is None else self.icount // 3

    @property
    def blank(self) -> bool:
        """True for the two 3-vert writer idioms: a blanked part or the divert-arm Terrain stub."""
        return self.vcount is not None and self.vcount <= _BLANK_VCOUNT


@dataclass
class CellCensus:
    """Everything deployed at one block, Disc1 view + the Disc4 mirror verdict."""

    bx: int
    by: int
    parts: dict[str, PartInfo] = field(default_factory=dict)
    donor: tuple[int, int] | None = None           # parsed "dx,dy" from Donor.txt
    donor_raw: str | None = None                   # the sidecar's literal text (kept even if unparseable)
    backups: int = 0                               # --in-place .bak siblings beside this cell
    mirror: str = ""                               # "current" | "stale" | "missing" | "" (no Disc4 tree)
    pins: int = 0                                  # Disc4-only part files (the mirror's free-ride pins)
    dirpath: Path | None = None                    # the Disc1 r-folder holding this cell's files

    @property
    def kind(self) -> str:
        """The cell's headline: ``land`` (real Terrain), ``water`` (arming stub / real sea parts only),
        or ``stub`` (nothing but blanks + the sidecar -- unusual, surfaced rather than hidden)."""
        t = self.parts.get("Terrain")
        if t is not None and t.vcount is not None and not t.blank:
            return "land"
        if any(p.name != "Terrain" and p.vcount is not None and not p.blank
               for p in self.parts.values()):
            return "water"
        return "stub"

    @property
    def has_real_object(self) -> bool:
        o = self.parts.get("Object")
        return o is not None and o.vcount is not None and not o.blank


@dataclass
class WorldCensus:
    """One mod folder's deployed overworld, as scanned."""

    root: Path                                     # the mod folder (e.g. <game>/FF9CustomMap-world)
    cells: dict[tuple[int, int], CellCensus] = field(default_factory=dict)
    has_disc4: bool = False
    disc4_only: list[tuple[int, int]] = field(default_factory=list)   # cells the mirror has, Disc1 lacks
    strays: list[str] = field(default_factory=list)                   # off-grid / unparseable Block files
    total_bytes: int = 0

    @property
    def landmasses(self) -> int:
        """Connected components over the deployed cells (4-adjacency) -- 'how many islands'."""
        seen: set[tuple[int, int]] = set()
        n = 0
        for start in self.cells:
            if start in seen:
                continue
            n += 1
            stack = [start]
            while stack:
                cx, cy = stack.pop()
                if (cx, cy) in seen:
                    continue
                seen.add((cx, cy))
                for nb in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                    if nb in self.cells and nb not in seen:
                        stack.append(nb)
        return n

    @property
    def stale_cells(self) -> list[tuple[int, int]]:
        return sorted(k for k, c in self.cells.items() if c.mirror in ("stale", "missing"))


def _read_header(path: Path) -> tuple[int, int | None, int | None]:
    """(size, vcount, icount) from a ``.ff9mesh``'s fixed 20-byte header; (size, None, None) if it
    isn't one (bad magic / truncated) -- surfaced as an unreadable part, never an exception."""
    try:
        size = path.stat().st_size
        with path.open("rb") as fh:
            head = fh.read(20)
        if len(head) < 20 or head[:4] != _MAGIC:
            return size, None, None
        _ver, vcount, icount, _flags = struct.unpack_from("<iiii", head, 4)
        return size, vcount, icount
    except OSError:
        return 0, None, None


def _scan_disc(disc_dir: Path):
    """One Disc tree -> ``(files, backups, strays)`` where ``files[(bx,by)][filename] = Path``."""
    files: dict[tuple[int, int], dict[str, Path]] = {}
    backups: dict[tuple[int, int], int] = {}
    strays: list[str] = []
    if not disc_dir.is_dir():
        return files, backups, strays
    for p in sorted(disc_dir.rglob("Block[[]*")):  # [[] = a literal '[' to glob (discmirror's idiom)
        if not p.is_file():
            continue
        m = BLOCK_RE.match(p.name)
        if m is None:
            b = _BAK_RE.match(p.name)
            if b is not None:                      # an --in-place backup sibling: counted, never a part
                key = (int(b.group(1)), int(b.group(2)))
                backups[key] = backups.get(key, 0) + 1
            else:
                strays.append(str(p.relative_to(disc_dir)))
            continue
        bx, by = int(m.group(1)), int(m.group(2))
        if not block_in_grid(bx, by):              # the GRID-BOUNDS law: an off-grid override is a DEAD
            strays.append(str(p.relative_to(disc_dir)))   # file the engine never streams -- surface it
            continue
        files.setdefault((bx, by), {})[p.name] = p
    return files, backups, strays


def _compare_cell(d1: dict[str, Path], d4: dict[str, Path]) -> tuple[str, int]:
    """The Disc4 mirror verdict for one cell: ('current'|'stale'|'missing', free-ride pin count).
    BYTE-equal or bust -- see the module docstring for why sizes are not enough."""
    pins = sum(1 for name in d4 if name not in d1)
    for name, p1 in d1.items():
        p4 = d4.get(name)
        if p4 is None:
            return "missing", pins
        try:
            if p1.stat().st_size != p4.stat().st_size or p1.read_bytes() != p4.read_bytes():
                return "stale", pins
        except OSError:
            return "stale", pins
    return "current", pins


def scan_tree(mod_root: Path) -> WorldCensus:
    """Census ``<mod_root>/FF9_Data/WorldMap`` (read-only). Disc1 is the canonical view; Disc4 is
    judged against it as the mirror. Raises nothing on a missing tree -- an empty census is a finding."""
    mod_root = Path(mod_root)
    census = WorldCensus(root=mod_root)
    wm = mod_root / "FF9_Data" / "WorldMap"
    d1_files, d1_baks, strays1 = _scan_disc(wm / "Disc1")
    d4_files, _d4_baks, strays4 = _scan_disc(wm / "Disc4")
    census.has_disc4 = (wm / "Disc4").is_dir() and bool(d4_files)
    census.strays = strays1 + [f"Disc4/{s}" for s in strays4]
    for key in sorted(d1_files):
        bx, by = key
        cell = CellCensus(bx=bx, by=by, backups=d1_baks.get(key, 0),
                          dirpath=next(iter(d1_files[key].values())).parent)
        for name, p in sorted(d1_files[key].items()):
            m = BLOCK_RE.match(name)
            part, ext = m.group(3), m.group(4)
            if ext == "txt":                       # the Donor sidecar -- one line "dx,dy"
                try:
                    raw = p.read_text(encoding="utf-8").strip()
                except OSError:
                    raw = None
                cell.donor_raw = raw
                if raw:
                    try:
                        dx, dy = (int(v) for v in raw.split(","))
                        cell.donor = (dx, dy)
                    except ValueError:
                        pass                       # unparseable donor: raw is still shown
                continue
            size, vcount, icount = _read_header(p)
            cell.parts[part] = PartInfo(name=part, size=size, vcount=vcount, icount=icount)
            census.total_bytes += size
        if census.has_disc4:
            mesh_only = {n: p for n, p in d1_files[key].items() if n.endswith(".ff9mesh")}
            d4_cell = {n: p for n, p in d4_files.get(key, {}).items() if n.endswith(".ff9mesh")}
            cell.mirror, cell.pins = _compare_cell(mesh_only, d4_cell)
        census.cells[key] = cell
    census.disc4_only = sorted(k for k in d4_files if k not in d1_files)
    return census


def find_world_trees(game_path: Path) -> list[Path]:
    """Mod folders under the game root that carry a worldmap override tree (``FF9_Data/WorldMap``),
    the conventional ``FF9CustomMap-world`` first. Top level only -- mod folders are flat siblings."""
    game_path = Path(game_path)
    found: list[Path] = []
    try:
        kids = sorted(game_path.iterdir(), key=lambda p: p.name.lower())
    except OSError:
        return found
    for child in kids:
        try:
            if child.is_dir() and (child / "FF9_Data" / "WorldMap").is_dir():
                found.append(child)
        except OSError:
            continue
    found.sort(key=lambda p: (p.name.lower() != "ff9custommap-world", p.name.lower()))
    return found
