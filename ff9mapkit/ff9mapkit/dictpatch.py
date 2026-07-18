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


def owns_registration(ln, *, fid, model_ids, anim_keys, text_blocks=()) -> bool:
    """True if ``ln`` is a DictionaryPatch line THIS deploy owns and should replace on re-apply / drop on
    revert: this field's own ``<directive> <fid> ...`` (``FieldScene``/``LocationName``), a ``3DModel <id>``
    whose id it mints (``model_ids``), a ``3DModelAnimation <key>`` whose key it registers (``anim_keys``),
    or a ``MessageFile <block>`` whose mesID it registers (``text_blocks``).

    ``MessageFile`` is keyed by the TEXT BLOCK, not the field id, and the two are NOT interchangeable: a
    DERIVED block equals the field id, but an EXPLICIT one need not (field 4005 sits on block 30110). So the
    caller passes the blocks it actually registers, exactly as it does for minted GEO ids -- deriving them
    from ``fid`` here would miss the explicit case AND claim a foreign line whose block happens to equal this
    field's id.

    Matching is by EXACT field id / GEO id / anim key / block -- NEVER by a shared GEO middle-block -- so a
    foreign ``3DModel``/``3DModelAnimation``/``MessageFile`` line (one this deploy did not write) always
    returns False and survives. Blank lines return False (they are neither owned nor meaningful)."""
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
    if p[:1] == ["MessageFile"] and p[1:2] and p[1] in {str(b) for b in text_blocks}:
        return True
    return False


def owned_predicate(*, fid, model_ids, anim_keys, status_icon_ids=(), charname_keys=(), text_blocks=()):
    """The ONE ownership rule a field deploy uses -- returns a ``line -> bool`` predicate covering every
    registration ``tools/deploy_field.py`` strips from the live DictionaryPatch and re-appends fresh:
    :func:`owns_registration`'s field/mint half, plus the two ``[[playable]]`` lines a redeploy re-sets
    (``BuffIcon``/``DebuffIcon <statusId>`` and ``CharacterDefaultName <charId> <LANG>``).

    It has to be ONE function because the deploy hands the very same predicate to
    :func:`foreign_registrations_dropped` as ``owned=``: the filter decides what gets removed, the predicate
    decides what removals are worth a warning, and if they disagree by a hair the guard either cries wolf on
    every run or goes silent on a real loss.

    EVERY CLAUSE IS DIRECTIVE-SCOPED, and that is the point. The script's earlier hand-rolled form claimed any
    line whose column 2 equalled the field id. Mint GEO ids start at 6000 (``models/mint.MINT_BAND_START``)
    and the custom field band is 4000-9899, so the two OVERLAP: deploying field 6000 into a shared mod folder
    claimed another session's ``3DModel 6000 GEO_...``, dropped it from the rewrite, and -- once the predicate
    became the guard's ``owned=`` -- suppressed the warning about losing it too. A foreign registration wiped
    in silence is the exact loss class this module exists to report."""
    icons, names = set(status_icon_ids), set(charname_keys)

    def _owned(ln):
        if owns_registration(ln, fid=fid, model_ids=model_ids, anim_keys=anim_keys,
                             text_blocks=text_blocks):
            return True
        p = ln.split()
        if len(p) >= 2 and p[0] in ("BuffIcon", "DebuffIcon") and p[1] in icons:
            return True
        return len(p) >= 3 and p[0] == "CharacterDefaultName" and (p[1], p[2]) in names
    return _owned


def revert_dictionary_patch(current_lines, backup_lines, *, fid, model_ids, anim_keys, text_blocks=()) -> tuple:
    """Compute a field deploy's DictionaryPatch revert. From ``current_lines`` (the live file NOW, which may
    carry lines other tools/deploys added since) keep everything EXCEPT the registrations this deploy owns
    (its ``FieldScene``/``LocationName``, its minted ``3DModel`` ids, its ``3DModelAnimation`` keys). Then, so
    reverting one field can't strip a registration another field had ALREADY made, re-add from ``backup_lines``
    (the pre-deploy snapshot) any OWNED line that pre-existed this deploy and isn't already present -- lines
    this deploy added fresh aren't in the backup, so they stay gone.

    Returns ``(kept_lines, foreign_dropped)`` where ``foreign_dropped`` lists any FOREIGN model/anim/field line that
    ended up dropped anyway (should always be empty -- it's a belt-and-suspenders warning source). Matching is
    exact-id/exact-key throughout, so a foreign ``3DModelAnimation`` sharing a minted model's GEO block (e.g. a
    ``model-anim-new`` clip added between deploys) is preserved, not wiped."""
    def _owned(ln):
        return owns_registration(ln, fid=fid, model_ids=model_ids, anim_keys=anim_keys,
                                 text_blocks=text_blocks)
    kept = [ln for ln in current_lines if ln.strip() and not _owned(ln)]
    seen = set(kept)
    for ln in backup_lines:
        if ln.strip() and _owned(ln) and ln not in seen:
            kept.append(ln)
            seen.add(ln)
    return kept, foreign_registrations_dropped(current_lines, kept, owned=_owned)


ID_KEYED_DIRECTIVES = ("FieldScene", "LocationName")
"""DictionaryPatch directives keyed by the FIELD ID in column 2 (``<directive> <fid> ...``)."""

TEXT_BLOCK_DIRECTIVES = ("MessageFile",)
"""DictionaryPatch directives keyed by a TEXT BLOCK (mesID) in column 2 -- NOT by the field id, which is
why a deploy passes the blocks it registers rather than letting them be derived from ``fid``."""

MINT_DIRECTIVES = ("3DModel", "3DModelAnimation")
"""DictionaryPatch directives keyed by a minted GEO id / AnimationDB key in column 2."""


def _registration_identity(parts):
    """What "did this registration survive?" is judged on, per directive kind -- or None for a line that is
    not a reported registration at all.

    ``FieldScene``/``LocationName`` judge on ``(directive, id)``, NOT the whole line: what the engine needs is
    that the id is still registered at all, and a re-deploy legitimately rewrites its own field's line with a
    new scene name or text-block id. Whole-line matching there would fire on every edit-deploy cycle, and a
    guard that cries wolf every run is a guard nobody reads.

    ``3DModel``/``3DModelAnimation`` keep WHOLE-LINE identity: a key re-pointed at a different GEO/ANH name is
    a genuine loss of the old clip -- that is the vanished key 60001 on field 30057 this module was built for."""
    if len(parts) < 2:
        return None
    if parts[0] in ID_KEYED_DIRECTIVES:
        return (parts[0], parts[1])
    if parts[0] in MINT_DIRECTIVES:
        return ("line", " ".join(parts))
    return None


def foreign_registrations_dropped(before_lines, after_lines, owned=None) -> list:
    """The FOREIGN registrations present in ``before_lines`` but absent from ``after_lines`` -- a safety net
    for a revert / re-apply / wholesale install that is about to silently lose a line it does not own. Returns
    the dropped lines (verbatim, de-duplicated, in first-seen order) so the caller can WARN loudly.

    Reported kinds: ``3DModel``/``3DModelAnimation`` (the vanished-clip footgun this module was minted for) AND
    the id-keyed ``FieldScene``/``LocationName``. FieldScene was originally excluded as "the deploy's own
    business" -- that was right about the deploy's OWN id and wrong about every other session's: with several
    checkouts deploying into ONE mod folder, a wholesale campaign install drops a co-resident field's
    FieldScene line, and an unregistered field id makes the engine load a null ``.eb`` -- a BLACK SCREEN in
    game with no error and no record on disk of why (2026-07-18: field 4003's line vanished and a retired
    registration was byte-identical to a lost one). The loudest signal we have must cover the worst symptom.

    OWN vs FOREIGN is the whole distinction, and it lives in the caller: ``owned`` is an optional
    ``line -> bool`` predicate excluding a dropped line the caller DOES own (its own fresh mint a revert
    correctly removes; its own field's line ``tools/deploy_field.py`` filters out and re-appends). A call site
    that reports FieldScene MUST pass a predicate mirroring its own filter exactly -- disagree in one direction
    and the guard goes silent, in the other and it fires on every deploy."""
    def _regs(lines):
        out = []
        for ln in lines:
            ident = _registration_identity(ln.split())
            if ident is not None:
                out.append((ident, ln.strip()))
        return out
    after = {ident for ident, _ in _regs(after_lines)}
    dropped, seen = [], set()
    for ident, ln in _regs(before_lines):
        if ident in after or ident in seen or (owned is not None and owned(ln)):
            continue
        dropped.append(ln)
        seen.add(ident)
    return dropped
