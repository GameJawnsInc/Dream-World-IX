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
(:func:`stale`: source files that changed since the copy -- another session deployed). Promoting a draft into the
live folder is the editor's later rung (C4); this module never writes the install.

A DRAFT HOLDS DISC 1's EDITS ONLY. The verbs' disc-4 mirror (``discmirror.auto_mirror``) compares each cell's stock
ground across discs, which needs the install's bundles; a draft's root has none, so the mirror logs NOT RUN there,
exactly as it does for any absolute ``--mod-folder`` outside the install. Its Disc4 tree is the source's as copied,
so a promoted draft must be mirrored then (C4).
"""
from __future__ import annotations

import hashlib
import json
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
