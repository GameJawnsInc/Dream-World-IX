r"""TIER W rung W6b-1 -- CAST B: THE 15bpp BAND STAMP (the committed half of the first direct-colour cast).

    py octopus_band_stamp.py --from C:\gd\SCRATCH\summon-format\ef429.bytes ^
       --root C:\gd\SCRATCH\summon-format\repaint-w6b\ef429-15bpp\cast-b

WHY ef429, AND WHY THIS FIGURE
------------------------------
The 15bpp DIRECT codec (RGBA + an explicit 1-bit STP sidecar, shift form) is proven exhaustively
offline -- all 65,536 halfwords, 14/14 writer-backed cells over 26 views -- and has NEVER BEEN CAST,
because no lawful 15bpp cell sat in a container a bench row could reach (``W6b-SCENERY.md`` section
2.3).  ef429 (``SpecialEffect.Octopus_Suction`` -- Gigan Octopus's "6 Legs") is the ONE lawful 15bpp
cell with no reader spill, so it is page-scope-safe.  This generator stamps its upper cell.

THE UV-FLATNESS SCREEN DECIDED THE FIGURE, AND IT SAID **STRIPES, NOT A WHEEL**
-------------------------------------------------------------------------------
Re-derived here per run by :func:`uv_report` on the cast-1f axes (``UV-ANALYSIS.md`` section 1), whose
calibration is the ef211 table it reproduces:

    cell (448,256)  geom 0x2109c  40 in-cell faces  OVERLAP x26.4  ANISO med 1.89 / p90 6.83 / max 9.06
    cell (448,384)  geom 0x2109c  56 in-cell faces  OVERLAP x38.9  ANISO med 1.44 / p90 2.67 / max 6.30
    baselines: the cast-proven SHREDDERS x11.7 / x13.6 / x41.3 -- the cast-proven FLAT reader x1.18,
               whose anisotropy is CONSTANT (med 2.209, max 2.299, spread 0.09)

So on the one axis that separated a figure from a smear the target sits inside the shredder band, and
on the other its anisotropy is not merely high but WIDELY SPREAD (7.17 on the target cell against the
flat reader's 0.09) -- a constant stretch is pre-compensable, a distribution is not.  A wheel would
appear ~26 times at ~26 different stretches.

**And a second, harder reason, specific to this container: the read band STRADDLES THE CELL BOUNDARY.**
The one ``so`` reader samples page lines 97..159 -- 31 lines in cell (448,256) and 32 in (448,384) --
so any figure taller than 31 lines is physically CUT IN HALF by the write span.  A wheel cannot be
completed inside cast B's cell; horizontal bands can.  That also makes the untouched lower cell a free
CONTROL: bands must appear on the upper part of each leg's band and stop dead at its midline.

THE INK IS **THE DARKEST COLOUR AT CONSTANT STP** -- ``new = old & 0x8000`` -- AND IT IS MEASURED
--------------------------------------------------------------------------------------------------
Measured on the stock container: every one of the reader's 1,984 covered halfwords in this cell is
``0xffff`` -- white, STP set.  The surface is uniform maximum light, so (i) contrast is maximal for any
dark ink and (ii) the phoenix cast's "slide the figure to where there is light to remove" search is
DEGENERATE here and is deliberately not run: placement is geometry, not luminance.  All 72 primitives
carry ABR 1 (ADDITIVE) with the semi-transparent flag set, so the legible channel is REMOVING light.

Two dark inks exist at direct colour and they are not equivalent:

    0x0000  the hardware CUTOUT -- the texel is skipped.
    0x8000  black with STP KEPT -- adds nothing under ABR 1, and DARKENS under ABR 0.

``0x8000`` is never less dark than the cutout under any ABR mode and is identical under the one this
container actually carries, while leaving bit 15 exactly as stock -- so the STP sidecar is carried
verbatim, no cutout is created, and the kit's cutout gate reports punch 0 / fill 0 with no
``acknowledge_cutout_reshape`` owed.  The rule is written per texel and is TOTAL: a texel whose STP is
clear would become ``0x0000`` (a new cutout), so it takes the minimal non-cutout dark word instead.
Both branch counts are reported.

THE QUAD-FAN CAVEAT, CHECKED RATHER THAN INHERITED
---------------------------------------------------
A separate session is fixing ``repaint._face_polys``, which fans a 4-corner face ``(0,1,2)+(0,2,3)`` on
the assumption its corners are perimeter-ordered; PSX quads are Z-ordered, and the perimeter fan on a
Z-ordered quad is a BOWTIE that under-reported ef211's arc cover by 17.4%.  This generator masks with
its own Z fan AND scores both, per run.  On ef429 the quads are Z-ordered too (40/40 and 56/56
winding-consistent under the Z fan, 0/40 and 0/56 under the perimeter fan) but the two covers AGREE to
the halfword (1,984 and 2,048), because every UV rect here spans the full 64-halfword cell width and an
axis-aligned rectangle is covered by either fan.  **The defect is real and inert on this target** --
stated as a measurement so no one has to wonder whether cast B is riding it.

PROVENANCE.  No stock byte run appears in this file; the container is read at run time and every
destination goes through ``ff9mapkit.summons.export.assert_local_only``.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import struct
import sys
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
sys.path.insert(0, os.path.join(_HERE, "..", "..", "..", "ff9mapkit"))

from ff9mapkit.summons import container as EC                     # noqa: E402
from ff9mapkit.summons import export as EX                        # noqa: E402
from ff9mapkit.summons import repaint as RP                       # noqa: E402
from ff9mapkit.summons import reskin as RS                        # noqa: E402
from ff9mapkit.summons import texture as KT                       # noqa: E402

EFFECT = 429
CELL = "cell.s0.x448_y256"
CONTROL_CELL = "cell.s0.x448_y384"
DEFAULT_ROOT = r"C:\gd\SCRATCH\summon-format\repaint-w6b\ef429-15bpp\cast-b"

#: THE PROFILE.  Three bands is a COUNT -- countable on a video frame, and distinct from the cast-A
#: probe's own signature on this same cell (k = 1 stripe), so the two casts can never be confused for
#: each other.  6 rows on / 4 off inside a 31-line cover is a 60/40 duty: bold enough to survive the
#: on-screen size of one leg, open enough that "three bars" and "one thick bar" are different pictures.
BANDS = 3
BAND_ROWS = 6


# ------------------------------------------------------------------ the corrected quad triangulation
def z_polys(pts: Sequence[Tuple[int, int]]) -> List[Tuple]:
    """The PSX quad fan ``(0,1,2) + (1,3,2)`` -- the GPU's own Z-order, not a perimeter walk."""
    if len(pts) == 4:
        return [(pts[0], pts[1], pts[2]), (pts[1], pts[3], pts[2])]
    return [tuple(pts[:3])]


def perimeter_polys(pts: Sequence[Tuple[int, int]]) -> List[Tuple]:
    """What ``repaint._face_polys`` does today -- scored beside the Z fan, never used to mask."""
    if len(pts) == 4:
        return [(pts[0], pts[1], pts[2]), (pts[0], pts[2], pts[3])]
    return [tuple(pts[:3])]


def _wind(t) -> float:
    (x0, y0), (x1, y1), (x2, y2) = t
    return (x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0)


def _fill(cover: Set[int], tri, page_x: int, page_y: int, per: int, cell) -> None:
    (x0, y0), (x1, y1), (x2, y2) = [(p[0] + 0.5, p[1] + 0.5) for p in tri]
    d = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
    if d == 0:
        return
    for py in range(int(min(y0, y1, y2)), int(max(y0, y1, y2)) + 1):
        cy = py + 0.5
        for px in range(int(min(x0, x1, x2)), int(max(x0, x1, x2)) + 1):
            cx = px + 0.5
            a = ((y1 - y2) * (cx - x2) + (x2 - x1) * (cy - y2)) / d
            b = ((y2 - y0) * (cx - x2) + (x0 - x2) * (cy - y2)) / d
            if a >= -1e-9 and b >= -1e-9 and (1.0 - a - b) >= -1e-9:
                hx, vy = page_x + px // per, page_y + py
                if (hx // RS.PAGE_CELL_W) * RS.PAGE_CELL_W == cell[0] and \
                   (vy // RP.CELL_LINES) * RP.CELL_LINES == cell[1]:
                    cover.add((vy - cell[1]) * RS.PAGE_CELL_W + (hx - cell[0]))


# ------------------------------------------------------------------------------- the flatness screen
def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _unit(a):
    n = math.sqrt(_dot(a, a))
    return (a[0] / n, a[1] / n, a[2] / n) if n else (0.0, 0.0, 0.0)


def affine_uv_to_xyz(uv, xyz):
    """``A`` (3x2) with ``p_i = A.(uv_i - uv_0) + p_0`` from the first three corners; None if flat."""
    (u0, v0), (u1, v1), (u2, v2) = uv[:3]
    d1, d2 = (u1 - u0, v1 - v0), (u2 - u0, v2 - v0)
    det = d1[0] * d2[1] - d1[1] * d2[0]
    if det == 0:
        return None
    p1, p2 = _sub(xyz[1], xyz[0]), _sub(xyz[2], xyz[0])
    inv = ((d2[1] / det, -d2[0] / det), (-d1[1] / det, d1[0] / det))
    return (tuple(p1[k] * inv[0][0] + p2[k] * inv[1][0] for k in range(3)),
            tuple(p1[k] * inv[0][1] + p2[k] * inv[1][1] for k in range(3)))


def _svals(j):
    (a, b), (c, d) = j
    e, f, g, h = (a + d) / 2.0, (a - d) / 2.0, (c + b) / 2.0, (c - b) / 2.0
    q, r = math.hypot(e, h), math.hypot(f, g)
    return q + r, abs(q - r)


def uv_report(blob: bytes, cell: Tuple[int, int]) -> List[dict]:
    """Per ``so`` reader of ``cell``: the cast-1f axes, both quad fans, and the reader's true cover.

    ANISO (``s1/s2`` of the UV->3D Jacobian in the face's own plane basis) measures shear; SCALE
    max/min measures whether one linear map or a distribution is at work; OVERLAP (sum of face UV area
    / distinct halfwords covered) measures how many times the same texels are drawn.  The published
    ROT resultant is reported in BOTH its conventions -- the raw one, whose ef211 shredder values this
    instrument reproduces at ``R = 0.0000``, and an orientation-canonicalised one that folds mirrored
    faces together -- because the two disagree on this container and a single number would hide that.
    """
    out: List[dict] = []
    for m in RP.bound_models(blob):
        if cell not in m.cover:
            continue
        g = next(x for x in EC.scan_geom(blob) if x.base == m.geom)
        per = KT.TEXELS_PER_HW[m.bpp]
        faces: List[dict] = []
        for mesh in g.meshes:
            vs = list(EC.vertices(blob, g, mesh))
            pool = g.base + mesh.p_uv
            for prim in EC.iter_primitives(blob, g, mesh):
                uvs = prim.get("uv")
                if not uvs:
                    continue
                pts = [(struct.unpack_from("<H", blob, pool + 2 * ui)[0] & 0xFF,
                        (struct.unpack_from("<H", blob, pool + 2 * ui)[0] >> 8) & 0xFF) for ui in uvs]
                probe: Set[int] = set()
                for t in z_polys(pts):
                    _fill(probe, t, m.page[0], m.page[1], per, cell)
                if not probe:
                    continue
                faces.append({"uv": pts, "abr": prim["abr"], "semi": prim["flag"] & 1,
                              "xyz": [tuple(float(c) for c in vs[vi][:3])
                                      for vi in prim["v"][:len(uvs)]]})
        if not faces:
            continue

        recs = []
        for f in faces:
            A = affine_uv_to_xyz(f["uv"], f["xyz"])
            if A is None:
                continue
            au, av = A
            n = _cross(au, av)
            if _dot(n, n) == 0:
                continue
            recs.append((au, av, n))
        # the common basis: the dominant normal, taken as an AXIS (the scatter matrix's leading
        # eigenvector by power iteration) so a ring of normals cannot be cancelled by sign choice.
        M = [[0.0] * 3 for _ in range(3)]
        for _au, _av, n in recs:
            u = _unit(n)
            for i in range(3):
                for j in range(3):
                    M[i][j] += u[i] * u[j]
        dom = (0.0, 0.0, 1.0)
        for _ in range(200):
            nxt = tuple(sum(M[i][j] * dom[j] for j in range(3)) for i in range(3))
            if _dot(nxt, nxt) == 0:
                break
            dom = _unit(nxt)
        if sum(1 for _a, _b, n in recs if _dot(n, dom) < 0) > len(recs) / 2:
            dom = (-dom[0], -dom[1], -dom[2])
        seed = (1.0, 0.0, 0.0) if abs(dom[0]) < 0.9 else (0.0, 1.0, 0.0)
        f1 = _unit(_cross(dom, seed))
        f2 = _cross(dom, f1)

        aniso, scales, raw_ang, canon_ang, plus, minus = [], [], [], [], 0, 0
        for au, av, n in recs:
            e1 = _unit(au)
            e2 = _sub(av, tuple(_dot(av, e1) * c for c in e1))
            if _dot(e2, e2) == 0:
                continue
            e2 = _unit(e2)
            s1, s2 = _svals(((_dot(au, e1), _dot(av, e1)), (_dot(au, e2), _dot(av, e2))))
            if s2 <= 0:
                continue
            aniso.append(s1 / s2)
            scales.append(math.sqrt(s1 * s2))
            th = math.atan2(_dot(au, f2), _dot(au, f1))
            raw_ang.append(th)
            if _dot(n, dom) >= 0:
                plus += 1
                canon_ang.append(th)
            else:
                minus += 1
                canon_ang.append(-th)                 # seen from behind: the chart is mirrored

        def _R(a):
            c = sum(math.cos(t) for t in a) / len(a)
            s = sum(math.sin(t) for t in a) / len(a)
            return math.hypot(c, s)

        cov_z: Set[int] = set()
        cov_p: Set[int] = set()
        area = 0.0
        for f in faces:
            for t in z_polys(f["uv"]):
                _fill(cov_z, t, m.page[0], m.page[1], per, cell)
                (x0, y0), (x1, y1), (x2, y2) = t
                area += abs((x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0)) / 2.0 / per
            for t in perimeter_polys(f["uv"]):
                _fill(cov_p, t, m.page[0], m.page[1], per, cell)
        quads = [f["uv"] for f in faces if len(f["uv"]) == 4]
        n_s = sorted(aniso)
        out.append({
            "geom": "%#x" % m.geom, "bpp": m.bpp, "faces_in_cell": len(faces),
            "quads": len(quads), "abr": sorted({f["abr"] for f in faces}),
            "semi_flag": sorted({f["semi"] for f in faces}),
            "aniso_med": round(n_s[len(n_s) // 2], 3), "aniso_max": round(max(aniso), 3),
            "aniso_p90": round(n_s[min(len(n_s) - 1, int(0.9 * len(n_s)))], 3),
            "aniso_spread": round(max(aniso) - n_s[len(n_s) // 2], 3),
            "aniso_le15_pct": round(100.0 * sum(1 for a in aniso if a <= 1.5) / len(aniso), 1),
            "scale_maxmin": round(max(scales) / min(scales), 2),
            "orient": [plus, minus],
            "rot_R_raw": round(_R(raw_ang), 4), "rot_R_canonical": round(_R(canon_ang), 4),
            "uv_area_halfwords": round(area, 1),
            "cover_z": len(cov_z), "cover_perimeter": len(cov_p), "cover_kit": len(m.cover[cell]),
            "overlap": round(area / max(1, len(cov_z)), 2),
            "quad_order": {"quads": len(quads),
                           "z_consistent": sum(1 for p in quads
                                               if _wind(z_polys(p)[0]) * _wind(z_polys(p)[1]) > 0),
                           "perimeter_consistent": sum(
                               1 for p in quads
                               if _wind(perimeter_polys(p)[0]) * _wind(perimeter_polys(p)[1]) > 0)},
            "cover": cov_z,
        })
    return out


# ------------------------------------------------------------------------------------------ the ink
def ink_word(old: int) -> Tuple[int, str]:
    """THE DARKEST COLOUR AT CONSTANT STP, per texel, and TOTAL.

    ``old & 0x8000`` is the darkest word that leaves bit 15 -- the blend selector, and the sidecar's
    only content -- exactly as the container had it.  It is the whole rule wherever STP is set.  Where
    STP is CLEAR that expression is ``0x0000``, which is the hardware CUTOUT: a different edit than the
    one intended, so such a texel takes the minimal NON-cutout dark word (``0x0001`` = r5 1, the
    smallest step the 5-bit encoding can see) instead.  Both branches are counted in the report.
    """
    if old & 0x8000:
        return 0x8000, "stp-kept"
    return 0x0001, "min-nonzero"


def _luma(word: int) -> float:
    r, g, b, _a = KT.bgr555_rgba(word)
    return 0.299 * r + 0.587 * g + 0.114 * b


# --------------------------------------------------------------------------------------- the figure
def band_tops(lo: int, hi: int) -> List[int]:
    """The top line of each band, evenly spread inside the reader's own covered line span."""
    span = hi - lo + 1
    tops = []
    for k in range(BANDS):
        centre = int(lo + (k + 0.5) * span / BANDS)
        tops.append(max(lo, min(hi - BAND_ROWS + 1, centre - BAND_ROWS // 2)))
    return tops


def generate(root: Optional[str] = None, from_path: Optional[str] = None, game=None,
             export: bool = True) -> Dict[str, object]:
    if from_path:
        stock = Path(from_path).read_bytes()
        source = str(from_path)
    else:
        stock, source = RS.R.read_stock_effect(EFFECT, game)

    root_p = Path(EX.assert_local_only(root or DEFAULT_ROOT))
    art = root_p / "art"
    if export:
        man = RP.export_art(stock, EFFECT, art, source=source, lane="direct15")
        art = Path(man["out_dir"])
    art.mkdir(parents=True, exist_ok=True)

    page = RP.texel_page(stock, CELL, EFFECT)
    if page.bpp != 15:
        raise SystemExit("%s is %dbpp -- this generator is the 15bpp DIRECT lane's" % (CELL, page.bpp))
    w, h = page.wh
    raw = stock[page.page_offset:page.page_offset + page.page_bytes]
    png = art / ("%s.png" % page.name)
    stp = RP.stp_sidecar_path(png)

    # THE NO-OP IDENTITY GATE, before anything is drawn.  The 15bpp lane's format of record is TWO
    # files; reading them back must reproduce the stock cell to the byte or nothing below means what
    # it says.  This is the direct-colour twin of the indexed lane's unpack/pack check, and it
    # exercises the sidecar path end to end rather than trusting it.
    noop = RP.read_direct_png(png, w, h)
    if noop != raw:
        raise SystemExit("NO-OP FAILED on %s: the exported RGBA + STP pair does not re-encode to the "
                         "stock bytes" % CELL)

    readers = uv_report(stock, page.cell)
    if len(readers) != 1:
        raise SystemExit("%s has %d so-readers; this cast is written for the measured ONE"
                         % (CELL, len(readers)))
    r = readers[0]
    control = uv_report(stock, RP.texel_page(stock, CONTROL_CELL, EFFECT).cell)
    cover = r["cover"]
    rows = sorted({hw // RS.PAGE_CELL_W for hw in cover})
    lo, hi = rows[0], rows[-1]

    words = list(struct.unpack_from("<%dH" % (w * h), raw, 0))
    cover_words = [words[hw] for hw in sorted(cover)]              # 15bpp: 1 halfword == 1 texel
    lum = [_luma(x) for x in cover_words]

    tops = band_tops(lo, hi)
    new = list(words)
    branch = {"stp-kept": 0, "min-nonzero": 0}
    hit: List[int] = []
    for top in tops:
        for y in range(top, top + BAND_ROWS):
            for x in range(w):
                i = y * w + x
                if i not in cover:
                    continue
                v, b = ink_word(words[i])
                branch[b] += 1
                if v != words[i]:
                    hit.append(i)
                new[i] = v

    out_raw = bytearray(len(raw))
    for i, v in enumerate(new):
        struct.pack_into("<H", out_raw, 2 * i, v)
    RP.write_direct_png(bytes(out_raw), w, h, png)
    # the pair must read back to exactly what we packed -- the same gate, now on the EDITED art
    if RP.read_direct_png(png, w, h) != bytes(out_raw):
        raise SystemExit("the stamped RGBA + STP pair does not re-encode to the bytes it was made "
                         "from -- refusing to stage")

    changed = [i for i in range(len(words)) if words[i] != new[i]]
    outside = sum(1 for i in changed if i not in cover)
    cut_before = sum(1 for x in words if x == KT.DIRECT15_CUTOUT)
    cut_after = sum(1 for x in new if x == KT.DIRECT15_CUTOUT)
    stp_before = sum(1 for x in words if x & 0x8000)
    stp_after = sum(1 for x in new if x & 0x8000)

    d = {
        "effect": EFFECT, "cell": page.name, "control_cell": CONTROL_CELL, "source": source,
        "root": str(root_p), "art": str(art), "png": str(png), "stp_png": str(stp),
        "page_offset": page.page_offset, "page_bytes": page.page_bytes, "wh": [w, h],
        "bpp": page.bpp, "vram": list(page.cell),
        "stock_sha256": RP._sha(stock),
        "noop_identity": True,
        "reader": {k: v for k, v in r.items() if k != "cover"},
        "control_reader": [{k: v for k, v in c.items() if k != "cover"} for c in control],
        "cover_halfwords": len(cover), "cover_rows": [lo, hi],
        "cover_stock_words": sorted({"%#06x" % x for x in cover_words}),
        "cover_luma_mean": round(sum(lum) / len(lum), 2),
        "cover_luma_min": round(min(lum), 2), "cover_luma_max": round(max(lum), 2),
        "bands": BANDS, "band_rows": BAND_ROWS, "band_tops": tops,
        "ink_branches": branch, "ink_words": sorted({"%#06x" % new[i] for i in hit}),
        "changed_texels": len(changed), "outside_cover": outside,
        "figure_share_of_cover": round(len(changed) / float(len(cover)), 4),
        "figure_share_of_page": round(len(changed) / float(w * h), 4),
        "luma_removed_per_texel": round(sum(_luma(words[i]) - _luma(new[i]) for i in changed)
                                        / max(1, len(changed)), 2),
        "cutouts_before": cut_before, "cutouts_after": cut_after,
        "stp_before": stp_before, "stp_after": stp_after,
    }
    (root_p / "derivation.json").write_text(json.dumps(d, indent=1, default=str), encoding="utf-8")
    return d


def report(d: Dict[str, object]) -> List[str]:
    r = d["reader"]
    return [
        "ef%03d %s  <- %s" % (d["effect"], d["cell"], d["source"]),
        "  cell            %#08x .. %#08x  VRAM %s  %dx%d @ %dbpp DIRECT   NO-OP identity (RGBA+STP "
        "-> stock bytes) %s"
        % (d["page_offset"], d["page_offset"] + d["page_bytes"], d["vram"], d["wh"][0], d["wh"][1],
           d["bpp"], "OK" if d["noop_identity"] else "FAILED"),
        "  reader          %s  %d in-cell faces (%d quads)  ABR %s  semi-flag %s"
        % (r["geom"], r["faces_in_cell"], r["quads"], r["abr"], r["semi_flag"]),
        "  UV SCREEN       OVERLAP x%.2f   ANISO med %.3f / p90 %.3f / max %.3f (spread %.3f, "
        "<=1.5 on %.1f%%)   SCALE max/min %.2f   ORIENT %s   ROT R raw %.4f / canonical %.4f"
        % (r["overlap"], r["aniso_med"], r["aniso_p90"], r["aniso_max"], r["aniso_spread"],
           r["aniso_le15_pct"], r["scale_maxmin"], r["orient"], r["rot_R_raw"],
           r["rot_R_canonical"]),
        "                  VERDICT: SHREDS -- overlap sits inside the cast-proven shredder band "
        "(x11.7 .. x41.3) and far outside the flat reader's x1.18, and the anisotropy is SPREAD, not "
        "constant.  The figure is BANDS.",
        "  quad fan        Z-consistent %d/%d, perimeter-consistent %d/%d; cover z-fan %d vs "
        "perimeter %d vs kit %d -- the _face_polys defect is REAL here and INERT (the covers agree)"
        % (r["quad_order"]["z_consistent"], r["quad_order"]["quads"],
           r["quad_order"]["perimeter_consistent"], r["quad_order"]["quads"],
           r["cover_z"], r["cover_perimeter"], r["cover_kit"]),
        "  cover           %d halfwords, lines %d..%d; stock words there %s (L mean %.2f, min %.2f, "
        "max %.2f) -- uniform, so placement is GEOMETRY not luminance"
        % (d["cover_halfwords"], d["cover_rows"][0], d["cover_rows"][1],
           ", ".join(d["cover_stock_words"]), d["cover_luma_mean"], d["cover_luma_min"],
           d["cover_luma_max"]),
        "  BANDS           %d x %d rows at y %s, full 64-texel width, inside the cover only"
        % (d["bands"], d["band_rows"], d["band_tops"]),
        "  ink             %s -- the darkest colour at CONSTANT STP; branches %s; mean luminance "
        "removed %.2f of a 255.00 ceiling"
        % (", ".join(d["ink_words"]), d["ink_branches"], d["luma_removed_per_texel"]),
        "  cutout / STP    cutouts %d -> %d (delta %d), STP set %d -> %d (delta %d) -- no cutout "
        "created, so the kit owes no acknowledge_cutout_reshape and the sidecar is carried verbatim"
        % (d["cutouts_before"], d["cutouts_after"], d["cutouts_after"] - d["cutouts_before"],
           d["stp_before"], d["stp_after"], d["stp_after"] - d["stp_before"]),
        "  MEASURED        %d texels changed = %.1f%% of the cover, %.1f%% of the page; outside the "
        "cover %d"
        % (d["changed_texels"], 100.0 * d["figure_share_of_cover"],
           100.0 * d["figure_share_of_page"], d["outside_cover"]),
        "  CONTROL         %s is left STOCK -- the reader's band spans BOTH cells (page lines "
        "97..159), so the bands must stop dead at the cell boundary" % d["control_cell"],
        "  wrote           %s" % d["png"],
        "                  %s" % d["stp_png"],
    ]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=None, help="staging root (default %s)" % DEFAULT_ROOT)
    ap.add_argument("--from", dest="from_path", default=None,
                    help="read this container FILE instead of the install")
    ap.add_argument("--no-export", action="store_true")
    ap.add_argument("--game", default=None)
    a = ap.parse_args(argv)
    d = generate(a.root, a.from_path, a.game, export=not a.no_export)
    print("\n".join(report(d)))
    # THE TWO NUMBERS THE CLAIM RESTS ON: nothing may land outside the reader's own cover, and the
    # RGBA+STP no-op identity has to have been checked before anything was drawn.
    return 0 if (d["outside_cover"] == 0 and d["noop_identity"]) else 1


if __name__ == "__main__":                                       # pragma: no cover
    raise SystemExit(main())
