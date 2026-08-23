"""The per-id deploy REVERT-script generator (extracted from ``tools/deploy_field.py`` so it is unit-testable).

A field deploy writes a small standalone Python script (``revert_deploy_<id>.py``) that undoes it, and a
subsequent deploy RUNS the prior revert as its prelude -- so this generated script is load-bearing for the
whole dev loop and it executes against the LIVE game install.

Security/robustness contract: every *data* value (paths, ids, names, the mod-folder) is injected as a
``repr()`` literal, NEVER interpolated raw into a string context. Raw interpolation was safe only by accident
-- ``deploy_field`` forces a sandbox name/id and Windows path rules happen to exclude quotes -- but it is a
code-generation-by-string-splicing pattern that becomes arbitrary-code-execution-on-revert the moment a
toml/mod-derived string reaches it. ``repr()`` closes that class outright: an odd character in a path or name
can no longer break, let alone escape, the generated script.

The ``*_revert_code`` arguments are the OPPOSITE: they are trusted Python fragments the caller generated for
the optional channels (start-state CSVs, BattlePatch, TextPatch, ForkDonorPatch) and are spliced in verbatim.
They begin with ``\\n`` + column-0 (unindented) code on purpose, so they dedent out of the ``for L in LANGS``
loop and run ONCE after it -- keep that splice position exactly.
"""
from __future__ import annotations

from pathlib import Path


def build_revert_script(*, kit, backup_dir, stamp, mod_folder, fid, name, fbg, text_block, repo,
                        mint_ids=(), mint_anim_keys=(), mes_blocks=(),
                        csv_revert_code="", bp_revert_code="", tp_revert_code="", fork_revert_code="") -> str:
    """Return the text of a field deploy's revert script. See the module docstring for the data-vs-code split.

    ``kit`` / ``backup_dir`` / ``repo`` may be str or Path (coerced); ``fid`` / ``text_block`` are ints;
    the ``*_revert_code`` fragments are trusted generated code (spliced verbatim)."""
    kit = str(kit)
    backup_dir = str(Path(backup_dir))
    repo = str(repo)
    fid = int(fid)
    text_block = int(text_block)
    _mint_ids_repr = repr(sorted(mint_ids))              # this deploy's minted GEO ids (drop their 3DModel lines)
    _mint_anim_keys_repr = repr(sorted(mint_anim_keys))   # this deploy's OWN 3DModelAnimation keys (drop only THESE)
    _mes_blocks_repr = repr(sorted(mes_blocks))            # this deploy's OWN registered text block(s)
    fid_str = str(fid)                                    # revert_dictionary_patch takes fid as a STRING
    evt_name = f"EVT_{name}"
    eb_stem = f"EVT_{name}.eb.bytes"
    note = f"revert_deploy_{fid}.py"
    final_msg = ("reverted: DictionaryPatch (incl. mint 3DModel/3DModelAnimation) + dialogue + start-state CSVs "
                 f"+ BattlePatch + TextPatch + ForkDonorPatch restored; {name} removed. (staged "
                 "Models//Animations/ trees left inert on disk)")
    return f'''#!/usr/bin/env python3
import sys, shutil
from pathlib import Path
sys.path.insert(0, {kit!r})
from ff9mapkit.config import find_game_path, ModLayout, LANGS
from ff9mapkit.fsutil import atomic_write_text
from ff9mapkit import dictpatch as _dp
from ff9mapkit import deploylog as _dlog   # NEEDED by the ledger call at the bottom -- a missing import here
#                                            NameErrors every generated revert, and a deploy RUNS the revert
#                                            as its prelude, so that would break deploying outright.
STAMP={stamp!r}; BK=Path({backup_dir!r}); _GAME=find_game_path(); live=ModLayout(_GAME/{mod_folder!r})
# surgical DictionaryPatch revert: drop THIS id's line + THIS deploy's OWN mint registrations (3DModel <mintId> by
# exact id and 3DModelAnimation <key> by exact key) from the CURRENT live file -- preserving any FOREIGN line another
# tool added into the SAME mod folder since this deploy (deploy_battle's "BattleScene <sceneid>", or a
# `model-anim-new` clip that merely SHARES a minted model's GEO block -- an exact-key drop leaves it be). Then
# restore this id's prior registration from the pre-deploy backup if it had one. A wholesale snapshot-restore (the
# old behavior) re-clobbered co-deployed lines; a GEO-BLOCK drop (the older-still behavior) wiped foreign clip lines
# like key 60001. (The staged Models//Animations/ FBX+clip trees are LEFT on disk -- inert once unregistered.)
_MINT_IDS=set({_mint_ids_repr}); _MINT_ANIM_KEYS=set({_mint_anim_keys_repr}); _MES_BLOCKS=set({_mes_blocks_repr})
# a MISSING live DictionaryPatch is EMPTY, not an error: a campaign deploy wholesale-replaces mod folders,
# and a deploy runs this script as its prelude -- crashing here would hard-block every redeploy of the slot
# (the prelude's exit code is checked) over a folder there is nothing left to revert in.
_dp_before=live.dictionary_patch.read_text(encoding="utf-8").splitlines() if live.dictionary_patch.exists() else []
_dpbak=BK/f"DictionaryPatch.txt.preDEPLOY.{{STAMP}}"
_bak=_dpbak.read_text(encoding="utf-8").splitlines() if _dpbak.exists() else []
_dpkeep,_lost=_dp.revert_dictionary_patch(_dp_before, _bak, fid={fid_str!r}, model_ids=_MINT_IDS, anim_keys=_MINT_ANIM_KEYS, text_blocks=_MES_BLOCKS)
live.dictionary_patch.parent.mkdir(parents=True, exist_ok=True)
# ATOMIC: at revert time this file is the ONLY copy of foreign lines added since the deploy -- a truncated
# write here loses other sessions' registrations with no backup that contains them.
atomic_write_text(live.dictionary_patch, "\\n".join(_dpkeep)+"\\n", newline="\\n")
for _dl in _lost:   # belt-and-suspenders: a foreign line this revert shouldn't have touched
    print(f"  !! WARNING: revert dropped a DictionaryPatch line it does not own: {{_dl}}")
shutil.rmtree(live.fieldmap_dir({fbg!r}), ignore_errors=True)
mc=live.mapconfig_path({evt_name!r})
if mc.exists(): mc.unlink()
for L in LANGS:
    p=live.eb_path(L,{eb_stem!r})
    if p.exists(): p.unlink()
    mb=BK/f"{{L}}-{text_block}.mes.preDEPLOY.{{STAMP}}"
    if mb.exists():
        live.mes_path(L,{text_block}).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(mb, live.mes_path(L,{text_block})){csv_revert_code}{bp_revert_code}{tp_revert_code}{fork_revert_code}
# Ledger: this id is now deliberately UNregistered, so `doctor` won't cry "lost registration" over it. Note a
# deploy runs the prior revert as its PRELUDE, so most 'retired' rows are immediately followed by a 'deployed'
# row -- last-event-wins makes that read correctly. This call only helps NEWLY generated reverts; the ~30 older
# scripts on disk emit nothing, which is exactly why deploylog.reconcile() (not this line) is the mechanism.
_dlog.record(_GAME, _dlog.RETIRED, {fid}, {mod_folder!r}, checkout={repo!r}, note={note!r})
print({final_msg!r})
'''
