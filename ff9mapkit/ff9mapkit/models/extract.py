"""Read a real FF9 field/character model prefab out of the install -> an in-memory Model struct.

The prefab lives in ``p0data4.bin`` at ``assets/resources/models/{typeInt}/{geoId}/{geoId}.fbx`` as a
native Unity ``GameObject`` (NOT a loose FBX): a root object (Transform + legacy ``Animation``) whose
children are the bone hierarchy (``bone000``.. GameObjects) and the mesh objects (each a
``SkinnedMeshRenderer``). We walk that hierarchy and decode:

  * the skeleton  -- every bone's name (``boneNNN`` -> FF9 bone number NNN), parent, local pos/rot/scale
  * each mesh     -- verts / normals / uvs / per-submesh triangles (verbatim packed vertex stream) +
                     per-vertex bone weights REMAPPED from the SkinnedMeshRenderer's ``m_Bones`` order to
                     the FF9 bone NUMBER (so the exported skin is skeleton-order-independent)
  * materials     -- per-submesh ``_MainTex`` texture stem (the on-disc ``{geoId}_{n}.png``)
  * textures      -- the Texture2D images

Everything is read via the typetree (robust across UnityPy shapes / Unity 5.2.3). Pure read: no I/O
beyond the install; the FBX/PNG writing is :mod:`ff9mapkit.models.export`.

Bone NUMBER is the fidelity linchpin: the engine's FBX importer names each imported bone GameObject
``bone{id:D3}`` where ``id`` is the trailing 3 digits of the FBX bone name, and FF9's own animation
clips bind to bones by that name -- so preserving the number round-trips the animation.
"""
from __future__ import annotations

import re
import struct
from pathlib import Path

from .. import config
from .._modeldb import MODELS

_NAME_TO_ID = {name: mid for mid, name in MODELS.items()}
_TYPE_INT = {"acc": 1, "main": 2, "mon": 3, "npc": 4, "sub": 5, "wep": 6}


def _unitypy():
    from ..extract import _unitypy as _u   # reuse the field extractor's lazy import + error message
    return _u()


def _p0data(idx: int, game=None) -> Path:
    return config.find_game_path(game) / "StreamingAssets" / f"p0data{idx}.bin"


def _p0data4(game=None) -> Path:
    return _p0data(4, game)


def _model_bundle_index(type_int: int) -> int:
    """Which p0data bundle holds a model of this type. Weapons (``GEO_WEP_*`` = type 6, under
    ``BattleMap/BattleModel/``) live in ``p0data2``; every other model type in ``p0data4``."""
    return 2 if type_int == 6 else 4


def resolve_geo(token: str) -> tuple[str, int, int]:
    """('GEO_MAIN_F0_VIV' | '8') -> (geo_name, geo_id, type_int). A pure-digit token is a model id."""
    tok = str(token).strip()
    if tok.isdigit():
        gid = int(tok)
        name = MODELS.get(gid)
        if not name:
            raise ValueError(f"no model with id {gid} (see `ff9mapkit models`)")
    else:
        name = tok.upper()
        if name not in _NAME_TO_ID:
            raise ValueError(f"unknown model name {name!r} (see `ff9mapkit models`)")
        gid = _NAME_TO_ID[name]
    grp = name.split("_")[1].lower()
    tint = _TYPE_INT.get(grp)
    if tint is None:
        raise ValueError(f"model {name!r} has unsupported group {grp!r} (field/char groups: "
                         f"{sorted(_TYPE_INT)})")
    return name, gid, tint


# ---- typetree navigation helpers (UnityPy 1.25: container values are PPtrs; resolve via assetsfile) ----

def _pid(x):
    """A PPtr-ish dict/tuple -> its m_PathID (or None)."""
    if isinstance(x, dict):
        return x.get("m_PathID")
    if isinstance(x, (tuple, list)) and x:
        return _pid(x[-1])
    return None


def _comp_pptr(entry):
    """A GameObject m_Component entry -> the component PPtr dict (across Unity 5.x pair / newer shapes)."""
    if isinstance(entry, (tuple, list)) and entry:
        entry = entry[-1]
    if isinstance(entry, dict):
        return entry.get("component") or entry.get("second") or entry
    return None


class _Bundle:
    """A p0data model bundle loaded once (p0data4 for most models, p0data2 for weapons), with
    pathid->ObjectReader + typetree cache."""

    def __init__(self, game=None, data_index: int = 4):
        self.env = _unitypy().load(str(_p0data(data_index, game)))
        # any container PPtr shares the same SerializedFile -> its .objects is the pathid table
        first = next(iter(self.env.container.values()))
        self.objs = first.assetsfile.objects
        self._tt: dict = {}

    def tt(self, pid):
        if pid in self._tt:
            return self._tt[pid]
        o = self.objs.get(pid)
        t = None
        if o is not None:
            try:
                t = o.read_typetree()
            except Exception:
                t = None
        self._tt[pid] = t
        return t

    def type_name(self, pid):
        o = self.objs.get(pid)
        return o.type.name if o is not None else None

    def find_prefab_go(self, type_int: int, geo_id: int):
        """The root GameObject pathid for this model's prefab. Weapons (type 6) live at
        ``battlemap/battlemodel/6/{id}/{id}.fbx``; every other type at ``models/{type}/{id}/{id}.fbx``."""
        sub = "battlemap/battlemodel/6" if type_int == 6 else f"models/{type_int}"
        want = f"{sub}/{geo_id}/{geo_id}.fbx"
        for k, pptr in self.env.container.items():
            if want in k.lower() and pptr.type.name == "GameObject":
                return getattr(pptr, "path_id", None) or getattr(pptr, "m_PathID", None)
        return None

    def components(self, go_tt):
        """[(type_name, pathid)] for a GameObject typetree's components."""
        out = []
        for c in go_tt.get("m_Component", []):
            p = _comp_pptr(c)
            pid = p and p.get("m_PathID")
            out.append((self.type_name(pid), pid))
        return out

    def go_name(self, go_pid):
        t = self.tt(go_pid)
        return t.get("m_Name") if t else None

    def transform_of(self, go_tt):
        for tn, pid in self.components(go_tt):
            if tn in ("Transform", "RectTransform"):
                return pid, self.tt(pid)
        return None, None


def _quat(d):
    return [float(d.get("x", 0.0)), float(d.get("y", 0.0)), float(d.get("z", 0.0)), float(d.get("w", 1.0))]


def _vec3(d, default=(0.0, 0.0, 0.0)):
    if not isinstance(d, dict):
        return list(default)
    return [float(d.get("x", default[0])), float(d.get("y", default[1])), float(d.get("z", default[2]))]


def _decode_mesh_tt(bundle: _Bundle, mesh_pid):
    """Decode a Mesh (by typetree) -> dict(verts, normals|None, uvs, submeshes=[tris], skin=[BoneWeight]).

    Ports battle.extract._decode_mesh to the typetree, generalized to the field-model channel layout
    (Unity 5.2.3: channel 0 pos, 1 normal, 2 color, 3 uv0, ...). Skin (per-vertex bone weights) is a
    SEPARATE ``m_Skin`` array in this Unity version, returned verbatim (boneIndex still in SMR order)."""
    md = bundle.tt(mesh_pid)
    vd = md["m_VertexData"]
    data = bytes(vd["m_DataSize"])
    vcount = int(vd["m_VertexCount"])
    chans = vd["m_Channels"]

    # Unity 5.2.3 packs vertices in one or more STREAMS: each stream is a contiguous block of
    # vcount * stride bytes (all vertices), stream N starting after N-1 (16-byte aligned). A channel
    # reads from stream_start[stream] + vi*stride[stream] + offset. Formats: 0=float32(4B) 1=float16(2B).
    _FMT = {0: (4, "<%df"), 1: (2, "<%de")}
    strides: dict = {}
    for c in chans:
        if c.get("dimension"):
            s = int(c.get("stream", 0))
            csize, _ = _FMT.get(int(c.get("format", 0)), (4, "<%df"))
            strides[s] = max(strides.get(s, 0), int(c["offset"]) + int(c["dimension"]) * csize)
    # Each stream is a contiguous vcount*stride block; a stream's START is 16-byte aligned, so an
    # intermediate stream is padded up to align the NEXT one -- but the LAST stream is NOT padded (the
    # buffer may or may not pad its tail to 16). So the data size is in [minTotal, align16(minTotal)].
    starts, cur = {}, 0
    order = sorted(strides)
    for i, s in enumerate(order):
        starts[s] = cur
        cur += strides[s] * vcount
        if i < len(order) - 1:
            cur = (cur + 15) & ~15                        # align the next stream's start
    if not (cur <= len(data) <= ((cur + 15) & ~15)):
        raise ValueError(f"mesh {md.get('m_Name')!r}: vertex data size mismatch "
                         f"(streams {strides} -> {cur}, data {len(data)})")

    def rd(ch, vi):
        s = int(ch.get("stream", 0))
        dim = int(ch["dimension"])
        csize, fmt = _FMT.get(int(ch.get("format", 0)), (4, "<%df"))
        base = starts[s] + vi * strides[s] + int(ch["offset"])
        return list(struct.unpack_from(fmt % dim, data, base))

    pos_c, nrm_c = chans[0], chans[1]
    uv_c = chans[3] if len(chans) > 3 and chans[3].get("dimension") else None
    verts = [rd(pos_c, i) for i in range(vcount)]
    normals = [rd(nrm_c, i) for i in range(vcount)] if nrm_c.get("dimension") else None
    uvs = [rd(uv_c, i)[:2] for i in range(vcount)] if uv_c else [[0.0, 0.0]] * vcount

    ib = bytes(md["m_IndexBuffer"])
    use32 = int(md.get("m_IndexFormat", 0)) == 1
    if use32:
        idx = struct.unpack("<%dI" % (len(ib) // 4), ib); ent = 4
    else:
        idx = struct.unpack("<%dH" % (len(ib) // 2), ib); ent = 2
    submeshes = []
    for s in md["m_SubMeshes"]:
        first = int(s["firstByte"]) // ent
        n = int(s["indexCount"])
        flat = idx[first:first + n]
        submeshes.append([[flat[i], flat[i + 1], flat[i + 2]] for i in range(0, len(flat) - 2, 3)])

    skin = []
    for bw in md.get("m_Skin", []):
        skin.append({
            "bone": [int(bw.get(f"boneIndex[{i}]", 0)) for i in range(4)],
            "weight": [float(bw.get(f"weight[{i}]", 0.0)) for i in range(4)],
        })
    bindposes = []
    for bp in md.get("m_BindPose", []):
        bindposes.append([[float(bp[f"e{r}{c}"]) for c in range(4)] for r in range(4)])
    return {"name": md.get("m_Name"), "verts": verts, "normals": normals, "uvs": uvs,
            "submeshes": submeshes, "skin": skin, "bindposes": bindposes, "vcount": vcount}


def _collect(token: str, game=None, bundle: "_Bundle | None" = None) -> dict:
    """Walk a real model prefab -> raw bones + per-SMR meshes (NO bind correction applied yet).

    Shared by :func:`read_model` (which applies the correction + reads textures) and
    :func:`bind_diagnostics` (which characterizes the bind-space variation). Returns a dict:
      geo, geo_id, type_int, bundle, bones[], root_bone, smrs[] where each smr is
      {name, mesh(decoded), idx_to_num, mat_stems, weights, samples=[(bone_name, m_BindPose)]}.
    Bone weights are REMAPPED to FF9 bone NUMBERS (skeleton-order-independent); ``samples`` carry the
    m_BindPose per bone of THIS mesh (kept per-SMR so the correction can be computed mesh-by-mesh).
    Pass ``bundle`` to reuse an already-loaded p0data4 across many models (bulk sweeps)."""
    geo, gid, tint = resolve_geo(token)
    b = bundle if bundle is not None else _Bundle(game, data_index=_model_bundle_index(tint))
    root_pid = b.find_prefab_go(tint, gid)
    if root_pid is None:
        sub = "battlemap/battlemodel/6" if tint == 6 else f"models/{tint}"
        raise FileNotFoundError(
            f"{geo} (id {gid}) not found at {sub}/{gid}/{gid}.fbx in p0data{_model_bundle_index(tint)}.bin")
    root_tt = b.tt(root_pid)

    # --- walk the transform hierarchy: collect bones + SkinnedMeshRenderers ---
    bones: list[dict] = []          # {name, parent, pos, rot, scale}  (hierarchy/pre-order)
    bone_pid_to_name: dict = {}      # transform pathid -> bone name (for skin remap)
    smr_pids: list = []              # (smr_pathid, enclosing_mesh_go_name)  enclosing = nearest ANCESTOR mesh GO

    def walk(tr_pid, tr_tt, parent_name, in_battle, enclosing_mesh):
        if not tr_tt:
            return
        go_pid = _pid(tr_tt.get("m_GameObject", {}))
        go_tt = b.tt(go_pid)
        name = go_tt.get("m_Name") if go_tt else None
        is_bone = bool(name and re.fullmatch(r"bone\d+", str(name)))
        # A character prefab bundles BOTH field (mesh*) and battle (battle_model*) geometry; the engine
        # HIDES the battle_model subtree in field mode (ModelFactory.CreateModel disables it). Exclude it
        # from a FIELD export -- else we'd export hidden geometry AND pollute the bind-pose correction
        # with the battle bind space (which differs -> the correction goes inconsistent). Bones are the
        # shared skeleton, so they're kept regardless.
        here_battle = in_battle or bool(name and str(name).lower().startswith("battle_model"))
        if is_bone:
            bones.append({
                "name": name, "parent": parent_name,
                "pos": _vec3(tr_tt.get("m_LocalPosition")),
                "rot": _quat(tr_tt.get("m_LocalRotation", {})),
                "scale": _vec3(tr_tt.get("m_LocalScale"), (1.0, 1.0, 1.0)),
            })
            bone_pid_to_name[tr_pid] = name
        has_smr = False
        if go_tt and not here_battle:
            for tn, pid in b.components(go_tt):
                if tn == "SkinnedMeshRenderer":
                    smr_pids.append((pid, enclosing_mesh))   # this SMR's nearest ancestor mesh GO
                    has_smr = True
        child_parent = name if is_bone else parent_name
        # A GO carrying an SMR becomes the "enclosing mesh" for its descendants -- so a mesh nested UNDER
        # another mesh (e.g. Garnet's rubber_band scrunchie under long_hair) is recorded as a child. The
        # engine's loose-FBX importer FLATTENS that nesting away; we keep it here so the emitter can merge a
        # dropped nested-child renderer back into a sibling.
        child_enclosing = name if has_smr else enclosing_mesh
        for ch in tr_tt.get("m_Children", []):
            cpid = _pid(ch)
            walk(cpid, b.tt(cpid), child_parent, here_battle, child_enclosing)

    root_tpid, root_ttr = b.transform_of(root_tt)
    walk(root_tpid, root_ttr, None, False, None)
    root_bone = next((bn["name"] for bn in bones if bn["parent"] is None), None)

    # --- each SkinnedMeshRenderer -> a mesh (geometry + skin remapped to bone numbers) ---
    smrs: list[dict] = []
    for smr_pid, mesh_parent in smr_pids:
        smr = b.tt(smr_pid)
        mesh_pid = _pid(smr.get("m_Mesh", {}))
        if not mesh_pid:
            continue
        mesh = _decode_mesh_tt(b, mesh_pid)
        # SMR bone list: index (in m_Skin.boneIndex) -> FF9 bone NUMBER via the bone GO name
        smr_bones = smr.get("m_Bones", [])
        idx_to_num = []
        for bp in smr_bones:
            bn_name = bone_pid_to_name.get(_pid(bp))
            idx_to_num.append(_bone_num(bn_name))
        samples = []                 # (bone_name, m_BindPose) for THIS mesh only
        for j, bindpose in enumerate(mesh.get("bindposes", [])):
            if j < len(idx_to_num) and idx_to_num[j] is not None:
                samples.append((f"bone{idx_to_num[j]:03d}", bindpose))
        # materials for this renderer (per submesh)
        mat_stems = []
        for mp in smr.get("m_Materials", []):
            mat_stems.append(_maintex_stem(b, _pid(mp)))
        # remap per-vertex weights to bone numbers, prune zero-weight influences
        remapped = []
        for w in mesh["skin"]:
            infl = []
            for bi, wt in zip(w["bone"], w["weight"]):
                if wt > 0.0 and 0 <= bi < len(idx_to_num) and idx_to_num[bi] is not None:
                    infl.append((idx_to_num[bi], wt))
            remapped.append(infl)
        smrs.append({"name": mesh["name"], "mesh": mesh, "idx_to_num": idx_to_num,
                     "mat_stems": mat_stems, "weights": remapped, "samples": samples,
                     "mesh_parent": mesh_parent})

    return {"geo": geo, "geo_id": gid, "type_int": tint, "bundle": b,
            "bones": bones, "root_bone": root_bone, "smrs": smrs}


def read_model(token: str, game=None, bundle: "_Bundle | None" = None) -> dict:
    """Read a real model prefab -> the Model struct consumed by :mod:`ff9mapkit.models.fbx_skin`.

    ``token`` is a GEO name (``GEO_NPC_F0_...``) or a model id. Returns a dict:
      geo, geo_id, type_int, root_bone, bones[], meshes[], materials[], textures{stem: PIL.Image}.
    Bone weights in each mesh are REMAPPED to FF9 bone NUMBERS (skeleton-order-independent).
    Pass ``bundle`` to reuse an already-loaded p0data4 across many models (bulk sweeps)."""
    c = _collect(token, game, bundle=bundle)
    bones, smrs, b = c["bones"], c["smrs"], c["bundle"]
    if not smrs:
        # Weapons (GEO_WEP_*) are STATIC meshes (MeshRenderer/MeshFilter, no skeleton) — the skinned
        # exporter can't read them. Their common edit is a texture reskin, which needs no mesh at all
        # (the engine's loose-.png disc-probe reskins the bundled weapon, ModelFactory.cs:100-116).
        gid = c["geo_id"]
        if c["type_int"] == 6:
            raise ValueError(
                f"{c['geo']} (id {gid}) is a WEAPON — a static mesh with no skeleton, which the skinned "
                f"model exporter can't handle. To recolor it, drop a loose PNG at "
                f"BattleMap/BattleModel/6/{gid}/{gid}.png in your mod folder (the engine reskins the "
                f"bundled weapon from it — no mesh export needed). Editing the weapon GEOMETRY needs a "
                f"static-mesh path (not yet built).")
        raise ValueError(f"{c['geo']} (id {gid}) has no skinned mesh to export (static/empty prefab).")

    meshes: list[dict] = []
    materials: list[dict] = []
    texture_stems: set = set()
    per_mesh_G: list = []
    for s in smrs:
        mesh = s["mesh"]
        mat_stems = s["mat_stems"]
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
        me = {"name": mesh["name"], "verts": mesh["verts"], "normals": mesh["normals"],
              "uvs": mesh["uvs"], "submeshes": subs, "weights": s["weights"],
              "parent": s.get("mesh_parent")}   # nearest ancestor MESH GO name (None = top-level) -> merge hint

        # --- bind-pose correction (PER MESH) -----------------------------------------------------
        # FF9's Unity import baked a coordinate transform into every model's m_BindPose that the
        # engine's FBX importer DROPS (ModelImporter recomputes bindpose from the bone REST pose, not
        # the stored m_BindPose). Left uncorrected the re-imported model renders transformed -- Vivi
        # came in upside-down (a 180-deg X flip). We recover G = boneWorld * m_BindPose and bake it
        # into the verts + normals, so the engine's recomputed bindpose reproduces the ORIGINAL
        # render, through animation. G is computed PER MESH: the bake is a global space conversion but
        # it can DIFFER between a character's SkinnedMeshRenderers (e.g. body vs a separately-authored
        # hair mesh) -- a single global G mis-orients the odd mesh out, so each mesh gets its own.
        # (When every mesh shares one G -- Vivi/Zidane -- this is byte-identical to the old bake.)
        # Derived from THIS mesh's own bindposes (self-correcting); None (no bake) if inconsistent
        # WITHIN the mesh (a per-bone bind variation the vertex bake can't express -- rare/none in FF9).
        G = _bind_correction(bones, s["samples"])
        per_mesh_G.append(G)
        if G is not None:
            R = [row[:3] for row in G[:3]]
            me["verts"] = [_affine(G, v) for v in me["verts"]]
            if me["normals"]:
                me["normals"] = [_mat3_vec(R, n) for n in me["normals"]]
        meshes.append(me)

    textures = _read_textures(b, c["geo_id"], texture_stems)
    non_null = [g for g in per_mesh_G if g is not None]
    return {"geo": c["geo"], "geo_id": c["geo_id"], "type_int": c["type_int"], "root_bone": c["root_bone"],
            "bones": bones, "meshes": meshes, "materials": materials, "textures": textures,
            "bind_correction": non_null[0] if non_null else None, "per_mesh_bind": per_mesh_G}


def merge_nested_child_meshes(model: dict, warn=None) -> list:
    """Fold each mesh that was a NESTED CHILD of another mesh (in the source prefab) into the largest
    top-level mesh sharing its texture. Mutates ``model['meshes']`` in place; returns [(child, target), ...].

    WHY: the engine's loose-FBX importer (``ModelImporter.CreateCustomModel``) parents EVERY mesh straight
    to the base object -- it reads no FBX mesh hierarchy -- and gives each ``SkinnedMeshRenderer`` no
    explicit rootBone/bounds. A small nested-child renderer (Garnet's 38-vert ``rubber_band`` scrunchie, a
    child of ``long_hair``) is then frustum-DROPPED where the top-level body/hair meshes still draw
    (in-game proven: it renders once merged, invisible standalone even scaled 3x). Merging its verts into a
    sibling makes them part of a renderer that reliably draws.

    Same-texture is REQUIRED (the importer reads ONE material per mesh -- submesh 0 -- so a two-texture
    merge would repaint the child with the target's texture). A nested child with no same-texture top-level
    target is left standalone (merging would corrupt it) and reported via ``warn``. Only ~3 real FF9 models
    have nested meshes (both Garnet field/battle variants merge cleanly; GEO_MON_F0_EFM's parts have unique
    textures -> left standalone). A no-op for every model without nesting -- and for structs that never
    carried parent info (e.g. a foreign glTF import), so it's safe to call on any engine-bound emit."""
    meshes = model.get("meshes") or []
    mats = model.get("materials") or []

    def tex(me):
        subs = me.get("submeshes") or []
        if not subs:
            return None
        mi = subs[0]["material_idx"]
        return mats[mi].get("texture") if 0 <= mi < len(mats) else None

    nested = [me for me in meshes if me.get("parent") is not None]
    if not nested:
        return []
    merged, drop = [], set()
    for child in nested:
        t = tex(child)
        targets = [o for o in meshes if o is not child and o.get("parent") is None and tex(o) == t]
        if not targets:
            if warn:
                warn(f"mesh {child['name']!r} was nested under {child['parent']!r} with no same-texture "
                     f"sibling to merge into -- it may not render (the loose-FBX importer drops nested-child "
                     f"renderers)")
            continue
        target = max(targets, key=lambda o: len(o["verts"]))
        off = len(target["verts"])
        target["verts"] = list(target["verts"]) + list(child["verts"])
        if target.get("normals") is not None and child.get("normals") is not None:
            target["normals"] = list(target["normals"]) + list(child["normals"])
        else:
            target["normals"] = None                       # mixed normals -> drop (emitter handles no-normals)
        target["uvs"] = list(target["uvs"]) + list(child["uvs"])
        target["weights"] = list(target["weights"]) + list(child["weights"])
        tris = target["submeshes"][0]["tris"]
        for sub in child["submeshes"]:
            tris = tris + [[a + off, b + off, c + off] for a, b, c in sub["tris"]]
        target["submeshes"][0]["tris"] = tris
        merged.append((child["name"], target["name"]))
        drop.add(id(child))
    if drop:
        model["meshes"] = [me for me in meshes if id(me) not in drop]
    return merged


def bind_diagnostics(token: str, game=None, bundle: "_Bundle | None" = None) -> dict:
    """Characterize a model's bind-space variation (offline; the input to choosing a correction).

    For every SkinnedMeshRenderer, compute G = boneWorld * m_BindPose for each of its bones and report:
      * ``within_dev`` -- max rotation-3x3 spread of G ACROSS the bones of THIS mesh (0 => the bake is a
        single per-mesh transform the vertex bake handles exactly; >0 => a per-bone variation it can't).
      * ``g0`` -- this mesh's representative G (its first bone's).
    Plus ``across_dev`` -- the max rotation spread of the per-mesh g0 BETWEEN meshes (>threshold =>
    a single GLOBAL bake mis-orients some mesh; the per-mesh bake is what fixes it)."""
    c = _collect(token, game, bundle=bundle)
    bones = c["bones"]
    from .fbx_skin import _mat_trs, _mat_mul
    byname = {bn["name"]: bn for bn in bones}
    cache: dict = {}

    def world(name):
        if name in cache:
            return cache[name]
        bn = byname[name]
        loc = _mat_trs(bn["pos"], bn["rot"], bn["scale"])
        cache[name] = loc if bn["parent"] is None else _mat_mul(world(bn["parent"]), loc)
        return cache[name]

    def rot_dev(mats):
        if len(mats) < 2:
            return 0.0
        m0 = mats[0]
        return max(abs(m[r][col] - m0[r][col]) for m in mats for r in range(3) for col in range(3))

    per_mesh = []
    for s in c["smrs"]:
        gs = [_mat_mul(world(name), bp) for name, bp in s["samples"] if name in byname]
        per_mesh.append({"mesh": s["name"], "nbones": len(gs),
                         "within_dev": rot_dev(gs), "g0": gs[0] if gs else None})
    g0s = [m["g0"] for m in per_mesh if m["g0"] is not None]
    across_dev = rot_dev(g0s)
    return {"geo": c["geo"], "geo_id": c["geo_id"], "type_int": c["type_int"],
            "nmeshes": len(c["smrs"]), "per_mesh": per_mesh, "across_dev": across_dev}


def _bone_num(name):
    if not name:
        return None
    m = re.fullmatch(r"bone(\d+)", str(name))
    return int(m.group(1)) if m else None


def _bind_correction(bones, samples):
    """The transform G = boneWorld * m_BindPose that FF9 baked into a mesh's bindposes and the engine
    DROPS (it recomputes each bindpose from the bone rest pose, discarding the stored m_BindPose). Return
    the single 4x4 (row-major) to bake into THIS mesh's verts + normals, or None if no single transform
    is safe.

    Almost every FF9 mesh shares ONE G across all its bones (a clean coordinate flip -> bake it, and
    the round-trip is exact). A few have per-bone rotational jitter or a genuine mix of flip families;
    we cluster the per-bone G by rotation FAMILY (coordinate flips differ by >=2.0 in the 3x3, while
    per-bone jitter is <0.2, so a 0.5 threshold separates families yet absorbs jitter) and return the
    DOMINANT family's transform when it holds a strict majority of the bones. That degrades gracefully:
    a mesh whose bones MOSTLY agree still gets baked (e.g. one stray bone can't veto a whole flipped
    mesh into shipping un-baked -- which the old all-or-nothing rule did, leaving it visibly flipped).
    A dominant bake is never worse than no bake by bone count. None only when NO family is a majority,
    so any single bake would be a coin-flip -- then we don't risk one."""
    if not samples:
        return None
    from .fbx_skin import _mat_trs, _mat_mul
    byname = {b["name"]: b for b in bones}
    cache: dict = {}

    def world(name):
        if name in cache:
            return cache[name]
        bn = byname[name]
        loc = _mat_trs(bn["pos"], bn["rot"], bn["scale"])
        cache[name] = loc if bn["parent"] is None else _mat_mul(world(bn["parent"]), loc)
        return cache[name]

    gs = [_mat_mul(world(name), bp) for name, bp in samples if name in byname]
    if not gs:
        return None

    # Cluster on the ROTATION 3x3 only -- orientation is what the bake corrects; G's translation jitters
    # harmlessly per bone (the model is hundreds of units tall). Each cluster keeps its first G as the
    # representative; a later G joins if within 0.5 of that rep.
    def rot_dist(a, b):
        return max(abs(a[r][c] - b[r][c]) for r in range(3) for c in range(3))

    clusters: list = []                    # each: [representative_G, count]
    for g in gs:
        for cl in clusters:
            if rot_dist(g, cl[0]) < 0.5:
                cl[1] += 1
                break
        else:
            clusters.append([g, 1])
    rep, count = max(clusters, key=lambda c: c[1])
    return rep if count * 2 > len(gs) else None


def _affine(M, v):
    x, y, z = v
    return [M[0][0] * x + M[0][1] * y + M[0][2] * z + M[0][3],
            M[1][0] * x + M[1][1] * y + M[1][2] * z + M[1][3],
            M[2][0] * x + M[2][1] * y + M[2][2] * z + M[2][3]]


def _mat3_vec(R, v):
    x, y, z = v
    return [R[0][0] * x + R[0][1] * y + R[0][2] * z,
            R[1][0] * x + R[1][1] * y + R[1][2] * z,
            R[2][0] * x + R[2][1] * y + R[2][2] * z]


def _maintex_stem(bundle: _Bundle, mat_pid):
    """A Material's _MainTex Texture2D m_Name (the on-disc PNG stem), or None."""
    if not mat_pid:
        return None
    md = bundle.tt(mat_pid)
    if not md:
        return None
    try:
        for kv in md["m_SavedProperties"]["m_TexEnvs"]:
            key = kv[0] if isinstance(kv, (list, tuple)) else kv.get("first")
            val = kv[1] if isinstance(kv, (list, tuple)) else kv.get("second")
            kname = key.get("name") if isinstance(key, dict) else str(key)
            if kname == "_MainTex":
                tex_pid = _pid(val.get("m_Texture", {}))
                t = bundle.tt(tex_pid)
                return t.get("m_Name") if t else None
    except Exception:
        return None
    return None


def _read_textures(bundle: _Bundle, geo_id: int, stems: set) -> dict:
    """{stem: PIL.Image} for the wanted texture stems, read from this geo's container entries."""
    out: dict = {}
    if not stems:
        return out
    prefix = f"/{geo_id}/"
    for k, pptr in bundle.env.container.items():
        kl = k.lower()
        if pptr.type.name != "Texture2D" or prefix not in kl:
            continue
        d = pptr.read()
        nm = getattr(d, "m_Name", None)
        if nm in stems and nm not in out:
            try:
                out[nm] = d.image
            except Exception:
                pass
    return out
