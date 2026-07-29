"""EXPERIMENTAL: turn an arbitrary image into a walkable FF9 field.

Feed an image + a hand-traced FLOOR polygon (in canvas pixels) and this synthesizes a deployable
field project: the image becomes the painted background, the floor polygon is UN-PROJECTED onto the
world ground plane into a walkmesh, and a vanilla FF9 camera ties them together. Optional foreground
cut-out PNGs become occluder overlays so the character walks *behind* near objects.

This is the MVP vertical slice of the researched design (project-ff9-image-to-field memory): a
Pillow-only, hand-mask path with a FIXED camera pitch. The one genuinely new piece of math is the
floor un-projection, which — because FF9's field projection is PERSPECTIVE (not orthographic) and we
target a single plane — is a closed-form projective HOMOGRAPHY (one 3x3 per camera, verified to
round-trip ``cam.to_canvas`` to ~2e-12 world units). Everything downstream (the camera synth, the
.bgi walkmesh codec, the .bgx overlay writer, deploy) is existing, in-game-proven machinery.

CRITICAL correctness fact: the un-projection uses ``cam.inv3(R_view)``, NEVER ``transpose(R_view)`` —
R_view is non-orthonormal because the k=14/15 vertical squash is baked into it; a transpose injects
~7% (hundreds of world units) of error.
"""
from __future__ import annotations

import math
from pathlib import Path

from .scene import cam as _cam
from .scene import guide as _guide

CANVAS_W, CANVAS_H = 384, 448
UPSCALE = 4                                    # painted layer PNGs are 4x the logical canvas
COLLISION_OUTSET = 48.0                        # COLLISION_RADIUS_W: extend the mesh so the player centre reaches the edge
DEFAULT_PITCH = 26.0                           # a vanilla FF9 3/4 pitch (room band 6-48)
DEFAULT_FOV = 42.0
DEFAULT_DISTANCE = 3000.0
Z_BASE = 4000                                  # far overlay Z for the opaque background
Z_FOREGROUND = 500                             # a near occluder (smaller Z = drawn in front of the actor)
CONTACT_Z_BIAS = 2                             # anchored occluder: keep the actor on top AT the contact line


class ImageFieldError(ValueError):
    pass


# ----------------------------------------------------------------- the homography (the new math)
def click_ray(cam: _cam.Cam, pt) -> tuple:
    """The world-frame camera ray under a canvas pixel -> ``(origin C, direction)``.

    THE one owner of the canvas-frame fold: subtract the camera's GTE centerOffset and the
    half-extents (the exact inverse of ``cam.to_canvas``), then pull the pixel through
    ``inv3(R_view)`` — NEVER a transpose (R_view carries the k=14/15 squash; a transpose is ~7%
    of vertical error). Kit cameras have offset (0,0); REAL imported cameras carry a nonzero one
    (map158's [26, 400] round-tripped 400.8 px wrong before the fold — the census's catch), and
    **277 of 741 real cameras have one**, so every ray construction must come from here —
    the plane inverse (:func:`unproject_floor`) and the walkmesh raycast
    (:func:`click_to_surface`) both do."""
    d = _cam.decompose(cam)
    Minv = _cam.inv3(d["R_view"])
    W, H, D = cam.range[0], cam.range[1], cam.proj
    ox, oy = cam.centerOffset
    ray = _cam.mv(Minv, (pt[0] - ox - W / 2.0, H / 2.0 + oy - pt[1], D))
    return d["C"], ray


def unproject_floor(cam: _cam.Cam, contour_px) -> list:
    """Un-project a canvas-pixel floor polygon onto the world ground plane Y=0 -> [(X, Z), ...].

    The plane-induced inverse of FF9's perspective projection: for each pixel we shoot
    :func:`click_ray` and intersect the y=0 plane. Raises :class:`ImageFieldError` if any vertex
    lands at or above the horizon (where the ray is parallel to the floor and the inverse blows
    up). For AUTHORING new geometry from art this plane form is the ceiling (THE PLANE LAW);
    placement onto an EXISTING walkmesh uses :func:`click_to_surface` instead."""
    out = []
    for i, (cx, cy) in enumerate(contour_px):
        C, ray = click_ray(cam, (cx, cy))
        if ray[1] == 0:
            raise ImageFieldError(f"floor vertex {i} ({cx:.0f},{cy:.0f}) is on the horizon line")
        s = -C[1] / ray[1]
        if s <= 0:
            hy = _cam.horizon_canvas_y(cam)
            raise ImageFieldError(
                f"floor vertex {i} (canvas y={cy:.0f}) is at/above the horizon (y={hy:.0f}) for this "
                f"camera — trace the floor BELOW the horizon, or steepen the pitch")
        out.append((C[0] + s * ray[0], C[2] + s * ray[2]))
    return out


def _ray_tri(orig, ray, a, b, c):
    """Möller–Trumbore: the ray parameter s where ``orig + s*ray`` meets triangle (a, b, c),
    else None. s > 0 only (a hit behind the camera is not under the pixel)."""
    e1 = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    e2 = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    p = (ray[1] * e2[2] - ray[2] * e2[1], ray[2] * e2[0] - ray[0] * e2[2],
         ray[0] * e2[1] - ray[1] * e2[0])
    det = e1[0] * p[0] + e1[1] * p[1] + e1[2] * p[2]
    if abs(det) < 1e-12:
        return None
    t = (orig[0] - a[0], orig[1] - a[1], orig[2] - a[2])
    u = (t[0] * p[0] + t[1] * p[1] + t[2] * p[2]) / det
    if u < -1e-9 or u > 1 + 1e-9:
        return None
    q = (t[1] * e1[2] - t[2] * e1[1], t[2] * e1[0] - t[0] * e1[2], t[0] * e1[1] - t[1] * e1[0])
    v = (ray[0] * q[0] + ray[1] * q[1] + ray[2] * q[2]) / det
    if v < -1e-9 or u + v > 1 + 1e-9:
        return None
    s = (e2[0] * q[0] + e2[1] * q[1] + e2[2] * q[2]) / det
    return s if s > 1e-9 else None


def click_to_surface(cam: _cam.Cam, tris, pt) -> dict:
    """Canvas click -> the VISIBLE point of a world-frame triangle soup under it (Rung 3's
    conversion: placement onto an EXISTING walkmesh, exact on slopes — benched to 1.7e-11u on
    the most-sloped real fields, ``studies/click-authoring/raycast_bench.py``).

    ``tris`` = ``[((x,y,z), (x,y,z), (x,y,z)), ...]``. Returns ``{"pos", "tri", "hits"}`` where
    ``hits`` is every intersection nearest-first ``[(s, tri_index, (x,y,z)), ...]`` — a stacked
    walkmesh (a bridge over a floor) yields several, and the FIRST is what the author actually
    sees under the pixel; callers surface the rest for disambiguation. Raises
    :class:`ImageFieldError` when no triangle lies under the click. The accepted hit re-projects
    through ``cam.to_canvas`` back onto the click (the same tripwire as :func:`click_to_world`)."""
    orig, ray = click_ray(cam, tuple(pt))
    hits = []
    for i, (a, b, c) in enumerate(tris):
        s = _ray_tri(orig, ray, a, b, c)
        if s is not None:
            hits.append((s, i, (orig[0] + s * ray[0], orig[1] + s * ray[1],
                                orig[2] + s * ray[2])))
    if not hits:
        raise ImageFieldError(
            f"no walkmesh under the click ({pt[0]:.1f},{pt[1]:.1f}) — the walkable area does "
            f"not reach this pixel")
    hits.sort(key=lambda h: h[0])
    pos = hits[0][2]
    cx, cy = _cam.to_canvas(pos, cam)
    err = math.hypot(cx - pt[0], cy - pt[1])
    if err > CLICK_ROUNDTRIP_TOL:
        raise ImageFieldError(
            f"click ({pt[0]:.1f},{pt[1]:.1f}) hits the walkmesh at ({pos[0]:.0f},{pos[1]:.0f},"
            f"{pos[2]:.0f}) but that point re-projects to canvas ({cx:.1f},{cy:.1f}) — {err:.2f} px "
            f"off. The camera's ray is not consistent with its forward projection")
    return {"pos": pos, "tri": hits[0][1], "hits": hits}


def mesh_world_tris(mesh) -> tuple:
    """A walkmesh (``scene.bgi.BgiWalkmesh`` or anything duck-shaped like one) -> the
    ``(world_triangles, floor_index_per_triangle)`` pair :func:`click_to_surface` consumes.
    World frame = ``vert + orgPos + floor.org`` (the import-frame law), straight from the
    mesh's own ``world_verts``."""
    wv = mesh.world_verts()
    tri_floor = {ti: fi for fi, fl in enumerate(mesh.floors) for ti in fl.tri_ndx_list}
    tris, floors = [], []
    for ti, t in enumerate(mesh.tris):
        tris.append(tuple(wv[vi] for vi in t.vtx))
        floors.append(tri_floor.get(ti))
    return tris, floors


# The per-click self-check's loudness threshold, canvas px. The homography round-trips synthesized
# cameras to ~2e-12 world units, so any honest inverse lands back on the click to far below a pixel;
# the defect classes this trips on are large (a transpose of R_view = tens of px of vertical error,
# a numerically degenerate camera = unbounded). Real imported cameras are vetted against this same
# bound by the click-authoring census (studies/click-authoring/PLAN.md, the Rung 3 gate).
CLICK_ROUNDTRIP_TOL = 0.25


def click_to_world(cam: _cam.Cam, pt) -> tuple:
    """One canvas click -> the world floor point (X, Z) under it, self-checked.

    THE conversion every click-authoring call site routes through (HOP 2 of the architecture in
    ``studies/click-authoring/PLAN.md``): un-project through the plane homography, then assert the
    forward projection lands back on the click. The re-projection is one extra 3x3 multiply and it
    turns the silent geometry-bug class (an inverse that is *almost* right — the transpose trap, a
    degenerate real camera) into a loud error at the exact click that hit it. Raises
    :class:`ImageFieldError` at/above the horizon — a click there has NO floor intersection and must
    refuse, never clamp."""
    (X, Z), = unproject_floor(cam, [tuple(pt)])
    cx, cy = _cam.to_canvas((X, 0.0, Z), cam)
    err = math.hypot(cx - pt[0], cy - pt[1])
    if err > CLICK_ROUNDTRIP_TOL:
        raise ImageFieldError(
            f"click ({pt[0]:.1f},{pt[1]:.1f}) un-projects to world ({X:.0f},{Z:.0f}) but that point "
            f"re-projects to canvas ({cx:.1f},{cy:.1f}) — {err:.2f} px off. The camera's inverse is "
            f"not consistent with its forward projection (a degenerate/unsupported camera pose)")
    return (X, Z)


def world_point_to_click(cam: _cam.Cam, p) -> tuple:
    """A world 3D point (x, y, z) -> the canvas pixel (cx, cy) it appears under.

    The general forward hop (``cam.to_canvas`` with the behind-camera guard). Raises
    :class:`ImageFieldError` for a point at/behind the camera plane, where the projection's
    ``abs(z)`` would silently mirror it onto the canvas at a bogus position."""
    P = (p[0], p[1], p[2])
    _, _, resz = _cam.project(P, cam)
    if resz <= 0:
        raise ImageFieldError(
            f"world point ({p[0]:.0f},{p[1]:.0f},{p[2]:.0f}) is at/behind the camera plane — "
            f"it does not appear on the canvas")
    return _cam.to_canvas(P, cam)


def world_to_click(cam: _cam.Cam, p) -> tuple:
    """A world FLOOR point (x, z) -> its canvas pixel: the y=0 specialization of
    :func:`world_point_to_click` (one owner of the behind-camera guard)."""
    return world_point_to_click(cam, (p[0], 0.0, p[1]))


def occluder_z(cam: _cam.Cam, contact_px) -> int:
    """Overlay Z for a foreground occluder standing on the floor at canvas pixel ``contact_px``.

    The engine sorts an actor against overlays by OT depth = resz/4 + depthOffset
    (FieldMapActor.cs:122), and an overlay quad sits at its Position Z in those same units. So
    anchoring a cut-out's Z to the ACTOR depth at its ground-contact point makes occlusion flip
    exactly there: walk in front (nearer) -> the actor draws over it; walk behind -> it draws over
    the actor. +CONTACT_Z_BIAS keeps the actor on top at the contact line itself (standing at the
    object's base means standing in front of its body)."""
    try:
        (X, Z), = unproject_floor(cam, [tuple(contact_px)])
    except ImageFieldError as e:
        raise ImageFieldError(f"foreground contact point: {e}") from e
    z = int(round(_cam.depth((X, 0.0, Z), cam))) + CONTACT_Z_BIAS
    if z >= Z_BASE:
        raise ImageFieldError(
            f"foreground contact ({contact_px[0]:.0f},{contact_px[1]:.0f}) computes overlay z={z}, at/behind "
            f"the base layer (z={Z_BASE}) so it could never occlude the actor — trace the point where the "
            f"object MEETS THE FLOOR (its base), not somewhere up its body")
    return z


def parse_foreground_spec(spec) -> dict:
    """Normalize a foreground spec -> ``{"image": path, "z": int|None, "contact": (cx, cy)|None}``.

    Accepts a bare path, the CLI form ``path@cx,cy`` (ground-contact canvas pixel -> anchored Z via
    :func:`occluder_z`), or a dict with ``image`` + optional ``z``/``contact``. A trailing ``@cx,cy``
    only counts as a contact anchor when it parses as two numbers, so paths containing '@' still work."""
    if isinstance(spec, dict):
        c = spec.get("contact")
        return {"image": spec["image"], "z": spec.get("z"), "contact": tuple(c) if c else None}
    s = str(spec)
    if "@" in s:
        path, _, tail = s.rpartition("@")
        parts = tail.split(",")
        if len(parts) == 2:
            try:
                return {"image": path, "z": None, "contact": (float(parts[0]), float(parts[1]))}
            except ValueError:
                pass
    return {"image": s, "z": None, "contact": None}


# ----------------------------------------------------------------- polygon helpers (stdlib)
def _signed_area(poly) -> float:
    n = len(poly)
    return 0.5 * sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))


def _as_ccw(poly) -> list:
    return list(poly) if _signed_area(poly) >= 0 else list(reversed(poly))


def _line_intersect(a, b):
    """Intersection of two lines each given as (px, pz, dx, dz); None if parallel."""
    ax, az, adx, adz = a
    bx, bz, bdx, bdz = b
    den = adx * bdz - adz * bdx
    if abs(den) < 1e-9:
        return None
    t = ((bx - ax) * bdz - (bz - az) * bdx) / den
    return (ax + t * adx, az + t * adz)


def outset_polygon(poly, dist: float) -> list:
    """Miter-offset a simple polygon OUTWARD by ``dist`` world units (each boundary edge moved along
    its outward normal, adjacent offset edges re-intersected). So the player CENTRE — which stops
    ~COLLISION_OUTSET inside a wall — can reach the visual floor edge."""
    pts = _as_ccw(poly)
    n = len(pts)
    lines = []
    for i in range(n):
        x1, z1 = pts[i]
        x2, z2 = pts[(i + 1) % n]
        dx, dz = x2 - x1, z2 - z1
        L = math.hypot(dx, dz) or 1.0
        nx, nz = dz / L, -dx / L                # right normal = outward for CCW
        lines.append((x1 + nx * dist, z1 + nz * dist, dx, dz))
    out = []
    for i in range(n):
        v = _line_intersect(lines[(i - 1) % n], lines[i])
        out.append(v if v is not None else (lines[i][0], lines[i][1]))
    return out


def _cross(a, b, c) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _point_in_tri(p, a, b, c) -> bool:
    d1, d2, d3 = _cross(p, a, b), _cross(p, b, c), _cross(p, c, a)
    has_neg = (d1 < 0) or (d2 < 0) or (d3 < 0)
    has_pos = (d1 > 0) or (d2 > 0) or (d3 > 0)
    return not (has_neg and has_pos)


def triangulate(poly) -> tuple:
    """Ear-clip a simple polygon (convex or mildly concave) -> (verts, faces). ``verts`` may be a
    re-wound copy of ``poly`` (forced CCW); ``faces`` are index triples into it."""
    pts = _as_ccw(poly)
    if len(pts) < 3:
        raise ImageFieldError("floor polygon needs at least 3 vertices")
    idx = list(range(len(pts)))
    faces = []
    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        clipped = False
        n = len(idx)
        for k in range(n):
            i0, i1, i2 = idx[(k - 1) % n], idx[k], idx[(k + 1) % n]
            a, b, c = pts[i0], pts[i1], pts[i2]
            if _cross(a, b, c) <= 0:            # reflex vertex (CCW convex = cross > 0)
                continue
            if any(j not in (i0, i1, i2) and _point_in_tri(pts[j], a, b, c) for j in idx):
                continue
            faces.append((i0, i1, i2))
            idx.pop(k)
            clipped = True
            break
        if not clipped:                         # numerically stuck -> fan the remainder (rare)
            break
    if len(idx) >= 3:
        for k in range(1, len(idx) - 1):
            faces.append((idx[0], idx[k], idx[k + 1]))
    return pts, faces


def write_walkmesh_obj(verts, faces, path) -> None:
    """Write a Wavefront .obj on the y=0 plane (FF9 world coords: ``v x 0 z``, 1-indexed faces)."""
    lines = ["# ff9mapkit image-field walkmesh (world coords, y=0 floor plane)"]
    lines += [f"v {x:.3f} 0 {z:.3f}" for (x, z) in verts]
    lines += [f"f {a + 1} {b + 1} {c + 1}" for (a, b, c) in faces]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


# ----------------------------------------------------------------- image layers (Pillow)
def _cover_crop(img, w: int, h: int):
    """Cover-crop ``img`` to exactly w x h: scale to fill the aspect, centre-crop the overflow."""
    from PIL import Image
    iw, ih = img.size
    scale = max(w / iw, h / ih)
    rw, rh = round(iw * scale), round(ih * scale)
    img = img.resize((rw, rh), Image.LANCZOS)
    left, top = (rw - w) // 2, (rh - h) // 2
    return img.crop((left, top, left + w, top + h))


def _cover_to_canvas(img, w: int, h: int):
    """Cover-crop ``img`` to the w:h aspect at the 4x painted-layer size (w*UPSCALE x h*UPSCALE).

    The crop happens AT 4x, so a high-res source keeps its detail up to 1536x1792 (cropping at the
    logical 384x448 and re-upscaling would throw that detail away first)."""
    return _cover_crop(img, w * UPSCALE, h * UPSCALE)


# ----------------------------------------------------------------- auto floor-seed (numpy tier)
SEED_BOX = (112, 396, 272, 436)        # (x0, y0, x1, y1): the bottom-centre strip the floor model seeds from
SEED_MAX_SPREAD = 0.055                # refuse if the seed strip's per-channel MAD mean exceeds this
AUTO_FLOOR_MAX_VERTS = 14
MAX_SEED_DEPTH_FACTOR = 1.0            # rows un-projecting deeper than factor*distance are untraceably far
COLLAPSE_FRACTION = 0.55               # a row narrower than this fraction of the running-median width ...
COLLAPSE_ROWS = 8                      # ... for this many consecutive rows = a doorway constriction: cut
WIDTH_WINDOW = 60                      # rows in the running width median


def _dp_simplify(points, eps: float) -> list:
    """Douglas-Peucker on an open chain (endpoints kept)."""
    if len(points) < 3:
        return list(points)
    (ax, ay), (bx, by) = points[0], points[-1]
    dx, dy = bx - ax, by - ay
    L = math.hypot(dx, dy) or 1.0
    dmax, imax = -1.0, 0
    for i in range(1, len(points) - 1):
        px, py = points[i]
        d = abs(dx * (py - ay) - dy * (px - ax)) / L
        if d > dmax:
            dmax, imax = d, i
    if dmax <= eps:
        return [points[0], points[-1]]
    return _dp_simplify(points[:imax + 1], eps)[:-1] + _dp_simplify(points[imax:], eps)


def auto_floor(image_path, *, pitch: float = DEFAULT_PITCH, fov: float = DEFAULT_FOV,
               distance: float = DEFAULT_DISTANCE, max_vertices: int = AUTO_FLOOR_MAX_VERTS) -> dict:
    """Detect the floor polygon from the image itself (the numpy tier of the design).

    Seeded region grow: model the floor's colour from the bottom-centre strip (robust median/MAD —
    a photo's floor is usually the homogeneous surface the camera stands on), take the colour-close
    pixels, CLOSE small gaps (plank seams / tile grout lines), keep the connected component the seed
    lives in, and turn its per-row extents into a polygon (going down the left edge and up the right
    makes it simple by construction — interior islands like furniture legs get bridged, which is the
    right call for a SEED the human refines in the tracer). The top is clamped below the camera
    horizon, then both chains are Douglas-Peucker'd down to ``max_vertices``.

    REFUSAL-BIASED (the design's honesty gate): raises :class:`ImageFieldError` with the reason when
    the seed strip isn't floor-like, the region doesn't reach the bottom of the frame, it's
    implausibly small/large, or too little of it survives the horizon clamp. The hand-traced
    ``--floor`` / ``--trace`` path is always the override."""
    try:
        import numpy as np
    except ImportError as e:
        raise ImageFieldError("auto floor-seed needs numpy (py -m pip install numpy, or the "
                              "ff9mapkit[image] extra) -- or hand-trace the floor with --trace") from e
    from PIL import Image, ImageFilter
    src = Image.open(image_path).convert("RGB")
    im = _cover_crop(src, CANVAS_W, CANVAS_H).filter(ImageFilter.GaussianBlur(2.0))
    a = np.asarray(im, dtype=np.float32) / 255.0                     # (H, W, 3)
    H, W = CANVAS_H, CANVAS_W

    x0, y0, x1, y1 = SEED_BOX
    seed = a[y0:y1, x0:x1].reshape(-1, 3)
    med = np.median(seed, axis=0)
    mad = np.median(np.abs(seed - med), axis=0)
    spread = float(mad.mean())
    if spread > SEED_MAX_SPREAD:
        raise ImageFieldError(
            f"auto floor-seed: the bottom-centre of the image doesn't look like a uniform floor "
            f"(colour spread {spread:.3f} > {SEED_MAX_SPREAD}) -- hand-trace it with --trace")

    tol = np.maximum(mad * 4.0, 0.035)                               # per-channel tolerance, floored
    cand = (np.abs(a - med) <= tol).all(axis=2)
    m = Image.fromarray((cand * 255).astype("uint8"), "L")           # close seams/grout so the grow crosses them
    m = m.filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.MinFilter(5))
    cand = np.asarray(m) > 127

    from collections import deque
    comp = np.zeros_like(cand)
    q = deque()
    sy, sx = np.nonzero(cand[y0:y1, x0:x1])
    for yy, xx in zip(sy[::7], sx[::7]):                             # a sparse sample of seed pixels suffices
        q.append((int(yy) + y0, int(xx) + x0))
    while q:
        y, x = q.popleft()
        if comp[y, x] or not cand[y, x]:
            continue
        comp[y, x] = True
        if y > 0: q.append((y - 1, x))
        if y < H - 1: q.append((y + 1, x))
        if x > 0: q.append((y, x - 1))
        if x < W - 1: q.append((y, x + 1))

    frac = float(comp.mean())
    if frac < 0.05:
        raise ImageFieldError(f"auto floor-seed: the isolated floor region is too small "
                              f"({frac:.0%} of the canvas) -- hand-trace it with --trace")
    if frac > 0.80:
        raise ImageFieldError(f"auto floor-seed: {frac:.0%} of the image matches the floor colour -- no "
                              f"distinct floor boundary to detect; hand-trace it with --trace")
    if int(comp[H - 12:, :].any(axis=0).sum()) < 0.20 * W:
        raise ImageFieldError("auto floor-seed: the detected region doesn't reach the bottom of the "
                              "frame (is the floor visible at the camera's feet?) -- hand-trace it with --trace")

    cam = _guide.make_camera(pitch, distance, fov_x_deg=fov, range_wh=(CANVAS_W, CANVAS_H))
    # clamp the far edge: below the horizon AND within a traceable world depth (near the horizon a
    # single canvas row spans hundreds of world units -- same-material floor running away through a
    # far doorway would otherwise drag the polygon to the horizon, the user's hallway failure)
    y_cap = _cam.to_canvas((0.0, 0.0, MAX_SEED_DEPTH_FACTOR * distance), cam)[1]
    top_min = int(math.ceil(max(_cam.horizon_canvas_y(cam) + 4, y_cap)))
    if top_min > 0:
        comp[:min(top_min, H), :] = False

    rows = np.nonzero(comp.any(axis=1))[0]
    if rows.size < 60:
        raise ImageFieldError(f"auto floor-seed: only {rows.size} floor rows survive below the camera "
                              f"horizon/depth cap -- steepen --pitch, or hand-trace it with --trace")

    # walk bottom -> top; terminate at a SUSTAINED abrupt width collapse. Perspective narrowing is
    # gradual (a few percent over tens of rows); the floor squeezing through a doorway into another
    # room halves in a handful of rows -- cut there and keep only this room's floor.
    kept, widths, collapse = [], [], 0
    for r in rows[::-1]:
        xs = np.nonzero(comp[r])[0]
        w = float(xs[-1] - xs[0])
        recent = sorted(widths[-WIDTH_WINDOW:])
        if recent and w < COLLAPSE_FRACTION * recent[len(recent) // 2]:
            collapse += 1
            if collapse >= COLLAPSE_ROWS:
                kept = kept[:len(kept) - (collapse - 1)]             # drop the constriction rows too
                break
        else:
            collapse = 0
        kept.append(int(r))
        widths.append(w)
    if len(kept) < 40:
        raise ImageFieldError("auto floor-seed: the floor region collapses just above the seed strip "
                              "(a constriction right at the camera?) -- hand-trace it with --trace")
    rows = kept[::-1]

    left = [(float(np.nonzero(comp[r])[0].min()), float(r)) for r in rows]
    right = [(float(np.nonzero(comp[r])[0].max()), float(r)) for r in rows]
    while left and (right[0][0] - left[0][0]) < 12:                  # trim a sliver-thin far tip
        left.pop(0), right.pop(0)

    eps = 2.0
    while True:
        lp, rp = _dp_simplify(left, eps), _dp_simplify(right, eps)
        if len(lp) + len(rp) <= max_vertices or eps > 64:
            break
        eps *= 2.0
    poly = [(round(x, 1), round(y, 1)) for x, y in lp + rp[::-1]]
    poly = [p for i, p in enumerate(poly) if i == 0 or p != poly[i - 1]]
    return {"floor": poly, "area_frac": frac, "seed_spread": spread, "eps": eps,
            "rows": (int(rows[0]), int(rows[-1]))}


# ----------------------------------------------------------------- the floor tracer (--trace)
_TRACE_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>ff9mapkit floor tracer — __TITLE__</title><style>
body{background:#16181d;color:#d8dbe2;font:14px/1.5 system-ui,sans-serif;margin:0;padding:16px}
#wrap{display:flex;gap:16px;flex-wrap:wrap}
#stage{position:relative;width:768px;height:896px;flex:none;cursor:crosshair;outline:1px solid #333}
#stage img,#stage canvas{position:absolute;left:0;top:0;width:768px;height:896px}
#side{max-width:560px;min-width:320px}
button{background:#2b3040;color:#d8dbe2;border:1px solid #444;border-radius:4px;padding:4px 12px;margin:2px;cursor:pointer}
button.on{background:#4a5578;border-color:#7a8ac0}
textarea{width:100%;height:120px;background:#0e1013;color:#9fd49f;border:1px solid #333;font:12px/1.4 monospace;box-sizing:border-box}
.tip{color:#9aa1ad;font-size:12.5px}.warn{color:#e0a05a}
input[type=range]{width:220px;vertical-align:middle}
</style></head><body>
<h3 style="margin:4px 0">ff9mapkit image-field tracer — __TITLE__</h3>
<div class="tip">This is the EXACT 384&times;448 canvas crop the build will use (shown 2&times;). Click the floor
outline in order (a closed walkable polygon, BELOW the yellow horizon line). Toggle to <b>contact</b> mode to mark
where each foreground object MEETS the floor (its base) — that anchors its occlusion depth. Then copy the command.</div>
<div id="wrap"><div id="stage"><img id="im" src="__IMGURI__"><canvas id="cv" width="768" height="896"></canvas></div>
<div id="side">
  <p>Mode: <button id="mFloor" class="on">floor polygon</button> <button id="mContact">contact points</button>
     <button id="undo">undo</button> <button id="clear">clear</button></p>
  <p>Camera pitch: <input type="range" id="pitch" min="__PMIN__" max="__PMAX__" value="__PITCH0__" step="1">
     <span id="pv"></span>&deg; <span class="tip">(horizon y=<span id="hv"></span> — slide until the horizon
     matches the image's own eye level; floor points must stay below it)</span></p>
  <p class="tip">cursor: <span id="cur">—</span> (logical canvas px) · drag a point to adjust · fov __FOV__ /
     distance __DIST__ baked at generation (re-run --trace to change them)</p>
  <p id="warn" class="warn"></p>
  <textarea id="cmd" readonly></textarea><br><button id="copy">copy command</button>
  <p class="tip">Contact markers emit <code>--foreground "fgN.png@cx,cy"</code> placeholders — save each object's
  cut-out (full-canvas PNG with alpha, e.g. erase everything but the object in an editor) and swap in its filename.</p>
</div></div>
<script>
const HORIZONS=__HORIZONS__, IMGARG=__IMGARG__, S=2, DEF={pitch:26,fov:42,distance:3000};
const FOV=__FOVJS__, DIST=__DISTJS__, OUTNAME=__OUTNAME__;
let pitch=__PITCH0__, mode='floor', floor=__FLOOR0__, contacts=[], drag=null;
const cv=document.getElementById('cv'), cx2=cv.getContext('2d');
const r1=v=>Math.round(v*10)/10, fmt=p=>r1(p.x)+','+r1(p.y);
function lists(){return mode==='floor'?floor:contacts}
function pos(e){const r=cv.getBoundingClientRect();return {x:(e.clientX-r.left)/S, y:(e.clientY-r.top)/S}}
function redraw(){
  cx2.clearRect(0,0,768,896);
  const hy=HORIZONS[pitch]*S;
  cx2.strokeStyle='#e8c84a';cx2.setLineDash([8,5]);cx2.beginPath();cx2.moveTo(0,hy);cx2.lineTo(768,hy);cx2.stroke();
  cx2.setLineDash([]);cx2.fillStyle='#e8c84a';cx2.font='12px monospace';cx2.fillText('horizon',6,hy-5);
  if(floor.length){cx2.strokeStyle='#6ee06e';cx2.lineWidth=1.5;cx2.beginPath();
    cx2.moveTo(floor[0].x*S,floor[0].y*S);for(const p of floor.slice(1))cx2.lineTo(p.x*S,p.y*S);cx2.stroke();
    if(floor.length>2){const a=floor[floor.length-1],b=floor[0];cx2.setLineDash([4,4]);cx2.beginPath();
      cx2.moveTo(a.x*S,a.y*S);cx2.lineTo(b.x*S,b.y*S);cx2.stroke();cx2.setLineDash([])}}
  floor.forEach((p,i)=>{const bad=p.y<HORIZONS[pitch];cx2.fillStyle=bad?'#e05a5a':'#6ee06e';
    cx2.beginPath();cx2.arc(p.x*S,p.y*S,4,0,7);cx2.fill();cx2.fillText(i,p.x*S+6,p.y*S-4)});
  contacts.forEach((p,i)=>{cx2.strokeStyle='#5ab8e0';cx2.lineWidth=2;cx2.beginPath();
    cx2.moveTo(p.x*S-6,p.y*S);cx2.lineTo(p.x*S+6,p.y*S);cx2.moveTo(p.x*S,p.y*S-6);cx2.lineTo(p.x*S,p.y*S+6);
    cx2.stroke();cx2.fillStyle='#5ab8e0';cx2.fillText('fg'+i,p.x*S+7,p.y*S+11)});
  document.getElementById('pv').textContent=pitch;
  document.getElementById('hv').textContent=r1(HORIZONS[pitch]);
  const bad=floor.filter(p=>p.y<HORIZONS[pitch]).length;
  document.getElementById('warn').textContent=bad?bad+' floor point(s) above the horizon (red) — the build will refuse them':'';
  cmd()}
function q(s){return '"'+s+'"'}
function cmd(){
  const parts=['py -m ff9mapkit image-field',q(IMGARG)];
  if(floor.length>=3)parts.push('--floor',q(floor.map(fmt).join(' ')));
  parts.push('--out',q(OUTNAME));
  if(pitch!==DEF.pitch)parts.push('--pitch',pitch);
  if(FOV!==DEF.fov)parts.push('--fov',FOV);
  if(DIST!==DEF.distance)parts.push('--distance',DIST);
  contacts.forEach((p,i)=>parts.push('--foreground',q('fg'+i+'.png@'+fmt(p))));
  document.getElementById('cmd').value=floor.length>=3?parts.join(' '):'(trace at least 3 floor points)'}
cv.addEventListener('mousedown',e=>{const p=pos(e);
  for(const L of [floor,contacts])for(const t of L)
    if(Math.hypot(t.x-p.x,t.y-p.y)<5){drag=t;return}
  lists().push(p);redraw()});
cv.addEventListener('mousemove',e=>{const p=pos(e);
  document.getElementById('cur').textContent=fmt(p);
  if(drag){drag.x=p.x;drag.y=p.y;redraw()}});
window.addEventListener('mouseup',()=>drag=null);
document.getElementById('pitch').oninput=e=>{pitch=+e.target.value;redraw()};
function setMode(m){mode=m;document.getElementById('mFloor').classList.toggle('on',m==='floor');
  document.getElementById('mContact').classList.toggle('on',m==='contact')}
document.getElementById('mFloor').onclick=()=>setMode('floor');
document.getElementById('mContact').onclick=()=>setMode('contact');
document.getElementById('undo').onclick=()=>{lists().pop();redraw()};
document.getElementById('clear').onclick=()=>{floor=[];contacts=[];redraw()};
document.getElementById('copy').onclick=()=>{const t=document.getElementById('cmd');t.select();
  (navigator.clipboard?navigator.clipboard.writeText(t.value):document.execCommand('copy'))};
redraw();
</script></body></html>
"""


def write_trace_html(image_path, out_html, *, pitch: float = DEFAULT_PITCH, fov: float = DEFAULT_FOV,
                     distance: float = DEFAULT_DISTANCE, pitch_band=(6, 48), floor0=None) -> dict:
    """Emit a self-contained click-to-trace page for ``image_path`` (the real-photo on-ramp).

    Shows the EXACT 384x448 cover-crop :func:`build_image_field` will use (the same cover-crop
    code), a pitch slider whose HORIZON LINE is precomputed per integer pitch from the real camera
    math (floor points must stay below it — and matching the line to the photo's own eye level is a
    crude pitch estimator), floor-polygon + foreground-contact tracing, and the ready-to-run
    ``image-field`` command. ``floor0`` pre-loads a starting polygon (the :func:`auto_floor` seed —
    every auto mask routes through this hand override). No network, no deps; any browser."""
    import base64
    import io
    import json
    from PIL import Image
    src = Image.open(image_path).convert("RGB")
    disp = _cover_crop(src, CANVAS_W * 2, CANVAS_H * 2)     # the same crop geometry, at display res
    buf = io.BytesIO()
    disp.save(buf, "JPEG", quality=88)
    uri = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    lo, hi = int(pitch_band[0]), int(pitch_band[1])
    horizons = {p: round(_cam.horizon_canvas_y(
        _guide.make_camera(float(p), distance, fov_x_deg=fov, range_wh=(CANVAS_W, CANVAS_H))), 1)
        for p in range(lo, hi + 1)}
    stem = Path(image_path).stem
    seed_pts = [{"x": float(x), "y": float(y)} for (x, y) in (floor0 or [])]
    html = (_TRACE_HTML
            .replace("__TITLE__", Path(image_path).name)
            .replace("__IMGURI__", uri)
            .replace("__FLOOR0__", json.dumps(seed_pts))
            .replace("__HORIZONS__", json.dumps(horizons))
            .replace("__IMGARG__", json.dumps(str(image_path)))
            .replace("__OUTNAME__", json.dumps(f"{stem}-field"))
            .replace("__PMIN__", str(lo)).replace("__PMAX__", str(hi))
            .replace("__PITCH0__", str(int(round(pitch))))
            .replace("__FOVJS__", f"{fov:g}").replace("__DISTJS__", f"{distance:g}")
            .replace("__FOV__", f"{fov:g}").replace("__DIST__", f"{distance:g}"))
    out = Path(out_html)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8", newline="\n")
    return {"html": str(out), "horizon": horizons[int(round(pitch))]}


# ----------------------------------------------------------------- orchestrator
def build_image_field(image_path, floor_px, out_dir, *, foreground=None, name="PICTURE",
                      field_id: int = 4003, pitch: float = DEFAULT_PITCH, fov: float = DEFAULT_FOV,
                      distance: float = DEFAULT_DISTANCE, area: int = 11) -> dict:
    """Synthesize a deployable field project from an image + a hand-traced floor polygon.

    ``floor_px`` = [(cx, cy), ...] the floor outline in logical canvas pixels (384x448, top-left,
    Y-down). ``foreground`` = optional [path | {"image": path, "z": int}] near-occluder PNGs (each a
    full-canvas cut-out with alpha; smaller Z = drawn in front of the actor). Writes ``out_dir`` with
    ``<name>.field.toml`` + ``walkmesh.obj`` + ``art/*.png``. Returns a manifest dict."""
    from PIL import Image
    out = Path(out_dir)
    (out / "art").mkdir(parents=True, exist_ok=True)

    cam = _guide.make_camera(pitch, distance, fov_x_deg=fov, range_wh=(CANVAS_W, CANVAS_H))

    # 1) floor polygon -> world -> outset -> triangulate -> walkmesh.obj
    world = unproject_floor(cam, floor_px)
    spawn = (sum(p[0] for p in world) / len(world), sum(p[1] for p in world) / len(world))
    grown = outset_polygon(world, COLLISION_OUTSET)
    verts, faces = triangulate(grown)
    for x, z in verts:                              # Int16 walkmesh bound (bgi._check_int16 raises otherwise)
        if not (-32767 <= x <= 32767 and -32767 <= z <= 32767):
            raise ImageFieldError(f"walkmesh vertex ({x:.0f},{z:.0f}) exceeds the Int16 world bound "
                                  f"— reduce distance/FOV or trace a smaller floor")
    write_walkmesh_obj(verts, faces, out / "walkmesh.obj")

    # 2) base background layer (opaque, far Z)
    base = Image.open(image_path).convert("RGB")
    _cover_to_canvas(base, CANVAS_W, CANVAS_H).save(out / "art" / "base.png")

    layers = [("art/base.png", Z_BASE)]
    fg_manifest, layer_notes = [], {}
    for i, fg in enumerate(foreground or []):
        spec = parse_foreground_spec(fg)
        if spec["contact"] is not None:                # anchored: occlusion flips at the contact line
            z = occluder_z(cam, spec["contact"])
            cx, cy = spec["contact"]
            layer_notes[f"art/fg{i}.png"] = f"# occluder anchored at floor contact ({cx:g},{cy:g}) -> actor-depth z"
        else:
            z = int(spec["z"]) if spec["z"] is not None else Z_FOREGROUND
        fim = Image.open(spec["image"]).convert("RGBA")
        _cover_to_canvas(fim, CANVAS_W, CANVAS_H).save(out / "art" / f"fg{i}.png")
        layers.append((f"art/fg{i}.png", z))
        fg_manifest.append({"image": str(spec["image"]), "z": z, "contact": spec["contact"]})

    # 3) emit the field.toml (camera + obj-walkmesh + layers + player)
    lines = [f"# EXPERIMENTAL image->field (auto-generated from {Path(image_path).name})",
             # text_block omitted on purpose: it derives from the field id and auto-registers.
             "[field]", f"id = {field_id}", f'name = "{name}"', f"area = {area}", "",
             "[camera]", 'entry_settle = "auto"   # computed hold: the camera settles behind the entry fade',
             f"pitch = {pitch:g}", f"distance = {int(distance)}", f"fov = {fov:g}",
             f"range = [{CANVAS_W}, {CANVAS_H}]", "",
             "[walkmesh]", 'obj = "walkmesh.obj"', 'frame = "world"', ""]
    for img_rel, z in layers:
        if img_rel in layer_notes:
            lines.append(layer_notes[img_rel])
        lines += ["[[layers]]", f'image = "{img_rel}"', f"z = {z}"]
    lines += ["", "[player]", f"spawn = [{int(round(spawn[0]))}, {int(round(spawn[1]))}]", ""]
    toml_path = out / f"{name}.field.toml"
    toml_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    return {"toml": str(toml_path), "walkmesh": str(out / "walkmesh.obj"),
            "world_floor": world, "spawn": spawn, "verts": len(verts), "faces": len(faces),
            "layers": layers, "foreground": fg_manifest}
