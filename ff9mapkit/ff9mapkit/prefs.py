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

_DEFAULTS = {"theme": "mist", "recent": [], "density": "comfortable"}

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
    """The saved theme mode (a key in :data:`.editor.theme.THEMES`, or ``"auto"``). Default ``"mist"`` (the
    FF9 climate) -- ``"auto"`` (match system) is still one click away in the picker, it is just no longer
    what a fresh install paints."""
    val = get("theme", "mist")
    return val if isinstance(val, str) and val else "mist"


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
# (evidence/audit_text_scale.py). The hero band moves too -- it paints with QPainter at sizes no
# stylesheet reaches, so it has to be TOLD; that is PLINTH, and it shipped.
TEXT_SCALES = (100, 110, 125, 150)


def os_text_scale() -> int:
    """Windows' Accessibility -> Text size, snapped to a rung we ship. 100 if unset or unreadable.

    HEED. Qt cannot see this slider (see the note above: it never reaches lfMessageFont, and the string
    appears in zero of Qt's DLLs) -- but PYTHON can, because it is just a registry value. So the app reads
    what Qt refuses to, and uses it to SEED the dial's default: someone who has already told Windows they
    want 150% text gets it on first launch, with no preference to discover.

    Pure + defensive, and modelled on a sibling that already ships: ``theme.detect_os_dark`` is the same
    shape -- an HKCU read wrapped in a bare except that degrades to the safe default. This is not a new
    pattern in this codebase, which is most of why it is defensible.

    SNAPPED TO NEAREST, and clamped by our own top rung. Microsoft documents the range as [100, 225]; we
    ship (100, 110, 125, 150). Windows' common stops (100/125/150) land exactly; 175/200/225 all clamp to
    150, which is the honest answer -- we cannot offer more than we ship, and the in-app dial is still
    there to be turned. NEAREST rather than snap-down because this is an ACCESSIBILITY seed: under-serving
    someone who asked for bigger text is the wrong direction to err, and it is a default, not a mandate.
    """
    try:
        import winreg

        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Accessibility")
        try:
            value, _ = winreg.QueryValueEx(key, "TextScaleFactor")
        finally:
            winreg.CloseKey(key)
        pct = int(value)
    except Exception:       # noqa: BLE001  (non-Windows / no winreg / key absent / junk value) -> inert
        return 100
    pct = max(100, min(225, pct))                     # the documented range; junk outside it is not obeyed
    return min(TEXT_SCALES, key=lambda s: (abs(s - pct), s))


def text_scale() -> int:
    """The text-size percent -- one of :data:`TEXT_SCALES`.

    AN EXPLICIT CHOICE ALWAYS WINS, and that ordering is the whole feature. A saved value means the user
    has been to Preferences and said what they want; Windows does not get to override that, ever. Only
    when nothing is saved does HEED seed the default from the OS slider (:func:`os_text_scale`) -- so the
    seed is a better FIRST GUESS, never a correction of a decision already made.

    Type-disciplined: a corrupt or hand-edited value degrades to the seed rather than to a bare 100, for
    the same reason -- a broken file should not silently cost a low-vision user their text size.
    """
    saved = load().get("text_scale")
    if saved in TEXT_SCALES:
        return saved
    return os_text_scale()


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


def getstarted_hidden() -> bool:
    """True once the user clicked Hide on Home's 'Get started' guide. Default False. Hiding is a USER
    choice and wins even while setup is incomplete (the Home setup banner remains the fail-safe there);
    the guide also hides ITSELF once the user is genuinely past it -- see shell._getstarted_show."""
    return get("getstarted_hidden", False) is True


def set_getstarted_hidden(on: bool) -> None:
    put("getstarted_hidden", bool(on))


def restore_session() -> bool:
    """Reopen the most recent project on launch. Default True -- the returning veteran picks up exactly
    where they left off, and F9 is live on restore. Newcomers are untouched: :meth:`shell.restore_last_session`
    no-ops on an empty recent list, so a fresh install with nothing to reopen sees no behavior change.
    Type-disciplined like :func:`guided` (also default-True): only an explicit ``False`` opts out; an absent
    key or a corrupt value degrades to the default (ON)."""
    return get("restore_session", True) is not False


def set_restore_session(on: bool) -> None:
    put("restore_session", bool(on))


def confirm_reversible_deploys() -> bool:
    """Whether a REVERSIBLE deploy (the test slot / an in-place fork) still pops a confirm modal before it
    runs. Default False -- F9 is a true one-keystroke loop, matching the 'reversible' labelling and Revert's
    one-click undo; the confirm can be opted back IN in Preferences. Install-to-game and the wholesale
    campaign/journey deploys keep their unconditional confirm regardless of this pref."""
    return get("confirm_reversible_deploys", False) is True


def set_confirm_reversible_deploys(on: bool) -> None:
    put("confirm_reversible_deploys", bool(on))


def raise_game_after_deploy() -> bool:
    """Bring the running FF9 window to the front after a successful deploy (ask-user #16). Default
    OFF -- focus-stealing is intrusive as a default; the veteran who lives in the F9 -> ~ loop opts in
    via Preferences. Raise/flash only, never synthetic input (the chair's ruling). Type-disciplined:
    only an explicit ``True`` opts in."""
    return get("raise_game_after_deploy", False) is True


def set_raise_game_after_deploy(on: bool) -> None:
    put("raise_game_after_deploy", bool(on))


def has_deployed() -> bool:
    """The sticky first-deploy marker: True once the user has ever deployed. Default False; latched True
    on the first successful deploy and never unset. The first-run READY spine reads it to stop pointing a
    newcomer at Deploy once they've found it (silent forever after)."""
    return get("has_deployed", False) is True


def set_has_deployed(on: bool) -> None:
    """Set the first-deploy marker. A one-way latch in practice (only ever called with True)."""
    put("has_deployed", bool(on))


# The Build & Deploy destination radio, remembered across sessions so a veteran's workflow (e.g. "deploy
# at its own id") survives an open/relaunch instead of hard-resetting to the has_tools default every time.
# 'inplace' is DELIBERATELY excluded -- it is donor-driven and auto-selects for a verbatim fork of a real
# field, so persisting it would fight that auto-selection. Only a radio the USER clicked is stored.
DEPLOY_DESTS = ("test", "own", "game", "other")


def deploy_dest() -> str | None:
    """The saved Build & Deploy destination mode -- one of :data:`DEPLOY_DESTS`, or ``None`` when the user
    has never pinned one (fall back to the has_tools default). Type-disciplined: a corrupt/unknown value
    (incl. the non-persistable ``"inplace"``) reads as ``None``."""
    val = get("deploy_dest", None)
    return val if val in DEPLOY_DESTS else None


def set_deploy_dest(mode: str) -> None:
    """Remember the destination the user CLICKED. Only the four persistable modes are stored; anything
    else (incl. ``"inplace"``) is ignored, so the auto-selecting In-place fork route never becomes a
    sticky global preference."""
    if mode in DEPLOY_DESTS:
        put("deploy_dest", mode)


def layout() -> dict:
    """The saved window layout: ``{"geometry": b64, "state": b64, "central_split": [ints],
    "console_split": [ints], "floorplan_split": [ints], "console_collapsed": bool}`` — any subset;
    garbage-tolerant like every pref (a corrupt value is just dropped)."""
    val = get("layout", {})
    if not isinstance(val, dict):
        return {}
    out = {}
    for k in ("geometry", "state"):
        if isinstance(val.get(k), str) and val[k]:
            out[k] = val[k]
    # ARITY IS PART OF "CORRUPT", and this docstring promised to drop corrupt values while never checking
    # it. `{"console_split": [1]}` is a list, non-empty, all ints, all >= 0 -- so it passed, was STORED,
    # and detonated later at an unguarded `(self._console_sizes or _DEFAULT_CONSOLE_SPLIT)[1]` with an
    # IndexError. `_restore_layout`'s `except Exception: pass  # never let a bad layout block launch` had
    # already swallowed the first raise AFTER storing the poison, so the crash surfaced far from its cause.
    # The SAVE path arity-checks (`if len(sizes) == 2`); only the restore path did not.
    for k, arity in (("central_split", 3), ("console_split", 2), ("floorplan_split", 2)):
        sizes = val.get(k)
        if (isinstance(sizes, list) and len(sizes) == arity
                and all(isinstance(x, int) and x >= 0 for x in sizes)):
            out[k] = sizes
    if val.get("console_collapsed") is True:
        out["console_collapsed"] = True
    return out


def set_layout(d: dict) -> None:
    put("layout", d)
