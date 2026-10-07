"""THE CONSUMPTION MATRIX -- assembles the lane's caches into the per-part x per-attribute x per-consumer table.

Inputs (run these first; each is self-calibrating):
  census.py         -> out/consumption_census.json   (what data EXISTS: 2178 meshes, 962 prefabs, shaders)
  consumer_map.py   -> out/consumer_map.json         (who READS it: every engine site, STOCK/PATCH)
  bind_oracle.py    -> out/bind_oracle.json          (which override files the engine BINDS; 81 live receipts)
  landdonor_water.py-> out/landdonor_water.json      (the 12,10 free-ride)

The consumer cells below are source readings; every one is pinned to a needle that is re-located in the CURRENT
clone and re-classified STOCK/PATCH at run time (provenance.py), so a moved or deleted line fails the run instead
of silently citing stale code.

Rerun:  py studies/terrain-malleability/consumption/matrix.py   -> prints the matrix, writes out/matrix.json
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import provenance as PV                               # noqa: E402

OUT = HERE / "out"

# (consumer, what it reads, file, needle) -- every row re-located + provenance-checked at run time
CONSUMERS = [
    ("walk-register", "position+index (per-tri geometric normal); tangents array kept",
     "Global/WM/WMBlock/WMBlock.cs", "Vector3 item = Vector3.Cross(a - b, a2 - b);"),
    ("walk-filter", "tangent.x corner-0 full value vs {4078,4088,2040} (skipped unless IgnoreExceptions)",
     "Global/WM/WMPhysics.cs", "if (num != 4078 || WMPhysics.IgnoreExceptions)"),
    ("walk-filter", "geometric normal ny > 0.1 (NOT stored normal)",
     "Global/WM/WMPhysics.cs", "Single num2 = Vector3.Dot(Vector3.up, mesh.TriangleNormals[i]);"),
    ("walk-hit", "tangent.x corner-0 -> mapid (IDALL)",
     "Global/WM/WMBlock/WMBlock.cs", "mapid = (Int32)tangents[triangles[hit.triangleIndex * 3]].x;"),
    ("walk-veto", "IDALL == 0x31EE rejects the whole mesh unless control type 1",
     "Global/WM/WMBlock/WMBlock.cs", "return mapid != 0x31EE || ff9.w_moveCHRControlPtr.type == 1;"),
    ("walk-legality", "topograph bits vs per-vehicle mask (limit)",
     "Global/ff9/ff9.cs", "bool flag = ff9.w_movementCheckTopographID(s_moveCHRControl.limit, (uint)num);"),
    ("walk-cache-bypass", "current topograph 49/52 -> query without the tri cache",
     "Global/ff9/ff9.cs", "if ((num2 == 52 || num2 == 49) && ff9.w_moveCHRControlPtr.type != 1)"),
    ("npc-ground", "full IDALL 0xFEE/0x18EE/0x7EE/0x1BEE/0x2CEE -> keep stored height + remap id (parked vehicles)",
     "Global/ff9/ff9.cs", "if (s_moveCHRStatus.id == 0xFEE && (posObj.index == 1"),
    ("vehicle-sink", "topograph -> sink row (boat draft)",
     "Global/ff9/ff9.cs", "public static Single w_movementGetSliceHeight(Int32 type, Int32 id, ref Boolean imd)"),
    ("vehicle-getoff", "topograph 53 (boat) / 45,46,52 / 52 + ground mask",
     "Global/ff9/ff9.cs", "if (ff9.m_GetIDTopograph(num2) != 53)"),
    ("event-dispatch", "event bits != 0 -> WorldEvent(cell x,z from POSITION, event id)",
     "Global/ff9/ff9.cs", "if (ff9.m_GetIDEvent(s_moveCHRStatus.id) != 0 && ff9.w_frameEventEnable)"),
    ("encounter-monsters", "AREA bits -> zone; topograph + fog -> record",
     "Global/ff9/ff9.cs", "Int32 zoneId = ff9.w_worldArea2Zone(ff9.m_GetIDArea(ff9.m_moveActorID));"),
    ("script-sysvar", "192 = area, 193 = topograph, 205 = topo 36-38 (Ragtime), 207 = zone(area)",
     "Global/ff9/ff9.cs", "public static Int32 w_frameGetParameter(Int32 function)"),
    ("weather", "AREA 9/12/13 -> fog colour offsets + clouds off",
     "Global/ff9/ff9.cs", "switch (ff9.m_GetIDArea(ff9.m_moveActorID))"),
    ("camera-mode", "AREA 12 (scene<4990) forces upper camera, disables the camera toggle",
     "Global/ff9/ff9.cs", "if (ff9.w_frameScenePtr < 4990 && ff9.m_GetIDArea(ff9.m_moveActorID) == 12)"),
    ("camera-height", "sky-cast position, first-in-buffer, IgnoreExceptions (skip-class + down-facing HIT); topo 49 speed",
     "Global/ff9/ff9.cs", "if (ff9.m_GetIDTopograph(idall) == 49 || ff9.w_movePadDOWN || ff9.w_movePadLR)"),
    ("location-name", "AREA (when area!=0 or topo 0/37) -> WorldLocationText (window title)",
     "Global/ff9/ff9.cs", "return FF9TextTool.WorldLocationText(ff9.m_GetIDArea(idall));"),
    ("dust-sps", "topograph 30/34/35 beach, 41 desert, 36-38 forest; water mask -> MOVE_WATER",
     "Global/ff9/ff9.cs", "if (ff9.m_GetIDTopograph(ff9.m_moveActorID) == 30 || ff9.m_GetIDTopograph(ff9.m_moveActorID) == 34"),
    ("vehicle-spray+SE", "water mask / topo 41 -> spray, desert dust, SE 38 volume",
     "Global/ff9/ff9.cs", "Boolean isAboveWater = ff9.w_movementCheckTopographID(ff9.w_movementWaterStatus, ff9.m_moveActorID);"),
    ("shadow", "ground_height (ray hit Y) only; no normal, no projection",
     "Global/ff9/ff9.cs", "wmshadow.transform.position = new Vector3(pos.x, s_moveCHRStatus.ground_height + num8, pos.z);"),
    ("chocobo", "topograph 3/18/21/22/28 tracks; 36-38 Hot&Cold",
     "Global/ff9/ff9.cs", "public static Boolean w_frameChocoboCheck()"),
    ("render-material", "prefab CHILD NAME -> MaterialDatabase (Terrain/Object/Falls/Stream/...)",
     "Global/WM/WMBlock/WMBlock.cs", "if (MaterialDatabase.TryGetValue(renderer.gameObject.name, out Material material))"),
    ("render-lights", "3 directional lights (only N.L consumers: ScrollTexture = Falls/Stream)",
     "Global/ff9/ff9.cs", "ff9.w_light[0].transform.rotation = Quaternion.LookRotation(Vector3.down);"),
    ("override-load", ".ff9mesh: pos + normal? + uv? + tangent? + indices; ONE submesh; RecalculateBounds",
     "Memoria/World/WorldMeshOverride.cs", "mesh.triangles = indices;"),
    ("override-key", "TryLoad key = prefab child NAME under hard-coded 0_1",
     "Global/WM/WMWorld/WMWorld.cs", "\"WorldMap/Disc{0}/0_1/r{1}/Block[{2}][{3}] {4}\", this.overrideDiscTag, block.InitialY, block.InitialX,"),
    ("override-divert", "IsSea cell: Terrain.ff9mesh EXISTS -> donor prefab, else SeaBlockPrefab",
     "Global/WM/WMWorld/WMWorld.cs", "&& Memoria.World.WorldMeshOverride.HasLandOverride(this.overrideDiscTag, initialX, initialY))"),
    ("override-texture", "per-cell PNG clones the child material (then SetupPreloadedMaterials may overwrite it)",
     "Global/WM/WMWorld/WMWorld.cs", "Material m = new Material(mr.sharedMaterial);   // keep the sea shader; swap the texture"),
    ("override-texture-overwrite", "LoadBlock ends with SetupPreloadedMaterials -> DB-named parts lose a per-cell PNG",
     "Global/WM/WMWorld/WMWorld.cs", "block.SetupPreloadedMaterials();"),
]

SPECIAL_IDALL = {0xFEE: "0xFEE skip+parked", 4088: "4088 skip", 2040: "2040 skip", 0x31EE: "0x31EE flight-veto",
                 0x18EE: "0x18EE parked", 0x7EE: "0x7EE parked", 0x1BEE: "0x1BEE parked", 0x2CEE: "0x2CEE parked"}


def main():
    C = json.loads((OUT / "consumption_census.json").read_text(encoding="utf-8"))
    B = json.loads((OUT / "bind_oracle.json").read_text(encoding="utf-8"))
    L = json.loads((OUT / "landdonor_water.json").read_text(encoding="utf-8"))
    CM = json.loads((OUT / "consumer_map.json").read_text(encoding="utf-8"))
    ok = C["calibration_ok"] and B["calibration_ok"] and L["calibration"]["ok"] and CM["self_check_ok"]
    print(f"input calibrations: census={C['calibration_ok']} bind_oracle={B['calibration_ok']} "
          f"landdonor={L['calibration']['ok']} consumer_map={CM['self_check_ok']}")

    # ---- part rows: what data exists (referenced meshes only = what the engine can load) --------------------------
    referenced = set()
    child_of = {}
    for pk, p in C["prefabs"].items():
        for ch in p["children"]:
            if ch.get("mesh_key"):
                referenced.add(ch["mesh_key"])
                child_of.setdefault(ch["mesh_key"], (ch["go"], tuple(ch.get("materials", []))))
    rows = defaultdict(list)
    for mk, m in C["meshes"].items():
        if mk in referenced:
            go, mats = child_of[mk]
            rows[go].append((mk, m, mats))
    out = {"parts": {}}
    print("\nPART (prefab child) | meshes | channels | 1-submesh | flat | perm | tan.yzw==0 | tan.x tri-uniform | "
          "up>0.1 | material -> shader : binds")
    for go in sorted(rows):
        rs = rows[go]
        ms = [m for _, m, _ in rs]
        mats = Counter(mt for _, _, mt in rs)
        mat = mats.most_common(1)[0][0][0] if mats else None
        sh = C["materials"].get(mat, {}).get("shader") if mat else None
        binds = C["shaders"].get(sh, {}).get("programs", [{}])[0].get("binds") if sh else None
        light = C["shaders"].get(sh, {}).get("programs", [{}])[0].get("lighting") if sh else None
        chans = Counter(tuple(sorted(m["channels"])) for m in ms)
        yzw0 = sum(all(m["tangent"][c]["n_distinct"] == 1 and m["tangent"][c]["min"] == 0.0 for c in "yzw") for m in ms)
        uni = min(m.get("tangent_x_tri_uniform", 1.0) for m in ms)
        tris = sum(m["tris"] for m in ms)
        up = sum(m["tris_upfacing_gt_0.1"] for m in ms)
        flags = Counter()
        specials = Counter()
        for m in ms:
            for k, v in m.get("flags_hist", {}).items():
                flags[int(k)] += v
            for idall, cnt in m.get("idall_hist_top", []):
                pass
        rec = {"meshes": len(ms), "channels": {",".join(k): v for k, v in chans.items()},
               "single_submesh": sum(m["submeshes"] == 1 for m in ms), "flat": sum(m["vcount"] == m["icount"] for m in ms),
               "index_permutation": sum(m.get("index_is_permutation", False) for m in ms),
               "identity_index": sum(m["identity_index"] for m in ms), "tan_yzw_all_zero": yzw0,
               "tan_x_tri_uniform_min": uni, "tris": tris, "upfacing": up,
               "skip_class_tris": sum(m.get("skip_class_tris", 0) for m in ms),
               "veto_tris": sum(m.get("flight_veto_tris", 0) for m in ms),
               "idall_flags_bits_hist": dict(flags), "material": dict(Counter(mt[0] for _, _, mt in rs if mt)),
               "shader": sh, "binds": binds, "shader_light_uniforms": light}
        out["parts"][go] = rec
        print(f"{go:<15}| {len(ms):4} | {'/'.join(k for k in rec['channels'])[:34]:<34} | {rec['single_submesh']:4} | "
              f"{rec['flat']:4} | {rec['index_permutation']:4} | {yzw0:4} | {uni:.3f} | {up / max(tris, 1):.3f} | "
              f"{mat} -> {sh} : {binds}{' +N.L' if binds and 'normal' in binds else ''}")
    # ---- IDALL bit usage across ALL referenced tris ----------------------------------------------------------------
    area = Counter(); topo = Counter(); event = Counter(); flags = Counter(); big = 0
    for mk in referenced:
        m = C["meshes"][mk]
        for k, v in m.get("area_hist", {}).items():
            area[int(k)] += v
        for k, v in m.get("topo_hist", {}).items():
            topo[int(k)] += v
        for k, v in m.get("event_hist", {}).items():
            event[int(k)] += v
        for k, v in m.get("flags_hist", {}).items():
            flags[int(k)] += v
        big += m.get("idall_gt_16bit", 0)
    full = Counter()
    for mk in referenced:
        for k, v in C["meshes"][mk].get("idall_hist", {}).items():
            full[int(k)] += v
    spec = {SPECIAL_IDALL[k]: full.get(k, 0) for k in SPECIAL_IDALL}
    flag2 = sum(v for k, v in full.items() if (k & 3) == 2)
    flag2_special = sum(v for k, v in full.items() if (k & 3) == 2 and k in SPECIAL_IDALL)
    flag2_other = Counter({k: v for k, v in full.items() if (k & 3) == 2 and k not in SPECIAL_IDALL})
    print(f"\nspecial full-value IDALL tri counts: {spec}")
    print(f"flags==2 tris: {flag2}, of which special full values: {flag2_special}; other flags-2 IDALLs "
          f"(hex, area, topo, tris): {[(hex(k), (k & 0x3F00) >> 8, (k & 0xFC) >> 2, v) for k, v in flag2_other.most_common(10)]}")
    out["special_idall"] = spec
    out["flags2"] = {"total": flag2, "special": flag2_special, "other_values": len(flag2_other)}
    print(f"\nIDALL over all referenced tris: event bits {dict(sorted(event.items()))}; flags bits {dict(sorted(flags.items()))}; "
          f"IDALL outside 0..0xFFFF: {big}")
    w_area = {a: area[a] for a in (9, 12, 13)}
    print(f"weather/camera AREA tiles: {w_area}  (area 12 also forces the upper camera on scenes < 4990)")
    blocks_12 = sorted({mk.split('/')[2] for mk in referenced if C['meshes'][mk].get('area_hist', {}).get('12')
                        and mk.startswith('d1/0_1')})
    print(f"disc-1 form-1 blocks carrying area-12 tiles: {len(blocks_12)} {blocks_12[:24]}")
    out["idall"] = {"event": dict(event), "flags": dict(flags), "area": dict(area), "topo": dict(topo),
                    "area_12_blocks_d1": blocks_12, "outside_16bit": big}
    # ---- consumers, re-located + provenance-classified --------------------------------------------------------------
    print("\nCONSUMER | reads | cite (re-located now) | provenance")
    out["consumers"] = []
    for name, reads, rel, needle in CONSUMERS:
        try:
            ln = PV.find_line(rel, needle)
            pv = PV.classify(rel, ln)
            cite, prov = pv["cite"], pv["verdict"] + (f"({','.join(pv['patches'])})" if pv["patches"] else "")
        except SystemExit:
            cite, prov, ok = f"{rel}: NEEDLE LOST", "?", False
        out["consumers"].append({"consumer": name, "reads": reads, "cite": cite, "prov": prov})
        print(f"  {name:<26} {reads[:78]:<78} {cite:<40} {prov}")
    # ---- headline override facts --------------------------------------------------------------------------------
    cal = B["calibration"]
    print(f"\nbind oracle: {len(B['cells'])} override cells; engine receipts matched {cal['match']}/{cal['match'] + len(cal['mismatch'])} "
          f"(excluded {len(cal['excluded_changed_after_log'])} changed after log); dead files {B['dead']}")
    l1 = L["disc1_12_10"]
    print(f"12,10 land donor free-ride: parts {l1['parts']}, water covers {l1['water_coverage'] * 100:.2f}% of the cell, "
          f"boat-legal first hit {l1['boat_legal_fraction'] * 100:.2f}%")
    out["ok"] = bool(ok)
    (OUT / "matrix.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
    print(f"\nwrote {OUT / 'matrix.json'}  all-inputs-calibrated={ok}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
