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
