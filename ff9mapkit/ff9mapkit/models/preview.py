"""Software-render an FF9 model -> a small textured preview image (pure PIL, no OpenGL/numpy).

The illustrative half of the models pillar: any surface that lists a model can show what it LOOKS
like. Facts the renderer leans on:

* The posed verts come from TRUE linear-blend skinning of the raw prefab data
  (:func:`_skinned_struct`): ``v' = sum(w_j * boneWorld_rest_j * m_BindPose_j * v)`` -- exactly the
  engine's own bundle render at rest pose. The ``read_model`` G-bake shortcut (rest-pose verts) is
  NOT enough here: it is a per-mesh RIGID correction, and models with genuinely divergent per-bone
  binds (the ``GEO_SUB_W0_*`` overworld actors) come out scrambled under it -- proven on W0_001,
  whose body rendered as a blob-on-a-stick until skinned per bone.
* FF9 model space is LH **Y-DOWN** (the glTF exporter's negate-Y mirror is the proof) -- which
  matches image coordinates, so the orthographic projection is direct: screen x = x, screen y = y.
* Unity UV wrap mode is REPEAT and some models author UVs a whole tile off ([1..2], negative --
  W0_001 mesh1); ``PIL.Image.transform`` samples outside the texture as transparent, so each
  triangle's UVs are translated by the integer tile of their minimum first.

Painter's algorithm (triangles sorted far -> near) + per-triangle affine texture mapping via
``PIL.Image.transform`` (NEAREST keeps FF9's crisp low-res texel look) + a flat-shaded lighting
buffer multiplied over the color at the end. FF9 materials are unlit cutout-alpha and double-sided,
so there is no backface culling and shading uses ``abs(dot)``. Supersample-then-downscale stands in
for antialiasing. Good enough for a thumbnail; not a renderer.
"""
from __future__ import annotations

import math

__all__ = ["render_model", "render_token", "projected_bounds", "DEFAULT_YAW", "DEFAULT_PITCH"]

DEFAULT_YAW = 30.0     # degrees about the vertical (Y) axis; a 3/4 view
DEFAULT_PITCH = 12.0   # degrees about X; a slight look-down


def _rot_y(deg: float):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]]


def _rot_x(deg: float):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]]


def _mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _mat_vec(m, v):
    return [m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
            m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
            m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2]]


def _trs4(pos, rot, scale):
    """Local pos/quat/scale -> a 4x4 (row-major) local transform T*R*S."""
    from .fbx_skin import _quat_to_matrix
    R = _quat_to_matrix(rot)
    return [
        [R[0][0] * scale[0], R[0][1] * scale[1], R[0][2] * scale[2], pos[0]],
        [R[1][0] * scale[0], R[1][1] * scale[1], R[1][2] * scale[2], pos[1]],
        [R[2][0] * scale[0], R[2][1] * scale[1], R[2][2] * scale[2], pos[2]],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _mm4(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def _mv4(m, v):
    x, y, z = v[0], v[1], v[2]
    return [m[0][0] * x + m[0][1] * y + m[0][2] * z + m[0][3],
            m[1][0] * x + m[1][1] * y + m[1][2] * z + m[1][3],
            m[2][0] * x + m[2][1] * y + m[2][2] * z + m[2][3]]


def _stand_pose(geo_id: int, bones: list, game=None, env5=None) -> list:
    """Bones re-posed from frame 0 of the model's most stand-like on-disc clip (falls back to the
    rest hierarchy if the model has no clips). Some rigs' REST pose is a collapsed authoring pose the
    player never sees (the GEO_SUB_W0_* overworld actors) -- the engine always drives them with a
    clip, so a faithful still is 'first frame of stand', not 'rest'."""
    from . import anim as _anim
    from . import _gltf_io
    from .. import catalog

    try:
        env = env5 if env5 is not None else _anim._load_env5(game)
        keys = _anim.list_clip_keys(env, geo_id)
    except Exception:
        return bones

    def rank(k):
        nm = (catalog.animation_name(k) or "").lower()
        for i, tokn in enumerate(("stand", "idle", "wait", "walk")):
            if tokn in nm:
                return (i, k)
        return (9, k)
    best, folder = (min(keys, key=rank), geo_id) if keys else (None, None)
    if best is None or rank(best)[0] == 9:
        # The own folder has no stand-like clip (or no clips at all) -- follow the engine's AnimationDB
        # name-token redirect to the DONOR folder holding the model's named idle/stand (an F1+ NPC variant
        # like GEO_NPC_F1_BBA keeps only niche gestures natively), so the thumbnail poses from a real rest
        # clip instead of a random gesture / the collapsed rest hierarchy.
        try:
            acts = catalog.animations_for_model(geo_id) or {}
            disc = _gltf_io.anim_disc_map(env)
            for act in ("stand", "idle", "idle1", "wait", "walk"):
                loc = catalog.locate_animation(acts[act], geo_id, disc) if act in acts else None
                if loc:
                    best, folder = loc
                    break
        except Exception:
            pass
    if best is None:
        return bones
    clip = _gltf_io.read_clip(env, folder, best)
    if not clip:
        return bones
    by_num = {ch.get("bone"): ch for ch in clip["bones"].values() if ch.get("bone") is not None}
    posed = []
    for bn in bones:
        ch = by_num.get(int(bn["name"][4:])) if bn["name"].startswith("bone") else None
        b2 = dict(bn)
        if ch:
            if ch.get("rot"):
                b2["rot"] = list(ch["rot"][0][1])
            if ch.get("pos"):
                b2["pos"] = list(ch["pos"][0][1])
            if ch.get("scale"):
                b2["scale"] = list(ch["scale"][0][1])
        posed.append(b2)
    return posed


def _pose_bones_at(bones: list, clip: dict, t: float) -> list:
    """Bones re-posed from a clip SAMPLED at time ``t`` (seconds) -- the animated-preview sibling of
    :func:`_stand_pose`'s frame-0 read.

    Each bone path the clip keys is matched to the skeleton by bone NUMBER (the engine binds by name),
    and each present rot/pos/scale channel is linearly interpolated at ``t``
    (:func:`~ff9mapkit.models.anim._sample_curve` -- exact between keys, clamped at both ends, which is
    what the engine itself does). A bone the clip doesn't key, or a channel it doesn't carry, KEEPS its
    rest TRS: playback only touches what a clip animates. The input list is never mutated."""
    from . import anim as _anim

    if not clip or not clip.get("bones"):
        return bones
    by_num = {ch.get("bone"): ch for ch in clip["bones"].values() if ch.get("bone") is not None}
    posed = []
    for bn in bones:
        ch = by_num.get(int(bn["name"][4:])) if bn["name"].startswith("bone") else None
        b2 = dict(bn)
        if ch:
            for chan in ("rot", "pos", "scale"):
                if ch.get(chan):
                    v = _anim._sample_curve(ch[chan], t)
                    if v is not None:
                        b2[chan] = list(v)      # the struct's TRS is a LIST everywhere else -- keep it one
        posed.append(b2)
    return posed


def _skinned_struct(token: str, game=None, bundle=None, *, pose: bool = True, env5=None,
                    collected: "dict | None" = None, textures: "dict | None" = None,
                    clip: "dict | None" = None, folder_id=None, anim_key=None, t: float = 0.0) -> dict:
    """Read a model and pose it by TRUE linear-blend skinning -> a render_model struct.

    Uses the raw prefab data (:func:`extract._collect`): bone world transforms composed from the
    hierarchy TRS, times each mesh's own stored ``m_BindPose`` -- the same product the engine's
    bundle path renders. Exact for every model, including the divergent per-bone binds the
    ``read_model`` rigid G-bake can only approximate. With ``pose`` (default) the bone TRS comes
    from frame 0 of the model's stand clip (see :func:`_stand_pose`). Static prefabs
    (weapons/props: no skin) pass through :func:`extract.read_static_model` verbatim.

    The animated-preview path reuses one model across many frames, so the two expensive per-call reads
    are injectable: ``collected`` is an already-walked :func:`extract._collect` dict and ``textures`` an
    already-decoded ``{stem: Image}`` (both container scans -- re-paying them per frame dominates the
    render). ``clip`` (a raw clip dict) or ``anim_key`` (+ ``folder_id``, read out of ``env5``) poses the
    bones at time ``t`` instead of at the stand pose. Every one of these defaults to None/0.0 and the
    untouched call renders exactly what it renders today.
    """
    from . import extract

    c = collected if collected is not None else extract._collect(token, game, bundle=bundle)
    if not c["smrs"]:
        return extract.read_static_model(token, game=game, bundle=c["bundle"])

    if clip is None and anim_key is not None and env5 is not None:
        from . import _gltf_io
        clip = _gltf_io.read_clip(env5, c["geo_id"] if folder_id is None else folder_id, anim_key)
    if clip is not None:
        bones = _pose_bones_at(c["bones"], clip, t)
    else:
        bones = _stand_pose(c["geo_id"], c["bones"], game=game, env5=env5) if pose else c["bones"]
    # bone world transforms (bones[] is pre-order, so parents resolve before children)
    world: dict = {}
    for bn in bones:
        local = _trs4(bn["pos"], bn["rot"], bn["scale"])
        world[bn["name"]] = _mm4(world[bn["parent"]], local) if bn["parent"] else local

    meshes: list = []
    materials: list = []
    texture_stems: set = set()
    for s in c["smrs"]:
        mesh, mat_stems = s["mesh"], s["mat_stems"]
        num_to_m: dict = {}
        for bone_name, bindpose in s["samples"]:
            w = world.get(bone_name)
            if w is not None:
                num_to_m[int(bone_name[4:])] = _mm4(w, bindpose)
        verts, normals = [], []
        src_normals = mesh.get("normals")
        for vi, v in enumerate(mesh["verts"]):
            infl = [(n, wt) for (n, wt) in s["weights"][vi] if n in num_to_m]
            if not infl:
                verts.append(list(v[:3]))
                if src_normals:
                    normals.append(list(src_normals[vi][:3]))
                continue
            tot = sum(wt for _, wt in infl) or 1.0
            px = py = pz = 0.0
            for n, wt in infl:
                sx, sy, sz = _mv4(num_to_m[n], v)
                px += sx * wt / tot; py += sy * wt / tot; pz += sz * wt / tot
            verts.append([px, py, pz])
            if src_normals:
                # rotate by the dominant influence (thumbnail-grade; _shade_of renormalizes)
                dom = max(infl, key=lambda p: p[1])[0]
                m = num_to_m[dom]
                nx, ny, nz = src_normals[vi][:3]
                normals.append([m[0][0] * nx + m[0][1] * ny + m[0][2] * nz,
                                m[1][0] * nx + m[1][1] * ny + m[1][2] * nz,
                                m[2][0] * nx + m[2][1] * ny + m[2][2] * nz])
        for stem in mat_stems:
            if stem:
                texture_stems.add(stem)
        base_mat = len(materials)
        subs = []
        for si, tris in enumerate(mesh["submeshes"]):
            subs.append({"material_idx": base_mat + si, "tris": tris})
            materials.append({"name": f"{mesh['name']}_mat{si}",
                              "texture": mat_stems[si] if si < len(mat_stems) else (
                                  mat_stems[0] if mat_stems else None)})
        meshes.append({"name": mesh["name"], "verts": verts,
                       "normals": normals if src_normals else None,
                       "uvs": mesh["uvs"], "submeshes": subs})

    if textures is None:
        # stems live under the PREFAB
        textures = extract._read_textures(c["bundle"], c["prefab_id"], texture_stems)
        extract._swap_alt_outfit_textures(c["geo"], c["geo_id"], c["bundle"], textures)
    return {"geo": c["geo"], "geo_id": c["geo_id"], "type_int": c["type_int"],
            "bones": c["bones"], "meshes": meshes, "materials": materials, "textures": textures}


def _gather_triangles(model: dict):
    """Model struct -> a flat triangle list [(v0,v1,v2, uv0,uv1,uv2, normal_mean, tex_stem)], with
    verts/uvs still in model space. One entry per triangle across every mesh + submesh."""
    materials = model.get("materials", [])
    tris = []
    for mesh in model.get("meshes", []):
        verts, uvs = mesh["verts"], mesh.get("uvs") or []
        normals = mesh.get("normals")
        for sub in mesh.get("submeshes", []):
            mi = sub.get("material_idx")
            stem = None
            if mi is not None and 0 <= mi < len(materials):
                stem = materials[mi].get("texture")
            for t in sub.get("tris", []):
                i0, i1, i2 = t[0], t[1], t[2]
                if max(i0, i1, i2) >= len(verts):
                    continue
                uv = [(uvs[i] if i < len(uvs) else [0.0, 0.0]) for i in (i0, i1, i2)]
                if normals:
                    n = [(normals[i0][k] + normals[i1][k] + normals[i2][k]) / 3.0 for k in range(3)]
                else:
                    n = [0.0, -1.0, 0.0]
                tris.append((verts[i0], verts[i1], verts[i2], uv[0], uv[1], uv[2], n, stem))
    return tris


def _shade_of(normal, R, *, ambient=0.55) -> int:
    """Flat lambert with abs(dot) (FF9 materials are double-sided) -> a 0..255 gray."""
    n = _mat_vec(R, normal)
    ln = math.sqrt(n[0] * n[0] + n[1] * n[1] + n[2] * n[2]) or 1.0
    # light from the upper-left-front of the viewer (Y-down: 'up' is -Y, 'toward viewer' is -Z)
    lx, ly, lz = -0.37, -0.61, -0.70
    d = abs(n[0] * lx + n[1] * ly + n[2] * lz) / ln
    return max(0, min(255, int(255.0 * (ambient + (1.0 - ambient) * d))))


def _affine_screen_to_tex(s, t):
    """Solve the 2x3 affine mapping screen pts s[0..2] -> texture pts t[0..2]; None if degenerate.
    Returns PIL ``Image.transform`` coefficients (a,b,c,d,e,f): out(x,y) samples tex(ax+by+c, dx+ey+f)."""
    (x0, y0), (x1, y1), (x2, y2) = s
    det = (x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)
    if abs(det) < 1e-9:
        return None

    def solve(v0, v1, v2):
        # Cramer on [[x0,y0,1],[x1,y1,1],[x2,y2,1]] @ [p,q,r]^T = [v0,v1,v2]^T
        p = (v0 * (y1 - y2) - y0 * (v1 - v2) + (v1 * y2 - v2 * y1)) / det
        q = (x0 * (v1 - v2) - v0 * (x1 - x2) + (x1 * v2 - x2 * v1)) / det
        r = (x0 * (y1 * v2 - y2 * v1) - y0 * (x1 * v2 - x2 * v1) + v0 * (x1 * y2 - x2 * y1)) / det
        return p, q, r
    a, b, c = solve(t[0][0], t[1][0], t[2][0])
    d, e, f = solve(t[0][1], t[1][1], t[2][1])
    return (a, b, c, d, e, f)


def projected_bounds(model: dict, *, yaw: float = DEFAULT_YAW, pitch: float = DEFAULT_PITCH):
    """``(minx, maxx, miny, maxy)`` of a struct's drawn triangle corners under the SAME rotation
    :func:`render_model` uses -- i.e. the box that call would auto-fit to. None for an empty model.

    This is the unit of :func:`render_model`'s ``fit=``: a clip's frames each fit differently (a walk
    cycle's silhouette breathes), so an animated preview unions these across every posed frame and
    renders them all against the one box, or the model visibly pulses and drifts frame to frame."""
    tris = _gather_triangles(model)
    if not tris:
        return None
    R = _mat_mul(_rot_x(pitch), _rot_y(yaw))
    xs, ys = [], []
    for t in tris:
        for v in t[:3]:
            p = _mat_vec(R, v)
            xs.append(p[0]); ys.append(p[1])
    return (min(xs), max(xs), min(ys), max(ys)) if xs else None


def render_model(model: dict, *, size: int = 256, yaw: float = DEFAULT_YAW,
                 pitch: float = DEFAULT_PITCH, shade: bool = True, margin: float = 0.07,
                 supersample: int = 2, fit=None):
    """A :func:`~ff9mapkit.models.extract.read_model` struct -> an RGBA ``PIL.Image`` preview.

    Orthographic 3/4 view on a transparent background, textured where the model carries textures
    (flat gray where not). ``yaw``/``pitch`` orbit the model; ``supersample`` renders at Nx and
    downscales (the antialiasing). Pure CPU; a character model renders in well under a second.

    ``fit`` overrides the auto-fit box with a caller's ``(minx, maxx, miny, maxy)`` in the same rotated
    space :func:`projected_bounds` reports -- the STABLE-FRAMING lever an animated preview needs
    (default None auto-fits this call's own verts, exactly as before).
    """
    from PIL import Image, ImageChops, ImageDraw

    ss = max(1, int(supersample))
    W = size * ss
    tris = _gather_triangles(model)
    if not tris:
        return Image.new("RGBA", (size, size), (0, 0, 0, 0))

    R = _mat_mul(_rot_x(pitch), _rot_y(yaw))
    # transform per triangle corner (verts repeat across tris; a per-mesh vert cache would save
    # ~2/3 of the work but the totals are tiny -- keep it simple)
    xf = [(_mat_vec(R, t[0]), _mat_vec(R, t[1]), _mat_vec(R, t[2])) + t[3:] for t in tris]

    xs = [p[0] for t in xf for p in t[:3]]
    ys = [p[1] for t in xf for p in t[:3]]
    if not xs:
        return Image.new("RGBA", (size, size), (0, 0, 0, 0))
    minx, maxx, miny, maxy = fit if fit is not None else (min(xs), max(xs), min(ys), max(ys))
    span = max(maxx - minx, maxy - miny) or 1.0
    scale = W * (1.0 - 2.0 * margin) / span
    # centre the model in the canvas (Y-down model space maps straight onto image rows)
    offx = (W - (maxx - minx) * scale) / 2.0 - minx * scale
    offy = (W - (maxy - miny) * scale) / 2.0 - miny * scale

    def to_screen(p):
        return (p[0] * scale + offx, p[1] * scale + offy)

    # painter: camera looks down +Z, so a LARGER mean z is FARTHER -- draw it first
    order = sorted(range(len(xf)), key=lambda i: -(xf[i][0][2] + xf[i][1][2] + xf[i][2][2]))

    textures = {}
    for stem, im in (model.get("textures") or {}).items():
        try:
            textures[stem] = im.convert("RGBA")
        except Exception:
            pass

    color = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    shade_buf = Image.new("L", (W, W), 255) if shade else None
    shade_draw = ImageDraw.Draw(shade_buf) if shade_buf is not None else None

    for i in order:
        p0, p1, p2, uv0, uv1, uv2, normal, stem = xf[i]
        s = [to_screen(p0), to_screen(p1), to_screen(p2)]
        area2 = (s[1][0] - s[0][0]) * (s[2][1] - s[0][1]) - (s[2][0] - s[0][0]) * (s[1][1] - s[0][1])
        if abs(area2) < 1e-3:
            continue
        bx0 = max(0, int(math.floor(min(pt[0] for pt in s))))
        by0 = max(0, int(math.floor(min(pt[1] for pt in s))))
        bx1 = min(W, int(math.ceil(max(pt[0] for pt in s))) + 1)
        by1 = min(W, int(math.ceil(max(pt[1] for pt in s))) + 1)
        bw, bh = bx1 - bx0, by1 - by0
        if bw <= 0 or bh <= 0:
            continue
        local = [(pt[0] - bx0, pt[1] - by0) for pt in s]

        tex = textures.get(stem)
        if tex is not None:
            tw, th = tex.size
            # Unity wraps (REPEAT); some models author UVs a whole tile off -> translate the
            # triangle back by the integer tile of its minimum (preserves intra-triangle deltas)
            du = math.floor(min(uv0[0], uv1[0], uv2[0]))
            dv = math.floor(min(uv0[1], uv1[1], uv2[1]))
            # Unity UV origin is bottom-left; PIL rows count from the top -> v flips. UV 0..1 spans
            # the full pixel GRID (u*tw, then PIL's NEAREST floors to the texel), clamped a hair
            # under the top edge so u=1 stays in bounds.
            tpts = [(min(max((u - du) * tw, 0.0), tw - 1e-3),
                     min(max((1.0 - (v - dv)) * th, 0.0), th - 1e-3)) for (u, v) in (uv0, uv1, uv2)]
            coeffs = _affine_screen_to_tex(local, tpts)
            if coeffs is None:
                continue
            patch = tex.transform((bw, bh), Image.AFFINE, coeffs, resample=Image.NEAREST)
            mask = Image.new("L", (bw, bh), 0)
            ImageDraw.Draw(mask).polygon(local, fill=255)
            mask = ImageChops.multiply(mask, patch.getchannel("A"))
            color.paste(patch, (bx0, by0), mask)
        else:
            mask = Image.new("L", (bw, bh), 0)
            ImageDraw.Draw(mask).polygon(local, fill=255)
            flat = Image.new("RGBA", (bw, bh), (152, 152, 164, 255))
            color.paste(flat, (bx0, by0), mask)

        if shade_draw is not None:
            shade_draw.polygon(s, fill=_shade_of(normal, R))

    if shade_buf is not None:
        rgb = ImageChops.multiply(color.convert("RGB"), Image.merge("RGB", (shade_buf,) * 3))
        color = Image.merge("RGBA", (*rgb.split(), color.getchannel("A")))
    if ss > 1:
        color = color.resize((size, size), Image.LANCZOS)
    return color


def render_token(token: str, *, game=None, bundle=None, pose: bool = True, env5=None, **kw):
    """Convenience: a GEO name / model id -> a rendered preview (reads the install).

    Pass a shared ``bundle`` (p0data4) and ``env5`` (p0data5) when rendering many models."""
    return render_model(_skinned_struct(token, game=game, bundle=bundle, pose=pose, env5=env5), **kw)
