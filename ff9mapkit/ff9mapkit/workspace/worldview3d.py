"""The World tab's 3D view: the overworld as the engine binds it, on the GPU (editor rung A0, read-only).

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

Not here (later rungs): picking (A1), the x-torus wrap at the 23|0 seam, sea animation, fog, the sky.
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
from PySide6.QtWidgets import QStackedLayout, QVBoxLayout, QWidget

NEAR = 0.05                    # render.raster drops a tri with any vertex this close to the eye (or behind it)
ORTHO_Y = (-200.0, 400.0)      # the y span an ortho still's depth maps over (the world sits in about -6..60)
MISSING_RGB = (200, 60, 200)   # render.raster's missing-texture magenta
FOV = 50.0                     # the interactive camera's field of view (the bench cameras' own)
PITCH_MIN, PITCH_MAX = 4.0, 89.0
DIST_MIN, DIST_MAX = 6.0, 2400.0
MAP_CENTRE = (768.0, 0.0, -640.0)                            # the 24x20 grid's middle, world units

GL_TRIANGLES, GL_FLOAT = 0x0004, 0x1406
GL_DEPTH_TEST, GL_CULL_FACE, GL_BACK, GL_LESS = 0x0B71, 0x0B44, 0x0405, 0x0201
GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT = 0x4000, 0x0100

_VERT = """#version 120
attribute vec3 a_pos;
attribute vec2 a_uv;
uniform mat4 u_mvp;
varying vec2 v_uv;
void main() { v_uv = a_uv; gl_Position = u_mvp * vec4(a_pos, 1.0); }
"""
# Unity V is bottom-up and the texture is uploaded top row first, so t = 1 - v: render.sample's
# floor((1 - frac(v)) * h) mod h is exactly GL's NEAREST + REPEAT texel for that t.
_FRAG = """#version 120
uniform sampler2D u_tex;
uniform int u_has_tex;
uniform vec3 u_missing;
varying vec2 v_uv;
void main() {
    if (u_has_tex == 0) { gl_FragColor = vec4(u_missing, 1.0); return; }
    gl_FragColor = vec4(texture2D(u_tex, vec2(v_uv.x, 1.0 - v_uv.y)).rgb, 1.0);
}
"""


class GLUnavailable(RuntimeError):
    """No usable OpenGL here (the offscreen platform, a headless CI box, a GL older than 2.1)."""


# ---------------------------------------------------------------- the projection (pure)
def view_basis(view):
    """``(eye, right, up, fwd)`` exactly as ``render.project`` derives them (fwd = at - eye, right = fwd x Y)."""
    eye = np.asarray(view["eye"], dtype=np.float64)
    fwd = np.asarray(view["at"], dtype=np.float64) - eye
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, [0.0, 1.0, 0.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
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

    @property
    def parts(self):
        return list(self.arrays)


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


def compare(oracle, gpu, *, sky=None) -> dict:
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
    """
    from ..world import render as R
    sky = R.SKY if sky is None else sky
    a = np.asarray(oracle, dtype=np.int16)
    b = np.asarray(gpu, dtype=np.int16)
    diff = (a != b).any(axis=2)
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


def load_scene(site, *, part_src=None):
    """``(Packed, {part: rgba or None})`` for a :class:`~ff9mapkit.world.render.RenderSite`, stock under the
    overrides. Pure numpy + file reads: the panel runs it on a worker thread."""
    from ..world import render as R
    batches = R.load_batches(site, part_src, stock=True)
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

    def draw(self, f, mvp: np.ndarray, *, cull: bool = True):
        f.glEnable(GL_DEPTH_TEST)
        f.glDepthFunc(GL_LESS)
        if cull:                                             # CCW front = the normal faces the eye (render's cull)
            f.glEnable(GL_CULL_FACE)
            f.glCullFace(GL_BACK)
        else:
            f.glDisable(GL_CULL_FACE)
        prog = self.prog
        prog.bind()
        prog.setUniformValue("u_mvp", QMatrix4x4(*[float(v) for v in mvp.reshape(-1)]))
        prog.setUniformValue1i(prog.uniformLocation("u_tex"), 0)
        prog.setUniformValue("u_missing", *[c / 255.0 for c in MISSING_RGB])
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

    def release_scene(self):
        for vbo in self.vbos.values():
            vbo.destroy()
        for tex in self.texs.values():
            tex.destroy()
        self.vbos, self.texs, self.draws = {}, {}, []


def _clear(f, rgb):
    f.glClearColor(rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0, 1.0)
    f.glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)


def render_still(batches, view, *, res=None, tex_lookup=None, site=None, cull=True):
    """One still on the GPU, the way ``render.raster(view, batches, ...)`` draws it: (H, W, 3) uint8.

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
        _clear(f, R.SKY)
        packed = pack(batches, view)
        scene = _GLScene()
        scene.init()
        scene.upload(packed, {p: texture_rgba(tex_lookup(p)) for p in packed.parts})
        scene.draw(f, clip_matrix(view, res), cull=cull)
        f.glFinish()
        img = fbo.toImage().convertToFormat(QImage.Format.Format_RGB888)
        fbo.release()
        scene.release_scene()
        ptr = img.constBits()
        arr = np.frombuffer(ptr, dtype=np.uint8, count=img.sizeInBytes()).reshape(H, img.bytesPerLine())
        return arr[:, :W * 3].reshape(H, W, 3).copy()        # copy: the QImage owns those bytes
    finally:
        ctx.doneCurrent()


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
        self.yaw = (self.yaw - dx_px * 0.3) % 360.0
        self.pitch = min(PITCH_MAX, max(PITCH_MIN, self.pitch + dy_px * 0.3))

    def pan(self, dx_px, dy_px, height_px):
        """Slide the target over the ground plane so the point under the cursor follows it."""
        per_px = 2.0 * self.dist * math.tan(math.radians(self.fov) / 2.0) / max(1, height_px)
        y = math.radians(self.yaw)
        rx, rz = -math.cos(y), math.sin(y)                   # screen-right on the ground (render's right = fwd x Y)
        fx, fz = math.sin(y), math.cos(y)                    # screen-up on the ground (toward the view direction)
        tx, ty, tz = self.target
        self.target = (tx - (dx_px * rx - dy_px * fx) * per_px, ty, tz - (dx_px * rz - dy_px * fz) * per_px)

    def zoom(self, steps):
        self.dist = min(DIST_MAX, max(DIST_MIN, self.dist * (0.85 ** steps)))


class WorldView3D(QOpenGLWidget):
    """The orbitable view. Left-drag orbits, right- or middle-drag pans, the wheel zooms, Home re-frames."""

    gl_failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        fmt = QSurfaceFormat()
        fmt.setDepthBufferSize(24)
        self.setFormat(fmt)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAccessibleName("3D overworld view")
        self.setMinimumSize(240, 180)
        self.camera = OrbitCamera()
        self._scene = _GLScene()
        self._pending = None                                 # (packed, textures) waiting for a current context
        self._ready = False
        self._drag = None

    def set_scene(self, packed: Packed, textures: dict):
        self._pending = (packed, textures)
        self.update()

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
        _clear(f, R.SKY)
        if not self._ready:
            return
        if self._pending is not None:
            self._scene.upload(*self._pending)
            self._pending = None
        cam = self.camera
        self._scene.draw(f, clip_matrix(cam.view(), (w, h), far=cam.far()))

    # -- input --
    def mousePressEvent(self, e):
        self._drag = (e.button(), e.position())
        e.accept()

    def mouseMoveEvent(self, e):
        if self._drag is None:
            return
        button, last = self._drag
        d: QPointF = e.position() - last
        if button == Qt.MouseButton.LeftButton:
            self.camera.orbit(d.x(), d.y())
        else:
            self.camera.pan(d.x(), d.y(), self.height())
        self._drag = (button, e.position())
        self.update()

    def mouseReleaseEvent(self, e):
        self._drag = None

    def wheelEvent(self, e):
        self.camera.zoom(e.angleDelta().y() / 120.0)
        self.update()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Home:
            self.camera = OrbitCamera()
            self.update()
            return
        super().keyPressEvent(e)

    def release_gl(self):
        if self._ready and self.context() is not None:
            self.makeCurrent()
            self._scene.release_scene()
            self.doneCurrent()


class WorldView3DPanel(QWidget):
    """The 3D page of the World tab: a status/fallback page until the map is loaded, then the view.

    ``load(site)`` reads on a worker thread (the World tab's own scan shape); ``load(site, sync=True)`` is the
    deterministic lane for tests and gui_snap."""

    _loaded = Signal(object, object, object)                 # (packed | None, textures | None, error | None)

    def __init__(self, pal, *, scale=100):
        super().__init__()
        self.pal, self._scale = pal, scale
        self.view = None
        self._busy = False
        self._focus = None
        self._loaded.connect(self._finish)
        self._stack = QStackedLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._status = self._message("Loading the map…", "Reading the blocks the engine binds: stock land "
                                     "under your overrides. About five seconds for the whole map.")
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
        if self._busy:
            return True
        self._busy = True
        self._show_message("Loading the map…", "Reading the blocks the engine binds: stock land under your "
                           "overrides. About five seconds for the whole map.")
        if sync:
            self._work(site)
            return True
        threading.Thread(target=self._work, args=(site,), daemon=True).start()
        return True

    def _work(self, site):
        try:
            packed, textures = load_scene(site)
            out = (packed, textures, None)
        except Exception as e:                               # noqa: BLE001 -- surfaced on the GUI thread
            out = (None, None, str(e))
        try:
            self._loaded.emit(*out)
        except RuntimeError:                                 # the panel died while the worker read
            pass

    def _finish(self, packed, textures, err):
        self._busy = False
        if err is not None:
            self._show_message("The map did not load", err)
            return
        if self.view is None:
            self.view = WorldView3D()
            self.view.gl_failed.connect(lambda msg: self._show_message("The 3D view needs OpenGL", msg))
            self._stack.addWidget(self.view)
        self.view.set_scene(packed, textures)
        if self._focus is not None:
            self.view.focus(*self._focus)
        self._stack.setCurrentWidget(self.view)

    def retheme(self, pal):
        self.pal = pal

    def set_scale(self, pct):
        self._scale = pct
