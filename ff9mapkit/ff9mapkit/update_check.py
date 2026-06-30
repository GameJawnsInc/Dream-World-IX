"""Opt-in update check for ff9mapkit — ask PyPI whether a newer release exists, fully offline-tolerant.

stdlib-only (urllib + json); NO new dependency. NEVER raises to the caller: a network failure, a malformed
response, or an unreadable config all degrade to "no update info". The opt-in flag + last-check timestamp
live in a small JSON in the per-user config dir (``%LOCALAPPDATA%\\ff9mapkit\\config`` / ``~/.local/share/...``)
so they SURVIVE a ``uv tool upgrade`` (which wipes the package's own ``data/``). The GUI runs :func:`check`
off the UI thread and surfaces the result; the CLI / tests call these functions directly.

The kit can't self-upgrade a running ``uv tool`` / ``pip`` install cleanly, so the policy is INFORM, not
auto-update: tell the user a version is out and the one command to run (:data:`UPGRADE_COMMAND`).
"""

from __future__ import annotations

import json
import re
import time
import urllib.request
from pathlib import Path

from . import __version__, provision

INSTALLED = __version__
PYPI_JSON_URL = "https://pypi.org/pypi/ff9mapkit/json"
PYPI_PROJECT_URL = "https://pypi.org/project/ff9mapkit/"
UPGRADE_COMMAND = "uv tool upgrade ff9mapkit"        # the installer/uv path (canonical)
PIP_UPGRADE_COMMAND = "pip install -U ff9mapkit"     # for a plain pip install
CHECK_INTERVAL_S = 24 * 60 * 60                      # the once-a-day launch gate


# ----------------------------------------------------------------- persistent state (survives an upgrade)
def _state_path() -> Path:
    return provision._user_dir("config") / "update_check.json"


def load_state() -> dict:
    try:
        return json.loads(_state_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_state(state: dict) -> None:
    try:
        p = _state_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError:
        pass


def was_prompted() -> bool:
    """True once the user has answered the first-run opt-in prompt (either way)."""
    return bool(load_state().get("prompted"))


def is_enabled() -> bool:
    """True if the user opted in to the once-a-day launch check."""
    return bool(load_state().get("enabled"))


def set_preference(enabled: bool) -> None:
    """Record the first-run choice (and that the user was asked)."""
    st = load_state()
    st["enabled"] = bool(enabled)
    st["prompted"] = True
    save_state(st)


# ----------------------------------------------------------------- version comparison
def _vkey(s: str):
    """A sort key for the kit's ``N.N.N[(a|b|rc)N]`` versions; ``None`` if unparseable. A FINAL release sorts
    after every prerelease of the same release (1.0.0 > 1.0.0b8 > 1.0.0b1)."""
    m = re.match(r"^\s*(\d+(?:\.\d+)*)(?:[._-]?(a|b|c|rc|alpha|beta|pre)\.?(\d+))?\s*$", s or "", re.I)
    if not m:
        return None
    rel = [int(x) for x in m.group(1).split(".")]
    while len(rel) < 4:
        rel.append(0)
    pre = m.group(2)
    if pre is None:
        pre_key = (1, 0, 0)                  # final release: ranks above any prerelease
    else:
        rank = {"a": 0, "alpha": 0, "b": 1, "beta": 1, "c": 2, "rc": 2, "pre": 2}.get(pre.lower(), 0)
        pre_key = (0, rank, int(m.group(3)))
    return (tuple(rel), pre_key)


def is_newer(latest: str, current: str = INSTALLED) -> bool:
    """True iff ``latest`` is strictly newer than ``current``. PEP 440-correct when ``packaging`` is
    importable, else a focused fallback for the kit's own scheme. Conservative: an unparseable pair returns
    ``False`` — never nag about a version we can't order."""
    if not latest or latest == current:
        return False
    try:
        from packaging.version import Version
        return Version(latest) > Version(current)
    except ImportError:
        pass
    except Exception:
        return False
    a, b = _vkey(latest), _vkey(current)
    return bool(a and b and a > b)


# ----------------------------------------------------------------- the network check
def fetch_latest(timeout: float = 4.0):
    """The latest released version string on PyPI, or ``None`` on ANY error (offline-tolerant)."""
    try:
        req = urllib.request.Request(PYPI_JSON_URL, headers={"User-Agent": f"ff9mapkit/{INSTALLED}"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:        # noqa: S310 (https literal)
            info = json.load(resp).get("info") or {}
        v = info.get("version")
        return str(v) if v else None
    except Exception:
        return None


def record_check(latest, *, now: float | None = None) -> None:
    st = load_state()
    st["last_check"] = float(time.time() if now is None else now)
    if latest:
        st["last_seen_latest"] = latest
    save_state(st)


def should_check_now(*, now: float | None = None) -> bool:
    """The once-a-day launch gate: opted in AND at least a day since the last check."""
    st = load_state()
    if not st.get("enabled"):
        return False
    last = st.get("last_check")
    if last is None:                         # opted in but never checked -> due now (clock-magnitude-independent)
        return True
    now = time.time() if now is None else now
    return (now - float(last)) >= CHECK_INTERVAL_S


def check(*, now: float | None = None) -> dict:
    """Run a check NOW (ignores the daily gate), stamp the time, and return
    ``{current, latest, ok, newer}``. Safe to call off the UI thread."""
    latest = fetch_latest()
    record_check(latest, now=now)
    return {"current": INSTALLED, "latest": latest, "ok": latest is not None,
            "newer": bool(latest and is_newer(latest))}
