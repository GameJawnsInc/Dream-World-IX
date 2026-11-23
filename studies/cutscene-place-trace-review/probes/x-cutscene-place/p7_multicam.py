import sys, shutil, re
from pathlib import Path
sys.path.insert(0, r"<SCRATCH>/review/x-cutscene-place")
import h
from ff9mapkit import build
from ff9mapkit.workspace import placedoc as PD
from ff9mapkit.scene import bgi

src = h.OUT / "work" / "novel" / "A"
for wm in ("obj", "auto"):
    dst = h.OUT / "work" / f"multicam_{wm}"
    shutil.rmtree(dst, ignore_errors=True)
    shutil.copytree(src, dst)
    t = dst / "a.field.toml"
    txt = t.read_text(encoding="utf-8")
    cams = ('[[camera]]\nentry_settle = "auto"\npitch = 48.0\ndistance = 4482\nfov = 42.2\n\n'
            '[[camera]]\npitch = 30.0\ndistance = 3000\nfov = 42.2\nyaw = 35\n')
    txt = re.sub(r"\[camera\]\n(?:[^\[\n].*\n)*", cams + "\n", txt, count=1)
    if wm == "auto":
        txt = txt.replace('[walkmesh]\nobj = "walkmesh.obj"', '[walkmesh]\nauto = true')
    t.write_text(txt, encoding="utf-8")
    proj = build.FieldProject.load(str(t))
    cs = build.resolve_cameras(proj)
    built = bgi.BgiWalkmesh.from_bytes(build.resolve_walkmesh(proj, build.resolve_camera(proj)))
    import ff9mapkit.imagefield as IF
    btris, _ = IF.mesh_world_tris(built)
    def ext(tris):
        xs = [v[0] for tr in tris for v in tr]; zs = [v[2] for tr in tris for v in tr]
        return (round(min(xs)), round(max(xs)), round(min(zs)), round(max(zs)))
    print(f"[{wm}] n_cams={len(cs)}  BUILD mesh extent {ext(btris)}")
    for ci in range(len(cs)):
        try:
            b = PD.build_surface_from_project(t, ci)
            print(f"   Place cam {ci}: extent {ext(b['tris'])}  same as build: {ext(b['tris']) == ext(btris)}")
        except Exception as e:
            print(f"   Place cam {ci}: ERROR {type(e).__name__}: {e}")
