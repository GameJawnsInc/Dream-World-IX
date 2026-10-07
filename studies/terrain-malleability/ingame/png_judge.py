"""Shared instrument for the PER-CELL PNG OVERRIDE experiment (terrain study README section 7.1, rank 6).

Imported by png_prep.py (offline build + calibration), png_session.py (the in-game scenario), png_post.py (offline
re-scoring of a run directory) and png_dryrun.py (FakeGame dry run). It holds no game bytes.

THE MECHANISM UNDER TEST (cites = the shared Memoria clone, s34 patch lines marked):
  * WMWorld.RegisterBlockComponent (WMWorld.cs:812-858) loads `Block[x][y] <child>.ff9mesh` (:823-825, s34) and
    ONLY IF that mesh override exists (:826) calls WorldMeshOverride.TryLoadTexture (:835-836, s34), which reads
    `<mod>/FF9_Data/WorldMap/Disc{d}/0_1/r{y}/Block[x][y] <child>.png` from the highest folder holding it
    (WorldMeshOverride.cs:141-170, s34), logs `[WorldMeshOverride] loaded texture '<child>' from <path>` (:160)
    and the call site clones the renderer's material with that texture (WMWorld.cs:839-845, s34).
  * LoadBlock then ends with block.SetupPreloadedMaterials() (WMWorld.cs:808, stock), which reassigns
    `renderer.material = MaterialDatabase[gameObject.name]` (WMBlock.cs:106-111, stock). The database holds a name
    only when its loose texture is found (WMBlock.cs:273-306, `SearchAssetOnDisc`); ObjectNameToPaths
    (WMBlock.cs:310-326) lists Terrain/Terrain2/Object/Object2/Falls/Stream/Quicksand/WaterShrine/Volcano*, and the
    Sea/Beach/River names are commented out (:328-341).
  * The sea animation swaps `mainTexture` on the SHARED asset materials only (WMRenderTextureBank.cs:46-63 load
    `WorldMap/Materials/Sea1..6`; UpdateSea_*_Render sets `<SharedMaterial>.mainTexture`), so a cloned per-cell
    material is never touched by it.
  * Sea1-6 and Terrain all render with the `WorldMap/Terrain` shader (consumption census), whose pixel program is
    `_MainTex x (0.40 + 0.60 x _DetailTex) x vertex light`, then a linear lerp to unity_FogColor; no alpha test.

THE JUDGE: count pixels of three vivid hue classes (one per deployed PNG) in harness frames at fixed poses, A (the
treatment cell, PNGs deployed) against B (the control cell, identical meshes, no PNG), plus the engine's own
receipts in Memoria.log.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
LAB = OUT / "png_lab" / "FF9CustomMap-lab"
PREP_JSON = OUT / "png_prep.json"

# ----------------------------------------------------------------------------------------------- the cells
DONOR = (12, 10)              # the s34 LandDonorPrefab (WMWorld.cs:1210-1211): Terrain, Sea1, Sea3, Sea4, Sea5
CELL_A = (21, 1)              # treatment: IsSea, all 8 neighbours sea, no live override in its 3x3 (session 7's cell)
CELL_B = (0, 13)              # control: same properties, ~800u from A (never in A's frame, nor A in B's)
DISC = 1
# Where the camera is faced (world_face probes walk ~30u and every hold restarts here): 36u west of the 6603 landing.
# The landing (68, -444) itself is NOT clear on every bearing: the 6603 entrance tile (event 1) sits 9-12u out on
# bearings 345-25 and the building footprint (topo 59) 12-14u out on 30-45 -- a probe toward P1 = 45 could re-enter
# the field. FACE_HOME's 40u disc is all area 14 (the safe road), walkable topo, event 0, flat (png_prep.py step 7).
FACE_HOME = (32.37, -448.61)
# The stand point: centroid of donor lawn tri 18 (topo 0, area 13), local (x, z); off the 4u lattice and off every
# shared edge (the LATTICE-EDGE TELEPORT TRAP, RESULTS.md section 5). Ground y is recomputed by png_prep.py.
STAND_LOCAL = (29.516, -27.384)

# What each cell carries in the lab folder. A PNG is deployed for Sea3 WITHOUT a Sea3 mesh on purpose (arm S3).
A_MESHES = ("Terrain", "Sea4")
A_PNGS = ("Terrain", "Sea4", "Sea3")
B_MESHES = ("Terrain", "Sea4")
PNG_COLOR = {"Terrain": (255, 0, 255), "Sea4": (255, 0, 0), "Sea3": (0, 255, 0)}
CLASS_OF = {"Terrain": "magenta", "Sea4": "red", "Sea3": "lime"}

# HSV hue windows (degrees, wrap allowed), minimum saturation, minimum value. Calibrated by png_prep.py:
# false positives over every archived terrain-session frame, and detection under the measured shading + fog.
# First pass (lime 95-145/S.45/V.25, red 345-15/S.45/V.25) hit real content in archived frames: dark grass (H 95-109,
# S <= .58, V <= .40) as lime on 11 frames, browns (H 5-15) as red; the one saturated red was the Southern Ring boat.
CLASSES = {
    "magenta": (275.0, 325.0, 0.40, 0.25),
    "red": (340.0, 4.0, 0.45, 0.40),
    "lime": (100.0, 145.0, 0.62, 0.42),
}

# Pixels around the player sprite are excluded (fractions of W, H). Derived from the calibrated camera model
# (png_prep.py prints the projected actor box; this is it with a >= 40 px margin at 1280x720).
PLAYER_BOX = (0.4375, 0.5625, 0.50, 0.68)


def cell_origin(cell):
    """World (x, z) of a block's local origin: x = 64 bx, z = -64 by; local z runs (-64, 0]."""
    return 64.0 * cell[0], -64.0 * cell[1]


def stand_world(cell, local=STAND_LOCAL):
    ox, oz = cell_origin(cell)
    return round(ox + local[0], 3), round(oz + local[1], 3)


def lab_relpath(cell, part, ext):
    """The mod-folder-relative path both loaders build: TryLoad (.ff9mesh) and TryLoadTexture (.png) share
    `FF9_Data/WorldMap/Disc{d}/0_1/r{y}/Block[x][y] <child>` (WorldMeshOverride.cs:35, :145-146;
    AssetManagerUtil.GetResourcesAssetsPath(true) == "FF9_Data")."""
    x, y = cell
    return f"FF9_Data/WorldMap/Disc{DISC}/0_1/r{y}/Block[{x}][{y}] {part}.{ext}"


# ----------------------------------------------------------------------------------------------- the classifier
def hsv(rgb):
    """uint8 (..., 3) -> (H degrees, S, V) float arrays."""
    a = rgb.astype(np.float32) / 255.0
    mx = a.max(-1)
    mn = a.min(-1)
    d = mx - mn
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    h = np.zeros_like(mx)
    nz = d > 1e-6
    rm = nz & (mx == r)
    gm = nz & (mx == g) & ~rm
    bm = nz & ~rm & ~gm
    h[rm] = ((g - b)[rm] / d[rm]) % 6.0
    h[gm] = (b - r)[gm] / d[gm] + 2.0
    h[bm] = (r - g)[bm] / d[bm] + 4.0
    h *= 60.0
    s = np.where(mx > 0, d / np.maximum(mx, 1e-6), 0.0)
    return h, s, mx


def class_mask(rgb, cls):
    h0, h1, smin, vmin = CLASSES[cls]
    h, s, v = hsv(rgb)
    hm = ((h >= h0) & (h <= h1)) if h0 <= h1 else ((h >= h0) | (h <= h1))
    return hm & (s >= smin) & (v >= vmin)


def keep_mask(w, h, box=PLAYER_BOX):
    keep = np.ones((h, w), bool)
    x0, x1, y0, y1 = int(box[0] * w), int(box[1] * w), int(box[2] * h), int(box[3] * h)
    keep[y0:y1, x0:x1] = False
    return keep


def load_rgb(path):
    from PIL import Image
    return np.asarray(Image.open(path).convert("RGB"))


def frame_counts(path_or_rgb, box=PLAYER_BOX) -> dict:
    """{"w", "h", "n" (scored pixels), "<class>": count, "<class>_frac": count / n} for one frame."""
    rgb = load_rgb(path_or_rgb) if not isinstance(path_or_rgb, np.ndarray) else path_or_rgb
    h, w = rgb.shape[:2]
    keep = keep_mask(w, h, box)
    out = {"w": int(w), "h": int(h), "n": int(keep.sum())}
    for cls in CLASSES:
        c = int((class_mask(rgb, cls) & keep).sum())
        out[cls] = c
        out[cls + "_frac"] = round(c / max(out["n"], 1), 6)
    return out


def noise_px(n: int) -> int:
    """The registered no-effect bound: 0.05% of the scored pixels, at least 200 (460 at 1280x720)."""
    return max(200, int(round(0.0005 * n)))


def gray_change(path_a, path_b, region=None) -> float:
    """Mean absolute gray-level difference between two frames (optionally inside a boolean region)."""
    a = load_rgb(path_a).astype(np.float32).mean(-1)
    b = load_rgb(path_b).astype(np.float32).mean(-1)
    if a.shape != b.shape:
        return float("nan")
    d = np.abs(a - b)
    if region is not None:
        d = d[region]
    return round(float(d.mean()) if d.size else float("nan"), 3)


# ----------------------------------------------------------------------------------------------- receipts
RECEIPT = re.compile(r"\[WorldMeshOverride\] loaded (texture )?'([^']+)' from (.+)$")


def receipts(text: str) -> list[dict]:
    """Every s34 bind receipt in a Memoria.log slice: mesh binds (WorldMeshOverride.cs:47) and texture binds
    (:160). Mesh receipts name the resource path; texture receipts name only the part, so the cell is read from
    the file path."""
    rows = []
    for line in text.splitlines():
        m = RECEIPT.search(line)
        if not m:
            continue
        kind = "texture" if m.group(1) else "mesh"
        src = m.group(3).strip()
        cm = re.search(r"Block\[(\d+)\]\[(\d+)\] (\w+)\.(ff9mesh|png)", src.replace("\\", "/"))
        cell = (int(cm.group(1)), int(cm.group(2))) if cm else None
        part = m.group(2).rsplit(" ", 1)[-1] if kind == "mesh" else m.group(2)
        lab = "ff9custommap-lab" in src.lower()
        rows.append({"kind": kind, "cell": cell, "part": part, "lab": lab, "src": src})
    return rows


def receipt_summary(rows, cells=(CELL_A, CELL_B)) -> dict:
    """{"A": {"mesh": [...parts], "texture": [...]}, "B": {...}} for the two experiment cells only."""
    out = {}
    for tag, cell in zip(("A", "B"), cells):
        out[tag] = {k: [r["part"] for r in rows if r["cell"] == tuple(cell) and r["kind"] == k]
                    for k in ("mesh", "texture")}
    return out


# ----------------------------------------------------------------------------------------------- camera model
# On-foot world camera, place 0 (areas 0-26, 46-50; ff9.cs:81 table, GA2). w_cameraGetPosstat blends the "down"
# posstat 0 and "up" posstat 2 by the actor's height (ff9.cs:3164-3175; w_cameraGetHeightParam ff9.cs:3177-3187:
# t = clamp((256 y + 1000) * 4096 / 4500, 0, 4096)). Raw table ff9.cs:148-... converted to units at ff9.cs:2582-2593.
# fieldOfView = pers / 8 * (Memoria.ini [Worldmap] FieldOfView / 44) (ff9.cs:2676). Eye offset = (sin, cos) x
# distance horizontally, cameraHeight up (ff9.cs:2686-2689); the camera LookAt()s the aim (ff9.cs:2747-2748).
# CALIBRATED by png_prep.py against session 7's `vcap-under.png` (the y=6 plane's known outline): IoU 0.956 with
# only the bearing free and NO FixTypeCam render offset (0.931 with the +558/+312 offsets of ff9.cs:2715-2716).
POSSTAT_DOWN = {"pers": 320.0, "d": 5000 / 256, "eye": 2200 / 256, "aim": 1000 / 256}
POSSTAT_UP = {"pers": 350.0, "d": 5500 / 256, "eye": 2400 / 256, "aim": 500 / 256}
RENDER_EYE, RENDER_AIM = 558 / 256, 312 / 256


def posstat(actor_y: float) -> dict:
    t = min(max((int(actor_y * 256) + 1000) * 4096 // 4500, 0), 4096) / 4096.0
    p = {k: POSSTAT_DOWN[k] + (POSSTAT_UP[k] - POSSTAT_DOWN[k]) * t for k in POSSTAT_DOWN}
    p["t"] = t
    return p


def camera(actor, bearing_deg, *, fov_setting=58.0, render_offsets=False):
    """(eye, aim, vertical fov) for the on-foot camera looking along ``bearing_deg`` (harness convention:
    atan2(dz, dx), 0 = +x east, 90 = +z north) from behind ``actor`` = (x, y, z)."""
    p = posstat(actor[1])
    fov = p["pers"] / 8.0 * (fov_setting / 44.0)
    f2 = np.array([math.cos(math.radians(bearing_deg)), 0.0, math.sin(math.radians(bearing_deg))])
    a = np.asarray(actor, dtype=np.float64)
    eye = a - p["d"] * f2 + np.array([0.0, p["eye"] + (RENDER_EYE if render_offsets else 0.0), 0.0])
    aim = a + np.array([0.0, p["aim"] + (RENDER_AIM if render_offsets else 0.0), 0.0])
    return eye, aim, fov


def ray_dirs(eye, aim, fov, w, h):
    """Unit-ish world ray directions for every pixel centre of a w x h frame (Unity LookAt, y up, no roll)."""
    f = aim - eye
    f = f / np.linalg.norm(f)
    r = np.cross([0.0, 1.0, 0.0], f)
    r = r / np.linalg.norm(r)
    u = np.cross(f, r)
    t = math.tan(math.radians(fov / 2.0))
    xs = (np.arange(w) + 0.5 - w / 2.0) / (h / 2.0) * t
    ys = -(np.arange(h) + 0.5 - h / 2.0) / (h / 2.0) * t
    X, Y = np.meshgrid(xs, ys)
    return f[None, None, :] + X[..., None] * r[None, None, :] + Y[..., None] * u[None, None, :]


def project(points, eye, aim, fov, w, h):
    """World points (N,3) -> pixel (x, y) arrays (pinhole, same frame as ray_dirs)."""
    f = aim - eye
    f = f / np.linalg.norm(f)
    r = np.cross([0.0, 1.0, 0.0], f)
    r = r / np.linalg.norm(r)
    u = np.cross(f, r)
    t = math.tan(math.radians(fov / 2.0))
    p = np.asarray(points, dtype=np.float64) - eye
    z = p @ f
    x = (p @ r) / z / t * (h / 2.0) + w / 2.0
    y = -(p @ u) / z / t * (h / 2.0) + h / 2.0
    return x, y


LABELS = ["sky", "outside", "terrain", "sea1", "sea3", "sea4", "sea5", "hole"]


def render_labels(scene, cell, actor, bearing, *, w=320, h=180, fov_setting=58.0, render_offsets=False,
                  far=400.0):
    """Ray-cast the experiment cell: the donor islet triangles (local coords, shifted to ``cell``), then the
    y = 0 water plane, owned inside the cell by the donor's first-hit sea raster (registration order Sea1, Sea3,
    Sea4, Sea5 -- WMWorld.cs:778-807 -- the same rule landdonor_water.raster_first_hit uses). Returns
    (label index array h x w, ray distance array)."""
    eye, aim, fov = camera(actor, bearing, fov_setting=fov_setting, render_offsets=render_offsets)
    D = ray_dirs(eye, aim, fov, w, h).reshape(-1, 3)
    n = D.shape[0]
    lab = np.zeros(n, np.int32)
    dist = np.full(n, np.inf)
    ox, oz = cell_origin(cell)
    off = np.array([ox, 0.0, oz])
    tris = scene["tris"] + off[None, None, :]
    best = np.full(n, np.inf)
    v0, v1, v2 = tris[:, 0], tris[:, 1], tris[:, 2]
    e1, e2 = v1 - v0, v2 - v0
    for k in range(len(tris)):                       # Moller-Trumbore, both windings
        pv = np.cross(D, e2[k])
        det = pv @ e1[k]
        ok = np.abs(det) > 1e-9
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        tv = eye - v0[k]
        uu = (pv @ tv) * inv
        qv = np.cross(tv, e1[k])
        vv = (D @ qv) * inv
        tt = (qv @ e2[k]) * inv
        hit = ok & (uu >= 0) & (vv >= 0) & (uu + vv <= 1) & (tt > 1e-6) & (tt < best)
        best[hit] = tt[hit]
    islet = np.isfinite(best)
    lab[islet] = LABELS.index("terrain")
    dist[islet] = best[islet] * np.linalg.norm(D[islet], axis=1)
    rest = ~islet
    with np.errstate(divide="ignore", invalid="ignore"):
        s = (0.0 - eye[1]) / D[:, 1]
    P = eye[None, :] + s[:, None] * D
    water = rest & (s > 0)
    dd = s * np.linalg.norm(D, axis=1)
    water &= dd < far
    lab[rest & ~water] = LABELS.index("sky")
    lx, lz = P[:, 0] - ox, P[:, 2] - oz
    inside = water & (lx >= 0) & (lx < 64) & (lz <= 0) & (lz > -64)
    lab[water & ~inside] = LABELS.index("outside")
    dist[water] = dd[water]
    step = scene["raster_step"]
    gi = np.clip((-lz[inside] / step).astype(int), 0, scene["owner"].shape[0] - 1)
    gj = np.clip((lx[inside] / step).astype(int), 0, scene["owner"].shape[1] - 1)
    own = scene["owner"][gi, gj]
    names = scene["owner_names"]
    lab_inside = np.array([LABELS.index(names[o]) if o >= 0 else LABELS.index("hole") for o in own], np.int32)
    lab[inside] = lab_inside
    return lab.reshape(h, w), dist.reshape(h, w)


def fog_b(dist, fit):
    """The fog blend measured on session 7's plane (png_prep.py): b = clip(a0 + a1 * dist, 0, 1)."""
    return np.clip(fit[0] + fit[1] * dist, 0.0, 1.0)


def lower_region(w, h):
    """The lower half of the frame minus the player box: at the stand point it is the cell's water and islet."""
    reg = keep_mask(w, h)
    reg[: h // 2, :] = False
    return reg


# ----------------------------------------------------------------------------------------------- the checks
TOL_Y = 0.15                 # bind proof: published y vs the islet ground (session 4b/7 read to < 0.01)
RED_MIN_FRAC = 0.02          # "the Sea4 PNG renders": >= 2% of the scored frame (projection predicts ~29-30%)
STATIC_MIN_RATIO = 0.95      # red count min/max across the 3 frames of one pose
ANIM_MIN_GRAY = 0.3          # control precondition: B's lower half changes by >= 0.3 gray between frames
MODEL_BAND = (0.5, 1.5)      # secondary: measured red fraction / projected Sea4-detectable fraction


def _shots(rec, pose, cell):
    return ((((rec.get("poses") or {}).get(pose) or {}).get(cell) or {}).get("shots")) or []


def evaluate(rec: dict, prep: dict) -> list[tuple[bool, str, str]]:
    """Every registered check, from a session record (png_session.py) and the prep json. Pure function: the live
    scenario and png_post.py (offline re-scoring of a run directory) call the same code."""
    phase = rec.get("phase", "main")
    png = phase == "main"
    gy = prep["stand_ground"]["y"]
    proj = {p["tag"]: p["projected"] for p in prep["poses"]}
    out: list[tuple[bool, str, str]] = []

    def chk(ok, what, detail=""):
        out.append((bool(ok), what, detail))

    poses = [t for t in ("P1", "P2") if t in (rec.get("poses") or {})]
    # L0 -- both cells bound the override islet (an unbound IsSea cell is open sea: y ~0, or the lawn's 3.2 kept)
    ys = {f"{t}/{c}": (rec["poses"][t].get(c) or {}).get("y") for t in poses for c in ("A", "B")}
    chk(bool(ys) and all(v is not None and abs(v - gy) <= TOL_Y for v in ys.values()),
        f"L0 bind: the actor stands on the verbatim islet at A and B (y {gy} +-{TOL_Y})", str(ys))
    # L1 / R1 -- the engine's receipts, per world load
    for v in rec.get("visits") or []:
        s = v.get("summary") or {}
        a, b = s.get("A") or {}, s.get("B") or {}
        loads = a.get("mesh", []).count("Terrain")
        want_tex = ["Terrain", "Sea4"] * loads if png else []
        lab_ok = all(r.get("lab") for r in v.get("rows", []) if r.get("cell") in (list(CELL_A), list(CELL_B),
                                                                                   tuple(CELL_A), tuple(CELL_B)))
        chk(loads >= 1 and a.get("mesh", []).count("Sea4") == loads and b.get("mesh", []).count("Terrain") == loads
            and b.get("mesh", []).count("Sea4") == loads and lab_ok,
            f"{v['tag']} mesh receipts: A and B each bound Terrain + Sea4 from FF9CustomMap-lab, once per world load",
            json.dumps(s))
        chk(a.get("texture", []) == want_tex,
            f"{v['tag']} texture receipts at A == {['Terrain', 'Sea4'] if png else []} per load "
            f"(TryLoadTexture runs inside a mesh bind only, Terrain registered before Sea4)",
            f"loads {loads}; A texture {a.get('texture')}")
        chk(b.get("texture", []) == [] and all("Sea3" != r.get("part") for r in v.get("rows", [])
                                               if r.get("kind") == "texture"),
            f"{v['tag']} no texture receipt for B, and none for Sea3 anywhere (a PNG with no same-part mesh is "
            f"never opened)", f"B texture {b.get('texture')}")
    # CTRL -- the classifier on the control cell, every frame
    bad = []
    for t in poses:
        for k, sh in enumerate(_shots(rec, t, "B")):
            for cls in CLASSES:
                if sh[cls] > noise_px(sh["n"]):
                    bad.append(f"{t}/B/{k}/{cls}={sh[cls]}")
    chk(bool(poses) and not bad, "CTRL: control cell B shows no vivid class above the noise bound in any frame",
        ", ".join(bad) or "all <= noise")
    # T1, S3, S4 -- A against B, frame by frame
    for t in poses:
        A, B = _shots(rec, t, "A"), _shots(rec, t, "B")
        n = min(len(A), len(B))
        if n == 0:
            chk(False, f"{t}: frames for both cells", f"A {len(A)} B {len(B)}")
            continue
        mg = [(A[k]["magenta"], B[k]["magenta"], noise_px(A[k]["n"])) for k in range(n)]
        chk(all(a <= b + nz for a, b, nz in mg),
            f"T1 {t}: Terrain PNG NOT rendered at A (magenta A <= B + noise; the islet is "
            f"{proj[t]['terrain']:.1%} of the frame if it were)", str(mg))
        lm = [(A[k]["lime"], B[k]["lime"], noise_px(A[k]["n"])) for k in range(n)]
        chk(all(a <= b + nz for a, b, nz in lm),
            f"S3 {t}: Sea3 PNG (no Sea3 mesh) NOT rendered at A (lime A <= B + noise; Sea3 is "
            f"{proj[t]['Sea3_detectable']:.1%} detectable if it were)", str(lm))
        rd = [(A[k]["red_frac"], B[k]["red"], noise_px(B[k]["n"])) for k in range(n)]
        if png:
            chk(all(fa >= RED_MIN_FRAC and b <= nz for fa, b, nz in rd),
                f"S4 {t}: Sea4 PNG rendered at A (red >= {RED_MIN_FRAC:.0%} of the frame in every frame; B <= noise)",
                str(rd))
            ratio = sum(fa for fa, _b, _n in rd) / n / max(proj[t]["Sea4_detectable"], 1e-9)
            chk(MODEL_BAND[0] <= ratio <= MODEL_BAND[1],
                f"S4m {t} (secondary, model): red fraction / projected Sea4-detectable "
                f"{proj[t]['Sea4_detectable']:.3f} within {MODEL_BAND}", f"ratio {ratio:.3f}")
            reds = [A[k]["red"] for k in range(n)]
            anim = (rec["poses"][t].get("B") or {}).get("gray_change") or []
            chk(max(anim or [0]) >= ANIM_MIN_GRAY,
                f"ANIM {t} (precondition): the stock sea animates across B's frames (lower-half change >= "
                f"{ANIM_MIN_GRAY})", str(anim))
            chk(min(reds) / max(max(reds), 1) >= STATIC_MIN_RATIO,
                f"S4s {t}: the Sea4 PNG stays on across the sea animation (red min/max >= {STATIC_MIN_RATIO})",
                str(reds))
        else:
            chk(all(A[k]["red"] <= B[k]["red"] + noise_px(A[k]["n"]) for k in range(n)),
                f"S4-nopng {t}: no PNG deployed -> no red at A", str(rd))
    rl = rec.get("reload") or {}
    if rl.get("shots"):
        fr = [sh["red_frac"] for sh in rl["shots"]]
        yok = rl.get("y") is not None and abs(rl["y"] - gy) <= TOL_Y
        chk(yok and (all(f >= RED_MIN_FRAC for f in fr) if png else all(sh["red"] <= noise_px(sh["n"])
                                                                         for sh in rl["shots"])),
            "R1: after a world reload A is the islet again and the Sea4 PNG is read again and renders (P1)",
            f"y {rl.get('y')} red {fr}")
    return out
