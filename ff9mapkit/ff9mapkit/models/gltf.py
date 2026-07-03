"""Export a FF9 model + its animations to a glTF 2.0 ``.glb`` -- a BLENDER-OPENABLE file (the edit loop's
forward half). Blender can't read the engine-facing FBX-ASCII, and Hades Workshop / AssetStudio either
mangle the mesh or drop the animations; this produces a clean, self-contained ``.glb`` with the skeleton,
skin, textures, AND the model's idle/walk/run clips so a modder can open + scrub + edit it.

Reuses ``extract.read_model`` for geometry (verts are already bind-corrected -- the per-mesh bake G lives in
the vertices, so the glTF skin's inverseBindMatrices are purely rest-derived and one-per-joint) and
``_gltf_io`` for the coordinate-independent binary/animation machinery. The only convention this file owns is
the FF9 (left-handed, Y-DOWN) -> glTF (right-handed, Y-up) change, which is a single-axis mirror: **negate Y**.
"""
from __future__ import annotations

from pathlib import Path

from .. import catalog, config
from . import extract, _gltf_io
from ._gltf_io import GltfBuffer, FLOAT, UNSIGNED_INT, UNSIGNED_SHORT, ARRAY_BUFFER, ELEMENT_ARRAY_BUFFER
from .fbx_skin import _mat_trs, _mat_mul, _mat_inv

DEFAULT_SCALE = 0.01                # FF9 models are ~hundreds of units tall; 0.01 -> a Blender-friendly few metres
DEFAULT_ACTIONS = ("idle", "walk", "run", "turn_l", "turn_r")


# ---------------------------------------------------------------- FF9 -> glTF(RH,Y-up): negate Y
#
# FF9's engine world is effectively Y-DOWN (the model's "up" is toward -Y -- Vivi's head sits at min-Y; cf.
# the walkmesh's `-worldY` and the canvas Y-inversion). glTF/Blender want RIGHT-handed **Y-UP**. A single-axis
# **negate-Y** mirror does BOTH at once: it flips Y-down->Y-up (model stands upright) AND flips handedness
# (LH->RH). (A negate-X mirror -- the mainstream Unity->glTF convention for Y-UP source models -- would leave
# FF9 upside-down.) det = -1, so triangle winding is reversed at emit (see the primitive loop).

def _cpos(v, s):
    """Position / bone translation: mirror Y (FF9 Y-down -> glTF Y-up), apply the uniform scale bake."""
    return [v[0] * s, -v[1] * s, v[2] * s]


def _cnrm(v):
    """Normal: mirror Y, no scale."""
    return [v[0], -v[1], v[2]]


def _cquat(q):
    """Rotation quaternion (x,y,z,w) under a negate-Y coordinate mirror -> (-x,y,-z,w) (keep the flipped
    axis' component (y) + w, negate the two perpendicular components (x,z)). The load-bearing remap."""
    return [-q[0], q[1], -q[2], q[3]]


def _mat4_colmajor(m):
    """A row-major 4x4 (list-of-rows) -> glTF's column-major flat 16."""
    return [m[r][c] for c in range(4) for r in range(4)]


def _sign_continuous(quats):
    """Flip the sign of any quaternion whose dot with the previous one is negative (same rotation, but keeps
    neighbours in one hemisphere so a glTF viewer's slerp/nlerp doesn't take the 360-degree long way)."""
    out = []
    prev = None
    for q in quats:
        if prev is not None and sum(a * b for a, b in zip(q, prev)) < 0.0:
            q = [-c for c in q]
        out.append(q)
        prev = q
    return out


# ---------------------------------------------------------------- animation clip selection

def _select_anim_keys(geo, geo_id, anims, p0d5_env):
    """Resolve which clips to embed -> [(action_label, animKey)] present on disc. ``anims`` is 'auto' (the
    model's named idle/walk/run/turn clips, topped up from its own folder so a model whose catalog ids don't
    line up with the on-disc keys still animates), 'all' (every clip in its folder), 'none', or a comma/space
    list of action labels / raw anim ids.

    Note: FF9's action->animKey map isn't always the on-disc key (the engine redirects name->folder->key via
    AnimationDB + GetRenameAnimationDirectory), so a labelled action may miss on disc; the top-up covers it."""
    if anims in (None, "none", "off"):
        return []
    on_disc = sorted({int(k.lower().split("/")[-1].removesuffix(".anim"))
                      for k, p in p0d5_env.container.items()
                      if p.type.name == "AnimationClip" and f"/animations/{geo_id}/" in k.lower()})
    on_disc_set = set(on_disc)
    actions = catalog.animations_for_model(geo) or {}          # {action_label: anim_id}
    picked: list = []
    if anims == "all":
        picked = [(str(k), k) for k in on_disc]
    elif anims in ("auto", "", "default"):
        for act in DEFAULT_ACTIONS:
            aid = actions.get(act)
            if aid is not None and aid in on_disc_set:
                picked.append((act, aid))
        if len({a for _, a in picked}) < 3:                    # thin/mismatched catalog -> top up from the folder
            seen = {a for _, a in picked}
            for aid in on_disc:
                if len(picked) >= 4:
                    break
                if aid not in seen:
                    picked.append((str(aid), aid))
                    seen.add(aid)
    else:
        toks = [t for t in str(anims).replace(",", " ").split() if t]
        for t in toks:
            if t.isdigit() and int(t) in on_disc_set:
                picked.append((t, int(t)))
            elif t in actions and actions[t] in on_disc_set:
                picked.append((t, actions[t]))
    # de-dup by animKey, keep first label
    seen, out = set(), []
    for lbl, aid in picked:
        if aid not in seen:
            seen.add(aid)
            out.append((lbl, aid))
    return out


# ---------------------------------------------------------------- exporter

def export_gltf(token: str, out_path, *, anims="auto", scale: float = DEFAULT_SCALE, game=None) -> dict:
    """Write a ``.glb`` for ``token`` (GEO name or id) at ``out_path``. Returns a manifest (counts + anims)."""
    model = extract.read_model(token, game=game)
    bones = model["bones"]
    meshes = model["meshes"]
    materials = model["materials"]
    s = float(scale)

    # bone bookkeeping: node index (bones first, then the mesh node), joint index (position in skin.joints),
    # bone NUMBER -> joint index (weights are keyed by FF9 bone number).
    by_name = {b["name"]: b for b in bones}
    node_of = {b["name"]: i for i, b in enumerate(bones)}       # bone name -> glTF node index
    mesh_node = len(bones)
    joint_of_num = {extract._bone_num(b["name"]): i for i, b in enumerate(bones)}
    children = {b["name"]: [] for b in bones}
    for b in bones:
        if b["parent"] is not None and b["parent"] in children:
            children[b["parent"]].append(node_of[b["name"]])

    # converted rest world matrix per bone (for inverseBindMatrices; Path A -- recompute from converted nodes)
    _wcache: dict = {}

    def world(name):
        if name in _wcache:
            return _wcache[name]
        b = by_name[name]
        local = _mat_trs(_cpos(b["pos"], s), _cquat(b["rot"]), b["scale"])
        _wcache[name] = local if b["parent"] is None else _mat_mul(world(b["parent"]), local)
        return _wcache[name]

    buf = GltfBuffer()

    # --- skin: joints + inverseBindMatrices ---
    ibm_flat: list = []
    for b in bones:
        ibm_flat += _mat4_colmajor(_mat_inv(world(b["name"])))
    ibm_acc = buf.add(ibm_flat, FLOAT, "MAT4")
    skin = {"joints": [node_of[b["name"]] for b in bones], "inverseBindMatrices": ibm_acc,
            "skeleton": node_of[model["root_bone"]]}

    # --- nodes: bones (TRS + children) then the mesh node (mesh + skin) ---
    nodes: list = []
    for b in bones:
        n = {"name": b["name"]}
        t = _cpos(b["pos"], s)
        r = _cquat(b["rot"])
        sc = b["scale"]
        if any(abs(v) > 1e-9 for v in t):
            n["translation"] = t
        if any(abs(v) > 1e-9 for v in (r[0], r[1], r[2])) or abs(r[3] - 1.0) > 1e-9:
            n["rotation"] = r
        if any(abs(v - 1.0) > 1e-9 for v in sc):
            n["scale"] = list(sc)
        if children[b["name"]]:
            n["children"] = children[b["name"]]
        nodes.append(n)
    nodes.append({"name": "Mesh", "mesh": 0, "skin": 0})

    # --- textures / materials (embed PNGs into the buffer as image bufferViews) ---
    img_of_stem: dict = {}
    gltf_images: list = []
    gltf_textures: list = []
    gltf_materials: list = []
    for mat in materials:
        stem = mat.get("texture")
        tex_index = None
        if stem is not None:
            if stem not in img_of_stem:
                img = model["textures"].get(stem)
                if img is not None:
                    import io
                    bio = io.BytesIO()
                    img.save(bio, format="PNG")
                    view = buf._view(bio.getvalue())            # raw PNG bytes as a bufferView
                    gltf_images.append({"name": stem, "bufferView": view, "mimeType": "image/png"})
                    gltf_textures.append({"source": len(gltf_images) - 1, "sampler": 0})
                    img_of_stem[stem] = len(gltf_textures) - 1
                else:
                    img_of_stem[stem] = None
            tex_index = img_of_stem[stem]
        pbr = {"metallicFactor": 0.0, "roughnessFactor": 1.0}
        if tex_index is not None:
            pbr["baseColorTexture"] = {"index": tex_index, "texCoord": 0}
        gltf_materials.append({"name": mat["name"], "pbrMetallicRoughness": pbr,
                               "alphaMode": "MASK", "alphaCutoff": 0.5, "doubleSided": True})

    # --- mesh primitives (one per submesh; verts already bake-corrected -> emit verbatim, converted) ---
    primitives: list = []
    warnings: list = []
    for mi, me in enumerate(meshes):
        if model.get("per_mesh_bind") and mi < len(model["per_mesh_bind"]) and model["per_mesh_bind"][mi] is None \
                and me["weights"]:
            warnings.append(f"mesh {me['name']!r} had no bind correction (per-bone variation) -- it may be "
                            f"mis-oriented in the glTF (rare; see docs)")
        pos_flat, nrm_flat, uv_flat, joints_flat, weights_flat = [], [], [], [], []
        has_n = bool(me.get("normals"))
        for vi, v in enumerate(me["verts"]):
            pos_flat += _cpos(v, s)
            if has_n:
                nrm_flat += _cnrm(me["normals"][vi])
            uv = me["uvs"][vi] if vi < len(me["uvs"]) else [0.0, 0.0]
            uv_flat += [uv[0], 1.0 - uv[1]]                     # glTF UV origin is top-left
            infl = sorted(me["weights"][vi], key=lambda t: -t[1])[:4]   # keep top-4 by weight (engine caps at 4)
            js = [joint_of_num.get(bn, 0) for bn, _ in infl]
            ws = [w for _, w in infl]
            while len(js) < 4:
                js.append(0)
                ws.append(0.0)
            tot = sum(ws) or 1.0
            joints_flat += js
            weights_flat += [w / tot for w in ws]
        pos_acc = buf.add(pos_flat, FLOAT, "VEC3", target=ARRAY_BUFFER, minmax=True)
        attrs = {"POSITION": pos_acc}
        if has_n:
            attrs["NORMAL"] = buf.add(nrm_flat, FLOAT, "VEC3", target=ARRAY_BUFFER)
        attrs["TEXCOORD_0"] = buf.add(uv_flat, FLOAT, "VEC2", target=ARRAY_BUFFER)
        attrs["JOINTS_0"] = buf.add(joints_flat, UNSIGNED_SHORT, "VEC4", target=ARRAY_BUFFER)
        attrs["WEIGHTS_0"] = buf.add(weights_flat, FLOAT, "VEC4", target=ARRAY_BUFFER)
        for sub in me["submeshes"]:
            idx = []
            for a, b2, c in sub["tris"]:
                idx += [a, c, b2]                              # reverse winding (negate-X flips handedness)
            idx_acc = buf.add(idx, UNSIGNED_INT, "SCALAR", target=ELEMENT_ARRAY_BUFFER)
            prim = {"attributes": attrs, "indices": idx_acc, "mode": 4}
            if sub["material_idx"] < len(gltf_materials):
                prim["material"] = sub["material_idx"]
            primitives.append(prim)

    # --- animations ---
    p0d5 = config.find_game_path(game) / "StreamingAssets" / "p0data5.bin"
    env5 = extract._unitypy().load(str(p0d5))
    selected = _select_anim_keys(model["geo"], model["geo_id"], anims, env5)
    gltf_anims: list = []
    anim_labels: list = []
    for label, key in selected:
        clip = _gltf_io.read_clip(env5, model["geo_id"], key)
        if not clip or not clip["bones"]:
            continue
        samplers, channels = [], []
        for path, ch in clip["bones"].items():
            bnum = extract._bone_num(path.split("/")[-1])
            if bnum not in joint_of_num:
                continue
            node = node_of[by_name.get(f"bone{bnum:03d}", {}).get("name", "")] if f"bone{bnum:03d}" in by_name else None
            if node is None:
                continue
            # rotation channel (the animated one)
            rot = ch.get("rot")
            if rot and len(rot) >= 2:
                times = [t for t, _ in rot]
                quats = _sign_continuous([_cquat(list(q)) for _, q in rot])
                tin = buf.add(times, FLOAT, "SCALAR", minmax=True)
                rout = buf.add([c for q in quats for c in q], FLOAT, "VEC4")
                samplers.append({"input": tin, "output": rout, "interpolation": "LINEAR"})
                channels.append({"sampler": len(samplers) - 1, "target": {"node": node, "path": "rotation"}})
            # position channel -- only where it actually moves (root walk translation); skip 2-key constants
            pos = ch.get("pos")
            if pos and len(pos) > 2:
                times = [t for t, _ in pos]
                pout = [c for _, p in pos for c in _cpos(list(p), s)]
                tin = buf.add(times, FLOAT, "SCALAR", minmax=True)
                pacc = buf.add(pout, FLOAT, "VEC3")
                samplers.append({"input": tin, "output": pacc, "interpolation": "LINEAR"})
                channels.append({"sampler": len(samplers) - 1, "target": {"node": node, "path": "translation"}})
        if channels:
            gltf_anims.append({"name": label, "samplers": samplers, "channels": channels})
            anim_labels.append(label)

    # --- assemble ---
    gltf = {
        "scene": 0,
        "scenes": [{"nodes": [node_of[model["root_bone"]], mesh_node]}],
        "nodes": nodes,
        "meshes": [{"name": model["geo"], "primitives": primitives}],
        "skins": [skin],
        "materials": gltf_materials,
        "samplers": [{"magFilter": 9728, "minFilter": 9728, "wrapS": 10497, "wrapT": 10497}],
        "accessors": buf.accessors,
        "bufferViews": buf.bufferViews,
    }
    if gltf_images:
        gltf["images"] = gltf_images
        gltf["textures"] = gltf_textures
    if gltf_anims:
        gltf["animations"] = gltf_anims

    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    _gltf_io.write_glb(gltf, buf.blob, out)
    return {"geo": model["geo"], "geo_id": model["geo_id"], "path": str(out),
            "bones": len(bones), "meshes": len(meshes), "primitives": len(primitives),
            "verts": sum(len(m["verts"]) for m in meshes), "textures": len(gltf_images),
            "anims": anim_labels, "scale": s, "warnings": warnings}
