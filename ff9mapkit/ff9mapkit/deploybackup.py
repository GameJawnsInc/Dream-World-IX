"""Collision-proof pre-deploy backups: ``<backups>/<file>.preDEPLOY.<STAMP>`` for ``tools/deploy_field.py``.

A field deploy snapshots every live file it is about to change (DictionaryPatch, ForkDonorPatch, the dialogue
``.mes``, the start-state CSVs, BattlePatch, TextPatch, ...) to ``<backups>/<label>.preDEPLOY.<STAMP>``, and the
revert script it generates restores from exactly those names. The names are only as unique as ``STAMP``.

THE BUG this module closes: ``STAMP`` was a one-second ``%Y%m%d-%H%M%S``. A scripted batch lands several deploys
in one second (the story-trace rung-3 batch deployed 22 forks in about 20 s), and the later deploy's backups
silently OVERWROTE the earlier one's -- which by then already held the earlier id's OWN ``FieldScene`` line and
ForkDonorPatch row. The earlier id's revert re-adds every line it owns that it finds in its backup
(``dictpatch.revert_dictionary_patch``, ``forkdonor.revert_row``), so it deleted its ``.eb`` and RESTORED its own
registration: a half-revert that leaves a FieldScene pointing at a missing ``.eb``, the null-.eb black screen.
Six rung-3 forks and one fight-ledger bench carried such a revert (studies/story-trace/HANDOFF.md).

Two layers, because a finer clock alone is not a guarantee (Windows clocks can be coarse, and deploys into
DIFFERENT mod folders share one backups dir without sharing a folder lock):

* :func:`claim_stamp` draws a microsecond stamp and CLAIMS it by writing the deploy's first backup
  create-exclusive. If that name is already taken it tries the same stamp with a ``-<n>`` suffix, so a frozen
  or coarse clock still terminates. Every field deploy takes that first backup unconditionally, so a claimed
  stamp is unique among all deploys that claim.
* :func:`backup_exclusive` writes every later backup create-exclusive too, and raises :class:`BackupExists`
  rather than replace a file that is already there: an overwritten backup can never be silent again.
"""
from __future__ import annotations

import datetime
import shutil
from pathlib import Path

#: The stamp's clock part. Microseconds, so a sequential batch no longer shares a stamp; the claim below is what
#: makes it UNIQUE. Stays sortable in deploy order (and after the old one-second stamps of the same second).
STAMP_FORMAT = "%Y%m%d-%H%M%S-%f"

#: How many suffixed variants of one clock reading :func:`claim_stamp` tries before giving up. Each failed try
#: means another deploy claimed that exact name, so reaching this is a runaway loop, not contention.
MAX_CLAIM_TRIES = 1000


class BackupExists(FileExistsError):
    """A pre-deploy backup name was already taken. It is never overwritten: another deploy's revert restores
    from it, and replacing it is exactly how a revert came to re-add the registration it should remove."""


def backup_name(label: str, stamp: str) -> str:
    """The file name every backup and every generated revert agree on: ``<label>.preDEPLOY.<stamp>``."""
    return f"{label}.preDEPLOY.{stamp}"


def backup_exclusive(src: "Path | str", dst: "Path | str") -> Path:
    """Copy ``src``'s bytes to ``dst`` CREATE-EXCLUSIVE and return ``dst``.

    Raises :class:`BackupExists` (leaving the existing file byte-for-byte untouched) when ``dst`` already exists.
    ``src`` is opened first, so a missing source creates nothing; a copy that fails midway removes its own partial
    file, never someone else's (it only ever unlinks a file this call created)."""
    src, dst = Path(src), Path(dst)
    with open(src, "rb") as fs:
        try:
            fd = open(dst, "xb")
        except FileExistsError:
            raise BackupExists(
                f"refusing to overwrite the existing backup {dst} -- another deploy's revert restores from it, "
                f"and replacing it would hand that revert this deploy's state instead of its own") from None
        try:
            with fd:
                shutil.copyfileobj(fs, fd)
        except BaseException:
            dst.unlink(missing_ok=True)
            raise
    return dst


def claim_stamp(backup_dir: "Path | str", first_src: "Path | str", first_label: str, *, now=None) -> str:
    """Claim a STAMP no other deploy holds, by writing this deploy's first backup create-exclusive.

    Writes ``first_src`` to ``<backup_dir>/<first_label>.preDEPLOY.<stamp>`` and returns ``stamp``. The stamp is
    ``now()`` formatted as :data:`STAMP_FORMAT`; if that backup name is taken, ``<stamp>-1``, ``<stamp>-2``, ... are
    tried in turn (never a fresh clock read, so a frozen or coarse clock cannot spin). ``now`` is a seam for tests
    (default :func:`datetime.datetime.now`). Raises :class:`BackupExists` after :data:`MAX_CLAIM_TRIES` taken names.

    Every caller must pass the backup it takes UNCONDITIONALLY and FIRST (deploy_field: the DictionaryPatch
    snapshot) -- the claim is only as strong as every deploy making it."""
    base = (now or datetime.datetime.now)().strftime(STAMP_FORMAT)
    root = Path(backup_dir)
    for n in range(MAX_CLAIM_TRIES):
        stamp = base if n == 0 else f"{base}-{n}"
        try:
            backup_exclusive(first_src, root / backup_name(first_label, stamp))
        except BackupExists:
            continue
        return stamp
    raise BackupExists(f"could not claim a backup stamp in {root}: {MAX_CLAIM_TRIES} names from {base} are all "
                       f"taken -- a runaway deploy loop, or a clock stuck on one reading")
