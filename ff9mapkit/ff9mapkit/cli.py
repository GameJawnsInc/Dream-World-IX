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
    import    - fork a real FF9 field (BG-borrow, or --editable custom scene) (Tier 3)
    list-fields - list the real FF9 fields available to import              (Tier 3)

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
          f"k={d['k']:.5f} C={tuple(round(x) for x in d['C'])} pitch={cam.pitch_deg(c):.1f}")
    w = cam.pitch_warning(cam.pitch_deg(c))
    if w:
        print(f"warning: {w}", file=sys.stderr)
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
    if args.from_bgx:                              # use an existing camera (e.g. the Blender export)
        cams = cam.parse_bgx_cameras(args.from_bgx)
        if not cams:
            print(f"no CAMERA in {args.from_bgx}", file=sys.stderr)
            return 2
        g = cams[0]
        pitch = cam.pitch_deg(g)
    else:                                          # author a camera from pitch/distance/fov
        g = guide.make_camera(args.pitch, args.distance, fov_x_deg=args.fov)
        pitch = args.pitch
    try:
        fr = guide.frame_floor(g, back_canvas_y=args.back, front_canvas_y=args.front)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    print(f"camera pitch={pitch:.1f} fovX={cam.decompose(g)['fov_x_deg']:.1f}")
    w = cam.pitch_warning(pitch)
    if w:
        print(f"warning: {w}", file=sys.stderr)
    print(f"floor world z [{fr.zf}..{fr.zb}] half-width {fr.half_width}")
    for nm, wld, cv in zip(("BL", "BR", "FR", "FL"), fr.corners_world, fr.corners_canvas):
        print(f"  {nm}: world {wld} -> canvas px {cv}")
    print(f"walkmesh corners (x,z): {guide.walkmesh_corners(fr)}")
    if args.png:
        if args.template:
            wpx, hpx = guide.render_paint_template(g, fr, args.png)
            print(f"paint template ({wpx}x{hpx}, transparent - paint UNDER it) -> {args.png}")
        else:
            guide.render_paint_guide(g, fr, args.png)
            print(f"paint guide (checkerboard) -> {args.png}")
    return 0


def _cmd_build(args: argparse.Namespace) -> int:
    from pathlib import Path
    from .build import BuildError, FieldProject, build_mod
    try:
        projects = [FieldProject.load(p) for p in args.field]
    except (OSError, ValueError) as e:
        print(f"failed to load project: {e}", file=sys.stderr)
        return 2
    out = Path(args.out)
    try:
        info = build_mod(projects, out, mod_name=args.mod_name, author=args.author,
                         description=args.description)
    except (BuildError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"built mod '{args.mod_name}' -> {info['root']}")
    for line in info["dictionary"]:
        print(f"  {line}")
    for w in info.get("warnings", []):
        print(f"warning: {w}", file=sys.stderr)
    print("To install: copy that folder into the game install (next to FF9_Launcher.exe), or "
          "build with --out pointing at the game's mod folder.")
    return 0


def _cmd_new(args: argparse.Namespace) -> int:
    from .pack import new_project, suggest_base
    proj = new_project(args.name, args.dest, field_id=args.id, area=args.area, pitch=args.pitch)
    fid = args.id if args.id is not None else suggest_base(args.name)
    print(f"scaffolded {proj}  (suggested field id {fid}, area {args.area})")
    print(f"  edit {proj}/{args.name.lower()}.field.toml, add art, then: ff9mapkit build "
          f"{proj}/{args.name.lower()}.field.toml")
    return 0


def _cmd_pack(args: argparse.Namespace) -> int:
    from pathlib import Path
    from .pack import pack_mod
    out = args.out or (Path(args.mod_root).resolve().name + ".zip")
    try:
        z = pack_mod(args.mod_root, out)
    except FileNotFoundError as e:
        print(f"mod folder not found: {e}", file=sys.stderr)
        return 2
    print(f"packed {args.mod_root} -> {z}")
    return 0


def _cmd_import(args: argparse.Namespace) -> int:
    from pathlib import Path
    from . import extract
    try:
        if args.editable:
            meta, toml = extract.write_editable_project(
                args.field, Path(args.out), name=args.name, field_id=args.id, game=args.game)
        else:
            meta, toml = extract.write_field_project(
                args.field, Path(args.out), name=args.name, field_id=args.id,
                game=args.game, want_atlas=args.atlas)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    cm = meta["camera"]
    print(f"imported {meta['field']}  (area {meta['area']}, mapid {meta['mapid']})")
    if args.editable:
        nb = meta.get("blend_layers", 0)
        print(f"  mode   : EDITABLE custom scene ({meta['layers']} art layers"
              f"{f', {nb} light/shadow' if nb else ''})")
    else:
        print("  mode   : BG-borrow (reuses the real art as-is)")
    print(f"  camera : pitch {cm['pitch_deg']} fov {cm['fov_deg']} range {cm['range']}"
          f"{'  SCROLLING' if meta['scrolling'] else ''}")
    print(f"  spawn  : {meta['player_start']}   walkmesh x{meta['walkmesh_bounds']['x']} z{meta['walkmesh_bounds']['z']}")
    print(f"  wrote  : {toml}")
    if args.editable:
        print(f"Next: repaint any layer_*.png / reshape walkmesh.obj / add content, then: ff9mapkit build {toml}")
    else:
        print(f"Next: edit it (add [[npc]]/[[gateway]]/dialogue), then: ff9mapkit build {toml}")
    return 0


def _cmd_list_fields(args: argparse.Namespace) -> int:
    from . import extract
    try:
        rows = extract.list_fields(args.pattern, game=args.game)
    except (RuntimeError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 2
    for folder, area, mapid in rows:
        print(f"  area {area:>2}  {mapid:<28}  ({folder})")
    print(f"{len(rows)} field(s)")
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

    gd = sub.add_parser("guide", help="emit a paint guide/template for a flat floor")
    gd.add_argument("--from-bgx", help="use an existing camera .bgx (e.g. the Blender export) "
                                       "instead of --pitch/--distance/--fov")
    gd.add_argument("--pitch", type=float, default=48.0, help="downward pitch in degrees (if not --from-bgx)")
    gd.add_argument("--distance", type=float, default=4500, help="camera distance from origin")
    gd.add_argument("--fov", type=float, default=42.2, help="horizontal FOV in degrees")
    gd.add_argument("--back", type=float, default=205, help="canvas Y of the floor back edge")
    gd.add_argument("--front", type=float, default=432, help="canvas Y of the floor front edge")
    gd.add_argument("--png", help="write a PNG here (checkerboard guide, or template with --template)")
    gd.add_argument("--template", action="store_true",
                    help="write a TRANSPARENT trace-over paint template (paint your room under it)")
    gd.set_defaults(func=_cmd_guide)

    bd = sub.add_parser("build", help="compile field.toml project(s) into a Memoria mod")
    bd.add_argument("field", nargs="+", help="one or more field.toml files")
    bd.add_argument("--out", default="dist", help="output mod folder (default: ./dist)")
    bd.add_argument("--mod-name", default="FF9CustomMap", help="mod name / InstallationPath")
    bd.add_argument("--author", default="", help="mod author")
    bd.add_argument("--description", default="", help="mod description")
    bd.set_defaults(func=_cmd_build)

    nw = sub.add_parser("new", help="scaffold a new field project directory")
    nw.add_argument("name", help="field name (e.g. MY_ROOM)")
    nw.add_argument("--dest", default=".", help="where to create the project dir")
    nw.add_argument("--id", type=int, default=None, help="custom field id (default: suggested)")
    nw.add_argument("--area", type=int, default=11, help="area id (>= 10)")
    nw.add_argument("--pitch", type=float, default=48.0, help="camera pitch for the template")
    nw.set_defaults(func=_cmd_new)

    pk = sub.add_parser("pack", help="zip a built mod for distribution")
    pk.add_argument("mod_root", help="path to a built mod folder")
    pk.add_argument("--out", default=None, help="output .zip (default: <modname>.zip)")
    pk.set_defaults(func=_cmd_pack)

    im = sub.add_parser("import", help="fork a REAL FF9 field into an editable field.toml (needs UnityPy)")
    im.add_argument("field", help="field name: full FBG, bare mapid, or a unique substring (e.g. grgr_map420)")
    im.add_argument("--out", default=".", help="project dir to write into (default: .)")
    im.add_argument("--name", default=None, help="custom field/script id (default: <MAPID-first-token>_FORK/_EDIT)")
    im.add_argument("--id", type=int, default=4003, help="custom field id (default: 4003)")
    im.add_argument("--editable", action="store_true",
                    help="fork as a full editable CUSTOM SCENE (re-exported walkmesh + the real art split "
                         "into one repaintable layer per depth, occlusion preserved) instead of BG-borrow; "
                         "needs the field exported in-game once via Memoria.ini [Export] Field=1")
    im.add_argument("--atlas", action="store_true", help="also extract the raw atlas.png (BG-borrow mode only)")
    im.set_defaults(func=_cmd_import)

    lf = sub.add_parser("list-fields", help="list real FF9 fields available to import (needs UnityPy)")
    lf.add_argument("pattern", nargs="?", default=None, help="substring filter (e.g. alex, treno, grgr)")
    lf.set_defaults(func=_cmd_list_fields)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
