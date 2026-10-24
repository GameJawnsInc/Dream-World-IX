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
(:func:`edits`: files the draft changed or added since the copy; :func:`removals`: files it deleted, as
``world-river --remove`` and a river move do) from the source moving on underneath it (:func:`stale`: source files
that changed since the copy -- another session deployed).

THE LEDGER TRAVELS WITH THE BYTES. A verb's ownership read (``river.deploy_ownership``) trusts a file only when the
folder's ledger records its bytes under that verb. So Promote writes each file into the live ledger under the
draft's own row's pipeline tag (never just "world-promote"), and mirrors it under that tag too; after a Promote the
draft takes the live ledger (the two are level); Revert and Undo/Redo put the ledger back with the bytes. Without
this a moved river, once promoted or undone, would read as foreign to its own verb and refuse to move again.

THE HISTORY (rung C3): every step the editor writes into a draft (an Accept, a recipe row) snapshots the files at
the cells it may write before and after (:func:`begin_step` / :func:`commit_step`), so :func:`undo` and :func:`redo`
walk the recipe byte for byte without re-running a verb, and :func:`recipe_rows` is the document Save writes.

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


def stands_in_for(folder):
    """The name of the live folder a draft at ``folder`` stands in for (its source), else None: the stack reads skip
    it, since the draft holds what it copied from there."""
    p = Path(str(folder))
    if not p.is_absolute():
        return None
    meta = read_meta(p)
    return Path(meta["source"]).name if meta else None


def removals(draft: Path) -> list:
    """Draft-relative paths the draft DELETED since it was copied (a removal is an edit too), sorted."""
    meta = read_meta(draft)
    if meta is None:
        return []
    have = _world_files(Path(draft))
    return sorted(rel for rel in meta["manifest"] if rel != LEDGER and rel not in have)


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
    for rel in edits(draft) + removals(draft):
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


def _ledger_key(rel: str):
    """``(disc, (bx, by), part)`` a world file is ledgered under, or None: a mesh by its part, a ``Donor.txt``
    sidecar as part ``Donor`` (``mesh.deploy_donor_sidecar``'s rows), so Promote ledgers both."""
    parsed = _parse_rel(rel)
    if parsed is None:
        return None
    if parsed[2] is not None:
        return parsed
    m = re.search(r"\] (\w+)\.txt$", rel)
    return (parsed[0], parsed[1], m.group(1)) if m else None


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


def _ledger_last(folder: Path) -> dict:
    """``(disc, bx, by, part) -> row``: ``folder``'s last ledger row for each world file."""
    from . import mesh as M
    last = {}
    for e in M.read_ledger(folder):
        try:
            last[(int(e["write_disc"]), int(e["cell"][0]), int(e["cell"][1]), str(e["part"]))] = e
        except (KeyError, TypeError, ValueError, IndexError):
            continue
    return last


def _row_tag(e):
    """A ledger row's writer as a ``ledger_pipeline`` tag: its ``pipeline`` field, else the verb its argv ran."""
    from . import mesh as M
    if e is None:
        return None
    tag = e.get("pipeline") or ({"verb": M.ledger_verb(e.get("argv")), "argv": e.get("argv")}
                                if M.ledger_verb(e.get("argv")) else None)
    return tag if tag and tag.get("verb") else None


def _ledger_tags(folder: Path, rels, last=None) -> dict:
    """``rel -> tag``: for each world file at ``rels``, the writer of ``folder``'s last ledger row for it, the tag
    Promote and Revert carry the file's bytes under."""
    last = _ledger_last(folder) if last is None else last
    out = {}
    for rel in rels:
        key = _ledger_key(rel)
        tag = None if key is None else _row_tag(last.get((key[0], *key[1], key[2])))
        if tag:
            out[rel] = tag
    return out


def _tagged(tag):
    """A ``ledger_pipeline`` for ``tag``, the writer the row keeps, with ``via`` naming the promote (or revert) that
    carried it -- inside one, whose own tag stays on rows that have no writer of their own (a nullcontext then)."""
    import contextlib
    from . import mesh as M
    if not tag:
        return contextlib.nullcontext()
    outer = M._LEDGER_PIPELINE or {}
    via = {"via": outer["verb"], **{k: v for k, v in outer.items() if k != "verb"}} if outer else {}
    return M.ledger_pipeline(**{**via, **{k: v for k, v in tag.items() if k != "via"}})


def _unlink_live(live: Path, *, source: Path) -> None:
    """THE ONE LIVE DELETE: park it (the deploy seam's backup), remove it, ledger the removal."""
    from . import mesh as M
    sha0 = _sha(live)
    bak = M.park_backup(live)
    live.unlink()
    parsed = _ledger_key(live.relative_to(source).as_posix())
    if parsed is not None:
        M.record_ledger_removal(source, cell=parsed[1], part=parsed[2], write_disc=parsed[0], removed_sha256=sha0,
                                backup=bak)


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
    parsed = _ledger_key(live.relative_to(source).as_posix())
    if parsed is not None:
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
    rels, gone = edits(draft), removals(draft)
    if not rels and not gone:
        raise ValueError(f"the draft of {source.name} has no edits to promote")
    man = meta["manifest"]
    moved = [rel for rel in rels
             if ((source / rel).exists() if rel not in man else not _same(source / rel, man[rel], 2))]
    moved += [rel for rel in gone if (source / rel).exists() and not _same(source / rel, man[rel], 2)]
    if moved:
        raise ValueError(f"{len(moved)} file(s) the draft edited changed in {source.name} since the draft was made "
                         f"(another deploy wrote them): {moved[:4]}. Promoting would overwrite that work; discard the "
                         "draft and place the edit again on a fresh one.")
    tags = _ledger_tags(draft, rels + gone)        # each file's bytes keep their verb in the live ledger
    # THE RELABEL: a file at the edited cells whose bytes the draft left as they were, but which the draft's ledger
    # gives another writer (a moved river's cell the new river fills with the old one's very bytes, an open Sea4
    # sheet): its bytes need no write, its ownership does, and its disc-4 copy must be mirrored again with the rest
    # (found by the ledgers: a key whose last row the draft wrote itself, the live folder's last row being another)
    dl, ll = _ledger_last(draft), _ledger_last(source)
    near = sorted({(k[1], k[2]) for k, e in dl.items() if e.get("sha256") and e != ll.get(k)})
    relabel = []
    for rel, p in sorted(_cell_files(draft, near).items()):
        key = _ledger_key(rel)
        if rel in rels or key is None or not (source / rel).is_file():
            continue
        e, sha = dl.get((key[0], *key[1], key[2])), _sha(p)
        if e and e.get("sha256") == sha == _sha(source / rel) and _row_tag(e) != _row_tag(
                ll.get((key[0], *key[1], key[2]))):
            relabel.append(rel)
    tags.update(_ledger_tags(draft, relabel, dl))
    cells = sorted({p[1] for p in map(_parse_rel, rels + gone + relabel) if p is not None})
    before = _cell_files(source, cells)            # (a relabelled cell's disc-4 copy is mirrored again: snapshot it)
    plan = {"op": "promote", "source": str(source), "folder": source.name, "cells": [list(c) for c in cells],
            "promoted": rels, "removed": gone, "relabelled": relabel}
    if dry_run:
        return plan
    stamp = time.strftime("%Y%m%d-%H%M%S")
    rec_dir, n = draft / PROMOTES / stamp, 2
    while rec_dir.exists():
        rec_dir, n = draft / PROMOTES / f"{stamp}-{n}", n + 1
    rec_dir.mkdir(parents=True)                    # (cells the live folder has nothing at snapshot no file: a sink
    before_sha = {}                                # of a stock island; the record must still be written)
    for rel, p in before.items():                  # the snapshot (bytes and hashes), before any byte moves
        dst = rec_dir / "before" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        data = p.read_bytes()
        dst.write_bytes(data)
        before_sha[rel] = hashlib.sha256(data).hexdigest()
    groups = {}                                    # tag -> the written disc-1 paths it mirrors under
    with M.ledger_pipeline("world-promote", draft=str(draft)):
        for rel in gone:                           # the deletions first: a moved river's new cells overlap its old
            if (source / rel).is_file():
                with _tagged(tags.get(rel)):
                    _unlink_live(source / rel, source=source)
                log(f"removed -> {source / rel}")
        for rel in rels:
            with _tagged(tags.get(rel)):
                _write_live(source / rel, (draft / rel).read_bytes(), source=source)
            groups.setdefault(json.dumps(tags.get(rel), sort_keys=True), []).append(source / rel)
            log(f"promoted -> {source / rel}")
        for rel in relabel:
            key = _ledger_key(rel)
            with _tagged(tags[rel]):
                M.record_ledger_write(source / rel, cell=key[1], part=key[2], write_disc=key[0], mod_root=source)
            groups.setdefault(json.dumps(tags[rel], sort_keys=True), []).append(source / rel)
            log(f"relabelled -> {source / rel} (bytes unchanged, now {tags[rel].get('verb')}'s)")
        for key, paths in groups.items():
            with _tagged(json.loads(key)):
                DM.auto_mirror(paths, mod_folder=source.name, log=log)
    after = _cell_files(source, cells)
    record = {**plan, "utc": time.strftime("%Y-%m-%dT%H:%M:%S"), "record": str(rec_dir),
              "before": before_sha, "tags": tags,
              "after": {rel: _sha(p) for rel, p in after.items()}, "reverted": None}
    _mark_promoted(draft, record)                  # the recipe's steps so far are live: undo stops above them
    (rec_dir / "promote.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
    _rebase(draft, meta, list(after) + list(before) + stale(draft))
    _take_ledger(draft, source)                    # level with the live folder: its ledger is the draft's now
    return record


def _take_ledger(draft: Path, source: Path) -> None:
    led = Path(source) / LEDGER
    if led.is_file():
        shutil.copy2(led, Path(draft) / LEDGER)


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
                _unlink_live(live, source=source)
                log(f"removed -> {live} (the promote created it)")
    rec["reverted"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    _unmark_promoted(draft, rec)
    (Path(rec["record"]) / "promote.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    # the draft: the promoted files are its edits again (their baseline is the restored live bytes); everything else
    # the promote touched (the disc-4 mirror) is level with the live folder again
    edited = set(rec["promoted"]) | set(rec.get("removed", ()))
    _rebase(draft, meta, [rel for rel in touched if rel not in edited])
    man = meta["manifest"]
    for rel in edited:
        live = source / rel
        if live.is_file():
            man[rel] = _record(live.read_bytes(), live.stat().st_mtime_ns, 0)   # the draft's copy differs: an edit
        else:
            man.pop(rel, None)
    _write_meta(draft, meta)
    # the ledger: the live one (level at every other cell), plus the draft's own bytes at the promoted files, under
    # the tags they were promoted with (the edits are the draft's again, owned by the verb that made them)
    _take_ledger(draft, source)
    for rel in sorted(rec["promoted"]):
        parsed = _ledger_key(rel)
        if (draft / rel).is_file() and parsed is not None:
            with _tagged((rec.get("tags") or {}).get(rel)):
                M.record_ledger_write(draft / rel, cell=parsed[1], part=parsed[2], write_disc=parsed[0],
                                      mod_root=draft)
    return {**rec, "op": "revert"}


# ---------------------------------------------------------------- the recipe's history (rung C3): undo and redo
HISTORY = "history.json"                          # <draft>/history.json: the steps, the cursor, the promoted mark
HISTORY_DIR = "history"                           # <draft>/history/<n>/{before,after}/<rel>: each step's cells
_PENDING = "pending"


def history(draft: Path) -> dict:
    """The draft's steps: ``{"steps": [...], "cursor": n, "promoted": m}``. Steps ``[0, cursor)`` are applied (the
    recipe), the rest can be redone; steps ``[0, promoted)`` are in the live folder and cannot be undone here (Revert
    promote first). Each step: ``{"row", "label", "cells", "before", "after", "dir"}``, where ``before`` / ``after``
    map every file at the step's cells to its sha-256 (a file missing from one side did not exist there)."""
    try:
        h = json.loads((Path(draft) / HISTORY).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        h = {}
    return {"steps": h.get("steps", []), "cursor": int(h.get("cursor", 0)), "promoted": int(h.get("promoted", 0))}


def _write_history(draft: Path, h: dict) -> None:
    tmp = Path(draft) / (HISTORY + ".tmp")
    tmp.write_text(json.dumps(h, indent=1), encoding="utf-8")
    tmp.replace(Path(draft) / HISTORY)


def _snap(draft: Path, cells, dest: Path) -> dict:
    """Copy every file at ``cells`` (both discs, every part) under ``dest``; ``rel -> sha``."""
    out = {}
    for rel, p in sorted(_cell_files(Path(draft), cells).items()):
        data = p.read_bytes()
        q = dest / rel
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_bytes(data)
        out[rel] = hashlib.sha256(data).hexdigest()
    return out


def _restore(draft: Path, files: dict, snap: Path, cells) -> None:
    """Put the files at ``cells`` back to ``files`` (from the snapshot ``snap``): written back, or removed when that
    side never had them."""
    for rel in sorted(set(files) | set(_cell_files(Path(draft), cells))):
        p = Path(draft) / rel
        if rel in files:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes((snap / rel).read_bytes())
        elif p.is_file():
            p.unlink()


def _keep_ledger(draft: Path, side: Path) -> None:
    """A step's side keeps the draft's ledger as it was then (the ownership reads trust bytes the ledger records)."""
    led = Path(draft) / LEDGER
    if led.is_file():
        side.mkdir(parents=True, exist_ok=True)
        shutil.copy2(led, side / LEDGER)


def _put_ledger(draft: Path, side: Path) -> None:
    """Put the draft's ledger back as the step's side kept it (a step recorded before the ledger was kept: none)."""
    if (side / LEDGER).is_file():
        shutil.copy2(side / LEDGER, Path(draft) / LEDGER)


def _differs(draft: Path, files: dict, cells) -> list:
    now = {rel: _sha(p) for rel, p in _cell_files(Path(draft), cells).items()}
    return sorted(rel for rel in set(now) | set(files) if now.get(rel) != files.get(rel))


def all_cells() -> list:
    """Every block of the world (24 x 20): a step whose cells are not known in advance snapshots them all."""
    return [(bx, by) for by in range(20) for bx in range(24)]


def begin_step(draft: Path, cells) -> None:
    """Before a step writes the draft: snapshot every file at the ``cells`` it may write (a superset is fine)."""
    pend = Path(draft) / HISTORY_DIR / _PENDING
    if pend.exists():
        shutil.rmtree(pend)
    cells = sorted({(int(bx) % 24, int(by)) for bx, by in cells})
    pend.mkdir(parents=True)                         # (a step over open sea has no file to snapshot)
    before = _snap(draft, cells, pend / "before")
    _keep_ledger(draft, pend / "before")
    (pend / "step.json").write_text(json.dumps({"cells": [list(c) for c in cells], "before": before}),
                                    encoding="utf-8")


def commit_step(draft: Path, row: dict, label: str) -> dict:
    """The step ran: record it after the applied steps (dropping any undone ones, as an edit after an undo does).
    Only the files that changed are kept in the step."""
    draft = Path(draft)
    pend = draft / HISTORY_DIR / _PENDING
    step = json.loads((pend / "step.json").read_text(encoding="utf-8"))
    cells = [tuple(c) for c in step["cells"]]
    after = _snap(draft, cells, pend / "after")
    _keep_ledger(draft, pend / "after")
    before = step["before"]
    moved = {rel for rel in set(before) | set(after) if before.get(rel) != after.get(rel)}
    keep = sorted({_parse_rel(rel)[1] for rel in moved if _parse_rel(rel) is not None})
    before = {rel: h for rel, h in before.items() if _parse_rel(rel) and _parse_rel(rel)[1] in keep}
    after = {rel: h for rel, h in after.items() if _parse_rel(rel) and _parse_rel(rel)[1] in keep}
    for side in ("before", "after"):                 # the untouched cells' copies go (a whole-map step stays small)
        for rel in _cell_files(pend / side, [c for c in cells if c not in set(keep)]):
            (pend / side / rel).unlink()
    h = history(draft)
    for old in h["steps"][h["cursor"]:]:
        shutil.rmtree(draft / old["dir"], ignore_errors=True)
    n = h["cursor"]
    rel_dir = f"{HISTORY_DIR}/{n:04d}"
    shutil.rmtree(draft / rel_dir, ignore_errors=True)
    pend.rename(draft / rel_dir)
    rec = {"row": row, "label": label, "cells": [list(c) for c in keep], "before": before, "after": after,
           "dir": rel_dir, "utc": time.strftime("%Y-%m-%dT%H:%M:%S")}
    h["steps"] = h["steps"][:n] + [rec]
    h["cursor"] = n + 1
    _write_history(draft, h)
    return rec


def abort_step(draft: Path) -> None:
    """The step failed: put its cells back as they were before it (a verb refuses before writing, so this is
    usually a no-op), and forget it."""
    pend = Path(draft) / HISTORY_DIR / _PENDING
    if not (pend / "step.json").is_file():
        return
    step = json.loads((pend / "step.json").read_text(encoding="utf-8"))
    _restore(draft, step["before"], pend / "before", [tuple(c) for c in step["cells"]])
    _put_ledger(draft, pend / "before")
    shutil.rmtree(pend)


def undo(draft: Path) -> dict:
    """Take the last applied step back out of the draft, byte for byte. Refuses a step already promoted (Revert
    promote first) and a step whose files changed since (something else wrote the draft)."""
    draft = Path(draft)
    h = history(draft)
    if h["cursor"] == 0:
        raise ValueError("nothing to undo")
    if h["cursor"] <= h["promoted"]:
        raise ValueError("the last step is promoted into the live folder: Revert promote first")
    s = h["steps"][h["cursor"] - 1]
    cells = [tuple(c) for c in s["cells"]]
    bad = _differs(draft, s["after"], cells)
    if bad:
        raise ValueError(f"{len(bad)} file(s) of '{s['label']}' changed since it was applied: {bad[:3]}")
    _restore(draft, s["before"], draft / s["dir"] / "before", cells)
    _put_ledger(draft, draft / s["dir"] / "before")
    h["cursor"] -= 1
    _write_history(draft, h)
    return s


def redo(draft: Path) -> dict:
    """Put the next undone step back into the draft, byte for byte (its recorded result: the verb is not re-run)."""
    draft = Path(draft)
    h = history(draft)
    if h["cursor"] >= len(h["steps"]):
        raise ValueError("nothing to redo")
    s = h["steps"][h["cursor"]]
    cells = [tuple(c) for c in s["cells"]]
    bad = _differs(draft, s["before"], cells)
    if bad:
        raise ValueError(f"{len(bad)} file(s) at '{s['label']}' changed since it was undone: {bad[:3]}")
    _restore(draft, s["after"], draft / s["dir"] / "after", cells)
    _put_ledger(draft, draft / s["dir"] / "after")
    h["cursor"] += 1
    _write_history(draft, h)
    return s


def recipe_rows(draft: Path) -> list:
    """The applied steps' recipe rows, in order: the draft's document."""
    h = history(draft)
    return [s["row"] for s in h["steps"][:h["cursor"]]]


def _mark_promoted(draft: Path, record: dict) -> None:
    h = history(draft)
    record["history_promoted_before"] = h["promoted"]
    h["promoted"] = h["cursor"]
    _write_history(draft, h)


def _unmark_promoted(draft: Path, record: dict) -> None:
    h = history(draft)
    h["promoted"] = int(record.get("history_promoted_before", 0))
    _write_history(draft, h)
