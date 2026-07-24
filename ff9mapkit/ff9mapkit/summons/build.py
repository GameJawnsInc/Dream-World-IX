"""The Model-struct adapter (TRANSPLANT.md section 3.3): turn a decoded summon creature (``summons.container``'s
``Geom`` -- skeleton parent+length tree, mesh table, run-length rigid skinning) and its motion clips
(``summons.motion``) into the EXACT dict shapes the kit's own glTF emission path consumes.

Matched shapes (cited so a drift is easy to catch in review):

  * the Model struct == ``ff9mapkit.models.extract.read_model``'s return value, walked by
    ``models/gltf.py:emit_model_gltf`` and ``models/fbx_skin.py:emit_skinned_fbx``::

        {"geo","geo_id","type_int","root_bone",
         "bones":  [{"name","parent","pos":[x,y,z],"rot":[x,y,z,w],"scale":[sx,sy,sz]}, ...],
         "meshes": [{"name","verts":[[x,y,z],...],"normals":None,"uvs":[[u,v],...],
                     "submeshes":[{"material_idx","tris":[[a,b,c],...]}],
                     "weights":[[(bone_num,weight),...],...]}, ...],
         "materials": [{"name","texture"}, ...], "textures": {}}

    ``bones[k]["pos"/"rot"/"scale"]`` are LOCAL (relative to ``parent``) -- both ``fbx_skin.bone_world``
    and ``gltf.py``'s ``world()`` recompute the WORLD matrix from exactly these fields by walking the
    parent chain, so the mesh verts below must be baked with the SAME forward-kinematics composition
    (see :func:`_forward_kinematics`) or the round-trip drifts.

  * the clip struct == ``ff9mapkit.models._gltf_io.read_clip``'s return value, walked by
    ``models/gltf.py:emit_model_gltf``'s animation loop (``clip["bones"][path]`` -> rot/pos/scale curves,
    ``path.split("/")[-1]`` resolved to a bone number)::

        {"name","sample_rate","length",
         "bones": {"boneNNN": {"rot": [(t,(x,y,z,w)), ...], "pos": [(t,(x,y,z)), ...]}}}

Geometry provenance (TRANSPLANT.md section 3.1, PROVEN math): node rest TRS = ``(restRot[b], (0,0,length[b]))``;
bind-pose verts = ``W[b] * pool_vertex`` where ``W[b]`` is bone b's WORLD transform under the chosen rest
pose. Skinning is rigid + run-length (``container.bone_of_vertex``) -> exactly one ``(bone, 1.0)`` weight per
vertex, no weight solve.

Coordinate convention (a documented ASSUMPTION, not itself M0-measured -- open question, not a claim): the
PSX creature's raw (x, y, z) are used VERBATIM as FF9-model-space (x, y, z), the same convention
``models/extract.py`` reads real models in (both Y-DOWN per ``models/gltf.py``'s own negate-Y FF9->glTF
comment). This rests on ``m0/CALIBRATION.md``'s ``PsxToUnityPos(tx,ty,tz)=(tx,-ty,tz)`` scale-1 map (negate-Y,
scale 1) lining up with that same negate-Y convention -- PLAUSIBLE, since that calibration was measured for
the live world-point hybrid (a different data path), not this offline bone-local geometry. No extra
transform is applied here; ``models/gltf.py`` applies its one uniform Y-negate + ``DEFAULT_SCALE`` bake at
emit time, exactly as it does for every real FF9 model.

Textures: :func:`adapt_model` has TWO modes.

  * ``part_images=None`` (the default) -- the original UNTEXTURED shape: one material per MESH carrying
    ``texture=None``, one welded vertex per pool entry, UVs as raw ``/255`` pool bytes that no image ever
    binds. Unchanged byte-for-byte from before the texture rung.
  * ``part_images={part: PIL image}`` (from :func:`ff9mapkit.summons.texture.decode_pages`) -- the TEXTURED
    shape. Texture binding in this format is **per-face-per-part**, not per-mesh (M4 section 5.3): every
    textured face carries a ``part`` byte selecting one of the <=6 ``{tpage, clut}`` materials, so one mesh
    mixes several pages. The adapter therefore groups a mesh's faces into one SUBMESH per part, splits any
    vertex whose corners disagree on UV, and normalises UVs against the real 128x128 page with the
    V-offset bake applied (``texture.uv_texcoord``).

Pure logic (no I/O beyond a caller-supplied blob); embeds no game bytes and writes nothing (glTF WRITE is
``summons/export.py``, a later module).
"""
from __future__ import annotations

import math
import struct
from typing import Dict, List, Optional, Sequence, Tuple

from . import container, motion, texture

__all__ = [
    "DEFAULT_FPS", "UNBOUND_PART", "mat3_to_quat", "rest_angles_from_clip",
    "adapt_model", "adapt_clip", "adapt_all_clips",
]

# PSX summon clips carry no stored tick rate (FORMAT.md 2.4: "one sample per rendered frame ... no
# interpolation, no keyframe times"). 15.0 documents TRANSPLANT.md 1.3's residual note ("~15 fps
# native-tick sampling") -- a DESIGN DEFAULT for clip playback speed in Blender, not a measured constant;
# it affects only how fast a preview plays, never skeleton/weight/topology correctness.
DEFAULT_FPS = 15.0


def mat3_to_quat(R) -> Tuple[float, float, float, float]:
    """A proper 3x3 rotation matrix -> quaternion ``(x, y, z, w)`` (Shepperd's method -- branches on the
    largest diagonal term for numerical stability near 180-degree rotations; the same algorithm
    ``models/gltf.py``'s ``_node_local_trs`` uses for a glTF node matrix, ported here for a bare 3x3).
    ``motion.build_rotation`` always returns a proper rotation (det==+1 by construction, three standard
    per-axis matrices multiplied together) -- unlike the LIVE per-frame matrices the s54 hybrid drive
    reads straight off ``SummonData+0x38`` (which CALIBRATION.md found can be improper on ~25 climax-hold
    frames), so no ``det<0`` guard is needed for this offline clip-decode path."""
    m00, m01, m02 = R[0]
    m10, m11, m12 = R[1]
    m20, m21, m22 = R[2]
    tr = m00 + m11 + m22
    if tr > 0:
        s = math.sqrt(tr + 1.0) * 2
        return ((m21 - m12) / s, (m02 - m20) / s, (m10 - m01) / s, 0.25 * s)
    if m00 > m11 and m00 > m22:
        s = math.sqrt(1.0 + m00 - m11 - m22) * 2
        return (0.25 * s, (m01 + m10) / s, (m02 + m20) / s, (m21 - m12) / s)
    if m11 > m22:
        s = math.sqrt(1.0 + m11 - m00 - m22) * 2
        return ((m01 + m10) / s, 0.25 * s, (m12 + m21) / s, (m02 - m20) / s)
    s = math.sqrt(1.0 + m22 - m00 - m11) * 2
    return ((m02 + m20) / s, (m12 + m21) / s, 0.25 * s, (m10 - m01) / s)


def _mat3_mul(A, B):
    return tuple(tuple(sum(A[r][k] * B[k][c] for k in range(3)) for c in range(3)) for r in range(3))


def _forward_kinematics(angles: Sequence[Tuple[int, int, int]], lengths: Sequence[int],
                        parents: Sequence[int]):
    """WORLD (rotation, translation) per node under one chosen pose -- mirrors
    ``transplant_spike.compose_skeleton`` but also carries the rotation (needed to bake bind-pose VERTS,
    not just node translations). ``node0`` is the root: ``R[0] = build_rotation(angles[0])``,
    ``t[0] = (0,0,0)`` (``lengths[0] == 0`` by construction -- ``Geom.lengths()`` -- so the same
    ``(0,0,length[k])`` local-offset formula already gives the root (0,0,0), no special case needed for
    translation; ``parent`` DOES need a k==0 special case -- see :func:`adapt_model`)."""
    n = len(lengths)
    R: List[tuple] = [None] * n
    t: List[Tuple[float, float, float]] = [None] * n
    R[0] = motion.build_rotation(*angles[0])
    t[0] = (0.0, 0.0, 0.0)
    for k in range(1, n):
        p = parents[k]
        Rp = R[p]
        R[k] = _mat3_mul(Rp, motion.build_rotation(*angles[k]))
        length = float(lengths[k])
        t[k] = (t[p][0] + Rp[0][2] * length, t[p][1] + Rp[1][2] * length, t[p][2] + Rp[2][2] * length)
    return R, t


def rest_angles_from_clip(blob: bytes, bone_count: int, clip: "motion.Clip",
                          frame: int = 0) -> List[Tuple[int, int, int]]:
    """Read one clip frame's decoded per-node angles for use as the skeleton's REST pose -- TRANSPLANT.md
    3.1's "clip[0]f0" option (a recognizable dragon instead of the straight-identity default)."""
    angles, _is_track, _touched = motion.decode_rotation(blob, clip, frame, bone_count)
    return angles


def _mesh_uvs(blob: bytes, g: "container.Geom", mesh: "container.Mesh") -> List[List[float]]:
    """Per-vertex ``[u, v]`` in [0,1], first-writer-wins across every primitive referencing that vertex
    (a shared vertex may carry more than one UV index for a real atlas seam; FF9's creatures use only
    FT4/FT3, both textured, so every vertex the closure proves reachable gets one). UV pool entries are
    ``u16 == (u | v<<8)`` -- an inline PSX ``(u8 u, u8 v)`` pair (the study's ``M4-mesh-payload.md``
    line 275, corpus-checked; FORMAT.md section 2.3 independently proves the pool is u16-WIDE and
    u16-indexed via the ``maxUVIndex == uvCount-1`` law, 969/969). These are the PRE-BAKE on-disk values
    -- FORMAT.md 2.3 also notes a load-time UV V-offset bake mutates the pool once in live memory, which
    this offline reader never sees; moot here since texture/CLUT emission is explicitly out of scope
    (see the module docstring) -- no material ever binds these coordinates to an actual image yet."""
    n = mesh.n_vert
    uv: List[Optional[List[float]]] = [None] * n
    pool = g.base + mesh.p_uv
    for prim in container.iter_primitives(blob, g, mesh):
        idxs = prim.get("uv")
        if not idxs:
            continue
        for vi, ui in zip(prim["v"], idxs):
            if uv[vi] is None:
                word = struct.unpack_from("<H", blob, pool + 2 * ui)[0]
                uv[vi] = [(word & 0xFF) / 255.0, ((word >> 8) & 0xFF) / 255.0]
    return [u if u is not None else [0.0, 0.0] for u in uv]


def _mesh_tris(blob: bytes, g: "container.Geom", mesh: "container.Mesh") -> List[List[int]]:
    """Fan-triangulate every primitive's vertex-index list (``FT4`` = 2 tris, ``FT3`` = 1 -- FORMAT.md
    section 2.3: creatures use only these two, both already ordered around the face perimeter)."""
    tris: List[List[int]] = []
    for prim in container.iter_primitives(blob, g, mesh):
        v = prim["v"]
        tris.append([v[0], v[1], v[2]])
        if len(v) == 4:
            tris.append([v[0], v[2], v[3]])
    return tris


UNBOUND_PART = -1
"""The material bucket for a face that binds no decoded page: an untextured bucket (``G4``/``G3``/``F4``/
``F3`` -- no UV indices at all), or a ``part`` byte past the package's ``partCount``. The latter is real
stock data, not corruption: 6 of the 24 creature packages index past ``partCount`` and the engine's
6-slot part table is zero-filled below it, so those faces render with ``tpage = clut = 0`` (D3 section 3.3)
-- an unrelated corner of VRAM. Exporting them UNTEXTURED is the honest reading; inventing a page for them
would be a guess."""


def _skinned_vertex(src, bone_of, vi, R_world, t_world):
    """One pool vertex -> its bind-pose world position + its single rigid weight (the run-length skin)."""
    x, y, z, _w = src[vi]
    b = bone_of[vi]
    R, t = R_world[b], t_world[b]
    return ([R[0][0] * x + R[0][1] * y + R[0][2] * z + t[0],
             R[1][0] * x + R[1][1] * y + R[1][2] * z + t[1],
             R[2][0] * x + R[2][1] * y + R[2][2] * z + t[2]], b)


def _adapt_meshes_textured(blob: bytes, g: "container.Geom", R_world, t_world, geo: str,
                           part_images: Dict[int, object],
                           v_offsets: Sequence[int]) -> Tuple[list, list, dict]:
    """The per-face-per-part build: ``(meshes, materials, textures)`` for the Model struct.

    One material per USED part (model-wide, so a part shared by both meshes is one material and one embedded
    image), one submesh per part inside each mesh, and a vertex split whenever two faces disagree on the UV
    (or the V-offset) at a shared pool vertex -- FF9's pool has no per-vertex UV, so a seam vertex genuinely
    carries several. UVs come out in the kit's bottom-left convention (``models/gltf.py`` re-flips them to
    glTF's top-left origin at emit time), which is why the ``1.0 -`` appears here."""
    def _part_of(prim):
        p = prim.get("part", UNBOUND_PART) if prim.get("uv") else UNBOUND_PART
        return p if p in part_images else UNBOUND_PART

    used = sorted({_part_of(p) for m in g.meshes for p in container.iter_primitives(blob, g, m)})
    mat_of = {p: i for i, p in enumerate(used)}
    materials, textures = [], {}
    for p in used:
        img = part_images.get(p)
        stem = f"{geo}_page{p}" if img is not None else None
        if stem is not None:
            textures[stem] = img
        materials.append({"name": f"{geo}_part{p}" if p != UNBOUND_PART else f"{geo}_untextured",
                          "texture": stem})

    meshes = []
    for mi, mesh in enumerate(g.meshes):
        bone_of = container.bone_of_vertex(mesh)
        src = list(container.vertices(blob, g, mesh))
        pool = g.base + mesh.p_uv
        remap: Dict[tuple, int] = {}
        verts, uvs, weights = [], [], []
        tris_by_part: Dict[int, list] = {}
        for prim in container.iter_primitives(blob, g, mesh):
            part = _part_of(prim)
            uv_idx = prim.get("uv") if part != UNBOUND_PART else None
            voff = v_offsets[part] if 0 <= part < len(v_offsets) else 0
            corner = []
            for n, vi in enumerate(prim["v"]):
                ui = uv_idx[n] if uv_idx else None
                # Key on the UV VALUE, not the pool index: FF9 stores one pool entry per face CORNER
                # (uvCount == the 4/3/4/3-per-face sum), so keying on the index would split every shared
                # edge. Keying on the resolved coordinate re-welds the corners that genuinely agree
                # (ef227: 7331 pool entries -> 1921 verts over a 1439-vertex pool) while still splitting
                # a real UV seam.
                uv = (texture.uv_texcoord(struct.unpack_from("<H", blob, pool + 2 * ui)[0], voff)
                      if ui is not None else None)
                key = (vi, uv)
                j = remap.get(key)
                if j is None:
                    j = len(verts)
                    remap[key] = j
                    pos, b = _skinned_vertex(src, bone_of, vi, R_world, t_world)
                    verts.append(pos)
                    uvs.append([0.0, 0.0] if uv is None else [uv[0], 1.0 - uv[1]])
                    weights.append([(b, 1.0)])
                corner.append(j)
            tris = tris_by_part.setdefault(part, [])
            tris.append([corner[0], corner[1], corner[2]])
            if len(corner) == 4:
                tris.append([corner[0], corner[2], corner[3]])
        meshes.append({
            "name": f"mesh{mi}", "verts": verts, "normals": None, "uvs": uvs,
            "submeshes": [{"material_idx": mat_of[p], "tris": tris_by_part[p]}
                          for p in sorted(tris_by_part)],
            "weights": weights,
        })
    return meshes, materials, textures


def adapt_model(blob: bytes, g: "container.Geom", *, geo: str = "SUMMON", geo_id: int = 0,
               rest_angles: Optional[Sequence[Tuple[int, int, int]]] = None,
               part_images: Optional[Dict[int, object]] = None,
               v_offsets: Sequence[int] = ()) -> dict:
    """The adapter: a decoded ``Geom`` -> the kit Model struct (module docstring). ``rest_angles`` is the
    per-node ``(ax, ay, az)`` 12-bit Euler REST rotation (e.g. :func:`rest_angles_from_clip`'s output);
    ``None`` (the default) means an IDENTITY rest pose -- "self-consistent design knob, not a gap"
    (TRANSPLANT.md 3.1). ``part_images`` (``{part: PIL image}`` from
    :func:`ff9mapkit.summons.texture.decode_pages`) switches on the TEXTURED build; ``v_offsets`` is the
    package's per-part texture V-offset array (``ModelPackage.v_offset``), needed for the UV bake."""
    parents = g.parents()
    lengths = g.lengths()
    n = g.bone_count
    angles = list(rest_angles) if rest_angles is not None else [(0, 0, 0)] * n
    R_world, t_world = _forward_kinematics(angles, lengths, parents)

    bones = []
    for k in range(n):
        bones.append({
            "name": f"bone{k:03d}", "parent": None if k == 0 else f"bone{parents[k]:03d}",
            "pos": [0.0, 0.0, float(lengths[k])], "rot": list(mat3_to_quat(motion.build_rotation(*angles[k]))),
            "scale": [1.0, 1.0, 1.0],
        })

    if part_images is not None:
        meshes, materials, textures = _adapt_meshes_textured(
            blob, g, R_world, t_world, geo, part_images, v_offsets)
        return {"geo": geo, "geo_id": geo_id, "type_int": None, "root_bone": "bone000",
                "bones": bones, "meshes": meshes, "materials": materials, "textures": textures}

    materials: list = []
    meshes: list = []
    for mi, mesh in enumerate(g.meshes):
        bone_of = container.bone_of_vertex(mesh)
        verts = []
        for (x, y, z, _w), b in zip(container.vertices(blob, g, mesh), bone_of):
            R, t = R_world[b], t_world[b]
            verts.append([R[0][0] * x + R[0][1] * y + R[0][2] * z + t[0],
                         R[1][0] * x + R[1][1] * y + R[1][2] * z + t[1],
                         R[2][0] * x + R[2][1] * y + R[2][2] * z + t[2]])
        mat_idx = len(materials)
        materials.append({"name": f"{geo}_mesh{mi}", "texture": None})
        meshes.append({
            "name": f"mesh{mi}", "verts": verts, "normals": None, "uvs": _mesh_uvs(blob, g, mesh),
            "submeshes": [{"material_idx": mat_idx, "tris": _mesh_tris(blob, g, mesh)}],
            "weights": [[(b, 1.0)] for b in bone_of],
        })

    return {"geo": geo, "geo_id": geo_id, "type_int": None, "root_bone": "bone000",
            "bones": bones, "meshes": meshes, "materials": materials, "textures": {}}


def adapt_clip(blob: bytes, bone_count: int, clip: "motion.Clip", *, name: Optional[str] = None,
              fps: float = DEFAULT_FPS) -> dict:
    """Decode ONE summon motion clip into the shape ``models/_gltf_io.py:read_clip`` returns (module
    docstring). Every node gets a DENSE per-frame rotation curve (the clip has no interpolation to thin --
    FORMAT.md 2.4); only node 0 (the root -- "only the root gets per-frame translation", FORMAT.md 2.4)
    gets a position curve. Per-frame angles are each node's own LOCAL rotation (not composed with its
    parent) -- exactly what a Unity legacy ``AnimationClip``'s per-bone curve stores, and exactly what
    ``gltf.py``'s ``"rotation"`` animation channel expects to SET on that bone each frame."""
    bones: Dict[str, dict] = {f"bone{k:03d}": {"rot": []} for k in range(bone_count)}
    root_pos = []
    for fr in range(clip.frame_count):
        angles, _is_track, _touched = motion.decode_rotation(blob, clip, fr, bone_count)
        t = fr / fps
        for k in range(bone_count):
            bones[f"bone{k:03d}"]["rot"].append((t, mat3_to_quat(motion.build_rotation(*angles[k]))))
        tx, ty, tz, _touched2 = motion.decode_root_translation(blob, clip, fr)
        root_pos.append((t, (float(tx), float(ty), float(tz))))
    bones["bone000"]["pos"] = root_pos
    length = (clip.frame_count - 1) / fps if clip.frame_count > 1 else 0.0
    return {"name": name or f"clip{clip.index}", "sample_rate": fps, "length": length, "bones": bones}


def adapt_all_clips(blob: bytes, mp: "container.ModelPackage", bone_count: int,
                    *, fps: float = DEFAULT_FPS) -> List[dict]:
    """:func:`adapt_clip` for every clip in a creature package, in file order."""
    out = []
    for i, off in enumerate(mp.motion_file_offsets):
        cl = motion.read_clip_header(blob, i, off)
        out.append(adapt_clip(blob, bone_count, cl, name=f"clip{i}", fps=fps))
    return out
