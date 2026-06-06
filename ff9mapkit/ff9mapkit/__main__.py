"""Enable ``python -m ff9mapkit ...`` (identical to the ``ff9mapkit`` console command).

Handy when the package isn't pip-installed on PATH -- run it from the repo:
    py -m ff9mapkit build my_room.field.toml --out dist

Robustness: running ``python -m ff9mapkit`` from a directory whose child folder is ALSO named
``ff9mapkit`` (e.g. the repo *parent* that contains the ``ff9mapkit/`` project) makes Python pick
up that folder as an empty PEP-420 namespace package, shadowing the real install -- so
``from . import __version__`` blows up with "cannot import name ... (unknown location)". This file
lives at the real package's true path, so we detect the shadow and repoint the import there.
"""

import sys
from pathlib import Path


def _ensure_real_package() -> None:
    """If ``ff9mapkit`` resolved to a namespace shadow (a folder with no __init__), repoint it at the
    real package -- the directory holding THIS file -- so the absolute import below loads code."""
    pkg = sys.modules.get("ff9mapkit")
    if pkg is not None and getattr(pkg, "__file__", None) is not None:
        return                                   # already the real, importable package -- nothing to do
    real_parent = str(Path(__file__).resolve().parent.parent)   # dir that CONTAINS the real ff9mapkit/
    sys.path.insert(0, real_parent)
    for name in [m for m in sys.modules if m == "ff9mapkit" or m.startswith("ff9mapkit.")]:
        if name != __name__:                     # keep this running module
            del sys.modules[name]
    import importlib
    importlib.invalidate_caches()


_ensure_real_package()
from ff9mapkit.cli import main      # noqa: E402  (must follow the sys.path repair above)

if __name__ == "__main__":
    sys.exit(main())
