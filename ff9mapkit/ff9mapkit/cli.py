"""``ff9mapkit`` command-line entry point.

Subcommands are wired up incrementally as the library lands:
    doctor    - show resolved game/mod paths and sanity-check the install   (Phase 0)
    disasm    - disassemble a .eb field script                              (Phase 1)
    camera    - read/synthesize/round-trip a .bgx camera                    (Phase 2)
    walkmesh  - convert an .obj walkmesh to .bgi / fix neighbor links       (Phase 2)
    guide     - emit a paint guide + walkmesh-in-frame for a camera spec    (Phase 2)
    build     - compile a field.toml into a Memoria mod folder              (Phase 4)
    new       - scaffold a new field project directory                      (Phase 5)
    pack      - package a built mod for distribution                        (Phase 5)

Anything not yet implemented prints a clear "coming in Phase N" message rather than failing
with an import error, so the installed console script is always runnable.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .config import ConfigError, ModLayout, find_game_path, find_mod_root


def _cmd_doctor(args: argparse.Namespace) -> int:
    try:
        game = find_game_path(args.game)
    except ConfigError as e:
        print(str(e), file=sys.stderr)
        return 2
    mod_root = find_mod_root(game, args.mod_folder)
    layout = ModLayout(mod_root)
    print(f"ff9mapkit {__version__}")
    print(f"game install : {game}")
    print(f"  exists     : {game.is_dir()}")
    launcher = game / "FF9_Launcher.exe"
    print(f"  launcher   : {'found' if launcher.is_file() else 'MISSING'} ({launcher.name})")
    print(f"mod root     : {mod_root}")
    print(f"  exists     : {mod_root.is_dir()}")
    print(f"  FieldMaps  : {layout.fieldmaps_dir}")
    print(f"  eb/field   : {layout.eventbinary_field_dir}")
    print(f"  dict patch : {layout.dictionary_patch} ({'present' if layout.dictionary_patch.is_file() else 'absent'})")
    return 0


def _cmd_disasm(args: argparse.Namespace) -> int:
    from .eb import EbScript

    eb = EbScript.from_file(args.file)
    print(f"=== {args.file}  size={len(eb.data)} entries={eb.entry_count} ===")
    for e in eb.entries:
        if e.empty:
            if args.all:
                print(f"\nENTRY {e.index}: (empty, off={e.off})")
            continue
        if args.entry is not None and e.index != args.entry:
            continue
        print(f"\nENTRY {e.index}: off={e.off} sz={e.size} type={e.type} "
              f"funcs={[f.tag for f in e.funcs]}  [{e.abs_start}..{e.abs_end}]")
        for f in e.funcs:
            print(f"  --- func{f.index} tag={f.tag} [{f.abs_start}..{f.abs_end}]")
            for ins in eb.instrs(f):
                print(f"    {ins}")
    return 0


def _cmd_camera(args: argparse.Namespace) -> int:
    from .scene import bgx, cam
    scene = bgx.BgxScene.from_file(args.bgx)
    if not scene.cameras:
        print("no CAMERA block in scene", file=sys.stderr)
        return 2
    c = scene.cameras[0]
    d = cam.decompose(c)
    print(f"camera: proj(H)={c.proj} pos={c.t} range={c.range} fovX={d['fov_x_deg']:.2f} "
          f"k={d['k']:.5f} C={tuple(round(x) for x in d['C'])}")
    if args.regen:
        r, t = cam.synth_r_t(d["C"], d["R_ortho"], c.proj, k=d["k"])
        c.r, c.t = r, t
        scene.set_camera(c)
        with open(args.regen, "w", newline="\n", encoding="utf-8") as fh:
            fh.write(scene.to_text())
        print(f"regenerated camera -> {args.regen}")
    return 0


def _cmd_walkmesh(args: argparse.Namespace) -> int:
    from .scene import bgi
    if args.action == "obj":
        out = bgi.obj_to_bgi(args.input)
        with open(args.output, "wb") as fh:
            fh.write(out)
        m = bgi.BgiWalkmesh.from_bytes(out)
        print(f"obj -> .bgi: {len(m.tris)} tris, {len(m.verts)} verts, {len(out)} bytes -> {args.output}")
    elif args.action == "fix":
        m = bgi.BgiWalkmesh.from_file(args.input)
        m.rebuild_neighbors()
        out = m.to_bytes()
        with open(args.output or args.input, "wb") as fh:
            fh.write(out)
        print(f"rebuilt neighbor links for {len(m.tris)} tris -> {args.output or args.input}")
    return 0


def _cmd_guide(args: argparse.Namespace) -> int:
    from .scene import bgi, cam, guide
    g = guide.make_camera(args.pitch, args.distance, fov_x_deg=args.fov)
    fr = guide.frame_floor(g, back_canvas_y=args.back, front_canvas_y=args.front)
    print(f"camera pitch={args.pitch} fovX={cam.decompose(g)['fov_x_deg']:.1f} dist={args.distance}")
    print(f"floor world z [{fr.zf}..{fr.zb}] half-width {fr.half_width}")
    for nm, w, cv in zip(("BL", "BR", "FR", "FL"), fr.corners_world, fr.corners_canvas):
        print(f"  {nm}: world {w} -> canvas px {cv}")
    print(f"walkmesh corners (x,z): {guide.walkmesh_corners(fr)}")
    if args.png:
        guide.render_paint_guide(g, fr, args.png)
        print(f"paint guide -> {args.png}")
    return 0


def _not_yet(phase: str):
    def _run(args: argparse.Namespace) -> int:
        print(f"'{args._cmd}' is not implemented yet (coming in {phase}).", file=sys.stderr)
        return 3
    return _run


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ff9mapkit", description="Author custom FF9 field maps.")
    p.add_argument("--version", action="version", version=f"ff9mapkit {__version__}")
    p.add_argument("--game", default=None, help="path to the FF9 install (overrides $FF9_GAME_PATH and config)")
    p.add_argument("--mod-folder", default="FF9CustomMap", help="mod folder name inside the install")
    sub = p.add_subparsers(dest="_cmd", required=True)

    d = sub.add_parser("doctor", help="show resolved paths and sanity-check the install")
    d.set_defaults(func=_cmd_doctor)

    ds = sub.add_parser("disasm", help="disassemble a .eb field script")
    ds.add_argument("file", help="path to a .eb / .eb.bytes file")
    ds.add_argument("-e", "--entry", type=int, default=None, help="only this entry index")
    ds.add_argument("-a", "--all", action="store_true", help="also list empty entry slots")
    ds.set_defaults(func=_cmd_disasm)

    cm = sub.add_parser("camera", help="inspect / regenerate a .bgx camera")
    cm.add_argument("bgx", help="path to a .bgx scene")
    cm.add_argument("--regen", metavar="OUT.bgx", help="rewrite with a re-synthesized camera (round-trip check)")
    cm.set_defaults(func=_cmd_camera)

    wm = sub.add_parser("walkmesh", help="convert/repair a walkmesh")
    wm.add_argument("action", choices=["obj", "fix"], help="obj: .obj->.bgi ; fix: rebuild neighbor links")
    wm.add_argument("input", help="input .obj (obj) or .bgi (fix)")
    wm.add_argument("output", nargs="?", help="output path (.bgi); for fix defaults to input")
    wm.set_defaults(func=_cmd_walkmesh)

    gd = sub.add_parser("guide", help="author a camera + emit a paint guide for a flat floor")
    gd.add_argument("--pitch", type=float, required=True, help="downward pitch in degrees")
    gd.add_argument("--distance", type=float, default=4500, help="camera distance from origin")
    gd.add_argument("--fov", type=float, default=42.2, help="horizontal FOV in degrees")
    gd.add_argument("--back", type=float, default=205, help="canvas Y of the floor back edge")
    gd.add_argument("--front", type=float, default=432, help="canvas Y of the floor front edge")
    gd.add_argument("--png", help="write a checkerboard paint-guide PNG here")
    gd.set_defaults(func=_cmd_guide)

    for name, phase in (("build", "Phase 4"), ("new", "Phase 5"), ("pack", "Phase 5")):
        s = sub.add_parser(name, help=f"(coming in {phase})")
        s.set_defaults(func=_not_yet(phase))

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
