#!/usr/bin/env python3
"""Diagnosability artifacts for a harness run -- pure helpers, no Session import.

WHY THIS EXISTS. A failed check used to leave one screenshot and a ``state-final.json`` captured
AFTER ``quit`` -- the wrong moment -- so "what was the game doing when this failed" cost a re-run,
and under a suite a re-run costs the whole suite. These are the pieces that make a failure readable
from the run directory alone:

* :class:`StateRing` -- the last ~10 s of published state, fed by the reads every wait already
  makes (no thread, no extra poll), flushed to ``states-<tag>.jsonl`` when something fails.
* :class:`StepLog` -- one row per request in ``steps.jsonl``: the literal steps, when the agent
  ACCEPTED it and when it FINISHED it. "Which step never landed" becomes a one-row read.
* :func:`build_env` -- ``env.json``: the DLL that was actually driven (sha256), the registrations
  in every mod folder, the ``Memoria.ini`` values the engine obeys, the driver's git head.

EVERY WRITER HERE IS ALLOWED TO FAIL AND NONE MAY RAISE INTO THE RUN. An artifact is worth less
than the disarm gate, less than the verdict, and less than the step it describes -- so a probe that
cannot answer writes ``null`` AND a named error, never an exception, and "could not read" is never
allowed to look like "not set".
"""
from __future__ import annotations

import collections
import datetime as _dt
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

from .channel import PROTOCOL

#: How many distinct published frames the ring keeps. The agent publishes every 2nd frame (~30/s),
#: and the ring dedupes on frame, so intake is capped at that rate whatever the poll rate: 300 is
#: the last ~10 seconds at full rate -- the window a failed check or a timed-out wait is diagnosed
#: from. Older history is already on disk in steps.jsonl (driver side) and events.jsonl (agent).
STATE_RING = 300


class StateRing:
    """The last ``n`` distinct published states, cheapest possible: one deque append per NEW frame.

    Dedupes on ``frame != last`` rather than ``>``, so a counter that restarts (a soft reset re-arms
    nothing, but a relaunch under ``--attach`` could) is still sampled rather than silently dropped.
    """

    def __init__(self, n: int = STATE_RING):
        self._buf: collections.deque = collections.deque(maxlen=max(1, int(n)))
        self._last_frame: int | None = None

    def push(self, st) -> bool:
        """Record ``st`` if its frame is new. Returns whether it was kept."""
        frame = st.frame
        if self._last_frame is not None and frame == self._last_frame:
            return False
        self._last_frame = frame
        self._buf.append((st.read_at, st.age, st.raw))
        return True

    def __len__(self) -> int:
        return len(self._buf)

    def frames(self) -> list[int]:
        return [int(raw.get("frame", -1)) for _, _, raw in self._buf]

    def clear(self) -> None:
        self._buf.clear()
        self._last_frame = None

    def dump(self, path) -> int:
        """Write the ring as JSONL (``{"t", "age", "state"}`` per row, oldest first). Returns the count.

        No header row: the FILENAME carries the reason (``states-FAILED-1.jsonl``) and the check row
        / report link it. The state is the agent's own document, untouched.
        """
        rows = list(self._buf)
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            for t, age, raw in rows:
                fh.write(json.dumps({"t": t, "age": age, "state": raw}, separators=(",", ":")) + "\n")
        return len(rows)


class StepLog:
    """Append-only JSONL. ``append`` returns False instead of raising -- the caller counts drops."""

    def append(self, path, row: dict) -> bool:
        try:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, default=str) + "\n")
            return True
        except Exception:                                  # noqa: BLE001 - see the module docstring
            return False


#: The ini sections env.json records, and which keys (None = the whole section). These are the
#: values that change what a harness result MEANS: the analog axis the injected press has to
#: satisfy, the boosters, the soft-reset gate the recovery ladder depends on, the autosave that
#: once wrote the owner's file, and the folder order that decides which DictionaryPatch wins.
INI_SECTIONS: dict[str, tuple[str, ...] | None] = {
    "AnalogControl": ("Enabled",),
    "Cheats": None,
    "Control": ("SoftReset",),
    "SaveFile": ("DisableAutoSave",),
    "Mod": ("FolderNames",),
}


def read_memoria_ini(path, sections=INI_SECTIONS) -> dict | None:
    """The values the ENGINE would use from a ``Memoria.ini``, or None if it cannot be read.

    LAST wins, because Memoria's parser does: ``IniFile.Init`` walks the file line by line and ends
    each with a plain dictionary assignment, re-entering a section on a repeated header -- the law
    :func:`ff9mapkit.coop.read_ini_key` documents. Hand-rolled rather than ``configparser`` because
    the stock file carries tab-indented ``;`` comment blocks, duplicate keys and no interpolation
    safety, and a strict parser would raise on the very file the engine plays happily. Values are
    kept as raw strings -- this records, it does not interpret. ``mod_folders`` is the ordered
    FolderNames list (the same regex :func:`ff9mapkit.deploystack.parse_folder_names` uses).
    """
    try:
        text = Path(path).read_text(encoding="utf-8-sig", errors="replace")
    except OSError:
        return None
    wanted = {name.lower(): (name, keys) for name, keys in sections.items()}
    out: dict = {}
    section: str | None = None
    for line in text.splitlines():
        t = line.strip()
        if not t or t[0] in ";#":
            continue
        if t.startswith("[") and "]" in t:
            section = t[1:t.index("]")].strip().lower()
            continue
        if section is None or "=" not in line:
            continue
        hit = wanted.get(section)
        if hit is None:
            continue
        name, keys = hit
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if keys is not None and key.lower() not in {k.lower() for k in keys}:
            continue
        out.setdefault(name, {})[key] = value
    folders = out.get("Mod", {}).get("FolderNames") or ""
    out["mod_folders"] = re.findall(r'"([^"]+)"', folders)
    return out


def sha256_file(path, chunk: int = 1 << 20) -> dict:
    """``{"path", "exists", "size", "mtime", "sha256"}`` -- ``sha256`` None when absent."""
    p = Path(path)
    info: dict = {"path": str(p), "exists": p.is_file(), "size": None, "mtime": None, "sha256": None}
    if not info["exists"]:
        return info
    st = p.stat()
    info["size"] = st.st_size
    info["mtime"] = _dt.datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds")
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    info["sha256"] = h.hexdigest()
    return info


_GIT_CACHE: dict[str, tuple[str | None, bool | None]] = {}


def git_head(repo) -> tuple[str | None, bool | None]:
    """``(short sha, dirty)`` for the checkout the driver ran from; ``(None, None)`` when unknown.

    Cached per process (one spawn per xdist worker) and bounded by a 5 s timeout. A failure -- no
    git, a hung subprocess -- RAISES so :func:`build_env`'s probe records it by name; "not a repo"
    is a clean ``(None, None)``. The cache only keeps answers, so a failed probe costs one more
    spawn on the next write and nothing else.
    """
    key = str(repo)
    if key in _GIT_CACHE:
        return _GIT_CACHE[key]
    out = subprocess.run(["git", "-C", key, "rev-parse", "--short", "HEAD"],
                         capture_output=True, text=True, timeout=5)
    sha: str | None = out.stdout.strip() or None
    dirty: bool | None = None
    if sha:
        status = subprocess.run(["git", "-C", key, "status", "--porcelain", "--untracked-files=no"],
                                capture_output=True, text=True, timeout=5)
        dirty = bool(status.stdout.strip())
    _GIT_CACHE[key] = (sha, dirty)
    return sha, dirty


def build_env(session, **extra) -> dict:
    """Everything about the run that a reader tomorrow needs and cannot reconstruct.

    Every probe runs in its own guard: one that fails writes ``null`` for its field AND a named entry
    in ``errors``, so "could not read the ini" is never mistaken for "the ini has no such key".
    ``extra`` is merged on top -- the suite adds its manifest and member list this way.
    """
    errors: dict[str, str] = {}

    def probe(name: str, fn, fallback=None):
        try:
            return fn()
        except Exception as err:                           # noqa: BLE001 - recorded, never raised
            errors[name] = f"{type(err).__name__}: {err}"
            return fallback

    game = Path(session.game_path)
    repo = Path(getattr(session, "repo_root", Path(__file__).resolve().parents[2]))
    sha, dirty = probe("git_head", lambda: git_head(repo), (None, None))

    def ini():
        doc = read_memoria_ini(game / "Memoria.ini")
        if doc is None:
            return {"present": False}
        return {"present": True, **doc}

    def registrations():
        from .session import scan_registrations              # late: session imports this module
        return {patch.parent.name: {str(fid): name for fid, name in rows}
                for patch, rows in scan_registrations(game)}

    env = {
        "written": _dt.datetime.now().isoformat(timespec="seconds"),
        "label": session.label,
        "run_dir": str(session.run_dir),
        "game_path": str(game),
        "attached": bool(session.attach),
        "driver": {
            "protocol": PROTOCOL,
            "python": sys.version.split()[0],
            "platform": sys.platform,
            "repo": str(repo),
            "git_head": sha,
            "git_dirty": dirty,
        },
        "engine": {
            "protocol": session.engine_protocol,
            "boot_seconds": getattr(session, "_boot_seconds", None),
            "first_state": getattr(session, "_first_state", None),
            "assembly_csharp": probe(
                "assembly_csharp",
                lambda: sha256_file(game / "x64" / "FF9_Data" / "Managed" / "Assembly-CSharp.dll")),
        },
        "window": {
            "requested": None if session.attach else list(session.window_size),
            "note": ("attached to a running game -- its window is whatever the player chose"
                     if session.attach else "windowed, from the launcher's own arguments"),
        },
        "memoria_ini": probe("memoria_ini", ini, {"present": None}),
        "registrations": probe("registrations", registrations, None),
        "errors": errors,
    }
    env.update(extra)
    return env
