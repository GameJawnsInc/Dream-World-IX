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
            # Prefer ON-FOOT locomotion clips (idle/stand/run/walk/turn) over mount/misc, and give every clip a
            # FRIENDLY label (its ANH action suffix) instead of a raw numeric id -- so an overworld WALKER like
            # Zidane comes in standing with readable Action names, not straddling an (absent) chocobo with clips
            # named "1143". (His lowest-id clips are the chocobo-RIDING ones -- disc order alone surfaced those.)
            seen = {a for _, a in picked}
            id_to_label = {aid: lbl for lbl, aid in actions.items()}
            # Neutral-rest first: 'stand' is the plain standing pose; 'idle1'/'idle2' are periodic FIDGETS
            # (e.g. Zidane's idle1 is a yawn), so they must not lead. Anything not listed sorts after (disc order).
            _ON_FOOT_ORDER = ("stand", "idle", "idle1", "idle2", "walk", "run", "turn", "turn_l", "turn_r")
            _onfoot_rank = {a: i for i, a in enumerate(_ON_FOOT_ORDER)}

            def _lbl(k):
                lbl = id_to_label.get(k)
                if lbl:
                    return lbl
                nm = catalog.animation_name(k)                 # ANH_SUB_W0_001_FLY_CHO -> "fly_cho"
                parts = nm.split("_") if nm else []
                return "_".join(parts[4:]).lower() if len(parts) >= 5 else str(k)

            rank = {k: i for i, k in enumerate(on_disc)}
            cand = [(_lbl(k), k) for k in on_disc if k not in seen]
            cand.sort(key=lambda lk: (_onfoot_rank.get(lk[0], len(_ON_FOOT_ORDER)), rank[lk[1]]))  # neutral-first
            for lbl, aid in cand:
                if len(picked) >= 4:
                    break
                picked.append((lbl, aid))
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

    # bone bookkeeping: node index (bones first, then the mesh nodes), joint index (position in skin.joints),
    # bone NUMBER -> joint index (weights are keyed by FF9 bone number).
    by_name = {b["name"]: b for b in bones}
    node_of = {b["name"]: i for i, b in enumerate(bones)}       # bone name -> glTF node index
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

    # --- mesh primitives: ONE named glTF mesh + node PER FF9 part (not one fused mesh) --------------------
    # Each FF9 SkinnedMeshRenderer (body / long_hair / rubber_band / short_hair / ...) becomes its own glTF
    # mesh + node, NAMED after the part, so Blender shows distinct editable objects. That (a) stops a
    # proportional-edit on one part from dragging a small neighbour (Garnet's 38-vert scrunchie sat fused to
    # the shoulder in the old single-mesh export), and (b) lets the return path match parts BY NAME (robust)
    # instead of a vertex-count heuristic. The engine's ModelFactory has NAME-keyed per-model branches
    # (Garnet's garnetShortHairTable does GetChildByName("long_hair"/"short_hair")), so part names are
    # load-bearing -- carry them faithfully. Each mesh node stamps ff9_geo/ff9_mesh in extras (Blender keeps
    # node extras as object custom properties + round-trips them), so `model-import` auto-detects the source.
    gltf_meshes: list = []
    mesh_nodes: list = []
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
        prims: list = []
        for sub in me["submeshes"]:
            idx = []
            for a, b2, c in sub["tris"]:
                idx += [a, c, b2]                              # reverse winding (negate-X flips handedness)
            idx_acc = buf.add(idx, UNSIGNED_INT, "SCALAR", target=ELEMENT_ARRAY_BUFFER)
            prim = {"attributes": attrs, "indices": idx_acc, "mode": 4}
            if sub["material_idx"] < len(gltf_materials):
                prim["material"] = sub["material_idx"]
            prims.append(prim)
        part = me.get("name") or f"mesh{mi}"
        gltf_meshes.append({"name": part, "primitives": prims})
        node_idx = len(nodes)
        nodes.append({"name": part, "mesh": mi, "skin": 0,
                      "extras": {"ff9_geo": model["geo"], "ff9_geo_id": model["geo_id"],
                                 "ff9_scale": s, "ff9_mesh": part}})
        mesh_nodes.append(node_idx)

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
            # scale channel -- mirror-invariant (no coord flip, no unit bake), emitted ONLY where it actually
            # varies (nearly every FF9 bone carries a CONSTANT scale curve; exporting those would bloat the
            # glTF + clutter Blender). So a modder can scrub + edit a real squash/stretch clip.
            scl = ch.get("scale")
            if scl and len(scl) >= 2:
                v0 = scl[0][1]
                if any(abs(c - c0) > 1e-4 for _, v in scl for c, c0 in zip(v, v0)):
                    times = [t for t, _ in scl]
                    sout = [c for _, v in scl for c in v]
                    tin = buf.add(times, FLOAT, "SCALAR", minmax=True)
                    sacc = buf.add(sout, FLOAT, "VEC3")
                    samplers.append({"input": tin, "output": sacc, "interpolation": "LINEAR"})
                    channels.append({"sampler": len(samplers) - 1, "target": {"node": node, "path": "scale"}})
        if channels:
            # Stamp the routing key so the return path (models.anim) can write each clip back to
            # Animations/{geoId}/{key}.anim even if Blender renames the Action -- extras survive a glTF
            # round-trip as Action custom properties; a purely-numeric name is the fallback.
            gltf_anims.append({"name": label, "samplers": samplers, "channels": channels,
                               "extras": {"ff9_anim_key": key, "ff9_anim_label": label}})
            anim_labels.append(label)

    # --- assemble ---
    gltf = {
        # stamp the source model + scale so `model-import` can auto-detect them (no need to retype --like)
        "asset": {"version": "2.0", "generator": "ff9mapkit",
                  "extras": {"ff9_geo": model["geo"], "ff9_geo_id": model["geo_id"], "ff9_scale": s}},
        "scene": 0,
        "scenes": [{"nodes": [node_of[model["root_bone"]], *mesh_nodes]}],
        "nodes": nodes,
        "meshes": gltf_meshes,
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
            "bones": len(bones), "meshes": len(meshes),
            "primitives": sum(len(gm["primitives"]) for gm in gltf_meshes),
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


def _root_parent_matrix(root_ni, parent_of, nodes, joint_set):
    """Compose the LOCAL matrices of a skin root joint's non-joint ancestors (the Blender Armature object / any
    empties BETWEEN the scene and bone000), top-down, into one row-major 4x4. Identity when the root joint is a
    direct scene child (our own export) OR every such ancestor is untransformed (a normal Blender re-export --
    ``export_yup`` bakes the axis conversion into the bones and leaves the Armature node identity)."""
    chain = []
    ni = parent_of.get(root_ni)
    while ni is not None and ni not in joint_set:
        chain.append(ni)
        ni = parent_of.get(ni)
    m = [[1.0 if i == j else 0.0 for j in range(4)] for i in range(4)]
    for ni in reversed(chain):                                # top-down so m = A_top * ... * A_bottom
        t, q, sc = _node_local_trs(nodes[ni])
        m = _mat_mul(m, _mat_trs(t, q, sc))
    return m


def _looks_identity(m, *, eps_t=1e-3, eps_r=1e-4, eps_s=1e-3) -> bool:
    """True if a row-major 4x4 is (within tolerance) identity -- no translation, rotation, non-unit scale, or
    shear. Tolerances are generous so float noise in a clean Blender export never trips the non-identity guard,
    yet any DELIBERATE armature move/rotate/scale (>~1mm / >~0.006deg / >0.1%) is caught."""
    for i in range(3):
        for j in range(3):
            if abs(m[i][j] - (1.0 if i == j else 0.0)) > (eps_s if i == j else eps_r):
                return False
    return all(abs(m[i][3]) <= eps_t for i in range(3))


def check_root_parent_transforms(nodes, joints) -> None:
    """Raise if any skin root joint has a NON-identity non-joint ancestor -- a live transform on the Blender
    Armature object (or a parent empty) that FF9 can't carry on a root bone. The engine parents a model's root
    bone to the identity base object (``ModelImporter.cs`` root branch -- its own TODO: intermediate
    GameObjects would be needed for a real root-parent transform), and our engine-facing FBX gives the root an
    IDENTITY 'Armature' Null. Such a transform would otherwise be SILENTLY DROPPED in every import path (the
    stamped/``--like`` paths keep the pristine skeleton; a re-rig drops the non-joint parent) -> the model
    imports at the wrong size/orientation with no warning. Refuse it loudly with the one-click Blender fix."""
    joint_set = set(joints)
    parent_of = {}
    for ni, node in enumerate(nodes):
        for ch in node.get("children", []) or []:
            parent_of[ch] = ni
    for ni in joints:
        if parent_of.get(ni) in joint_set:
            continue                                          # not a root joint (its parent is another bone)
        if not _looks_identity(_root_parent_matrix(ni, parent_of, nodes, joint_set)):
            nm = nodes[ni].get("name", f"node{ni}") if ni < len(nodes) else f"node{ni}"
            raise ValueError(
                f"the object above {nm} (the Blender Armature / a parent empty) has a live transform "
                f"(move / rotate / scale) that FF9 can't carry on a root bone -- it would be dropped and the "
                f"model would import at the wrong size or orientation. In Blender select the Armature (and any "
                f"parent), then Object > Apply > All Transforms (Ctrl+A) so the transform bakes into the bones "
                f"+ mesh, and re-export. (A non-uniform armature scale must be applied too; per-bone scale "
                f"inside the rig is fine.)")


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
    check_root_parent_transforms(nodes, joints)               # refuse a live armature transform FF9 can't carry

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

    # Recover each part's NAME (the load-bearing bit -- see export_gltf). Prefer the mesh node's ff9_mesh
    # extra (survives a Blender round-trip as an object custom property), then the node/object NAME, then the
    # glTF mesh name; strip Blender's ".001" dedup suffix. Keyed by POSITION accessor so it attaches to the
    # right vertex set below (a file we emit gives one POSITION accessor per part).
    node_name_of_mesh: dict = {}
    node_extra_of_mesh: dict = {}
    for node in nodes:
        if "mesh" in node:
            node_name_of_mesh.setdefault(node["mesh"], node.get("name"))
            ex = node.get("extras") or {}
            if ex.get("ff9_mesh"):
                node_extra_of_mesh.setdefault(node["mesh"], ex["ff9_mesh"])
    name_of_pos: dict = {}
    for mesh_i, gm in enumerate(gltf.get("meshes", [])):
        part = node_extra_of_mesh.get(mesh_i) or node_name_of_mesh.get(mesh_i) or gm.get("name")
        part = re.sub(r"\.\d+$", "", str(part)) if part else None
        for prim in gm.get("primitives", []):
            name_of_pos.setdefault(prim["attributes"]["POSITION"], part)

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
        root_num = extract._bone_num(root_bone) if root_bone else None
        if root_num is None:
            root_num = extract._bone_num(bones[0]["name"]) if bones else 0
        weights = [[(root_num, 1.0)]] * len(verts)           # unskinned mesh -> bind to root (never weightless)
        if "JOINTS_0" in attrs and "WEIGHTS_0" in attrs:
            J = _gltf_io.decode_accessor(gltf, blob, attrs["JOINTS_0"])
            W = _gltf_io.decode_accessor(gltf, blob, attrs["WEIGHTS_0"])
            weights = []
            for jv, wv in zip(J, W):
                infl = [(num_of_joint.get(int(j), 0), float(w)) for j, w in zip(jv, wv) if w > 0.0]
                if not infl:
                    infl = [(root_num, 1.0)]                 # Blender may zero a vertex's weights -> a weightless
                tot = sum(w for _, w in infl) or 1.0         # vertex collapses to the origin; bind it to the root
                weights.append([(bn, w / tot) for bn, w in infl])
        subs = []
        for prim in prims:
            base_mat = len(materials)
            idx = [int(x[0]) for x in _gltf_io.decode_accessor(gltf, blob, prim["indices"])]
            tris = [[idx[i], idx[i + 2], idx[i + 1]] for i in range(0, len(idx) - 2, 3)]   # un-reverse winding
            subs.append({"material_idx": base_mat, "tris": tris})
            materials.append({"name": f"mat{base_mat}", "texture": mat_stem(prim.get("material", -1))})
        # Real carried names (incl. FF9's common "mesh0"/"mesh1") match by name downstream; a genuinely
        # nameless part gets a SYNTHETIC placeholder that can't collide with a real part name, so the re-rig
        # routes it through the order-independent vertex-count fallback instead of a naive name-match.
        meshes.append({"name": name_of_pos.get(pos_acc) or f"__part{len(meshes)}", "verts": verts,
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
    # Fold any nested-child mesh into a same-texture sibling first -- the loose-FBX importer flattens the
    # hierarchy + drops such renderers (Garnet's rubber_band scrunchie); merging keeps them visible. No-op
    # unless a mesh carries `parent` (only real-model structs do), so foreign-glTF re-rigs pass through.
    merge_warnings: list = []
    extract.merge_nested_child_meshes(model, warn=merge_warnings.append)
    text, meta = fbx_skin.emit_skinned_fbx(model)
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / f"{geo_id}.fbx").write_text(text, encoding="ascii", newline="\n")
    saved = []
    for stem, img in (model.get("textures") or {}).items():
        img.save(str(dest / f"{stem}.png"))
        saved.append(f"{stem}.png")
    return {"fbx": str(dest / f"{geo_id}.fbx"), "textures": saved, "euler_max_err": meta["euler_max_err"],
            "merge_warnings": merge_warnings}


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


def _restore_mesh_names(edited_meshes: list, orig_meshes: list) -> None:
    """Rename each edited mesh to its matching ORIGINAL part name (and carry its ``parent`` merge-hint), in
    place. Name-match first (the robust path -- ``import_gltf`` carries part names), then a closest-vertex-
    count fallback for any part that arrived unnamed / unrecognized (old fused-mesh exports, heavy Blender
    renames). See the caller for WHY part names are load-bearing (engine NAME-keyed branches like Garnet's
    hair swap); ``parent`` lets the emitter re-merge a nested-child mesh the importer would drop."""
    by_name = {m["name"]: m for m in orig_meshes}
    used: set = set()
    unmatched: list = []
    for em in edited_meshes:
        nm = re.sub(r"\.\d+$", "", str(em.get("name") or ""))
        if nm in by_name and nm not in used:
            em["name"] = nm
            em["parent"] = by_name[nm].get("parent")
            used.add(nm)
        else:
            unmatched.append(em)
    avail = [i for i, m in enumerate(orig_meshes) if m["name"] not in used]
    for em in unmatched:
        if not avail:
            break
        j = min(avail, key=lambda k: abs(len(orig_meshes[k]["verts"]) - len(em["verts"])))
        em["name"] = orig_meshes[j]["name"]
        em["parent"] = orig_meshes[j].get("parent")
        avail.remove(j)


def deploy_edit(gltf_path, mod_folder, *, like=None, geo_id=None, scale=None, game=None,
                write_anims=True) -> dict:
    """Bring a (Blender-edited) glTF back into the game: import it, emit the FBX + textures into ``mod_folder``
    at ``Models/{type}/{id}/`` (an override -- deletes to revert), AND (``write_anims``) write back any clip
    whose curves changed as a loose ``.anim`` override -- so ONE edited glTF round-trips mesh AND animation.

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
            # Restore the ORIGINAL mesh GameObject names. The engine has NAME-keyed per-model branches -- e.g.
            # Garnet's `garnetShortHairTable` in ModelFactory.CreateModel does GetChildByName("long_hair"/
            # "short_hair") to hide a hair mesh by scenario; a re-rig whose parts lost their names NREs there
            # and mis-renders her hair as flailing spikes. Names are cosmetic to skinning but load-bearing
            # here. Match BY NAME first (import_gltf now carries each part's name faithfully); only fall back
            # to a closest-vertex-count guess for parts that arrive unnamed (an old fused-mesh export, or a
            # part Blender renamed past recognition).
            _restore_mesh_names(edited["meshes"], orig["meshes"])
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
    # Round-trip the animations too: write back only clips whose curves changed (spliced onto the pristine
    # source), so an edit to the mesh alone leaves every clip on its byte-faithful bundled version.
    anims = {"written": [], "skipped": []}
    if write_anims:
        try:
            from . import anim as _anim
            anims = _anim.deploy_gltf_anim_edits(gltf_path, mod_folder, geo=like, scale=scale, game=game)
        except (RuntimeError, FileNotFoundError, ValueError, KeyError) as e:
            anims = {"written": [], "skipped": [], "error": str(e)}
    return {"id": tid, "type_int": type_int, "mode": mode, "source": like, "path": info["fbx"],
            "textures": info["textures"], "merge_warnings": info.get("merge_warnings", []), "anims": anims}
