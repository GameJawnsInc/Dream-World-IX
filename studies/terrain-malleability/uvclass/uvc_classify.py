"""uvclass THE CLASSIFIER -- one function, shared by the census and the calibration (synthetic + known cases).

Per edge-continuous UV PATCH (uvc_common.patches) -> (class, sub):

  L  lattice-tiled   -- a TILE-SCALE chart (uv extent <= 264 px = one 2x2 mains region, plan extent <= 9u = 2x2
                        cells) of REUSED art (sampled >= 2 blocks away, uvc_features reuse_far). The window is
                        chosen per cell; seams between cells are stock-normal (ground-junction synthesis: only
                        23.5% of stock cross-cell shared positions match).
                        sub L.rule = the art lies in a DECODED kit vocabulary (grassland GROUNDS mains rects,
                                     desert secondary, meadow D, B strip + translated STRIPS) -> retile by rule
                        sub L.free = tile-scale, reused, but no decoded window rule (canopy, brush, ...) ->
                                     layout must be carried; each chart is tiny so smooth deformation is local-affine
  P  planar          -- a CHART larger than a tile that is plan-affine T = A(x,z)+c within TAU, or an oblique
                        3D-affine projection whose invariant direction is >= 45 deg above horizontal.
                        (a tile-scale chart of UNIQUE art that is plan-affine is P.unique)
  W  wall-projected  -- not plan-affine; affine in (s,y) for a straight horizontal invariant (W.proj) or in
                        (arclength-along-own-curve, y) (W.arc), or oblique 3D-affine with invariant < 45 deg.
  W.keyed / L.keyed  -- a chart larger than a tile whose uv is KEYED to vertex ROLES (keying exponent kappa >= 0.6:
                        texel density ~ 1/tri size, i.e. the uv window is fixed whatever the geometry does -- the
                        coastal lip's one-tile-per-column course, uvc_probe_keying.py). Steep -> W.keyed (survives
                        height scaling and along-wall moves within the stock column/course envelope), flat -> L.keyed.
  M  mural / free    -- no affine chart fits within TAU and the chart is not keyed. sub M.smooth = a full quadratic in (x,y,z) fits within
                        TAU (a smooth curved field); M.flow = texture axis follows the contour (flow spread <=
                        15 deg; the rock band-sweep); M.free = neither. M.unique = tile-scale unique art, non-affine.

TAU (affine tolerance) = 8 px Moguri (= 4 u-quanta / 2 v-quanta; stock uv is quantized 1/1024 = 2px u, 4px v,
so an EXACT affine chart scores <= ~2.3 px -- uvc_calibrate.py C1 measures the floor). Sensitivity is reported
at TAU 4/16/32 by uvc_census.py.
"""
import math

import numpy as np

import sys
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
from ff9mapkit.world import grassland as G  # noqa: E402

TAU = 8.0
SMALL_EXT = 264.0
SMALL_PLAN = 9.0
REUSE_FAR = 2.0
FLOW_SPREAD = 15.0
KEYED_KAPPA = 0.6


def _decoded_regions():
    """Atlas rects (raw uv) of every DECODED kit tile vocabulary, padded by the measured bleed."""
    regs = []
    for g in G.GROUNDS:
        regs.append(("mains:" + g, G.ground_main_region(g)))
    lo_u, lo_v, hi_u, hi_v = G.FAM_REGION["main"]
    sd = G.DESERT_MAINS_SECONDARY
    regs.append(("mains:desert2", (lo_u + sd["du"], lo_v + sd["dv"], hi_u + sd["du"], hi_v + sd["dv"])))
    regs.append(("meadowD", G.FAM_REGION["D"]))
    b = G.FAM_REGION["B"]
    regs.append(("stripB", b))
    for (fa, fb), s in G.STRIPS.items():
        regs.append((f"strip:{fa}|{fb}", (b[0] + s["du"], b[1] + s["dv"], b[2] + s["du"], b[3] + s["dv"])))
    return regs


DECODED = _decoded_regions()
PAD_U, PAD_V = 20 / 2048.0, 20 / 4096.0          # ~ the mains bleed (+-0.15 quadrant ~ 19px)


def in_decoded(u, v):
    for name, (u0, v0, u1, v1) in DECODED:
        if u0 - PAD_U <= u <= u1 + PAD_U and v0 - PAD_V <= v <= v1 + PAD_V:
            return name
    return None


def _ok(x, tau):
    return (x is not None) and (not (isinstance(x, float) and math.isnan(x))) and x <= tau


def classify(row: dict, tau: float = TAU):
    """row: patch features (uvc_features cols) + 'reuse_far' (patch median) + 'decoded' (name or None)."""
    ext = max(row["uv_ext_u"], row["uv_ext_v"])
    small = ext <= SMALL_EXT and row["plan_ext"] <= SMALL_PLAN
    reused = row.get("reuse_far", 99) >= REUSE_FAR
    cell_ok = math.isnan(row["cell_plan_max"]) or row["cell_plan_max"] <= tau
    if small:
        if reused:
            return ("L", "L.rule" if row.get("decoded") else "L.free")
        return ("P", "P.unique") if cell_ok else ("M", "M.unique")
    if _ok(row["plan_max"], tau):
        return ("P", "P.chart")
    if _ok(row["wall_max"], tau):
        return ("W", "W.proj")
    if _ok(row["arc_max"], tau):
        return ("W", "W.arc")
    if _ok(row["a3_max"], tau) and row["nonplanar_deg"] >= 10:
        return ("P", "P.oblique") if row["a3_elev"] >= 45 else ("W", "W.oblique")
    if math.isnan(row["plan_max"]):                    # too few distinct verts to fit a chart (m < 5)
        return ("W", "W.unfit") if row["slope_p50"] >= 45 else ("P", "P.unfit")
    k = row.get("kappa", float("nan"))
    if not math.isnan(k) and k >= KEYED_KAPPA:         # uv KEYED to vertex roles (tile corners), not projected
        return ("W", "W.keyed") if row["slope_p50"] >= 45 else ("L", "L.keyed")
    if _ok(row["quad_max"], tau):
        return ("M", "M.smooth")
    if not math.isnan(row["flow_spread"]) and row["flow_spread"] <= FLOW_SPREAD:
        return ("M", "M.flow")
    return ("M", "M.free")


CLASSES = ("L", "P", "W", "M")
SUBS = ("L.rule", "L.free", "L.keyed", "P.chart", "P.oblique", "P.unique", "P.unfit", "W.proj", "W.arc",
        "W.oblique", "W.keyed", "W.unfit", "M.smooth", "M.flow", "M.free", "M.unique")


def patch_rows(z):
    """Build per-patch row dicts from a features npz (uvc_features.py output) + raw uv for the decoded test."""
    cols = list(z["cols"])
    F = z["F"]
    pid = z["pid"]
    NP = len(F)
    # patch median far-reuse
    order = np.argsort(pid, kind="stable")
    sp = pid[order]
    bounds = np.searchsorted(sp, np.arange(NP + 1))
    rf = z["reuse_far"][order]
    reuse = np.array([np.median(rf[bounds[p]:bounds[p + 1]]) if bounds[p + 1] > bounds[p] else 0
                      for p in range(NP)])
    rows = []
    for p in range(NP):
        r = {c: float(F[p, i]) for i, c in enumerate(cols)}
        r["reuse_far"] = float(reuse[p])
        rows.append(r)
    return rows, order, bounds
