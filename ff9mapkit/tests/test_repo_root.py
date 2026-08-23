"""``tools/repo_root.py`` -- the main-repo resolver behind every backup/revert dir of game-install state.

The trap it closes (project-ff9-worktree-parked-backups, fired twice on 2026-07-30): a tool that roots
``backups/`` / ``tools/scroll_out/`` at ``Path(__file__)/..`` parks a deploy's ONLY undo in whichever
ephemeral agent worktree it ran from -- the live install keeps the deploy while the backup evaporates
with the tree. The resolver answers the MAIN repo from anywhere (the common git dir's parent), and
falls back to the running checkout when git cannot answer, so a gitless run loses nothing it had.

The synthetic-repo tests build a real ``git init`` main + a real linked worktree under tmp_path --
nothing here reads the developer's actual repos. The fallback tests swap NAMES on the private module
instance (never a shared module's attributes -- project-ff9-global-module-monkeypatch).
"""
import importlib.util
import os
import pathlib
import shutil
import subprocess

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
_RR = REPO / "tools" / "repo_root.py"
if not _RR.is_file():
    pytest.skip("repo-only tools/ script not present (installed-package layout)", allow_module_level=True)

_spec = importlib.util.spec_from_file_location("repo_root", _RR)
rr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rr)


def _git(*args, cwd):
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


@pytest.fixture
def main_and_worktree(tmp_path):
    """A synthetic main repo (one commit) + a real linked worktree, each with a tools/ dir."""
    if shutil.which("git") is None:
        pytest.skip("git not available")
    main = tmp_path / "main"
    main.mkdir()
    if _git("init", cwd=main).returncode:
        pytest.skip("git init failed in tmp_path")
    _git("-c", "user.name=t", "-c", "user.email=t@t", "commit", "--allow-empty", "-m", "init", cwd=main)
    wt = tmp_path / "wt"
    r = _git("worktree", "add", "--detach", str(wt), cwd=main)
    if r.returncode:
        pytest.skip(f"git worktree add failed: {r.stderr.strip()}")
    (main / "tools").mkdir()
    (wt / "tools").mkdir()
    if rr._git_common_dir(main) is None:                    # e.g. a git too old for --path-format=absolute
        pytest.skip("this git cannot answer --git-common-dir --path-format=absolute")
    return main, wt


def test_from_the_main_repo_resolves_to_itself(main_and_worktree):
    main, _ = main_and_worktree
    got = rr.main_repo_root(start=main / "tools")
    assert os.path.samefile(got, main)


def test_from_a_linked_worktree_resolves_to_the_main_repo_not_the_worktree(main_and_worktree):
    """THE regression: run from an agent worktree, the old ``__file__/..`` rooting answered the
    worktree -- so the deploy's only backups + revert scripts landed in a tree that gets cleaned."""
    main, wt = main_and_worktree
    got = rr.main_repo_root(start=wt / "tools")
    assert os.path.samefile(got, main)
    assert not os.path.samefile(got, wt)


def test_gitless_fallback_is_the_running_checkout(tmp_path, monkeypatch):
    """When git cannot answer, the pre-fix behavior survives: the caller's own checkout (start's
    parent), or an explicit ``fallback``. Seam: swap the private module's ``_git_common_dir`` NAME."""
    monkeypatch.setattr(rr, "_git_common_dir", lambda start: None)
    tools = tmp_path / "checkout" / "tools"
    tools.mkdir(parents=True)
    assert rr.main_repo_root(start=tools) == tmp_path / "checkout"
    assert rr.main_repo_root(start=tools, fallback=tmp_path / "elsewhere") == tmp_path / "elsewhere"


def test_a_missing_git_binary_is_a_fallback_not_a_crash(tmp_path, monkeypatch):
    """The subprocess call itself failing (no git on PATH -> FileNotFoundError) must degrade to the
    fallback. The stub replaces the ``subprocess`` NAME on the private module instance; the except
    clause reads the module-level ``_GIT_ERRORS`` tuple, so it never dereferences the stub."""
    class _NoGit:
        @staticmethod
        def run(*a, **k):
            raise FileNotFoundError("git")
    monkeypatch.setattr(rr, "subprocess", _NoGit())
    tools = tmp_path / "checkout" / "tools"
    tools.mkdir(parents=True)
    assert rr.main_repo_root(start=tools) == tmp_path / "checkout"


def test_this_checkout_resolves_to_a_root_that_owns_the_real_git_dir():
    """Smoke on the real repo this suite runs in: the answer owns a ``.git`` DIRECTORY (a linked
    worktree's own ``.git`` is a file -- so this discriminates main from worktree wherever we run)."""
    got = rr.main_repo_root()
    assert (pathlib.Path(got) / ".git").is_dir()
    assert (pathlib.Path(got) / "tools").is_dir()


def test_default_start_is_the_tools_dir_of_this_checkout():
    """The default ``start`` must be where the SCRIPTS live (tools/), so every shim resolves from its
    own location -- and the default fallback is then that checkout's root, the pre-fix behavior."""
    assert pathlib.Path(rr._HERE).name == "tools"


# ---------------------------------------------------------------- the consumers, statically

def _src(name):
    return (REPO / "tools" / f"{name}.py").read_text(encoding="utf-8")


def test_every_backup_writer_spends_the_resolver():
    """Every tool that backs up GAME-INSTALL state must root its backup + revert dirs at the MAIN repo:
    deploy_field (BK + OUT), wire_newgame_from_stock (backups_dir/reverts_dir), the DLL backup/restore pair
    (BKP, defined once in restore -- backup_memoria_dll imports it, so the pair is covered by restore's
    definition), and the three sibling deploy shims (deploy_battle's BK + OUT, deploy_campaign's and
    deploy_journey's backups_dir/reverts_dir)."""
    for name in ("deploy_field", "wire_newgame_from_stock", "restore_memoria_dll",
                 "deploy_battle", "deploy_campaign", "deploy_journey"):
        assert "main_repo_root" in _src(name), f"tools/{name}.py no longer spends repo_root.main_repo_root"
    assert "from restore_memoria_dll import" in _src("backup_memoria_dll")
    # and the exact worktree-parked rootings must not come back
    assert '"..", "backups"' not in _src("deploy_field")
    assert '"..", "backups"' not in _src("restore_memoria_dll")
    assert 'REPO / "backups"' not in _src("wire_newgame_from_stock")
    for name in ("deploy_battle", "deploy_campaign", "deploy_journey"):
        assert 'REPO / "backups"' not in _src(name), f"tools/{name}.py roots backups at the RUNNING checkout"
    assert 'Path(os.path.dirname(__file__)) / "scroll_out"' not in _src("deploy_battle")
    for name in ("deploy_campaign", "deploy_journey"):
        assert 'HERE / "scroll_out"' not in _src(name), f"tools/{name}.py roots reverts at the RUNNING checkout"


def test_the_per_worktree_deploy_pin_did_not_move_with_the_backups():
    """The OTHER root must NOT follow: ``.ff9deploy.toml`` is the deliberately PER-WORKTREE deploy pin, so
    reading it from the main repo would un-isolate every session's mod folder (the exact clobber the pin
    exists to prevent). It stays at the running checkout in both shims that read one."""
    for name in ("deploy_battle", "deploy_campaign"):
        assert 'REPO / ".ff9deploy.toml"' in _src(name), \
            f"tools/{name}.py must read its deploy pin from the RUNNING checkout"
