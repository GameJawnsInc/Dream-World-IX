"""World DRAFTS: a mod folder's world files copied OUT of the install, where the editor's edits land first.

The overworld editor's Accept (rung C1) never writes the live install. It writes a DRAFT: a copy of one mod
folder's ``FF9_Data/WorldMap`` disc trees (Disc1 and its Disc4 mirror, the ``.bak-*`` backups left behind) plus
its ``.ff9world.jsonl`` ledger, under :func:`drafts_dir`. The world verbs take the draft's absolute path as their
``--mod-folder`` unchanged, so an edit through the editor is the same CLI call, writing the same bytes, as one typed
by hand (``Path(game) / absolute`` is the absolute path).

THE LAUNCHER LAW (memory ``project-ff9-launcher-activates-new-folders``): the Memoria launcher activates any new
folder it finds in the install, so a draft root inside the game folder would put an unreviewed draft into the game
on the next launch. :func:`ensure_draft` refuses one.

A draft keeps a manifest of what it copied (``draft.json``: each file's sha-256, size and both mtimes; a file whose
size and mtime still match is unchanged without a hash), so it can tell its own edits
(:func:`edits`: files the draft changed or added since the copy) from the source moving on underneath it
(:func:`stale`: source files that changed since the copy -- another session deployed).

PROMOTE (rung C4) is the ONE path from a draft into the install: :func:`promote` writes the draft's edits into its
live folder (refusing when a file it edited moved in the live folder since the copy), backs up and ledgers each write
as the deploy seam does, runs the disc-4 mirror there, and snapshots every live file at the edited cells first, so
:func:`revert` puts them back byte for byte. Nothing else in this module writes the install.

A DRAFT HOLDS DISC 1's EDITS ONLY. The verbs' disc-4 mirror (``discmirror.auto_mirror``) compares each cell's stock
ground across discs, which needs the install's bundles; a draft's root has none, so the mirror logs NOT RUN there,
exactly as it does for any absolute ``--mod-folder`` outside the install. Its Disc4 tree is the source's as copied;
:func:`promote` runs the mirror in the live folder.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import time
from pathlib import Path

DRAFT_FILE = "draft.json"
DISCS = (1, 4)                                    # the disc-1 edit and its disc-4 mirror (auto_mirror's target)
LEDGER = ".ff9world.jsonl"


def drafts_dir() -> Path:
    """Where drafts live: the kit's extract cache (gitignored in a checkout, per-user when installed)."""
    from .. import provision
    return provision.cache_dir() / "world-drafts"


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _same(p: Path, rec, which: int) -> bool:
    """Is file ``p`` still the bytes manifest record ``rec`` names? Its stat first (``rec[which]`` is the mtime of
    that side's copy), its hash only when the stat moved."""
    try:
        st = p.stat()
    except OSError:
        return False
    if st.st_size == rec[1] and st.st_mtime_ns == rec[which]:
        return True
    return st.st_size == rec[1] and _sha(p) == rec[0]


def _world_files(folder: Path):
    """``rel -> path`` for every file a draft carries: the DISCS trees without backups, and the ledger."""
    out = {}
    for d in DISCS:
        tree = folder / "FF9_Data" / "WorldMap" / f"Disc{d}"
        if tree.is_dir():
            for p in tree.rglob("*"):
                if p.is_file() and ".bak-" not in p.name:
                    out[p.relative_to(folder).as_posix()] = p
    return out


def _inside(p: Path, root: Path) -> bool:
    try:
        p.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


DRAFT_SUFFIX = ".draft"


def draft_path(source: Path, *, root=None) -> Path:
    """``<root>/<folder>.draft``: named apart from its source, so a point read from it says "the draft" (a file's
    owner is its folder's name)."""
    return Path(root or drafts_dir()) / (Path(source).name + DRAFT_SUFFIX)


def read_meta(draft: Path):
    """The draft's ``draft.json``, or None when ``draft`` is not a draft."""
    try:
        return json.loads((Path(draft) / DRAFT_FILE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def ensure_draft(source: Path, *, game, root=None) -> Path:
    """The draft of mod folder ``source``: reuse the one already made from it (its edits kept), else copy one.

    Refuses a draft root inside the install (THE LAUNCHER LAW) and a source with no world tree."""
    source = Path(source)
    root = Path(root or drafts_dir())
    if game is not None and _inside(root, Path(game)):
        raise ValueError(f"the draft folder {root} is inside the game install {game}: the launcher would activate "
                         "it as a mod on the next launch. Drafts must live outside the install.")
    draft = draft_path(source, root=root)
    meta = read_meta(draft)
    if meta is not None:
        if Path(meta["source"]).resolve() != source.resolve():
            raise ValueError(f"{draft} is a draft of {meta['source']}, not of {source}")
        return draft
    files = _world_files(source)
    if not any(r.startswith("FF9_Data/") for r in files):
        raise ValueError(f"{source} has no FF9_Data/WorldMap disc tree to draft")
    if draft.exists():
        raise ValueError(f"{draft} exists and is not a draft; move it aside")
    tmp = draft.with_name(draft.name + ".making")
    if tmp.exists():
        shutil.rmtree(tmp)
    manifest = {}
    for rel, p in sorted(files.items()):
        dst = tmp / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        data = p.read_bytes()                     # one read, one write, the hash from the bytes in hand
        dst.write_bytes(data)
        manifest[rel] = [hashlib.sha256(data).hexdigest(), len(data), p.stat().st_mtime_ns, 0]
    for rel in manifest:                          # the copy's own mtimes, once the copy is whole
        manifest[rel][3] = (tmp / rel).stat().st_mtime_ns
    led = source / LEDGER
    if led.is_file():
        shutil.copy2(led, tmp / LEDGER)
    meta = {"source": str(source.resolve()), "made": time.strftime("%Y-%m-%dT%H:%M:%S"), "manifest": manifest}
    (tmp / DRAFT_FILE).write_text(json.dumps(meta, indent=1), encoding="utf-8")
    tmp.rename(draft)                             # whole or not at all: a half copy is never taken for a draft
    return draft


def edits(draft: Path) -> list:
    """Draft-relative paths the draft changed or added since it was copied (its own edits), sorted."""
    meta = read_meta(draft)
    if meta is None:
        return []
    man = meta["manifest"]
    out = []
    for rel, p in _world_files(Path(draft)).items():
        if rel == LEDGER:
            continue
        if rel not in man or not _same(p, man[rel], 3):
            out.append(rel)
    return sorted(out)


def stale(draft: Path) -> list:
    """Source-relative paths that changed in the SOURCE since the draft was copied (another deploy moved it on)."""
    meta = read_meta(draft)
    if meta is None:
        return []
    man = meta["manifest"]
    src = _world_files(Path(meta["source"]))
    out = [rel for rel, p in src.items() if rel != LEDGER and (rel not in man or not _same(p, man[rel], 2))]
    out += [rel for rel in man if rel not in src]
    return sorted(set(out))


def edited_blocks(draft: Path) -> list:
    """``(disc, bx, by)`` for every block whose files the draft edited, sorted (the caption's count)."""
    import re
    got = set()
    for rel in edits(draft):
        m = re.search(r"Disc(\d+)/[^/]+/r\d+/Block\[(\d+)\]\[(\d+)\]", rel)
        if m:
            got.add((int(m.group(1)), int(m.group(2)), int(m.group(3))))
    return sorted(got)


def discard(draft: Path, *, root=None) -> None:
    """Delete a draft (its edits with it). Refuses anything that is not a draft under the drafts root."""
    draft = Path(draft)
    root = Path(root or drafts_dir())
    if read_meta(draft) is None or not _inside(draft, root) or draft.resolve() == root.resolve():
        raise ValueError(f"{draft} is not a draft under {root}")
    shutil.rmtree(draft)


# ---------------------------------------------------------------- promote (rung C4): the draft into the live folder
PROMOTES = "promotes"                             # <draft>/promotes/<stamp>/ : each promote's record and snapshot
_REL = re.compile(r"Disc(\d+)/[^/]+/r\d+/Block\[(\d+)\]\[(\d+)\] (.+?)(\.ff9mesh)?$")


def _parse_rel(rel: str):
    """``(disc, (bx, by), part)`` of a world file's relative path (part None for a sidecar), or None."""
    m = _REL.search(rel)
    if not m:
        return None
    return int(m.group(1)), (int(m.group(2)), int(m.group(3))), m.group(4) if m.group(5) else None


def _cell_files(folder: Path, cells) -> dict:
    """``rel -> path`` for every live file at ``cells`` on the DISCS trees (every part, sidecars too), no backups."""
    out = {}
    for d in DISCS:
        tree = folder / "FF9_Data" / "WorldMap" / f"Disc{d}"
        for bx, by in cells:
            for p in tree.glob(f"*/r{by}/Block[[]{bx}[]][[]{by}[]] *"):
                if p.is_file() and ".bak-" not in p.name and not p.name.endswith(".promoting"):
                    out[p.relative_to(folder).as_posix()] = p
    return out


def _write_meta(draft: Path, meta: dict) -> None:
    tmp = Path(draft) / (DRAFT_FILE + ".tmp")
    tmp.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    tmp.replace(Path(draft) / DRAFT_FILE)


def _record(data: bytes, src_mtime: int, draft_mtime: int) -> list:
    return [hashlib.sha256(data).hexdigest(), len(data), src_mtime, draft_mtime]


def _rebase(draft: Path, meta: dict, rels) -> None:
    """Bring the draft level with the live folder at ``rels``: copy each live file in and record it as the baseline
    (a file the live folder no longer has leaves the draft and the manifest)."""
    source, man = Path(meta["source"]), meta["manifest"]
    for rel in sorted(set(rels)):
        live, mine = source / rel, Path(draft) / rel
        if live.is_file():
            data = live.read_bytes()
            mine.parent.mkdir(parents=True, exist_ok=True)
            mine.write_bytes(data)
            man[rel] = _record(data, live.stat().st_mtime_ns, mine.stat().st_mtime_ns)
        else:
            if mine.is_file():
                mine.unlink()
            man.pop(rel, None)
    _write_meta(draft, meta)


def _write_live(live: Path, data: bytes, *, source: Path) -> None:
    """THE ONE LIVE WRITE: park what is there (the deploy seam's backup), write it whole (a temp file renamed over
    it), and ledger the bytes, so a later deploy at this cell reads them as kit-written, not foreign."""
    from . import mesh as M
    if live.exists():
        M.park_backup(live)
    live.parent.mkdir(parents=True, exist_ok=True)
    tmp = live.with_name(live.name + ".promoting")
    tmp.write_bytes(data)
    os.replace(tmp, live)
    parsed = _parse_rel(live.relative_to(source).as_posix())
    if parsed is not None and parsed[2] is not None:
        disc, cell, part = parsed
        M.record_ledger_write(live, cell=cell, part=part, write_disc=disc, mod_root=source)


def promote(draft: Path, *, game, dry_run: bool = False, log=print) -> dict:
    """Write the draft's edits into its live mod folder, then mirror them to disc 4 the way the verbs do.

    Refuses, before writing anything, when the draft has no edits, when its source is not a folder of ``game``, or
    when any file it edited changed in the live folder since the copy (another session deployed there: promoting
    would overwrite their bytes). Every live file at the edited cells (both discs, every part) is snapshotted first
    into ``<draft>/promotes/<stamp>/``, so :func:`revert` restores them exactly. Afterwards the draft is rebased: it
    equals the live folder again, with no edits and nothing stale. Returns the promote record."""
    from . import discmirror as DM
    from . import mesh as M
    draft = Path(draft)
    meta = read_meta(draft)
    if meta is None:
        raise ValueError(f"{draft} is not a draft")
    source = Path(meta["source"])
    if game is None or not _inside(source, Path(game)):
        raise ValueError(f"the draft's source {source} is not a folder of the install {game}")
    rels = edits(draft)
    if not rels:
        raise ValueError(f"the draft of {source.name} has no edits to promote")
    man = meta["manifest"]
    moved = [rel for rel in rels
             if ((source / rel).exists() if rel not in man else not _same(source / rel, man[rel], 2))]
    if moved:
        raise ValueError(f"{len(moved)} file(s) the draft edited changed in {source.name} since the draft was made "
                         f"(another deploy wrote them): {moved[:4]}. Promoting would overwrite that work; discard the "
                         "draft and place the edit again on a fresh one.")
    cells = sorted({p[1] for p in map(_parse_rel, rels) if p is not None})
    before = _cell_files(source, cells)
    plan = {"op": "promote", "source": str(source), "folder": source.name, "cells": [list(c) for c in cells],
            "promoted": rels}
    if dry_run:
        return plan
    stamp = time.strftime("%Y%m%d-%H%M%S")
    rec_dir, n = draft / PROMOTES / stamp, 2
    while rec_dir.exists():
        rec_dir, n = draft / PROMOTES / f"{stamp}-{n}", n + 1
    before_sha = {}
    for rel, p in before.items():                  # the snapshot (bytes and hashes), before any byte moves
        dst = rec_dir / "before" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        data = p.read_bytes()
        dst.write_bytes(data)
        before_sha[rel] = hashlib.sha256(data).hexdigest()
    written = []
    with M.ledger_pipeline("world-promote", draft=str(draft)):
        for rel in rels:
            _write_live(source / rel, (draft / rel).read_bytes(), source=source)
            written.append(source / rel)
            log(f"promoted -> {source / rel}")
        DM.auto_mirror(written, mod_folder=source.name, log=log)
    after = _cell_files(source, cells)
    record = {**plan, "utc": time.strftime("%Y-%m-%dT%H:%M:%S"), "record": str(rec_dir),
              "before": before_sha,
              "after": {rel: _sha(p) for rel, p in after.items()}, "reverted": None}
    (rec_dir / "promote.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
    _rebase(draft, meta, list(after) + list(before) + stale(draft))
    return record


def promotes(draft: Path) -> list:
    """The draft's promote records, oldest first."""
    out = []
    for p in sorted((Path(draft) / PROMOTES).glob("*/promote.json")):
        try:
            out.append(json.loads(p.read_text(encoding="utf-8")))
        except ValueError:
            continue
    return out


def last_promote(draft: Path):
    """The newest promote not yet reverted, or None."""
    live = [r for r in promotes(draft) if not r.get("reverted")]
    return live[-1] if live else None


def revert(draft: Path, *, game, dry_run: bool = False, log=print) -> dict:
    """Undo the draft's last promote: every file at its cells goes back to the snapshot's bytes (a file the promote
    created is parked and removed), the disc-4 files with them, exactly. Refuses when any of those files changed after
    the promote (a later deploy: reverting would erase it). The promoted bytes stay in the draft, as its edits again."""
    from . import mesh as M
    draft = Path(draft)
    meta = read_meta(draft)
    rec = last_promote(draft) if meta is not None else None
    if rec is None:
        raise ValueError(f"{draft} has no promote to revert")
    source = Path(rec["source"])
    if game is None or not _inside(source, Path(game)):
        raise ValueError(f"the promote's folder {source} is not a folder of the install {game}")
    now = _cell_files(source, [tuple(c) for c in rec["cells"]])
    changed = sorted(rel for rel in set(now) | set(rec["after"])
                     if (rel in now) != (rel in rec["after"]) or (rel in now and _sha(now[rel]) != rec["after"][rel]))
    if changed:
        raise ValueError(f"{len(changed)} file(s) at the promoted blocks changed after the promote: {changed[:4]}. "
                         "Reverting would erase that later work.")
    if dry_run:
        return {**rec, "op": "revert"}
    snap = Path(rec["record"]) / "before"
    for rel, sha in rec["before"].items():          # every snapshot whole before any byte moves
        if not (snap / rel).is_file() or _sha(snap / rel) != sha:
            raise ValueError(f"the snapshot of {rel} is missing or damaged; nothing was restored")
    touched = sorted(set(rec["before"]) | set(rec["after"]))
    with M.ledger_pipeline("world-promote", draft=str(draft), revert=rec["utc"]):
        for rel in touched:
            live = source / rel
            if rel in rec["before"]:
                if not live.is_file() or _sha(live) != rec["before"][rel]:
                    _write_live(live, (snap / rel).read_bytes(), source=source)
                    log(f"restored -> {live}")
            elif live.is_file():
                sha0 = _sha(live)
                bak = M.park_backup(live)
                live.unlink()
                parsed = _parse_rel(rel)
                if parsed is not None and parsed[2] is not None:
                    M.record_ledger_removal(source, cell=parsed[1], part=parsed[2], write_disc=parsed[0],
                                            removed_sha256=sha0, backup=bak)
                log(f"removed -> {live} (the promote created it)")
    rec["reverted"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    (Path(rec["record"]) / "promote.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    # the draft: the promoted files are its edits again (their baseline is the restored live bytes); everything else
    # the promote touched (the disc-4 mirror) is level with the live folder again
    edited = set(rec["promoted"])
    _rebase(draft, meta, [rel for rel in touched if rel not in edited])
    man = meta["manifest"]
    for rel in edited:
        live = source / rel
        if live.is_file():
            man[rel] = _record(live.read_bytes(), live.stat().st_mtime_ns, 0)   # the draft's copy differs: an edit
        else:
            man.pop(rel, None)
    _write_meta(draft, meta)
    return {**rec, "op": "revert"}
