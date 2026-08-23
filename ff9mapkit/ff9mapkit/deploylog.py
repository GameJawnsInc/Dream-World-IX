"""The DEPLOY LEDGER -- an append-only history of who registered (and who retired) a field id.

The incident this exists for (2026-07-18): field 4003's ``FieldScene`` line was gone, and an investigator
spent real time on it before learning that ``revert_deploy_4003.py`` had been run deliberately as cleanup
eleven hours earlier. **A retired registration and a LOST one are byte-identical** -- a line that is not
there. Nothing on disk recorded why, because a removal leaves no residue. This module gives every
registration a paper trail, so a missing line can explain itself.

WHERE IT LIVES, and why not in the mod folder. The ledger is written BESIDE ``Memoria.ini`` in the game
install root (``<game>/ff9mapkit-deploys.log``), NOT inside ``FF9CustomMap*/``. ``deploy_campaign``
wholesale-replaces a mod folder (``rmtree`` + ``copytree``) -- that is the exact operation behind incident
1 -- so a log kept inside one would be destroyed by the very event it is supposed to explain. The install
root is also the ONE directory every concurrent checkout already shares, which is the point: the history
has to span checkouts, because the sessions clobbering each other are in different checkouts.

WHY THIS IS NOT A TOMBSTONE IN THE REVERT SCRIPT. An earlier draft wrote a "retired" marker only from the
generated revert template. That fails three ways: (a) an ordinary deploy RUNS the prior revert as its own
prelude (``tools/deploy_field.py``), so the marker fires on nearly every deploy and the ONE true retirement
is indistinguishable from hundreds of preludes; (b) ~30 revert scripts already sit on disk from the older
template and would never emit one; (c) it covers only the revert path -- not a campaign wipe, not a hand
edit, not a foreign deploy's drop. So the mechanism is LEDGER + RECONCILIATION: record what we deploy, then
:func:`reconcile` compares the ledger against what is ACTUALLY registered right now. That covers every
removal path, including the ones nothing instruments.

NEVER LOAD-BEARING. :func:`record` is diagnostics. A read-only install, a missing directory or a
permissions failure must not fail a deploy, so expected filesystem errors are swallowed and reported by
return value. Anything that is NOT a filesystem error is a bug in this module -- that is warned about on
stderr rather than hidden, because a silent swallow of a ``TypeError`` is how a guard rots.
"""

from __future__ import annotations

import datetime
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from .deploystack import dictionary_ids_at, parse_folder_names
from .fsutil import exclusive_fd_lock

#: How long :func:`record` will fight for the ledger lock before giving the line up as unrecordable. A
#: line lost to a sustained pile-up is the correct trade for a DIAGNOSTIC; a deploy blocked is not. (The
#: lock itself lives in ``fsutil.exclusive_fd_lock`` now -- extracted so the LOAD-BEARING rewriters, the
#: deploy scripts' DictionaryPatch merges, share the one implementation this module's concurrency test
#: proved out. The timeout raises ``fsutil.FileLockTimeout``, a ``TimeoutError`` -> ``OSError``, so
#: :func:`record`'s wholesale OSError swallow keeps covering it.)
_LOCK_TIMEOUT = 5.0

LEDGER_NAME = "ff9mapkit-deploys.log"

#: the event vocabulary. 'deployed' = this id was registered in that mod folder; 'retired' = it was
#: deliberately unregistered. Anything else is written through verbatim (forward compatibility -- an
#: older kit reading a newer ledger must not choke), but only these two drive :func:`reconcile`.
DEPLOYED = "deployed"
RETIRED = "retired"

_N_FIELDS = 6


def ledger_path(game) -> Path:
    """``<game>/ff9mapkit-deploys.log`` -- beside ``Memoria.ini``, deliberately OUTSIDE every mod folder
    (see the module docstring: a campaign deploy rmtrees mod folders)."""
    return Path(game) / LEDGER_NAME


@dataclass
class Entry:
    """One ledger line. ``when`` is a local-time ISO-8601 string (kept as text -- the ledger is read by
    humans at least as often as by code), ``checkout`` is the repo/cwd the deploy ran from, which is the
    field that actually answers "which of my six sessions did this"."""
    when: str
    event: str
    field_id: int
    mod_folder: str
    checkout: str
    note: str

    def line(self) -> str:
        """This entry as its tab-separated ledger line (no trailing newline)."""
        return "\t".join(_clean(v) for v in (self.when, self.event, str(self.field_id),
                                             self.mod_folder, self.checkout, self.note))


def _clean(value) -> str:
    """Flatten a field so it cannot break the one-record-per-line format. Tabs are the separator and a
    newline would forge a second record, so both become spaces -- a mod folder or note is free text and
    a Windows path can carry anything."""
    return str(value).replace("\t", " ").replace("\r", " ").replace("\n", " ").strip()


def record(game, event: str, field_id: int, mod_folder: str, checkout=None, note: str = "") -> bool:
    """Append one event to the ledger. Returns True if the line was written, False if it was not --
    NEVER raises for a filesystem reason, because a deploy must not fail over its own diagnostics.

    WINDOWS ATOMICITY, honestly, and MEASURED. The line is pre-encoded and handed to a SINGLE ``os.write``
    on a descriptor opened ``O_APPEND | O_CREAT | O_WRONLY``. On POSIX that is the documented atomic-append
    guarantee for small writes. **On Windows it is NOT enough, and the concurrency test proved it**: the
    MSVC CRT implements append mode by seeking to end inside ``_write``, so ``O_APPEND`` here is a
    seek-then-write -- exactly the interleaving hazard -- and 4 barrier-synchronised processes writing 20
    lines each left 69 of 80 on disk, the rest overwritten. (An earlier draft asserted the POSIX guarantee
    applied; it does not. Do not restore that claim.) So the write also takes a cross-process EXCLUSIVE
    LOCK (``fsutil.exclusive_fd_lock`` -- ``fcntl.flock`` / ``msvcrt.locking``), which is what actually
    serialises appenders on Windows. ``tests/test_deploylog.py`` drives the real :func:`record` through a
    barrier and asserts no line is lost or torn, against a deliberately seek-then-write control that still
    tears.

    ``checkout`` defaults to the current working directory -- the deploy scripts pass their repo root."""
    ent = Entry(_now(), event, int(field_id), str(mod_folder),
                str(checkout if checkout is not None else Path.cwd()), note)
    data = (ent.line() + "\n").encode("utf-8", errors="replace")
    fd = None
    try:
        fd = os.open(str(ledger_path(game)), os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o644)
        with exclusive_fd_lock(fd, timeout=_LOCK_TIMEOUT, name=LEDGER_NAME):
            os.lseek(fd, 0, os.SEEK_END)   # no-op under POSIX O_APPEND; the real append on Windows
            os.write(fd, data)
        return True
    except OSError:
        # read-only install, a path that isn't a directory, a permissions denial: all legitimate states of
        # somebody else's machine, and none of them are worth a word of a deploy's output.
        return False
    except Exception as e:                                    # noqa: BLE001
        # NOT a filesystem error => a bug in here (a bad type reaching _clean, say). Still don't fail the
        # deploy, but say so out loud: a guard that swallows its own bugs stops being a guard.
        print(f"  !! deploy ledger: internal error, not recorded ({type(e).__name__}: {e})", file=sys.stderr)
        return False
    finally:
        if fd is not None:
            try:
                os.close(fd)
            except OSError:
                pass


def _now() -> str:
    return datetime.datetime.now().isoformat(timespec="seconds")


def read(game) -> list:
    """Every parseable :class:`Entry`, in file order. A missing or unreadable ledger yields ``[]`` (the
    common case on a fresh install -- absence of history is not an error). Malformed lines are SKIPPED
    rather than raising: the file is appended to by concurrent processes, so tolerating one bad record is
    the difference between a diagnostic that degrades and one that dies."""
    p = ledger_path(game)
    try:
        text = p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []
    out = []
    for line in text.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != _N_FIELDS:
            continue
        try:
            fid = int(parts[2])
        except ValueError:
            continue
        out.append(Entry(parts[0], parts[1], fid, parts[3], parts[4], parts[5]))
    return out


def last_events(game) -> dict:
    """``field_id -> the LAST Entry recorded for it``. Last-writer-wins is the whole model: a redeploy
    after a retirement means deployed, and a retirement after a deploy means retired."""
    out: dict = {}
    for e in read(game):
        out[e.field_id] = e
    return out


def registrations(game, folder_names: list | None = None) -> tuple:
    """``(reg, folders)`` where ``reg`` maps ``id -> {kind: folder}`` for every id currently registered by ANY
    stacked mod folder's ``DictionaryPatch.txt``, plus the ``FolderNames`` stack it read. Reuses
    :func:`ff9mapkit.deploystack.dictionary_ids_at`, so "registered" means exactly what the id-collision
    guard means by it. ``folders == []`` => the stack could not be read; callers must then report NOTHING
    (an unreadable ini is not evidence that anything vanished).

    THE KIND IS CARRIED ON PURPOSE, AND KEYS THE INNER MAP. ``dictionary_ids_at`` indexes ``FieldScene`` AND
    ``BattleScene``, and the two share one id space across folders -- ``deploystack`` documents ``-ate``'s
    ``FieldScene 30011`` against ``-bb``'s ``BattleScene 30011`` as a real multi-hour incident. Judging a
    ledger row on the bare number lets that battle scene stand in for the vanished field: the id looks
    registered, the field is still gone, and :func:`reconcile` reports all clear on exactly the failure it
    exists to catch. Nor can the kinds collapse to one winner -- a stack where a LATER folder registers the
    battle scene would mask a live ``FieldScene`` in an earlier one and invent a loss. Both kinds are kept;
    within a kind the last folder in the stack wins, matching the engine."""
    game = Path(game)
    order = folder_names
    if order is None:
        ini = game / "Memoria.ini"
        order = parse_folder_names(ini.read_text(encoding="utf-8", errors="ignore")) if ini.is_file() else []
    reg: dict = {}
    for f in order:
        for fid, (kind, _name) in dictionary_ids_at(game / f).items():
            reg.setdefault(fid, {})[kind] = f
    return reg, list(order)


@dataclass
class ReconcileReport:
    """The payoff. ``missing`` = ids the ledger says were DEPLOYED but which no stacked mod folder
    registers right now -- each one is a registration that vanished, and its :class:`Entry` says when,
    from which checkout, into which folder. ``retired`` = ids whose last event is an explicit retirement;
    they are DELIBERATE and are reported separately (not mixed into ``missing``, and not suppressed
    either: "4003 was retired at 01:29 from worktree X" is precisely the sentence the 2026-07-18
    investigation needed and did not have). ``folders`` is the FolderNames stack; empty means the stack
    was unreadable and nothing was judged."""
    missing: list
    retired: list
    folders: list

    @property
    def ok(self) -> bool:
        return not self.missing


def reconcile(game, folder_names: list | None = None) -> ReconcileReport:
    """Compare the ledger against what is ACTUALLY registered, and name the ids that lost their
    registration. This -- not any per-removal instrumentation -- is what covers every removal path: a
    campaign wholesale-replace, a hand edit, a foreign deploy's drop, and the ~30 revert scripts already
    on disk from the old template that will never record anything themselves.

    Degrades to an empty report when the ledger is absent or the ``FolderNames`` stack can't be read
    (no false alarm -- an unreadable ini would otherwise flag EVERY id ever deployed).

    A row counts as still registered only when its id is registered as a ``FieldScene``. Everything the ledger
    records is a FIELD deploy, and a ``BattleScene`` holding the same number is not that field -- it is the
    cross-folder id collision ``deploystack`` warns about. See :func:`registrations`."""
    last = last_events(game)
    if not last:
        return ReconcileReport([], [], [])
    reg, folders = registrations(game, folder_names)
    if not folders:
        return ReconcileReport([], [], [])
    missing = [e for fid, e in sorted(last.items())
               if e.event == DEPLOYED and "FieldScene" not in reg.get(fid, {})]
    retired = [e for fid, e in sorted(last.items()) if e.event == RETIRED]
    return ReconcileReport(missing, retired, folders)


def reconcile_warning(report: ReconcileReport) -> str | None:
    """A human-readable block for a report with ``missing`` ids, or ``None`` when clear. Retirements are
    deliberate, so they never make this fire -- ``doctor`` lists them separately."""
    if report.ok:
        return None
    lines = [f"LOST REGISTRATION: {len(report.missing)} field id(s) the deploy ledger says were deployed have "
             f"no `FieldScene` registration in any stacked mod folder ({', '.join(report.folders)}). The engine "
             f"loads a null .eb for such an id -> black screen with no error. Each was last deployed:"]
    for e in report.missing:
        note = f"  [{e.note}]" if e.note else ""
        lines.append(f"  - id {e.field_id}  {e.when}  folder '{e.mod_folder}'  from {e.checkout}{note}")
    lines.append("Fix: re-deploy from that checkout. (If you retired it on purpose, the ledger just doesn't "
                 "know -- run the revert script, or ignore this.)")
    return "\n".join(lines)
