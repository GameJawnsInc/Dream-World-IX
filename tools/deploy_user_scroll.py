#!/usr/bin/env python3
"""Take a Blender scroll export (camera.bgx + walkmesh.obj + my_room.field.toml) and:
  1. regenerate a correct WIDE paint guide + template for THAT exact camera+walkmesh
     (so the human can paint a real full-width background), and
  2. deploy the room to field 4003 NOW with a matched checkerboard floor over the user's own
     walkmesh, so they can walk it + see the scroll immediately.

Reversible (reverts SCROLLDEMO first, writes its own revert). Run:
    python tools/deploy_user_scroll.py <path-to-export-dir>
"""
import os, sys, struct, shutil, tempfile, datetime
from pathlib import Path

KIT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ff9mapkit"))
sys.path.insert(0, KIT)
from ff9mapkit.scene import cam as C, guide as G
from ff9mapkit import build as B
from ff9mapkit.config import find_game_path, ModLayout, LANGS
from ff9mapkit.eb import EbScript, edit, disasm
from PIL import Image, ImageDraw

if len(sys.argv) <= 1:
    sys.exit("usage: python tools/deploy_user_scroll.py <path-to-blender-scroll-export-dir>")
SRC = Path(sys.argv[1])
NAME, FID = "MY_ROOM", 4003
S = 4

cam = C.parse_bgx_cameras(str(SRC / "camera.bgx"))[0]
RW, RH = int(cam.range[0]), int(cam.range[1])
# read the user's walkmesh world corners (back edge first two, front edge last two)
verts = []
for ln in (SRC / "walkmesh.obj").read_text().splitlines():
    if ln.startswith("v "):
        _, x, y, z = ln.split()[:4]
        verts.append((float(x), float(z)))
xs = [v[0] for v in verts]; zs = [v[1] for v in verts]
X0, X1, ZB, ZF = min(xs), max(xs), max(zs), min(zs)     # back = larger z, front = smaller z
print(f"camera Range {RW}x{RH}, pitch {C.pitch_deg(cam):.1f}; walkmesh x[{X0:.0f}..{X1:.0f}] z[{ZF:.0f}..{ZB:.0f}]")

def cvpx(x, z):
    cx, cy = C.to_canvas((x, 0, z), cam)
    return (cx * S, cy * S)

# ---- checker floor matched to the user's own walkmesh, on the full wide canvas ----
img = Image.new("RGBA", (RW * S, RH * S), (0, 0, 0, 0))
dr = ImageDraw.Draw(img, "RGBA")
N = 12
gx = [X0 + (X1 - X0) * i / N for i in range(N + 1)]
gz = [ZF + (ZB - ZF) * j / N for j in range(N + 1)]
for j in range(N):
    for i in range(N):
        q = [cvpx(gx[i], gz[j]), cvpx(gx[i + 1], gz[j]), cvpx(gx[i + 1], gz[j + 1]), cvpx(gx[i], gz[j + 1])]
        dr.polygon(q, fill=((110, 150, 120, 255) if (i + j) % 2 == 0 else (60, 84, 70, 255)))
outline = [cvpx(X0, ZB), cvpx(X1, ZB), cvpx(X1, ZF), cvpx(X0, ZF)]
dr.line(outline + [outline[0]], fill=(255, 220, 90, 255), width=3 * S)
img.save(SRC / "_checker.png")
Image.new("RGBA", (RW * S, RH * S), (26, 28, 34, 255)).save(SRC / "_surround.png")

# ---- a correct WIDE paint guide + template for this camera (for the human to paint a real bg) ----
fr = G.frame_floor(cam, back_canvas_y=float(cam.range[1]) * 0.30, front_canvas_y=float(cam.range[1]) * 0.94,
                   half_width=int(round(max(abs(X0), abs(X1)))))
G.render_paint_guide(cam, fr, SRC / "paint_guide_WIDE.png", scale=S, nx=14, nz=5)
G.render_paint_template(cam, fr, SRC / "paint_template_WIDE.png", scale=S, nx=14, nz=6)
print(f"wrote WIDE paint guide/template ({RW*S}x{RH*S}) to {SRC} — paint art/back.png at that size")

# ---- assemble a build dir = the user's export + the checker layers ----
tmp = Path(tempfile.mkdtemp(prefix="userscroll_"))
for f in ("camera.bgx", "walkmesh.obj"):
    shutil.copyfile(SRC / f, tmp / f)
shutil.copyfile(SRC / "_surround.png", tmp / "_surround.png")
shutil.copyfile(SRC / "_checker.png", tmp / "_checker.png")
# rewrite the toml: keep the user's [field]/[camera]/[walkmesh]/[player]/npc/gateway, add layers
toml = (SRC / "my_room.field.toml").read_text(encoding="utf-8")
layers = ('[[layers]]\nimage = "_surround.png"\nz = 4000\n'
          '[[layers]]\nimage = "_checker.png"\nz = 3000\n')
# insert the layers right before [player] (or append)
if "[player]" in toml:
    toml = toml.replace("[player]", layers + "\n[player]", 1)
else:
    toml += "\n" + layers
(tmp / "room.field.toml").write_text(toml, encoding="utf-8", newline="\n")

info = B.build_mod([B.FieldProject.load(tmp / "room.field.toml")], tmp / "mod", mod_name="FF9CustomMap")
FBG = info["fields"][0]
tl = ModLayout(tmp / "mod")
eb0 = tl.eb_path("us", f"EVT_{NAME}.eb.bytes").read_bytes()
s0 = EbScript.from_bytes(eb0); f0 = s0.entry(0).func_by_tag(0)
assert 0x71 in [i.op for i in disasm.iter_code(eb0, f0.abs_start, f0.abs_end)], "no BGCACTIVE"
print("built:", FBG, "| BGCACTIVE ok")

# ---- revert any prior 4003 test, then deploy reversibly ----
live = ModLayout(find_game_path() / "FF9CustomMap")
for r in (Path(KIT).parents[0] / "tools" / "scroll_out" / "revert_scroll_demo.py",):
    if r.exists():
        os.system(f'py "{r}"')
        break
BK = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backups")))
STAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
shutil.copyfile(live.dictionary_patch, BK / f"DictionaryPatch.txt.preUSERSCROLL.{STAMP}")
for L in LANGS:
    shutil.copyfile(live.eb_path(L, "EVT_HUT_INT.eb.bytes"),
                    BK / f"{L}-EVT_HUT_INT.eb.bytes.preUSERSCROLL.{STAMP}")
shutil.rmtree(live.fieldmap_dir(FBG), ignore_errors=True)
shutil.copytree(tl.fieldmap_dir(FBG), live.fieldmap_dir(FBG))
for L in LANGS:
    live.ensure_dirs(FBG, langs=[L])
    shutil.copyfile(tl.eb_path(L, f"EVT_{NAME}.eb.bytes"), live.eb_path(L, f"EVT_{NAME}.eb.bytes"))
dp = [ln for ln in live.dictionary_patch.read_text(encoding="utf-8").splitlines()
      if ln.strip() and ln.split()[1:2] != [str(FID)]]
dp.append(info["dictionary"][0])
live.dictionary_patch.write_text("\n".join(dp) + "\n", encoding="utf-8", newline="\n")
for L in LANGS:
    p = live.eb_path(L, "EVT_HUT_INT.eb.bytes"); eb = p.read_bytes(); s = EbScript.from_bytes(eb); ok = False
    for ent in s.entries:
        for fn in ent.funcs:
            for ins in disasm.iter_code(eb, fn.abs_start, fn.abs_end):
                if ins.op == 0x2B and ins.imm(0) != FID:
                    eb = edit.patch_bytes(eb, (ins.end - ins.length) + 2, struct.pack("<H", FID),
                                          expect=struct.pack("<H", ins.imm(0))); ok = True
    assert ok, f"{L}: no interior Field() to repoint"
    p.write_bytes(eb)
print("deployed MY_ROOM (your walkmesh + matched checker) -> field 4003; interior door -> 4003")

revert = f'''#!/usr/bin/env python3
import sys, shutil
from pathlib import Path
sys.path.insert(0, r"{KIT}")
from ff9mapkit.config import find_game_path, ModLayout, LANGS
STAMP="{STAMP}"; BK=Path(r"{BK}"); live=ModLayout(find_game_path()/"FF9CustomMap")
shutil.copyfile(BK/f"DictionaryPatch.txt.preUSERSCROLL.{{STAMP}}", live.dictionary_patch)
for L in LANGS:
    shutil.copyfile(BK/f"{{L}}-EVT_HUT_INT.eb.bytes.preUSERSCROLL.{{STAMP}}", live.eb_path(L,"EVT_HUT_INT.eb.bytes"))
shutil.rmtree(live.fieldmap_dir("{FBG}"), ignore_errors=True)
for L in LANGS:
    p=live.eb_path(L,"EVT_{NAME}.eb.bytes")
    if p.exists(): p.unlink()
print("reverted: interior door + DictionaryPatch restored; MY_ROOM removed.")
'''
out = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "scroll_out")))
out.mkdir(exist_ok=True)
(out / "revert_user_scroll.py").write_text(revert, encoding="utf-8", newline="\n")
shutil.rmtree(tmp, ignore_errors=True)
print(f"revert: {out/'revert_user_scroll.py'}")
print("\n=== Reach it: Alexandria -> hut exterior -> interior DOOR -> MY_ROOM (4003). ===")
