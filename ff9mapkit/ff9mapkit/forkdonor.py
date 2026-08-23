"""Pure ``ForkDonorPatch.txt`` row bookkeeping -- the fork-fidelity donor map's merge and revert.

The file is one ``<forkId> <donorRealId>`` row per forked field (read by the engine's s24-s33 fork-donor
remap suite at launch), shared by every deploy into the folder. ``tools/deploy_field.py`` used to inline
the merge and revert with a WHOLESALE snapshot restore -- which re-clobbered every row another deploy added
between a deploy and its revert: fork A deploys (backup = the empty/absent file), fork B adds its row,
redeploy A runs A's revert as the prelude and B's row is GONE -- B silently loses its donor remap (the
recurring hand-written ``4003 1860`` class: broken character-vs-overlay occlusion, lost off-mesh
exemptions). The revert here is SURGICAL: it touches only this fork's own row, exactly like
``dictpatch.revert_dictionary_patch`` for DictionaryPatch and ``battlepatch.revert_splice`` for
BattlePatch blocks.
"""
from __future__ import annotations

#: the file's one comment line; re-emitted at the top of every rewrite (byte-compatible with the header
#: ``tools/deploy_field.py`` has always written, so existing live files round-trip unchanged).
HEADER = "# ff9mapkit fork-fidelity: <forkId> <donorRealId>"


def _rows(text: str) -> list:
    """The data rows of a ForkDonorPatch text -- blank and ``#`` comment lines dropped."""
    return [ln for ln in (text or "").splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")]


def own_row(text: str, fid) -> str | None:
    """This fork's own ``<fid> <donor>`` row in ``text``, or ``None``. Matched on the EXACT first token --
    never a substring, so fork 300 can't claim fork 3000's row."""
    for ln in _rows(text):
        if ln.split()[0:1] == [str(fid)]:
            return ln
    return None


def merge_row(live_text: str, fid, donor) -> str:
    """``live_text`` with this fork's row set to ``<fid> <donor>`` -- replacing its own prior row, keeping
    every FOREIGN row, header first. The deploy-side write."""
    rows = [ln for ln in _rows(live_text) if ln.split()[0:1] != [str(fid)]]
    rows.append(f"{fid} {donor}")
    return HEADER + "\n" + "\n".join(rows) + "\n"


def revert_row(current_text: str, backup_text: str, fid) -> str:
    """The SURGICAL revert: drop this fork's row from ``current_text`` (the live file NOW, which may carry
    rows other deploys added since), then re-add the row it had in ``backup_text`` (the pre-deploy
    snapshot; ``""`` when the file didn't exist). Foreign rows always survive. Returns the new file text;
    ``""`` means no rows remain (caller deletes the file)."""
    rows = [ln for ln in _rows(current_text) if ln.split()[0:1] != [str(fid)]]
    prior = own_row(backup_text, fid)
    if prior is not None:
        rows.append(prior)
    return (HEADER + "\n" + "\n".join(rows) + "\n") if rows else ""
