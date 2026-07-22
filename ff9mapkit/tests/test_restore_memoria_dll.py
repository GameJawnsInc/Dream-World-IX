"""``tools/restore_memoria_dll.py`` -- the engine-revert path named by the CLAUDE.md hard constraint.

The failure mode pinned here (found 2026-07-22, s47 review): ``baseline`` mode globbed
``<dll>.*baseline*``, matched NOTHING in backups/ -- the documented ``*.baseline-rebuild-*`` set is
gone and the current build lane writes ``Assembly-CSharp.x64.dll.<ts>`` (arch BEFORE ``.dll``, which
the old prefix glob can never match) -- printed a per-DLL skip, then ended with ``Done.``. A user
believing they reverted the engine had not. These tests pin (a) that every observed backup naming
convention is found, (b) that arch-specific backups land only in their own Managed folder while
arch-neutral ones land in both, (c) that the newest match wins, and (d) that restoring NOTHING exits
non-zero with a loud message -- never a bare ``Done.``.

Every fixture install is built explicitly under tmp_path. Nothing here may fall through to the
developer's real backups/ or game install.
"""

import importlib.util
import os
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("restore_memoria_dll", REPO / "tools" / "restore_memoria_dll.py")
rmd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rmd)


# ---------------------------------------------------------------- fixtures

def _install(tmp_path, backups=()):
    """A fake layout: a backups/ dir with the given (name, content) files, and one empty
    Managed dir per arch. Returns (bkp, managed) ready for rmd.restore(). Backup mtimes are
    staggered in list order so 'newest' is deterministic regardless of filesystem timing."""
    bkp = tmp_path / "backups"
    bkp.mkdir()
    for i, (name, content) in enumerate(backups):
        p = bkp / name
        p.write_bytes(content)
        t = 1_000_000_000 + i * 60
        os.utime(p, (t, t))
    managed = {}
    for arch in ("x64", "x86"):
        d = tmp_path / "game" / arch / "FF9_Data" / "Managed"
        d.mkdir(parents=True)
        managed[arch] = str(d)
    return str(bkp), managed


def _managed_bytes(managed, arch, dll="Assembly-CSharp.dll"):
    p = pathlib.Path(managed[arch]) / dll
    return p.read_bytes() if p.exists() else None


# ---------------------------------------------------------------- the 2026-07-22 incident, pinned

def test_current_build_lane_per_arch_names_are_found_and_land_per_arch(tmp_path, capsys):
    """The exact real names from the s47 build lane: arch before .dll. The old glob missed these
    entirely; now each restores into its OWN arch's Managed folder."""
    bkp, managed = _install(tmp_path, [
        ("Assembly-CSharp.x64.dll.20260722-095733", b"pre-s47-x64"),
        ("Assembly-CSharp.x86.dll.20260722-095733", b"pre-s47-x86"),
    ])
    restored, failed = rmd.restore("20260722-095733", bkp, managed)
    assert (restored, failed) == (2, 0)
    assert _managed_bytes(managed, "x64") == b"pre-s47-x64"
    assert _managed_bytes(managed, "x86") == b"pre-s47-x86"


def test_nothing_matched_exits_nonzero_and_says_so_loudly(tmp_path, capsys, monkeypatch):
    """The headline bug: baseline matching nothing must NOT end in a success line + exit 0.
    main() runs against the same fake install via the module constants."""
    bkp, managed = _install(tmp_path, [
        ("Assembly-CSharp.x64.dll.20260722-095733", b"x64"),   # real backups exist...
        ("Assembly-CSharp.x86.dll.20260722-095733", b"x86"),
    ])
    monkeypatch.setattr(rmd, "BKP", bkp)
    monkeypatch.setattr(rmd, "MANAGED", managed)
    rc = rmd.main(["restore_memoria_dll.py", "baseline"])      # ...but none match 'baseline'
    out = capsys.readouterr().out
    assert rc == 1
    assert "NOTHING RESTORED" in out
    assert "UNCHANGED" in out
    assert "Done" not in out
    assert "Assembly-CSharp.x64.dll.20260722-095733" in out    # the hint names what IS on disk
    assert _managed_bytes(managed, "x64") is None              # and truly nothing was written


def test_something_restored_exits_zero_even_with_dll_gaps(tmp_path, capsys, monkeypatch):
    """backups/ has never held all three DLLs at once -- a missing Memoria.Prime/UnityEngine.UI
    backup is a reported skip, not a failure, as long as SOMETHING was restored."""
    bkp, managed = _install(tmp_path, [
        ("Assembly-CSharp.x64.dll.20260722-095733", b"x64"),
        ("Assembly-CSharp.x86.dll.20260722-095733", b"x86"),
    ])
    monkeypatch.setattr(rmd, "BKP", bkp)
    monkeypatch.setattr(rmd, "MANAGED", managed)
    rc = rmd.main(["restore_memoria_dll.py", "20260722-095733"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Done: 2 file(s) restored" in out
    assert "no backup found for Memoria.Prime.dll" in out


# ---------------------------------------------------------------- naming-convention coverage

def test_every_observed_naming_convention_is_classified(tmp_path):
    """One representative real name per convention in backups/ today, all for one selector-free
    sweep: the finder must see all of them and bucket the arch correctly."""
    bkp, _ = _install(tmp_path, [
        ("Assembly-CSharp.dll.20260716-101735", b"neutral"),                       # bare timestamp
        ("Assembly-CSharp.dll.x64.20260622-230806", b"old-x64"),                   # arch after .dll
        ("Assembly-CSharp.dll.pre-debugmenu-features-x86.20260703-134136", b"lbl-x86"),  # labeled arch
        ("Assembly-CSharp.x64.dll.20260722-095733", b"new-x64"),                   # current lane
        ("Assembly-CSharp.dll.baseline-rebuild-6b8bb2d5.20250713", b"baseline"),   # the documented set
    ])
    by_arch = rmd.find_backups("Assembly-CSharp.dll", "", bkp)
    assert set(by_arch) == {None, "x64", "x86"}
    # newest (mtime order = list order) wins per bucket
    assert by_arch["x64"].endswith("Assembly-CSharp.x64.dll.20260722-095733")
    assert by_arch["x86"].endswith("pre-debugmenu-features-x86.20260703-134136")
    assert by_arch[None].endswith("baseline-rebuild-6b8bb2d5.20250713")


def test_baseline_selector_still_pins_the_documented_set_when_it_exists(tmp_path):
    bkp, managed = _install(tmp_path, [
        ("Assembly-CSharp.dll.20260716-101735", b"other"),
        ("Assembly-CSharp.dll.baseline-rebuild-6b8bb2d5.20250713", b"baseline"),
    ])
    restored, failed = rmd.restore("baseline", bkp, managed)
    assert (restored, failed) == (2, 0)                        # arch-neutral -> both arches
    assert _managed_bytes(managed, "x64") == b"baseline"
    assert _managed_bytes(managed, "x86") == b"baseline"


def test_arch_specific_beats_arch_neutral_for_its_own_arch_only(tmp_path):
    bkp, managed = _install(tmp_path, [
        ("Assembly-CSharp.dll.mylabel.20260101-000000", b"neutral"),
        ("Assembly-CSharp.x64.dll.mylabel.20260101-000000", b"x64-specific"),
    ])
    restored, failed = rmd.restore("mylabel", bkp, managed)
    assert (restored, failed) == (2, 0)
    assert _managed_bytes(managed, "x64") == b"x64-specific"
    assert _managed_bytes(managed, "x86") == b"neutral"        # falls back to the neutral file


def test_newest_by_mtime_wins_across_conventions(tmp_path):
    """Lexicographic name order disagrees with age across conventions ('.dll.x64.' sorts before
    '.x64.dll.'), so 'latest' must be mtime, not name."""
    bkp, managed = _install(tmp_path, [
        ("Assembly-CSharp.x64.dll.20260101-000000", b"older-new-style"),
        ("Assembly-CSharp.dll.x64.20260102-000000", b"newer-old-style"),   # later mtime (list order)
    ])
    restored, _ = rmd.restore("2026", bkp, managed)
    assert restored == 1                                       # x64 only; no x86/neutral candidate
    assert _managed_bytes(managed, "x64") == b"newer-old-style"


def test_arch_token_must_be_a_whole_token(tmp_path):
    """'x64' inside a larger word must not classify -- only a delimited token counts."""
    assert rmd.backup_arch("Assembly-CSharp.dll.pre-fix64bug.20260101") is None
    assert rmd.backup_arch("Assembly-CSharp.dll.x64.20260101") == "x64"
    assert rmd.backup_arch("Assembly-CSharp.x86.dll.20260101") == "x86"
    assert rmd.backup_arch("Assembly-CSharp.dll.pre-gui-redesign-x64.20260703-172058") == "x64"


# ---------------------------------------------------------------- copy failure = loud, non-zero

def test_copy_failure_counts_failed_and_main_exits_nonzero(tmp_path, capsys, monkeypatch):
    """A locked/unwritable destination (FF9 running) must surface as a failure, not vanish."""
    bkp, managed = _install(tmp_path, [
        ("Assembly-CSharp.x64.dll.20260722-095733", b"x64"),
    ])
    # make the x64 destination un-copyable: a plain FILE where the Managed DIR should be,
    # so the copy raises OSError (NotADirectoryError) just like a locked/unreachable dest
    blocker = tmp_path / "not-a-dir"
    blocker.write_bytes(b"")
    managed["x64"] = str(blocker / "Managed")
    monkeypatch.setattr(rmd, "BKP", bkp)
    monkeypatch.setattr(rmd, "MANAGED", managed)
    rc = rmd.main(["restore_memoria_dll.py", "20260722-095733"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "COPY FAILED" in out
    assert "PARTIAL: 0 file(s) restored, 1 FAILED" in out
