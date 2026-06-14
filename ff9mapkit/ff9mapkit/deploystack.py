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


# Relative paths (within a mod folder) of the CSVs the engine reads HIGHEST-PRIORITY-WINS (whole-file): the
# starting bag (GetCsvWithHighestPriority) and the 99-row growth curve (Leveling.csv, ff9level.cs:53). A single
# folder's whole file wins outright -> a higher-priority stacked folder SHADOWS the lower one's copy entirely.
# The other CSVs (ShopItems / DefaultEquipment / BaseStats / Actions / StatusData) MERGE low->high by id, so a
# stacked folder only collides per-id, NOT whole-file -- they are deliberately NOT listed here.
_PRESET_STEMS = ("Zidane", "Vivi", "Garnet", "Steiner", "Freya", "Quina", "Eiko", "Amarant", "Cinna1", "Cinna2",
                 "Marcus1", "Marcus2", "Blank1", "Blank2", "Beatrix1", "Beatrix2", "StageZidane", "StageCinna",
                 "StageMarcus", "StageBlank")
HIGHEST_WINS_CSVS = ("StreamingAssets/Data/Items/InitialItems.csv",
                     "StreamingAssets/Data/Characters/Leveling.csv",
                     *(f"StreamingAssets/Data/Characters/Abilities/{s}.csv" for s in _PRESET_STEMS))  # [[learn]] lists


def check_csv_shadow(game_dir, target_folder: str, csv_relpath: str,
                     folder_names: list | None = None) -> str | None:
    """Will a HIGHEST-PRIORITY-WINS CSV (``InitialItems.csv``) deployed into ``target_folder`` be SHADOWED by a
    higher-priority mod folder that also ships it? Unlike a ``.mes`` (per-block) or a MERGED CSV (per-id), a
    highest-wins WHOLE file is silently ignored if ANY higher folder ships its own copy -> the starting bag is
    dropped with no error. Mirrors :func:`check_text_block_shadow`. Returns a one-line warning, or ``None`` when
    clear / unreadable / the target isn't in the stack (no false alarm). The MERGED CSVs need no such check."""
    game_dir = Path(game_dir)
    order = folder_names
    if order is None:
        ini = game_dir / "Memoria.ini"
        order = parse_folder_names(ini.read_text(encoding="utf-8", errors="ignore")) if ini.is_file() else []
    if target_folder not in order:
        return None
    higher = order[:order.index(target_folder)]
    rel = csv_relpath.replace("\\", "/")
    shadowed_by = next((f for f in higher if (game_dir / f / rel).is_file()), None)
    if shadowed_by is None:
        return None
    name = rel.rsplit("/", 1)[-1]
    return (f"{name} SHADOWED: '{shadowed_by}' is HIGHER priority than '{target_folder}' in Memoria.ini "
            f"FolderNames and also ships {name}, which is read HIGHEST-PRIORITY-WINS -- the engine uses "
            f"'{shadowed_by}'s {name}, not yours (your starting bag is silently dropped). Deploy to the "
            f"highest-priority folder, or remove the higher folder's {name}.")


# ---- cross-folder NAME-collision guard (scene/.eb files resolve BY NAME, highest-folder-wins) ----
# A field's scene (``FBG_*``) and event script (``EVT_*.eb.bytes``) are looked up by NAME, and -- exactly like
# the highest-wins CSV above -- the engine serves the copy from the FIRST FolderNames folder that has it. So two
# worktrees/campaigns that fork the SAME source field deploy IDENTICALLY-named FBG/EVT into different folders;
# the higher folder's (WRONG) fork wins -> a torn load / black screen. (This bit the Dali chain until
# ``import-chain --name-prefix`` namespaced every member.) This guard catches the collision at deploy time.

@dataclass
class NameCollision:
    """One scene/.eb name a deploy would put in ``target_folder`` that ANOTHER live FolderNames folder already
    ships. ``kind`` is ``"eb"`` or ``"scene"``; ``name`` is the on-disk base name (``EVT_DC_DL_ENT`` /
    ``FBG_N11_DC_DL_ENT``). ``relation``: ``"shadows_us"`` (the other folder is higher priority -> it serves its
    copy, ours is dead), ``"we_shadow"`` (we are higher -> we break the other), ``"ambiguous"`` (the target isn't
    listed in FolderNames yet, so whichever order it lands in decides the winner)."""
    kind: str
    name: str
    other_folder: str
    relation: str


def eb_names_at(root) -> set:
    """The EVT base names (``EVT_*.eb.bytes`` stems, extension stripped) a mod/dist root ships, across all langs."""
    d = ModLayout(Path(root)).eventbinary_field_dir
    return {p.name[:-len(".eb.bytes")] for p in d.rglob("*.eb.bytes")} if d.is_dir() else set()


def scene_names_at(root) -> set:
    """The FBG scene-dir names a mod/dist root ships."""
    d = ModLayout(Path(root)).fieldmaps_dir
    return {p.name for p in d.iterdir() if p.is_dir()} if d.is_dir() else set()


def check_name_collisions(game_dir, target_folder: str, eb_names, scene_names,
                          folder_names: list | None = None) -> list:
    """Do any EVT/.eb or FBG-scene names a deploy puts in ``target_folder`` collide (same name) with one a
    DIFFERENT live FolderNames folder already ships? Returns a list of :class:`NameCollision` (``[]`` => clear).
    Reads ``Memoria.ini`` ``FolderNames`` (unless ``folder_names`` is passed); degrades to ``[]`` when the stack
    can't be read. The TARGET folder is EXCLUDED -- a redeploy of the same campaign replaces its own files in
    place, which is not a collision. Only folders actually in the stack are checked (others aren't loaded)."""
    game_dir = Path(game_dir)
    order = folder_names
    if order is None:
        ini = game_dir / "Memoria.ini"
        order = parse_folder_names(ini.read_text(encoding="utf-8", errors="ignore")) if ini.is_file() else []
    others = [f for f in order if f != target_folder]
    if not others:
        return []
    ti = order.index(target_folder) if target_folder in order else None
    want = {"eb": set(eb_names), "scene": set(scene_names)}
    out: list = []
    for f in others:
        have = {"eb": eb_names_at(game_dir / f), "scene": scene_names_at(game_dir / f)}
        rel = "ambiguous" if ti is None else ("shadows_us" if order.index(f) < ti else "we_shadow")
        for kind in ("eb", "scene"):
            for nm in sorted(want[kind] & have[kind]):
                out.append(NameCollision(kind, nm, f, rel))
    return out


def name_collision_warning(collisions: list, target_folder: str) -> str | None:
    """A human-readable multi-line warning for cross-folder name collisions, or ``None`` when clear."""
    if not collisions:
        return None
    by_folder: dict = {}
    for c in collisions:
        by_folder.setdefault(c.other_folder, []).append(c)
    rel_tag = {
        "shadows_us": "is HIGHER priority -> it shadows YOURS (your fields won't load)",
        "we_shadow":  "is LOWER priority -> YOURS shadows it (you break that campaign)",
        "ambiguous":  f"is in the stack ('{target_folder}' isn't listed yet -> FolderNames order decides)",
    }
    lines = [f"NAME COLLISION: {len(collisions)} scene/.eb name(s) this deploy puts in '{target_folder}' are "
             f"ALSO shipped by another Memoria.ini FolderNames folder -- these resolve BY NAME, "
             f"highest-folder-wins, so the WRONG fork loads (a silent shadow -> torn load / black screen):"]
    for f, cs in by_folder.items():
        names = ", ".join(c.name for c in cs[:8]) + (" ..." if len(cs) > 8 else "")
        lines.append(f"  - vs '{f}' ({rel_tag[cs[0].relation]}): {names}")
    lines.append("Fix: re-fork the chain with a campaign-unique prefix -- `ff9mapkit import-chain <seed> "
                 "--name-prefix <TAG>` -- so every FBG/EVT name is globally unique; or drop the colliding "
                 "folder from Memoria.ini FolderNames.")
    return "\n".join(lines)


# ---- cross-folder ID-collision guard (FF9DBAll.EventDB[id] is GLOBAL across folders) ----
# A field/battle id is the KEY into the global ``FF9DBAll.EventDB`` (id -> eb-name), which DataPatchers populates
# from EVERY FolderNames folder's ``DictionaryPatch.txt`` at boot. Two folders that register the SAME id collide:
# ``EventDB[id]`` ends up holding ONE name, so the OTHER registration's field/battle loads the WRONG ``.eb`` ->
# ``loadEventData`` null -> ``EventEngine.StartEvents(ebFileData=null)`` -> black screen. This cost a multi-hour
# debug: ``-ate``'s ``FieldScene 30011 TEST30011`` collided with ``-bb``'s ``BattleScene 30011 CAMKEYS``, so
# warping to field 30011 tried to load ``EVT_BATTLE_CAMKEYS`` from the FIELD path (not there) -> null. Because the
# names DIFFER (``TEST30011`` vs ``CAMKEYS``), the NAME guard above does NOT catch it -- this id guard does.
# NOTE: which registration "wins" ``EventDB[id]`` is DataPatchers processing-order dependent (in the 30011 case
# the battle won despite ``-bb`` being a higher-priority folder), so EITHER side can break -> flag ANY collision
# and don't assert a winner. (Memory: project-ff9-eventdb-id-collision.)

@dataclass
class IdCollision:
    """One field/scene id a deploy registers that ANOTHER live FolderNames folder's ``DictionaryPatch.txt``
    already uses. ``other_kind`` is ``"FieldScene"``/``"BattleScene"``; ``other_name`` is that line's MAPID /
    scene name (for the message)."""
    field_id: int
    other_folder: str
    other_kind: str
    other_name: str


def dictionary_ids_at(root) -> dict:
    """Map ``id -> (kind, name)`` for every ``FieldScene``/``BattleScene`` line in a mod/dist root's
    ``DictionaryPatch.txt`` (``{}`` if absent/unreadable). ``kind`` = the leading token; ``name`` = the MAPID
    (``FieldScene`` field 3) or scene name (``BattleScene`` field 2). On a duplicate id within one file the last
    line wins (mirrors the engine's last-writer-wins)."""
    out: dict = {}
    p = Path(root) / "DictionaryPatch.txt"
    if not p.is_file():
        return out
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.split()
        if len(parts) < 2 or parts[0] not in ("FieldScene", "BattleScene"):
            continue
        try:
            fid = int(parts[1])
        except ValueError:
            continue
        # the human name sits at a DIFFERENT field by kind: FieldScene <id> <area> <MAPID> <NAME> <txt> (field 3
        # = MAPID); BattleScene <id> <NAME> <BBG> (field 2 = scene name).
        name = (parts[3] if len(parts) > 3 else "") if parts[0] == "FieldScene" else (parts[2] if len(parts) > 2 else "")
        out[fid] = (parts[0], name)
    return out


def check_id_collisions(game_dir, target_folder: str, ids, folder_names: list | None = None) -> list:
    """Do any field/scene ``ids`` a deploy registers into ``target_folder`` collide with an id ANOTHER live
    FolderNames folder's ``DictionaryPatch`` already uses? (``EventDB`` is GLOBAL -> a shared id makes one side
    load the wrong ``.eb`` -> black screen.) Returns a list of :class:`IdCollision` (``[]`` => clear). Reads
    ``Memoria.ini`` ``FolderNames`` (unless ``folder_names`` passed); degrades to ``[]`` when unreadable. The
    TARGET folder is EXCLUDED (a redeploy reuses its own id, not a collision); only folders actually in the stack
    are checked (others aren't loaded). Distinct from :func:`check_name_collisions` -- that catches same-NAME
    files; this catches same-ID registrations whose names may DIFFER (the case that guard misses)."""
    game_dir = Path(game_dir)
    order = folder_names
    if order is None:
        ini = game_dir / "Memoria.ini"
        order = parse_folder_names(ini.read_text(encoding="utf-8", errors="ignore")) if ini.is_file() else []
    others = [f for f in order if f != target_folder]
    if not others:
        return []
    want = sorted({int(i) for i in ids})
    out: list = []
    for f in others:
        their = dictionary_ids_at(game_dir / f)
        for i in want:
            if i in their:
                kind, name = their[i]
                out.append(IdCollision(i, f, kind, name))
    return out


def id_collision_warning(collisions: list, target_folder: str) -> str | None:
    """A human-readable multi-line warning for cross-folder id collisions, or ``None`` when clear."""
    if not collisions:
        return None
    lines = [f"ID COLLISION: {len(collisions)} id(s) this deploy registers in '{target_folder}' are ALSO used by "
             f"another Memoria.ini FolderNames folder. FF9DBAll.EventDB is GLOBAL across folders, so a shared id "
             f"maps to ONE .eb -- one side loads the WRONG script (null .eb -> StartEvents(null) -> black screen):"]
    for c in collisions:
        lines.append(f"  - id {c.field_id} vs '{c.other_folder}' ({c.other_kind} '{c.other_name}')")
    lines.append("Fix: use an id no other stacked folder registers -- e.g. your worktree's `.ff9deploy.toml` "
                 "scratch/campaign band. (Diagnose: grep -rn '<id>' FF9CustomMap*/DictionaryPatch.txt.)")
    return "\n".join(lines)
