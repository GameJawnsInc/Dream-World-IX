"""Small persistent UI preferences for the Workspace (currently: the chosen theme).

stdlib-only, NEVER raises to the caller (an unreadable/corrupt file degrades to defaults). Stored as JSON
in the per-user config dir -- the same place :mod:`.update_check` keeps its state -- so the choice SURVIVES
a ``uv tool upgrade`` (which wipes the package's own ``data/``). A SEPARATE file from ``update_check.json``
(that one owns the update-check opt-in); these settings are independent.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import provision

_DEFAULTS = {"theme": "auto"}


def _path() -> Path:
    return provision._user_dir("config") / "prefs.json"


def load() -> dict:
    try:
        d = json.loads(_path().read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def save(d: dict) -> None:
    try:
        p = _path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(d, indent=2), encoding="utf-8")
    except OSError:
        pass


def get(key: str, default=None):
    """Read one preference, falling back to its built-in default then ``default``."""
    return load().get(key, _DEFAULTS.get(key, default))


def put(key: str, value) -> None:
    """Write one preference (read-modify-write, so unrelated keys are preserved)."""
    d = load()
    d[key] = value
    save(d)


def theme() -> str:
    """The saved theme mode (a key in :data:`.editor.theme.THEMES`, or ``"auto"``). Default ``"auto"``."""
    val = get("theme", "auto")
    return val if isinstance(val, str) and val else "auto"


def set_theme(mode: str) -> None:
    put("theme", mode)
