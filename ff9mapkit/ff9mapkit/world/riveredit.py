"""Moving the river as the overworld editor drives it (rung C5): the river's own carried land and its island's coast
ring as the ghost, the placements it fits, which of them is free once the river is out, and the ONE place the
editor's ``world-river`` command is built.

THE CLI STAYS THE ORACLE: Check runs :func:`command` with ``--dry-run`` and Accept without, and both read the verdict
``--report-json`` writes. A move is ``world-river --at NEW --move-from OLD``: the verb reads the old deploy's files
from the folder's ledger, leaves them out of every occupancy read, judges the new placement as if the old river were
gone, and only takes the old one out once every gate is green.

THE PLACEMENTS a river can take are whole-block shifts that land its island's block rectangle on true open ocean
(``river.open_ocean_offsets``): 56 on disc 1. Measured on FF9CustomMap-world (C5.md), every one of them already
holds an edit, and once the river is out exactly one more is free: one block north of it. So the tool shows every
placement, marks each one free or held, and a click picks the nearest.

THE GHOST is the fragment's own stock triangles and the minted island's coast ring, moved by the shift (a whole-block
shift moves every cell by the same block step, so the cells need composing once).

THE DISC-4 HALF needs nothing here: a river's disc-4 step is the mirror's COPY, which a draft cannot run and Promote
runs in the live folder (keeping the ledger's world-river tag, so the moved river stays the verb's own).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .forestedit import CENTRE_STEP, SoupIndex, fmt_num, read_verdict   # noqa: F401  (the tools' shared kit)

DONOR = "cluster-c"
BLOCK = 64.0


@dataclass
class RiverShape:
    """The river, read once: its carried stock triangles and its island's coast ring at the home placement
    (``tris`` ``(n, 3, 3)``, ``ring`` ``(m, 2)``), the island's blocks there (``blocks``), the cells a deploy writes at
    the first fitting shift (``cells``, at ``cells_shift``), and every fitting shift (``shifts``, nearest first)."""
    tris: np.ndarray
    ring: np.ndarray
    blocks: list
    cells: list
    cells_shift: tuple
    shifts: list

    def cells_at(self, shift) -> list:
        """The cells a deploy at whole-block ``shift`` writes (wrapped labels)."""
        dx, dy = shift[0] - self.cells_shift[0], shift[1] - self.cells_shift[1]
        return sorted((int((x + dx) % 24), y + dy) for x, y in self.cells)

    def blocks_at(self, shift) -> list:
        return sorted((int((x + shift[0]) % 24), y + shift[1]) for x, y in self.blocks)


def shape(*, game=None) -> RiverShape:
    """Read the river: the fragment, the island ring, the fitting shifts, and the cells (one composition, at the
    nearest fitting shift; about fifteen seconds)."""
    from . import river as R
    donor = R.CLUSTER_C
    win = R.read_window(donor, game=game)
    frag = R.build_fragment(win, donor)
    ol = R.outline(frag)
    blocks = sorted(R.mint(ol)["blocks"])
    shifts = []
    for s in R.open_ocean_offsets(blocks, limit=4096, game=game):     # nearest first; the x-torus lists each twice
        if not any(same_shift(s, t) for t in shifts):
            shifts.append(tuple(s))
    if not shifts:
        raise ValueError("no whole-block shift lands the river's island on open ocean")
    comp = R.compose(frag, offset=offset_of(shifts[0]), window=win, ol=ol, disc=donor.disc, game=game)
    cells = sorted(tuple(int(v) for v in k.split(",")) for k in comp.plan["cells"])
    tris = np.asarray([t["P"] for t in frag.tris], dtype=np.float64).reshape(-1, 3, 3)
    return RiverShape(tris=tris, ring=np.asarray(ol.ring, dtype=np.float64), blocks=[tuple(b) for b in blocks],
                      cells=cells, cells_shift=tuple(shifts[0]), shifts=[tuple(s) for s in shifts])


def offset_of(shift) -> tuple:
    """A whole-block shift as ``--at``'s world translation (``+ 0.0``: never a -0.0)."""
    return (BLOCK * shift[0] + 0.0, -BLOCK * shift[1] + 0.0)


def shift_of(offset) -> tuple:
    from .river import block_shift
    return tuple(block_shift(offset))


def same_shift(a, b) -> bool:
    """The x-torus: 24 columns is no shift."""
    return a is not None and b is not None and (a[0] - b[0]) % 24 == 0 and a[1] == b[1]


def placed(rs: RiverShape, shift):
    """The ghost at ``shift``: ``(tris, rim)``, the fragment's triangles and the island ring (seated at y 0.4, the
    island lane's sea level), both moved. Columns are wrapped onto the map's 0..1536 the way the view draws it."""
    dx, dz = offset_of(shift)
    tris = rs.tris.copy()
    tris[..., 0] += dx
    tris[..., 2] += dz
    rim = np.column_stack([rs.ring[:, 0] + dx, np.full(len(rs.ring), 0.4), rs.ring[:, 1] + dz])
    span = 24 * BLOCK
    shift_x = -span * math.floor(float(rim[:, 0].mean()) / span)          # one wrap for the whole ghost
    tris[..., 0] += shift_x
    rim[:, 0] += shift_x
    return tris, rim


def centre(rs: RiverShape, shift) -> tuple:
    """The middle of the island's blocks at ``shift`` (where the ghost's handle sits), x on the map."""
    bs = rs.blocks_at(shift)
    xs = [b[0] for b in rs.blocks]
    cx = BLOCK * ((min(xs) + max(xs)) / 2.0 + shift[0]) + BLOCK / 2.0
    cz = -(BLOCK * (sum(b[1] for b in bs) / len(bs)) + BLOCK / 2.0)
    return (cx % (24 * BLOCK), cz)


def nearest(rs: RiverShape, x: float, z: float):
    """The fitting shift whose island middle is nearest ``(x, z)`` (the x-torus measured round)."""
    span = 24 * BLOCK

    def d(s):
        cx, cz = centre(rs, s)
        ddx = abs(cx - x) % span
        return min(ddx, span - ddx) ** 2 + (cz - z) ** 2
    return min(rs.shifts, key=d)


def placements(rs: RiverShape, folder, *, game=None) -> list:
    """Where this verb's river stands in ``folder`` now: the whole-block shifts of its live deploys there, most files
    first, as ``[(shift, owned paths)]``. A file stands at the placement its LAST ledger row names (``deploy_ownership``
    accepts any row with its bytes, so a cell a move filled with the old river's very bytes would read as both); the
    owned paths are the ownership read's at that placement, what ``--move-from`` takes out."""
    from collections import Counter
    from pathlib import Path
    from .. import config
    from . import mesh as M
    from . import river as R
    last = {}
    for e in M.read_ledger(Path(config.find_game_path(game)) / str(folder)):
        try:
            last[(int(e["write_disc"]), (int(e["cell"][0]), int(e["cell"][1])), str(e["part"]))] = e
        except (KeyError, TypeError, ValueError, IndexError):
            continue
    standing = Counter()
    for e in last.values():
        verb, sh = R._row_verb_shift(e)
        if verb == R.REMOVE_VERB and sh is not None and e.get("op") != "remove" and e.get("sha256"):
            key = next((s for s in standing if same_shift(s, sh)), tuple(sh))
            standing[key] += 1
    out = []
    for sh, _n in standing.most_common():
        own = R.deploy_ownership(rs.cells_at(sh), str(folder), shift=sh, game=game)
        if own["owned"]:
            out.append((tuple(sh), [Path(f["path"]) for f in own["owned"]]))
    return out


def preview(rs: RiverShape, shift, *, river_at, occupied) -> dict:
    """The placement's laws: ``{"ok", "why", "where", "blocks"}``. ``river_at`` is the river's shift now (None: no
    river there, the tool places a new one); ``occupied(cells)`` returns ``{cell: [folder names]}`` for the cells some
    folder of the stack (or the draft) holds, the river's own files left out."""
    cells = rs.cells_at(shift)
    mids = [(BLOCK * c[0] + BLOCK / 2.0, -(BLOCK * c[1] + BLOCK / 2.0)) for c in cells]
    if same_shift(shift, river_at):
        return {"ok": False, "why": "the river is here now", "where": [], "blocks": cells}
    taken = occupied(cells)
    if taken:
        folders = sorted({f for fs in taken.values() for f in fs})
        return {"ok": False, "why": f"{len(taken)} of its {len(cells)} blocks already hold an edit in "
                                    + ", ".join(folders),
                "where": [m for c, m in zip(cells, mids) if c in taken], "blocks": cells}
    return {"ok": True, "why": "", "where": [], "blocks": cells}


def free_shifts(rs: RiverShape, *, river_at, occupied) -> list:
    """Every fitting shift the preview passes (the free placements), nearest first."""
    return [s for s in rs.shifts if preview(rs, s, river_at=river_at, occupied=occupied)["ok"]]


def cell_of_path(p):
    """The ``(bx, by)`` block of a world override file's path, or None."""
    import re
    m = re.search(r"Block\[(\d+)\]\[(\d+)\]", str(p))
    return (int(m.group(1)), int(m.group(2))) if m else None


def command(mod_folder, shift, *, move_from=None, dry_run: bool = True, report=None) -> list:
    """The ``world-river`` argv (after ``python -m ff9mapkit``): the cluster-c carry at ``shift``, moved from the
    deploy at shift ``move_from`` when given. The ``=`` form keeps a negative DX from reading as a flag."""
    dx, dz = offset_of(shift)
    argv = ["world-river", "--mod-folder", str(mod_folder), f"--at={fmt_num(dx, 1.0)},{fmt_num(dz, 1.0)}"]
    if move_from is not None:
        fx, fz = offset_of(move_from)
        argv.append(f"--move-from={fmt_num(fx, 1.0)},{fmt_num(fz, 1.0)}")
    if dry_run:
        argv.append("--dry-run")
    if report is not None:
        argv += ["--report-json", str(report)]
    return argv
