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

_DEFAULTS = {"theme": "auto", "recent": [], "density": "comfortable"}

RECENT_KINDS = ("journey", "campaign", "field", "save")   # the openable project kinds an MRU row can hold
RECENT_LIMIT = 10
DENSITIES = ("comfortable", "compact")                    # UI density: roomy (default) vs tight (power-user)


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


def density() -> str:
    """The saved UI density: ``"comfortable"`` (roomy, the default) or ``"compact"`` (tight). Type-disciplined
    -- a corrupt/unknown value degrades to the default."""
    val = get("density", "comfortable")
    return val if val in DENSITIES else "comfortable"


def set_density(mode: str) -> None:
    put("density", mode if mode in DENSITIES else "comfortable")


def guided() -> bool:
    """Beginner mode: True = Guided (expert form fields tuck into a per-form 'Advanced' drawer, the default),
    False = Full (every field inline). Nothing is ever removed -- Guided only tucks. Default True."""
    return get("guided", True) is not False


def set_guided(on: bool) -> None:
    put("guided", bool(on))


# CALIBRE -- the text-size dial, as INTEGER PERCENTS (never floats: this round-trips through JSON, and a
# 1.1 that reads back as 1.1000000000000001 would make the byte-identity gate at 100% flap).
#
# Why an in-app dial rather than following Windows: THE APP CANNOT FOLLOW WINDOWS. The Accessibility ->
# Text size slider writes HKCU\Software\Microsoft\Accessibility\TextScaleFactor and does NOT touch
# NONCLIENTMETRICS.lfMessageFont, which is where Qt reads its font -- verified by setting the key to 150,
# broadcasting WM_SETTINGCHANGE, and watching lfMessageFont stay at -12 Segoe UI. The string
# TextScaleFactor appears in ZERO of the 338 DLLs Qt ships. No Qt app on the desktop tracks that slider.
# (Display -> Scale is a different setting and the app already honours it correctly: QSS px are LOGICAL
# px, multiplied by devicePixelRatio. That part was never broken.)
# So: the only text-only lever that can exist on Windows is one we ship. This is it.
#
# THE PRICE, MEASURED AND NOT HIDDEN (evidence/probe_toolbar_budget.py, at a REAL asserted 1280px window):
# the toolbar is tight, and bigger text pushes items into Qt's extension chevron, where they are reachable
# but INVISIBLE -- 15/15 at 100%, 14/15 at 110%, 13/15 at 125%, 11/15 at 150%. At 1600px and above,
# every scale is 15/15. That is a real cost and it is judged worth paying: a user who turns text up has
# said they want bigger text more than they want a dense toolbar, the items stay reachable via the
# chevron AND via Ctrl-K, and the a11y suite already fences graceful toolbar overflow as the app's
# accepted behaviour at narrow widths. It is NOT silent -- it is written here.
# Everything else is clean: audited natively at all four scales, nothing else in the app clips
# (evidence/audit_text_scale.py). The one surface the dial deliberately does not move is the hero band,
# which paints with QPainter at hard pixel sizes that no stylesheet reaches -- that is PLINTH, unbuilt.
TEXT_SCALES = (100, 110, 125, 150)


def text_scale() -> int:
    """The saved text-size percent -- one of :data:`TEXT_SCALES`, default 100. Type-disciplined: a corrupt
    or hand-edited value degrades to 100 (which is the provably-inert setting)."""
    val = get("text_scale", 100)
    return val if val in TEXT_SCALES else 100


def set_text_scale(pct: int) -> None:
    put("text_scale", pct if pct in TEXT_SCALES else 100)


MOTIONS = ("auto", "on", "off")                           # UI motion: follow the OS / always / never


def motion() -> str:
    """The UI-motion preference: ``"auto"`` (follow the OS reduce-motion setting, the default), ``"on"``, or
    ``"off"``. Type-disciplined -- a corrupt/unknown value degrades to ``"auto"``."""
    val = get("motion", "auto")
    return val if val in MOTIONS else "auto"


def set_motion(mode: str) -> None:
    put("motion", mode if mode in MOTIONS else "auto")


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
    """The saved window layout: ``{"geometry": b64, "state": b64, "central_split": [ints],
    "console_split": [ints], "console_collapsed": bool}`` — any subset; garbage-tolerant like every pref
    (a corrupt value is just dropped)."""
    val = get("layout", {})
    if not isinstance(val, dict):
        return {}
    out = {}
    for k in ("geometry", "state"):
        if isinstance(val.get(k), str) and val[k]:
            out[k] = val[k]
    for k in ("central_split", "console_split"):
        sizes = val.get(k)
        if isinstance(sizes, list) and sizes and all(isinstance(x, int) and x >= 0 for x in sizes):
            out[k] = sizes
    if val.get("console_collapsed") is True:
        out["console_collapsed"] = True
    return out


def set_layout(d: dict) -> None:
    put("layout", d)
