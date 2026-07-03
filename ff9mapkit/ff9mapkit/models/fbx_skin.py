"""Emit a SKINNED FBX-ASCII from a Model struct (:mod:`ff9mapkit.models.extract`) that Memoria's own
FBX importer (``Memoria/Assets/3DModel/*``) re-imports faithfully.

Pure (no I/O). The format is exactly what ``FbxAsciiReader`` + ``FbxDocument.GetSkeleton/GetGeometries``
+ ``FbxDeformer`` accept -- verified line-by-line against the reader:

  * one ``Geometry`` per mesh: ``Vertices`` + ``PolygonVertexIndex`` (LAST index of each face negated,
    the FBX polygon-end convention), ``LayerElementNormal`` / ``LayerElementUV`` (ByVertex / Direct);
  * one mesh ``Model`` (type "") per mesh, identity transform (so ``GetVertices`` leaves verts verbatim);
  * one bone ``Model`` per bone: the armature root typed ``"Root"`` (the reader forces its BoneId=0),
    every other bone ``"LimbNode"``, NAMED ``bone{NNN}`` so ``FbxSkeleton`` reads the FF9 bone NUMBER
    from the trailing 3 digits -- that name is what FF9's own animation clips bind to;
  * bone transforms as ``Lcl Translation`` / ``Lcl Rotation`` (EULER, order XYZ = the document default)
    / ``Lcl Scaling`` -- the importer RECOMPUTES bindposes from these, so they must reproduce the
    original rest pose;  the quaternion->euler here is the exact inverse of Memoria's
    ``SetupFromEulerAngles`` (q = qz*qy*qx) and is SELF-CHECKED per bone (recompose & compare);
  * a ``Deformer`` "Skin" per mesh + a ``Deformer`` "Cluster" per (mesh, bone) with ``Indexes`` +
    ``Weights`` (the only fields the importer reads) and correct ``Transform``/``TransformLink`` bind
    matrices (ignored by the engine, but needed for Blender to display the skin correctly);
  * ``Material`` + ``Texture`` (``RelativeFilename`` = ``{stem}.png``) per submesh material;
  * a ``Connections`` block wiring geometry->model, bone->parent, skin->geometry, cluster->skin,
    cluster->bone, texture->material (OP), material->model.
"""
from __future__ import annotations

import math

# ---------------------------------------------------------------- quaternion / matrix math

def _qmul(a, b):
    """Unity Hamilton product a*b (x,y,z,w)."""
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    )


def setup_from_euler_xyz(x_deg, y_deg, z_deg):
    """Memoria's ExtensionMethodsQuaternion.SetupFromEulerAngles(order=EULER_XYZ): q = qz*qy*qx."""
    h = math.pi / 360.0
    qx = (math.sin(x_deg * h), 0.0, 0.0, math.cos(x_deg * h))
    qy = (0.0, math.sin(y_deg * h), 0.0, math.cos(y_deg * h))
    qz = (0.0, 0.0, math.sin(z_deg * h), math.cos(z_deg * h))
    return _qmul(_qmul(qz, qy), qx)


def _quat_to_matrix(q):
    """(x,y,z,w) -> 3x3 rotation matrix (standard, matches Unity's quaternion algebra)."""
    x, y, z, w = q
    n = math.sqrt(x * x + y * y + z * z + w * w) or 1.0
    x, y, z, w = x / n, y / n, z / n, w / n
    return [
        [1 - 2 * (y * y + z * z), 2 * (x * y - w * z),     2 * (x * z + w * y)],
        [2 * (x * y + w * z),     1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
        [2 * (x * z - w * y),     2 * (y * z + w * x),     1 - 2 * (x * x + y * y)],
    ]


def quat_to_euler_xyz(q):
    """(x,y,z,w) -> (X,Y,Z) euler degrees for R = Rz*Ry*Rx (the decomposition matching qz*qy*qx)."""
    m = _quat_to_matrix(q)
    sy = -m[2][0]
    sy = max(-1.0, min(1.0, sy))
    Y = math.asin(sy)
    if abs(sy) < 0.9999995:
        X = math.atan2(m[2][1], m[2][2])
        Z = math.atan2(m[1][0], m[0][0])
    else:                                   # gimbal lock: fold Z into X
        X = math.atan2(-m[1][2], m[1][1])
        Z = 0.0
    return (math.degrees(X), math.degrees(Y), math.degrees(Z))


def _quat_close(a, b, eps=1e-4):
    """True if quaternions a,b represent the same rotation (double-cover: a == +/-b)."""
    d = sum(u * v for u, v in zip(a, b))
    return abs(abs(d) - 1.0) < eps


# 4x4 affine matrices as row-major 16-lists (FBX column-major order handled at emit time)

def _mat_trs(pos, quat, scale):
    r = _quat_to_matrix(quat)
    sx, sy, sz = scale
    return [
        [r[0][0] * sx, r[0][1] * sy, r[0][2] * sz, pos[0]],
        [r[1][0] * sx, r[1][1] * sy, r[1][2] * sz, pos[1]],
        [r[2][0] * sx, r[2][1] * sy, r[2][2] * sz, pos[2]],
        [0.0, 0.0, 0.0, 1.0],
    ]


def _mat_mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def _mat_inv(m):
    """Inverse of an affine 4x4 (general Gauss-Jordan; robust for scale/shear)."""
    n = 4
    a = [row[:] + [1.0 if i == j else 0.0 for j in range(n)] for i, row in enumerate(m)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(a[r][col]))
        if abs(a[piv][col]) < 1e-12:
            a[piv][col] += 1e-12
        a[col], a[piv] = a[piv], a[col]
        d = a[col][col]
        a[col] = [v / d for v in a[col]]
        for r in range(n):
            if r != col:
                f = a[r][col]
                a[r] = [a[r][k] - f * a[col][k] for k in range(2 * n)]
    return [row[n:] for row in a]


def _fbx_matrix_flat(m):
    """Row-major 4x4 -> FBX's column-major flat 16 (translation in the last 4)."""
    return [m[r][c] for c in range(4) for r in range(4)]


# ---------------------------------------------------------------- emit

def _f(v):
    return format(float(v), ".9g")


def _arr(name, values, per_line=None):
    vals = list(values)
    body = ",".join(_f(v) for v in vals)
    return f"{name}: *{len(vals)} {{\n    a: {body}\n}}"


class _Ids:
    def __init__(self):
        self._n = 1000000
    def next(self):
        self._n += 1
        return self._n


def emit_skinned_fbx(model: dict) -> tuple[str, dict]:
    """Model dict -> (fbx_ascii_text, meta). meta carries counts + the self-check result."""
    bones = model["bones"]
    meshes = model["meshes"]
    materials = model["materials"]
    root_bone = model["root_bone"]

    # --- bone world matrices (for cluster bind) + euler self-check ---
    by_name = {b["name"]: b for b in bones}
    world_cache: dict = {}

    def bone_world(name):
        if name in world_cache:
            return world_cache[name]
        b = by_name[name]
        local = _mat_trs(b["pos"], b["rot"], b["scale"])
        m = local if b["parent"] is None else _mat_mul(bone_world(b["parent"]), local)
        world_cache[name] = m
        return m

    euler_max_err = 0.0
    bad = []
    for b in bones:
        e = quat_to_euler_xyz(b["rot"])
        recomposed = setup_from_euler_xyz(*e)
        if not _quat_close(recomposed, b["rot"]):
            bad.append(b["name"])
        d = 1.0 - abs(sum(u * v for u, v in zip(recomposed, b["rot"])))
        euler_max_err = max(euler_max_err, abs(d))
        b["_euler"] = e
    if bad:
        raise ValueError(f"euler round-trip failed for bones {bad[:8]} "
                         f"(quat->euler XYZ != SetupFromEulerAngles inverse); max_err={euler_max_err:.2e}")

    ids = _Ids()
    obj_lines: list[str] = []
    conn_lines: list[str] = []

    # An "Armature" null-node parent for the root bone. The engine importer dereferences bone.Parent for
    # ANY bone whose boneParentId < 0 (ModelImporter.cs:108) -- a TRUE root with a null Parent NREs (the
    # model then loads as null -> invisible + a softlocked field). Giving the root a non-bone parent
    # (identity, BoneId stays -1) satisfies that with no DLL: the composed root transform is unchanged and
    # the root is still parented to the base object at build (its boneParentId remains -1). Mirrors how
    # Blender/Maya FBX structure a skeleton (Armature -> root bone).
    arm_id = ids.next()
    obj_lines.append(
        f'Model: {arm_id}, "Model::Armature", "Null" {{\n'
        f'    Version: 232\n'
        f'    Properties70: {{\n'
        f'        P: "Lcl Translation", "Lcl Translation", "", "A", 0, 0, 0\n'
        f'        P: "Lcl Rotation", "Lcl Rotation", "", "A", 0, 0, 0\n'
        f'        P: "Lcl Scaling", "Lcl Scaling", "", "A", 1, 1, 1\n'
        f'    }}\n'
        f'}}')

    # bone Model nodes
    bone_id = {}
    for b in bones:
        nid = ids.next()
        bone_id[b["name"]] = nid
        typ = "Root" if b["name"] == root_bone else "LimbNode"
        ex, ey, ez = b["_euler"]
        px, py, pz = b["pos"]
        sx, sy, sz = b["scale"]
        obj_lines.append(
            f'Model: {nid}, "Model::{b["name"]}", "{typ}" {{\n'
            f'    Version: 232\n'
            f'    Properties70: {{\n'
            f'        P: "Lcl Translation", "Lcl Translation", "", "A", {_f(px)}, {_f(py)}, {_f(pz)}\n'
            f'        P: "Lcl Rotation", "Lcl Rotation", "", "A", {_f(ex)}, {_f(ey)}, {_f(ez)}\n'
            f'        P: "Lcl Scaling", "Lcl Scaling", "", "A", {_f(sx)}, {_f(sy)}, {_f(sz)}\n'
            f'    }}\n'
            f'}}')
    # bone parent connections (child -> parent); the root bone parents to the Armature null (non-bone),
    # so the importer's root-branch bone.Parent deref (ModelImporter.cs:108) resolves instead of NREing.
    for b in bones:
        parent_id = bone_id[b["parent"]] if b["parent"] is not None else arm_id
        conn_lines.append(f'C: "OO", {bone_id[b["name"]]}, {parent_id}')

    # materials + textures
    mat_id = {}
    for mi, mat in enumerate(materials):
        mid = ids.next()
        mat_id[mi] = mid
        obj_lines.append(
            f'Material: {mid}, "Material::{mat["name"]}", "" {{\n'
            f'    Version: 102\n'
            f'    ShadingModel: "Phong"\n'
            f'    Properties70: {{ }}\n'
            f'}}')
        if mat.get("texture"):
            tid = ids.next()
            stem = mat["texture"]
            obj_lines.append(
                f'Texture: {tid}, "Texture::{stem}", "" {{\n'
                f'    Version: 202\n'
                f'    TextureName: "Texture::{stem}"\n'
                f'    Properties70: {{ }}\n'
                f'    FileName: "{stem}.png"\n'
                f'    RelativeFilename: "{stem}.png"\n'
                f'}}')
            conn_lines.append(f'C: "OP", {tid}, {mid}, "DiffuseColor"')

    # per-mesh geometry + model + skin/clusters
    for mesh in meshes:
        verts = mesh["verts"]
        geo_id = ids.next()
        model_id = ids.next()
        # polygon index: flatten submesh tris, negate the last index of each face
        poly = []
        for sub in mesh["submeshes"]:
            for tri in sub["tris"]:
                a, b2, c = tri
                poly += [a, b2, -(c + 1)]
        flat_v = [x for v in verts for x in v]
        geo = [f'Geometry: {geo_id}, "Geometry::{mesh["name"]}", "Mesh" {{']
        geo.append("    " + _arr("Vertices", flat_v).replace("\n", "\n    "))
        geo.append("    " + _arr("PolygonVertexIndex", poly).replace("\n", "\n    "))
        if mesh.get("normals"):
            flat_n = [x for v in mesh["normals"] for x in v]
            geo.append('    LayerElementNormal: 0 {')
            geo.append('        Version: 101\n        Name: "Normals"')
            geo.append('        MappingInformationType: "ByVertex"')
            geo.append('        ReferenceInformationType: "Direct"')
            geo.append("        " + _arr("Normals", flat_n).replace("\n", "\n        "))
            geo.append('    }')
        flat_uv = [x for uv in mesh["uvs"] for x in uv]
        geo.append('    LayerElementUV: 0 {')
        geo.append('        Version: 101\n        Name: "UVMap"')
        geo.append('        MappingInformationType: "ByVertex"')
        geo.append('        ReferenceInformationType: "Direct"')
        geo.append("        " + _arr("UV", flat_uv).replace("\n", "\n        "))
        geo.append('    }')
        geo.append('    Layer: 0 {\n        Version: 100\n    }')
        geo.append('}')
        obj_lines.append("\n".join(geo))

        obj_lines.append(
            f'Model: {model_id}, "Model::{mesh["name"]}", "Mesh" {{\n'
            f'    Version: 232\n'
            f'    Properties70: {{\n'
            f'        P: "Lcl Translation", "Lcl Translation", "", "A", 0, 0, 0\n'
            f'        P: "Lcl Rotation", "Lcl Rotation", "", "A", 0, 0, 0\n'
            f'        P: "Lcl Scaling", "Lcl Scaling", "", "A", 1, 1, 1\n'
            f'    }}\n'
            f'}}')
        conn_lines.append(f'C: "OO", {geo_id}, {model_id}')              # geometry -> mesh model
        # material for submesh 0 -> the mesh model (GetMaterialIndex looks up the model's material)
        if mesh["submeshes"]:
            m0 = mesh["submeshes"][0]["material_idx"]
            if m0 in mat_id:
                conn_lines.append(f'C: "OO", {mat_id[m0]}, {model_id}')

        # skin + clusters (group per-vertex influences by bone number)
        by_bone: dict = {}
        for vi, infl in enumerate(mesh["weights"]):
            for bnum, w in infl:
                by_bone.setdefault(bnum, []).append((vi, w))
        if by_bone:
            skin_id = ids.next()
            obj_lines.append(
                f'Deformer: {skin_id}, "Deformer", "Skin" {{\n'
                f'    Version: 100\n    Link_DeformAcc: 0\n}}')
            conn_lines.append(f'C: "OO", {skin_id}, {geo_id}')           # skin -> geometry
            for bnum, pairs in by_bone.items():
                bname = f"bone{bnum:03d}"
                if bname not in bone_id:
                    continue
                cl_id = ids.next()
                idxs = [vi for vi, _ in pairs]
                wts = [w for _, w in pairs]
                bw = bone_world(bname)
                transform = _mat_inv(bw)        # geometry(=identity) -> bone bind
                obj_lines.append(
                    f'Deformer: {cl_id}, "SubDeformer", "Cluster" {{\n'
                    f'    Version: 100\n'
                    f'    ' + _arr("Indexes", idxs).replace("\n", "\n    ") + '\n'
                    f'    ' + _arr("Weights", wts).replace("\n", "\n    ") + '\n'
                    f'    ' + _arr("Transform", _fbx_matrix_flat(transform)).replace("\n", "\n    ") + '\n'
                    f'    ' + _arr("TransformLink", _fbx_matrix_flat(bw)).replace("\n", "\n    ") + '\n'
                    f'}}')
                conn_lines.append(f'C: "OO", {cl_id}, {skin_id}')        # cluster -> skin
                # cluster -> bone: the engine reads this via GetFirstConnectedIndex(clusterId, asChild=false)
                # -> it matches the connection whose Properties[2]==clusterId and takes the bone from
                # Properties[1]. So the CLUSTER id must be the PARENT slot (Properties[2]), the BONE the
                # child slot (Properties[1]) -- i.e. `C: "OO", boneId, clusterId` (REVERSED from the usual
                # cluster-child-of-bone convention). Emit it the other way and no subdeformer links, so
                # GetBoneWeights returns null, hasAnim=false, anim=null, and the WHOLE skeleton is dropped
                # (the mesh renders as raw un-skinned verts -- the T-pose bug). (FbxDocument.cs:132.)
                conn_lines.append(f'C: "OO", {bone_id[bname]}, {cl_id}')  # bone(Prop1) -> cluster(Prop2)

    text = _HEADER + "\nObjects: {\n" + _indent("\n".join(obj_lines)) + "\n}\n\n" \
           + "Connections: {\n" + _indent("\n".join(conn_lines)) + "\n}\n"
    # Self-check: parse our own output through a faithful port of the engine's FbxAsciiReader, so a
    # malformed FBX (e.g. a missing node colon) is caught HERE, offline -- never written to disk and
    # never seen as a null model + softlocked field in-game.
    from . import fbx_validate
    fbx_validate.validate(text)
    meta = {"bones": len(bones), "meshes": len(meshes), "materials": len(materials),
            "euler_max_err": euler_max_err}
    return text, meta


def _indent(block, pad="    "):
    return "\n".join(pad + ln if ln else ln for ln in block.split("\n"))


_HEADER = """; FBX 7.4.0 project file
; Exported by ff9mapkit (custom-model pillar) -- skinned FF9 field/character model
; ----------------------------------------------------

FBXHeaderExtension:  {
    FBXHeaderVersion: 1003
    FBXVersion: 7400
    Creator: "ff9mapkit"
}
"""
