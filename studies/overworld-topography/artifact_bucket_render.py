"""Bucket-labeled render of the artifact window: same triangles as artifact_zoom_render.py, but
solid-colored by GroundRetile classification bucket (mains=tan, wall=gray, sand=yellow,
recovered=MAGENTA, foam=cyan, other=black) instead of textured -- to nail down which bucket
produces the hatched patch by elimination, not guesswork."""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ff9mapkit"))
from ff9mapkit import config as _cfg                          # noqa: E402
from ff9mapkit.world import mesh as M                          # noqa: E402
from ff9mapkit.world import discmirror as DM                   # noqa: E402
from ff9mapkit.world import transplant as TR                   # noqa: E402
from ff9mapkit.world.transplant import decode_id               # noqa: E402

BLOCK = 64.0
SC = 24

BUCKET_COLOR = {
    "mains": (210, 180, 140), "wall": (120, 120, 120), "sand": (230, 210, 90),
    "recovered": (255, 0, 255), "foam": (0, 220, 220), None: (0, 0, 0),
}

# ---- tag every terrain tri the retile touches with its bucket, keyed by donor-frame centroid ----
_tag_by_centroid: dict = {}
_ORIG_APPLY = TR.GroundRetile.apply


def _tagging_apply(self, part, poly):
    n_before = dict(self.n)
    u_before = len(self.unclassified)
    result = _ORIG_APPLY(self, part, poly)
    if part in ("terrain", "beach1"):
        cx = round(sum(v[0][0] for v in poly) / len(poly), 3)
        cz = round(sum(v[0][2] for v in poly) / len(poly), 3)
        n_after = dict(self.n)
        bucket = next((k for k in n_after if n_after.get(k, 0) > n_before.get(k, 0)), None)
        if len(self.unclassified) > u_before:
            bucket = None
        _tag_by_centroid[(cx, cz)] = bucket
    return result


TR.GroundRetile.apply = _tagging_apply


def world_tris(bm, bx, by):
    V = np.asarray(bm.verts, dtype=np.float64)
    N = np.asarray(bm.normals, dtype=np.float64)
    U = np.asarray(bm.uvs, dtype=np.float64)
    T = np.asarray(bm.tangents, dtype=np.float64) if hasattr(bm, "tangents") else None
    for i in np.asarray(bm.flat_index, dtype=np.int64).reshape(-1, 3):
        p3 = [(V[j][0] + BLOCK * bx, V[j][1], V[j][2] - BLOCK * by) for j in i]
        yield p3


def render(mesh_entries, cx, cz, winx, winz):
    x0, x1 = cx - winx / 2, cx + winx / 2
    z0, z1 = cz - winz / 2, cz + winz / 2
    RW, RH = int(winx * SC), int(winz * SC)
    tex = Image.new("RGB", (RW, RH), (150, 178, 210))
    tp = tex.load()
    tris = []
    for (bx, by, bm) in mesh_entries:
        for p3 in world_tris(bm, bx, by):
            if max(p[0] for p in p3) < x0 or min(p[0] for p in p3) > x1:
                continue
            if max(p[2] for p in p3) < z0 or min(p[2] for p in p3) > z1:
                continue
            # match to the ORIGINAL donor-frame centroid: target = donor + (704, 0) for this window
            cx_t = round(sum(p[0] for p in p3) / 3 - 704.0, 3)
            cz_t = round(sum(p[2] for p in p3) / 3, 3)
            # nearest tag within 0.05 (float rounding)
            bucket = None
            for (kx, kz), b in _tag_by_centroid.items():
                if abs(kx - cx_t) < 0.05 and abs(kz - cz_t) < 0.05:
                    bucket = b
                    break
            tris.append((max(p[1] for p in p3), p3, bucket))
    for _, p3, bucket in sorted(tris, key=lambda t: t[0]):
        sx = [(p[0] - x0) * SC for p in p3]
        sy = [(z1 - p[2]) * SC for p in p3]
        bx0, bx1 = int(min(sx)), int(max(sx)) + 1
        by0, by1 = int(min(sy)), int(max(sy)) + 1
        d = (sy[1] - sy[2]) * (sx[0] - sx[2]) + (sx[2] - sx[1]) * (sy[0] - sy[2])
        if abs(d) < 1e-9:
            continue
        col = BUCKET_COLOR.get(bucket, (255, 255, 255))
        for pxx in range(max(0, bx0), min(RW, bx1)):
            for pyy in range(max(0, by0), min(RH, by1)):
                w0 = ((sy[1] - sy[2]) * (pxx - sx[2]) + (sx[2] - sx[1]) * (pyy - sy[2])) / d
                w1 = ((sy[2] - sy[0]) * (pxx - sx[2]) + (sx[0] - sx[2]) * (pyy - sy[2])) / d
                w2 = 1 - w0 - w1
                if w0 < -1e-9 or w1 < -1e-9 or w2 < -1e-9:
                    continue
                tp[pxx, pyy] = col
    return tex


_captured: dict = {}


def _fake_deploy_override(bm, *, mod_folder, game=None, lod="0_1", part="Terrain"):
    _captured[(bm.x, bm.y, part.lower())] = bm
    return "FAKE"


def _fake_sidecar(dx, dy, *, mod_folder, disc, x, y, lod="0_1", game=None):
    return "FAKE"


def _fake_mirror(paths, *, mod_folder, skip_mirror=False, game=None):
    return None


M.deploy_override = _fake_deploy_override
M.deploy_donor_sidecar = _fake_sidecar
DM.auto_mirror = _fake_mirror

gt = TR.GroundRetile.for_donor((8, 17), "desert", size=(2, 2), strips="auto", extra=8.0, disc=1)
summary = TR.transplant_region(
    "FF9CustomMap-world", cell=(19, 17), donor=(8, 17), size=(2, 2), rot=0, shift=(0.0, 0.0),
    strips="auto", tweaks=[gt], extra=8.0, land_margin=0.0, disc=1, dry_run=False)
assert summary["clean"]
print(f"tagged {len(_tag_by_centroid)} terrain/beach1 tri classifications")

carry_entries = [(bx, by, bm) for (bx, by, part), bm in _captured.items() if part == "terrain"]
tex = render(carry_entries, 1315.0, -1132.0, 40.0, 40.0)
OUT = Path(__file__).with_name("out")
OUT.mkdir(exist_ok=True)
tex.save(OUT / "artifact_bucket_render.png")
print("->", OUT / "artifact_bucket_render.png")
print("legend:", BUCKET_COLOR)
