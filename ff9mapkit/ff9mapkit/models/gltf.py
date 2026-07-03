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

import re
from pathlib import Path

from .. import catalog, config
from . import extract, _gltf_io, fbx_skin
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

def export_gltf(token: str, out_path, *, anims="auto", scale: float = DEFAULT_SCALE, game=None, _model=None) -> dict:
    """Write a ``.glb`` for ``token`` (GEO name or id) at ``out_path``. Returns a manifest (counts + anims).
    ``_model`` is an internal hook to pass a pre-read struct (bulk sweeps) and skip the p0data4 read."""
    model = _model if _model is not None else extract.read_model(token, game=game)
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
    # Name the mesh node + carry the source stamp in NODE extras too (Blender preserves node extras as object
    # custom properties + round-trips them on export, and keeps object/mesh NAMES -- unlike asset.extras, which
    # Blender drops -- so `model-import` can auto-detect the source even after a Blender edit).
    nodes.append({"name": model["geo"], "mesh": 0, "skin": 0,
                  "extras": {"ff9_geo": model["geo"], "ff9_geo_id": model["geo_id"], "ff9_scale": s}})

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

    # --- animations (skip the p0data5 load entirely when no clips are wanted) ---
    selected = []
    if anims not in (None, "none", "off"):
        env5 = extract._unitypy().load(str(config.find_game_path(game) / "StreamingAssets" / "p0data5.bin"))
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
        # stamp the source model + scale so `model-import` can auto-detect them (no need to retype --like)
        "asset": {"version": "2.0", "generator": "ff9mapkit",
                  "extras": {"ff9_geo": model["geo"], "ff9_geo_id": model["geo_id"], "ff9_scale": s}},
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


# ================================================================ RETURN path: glTF -> kit Model struct
# The inverse of the forward conversion. negate-Y is an involution, so the axis flip is the SAME op; only the
# uniform scale un-bakes (divide by S) and the winding/UV flips reverse (they're also self-inverse).

def _icpos(v, s):
    return [v[0] / s, -v[1] / s, v[2] / s]


def _icnrm(v):
    return [v[0], -v[1], v[2]]


def _icquat(q):
    return [-q[0], q[1], -q[2], q[3]]


def _node_local_trs(node):
    """A glTF node's local (translation, rotation xyzw, scale). Decomposes ``matrix`` if present (else TRS)."""
    if "matrix" in node:
        import math
        m = node["matrix"]                                   # column-major 16
        col = [[m[c * 4 + r] for r in range(4)] for c in range(4)]
        t = [col[3][0], col[3][1], col[3][2]]
        sx = math.sqrt(sum(col[0][k] ** 2 for k in range(3))) or 1.0
        sy = math.sqrt(sum(col[1][k] ** 2 for k in range(3))) or 1.0
        sz = math.sqrt(sum(col[2][k] ** 2 for k in range(3))) or 1.0
        R = [[col[0][0] / sx, col[1][0] / sy, col[2][0] / sz],
             [col[0][1] / sx, col[1][1] / sy, col[2][1] / sz],
             [col[0][2] / sx, col[1][2] / sy, col[2][2] / sz]]
        tr = R[0][0] + R[1][1] + R[2][2]
        if tr > 0:
            w = math.sqrt(tr + 1.0) * 0.5
            x = (R[2][1] - R[1][2]) / (4 * w); y = (R[0][2] - R[2][0]) / (4 * w); z = (R[1][0] - R[0][1]) / (4 * w)
        else:
            i = max(range(3), key=lambda k: R[k][k])
            j, k = (i + 1) % 3, (i + 2) % 3
            sN = math.sqrt(1.0 + R[i][i] - R[j][j] - R[k][k]) * 2.0
            q = [0.0, 0.0, 0.0, 0.0]
            q[3] = (R[k][j] - R[j][k]) / sN
            q[i] = 0.25 * sN
            q[j] = (R[j][i] + R[i][j]) / sN
            q[k] = (R[k][i] + R[i][k]) / sN
            x, y, z, w = q
        return t, [x, y, z, w], [sx, sy, sz]
    return (list(node.get("translation", [0.0, 0.0, 0.0])),
            list(node.get("rotation", [0.0, 0.0, 0.0, 1.0])),
            list(node.get("scale", [1.0, 1.0, 1.0])))


def import_gltf(path, *, scale: float = DEFAULT_SCALE) -> dict:
    """Parse a glTF ``.glb``/``.gltf`` back into the kit's Model struct (the shape ``fbx_skin.emit_skinned_fbx``
    consumes), applying the inverse (negate-Y, /scale) conversion. Full round-trip: skeleton + skin + mesh.

    Skeleton nodes MUST be named ``boneNNN`` (the kit's bone-number key); a skin joint that isn't fails loud.
    Weights are re-keyed to FF9 bone NUMBER via the joint->node->name map, pruned + capped at 4."""
    s = float(scale)
    gltf, blob = _gltf_io.read_glb(path)
    nodes = gltf.get("nodes", [])
    skins = gltf.get("skins", [])
    if not skins:
        raise ValueError("glTF has no skin -- this importer expects a skinned FF9 model (armature + mesh)")
    skin = skins[0]
    joints = skin["joints"]

    parent_of = {}
    for ni, node in enumerate(nodes):
        for ch in node.get("children", []) or []:
            parent_of[ch] = ni
    name_of = {ni: nodes[ni].get("name", f"node{ni}") for ni in range(len(nodes))}

    def bone_name(ni):
        nm = name_of[ni]
        if not re.fullmatch(r"bone\d+", str(nm)):
            raise ValueError(f"glTF skin joint node {nm!r} isn't named boneNNN -- can't map it to an FF9 bone. "
                             f"Rename armature bones back to bone000.. (don't rename/add non-FF9 bones).")
        return nm

    joint_set = set(joints)
    bones = []
    for ni in joints:
        nm = bone_name(ni)
        p = parent_of.get(ni)
        parent_name = bone_name(p) if (p is not None and p in joint_set) else None    # a non-joint parent -> root
        t, q, sc = _node_local_trs(nodes[ni])
        bones.append({"name": nm, "parent": parent_name,
                      "pos": _icpos(t, s), "rot": _icquat(q), "scale": sc})
    root_bone = next((b["name"] for b in bones if b["parent"] is None), bones[0]["name"] if bones else None)
    num_of_joint = {j: extract._bone_num(bone_name(joints[j])) for j in range(len(joints))}

    # materials: glTF material -> {name, texture stem} (recovered from the base-color image name)
    gmats = gltf.get("materials", [])
    gtex = gltf.get("textures", [])
    gimg = gltf.get("images", [])

    def mat_stem(gi):
        try:
            ti = gmats[gi]["pbrMetallicRoughness"]["baseColorTexture"]["index"]
            return gimg[gtex[ti]["source"]].get("name")
        except Exception:
            return None

    # group primitives by POSITION accessor -> one kit mesh per distinct vertex set
    meshes, materials = [], []
    by_pos: dict = {}
    for gm in gltf.get("meshes", []):
        for prim in gm.get("primitives", []):
            by_pos.setdefault(prim["attributes"]["POSITION"], []).append(prim)
    for pos_acc, prims in by_pos.items():
        p0 = prims[0]
        verts = [_icpos(v, s) for v in _gltf_io.decode_accessor(gltf, blob, pos_acc)]
        attrs = p0["attributes"]
        normals = [_icnrm(n) for n in _gltf_io.decode_accessor(gltf, blob, attrs["NORMAL"])] \
            if "NORMAL" in attrs else None
        uvs = [[u, 1.0 - v] for u, v in _gltf_io.decode_accessor(gltf, blob, attrs["TEXCOORD_0"])] \
            if "TEXCOORD_0" in attrs else [[0.0, 0.0]] * len(verts)
        weights = [[0, 0.0]] * len(verts)
        if "JOINTS_0" in attrs and "WEIGHTS_0" in attrs:
            J = _gltf_io.decode_accessor(gltf, blob, attrs["JOINTS_0"])
            W = _gltf_io.decode_accessor(gltf, blob, attrs["WEIGHTS_0"])
            weights = []
            for jv, wv in zip(J, W):
                infl = [(num_of_joint.get(int(j), 0), float(w)) for j, w in zip(jv, wv) if w > 0.0]
                tot = sum(w for _, w in infl) or 1.0
                weights.append([(bn, w / tot) for bn, w in infl])
        subs = []
        for prim in prims:
            base_mat = len(materials)
            idx = [int(x[0]) for x in _gltf_io.decode_accessor(gltf, blob, prim["indices"])]
            tris = [[idx[i], idx[i + 2], idx[i + 1]] for i in range(0, len(idx) - 2, 3)]   # un-reverse winding
            subs.append({"material_idx": base_mat, "tris": tris})
            materials.append({"name": f"mat{base_mat}", "texture": mat_stem(prim.get("material", -1))})
        meshes.append({"name": gltf["meshes"][0].get("name", "mesh"), "verts": verts,
                       "normals": normals, "uvs": uvs, "submeshes": subs, "weights": weights})

    # embedded images -> PIL, keyed by the same stem the materials reference (self-consistent for re-emit)
    textures = {}
    for img in gltf.get("images", []) or []:
        stem = img.get("name")
        raw = None
        if "bufferView" in img:
            bv = gltf["bufferViews"][img["bufferView"]]
            o = bv.get("byteOffset", 0)
            raw = blob[o:o + bv["byteLength"]]
        elif str(img.get("uri", "")).startswith("data:"):
            import base64
            raw = base64.b64decode(img["uri"].split(",", 1)[1])
        if stem and raw:
            try:
                from PIL import Image
                import io
                textures[stem] = Image.open(io.BytesIO(raw))
            except Exception:
                pass

    return {"geo": None, "geo_id": None, "type_int": None, "root_bone": root_bone,
            "bones": bones, "meshes": meshes, "materials": materials, "textures": textures}


class TopologyMismatch(ValueError):
    """The edited glTF's vertex/mesh topology differs from the source (Blender commonly seam-splits verts on
    export) -- the v1 mesh-splice can't map onto the original weights; deploy_edit falls back to the re-rig."""


def apply_gltf_edit(source_token: str, path, *, scale: float = DEFAULT_SCALE, game=None) -> dict:
    """v1 (safest) return path: keep the ORIGINAL model's skeleton + per-vertex weights + textures, and splice
    in only the EDITED geometry (verts / normals / uvs) from the glTF. Guards that each mesh's vertex COUNT is
    unchanged (a retexture / reshape edit) -- adding/removing verts needs the full :func:`import_gltf` re-rig.
    Returns a Model struct ready for ``fbx_skin.emit_skinned_fbx``."""
    orig = extract.read_model(source_token, game=game)
    edited = import_gltf(path, scale=scale)
    if len(edited["meshes"]) != len(orig["meshes"]):
        raise TopologyMismatch(f"glTF has {len(edited['meshes'])} mesh(es) but {orig['geo']} has "
                               f"{len(orig['meshes'])} -- mesh split differs")
    for i, (om, em) in enumerate(zip(orig["meshes"], edited["meshes"])):
        if len(em["verts"]) != len(om["verts"]):
            raise TopologyMismatch(f"mesh #{i} ({om['name']}): glTF has {len(em['verts'])} verts, original has "
                                   f"{len(om['verts'])} (Blender seam-splits verts) -- vertex count changed")
        om["verts"] = em["verts"]                            # splice edited geometry onto the original rig
        if em["normals"]:
            om["normals"] = em["normals"]
        om["uvs"] = em["uvs"]
    return orig


def _emit_model_to(model: dict, dest_dir, geo_id: int) -> dict:
    """Emit a Model struct as the engine-facing skinned FBX-ASCII + its textures into ``dest_dir`` (the target
    ``Models/{type}/{id}/`` folder). ``fbx_skin.emit_skinned_fbx``'s euler self-check + validate gate applies."""
    text, meta = fbx_skin.emit_skinned_fbx(model)
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"{geo_id}.fbx").write_text(text, encoding="ascii", newline="\n")
    saved = []
    for stem, img in (model.get("textures") or {}).items():
        img.save(str(dest / f"{stem}.png"))
        saved.append(f"{stem}.png")
    return {"fbx": str(dest / f"{geo_id}.fbx"), "textures": saved, "euler_max_err": meta["euler_max_err"]}


def source_from_gltf(path) -> tuple:
    """Detect the source model + export scale of a glTF WE produced -> (geo_name, scale|None), so
    ``model-import`` needs no --like. Robust to a Blender round-trip by checking, in order: ``asset.extras``
    (a raw un-edited file), any NODE's ``extras`` (Blender keeps node extras as object custom properties),
    then any mesh/node NAME that matches a real GEO name (Blender keeps names; a ``.001`` suffix is stripped).
    (None, None) for a foreign glTF with none of these."""
    try:
        gltf, _ = _gltf_io.read_glb(path)
    except Exception:
        return None, None
    ex = (gltf.get("asset") or {}).get("extras") or {}
    if ex.get("ff9_geo"):
        return ex["ff9_geo"], ex.get("ff9_scale")
    for node in gltf.get("nodes", []) or []:
        nex = node.get("extras") or {}
        if nex.get("ff9_geo"):
            return nex["ff9_geo"], nex.get("ff9_scale")
    for nm in ([m.get("name") for m in gltf.get("meshes", []) or []]
               + [n.get("name") for n in gltf.get("nodes", []) or []]):
        base = re.sub(r"\.\d+$", "", str(nm or ""))          # strip Blender's ".001" dedup suffix
        if base in extract._NAME_TO_ID:
            return base, None                                # name match -> scale unknown, falls back to 0.01
    return None, None


def deploy_edit(gltf_path, mod_folder, *, like=None, geo_id=None, scale=None, game=None) -> dict:
    """Bring a (Blender-edited) glTF back into the game: import it, emit the FBX + textures into ``mod_folder``
    at ``Models/{type}/{id}/`` (an override -- deletes to revert).

    If ``like`` is not given, the source model is AUTO-DETECTED from the glTF's ``asset.extras`` stamp (any
    file exported by ``model-gltf``), so a round-tripped edit needs no --like. ``like="<GEO>"`` uses the v1
    mesh-splice (keep the source's rig + textures, take only edited geometry -- vertex count must match); a
    glTF with no stamp AND no ``like`` falls back to a full re-rig (needs ``geo_id`` for the target id/type).
    ``geo_id`` overrides the target id (default: the source id -> a straight override; or a mint id >=6000)."""
    stamp_geo, stamp_scale = source_from_gltf(gltf_path)
    if like is None and geo_id is None and stamp_geo is not None:
        like = stamp_geo                                     # auto: a glTF we exported knows its own source
    if scale is None:
        scale = float(stamp_scale) if stamp_scale is not None else DEFAULT_SCALE

    if like:
        _geo, src_id, type_int = extract.resolve_geo(like)
        tid = int(geo_id) if geo_id is not None else src_id
        try:
            model = apply_gltf_edit(like, gltf_path, scale=scale, game=game)     # v1: pristine rig, splice geometry
            mode = "mesh-splice"
        except TopologyMismatch:
            # Blender changed the topology (seam-split verts) -> HYBRID re-rig: keep the pristine SKELETON +
            # id/type/textures, take the edited geometry + weights (keyed by FF9 bone number) from the glTF.
            edited = import_gltf(gltf_path, scale=scale)
            orig = extract.read_model(like, game=game)
            model = {"geo": orig["geo"], "geo_id": orig["geo_id"], "type_int": orig["type_int"],
                     "root_bone": orig["root_bone"], "bones": orig["bones"],
                     "meshes": edited["meshes"], "materials": edited["materials"],
                     "textures": edited["textures"] or orig["textures"]}
            mode = "re-rig (topology changed)"
    else:
        model = import_gltf(gltf_path, scale=scale)
        if geo_id is None:
            raise ValueError("a full re-rig import needs --id (the target model id + its type); pass --like <GEO> "
                             "or a glTF we exported (auto-detected) to keep an existing model's rig + type")
        nm = extract.MODELS.get(int(geo_id))
        type_int = extract._TYPE_INT.get(nm.split("_")[1].lower()) if nm else None
        if type_int is None:
            raise ValueError(f"can't derive the model type for id {geo_id} (not a known GEO id) -- use --like <GEO>")
        tid = int(geo_id)
        mode = "re-rig"

    dest = Path(mod_folder) / "StreamingAssets" / "Assets" / "Resources" / "Models" / str(type_int) / str(tid)
    info = _emit_model_to(model, dest, tid)
    return {"id": tid, "type_int": type_int, "mode": mode, "source": like, "path": info["fbx"],
            "textures": info["textures"]}
