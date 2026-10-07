"""THE CONSUMER MAP -- every engine site that reads overworld block-mesh data, with its enclosing method and
STOCK/PATCH provenance. The rerunnable evidence behind the consumption matrix's consumer columns.

Scans the patched Memoria clone (read-only) for the patterns through which mesh data reaches gameplay:
  IDALL-BITS   m_GetIDEvent / m_GetIDArea / m_GetIDTopograph            (tangent.x bit-field decodes)
  IDALL-FULL   full-value equality on a hit id (0x31EE, 4078/4088/2040, 0xFEE ...)  (area+flags bits load-bearing)
  TOPO-MASK    w_movementCheckTopographID                              (per-vehicle bit masks over topograph)
  TANGENT      tangents[...]  (which component is read)
  NORMALS      .Normals / TriangleNormals / mesh.normals              (stored vs recomputed normals)
  RAY          w_cellHit / w_nwpHit / WMBlock.Raycast callers          (position consumers)
  BYPASS       WMPhysics.IgnoreExceptions = true                       (sites that skip the up-facing + mapid filters)

Method attribution: the nearest preceding C# method signature line. Provenance: provenance.added_lines (git diff vs
the pinned upstream HEAD), so every row says STOCK or PATCH(<patch files>).

Self-check (asserted): the scan must find WMPhysics.cs's `tangents[triangles[i * 3]].x` read as TANGENT .x, find NO
tangent .y/.z/.w read anywhere in the world code, and find the `m_GetIDArea` decode in w_worldGetBattleScenePtr --
three facts already established by eye; if the scanner misses any of them it is blind and the run fails.

Rerun:  py studies/terrain-malleability/consumption/consumer_map.py     -> out/consumer_map.json
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import provenance as PV                               # noqa: E402

ACS = PV.ACS
FILES = ["Global/ff9/ff9.cs", "Global/WM/WMBlock/WMBlock.cs", "Global/WM/WMPhysics.cs", "Global/WM/WMWorld/WMWorld.cs",
         "Memoria/World/WorldMeshOverride.cs", "Global/World/WorldHUD.cs", "Global/Event/EventCollision.cs",
         "Global/Event/Engine/EventEngine.cs", "Global/Event/Engine/EventEngine.ProcessEvents.cs",
         "Global/WM/WMScriptDirector.cs", "Memoria/Application/SmoothFrameUpdater_World.cs"]
PATTERNS = {
    "IDALL-BITS": re.compile(r"m_GetID(Event|Area|Topograph)\("),
    "IDALL-FULL": re.compile(r"(mapid|\.id|num) (==|!=) (0x[0-9A-Fa-f]+|\d{3,5})\b|num (!=|==) (4078|4088|2040)"),
    "TOPO-MASK": re.compile(r"w_movementCheckTopographID\("),
    "TANGENT": re.compile(r"tangents\[[^\]]*\]\]?\.([xyzw])|Tangents\b"),
    "NORMALS": re.compile(r"\.Normals\b|TriangleNormals|mesh\.normals|\.normals\b"),
    "RAY": re.compile(r"\bw_cellHit\(|\bw_nwpHit\(|\.Raycast\(ray|absoluteBlock\.Raycast\(|block\.Raycast\("),
    "BYPASS": re.compile(r"WMPhysics\.IgnoreExceptions = true"),
}
SIG = re.compile(r"^\s*(public|private|protected|internal)\s+(static\s+)?[\w<>\[\],. ]+\s+(\w+)\s*\(")


def scan():
    rows = []
    for rel in FILES:
        p = ACS / rel
        if not p.is_file():
            continue
        lines = p.read_text(encoding="utf-8", errors="replace").split("\n")
        added = PV.added_lines(rel)
        method = "?"
        in_block_comment = False
        for i, ln in enumerate(lines, 1):
            s = ln.strip()
            if "/*" in s and "*/" not in s:
                in_block_comment = True
            if in_block_comment:
                if "*/" in s:
                    in_block_comment = False
                continue
            if s.startswith("//"):
                continue
            m = SIG.match(ln)
            if m:
                method = m.group(3)
            for cls, pat in PATTERNS.items():
                for mm in pat.finditer(ln):
                    detail = mm.group(1) if cls in ("IDALL-BITS",) else (mm.group(1) if cls == "TANGENT" and mm.lastindex else None)
                    if cls == "IDALL-FULL" and (rel.endswith("EventCollision.cs") or ("posObj.index" in ln and "id ==" not in ln)):
                        continue                       # EventCollision's numeric tests are FIELD quad/NPC ids, not world IDALL
                    rows.append({"class": cls, "detail": detail, "file": rel, "line": i, "method": method,
                                 "prov": "PATCH" if i in added else "STOCK", "text": s[:150]})
    return rows


def main():
    rows = scan()
    # attribute PATCH rows to patch files
    plus = PV._patch_plus_lines()
    for r in rows:
        if r["prov"] == "PATCH":
            r["patches"] = [n for n, st in plus.items() if r["text"].strip() in st] or ["(context-shifted)"]
    # ---- self-check -------------------------------------------------------------------------------------------
    t_x = [r for r in rows if r["class"] == "TANGENT" and r["detail"] == "x" and r["file"].endswith("WMPhysics.cs")]
    t_yzw = [r for r in rows if r["class"] == "TANGENT" and r["detail"] in ("y", "z", "w")]
    area_enc = [r for r in rows if r["class"] == "IDALL-BITS" and r["detail"] == "Area" and r["method"] == "w_worldGetBattleScenePtr"]
    ok = bool(t_x) and not t_yzw and bool(area_enc)
    print(f"SELF-CHECK tangent.x in WMPhysics: {len(t_x)}  tangent.y/z/w reads: {len(t_yzw)}  "
          f"area decode in w_worldGetBattleScenePtr: {len(area_enc)}  -> {'OK' if ok else 'FAIL'}")
    by = defaultdict(list)
    for r in rows:
        by[(r["class"], r["detail"])].append(r)
    for (cls, det), rs in sorted(by.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
        meths = Counter(r["method"] for r in rs)
        prov = Counter(r["prov"] for r in rs)
        print(f"\n{cls} {det or ''}: {len(rs)} sites  prov={dict(prov)}")
        for r in rs:
            tag = r["prov"] if r["prov"] == "STOCK" else f"PATCH{r.get('patches')}"
            print(f"   {r['file'].split('/')[-1]}:{r['line']:<6} {r['method']:<34} {tag:<8} {r['text'][:95]}")
    (HERE / "out" / "consumer_map.json").write_text(json.dumps({"self_check_ok": ok, "rows": rows}, indent=1), encoding="utf-8")
    print(f"\nwrote {HERE / 'out' / 'consumer_map.json'}  rows={len(rows)}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
