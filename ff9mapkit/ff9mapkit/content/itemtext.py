r"""``[[item_text]]`` -- author an item's menu NAME + help/battle DESCRIPTION (the last items_equipment
piece). NOT a CSV: the text lives in the engine's localized DisplayBatch, set at startup from the text
bundles. The drop-in override channel is a **``TextPatch.txt``** at the mod-folder root -- the same
per-folder patch-file mechanism the kit already emits for ``DictionaryPatch.txt`` / ``BattlePatch.txt``.

THE ENGINE FORMAT (``Memoria.TextPatcher.PatchTexts`` + ``DataPatchers.Initialize``, both fully read):
``TextPatch.txt`` is a line list of *patcher blocks* in four scopes by a leader line -- ``>DIALOG`` /
``>BATTLE`` / ``>INTERFACE`` / **``>DATABASE``** (item name/desc = ``>DATABASE``). Within a block:
  * ``[code=Condition] <NCalc> [/code]`` BEFORE any modifier -> the patcher-level Condition (which entry).
  * ``FindAndReplace`` + ``Find: <regex>`` + ``Replace: <text>`` -> a find/replace modifier.
  * ``// `` lines are skipped (comments) -> our ``//`` sentinel markers are inert (same as BattlePatch).
  * ★ ``ApplyPatch`` applies only the FIRST matching modifier then ``return true`` -> emit ONE ``>DATABASE``
    block per (item, field-kind) -- never stack modifiers.

THE CONDITION (``TextPatcher.PatchDatabaseString(str, databaseName, id, isName, isHelp)`` -> NCalc params):
``Database`` (string), ``EntryId`` (int), ``IsNameEntry`` (bool), ``IsHelpEntry`` (bool). For ITEMS the
engine setters are (``FF9TextTool.cs:776-789``, VERIFIED):
  * ``SetItemName(id,v)``     -> ``(v, "RegularItem", id, true,  false)`` -> ``IsNameEntry``.
  * ``SetItemHelpDesc(id,v)`` -> ``(v, "RegularItem", id, false, true )`` -> ``IsHelpEntry``.
  * ``SetItemBattleDesc(id,v)``-> ``(v, "RegularItem", id, false, true )`` -> **also ``IsHelpEntry``**.
★★ CONSTRAINT: the help-desc and the battle-desc are flagged IDENTICALLY -> via TextPatch they CANNOT be
targeted separately; one ``IsHelpEntry`` condition replaces BOTH. So v1 exposes ``display_name`` (the menu
name) + ``description`` (the help + battle text, together).

VALUE ENCODING (``Replace:`` is a .NET ``Regex.Replace`` replacement string, ``TextPatcher.cs:84,337``):
  * Full-replace = ``Find: \A[\s\S]*\z`` (absolute start/end anchors; matches the whole base string ONCE,
    Multiline-immune -- ``^[\s\S]*$`` would multi-match under ``RegexOptions.Multiline``).
  * ★ ``$`` -> ``$$`` in the Replace text (``Regex.Replace`` reads ``$N``/``$&`` as group refs).
  * The engine does ``Replace.Replace("\n", <newline>)`` -> a real newline in the author's text becomes the
    two chars ``\n`` on the (single) ``Replace:`` line, which the engine turns back into a newline.

PROVENANCE: the kit writes ONLY the author's strings + the resolved item id -- it reads NOTHING from the
game bundles (unlike the CSV deltas, which carry a base row). RELAUNCH to apply (``DataPatchers.Initialize``
runs once at AssetManager bring-up, before the item text is imported -- F6 Reload won't re-read it).

    [[item_text]]
    name = "Potion"                       # the item to rename/redescribe (name or id; RegularItem space)
    display_name = "Mega Potion"          # optional: the menu name (IsNameEntry)
    description  = "Restores 15 HP."      # optional: the help + battle description (IsHelpEntry, both)
    # at least one of display_name / description is required.
"""
from __future__ import annotations

from .. import items as _items

DATABASE_NAME = "RegularItem"               # typeof(RegularItem).Name -- the Database for a normal item
FULL_REPLACE_FIND = r"\A[\s\S]*\z"          # .NET absolute anchors: replace the WHOLE base string, once
NO_ITEM = 255                               # RegularItem.NoItem -- the empty-slot sentinel, never a real item


class ItemTextError(ValueError):
    pass


def _escape_replace(text) -> str:
    """Sanitise one author string into a single ``Replace:`` value: ``$`` -> ``$$`` (else ``Regex.Replace``
    reads it as a group ref), real newlines -> the literal two chars ``\\n`` (the engine reads the patch
    line-by-line then converts ``\\n`` back to a newline -> a multi-line description survives on one line).

    Rejects a LITERAL backslash-n in the author text: this channel reserves ``\\n`` for a line break (the
    engine unconditionally rewrites ``\\n`` -> newline, with no escape and no ``\\\\`` un-doubling), so a
    literal ``\\n`` cannot be represented and would silently become an unintended line break in-game. Better
    to fail the build than to corrupt the text the human can't see (the kit's offline-fail rule)."""
    if not isinstance(text, str):
        raise ItemTextError(f"text must be a string, got {type(text).__name__}")
    if "\\n" in text:
        raise ItemTextError(
            "text contains a literal backslash-n (\\n) -- this channel reserves \\n for a line break (the "
            "engine rewrites \\n to a newline) and cannot show it literally. Use a real line break for a new "
            "line, and remove the literal \\n.")
    out = text.replace("$", "$$")
    return out.replace("\r\n", "\\n").replace("\r", "\\n").replace("\n", "\\n")


def _condition(item_id: int, flag: str) -> str:
    """The NCalc patcher condition for one item entry. ``flag`` is ``IsNameEntry`` (the menu name) or
    ``IsHelpEntry`` (the help+battle description)."""
    return f"Database == '{DATABASE_NAME}' && EntryId == {item_id} && {flag} == true"


def _block(item_id: int, flag: str, text) -> list[str]:
    """One ``>DATABASE`` patcher: a condition (which entry) + a full-replace of its text. The ``[code=Condition]``
    precedes ``FindAndReplace`` so it binds at the PATCHER level (gates the whole block)."""
    return [
        ">DATABASE",
        f"[code=Condition] {_condition(item_id, flag)} [/code]",
        "FindAndReplace",
        f"Find: {FULL_REPLACE_FIND}",
        f"Replace: {_escape_replace(text)}",
    ]


def render_block_lines(text_blocks) -> list[str]:
    """``[[item_text]]`` blocks -> the ``>DATABASE`` patch lines (no markers). Pure + offline: the item name
    resolves via :func:`items.resolve` (RegularItem space); the strings are the author's. Raises
    :class:`ItemTextError` so a bad block fails the lint/build, never the running game.

    Per item: a ``display_name`` -> an ``IsNameEntry`` block; a ``description`` -> an ``IsHelpEntry`` block
    (which the engine applies to BOTH the menu-help and the battle description -- they share the flag)."""
    lines: list[str] = []
    for n, b in enumerate(text_blocks or []):
        if not isinstance(b, dict):
            raise ItemTextError(f"[[item_text]] #{n} must be a table (e.g. {{ name = \"Potion\", "
                                f"display_name = \"Mega Potion\" }})")
        name = b.get("name")
        if name is None:
            raise ItemTextError(f"[[item_text]] #{n} needs a `name` (the item to rename/redescribe)")
        try:
            item_id = _items.resolve(name)
        except (ValueError, TypeError) as ex:
            raise ItemTextError(f"[[item_text]] {name!r}: {ex}") from ex
        if item_id == NO_ITEM:                            # mirror the [[shop]]/[[synthesis]] NoItem guards
            raise ItemTextError(f"[[item_text]] {name!r} resolves to NoItem ({NO_ITEM}), the empty-slot "
                                f"sentinel -- it is not a real item, pick one to retext")
        disp, desc = b.get("display_name"), b.get("description")
        if disp is None and desc is None:
            raise ItemTextError(f"[[item_text]] {name!r} sets neither display_name nor description "
                                f"(give at least one)")
        try:
            if disp is not None:
                lines += _block(item_id, "IsNameEntry", disp)
            if desc is not None:
                lines += _block(item_id, "IsHelpEntry", desc)
        except ItemTextError as ex:
            raise ItemTextError(f"[[item_text]] {name!r} {ex}") from ex
    return lines


def validate_blocks(text_blocks) -> list[str]:
    """Offline structural validation (for ``lint`` -- no install needed): re-run the emission and surface the
    first :class:`ItemTextError` as a message (empty list => OK)."""
    try:
        render_block_lines(text_blocks)
    except ItemTextError as ex:
        return [str(ex)]
    return []


# ---- non-clobbering merge into a live TextPatch.txt (deploy) -----------------------------------------
def _markers(field_id):
    return (f"// >>> ff9mapkit field {field_id} TextPatch (auto -- edit the field.toml, not here)",
            f"// <<< ff9mapkit field {field_id}")


def merge_text_patch(live_text: str, block_lines, field_id) -> str:
    """Splice ``block_lines`` into ``live_text`` between this field's ``//`` sentinel markers, REPLACING any
    prior block for the same id and PRESERVING every other line (another field's item text, a stacked
    worktree's lines). The engine skips ``//`` lines, so the markers are inert. Empty ``block_lines`` just
    strips our prior block (a redeploy after the toml's [[item_text]] was removed). Idempotent. Mirrors
    :func:`ff9mapkit.battle.battlepatch.merge_battle_patch`."""
    begin, end = _markers(field_id)
    kept, skip = [], False
    for ln in live_text.splitlines():
        if ln.strip() == begin:
            skip = True
            continue
        if ln.strip() == end:
            skip = False
            continue
        if not skip:
            kept.append(ln)
    while kept and not kept[-1].strip():                   # trim trailing blank lines before re-appending
        kept.pop()
    block = [ln for ln in (block_lines or []) if ln.strip()]
    out = list(kept)
    if block:
        out += [begin, *block, end]
    return ("\n".join(out) + "\n") if out else ""
