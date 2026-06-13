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
    """``('campaign', plan)`` | ``('battle', None)`` | ``('field', None)`` for the picked file.

    A campaign.toml has a ``[campaign]`` table (``load_campaign`` raises on anything else); a battle.toml
    has a ``[battlemap]`` table; else it's a field.toml -- the cheap, exact discriminators (mirrors the
    tkinter Build GUI)."""
    try:
        from ..campaign import load_campaign
        return "campaign", load_campaign(path)
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


def revert_field_argv(repo_root):
    return [sys.executable, _tool(repo_root, "scroll_out", "revert_deploy.py")]


def revert_campaign_argv(repo_root):
    return [sys.executable, _tool(repo_root, "scroll_out", "revert_campaign.py")]


def revert_battle_argv(repo_root):
    """The interpreter + the latest ``revert_battle_*.py``, or ``None`` if no battle deploy to undo."""
    s = latest_battle_revert(repo_root)
    return [sys.executable, str(s)] if s else None
