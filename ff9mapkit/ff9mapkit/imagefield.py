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


class ImageFieldError(ValueError):
    pass


# ----------------------------------------------------------------- the homography (the new math)
def unproject_floor(cam: _cam.Cam, contour_px) -> list:
    """Un-project a canvas-pixel floor polygon onto the world ground plane Y=0 -> [(X, Z), ...].

    The plane-induced inverse of FF9's perspective projection: for each pixel we shoot the camera
    ray through it and intersect the y=0 plane. Raises :class:`ImageFieldError` if any vertex lands
    at or above the horizon (where the ray is parallel to the floor and the inverse blows up)."""
    d = _cam.decompose(cam)
    C, Minv = d["C"], _cam.inv3(d["R_view"])   # inv3, NOT transpose — R_view carries the k=14/15 squash
    W, H, D = cam.range[0], cam.range[1], cam.proj
    out = []
    for i, (cx, cy) in enumerate(contour_px):
        ray = _cam.mv(Minv, (cx - W / 2.0, H / 2.0 - cy, D))
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
def _cover_to_canvas(img, w: int, h: int):
    """Cover-crop ``img`` to the w:h aspect (fill, centre-crop the overflow), then resize to w*UPSCALE."""
    from PIL import Image
    iw, ih = img.size
    scale = max(w / iw, h / ih)
    rw, rh = round(iw * scale), round(ih * scale)
    img = img.resize((rw, rh), Image.LANCZOS)
    left, top = (rw - w) // 2, (rh - h) // 2
    img = img.crop((left, top, left + w, top + h))
    return img.resize((w * UPSCALE, h * UPSCALE), Image.LANCZOS)


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
    for i, fg in enumerate(foreground or []):
        fp, z = (fg["image"], int(fg.get("z", Z_FOREGROUND))) if isinstance(fg, dict) else (fg, Z_FOREGROUND)
        fim = Image.open(fp).convert("RGBA")
        _cover_to_canvas(fim, CANVAS_W, CANVAS_H).save(out / "art" / f"fg{i}.png")
        layers.append((f"art/fg{i}.png", z))

    # 3) emit the field.toml (camera + obj-walkmesh + layers + player)
    lines = [f"# EXPERIMENTAL image->field (auto-generated from {Path(image_path).name})",
             "[field]", f"id = {field_id}", f'name = "{name}"', f"area = {area}", "text_block = 1073", "",
             "[camera]", f"pitch = {pitch:g}", f"distance = {int(distance)}", f"fov = {fov:g}",
             f"range = [{CANVAS_W}, {CANVAS_H}]", "",
             "[walkmesh]", 'obj = "walkmesh.obj"', 'frame = "world"', ""]
    for img_rel, z in layers:
        lines += ["[[layers]]", f'image = "{img_rel}"', f"z = {z}"]
    lines += ["", "[player]", f"spawn = [{int(round(spawn[0]))}, {int(round(spawn[1]))}]", ""]
    toml_path = out / f"{name}.field.toml"
    toml_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    return {"toml": str(toml_path), "walkmesh": str(out / "walkmesh.obj"),
            "world_floor": world, "spawn": spawn, "verts": len(verts), "faces": len(faces),
            "layers": layers}
