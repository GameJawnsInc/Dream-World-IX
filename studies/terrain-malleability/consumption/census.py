"""THE CONSUMPTION CENSUS -- what overworld mesh data EXISTS, per part type, per attribute, both discs.

Reads the user's own install (UnityPy, read-only) and writes ONE derived-statistics cache:
  out/consumption_census.json   (counts / ranges / names only -- no mesh bytes, provenance-clean)
Shader source text needed to read the Bind lists is written to a TEMP dir OUTSIDE the repo
(%TEMP%/ff9-consumption-shaders/), never into the repo.

Sections:
  meshes    -- every worldmap/disc{1,4}/{0_1,0_2}/r*/block[x][y] <part> mesh: vertex/index counts,
               channel set (m_CurrentChannels bitmask + per-channel format/dim), submesh count, index
               format, IDENTITY-index test (index[i]==i), tangent .x/.y/.z/.w distinct-value stats,
               normal distinct count, uv range, stored AABB vs recomputed AABB.
  prefabs   -- every WorldMap/Prefabs/WorldDisc{d}/r*/Block[x][y](f) prefab: WMBlockPrefab slot -> child
               GameObject name, flags (IsSea/IsSwitchable/...), per child mesh name + material names.
  worlddisc -- the 480 WMBlock components of the bundled WorldDisc-InCaseThatItNeedsToCreateAgain
               prefab (IsSea etc.) -- a PROXY for the live baked WorldDisc (assumption, see NOTES).
  materials -- every WorldMap/Materials/*.mat: shader name, tex envs (+ST), floats.
  shaders   -- every shader those materials use: Bind list per SubProgram + lighting uniforms read.

CALIBRATION baked in (asserted, exits non-zero on failure):
  * block (8,17) terrain decodes 339 verts with channels {0,1,3,7} (known from the kit's own read).
  * the bundle's WorldMap/Terrain shader Bind list == the install's StreamingAssets/Shaders/WorldMap/Terrain.txt
    Bind list (two independent copies of the same program must agree).

Rerun:  py studies/terrain-malleability/consumption/census.py      (~2-4 min, both discs)
"""
import json
import os
import re
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
import numpy as np                                   # noqa: E402
from ff9mapkit.world import extract as X             # noqa: E402

OUT = Path(__file__).resolve().parent / "out"
SHADER_TMP = Path(tempfile.gettempdir()) / "ff9-consumption-shaders"
GAME_SHADERS = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\StreamingAssets\Shaders")

CH_NAMES = {0: "position", 1: "normal", 2: "color", 3: "uv0", 4: "uv1", 5: "uv2", 6: "uv3", 7: "tangent"}
FMT_SIZE = {0: 4, 1: 2, 2: 1, 3: 1}                  # Unity 5.x: float32, float16, color(unorm8), byte

MESH_RE = re.compile(r"worldmap/disc(\d)/(0_[12])/r(\d+)/block\[(\d+)\]\[(\d+)\] ([a-z0-9_]+)(?:\.asset)?$")
PREFAB_RE = re.compile(r"worldmap/prefabs/worlddisc(\d)/r(\d+)/block\[(\d+)\]\[(\d+)\](f?)\.prefab$")

SLOTS = ["TerrainForm1", "ObjectForm1", "TerrainForm2", "ObjectForm2", "Beach1", "Beach2", "Stream", "River",
         "RiverJoint", "Falls", "Sea1", "Sea2", "Sea3", "Sea4", "Sea5", "Sea6", "VolcanoCrater1", "VolcanoLava1",
         "VolcanoCrater2", "VolcanoLava2", "Sea3_2", "Sea4_2", "Sea5_2"]
FLAGS = ["Is3_9", "IsSea", "HasSpecialObject", "IsSwitchable", "HasRiver", "HasRiverJoint", "HasStream", "HasFalls",
         "HasBeach1", "HasBeach2", "HasSea", "HasVolcanoCrater", "HasVolcanoLava", "Number", "Form", "IsReady"]


def decode_vertices(md):
    """{channel_index: ndarray(vcount, dim)} for every present float channel, via the real stride."""
    vd = md.m_VertexData
    raw = bytes(vd.m_DataSize)
    vcount = int(vd.m_VertexCount)
    chans = {}
    stride = 0
    for ci, c in enumerate(vd.m_Channels):
        if c.dimension:
            chans[ci] = (int(c.stream), int(c.offset), int(c.format), int(c.dimension))
            stride = max(stride, int(c.offset) + int(c.dimension) * FMT_SIZE[int(c.format)])
    if not raw or vcount == 0:
        return {}, chans, vcount, stride
    assert all(s == 0 for s, *_ in chans.values()), "multi-stream vertex data not handled"
    assert vcount * stride == len(raw), f"stride mismatch {vcount}*{stride}!={len(raw)}"
    buf = np.frombuffer(raw, dtype=np.uint8).reshape(vcount, stride)
    arrs = {}
    for ci, (_s, off, fmt, dim) in chans.items():
        if fmt == 0:
            arrs[ci] = buf[:, off:off + 4 * dim].copy().view("<f4").reshape(vcount, dim)
        elif fmt == 2:
            arrs[ci] = buf[:, off:off + dim].astype(np.float32) / 255.0
        else:
            arrs[ci] = None
    return arrs, chans, vcount, stride


def distinct_stats(col):
    u = np.unique(np.round(col.astype(np.float64), 6))
    return {"n_distinct": int(u.size), "min": float(u.min()), "max": float(u.max()),
            "sample": [float(x) for x in u[:8]]}


def mesh_record(md):
    arrs, chans, vcount, stride = decode_vertices(md)
    ib = bytes(md.m_IndexBuffer)
    use16 = getattr(md, "m_Use16BitIndices", 1) not in (0, False) and getattr(md, "m_IndexFormat", 0) != 1
    idx = np.frombuffer(ib, dtype="<u2" if use16 else "<u4").astype(np.int64)
    rec = {
        "name": md.m_Name, "vcount": vcount, "icount": int(idx.size),
        "channels": {CH_NAMES[ci]: {"fmt": f, "dim": d} for ci, (_s, _o, f, d) in chans.items()},
        "current_channels_mask": int(md.m_VertexData.m_CurrentChannels),
        "submeshes": len(md.m_SubMeshes),
        "submesh_topology": sorted({int(getattr(s, "topology", 0) or 0) for s in md.m_SubMeshes}),
        "index16": bool(use16),
        "identity_index": bool(idx.size == vcount and np.array_equal(idx, np.arange(vcount))),
        "index_is_permutation": bool(idx.size == vcount and np.array_equal(np.sort(idx), np.arange(vcount))),
        "readable": int(getattr(md, "m_IsReadable", -1)),
        "stride": stride,
    }
    aabb = md.m_LocalAABB
    rec["aabb_stored"] = [aabb.m_Center.x, aabb.m_Center.y, aabb.m_Center.z, aabb.m_Extent.x, aabb.m_Extent.y, aabb.m_Extent.z]
    if 0 in arrs and arrs[0] is not None and vcount:
        P = arrs[0]
        lo, hi = P.min(0), P.max(0)
        rec["aabb_computed"] = [float(x) for x in ((lo + hi) / 2).tolist() + ((hi - lo) / 2).tolist()]
    if 7 in arrs and arrs[7] is not None and vcount:
        T = arrs[7]
        rec["tangent"] = {c: distinct_stats(T[:, i]) for i, c in enumerate("xyzw")}
        # per-TRIANGLE tangent.x uniformity: does every corner of a tri carry the same id?
        if idx.size % 3 == 0 and idx.size:
            tx = T[:, 0][idx].reshape(-1, 3)
            rec["tangent_x_tri_uniform"] = float(np.mean((tx[:, 0] == tx[:, 1]) & (tx[:, 1] == tx[:, 2])))
            rec["tangent_x_integral"] = bool(np.all(np.mod(T[:, 0], 1.0) == 0))
    if 1 in arrs and arrs[1] is not None and vcount:
        N = np.round(arrs[1].astype(np.float64), 4)
        rec["normal_distinct"] = int(np.unique(N, axis=0).shape[0])
        rec["normal_mean"] = [float(x) for x in arrs[1].mean(0)]
    if 3 in arrs and arrs[3] is not None and vcount:
        U = arrs[3]
        rec["uv0_range"] = [float(U[:, 0].min()), float(U[:, 0].max()), float(U[:, 1].min()), float(U[:, 1].max())]
    for ci in (2, 4, 5, 6):
        if ci in arrs:
            rec[f"has_{CH_NAMES[ci]}"] = True
    # geometric up-facing census exactly as WMBlock.AddWalkMesh/WMPhysics compute it (index-order corners)
    if 0 in arrs and idx.size % 3 == 0 and idx.size:
        P = arrs[0].astype(np.float64)
        t = idx.reshape(-1, 3)
        n = np.cross(P[t[:, 1]] - P[t[:, 0]], P[t[:, 2]] - P[t[:, 0]])
        ln = np.linalg.norm(n, axis=1)
        ny = np.where(ln > 0, n[:, 1] / np.where(ln > 0, ln, 1), 0.0)
        rec["tris"] = int(t.shape[0])
        rec["tris_upfacing_gt_0.1"] = int(np.sum(ny > 0.1))
        rec["tris_degenerate"] = int(np.sum(ln == 0))
        if 7 in arrs and arrs[7] is not None:
            tx0 = arrs[7][:, 0][t[:, 0]].astype(np.int64)
            rec["idall_hist_top"] = Counter(tx0.tolist()).most_common(6)
            rec["area_hist"] = {int(k): int(v) for k, v in Counter(((tx0 & 0x3F00) >> 8).tolist()).items()}
            rec["topo_hist"] = {int(k): int(v) for k, v in Counter(((tx0 & 0xFC) >> 2).tolist()).items()}
            rec["event_hist"] = {int(k): int(v) for k, v in Counter(((tx0 & 0xC000) >> 14).tolist()).items()}
            rec["flags_hist"] = {int(k): int(v) for k, v in Counter((tx0 & 3).tolist()).items()}
            rec["idall_hist"] = {int(k): int(v) for k, v in Counter(tx0.tolist()).items()}
            rec["idall_gt_16bit"] = int((tx0 > 0xFFFF).sum() + (tx0 < 0).sum())
            rec["skip_class_tris"] = int(np.isin(tx0, [4078, 4088, 2040]).sum())
            rec["flight_veto_tris"] = int((tx0 == 0x31EE).sum())
    return rec


def pptr_obj(pp):
    try:
        return pp.deref() if hasattr(pp, "deref") else pp.get_obj()
    except Exception:
        return None


def go_children(tr):
    out = []
    for ch in tr.m_Children:
        o = pptr_obj(ch)
        if o is None:
            continue
        t = o.read()
        g = pptr_obj(t.m_GameObject).read()
        out.append((o.path_id, g, t))
    return out


MESH_KEY_BY_PID = {}                                 # (assets file, path id) -> census mesh key


def prefab_record(go, mat_names):
    comps = {cid: pptr_obj(pp) for cid, pp in go.m_Component}
    rec = {"name": go.m_Name}
    tr = comps[4].read()
    kids = go_children(tr)
    by_tr = {}
    rec["children"] = []
    for tid, g, _t in kids:
        crec = {"go": g.m_Name}
        for cid, pp in g.m_Component:
            o = pptr_obj(pp)
            if o is None:
                continue
            tn = o.type.name
            if tn == "MeshFilter":
                m = pptr_obj(o.read().m_Mesh)
                crec["mesh"] = m.read().m_Name if m is not None else None
                if m is not None:
                    crec["mesh_key"] = MESH_KEY_BY_PID.get(m.path_id)
            elif tn in ("MeshRenderer", "Renderer"):
                mats = []
                for mp in o.read().m_Materials:
                    mo = pptr_obj(mp)
                    if mo is not None:
                        nm = mo.read().m_Name
                        mats.append(nm)
                        mat_names[nm] = mo
                crec["materials"] = mats
            elif tn == "MonoBehaviour":
                crec.setdefault("monobehaviours", []).append(tn)
        rec["children"].append(crec)
        by_tr[tid] = g.m_Name
    mb = comps.get(114)
    if mb is not None:
        tt = mb.read_typetree()
        rec["slots"] = {s: by_tr.get(tt[s]["m_PathID"], ("<foreign>" if tt[s]["m_PathID"] else None))
                        for s in SLOTS if s in tt}
        rec["slots"] = {k: v for k, v in rec["slots"].items() if v}
        rec["flags"] = {f: tt[f] for f in FLAGS if f in tt}
    return rec


def shader_binds(text):
    """[(subprogram-kind, api, [bind channels], [lighting uniforms])] parsed from compiled ShaderLab text."""
    out = []
    for m in re.finditer(r'Program "(vp|fp)" \{(.*?)\n\t*\}\n', text, re.S):
        kind = m.group(1)
        for sp in re.finditer(r'SubProgram "([^"]+)"\s*\{(.*?)"(?:vs|ps)_', m.group(2), re.S):
            body = sp.group(2)
            binds = re.findall(r'Bind "([a-z0-9_]+)"', body)
            light = sorted(set(re.findall(r"\[(unity_Light\w+|glstate_lightmodel_ambient|_WorldSpaceLightPos0|unity_4Light\w+)\]", body)))
            out.append({"kind": kind, "api": sp.group(1).strip(), "binds": binds, "lighting": light})
    if not out:                                       # fall back: whole-text Bind scan
        out.append({"kind": "?", "api": "?", "binds": re.findall(r'Bind "([a-z0-9_]+)"', text), "lighting": []})
    return out


def main():
    OUT.mkdir(exist_ok=True)
    SHADER_TMP.mkdir(exist_ok=True)
    result = {"meshes": {}, "prefabs": {}, "worlddisc": {}, "materials": {}, "shaders": {}}
    mat_seen = {}
    for disc in (1, 4):
        env = X._worldmap_env(disc)
        C = {k.lower(): v for k, v in env.container.items()}
        items = sorted(C.items(), key=lambda kv: (0 if MESH_RE.search(kv[0]) else 1, kv[0]))
        for key, o in items:
            m = MESH_RE.search(key)
            if m and int(m.group(1)) == disc and o.type.name == "Mesh":
                _d, lod, _r, x, y, part = m.groups()
                result["meshes"][f"d{disc}/{lod}/{x},{y}/{part}"] = mesh_record(o.read())
                MESH_KEY_BY_PID[getattr(o, "m_PathID", getattr(o, "path_id", None))] = f"d{disc}/{lod}/{x},{y}/{part}"
                continue
            m = PREFAB_RE.search(key)
            if m and int(m.group(1)) == disc:
                _d, _r, x, y, f = m.groups()
                result["prefabs"][f"d{disc}/{x},{y}{f}"] = prefab_record(o.read(), mat_seen)
        print(f"disc {disc}: meshes so far {len(result['meshes'])}, prefabs {len(result['prefabs'])}", flush=True)
        if disc == 1:
            wd = C.get("assets/resources/worldmap/prefabs/worlddisc-incasethatitneedstocreateagain.prefab")
            if wd is not None:
                root = wd.read()
                tr = pptr_obj([pp for cid, pp in root.m_Component if cid == 4][0]).read()
                for _tid, g, _t in go_children(tr):
                    for cid, pp in g.m_Component:
                        ob = pptr_obj(pp)
                        if ob is not None and ob.type.name == "MonoBehaviour":
                            tt = ob.read_typetree()
                            result["worlddisc"][f"{tt['InitialX']},{tt['InitialY']}"] = {
                                k: tt[k] for k in ("IsSea", "HasSpecialObject", "IsSwitchable", "Number")}
            # every WorldMap material (not only prefab-referenced ones)
            for key, o in sorted(C.items()):
                if "worldmap/" in key and key.endswith(".mat") and o.type.name == "Material":
                    mat_seen.setdefault(o.read().m_Name, o)
    # ---- materials + shaders (both discs' prefab references + every WorldMap .mat) ----
    for name, mo in sorted(mat_seen.items()):
        tt = mo.read_typetree()
        sh = pptr_obj(mo.read().m_Shader)
        shname = None
        if sh is not None:
            stt = sh.read_typetree()
            script = stt.get("m_Script") or ""
            sm = re.match(r'\s*Shader "([^"]+)"', script)
            shname = sm.group(1) if sm else stt.get("m_Name")
            if shname not in result["shaders"]:
                safe = re.sub(r"[^A-Za-z0-9_.-]", "_", shname)
                (SHADER_TMP / f"{safe}.shader.txt").write_text(script, encoding="utf-8")
                result["shaders"][shname] = {"programs": shader_binds(script),
                                             "dump": str(SHADER_TMP / f"{safe}.shader.txt")}
        props = tt["m_SavedProperties"]
        result["materials"][name] = {
            "shader": shname,
            "tex": {e[0]["name"]: {"scale": [e[1]["m_Scale"]["x"], e[1]["m_Scale"]["y"]],
                                   "has_tex": bool(e[1]["m_Texture"]["m_PathID"])} for e in props["m_TexEnvs"]},
            "floats": {e[0]["name"]: e[1] for e in props["m_Floats"]},
        }
    # ---- calibration -------------------------------------------------------------------------------
    ok = True
    k = "d1/0_1/8,17/terrain"
    r = result["meshes"].get(k)
    c1 = r is not None and r["vcount"] == 339 and set(r["channels"]) == {"position", "normal", "uv0", "tangent"}
    print(f"CALIB mesh (8,17) terrain 339 verts, channels pos/nrm/uv0/tan: {'OK' if c1 else 'FAIL'}")
    ok &= c1
    inst = GAME_SHADERS / "WorldMap" / "Terrain.txt"
    if inst.is_file() and "WorldMap/Terrain" in result["shaders"]:
        a = [p["binds"] for p in shader_binds(inst.read_text(encoding="utf-8", errors="replace"))]
        b = [p["binds"] for p in result["shaders"]["WorldMap/Terrain"]["programs"]]
        c2 = a == b
        print(f"CALIB WorldMap/Terrain binds bundle={b} install={a}: {'OK' if c2 else 'FAIL'}")
        ok &= c2
    else:
        print("CALIB shader: install copy or bundle shader missing -> FAIL")
        ok = False
    result["calibration_ok"] = bool(ok)
    (OUT / "consumption_census.json").write_text(json.dumps(result, indent=0, default=str), encoding="utf-8")
    print(f"wrote {OUT / 'consumption_census.json'}  meshes={len(result['meshes'])} prefabs={len(result['prefabs'])} "
          f"worlddisc={len(result['worlddisc'])} materials={len(result['materials'])} shaders={len(result['shaders'])}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
