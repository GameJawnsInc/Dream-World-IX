"""The World tab's 3D view: the overworld on the GPU as the game loads it (editor rungs A0-A1 and the stack).

``studies/overworld-editor/PLAN.md`` rung A0. The data path is the software renderer's own
(:func:`ff9mapkit.world.render.load_batches` with ``stock=True``: stock land under the deployed overrides, open sea
round them, a donor's free-riding parts), and the look is the renderer's engine-faithful rules done by a trivial
shader: unlit, NEAREST sampling with repeat, Unity V bottom-up, an alpha-0 texel drawn white (the blank-tile law),
sea opaque at frame 0, the game-eye back-face cull, a missing texture magenta. ``world/render.py`` is the ORACLE:
:func:`render_still` draws a still with the same camera dict ``render.raster`` takes, and the A0 acceptance compares
the two by defect class (:func:`compare`, ``tests/test_worldview3d.py``).

Laws this surface honours by construction:

- **No I/O uninvited, no GL uninvited.** Nothing here runs at Workspace start: the World tab imports this module and
  builds :class:`WorldView3DPanel` only on the user's own "3D view" click, and the map load (about 5 s for the whole
  disc-1 grid, measured 2026-10-23) runs on a worker thread that marshals back by Signal.
- **No silent blank.** The offscreen Qt platform has no OpenGL (measured: a QOpenGLWidget there never initialises and
  grabs 0x0), and neither does every machine. :func:`gl_available` asks first and the panel says so in words; a GL
  view that would only ever paint the clear colour is never shown.
- **One projection.** :func:`clip_matrix` is ``render.project`` written as a matrix (plus the half-pixel shift from
  the software renderer's pixel-corner samples to GL's pixel centres), and the interactive orbit camera produces the
  same camera dict, so the view and the oracle can never drift apart by construction.

Rung A1 adds :func:`pick` (the eye ray through a pixel, front faces only) and the pin. The site the World tab hands
in resolves every file through ``Memoria.ini``'s ``FolderNames`` the engine's way (``render.RenderSite.stack``,
``studies/overworld-editor/STACK.md``), or one folder over stock on request. Not here: the x-torus wrap at the 23|0
seam, forms (Terrain2/Object2), sea animation, fog, the sky.
"""

from __future__ import annotations

import dataclasses
import math
import threading

try:
    import numpy as np
except ImportError:                                          # pragma: no cover
    np = None

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QImage, QMatrix4x4, QOffscreenSurface, QOpenGLContext, QSurfaceFormat
from PySide6.QtOpenGL import (QOpenGLBuffer, QOpenGLFramebufferObject, QOpenGLFramebufferObjectFormat,
                              QOpenGLShader, QOpenGLShaderProgram, QOpenGLTexture)
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QHBoxLayout, QStackedLayout, QVBoxLayout, QWidget

NEAR = 0.05                    # render.raster drops a tri with any vertex this close to the eye (or behind it)
# the game camera's vehicles (C8): the travel modes offered, how each sits (measured in game: c8_lab.py) -- and, C21,
# how each was reached, since that moves the camera's final nudges (gamecam.fix_target): (mode, how, label)
VEHICLE_CHOICES = ((0, "boarded", "On foot"), (1, "boarded", "Chocobo"), (6, "boarded", "Gold chocobo, flying"),
                   (6, "pepper", "Gold chocobo, after a Dead Pepper"), (7, "boarded", "Blue Narciss"),
                   (8, "boarded", "Hilda Garde III"), (8, "loaded", "Hilda Garde III, back from its bridge"),
                   (9, "boarded", "Invincible"))
VEHICLE_MODES = tuple(dict.fromkeys(m for m, _h, _l in VEHICLE_CHOICES))
VEHICLE_LABELS = {m: label for m, how, label in VEHICLE_CHOICES if how == "boarded"}
HOW_ROLE = 0x0101              # Qt.UserRole + 1: the chooser item's ``how`` beside its mode (the item data)
FLYING_MODES = (6, 8, 9)
BOAT_MODE = 7
BOAT_DRAFT = -0.703125         # the Blue Narciss rides at the water's surface less this (published -0.703125)
CEILING = 42.1875              # a flyer's ceiling (the vehicle study's rank 5, measured)
ORTHO_Y = (-200.0, 400.0)      # the y span an ortho still's depth maps over (the world sits in about -6..60)
MISSING_RGB = (200, 60, 200)   # render.raster's missing-texture magenta
FOV = 50.0                     # the interactive camera's field of view (the bench cameras' own)
PITCH_MIN, PITCH_MAX = 4.0, 89.0
DIST_MIN, DIST_MAX = 6.0, 2400.0
MAP_CENTRE = (768.0, 0.0, -640.0)                            # the 24x20 grid's middle, world units

GL_TRIANGLES, GL_FLOAT = 0x0004, 0x1406
GL_DEPTH_TEST, GL_CULL_FACE, GL_BACK, GL_LESS = 0x0B71, 0x0B44, 0x0405, 0x0201
GL_CW, GL_CCW = 0x0900, 0x0901
GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT = 0x4000, 0x0100
GL_BLEND, GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA = 0x0BE2, 0x0302, 0x0303

_VERT = """#version 120
attribute vec3 a_pos;
attribute vec2 a_uv;
uniform mat4 u_mvp;
varying vec2 v_uv;
varying vec3 v_pos;
void main() { v_uv = a_uv; v_pos = a_pos; gl_Position = u_mvp * vec4(a_pos, 1.0); }
"""
# Unity V is bottom-up and the texture is uploaded top row first, so t = 1 - v: render.sample's
# floor((1 - frac(v)) * h) mod h is exactly GL's NEAREST + REPEAT texel for that t.
_FRAG = """#version 120
uniform sampler2D u_tex;
uniform int u_has_tex;
uniform vec3 u_missing;
uniform float u_alpha;
uniform int u_fog;
uniform vec3 u_eye;
uniform vec3 u_fwd;
uniform vec4 u_fog_ramp;
uniform vec3 u_fog_rgb;
varying vec2 v_uv;
varying vec3 v_pos;
void main() {
    vec3 col = u_has_tex == 0 ? u_missing : texture2D(u_tex, vec2(v_uv.x, 1.0 - v_uv.y)).rgb;
    float a = u_has_tex == 0 ? u_alpha : 1.0;
    if (u_fog == 1) {
        float d = dot(v_pos - u_eye, u_fwd);
        float e = u_fog_ramp.y + u_fog_ramp.z * max(0.0, v_pos.y - u_fog_ramp.w);
        col = mix(col, u_fog_rgb, clamp((d - u_fog_ramp.x) / max(e - u_fog_ramp.x, 1e-6), 0.0, 1.0));
    }
    gl_FragColor = vec4(col, a);
}
"""
# THE GAME'S FOG (editor C18, world.fog): the scene only (a missing texture's magenta too, as render.raster's twin
# fogs it) -- draw_solid turns it off, so the editor's own drawings (a ghost, a refusal mark, the pick's pin) stay as
# bright as ever: they are the author's, not the game's


class GLUnavailable(RuntimeError):
    """No usable OpenGL here (the offscreen platform, a headless CI box, a GL older than 2.1)."""


# ---------------------------------------------------------------- the projection (pure)
def view_basis(view):
    """``(eye, right, up, fwd)`` exactly as ``render.project`` derives them (fwd = at - eye, right = Y x fwd: the
    game's left-handed frame, C7)."""
    eye = np.asarray(view["eye"], dtype=np.float64)
    fwd = np.asarray(view["at"], dtype=np.float64) - eye
    fwd /= np.linalg.norm(fwd)
    right = np.cross([0.0, 1.0, 0.0], fwd)
    right /= np.linalg.norm(right)
    up = np.cross(fwd, right)
    return eye, right, up, fwd


def clip_matrix(view, res, *, far=None) -> np.ndarray:
    """The 4x4 world -> clip matrix (column vectors) of a ``render`` camera dict at ``res`` = (W, H).

    ``render.project`` puts pixel ``i`` at screen coordinate ``i`` (its raster samples pixel corners) with sy growing
    down; GL samples pixel centres with y growing up, so the window coordinate is ``(sx + 0.5, H - sy - 0.5)``. The
    result, divided through, lands every vertex on the pixel ``render.project`` puts it on."""
    W, H = res
    if view["kind"] == "ortho":
        x0, x1, z0, z1 = view["x0"], view["x1"], view["z0"], view["z1"]
        ax = 2.0 * (W - 1) / (W * (x1 - x0))                 # ndc_x = 2 (sx + .5) / W - 1
        az = 2.0 * (H - 1) / (H * (z1 - z0))                 # ndc_y = 1 - 2 (sy + .5) / H
        y_lo, y_hi = ORTHO_Y
        ay = -2.0 / (y_hi - y_lo)                            # higher ground = nearer (render's depth is -y)
        return np.array([
            [ax, 0.0, 0.0, -ax * x0 + 1.0 / W - 1.0],
            [0.0, 0.0, -az, az * z0 + 1.0 - 1.0 / H],
            [0.0, ay, 0.0, -ay * (y_lo + y_hi) / 2.0],
            [0.0, 0.0, 0.0, 1.0]])
    eye, right, up, fwd = view_basis(view)
    if far is None:
        far = float(view.get("reach", 0.0)) + float(np.linalg.norm(np.asarray(view["at"]) - eye)) + 50.0 \
            if "reach" in view else 4000.0
    near = float(view.get("near", NEAR))
    t = math.tan(math.radians(view["fov"]) / 2.0)
    vm = np.eye(4)
    vm[0, :3], vm[1, :3], vm[2, :3] = right, up, fwd
    vm[:3, 3] = -vm[:3, :3] @ eye                            # (cx, cy, cz, 1): render.project's rel @ basis
    pm = np.array([
        [(H / W) / t, 0.0, 1.0 / W, 0.0],
        [0.0, 1.0 / t, -1.0 / H, 0.0],
        [0.0, 0.0, (far + near) / (far - near), -2.0 * far * near / (far - near)],
        [0.0, 0.0, 1.0, 0.0]])
    return pm @ vm


def window_xy(view, res, verts):
    """``(sx, sy)`` in ``render.project``'s pixel frame, from :func:`clip_matrix` -- the projection check's seam."""
    W, H = res
    hom = np.c_[np.asarray(verts, dtype=np.float64), np.ones(len(verts))] @ clip_matrix(view, res).T
    ndc = hom[:, :3] / hom[:, 3:4]
    return (ndc[:, 0] + 1.0) * W / 2.0 - 0.5, H - (ndc[:, 1] + 1.0) * H / 2.0 - 0.5


# ---------------------------------------------------------------- the scene (pure)
@dataclasses.dataclass
class Packed:
    """Unindexed GPU-ready geometry. ``arrays[part]`` is float32 (N, 5) = x, y, z, u, v, three rows a triangle;
    ``draws`` keeps ``render.raster``'s batch order as ``(part, first_vertex, vertex_count)`` so a depth TIE resolves
    the way the oracle's strict ``<`` does (first drawn wins)."""

    arrays: dict
    draws: list
    tris: int = 0
    _pick: dict = dataclasses.field(default_factory=dict, repr=False)   # part -> (v0, e1, e2, n), built on first pick
    _ground: dict | None = dataclasses.field(default=None, repr=False)  # part -> {16u cell: up tri ids}, once built

    def pick_arrays(self, part):
        """Float64 ``(v0, e1, e2, normal)`` per triangle of ``part``, computed once (a click must not re-allocate
        them for the whole map)."""
        if part not in self._pick:
            v = self.arrays[part][:, :3].astype(np.float64).reshape(-1, 3, 3)
            v0, e1, e2 = v[:, 0].copy(), v[:, 1] - v[:, 0], v[:, 2] - v[:, 0]
            self._pick[part] = (v0, e1, e2, np.cross(e1, e2))
        return self._pick[part]

    @property
    def parts(self):
        return list(self.arrays)

    def ground_grid(self):
        """The plan grid :func:`ground_y` reads (``part -> {(i, j): ascending up-facing tri ids whose plan box meets
        16u cell (i, j)}``), or None while it is not built: the probe then scans every tri, as it did."""
        return self._ground

    def build_ground_grid(self):
        """Build :meth:`ground_grid` (about 0.4 s for the whole map: the panel runs it on a worker). Every tri whose
        plan box holds a point is in that point's cell, so a cell's tris are the whole scan's candidates there."""
        if self._ground is not None:
            return self._ground
        grid = {}
        for part in self.arrays:
            v0, e1, e2, n = self.pick_arrays(part)
            lo = np.minimum(v0, np.minimum(v0 + e1, v0 + e2))
            hi = np.maximum(v0, np.maximum(v0 + e1, v0 + e2))
            up = np.flatnonzero(n[:, 1] > 0.0)
            i0 = np.floor(lo[up, 0] / GROUND_CELL).astype(np.int64)
            i1 = np.floor(hi[up, 0] / GROUND_CELL).astype(np.int64)
            j0 = np.floor(lo[up, 2] / GROUND_CELL).astype(np.int64)
            j1 = np.floor(hi[up, 2] / GROUND_CELL).astype(np.int64)
            cells = {}
            for tri, a, b, c, d in zip(up.tolist(), i0.tolist(), i1.tolist(), j0.tolist(), j1.tolist()):
                for i in range(a, b + 1):
                    for j in range(c, d + 1):
                        cells.setdefault((i, j), []).append(tri)
            grid[part] = {k: np.asarray(v, dtype=np.int64) for k, v in cells.items()}
        self._ground = grid                              # (one assignment: a probe sees it built or not at all)
        return grid


def _view_keep(view, verts, tris):
    """``render.raster``'s two whole-triangle rules for a perspective still: drop a tri with any vertex at depth
    <= NEAR, and (with ``reach``) a tri whose centroid lies farther than ``reach`` from ``at``. GL would clip the first
    and draw the second; the oracle does neither, so a still applies them here."""
    eye, _, _, fwd = view_basis(view)
    dep = (verts - eye) @ fwd
    keep = (dep[tris] > NEAR).all(axis=1)
    if "reach" in view:
        cen = verts[tris].mean(axis=1)
        keep &= np.linalg.norm(cen - np.asarray(view["at"], dtype=np.float64), axis=1) <= view["reach"]
    return keep


def pack(batches, view=None) -> Packed:
    """``render.load_batches`` output -> :class:`Packed`. ``view`` (a perspective still's camera) applies the
    oracle's whole-triangle rules first; the interactive view passes none and draws everything."""
    chunks, draws, counts = {}, [], {}
    ntri = 0
    for part, verts, uvs, tris in batches:
        tris = np.asarray(tris, dtype=np.int64).reshape(-1, 3)
        if view is not None and view["kind"] == "persp" and len(tris):
            tris = tris[_view_keep(view, np.asarray(verts, dtype=np.float64), tris)]
        if not len(tris):
            continue
        flat = tris.reshape(-1)
        block = np.empty((len(flat), 5), dtype=np.float32)
        block[:, :3] = np.asarray(verts, dtype=np.float64)[flat]
        block[:, 3:] = np.asarray(uvs, dtype=np.float64)[flat]
        first = counts.get(part, 0)
        chunks.setdefault(part, []).append(block)
        counts[part] = first + len(block)
        draws.append((part, first, len(block)))
        ntri += len(tris)
    arrays = {p: np.ascontiguousarray(np.concatenate(c)) for p, c in chunks.items()}
    return Packed(arrays=arrays, draws=draws, tris=ntri)


def texture_rgba(tex):
    """A ``render.tex_for`` array -> what the GPU samples: alpha-0 texels WHITE (``render.sample``), all opaque.
    ``None`` stays ``None`` (drawn magenta)."""
    if tex is None:
        return None
    out = np.array(tex[..., :4] if tex.shape[-1] >= 4 else np.dstack([tex, np.full(tex.shape[:2], 255)]),
                   dtype=np.uint8, copy=True)
    blank = out[..., 3] == 0
    out[blank, :3] = 255
    out[..., 3] = 255
    return np.ascontiguousarray(out)


def compare(oracle, gpu, *, sky=None, tol: int = 0) -> dict:
    """How a GPU still differs from ``render.raster``'s, by defect class (measured 2026-10-23 on the V-shore bench
    and a disc-1 coast; ``studies/overworld-editor/A0.md``):

    * ``differ``: pixels not equal. Two precision classes make nearly all of them and neither is a defect: 1-px
      LINES where a pixel centre lies exactly on a shared triangle edge (the oracle paints both triangles there and
      keeps the first; GL's fill rule gives the pixel to one, so a tile border pixel takes its neighbour tile's
      colour), and isolated DOTS where a nearest-texel pick lands on a texel border (float32 on the GPU, float64 in
      the oracle) on high-frequency rock and grass.
    * ``coverage``: pixels that are sky in one image and not in the other -- a hole, a culled face or a missing
      triangle changes this; the precision classes touch it only along silhouettes.
    * ``blob``: differing pixels whose whole 3x3 neighbourhood differs too. A wrong texture, a flipped tile or a
      missing triangle is an AREA; a line or a dot never fills a 3x3 block.

    ``tol``: a channel within this many levels counts as equal (the fog's blend, float32 on the GPU and float64 in its
    software twin, rounds a level apart on fogged pixels: C18, so one level); exact by default.
    """
    from ..world import render as R
    sky = R.SKY if sky is None else sky
    a = np.asarray(oracle, dtype=np.int16)
    b = np.asarray(gpu, dtype=np.int16)
    diff = (np.abs(a - b) > tol).any(axis=2)
    H, W = diff.shape
    sky_a = (a == sky).all(axis=2)
    sky_b = (b == sky).all(axis=2)
    pad = np.pad(diff, 1, mode="constant", constant_values=False)
    full = np.ones_like(diff)
    for dy in (0, 1, 2):
        for dx in (0, 1, 2):
            full &= pad[dy:dy + H, dx:dx + W]
    return {"pixels": int(diff.size), "differ": int(diff.sum()), "coverage": int((sky_a != sky_b).sum()),
            "blob": int(full.sum())}


def pixel_ray(view, res, mx, my):
    """``(origin, unit direction)`` of the eye ray through window point ``(mx, my)`` (top-left origin, device pixels,
    continuous -- a mouse position). Pixel ``i``'s centre is ``i + 0.5`` there and ``i`` in render.project's frame,
    the same half-pixel the clip matrix carries, so the ray passes exactly where that pixel was drawn."""
    W, H = res
    eye, right, up, fwd = view_basis(view)
    f = (H / 2.0) / math.tan(math.radians(view["fov"]) / 2.0)
    a = (mx - 0.5 - W / 2.0) / f
    b = -(my - 0.5 - H / 2.0) / f
    d = fwd + a * right + b * up
    return eye, d / np.linalg.norm(d)


def pick(packed: Packed, view, res, mx, my, *, near=None):
    """The surface under window point ``(mx, my)``: ``(world xyz, part)`` of the nearest FRONT-facing triangle the
    eye ray hits (the view culls back faces, so a pick never lands on one you cannot see), or ``None`` for sky.
    Vectorised Moller-Trumbore over every packed triangle: ~287k on the whole map, a few tens of ms."""
    eye, d = pixel_ray(view, res, mx, my)
    near = float(view.get("near", NEAR)) if near is None else near
    best_t, best = math.inf, None
    for part in packed.arrays:
        v0, e1, e2, n = packed.pick_arrays(part)
        front = n @ d < 0.0                                  # the game-eye cull: the normal faces the eye
        p = np.cross(d, e2)
        det = np.einsum("ij,ij->i", e1, p)
        ok = front & (np.abs(det) > 1e-12)
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        s = eye - v0
        u = np.einsum("ij,ij->i", s, p) * inv
        q = np.cross(s, e1)
        w = (q @ d) * inv
        t = np.einsum("ij,ij->i", e2, q) * inv
        hit = ok & (u >= 0) & (w >= 0) & (u + w <= 1) & (t > near)
        if hit.any():
            i = int(np.argmin(np.where(hit, t, np.inf)))
            if t[i] < best_t:
                best_t, best = float(t[i]), part
    if best is None:
        return None
    return tuple(float(c) for c in eye + best_t * d), best


WORLD_W = 1536.0                                             # the world's width: x wraps here
SEAM_COPY = 192.0                                            # three columns each side of x = 0 drawn again across it


def seam_copies(batches, width=SEAM_COPY):
    """THE SEAM, DRAWN TWICE (rung C10): the batches, then the triangles within ``width`` of x = 0 again across it --
    columns 0-2 east of x = 1536 and columns 21-23 west of x = 0 -- so an island straddling the seam reads whole at
    both ends of the map, and a ghost there stands on it. Appended after every batch, so a depth tie inside the map
    still resolves as the oracle's does; a pick on a copy is a point 1536u off, which the World tab folds back."""
    out = list(batches)
    for part, verts, uvs, tris in batches:
        t = np.asarray(tris, dtype=np.int64).reshape(-1, 3)
        if not len(t):
            continue
        v = np.asarray(verts, dtype=np.float64)
        uv = np.asarray(uvs, dtype=np.float64)
        cx = v[t].mean(axis=1)[:, 0]
        for sel, shift in ((cx < width, WORLD_W), (cx >= WORLD_W - width, -WORLD_W)):
            if not sel.any():
                continue
            st = t[sel]
            used = np.unique(st)
            remap = np.full(len(v), -1, dtype=np.int64)
            remap[used] = np.arange(len(used))
            nv = v[used].copy()
            nv[:, 0] += shift
            out.append((part, nv, uv[used], remap[st]))
    return out


def seam_shifts(xs, width=SEAM_COPY):
    """The x offsets a drawing at ``xs`` is drawn at: itself, and its twin across the seam when it lies within
    ``width`` of x = 0 or of x = 1536 (where the view draws the map again)."""
    xs = np.asarray(xs, dtype=np.float64)
    out = [0.0]
    if not xs.size:
        return out
    if float(xs.min()) < width:
        out.append(WORLD_W)
    if float(xs.max()) > WORLD_W - width:
        out.append(-WORLD_W)
    return out


def load_scene(site, *, part_src=None, memo=None):
    """``(Packed, {part: rgba or None})`` for a :class:`~ff9mapkit.world.render.RenderSite`, stock under the
    overrides, the seam drawn twice (:func:`seam_copies`). Pure numpy + file reads: the panel runs it on a worker
    thread, with its :class:`~ff9mapkit.world.render.CellMemo` so a reload draws only the cells that moved."""
    from ..world import render as R
    batches = seam_copies(R.load_batches(site, part_src, stock=True, memo=memo))
    packed = pack(batches)
    return packed, {p: texture_rgba(R.tex_for(p, site)) for p in packed.parts}


# ---------------------------------------------------------------- GL (needs a current context)
def gl_available() -> bool:
    """True when this Qt platform can make an OpenGL 2.1+ context. Cheap; the panel asks before it builds a view."""
    from PySide6.QtGui import QGuiApplication
    if QGuiApplication.instance() is None or QGuiApplication.platformName() in ("offscreen", "minimal"):
        return False
    ctx = QOpenGLContext()
    if not ctx.create():
        return False
    fmt = ctx.format()
    return (fmt.majorVersion(), fmt.minorVersion()) >= (2, 1) or ctx.isOpenGLES()


class _GLScene:
    """One :class:`Packed` scene's GL resources in the CURRENT context: a shader, a VBO and a texture per part."""

    def __init__(self):
        self.prog = None
        self.vbos, self.texs = {}, {}
        self.draws = []

    def init(self):
        prog = QOpenGLShaderProgram()
        if not (prog.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Vertex, _VERT)
                and prog.addShaderFromSourceCode(QOpenGLShader.ShaderTypeBit.Fragment, _FRAG)
                and prog.link()):
            raise GLUnavailable(f"the 3D view's shader did not build: {prog.log().strip()}")
        self.prog = prog

    def upload(self, packed: Packed, textures: dict):
        self.release_scene()
        for part, arr in packed.arrays.items():
            vbo = QOpenGLBuffer(QOpenGLBuffer.Type.VertexBuffer)
            vbo.create()
            vbo.bind()
            data = arr.tobytes()
            vbo.allocate(data, len(data))
            vbo.release()
            self.vbos[part] = vbo
            rgba = textures.get(part)
            if rgba is not None:
                tex = QOpenGLTexture(QOpenGLTexture.Target.Target2D)
                tex.setSize(rgba.shape[1], rgba.shape[0])
                tex.setFormat(QOpenGLTexture.TextureFormat.RGBA8_UNorm)
                tex.setMipLevels(1)
                tex.allocateStorage(QOpenGLTexture.PixelFormat.RGBA, QOpenGLTexture.PixelType.UInt8)
                tex.setData(QOpenGLTexture.PixelFormat.RGBA, QOpenGLTexture.PixelType.UInt8, rgba.tobytes())
                tex.setMinMagFilters(QOpenGLTexture.Filter.Nearest, QOpenGLTexture.Filter.Nearest)
                tex.setWrapMode(QOpenGLTexture.WrapMode.Repeat)
                self.texs[part] = tex
        self.draws = list(packed.draws)

    def draw(self, f, mvp: np.ndarray, *, cull: bool = True, ortho: bool = False, fog=None, view=None):
        """The scene; ``fog`` (a ``world.fog.Fog``) fogs it as ``view``'s camera sees it."""
        f.glEnable(GL_DEPTH_TEST)
        f.glDepthFunc(GL_LESS)
        if cull:                                             # the normal faces the eye (render's cull): in the
            f.glEnable(GL_CULL_FACE)                         # game's left-handed perspective that face winds CW on
            f.glFrontFace(GL_CCW if ortho else GL_CW)        # screen; the top-down ortho frame is unmirrored
            f.glCullFace(GL_BACK)
        else:
            f.glDisable(GL_CULL_FACE)
        prog = self.prog
        prog.bind()
        prog.setUniformValue("u_mvp", QMatrix4x4(*[float(v) for v in mvp.reshape(-1)]))
        prog.setUniformValue1i(prog.uniformLocation("u_tex"), 0)
        prog.setUniformValue("u_missing", *[c / 255.0 for c in MISSING_RGB])
        prog.setUniformValue1f(prog.uniformLocation("u_alpha"), 1.0)
        _fog_uniforms(prog, fog, view)
        loc_p, loc_uv = prog.attributeLocation("a_pos"), prog.attributeLocation("a_uv")
        bound = None
        for part, first, count in self.draws:
            if part != bound:
                self.vbos[part].bind()
                prog.enableAttributeArray(loc_p)
                prog.enableAttributeArray(loc_uv)
                prog.setAttributeBuffer(loc_p, GL_FLOAT, 0, 3, 20)
                prog.setAttributeBuffer(loc_uv, GL_FLOAT, 12, 2, 20)
                tex = self.texs.get(part)
                if tex is not None:
                    tex.bind(0)
                prog.setUniformValue1i(prog.uniformLocation("u_has_tex"), 1 if tex is not None else 0)
                bound = part
            f.glDrawArrays(GL_TRIANGLES, first, count)
        if bound is not None:
            self.vbos[bound].release()
        prog.release()

    def draw_solid(self, f, mvp: np.ndarray, tris_xyz: np.ndarray, rgb, *, alpha: float = 1.0, depth: bool = False):
        """Untextured triangles in one colour, no cull: on top of everything (the pick's pin, a refusal mark), or
        ``depth=True`` inside the scene (the forest ghost, which the hills in front of it should hide). ``alpha``
        below 1 blends it over what is drawn."""
        if not len(tris_xyz):
            return
        data = np.ascontiguousarray(np.c_[tris_xyz, np.zeros((len(tris_xyz), 2))], dtype=np.float32).tobytes()
        vbo = QOpenGLBuffer(QOpenGLBuffer.Type.VertexBuffer)
        vbo.create()
        vbo.bind()
        vbo.allocate(data, len(data))
        if depth:
            f.glEnable(GL_DEPTH_TEST)
            f.glDepthFunc(GL_LESS)
        else:
            f.glDisable(GL_DEPTH_TEST)
        f.glDisable(GL_CULL_FACE)
        if alpha < 1.0:
            f.glEnable(GL_BLEND)
            f.glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        prog = self.prog
        prog.bind()
        prog.setUniformValue("u_mvp", QMatrix4x4(*[float(v) for v in mvp.reshape(-1)]))
        prog.setUniformValue1i(prog.uniformLocation("u_has_tex"), 0)
        prog.setUniformValue1i(prog.uniformLocation("u_fog"), 0)         # the author's drawings: never fogged
        prog.setUniformValue("u_missing", *[c / 255.0 for c in rgb])
        prog.setUniformValue1f(prog.uniformLocation("u_alpha"), float(alpha))
        loc_p, loc_uv = prog.attributeLocation("a_pos"), prog.attributeLocation("a_uv")
        prog.enableAttributeArray(loc_p)
        prog.enableAttributeArray(loc_uv)
        prog.setAttributeBuffer(loc_p, GL_FLOAT, 0, 3, 20)
        prog.setAttributeBuffer(loc_uv, GL_FLOAT, 12, 2, 20)
        f.glDrawArrays(GL_TRIANGLES, 0, len(tris_xyz))
        if alpha < 1.0:
            f.glDisable(GL_BLEND)
        vbo.release()
        vbo.destroy()
        prog.release()

    def release_scene(self):
        for vbo in self.vbos.values():
            vbo.destroy()
        for tex in self.texs.values():
            tex.destroy()
        self.vbos, self.texs, self.draws = {}, {}, []


def _fog_uniforms(prog, fog, view):
    """The fragment shader's fog: off without a fog or a perspective view, else its ramp, colour and the eye's frame."""
    if fog is None or view is None or view.get("kind") != "persp":
        prog.setUniformValue1i(prog.uniformLocation("u_fog"), 0)
        return
    eye = np.asarray(view["eye"], dtype=np.float64)
    fwd = np.asarray(view["at"], dtype=np.float64) - eye
    fwd /= np.linalg.norm(fwd)
    prog.setUniformValue1i(prog.uniformLocation("u_fog"), 1)
    prog.setUniformValue("u_eye", *[float(v) for v in eye])
    prog.setUniformValue("u_fwd", *[float(v) for v in fwd])
    prog.setUniformValue("u_fog_ramp", float(fog.start), float(fog.end), float(fog.per_u), float(fog.floor))
    prog.setUniformValue("u_fog_rgb", *[c / 255.0 for c in fog.rgb])


def _clear(f, rgb):
    f.glClearColor(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0, 1.0)
    f.glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)


def render_still(batches, view, *, res=None, tex_lookup=None, site=None, cull=True, fog=None):
    """One still on the GPU, the way ``render.raster(view, batches, ...)`` draws it: (H, W, 3) uint8; ``fog`` as
    ``world.fog.fog_still`` fogs a raster still (the sky cleared to the fog's colour).

    ``tex_lookup`` (part -> texture array or None) is the hermetic hook, as in ``render.raster``; else ``site``'s
    textures; ``cull`` as ``render.raster``'s. Needs a QGuiApplication on a GL platform; raises
    :class:`GLUnavailable` otherwise."""
    from ..world import render as R
    if res is None:
        res = site.res if site is not None else R.RES
    if tex_lookup is None:
        tex_lookup = lambda part: R.tex_for(part, site)      # noqa: E731
    if not gl_available():
        raise GLUnavailable("no OpenGL context on this Qt platform")
    W, H = res
    ctx = QOpenGLContext()
    if not ctx.create():
        raise GLUnavailable("QOpenGLContext.create() failed")
    surf = QOffscreenSurface()
    surf.setFormat(ctx.format())
    surf.create()
    if not ctx.makeCurrent(surf):
        raise GLUnavailable("could not make the GL context current")
    try:
        ffmt = QOpenGLFramebufferObjectFormat()
        ffmt.setAttachment(QOpenGLFramebufferObject.Attachment.Depth)
        fbo = QOpenGLFramebufferObject(W, H, ffmt)
        fbo.bind()
        f = ctx.functions()
        f.glViewport(0, 0, W, H)
        _clear(f, fog.rgb if fog is not None and view["kind"] == "persp" else R.SKY)
        packed = pack(batches, view)
        scene = _GLScene()
        scene.init()
        scene.upload(packed, {p: texture_rgba(tex_lookup(p)) for p in packed.parts})
        scene.draw(f, clip_matrix(view, res), cull=cull, ortho=view["kind"] == "ortho", fog=fog, view=view)
        f.glFinish()
        img = fbo.toImage().convertToFormat(QImage.Format.Format_RGB888)
        fbo.release()
        scene.release_scene()
        ptr = img.constBits()
        arr = np.frombuffer(ptr, dtype=np.uint8, count=img.sizeInBytes()).reshape(H, img.bytesPerLine())
        return arr[:, :W * 3].reshape(H, W, 3).copy()        # copy: the QImage owns those bytes
    finally:
        ctx.doneCurrent()


PIN_HALO_RGB = (12, 12, 12)    # drawn under the accent pin: the world under it is any colour (sea is the dark
#                                theme's accent blue), so the pin carries its own ground

def ribbon_tris(ring, height):
    """An upright band ``height`` tall standing on the closed ring of ``(x, y, z)`` points: a ghost's rim, drawn so
    it reads from any angle (a flat outline vanishes edge-on). Two triangles per ring edge."""
    ring = np.asarray(ring, dtype=np.float64)
    nxt = np.roll(ring, -1, axis=0)
    top, ntop = ring + (0.0, height, 0.0), nxt + (0.0, height, 0.0)
    return np.stack([ring, nxt, ntop, ring, ntop, top], axis=1).reshape(-1, 3)


def plane_hit(view, res, mx, my, y):
    """Where the eye ray through window point ``(mx, my)`` meets the level plane at height ``y``: ``(x, z)``, or
    None when the ray runs level or away from it. The ghost drag's ground: a pick per mouse move would cost tens of
    ms, the plane costs nothing, and the ghost's own rim height is the plane it slides on."""
    eye, d = pixel_ray(view, res, mx, my)
    if abs(d[1]) < 1e-9:
        return None
    t = (y - eye[1]) / d[1]
    if t <= 0.0:
        return None
    p = eye + t * d
    return float(p[0]), float(p[2])


def pin_tris(xyz, height, *, w_frac=0.12):
    """Two crossed upright quads standing on ``xyz``, ``height`` tall: the picked point's marker (12 vertices)."""
    x, y, z = xyz
    w = height * w_frac
    out = []
    for dx, dz in ((w, 0.0), (0.0, w)):
        a, b = (x - dx, y, z - dz), (x + dx, y, z + dz)
        c, d = (x + dx, y + height, z + dz), (x - dx, y + height, z - dz)
        out += [a, b, c, a, c, d]
    return np.asarray(out, dtype=np.float64)


# ---------------------------------------------------------------- the interactive view
@dataclasses.dataclass
class OrbitCamera:
    """Orbit about ``target``: ``yaw`` degrees about +y (0 = the eye south of the target, looking north), ``pitch``
    above the horizon, ``dist`` world units. :meth:`view` is a ``render`` camera dict, so the one projection serves."""

    target: tuple = MAP_CENTRE
    yaw: float = 0.0
    pitch: float = 55.0
    dist: float = 1100.0
    fov: float = FOV

    def eye(self):
        p, y = math.radians(self.pitch), math.radians(self.yaw)
        tx, ty, tz = self.target
        return (tx - self.dist * math.cos(p) * math.sin(y), ty + self.dist * math.sin(p),
                tz - self.dist * math.cos(p) * math.cos(y))

    def view(self):
        return dict(kind="persp", eye=self.eye(), at=tuple(self.target), fov=self.fov,
                    near=max(NEAR, self.dist / 400.0))

    def far(self):
        return self.dist + 2600.0

    def orbit(self, dx_px, dy_px):
        self.yaw = (self.yaw + dx_px * 0.3) % 360.0          # the world turns with the hand (left-handed frame)
        self.pitch = min(PITCH_MAX, max(PITCH_MIN, self.pitch + dy_px * 0.3))

    def pan(self, dx_px, dy_px, height_px):
        """Slide the target over the ground plane so the point under the cursor follows it."""
        per_px = 2.0 * self.dist * math.tan(math.radians(self.fov) / 2.0) / max(1, height_px)
        y = math.radians(self.yaw)
        rx, rz = math.cos(y), -math.sin(y)                   # screen-right on the ground (render's right = Y x fwd)
        fx, fz = math.sin(y), math.cos(y)                    # screen-up on the ground (toward the view direction)
        tx, ty, tz = self.target
        self.target = (tx - (dx_px * rx - dy_px * fx) * per_px, ty, tz - (dx_px * rz - dy_px * fz) * per_px)

    def zoom(self, steps):
        self.dist = min(DIST_MAX, max(DIST_MIN, self.dist * (0.85 ** steps)))


GROUND_CELL = 16.0                                           # the ground grid's plan cell (Packed.build_ground_grid)


def ground_y(packed: Packed, x: float, z: float):
    """The highest up-facing surface of the scene under ``(x, z)`` (a ray straight down from the sky), or None: the
    terrain the game camera's eye probes (``world.gamecam``'s ``ground``). With the Packed's ground grid built, only
    the tris of the point's 16u cell are tested -- the same tests and arithmetic, so the same heights: a game-camera
    frame's four probes over the whole map were 95-104 ms on the GUI thread (PERF.md 6)."""
    if packed is None:
        return None
    grid = packed.ground_grid()
    key = (math.floor(x / GROUND_CELL), math.floor(z / GROUND_CELL))
    best = None
    for part in packed.arrays:
        v0, e1, e2, n = packed.pick_arrays(part)
        if grid is not None:
            cand = grid.get(part, {}).get(key)
            if cand is None:
                continue
            v0, e1, e2, n = v0[cand], e1[cand], e2[cand], n[cand]
        ok = n[:, 1] > 0.0                                   # faces up: the face a ray from the sky meets
        lo = np.minimum(v0, np.minimum(v0 + e1, v0 + e2))
        hi = np.maximum(v0, np.maximum(v0 + e1, v0 + e2))
        ok &= (lo[:, 0] <= x) & (x <= hi[:, 0]) & (lo[:, 2] <= z) & (z <= hi[:, 2])
        idx = np.flatnonzero(ok)
        if not len(idx):
            continue
        a, b, c = v0[idx], v0[idx] + e1[idx], v0[idx] + e2[idx]
        d = (b[:, 2] - c[:, 2]) * (a[:, 0] - c[:, 0]) + (c[:, 0] - b[:, 0]) * (a[:, 2] - c[:, 2])
        good = np.abs(d) > 1e-12
        d = np.where(good, d, 1.0)
        w0 = ((b[:, 2] - c[:, 2]) * (x - c[:, 0]) + (c[:, 0] - b[:, 0]) * (z - c[:, 2])) / d
        w1 = ((c[:, 2] - a[:, 2]) * (x - c[:, 0]) + (a[:, 0] - c[:, 0]) * (z - c[:, 2])) / d
        w2 = 1.0 - w0 - w1
        inside = good & (w0 >= -1e-9) & (w1 >= -1e-9) & (w2 >= -1e-9)
        if inside.any():
            y = float((w0 * a[:, 1] + w1 * b[:, 1] + w2 * c[:, 1])[inside].max())
            best = y if best is None else max(best, y)
    return best


class GameCamera:
    """THE GAME'S OWN CAMERA (editor C7): the chase camera ``world.gamecam`` decodes, for the party standing at
    ``player`` with the camera's yaw ``rotation`` -- its distance, height and field of view from the engine's tables
    and the user's Memoria.ini ``[Worldmap]`` (``settings``), the eye lifted over ``ground``. The orbit camera's
    interface, so the view drives either: a sideways drag turns it (the bumpers do the same in the game); it does not
    pan or zoom, since the game's does not.

    ``mode`` is the travel mode (gEventGlobal[190], C8): a chocobo, the boat and the airships each frame their own way
    (``gamecam.pose``); ``how`` is how it was reached (C21: boarded, after a Dead Pepper, or loaded aboard, which
    moves the final nudges: ``gamecam.fix_target``, for the disc-1 world scripts this view draws); ``table`` is the
    game's TransportControls (``gamecam.transport_table``); ``topograph`` the cell's under the party (a chocobo over
    forest widens its view). The panel seats the party as each vehicle sits."""

    def __init__(self, player, rotation=0.0, *, settings=None, area=14, ground=None, mode=0, table=None,
                 topograph=None, how="boarded"):
        self.player, self.rotation = tuple(float(v) for v in player), float(rotation) % 360.0
        self.settings, self.area, self.ground = settings, int(area), ground
        self.mode, self.table, self.topograph, self.how = int(mode), table, topograph, str(how)
        self.dist = 0.0
        self._memo = None

    @property
    def target(self):
        return self.player

    @target.setter
    def target(self, xyz):                                   # focus() moves the party, as the game's teleport does
        self.player = tuple(float(v) for v in xyz)

    def view(self):
        from ..world import gamecam as G
        key = (self.player, round(self.rotation, 3), self.area, self.mode, self.topograph, self.how)
        if self._memo is None or self._memo[0] != key:
            v = G.pose(self.player, self.rotation, settings=self.settings or G.Settings(), area=self.area,
                       ground=self.ground, mode=self.mode, table=self.table, how=self.how, disc=1,
                       topograph=self.topograph)
            v["near"] = NEAR
            self._memo = (key, v)
        return dict(self._memo[1])

    def far(self):
        return 2600.0

    def orbit(self, dx_px, dy_px):
        self.rotation = (self.rotation + dx_px * 0.3) % 360.0

    def pan(self, dx_px, dy_px, height_px):
        pass

    def zoom(self, steps):
        pass

    @classmethod
    def from_orbit(cls, cam: "OrbitCamera", player, **kw):
        """The game camera looking the way the orbit camera looks: the game's eye sits at +(sin, cos) of its yaw
        from the party, the orbit's at -(sin, cos), so the yaw is the orbit's plus 180."""
        return cls(player, (cam.yaw + 180.0) % 360.0, **kw)

    def to_orbit(self) -> "OrbitCamera":
        return OrbitCamera(target=self.player, yaw=(self.rotation + 180.0) % 360.0, pitch=35.0, dist=160.0)


class WorldView3D(QOpenGLWidget):
    """The orbitable view. Left-drag orbits, right- or middle-drag pans, the wheel zooms, Home re-frames."""

    gl_failed = Signal(str)
    picked = Signal(object)                                  # ((x, y, z), part) or None (sky) -- a click, not a drag
    ghost_moved = Signal(float, float)                       # the ghost's new centre while it is dragged
    ghost_dropped = Signal(float, float)                     # ...and where it was let go (the host judges it then)
    camera_changed = Signal(bool)                            # the view left (False) the game camera on its own (Home)
    party_moved = Signal(float, float, float)                # the game camera's party stands here now (a click)
    CLICK_SLOP = 4                                           # device px a press may wander and still be a click

    def __init__(self, parent=None):
        super().__init__(parent)
        fmt = QSurfaceFormat()
        fmt.setDepthBufferSize(24)
        self.setFormat(fmt)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("3D overworld view")
        self.setMinimumSize(240, MIN_VIEW_H)
        self.camera = OrbitCamera()
        self._scene = _GLScene()
        self._pending = None                                 # (packed, textures) waiting for a current context
        self._ready = False
        self._drag = None
        self._press_at = None
        self.packed = None                                   # the scene the view draws (the pick's triangles)
        self.marker = None                                   # (x, y, z) of the last pick
        self.marker_rgb = None                               # the theme accent; the panel sets it (no colour of its own)
        # what a tool draws over the map: [(tris (n, 3), rgb, alpha, depth)], in order (the forest ghost, its rim,
        # its refusal marks). The host owns the list and its colours; the view only draws it.
        self.overlays = []
        self.fog = None                                      # world.fog.Fog the game camera draws (C18), or None
        # a draggable ghost: {"center": (x, z), "y": rim height, "poly": (m, 2) plan ring}. A left press inside its
        # plan drags it on the level plane at y (ghost_moved / ghost_dropped); anywhere else the camera orbits
        self.ghost = None
        self._ghost_grab = None                              # (dx, dz) from the grab point to the centre

    def set_camera(self, camera):
        """Drive the view from ``camera`` (an :class:`OrbitCamera` or a :class:`GameCamera`)."""
        self.camera = camera
        self.update()

    def game_mode(self) -> bool:
        return isinstance(self.camera, GameCamera)

    def set_scene(self, packed: Packed, textures: dict):
        self._pending = (packed, textures)
        self.packed = packed
        self.update()

    def device_res(self):
        dpr = self.devicePixelRatioF()
        return max(1, int(self.width() * dpr)), max(1, int(self.height() * dpr))

    def pick_at(self, x, y):
        """Pick at widget point ``(x, y)`` (logical px): ``((x, y, z), part)`` or None. Sets the marker."""
        if self.packed is None:
            return None
        dpr = self.devicePixelRatioF()
        res = self.device_res()
        hit = pick(self.packed, self.camera.view(), res, x * dpr, y * dpr)
        self.marker = None if hit is None else hit[0]
        self.update()
        return hit

    def focus(self, wx, wz, *, dist=160.0, y=0.0):
        self.camera.target, self.camera.dist = (float(wx), float(y), float(wz)), dist
        self.update()

    def initializeGL(self):
        try:
            self._scene.init()
            self._ready = True
        except GLUnavailable as e:
            self._ready = False
            self.gl_failed.emit(str(e))

    def paintGL(self):
        from ..world import render as R
        f = self.context().functions()
        dpr = self.devicePixelRatioF()
        w, h = max(1, int(self.width() * dpr)), max(1, int(self.height() * dpr))
        f.glViewport(0, 0, w, h)
        cam = self.camera
        fog = self.fog if self.game_mode() else None          # the game's fog only through the game's eye
        _clear(f, fog.rgb if fog is not None else R.SKY)
        if not self._ready:
            return
        if self._pending is not None:
            self._scene.upload(*self._pending)
            self._pending = None
        view = cam.view()
        mvp = clip_matrix(view, (w, h), far=cam.far())
        self._scene.draw(f, mvp, fog=fog, view=view)
        for tris, rgb, alpha, depth in self.overlays:
            for s in seam_shifts(tris[:, 0]) if len(tris) else (0.0,):   # a drawing at the seam, at both ends
                self._scene.draw_solid(f, mvp, tris + (s, 0.0, 0.0) if s else tris, rgb, alpha=alpha, depth=depth)
        if self.marker is not None and self.marker_rgb is not None:
            h = max(1.5, cam.dist * 0.04)
            hx, hy, hz = self.marker
            self._scene.draw_solid(f, mvp, pin_tris((hx, hy - h * 0.06, hz), h * 1.12, w_frac=0.3), PIN_HALO_RGB)
            self._scene.draw_solid(f, mvp, pin_tris(self.marker, h), self.marker_rgb)

    def set_overlays(self, overlays):
        self.overlays = list(overlays)
        self.update()

    def set_ghost(self, ghost):
        self.ghost = ghost
        if ghost is None:
            self._ghost_grab = None

    def _ghost_plane(self, e):
        dpr = self.devicePixelRatioF()
        return plane_hit(self.camera.view(), self.device_res(), e.position().x() * dpr, e.position().y() * dpr,
                         self.ghost["y"])

    # -- input --
    def mousePressEvent(self, e):
        self._drag = (e.button(), e.position())
        self._press_at = (e.button(), e.position(), 0.0)
        self._ghost_grab = None
        if e.button() == Qt.MouseButton.LeftButton and self.ghost is not None:
            from ..world.forestedit import _pip
            at = self._ghost_plane(e)
            poly = np.asarray(self.ghost["poly"], dtype=np.float64)
            for s in seam_shifts(poly[:, 0]) if at is not None else ():   # the ghost or its twin across the seam
                if bool(_pip(np.asarray([at]), poly + (s, 0.0))[0]):
                    cx, cz = self.ghost["center"]
                    self._ghost_grab = (cx + s - at[0], cz - at[1])
                    break
        e.accept()

    def mouseMoveEvent(self, e):
        if self._drag is None:
            return
        if self._ghost_grab is not None:                     # dragging the ghost, not the camera
            if self._press_at is not None:                   # within the slop it is still a click (a pick)
                b0, p0, far = self._press_at
                far = max(far, math.hypot(*(e.position() - p0).toTuple()))
                self._press_at = (b0, p0, far)
                if far * self.devicePixelRatioF() <= self.CLICK_SLOP:
                    return
                self._press_at = None                        # a drag from here on, never a click
            at = self._ghost_plane(e)
            if at is not None:
                self.ghost_moved.emit(at[0] + self._ghost_grab[0], at[1] + self._ghost_grab[1])
            return
        button, last = self._drag
        d: QPointF = e.position() - last
        if self._press_at is not None:
            b0, p0, _ = self._press_at
            self._press_at = (b0, p0, max(self._press_at[2], math.hypot(*(e.position() - p0).toTuple())))
            if self._press_at[2] * self.devicePixelRatioF() <= self.CLICK_SLOP:
                return                                       # still a click: the camera holds still
        if button == Qt.MouseButton.LeftButton:
            self.camera.orbit(d.x(), d.y())
        else:
            self.camera.pan(d.x(), d.y(), self.height())
        self._drag = (button, e.position())
        self.update()

    def mouseReleaseEvent(self, e):
        self._drag = None
        grab, self._ghost_grab = self._ghost_grab, None
        if grab is not None and self._press_at is None:      # a ghost drag ends where the plane meets the cursor
            at = self._ghost_plane(e)
            cx, cz = self.ghost["center"] if at is None else (at[0] + grab[0], at[1] + grab[1])
            self.ghost_dropped.emit(cx, cz)
            return
        press, self._press_at = self._press_at, None
        if (press is not None and press[0] == Qt.MouseButton.LeftButton and e.button() == Qt.MouseButton.LeftButton
                and press[2] * self.devicePixelRatioF() <= self.CLICK_SLOP):
            hit = self.pick_at(e.position().x(), e.position().y())
            if hit is not None and self.game_mode():         # the game camera: the party stands where you click
                self.camera.target = hit[0]
                self.party_moved.emit(*hit[0])
                self.update()
            self.picked.emit(hit)

    def wheelEvent(self, e):
        self.camera.zoom(e.angleDelta().y() / 120.0)
        self.update()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Home:
            self.camera = OrbitCamera()
            self.camera_changed.emit(False)
            self.update()
            return
        super().keyPressEvent(e)

    def release_gl(self):
        if self._ready and self.context() is not None:
            self.makeCurrent()
            self._scene.release_scene()
            self.doneCurrent()


def _rgb(hexcolour):
    h = str(hexcolour).lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


MIN_VIEW_H = 180                                             # the view's own floor (a tool's card may lower it)


class WorldView3DPanel(QWidget):
    """The 3D page of the World tab: a status/fallback page until the map is loaded, then the view.

    ``load(site)`` reads on a worker thread (the World tab's own scan shape); ``load(site, sync=True)`` is the
    deterministic lane for tests and gui_snap."""

    _loaded = Signal(object, object, object)                 # (packed | None, textures | None, error | None)
    picked = Signal(object)                                  # the view's pick, forwarded: ((x, y, z), part) or None
    ghost_moved = Signal(float, float)                       # the view's ghost drag, forwarded
    ghost_dropped = Signal(float, float)

    def __init__(self, pal, *, scale=100):
        super().__init__()
        self.pal, self._scale = pal, scale
        self.view = None
        self.site = None                                     # the RenderSite the view drew (the pick's facts read it)
        self._busy = False
        self._next = None                                    # a load asked while one runs
        from ..world import render as R
        self._cells = R.CellMemo()                           # every reload draws only the cells whose files moved
        self._focus = None
        self._overlays, self._ghost = [], None               # a tool's drawing, held until the view exists
        self._floor = None                                   # set_view_floor's height, or None for MIN_VIEW_H
        self._caption_folded = False                         # fold_caption: a carry card's room
        self._loaded.connect(self._finish)
        from . import widgets
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)
        # which folders the view drew, in the engine's order: the caption is the view's legend (a view that
        # silently draws a different stack from the game's is the defect this page exists to prevent)
        # the page's own bar: the host's controls for what the view draws (add_control), then the caption on a line of
        # its own. On the page, not the World tab's head row -- that row's wrapped scan summary clipped at 150% with
        # one more control. Not beside the controls either: in the column they leave it wrapped to four lines at 150%
        # (five once a draft is drawn) and squeezed a carry card's verdict out of a 1280x850 window.
        self.bar = QHBoxLayout()
        self.bar.setContentsMargins(0, 0, 0, 0)
        self.bar.setSpacing(8)
        self.bar.addStretch(1)
        from PySide6.QtWidgets import QPushButton
        self.game_btn = QPushButton("As the game sees it")
        self.game_btn.setProperty("role", "quiet")
        self.game_btn.setCheckable(True)
        self.game_btn.setAccessibleName("Game camera")
        self.game_btn.setToolTip("Frame the map as the game's own camera does for the party standing at the last "
                                 "picked point (or the view's centre): its distance, height and field of view from "
                                 "the engine's tables and your Memoria.ini [Worldmap]. A click stands the party "
                                 "somewhere else; drag sideways to turn the camera, as the bumpers do. Home goes back "
                                 "to the free view.")
        self.game_btn.toggled.connect(self.set_game_camera)
        self.game_btn.toggled.connect(self._name_game_btn)
        self.game_btn.hide()                                 # until the view is up
        # C8: the travel mode the game camera frames for, and a flyer's height (shown only with the game camera on)
        from PySide6.QtWidgets import QComboBox, QDoubleSpinBox
        self.vehicle_box = QComboBox()
        self.vehicle_box.setAccessibleName("Game camera vehicle")
        self.vehicle_box.setToolTip("How the party travels: on foot, on a chocobo, on the boat or an airship. Each "
                                    "vehicle's camera sits at its own distance and height, as the game's does, and "
                                    "the game lifts it after a Dead Pepper in the air or when the airship comes "
                                    "back from its bridge.")
        for m, how, label in VEHICLE_CHOICES:
            self.vehicle_box.addItem(label, m)
            self.vehicle_box.setItemData(self.vehicle_box.count() - 1, how, HOW_ROLE)
        # the longest name never sets the bar's width (the window's floor): the list opens as wide as its items
        self.vehicle_box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.vehicle_box.setMinimumContentsLength(12)
        self.vehicle_box.currentIndexChanged.connect(lambda _ix: self._vehicle_changed())
        self.alt_spin = QDoubleSpinBox()
        self.alt_spin.setAccessibleName("Game camera flying height")
        self.alt_spin.setToolTip(f"How high the airship (or the flying chocobo) flies. The game keeps a flyer on or "
                                 f"above the ground below it and never above {CEILING:g}.")
        self.alt_spin.setRange(0.0, CEILING)
        self.alt_spin.setDecimals(1)
        self.alt_spin.setSingleStep(2.0)
        self.alt_spin.setValue(24.0)
        self.alt_spin.valueChanged.connect(lambda _v: self._seat_party())
        # C18: the game's fog with the game camera; the Mist covers disc 1 until the Outer Continent, and disc 4
        from PySide6.QtWidgets import QCheckBox
        self.mist_box = QCheckBox("Mist")
        self.mist_box.setAccessibleName("Game camera mist")
        self.mist_box.setChecked(True)
        self.mist_box.toggled.connect(lambda _on: self._set_fog())
        for w in (self.vehicle_box, self.alt_spin, self.mist_box):
            w.hide()
            self.bar.addWidget(w)
        self.bar.addWidget(self.game_btn)
        outer.addLayout(self.bar)
        self.caption = widgets.role_label("", "caption")
        self.caption.setWordWrap(True)
        self.caption.setAccessibleName("3D view folders")
        self.caption.hide()
        outer.addWidget(self.caption)
        host = self._host = QWidget()
        self._stack = QStackedLayout(host)
        self._stack.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(host, 1)
        self._status = self._message("Loading the map…", "Reading the blocks the engine binds, through your "
                                     "mod folders in the game's order. About five seconds for the whole map.")
        self._stack.addWidget(self._status)

    def _message(self, title, teach):
        from . import widgets
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(widgets.empty_state("", title, teach=teach))
        return page

    def _show_message(self, title, teach):
        old = self._status
        self._status = self._message(title, teach)
        self._stack.addWidget(self._status)
        self._stack.setCurrentWidget(self._status)
        self._stack.removeWidget(old)
        old.deleteLater()

    def set_view_floor(self, h=None):
        """Lower the view's floor to ``h`` px (None: back to ``MIN_VIEW_H``), so it gives way first when the page is
        short. The host gets the same EXPLICIT minimum: a stacked layout floors at its tallest page, and the hidden
        status page outranks the view's own floor otherwise."""
        self._floor = h
        self._host.setMinimumHeight(0 if h is None else h)
        if self.view is not None:
            self.view.setMinimumHeight(MIN_VIEW_H if h is None else h)

    def add_control(self, w):
        """Put a host control (the World tab's draw chooser) at the front of the page's bar."""
        self.bar.insertWidget(0, w)

    def set_caption(self, text):
        self.caption.setText(text)
        self.caption.setVisible(bool(text) and not self._caption_folded)

    def fold_caption(self, folded):
        """Fold the caption away (a carry card is open and the caption says nothing the draw box does not), or show
        it again; the text is kept either way."""
        self._caption_folded = bool(folded)
        self.caption.setVisible(bool(self.caption.text()) and not self._caption_folded)

    def set_overlays(self, overlays):
        """What a tool draws over the map (:attr:`WorldView3D.overlays`), now or once the view exists."""
        self._overlays = list(overlays)
        if self.view is not None:
            self.view.set_overlays(self._overlays)

    def set_ghost(self, ghost):
        self._ghost = ghost
        if self.view is not None:
            self.view.set_ghost(ghost)

    def status_text(self):
        """The words on the status page (the fallback fence reads it)."""
        from PySide6.QtWidgets import QLabel
        return " ".join(lab.text() for lab in self._status.findChildren(QLabel) if lab.text())

    def focus(self, wx, wz):
        """Centre the camera on a world point (the atlas's selected block), now or once the view exists."""
        self._focus = (wx, wz)
        if self.view is not None:
            self.view.focus(wx, wz)

    def load(self, site, *, sync=False):
        if not gl_available():
            self._show_message("The 3D view needs OpenGL",
                               "This display has no OpenGL 2.1 context (a remote desktop or a headless run). "
                               "The chart view and world-render's stills still work.")
            return False
        if self._busy:                                       # the last load asked is the one drawn: this one loads
            self._next = site                                # when the running one lands (it was dropped, and the
            return True                                      # view kept the old folder: review of C19's fixes, r5)
        self._busy = True
        self._show_message("Loading the map…", "Reading the blocks the engine binds, through your mod folders "
                           "in the game's order. About five seconds for the whole map.")
        self.site = site
        if sync:
            self._work(site)
            return True
        threading.Thread(target=self._work, args=(site,), daemon=True).start()
        return True

    def forget_cells(self):
        """The next load draws every cell again (the World tab's Rescan re-reads everything from disk)."""
        self._cells.forget()

    def _work(self, site):
        try:
            packed, textures = load_scene(site, memo=self._cells)
            out = (packed, textures, None)
        except Exception as e:                               # noqa: BLE001 -- surfaced on the GUI thread
            out = (None, None, str(e))
        try:
            self._loaded.emit(*out)
        except RuntimeError:                                 # the panel died while the worker read
            pass

    def _finish(self, packed, textures, err):
        self._busy = False
        nxt, self._next = self._next, None
        if nxt is not None:                                  # overtaken by a newer request: that one is loaded
            self.load(nxt)
            return
        if err is not None:
            self._show_message("The map did not load", err)
            return
        if self.view is None:
            self.view = WorldView3D()
            if self._floor is not None:
                self.view.setMinimumHeight(self._floor)
            self.view.gl_failed.connect(lambda msg: self._show_message("The 3D view needs OpenGL", msg))
            self.view.picked.connect(self.picked.emit)
            self.view.ghost_moved.connect(self.ghost_moved.emit)
            self.view.ghost_dropped.connect(self.ghost_dropped.emit)
            self.view.camera_changed.connect(self._camera_changed)
            self.view.party_moved.connect(lambda x, y, z: self._seat_party())
            self.view.marker_rgb = _rgb(self.pal["accent"])
            self.view.set_overlays(self._overlays)
            self.view.set_ghost(self._ghost)
            self._stack.addWidget(self.view)
        self.view.set_scene(packed, textures)
        if self._focus is not None:
            self.view.focus(*self._focus)
        self._stack.setCurrentWidget(self.view)
        self.game_btn.show()
        if self.view.game_mode():                            # a reload: the party re-stands on the new ground
            self._build_ground(packed)
            self._seat_party()
        # the status page leaves the stack once the view is up (a later message puts a fresh one back): a stacked
        # layout's height-for-width is its tallest page's, so the hidden page's wrapped teach line otherwise
        # outranks set_view_floor's explicit minimum and the card under the view is the one squeezed
        self._stack.removeWidget(self._status)

    # -- the game's own camera (editor C7) --
    def set_game_camera(self, on: bool):
        """Frame the view as the game's camera would (on), or go back to the free orbit about the same point (off)."""
        if self.view is None:
            return
        self._show_vehicle(on)
        if not on:
            if self.view.game_mode():
                self.view.set_camera(self.view.camera.to_orbit())
            return
        if self.view.game_mode():
            return
        from ..world import gamecam as G
        m = self.view.marker
        x, z = (m[0], m[2]) if m is not None else (self.view.camera.target[0], self.view.camera.target[2])
        game = getattr(self.site, "game", None) if self.site is not None else None
        settings = G.Settings.from_game(game) if game is not None else G.Settings()
        view = self.view                # the eye probes the scene drawn NOW: a reload re-seats the party on new ground,
        #                                 and a probe bound to this click's scene kept the old (PERF.md defect 1)
        cam = GameCamera.from_orbit(self.view.camera, (x, 0.0, z), settings=settings,
                                    ground=lambda gx, gz: ground_y(view.packed, gx, gz),
                                    mode=int(self.vehicle_box.currentData() or 0), table=G.transport_table(game),
                                    how=self._vehicle_how())
        self._set_fog()
        self.view.set_camera(cam)
        self._build_ground(self.view.packed)
        self._seat_party()

    @staticmethod
    def _build_ground(packed):
        """The game camera's ground grid, on a worker (its probe scans the map until the grid lands)."""
        if packed is not None and packed.ground_grid() is None:
            threading.Thread(target=packed.build_ground_grid, daemon=True).start()

    def _set_fog(self):
        """The game's fog for the game camera (C18): the Mist years' (measured) or the years without, as the switch
        says, in the install's daylight fog colour; the switch's tooltip says which and where it comes from."""
        if self.view is None:
            return
        from ..world import fog as FG
        game = getattr(self.site, "game", None) if self.site is not None else None
        fog = FG.from_game(game, mist=self.mist_box.isChecked())
        self.view.fog = fog
        self.mist_box.setToolTip("The game's fog, as the game's camera sees it: on = the Mist years (disc 1 until "
                                 "the Outer Continent, and disc 4), off = the years without mist. " + fog.note())
        self.view.update()

    def _show_vehicle(self, on: bool):
        self.vehicle_box.setVisible(on)
        self.mist_box.setVisible(on)
        self.alt_spin.setVisible(on and int(self.vehicle_box.currentData() or 0) in FLYING_MODES)

    def _vehicle_how(self) -> str:
        return str(self.vehicle_box.currentData(HOW_ROLE) or "boarded")

    def _vehicle_changed(self):
        cam = self.view.camera if self.view is not None else None
        if isinstance(cam, GameCamera):
            cam.mode = int(self.vehicle_box.currentData() or 0)
            cam.how = self._vehicle_how()
            self._show_vehicle(True)
            self._seat_party()

    def _seat_party(self):
        """Seat the game camera's party at its point as its vehicle sits there (C8, measured in game): on foot or a
        chocobo on the ground it stands on; the boat at the water's surface less 0.703; a flyer at the height spin,
        raised to the ground below it and never above the ceiling. In the cell's own AREA (which picks the camera's
        posstats: stock grass at the Landing Site is area 42, kit lawn 14) and topograph (a chocobo's forest view)."""
        cam = self.view.camera if self.view is not None else None
        if not isinstance(cam, GameCamera):
            return
        x, _y, z = cam.player
        g = self._ground_at(x, z)
        top = ground_y(self.view.packed, x, z)
        stand = g.get("stand_y", top)
        if cam.mode in FLYING_MODES:
            y = min(CEILING, max(float(self.alt_spin.value()), top if top is not None else 0.0))
        elif cam.mode == BOAT_MODE:
            y = (top if top is not None else 0.0) + BOAT_DRAFT
        else:
            y = 0.0 if stand is None else stand
        cam.player = (x, float(y), z)
        cam.area = int(g.get("area", 14) or 0)
        cam.topograph = g.get("topograph")
        cam._memo = None
        self.view.update()

    def _ground_at(self, x, z) -> dict:
        """The point facts' ground (area, topograph, the height one stands at), or {} when they cannot be read."""
        try:
            from ..world import pointinfo as PI
            return dict(PI.point_info(self.site, x, z, landmark=False)["ground"])
        except Exception:                                    # noqa: BLE001 -- the kit's lawn area: the safe default
            return {}

    def _area_at(self, x, z) -> int:
        return int(self._ground_at(x, z).get("area", 14) or 0)

    def _camera_changed(self, game: bool):
        """The view changed camera on its own (Home goes back to the orbit): the button follows, and the game
        camera's controls with it -- left on the bar, the Mist switch toggled a fog nothing drew (review of C18)."""
        self.game_btn.blockSignals(True)
        self.game_btn.setChecked(game)
        self.game_btn.blockSignals(False)
        self._name_game_btn(game)
        self._show_vehicle(game)

    def _name_game_btn(self, game: bool):
        """The button names where it takes you, as the World tab's chart / 3D toggle does."""
        self.game_btn.setText("Free view" if game else "As the game sees it")

    def retheme(self, pal):
        self.pal = pal
        if self.view is not None:
            self.view.marker_rgb = _rgb(pal["accent"])
            self.view.update()

    def set_scale(self, pct):
        self._scale = pct
