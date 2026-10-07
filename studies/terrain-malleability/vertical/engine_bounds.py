"""THE VERTICAL ENVELOPE -- engine-side bounds, every constant read OUT OF SOURCE (not hand-copied).

For each anchor this script locates the line in the LIVE Memoria clone (C:/gd/FFIX/Memoria, which
carries our memoria-patches stack as working-copy edits) AND in the clone's committed HEAD
(`git show HEAD:<path>` = stock Memoria 6b8bb2d5, read-only, no index lock). An anchor whose exact
line text exists in HEAD is STOCK; one that exists only in the working copy is OUR PATCH.

It then derives the unit values the vertical-envelope table needs:
  * ground ray: climb origin offset, sky offset, the (dead) rayDistance, the miss fallback
  * flight ceiling (kmovementMaximumHeight) and where it is enforced
  * camera ride clamp (37.1 / 33.2), fuzzy probe radius, flyer eye floor, the posstat table in units
  * the SINK table per (slice_type, terrain class) in units, and the per-actor slice_type
  * the topograph LIMIT masks bit-decoded into topo sets per movement mode (foot..Invincible)
  * the airship landing tolerances, Blue Narciss y=0 pin, shadow lift, mist height-fog base

Read-only on everything. Writes out/engine_bounds.json.
Run:  py studies/terrain-malleability/vertical/engine_bounds.py
"""
import json
import math
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, r"C:\gd\Dream-World-IX\ff9mapkit")

MEM = Path(r"C:\gd\FFIX\Memoria")
HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)

FILES = {
    "ff9": "Assembly-CSharp/Global/ff9/ff9.cs",
    "physics": "Assembly-CSharp/Global/WM/WMPhysics.cs",
    "block": "Assembly-CSharp/Global/WM/WMBlock/WMBlock.cs",
    "world": "Assembly-CSharp/Global/WM/WMWorld/WMWorld.cs",
    "settings": "Assembly-CSharp/Global/WM/WMWorld/WMWorldSettings.cs",
    "actor": "Assembly-CSharp/Global/WM/WMActor/WMActor.cs",
    "director": "Assembly-CSharp/Global/WM/WMScriptDirector.cs",
}


def live(rel):
    return (MEM / rel).read_text(encoding="utf-8-sig", errors="replace").splitlines()


def stock(rel):
    r = subprocess.run(["git", "--no-optional-locks", "-C", str(MEM), "show", f"HEAD:{rel}"],
                       capture_output=True, check=True)
    return r.stdout.decode("utf-8-sig", errors="replace").splitlines()


SRC = {k: (live(v), stock(v)) for k, v in FILES.items()}


def anchor(key, pattern, *, nth=0):
    """Find `pattern` (regex) in file `key`; return {live_line, stock_line, status, text}."""
    lv, st = SRC[key]
    rx = re.compile(pattern)
    lhits = [i + 1 for i, s in enumerate(lv) if rx.search(s)]
    if not lhits:
        raise SystemExit(f"ANCHOR MISSING in live {FILES[key]}: {pattern!r}")
    ln = lhits[nth] if nth < len(lhits) else lhits[-1]
    text = lv[ln - 1].strip()
    # the k-th identical line in live maps to the k-th identical line in stock (robust to duplicates)
    k = sum(1 for s in lv[:ln - 1] if s.strip() == text)
    shits = [i + 1 for i, s in enumerate(st) if s.strip() == text]
    sl = shits[k] if k < len(shits) else (shits[-1] if shits else None)
    return {"file": FILES[key], "live_line": ln, "stock_line": sl,
            "status": "stock" if shits else "OUR-PATCH", "text": text[:160]}


def anchor_after(key, after, pattern):
    """First `pattern` line after the first `after` line (for lines that repeat verbatim)."""
    lv = SRC[key][0]
    a = next(i for i, s in enumerate(lv) if re.search(after, s))
    rx = re.compile(pattern)
    nth = sum(1 for s in lv[:a] if rx.search(s))
    return anchor(key, pattern, nth=nth)


def num(s):
    return float(s.rstrip("fF"))


E = {}          # evidence anchors
D = {}          # derived values

# ---- 1. the ground ray ------------------------------------------------------------------------------
E["rayStartOffsetYFromSky"] = anchor("ff9", r"rayStartOffsetYFromSky = [\d.]+f;")
E["rayStartOffsetY"] = anchor("ff9", r"ff9\.rayStartOffsetY = [\d.]+f;")
E["rayDistance"] = anchor("ff9", r"ff9\.rayDistance = [\d.]+f;")
E["defaultHeight"] = anchor("ff9", r"ff9\.defaultHeight = [\d.]+f;")
for k in ("rayStartOffsetYFromSky", "rayStartOffsetY", "rayDistance", "defaultHeight"):
    D[k] = num(re.search(r"= ([\d.]+f)", E[k]["text"]).group(1))
E["nwpHit_origin"] = anchor("ff9", r"origin\.y \+= \(\(!WMPhysics\.CastRayFromSky\)")
E["nwpHit_block_null_fallback"] = anchor("ff9", r"if \(absoluteBlock == null\)")
E["phys_t_negative_reject"] = anchor("physics", r"if \(\(Double\)num3 < 0\.0\)")
E["phys_upfacing_filter"] = anchor("physics", r"if \(num2 <= 0\.1f\)")
E["phys_skip_4078"] = anchor("physics", r"if \(num != 4078 \|\| WMPhysics\.IgnoreExceptions\)")
# rayDistance is passed in but never read: count 'distance' tokens inside WMBlock.Raycast's body
blv = SRC["block"][0]
start = next(i for i, s in enumerate(blv) if "public Boolean Raycast(Ray ray, out WMRaycastHit hit, Single distance" in s)
depth, body, i = 0, [], start
while True:
    s = blv[i]
    depth += s.count("{") - s.count("}")
    body.append(s)
    i += 1
    if depth == 0 and len(body) > 2:
        break
uses = sum(len(re.findall(r"\bdistance\b", s)) for s in body[1:])
E["block_raycast_sig"] = anchor("block", r"public Boolean Raycast\(Ray ray, out WMRaycastHit hit, Single distance")
D["block_raycast_distance_uses_in_body"] = uses          # 0 => the parameter is dead
D["sky_cast_terrain_ceiling_rel_actor_y"] = D["rayStartOffsetYFromSky"]
D["walk_climb_ceiling_rel_actor_y"] = D["rayStartOffsetY"]

# ---- 2. flight ceiling ------------------------------------------------------------------------------
E["kmovementMaximumHeight"] = anchor("ff9", r"const Single kmovementMaximumHeight = [\d.]+f;")
E["flight_ceiling_clamp"] = anchor("ff9", r"w_moveActorPtr\.pos\[1\] > 42\.1875f")
E["flight_floor_raise"] = anchor("ff9", r"Single num2 = s_moveCHRStatus\.ground_height \+ num;")
E["flight_yspeed_apply"] = anchor("ff9", r"pos4\[index\] = num11 \+ ff9\.w_moveCHRControl_YSpeed;")
D["flight_ceiling"] = num(re.search(r"= ([\d.]+f)", E["kmovementMaximumHeight"]["text"]).group(1))

# ---- 3. camera ---------------------------------------------------------------------------------------
E["camera_ride_clamp"] = anchor("ff9", r"Mathf\.Min\(num12, 33\.2f\) : Mathf\.Min\(num12, 37\.1f\)")
E["camera_ride_raise"] = anchor("ff9", r"num19 = ff9\.w_cameraPosstatNow\.cameraCorrect \+ num12;")
E["camera_fuzzy_radius"] = anchor("ff9", r"Single num21 = 5\.5f;")
E["camera_fuzzy_is_not_fly"] = anchor("ff9", r"ff9\.w_cameraFuzzy = !ff9\.w_moveCHRControlPtr\.flg_fly;")
E["camera_flyer_eye_floor"] = anchor("ff9", r"Single num = 17\.578125f;")
E["camera_flyer_eye_floor_use"] = anchor("ff9", r"if \(ff9\.w_moveCHRControlPtr\.type == 1 && num19 < num\)")
E["camera_ignore_exceptions"] = anchor_after("ff9", r"if \(!ff9\.GetEventEye\(\)\)", r"WMPhysics\.IgnoreExceptions = true;")
E["camera_correct_units"] = anchor("ff9", r"cameraCorrect = s_cameraPosstat\.cameraCorrect \* 0\.00390625f \* -1f;")
E["camera_eye_offset_y"] = anchor("ff9", r"w_cameraEyeOffset\.y = ff9\.w_cameraPosstatNow\.cameraHeight")
m = re.search(r"Min\(num12, ([\d.]+)f\) : Mathf\.Min\(num12, ([\d.]+)f\)", E["camera_ride_clamp"]["text"])
D["camera_ride_clamp_flyer_type1"], D["camera_ride_clamp_other"] = float(m.group(1)), float(m.group(2))
D["camera_fuzzy_radius"] = 5.5
D["camera_flyer_eye_floor"] = 17.578125
# the posstat table
fv = SRC["ff9"][0]
i0 = next(i for i, s in enumerate(fv) if "ff9.w_cameraPosstat = new ff9.s_cameraPosstat[]" in s)
blob = " ".join(fv[i0:i0 + 90])
ent = re.findall(r"cameraPers = ([-\d.]+)f,\s*cameraDistance = ([-\d.]+)f,\s*cameraHeight = ([-\d.]+)f,"
                 r"\s*cameraCorrect = ([-\d.]+)f,\s*aimHeight = ([-\d.]+)f", blob)
E["camera_posstat_table"] = {"file": FILES["ff9"], "live_line": i0 + 1,
                             "stock_line": anchor("ff9", r"ff9\.w_cameraPosstat = new ff9\.s_cameraPosstat\[\]")["stock_line"],
                             "status": "stock", "text": f"{len(ent)} entries"}
D["camera_posstat_units"] = [
    {"i": k, "pers": float(p), "distance_u": float(d) / 256, "eye_height_u": -float(h) / 256,
     "correct_u": -float(c) / 256, "aim_height_u": -float(a) / 256,
     "clip_threshold_other_u": -float(c) / 256 + D["camera_ride_clamp_other"],
     "clip_threshold_flyer_u": -float(c) / 256 + D["camera_ride_clamp_flyer_type1"],
     "flat_ground_pitch_deg": round(math.degrees(math.atan2(-float(h) / 256 - (-float(a) / 256), float(d) / 256)), 2)}
    for k, (p, d, h, c, a) in enumerate(ent)]
# absolute eye ceiling, the hard-coded Memoria-site camera dome, the altitude blend of the framing
E["camera_eye_abs_ceiling"] = anchor("ff9", r"w_cameraWorldEye\.y = Mathf\.Min\(ff9\.w_cameraWorldEye\.y, [\d.]+f\);")
D["camera_eye_abs_ceiling_u"] = float(re.search(r", ([\d.]+)f\);", E["camera_eye_abs_ceiling"]["text"]).group(1))
E["camera_dome_center_x"] = anchor("ff9", r"Single num28 = ff9\.w_cameraWorldEye\.x \+ [\d.]+f;")
E["camera_dome_center_z"] = anchor("ff9", r"Single num29 = ff9\.w_cameraWorldEye\.z \+ [\d.]+f;")
E["camera_dome_radius"] = anchor("ff9", r"Single num30 = 54\.6875f;")
E["camera_dome_floor"] = anchor("ff9", r"Single num32 = ff9\.SquareRoot0\(num31\) - [\d.]+f;")
dx = float(re.search(r"\+ ([\d.]+)f;", E["camera_dome_center_x"]["text"]).group(1))
dz = float(re.search(r"\+ ([\d.]+)f;", E["camera_dome_center_z"]["text"]).group(1))
drop = float(re.search(r"- ([\d.]+)f;", E["camera_dome_floor"]["text"]).group(1))
D["camera_dome"] = {"eye_center_xz": [-dx, -dz], "wrap_equiv_x": -dx + 1536, "radius": 54.6875,
                    "floor_at_center_u": 54.6875 - drop}
E["camera_height_param"] = anchor("ff9", r"hparam /= 4500;")
E["camera_height_param_bias"] = anchor("ff9", r"hparam \+= 1000;")
D["camera_framing_blend_band_u"] = [-1000 / 256, (4500 - 1000) / 256]   # t=0 .. t=4096
E["camera_area2place"] = anchor("ff9", r"ff9\.w_cameraArea2Place = new Byte\[\]")
a0 = E["camera_area2place"]["live_line"] - 1
ablob = " ".join(fv[a0:a0 + 80])
a2p = [int(x) for x in re.findall(r"\b(\d+)\b", ablob[ablob.index("{"):ablob.index("}")])]
D["camera_area2place"] = {p: [i for i, v in enumerate(a2p) if v == p] for p in sorted(set(a2p))}
E["camera_element_table"] = anchor("ff9", r"ff9\.s_cameraElement\[,\] array2 = new ff9\.s_cameraElement\[5, 3\];")
e0 = E["camera_element_table"]["live_line"] - 1
eblob = " ".join(fv[e0:e0 + 90])
D["camera_element"] = {f"{a},{b}": {"down": int(dn), "up": int(up), "fly": int(fl)} for a, b, dn, up, fl in
                       re.findall(r"array2\[(\d), (\d)\] = new ff9\.s_cameraElement\s*\{\s*down = (\d+),\s*up = (\d+),\s*fly = (\d+)", eblob)}
# the editor-only custom projection (near/far if it were ever used)
E["proj_geom_screen"] = anchor("world", r"public Int32 PsxGeomScreen = \d+;")
E["proj_clip_distance"] = anchor("world", r"public Int32 ClipDistance = \d+;")
E["proj_only_from_contextmenu"] = anchor("director", r"\[ContextMenu\(\"Use Custom Projection Matrix\"\)\]")
gs = int(re.search(r"= (\d+);", E["proj_geom_screen"]["text"]).group(1))
cd = int(re.search(r"= (\d+);", E["proj_clip_distance"]["text"]).group(1))
D["custom_projection_near_far_u"] = [gs / 256, (gs + cd) / 256]
E["block_stream_hard_limit"] = anchor("world", r"Int32 distanceHardLimit = 8;")
E["block_stream_plan_only"] = anchor("world", r"this\.Blocks\[currentX \+ i, currentY \+ j\]\.IsInsideSight = true;")
E["iifa_hide_center"] = anchor("world", r"Vector3 b = ff9\.w_effectLastPos \+ new Vector3\(0f, -15\.15f, 0f\);")
E["iifa_hide_radius"] = anchor("world", r"if \(num < 12f\)")
E["iifa_hide_block"] = anchor("world", r"WMBlock wmblock = this\.InitialBlocks\[11, 4\];")
E["effect_last_pos"] = anchor("ff9", r"ff9\.w_effectLastPos = new Vector3\(")
mm = re.search(r"Vector3\(([-\d.]+)f, ([-\d.]+)f, ([-\d.]+)f\)", E["effect_last_pos"]["text"])
D["iifa_hide_center_world"] = [float(mm.group(1)), float(mm.group(2)) - 15.15, float(mm.group(3))]

# ---- 4. fog ------------------------------------------------------------------------------------------
E["mist_heightfog_on"] = anchor("ff9", r"globalFog\.heightFog = true;")
E["mist_heightfog_base"] = anchor("ff9", r"globalFog\.height = 29f;")
E["nomist_heightfog_off"] = anchor("ff9", r"globalFog\.heightFog = false;")
E["mist_t_ref"] = anchor("ff9", r"position\.y / 52\.1875f")
D["mist_height_fog_base_u"] = 29.0
D["mist_fog_camera_y_ref_u"] = 52.1875

# ---- 5. sink / slice ---------------------------------------------------------------------------------
E["sink_array"] = anchor("ff9", r"ff9\.w_movementSinkArray = new Int16\[,\]")
j0 = E["sink_array"]["live_line"] - 1
sblob = " ".join(fv[j0:j0 + 50])
rows = re.findall(r"\{\s*([-\d\s,]+?)\s*\}", sblob[sblob.index("{") + 1:])
sink = [[int(x) for x in r.replace(" ", "").split(",") if x != ""] for r in rows[:4]]
E["slice_class_switch"] = anchor("ff9", r"public static Single w_movementGetSliceHeight")
E["slice_apply"] = anchor("ff9", r"wmActor\.pos1 = s_moveCHRStatus\.ground_height \+ s_moveCHRStatus\.slice_height;")
E["slice_immediate_flag"] = anchor("ff9", r"imd = \(num2 <= 0\);")
E["walk_probe_uses_actor_y"] = anchor_after("ff9", r"public static void w_movementControl\(", r"Vector3 pos = ff9\.w_moveActorPtr\.pos;")
CLASS_NAMES = ["36/37/38 forest+hillside", "53", "54", "55", "56", "57", "51 stream", "48 river",
               "other (incl. all grass/dirt/rock 49/50/52)"]
D["sink_table_raw"] = sink
D["sink_table_u"] = {f"slice_type {t}": {CLASS_NAMES[c]: (-(v - 100) / 256 if v else 0.0)
                                          for c, v in enumerate(row)} for t, row in enumerate(sink)}
# per-actor slice_type / flg_fly from the w_moveCHRStatus table
k0 = next(i for i, s in enumerate(fv) if "ff9.w_moveCHRStatus = new ff9.s_moveCHRStatus[" in s)
stblob = " ".join(fv[k0:k0 + 330])
srows = re.findall(r"slice_type = (\d+),.*?flg_fly = (\d+),\s*control = (\d+),\s*cache = (\d+)", stblob)
D["actor_status"] = [{"index": i, "slice_type": int(a), "flg_fly": int(b), "control": int(c), "cache": int(d)}
                     for i, (a, b, c, d) in enumerate(srows)]
E["actor_status_table"] = {"file": FILES["ff9"], "live_line": k0 + 1,
                           "stock_line": anchor("ff9", r"ff9\.w_moveCHRStatus = new ff9\.s_moveCHRStatus\[")["stock_line"],
                           "status": "stock", "text": f"{len(srows)} rows"}
# effective on-foot climb ceiling per terrain class for the controlled walker (index 1 = slice_type 1)
st1 = D["actor_status"][1]["slice_type"]
D["foot_effective_climb_by_class_u"] = {CLASS_NAMES[c]: D["rayStartOffsetY"] + (-(v - 100) / 256 if v else 0.0)
                                        for c, v in enumerate(sink[st1])}

# ---- 6. limit masks -> topo sets per mode ------------------------------------------------------------
c0 = next(i for i, s in enumerate(fv) if "ff9.w_moveCHRControl = new ff9.s_moveCHRControl[12]" in s)
cblob = "\n".join(fv[c0:c0 + 300])
blocks = [b for b in re.split(r"new ff9\.s_moveCHRControl", cblob)[1:] if not b.startswith("[")]
modes = []
for b in blocks:
    name = re.match(r"\s*(?://\s*(.*?)\n)?", b).group(1) or "?"
    g = lambda key: re.search(rf"{key} = ([^,\n]+),", b)
    lim = re.search(r"limit = new UInt32\[\]\s*\{\s*(?:0x)?([0-9A-Fa-f]+)u,\s*(?:0x)?([0-9A-Fa-f]+)u", b)
    l0, l1 = (int(lim.group(1), 16), int(lim.group(2), 16)) if lim else (0, 0)
    topos = sorted([t for t in range(32) if (l1 >> t) & 1] + [t for t in range(32, 64) if (l0 >> (t - 32)) & 1])
    modes.append({"mode": len(modes), "name": name.strip(), "type": int(g("type").group(1)),
                  "flg_fly": g("flg_fly").group(1).strip() == "true",
                  "speed_move": int(g("speed_move").group(1)), "radius": int(g("radius").group(1)),
                  "type_cam_inline": (int(g("type_cam").group(1)) if g("type_cam") else None),
                  "limit": [hex(l0), hex(l1)], "legal_topos": topos})
E["control_table"] = {"file": FILES["ff9"], "live_line": c0 + 1,
                      "stock_line": anchor("ff9", r"ff9\.w_moveCHRControl = new ff9\.s_moveCHRControl\[12\]")["stock_line"],
                      "status": "stock", "text": f"{len(modes)} modes"}
E["limit_check"] = anchor("ff9", r"public static Boolean w_movementCheckTopographID\(UInt32\[\] check, UInt32 id\)")
D["modes"] = modes
foot = set(modes[0]["legal_topos"])
fly = set(modes[8]["legal_topos"])
D["flight_blocked_topos"] = sorted(set(range(64)) - fly)
D["foot_blocked_topos"] = sorted(set(range(64)) - foot)
D["flight_legal_but_foot_blocked"] = sorted(fly - foot)

# ---- 7. vehicles / landing / shadow ------------------------------------------------------------------
E["narciss_ground_pinned_0"] = anchor_after("ff9", r"public static void w_movementUpdate\(\)", r"if \(posObj\.index == 8\)")
E["airship_land_height_tol"] = anchor("ff9", r"if \(ff9\.abs\(-vector\.y - num14\) > ff9\.S\(350\)\)")
E["airship_land_forbidden_topo"] = anchor("ff9", r"if \(num10 == 45 \|\| num10 == 46 \|\| num10 == 52\)")
E["airship_land_ring_radius"] = anchor("ff9", r"Int32 fixedPoint = ff9\.w_moveCHRControlPtr\.radius \* j / num13;")
E["narciss_land_topo53"] = anchor("ff9", r"if \(ff9\.m_GetIDTopograph\(num2\) != 53\)")
E["shadow_y"] = anchor("ff9", r"wmshadow\.transform\.position = new Vector3\(pos\.x, s_moveCHRStatus\.ground_height \+ num8, pos\.z\);")
E["shadow_lift_airship"] = anchor("ff9", r"num8 = 0\.6f;")
E["actor_fog_by_height_disabled"] = anchor("actor", r"this\.SetFog\(1f\);")
D["airship_land_height_tol_u"] = 350 / 256
D["airship_land_ring_radius_u"] = {m["name"]: m["radius"] / 256 for m in modes if m["mode"] in (6, 7, 8, 9)}
D["flying_actor_sky_origin_max_u"] = D["flight_ceiling"] + D["rayStartOffsetYFromSky"]

# ---- 8. per-mode step length and steepest climbable continuous slope ---------------------------------------
E["ground_step_speed"] = anchor("ff9", r"w_moveCHRControl_XZSpeed = ff9\.S\(ff9\.w_moveCHRControlPtr\.speed_move \* moveSpeed >> 12\);")
E["ground_step_full_stick"] = anchor("ff9", r"Int32 moveSpeed = leftStickX != 0 \|\| leftStickY != 0 \? 4096 : 0;")
# full stick: XZSpeed = S(speed_move * 4096 >> 12) = speed_move/256 per world tick; the fan's first probe is at
# that distance, so a continuous slope is climbable iff rise per step <= ceiling(standing class)
st_of_mode = {0: 1, 1: 1, 2: 1, 3: 1, 4: 1, 5: 1}         # modes 0-5 drive index 1/3-7 actors: slice_type 1
D["step_and_slope_by_mode"] = {}
for mo in modes:
    if mo["mode"] not in st_of_mode:
        continue
    step = mo["speed_move"] / 256
    row = {}
    for cls, ceil in D["foot_effective_climb_by_class_u"].items():
        row[cls.split()[0]] = {"ceiling_u": round(ceil, 4), "max_slope_deg": round(math.degrees(math.atan2(ceil, step)), 2)}
    D["step_and_slope_by_mode"][mo["name"]] = {"step_u": step, "by_standing_class": row}

res = {"evidence": E, "derived": D}
(OUT / "engine_bounds.json").write_text(json.dumps(res, indent=1))

# ---- print -------------------------------------------------------------------------------------------
print("EVIDENCE (live line / stock line / status):")
for k, v in E.items():
    print(f"  {k:34s} {v['file'].split('/')[-1]}:{v['live_line']:<5} stock:{str(v['stock_line']):<5} {v['status']:9s} | {v['text'][:90]}")
print("\nDERIVED:")
for k in ("rayStartOffsetY", "rayStartOffsetYFromSky", "rayDistance", "defaultHeight",
          "block_raycast_distance_uses_in_body", "flight_ceiling", "camera_ride_clamp_other",
          "camera_ride_clamp_flyer_type1", "camera_flyer_eye_floor", "custom_projection_near_far_u",
          "iifa_hide_center_world", "mist_height_fog_base_u", "airship_land_height_tol_u",
          "airship_land_ring_radius_u", "flying_actor_sky_origin_max_u", "camera_eye_abs_ceiling_u",
          "camera_dome", "camera_framing_blend_band_u", "camera_area2place", "camera_element"):
    print(f"  {k}: {D[k]}")
print("  camera posstat (i: distance, eye_h, correct -> clip threshold other/flyer):")
for p in D["camera_posstat_units"]:
    print(f"    {p['i']}: dist {p['distance_u']:.2f} eye_h {p['eye_height_u']:+.2f} correct {p['correct_u']:.2f}"
          f" aim {p['aim_height_u']:.2f} pitch {p['flat_ground_pitch_deg']:5.1f}deg"
          f" -> {p['clip_threshold_other_u']:.2f} / {p['clip_threshold_flyer_u']:.2f}")
print("  sink table (u):")
for t, row in D["sink_table_u"].items():
    print(f"    {t}: " + ", ".join(f"{k.split()[0]}={v:+.3f}" for k, v in row.items()))
print("  actor status (index: slice_type, flg_fly):",
      [(a["index"], a["slice_type"], a["flg_fly"]) for a in D["actor_status"]])
print("  ON-FOOT effective climb ceiling by standing class (u):")
for k, v in D["foot_effective_climb_by_class_u"].items():
    print(f"    {k}: {v:.4f}")
print("  modes:")
for m in modes:
    print(f"    {m['mode']:2d} {m['name'][:22]:22s} type {m['type']} fly {m['flg_fly']!s:5s} radius {m['radius']:4d}"
          f" limit {m['limit']} topos {m['legal_topos']}")
print("  steepest climbable slope (deg) by mode / standing class:")
for nm, v in D["step_and_slope_by_mode"].items():
    print(f"    {nm[:24]:24s} step {v['step_u']:.4f}: " + ", ".join(
        f"{k}={w['max_slope_deg']}" for k, w in v["by_standing_class"].items() if k in ("36/37/38", "other")))
print("  flight-blocked topos:", D["flight_blocked_topos"])
print("  flight-legal but foot-blocked:", D["flight_legal_but_foot_blocked"])
n_patch = sum(1 for v in E.values() if v["status"] != "stock")
print(f"\n{len(E)} anchors, {n_patch} from OUR PATCH stack, {len(E) - n_patch} stock.")
