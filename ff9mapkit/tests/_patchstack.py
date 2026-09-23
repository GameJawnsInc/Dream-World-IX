"""Read the LIVE Memoria patch stack (``memoria-patches/``) for tests that pin a kit catalog to the engine.

The custom engine routes some ``fldMapNo`` gates through ``EffectiveFieldId`` and leaves the rest on the raw id; a
kit catalog that says which behaviours a fork keeps (walkmesh hotfixes, the idgated lost-on-mint axes) has to
agree with it. The patch files are the engine's source of truth (the shared Memoria clone can lose patches), and
they ship in this repo, so these checks need no clone and no install. Stack order and the dead-patch skip set
come from ``tools/memoria_stack_replay.py``.
"""
from __future__ import annotations

import importlib.util
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location("memoria_stack_replay", REPO / "tools" / "memoria_stack_replay.py")
msr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(msr)

#: ``EffectiveFieldId(FF9StateSystem.Common.FF9.fldMapNo) <op> <id>`` -- a gate wrapped INLINE (s24/s29/s65).
#: ``.format(op, id)``; ``op`` is a regex (``==``, ``!=``, ``[<>]=``).
WRAPPED = r"EffectiveFieldId\(FF9StateSystem\.Common\.FF9\.fldMapNo\) {} {}\b"


def live_patches() -> list:
    """The live stack's patch bytes, in stack order, dead patches skipped."""
    return [(msr.PATCHES / n).read_bytes() for n in msr.stack() if n not in msr.DEAD]


def _changed(file_name, pattern, patches):
    """``(+1 | -1, line)`` for every added/removed line matching ``pattern`` in ``file_name`` (None = any file)."""
    if patches is None:
        patches = live_patches()
    for blob in patches:
        for path, sec in msr.sections(blob):
            if not path or (file_name is not None
                            and path.replace("\\", "/").rsplit("/", 1)[-1] != file_name):
                continue
            for ln in sec.decode("utf-8", "replace").splitlines():
                if ln.startswith(("+++", "---")) or not ln.startswith(("+", "-")) or not re.search(pattern, ln):
                    continue
                yield (1 if ln.startswith("+") else -1), ln[1:].strip()


def net_added(file_name, pattern, patches=None) -> int:
    """Across the LIVE patch stack -- or ``patches``, a list of patch bytes -- lines ADDED to ``file_name``
    (a bare file name; None = every file) matching ``pattern``, minus lines removed: how many sites the stack
    leaves in that form. Context lines never count."""
    return sum(sign for sign, _ in _changed(file_name, pattern, patches))


def net_lines(file_name, pattern, patches=None) -> list:
    """The added lines themselves (stripped), net of any later patch that removes the same text -- for checking
    that every wrap the stack leaves in a file is one a catalog accounts for."""
    count = {}
    for sign, text in _changed(file_name, pattern, patches):
        count[text] = count.get(text, 0) + sign
    return [text for text, n in count.items() for _ in range(n)]


def touches(file_name, patches=None) -> bool:
    """True when any live patch has a section for ``file_name`` -- a file no patch touches runs stock code."""
    if patches is None:
        patches = live_patches()
    return any(path and path.replace("\\", "/").rsplit("/", 1)[-1] == file_name
               for blob in patches for path, _ in msr.sections(blob))
