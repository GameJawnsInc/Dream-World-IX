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
EDITING A PLACED STEP (rung C9): :func:`begin_edit` undoes back to the step and lifts it and the steps after it out;
the edited shape goes in its place (or nothing, for a delete), and each step after it goes back on top, replayed from
its record (:func:`replay`) where no block it reads changed (:func:`dirty_after`), else re-run; :func:`finish_edit`
keeps the result, :func:`cancel_edit` puts the draft back exactly as it was.

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


_IS_DRAFT: dict = {}           # draft.json path -> ((size, mtime_ns, file id), is it a draft)


def is_draft(draft) -> bool:
    """``read_meta(draft) is not None``, without parsing ``draft.json`` again while its stat stands: the World tab
    asks it per Accept (14-16 times), per undo and per ghost drag frame, and a parse of the 423 KB file was 2.5-4.7 ms
    on the GUI thread (PERF.md 7). A meta write replaces the file, so its stat moves."""
    f = Path(draft) / DRAFT_FILE
    try:
        st = os.stat(f)
    except OSError:
        return False
    key = (st.st_size, st.st_mtime_ns, st.st_ino)
    hit = _IS_DRAFT.get(str(f))
    if hit is not None and hit[0] == key:
        return hit[1]
    ok = read_meta(draft) is not None
    _IS_DRAFT[str(f)] = (key, ok)
    return ok


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
    _sweep_discarded(draft)                       # (what an earlier discard could not delete yet)
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
    """Delete a draft (its edits with it), whole or not at all. Refuses anything that is not a draft under the drafts
    root. The draft is renamed aside first -- Windows refuses that, whole, while a reader holds a file in it (waited
    out by :func:`_retry`) -- and the renamed copy is deleted: a bare rmtree stopped at the first held file, deleting
    bottom-up with draft.json last, and left a gutted folder that was still a draft (review of the perf commits)."""
    draft = Path(draft)
    root = Path(root or drafts_dir())
    if read_meta(draft) is None or not _inside(draft, root) or draft.resolve() == root.resolve():
        raise ValueError(f"{draft} is not a draft under {root}")
    aside = draft.with_name(f"{draft.name}{_DISCARDING}{os.getpid()}-{time.time_ns()}")
    _retry(lambda: draft.rename(aside))
    _sweep_discarded(draft)


_DISCARDING = ".discarding-"                      # a discarded draft's name while it is deleted (never a draft's)


def _sweep_discarded(draft: Path) -> None:
    """Delete what discards of ``draft`` renamed aside (a leftover a reader held is taken on the next sweep)."""
    head = Path(draft).name + _DISCARDING                # (a listing, not a glob: a '[...]' in the name is no set)
    try:
        names = [n for n in os.listdir(Path(draft).parent) if n.startswith(head)]
    except OSError:
        return
    for n in names:
        shutil.rmtree(Path(draft).parent / n, ignore_errors=True)


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


_HEAD = re.compile(r"^Block\[\d+\]\[\d+\] ")


def _cell_files(folder: Path, cells) -> dict:
    """``rel -> path`` for every live file at ``cells`` on the DISCS trees (every part, sidecars too), no backups.
    One listing per row directory (a glob per cell and disc was 960 globs for a whole-map step: PERF.md 3)."""
    folder = Path(folder)
    rows = {}
    for bx, by in cells:
        rows.setdefault(int(by), set()).add(f"Block[{int(bx)}][{int(by)}] ")
    out = {}
    for d in DISCS:
        tree = folder / "FF9_Data" / "WorldMap" / f"Disc{d}"
        try:
            lods = sorted(e.name for e in os.scandir(tree) if e.is_dir())
        except OSError:
            continue
        for lod in lods:
            for by, heads in sorted(rows.items()):
                row = tree / lod / f"r{by}"
                try:
                    entries = sorted(os.scandir(row), key=lambda e: e.name)
                except OSError:
                    continue
                for e in entries:
                    m = _HEAD.match(e.name)
                    if (m and m.group(0) in heads and ".bak-" not in e.name and not e.name.endswith(".promoting")
                            and e.is_file()):
                        out[f"FF9_Data/WorldMap/Disc{d}/{lod}/r{by}/{e.name}"] = row / e.name
    return out


RACY_NS = 2 * 10 ** 9           # a file written within this of a stat can be written again at the same size and time


def _unmoved(p: Path, rec, at) -> bool:
    """Is ``p`` still the file a step's begin stat'ed as ``rec`` ([size, mtime_ns]) at ``at`` (ns)? Its size and
    time stand, and it was last written more than :data:`RACY_NS` before that stat: a file written in the stat's own
    clock tick can be written again at the same size and time (git's racy-clean rule), so that one is hashed."""
    if rec is None or at is None:
        return False
    try:
        st = os.stat(p)
    except OSError:
        return False
    return st.st_size == rec[0] and st.st_mtime_ns == rec[1] and rec[1] < at - RACY_NS


def _write_meta(draft: Path, meta: dict) -> None:
    tmp = Path(draft) / (DRAFT_FILE + ".tmp")
    tmp.write_text(json.dumps(meta, indent=1), encoding="utf-8")
    _retry(lambda: tmp.replace(Path(draft) / DRAFT_FILE))   # (a reader of draft.json waited out, as history's)


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
    if not dry_run:
        abort_step(Path(draft))                          # (a failed abort, finished before the draft is copied)
    from . import discmirror as DM
    from . import mesh as M
    draft = Path(draft)
    meta = read_meta(draft)
    if meta is None:
        raise ValueError(f"{draft} is not a draft")
    source = Path(meta["source"])
    if game is None or not _inside(source, Path(game)):
        raise ValueError(f"the draft's source {source} is not a folder of the install {game}")
    if history(draft)["edit"]:
        raise ValueError("an edit of a placed step is open in the draft: accept or cancel it first")
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
    # (found by the ledgers: a key whose last row the draft WROTE ITSELF -- a row the live ledger does not hold -- and
    # names a writer, the live folder's last row naming another). A row the draft inherited from its copy is not its
    # own: when the live ledger moved on after the copy (another draft of the folder promoted and reverted there), the
    # two last rows differ although the draft wrote nothing, and an inherited row that names no writer (an old
    # argv-less row) then crashed this promote half way (c9_lab, 2026-10-24)
    dl, ll = _ledger_last(draft), _ledger_last(source)
    live_rows = {json.dumps(e, sort_keys=True) for e in M.read_ledger(source)}
    near = sorted({(k[1], k[2]) for k, e in dl.items() if e.get("sha256") and _row_tag(e)
                   and json.dumps(e, sort_keys=True) not in live_rows})
    relabel = []
    for rel, p in sorted(_cell_files(draft, near).items()):
        key = _ledger_key(rel)
        if rel in rels or key is None or not (source / rel).is_file():
            continue
        e, sha = dl.get((key[0], *key[1], key[2])), _sha(p)
        own = e is not None and _row_tag(e) and json.dumps(e, sort_keys=True) not in live_rows
        if own and e.get("sha256") == sha == _sha(source / rel) and \
                _row_tag(e) != _row_tag(ll.get((key[0], *key[1], key[2]))):
            relabel.append(rel)
    tags.update(_ledger_tags(draft, relabel, dl))
    relabel = [rel for rel in relabel if rel in tags]   # every tag known before the first byte moves
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
    map every file at the step's cells to its sha-256 (a file missing from one side did not exist there). ``edit``
    is the open edit of a placed step (:func:`begin_edit`), else None."""
    try:
        h = json.loads((Path(draft) / HISTORY).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        h = {}
    return {"steps": h.get("steps", []), "cursor": int(h.get("cursor", 0)), "promoted": int(h.get("promoted", 0)),
            "edit": h.get("edit")}


def _write_history(draft: Path, h: dict) -> None:
    """history.json, whole: written aside and put in place, waiting out a reader that holds it open (the window's
    thread reads it while a worker records a step; Windows refuses the replace meanwhile: review of the perf
    commits, CR-2)."""
    tmp = Path(draft) / (HISTORY + ".tmp")
    tmp.write_text(json.dumps(h, indent=1), encoding="utf-8")
    _retry(lambda: tmp.replace(Path(draft) / HISTORY))


def _snap(draft: Path, cells, dest: Path, files=None) -> dict:
    """Copy every file at ``cells`` (both discs, every part) under ``dest``; ``rel -> sha``. ``files``: the cells'
    listing, when the caller has it."""
    out, made = {}, set()
    for rel, p in sorted((_cell_files(Path(draft), cells) if files is None else files).items()):
        data = p.read_bytes()
        q = dest / rel
        if q.parent not in made:
            q.parent.mkdir(parents=True, exist_ok=True)
            made.add(q.parent)
        q.write_bytes(data)
        out[rel] = hashlib.sha256(data).hexdigest()
    return out


def _retry(fn, *, tries: int = 60, wait: float = 0.05):
    """``fn()``, again while Windows refuses it (``PermissionError``: another thread or process holds the file open,
    as a card's island read does for a moment after an Accept), for up to ``tries * wait`` seconds."""
    for i in range(tries):
        try:
            return fn()
        except PermissionError:
            if i == tries - 1:
                raise
            time.sleep(wait)


def _restore(draft: Path, files: dict, snap: Path, cells, unmoved=None) -> None:
    """Put the files at ``cells`` back to ``files`` (from the snapshot ``snap``): written back, or removed when that
    side never had them. A file a reader holds open for a moment is waited for (:func:`_retry`): an Edit clicked
    while a card still reads the island it just accepted raced its own undo here (c11_lab). ``unmoved(rel, path)``
    True leaves a file that is still the snapshot's bytes as it is."""
    for rel in sorted(set(files) | set(_cell_files(Path(draft), cells))):
        p = Path(draft) / rel
        if rel in files and unmoved is not None and unmoved(rel, p):
            continue
        if rel in files:
            p.parent.mkdir(parents=True, exist_ok=True)
            data = (snap / rel).read_bytes()
            _retry(lambda p=p, data=data: p.write_bytes(data))
        elif p.is_file():
            _retry(p.unlink)


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
    """Before a step writes the draft: snapshot every file at the ``cells`` it may write (a superset is fine). A
    pending step left by an abort that failed is aborted first: its snapshot holds the before-images of the half
    step, which deleting it left in the draft unrecorded (review of the perf commits, F2)."""
    pend = Path(draft) / HISTORY_DIR / _PENDING
    abort_step(draft)
    if pend.exists():
        shutil.rmtree(pend)
    cells = sorted({(int(bx) % 24, int(by)) for bx, by in cells})
    pend.mkdir(parents=True)                         # (a step over open sea has no file to snapshot)
    files, at = _cell_files(draft, cells), time.time_ns()
    stat = {}                                        # each file's size and time: what commit and abort trust
    for rel, p in files.items():
        st = os.stat(p)
        stat[rel] = [st.st_size, st.st_mtime_ns]
    before = _snap(draft, cells, pend / "before", files)
    _keep_ledger(draft, pend / "before")
    (pend / "step.json").write_text(json.dumps({"cells": [list(c) for c in cells], "before": before,
                                                "stat": stat, "at": at}), encoding="utf-8")


def commit_step(draft: Path, row: dict, label: str) -> dict:
    """The step ran: record it after the applied steps (dropping any undone ones, as an edit after an undo does).
    Only the files that changed are kept in the step. A file whose size and time stand since :func:`begin_step` is
    the bytes it snapshotted (:func:`_unmoved`), so only the files that moved are read again (a whole-map step read
    all 2,088 again and copied them: PERF.md 3)."""
    draft = Path(draft)
    pend = draft / HISTORY_DIR / _PENDING
    step = json.loads((pend / "step.json").read_text(encoding="utf-8"))
    cells = [tuple(c) for c in step["cells"]]
    before, stat, at = step["before"], step.get("stat", {}), step.get("at")
    now = _cell_files(draft, cells)
    after = {rel: before[rel] if rel in before and _unmoved(p, stat.get(rel), at) else _sha(p)
             for rel, p in sorted(now.items())}
    moved = {rel for rel in set(before) | set(after) if before.get(rel) != after.get(rel)}
    keep = sorted({_parse_rel(rel)[1] for rel in moved if _parse_rel(rel) is not None})
    keep_set = set(keep)
    _snap(draft, keep, pend / "after", {rel: p for rel, p in now.items()        # the kept cells' after side only
                                        if _parse_rel(rel) and _parse_rel(rel)[1] in keep_set})
    _keep_ledger(draft, pend / "after")
    before = {rel: h for rel, h in before.items() if _parse_rel(rel) and _parse_rel(rel)[1] in keep}
    after = {rel: h for rel, h in after.items() if _parse_rel(rel) and _parse_rel(rel)[1] in keep}
    # THE ORDER: the pending folder goes in place first, under a name no step holds, retried while a handle is open
    # in it; only then is it trimmed, the history written and the undone steps dropped. A rename that still fails
    # leaves the pending step whole (abort_step finishes it) and the undone steps redo-able (review of the perf
    # fixes, round 2, H2)
    h = history(draft)
    n = h["cursor"]
    rel_dir = f"{HISTORY_DIR}/{n:04d}"
    if (draft / rel_dir).exists():                   # (an undone step's folder: kept until the history drops it)
        rel_dir = f"{HISTORY_DIR}/{n:04d}-{time.time_ns()}"
    _retry(lambda: pend.rename(draft / rel_dir))
    home = draft / rel_dir
    for rel in _cell_files(home / "before", [c for c in cells if c not in keep_set]):
        (home / "before" / rel).unlink()             # the untouched cells' copies go (a whole-map step stays small)
    (home / "step.json").write_text(json.dumps({"cells": step["cells"], "before": step["before"]}),
                                    encoding="utf-8")
    rec = {"row": row, "label": label, "cells": [list(c) for c in keep], "before": before, "after": after,
           "dir": rel_dir, "utc": time.strftime("%Y-%m-%dT%H:%M:%S")}
    undone = h["steps"][n:]
    h["steps"] = h["steps"][:n] + [rec]
    h["cursor"] = n + 1
    _write_history(draft, h)
    for old in undone:                               # (dropped from the history: their folders go)
        shutil.rmtree(draft / old["dir"], ignore_errors=True)
    return rec


def abort_step(draft: Path) -> None:
    """The step failed: put its cells back as they were before it (a verb refuses before writing, so this is
    usually a no-op), and forget it. Only what the step moved is written back (:func:`_unmoved`): rewriting all
    2,088 files of a whole-map step took 14-28 s and moved every file's time (PERF.md 3)."""
    pend = Path(draft) / HISTORY_DIR / _PENDING
    if not (pend / "step.json").is_file():
        return
    step = json.loads((pend / "step.json").read_text(encoding="utf-8"))
    if any(not (pend / "before" / rel).is_file() for rel in step["before"]):
        shutil.rmtree(pend)                          # a commit's, trimmed before a rename that failed (an older kit):
        return                                       # its writes are in the draft; replayed in part it wedged it (H2)
    stat, at = step.get("stat", {}), step.get("at")
    _restore(draft, step["before"], pend / "before", [tuple(c) for c in step["cells"]],
             unmoved=lambda rel, p: _unmoved(p, stat.get(rel), at))
    _put_ledger(draft, pend / "before")
    shutil.rmtree(pend)


def undo(draft: Path) -> dict:
    """Take the last applied step back out of the draft, byte for byte. Refuses a step already promoted (Revert
    promote first) and a step whose files changed since (something else wrote the draft)."""
    draft = Path(draft)
    abort_step(draft)                                    # a failed abort, finished before this rewrites its cells
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
    abort_step(draft)                                    # a failed abort, finished before this rewrites its cells
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


OWED = "promote-owed.json"                        # <draft>/promote-owed.json: the game is owed a promote back


def owe_promote(draft: Path, fence: int) -> None:
    """The editor took the draft's promotes out of the game to edit a step that was in it (rung C19): until the
    first ``fence`` steps are promoted back, this says so on disk, so a Workspace that closes or dies mid-edit puts
    the game right on its next launch (the in-memory chain dies with it)."""
    tmp = Path(draft) / (OWED + ".tmp")
    tmp.write_text(json.dumps({"fence": int(fence), "utc": time.strftime("%Y-%m-%dT%H:%M:%S")}), encoding="utf-8")
    tmp.replace(Path(draft) / OWED)


def promote_owed(draft: Path):
    """The fence :func:`owe_promote` recorded (how many steps the game is owed back), or None."""
    try:
        return int(json.loads((Path(draft) / OWED).read_text(encoding="utf-8"))["fence"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def settle_promote(draft: Path) -> None:
    """The promote back ran (or can no longer run): nothing is owed."""
    (Path(draft) / OWED).unlink(missing_ok=True)


# ---------------------------------------------------------------- editing a placed step (rung C9)
EDIT_DIR = "edit"                                 # <draft>/history/edit/<n>/ : the lifted steps while an edit is open


def begin_edit(draft: Path, k: int) -> dict:
    """Open an edit of applied step ``k`` (0-based): undo back to it, byte for byte, and LIFT step ``k`` and every
    step after it out of the history (their records parked under ``history/edit/``, so :func:`cancel_edit` puts them
    back exactly). The draft is then as it was before step ``k``: the card judges the edited shape there, and the
    caller puts the steps after it back on top, each replayed (:func:`replay`) or re-run. Refuses a step out of range,
    a promoted step (Revert promote first), an edit already open and a lifted step whose record is gone; whatever
    fails on the way (an undo that refuses, a step's folder the disk will not move, the history write) is put back
    -- the folders moved back, the steps undone redone -- before it is raised: the open is whole or nothing (review
    of the perf fixes, round 3, H1)."""
    draft = Path(draft)
    abort_step(draft)                                    # (an abort that failed, finished first: F2)
    h = history(draft)
    if h["edit"]:
        raise ValueError("an edit is already open in the draft")
    if not 0 <= k < h["cursor"]:
        raise ValueError(f"step {k + 1} is not an applied step of the recipe")
    if k < h["promoted"]:
        raise ValueError(f"step {k + 1} is in the game (promoted): Revert promote first")
    for i, s in enumerate(h["steps"][k:], start=k):      # (an older kit could drop an undone step's folder)
        if not (draft / s["dir"]).is_dir():
            raise ValueError(f"the record of step {i + 1} ({s['label']}) is missing from the draft ({s['dir']})")
    park = draft / HISTORY_DIR / EDIT_DIR
    shutil.rmtree(park, ignore_errors=True)
    park.mkdir(parents=True)                             # (a leftover the disk keeps refuses here, nothing moved)
    cursor, done, moved = h["cursor"], 0, []
    try:
        while history(draft)["cursor"] > k:
            undo(draft)
            done += 1
        h = history(draft)
        lifted = []
        for i, s in enumerate(h["steps"][k:]):
            rel = f"{HISTORY_DIR}/{EDIT_DIR}/{i:04d}"
            _retry(lambda s=s, rel=rel: (draft / s["dir"]).rename(draft / rel))
            moved.append((s["dir"], rel))
            lifted.append({**s, "dir": rel, "home": s["dir"]})
        h["steps"] = h["steps"][:k]
        h["edit"] = {"at": k, "applied": cursor - k, "lifted": lifted, "utc": time.strftime("%Y-%m-%dT%H:%M:%S")}
        _write_history(draft, h)
    except (ValueError, OSError):                        # a refusal, or the disk: either way, back as it was
        for home, rel in reversed(moved):
            _retry(lambda home=home, rel=rel: (draft / rel).rename(draft / home))
        for _ in range(done):
            redo(draft)
        raise
    return h["edit"]


def replay(draft: Path, step: dict) -> bool:
    """Put a lifted step back on top of the draft as it was recorded, without re-running its verb: its after-images
    at its cells, and its own ledger rows appended. Only when its files are still exactly as it found them (its
    before-images) and its ledger then was the ledger before it plus its own rows; otherwise nothing is written and
    False comes back (the caller re-runs its row). Whether the verb READ only unchanged blocks is the caller's call
    (the dirty set: :func:`dirty_after`)."""
    draft = Path(draft)
    cells = [tuple(c) for c in step["cells"]]
    if _differs(draft, step["before"], cells):
        return False
    side = draft / step["dir"]
    before, after = side / "before" / LEDGER, side / "after" / LEDGER
    delta = b""
    if after.is_file():
        a = after.read_bytes()
        b = before.read_bytes() if before.is_file() else b""
        if not a.startswith(b):
            return False
        delta = a[len(b):]
    begin_step(draft, cells)
    _restore(draft, step["after"], side / "after", cells)
    if delta:
        with open(draft / LEDGER, "ab") as f:
            f.write(delta)
    commit_step(draft, step["row"], step["label"])
    return True


def _by_cell(files: dict) -> dict:
    out = {}
    for rel, sha in files.items():
        p = _parse_rel(rel)
        if p is not None:
            out.setdefault(p[1], {})[rel] = sha
    return out


def dirty_after(dirty, old, new) -> set:
    """THE DIRTY SET of an edit: the blocks where the edited draft may differ from the draft as it was, once a step
    is put back. ``old`` is the step as first recorded, ``new`` the one now in its place (None: nothing in its place,
    a deleted step). A block both wrote alike is clean again; any other block either wrote is dirty; a block neither
    wrote keeps what it was. Conservative: a dirty block only costs a re-run."""
    o = _by_cell(old["after"]) if old else {}
    n = _by_cell(new["after"]) if new else {}
    oc = {tuple(c) for c in old["cells"]} if old else set()
    nc = {tuple(c) for c in new["cells"]} if new else set()
    same = {c for c in oc & nc if o.get(c, {}) == n.get(c, {})}
    return (set(dirty) | oc | nc) - same


def finish_edit(draft: Path) -> dict:
    """Close an open edit, keeping what was put back: the lifted records go (undone steps beyond it with them, as
    any edit after an undo drops them)."""
    draft = Path(draft)
    h = history(draft)
    e = h["edit"]
    if not e:
        raise ValueError("no edit is open in the draft")
    shutil.rmtree(draft / HISTORY_DIR / EDIT_DIR, ignore_errors=True)
    h["edit"] = None
    _write_history(draft, h)
    return e


def cancel_edit(draft: Path) -> dict:
    """Close an open edit as if it never began: a half-run step is aborted, every step put back since
    :func:`begin_edit` is undone byte for byte, and the lifted steps go back in, applied as they were (redone from
    their records), the undone ones after them still redoable."""
    draft = Path(draft)
    abort_step(draft)
    e = history(draft)["edit"]
    if not e:
        raise ValueError("no edit is open in the draft")
    k = e["at"]
    while history(draft)["cursor"] > k:
        undo(draft)
    h = history(draft)
    for s in h["steps"][k:]:
        shutil.rmtree(draft / s["dir"], ignore_errors=True)
    steps = h["steps"][:k]
    for s in e["lifted"]:
        shutil.rmtree(draft / s["home"], ignore_errors=True)
        (draft / s["dir"]).rename(draft / s["home"])
        steps.append({**{key: v for key, v in s.items() if key != "home"}, "dir": s["home"]})
    h["steps"], h["cursor"], h["edit"] = steps, k, None
    _write_history(draft, h)
    for _ in range(e["applied"]):
        redo(draft)
    shutil.rmtree(draft / HISTORY_DIR / EDIT_DIR, ignore_errors=True)
    return e
