"""Atomic file writes for load-bearing files.

The rule: a file another layer reads (a save container, ``Memoria.ini``, a
``DictionaryPatch.txt`` registry, a hand-authored ``field.toml``, an engine DLL) must never
be observable half-written. The pattern -- write a sibling ``.tmp``, then ``os.replace`` it
in (an atomic rename on both Windows and POSIX) -- lived in per-site copies (prefs,
save_items, models/thumbcache, workspace/thumbs); new writers route through here instead of
``Path.write_text``/``write_bytes`` or a bare ``open(..., "w")``.
"""

from __future__ import annotations

import os
from pathlib import Path


def atomic_write_bytes(path: "Path | str", data: bytes) -> None:
    """Write ``data`` to ``path`` so the file is never observed half-written."""
    p = Path(path)
    tmp = p.with_name(p.name + ".tmp")
    try:
        with open(tmp, "wb") as fh:
            fh.write(data)
        os.replace(tmp, p)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def atomic_write_text(path: "Path | str", text: str, encoding: str = "utf-8",
                      newline: "str | None" = None) -> None:
    """Drop-in atomic ``Path.write_text``: same text-mode newline translation, same encoding
    default as the kit's writers, but staged through a sibling ``.tmp`` + ``os.replace``."""
    p = Path(path)
    tmp = p.with_name(p.name + ".tmp")
    try:
        with open(tmp, "w", encoding=encoding, newline=newline) as fh:
            fh.write(text)
        os.replace(tmp, p)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
