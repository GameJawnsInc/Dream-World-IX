"""The mountain as the overworld editor drives it (rung C2): the qualified massifs, a massif's ghost outline (its
rock stretched by ``--rock-height`` exactly as the carve stretches it), the placement laws as a fast preview, the
island's ground and the donor's home ground, and the ONE place the editor's ``world-mountain`` command is built.

THE CLI STAYS THE ORACLE, as for the forest (:mod:`world.forestedit`): Check and Accept run :func:`command`'s argv,
``world-mountain`` itself, and read back the verdict ``--report-json`` writes.

The preview (:func:`footprint_preview`) is ``interior.carve_mountain``'s exact-placement laws in its own order --
the deployed blocks the span needs, the working band inside the span, then the band clear of every non-plain tri
(``band_offenders``) -- vectorised so it can run while a handle moves, and fenced against the carve at many
centres. It is still only a preview: the carve's other gates (the hole, the zip, rock rigidity, the apron, the
probes, the atlas and the placement census) run on Check.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from . import grassland as G
from . import interior as IN
from .extract import decode_id
from .forestedit import CENTRE_STEP, SPREAD_RES, SPREAD_STEP, SoupIndex, _near, _pip, fmt_num, plan_xz, read_verdict

__all__ = ["CENTRE_STEP", "SPREAD_STEP", "SPREAD_RES", "HEIGHT_STEP", "HEIGHT_RES", "SoupIndex", "fmt_num",
           "read_verdict", "massif_donors", "MassifOutline", "outline", "placed", "island_ground", "reach_for",
           "footprint_preview", "command"]

HEIGHT_STEP = 0.05                 # the rock-height spin's arrow step
HEIGHT_RES = 0.01                  # ...and its resolution
BAND = IN.MTN_CLEAR + 4.0          # carve_mountain's SCAN_BAND (its default)
DEFAULT_REACH = 96.0               # world-mountain --reach's default


def _blocks(spec: str) -> list:
    """A ``--donor`` rect spec as ``cli._parse_block_rect`` lists it (x-major), the order the carve reads."""
    from .donors import spec_blocks
    return sorted(spec_blocks(spec))


def massif_donors() -> list:
    """The qualified massif rows of ``donors.toml``, the donor picker's whole list. Each row gains ``donor``: the
    ``--donor`` spelling (the row's own rect spec)."""
    from .donors import load_donors
    from .handles import handle
    cls = handle("mountain", "donor").catalogue
    return [{**r, "donor": r["blocks"]} for r in load_donors()
            if r.get("class") == cls and r.get("status") == "qualified"]


@dataclass
class MassifOutline:
    """A massif donor's rock blob in its own frame: plan about the blob centre, heights above its de-tilted rim's
    median (the carve seats that median on the ground). ``height_ok`` is False for a massif ``--rock-height``
    refuses (geometry on its face the stretch would leave behind: the horseshoe's falls)."""
    donor: str
    tris: np.ndarray               # (n, 3, 3) the blob's triangles, unstretched
    rim: np.ndarray                # (m, 3) the rim ring, in order
    r_rim: float                   # the rim's widest plan radius, unspread (the span law sizes from it)
    height_ok: bool
    home_ground: str | None
    base: np.ndarray = field(repr=False, default=None)   # the donor-frame point the ghost's origin is
    blob: dict = field(repr=False, default_factory=dict)
    _stretched: dict = field(repr=False, default_factory=dict)

    def tris_at(self, rock_height: float) -> np.ndarray:
        """The blob at ``rock_height``: ``interior._rock_height_map`` itself (tens of milliseconds), cached."""
        s = round(float(rock_height), 6)
        if s == 1.0 or not self.height_ok:
            return self.tris
        if s not in self._stretched:
            B = self.blob
            V2, _n, _ref, _r = IN._rock_height_map(B, s, rock_topos=IN.MOUNTAIN_ROCK_TOPOS, log=lambda *a: None)
            self._stretched[s] = np.array([[V2[i] for i in B["dtri"][t]] for t in B["blob"]],
                                          dtype=np.float64) - self.base
        return self._stretched[s]


def outline(donor: str, *, disc: int = 1, game=None) -> MassifOutline:
    """Read massif ``donor`` (a ``--donor`` rect spec) the way ``world-mountain`` gathers it: the catalogue's
    alcove, else Uaho's own, then ``interior._mountain_blob`` (a stock read, under a second or two)."""
    from .donors import catalog_alcove, row_for_blocks
    blocks = _blocks(donor)
    alcove = catalog_alcove(blocks)
    if alcove is None:
        alcove = IN.UAHO_ALCOVE if blocks == [IN.MOUNTAIN_DONOR] else None
    B = IN._mountain_blob(blocks, rock_topos=IN.MOUNTAIN_ROCK_TOPOS, alcove_box=alcove, disc=disc, game=game,
                          log=lambda *a: None)
    cx, cz = B["c_local"]
    base = np.array([cx, float(np.median([p[1] for p in B["rim2"]])), cz])
    dV2 = np.asarray(B["dV2"], dtype=np.float64)
    tris = np.array([[dV2[i] for i in B["dtri"][t]] for t in B["blob"]], dtype=np.float64) - base
    rim = np.array(B["rim2"], dtype=np.float64) - base
    row = row_for_blocks(blocks) or {}
    ol = MassifOutline(donor, tris, rim, float(B["r_rim"]),
                       height_ok=not (B["ensemble_apertures"] or B["sweep"]),
                       home_ground=row.get("home_ground"), base=base, blob=B)
    return ol


def placed(ol: MassifOutline, center, *, spread: float = 1.0, rot_deg: float = 0.0, rock_height: float = 1.0,
           ground_y: float = 0.0):
    """The ghost at ``center``: ``(tris (n, 3, 3), rim (m, 3))`` in world units, the rim median on ``ground_y``.
    The plan map is the carve's ``rot_pt`` (scale, then turn: the same map, a uniform scale commutes)."""
    cx, cz = center
    t = ol.tris_at(rock_height).copy()
    t[..., [0, 2]] = plan_xz(t[..., [0, 2]], spread=spread, rot_deg=rot_deg) + (cx, cz)
    t[..., 1] += ground_y
    r = ol.rim.copy()
    r[:, [0, 2]] = plan_xz(ol.rim[:, [0, 2]], spread=spread, rot_deg=rot_deg) + (cx, cz)
    r[:, 1] += ground_y
    return t, r


# ---------------------------------------------------------------- the island's ground, the read window
_TOPO_GROUND = {g["topo"]: name for name, g in G.GROUNDS.items()}


def _massif_arrays(ix: SoupIndex):
    """The per-tri arrays the massif laws need, built once per island read: block, topograph, corner u."""
    if getattr(ix, "_mtn", None) is None:
        meta = ix._meta
        blk = np.array([m[0] for m in meta], dtype=np.int64).reshape(-1, 2)
        topo = np.array([decode_id(int(round(m[1])))["topograph"] for m in meta], dtype=np.int64)
        u = np.array([[uv[0] for uv in m[3]] for m in meta], dtype=np.float64).reshape(-1, 3)
        ix._mtn = (blk, topo, u)
    return ix._mtn


def island_ground(ix: SoupIndex, x: float, z: float) -> str:
    """The ground family ``world-mountain --ground`` should speak at ``(x, z)``: the family of the walkable
    ground there (the top hit), else the most common ground family in its block, else grass."""
    blk, topo, _u = _massif_arrays(ix)
    lo, hi = ix.lo, ix.hi
    cand = np.flatnonzero((lo[:, 0] <= x) & (x <= hi[:, 0]) & (lo[:, 1] <= z) & (z <= hi[:, 1]))
    for t in cand:
        if _inside(ix, t, x, z) and int(topo[t]) in _TOPO_GROUND:
            return _TOPO_GROUND[int(topo[t])]
    b = (math.floor(x / IN.BLOCK), math.floor(-z / IN.BLOCK))
    here = topo[(blk[:, 0] == b[0]) & (blk[:, 1] == b[1])]
    counts = {name: int((here == g).sum()) for g, name in _TOPO_GROUND.items()}
    best = max(counts, key=counts.get) if counts else "grass"
    return best if counts.get(best) else "grass"


def _inside(ix, t, x, z):
    a, b, c = (ix.pos[ix.tris[t]][k] for k in range(3))
    d = (b[2] - c[2]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[2] - c[2])
    if abs(d) <= 1e-12:
        return False
    w0 = ((b[2] - c[2]) * (x - c[0]) + (c[0] - b[0]) * (z - c[2])) / d
    w1 = ((c[2] - a[2]) * (x - c[0]) + (a[0] - c[0]) * (z - c[2])) / d
    return w0 >= -1e-9 and w1 >= -1e-9 and 1 - w0 - w1 >= -1e-9


def reach_for(r_placed: float, *, gblend: float = IN.MTN_GBLEND) -> float:
    """The ``--reach`` the carve needs to see every block its span can take (the apron rect, ``r + gblend + 2``):
    the default 96 unless the placed massif is wider (the snow ridge spread past x1.2)."""
    need = r_placed + gblend + 2.0
    return DEFAULT_REACH if need <= DEFAULT_REACH else float(8 * math.ceil(need / 8.0))


def _window(center, reach):
    """``read_deployed_blocks``' window: the blocks whose rect meets ``center +- reach``."""
    wx, wz = center
    bx0, bx1 = math.floor((wx - reach) / IN.BLOCK), math.floor((wx + reach) / IN.BLOCK)
    by0, by1 = math.floor(-(wz + reach) / IN.BLOCK), math.floor(-(wz - reach) / IN.BLOCK)
    return lambda b: bx0 <= b[0] <= bx1 and by0 <= b[1] <= by1


# ---------------------------------------------------------------- the placement laws, vectorised
def footprint_preview(ix: SoupIndex, center, rim_xz, r_placed: float, *, ground: str = "grass",
                      gblend: float = IN.MTN_GBLEND) -> dict:
    """``carve_mountain``'s exact-placement laws for a ghost centred at ``center`` whose placed rim is ``rim_xz``
    (world plan points, in order) and whose widest rim radius is ``r_placed``: ``{"ok", "gate", "where", "why",
    "span"}``. The gates in the carve's order: ``blocks`` (the span needs deployed islands), ``span`` (the working
    band stays on covered ground), ``footprint`` (no non-plain tri in or near the band)."""
    poly = np.asarray(rim_xz, dtype=np.float64)
    reach = reach_for(r_placed, gblend=gblend)
    inwin = _window(center, reach)
    present = {b for b in ix.blocks if inwin(b)}
    CX, CZ = float(center[0]), float(center[1])
    B = IN.BLOCK
    seed = (math.floor(CX / B), math.floor(-CZ / B))
    half = r_placed + BAND + 2.0

    def rect(h):
        return [(bx, by) for by in range(math.floor(-(CZ + h) / B), math.floor(-(CZ - h) / B) + 1)
                for bx in range(math.floor((CX - h) / B), math.floor((CX + h) / B) + 1)]
    if not present:
        return {"ok": False, "gate": "blocks", "where": [], "why": "no island here", "span": []}
    nb = [b for b in rect(r_placed + gblend + 2.0) if b != seed and b in present]
    route = 2.0 * half <= B and bool(nb) and all(b in present for b in rect(half))
    if 2.0 * half <= B and not route:
        span = span_rect = [seed]
    else:
        core = rect(half)
        missing = [b for b in core if b not in present]
        if missing:
            return {"ok": False, "gate": "blocks", "where": [IN._block_mid(b) for b in sorted(missing)],
                    "why": f"{len(missing)} block{'s' if len(missing) != 1 else ''} with no island", "span": []}
        span = sorted(set(core) | {b for b in rect(r_placed + gblend + 2.0) if b in present})
        span_rect = core
    if any(b not in present for b in span):
        return {"ok": False, "gate": "blocks", "where": [IN._block_mid(seed)], "why": "no island here", "span": []}
    x0, x1 = B * min(b[0] for b in span_rect), B * (max(b[0] for b in span_rect) + 1)
    z0, z1 = -B * (max(b[1] for b in span_rect) + 1), -B * min(b[1] for b in span_rect)
    m = BAND + 2
    if poly[:, 0].min() < x0 + m or poly[:, 0].max() > x1 - m or poly[:, 1].min() < z0 + m \
            or poly[:, 1].max() > z1 - m:
        out = [tuple(p) for p in poly if not (x0 + m <= p[0] <= x1 - m and z0 + m <= p[1] <= z1 - m)]
        return {"ok": False, "gate": "span", "where": out, "why": "the edge of the deployed blocks", "span": span}
    blk, topo, u = _massif_arrays(ix)
    g = G.GROUNDS[ground]
    lo_u, hi_u = G.FAM_REGION["main"][0], G.FAM_REGION["main"][2]
    uu = u - g["mains_du"]
    plain = (topo == g["topo"]) & ((lo_u - 0.02 <= uu) & (uu <= hi_u + 0.02)).all(axis=1)
    in_span = np.zeros(len(blk), dtype=bool)
    for b in span:
        in_span |= (blk[:, 0] == b[0]) & (blk[:, 1] == b[1])
    lo, hi = poly.min(axis=0) - BAND, poly.max(axis=0) + BAND
    cand = np.flatnonzero(in_span & ~plain & ((ix.corner.max(axis=1) >= lo) & (ix.corner.min(axis=1) <= hi)).all(axis=1))
    hit = _pip(ix.cent[cand], poly) | _near(ix.cent[cand], poly, BAND)
    rest = ~hit
    if rest.any():
        cor = ix.corner[cand[rest]]
        ch = (_pip(cor, poly) | _near(cor, poly, BAND)).any(axis=1)
        hit[np.flatnonzero(rest)[ch]] = True
    bad = cand[hit]
    if len(bad):
        return {"ok": False, "gate": "footprint", "where": [tuple(ix.cent[t]) for t in bad[:12]],
                "why": IN.massif_ground_words(int(topo[bad[0]]), ground), "span": span}
    # THE ANCHOR (the carve's next refusal, the same gate): plain ground just outside the rim to seat it on -- a
    # deployed block holds only its land, so a rim over open sea inside one meets nothing above and is refused here
    near = np.flatnonzero(in_span & plain & ((ix.corner.max(axis=1) >= poly.min(axis=0) - IN.MTN_CLEAR - 3.0)
                                             & (ix.corner.min(axis=1) <= poly.max(axis=0) + IN.MTN_CLEAR + 3.0))
                          .all(axis=1))
    v = ix.corner[near].reshape(-1, 2)
    if not len(v) or not (~_pip(v, poly) & _near(v, poly, IN.MTN_CLEAR + 3.0)).any():
        return {"ok": False, "gate": "footprint", "where": [(CX, CZ)], "why": "no plain ground round its rim",
                "span": span}
    return {"ok": True, "gate": None, "where": [], "why": "", "span": span}


# ---------------------------------------------------------------- the command
def command(mod_folder, center, donor: str, *, spread: float = 1.0, rot_deg: float = 0.0, rock_height: float = 1.0,
            ground: str = "grass", reach: float = DEFAULT_REACH, dry_run: bool = True, report=None) -> list:
    """The ``world-mountain`` argv (after ``python -m ff9mapkit``) for these handles -- what Check (``dry_run``)
    and Accept run, and what Copy command copies. Defaults are omitted, as a hand-typed command omits them; the
    angle is always given (``--center`` alone means 0, but the editor's angle is a handle)."""
    argv = ["world-mountain", "--mod-folder", str(mod_folder),
            "--center", f"{fmt_num(center[0], CENTRE_STEP)},{fmt_num(center[1], CENTRE_STEP)}",
            "--donor", str(donor)]
    if float(rot_deg or 0.0) % 360.0:
        argv += ["--rot", fmt_num(float(rot_deg) % 360.0, 1.0)]
    if abs(float(spread) - 1.0) > 1e-9:
        argv += ["--spread", fmt_num(spread, SPREAD_RES)]
    if abs(float(rock_height) - 1.0) > 1e-9:
        argv += ["--rock-height", fmt_num(rock_height, HEIGHT_RES)]
    if ground != "grass":
        argv += ["--ground", ground]
    if float(reach) != DEFAULT_REACH:
        argv += ["--reach", fmt_num(reach, 1.0)]
    if dry_run:
        argv.append("--dry-run")
    if report is not None:
        argv += ["--report-json", str(report)]
    return argv
