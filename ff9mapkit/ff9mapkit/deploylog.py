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

import contextlib
import datetime
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .deploystack import dictionary_ids_at, parse_folder_names

try:                                    # POSIX
    import fcntl
except ImportError:                     # pragma: no cover - Windows
    fcntl = None
try:                                    # Windows
    import msvcrt
except ImportError:                     # pragma: no cover - POSIX
    msvcrt = None

#: The byte offset :func:`_exclusive` locks on Windows. Deliberately far past any plausible end of file, so
#: the lock is a pure cross-process mutex and never a mandatory lock over real records (Windows byte-range
#: locks BLOCK other processes' writes to the locked range; locking real data would be a foot-gun).
_LOCK_OFFSET = 1 << 40
#: How long :func:`_exclusive` will fight for the Windows lock before giving the line up as unrecordable.
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
    LOCK (:func:`_exclusive` -- ``fcntl.flock`` / ``msvcrt.locking``), which is what actually serialises
    appenders on Windows. ``tests/test_deploylog.py`` drives the real :func:`record` through a barrier and
    asserts no line is lost or torn, against a deliberately seek-then-write control that still tears.

    ``checkout`` defaults to the current working directory -- the deploy scripts pass their repo root."""
    ent = Entry(_now(), event, int(field_id), str(mod_folder),
                str(checkout if checkout is not None else Path.cwd()), note)
    data = (ent.line() + "\n").encode("utf-8", errors="replace")
    fd = None
    try:
        fd = os.open(str(ledger_path(game)), os.O_APPEND | os.O_CREAT | os.O_WRONLY, 0o644)
        with _exclusive(fd):
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


@contextlib.contextmanager
def _exclusive(fd):
    """Hold a cross-process exclusive lock on ``fd`` for the duration of the block, so two checkouts
    appending at the same instant serialise instead of clobbering (see :func:`record`).

    POSIX takes ``flock`` on the descriptor. Windows takes a byte-range lock at :data:`_LOCK_OFFSET`, far
    past EOF, so it acts purely as a mutex -- via ``LK_NBLCK`` in a short backoff loop, NOT the blocking
    ``LK_LOCK``: that one retries on a **one-second** granularity, which turned the 80-line concurrency
    test into a 35-second test and would stall a contended deploy for whole seconds to write one
    diagnostic line. After :data:`_LOCK_TIMEOUT` the ``OSError`` propagates to :func:`record`, which
    swallows it -- a line lost to a sustained pile-up is the correct trade; a deploy blocked is not. On
    an exotic platform with neither module the block is a no-op: the single ``os.write`` is still the
    best available, and the ledger stays non-fatal."""
    if fcntl is not None:
        fcntl.flock(fd, fcntl.LOCK_EX)
        try:
            yield
        finally:
            with contextlib.suppress(OSError):
                fcntl.flock(fd, fcntl.LOCK_UN)
    elif msvcrt is not None:
        deadline, delay = time.monotonic() + _LOCK_TIMEOUT, 0.001
        while True:
            os.lseek(fd, _LOCK_OFFSET, os.SEEK_SET)
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise
                time.sleep(delay)
                delay = min(delay * 2, 0.05)
        try:
            yield
        finally:
            with contextlib.suppress(OSError):
                os.lseek(fd, _LOCK_OFFSET, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:                                   # pragma: no cover - neither fcntl nor msvcrt
        yield


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


def registered_ids(game, folder_names: list | None = None) -> tuple:
    """``(ids, folders)`` -- every field/battle id currently registered by ANY stacked mod folder's
    ``DictionaryPatch.txt``, plus the ``FolderNames`` stack it read. Reuses
    :func:`ff9mapkit.deploystack.dictionary_ids_at`, so "registered" means exactly what the id-collision
    guard means by it. ``folders == []`` => the stack could not be read; callers must then report NOTHING
    (an unreadable ini is not evidence that anything vanished)."""
    game = Path(game)
    order = folder_names
    if order is None:
        ini = game / "Memoria.ini"
        order = parse_folder_names(ini.read_text(encoding="utf-8", errors="ignore")) if ini.is_file() else []
    ids: set = set()
    for f in order:
        ids |= set(dictionary_ids_at(game / f))
    return ids, list(order)


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
    (no false alarm -- an unreadable ini would otherwise flag EVERY id ever deployed)."""
    last = last_events(game)
    if not last:
        return ReconcileReport([], [], [])
    ids, folders = registered_ids(game, folder_names)
    if not folders:
        return ReconcileReport([], [], [])
    missing = [e for fid, e in sorted(last.items())
               if e.event == DEPLOYED and fid not in ids]
    retired = [e for fid, e in sorted(last.items()) if e.event == RETIRED]
    return ReconcileReport(missing, retired, folders)


def reconcile_warning(report: ReconcileReport) -> str | None:
    """A human-readable block for a report with ``missing`` ids, or ``None`` when clear. Retirements are
    deliberate, so they never make this fire -- ``doctor`` lists them separately."""
    if report.ok:
        return None
    lines = [f"LOST REGISTRATION: {len(report.missing)} field id(s) the deploy ledger says were deployed are "
             f"NOT registered by any stacked mod folder ({', '.join(report.folders)}). The engine loads a null "
             f".eb for such an id -> black screen with no error. Each was last deployed:"]
    for e in report.missing:
        note = f"  [{e.note}]" if e.note else ""
        lines.append(f"  - id {e.field_id}  {e.when}  folder '{e.mod_folder}'  from {e.checkout}{note}")
    lines.append("Fix: re-deploy from that checkout. (If you retired it on purpose, the ledger just doesn't "
                 "know -- run the revert script, or ignore this.)")
    return "\n".join(lines)
