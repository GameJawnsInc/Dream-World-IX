r"""TIER W rung 1 -- THE READ-OUT.  **Study shim over the promoted kit module.**

    py summon_camera.py read 227            # the human read-out + the merged timeline
    py summon_camera.py roundtrip           # the W1b gate over the whole corpus
    py summon_camera.py census              # the W1d corpus census
    py summon_camera.py dump 227            # decoded rows -> SCRATCH (never the repo)

WHAT THIS FILE IS NOW
---------------------
The reader itself was PROMOTED into the kit as :mod:`ff9mapkit.summons.camera` -- the extractor
(``walk_camera_ops`` + ``id2_directory`` + ``extract_shots``), the adapter into ``camera_codec``, the
read-out and ``merged_timeline``.  That is everything a user of the shipped ``summon-reskin`` /
``summon-rescore`` verbs needs, and it is unchanged by the move: W1's three corrections (the id-2
extra-sector base, the frame word's ``0xE000`` marks, ``0x23`` being a camera op) live there now.

This file is the STUDY's view of that module.  It re-exports it under the study's own name and adds
back the four things that are deliberately study-only.

``sys.modules[__name__] = _kit`` makes ``import summon_camera as W`` yield **the kit module object
itself**, not a copy.  That is the point:

* the underscored names (``_SHOT_LETTERS``, ``_machine_slot``, ``_REPO``) resolve, which a
  ``from ... import *`` re-export could never carry;
* ``monkeypatch.setattr(W, "_load", ...)`` mutates the object the kit code actually reads, so the
  study tests keep testing something rather than patching a shadow copy.

Every function defined below therefore reaches back through ``_kit.`` for anything a caller could
patch.  A bare global here would resolve in THIS file's namespace, which no test can see.

WHAT IS ADDED BACK HERE, AND WHY IT DID NOT GO
-----------------------------------------------
1. **The SCRATCH corpus** (``SCRATCH_CORPUS`` / ``SCRATCH_OUT`` / ``corpus_paths`` / ``_load``): a
   372-file extraction of the user's own install, on this machine only.  The kit reads ONE effect
   from the user's install through ``rescore.read_stock_effect``; a corpus is a dev luxury.
2. **The census** (``CensusRow`` / ``census_one`` / ``census`` / ``census_summary``): a survey of that
   corpus.  Evidence for the study record, not a verb anybody ships.
3. **The CSV dump** (``DUMP_FIELDS`` / ``dump_rows`` / ``dump_shots``): decoded STOCK data.  It exists
   to be read once and thrown away, and ``dump_shots`` refuses to write it under the repo.
4. **R3's phase recovery** (``recover_machines`` / ``_hle_ops``): it reaches into tier-r
   (``summon_inspect`` + ``tier_r_disasm`` + ``tier_r_annot`` + a 165 KB ``hle_ops.json``) -- 4,654
   lines and a data file -- to add ONE advisory column, the reframe budget.  ``merged_timeline`` and
   ``read_out`` already take ``machines`` as an optional argument defaulting to none, and the CLI
   already shipped ``--no-phases`` as a supported mode, so the kit takes the degraded state as its
   normal one and never carries a MIPS disassembler to get a column back.

THE BOOTSTRAP IS LOAD-BEARING (do not reorder)
-----------------------------------------------
The three ``sys.path`` inserts must run BEFORE the kit import.  ``<repo>/ff9mapkit`` first-on-path is
what makes the LOCAL package shadow any editable install; ``thomas-swap/disasm`` and ``tier-r`` are
what every sibling study module (``retime``, ``w_survey``, the gate runners, the tests) relies on
this import to have set up -- several of them import ``ef_container`` on the strength of it.

PROVENANCE
----------
Unchanged: the corpus is extracted from the user's own install at ``C:\gd\SCRATCH\summon-format`` and
decoded dumps go only under ``C:\gd\SCRATCH\summon-format\camera-w1``.  This file, its tests and the
report contain **no stock bytes** -- only offsets, counts, sizes and frame numbers.
"""
from __future__ import annotations

import collections
import csv
import glob
import os
import sys
from dataclasses import dataclass
from typing import Optional, Sequence, Tuple

_HERE = os.path.dirname(os.path.abspath(__file__))
_STUDY = os.path.dirname(_HERE)                                  # studies/custom-summons
_REPO = os.path.dirname(os.path.dirname(_STUDY))                 # <repo>
sys.path.insert(0, os.path.join(_STUDY, "thomas-swap", "disasm"))
sys.path.insert(0, os.path.join(_STUDY, "tier-r"))
sys.path.insert(0, os.path.join(_REPO, "ff9mapkit"))

from ff9mapkit.summons import camera as _kit                     # noqa: E402

#: THE ALIAS.  Every later ``import summon_camera`` -- and this module's own name -- now resolves to
#: the kit module object.  Names are set ON that object below, never left in this file's globals.
sys.modules[__name__] = _kit

#: same env override tier-r uses, so a run without the extraction skips instead of failing
SCRATCH_CORPUS = os.environ.get("FF9_SUMMON_SCRATCH", r"C:\gd\SCRATCH\summon-format")
SCRATCH_OUT = os.path.join(SCRATCH_CORPUS, "camera-w1")

_kit.SCRATCH_CORPUS = SCRATCH_CORPUS
_kit.SCRATCH_OUT = SCRATCH_OUT
_kit._HERE = _HERE
_kit._STUDY = _STUDY
#: the repo root, re-pinned from THIS file's location.  The kit's own provenance guard is
#: ``export.assert_local_only`` (a ``.git``-ancestor search that needs no such constant, and is
#: correct in an installed wheel where counting three directories up is arbitrary); the study keeps
#: the NAME because ``dump_shots`` and the gate runners cite it directly.
_kit._REPO = _REPO


# ============================================================ (A) R3's phase recovery (study-only)
def recover_machines(blob: bytes, source: str):
    """R3's state machines for this container, or () if R3's inspector is unavailable/defeated."""
    try:
        import summon_inspect as S
    except Exception:                                             # pragma: no cover
        return ()
    out = []
    for rec in S.recover_container(blob, source, _kit._hle_ops()):
        if rec.machine is not None and rec.verdict == "clean":
            out.append(rec.machine)
    return tuple(out)


def _hle_ops() -> Optional[dict]:
    """tier-r's HLE op table, or None.  Cached ON THE KIT MODULE so the cache is shared with every
    caller that resolved this module through ``sys.modules``."""
    if getattr(_kit, "_OPS_CACHE", None) is None:
        try:
            import json
            with open(os.path.join(_STUDY, "tier-r", "hle_ops.json"), "r", encoding="utf-8") as fh:
                raw = json.load(fh)
            _kit._OPS_CACHE = {int(k): v for k, v in (raw.get("ops") or raw).items()}
        except Exception:                                         # pragma: no cover
            _kit._OPS_CACHE = {}
    return _kit._OPS_CACHE or None


_kit._OPS_CACHE = None
_kit.recover_machines = recover_machines
_kit._hle_ops = _hle_ops


# ============================================================ (B) the corpus (study-only)
def _load(effect, root: str = SCRATCH_CORPUS) -> Tuple[bytes, str]:
    path = effect if os.path.sep in str(effect) or str(effect).endswith(".bytes") else \
        os.path.join(root, "ef%03d.bytes" % int(effect))
    if not os.path.isfile(path):
        raise _kit.SummonCameraError("no such container: %s (extract the corpus first)" % path)
    with open(path, "rb") as fh:
        return fh.read(), os.path.splitext(os.path.basename(path))[0]


def corpus_paths(root: str = SCRATCH_CORPUS) -> list:
    return sorted(glob.glob(os.path.join(root, "ef*.bytes")))


_kit._load = _load
_kit.corpus_paths = corpus_paths


# ============================================================ (C) THE CORPUS CENSUS (study-only)
@dataclass
class CensusRow:
    source: str
    n_seq_ops: int
    n_camera_ops: int
    n_shots: int
    n_dynamic: int
    n_setup_none: int
    shot_sizes: Tuple[int, ...]
    keyframes: Tuple[int, ...]
    spans: Tuple[int, ...]
    n_sequences: Tuple[int, ...]
    roundtrip_ok: int
    roundtrip_bad: Tuple[str, ...]
    skipped: Tuple[str, ...]
    shot_shas: Tuple[str, ...]


def census_one(path: str) -> CensusRow:
    import hashlib
    source = os.path.splitext(os.path.basename(path))[0]
    with open(path, "rb") as fh:
        blob = fh.read()
    ex = _kit.extract_shots(blob, source)
    ok, bad, sizes, kfs, spans, nseq, shas = 0, [], [], [], [], [], []
    for s in ex.shots:
        good, out = s.roundtrip()
        if good:
            ok += 1
        else:
            bad.append("c%d idx%d: %d B in, %d B out" % (s.slot, s.index, s.size, len(out)))
        sizes.append(s.size)
        kfs.append(sum(len(_kit.keyframes(s.camera, i)) for i in range(len(s.camera["sequences"]))))
        spans.append(_kit.shot_span(s.camera))
        nseq.append(len(s.camera["sequences"]))
        shas.append(hashlib.sha256(s.block).hexdigest())
    return CensusRow(
        source=source, n_seq_ops=ex.walk.n_ops, n_camera_ops=len(ex.walk.ops),
        n_shots=len(ex.shots), n_dynamic=ex.dynamic,
        n_setup_none=sum(1 for o, w in ex.skipped if w == "none"),
        shot_sizes=tuple(sizes), keyframes=tuple(kfs), spans=tuple(spans),
        n_sequences=tuple(nseq), roundtrip_ok=ok, roundtrip_bad=tuple(bad),
        skipped=tuple("c%d %s idx%d: %s" % (o.chunk_slot, o.kind, o.arg1, w)
                      for o, w in ex.skipped if w not in ("none", "dynamic")),
        shot_shas=tuple(shas))


def census(root: str = SCRATCH_CORPUS, limit: Optional[int] = None):
    paths = _kit.corpus_paths(root)
    if limit:
        paths = paths[:limit]
    return [_kit.census_one(p) for p in paths]


def census_summary(rows: Sequence[CensusRow]) -> dict:
    sizes = [n for r in rows for n in r.shot_sizes]
    kfs = [n for r in rows for n in r.keyframes]
    spans = [n for r in rows for n in r.spans]
    sha = collections.defaultdict(list)
    for r in rows:
        for i, h in enumerate(r.shot_shas):
            sha[h].append(r.source)
    dup = {h: v for h, v in sha.items() if len(v) > 1}
    return {
        "effects": len(rows),
        "effects_with_camera_ops": sum(1 for r in rows if r.n_camera_ops),
        "effects_with_shots": sum(1 for r in rows if r.n_shots),
        "camera_ops": sum(r.n_camera_ops for r in rows),
        "shots": sum(r.n_shots for r in rows),
        "dynamic": sum(r.n_dynamic for r in rows),
        "setup_none": sum(r.n_setup_none for r in rows),
        "roundtrip_ok": sum(r.roundtrip_ok for r in rows),
        "roundtrip_bad": [b for r in rows for b in r.roundtrip_bad],
        "skipped": [s for r in rows for s in r.skipped],
        "shots_per_effect": dict(sorted(collections.Counter(r.n_shots for r in rows).items())),
        "sequences_per_shot": dict(sorted(collections.Counter(
            n for r in rows for n in r.n_sequences).items())),
        "bytes_total": sum(sizes),
        "size_min": min(sizes) if sizes else 0,
        "size_max": max(sizes) if sizes else 0,
        "size_mean": (sum(sizes) / len(sizes)) if sizes else 0,
        "kf_min": min(kfs) if kfs else 0,
        "kf_max": max(kfs) if kfs else 0,
        "kf_mean": (sum(kfs) / len(kfs)) if kfs else 0,
        "kf_total": sum(kfs),
        "span_min": min(spans) if spans else 0,
        "span_max": max(spans) if spans else 0,
        "span_mean": (sum(spans) / len(spans)) if spans else 0,
        "identical_groups": len(dup),
        "identical_refs": sum(len(v) for v in dup.values()),
        "identical_cross_effect": sum(1 for v in dup.values() if len(set(v)) > 1),
    }


_kit.CensusRow = CensusRow
_kit.census_one = census_one
_kit.census = census
_kit.census_summary = census_summary


# ============================================================ (D) dumps (SCRATCH only, study-only)
DUMP_FIELDS = ["effect", "shot", "op", "op_at", "chunk", "subfile", "file_lo", "size",
               "outer_flags", "sequence", "local_frame", "frame_marks", "abs_seq_tick",
               "code_flags", "cam_code", "cam_flags", "cam_pitch", "cam_orientation", "cam_roll",
               "cam_distance", "move_duration", "move_type", "tgt_code", "tgt_flags", "tgt_pitch",
               "tgt_orientation", "tgt_roll", "tgt_distance", "tmove_duration", "tmove_type",
               "focal_H", "focal_duration", "focal_flags"]


def dump_rows(blob: bytes, source: str) -> list:
    ex = _kit.extract_shots(blob, source)
    rows = []
    for i, s in enumerate(ex.shots):
        for si in range(len(s.camera["sequences"])):
            for k in _kit.keyframes(s.camera, si):
                r = {"effect": source, "shot": _kit._SHOT_LETTERS[i % 26], "op": s.op.kind,
                     "op_at": s.op.at, "chunk": s.slot, "subfile": s.index, "file_lo": s.lo,
                     "size": s.size, "outer_flags": s.camera["flags"], "sequence": si,
                     "local_frame": k.local_frame, "frame_marks": k.marks,
                     "abs_seq_tick": s.op.seq_tick + k.local_frame - 1, "code_flags": k.flags}
                p = k.pose("campos")
                if p:
                    r.update({"cam_" + a: p[b] for a, b in
                              (("code", "code"), ("flags", "flags"), ("pitch", "pitch"),
                               ("orientation", "orientation"), ("roll", "roll"),
                               ("distance", "distance"))})
                t = k.pose("tgtpos")
                if t:
                    r.update({"tgt_" + a: t[b] for a, b in
                              (("code", "code"), ("flags", "flags"), ("pitch", "pitch"),
                               ("orientation", "orientation"), ("roll", "roll"),
                               ("distance", "distance"))})
                mv = k.movement("cammove")
                if mv:
                    r.update(move_duration=mv["duration"], move_type=mv["type"])
                tm = k.movement("tgtmove")
                if tm:
                    r.update(tmove_duration=tm["duration"], tmove_type=tm["type"])
                f = k.focal()
                if f:
                    r.update(focal_H=f["distance"], focal_duration=f["duration"],
                             focal_flags=f["flags"])
                rows.append(r)
    return rows


def dump_shots(rows: Sequence[dict], out_path: str) -> int:
    """Write decoded rows to a CSV -- SCRATCH only.  Decoded stock data never enters the repo."""
    ap = os.path.abspath(out_path)
    repo = os.path.abspath(_kit._REPO)
    if os.path.commonpath([ap, repo]) == repo:
        raise _kit.SummonCameraError(
            "refusing to write decoded stock-derived data under the repo: %s" % ap)
    os.makedirs(os.path.dirname(ap), exist_ok=True)
    with open(ap, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=_kit.DUMP_FIELDS, restval="", extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows)


_kit.DUMP_FIELDS = DUMP_FIELDS
_kit.dump_rows = dump_rows
_kit.dump_shots = dump_shots


# ============================================================ CLI (study-only)
def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("verb", choices=("read", "roundtrip", "census", "dump", "timeline"))
    ap.add_argument("effect", nargs="?", default=227)
    ap.add_argument("--corpus-root", default=_kit.SCRATCH_CORPUS)
    ap.add_argument("--out", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--no-phases", action="store_true",
                    help="skip R3's state-machine recovery (faster; the timeline loses its phase rows)")
    a = ap.parse_args(argv)

    if a.verb in ("read", "timeline", "dump"):
        blob, src = _kit._load(a.effect, a.corpus_root)
        machines = () if a.no_phases else _kit.recover_machines(blob, src)
        if a.verb == "dump":
            out = a.out or os.path.join(_kit.SCRATCH_OUT, "%s_camera.csv" % src)
            n = _kit.dump_shots(_kit.dump_rows(blob, src), out)
            print("wrote %d keyframe rows -> %s" % (n, out))
            return 0
        if a.verb == "read":
            print("\n".join(_kit.read_out(blob, src, machines)))
        print("\n".join(_kit.timeline_lines(_kit.merged_timeline(blob, src, machines))))
        return 0

    rows = _kit.census(a.corpus_root, a.limit)
    s = _kit.census_summary(rows)
    if a.verb == "roundtrip":
        print("ROUND-TRIP over %d containers: %d/%d camera blocks byte-exact"
              % (s["effects"], s["roundtrip_ok"], s["shots"]))
        for b in s["roundtrip_bad"]:
            print("  FAIL " + b)
        for k in s["skipped"]:
            print("  skipped " + k)
        return 0 if s["roundtrip_ok"] == s["shots"] and not s["roundtrip_bad"] else 1
    for k, v in s.items():
        print("%-24s %s" % (k, v if not isinstance(v, list) else "%d entries" % len(v)))
    return 0


_kit.main = main

if __name__ == "__main__":                                        # pragma: no cover
    raise SystemExit(main())
