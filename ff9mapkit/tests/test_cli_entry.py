"""``python -m ff9mapkit`` must work even when the current directory has a sibling folder named
``ff9mapkit``.

This is the bug a user hit running ``py -m ff9mapkit ...`` from the repo *parent*: Python picks up
the sibling ``ff9mapkit/`` folder as an empty PEP-420 namespace package, shadowing the real install,
so ``from . import __version__`` fails. ``__main__.py`` detects that shadow and repoints at the real
package. (On a clean site-packages install there's no shadow and ``-m`` works anyway, so this passes
either way -- it only fails if the shadow repair regresses.)

The precondition -- "``python -m ff9mapkit`` is runnable as an installed package" -- is probed at
RUNTIME by actually running it from a neutral dir, NOT via ``importlib.metadata``: a stray
``ff9mapkit.egg-info`` left in the tree (or xdist worker metadata leakage) makes
``importlib.metadata.distribution`` report "installed" even when the package isn't importable from
elsewhere, which used to make this test flakily FAIL under ``pytest -n`` instead of skipping. Running
the subprocess is the source of truth, so the result is deterministic regardless of how the suite is run.
"""

from __future__ import annotations

import subprocess
import sys

import pytest


def _dash_m_version(cwd) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-m", "ff9mapkit", "--version"],
                          cwd=cwd, capture_output=True, text=True)


def test_dash_m_runs_under_namespace_shadow(tmp_path):
    # The shadow-repair scenario is only meaningful when `python -m ff9mapkit` is actually runnable as an
    # installed package. Probe that from a NEUTRAL dir (no shadow) by really running it -- robust to a stray
    # egg-info / xdist metadata leakage (metadata presence != importable). If it isn't runnable here (a
    # multi-worktree no-install setup -- run from the kit root instead), the scenario is moot, so skip.
    neutral = tmp_path / "neutral"
    neutral.mkdir()
    if _dash_m_version(neutral).returncode != 0:
        pytest.skip("`python -m ff9mapkit` not runnable as an install here; namespace-shadow repair is moot")

    # The shadow trap: an empty dir named ff9mapkit shadows the real install as a PEP-420 namespace package.
    shadow = tmp_path / "shadow"
    (shadow / "ff9mapkit").mkdir(parents=True)
    r = _dash_m_version(shadow)
    assert r.returncode == 0, f"stdout={r.stdout!r}\nstderr={r.stderr!r}"
    assert "ff9mapkit" in (r.stdout + r.stderr)
