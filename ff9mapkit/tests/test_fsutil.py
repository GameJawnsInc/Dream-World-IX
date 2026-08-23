"""fsutil: the atomic-write helpers every load-bearing writer routes through, and the cross-process
sidecar lock (``locked_sidecar``) that serialises DictionaryPatch-style read->merge->write rewrites.

The lock's reason to exist: 18+ concurrent sessions share ONE game install, and two deploys into the same
mod folder interleaving their read->merge->write windows silently drop whichever lines the other read past
-- a lost ``FieldScene`` line is the null-.eb black-screen class, invisible to the foreign-drop guard
because the clobber happens in the OTHER process's window. The concurrency test here follows
``test_deploylog.py``'s pattern: REAL processes through a barrier, plus a deliberately unlocked negative
control that DOES lose lines, so the positive test isn't vacuous.
"""

import multiprocessing as mp
import os
import pathlib
import time

import pytest

from ff9mapkit import fsutil


def test_atomic_write_bytes_roundtrip_and_no_tmp_left(tmp_path):
    p = tmp_path / "out.bin"
    fsutil.atomic_write_bytes(p, b"\x00\x01")
    assert p.read_bytes() == b"\x00\x01"
    fsutil.atomic_write_bytes(p, b"\x02")          # overwrite replaces wholesale
    assert p.read_bytes() == b"\x02"
    assert not p.with_name(p.name + ".tmp").exists()


def test_atomic_write_text_matches_path_write_text(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_text("x\ny\n", encoding="utf-8")
    fsutil.atomic_write_text(b, "x\ny\n", encoding="utf-8")
    assert b.read_bytes() == a.read_bytes()        # drop-in: identical newline translation
    assert not b.with_name(b.name + ".tmp").exists()


# ---------------------------------------------------------------- the sidecar lock

def test_locked_sidecar_locks_a_sidecar_and_leaves_the_target_alone(tmp_path):
    target = tmp_path / "DictionaryPatch.txt"
    target.write_text("FieldScene 4003 11 10 TESTROOM 1073\n", encoding="utf-8")
    with fsutil.locked_sidecar(target):
        pass
    # the sidecar sits BESIDE the target and is deliberately never deleted (unlinking a lockfile another
    # process still holds open reopens the race); the target itself is untouched.
    assert (tmp_path / "DictionaryPatch.txt.lock").exists()
    assert target.read_text(encoding="utf-8") == "FieldScene 4003 11 10 TESTROOM 1073\n"


def test_a_held_lock_times_out_loudly_and_names_the_lockfile(tmp_path):
    target = tmp_path / "DictionaryPatch.txt"
    with fsutil.locked_sidecar(target):
        with pytest.raises(fsutil.FileLockTimeout) as ei:
            with fsutil.locked_sidecar(target, timeout=0.2):
                raise AssertionError("acquired a lock another holder owns")
    assert "DictionaryPatch.txt.lock" in str(ei.value)
    # ...and the lock is reacquirable once released (nothing wedged, no stale state)
    with fsutil.locked_sidecar(target, timeout=0.2):
        pass


def test_lock_timeout_stays_inside_the_ledgers_oserror_net():
    # deploylog.record() swallows OSError wholesale (the ledger is never load-bearing); the shared lock's
    # timeout must stay inside that net so a contended LEDGER drops its line rather than failing a deploy,
    # while the LOAD-BEARING callers (the deploy scripts) catch FileLockTimeout by name and abort.
    assert issubclass(fsutil.FileLockTimeout, TimeoutError)
    assert issubclass(fsutil.FileLockTimeout, OSError)


def test_no_lock_modules_degrades_to_unlocked_not_fatal(tmp_path, monkeypatch):
    # the exotic-platform contract (same as the deploy ledger): neither fcntl nor msvcrt -> a no-op, never
    # a crash. (Patching fsutil's OWN globals only -- restored by monkeypatch.)
    monkeypatch.setattr(fsutil, "fcntl", None)
    monkeypatch.setattr(fsutil, "msvcrt", None)
    with fsutil.locked_sidecar(tmp_path / "DictionaryPatch.txt"):
        pass


# ------------------------------------------------- concurrency (with a negative control)

_N_PROCS = 4
_N_ROUNDS = 12
_SEED = "FieldScene 4003 11 10 FOREIGN 1073"


def _locked_rmw_worker(path, tag, barrier, rounds):
    """Drives the REAL deployed pattern: hold <target>.lock across read -> merge -> atomic write, one
    appended FieldScene line per round. This is the shape tools/deploy_field.py, tools/deploy_battle.py,
    and the generated reverts all ship."""
    p = pathlib.Path(path)
    for i in range(rounds):
        barrier.wait()                                    # every process enters the window at the SAME instant
        with fsutil.locked_sidecar(p):
            lines = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
            lines.append(f"FieldScene 30000 11 10 {tag}_{i} 1073")
            fsutil.atomic_write_text(p, "\n".join(lines) + "\n", newline="\n")


def _unlocked_rmw_worker(path, tag, barrier, rounds):
    """The NEGATIVE CONTROL: the PRE-lock deploy pattern -- read, dwell, atomic replace, no lock. The
    dwell keeps every process inside the read-to-write window together, so the last writer erases the
    others' lines: an atomic replace makes each rewrite all-or-nothing but serialises nothing.

    Two Windows sharp edges are deliberately sanded off so the control isolates PURE LINE LOSS -- both are
    ADDITIONAL failure modes of the unlocked pattern that the lock also prevents, and both were measured
    here before the sanding: (a) unlocked processes fight over atomic_write_text's one shared ``.tmp``
    sibling and die on PermissionError (hence a per-process staging name); (b) ``os.replace`` onto a target
    another process momentarily holds open for read ALSO dies on PermissionError, and one dead worker left
    the rest waiting at the barrier forever (hence the retry loops)."""
    p = pathlib.Path(path)
    for i in range(rounds):
        barrier.wait()
        while True:
            try:
                lines = p.read_text(encoding="utf-8").splitlines() if p.exists() else []
                break
            except OSError:                               # the target is mid-replace by another process
                time.sleep(0.001)
        time.sleep(0.02)                                  # all N read the same state, then all N write
        lines.append(f"FieldScene 30000 11 10 {tag}_{i} 1073")
        tmp = p.with_name(f"{p.name}.{tag}.tmp")
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        while True:
            try:
                os.replace(tmp, p)
                break
            except PermissionError:                       # another process holds the target open for read
                time.sleep(0.001)


def _run_workers(worker, path):
    # daemon=True: if a worker dies, its siblings wait at the barrier forever -- daemons then die with the
    # test process instead of hanging pytest's exit (measured: one PermissionError-killed worker did that).
    barrier = mp.Barrier(_N_PROCS)
    procs = [mp.Process(target=worker, args=(str(path), f"proc{k}", barrier, _N_ROUNDS), daemon=True)
             for k in range(_N_PROCS)]
    for p in procs:
        p.start()
    for p in procs:
        p.join(120)
    try:
        assert all(p.exitcode == 0 for p in procs), [p.exitcode for p in procs]
    finally:
        for p in procs:                                   # a barrier-stuck straggler would outlive join(120)
            if p.is_alive():
                p.terminate()


def test_concurrent_locked_rewrites_lose_no_line(tmp_path):
    """The deliverable: N barrier-synchronised processes doing locked read->merge->write leave EVERY line
    on disk -- their own and the pre-existing 'foreign' registration -- and none torn."""
    target = tmp_path / "DictionaryPatch.txt"
    target.write_text(_SEED + "\n", encoding="utf-8")
    _run_workers(_locked_rmw_worker, target)
    lines = [ln for ln in target.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1 + _N_PROCS * _N_ROUNDS, "a registration line was lost"
    assert _SEED in lines, "the foreign line was dropped"
    assert all(len(ln.split()) == 6 and ln.startswith("FieldScene ") for ln in lines), "a line was torn"
    payloads = {ln.split()[4] for ln in lines if ln != _SEED}
    assert payloads == {f"proc{k}_{i}" for k in range(_N_PROCS) for i in range(_N_ROUNDS)}


def test_negative_control_unlocked_rewrites_DO_lose_lines(tmp_path):
    """Without this, the test above proves nothing -- it could pass on a harness that never actually
    interleaves. The unlocked read->merge->write under the same barrier must visibly lose lines: that IS
    the pre-fix deploy loop, and the loss it demonstrates is the null-.eb black-screen class."""
    target = tmp_path / "DictionaryPatch.txt"
    target.write_text(_SEED + "\n", encoding="utf-8")
    _run_workers(_unlocked_rmw_worker, target)
    lines = [ln for ln in target.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) < 1 + _N_PROCS * _N_ROUNDS, \
        "the negative control lost nothing -- the positive test is vacuous"
