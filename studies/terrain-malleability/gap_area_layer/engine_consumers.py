"""ENGINE AREA CONSUMERS -- every C# site that reads the overworld tile AREA bits, directly or through a sysvar,
with its enclosing method, STOCK/PATCH provenance, cadence (continuous / one-shot / event) and effect.

Gap lane `gap_area_layer` of studies/terrain-malleability. READ-ONLY on the Memoria clone (source text + `git diff`
via the consumption lane's provenance oracle, imported with bytecode writing OFF so nothing lands in that lane's dir).

What it scans (the WHOLE Assembly-CSharp tree, every *.cs, not only ff9.cs):
  DIRECT     m_GetIDArea(            -- the bit decode itself (ff9.cs m_GetIDArea body excluded)
  SYSVAR     w_frameGetParameter(192|207) and GetSysvar(192|207)  -- the indirect routes the consumption lane's
             regex could not see
  TABLE      w_cameraArea2Place[ / w_worldAreaZone[ / w_worldArea2Zone( / BeachData  -- area-keyed LUTs
  ROUTE      GetSysvar(<non-literal>) / w_frameGetParameter(<non-literal>)  -- generic pass-throughs (the .eb
             script path; anything that can be configured to read 192/207)
  INDIRECT   callers of methods whose RETURN carries area (w_worldLocationName, CheckBeachMinigame,
             w_worldGetBattleScenePtr) -- 1 level of call-graph propagation

It also PARSES the area-keyed tables straight from source (so the policy numbers have a rerunnable origin):
w_cameraArea2Place (area -> camera place), w_worldAreaZone (area -> encounter zone), w_cameraElement (type_cam x
place -> posstat down/up/fly), w_cameraPosstat, EMinigame.BeachData (the AllSandyBeach areas), and
w_moveCHRControl[i].type_cam (vehicle -> camera type).

CALIBRATION (exit 1 on failure): the scan must rediscover the consumption lane's 9 area sites
(consumption/out/consumer_map.json, IDALL-BITS Area) AND the w_cameraArea2Place read in w_cameraChangeUpdate;
and the parsed w_worldAreaZone must equal the kit's independent transcription (world/worldpack.py _AREA_ZONE).

Rerun:  py studies/terrain-malleability/gap_area_layer/engine_consumers.py   -> out/engine_consumers.json
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.dont_write_bytecode = True                       # never drop a __pycache__ into another lane's dir
HERE = Path(__file__).resolve().parent
TM = HERE.parent
sys.path.insert(0, str(TM / "consumption"))
sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")
import provenance as PV                               # noqa: E402  (consumption lane's calibrated oracle)

ACS = PV.ACS
OUT = HERE / "out"

SIG = re.compile(r"^\s*(?:\[[^\]]*\]\s*)*(?:public|private|protected|internal)\s+(?:static\s+|override\s+|virtual\s+|"
                 r"readonly\s+|unsafe\s+|new\s+)*[\w<>\[\],.? ]+?\s+(\w+)\s*\(")
PATTERNS = [
    ("DIRECT", re.compile(r"\bm_GetIDArea\(")),
    ("SYSVAR192", re.compile(r"\b(?:w_frameGetParameter|GetSysvar)\(\s*192\s*\)")),
    ("SYSVAR207", re.compile(r"\b(?:w_frameGetParameter|GetSysvar)\(\s*207\s*\)")),
    ("TABLE", re.compile(r"\bw_cameraArea2Place\[|\bw_worldAreaZone\[|\bw_worldArea2Zone\(|\bBeachData\[")),
    ("ROUTE", re.compile(r"\b(?:w_frameGetParameter|GetSysvar)\(\s*(?!\d+\s*\))[^)]")),
]
# methods whose RETURN value carries area -> their callers are area consumers too (1-level propagation)
AREA_RETURNING = {"w_worldLocationName": r"\bw_worldLocationName\(\)", "CheckBeachMinigame": r"\bCheckBeachMinigame\(\)",
                  "w_worldGetBattleScenePtr": r"\bw_worldGetBattleScenePtr\(\)"}
SKIP_DEFS = {("Global/ff9/ff9.cs", "m_GetIDArea")}

# Human annotation per enclosing method -- every consumer found MUST have one (an unannotated hit fails the run,
# so a new consumer cannot hide behind the table).  (cadence, effect)
ANNOT = {
    "m_GetIDArea": ("-", "definition: (IDALL & 0x3F00) >> 8"),
    "w_cameraUpdate": ("continuous (every camera frame)", "area 12 AND w_frameScenePtr<4990 -> upperCounterForce=true: "
                       "drives the perspective counter to 0 (the DEFAULT near view) -- cancels the high 'bird's-eye' "
                       "view (posstat 7)"),
    "w_cameraChangeTrigger": ("event (player presses the perspective toggle)", "area 12 AND scene<4990 -> toggle "
                              "refused (no switch to the high view)"),
    "w_cameraChangeUpdate": ("continuous (every camera frame)", "w_cameraArea2Place[sysvar192] -> camera PLACE 0/1/2 -> "
                             "w_cameraElement[type_cam, place] picks the 'down' posstat (framing below actor y 13.67)"),
    "w_worldLocationName": ("continuous (every w_frameUpdateEvent)", "area -> WorldLocationText(area) for the PC window "
                            "title (area!=0, or topograph 0/37)"),
    "w_frameUpdateEvent": ("continuous", "caller of w_worldLocationName -> PlayerWindow.SetTitle (desktop window title)"),
    "w_frameGetParameter": ("on demand", "sysvar 192 = area; sysvar 207 = w_worldArea2Zone(area) (the .eb + UI route)"),
    "w_weatherDeside": ("ONE-SHOT (w_frameCounterReady==10 and keventScriptNo==0 -> the area under the SPAWN)",
                        "areas 9/12/13: Color[3] g/toffsetup=32600, re-dest weather, w_frameCloud=false (clouds off)"),
    "w_worldArea2Zone": ("-", "LUT read: w_worldAreaZone[area]"),
    "w_worldGetBattleScenePtr": ("event (each random-encounter roll that fires)", "zone=w_worldArea2Zone(area) -> the "
                                 "zone's record slice x topograph x fog -> battle scene (s60: miss = no battle)"),
    "SelectScene": ("event (encounter)", "caller of w_worldGetBattleScenePtr -> the battle scene"),
    "CheckBeachMinigame": ("continuous (polled by icon/collision/input each frame)", "sysvar192 in BeachData (21 areas) "
                           "AND GLOB bit 1042 AND on foot -> 'beach' search armed for that area's GLOB bit 856+i"),
    "PollFIcon_or_icon": ("continuous", "Beach / Exclamation+Beach bubble icon"),
    "MenuOpenEvent": ("event (menu open on the world map)", "FF9.mapNameStr = WorldLocationText(sysvar192) -> becomes "
                      "the SAVE-SLOT preview Location (SharedDataBytesStorage.cs:482)"),
    "DisplayGeneralInfo": ("event (main menu draw)", "main-menu location label = WorldLocationText(sysvar192)"),
    "GetSysvar": ("on demand", "generic sysvar router: code>=192 -> w_frameGetParameter(code)"),
    "PollCollisionIcon": ("continuous (icon poll)", "CheckBeachMinigame -> ExclamationAndBeach bubble instead of "
                          "Exclamation when a talkable object is near"),
    "CollisionRequest": ("continuous (collision poll, world mode)", "CheckBeachMinigame -> the BEACH bubble icon when "
                         "nothing else is targeted"),
    "ReadInput": ("continuous (input read, world mode)", "CheckBeachMinigame AND IsWorldTrigger -> strips Confirm "
                  "from the input mask (SQEX #2893) so the beach dig wins over a world trigger"),
    "expr_jumpToSubCommand": ("on demand (every .eb B_SYSVAR read)", "the .eb route: B_SYSVAR[n] -> GetSysvar(n) "
                              "-> w_frameGetParameter for n>=192 (world dispatchers read 192/207 here)"),
    "ReadCounter": ("on demand (journal draw)", "PATCH: Journal counter reads ANY configured sysvar; an area consumer "
                    "only if a journal entry is authored with A=192/207"),
    "WorldReadout": ("continuous while the ~ menu World tab is open", "PATCH: debug readout of event/area/topograph"),
}


def scan():
    rows = []
    files = sorted(p for p in ACS.rglob("*.cs") if "\\obj\\" not in str(p) and "/obj/" not in str(p))
    for p in files:
        rel = p.relative_to(ACS).as_posix()
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").split("\n")
        except OSError:
            continue
        txt = "\n".join(lines)
        if not any(k in txt for k in ("m_GetIDArea", "w_frameGetParameter", "GetSysvar", "w_cameraArea2Place",
                                      "w_worldAreaZone", "w_worldArea2Zone", "BeachData", "w_worldLocationName",
                                      "CheckBeachMinigame", "w_worldGetBattleScenePtr")):
            continue
        added = None
        method = "?"
        in_bc = False
        for i, ln in enumerate(lines, 1):
            s = ln.strip()
            if in_bc:
                if "*/" in s:
                    in_bc = False
                continue
            if s.startswith("/*") and "*/" not in s:
                in_bc = True
                continue
            if s.startswith("//"):
                continue
            m = SIG.match(ln)
            if m and not s.endswith(";"):
                method = m.group(1)
            code = s.split("//")[0]
            kinds = [k for k, pat in PATTERNS if pat.search(code)]
            for name, rx in AREA_RETURNING.items():
                if re.search(rx, code) and method != name and not re.search(r"\bstatic\b.*\b" + name + r"\(", code):
                    kinds.append("INDIRECT:" + name)
            if not kinds:
                continue
            if (rel, method) in SKIP_DEFS and kinds == ["DIRECT"] and "public static" in code:
                kinds = ["DEF"]
            if added is None:
                added = PV.added_lines(rel)
            rows.append({"file": rel, "line": i, "method": method, "kinds": kinds,
                         "prov": "PATCH" if i in added else "STOCK", "text": s[:170]})
    return rows


def _byte_array(src, name):
    m = re.search(r"ff9\." + name + r"\s*=\s*new Byte\[\]\s*\{([^}]*)\}", src)
    return [int(x) for x in re.findall(r"\d+", m.group(1))]


def parse_tables():
    src = (ACS / "Global/ff9/ff9.cs").read_text(encoding="utf-8", errors="replace")
    place = _byte_array(src, "w_cameraArea2Place")
    zone = _byte_array(src, "w_worldAreaZone")
    figure = _byte_array(src, "w_worldZoneFigure")
    post = []
    m = re.search(r"ff9\.w_cameraPosstat = new ff9\.s_cameraPosstat\[\]\s*\{(.*?)\};\s*ff9\.s_cameraElement", src, re.S)
    for blk in re.findall(r"\{([^{}]*)\}", m.group(1)):
        d = dict((k, float(v)) for k, v in re.findall(r"(\w+)\s*=\s*(-?[\d.]+)f", blk))
        post.append(d)
    elem = {}
    for a, b, dn, up, fl in re.findall(r"array2\[(\d), (\d)\] = new ff9\.s_cameraElement\s*\{\s*down = (\d+),\s*up = (\d+),"
                                       r"\s*fly = (\d+)\s*\}", src):
        elem[f"{a},{b}"] = {"down": int(dn), "up": int(up), "fly": int(fl)}
    tc = {int(i): int(v) for i, v in re.findall(r"w_moveCHRControl\[(\d+)\]\.type_cam = (\d+);", src)}
    em = (ACS / "Global/EMinigame.cs").read_text(encoding="utf-8", errors="replace")
    bm = re.search(r"BeachData = new List<Int32>\s*\{([^}]*)\}", em)
    beach = [int(x) for x in re.findall(r"\d+", bm.group(1))]
    return {"w_cameraArea2Place": place, "w_worldAreaZone": zone, "w_worldZoneFigure": figure,
            "w_cameraPosstat": post, "w_cameraElement": elem, "type_cam_by_control": tc, "BeachData": beach}


def place_effect(tables):
    """For each camera type, does place 1 / place 2 actually change the selected posstats vs place 0?"""
    post, elem = tables["w_cameraPosstat"], tables["w_cameraElement"]
    out = {}
    for tcam in range(5):
        p0 = elem[f"{tcam},0"]
        row = {}
        for pl in (1, 2):
            e = elem[f"{tcam},{pl}"]
            diffs = {}
            for slot in ("down", "up", "fly"):
                a, b = post[p0[slot]], post[e[slot]]
                dd = {k: (a[k], b[k]) for k in a if a[k] != b[k]}
                if dd:
                    diffs[slot] = {"posstat": [p0[slot], e[slot]], "fields": dd}
            row[f"place{pl}"] = diffs or "IDENTICAL to place 0"
        out[f"type_cam{tcam}"] = row
    return out


def main():
    OUT.mkdir(exist_ok=True)
    rows = scan()
    tables = parse_tables()
    # ---------------- calibration ----------------
    known = json.loads((TM / "consumption/out/consumer_map.json").read_text(encoding="utf-8"))["rows"]
    known_sites = {(r["file"], r["line"]) for r in known if r["class"] == "IDALL-BITS" and r["detail"] == "Area"}
    found = {(r["file"], r["line"]) for r in rows}
    miss = sorted(known_sites - found)
    cam = [r for r in rows if r["method"] == "w_cameraChangeUpdate" and "w_cameraArea2Place[" in r["text"]]
    from ff9mapkit.world import worldpack as WP
    kit_zone = list(WP._AREA_ZONE)
    zone_ok = tables["w_worldAreaZone"][:len(kit_zone)] == kit_zone[:len(tables["w_worldAreaZone"])]
    calib = {"known_consumption_sites": len(known_sites), "rediscovered": len(known_sites) - len(miss), "missed": miss,
             "w_cameraArea2Place_read_found": [f"{r['file']}:{r['line']}" for r in cam],
             "area_zone_len_engine": len(tables["w_worldAreaZone"]), "area_zone_len_kit": len(kit_zone),
             "area_zone_matches_kit": zone_ok, "place_len": len(tables["w_cameraArea2Place"])}
    ok = not miss and bool(cam) and zone_ok and len(tables["w_cameraArea2Place"]) >= 64
    unannot0 = sorted({r["method"] for r in rows if r["method"] not in ANNOT and "DEF" not in r["kinds"]})
    ok = ok and not unannot0
    # ---------------- annotation coverage ----------------
    unannot = sorted({r["method"] for r in rows if r["method"] not in ANNOT and "DEF" not in r["kinds"]})
    for r in rows:
        a = ANNOT.get(r["method"])
        r["cadence"], r["effect"] = (a if a else ("UNANNOTATED", "UNANNOTATED"))
        if r["prov"] == "PATCH":
            plus = PV._patch_plus_lines()
            r["patches"] = [n for n, st in plus.items() if r["text"].strip() in st] or ["(context-shifted)"]
    pl = tables["w_cameraArea2Place"]
    zone = tables["w_worldAreaZone"]
    place_groups = {}
    for a, v in enumerate(pl):
        place_groups.setdefault(v, []).append(a)
    res = {"calibration": calib, "calibration_ok": ok, "unannotated_methods": unannot,
           "rows": rows, "tables": tables, "place_groups": place_groups, "place_effect": place_effect(tables),
           "zone_groups": {z: [a for a, v in enumerate(zone) if v == z] for z in sorted(set(zone))}}
    (OUT / "engine_consumers.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print("CALIBRATION", json.dumps(calib))
    print("place groups:", {k: (min(v), max(v), len(v)) for k, v in place_groups.items()})
    for k, v in place_groups.items():
        print(f"  place {k}: areas {v}")
    print("BeachData:", tables["BeachData"])
    print("type_cam by control:", tables["type_cam_by_control"])
    print("place effect:", json.dumps(res["place_effect"], indent=0)[:2500])
    print(f"\n{len(rows)} consumer rows; prov={dict(Counter(r['prov'] for r in rows))}")
    for r in rows:
        print(f"  {r['prov']:<5} {r['file'].split('/')[-1]}:{r['line']:<6} {r['method']:<28} {','.join(r['kinds']):<34} "
              f"{r['text'][:80]}")
    if unannot:
        print("UNANNOTATED methods (add an ANNOT entry):", unannot)
    print("CALIBRATION", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
