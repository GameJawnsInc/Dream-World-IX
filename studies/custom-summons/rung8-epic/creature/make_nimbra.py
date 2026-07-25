"""RUNG 8 -- BUILD NIMBRA: mesh + rig + atlas -> the engine-ready FBX/PNG, plus the offline eye.

    py studies/custom-summons/rung8-epic/creature/make_nimbra.py [--no-render]

Writes (all under this folder, all committable -- 100% original, zero Square-Enix bytes):

    nimbra/6400.fbx          the ENGINE copy: FBX-ASCII, raw FF9 units, self-validated
    nimbra/6400.png          the 256x256 atlas
    nimbra/nimbra_model.json the struct dump the headless-Blender eye reads (bpy-side, no ff9mapkit)
    renders/*.png            THE OFFLINE EYE -- turntable x4 (bind pose) + one mid-frame per clip

...and stages a deploy-ready copy under ``rung8-epic/stage/creature/`` (NEVER the game install).

WHY PURE PYTHON AND NOT A BLENDER BUILD (the one place this lane reads STORYBOARD 7.2 and picks):
``emit_skinned_fbx`` writes FBX-ASCII and then RE-PARSES its own output through ``fbx_validate``, a
faithful port of Memoria's ``FbxAsciiReader`` -- so the file is checked by the ACTUAL CONSUMER's
grammar before it ever reaches disk. Blender is used where it is genuinely stronger (an independent
renderer for the eye, and a second opinion on the rig), but it cannot be the emitter here: Blender's
importer does not read FBX-ASCII at all, and its exporter would put us back in the m1b
FBX_SCALE_ALL/unit-metadata game. Authoring in FF9 units directly means the "raw units" law is
satisfied BY CONSTRUCTION -- ``--no-render`` prints the measured vertex bounds so it is also
satisfied by measurement (see ``validate_nimbra.py``).
"""
from __future__ import annotations

import json
import math
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parents[3]                       # the worktree root
sys.path.insert(0, str(HERE))                # sibling imports (nimbra_spec / nimbra_clips)
try:
    import ff9mapkit  # noqa: F401
except ImportError:
    sys.path.insert(0, str(ROOT / "ff9mapkit"))

import nimbra_clips as NC                                        # noqa: E402
import nimbra_spec as NS                                         # noqa: E402

OUT = HERE / "nimbra"
RENDERS = HERE / "renders"
STAGE = HERE.parent / "stage" / "creature"

# The storyboard's budgets (1.4). We report against them; the HARD ceiling is 6 parts / 7000 verts.
BUDGET_PARTS, BUDGET_VERTS = 6, 7000
TARGET = {"mask": (96, 130), "cowl": (220, 340), "arms": (520, 800),
          "core": (300, 460), "veil": (960, 1560)}


def calibrate_winding(game=None) -> int:
    """+1 if a real FF9 mesh winds cross(v1-v0, v2-v0) OUTWARD vs its centroid, -1 if inward. Verbatim
    from ``examples/boletta/make_creature.py`` -- whatever a shipping model uses provably renders, and
    an inside-out mesh is INVISIBLE in-game while looking fine in a double-sided previewer. Falls back
    to the calibrated +1 when no install is reachable (read-only either way)."""
    try:
        from ff9mapkit.models import extract
        m = extract.read_model("GEO_NPC_F1_BBA", game=game)
    except Exception as exc:
        print(f"  winding: no install read ({type(exc).__name__}) -> calibrated fallback +1")
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
    print(f"  winding: measured on GEO_NPC_F1_BBA, score {score:+d}")
    return 1 if score >= 0 else -1


# --------------------------------------------------------------------------- offline skinning (previews)

def _qmat(q):
    x, y, z, w = q
    n = math.sqrt(x * x + y * y + z * z + w * w) or 1.0
    x, y, z, w = x / n, y / n, z / n, w / n
    return ((1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)),
            (2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)),
            (2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)))


def _mm(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def _mv(m, v):
    return tuple(sum(m[i][k] * v[k] for k in range(3)) for i in range(3))


def bone_world(bones, pose):
    """(rotation matrix, world position) per bone for a pose dict {boneNum: {'rot':q,'pos':(x,y,z)}}."""
    out = {}
    for i, b in enumerate(bones):
        p = pose.get(i, {})
        lr = _qmat(p.get("rot") or (0.0, 0.0, 0.0, 1.0))
        lp = tuple(p.get("pos") or b["pos"])
        if b["parent"] is None:
            out[i] = (lr, lp)
        else:
            pi = next(j for j, bb in enumerate(bones) if bb["name"] == b["parent"])
            PR, PP = out[pi]
            wp = tuple(PP[k] + _mv(PR, lp)[k] for k in range(3))
            out[i] = (_mm(PR, lr), wp)
    return out


def rest_world(bones):
    return {i: wp for i, (_r, wp) in bone_world(bones, {}).items()}


def pose_model(model: dict, pose: dict) -> dict:
    """Linear-blend-skin the struct into a new struct -- ``v' = sum_j w_j (R_j (v - rest_j) + world_j)``.
    Rest rotations are identity and scales are 1, so the inverse bind is a pure -rest_j translation."""
    bones = model["bones"]
    bw = bone_world(bones, pose)
    rest = rest_world(bones)
    mesh = model["meshes"][0]
    V = []
    for v, infl in zip(mesh["verts"], mesh["weights"]):
        acc = [0.0, 0.0, 0.0]
        tot = 0.0
        for bn, w in infl:
            R, P = bw[bn]
            r = rest[bn]
            d = _mv(R, (v[0] - r[0], v[1] - r[1], v[2] - r[2]))
            for k in range(3):
                acc[k] += w * (d[k] + P[k])
            tot += w
        V.append(tuple(a / (tot or 1.0) for a in acc))
    out = dict(model)
    out["meshes"] = [dict(mesh, verts=V, normals=None)]
    return out


def pose_at(curves: dict, frame: int) -> dict:
    """The pose dict at an integer frame of a clip's raw curves."""
    pose = {}
    for bn, ch in curves.items():
        e = {}
        for chan, keys in ch.items():
            e[chan] = keys[min(frame, len(keys) - 1)][1]
        pose[bn] = e
    return pose


# --------------------------------------------------------------------------- main

def main(argv):
    render = "--no-render" not in argv
    print("NIMBRA -- rung 8, the composed epic (creature lane)")
    wind = calibrate_winding()

    model = NS.build_model(wind)
    mesh = model["meshes"][0]
    nv, nt = len(mesh["verts"]), len(mesh["submeshes"][0]["tris"])

    # ---- budgets + silhouette geometry report (STORYBOARD 1.3/1.4) -------------------------------
    groups = {"mask": ["mask"], "cowl": ["cowl"], "arms": ["armL", "armR"], "core": ["core"],
              "veil": [f"veil{i}" for i in range(NS.VEIL_N)]}
    print(f"  ONE merged mesh, {len(groups)} logical parts (budget <= {BUDGET_PARTS})")
    for g, names in groups.items():
        v = sum(model["parts"][n][1] - model["parts"][n][0] for n in names)
        t = sum(model["parts"][n][3] - model["parts"][n][2] for n in names)
        tv, tt = TARGET[g]
        print(f"    {g:<5} {v:>5} verts {t:>5} tris   (storyboard target {tv}/{tt})")
    print(f"    TOTAL {nv:>5} verts {nt:>5} tris   (hard ceiling {BUDGET_VERTS} verts)")
    assert nv <= BUDGET_VERTS, f"vert budget blown: {nv} > {BUDGET_VERTS}"
    assert len(groups) <= BUDGET_PARTS

    xs = [v[0] for v in mesh["verts"]]
    ys = [v[1] for v in mesh["verts"]]
    zs = [v[2] for v in mesh["verts"]]
    print(f"  bounds  X [{min(xs):.0f}, {max(xs):.0f}]  Y [{min(ys):.0f}, {max(ys):.0f}]  "
          f"Z [{min(zs):.0f}, {max(zs):.0f}]   height {max(ys) - min(ys):.0f}u "
          f"(storyboard 1400u, Y-DOWN so the crown is the MINIMUM)")
    assert min(ys) <= -1380.0, "crown is not at ~-1400 -- the model is not authored in raw FF9 units"
    assert 1300.0 <= (max(ys) - min(ys)) <= 1500.0, "total height outside the 1400u design"

    # ---- weights sanity -------------------------------------------------------------------------
    maxinf = max(len(w) for w in mesh["weights"])
    worst = max(abs(sum(w for _b, w in inf) - 1.0) for inf in mesh["weights"])
    used = sorted({b for inf in mesh["weights"] for b, _w in inf})
    print(f"  weights: <= {maxinf} influences/vert, |sum-1| max {worst:.2e}, "
          f"bones carrying weight {len(used)}/{len(model['bones'])} {used}")
    assert worst < 1e-9 and maxinf <= 4

    # ---- the atlas ------------------------------------------------------------------------------
    tex = NS.build_texture()
    model["textures"] = {str(NS.GEO_ID): tex}

    # ---- emit (self-validating against Memoria's own FBX grammar) ---------------------------------
    from ff9mapkit.models import fbx_skin
    text, meta = fbx_skin.emit_skinned_fbx(model)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{NS.GEO_ID}.fbx").write_text(text, encoding="ascii", newline="\n")
    tex.save(OUT / f"{NS.GEO_ID}.png")
    print(f"  emitted {OUT / f'{NS.GEO_ID}.fbx'}  ({len(text)} bytes, "
          f"euler_max_err {meta['euler_max_err']:.2e}, bones {meta['bones']})")

    # ---- the struct dump the bpy eye consumes (no ff9mapkit needed inside Blender) ----------------
    dump = {
        "geo": model["geo"], "geo_id": model["geo_id"], "wind": wind,
        "bones": model["bones"], "parts": model["parts"],
        "verts": mesh["verts"], "normals": mesh["normals"], "uvs": mesh["uvs"],
        "tris": mesh["submeshes"][0]["tris"], "weights": mesh["weights"],
        "texture": f"{NS.GEO_ID}.png",
        "clips": {n: {"frames": c["frames"], "speed": c["speed"], "key": c["key"],
                      "curves": {str(b): {k: [[t, list(v)] for t, v in keys]
                                          for k, keys in ch.items()}
                                 for b, ch in c["curves"].items()}}
                  for n, c in NC.all_clips().items()},
    }
    (OUT / "nimbra_model.json").write_text(json.dumps(dump), encoding="utf-8")
    print(f"  dumped  {OUT / 'nimbra_model.json'} (bpy bridge)")

    # ---- stage the deployable pair ----------------------------------------------------------------
    STAGE.mkdir(parents=True, exist_ok=True)
    shutil.copy2(OUT / f"{NS.GEO_ID}.fbx", STAGE / f"{NS.GEO_ID}.fbx")
    shutil.copy2(OUT / f"{NS.GEO_ID}.png", STAGE / f"{NS.GEO_ID}.png")
    print(f"  staged  {STAGE} (NOT the game install)")

    # ---- THE OFFLINE EYE (kit software renderer) --------------------------------------------------
    if render:
        render_eye(model)
    return 0


# Frames sampled per clip for the contact sheets, at the beats STORYBOARD 1.7 names -- expressed as
# FRACTIONS of the clip and resolved against each clip's OWN length. They used to be absolute indices
# tied to 90/75/60, which STORYBOARD 11.9's re-cut turned into a KeyError/mis-sample the moment the
# clips were sized to their beats: a sampling table is a copy of the tick table and goes stale the same
# way (11.5's "three independent copies" lesson, one lane further on).
CLIP_BEATS = {
    "emerge": [0.0, 0.202, 0.404, 0.607, 0.809, 1.0],       # folded -> unfurling -> at rest
    "drift": [0.0, 0.203, 0.405, 0.595, 0.797, 1.0],        # one full loop; first and last MUST match
    "driftlook": [0.0, 0.203, 0.405, 0.595, 0.797, 1.0],    # the same cycle, 25 frames
    "strike": [0.0, 0.203, 0.407, 0.610, 0.780, 1.0],       # rest -> wind-back -> LUNGE PEAK -> settle
}
TURNTABLE = [180, 210, 240, 270, 300, 330, 0, 90]      # 180 = dead front (the party's view)
# per-clip camera: the strike DRIVES FORWARD (+Z) and the drift's wave travels around the axis, and
# both are almost invisible head-on -- a 3/4 view is the only one that shows them at all
CLIP_YAW = {"emerge": 196.0, "drift": 232.0, "driftlook": 232.0, "strike": 244.0}


def clip_frames(name, frames):
    """``CLIP_BEATS[name]`` resolved onto a clip of ``frames`` frames (last index ``frames - 1``)."""
    return [int(round(u * (frames - 1))) for u in CLIP_BEATS[name]]


def render_eye(model):
    """THE OFFLINE EYE (mandatory, STORYBOARD 7.2): contact sheets a human/agent actually LOOKS at.
    The rung-7-era "red circle" incident is the reason this is not optional."""
    from PIL import Image
    from ff9mapkit.models import preview
    RENDERS.mkdir(parents=True, exist_ok=True)

    def sheet(items, path, size=250, cols=4):
        rows = (len(items) + cols - 1) // cols
        out = Image.new("RGBA", (size * cols, size * rows), (20, 22, 24, 255))
        for i, (m, yaw) in enumerate(items):
            out.alpha_composite(preview.render_model(m, size=size, yaw=float(yaw), pitch=8.0),
                                ((i % cols) * size, (i // cols) * size))
        out.save(path)

    for tag, yaw in (("front", 180.0), ("three_q", 225.0), ("side", 270.0), ("back", 0.0)):
        preview.render_model(model, size=420, yaw=yaw, pitch=8.0).save(
            RENDERS / f"kit_turntable_{tag}.png")
    sheet([(model, y) for y in TURNTABLE], RENDERS / "kit_turntable_sheet.png")

    for name, c in NC.all_clips().items():
        items = []
        picks = clip_frames(name, c["frames"])
        for f in picks:
            posed = pose_model(model, pose_at(c["curves"], f))
            posed["textures"] = model["textures"]
            items.append((posed, CLIP_YAW[name]))
        sheet(items, RENDERS / f"kit_clip_{name}.png", size=250, cols=6)
        mid = picks[3]
        posed = pose_model(model, pose_at(c["curves"], mid))
        posed["textures"] = model["textures"]
        preview.render_model(posed, size=420, yaw=CLIP_YAW[name], pitch=8.0).save(
            RENDERS / f"kit_clip_{name}_f{mid}.png")
    print(f"  rendered {RENDERS} -- LOOK AT THEM before anything is deployed "
          f"(THE OFFLINE-EYE / MODEL-PREVIEW LAW)")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
