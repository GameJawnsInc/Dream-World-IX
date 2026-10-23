"""``tools/build_saxaudio.py`` -- the native audio plugin build + install rails.

Pins that the wrapper (a) builds a PINNED upstream commit with dash-style list args and the x86 ->
Win32 platform mapping, (b) refuses to touch Plugins while FF9 runs, (c) backs up both arches BEFORE
installing and sha-verifies the landing, and (d) restores the newest backup.

Every fixture install is built under tmp_path; the fake runner never touches msbuild or the game.
"""

import importlib.util
import os
import pathlib
import re
import types

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("build_saxaudio", REPO / "tools" / "build_saxaudio.py")
bs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(bs)


@pytest.fixture
def fake_install(tmp_path, monkeypatch):
    plugins = {}
    for arch in bs.ARCHES:
        d = tmp_path / "game" / arch / "FF9_Data" / "Plugins"
        d.mkdir(parents=True)
        (d / bs.DLL).write_bytes(b"stock-" + arch.encode())
        plugins[arch] = str(d)
    built = {}
    for arch in bs.ARCHES:
        p = tmp_path / "out" / arch / bs.DLL
        p.parent.mkdir(parents=True)
        p.write_bytes(b"fixed-" + arch.encode())
        built[arch] = str(p)
    bkp = tmp_path / "backups"
    monkeypatch.setattr(bs, "PLUGINS", plugins)
    monkeypatch.setattr(bs, "BKP", str(bkp))
    monkeypatch.setattr(bs, "RUN", lambda *a, **k: types.SimpleNamespace(stdout="", returncode=0))
    return types.SimpleNamespace(plugins=plugins, built=built, bkp=bkp)


def test_pinned_commit_is_a_full_sha():
    assert re.fullmatch(r"[0-9a-f]{40}", bs.PINNED_COMMIT)


def test_msbuild_args_are_dash_style_and_map_x86_to_win32():
    args = bs.msbuild_args("msbuild.exe", "SaXAudio.vcxproj", "x86", r"C:\o", r"C:\i")
    assert isinstance(args, list)
    assert "-p:Platform=Win32" in args and "-p:Configuration=Release" in args
    assert f"-p:PlatformToolset={bs.TOOLSET}" in args
    assert args[args.index("-t:Build")] and not any(a.startswith("/") for a in args[2:])
    assert f"-p:OutDir=C:\\o{os.sep}" in args


def test_install_refuses_while_ff9_runs(fake_install, monkeypatch):
    monkeypatch.setattr(bs, "RUN", lambda *a, **k: types.SimpleNamespace(stdout="FF9.exe  1234", returncode=0))
    with pytest.raises(SystemExit):
        bs.install(fake_install.built)
    for arch, d in fake_install.plugins.items():
        assert (pathlib.Path(d) / bs.DLL).read_bytes() == b"stock-" + arch.encode()


def test_install_backs_up_then_lands_then_restore_reverts(fake_install):
    assert bs.install(fake_install.built, "pre-test")
    for arch, d in fake_install.plugins.items():
        assert (pathlib.Path(d) / bs.DLL).read_bytes() == b"fixed-" + arch.encode()
        (bk,) = fake_install.bkp.glob(f"SaXAudio.{arch}.dll.pre-test.*")
        assert bk.read_bytes() == b"stock-" + arch.encode()
    assert bs.restore()
    for arch, d in fake_install.plugins.items():
        assert (pathlib.Path(d) / bs.DLL).read_bytes() == b"stock-" + arch.encode()
