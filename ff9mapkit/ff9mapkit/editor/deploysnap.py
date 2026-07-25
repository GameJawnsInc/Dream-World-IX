"""What was in the project the last time it was deployed -- so "am I looking at what the game is running?"
has an answer.

THE LAW THIS SERVES is the loudest one in the brief: *"One change per in-game test. When a build breaks, we
need to know which edit did it."* The toolkit had no way to answer **which edit**. The deploy path already
records a successful deploy's target, id, destination and revertibility -- but only in memory
(``shell._proc_done``), so the moment you keep editing, "what is in the game" becomes something you hold in
your head. This module persists the project side of that record; :mod:`.tomldiff` turns two of them into a
list a human reads before spending a playtest.

WHAT IS STORED: the PARSED toml, not its text. The kit's own serializer (``model.dumps``) does not preserve
comments or key order -- its contract is round-trip *value* equality -- so the first GUI save of a
hand-written file rewrites the whole document and a text diff would report it as a total rewrite. The
existing in-session dirty check compares dicts for exactly this reason (``shell._dirty_members``). A parsed
snapshot is also what makes the diff semantic rather than textual.

NORMALIZED THROUGH JSON ON BOTH SIDES, and that is a correctness point rather than a storage detail. TOML has
first-class dates and times, so ``tomllib`` can hand back ``datetime`` objects that JSON cannot hold. Storing
them stringified and comparing against live ``datetime``s would report a spurious change on every single
refresh, forever. So :func:`normalize` runs over BOTH the stored snapshot and the live data before they are
compared -- the two sides are always in the same representation.

A SNAPSHOT IS NOT A BACKUP AND NOT A ROLLBACK. This repo has git and its owner uses it; restoring old source
is git's job and doing it here would be a worse version of a tool that already exists. The scarce thing at a
playtest is ATTENTION, so this only ever answers "what is different, and how much".

NEVER LOAD-BEARING (the same rule :mod:`..deploylog` states). A deploy must not fail because a cache
directory is read-only, full, or missing, so every filesystem error here is swallowed and reported by return
value. A corrupt or unreadable snapshot reads as "no snapshot", which degrades to the honest pre-first-deploy
state instead of to a traceback.
"""

from __future__ import annotations

import contextlib
import dataclasses
import datetime as _dt
import hashlib
import json
import os
import time
from pathlib import Path

from .. import provision
from ..fsutil import atomic_write_text
from . import tomldiff

_SCHEMA = 1                      # bump if the payload shape changes -> older snapshots read as absent


def snap_dir() -> Path:
    return provision.cache_dir() / "deploysnap"


def key_for(project_path) -> str:
    """A stable, filename-safe key for a project file: a readable stem plus a hash of the resolved path.

    The hash carries the identity (two ``campaign.toml`` files in different folders are different projects);
    the stem is there so a human can tell what a cache file is without opening it. ``os.path.normcase`` so
    Windows' case-insensitive paths do not mint two snapshots for one project.
    """
    p = Path(project_path)
    with contextlib.suppress(OSError):
        p = p.resolve()
    h = hashlib.sha1(os.path.normcase(str(p)).encode("utf-8")).hexdigest()[:16]
    stem = "".join(c if c.isalnum() or c in "-_" else "_" for c in p.name)[:48]
    return f"{stem}.{h}"


def normalize(v):
    """Both sides of every comparison pass through here -- see the module docstring on dates.

    Also collapses tuples to lists: ``json.loads`` can only ever produce lists, so a live tuple (which no
    toml parse produces today, but a future scene merge could) would otherwise diff against its own
    round-trip.
    """
    if isinstance(v, dict):
        return {str(k): normalize(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [normalize(x) for x in v]
    if isinstance(v, (_dt.datetime, _dt.date, _dt.time)):
        return v.isoformat()
    return v


def capture(files: dict) -> dict:
    """A snapshot payload from ``{label: parsed_toml_dict}``. Labels are what a diff row is prefixed with."""
    return {label: normalize(data) for label, data in files.items()}


def write(project_path, files: dict, *, dest=None, field_id=None, when=None) -> "Path | None":
    """Persist a snapshot for ``project_path``. Returns the file written, or ``None`` on any I/O failure.

    ``dest`` is the destination the deploy went to (the Build tab's ``deploy_dest_key()`` tuple). It is
    recorded rather than folded into the key on purpose: keying by destination would silently start a FRESH
    history the first time someone moved the radio, so "no changes" would appear right after a re-aim to a
    place that has never been deployed. Recorded, the UI can say "that deploy went somewhere else" instead.
    """
    payload = {"schema": _SCHEMA, "project": str(project_path), "when": when or time.time(),
               "dest": list(dest) if dest else None, "field_id": field_id,
               "files": capture(files)}
    try:
        d = snap_dir()
        d.mkdir(parents=True, exist_ok=True)
        path = d / f"{key_for(project_path)}.json"
        atomic_write_text(path, json.dumps(payload, indent=1, sort_keys=True, default=str))
        return path
    except OSError:
        return None                      # diagnostics only -- a deploy never fails because of this


def read(project_path) -> "dict | None":
    """The stored snapshot, or ``None`` if there is none / it is unreadable / it predates the schema."""
    try:
        raw = (snap_dir() / f"{key_for(project_path)}.json").read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        payload = json.loads(raw)
    except ValueError:
        return None                      # a truncated write reads as absent, never as a crash
    if not isinstance(payload, dict) or payload.get("schema") != _SCHEMA:
        return None
    return payload


def forget(project_path) -> bool:
    """Drop a project's snapshot (the honest reset when a comparison stops being meaningful)."""
    try:
        (snap_dir() / f"{key_for(project_path)}.json").unlink()
        return True
    except OSError:
        return False


def changes(snapshot: dict, files: dict) -> list:
    """Every semantic change between a stored ``snapshot`` and the live ``{label: data}``.

    A file that APPEARED or VANISHED since the snapshot is reported as one change against its label rather
    than as every key inside it -- adding a member to a campaign is one edit, not forty.
    """
    old_files = (snapshot or {}).get("files") or {}
    new_files = capture(files)
    out = []
    for label in list(old_files) + [k for k in new_files if k not in old_files]:
        if label not in new_files:
            # file=label / where="" -- the FILE is the subject, so it groups under its own name and renders
            # without a dangling arrow. `tables` is the only context worth a row here: naming every key
            # inside a vanished member would bury the one fact (it is gone) under forty.
            out.append(tomldiff.Change(tomldiff.REMOVED, "", old=old_files[label], file=label,
                                       detail=(("tables", len(old_files[label] or {})),)))
        elif label not in old_files:
            out.append(tomldiff.Change(tomldiff.ADDED, "", new=new_files[label], file=label,
                                       detail=(("tables", len(new_files[label] or {})),)))
        else:
            # Tag, never prefix: `Change.file` is separate from `Change.where` so the UI can GROUP by file,
            # and a single-file project's rows carry no file at all.
            multi = len(new_files) > 1
            for c in tomldiff.diff(old_files[label], new_files[label]):
                out.append(dataclasses.replace(c, file=label) if multi else c)
    return out


def age_str(snapshot: dict, *, now=None) -> str:
    """How long ago that deploy was, for the chip's tooltip. Coarse on purpose -- nobody needs seconds."""
    when = (snapshot or {}).get("when")
    if not isinstance(when, (int, float)):
        return "at an unknown time"
    secs = max(0, int((now if now is not None else time.time()) - when))
    if secs < 90:
        return "moments ago"
    for div, unit in ((60, "minute"), (3600, "hour"), (86400, "day")):
        n = secs // div
        if div == 60 and secs < 3600:
            return f"{n} minute{'s' if n != 1 else ''} ago"
        if div == 3600 and secs < 86400:
            return f"{n} hour{'s' if n != 1 else ''} ago"
        if div == 86400:
            return f"{n} day{'s' if n != 1 else ''} ago"
    return "a while ago"
