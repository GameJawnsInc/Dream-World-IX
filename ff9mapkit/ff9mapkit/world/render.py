"""Offline textured software renderer over deployed overworld block meshes.

Promoted from ``studies/path-d-new-world/render_gate.py`` (THE RENDER GATE,
registration RENDER-GATE.md) following the ``meshedit.py`` precedent: the study
file remains as a thin shim bound to the V-shore bench preset; this module is
the site-parameterized library. The lift is byte-faithful -- the six committed
bench cameras render pixel-identical through this module (the P-E determinism
gate), and ``terrain_gate.py`` exercises the whole seam.

Engine-faithful choices (Memoria trace, 2026-08-02): UNLIT (WorldMap/Terrain
binds no normal), uv plain 0..1 over one 1024^2 terrain atlas, sea layers
OPAQUE and geometric (frame-swap anim -> frame 0 for stills), NEAREST sampling
(vanilla), alpha-0 texels render WHITE in-game (blank-tile law, world/atlas.py).
Built on the kit's own prior art: ``atlas.load_atlas`` (engine-resolved),
per-name frame-0 caustic textures (THE PER-NAME MATERIAL LAW), and THE
GAME-EYE PASS cull convention (cull when cross(b-a, c-a) . (toward-eye) <= 0;
holes render as sky).

READ-ONLY over the install. Never wired as a deploy side effect: rendering is
opt-in (the ``world-render`` verb), and its output is a report, never a build
failure.

BLIND-SPOT LEDGER (named, standing -- carried verbatim from RENDER-GATE.md):
The renderer cannot see: caustic/uv ANIMATION (sea scrolls in-game), texture
filtering/mip differences, fog/atmosphere, the skybox, draw-order transparency
blending between sea layers, LOD/far-clip behavior, and the ACTUAL in-game
camera path. A green render gate is still a REGRESSION HARNESS, NOT AN ORACLE
-- it sees one lighting-free frame from fixed cameras. Owner playtests remain
the verdict; the gate's job is to stop known DEFECT CLASSES from shipping
again.
"""
from __future__ import annotations

import dataclasses
import math
from pathlib import Path

from PIL import Image

try:
    import numpy as np
except ImportError:                                          # pragma: no cover
    np = None

from .. import config
from . import atlas as A
from . import extract as X
from . import mesh as M

__all__ = [
    "RenderSite", "BENCH_VSHORE", "BENCH_VIEWS", "BENCH_CORNER_BBOX",
    "BLIND_SPOTS", "PARTS", "WATER_TEX", "SKY", "BLANK_WHITE",
    "load_batches", "live_path", "tex_for", "sample", "project", "raster",
    "diff", "render_blocks", "render_state", "calibrate", "cmd_flow",
    "face_grads", "flow_records", "views_around", "cells_around",
    "ground_y_near",
]

BLIND_SPOTS = (
    "BLIND SPOTS (standing): no uv/caustic animation, no filtering/mip, no "
    "fog/skybox, no sea-layer transparency blending, no LOD/far-clip, not the "
    "in-game camera path. A clean render is a REGRESSION HARNESS, NOT AN "
    "ORACLE -- the owner playtest remains the verdict."
)

PARTS = ("Terrain", "Object", "Beach1", "Sea1", "Sea2", "Sea3", "Sea4", "Sea5")
WATER_TEX = {"Beach1": "11_0_128_0", "Sea1": "10_64_0_0", "Sea2": "10_128_0_0",
             "Sea3": "10_128_64_0", "Sea4": "10_128_128_0", "Sea5": "11_64_0_0"}
SKY = (152, 178, 208)
BLANK_WHITE = (255, 255, 255)                                # alpha-0 sample -> white
RES = (960, 640)


def _require_numpy():
    if np is None:
        raise RuntimeError(
            "world rendering needs numpy: pip install numpy (or ff9mapkit[image])")


@dataclasses.dataclass(frozen=True)
class RenderSite:
    """Where to read deployed block meshes from. ``game=None`` resolves the
    install via ``config.find_game_path``; ``water_texdir=None`` derives the
    Moguri loose worldmap texture dir under it (missing dir -> water parts
    render magenta, harmless for geometry checks)."""
    cells: tuple                                             # ((bx, by), ...)
    disc: int = 9
    mod_folder: str = "FF9CustomMap-world"
    game: Path | None = None
    water_texdir: Path | None = None
    parts: tuple = PARTS
    res: tuple = RES

    def resolved(self) -> "RenderSite":
        game = Path(config.find_game_path(None)) if self.game is None else Path(self.game)
        texdir = self.water_texdir
        if texdir is None:
            texdir = game / "MoguriMain" / "StreamingAssets" / "Assets" / \
                "Resources" / "worldmap" / "textures"
        return dataclasses.replace(self, game=game, water_texdir=Path(texdir))


# The V-shore bench (Path D, disc 9): the six bench cells plus the sea ring
# around them -- without the ring, distant coast renders with SKY behind where
# the game shows sea (the graze-camera floating-sliver artifact). Missing
# files skip silently, so absent ring blocks are free.
_BENCH_CELLS = ((5, 7), (6, 7), (7, 7), (5, 8), (6, 8), (7, 8),
                (4, 6), (5, 6), (6, 6), (7, 6), (8, 6), (4, 7), (8, 7),
                (4, 8), (8, 8), (4, 9), (5, 9), (6, 9), (7, 9), (8, 9))
BENCH_VSHORE = RenderSite(cells=_BENCH_CELLS)

# committed bench cameras -- constants once calibration passed; every run
# comparable. owner_close/graze are the playtest-8 vantage classes: the
# mid-range four missed both residuals, so close-range cameras were hand-
# placed to the owner's real vantage (near-top-down ~60 deg / low offshore
# graze) -- `views_around` derives the same two classes for arbitrary sites.
BENCH_VIEWS = {
    "sea_w": dict(kind="persp", eye=(348.0, 9.0, -524.0), at=(381.0, 2.0, -513.0),
                  fov=50.0, reach=90.0),
    "sea_sw": dict(kind="persp", eye=(356.0, 7.0, -540.0), at=(380.0, 2.0, -511.0),
                   fov=50.0, reach=90.0),
    "top": dict(kind="ortho", x0=362.0, x1=398.0, z0=-528.0, z1=-498.0),
    "island": dict(kind="persp", eye=(330.0, 40.0, -604.0), at=(414.0, 2.0, -510.0),
                   fov=55.0, reach=220.0),
    "owner_close": dict(kind="persp", eye=(384.0, 21.0, -504.0),
                        at=(377.5, 0.5, -513.5), fov=50.0, reach=45.0),
    "graze": dict(kind="persp", eye=(366.0, 3.0, -526.0),
                  at=(379.5, 1.0, -512.5), fov=45.0, reach=90.0),
}
BENCH_CORNER_BBOX = (370.0, 390.0, -520.0, -505.0)           # P-D localization box

PRESETS = {"bench-vshore": (BENCH_VSHORE, BENCH_VIEWS)}


# ---------------------------------------------------------------- textures
_TEX: dict = {}


def tex_for(part, site: RenderSite, cache: dict | None = None):
    """(H,W,4) uint8 RGBA or None. Terrain/Object via the kit's engine-resolved
    loader; water parts via the per-name frame-0 Moguri loose PNGs."""
    _require_numpy()
    site = site.resolved()
    cache = _TEX if cache is None else cache
    key = (str(site.game), str(site.water_texdir), part)
    if key in cache:
        return cache[key]
    img = None
    if part in ("Terrain", "Object"):
        img = A.load_atlas(part.lower() if part != "Terrain" else "terrain",
                           game=site.game, source="engine")
    elif part in WATER_TEX:
        p = site.water_texdir / f"{WATER_TEX[part]}.png"
        if p.is_file():
            img = Image.open(p)
    cache[key] = np.asarray(img.convert("RGBA")) if img is not None else None
    return cache[key]


def sample(tex, u, v):
    """NEAREST, Unity V bottom-up; wrap repeat; alpha-0 -> white (blank-tile law)."""
    h, w = tex.shape[:2]
    iu = np.floor((u % 1.0) * w).astype(np.int64) % w
    iv = np.floor((1.0 - (v % 1.0)) * h).astype(np.int64) % h
    rgba = tex[iv, iu].astype(np.float32)
    blank = rgba[:, 3] == 0
    rgb = rgba[:, :3]
    rgb[blank] = BLANK_WHITE
    return rgb


# ---------------------------------------------------------------- mesh loading
def live_path(site: RenderSite, bx, by, part):
    site = site.resolved()
    root = site.game / site.mod_folder / "FF9_Data" / "WorldMap" / \
        f"Disc{site.disc}" / "0_1"
    return root / f"r{by}" / f"Block[{bx}][{by}] {part}.ff9mesh"


def load_batches(site: RenderSite, part_src=None):
    """[(part, verts Nx3 world, uvs Nx2, tris Mx3)]; ``part_src`` maps
    (bx,by,part)->Path overriding the live file (walk_sim convention)."""
    _require_numpy()
    site = site.resolved()
    batches = []
    for (bx, by) in site.cells:
        ox, oz = X.block_world_origin(bx, by)
        for part in site.parts:
            p = live_path(site, bx, by, part)
            if part_src is not None:
                p = part_src.get((bx, by, part), p)
            if not p.is_file():
                continue
            bm = M.blockmesh_from_ff9mesh(p, disc=site.disc, x=bx, y=by,
                                          part=part.lower())
            pos = np.asarray(bm.chan_arrays[X.CH_POS], dtype=np.float64)
            uvc = bm.chan_arrays.get(X.CH_UV)
            uv = np.asarray(uvc, dtype=np.float64)[:, :2] if uvc is not None \
                else np.zeros((len(pos), 2))
            tris = np.asarray(bm.tris, dtype=np.int64)
            w = pos.copy()
            w[:, 0] += ox
            w[:, 2] += oz
            batches.append((part, w, uv, tris))
    return batches


# ---------------------------------------------------------------- camera
def project(view, verts, res=RES):
    """world Nx3 -> (sx, sy, depth); depth grows AWAY from the eye."""
    W, H = res
    if view["kind"] == "ortho":
        x0, x1, z0, z1 = view["x0"], view["x1"], view["z0"], view["z1"]
        sx = (verts[:, 0] - x0) / (x1 - x0) * (W - 1)
        sy = (verts[:, 2] - z0) / (z1 - z0) * (H - 1)
        return sx, sy, -verts[:, 1]
    eye = np.array(view["eye"])
    at = np.array(view["at"])
    fwd = at - eye
    fwd /= np.linalg.norm(fwd)
    right = np.cross(fwd, [0.0, 1.0, 0.0])
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    rel = verts - eye
    cx, cy, cz = rel @ right, rel @ up, rel @ fwd
    f = (H / 2.0) / math.tan(math.radians(view["fov"]) / 2.0)
    czs = np.where(np.abs(cz) < 1e-6, 1e-6, cz)
    return W / 2.0 + f * cx / czs, H / 2.0 - f * cy / czs, cz


# ---------------------------------------------------------------- raster
def raster(view, batches, title, *, site: RenderSite, out_dir=None, cull=True,
           want_ids=False, tex_lookup=None, verbose=True):
    """Rasterize one view. ``out_dir=None`` skips the PNG save (pure mode);
    ``tex_lookup`` (part -> texture array or None) overrides install textures
    -- the hermetic-test hook. ``want_ids``: also return an int32 per-pixel
    owner buffer (batch_index * 2**20 + tri_index, -1 = sky) -- the
    seam-forensics hook."""
    _require_numpy()
    W, H = site.res
    if tex_lookup is None:
        tex_lookup = lambda part: tex_for(part, site)        # noqa: E731
    color = np.zeros((H, W, 3), dtype=np.float32)
    color[:] = SKY
    zbuf = np.full((H, W), np.inf)
    idbuf = np.full((H, W), -1, dtype=np.int64) if want_ids else None
    eye = np.array(view.get("eye", (0.0, 1e6, 0.0)))         # ortho: eye at +inf y
    ncull = ntri = 0

    for bi, (part, verts, uvs, tris) in enumerate(batches):
        sx, sy, dep = project(view, verts, site.res)
        tex = tex_lookup(part)
        for ti_i, t in enumerate(tris):
            i0, i1, i2 = int(t[0]), int(t[1]), int(t[2])
            if view["kind"] == "persp":
                if dep[i0] <= 0.05 or dep[i1] <= 0.05 or dep[i2] <= 0.05:
                    continue
                if "reach" in view:
                    cx3 = (verts[i0] + verts[i1] + verts[i2]) / 3.0
                    if np.linalg.norm(cx3 - np.array(view["at"])) > view["reach"]:
                        continue
            ntri += 1
            if cull:
                # THE GAME-EYE PASS (terrace_wall_strip convention, calibrated):
                # cull when the geometric normal faces away from the eye.
                a3, b3, c3 = verts[i0], verts[i1], verts[i2]
                fn = np.cross(b3 - a3, c3 - a3)
                to_eye = eye - (a3 + b3 + c3) / 3.0
                if float(fn @ to_eye) <= 0.0:
                    ncull += 1
                    continue
            x0f = min(sx[i0], sx[i1], sx[i2]); x1f = max(sx[i0], sx[i1], sx[i2])
            y0f = min(sy[i0], sy[i1], sy[i2]); y1f = max(sy[i0], sy[i1], sy[i2])
            if x1f < 0 or y1f < 0 or x0f > W - 1 or y0f > H - 1:
                continue
            area = ((sx[i1] - sx[i0]) * (sy[i2] - sy[i0])
                    - (sx[i2] - sx[i0]) * (sy[i1] - sy[i0]))
            if abs(area) < 1e-9:
                continue
            xa = max(int(x0f), 0); xb = min(int(math.ceil(x1f)), W - 1)
            ya = max(int(y0f), 0); yb = min(int(math.ceil(y1f)), H - 1)
            gx, gy = np.meshgrid(np.arange(xa, xb + 1), np.arange(ya, yb + 1))
            b0 = ((sx[i1] - sx[i2]) * (gy - sy[i2]) - (sy[i1] - sy[i2]) * (gx - sx[i2])) / -area
            b1 = ((sx[i2] - sx[i0]) * (gy - sy[i0]) - (sy[i2] - sy[i0]) * (gx - sx[i0])) / -area
            b2 = 1.0 - b0 - b1
            m = (b0 >= -1e-9) & (b1 >= -1e-9) & (b2 >= -1e-9)
            if not m.any():
                continue
            if view["kind"] == "persp":                      # perspective-correct
                iz = np.array([1.0 / dep[i0], 1.0 / dep[i1], 1.0 / dep[i2]])
                izp = b0 * iz[0] + b1 * iz[1] + b2 * iz[2]
                d = 1.0 / np.maximum(izp, 1e-12)
                pu = (b0 * uvs[i0, 0] * iz[0] + b1 * uvs[i1, 0] * iz[1]
                      + b2 * uvs[i2, 0] * iz[2]) * d
                pv = (b0 * uvs[i0, 1] * iz[0] + b1 * uvs[i1, 1] * iz[1]
                      + b2 * uvs[i2, 1] * iz[2]) * d
            else:
                d = b0 * dep[i0] + b1 * dep[i1] + b2 * dep[i2]
                pu = b0 * uvs[i0, 0] + b1 * uvs[i1, 0] + b2 * uvs[i2, 0]
                pv = b0 * uvs[i0, 1] + b1 * uvs[i1, 1] + b2 * uvs[i2, 1]
            zt = zbuf[ya:yb + 1, xa:xb + 1]
            vis = m & (d < zt)
            if not vis.any():
                continue
            sub = color[ya:yb + 1, xa:xb + 1]
            if tex is not None:
                sub[vis] = sample(tex, pu[vis], pv[vis])
            else:
                sub[vis] = (200, 60, 200)                    # missing texture = magenta
            zt[vis] = d[vis]
            if idbuf is not None:
                idbuf[ya:yb + 1, xa:xb + 1][vis] = bi * (1 << 20) + ti_i

    img = Image.fromarray(np.clip(color, 0, 255).astype(np.uint8))
    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        img.save(out_dir / f"{title}.png")
        if verbose:
            print(f"   render {title}.png  tris={ntri} culled={ncull}")
    elif verbose:
        print(f"   render {title} (unsaved)  tris={ntri} culled={ncull}")
    if want_ids:
        return np.asarray(img), idbuf
    return np.asarray(img)


# ---------------------------------------------------------------- diff
def diff(a, b, title, *, out_dir=None, thresh=18, verbose=True):
    """Max-channel pixel diff; writes ``diff_<title>.png`` with changed pixels
    in red when any change and ``out_dir`` given. Reports; never fails."""
    _require_numpy()
    d = np.abs(a.astype(np.int32) - b.astype(np.int32)).max(axis=2)
    mask = d > thresh
    n = int(mask.sum())
    ys, xs = np.nonzero(mask)
    box = None if n == 0 else (int(xs.min()), int(xs.max()), int(ys.min()), int(ys.max()))
    if verbose:
        print(f"   diff {title}: {n} px changed  box={box}")
    if n and out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        vis = (a // 3).astype(np.uint8)
        vis[mask] = (255, 40, 40)
        Image.fromarray(vis).save(out_dir / f"diff_{title}.png")
    return n, box


# ---------------------------------------------------------------- entry points
def render_blocks(site: RenderSite, views, *, out_dir=None, part_src=None,
                  prefix="", want_ids=False, verbose=True):
    """THE one entry point: load the site's deployed block meshes (optionally
    overridden per-part via ``part_src``) and raster every view. Returns
    {view_name: image array} (with ``want_ids``: (image, idbuf) tuples)."""
    batches = load_batches(site, part_src)
    if verbose:
        nt = sum(len(t) for _, _, _, t in batches)
        print(f"[render] {len(batches)} part batches, {nt} tris total")
    return {vn: raster(v, batches, f"{prefix}{vn}", site=site, out_dir=out_dir,
                       want_ids=want_ids, verbose=verbose)
            for vn, v in views.items()}


def render_state(tag, *, site: RenderSite, views, out_dir=None, state_src=None,
                 verbose=True):
    """The study's ``cmd_render``: render one named corpus state. ``state_src``
    maps tag -> {(bx,by,part): Path}; None allows only ``"live"``."""
    if state_src is not None:
        src = state_src(tag)
    elif tag == "live":
        src = {}
    else:
        raise ValueError(f"no state_src given; unknown state {tag!r}")
    for p in src.values():
        assert Path(p).is_file(), f"missing corpus file: {p}"
    batches = load_batches(site, src)
    if verbose:
        nt = sum(len(t) for _, _, _, t in batches)
        print(f"[{tag}] {len(batches)} part batches, {nt} tris total")
    return {vn: raster(v, batches, f"{tag}_{vn}", site=site, out_dir=out_dir,
                       verbose=verbose)
            for vn, v in views.items()}


def calibrate(*, site: RenderSite, views, out_dir, state_src,
              tags=("baseline", "v1", "v2")):
    """The study's calibration run: P-E determinism (baseline re-render diffs
    to 0 px) + candidate-vs-baseline diffs for every committed camera."""
    imgs = {t: render_state(t, site=site, views=views, out_dir=out_dir,
                            state_src=state_src) for t in tags}
    base = tags[0]
    print(f"\n=== P-E determinism ({base} re-render) ===")
    b = load_batches(site, state_src(base))
    for vn, v in views.items():
        r2 = raster(v, b, f"{base}2_{vn}", site=site, out_dir=out_dir)
        diff(imgs[base][vn], r2, f"PE_{vn}", out_dir=out_dir, thresh=0)
    print(f"\n=== candidate vs {base} ===")
    for tag in tags[1:]:
        for vn in views:
            diff(imgs[base][vn], imgs[tag][vn], f"{tag}_{vn}", out_dir=out_dir)
    return imgs


# ---------------------------------------------------------------- texture flow
def face_grads(verts, uvs, tri):
    """3D uv gradients of one face: (grad_u, grad_v, handedness, unit normal).
    grad_u is the in-plane world vector g with g.e1 = du1, g.e2 = du2 --
    frame-independent, so faces are comparable across the whole mesh.
    handedness = (grad_u x grad_v) . n -- its SIGN flips iff the texture is
    mirrored relative to the winding ("flipped faces" in owner language).
    A ~zero gradient = constant-uv smear (one texel stretched over the face)."""
    a, b, c = verts[tri[0]], verts[tri[1]], verts[tri[2]]
    e1, e2 = b - a, c - a
    n = np.cross(e1, e2)
    n2 = float(n @ n)
    if n2 < 1e-12:
        return None
    d1 = uvs[tri[1]] - uvs[tri[0]]
    d2 = uvs[tri[2]] - uvs[tri[0]]
    x2n, nx1 = np.cross(e2, n), np.cross(n, e1)
    gu = (d1[0] * x2n + d2[0] * nx1) / n2
    gv = (d1[1] * x2n + d2[1] * nx1) / n2
    nu = n / math.sqrt(n2)
    return gu, gv, float(np.cross(gu, gv) @ nu), nu


def flow_records(verts, uvs, tris, zone=None):
    """Per-face flow records [(idx, centroid, |gu|, |gv|, hand)] + shared-edge
    records [(idx_a, idx_b, mid, dang_u_deg, uv_jump)] for Terrain faces
    (zone = optional (x0,x1,z0,z1) centroid filter)."""
    _require_numpy()
    faces, gus = [], {}
    edge_map = {}
    for fi, t in enumerate(tris):
        i0, i1, i2 = int(t[0]), int(t[1]), int(t[2])
        cx = (verts[i0] + verts[i1] + verts[i2]) / 3.0
        if zone is not None:
            x0, x1, z0, z1 = zone
            if not (x0 <= cx[0] <= x1 and z0 <= cx[2] <= z1):
                continue
        g = face_grads(verts, uvs, (i0, i1, i2))
        if g is None:
            continue
        gu, gv, hand, _ = g
        faces.append((fi, cx, float(np.linalg.norm(gu)),
                      float(np.linalg.norm(gv)), hand))
        gus[fi] = (gu, gv)
        for a, b in ((i0, i1), (i1, i2), (i2, i0)):
            ka = (round(float(verts[a][0]), 3), round(float(verts[a][1]), 3),
                  round(float(verts[a][2]), 3))
            kb = (round(float(verts[b][0]), 3), round(float(verts[b][1]), 3),
                  round(float(verts[b][2]), 3))
            ek = tuple(sorted((ka, kb)))
            edge_map.setdefault(ek, []).append(
                (fi, {ka: uvs[a].copy(), kb: uvs[b].copy()}))
    edges = []
    for ek, uses in edge_map.items():
        if len(uses) != 2:
            continue
        (fa, uva), (fb, uvb) = uses
        gua = gus[fa][0]
        gub = gus[fb][0]
        na, nb = np.linalg.norm(gua), np.linalg.norm(gub)
        if na < 1e-9 or nb < 1e-9:
            dang = 180.0                                     # smear vs anything
        else:
            dang = math.degrees(math.acos(
                max(-1.0, min(1.0, float(gua @ gub) / (na * nb)))))
        jump = max(float(np.abs(uva[k] - uvb[k]).max()) for k in uva)
        mid = np.array(ek[0]) * 0.5 + np.array(ek[1]) * 0.5
        edges.append((fa, fb, mid, dang, jump))
    return faces, edges


def _flow_summary(label, faces, edges):
    gm = np.array([[f[2], f[3]] for f in faces]) if faces else np.zeros((0, 2))
    hands = np.array([f[4] for f in faces]) if faces else np.zeros(0)
    nzero = int((gm.max(axis=1) < 1e-6).sum()) if len(gm) else 0
    print(f"[{label}] {len(faces)} faces, {len(edges)} shared edges")
    if len(gm):
        p = np.percentile
        print(f"   |grad| u p1/p50/p99: {p(gm[:,0],1):.5f}/{p(gm[:,0],50):.5f}/"
              f"{p(gm[:,0],99):.5f}   v: {p(gm[:,1],1):.5f}/{p(gm[:,1],50):.5f}/"
              f"{p(gm[:,1],99):.5f}")
        print(f"   handedness: {int((hands > 0).sum())} pos / "
              f"{int((hands < 0).sum())} neg   constant-uv faces: {nzero}")
    if edges:
        da = np.array([e[3] for e in edges])
        seams = [e for e in edges if e[4] > 0.03]
        print(f"   edge d-angle(u) p50/p90/p99: {np.percentile(da,50):.1f}/"
              f"{np.percentile(da,90):.1f}/{np.percentile(da,99):.1f} deg   "
              f"uv-cut edges (jump>0.03): {len(seams)}")
    return gm, hands


def cmd_flow(tag="live", *, site: RenderSite, corner_bbox, state_src=None,
             stock_ref=(5, 14, 1)):
    """The analytic texture-flow instrument: judge a zone's uv flow against two
    references -- a stock donor block's own distribution and the live site
    OUTSIDE the zone (the owner-passed look)."""
    _require_numpy()
    sbx, sby, sdisc = stock_ref
    print(f"=== reference: stock donor block ({sbx},{sby}), disc {sdisc} ===")
    bm = X.read_block(sbx, sby, disc=sdisc, part="terrain")
    ox, oz = X.block_world_origin(sbx, sby)
    pos = np.asarray(bm.chan_arrays[X.CH_POS], dtype=np.float64)
    pos[:, 0] += ox
    pos[:, 2] += oz
    suv = bm.chan_arrays.get(X.CH_UV)
    suv = np.asarray(suv, dtype=np.float64)[:, :2]
    sf, se = flow_records(pos, suv, np.asarray(bm.tris, dtype=np.int64))
    sgm, shands = _flow_summary(f"stock {sbx},{sby}", sf, se)

    if state_src is not None:
        src = state_src(tag)
    elif tag == "live":
        src = {}
    else:
        raise ValueError(f"no state_src given; unknown state {tag!r}")
    batches = load_batches(site, src)
    terr = [(p, v, u, t) for (p, v, u, t) in batches if p == "Terrain"]
    bench_f, bench_e, corner_f, corner_e = [], [], [], []
    x0, x1, z0, z1 = corner_bbox
    for _, v, u, t in terr:
        cf, ce = flow_records(v, u, t, zone=corner_bbox)
        corner_f += cf
        corner_e += ce
        bf, be = flow_records(v, u, t)
        bench_f += [f for f in bf if not (x0 <= f[1][0] <= x1 and z0 <= f[1][2] <= z1)]
        bench_e += [e for e in be if not (x0 <= e[2][0] <= x1 and z0 <= e[2][2] <= z1)]
    print("\n=== reference: live site outside the zone (owner-passed) ===")
    _flow_summary("bench-out", bench_f, bench_e)
    print(f"\n=== EVAL: zone bbox {corner_bbox} [{tag}] ===")
    _flow_summary("corner", corner_f, corner_e)

    lo = float(np.percentile(sgm.max(axis=1), 1)) / 2.0 if len(sgm) else 1e-4
    hand_ref = 1.0 if (shands > 0).sum() >= (shands < 0).sum() else -1.0
    smears = [f for f in corner_f if max(f[2], f[3]) < 1e-6]
    stretch = [f for f in corner_f if 1e-6 <= max(f[2], f[3]) < lo]
    flips = [f for f in corner_f if f[4] * hand_ref < 0 and max(f[2], f[3]) >= 1e-6]
    print(f"\n--- verdicts (stock floor {lo:.5f}, stock handedness "
          f"{'+' if hand_ref > 0 else '-'}) ---")
    for name, group in (("CONSTANT-UV SMEAR", smears), ("STRETCHED", stretch),
                        ("HANDEDNESS FLIP (mirrored)", flips)):
        print(f"{name}: {len(group)} faces")
        for f in sorted(group, key=lambda f: (f[1][0], f[1][2]))[:12]:
            print(f"   @({f[1][0]:7.2f},{f[1][1]:6.2f},{f[1][2]:8.2f})  "
                  f"|gu|={f[2]:.5f} |gv|={f[3]:.5f} hand={f[4]:+.6f}")
    hot = sorted([e for e in corner_e if e[3] > 45.0 and e[4] <= 0.03],
                 key=lambda e: -e[3])
    print(f"ROTATED FLOW (edge d-angle>45deg, uv-continuous): {len(hot)} edges")
    for e in hot[:12]:
        print(f"   @({e[2][0]:7.2f},{e[2][1]:6.2f},{e[2][2]:8.2f})  "
              f"d-angle={e[3]:6.1f}  jump={e[4]:.4f}")
    return dict(smears=len(smears), stretch=len(stretch), flips=len(flips),
                rotated=len(hot))


# ---------------------------------------------------------------- auto rig
# The two close-range vantage CLASSES, by construction (RENDER-GATE.md:124-135:
# the four mid-range cameras MISSED both playtest-8 residuals; owner_close and
# graze were hand-placed to the owner's real vantage). Parameters derived from
# those two committed cameras: close = eye ~11.5u out / ~20.5u up (~60 deg
# pitch onto the target), graze = eye ~19u out / ~2u above the waterline,
# near edge-on. Four azimuths per class because the rig cannot know which side
# the sea is on; names encode the eye-offset direction in world axes.
_AZIMUTHS = (("px_pz", (0.7071067811865476, 0.7071067811865476)),
             ("nx_pz", (-0.7071067811865476, 0.7071067811865476)),
             ("nx_nz", (-0.7071067811865476, -0.7071067811865476)),
             ("px_nz", (0.7071067811865476, -0.7071067811865476)))
CLOSE_DIST, CLOSE_UP = 11.5, 20.5
GRAZE_DIST, GRAZE_UP = 19.0, 2.0


def views_around(wx, wz, *, ground_y=0.0, overview=True):
    """Derive the committed vantage classes for an arbitrary target: one ortho
    ``top`` (the bench's 36x30u box), 4x ``close_*`` (near-top-down, ~60 deg),
    4x ``graze_*`` (low offshore, near edge-on to the waterline), plus one
    ``overview`` (the bench island camera translated to the target)."""
    at_close = (wx, ground_y + 0.5, wz)
    at_graze = (wx, ground_y + 1.0, wz)
    views = {"top": dict(kind="ortho", x0=wx - 18.0, x1=wx + 18.0,
                         z0=wz - 15.0, z1=wz + 15.0)}
    for name, (dx, dz) in _AZIMUTHS:
        views[f"close_{name}"] = dict(
            kind="persp", eye=(wx + CLOSE_DIST * dx, ground_y + 0.5 + CLOSE_UP,
                               wz + CLOSE_DIST * dz),
            at=at_close, fov=50.0, reach=45.0)
        views[f"graze_{name}"] = dict(
            kind="persp", eye=(wx + GRAZE_DIST * dx, ground_y + 1.0 + GRAZE_UP,
                               wz + GRAZE_DIST * dz),
            at=at_graze, fov=45.0, reach=90.0)
    if overview:
        views["overview"] = dict(
            kind="persp", eye=(wx - 84.0, ground_y + 40.0, wz - 94.0),
            at=(wx, ground_y + 2.0, wz), fov=55.0, reach=220.0)
    return views


def ground_y_near(batches, wx, wz, radius=8.0, fallback=0.0):
    """Median Terrain-vert height within ``radius`` of the target -- anchors
    the auto rig's eye/at heights to the site's own ground."""
    _require_numpy()
    ys = []
    for part, verts, _, _ in batches:
        if part != "Terrain":
            continue
        d2 = (verts[:, 0] - wx) ** 2 + (verts[:, 2] - wz) ** 2
        near = verts[d2 <= radius * radius]
        if len(near):
            ys.append(near[:, 1])
    if not ys:
        return fallback
    return float(np.median(np.concatenate(ys)))


def cells_around(wx, wz, radius=96.0):
    """The block cover of the square [wx-r, wx+r] x [wz-r, wz+r], clamped to
    the 24x20 grid. Missing block files skip silently at load, so an over-
    generous cover is free (and buys the sea ring behind distant coast)."""
    bx_lo = max(0, math.floor((wx - radius) / X.BLOCK_SIZE))
    bx_hi = min(M.GRID_COLS - 1, math.floor((wx + radius) / X.BLOCK_SIZE))
    by_lo = max(0, math.floor(-(wz + radius) / X.BLOCK_SIZE))
    by_hi = min(M.GRID_ROWS - 1, math.floor(-(wz - radius) / X.BLOCK_SIZE))
    return tuple((bx, by) for by in range(by_lo, by_hi + 1)
                 for bx in range(bx_lo, bx_hi + 1))
