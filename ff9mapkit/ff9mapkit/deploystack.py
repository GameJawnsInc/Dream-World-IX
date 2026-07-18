"""Mod-folder STACK analysis -- the text-block SHADOW guard.

A field loads its dialogue by **mesID** (``text_block``), keyed into ONE FLAT GLOBAL NUMERIC NAMESPACE
shared by every real FF9 field, every stacked mod folder, AND the base-game archive. Two distinct
collisions follow, and this module guards both.

**How the engine really resolves it (source-verified, and NOT "first folder wins"):**
``FF9TextTool.ImportStrtWithCumulativeModFiles`` iterates ``AssetManager.LoadStringMultiple(path).Reverse()``
and calls ``ExtractSentense`` on EVERY file into ONE shared dict; ``LoadStringMultiple`` walks
``FolderHighToLow`` and then unconditionally appends the BASE GAME asset via ``Resources.Load``. After the
``.Reverse()`` the base game is applied FIRST and the highest-priority folder LAST, and ``ExtractSentense``
writes ``table[id++]``. So it is a **per-txid CUMULATIVE MERGE, last writer wins**, not a whole-file pick.

1. **CROSS-FOLDER shadow** -- when several stacked folders (per-worktree ``FF9CustomMap-*`` test slots) all
   define the same block, the *lower*-priority folder's lines lose. (This bit an ``[[on_entry]]`` playtest: a
   probe in ``FF9CustomMap-sf`` showed ``FF9CustomMap``'s stale "Rally-ho!" instead of its authored line.)
2. **VANILLA squat** -- because the base game is always in the merge, a custom field's ``.mes`` on a REAL
   block overwrites *the shipping game's dialogue* for that location, in a single folder, with no stacking
   required. The overwrite is PARTIAL (a short custom file replaces only the leading txids and leaves the
   vanilla tail intact), which is exactly why it goes unnoticed. The kit default **1073 is not a free id --
   it is ``MES_MAGE2``, Black Mage Village** (real fields 3050-3059); ``8`` is Ice Cavern, ``22`` Lindblum
   Castle. Guarding (1) by "pick another real block" is what CAUSES (2), so the two checks must ship together.

The cure for BOTH is a mesID that belongs to nobody: a CUSTOM block registered via a DictionaryPatch
``MessageFile <id> <name>`` line (``DataPatchers`` parses it as a plain ``Int32``, no range check, no engine
rebuild), which satisfies the ``FieldScene`` gate ``!FF9DBAll.MesDB.ContainsKey(mesID)``. That is what
:func:`suggest_text_blocks` proposes and what ``register_text_block`` emits.

A **verbatim/native fork is exempt from (2) by construction** -- it re-ships its donor's own byte-identical
text on the donor's own block, so the "overwrite" is a no-op. Pass ``verbatim=True``. Remapping such a fork
off its donor block would be actively HARMFUL: voice-acting clips resolve off the same mesID
(``VoicePlayer``) and ``UniversalTextId``'s dual-language remap is keyed by a table of real mesIDs.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ._fieldtext import EVENT_ID_TO_MES
from .config import LANGS, ModLayout


# The scratch/hand-picked CUSTOM text-block band. Journeys carve their own disjoint windows from
# ``journey.TEXT_BLOCK_BASE`` (20000) -- one per campaign -- so single-field and hand-authored deploys
# allocate from HIGHER up to stay clear of any future journey window. (``examples/stolen-ember`` picked
# 30100-30102 by hand and lands in this band naturally.) Nothing in the engine caps a mesID: the
# ``MessageFile`` directive is a bare ``Int32.TryParse``.
SCRATCH_TEXT_BLOCK_BASE = 30000


def _vanilla_index() -> dict:
    """``block -> tuple(real field ids)`` -- the reverse of :data:`EVENT_ID_TO_MES`. Every key is a REAL
    shipping FF9 text block by construction (the table is generated from the engine's own ``eventIDToMESID``),
    so no id-range heuristic is needed -- and none would be correct: the table also holds the real overworld
    dispatchers 9000-9012 (block 68), which a ``field_id < 4000`` filter would wrongly exclude."""
    out: dict = {}
    for fid, blk in EVENT_ID_TO_MES.items():
        out.setdefault(int(blk), []).append(int(fid))
    return {b: tuple(sorted(f)) for b, f in out.items()}


_VANILLA: dict = _vanilla_index()


def vanilla_fields_on(text_block: int) -> tuple:
    """The REAL FF9 field ids whose dialogue lives in ``text_block`` (``()`` when the block is not a shipping
    one). A custom field deploying on a non-empty block overwrites that location's text -- see the VANILLA
    squat note in the module docstring."""
    return _VANILLA.get(int(text_block), ())


def describe_vanilla(text_block: int) -> str:
    """A compact human label for the real fields a block owns -- ``"10 real fields 3050-3059"``. Deliberately
    id-based, NOT name-based: ``reference/field-manifest.tsv`` lives at the repo root and is not shipped as
    package data, so an installed user has no name lookup, whereas the id table always ships."""
    ids = vanilla_fields_on(text_block)
    if not ids:
        return ""
    if len(ids) == 1:
        return "1 real field {}".format(ids[0])
    # only render a dash SPAN when the ids are actually contiguous -- a few real blocks own gapped id sets,
    # and "600-620" for 21 fields that skip several would overstate the reach of the message.
    contiguous = len(ids) == ids[-1] - ids[0] + 1
    where = f"{ids[0]}-{ids[-1]}" if contiguous else f"incl. {ids[0]}, {ids[-1]}"
    return f"{len(ids)} real fields {where}"


def suggest_text_blocks(taken=(), n: int = 3, base: int = SCRATCH_TEXT_BLOCK_BASE) -> list:
    """``n`` CUSTOM mesIDs that belong to nobody: not owned by a real FF9 field and not defined by any folder
    in ``taken``. These REQUIRE ``register_text_block = true`` (a DictionaryPatch ``MessageFile`` line) --
    without it ``DataPatchers`` fails the ``MesDB.ContainsKey`` gate and SKIPS the whole FieldScene (black
    screen), which is a strictly worse failure than the wrong text this guard is about.

    This deliberately does NOT propose "a real block no higher folder defines" (the guard's original advice).
    That advice is what put custom text on Ice Cavern and Lindblum Castle: every real block is owned by a real
    location, so re-pointing at one only MOVES the corruption."""
    busy = {int(b) for b in taken}
    out: list = []
    cur = int(base)
    while len(out) < max(0, int(n)):
        if cur not in busy and cur not in _VANILLA:
            out.append(cur)
        cur += 1
    return out


@dataclass
class ShadowReport:
    """The result of :func:`check_text_block_shadow`, covering BOTH collisions in the module docstring.

    ``shadowed_by`` is the first higher-priority folder that also defines ``text_block`` (``None`` => no
    cross-folder shadow). ``vanilla_fields`` is the real FF9 fields the block belongs to, non-empty only when
    this deploy would OVERWRITE their shipping dialogue -- it is left empty for a ``verbatim`` fork, which
    re-ships the donor's own text and is therefore harmless. ``suggestions`` are free CUSTOM mesIDs (they
    require ``register_text_block = true``). ``order`` is the parsed ``FolderNames`` stack."""
    target_folder: str
    text_block: int
    lang: str
    shadowed_by: str | None
    suggestions: list
    order: list
    vanilla_fields: tuple = ()

    @property
    def squats_vanilla(self) -> bool:
        """Would this deploy overwrite a REAL FF9 location's dialogue? (The base game is always in the
        cumulative merge, so this needs no stacked folder at all.)"""
        return bool(self.vanilla_fields)

    @property
    def ok(self) -> bool:
        """Clear on BOTH axes. NOTE this is deliberately stricter than the pre-fix guard, which considered a
        block "clear" while it was silently overwriting Black Mage Village."""
        return self.shadowed_by is None and not self.vanilla_fields


def parse_folder_names(memoria_ini_text: str) -> list:
    """The ordered mod-folder priority list from a ``Memoria.ini``'s ``FolderNames = "A", "B", ...`` line
    (highest priority first). ``[]`` if the key is absent. Skips comment lines (``;``). NOTE: the stock ini
    comment calling ``Priorities`` "only a hint" is WRONG -- the Memoria Launcher treats Priorities as the
    MASTER order and rewrites FolderNames from it at every Play click, so any WRITER must set both keys in
    the same order (:func:`ff9mapkit.coop.mod_order_updates`); reading FolderNames alone stays correct."""
    for line in memoria_ini_text.splitlines():
        s = line.strip()
        if s.startswith(";") or "=" not in s:
            continue
        key, _, value = s.partition("=")
        if key.strip().lower() == "foldernames":
            return re.findall(r'"([^"]+)"', value)
    return []


def blocks_at(root, lang: str = "us") -> set:
    """The field text-block ids (``.mes`` file stems) a mod/dist ROOT defines for ``lang`` -- mirrors
    :func:`eb_names_at` / :func:`scene_names_at`, so a built campaign dist can be checked before install."""
    d = ModLayout(Path(root)).text_field_dir(lang)
    out = set()
    if d.is_dir():
        for p in d.glob("*.mes"):
            try:
                out.add(int(p.stem))
            except ValueError:
                pass
    return out


def _blocks_in(game_dir: Path, folder: str, lang: str) -> set:
    """The field text-block ids (``.mes`` file stems) a mod folder defines for ``lang``."""
    return blocks_at(Path(game_dir) / folder, lang)


def donor_block_for(project_raw) -> int | None:
    """The DONOR's real text block for a fork's ``field.toml`` raw dict, or ``None`` when the project is not a
    fork (or its donor is unknown/not a real field). Mirrors ``build._verbatim_donor_id``'s three recorded
    donor forms -- ``[verbatim_eb] donor`` (verbatim), ``[field] source_field`` (native/editable),
    ``[field] borrow_field`` (BG-borrow) -- deliberately NOT just the verbatim one: a ``--native`` fork also
    carries its donor's text and is equally exempt from the vanilla axis.

    Kept here (rather than inlined at a call site) so the predicate is unit-testable: an earlier version of
    this guard tested ``"verbatim_eb" in raw``, which both false-positived every native fork AND blanket-
    suppressed the vanilla axis for verbatim forks sitting on a block that was NOT their donor's."""
    fld = (project_raw.get("field") or {}) if hasattr(project_raw, "get") else {}
    for blk, key in (("verbatim_eb", "donor"), ("field", "source_field"), ("field", "borrow_field")):
        v = (project_raw.get(blk) or {}).get(key) if blk != "field" else fld.get(key)
        if isinstance(v, bool):
            continue
        if isinstance(v, str) and v.isdigit():
            v = int(v)
        if isinstance(v, int):
            blkid = EVENT_ID_TO_MES.get(v)
            return int(blkid) if blkid is not None else None
    return None


def fork_donor_blocks_at(root) -> set:
    """The text blocks a built dist's FORKS legitimately own -- the donor block of every ``<forkId>
    <donorRealId>`` row in its ``ForkDonorPatch.txt``. Feeds ``check_text_block_shadows(verbatim_blocks=)``.

    The rule this encodes: squatting is putting text on a real location's block you have NO relationship to.
    A fork of donor D writing D's block is re-shipping D's OWN text (byte-identical when ``--verbatim``,
    edited-in-place when native) -- it is not overwriting a third party. ``{}`` when the file is absent, which
    is the correct conservative default: a dist with no forks has no exemptions to claim."""
    out: set = set()
    p = Path(root) / "ForkDonorPatch.txt"
    if not p.is_file():
        return out
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.split("#", 1)[0].split()
        if len(parts) < 2:
            continue
        try:
            donor = int(parts[1])
        except ValueError:
            continue
        blk = EVENT_ID_TO_MES.get(donor)
        if blk is not None:
            out.add(int(blk))
    return out


def check_text_block_shadow(game_dir, target_folder: str, text_block: int, lang: str = "us",
                            folder_names: list | None = None, verbatim_blocks=()) -> ShadowReport:
    """Is a field's ``text_block`` deployed into ``target_folder`` in collision -- either SHADOWED by a
    higher-priority mod folder, or squatting a REAL FF9 location's block? Reads ``Memoria.ini``
    ``FolderNames`` (unless ``folder_names`` is passed) + each folder's ``field/*.mes``.

    ``verbatim_blocks`` are blocks a FORK legitimately owns -- pass ``{donor_block_for(project.raw)}``. A fork
    re-ships its donor's own text on the donor's own block, so the vanilla axis is suppressed for THAT block
    (the overwrite is a no-op) while the cross-folder axis still applies -- two forks of the SAME donor in two
    stacked folders genuinely do fight. This is a set of blocks and NOT a boolean on purpose: a boolean
    suppresses the vanilla axis for whatever block the fork happens to carry, so a fork left on the kit
    default (1073 = Black Mage Village) would be waved through while really overwriting it.

    Degrades gracefully when the stack can't be read; if the target isn't listed in ``FolderNames`` nothing is
    treated as higher-priority (no false alarm). The VANILLA axis needs no stack at all, so it still reports."""
    game_dir = Path(game_dir)
    order = folder_names
    if order is None:
        ini = game_dir / "Memoria.ini"
        order = parse_folder_names(ini.read_text(encoding="utf-8", errors="ignore")) if ini.is_file() else []
    higher = order[:order.index(target_folder)] if target_folder in order else []
    blocks = {f: _blocks_in(game_dir, f, lang) for f in order}
    shadowed_by = next((f for f in higher if text_block in blocks.get(f, set())), None)
    # Alternatives are free CUSTOM ids, NOT "a real block no higher folder defines" -- see suggest_text_blocks.
    taken = set().union(*blocks.values()) if blocks else set()
    suggestions = suggest_text_blocks(taken | {text_block}, 3)
    vanilla = () if int(text_block) in {int(b) for b in verbatim_blocks} else vanilla_fields_on(text_block)
    return ShadowReport(target_folder, text_block, lang, shadowed_by, suggestions, order, vanilla)


def _fix_hint(report: ShadowReport) -> str:
    """The shared remediation sentence: a free custom block + the registration that makes it legal."""
    if not report.suggestions:
        return ("Fix: set text_block to a custom mesID no folder defines, with register_text_block = true.")
    alts = ", ".join(str(s) for s in report.suggestions)
    return (f"Fix: text_block = {report.suggestions[0]} with register_text_block = true "
            f"(free custom ids: {alts}) -- the build then emits a DictionaryPatch `MessageFile` line so the "
            f"FieldScene MesDB gate passes. Do NOT just pick another REAL block: every one is owned by a real "
            f"location, so that only moves the corruption.")


def shadow_warning(report: ShadowReport, mod_folder: str | None = None) -> str | None:
    """A human-readable warning for a colliding text block, or ``None`` when clear on both axes.
    ``mod_folder`` overrides the report's ``target_folder`` label (they match in normal use)."""
    if report.ok:
        return None
    target = mod_folder or report.target_folder
    lang = f" [lang {report.lang}]" if report.lang != "us" else ""
    lines = []
    if report.shadowed_by is not None:
        lines.append(f"TEXT SHADOWED{lang}: block {report.text_block} is also defined by "
                     f"'{report.shadowed_by}', which is HIGHER priority than '{target}' in Memoria.ini "
                     f"FolderNames -- the engine will show '{report.shadowed_by}'s text, not yours.")
    if report.squats_vanilla:
        lines.append(f"TEXT OVERWRITES VANILLA{lang}: block {report.text_block} is a REAL FF9 text block "
                     f"({describe_vanilla(report.text_block)}) -- the base game is part of the engine's "
                     f"cumulative text merge, so this deploy replaces that location's own dialogue for the "
                     f"whole playthrough (partially: the leading txids only, which is why it looks fine).")
    lines.append(_fix_hint(report))
    return " ".join(lines)


def check_text_block_shadows(game_dir, target_folder: str, text_blocks, lang: str | None = "us",
                             folder_names: list | None = None, verbatim_blocks=()) -> list:
    """Batch :func:`check_text_block_shadow` -- which of ``text_blocks`` deployed into ``target_folder`` collide,
    either SHADOWED by a higher-priority folder or squatting a REAL location's block? Returns only the COLLIDING
    :class:`ShadowReport`\\ s (``[]`` => all clear), reading the ``FolderNames`` stack ONCE (vs once per block).
    Used by ``deploy_campaign`` to give every member's text block the guard a single-field deploy already runs.

    ``lang=None`` checks EVERY language in :data:`LANGS` and reports per-language, which is what a caller
    gathering blocks across all languages must do -- comparing an all-language block set against only the ``us``
    subtree mismatches in both directions. A novel field's text is identical across languages so its findings
    are symmetric (deduped here); a VERBATIM fork's per-language bodies come from genuinely lang-asymmetric
    donor data, so it can legitimately collide in one language only.

    ``verbatim_blocks`` are blocks carried by a verbatim/native fork -- exempt from the vanilla check (they
    re-ship the donor's own text), still subject to the cross-folder check.

    Degrades to ``[]`` when the stack can't be read; the vanilla axis needs no stack and still reports."""
    game_dir = Path(game_dir)
    order = folder_names
    if order is None:
        ini = game_dir / "Memoria.ini"
        order = parse_folder_names(ini.read_text(encoding="utf-8", errors="ignore")) if ini.is_file() else []
    higher = order[:order.index(target_folder)] if target_folder in order else []
    langs = list(LANGS) if lang is None else [lang]
    vb = {int(b) for b in verbatim_blocks}
    wanted = sorted({int(b) for b in text_blocks})
    per_lang = {L: {f: _blocks_in(game_dir, f, L) for f in order} for L in langs}
    taken = set().union(*(bs for bf in per_lang.values() for bs in bf.values())) if order else set()
    out: list = []
    # Accumulates ids already handed to an EARLIER finding in this same run, so two colliding blocks in one
    # deploy get DIFFERENT alternatives. Without it every row suggested the same id and a user applying the
    # advice to both offenders would create a fresh collision -- caused by this tool's own recommendation.
    handed: set = set()
    for tb in wanted:
        # The SHADOW axis is per-language: a fork's per-language bodies are genuinely asymmetric, so report
        # the first language that collides and any FURTHER language whose shadowing folder DIFFERS. (A novel
        # field's text is identical across langs, so its finding is symmetric and collapses to one row.)
        seen_shadow: set = set()
        for L in langs:
            by_folder = per_lang[L]
            shadowed_by = next((f for f in higher if tb in by_folder.get(f, set())), None)
            if shadowed_by is None or shadowed_by in seen_shadow:
                continue
            seen_shadow.add(shadowed_by)
            sug = suggest_text_blocks(taken | handed | {tb}, 3)
            handed.update(sug[:1])                        # reserve only the id the message actually names
            out.append(ShadowReport(target_folder, tb, L, shadowed_by, sug, order, ()))
        # The VANILLA axis is language-INDEPENDENT -- it is a property of the block ID, not of any file on
        # disk -- so it is evaluated ONCE per block. Folding it into the per-language loop above emits one
        # spurious duplicate per language that happens not to collide.
        vanilla = () if tb in vb else vanilla_fields_on(tb)
        if vanilla:
            sug = suggest_text_blocks(taken | handed | {tb}, 3)
            handed.update(sug[:1])
            out.append(ShadowReport(target_folder, tb, langs[0], None, sug, order, vanilla))
    return out


def text_shadow_warning(reports: list, target_folder: str) -> str | None:
    """A human-readable multi-line warning for colliding text blocks (the batch analogue of
    :func:`shadow_warning`), or ``None`` when clear."""
    if not reports:
        return None
    shadowed = [r for r in reports if r.shadowed_by is not None]
    squat = [r for r in reports if r.squats_vanilla]
    # count distinct BLOCKS, not rows: one block failing both axes emits a row per axis.
    n = len({r.text_block for r in reports})
    lines = [f"TEXT BLOCK COLLISION: {n} text block(s) this deploy puts in '{target_folder}' "
             f"collide -- dialogue (incl. [[logic_edit]] text rewrites) will be wrong:"]
    # each row names its OWN alternative -- a single blanket id would have every offender move onto the
    # same block, which is a fresh collision this tool would have caused.
    for r in shadowed:
        lang = f", lang {r.lang}" if r.lang != "us" else ""
        alt = f" -> use {r.suggestions[0]}" if r.suggestions else ""
        lines.append(f"  - block {r.text_block} SHADOWED by higher-priority '{r.shadowed_by}'{lang} "
                     f"-- the engine serves that folder's .mes, so yours shows the OLD text{alt}")
    for r in squat:
        alt = f" -> use {r.suggestions[0]}" if r.suggestions else ""
        lines.append(f"  - block {r.text_block} OVERWRITES VANILLA ({describe_vanilla(r.text_block)}) "
                     f"-- the base game is in the engine's cumulative merge, so this replaces that "
                     f"location's own dialogue for the whole playthrough{alt}")
    lines.append("Fix: give each field above its OWN listed block with register_text_block = true -- the "
                 "build then emits a DictionaryPatch `MessageFile` line so the FieldScene MesDB gate passes. "
                 "Do NOT re-point at another REAL block: every one is owned by a real location, so that only "
                 "moves the corruption.")
    if shadowed:
        lines.append("(For the shadowed rows you may instead deploy this folder HIGHER in Memoria.ini "
                     "FolderNames, or remove the higher folder's copy of the block.)")
    return "\n".join(lines)


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
