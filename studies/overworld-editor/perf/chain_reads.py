"""Lane chain: the draft reads (world/draft.py) on the real folder (~2,000 world files) and the 5-step gold draft --
their wall, and three prototypes compared against the unpatched code IN THIS SCRIPT, with == on every answer.

    py studies/overworld-editor/perf/chain_reads.py [runs]

Reads, each `runs` times (default 5; min is the headline, three other lanes share the machine):
  read_meta, history, edits, removals, edited_blocks, stale, last_promote (the forest card's "draftinfo" worker
  runs edited_blocks + stale + last_promote; the bar's refresh runs read_meta + history on the GUI thread);
  _world_files on the install folder and on the draft; _cell_files over all_cells() (begin_step's whole-map
  snapshot list; commit_step lists it three times).
Prototypes (monkeypatch-free: separate functions here, compared by == against the module's own):
  P1 _world_files by os.scandir (one listing per directory, no Path.rglob/relative_to);
  P2 edits/removals/stale with the stat taken from the scandir entry (Windows fills it from the directory listing:
     no per-file stat call) -- identity checked file by file against os.stat, and on the answers;
  P3 _cell_files over many cells by one listing per r-directory instead of one glob per cell per disc;
  P4 edited_blocks with one manifest read and one walk (it reads the manifest twice and walks twice).
Writes only under OUT/work/reads.
"""
from __future__ import annotations

import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chain_common as CC                                             # noqa: E402

from ff9mapkit.world import draft as D                                # noqa: E402

DISCS, LEDGER = D.DISCS, D.LEDGER


# ---------------------------------------------------------------- P1: one scandir per directory
def wf_fast(folder: Path, *, with_stat=False):
    """D._world_files by os.scandir: same keys (relative posix), same Path values. ``with_stat``: also the entry's
    stat (on Windows, from the directory listing)."""
    folder = Path(folder)
    out, st = {}, {}
    root = str(folder)
    for d in DISCS:
        tree = folder / "FF9_Data" / "WorldMap" / f"Disc{d}"
        if not tree.is_dir():
            continue
        stack = [str(tree)]
        while stack:
            p = stack.pop()
            with os.scandir(p) as it:
                for e in it:
                    if e.is_dir(follow_symlinks=False):
                        stack.append(e.path)
                    elif ".bak-" not in e.name and e.is_file():
                        rel = os.path.relpath(e.path, root).replace("\\", "/")
                        out[rel] = Path(e.path)
                        if with_stat:
                            st[rel] = e.stat()
    return (out, st) if with_stat else out


# ---------------------------------------------------------------- P2: edits / removals / stale off the entry stat
def _same_st(p, s, rec):
    if s.st_size == rec[1] and s.st_mtime_ns == rec[-1]:
        return True
    return s.st_size == rec[1] and D._sha(p) == rec[0]


def edits_fast(draft):
    meta = D.read_meta(draft)
    if meta is None:
        return []
    man = meta["manifest"]
    files, st = wf_fast(Path(draft), with_stat=True)
    out = []
    for rel, p in files.items():
        if rel == LEDGER:
            continue
        if rel not in man:
            out.append(rel)
            continue
        rec = man[rel]
        s = st[rel]
        same = (s.st_size == rec[1] and s.st_mtime_ns == rec[3]) or (s.st_size == rec[1] and D._sha(p) == rec[0])
        if not same:
            out.append(rel)
    return sorted(out)


def stale_fast(draft):
    meta = D.read_meta(draft)
    if meta is None:
        return []
    man = meta["manifest"]
    files, st = wf_fast(Path(meta["source"]), with_stat=True)
    out = []
    for rel, p in files.items():
        if rel == LEDGER:
            continue
        if rel not in man:
            out.append(rel)
            continue
        rec, s = man[rel], st[rel]
        if not ((s.st_size == rec[1] and s.st_mtime_ns == rec[2]) or (s.st_size == rec[1] and D._sha(p) == rec[0])):
            out.append(rel)
    out += [rel for rel in man if rel not in files]
    return sorted(set(out))


# ---------------------------------------------------------------- P4: edited_blocks, one meta read and one walk
_BLK = re.compile(r"Disc(\d+)/[^/]+/r\d+/Block\[(\d+)\]\[(\d+)\]")


def edited_blocks_once(draft):
    meta = D.read_meta(draft)
    if meta is None:
        return []
    man = meta["manifest"]
    files, st = wf_fast(Path(draft), with_stat=True)
    rels = []
    for rel, p in files.items():
        if rel == LEDGER:
            continue
        rec = man.get(rel)
        if rec is None:
            rels.append(rel)
            continue
        s = st[rel]
        if not ((s.st_size == rec[1] and s.st_mtime_ns == rec[3]) or (s.st_size == rec[1] and D._sha(p) == rec[0])):
            rels.append(rel)
    rels += [rel for rel in man if rel != LEDGER and rel not in files]
    got = set()
    for rel in rels:
        m = _BLK.search(rel)
        if m:
            got.add((int(m.group(1)), int(m.group(2)), int(m.group(3))))
    return sorted(got)


# ---------------------------------------------------------------- P3: _cell_files by one listing per r-directory
def cell_files_fast(folder: Path, cells) -> dict:
    """D._cell_files: every file at ``cells`` on the DISCS trees, no backups, no .promoting stage."""
    folder = Path(folder)
    want = {}
    for bx, by in cells:
        want.setdefault(int(by), set()).add(int(bx))
    pat = re.compile(r"^Block\[(\d+)\]\[(\d+)\] ")
    out = {}
    root = str(folder)
    for d in DISCS:
        tree = folder / "FF9_Data" / "WorldMap" / f"Disc{d}"
        try:
            lods = [e for e in os.scandir(tree) if e.is_dir()]
        except OSError:
            continue
        for lod in lods:
            for by, xs in want.items():
                rdir = os.path.join(lod.path, f"r{by}")
                try:
                    it = os.scandir(rdir)
                except OSError:
                    continue
                with it:
                    for e in it:
                        m = pat.match(e.name)
                        if not m or int(m.group(2)) != by or int(m.group(1)) not in xs:
                            continue
                        if ".bak-" in e.name or e.name.endswith(".promoting") or not e.is_file():
                            continue
                        out[os.path.relpath(e.path, root).replace("\\", "/")] = Path(e.path)
    return out


def main(runs=5):
    draft_root = CC.fresh_copy("reads")
    draft = D.draft_path(CC.SOURCE, root=draft_root)
    assert D.read_meta(draft) is not None, draft
    out = {"t": time.strftime("%Y-%m-%d %H:%M:%S"), "draft": str(draft), "runs": runs,
           "files": {"source": len(D._world_files(CC.SOURCE)), "draft": len(D._world_files(draft))},
           "draft_json_bytes": (draft / D.DRAFT_FILE).stat().st_size,
           "history_json_bytes": (draft / D.HISTORY).stat().st_size,
           "ledger_bytes": (draft / D.LEDGER).stat().st_size}
    t = {}
    for name, fn in (("read_meta", lambda: D.read_meta(draft)), ("history", lambda: D.history(draft)),
                     ("recipe_rows", lambda: D.recipe_rows(draft)),
                     ("edits", lambda: D.edits(draft)), ("removals", lambda: D.removals(draft)),
                     ("edited_blocks", lambda: D.edited_blocks(draft)), ("stale", lambda: D.stale(draft)),
                     ("last_promote", lambda: D.last_promote(draft)),
                     ("promote_owed", lambda: D.promote_owed(draft)),
                     ("draftinfo (edited_blocks+stale+last_promote)",
                      lambda: ({(bx, by) for disc, bx, by in D.edited_blocks(draft) if disc == 1}, D.stale(draft),
                               D.last_promote(draft))),
                     ("_world_files(source)", lambda: D._world_files(CC.SOURCE)),
                     ("_world_files(draft)", lambda: D._world_files(draft)),
                     ("_cell_files(draft, all_cells)", lambda: D._cell_files(draft, D.all_cells())),
                     ("_cell_files(source, all_cells)", lambda: D._cell_files(CC.SOURCE, D.all_cells())),
                     ("P1 wf_fast(source)", lambda: wf_fast(CC.SOURCE)),
                     ("P1 wf_fast(draft)", lambda: wf_fast(draft)),
                     ("P2 edits_fast", lambda: edits_fast(draft)),
                     ("P2 stale_fast", lambda: stale_fast(draft)),
                     ("P4 edited_blocks_once", lambda: edited_blocks_once(draft)),
                     ("P4 draftinfo (once+P2 stale)",
                      lambda: ({(bx, by) for disc, bx, by in edited_blocks_once(draft) if disc == 1},
                               stale_fast(draft), D.last_promote(draft))),
                     ("P3 cell_files_fast(draft, all_cells)", lambda: cell_files_fast(draft, D.all_cells())),
                     ("P3 cell_files_fast(source, all_cells)", lambda: cell_files_fast(CC.SOURCE, D.all_cells()))):
        t[name], _ = CC.timeit(fn, n=runs)
        print(f"{name:48s} min {t[name]['min']:.4f}  median {t[name]['median']:.4f}")
    out["wall"] = t
    # identity of every prototype against the module's own answer, on the real folder and the real draft
    ident = {}
    ident["P1 source"] = wf_fast(CC.SOURCE) == D._world_files(CC.SOURCE)
    ident["P1 draft"] = wf_fast(draft) == D._world_files(draft)
    ident["P2 edits"] = edits_fast(draft) == D.edits(draft)
    ident["P2 stale"] = stale_fast(draft) == D.stale(draft)
    ident["P4 edited_blocks"] = edited_blocks_once(draft) == D.edited_blocks(draft)
    ident["P3 draft all_cells"] = cell_files_fast(draft, D.all_cells()) == D._cell_files(draft, D.all_cells())
    ident["P3 source all_cells"] = cell_files_fast(CC.SOURCE, D.all_cells()) == D._cell_files(CC.SOURCE,
                                                                                             D.all_cells())
    h = D.history(draft)
    for i, s in enumerate(h["steps"]):
        cells = [tuple(c) for c in s["cells"]]
        ident[f"P3 step {i} cells (draft)"] = cell_files_fast(draft, cells) == D._cell_files(draft, cells)
    # the entry stat against os.stat, file by file (P2's premise), on both folders
    for name, folder in (("source", CC.SOURCE), ("draft", draft)):
        files, st = wf_fast(folder, with_stat=True)
        bad = [rel for rel, p in files.items()
               if (lambda s: (s.st_size, s.st_mtime_ns))(p.stat()) != (st[rel].st_size, st[rel].st_mtime_ns)]
        ident[f"P2 entry stat == os.stat ({name}, {len(files)} files)"] = not bad
        if bad:
            ident[f"P2 bad ({name})"] = bad[:10]
    # P2 must also see an edit: touch one draft file's bytes (same size, new content) and compare again
    victim = sorted(D._world_files(draft))[5]
    p = draft / victim
    data = p.read_bytes()
    p.write_bytes(bytes([data[0] ^ 1]) + data[1:])
    ident["P2 edits after a same-size rewrite"] = edits_fast(draft) == D.edits(draft) and victim in D.edits(draft)
    ident["P4 after a same-size rewrite"] = edited_blocks_once(draft) == D.edited_blocks(draft)
    p.write_bytes(data)                                                 # (back, bytes; its mtime moved: hashed)
    ident["P2 edits after the restore"] = edits_fast(draft) == D.edits(draft)
    out["identity"] = ident
    for k, v in ident.items():
        print(f"identity {k}: {v}")
    CC.save("reads.json", out)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 5)
