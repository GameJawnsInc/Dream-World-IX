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


def latest_battle_revert(repo_root):
    """The most recently written ``tools/scroll_out/revert_battle_*.py``, or ``None``."""
    scroll = Path(repo_root) / "tools" / "scroll_out"
    scripts = sorted(scroll.glob("revert_battle_*.py"), key=lambda p: p.stat().st_mtime, reverse=True)
    return scripts[0] if scripts else None


def latest_journey_revert(repo_root):
    """The most recently written journey revert script, or ``None``.

    A journey deploy writes ONE of two reverts depending on the mode: the full ``--apply`` one-shot writes the
    unified ``revert_journey.py``; a standalone ``--apply-links`` writes only ``revert_journey_links.py``. The
    GUI Revert button must undo the user's LAST journey action, so we pick the most-recently-modified of the
    two (mirrors :func:`latest_battle_revert`) -- never a stale unified revert left over from an earlier run."""
    scroll = Path(repo_root) / "tools" / "scroll_out"
    cands = [p for p in (scroll / "revert_journey.py", scroll / "revert_journey_links.py") if p.is_file()]
    return max(cands, key=lambda p: p.stat().st_mtime) if cands else None


# --------------------------------------------------------------------------- import argv (FFIX Import)
def import_args(field, *, out, field_id, name=None, art="native", carry_npcs=True, carry_text=True,
                dialogue_stubs=False, save_moogle=False):
    """The ``ff9mapkit import ...`` argv for a field fork (no ``py -m ff9mapkit`` prefix).

    ``art`` is 'native' (--native) / 'borrow' (neither flag) / 'editable' (--editable). The carry flags
    map to the fidelity options; --carry-text and --save-moogle both imply --graft-player-funcs (which the
    kit also enforces), so we pass it explicitly when any carry is on for the command to read honestly."""
    args = ["import", str(field), "--out", str(out), "--id", str(field_id)]
    if name:
        args += ["--name", str(name)]
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


# --------------------------------------------------------------------------- deploy / revert argv
# Each returns a FULL argv whose [0] is the interpreter, so a QProcess can split it into
# program=argv[0], arguments=argv[1:], and a subprocess can run it as-is.
def _tool(repo_root, *parts):
    return str(Path(repo_root, "tools", *parts))


def build_argv(field, out, *, mod_name="FF9CustomMap"):
    """``ff9mapkit build`` a single field.toml into ``out`` (the 'build only' target, no deploy)."""
    return [sys.executable, "-m", "ff9mapkit", "build", str(field), "--out", str(out),
            "--mod-name", mod_name]


def build_campaign_argv(path):
    """``ff9mapkit build-all`` -- compile every member of a campaign into its dist/ (no deploy)."""
    return [sys.executable, "-m", "ff9mapkit", "build-all", str(path)]


def deploy_field_argv(repo_root, field):
    """Reversibly deploy a field.toml into this worktree's test slot (``tools/deploy_field.py``)."""
    return [sys.executable, _tool(repo_root, "deploy_field.py"), str(field)]


def deploy_campaign_argv(repo_root, path, *, wire_newgame=False):
    """Reversibly deploy a whole campaign (``tools/deploy_campaign.py --apply``)."""
    a = [sys.executable, _tool(repo_root, "deploy_campaign.py"), str(path), "--apply"]
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


def deploy_journey_argv(repo_root, journeys, *, apply=False, wire_newgame=False, apply_links=False):
    """Deploy (or dry-run) a multi-campaign journey manifest via ``tools/deploy_journey.py``.

    Default (no flags) = a DRY-RUN that lints + prints the ordered deploy playbook (no game files touched).
    ``apply`` = the ONE-SHOT deploy (every campaign into its own stacked folder, the cross-campaign links,
    then the hub field -- one unified revert); ``wire_newgame`` additionally points New Game at the hub
    (single-owner, so it's gated under ``--apply`` -- a no-op alone). ``apply_links`` = re-apply ONLY the
    cross-campaign link ``.eb`` remaps (run after a campaign re-deploy wipes them)."""
    a = [sys.executable, _tool(repo_root, "deploy_journey.py"), str(journeys)]
    if apply:
        a.append("--apply")
        if wire_newgame:
            a.append("--wire-newgame")
    elif apply_links:
        a.append("--apply-links")
    return a


def revert_field_argv(repo_root):
    return [sys.executable, _tool(repo_root, "scroll_out", "revert_deploy.py")]


def revert_campaign_argv(repo_root):
    return [sys.executable, _tool(repo_root, "scroll_out", "revert_campaign.py")]


def revert_journey_argv(repo_root):
    """The interpreter + the MOST RECENT journey revert script (the unified ``revert_journey.py`` from a full
    ``--apply``, or the links-only ``revert_journey_links.py`` from ``--apply-links``), or ``None`` if no
    journey deploy is undoable yet. Picking by mtime (like :func:`revert_battle_argv`) means the GUI Revert
    undoes the user's LAST journey action, never a stale earlier unified revert."""
    s = latest_journey_revert(repo_root)
    return [sys.executable, str(s)] if s else None


def newgame_retarget_argv(repo_root, field_id):
    """Point New Game straight at a deployed field id (``tools/retarget_newgame_warp.py``) -- the hub-less
    single-destination entry. SINGLE-OWNER: it replaces the current New-Game landing; the field must already
    be registered (deployed), and the game must relaunch to pick it up. Reversible (writes a revert script)."""
    return [sys.executable, _tool(repo_root, "retarget_newgame_warp.py"), str(field_id)]


def revert_newgame_argv(repo_root):
    """The interpreter + ``tools/scroll_out/revert_newgame_retarget.py`` (written by the New-Game retarget)."""
    return [sys.executable, _tool(repo_root, "scroll_out", "revert_newgame_retarget.py")]


def revert_battle_argv(repo_root):
    """The interpreter + the latest ``revert_battle_*.py``, or ``None`` if no battle deploy to undo."""
    s = latest_battle_revert(repo_root)
    return [sys.executable, str(s)] if s else None
