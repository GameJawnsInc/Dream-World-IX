"""Atomic file writes + the cross-process file lock for load-bearing files.

The atomic-write rule: a file another layer reads (a save container, ``Memoria.ini``, a
``DictionaryPatch.txt`` registry, a hand-authored ``field.toml``, an engine DLL) must never
be observable half-written. The pattern -- write a sibling ``.tmp``, then ``os.replace`` it
in (an atomic rename on both Windows and POSIX) -- lived in per-site copies (prefs,
save_items, models/thumbcache, workspace/thumbs); new writers route through here instead of
``Path.write_text``/``write_bytes`` or a bare ``open(..., "w")``.

The lock rule: an atomic write makes a rewrite all-or-nothing, but it does NOT serialise two
rewriters -- 18+ concurrent sessions share one game install, and two deploys interleaving
their ``DictionaryPatch.txt`` read->merge->write windows silently drop whichever lines the
other read past (a lost ``FieldScene`` line is the null-.eb black-screen class, and the
foreign-drop guard cannot see it because the clobber happens in the OTHER process's window).
:func:`locked_sidecar` is the serialiser; the fd-level primitive under it
(:func:`exclusive_fd_lock`) is the same measured, tear-tested lock the deploy ledger
(``deploylog``) proved out.
"""

from __future__ import annotations

import contextlib
import os
import time
from pathlib import Path

try:                                    # POSIX
    import fcntl
except ImportError:                     # pragma: no cover - Windows
    fcntl = None
try:                                    # Windows
    import msvcrt
except ImportError:                     # pragma: no cover - POSIX
    msvcrt = None

#: The byte offset :func:`exclusive_fd_lock` locks on Windows. Deliberately far past any plausible end of
#: file, so the lock is a pure cross-process mutex and never a mandatory lock over real records (Windows
#: byte-range locks BLOCK other processes' writes to the locked range; locking real data would be a
#: foot-gun).
_LOCK_OFFSET = 1 << 40

#: Default deadline for :func:`locked_sidecar`. The guarded critical sections are a few milliseconds of
#: small-file I/O, so even 18 sessions piling onto one folder clear in well under a second -- reaching
#: this deadline means another process is WEDGED mid-write (stopped in a debugger, hung on I/O), and the
#: caller must abort loudly rather than proceed unlocked. Generous, because a false abort mid-deploy costs
#: a re-run while a longer wait costs nothing.
LOCK_TIMEOUT = 10.0


class FileLockTimeout(TimeoutError):
    """:func:`exclusive_fd_lock` gave the lock up as unacquirable within its deadline.

    ``TimeoutError`` IS an ``OSError``, deliberately: a caller that swallows filesystem errors wholesale
    (the deploy ledger's ``record`` -- never load-bearing) swallows this too and merely drops its line. A
    load-bearing caller (a deploy's DictionaryPatch rewrite) catches it BY NAME and aborts loudly --
    proceeding unlocked is how a concurrent deploy loses another session's registration."""


def atomic_write_bytes(path: "Path | str", data: bytes) -> None:
    """Write ``data`` to ``path`` so the file is never observed half-written."""
    p = Path(path)
    tmp = p.with_name(p.name + ".tmp")
    try:
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, p)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def atomic_write_text(path: "Path | str", text: str, encoding: str = "utf-8",
                      newline: "str | None" = None) -> None:
    """Drop-in atomic ``Path.write_text``: same text-mode newline translation, same encoding
    default as the kit's writers, but staged through a sibling ``.tmp`` + ``os.replace``."""
    p = Path(path)
    tmp = p.with_name(p.name + ".tmp")
    try:
        with open(tmp, "w", encoding=encoding, newline=newline) as fh:
            fh.write(text)
        os.replace(tmp, p)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def _acquire(try_lock, name, timeout) -> None:
    """Non-blocking acquire in a short backoff loop against a deadline. NB-with-backoff on BOTH platforms,
    never the blocking forms: Windows ``LK_LOCK`` retries on a one-second granularity (measured: it turned
    an 80-line concurrency test into a 35-second test), and a blocking POSIX ``flock`` waits forever on a
    wedged holder -- a bounded loud failure beats both."""
    deadline, delay = time.monotonic() + timeout, 0.001
    while True:
        try:
            try_lock()
            return
        except OSError:
            if time.monotonic() >= deadline:
                raise FileLockTimeout(
                    f"could not lock {name} within {timeout:g}s -- another process (a concurrent "
                    f"deploy/revert?) is holding it. The OS releases the lock when its holder exits, "
                    f"so a stale lockfile cannot be the cause: find the wedged process, or re-run "
                    f"once the other operation finishes.")
            time.sleep(delay)
            delay = min(delay * 2, 0.05)


@contextlib.contextmanager
def exclusive_fd_lock(fd, timeout: float = LOCK_TIMEOUT, name: str = "file"):
    """Hold a cross-process exclusive lock on ``fd`` for the duration of the block.

    POSIX takes ``flock`` on the descriptor; Windows takes a one-byte range lock at
    :data:`_LOCK_OFFSET`, far past EOF, so it acts purely as a mutex. Both acquire via
    :func:`_acquire` (non-blocking + backoff, :class:`FileLockTimeout` past ``timeout``). On an
    exotic platform with neither ``fcntl`` nor ``msvcrt`` the block is a NO-OP -- the caller's
    write is then merely unserialised, which is the pre-lock status quo, not a new failure.
    The OS releases the lock when ``fd`` closes -- including at process death -- so a crashed
    holder cannot wedge anyone. Extracted from ``deploylog`` (where the concurrency test proved
    Windows ``O_APPEND`` alone tears) so every rewriter shares the one proven implementation."""
    if fcntl is not None:
        _acquire(lambda: fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB), name, timeout)
        try:
            yield
        finally:
            with contextlib.suppress(OSError):
                fcntl.flock(fd, fcntl.LOCK_UN)
    elif msvcrt is not None:
        def _try_lock():
            os.lseek(fd, _LOCK_OFFSET, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        _acquire(_try_lock, name, timeout)
        try:
            yield
        finally:
            with contextlib.suppress(OSError):
                os.lseek(fd, _LOCK_OFFSET, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
    else:                                   # pragma: no cover - neither fcntl nor msvcrt
        yield


@contextlib.contextmanager
def locked_sidecar(target: "Path | str", timeout: float = LOCK_TIMEOUT):
    """Serialise a read->merge->write of ``target`` across processes by holding ``<target>.lock``.

    The lock is a SIDECAR, never ``target`` itself, because the write side is an atomic
    ``os.replace``: replacing the target swaps its file identity out from under any lock held ON
    it, while the sidecar's identity is stable across the swap. The sidecar is created on first
    use and deliberately NEVER deleted -- unlinking a lockfile another process still holds open
    reopens the race (a newcomer creates-and-locks a FRESH file while the old holder still owns
    the unlinked ghost). A stray ``*.lock`` beside a mod file is inert to the engine.

    ``target``'s parent directory must exist (every caller creates the mod folder first). A
    platform with neither lock module degrades to unlocked, non-fatally, like the deploy ledger;
    a TIMEOUT raises :class:`FileLockTimeout` instead, because the caller is about to rewrite a
    registry other sessions co-own and proceeding unlocked is the one wrong answer."""
    p = Path(target)
    lock = p.with_name(p.name + ".lock")
    fd = os.open(str(lock), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        with exclusive_fd_lock(fd, timeout=timeout, name=str(lock)):
            yield
    finally:
        os.close(fd)
