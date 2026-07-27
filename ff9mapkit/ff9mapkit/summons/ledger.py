r"""THE WRITE LEDGER for the summon EDIT lanes -- every write a build performs, plus the revert that
undoes exactly those writes and nothing else.

A summon reskin or rescore writes a whole-container override into a mod folder. That is a destructive
act against shared state (one FF9 install, several mod folders, several concurrent sessions), and the
lane's characteristic failure is SILENCE: ``SFX.Play`` passes ``suppressMissingError = true``, so a
misresolved or half-written override logs nothing at all and the stock effect simply plays. "Nothing
changed" is therefore the symptom of every mistake, which is why this ledger exists and why every rule
below is enforced here rather than trusted to each call site.

THE FIVE RULES
--------------
1. **A pre-existing file is BACKED UP before it is overwritten**, and the backup path is recorded.
2. **A newly created file records ``None``**, so the revert DELETES it rather than restoring a file
   that never existed.
3. **Every write is READ BACK and compared.** A write that did not land is exactly the silent failure
   this lane cannot afford; :class:`LedgerError` is raised the moment the readback disagrees.
4. **A ``ModFileList.txt`` is APPENDED TO, never CREATED.** ``TryFindAssetInModOnDisc`` TRUSTS such a
   list and never calls ``File.Exists``, so a folder that has one hides every file the list omits --
   and creating one would therefore make every OTHER file in that folder invisible at a stroke.
5. **The emitted revert script is ``--root``-rebasable.** Every destination under the mod root is
   recorded relative to it, so the same plan can undo the same writes in a DIFFERENT folder (a sandbox
   rehearsal, a re-pinned deploy target). A script that can only undo itself in the one absolute
   directory it was born in is a script nobody can safely rehearse.

RELATIONSHIP TO ``summons/deploy.py``
-------------------------------------
``deploy.py`` carries its own ``_Ledger`` (the ``[[summon]]`` transplant lane's, shipped and proven).
This one is a strict SUPERSET of it: same backup/readback/record posture, plus ``mod_root`` tracking,
the ``rel`` per-entry rebase key, ``add_list_line``/``list_rel`` and the ``--root`` revert template.
``deploy.py`` is deliberately NOT changed to import this module -- that lane is deployed and cast-proven
and a promotion is not the moment to re-plumb it. This note is the cross-reference so the duplication is
a KNOWN one with a stated direction (if the two ever converge, this is the superset to converge on), not
a silent fork somebody discovers later.

PROVENANCE: this module writes only caller-supplied bytes to caller-supplied paths. It embeds no game
data and resolves no path of its own -- the local-only / repo / install guards live with the lanes that
choose the destination.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from pathlib import Path
from typing import List, Optional

__all__ = ["LedgerError", "Ledger", "REVERT_TEMPLATE"]


class LedgerError(RuntimeError):
    """Raised when a write did not land as written (the readback disagrees) -- the silent-failure guard."""


class Ledger:
    """Accumulates every write of one build and renders the revert that undoes exactly those writes."""

    def __init__(self, backup_dir, mod_root=None):
        self.backup_dir = Path(backup_dir)
        #: the mod folder every recorded destination lives under. Recorded so the emitted revert
        #: script can take ``--root`` and undo the same writes in a DIFFERENT folder instead of being
        #: welded to the one absolute path it was born in. ``None`` is legitimate: a lane whose writes
        #: straddle a mod folder AND a staging-only sibling records absolute paths only, because a
        #: HALF-rebased revert would be worse than an un-rebasable one.
        self.mod_root = Path(mod_root) if mod_root is not None else None
        self.stamp = time.strftime("%Y%m%d-%H%M%S")
        self.files: List[dict] = []
        self.list_line: Optional[str] = None
        self.list_path: Optional[str] = None
        self.list_rel: Optional[str] = None

    def _rel(self, path) -> Optional[str]:
        """``path`` expressed relative to the mod root, or ``None`` when it is not under it.

        ``None`` is the honest answer, not a fallback: a file outside the mod root cannot be rebased by
        ``--root``, so the script keeps its absolute path and says so. An escaping ``../`` is rejected
        HERE rather than at either call site -- a relative path that climbs out of the root would let a
        later ``--root`` resolve into a file the caller never named.
        """
        if self.mod_root is None:
            return None
        try:
            rel = Path(os.path.relpath(Path(path).resolve(),
                                       self.mod_root.resolve())).as_posix()
        except (ValueError, OSError):                            # pragma: no cover - another drive
            return None
        return None if (rel == ".." or rel.startswith("../")) else rel

    def _record(self, dest, backup) -> None:
        self.files.append({"dest": str(dest), "backup": str(backup) if backup else None,
                           "rel": self._rel(dest)})

    def write_bytes(self, dest, data: bytes) -> str:
        """Back up (if it exists), write atomically, READ BACK, record. Returns the sha256 written."""
        from .. import fsutil
        dest = Path(dest)
        backup = None
        if dest.exists():
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            backup = self.backup_dir / ("%s.pre-%s" % (dest.name, self.stamp))
            shutil.copyfile(dest, backup)
        dest.parent.mkdir(parents=True, exist_ok=True)
        fsutil.atomic_write_bytes(dest, data)
        if dest.read_bytes() != data:                            # pragma: no cover
            raise LedgerError("write verification failed at %s -- readback != what we wrote" % dest)
        self._record(dest, backup)
        return hashlib.sha256(data).hexdigest()

    def add_list_line(self, list_path, line: str) -> bool:
        """Append ``line`` to an EXISTING ``ModFileList.txt``; return whether it was added.

        NEVER creates one (rule 4). Returns ``False`` both when there is no list and when the line is
        already present -- an idempotent no-op, so re-running a build cannot grow the file.
        """
        from .. import fsutil
        lp = Path(list_path)
        if not lp.exists():
            return False
        lines = lp.read_text(encoding="utf-8").splitlines()
        if any(l.strip().lower() == line for l in lines):
            return False
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        backup = self.backup_dir / ("%s.pre-%s" % (lp.name, self.stamp))
        shutil.copyfile(lp, backup)
        lines.append(line)
        fsutil.atomic_write_text(lp, "\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        self.list_line, self.list_path = line, str(lp)
        self.list_rel = self._rel(lp)
        self._record(lp, backup)
        return True

    def revert_plan(self) -> dict:
        return {"files": self.files, "list_line": self.list_line, "list_path": self.list_path,
                "list_rel": self.list_rel,
                "mod_root": str(self.mod_root) if self.mod_root is not None else ""}

    def write_revert_script(self, out_dir, name: str,
                            prefix: str = "revert_summon_camera") -> Path:
        """Render :data:`REVERT_TEMPLATE` with this ledger's plan -> ``<out_dir>/<prefix>_<name>.py``.

        The plan is injected as ``repr(json.dumps(plan))`` -- a Python literal wrapping a JSON document
        -- so no path, quote or backslash in a recorded name can break out of the template.
        """
        from .. import fsutil
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        plan = json.dumps(self.revert_plan(), indent=2)
        script = REVERT_TEMPLATE.replace("__PLAN__", repr(plan))
        p = out_dir / ("%s_%s.py" % (prefix, name))
        fsutil.atomic_write_text(p, script, encoding="utf-8", newline="\n")
        return p


REVERT_TEMPLATE = '''#!/usr/bin/env python3
"""Auto-generated revert for a summon container override -- stdlib only, no ff9mapkit import.

Restores each backed-up file, deletes each file the build newly created, and drops the ModFileList
line it added. Idempotent: safe to run more than once.

    py revert_summon_camera_<ef>.py [--root <mod folder>] [--dry-run]

``--root`` re-targets every path the plan recorded UNDER the mod root it was staged into. The staged
root is the DEFAULT, so the zero-argument invocation is byte-for-byte the original behaviour. It exists
because a script that can only undo itself in the one absolute directory it was born in is un-rehearsable,
and rehearsing a revert in a sandbox before pointing it at a real mod folder is the whole point of
shipping one.

Paths the plan recorded OUTSIDE the mod root -- the backups, which live in the staging WORK dir -- stay
absolute and are never rebased: a backup is staging-side state, not mod-folder state.
"""
import json, shutil, sys
from pathlib import Path

PLAN = json.loads(__PLAN__)


REBASABLE = any(e.get("rel") for e in PLAN["files"]) or bool(PLAN.get("list_rel"))


def parse_argv(argv):
    root, explicit, dry, rest = PLAN.get("mod_root") or "", False, False, []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--root":
            if i + 1 >= len(argv):
                print("FAIL: --root needs a directory"); raise SystemExit(2)
            root, explicit = argv[i + 1], True; i += 2; continue
        if a.startswith("--root="):
            root, explicit = a.split("=", 1)[1], True; i += 1; continue
        if a == "--dry-run":
            dry = True; i += 1; continue
        if a in ("-h", "--help"):
            print(__doc__); raise SystemExit(0)
        rest.append(a); i += 1
    if rest:
        print(f"FAIL: unexpected argument(s): {' '.join(rest)}"); raise SystemExit(2)
    # A plan built by a ledger that was given no mod root records ONLY absolute paths, so --root has
    # nothing to rebase.  Refuse it loudly rather than accepting a flag that does nothing: silently
    # ignoring --root would let a caller believe they had re-targeted a revert that in fact still
    # points at the original folder -- a partial or wrong-folder revert is worse than no revert.
    if explicit and not REBASABLE:
        print("FAIL: --root has nothing to rebase -- this plan records no mod-root-relative path "
              "(it was staged without a mod root, so every path in it is absolute).")
        raise SystemExit(2)
    if REBASABLE and not root:
        print("FAIL: this plan records mod-root-relative paths but no mod root -- pass "
              "--root <mod folder>")
        raise SystemExit(2)
    return (Path(root) if root else None), dry


ROOT, DRY = parse_argv(sys.argv[1:])


def target(entry):
    """Where to restore to: rebased under ROOT when the plan recorded a mod-root-relative path,
    else the absolute path the write actually landed at (which --root cannot honestly rebase)."""
    rel = entry.get("rel")
    return (ROOT / rel) if (rel and ROOT is not None) else Path(entry["dest"])


list_path = (ROOT / PLAN["list_rel"]) if (PLAN.get("list_rel") and ROOT is not None) \\
    else Path(PLAN.get("list_path") or "")
if PLAN.get("list_line") and PLAN.get("list_path") and list_path.exists():
    kept = [ln for ln in list_path.read_text(encoding="utf-8").splitlines()
            if ln.strip().lower() != PLAN["list_line"]]
    if DRY:
        print(f"would drop ModFileList line: {PLAN['list_line']}  ({list_path})")
    else:
        list_path.write_text("\\n".join(kept) + ("\\n" if kept else ""),
                             encoding="utf-8", newline="\\n")
        print(f"dropped ModFileList line: {PLAN['list_line']}")

stop = ROOT.resolve() if (ROOT is not None and ROOT.exists()) else None
for entry in PLAN["files"]:
    dest, backup = target(entry), entry.get("backup")
    if backup and Path(backup).exists():
        if DRY:
            print(f"would restore {dest} <- {Path(backup).name}")
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(backup, dest)
        print(f"restored {dest} <- {Path(backup).name}")
    elif dest.exists():
        if DRY:
            print(f"would delete  {dest}")
            continue
        dest.unlink()
        print(f"deleted  {dest}")
        parent = dest.parent
        while parent.exists() and parent.name and not any(parent.iterdir()):
            if stop is not None and parent.resolve() == stop:
                break                      # never prune the mod folder the caller pointed us at
            parent.rmdir()
            parent = parent.parent
print("dry run -- nothing written." if DRY else "summon override revert complete.")
'''


#: the study lanes (and their tests) name this class ``_Ledger``; it was private only while it lived in
#: one study script. The public name is :class:`Ledger`.
_Ledger = Ledger
#: the study name for :data:`REVERT_TEMPLATE`.
_REVERT_TEMPLATE = REVERT_TEMPLATE
