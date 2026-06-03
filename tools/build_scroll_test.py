#!/usr/bin/env python3
"""Phase-0 SCROLL SPIKE: a larger-than-screen (2x-wide) room as field 4003/SCROLL01.

Goal: prove the Memoria engine scrolls the view to follow the player on a MINTED custom field.
Engine facts (from source):
  * 3D scroll is automatic for a walkable field (FieldMap.SceneService3DScroll), but gated on the
    field's Active flag (IsActive => flags & FieldMapFlags.Active).
  * Active is set by the script opcode BGCACTIVE 0x71 "EnableCameraServices" (args isActive,
    frameCount, sinusOrLinear). The blank field never calls it -> we inject BGCACTIVE(1,0,0).
  * .bgx CAMERA Range = full painting size; Viewport = scroll clamp
    (vrpMinX,vrpMaxX,vrpMinY,vrpMaxY). The view-window spans the painting when
    Viewport = (HalfNative, w-HalfNative, HalfNative_h, h-HalfNative_h) = (160, w-160, 112, h-112).
  * The camera FOCAL LENGTH must NOT change for a wider painting: build proj from the 384 window,
    then widen Range to 768. (make_camera couples proj to range_w, so we pass proj explicitly and
    emit a camera.bgx the field.toml borrows.)

Deploy = reachable via the interior door repoint (HUT_INT Field(4000) -> Field(4003)), same
reversible harness as every bounds test. Writes tools/scroll_out/revert_scroll_test.py.

Run:  python tools/build_scroll_test.py
"""
import os, sys, struct, shutil, tempfile, datetime
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.scene import cam as C, guide as G, bgx as BGX
from ff9mapkit import build as B
from ff9mapkit.config import find_game_path, ModLayout, LANGS
from ff9mapkit.eb import EbScript, edit, opcodes, disasm
from PIL import Image, ImageDraw, ImageFont

OUT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "scroll_out")))
OUT.mkdir(parents=True, exist_ok=True)

# ---------- camera + canvas ----------
NAME = "SCROLL01"
FID, AREA = 4003, 11
PITCH, DIST, FOVX, YAW = 40.0, 4500.0, 42.2, 0.0
WIN_W = 384                       # the focal-defining window width (normal field)
RANGE_W, RANGE_H = 768, 448       # the FULL painting: 2x wide -> horizontal scroll
HALF_W, HALF_H = 160, 112         # PSX-native half-extents used by the engine's scroll clamp
S = 4                              # PNG upscale
CHAR_OFF = 0.0                     # keep walkmesh exactly on the painted floor (clean scroll read)

# scroll clamp so the native view window can span the whole painting (FieldMap.cs:1111-1114)
VIEWPORT = (HALF_W, RANGE_W - HALF_W, HALF_H, RANGE_H - HALF_H)   # (160, 608, 112, 336)
proj = G.proj_from_fov_x(FOVX, WIN_W)                              # focal from the 384 window, NOT 768
cam = G.make_camera(PITCH, DIST, proj=proj, yaw_deg=YAW,
                    range_wh=(RANGE_W, RANGE_H), viewport=VIEWPORT)
print(f"camera: pitch {PITCH} fov {FOVX} -> proj {proj}; Range {RANGE_W}x{RANGE_H}; Viewport {VIEWPORT}")

def cv(x, z):
    return C.to_canvas((x, 0, z), cam)

# ---------- frame the floor so it fills the wide canvas ----------
BACK_CY, FRONT_CY = 120.0, 430.0
ZB = round(C.solve_z_for_canvasY(cam, BACK_CY))
ZF = round(C.solve_z_for_canvasY(cam, FRONT_CY))

def solve_x_for_cx(target_cx, z, lo=-20000.0, hi=20000.0):
    """World x (at given z) whose foot projects to canvas column target_cx (monotonic -> bisect)."""
    fa = cv(lo, z)[0] - target_cx
    for _ in range(80):
        m = 0.5 * (lo + hi)
        fm = cv(m, z)[0] - target_cx
        if abs(fm) < 0.01:
            return m
        if (fm > 0) == (fa > 0):
            lo, fa = m, fm
        else:
            hi = m
    return 0.5 * (lo + hi)

# fill canvas columns ~24..(W-24) at the FRONT row (widest footprint); world rect uses that x-extent
XL = solve_x_for_cx(24.0, ZF)
XR = solve_x_for_cx(RANGE_W - 24.0, ZF)
print(f"floor world: x[{XL:.0f}..{XR:.0f}]  z[{ZF}..{ZB}]   (front fills canvas ~24..{RANGE_W-24})")
world = [(XL, ZB), (XR, ZB), (XR, ZF), (XL, ZF)]        # BL, BR, FR, FL (x,z)
for nm, (x, z) in zip(("BL", "BR", "FR", "FL"), world):
    print(f"   {nm} world=({x:.0f},0,{z}) -> canvas {tuple(round(v,1) for v in cv(x,z))}")

# ---------- paint floor.png (checker + numbered landmark columns + walkmesh outline) ----------
img = Image.new("RGBA", (RANGE_W * S, RANGE_H * S), (0, 0, 0, 0))
dr = ImageDraw.Draw(img, "RGBA")

def px(x, z):
    cx, cy = cv(x, z)
    return (cx * S, cy * S)

N = 10
xs = [XL + (XR - XL) * i / N for i in range(N + 1)]
zs = [ZF + (ZB - ZF) * j / N for j in range(N + 1)]
for j in range(N):
    for i in range(N):
        q = [px(xs[i], zs[j]), px(xs[i + 1], zs[j]), px(xs[i + 1], zs[j + 1]), px(xs[i], zs[j + 1])]
        dr.polygon(q, fill=((95, 140, 110, 255) if (i + j) % 2 == 0 else (55, 80, 66, 255)))

try:
    fnt = ImageFont.truetype("arial.ttf", 28 * S // 2)
except OSError:
    fnt = ImageFont.load_default()

# 5 bright numbered landmark columns spread across the floor width -> scroll is obvious
band_cols = [(255, 80, 80), (255, 180, 60), (90, 230, 120), (90, 190, 255), (200, 120, 255)]
for k in range(5):
    bx = XL + (XR - XL) * k / 4
    p0, p1 = px(bx, ZB), px(bx, ZF)
    dr.line([p0, p1], fill=band_cols[k] + (255,), width=5 * S)
    dr.text((p1[0] + 6, p1[1] - 40 * S // 2), f"x={bx:.0f}", fill=band_cols[k] + (255,), font=fnt,
            stroke_width=S, stroke_fill=(0, 0, 0, 230))

# walkmesh outline (bright) so the user can see the floor edge track with the scroll
out = [px(x, z) for (x, z) in world]
dr.line(out + [out[0]], fill=(255, 230, 90, 255), width=3 * S)
img.save(OUT / "floor.png")
Image.new("RGBA", (RANGE_W * S, RANGE_H * S), (22, 24, 30, 255)).save(OUT / "surround.png")
print("wrote floor.png (checker + 5 numbered columns + walkmesh outline) + surround.png")

# ---------- camera.bgx (so the field.toml can BORROW the wide-range / normal-focal camera) ----------
(OUT / "camera.bgx").write_text(BGX.build(cam, [], header_comment=f"{NAME} scroll camera"),
                                encoding="utf-8", newline="\n")

# ---------- field.toml ----------
SPAWN_Z = round((ZF + ZB) / 2)
toml = f"""# SCROLL SPIKE: 2x-wide horizontally-scrolling room (Phase 0)
[field]
id = {FID}
name = "{NAME}"
area = {AREA}
text_block = 1073

[camera]
borrow = "camera.bgx"   # wide Range {RANGE_W}x{RANGE_H} + scroll Viewport, normal focal length

[walkmesh]
quad = [[{XL:.0f},{ZB}],[{XR:.0f},{ZB}],[{XR:.0f},{ZF}],[{XL:.0f},{ZF}]]
character_offset = {CHAR_OFF:g}

[[layers]]
image = "surround.png"
z = 4000
size = [{RANGE_W}, {RANGE_H}]
[[layers]]
image = "floor.png"
z = 3000
size = [{RANGE_W}, {RANGE_H}]

[player]
spawn = [0, {SPAWN_Z}]
"""
(OUT / "scroll.field.toml").write_text(toml, encoding="utf-8", newline="\n")
print(f"wrote {OUT/'scroll.field.toml'}  (spawn at world (0,{SPAWN_Z}))")

# ---------- build via the kit into a temp mod ----------
tmp = Path(tempfile.mkdtemp(prefix="scrollbuild_"))
proj_obj = B.FieldProject.load(OUT / "scroll.field.toml")
info = B.build_mod([proj_obj], tmp, mod_name="FF9CustomMap")
FBG = info["fields"][0]
print("built:", FBG, "| dict:", info["dictionary"][0])

# ---------- inject BGCACTIVE(1,0,0) into Main_Init (entry 0, tag 0) of each language ----------
tmp_layout = ModLayout(tmp)
ENABLE = opcodes.encode(0x71, 1, 0, 0)   # 71 00 01 00 00
print("BGCACTIVE bytes:", ENABLE.hex())
for L in LANGS:
    p = tmp_layout.eb_path(L, f"EVT_{NAME}.eb.bytes")
    eb = p.read_bytes()
    s = EbScript.from_bytes(eb)
    f = s.entry(0).func_by_tag(0)
    eb2 = edit.insert_bytes(eb, f.abs_start, ENABLE)
    # verify the opcode is now present in Main_Init
    s2 = EbScript.from_bytes(eb2)
    f2 = s2.entry(0).func_by_tag(0)
    ops = [ins.op for ins in disasm.iter_code(eb2, f2.abs_start, f2.abs_end)]
    assert 0x71 in ops, f"{L}: BGCACTIVE not present after inject"
    p.write_bytes(eb2)
print(f"injected + verified BGCACTIVE in all {len(LANGS)} languages")

# ---------- verify the built scene carries the wide Range + scroll Viewport ----------
built_bgx = (tmp_layout.fieldmap_dir(FBG) / f"{FBG}.bgx").read_text(encoding="utf-8")
bc = C.parse_bgx_cameras_text(built_bgx)[0]
print(f"built .bgx camera: Range {bc.range}  Viewport {bc.viewport}  proj {bc.proj}")
assert bc.range == [RANGE_W, RANGE_H] and list(bc.viewport) == list(VIEWPORT) and bc.proj == proj

if "--dry" in sys.argv:
    print(f"\n[--dry] built + injected OK; temp mod at {tmp} (NOT deployed, NOT cleaned).")
    sys.exit(0)

# ---------- deploy into the live FF9CustomMap (reversible) ----------
GAME = find_game_path()
live = ModLayout(GAME / "FF9CustomMap")
BK = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backups")))
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

# back up DictionaryPatch + the 7 interior EVTs we touch
shutil.copyfile(live.dictionary_patch, BK / f"DictionaryPatch.txt.preSCROLL.{STAMP}")
for L in LANGS:
    shutil.copyfile(live.eb_path(L, "EVT_HUT_INT.eb.bytes"),
                    BK / f"{L}-EVT_HUT_INT.eb.bytes.preSCROLL.{STAMP}")

# copy SCROLL01 FieldMaps + EVTs into the live mod
shutil.rmtree(live.fieldmap_dir(FBG), ignore_errors=True)
shutil.copytree(tmp_layout.fieldmap_dir(FBG), live.fieldmap_dir(FBG))
for L in LANGS:
    live.ensure_dirs(FBG, langs=[L])
    shutil.copyfile(tmp_layout.eb_path(L, f"EVT_{NAME}.eb.bytes"),
                    live.eb_path(L, f"EVT_{NAME}.eb.bytes"))

# merge the 4003 DictionaryPatch line (keep the live 4000/4002 lines)
dp = live.dictionary_patch.read_text(encoding="utf-8").rstrip("\n").splitlines()
dp = [ln for ln in dp if not ln.split()[1:2] == [str(FID)]]   # drop any stale 4003 line
dp.append(info["dictionary"][0])
live.dictionary_patch.write_text("\n".join(dp) + "\n", encoding="utf-8", newline="\n")

# repoint the interior door: HUT_INT Field(4000) -> Field(4003), all langs (same-length 2-byte patch)
for L in LANGS:
    p = live.eb_path(L, "EVT_HUT_INT.eb.bytes")
    eb = p.read_bytes()
    s = EbScript.from_bytes(eb)
    patched = False
    for ent in s.entries:
        for fn in ent.funcs:
            for ins in disasm.iter_code(eb, fn.abs_start, fn.abs_end):
                if ins.op == 0x2B and ins.imm(0) == 4000:
                    argoff = (ins.end - ins.length) + 2          # opcode(1) + arg_flag(1)
                    eb = edit.patch_bytes(eb, argoff, struct.pack("<H", FID),
                                          expect=struct.pack("<H", 4000))
                    patched = True
    assert patched, f"{L}: no Field(4000) found in interior to repoint"
    p.write_bytes(eb)
print("deployed: SCROLL01 assets + DictionaryPatch 4003 line + interior door -> 4003")

# ---------- emit the revert script ----------
revert = f'''#!/usr/bin/env python3
"""Revert the SCROLL01 (field 4003) scroll spike: restore interior door + DictionaryPatch, remove SCROLL01."""
import sys, shutil
from pathlib import Path
sys.path.insert(0, r"{KIT}")
from ff9mapkit.config import find_game_path, ModLayout, LANGS
STAMP = "{STAMP}"
BK = Path(r"{BK}")
live = ModLayout(find_game_path() / "FF9CustomMap")
shutil.copyfile(BK / f"DictionaryPatch.txt.preSCROLL.{{STAMP}}", live.dictionary_patch)
for L in LANGS:
    shutil.copyfile(BK / f"{{L}}-EVT_HUT_INT.eb.bytes.preSCROLL.{{STAMP}}", live.eb_path(L, "EVT_HUT_INT.eb.bytes"))
shutil.rmtree(live.fieldmap_dir("{FBG}"), ignore_errors=True)
for L in LANGS:
    p = live.eb_path(L, "EVT_{NAME}.eb.bytes")
    if p.exists():
        p.unlink()
print("reverted: interior door + DictionaryPatch restored; SCROLL01 removed.")
'''
(OUT / "revert_scroll_test.py").write_text(revert, encoding="utf-8", newline="\n")
shutil.rmtree(tmp, ignore_errors=True)
print(f"\nrevert script: {OUT/'revert_scroll_test.py'}")
print("\n=== DEPLOYED. Reach it: Alexandria -> hut exterior -> interior DOOR -> SCROLL01 (4003). ===")
