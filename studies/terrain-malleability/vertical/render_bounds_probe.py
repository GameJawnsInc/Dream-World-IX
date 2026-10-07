"""RENDER-SIDE vertical bounds: is there planet curvature, and where are the world camera's clip planes?

1. CURVATURE. Stock C# has NO bend/curve logic (grep in NOTES.md). If a bend existed it would live in the
   vertex program of the world materials. Memoria ships the world shaders as text under
   StreamingAssets/Shaders/WorldMap/*.txt; this probe (a) parses each text shader's vertex program and
   reports whether it does anything to the position beyond the 4 MVP dot products, and (b) CALIBRATES that
   those text files are the shaders the blocks actually render with: it reads the Shader objects out of the
   worldmap asset bundle (p0data3.bin) with UnityPy and compares their serialized program text to the text
   file (whitespace-normalized SHA-1). Raw shader text is dumped ONLY to the scratchpad (never the repo).
2. CLIP PLANES. The live world camera is the scene object "WorldCamera" (WMWorld.cs:125); its projection is
   the prefab's own near/far/fov (the custom PSX projection is editor-only -- WMScriptDirector.cs:352). This
   probe scans the player's level files for a Camera on a GameObject named WorldCamera and prints its planes.

Read-only on the install. Writes out/render_bounds_probe.json (hashes, booleans, numbers only).
Run:  py studies/terrain-malleability/vertical/render_bounds_probe.py
"""
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
import UnityPy                                      # noqa: E402
from ff9mapkit.world import extract as X            # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX")
SHD = GAME / "StreamingAssets" / "Shaders" / "WorldMap"
TMP = Path(r"C:\Users\skaki\AppData\Local\Temp\claude\C--gd-Dream-World-IX"
           r"\8b61f6d3-b0c2-4ade-9f22-b2bc267b1c8d\scratchpad\vertical_shaders")
TMP.mkdir(parents=True, exist_ok=True)


def norm(s):
    return re.sub(r"\s+", " ", s).strip()


def vertex_ops(text):
    """The d3d9 vertex-program instructions (between the first "vs_ and its closing quote)."""
    m = re.search(r'"vs_\d_\d(.*?)"', text, re.S)
    if not m:
        return None
    return [ln.strip() for ln in m.group(1).splitlines() if ln.strip()]


def strict_mvp(text):
    """STRICT check: oPos is written ONLY from dp4 against the four rows of the constant matrix bound to
    glstate_matrix_mvp, applied to v0 or to a register built from v0 alone (the (x,y,z,1) homogenize mad/mov),
    possibly staged through a register written only by such dp4s and then mov'd into oPos. Any other write to a
    position register (e.g. a distance-based y-drop = a curvature bend) FAILS. Returns (ok, reason)."""
    ops = vertex_ops(text)
    if not ops:
        return False, "no vs program"
    mvp_rows = None
    for b in re.findall(r"Matrix (\d+) \[glstate_matrix_mvp\]", text):
        mvp_rows = {f"c{int(b) + i}" for i in range(4)}
    if mvp_rows is None:
        return False, "no glstate_matrix_mvp binding"
    pos_regs, pure = {"v0"}, {}                      # pure[reg] = components holding an untouched MVP row
    covered = set()                                  # oPos components written (must end as xyzw: no vacuous pass)
    for o in ops:
        if o.startswith(("dcl", "def")):
            continue
        parts = [x for x in re.split(r"[ ,]+", o) if x]
        opc, dst, srcs = parts[0], parts[1], parts[2:]
        dreg = dst.split(".")[0]
        dmask = set(dst.split(".")[1]) if "." in dst else set("xyzw")
        sregs = [x.split(".")[0].lstrip("-") for x in srcs]
        if opc in ("mad", "mov") and "v0" in sregs and all(r == "v0" or r.startswith("c") for r in sregs):
            pos_regs.add(dreg)
            continue
        if opc == "dp4" and len(sregs) == 2 and sregs[0] in mvp_rows and sregs[1] in pos_regs:
            if dreg != "oPos":
                pure.setdefault(dreg, set()).update(dmask)
            else:
                covered |= dmask
            continue
        if dreg == "oPos":
            if opc == "mov" and sregs and dmask <= pure.get(sregs[0], set()):
                covered |= dmask
                continue
            return False, f"oPos written by non-MVP op {opc}"
        if opc == "dp4" and dreg != "oPos" and len(sregs) == 2 and sregs[0] in mvp_rows and sregs[1] not in pos_regs:
            return False, f"MVP row applied to a non-position register {sregs[1]}"
        if dreg in pos_regs and dreg != "v0":
            # the register stops holding the untouched position from here on (a scratch reuse AFTER the
            # MVP is harmless; a later MVP read of it is caught above / by the dp4-into-oPos rule)
            pos_regs.discard(dreg)
        if dreg in pure:
            pure[dreg] -= dmask                      # those components are no longer a pure MVP row
    if covered != set("xyzw"):
        return False, f"UNVERIFIED: oPos components written via MVP = {''.join(sorted(covered)) or 'none'}"
    return True, "oPos = MVP(v0) only"


def pos_analysis(ops):
    """Which ops touch the incoming position register v0 / oPos? A pure MVP = oPos written only by dp4 with a
    constant matrix row against v0 (or the r0 = (v0.xyz,1) copy)."""
    v0_reads = [o for o in ops if re.search(r"\bv0\b", o) and not o.startswith("dcl")]
    opos = [o for o in ops if o.startswith(("dp4 oPos", "mov oPos", "mad oPos", "add oPos", "mul oPos"))]
    # any trig / pow on anything derived from position would be a bend candidate
    trig = [o for o in ops if o.split()[0] in ("sincos", "pow", "exp", "log", "rsq") and "oPos" in o]
    return {"v0_reads": v0_reads, "oPos_writes": opos, "trig_on_oPos": trig}


res = {"text_shaders": {}, "bundle_shaders": {}, "camera": []}
# ---- 1a. text shaders ------------------------------------------------------------------------------------
for f in sorted(SHD.glob("*.txt")):
    t = f.read_text(encoding="utf-8", errors="replace")
    name = re.search(r'Shader "([^"]+)"', t).group(1)
    ops = vertex_ops(t)
    pa = pos_analysis(ops) if ops else None
    pure, why = strict_mvp(t)
    # provenance: keep only opcode NAMES + counts in the repo, never shader text
    res["text_shaders"][name] = {"file": f.name, "sha1_norm": hashlib.sha1(norm(t).encode()).hexdigest()[:16],
                                 "vertex_ops": len(ops or []),
                                 "oPos_write_opcodes": [o.split()[0] for o in (pa or {}).get("oPos_writes", [])],
                                 "v0_read_count": len((pa or {}).get("v0_reads", [])), "pure_mvp": pure,
                                 "why": why}

# NEGATIVE CONTROLS (a check that cannot fail proves nothing): inject the classic curved-world bend -- a
# position-dependent y-drop before the MVP -- and a post-MVP clip-space tamper into the real Terrain program;
# the strict check must ACCEPT the pristine program and REJECT both.
_t = (SHD / "Terrain.txt").read_text(encoding="utf-8", errors="replace")
_bent = _t.replace("dp4 oPos.x, c0, r0", "mad r0.y, r0.x, r0.x, r0.y\n\t\t\t\t\t\tdp4 oPos.x, c0, r0", 1)
_tamp = _t.replace("mov oPos.zw, r1", "add r1.w, r1.w, c15.x\n\t\t\t\t\t\tmov oPos.zw, r1", 1)
res["negative_control"] = {"pristine_terrain": strict_mvp(_t), "bent_terrain": strict_mvp(_bent),
                           "clipspace_tamper": strict_mvp(_tamp)}
assert res["negative_control"]["pristine_terrain"][0] and not res["negative_control"]["bent_terrain"][0] \
    and not res["negative_control"]["clipspace_tamper"][0], f"strict_mvp failed its controls: {res['negative_control']}"
print("NEGATIVE CONTROLS:", res["negative_control"])

# ---- 1b. bundle shaders (calibration: are the text files what the blocks render with?) ---------------------
env = X._worldmap_env(1)
for obj in env.objects:
    if obj.type.name != "Shader":
        continue
    try:
        d = obj.read()
    except Exception as e:                                      # noqa: BLE001
        res["bundle_shaders"][f"pathid {obj.path_id}"] = {"error": str(e)[:120]}
        continue
    script = getattr(d, "m_Script", None)
    if isinstance(script, (bytes, bytearray)):
        script = script.decode("utf-8", errors="replace")
    nm = None
    if isinstance(script, str):
        mm = re.search(r'Shader "([^"]+)"', script)
        nm = mm.group(1) if mm else None
    nm = nm or getattr(d, "m_Name", None) or getattr(d, "name", None) or f"pathid {obj.path_id}"
    entry = {"has_script_text": isinstance(script, str) and len(script or "") > 0}
    if entry["has_script_text"]:
        (TMP / (re.sub(r"[^A-Za-z0-9_]+", "_", nm) + ".shader.txt")).write_text(script, encoding="utf-8")
        entry["sha1_norm"] = hashlib.sha1(norm(script).encode()).hexdigest()[:16]
        ops = vertex_ops(script)
        if ops:
            pa = pos_analysis(ops)
            entry["oPos_write_opcodes"] = [o.split()[0] for o in pa["oPos_writes"]]
            entry["pure_mvp"], entry["why"] = strict_mvp(script)
        tx = res["text_shaders"].get(nm)
        entry["matches_streamingassets_text"] = (tx is not None and tx["sha1_norm"] == entry["sha1_norm"])
    res["bundle_shaders"][nm] = entry

# which shader do the block terrain materials reference?  (MeshRenderer -> Material -> Shader name)
mat_shader = {}
for obj in env.objects:
    if obj.type.name != "Material":
        continue
    try:
        m = obj.read()
        sh = m.m_Shader.read() if m.m_Shader else None
        sname = None
        if sh is not None:
            s = getattr(sh, "m_Script", None)
            if isinstance(s, (bytes, bytearray)):
                s = s.decode("utf-8", errors="replace")
            if isinstance(s, str):
                mm = re.search(r'Shader "([^"]+)"', s)
                sname = mm.group(1) if mm else None
            sname = sname or getattr(sh, "m_Name", None)
        mat_shader[m.m_Name] = sname
    except Exception as e:                                      # noqa: BLE001
        mat_shader[f"pathid {obj.path_id}"] = f"ERR {str(e)[:60]}"
res["materials_in_worldmap_bundle"] = mat_shader

# ---- 2. the WorldCamera's clip planes ------------------------------------------------------------------------
data = GAME / "x64" / "FF9_Data"
for lv in sorted(data.glob("level*"), key=lambda p: int(p.name[5:] or 0)):
    try:
        e = UnityPy.load(str(lv))
    except Exception:                                           # noqa: BLE001
        continue
    for obj in e.objects:
        if obj.type.name != "Camera":
            continue
        try:
            c = obj.read()
            go = c.m_GameObject.read()
            gname = go.m_Name
        except Exception:                                       # noqa: BLE001
            continue
        res["camera"].append({"level": lv.name, "gameobject": gname,
                              "near": float(getattr(c, "near_clip_plane", float("nan"))),
                              "far": float(getattr(c, "far_clip_plane", float("nan"))),
                              "fov": float(getattr(c, "field_of_view", float("nan")))})

print("TEXT SHADERS (StreamingAssets/Shaders/WorldMap): name -> pure MVP vertex transform?")
for k, v in res["text_shaders"].items():
    print(f"  {k:32s} pure_mvp={v['pure_mvp']}  oPos write opcodes={v['oPos_write_opcodes']}")
print("\nBUNDLE SHADERS (p0data3 worldmap env):")
for k, v in res["bundle_shaders"].items():
    print(f"  {k:32s} {v}")
print("\nMATERIALS -> shader:", {k: v for k, v in list(mat_shader.items())[:40]})
print("\nCAMERAS:")
for c in res["camera"]:
    if "world" in c["gameobject"].lower() or c["level"] in ("level1", "level2"):
        print("  ", c)
print("  (all cameras named *World*):", [c for c in res["camera"] if "world" in c["gameobject"].lower()])
(OUT / "render_bounds_probe.json").write_text(json.dumps(res, indent=1, default=str))
print("wrote", OUT / "render_bounds_probe.json")
