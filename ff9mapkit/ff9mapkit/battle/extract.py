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


def _p0data7(game=None) -> Path:
    return config.find_game_path(game) / "StreamingAssets" / "p0data7.bin"


def _grab(env, suffixes: dict) -> dict:
    """{key: bytes} for the TextAsset whose container ENDS WITH suffixes[key] (case-insensitive)."""
    want = {k: v.lower() for k, v in suffixes.items()}
    out: dict = {}
    for o in env.objects:
        if o.type.name != "TextAsset":
            continue
        c = (getattr(o, "container", None) or "").lower()
        for k, suf in want.items():
            if k not in out and c.endswith(suf):
                from ..extract import _raw_bytes
                out[k] = _raw_bytes(o.read())
    return out


def _lang_of(text: str):
    """Classify a battle-text variant by language signature. All langs share entry COUNT/order (indices
    are language-independent), so this only picks WHICH localized strings to ship per language."""
    if any("぀" <= c <= "ヿ" or "一" <= c <= "鿿" for c in text):
        return "jp"
    if "Coltellata" in text or "Niente" in text:
        return "it"
    if "Gobelin" in text or "Gobelipunch" in text:
        return "fr"
    if "Duende" in text:
        return "es"
    if "Isegrim" in text or "Nichts" in text:
        return "gr"
    if "Goblin" in text and "Fang" in text:
        return "en"
    return None


def read_scene_assets(donor, game=None) -> dict:
    """Fork a real battle SCENE's gameplay+sequence+text out of the install (for a tier-c mint).

    `donor` is a battle-scene NAME (e.g. 'EF_R007', the part after 'EVT_BATTLE_'). Returns
    ``{raw16, raw17, donor_id, eb:{lang:bytes}, mes:{lang:bytes}}`` -- everything a minted scene needs
    EXCEPT the map (geometry) and the INB (authored at build time). The raw17/eb/mes carry the donor's
    working camera + AI + text verbatim, so the minted clone is internally consistent. Provenance: these
    are SE-derived; the caller writes them to a gitignored project dir, never the repo.
    """
    UnityPy = _unitypy()
    donor = donor.upper()
    needle = f"battlescene/evt_battle_{donor.lower()}/"
    env2 = UnityPy.load(str(_p0data2(game)))
    raw16 = raw17 = None
    donor_id = None
    for o in env2.objects:
        if o.type.name != "TextAsset":
            continue
        c = (getattr(o, "container", None) or "").lower()
        if needle not in c:
            continue
        from ..extract import _raw_bytes
        if c.endswith("dbfile0000.raw16.bytes"):
            raw16 = _raw_bytes(o.read())
        elif c.endswith(".raw17.bytes"):
            raw17 = _raw_bytes(o.read())
            donor_id = int(c.rsplit("/", 1)[-1].split(".", 1)[0])    # '<id>.raw17.bytes' -> id
    if raw16 is None or raw17 is None or donor_id is None:
        raise ValueError(f"battle scene {donor!r} not found (looked for {needle!r}). "
                         f"Try a name from `ff9mapkit battle-list --scenes`.")

    env7 = UnityPy.load(str(_p0data7(game)))
    eb = _grab(env7, {l: f"eventbinary/battle/{l}/evt_battle_{donor.lower()}.eb.bytes"
                      for l in config.LANGS})
    missing = [l for l in config.LANGS if l not in eb]
    if missing:
        raise ValueError(f"battle eb for {donor!r} missing langs: {missing}")

    # battle text: <donor_id>.mes lives in resources.assets, one per language
    ra = config.find_game_path(game) / "x64" / "FF9_Data" / "resources.assets"
    if not ra.exists():
        ra = config.find_game_path(game) / "FF9_Data" / "resources.assets"
    env_ra = UnityPy.load(str(ra))
    by, eng = {}, None
    from ..extract import _raw_bytes
    for o in env_ra.objects:
        if o.type.name != "TextAsset":
            continue
        d = o.read()
        if d.m_Name != f"{donor_id}.mes":
            continue
        raw = _raw_bytes(d)
        lang = _lang_of(raw.decode("utf-8", "replace"))
        if lang == "en":
            eng = raw
        elif lang:
            by[lang] = raw
    if eng is None and not by:
        raise ValueError(f"battle text {donor_id}.mes not found in resources.assets")
    pick = {"us": eng, "uk": eng, "fr": by.get("fr"), "gr": by.get("gr"),
            "it": by.get("it"), "es": by.get("es"), "jp": by.get("jp")}
    mes = {l: (pick.get(l) or eng or next(iter(by.values()))) for l in config.LANGS}
    return {"raw16": raw16, "raw17": raw17, "donor_id": donor_id, "eb": eb, "mes": mes}


def write_scene_assets(out_dir, donor, game=None) -> dict:
    """Fork `donor` scene assets into ``<out_dir>/scene/`` (gitignored). Layout consumed by build.py:
    ``scene/dbfile0000.raw16.bytes``, ``scene/btlseq.raw17.bytes``, ``scene/eb/<lang>.eb.bytes``,
    ``scene/mes/<lang>.mes``. Returns a small manifest (donor, donor_id, byte sizes)."""
    a = read_scene_assets(donor, game)
    sdir = Path(out_dir) / "scene"
    (sdir / "eb").mkdir(parents=True, exist_ok=True)
    (sdir / "mes").mkdir(parents=True, exist_ok=True)
    (sdir / "dbfile0000.raw16.bytes").write_bytes(a["raw16"])
    (sdir / "btlseq.raw17.bytes").write_bytes(a["raw17"])
    for lang in config.LANGS:
        (sdir / "eb" / f"{lang}.eb.bytes").write_bytes(a["eb"][lang])
        (sdir / "mes" / f"{lang}.mes").write_bytes(a["mes"][lang])
    return {"donor": donor.upper(), "donor_id": a["donor_id"],
            "raw16": len(a["raw16"]), "raw17": len(a["raw17"]), "langs": len(config.LANGS)}


def list_battle_scenes(pattern=None, game=None) -> list[str]:
    """List real battle-scene NAMES available to fork as a mint donor (e.g. EF_R007 = Evil Forest)."""
    import re
    UnityPy = _unitypy()
    env = UnityPy.load(str(_p0data2(game)))
    rx = re.compile(r"battlescene/evt_battle_([^/]+)/dbfile0000\.raw16", re.I)
    names = set()
    for o in env.objects:
        m = rx.search((getattr(o, "container", None) or "").lower())
        if m:
            names.add(m.group(1).upper())
    rows = sorted(names)
    if pattern:
        rows = [n for n in rows if pattern.lower() in n.lower()]
    return rows


def write_battle_project(bbg, out_dir, *, name=None, scene_id=5000, game=None,
                         fork_scene=None, ship_as=None):
    """Fork `bbg` into `out_dir`: <bbg>.fbx + image#.png + an editable battle.toml. Returns (meta, toml).

    ``fork_scene`` (a donor battle-scene NAME, e.g. 'EF_R007') ALSO forks that scene's gameplay/sequence/
    text into ``scene/`` and writes a tier-c MINT battle.toml -- a brand-new, independently-triggerable
    battle. ``ship_as`` (e.g. 'BBG_B200') ships the geometry under a NEW bbg number instead of overriding
    the forked slot (the kit authors a static INB for it at build time).
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    groups, env, bbg = read_bbg(bbg, game)
    tex = _fbx.textures_used(groups)
    text, ngeo = _fbx.emit_fbx(groups)
    ship_bbg = ship_as or bbg
    (out / f"{ship_bbg}.fbx").write_text(text, encoding="ascii", newline="\n")
    saved = _save_textures(env, bbg, out, tex)
    name = name or f"{bbg}_FORK"
    meta = {"bbg": ship_bbg, "src_bbg": bbg, "groups": len(groups), "geometries": ngeo, "textures": saved}
    toml_path = out / "battle.toml"
    if fork_scene:
        scene_meta = write_scene_assets(out, fork_scene, game)
        meta["scene"] = scene_meta
        toml_path.write_text(_mint_toml(ship_bbg, name, scene_id, ngeo, len(groups), scene_meta,
                                        new_bbg=bool(ship_as)),
                             encoding="utf-8", newline="\n")
    else:
        toml_path.write_text(_battle_toml(ship_bbg, name, scene_id, ngeo, len(groups)),
                             encoding="utf-8", newline="\n")
    return meta, toml_path


def _mint_toml(bbg, name, scene_id, ngeo, ngroups, scene_meta, *, new_bbg) -> str:
    tint = "" if not new_bbg else (
        '\n# char_tint = [128, 128, 128]   # optional RGB tint the engine lights party/enemies with on this'
        '\n#                                # map (0-255); default neutral. shadow = 32 by default.')
    return f'''# Tier-c MINT: a brand-new battle SCENE forked by `ff9mapkit battle-import --fork-scene`.
# Geometry: {bbg}.fbx ({ngeo} meshes / {ngroups} groups) + image#.png.  Gameplay/camera/text forked from
# donor scene {scene_meta["donor"]} (id {scene_meta["donor_id"]}) into scene/ (raw16 + raw17 + eb + mes).
# Edit {bbg}.fbx in Blender / repaint the PNGs to make the map your own, then:
#   ff9mapkit battle-build battle.toml --out dist
#   py tools/deploy_battle.py battle.toml --trigger-field 5000   # reversible; repoints a field's encounter
# Then RELAUNCH FF9 (a new BattleScene id loads at launch) and trigger the battle on the trigger field.

[battlemap]
bbg = "{bbg}"          # ships AS this slot. A NEW number (BBG_B178+) = a wholly original map (the kit
#                        authors a static INB for it). An existing number would OVERRIDE that real map.
fbx = "{bbg}.fbx"
scene_id = {scene_id}        # the net-new battle id this mint registers (must not collide with any field/scene id)
scene_name = "{name}"     # -> EVT_BATTLE_{name} + BSC_{name}{tint}

# --- tune the fight (optional) -----------------------------------------------------------------------
# The donor's enemies/camera are forked verbatim; uncomment to OVERRIDE. Enemy TYPES are kept (so the
# forked attack sequences stay valid) -- you reposition / restat / re-reward them and pick the camera.
# [scene]
# camera = 0                 # pattern camera: 0/1/2 = a fixed PSX pose, >=3 = random (default = donor's).
# #                            Pin it 0-2 to make the OPENING-camera tweaks below deterministic.
# camera_yaw = 0             # rotate the opening sweep N degrees around the battle (in place, no repack)
# camera_pitch = 0           # tilt N degrees -- FINICKY: an offset onto the donor's base pitch, so a large
# #                            value can dip the camera below the floor (the ground mesh is see-through from
# #                            under). Use small steps + test; yaw + zoom are the predictable knobs.
# camera_zoom = 1.0          # opening-camera distance multiplier (1.5 = farther out, 0.7 = closer in)
#
# --- author the opening camera SWEEP from keyframes (optional, advanced) ------------------------------
# Replaces the opening swoop with your own, in the SAME grammar the base game uses. Keyframes ADJUST the
# battle's PROVEN framing (the shot it normally settles into): yaw/pitch/roll are degree OFFSETS and `zoom`
# is a distance multiplier, so {} = the normal framing. Keyframe 0 is the instant START pose; each later
# one MOVES the camera there over `move` frames. End on {} (or small offsets) so the fight stays framed --
# the camera's origin is the battle centre, and distance is measured from it, so anchoring on the proven
# pose is what stops a sweep from mis-framing. The donor's on-fight look-at + the intro->battle handoff are
# kept. Pin `camera = 0` above. Needs >= 2 keyframes (a start + a move).
# [[scene.camera_keyframes]]    # START: swing 76deg to one side, 2.5x farther out, slightly higher
# yaw = -76                     # degrees to orbit from the normal shot (+/-)
# pitch = 5                     # degrees to tilt (small; +tips the camera down toward the floor)
# zoom = 2.5                    # distance x2.5 (start wide); 1.0 = the normal framing, <1 = closer
# [[scene.camera_keyframes]]    # swoop IN and around
# yaw = -20
# zoom = 1.6
# move = 45                     # frames to reach this pose
# ease = "in"                   # in (start slow) | out (end slow) | linear
# [[scene.camera_keyframes]]    # settle EXACTLY on the battle's normal framing
# move = 30
# ease = "out"
#
# monster_count = 4          # how many of the 4 slots SPAWN (1-4). The kit re-authors the eb's enemy-AI
# #                            binding to match, so you CAN exceed the donor's natural count. Give each
# #                            active slot a 'type' (an existing scene type).
# [[scene.enemy]]
# slot = 0                   # which placed enemy (0-3) in the pattern
# type = 0                   # which enemy TYPE fills this slot (0..N-1; must be a type ALREADY in this
# #                            scene so the forked attack sequences/models cover it). Makes it targetable.
# pos = [300, -400]          # [x, z] on the battle ground (or [x, y, z] to set height); rot = 0..4095
# hp = 1500                  # this enemy TYPE's stats (hp/mp/gil/exp/level/speed/strength/magic/spirit)
# gil = 999
# drop  = ["Hi-Potion", "Ether", "none", "none"]   # WinItems[4] by name/id ("none" = empty)
# steal = ["Phoenix Down", "none", "none", "none"] # StealItems[4]
'''


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
