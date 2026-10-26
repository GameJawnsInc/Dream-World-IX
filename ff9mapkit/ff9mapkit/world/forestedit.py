"""The forest as the overworld editor drives it (rung C1): the qualified canopies, a canopy's ghost outline, the
footprint law as a fast preview, and the ONE place the editor's ``world-forest`` command line is built.

THE CLI STAYS THE ORACLE. The editor never carves in its own process: Check and Accept run
:func:`command`'s argv, which is ``world-forest`` itself (``--dry-run`` for Check), and read back the verdict
``--report-json`` writes. So an editor-placed forest is, by construction, the same call writing the same bytes as
the command typed by hand (``tests/test_world_forestedit.py`` holds both halves of that).

The preview (:func:`footprint_preview`) is the carve's footprint law (``interior.carve_forest``'s
``footprint_lawful``), vectorised so it can run while a handle moves. It is the same predicate, fenced against the
gate's own loop at many centres, and still only a preview: the carve's other gates (the step law, the walk-in
simulation, the placement census) run on Check.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from . import interior as IN
from .extract import decode_id

CENTRE_STEP = 0.1                  # the editor's centre resolution (world units): commands stay short and exact
SPREAD_STEP = 0.05                 # the spread spin's arrow step
SPREAD_RES = 0.01                  # ...and its resolution (two decimals): a typed 1.33 runs as 1.33, never 1.35


def canopy_donors() -> list:
    """The qualified canopy rows of ``donors.toml``, the donor picker's whole list (the picker cannot offer a
    canopy the catalogue has not qualified). Each row gains ``donor``: the ``(bx, by)`` ``--donor`` names, the
    rect's first block (the block whose blob the reader gathers whole)."""
    from .donors import load_donors, spec_blocks
    from .handles import handle
    cls = handle("forest", "donor").catalogue
    out = []
    for r in load_donors():
        if r.get("class") == cls and r.get("status") == "qualified":
            out.append({**r, "donor": min(spec_blocks(r["blocks"]))})
    return out


@dataclass
class Outline:
    """A canopy donor's blob in its own frame: plan about the blob centre, heights above its rim's median."""
    donor: tuple
    tris: np.ndarray               # (n, 3, 3) the blob's triangles
    rim: np.ndarray                # (m, 3) the rim ring, in order
    size: tuple                    # (width x, depth z) of the unturned, unspread blob


def outline(donor, *, disc: int = 1, game=None) -> Outline:
    """Read donor ``(bx, by)``'s canopy blob (stock, about a second) the way ``carve_forest`` gathers it."""
    from collections import Counter
    dv_w, _uv, _n, _t, dtris, blob, _bb = IN._forest_donor(tuple(donor), disc=disc, game=game)
    bpts = np.array([dv_w[i] for t in blob for i in dtris[t]])
    cx = (bpts[:, 0].min() + bpts[:, 0].max()) / 2
    cz = (bpts[:, 2].min() + bpts[:, 2].max()) / 2
    eu = Counter()
    for t in blob:
        tri = dtris[t]
        for a, b in ((0, 1), (1, 2), (2, 0)):
            eu[tuple(sorted((IN.kk3(dv_w[tri[a]]), IN.kk3(dv_w[tri[b]]))))] += 1
    rim = np.array(IN.chain_ring([e for e, n in eu.items() if n == 1], "donor rim", min_len=IN.FOREST_RIM_MIN),
                   dtype=np.float64)
    base = np.array([cx, float(np.median(rim[:, 1])), cz])
    tris = np.array([[dv_w[i] for i in dtris[t]] for t in blob], dtype=np.float64) - base
    return Outline(tuple(donor), tris, rim - base,
                   (float(bpts[:, 0].max() - bpts[:, 0].min()), float(bpts[:, 2].max() - bpts[:, 2].min())))


def plan_xz(xz: np.ndarray, *, spread: float, rot_deg: float) -> np.ndarray:
    """``_forest_plan``'s map on plan points about the origin: turn ``rot_deg`` (positive turns east -> south, a
    whole quarter turn the exact swap), then scale ``spread``."""
    x, z = xz[..., 0], xz[..., 1]
    d = float(rot_deg or 0.0) % 360.0
    if d % 90.0 == 0.0:
        for _ in range(int(d // 90)):
            x, z = z, -x
    else:
        c, s = math.cos(math.radians(d)), math.sin(math.radians(d))
        x, z = c * x + s * z, -s * x + c * z
    return np.stack([x * spread, z * spread], axis=-1)


def placed(ol: Outline, center, *, spread: float = 1.0, rot_deg: float = 0.0, ground_y: float = 0.0):
    """The ghost at ``center``: ``(tris (n, 3, 3), rim (m, 3))`` in world units, the rim on ``ground_y``."""
    cx, cz = center
    t = ol.tris.copy()
    t[..., [0, 2]] = plan_xz(ol.tris[..., [0, 2]], spread=spread, rot_deg=rot_deg) + (cx, cz)
    t[..., 1] += ground_y
    r = ol.rim.copy()
    r[:, [0, 2]] = plan_xz(ol.rim[:, [0, 2]], spread=spread, rot_deg=rot_deg) + (cx, cz)
    r[:, 1] += ground_y
    return t, r


# ---------------------------------------------------------------- the footprint law, vectorised
class SoupIndex:
    """One island soup's arrays for :func:`footprint_preview` (built once per read window)."""

    def __init__(self, soup):
        pos = np.asarray(soup["pos"], dtype=np.float64)
        tris = np.asarray(soup["tris"], dtype=np.int64)
        self.pos, self.tris = pos, tris
        self._meta = soup["meta"]                                                 # (block, idall, fam, uvs) per tri
        self.corner = pos[tris][..., [0, 2]] if len(tris) else np.zeros((0, 3, 2))   # (n, 3, 2)
        self.cent = np.array(IN._tri_centroids(soup), dtype=np.float64).reshape(-1, 2)  # the gate's own floats
        self.grass = np.array([m[2] == "main" and decode_id(int(round(m[1])))["topograph"] == 0
                               for m in soup["meta"]], dtype=bool)
        self.what = [IN.ground_words(m[2], decode_id(int(round(m[1])))["topograph"]) for m in soup["meta"]]
        self.coast = np.asarray(soup["coast"], dtype=np.float64).reshape(-1, 2)
        self.blocks = set(soup["blocks"])
        self.lo, self.hi = self.corner.min(axis=1), self.corner.max(axis=1)     # each tri's plan box

    def ground_y(self, x, z):
        """The soup's surface height under ``(x, z)`` (the top hit), or None off the island."""
        cand = np.flatnonzero((self.lo[:, 0] <= x) & (x <= self.hi[:, 0]) & (self.lo[:, 1] <= z) & (z <= self.hi[:, 1]))
        if not len(cand):
            return None
        a, b, c = (self.pos[self.tris[cand]][:, k] for k in range(3))
        d = (b[:, 2] - c[:, 2]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 2] - c[:, 2])
        ok = np.abs(d) > 1e-12
        d = np.where(ok, d, 1.0)
        w0 = ((b[:, 2] - c[:, 2]) * (x - c[:, 0]) + (c[:, 0] - b[:, 0]) * (z - c[:, 2])) / d
        w1 = ((c[:, 2] - a[:, 2]) * (x - c[:, 0]) + (a[:, 0] - c[:, 0]) * (z - c[:, 2])) / d
        w2 = 1 - w0 - w1
        inside = ok & (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
        if not inside.any():
            return None
        y = w0 * a[:, 1] + w1 * b[:, 1] + w2 * c[:, 1]
        return float(y[inside].max())


def _pip(pts: np.ndarray, poly: np.ndarray) -> np.ndarray:
    """``interior.pip`` over many points: the same even-odd crossing test, the same 1e-12 guard."""
    px, pz = pts[..., 0][..., None], pts[..., 1][..., None]
    xi, zi = poly[:, 0], poly[:, 1]
    xj, zj = np.roll(poly[:, 0], 1), np.roll(poly[:, 1], 1)
    cross = ((zi > pz) != (zj > pz)) & (px < (xj - xi) * (pz - zi) / (zj - zi + 1e-12) + xi)
    return (cross.sum(axis=-1) % 2) == 1


def _near(pts: np.ndarray, poly: np.ndarray, d: float) -> np.ndarray:
    """``interior.near_poly`` over many points: within ``d`` (strictly) of an edge."""
    p = pts[..., None, :]
    a = poly
    e = np.roll(poly, -1, axis=0) - poly
    L2 = (e * e).sum(axis=1) + 1e-12
    t = np.clip(((p - a) * e).sum(axis=-1) / L2, 0.0, 1.0)
    q = a + t[..., None] * e
    dd = ((p - q) ** 2).sum(axis=-1)
    return (dd < d * d).any(axis=-1)


def footprint_preview(ix: SoupIndex, rim_xz) -> dict:
    """``carve_forest``'s footprint law for a ghost whose rim is ``rim_xz`` (world plan points, in order):
    ``{"ok", "seen", "where", "why"}``. ``ok`` is the gate's ``seen is not None and seen >= 40``."""
    poly = np.asarray(rim_xz, dtype=np.float64)
    if not len(ix.tris):
        return {"ok": False, "seen": None, "where": [], "why": "no island here"}
    # only a tri whose plan box meets the rim's box grown by the band can be in or near it (exact, not a heuristic);
    # the index holds each tri's box (taking them again was most of a drag frame: PERF.md 6)
    lo, hi = poly.min(axis=0) - IN.SCAN_BAND, poly.max(axis=0) + IN.SCAN_BAND
    cand = np.flatnonzero(((ix.hi >= lo) & (ix.lo <= hi)).all(axis=1))
    hit = _pip(ix.cent[cand], poly) | _near(ix.cent[cand], poly, IN.SCAN_BAND)
    rest = ~hit
    if rest.any():
        cor = ix.corner[cand[rest]]
        ch = (_pip(cor, poly) | _near(cor, poly, IN.SCAN_BAND)).any(axis=1)
        hit[np.flatnonzero(rest)[ch]] = True
    idx = cand[hit]
    bad = [i for i in idx if not ix.grass[i]]
    where, why = [tuple(ix.cent[i]) for i in bad[:12]], (ix.what[bad[0]] if bad else "")
    if not bad and len(ix.coast) and len(idx):
        v = ix.pos[ix.tris[idx]][..., [0, 2]].reshape(-1, 2)
        # a coast point outside the tested verts' box grown by RIM_MARGIN is farther than that from every one of them
        coast = ix.coast
        keep = ((coast >= v.min(axis=0) - IN.RIM_MARGIN) & (coast <= v.max(axis=0) + IN.RIM_MARGIN)).all(axis=1)
        coast = coast[keep]
        near_coast = np.zeros(len(v), dtype=bool)
        if len(coast):
            d2 = ((v[:, None, :] - coast[None, :, :]) ** 2).sum(axis=-1).min(axis=1)
            near_coast = d2 < IN.RIM_MARGIN ** 2
        if near_coast.any():
            where, why = [tuple(p) for p in v[near_coast][:12]], "the coast rim"
    if where:
        return {"ok": False, "seen": None, "where": where, "why": why}
    seen = int(len(idx))
    return {"ok": seen >= 40, "seen": seen, "where": [] if seen >= 40 else [tuple(poly.mean(axis=0))],
            "why": "" if seen >= 40 else "too little plain grass under it"}


# ---------------------------------------------------------------- the command and its verdict
def fmt_num(v: float, step: float) -> str:
    """``v`` on the handle's grid, printed short (``1400``, ``-462.5``, ``1.25``)."""
    q = round(round(float(v) / step) * step, 6)
    return f"{q:.6f}".rstrip("0").rstrip(".") if q != int(q) else str(int(q))


def command(mod_folder, center, donor, *, spread: float = 1.0, rot_deg: float = 0.0, dry_run: bool = True,
            report=None) -> list:
    """The ``world-forest`` argv (after ``python -m ff9mapkit``) for these handles -- what Check (``dry_run``)
    and Accept run, and what Copy command copies. Defaults are omitted, as a hand-typed command omits them."""
    argv = ["world-forest", "--mod-folder", str(mod_folder),
            "--center", f"{fmt_num(center[0], CENTRE_STEP)},{fmt_num(center[1], CENTRE_STEP)}",
            "--donor", f"{int(donor[0])},{int(donor[1])}"]
    if abs(float(spread) - 1.0) > 1e-9:
        argv += ["--spread", fmt_num(spread, SPREAD_RES)]
    if float(rot_deg or 0.0) % 360.0:
        argv += ["--rot", fmt_num(float(rot_deg) % 360.0, 1.0)]
    if dry_run:
        argv.append("--dry-run")
    if report is not None:
        argv += ["--report-json", str(report)]
    return argv


def disc4_words(v) -> str:
    """Where a two-call Accept (the sink's, the coast morph's) writes, as its Check's report says (``disc4``: the
    disc-4 preview's outcome)."""
    if (v or {}).get("disc4") == "refuses":
        return "on disc 1 only: disc 4's own replay refuses there, so disc 4 keeps its own ground"
    return "on disc 1 and on disc 4"


def read_verdict(path) -> dict | None:
    """The ``--report-json`` verdict, or None when the job wrote none (it died before deciding)."""
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
