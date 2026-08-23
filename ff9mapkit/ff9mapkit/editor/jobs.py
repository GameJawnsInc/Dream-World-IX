"""tk-free build / deploy / import job layer -- the backend the GUIs are a view over.

The Build & Deploy and FFIX Import flows are forms + a subprocess stream + a verdict. This module holds
the *non-view* parts of both so the Qt Workspace (and a test) can reuse them verbatim, with no tk and no
Qt: the file-kind detector, the deploy-target reader, the deployed-field lister, and the argv builders
for every shell-out (the ``ff9mapkit import ...`` line, the ``tools/deploy_*.py`` deploys, the reverts).

The deploy *tools* live at the REPO root (``tools/``), not inside the kit package, so the argv builders
take ``repo_root`` rather than hardcoding a checkout path. ``detect_game_mod`` / ``detect_deployed_fields``
go through :mod:`..config` (the install resolver), so they need no repo path.
"""

from __future__ import annotations

import datetime
import shutil
import sys
import tomllib
from pathlib import Path


# --------------------------------------------------------------------------- file-kind detection
def detect_kind(path):
    """``('campaign', plan)`` | ``('journey', manifest)`` | ``('battle', None)`` | ``('field', None)``.

    A campaign.toml has a ``[campaign]`` table (``load_campaign`` raises on anything else); a journeys.toml
    has a ``[hub]`` table and/or ``[[journey]]`` rows (``load_journeys`` raises otherwise); a battle.toml
    has a ``[battlemap]`` table; else it's a field.toml -- the cheap, exact discriminators (the four kinds
    are table-disjoint, so the order is just for readability). Mirrors the tkinter Build GUI + the journey
    front door."""
    try:
        from ..campaign import load_campaign
        return "campaign", load_campaign(path)
    except Exception:
        pass
    try:
        from ..journey import load_journeys
        return "journey", load_journeys(path)
    except Exception:
        pass
    try:
        with open(path, "rb") as fh:
            if "battlemap" in tomllib.load(fh):
                return "battle", None
    except Exception:
        pass
    return "field", None


def field_id_name(path):
    """``(id, name)`` from a field.toml's ``[field]`` table, or ``(None, None)`` -- a light parse."""
    try:
        d = tomllib.loads(Path(path).read_text(encoding="utf-8"))
        f = d.get("field", {}) or {}
        return (f.get("id"), f.get("name"))
    except Exception:
        return (None, None)


def field_inplace_target(path):
    """For a VERBATIM fork of a REAL field, the in-place deploy target: a dict
    ``{donor, name, text_block, is_forest}`` -- deploy the fork under the donor's OWN id (so the engine
    loads it in place of the real field, keeping any id-hardcoded behaviour like the Chocobo HUD), keeping
    the donor's registered text block (``EVENT_ID_TO_MES`` -- the HUD zone gate for the forests). Returns
    ``None`` when the project isn't a verbatim fork of a real field (nothing to deploy in place). ``name``
    is the fork's own name (the FieldScene FBG-override; the HUD keys on id + zone, not name)."""
    try:
        d = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None
    vb = d.get("verbatim_eb") or {}
    donor = vb.get("donor")
    if not isinstance(donor, int) or donor >= 4000:            # only a fork of a real (locked-band) field
        return None
    f = d.get("field", {}) or {}
    from .._fieldtext import EVENT_ID_TO_MES
    tb = EVENT_ID_TO_MES.get(donor, f.get("text_block") or 1073)
    return {"donor": donor, "name": f.get("name") or Path(path).stem,
            "text_block": tb, "is_forest": donor in (2950, 2951, 2952)}


def current_newgame_target(mod_folder):
    """Where a deployed field-70 New-Game override points -- the field id New Game lands on -- or ``None``
    when no override is deployed under ``mod_folder`` (or it can't be parsed).

    ``mod_folder`` is the on-disk mod-folder DIRECTORY (e.g. ``<game>/FF9CustomMap``), not just its name.
    Pure + side-effect-free (reads one ``.eb.bytes`` file, writes nothing), so it is unit-testable against
    a scratch tree. Used to NAME the New-Game casualty a wholesale campaign/journey deploy would silently
    wipe (that deploy wholesale-replaces the mod folder, taking the override with it). Returns the first
    ``Field()`` warp in the override's Main_Init -- the current New-Game destination. Never raises."""
    try:
        from ..newgame import LANGS, OVERRIDE_REL, newgame_target
        base = Path(mod_folder)
        for lang in LANGS:
            p = base / OVERRIDE_REL.format(lang=lang)
            if p.is_file():
                try:
                    tgt = newgame_target(p.read_bytes())
                except Exception:                            # noqa: BLE001 -- unparseable/corrupt -> None
                    tgt = None
                if tgt is not None:
                    return tgt
        return None
    except Exception:                                        # noqa: BLE001 -- bad path / import failure -> None
        return None


# --------------------------------------------------------------------------- install / deploy targets
def detect_game_mod():
    """The game's ``FF9CustomMap`` folder, or ``None`` if the install can't be found."""
    try:
        from .. import config
        return config.find_game_path() / "FF9CustomMap"
    except Exception:
        return None


def detect_deploy_target(repo_root):
    """``(mod_folder, field_id)`` from this worktree's ``.ff9deploy.toml``, or sane defaults -- the test
    slot the field deploy and battle deploy write into."""
    mod, fid = "FF9CustomMap", None
    f = Path(repo_root) / ".ff9deploy.toml"
    if f.is_file():
        try:
            d = tomllib.loads(f.read_text(encoding="utf-8"))
            mod = d.get("mod_folder", mod) or mod
            fid = d.get("id")
        except Exception:
            pass
    return mod, fid


def has_deploy_tools(repo_root) -> bool:
    """True if the deploy SCRIPTS (``tools/deploy_field.py`` etc.) are present -- i.e. this is a repo checkout,
    not an installed wheel (the wheel ships no ``tools/``). The Workspace uses it to hide the dev-only deploy
    paths (test-slot / battle / reverts) for an installed copy."""
    return (Path(repo_root) / "tools" / "deploy_field.py").is_file()


def resolve_dev_repo(default_repo):
    """The repo root the Workspace should use for the DEV deploy loop (the debug-menu test slot + ``tools/``).

    Lets an INSTALLED Workspace light up dev mode against a source checkout, in precedence order:
      1. ``$FF9_REPO`` -- if it points at a checkout (explicit opt-in; wins even over a repo launch);
      2. ``default_repo`` -- if it already is a checkout (the normal ``apps/ff9_workspace.pyw`` launch);
      3. a walk UP from the current directory -- an installed launcher started from inside a checkout;
      4. else ``default_repo`` unchanged -- stay in installed / end-user mode (no test slot).
    Always returns a ``Path``. An ``$FF9_REPO`` that isn't a checkout is ignored (never silently breaks)."""
    import os
    env = os.environ.get("FF9_REPO")
    if env and has_deploy_tools(env):
        return Path(env)
    if has_deploy_tools(default_repo):
        return Path(default_repo)
    try:
        cwd = Path.cwd()
        for cand in (cwd, *cwd.parents):
            if has_deploy_tools(cand):
                return cand
    except OSError:                      # cwd deleted / unreadable -> just fall back
        pass
    return Path(default_repo)


# --------------------------------------------------------------------------- the shared undo home
# TWO roots, deliberately distinct -- the same split ``tools/deploy_field.py`` makes internally between its
# ``_REPO`` and ``_MAIN``. The tool SCRIPTS run from the checkout the Workspace was launched from (a
# worktree runs ITS OWN code, which is the point of a worktree), but the ``backups/`` + ``tools/scroll_out/``
# they write into live in the MAIN repo: a worktree is ephemeral, so an undo parked in one evaporates while
# the live game install keeps the deploy (project-ff9-worktree-parked-backups). Launched from a worktree,
# a GUI that looked in its own scroll_out saw an EMPTY ledger and every Revert button missed.
#
# We ASK the checkout's own ``tools/repo_root.py`` instead of re-deriving the rule here, because two
# implementations of "where does the undo live" is the very defect being fixed one layer up -- and a
# checkout too old to HAVE repo_root.py falls back to answering itself, which is exactly where that
# checkout's tools write. The package cannot simply import it: it is a repo-only ``tools/`` module and is
# deliberately dependency-free (``tools/restore_memoria_dll.py`` imports it with no kit on sys.path).
_MAIN_REPO: dict = {}      # str(repo_root) -> Path. Keyed on the INPUT: a bare process-wide memo of one
                           # answer is how a shared global rots (project-ff9-global-module-monkeypatch).


def _repo_root_module(repo_root):
    """The checkout's ``tools/repo_root.py`` loaded as a private module, or ``None`` when it is absent or
    unloadable. Never registered in ``sys.modules`` -- the tools import it under the bare name
    ``repo_root``, and this must not shadow or be shadowed by that."""
    p = Path(repo_root) / "tools" / "repo_root.py"
    if not p.is_file():
        return None
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("_ff9mapkit_tools_repo_root", p)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    except Exception:                    # noqa: BLE001 -- a broken helper must never break the GUI
        return None


def main_repo_root(repo_root):
    """The MAIN repo for ``repo_root`` -- itself from the main checkout, the owning repo from a linked
    worktree. Falls back to ``repo_root`` unchanged when the resolver is absent or cannot answer (no git,
    not a repo, an installed copy with no ``tools/``), which is the pre-fix rooting and therefore still
    agrees with such a checkout's own scripts. Memoized per input; never raises."""
    key = str(repo_root)
    if key not in _MAIN_REPO:
        got = None
        mod = _repo_root_module(repo_root)
        if mod is not None:
            try:
                got = Path(mod.main_repo_root(start=Path(repo_root) / "tools", fallback=Path(repo_root)))
            except Exception:            # noqa: BLE001 -- ditto
                got = None
        _MAIN_REPO[key] = got if got is not None else Path(repo_root)
    return _MAIN_REPO[key]


def scroll_out_dir(repo_root) -> Path:
    """The revert cache every ``tools/deploy_*.py`` writes into -- the MAIN repo's ``tools/scroll_out``.
    ONE per machine, so a slot's revert is found no matter which worktree deployed it."""
    return main_repo_root(repo_root) / "tools" / "scroll_out"


def install_backups_dir(repo_root) -> Path:
    """Where a snapshot of live GAME-INSTALL state belongs -- the MAIN repo's ``backups/`` (Hard-Constraint
    §2's dir, kept off any ephemeral worktree)."""
    return main_repo_root(repo_root) / "backups"


def detect_deployed_fields(mod_folder):
    """``[(id, name), ...]`` of the FieldScene lines in the worktree mod folder's DictionaryPatch -- the
    fields whose encounter a battle-mint can repoint (the valid 'trigger field' choices)."""
    out = []
    try:
        from .. import config
        dp = config.find_game_path() / mod_folder / "DictionaryPatch.txt"
        if dp.is_file():
            for ln in dp.read_text(encoding="utf-8").splitlines():
                p = ln.split()
                if p[:1] == ["FieldScene"] and len(p) >= 5:
                    out.append((p[1], p[4]))
    except Exception:
        pass
    return out


def scan_deployed_reverts(dict_patch, scroll_dir):
    """The 'Deployed here' ledger: every field registered in a mod folder's DictionaryPatch paired with
    the per-id undo script ``deploy_field`` wrote for it (``revert_deploy_<id>.py``), plus the folder-wide
    campaign / New-Game reverts -- so a user can see and undo ANY accumulated deploy, not just the latest
    one the single Revert button reaches (the per-id scripts accumulate unlisted).

    Pure and side-effect-free (reads two paths, writes nothing), so it is unit-testable against a scratch
    tree. ``dict_patch`` = the mod folder's DictionaryPatch.txt (or ``None`` -> no field rows); ``scroll_dir``
    = ``tools/scroll_out`` (the revert cache, or ``None`` on an installed copy -> every script reads absent).

    Returns a list of row dicts -- field rows first (DictionaryPatch order), then the folder-wide reverts
    newest-first by mtime::

        {"kind": "field"|"campaign"|"newgame", "id": str|None, "name": str,
         "script": str|None, "mtime": float|None}

    A row whose ``script`` is ``None`` has no undo script on disk -- the GUI renders it read-only
    informational (the registration is real; there is just nothing to run).
    """
    scroll = Path(scroll_dir) if scroll_dir else None

    def _script(fname):
        if scroll is None:
            return None
        p = scroll / fname
        return p if p.is_file() else None

    rows = []
    if dict_patch is not None:
        dp = Path(dict_patch)
        try:
            lines = dp.read_text(encoding="utf-8").splitlines() if dp.is_file() else []
        except OSError:
            lines = []
        for ln in lines:
            p = ln.split()
            if p[:1] == ["FieldScene"] and len(p) >= 5:
                fid, name = p[1], p[4]
                s = _script(f"revert_deploy_{fid}.py")
                rows.append({"kind": "field", "id": fid, "name": name,
                             "script": str(s) if s else None,
                             "mtime": s.stat().st_mtime if s else None})
    # Folder-wide reverts (not per-id): the wholesale campaign deploy + the two New-Game wirings. Only the
    # ones that exist on disk become rows, newest first (mirrors latest_newgame_revert's mtime pick).
    extra = []
    for kind, label, fname in (("campaign", "campaign deploy", "revert_campaign.py"),
                               ("install", "Install to game", "revert_install.py"),
                               ("newgame", "New Game entry", "revert_newgame_from_stock.py"),
                               ("newgame", "New Game retarget", "revert_newgame_retarget.py")):
        s = _script(fname)
        if s:
            extra.append({"kind": kind, "id": None, "name": label,
                          "script": str(s), "mtime": s.stat().st_mtime})
    extra.sort(key=lambda r: r["mtime"], reverse=True)
    return rows + extra


def latest_battle_revert(repo_root):
    """The most recently written ``tools/scroll_out/revert_battle_*.py``, or ``None``."""
    scroll = scroll_out_dir(repo_root)
    scripts = sorted(scroll.glob("revert_battle_*.py"), key=lambda p: p.stat().st_mtime, reverse=True)
    return scripts[0] if scripts else None


def latest_journey_revert(repo_root):
    """The most recently written journey revert script, or ``None``.

    A journey deploy writes ONE of two reverts depending on the mode: the full ``--apply`` one-shot writes the
    unified ``revert_journey.py``; a standalone ``--apply-links`` writes only ``revert_journey_links.py``. The
    GUI Revert button must undo the user's LAST journey action, so we pick the most-recently-modified of the
    two (mirrors :func:`latest_battle_revert`) -- never a stale unified revert left over from an earlier run."""
    scroll = scroll_out_dir(repo_root)
    cands = [p for p in (scroll / "revert_journey.py", scroll / "revert_journey_links.py") if p.is_file()]
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None


# --------------------------------------------------------------------------- import argv (FFIX Import)
def import_args(field, *, out, field_id, name=None, art="native", carry_npcs=True, carry_text=True,
                dialogue_stubs=False, save_moogle=False, verbatim=False,
                swap_player=None, neutralize_gestures=False):
    """The ``ff9mapkit import ...`` argv for a field fork (no ``py -m ff9mapkit`` prefix).

    ``verbatim`` = the TRUEST fork (``--verbatim``): ship the donor's whole ``.eb`` + ``.mes`` and run the
    real logic (story gating, rotating cast, real doors -- the proven faithful path, docs/FORK_FIDELITY.md).
    It implies ``--native`` and carries every NPC/prop/line itself, so the ``art``/carry options DON'T apply
    and we emit ONLY ``--verbatim`` (a short, honest command). ``art``/carry below are the RE-AUTHORABLE path:
    ``art`` is 'native' (--native) / 'borrow' (neither flag) / 'editable' (--editable); the carry flags map to
    the fidelity options, and --carry-text / --save-moogle imply --graft-player-funcs (kit-enforced, passed
    explicitly so the command reads honestly).

    ``swap_player`` (--swap-player WHO) changes who you WALK as -- a playable name or any GEO model; it implies
    ``--verbatim`` in the CLI, so the flags go BEFORE the verbatim early-return (they apply to either path).
    ``neutralize_gestures`` (--neutralize-gestures) rewrites the swapped rig's scripted gestures to idle; the
    CLI requires it be paired with ``swap_player`` (the GUI guards this before building the argv)."""
    args = ["import", str(field), "--out", str(out), "--id", str(field_id)]
    if name:
        args += ["--name", str(name)]
    if swap_player:
        args += ["--swap-player", str(swap_player)]
    if neutralize_gestures:
        args.append("--neutralize-gestures")
    if verbatim:
        args.append("--verbatim")
        return args
    if art == "native":
        args.append("--native")
    elif art == "editable":
        args.append("--editable")
    if carry_npcs or carry_text or save_moogle:
        args.append("--graft-player-funcs")
    if carry_text:
        args.append("--carry-text")
    if dialogue_stubs:
        args.append("--dialogue")
    if save_moogle:
        args.append("--save-moogle")
    return args


def import_chain_args(seeds, *, out=None, whole_zone=True, ids=None, verbatim=True, id_base=None,
                      name_prefix=None, fresh_ids=False, flags_per_field=None, max_fields=None,
                      campaign_name=None, swap_player=None, neutralize_gestures=False):
    """The ``ff9mapkit import-chain ...`` argv for forking a CONNECTED REGION (a multi-field chain) into ONE
    campaign -- the workflow behind the disc-1 opening, now a GUI action.

    ``seeds`` is the raw seed string ('300', '50,100,64', or an FBG substring). With no ``out`` it's the
    DRY-RUN (prints the blast radius + coverage, touches nothing) -- the region analogue of fork-report.
    ``ids`` (a compact range string, e.g. '100-117') scopes the fork to an EXPLICIT id set -- one story-state
    cluster of a revisited zone, not all its visits; it takes precedence over and suppresses ``whole_zone``.
    Otherwise ``whole_zone`` seeds every field in each seed's zone (catches cutscene-only screens the door-walk
    misses; it also auto-raises the walk's --max-fields to fit). ``verbatim`` ships each member's real .eb +
    .mes so the chain runs the real logic. STABLE IDS are the kit DEFAULT (re-forking into an existing ``out``
    reuses its donor->id+name map so in-fork saves survive) -- ``fresh_ids`` opts out (re-number from scratch).

    ``swap_player`` (--swap-player WHO) plays the WHOLE chain as one character/model (implies --verbatim);
    ``neutralize_gestures`` (--neutralize-gestures) stands cleanly through cutscene gestures (requires a swap;
    the GUI guards that before building the argv)."""
    args = ["import-chain", str(seeds)]
    if ids:                                # explicit cluster wins over whole-zone (the two are mutually exclusive)
        args += ["--ids", str(ids)]
    elif whole_zone:
        args.append("--whole-zone")
    if verbatim:
        args.append("--verbatim")
    if swap_player:
        args += ["--swap-player", str(swap_player)]
    if neutralize_gestures:
        args.append("--neutralize-gestures")
    if out:
        args += ["--out", str(out)]
    if id_base is not None:
        args += ["--id-base", str(id_base)]
    if name_prefix:
        args += ["--name-prefix", str(name_prefix)]
    if flags_per_field is not None:
        args += ["--flags-per-field", str(flags_per_field)]
    if max_fields is not None:
        args += ["--max-fields", str(max_fields)]
    if campaign_name:
        args += ["--campaign-name", str(campaign_name)]
    if fresh_ids:
        args.append("--fresh-ids")
    return args


# --------------------------------------------------------------------------- Install-to-game backup law
def _stamp():
    return datetime.datetime.now().strftime("%Y%m%d-%H%M%S")


def snapshot_mod_folder(mod_folder, backups_dir, reverts_dir):
    """Honor Hard-Constraint §2 (back up before editing any game file) on an 'Install to game' write:
    snapshot the WHOLE live mod folder and emit a standalone ``revert_install.py`` that restores it.

    Why the whole folder rather than just the installed id's files: 'Install to game' runs
    ``ff9mapkit build ... --preserve-existing``, which REWRITES the folder's DictionaryPatch wholesale
    (plus BattlePatch/TextPatch and the mod-global CSVs) alongside the built id's StreamingAssets bytes --
    the write-set spans registration files rebuilt from scratch, so a reliable per-id derivation isn't
    available at this layer. Per the chair's ruling (correctness beats economy) we copy the whole folder;
    a re-install over unchanged files restores them byte-identically.

    Copies ``mod_folder`` to ``backups_dir/<stamp>/<name>/`` and writes ``revert_install.py`` into
    ``reverts_dir`` (the same revert-cache the ledger + Revert read). The revert deletes the live folder and
    restores the snapshot -- or, when the folder did NOT exist before the install, removes it. Returns the
    revert-script :class:`Path`, or ``None`` when there is nothing to protect or the backup could not be
    written (the caller then tells the user Revert is unavailable rather than overclaiming).

    Pure of any game knowledge (two path args in, one path out); never raises."""
    try:
        mod = Path(mod_folder)
        backups_dir, reverts_dir = Path(backups_dir), Path(reverts_dir)
        snap = None
        if mod.is_dir():
            snap = backups_dir / _stamp() / mod.name
            snap.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(mod, snap)                        # the pre-install truth, kept whole
        reverts_dir.mkdir(parents=True, exist_ok=True)
        rl = ['"""Revert an Install-to-game: restore the mod-folder snapshot taken before the install."""',
              "import os, shutil",
              f"LIVE = {str(mod)!r}",
              f"SNAP = {str(snap) if snap else None!r}",
              "if SNAP and os.path.isdir(SNAP):",
              "    if os.path.isdir(LIVE): shutil.rmtree(LIVE)",
              "    shutil.copytree(SNAP, LIVE); print('restored', LIVE)",
              "elif os.path.isdir(LIVE):",                    # folder was absent before -> the install created it
              "    shutil.rmtree(LIVE); print('removed', LIVE)",
              "else:",
              "    print('nothing to revert:', LIVE)",
              ""]
        p = reverts_dir / "revert_install.py"
        p.write_text("\n".join(rl), encoding="utf-8")
        return p
    except OSError:                                           # a copy/write failure -> no undo (caller warns)
        return None


# --------------------------------------------------------------------------- deploy / revert argv
# Each returns a FULL argv whose [0] is the interpreter, so a QProcess can split it into
# program=argv[0], arguments=argv[1:], and a subprocess can run it as-is.
def _tool(repo_root, *parts):
    """A path under the RUNNING checkout's ``tools/`` -- the deploy SCRIPTS. Undo artifacts do not live
    here: they resolve through :func:`scroll_out_dir` (the main repo), matching what the scripts do."""
    return str(Path(repo_root, "tools", *parts))


def revert_install_argv(repo_root):
    """The interpreter + the Install-to-game revert script (dev repo: ``tools/scroll_out/revert_install.py``),
    or ``None`` if no install has been snapshotted yet."""
    p = scroll_out_dir(repo_root) / "revert_install.py"
    return [sys.executable, str(p)] if p.is_file() else None


def revert_install_pkg_argv():
    """The installed-copy Install-to-game revert (the per-user cache's ``revert_install.py``), or ``None``."""
    p = _cache_revert("revert_install.py")
    return [sys.executable, str(p)] if p else None


def build_argv(field, out, *, mod_name="FF9CustomMap", preserve_existing=False):
    """``ff9mapkit build`` a single field.toml into ``out`` (the 'build only' target, no deploy).

    ``preserve_existing`` is for INSTALLING into a shipping mod folder that already holds other fields:
    a build writes the whole DictionaryPatch, so without it the other fields would be unregistered
    (their files would stay, and the engine would black-screen on them)."""
    a = [sys.executable, "-m", "ff9mapkit", "build", str(field), "--out", str(out),
         "--mod-name", mod_name]
    return a + ["--preserve-existing"] if preserve_existing else a


def build_campaign_argv(path):
    """``ff9mapkit build-all`` -- compile every member of a campaign into its dist/ (no deploy)."""
    return [sys.executable, "-m", "ff9mapkit", "build-all", str(path)]


def pack_argv(mod_root, out_zip, *, name=None):
    """``ff9mapkit pack`` -- zip a built mod folder for distribution. ``name`` = the mod-folder name
    INSIDE the zip (what Memoria.ini FolderNames will call it) when the staged folder is a dist/."""
    a = [sys.executable, "-m", "ff9mapkit", "pack", str(mod_root), "--out", str(out_zip)]
    if name:
        a += ["--name", str(name)]
    return a


def deploy_field_argv(repo_root, field):
    """Reversibly deploy a field.toml into this worktree's test slot (``tools/deploy_field.py``)."""
    return [sys.executable, _tool(repo_root, "deploy_field.py"), str(field)]


def deploy_field_own_id_argv(repo_root, field, field_id, name):
    """Reversibly deploy a field at its OWN id and name: ``deploy_field.py <field> --id <id> --name <name>``.

    The gap this fills: the test slot is reversible but overrides the field's id, and the game install
    uses the real id but is a wholesale ``build`` with no revert script. This is both -- the field lands
    where it declares, and the deploy backs up the DictionaryPatch, merges into it (other fields keep
    their registrations) and writes a per-id ``revert_deploy_<id>.py``.

    ``--name`` is REQUIRED here: without it deploy_field sandboxes the name to ``TEST<id>``, which is
    right for a throwaway slot and wrong for a field installed under its own identity."""
    return [sys.executable, _tool(repo_root, "deploy_field.py"), str(field),
            "--id", str(field_id), "--name", str(name)]


def deploy_field_inplace_argv(repo_root, field, target):
    """Reversibly deploy a verbatim fork IN PLACE on its donor id (``target`` from
    :func:`field_inplace_target`): ``deploy_field.py <field> --id <donor> --name <name> --text-block <tb>``.
    The mod folder defaults from ``.ff9deploy.toml`` (the worktree's reversible test folder). Overriding
    ``--id`` to the donor + keeping its registered text block is what makes the engine load this in place of
    the real field (and keeps the Chocobo HUD, which is hardcoded on the donor id + zone 945)."""
    return [sys.executable, _tool(repo_root, "deploy_field.py"), str(field),
            "--id", str(target["donor"]), "--name", str(target["name"]),
            "--text-block", str(target["text_block"])]


def deploy_campaign_argv(repo_root, path, *, wire_newgame=False, mod_folder=None):
    """Reversibly deploy a whole campaign (``tools/deploy_campaign.py --apply``). ``mod_folder`` pins the
    install target to the campaign's DECLARED folder (``plan.mod_folder``) -- without it the tool falls back
    to ``.ff9deploy.toml``/``FF9CustomMap``, which can silently disagree with the folder the UI labels + the
    post-deploy "add to FolderNames" hint name (the dev-path analogue of the pkg path's mod_folder pass)."""
    a = [sys.executable, _tool(repo_root, "deploy_campaign.py"), str(path), "--apply"]
    if mod_folder:
        a += ["--mod-folder", str(mod_folder)]
    if not wire_newgame:
        a.append("--no-warp")
    return a


def deploy_battle_argv(repo_root, battle, *, trigger=None):
    """Reversibly deploy a battle map (``tools/deploy_battle.py``), optionally repointing a trigger field."""
    a = [sys.executable, _tool(repo_root, "deploy_battle.py"), str(battle)]
    if trigger:
        a += ["--trigger-field", str(trigger)]
    return a


def fork_command_argv(command, *, out_abs=None):
    """Turn a reference-arc playbook line (``import-chain <seed> --out <key> ...``, from
    :func:`..refarc.parse_fork_commands`) into a runnable argv: ``[python, -m, ff9mapkit, import-chain, ...]``.
    With ``out_abs`` the ``--out`` value is rewritten to that absolute path, so the fork can run from the kit
    root (the local-package shadow) yet still land the campaign folder beside the journeys.toml."""
    import shlex
    parts = shlex.split(str(command))
    if out_abs is not None and "--out" in parts:
        i = parts.index("--out")
        if i + 1 < len(parts):
            parts[i + 1] = str(out_abs)
    return [sys.executable, "-m", "ff9mapkit", *parts]


def deploy_journey_argv(repo_root, journeys, *, apply=False, newgame="none", wire_newgame=False, apply_links=False,
                        single_folder=False):
    """Deploy (or dry-run) a multi-campaign journey manifest via ``tools/deploy_journey.py``.

    Default (no flags) = a DRY-RUN that lints + prints the ordered deploy playbook (no game files touched).
    ``apply`` = the ONE-SHOT deploy (every campaign into its own stacked folder, the cross-campaign links,
    then the hub field -- one unified revert). ``newgame`` (gated under ``--apply``) chooses where New Game
    lands -- SINGLE-OWNER, replaces the current target: ``"none"`` (unchanged, reach the hub via the debug menu (~)), ``"hub"``
    (the hub selector menu, seamless), or ``"entry"`` (STRAIGHT into the opening field, no menu -- single-journey
    only; keeps the real opening FMV). ``wire_newgame=True`` is a back-compat alias for ``newgame="hub"``.
    ``apply_links`` = re-apply ONLY the cross-campaign link ``.eb`` remaps (run after a campaign re-deploy).
    ``single_folder`` (with ``apply``) = MERGE the whole journey into ONE stacked mod folder (a single
    FolderNames entry) instead of one folder per campaign."""
    mode = newgame if (newgame and newgame != "none") else "none"
    a = [sys.executable, _tool(repo_root, "deploy_journey.py"), str(journeys)]
    if apply:
        a.append("--apply")
        if single_folder:
            a.append("--single-folder")
        if mode != "none":
            a += ["--newgame", mode]
        elif wire_newgame:                    # back-compat alias (deploy_journey maps --wire-newgame -> hub)
            a.append("--wire-newgame")
    elif apply_links:
        a.append("--apply-links")
    return a


# ---- installed-copy deploy (no repo tools/): the package CLI + a per-user revert cache ----
# An installed wheel ships no tools/, so the Workspace routes campaign/journey deploys through the package
# CLI commands (ff9mapkit deploy-campaign / deploy-journey) instead of the tool scripts. Their snapshots +
# revert scripts land in provision.deploy_reverts_dir() (a per-user cache), which the Revert button reads.
def deploy_campaign_pkg_argv(path, *, wire_newgame=False, mod_folder="FF9CustomMap"):
    """`ff9mapkit deploy-campaign <path> --apply` -- the installed-copy campaign deploy (no repo tools)."""
    a = [sys.executable, "-m", "ff9mapkit", "deploy-campaign", str(path), "--apply",
         "--mod-folder", str(mod_folder)]
    if not wire_newgame:
        a.append("--no-warp")
    return a


def deploy_journey_pkg_argv(path, *, apply=False, newgame="none", apply_links=False, single_folder=False):
    """`ff9mapkit deploy-journey <path> [...]` -- the installed-copy journey deploy/dry-run (no repo tools)."""
    a = [sys.executable, "-m", "ff9mapkit", "deploy-journey", str(path)]
    if apply:
        a.append("--apply")
        if single_folder:
            a.append("--single-folder")
        if newgame and newgame != "none":
            a += ["--newgame", newgame]
    elif apply_links:
        a.append("--apply-links")
    return a


def _cache_revert(name):
    """The per-user-cache revert script an installed-copy deploy wrote (deploy_reverts_dir/<name>), or None."""
    try:
        from .. import provision
        p = provision.deploy_reverts_dir() / name
        return p if p.is_file() else None
    except Exception:
        return None


def revert_campaign_pkg_argv():
    p = _cache_revert("revert_campaign.py")
    return [sys.executable, str(p)] if p else None


def revert_journey_pkg_argv():
    p = _cache_revert("revert_journey.py")
    return [sys.executable, str(p)] if p else None


def newgame_from_stock_pkg_argv(field_id, *, mod_folder="FF9CustomMap"):
    """`ff9mapkit newgame <id>` -- point New Game at a deployed field (create the field-70 override from
    stock). The installed-copy equivalent of tools/wire_newgame_from_stock.py."""
    return [sys.executable, "-m", "ff9mapkit", "newgame", str(field_id), "--mod-folder", str(mod_folder)]


def revert_newgame_pkg_argv():
    """The most-recent installed-copy New-Game revert (from-stock or retarget) in the per-user cache, or None."""
    try:
        from .. import provision
        rv = provision.deploy_reverts_dir()
        cands = [p for p in (rv / "revert_newgame_from_stock.py", rv / "revert_newgame_retarget.py") if p.is_file()]
        if not cands:
            return None
        return [sys.executable, str(max(cands, key=lambda x: x.stat().st_mtime))]
    except Exception:
        return None


def revert_field_argv(repo_root, field_id=None):
    """Undo a field deploy. Without ``field_id`` this is the LATEST deploy (``revert_deploy.py``, whatever
    id it targeted); with one it is that id's own script (``revert_deploy_<id>.py``), which deploy_field
    writes per id -- so reverting field 4008 cannot undo someone else's later 4003 deploy instead."""
    scroll = scroll_out_dir(repo_root)
    if field_id is not None:
        per_id = scroll / f"revert_deploy_{int(field_id)}.py"
        if per_id.is_file():
            return [sys.executable, str(per_id)]
    return [sys.executable, str(scroll / "revert_deploy.py")]


def revert_campaign_argv(repo_root):
    return [sys.executable, str(scroll_out_dir(repo_root) / "revert_campaign.py")]


def revert_journey_argv(repo_root):
    """The interpreter + the MOST RECENT journey revert script (the unified ``revert_journey.py`` from a full
    ``--apply``, or the links-only ``revert_journey_links.py`` from ``--apply-links``), or ``None`` if no
    journey deploy is undoable yet. Picking by mtime (like :func:`revert_battle_argv`) means the GUI Revert
    undoes the user's LAST journey action, never a stale earlier unified revert."""
    s = latest_journey_revert(repo_root)
    return [sys.executable, str(s)] if s else None


def newgame_from_stock_argv(repo_root, field_id, *, mod_folder="FF9CustomMap"):
    """Point New Game at a deployed field id by CREATING the field-70 override from STOCK
    (``tools/wire_newgame_from_stock.py``) -- the robust path: it extracts stock field 70, repoints its
    terminal ``Field(50)``->``Field(<id>)`` (all 7 langs, the opening FMV+fade preserved), and works even when
    NO override exists yet (a clean install, or after a fresh wholesale campaign deploy wiped it). This is the
    disc-1-proven New-Game wiring; the patch-only :func:`newgame_retarget_argv` no-ops when there's nothing to
    patch. Reversible (writes ``revert_newgame_from_stock.py``).

    ``mod_folder`` MUST match the folder the wholesale deploy wiped (the tool defaults it to FF9CustomMap):
    a re-wire that lands in FF9CustomMap after a campaign whose ``mod_folder`` is something else restores the
    override in the WRONG folder. Mirrors :func:`newgame_from_stock_pkg_argv` and the tool's --mod-folder."""
    return [sys.executable, _tool(repo_root, "wire_newgame_from_stock.py"), str(field_id),
            "--mod-folder", str(mod_folder)]


def newgame_retarget_argv(repo_root, field_id):
    """Point New Game straight at a deployed field id by PATCHING an existing field-70 override
    (``tools/retarget_newgame_warp.py``). NO-OPS when no override exists -- prefer
    :func:`newgame_from_stock_argv` (create-from-stock) for a fresh fork. Reversible."""
    return [sys.executable, _tool(repo_root, "retarget_newgame_warp.py"), str(field_id)]


def latest_newgame_revert(repo_root):
    """The most-recent New-Game revert script -- the create-from-stock ``revert_newgame_from_stock.py`` OR the
    patch ``revert_newgame_retarget.py`` -- by mtime (like :func:`latest_journey_revert`), or ``None``. So the
    GUI Revert undoes whichever New-Game action ran LAST, regardless of which wiring tool wrote it."""
    scroll = scroll_out_dir(repo_root)
    cands = [p for p in (scroll / "revert_newgame_from_stock.py", scroll / "revert_newgame_retarget.py")
             if p.is_file()]
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None


def revert_newgame_argv(repo_root):
    """The interpreter + the most-recent New-Game revert script (from-stock or retarget), or ``None``."""
    s = latest_newgame_revert(repo_root)
    return [sys.executable, str(s)] if s else None


def revert_battle_argv(repo_root):
    """The interpreter + the latest ``revert_battle_*.py``, or ``None`` if no battle deploy to undo."""
    s = latest_battle_revert(repo_root)
    return [sys.executable, str(s)] if s else None


def coop_setup_argv(action, code=None, *, lan=None, new_code=False, rebuild_room=False,
                    guest_slots=None, guest_wait=None, ghost_as=None, follow_host=None):
    """``ff9mapkit coop host|join`` argv, setup only (``--no-bridge`` -- the GUI runs the bridge
    in-process). ``lan``: None = relay mode; ``""`` = bare ``--lan`` (host); an IP = ``--lan <ip>`` (join).
    The play-style knobs (s37) pass through when not None: ``guest_slots`` a human slot spec
    ('none'/'2'/'2,3'), ``guest_wait`` seconds, ``ghost_as`` off/auto/name, ``follow_host`` a bool.
    (The ``--diorama`` knob was removed with the s42 engine -- the diorama is always-on.)"""
    a = [sys.executable, "-m", "ff9mapkit", "coop", str(action)]
    if code:
        a.append(str(code))
    a.append("--no-bridge")
    if lan is not None:
        a += ["--lan"] if lan == "" else ["--lan", str(lan)]
    if new_code:
        a.append("--new-code")
    if rebuild_room:
        a.append("--rebuild-room")
    if guest_slots is not None:
        a += ["--guest-slots", str(guest_slots)]
    if guest_wait is not None:
        a += ["--guest-wait", str(int(guest_wait))]
    if ghost_as is not None:
        a += ["--ghost-as", str(ghost_as)]
    if follow_host is not None:
        a += ["--follow-host", "on" if follow_host else "off"]
    return a
