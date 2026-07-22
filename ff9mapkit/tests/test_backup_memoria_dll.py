"""``tools/backup_memoria_dll.py`` -- the standard pre-build engine snapshot.

The writer-side companion to ``test_restore_memoria_dll.py``: the backup step used to be a
hand-typed copy command, which produced four naming conventions in backups/ and never once
captured Memoria.Prime.dll / UnityEngine.UI.dll. These tests pin (a) that the full 3-DLL x
2-arch set is captured under the ONE canonical name and the restore one-liner is printed,
(b) the round-trip -- what backup writes, restore routes back byte-identical per arch,
(c) that a partial or empty capture exits non-zero (partial backup = partial safety),
(d) that a label carrying an arch token is refused before anything is written, and (e) that
an existing backup file is never overwritten.

Every fixture install is built explicitly under tmp_path. Nothing here may fall through to
the developer's real backups/ or game install.
"""

import importlib.util
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]


def _load(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "tools" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


bmd = _load("backup_memoria_dll")
rmd = _load("restore_memoria_dll")

DLLS = ("Assembly-CSharp.dll", "Memoria.Prime.dll", "UnityEngine.UI.dll")


# ---------------------------------------------------------------- fixtures

def _install(tmp_path, dlls=DLLS):
    """A fake live install (both arches' Managed dirs populated with distinct bytes per
    arch x dll) plus an empty backups dir. Returns (bkp, managed)."""
    bkp = tmp_path / "backups"
    bkp.mkdir(parents=True)
    managed = {}
    for arch in ("x64", "x86"):
        d = tmp_path / "game" / arch / "FF9_Data" / "Managed"
        d.mkdir(parents=True)
        for dll in dlls:
            (d / dll).write_bytes(f"{arch}:{dll}".encode())
        managed[arch] = str(d)
    return str(bkp), managed


def _patched_main(monkeypatch, bkp, managed, argv_tail=()):
    monkeypatch.setattr(bmd, "BKP", bkp)
    monkeypatch.setattr(bmd, "MANAGED", managed)
    return bmd.main(["backup_memoria_dll.py", *argv_tail])


# ---------------------------------------------------------------- the happy path

def test_full_set_captured_with_canonical_names_and_restore_hint(tmp_path, capsys, monkeypatch):
    bkp, managed = _install(tmp_path)
    rc = _patched_main(monkeypatch, bkp, managed)
    out = capsys.readouterr().out
    assert rc == 0
    assert "Done: full set captured (6/6)" in out
    names = sorted(p.name for p in pathlib.Path(bkp).iterdir())
    assert len(names) == 6
    # one shared timestamp across the whole set, in the canonical per-arch form
    stamps = set()
    for n in names:
        m = re.fullmatch(r"(Assembly-CSharp|Memoria\.Prime|UnityEngine\.UI)\.(x64|x86)\.dll\.(\d{8}-\d{6})", n)
        assert m, n
        stamps.add(m.group(3))
    assert len(stamps) == 1
    (ts,) = stamps
    assert f"Restore with: py tools/restore_memoria_dll.py {ts}" in out
    # bytes match the live source they were taken from
    assert (pathlib.Path(bkp) / f"Memoria.Prime.x86.dll.{ts}").read_bytes() == b"x86:Memoria.Prime.dll"


def test_round_trip_backup_then_restore_is_byte_identical_per_arch(tmp_path):
    """The compatibility contract between the two tools: what backup writes, restore routes
    back into the right arch's Managed folder, byte-identical, via the printed selector."""
    bkp, managed = _install(tmp_path)
    done, missing, failed = bmd.backup("20260722-101500", "pre-s48", bkp, managed)
    assert (done, missing, failed) == (6, 0, 0)
    # a second, empty install stands in for a machine after a bad build
    _, fresh = _install(tmp_path / "after", dlls=())
    restored, rfailed = rmd.restore("20260722-101500", bkp, fresh)
    assert (restored, rfailed) == (6, 0)
    for arch in ("x64", "x86"):
        for dll in DLLS:
            got = (pathlib.Path(fresh[arch]) / dll).read_bytes()
            assert got == f"{arch}:{dll}".encode()


def test_canonical_names_classify_arch_on_the_restore_side():
    for dll in DLLS:
        for arch in ("x64", "x86"):
            name = bmd.canonical_name(dll, arch, "20260101-000000", "pre-s48")
            assert rmd.backup_arch(name) == arch, name


# ---------------------------------------------------------------- partial/empty = non-zero

def test_missing_source_dll_is_partial_and_exits_nonzero(tmp_path, capsys, monkeypatch):
    bkp, managed = _install(tmp_path)
    (pathlib.Path(managed["x86"]) / "UnityEngine.UI.dll").unlink()
    rc = _patched_main(monkeypatch, bkp, managed)
    out = capsys.readouterr().out
    assert rc == 1
    assert "PARTIAL: 5/6 captured (1 missing, 0 failed)" in out
    assert "Restore what WAS captured" in out
    assert len(list(pathlib.Path(bkp).iterdir())) == 5


def test_empty_install_backs_up_nothing_and_exits_nonzero(tmp_path, capsys, monkeypatch):
    bkp, managed = _install(tmp_path, dlls=())
    rc = _patched_main(monkeypatch, bkp, managed)
    out = capsys.readouterr().out
    assert rc == 1
    assert "NOTHING BACKED UP" in out
    assert "Do NOT build" in out
    assert list(pathlib.Path(bkp).iterdir()) == []


# ---------------------------------------------------------------- label rules

def test_label_lands_in_the_name_and_selects_on_restore(tmp_path):
    bkp, managed = _install(tmp_path)
    bmd.backup("20260722-101500", "pre-s48", bkp, managed)
    by_arch = rmd.find_backups("Assembly-CSharp.dll", "pre-s48", bkp)
    assert set(by_arch) == {"x64", "x86"}
    assert by_arch["x64"].endswith("Assembly-CSharp.x64.dll.pre-s48.20260722-101500")


def test_arch_token_label_is_refused_before_anything_is_written(tmp_path, capsys, monkeypatch):
    bkp, managed = _install(tmp_path)
    rc = _patched_main(monkeypatch, bkp, managed, argv_tail=("pre-x86",))
    out = capsys.readouterr().out
    assert rc == 1
    assert "REFUSED" in out and "arch token" in out
    assert list(pathlib.Path(bkp).iterdir()) == []          # truly nothing written
    # same for a charset violation (dots would break [._-] tokenization)
    assert bmd.check_label("pre.s48") is not None
    assert bmd.check_label("pre-s48") is None


# ---------------------------------------------------------------- never overwrite a backup

def test_existing_destination_is_never_overwritten(tmp_path, capsys):
    bkp, managed = _install(tmp_path)
    prior = pathlib.Path(bkp) / bmd.canonical_name("Assembly-CSharp.dll", "x64", "20260722-101500")
    prior.write_bytes(b"the-old-snapshot")
    done, missing, failed = bmd.backup("20260722-101500", "", bkp, managed)
    out = capsys.readouterr().out
    assert (done, missing, failed) == (5, 0, 1)
    assert "NOT overwritten" in out
    assert prior.read_bytes() == b"the-old-snapshot"


# ---------------------------------------------------------------- missing backups dir

def test_missing_backups_dir_is_created_with_a_worktree_warning(tmp_path, capsys, monkeypatch):
    _, managed = _install(tmp_path)
    bkp = str(tmp_path / "no-such-dir" / "backups")
    rc = _patched_main(monkeypatch, bkp, managed)
    out = capsys.readouterr().out
    assert rc == 0
    assert "created" in out and "WORKTREE" in out
    assert len(list(pathlib.Path(bkp).iterdir())) == 6
