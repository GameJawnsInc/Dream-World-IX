"""Battle-map geometry model + ASCII-FBX emitter (PURE — no I/O, no UnityPy; offline-testable).

A battle background ("BBG") is a Unity model whose child meshes are named Group_0/2/4/8 and classified
by battlebg.getBbgAttr (battlebg.cs:266): Group_0=PLUS(additive), Group_2=GROUND, Group_4=MINUS
(subtractive), Group_8=SKY. Memoria's ModelImporter/FbxIO loads a loose FBX from the mod folder INSTEAD
of the bundle, so a custom battle map ships as an ASCII FBX (+ image#.png textures).

Recipe verified in-game 2026-06-09 (a synthetic quad AND a faithful BBG_B013 round-trip):
  * one FBX Geometry per submesh, named "Geometry::Group_N" (duplicate names are fine — getBbgAttr
    matches the literal child-name string);
  * verts / uvs / normals VERBATIM (no axis flip, no scale, no UV V-flip);
  * triangles use the FBX polygon-end convention (last index of each face = -i-1); native winding kept;
  * the Model node is typed "Mesh" (NOT LimbNode/Root — else a skeleton NRE in CreateCustomModelFromFbx)
    with identity transform, so GetVertices applies an identity bone matrix;
  * the Material's ShadingModel is set DIRECTLY to the group's PSX shader — imported meshes become
    SkinnedMeshRenderers, which battlebg's MeshRenderer-only shader pass (SetMaterialShader/setBGColor)
    skips, so the in-FBX shader is what sticks (GetShaderPathFromType passes non-Default/Phong verbatim);
  * texture via a Texture node RelativeFilename + an "OP" connection; loaded from disc next to the FBX.

`groups` is the canonical geometry structure (also what battle.extract produces):
    [ { "name": "Group_2",
        "verts":  [[x,y,z], ...],            # per vertex (Unity space, verbatim)
        "normals":[[x,y,z], ...] | None,     # per vertex
        "uvs":    [[u,v], ...],              # per vertex
        "submeshes": [ {"texture": "image6", "tris": [[a,b,c], ...]} ] },  # tris index into verts
      ... ]
"""
from __future__ import annotations

# Group child-name -> PSX shader (battlebg.SetDefaultShader, battlebg.cs:52-75) and attribute name.
GROUP_SHADER = {
    "Group_0": "PSX/BattleMap_Plus",
    "Group_2": "PSX/BattleMap_Ground",
    "Group_4": "PSX/BattleMap_Minus",
    "Group_8": "PSX/BattleMap_Sky",
}
GROUP_ATTR = {"Group_0": "PLUS", "Group_2": "GROUND", "Group_4": "MINUS", "Group_8": "SKY"}


def validate_groups(groups) -> list[str]:
    """Return human-readable problems with a `groups` structure (empty => OK)."""
    problems: list[str] = []
    if not groups:
        problems.append("no geometry groups")
    for g in groups:
        name = g.get("name")
        if name not in GROUP_SHADER:
            problems.append(f"group {name!r} is not one of Group_0/2/4/8 "
                            f"(getBbgAttr would default it to PLUS)")
        vc = len(g.get("verts", []))
        if vc == 0:
            problems.append(f"group {name!r} has no vertices")
        if g.get("normals") is not None and len(g["normals"]) != vc:
            problems.append(f"group {name!r}: normals count ({len(g['normals'])}) != verts count ({vc})")
        if len(g.get("uvs", [])) != vc:
            problems.append(f"group {name!r}: uvs count ({len(g.get('uvs', []))}) != verts count ({vc})")
        for sm in g.get("submeshes", []):
            if not sm.get("texture"):
                problems.append(f"group {name!r}: a submesh has no texture")
            for tri in sm.get("tris", []):
                if any(i < 0 or i >= vc for i in tri):
                    problems.append(f"group {name!r}: triangle index out of range (verts={vc})")
                    break
    return problems


def textures_used(groups) -> list[str]:
    """Sorted unique texture stems referenced by the geometry (the image#.png siblings to ship)."""
    return sorted({sm["texture"] for g in groups for sm in g.get("submeshes", []) if sm.get("texture")})


def emit_fbx(groups) -> tuple[str, int]:
    """Render `groups` to ASCII FBX text. Returns (fbx_text, geometry_count).

    One Geometry/Model/Material/Texture per submesh. The Model is typed "Mesh" with no transform, so
    Memoria reads vertices verbatim; the Material's ShadingModel is the group's PSX shader.
    """
    objs: list[str] = []
    conns: list[str] = []
    nid = 1000
    ngeo = 0
    for g in groups:
        name = g["name"]
        shader = GROUP_SHADER.get(name, "PSX/BattleMap_Plus")
        verts = g["verts"]
        norms = g.get("normals")
        uvs = g["uvs"]
        vc = len(verts)
        has_n = norms is not None and len(norms) == vc
        vflat = ",".join(f"{c:g}" for v in verts for c in v)
        nflat = ",".join(f"{c:g}" for n in norms for c in n) if has_n else ""
        uflat = ",".join(f"{c:g}" for uv in uvs for c in uv)
        for sm in g["submeshes"]:
            gid, mid, matid, texid = nid, nid + 1, nid + 2, nid + 3
            nid += 10
            ngeo += 1
            pvi: list[int] = []
            for (a, b, c) in sm["tris"]:
                pvi += [a, b, -c - 1]   # FBX polygon-end convention
            pviflat = ",".join(str(i) for i in pvi)
            tex = sm["texture"]
            geo = [f'\tGeometry: {gid}, "Geometry::{name}", "Mesh" {{']
            geo.append(f'\t\tVertices: *{vc * 3} {{\n\t\t\ta: {vflat}\n\t\t}}')
            geo.append(f'\t\tPolygonVertexIndex: *{len(pvi)} {{\n\t\t\ta: {pviflat}\n\t\t}}')
            if has_n:
                geo.append(f'\t\tLayerElementNormal: 0 {{\n\t\t\tMappingInformationType: "ByVertex"\n'
                           f'\t\t\tReferenceInformationType: "Direct"\n'
                           f'\t\t\tNormals: *{vc * 3} {{\n\t\t\t\ta: {nflat}\n\t\t\t}}\n\t\t}}')
            geo.append(f'\t\tLayerElementUV: 0 {{\n\t\t\tMappingInformationType: "ByVertex"\n'
                       f'\t\t\tReferenceInformationType: "Direct"\n'
                       f'\t\t\tUV: *{vc * 2} {{\n\t\t\t\ta: {uflat}\n\t\t\t}}\n\t\t}}')
            geo.append('\t}')
            objs.append("\n".join(geo))
            objs.append(f'\tModel: {mid}, "Model::{name}", "Mesh" {{\n\t}}')
            objs.append(f'\tMaterial: {matid}, "Material::{name}_{texid}", "" {{\n'
                        f'\t\tShadingModel: "{shader}"\n\t}}')
            objs.append(f'\tTexture: {texid}, "Texture::{tex}", "" {{\n'
                        f'\t\tRelativeFilename: "{tex}.png"\n\t}}')
            conns.append(f'\tC: "OO", {gid}, {mid}')        # geometry -> model
            conns.append(f'\tC: "OO", {matid}, {mid}')      # material -> model
            conns.append(f'\tC: "OP", {texid}, {matid}, "DiffuseColor"')  # texture -> material
    return (
        "; FBX 7.4.0 project file\n\nFBXHeaderExtension:  {\n\tFBXVersion: 7400\n}\n"
        "Objects:  {\n" + "\n".join(objs) + "\n}\n"
        "Connections:  {\n" + "\n".join(conns) + "\n}\n"
    ), ngeo


# --------------------------------------------------------------------- parse (inverse of emit_fbx)
import re as _re

_NODE_RE = _re.compile(r'(Geometry|Model|Material|Texture):\s*(\d+),\s*"([^"]*)",\s*"[^"]*"\s*\{')
_CONN_RE = _re.compile(r'C:\s*"(OO|OP)",\s*(\d+),\s*(\d+)')


def _block(text, start):
    """The text of the brace-balanced block beginning at the '{' at/after `start`. Tolerant of the
    nested `{ }` of LayerElement*/array sub-blocks our emitter produces."""
    depth = 0
    i = text.index("{", start)
    j = i
    while j < len(text):
        ch = text[j]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[i + 1:j]
        j += 1
    return text[i + 1:]


def _floats(s):
    return [float(x) for x in s.replace("\n", " ").split(",") if x.strip()]


def _ints(s):
    return [int(float(x)) for x in s.replace("\n", " ").split(",") if x.strip()]


def parse_fbx(text):
    """Inverse of :func:`emit_fbx`: parse an FBX WE emitted back to the canonical `groups` structure.

    NOT a general FBX reader -- it understands exactly our emitter's layout (one Geometry/Model/Material/
    Texture per submesh, the Connections tying texture->material->model<-geometry). Geometries that share a
    child-name (Group_N) are merged into one group with one submesh each, so
    ``emit_fbx(parse_fbx(emit_fbx(g))) == emit_fbx(g)`` (round-trip; tested). Lets the Blender add-on load a
    kit-built/forked BBG_B###.fbx for reshaping, then re-export it through the same emitter.
    """
    # 1) index every Objects node by id, capturing its inner block text
    nodes = {}                                            # id -> (kind, child_name, block_text)
    for m in _NODE_RE.finditer(text):
        kind, nid, label = m.group(1), int(m.group(2)), m.group(3)
        child = label.split("::", 1)[1] if "::" in label else label
        nodes[nid] = (kind, child, _block(text, m.end() - 1))
    # 2) connections: geo->model (OO), material->model (OO), texture->material (OP)
    model_of_geo, mat_of_model, tex_of_mat = {}, {}, {}
    for ck, src, dst in _CONN_RE.findall(text):
        src, dst = int(src), int(dst)
        sk = nodes.get(src, (None,))[0]
        if ck == "OO" and sk == "Geometry":
            model_of_geo[src] = dst
        elif ck == "OO" and sk == "Material":
            mat_of_model[dst] = src                       # model <- material
        elif ck == "OP" and sk == "Texture":
            tex_of_mat[dst] = src                         # material <- texture
    # 3) per geometry -> its texture stem, via model<-material<-texture
    groups, by_name = [], {}
    for gid, (kind, name, body) in nodes.items():
        if kind != "Geometry":
            continue
        verts = [list(v) for v in _chunk(_floats(_named_array(body, "Vertices")), 3)]
        pvi = _ints(_named_array(body, "PolygonVertexIndex"))
        tris = [[pvi[i], pvi[i + 1], -pvi[i + 2] - 1] for i in range(0, len(pvi) - 2, 3)]
        nrm_raw = _named_array(body, "Normals")
        normals = [list(v) for v in _chunk(_floats(nrm_raw), 3)] if nrm_raw is not None else None
        uvs = [list(v) for v in _chunk(_floats(_named_array(body, "UV") or ""), 2)]
        tex = None
        mid = model_of_geo.get(gid)
        if mid is not None:
            matid = mat_of_model.get(mid)
            if matid is not None:
                texid = tex_of_mat.get(matid)
                if texid is not None:
                    tex = nodes[texid][1]                 # Texture child-name == the stem
        g = by_name.get(name)
        if g is None:
            g = {"name": name, "verts": verts, "normals": normals, "uvs": uvs, "submeshes": []}
            by_name[name] = g
            groups.append(g)
        g["submeshes"].append({"texture": tex, "tris": tris})
    return groups


def _named_array(body, key):
    """The flat ``a: ...`` payload string of the first ``<key>: *N { a: ... }`` in `body`, or None."""
    m = _re.search(rf'{key}:\s*\*\d+\s*\{{\s*a:\s*([^}}]*)\}}', body, _re.S)
    return m.group(1) if m else None


def _chunk(flat, n):
    return [flat[i:i + n] for i in range(0, len(flat) - n + 1, n)]
