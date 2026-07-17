"""Pure DictionaryPatch.txt revert/re-apply bookkeeping, shared by ``tools/deploy_field.py`` and the revert
scripts it generates.

A field deploy (and its revert) must touch ONLY the DictionaryPatch registrations it itself owns -- this
field's ``FieldScene``/``LocationName`` line, the ``3DModel <id>`` GEO ids it mints, and the
``3DModelAnimation <key>`` clips it registers (``custom_battle_anims``). Everything else in the file is
FOREIGN and must survive the revert-then-re-apply cycle: a co-deployed field's lines, another tool's lines,
and -- the footgun this module fixes -- a ``3DModelAnimation <key> <name>`` that ``ff9mapkit model-anim-new``
wrote DIRECTLY into DictionaryPatch BETWEEN two deploys of the same slot.

The bug (found 2026-07-08): the old rule dropped stale ``3DModelAnimation`` lines by the GEO MIDDLE-BLOCK
their ANH name shares with a minted model (``NPC_F1_M300`` in ``ANH_NPC_F1_M300_IDLE``). That block is shared
by EVERY clip of that model, so re-deploying a field that mints ``GEO_NPC_F1_M300`` silently wiped a foreign
clip line (e.g. key 60001) that ``model-anim-new`` had added for the same model -- even though the deploy
never wrote that line and it wasn't in the deploy's pre-deploy snapshot to be restored. The fix: match by the
EXACT id/key the deploy owns (carried in ``mint_lines``), never by shared block. Mint anim keys are
deterministic per (model, clip) -- ``deploy_new_anim`` reuses the key registered to an ANH name, and
``battle_animset_remap`` computes ``1_000_000 + (mint_id-6000)*100 + i`` -- so exact-key matching drops
exactly this deploy's own registrations across re-deploys and leaves foreign keys intact.
"""
from __future__ import annotations


def mint_model_ids(mint_lines) -> set:
    """The GEO ids this deploy mints -- the ``<id>`` of each ``3DModel <id> <NAME>`` line. Revert drops a
    live ``3DModel`` line only when its id is in this set (an exact-id match, never a name/block match)."""
    ids = set()
    for ln in mint_lines:
        p = ln.split()
        if p[:1] == ["3DModel"] and len(p) >= 2:
            ids.add(p[1])
    return ids


def mint_anim_keys(mint_lines) -> set:
    """The AnimationDB keys this deploy registers -- the ``<key>`` of each ``3DModelAnimation <key> <NAME>``
    line. Revert/re-apply drops a live ``3DModelAnimation`` line only when its key is in this set, so a
    FOREIGN clip sharing the mint's GEO block but with a key this deploy does not own is PRESERVED."""
    keys = set()
    for ln in mint_lines:
        p = ln.split()
        if p[:1] == ["3DModelAnimation"] and len(p) >= 2:
            keys.add(p[1])
    return keys


def owns_registration(ln, *, fid, model_ids, anim_keys) -> bool:
    """True if ``ln`` is a DictionaryPatch line THIS deploy owns and should replace on re-apply / drop on
    revert: this field's own ``<directive> <fid> ...`` (``FieldScene``/``LocationName``), a ``3DModel <id>``
    whose id it mints (``model_ids``), or a ``3DModelAnimation <key>`` whose key it registers (``anim_keys``).

    Matching is by EXACT field id / GEO id / anim key -- NEVER by a shared GEO middle-block -- so a foreign
    ``3DModel``/``3DModelAnimation`` line (one this deploy did not write) always returns False and survives.
    Blank lines return False (they are neither owned nor meaningful)."""
    p = ln.split()
    if not ln.strip():
        return False
    if p[:1] in (["FieldScene"], ["LocationName"]) and p[1:2] == [str(fid)]:
        return True                # this field's own line (id in column 2); directive-scoped so a coincidentally
        #                            same-numbered 3DModel/BattleScene line (custom ids overlap 4000-9899) is never claimed
    if p[:1] == ["3DModel"] and p[1:2] and p[1] in model_ids:
        return True
    if p[:1] == ["3DModelAnimation"] and len(p) >= 2 and p[1] in anim_keys:
        return True
    return False


def revert_dictionary_patch(current_lines, backup_lines, *, fid, model_ids, anim_keys) -> tuple:
    """Compute a field deploy's DictionaryPatch revert. From ``current_lines`` (the live file NOW, which may
    carry lines other tools/deploys added since) keep everything EXCEPT the registrations this deploy owns
    (its ``FieldScene``/``LocationName``, its minted ``3DModel`` ids, its ``3DModelAnimation`` keys). Then, so
    reverting one field can't strip a registration another field had ALREADY made, re-add from ``backup_lines``
    (the pre-deploy snapshot) any OWNED line that pre-existed this deploy and isn't already present -- lines
    this deploy added fresh aren't in the backup, so they stay gone.

    Returns ``(kept_lines, foreign_dropped)`` where ``foreign_dropped`` lists any FOREIGN model/anim line that
    ended up dropped anyway (should always be empty -- it's a belt-and-suspenders warning source). Matching is
    exact-id/exact-key throughout, so a foreign ``3DModelAnimation`` sharing a minted model's GEO block (e.g. a
    ``model-anim-new`` clip added between deploys) is preserved, not wiped."""
    def _owned(ln):
        return owns_registration(ln, fid=fid, model_ids=model_ids, anim_keys=anim_keys)
    kept = [ln for ln in current_lines if ln.strip() and not _owned(ln)]
    seen = set(kept)
    for ln in backup_lines:
        if ln.strip() and _owned(ln) and ln not in seen:
            kept.append(ln)
            seen.add(ln)
    return kept, foreign_registrations_dropped(current_lines, kept, owned=_owned)


def foreign_registrations_dropped(before_lines, after_lines, owned=None) -> list:
    """The FOREIGN ``3DModel``/``3DModelAnimation`` registrations present in ``before_lines`` but absent from
    ``after_lines`` -- a safety net for a revert/re-apply that is about to silently lose a model/anim line it
    does not own. Returns the dropped lines (verbatim, de-duplicated, in first-seen order) so the caller can
    WARN loudly. Only model/anim registrations are reported (a dropped FieldScene is the deploy's own
    business). ``owned`` is an optional ``line -> bool`` predicate: a dropped line the deploy DOES own (e.g.
    its own fresh mint the revert correctly removes) is excluded, so only genuinely-foreign losses warn."""
    def _regs(lines):
        out = []
        for ln in lines:
            p = ln.split()
            if p[:1] in (["3DModel"], ["3DModelAnimation"]) and len(p) >= 2:
                out.append(ln.strip())
        return out
    after = set(_regs(after_lines))
    dropped, seen = [], set()
    for ln in _regs(before_lines):
        if ln in after or ln in seen or (owned is not None and owned(ln)):
            continue
        dropped.append(ln)
        seen.add(ln)
    return dropped
