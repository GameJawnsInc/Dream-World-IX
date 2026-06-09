"""Fork a REAL FF9 battle background (BBG) out of the user's install -> editable working dir.

Offline, read-only on the install. UnityPy is a LAZY import (extract-only) reused from the field
extractor. Provenance: everything extracted is written to the caller's out_dir (never the package/repo)
and is gitignored. Ports the proven tools/extract_bbg_geometry.py decode — a manual struct-unpack of the
packed Unity-5 m_VertexData/m_IndexBuffer (the path that round-tripped in-game; UnityPy's OBJ export
flips X, so it is NOT used) — plus the Texture2D-by-m_Name PNG dump.
"""
from __future__ import annotations

import struct
from pathlib import Path

from .. import config
from . import fbx as _fbx


def _unitypy():
    from ..extract import _unitypy as _u  # reuse the field extractor's lazy import + error message
    return _u()


def _p0data2(game=None) -> Path:
    return config.find_game_path(game) / "StreamingAssets" / "p0data2.bin"


def _comp_pptr(comp):
    """A GameObject m_Component entry -> its component PPtr (across UnityPy shapes)."""
    return comp.component if hasattr(comp, "component") else comp[1]


def _decode_mesh(mesh_pptr):
    """Decode a Mesh PPtr -> (verts, normals|None, uvs, [per-submesh tris], vertexCount), verbatim."""
    md = mesh_pptr.read()
    vd = md.m_VertexData
    data = bytes(vd.m_DataSize)
    vcount = vd.m_VertexCount
    chans = vd.m_Channels
    stride = 0
    for c in chans:
        if c.dimension:
            stride = max(stride, c.offset + c.dimension * 4)  # format 0 = float32
    if vcount * stride != len(data):
        raise ValueError(f"vertex stride mismatch (v{vcount} * s{stride} != {len(data)})")
    pos_c, nrm_c, uv_c = chans[0], chans[1], chans[3]

    def rd(off, dim, vi):
        return list(struct.unpack_from("<%df" % dim, data, vi * stride + off))

    verts = [rd(pos_c.offset, pos_c.dimension, i) for i in range(vcount)]
    normals = [rd(nrm_c.offset, nrm_c.dimension, i) for i in range(vcount)] if nrm_c.dimension else None
    uvs = ([rd(uv_c.offset, uv_c.dimension, i) for i in range(vcount)]
           if uv_c.dimension else [[0.0, 0.0]] * vcount)

    ib = bytes(md.m_IndexBuffer)
    use32 = getattr(md, "m_IndexFormat", None) == 1 or getattr(md, "m_Use16BitIndices", 1) in (0, False)
    if use32:
        idx = struct.unpack("<%dI" % (len(ib) // 4), ib)
        ent = 4
    else:
        idx = struct.unpack("<%dH" % (len(ib) // 2), ib)
        ent = 2
    submeshes = []
    for s in md.m_SubMeshes:
        first = s.firstByte // ent
        flat = idx[first:first + s.indexCount]
        submeshes.append([[flat[i], flat[i + 1], flat[i + 2]] for i in range(0, len(flat) - 2, 3)])
    return verts, normals, uvs, submeshes, vcount


def _maintex_name(mat_pptr):
    """Material PPtr -> its _MainTex Texture2D m_Name (the on-disc PNG stem), or None."""
    if not getattr(mat_pptr, "path_id", 0):
        return None
    md = mat_pptr.read()
    try:
        for kv in md.m_SavedProperties.m_TexEnvs:
            key, val = kv[0], kv[1]
            if getattr(key, "name", str(key)) == "_MainTex":
                tex = val.m_Texture
                return tex.read().m_Name if getattr(tex, "path_id", 0) else None
    except Exception:
        return None
    return None


def read_bbg(bbg, game=None):
    """Return (groups, env, bbg) for the named battle background, e.g. 'BBG_B013'.

    `groups` is the canonical structure consumed by fbx.emit_fbx. `env` is the loaded bundle (reused to
    save textures without re-reading p0data2.bin).
    """
    UnityPy = _unitypy()
    env = UnityPy.load(str(_p0data2(game)))
    needle = f"battlemap_all/{bbg.lower()}/"
    by_id = {}
    cont = []
    for o in env.objects:
        by_id[o.path_id] = o
        if needle in (getattr(o, "container", None) or "").lower():
            cont.append(o)
    bbg_go = next((o for o in cont if o.type.name == "GameObject" and o.read().m_Name == bbg), None)
    if bbg_go is None:
        raise ValueError(f"battle map {bbg!r} not found (looked for container {needle!r}). "
                         f"Try `ff9mapkit battle-list` for the available names.")
    bd = bbg_go.read()
    tpid = None
    for comp in bd.m_Component:
        pp = _comp_pptr(comp)
        if pp.type.name == "Transform":
            tpid = pp.path_id
            break
    children = []
    for o in env.objects:
        if o.type.name != "Transform":
            continue
        try:
            tt = o.read_typetree()
        except Exception:
            continue
        fa = tt.get("m_Father", {})
        if isinstance(fa, dict) and fa.get("m_PathID") == tpid:
            goid = tt.get("m_GameObject", {}).get("m_PathID")
            if goid in by_id:
                children.append(by_id[goid])

    groups = []
    for go in children:
        d = go.read()
        mesh_pptr, mats = None, []
        for comp in d.m_Component:
            pp = _comp_pptr(comp)
            cd = pp.read()
            tn = pp.type.name
            if tn == "MeshFilter":
                mp = getattr(cd, "m_Mesh", None)
                if mp is not None and getattr(mp, "path_id", 0):
                    mesh_pptr = mp
            elif tn in ("MeshRenderer", "SkinnedMeshRenderer"):
                mats = list(getattr(cd, "m_Materials", []) or [])
        if mesh_pptr is None:
            continue
        verts, normals, uvs, submeshes_idx, _vc = _decode_mesh(mesh_pptr)
        sm = []
        for i, tris in enumerate(submeshes_idx):
            tex = _maintex_name(mats[i]) if i < len(mats) else None
            sm.append({"texture": tex, "tris": tris})
        groups.append({"name": d.m_Name, "attr": _fbx.GROUP_ATTR.get(d.m_Name, "PLUS"),
                       "verts": verts, "normals": normals, "uvs": uvs, "submeshes": sm})
    order = {"Group_0": 0, "Group_2": 1, "Group_4": 2, "Group_8": 3}
    groups.sort(key=lambda g: order.get(g["name"], 99))
    if not groups:
        raise ValueError(f"{bbg}: no group meshes found under {needle!r}")
    return groups, env, bbg


def _save_textures(env, bbg, out_dir, names) -> list[str]:
    needle = f"battlemap_all/{bbg.lower()}/"
    want = set(names)
    saved = []
    for o in env.objects:
        if o.type.name != "Texture2D":
            continue
        if needle not in (getattr(o, "container", None) or "").lower():
            continue
        d = o.read()
        if d.m_Name in want:
            d.image.save(str(Path(out_dir) / f"{d.m_Name}.png"))
            saved.append(d.m_Name)
    return saved


def list_battle_maps(pattern=None, game=None) -> list[str]:
    """List real BBG names available to fork (e.g. BBG_B013)."""
    import re
    UnityPy = _unitypy()
    env = UnityPy.load(str(_p0data2(game)))
    rx = re.compile(r"battlemap_all/(bbg_b\d+)/\1\.", re.I)
    names = set()
    for o in env.objects:
        m = rx.search((getattr(o, "container", None) or "").lower())
        if m:
            names.add(m.group(1).upper())
    rows = sorted(names, key=lambda n: int(n[5:]) if n[5:].isdigit() else 0)
    if pattern:
        rows = [n for n in rows if pattern.lower() in n.lower()]
    return rows


def write_battle_project(bbg, out_dir, *, name=None, scene_id=5000, game=None):
    """Fork `bbg` into `out_dir`: <bbg>.fbx + image#.png + an editable battle.toml. Returns (meta, toml)."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    groups, env, bbg = read_bbg(bbg, game)
    tex = _fbx.textures_used(groups)
    text, ngeo = _fbx.emit_fbx(groups)
    (out / f"{bbg}.fbx").write_text(text, encoding="ascii", newline="\n")
    saved = _save_textures(env, bbg, out, tex)
    name = name or f"{bbg}_FORK"
    toml_path = out / "battle.toml"
    toml_path.write_text(_battle_toml(bbg, name, scene_id, ngeo, len(groups)),
                         encoding="utf-8", newline="\n")
    meta = {"bbg": bbg, "groups": len(groups), "geometries": ngeo, "textures": saved}
    return meta, toml_path


def _battle_toml(bbg, name, scene_id, ngeo, ngroups) -> str:
    return f'''# Battle background forked from {bbg} by `ff9mapkit battle-import`.
# Geometry: {bbg}.fbx ({ngeo} meshes / {ngroups} groups).  Textures: image#.png in this dir.
# Edit {bbg}.fbx in Blender (KEEP the mesh objects named Group_0/2/4/8) and/or repaint the PNGs, then:
#   ff9mapkit battle-build battle.toml --out dist
#   py tools/deploy_battle.py battle.toml      # reversible install into your mod folder

[battlemap]
bbg = "{bbg}"          # the slot this map SHIPS AS. Keep it = the forked slot to OVERRIDE that real
#                        battle map (proven, no relaunch). Rename to a new BBG_* only if you ALSO wire
#                        a scene below.
fbx = "{bbg}.fbx"      # geometry file in this dir (edit in Blender, re-export over it)

# --- scene wiring (optional) -------------------------------------------------------------------------
# With bbg = the forked slot (above), this OVERRIDES the real map for every battle that uses it -- no
# wiring needed. To point a DIFFERENT existing battle at this map instead, uncomment:
# repoint_scene = 67          # an existing battle-scene id; its bg becomes `bbg` (via BattlePatch.txt)
#
# EXPERIMENTAL (tier c) -- mint a brand-new battle scene. A new scene id also needs its own .raw16/.raw17
# scene assets + a camera, which the kit does NOT yet author, so a bare new id will not load. Leave off
# unless you know what you're doing:
# scene_id = {scene_id}
# scene_name = "{name}"
'''
