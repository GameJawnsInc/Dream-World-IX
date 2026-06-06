"""``python -m ff9mapkit`` must work even when the current directory has a sibling folder named
``ff9mapkit``.

This is the bug a user hit running ``py -m ff9mapkit ...`` from the repo *parent*: Python picks up
the sibling ``ff9mapkit/`` folder as an empty PEP-420 namespace package, shadowing the real install,
so ``from . import __version__`` fails. ``__main__.py`` detects that shadow and repoints at the real
package. (On a clean site-packages install there's no shadow and ``-m`` works anyway, so this passes
either way -- it only fails if the shadow repair regresses.)
"""

from __future__ import annotations

import subprocess
import sys


def test_dash_m_runs_under_namespace_shadow(tmp_path):
    (tmp_path / "ff9mapkit").mkdir()           # an empty dir named ff9mapkit -> the shadow trap
    r = subprocess.run([sys.executable, "-m", "ff9mapkit", "--version"],
                       cwd=tmp_path, capture_output=True, text=True)
    assert r.returncode == 0, f"stdout={r.stdout!r}\nstderr={r.stderr!r}"
    assert "ff9mapkit" in (r.stdout + r.stderr)
