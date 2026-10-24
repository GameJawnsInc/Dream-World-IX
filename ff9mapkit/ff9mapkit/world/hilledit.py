"""A grass hill as the overworld editor drives it (rung 6): the island's own triangles lifted by the hill's raised
cosine as the ghost, the verb's cheap laws as a preview, and the ONE place the editor's ``world-hill`` command is
built.

THE CLI STAYS THE ORACLE: Check runs :func:`command` with ``--dry-run`` and Accept without, and both read the verdict
``--report-json`` writes. The ghost is not an approximation: ``interior.build_hill`` is a pure-Y displacement of the
island's deployed vertices by ``raised_cosine(distance, height, radius)``, so :func:`lifted` applies that very formula
to the same vertices, and the ghost is the hill the verb will write.

THE LAWS the preview runs are ``build_hill``'s own, over the same triangles, in its order: the footprint (pure mains
in a disc of radius + 2, at least 60 triangles, relief under 2.4u, clear of forest / stamps / rock), the displaced
triangles all mains, the flank (no face steeper than ``MAX_FLANK``, none facing down) and the peak cap. The crack gate
and the placement census run on Check.

THE DISC-4 HALF needs nothing here: a hill's disc-4 step is the mirror's COPY, which Promote runs in the live folder.
"""
from __future__ import annotations

import math

import numpy as np

from .forestedit import CENTRE_STEP, SoupIndex, fmt_num, read_verdict   # noqa: F401  (the tools' shared kit)

DONOR = "hill"                    # the card's one "donor": a hill carries nothing
RIM_N = 48


def _fam(ix: SoupIndex) -> np.ndarray:
    f = getattr(ix, "_hill_fam", None)
    if f is None:
        f = ix._hill_fam = np.array([m[2] for m in ix._meta])
        ix._hill_cy = ix.pos[ix.tris][..., 1].mean(axis=1) if len(ix.tris) else np.zeros(0)
    return f


def lift(ix: SoupIndex, center, height: float, radius: float) -> np.ndarray:
    """Each soup vertex's lift: ``interior.raised_cosine`` of its plan distance to the centre."""
    d = np.hypot(ix.pos[:, 0] - center[0], ix.pos[:, 2] - center[1])
    return np.where(d >= radius, 0.0, height / 2.0 * (1.0 + np.cos(np.pi * np.minimum(d, radius) / radius)))


def lifted(ix: SoupIndex, center, height: float, radius: float):
    """``(tris, touched)``: the triangles the hill moves, ``(n, 3, 3)`` lifted, and their indices in the soup."""
    if not len(ix.tris):
        return np.zeros((0, 3, 3)), np.zeros(0, dtype=np.int64)
    up = lift(ix, center, height, radius)
    touched = np.flatnonzero((up[ix.tris] > 1e-9).any(axis=1))
    P = ix.pos.copy()
    P[:, 1] += up
    return P[ix.tris[touched]], touched


def rim(ix: SoupIndex, center, radius: float, ground_y: float) -> np.ndarray:
    """The hill's footprint circle, seated on ``ground_y`` (the ghost's rim)."""
    a = np.linspace(0.0, 2.0 * math.pi, RIM_N, endpoint=False)
    return np.column_stack([center[0] + radius * np.cos(a), np.full(RIM_N, ground_y), center[1] + radius * np.sin(a)])


def preview(ix: SoupIndex, center, height: float, radius: float) -> dict:
    """``build_hill``'s laws at an exact centre: ``{"ok", "gate", "why", "where", "report"}``."""
    from . import interior as IN
    cx, cz = float(center[0]), float(center[1])
    if not len(ix.tris):
        return {"ok": False, "gate": "footprint", "why": "no island here", "where": [], "report": {}}
    fam = _fam(ix)
    foot = radius + 2.0
    d2 = (ix.cent[:, 0] - cx) ** 2 + (ix.cent[:, 1] - cz) ** 2
    sel = d2 < foot ** 2

    def refuse(gate, why, where):
        return {"ok": False, "gate": gate, "why": why, "where": [tuple(map(float, w)) for w in where][:24],
                "report": {}}
    if sel.sum() < 60:
        return refuse("footprint", "the hill's footprint runs off the island", [(cx, cz)])
    bad = np.flatnonzero(sel & (fam != "main"))
    if len(bad):
        return refuse("footprint", f"the footprint meets {ix.what[bad[0]]}", ix.cent[bad])
    cy = ix._hill_cy[sel]
    if float(cy.max() - cy.min()) > 2.4:
        return refuse("footprint", "the footprint is not level ground (an earlier hill or the island's relief)",
                      [(cx, cz)])
    for f, clear in (("forest", IN.FOREST_CLEAR), ("stamp", IN.STAMP_CLEAR), ("rock", IN.RIM_CLEAR)):
        near = fam == f
        if near.any() and float(np.sqrt(d2[near].min())) - foot < clear:
            k = np.flatnonzero(near)[int(np.argmin(d2[near]))]
            what = {"forest": "a forest", "stamp": "a meadow stamp", "rock": "the coast's rock"}[f]
            return refuse("footprint", f"the footprint comes within {clear:g}u of {what}", [ix.cent[k]])
    tris, touched = lifted(ix, (cx, cz), height, radius)
    notmain = touched[fam[touched] != "main"]
    if len(notmain):
        return refuse("footprint", f"the hill would lift {ix.what[notmain[0]]}", ix.cent[notmain])
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    n = np.cross(b - a, c - a)
    L = np.linalg.norm(n, axis=1)
    L = np.where(L > 0, L, 1.0)
    slope = np.degrees(np.arccos(np.minimum(1.0, np.abs(n[:, 1]) / L)))
    down = n[:, 1] <= 0
    worst = float(slope.max()) if len(slope) else 0.0
    peak = float(tris[..., 1].max()) if len(tris) else 0.0
    report = {"displaced_tris": int(len(touched)), "worst_flank": round(worst, 1), "peak_y": round(peak, 2)}
    if worst > IN.MAX_FLANK or down.any():
        where = ix.cent[touched[down]] if down.any() else [ix.cent[touched[int(np.argmax(slope))]]]
        return {**refuse("flank", f"a flank leans {worst:.1f}° (the limit is {IN.MAX_FLANK}°): lower it or widen "
                                  "it", where), "report": report}
    if peak > IN.PEAK_CAP:
        k = np.unravel_index(int(np.argmax(tris[..., 1])), tris.shape[:2])
        return {**refuse("peak", f"its top at y {peak:.2f} leaves the lowland band (the cap is {IN.PEAK_CAP})",
                         [(tris[k][0], tris[k][2])]), "report": report}
    return {"ok": True, "gate": None, "why": "", "where": [], "report": report}


def command(mod_folder, center, *, height: float = 4.2, radius: float = 18.0, dry_run: bool = True,
            report=None) -> list:
    """The ``world-hill`` argv (after ``python -m ff9mapkit``): an exact centre; the sizes only off their defaults
    (as a hand-typed command leaves them)."""
    from .handles import handle
    argv = ["world-hill", "--mod-folder", str(mod_folder),
            "--center", f"{fmt_num(center[0], CENTRE_STEP)},{fmt_num(center[1], CENTRE_STEP)}"]
    for key, val in (("height", height), ("radius", radius)):
        if abs(float(val) - handle("hill", key).default) > 1e-9:
            argv += [f"--{key}", fmt_num(val, 0.1)]
    if dry_run:
        argv.append("--dry-run")
    if report is not None:
        argv += ["--report-json", str(report)]
    return argv
