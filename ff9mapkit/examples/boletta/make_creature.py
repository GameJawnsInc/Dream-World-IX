"""Boletta -- a wholly-original creature, authored in plain Python against the kit's Model struct.

This is the worked example of the FROM-SCRATCH model path: nothing about her comes from FF9's
data -- the mesh, rig, weights, texture, and (in make_creature_anims.py) her animation clip are
all generated here, then shipped through the same pipeline an edited real model uses:

    Model struct -> emit_skinned_fbx -> [[mint]] fbx= (a new GEO id) -> [[npc]] placement

Run it (from the kit root, or anywhere with ff9mapkit installed):

    py examples/boletta/make_creature.py

writes `creature/6300.fbx` + `creature/6300.png` (the [[mint]] payload -- boletta.field.toml points
at them) and `boletta_preview_*.png` (software renders, so you can see her before the game does).

Model-space facts this file encodes (they apply to ANY from-scratch model):
  * The struct space is the engine's: Y-DOWN (ground at y=0, the head at the most-negative y),
    FF9 units (a knee-high critter is ~300 tall), left-handed like Unity.
  * Triangle WINDING is calibrated from a real model, not assumed -- FF9's cutout materials can
    cull backfaces, and an inside-out mesh looks "fine" in a double-sided previewer while being
    invisible in-game. `calibrate_winding` measures how a shipping mesh winds (outward, +1) and
    falls back to that known value when no install is present.
  * Texture V: the struct's v=0 is the image BOTTOM (Unity convention). For a cylindrical strip
    that means the image's TOP rows must map to the model's TOP -- the first draft of this file
    got it backwards and rendered the painted face upside down (smile above the eyes). The
    preview renderer is how you catch that offline.
  * ONE merged mesh: a tiny standalone renderer can be one-shot disabled by the field's
    character-show pass (the Garnet-scrunchie lesson) -- keep every part in a single mesh.
"""
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).parent

try:
    import ff9mapkit  # noqa: F401  (installed kit)
except ImportError:                 # repo checkout, script run directly: the kit root is two up
    sys.path.insert(0, str(HERE.parents[1]))

GEO_NAME, GEO_ID = "GEO_NPC_F1_M300", 6300     # mint band >= 6000; token M300 = the id's band offset
SEG = 14                                       # radial segments everywhere

# The rig: 5 bones, authored at REST (identity rotations -- the idle clip poses them).
# Y-down: bone000 sits mid-body at world (0,-130,0); children are LOCAL offsets from the parent.
BONES = [
    {"name": "bone000", "parent": None,      "pos": (0.0, -130.0, 0.0),   "rot": (0, 0, 0, 1), "scale": (1, 1, 1)},
    {"name": "bone001", "parent": "bone000", "pos": (0.0, -82.0, 0.0),    "rot": (0, 0, 0, 1), "scale": (1, 1, 1)},  # stem top
    {"name": "bone002", "parent": "bone001", "pos": (0.0, -48.0, 0.0),    "rot": (0, 0, 0, 1), "scale": (1, 1, 1)},  # cap
    {"name": "bone003", "parent": "bone000", "pos": (-46.0, 114.0, 16.0), "rot": (0, 0, 0, 1), "scale": (1, 1, 1)},  # foot L
    {"name": "bone004", "parent": "bone000", "pos": (46.0, 114.0, 16.0),  "rot": (0, 0, 0, 1), "scale": (1, 1, 1)},  # foot R
]


def calibrate_winding(game=None) -> int:
    """+1 if a real FF9 mesh winds cross(v1-v0, v2-v0) OUTWARD (vs the mesh centroid), -1 if inward.
    Whatever a shipping model uses provably renders. Falls back to the known calibrated value (+1,
    measured against BBA 2026-07-08) when no FF9 install is reachable."""
    try:
        from ff9mapkit.models import extract
        m = extract.read_model("GEO_NPC_F1_BBA", game=game)
    except Exception:
        return 1
    mesh = max(m["meshes"], key=lambda me: len(me["verts"]))
    verts = mesh["verts"]
    cx = sum(v[0] for v in verts) / len(verts)
    cy = sum(v[1] for v in verts) / len(verts)
    cz = sum(v[2] for v in verts) / len(verts)
    score = 0
    for sub in mesh["submeshes"]:
        for a, b, c in sub["tris"]:
            v0, v1, v2 = verts[a], verts[b], verts[c]
            nx = (v1[1] - v0[1]) * (v2[2] - v0[2]) - (v1[2] - v0[2]) * (v2[1] - v0[1])
            ny = (v1[2] - v0[2]) * (v2[0] - v0[0]) - (v1[0] - v0[0]) * (v2[2] - v0[2])
            nz = (v1[0] - v0[0]) * (v2[1] - v0[1]) - (v1[1] - v0[1]) * (v2[0] - v0[0])
            mx = (v0[0] + v1[0] + v2[0]) / 3 - cx
            my = (v0[1] + v1[1] + v2[1]) / 3 - cy
            mz = (v0[2] + v1[2] + v2[2]) / 3 - cz
            d = nx * mx + ny * my + nz * mz
            score += (1 if d > 0 else -1) if d != 0 else 0
    return 1 if score >= 0 else -1


def build_texture() -> Image.Image:
    """The 256x256 atlas: stem strip (left half, with the painted face) + cap disc + gills + feet."""
    img = Image.new("RGBA", (256, 256), (232, 213, 176, 255))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, 127, 137], fill=(236, 219, 184, 255))            # stem strip base
    for px, s in ((46, 1.0), (82, -1.0)):                               # two oval eyes + glints
        d.ellipse([px - 8, 42, px + 8, 66], fill=(42, 30, 28, 255))
        d.ellipse([px - 4 + 3 * s, 46, px + 3 + 3 * s, 54], fill=(255, 255, 255, 255))
    d.arc([56, 70, 72, 82], 15, 165, fill=(120, 84, 60, 255), width=3)  # smile below the eyes
    d.ellipse([28, 62, 40, 72], fill=(240, 168, 148, 180))              # blush
    d.ellipse([88, 62, 100, 72], fill=(240, 168, 148, 180))
    d.ellipse([130, 4, 254, 128], fill=(196, 44, 40, 255))              # cap disc: red...
    for (sx, sy, sr) in ((192, 40, 11), (166, 76, 9), (216, 84, 8), (178, 52, 5), (208, 56, 6)):
        d.ellipse([sx - sr, sy - sr, sx + sr, sy + sr], fill=(246, 240, 228, 255))   # ...white spots
    d.rectangle([132, 108, 168, 132], fill=(226, 202, 158, 255))        # under-cap gills (cream)
    d.rectangle([140, 142, 224, 176], fill=(150, 106, 74, 255))         # feet (warm brown)
    return img


def build_model(wind: int = 1) -> dict:
    """The complete Model struct (fresh lists -- safe to call repeatedly). ``wind`` from
    :func:`calibrate_winding`."""
    V, N, UV, W, TRIS = [], [], [], [], []

    def tri(a, b, c):
        return (a, b, c) if wind > 0 else (a, c, b)

    def add_v(p, n, uv, w):
        V.append(tuple(p)); N.append(tuple(n)); UV.append(tuple(uv)); W.append(list(w))
        return len(V) - 1

    def uvy(rowfrac):        # struct v (0 = image bottom) from an image-row fraction (0 = image top)
        return 1.0 - rowfrac

    # ---- stem: tapered cylinder, y -20 (near ground) .. -212 (cap seat); azimuth 0 = +Z (the face)
    STEM = [(-20.0, 58.0), (-70.0, 60.0), (-120.0, 57.0), (-165.0, 50.0), (-212.0, 42.0)]
    rows = []
    for (y, r) in STEM:
        t = max(0.0, min(1.0, (-y - 80.0) / 120.0))                      # root->stem-top weight blend
        w = [(1, t), (0, 1.0 - t)] if 0.0 < t < 1.0 else ([(1, 1.0)] if t >= 1.0 else [(0, 1.0)])
        row = []
        for s in range(SEG + 1):                                         # +1: seam vert for clean UV wrap
            az = 2.0 * math.pi * s / SEG
            x, z = math.sin(az) * r, math.cos(az) * r
            u = 0.02 + 0.46 * (((s / SEG) + 0.5) % 1.0)                  # face lands mid-strip
            # image TOP rows land at the stem TOP (rowfrac decreases with height) -- see module doc
            v = uvy(0.52 - 0.50 * (-y - 20.0) / 192.0)
            row.append(add_v((x, y, z), (math.sin(az), 0.0, math.cos(az)), (u, v), w))
        rows.append(row)
    for j in range(len(rows) - 1):
        a, b = rows[j], rows[j + 1]
        for s in range(SEG):
            TRIS.append(tri(a[s], b[s], b[s + 1]))
            TRIS.append(tri(a[s], b[s + 1], a[s + 1]))

    # ---- cap: flattened hemisphere (radius 118, squash .62, overhanging the stem) + apex + under-ring
    CAP_C, CAP_R, CAP_SQ = -212.0, 118.0, 0.62
    cap_rows = []
    for k in range(1, 5):
        ring = math.radians(90.0 * (5 - k) / 5.0)                        # rim -> near-apex
        rr, yy = CAP_R * math.sin(ring), CAP_C - CAP_R * CAP_SQ * math.cos(ring)
        row = []
        for s in range(SEG + 1):
            az = 2.0 * math.pi * s / SEG
            ny = -(1.0 - rr / CAP_R)                                     # blend radial -> up(-Y)
            nl = math.sqrt((rr / CAP_R) ** 2 + ny * ny) or 1.0
            n = (math.sin(az) * (rr / CAP_R) / nl, ny / nl, math.cos(az) * (rr / CAP_R) / nl)
            fr = 0.23 * (rr / CAP_R)                                     # polar UV in the cap disc
            row.append(add_v((math.sin(az) * rr, yy, math.cos(az) * rr), n,
                             (0.75 + fr * math.sin(az), uvy(0.26 + fr * math.cos(az))), [(2, 1.0)]))
        cap_rows.append(row)
    apex = add_v((0.0, CAP_C - CAP_R * CAP_SQ, 0.0), (0.0, -1.0, 0.0), (0.75, uvy(0.26)), [(2, 1.0)])
    for j in range(len(cap_rows) - 1):
        a, b = cap_rows[j], cap_rows[j + 1]
        for s in range(SEG):
            TRIS.append(tri(a[s], b[s], b[s + 1]))
            TRIS.append(tri(a[s], b[s + 1], a[s + 1]))
    top = cap_rows[-1]
    for s in range(SEG):
        TRIS.append(tri(top[s], apex, top[s + 1]))
    ring_in, ring_out = [], []
    for s in range(SEG + 1):                                             # flat annulus facing DOWN (+Y)
        az = 2.0 * math.pi * s / SEG
        ring_in.append(add_v((math.sin(az) * 46.0, CAP_C, math.cos(az) * 46.0), (0.0, 1.0, 0.0),
                             (0.56 + 0.02 * math.sin(az), uvy(0.47 + 0.02 * math.cos(az))), [(2, 1.0)]))
        ring_out.append(add_v((math.sin(az) * CAP_R, CAP_C, math.cos(az) * CAP_R), (0.0, 1.0, 0.0),
                              (0.56 + 0.05 * math.sin(az), uvy(0.47 + 0.05 * math.cos(az))), [(2, 1.0)]))
    for s in range(SEG):
        TRIS.append(tri(ring_out[s], ring_in[s], ring_in[s + 1]))
        TRIS.append(tri(ring_out[s], ring_in[s + 1], ring_out[s + 1]))

    # ---- feet: two squashed ellipsoids, bottoms flattened just above the ground plane
    for side, bone in ((-1.0, 3), (1.0, 4)):
        cx0, cy0, cz0, rx, ry, rz = 46.0 * side, -16.0, 16.0, 30.0, 17.0, 38.0
        frows = []
        for k in range(1, 4):
            th = math.pi * k / 4.0
            row = []
            for s in range(SEG):
                az = 2.0 * math.pi * s / SEG
                nx, ny, nz = math.sin(th) * math.sin(az), -math.cos(th), math.sin(th) * math.cos(az)
                p = (cx0 + nx * rx, min(-1.0, cy0 + ny * ry), cz0 + nz * rz)
                u = 0.62 + 0.05 * nx + (0.16 if side > 0 else 0.0)
                row.append(add_v(p, (nx / rx * 30, ny / ry * 17, nz / rz * 38),
                                 (u, uvy(0.62 + 0.05 * nz)), [(bone, 1.0)]))
            frows.append(row)
        u0 = 0.62 + (0.16 if side > 0 else 0.0)
        topv = add_v((cx0, cy0 - ry, cz0), (0.0, -1.0, 0.0), (u0, uvy(0.62)), [(bone, 1.0)])
        botv = add_v((cx0, -1.0, cz0), (0.0, 1.0, 0.0), (u0, uvy(0.62)), [(bone, 1.0)])
        for s in range(SEG):
            s2 = (s + 1) % SEG
            TRIS.append(tri(frows[0][s], topv, frows[0][s2]))
            for j in range(len(frows) - 1):
                TRIS.append(tri(frows[j][s], frows[j + 1][s], frows[j + 1][s2]))
                TRIS.append(tri(frows[j][s], frows[j + 1][s2], frows[j][s2]))
            TRIS.append(tri(frows[-1][s], botv, frows[-1][s2]))
    N = [tuple(c / (math.sqrt(sum(x * x for x in n)) or 1.0) for c in n) for n in N]

    return {
        "geo": GEO_NAME, "geo_id": GEO_ID, "type_int": 4, "root_bone": "bone000",
        "bones": [dict(b) for b in BONES],
        "meshes": [{"name": "mesh0", "verts": V, "normals": N, "uvs": UV,
                    "submeshes": [{"tris": TRIS, "material_idx": 0}], "weights": W}],
        "materials": [{"name": "mat_boletta", "texture": str(GEO_ID)}],
        "textures": {str(GEO_ID): build_texture()},
    }


def main():
    from ff9mapkit.models import fbx_skin, preview
    wind = calibrate_winding()
    model = build_model(wind)
    mesh = model["meshes"][0]
    print(f"winding: {'outward' if wind > 0 else 'inward'} ({wind:+d})  "
          f"verts {len(mesh['verts'])}  tris {len(mesh['submeshes'][0]['tris'])}  bones {len(model['bones'])}")
    text, meta = fbx_skin.emit_skinned_fbx(model)        # self-validates against the engine tokenizer
    out = HERE / "creature"
    out.mkdir(exist_ok=True)
    (out / f"{GEO_ID}.fbx").write_text(text, encoding="ascii", newline="\n")
    model["textures"][str(GEO_ID)].save(out / f"{GEO_ID}.png")
    print(f"emitted {out / f'{GEO_ID}.fbx'}  (euler_max_err {meta['euler_max_err']:.2e})")
    for tag, yaw in (("front", 195.0), ("three_q", 145.0)):
        preview.render_model(model, size=320, yaw=yaw).save(HERE / f"boletta_preview_{tag}.png")
    print("previews written -- look at them before the game does")


if __name__ == "__main__":
    main()
