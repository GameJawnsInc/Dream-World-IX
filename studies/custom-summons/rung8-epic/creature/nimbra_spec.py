"""NIMBRA -- the rung-8 creature: mesh + rig + atlas, authored from nothing.

Binding contract: ``studies/custom-summons/rung8-epic/STORYBOARD.md`` sections 1.2-1.6. This module is
PURE (stdlib + PIL/numpy for the atlas only, no bpy, no engine reads) so it can be imported by the
build driver, the clip authoring lane, AND the headless-Blender offline eye alike.

MODEL SPACE (the engine's, per ``examples/boletta/make_creature.py``):
  * **Y-DOWN** -- ground at y = 0, the crown at the most-NEGATIVE y (NIMBRA's crown = -1400).
  * FF9 units, left-handed like Unity. The struct's verts are what ``emit_skinned_fbx`` writes
    VERBATIM into the FBX ``Vertices`` array, and ``ModelImporter`` reads THAT verbatim -- so the
    numbers here are literally the in-game units (the m1b "raw units" law, arrived at by
    construction rather than by a x100 Blender bake).
  * Texture v = 0 is the image BOTTOM (Unity). :func:`page_uv` does that flip once, centrally, so
    no call site can repeat the boletta upside-down-face bug.
  * Triangle winding is CALIBRATED, never assumed (``make_nimbra.calibrate_winding``). Every
    triangle here is emitted through :func:`_Builder.tri` with an explicit OUTWARD hint, so the
    canonical mesh is provably outward-wound before the calibrated flip is applied.

WHY ONE MERGED MESH (STORYBOARD 1.4): a standalone renderer can be one-shot disabled by a
character-show pass (the Garnet-scrunchie lesson), and one mesh keeps ``SFXDataMesh``'s per-
ModelSequence ``Key``/``HideMeshes`` machinery entirely out of play -- exactly right for a creature
that is never partially hidden.

THE PALETTE IS AUTHORED DARK ON PURPOSE (STORYBOARD 1.5 / rung-7 residual b): an SFX-instantiated
model keeps its FBX material state -- there is NO battle-actor lighting or tint pass -- so NIMBRA
renders at full texture brightness against a blacked-out arena with zero attenuation. Every colour
below is the storyboard hex multiplied by :data:`DARKEN`.
"""
from __future__ import annotations

import math

GEO_NAME, GEO_ID = "GEO_MON_B0_M400", 6400      # STORYBOARD 6.4; mint band >= 6000, token M400
ATLAS = 256                                     # one 256x256 page for the whole creature

# --------------------------------------------------------------------------- palette (STORYBOARD 1.5)

DARKEN = 0.85                                   # "author ~15% darker than you want" -- no lighting pass


def _hex(h: str, k: float = DARKEN):
    h = h.lstrip("#")
    return tuple(max(0, min(255, int(round(int(h[i:i + 2], 16) * k)))) for i in (0, 2, 4))


BASE = _hex("8FA79B")       # body base   -- cowl, core, arms
HI = _hex("C7D6CE")         # highlight   -- mask face, cowl crest, arm leading edges
DEEP = _hex("3A4A46")       # deep        -- mask underside, cowl interior, veil roots
VEIL_TIP = _hex("2E3A38")   # the veil gradient's far end
ACCENT = _hex("C8912E")     # THE ONE WARM BEAT -- eye hollows + the mask rim ring. Nowhere else.
VOID = _hex("11 1614".replace(" ", ""))   # the hollow behind the cowl / behind the mask

# --------------------------------------------------------------------------- atlas pages (pixel rects)
# (x0, y0, x1, y1) with y0 = the TOP row. page_uv() performs the single Unity v-flip.
PAGES = {
    "mask": (4, 4, 124, 124),      # the oval face, painted planar -- the eyes land where the UV says
    "cowl": (132, 4, 252, 68),     # crest-to-hem gradient
    "arms": (132, 76, 252, 124),   # leading-edge highlight -> deep trailing edge
    "core": (132, 132, 252, 196),  # column shading
    "veil": (4, 132, 124, 252),    # BASE -> VEIL_TIP vertical gradient with mist striations
    "void": (200, 204, 252, 252),  # flat near-black: mask back, cowl interior
}


def page_uv(page: str, s: float, t: float) -> tuple:
    """(s, t) in [0,1]^2 with **t = 0 at the page TOP** -> struct (u, v) with v = 0 at the image BOTTOM.

    The whole model's texture orientation funnels through this one function; get it right here and
    the boletta "smile above the eyes" bug is structurally unreachable."""
    x0, y0, x1, y1 = PAGES[page]
    px = x0 + max(0.0, min(1.0, s)) * (x1 - x0)
    py = y0 + max(0.0, min(1.0, t)) * (y1 - y0)
    return (px / ATLAS, 1.0 - py / ATLAS)


# --------------------------------------------------------------------------- the rig (STORYBOARD 1.6)
# 14 bones, authored at REST with IDENTITY rotations -- the clips do all the posing. Positions below
# are WORLD (Y-down); build_bones() converts to the parent-local offsets the FBX carries.
BONE_WORLD = [
    ("bone000", None,      (0.0, -740.0, 0.0)),      # root / core base
    ("bone001", "bone000", (0.0, -910.0, 0.0)),      # spine
    ("bone002", "bone001", (0.0, -1080.0, 0.0)),     # chest
    ("bone003", "bone002", (0.0, -1170.0, 0.0)),     # neck (no geometry -- the mask FLOATS clear)
    ("bone004", "bone003", (0.0, -1305.0, 0.0)),     # mask
    ("bone005", "bone002", (-218.0, -1050.0, 28.0)),  # shoulder L (at the yoke's outer corner)
    ("bone006", "bone002", (218.0, -1050.0, 28.0)),   # shoulder R
    ("bone007", "bone005", (-240.0, -800.0, 16.0)),   # forearm L
    ("bone008", "bone006", (240.0, -800.0, 16.0)),    # forearm R
    ("bone009", "bone007", (-252.0, -470.0, -8.0)),   # point L
    ("bone010", "bone008", (252.0, -470.0, -8.0)),    # point R
    ("bone011", "bone000", (62.0, -430.0, 62.0)),    # veil A  (ribbon 0, az 45)
    ("bone012", "bone000", (62.0, -430.0, -62.0)),   # veil B  (ribbon 1, az 135)
    ("bone013", "bone000", (-62.0, -430.0, -62.0)),  # veil C  (ribbon 2, az 225)
    #                                                  ribbon 3 (az 315) rides a bone000/bone011 BLEND
    #                                                  so the fray never reads as rigid (STORYBOARD 1.6)
]
BONE_NUM = {name: i for i, (name, _p, _w) in enumerate(BONE_WORLD)}


def build_bones() -> list:
    """The kit Model-struct ``bones`` list: parent-local pos, identity rot, unit scale."""
    world = {n: w for (n, _p, w) in BONE_WORLD}
    out = []
    for name, parent, w in BONE_WORLD:
        if parent is None:
            local = w
        else:
            pw = world[parent]
            local = (w[0] - pw[0], w[1] - pw[1], w[2] - pw[2])
        out.append({"name": name, "parent": parent, "pos": local,
                    "rot": (0.0, 0.0, 0.0, 1.0), "scale": (1.0, 1.0, 1.0)})
    return out


# --------------------------------------------------------------------------- small vector helpers

def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(v):
    n = math.sqrt(_dot(v, v)) or 1.0
    return (v[0] / n, v[1] / n, v[2] / n)


def _lerp(a, b, t):
    return a + (b - a) * t


def _smooth(t):
    """smoothstep on [0,1] -- the taper/blend easing used throughout."""
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def frame_at(tangent, ref=(0.0, 0.0, 1.0)):
    """A stable (W, H, T) frame for a swept cross-section, handed so that W x H == -T.

    That is the SAME handedness a plain Y-down cylinder has (X x Z == -Y with travel +Y), which is
    what makes the shared band/cap winding below come out OUTWARD for tubes, arms and ribbons alike.
    """
    T = _norm(tangent)
    if abs(_dot(T, ref)) > 0.95:                 # tangent ~ parallel to the reference: pick another
        ref = (0.0, 1.0, 0.0) if abs(_dot(T, (0.0, 1.0, 0.0))) < 0.95 else (1.0, 0.0, 0.0)
    W = _norm(_cross(T, ref))
    H = _norm(_cross(W, T))
    return W, H, T


# --------------------------------------------------------------------------- the builder

class _Builder:
    """Accumulates verts/uvs/weights/tris. Normals are ACCUMULATED from the (canonically outward)
    face normals, so a smooth-shaded surface falls out for free and no call site hand-derives one."""

    def __init__(self):
        self.V, self.UV, self.W, self.T = [], [], [], []
        self._n = []            # per-vertex accumulated face normal
        self.parts = {}         # part name -> (vert_start, vert_end, tri_start, tri_end)

    # -- vertices -------------------------------------------------------
    def v(self, pos, uv, weights):
        self.V.append((float(pos[0]), float(pos[1]), float(pos[2])))
        self.UV.append((float(uv[0]), float(uv[1])))
        self.W.append([(int(b), float(w)) for b, w in weights if w > 1e-4])
        self._n.append([0.0, 0.0, 0.0])
        return len(self.V) - 1

    # -- triangles ------------------------------------------------------
    def tri(self, a, b, c, out_hint):
        """Append triangle (a,b,c), SWAPPING b/c if its geometric normal opposes ``out_hint``.

        Every face in the model is oriented against an explicit outward direction -- no winding is
        ever inferred from an index pattern, so a copy-pasted band can't silently invert a part."""
        p0, p1, p2 = self.V[a], self.V[b], self.V[c]
        n = _cross(_sub(p1, p0), _sub(p2, p0))
        if _dot(n, out_hint) < 0.0:
            b, c = c, b
            n = (-n[0], -n[1], -n[2])
        self.T.append((a, b, c))
        for i in (a, b, c):                      # area-weighted accumulation (n is un-normalized)
            self._n[i][0] += n[0]
            self._n[i][1] += n[1]
            self._n[i][2] += n[2]

    def band(self, low, high, hints, closed=True):
        """Bridge two rings of equal length. ``low`` is the row at LARGER y (nearer the ground in
        Y-down space); ``hints[s]`` is the outward direction at column s."""
        n = len(low)
        rng = range(n) if closed else range(n - 1)
        for s in rng:
            s2 = (s + 1) % n
            h = hints[s]
            self.tri(low[s], high[s], high[s2], h)
            self.tri(low[s], high[s2], low[s2], h)

    def fan(self, ring, apex, out_hint, closed=True):
        n = len(ring)
        rng = range(n) if closed else range(n - 1)
        for s in rng:
            self.tri(ring[s], apex, ring[(s + 1) % n], out_hint)

    def quad(self, a, b, c, d, out_hint):
        self.tri(a, b, c, out_hint)
        self.tri(a, c, d, out_hint)

    # -- bookkeeping ----------------------------------------------------
    def mark(self, name, v0, t0):
        self.parts[name] = (v0, len(self.V), t0, len(self.T))

    def normals(self):
        out = []
        for n in self._n:
            ln = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2) or 1.0
            out.append((n[0] / ln, n[1] / ln, n[2] / ln))
        return out


# --------------------------------------------------------------------------- part 1: THE MASK
# A smooth pale oval PLATE, slightly CONCAVE, floating a clear gap above the cowl. No carved features
# except two shallow amber eye-hollows -- the dominant silhouette read (STORYBOARD 1.2).

MASK_C = (0.0, -1305.0, 0.0)      # centre; the plate spans y -1400 (crown) .. -1210
MASK_HW, MASK_HH = 70.0, 95.0     # 140 wide x 190 tall
MASK_FRONT_Z, MASK_BACK_Z = -16.0, -40.0   # dish depth toward +Z / bulge away -- 40 deep overall
MASK_SEG = 12
MASK_FRONT_RINGS = (0.40, 0.74, 1.0)   # the read side gets the extra ring
MASK_BACK_RINGS = (0.55, 0.97)         # the back is never lit and never seen -- keep it cheap


def _mask(B):
    v0, t0 = len(B.V), len(B.T)
    cx, cy, cz = MASK_C
    W = [(BONE_NUM["bone004"], 1.0)]

    def surf(fr, s, z_at, page, uvfn):
        """One ring of the plate at radial fraction ``fr``."""
        row = []
        for k in range(MASK_SEG):
            az = 2.0 * math.pi * k / MASK_SEG
            ex, ey = math.sin(az) * fr, math.cos(az) * fr
            p = (cx + ex * MASK_HW, cy + ey * MASK_HH, cz + z_at(fr))
            row.append(B.v(p, uvfn(ex, ey), W))
        return row

    # planar UV: the painted eyes + rim ring land exactly where the geometry puts them
    def uv_front(ex, ey):
        return page_uv("mask", 0.5 + 0.5 * ex, 0.5 + 0.5 * ey)

    def uv_back(ex, ey):
        return page_uv("void", 0.5 + 0.35 * ex, 0.5 + 0.35 * ey)

    front_c = B.v((cx, cy, cz + MASK_FRONT_Z), uv_front(0.0, 0.0), W)
    front = [surf(fr, MASK_SEG, lambda r: MASK_FRONT_Z * (1.0 - r * r), "mask", uv_front)
             for fr in MASK_FRONT_RINGS]
    back_c = B.v((cx, cy, cz + MASK_BACK_Z), uv_back(0.0, 0.0), W)
    back = [surf(fr, MASK_SEG, lambda r: MASK_BACK_Z * (1.0 - r * r), "void", uv_back)
            for fr in MASK_BACK_RINGS]

    B.fan(front[0], front_c, (0.0, 0.0, 1.0))
    for j in range(len(front) - 1):
        hints = [(math.sin(2 * math.pi * k / MASK_SEG) * 0.35,
                  math.cos(2 * math.pi * k / MASK_SEG) * 0.35, 1.0) for k in range(MASK_SEG)]
        B.band(front[j + 1], front[j], hints)          # inner ring is "high" (nearer the dish centre)
    B.fan(back[0], back_c, (0.0, 0.0, -1.0))
    for j in range(len(back) - 1):
        hints = [(math.sin(2 * math.pi * k / MASK_SEG) * 0.35,
                  math.cos(2 * math.pi * k / MASK_SEG) * 0.35, -1.0) for k in range(MASK_SEG)]
        B.band(back[j], back[j + 1], hints)
    # the rim: bridge the outer front ring to the outer back ring, normals purely radial
    hints = [(math.sin(2 * math.pi * k / MASK_SEG), math.cos(2 * math.pi * k / MASK_SEG), 0.0)
             for k in range(MASK_SEG)]
    B.band(back[-1], front[-1], hints)
    B.mark("mask", v0, t0)


# --------------------------------------------------------------------------- part 2: THE COWL
# "A hunched, hollow shoulder yoke. Suggests a body that isn't there. Reads as 'cloaked' at
# silhouette." (STORYBOARD 1.2, and its ASCII: the yoke's outline flares DOWN and OUT while the core
# column shows THROUGH the opening.) So the cowl is an OPEN CAPE, not a closed bell -- an arc of ~292
# degrees around the back with a gap at the FRONT, two skins (outer + lining) welded along the hem and
# both free edges. That gap is what makes it read as hollow and lets the core column be seen at all;
# the first draft closed the revolution and rendered as a mushroom cap with the whole torso hidden.

# SHORT AND WIDE, per the ASCII: the yoke is only its own two rows (`___/   \___` over
# `/___________\`) and the ARMS take over the outline below it. The storyboard TABLE's "300 tall" was
# tried first as a full-length cape and it swallowed the core column AND the arms whole -- the second
# offline-eye pass showed a mushroom with two detached cones beside it. Front collar -1160 to hem -985
# is 175; the hunched BACK collar rides to -1232, so the yoke's overall vertical extent is 247.
COWL_TOP, COWL_BOT = -1160.0, -985.0
COWL_HUNCH = 72.0                        # the BACK collar rises BEHIND the mask -- that IS the hunch
# The front opening WIDENS with height: a constant-angle slit reads as a slot cut in a bucket, a
# widening one reads as two panels hanging apart. (az is measured from +Z = dead front.)
COWL_OPEN_TOP, COWL_OPEN_HEM = math.radians(17.0), math.radians(46.0)
COWL_SEG = 18                            # columns across the open arc (SEG+1 verts per row)
COWL_RAG = 17.0                          # how far the hem waves up/down per column -- a decayed edge
# (t, half-width X, half-depth Z, centre Z) -- flares FAST to the shoulder, then holds
COWL_PROFILE = [
    (0.00, 100.0, 80.0, -8.0),
    (0.35, 196.0, 140.0, -18.0),
    (0.72, 240.0, 172.0, -28.0),
    (1.00, 252.0, 182.0, -34.0),
]


def _cowl_ring(t):
    for i in range(len(COWL_PROFILE) - 1):
        t0, *_a = COWL_PROFILE[i]
        t1, *_b = COWL_PROFILE[i + 1]
        if t0 <= t <= t1:
            f = _smooth((t - t0) / (t1 - t0)) if t1 > t0 else 0.0
            return (_lerp(_a[0], _b[0], f), _lerp(_a[1], _b[1], f), _lerp(_a[2], _b[2], f))
    return tuple(COWL_PROFILE[-1][1:])


def _cowl_az(k, t):
    """Column k at height t -> azimuth, sweeping the LONG way round the back (az 0 = the open front)."""
    op = _lerp(COWL_OPEN_TOP, COWL_OPEN_HEM, _smooth(t))
    return op + (2.0 * math.pi - 2.0 * op) * (k / COWL_SEG)


def _cowl_y(t, az, k):
    """The collar rides higher at the BACK -- that lift IS the hunch. The hem frays."""
    top = COWL_TOP - COWL_HUNCH * (0.5 - 0.5 * math.cos(az))
    rag = COWL_RAG * math.sin(4.7 * k / COWL_SEG * 2.0 * math.pi + 0.9) * _smooth(t) ** 2
    return _lerp(top, COWL_BOT, t) + rag


def _cowl(B):
    v0, t0 = len(B.V), len(B.T)
    ROWS = 7

    def wt(t):
        f = _smooth((t - 0.30) / 0.70)
        return [(BONE_NUM["bone002"], 1.0 - 0.42 * f), (BONE_NUM["bone001"], 0.42 * f)]

    def shell(scale, page, lining):
        rows, hints = [], []
        for r in range(ROWS):
            t = r / (ROWS - 1)
            rx, rz, zc = _cowl_ring(t)
            rx, rz = rx * scale, rz * scale
            row, hs = [], []
            for k in range(COWL_SEG + 1):
                az = _cowl_az(k, t)
                sx, cz_ = math.sin(az), math.cos(az)
                p = (sx * rx, _cowl_y(t, az, k), zc + cz_ * rz)
                s = k / COWL_SEG
                uv = (page_uv(page, 0.5 + 0.42 * (s - 0.5), 0.5 + 0.40 * (t - 0.5)) if lining
                      else page_uv(page, 0.03 + 0.94 * s, 0.05 + 0.90 * t))
                B.v(p, uv, wt(t))
                row.append(len(B.V) - 1)
                n = _norm((sx / rx, -0.26 * (1.0 - t), cz_ / rz))
                hs.append((-n[0], -n[1], -n[2]) if lining else n)
            rows.append(row)
            hints.append(hs)
        for r in range(ROWS - 1):
            if lining:                                  # lining faces INWARD -> reverse the bridge
                B.band(rows[r], rows[r + 1], hints[r], closed=False)
            else:
                B.band(rows[r + 1], rows[r], hints[r], closed=False)
        return rows

    outer = shell(1.00, "cowl", False)
    inner = shell(0.86, "void", True)

    # weld the hem (looking down, outward normal +Y) and the collar rim (outward -Y)
    for k in range(COWL_SEG):
        B.quad(outer[-1][k], outer[-1][k + 1], inner[-1][k + 1], inner[-1][k], (0.0, 1.0, 0.0))
        B.quad(inner[0][k], inner[0][k + 1], outer[0][k + 1], outer[0][k], (0.0, -1.0, 0.0))
    # weld the two FREE EDGES of the opening (the cape's front hems)
    for r in range(ROWS - 1):
        tt = r / (ROWS - 1)
        az0, az1 = _cowl_az(0, tt), _cowl_az(COWL_SEG, tt)
        e0 = (math.cos(az0), 0.0, -math.sin(az0))       # tangential, pointing out of the gap
        e1 = (-math.cos(az1), 0.0, math.sin(az1))
        B.quad(outer[r][0], inner[r][0], inner[r + 1][0], outer[r + 1][0], e0)
        B.quad(outer[r][COWL_SEG], outer[r + 1][COWL_SEG],
               inner[r + 1][COWL_SEG], inner[r][COWL_SEG], e1)
    B.mark("cowl", v0, t0)


# --------------------------------------------------------------------------- part 3: THE ARMS
# Long, thin, tapering to POINTS. No hands, no fingers. They hang; they do not gesture until the
# strike (STORYBOARD 1.2). 620 long, 55 -> 8 taper.

ARM_SEG, ARM_ROWS = 8, 22
ARM_KNOTS = [                                   # (t, |x|, y, z) -- the hang line, slightly bowed
    (0.00, 218.0, -1035.0, 28.0),               # the shoulder bulges out of the yoke's outer corner
    (0.35, 236.0, -862.0, 20.0),
    (0.70, 246.0, -660.0, 6.0),
    (1.00, 252.0, -470.0, -8.0),                # ...and lands level with the yoke's own widest point
]
ARM_BONES = {-1.0: ("bone005", "bone007", "bone009"), 1.0: ("bone006", "bone008", "bone010")}


def _arm_point(side, t):
    for i in range(len(ARM_KNOTS) - 1):
        t0, *a = ARM_KNOTS[i]
        t1, *b = ARM_KNOTS[i + 1]
        if t0 <= t <= t1:
            f = _smooth((t - t0) / (t1 - t0)) if t1 > t0 else 0.0
            return (side * _lerp(a[0], b[0], f), _lerp(a[1], b[1], f), _lerp(a[2], b[2], f))
    x, y, z = ARM_KNOTS[-1][1:]
    return (side * x, y, z)


def _arm_weights(side, t):
    """shoulder -> forearm -> point, PLUS a chest anchor on the topmost rows.

    Without that anchor the arm is rigid from its very first ring, so any shoulder rotation (the
    strike's 47-degree wind-back) tears a visible hole between the yoke's corner and the limb -- the
    fourth offline-eye pass caught exactly that. Bleeding bone002 into t < 0.22 sews the shoulder to
    the cloth and lets the rest of the arm swing freely."""
    sh, fa, pt = ARM_BONES[side]
    if t < 0.22:
        f = _smooth(t / 0.22)
        return [(BONE_NUM["bone002"], 0.78 * (1.0 - f)), (BONE_NUM[sh], 1.0 - 0.78 * (1.0 - f))]
    if t < 0.58:
        f = _smooth((t - 0.22) / 0.36)
        return [(BONE_NUM[sh], 1.0 - f), (BONE_NUM[fa], f)]
    f = _smooth((t - 0.58) / 0.42)
    return [(BONE_NUM[fa], 1.0 - f), (BONE_NUM[pt], f)]


def _arm(B, side):
    v0, t0 = len(B.V), len(B.T)
    rows, hints = [], []
    for r in range(ARM_ROWS):
        t = r / (ARM_ROWS - 1)
        c = _arm_point(side, t)
        nxt = _arm_point(side, min(1.0, t + 1e-3))
        prv = _arm_point(side, max(0.0, t - 1e-3))
        Wv, Hv, _T = frame_at(_sub(nxt, prv))
        # taper HARD: "long, thin, tapering to POINTS" -- a slow taper made them read as tentacles,
        # indistinguishable from the veil ribbons in the first offline-eye pass.
        rad = 8.0 + 47.0 * (1.0 - t) ** 1.55
        wts = _arm_weights(side, t)
        row, hs = [], []
        for k in range(ARM_SEG):
            az = 2.0 * math.pi * k / ARM_SEG
            d = (Wv[0] * math.sin(az) + Hv[0] * math.cos(az),
                 Wv[1] * math.sin(az) + Hv[1] * math.cos(az),
                 Wv[2] * math.sin(az) + Hv[2] * math.cos(az))
            p = (c[0] + d[0] * rad, c[1] + d[1] * rad, c[2] + d[2] * rad)
            # leading edge (facing +Z, the party side) takes the highlight; trailing edge deep
            lead = 0.5 + 0.5 * d[2]
            B.v(p, page_uv("arms", 0.04 + 0.92 * lead, 0.05 + 0.9 * t), wts)
            row.append(len(B.V) - 1)
            hs.append(d)
        rows.append(row)
        hints.append(hs)
    for r in range(ARM_ROWS - 1):
        B.band(rows[r + 1], rows[r], hints[r])          # r+1 is nearer the ground (larger y)
    tip_c = _arm_point(side, 1.0)
    tip = B.v((tip_c[0], tip_c[1] + 34.0, tip_c[2]), page_uv("arms", 0.5, 0.99),
              _arm_weights(side, 1.0))
    B.fan(rows[-1], tip, (0.0, 1.0, 0.0))
    # CAP THE SHOULDER END. The tube's top ring is a hole, and the shoulder pokes out of the yoke's
    # outer corner far enough to show it -- the third offline-eye pass caught an open cone there.
    top_c = _arm_point(side, 0.0)
    top = B.v((top_c[0], top_c[1] - 26.0, top_c[2]), page_uv("arms", 0.5, 0.02),
              _arm_weights(side, 0.0))
    B.fan(rows[0], top, (0.0, -1.0, 0.0))
    B.mark(f"arm{'L' if side < 0 else 'R'}", v0, t0)


# --------------------------------------------------------------------------- part 4: THE CORE
# A narrowing torso column. No waist, no hips. y -1080 -> -740, radius 105 -> 45.

CORE_SEG, CORE_ROWS = 14, 12
# The top is raised to -1140 (from the storyboard table's -1080) so the column rises THROUGH the
# yoke's collar and is a long clean read below the hem -- STORYBOARD 1.2's ASCII shows the core as a
# continuous `|` from the yoke all the way down to the veil. Taper unchanged (224 -> 90 dia).
CORE_TOP, CORE_BOT = -1140.0, -740.0


def _core(B):
    v0, t0 = len(B.V), len(B.T)
    rows, hints = [], []
    for r in range(CORE_ROWS):
        t = r / (CORE_ROWS - 1)
        y = _lerp(CORE_TOP, CORE_BOT, t)
        rad = _lerp(96.0, 38.0, _smooth(t)) * (1.0 + 0.06 * math.sin(t * 5.0))
        f = _smooth(t)
        wts = [(BONE_NUM["bone002"], max(0.0, 1.0 - 2.0 * f)),
               (BONE_NUM["bone001"], 1.0 - abs(1.0 - 2.0 * f)),
               (BONE_NUM["bone000"], max(0.0, 2.0 * f - 1.0))]
        row, hs = [], []
        for k in range(CORE_SEG):
            az = 2.0 * math.pi * k / CORE_SEG
            sx, cz_ = math.sin(az), math.cos(az)
            B.v((sx * rad, y, cz_ * rad),
                page_uv("core", 0.03 + 0.94 * (k / CORE_SEG), 0.04 + 0.92 * t), wts)
            row.append(len(B.V) - 1)
            hs.append((sx, 0.0, cz_))
        rows.append(row)
        hints.append(hs)
    for r in range(CORE_ROWS - 1):
        B.band(rows[r + 1], rows[r], hints[r])
    apex = B.v((0.0, CORE_TOP - 30.0, 0.0), page_uv("core", 0.5, 0.02),
               [(BONE_NUM["bone002"], 1.0)])
    B.fan(rows[0], apex, (0.0, -1.0, 0.0))
    B.mark("core", v0, t0)


# --------------------------------------------------------------------------- part 5: THE VEIL
# NO LEGS. The core frays into 4 tapering ribbons that hang and sway -- 45% of total height, the
# secondary silhouette read, and the reason NIMBRA reads correctly over a blacked-out floor.

VEIL_SEG, VEIL_ROWS, VEIL_N = 8, 26, 4
VEIL_TOP, VEIL_BOT = -760.0, -20.0             # 740 long
VEIL_BONE = {0: "bone011", 1: "bone012", 2: "bone013"}   # ribbon 3 -> bone000/bone011 blend


def _ribbon_point(i, t):
    """The hanging line of ribbon ``i`` at parameter t (0 = root, 1 = frayed tip)."""
    phase = i * math.pi * 0.5
    az = math.radians(45.0 + 90.0 * i) + math.radians(13.0) * math.sin(2.4 * math.pi * t + phase)
    R = 46.0 + 66.0 * t ** 1.35
    y = _lerp(VEIL_TOP, VEIL_BOT, t)
    x = math.sin(az) * R + 11.0 * math.sin(3.1 * math.pi * t + phase)
    z = math.cos(az) * R + 11.0 * math.cos(2.7 * math.pi * t + phase)
    return (x, y, z)


def _ribbon_weights(i, t):
    f = _smooth(t)
    if i in VEIL_BONE:
        return [(BONE_NUM["bone000"], 1.0 - 0.88 * f), (BONE_NUM[VEIL_BONE[i]], 0.88 * f)]
    # ribbon D: a bone000/bone011 BLEND, so the fray never reads as rigid (STORYBOARD 1.6)
    return [(BONE_NUM["bone000"], 1.0 - 0.55 * f), (BONE_NUM["bone011"], 0.55 * f)]


def _ribbon(B, i):
    v0, t0 = len(B.V), len(B.T)
    rows, hints = [], []
    for r in range(VEIL_ROWS):
        t = r / (VEIL_ROWS - 1)
        c = _ribbon_point(i, t)
        Wv, Hv, _T = frame_at(_sub(_ribbon_point(i, min(1.0, t + 1e-3)),
                                   _ribbon_point(i, max(0.0, t - 1e-3))))
        hw = 45.0 * (1.0 - t) ** 0.85 + 3.0            # width  90 -> 6
        hh = 14.0 * (1.0 - t) ** 0.90 + 1.5            # a flattened section, not a tube
        wts = _ribbon_weights(i, t)
        row, hs = [], []
        for k in range(VEIL_SEG):
            az = 2.0 * math.pi * k / VEIL_SEG
            sa, ca = math.sin(az), math.cos(az)
            d = (Wv[0] * sa * hw + Hv[0] * ca * hh,
                 Wv[1] * sa * hw + Hv[1] * ca * hh,
                 Wv[2] * sa * hw + Hv[2] * ca * hh)
            B.v((c[0] + d[0], c[1] + d[1], c[2] + d[2]),
                page_uv("veil", 0.04 + 0.92 * (0.5 + 0.5 * sa), 0.02 + 0.96 * t), wts)
            row.append(len(B.V) - 1)
            hs.append(_norm((Wv[0] * sa / hw + Hv[0] * ca / hh,
                             Wv[1] * sa / hw + Hv[1] * ca / hh,
                             Wv[2] * sa / hw + Hv[2] * ca / hh)))
        rows.append(row)
        hints.append(hs)
    for r in range(VEIL_ROWS - 1):
        B.band(rows[r + 1], rows[r], hints[r])
    tip_c = _ribbon_point(i, 1.0)
    tip = B.v((tip_c[0], tip_c[1] + 22.0, tip_c[2]), page_uv("veil", 0.5, 0.995),
              _ribbon_weights(i, 1.0))
    B.fan(rows[-1], tip, (0.0, 1.0, 0.0))
    # cap the root too: it sits just outside the core's 45u waist, so its upward-facing hole IS
    # reachable from a battle camera that looks slightly down
    root_c = _ribbon_point(i, 0.0)
    root = B.v((root_c[0], root_c[1] - 16.0, root_c[2]), page_uv("veil", 0.5, 0.01),
               _ribbon_weights(i, 0.0))
    B.fan(rows[0], root, (0.0, -1.0, 0.0))
    B.mark(f"veil{i}", v0, t0)


# --------------------------------------------------------------------------- assembly

def build_model(wind: int = 1) -> dict:
    """The complete kit Model struct. ``wind`` comes from ``make_nimbra.calibrate_winding``:
    +1 keeps the canonical (outward) order, -1 mirrors every triangle."""
    B = _Builder()
    _mask(B)
    _cowl(B)
    _arm(B, -1.0)
    _arm(B, 1.0)
    _core(B)
    for i in range(VEIL_N):
        _ribbon(B, i)

    # normalize weights (smooth weights are fine for our OWN creature; the engine blends them)
    W = []
    for infl in B.W:
        tot = sum(w for _b, w in infl) or 1.0
        W.append([(b, w / tot) for b, w in sorted(infl, key=lambda p: -p[1])[:4]])

    tris = [(a, b, c) if wind > 0 else (a, c, b) for (a, b, c) in B.T]
    return {
        "geo": GEO_NAME, "geo_id": GEO_ID, "type_int": 4, "root_bone": "bone000",
        "bones": build_bones(),
        "meshes": [{"name": "nimbra", "verts": B.V, "normals": B.normals(), "uvs": B.UV,
                    "submeshes": [{"tris": tris, "material_idx": 0}], "weights": W}],
        "materials": [{"name": "mat_nimbra", "texture": str(GEO_ID)}],
        "parts": B.parts,
    }


# --------------------------------------------------------------------------- the atlas

def build_texture():
    """The 256x256 atlas, painted procedurally (PIL + numpy) -- zero imported image assets, 100%
    original pixels. Finished with a Bayer dither + 15-bit quantization: PSX hardware was 15-bit
    RGB with a CLUT, so the banding IS the period flavour, not an artefact."""
    import numpy as np
    from PIL import Image

    rng = np.random.default_rng(8422)            # fixed seed -> the atlas is reproducible byte-for-byte
    img = np.zeros((ATLAS, ATLAS, 3), dtype=np.float64)
    img[:, :] = np.array(VOID, dtype=np.float64)

    def value_noise(h, w, cells, octaves=3, seed_rng=rng):
        """Tileable-enough multi-octave value noise in [0,1] (smoothstep-interpolated lattice)."""
        acc = np.zeros((h, w), dtype=np.float64)
        amp, tot = 1.0, 0.0
        for o in range(octaves):
            n = max(2, int(cells * (2 ** o)))
            lat = seed_rng.random((n + 1, n + 1))
            ys = np.linspace(0, n, h, endpoint=False)
            xs = np.linspace(0, n, w, endpoint=False)
            y0 = ys.astype(int)[:, None]
            x0 = xs.astype(int)[None, :]
            fy = (ys - ys.astype(int))[:, None]
            fx = (xs - xs.astype(int))[None, :]
            sy = fy * fy * (3 - 2 * fy)
            sx = fx * fx * (3 - 2 * fx)
            a = lat[y0, x0] * (1 - sx) + lat[y0, x0 + 1] * sx
            b = lat[y0 + 1, x0] * (1 - sx) + lat[y0 + 1, x0 + 1] * sx
            acc += amp * (a * (1 - sy) + b * sy)
            tot += amp
            amp *= 0.5
        return acc / tot

    def rect(page):
        x0, y0, x1, y1 = PAGES[page]
        return slice(y0, y1), slice(x0, x1), (y1 - y0), (x1 - x0)

    def grad(h, w, top, bot, curve=1.0):
        t = np.broadcast_to((np.linspace(0.0, 1.0, h) ** curve)[:, None, None], (h, w, 1))
        return (np.array(top, dtype=np.float64)[None, None, :] * (1 - t)
                + np.array(bot, dtype=np.float64)[None, None, :] * t)

    # ---- MASK: a pale plate, the rim ringed in the ONE accent, two amber eye-hollows -------------
    ys, xs, h, w = rect("mask")
    yy, xx = np.mgrid[0:h, 0:w]
    ex = (xx - (w - 1) / 2) / ((w - 1) / 2)
    ey = (yy - (h - 1) / 2) / ((h - 1) / 2)
    r = np.sqrt(ex ** 2 + ey ** 2)
    face = (np.array(HI, dtype=np.float64)[None, None, :] * (1.0 - 0.30 * r ** 1.6)[:, :, None]
            + np.array(BASE, dtype=np.float64)[None, None, :] * (0.30 * r ** 1.6)[:, :, None])
    face *= (0.86 + 0.28 * value_noise(h, w, 4))[:, :, None]        # painterly mottle
    # a faint vertical seam down the plate -- the only "feature" besides the eyes
    face *= (1.0 - 0.10 * np.exp(-((ex / 0.045) ** 2)))[:, :, None]
    # the accent rim ring (~4px): r in [0.90, 1.0]
    ring = np.clip((r - 0.88) / 0.09, 0.0, 1.0) * np.clip((1.06 - r) / 0.06, 0.0, 1.0)
    face = face * (1 - ring)[:, :, None] + np.array(ACCENT, dtype=np.float64)[None, None, :] * ring[:, :, None]
    # the UNDERSIDE goes deep (STORYBOARD 1.5) -- a plate lit evenly reads as sports equipment; a
    # plate that falls off toward its chin reads as a face with nothing behind it
    face *= (1.0 - 0.46 * np.clip((ey + 0.15) / 1.05, 0.0, 1.0) ** 1.5)[:, :, None]
    face *= np.clip((1.03 - r) / 0.05, 0.0, 1.0)[:, :, None]        # outside the oval -> void
    # two shallow amber eye-hollows (STORYBOARD 1.2/1.5): the one "something is looking at you" beat
    # The plate is only 140u wide against a 545u shoulder span, so at battle distance the hollows are
    # the ONLY thing that makes it a face -- they are authored generously and hot-cored on purpose.
    for sgn in (-1.0, 1.0):
        d = np.sqrt(((ex - sgn * 0.35) / 0.235) ** 2 + ((ey + 0.09) / 0.145) ** 2)
        hollow = np.clip((1.0 - d), 0.0, 1.0) ** 0.62
        socket = np.array(DEEP, dtype=np.float64)[None, None, :] * 0.42
        glow = np.array(ACCENT, dtype=np.float64)[None, None, :] * 1.12
        core = np.clip((1.0 - d / 0.62), 0.0, 1.0) ** 0.85
        eye = socket * (1 - core)[:, :, None] + glow * core[:, :, None]
        face = face * (1 - hollow)[:, :, None] + eye * hollow[:, :, None]
    img[ys, xs] = face

    # ---- COWL: crest highlight -> deep hem, with a woven mist grain --------------------------------
    ys, xs, h, w = rect("cowl")
    g = grad(h, w, HI, DEEP, curve=0.85)
    g *= (0.80 + 0.36 * value_noise(h, w, 5))[:, :, None]
    yy, xx = np.mgrid[0:h, 0:w]
    g *= (1.0 - 0.16 * np.abs(np.sin(xx * 0.42 + 1.7 * np.sin(yy * 0.09))))[:, :, None]
    img[ys, xs] = g

    # ---- ARMS: leading edge (left of the page) bright, trailing edge deep -------------------------
    ys, xs, h, w = rect("arms")
    yy, xx = np.mgrid[0:h, 0:w]
    lead = (xx / max(1, w - 1))[:, :, None]
    a = (np.array(HI, dtype=np.float64)[None, None, :] * lead
         + np.array(DEEP, dtype=np.float64)[None, None, :] * (1 - lead))
    a *= (1.0 - 0.42 * (yy / max(1, h - 1)) ** 1.4)[:, :, None]     # darken toward the points
    a *= (0.84 + 0.30 * value_noise(h, w, 6))[:, :, None]
    img[ys, xs] = a

    # ---- CORE: base column, vertical shading, a subtle round-the-back falloff ---------------------
    ys, xs, h, w = rect("core")
    yy, xx = np.mgrid[0:h, 0:w]
    around = np.abs(np.cos(np.pi * xx / max(1, w - 1)))             # the wrap's lit/unlit sweep
    c = (np.array(BASE, dtype=np.float64)[None, None, :] * (0.55 + 0.45 * (1 - around))[:, :, None]
         + np.array(DEEP, dtype=np.float64)[None, None, :] * (0.45 * around)[:, :, None])
    c *= (1.0 - 0.30 * (yy / max(1, h - 1)))[:, :, None]
    c *= (0.86 + 0.26 * value_noise(h, w, 5))[:, :, None]
    img[ys, xs] = c

    # ---- VEIL: BASE -> VEIL_TIP down the page, with vertical mist striations ----------------------
    ys, xs, h, w = rect("veil")
    yy, xx = np.mgrid[0:h, 0:w]
    t = (yy / max(1, h - 1))[:, :, None] ** 0.8
    v = (np.array(BASE, dtype=np.float64)[None, None, :] * (1 - t)
         + np.array(VEIL_TIP, dtype=np.float64)[None, None, :] * t)
    # the striations WANDER (their phase is driven by noise down the page) -- a fixed-frequency sine
    # read as corduroy in the eye pass, which is a fabric, and NIMBRA is not wearing anything
    streak = 0.5 + 0.5 * np.sin(xx * 0.42 + 5.2 * value_noise(h, w, 2) * math.pi)
    v *= (0.86 + 0.24 * streak)[:, :, None]
    v *= (0.88 + 0.24 * value_noise(h, w, 7))[:, :, None]
    # the fray: the bottom rows dissolve toward the void so the tip reads torn even before the clip
    fray = np.clip((yy / max(1, h - 1) - 0.72) / 0.28, 0.0, 1.0)
    fray = fray * (0.35 + 0.65 * value_noise(h, w, 9))
    v = v * (1 - fray)[:, :, None] + np.array(VOID, dtype=np.float64)[None, None, :] * fray[:, :, None]
    img[ys, xs] = v

    # ---- VOID swatch: near-black with the faintest grain (mask back, cowl interior) ---------------
    ys, xs, h, w = rect("void")
    img[ys, xs] = np.array(VOID, dtype=np.float64)[None, None, :] * (0.75 + 0.45 * value_noise(h, w, 4))[:, :, None]

    # ---- PSX finish: 4x4 Bayer dither + 15-bit (5 bits/channel) quantization ----------------------
    bayer = np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]], dtype=np.float64)
    bayer = (bayer / 16.0 - 0.5) * (255.0 / 31.0)
    tile = np.tile(bayer, (ATLAS // 4, ATLAS // 4))[:, :, None]
    q = np.clip(img + tile, 0, 255)
    q = np.round(q / 255.0 * 31.0) / 31.0 * 255.0
    return Image.fromarray(q.astype(np.uint8), "RGB").convert("RGBA")
