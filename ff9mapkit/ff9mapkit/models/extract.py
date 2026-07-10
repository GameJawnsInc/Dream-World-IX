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
from .._modelalias import DBALL_SWITCH, GEOID_SPECIALS, REVERT_UPSCALE, SUB_TYPE_GEO_IDS, UPSCALE
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


def resolve_prefab(token: str) -> tuple[str, int, int]:
    """Where a model's GEOMETRY actually ships: token -> (prefab_name, prefab_id, prefab_type_int).

    ~103 of the 710 GEO catalog ids have NO prefab under their own id -- a character BATTLE form's
    body is the very prefab its FIELD form loads (``GEO_MAIN_B0_000`` -> 98 = ``GEO_MAIN_F0_ZDN``),
    bosses borrow character bodies, Zidane's alt outfits share 98, three accessories point at their
    F1 twin. The engine finds the donor by ``CheckUpscale`` -> ``GetRenameModelPath``
    (ModelFactory.cs); this replays that chain from the baked ``_modelalias`` tables:

      1. ``UPSCALE`` maps the requested name into the HD-rename space,
      2. ``REVERT_UPSCALE`` (falling back to ``DBALL_SWITCH`` + a second revert =
         ``GetNameFromFF9DBALL``) maps it back to the name whose prefab ships,
      3. the id comes from ``GEOID_SPECIALS`` (two names the GEO table never lists) else the GEO
         table; the type dir from the POST-UPSCALE name's group (that's what the engine's
         ``GetModelType(upscalePath)`` reads), with the ``GEO_WEP`` + ``SUB_TYPE_GEO_IDS`` overrides.

    Identity is untouched: :func:`resolve_geo` keeps returning the REQUESTED (name, id, type) --
    animations key off the requested id (``animations/5414`` = Zidane's 36 battle clips; the prefab
    id 98 holds his 400 FIELD clips) and every mint/anim/deploy caller depends on that. Only the two
    prefab lookups (and the loose-override target, which the engine probes POST-alias) go through
    here. An un-aliased model returns its own identity unchanged."""
    geo, gid, tint = resolve_geo(token)
    up = UPSCALE.get(geo, geo)                                 # CheckUpscale
    resolved = REVERT_UPSCALE.get(up)                          # GetRenameModelPath...
    if resolved is None:
        r = DBALL_SWITCH.get(up, up)                           # ...via GetNameFromFF9DBALL
        resolved = REVERT_UPSCALE.get(r, r)
    pgid = GEOID_SPECIALS.get(resolved, _NAME_TO_ID.get(resolved, -1))   # GetGEOID
    if pgid == -1:
        return geo, gid, tint                                  # unresolvable -> the requested identity
    if resolved.startswith("GEO_WEP"):
        return resolved, pgid, _TYPE_INT["wep"]
    ptint = _TYPE_INT.get(up.split("_")[1].lower(), tint)      # type dir = the POST-UPSCALE name's group
    if pgid in SUB_TYPE_GEO_IDS:
        ptint = _TYPE_INT["sub"]                               # the two mask prefabs live in models/5/
    return resolved, pgid, ptint


def is_battle_form(geo_name: str) -> bool:
    """True for a BATTLE-form GEO name (``GEO_MAIN_B0_*`` / ``GEO_MON_B3_*`` / any ``B*`` form token).
    Decides which overlay subtree a prefab walk hides -- the engine shows ``battle_model*`` and hides
    ``field_model*`` in battle, and the reverse on a field (ModelFactory.CreateModel:179-198)."""
    parts = str(geo_name).split("_")
    return len(parts) > 2 and parts[2].startswith("B")


def overlay_hide_prefixes(geo_name: str) -> tuple:
    """The overlay-subtree name prefixes a prefab walk HIDES for this requested form. Field/world forms
    hide ``battle_model*`` (the old behavior, unchanged); battle forms hide ``field_model*`` and KEEP
    the battle overlay -- except ``GEO_MAIN_B0_001`` (ZIDANE_SWORD), where the engine ADDITIONALLY
    hides the Orichalcum overlay (BattlePlayerCharacter.HideZidaneOrichalcum) -> body only."""
    if str(geo_name).upper() == "GEO_MAIN_B0_001":
        return ("battle_model", "field_model")
    return ("field_model",) if is_battle_form(geo_name) else ("battle_model",)


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
        self.data_index = data_index
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


def _open_prefab(token: str, game=None, bundle: "_Bundle | None" = None) -> tuple:
    """Resolve ``token`` to its shipping PREFAB and open it -> (geo, gid, tint, prefab_geo, prefab_id,
    prefab_tint, bundle, root_pid). The single gate both prefab walks go through.

    The container lookup runs on the PREFAB identity (:func:`resolve_prefab`) -- the fix for the ~103
    catalog ids with no own-id prefab (character battle forms, boss aliases, Zidane's alt outfits): the
    old requested-id lookup raised a fake ``models/2/5414/5414.fbx`` miss for them. A passed ``bundle``
    is reused only when it holds the right p0data archive. 43 ids have geometry NOWHERE (PSX-era
    leftovers, e.g. the whole unused ``GEO_MAIN_B2_*`` band) -> an actionable refusal, not a fake path."""
    geo, gid, tint = resolve_geo(token)
    pgeo, pgid, ptint = resolve_prefab(token)
    didx = _model_bundle_index(ptint)
    b = bundle if bundle is not None and getattr(bundle, "data_index", didx) == didx else \
        _Bundle(game, data_index=didx)
    root_pid = b.find_prefab_go(ptint, pgid)
    if root_pid is None:
        sub = "battlemap/battlemodel/6" if ptint == 6 else f"models/{ptint}"
        where = f"{sub}/{pgid}/{pgid}.fbx in p0data{didx}.bin"
        if (pgeo, pgid) == (geo, gid):
            raise FileNotFoundError(
                f"{geo} (id {gid}) is an UNSHIPPED model: no geometry on disc (nothing at {where}, and "
                f"no donor in the engine's alias tables). The GEO catalog lists PSX-era leftover ids "
                f"that never shipped a PC prefab -- this one cannot be exported or previewed.")
        raise FileNotFoundError(
            f"{geo} (id {gid}) resolves to donor prefab {pgeo} (id {pgid}) but {where} is missing -- "
            f"damaged install?")
    return geo, gid, tint, pgeo, pgid, ptint, b, root_pid


def _collect(token: str, game=None, bundle: "_Bundle | None" = None) -> dict:
    """Walk a real model prefab -> raw bones + per-SMR meshes (NO bind correction applied yet).

    Shared by :func:`read_model` (which applies the correction + reads textures) and
    :func:`bind_diagnostics` (which characterizes the bind-space variation). Returns a dict:
      geo, geo_id, type_int, prefab_geo/prefab_id/prefab_tint (where the geometry ships -- differs
      from the requested identity for alias models), bundle, bones[], root_bone, smrs[] where each
      smr is {name, mesh(decoded), idx_to_num, mat_stems, weights, samples=[(bone_name, m_BindPose)]}.
    Bone weights are REMAPPED to FF9 bone NUMBERS (skeleton-order-independent); ``samples`` carry the
    m_BindPose per bone of THIS mesh (kept per-SMR so the correction can be computed mesh-by-mesh).
    Pass ``bundle`` to reuse an already-loaded p0data4 across many models (bulk sweeps)."""
    geo, gid, tint, pgeo, pgid, ptint, b, root_pid = _open_prefab(token, game, bundle)
    root_tt = b.tt(root_pid)

    # --- walk the transform hierarchy: collect bones + SkinnedMeshRenderers ---
    bones: list[dict] = []          # {name, parent, pos, rot, scale}  (hierarchy/pre-order)
    bone_pid_to_name: dict = {}      # transform pathid -> bone name (for skin remap)
    smr_pids: list = []              # (smr_pathid, enclosing_mesh_go_name)  enclosing = nearest ANCESTOR mesh GO

    # A character prefab bundles per-MODE overlay subtrees next to the shared body (mesh*): the engine
    # hides ``battle_model*`` on a field load and ``field_model*`` in battle (ModelFactory.CreateModel).
    # Mirror that from the REQUESTED form (overlay_hide_prefixes): a field/world form drops the battle
    # overlay (unchanged behavior), a battle form drops the field overlay and KEEPS the battle one
    # (Zidane's B0_000 = body + the 103-vert Orichalcum daggers -- the body itself is mesh0/1, the same
    # prefab the field loads). Mixing overlay + body bind spaces is safe: the correction is computed
    # PER MESH (read_model). Bones are the shared skeleton, so they're kept regardless.
    hide_prefixes = overlay_hide_prefixes(geo)

    def walk(tr_pid, tr_tt, parent_name, in_hidden, enclosing_mesh):
        if not tr_tt:
            return
        go_pid = _pid(tr_tt.get("m_GameObject", {}))
        go_tt = b.tt(go_pid)
        name = go_tt.get("m_Name") if go_tt else None
        is_bone = bool(name and re.fullmatch(r"bone\d+", str(name)))
        here_hidden = in_hidden or bool(name and str(name).lower().startswith(hide_prefixes))
        if is_bone:
            bones.append({
                "name": name, "parent": parent_name,
                "pos": _vec3(tr_tt.get("m_LocalPosition")),
                "rot": _quat(tr_tt.get("m_LocalRotation", {})),
                "scale": _vec3(tr_tt.get("m_LocalScale"), (1.0, 1.0, 1.0)),
            })
            bone_pid_to_name[tr_pid] = name
        has_smr = False
        if go_tt and not here_hidden:
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
            walk(cpid, b.tt(cpid), child_parent, here_hidden, child_enclosing)

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
            "prefab_geo": pgeo, "prefab_id": pgid, "prefab_tint": ptint,
            "bones": bones, "root_bone": root_bone, "smrs": smrs}


def read_model(token: str, game=None, bundle: "_Bundle | None" = None) -> dict:
    """Read a real model prefab -> the Model struct consumed by :mod:`ff9mapkit.models.fbx_skin`.

    ``token`` is a GEO name (``GEO_NPC_F0_...``) or a model id. Returns a dict:
      geo, geo_id, type_int (the REQUESTED identity -- what animations key off), prefab_geo/
      prefab_id/prefab_tint (where the geometry SHIPS -- differs for the ~60 alias models, e.g.
      ``GEO_MAIN_B0_000`` -> prefab 98; also the loose-override folder the engine probes), root_bone,
      bones[], meshes[], materials[], textures{stem: PIL.Image}.
    Bone weights in each mesh are REMAPPED to FF9 bone NUMBERS (skeleton-order-independent).
    Pass ``bundle`` to reuse an already-loaded p0data4 across many models (bulk sweeps)."""
    c = _collect(token, game, bundle=bundle)
    bones, smrs, b = c["bones"], c["smrs"], c["bundle"]
    if not smrs:
        # A STATIC prefab (no SkinnedMeshRenderer): weapons (GEO_WEP_*) + some props. Read its MeshFilter
        # geometry wrapped in a trivial 1-bone rig, so the skinned emitter + the whole model-gltf/import
        # pipeline handle it unchanged (the engine imports a bone-less/1-bone mesh as a rigid model).
        return read_static_model(token, game=game, bundle=b)

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

    textures = _read_textures(b, c["prefab_id"], texture_stems)   # stems live under the PREFAB's folder
    _swap_alt_outfit_textures(c["geo"], c["geo_id"], b, textures)
    non_null = [g for g in per_mesh_G if g is not None]
    return {"geo": c["geo"], "geo_id": c["geo_id"], "type_int": c["type_int"], "root_bone": c["root_bone"],
            "prefab_geo": c["prefab_geo"], "prefab_id": c["prefab_id"], "prefab_tint": c["prefab_tint"],
            "bones": bones, "meshes": meshes, "materials": materials, "textures": textures,
            "bind_correction": non_null[0] if non_null else None, "per_mesh_bind": per_mesh_G}


def read_static_model(token: str, game=None, bundle: "_Bundle | None" = None) -> dict:
    """Read a STATIC model prefab (``MeshFilter`` + ``MeshRenderer``, no skeleton — e.g. weapons) into the
    same Model struct the skinned pipeline consumes, by wrapping it in a trivial 1-bone rig: a single
    ``bone000`` at the origin (identity) with every vertex weighted 100% to it. The engine imports a
    1-bone mesh as a rigid model that renders exactly as the original (bone000 = identity → no
    deformation), so the emitter / ``model-gltf`` / ``model-import`` all work unchanged. Weapons attach to
    the character's hand bone in battle code (``btl_eqp``), so the model itself is just a rigid mesh at the
    origin. No bind correction (a static mesh has no ``m_BindPose`` — its verts are already model-space)."""
    geo, gid, tint, pgeo, pgid, ptint, b, root_pid = _open_prefab(token, game, bundle)

    found: list = []                 # (mesh_pid, [mat_pids], go_name), pre-order
    seen: set = set()

    def walk(tr_pid, tr_tt):
        if not tr_tt:
            return
        go_tt = b.tt(_pid(tr_tt.get("m_GameObject", {})))
        if go_tt:
            mesh_pid = None
            mat_pids: list = []
            for tn, pid in b.components(go_tt):
                if tn == "MeshFilter":
                    mesh_pid = _pid((b.tt(pid) or {}).get("m_Mesh", {}))
                elif tn == "MeshRenderer":
                    mat_pids = [_pid(mp) for mp in (b.tt(pid) or {}).get("m_Materials", [])]
            if mesh_pid and mesh_pid not in seen:
                seen.add(mesh_pid)
                found.append((mesh_pid, mat_pids, go_tt.get("m_Name")))
        for ch in tr_tt.get("m_Children", []):
            cpid = _pid(ch)
            walk(cpid, b.tt(cpid))

    root_tpid, root_ttr = b.transform_of(b.tt(root_pid))
    walk(root_tpid, root_ttr)
    if not found:
        raise ValueError(f"{geo} (id {gid}) has no MeshFilter geometry to export (empty prefab).")

    bones = [{"name": "bone000", "parent": None, "pos": [0.0, 0.0, 0.0],
              "rot": [0.0, 0.0, 0.0, 1.0], "scale": [1.0, 1.0, 1.0]}]
    meshes: list = []
    materials: list = []
    texture_stems: set = set()
    for mesh_pid, mat_pids, goname in found:
        mesh = _decode_mesh_tt(b, mesh_pid)
        name = mesh.get("name") or goname or f"mesh{len(meshes)}"
        mat_stems = [_maintex_stem(b, mp) for mp in mat_pids]
        for st in mat_stems:
            if st:
                texture_stems.add(st)
        base_mat = len(materials)
        subs = []
        for si, tris in enumerate(mesh["submeshes"]):
            subs.append({"material_idx": base_mat + si, "tris": tris})
            materials.append({"name": f"{name}_mat{si}",
                              "texture": mat_stems[si] if si < len(mat_stems) else (
                                  mat_stems[0] if mat_stems else None)})
        meshes.append({
            "name": name, "verts": mesh["verts"],
            "normals": mesh["normals"] or [[0.0, 1.0, 0.0]] * len(mesh["verts"]),
            "uvs": mesh["uvs"], "submeshes": subs,
            "weights": [[(0, 1.0)] for _ in mesh["verts"]],   # every vert 100% -> bone000
            "parent": None})
    textures = _read_textures(b, pgid, texture_stems)             # stems live under the PREFAB's folder
    _swap_alt_outfit_textures(geo, gid, b, textures)
    return {"geo": geo, "geo_id": gid, "type_int": tint, "root_bone": "bone000",
            "prefab_geo": pgeo, "prefab_id": pgid, "prefab_tint": ptint,
            "bones": bones, "meshes": meshes, "materials": materials, "textures": textures,
            "bind_correction": None, "per_mesh_bind": [None] * len(meshes)}


_ALT_TEXTURE_FORMS = {"GEO_MAIN_F3_ZDN", "GEO_MAIN_F4_ZDN", "GEO_MAIN_F5_ZDN"}


def _swap_alt_outfit_textures(geo: str, gid: int, bundle: _Bundle, textures: dict) -> None:
    """Zidane's alt outfits (F3/F4/F5) share prefab 98 but carry their OWN art: the engine loads
    ``models/2/{gid}/{gid}_{n}.png`` and reassigns it over the prefab texture, keeping the OLD texture
    name (ModelFactory.CreateModel:75-91). Mirror that: swap each prefab stem's IMAGE for the
    requested-id image with the same ``_{n}`` suffix, keeping the stem KEY (material references and
    on-disc texture names stay the prefab's, exactly like the engine). Missing alt art -> keep the
    prefab image. No-op for every other model."""
    if geo not in _ALT_TEXTURE_FORMS or not textures:
        return
    want = {f"{gid}_{stem.rsplit('_', 1)[-1]}": stem for stem in textures}
    alt = _read_textures(bundle, gid, set(want))
    for alt_stem, stem in want.items():
        if alt_stem in alt:
            textures[stem] = alt[alt_stem]


_OVERLAY_PREFIXES = ("battle_model", "field_model")


def strip_overlay_meshes(model: dict, warn=None) -> list:
    """Drop the engine's per-mode overlay meshes (``battle_model*`` / ``field_model*``) from a Model
    struct before a LOOSE-OVERRIDE deploy of a real id. Mutates in place; returns the dropped names.

    WHY: a shared character prefab carries both modes' geometry, and at load the engine hides the
    wrong mode's subtree BY NAME -- ``GetChildByName("battle_model")``, an exact match on the subtree
    ROOT. The loose-FBX importer flattens every mesh to a direct child named after the MESH
    (``battle_model0``), so that hide can never fire on an override: a deployed overlay would render
    in BOTH modes (field Zidane grows the battle-only Orichalcum daggers). Stripping matches what a
    field-form override always shipped (body only); battle loses only the cosmetic overlay. To keep an
    overlay mesh in both modes deliberately, rename it in Blender first. Materials no surviving
    submesh references are compacted away (the FBX emitter writes EVERY ``materials[]`` row, and a
    dangling one would shift the engine importer's material indexing) and their textures pruned."""
    meshes = model.get("meshes") or []
    drop = [me for me in meshes if str(me.get("name", "")).lower().startswith(_OVERLAY_PREFIXES)]
    if not drop:
        return []
    drop_ids = {id(me) for me in drop}
    model["meshes"] = [me for me in meshes if id(me) not in drop_ids]
    mats = model.get("materials") or []
    used = sorted({sub["material_idx"] for me in model["meshes"] for sub in me.get("submeshes") or []
                   if 0 <= sub.get("material_idx", -1) < len(mats)})
    remap = {old: new for new, old in enumerate(used)}
    model["materials"] = [mats[i] for i in used]
    for me in model["meshes"]:
        for sub in me.get("submeshes") or []:
            if sub.get("material_idx") in remap:
                sub["material_idx"] = remap[sub["material_idx"]]
    stems = {m.get("texture") for m in model["materials"] if m.get("texture")}
    if isinstance(model.get("textures"), dict):
        model["textures"] = {k: v for k, v in model["textures"].items() if k in stems}
    dropped = [me["name"] for me in drop]
    if warn:
        warn(f"stripped {len(dropped)} overlay mesh(es) ({', '.join(dropped)}): the engine hides an "
             f"overlay by its subtree NAME, which a loose-FBX override flattens away -- deployed, it "
             f"would render in BOTH field and battle. The override ships the shared body (what a "
             f"field-form override always shipped); rename the mesh in Blender to keep it deliberately.")
    return dropped


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
