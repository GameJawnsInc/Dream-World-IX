"""``ff9mapkit`` command-line entry point.

Subcommands are wired up incrementally as the library lands:
    doctor    - show resolved game/mod paths and sanity-check the install   (Phase 0)
    disasm    - disassemble a .eb field script                              (Phase 1)
    camera    - read/synthesize/round-trip a .bgx camera                    (Phase 2)
    walkmesh  - convert .obj->.bgi / fix neighbor links / verify a walkmesh  (Phase 2)
    guide     - emit a paint guide + walkmesh-in-frame for a camera spec    (Phase 2)
    lint      - check a field.toml's logic (story flags / dup names / placement)  (P2)
    build     - compile a field.toml into a Memoria mod folder              (Phase 4)
    new       - scaffold a new field project directory                      (Phase 5)
    pack      - package a built mod for distribution                        (Phase 5)
    import    - fork a real FF9 field (BG-borrow, or --editable custom scene) (Tier 3)
    list-fields - list the real FF9 fields available to import              (Tier 3)
    battle-import - fork a real FF9 battle background (BBG) into an editable battle.toml (needs UnityPy)
    battle-build  - compile a battle.toml into a Memoria mod (custom 3D battle map; stock engine)
    battle-list   - list the real FF9 battle backgrounds available to fork
    dialogue  - view a field.toml's authored dialogue + how each line wraps on screen
    dialogue-import - read a REAL FF9 field's dialogue (or a built mod's) -- 'NPC -> text'
    animations/items - browse the cutscene-gesture / item catalogs by name
    models/scenes/catalog - the Info Hub: browse models (+ their animations), battle scenes, or
                            search every reference catalog by name
    extract-templates - regenerate base assets from the user's own FF9 install (no game data shipped)

Anything not yet implemented prints a clear "coming in Phase N" message rather than failing
with an import error, so the installed console script is always runnable.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .config import ConfigError, ModLayout, find_game_path, find_mod_root
from .flags import FIRST_SAFE_FLAG     # the census-grounded safe campaign flag floor (clear of real-FF9 flags)


def _has_unitypy() -> bool:
    """True if UnityPy imports (the optional dep used by `import` / `list-fields`)."""
    try:
        import UnityPy  # noqa: F401
        return True
    except ImportError:
        return False


def _cmd_doctor(args: argparse.Namespace) -> int:
    # Environment first, so these show even if the game path isn't configured yet.
    print(f"ff9mapkit {__version__}")
    print(f"  UnityPy    : {'present' if _has_unitypy() else 'absent (only needed for import / list-fields)'}")
    try:
        game = find_game_path(args.game)
    except ConfigError as e:
        print(str(e), file=sys.stderr)
        return 2
    mod_root = find_mod_root(game, args.mod_folder)
    layout = ModLayout(mod_root)
    print(f"game install : {game}")
    print(f"  exists     : {game.is_dir()}")
    launcher = game / "FF9_Launcher.exe"
    print(f"  launcher   : {'found' if launcher.is_file() else 'MISSING'} ({launcher.name})")
    streaming = game / "StreamingAssets"
    print(f"  assets     : {'found' if streaming.is_dir() else 'MISSING'} (StreamingAssets)")
    print(f"mod root     : {mod_root}")
    print(f"  exists     : {mod_root.is_dir()}")
    print(f"  FieldMaps  : {layout.fieldmaps_dir}")
    print(f"  eb/field   : {layout.eventbinary_field_dir}")
    print(f"  dict patch : {layout.dictionary_patch} ({'present' if layout.dictionary_patch.is_file() else 'absent'})")
    from . import provision
    print(f"templates    : {'extracted' if provision.templates_present() else 'NOT extracted -- run: ff9mapkit extract-templates'}")
    return 0


def _cmd_extract_templates(args: argparse.Namespace) -> int:
    """Regenerate the kit's base assets (blank field, exit-region template, test fixtures) from the
    user's own FF9 install -- the bring-your-own-install step that lets the repo ship no game data."""
    from . import provision
    if not _has_unitypy():
        print("extract-templates needs UnityPy (reads FF9's p0data assetbundles). Install it:\n"
              "    py -m pip install UnityPy", file=sys.stderr)
        return 2
    try:
        find_game_path(args.game)            # clear error if the install can't be resolved
    except ConfigError as e:
        print(str(e), file=sys.stderr)
        return 2
    print("Regenerating base assets from your FF9 install (no game data is shipped with ff9mapkit):")
    try:
        rep = provision.extract_templates(game=args.game, fixtures=not args.no_fixtures, verbose=True)
    except Exception as e:
        print(f"\nextract-templates failed: {e}", file=sys.stderr)
        return 1
    print(f"\nOK -- {len(rep['verified'])} assets regenerated + verified against the manifest.")
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
    elif args.action == "verify":
        return _walkmesh_verify(args.input)
    return 0


def _walkmesh_verify(path: str) -> int:
    """Run the walkmesh + content checks standalone (no build). Accepts a .field.toml (full checks:
    geometry, content placement, layer art) or a raw .bgi (geometry only). Exit 1 if any warning."""
    from .scene import bgi
    if str(path).endswith(".toml"):
        from .build import FieldProject, verify_walkmesh
        rep = verify_walkmesh(FieldProject.load(path))
        print(f"walkmesh verify: {path}  [{rep.get('source', '?')}]")
    else:
        from .build import _walkmesh_stats
        rep = {**_walkmesh_stats(bgi.BgiWalkmesh.from_file(path)), "warnings": []}
        print(f"walkmesh verify: {path}")
    if rep.get("floors") is not None:
        line = f"  floors {rep['floors']}  |  walk-reachable {rep['reachable']}"
        if rep["stranded"]:
            line += f"  |  NOT reachable on foot: {rep['stranded']}"
        print(line)
        extra = f", {len(rep['degenerate'])} degenerate tri(s)" if rep["degenerate"] else ""
        print(f"  {rep['tris']} tris, {rep['verts']} verts, {rep['seams']} cross-floor seam(s){extra}")
        if rep.get("bounds"):
            b = rep["bounds"]
            print(f"  bounds  x{b['x']}  z{b['z']}")
    warns = rep.get("warnings", [])
    if warns:
        print(f"  {len(warns)} warning(s):")
        for m in warns:
            print(f"    ! {m}")
        return 1
    print("  OK -- no warnings.")
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


def _cmd_lint(args: argparse.Namespace) -> int:
    """Check a field.toml WITHOUT building -- ONE pass over every offline validator: schema errors
    (validate), story/flag logic + dialogue overflow + dup names (lint_logic), reserved flag-band use
    (lint_flag_bands), walkmesh geometry + content placement + layer art + cutscene movement
    (verify_walkmesh), and camera pitch range. Warnings are grouped by [section]. Exits 1 if anything is
    reported, so it's scriptable. Merges a sibling scene.toml first."""
    from .build import FieldProject, lint_all
    try:
        proj = FieldProject.load(args.field)
    except (OSError, ValueError) as e:
        print(f"failed to load: {e}", file=sys.stderr)
        return 2
    rep = lint_all(proj)
    print(f"lint: {args.field}  [{rep.source}]")
    for p in rep.errors:
        print(f"  ERROR  {p}")
    for tag, items in (("logic", rep.logic), ("flags", rep.flags),
                       ("placement", rep.placement), ("camera", rep.camera)):
        for w in items:
            print(f"  warn  [{tag}] {w}")
    if rep.ok:
        print("  OK -- no problems.")
        return 0
    print(f"  {len(rep.errors)} error(s), {len(rep.warnings)} warning(s)")
    return 1


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
        gpf = getattr(args, "graft_player_funcs", False)
        ct = getattr(args, "carry_text", False)
        sm = getattr(args, "save_moogle", False)
        if ct or sm:
            gpf = True             # text carry / save-moogle ride on the graft (the carried objects/funcs must exist)
        # #4 (FORK_FIDELITY.md): BG-borrow black-screens area<10 -- the engine builds 'FBG_N<area>' and reads
        # exactly 2 chars, so single-digit areas never resolve. The native path ships its own art at a remapped
        # area>=10 (seam-free + lit), so auto-route the default (borrow) path to native there -- this unblocks
        # forking the early-game fields (Alexandria area1, Cargo Ship area0) with a plain `import`.
        auto_native_area = None
        if not args.native and not args.editable:
            try:
                _folder, _ = extract.resolve_field(args.field, args.game)
                _area, _ = extract.parse_fbg_folder(_folder)
                if _area < extract.MIN_CUSTOM_AREA:
                    args.native = True
                    auto_native_area = _area
            except (RuntimeError, FileNotFoundError, ValueError):
                pass               # can't resolve area offline -> let the normal dispatch surface any error
        if args.native:
            meta, toml = extract.write_native_project(
                args.field, Path(args.out), name=args.name, field_id=args.id, game=args.game,
                graft_player_funcs=gpf, carry_text=ct, graft_savepoint=sm)
        elif args.editable:
            meta, toml = extract.write_editable_project(
                args.field, Path(args.out), name=args.name, field_id=args.id, game=args.game,
                graft_player_funcs=gpf, carry_text=ct, graft_savepoint=sm)
        else:
            meta, toml = extract.write_field_project(
                args.field, Path(args.out), name=args.name, field_id=args.id,
                game=args.game, want_atlas=args.atlas, graft_player_funcs=gpf, carry_text=ct, graft_savepoint=sm)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    cm = meta["camera"]
    print(f"imported {meta['field']}  (area {meta['area']}, mapid {meta['mapid']})")
    if args.native:
        print("  mode   : NATIVE custom scene (atlas.png + .bgs, NO .bgx -- seamless per-tile render, Moguri-style)")
        print(f"  atlas  : {meta.get('atlas_source', '?')}")
        if auto_native_area is not None:
            print(f"  note   : auto-selected --native (source area {auto_native_area} < 10 black-screens via BG-borrow)")
    elif args.editable:
        nb = meta.get("blend_layers", 0)
        print(f"  mode   : EDITABLE custom scene ({meta['layers']} art layers"
              f"{f', {nb} light/shadow' if nb else ''})")
    else:
        print("  mode   : BG-borrow (reuses the real art as-is)")
    print(f"  camera : pitch {cm['pitch_deg']} fov {cm['fov_deg']} range {cm['range']}"
          f"{'  SCROLLING' if meta['scrolling'] else ''}")
    print(f"  spawn  : {meta['player_start']}   walkmesh x{meta['walkmesh_bounds']['x']} z{meta['walkmesh_bounds']['z']}")
    ic = meta.get("imported_content")
    if ic:
        bits = []
        if ic["gateways"]:
            bits.append(f"{ic['gateways']} gateway(s)")
        if ic["encounter"]:
            bits.append("encounter")
        if ic["music"] is not None:
            bits.append(f"BGM song {ic['music']}")
        if ic["control_direction"] is not None:
            bits.append(f"movement dir {ic['control_direction']}")
        if ic.get("ladders"):
            bits.append(f"{ic['ladders']} ladder(s)")
        if ic.get("jumps"):
            bits.append(f"{ic['jumps']} jump(s)")
        if ic.get("objects"):
            bits.append(f"{ic['objects']} object(s) carried")
        if ic.get("player_funcs"):
            bits.append(f"{ic['player_funcs']} player-func(s) grafted (interactions)")
        if ic.get("carry_text"):
            bits.append(f"{ic['carry_text']} dialogue line(s) carried verbatim")
        if ic.get("save_moogle"):
            bits.append("a faithful SAVE MOOGLE (pops out of the barrel + saves)")
        print(f"  content: {', '.join(bits) if bits else 'none found in the source script'}"
              + ("   (gateways point at REAL fields -- retarget them)" if ic["gateways"] else ""))
        if ic.get("spawn_flash_fixed"):
            print("  note   : the save Moogle's spawn pose was normalised to its rest pose (no load flash on a fork)")
        if ic.get("spawn_flash"):
            print(f"  warning: {ic['spawn_flash']} carried object(s) spawn at a different pose than they rest -- they "
                  "may visibly snap to rest on a fork (the source field's entrance fade hides it). (docs/SAVEPOINT.md)")
    if args.dialogue:
        from . import dialogue as DLG
        try:
            lines = DLG.read_field_dialogue(args.field, lang="us", game=args.game)
            n = sum(1 for ln in DLG.present(lines) if ln.source == "npc" and ln.text)
            if n:
                with open(toml, "a", encoding="utf-8") as fh:
                    fh.write("\n" + DLG.npc_stub_toml(lines, field_ref=args.field))
                print(f"  dialogue: appended {n} editable [[npc]] stub(s) (commented) -- uncomment + re-author them")
            else:
                print("  dialogue: no NPC dialogue found in this field")
        except (RuntimeError, FileNotFoundError, ValueError) as e:
            print(f"  dialogue: skipped ({e})", file=sys.stderr)
    print(f"  wrote  : {toml}")
    if args.native:
        print(f"Next: add content (retarget imported gateways, add [[npc]]/dialogue), then: ff9mapkit build {toml}")
    elif args.editable:
        print(f"Next: repaint any layer_*.png / reshape walkmesh.obj / add content, then: ff9mapkit build {toml}")
    else:
        print(f"Next: edit it (retarget imported gateways, add [[npc]]/dialogue), then: ff9mapkit build {toml}")
    return 0


def _chain_label_fn(game=None):
    """id -> display name. Prefers reference/field-manifest.tsv (nice names like 'Ice Cavern/Entrance');
    falls back to the FBG mapid (always available, provenance-clean) so it works with no reference dir."""
    from pathlib import Path
    from . import extract
    names: dict = {}
    for cand in (Path(__file__).resolve().parents[2] / "reference" / "field-manifest.tsv",
                 Path.cwd() / "reference" / "field-manifest.tsv"):
        try:
            if cand.is_file():
                for line in cand.read_text(encoding="utf-8", errors="replace").splitlines():
                    cols = line.split("\t")
                    if len(cols) >= 3 and cols[1].strip().isdigit():
                        names.setdefault(int(cols[1]), cols[2].strip())
                break
        except OSError:
            pass

    def label(fid):
        if fid in names:
            return names[fid]
        folder = extract.ID_TO_FBG.get(int(fid))
        return re.sub(r"^fbg_n\d+_", "", folder) if folder else "?"
    return label


def _resolve_chain_seeds(seed: str, game=None):
    """Seed -> field-id list. A numeric seed is that id; otherwise an FBG substring seeds EVERY matching
    field (e.g. 'iccv' seeds the whole Ice Cavern zone)."""
    from . import extract
    s = seed.strip()
    if s.lstrip("-").isdigit():
        return [int(s)]
    sl = s.lower()
    hits = sorted(fid for fid, folder in extract.ID_TO_FBG.items() if sl in folder)
    if not hits:
        raise FileNotFoundError(f"no field id or FBG folder matches seed {seed!r}")
    return hits


def _deploy_cfg():
    """The worktree's .ff9deploy.toml (mod_folder + campaign_id_base defaults), or {}."""
    import tomllib
    from pathlib import Path
    f = Path(__file__).resolve().parents[2] / ".ff9deploy.toml"
    try:
        return tomllib.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}
    except Exception:
        return {}


def _print_campaign_summary(plan, out_dir):
    n = len(plan.members)
    ids = f"{plan.members[0].new_id}-{plan.members[-1].new_id}" if n else "-"
    sc = sum(1 for e in plan.edges if e["story_conditional"])
    print(f"{n} fields forked into {out_dir} (ids {ids}); {len(plan.edges)} in-chain gateways retargeted.")
    if sc:
        print(f"  {sc} STORY-COND edge(s) flagged -- add requires_flag (see campaign.toml).")
    if plan.seams:
        kinds = {}
        for s in plan.seams:
            kinds[s["kind"]] = kinds.get(s["kind"], 0) + 1
        print("  " + str(len(plan.seams)) + " seam(s): " + ", ".join(f"{v} {k}" for k, v in sorted(kinds.items())))
    if plan.needs_export:
        print(f"  {len(plan.needs_export)} member(s) NEED an in-game [Export] before deploy: "
              + " ".join(plan.needs_export))
    print(f"  wrote: {out_dir}/campaign.toml")
    print(f"Next: ff9mapkit build-all {out_dir}/campaign.toml")


def _cmd_build_all(args: argparse.Namespace) -> int:
    from . import campaign
    try:
        info = campaign.build_campaign(args.campaign, out=args.out, author=args.author or "",
                                       description=args.description or "", allow_artless=args.allow_artless)
    except (campaign.CampaignError, FileNotFoundError, ValueError, RuntimeError) as e:
        print(str(e), file=sys.stderr)
        return 2
    plan = info["plan"]
    print(f"built campaign '{plan.name}' (mod {plan.mod_folder}, {len(info['dictionary'])} fields) -> {info['out']}")
    for line in info["dictionary"]:
        print("  " + line)
    for w in info["warnings"]:
        print("  warning: " + w, file=sys.stderr)
    print(f"Next: add '{plan.mod_folder}' to Memoria.ini [Mod] FolderNames + relaunch, then deploy-all (P4).")
    return 0


def _cmd_lint_campaign(args: argparse.Namespace) -> int:
    from pathlib import Path
    from . import campaign
    try:
        plan = campaign.load_campaign(args.campaign)
        errors, warnings = campaign.lint_campaign(plan, Path(args.campaign).parent)
    except (campaign.CampaignError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    if getattr(args, "graph", False):
        print(campaign.render_graph(plan))
    for w in warnings:
        print("warning: " + w, file=sys.stderr)
    for e in errors:
        print("error: " + e, file=sys.stderr)
    if errors:
        print(f"campaign '{plan.name}': FAILED -- {len(errors)} error(s), {len(warnings)} warning(s)",
              file=sys.stderr)
        return 2
    print(f"campaign '{plan.name}' OK -- {len(plan.members)} members, {len(plan.edges)} edges, "
          f"{len(plan.seams)} seams, {len(warnings)} warning(s)")
    return 0


def _cmd_new_campaign(args: argparse.Namespace) -> int:
    from pathlib import Path
    from . import campaign
    cfg = _deploy_cfg()
    id_base = args.id_base if args.id_base is not None else int(cfg.get("campaign_id_base", 4000))
    mod_folder = args.mod_folder or cfg.get("mod_folder") or "FF9CustomMap"
    try:
        plan = campaign.new_campaign(args.name, mod_folder, Path(args.dir), id_base=id_base,
                                     flag_base=args.flag_base, flags_per_field=args.flags_per_field)
    except campaign.CampaignError as e:
        print(str(e), file=sys.stderr)
        return 2
    cpath = Path(args.dir) / "campaign.toml"
    print(f"created empty campaign '{plan.name}' at {cpath} (id_base {plan.id_base}, "
          f"mod_folder {plan.mod_folder}).\nNext: ff9mapkit add-field {cpath} --name ROOM1")
    return 0


def _cmd_add_field(args: argparse.Namespace) -> int:
    from pathlib import Path
    from . import campaign
    cpath = Path(args.campaign)
    try:
        plan = campaign.load_campaign(cpath)
        m = campaign.add_field(plan, cpath.parent, name=args.name, source=args.source, game=args.game)
    except (campaign.CampaignError, RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    kind = f"forked field {args.source}" if args.source else "blank room"
    print(f"added {m.name} (id {m.new_id}, {kind}) -> {m.toml_rel}; campaign now has {len(plan.members)} "
          f"member(s).\nEdit it: ff9mapkit edit {cpath.parent / m.toml_rel}")
    return 0


def _cmd_import_chain(args: argparse.Namespace) -> int:
    from pathlib import Path
    from . import chain, eventscan, extract
    try:
        seeds = _resolve_chain_seeds(args.seed, game=args.game)
        bundle = extract.EventBundle(game=args.game)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2

    def zone_fn(fid):
        return chain.zone_label(extract.ID_TO_FBG.get(int(fid)))

    def forkable_fn(fid):
        return int(fid) in extract.ID_TO_FBG       # has a real background -> a walkable field we can fork

    def scan_fn(fid):
        eb = bundle.eb_for_id(fid)
        if eb is None:
            return {"found": False}
        warps = eventscan.scan_all_warps(eb)
        edges = [{"to": g["to"], "kind": chain.WALK_IN, "entrance": g["entrance"],
                  "zone": g["zone"], "story_conditional": g["story_conditional"]}
                 for g in warps["walk_in"]]
        edges += [{"to": s["to"], "kind": chain.SCRIPTED, "entrance": s["entrance"],
                   "trigger": s["trigger"]} for s in warps["scripted"]]
        return {"found": True, "edges": edges, "overworld_exits": warps["overworld_exits"],
                "encounter": eventscan.scan_encounter(eb), "music": eventscan.scan_music(eb)}

    zones = [z.strip().lower() for z in args.zones.split(",") if z.strip()] if args.zones else None
    stop_at = [int(x) for x in args.stop_at.split(",") if x.strip()] if args.stop_at else None
    result = chain.walk(seeds, scan_fn, zone_fn, forkable_fn=forkable_fn, max_hops=args.max_hops,
                        zones=zones, stop_at=stop_at, max_fields=args.max_fields,
                        follow_scripted=args.follow_scripted,
                        stop_at_zone_boundary=not args.cross_zones)

    if args.out:                                  # P2 write mode: fork the chain into campaign/
        from . import campaign
        cfg = _deploy_cfg()
        id_base = args.id_base if args.id_base is not None else int(cfg.get("campaign_id_base", 6000))
        mod_folder = args.mod_folder or cfg.get("mod_folder") or "FF9CustomMap-ow"
        seed_zone = chain.zone_label(extract.ID_TO_FBG.get(seeds[0]))
        cname = args.campaign_name or f"{seed_zone.upper()}_CAMPAIGN"
        try:
            plan = campaign.write_campaign(result, Path(args.out), id_base=id_base,
                        flag_base=args.flag_base, flags_per_field=args.flags_per_field,
                        name=cname, mod_folder=mod_folder, game=args.game, live_seams=args.live_seams)
        except (RuntimeError, FileNotFoundError, ValueError) as e:
            print(str(e), file=sys.stderr)
            return 2
        _print_campaign_summary(plan, args.out)
        return 0

    print(chain.render(result, label_fn=_chain_label_fn(game=args.game)))
    return 0


def _cmd_battle_import(args: argparse.Namespace) -> int:
    from pathlib import Path
    from .battle import extract as bextract
    try:
        meta, toml = bextract.write_battle_project(
            args.bbg, Path(args.out), name=args.name, scene_id=args.id, game=args.game,
            fork_scene=args.fork_scene, ship_as=args.ship_as)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"imported {meta['bbg']}  ({meta['groups']} groups, {meta['geometries']} meshes, "
          f"{len(meta['textures'])} textures)")
    if meta.get("scene"):
        s = meta["scene"]
        print(f"  forked scene {s['donor']} (id {s['donor_id']}): raw16 {s['raw16']}B + raw17 {s['raw17']}B"
              f" + eb/mes x{s['langs']}  -> MINT (scene_id {args.id})")
    print(f"  wrote  : {toml}  (+ {meta['bbg']}.fbx + image#.png"
          f"{' + scene/' if meta.get('scene') else ''})")
    nxt = ("edit %s.fbx in Blender / repaint PNGs, then: ff9mapkit battle-build %s" % (meta['bbg'], toml))
    if meta.get("scene"):
        nxt += "  then  py tools/deploy_battle.py %s --trigger-field 5000  (relaunch + walk)" % toml
    print(f"Next: {nxt}")
    return 0


def _cmd_battle_build(args: argparse.Namespace) -> int:
    from pathlib import Path
    from .battle.build import BattleBuildError, BattleProject, build_battle_mod
    try:
        projects = [BattleProject.load(p) for p in args.battle]
    except (OSError, ValueError) as e:
        print(f"failed to load project: {e}", file=sys.stderr)
        return 2
    try:
        info = build_battle_mod(projects, Path(args.out), mod_name=args.mod_name,
                                author=args.author, description=args.description)
    except (BattleBuildError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"built battle mod '{args.mod_name}' -> {info['root']}")
    for m in info["maps"]:
        print(f"  map: {m}")
    for line in info["dictionary"]:
        print(f"  DictionaryPatch: {line}")
    for line in info["battle_patch"]:
        print(f"  BattlePatch: {line}")
    for w in info["warnings"]:
        print(f"warning: {w}", file=sys.stderr)
    print("To install reversibly into your mod folder: py tools/deploy_battle.py <battle.toml>")
    return 0


def _cmd_battle_list(args: argparse.Namespace) -> int:
    from .battle import extract as bextract
    try:
        if args.scenes:
            rows = bextract.list_battle_scenes(args.pattern, game=args.game)
            kind = "battle scene(s) [mint donors]"
        else:
            rows = bextract.list_battle_maps(args.pattern, game=args.game)
            kind = "battle map(s)"
    except (RuntimeError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 2
    for n in rows:
        print(n)
    print(f"{len(rows)} {kind}")
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


def _cmd_animations(args: argparse.Namespace) -> int:
    """List a character's cutscene gestures (pick one by name for `animation = "<name>"`)."""
    from . import animations as A
    if not args.character:
        print("Characters with an animation catalog (use the name as the cutscene actor's preset):")
        for c in sorted(set(A.TOKENS.values())):
            friendly = next(k for k, v in A.TOKENS.items() if v == c)
            print(f"  {friendly:<10} ({c})  {len(A.catalog(c)):>3} gestures")
        print("\nThen: ff9mapkit animations <character>   (e.g. ff9mapkit animations vivi)")
        return 0
    try:
        acts = A.actions(args.character)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    if args.filter:
        f = args.filter.lower()
        acts = [(a, i) for a, i in acts if f in a]
    print(f"{args.character}: {len(acts)} gesture(s). In a [cutscene] step write  animation = \"<name>\".")
    print(f"  core aliases (every character): {'  '.join(sorted(set(A.CORE)))}\n")
    if args.ids:
        for a, i in acts:
            print(f"  {a:<26} {i}")
    else:
        names = [a for a, _ in acts]
        for r in range(0, len(names), 3):
            print("  " + "".join(f"{n:<26}" for n in names[r:r + 3]).rstrip())
    return 0


def _cmd_flags(args: argparse.Namespace) -> int:
    """Browse the FF9 story-flag registry (named vars, reserved regions, scenario milestones, safe band)."""
    from . import flags as F
    rows = F.registry_rows()
    if args.filter:
        f = args.filter.lower()
        rows = [r for r in rows if f in r[1].lower() or f in r[3].lower()]
    print(f"{len(rows)} registry entr(ies). Author a custom story flag with a [[flag]] table "
          f"(name + index in [{F.FIRST_SAFE_FLAG}, {F.CHOICE_SCRATCH_FLOOR})), then gate by name "
          f'(requires_flag = "<name>").\n')
    for kind, name, loc, meaning, tier in rows:
        print(f"  [{kind:8}] {name:24} {loc:18} ({tier})  {meaning}")
    return 0


def _cmd_flags_inspect(args: argparse.Namespace) -> int:
    """Decode + render a save's gEventGlobal story state. Reads an encrypted SavedData_ww.dat (one report
    per populated slot), a Memoria plaintext extra-save, or an open save JSON / bare Base64 gEventGlobal."""
    from . import flags as F
    from . import save as S
    try:
        reports = S.inspect(args.save)
    except Exception as e:                                              # noqa: BLE001
        print(f"could not read story state: {e}")
        return 2
    multi = len(reports) > 1
    for i, (label, rep) in enumerate(reports):
        if multi:                                                      # label each slot of a multi-save .dat
            print(("\n" if i else "") + f"=== {label} ===")
        print(F.render_report(rep, show_bits=args.all))
    return 0


def _cmd_flags_diff(args: argparse.Namespace) -> int:
    """Diff two saves' gEventGlobal story state (A -> B) -- what a beat / session wrote. Each arg reads the
    same forms as flags-inspect; with one save, --slot-a/--slot-b pick two slots (default: slot 0 -> slot 1)."""
    from . import flags as F
    from . import save as S
    try:
        reps_a = S.inspect(args.a)
        reps_b = S.inspect(args.b) if args.b else reps_a
    except Exception as e:                                              # noqa: BLE001
        print(f"could not read story state: {e}")
        return 2
    sa = args.slot_a if args.slot_a is not None else 0
    sb = args.slot_b if args.slot_b is not None else (1 if args.b is None else 0)
    if not 0 <= sa < len(reps_a):
        print(f"save A has {len(reps_a)} populated slot(s); --slot-a {sa} is out of range")
        return 2
    if not 0 <= sb < len(reps_b):
        print(f"save B has {len(reps_b)} populated slot(s); --slot-b {sb} is out of range "
              f"(diffing two slots of one save needs >=2 populated slots)")
        return 2
    (la, ra), (lb, rb) = reps_a[sa], reps_b[sb]
    print(f"A: {la}\nB: {lb}\n")
    print(F.render_diff(F.diff_reports(ra, rb), show_bits=args.all))
    return 0


def _cmd_save_edit(args: argparse.Namespace) -> int:
    """Set a real FF9 save's story state (ScenarioCounter + flags) -- the RECREATE verb. Dry-run unless
    --out or --in-place is given; --in-place backs the original up first. Never mutates other state."""
    import os
    import time
    import tomllib
    from . import flags as F
    from . import save as S
    try:
        sv = S.FF9Save.load(args.save)
    except Exception as e:                                              # noqa: BLE001
        print(f"could not read save: {e}")
        return 2

    if args.list:
        rows = sv.populated()
        print(f"{len(rows)} populated save(s) in {args.save}:\n")
        for s in rows:
            who = "autosave" if s.block == 0 else f"slot {s.slot} save {s.save}"
            print(f"  block {s.block:<3} [{who:14}]  ScenarioCounter {s.scenario:<6} {s.beat:<20} chests {s.chests}")
        return 0

    # pick the target block
    if args.block is not None:
        n = args.block
    elif args.autosave:
        n = 0
    elif args.slot is not None and args.save_index is not None:
        n = S.block_index(args.slot, args.save_index)
    else:
        print("pick a save: --list to see them, then --slot S --save V (or --autosave, or --block N).")
        return 2

    # resolve edits
    name_map = {}
    if args.names:
        try:
            with open(args.names, "rb") as fh:
                name_map = F.collect_flag_defs(tomllib.load(fh))
        except Exception as e:                                         # noqa: BLE001
            print(f"--names: {e}")
            return 2

    def _bits(spec):
        out = []
        for tok in (spec or "").split(","):
            tok = tok.strip()
            if tok:
                out.append(F.resolve(tok, name_map))
        return out

    extra = S.extra_file_path(args.save, n)
    extra_exists = bool(extra and os.path.exists(extra))
    try:
        scenario = F.resolve_scenario(args.scenario) if args.scenario else None
        set_bits, clear_bits = _bits(args.set_flags), _bits(args.clear_flags)
        # Memoria's per-slot extra file holds the AUTHORITATIVE gEventGlobal (it overrides the vanilla main
        # block on load), so read from it when present; fall back to the main block for a vanilla-only save.
        src = S.read_extra_gEventGlobal(extra) if extra_exists else None
        if src is None:
            src = sv.gEventGlobal(n)
        geg = bytearray(src)
        notes = S.edit_story_state(geg, scenario=scenario, set_flags=set_bits, clear_flags=clear_bits)
        sv.set_gEventGlobal(n, bytes(geg))                 # stage the vanilla main-block edit (in memory)
    except (ValueError, IndexError) as e:
        print(f"edit failed: {e}")
        return 2

    if not notes:
        print("nothing to change (give --scenario / --set / --clear).")
        return 0
    who = "autosave" if n == 0 else f"slot {(n - 1) // 15} save {(n - 1) % 15}"
    print(f"block {n} [{who}] changes:")
    for note in notes:
        print(f"  - {note}")
    print("  Memoria extra file: " + ("present (governs the loaded state)" if extra_exists else "none (vanilla save)"))

    def _backup(path):
        bak = f"{path}.bak.{time.strftime('%Y%m%d-%H%M%S')}"
        with open(path, "rb") as s, open(bak, "wb") as d:
            d.write(s.read())
        return bak

    if getattr(args, "in_place", False):
        print(f"  backed up -> {_backup(args.save)}")
        sv.write(args.save)
        if extra_exists:
            print(f"  backed up -> {_backup(extra)}")
            S.patch_extra_gEventGlobal(extra, bytes(geg))
            chk = S.read_extra_gEventGlobal(extra)
            print(f"  patched main block + Memoria extra ({os.path.basename(extra)}); "
                  f"verified extra ScenarioCounter now {chk[0] | chk[1] << 8}")
        else:
            print("  patched main block")
    elif args.out:
        sv.write(args.out)
        print(f"wrote edited main container -> {args.out}")
        if extra_exists:
            print("  NOTE: --out writes only the main container; the Memoria extra file GOVERNS the loaded "
                  "state and is NOT included -- use --in-place to edit a loadable save.")
    else:
        print("(dry run -- pass --in-place to edit the real save, or --out FILE for a main-container copy)")
    return 0


def _safe_console():
    """Keep dialogue output (which dumps arbitrary FF9 text -- smart quotes, box-drawing, CJK) from crashing
    a legacy console: replace any char the console encoding can't represent instead of raising. No-op on a
    UTF-8 console / when stdout can't be reconfigured."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors="replace")       # keep the console's encoding; just don't crash
        except Exception:                              # noqa: BLE001 -- redirected/older stream
            pass


def _cmd_dialogue(args: argparse.Namespace) -> int:
    """View the authored dialogue of a field.toml -- every NPC line / event message / choice prompt /
    cutscene 'say', with its FINAL on-screen wrapping (the well-formatted-text check). Read-only. A
    campaign.toml (a [campaign] manifest) instead reviews EVERY member field's dialogue in one pass."""
    _safe_console()
    import tomllib
    from . import dialogue as DLG
    from .build import FieldProject
    try:
        with open(args.field, "rb") as fh:
            data = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as e:
        print(f"failed to load: {e}", file=sys.stderr)
        return 2
    # a campaign manifest has a [campaign] table and [[field]] members (a list); a single field has a
    # [field] TABLE -- so a field.toml never misroutes even if it carries a stray [campaign] key.
    is_campaign = "campaign" in data and not isinstance(data.get("field"), dict)
    if is_campaign:
        return _dialogue_campaign(args, DLG)
    try:
        proj = FieldProject.load(args.field)
    except (OSError, ValueError) as e:
        print(f"failed to load: {e}", file=sys.stderr)
        return 2
    lines = DLG.project_dialogue(proj)
    if not lines:
        print(f"{args.field}: no dialogue (no NPC lines / events / choices / cutscene says).")
        return 0
    print(f"dialogue: {args.field}  ({len(lines)} line(s))\n")
    print(DLG.format_lines(lines, clean=args.clean))
    bad = DLG.flag_overflow(lines)
    if bad:
        print(f"{len(bad)} line(s) may overflow the window (an unbreakable wide word) -- check in-game:",
              file=sys.stderr)
        for ln in bad:
            print(f"  ! {ln.who}", file=sys.stderr)
    return 0


def _dialogue_campaign(args: argparse.Namespace, DLG) -> int:
    """Review every member field's authored dialogue in a campaign.toml, in member order, with a roll-up
    (total lines + which fields may overflow). A member that fails to load is noted and skipped, not fatal."""
    from pathlib import Path
    from . import campaign
    from .build import FieldProject
    try:
        plan = campaign.load_campaign(args.field)
    except (campaign.CampaignError, OSError, ValueError) as e:
        print(f"failed to load campaign: {e}", file=sys.stderr)
        return 2
    base = Path(args.field).parent
    members = []
    for m in plan.members:
        p = (base / m.toml_rel)
        label = f"{m.name} (id {m.new_id})"
        if not campaign._within(base, p):              # a crafted/stale toml_rel must not read outside the set
            members.append((label, None, f"field.toml path escapes the campaign folder ({m.toml_rel})"))
            continue
        try:
            members.append((label, FieldProject.load(p), None))
        except Exception as e:                         # noqa: BLE001 -- one broken member must not abort the review
            members.append((label, None, f"{type(e).__name__}: {e}"))
    fields = DLG.campaign_dialogue(members)
    print(f"dialogue (campaign): {plan.name}  ({len(fields)} member field(s))\n")
    total, with_dialogue, overflow = 0, 0, []
    for fd in fields:
        if fd.error:
            print(f"=== {fd.label} ===  (skipped: {fd.error})\n")
            continue
        if not fd.lines:
            print(f"=== {fd.label} ===  (no dialogue)\n")
            continue
        with_dialogue += 1
        total += len(fd.lines)
        print(f"=== {fd.label} ===  ({len(fd.lines)} line(s))")
        print(DLG.format_lines(fd.lines, clean=args.clean))
        bad = DLG.flag_overflow(fd.lines)
        if bad:
            overflow.append((fd.label, bad))
    print(f"total: {total} line(s) across {with_dialogue} field(s) with dialogue.")
    if overflow:
        print(f"{len(overflow)} field(s) may overflow the window (an unbreakable wide word) -- check in-game:",
              file=sys.stderr)
        for label, bad in overflow:
            for ln in bad:
                print(f"  ! {label}: {ln.who}", file=sys.stderr)
    return 0


def _cmd_dialogue_import(args: argparse.Namespace) -> int:
    """Read a REAL FF9 field's dialogue (or a built mod folder's, with --mod) and show 'NPC -> text' --
    the 'import from the game to prove plausibility' verb. Reading the live install needs UnityPy."""
    _safe_console()
    from . import dialogue as DLG
    try:
        if args.mod:
            lines = DLG.read_local_dialogue(args.mod, args.field, lang=args.lang)
            src = args.mod
        else:
            lines = DLG.read_field_dialogue(args.field, lang=args.lang, game=args.game, zone_id=args.zone_id)
            src = "the game install"
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    show_all = args.show_all
    shown = DLG.present(lines, show_system=show_all, dedupe=not show_all)
    print(f"dialogue-import: {args.field}  (from {src}, lang {args.lang}) -- {len(shown)} line(s)\n")
    print(DLG.format_lines(lines, clean=args.clean, show_system=show_all, dedupe=not show_all))
    hidden = len(lines) - len(shown)
    if hidden and not show_all:
        print(f"({hidden} system/duplicate window(s) hidden -- pass --all to show them)", file=sys.stderr)
    unresolved = sum(1 for ln in shown if ln.text is None)
    if unresolved and not args.mod:
        status = DLG.text_source_status(game=args.game)
        if status != "ok":
            print(f"note: {unresolved} line(s) unresolved -- {status}.", file=sys.stderr)
        else:
            print(f"note: {unresolved} line(s) had no resolvable text -- the field's text block didn't "
                  "cover them; pass --zone-id <n> to read a specific <n>.mes block directly.", file=sys.stderr)
    if args.out:
        import json
        recs = [{"source": ln.source, "who": ln.who, "txid": ln.txid, "tail": ln.tail,
                 "pos": list(ln.pos) if ln.pos else None, "text": ln.text} for ln in shown]
        from pathlib import Path
        Path(args.out).write_text(json.dumps(recs, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {args.out}  (SE-derived view -- keep it gitignored)")
    return 0


def _cmd_items(args: argparse.Namespace) -> int:
    """List FF9 item names + ids (use a name for `give_item = ["<name>", count]`)."""
    from . import items as I
    rows = [(i, n) for i, n in I.all_items() if n != "NoItem"]
    if args.filter:
        f = args.filter.lower()
        rows = [(i, n) for i, n in rows if f in n.lower()]
    print(f'{len(rows)} item(s). In an [[event]]/[[choice]] write  give_item = ["<name>", count]  '
          f"(or a numeric id).\n")
    for i, n in rows:
        print(f"  {i:>3}  {n}")
    return 0


def _print_model_detail(m) -> int:
    """One model + its animation gestures (the (group, token) join)."""
    from . import catalog as C
    formk = C.FORM_KIND.get(m.form[:1], "?")
    print(f"model {m.id}: {m.name}")
    print(f"  group {m.group} ({m.kind})  |  form {m.form} ({formk})  |  token {m.token}")
    acts = C.animation_actions(m.id)
    if not acts:
        print("  no animations found for this model's (group, token) "
              "-- often a numbered battle-only model.")
        return 0
    npc = C.npc_anims(m.id)
    if npc and m.field:                                          # the archetype payoff: ready to drop in
        slots = "  ".join(f"{k}={v}" for k, v in npc.items())
        print(f'  place as a field NPC:  [[npc]] model = "{m.name}"')
        print(f"    auto-resolved anims: {slots}")
    core = ("idle", "walk", "run", "turn_l", "turn_r")          # movement gestures first
    ordered = [(a, i) for a in core for (aa, i) in acts if aa == a]
    ordered += [(a, i) for a, i in acts if a not in core]
    print(f"\n  {len(acts)} animation(s). Use an id for an NPC anim slot or a cutscene `animation`:\n")
    for r in range(0, len(ordered), 2):
        print("  " + "".join(f"{a:<22}{i:<8}" for a, i in ordered[r:r + 2]).rstrip())
    return 0


def _cmd_models(args: argparse.Namespace) -> int:
    """Browse actor/field models; naming one exactly shows its animation gestures."""
    from . import catalog as C
    if args.pattern is not None:                                # exact id/name -> detail view
        m = C.model(args.pattern)
        if m is not None:
            return _print_model_detail(m)
    rows = C.models(args.pattern, group=args.group, field_only=args.field)
    if not rows:
        where = f" in group {args.group}" if args.group else ""
        print(f"no models match {args.pattern!r}{where}.", file=sys.stderr)
        return 0
    if len(rows) == 1:                                          # a unique match -> jump to detail
        return _print_model_detail(rows[0])
    print(f"{len(rows)} model(s). The id is what SetModel() / an [[npc]] `model` takes.\n")
    for m in rows:
        tag = f"{m.kind}/{m.form}"
        extra = f"   {len(C.animations_for_model(m.id))} anims" if args.anims else ""
        print(f"  {m.id:>4}  {m.name:<22} {tag:<16}{extra}".rstrip())
    print(f"\nName one to see its gestures:  ff9mapkit models {rows[0].name}")
    return 0


def _cmd_scenes(args: argparse.Namespace) -> int:
    """List FF9 battle-scene (encounter) ids -- what an [encounter] points SetRandomBattles at."""
    from . import catalog as C
    rows = C.battle_scenes(args.pattern)
    if not rows:
        print(f"no battle scenes match {args.pattern!r}.", file=sys.stderr)
        return 0
    print(f"{len(rows)} battle scene(s). The id goes in an [encounter] (e.g. scenes = [<id>, ...]).\n")
    for nm, sid in rows:
        print(f"  {sid:>4}  {nm}")
    return 0


def _cmd_archetypes(args: argparse.Namespace) -> int:
    """List built-in NPC archetypes -- place a common NPC by one name."""
    from . import archetypes as A
    from . import catalog as C
    print('Built-in NPC archetypes -- use as  [[npc]] archetype = "<name>"  (animations auto-resolve):\n')
    for name in A.names():
        model = A.resolve(name)[0]
        if model is None:
            print(f"  {name:<12} (keeps the cloned player)")
        else:
            m = C.model(model)
            print(f"  {name:<12} {m.name if m else model}")
    print('\nAny other model:  [[npc]] model = "GEO_..."   (browse: ff9mapkit models)')
    print('Full reference (roles + where each appears in FF9):  ff9mapkit/docs/ARCHETYPES.md')
    return 0


def _cmd_catalog(args: argparse.Namespace) -> int:
    """Search every reference catalog by name -- the Info Hub 'grab anything'."""
    from . import catalog as C
    res = C.search(args.query)
    if not any(res.values()):
        print(f"nothing matches {args.query!r} in models / items / scenes / fields.")
        return 0
    lim = args.limit
    if res["models"]:
        print(f"models ({len(res['models'])}):")
        for m in res["models"][:lim]:
            print(f"  {m.id:>4}  {m.name:<22} {m.kind}")
        if len(res["models"]) > lim:
            print(f"  ... +{len(res['models']) - lim} more (ff9mapkit models {args.query})")
    if res["items"]:
        print(f"items ({len(res['items'])}):")
        for i, n in res["items"][:lim]:
            print(f"  {i:>4}  {n}")
        if len(res["items"]) > lim:
            print(f"  ... +{len(res['items']) - lim} more (ff9mapkit items -f {args.query})")
    if res["scenes"]:
        print(f"battle scenes ({len(res['scenes'])}):")
        for nm, sid in res["scenes"][:lim]:
            print(f"  {sid:>4}  {nm}")
        if len(res["scenes"]) > lim:
            print(f"  ... +{len(res['scenes']) - lim} more (ff9mapkit scenes {args.query})")
    if res["fields"]:
        print(f"fields ({len(res['fields'])}):")
        for fbg, fid, evt in res["fields"][:lim]:
            print(f"  {fid:>4}  {evt:<26} ({fbg})")
        if len(res["fields"]) > lim:
            print(f"  ... +{len(res['fields']) - lim} more (ff9mapkit list-fields {args.query})")
    return 0


def _cmd_edit(args: argparse.Namespace) -> int:
    """Launch the form-based field-logic editor (Tkinter)."""
    try:
        from .editor import app
    except Exception as e:                       # noqa: BLE001 - e.g. tkinter missing on a headless box
        print(f"could not start the editor UI (is tkinter installed?): {e}", file=sys.stderr)
        return 2
    app.main(args.field)
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

    wm = sub.add_parser("walkmesh", help="convert/repair/verify a walkmesh")
    wm.add_argument("action", choices=["obj", "fix", "verify"],
                    help="obj: .obj->.bgi ; fix: rebuild neighbor links ; verify: run the checks")
    wm.add_argument("input", help="input .obj (obj), .bgi (fix), or .bgi/.field.toml (verify)")
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

    ln = sub.add_parser("lint", help="check a field.toml without building -- one pass over every offline "
                        "validator (schema, story/flag logic, reserved flag bands, walkmesh geometry + "
                        "content placement, layer art, camera pitch)")
    ln.add_argument("field", help="path to a .field.toml")
    ln.set_defaults(func=_cmd_lint)

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
    im.add_argument("--native", action="store_true",
                    help="fork as a NATIVE custom scene: ship the real atlas.png + .bgs (per-tile depth) + "
                         "custom walkmesh, NO .bgx -- renders via the engine's seamless native path (no tile "
                         "seams, faithful occlusion), exactly how Moguri ships. Also forks area<10 fields that "
                         "BG-borrow can't. Needs no in-game export.")
    im.add_argument("--atlas", action="store_true", help="also extract the raw atlas.png (BG-borrow mode only)")
    im.add_argument("--dialogue", action="store_true",
                    help="also append the real field's NPC dialogue as editable [[npc]] stubs (commented) "
                         "for re-authoring -- the words become kit-authored content, not a faithful graft")
    im.add_argument("--graft-player-funcs", action="store_true",
                    help="also carry the donor PLAYER functions a carried object interacts with, onto the fork "
                         "player, so the interactions FIRE (a chest/cask turns to face you on examine, boxes "
                         "gesture) -- the objects carry their interactive funcs WHOLE instead of init_only. "
                         "Clean gesture funcs only; text/exotic/non-Zidane interactions stay dropped. (docs/PLAYER_GRAFT.md)")
    im.add_argument("--carry-text", action="store_true",
                    help="FAITHFULLY carry the donor field's referenced dialogue text (per language, VERBATIM) "
                         "and remap the grafted windows to it, so a carried NPC's talk + grafted text "
                         "interactions show the REAL words (vs --dialogue's editable stubs you re-author). "
                         "Implies --graft-player-funcs; the words are SE-derived (gitignored sidecar). (docs/TEXT_CARRY.md)")
    im.add_argument("--save-moogle", action="store_true",
                    help="carry the donor field's SAVE POINT (the hidden save Moogle + its book/feather/tent + "
                         "pose surgery) VERBATIM as a faithful FF9 save point -- the Moogle pops out of its barrel "
                         "+ the full save flourish, exactly as the original. Implies --graft-player-funcs; emits a "
                         "[[save_moogle]] block. Only fires on a field that actually has one. (docs/SAVEPOINT.md)")
    im.set_defaults(func=_cmd_import)

    ic = sub.add_parser("import-chain",
                        help="walk a connected region of REAL fields from a seed (read-only door graph; P1)")
    ic.add_argument("seed", help="seed field id (e.g. 300) OR an FBG substring (e.g. iccv = seed every Ice Cavern screen)")
    ic.add_argument("--zones", default=None,
                    help="comma-separated zone tokens to span (e.g. iccv,vgdl); default = stay in the seed's zone")
    ic.add_argument("--max-hops", type=int, default=20, dest="max_hops",
                    help="BFS depth cap (default 20; within --zones, --max-fields is the real bound)")
    ic.add_argument("--max-fields", type=int, default=25, dest="max_fields",
                    help="hard field cap; aborts LOUDLY if exceeded (default 25)")
    ic.add_argument("--stop-at", default=None, dest="stop_at", help="comma-separated field ids to not cross")
    ic.add_argument("--follow-scripted", action="store_true", dest="follow_scripted",
                    help="also follow scripted/teleport warps (default: list them as seams, don't recurse)")
    ic.add_argument("--cross-zones", action="store_true", dest="cross_zones",
                    help="don't stop at zone boundaries (follow into any zone, bounded by --max-hops/--max-fields)")
    ic.add_argument("--dry-run", action="store_true", dest="dry_run",
                    help="just print the discovered graph (the default when --out is omitted)")
    # P2 write mode: --out flips import-chain from the read-only dry-run to forking the chain.
    ic.add_argument("--out", default=None,
                    help="WRITE the chain: emit campaign.toml + per-member field.tomls into this dir (P2)")
    ic.add_argument("--id-base", type=int, default=None, dest="id_base",
                    help="member i gets id_base+i (default: .ff9deploy.toml campaign_id_base, else 6000; >=4000)")
    ic.add_argument("--flag-base", type=int, default=FIRST_SAFE_FLAG, dest="flag_base",
                    help=f"campaign flag band start recorded in campaign.toml (default {FIRST_SAFE_FLAG}, "
                         f"the safe floor clear of real-FF9 chest flags)")
    ic.add_argument("--flags-per-field", type=int, default=64, dest="flags_per_field",
                    help="reserved GLOB block width per field (recorded for P5; default 64)")
    ic.add_argument("--campaign-name", default=None, dest="campaign_name",
                    help="campaign/mod name (default <SEED-ZONE>_CAMPAIGN)")
    ic.add_argument("--mod-folder", default=None, dest="mod_folder",
                    help="target mod folder in campaign.toml (default: .ff9deploy.toml, else FF9CustomMap-ow)")
    ic.add_argument("--live-seams", action="store_true", dest="live_seams",
                    help="emit out-of-chain gateways as LIVE doors into the real game (default: comment as seams)")
    ic.set_defaults(func=_cmd_import_chain)

    ba = sub.add_parser("build-all", help="compile a campaign.toml (all member fields) into one Memoria mod (P3)")
    ba.add_argument("campaign", help="path to the campaign.toml manifest (from import-chain --out)")
    ba.add_argument("--out", default=None, help="output mod folder (default: <campaign-dir>/dist)")
    ba.add_argument("--author", default=None, help="ModDescription author (optional)")
    ba.add_argument("--description", default=None, help="ModDescription description (optional)")
    ba.add_argument("--allow-artless", action="store_true", dest="allow_artless",
                    help="build editable members that lack exported art (they render with NO background)")
    ba.set_defaults(func=_cmd_build_all)

    lc = sub.add_parser("lint-campaign",
                        help="validate a campaign.toml (edges/entry/seams/ids/flags) without building (P5)")
    lc.add_argument("campaign", help="path to the campaign.toml manifest")
    lc.add_argument("--graph", action="store_true",
                    help="also print the resolved member graph (doors/seams/dead-ends/unreachable)")
    lc.set_defaults(func=_cmd_lint_campaign)

    nc = sub.add_parser("new-campaign", help="create an EMPTY campaign manifest to author by hand (P6)")
    nc.add_argument("dir", help="directory to create campaign.toml in")
    nc.add_argument("--name", required=True, help="campaign / mod display name")
    nc.add_argument("--mod-folder", default=None, dest="mod_folder",
                    help="Memoria mod folder (default: .ff9deploy.toml / FF9CustomMap)")
    nc.add_argument("--id-base", type=int, default=None, dest="id_base",
                    help="first member field id (default: deploy cfg / 4000)")
    nc.add_argument("--flag-base", type=int, default=FIRST_SAFE_FLAG, dest="flag_base")
    nc.add_argument("--flags-per-field", type=int, default=64, dest="flags_per_field")
    nc.set_defaults(func=_cmd_new_campaign)

    af = sub.add_parser("add-field", help="add a member to a campaign: a blank room, or fork a real field (P6)")
    af.add_argument("campaign", help="path to the campaign.toml manifest")
    af.add_argument("--name", required=True, help="member name (unique; e.g. HUB)")
    af.add_argument("--source", default=None,
                    help="a real field id or unique FBG name to FORK (needs the game); omit for a blank room")
    af.set_defaults(func=_cmd_add_field)

    lf = sub.add_parser("list-fields", help="list real FF9 fields available to import (needs UnityPy)")
    lf.add_argument("pattern", nargs="?", default=None, help="substring filter (e.g. alex, treno, grgr)")
    lf.set_defaults(func=_cmd_list_fields)

    bi = sub.add_parser("battle-import",
                        help="fork a REAL FF9 battle background (BBG) into an editable battle.toml (needs UnityPy)")
    bi.add_argument("bbg", help="battle-bg name to fork GEOMETRY from, e.g. BBG_B013 (see `battle-list`)")
    bi.add_argument("--out", default=".", help="dir to write into (default: .)")
    bi.add_argument("--name", default=None, help="scene name for a minted scene (default: <BBG>_FORK)")
    bi.add_argument("--id", type=int, default=5000, help="scene id for a minted scene (default 5000)")
    bi.add_argument("--fork-scene", default=None, metavar="DONOR",
                    help="ALSO fork a battle scene's gameplay/camera/text (a tier-c MINT), e.g. EF_R007 "
                         "(see `battle-list --scenes`). Yields a brand-new, independently-triggerable battle.")
    bi.add_argument("--ship-as", default=None, metavar="BBG_B###",
                    help="ship the geometry under a NEW bbg number (e.g. BBG_B200) = a wholly original map "
                         "(the kit authors a static INB for it), instead of overriding the forked slot.")
    bi.set_defaults(func=_cmd_battle_import)

    bb = sub.add_parser("battle-build", help="compile a battle.toml into a Memoria mod (custom battle map)")
    bb.add_argument("battle", nargs="+", help="one or more battle.toml files")
    bb.add_argument("--out", default="dist", help="output mod folder (default: ./dist)")
    bb.add_argument("--mod-name", default="FF9CustomMap", help="mod name / InstallationPath")
    bb.add_argument("--author", default="", help="mod author")
    bb.add_argument("--description", default="", help="mod description")
    bb.set_defaults(func=_cmd_battle_build)

    bl = sub.add_parser("battle-list",
                        help="list real FF9 battle backgrounds available to fork (needs UnityPy)")
    bl.add_argument("pattern", nargs="?", default=None, help="substring filter (e.g. b013)")
    bl.add_argument("--scenes", action="store_true",
                    help="list battle SCENE names (mint donors, e.g. EF_R007) instead of map names")
    bl.set_defaults(func=_cmd_battle_list)

    an = sub.add_parser("animations", help="list a character's cutscene gestures (pick by name)")
    an.add_argument("character", nargs="?", help="vivi / zidane / garnet / steiner / freya / quina / eiko / amarant")
    an.add_argument("-f", "--filter", help="only show gestures whose name contains this")
    an.add_argument("--ids", action="store_true", help="also print each gesture's numeric anim id")
    an.set_defaults(func=_cmd_animations)

    it = sub.add_parser("items", help="list FF9 item names + ids (give_item by name)")
    it.add_argument("-f", "--filter", help="only show items whose name contains this")
    it.set_defaults(func=_cmd_items)

    ar = sub.add_parser("archetypes", help="list built-in NPC archetypes (place a common NPC by name)")
    ar.set_defaults(func=_cmd_archetypes)

    md = sub.add_parser("models", help="browse actor/field models; name one to see its animations")
    md.add_argument("pattern", nargs="?", default=None,
                    help="name/token substring to filter, or an exact model name/id for detail")
    md.add_argument("-g", "--group", help="filter by group (MAIN/NPC/MON/ACC/SUB/WEP) or kind (npc/playable/...)")
    md.add_argument("--field", action="store_true", help="only field-form models (the ones you place as NPCs)")
    md.add_argument("--anims", action="store_true", help="also show each model's gesture count")
    md.set_defaults(func=_cmd_models)

    sc = sub.add_parser("scenes", help="list FF9 battle-scene (encounter) ids by name")
    sc.add_argument("pattern", nargs="?", default=None, help="name substring (e.g. alex, evil, b3)")
    sc.set_defaults(func=_cmd_scenes)

    ct = sub.add_parser("catalog", help="search every reference catalog (models/items/scenes/fields) by name")
    ct.add_argument("query", help="substring to search across all catalogs")
    ct.add_argument("--limit", type=int, default=15, help="max rows per kind (default 15)")
    ct.set_defaults(func=_cmd_catalog)

    fl = sub.add_parser("flags", help="browse the FF9 story-flag registry (named vars / reserved regions / milestones)")
    fl.add_argument("filter", nargs="?", default=None, help="substring to filter by name or meaning")
    fl.set_defaults(func=_cmd_flags)

    fi = sub.add_parser("flags-inspect",
                        help="decode a save's story state (SavedData_ww.dat per slot, or a save JSON / Base64)")
    fi.add_argument("save", help="path to SavedData_ww.dat (per slot), a Memoria extra-save, a save JSON "
                                 "file / text, or a bare Base64 gEventGlobal blob")
    fi.add_argument("--all", action="store_true", help="also list the unmapped set bits")
    fi.set_defaults(func=_cmd_flags_inspect)

    fd = sub.add_parser("flags-diff",
                        help="diff two saves' story state (A -> B): what scenario/flags a beat changed")
    fd.add_argument("a", help="save A: SavedData_ww.dat / a Memoria extra-save / a save JSON file-or-text "
                              "/ a bare Base64 gEventGlobal blob")
    fd.add_argument("b", nargs="?", default=None,
                    help="save B (default: same source as A -- diff two slots of one save)")
    fd.add_argument("--slot-a", type=int, default=None, help="A's populated-slot index (default 0)")
    fd.add_argument("--slot-b", type=int, default=None,
                    help="B's populated-slot index (default 1 when B is omitted, else 0)")
    fd.add_argument("--all", action="store_true", help="also list the raw unmapped bit indices")
    fd.set_defaults(func=_cmd_flags_diff)

    se = sub.add_parser("save-edit",
                        help="set a real FF9 save's story state (ScenarioCounter + flags) -- the 'recreate' verb")
    se.add_argument("save", help="path to SavedData_ww.dat (or a copy of it)")
    se.add_argument("--list", action="store_true", help="list the populated saves (slot/save, scenario, chests) and exit")
    se.add_argument("--slot", type=int, help="save slot 0-9")
    se.add_argument("--save", dest="save_index", type=int, help="save 0-14 within the slot")
    se.add_argument("--block", type=int, help="raw data-block index (alternative to --slot/--save; 0 = autosave)")
    se.add_argument("--autosave", action="store_true", help="target the autosave block")
    se.add_argument("--scenario", help="set ScenarioCounter: a value (2500) or an area name (\"Ice Cavern\")")
    se.add_argument("--set", dest="set_flags", help="comma-separated flag indices (or [[flag]] names with --names) to SET")
    se.add_argument("--clear", dest="clear_flags", help="comma-separated flag indices to CLEAR")
    se.add_argument("--names", help="a field.toml/campaign.toml whose [[flag]] table names --set/--clear flags")
    se.add_argument("--out", help="write the edited save to this path (safe; leaves the original untouched)")
    se.add_argument("--in-place", action="store_true", help="overwrite the save (a timestamped .bak is made first)")
    se.set_defaults(func=_cmd_save_edit)

    ed = sub.add_parser("edit", help="open the form-based field-logic editor (no TOML hand-editing)")
    ed.add_argument("field", nargs="?", default=None, help="a .field.toml to open (optional)")
    ed.set_defaults(func=_cmd_edit)

    dl = sub.add_parser("dialogue", help="view a field.toml's authored dialogue + how each line wraps on "
                        "screen (or a campaign.toml: review every member field at once)")
    dl.add_argument("field", help="path to a .field.toml (or a campaign.toml to review the whole set)")
    dl.add_argument("--clean", action="store_true", help="strip FF9 control tags for a plain read")
    dl.set_defaults(func=_cmd_dialogue)

    di = sub.add_parser("dialogue-import",
                        help="read a REAL FF9 field's dialogue (or a built mod's, with --mod) -- 'NPC -> text'")
    di.add_argument("field", help="real field id or FBG name (e.g. 100, alexandria); or a name/id in the --mod")
    di.add_argument("--lang", default="us", help="language block to read (default us)")
    di.add_argument("--mod", default=None,
                    help="read from a BUILT mod folder on disk instead of the install (no UnityPy needed); "
                         "e.g. --mod release/FF9CustomMap")
    di.add_argument("--zone-id", type=int, default=None, dest="zone_id",
                    help="the field's text-block id -> read <zone-id>.mes directly (else auto-detect by txid)")
    di.add_argument("--clean", action="store_true", help="strip FF9 control tags for a plain read")
    di.add_argument("--all", action="store_true", dest="show_all",
                    help="show ALL window calls incl. system/notification windows + repeated call sites "
                         "(default hides them: only real dialogue, de-duplicated)")
    di.add_argument("--out", default=None,
                    help="also write a JSON view here (use a .dialogue.json suffix -- SE-derived, gitignored)")
    di.set_defaults(func=_cmd_dialogue_import)

    xt = sub.add_parser("extract-templates",
                        help="regenerate the kit's base assets from YOUR FF9 install (ships no game data)")
    xt.add_argument("--no-fixtures", action="store_true", help="skip the test fixtures (templates only)")
    xt.set_defaults(func=_cmd_extract_templates)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
