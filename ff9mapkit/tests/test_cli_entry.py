"""``python -m ff9mapkit`` must work even when the current directory has a sibling folder named
``ff9mapkit``.

This is the bug a user hit running ``py -m ff9mapkit ...`` from the repo *parent*: Python picks up
the sibling ``ff9mapkit/`` folder as an empty PEP-420 namespace package, shadowing the real install,
so ``from . import __version__`` fails. ``__main__.py`` detects that shadow and repoints at the real
package. (On a clean site-packages install there's no shadow and ``-m`` works anyway, so this passes
either way -- it only fails if the shadow repair regresses.)
"""

from __future__ import annotations

import importlib.metadata
import subprocess
import sys

import pytest


def _installed() -> bool:
    """True if ff9mapkit is pip-installed (in site-packages). The namespace-shadow REPAIR only has a real
    package to repoint at when there IS an install; with no install (a deliberate multi-worktree setup --
    run from the kit root instead), `-m ff9mapkit` from a FOREIGN dir resolves nothing, so the scenario is
    moot and the test skips."""
    try:
        importlib.metadata.distribution("ff9mapkit")
        return True
    except importlib.metadata.PackageNotFoundError:
        return False


@pytest.mark.skipif(not _installed(), reason="ff9mapkit not pip-installed; `-m` from a foreign dir needs an "
                                             "install (run from the kit root). Uninstalled for multi-worktree.")
def test_dash_m_runs_under_namespace_shadow(tmp_path):
    (tmp_path / "ff9mapkit").mkdir()           # an empty dir named ff9mapkit -> the shadow trap
    r = subprocess.run([sys.executable, "-m", "ff9mapkit", "--version"],
                       cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 0, f"stdout={r.stdout!r}\nstderr={r.stderr!r}"
    assert "ff9mapkit" in (r.stdout + r.stderr)
