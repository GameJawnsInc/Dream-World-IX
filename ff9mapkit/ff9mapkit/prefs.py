"""Small persistent UI preferences for the Workspace (the chosen theme + the recent-projects list).

stdlib-only, NEVER raises to the caller (an unreadable/corrupt file degrades to defaults). Stored as JSON
in the per-user config dir -- the same place :mod:`.update_check` keeps its state -- so the choice SURVIVES
a ``uv tool upgrade`` (which wipes the package's own ``data/``). A SEPARATE file from ``update_check.json``
(that one owns the update-check opt-in); these settings are independent.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import provision

_DEFAULTS = {"theme": "auto", "recent": []}

RECENT_KINDS = ("journey", "campaign", "field", "save")   # the openable project kinds an MRU row can hold
RECENT_LIMIT = 10


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
        tmp = p.with_name(p.name + ".tmp")         # atomic: a crash mid-write must not wipe theme + MRU
        tmp.write_text(json.dumps(d, indent=2), encoding="utf-8")
        tmp.replace(p)
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


def recent() -> list:
    """The recent-projects list, most recent first: ``[{"kind": k, "path": p}, ...]`` with ``kind`` in
    :data:`RECENT_KINDS`. Type-disciplined like :func:`theme`: a hand-edited/corrupt file can hold anything,
    so every entry is validated and garbage is dropped (never raises)."""
    val = get("recent", [])
    if not isinstance(val, list):
        return []
    out = []
    for e in val:
        if (isinstance(e, dict) and e.get("kind") in RECENT_KINDS
                and isinstance(e.get("path"), str) and e["path"]):
            out.append({"kind": e["kind"], "path": e["path"]})
    return out[:RECENT_LIMIT]


def add_recent(kind: str, path) -> None:
    """Record an opened project at the FRONT of the recent list (deduped by path, capped at
    :data:`RECENT_LIMIT`). ``path`` is resolved so dialog-relative strings compare equal later."""
    if kind not in RECENT_KINDS:
        return
    try:
        p = str(Path(path).resolve())
    except OSError:
        p = str(path)
    rows = [e for e in recent() if e["path"] != p]
    rows.insert(0, {"kind": kind, "path": p})
    put("recent", rows[:RECENT_LIMIT])


def remove_recent(path) -> None:
    """Drop one path from the recent list (e.g. the file no longer exists)."""
    p = str(path)
    put("recent", [e for e in recent() if e["path"] != p])


def restore_session() -> bool:
    """Opt-in: reopen the most recent project on launch. Default False."""
    return get("restore_session", False) is True


def set_restore_session(on: bool) -> None:
    put("restore_session", bool(on))


def layout() -> dict:
    """The saved window layout: ``{"geometry": b64, "state": b64, "central_split": [ints]}`` — any subset;
    garbage-tolerant like every pref (a corrupt value is just dropped)."""
    val = get("layout", {})
    if not isinstance(val, dict):
        return {}
    out = {}
    for k in ("geometry", "state"):
        if isinstance(val.get(k), str) and val[k]:
            out[k] = val[k]
    cs = val.get("central_split")
    if isinstance(cs, list) and cs and all(isinstance(x, int) and x >= 0 for x in cs):
        out["central_split"] = cs
    return out


def set_layout(d: dict) -> None:
    put("layout", d)
