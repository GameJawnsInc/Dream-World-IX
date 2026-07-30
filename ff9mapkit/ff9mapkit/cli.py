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
    gen-hub   - generate a World-Hub field.toml from a journeys.toml registry (P6)
    lint-journey     - validate a multi-campaign journeys.toml (id/flag disjointness, links resolve)
    assemble-journey - lint + emit the World-Hub field for bare AND multi-campaign journeys
    reference-arcs   - FF9 reference-arc scaffold: emit a chained journeys.toml of FF9's real story arcs
    extract-field - cache a real field's camera+walkmesh into the gitignored workspace cache
    import    - fork a real FF9 field (BG-borrow, or --editable custom scene) (Tier 3)
    list-fields - list the real FF9 fields available to import              (Tier 3)
    find-field  - resolve a field id / name / FBG substring -> id + friendly name + archive folder
    battle-import - fork a real FF9 battle background (BBG) into an editable battle.toml (needs UnityPy)
    battle-build  - compile a battle.toml into a Memoria mod (custom 3D battle map; stock engine)
    battle-list   - list the real FF9 battle backgrounds available to fork
    battle-actions- list the shared PLAYER abilities (Actions.csv) + the scriptId formula catalog
    battle-telemetry - log every battle calc to a JSONL (Overload hook) + summarize it (--report)
    battle-scene  - inspect a real battle scene's enemy data (stats/affinities/rewards/attacks)
    encounters    - browse battle LOCATIONS: what's in a real place, and where a monster appears
    dialogue  - view a field.toml's authored dialogue + how each line wraps on screen
    dialogue-import - read a REAL FF9 field's dialogue (or a built mod's) -- 'NPC -> text'
    fork-report - preview, offline, what a fork of a REAL field will/won't reproduce (fidelity report)
    animations/items - browse the cutscene-gesture / item catalogs by name
    models/scenes/catalog - the Info Hub: browse models (+ their animations), battle scenes, or
                            search every reference catalog by name
    extract-templates - regenerate base assets from the user's own FF9 install (no game data shipped)
    setup     - one-shot: find the FF9 install, remember it, extract base assets, report Memoria status

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


def _print_engine_status(game) -> None:
    """Explain, in plain language, what the installed engine can and can't run. Advisory only -- this
    never affects `doctor`'s exit code, and every probe underneath it is best-effort (a version reads
    None off Windows, in which case the drift note is simply skipped)."""
    from . import memoria
    rep = memoria.engine_report(game)
    ver = f" (Assembly-CSharp v{rep['assembly_version']})" if rep["assembly_version"] else ""
    if not rep["memoria_installed"]:
        print("engine       : Memoria NOT detected -- no mod of any kind will load without it.")
        print("  Install Memoria first (https://github.com/Albeoris/Memoria), then re-run doctor.")
        return
    if rep["dwix_bundle_applied"]:
        print(f"engine       : Memoria + Dream World IX patches{ver}")
        print("  Forked real fields and the world-* overworld commands should work.")
        print("  (A Memoria update or re-patch reverts this -- re-run setup --install-engine to reapply.)")
        return
    # The signal is "our installer left backups here", so a SELF-BUILT patched engine (msbuild deploys
    # straight into Managed, no backup dir) reads as stock -- hence "not detected", never "you have stock".
    print(f"engine       : Memoria{ver} -- no Dream World IX patches detected.")
    print("  (If you built the memoria-patches/ stack yourself, that won't show up here -- this only")
    print("  detects the bundle installed via ff9mapkit.)")
    print("  Already works unmodified: novel from-scratch fields, custom models, battle content,")
    print("  audio, and playable characters.")
    print("  Needs the patched engine: FORKED real fields, and the world-* overworld commands.")
    print("  To get it, see ff9mapkit/docs/ENGINE.md, or:")
    print("      ff9mapkit setup --install-engine <dwix-custom-memoria-*.zip>")
    built, base = rep["assembly_build_date"], rep["base_commit_date"]
    if built and abs((built - base).days) > memoria.STALE_WARNING_DAYS:
        print(f"  NOTE: your Memoria compiled {built}, but the prebuilt bundle is pinned to the")
        print(f"  {base} base -- that's a big gap, and the bundle only replaces managed DLLs, not")
        print("  Memoria's native side. If it crashes, build the memoria-patches/ stack against your")
        print("  own Memoria source instead (ENGINE.md option 3).")


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
    _print_engine_status(game)
    # deploy LEDGER reconciliation: an id the ledger says was deployed but that NO stacked mod folder
    # registers any more is a registration that VANISHED (a campaign wholesale-replace, a foreign deploy's
    # drop, a hand edit) -- and the engine black-screens on it with no error. Retirements are deliberate and
    # listed separately, because the 2026-07-18 hunt burned hours on a field that had simply been retired.
    from . import deploylog
    _rep = deploylog.reconcile(game)
    print(f"deploy ledger: {deploylog.ledger_path(game)} "
          f"({'present' if deploylog.ledger_path(game).is_file() else 'absent -- written on the next deploy'})")
    _warn = deploylog.reconcile_warning(_rep)
    if _warn:
        print("  !! " + _warn.replace("\n", "\n  "))
    if _rep.retired:
        print(f"  retired on purpose (not a problem): "
              f"{', '.join(f'{e.field_id} @ {e.when}' for e in _rep.retired)}")
    return 0


def _cmd_coop(args: argparse.Namespace) -> int:
    """Two-player co-op ghost sync in one command per side -- see ff9mapkit/coop.py."""
    from . import coop
    try:
        return coop.run(args)
    except (ConfigError, FileNotFoundError, RuntimeError, ValueError, OSError) as e:
        print(str(e), file=sys.stderr)
        return 2


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


def _cmd_setup(args: argparse.Namespace) -> int:
    """One-shot post-install setup: find the FF9 install, remember it in the user config, regenerate the
    base assets, and report the Memoria engine status. ``--install-engine <zip>`` additionally installs the
    Dream World IX engine bundle (backed up first). Safe to re-run; returns non-zero only so a calling
    script (e.g. the installer) can tell -- it never needs to block."""
    from pathlib import Path

    from . import memoria, provision
    from .config import save_game_path

    # 1) resolve the install, and remember it so future commands need no --game/$FF9_GAME_PATH
    try:
        game = find_game_path(args.game)
    except ConfigError as e:
        print(str(e), file=sys.stderr)
        print("\nOnce you know the path, run:  ff9mapkit setup --game \"<path>\"", file=sys.stderr)
        return 2
    print(f"Found FINAL FANTASY IX:  {game}")
    try:
        cfg = save_game_path(game)
        print(f"  remembered in {cfg}  (future commands won't need --game)")
    except OSError as e:                                  # noqa: BLE001 - config write is best-effort
        print(f"  (couldn't save the config: {e})", file=sys.stderr)

    rc = 0
    # 2) regenerate the base assets (the one-time bring-your-own-install step; reads YOUR install)
    if not args.no_extract:
        if provision.templates_present() and not args.force:
            print("Base assets:  already extracted (use --force to redo).")
        elif not _has_unitypy():
            print("Base assets:  SKIPPED -- UnityPy isn't installed (it reads FF9's assetbundles).\n"
                  "  Install it:  pip install UnityPy   (or reinstall ff9mapkit with the [assets] extra)",
                  file=sys.stderr)
            rc = 1
        else:
            print("Base assets:  regenerating from your install (ff9mapkit ships no game data)...")
            try:
                rep = provision.extract_templates(game=str(game), fixtures=not args.no_fixtures, verbose=True)
                print(f"  OK -- {len(rep['verified'])} assets regenerated + verified.")
            except Exception as e:                       # noqa: BLE001
                print(f"  extract-templates failed: {e}", file=sys.stderr)
                rc = 1

    # 3) Memoria engine status (forked fields need it; novel/from-scratch fields run on stock Memoria)
    st = memoria.memoria_status(game)
    if st["installed"]:
        print("Memoria engine:  detected -- forked real fields will work.")
    else:
        print("Memoria engine:  NOT detected.")
        print("  From-scratch / BG-borrow fields run on stock Memoria. To play FORKED real fields, install\n"
              "  Memoria + the Dream World IX engine bundle (dwix-custom-memoria-*.zip) -- see docs/ENGINE.md,\n"
              "  or re-run:  ff9mapkit setup --install-engine <bundle.zip>")

    # 4) opt-in: install the engine bundle (backed up; never touches Memoria.ini). Version-aware +
    #    graceful, so the installer can pass --install-engine unconditionally (Memoria may be absent).
    if args.install_engine:
        zp = Path(args.install_engine)
        if not zp.is_file():
            print(f"--install-engine: file not found: {zp}", file=sys.stderr)
            return 1
        if not st["installed"]:
            # Memoria isn't here yet (common when our installer runs first) -- non-fatal; show how to
            # apply it later. (Novel / BG-borrow fields don't need it; only forked real fields do.)
            print("Engine bundle:  SKIPPED -- Memoria isn't installed in this FF9 folder yet.")
            print("  Forked real fields need Memoria. Install it (https://github.com/Albeoris/Memoria),")
            print(f'  then re-run:  ff9mapkit setup --install-engine "{zp}"')
            return rc
        cmp = memoria.engine_compat(game, zp)
        if cmp["already_applied"] and not args.force:
            print(f"Engine bundle:  Dream World IX patches already installed "
                  f"(Assembly-CSharp v{cmp['installed']}) -- nothing to do.")
            print("  (--force reinstalls. If you later update or re-patch Memoria, re-run this to reapply.)")
            return rc
        if cmp["installed"] and cmp["bundle"] and cmp["installed"] != cmp["bundle"]:
            print(f"Engine bundle:  replacing your Memoria engine (Assembly-CSharp v{cmp['installed']}) with")
            print(f"  the Dream World IX patched build (v{cmp['bundle']}, based on Memoria {memoria.BASE_COMMIT}).")
        else:
            print(f"Engine bundle:  installing {zp.name} (backing up the originals first)...")
        import datetime  # noqa: PLC0415
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        try:
            rep = memoria.install_engine_bundle(game, zp, stamp=stamp)
            print(f"  backed up {len(rep['backed_up'])} DLL(s) -> {rep['backup_root']}")
            print(f"  installed {len(rep['installed'])} DLL(s) into x64 + x86 Managed. Relaunch FF9 to load it.")
            print("  NOTE: a later Memoria update / re-patch OVERWRITES these -- just re-run this to reapply.")
            print("  (Undo: copy the backed-up DLLs back over the Managed ones.)")
        except Exception as e:                           # noqa: BLE001
            print(f"  engine install failed: {e}", file=sys.stderr)
            return 1

    if rc == 0:
        print("\nSetup complete.  Try 'ff9mapkit doctor', or open the GUI with 'ff9mapkit-workspace'.")
    return rc


def _cmd_deploy_campaign(args: argparse.Namespace) -> int:
    """Reversibly install a built campaign into the live game + wire New Game (the installed-copy equivalent of
    tools/deploy_campaign.py). SAFE BY DEFAULT: prints the plan; pass --apply to touch the game. Snapshots +
    reverts go to a per-user cache (the wheel ships no repo tools/scroll_out)."""
    from . import deploy, provision
    from .deploy import DeployError
    try:
        report = deploy.deploy_campaign(
            args.target, mod_folder=args.mod_folder, entry=args.entry, apply=args.apply,
            allow_artless=args.allow_artless, no_warp=args.no_warp,
            allow_name_collision=args.allow_name_collision, allow_id_collision=args.allow_id_collision,
            flag_base=args.flag_base, no_promote_csv=args.no_promote_csv, promote_csv_to=args.promote_csv_to,
            out_dist=args.out_dist, backups_dir=provision.deploy_backups_dir(),
            reverts_dir=provision.deploy_reverts_dir())
    except DeployError as e:
        print(str(e), file=sys.stderr)
        return 2
    return report["rc"]


def _cmd_deploy(args: argparse.Namespace) -> int:
    """Reversibly install ONE field.toml into the live game (the installed-copy equivalent of
    tools/deploy_field.py, minus its repo-only dev-loop levers). SAFE BY DEFAULT: prints the plan; pass
    --apply to touch the game. Snapshot + revert go to a per-user cache."""
    from . import deploy, provision
    from .deploy import DeployError
    try:
        report = deploy.deploy_field(
            args.field, game=getattr(args, "game", None), mod_folder=getattr(args, "mod_folder", None),
            apply=args.apply, allow_name_collision=args.allow_name_collision,
            allow_id_collision=args.allow_id_collision, allow_drop=args.allow_drop,
            out_dist=args.out_dist, backups_dir=provision.deploy_backups_dir(),
            reverts_dir=provision.deploy_reverts_dir())
    except DeployError as e:
        print(str(e), file=sys.stderr)
        return 2
    return report["rc"]


def _cmd_deploy_journey(args: argparse.Namespace) -> int:
    """Deploy (or dry-run) a multi-campaign journey into the live game (the installed-copy equivalent of
    tools/deploy_journey.py). Default = a dry-run playbook; --apply runs the one-shot install with one unified
    revert. Snapshots + reverts go to a per-user cache."""
    from . import deploy, provision
    report = deploy.deploy_journey(
        args.journeys, apply=args.apply, newgame=args.newgame, apply_links=args.apply_links,
        single_folder=args.single_folder, allow_collision=args.allow_collision, hub_out=args.hub_out,
        backups_dir=provision.deploy_backups_dir(), reverts_dir=provision.deploy_reverts_dir())
    return report["rc"]


def _cmd_newgame(args: argparse.Namespace) -> int:
    """Point New Game at a deployed custom field id (the installed-copy New-Game wiring). Creates the field-70
    override FROM STOCK by default (robust: works on a clean install / fresh fork); --retarget patches an
    existing override. Reversible -- the revert script lands in the per-user deploy cache."""
    from . import newgame, provision
    try:
        game = find_game_path(args.game)
    except ConfigError as e:
        print(str(e), file=sys.stderr)
        return 2
    bk, rv = provision.deploy_backups_dir(), provision.deploy_reverts_dir()
    if args.retarget:
        res = newgame.retarget(game, args.field_id, frm=args.frm, backups_dir=bk, reverts_dir=rv,
                               dry_run=args.dry_run)
    else:
        res = newgame.wire_from_stock(game, args.field_id, mod_folder=args.mod_folder, backups_dir=bk,
                                      reverts_dir=rv, dry_run=args.dry_run)
    if res.get("revert"):
        print(f"  revert: py {res['revert']}")
    return 0 if res["ok"] else 2


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


def _pursuit_extent(wmesh) -> float:
    """Moved to :func:`ff9mapkit.scene.routes.pursuit_extent` (the Workspace's stage
    sweep shares it); kept as an alias for the lint lane below."""
    from .scene.routes import pursuit_extent
    return pursuit_extent(wmesh)


def _cmd_behavior(args: argparse.Namespace) -> int:
    """behavior compile|lint|view <field.toml> -- the [behavior] tree surface, offline.

    compile: dry-compile (placeholder entry slots -- the real ones bind at build) and
    print the report: blackboard map (the ~ Flags live trace), per-unit action ids,
    public-flag indices for [[choice]] set_flag wiring. lint: the static checks plus a
    walkability SWEEP of every route a patrol/march/flee references (the layout
    probe's sweep -- a leg that leaves the mesh stalls its walker in-game); a
    route="auto" patrol/march is judged on its ROUTED line (what the build compiles)
    and each auto-routed leg is reported as such, not as a jam. Every sweep is
    FLOOR-AWARE: a leg crossing floors anywhere but a real seam edge wedges against
    the terrace base (looks on-mesh in flattened 2D) and is an error. lint also
    sweeps the DYNAMIC feeds: a chase tests the family of pursuit legs its branch's
    own near radius admits; a wander is modelled the way the engine plays it -- the
    roll lands ANYWHERE in the box, mesh or not, so walker x every-roll-cell legs
    are tested and the jam fraction reported. view: compile, then
    disassemble every generated body (the ticker, each duty walk, each dispatch/nudge
    function) -- the bytecode the trees became."""
    from . import build as _build
    from .content import behavior as B
    from .content import behaviortoml as BT

    project = _build.FieldProject.load(args.field)
    raw = project.raw
    if not BT.table(raw):
        print("no [behavior] table (with [[behavior.unit]] rows) in this field.toml",
              file=sys.stderr)
        return 2
    problems = BT.validate(raw, verbatim="verbatim_eb" in raw)

    wmesh = None
    wmesh_err = None
    try:
        wmesh = _build.behavior_walkmesh(project)
    except Exception as e:
        wmesh_err = str(e)
    plan = {}
    plan_err = None
    if BT.wants_autoroute(raw):
        try:                                       # wmesh None -> the plan's own error
            plan = BT.autoroute_plan(raw, wmesh)
        except BT.BehaviorTomlError as e:
            plan_err = str(e)

    if args.action == "lint":
        warnings = []
        routed_lines = BT.describe_autoroute(plan, raw)
        if plan_err:
            problems.append(plan_err)
        # THE CLOCK-COUPLED BATTLE LAW: a timed field firing a scene whose AI reads
        # B_SYSVAR[17] (= TimerUI.Time) -- it ends itself on an expired clock
        warnings += BT.clock_coupled_warnings(raw, game=getattr(args, "game", None))
        # THE DRAINING-CONDITION LAW: stacked once-branches on a gate that can stop
        # holding -- everything below the first silently starves
        warnings += BT.draining_once_warnings(raw)
        # a hud digits reserve wider than the u16 value operand can ever show
        warnings += BT.hud_digits_warnings(raw)
        mpaths = BT.marker_paths(raw)
        if wmesh is None:
            warnings.append(f"(no walkmesh resolved -- route sweeps skipped: {wmesh_err})")
        else:
            from .scene import routes as _routes
            bedges = _routes.mesh_boundary_edges(wmesh)
            positions = BT._npc_marker_positions(raw)
            seen = set()
            jam_hint = False
            for ref in BT.movement_route_refs(raw):
                # sweep what the walker actually walks: patrol always CYCLES (wrap leg
                # included), march never does; flee keeps the marker's own closed flag
                # (threat-gone retargets make any refuge pair a plausible leg)
                key = (ref["ui"], ref["bi"])
                if ref["autoroute"] and key in plan:
                    pts = plan[key]["points"]      # the ROUTED line is what compiles --
                    closed = ref["verb"] == "patrol"   # lint judges it, not the authored one
                    name = f"{ref['verb']} {BT._route_label(ref['value'])} ({ref['unit']!r})"
                elif ref["autoroute"]:
                    continue                       # plan errored -- already a problem
                else:
                    try:
                        pts = BT._resolve_route(ref["value"], positions, mpaths,
                                                ref["unit"] or "?")
                    except BT.BehaviorTomlError:
                        continue                   # unresolvable -> validate reported it
                    closed = (ref["verb"] == "patrol" or
                              (ref["verb"] == "flee" and isinstance(ref["value"], str)
                               and mpaths.get(ref["value"], ((), False))[1]))
                    name = (ref["value"] if isinstance(ref["value"], str)
                            else f"{ref['unit']}#{ref['bi']} {ref['verb']}")
                dk = (tuple(map(tuple, pts)), closed)
                if dk in seen:
                    continue
                seen.add(dk)
                legs = _routes.sweep_polyline(pts, wmesh, bedges, closed=closed)
                probs = _routes.describe_leg_problems(name, legs)
                # OFF-MESH and an unseamed floor crossing both jam every lap = errors
                jams = [p for p in probs if "OFF-MESH" in p or "NO SEAM" in p]
                problems += jams
                warnings += [p for p in probs if p not in jams]
                if jams and ref["verb"] in ("patrol", "march") and not ref["autoroute"]:
                    jam_hint = True
            if jam_hint:
                warnings.append('hint: patrol/march accept route = "auto" -- the build '
                                're-routes jammed legs through the walkmesh pathfinder '
                                '(clear legs stay as authored)')
            # THE PURSUIT SWEEP: chase/wander have no authored line to route (their
            # target is a runtime position -- the Path-B study), so sweep the FAMILY of
            # legs each branch's own engagement gate admits. WARNINGS only: a dynamic
            # jam is probabilistic (it needs the quarry to stand on a bad spot), unlike
            # a static route's off-mesh leg, which jams every lap.
            extent = _pursuit_extent(wmesh)
            pursuit_hint = False
            pseen = set()
            for ref in BT.pursuit_refs(raw):
                label = (f"{ref['verb']} {ref['target']!r} ({ref['unit']!r} "
                         f"branch #{ref['bi']})")
                if ref["verb"] == "wander":
                    # the roll-anywhere, floor-aware model: the engine's roll never
                    # checks the mesh, so the family is walker x EVERY box cell
                    dk = ("wander", ref["centre"], ref["wradius"])
                    if dk in pseen:
                        continue
                    pseen.add(dk)
                    res = _routes.sweep_wander(wmesh, ref["centre"][0], ref["centre"][1],
                                               ref["wradius"], bedges=bedges)
                    warnings += _routes.describe_wander_problems(
                        f"{ref['target']!r} ({ref['unit']!r} branch #{ref['bi']})", res)
                    continue
                radius = ref["radius"]
                ungated = radius is None
                if ungated:
                    radius = extent            # no near gate -> the whole field
                dk = (ref["verb"], radius, ref["standoff"], ref["source_box"],
                      ref["target_box"])
                if dk in pseen:
                    continue                   # identical families (the raid's twin
                pseen.add(dk)                  # guards) report once
                res = _routes.sweep_pursuit(wmesh, radius, standoff=ref["standoff"],
                                            bedges=bedges,
                                            source_box=ref["source_box"],
                                            target_box=ref["target_box"])
                if ungated:
                    label += " [UNGATED: no near/any_near row bounds this target, so the "
                    label += f"family is the whole field ({extent:.0f}u)]"
                probs = _routes.describe_pursuit_problems(label, res)
                warnings += probs
                if probs and res["blocked"]:
                    pursuit_hint = True
            if pursuit_hint:
                warnings.append('hint: a dynamic chase cannot be auto-routed (no '
                                'build-time leg origin) -- tighten the branch\'s near '
                                'radius so it engages only where the line is clear, or '
                                'add a march route = "auto" approach leg and chase from '
                                'close range')
        for p in problems:
            print(f"error: {p}")
        for w in warnings:
            print(f"warning: {w}")
        for r in routed_lines:
            print(f"routed: {r}")
        if not problems and not warnings:
            print("behavior lint: clean" + (" (auto-routing applied)" if routed_lines else ""))
        elif not problems:
            print("behavior lint: no errors")
        return 1 if problems else 0

    if plan_err:
        problems.append(plan_err)
    if problems:
        for p in problems:
            print(f"error: {p}", file=sys.stderr)
        return 1
    units = BT.units(raw)
    slots = {str(u["npc"]): i + 2 for i, u in enumerate(units)}   # placeholders (build binds real ones)
    fb = BT.build(raw, npc_slots=slots,
                  npc_txids_by_name={n.get("name"): 0 for n in raw.get("npc", []) or []
                                     if n.get("name") and "dialogue" in n},
                  behavior_txids={**{(ui, bi): 0 for ui, bi, _ in BT.announce_lines(raw)},
                                  **{("hud", hi): 0 for hi, _h in BT.hud_lines(raw)}},
                  routed=plan)
    try:
        cb = fb.compile()
    except B.BehaviorError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    b = raw["behavior"]
    print(cb.report)
    pf = [(nm, fb.bb.flag(str(nm))) for nm in (b.get("public_flags") or [])]
    if pf:
        print("\npublic flags (wire [[choice]] set_flag rows to these indices):")
        for nm, idx in pf:
            print(f"  {nm} -> Global.Bit[{idx}]  (set_flag = [{idx}, 1])")
    if fb.pool_flags:
        print("\npool spawn-request flags (a [[choice]] Hire row sets one; the next "
              "never-spawned pooled unit spawns at the player):")
        for nm, idx in fb.pool_flags.items():
            print(f"  {nm} -> Global.Bit[{idx}]  (set_flag = [{idx}, 1])")
    routed_lines = BT.describe_autoroute(plan, raw)
    if routed_lines:
        print('\nauto-routed legs (route = "auto"; clear legs stay as authored):')
        for r in routed_lines:
            print(f"  {r}")
    print(f"\nstable hash {cb.stable_hash()}  (entry slots shown are PLACEHOLDERS; "
          f"announce txids bind at build)")
    if args.action == "view":
        from .eb import disasm as D

        def dump(label, body):
            print(f"\n--- {label} ({len(body)} bytes)")
            for ins in D.iter_code(body, 0, len(body)):
                print(f"    {ins}")
        dump("ticker (the seated brain entry)", cb.ticker_body)
        dump("Main_Init prepend (the blackboard reset)", cb.main_init)
        for name, body in cb.duty_bodies.items():
            dump(f"{name}: tag-1 duty walk", body)
        for name, funcs in cb.action_funcs.items():
            for tag, body in funcs:
                dump(f"{name}: tag-{tag} body", body)
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
        if args.template and getattr(args, "template_layers", False):
            import os
            out_dir = os.path.dirname(args.png) or "."
            base = os.path.splitext(os.path.basename(args.png))[0]
            files = guide.render_paint_template_layers(g, fr, out_dir, basename=base)
            print(f"paint template: {len(files) - 1} layer PNGs + manifest -> {out_dir} "
                  f"(load {base}.manifest.json in your paint app)")
        elif args.template:
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
                         description=args.description,
                         preserve_existing=getattr(args, "preserve_existing", False))
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


def _cmd_paint_template(args: argparse.Namespace) -> int:
    """Project a field.toml's FLOOR + CONTENT onto per-layer trace-over paint-template PNGs (+ a legend).

    Unlike `guide` (camera-only), this reads the whole field: it resolves the camera, frames the floor,
    and projects every content marker (NPCs/props/gateways/events/save points/ladders/jumps/choices/
    waypoints/camera zones/spawn) -- so the artist sees where each thing lands + how tall to paint it.
    Works on a from-scratch field (full floor + content) or a fork (content overlay on the real art)."""
    import os

    from . import build
    from .scene import guide, paint
    try:
        project = build.FieldProject.load(args.field)
    except (OSError, ValueError, KeyError) as e:
        print(f"error: can't load {args.field}: {e}", file=sys.stderr)
        return 2
    try:
        cams = build.resolve_cameras(project)
    except build.BuildError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    if not cams:
        print("error: [camera] section is required", file=sys.stderr)
        return 2
    cam0 = cams[0]
    cfgs = build.camera_cfgs(project)
    c0 = cfgs[0] if cfgs else {}
    fr_cfg = c0.get("frame") or {}
    frame = None
    if "borrow" not in c0 or fr_cfg:                 # synth field, or a borrow with an explicit frame
        try:
            frame = guide.frame_floor(cam0, back_canvas_y=float(fr_cfg.get("back", 205)),
                                      front_canvas_y=float(fr_cfg.get("front", 432)))
        except ValueError as e:
            print(f"note: floor layers skipped ({e})", file=sys.stderr)
    scene_cfg = None                                 # the two-file split: <field>.scene.toml sibling
    if args.field.endswith(".field.toml"):
        spath = args.field[: -len(".field.toml")] + ".scene.toml"
        if os.path.isfile(spath):
            import tomllib
            with open(spath, "rb") as fh:
                scene_cfg = tomllib.load(fh)
    items = paint.normalize_content(project.raw, scene_cfg)
    walkmesh = None                                  # the field's REAL floor outline (forks / modeled)
    try:
        from .scene import bgi
        wm_cfg = project.raw.get("walkmesh", {}) or {}
        ref = wm_cfg.get("bgi") or wm_cfg.get("reference")   # a shipped/borrowed .bgi (forks)
        wm_bytes = project.path(ref).read_bytes() if ref else build.resolve_walkmesh(project, cam0)
        wmesh = bgi.BgiWalkmesh.from_bytes(wm_bytes)
        verts, tris = wmesh.world_verts(), [tuple(t.vtx) for t in wmesh.tris]
        if verts and tris:
            walkmesh = (verts, tris)
    except Exception:                                # no/odd walkmesh (e.g. BG-borrow only) -> skip the layer
        walkmesh = None
    out_dir = args.out or os.path.dirname(os.path.abspath(args.field)) or "."
    # a fork ships a composited background.png next to the field -> use it as the base layer so the
    # guides sit on the real art (not black). From-scratch fields have no background.png -> stays None.
    base_image = "background.png" if os.path.isfile(os.path.join(out_dir, "background.png")) else None
    files = paint.render_full_template(cam0, frame, items, out_dir, basename=args.basename,
                                       walkmesh=walkmesh, base_image=base_image)
    ntypes = len({it["type"] for it in items})
    print(f"paint template: {len(files) - 3} layer PNGs + legend + manifest + Photoshop importer -> {out_dir}")
    print(f"  {len(items)} content markers across {ntypes} types; in Photoshop run "
          f"{args.basename}.import.jsx (File > Scripts > Browse...) to load all layers, "
          f"{args.basename}.legend.json for names/heights")
    if len(cams) > 1:
        print(f"  note: field has {len(cams)} cameras; projected camera 0 only "
              "(per-camera fan-out is a follow-up)", file=sys.stderr)
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


def _cmd_gen_hub(args: argparse.Namespace) -> int:
    """Generate a World-Hub field.toml from a journeys.toml registry. Pure codegen (no game install): it
    emits a BG-borrow hub field whose narrator menu warps to each journey's entry. Build/deploy the emitted
    field.toml like any field. With --extract-camera the borrowed camera is cached for you (no manual step)."""
    from . import hub
    if args.extract_camera and not _has_unitypy():
        print("--extract-camera needs UnityPy (pip install UnityPy) + your FF9 install.", file=sys.stderr)
        return 2
    try:
        info = hub.generate(args.journeys, out_path=args.out, extract_camera=args.extract_camera,
                            game=args.game, force=args.force)
    except (OSError, ValueError, ConfigError) as e:    # HubError (a ValueError) + unreadable/parse/install errors
        print(str(e), file=sys.stderr)
        return 2
    spec = info["spec"]
    print(f"generated hub '{spec.name}' (id {spec.id}, {info['journeys']} journey(s)) -> {info['path']}")
    for j in spec.journeys:
        seed = f", seed {j.set_scenario}" if j.set_scenario is not None else ""
        print(f"  {j.name!r} -> field {j.entry}{seed}")
    for w in info.get("warnings", []):
        print(f"warning: {w}", file=sys.stderr)
    ex = info.get("extracted")
    if ex:
        verb = "reused cached" if ex.get("cached") else "extracted"
        print(f"camera: {verb} field {spec.borrow_field} -> {ex['camera']}")
        print(f"Next: `ff9mapkit build {info['path']}` (or tools/deploy_field.py) -- the camera is wired up.")
    else:
        print(f"Next: extract the borrowed camera ({spec.camera}) -- e.g. "
              f"`ff9mapkit extract-field <id>` or `gen-hub --extract-camera` -- then "
              f"`ff9mapkit build {info['path']}` (or tools/deploy_field.py).")
    return 0


def _cmd_lint_journey(args: argparse.Namespace) -> int:
    """Validate a multi-campaign journeys.toml offline: campaigns exist + parse, the GLOBAL id-disjointness
    guarantee (every campaign of every journey + bare entries share one EventDB namespace), flag windows fit,
    links resolve to real members + boundaries, entries valid, seeds in range. Pure (no game install)."""
    from . import journey
    try:
        manifest = journey.load_journeys(args.journeys)
        errors, warnings = journey.lint_manifest(manifest)
    except (journey.JourneyError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    if getattr(args, "graph", False):
        print(journey.render_journey_plan(manifest))
    for w in warnings:
        print("warning: " + w, file=sys.stderr)
    for e in errors:
        print("error: " + e, file=sys.stderr)
    n = len(manifest.journeys)
    if errors:
        print(f"journeys '{manifest.path.name}': FAILED -- {len(errors)} error(s), {len(warnings)} warning(s)",
              file=sys.stderr)
        return 2
    print(f"journeys '{manifest.path.name}' OK -- {n} journey(s), {len(warnings)} warning(s)")
    return 0


def _cmd_assemble_journey(args: argparse.Namespace) -> int:
    """Assemble a multi-campaign journeys.toml: lint it (the namespace guarantee), then emit the World-Hub
    field.toml resolving BOTH bare single-field and multi-campaign journeys (gen-hub handles only the bare
    form). Pure offline codegen -- build/deploy the emitted hub like any field; the per-campaign deploy +
    cross-campaign link wiring is the in-game step (tools/deploy_campaign.py per member, then the hub)."""
    from . import journey
    try:
        manifest = journey.load_journeys(args.journeys)
        if getattr(args, "graph", False) or args.dry_run:
            errors, warnings = journey.lint_manifest(manifest)
            for w in warnings:
                print("warning: " + w, file=sys.stderr)
            if errors:
                for e in errors:
                    print("error: " + e, file=sys.stderr)
                return 2
            print(journey.render_journey_plan(manifest))
            if args.dry_run:
                print("DRY-RUN -- no hub field.toml written. Drop --dry-run to emit it.")
                return 0
        if getattr(args, "extract_camera", False) and not _has_unitypy():
            print("--extract-camera needs UnityPy (pip install UnityPy) + your FF9 install.", file=sys.stderr)
            return 2
        info = journey.generate_hub(manifest.path, out_path=args.out,
                                    extract_camera=getattr(args, "extract_camera", False),
                                    game=getattr(args, "game", None), force=getattr(args, "force", False))
    except (journey.JourneyError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    spec = info["spec"]
    print(f"assembled hub '{spec.name}' (id {spec.id}, {len(spec.journeys)} journey(s)) -> {info['path']}")
    for j in spec.journeys:
        seed = f", seed {j.set_scenario}" if j.set_scenario is not None else ""
        print(f"  {j.name!r} -> field {j.entry}{seed}")
    for w in info.get("warnings", []):
        print("warning: " + w, file=sys.stderr)
    ex = info.get("extracted")
    if ex:
        print(f"camera: {'reused cached' if ex.get('cached') else 'extracted'} field {spec.borrow_field} "
              f"-> {ex['camera']}  (the hub [camera] borrow is wired up)")
    elif spec.borrow_field:
        print(f"Next: extract the hub camera -- `ff9mapkit assemble-journey {args.journeys} --extract-camera` "
              f"(or `ff9mapkit extract-field {spec.borrow_field}`) -- then build/deploy the hub.")
    print(f"Then build + deploy the hub (`tools/deploy_field.py {info['path']}`) + each campaign "
          f"(`tools/deploy_campaign.py --no-warp`); or run the whole journey with `tools/deploy_journey.py "
          f"{args.journeys} --apply`.")
    return 0


def _cmd_reference_arcs(args: argparse.Namespace) -> int:
    """The FF9 reference-arc scaffold -- the north-star planning + fork-and-test harness. List the curated
    arc->seed table, print the fork PLAYBOOK, or EMIT a multi-campaign journeys.toml laying the arcs out as a
    chained journey + the `import-chain` commands to fork each one. Pure offline (no game install). It is NOT
    a one-click rebuild of FF9 -- it's a PLAN you execute arc-by-arc (docs/FORK_FIDELITY.md)."""
    from pathlib import Path
    from . import refarc
    if args.reconcile:                              # STEP 2 -- operates on a journeys.toml, NOT an arc table
        jp = Path(args.reconcile)
        if not jp.is_file():
            print(f"{jp}: no such file", file=sys.stderr)
            return 2
        new_text, notes = refarc.reconcile_arc_journey(jp.read_text(encoding="utf-8"), jp.parent)
        for n in notes:
            print(f"  [{n.level}] {n.text}")
        if new_text == jp.read_text(encoding="utf-8"):
            print("nothing to fill (fork the campaigns first, or the entry/links are already set).")
            return 0
        jp.write_text(new_text, encoding="utf-8", newline="\n")
        print(f"wrote {jp}  (entry + links filled from the forked campaigns). Re-lint with `lint-journey`.")
        return 0
    if args.regen:                                  # REGENERATE the region PICKER's all-zones catalog
        if args.pattern and not args.out:           # a filtered regen must NOT clobber the shipped full catalog
            print("--pattern needs --out (a filtered catalog is a subset -- it would overwrite the shipped "
                  "all-zones catalog). Add --out <path>, or drop --pattern to refresh the full catalog.",
                  file=sys.stderr)
            return 2
        try:
            p, n = refarc.regenerate_region_catalog(out=args.out, pattern=args.pattern,
                       split_visits=not args.no_split_visits, gap=args.gap)
        except refarc.RefArcError as e:
            print(str(e), file=sys.stderr)
            return 2
        print(f"wrote {n} regions -> {p}")
        print("The region picker ('Browse FF9 regions' / 'Add region to arc') now reads this accurate, "
              "all-zones catalog (each zone -> its real entry seed).")
        return 0
    try:
        aset = refarc.load_reference_arcs(args.table)
    except (refarc.RefArcError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    if args.emit:
        out = Path(args.emit)
        out.mkdir(parents=True, exist_ok=True)
        jpath = out / "journeys.toml"
        if jpath.exists() and not args.force:
            print(f"{jpath} already exists (use --force to overwrite)", file=sys.stderr)
            return 2
        jpath.write_text(refarc.render_arc_journey_toml(
            aset, hub_name=args.hub_name, hub_id=args.hub_id, borrow_bg=args.borrow_bg, id_base=args.id_base),
            encoding="utf-8", newline="\n")
        print(f"wrote {jpath}  ({len(aset.arcs)} arcs, hub id {args.hub_id})")
        print("Next: fork each arc (the import-chain playbook is in the file header), fill the entry from "
              "the forked entry campaign (links auto-wire at deploy), then deploy (Build & Deploy -> this file, or "
              f"`py tools/deploy_journey.py {jpath.as_posix()} --apply`).")
        return 0
    if args.playbook:
        for i, (_arc, cmd) in enumerate(refarc.fork_playbook(aset, id_base=args.id_base), 1):
            print(f"{i:>2}. {cmd}")
        return 0
    print(f"{aset.title}  ({len(aset.arcs)} arcs, in story order):")
    for arc in aset.arcs:
        print(f"  {arc.key:<14} seed {arc.seed:<5} {arc.name}")
    print("\n--emit <dir> to scaffold a chained journeys.toml; --playbook for just the fork commands.")
    return 0


def _cmd_extract_field(args: argparse.Namespace) -> int:
    """Cache real FF9 fields' camera + walkmesh in the gitignored workspace cache, for reuse by BG-borrow
    tomls / `gen-hub --extract-camera`. Needs the install + UnityPy."""
    if not _has_unitypy():
        print("extract-field needs UnityPy (pip install UnityPy) + your FF9 install.", file=sys.stderr)
        return 2
    from . import extract
    rc = 0
    for fid in args.ids:
        try:
            res = extract.cache_field(fid, game=args.game, force=args.force)
        except (OSError, ValueError, ConfigError) as e:
            print(f"field {fid}: {e}", file=sys.stderr)
            rc = 1
            continue
        print(f"field {fid}: {'already cached' if res.get('cached') else 'extracted'} -> {res['camera']}")
    return rc


def _cmd_export_art(args: argparse.Namespace) -> int:
    """Assemble per-overlay background PNGs OFFLINE -- our own `[Export] Field=1`, no in-game hang.
    Targets: one field, a campaign.toml (every member's donor field), or --all."""
    if not _has_unitypy():
        print("export-art needs UnityPy (pip install UnityPy) + your FF9 install.", file=sys.stderr)
        return 2
    from . import extract
    _safe_console()
    write_atlas = not args.no_atlas
    comp = args.composite

    def progress(k, total, folder, summ, err):
        if err:
            print(f"  [{k}/{total}] {folder}: SKIP ({err})", file=sys.stderr)
        elif comp:
            print(f"  [{k}/{total}] {folder}: {summ['size'][0]}x{summ['size'][1]}")
        else:
            tag = "" if summ["atlas"] else " (no atlas)"
            print(f"  [{k}/{total}] {folder}: {summ['overlays']} overlays{tag}")

    try:
        if args.all:
            res = extract.export_all_art(args.out, game=args.game, pattern=args.pattern,
                                         write_atlas=write_atlas, composite=comp, on_field=progress)
        elif args.target and str(args.target).lower().endswith(".toml"):
            res = extract.export_campaign_art(args.target, args.out, game=args.game,
                                              write_atlas=write_atlas, composite=comp, on_field=progress)
        elif args.target:
            if comp:
                summ = extract.export_field_composite(args.target, args.out, game=args.game)
                print(f"{summ['folder']}: {summ['size'][0]}x{summ['size'][1]} background -> {summ['path']}")
            else:
                summ = extract.export_field_art(args.target, args.out, game=args.game, write_atlas=write_atlas)
                atxt = " + atlas.png" if summ["atlas"] else ""
                print(f"{summ['folder']}: {summ['overlays']} overlays ({summ['source']}){atxt} -> {summ['dir']}")
            return 0
        else:
            print("export-art: give a field, a campaign.toml, or --all", file=sys.stderr)
            return 2
    except (FileNotFoundError, ValueError, RuntimeError, ConfigError) as e:
        print(str(e), file=sys.stderr)
        return 2
    where = args.out or "<install>/StreamingAssets/FieldMaps"
    unit = "background PNG(s)" if comp else "overlays"
    print(f"\nexported {res['fields']}/{res['total']} field(s), {res['units']} {unit} -> {where}")
    if res["failed"]:
        print(f"  {len(res['failed'])} field(s) skipped (no readable art):", file=sys.stderr)
        for tok, err in res["failed"][:10]:
            print(f"    {tok}: {err}", file=sys.stderr)
    return 0 if res["fields"] else 1


def _cmd_repaint_native(args: argparse.Namespace) -> int:
    """SPATIAL<->ATLAS repaint round-trip for a NATIVE fork: unpack the tile-packed atlas.png into
    per-overlay spatial layers (default), or --pack the (edited) layers back into atlas.png. No game
    needed -- operates on the project's own scene.bgs.bytes + atlas.png (provenance-clean)."""
    from . import extract
    _safe_console()
    try:
        from PIL import Image  # noqa: F401, PLC0415 - the round-trip needs Pillow
    except ImportError:
        print("repaint-native needs Pillow (pip install Pillow).", file=sys.stderr)
        return 2
    try:
        if args.pack:
            res = extract.repack_native_atlas(args.project, args.from_dir, backup=not args.no_backup)
            for note in res["notes"]:
                print(f"  {note}")
            print(f"repacked {res['overlays_repacked']} layer(s), {res['cells_written']} tile(s) changed "
                  f"(TileSize {res['tile_size']}) -> {res['atlas']}")
            print("Next: deploy the project -> the repainted background shows in-game."
                  if res["cells_written"] else "No tiles changed (the layers match the atlas) -- nothing to do.")
        else:
            res = extract.export_native_repaint(args.project, args.out)
            print(f"unpacked {res['overlays']} layer(s) (TileSize {res['tile_size']}, atlas "
                  f"{res['atlas_size'][0]}x{res['atlas_size'][1]}) -> {res['dir']}")
            print(f"Next: repaint any Overlay*.png, then: ff9mapkit repaint-native {args.project} --pack")
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(str(e), file=sys.stderr)
        return 2
    return 0


def _cmd_import_all(args: argparse.Namespace) -> int:
    """Bulk-import a foldered, Blender-ready archive of fields -- whole game (--all), a zone (--pattern),
    or a campaign.toml. Lightweight model-against projects by default; --editable for repaintable scenes."""
    if not _has_unitypy():
        print("import-all needs UnityPy (pip install UnityPy) + your FF9 install.", file=sys.stderr)
        return 2
    from . import extract
    _safe_console()

    def progress(k, total, label, dest, err):
        if err:
            print(f"  [{k}/{total}] {label}: SKIP ({err})", file=sys.stderr)
        else:
            print(f"  [{k}/{total}] {label} -> {dest}")

    try:
        if args.target and str(args.target).lower().endswith(".toml"):
            res = extract.import_campaign_fields(args.target, args.out, game=args.game,
                                                 editable=args.editable, on_field=progress)
        elif args.all or args.pattern:
            res = extract.import_all(args.out, game=args.game, pattern=args.pattern,
                                     editable=args.editable, on_field=progress)
        else:
            print("import-all: give a campaign.toml, or --all (optionally --pattern <zone>)", file=sys.stderr)
            return 2
    except (FileNotFoundError, ValueError, RuntimeError, ConfigError) as e:
        print(str(e), file=sys.stderr)
        return 2
    mode = "editable" if args.editable else "lightweight"
    print(f"\nimported {res['fields']}/{res['total']} field(s) [{mode}] -> {args.out}")
    if res["failed"]:
        print(f"  {len(res['failed'])} field(s) skipped (no readable scene/art):", file=sys.stderr)
        for lbl, err in res["failed"][:10]:
            print(f"    {lbl}: {err}", file=sys.stderr)
    return 0 if res["fields"] else 1


def _cmd_pack(args: argparse.Namespace) -> int:
    from pathlib import Path
    from .pack import pack_mod
    name = (getattr(args, "name", None) or "").strip() or None
    out = args.out or ((name or Path(args.mod_root).resolve().name) + ".zip")
    try:
        z = pack_mod(args.mod_root, out, name=name)
    except FileNotFoundError as e:
        print(f"mod folder not found: {e}", file=sys.stderr)
        return 2
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"packed {args.mod_root} -> {z}")
    return 0


def _cmd_import(args: argparse.Namespace) -> int:
    from pathlib import Path
    from . import extract
    try:
        # A NAME token resolving to a SHARED FBG folder (~142 fields are the same room at another story
        # beat) picks ONE sibling silently -- warn up front (an `import <id>` pick is exact, no warning).
        _tok = str(args.field).strip()
        if not (_tok.isdigit() and int(_tok) in extract.ID_TO_FBG):
            try:
                _shared_folder, _ = extract.resolve_field(args.field, args.game)
                extract.warn_shared_fbg(_shared_folder)
            except (RuntimeError, FileNotFoundError, ValueError, OSError):
                pass           # unresolvable here -> the normal dispatch below surfaces the real error
        gpf = getattr(args, "graft_player_funcs", False)
        ct = getattr(args, "carry_text", False)
        sm = getattr(args, "save_moogle", False)
        if ct or sm:
            gpf = True             # text carry / save-moogle ride on the graft (the carried objects/funcs must exist)
        # #4 (FORK_FIDELITY.md): BG-borrow black-screens area<10 -- the engine builds 'FBG_N<area>' and reads
        # exactly 2 chars, so single-digit areas never resolve. The native path ships its own art at a remapped
        # area>=10 (seam-free + lit), so auto-route the default (borrow) path to native there -- this unblocks
        # forking the early-game fields (Alexandria area1, Cargo Ship area0) with a plain `import`.
        if getattr(args, "neutralize_gestures", False) and not getattr(args, "swap_player", None):
            print("--neutralize-gestures requires --swap-player (it rewrites the swapped rig's gestures)",
                  file=sys.stderr)
            return 2
        if getattr(args, "swap_player", None):
            from . import playerswap as _ps
            _ps.resolve_char(args.swap_player)   # fail fast on an unknown character (ValueError -> caught below)
            args.verbatim = True                 # the swap patches the donor's player entry -> needs the verbatim .eb
        if args.verbatim:
            args.native = True            # --verbatim ships the native scene + the donor's WHOLE .eb
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
        # A fork CARRIES its donor's dialogue, so it must sit on the DONOR's own text block -- exactly what
        # campaign.py's chain-fork path already does. Without this every `ff9mapkit import` emitted the shared
        # literal 1073 (Black Mage Village) and wrote the donor's text over that location's. Keeping the
        # donor's block is required, not merely tidy: voice-acting clips resolve off the same mesID and
        # UniversalTextId's dual-language remap is keyed by a table of real mesIDs.
        _tb = None
        try:
            from ._fieldtext import EVENT_ID_TO_MES as _E2M
            from .dialogue import _resolve_field_id as _rfi      # the SAME resolver extract records the donor with
            _tb = _E2M.get(int(_rfi(args.field)))
        except (RuntimeError, FileNotFoundError, ValueError, TypeError):
            pass                   # donor id unresolvable offline -> the build derives from the field id
        if args.native:
            meta, toml = extract.write_native_project(
                args.field, Path(args.out), name=args.name, field_id=args.id, game=args.game, text_block=_tb,
                graft_player_funcs=gpf, carry_text=ct, graft_savepoint=sm, verbatim=args.verbatim)
        elif args.editable:
            meta, toml = extract.write_editable_project(
                args.field, Path(args.out), name=args.name, field_id=args.id, game=args.game, text_block=_tb,
                graft_player_funcs=gpf, carry_text=ct, graft_savepoint=sm)
        else:
            meta, toml = extract.write_field_project(
                args.field, Path(args.out), name=args.name, field_id=args.id, text_block=_tb,
                game=args.game, want_atlas=args.atlas, graft_player_funcs=gpf, carry_text=ct, graft_savepoint=sm)
        args._swapped_to = None
        args._swap_gestures = 0
        if getattr(args, "swap_player", None):           # productionized Tier-A: walk as a different existing char
            from . import playerswap
            args._swapped_to, _ = playerswap.resolve_char(args.swap_player)
            args._swap_gestures = extract.apply_player_swap(
                toml, args._swapped_to, neutralize=getattr(args, "neutralize_gestures", False)) or 0
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    cm = meta["camera"]
    print(f"imported {meta['field']}  (area {meta['area']}, mapid {meta['mapid']})")
    if args.native:
        print("  mode   : NATIVE custom scene (atlas.png + .bgs, NO .bgx -- seamless per-tile render, Moguri-style)")
        print(f"  atlas  : {meta.get('atlas_source', '?')}")
        if args.verbatim:
            ic = meta.get("imported_content", {})
            n_exits = len(ic.get("field_exits", []))
            print(f"  logic  : VERBATIM .eb -- ships the field's REAL event script whole ({n_exits} Field() exit(s); "
                  "add a [startup] block to boot a beat). The declarative blocks are not used in this mode.")
            if ic.get("battle_bgm"):
                print(f"  bgm    : {ic['battle_bgm']} scripted battle(s) carry the donor's real battle theme "
                      "([[battle_bgm]] -> a scene-keyed Music: line; a mint would otherwise lose it)")
        if getattr(args, "_swapped_to", None):
            print(f"  player : SWAPPED -> you walk as {args._swapped_to} (SetModel + movement anims patched; "
                  "party/menu state unchanged)")
            if args._swap_gestures and getattr(args, "neutralize_gestures", False):
                print(f"  gesture: NEUTRALIZED {args._swap_gestures} scripted gesture(s) -> the rig's idle, so "
                      f"{args._swapped_to} STANDS cleanly through the cutscene (it won't emote -- for story "
                      "fidelity use a verbatim fork at the right beat). WaitAnimation timing left intact.")
            elif args._swap_gestures:
                print(f"  WARN   : the player plays {args._swap_gestures} scripted GESTURE(s) (RunAnimation) -- those "
                      f"reference the ORIGINAL rig and will glitch on {args._swapped_to} (only movement clips are "
                      "swapped). Add --neutralize-gestures to stand cleanly, or fork a free-roam field.")
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
    if ic and not ic.get("verbatim_eb"):          # verbatim mode has no declarative content summary (it's all .eb)
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
        if ic.get("gateway_carry"):
            bits.append(f"{ic['gateway_carry']} story-gated door(s) carried verbatim")
        print(f"  content: {', '.join(bits) if bits else 'none found in the source script'}"
              + ("   (gateways point at REAL fields -- retarget them)" if ic["gateways"] else ""))
        if ic.get("spawn_flash_fixed"):
            print("  note   : the save Moogle's spawn pose was normalised to its rest pose (no load flash on a fork)")
        if ic.get("spawn_flash"):
            print(f"  warning: {ic['spawn_flash']} carried object(s) spawn at a different pose than they rest -- they "
                  "may visibly snap to rest on a fork (the source field's entrance fade hides it). (docs/SAVEPOINT.md)")
        if ic.get("story_branch"):
            print(f"  warning: {ic['story_branch']} STORY-BRANCH door(s) share a zone (the real field selects one by "
                  "story flag).\n           Gate each with requires_flag in the field.toml, else both arm and you "
                  "hit the wrong exit. (FORK_FIDELITY.md #2)")
        if ic.get("gateway_gated_seam"):
            print(f"  warning: {ic['gateway_gated_seam']} story-gated door(s) reference sibling/cutscene logic and "
                  "couldn't be carried --\n           left as ungated seams (the gate is dropped); those refs ARE the "
                  "field's own event logic,\n           so use --verbatim for them. (Player-call doors DO carry with "
                  "--graft-player-funcs.) (FORK_FIDELITY.md #2b)")
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
    """Seed(s) -> field-id list. Accepts a COMMA-SEPARATED list of tokens; each token is a numeric field id
    OR an FBG substring that seeds EVERY matching field (e.g. 'iccv' = the whole Ice Cavern zone). Several
    tokens fork multiple zones as ONE campaign (with --whole-zone -> cross-zone warps auto-retarget in-fork);
    seeds keep token order (so the first stays the campaign entry) and are de-duplicated."""
    from . import extract
    out: list[int] = []
    seen: set = set()
    for tok in seed.split(","):
        s = tok.strip()
        if not s:
            continue
        if s.lstrip("-").isdigit():
            ids = [int(s)]
        else:
            sl = s.lower()
            ids = sorted(fid for fid, folder in extract.ID_TO_FBG.items() if sl in folder)
            if not ids:
                raise FileNotFoundError(f"no field id or FBG folder matches seed token {s!r}")
        for fid in ids:
            if fid not in seen:
                seen.add(fid)
                out.append(fid)
    if not out:
        raise FileNotFoundError(f"no field id or FBG folder matches seed {seed!r}")
    return out


def _deploy_cfg():
    """The worktree's .ff9deploy.toml (mod_folder + campaign_id_base defaults), or {}."""
    import tomllib
    from pathlib import Path
    f = Path(__file__).resolve().parents[2] / ".ff9deploy.toml"
    try:
        return tomllib.loads(f.read_text(encoding="utf-8")) if f.is_file() else {}
    except Exception:
        return {}


def _print_campaign_summary(plan, out_dir, *, verbatim=False):
    n = len(plan.members)
    ids = f"{plan.members[0].new_id}-{plan.members[-1].new_id}" if n else "-"
    sc = sum(1 for e in plan.edges if e["story_conditional"])
    mode = "VERBATIM (whole donor .eb + .mes, real logic)" if verbatim else "declarative"
    print(f"{n} fields forked [{mode}] into {out_dir} (ids {ids}); "
          f"{len(plan.edges)} in-chain gateways retargeted.")
    if sc:
        print(f"  {sc} STORY-COND edge(s) flagged -- add requires_flag (see campaign.toml).")
    if plan.seams:
        kinds = {}
        for s in plan.seams:
            kinds[s["kind"]] = kinds.get(s["kind"], 0) + 1
        print("  " + str(len(plan.seams)) + " seam(s): " + ", ".join(f"{v} {k}" for k, v in sorted(kinds.items())))
    degraded = set(getattr(plan, "verbatim_degraded", []) or [])
    if degraded:                                  # verbatim members that lost their .eb (no native atlas)
        print(f"  {len(degraded)} member(s) fell back to DECLARATIVE -- NOT verbatim (no native atlas; "
              f"re-synthesized logic, no real .eb): " + " ".join(sorted(degraded)))
    plain_export = [n for n in plan.needs_export if n not in degraded]
    if plain_export:
        print(f"  {len(plain_export)} member(s) NEED an in-game [Export] before deploy: "
              + " ".join(plain_export))
    swap = getattr(plan, "swap_player", None)
    if swap:                                      # --swap-player: walk as one char across the chain
        gw = getattr(plan, "swap_gesture_warn", {}) or {}
        sk = getattr(plan, "swap_skipped", []) or []
        swapped_n = sum(1 for m in plan.members if m.name not in sk and m.name not in degraded)
        print(f"  PLAYER SWAP: you walk as {swap} across the chain ({swapped_n} verbatim member(s) swapped).")
        if sk:
            print(f"    {len(sk)} member(s) had no swappable player entry -- left as the donor's: " + " ".join(sorted(sk)))
        if gw:
            tot = sum(gw.values())
            if getattr(plan, "neutralized", False):
                print(f"    NEUTRALIZED {tot} scripted gesture(s) across {len(gw)} member(s) -> {swap}'s idle "
                      f"(stands cleanly through the cutscenes): " + " ".join(sorted(gw)))
            else:
                print(f"    WARN: {len(gw)} member(s) play {tot} scripted GESTURE(s) that will glitch on {swap} "
                      f"(cutscene fields; only movement clips are swapped). Add --neutralize-gestures: "
                      + " ".join(sorted(gw)))
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
    print(f"Next: add '{plan.mod_folder}' to Memoria.ini [Mod] FolderNames AND Priorities (same order; "
          f"the launcher rewrites FolderNames from Priorities) + relaunch, then deploy-all (P4).")
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
    if getattr(args, "neutralize_gestures", False) and not getattr(args, "swap_player", None):
        print("--neutralize-gestures requires --swap-player (it rewrites the swapped rig's gestures)",
              file=sys.stderr)
        return 2
    if getattr(args, "swap_player", None):       # validate the char + force verbatim BEFORE the (costly) walk
        from . import playerswap
        try:
            playerswap.resolve_char(args.swap_player)
        except ValueError as e:
            print(str(e), file=sys.stderr)
            return 2
        args.verbatim = True                     # the swap patches each member's donor player entry
    try:
        seeds = _resolve_chain_seeds(args.seed, game=args.game)
        bundle = extract.EventBundle(game=args.game)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2

    restrict_ids = None                           # set by --ids: bound the walk to exactly the cluster
    if getattr(args, "ids", None) and getattr(args, "whole_zone", False):
        print("--ids and --whole-zone are mutually exclusive (--ids forks an explicit cluster; --whole-zone "
              "forks the whole zone)", file=sys.stderr)
        return 2
    if getattr(args, "ids", None):                # fork EXACTLY this id set -> scope to one story-state cluster
        try:
            want = chain.parse_id_ranges(args.ids)
        except ValueError as e:
            print(f"--ids: {e}", file=sys.stderr)
            return 2
        live = extract.build_field_index(args.game, verbose=False)   # folder_lower -> bundle (LIVE-forkable only)
        missing = [fid for fid in want if fid not in extract.ID_TO_FBG]
        if missing:
            print(f"--ids: {len(missing)} id(s) have no background field and were dropped: "
                  f"{chain.format_id_ranges(missing)}", file=sys.stderr)
        not_live = [fid for fid in want if fid in extract.ID_TO_FBG and fid not in seeds
                    and extract.ID_TO_FBG[fid].lower() not in live]   # in the static table but no install bundle
        if not_live:
            print(f"--ids: {len(not_live)} id(s) have no live background bundle in this install and were "
                  f"dropped: {chain.format_id_ranges(not_live)}", file=sys.stderr)
        extra = sorted(fid for fid in want if fid not in seeds
                       and fid in extract.ID_TO_FBG
                       and extract.ID_TO_FBG[fid].lower() in live)    # skip table-only variants with NO live bundle
        seeds = seeds + extra                     # original seed(s) FIRST -> entry_field stays the intended entry
        restrict_ids = set(seeds)                 # bound the BFS to the cluster so a door can't pull in a
        #                                           same-zone sibling visit (the leak finding #1 fix)
        args.max_fields = max(args.max_fields, len(seeds))           # never truncate the cluster we asked for
    elif getattr(args, "whole_zone", False):     # seed EVERY forkable field in the seed's zone(s) -> the whole
        live = extract.build_field_index(args.game, verbose=False)   # folder_lower -> bundle (LIVE-forkable only)
        seed_zones = {chain.zone_label(extract.ID_TO_FBG[s])          # zone forks, not just the door-reachable
                      for s in seeds if s in extract.ID_TO_FBG}       # slice (cutscene-only screens included)
        extra = sorted(fid for fid, folder in extract.ID_TO_FBG.items()
                       if chain.zone_label(folder) in seed_zones and fid not in seeds
                       and folder.lower() in live)                    # skip table-only variants with NO live bundle
        seeds = seeds + extra                     # original seed(s) FIRST -> entry_field stays the intended entry
        args.max_fields = max(args.max_fields, len(seeds))           # never truncate the zone we asked for

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
                        stop_at_zone_boundary=not args.cross_zones, restrict_ids=restrict_ids)

    def _zone_members(z):                         # all forkable fields in a zone (for the coverage hint)
        return [fid for fid, folder in extract.ID_TO_FBG.items() if chain.zone_label(folder) == z]
    # the coverage hint nudges toward --whole-zone for an under-forked zone; with --ids the partial fork is
    # DELIBERATE (one story-state cluster), so the "you missed 30 fields" nudge would be misleading -> skip it.
    coverage = {} if restrict_ids is not None else chain.zone_coverage(result, _zone_members)

    if args.out:                                  # P2 write mode: fork the chain into campaign/
        from . import campaign
        cfg = _deploy_cfg()
        id_base = args.id_base if args.id_base is not None else int(cfg.get("campaign_id_base", 6000))
        mod_folder = args.mod_folder or cfg.get("mod_folder") or "FF9CustomMap-ow"
        seed_zone = chain.zone_label(extract.ID_TO_FBG.get(seeds[0]))
        cname = args.campaign_name or f"{seed_zone.upper()}_CAMPAIGN"  # --swap-player validated at fn top (fail-fast)
        # STABLE-ID mode: a re-fork reuses the EXISTING <out>/campaign.toml's donor->id+name map so an in-fork
        # SAVE survives (default ON when --out already holds one; --fresh-ids opts out). Same dir only -- the
        # carried member files live under --out, so reuse and re-fork share one tree.
        prior_plan = None
        prior_src = Path(args.out) / "campaign.toml"
        if not getattr(args, "fresh_ids", False) and prior_src.exists():
            try:
                prior_plan = campaign.load_campaign(prior_src)
            except Exception as e:                       # a corrupt/non-manifest toml -> fall back to fresh ids
                print(f"warn: could not read {prior_src} for stable ids ({e}); allocating FRESH ids "
                      f"(re-fork will shift them -- stale in-fork saves)", file=sys.stderr)
        if prior_plan is not None:
            # Loud guards: silently reusing the WRONG prior, or changing the flag geometry, corrupts saves.
            if prior_plan.name and prior_plan.name != cname:
                print(f"warn: --out holds campaign '{prior_plan.name}' but this fork is '{cname}' -- reusing its "
                      f"ids for stable allocation. If that's not the same campaign, use --fresh-ids or a clean "
                      f"--out.", file=sys.stderr)
            if prior_plan.flag_base != args.flag_base or prior_plan.flags_per_field != args.flags_per_field:
                print(f"warn: flag geometry changed (prior flag_base={prior_plan.flag_base}/"
                      f"per_field={prior_plan.flags_per_field} -> now {args.flag_base}/{args.flags_per_field}); "
                      f"ids stay stable but EVERY member's story-flag window shifts -- in-fork save flags will "
                      f"desync. Keep them equal to preserve saves.", file=sys.stderr)
        try:
            plan = campaign.write_campaign(result, Path(args.out), id_base=id_base,
                        flag_base=args.flag_base, flags_per_field=args.flags_per_field,
                        name=cname, mod_folder=mod_folder, game=args.game, live_seams=args.live_seams,
                        verbatim=args.verbatim, swap_player=getattr(args, "swap_player", None),
                        neutralize_gestures=getattr(args, "neutralize_gestures", False),
                        name_prefix=getattr(args, "name_prefix", "") or "", prior_plan=prior_plan)
        except (RuntimeError, FileNotFoundError, ValueError) as e:
            print(str(e), file=sys.stderr)
            return 2
        if prior_plan is not None:
            real_priors = sum(1 for m in prior_plan.members if m.real_id)
            print(f"stable-ids: reused {len(plan.reused_ids)} prior id(s) from {prior_src}"
                  + (f", appended {len(plan.appended_ids)} new (>{max([m.new_id for m in prior_plan.members], default=0)})"
                     if plan.appended_ids else "")
                  + (f", carried {len(plan.carried)} not-re-discovered ({', '.join(plan.carried)})" if plan.carried else "")
                  + " -- in-fork saves survive this re-fork.")
            if real_priors and not plan.reused_ids:      # nothing matched -> almost certainly the wrong manifest
                print(f"  warn: 0 of {real_priors} prior donor(s) were re-discovered -- '{prior_src}' looks like a "
                      f"DIFFERENT campaign. If so, use --fresh-ids or a clean --out (else its ids leak in).",
                      file=sys.stderr)
            for nm, fid in plan.carried_missing:
                print(f"  warn: prior member {nm} (id {fid}) has no files on disk -- dropped; later members' "
                      f"flag windows may shift. Re-append it or restore its dir.", file=sys.stderr)
        _print_campaign_summary(plan, args.out, verbatim=args.verbatim)
        cov_lines = chain.render_coverage(coverage)
        if cov_lines:
            print("\nUNDER-FORKED ZONES (the bytes are there -- re-fork with --whole-zone to capture them):")
            print("\n".join(cov_lines))
        return 0

    print(chain.render(result, label_fn=_chain_label_fn(game=args.game), coverage=coverage))
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
        if s.get("mes_note"):
            print(f"warning: {s['mes_note']}", file=sys.stderr)
    print(f"  wrote  : {toml}  (+ {meta['bbg']}.fbx + image#.png"
          f"{' + scene/' if meta.get('scene') else ''})")
    nxt = ("edit %s.fbx in Blender / repaint PNGs, then: ff9mapkit battle-build %s" % (meta['bbg'], toml))
    if meta.get("scene"):
        nxt += "  then  py tools/deploy_battle.py %s --trigger-field 5000  (relaunch + walk)" % toml
    print(f"Next: {nxt}")
    return 0


def _cmd_model_export(args: argparse.Namespace) -> int:
    from pathlib import Path
    from .models import export as mexport
    try:
        if args.deploy:
            meta = mexport.deploy_override(args.model, args.deploy, game=args.game)
            print(f"deployed {meta['geo']} (id {meta['geo_id']}) -> {meta['path']}")
            print(f"  euler round-trip max err {meta['euler_max_err']:.1e} (0.0 = exact)")
            _print_model_notes(meta["geo"], minted=False, merge_warnings=meta.get("merge_warnings"))
            print("Next: ~ -> Reload field (or warp to a field that uses this model) and confirm it "
                  "renders + animates IDENTICALLY. Revert by deleting that Models/<type>/<id>/ subfolder.")
            return 0
        meta = mexport.export_model(args.model, Path(args.out), game=args.game, flat=args.flat)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"exported {meta['geo']} (id {meta['geo_id']}, type {meta['type_int']}): "
          f"{meta['meshes']} mesh / {meta['verts']} verts / {meta['bones']} bones / "
          f"{len(meta['textures'])} texture(s)")
    print(f"  euler round-trip max err {meta['euler_max_err']:.1e} (0.0 = exact)")
    print(f"  wrote: {meta['fbx']}")
    print(f"To override this model in-game (no DLL), place it at:  <modfolder>/{meta['engine_path']}")
    _print_model_notes(meta["geo"], minted=False, merge_warnings=meta.get("merge_warnings"))
    return 0


def _print_model_notes(geo, *, minted, merge_warnings=None):
    """Surface the merge warnings + the engine appearance-logic notes (THE RULE: name-keyed engine appearance
    is preserved by an OVERRIDE, bypassed by a MINT; a story-evolved character is several ids) + the overworld
    guidance for a world-form model (a different in-game surface than a field)."""
    from . import catalog as C
    from .models import appearance
    for w in (merge_warnings or []):
        print(f"  WARN: {w}")
    for note in appearance.appearance_notes(geo, minted=minted):
        print(f"  NOTE: {note}")
    m = C.model(geo)
    if m is not None and m.form[:1] == "W":
        who = C.world_character(geo) or C.world_role(geo)
        print(f"  NOTE: OVERWORLD model ({who + ' -- ' if who else ''}world-map actor) -- reskin AND .anim edits "
              f"are both DLL-free here (same loose-FBX/.anim path as a field). See it on the WORLD MAP (~ -> "
              f"warp to a field, then walk out to the overworld), not a field reload. CAVEAT: the Bee / "
              f"Chocobo-minigame scene uses bundled clips, so an .anim edit won't show THERE (the mesh will).")


def _cmd_model_mint(args: argparse.Namespace) -> int:
    """Mint a NEW additive GEO model id (a fresh SetModel target, not an override) -- DLL-free."""
    from pathlib import Path
    from .models import mint as mmint
    try:
        if args.deploy:
            man = mmint.deploy_mint(args.source, args.id, args.deploy, args.name, game=args.game)
            where = "--deploy MODFOLDER"
        else:
            man = mmint.mint_manifest(args.source, args.id, args.name, game=args.game)
            from .models import export as mexport
            dest = Path(args.out).joinpath(*mexport.model_dir_parts(man["type_int"], man["id"]))
            mmint.export_mint(args.source, args.id, dest, new_name=man["name"], game=args.game)
            man["fbx"] = str(dest / f"{man['id']}.fbx")
            where = args.out
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"minted GEO id {man['id']} = {man['name']} (type {man['type_int']}) from {man['source']}")
    print(f"  wrote: {man['fbx']}  (into {where})")
    print(f"  register it with this DictionaryPatch line:  {man['directive']}")
    if args.deploy:
        print(f"  (appended to {man['dictionary_patch']})")
    print(f"  place it:  [[npc]] model = {man['id']}   (borrows {man['anims_from']}'s animset by name)")
    print("  RELAUNCH FF9 to register the new id (a 3DModel line is read at launch, like a FieldScene line).")
    _print_model_notes(man["source"], minted=True, merge_warnings=man.get("merge_warnings"))
    return 0


def _cmd_model_gltf(args: argparse.Namespace) -> int:
    """Export a real FF9 model + its animations to a Blender-openable glTF (.glb)."""
    from .models import gltf as mgltf
    out = args.out or f"{str(args.model).replace('/', '_')}.glb"
    try:
        man = mgltf.export_gltf(args.model, out, anims=args.anims, scale=args.scale, game=args.game,
                                bone_labels=not getattr(args, "plain_bones", False))
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"exported {man['geo']} (id {man['geo_id']}) -> {man['path']}")
    nlab = man.get("bone_labels") or 0
    if nlab:
        print(f"  bones wear anatomical display labels (bone012_R_hand -- {nlab} labeled; cosmetic only, "
              f"--plain-bones for raw names)")
    print(f"  {man['bones']} bones / {man['meshes']} mesh part(s) / {man['verts']} verts / "
          f"{man['textures']} texture(s) / anims: {', '.join(man['anims']) or 'none'}")
    for d in man.get("donor_anims") or []:
        who = d["model"] or "model %s" % d["folder"]
        print(f"  donor clips: {', '.join(d['labels'])} <- Animations/{d['folder']}/ ({who}'s folder -- the "
              f"engine's AnimationDB redirect; clips bind by bone name, so a same-rig donor clip plays cleanly)")
    print(f"  (each part is a SEPARATE named object in Blender -- edit one without disturbing the others)")
    for w in man.get("warnings", []):
        print(f"  WARN: {w}")
    _print_model_notes(man["geo"], minted=False, merge_warnings=None)
    print("Open in Blender: File > Import > glTF 2.0. It comes in rigged + textured; switch to the Animation "
          "workspace + pick an Action to scrub a clip. (Model is Y-up, ~scale 0.01 of FF9 units.)")
    return 0


def _cmd_model_anim_new(args: argparse.Namespace) -> int:
    """Author a wholly NEW animation clip (not an edit): from a Blender .glb action, or the built-in
    spin template (the no-Blender demo). Registers it via a 3DModelAnimation DictionaryPatch line."""
    from .models import anim as manim
    from .models import extract as mextract
    try:
        model = mextract.read_model(args.model, game=args.game)
        warns: list = []
        if args.glb:
            if not args.action:
                print("--glb needs --action <the Blender action/animation name>", file=sys.stderr)
                return 2
            from .models import _gltf_io
            gltf, blob = _gltf_io.read_glb(args.glb)
            parsed = manim.parse_gltf_animations(gltf, blob)
            hit = next((pa for pa in parsed if (pa.get("label") or "") == args.action), None)
            if hit is None:
                labels = ", ".join(str(pa.get("label")) for pa in parsed) or "none"
                print(f"no animation named {args.action!r} in {args.glb} (found: {labels})", file=sys.stderr)
                return 2
            clip = manim.new_clip(model["bones"], hit["bones"], name=args.suffix.lower(),
                                  warn=warns.append)
        else:
            b0 = next((b for b in model["bones"] if b["name"] == "bone000"), None)
            rest = tuple(b0["rot"]) if b0 and b0.get("rot") else None   # compose the yaw onto the real rest
            clip = manim.new_clip(model["bones"], manim.synth_spin_curves(rest=rest),
                                  name=args.suffix.lower(), warn=warns.append)
        man = manim.deploy_new_anim(args.model, clip, args.deploy, key=args.key,
                                    suffix=args.suffix, game=args.game)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    for w in warns:
        print(f"  WARN: {w}")
    print(f"new clip {man['name']} (key {man['key']}) -> {man['path']}")
    print(f"  registered: {man['directive']}  (in {man['dictionary_patch']})")
    print(f"Play it anywhere an anim id goes -- e.g. [[npc]] anims = {{ stand = {man['key']} }} or a "
          f"cutscene animation step. RELAUNCH to register the key (DictionaryPatch loads at startup).")
    return 0


def _cmd_summon_export(args: argparse.Namespace) -> int:
    """Export a stock summon creature's ef###.bytes -> a Blender-openable .glb (rig + skin + clips).
    Output is LOCAL-ONLY by design (a stock-creature export is Square-Enix content -- see summons/export.py)."""
    from pathlib import Path

    from .summons import export as sx
    geo = args.geo or f"SUMMON_{Path(args.ef).stem.upper()}"
    out = args.out or str(sx.default_out(args.ef))
    try:
        man = sx.export_summon_glb(args.ef, out, geo=geo, geo_id=args.id, anims=args.anims,
                                   scale=args.scale, rest=args.rest, fps=args.fps,
                                   textures=not args.no_textures)
    except (sx.SummonExportError, RuntimeError, FileNotFoundError, OSError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    cr = man["creature"]
    print(f"exported {man['geo']} -> {man['path']}")
    print(f"  {man['bones']} bones / {cr['meshes']} mesh part(s) / {man['verts']} verts / "
          f"rest={man['rest']} / clips: {len(man['clip_frames'])} {man['clip_frames'] or '(none)'}")
    print(f"  textures: {man['textures']} page(s) decoded"
          if cr.get("textured") else "  textures: none (untextured export)")
    for w in man.get("warnings") or []:
        print(f"  ! {w}")
    print("LOCAL-ONLY by design: a stock summon export is Square-Enix content -- it stays under "
          f"{sx.DEFAULT_OUT_DIR} (never the repo / a mod folder / the install).")
    print("Open in Blender: File > Import > glTF 2.0 (rigged; switch to Animation + pick an Action to scrub "
          "a clip). Model is Y-up, ~scale 0.01 of FF9 units.")
    return 0


def _cmd_summon_rig_ref(args: argparse.Namespace) -> int:
    """Export ONLY a summon's rig reference -> a .glb skeleton (bone000..bone09N, no mesh, no clips) to skin
    your own mesh onto. Output is LOCAL-ONLY by design (still stock-derived -- see summons/export.py)."""
    from pathlib import Path

    from .summons import export as sx
    geo = args.geo or f"SUMMON_{Path(args.ef).stem.upper()}"
    out = args.out or str(sx.default_out(args.ef, rig=True))
    try:
        man = sx.export_rig_ref(args.ef, out, geo=geo, geo_id=args.id, rest=args.rest)
    except (sx.SummonExportError, RuntimeError, FileNotFoundError, OSError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"exported rig reference {man['geo']} -> {man['path']}")
    print(f"  {man['bones']} bones (bone000..bone{man['bones'] - 1:03d}), rest={man['rest']}, no mesh, "
          f"no clips -- the armature to skin your mesh onto")
    print("LOCAL-ONLY by design: the rig is derived from a stock creature -- it stays under "
          f"{sx.DEFAULT_OUT_DIR} (never the repo / a mod folder / the install).")
    print("Open in Blender, skin your mesh onto these bones (KEEP the boneNNN names + hierarchy), then it "
          "binds the dragon's motion by bone name for the transplant.")
    return 0


def _summon_lanes():
    from .summons.deploy import LANES
    return LANES


def _rebase_summon_paths(block: dict, base_dir) -> dict:
    """Resolve a ``--from-toml`` block's RELATIVE file paths against the TOML's own directory.

    The block-schema layer already documents this rule ("a bare name resolves under the field's asset
    dir" -- ``content/summon.py:_path_problems``), and ``ff9mapkit lint``/``build`` honour it via
    ``base_dir``. The standalone deploy verbs read the same block and hand it to
    ``deploy.normalize_spec``, which takes paths VERBATIM -- so before this, a block that linted green
    died at emit ("model FBX not found") the moment the caller's cwd was not the TOML's folder. Absolute
    paths are left alone; ``clips`` is only rebased when it carries authored paths rather than the donor
    index selector."""
    from pathlib import Path as _P

    from .summons import deploy as _sd

    base = _P(base_dir)

    def one(v):
        p = _P(str(v))
        return str(p if p.is_absolute() else base / p)

    out = dict(block)
    for key in ("model", "sequence", "short_sequence"):
        if out.get(key):
            out[key] = one(out[key])
    for key in ("particles", "textures"):
        if out.get(key):
            out[key] = [one(v) for v in out[key]]
    if _sd.authored_clip_paths(out.get("clips")) is not None and out.get("clips"):
        out["clips"] = [one(v) for v in out["clips"]]
    return out


def _summon_block_from_args(args: argparse.Namespace) -> dict:
    """Build a ``[[summon]]`` block dict from the shared summon CLI flags (donor/lane/id/name/... ).
    A ``--from-toml`` overrides everything with the first ``[[summon]]`` table in a TOML file."""
    if getattr(args, "from_toml", None):
        try:
            import tomllib
        except ModuleNotFoundError as e:                     # pragma: no cover - py<3.11
            raise SystemExit(f"--from-toml needs Python 3.11+ (tomllib): {e}")
        from pathlib import Path as _P
        src = _P(args.from_toml)
        doc = tomllib.loads(src.read_text(encoding="utf-8"))
        blocks = doc.get("summon")
        if not blocks:
            raise SystemExit(f"{args.from_toml} has no [[summon]] block")
        block = dict(blocks[0] if isinstance(blocks, list) else blocks)
        block = _rebase_summon_paths(block, src.resolve().parent)
    else:
        block = {"donor": args.donor, "lane": args.lane}
        if getattr(args, "model", None):
            block["model"] = args.model
        if getattr(args, "textures", None):
            block["textures"] = [t for t in args.textures.split(",") if t.strip()]
        if args.id is not None:
            block["id"] = args.id
        if args.name:
            block["name"] = args.name
        if args.group:
            block["group"] = args.group
        if args.private_ef is not None:
            block["private_ef"] = args.private_ef
        if args.node_count is not None:
            block["node_count"] = args.node_count
        if args.hide_mask:
            block["hide_mask"] = args.hide_mask
        if getattr(args, "hide_meshes", None):
            block["hide_meshes"] = [k for k in args.hide_meshes.split(",") if k.strip()]
        if getattr(args, "clips", None):
            block["clips"] = args.clips
    # The deploy engine (summons.deploy) takes a NUMERIC donor only; a name ("Bahamut__Full") is the
    # block-schema layer's to resolve (content.summon.resolve_donor). build/lint route through it, but
    # these standalone deploy verbs otherwise call deploy.deploy()/stage_import() -> normalize_spec
    # directly, so a DOCUMENTED name-donor block passes lint and then dies at deploy. Resolve it here.
    if "donor" in block:
        from .content import summon as _summon
        try:
            block["donor"], _ = _summon.resolve_donor(block["donor"])
        except _summon.SummonBlockError as e:
            raise SystemExit(str(e))
    return block


def _cmd_summon_import(args: argparse.Namespace) -> int:
    """Package the user's OWN retargeted summon model (a Blender .glb from summon-rig-ref, or a ready .fbx)
    into their mod folder -- the reverse of the export guard. Validates the bone000..092 rig, mints the
    GEO id, deploys the host .seq (+ overlay clips/manifest for lane=overlay). Hybrid lane still needs the
    explicit `summon-deploy --arm` step to write [SfxHybrid]."""
    from . import config
    from .summons import deploy as sd
    block = _summon_block_from_args(args)
    block.pop("model", None)                                  # the model is the positional arg here
    try:
        game = config.find_game_path(getattr(args, "game", None))
        mod_root = config.find_mod_root(game, args.mod_folder)
        res = sd.stage_import(args.model_file, block, game=str(game), mod_root=mod_root,
                              dry_run=args.dry_run, scale=args.scale)
    except (sd.SummonDeployError, ValueError, FileNotFoundError, OSError) as e:
        print(str(e), file=sys.stderr)
        return 2
    spec = res["spec"]
    print(f"summon-import: {res['imported_from']} -> {spec['name']} (id {spec['id']}), lane={res['lane']}"
          + ("  *** DRY RUN (staged, live mod folder untouched) ***" if res["dry_run"] else ""))
    print(f"  model    : {res['mint']['fbx_dest']}")
    # Same honesty fix as _cmd_summon_deploy below: an AUTHORED (`sequence=`) block normalizes
    # `donor = None` (Finding 8) -- print that, not a bare "donor None".
    origin = "authored cast (no donor)" if spec.get("sequence") else f"donor {spec['donor']}"
    print(f"  host .seq: {res['seq']['seq_dest']}  (private ef{spec['private_ef']:03d}, {origin})")
    if res["lane"] == "overlay":
        print(f"  overlay  : {len(res['overlay']['clips'])} clip(s) + .sfxmodel + FileList.txt")
    if res["mint"]["directive_added"]:
        print("  *** NEW GEO id -- RELAUNCH FF9 to register the 3DModel line. ***")
    if res["lane"] == "hybrid":
        print("  next: `ff9mapkit summon-deploy --arm ...` to write [SfxHybrid] (needs the s58 engine), then "
              "point a summon ability's vfx1 at the private ef.")
    print(f"  revert   : {res['revert_script']}")
    return 0


def _cmd_summon_deploy(args: argparse.Namespace) -> int:
    """Deploy a [[summon]] transplant (assets) and, with --arm, ARM Memoria.ini [SfxHybrid] (hybrid lane).
    The asset emit is the same as a block build; the engine-arm is the confirm-first step (it mutates the
    live Memoria.ini, needs the s58 SfxHybridDrive engine, and needs a relaunch). Standalone (flags or
    --from-toml)."""
    from . import config
    from .summons import deploy as sd
    block = _summon_block_from_args(args)
    if not block.get("model"):
        print("summon-deploy needs a model: pass --model <fbx> (or --from-toml a block with `model`)",
              file=sys.stderr)
        return 2
    try:
        game = config.find_game_path(getattr(args, "game", None))
        mod_root = None if args.dry_run else config.find_mod_root(game, args.mod_folder)
        res = sd.deploy(block, game=str(game), mod_root=mod_root, arm=args.arm, dry_run=args.dry_run)
    except (sd.SummonDeployError, ValueError, FileNotFoundError, OSError) as e:
        print(str(e), file=sys.stderr)
        return 2
    spec = res["spec"]
    # An AUTHORED cast has no donor at all -- `spec['donor']` is only ever the schema default there, and
    # printing "donor 227" on a 100%-original summon receipt is a lie the reader would act on.
    origin = "authored cast (no donor)" if spec.get("sequence") else f"donor {spec['donor']}"
    print(f"summon-deploy: {spec['name']} (id {spec['id']}), lane={res['lane']}, {origin}, "
          f"private ef{spec['private_ef']:03d}"
          + ("  *** DRY RUN (staged under SCRATCH) ***" if res["dry_run"] else ""))
    print(f"  mod folder: {res['mod_root']}")
    print(f"  model     : {res['mint']['fbx_dest']}")
    print(f"  host .seq : {res['seq']['seq_dest']}")
    if res["lane"] == "overlay":
        print(f"  overlay   : {len(res['overlay']['clips'])} clip(s) + .sfxmodel + FileList.txt (DLL-free)")
    if res.get("armed"):
        print("  [SfxHybrid]: ARMED (Memoria.ini backed up) -- RELAUNCH to apply.")
    if res["mint"]["directive_added"]:
        print("  *** NEW GEO id -- RELAUNCH FF9 to register the 3DModel line. ***")
    print("  Reminder: point a summon ability's vfx1 at the private ef (this verb never edits Actions.csv).")
    print(f"  revert    : {res['revert_script']}")
    return 0


def _cmd_summon_seq_lint(args: argparse.Namespace) -> int:
    """Lint a hand-authored SFX .seq (and any .sfxmodel beside it) -- THE SILENT-SKIP GUARD. The engine
    drops an unknown operation and ignores an unknown argument key with no log at all, so a typo in a cast
    is invisible until a playtest. Also checks the study's mechanically-expressible laws (PHASE-LOCK,
    FIGURE-VISIBILITY, INTENSITY, ANIM=IDLE RELEASE) and refuses PlayCamera/ShiftWorld."""
    from pathlib import Path

    from .summons import seqlint as sl
    particles = [p for p in (args.particles or "").split(",") if p.strip()]
    rc = 0
    for raw in args.files:
        p = Path(raw)
        try:
            if p.suffix.lower() == ".sfxmodel":
                problems = [f"ERROR: {m}" for m in sl.lint_sfxmodel_file(p)]
                ticks = None
            else:
                rep = sl.lint_seq_file(p, private_ef=args.private_ef, particles=particles or None)
                problems = [str(x) for x in rep.problems]
                ticks = rep
        except sl.SeqLintError as e:
            print(str(e), file=sys.stderr)
            rc = 2
            continue
        errs = [m for m in problems if m.startswith("ERROR")]
        print(f"{p}: {len(errs)} error(s), {len(problems) - len(errs)} warning(s)"
              + (f", {len(ticks.lines)} op line(s), {ticks.total_ticks} fixed-Wait ticks "
                 f"(>= {ticks.total_ticks / 15.0:.1f}s at BattleTPS=15; excludes "
                 f"{ticks.clip_bound_waits} clip-bound and any SFX-bound wait)"
                 if ticks is not None else ""))
        for m in problems:
            print(f"  {m}")
        if errs:
            rc = 2
    if rc == 0:
        print("clean -- no operation or argument would be silently dropped.")
    return rc


# ---------------------------------------------------------------- the summon CONTAINER-EDIT lanes
# `summon-reskin` (palettes) and `summon-rescore` (camera) edit a STOCK effect container in place --
# no model, no donor, no transplant.  They climb the same sub-verb ladder, stage into the same
# local-only tree, deploy through the same ledger and refuse on the same ModFileList law, so the
# machinery below is shared rather than written twice and left to drift.

#: the sub-verb ladder, in the order an author walks it.
_SUMMON_EDIT_ACTIONS = ("scaffold", "plan", "build", "verify", "deploy", "revert")

#: ``export-art``'s round-trip formats, mirroring :data:`ff9mapkit.summons.repaint.ART_LANES`.
#: Stated literally here because the parser is built before any summon module is imported (every
#: handler imports lazily), and PINNED EQUAL to the module's own tuple by a test -- a `choices=` list
#: that drifted from the lane the handler dispatches on would refuse a lane that works, or offer one
#: that does not.
_SUMMON_ART_LANES = ("indexed", "rgba", "direct15")


class _SummonEditUsage(Exception):
    """A usage refusal in the edit lanes (a missing ``--ef``, a spec that cannot be resolved).

    Raised rather than handed to ``argparse.error`` so it exits 2 like every other refusal in these
    verbs: to the author, "you did not say which effect" and "this build refuses to stage" are the
    same class of answer -- the tool declined and said why -- and giving them different exit codes
    would make a wrapper script treat one of them as a verdict.
    """

    #: what the refusal banner calls this, instead of a private class name nobody can act on.
    REFUSAL_LABEL = "usage"


def _summon_edit_game(args, *, required: bool):
    """The resolved FF9 install root, or ``None`` when absent and ``required`` is False.

    Both edit verbs declare ``--game`` with ``default=argparse.SUPPRESS`` so a ROOT-level ``--game``
    SURVIVES into the subcommand: a subparser option carrying a literal default silently OVERWRITES
    the value the root parser already parsed (the live trap ``summon-deploy``/``summon-import`` still
    carry).  Read through ``getattr`` rather than ``args.game`` because SUPPRESS means this subparser
    contributes the attribute only when the flag was actually given -- whether it exists at all is
    then the ROOT parser's business, and a handler that depends on another parser's defaults staying
    put has a bug waiting for the day they do not.
    """
    from . import config
    try:
        return config.find_game_path(getattr(args, "game", None))
    except config.ConfigError:
        if required:
            raise
        return None


def _summon_edit_mod_root(args):
    """The mod folder ``deploy``/``revert`` act on: ``--root`` wins, else the documented resolver.

    Below ``--root`` the order is :func:`ff9mapkit.config.resolve_mod_folder`'s --
    ``--mod-folder`` > ``$FF9_MOD_FOLDER`` > the nearest ``.ff9deploy.toml`` > ``FF9CustomMap``.

    THE ROOT-DEFAULT READING: the root parser gives ``--mod-folder`` the literal default
    ``FF9CustomMap``, so by the time a handler sees it, "the user typed the default" and "the user
    said nothing at all" are the same string.  It is read as UNSET, so a checkout that pinned its own
    folder in ``.ff9deploy.toml`` is not overruled by a default nobody typed -- that silent overrule
    is the shared-install collision the pin exists to prevent.  The cost is stated rather than
    hidden: typing ``--mod-folder FF9CustomMap`` inside a pinned checkout still resolves the pin, and
    ``--root`` is the way to name a folder unconditionally.
    """
    from pathlib import Path

    from . import config
    root = getattr(args, "root", None)
    if root:
        return Path(root)
    explicit = getattr(args, "mod_folder", None)
    if explicit == config.DEFAULT_MOD_FOLDER:
        explicit = None
    game = config.find_game_path(getattr(args, "game", None))
    return config.find_mod_root(game, config.resolve_mod_folder(explicit))


def _summon_edit_emit_spec(text: str, out, force: bool, what: str) -> int:
    """Write a scaffolded spec to ``out``, or stream it to stdout when ``out`` is None.

    Never over an existing file without ``--force``: silently replacing an author's finished spec
    with a fresh identity scaffold is the single most destructive thing either scaffold verb could do
    -- the law :func:`ff9mapkit.summons.rescore.write_scaffold` already enforces for the camera lane,
    applied here so the palette lane cannot answer the same mistake differently.
    """
    from pathlib import Path

    from . import fsutil
    if not out:
        sys.stdout.write(text)
        return 0
    p = Path(out)
    if p.exists() and not force:
        print("%s already exists. `scaffold` refuses to overwrite an authored spec -- pass --force "
              "if you really mean to replace it." % p, file=sys.stderr)
        return 2
    p.parent.mkdir(parents=True, exist_ok=True)
    fsutil.atomic_write_text(p, text, encoding="utf-8", newline="\n")
    print("wrote %s (%d lines) -- a guarded %s spec at IDENTITY (it builds 0 changed bytes; move one "
          "number at a time)" % (p, text.count("\n"), what))
    return 0


def _summon_edit_spec_path(args, suffix: str):
    """The spec to act on: the positional if given, else ``ef###_<suffix>.toml`` in the CWD.

    Resolved against the CURRENT DIRECTORY, never against the package directory: a module-relative
    default would resolve to a path inside site-packages that holds no toml, which is a refusal
    dressed up as a lookup.
    """
    if args.spec:
        return args.spec
    if args.ef is None:
        raise _SummonEditUsage(
            "`%s` needs a spec file: pass the *_%s.toml as the positional argument, or --ef N to "
            "resolve ef<NNN>_%s.toml in the current directory." % (args.action, suffix, suffix))
    return "ef%03d_%s.toml" % (args.ef, suffix)


def _summon_edit_effect(args, suffix: str, table: str) -> int:
    """Which effect a sub-verb is about, WITHOUT reading the install or building anything.

    ``revert`` has to work on a machine whose install has moved or gone, so the effect id comes from
    ``--ef`` or straight out of the spec's own ``[<table>] effect`` -- never from a build.
    """
    import tomllib
    if args.ef is not None:
        return int(args.ef)
    path = _summon_edit_spec_path(args, suffix)
    try:
        with open(path, "rb") as fh:
            doc = tomllib.load(fh)
        return int((doc.get(table) or {})["effect"])
    except (OSError, ValueError, KeyError, TypeError) as e:
        raise _SummonEditUsage("cannot read the effect id from %s (%s) -- pass --ef N instead"
                               % (path, e))


def _summon_edit_revert(script, args, what: str) -> int:
    """Run a ledger-emitted revert script.

    Run as a SUBPROCESS, not exec'd in-process: that file is the offline handoff artifact -- stdlib
    only, no ``ff9mapkit`` import, ``--root``-rebasable, ``--dry-run``-aware -- and running it exactly
    the way a user without the kit installed would run it is what keeps the two paths honest.  A
    handler that re-implemented the plan would be testing a second implementation.

    THE RE-TARGETING LAW: a revert's destination is a HISTORICAL FACT, not a preference.  The plan
    already knows the folder its writes landed in and bakes it in as the script's own default, so
    this handler re-targets it ONLY on an explicit per-invocation ``--root`` or ``--mod-folder``.

    Silently rebasing onto "whatever folder resolves right now" is destructive in a way nothing would
    warn about: a ledger entry for a file the build newly CREATED records no backup, so the revert
    DELETES it -- and rebased onto a mod folder that plate never wrote to, that deletes somebody
    else's perfectly good override.  A staged build reverted against the live install, or a dry-run
    deploy reverted after the pin changed, would both do exactly that.  The resolver's answer is
    still printed, so a mismatch is visible rather than acted on.
    """
    import subprocess
    from pathlib import Path

    script = Path(script)
    if not script.is_file():
        print("nothing to revert: no ledger revert script at %s.\n"
              "  `deploy` writes one the moment it touches a mod folder.  A `build` only stages into "
              "a local tree and has nothing to undo in a mod folder -- delete the staging root "
              "instead." % script, file=sys.stderr)
        return 2
    from . import config
    explicit = bool(getattr(args, "root", None)) or \
        getattr(args, "mod_folder", None) not in (None, config.DEFAULT_MOD_FOLDER)
    cmd = [sys.executable, str(script)]
    if explicit:
        target = _summon_edit_mod_root(args)
        cmd += ["--root", str(target)]
        where = "RE-TARGETED to %s (you named it)" % target
    else:
        where = ("wherever this plan recorded its writes -- pass --root to re-target it deliberately "
                 "(a revert's destination is history, not a preference)")
    if args.dry_run:
        cmd.append("--dry-run")
    print("%s revert: %s\n  %s%s"
          % (what, script, where, "\n  *** DRY RUN -- nothing will be written ***"
             if args.dry_run else ""))
    return subprocess.call(cmd)


def _summon_reskin_lanes(spec: dict) -> tuple:
    """Which levers ONE ``[reskin]`` spec declares: ``(has CLUT targets, has TEXEL targets)``.

    One spec, two levers, because their byte spans are provably disjoint (the CLUT strip and the
    texel pages are adjacent and non-overlapping): making an author keep two files in step for one
    container would invent a drift risk the format does not have.
    """
    r = spec.get("reskin") or {}
    return bool(r.get("target")), bool(r.get("texel"))


def _summon_reskin_spec_lanes(path) -> tuple:
    """The same answer WITHOUT building anything -- `revert` has to work on a machine whose install
    has moved or gone, and it still has to know which lane staged the artifact it is undoing."""
    import tomllib
    try:
        with open(path, "rb") as fh:
            return _summon_reskin_lanes(tomllib.load(fh))
    except (OSError, ValueError):
        return (True, False)


def _cmd_summon_reskin(args: argparse.Namespace) -> int:
    """Edit a STOCK summon's own art in place -- no model, no donor, the container's own bytes.

    TWO LEVERS ON ONE LADDER.  `[[reskin.target]]` is the CLUT recolour (lever #1, a per-index colour
    function); `[[reskin.texel]]` is the TEXEL REPAINT (lever #2, the indices themselves -- shape,
    edge and silhouette, which a recolour structurally cannot touch).  A spec may declare either or
    BOTH, and a spec declaring both builds the recolour first and hands its patched bytes to the
    repaint, so the two levers ship as ONE container, ONE ledger and ONE revert with their
    changed-byte sets gated disjoint.

    `export-art` decodes every ADDRESSABLE page to a paintable PNG + its overlays + a guarded
    scaffold under a local-only root -- the id-4 creature pages AND the scenery VRAM page-cells whose
    depth the container states, with every refused cell NAMED and its measurement printed as a
    commented block, because on the scenery surface the refusals are the larger half by two orders of
    magnitude; `scaffold` emits a fully guarded CLUT spec at identity;
    `plan` resolves every target and prints every gate group without writing a byte; `build` stages
    the patched container + previews + the deploy/revert scripts; `verify` re-reads what is staged AS
    BYTES; `deploy` writes into the resolved mod folder through the ledger; `revert` runs that
    ledger's own script."""
    from pathlib import Path

    from . import config
    from .summons import camera as _cam
    from .summons import ledger as _led
    from .summons import repaint as rp
    from .summons import reskin as rk

    refusals = (rk.ReskinError, rp.RepaintError, rk.R.RescoreError, _cam.SummonCameraError,
                _led.LedgerError, config.ConfigError, _SummonEditUsage, ValueError, OSError)
    try:
        if args.action == "scaffold":
            if args.ef is None:
                raise _SummonEditUsage("`scaffold` needs --ef N (the stock effect id to read)")
            blob, src = None, ""
            if args.from_path:
                blob, src = Path(args.from_path).read_bytes(), args.from_path
            text, _pmap = rk.scaffold(args.ef, blob=blob, game=getattr(args, "game", None),
                                      source=src)
            return _summon_edit_emit_spec(text, args.out, args.force, "reskin")

        if args.action == "export-art":
            if args.ef is None:
                raise _SummonEditUsage("`export-art` needs --ef N (the stock effect id to read)")
            if args.from_path:
                blob, src = Path(args.from_path).read_bytes(), args.from_path
            else:
                blob, src = rk.R.read_stock_effect(args.ef, getattr(args, "game", None))
            man = rp.export_art(blob, args.ef, args.out or None, source=src, lane=args.art_lane,
                                overlays=not args.no_coverage)
            print("ef%03d  %d page(s) exported -- lane %s" % (args.ef, len(man["parts"]),
                                                              man["lane"]))
            print("  source        : %s" % man["source"])
            print("  stock sha256  : %s  (the drift guard the pack re-reads)" % man["stock_sha256"])
            print("  out           : %s" % man["out_dir"])
            for e in man["parts"]:
                cov = ("%d/%d sampled (%.1f%%), %d interior hole(s)"
                       % (e["covered_texels"], e["wh"][0] * e["wh"][1],
                          100.0 * e["covered_texels"] / max(1, e["wh"][0] * e["wh"][1]),
                          e["interior_holes"])
                       if e["coverage_available"] else
                       "coverage UNAVAILABLE (%s)" % e["coverage_reason"])
                print("    %-12s %#08x %dx%d  %s" % (e["name"], e["page_offset"], e["wh"][0],
                                                     e["wh"][1], cov))
            tx = man.get("texanim") or {}
            if tx.get("armed"):
                print()
                for line in tx.get("lines", ()):
                    print("  %s" % line)
            print("\n  These PNGs are DECODED STOCK ART -- local-only, never committable.  Paint them")
            print("  IN INDEX SPACE keeping the file name (the name is the contract); the .coverage")
            print("  overlay hatches the texels no face ever samples, where paint is inert.")
            return 0

        if args.action == "revert":
            ef = _summon_edit_effect(args, "reskin", "reskin")
            # WHICH LANE staged it decides where the ledger script is: a texel (or composed) build
            # stages under the repaint root, and a revert pointed at the wrong root would report
            # "nothing to revert" about an override that is very much still live.
            _has_clut, has_texel = _summon_reskin_spec_lanes(_summon_edit_spec_path(args, "reskin"))
            root = Path(args.out or (rp.staging_root(ef) if has_texel else rk.staging_root(ef)))
            script = ("revert_summon_repaint_ledger_%d.py" if has_texel else
                      "revert_summon_reskin_ledger_%d.py") % ef
            return _summon_edit_revert(root / script, args, "summon-reskin")

        spec_path = _summon_edit_spec_path(args, "reskin")
        # `--from` is honoured on every reading sub-verb, not only `scaffold`: the whole gate stack
        # (span guards, per-target guards, shared/multi-writer/dual-depth/texanim/headroom, the
        # cutout law, the drift guard) runs identically on caller-supplied bytes, so an offline
        # container is checked exactly as hard as the install's -- a law that held on only one of two
        # entry paths would not be one.
        blob = Path(args.from_path).read_bytes() if args.from_path else None
        spec = rp.load_spec(spec_path)        # accepts target-only, texel-only, or both
        has_clut, has_texel = _summon_reskin_lanes(spec)

        b = bt = None
        if has_clut:
            b = rk.build(spec, spec_path, getattr(args, "game", None), blob=blob)
            b.check = rk.self_check(b)
            print("\n".join(rk.describe(b)))
            print("\n".join(rk.check_lines(b)))
        if has_texel:
            if b is not None:
                print("\n  COMPOSING -- the texel lever splices into the recolour's own patched bytes,")
                print("  so this is ONE container carrying both levers, with one ledger and one revert.")
            bt = rp.build(spec, spec_path, getattr(args, "game", None),
                          # reuse the CLUT lane's already-read stock bytes rather than reading the
                          # install a second time for the same container
                          blob=(b.orig if b is not None else blob),
                          base=(b.patched if b is not None else None),
                          base_label=("composed on this spec's own [[reskin.target]] rows (%d CLUT "
                                      "bytes)" % len(b.check.changed)) if b is not None else "")
            bt.check = rp.self_check(bt)
            print("")
            print("\n".join(rp.describe(bt)))
            print("\n".join(rp.check_lines(bt)))

        # The lane that OWNS the artifact: with both levers live the repaint's `patched` IS the
        # composed container, so it stages and verifies and the recolour never writes a second file.
        lane, art = ((rp, bt) if bt is not None else (rk, b))
        ok = all(x.check.ok for x in (b, bt) if x is not None)
        # A real deploy MUST resolve the install (that is where it writes); every other path, the
        # dry run included, works without one -- a rehearsal that needs the thing it is rehearsing
        # not to touch is not a rehearsal.
        game_root = _summon_edit_game(args, required=args.action == "deploy" and not args.dry_run)

        if args.action == "plan":
            if args.previews:
                root = Path(args.out or lane.staging_root(art.effect))
                files = []
                if b is not None:
                    files += rk.render_previews(b, root / "previews")
                if bt is not None:
                    files += rp.render_previews(bt, root / "previews")
                print("\n  previews (decoded STOCK art -- local-only, never committable):")
                for f in files:
                    print("    %s" % f)
            else:
                print("\nplan only -- nothing written.")
            return 0 if ok else 1

        if args.action == "verify":
            res = lane.verify(art, root=args.out or None)
            print("")
            for line in res["lines"]:
                print("  %s" % line)
            ok = bool(res["ok"]) and ok
            print("\n  VERIFY: %s" % ("PASS" if ok else "FAIL"))
            return 0 if ok else 1

        # build / deploy both WRITE, so both are gated on the self-check(s) first.
        if not ok:
            print("\nREFUSING TO STAGE -- the self-check failed (see the gates above).",
                  file=sys.stderr)
            return 1

        if args.action == "build":
            out = lane.stage(art, root=args.out or None, game_root=game_root,
                             previews=not args.no_previews)
            print("\n  STAGED")
        else:                                                    # deploy
            root = Path(args.out or lane.staging_root(art.effect))
            mod_root = (root / "dry-run-mod") if args.dry_run else _summon_edit_mod_root(args)
            out = lane.stage(art, root=root, game_root=game_root, allow_install=not args.dry_run,
                             previews=not args.no_previews, mod_root=mod_root,
                             refuse_modfilelist=True)
            print("\n  %s" % ("DRY RUN -- staged into a local mirror, the mod folder is untouched"
                              if args.dry_run else "DEPLOYED"))
        for k, v in out.items():
            if k in ("transforms", "per_target_bytes", "texels"):
                continue
            if isinstance(v, dict):
                for k2, v2 in v.items():
                    print("    %-22s %s" % (k2, v2))
            elif isinstance(v, list):
                for v2 in v:
                    print("    %-22s %s" % (k, v2))
            else:
                print("    %-22s %s" % (k, v))
        if args.action == "deploy" and not args.dry_run:
            print("    SFX.Play re-reads the container and wipes the texture cache on every cast, so "
                  "the edit is live on the NEXT cast -- no relaunch, no reload."
                  + ("  A PAGE upload is itself the cache-invalidating event, so a repaint's "
                     "guarantee is the stronger of the two." if bt is not None else ""))
        return 0
    except refusals as e:
        # A refusal is a RESULT of these verbs, so it is presented as one -- a traceback would bury
        # the paragraph the author is meant to read.  The CLASS is named alongside the message
        # because `ValueError`/`OSError` are in the net for spec and IO problems, and an unexpected
        # one of those must stay distinguishable from a gate that deliberately said no.
        print("\nREFUSED (%s)\n%s" % (getattr(e, "REFUSAL_LABEL", type(e).__name__), e),
              file=sys.stderr)
        return 2


def _cmd_summon_rescore(args: argparse.Namespace) -> int:
    """Re-frame a STOCK summon's CAMERA in place -- pose/orientation/focal on its own camera blocks.

    Same ladder as `summon-reskin`: `scaffold` emits a guarded identity spec derived from the
    container's own id-2 camera archive, `plan` builds + prints the delta/splice/self-check without
    writing, `build` stages, `verify` re-reads the staged bytes, `deploy` writes into the resolved
    mod folder through the ledger and `revert` runs that ledger's script.  This lane may not touch a
    duration, a frame word, or the block's byte length -- refused at the call site, not in a note."""
    import os
    from pathlib import Path

    from . import config
    from .summons import camera as _cam
    from .summons import ledger as _led
    from .summons import rescore as rs

    refusals = (rs.RescoreError, _cam.SummonCameraError, _led.LedgerError, config.ConfigError,
                _SummonEditUsage, ValueError, OSError)
    try:
        if args.action == "read":
            if args.ef is None:
                raise _SummonEditUsage("`read` needs --ef N (the stock effect id to read)")
            if args.from_path:
                blob, source = Path(args.from_path).read_bytes(), args.from_path
            else:
                blob, source = rs.read_stock_effect(args.ef, getattr(args, "game", None))
            print("\n".join(_cam.read_out(blob, source, machines=())))
            return 0

        if args.action == "scaffold":
            if args.ef is None:
                raise _SummonEditUsage("`scaffold` needs --ef N (the stock effect id to read)")
            if args.from_path:
                blob, source = Path(args.from_path).read_bytes(), args.from_path
            else:
                blob, source = rs.read_stock_effect(args.ef, getattr(args, "game", None))
            # `machines=()` always: the tier-R state-machine recovery is a study-only instrument and
            # was deliberately not promoted, so the scaffold reports no reframe BUDGET column rather
            # than dragging a MIPS disassembler into the package for one advisory line.
            sc = rs.scaffold(args.ef, blob, source, machines=())
            print("\n".join(rs.scaffold_summary(sc)), file=sys.stderr if not args.out else sys.stdout)
            return _summon_edit_emit_spec(sc.text, args.out, args.force, "rescore")

        if args.action == "revert":
            ef = _summon_edit_effect(args, "rescore", "rescore")
            work = Path(args.out or rs.staging_root(ef))
            return _summon_edit_revert(work / ("revert_summon_camera_%d.py" % ef),
                                       args, "summon-rescore")

        spec_path = _summon_edit_spec_path(args, "rescore")
        # See `_cmd_summon_reskin`: `--from` reads a container FILE on every sub-verb, and the drift
        # guard, the alternates check and the self-check all run on those bytes unchanged.
        blob = Path(args.from_path).read_bytes() if args.from_path else None
        b = rs.build_patched(rs.load_spec(spec_path), spec_path, getattr(args, "game", None),
                             blob=blob)
        print("\n".join(rs.describe(b)))
        # See `_cmd_summon_reskin`: only a REAL deploy needs the install resolved.
        game_root = _summon_edit_game(args, required=args.action == "deploy" and not args.dry_run)

        if args.action == "plan":
            print("\nplan only -- nothing written.")
            return 0 if (b.check is None or b.check.ok) else 1

        if args.action == "verify":
            res = rs.verify(b, mod_root=os.path.join(args.out, "mod") if args.out else None)
            print("\n  VERIFY  %s\n    %d B on disc, sha %s\n    %s"
                  % ("PASS" if res["ok"] else "FAIL", res["bytes"],
                     (res["sha256"] or "-")[:16], res["reason"]))
            return 0 if res["ok"] else 1

        if b.check is not None and not b.check.ok:
            print("\nREFUSING TO STAGE -- the self-check failed (see above).", file=sys.stderr)
            return 1

        if args.action == "build":
            out = rs.stage(b, mod_root=os.path.join(args.out, "mod") if args.out else None,
                           work_dir=args.out or None, game_root=game_root)
            print("\n  STAGED")
        else:                                                    # deploy
            # The work dir is passed EXPLICITLY on this path.  `stage` derives its default from the
            # resolved mod root's parent, which on a deploy is a directory inside the game install --
            # backups and the revert script must never land there.
            work = Path(args.out or rs.staging_root(b.effect))
            mod_root = (work / "dry-run-mod") if args.dry_run else _summon_edit_mod_root(args)
            out = rs.stage(b, mod_root=mod_root, work_dir=work, game_root=game_root,
                           allow_install=not args.dry_run, refuse_modfilelist=True)
            print("\n  %s" % ("DRY RUN -- staged into a local mirror, the mod folder is untouched"
                              if args.dry_run else "DEPLOYED"))
        for k, v in out.items():
            print("    %-22s %s" % (k, v))
        if not out["modfilelist_present"]:
            print("    (no ModFileList.txt in this mod folder -- correct: one must never be CREATED, "
                  "or every OTHER file in the folder becomes invisible at a stroke)")
        return 0
    except refusals as e:
        # A refusal is a RESULT of these verbs, so it is presented as one -- a traceback would bury
        # the paragraph the author is meant to read.  The CLASS is named alongside the message
        # because `ValueError`/`OSError` are in the net for spec and IO problems, and an unexpected
        # one of those must stay distinguishable from a gate that deliberately said no.
        print("\nREFUSED (%s)\n%s" % (getattr(e, "REFUSAL_LABEL", type(e).__name__), e),
              file=sys.stderr)
        return 2


def _cmd_image_field(args: argparse.Namespace) -> int:
    """EXPERIMENTAL: synthesize a walkable FF9 field from an image + a hand-traced floor polygon."""
    from pathlib import Path

    from . import imagefield
    if args.auto_floor and args.floor:
        print("pick one: --floor (hand-traced) or --auto-floor (detected)", file=sys.stderr)
        return 2
    auto = None
    if args.auto_floor:
        try:
            auto = imagefield.auto_floor(args.image, pitch=args.pitch, fov=args.fov, distance=args.distance)
        except (imagefield.ImageFieldError, FileNotFoundError) as e:
            if not args.trace:
                print(str(e), file=sys.stderr)
                return 2
            print(f"note: {e}  (tracer opens un-seeded)")
    if args.trace:
        out_html = (Path(args.out) / "trace.html" if args.out
                    else Path(args.image).with_name(Path(args.image).stem + ".trace.html"))
        try:
            man = imagefield.write_trace_html(args.image, out_html, pitch=args.pitch, fov=args.fov,
                                              distance=args.distance, floor0=(auto or {}).get("floor"))
        except (imagefield.ImageFieldError, ValueError, FileNotFoundError) as e:
            print(str(e), file=sys.stderr)
            return 2
        print(f"[EXPERIMENTAL] floor tracer -> {man['html']}")
        if auto:
            print(f"  auto floor-seed pre-loaded: {len(auto['floor'])} points "
                  f"({auto['area_frac']:.0%} of the canvas) -- drag/undo to refine, then copy the command.")
        print("Open it in a browser: click the floor outline (below the horizon line), optionally mark each "
              "foreground object's ground-contact point, then copy the emitted image-field command.")
        return 0
    if not (args.floor or auto):
        print("--floor is required to build (or --auto-floor to detect it, or --trace to click-trace it)",
              file=sys.stderr)
        return 2
    if not args.out:
        print("--out is required to build (the output project dir)", file=sys.stderr)
        return 2
    try:
        if auto:
            floor = auto["floor"]
            print(f"auto floor-seed: {len(floor)} points ({auto['area_frac']:.0%} of the canvas) -- "
                  f"refine by hand via:  --floor \"{' '.join(f'{x:g},{y:g}' for x, y in floor)}\"")
        else:
            floor = []
            for tok in str(args.floor).replace(";", " ").split():
                cx, cy = tok.split(",")
                floor.append((float(cx), float(cy)))
        if len(floor) < 3:
            print("--floor needs >=3 'cx,cy' canvas-pixel points (the floor outline)", file=sys.stderr)
            return 2
        fg = list(args.foreground or [])
        man = imagefield.build_image_field(
            args.image, floor, args.out, foreground=fg, name=args.name, field_id=args.id,
            pitch=args.pitch, fov=args.fov, distance=args.distance,
            gateways=list(args.gateway or []), events=list(args.event_zone or []))
    except (imagefield.ImageFieldError, ValueError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"[EXPERIMENTAL] synthesized {args.name} -> {man['toml']}")
    print(f"  walkmesh: {man['verts']} verts / {man['faces']} tris; spawn "
          f"({man['spawn'][0]:.0f}, {man['spawn'][1]:.0f}); {len(man['layers'])} layer(s)")
    for f in man.get("foreground", []):
        if f["contact"]:
            print(f"  occluder {Path(f['image']).name}: contact ({f['contact'][0]:g},{f['contact'][1]:g}) "
                  f"-> z {f['z']} (walk in front = actor on top; walk behind = occluded)")
    for gi, gw in enumerate(man.get("gateways", [])):
        print(f"  gateway door{gi} -> field {gw['to']}"
              + (f" entrance {gw['entrance']}" if gw['entrance'] else "")
              + " (corners 0->1 = the walk-out edge)")
    for ei, ev in enumerate(man.get("events", [])):
        print(f"  event zone{ei}: {ev['message']!r}")
    print(f"Deploy + walk it: py tools/deploy_field.py {man['toml']} --id 30058   (then ~ -> Warp 30058)")
    print("HAND-TRACED FLOOR: the polygon must outline the floor in the FINAL 384x448 canvas (top-left, "
          "Y-down), below the horizon. Only the human can confirm it lands on the art in-game (CLAUDE.md).")
    return 0


def _cmd_model_preview(args: argparse.Namespace) -> int:
    """Software-render a model to a PNG still (the same renderer behind the GUI thumbnails)."""
    from .models import preview as mpreview
    out = args.out or f"{str(args.model).replace('/', '_')}.png"
    try:
        img = mpreview.render_token(args.model, game=args.game, pose=not args.rest,
                                    size=args.size, yaw=args.yaw, pitch=args.pitch)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    img.save(out)
    print(f"rendered {args.model} -> {out}  ({args.size}x{args.size}, yaw {args.yaw:g}, pitch {args.pitch:g}, "
          + ("rest pose" if args.rest else "stand pose") + ")")
    return 0


def _cmd_model_reskin(args: argparse.Namespace) -> int:
    """The cheapest model edit: export a model's textures / deploy edited PNGs as a loose reskin."""
    from .models import reskin as mreskin
    if not args.export_textures and not args.texture:
        print("model-reskin needs --export-textures DIR (get the editable PNGs) or "
              "--texture PNG... --deploy MODFOLDER (ship the edited ones)", file=sys.stderr)
        return 2
    try:
        if args.export_textures:
            man = mreskin.export_textures(args.model, args.export_textures, game=args.game)
            print(f"exported {len(man['textures'])} texture(s) of {man['geo']} -> {man['dir']}")
            for t in man["textures"]:
                print(f"  {t['name']}  ({t['size'][0]}x{t['size'][1]})")
            print("Edit them in any image editor (any size works), KEEP THE NAMES, then: "
                  f"ff9mapkit model-reskin {args.model} --deploy MODFOLDER --texture <edited.png...>")
        if args.texture:
            if not args.deploy:
                print("--texture needs --deploy MODFOLDER (where to ship the reskin)", file=sys.stderr)
                return 2
            man = mreskin.deploy_reskin(args.model, args.texture, args.deploy, game=args.game)
            print(f"reskinned {man['geo']} (id {man['geo_id']}): {', '.join(man['deployed'])}")
            print(f"  -> {man['dir']}")
            print("Field models: ~ -> Reload field re-probes the texture. Battle/weapon models load "
                  "on battle entry -- a RELAUNCH is the sure path.")
        for w in man.get("warnings", []):
            print(f"  NOTE: {w}")
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    return 0


def _cmd_model_deployed(args: argparse.Namespace) -> int:
    """List (or revert one of) a mod folder's loose model overrides/reskins/mints/anim overrides."""
    from .models import deployed
    entries = deployed.scan_mod(args.mod_folder)
    if args.revert is not None:
        matches = [e for e in entries if e["geo_id"] == args.revert
                   and (args.kind is None or e["kind"] == args.kind)]
        if not matches:
            print(f"nothing deployed at id {args.revert}"
                  + (f" with kind {args.kind}" if args.kind else ""), file=sys.stderr)
            return 2
        if len(matches) > 1:
            kinds = ", ".join(e["kind"] for e in matches)
            print(f"id {args.revert} has {len(matches)} deployed entries ({kinds}) -- "
                  f"disambiguate with --kind", file=sys.stderr)
            return 2
        r = deployed.revert_entry(args.mod_folder, matches[0])
        print(f"reverted: {deployed.describe(matches[0])}")
        if r["directive_removed"]:
            print("  stripped its 3DModel line -- RELAUNCH to unregister the id")
        return 0
    if not entries:
        print("no loose model overrides in this folder")
        return 0
    for e in entries:
        print(f"  {deployed.describe(e)}")
    print(f"{len(entries)} entr{'y' if len(entries) == 1 else 'ies'} "
          f"(revert one: model-deployed <mod> --revert <id> [--kind <kind>])")
    return 0


def _cmd_model_import(args: argparse.Namespace) -> int:
    """Bring a (Blender-edited) glTF back into the game -> a loose-FBX override (the edit loop return path)."""
    from .models import gltf as mgltf
    if not args.deploy:
        print("model-import needs --deploy MODFOLDER (where to write the override)", file=sys.stderr)
        return 2
    try:
        r = mgltf.deploy_edit(args.gltf, args.deploy, like=args.like, geo_id=args.id,
                              scale=args.scale, game=args.game, write_anims=not args.no_anims)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"imported glTF -> model id {r['id']} ({r['mode']}"
          + (f", rig from {r['source']}" if r['source'] else "") + ")")
    print(f"  wrote: {r['path']}  (+ {len(r['textures'])} texture(s))")
    anims = r.get("anims") or {}
    _anim_dirs = ", ".join(f"Animations/{f}/" for f in (anims.get("folders") or [anims.get("geo_id")]))
    if anims.get("written"):
        print(f"  animations: wrote {len(anims['written'])} edited clip override(s) -> {_anim_dirs}*.anim")
    elif anims.get("error"):
        print(f"  animations: skipped ({anims['error']})")
    elif not args.no_anims:
        print("  animations: no changed clips to write (untouched clips keep the bundled version)")
    for w in anims.get("warnings", []):
        print(f"  WARN: {w}")
    if anims.get("written"):
        # The engine caches loaded clips in a static AnimationClipReader.LoadedClips (keyed by path, checked
        # before disc), and a debug-menu field-reload re-requests the SAME path -> it gets the cached clip. So a
        # re-deployed .anim needs a RELAUNCH; only the mesh/FBX is picked up by the menu reload.
        print(f"  RELAUNCH FF9 to apply the .anim clip(s) (a debug-menu field-reload keeps the cached clip); the MESH "
              f"shows after a menu reload. Revert: delete Models/<type>/{r['id']}/ + {_anim_dirs}.")
    else:
        print(f"  ~ -> Reload field (or warp to a field using this model) to see the edit. Revert by "
              f"deleting that Models/<type>/{r['id']}/ folder.")
    if r.get("source"):
        _print_model_notes(r["source"], minted=int(r["id"]) >= 6000, merge_warnings=r.get("merge_warnings"))
    return 0


def _cmd_model_anim(args: argparse.Namespace) -> int:
    """Dump/deploy a model's REAL animation clips as loose ``.anim`` JSON -- hand-edit the numbers, or prove
    the loose-override path. DLL-free: the engine reads Animations/{geoId}/{key}.anim from the mod folder."""
    from pathlib import Path
    from .models import anim as manim
    try:
        if args.deploy:
            r = manim.deploy_source_anims(args.model, args.deploy, which=args.clips, game=args.game)
            where = Path(args.deploy)
        else:
            r = manim.deploy_source_anims(args.model, args.out, which=args.clips, game=args.game)
            where = Path(args.out)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    folders = sorted({Path(w).parent.name for w in r["written"]}, key=int) or [str(r["geo_id"])]
    fdir = folders[0] if len(folders) == 1 else "{%s}" % ",".join(folders)   # donor-located clips span folders
    print(f"{'deployed' if args.deploy else 'dumped'} {len(r['written'])} clip(s) for {r['geo']} "
          f"(id {r['geo_id']}) -> {where}/StreamingAssets/Assets/Resources/Animations/{fdir}/")
    if r.get("missing"):
        print(f"  NOT FOUND anywhere on disc (own folder, donor folder, or a same-name sibling id): "
              f"{', '.join(map(str, r['missing']))}")
    if not r["written"]:
        print(f"  (no clips matched; available keys: {', '.join(map(str, r['keys'])) or 'none'})")
    else:
        print(f"  keys: {', '.join(str(Path(w).stem) for w in r['written'])}")
        print("  Edit the JSON (time/x/y/z/w per bone) and re-deploy, or edit the .glb in Blender + "
              "`model-import`. RELAUNCH FF9 to apply (the engine caches clips by path; a debug-menu field-reload "
              "keeps the cached one).")
    return 0


def _cmd_playable_anims(args: argparse.Namespace) -> int:
    """The Blender edit loop for a 13th character's custom_battle_anims animset: INFO (which donor model to
    export) or ROUTE an edited donor .glb onto the character's OWN minted animset (the donor is never touched)."""
    from ff9mapkit import build as B
    from ff9mapkit.models import anim as manim
    from ff9mapkit.battle import characterdelta as _cd
    try:
        info = B.resolve_playable_animset(args.field, name=args.name, game=args.game)
    except (B.BuildError, RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    src = info["source_geo"] or f"id {info['src_geo_id']}"
    glb_name = f"{info['name'].lower()}_anims.glb"

    def _motion_labels():                                  # {src_key -> "NN_motion"} for the donor's 34 slots
        try:
            return _cd.battle_motion_labels(info["serial"], game=args.game) if info.get("serial") else {}
        except _cd.CharacterDeltaError:
            return {}

    if args.export:                                        # export the donor with NAMED Actions (attack/cast/...)
        from ff9mapkit.models import gltf as mgltf
        keys = " ".join(str(sk) for (_sg, sk, _dk) in info["clips"])   # only the animset's clips, all labeled
        try:
            man = mgltf.export_gltf(src, args.export, anims=keys, label_overrides=_motion_labels(), game=args.game)
        except (RuntimeError, FileNotFoundError, ValueError) as e:
            print(str(e), file=sys.stderr)
            return 2
        print(f"exported {info['name']}'s {len(man['anims'])} battle motions -> {man['path']} (from {src}, unchanged)")
        print(f"  Actions are NAMED by motion: {', '.join(man['anims'][:6])}{' ...' if len(man['anims']) > 6 else ''}")
        print(f"  Open in Blender (File > Import > glTF 2.0), edit a pose in the Animation workspace, export the .glb,")
        print(f"  then: ff9mapkit playable-anims {args.field} --edit {args.export} --deploy MODFOLDER")
        return 0

    if not args.edit:                                      # INFO mode -- show the whole loop + the motion->key table
        print(f"{info['name']}'s battle animset ({info['key_count']} clips) is minted at model id "
              f"{info['dest_geo_id']} (Animations/{info['dest_geo_id']}/), sourced from {src}.")
        print("Edit loop (the donor is NEVER touched):")
        print(f"  1. ff9mapkit playable-anims {args.field} --export {glb_name}   (NAMED Actions: attack/cast/...)")
        print(f"  2. open {glb_name} in Blender, scrub/edit the Action(s) you want unique, export the .glb")
        print(f"  3. ff9mapkit playable-anims {args.field} --edit {glb_name} --deploy MODFOLDER")
        print(f"     (writes ONLY {info['name']}'s Animations/{info['dest_geo_id']}/ -- {src} is unchanged)")
        labels = _motion_labels()
        if labels:                                         # a quick motion -> clip-key reference
            common = {"idle", "attack", "cast", "hit", "victory", "defend", "run", "dodge", "item"}
            picks = sorted((lbl, k) for k, lbl in labels.items() if lbl.split("_", 1)[-1] in common)
            print("  key motions (Action name in Blender -> clip key): "
                  + ", ".join(f"{lbl}={k}" for lbl, k in picks))
        return 0
    if not args.deploy:
        print("playable-anims --edit needs --deploy MODFOLDER (where to write the character's animset)", file=sys.stderr)
        return 2
    # Blender drops the ff9_anim_key glTF stamp on re-export, so route the edited Actions back by their NAME:
    # invert the same {key -> "NN_motion"} map the --export step named them with ("23_attack" -> its clip key).
    _label_keys = {v.lower(): k for k, v in _motion_labels().items()}
    try:
        r = manim.deploy_battle_animset_edits(info["clips"], info["dest_geo_id"], args.edit, args.deploy,
                                              game=args.game, label_keys=_label_keys)
    except (manim.AnimsetError, RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"routed {len(r['edited'])} edited + {len(r['faithful'])} faithful clip(s) -> "
          f"{info['name']}'s Animations/{r['dest_geo_id']}/ ({info['key_count']} total)")
    if r["edited"]:
        print(f"  edited motions (source keys): {', '.join(map(str, r['edited']))}")
    elif r.get("glb_anims") and not r.get("matched"):      # the glb had clips but NONE belong to this animset
        print(f"  0 edits applied -- NONE of the .glb's {r['glb_anims']} animation(s) belong to {info['name']}'s "
              f"animset. Did you export the RIGHT donor? -> ff9mapkit model-gltf {src} --anims all")
    else:
        print("  no CHANGED clips in the .glb (every matched Action equals the donor) -- edit a pose in Blender first")
    for w in r.get("warnings", []):
        print(f"  WARN: {w}")
    print(f"  {src} is untouched. RELAUNCH FF9 to apply (the engine caches .anim by path; a menu reload keeps the cached one), "
          f"then enter a battle to see {info['name']}'s new motion.")
    print(f"  NOTE: run this AFTER deploying the field, and RE-RUN it after any re-deploy -- deploy_field re-ships the "
          f"faithful animset (per-file overwrite) and deploy_campaign/deploy_journey REBUILD the whole folder, either "
          f"of which wipes these edits.")
    return 0


def _cmd_sound_list(args: argparse.Namespace) -> int:
    """List the id -> ResourceID map for music or SFX -- what to pass to `audio-import --song` / what file
    to override."""
    from . import sound as S
    kind = getattr(args, "kind", "music")
    try:
        table = S.read_manifest(kind, game=args.game)
    except Exception as e:                                 # noqa: BLE001
        print(f"could not read the {kind} manifest: {e}", file=sys.stderr)
        return 2
    filt = (args.filter or "").strip().lower()
    rows = [r for r in table if not filt or filt in r["resource_id"].lower() or filt == str(r["id"])]
    print(f"{len(rows)} {kind} track(s) (id -> ResourceID):")
    for r in rows:
        print(f"  {r['id']:>5}  {r['resource_id']}")
    print(f"\n  override one:  ff9mapkit audio-import <in.wav> --song <id>"
          f"{' --kind sfx' if kind == 'sfx' else ''} --deploy <modfolder>")
    return 0


def _cmd_audio_import(args: argparse.Namespace) -> int:
    """Import a custom music/SFX track: transcode to Ogg Vorbis + drop it as a loose override of an existing
    id (DLL-free). Sets Memoria.ini PriorityToOGG=1 so the OGG wins over the bundled AKB."""
    import os
    from . import sound as S
    if not args.deploy:
        print("audio-import needs --deploy MODFOLDER (where to write the override)", file=sys.stderr)
        return 2
    try:
        if args.new_song:
            res = S.mint_song(args.input, args.deploy, kind=args.kind, new_id=args.id,
                              loop_start=args.loop_start, loop_end=args.loop_end, quality=args.quality,
                              set_priority=not args.no_set_priority, game=args.game)
        else:
            res = S.deploy_audio(args.input, args.song, args.deploy, kind=args.kind,
                                 loop_start=args.loop_start, loop_end=args.loop_end, quality=args.quality,
                                 set_priority=not args.no_set_priority, game=args.game)
    except Exception as e:                                 # noqa: BLE001
        print(f"audio-import failed: {e}", file=sys.stderr)
        return 2
    if res.get("minted"):
        print(f"minted NEW {args.kind} id {res['song_id']} = {res['resource_id']}")
        print(f"  ogg:      {res['path']}")
        print(f"  manifest: {res['manifest']}")
        print(f"  PLAY IT in a field:  [music] song = {res['song_id']}   (or .eb RunSoundCode(0, {res['song_id']}))")
    else:
        print(f"imported {args.kind} id {res['song_id']} = {res['resource_id']}")
        print(f"  wrote: {res['path']}")
    loop = ("auto-loop (whole track)" if res["loop_start"] is None and res["loop_end"] is None
            else f"loop {res['loop_start']}..{res['loop_end']} samples") if args.kind == "music" else "play-once (sfx)"
    print(f"  {loop}")
    p = res.get("priority")
    if p and p.get("changed"):
        print(f"  set PriorityToOGG=1 in Memoria.ini (was {p['was']}; backup {os.path.basename(p['backup'] or '')})")
    elif p and p.get("was") == "1":
        print("  PriorityToOGG already 1")
    elif args.no_set_priority:
        print("  [!] did NOT set PriorityToOGG -- set [Audio] PriorityToOGG=1 in Memoria.ini or the bundle track wins")
    vk, vv = res.get("volume_key", "MusicVolume"), res.get("volume")
    if vv == 0:
        print(f"  [!] {vk} is 0 (MUTED) -- turn it up (in-game Config or Memoria.ini) or you won't hear it")
    print(f"  RESTART FF9 to hear it (audio loads at startup; a menu reload won't reload it)."
          + (f" ({vk} = {vv})" if vv is not None else f" Check {vk} > 0."))
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
                                author=args.author, description=args.description, game=args.game)
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
    for ln in info.get("lint", []):
        print(f"  lint {ln}")
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


def _cmd_world_extract(args: argparse.Namespace) -> int:
    """Extract an overworld block's terrain mesh (the Path-C geometry-edit foundation) -> .obj + .mapids.json."""
    from .world import extract as W
    try:
        if args.list:
            blocks = W.list_blocks(disc=args.disc, lod=args.lod, game=args.game)
            for (x, y) in blocks:
                print(f"  block[{x}][{y}]")
            print(f"disc{args.disc}: {len(blocks)} terrain block(s)")
            return 0
        if not args.block:
            print("give a block to extract: world-extract --block X Y  (or --list)", file=sys.stderr)
            return 2
        x, y = args.block
        summ = W.extract_block(x, y, disc=args.disc, lod=args.lod, out_dir=(args.out or "."), game=args.game)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"block[{x}][{y}] '{summ['name']}': {summ['vertices']} verts / {summ['triangles']} tris  "
          f"(round-trip {'OK' if summ['roundtrip'] else 'FAILED -- decode not lossless!'})")
    if summ["place_entrances"]:
        print("  place entrances: " + ", ".join(f"area {e['area']} (x{e['tris']} tris)"
                                                 for e in summ["place_entrances"]))
    else:
        print("  (no place-entrance tiles -- plain terrain block)")
    print(f"  topograph types present: {summ['topographs']}")
    print(f"  -> {summ['files']['obj']}")
    print(f"  -> {summ['files']['mapids']}")
    return 0


def _cmd_world_deploy(args: argparse.Namespace) -> int:
    """Deploy an (optionally reshaped) overworld block, or a whole reshaped region, as loose .ff9mesh override(s)
    (needs the WorldMeshOverride engine patch). Reshapes (--hill/--crater/--flatten) are seam-continuous: the edit
    is evaluated in WORLD XZ and every block whose footprint the radius touches is redeployed, so nothing tears."""
    from .world import extract as W, mesh as M

    if args.flatten and (args.hill or args.crater):
        print("pick one of --hill / --crater / --flatten", file=sys.stderr)
        return 2
    if args.hill and args.crater:
        print("pick --hill OR --crater, not both", file=sys.stderr)
        return 2
    if (args.hill or args.crater or args.flatten) and (args.lift or args.spike):
        print("--lift/--spike are a [diag] flat bump, not a reshape -- pick --hill/--crater/--flatten OR "
              "--lift/--spike, not both", file=sys.stderr)
        return 2
    reshape = bool(args.hill or args.crater or args.flatten)
    hill_amt = args.hill if args.hill else (-args.crater if args.crater else 0.0)

    def _explicit():
        if args.cluster:
            x0, y0, x1, y1 = args.cluster
            return [(x, y) for x in range(min(x0, x1), max(x0, x1) + 1)
                    for y in range(min(y0, y1), max(y0, y1) + 1)]
        return [(args.block[0], args.block[1])] if args.block else []

    explicit = _explicit()
    if not explicit and not (reshape and args.center):
        print("give a target: --block X Y, --cluster XMIN YMIN XMAX YMAX, or (with a reshape) --center WX WZ",
              file=sys.stderr)
        return 2

    try:
        if args.center:
            cx, cz = args.center
        else:                                             # centre of the explicit block(s)' world footprint
            oxs = [x * W.BLOCK_SIZE for (x, _) in explicit]
            ozt = [-y * W.BLOCK_SIZE for (_, y) in explicit]
            cx = (min(oxs) + max(oxs) + W.BLOCK_SIZE) / 2.0
            cz = (min(ozt) + max(ozt) - W.BLOCK_SIZE) / 2.0

        if reshape:                                       # crack-free set: every block the radius actually reaches
            allblocks = set(W.list_blocks(disc=args.disc, lod=args.lod, game=args.game))
            targets = W.blocks_touched(cx, cz, args.radius, allblocks)
            targets = sorted(set(targets) | {b for b in explicit if b in allblocks})
            if not targets:
                print(f"no disc-{args.disc} blocks within radius {args.radius:g} of world ({cx:.0f},{cz:.0f})",
                      file=sys.stderr)
                return 2
        elif args.cluster:                                # a multi-block lift/spike/faithful: skip ocean gaps
            allblocks = set(W.list_blocks(disc=args.disc, lod=args.lod, game=args.game))
            targets = [b for b in explicit if b in allblocks]
            if not targets:
                print("none of the --cluster blocks exist as terrain on this disc", file=sys.stderr)
                return 2
        else:
            targets = explicit

        # read all targets first, so the entrance-safety refusal below never leaves a partial deploy
        bms = [W.read_block(x, y, disc=args.disc, lod=args.lod, game=args.game) for (x, y) in targets]

        # SAFETY: a reshape that raises/lowers a place-ENTRANCE block softlocks the player -- the spawn/field-exit
        # drops the actor at the tile's STALE pre-raise Y, below the new surface, and foot movement raycasts DOWN
        # so it never reaches the raised tiles -- AND sinks the entrance prop model into a pit. Refuse unless forced.
        if reshape and not args.allow_entrances:
            ent = [(bm.x, bm.y, sorted({W.decode_id(i)["area"] for i in W.block_mapids(bm) if W.decode_id(i)["event"]}))
                   for bm in bms]
            ent = [(x, y, a) for (x, y, a) in ent if a]
            if ent:
                print("REFUSED: this reshape touches place-ENTRANCE block(s) -- raising/lowering them softlocks the "
                      "player (embed) and sinks the entrance prop into a pit:", file=sys.stderr)
                for (x, y, a) in ent:
                    print(f"  [{x}][{y}] entrance area(s) {a}", file=sys.stderr)
                print("  move the edit off them (adjust --center / smaller --radius), or pass --allow-entrances to "
                      "override.", file=sys.stderr)
                return 2

        written = []
        for bm in bms:
            x, y = bm.x, bm.y
            ox, oz = W.block_world_origin(x, y)
            if args.lift:
                M.lift_block(bm, args.lift)
                op = f"lift +{args.lift:g}"
            elif args.spike:
                bi = M.raise_vertex_near_center(bm, args.spike)
                op = f"spike vtx {bi} +{args.spike:g}"
            elif args.flatten:
                n = M.flatten_region(bm, radius=args.radius, center=(cx, cz), height=args.height,
                                     falloff=args.falloff, world_origin=(ox, oz))
                op = f"flatten r{args.radius:g} ({n} v)"
            elif reshape:
                n = M.deform_radial(bm, amount=hill_amt, radius=args.radius, center=(cx, cz),
                                    falloff=args.falloff, world_origin=(ox, oz))
                op = f"{'hill' if hill_amt > 0 else 'crater'} {hill_amt:+g} r{args.radius:g} ({n} v)"
            else:
                op = "faithful copy"
            if reshape and not args.no_normals:
                M.recompute_normals(bm)
            dest = M.deploy_override(bm, mod_folder=args.mod_folder, game=args.game, lod=args.lod)
            written.append((x, y, op, dest))
        if written:
            from .world import discmirror as DM
            DM.auto_mirror([w[3] for w in written], mod_folder=args.mod_folder, skip_mirror=args.skip_mirror)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2

    print(f"deployed {len(written)} block override(s) into {args.mod_folder}")
    if reshape:
        kind = "flatten" if args.flatten else ("hill" if hill_amt > 0 else "crater")
        print(f"  {kind}: centre world ({cx:.0f},{cz:.0f}) radius {args.radius:g} falloff {args.falloff}"
              + ("" if args.no_normals else " + smooth normals"))
    for (x, y, op, _) in written:
        print(f"  [{x}][{y}]: {op}")
    print("  RELAUNCH the game (a new loose asset isn't hot-reloaded), reach the disc-%d overworld, walk to the edit."
          % args.disc)
    print("  Memoria.log shows \"[WorldMeshOverride] loaded ...\" per block when the hook fires.")
    return 0


def _cmd_world_locate(args: argparse.Namespace) -> int:
    """Decode the overworld ENTRANCE dispatch: which world CELLS/blocks lead to which field, with the
    ScenarioCounter branches. Geography = the dispatcher's object-0 cell-tag triggers (the engine packs the walked
    CELL into the dispatch key -- ff9.cs WorldEvent); the tile's IDALL area bits are NOT the key."""
    from .world import locate as Loc
    try:
        rows = Loc.locate(game=args.game)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2

    def _dests(ds):
        if not ds:
            return "(no dispatch case: scripted world event, no walk-on warp)"
        out = []
        for d in ds:
            f = "(no warp)" if d["field"] is None else ("field %d" % d["field"] + (" %s" % d["name"] if d["name"] else ""))
            out.append((d["condition"] + " -> " if (d["condition"] != "default" or len(ds) > 1) else "") + f)
        return " | ".join(out)

    if args.block:
        bx, by = args.block
        rows = [r for r in rows if (bx, by) in r["blocks"]]
        if not rows:
            print(f"block [{bx}][{by}] carries no overworld entrance trigger (plain terrain)")
            return 0
    elif args.case is not None:
        rows = [r for r in rows if r["case"] == args.case]
    elif args.field is not None:
        rows = [r for r in rows if any(d["field"] == args.field for d in r["destinations"])]
        if not rows:
            print(f"no overworld dispatch case leads to field {args.field}")
            return 0

    for r in rows:
        head = "case %2d" % r["case"] if r["case"] is not None else "no-case"
        lm = ""
        if r["landmark"] is not None:
            lm = " ~ %s (d=%.0fu)" % (r["landmark"]["name"], r["landmark"]["dist"])
        print(f"{head}:{lm} {_dests(r['destinations'])}")
        if r["cells"]:
            cells = " ".join("(%d,%d)e%d" % c for c in r["cells"])
            blk = " ".join("[%d][%d]" % b for b in r["blocks"])
            print(f"         cells: {cells}   blocks: {blk}")
    print(f"\n{len(rows)} row(s). Read: CELLS + a field = a walk-on overworld entrance (the walked cell's packed "
          "tag picks the object-0 trigger, whose Byte[39] case picks the destination -- the tile's IDALL area "
          "bits are NOT the key, they are a cosmetic regional tag); FIELD only = a scripted/return destination "
          "with no walk-on tile; ~landmark = nearest engine navipos marker to the cells, with its distance. "
          "Destinations are BASE-game -- a deployed journey may field_remap them.")
    return 0


def _cmd_world_retarget(args: argparse.Namespace) -> int:
    """LEVER B: rewrite a world tile's entry id (tangent.x IDALL) to MAKE or MOVE an overworld entrance, deployed
    as a loose .ff9mesh override (geometry untouched). --event 1 --area N makes plain land an entrance to area N;
    --area N --only-entrances re-points an existing entrance. Needs the WorldMeshOverride engine patch."""
    from .world import extract as W, mesh as M
    if args.event is None and args.area is None and args.topograph is None:
        print("nothing to change: give --event and/or --area (and optionally --topograph)", file=sys.stderr)
        return 2
    x, y = args.block
    try:
        bm = W.read_block(x, y, disc=args.disc, lod=args.lod, game=args.game)
        before = W.block_summary(bm)["place_entrances"]
        n = M.retarget_tiles(bm, event=args.event, area=args.area, topograph=args.topograph,
                             center=(tuple(args.center) if args.center else None), radius=args.radius,
                             world_origin=W.block_world_origin(x, y), only_entrances=args.only_entrances)
        if n == 0:
            print("no tiles matched (check --center/--radius/--only-entrances vs this block's tiles)", file=sys.stderr)
            return 2
        after = W.block_summary(bm)["place_entrances"]
        dest = M.deploy_override(bm, mod_folder=args.mod_folder, game=args.game, lod=args.lod)
        from .world import discmirror as DM
        DM.auto_mirror([dest], mod_folder=args.mod_folder, skip_mirror=args.skip_mirror)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"retargeted {n} tile(s) on block[{x}][{y}] -> {dest}")
    print(f"  entrances before: {[(e['area'], e['event']) for e in before]}")
    print(f"  entrances after:  {[(e['area'], e['event']) for e in after]}")
    try:                                                     # what the DISPATCHER says about this block's cells
        from .world import locate as Loc
        from .world.entrance import cell_to_block
        a2f = Loc.case_to_fields(game=args.game)
        trig = sorted((cell, c) for c, cells in Loc.case_to_cells(game=args.game).items()
                      for cell in cells if cell_to_block(cell[0], cell[1]) == (x, y))
        for (cx, cz, ev), c in trig:
            if c is None:
                print(f"  dispatcher trigger at cell ({cx},{cz}) event {ev}: no Byte[39] case (scripted event)")
                continue
            fs = " | ".join(((cond + ": ") if cond != "default" else "") + ("field %d" % f if f is not None else "(no warp)")
                            for cond, f in a2f.get(c, [])) or "(case has no dispatch arm)"
            print(f"  dispatcher trigger at cell ({cx},{cz}) event {ev} -> case {c}: {fs}")
        if not trig:
            print("  NO dispatcher trigger covers this block's cells -- event/area bits alone warp nowhere "
                  "(world-entrance authors the trigger)")
    except (RuntimeError, FileNotFoundError, ValueError):
        pass
    print("  RELAUNCH + reach the overworld. TOPOGRAPH edits change WALKABILITY/encounters (the move gate reads "
          "the tile topograph). NOTE: --event/--area alone do NOT create a warp -- the destination comes from the "
          "world .eb object-0 trigger GetIP-keyed to the CELL position, and the tile's area bits are not read by "
          "dispatch at all (cosmetic regional tag).")
    return 0


def _cmd_world_mesh_export(args: argparse.Namespace) -> int:
    """Export block sub-mesh(es) to an OBJ for Blender mesh-surgery (splice a multi-block building / reshape / model)."""
    from .world import blendio as BIO
    blocks = [tuple(b) for b in args.block]
    try:
        info = BIO.export_obj(blocks, disc=args.disc, part=args.part, lod=args.lod, out=args.out, game=args.game)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"exported {len(info['blocks'])} block(s) {args.part} mesh -> {info['path']}  "
          f"({info['verts']} verts, {info['tris']} tris; WORLD coords, Y-up)")
    print(f"  edit in Blender (default OBJ axes), then: world-mesh-build <obj> --into-block X Y --part {args.part} "
          "--mod-folder <mod>")
    return 0


def _parse_tile_spec(spec: str) -> tuple:
    """``TOPO:VARIANT`` -> ``(topo, variant)``; shared by world-mesh-build and world-entrance --tile."""
    try:
        t, v = spec.split(":")
        return (int(t), int(v))
    except ValueError:
        raise ValueError("--tile must be TOPOGRAPH:VARIANT (e.g. 52:0); see `world-atlas-catalog`") from None


def _parse_tile_uv_spec(spec: str) -> tuple:
    """``Umin,Vmin,Umax,Vmax`` -> a 4-float tuple; shared by world-mesh-build and world-entrance --tile-uv."""
    try:
        uv = tuple(float(x) for x in spec.split(","))
    except ValueError:
        uv = ()
    if len(uv) != 4:
        raise ValueError("--tile-uv must be umin,vmin,umax,vmax (from `world-atlas-add-tile`)")
    return uv


def _cmd_world_mesh_build(args: argparse.Namespace) -> int:
    """Rebuild an edited OBJ into a block's loose .ff9mesh override + deploy (Object=building; IDALL stamped uniform)."""
    from .world import blendio as BIO
    try:
        tile = _parse_tile_spec(args.tile) if args.tile else None
        tile_uv = _parse_tile_uv_spec(args.tile_uv) if args.tile_uv else None
        if args.idall is not None and not 0 <= args.idall <= 0xFFFF:
            raise ValueError("--idall must be 0..65535 (the raw 16-bit tangent.x IDALL)")
        info = BIO.build_from_obj(args.obj, into_block=tuple(args.into_block), mod_folder=args.mod_folder,
                                  disc=args.disc, part=args.part, lod=args.lod, topograph=args.topograph,
                                  idall=args.idall, at=(tuple(args.at) if args.at else None), seat=args.seat,
                                  keep_block=args.keep_block, texture=args.texture, tile=tile, tile_uv=tile_uv,
                                  game=args.game, skip_mirror=args.skip_mirror)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    bx, by = info["into_block"]
    from .world.extract import decode_id
    d = decode_id(info["idall"])
    stamp = (f"IDALL {info['idall']} (0x{info['idall']:04X} = event {d['event']}, area {d['area']}, "
             f"topo {d['topograph']}, flags {d['flags']})" if args.idall is not None
             else f"topograph {args.topograph}")
    print(f"built {args.part} override for block[{bx}][{by}] "
          f"({info['verts']} verts, {info['tris']} tris, {stamp}) -> {info['dest']}")
    if info["idall"] in (4078, 4088, 2040):
        print("  ⓘ RENDER-ONLY stamp: WMPhysics.Raycast skips this id, so the mesh is walk-through and cannot "
              "shadow an entrance trigger. Sky-cast placement (spawn/arrive) still hits it -- keep it clear of those.")
    if info.get("replaced_stock_tris") and not args.keep_block:
        print(f"  ⚠ this REPLACED the block's stock {args.part} mesh ({info['replaced_stock_tris']} tris -- e.g. "
              f"trees/bridges/town). Re-run with --keep-block to append instead of replace.")
    if args.texture:
        print(f"  textured UV-less faces from the learned {args.part} atlas palette"
              f"{' (applied)' if info.get('textured') else ' (nothing to stamp -- OBJ already has UVs)'}")
    print("  RELAUNCH or re-enter the overworld. (Object mesh drives render + walkmesh; topo 59 = impassable blocker.)")
    return 0


def _cmd_world_texture_palette(args: argparse.Namespace) -> int:
    """Inspect the learned atlas UV palette (topograph -> donor tiles) used by `world-mesh-build --texture`."""
    from .world import palette as PAL
    try:
        pal = PAL.build_palette(disc=args.disc, part=args.part, max_blocks=args.max_blocks,
                                cache=not args.no_cache, game=args.game)
    except (ValueError, ConfigError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 2
    if not pal:
        print(f"no {args.part} UV palette found for disc {args.disc} (no blocks with UVs?)", file=sys.stderr)
        return 2
    print(f"{args.part} atlas UV palette (disc {args.disc}): topograph -> #distinct tiles, #donor faces, modal tile")
    for topo, ntiles, nfaces, modal in PAL.palette_summary(pal):
        m = "  ".join(f"({u:.3f},{v:.3f})" for u, v in modal) if modal else "-"
        print(f"  topo {topo:2}: {ntiles:4} tiles  {nfaces:5} faces   modal {m}")
    return 0


def _cmd_world_atlas_extract(args: argparse.Namespace) -> int:
    """Extract the shared overworld texture atlas (res(1_24)_terrain/_objects) to a PNG -- for previewing or
    repainting (drop the repainted PNG back via `world-atlas-reskin` for a no-DLL HD reskin). Default = the atlas
    the ENGINE renders (a loose HD mod override like Moguri's when one is stacked); --source bundle = vanilla."""
    from .world import atlas as A
    try:
        dest = A.extract_atlas(args.part, out=args.out, game=args.game, source=args.source)
        kind, loose = A.resolve_atlas_source(args.part, game=args.game) if args.source == "engine" \
            else ("bundle", None)
    except (ValueError, ConfigError, FileNotFoundError, ImportError) as e:
        print(str(e), file=sys.stderr)
        return 2
    from PIL import Image
    with Image.open(dest) as im:
        w, h = im.size
    src = f"loose override {loose}" if kind == "loose" else "the vanilla p0data bundle"
    print(f"extracted the {args.part} atlas ({w}x{h}, from {src}) -> {dest}")
    return 0


def _cmd_world_atlas_catalog(args: argparse.Namespace) -> int:
    """Render a visual tile CATALOG (contact sheet): each topograph's real donor tiles as labeled thumbnails, so you
    pick a look by eye and pass `world-mesh-build --tile TOPO:VARIANT`."""
    from .world import atlas as A
    try:
        dest = A.tile_catalog(args.part, disc=args.disc, out=args.out, per_topo=args.per_topo, game=args.game)
    except (ValueError, ConfigError, FileNotFoundError, ImportError) as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"wrote the {args.part} tile catalog -> {dest}")
    print("  pick a tile by its TOPO:VARIANT label, then: world-mesh-build <obj> ... --tile TOPO:VARIANT")
    return 0


def _cmd_world_terrain(args: argparse.Namespace) -> int:
    """Reshape walkable overworld terrain (raise/lower/flatten a hill, or a ridge/valley) by deforming the stock mesh
    across every block it touches. No DLL (loose Terrain override via s34); RELAUNCH to apply."""
    from .world import terrain as T
    at = seg = None
    if args.at:
        at = tuple(args.at)
    if args.ridge:
        seg = ((args.ridge[0], args.ridge[1]), (args.ridge[2], args.ridge[3]))
    amount = None
    if args.raise_h is not None:
        amount = abs(args.raise_h)
    elif args.lower is not None:
        amount = -abs(args.lower)
    try:
        summary = T.reshape(args.mod_folder, at=at, seg=seg, radius=args.radius, amount=amount,
                            flatten=args.flatten, height=args.height, disc=args.disc, falloff=args.falloff,
                            game=args.game, dry_run=args.dry_run, skip_mirror=args.skip_mirror)
    except (ValueError, ConfigError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 2
    verb = "would reshape" if args.dry_run else "reshaped"
    print(f"{verb} terrain ({summary['op']}, radius {summary['radius']}) across {len(summary['blocks'])} block(s):")
    for b in summary["blocks"]:
        print(f"  block {tuple(b['block'])}: moved {b['moved']} verts")
    if summary["skipped_sea"]:
        print(f"  (skipped {len(summary['skipped_sea'])} sea/no-terrain block(s): {summary['skipped_sea']})")
    if not summary["blocks"]:
        print("  nothing moved -- check --at/--radius (is the spot on land, in range?)", file=sys.stderr)
        return 2
    if not args.dry_run:
        print("  RELAUNCH to apply. Reshaping keeps the stock texture + walkability (single surface = walkable).")
    return 0


def _parse_cells(spec: str):
    """Parse a ``"x,y;x,y;..."`` (or whitespace-separated) cell list into ``[(x,y), ...]``. Also accepts a rectangular
    range ``"x0-x1,y0-y1"`` -> every cell in the box (a coast-to-island bridge / a small landmass)."""
    cells = []
    for tok in spec.replace(" ", ";").split(";"):
        tok = tok.strip()
        if not tok:
            continue
        xs, ys = tok.split(",")
        xr = [int(v) for v in xs.split("-")]
        yr = [int(v) for v in ys.split("-")]
        for x in range(min(xr), max(xr) + 1):
            for y in range(min(yr), max(yr) + 1):
                cells.append((x, y))
    # de-dup, keep order
    seen, out = set(), []
    for c in cells:
        if c not in seen:
            seen.add(c); out.append(c)
    return out


def _cmd_world_reclaim(args: argparse.Namespace) -> int:
    """RECLAIM ocean cells as walkable LAND (Path D -- new continent). Synthesizes a fresh flat, textured, walkable
    terrain override for each sea cell; the custom engine's s34 divert renders it as land. RELAUNCH to apply."""
    from .world import terrain as T
    try:
        cells = _parse_cells(args.cells)
        if not cells:
            print("no cells parsed -- give e.g. --cells '2,5;3,5' or a range '2-4,5-6'", file=sys.stderr)
            return 2
        summary = T.reclaim(args.mod_folder, cells=cells, disc=args.disc, profile=args.profile,
                            topograph=args.topograph, seg=args.seg, height=args.height, beach=args.beach,
                            shore_topo=args.shore_topo, rim_run=args.rim_run, game=args.game, dry_run=args.dry_run,
                            skip_mirror=args.skip_mirror, target_disc=args.target_disc,
                            all_sea_target=args.all_sea_target)
    except (ValueError, ConfigError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 2
    verb = "would reclaim" if args.dry_run else "reclaimed"
    print(f"{verb} {len(summary['cells'])} ocean cell(s) as walkable land "
          f"(disc {summary['disc']}, profile {summary['profile']}):")
    for c in summary["cells"]:
        edges = f", {c['water_edges']} water edge(s)" if "water_edges" in c else ""
        print(f"  cell {tuple(c['cell'])}: {c['tris']} tris / {c['verts']} verts{edges}")
    if not args.dry_run:
        print("  Needs the CUSTOM engine (s34 ocean->land divert). RELAUNCH (or exit+re-enter the overworld).")
        print("  A lone cell is an ISLAND -- reach it via the debug menu (~)->World->Teleport, or bridge from the coast with more cells.")
    return 0


def _cmd_world_coast(args: argparse.Namespace) -> int:
    """FAITHFUL coast (Path D): place a REAL FF9 coastal block at target ocean cells -- copy its terrain + write the
    Donor.txt sidecar so the engine renders that block's animated beach/sea/foam. `--list` browses coastal donors."""
    from .world import terrain as T
    from .world import extract as X
    if args.list:
        try:
            donors = X.list_coastal_donors(disc=args.disc, game=args.game, beach_only=not args.all_coasts)
        except (ValueError, ConfigError, FileNotFoundError) as e:
            print(str(e), file=sys.stderr)
            return 2
        kind = "coastal" if args.all_coasts else "beach"
        print(f"{len(donors)} real {kind} donor block(s) on disc {args.disc} (x,y -> sub-meshes) -- pick one for --donor:")
        for (x, y), subs in donors.items():
            print(f"  {x},{y}: {', '.join(subs)}")
        print("  (18,15) is the proven donor. Copy its coast to an ocean cell: world-coast --cells X,Y --donor 18,15")
        return 0
    if not args.cells or not args.donor:
        print("give --cells and --donor (or --list to browse donors)", file=sys.stderr)
        return 2
    try:
        cells = _parse_cells(args.cells)
        dx, dy = (int(v) for v in args.donor.split(","))
        # warn (don't block) if the donor isn't a coastal block -- it'll render land but no beach/foam
        try:
            coastal = X.list_coastal_donors(disc=args.disc, game=args.game, beach_only=False)
            if (dx, dy) not in coastal:
                print(f"  note: donor ({dx},{dy}) has no beach/sea sub-mesh -- it renders land but NO beach/foam "
                      f"(use --list for real coast donors)", file=sys.stderr)
        except Exception:  # noqa: BLE001 -- donor-quality warning is best-effort
            pass
        summary = T.coast(args.mod_folder, cells=cells, donor=(dx, dy), disc=args.disc, game=args.game,
                          dry_run=args.dry_run, skip_mirror=args.skip_mirror,
                          target_disc=getattr(args, "target_disc", None))
    except (ValueError, ConfigError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 2
    verb = "would place" if args.dry_run else "placed"
    print(f"{verb} real coast (donor block {tuple(summary['donor'])}) at {len(summary['cells'])} cell(s):")
    for c in summary["cells"]:
        print(f"  cell {tuple(c['cell'])}: {c['tris']} tris / {c['verts']} verts + Donor.txt")
    if not args.dry_run:
        print("  Needs the custom engine (per-cell coastal donor). RELAUNCH to apply.")
    return 0


def _cmd_world_transplant(args: argparse.Namespace) -> int:
    """VERBATIM island transplant: carry a complete real coastal block -- land + beach + the full Wang'd
    ocean, every sub-mesh -- to a custom ocean cell, with a 0-mod-4 in-cell shift + 90-degree rotation,
    offline-gated (placement census + weld audit + land fit) before any write."""
    from .world import transplant as TR

    def _fmt(v):
        if isinstance(v, float):
            return f"{v:.6g}"
        if isinstance(v, (list, tuple)):
            return "[" + ",".join(_fmt(x) for x in v) + "]"
        return str(v)

    try:
        bx, by = (int(v) for v in args.cell.split(","))
        dx, dy = (int(v) for v in args.donor.split(","))
        snx, sny = (int(v) for v in args.size.lower().split("x"))
        shift = "auto" if args.shift.strip().lower() == "auto" \
            else tuple(float(v) for v in args.shift.split(","))
        strips = args.strips.strip().lower()
        if strips not in ("auto", "all", "none"):
            strips = tuple(d.strip() for d in args.strips.split(","))
        # region grow cuts are census-validated with boundary fills + spill clips
        # auto-wired (the shared world-transplant/world-fuse core in transplant.py)
        tweaks, notes = TR.build_grow_tweaks(
            (dx, dy), (snx, sny),
            grow_cut=(args.grow_cut.split(",") if args.grow_cut else ()),
            grow_cut_z=(args.grow_cut_z.split(",") if args.grow_cut_z else ()),
            disc=args.disc, game=args.game)
        for n in notes:
            print(n)
        # the cliff-coast morphs build their tweak sets from the donor bytes, every law
        # gate offline (coastmorph.py -- the in-game-proven bump/headland pair)
        if (args.cliff_bump or args.cliff_headland or args.cliff_bay or args.cliff_lobes
                or args.beach_bump or args.beach_rebuild or args.beach_reshape
                or args.beach_slide or args.strips_rebuild or args.sand_rebuild
                or args.cap_rebuild or args.beach_mint or args.band_convert):
            from .world import coastmorph as CM
            if (snx, sny) != (1, 1):
                raise ConfigError("cliff morphs are single-cell v1 -- drop --size")
            for spec, fn in ((args.cliff_bump, CM.cliff_bump),
                             (args.cliff_headland, CM.cliff_headland),
                             (args.cliff_bay, CM.cliff_bay),
                             (args.beach_bump, CM.beach_bump),
                             (args.beach_reshape, CM.beach_reshape),
                             (args.beach_slide, CM.beach_slide)):
                if not spec:
                    continue
                s0, s1, sd = spec.split(":")
                p0 = tuple(float(v) for v in s0.split(","))
                p1 = tuple(float(v) for v in s1.split(","))
                tweaks = list(tweaks) + fn((dx, dy), p0, p1, float(sd),
                                           disc=args.disc, game=args.game)
            if args.beach_rebuild:
                s0, s1 = args.beach_rebuild.split(":")
                p0 = tuple(float(v) for v in s0.split(","))
                p1 = tuple(float(v) for v in s1.split(","))
                tweaks = list(tweaks) + CM.beach_rebuild(
                    (dx, dy), p0, p1, disc=args.disc, game=args.game)
            if args.strips_rebuild:
                tweaks = list(tweaks) + CM.strips_rebuild(
                    (dx, dy), disc=args.disc, game=args.game)
            if args.sand_rebuild:
                tweaks = list(tweaks) + CM.sand_rebuild(
                    (dx, dy), disc=args.disc, game=args.game)
            if args.cap_rebuild:
                tweaks = list(tweaks) + CM.cap_rebuild(
                    (dx, dy), disc=args.disc, game=args.game)
            if args.beach_mint:
                spec = args.beach_mint.strip().lower()
                wpart, _, lpart = spec.partition(":")
                w = None if wpart == "auto" else float(wpart)
                lnd = float(lpart) if lpart else None
                tweaks = list(tweaks) + CM.beach_mint(
                    (dx, dy), width=w, land=lnd, disc=args.disc, game=args.game)
            if args.band_convert:
                cspec, _, tpart = args.band_convert.strip().partition(":")
                ccx, ccz = (int(v) for v in cspec.split(","))
                tweaks = list(tweaks) + CM.band_convert(
                    (dx, dy), (ccx, ccz), tpart.strip().lower(),
                    disc=args.disc, game=args.game)
            if args.cliff_lobes:
                s0, s1, sd = args.cliff_lobes.split(":")
                p0 = tuple(float(v) for v in s0.split(","))
                p1 = tuple(float(v) for v in s1.split(","))
                tweaks = list(tweaks) + CM.cliff_lobes(
                    (dx, dy), p0, p1, [float(v) for v in sd.split(",")],
                    disc=args.disc, game=args.game)
        # the SHORE tweaks (the productized island-B pattern): bank_lower +
        # virgin_mint ride any placement, single-cell or region -- each verb's
        # tweak block derives from its own spec coords (build_shore_tweaks)
        if args.bank_lower or args.virgin_mint:
            from .world import coastmorph as CM
            sh, sh_notes = CM.build_shore_tweaks(
                (dx, dy), (snx, sny),
                bank=(CM.parse_bank_lower_spec(args.bank_lower)
                      if args.bank_lower else None),
                mint=(CM.parse_virgin_mint_spec(args.virgin_mint)
                      if args.virgin_mint else None),
                disc=args.disc, game=args.game)
            for n in sh_notes:
                print(n)
            tweaks = list(tweaks) + sh
        # THE GROUND-FAMILY RETILE (the translation law over the whole carried block):
        # built from the donor's own bytes, every class byte-measured, strict gate
        if getattr(args, "ground", None):
            if args.in_place:
                raise ConfigError("--ground rides the transplant path, not --in-place "
                                  "(retiling a REAL cell in place is unstudied)")
            gt = TR.GroundRetile.for_donor((dx, dy), args.ground.strip().lower(),
                                           size=(snx, sny), strips=strips,
                                           extra=args.extra,
                                           disc=args.disc, game=args.game)
            print(f"ground retile {gt.src} -> {gt.dst}: sand anchors "
                  f"{[f'{s:.4f}->{d:.4f}' for (s, d) in gt.sand_anchors] or 'none'}; "
                  f"recover cells {sorted(gt.recover_cells) or 'none'} "
                  f"(budget {gt.recover_budget} tris); degenerate-sand guard "
                  f"{gt.expected.get('sand_degenerate_recovered', 0)} tris")
            tweaks = list(tweaks) + [gt]
        if args.in_place:
            if (bx, by) != (dx, dy):
                raise ConfigError("--in-place morphs the donor's own REAL cell: --cell "
                                  "must equal --donor")
            if not tweaks:
                raise ConfigError("--in-place needs at least one morph flag to apply")
            summary = TR.morph_in_place(args.mod_folder, cell=(bx, by), tweaks=list(tweaks),
                                        disc=args.disc, game=args.game,
                                        dry_run=args.dry_run, skip_mirror=args.skip_mirror)
        else:
            kw = dict(cell=(bx, by), donor=(dx, dy), rot=args.rot, shift=shift, strips=strips,
                      tweaks=tweaks, extra=args.extra, land_margin=args.land_margin, disc=args.disc,
                      game=args.game, census_samples=args.samples,
                      allow_mod_overwrite=args.allow_mod_overwrite,
                      allow_wang_seams=args.allow_wang_seams,
                      enforce_wang_carry=args.enforce_wang_carry,
                      allow_orphan_decals=args.allow_orphan_decals,
                      enforce_orphan_decals=args.enforce_orphan_decals,
                      redress_orphans=args.redress_orphans,
                      enforce_texture_gates=args.enforce_texture_gates,
                      allow_texture_gates=args.allow_texture_gates, dry_run=args.dry_run,
                      skip_mirror=args.skip_mirror)
            if (snx, sny) == (1, 1):
                summary = TR.transplant(args.mod_folder, **kw)      # the byte-proven single-cell path
            else:
                summary = TR.transplant_region(args.mod_folder, size=(snx, sny), **kw)
    except (ValueError, ConfigError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 2
    if summary["op"] == "morph-in-place":
        print(f"IN-PLACE morph: real cell {tuple(summary['cell'])} "
              f"(touched parts: {', '.join(summary['touched'])})")
        for g in summary["gates"]:
            detail = "  ".join(f"{k}={_fmt(v)}" for k, v in g.items()
                               if k not in ("gate", "ok"))
            print(f"  GATE {g['gate']}: {detail} -> {'ok' if g['ok'] else 'FAIL'}")
        if not summary["clean"]:
            print("NOT CLEAN -- deploy refused", file=sys.stderr)
            return 2
        if args.dry_run:
            print("dry run: gates CLEAN -- re-run without --dry-run to deploy")
            return 0
        print("deployed:")
        for q in summary["deployed"]:
            print("  " + q)
        print("  Needs the CUSTOM engine (s34). RELAUNCH (or exit+re-enter the overworld) "
              "to apply; revert = delete the deployed files.")
        return 0
    sx, sz = summary["shift"]
    if summary["op"] == "transplant-region":
        (rnx, rny), (rtw, rth) = summary["size"], summary["tsize"]
        print(f"verbatim REGION transplant: donor rect {tuple(summary['donor'])}+{rnx}x{rny} -> "
              f"target rect {tuple(summary['cell'])}+{rtw}x{rth} (rot {summary['rot']} deg, "
              f"shift {sx:+g},{sz:+g}; tongue strips: {','.join(summary['strips']) or 'none'}; "
              f"coverage strips: {','.join(summary['coverage_strips']) or 'none'})")
    else:
        print(f"verbatim transplant: donor block {tuple(summary['donor'])} -> cell {tuple(summary['cell'])} "
              f"(rot {summary['rot']} deg, shift {sx:+g},{sz:+g}; tongue strips: "
              f"{','.join(summary['strips']) or 'none'}; coverage strips: "
              f"{','.join(summary['coverage_strips']) or 'none'})")
    print("  carried: " + "  ".join(f"{p}:{n}" for p, n in summary["carried"].items()))
    for key, meta in summary.get("cells", {}).items():
        blank = f"  blanked: {','.join(meta['blanked'])}" if meta["blanked"] else ""
        print(f"  cell {key}: donor prefab {tuple(meta['donor'])}  "
              + "  ".join(f"{p}:{n}" for p, n in meta["carried"].items()) + blank)
    if summary.get("blanked"):
        print(f"  blanked (all tris clipped away): {', '.join(summary['blanked'])}")
    for g in summary["gates"]:
        detail = "  ".join(f"{k}={_fmt(v)}" for k, v in g.items() if k not in ("gate", "ok", "warn"))
        print(f"  GATE {g['gate']}: {detail} -> {'ok' if g['ok'] else 'FAIL'}")
        if g.get("warn") and g["gate"] == "wang-carry":
            dn, sn = g.get("incoherent_deep", 0), g.get("incoherent_shallow", 0)
            print(f"  !! WARNING {g['gate']}: {g.get('incoherent', '?')} cropped-Wang frame seam(s) on "
                  f"the carried rim ({dn} deep sea3/sea5, {sn} shallow sea1/sea2) -- shipping FF9 abuts "
                  f"neither mid nor shallow water to the deep ring, so review these in-game and re-tile "
                  f"the rim (wang_rim_retile for sea3/sea5, the {{sea1,sea5}} ladder for sea1/sea2), or "
                  f"pass --enforce-wang-carry to refuse (--allow-wang-seams to silence).")
        if g.get("warn") and g["gate"] == "orphan-decals":
            print(f"  !! WARNING {g['gate']}: {g.get('n_orphans', '?')} orphaned transition-vocabulary "
                  f"decal(s) at cell(s) {g.get('cells')} -- a grass|desert or desert|dunes STRIPS "
                  f"fringe/straddle tile carried without the neighbourhood context that justifies it "
                  f"(a same-cell partner for straddle rows, the partner family within 2 cells for "
                  f"fringe rows), or with a topo byte breaking its own decal group's norm: "
                  f"{g.get('detail') or 'see cells above'}. Review in-game (a hard-edged ecotone seam) "
                  f"and either pass --redress-orphans to auto-fix to the wearing side's plain mains at "
                  f"build time (changes output bytes), or --enforce-orphan-decals to refuse "
                  f"(--allow-orphan-decals to silence).")
        if g.get("warn") and g["gate"] in ("tex-zero-uv", "tex-one-window", "tex-family-rect",
                                           "sea-plan"):
            print(f"  !! WARNING {g['gate']}: {g.get('detail') or 'see the gate row above'} -- the "
                  f"Rung-F UV/relief arc's own acceptance criteria (studies/overworld-topography, "
                  f"8 in-game rounds). Review in-game (a flat-sheet texture stain, a white atlas "
                  f"gutter, or a sea-plane defect) or pass --enforce-texture-gates to refuse "
                  f"(--allow-texture-gates to silence).")
    if not summary["clean"]:
        print("NOT CLEAN -- deploy refused (every gate must pass; iterate with --dry-run)", file=sys.stderr)
        return 2
    if args.dry_run:
        print("dry run: gates CLEAN -- re-run without --dry-run to deploy")
        return 0
    print("deployed:")
    for q in summary["deployed"]:
        print("  " + q)
    print("  Needs the CUSTOM engine (s34 + Donor.txt). RELAUNCH (or exit+re-enter the overworld) to apply.")
    return 0


def _cmd_world_morphs(args: argparse.Namespace) -> int:
    """The coast window scanner: discovered morph windows + probed per-verb ceilings."""
    from .world import coastscan as CS
    verbs = tuple(v.strip() for v in args.verbs.split(",")) if args.verbs else None
    mod = args.mod_folder or "<MOD>"
    try:
        if args.block:
            bx, by = (int(v) for v in args.block.split(","))
            cells = [(bx, by)]
        elif getattr(args, "all", False):
            cells = [(x, y) for y in range(20) for x in range(24)]
        else:
            raise ConfigError("pass --block BX,BY or --all")
        total = 0
        for (bx, by) in cells:
            try:
                windows = CS.scan_block(bx, by, verbs=verbs, disc=args.disc,
                                        game=args.game)
            except Exception as e:                  # a corrupt/edge block never kills a sweep
                print(f"({bx},{by}): scan error -- {e}", file=sys.stderr)
                continue
            if windows:
                print(CS.format_catalog(windows, mod_folder=mod))
                total += len(windows)
            elif args.block:
                print(f"({bx},{by}): no beach or cliff windows found")
        if len(cells) > 1:
            print(f"-- {total} windows across the sweep")
    except (ValueError, ConfigError) as e:
        print(str(e), file=sys.stderr)
        return 2
    return 0


def _cmd_world_island(args: argparse.Namespace) -> int:
    """Synthesize a fully-custom cliff ISLAND / LANDMASS: organic coastline + faithful rock wall + the real
    grass tile language (mains + verbatim meadow stamps; flat interior by default, OPT-IN rolling relief via
    --relief), gated offline (geometry, UV language, slope envelope, and the ENGINE PLACEMENT simulator)
    before deploy. Needs the custom engine (s34); re-enter the world map."""
    from .world import island as I
    from .world.grassland import GROUNDS
    gcls = GROUNDS.get(args.ground, {}).get("cls", "island")
    if gcls != "island":
        print(f"note: in stock FF9, '{args.ground}' is a {gcls.upper()} vocabulary "
              f"(scrub = grass<->dirt seam strips; brush = ~30-deg hillsides; dunes = "
              f"coast-less interior fill) -- a whole island of it reads off-language "
              f"(the 2026-07-15 ground-sampler playtest). Minting anyway.")
    beach = None
    if getattr(args, "beach", None):
        parts_ = [s.strip() for s in args.beach.split(":")]
        b0, b1 = (float(v) for v in parts_[0].split(","))
        beach = {"bearing": (b0, b1)}
        if len(parts_) > 1 and parts_[1]:
            beach["width"] = float(parts_[1])
        if len(parts_) > 2 and parts_[2]:
            beach["swash"] = float(parts_[2])
        if getattr(args, "beach_pins", None):
            beach["pins_from"] = tuple(int(v) for v in args.beach_pins.split(","))
    try:
        relief_amp = args.relief_amp if args.relief else 0.0
        kw = dict(base_radius=args.radius, seed=args.seed, lobes=args.lobes, land_height=args.height,
                  rim_run=args.rim_run, n_patches=args.patches, flat=args.flat, ground=args.ground,
                  relief_amp=relief_amp, relief_seed=args.relief_seed,
                  beach=beach, disc=args.disc, game=args.game, dry_run=args.dry_run,
                  skip_mirror=args.skip_mirror, target_disc=args.target_disc,
                  all_sea_target=args.all_sea_target)
        if args.center:
            wx, wz = (float(v) for v in args.center.split(","))
            summary = I.landmass(args.mod_folder, center=(wx, wz), **kw)
        else:
            bx, by = (int(v) for v in args.cell.split(","))
            summary = I.landmass(args.mod_folder, cell=(bx, by), **kw)
    except (ValueError, ConfigError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 2
    verb = "would deploy" if args.dry_run else "deployed"
    cx, cz = summary["center"]
    relief_note = ""
    if relief_amp > 0.0:
        p99 = summary["report"].get("main_slope_p99", 0.0)
        relief_note = f", rolling relief amp {relief_amp} (ground slope p99 {p99} deg)"
    print(f"{verb} a synthetic landmass at world ({cx:.0f}, {cz:.0f}) (radius {summary['radius']}, "
          f"seed {summary['seed']}{relief_note}) across {len(summary['blocks'])} block(s):")
    for b in summary["blocks"]:
        blk = tuple(b["block"])
        place = summary["report"].get("placement", {}).get(blk)
        extra = ""
        if place and "centre" in place:
            gy, nm, topo = place["centre"]
            extra = f"; centre grounds y={gy} on {nm} topo {topo}"
        print(f"  block {blk}: {b['tris']} tris ({b['verts']} verts){extra}")
    for g in summary["report"].get("texgates", []):
        if g.get("warn"):
            print(f"  !! WARNING {g['gate']}: {g.get('detail') or 'see the report'} -- THE TEXTURE + "
                  f"SEA GATES (studies/overworld-topography's Rung-F UV/relief arc). The mint is "
                  f"deployed; review it in-game before building on it.")
    print("all gates CLEAN (geometry, UV language, placement census: 0 MISS). "
          "~ -> World -> Teleport to the centre; a first-time block needs a world re-entry.")
    return 0


def _parse_world_point(args) -> tuple:
    """(point, exact) from --center / --near (one required)."""
    if getattr(args, "center", None):
        wx, wz = (float(v) for v in args.center.split(","))
        return (wx, wz), True
    wx, wz = (float(v) for v in args.near.split(","))
    return (wx, wz), False


def _cmd_world_forest(args: argparse.Namespace) -> int:
    """Carry a REAL canopy blob (verbatim verts/UVs/normals/topo-37) onto a DEPLOYED kit island --
    the productized island-E forest re-home (in-game proven 2026-07-12). Gates: canopy carry + the
    comprehensive step law + the perimeter walk-in simulation + placement census."""
    from .world import interior as IN
    try:
        (wx, wz), exact = _parse_world_point(args)
        dx, dy = (int(v) for v in args.donor.split(","))
        blocks = IN.read_deployed_blocks(args.mod_folder, near=(wx, wz), reach=args.reach,
                                         disc=args.disc, game=args.game)
        soup = IN.soup_from_blocks(blocks)
        res = IN.carve_forest(soup, center=(wx, wz) if exact else None,
                              near=None if exact else (wx, wz), donor=(dx, dy),
                              disc=args.disc, game=args.game)
        IN.census_gate(res["changed"], disc=args.disc, game=args.game,
                       probe=(res["center"], 37))
        if not args.dry_run:
            IN.deploy_changed(res["changed"], mod_folder=args.mod_folder, disc=args.disc,
                              game=args.game, skip_mirror=args.skip_mirror)
    except (ValueError, ConfigError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 2
    verb = "would deploy" if args.dry_run else "deployed"
    cx, cz = res["center"]
    r = res["report"]
    print(f"{verb} the canopy carry at world ({cx:.0f},{cz:.0f}): {r['blob_tris']} donor tris, "
          f"{r['dropped']} island tris carved, {r['zip_tris']} zip tris; wall rise {r['wall_rise']} / "
          f"zip rise {r['zip_rise']} (ceiling 2.34). All gates CLEAN incl. the perimeter walk-in "
          f"simulation + placement census. ~ -> World -> re-enter, then walk INTO and OVER the canopy.")
    return 0


def _cmd_world_hill(args: argparse.Namespace) -> int:
    """Raise a raised-cosine GRASS HILL on a DEPLOYED kit island by pure-Y displacement of the deployed
    bytes -- the productized island-E hill at scale (in-game proven 2026-07-12). Gates: the measured
    grass slope envelope (p99 28.6 deg), lowland-band peak cap, cracks, placement census."""
    from .world import interior as IN
    try:
        (wx, wz), exact = _parse_world_point(args)
        blocks = IN.read_deployed_blocks(args.mod_folder, near=(wx, wz),
                                         reach=max(96.0, args.radius + 10.0),
                                         disc=args.disc, game=args.game)
        soup = IN.soup_from_blocks(blocks)
        res = IN.build_hill(soup, center=(wx, wz) if exact else None,
                            near=None if exact else (wx, wz),
                            height=args.height, radius=args.radius)
        IN.census_gate(res["changed"], disc=args.disc, game=args.game)
        if not args.dry_run:
            IN.deploy_changed(res["changed"], mod_folder=args.mod_folder, disc=args.disc,
                              game=args.game, skip_mirror=args.skip_mirror)
    except (ValueError, ConfigError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 2
    verb = "would deploy" if args.dry_run else "deployed"
    cx, cz = res["center"]
    r = res["report"]
    print(f"{verb} a grass hill at world ({cx:.0f},{cz:.0f}) (H {args.height}, R {args.radius}): "
          f"{r['displaced_tris']} tris displaced, worst flank {r['worst_flank']} deg "
          f"(<= {IN.MAX_FLANK}), peak y {r['peak_y']} (<= {IN.PEAK_CAP}); "
          f"{len(res['changed'])} block(s) changed. All gates CLEAN. ~ -> World -> re-enter, "
          f"then walk the hill from all sides.")
    return 0


def _ground_choices() -> tuple:
    """The ground-family names from :data:`grassland.GROUNDS` (grass first -- the default)."""
    from .world.grassland import GROUNDS
    return tuple(GROUNDS)


def _parse_block_rect(spec: str) -> list:
    """``BX,BY`` or a rect ``BX0-BX1,BY0-BY1`` (either axis may be a range) -> block list."""
    def rng(s):
        if "-" in s:
            a, b = s.split("-")
            return list(range(int(a), int(b) + 1))
        return [int(s)]
    xs, ys = spec.split(",")
    return [(x, y) for x in rng(xs) for y in rng(ys)]


def _cmd_world_mountain(args: argparse.Namespace) -> int:
    """Carry a REAL rock massif (verbatim topo-49/7/62 geometry+UV+normals+aperture plugs) onto a
    DEPLOYED kit island -- the productized Uaho carry (in-game proven 2026-07-13). Gates: ROCK-RIGID +
    weld-safe lift + zip envelope + placement probes + census."""
    from .world import interior as IN
    try:
        (wx, wz), exact = _parse_world_point(args)
        donor_blocks = _parse_block_rect(args.donor)
        blocks = IN.read_deployed_blocks(args.mod_folder, near=(wx, wz), reach=args.reach,
                                         disc=args.disc, game=args.game)
        soup = IN.soup_from_blocks(blocks)
        res = IN.carve_mountain(soup, center=(wx, wz) if exact else None,
                                near=None if exact else (wx, wz), donor=donor_blocks,
                                ground=args.ground, disc=args.disc, game=args.game)
        IN.census_gate(res["changed"], disc=args.disc, game=args.game)
        if not args.dry_run:
            # both inner writers force-skip their own auto-mirror -- the CLI unions their
            # written paths and does ONE mirror pass for the whole carve, below.
            mountain_written = IN.deploy_changed(res["changed"], mod_folder=args.mod_folder, disc=args.disc,
                                                 game=args.game, skip_mirror=True)
            mountain_written = list(mountain_written) + list(
                IN.deploy_mountain_parts(res, mod_folder=args.mod_folder, disc=args.disc,
                                         game=args.game, skip_mirror=True))
            from .world import discmirror as DM
            DM.auto_mirror(mountain_written, mod_folder=args.mod_folder, skip_mirror=args.skip_mirror)
    except (ValueError, ConfigError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 2
    verb = "would deploy" if args.dry_run else "deployed"
    cx, cz = res["center"]
    r = res["report"]
    tx, tz = r["teleport"]
    ens = (f" + THE ENSEMBLE CARRY ({r['ensemble_tris']} falls/river/object tris riding "
           f"the same rigid map, Donor.txt -> {res['donor_ref']})") if r.get("ensemble_tris") else ""
    print(f"{verb} the massif carry at world ({cx:.0f},{cz:.0f}) rot {r['rot_deg']}deg across "
          f"{len(r['blocks'])} block(s): {r['blob_tris']} donor tris (+{r['plugs']} aperture "
          f"plugs), {r['dropped']} island tris carved, {r['zip_tris']} zip tris{ens}; peak y "
          f"{r['peak_y']}, rock rigidity drift {r['rock_rigid'] * 100:.1f}% (<= 3.5), apron "
          f"slope {r['apron_slope']} deg (<= {IN.MTN_APRON_SLOPE}). All gates CLEAN incl. the "
          f"placement probes + census. ~ -> World -> re-enter, then teleport ({tx}, {tz}) and "
          f"face the massif; walk the whole rim.")
    return 0


def _cmd_world_mirror(args: argparse.Namespace) -> int:
    """Mirror a mod folder's Disc1 WorldMap overrides into the Disc4 tree (the overworld ships TWO
    asset trees -- disc1 serves discs 1-3, disc4 has its own -- and every s34 lookup is keyed on the
    engine's currentDisc, so un-mirrored custom land VANISHES on disc 4). Free-ride donor-prefab
    parts pin as explicit source-disc-byte overrides."""
    from .world import discmirror as DM
    try:
        out = DM.mirror(args.mod_folder, src_disc=args.src_disc, dst_disc=args.dst_disc,
                        game=args.game, dry_run=args.dry_run)
    except (ValueError, ConfigError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 2
    verb = "would mirror" if args.dry_run else "mirrored"
    print(f"{verb} {len(out['mirrored'])} file(s) + {len(out['pinned'])} free-ride pin(s) into "
          f"Disc{args.dst_disc}; {len(out['skipped'])} cell(s) skipped."
          + (" RELAUNCH to apply." if not args.dry_run else ""))
    for blk, why in out["skipped"]:
        print(f"  skipped {blk}: {why}")
    return 0


def _cmd_world_water(args: argparse.Namespace) -> int:
    """Synthesize graded OPEN-OCEAN water (shallow->deep) on sea cells from a built-in depth gradient -- the faithful
    marching-band synthesizer (Sea3/Sea5/Sea4 alphabet, byte-proven UVs). Needs the custom engine (s34); RELAUNCH."""
    from .world import water as W
    try:
        cells = _parse_cells(args.cells)
        if not cells:
            print("no cells parsed -- give e.g. --cells '3,17' or a range '2-4,16-18'", file=sys.stderr)
            return 2
        dx, dy = (int(v) for v in args.donor.split(","))
        if args.verbatim:
            sx, sy = (int(v) for v in args.verbatim.split(","))
            summary = W.deploy_verbatim(args.mod_folder, cells=cells, source=(sx, sy), donor=(dx, dy),
                                        disc=args.disc, height=args.height, game=args.game, dry_run=args.dry_run,
                                        skip_mirror=args.skip_mirror)
        elif args.reproduce:
            sx, sy = (int(v) for v in args.reproduce.split(","))
            summary = W.reproduce(args.mod_folder, cells=cells, source=(sx, sy), donor=(dx, dy), seed=args.seed,
                                  disc=args.disc, height=args.height, game=args.game, dry_run=args.dry_run,
                                  skip_mirror=args.skip_mirror)
        else:
            summary = W.water(args.mod_folder, cells=cells, donor=(dx, dy), deep_dir=args.deep, shallows=args.shallows,
                              threshold=args.threshold, span=args.span, noise=args.noise, seed=args.seed,
                              disc=args.disc, height=args.height, game=args.game, dry_run=args.dry_run,
                              skip_mirror=args.skip_mirror)
    except (ValueError, ConfigError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 2
    if args.verbatim:
        verb = "would place" if args.dry_run else "placed"
        print(f"{verb} VERBATIM real ocean block {tuple(summary['source'])} (donor {tuple(summary['donor'])}) "
              f"at {len(summary['cells'])} cell(s) -- the A/B reference for world-water:")
        for c in summary["cells"]:
            print(f"  cell {tuple(c['cell'])}: carried {c['carried']} ({c['verts']} verts)")
    elif args.reproduce:
        verb = "would reproduce" if args.dry_run else "reproduced"
        print(f"{verb} block {tuple(summary['source'])}'s arrangement with SYNTHESIZED tiles (donor "
              f"{tuple(summary['donor'])}) at {len(summary['cells'])} cell(s) -- the fidelity A/B for world-water:")
        for c in summary["cells"]:
            s = c["shades"]
            print(f"  cell {tuple(c['cell'])}: sea3={s['sea3']} sea5={s['sea5']} sea4={s['sea4']} "
                  f"(sea3|sea4 seams={c['adjacency_violations']})")
    else:
        verb = "would synthesize" if args.dry_run else "synthesized"
        desc = f"graded, deeper toward {summary['deep_dir']}" if summary.get("deep_dir") else "open ocean (mostly deep)"
        print(f"{verb} ocean water ({desc}, donor {tuple(summary['donor'])}) at {len(summary['cells'])} cell(s):")
        for c in summary["cells"]:
            s = c["shades"]
            print(f"  cell {tuple(c['cell'])}: sea3={s['sea3']} sea5={s['sea5']} sea4={s['sea4']} "
                  f"(sea3|sea4 seams={c['adjacency_violations']})")
        if any(c["adjacency_violations"] for c in summary["cells"]):
            print("  WARNING: a sea3|sea4 direct adjacency slipped the transition band -- report this (should be 0).",
                  file=sys.stderr)
    if not args.dry_run:
        print("  Needs the CUSTOM engine (s34 sea->land divert). RELAUNCH (or exit+re-enter the overworld).")
        print("  A lone cell is reachable via the debug menu (~) -> World -> Teleport; a contiguous run of cells stays seamless.")
    return 0


def _cmd_world_atlas_reskin(args: argparse.Namespace) -> int:
    """Deploy a repainted atlas PNG as a no-DLL HD reskin (T2) -- keep the SAME UV layout, replace the pixels."""
    from .world import atlas as A
    try:
        dest = A.deploy_atlas(args.png, args.part, mod_folder=args.mod_folder, game=args.game)
    except (ValueError, ConfigError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"deployed the repainted {args.part} atlas -> {dest}")
    print("  RELAUNCH to apply. Keep the same UV layout (tile positions) or existing geometry will sample wrong.")
    return 0


def _cmd_world_atlas_add_tile(args: argparse.Namespace) -> int:
    """T3: paint a NEW tile into a FREE (unused) atlas region + deploy the reskinned atlas. Prints the UV rect to
    stamp on custom geometry with `world-mesh-build --tile-uv`. Give a tile PNG, or omit for a magenta test pattern."""
    from .world import atlas as A
    try:
        tile = A.load_tile_png(args.png) if args.png else A.make_test_tile(args.size)
        info = A.add_tile(tile, args.part, mod_folder=args.mod_folder, game=args.game, tile_px=args.size)
    except (ValueError, ConfigError, FileNotFoundError, ImportError) as e:
        print(str(e), file=sys.stderr)
        return 2
    u0, v0, u1, v1 = info["uv_rect"]
    print(f"painted a new {args.part} tile at atlas px {info['box']} -> reskinned atlas {info['dest']}")
    print(f"  UV rect: {u0:.4f},{v0:.4f},{u1:.4f},{v1:.4f}")
    print(f"  now stamp it on geometry:  world-mesh-build <obj> --into-block X Y --part {args.part} "
          f"--tile-uv {u0:.4f},{v0:.4f},{u1:.4f},{v1:.4f} --mod-folder {args.mod_folder}")
    print("  RELAUNCH to apply.")
    return 0


def _cmd_world_mesh_trim(args: argparse.Namespace) -> int:
    """Auto-remove faces from a building OBJ. `--floor` drops the low flat base courtyard-floor/apron -- the flat
    faces that read as a brown 'dirt' patch under the top-down overworld camera -- keeping walls/towers/roofs."""
    from .world import blendio as BIO
    if not args.floor:
        print("nothing to trim: pass --floor (drops the low flat base floor/apron faces)", file=sys.stderr)
        return 2
    try:
        obj = BIO.read_obj(args.obj)
        before = len(obj["faces"])
        trimmed = BIO.trim_floor(obj, base_height=args.base_height, up_threshold=args.up_threshold)
        BIO.write_obj(trimmed, args.out)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"trimmed {before} -> {trimmed['kept']} tris (dropped {trimmed['dropped']} low up-facing base floor/apron "
          f"face(s)) -> {args.out}")
    print("  walls/towers/roofs kept; deploy with `world-entrance --building <out>` (or `world-mesh-build`).")
    return 0


def _cmd_world_entrance(args: argparse.Namespace) -> int:
    """One-shot: author a whole custom OVERWORLD ENTRANCE -- the trigger function (into every world dispatcher that
    carries the destination case, all 7 langs), the event tiles, and (optionally) a modelled building -- all folded
    into one deploy. Reversible = delete the printed files (or re-deploy the journey)."""
    from pathlib import Path
    from .world import entrance as EN
    if not args.extend_nameplate_band and args.cell is None:
        print("--cell X Z is required (except with --extend-nameplate-band)", file=sys.stderr)
        return 2
    if args.extend_nameplate_band:
        s = EN.extend_nameplate_band(args.mod_folder, dry_run=args.dry_run)
        verb = "would extend" if args.dry_run else "extended"
        print(f"{verb} THE NAMEPLATE BAND (func-0xB range arms -> cases 65-{EN.VIRGIN_CASE_MAX}, minus "
              f"the 91-93 vehicle trio) in {len(s['written'])} dispatcher file(s); "
              f"{len(s['skipped'])} already extended. Explored words: gEventGlobal bytes 2006-2017 "
              f"(flags.NAMEPLATE_EXPLORED_FLOOR, kit-reserved). Stock cases 1-64/91-93/156+ compute "
              f"byte-equivalently (256-case interpreter proof in tests). Re-enter the world to apply.")
        return 0
    n_dest = sum(v is not None for v in (args.field, args.case, args.field_direct))
    if n_dest != 1:
        print("give a destination: exactly one of --field <id> / --case <n> (the dispatcher-case "
              "route, real base fields; see `world-locate`) or --field-direct <id> (a CUSTOM "
              "field: the trigger warps it directly)", file=sys.stderr)
        return 2
    if (args.texture or args.tile or args.tile_uv) and not args.building:
        print("--texture/--tile/--tile-uv texture the --building mesh -- pass --building <obj> too", file=sys.stderr)
        return 2
    if args.action_prompt and args.field_direct is None:
        print("--action-prompt needs --field-direct <id> (it gates a CUSTOM destination's warp on Confirm; the "
              "real dispatcher-case route already owns town-entry behavior)", file=sys.stderr)
        return 2
    if args.nameplate and not args.action_prompt:
        print("--nameplate needs --action-prompt (it rides the confirm-gated entrance -- it summons the native "
              "location nameplate + \"Enter with [X]\" HUD while the tile is stood on)", file=sys.stderr)
        return 2
    if args.nameplate_name is not None:
        if args.field_direct is None:
            print("--nameplate-name needs --field-direct <id> (the CUSTOM-name nameplate SURGERY warps a custom "
                  "field through a repointed dead AREA-switch case)", file=sys.stderr)
            return 2
        if args.action_prompt or args.nameplate:
            print("--nameplate-name is the NATIVE-FLOW surgery nameplate -- drop --action-prompt/--nameplate "
                  "(the superseded self-summon path)", file=sys.stderr)
            return 2
    building = None
    try:
        if args.building:
            if args.building_idall is not None and not 0 <= args.building_idall <= 0xFFFF:
                raise ValueError("--building-idall must be 0..65535 (the raw 16-bit tangent.x IDALL)")
            building = {"obj": args.building, "at": (tuple(args.building_at) if args.building_at else None),
                        "seat": not args.no_seat, "keep_block": not args.replace_town, "topograph": args.topograph,
                        "idall": args.building_idall,
                        "texture": args.texture, "tile": (_parse_tile_spec(args.tile) if args.tile else None),
                        "tile_uv": (_parse_tile_uv_spec(args.tile_uv) if args.tile_uv else None)}
        info = EN.author_entrance(
            cell=tuple(args.cell), mod_folder=args.mod_folder, field=args.field, case=args.case,
            direct_field=args.field_direct, event=args.event,
            disc=args.disc, lod=args.lod, trigger_at=(tuple(args.trigger_at) if args.trigger_at else None),
            trigger_radius=args.trigger_radius, set_tile_area=not args.no_tile_area, building=building,
            flatten_pad=args.flatten_pad, block_footprint=not args.hollow_building, fresh=args.fresh,
            trigger_only=args.trigger_only, prompt=args.action_prompt, nameplate=args.nameplate,
            nameplate_name=args.nameplate_name, nameplate_case=args.nameplate_case,
            dry_run=args.dry_run, game=args.game, skip_mirror=args.skip_mirror)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2

    tag = info["tag_hex"]
    fld = info["field"]
    head = "PLAN (dry run -- nothing written)" if info["dry_run"] else "authored overworld entrance"
    print(f"{head}: cell {tuple(info['cell'])} tag {tag} -> case {info['case']}"
          + (f" -> field {fld}" if fld is not None else " (case has no default field)"))
    print(f"  {info['dest_note']}")
    if args.action_prompt:
        print("  action-prompt: raises the \"!\" bubble; warps only on a Confirm press (faithful town-style entry)")
    if args.nameplate:
        print("  nameplate: SELF-PAINTS the NATIVE entrance HUD (location nameplate + \"Enter with [X]\") every "
              "frame on the tile via SetTextVariable + WindowAsync(6/7) -- no Byte[24]/Byte[38] writes; Confirm warps")
    if info.get("surgery"):
        nr = info["name_rename"]
        if info["case"] > 60:
            print(f"  VIRGIN-CASE nameplate ({info['case']}): the trigger self-summons the native HUD with its own "
                  f"case; NO stock bytes are edited (the AREA switch tops out at 60, so there is nothing to repoint)")
            print(f"    warp branch: [Byte[24]=100 mute] + [set explored word {info['explored_word']} bit "
                  f"{info['explored_bit']} (gEventGlobal bit {info['explored_bit_index']})] + zone-in + "
                  f"Field({info['field']})")
        else:
            print(f"  nameplate SURGERY: the entrance runs the game's REAL native flow; the location nameplate shows "
                  f"\"{nr['to']}\" (a CUSTOM name)")
            print(f"    dead AREA-switch case {info['case']} repointed -> [set explored word {info['explored_word']} "
                  f"bit {info['explored_bit']} (gEventGlobal bit {info['explored_bit_index']})] + Field({info['field']})")
        print(f"    name registered into world text block {nr['text_block']} at locId {nr['locid']} "
              f"(split[{info['case']}]) -- shows \"?\" until first visit, then the name (faithful)")
        for p in info.get("name_text_files", []):
            print(f"      -> {p}")
    wrote = info["dispatchers_written"]
    print(f"  trigger func -> {len(wrote)} dispatcher(s) x {len(info['langs'])} langs"
          f" = {len(wrote) * len(info['langs'])} .eb file(s): {', '.join(w['name'].replace('evt_world_', '') for w in wrote) or '(none)'}")
    if info["dispatchers_skipped"]:
        print(f"  skipped (cell already has an entrance there): {', '.join(s.replace('evt_world_', '') for s in info['dispatchers_skipped'])}")
    if info.get("trigger_only"):
        print("  trigger-only: the deployed terrain / event tiles / building were left untouched")
    else:
        pad = f", flattened {info['pad_flattened']} pad verts" if info.get("pad_flattened") else ""
        blk = f", {info['footprint_blocked']} tiles blocked under the building" if info.get("footprint_blocked") else ""
        # report the area field HONESTLY: --no-tile-area leaves each tile's own area untouched, and printing
        # the case there reads as "we stamped it", which is exactly how a wrong deploy gets believed
        area = f"area={info['case']}" if info.get("tile_area_stamped", True) else "area=KEPT (--no-tile-area)"
        print(f"  event tiles: {info['tiles_set']} triangle(s) set event={info['event']} {area} "
              f"in block{tuple(info['block'])}{pad}{blk}")
    if info.get("terrain_override"):
        print(f"    -> {info['terrain_override']}")
    if info.get("building"):
        b = info["building"]
        if b.get("planned"):
            print(f"  building (planned): {b['obj']} at {tuple(b['at'])} seat={b['seat']} keep_block={b['keep_block']}"
                  + (" texture=True" if b.get("texture") else ""))
        else:
            print(f"  building: {b['verts']} verts / {b['tris']} tris (kept stock town: {b['kept_stock']}) -> {b['dest']}")
            if args.texture or args.tile or args.tile_uv:
                print("  textured the building's UV-less faces"
                      f"{' (applied)' if b.get('textured') else ' (nothing to stamp -- OBJ already has UVs)'}")
    for note in info.get("notes", []):
        print(f"  note: {note}")
    if info.get("warning"):
        print(f"  WARNING: {info['warning']}", file=sys.stderr)
    if info["backups"]:
        print(f"  backed up {len(info['backups'])} pre-edit dispatcher file(s) -> {Path(info['backups'][0]).parent}")
    if not info["dry_run"]:
        _enter = ('stand on the cell -- a "!" appears; press Confirm to enter (faithful town-style)'
                  if args.action_prompt else
                  "walk ONTO the cell -- stepping on the event tile fires the warp (auto-warp)")
        print("  RELAUNCH the game (new loose assets aren't hot-reloaded), reach the disc-%d overworld, and %s. "
              "(Mesh overrides need the WorldMeshOverride engine patch.)"
              % (info.get("disc", args.disc), _enter))
    return 0


def _cmd_world_fuse(args: argparse.Namespace) -> int:
    """Validate + deploy a multi-placement transplant LAYOUT (the cross-donor FUSE): several
    verbatim landmasses in adjacent target rects, every shared border certified open water
    (see world/fuse.py -- the fuse law). Layout = a toml of [[placement]] tables."""
    import tomllib
    from .world import fuse as FU, transplant as TR
    try:
        with open(args.layout, "rb") as fh:
            doc = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as e:
        print(f"cannot read {args.layout}: {e}", file=sys.stderr)
        return 2
    rows = doc.get("placement", [])
    if not rows:
        print("the layout has no [[placement]] tables", file=sys.stderr)
        return 2
    try:
        placements = []
        for i, row in enumerate(rows):
            for req in ("cell", "donor", "size"):
                if req not in row:
                    raise ValueError(f"[[placement]] #{i}: missing '{req}'")
            pl = {"cell": tuple(int(v) for v in row["cell"]),
                  "donor": tuple(int(v) for v in row["donor"]),
                  "size": tuple(int(v) for v in row["size"]),
                  "rot": int(row.get("rot", 0))}
            sh = row.get("shift", (0.0, 0.0))
            pl["shift"] = "auto" if sh == "auto" else tuple(float(v) for v in sh)
            if "land_margin" in row:
                pl["land_margin"] = float(row["land_margin"])
            if "strips" in row:
                pl["strips"] = row["strips"]
            # tweak builders: grow cuts + the SHORE tweaks (the productized
            # island-B pattern -- optional [placement.bank_lower] /
            # [placement.virgin_mint] sub-tables, same builder as the
            # world-transplant flags). Attached as a FACTORY, not a list:
            # tweak objects are stateful and fuse_layout applies each placement
            # twice (gates + deploy), rebuilding fresh per pass.
            def _build_tweaks(row=row, donor=pl["donor"], size=pl["size"],
                              notes=None):
                tw, n = TR.build_grow_tweaks(donor, size,
                                             grow_cut=row.get("grow_cut", ()),
                                             grow_cut_z=row.get("grow_cut_z", ()),
                                             disc=args.disc, game=args.game)
                n = list(n)
                if (row.get("bank_lower") is not None
                        or row.get("virgin_mint") is not None):
                    from .world import coastmorph as CM
                    shore, n2 = CM.build_shore_tweaks(
                        donor, size,
                        bank=row.get("bank_lower"), mint=row.get("virgin_mint"),
                        disc=args.disc, game=args.game)
                    tw = list(tw) + shore
                    n += n2
                if notes is not None:
                    notes.extend(n)
                return tw
            notes = []
            tweaks = _build_tweaks(notes=notes)   # validate early, collect notes
            for n in notes:
                print(f"placement #{i}: {n}")
            if tweaks:
                pl["tweaks_factory"] = _build_tweaks
            placements.append(pl)
        out = FU.fuse_layout(args.mod_folder, placements, disc=args.disc, game=args.game,
                             allow_overwrite=args.allow_overwrite, dry_run=args.dry_run,
                             skip_mirror=args.skip_mirror)
    except (ValueError, ConfigError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 2
    head = "LAYOUT PLAN (dry run -- nothing written)" if out["dry_run"] else \
        ("fused layout deployed" if out["clean"] else "layout REFUSED -- nothing written")
    print(f"{head}: {len(out['placements'])} placement(s)")
    for i, s in enumerate(out["placements"]):
        (rnx, rny) = s["size"]
        print(f"  #{i}: donor {tuple(s['donor'])}+{rnx}x{rny} -> cell {tuple(s['cell'])} "
              f"(rot {s['rot']}, clean={s['clean']})")
    for g in out["fuse_gates"]:
        mark = "ok" if g["ok"] else "FAIL"
        extra = ""
        if g["gate"].startswith("fuse["):
            extra = f"  plane={g['plane']:g} rows={g['rows']}"
            if g["n_bad"]:
                extra += f" bad={g['n_bad']} e.g. {g['bad'][0]}"
            if g.get("grade_jumps"):
                extra += f" grade-jumps={g['grade_jumps']} (reported, not failing)"
        elif g["gate"] == "existing-overrides" and g["n_files"]:
            extra = f"  {g['n_files']} file(s) already deployed at target cells" + \
                ("" if g["ok"] else " -- pass --allow-overwrite to re-deploy over them")
        elif g["gate"].startswith("placement") and not g["ok"]:
            extra = f"  failing gates: {', '.join(g['bad'])}"
        print(f"  GATE {g['gate']}: {mark}{extra}")
    if out["deployed"]:
        print(f"deployed {len(out['deployed'])} file(s); RELAUNCH (or exit+re-enter the "
              f"overworld) to apply. Needs the CUSTOM engine (s34 + Donor.txt).")
    return 0 if out["clean"] else 2


def _cmd_world_environment(args: argparse.Namespace) -> int:
    """Emit Memoria's ``Environment.txt`` into a mod folder from a ``[world_environment]`` toml -- overworld
    weather (mist/rain/light), world effects, and place alternate-forms. No DLL (a stock-Memoria seam);
    RELAUNCH to apply."""
    import tomllib
    from .world import environment as ENV
    try:
        with open(args.config, "rb") as fh:
            doc = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as e:
        print(f"cannot read {args.config}: {e}", file=sys.stderr)
        return 2
    cfg = doc.get("world_environment", doc)             # accept a [world_environment] block or a bare doc
    problems = ENV.validate_environment(cfg)
    if problems:
        for p in problems:
            print(f"  {p}", file=sys.stderr)
        return 2
    if args.dry_run:
        print(ENV.build_environment_txt(cfg), end="")
        return 0
    try:
        dest = ENV.write_environment(cfg, mod_folder=args.mod_folder, game=args.game)
    except (ValueError, ConfigError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 2
    print(f"wrote {dest}")
    print("  RELAUNCH the game (or re-enter the overworld) to apply. The mod folder must be in "
          "Memoria.ini [Mod] FolderNames.")
    return 0


def _cmd_world_minimap(args: argparse.Namespace) -> int:
    """Composite the mod folder's deployed overworld land onto the in-game all-world map image."""
    from .world import navimap as NM
    try:
        s = NM.composite_world_map(args.mod_folder, disc=args.disc, dry_run=args.dry_run)
    except (ValueError, FileNotFoundError, ConfigError) as e:
        print(str(e), file=sys.stderr)
        return 2
    head = "PLAN (dry run -- nothing written)" if s["dry_run"] else "world map composited"
    print(f"{head}: {s['blocks']} deployed block(s), {s['tris']} land tris drawn "
          f"(fill {s['fill']}, art rect {tuple(s['art_rect'])})")
    print(f"  base: {s['source']}")
    if not s["dry_run"]:
        print(f"  -> {s['out']}")
        print("  RELAUNCH to apply; the override must sit ABOVE any folder shipping its own "
              "map PNG (MoguriMain) in Memoria.ini FolderNames AND Priorities (edit BOTH, same "
              "order, game+launcher closed -- the launcher rewrites FolderNames from Priorities).")
    return 0


def _cmd_world_rename_markers(args: argparse.Namespace) -> int:
    """Rename overworld minimap markers: rewrite the world text block (68) txid-0 label at ``locId+1`` and shadow
    it per-language into the mod folder (``embeddedasset/text/<lang>/field/68.mes``). No DLL; RELAUNCH to apply."""
    import tomllib
    from .world import navimap as NM
    try:
        with open(args.config, "rb") as fh:
            doc = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as e:
        print(f"cannot read {args.config}: {e}", file=sys.stderr)
        return 2
    cfg = doc.get("marker_rename", [])
    try:
        renames = NM.resolve_renames(cfg)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 2
    if not renames:
        print("no [[marker_rename]] entries found (need {name|locid, to})", file=sys.stderr)
        return 2
    if args.dry_run:
        for loc in sorted(renames):
            print(f"  locId {loc} ({NM.MARKER_NAMES.get(loc, '?')}) -> {renames[loc]!r}")
        return 0
    langs = None if args.lang == "all" else [args.lang]
    try:
        written = NM.deploy_marker_renames(cfg, mod_folder=args.mod_folder, game=args.game, langs=langs)
    except (ValueError, ConfigError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 2
    lang_names = sorted({p.parent.parent.name for p in written})
    print(f"renamed {len(renames)} marker(s) -> {len(written)} .mes file(s) [{', '.join(lang_names)}]")
    for loc in sorted(renames):
        print(f"  locId {loc} ({NM.MARKER_NAMES.get(loc, '?')}) -> {renames[loc]!r}")
    print("  RELAUNCH the game to apply. The mod folder must be in Memoria.ini [Mod] FolderNames.")
    return 0


def _cmd_world_encounter_rate(args: argparse.Namespace) -> int:
    """Retune the overworld random-encounter FREQUENCY: rewrite the world dispatchers' RunWorldCode(26) writes
    (w_frameEventBattleProb) per-language into the mod folder. No DLL (a plain .eb immediate rewrite, stacking on
    world-entrance); RELAUNCH or re-enter the overworld to apply."""
    from pathlib import Path
    from .world import encounter as EC
    langs = None if args.lang == "all" else [args.lang]
    try:
        summary = EC.deploy_encounter_rate(
            mod_folder=args.mod_folder, game=args.game,
            multiplier=args.multiplier, set_prob=args.set_prob, peaceful=args.peaceful,
            langs=langs, dry_run=args.dry_run)
    except (ValueError, ConfigError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 2
    verb = "would retune" if args.dry_run else "retuned"
    print(f"{verb} overworld encounter rate ({summary['mode']}) across {len(summary['dispatchers'])} dispatcher(s)")
    for d in summary["dispatchers"]:
        for w in (d.get("writes") or []):
            beat = "Main_Init" if w["tag"] == 0 else "Main_Reinit" if w["tag"] == 10 else f"tag{w['tag']}"
            print(f"  {d['name']} {beat}: prob {w['from']} (p=1/{w['from']+1}) -> {w['to']} (p=1/{w['to']+1})")
    if not args.dry_run:
        lang_names = sorted({Path(p).parent.name for p in summary["written"]})
        print(f"  wrote {len(summary['written'])} .eb file(s) [{', '.join(lang_names)}]")
        print("  RELAUNCH the game (or re-enter the overworld) to apply. The mod folder must be in "
              "Memoria.ini [Mod] FolderNames.")
    return 0


_FRIENDLY_NAMES = ("Mu", "Ghost", "Ladybug", "Yeti", "Nymph", "Jabberwock", "Feather Circle", "Garuda", "Yan")


def _cmd_world_encounters(args: argparse.Namespace) -> int:
    """Inspect / re-table the overworld random-encounter TABLE (discmr.img sub-table 3, 355 records). `--list`
    (or no `--config`) dumps it; `--config <toml>` applies [[set]]/[remap] edits and deploys a whole-file
    discmr.img override into the mod folder. No DLL (AssetManager mod-override); RELAUNCH to apply."""
    from .world import worldpack as WP
    try:
        d = WP.load_discmr(args.disc, game=args.game)
    except (ValueError, ConfigError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 2
    if not args.config:                                            # inspect
        print(f"discmr.img disc{args.disc}: {len(d.encounters)} encounter records, {len(d.specials)} special rows")
        if getattr(args, "zones", False):                          # per-ZONE breakdown (the selection unit)
            print("  zone -> areas (the debug menu's 'area' field) -> record slice -> topographs:  "
                  "target with [[set]] area=N or zone=Z")
            for z in range(WP.ZONE_COUNT):
                sl = WP.zone_slice(z)
                topos = sorted({d.encounters[i].topograph for i in sl})
                s0 = sorted({d.encounters[i].scene[0] for i in sl})
                print(f"    zone {z:2}: areas {WP.zone_areas(z)}  rec {sl.start}-{sl.stop - 1}  "
                      f"topo {topos}  scene[0]={s0}")
            return 0
        if args.all:
            for i, r in enumerate(d.encounters):
                print(f"  [{i:3}] topo={r.topograph:2} fog={r.fog} scene={r.scene}")
        else:                                                      # per-topograph summary (author-friendly)
            from collections import defaultdict
            by_topo: dict = defaultdict(list)
            for i, r in enumerate(d.encounters):
                by_topo[r.topograph].append(r)
            print("  topograph -> records (distinct scene[0] ids):  [--all for every record]")
            for topo in sorted(by_topo):
                rs = by_topo[topo]
                s0 = sorted({r.scene[0] for r in rs})
                print(f"    topo {topo:2}: {len(rs):2} rec  scene[0]={s0}")
        print("  special rows (the Friendly-Monster creatures; 1-based indices into the table):")
        for i, area in enumerate(d.specials):
            live = [a for a in area if a != WP.SPECIAL_EMPTY]
            print(f"    [{i}] {_FRIENDLY_NAMES[i]}: {live}")
        return 0
    import tomllib
    try:
        with open(args.config, "rb") as fh:
            doc = tomllib.load(fh)
    except (OSError, tomllib.TOMLDecodeError) as e:
        print(f"cannot read {args.config}: {e}", file=sys.stderr)
        return 2
    cfg = doc.get("encounters", doc)                               # accept an [encounters] block or a bare doc
    try:
        summary = WP.apply_config(d, cfg)
        dest = WP.deploy_discmr(d, mod_folder=args.mod_folder, game=args.game, dry_run=args.dry_run)
    except (ValueError, ConfigError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 2
    for s in summary["sets"]:
        m = s["match"]
        sel = ", ".join(f"{k}={v}" for k, v in m.items() if v is not None) or "all"
        print(f"  set [{sel}] -> {s['count']} record(s)")
    if summary["remapped"]:
        print(f"  remapped {summary['remapped']} scene slot(s)")
    print(f"  {'would write' if args.dry_run else 'wrote'} {dest}")
    if not args.dry_run:
        print("  RELAUNCH the game to apply. The mod folder must be in Memoria.ini [Mod] FolderNames.")
    return 0


def _cmd_battle_actions(args: argparse.Namespace) -> int:
    """List the shared PLAYER ability table (Actions.csv) + the scriptId formula catalog (read-live)."""
    _safe_console()
    from .battle import battlecsv as B
    if args.script_ids:
        for sid in sorted(B.SCRIPT_IDS):
            print(f"  {sid:>3}  {B.SCRIPT_IDS[sid]}")
        print(f"\n{len(B.SCRIPT_IDS)} stock battle-calc formulas. Re-pointing an action's scriptId at one of "
              "these is pure CSV (no DLL);\na NEW formula needs a Memoria.Scripts.<Mod>.dll (not the engine DLL).")
        return 0
    if not B.available(game=args.game):
        print("needs your FF9 install (StreamingAssets/Data/Battle/Actions.csv); set FF9_GAME_PATH "
              "or run from the game dir.", file=sys.stderr)
        return 2
    rows = B.actions(game=args.game)
    if args.filter:
        f = args.filter.lower()
        rows = [a for a in rows if f in a.name.lower()]
    for a in rows:
        print(f"  {a.id:>3}  {a.summary()}")
    print(f"\n{len(rows)} action(s) -- the PLAYER ability table. (Enemy attacks live per-scene in the raw16; "
          "see `battle-scene`.)")
    return 0


def _cmd_characters(args: argparse.Namespace) -> int:
    """List the playable characters' base combat stats (BaseStats.csv, read-live) -- the ``[[character]]``
    targets. The player side of battle tuning; the growth curve = ``[[leveling]]`` (Leveling.csv)."""
    _safe_console()
    from .battle import characterdelta as CD
    cat = CD.basestats_catalog(game=args.game)
    if cat is None:
        print("needs your FF9 install (StreamingAssets/Data/Characters/BaseStats.csv); set FF9_GAME_PATH "
              "or run from the game dir.", file=sys.stderr)
        return 2
    for name, cid, stats in cat:
        print(f"  {cid:>2}  {name:<10}  " + "  ".join(f"{s[:3].title()} {v}" for s, v in stats))
    print(f"\n{len(cat)} characters -- the [[character]] targets (BaseStats.csv, partial per-id delta). The "
          "99-step\ngrowth curve is Leveling.csv ([[leveling]] level = N, whole-file).")
    return 0


def _cmd_battle_ai(args: argparse.Namespace) -> int:
    """Disassemble a battle scene's enemy AI (EVT_BATTLE_<scene>.eb) -- the read-only 'see the enemy's AI' view:
    Main_Init spawn-binding + per-type AI functions by tag, with named commands + annotated expressions.
    With ``--asm`` instead ASSEMBLES an expression (the disassembler's inverse) -> its bytes + a re-disasm proof."""
    _safe_console()
    if args.asm is not None:                                # Phase-6c-i: assemble an AI expression -> bytes
        from .eb import exprasm, disasm
        try:
            b = exprasm.assemble(args.asm)
        except exprasm.AssembleError as e:
            print(f"assemble error: {e}", file=sys.stderr)
            return 2
        back, _ = disasm.pretty_expr(b, 0)
        print(f"bytes ({len(b)}): {b.hex(' ')}\nre-disasm: {back}")
        return 0
    from .battle import battleai as BA
    if args.asm_block is not None:                          # Phase-6c-ii: assemble a COMMAND block -> bytes
        from .eb import cmdasm
        try:
            b = cmdasm.assemble_block(args.asm_block.replace(";", "\n"))   # ';' separates lines for a 1-line arg
        except cmdasm.CmdAsmError as e:
            print(f"assemble error: {e}", file=sys.stderr)
            return 2
        print(f"bytes ({len(b)}): {b.hex(' ')}")
        for off, mn, ops in BA._decode_func_pretty(b, 0, len(b)):   # the re-disassembly proof
            print(f"  [{off}] {mn}({', '.join(ops)})")
        return 0
    if not args.donor:
        print("a scene name is required (or use --asm / --asm-block to assemble AI source)", file=sys.stderr)
        return 2
    if args.lint:                                           # Phase-6c-iii: lint a scene's enemy AI offline
        from .battle import ailint, extract, scene_data
        try:
            eb = BA._scene_eb(args.donor, game=args.game)
        except (RuntimeError, FileNotFoundError, ValueError) as e:
            print(str(e), file=sys.stderr)
            return 2
        atk = None
        try:                                                # the scene's attack count enables the Attack-idx check
            assets = extract.read_scene_assets(args.donor, game=args.game)
            if assets.get("raw16"):
                atk = scene_data.parse_counts(assets["raw16"])[2]
        except Exception:                                   # noqa: BLE001 -- atk-count is optional
            atk = None
        issues = ailint.lint_ai(eb, atk_count=atk)
        if not issues:
            print(f"# {args.donor} AI: clean ({'no attack-idx check -- ' if atk is None else ''}no issues)")
            return 0
        print(f"# {args.donor} AI: {len(issues)} issue(s)")
        for i in issues:
            print(f"  {i}")
        return 1
    try:
        print(BA.scene_ai_sites(args.donor, game=args.game) if args.sites
              else BA.analyze_scene(args.donor, game=args.game))
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    return 0


def _cmd_battle_seq(args: argparse.Namespace) -> int:
    """Disassemble a battle scene's attack SEQUENCES (btlseq.raw17) -- the read-only 'see the choreography'
    view: each sub_no (attack index) as named instructions with resolved anim ids. With ``--sites`` lists the
    patchable operands (offset/value) for ``[[scene.seq_patch]]`` instead of the disassembly."""
    _safe_console()
    from .battle import seqdis as SD
    if args.asm is not None:                            # assemble a sequence source -> bytes + a re-disasm proof
        from .battle import seqasm
        try:
            instrs = seqasm.assemble(args.asm)
        except seqasm.SeqAsmError as e:
            print(f"assemble error: {e}", file=sys.stderr)
            return 2
        b = seqasm.assemble_bytes(instrs)
        print(f"bytes ({len(b)}): {b.hex(' ')}")
        for ins in instrs:                              # the re-disassembly proof (canonical form)
            print(f"  {seqasm.to_source([ins])}")
        return 0
    if not args.donor:
        print("a scene name is required (or use --asm to assemble a sequence source)", file=sys.stderr)
        return 2
    if args.lint:                                       # lint a scene's sequences offline (anim-code range, etc.)
        from .battle import seqauthor
        try:
            raw17 = SD._scene_raw17(args.donor, game=args.game)
        except (RuntimeError, FileNotFoundError, ValueError) as e:
            print(str(e), file=sys.stderr)
            return 2
        issues = seqauthor.lint_seq(raw17)
        if not issues:
            print(f"# {args.donor} sequences: clean")
            return 0
        print(f"# {args.donor} sequences: {len(issues)} issue(s)")
        for i in issues:
            print(f"  {i}")
        return 1
    try:
        out = (SD.scene_seq_sites(args.donor, game=args.game) if args.sites
               else SD.analyze_scene_seq(args.donor, game=args.game))
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    print(out)
    return 2 if "<unreadable" in out else 0           # a malformed raw17 disasm exits non-zero (parity w/ --sites)


def _cmd_ability_gems(args: argparse.Namespace) -> int:
    """List the support abilities + their gem COSTS (AbilityGems.csv, read-live) -- the ``[[ability_gem]]``
    targets. Re-costing a support ability is the build-economy balance lever."""
    _safe_console()
    from .battle import characterdelta as CD
    cat = CD.ability_gems_catalog(game=args.game)
    if cat is None:
        print("needs your FF9 install (StreamingAssets/Data/Characters/Abilities/AbilityGems.csv); set "
              "FF9_GAME_PATH or run from the game dir.", file=sys.stderr)
        return 2
    f = (args.filter or "").lower()
    rows = [r for r in cat if not f or f in r[0].lower()]
    for name, aid, gems in rows:
        print(f"  {aid:>2}  {name:<16}  {gems:>3} gems")
    print(f"\n{len(rows)} support abilities -- the [[ability_gem]] targets (AbilityGems.csv, partial per-id "
          "delta).\n[[ability_gem]] ability = \"<name or id>\", gems = N (re-cost it; cheaper = stronger builds).")
    return 0


def _cmd_ability_features(args: argparse.Namespace) -> int:
    """Preview the ``AbilityFeatures.txt`` a field.toml's ``[[ability_feature]]`` blocks emit (the no-DLL
    ability-EFFECT DSL: SA/AA/CMD), or ``--tags`` for the per-kind ``[code=...]`` tag + SA-name reference. The
    actual file is written + deployed (reversibly) by build/deploy_field; RELAUNCH to apply (startup-loaded)."""
    _safe_console()
    from pathlib import Path
    from .battle import abilityfeatures as AF
    from .battle import characterdelta as CD
    if args.tags or not args.toml:
        print("Supporting abilities (>SA, id 0-63) -- the [[ability_feature]] kind=\"SA\" targets:")
        names = CD._SA_NAMES
        for r in range(0, len(names), 4):
            print("  " + "".join(f"{i:>2} {names[i]:<15}" for i in range(r, min(r + 4, len(names)))))
        print("\n>SA feature types (the first token of a body line):\n  " + " / ".join(AF._SA_FEATURE_KW))
        print("\n>AA  [code=...] tags:  " + "  ".join(sorted(AF._AA_TAGS)))
        print(">CMD [code=...] tags:  " + "  ".join(sorted(AF._CMD_TAGS)))
        print("\n[[ability_feature]] kind=\"SA\"|\"AA\"|\"CMD\"  ability=\"<name/id>\"  cumulate=true  "
              "features=\"\"\"...\"\"\"")
        print("  >AA ability = an Actions.csv id 0-191 (or a name, resolved at build); >CMD = an int command id.")
        return 0
    import tomllib
    try:
        raw = tomllib.loads(Path(args.toml).read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as e:
        print(f"failed to read {args.toml}: {e}", file=sys.stderr)
        return 2
    feats = raw.get("ability_feature")
    if not feats:
        print("no [[ability_feature]] blocks in this toml.", file=sys.stderr)
        return 0
    try:
        lines, warnings = AF.build_lines(feats, game=args.game)
    except AF.AbilityFeatureError as e:
        print(str(e), file=sys.stderr)
        return 2
    print("\n".join(lines))
    for w in warnings:
        print(f"warning: {w}", file=sys.stderr)
    return 0


def _cmd_battle_telemetry(args: argparse.Namespace) -> int:
    """Install/remove the battle-calc TELEMETRY hook (the Scripts-DLL Overload channel) in a LIVE mod folder,
    or summarize a captured JSONL. Install compiles the mod's whole ``Scripts/Sources`` tree (existing battle
    formulas + the hook) into ``Memoria.Scripts.<folder>.dll`` -- RELAUNCH to load."""
    _safe_console()
    from pathlib import Path
    from .battle import telemetry as T
    from .battle.scriptcompile import ScriptCompileError
    if args.report is not None or args.clear:
        try:
            jsonl = Path(args.report) if args.report else T.default_jsonl_path(args.game)
        except ConfigError as e:
            print(str(e), file=sys.stderr)
            return 2
        if args.clear:
            if jsonl.is_file():
                jsonl.unlink()
                print(f"cleared {jsonl}")
            else:
                print(f"nothing to clear ({jsonl} absent)")
            return 0
        print(f"telemetry: {jsonl}")
        print(T.summarize(T.read_events(jsonl)))
        return 0
    if not args.mod_folder:
        print("battle-telemetry needs a mod folder (name or path) to install into -- or --report/--clear",
              file=sys.stderr)
        return 2
    cand = Path(args.mod_folder)
    if cand.is_dir():
        mod_root = cand.resolve()
    else:
        try:
            mod_root = find_mod_root(find_game_path(args.game), args.mod_folder)
        except ConfigError as e:
            print(str(e), file=sys.stderr)
            return 2
        if not mod_root.is_dir():
            print(f"mod folder not found: {mod_root}", file=sys.stderr)
            return 2
    try:
        if args.off:
            dll = T.remove(mod_root, game=args.game)
            print(f"telemetry hook removed from {mod_root.name}"
                  + (f" (mod DLL recompiled from its remaining battle formulas: {dll.name})" if dll
                     else " (mod DLL deleted -- no other scripted content)"))
        else:
            dll = T.install(mod_root, game=args.game)
            print(f"telemetry hook installed -> {dll}")
            print(f"  events append to <game>/{T.JSONL_BASENAME}")
            print("  RELAUNCH the game to load it (scripts DLLs load once at title; a menu reload won't).")
            print("  summarize a capture:  ff9mapkit battle-telemetry --report")
    except ScriptCompileError as e:
        print(str(e), file=sys.stderr)
        return 2
    return 0


def _cmd_battle_patch(args: argparse.Namespace) -> int:
    """Preview the ``BattlePatch.txt`` a field.toml's ``[[battle_patch]]`` / ``[[battle_enemy]]`` /
    ``[[battle_attack]]`` blocks emit (offline, no install) -- or, with ``--fields``, the catalog of tunable
    field names by token. The actual patch is written + deployed (reversibly) by build/deploy_field."""
    _safe_console()
    from .battle import battlepatch as BP
    if args.fields:
        for title, m in (("enemy   (Enemy: / EnemyByName: / AnyEnemyByName:)", BP.ENEMY_FIELDS),
                         ("attack  (Attack: / AttackByName: / AnyAttackByName:)", BP.ATTACK_FIELDS),
                         ("pattern (Pattern:)", BP.PATTERN_FIELDS),
                         ("scene   (Battle: flags)", BP.SCENE_FLAGS)):
            print(f"\n{title}")
            by_engine: dict = {}
            for k, (eng, _enc, _max) in m.items():
                by_engine.setdefault(eng, []).append(k)
            for eng, keys in by_engine.items():
                print(f"  {'/'.join(keys):<30} -> {eng}")
        print("\nelement/status fields take NAMES (weak = [\"Fire\"], auto_status = [\"Protect\"]); drop/steal "
              "take 4 item names/ids ('none'=empty); scene flags take true/false; the rest take integers.")
        return 0
    if not args.toml:
        print("give a field.toml to preview, or `--fields` for the tunable-field catalog", file=sys.stderr)
        return 2
    import tomllib
    from pathlib import Path
    try:
        raw = tomllib.loads(Path(args.toml).read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as e:
        print(f"could not read {args.toml}: {e}", file=sys.stderr)
        return 2
    try:
        lines, warns = BP.build_lines(raw.get("battle_patch"), raw.get("battle_enemy"), raw.get("battle_attack"))
    except BP.BattlePatchError as e:
        print(f"battle-patch error: {e}", file=sys.stderr)
        return 1
    if not lines:
        print("no [[battle_patch]] / [[battle_enemy]] / [[battle_attack]] blocks in this field.toml")
        return 0
    print("# --- BattlePatch.txt (emitted from this field.toml; merged with BGM + deployed reversibly) ---")
    for ln in lines:
        print(ln)
    for w in warns:
        print(f"  ! {w}", file=sys.stderr)
    return 0


def _item_label(ids) -> str:
    from . import items as I
    names = [I.name_of(i) or str(i) for i in ids if i != 255]
    return "/".join(names) if names else "-"


def _cmd_battle_scene(args: argparse.Namespace) -> int:
    """Inspect a REAL battle scene's enemy data: read-only fork its raw16 and print every enemy type's
    stats / affinities / rewards + the attack table. The 'import -> SEE it' step for battle tuning."""
    _safe_console()
    from .battle import battlecsv as B, extract as bextract, scene_codec, scenelint
    try:
        assets = bextract.read_scene_assets(args.donor, game=args.game)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    scene = scene_codec.parse_scene(assets["raw16"])
    flags = ([f for f, on in (("back-attack", scene.back_attack), ("preemptive", scene.preemptive),
                              ("no-escape", not scene.can_escape), ("no-EXP", scene.no_exp)) if on])
    print(f"scene {args.donor} (id {assets['donor_id']}): {scene.pat_count} pattern(s), "
          f"{scene.typ_count} enemy type(s), {scene.atk_count} attack(s)"
          + (f"  [{', '.join(flags)}]" if flags else ""))
    names = _best_effort_monster_names(assets["donor_id"], args.game)   # rung 8: real display names, best-effort
    for t, m in enumerate(scene.monsters):
        label = names[t] if names and t < len(names) and names[t] else None
        print(f"\n  enemy type {t}{f' -- {label}' if label else ''}:  HP {m.hp}  MP {m.mp}  Lv {m.level}  "
              f"(Spd {m.speed} Str {m.strength} Mag {m.magic} Spr {m.spirit})")
        print(f"    defence: phys {m.phys_def}/{m.phys_evade}  mag {m.mag_def}/{m.mag_evade}  hit {m.hit_rate}")
        aff = [f"{lab} {'/'.join(B.decode_elements(mask))}"
               for lab, mask in (("weak", m.weak_element), ("null", m.guard_element),
                                 ("absorb", m.absorb_element), ("half", m.half_element)) if B.decode_elements(mask)]
        if aff:
            print(f"    elements: {';  '.join(aff)}")
        st = [f"{lab} {'/'.join(B.decode_status(mask))}"
              for lab, mask in (("resist", m.resist_status), ("auto", m.auto_status),
                                ("initial", m.initial_status)) if B.decode_status(mask)]
        if st:
            print(f"    status: {';  '.join(st)}")
        print(f"    rewards: gil {m.gil}  EXP {m.exp}  card {m.win_card}  "
              f"drop {_item_label(m.drop)}  steal {_item_label(m.steal)}")
    if scene.attacks:
        print(f"\n  attack table ({scene.atk_count}):")
        for i, a in enumerate(scene.attacks):
            els = B.decode_elements(a.elements)
            extra = ("  " + "/".join(els) if els else "") \
                + (f"  rate {a.rate}" if a.rate not in (0, 255) else "") + (f"  {a.mp} MP" if a.mp else "")
            print(f"    [{i}] {B.script_name(a.script_id)}  pow {a.power}{extra}")
    aps = sorted({p.ap for p in scene.patterns})
    print(f"\n  AP reward (per formation): {', '.join(str(a) for a in aps)}")
    _print_found_in_line(assets["donor_id"], args.game)                 # rung 8: where this scene is fought
    print()
    print(scenelint.format_findings(scenelint.lint_scene(scene)))
    print(f"\n  Fork + tune:  ff9mapkit battle-import --fork-scene {args.donor} ...  "
          "then [scene]/[[scene.enemy]] in battle.toml")
    return 0


def _best_effort_monster_names(scene_id: int, game) -> "list | None":
    """``battle-scene``'s real-name enrichment (rung 8, ``battle.locate``) -- a census/locate/install hiccup
    must never break the (already-working) stat printout above it, so any failure here just falls back to
    the bare ``enemy type N`` label."""
    try:
        from .battle import locate as LOC
        return LOC.monster_names(scene_id, game=game)
    except Exception:                                        # noqa: BLE001 -- purely additive, never fatal here
        return None


def _print_found_in_line(scene_id: int, game) -> None:
    """``battle-scene``'s "found in" enrichment (rung 8): the real place(s) that fight this scene (via
    ``battle.locate``), or its honest classification bucket when the census never reached it. Best-effort,
    same non-fatal contract as :func:`_best_effort_monster_names`."""
    try:
        from .battle import locate as LOC
        places = LOC.scene_places(scene_id, game=game)
        if places:
            descs = []
            for g in places:
                loc_name = g["arc_name"] or "an unmapped field"
                fids = g["fields"]
                fdesc = f"field {fids[0]}" if len(fids) == 1 else f"fields {', '.join(str(f) for f in fids)}"
                descs.append(f"{loc_name} ({fdesc}, {'/'.join(g['kinds'])})")
            print(f"\n  found in: {'; '.join(descs)}")
        else:
            print(f"\n  found in: not reached by any real field's census [{LOC.classify(scene_id, game=game)}]")
    except Exception:                                        # noqa: BLE001 -- purely additive, never fatal here
        pass


# ------------------------------------------------------------------------------- `encounters` (rungs 7+8) ---
def _resolve_scene_ref(ref, *, strict: bool = True) -> "int | None":
    """Resolve an ``encounters`` scene reference -- a raw id, a full ``BSC_...`` name, or the short
    donor-style name the other ``battle-*`` verbs take (e.g. ``EF_R007``, no ``BSC_`` prefix) -- to a scene
    id. ``strict=False`` (auto-detecting a bare positional query) returns None instead of raising when
    nothing matches, so the caller can fall through to a place/monster search; ``strict=True`` (an explicit
    ``--scene``) re-raises :func:`catalog.resolve_scene`'s own ``ValueError`` (with its did-you-mean hints)
    for the caller's standard ``(RuntimeError, FileNotFoundError, ValueError)`` handler to report."""
    from . import catalog as C
    s = str(ref).strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    candidates = [s] if s.upper().startswith("BSC_") else [s, f"BSC_{s}"]
    last_err: "ValueError | None" = None
    for cand in candidates:
        try:
            return C.resolve_scene(cand)
        except ValueError as e:
            last_err = e
    if strict:
        raise last_err
    return None


def _match_arc_keys(query: str, arcs: dict) -> list:
    """Arc keys whose key/name/zone contains ``query`` (case-insensitive substring) -- the PLACE axis of
    ``encounters``'s query matching."""
    q = query.strip().lower()
    if not q:
        return []
    return sorted(ak for ak, meta in arcs.items()
                  if q in ak.lower() or q in (meta.get("name") or "").lower()
                  or q in (meta.get("zone") or "").lower())


def _rows_for_arcs(census: dict, field_arc: dict, arc_keys) -> list:
    """Every ``(scene_id, field_id, kind)`` triplet touched by a field in one of ``arc_keys`` -- the forward
    (place -> battles) direction, read straight off the census (no reverse index needed)."""
    arc_set = set(arc_keys)
    rows = []
    for fid, rec in census.items():
        if field_arc.get(fid) not in arc_set:
            continue
        for sid in rec["random"]:
            rows.append((sid, fid, "random"))
        for sid in rec["scripted"]:
            rows.append((sid, fid, "scripted"))
    return rows


def _place_label(field_arc: dict, arcs: dict, field_id: int) -> str:
    ak = field_arc.get(field_id)
    return (arcs.get(ak, {}).get("name") if ak else None) or "(unmapped field)"


def _print_encounters_summary(census: dict, field_arc: dict, arcs: dict, classification: dict) -> int:
    """``encounters`` with no args -- one row per PLACE with any battle content (random/scripted scene
    counts), plus the honest scene-classification totals (``--unresolved`` gives the full gap detail)."""
    from collections import Counter
    by_arc: dict = {}
    for fid, rec in census.items():
        g = by_arc.setdefault(field_arc.get(fid), {"fields": set(), "random": set(), "scripted": set()})
        g["fields"].add(fid)
        g["random"].update(rec["random"])
        g["scripted"].update(rec["scripted"])
    rows = sorted(((arcs.get(ak, {}).get("name") if ak else None) or "(unmapped field)", g)
                  for ak, g in by_arc.items())
    print(f"{len(rows)} place(s) with battle content ({len(census)} field(s) total, {len(arcs)} places known):\n")
    print(f"  {'place':<34} {'fields':>6} {'random':>7} {'scripted':>9}")
    for name, g in rows:
        print(f"  {name:<34} {len(g['fields']):>6} {len(g['random']):>7} {len(g['scripted']):>9}")
    tot = Counter(classification.values())
    print(f"\n  scene coverage: {tot.get('placed', 0)} placed, {tot.get('model-bucket', 0)} model-bucket, "
          f"{tot.get('overworld', 0)} overworld, {tot.get('unplaced', 0)} unplaced  "
          "(`--unresolved` for the honest gap detail)")
    print("\n  ff9mapkit encounters <place|monster|scene>   -- narrow to one place, monster, or scene")
    return 0


def _print_scene_detail(sid: int, field_arc: dict, arcs: dict, classification: dict, scene_sites: dict,
                         args: argparse.Namespace, names_ok: bool) -> int:
    """``--scene``/auto-detected-scene detail: places (or the honest classification if unplaced) + monster/
    attack names (skipped when ``names_ok`` is False, i.e. ``--no-names``)."""
    from . import catalog as C
    name = C.scene_name(sid) or f"scene {sid}"
    cls = classification.get(sid, "unplaced")
    print(f"scene {sid}  ({name})  [{cls}]")
    sites = scene_sites.get(sid, [])
    if not sites:
        print("  not reached by any real field's census (see `--unresolved` for the honest gap buckets)")
    else:
        groups: dict = {}
        for fid, kind in sites:
            g = groups.setdefault(field_arc.get(fid), {"fields": set(), "kinds": set()})
            g["fields"].add(fid)
            g["kinds"].add(kind)
        for ak, g in sorted(groups.items(),
                             key=lambda kv: (arcs.get(kv[0], {}).get("name") if kv[0] else None) or "~"):
            loc_name = (arcs.get(ak, {}).get("name") if ak else None) or "(unmapped field)"
            fids = ", ".join(str(f) for f in sorted(g["fields"]))
            print(f"  {loc_name:<28} field(s) {fids}  ({'/'.join(sorted(g['kinds']))})")
    if names_ok:
        from .battle import locate as LOC
        names = LOC.monster_names(sid, lang=args.lang, game=args.game)
        atks = LOC.attack_names(sid, lang=args.lang, game=args.game)
        print("  monsters: " + (", ".join(n or "?" for n in names) if names
                                 else "(no resolvable text pool for this scene)"))
        if atks:
            print("  attacks:  " + ", ".join(a or "?" for a in atks))
    print("\n  Full enemy data:  ff9mapkit battle-scene <donor-name>  (see `scenes` to find the short name)")
    return 0


def _print_encounter_matches(rows, field_arc: dict, arcs: dict, lang: str, game, names_ok: bool) -> None:
    """One line per unique ``(scene_id, field_id, kind)`` battle -- the shared printer for both
    ``encounters`` query axes (a place match and a monster match land here identically)."""
    from . import catalog as C
    from .battle import locate as LOC
    cache: dict = {}
    for sid, fid, kind in sorted(set(rows)):
        name = C.scene_name(sid) or f"scene {sid}"
        place = _place_label(field_arc, arcs, fid)
        line = f"  scene {sid:<4} {name:<18} {kind:<9} {place} (field {fid})"
        if names_ok:
            if sid not in cache:
                cache[sid] = LOC.monster_names(sid, lang=lang, game=game)
            if cache[sid]:
                line += "  -- " + ", ".join(n or "?" for n in cache[sid])
        print(line)


def _print_encounters_unresolved(rep: dict) -> int:
    """``--unresolved`` -- the honest coverage report :func:`locate.unresolved_report` already assembles."""
    print(f"battle-location coverage (cache v{rep['cache_version']}, {rep['scene_count']} scene id(s), "
          f"{rep['field_count']} field(s) with battle content):\n")
    tot = rep["classification_totals"]
    for k in ("placed", "model-bucket", "overworld", "unplaced"):
        print(f"  {k:<14} {tot.get(k, 0)}")
    if rep["computed_operand_fields"]:
        print(f"\n  computed-operand SetRandomBattles (operand not statically readable): "
              f"field(s) {rep['computed_operand_fields']}")
    if rep["junk_scene_ids"]:
        print(f"  engine-skipped 'Junk?' scene id(s): {rep['junk_scene_ids']}")
    if rep["name_gaps"]:
        extra = f"  (+{len(rep['name_gaps']) - 20} more)" if len(rep["name_gaps"]) > 20 else ""
        print(f"  scene id(s) with no resolvable name data ({len(rep['name_gaps'])}): "
              f"{rep['name_gaps'][:20]}{extra}")
    if rep["fields_without_arc"]:
        print(f"  real field id(s) never placed in a place: {rep['fields_without_arc']}")
    return 0


def _cmd_encounters(args: argparse.Namespace) -> int:
    """Browse battle LOCATIONS: what real place(s) trigger a battle scene, and where a monster appears.
    No args -> a per-place summary. A query auto-detects a place name/zone token, a monster name, or a
    ``BSC_`` scene name/id (force one axis with ``--monster``/``--place``). Differs from ``scenes`` (a bare
    ``BSC_`` name/id catalog list, no place or monster join) and ``world-encounters`` (the OVERWORLD terrain
    encounter TABLE only -- this covers field-scoped town/dungeon/boss battles)."""
    _safe_console()
    if args.monster and args.no_names:
        print("--monster needs monster-name data; drop --no-names", file=sys.stderr)
        return 2
    from .battle import locate as LOC
    try:
        if args.unresolved:
            return _print_encounters_unresolved(LOC.unresolved_report(game=args.game, force=args.force))
        if args.no_names:
            # A warm map (memo/disk) already holds the census -- reuse it (the census loop is the ~6s
            # dominant cost); only a cold miss pays the census-only private helpers, which skip the
            # raw16/text-pool name scans a full build_map() would add.
            bm = None if args.force else LOC.cached_map(game=args.game)
            if bm is not None:
                census, field_arc, arcs = bm.census, bm.field_arc, bm.arcs
                classification, scene_sites = bm.classification, bm.scene_sites
            else:
                census, _computed = LOC._census(game=args.game)
                field_arc, arcs = LOC._zone_join()
                classification, _junk = LOC._classify_scenes(census)
                scene_sites = LOC._scene_site_index(census)
            names_ok = False
        else:
            bm = LOC.build_map(game=args.game, force=args.force)
            census, field_arc, arcs = bm.census, bm.field_arc, bm.arcs
            classification, scene_sites = bm.classification, bm.scene_sites
            names_ok = True
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2

    try:
        if args.scene:
            sid = _resolve_scene_ref(args.scene)
            return _print_scene_detail(sid, field_arc, arcs, classification, scene_sites, args, names_ok)

        if not args.query:
            return _print_encounters_summary(census, field_arc, arcs, classification)

        rows: list = []
        axes: list = []
        sid = None if args.monster else _resolve_scene_ref(args.query, strict=False)
        if sid is not None and not args.place:
            return _print_scene_detail(sid, field_arc, arcs, classification, scene_sites, args, names_ok)
        if not args.monster:
            arc_hits = _match_arc_keys(args.query, arcs)
            if arc_hits:
                rows += _rows_for_arcs(census, field_arc, arc_hits)
                axes.append("place")
        if not args.place and names_ok:
            mon_hits = LOC.find_monster(args.query, lang=args.lang, game=args.game)
            if mon_hits:
                for msid in sorted({s for s, _ in mon_hits}):
                    rows += [(msid, fid, kind) for fid, kind in scene_sites.get(msid, [])]
                axes.append("monster")
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2

    if not rows:
        skip_note = " (monster search needs names -- drop --no-names)" if not names_ok and not args.place else ""
        print(f"no place, monster, or scene matches {args.query!r}{skip_note}. Try `ff9mapkit scenes "
              f"{args.query}` or `ff9mapkit encounters --unresolved`.", file=sys.stderr)
        return 1
    print(f"{len(set(rows))} battle(s) match {args.query!r}  [{'/'.join(axes)}]:\n")
    _print_encounter_matches(rows, field_arc, arcs, args.lang, args.game, names_ok)
    return 0


def _cmd_list_fields(args: argparse.Namespace) -> int:
    from . import extract
    from . import catalog
    if args.players or args.non_zidane:
        return _list_fields_with_players(args)
    try:
        rows = extract.list_fields(None, game=args.game)     # fetch all; filter below so a numeric ID query
    except (RuntimeError, FileNotFoundError) as e:            # (e.g. `list-fields 2951`) matches too, not just
        print(str(e), file=sys.stderr)                       # the FBG/MAPID name substring the index is keyed by
        return 2
    folder_ids: dict = {}                                    # a shared background folder maps to several field
    for fid, (fbg, _evt) in catalog.FIELD_BY_ID.items():     # ids (the same room at different story beats)
        folder_ids.setdefault(fbg, []).append(fid)
    for v in folder_ids.values():
        v.sort()
    pat = (args.pattern or "").lower()

    def _match(folder, mapid, ids):
        if not pat:
            return True
        if pat in folder or pat in mapid.lower():
            return True
        return any(pat in str(i) for i in ids)               # match by field ID (the id the number IS)

    shown = 0
    for folder, area, mapid in rows:
        ids = folder_ids.get(folder, [])
        if not _match(folder, mapid, ids):
            continue
        idcol = ", ".join(str(i) for i in ids) if ids else "?"
        print(f"  {idcol:<14}  area {area:>2}  {mapid:<28}  ({folder})")
        shown += 1
    print(f"{shown} field(s)")
    return 0


def _cmd_find_field(args: argparse.Namespace) -> int:
    from . import extract
    rows = extract.find_fields(args.query, archive_dir=args.archive)
    if not rows:
        print(f"no field matches {args.query!r}", file=sys.stderr)
        return 1
    for r in rows:
        label = r["name"] or r["evt"] or r["fbg"]        # friendly HW name, else EVT name, else FBG
        loc = f"  {r['folder']}" if r["folder"] else ""
        print(f"{r['id']:>5}  {label:<30}  {r['fbg']}{loc}")
    return 0


def _list_fields_with_players(args: argparse.Namespace) -> int:
    """`list-fields --players` / `--non-zidane`: enrich the list with WHO you control in each field
    (id-centric -- an alternate event script on a shared background is its own row). Reads each .eb."""
    _safe_console()
    from . import forkreport as FR
    if not args.pattern:
        print("Resolving the controlled player across all fields (reads each .eb, ~30s)...", file=sys.stderr)
    try:
        rows, scanned = FR.field_players(game=args.game, pattern=args.pattern,
                                         non_zidane_only=args.non_zidane)
    except (RuntimeError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 2
    for fp in rows:
        label = fp.player + (" *" if fp.non_zidane else "")
        print(f"  {fp.field_id:>5}  {label:<24}  {fp.fbg}")
    nz = [fp for fp in rows if fp.non_zidane]
    cast = sum(1 for fp in nz if fp.playable)
    drivers = len(nz) - cast
    scope = " non-Zidane" if args.non_zidane else ""
    # break the non-Zidane rows into real playable-cast DONORS vs GEO cutscene-driver "players"
    if nz:
        bd = f"{cast} playable-cast donor(s)" + (f", {drivers} cutscene-driver model(s)" if drivers else "")
        tail = (f"   (* = non-Zidane: {bd}; fork a donor via --verbatim --swap-player)"
                if not args.non_zidane else f"   ({bd}; fork a donor via --verbatim --swap-player)")
    else:
        tail = ""
    print(f"{len(rows)}{scope} field(s) of {scanned} scanned{tail}")
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


def _cmd_items_inspect(args: argparse.Namespace) -> int:
    """Decode + render a save's items / equipment / gil (read-only) from the Memoria extra file -- the
    load-authoritative store. One report per populated slot of a SavedData_ww.dat, or one for a given extra."""
    from . import save_items as SI
    try:
        reports = SI.inspect(args.save)
    except Exception as e:                                              # noqa: BLE001
        print(f"could not read items/equipment: {e}")
        return 2
    multi = len(reports) > 1
    for i, (label, rep) in enumerate(reports):
        if multi:
            print(("\n" if i else "") + f"=== {label} ===")
        print(SI.render_report(rep))
    return 0


def _cmd_items_set_gil(args: argparse.Namespace) -> int:
    """Write a save's gil. Given a Memoria extra-save directly -> writes that extra (load-authoritative). Given a
    SavedData_ww.dat container + a slot -> writes the encrypted MAIN block AND mirrors to the Memoria extra when
    present (so a vanilla no-extra save is editable too). Dry-run by default; --apply performs it (backup-guarded)."""
    from . import save_items as SI
    try:
        if SI.load_extra_common(args.save)[0] is not None:             # a Memoria extra-save directly
            rep = SI.set_gil(args.save, args.gil, dry_run=not args.apply, backup=not args.no_backup)
            print(SI.render_gil_write(rep))
        else:                                                          # a SavedData_ww.dat container + slot
            block = SI._resolve_block(slot=args.slot, save=args.save_no, autosave=args.autosave)
            res = SI.set_gil_in_save(args.save, block, args.gil, dry_run=not args.apply,
                                     backup=not args.no_backup)
            print(SI.render_gil_dual(res))
    except Exception as e:                                              # noqa: BLE001
        print(f"could not set gil: {e}")
        return 2
    return 0


def _cmd_items_set_item(args: argparse.Namespace) -> int:
    """Set an item's inventory count (count 0 removes it). On a container, dual-writes the MAIN block + the
    Memoria extra mirror (so a vanilla no-extra save is editable too); on an extra-save directly, writes that.
    Dry-run unless --apply."""
    from . import save_items as SI
    try:
        if SI.load_extra_common(args.save)[0] is not None:             # a Memoria extra-save directly
            rep = SI.set_item(args.save, args.item, args.count, dry_run=not args.apply, backup=not args.no_backup)
            print(SI.render_item_write(rep))
        else:                                                          # a SavedData_ww.dat container + slot
            block = SI._resolve_block(slot=args.slot, save=args.save_no, autosave=args.autosave)
            res = SI.set_item_in_save(args.save, block, args.item, args.count, dry_run=not args.apply,
                                      backup=not args.no_backup)
            print(SI.render_item_dual(res))
    except Exception as e:                                              # noqa: BLE001
        print(f"could not set item: {e}")
        return 2
    return 0


def _cmd_items_set_equip(args: argparse.Namespace) -> int:
    """Set one equip slot of one character (item 'empty'/255 unequips). On a container, dual-writes the MAIN
    block + the Memoria extra mirror (so a vanilla no-extra save is editable too); on an extra-save directly,
    writes that. Dry-run unless --apply."""
    from . import save_items as SI
    try:
        if SI.load_extra_common(args.save)[0] is not None:             # a Memoria extra-save directly
            rep = SI.set_equip(args.save, args.character, args.equip_slot, args.item,
                               dry_run=not args.apply, backup=not args.no_backup)
            print(SI.render_equip_write(rep))
        else:                                                          # a SavedData_ww.dat container + slot
            block = SI._resolve_block(slot=args.slot, save=args.save_no, autosave=args.autosave)
            res = SI.set_equip_in_save(args.save, block, args.character, args.equip_slot, args.item,
                                       dry_run=not args.apply, backup=not args.no_backup)
            print(SI.render_equip_dual(res))
    except Exception as e:                                              # noqa: BLE001
        print(f"could not set equipment: {e}")
        return 2
    return 0


def _cmd_items_set_keyitem(args: argparse.Namespace) -> int:
    """Give / remove a KEY (important) item by name. On a container, dual-writes the MAIN block's rareItems +
    the Memoria extra's rareItemsEx (so a vanilla no-extra save is editable too); on an extra-save directly,
    writes that. Default gives it (obtained); --remove removes it, --used marks it used. Dry-run unless --apply."""
    from . import save_items as SI
    try:
        obtained = not args.remove and not args.not_obtained
        used = args.used and not args.remove
        if SI.load_extra_common(args.save)[0] is not None:             # a Memoria extra-save directly
            rep = SI.set_keyitem_extra(args.save, args.keyitem, obtained=obtained, used=used,
                                       dry_run=not args.apply, backup=not args.no_backup)
            print(SI.render_keyitem_write(rep))
        else:                                                          # a SavedData_ww.dat container + slot
            block = SI._resolve_block(slot=args.slot, save=args.save_no, autosave=args.autosave)
            res = SI.set_keyitem_in_save(args.save, block, args.keyitem, obtained=obtained, used=used,
                                         dry_run=not args.apply, backup=not args.no_backup)
            print(SI.render_keyitem_dual(res))
    except Exception as e:                                              # noqa: BLE001
        print(f"could not set key item: {e}")
        return 2
    return 0


def _cmd_items_set_stat(args: argparse.Namespace) -> int:
    """Set a character's permanent growth stat (Speed/Strength/Magic/Spirit) to a target value -- writes both the
    displayed `basis` and the hidden equipment `bonus` accumulator so the change shows immediately AND holds
    through level-ups. On a container, dual-writes the MAIN block + the Memoria extra mirror (vanilla saves
    editable too); on an extra-save directly, writes that. Dry-run unless --apply."""
    from . import save_items as SI
    try:
        if SI.load_extra_common(args.save)[0] is not None:             # a Memoria extra-save directly
            rep = SI.set_stat_extra(args.save, args.character, args.stat, args.value,
                                    dry_run=not args.apply, backup=not args.no_backup)
            print(SI.render_stat_write(rep))
        else:                                                          # a SavedData_ww.dat container + slot
            block = SI._resolve_block(slot=args.slot, save=args.save_no, autosave=args.autosave)
            res = SI.set_stat_in_save(args.save, block, args.character, args.stat, args.value,
                                      dry_run=not args.apply, backup=not args.no_backup)
            print(SI.render_stat_dual(res))
    except Exception as e:                                              # noqa: BLE001
        print(f"could not set stat: {e}")
        return 2
    return 0


def _cmd_items_set_ap(args: argparse.Namespace) -> int:
    """Set the AP of a character's ability (so it's mastered / usable). `ability` is a name, an AA:X / SA:X token,
    a numeric abil_id, or 'all'; `value` is master / max / forget / a number. On a container, dual-writes the MAIN
    block's pa array + the Memoria extra's pa_extended (so a vanilla no-extra save is editable too); on an
    extra-save directly, writes that. The editor changes abilities ALREADY in the pool. Dry-run unless --apply."""
    from . import save_items as SI
    try:
        if SI.load_extra_common(args.save)[0] is not None:             # a Memoria extra-save directly
            rep = SI.set_ap_extra(args.save, args.character, args.ability, args.value,
                                  dry_run=not args.apply, backup=not args.no_backup)
            print(SI.render_ability_write(rep))
        else:                                                          # a SavedData_ww.dat container + slot
            block = SI._resolve_block(slot=args.slot, save=args.save_no, autosave=args.autosave)
            res = SI.set_ap_in_save(args.save, block, args.character, args.ability, args.value,
                                    dry_run=not args.apply, backup=not args.no_backup)
            print(SI.render_ability_dual(res))
    except Exception as e:                                              # noqa: BLE001
        print(f"could not set AP: {e}")
        return 2
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
            print(f"  block {s.block:<3} [{who:14}]  ScenarioCounter {s.scenario:<6} {s.beat:<20} mognet locks {s.mognet_locks}")
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
    def _worldpos(spec):
        """Parse --world-pos 'X,Z' into (x, z) floats; either may be blank to leave that axis alone."""
        if not spec:
            return None, None
        parts = [p.strip() for p in spec.split(",")]
        if len(parts) != 2:
            raise ValueError("--world-pos must be 'X,Z' (two comma-separated numbers; leave one blank to keep it)")
        return (float(parts[0]) if parts[0] else None, float(parts[1]) if parts[1] else None)

    try:
        scenario = F.resolve_scenario(args.scenario) if args.scenario else None
        set_bits, clear_bits = _bits(args.set_flags), _bits(args.clear_flags)
        wx, wz = _worldpos(getattr(args, "world_pos", None))
        wactor = getattr(args, "world_actor", "player") or "player"
        # Memoria's per-slot extra file holds the AUTHORITATIVE gEventGlobal (it overrides the vanilla main
        # block on load), so read from it when present; fall back to the main block for a vanilla-only save.
        src = S.read_extra_gEventGlobal(extra) if extra_exists else None
        if src is None:
            src = sv.gEventGlobal(n)
        geg = bytearray(src)
        if wx is not None or wz is not None:               # show the current spot so the user has a reference
            print(f"current {wactor} overworld position: "
                  f"{tuple(round(v, 1) for v in S.decode_world_position(geg, wactor))} (X, Z; Y ground-snapped)")
        notes = S.edit_story_state(geg, scenario=scenario, set_flags=set_bits, clear_flags=clear_bits)
        notes += S.edit_world_position(geg, wx, wz, actor=wactor)
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
        bak = S._unique_backup_path(f"{path}.bak.{time.strftime('%Y%m%d-%H%M%S')}")
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
        # a crafted/stale toml_rel must not read outside the set (lexical screen first -- _rel_is_clean)
        if not (campaign._rel_is_clean(m.toml_rel) or campaign._within(base, p)):
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


def _cmd_fork_report(args: argparse.Namespace) -> int:
    """Preview, OFFLINE, what a fork of a real field will and won't reproduce (roster / interaction
    fidelity, story gating, a suggested [startup] beat) -- the 'before you fork, is it faithful?' verb."""
    _safe_console()
    from . import forkreport as FR
    try:
        fid = FR.resolve_field_id(args.field, game=args.game)
        if getattr(args, "explain", False):
            print(FR.format_explain(FR.explain(fid, game=args.game)))
            return 0
        rep = FR.analyze(fid, game=args.game)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    print(FR.format_report(rep))
    return 0


def _cmd_logic_map(args: argparse.Namespace) -> int:
    """Build a read-only LOGIC MAP of a real field's whole ``.eb`` -- every entry/routine, the resolved call
    graph (RunScript edges), and the dialogue/item/flag side-effects each routine performs. The legible,
    inspectable VIEW of a verbatim fork (whose declarative blocks are empty by design)."""
    _safe_console()
    from . import forkreport as FR
    from . import logic_map as LM
    try:
        fid = FR.resolve_field_id(args.field, game=args.game)
        lm = LM.logic_map(fid, game=args.game)
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    if getattr(args, "json", False):
        import json
        print(json.dumps(LM.to_dict(lm), indent=2))
    else:
        print(LM.format_logic_map(lm))
    return 0


def _cmd_chocobo_export(args: argparse.Namespace) -> int:
    """Export a Chocobo Hot & Cold forest's dig PRIZE POOL + TIMER as an editable ``[chocobo]`` block --
    paste it into the verbatim fork's field.toml, edit values, build/deploy. Applying an unedited export
    is byte-identical. Source: a real field (2950/2951/2952 or an FBG selector) or a verbatim project's
    field.toml (scanned through the build's own compose, so slot coordinates match the build exactly)."""
    _safe_console()
    from .content import chocobo as CH
    src = str(args.source)
    note = ""
    try:
        if src.lower().endswith(".toml"):
            from .build import FieldProject, compose_verbatim_eb
            project = FieldProject.load(src)
            data, _suffix = compose_verbatim_eb(project)
            if data is None:
                print("that field.toml has no [verbatim_eb] block with a valid `bin` -- [chocobo] only "
                      "applies to a verbatim forest fork", file=sys.stderr)
                return 2
            note = f" ({project.name})"
        else:
            from . import forkreport as FR
            from .extract import EventBundle
            fid = FR.resolve_field_id(src, game=args.game)
            data = EventBundle(args.game).eb_for_id(fid)
            note = f" (field {fid})"
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    sc = CH.scan(data)
    if sc is None:
        print(f"no dig-prize pool found in{note or ' this field'} -- Chocobo Hot & Cold lives in fields "
              "2950 (Forest) / 2951 (Lagoon) / 2952 (Air Garden)", file=sys.stderr)
        return 2
    print(CH.export_toml(sc, field_note=note))
    return 0


def _cmd_lint_eb(args: argparse.Namespace) -> int:
    """Structurally lint a field's ``.eb`` (decode / jump bounds / switch bounds / reachable terminator /
    dangling RunScript) -- the offline soundness check for a verbatim fork or an in-place edit. Accepts a
    real field id/name OR a path to a ``.eb`` / verbatim ``.bin``. Exit 1 if any ERROR is found."""
    _safe_console()
    from . import eblint
    import os
    target = args.field
    try:
        if os.path.isfile(target):
            data = open(target, "rb").read()
            label = os.path.basename(target)
        else:
            from . import forkreport as FR
            from .extract import EventBundle
            fid = FR.resolve_field_id(target, game=args.game)
            data = EventBundle(args.game).eb_for_id(fid)
            label = f"field {fid}"
    except (RuntimeError, FileNotFoundError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2
    if not data:
        print(f"no .eb bytes for {target} (not present in this install)", file=sys.stderr)
        return 2
    issues = eblint.lint_eb(data)
    errs = eblint.errors(issues)
    for i in issues:
        print(str(i))
    print(f"\n{label}: {len(errs)} error(s), {len(issues) - len(errs)} warning(s)")
    return 1 if errs else 0


def _cmd_find_rooms(args: argparse.Namespace) -> int:
    """Sweep all fields for the best swap/demo TEST ROOMS (single-PC + swap-clean + a close 3/4 camera).
    The 'where can I cleanly walk as a swapped character / see the model's detail?' verb -- a ~45s offline
    sweep (a cheap .eb prefilter, then a camera read on the survivors)."""
    _safe_console()
    from . import forkreport as FR
    print(f"Sweeping fields for swap/demo rooms (this takes ~45s)...", file=sys.stderr)
    try:
        sweep = FR.find_rooms(game=args.game, limit=args.limit, max_fov=args.max_fov)
    except (RuntimeError, FileNotFoundError) as e:
        print(str(e), file=sys.stderr)
        return 2
    print(FR.format_room_table(sweep))
    return 0


def _cmd_items(args: argparse.Namespace) -> int:
    """List FF9 item names + ids (use a name for `give_item = ["<name>", count]`). With --abilities, list each
    character's learnable abilities (name / AA:X-SA:X token / AP-to-master) for `items-set-ap` instead."""
    if getattr(args, "abilities", False):
        from . import abilities as AB
        if not AB.available():
            print("ability names need your FF9 install (set FF9_GAME_PATH or run from the game dir). You can "
                  "still edit AP by AA:X / SA:X token or numeric id without it.")
            return 0
        want = args.filter.lower() if args.filter else None
        for mt, pname in AB.PRESET_NAMES.items():
            pool = [a for a in AB.pool_for_preset(mt) if a.abil_id != 0]
            if not pool:
                continue
            shown = [a for a in pool if not want or want in (a.name or "").lower() or want in a.token.lower()]
            if not shown:
                continue
            print(f"\n{pname} (preset {mt}):")
            for a in shown:
                print(f"  {a.token:<10} {a.ap_req:>4} AP  {a.name or '(unnamed)'}")
        print("\n  Edit with:  items-set-ap <save> <character> <name|AA:X|SA:X|id|all> <master|max|forget|N>")
        return 0
    from . import items as I
    from . import itemstats as S
    rows = [(i, n) for i, n in I.all_items() if n != "NoItem"]
    if args.filter:
        f = args.filter.lower()
        rows = [(i, n) for i, n in rows if f in n.lower()]
    print(f'{len(rows)} item(s). In an [[event]]/[[choice]] write  give_item = ["<name>", count]  '
          f"(or a numeric id).\n")
    live = S.available()
    for i, n in rows:
        s = S.summary(i) if live else None
        print(f"  {i:>3}  {n:<16}{'  ' + s if s else ''}")
    if not live:
        print("\n  (stat detail -- weapon power, armor defence, effects -- needs your FF9 install; "
              "set FF9_GAME_PATH or run from the game dir.)")
    return 0


def _print_model_detail(m) -> int:
    """One model + its animation gestures (the (group, token) join)."""
    from . import catalog as C
    formk = C.FORM_KIND.get(m.form[:1], "?")
    print(f"model {m.id}: {m.name}")
    print(f"  group {m.group} ({m.kind})  |  form {m.form} ({formk})  |  token {m.token}")
    if m.form[:1] == "W":                                        # a world-form model = an overworld actor
        who = C.world_character(m.id) or C.world_role(m.id)      # authoritative name if the engine names it
        print(f"  OVERWORLD actor{' -- ' + who if who else ''} -- reskin + .anim edits are DLL-free "
              f"(same as a field); see it on the world map. `model-gltf {m.name}` to edit.")
    ap = m.appearance
    if ap.story_evolved:
        others = [f for f in ap.forms if f != m.name]
        print(f"  story-evolved: {len(ap.forms)} field forms -- {', '.join(ap.forms)}")
        print(f"    the game loads a different form per story beat; editing THIS id leaves the others stock"
              + (f" (override each: {', '.join(others)})." if others else "."))
    if ap.scenario_gated:
        what = {"hair-swap": "the engine hides long_hair/short_hair by ScenarioCounter (name-keyed)",
                "texture-reassign": "the engine rebuilds this form's textures per story beat (name-keyed)",
                }.get(ap.gate_kind, ap.gate_kind)
        print(f"  scenario-gated look: {what}.")
        print("    an OVERRIDE (re-import at this id) preserves it; a MINT (new id) bypasses it "
              "(see `model-import`/`model-mint` for the fix).")
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
        marks = (["gated"] if m.appearance.scenario_gated else []) + \
                (["evolved"] if m.appearance.story_evolved else [])
        ap = f"   ({'/'.join(marks)})" if marks else ""
        print(f"  {m.id:>4}  {m.name:<22} {tag:<16}{extra}{ap}".rstrip())
    print(f"\nName one to see its gestures + appearance:  ff9mapkit models {rows[0].name}")
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


def _cmd_sps(args: argparse.Namespace) -> int:
    """List / decode / preview a field's SPS particle effects (fire/smoke/magic). Install-gated (UnityPy)."""
    if getattr(args, "templates", False):
        from .sps import templates as T
        print("Tier-2 [[sps]] effect templates (use as: template = \"<name>\"):\n")
        for name, desc, field, sid in T.list_templates():
            print(f"  {name:<10} {desc:<34} (clones {field} #{sid})")
        return 0
    if not args.field:
        print("give a field token (or --templates). e.g. `ff9mapkit sps 303`", file=sys.stderr)
        return 2
    from .sps import catalog as SC
    rows = SC.list_field_sps(args.field)
    if not rows:
        print(f"no SPS effects for field {args.field!r} (needs the FF9 install + UnityPy, and a field that "
              "carries .sps effects). `ff9mapkit list-fields` lists field tokens.", file=sys.stderr)
        return 0
    if args.id is None and not args.png and not args.gif:
        print(f"{len(rows)} SPS effect(s) in {rows[0].folder}. Each <id> is a RunSPSCode effect:\n")
        for e in rows:
            print(f"  {e.sps_id:>5}  {e.sps_id}.sps")
        print(f"\nDecode one:  ff9mapkit sps {args.field} --id {rows[0].sps_id}"
              f"\nPreview:     ff9mapkit sps {args.field} --id {rows[0].sps_id} --png out.png")
        return 0
    target = args.id if args.id is not None else rows[0].sps_id
    entry = next((e for e in rows if e.sps_id == target), None)
    if entry is None:
        print(f"field {args.field} has no SPS effect {target} (have: {[e.sps_id for e in rows]})", file=sys.stderr)
        return 2
    sps = SC.load_sps(entry)
    print(f"SPS effect {target} in {entry.folder}:")
    for label, value in SC.effect_facts(sps):
        print(f"  {label:<16} {value}")
    if args.png or args.gif:
        tcb = SC.load_tcb(args.field)
        if tcb is None:
            print("  (no spt.tcb for this field -- cannot render a textured preview)", file=sys.stderr)
            return 2
        from .sps import render
        if args.png:
            render.save_png(render.render_strip(sps, tcb, scale=args.scale), args.png)
            print(f"  wrote {args.png} (a {sps.frame_count}-frame contact sheet)")
        if args.gif:
            render.save_gif(sps, tcb, args.gif, scale=args.scale)
            print(f"  wrote {args.gif} (~15 fps loop)")
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

    co = sub.add_parser("coop", help="two-player co-op ghost sync: set up + run a session in one command "
                                     "(needs the Dream World IX custom engine, s36)")
    co.add_argument("action", choices=["host", "join", "show", "off", "bridge"],
                    help="host = start a session (prints/copies your code) | join = join a friend's | "
                         "show = print the current co-op config | "
                         "off = disable co-op in Memoria.ini | bridge = run just the ws->wss bridge")
    co.add_argument("code", nargs="?", default=None,
                    help="the session code (join: REQUIRED, the host's ff9-XXXXXXXX; host: optional override)")
    co.add_argument("--port", type=int, default=49201, help="local bridge port (default 49201)")
    co.add_argument("--relay", default=None, help="relay URL override, ws:// or wss:// (default: built in)")
    co.add_argument("--lan", nargs="?", const="", default=None, metavar="HOST_IP",
                    help="direct-LAN mode instead of the relay (no bridge): host uses bare --lan, "
                         "join needs the host's IP, e.g. --lan 192.168.1.50")
    co.add_argument("--field", type=int, default=None,
                    help="restrict co-op to ONE field id (default: everywhere -- any screen both players share)")
    co.add_argument("--guest-slots", default=None, metavar="SLOTS",
                    help="battle co-op: which of YOUR party slots the other player commands -- "
                         "party positions 1-4 as the menu shows them ('2', '2,3', 'all', 'none'). "
                         "Only written when given; needs the s37 engine")
    co.add_argument("--guest-wait", type=int, default=None, metavar="SECONDS",
                    help="cap how long a guest's battle turn may freeze the ATB gauges "
                         "(seconds; 0 = no cap; engine default 30). Only written when given")
    co.add_argument("--ghost-as", default=None, metavar="WHO",
                    help="visitor mode: dress the other player's ghost -- 'auto' (the party member "
                         "they command in battle), a playable name (vivi, dagger, ...), or 'off' "
                         "(their own model). Only written when given")
    co.add_argument("--follow-host", choices=["on", "off"], default=None,
                    help="guest side: 'on' auto-warps your game to whatever field the host is on, "
                         "pauses your own random encounters while paired, and boots the host's "
                         "battles live on your screen (render-only). Only written when given")
    co.add_argument("--no-bridge", action="store_true", help="write the config but don't run the bridge")
    co.add_argument("--no-room", action="store_true", help="skip the co-op room check/build")
    co.add_argument("--rebuild-room", action="store_true", help="rebuild the FF9Coop room even if a room "
                                                                "is already registered")
    co.add_argument("--new-code", action="store_true", help="host: mint a fresh session code instead of "
                                                            "reusing the saved one")
    co.add_argument("--insecure", action="store_true", help="skip TLS certificate verification (self-signed relays)")
    co.set_defaults(func=_cmd_coop)

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
    gd.add_argument("--template-layers", action="store_true",
                    help="with --template: write SEPARATE per-layer PNGs (grid / outline / height) + a "
                         "<name>.manifest.json instead of one combined PNG, so you can toggle each "
                         "guide in your paint app")
    gd.set_defaults(func=_cmd_guide)

    bd = sub.add_parser("build", help="compile field.toml project(s) into a Memoria mod")
    bd.add_argument("field", nargs="+", help="one or more field.toml files")
    bd.add_argument("--out", default="dist", help="output mod folder (default: ./dist)")
    bd.add_argument("--mod-name", default="FF9CustomMap", help="mod name / InstallationPath")
    bd.add_argument("--author", default="", help="mod author")
    bd.add_argument("--description", default="", help="mod description")
    bd.add_argument("--preserve-existing", action="store_true",
                    help="keep registrations already in --out that this build does not emit -- for "
                         "INSTALLING into a shipping mod folder that holds other fields (without it, a "
                         "build that would unregister them refuses)")
    bd.set_defaults(func=_cmd_build)

    bh = sub.add_parser("behavior", help="the [behavior] tree surface: dry-compile + report, lint with "
                                         "route sweeps, or view the generated bytecode")
    bh.add_argument("action", choices=["compile", "lint", "view"],
                    help="compile = report (blackboard/actions/public flags); lint = static checks + "
                         "walkability sweeps of referenced route markers; view = compile + disassemble "
                         "every generated body")
    bh.add_argument("field", help="path to the field.toml")
    bh.set_defaults(func=_cmd_behavior)

    ln = sub.add_parser("lint", help="check a field.toml without building -- one pass over every offline "
                        "validator (schema, story/flag logic, reserved flag bands, walkmesh geometry + "
                        "content placement, layer art, camera pitch)")
    ln.add_argument("field", help="path to a .field.toml")
    ln.set_defaults(func=_cmd_lint)

    pt = sub.add_parser("paint-template", help="project a field.toml's floor + content onto per-layer "
                        "trace-over PNGs + a legend (camera-aware; covers every content type)")
    pt.add_argument("field", help="path to a .field.toml")
    pt.add_argument("--out", default=None, help="output dir (default: the field.toml's dir)")
    pt.add_argument("--basename", default="paint_template", help="output filename stem (default paint_template)")
    pt.set_defaults(func=_cmd_paint_template)

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
    pk.add_argument("--name", default=None,
                    help="the mod-folder name INSIDE the zip (what Memoria.ini FolderNames will call it; "
                         "default = the folder's own name — use this when packing a staged dist/)")
    pk.set_defaults(func=_cmd_pack)

    gh = sub.add_parser("gen-hub", help="generate a World-Hub field.toml from a journeys.toml registry "
                        "(a journey selector: pick a journey -> warp into it) (P6)")
    gh.add_argument("journeys", help="path to a journeys.toml ([hub] + [[journey]] rows)")
    gh.add_argument("--out", default=None,
                    help="output field.toml (default: hub.field.toml beside the journeys.toml)")
    gh.add_argument("--extract-camera", dest="extract_camera", action="store_true",
                    help="pull the borrowed room's camera ([hub] borrow_field) into the workspace cache and "
                         "wire the emitted toml to it (needs the install + UnityPy)")
    gh.add_argument("--force", action="store_true", help="re-extract the camera even if already cached")
    gh.set_defaults(func=_cmd_gen_hub)

    lj = sub.add_parser("lint-journey", help="validate a multi-campaign journeys.toml offline (id/flag "
                        "disjointness, links resolve, entries valid) -- the assembler's namespace guarantee")
    lj.add_argument("journeys", help="path to a journeys.toml ([hub] + [[journey]] rows, bare or multi-campaign)")
    lj.add_argument("--graph", action="store_true",
                    help="also print the resolved namespace (entry ids, campaign id bands, flag windows, links)")
    lj.set_defaults(func=_cmd_lint_journey)

    aj = sub.add_parser("assemble-journey", help="assemble a multi-campaign journeys.toml: lint + emit the "
                        "World-Hub field.toml (resolves BOTH bare and multi-campaign journeys)")
    aj.add_argument("journeys", help="path to a journeys.toml ([hub] + [[journey]] rows)")
    aj.add_argument("--out", default=None,
                    help="output hub field.toml (default: hub.field.toml beside the journeys.toml)")
    aj.add_argument("--graph", action="store_true", help="print the resolved namespace before emitting")
    aj.add_argument("--dry-run", dest="dry_run", action="store_true",
                    help="lint + print the resolved plan, but DON'T write the hub field.toml")
    aj.add_argument("--extract-camera", dest="extract_camera", action="store_true",
                    help="pull the hub's [hub] borrow_field camera into the workspace cache + wire the emitted "
                         "[camera] borrow to it (needs the install + UnityPy)")
    aj.add_argument("--force", action="store_true", help="re-extract the camera even if already cached")
    aj.set_defaults(func=_cmd_assemble_journey)

    ra = sub.add_parser("reference-arcs", help="FF9 reference-arc scaffold: list the curated arc->seed table, "
                        "print the fork playbook, or emit a chained journeys.toml (the north-star harness)")
    ra.add_argument("--table", default=None,
                    help="a custom reference-arc table (default: the packaged FF9 disc-1 spine)")
    ra.add_argument("--emit", default=None, metavar="DIR",
                    help="WRITE a journeys.toml scaffold (the arcs as a chained journey + the fork playbook) into DIR")
    ra.add_argument("--playbook", action="store_true", help="print ONLY the import-chain fork commands")
    ra.add_argument("--reconcile", default=None, metavar="JOURNEYS_TOML",
                    help="STEP 2: fill an emitted journeys.toml's ENTRY placeholder from the campaigns forked "
                         "beside it + clear the obsolete link templates (cross-campaign warps auto-wire at "
                         "deploy). Run after forking; writes in place. Ignores --table.")
    ra.add_argument("--regen", action="store_true",
                    help="REGENERATE the region PICKER's catalog (every forkable zone -> its entry seed) from the "
                         "game's real field->zone data, into the shipped data/region_catalog.toml")
    ra.add_argument("--out", default=None, help="with --regen: write the catalog here (default: the shipped data file)")
    ra.add_argument("--pattern", default=None,
                    help="with --regen: only zones whose token/area matches (e.g. 'dali', 'alex')")
    ra.add_argument("--no-split-visits", action="store_true", dest="no_split_visits",
                    help="with --regen: one region per WHOLE zone (the old behavior) instead of one per "
                         "story-state visit -- a region then forks every revisit screen (--whole-zone)")
    ra.add_argument("--gap", type=int, default=None,
                    help="with --regen: the field-id gap that separates story-state visits (default 120; "
                         "smaller = split more finely, larger = merge nearby visits)")
    ra.add_argument("--force", action="store_true", help="with --emit, overwrite an existing journeys.toml")
    ra.add_argument("--hub-name", default="FF9 Disc 1", dest="hub_name", help="hub field display name (--emit)")
    ra.add_argument("--hub-id", type=int, default=4600, dest="hub_id", help="hub field id, >=4000 (--emit)")
    ra.add_argument("--borrow-bg", default=None, dest="borrow_bg",
                    help="hub art borrow field (--emit; default: Mognet Central, FF9's journey nexus)")
    ra.add_argument("--id-base", type=int, default=6000, dest="id_base",
                    help="first arc's campaign id base; arc i gets id_base + i*100 (default 6000)")
    ra.set_defaults(func=_cmd_reference_arcs)

    ef = sub.add_parser("extract-field", help="cache a real field's camera+walkmesh in the gitignored "
                        "workspace cache (reused by BG-borrow tomls / gen-hub --extract-camera)")
    ef.add_argument("ids", nargs="+", help="real field id(s) to cache (e.g. 950)")
    ef.add_argument("--force", action="store_true", help="re-extract even if already cached")
    ef.set_defaults(func=_cmd_extract_field)

    ea = sub.add_parser("export-art", help="assemble a field's per-overlay background PNGs OFFLINE -- our own "
                        "[Export] Field=1 (no in-game hang); needs UnityPy")
    ea.add_argument("target", nargs="?", default=None,
                    help="a field (FBG / mapid / unique substring), OR a campaign.toml (export every member's "
                         "donor field). Omit with --all.")
    ea.add_argument("--all", action="store_true",
                    help="export EVERY real field (the full drop-in for the in-game startup dump)")
    ea.add_argument("--pattern", default=None,
                    help="with --all: only fields whose FBG folder contains this substring (e.g. a zone: dali, iccv)")
    ea.add_argument("--composite", action="store_true",
                    help="write ONE composited background PNG per field (clean opaque art, no walkmesh "
                         "footprint) into a FLAT folder -- a browsable whole-game gallery to scroll through "
                         "while planning journeys, instead of the raw per-overlay layers")
    ea.add_argument("--out", default=None,
                    help="output root (default: <install>/StreamingAssets/FieldMaps, the engine's own "
                         "location -- a true drop-in). Raw: each field -> <out>/<FBG>/Overlay{i}.png; "
                         "--composite: each field -> <out>/<FBG>.png. For a gallery use --out reference/all-fields-export.")
    ea.add_argument("--no-atlas", action="store_true", help="(raw mode) don't also dump the source atlas.png")
    ea.set_defaults(func=_cmd_export_art)

    rp = sub.add_parser("repaint-native", help="repaint a native fork's background: unpack its tile-packed "
                        "atlas into spatial layers, then --pack the edited layers back (seamless HD, no game)")
    rp.add_argument("project", help="a native fork project dir (has scene.bgs.bytes + atlas.png + a *.field.toml)")
    rp.add_argument("--pack", action="store_true",
                    help="blit the (edited) repaint/Overlay*.png layers BACK into atlas.png (else: unpack them)")
    rp.add_argument("--out", default=None,
                    help="(unpack) where to write the spatial layers + manifest (default: <project>/repaint/)")
    rp.add_argument("--from", dest="from_dir", default=None,
                    help="(--pack) the repaint dir holding the edited layers (default: <project>/repaint/)")
    rp.add_argument("--no-backup", action="store_true", help="(--pack) don't back up the current atlas.png first")
    rp.set_defaults(func=_cmd_repaint_native)

    iaa = sub.add_parser("import-all", help="bulk-import a foldered, Blender-ready archive of fields -- whole "
                         "game / a zone / a campaign (lightweight by default; needs UnityPy)")
    iaa.add_argument("target", nargs="?", default=None,
                     help="a campaign.toml (fold its members under <out>/<CAMPAIGN>/<MEMBER>/). Omit and use "
                          "--all / --pattern for the whole game.")
    iaa.add_argument("--all", action="store_true", help="import every real field")
    iaa.add_argument("--pattern", default=None,
                     help="only fields whose FBG folder contains this substring (a zone, e.g. iccv / dali / trno)")
    iaa.add_argument("--out", required=True,
                     help="archive root. Whole game -> <out>/<ZONE>/<FBG>/; campaign -> <out>/<CAMPAIGN>/<MEMBER>/. "
                          "Use a GITIGNORED path -- this is SE-derived art (e.g. reference/all-fields-import).")
    iaa.add_argument("--editable", action="store_true",
                     help="full editable custom scene per field (repaintable per-depth layers, reshapeable) "
                          "instead of the lightweight model-against project -- bigger + slower, for art-modding "
                          "a whole set at once. Default = lightweight; promote single fields with `import --editable`.")
    iaa.set_defaults(func=_cmd_import_all)

    im = sub.add_parser("import", help="fork a REAL FF9 field into an editable field.toml (needs UnityPy)")
    im.add_argument("field", help="field name: full FBG, bare mapid, or a unique substring (e.g. grgr_map420)")
    im.add_argument("--out", default=".", help="project dir to write into (default: .)")
    im.add_argument("--name", default=None, help="custom field/script id (default: <MAPID-first-token>_FORK/_EDIT)")
    im.add_argument("--id", type=int, default=4003, help="custom field id (default: 4003)")
    im.add_argument("--editable", action="store_true",
                    help="fork as a full editable CUSTOM SCENE (re-exported walkmesh + the real art split "
                         "into one repaintable layer per depth, occlusion preserved) instead of BG-borrow; "
                         "art is assembled OFFLINE from the atlas now -- no in-game [Export] step needed")
    im.add_argument("--native", action="store_true",
                    help="fork as a NATIVE custom scene: ship the real atlas.png + .bgs (per-tile depth) + "
                         "custom walkmesh, NO .bgx -- renders via the engine's seamless native path (no tile "
                         "seams, faithful occlusion), exactly how Moguri ships. Also forks area<10 fields that "
                         "BG-borrow can't. Needs no in-game export.")
    im.add_argument("--verbatim", action="store_true",
                    help="MOST FAITHFUL: fork over a native scene AND ship the field's REAL event script WHOLE "
                         "(entry-0 + every object + every gateway, layout intact) instead of re-synthesizing -- "
                         "the field runs its own logic (story gating, rotating cast, real doors). Implies "
                         "--native; pair with a [startup] block to boot a chosen beat. (docs/FORK_FIDELITY.md)")
    im.add_argument("--swap-player", metavar="WHO", default=None,
                    help="SWAP who you WALK as to a playable (zidane/vivi/steiner/garnet/freya/quina/eiko/"
                         "amarant; aliases dagger, salamander) OR ANY model -- a GEO name or numeric id (a "
                         "moogle 199, GEO_NPC_F0_BMG, ...; `ff9mapkit models`). Patches the player entry's "
                         "SetModel + movement anims to that rig. Implies --verbatim (needs the donor player "
                         "entry); party/menu state is unchanged. CLEAN on free-roam fields; on a cutscene-heavy "
                         "field the player's scripted GESTURES glitch (warned) -- only movement clips are swapped. "
                         "(memory project-ff9-pc-party-system)")
    im.add_argument("--neutralize-gestures", action="store_true",
                    help="with --swap-player: rewrite the player's scripted cutscene GESTURES to the new rig's "
                         "idle so it STANDS cleanly instead of glitching (the character won't emote -- for story "
                         "fidelity use a verbatim fork at the right beat instead). Requires --swap-player.")
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
    ic.add_argument("seed", help="seed field id (e.g. 300) OR an FBG substring (e.g. iccv = seed every Ice "
                                 "Cavern screen). COMMA-SEPARATED for several (e.g. 50,100 or tshp,alxt) -> "
                                 "with --whole-zone forks multiple zones as ONE campaign (cross-zone warps "
                                 "auto-retarget in-fork); the first token stays the entry.")
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
    ic.add_argument("--whole-zone", action="store_true", dest="whole_zone",
                    help="fork EVERY forkable field in the seed's zone(s), not just those door-reachable from the "
                         "seed -- captures cutscene-only / non-door-connected screens the walk misses (the seed "
                         "stays the entry). Raises --max-fields to fit the zone. Same as seeding an FBG substring.")
    ic.add_argument("--ids", default=None, dest="ids",
                    help="fork EXACTLY this set of field ids (a compact range string, e.g. 100-117 or "
                         "100-117,150-167) instead of a whole zone -- scopes the fork to ONE story-state cluster "
                         "(e.g. Alexandria's disc-1 opening, not all 48 revisit screens). The seed stays the "
                         "entry; raises --max-fields to fit. Mutually exclusive with --whole-zone.")
    ic.add_argument("--dry-run", action="store_true", dest="dry_run",
                    help="just print the discovered graph (the default when --out is omitted)")
    # P2 write mode: --out flips import-chain from the read-only dry-run to forking the chain.
    ic.add_argument("--out", default=None,
                    help="WRITE the chain: emit campaign.toml + per-member field.tomls into this dir (P2)")
    ic.add_argument("--id-base", type=int, default=None, dest="id_base",
                    help="member i gets id_base+i (default: .ff9deploy.toml campaign_id_base, else 6000; >=4000)")
    ic.add_argument("--fresh-ids", action="store_true", dest="fresh_ids",
                    help="ignore any existing <out>/campaign.toml and re-allocate every id from id_base (the old "
                         "index-based behavior). A re-fork then SHIFTS ids -> any in-fork SAVE goes stale. Default: "
                         "STABLE ids -- reuse the prior donor->id+name map, append net-new donors above the max, so "
                         "saves survive re-forking into the SAME --out.")
    ic.add_argument("--flag-base", type=int, default=FIRST_SAFE_FLAG, dest="flag_base",
                    help=f"campaign flag band start recorded in campaign.toml (default {FIRST_SAFE_FLAG}, "
                         f"the safe floor clear of real-FF9 chest flags)")
    ic.add_argument("--flags-per-field", type=int, default=64, dest="flags_per_field",
                    help="reserved GLOB block width per field (recorded for P5; default 64)")
    ic.add_argument("--campaign-name", default=None, dest="campaign_name",
                    help="campaign/mod name (default <SEED-ZONE>_CAMPAIGN)")
    ic.add_argument("--name-prefix", default=None, dest="name_prefix",
                    help="prefix every member's deployed FBG/EVT name (e.g. DC -> DC_DL_ENT) so two "
                         "campaigns/worktrees forking the SAME source field don't collide on the by-name, "
                         "highest-folder-wins scene/.eb resolution. Use a short unique tag per campaign.")
    ic.add_argument("--mod-folder", default=None, dest="mod_folder",
                    help="target mod folder in campaign.toml (default: .ff9deploy.toml, else FF9CustomMap-ow)")
    ic.add_argument("--live-seams", action="store_true", dest="live_seams",
                    help="emit out-of-chain gateways as LIVE doors into the real game (default: comment as seams)")
    ic.add_argument("--verbatim", action="store_true",
                    help="MOST FAITHFUL: fork every member NATIVE + VERBATIM (ship each donor's whole .eb + "
                         ".mes, run the real logic; in-chain doors retargeted to sibling forks)")
    ic.add_argument("--swap-player", metavar="WHO", default=None,
                    help="play as one character/model across the WHOLE chain: a playable (zidane/vivi/steiner/"
                         "garnet/freya/quina/eiko/amarant; aliases dagger, salamander) OR any model (a GEO name "
                         "or id, e.g. a moogle 199). Swaps every member's player rig (SetModel + movement anims). "
                         "Implies --verbatim; party/menu unchanged; cutscene-gesture members warned. "
                         "(see import --swap-player)")
    ic.add_argument("--neutralize-gestures", action="store_true",
                    help="with --swap-player: stand cleanly through cutscene gestures across the chain "
                         "(see import --neutralize-gestures). Requires --swap-player.")
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
    lf.add_argument("pattern", nargs="?", default=None,
                    help="filter by FBG/MAPID name OR field id substring (e.g. alex, treno, 2951)")
    lf.add_argument("--players", action="store_true",
                    help="also show WHO you control in each field (reads each .eb; a full sweep is ~30s)")
    lf.add_argument("--non-zidane", action="store_true",
                    help="only fields you play as someone other than Zidane (the verbatim-fork donors; implies --players)")
    lf.set_defaults(func=_cmd_list_fields)

    ff = sub.add_parser("find-field",
                        help="resolve a field id / name / FBG substring -> id + friendly name + archive folder")
    ff.add_argument("query", help="a field id (exact match), or an FBG/EVT/friendly-name substring "
                                  "(e.g. 2934, cysw, \"Cargo Room\")")
    ff.add_argument("--archive", default=None,
                    help="an import-all archive dir to show each match's folder "
                         "(default: reference/all-fields-import if present). Pure lookup needs no install.")
    ff.set_defaults(func=_cmd_find_field)

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

    me = sub.add_parser("model-export",
                        help="export a REAL FF9 field/character model to an editable skinned FBX (needs UnityPy)")
    me.add_argument("model", help="GEO name or model id to export, e.g. GEO_MAIN_F0_VIV or 8 (see `models`)")
    me.add_argument("--out", default=".", help="dir to write the Models/<type>/<id>/ tree into (default: .)")
    me.add_argument("--flat", action="store_true",
                    help="write <id>.fbx + textures directly in --out (for editing) instead of the engine "
                         "Models/<type>/<id>/ override layout")
    me.add_argument("--deploy", metavar="MODFOLDER", default=None,
                    help="export the UNEDITED model straight into MODFOLDER at the engine override path "
                         "(the Phase-1 fidelity test) instead of writing to --out")
    me.add_argument("--game", default=argparse.SUPPRESS, help="path to the FF9 install (default: auto-detect)")
    me.set_defaults(func=_cmd_model_export)

    mm = sub.add_parser("model-mint",
                        help="mint a NEW additive GEO model id (a fresh SetModel target, not an override) -- DLL-free")
    mm.add_argument("source", help="GEO name or id whose geometry to re-export to the new id (e.g. GEO_NPC_F1_BBA)")
    mm.add_argument("--id", type=int, required=True,
                    help="the new GEO id (>= 6000 -- clear of every real id, which top out at 5511)")
    mm.add_argument("--name", default=None,
                    help="the new GEO name GEO_<GROUP>_<FORM>_<TOKEN> (default: auto from source + id; the "
                         "GROUP sets the model type + path). Must NOT be a real FF9 name.")
    mm.add_argument("--deploy", metavar="MODFOLDER", default=None,
                    help="deploy into MODFOLDER: write the FBX AND append the `3DModel` directive to its "
                         "DictionaryPatch.txt (RELAUNCH to register)")
    mm.add_argument("--out", default=".", help="dir to write the Models/<type>/<id>/ tree into (default: .)")
    mm.add_argument("--game", default=argparse.SUPPRESS, help="path to the FF9 install (default: auto-detect)")
    mm.set_defaults(func=_cmd_model_mint)

    mg = sub.add_parser("model-gltf",
                        help="export a REAL FF9 model + its animations to a Blender-openable glTF (.glb) -- the edit loop")
    mg.add_argument("model", help="GEO name or model id to export, e.g. GEO_MAIN_F0_VIV or 8 (see `models`)")
    mg.add_argument("--out", default=None, help="output .glb path (default: <geo>.glb in the current dir)")
    mg.add_argument("--anims", default="auto",
                    help="which clips to embed: 'auto' (idle/walk/run/turns), 'all' (the model's whole folder), "
                         "'none', or a comma/space list of action labels or raw anim ids. A clip that lives in "
                         "a DONOR model's folder (the engine's AnimationDB name redirect -- e.g. most of "
                         "GEO_NPC_F1_BBA's actions live in GEO_NPC_F0_BBA's Animations/112/) is found + "
                         "embedded automatically")
    mg.add_argument("--scale", type=float, default=0.01,
                    help="uniform scale bake (default 0.01: FF9's hundreds-of-units models -> a few Blender metres)")
    mg.add_argument("--plain-bones", action="store_true",
                    help="name bones raw boneNNN instead of the default labeled bone012_R_hand form "
                         "(labels are anatomical guesses derived from the rig family's rest pose -- a "
                         "display layer only; either naming round-trips through model-import/-anim-new)")
    mg.add_argument("--game", default=argparse.SUPPRESS, help="path to the FF9 install (default: auto-detect)")
    mg.set_defaults(func=_cmd_model_gltf)

    mi = sub.add_parser("model-import",
                        help="bring a Blender-edited glTF back into the game as a loose-FBX override (return path)")
    mi.add_argument("gltf", help="the edited .glb/.gltf file (exported from Blender)")
    mi.add_argument("--like", default=None,
                    help="GEO name/id whose rig + textures to KEEP (v1 mesh-splice: take only edited geometry; "
                         "vertex count must match). AUTO-DETECTED from the glTF stamp if we exported it, so you "
                         "usually don't pass this; give it for a foreign glTF or to force a different source.")
    mi.add_argument("--id", type=int, default=None,
                    help="target model id to write (default: the source's id -> a straight override; a mint id "
                         ">=6000 for a new model). Only needed for a full re-rig of an unstamped glTF.")
    mi.add_argument("--deploy", metavar="MODFOLDER", default=None,
                    help="mod folder to write the override into (Models/<type>/<id>/)")
    mi.add_argument("--scale", type=float, default=None,
                    help="the scale the glTF was exported at (default: auto from the glTF stamp, else 0.01)")
    mi.add_argument("--no-anims", action="store_true",
                    help="import the mesh only -- skip writing back any edited animation clips (by default an "
                         "edited .glb round-trips mesh AND changed clips as loose .anim overrides)")
    mi.add_argument("--game", default=argparse.SUPPRESS, help="path to the FF9 install (default: auto-detect)")
    mi.set_defaults(func=_cmd_model_import)

    ma = sub.add_parser("model-anim",
                        help="dump/deploy a model's animation clips as editable loose .anim JSON (DLL-free)")
    ma.add_argument("model", help="GEO name or model id whose clips to dump, e.g. GEO_MAIN_F0_VIV or 8")
    ma.add_argument("--clips", default="all",
                    help="which clips: 'all' (default: every clip in the model's OWN folder) or a comma/space "
                         "list of anim KEYS (see `models <GEO>` / `model-gltf --anims all`). A key living in a "
                         "DONOR model's folder (the engine's AnimationDB redirect) resolves + dumps at its real "
                         "Animations/<folder>/ path")
    ma.add_argument("--out", default=".", help="dir to write the Animations/<geoId>/ tree into (default: .)")
    ma.add_argument("--deploy", metavar="MODFOLDER", default=None,
                    help="write straight into MODFOLDER's StreamingAssets override path instead of --out "
                         "(the loose-override-path proof; ~ -> Reload field to apply)")
    ma.add_argument("--game", default=argparse.SUPPRESS, help="path to the FF9 install (default: auto-detect)")
    ma.set_defaults(func=_cmd_model_anim)

    man = sub.add_parser("model-anim-new",
                         help="author a wholly NEW animation clip for a model (a Blender .glb action, or "
                              "the built-in spin demo) -- registered via 3DModelAnimation, DLL-free")
    man.add_argument("model", help="GEO name or model id the clip animates, e.g. GEO_NPC_F1_BBA (see `models`)")
    man.add_argument("--glb", default=None, help="a .glb carrying the new action (made on this model's rig "
                                                 "via `model-gltf` -> Blender; omit for the spin demo)")
    man.add_argument("--action", default=None, help="the Blender action/animation name inside --glb")
    man.add_argument("--suffix", default="CUSTOM1",
                     help="the clip's ANH name suffix (ANH_<grp>_<form>_<tok>_<SUFFIX>; default CUSTOM1)")
    man.add_argument("--key", type=int, default=None,
                     help="the AnimationDB key to register (default: next free in the 60000-65535 band; "
                          "a FIELD anim id must fit 16 bits, so keys above 65535 are rejected)")
    man.add_argument("--deploy", metavar="MODFOLDER", required=True,
                     help="mod folder to write Animations/<id>/<key>.anim + the DictionaryPatch line into")
    man.add_argument("--game", default=argparse.SUPPRESS, help="path to the FF9 install (default: auto-detect)")
    man.set_defaults(func=_cmd_model_anim_new)

    se = sub.add_parser("summon-export",
                        help="export a stock summon creature's ef###.bytes -> a Blender-openable .glb "
                             "(rig + skin + motion clips). Output LOCAL-ONLY by design")
    se.add_argument("ef", help="a local ef###.bytes summon-creature container (extracted from YOUR install, "
                               "kept under C:/gd/SCRATCH/...), e.g. ef227 (Bahamut) / ef261 (Odin)")
    se.add_argument("--out", default=None,
                    help="output .glb path (default: <DEFAULT_OUT_DIR>/<ef-stem>.glb). REFUSED if inside the "
                         "repo, a mod folder (StreamingAssets), or the FF9 install -- a stock export is "
                         "Square-Enix content and must stay local (there is no --force)")
    se.add_argument("--anims", default="all",
                    help="which motion clips to embed: 'all' (default), 'none', or a comma/space list of clip "
                         "INDICES (0-based, file order)")
    se.add_argument("--rest", choices=["identity", "clip0"], default="identity",
                    help="rest pose: 'identity' (default) or 'clip0' (clip 0 frame 0 -- a recognizable posed "
                         "creature instead of the straight skeleton)")
    se.add_argument("--scale", type=float, default=0.01,
                    help="uniform scale bake (default 0.01: FF9's hundreds-of-units models -> a few metres)")
    se.add_argument("--fps", type=float, default=15.0,
                    help="clip playback rate for Blender preview (default 15; a preview knob, not a measured "
                         "tick -- topology/skeleton are unaffected)")
    se.add_argument("--no-textures", action="store_true",
                    help="skip the texture decode (geometry + rig + clips only). Textures are ON by default: "
                         "the creature's id-4 texture pages + CLUTs are decoded to one RGBA PNG per material "
                         "part and embedded in the .glb. A creature whose texture block is not the "
                         "documented 8bpp layout falls back to untextured on its own, with a warning")
    se.add_argument("--geo", default=None, help="GEO name to stamp (default: SUMMON_<ef-stem>)")
    se.add_argument("--id", type=int, default=0, help="geo id to stamp in the manifest (default 0)")
    se.set_defaults(func=_cmd_summon_export)

    sr = sub.add_parser("summon-rig-ref",
                        help="export ONLY a summon's rig reference -> a .glb skeleton (bone000..bone09N, no "
                             "mesh, no clips) to skin your own mesh onto. Output LOCAL-ONLY by design")
    sr.add_argument("ef", help="a local ef###.bytes summon-creature container (as in summon-export)")
    sr.add_argument("--out", default=None,
                    help="output .glb path (default: <DEFAULT_OUT_DIR>/<ef-stem>_rig.glb). REFUSED inside the "
                         "repo / a mod folder (StreamingAssets) / the FF9 install -- the rig is stock-derived "
                         "and must stay local (there is no --force)")
    sr.add_argument("--rest", choices=["identity", "clip0"], default="identity",
                    help="rest pose the armature is posed in: 'identity' (default) or 'clip0'")
    sr.add_argument("--geo", default=None, help="GEO name to stamp (default: SUMMON_<ef-stem>)")
    sr.add_argument("--id", type=int, default=0, help="geo id to stamp in the manifest (default 0)")
    sr.set_defaults(func=_cmd_summon_rig_ref)

    def _add_summon_lane_args(sp, *, with_model_flag: bool):
        # shared [[summon]] block flags for summon-import / summon-deploy
        sp.add_argument("--donor", type=int, default=227,
                        help="the NUMERIC donor effect id whose live cast we wear (default 227 = Bahamut)")
        sp.add_argument("--lane", choices=list(_summon_lanes()), default="hybrid",
                        help="hybrid (s58 drive, needs the custom engine; DEFAULT) | overlay (DLL-free)")
        if with_model_flag:
            sp.add_argument("--model", default=None, help="the user's retargeted FBX (bone000..092 rig)")
        sp.add_argument("--textures", default=None,
                        help="comma-separated texture PNGs to deploy beside the FBX (default: PNGs beside it)")
        sp.add_argument("--id", type=int, default=None, help="mint GEO id (default: next free >=6000)")
        sp.add_argument("--name", default=None,
                        help="mint GEO name GEO_<GRP>_<FORM>_<TOK> (default: derived from id + group)")
        sp.add_argument("--group", default=None, help="silhouette family token (MON/MAIN/SUB...; default MON)")
        sp.add_argument("--private-ef", dest="private_ef", type=int, default=None,
                        help="the stock-ABSENT effect id hosting the cast .seq (default: auto-alloc; bench 84)")
        sp.add_argument("--node-count", dest="node_count", type=int, default=None,
                        help="[SfxHybrid] NodeCount = donor bone count (default 93)")
        sp.add_argument("--hide-mask", dest="hide_mask", default=None,
                        help="[SfxHybrid] HideMask (default 0x3 = Bahamut's 2 meshes)")
        sp.add_argument("--hide-meshes", dest="hide_meshes", default=None,
                        help="comma-separated mesh KEYS spliced as HideMeshes= on the host .seq (0x optional)")
        sp.add_argument("--from-toml", dest="from_toml", default=None,
                        help="read the first [[summon]] block from this TOML file instead of the flags")
        sp.add_argument("--mod-folder", dest="mod_folder", default="FF9CustomMap",
                        help="mod folder name inside the install (default FF9CustomMap)")
        sp.add_argument("--game", default=None, help="path to the FF9 install (default: auto-detect)")
        sp.add_argument("--dry-run", dest="dry_run", action="store_true",
                        help="stage every artifact under a SCRATCH mirror; the live install is untouched")

    si = sub.add_parser("summon-import",
                        help="package YOUR retargeted summon model (a Blender .glb from summon-rig-ref, or a "
                             ".fbx) into your mod folder -- validates the bone000..092 rig, mints + deploys")
    si.add_argument("model_file", help="your retargeted .glb (from summon-rig-ref) or a ready .fbx")
    _add_summon_lane_args(si, with_model_flag=False)
    si.add_argument("--clips", default=None,
                    help="overlay lane only: which donor clips to bake to .anim ('all'|'none'|index list)")
    si.add_argument("--scale", type=float, default=None,
                    help="glTF import scale (default 0.01, the summon-rig-ref export scale)")
    si.set_defaults(func=_cmd_summon_import)

    sd_ = sub.add_parser("summon-deploy",
                         help="deploy a [[summon]] transplant (assets) and, with --arm, arm Memoria.ini "
                              "[SfxHybrid] (hybrid lane needs the s58 engine; overlay is DLL-free)")
    _add_summon_lane_args(sd_, with_model_flag=True)
    sd_.add_argument("--clips", default=None,
                     help="overlay lane only: which donor clips to bake to .anim ('all'|'none'|index list)")
    sd_.add_argument("--arm", action="store_true",
                     help="ALSO write Memoria.ini [SfxHybrid] (hybrid lane): backs the ini up, string-probes "
                          "the DLL for SfxHybridDrive, prints the diff. Confirm-first -- omit to only stage "
                          "the assets + print the [SfxHybrid] block. RELAUNCH to apply.")
    sd_.set_defaults(func=_cmd_summon_deploy)

    ssl = sub.add_parser("summon-seq-lint",
                         help="lint a hand-authored SFX .seq / .sfxmodel -- THE SILENT-SKIP GUARD (the "
                              "engine drops an unknown op or arg key with no log at all)")
    ssl.add_argument("files", nargs="+", help="the .seq and/or .sfxmodel files to lint")
    ssl.add_argument("--private-ef", dest="private_ef", type=int, default=None,
                     help="cross-check every LoadSFX/PlaySFX/WaitSFX* `SFX=` id against this private "
                          "effect id (a cast must never LoadSFX a stock id from a private host folder)")
    ssl.add_argument("--particles", default=None,
                     help="comma-separated particle .sfxmodel file names that WILL be staged beside the "
                          "sequence; every `SFXModel=` path must resolve into this set")
    ssl.set_defaults(func=_cmd_summon_seq_lint)

    def _add_summon_edit_args(sp, *, lane: str, suffix: str):
        """The sub-verb ladder + the flags BOTH container-edit lanes share.

        ``--game`` and ``--mod-folder`` are declared ``default=argparse.SUPPRESS`` deliberately: a
        subparser option carrying a literal default OVERWRITES the value the ROOT parser already
        parsed, so ``ff9mapkit --mod-folder X summon-reskin deploy ...`` would silently deploy into
        FF9CustomMap.  That is not hypothetical -- ``summon-import``/``summon-deploy`` still carry it
        (retro-fitting them changes where they deploy, a separate decision).  SUPPRESS means this
        parser contributes the attribute only when the flag is actually given, so whatever the root
        already parsed is what the handler sees; the handlers read both through
        ``getattr(args, name, None)`` so they never depend on the root parser's own defaults.
        """
        # The ladder is shared; the READING verb on the end is per lane -- `read` dumps the camera
        # keyframes, `export-art` decodes the texture pages.  Neither belongs on the other lane, and
        # an action a lane cannot perform is refused by argparse rather than by a handler.
        actions = list(_SUMMON_EDIT_ACTIONS)
        actions += {"rescore": ["read"], "reskin": ["export-art"]}.get(lane, [])
        sp.add_argument("action", choices=actions,
                        help="scaffold: read the stock container and EMIT a guarded spec, every knob "
                             "at identity | plan: build + print every gate, write nothing | build: "
                             "stage the patched container + its scripts under a local-only root | "
                             "verify: re-read what is staged AS BYTES and diff it against a fresh "
                             "rebuild | deploy: write into the resolved mod folder through the ledger "
                             "| revert: run that ledger's own revert script"
                             + (" | read: print the full shot read-out (W1's READ-OUT -- every "
                                "keyframe in human terms), writing nothing" if lane == "rescore"
                                else "")
                             + (" | export-art: decode every creature texture page to a paintable "
                                "INDEXED PNG + a UV coverage overlay + a guarded [[reskin.texel]] "
                                "scaffold, under a local-only root" if lane == "reskin" else ""))
        sp.add_argument("spec", nargs="?", default=None,
                        help="the *_%s.toml (plan/build/verify/deploy, and revert when --ef is "
                             "omitted). With only --ef N, ef###_%s.toml is resolved in the CURRENT "
                             "directory -- never beside the package" % (suffix, suffix))
        sp.add_argument("--ef", type=int, default=None,
                        help="the stock effect id. REQUIRED by `scaffold`; resolves the spec (and, "
                             "for `revert`, the staging root) for the others")
        sp.add_argument("--from", dest="from_path", default=None,
                        help="read this container FILE instead of the install's resources.assets -- "
                             "for an effect this install cannot resolve, or to work offline. Honoured "
                             "by every sub-verb that reads a container, not just scaffold: the drift "
                             "guard runs on the supplied bytes exactly as it does on the install's, "
                             "so a stale file is refused rather than trusted")
        sp.add_argument("--out", default=None,
                        help="scaffold: write the emitted toml here instead of stdout. Every other "
                             "sub-verb: the STAGING ROOT (default: a per-effect dir under the kit's "
                             "local-only summon output root; the repo, a mod-asset tree and the "
                             "install are refused there, with no --force)")
        sp.add_argument("--force", action="store_true",
                        help="scaffold: overwrite an existing spec (refused by default -- replacing "
                             "an authored spec with a fresh identity scaffold is unrecoverable)")
        sp.add_argument("--root", default=None,
                        help="the mod folder, named unconditionally. deploy: without it the "
                             "destination comes from --mod-folder > $FF9_MOD_FOLDER > the nearest "
                             ".ff9deploy.toml > FF9CustomMap. revert: without it (or an explicit "
                             "--mod-folder) the revert runs where the plan RECORDED its writes -- a "
                             "revert's destination is history, not a preference, and rebasing one "
                             "onto a folder it never wrote to deletes somebody else's override")
        sp.add_argument("--dry-run", dest="dry_run", action="store_true",
                        help="deploy: stage into a local dry-run mirror instead of the mod folder "
                             "(the ledger and its revert script are still exercised). revert: print "
                             "what would be restored or deleted and write nothing")
        sp.add_argument("--mod-folder", dest="mod_folder", default=argparse.SUPPRESS,
                        help="mod folder name inside the install (deploy/revert). SUPPRESS-defaulted "
                             "so a root-level --mod-folder survives into this subcommand")
        sp.add_argument("--game", default=argparse.SUPPRESS,
                        help="path to the FF9 install (default: auto-detect). SUPPRESS-defaulted so a "
                             "root-level --game survives into this subcommand")

    srk = sub.add_parser("summon-reskin",
                         help="RECOLOUR or REPAINT a stock summon in place -- its own CLUT palettes "
                              "([[reskin.target]], hue/saturation/value) and/or its own texture "
                              "pages ([[reskin.texel]], the indices themselves: shape, edge and "
                              "silhouette), on the id-4 CREATURE pages and on the SCENERY VRAM "
                              "page-cells at 4 / 8 / 15 bpp. No model, no donor. Every guard is "
                              "derived from the container, and a shared / multi-writer / dual-depth "
                              "/ zero-headroom palette -- or a cell whose DEPTH the container never "
                              "states, a same-bytes-two-depths cell, a program-VRAM WRITE, an "
                              "unnamed co-transform writer or spill column, or an armed texanim "
                              "table that does not DECODE -- REFUSES rather than flickers")
    _add_summon_edit_args(srk, lane="reskin", suffix="reskin")
    srk.add_argument("--previews", action="store_true",
                     help="plan: ALSO render the before/after previews (decoded stock art -- staged "
                          "local-only, never committable)")
    srk.add_argument("--no-previews", dest="no_previews", action="store_true",
                     help="build/deploy: skip the preview render")
    srk.add_argument("--art-lane", dest="art_lane", default="indexed",
                     choices=list(_SUMMON_ART_LANES),
                     help="export-art: the round-trip format. `indexed` (the default) writes a "
                          "P-mode PNG whose pixels ARE the palette indices -- byte-identical on "
                          "93/93 stock creature pages and on every 4/8bpp scenery cell. `direct15` "
                          "is the 15bpp DIRECT-colour surface (RGBA + an explicit STP sidecar), "
                          "proven offline and uncast. `rgba` REFUSES with the measurement that rules "
                          "it out rather than silently not existing")
    srk.add_argument("--no-coverage", dest="no_coverage", action="store_true",
                     help="export-art: skip the UV coverage overlays (they are the instrument that "
                          "tells a painter which texels are live -- ~1/3 of a page never is)")
    srk.set_defaults(func=_cmd_summon_reskin)

    srs = sub.add_parser("summon-rescore",
                         help="RE-FRAME a stock summon's camera in place -- pose / orientation / roll "
                              "/ focal distance on its own camera blocks. Refuses any duration, any "
                              "frame word and any length change: the two clocks stay aligned")
    _add_summon_edit_args(srs, lane="rescore", suffix="rescore")
    srs.set_defaults(func=_cmd_summon_rescore)

    imf = sub.add_parser("image-field",
                         help="EXPERIMENTAL: synthesize a walkable FF9 field from an image + a hand-traced "
                              "floor polygon (Pillow-only; the floor is un-projected into a walkmesh)")
    imf.add_argument("image", help="the source image (becomes the painted background)")
    imf.add_argument("--floor", default=None,
                     help="the floor outline as canvas-pixel points 'cx,cy cx,cy ...' (384x448, top-left, "
                          "Y-down; >=3 points, below the horizon); omit and use --trace to click-trace it")
    imf.add_argument("--trace", action="store_true",
                     help="emit a self-contained click-to-trace HTML page (the exact canvas crop + a pitch-"
                          "linked horizon line) instead of building; it prints the ready image-field command")
    imf.add_argument("--auto-floor", dest="auto_floor", action="store_true",
                     help="detect the floor polygon from the image (seeded region grow from the bottom-"
                          "centre; needs numpy; refuses when unsure). Combine with --trace to pre-load the "
                          "tracer with the detected polygon for hand refinement")
    imf.add_argument("--out", default=None,
                     help="output project dir (writes <name>.field.toml + walkmesh.obj + art/; with --trace, "
                          "where trace.html goes — default: next to the image)")
    imf.add_argument("--name", default="PICTURE", help="field name / project stem (default PICTURE)")
    imf.add_argument("--id", type=int, default=4003, help="field id to stamp in the toml (default 4003)")
    imf.add_argument("--pitch", type=float, default=26.0,
                     help="camera downward pitch in degrees (default 26; FF9 room band 6-48)")
    imf.add_argument("--fov", type=float, default=42.0, help="horizontal FOV (default 42)")
    imf.add_argument("--distance", type=float, default=3000.0,
                     help="camera distance (default 3000; smaller = closer/larger floor)")
    imf.add_argument("--foreground", action="append", default=None,
                     help="a near-occluder cut-out PNG (full-canvas, alpha); repeatable. Bare path = always in "
                          "front of the actor; 'path@cx,cy' anchors it at its floor-contact canvas pixel so "
                          "occlusion flips there (walk in front = actor on top, walk behind = occluded)")
    imf.add_argument("--gateway", action="append", default=None,
                     help="an exit zone 'to[,entrance]@cx,cy;cx,cy;cx,cy;cx,cy' (repeatable): a 4-corner "
                          "quad in canvas pixels sending the player to field 'to'; corners 0-1 become the "
                          "walk-out edge. Un-projected through the same camera as --floor")
    imf.add_argument("--event-zone", dest="event_zone", action="append", default=None,
                     help="a walk-in message zone 'message@cx,cy;cx,cy;cx,cy;cx,cy' (repeatable), same "
                          "canvas-pixel frame as --floor")
    imf.set_defaults(func=_cmd_image_field)

    mp = sub.add_parser("model-preview",
                        help="software-render a model to a PNG still (textured, posed at its stand clip) -- no Blender")
    mp.add_argument("model", help="GEO name or model id to render, e.g. GEO_MAIN_F0_VIV or 8 (see `models`)")
    mp.add_argument("--out", default=None, help="output .png path (default: <model>.png in the current dir)")
    mp.add_argument("--size", type=int, default=256, help="image size in px (square; default 256)")
    mp.add_argument("--yaw", type=float, default=30.0, help="turntable angle in degrees (default 30: a 3/4 view)")
    mp.add_argument("--pitch", type=float, default=12.0, help="look-down angle in degrees (default 12)")
    mp.add_argument("--rest", action="store_true",
                    help="render the raw rest pose instead of frame 0 of the model's stand clip")
    mp.add_argument("--game", default=argparse.SUPPRESS, help="path to the FF9 install (default: auto-detect)")
    mp.set_defaults(func=_cmd_model_preview)

    mr = sub.add_parser("model-reskin",
                        help="the cheapest model edit: export a model's textures, or deploy edited PNGs "
                             "as a loose reskin (no Blender, no FBX, no DLL)")
    mr.add_argument("model", help="GEO name or model id to reskin, e.g. GEO_MAIN_F0_VIV or 8 (see `models`)")
    mr.add_argument("--export-textures", metavar="DIR", default=None,
                    help="write the model's pristine textures as editable {stem}.png files into DIR")
    mr.add_argument("--texture", metavar="PNG", nargs="+", default=None,
                    help="edited PNG file(s) to ship -- each must KEEP its {stem}.png name")
    mr.add_argument("--deploy", metavar="MODFOLDER", default=None,
                    help="mod folder to write the reskin into (the model's own override dir)")
    mr.add_argument("--game", default=argparse.SUPPRESS, help="path to the FF9 install (default: auto-detect)")
    mr.set_defaults(func=_cmd_model_reskin)

    mdp = sub.add_parser("model-deployed",
                         help="list (or revert) a mod folder's loose model overrides / reskins / mints / "
                              "anim overrides -- the read side of the write-only override system")
    mdp.add_argument("mod_folder", help="the mod folder to scan, e.g. <game>/FF9CustomMap")
    mdp.add_argument("--revert", type=int, metavar="ID", default=None,
                     help="delete the deployed entry at this model id (a mint also loses its 3DModel line)")
    mdp.add_argument("--kind", choices=["override", "reskin", "mint", "anims", "mint-directive"],
                     default=None, help="disambiguate --revert when an id has several entry kinds")
    mdp.set_defaults(func=_cmd_model_deployed)

    pa = sub.add_parser("playable-anims",
                        help="the Blender edit loop for a 13th character's custom_battle_anims animset -- route "
                             "edited donor clips onto the character's OWN minted animset (donor untouched)")
    pa.add_argument("field", help="the field.toml carrying the [[playable]] custom_battle_anims block")
    pa.add_argument("--export", metavar="GLB", default=None,
                    help="export the DONOR battle model + its animset to this .glb for Blender, with each Action "
                         "NAMED by its battle motion ('23_attack', '27_cast') instead of a raw clip key")
    pa.add_argument("--edit", metavar="GLB", default=None,
                    help="a Blender-edited .glb (from --export) to route onto the character's animset. Omit "
                         "both --export/--edit for INFO (the whole loop + the motion->key table).")
    pa.add_argument("--deploy", metavar="MODFOLDER", default=None,
                    help="mod folder to write the character's Animations/<mintId>/ animset into (with --edit)")
    pa.add_argument("--name", default=None,
                    help="the [[playable]] name, if the field defines more than one custom_battle_anims character")
    pa.add_argument("--game", default=argparse.SUPPRESS, help="path to the FF9 install (default: auto-detect)")
    pa.set_defaults(func=_cmd_playable_anims)

    for _snd, _label in (("music", "music"), ("sfx", "SFX")):
        sl = sub.add_parser(f"{_snd}-list", help=f"list {_label} song-id -> ResourceID (what audio-import replaces)")
        sl.add_argument("--filter", default=None, help="substring or exact-id filter")
        sl.add_argument("--game", default=argparse.SUPPRESS, help="path to the FF9 install (default: auto-detect)")
        sl.set_defaults(func=_cmd_sound_list, kind=_snd)

    ai = sub.add_parser("audio-import",
                        help="import a custom MUSIC/SFX track (Ogg Vorbis): REPLACE an id or MINT a new one -- DLL-free")
    ai.add_argument("input", help="source audio (wav/mp3/ogg/flac/...) -- transcoded to Ogg Vorbis")
    _tgt = ai.add_mutually_exclusive_group(required=True)
    _tgt.add_argument("--song", type=int, help="REPLACE this existing id (see `music-list`/`sfx-list`)")
    _tgt.add_argument("--new-song", action="store_true",
                      help="MINT a NEW id (add a track, don't swap); id auto-picked (>=1000) unless --id. Trigger "
                           "it with a field's [music] song = <id>")
    ai.add_argument("--id", type=int, default=None, help="the id to mint at (with --new-song; default: auto-pick)")
    ai.add_argument("--kind", choices=["music", "sfx"], default="music", help="music (default) or sfx")
    ai.add_argument("--loop-start", type=int, default=None,
                    help="loop start SAMPLE (music auto-loops the whole track if omitted; ignored for sfx)")
    ai.add_argument("--loop-end", type=int, default=None, help="loop end SAMPLE")
    ai.add_argument("--quality", type=int, default=6, help="libvorbis quality 0-10 (default 6)")
    ai.add_argument("--no-set-priority", action="store_true",
                    help="don't touch Memoria.ini -- you must set [Audio] PriorityToOGG=1 yourself or the "
                         "bundled track wins")
    ai.add_argument("--deploy", metavar="MODFOLDER", default=None, help="mod folder to write the override into")
    ai.add_argument("--game", default=argparse.SUPPRESS, help="path to the FF9 install (default: auto-detect)")
    ai.set_defaults(func=_cmd_audio_import)

    bb = sub.add_parser("battle-build", help="compile a battle.toml into a Memoria mod (custom battle map)")
    bb.add_argument("battle", nargs="+", help="one or more battle.toml files")
    bb.add_argument("--out", default="dist", help="output mod folder (default: ./dist)")
    bb.add_argument("--mod-name", default="FF9CustomMap", help="mod name / InstallationPath")
    bb.add_argument("--author", default="", help="mod author")
    bb.add_argument("--description", default="", help="mod description")
    bb.add_argument("--game", default=argparse.SUPPRESS,
                    help="FF9 install dir (only needed for an enemy re-skin `[[scene.enemy]] model =`, which "
                         "reads a donor model from the install; default: $FF9_GAME_PATH / common Steam paths)")
    bb.set_defaults(func=_cmd_battle_build)

    bl = sub.add_parser("battle-list",
                        help="list real FF9 battle backgrounds available to fork (needs UnityPy)")
    bl.add_argument("pattern", nargs="?", default=None, help="substring filter (e.g. b013)")
    bl.add_argument("--scenes", action="store_true",
                    help="list battle SCENE names (mint donors, e.g. EF_R007) instead of map names")
    bl.set_defaults(func=_cmd_battle_list)

    bac = sub.add_parser("battle-actions",
                         help="list the shared PLAYER abilities (Actions.csv) + the scriptId formula catalog")
    bac.add_argument("-f", "--filter", help="only show actions whose name contains this")
    bac.add_argument("--script-ids", action="store_true",
                     help="dump the scriptId->formula catalog (the data-vs-DLL boundary)")
    bac.set_defaults(func=_cmd_battle_actions)

    we = sub.add_parser("world-extract",
                        help="extract an overworld block's terrain mesh (geometry + per-tile ids) -- Path C "
                             "geometry-edit foundation (needs UnityPy)")
    we.add_argument("--disc", type=int, default=1, help="world disc: 1 or 4 (default 1)")
    we.add_argument("--block", type=int, nargs=2, metavar=("X", "Y"),
                    help="block grid coords to extract, e.g. --block 3 7")
    we.add_argument("--lod", default="0_1", help="LOD dir (0_1 = the walkmesh form, default; 0_2 = far LOD)")
    we.add_argument("--list", action="store_true",
                    help="list the disc's terrain blocks instead of extracting one")
    we.add_argument("--out", help="output dir for the .obj + .mapids.json (default: current dir)")
    we.set_defaults(func=_cmd_world_extract)

    wd = sub.add_parser("world-deploy",
                        help="deploy an (optionally reshaped) overworld block/region as loose .ff9mesh override(s) "
                             "(needs the WorldMeshOverride engine patch)")
    wd.add_argument("--block", type=int, nargs=2, metavar=("X", "Y"),
                    help="a single block, e.g. --block 3 7 (faithful copy / lift / spike / a small local hill)")
    wd.add_argument("--cluster", type=int, nargs=4, metavar=("XMIN", "YMIN", "XMAX", "YMAX"),
                    help="a rectangular block span; its centre seeds a reshape (deployed as-is for --lift/--spike)")
    wd.add_argument("--disc", type=int, default=1, help="world disc: 1 or 4 (default 1)")
    wd.add_argument("--lod", default="0_1", help="LOD dir (default 0_1, the walkmesh form)")
    wd.add_argument("--mod-folder", required=True,
                    help="the stacked FolderNames mod folder to deploy into (e.g. FF9CustomMap)")
    # purposeful reshaping (seam-continuous; auto-redeploys every block the radius touches)
    wd.add_argument("--hill", type=float, default=0.0,
                    help="raise a smooth HILL of this peak height (world units), e.g. --hill 24")
    wd.add_argument("--crater", type=float, default=0.0,
                    help="sink a smooth CRATER of this depth (world units)")
    wd.add_argument("--flatten", action="store_true", help="flatten the region to a plateau/clearing")
    wd.add_argument("--height", type=float, default=None,
                    help="target height for --flatten (default: the region's mean height)")
    wd.add_argument("--radius", type=float, default=96.0,
                    help="reshape radius in world units (default 96 = 1.5 blocks)")
    wd.add_argument("--center", type=float, nargs=2, metavar=("WX", "WZ"),
                    help="reshape centre in world XZ (default: the --block/--cluster centre)")
    wd.add_argument("--falloff", choices=["smooth", "gauss", "cone"], default="smooth",
                    help="reshape falloff shape (default smooth = creaseless smoothstep dome)")
    wd.add_argument("--no-normals", action="store_true",
                    help="skip the smooth-normal recompute after a reshape (leaves stale shading)")
    wd.add_argument("--allow-entrances", action="store_true",
                    help="override the safety refusal when a reshape touches a place-entrance block "
                         "(raising/lowering those softlocks the player + pits the entrance prop)")
    # diagnostics (single-vertex / whole-block, no auto-expand -- the override-mechanism proofs)
    wd.add_argument("--spike", type=float, default=0.0,
                    help="[diag] raise the centre vertex by N units (tears on the unindexed mesh; a hook test)")
    wd.add_argument("--lift", type=float, default=0.0,
                    help="[diag] raise the WHOLE block(s) by N units -- an unmistakable plateau")
    wd.add_argument("--skip-mirror", action="store_true",
                    help="don't auto-mirror the written override(s) to Disc4 (THE DISC-4 GAP; default: mirror)")
    wd.set_defaults(func=_cmd_world_deploy)

    wl = sub.add_parser("world-locate",
                        help="decode which overworld cells/blocks lead to which field -- the entrance dispatch "
                             "(cell trigger -> Byte[39] case -> Field), with ScenarioCounter branches + navipos "
                             "landmark naming (the reliable place->blocks map)")
    wl.add_argument("--case", "--area", dest="case", type=int,
                    help="show only this dispatch case (Map.Byte[39]; --area is the deprecated pre-census spelling "
                         "-- the case never was the tile IDALL area)")
    wl.add_argument("--block", type=int, nargs=2, metavar=("X", "Y"),
                    help="show the entrance trigger(s) whose cells sit in this block")
    wl.add_argument("--field", type=int, help="show which cases/cells lead to this destination field id")
    wl.set_defaults(func=_cmd_world_locate)

    wr = sub.add_parser("world-retarget",
                        help="edit a world tile's IDALL (tangent.x): topograph = WALKABILITY/terrain (in-game "
                             "proven); event/area = trigger flag only -- a real entrance needs a world .eb entry")
    wr.add_argument("--block", type=int, nargs=2, metavar=("X", "Y"), required=True,
                    help="the block to edit (pick with world-locate)")
    wr.add_argument("--disc", type=int, default=1, help="world disc (default 1)")
    wr.add_argument("--lod", default="0_1", help="LOD dir (default 0_1)")
    wr.add_argument("--mod-folder", required=True, help="the stacked FolderNames mod folder to deploy into")
    wr.add_argument("--area", type=int, help="set the tile's IDALL area bits -- a COSMETIC regional tag, NOT the "
                                             "dispatch key (the destination comes from the cell's dispatcher "
                                             "trigger; see world-locate / world-entrance)")
    wr.add_argument("--event", type=int, choices=[0, 1, 2, 3],
                    help="set the event-trigger bits (0=land, 1-3=fires WorldEvent) -- NOTE: bits alone do NOT make "
                         "a working entrance; the destination is a world .eb entry keyed to the cell")
    wr.add_argument("--topograph", type=int, help="set the topograph/terrain type (default: keep each tile's own)")
    wr.add_argument("--center", type=float, nargs=2, metavar=("WX", "WZ"),
                    help="limit to tiles within --radius of this world XZ (default: the whole block)")
    wr.add_argument("--radius", type=float, help="region radius in world units around --center")
    wr.add_argument("--only-entrances", action="store_true",
                    help="only retarget tiles that ALREADY carry an entrance (re-point, don't create)")
    wr.add_argument("--skip-mirror", action="store_true",
                    help="don't auto-mirror the written override to Disc4 (THE DISC-4 GAP; default: mirror)")
    wr.set_defaults(func=_cmd_world_retarget)

    wme = sub.add_parser("world-mesh-export",
                         help="export a block Object/Terrain sub-mesh to OBJ for Blender mesh surgery (splice a "
                              "multi-block building, reshape, or model new) -- UVs+normals preserved, world coords")
    wme.add_argument("--block", type=int, nargs=2, metavar=("X", "Y"), action="append", required=True,
                     help="a block to export; repeatable -- e.g. --block 20 10 --block 19 10 to splice a multi-block structure")
    wme.add_argument("--part", choices=["object", "terrain"], default="object",
                     help="object = buildings/structures (default); terrain = ground/walkmesh")
    wme.add_argument("--disc", type=int, default=1, help="world disc (default 1)")
    wme.add_argument("--lod", default="0_1", help="LOD dir (default 0_1)")
    wme.add_argument("--out", required=True, help="output .obj path")
    wme.set_defaults(func=_cmd_world_mesh_export)

    wmb = sub.add_parser("world-mesh-build",
                         help="rebuild an edited OBJ into a block's loose .ff9mesh override + deploy (Object = a "
                              "building; the per-triangle IDALL is stamped uniformly -- topo 59 = impassable)")
    wmb.add_argument("obj", help="the edited .obj exported from Blender")
    wmb.add_argument("--into-block", type=int, nargs=2, metavar=("X", "Y"), required=True,
                     help="the TARGET block whose local frame + override path the mesh is written into")
    wmb.add_argument("--part", choices=["object", "terrain"], default="object")
    wmb.add_argument("--disc", type=int, default=1, help="world disc (default 1)")
    wmb.add_argument("--lod", default="0_1", help="LOD dir (default 0_1)")
    wmb.add_argument("--topograph", type=int, default=59,
                     help="topograph stamped on every triangle's IDALL (default 59 = the stock impassable structure "
                          "type; a building blocks on-foot)")
    wmb.add_argument("--idall", type=int, metavar="N",
                     help="stamp this RAW 16-bit IDALL on every triangle instead of encoding --topograph -- the only "
                          "way to set the area/flags bit-fields. Pass 4078 (0x0FEE) for a RENDER-ONLY marker: "
                          "WMPhysics skips 4078/4088/2040, so the mesh is walk-through and cannot shadow an entrance "
                          "trigger (a spawn/arrive sky-cast still hits it -- keep marker tris clear of those)")
    wmb.add_argument("--mod-folder", required=True, help="the stacked FolderNames mod folder to deploy into")
    wmb.add_argument("--at", type=float, nargs=2, metavar=("WX", "WZ"),
                     help="place the mesh's XZ centre at this WORLD spot (so you can MODEL AT THE ORIGIN in Blender "
                          "and drop it here); omit to treat the OBJ as already world-positioned")
    wmb.add_argument("--seat", action="store_true",
                     help="drop the mesh so its lowest point rests on the terrain surface at --at (auto-ground)")
    wmb.add_argument("--keep-block", action="store_true",
                     help="merge with the block's STOCK structures (keep e.g. the town already there) instead of "
                          "replacing them")
    wmb.add_argument("--texture", action="store_true",
                     help="stamp real atlas tiles onto UV-less new faces (a Blender model without UVs, or the "
                          "--solid-base hull) from the learned palette -- so they render textured, not [0,0] white")
    wmb.add_argument("--tile", metavar="TOPO:VARIANT",
                     help="force ONE specific atlas tile on all new faces (e.g. 52:0 = a castle wall); pick it from "
                          "`world-atlas-catalog`. Implies --texture")
    wmb.add_argument("--tile-uv", metavar="Umin,Vmin,Umax,Vmax",
                     help="stamp a CUSTOM UV rect on all new faces -- the region a NEW tile you painted via "
                          "`world-atlas-add-tile` occupies (T3)")
    wmb.add_argument("--skip-mirror", action="store_true",
                     help="don't auto-mirror the written override to Disc4 (THE DISC-4 GAP; default: mirror)")
    wmb.set_defaults(func=_cmd_world_mesh_build)

    wtp = sub.add_parser("world-texture-palette",
                         help="inspect the learned overworld atlas UV palette (topograph -> real donor tiles) that "
                              "`world-mesh-build --texture` stamps onto new geometry")
    wtp.add_argument("--disc", type=int, default=1, help="world disc (default 1)")
    wtp.add_argument("--part", choices=["terrain", "object"], default="terrain")
    wtp.add_argument("--max-blocks", type=int, default=24, help="how many real blocks to sample (default 24)")
    wtp.add_argument("--no-cache", action="store_true", help="force a fresh scan instead of the cached palette")
    wtp.set_defaults(func=_cmd_world_texture_palette)

    wax = sub.add_parser("world-atlas-extract",
                         help="extract the shared overworld texture atlas (terrain/object) to a PNG for previewing "
                              "or repainting -- by default the atlas the ENGINE renders (mod-stack resolved)")
    wax.add_argument("--part", choices=["terrain", "object"], default="terrain")
    wax.add_argument("--out", required=True, help="output PNG path")
    wax.add_argument("--source", choices=["engine", "bundle"], default="engine",
                     help="'engine' (default) = the atlas the game renders, resolved like SearchAssetOnDisc across "
                          "the Memoria.ini FolderNames stack (e.g. Moguri's HD atlas); "
                          "'bundle' = the vanilla 1024x1024 p0data atlas")
    wax.set_defaults(func=_cmd_world_atlas_extract)

    wac = sub.add_parser("world-atlas-catalog",
                         help="render a visual tile CATALOG (each topograph's real donor tiles as labeled thumbnails) "
                              "so you can pick a texture by eye for `world-mesh-build --tile`")
    wac.add_argument("--part", choices=["terrain", "object"], default="terrain")
    wac.add_argument("--disc", type=int, default=1, help="world disc (default 1)")
    wac.add_argument("--per-topo", type=int, default=8, help="thumbnails per topograph row (default 8)")
    wac.add_argument("--out", required=True, help="output PNG (contact sheet) path")
    wac.set_defaults(func=_cmd_world_atlas_catalog)

    war = sub.add_parser("world-atlas-reskin",
                         help="deploy a repainted atlas PNG as a no-DLL HD reskin (T2): same UV layout, new pixels")
    war.add_argument("png", help="the repainted atlas PNG (1024x1024, same tile layout)")
    war.add_argument("--part", choices=["terrain", "object"], default="terrain")
    war.add_argument("--mod-folder", required=True, help="the FolderNames mod folder to deploy into")
    war.set_defaults(func=_cmd_world_atlas_reskin)

    wtr = sub.add_parser("world-terrain",
                         help="reshape WALKABLE overworld terrain -- raise/lower/flatten a hill or a ridge/valley by "
                              "deforming the stock mesh across every block it touches (seamless). No DLL; relaunch.")
    wtr.add_argument("--mod-folder", required=True, help="the FolderNames mod folder to deploy into")
    wtr.add_argument("--radius", type=float, required=True, help="reshape radius (world units)")
    _shape = wtr.add_mutually_exclusive_group(required=True)
    _shape.add_argument("--at", type=float, nargs=2, metavar=("X", "Z"), help="a radial hill/crater centre (world XZ)")
    _shape.add_argument("--ridge", type=float, nargs=4, metavar=("X0", "Z0", "X1", "Z1"),
                        help="a ridge/valley along the world-XZ segment (X0,Z0)->(X1,Z1)")
    _op = wtr.add_mutually_exclusive_group(required=True)
    _op.add_argument("--raise", dest="raise_h", type=float, metavar="H", help="raise by H (a hill / ridge)")
    _op.add_argument("--lower", type=float, metavar="H", help="lower by H (a crater / valley)")
    _op.add_argument("--flatten", action="store_true", help="flatten toward --height (default the local mean); radial")
    wtr.add_argument("--height", type=float, help="with --flatten: the target Y (default = the local mean)")
    wtr.add_argument("--falloff", default="smooth", help="edge falloff (default smooth)")
    wtr.add_argument("--disc", type=int, default=1, help="world disc (default 1)")
    wtr.add_argument("--dry-run", action="store_true", help="report the blocks it would reshape, write nothing")
    wtr.add_argument("--skip-mirror", action="store_true",
                     help="don't auto-mirror the written override(s) to Disc4 (THE DISC-4 GAP; default: mirror)")
    wtr.set_defaults(func=_cmd_world_terrain)

    wrc = sub.add_parser("world-reclaim",
                         help="RECLAIM ocean cells as walkable LAND (Path D -- new continent): synthesize a flat, "
                              "textured, walkable terrain override per sea cell. Needs the custom engine; relaunch.")
    wrc.add_argument("--mod-folder", required=True, help="the FolderNames mod folder to deploy into")
    wrc.add_argument("--target-disc", type=int, default=None, help="deploy the produced overrides into THIS disc's namespace instead of --disc's. --disc stays the READ disc (which stock tree real bytes are borrowed from; only 1 or 4 exist). Use 9 for a Path D synthetic world, whose engine-side override namespace is deliberately disjoint from the real trees.")
    wrc.add_argument("--all-sea-target", action="store_true", help='the target grid is ALL SEA (a blank Path D world), so skip the open-ocean/real-land probes that read the unrelated real disc. Do NOT pass this for an s75 CLONE target -- a clone carries the stock IsSea pattern, so those probes are correct there and must keep running.')
    wrc.add_argument("--cells", required=True,
                     help="sea cells to reclaim: 'x,y;x,y' (e.g. '2,5;3,5') or a range 'x0-x1,y0-y1' (a landmass). "
                          "Grid is 24x20; a lone cell is an island, a contiguous run bridges from the coast.")
    wrc.add_argument("--profile", choices=["island", "flat", "cliff"], default="island",
                     help="'island' (default) = grass plateau ramping to a sand beach ring; 'cliff' = rolling land top "
                          "dropping via a STEEP near-vertical ROCK WALL to the waterline (FAITHFUL to 208 real cliffs: "
                          "~73deg, arc-length rock UVs); 'flat' = a bare slab of one --topograph")
    wrc.add_argument("--height", type=float, default=None,
                     help="land Y: plateau/wall height (default island 6 / cliff 3.2 ~ real interior-land Y) or flat-slab Y (default 0)")
    wrc.add_argument("--beach", type=float, default=None,
                     help="island shore ramp WIDTH in units (default 22 gentle) -- how far the drop slopes inland (island profile)")
    wrc.add_argument("--rim-run", type=float, default=None,
                     help="cliff wall RUN in units (default 1.0 -> ~73deg at height 3.2); smaller = steeper (cliff profile)")
    wrc.add_argument("--shore-topo", type=int, default=None,
                     help="island shore-edge terrain type (default 20 sand; 58 is on-foot BLOCKED)")
    wrc.add_argument("--topograph", type=int, default=0,
                     help="flat-profile terrain type (default 0 = plains; 49/58/59 are BLOCKED)")
    wrc.add_argument("--seg", type=int, default=10, help="tessellation per 64u block edge (default 10)")
    wrc.add_argument("--disc", type=int, default=1, help="world disc (default 1)")
    wrc.add_argument("--dry-run", action="store_true", help="report the cells it would reclaim, write nothing")
    wrc.add_argument("--skip-mirror", action="store_true",
                     help="don't auto-mirror the written override(s) to Disc4 (THE DISC-4 GAP; default: mirror)")
    wrc.set_defaults(func=_cmd_world_reclaim)

    wct = sub.add_parser("world-coast",
                         help="FAITHFUL coast (Path D): place a REAL FF9 coastal block at ocean cells -- copies its "
                              "terrain + animated beach/sea/foam (via a Donor.txt sidecar). --list browses donors.")
    wct.add_argument("--target-disc", type=int, default=None, help="deploy the produced overrides into THIS disc's namespace instead of --disc's. --disc stays the READ disc (which stock tree real bytes are borrowed from; only 1 or 4 exist). Use 9 for a Path D synthetic world, whose engine-side override namespace is deliberately disjoint from the real trees.")
    wct.add_argument("--mod-folder", default=argparse.SUPPRESS,
                     help="the FolderNames mod folder to deploy into (default FF9CustomMap)")
    wct.add_argument("--cells", help="target ocean cells: 'x,y;x,y' or a range 'x0-x1,y0-y1'")
    wct.add_argument("--donor", help="the REAL coastal donor block 'dx,dy' to copy (e.g. 18,15; see --list)")
    wct.add_argument("--list", action="store_true", help="list real coastal donor blocks (with a beach) and exit")
    wct.add_argument("--all-coasts", action="store_true", help="with --list: include sea-fringed coasts, not just beaches")
    wct.add_argument("--disc", type=int, default=1, help="world disc (default 1)")
    wct.add_argument("--dry-run", action="store_true", help="report what it would place, write nothing")
    wct.add_argument("--skip-mirror", action="store_true",
                     help="don't auto-mirror the written override(s) to Disc4 (THE DISC-4 GAP; default: mirror)")
    wct.set_defaults(func=_cmd_world_coast)

    wtp = sub.add_parser("world-transplant",
                         help="VERBATIM island transplant: carry a complete real coastal block (land + beach + "
                              "the full Wang'd ocean, every sub-mesh) to a custom ocean cell, with a 0-mod-4 "
                              "in-cell shift + 90-degree rotation -- fully verbatim, offline-gated (placement "
                              "census + weld audit). Needs the custom engine; relaunch.")
    wtp.add_argument("--mod-folder", required=True, help="the FolderNames mod folder to deploy into")
    wtp.add_argument("--cell", required=True, metavar="BX,BY", help="target ocean cell (grid 24x20)")
    wtp.add_argument("--donor", required=True, metavar="DX,DY",
                     help="the real donor block to carry; 7,17 is the proven beach island "
                          "(world-coast --list browses coastal donors). With --size, the donor RECT's "
                          "min-x,min-y anchor cell.")
    wtp.add_argument("--size", default="1x1", metavar="NXxNY",
                     help="carry a MULTI-CELL donor rect of NXxNY blocks as ONE rigid assembly (e.g. 2x1 = a "
                          "real 2-block landmass); --cell anchors the target rect (swaps to NYxNX under rot "
                          "90/270), each target cell gets its own overrides + Donor.txt sidecar, interior "
                          "borders re-partition watertight. Default 1x1 = the proven single-cell path.")
    wtp.add_argument("--rot", type=int, default=0, choices=(0, 90, 180, 270),
                     help="rotate about the cell (with --size: the region) centre -- 90-degree multiples keep "
                          "the 4u tile lattice (and the Wang ocean) fully verbatim (default 0)")
    wtp.add_argument("--grow-cut", default=None, metavar="X[,X..]",
                     help="RowInsert GROWTH cuts at these DONOR-frame x lattice lines (comma-separated; each "
                          "census-clean per `cut_census` -- straddle-0, no component risks). Each cut inserts "
                          "one 4u column: everything east shifts +4 and the vacated column is filled per the "
                          "learned tile laws. Composes with --size (a region cut's shift crosses interior "
                          "borders and its fill spans rows); REGION lines are census-validated here and any "
                          "empty-cell boundary fills (certified open water) are wired automatically -- a "
                          "clean pure-water line is a legal SLIDE cut. Growth eats the land margin -- "
                          "usually needs --land-margin 0.")
    wtp.add_argument("--grow-cut-z", default=None, metavar="Z[,Z..]",
                     help="z-axis growth cuts at these DONOR-frame z lattice planes (negative values -- "
                          "use --grow-cut-z=-384 form; census `cut_census axis='z'`). Each cut inserts one "
                          "4u ROW: everything SOUTH shifts -4 and the vacated row is filled per the same "
                          "tile laws (the exact-rotation adapter over the proven x-cut). Composes with "
                          "--grow-cut; region lines are census-validated + boundary fills auto-wired.")
    wtp.add_argument("--cliff-bump", default=None, metavar="X0,Z0:X1,Z1:D",
                     help="CLIFF-COAST MORPH rung 1 (in-game proven 2026-07-09): bow the cliff-base outline "
                          "run between the two DONOR-frame endpoints seaward by a sin^2 profile of depth D "
                          "(units; the conforming envelope is ~2.5 -- a depth that would fold a waterline "
                          "tile is refused offline). Land UVs drag; water re-evaluates through its own tile "
                          "map (no caustic stretch). Needs a pure-sea4 shore (the cliff seam law).")
    wtp.add_argument("--cliff-headland", default=None, metavar="X0,Z0:X1,Z1:D",
                     help="CLIFF-COAST MORPH rung 2 (in-game proven 2026-07-09): rebuild the window's wall "
                          "over a sin^2-pushed outline of depth D as a structural PROMONTORY -- one inserted "
                          "wall column per gap (the window's gap count must be a multiple of 4, the "
                          "deterministic-U-ramp law), native lattice grass re-fill, sea zipped back to the "
                          "new outline. Every law gate (crack/grain/water-density/ledger) runs offline.")
    wtp.add_argument("--beach-bump", default=None, metavar="X0,Z0:X1,Z1:D",
                     help="the BEACH conforming bow (the beach frontier's rung 1): bow a sandy shore's "
                          "WATERLINE (beach1's seaward boundary -- every vert welded with sea2) by a sin^2 "
                          "profile of depth D (+ = seaward). Foam and wash drag together; the swash ribbon "
                          "breathes within the real 3.3-6.7u envelope (the RIBBON GATE refuses a bow that "
                          "pinches or overstretches it). Endpoints = two waterline verts (donor frame).")
    wtp.add_argument("--cliff-lobes", default=None, metavar="X0,Z0:X1,Z1:D1,D2,..",
                     help="COMPOSED morphs in ONE window: a piecewise profile of sin^2 lobes, one per "
                          "signed depth (+ = seaward headland, - = landward bay; '3.5,-5,6.5' = a bay "
                          "between two headlands). One reshape = walls, fills and sea zip continuous "
                          "across the lobes by construction. Every law gate applies to the whole "
                          "composition (reach, crack/grain with the ring-extension ladder, water "
                          "density, signed ledger).")
    wtp.add_argument("--cliff-bay", default=None, metavar="X0,Z0:X1,Z1:D",
                     help="the promontory's inward mirror: carve a structural BAY of depth D into the window "
                          "-- the wedge consumes grass (crease-footprint drops + native re-fill of the rim "
                          "ring), the rebuilt wall lines the cove, the sea zips landward over the vacated "
                          "wedge (beyond-the-shore zip tiles are translate-CLONES of the nearest real tile, "
                          "never raw extrapolation). Same laws + gates as the headland; a too-deep bay that "
                          "reaches a land component is refused offline.")
    wtp.add_argument("--allow-mod-overwrite", action="store_true",
                     help="waive THE MOD-OVERWRITE GATE: by default a target data cell that "
                          "already holds override files in the mod folder REFUSES unless its "
                          "Donor.txt names this deploy's own sidecar donor (a re-deploy of the "
                          "same transplant). The stock real-target gate cannot see mod content "
                          "-- this one keeps a prior islet/transplant from being silently "
                          "replaced (the dunes-islet incident, 2026-07-15).")
    wtp.add_argument("--enforce-wang-carry", action="store_true", dest="enforce_wang_carry",
                     help="ENFORCE THE WANG-CARRY GATE (default report-only): FAIL the build when the "
                          "carried region's outer frame has a mid (Sea3) / mis-oriented Sea5 tile OR a "
                          "shallow (Sea1/Sea2) tile facing the open-ocean deep ring (a cropped-Wang hard "
                          "shallow|deep seam, no transition ring; stock abuts neither mid nor shallow "
                          "water to the deep ring). Use for a fresh mint onto known-deep ocean (every "
                          "frame edge is a crop); a coastal donor's own pre-existing shelf would false-"
                          "positive, so it stays opt-in until the donor-baseline subtraction lands.")
    wtp.add_argument("--allow-wang-seams", action="store_true", dest="allow_wang_seams",
                     help="waive THE WANG-CARRY GATE even when enforced (--enforce-wang-carry).")
    wtp.add_argument("--enforce-orphan-decals", action="store_true", dest="enforce_orphan_decals",
                     help="ENFORCE THE ORPHAN-DECAL GATE (default report-only): FAIL the build when "
                          "the carried region wears a transition-vocabulary decal (a grass|desert or "
                          "desert|dunes STRIPS fringe/straddle tile) without the neighbourhood "
                          "context that justifies it -- a same-cell straddle for rows 1/3, the "
                          "partner family within 2 cells for rows 0/2 -- or with a topo byte that "
                          "breaks its own decal group's measured norm. The comp[1] orphan-decal "
                          "class (studies/overworld-topography/GROUND-FAMILY-DECODE-2026-07-19.md "
                          "Round 10 + comp1_orphan_redress.py).")
    wtp.add_argument("--allow-orphan-decals", action="store_true", dest="allow_orphan_decals",
                     help="waive THE ORPHAN-DECAL GATE even when enforced (--enforce-orphan-decals).")
    wtp.add_argument("--enforce-texture-gates", action="store_true", dest="enforce_texture_gates",
                     help="ENFORCE THE TEXTURE + SEA GATES (default report-only): FAIL the build on "
                          "a zero-UV-area / bit-identical-UV Terrain tri above the 0.0005 ceiling "
                          "(the constant-UV stamp -- the flat-sheet stain the Rung-F UV arc spent 8 "
                          "in-game rounds removing), a ground tri whose UVs escape its own family's "
                          "catalogued mains rect (a transparent atlas gutter = white in game), or a "
                          "sea-plan violation (land fully submerged under the y=0 plane, adjacent "
                          "blocks' Sea4 plan areas differing by more than 4x -- the degenerate "
                          "one-blob Sea4 stub -- or real water overlapping land in plan beyond "
                          "stock's own 0.1913 headline). All three measure CLEAN on real stock "
                          "bytes, so this is safe to enforce on a verbatim carry; it stays opt-in "
                          "only to match the two carry gates above.")
    wtp.add_argument("--allow-texture-gates", action="store_true", dest="allow_texture_gates",
                     help="waive THE TEXTURE + SEA GATES even when enforced "
                          "(--enforce-texture-gates).")
    wtp.add_argument("--redress-orphans", action="store_true", dest="redress_orphans",
                     help="auto-fix every ORPHAN-DECAL GATE finding to the wearing side's plain "
                          "GROUNDS mains (assign_mains + ground_uv, the proven FIX-G shape: UV "
                          "always, topo only when the tri still carries the decal's own dedicated "
                          "fringe topo) IN MEMORY at build time, before any write. Changes output "
                          "bytes vs. a plain carry -- opt-in; a byte-identical re-run needs this "
                          "flag every time.")
    wtp.add_argument("--ground", default=None, metavar="FAMILY",
                     help="RETILE the carried block to another ground family by the byte-measured "
                          "TRANSLATION LAWS (grassland.GROUNDS + coastmorph.SAND_BANDS): ground "
                          "mains and the rock wall band shift by the family deltas, the sand band "
                          "re-pins onto the target's own pins (topo 31->32), beach1 foam relabels "
                          "(30->34, the texture is universal); geometry/heights/water stay "
                          "byte-verbatim. A donor texture class with no measured translation "
                          "REFUSES offline (path strips re-uv as target mains under a prescan "
                          "budget). Beach donors need a target with a measured sand family "
                          "(currently: desert). Composes with --size (the prescan mirrors the "
                          "region gather).")
    wtp.add_argument("--strips-rebuild", action="store_true",
                     help="the STRIP-BAND identity rebuild (the sea5-emission proof): drop every "
                          "DECODABLE sea1 + sea5 Wang strip cell of the donor and re-derive its tiles "
                          "from the learned table over the same verts (fresh anti-tiling variant picks "
                          "-- indistinguishable by design). Inset-rect variants (~7%% of sea5, the "
                          "sea3-inset family) and conforming ring tris stay verbatim. Every emitted "
                          "cell self-checks by re-decode.")
    wtp.add_argument("--beach-mint", default=None, metavar="WIDTH|auto[:LAND]",
                     help="BEACH-MINT: re-mint the donor's beach sand+foam assembly from "
                          "chain specs -- interfaces pinned (land chain/waterline/end welds), "
                          "everything between synthesized (a smooth seam chain at the given "
                          "band WIDTH in world units, eased from the pinned ends; 'auto' keeps "
                          "the end-width profile), clean column topology (no fan transport), "
                          "fresh sand P/Q + foam run/BL-cap language walks. The optional "
                          ":LAND suffix (rung 2a, the free-footprint mint) synthesizes the "
                          "LAND CHAIN too: interior L verts push LAND units landward (sin^2 "
                          "eased, cap ends pinned) conforming to the berm surface, the berm "
                          "is CLIPPED at the new chain (pure real bytes, the beach_slide "
                          "machinery) and the widened band takes the strip. Gated by the "
                          "ribbon/slope/swash envelopes, the assembly-boundary gate, T-vertex, "
                          "per-tri re-decode, and (with LAND) the clip ledgers (partition/"
                          "coverage/steep-face/object-anchor/drop-don't-drag). Rung-1 class: "
                          "the block's single x-monotone column beach.")
    wtp.add_argument("--virgin-mint", default=None,
                     metavar="X0,Z0:X1,Z1[:WIDTH[:SWASH]][:pins=PX,PY]",
                     help="BEACH-MINT rung 3 -- THE VIRGIN-SHORE MINT: author a NEW "
                          "beach on a bare grass coast (no donor beach to pin to). "
                          "X0,Z0 / X1,Z1 = world anchors for the two cap pinch points "
                          "on the shoreline (snapped to a real shore vert within 0.6u, "
                          "else inserted on the shore edge). The chains synthesize from "
                          "the grass edge (S rides the real shoreline with the prior "
                          "height profile; L cuts landward into the topo-0 berm at the "
                          "band WIDTH target, default 2.4; W pushes SWASH seaward into "
                          "the wash, default 4.6, snapping to a real convergence vert "
                          "when in reach). The berm clips at the footprint, touched "
                          "water tiles drop and their outside fragments re-emit with "
                          "continued uvs, sand+foam emit by the proven language walks, "
                          "and the RING RE-BANDS where the mint leaves sea3 fronting "
                          "wash (conforming quads included -- the deformed-tile rect "
                          "law). Gated by the union crack gate, T-vertex, the lattice "
                          "adjacency + shade-agreement laws, per-tri re-decodes, the "
                          "band/slope/swash/column envelopes, and THE GRASS-TONGUE LAW "
                          "(4.06u to every existing beach). :pins=PX,PY byte-reads the "
                          "foam family + sand run/cap pins from a beach-bearing "
                          "reference block (REQUIRED when the mint block has no beach "
                          "of its own -- the island-B pattern). Works on regions too: "
                          "the mint block derives from the spec coords (canonical "
                          "floor(x/64), floor(-z/64)) and composes with --bank-lower "
                          "(the mint computes on the POST-bank geometry).")
    wtp.add_argument("--bank-lower", default=None,
                     metavar="CX,CZ:RADIUS[:SLOPE[:CAP]][:along=AX,AZ/BX,BZ]",
                     help="THE BANK RESHAPE (the virgin mint's site preparation): sink a "
                          "mesa/cliff-top bank into a beach-capable profile -- every "
                          "terrain vert within RADIUS of CX,CZ sinks toward "
                          "min(SLOPE*d_shore, CAP) (defaults 0.55/2.2), shore- and "
                          "frame-welded verts pinned, plateau falloff at the rim. "
                          ":along=AX,AZ/BX,BZ runs the falloff from the beach CHORD "
                          "instead of the point (THE CORRIDOR LAW -- on a small islet a "
                          "radial reach flattens the far rim). Touched topo-58 walls "
                          "re-pin V per column under THE LIP ANCHOR (crest keeps the "
                          "painted lip row; the base crops at the column's own density; "
                          "the V-IN-BAND gate polices the byte-derived strip band). "
                          "Composes with --virgin-mint (bank first, mint on the post-"
                          "bank geometry); the bank block derives from CX,CZ.")
    wtp.add_argument("--band-convert", default=None, metavar="CX,CZ:PART",
                     help="THE ONE-CELL BAND-CONVERSION (rung 3's probe -- the first FRESH "
                          "deformed-tile emission): re-band one LATTICE water cell of a "
                          "non-strip band (sea3/sea4) into strip band PART (sea1/sea5) and "
                          "re-emit every affected strip neighbour under its new deep-edge-set "
                          "via THE DEFORMED-TILE RECT LAW (rects CHOSEN from the learned Wang "
                          "table for the new shade field, block-observed exact floats -- the "
                          "virgin mint's ring re-band in miniature). CX,CZ = a donor-frame 4u "
                          "cell index. Geometry/normals/IDALL transport verbatim; gated by the "
                          "shade-agreement law (pre null test + post), adjacency law, re-decode "
                          "and geometry-identity.")
    wtp.add_argument("--cap-rebuild", action="store_true",
                     help="the END-CAP identity rebuild (the cap-law completeness proof): every "
                          "lawful foam end cap and sand row-B cap re-emits through the learned "
                          "cap laws with the donor's own slot + snaps, byte-equality gated -- "
                          "caps have zero lawful freedom beyond their texel snaps, so the "
                          "round-trip IS the proof (the slot-flip experiment was falsified "
                          "in-game: the TR curl-out graphic never fades, so slots transport). "
                          "Spit/river-mouth (BR), subdivided and frame-split caps stay verbatim.")
    wtp.add_argument("--sand-rebuild", action="store_true",
                     help="the SAND-BAND identity rebuild (the beach's third discrete language, "
                          "byte-learned map-wide): drop every closed decodable topo-31 run column "
                          "group and re-derive its u's from the learned two-rect strip, FLIPPING "
                          "each group onto the other rect (lawful by the one-shade law -- the "
                          "strongest generative statement a two-rect language allows; orientation/"
                          "folds/subdivision transport through the 1-D u-affine; v/positions "
                          "byte-unchanged). Caps (row B), the conforming bend tier and frame-split "
                          "columns stay verbatim. Every emitted column self-checks by re-decode.")
    wtp.add_argument("--in-place", action="store_true",
                     help="morph the donor's own REAL cell in place (--cell == --donor): apply the "
                          "given morph flags to the cell's real parts and deploy loose per-part "
                          "overrides keyed to that same cell (the s34 override loads for any streamed "
                          "block). The route for shores no single-cell transplant can carry -- every "
                          "nose beach's landmass is a coastline fragment. No census/land-fit (the cell "
                          "keeps its real neighbours; morphs pin block-frame verts). Revert = delete "
                          "the deployed files.")
    wtp.add_argument("--beach-rebuild", default=None, metavar="X0,Z0:X1,Z1",
                     help="STRUCTURAL beach, identity mode (in-game proven ~indistinguishable): drop the "
                          "window's shore ladder (foam run tiles / sea2 wash / sea1 Wang ring) and re-derive "
                          "it from pure language over the SAME verts -- the generative proof that reshaping "
                          "is a controlled delta. Endpoints = two waterline verts (donor frame).")
    wtp.add_argument("--beach-reshape", default=None, metavar="X0,Z0:X1,Z1:D",
                     help="the STRUCTURAL beach SHAPE morph: slide the beach ASSEMBLY (sand seam + waterline "
                          "together -- THE HUG LAW: within-beach swash width is near-constant, the foam line "
                          "rides the sand edge) by a sin^2 profile of depth D (+ = seaward) and RE-LAY the "
                          "water ladder over the new footprint, strain-free: foam run tiles over the moved "
                          "chains, the wash re-laid with a width-driven lattice boundary, the sea1/sea3 "
                          "patchwork transported by a per-column pullback with the EDGE-SHADE FIELD re-solved "
                          "(transported shades preferred, flips minimized over the learned table). The berm "
                          "terrain DRAGS (the land-drag envelope caps depth at ~2.5). THE SHAPE-CLASS LAW "
                          "gates direction: a beach may deepen its own curvature (a pocket deepens landward, "
                          "a headland-nose grows seaward) but never cross its chord toward the opposite "
                          "class -- the coast behind it sets the class.")
    wtp.add_argument("--beach-slide", default=None, metavar="X0,Z0:X1,Z1:D",
                     help="the FULL-ASSEMBLY beach slide -- true beach movement past the +-2.5u drag cap: "
                          "the LAND CHAIN rides the same sin^2 profile as the sand seam + waterline (the "
                          "hug law completed), the sand band translates VERBATIM (width/texel density/chain "
                          "pins preserved by construction -- the sand census proved a widened band has no "
                          "lawful fill: one v-rect stretches 1.8-6.6u only, row B is terminal-only), the "
                          "berm strip it moves into is CLIPPED at the translated chain (pure bytes), the "
                          "band y re-conforms (slope gate 0.10-0.58), and the vacated shore re-lays through "
                          "the beach-reshape water machinery. LANDWARD ONLY v1 (D < 0, pocket deepening).")
    wtp.add_argument("--shift", default="auto",
                     help="in-cell shift 'dx,dz' in units, each a multiple of 4, clamped to what the donor's "
                          "neighbour strips can refill; default auto = centre the land in the cell")
    wtp.add_argument("--strips", default="auto",
                     help="which neighbour edge strips to carry: 'auto' = only where the donor's own land "
                          "reaches that border (the island's tongue -- neighbour blocks are FOREIGN content "
                          "otherwise), 'all', 'none', or explicit directions like 'E,N'")
    wtp.add_argument("--extra", type=float, default=8.0,
                     help="neighbour edge-strip width to carry, in units (default 8 = the proven island tongue)")
    wtp.add_argument("--land-margin", type=float, default=2.0,
                     help="land must sit this far inside the cell frame (island default 2; pass 0 for a donor "
                          "whose land legitimately reaches the block border)")
    wtp.add_argument("--samples", type=int, default=24,
                     help="placement-census grid resolution (default 24 = 576 ground probes)")
    wtp.add_argument("--disc", type=int, default=1, help="world disc (default 1)")
    wtp.add_argument("--dry-run", action="store_true", help="build + run every gate, write nothing")
    wtp.add_argument("--skip-mirror", action="store_true",
                     help="don't auto-mirror the written override(s) to Disc4 (THE DISC-4 GAP; default: mirror)")
    wtp.set_defaults(func=_cmd_world_transplant)

    wms = sub.add_parser("world-morphs",
                         help="the COAST WINDOW SCANNER: walk a real block's beach waterline runs + cliff "
                              "base runs and print the lawful morph windows with per-verb depth CEILINGS -- "
                              "probed by calling the real builders down a depth ladder (the offline gates ARE "
                              "the law) and certified via an in-place dry-run, so every line deploys as "
                              "printed with world-transplant --in-place. A verb with no lawful rung reports "
                              "its binding refusal instead.")
    wms.add_argument("--block", default=None, metavar="BX,BY",
                     help="scan one block (grid 24x20)")
    wms.add_argument("--all", action="store_true",
                     help="scan the whole map's coastal blocks (minutes; prints progress)")
    wms.add_argument("--verbs", default=None,
                     help="comma list to probe (default all): beach-bump,beach-reshape,"
                          "beach-slide,cliff-bump,cliff-headland,cliff-bay")
    wms.add_argument("--mod-folder", default=argparse.SUPPRESS,
                     help="printed into the ready-to-run deploy lines (display only; default FF9CustomMap)")
    wms.add_argument("--disc", type=int, default=1, help="world disc (default 1)")
    wms.set_defaults(func=_cmd_world_morphs)

    wis = sub.add_parser("world-island",
                         help="synthesize a fully-CUSTOM cliff island/landmass on open ocean: organic coastline + "
                              "faithful rock wall + the real grass language (mains + verbatim meadow stamps), "
                              "offline-gated (geometry + UV + slope envelope + engine-placement census). The "
                              "interior is FLAT at --height by default; --relief adds gentle inland rolling "
                              "undulation (local prominence still = world-hill/world-forest/world-mountain). "
                              "Needs the custom engine; re-enter the world.")
    wis.add_argument("--mod-folder", required=True, help="the FolderNames mod folder to deploy into")
    wis.add_argument("--target-disc", type=int, default=None,
                     help="deploy the produced overrides into THIS disc's namespace instead of --disc's. --disc "
                          "stays the READ disc (which stock tree real bytes are borrowed from; only 1 and 4 exist). "
                          "Use 9 for a Path D synthetic world, whose engine-side override namespace (s74) is "
                          "deliberately disjoint from the real trees.")
    wis.add_argument("--all-sea-target", action="store_true",
                     help="the target grid is ALL SEA (a blank Path D world), so skip THE OPEN-OCEAN TARGET LAW, "
                          "which probes the unrelated real disc. Do NOT pass this for an s75 CLONE target -- a "
                          "clone carries the stock IsSea pattern, so the law is correct there and must keep running.")
    _wtgt = wis.add_mutually_exclusive_group(required=True)
    _wtgt.add_argument("--cell", metavar="BX,BY", help="centre the island on ocean block BX,BY (grid 24x20)")
    _wtgt.add_argument("--center", metavar="WX,WZ",
                       help="centre at WORLD coords (x 0..1535, z 0..-1279); a large radius spans blocks and "
                            "splits per-block automatically (a multi-cell landmass)")
    wis.add_argument("--radius", type=float, default=24.0,
                     help="base coastline radius in units (default 24 ~ one block; bigger spans blocks)")
    wis.add_argument("--seed", type=float, default=None,
                     help="island shape seed (deterministic; default derives from the centre)")
    wis.add_argument("--lobes", type=int, default=1,
                     help="1 = a perturbed-circle island (default); 2-3 = an ASYMMETRIC multi-lobe landmass "
                          "(elongation, waists, natural corners -- gated against the measured FF9 coastline language)")
    wis.add_argument("--height", type=float, default=3.2,
                     help="interior land height (default 3.2 = the real coastal-cliff interior median)")
    wis.add_argument("--rim-run", type=float, default=1.0,
                     help="cliff wall RUN in units (default 1.0 -> ~73deg at height 3.2); smaller = steeper")
    wis.add_argument("--patches", type=int, default=2,
                     help="max meadow patches (verbatim stamps; only perfectly-fitting ones place; default 2)")
    wis.add_argument("--flat", action="store_true",
                     help="skip the verbatim meadow stamps (no install data needed)")
    wis.add_argument("--relief", action="store_true",
                     help="OPT-IN rolling relief: gentle inland undulation from a deterministic WORLD-XZ "
                          "value-noise field (calibrated to stock lowland: slope p99 ~11 deg, wavelength "
                          "~20u), faded to 0 at the shore so the wall-top rim stays welded. Default OFF "
                          "(flat = byte-identity with prior mints). Mutually exclusive with "
                          "world-hill/forest/mountain on the same island (the 2.4u envelope gate is the backstop).")
    wis.add_argument("--relief-amp", type=float, default=1.3,
                     help="relief base amplitude in units (default 1.3 = the calibrated grass default; "
                          "GROUNDS scales it per family, e.g. desert ~1.6x). Only applies with --relief.")
    wis.add_argument("--relief-seed", type=float, default=None,
                     help="relief field seed (deterministic; default derives from the centre)")
    wis.add_argument("--ground", choices=_ground_choices(), default="grass",
                     help="walkable ground family (byte-measured TRANSLATION LAWS): grass (default), "
                          "desert, snow, canyon are island-complete fills; scrub/brush/dunes are "
                          "stock seam/slope/interior vocabularies (mintable, but a whole island of "
                          "them reads off-language); meadow patches are grass-only")
    wis.add_argument("--beach", default=None, metavar="B0,B1[:WIDTH[:SWASH]]",
                     help="THE LADDER MINT: replace the cliff wall along the outline arc between "
                          "bearings B0..B1 (degrees CCW, east=0, south=270) with the measured beach "
                          "profile (berm -> sand band -> foam ribbon) and mint its water ladder "
                          "(wash collar -> sea1 ring -> sea5 ring, the sea4 plane cut back) -- "
                          "adjacency lawful by construction, the arc ends pinch against the "
                          "full-height flanking cliffs. v1: single-block, grass+desert families. "
                          "WIDTH = the sand band (default 2.4), SWASH = the foam ribbon (3.8-4.6).")
    wis.add_argument("--beach-pins", default=None, metavar="BX,BY",
                     help="the beach language reference block (sand v pins, foam family, strip float "
                          "dialect, AND the beach block's divert donor). Default per family: grass "
                          "(7,17), desert (20,5).")
    wis.add_argument("--disc", type=int, default=1, help="world disc (default 1)")
    wis.add_argument("--dry-run", action="store_true", help="build + run every gate, write nothing")
    wis.add_argument("--skip-mirror", action="store_true",
                     help="don't auto-mirror the written override(s) to Disc4 (THE DISC-4 GAP; default: mirror)")
    wis.set_defaults(func=_cmd_world_island)

    wfo = sub.add_parser("world-forest",
                         help="carry a REAL canopy blob (verbatim topo-37 forest) onto a DEPLOYED kit island -- "
                              "the in-game-proven canopy-carry recipe (carve a lattice hole, seat the blob, zip "
                              "a grass annulus with byte-decoded mains UVs). Gated by the CANOPY STEP LAW + a "
                              "perimeter walk-in simulation (takes a few minutes) + the placement census. "
                              "Needs the custom engine; re-enter the world.")
    wfo.add_argument("--mod-folder", required=True, help="the FolderNames mod folder holding the island")
    _ftg = wfo.add_mutually_exclusive_group(required=True)
    _ftg.add_argument("--center", metavar="WX,WZ", help="EXACT blob centre in world coords (gated, no scan)")
    _ftg.add_argument("--near", metavar="WX,WZ",
                      help="scan a ~80u window around this point for the best lawful plain-grass placement")
    wfo.add_argument("--donor", default="15,15", metavar="BX,BY",
                     help="real block whose topo-37 canopy blob to carry (default 15,15 = the proven "
                          "grass-bounded donor; a multi-blob or non-simple-rim donor refuses)")
    wfo.add_argument("--reach", type=float, default=96.0,
                     help="deployed-block load window around the point in units (default 96)")
    wfo.add_argument("--disc", type=int, default=1, help="world disc (default 1)")
    wfo.add_argument("--dry-run", action="store_true", help="build + run every gate, write nothing")
    wfo.add_argument("--skip-mirror", action="store_true",
                     help="don't auto-mirror the written override(s) to Disc4 (THE DISC-4 GAP; default: mirror)")
    wfo.set_defaults(func=_cmd_world_forest)

    whl = sub.add_parser("world-hill",
                         help="raise a raised-cosine GRASS HILL on a DEPLOYED kit island by pure-Y displacement "
                              "of the deployed bytes (mains UVs are XZ-linear, so every tile stays lawful) -- "
                              "the in-game-proven grass-hill language (slope p99 28.6 deg, lowland-band peak "
                              "cap, local normal re-smooth). Needs the custom engine; re-enter the world.")
    whl.add_argument("--mod-folder", required=True, help="the FolderNames mod folder holding the island")
    _htg = whl.add_mutually_exclusive_group(required=True)
    _htg.add_argument("--center", metavar="WX,WZ", help="EXACT hill centre in world coords (gated, no scan)")
    _htg.add_argument("--near", metavar="WX,WZ",
                      help="scan a ~112u window around this point for the best lawful pure-mains placement")
    whl.add_argument("--height", type=float, default=4.2,
                     help="prominence in units (default 4.2; the real language is 3.5-5.2)")
    whl.add_argument("--radius", type=float, default=18.0,
                     help="footprint radius in units (default 18; the real language is 20-26u diameter runs)")
    whl.add_argument("--disc", type=int, default=1, help="world disc (default 1)")
    whl.add_argument("--dry-run", action="store_true", help="build + run every gate, write nothing")
    whl.add_argument("--skip-mirror", action="store_true",
                     help="don't auto-mirror the written override(s) to Disc4 (THE DISC-4 GAP; default: mirror)")
    whl.set_defaults(func=_cmd_world_hill)

    wmt = sub.add_parser("world-mountain",
                         help="carry a REAL rock massif (verbatim topo-49/7/62 geometry+UV+normals, incl. "
                              "Object-aperture plugs) onto a DEPLOYED kit island -- the in-game-proven Uaho "
                              "carry (rock stays RIGID, the grass apron rises to meet it; hole carve + DP-zip "
                              "annulus). Gated by ROCK-RIGID + the weld-safe lift + the zip envelope + "
                              "placement probes + the census. Needs the custom engine; re-enter the world.")
    wmt.add_argument("--mod-folder", required=True, help="the FolderNames mod folder holding the island")
    _mtg = wmt.add_mutually_exclusive_group(required=True)
    _mtg.add_argument("--center", metavar="WX,WZ",
                      help="EXACT massif centre in world coords, rotation 0 (gated, no scan)")
    _mtg.add_argument("--near", metavar="WX,WZ",
                      help="scan a ~20u window around this point for the best lawful plain-grass placement "
                           "(exact 90-deg rotations as fallbacks)")
    wmt.add_argument("--donor", default="0,0", metavar="BX[,-BX1],BY[-BY1]",
                     help="real block(s) whose rock massif to carry: one block (default 0,0 = Uaho, alcove + "
                          "aperture-plug anatomy studied) or a rect for a massif that straddles a border "
                          "(10,5-6 = the crag; the target sizes itself to a multi-block span automatically). "
                          "A new donor needs its own anatomy pass first -- see "
                          "studies/overworld-topography/README.md.")
    wmt.add_argument("--reach", type=float, default=96.0,
                     help="deployed-block load window around the point in units (default 96)")
    wmt.add_argument("--ground", choices=_ground_choices(), default="grass",
                     help="the bench island's ground family: the zip annulus + plain-ground checks speak "
                          "it (match the island's world-island --ground)")
    wmt.add_argument("--disc", type=int, default=1, help="world disc (default 1)")
    wmt.add_argument("--dry-run", action="store_true", help="build + run every gate, write nothing")
    wmt.add_argument("--skip-mirror", action="store_true",
                     help="don't auto-mirror the written override(s) to Disc4 (THE DISC-4 GAP; default: mirror)")
    wmt.set_defaults(func=_cmd_world_mountain)

    wmi = sub.add_parser("world-mirror",
                         help="mirror a mod folder's Disc1 WorldMap overrides into the Disc4 tree -- the "
                              "overworld ships TWO asset trees (disc1 serves discs 1-3; disc4 is its own) and "
                              "every s34 lookup keys on the engine's currentDisc, so un-mirrored custom land "
                              "VANISHES on disc 4. Copies every Block override + Donor.txt (per-cell gated: the "
                              "destination's real cell must be ocean or byte-identical) and PINS un-overridden "
                              "donor-prefab free-ride parts (falls/rivers/objects) as explicit source-disc-byte "
                              "overrides. Run after any custom-ocean world deploy. RELAUNCH to apply.")
    wmi.add_argument("--mod-folder", required=True, help="the FolderNames mod folder to mirror")
    wmi.add_argument("--src-disc", type=int, default=1, help="source disc tree (default 1)")
    wmi.add_argument("--dst-disc", type=int, default=4, help="destination disc tree (default 4)")
    wmi.add_argument("--dry-run", action="store_true", help="report the plan, write nothing")
    wmi.set_defaults(func=_cmd_world_mirror)

    wwt = sub.add_parser("world-water",
                         help="synthesize custom GRADED open-ocean water (shallow->deep) on sea cells -- the faithful "
                              "marching-band synthesizer (Sea3/Sea5/Sea4, byte-proven UVs). Needs the custom engine; relaunch.")
    wwt.add_argument("--mod-folder", required=True, help="the FolderNames mod folder to deploy into")
    wwt.add_argument("--cells", required=True,
                     help="target ocean cells: 'x,y;x,y' (e.g. '3,17') or a range 'x0-x1,y0-y1' (a contiguous patch "
                          "stays seamless). Grid is 24x20; reach a lone cell via the debug menu (~)->World->Teleport.")
    wwt.add_argument("--donor", default="15,4",
                     help="a real DEEP-OCEAN donor block 'dx,dy' whose base sea prefab backs the cell (default 15,4)")
    wwt.add_argument("--deep", choices=["N", "S", "E", "W"], default=None,
                     help="OMIT for faithful open ocean (mostly deep, ~94%% Sea4 like real FF9 open water); give a "
                          "direction for a graded shallow->deep RAMP toward it (a coast/bay)")
    wwt.add_argument("--shallows", type=float, default=0.05,
                     help="open-ocean shallow-patch fraction (default 0.05 ~ real; 0 = uniform deep Sea4). Ignored with --deep.")
    wwt.add_argument("--threshold", type=float, default=1.0, help="depth at the shallow|deep seam (default 1.0)")
    wwt.add_argument("--span", type=float, default=2.0, help="depth range shallow->deep across the region (default 2.0)")
    wwt.add_argument("--noise", type=float, default=0.5, help="organic wobble on the shallow|deep contour (default 0.5)")
    wwt.add_argument("--height", type=float, default=-0.1,
                     help="ocean walkmesh Y (default -0.1, just below the Y=0 surface so a boat floats on top; a bigger "
                          "negative sinks the vehicle, 0 z-fights the water)")
    _wref = wwt.add_mutually_exclusive_group()
    _wref.add_argument("--verbatim", nargs="?", const="8,4", metavar="BX,BY",
                       help="A/B REFERENCE: instead of synthesizing, deploy REAL ocean block BX,BY verbatim (default 8,4, "
                            "the byte-proven block) onto --cells -- the north-star to compare world-water against at the same spot")
    _wref.add_argument("--reproduce", nargs="?", const="8,4", metavar="BX,BY",
                       help="FIDELITY A/B: reproduce REAL block BX,BY's shallow/deep LAYOUT (default 8,4) with SYNTHESIZED "
                            "tiles -- deploy beside --verbatim of the same block; they should look alike (the 17/17 shape-match, in-game)")
    wwt.add_argument("--seed", type=int, default=0, help="anti-tiling PRNG seed (deterministic; vary for a new shuffle)")
    wwt.add_argument("--disc", type=int, default=1, help="world disc (default 1)")
    wwt.add_argument("--dry-run", action="store_true", help="report the cells it would fill, write nothing")
    wwt.add_argument("--skip-mirror", action="store_true",
                     help="don't auto-mirror the written override(s) to Disc4 (THE DISC-4 GAP; default: mirror)")
    wwt.set_defaults(func=_cmd_world_water)

    wat = sub.add_parser("world-atlas-add-tile",
                         help="T3: paint a NEW tile into a FREE atlas region + deploy the reskin; prints the UV rect "
                              "to stamp on custom geometry via `world-mesh-build --tile-uv`")
    wat.add_argument("png", nargs="?", help="a tile PNG to add (omit for a magenta test pattern)")
    wat.add_argument("--part", choices=["terrain", "object"], default="object")
    wat.add_argument("--size", type=int, default=48, help="tile size in atlas px (default 48)")
    wat.add_argument("--mod-folder", required=True, help="the FolderNames mod folder to deploy into")
    wat.set_defaults(func=_cmd_world_atlas_add_tile)

    wmt = sub.add_parser("world-mesh-trim",
                         help="auto-remove faces from a building OBJ: --floor drops the low flat base courtyard-floor/"
                              "apron that reads as a dirt patch under the overworld camera (keeps walls/towers/roofs)")
    wmt.add_argument("obj", help="the input .obj (e.g. a world-mesh-export of a castle)")
    wmt.add_argument("--out", required=True, help="output path for the trimmed .obj")
    wmt.add_argument("--floor", action="store_true",
                     help="drop the low up-facing base floor/apron faces (the flat 'dirt mound' look)")
    wmt.add_argument("--base-height", type=float, default=6.0,
                     help="how far above the mesh's lowest Y still counts as 'floor' (default 6)")
    wmt.add_argument("--up-threshold", type=float, default=0.5,
                     help="min upward normal component (0-1) for a face to count as floor (default 0.5)")
    wmt.set_defaults(func=_cmd_world_mesh_trim)

    wen = sub.add_parser("world-entrance",
                         help="author a WHOLE custom overworld entrance in one shot: the trigger function (into "
                              "every world dispatcher that carries the destination case, all 7 langs) + the event "
                              "tiles + an optional modelled building. Needs the WorldMeshOverride engine patch.")
    wen.add_argument("--cell", type=int, nargs=2, metavar=("X", "Z"),
                     help="the overworld CELL to place the entrance (32u cells; see the debug-menu World "
                          "tab / world-locate). Required except with --extend-nameplate-band")
    wen.add_argument("--field", type=int,
                     help="destination base field id (resolved to a dispatch case; e.g. --field 300 = Ice Cavern). "
                          "A fork/journey field_remap/s28 then sends it on to your fork")
    wen.add_argument("--case", type=int,
                     help="destination dispatch case directly (== Map.Byte[39]; the AREA switch case). Alternative "
                          "to --field for power users")
    wen.add_argument("--field-direct", type=int, metavar="ID",
                     help="a CUSTOM destination field id (a registered kit field, e.g. 6500): the trigger func "
                          "warps Field(ID) directly behind the template's own vehicle/state gate -- no dispatcher "
                          "case is used or touched (the AREA switch only carries real base fields), so custom "
                          "entrances compose additively. Fires in every free-roam world state. The destination "
                          "must be DEPLOYED (a registered-but-assetless id crashes on warp)")
    wen.add_argument("--event", type=int, choices=[1, 2, 3], default=1,
                     help="the tile trigger id (default 1) -- must match the tag's low bits; the base game uses 1")
    wen.add_argument("--disc", type=int, default=1, help="world disc (default 1)")
    wen.add_argument("--lod", default="0_1", help="LOD dir (default 0_1, the walkmesh form)")
    wen.add_argument("--mod-folder", required=True,
                     help="the stacked FolderNames mod folder to deploy into (e.g. FF9CustomMap)")
    wen.add_argument("--trigger-at", type=float, nargs=2, metavar=("WX", "WZ"),
                     help="world XZ centre of the event-tile cluster (default: the cell centre). Keep it INSIDE the "
                          "cell -- tiles that spill into a neighbour pack a different tag and fire nothing")
    wen.add_argument("--trigger-radius", type=float, default=14.0,
                     help="event-tile cluster radius in world units (default 14; the cell is 32u wide)")
    wen.add_argument("--no-tile-area", action="store_true",
                     help="do NOT stamp the cosmetic tile AREA (dispatch reads Byte[39], not the tile area; "
                          "world-locate reads the dispatcher's trigger table, so the stamp is pure bookkeeping)")
    wen.add_argument("--trigger-only", action="store_true",
                     help="refresh ONLY the dispatcher trigger functions (.eb) -- leave the deployed terrain / "
                          "event tiles / building untouched. The re-deploy mode for picking up a kit upgrade to "
                          "the trigger body (e.g. the zone-in fade) on an already-authored entrance")
    wen.add_argument("--action-prompt", action="store_true",
                     help="FAITHFUL \"!\" entrance (--field-direct only): the tile raises the \"!\" bubble and warps "
                          "only when you press Confirm while standing on it -- the way real FF9 towns enter (a "
                          "B_KEYON(Confirm) gate, byte-copied from the real dispatcher). Default (off) = auto-warp "
                          "the instant you step on the tile")
    wen.add_argument("--nameplate", action="store_true",
                     help="(with --action-prompt) also summon the NATIVE overworld entrance HUD -- the location "
                          "nameplate + the \"Enter with [X]\" dialog -- via the real dispatcher handshake, so the "
                          "windows show + auto-hide natively (the warp still runs through our Confirm gate)")
    wen.add_argument("--nameplate-name", metavar="NAME",
                     help="the NATIVE-FLOW nameplate SURGERY (--field-direct only; supersedes --action-prompt/"
                          "--nameplate): the whole entrance runs the game's REAL native flow, and the approach "
                          "nameplate shows this CUSTOM location name (not \"?\", not a borrowed town). Repoints a "
                          "DEAD high AREA-switch case (--nameplate-case, default 53) to [set explored bit]+Field(ID) "
                          "in every carrying dispatcher/lang, and registers NAME into world text block 68. The name "
                          "shows \"?\" until first visit then the name -- faithful town behaviour. RELAUNCH to apply")
    wen.add_argument("--nameplate-case", type=int, default=53, metavar="N",
                     help="the nameplate case. 2-60: the SURGERY lane -- a DEAD AREA-switch case is repointed "
                          "(default 53 -> the \"???\" placeholder slot; the tool verifies + refuses a live case). "
                          "!! Switch-dead is NOT enough: case 52 is the quicksand's hardcoded main-loop "
                          "Battle(0,144) branch (the only such case; census 2026-07-26) and 43/54-59 carry real "
                          "labels -- 53 is the ONLY clean surgery slot. 61-64: the VIRGIN band -- past the stock "
                          "table and switch entirely, no stock bytes touched (the trigger self-summons the plate, "
                          "block-68 is extended); the robust lane for additional named entrances")
    # optional building (folds world-mesh-build in)
    wen.add_argument("--building", help="an OBJ modelled/exported in Blender to place + seat as the cell's structure")
    wen.add_argument("--building-at", type=float, nargs=2, metavar=("WX", "WZ"),
                     help="world XZ to drop the building's centre (default: the cell centre)")
    wen.add_argument("--no-seat", action="store_true",
                     help="don't auto-drop the building onto the terrain surface (place at its modelled height)")
    wen.add_argument("--replace-town", action="store_true",
                     help="REPLACE the block's stock Object structures instead of merging the building alongside them "
                          "(default: keep e.g. an existing town)")
    wen.add_argument("--topograph", type=int, default=59,
                     help="topograph stamped on the building's tiles (default 59 = impassable structure)")
    wen.add_argument("--building-idall", type=int, metavar="N",
                     help="stamp this RAW IDALL on the building mesh instead of encoding --topograph. ⚠ NEEDED to "
                          "keep the building RENDER-ONLY on a cell whose block prefab already HAS an Object "
                          "component (a reclaimed/Donor.txt cell, or a real town block): there the engine feeds the "
                          "Object override to AddWalkMeshForm1, so the model becomes collision and its culled walls "
                          "+ buried base become INVISIBLE COLLISION. Pass 4078 (the WMPhysics skip id) to make it "
                          "genuinely render-only; footprint collision still comes from the topo-59 terrain hull. On "
                          "a BARE block RegisterBareObjectOverride is already render-only and this is unnecessary")
    wen.add_argument("--texture", action="store_true",
                     help="stamp real atlas tiles onto the building's UV-less faces from the learned palette (same "
                          "as world-mesh-build --texture; a Blender OBJ without UVs otherwise renders [0,0] white). "
                          "Keep faces near real-tile scale (~1-2u panels) -- the stamp doesn't rescale, so a big "
                          "face smears one small tile across itself")
    wen.add_argument("--tile", metavar="TOPO:VARIANT",
                     help="force ONE specific atlas tile on the building's new faces (e.g. 52:0 = a castle wall); "
                          "pick from `world-atlas-catalog`. Implies --texture")
    wen.add_argument("--tile-uv", metavar="Umin,Vmin,Umax,Vmax",
                     help="stamp a CUSTOM UV rect on the building's new faces (a tile painted via "
                          "`world-atlas-add-tile`)")
    wen.add_argument("--hollow-building", action="store_true",
                     help="don't block the building's footprint -- by default the TERRAIN under the building is made "
                          "impassable so you stop at its edge and can't wander into a hollow 3D model (courtyards/gaps) "
                          "and get boxed. Pass this to leave the footprint walkable (a decorative walk-through prop).")
    wen.add_argument("--flatten-pad", type=float, metavar="RADIUS",
                     help="[steep ground only] flatten a pad of this radius under the building to the seat height. "
                          "Auto-capped to the building footprint so the flat ground stays UNDER the impassable "
                          "structure (a wider pad leaves walkable edge-steps you get stuck on). Usually unneeded -- "
                          "seating alone handles most spots; the building skirt hides a small float.")
    wen.add_argument("--extend-nameplate-band", action="store_true",
                     help="standalone: deploy THE EXTENDED NAMEPLATE BAND (the func-0xB range-arm "
                          "splice) into every free-roam dispatcher of --mod-folder, enabling virgin "
                          "nameplate cases 65-155 (a virgin-case deploy past 64 also runs this "
                          "automatically). Idempotent; stock cases compute byte-equivalently; "
                          "explored bits live in the kit-reserved words at gEventGlobal bytes "
                          "2006-2017. Only --mod-folder (and optionally --dry-run) apply")
    wen.add_argument("--fresh", action="store_true",
                     help="re-read this block's terrain/object from PRISTINE p0data, ignoring any already-deployed "
                          "override -- use when RE-doing a block (a flatten pad or a kept building otherwise COMPOUNDS "
                          "on each re-run). Drops other entrances' event tiles in the same block.")
    wen.add_argument("--dry-run", action="store_true",
                     help="compute + print the full plan (dispatchers, case, tiles, building) without writing anything")
    wen.add_argument("--skip-mirror", action="store_true",
                     help="don't auto-mirror the written terrain/building override(s) to Disc4 (THE DISC-4 GAP; "
                          "default: mirror)")
    wen.set_defaults(func=_cmd_world_entrance)

    wfu = sub.add_parser("world-fuse",
                         help="validate + deploy a multi-placement transplant LAYOUT (the cross-donor FUSE): "
                              "several verbatim landmasses in adjacent target rects, every shared border "
                              "certified open water row-by-row. Needs the WorldMeshOverride engine patch.")
    wfu.add_argument("layout", help="a .toml of [[placement]] tables: cell=[X,Y] donor=[DX,DY] size=[NX,NY] "
                                    "(optional rot / shift / land_margin / strips / grow_cut / grow_cut_z)")
    wfu.add_argument("--mod-folder", required=True, help="the stacked FolderNames mod folder to deploy into")
    wfu.add_argument("--disc", type=int, default=1, help="world disc (default 1)")
    wfu.add_argument("--allow-overwrite", action="store_true",
                     help="deploy even where target cells already have override files on disk (re-deploying "
                          "the same layout is the normal iteration flow; without this flag a collision refuses "
                          "so an unrelated island can't be silently clobbered)")
    wfu.add_argument("--dry-run", action="store_true",
                     help="validate the whole layout (placement gates + rect overlap + fuse borders + "
                          "collisions) and print the verdicts without writing anything")
    wfu.add_argument("--skip-mirror", action="store_true",
                     help="don't auto-mirror the deployed layout's overrides to Disc4 (THE DISC-4 GAP; default: mirror)")
    wfu.set_defaults(func=_cmd_world_fuse)

    wev = sub.add_parser("world-environment",
                         help="author overworld WEATHER / effects: emit Memoria's Environment.txt (force mist on/off, "
                              "add rain / weather-light zones, toggle world effects, force place alternate-forms) into "
                              "a mod folder from a [world_environment] toml. No DLL (stock-Memoria seam); relaunch to apply.")
    wev.add_argument("config", help="a .toml with a [world_environment] table: mist/disc4 = true|false|<NCalc>, plus "
                                    "[[world_environment.rain]] / [[..light]] / [[..effect]] / [[..place]] lists "
                                    "(a bare doc with those keys also works)")
    wev.add_argument("--mod-folder", required=True,
                     help="the FolderNames mod folder to write into (e.g. FF9CustomMap); file -> "
                          "<mod>/StreamingAssets/Data/World/Environment.txt")
    wev.add_argument("--dry-run", action="store_true", help="print the Environment.txt it would write, write nothing")
    wev.set_defaults(func=_cmd_world_environment)

    wmm = sub.add_parser("world-minimap",
                         help="draw a mod folder's deployed overworld LAND onto the in-game all-world map "
                              "image (the mod-overridable world_map_full_all.png) -- the custom continent "
                              "appears on the map. Data-derived: the engine's own 1536x1280 projection onto "
                              "the image's detected art rect, colours sampled from how the map draws real "
                              "islets. No DLL; relaunch to apply. NOTE: the override must sit ABOVE any "
                              "folder shipping its own map PNG (e.g. MoguriMain) in Memoria.ini FolderNames "
                              "AND Priorities (edit BOTH, same order -- the launcher rewrites FolderNames "
                              "from Priorities at every Play click).")
    wmm.add_argument("--mod-folder", required=True,
                     help="the FolderNames mod folder whose WorldMap terrain to draw + where the PNG lands")
    wmm.add_argument("--disc", type=int, default=1, help="world disc (default 1)")
    wmm.add_argument("--dry-run", action="store_true", help="report the plan, write nothing")
    wmm.set_defaults(func=_cmd_world_minimap)

    wrm = sub.add_parser("world-rename-markers",
                         help="rename overworld minimap MARKER labels: rewrite the world text (block 68), shadowed "
                              "per-language into the mod folder. No DLL; relaunch to apply.")
    wrm.add_argument("config", help="a .toml with [[marker_rename]] entries: {name = <current label> | locid = "
                                    "<0-63>, to = <new label>}. A name renames every slot it owns (South Gate = 6-10).")
    wrm.add_argument("--mod-folder", required=True,
                     help="the FolderNames mod folder to write into (e.g. FF9CustomMap)")
    wrm.add_argument("--lang", default="all",
                     help="language to rename in (default: all 7; or a single us/uk/jp/es/fr/gr/it)")
    wrm.add_argument("--dry-run", action="store_true", help="print `locId (old) -> new`, write nothing")
    wrm.set_defaults(func=_cmd_world_rename_markers)

    wer = sub.add_parser("world-encounter-rate",
                         help="retune the overworld random-encounter FREQUENCY: rewrite the world dispatchers' "
                              "RunWorldCode(26) rate writes (w_frameEventBattleProb) per-language into a mod folder. "
                              "No DLL (a plain .eb immediate rewrite); relaunch to apply.")
    wer.add_argument("--mod-folder", required=True,
                     help="the FolderNames mod folder to write into (e.g. FF9CustomMap)")
    _grp = wer.add_mutually_exclusive_group(required=True)
    _grp.add_argument("--multiplier", type=float, metavar="F",
                      help="encounter-FREQUENCY multiplier: 2.0 = twice as many encounters, 0.5 = half "
                           "(scales the game's own per-zone rates, preserving their relative danger; idempotent)")
    _grp.add_argument("--set", dest="set_prob", type=int, metavar="PROB",
                      help="force an absolute w_frameEventBattleProb everywhere (advanced; p = 1/(PROB+1), so lower "
                           "= more encounters). e.g. 231 = the vanilla standard rate")
    _grp.add_argument("--peaceful", action="store_true",
                      help="a near-encounter-free overworld (prob = 65535 -> p = 1/65536)")
    wer.add_argument("--lang", default="all",
                     help="language to retune (default: all 7; or a single us/uk/jp/es/fr/gr/it)")
    wer.add_argument("--dry-run", action="store_true",
                     help="print the per-dispatcher before->after rates, write nothing")
    wer.set_defaults(func=_cmd_world_encounter_rate)

    wet = sub.add_parser("world-encounters",
                         help="inspect / re-table the overworld random-encounter TABLE (discmr.img): which battle "
                              "scenes spawn on which terrain. --list dumps it; --config applies edits + deploys a "
                              "discmr.img override. No DLL (AssetManager mod-override); relaunch to apply.")
    wet.add_argument("--disc", type=int, default=1, choices=[1, 4],   # a REAL read disc: discmr.img only exists for 1/4
                     help="which disc's discmr.img (default 1; disc 4 has its own late-game table)")
    wet.add_argument("--list", action="store_true", help="inspect the table (per-topograph summary), write nothing")
    wet.add_argument("--zones", action="store_true",
                     help="inspect by ZONE (the selection unit): each zone's areas, record slice + topographs")
    wet.add_argument("--all", action="store_true", help="with --list: print every one of the 355 records")
    wet.add_argument("--config", help="a .toml with [[set]] (all|index|area|zone|topograph[+fog] -> scene[]/pattern/"
                                      "pad) and/or [remap] (old_scene_id = new_scene_id) edits; [encounters] or bare doc")
    wet.add_argument("--mod-folder", default=argparse.SUPPRESS,
                     help="mod folder to deploy the modified discmr.img into (default FF9CustomMap)")
    wet.add_argument("--dry-run", action="store_true", help="with --config: print the edit summary, write nothing")
    wet.set_defaults(func=_cmd_world_encounters)

    bsc = sub.add_parser("battle-scene",
                         help="inspect a real battle scene's enemy data (stats/affinities/rewards/attacks)")
    bsc.add_argument("donor", help="battle scene name to inspect, e.g. EF_R007 (see `battle-list --scenes`)")
    bsc.set_defaults(func=_cmd_battle_scene)

    bai = sub.add_parser("battle-ai",
                         help="disassemble a battle scene's enemy AI (EVT_BATTLE_<scene>.eb) -- read-only")
    bai.add_argument("donor", nargs="?", help="battle scene name, e.g. EF_R007 (see `battle-list --scenes`)")
    bai.add_argument("--sites", action="store_true",
                     help="list patchable AI constants (offset/value) for [[scene.ai_patch]] instead of the disasm")
    bai.add_argument("--asm", metavar="EXPR",
                     help="assemble an AI expression (e.g. \"{B_CURHP const(50) B_LT B_EXPR_END}\") -> its bytes; "
                          "the inverse of the disassembled expression form -- no scene needed")
    bai.add_argument("--asm-block", metavar="SRC", dest="asm_block",
                     help="assemble an AI COMMAND block -> its bytes + a re-disasm proof; ';' separates lines "
                          "(e.g. \"JMP_IF(end); SET({B_CURHP const(1) B_LT B_EXPR_END}); end:; RET()\") -- no scene")
    bai.add_argument("--lint", action="store_true",
                     help="lint the scene's enemy AI offline (decode / jump bounds / reachable RET / Attack-index "
                          "range); exit 1 if any issue is found")
    bai.set_defaults(func=_cmd_battle_ai)

    bsq = sub.add_parser("battle-seq",
                         help="disassemble / lint / assemble a battle scene's attack sequences (btlseq.raw17)")
    bsq.add_argument("donor", nargs="?", help="battle scene name, e.g. EF_R007 (see `battle-list --scenes`)")
    bsq.add_argument("--sites", action="store_true",
                     help="list patchable sequence operands (offset/value) for [[scene.seq_patch]] instead of the "
                          "disasm")
    bsq.add_argument("--asm", metavar="SRC",
                     help="assemble a sequence source (e.g. \"WaitAnim; Anim(anim_code=0); Calc; End\") -> its "
                          "bytes + a re-disasm proof; the inverse of the disassembly -- no scene needed")
    bsq.add_argument("--lint", action="store_true",
                     help="lint the scene's sequences offline (Anim-code range etc.); exit 1 if any issue is found")
    bsq.set_defaults(func=_cmd_battle_seq)

    ch = sub.add_parser("characters",
                        help="list the playable characters' base stats (the [[character]] / [[leveling]] targets)")
    ch.set_defaults(func=_cmd_characters)

    ag = sub.add_parser("ability-gems",
                        help="list support abilities + gem costs (the [[ability_gem]] targets)")
    ag.add_argument("-f", "--filter", help="only show abilities whose name contains this")
    ag.set_defaults(func=_cmd_ability_gems)

    afp = sub.add_parser("ability-features",
                         help="preview the AbilityFeatures.txt a field.toml emits (SA/AA/CMD ability-effect DSL)")
    afp.add_argument("toml", nargs="?", default=None, help="field.toml to preview (omit for the tag/name reference)")
    afp.add_argument("--tags", action="store_true", help="list the SA names + the legal [code=...] tags per kind")
    afp.add_argument("--game", default=argparse.SUPPRESS, help="FF9 install dir (only needed to resolve an >AA ability by NAME)")
    afp.set_defaults(func=_cmd_ability_features)

    bp = sub.add_parser("battle-patch",
                        help="preview the BattlePatch.txt a field.toml emits (enemy/attack/scene tuning by name)")
    bp.add_argument("toml", nargs="?", default=None, help="field.toml to preview (omit when using --fields)")
    bp.add_argument("--fields", action="store_true",
                    help="list the tunable [PatchableField] names by token instead of previewing a toml")
    bp.set_defaults(func=_cmd_battle_patch)

    bt = sub.add_parser("battle-telemetry",
                        help="log every battle calc to a JSONL (the Scripts-DLL Overload hook) -- install into "
                             "a live mod folder, --off to remove, --report to summarize a capture")
    bt.add_argument("mod_folder", nargs="?", default=None,
                    help="live mod folder to instrument -- a name (resolved in the game install, e.g. "
                         "FF9CustomMap) or a path; omit with --report/--clear")
    bt.add_argument("--off", action="store_true", help="remove the hook + recompile the mod DLL without it")
    bt.add_argument("--report", nargs="?", const="", default=None, metavar="JSONL",
                    help="summarize a captured telemetry file (default: <game>/ff9mk_battle_telemetry.jsonl)")
    bt.add_argument("--clear", action="store_true", help="delete the captured JSONL (start a fresh session)")
    bt.add_argument("--game", default=argparse.SUPPRESS, help="path to the FF9 install (default: auto-detect)")
    bt.set_defaults(func=_cmd_battle_telemetry)

    an = sub.add_parser("animations", help="list a character's cutscene gestures (pick by name)")
    an.add_argument("character", nargs="?", help="vivi / zidane / garnet / steiner / freya / quina / eiko / amarant")
    an.add_argument("-f", "--filter", help="only show gestures whose name contains this")
    an.add_argument("--ids", action="store_true", help="also print each gesture's numeric anim id")
    an.set_defaults(func=_cmd_animations)

    it = sub.add_parser("items", help="list FF9 item names + ids (give_item by name); --abilities lists "
                                      "ability names for items-set-ap")
    it.add_argument("-f", "--filter", help="only show items/abilities whose name (or token) contains this")
    it.add_argument("--abilities", action="store_true",
                    help="list each character's learnable abilities (name / AA:X-SA:X token / AP) instead of items")
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

    enc = sub.add_parser("encounters",
                         help="browse battle LOCATIONS: what battles are in a real place, and where a monster "
                              "appears (joins the .eb field census + region_catalog + monster names). Unlike "
                              "`scenes` (a bare BSC_ id/name catalog list, no place or monster join) and "
                              "`world-encounters` (the OVERWORLD terrain encounter TABLE only), this covers "
                              "field-scoped town/dungeon/boss battles. No args = summary browse.")
    enc.add_argument("query", nargs="?", default=None,
                     help="a place name/zone token (e.g. 'Evil Forest'), a monster name (e.g. 'Goblin'), or a "
                          "BSC_ scene name/id -- auto-detected (force one axis with --monster/--place)")
    _enc_axis = enc.add_mutually_exclusive_group()
    _enc_axis.add_argument("--monster", action="store_true", help="force `query` to be read as a monster name")
    _enc_axis.add_argument("--place", action="store_true",
                           help="force `query` to be read as a place name/zone token")
    enc.add_argument("--scene", metavar="ID|NAME", default=None,
                     help="one scene's full detail (places it's fought + monster/attack names): a raw id, a "
                          "full BSC_ name, or the short donor-style name `battle-scene` takes (e.g. EF_R007)")
    enc.add_argument("--unresolved", action="store_true",
                     help="list the honest coverage gaps instead: scene classification totals, "
                          "computed-operand fields, junk scene ids, name gaps, and fields never placed")
    enc.add_argument("--lang", default="us", choices=["us", "uk", "fr", "gr", "it", "es", "jp"],
                     help="language for monster/attack names (default us)")
    enc.add_argument("--no-names", action="store_true", dest="no_names",
                     help="census + place data only -- reuse the cached map when one exists, else build "
                          "WITHOUT the raw16/text-pool name scan (no monster names shown, disables "
                          "--monster)")
    enc.add_argument("--force", action="store_true",
                     help="rebuild the cached battle-location map from the install instead of reusing it")
    enc.set_defaults(func=_cmd_encounters)

    sp = sub.add_parser("sps", help="list/decode/preview a field's SPS particle effects (fire/smoke/magic); needs UnityPy")
    sp.add_argument("field", nargs="?", default=None, help="a field id or FBG/mapid token (see `ff9mapkit list-fields`)")
    sp.add_argument("--templates", action="store_true", help="list the [[sps]] creator templates (fire/smoke/...)")
    sp.add_argument("--id", type=int, default=None, help="decode ONE effect by id (full facts)")
    sp.add_argument("--png", metavar="OUT", help="render the effect's frames to a contact-sheet PNG")
    sp.add_argument("--gif", metavar="OUT", help="render the effect to an animated GIF (~15 fps)")
    sp.add_argument("--scale", type=int, default=3, help="preview pixel scale (default 3)")
    sp.set_defaults(func=_cmd_sps)

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

    ii = sub.add_parser("items-inspect",
                        help="decode a save's items / equipment / gil (read-only; from the Memoria extra file)")
    ii.add_argument("save", help="path to SavedData_ww.dat (per slot) or a Memoria extra-save file")
    ii.set_defaults(func=_cmd_items_inspect)

    sg = sub.add_parser("items-set-gil",
                        help="write a save's gil into the Memoria extra file (dry-run unless --apply)")
    sg.add_argument("save", help="a SavedData_ww_Memoria_*.dat extra file, OR a SavedData_ww.dat container "
                                 "(then pass --slot/--save-no or --autosave)")
    sg.add_argument("gil", type=int, help="the new gil value (0..9,999,999, the in-game cap)")
    sg.add_argument("--slot", type=int, default=None, help="0-indexed slot (container only; menu shows it +1)")
    sg.add_argument("--save-no", type=int, default=None, help="0-indexed save within the slot (container only)")
    sg.add_argument("--autosave", action="store_true", help="edit the autosave (container only)")
    sg.add_argument("--apply", action="store_true", help="actually write (default is a dry-run preview)")
    sg.add_argument("--no-backup", action="store_true", help="skip writing the <file>.bak backup on --apply")
    sg.set_defaults(func=_cmd_items_set_gil)

    def _add_save_target(p):                                            # the shared save-target flags
        p.add_argument("save", help="a SavedData_ww_Memoria_*.dat extra file, OR a SavedData_ww.dat container "
                                    "(then pass --slot/--save-no or --autosave)")
        p.add_argument("--slot", type=int, default=None, help="0-indexed slot (container only; menu shows it +1)")
        p.add_argument("--save-no", type=int, default=None, help="0-indexed save within the slot (container only)")
        p.add_argument("--autosave", action="store_true", help="edit the autosave (container only)")
        p.add_argument("--apply", action="store_true", help="actually write (default is a dry-run preview)")
        p.add_argument("--no-backup", action="store_true", help="skip the <file>.bak backup on --apply")

    si = sub.add_parser("items-set-item",
                        help="set an item's inventory count in the Memoria extra file (0 removes; dry-run "
                             "unless --apply)")
    _add_save_target(si)
    si.add_argument("item", help="item name or 0-254 id (e.g. Potion, 'Phoenix Down', 236)")
    si.add_argument("count", type=int, help="the new stack count (0 removes the item; clamps to 99)")
    si.set_defaults(func=_cmd_items_set_item)

    se = sub.add_parser("items-set-equip",
                        help="set one equip slot of one character in the Memoria extra file (dry-run unless "
                             "--apply)")
    _add_save_target(se)
    se.add_argument("character", help="CharacterId 0-11 or a name (Zidane..Beatrix, Dagger, Salamander)")
    se.add_argument("equip_slot", metavar="slot", help="weapon | head | wrist | armor | accessory (aliases "
                                                       "body, acc)")
    se.add_argument("item", help="item name/id to equip, or 'empty'/255 to unequip")
    se.set_defaults(func=_cmd_items_set_equip)

    sk = sub.add_parser("items-set-keyitem",
                        help="give / remove a KEY (important) item by name in the Memoria extra file (dry-run "
                             "unless --apply)")
    _add_save_target(sk)
    sk.add_argument("keyitem", help="key-item name (live from the install) or a 0-255 id")
    sk.add_argument("--remove", action="store_true", help="remove the key item (clear obtained + used)")
    sk.add_argument("--used", action="store_true", help="also mark it used (default: obtained, not used)")
    sk.add_argument("--not-obtained", action="store_true", help="mark known-but-not-obtained (rare)")
    sk.set_defaults(func=_cmd_items_set_keyitem)

    ss = sub.add_parser("items-set-stat",
                        help="set a character's permanent stat (Speed/Strength/Magic/Spirit) in the Memoria "
                             "extra file (dry-run unless --apply)")
    _add_save_target(ss)
    ss.add_argument("character", help="CharacterId 0-11 or a name (Zidane..Beatrix)")
    ss.add_argument("stat", help="Speed | Strength | Magic | Spirit")
    ss.add_argument("value", type=int, help="target value (Speed/Spirit cap 50, Strength/Magic cap 99)")
    ss.set_defaults(func=_cmd_items_set_stat)

    sa = sub.add_parser("items-set-ap",
                        help="set a character's ability AP / mastery in the Memoria extra file (dry-run unless "
                             "--apply)")
    _add_save_target(sa)
    sa.add_argument("character", help="CharacterId 0-11 or a name (Zidane..Beatrix)")
    sa.add_argument("ability", help="ability name, AA:X / SA:X token, numeric abil_id, or 'all'")
    sa.add_argument("value", help="master | max | forget | a number (0-255)")
    sa.set_defaults(func=_cmd_items_set_ap)

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

    from .save import WORLD_ACTORS as S_WORLD_ACTORS
    se = sub.add_parser("save-edit",
                        help="set a real FF9 save's story state (ScenarioCounter + flags) -- the 'recreate' verb")
    se.add_argument("save", help="path to SavedData_ww.dat (or a copy of it)")
    se.add_argument("--list", action="store_true", help="list the populated saves (slot/save, scenario, mognet locks) and exit")
    se.add_argument("--slot", type=int, help="save slot 0-9")
    se.add_argument("--save", dest="save_index", type=int, help="save 0-14 within the slot")
    se.add_argument("--block", type=int, help="raw data-block index (alternative to --slot/--save; 0 = autosave)")
    se.add_argument("--autosave", action="store_true", help="target the autosave block")
    se.add_argument("--scenario", help="set ScenarioCounter: a value (2500) or an area name (\"Ice Cavern\")")
    se.add_argument("--set", dest="set_flags", help="comma-separated flag indices (or [[flag]] names with --names) to SET")
    se.add_argument("--clear", dest="clear_flags", help="comma-separated flag indices to CLEAR")
    se.add_argument("--world-pos", dest="world_pos", metavar="X,Z",
                    help="relocate the OVERWORLD actor to world X,Z (e.g. \"272,-1142\"; leave one blank to keep "
                         "that axis). Y is ground-snapped. Only for an overworld save; pick a WALKABLE spot.")
    se.add_argument("--world-actor", dest="world_actor", choices=list(S_WORLD_ACTORS), default="player",
                    help="which overworld actor --world-pos moves: player (default) or chocobo (Choco's parked spot)")
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

    fr = sub.add_parser("fork-report",
                        help="preview what a fork of a REAL field will/won't reproduce, offline (fidelity report)")
    fr.add_argument("field", help="real field id or FBG name (e.g. 354, dl_shp, lb_tmp) -- see `list-fields`")
    fr.add_argument("--explain", action="store_true",
                    help="decode each NPC's talk routine into readable English (dialogue + items + the funcs "
                         "it runs) -- shows WHY a render-only NPC needs --verbatim")
    fr.set_defaults(func=_cmd_fork_report)

    lmp = sub.add_parser("logic-map",
                         help="read-only legible map of a REAL field's whole .eb (entries/routines, the resolved "
                              "call graph, dialogue/item/flag effects) -- the inspectable view of a verbatim fork")
    lmp.add_argument("field", help="real field id or FBG name (e.g. 354, dl_shp) -- see `list-fields`")
    lmp.add_argument("--json", action="store_true",
                     help="emit the map as JSON (the generated [view]) instead of the readable transcript")
    lmp.set_defaults(func=_cmd_logic_map)

    chx = sub.add_parser("chocobo-export",
                         help="export a Chocobo Hot & Cold forest's dig PRIZE POOL + TIMER as an editable "
                              "[chocobo] block (paste into the verbatim fork's field.toml; unedited = byte-identical)")
    chx.add_argument("source", help="field id / FBG name (2950, ch_fst) or a verbatim project's field.toml")
    chx.set_defaults(func=_cmd_chocobo_export)

    le = sub.add_parser("lint-eb",
                        help="structurally lint a field's .eb (decode / jump+switch bounds / reachable terminator / "
                             "dangling RunScript) -- the offline soundness check for a verbatim fork or an edit")
    le.add_argument("field", help="a real field id/name OR a path to a .eb / verbatim .bin")
    le.set_defaults(func=_cmd_lint_eb)

    fdr = sub.add_parser("find-rooms",
                         help="sweep ALL fields for the best swap/demo test rooms (single-PC + swap-clean + close camera)")
    fdr.add_argument("--limit", type=int, default=20, help="max rooms to show (default 20)")
    fdr.add_argument("--max-fov", type=float, default=45.0,
                     help="upper FOV bound, degrees (default 45 = exclude wide establishing lenses; raise to widen)")
    fdr.set_defaults(func=_cmd_find_rooms)

    xt = sub.add_parser("extract-templates",
                        help="regenerate the kit's base assets from YOUR FF9 install (ships no game data)")
    xt.add_argument("--no-fixtures", action="store_true", help="skip the test fixtures (templates only)")
    xt.set_defaults(func=_cmd_extract_templates)

    su = sub.add_parser("setup",
                        help="one-shot post-install setup: find your FF9 install, remember it, extract base "
                             "assets, report Memoria status (--install-engine ZIP to install the engine bundle)")
    su.add_argument("--install-engine", metavar="ZIP", default=None,
                    help="also install the Dream World IX engine bundle (dwix-custom-memoria-*.zip) -- backs "
                         "up the originals; needed only to play FORKED real fields")
    su.add_argument("--force", action="store_true", help="re-extract the base assets even if already present")
    su.add_argument("--no-extract", action="store_true", help="skip the base-asset extraction step")
    su.add_argument("--no-fixtures", action="store_true", help="skip test fixtures during extraction")
    su.set_defaults(func=_cmd_setup)

    dpf = sub.add_parser("deploy", aliases=["deploy-field"],
                         help="reversibly INSTALL one field.toml into the live game, into a DEDICATED mod "
                              "folder (SAFE by default: prints the plan; --apply touches the game).")
    dpf.add_argument("field", help="path to the field.toml to install")
    dpf.add_argument("--mod-folder", dest="mod_folder", default=None,
                     help="mod folder to install into (default: a dedicated FF9CustomMap-<field name>)")
    dpf.add_argument("--out-dist", dest="out_dist", default=None,
                     help="keep the staged build here instead of a temp dir (for inspection)")
    dpf.add_argument("--allow-name-collision", action="store_true", dest="allow_name_collision",
                     help="install even when EVT/FBG names collide with another FolderNames folder (default ABORT)")
    dpf.add_argument("--allow-id-collision", action="store_true", dest="allow_id_collision",
                     help="install even when the field id collides with another FolderNames folder (default ABORT)")
    dpf.add_argument("--allow-drop", action="store_true", dest="allow_drop",
                     help="install into a folder holding OTHER fields, unregistering them (default ABORT). A "
                          "single-field install replaces its folder wholesale; iterate many fields into one "
                          "shared folder with the repo's tools/deploy_field.py instead.")
    dpf.add_argument("--game", default=argparse.SUPPRESS, help="game install path (default: auto-detect)")
    dpf.add_argument("--apply", action="store_true", help="ACTUALLY touch the game (default: dry-run, prints the plan)")
    dpf.set_defaults(func=_cmd_deploy)

    dca = sub.add_parser("deploy-campaign",
                         help="reversibly INSTALL a built campaign into the live game + wire New Game (SAFE by "
                              "default: prints the plan; --apply touches the game). The installed-copy deploy.")
    dca.add_argument("target", help="path to campaign.toml (built fresh) OR a prebuilt dist/ directory")
    dca.add_argument("--mod-folder", dest="mod_folder", default=argparse.SUPPRESS,
                     help="Memoria mod folder to install into (default FF9CustomMap)")
    dca.add_argument("--entry", default=None, help="New-Game entry: member name, field id, or omit for the manifest entry")
    dca.add_argument("--out-dist", dest="out_dist", default=None, help="where to stage the build (default: target/dist)")
    dca.add_argument("--allow-artless", action="store_true", dest="allow_artless",
                     help="install editable members that lack exported art (they render with NO background)")
    dca.add_argument("--no-warp", action="store_true", dest="no_warp", help="install the mod but skip New-Game wiring")
    dca.add_argument("--allow-name-collision", action="store_true", dest="allow_name_collision",
                     help="install even when EVT/FBG names collide with another FolderNames folder (default ABORT)")
    dca.add_argument("--allow-id-collision", action="store_true", dest="allow_id_collision",
                     help="install even when a field/scene id collides with another FolderNames folder (default ABORT)")
    dca.add_argument("--flag-base", type=int, default=None, dest="flag_base",
                     help="override the campaign's flag_base (the journey assembler's disjoint-window lever)")
    dca.add_argument("--no-promote-csv", action="store_true", dest="no_promote_csv",
                     help="do NOT promote the entry field's start-state CSVs to the highest FolderNames folder")
    dca.add_argument("--promote-csv-to", dest="promote_csv_to", default=None,
                     help="folder to promote start-state CSVs into (default: the highest Memoria.ini FolderNames folder)")
    dca.add_argument("--apply", action="store_true", help="ACTUALLY touch the game (default: dry-run, prints the plan)")
    dca.set_defaults(func=_cmd_deploy_campaign)

    dje = sub.add_parser("deploy-journey",
                         help="deploy (or dry-run) a multi-campaign JOURNEY into the live game: campaigns + links "
                              "+ hub, one unified revert. Default = the dry-run playbook; --apply does the install.")
    dje.add_argument("journeys", help="path to a journeys.toml ([hub] + [[journey]] rows)")
    dje.add_argument("--apply", action="store_true",
                     help="ONE-SHOT: deploy every campaign (seeded entry) + links + the hub field, one unified "
                          "revert (default is a dry-run that prints the playbook). New Game is NOT touched unless "
                          "you add --newgame hub|entry.")
    dje.add_argument("--newgame", choices=("none", "hub", "entry"), default="none",
                     help="with --apply, where New Game lands (SINGLE-OWNER). none (default) = unchanged, reach "
                          "the hub via the debug menu (~). hub = the hub selector menu. entry = straight into the opening field.")
    dje.add_argument("--wire-newgame", action="store_const", const="hub", dest="newgame",
                     help="back-compat alias for --newgame hub.")
    dje.add_argument("--apply-links", action="store_true", dest="apply_links",
                     help="EXECUTE ONLY the cross-campaign link .eb remaps (re-run after any campaign re-deploy)")
    dje.add_argument("--single-folder", dest="single_folder", nargs="?", const="", default=None,
                     help="with --apply, MERGE the whole journey into ONE stacked mod folder (a single FolderNames "
                          "entry). Optional NAME (default FF9CustomMap-<hub>).")
    dje.add_argument("--allow-collision", action="store_true", dest="allow_collision",
                     help="(single-folder) install even if the merged journey collides with another FolderNames folder")
    dje.add_argument("--hub-out", dest="hub_out", default=None,
                     help="path for the emitted hub field.toml (default: hub.field.toml beside the journeys.toml)")
    dje.set_defaults(func=_cmd_deploy_journey)

    ng = sub.add_parser("newgame",
                        help="point New Game at a deployed custom field id (creates the field-70 override from "
                             "stock; the opening FMV is preserved). The installed-copy New-Game wiring.")
    ng.add_argument("field_id", type=int, help="the field id New Game should land on (must be deployed/registered)")
    ng.add_argument("--mod-folder", dest="mod_folder", default=argparse.SUPPRESS,
                    help="mod folder to write the override into (default FF9CustomMap)")
    ng.add_argument("--retarget", action="store_true",
                    help="PATCH an existing field-70 override instead of creating one from stock")
    ng.add_argument("--from", dest="frm", type=int, default=None,
                    help="(--retarget) the override's current target id (default: auto-detected)")
    ng.add_argument("--game", default=argparse.SUPPRESS, help="game install path (default: auto-detect)")
    ng.add_argument("--dry-run", action="store_true", help="report only; write nothing")
    ng.set_defaults(func=_cmd_newgame)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
