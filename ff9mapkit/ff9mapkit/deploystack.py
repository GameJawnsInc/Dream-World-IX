"""Mod-folder STACK analysis -- the text-block SHADOW guard.

A field loads its dialogue by **mesID** (``text_block``), and the engine reads that ``.mes`` from the
**first** mod folder in ``Memoria.ini``'s ``FolderNames`` that provides ``field/<mesID>.mes`` (earliest =
highest priority). When several stacked mod folders -- e.g. per-worktree ``FF9CustomMap-*`` test slots --
all define the kit-default block **1073**, a *lower*-priority folder's text is **shadowed**: the field
renders some *other* folder's block-1073 text, not yours. (This bit an ``[[on_entry]]`` playtest: a probe
in ``FF9CustomMap-sf`` showed ``FF9CustomMap``'s stale "Rally-ho!" instead of its authored line.)

This module catches it at **deploy time** -- offline, by reading ``Memoria.ini`` + the folders'
``field/*.mes`` -- and suggests a concrete fix: a real mesID (one some stacked folder defines, hence a
valid ``MesDB`` id) that **no higher-priority folder** defines, so your folder's override wins.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .config import ModLayout


@dataclass
class ShadowReport:
    """The result of :func:`check_text_block_shadow`. ``shadowed_by`` is the first higher-priority folder
    that also defines ``text_block`` (``None`` => clear, your text wins). ``suggestions`` are valid mesIDs
    no higher-priority folder defines (safe alternatives). ``order`` is the parsed ``FolderNames`` stack."""
    target_folder: str
    text_block: int
    lang: str
    shadowed_by: str | None
    suggestions: list
    order: list

    @property
    def ok(self) -> bool:
        return self.shadowed_by is None


def parse_folder_names(memoria_ini_text: str) -> list:
    """The ordered mod-folder priority list from a ``Memoria.ini``'s ``FolderNames = "A", "B", ...`` line
    (highest priority first). ``[]`` if the key is absent. Skips comment lines (``;``) so the commented
    "Priorities is only a hint" note above the real line is ignored."""
    for line in memoria_ini_text.splitlines():
        s = line.strip()
        if s.startswith(";") or "=" not in s:
            continue
        key, _, value = s.partition("=")
        if key.strip().lower() == "foldernames":
            return re.findall(r'"([^"]+)"', value)
    return []


def _blocks_in(game_dir: Path, folder: str, lang: str) -> set:
    """The field text-block ids (``.mes`` file stems) a mod folder defines for ``lang``."""
    d = ModLayout(game_dir / folder).text_field_dir(lang)
    out = set()
    if d.is_dir():
        for p in d.glob("*.mes"):
            try:
                out.add(int(p.stem))
            except ValueError:
                pass
    return out


def check_text_block_shadow(game_dir, target_folder: str, text_block: int, lang: str = "us",
                            folder_names: list | None = None) -> ShadowReport:
    """Will a field's ``text_block`` deployed into ``target_folder`` be SHADOWED by a higher-priority mod
    folder? Reads ``Memoria.ini`` ``FolderNames`` (unless ``folder_names`` is passed) + each folder's
    ``field/*.mes``. Degrades gracefully (``shadowed_by=None``) when the stack can't be read; if the target
    isn't listed in ``FolderNames`` nothing is treated as higher-priority (no false alarm)."""
    game_dir = Path(game_dir)
    order = folder_names
    if order is None:
        ini = game_dir / "Memoria.ini"
        order = parse_folder_names(ini.read_text(encoding="utf-8", errors="ignore")) if ini.is_file() else []
    higher = order[:order.index(target_folder)] if target_folder in order else []
    blocks = {f: _blocks_in(game_dir, f, lang) for f in order}
    higher_blocks = set().union(*(blocks[f] for f in higher)) if higher else set()
    shadowed_by = next((f for f in higher if text_block in blocks.get(f, set())), None)
    # valid alternatives = real mesIDs (some stacked folder ships them, so they're in MesDB) that no
    # higher-priority folder defines -> your override wins. Exclude the current (shadowed) block.
    valid = set().union(*blocks.values()) if blocks else set()
    suggestions = sorted(valid - higher_blocks - {text_block})[:6]
    return ShadowReport(target_folder, text_block, lang, shadowed_by, suggestions, order)


def shadow_warning(report: ShadowReport, mod_folder: str | None = None) -> str | None:
    """A human-readable one-block warning for a shadowed deploy, or ``None`` when the block is clear.
    ``mod_folder`` overrides the report's ``target_folder`` label (they match in normal use)."""
    if report.ok:
        return None
    target = mod_folder or report.target_folder
    fix = (f" Use a real block no higher-priority folder defines -- e.g. text_block = {report.suggestions[0]}"
           f" (try: {', '.join(str(s) for s in report.suggestions[:4])})."
           if report.suggestions else
           " Set text_block to a real mesID that no higher-priority folder defines.")
    return (f"TEXT SHADOWED: block {report.text_block} is also defined by '{report.shadowed_by}', which is "
            f"HIGHER priority than '{target}' in Memoria.ini FolderNames -- the engine will show "
            f"'{report.shadowed_by}'s text, not yours.{fix}")
