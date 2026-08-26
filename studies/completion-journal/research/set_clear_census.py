"""set_clear_census.py -- ground-truth scan for PLAN.md's "94 bits explicitly cleared / 85
genuine set-then-clear toggles" claim (T4 blocker: "A monotone 'collected' latch is WRONG for
~85 bits").

For every real field's event script, walk every GLOB story-bit assign (``kind=='assign'``,
``source==0``, ``vtype in (0,1)``, literal ``value in (0,1)``) via ``FieldFlow``/``FuncFlow``
(``ff9mapkit.eb.cfg``) -- the same instrument ``research/dominance_census.py`` and
``studies/completion-journal/research/treasure_join.py`` use. For every bit index with BOTH a
set-to-1 site and a set-to-0 site anywhere in the 818-field corpus, classify the clear(s):

  init-zeroing   every clear is explained by a same-(field,entry,func) set of the SAME bit in a
                 Main_Init (tag==0) function, with the clear byte-offset BEFORE the set's --
                 i.e. "reset a scratch/derived bit, then immediately recompute it" within one
                 execution. This never leaves an observable false-then-cleared state in a save;
                 it is not a player-visible un-collect.
  genuine        at least one clear site is NOT explained that way: it sits in a non-Main_Init
                 function (an interaction/cutscene handler), or in a field/function that carries
                 no matching set for the same bit, or it follows the set later in the SAME
                 Main_Init execution (set-then-clear, not clear-then-set). This is a real
                 mid-game revoke a monotone latch would misrender.

Also flags whether each toggled bit falls in the engine's Treasure-Hunter-scored byte ranges
(896-960, 966-975 at 1 pt/bit; 182-186 at 2 pt/bit -- ``Global/Event/EventState.cs:62-70``,
verified this same way by ``treasure_join.py``).

Run from ``ff9mapkit/`` (so the local package shadows any editable install):

    py ../studies/completion-journal/research/set_clear_census.py

Writes ``set_clear_census.json`` next to this file (gitignored -- derived from the user's own
install, regenerable). Read-only: no deploy, no game-folder write, no git.
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
for p in (os.path.join(_REPO, "ff9mapkit"), _REPO):
    if p not in sys.path:
        sys.path.insert(0, p)

from ff9mapkit.extract import EventBundle, ID_TO_EVT            # noqa: E402
from ff9mapkit.eb import EbScript                                # noqa: E402
from ff9mapkit.eb.cfg import FieldFlow                           # noqa: E402

# Treasure-Hunter scoring, EventState.cs:65-70 (same ranges treasure_join.py verified):
# bytes 896-960 & 966-975 at 1 pt/bit, bytes 182-186 at 2 pt/bit.
_TH_SINGLE = set(range(896 * 8, 961 * 8)) | set(range(966 * 8, 976 * 8))
_TH_DOUBLE = set(range(182 * 8, 187 * 8))

_MAIN_INIT_TAG = 0


def _load_names() -> dict[int, str]:
    names: dict[int, str] = {}
    path = os.path.join(_REPO, "reference", "field-manifest.tsv")
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                parts = line.rstrip("\n").split("\t")
                if len(parts) < 3:
                    continue
                try:
                    fid = int(parts[1])
                except ValueError:
                    continue
                names.setdefault(fid, parts[2])
    except OSError:
        pass
    return names


def _th_class(bit: int) -> int:
    if bit in _TH_DOUBLE:
        return 2
    if bit in _TH_SINGLE:
        return 1
    return 0


def main() -> int:
    bundle = EventBundle()
    names = _load_names()
    stats: dict = defaultdict(int)

    # bit -> list of site dicts (one per write instruction)
    sets_by_bit: dict[int, list] = defaultdict(list)
    clears_by_bit: dict[int, list] = defaultdict(list)

    for fid in sorted(ID_TO_EVT):
        try:
            data = bundle.eb_for_id(fid)
            if not data:
                continue
            eb = EbScript.from_bytes(data)
        except Exception:
            stats["fields_unreadable"] += 1
            continue
        stats["fields_scanned"] += 1
        try:
            ff = FieldFlow.build(eb)
        except Exception:
            stats["fields_flow_failed"] += 1
            continue

        for key, fl in ff.flows.items():
            ei, fi = key
            ftag = eb.entries[ei].funcs[fi].tag
            for st, blk in fl.iter_sets(eb.data):
                if st.kind != "assign" or st.source != 0 or st.vtype not in (0, 1):
                    continue
                if st.value not in (0, 1):
                    continue
                site = {
                    "field": fid, "entry": ei, "fi": fi, "tag": ftag, "off": st.off,
                    "block": blk,
                }
                if st.value == 1:
                    sets_by_bit[st.index].append(site)
                    stats["set_sites"] += 1
                else:
                    clears_by_bit[st.index].append(site)
                    stats["clear_sites"] += 1

    stats["distinct_bits_set"] = len(sets_by_bit)
    stats["distinct_bits_cleared"] = len(clears_by_bit)

    toggled_bits = sorted(b for b in clears_by_bit if b in sets_by_bit)
    stats["distinct_bits_set_and_cleared"] = len(toggled_bits)

    per_bit: list = []
    genuine_bits: list = []
    init_zero_bits: list = []

    for b in toggled_bits:
        set_sites = sets_by_bit[b]
        clear_sites = clears_by_bit[b]
        # index same-function sets for quick lookup: (field, entry, fi) -> [set sites]
        set_by_func: dict = defaultdict(list)
        for s in set_sites:
            set_by_func[(s["field"], s["entry"], s["fi"])].append(s)

        explained: list = []      # clear sites the reset-then-recompute pattern explains
        unexplained: list = []    # clear sites that are a genuine revoke signal
        for c in clear_sites:
            fk = (c["field"], c["entry"], c["fi"])
            same_func_sets = set_by_func.get(fk, [])
            match = c["tag"] == _MAIN_INIT_TAG and any(
                s["off"] > c["off"] for s in same_func_sets)
            (explained if match else unexplained).append(c)

        cls = "init-zeroing" if not unexplained else "genuine"
        fields = sorted({s["field"] for s in set_sites} | {c["field"] for c in clear_sites})
        entry = {
            "bit": b,
            "class": cls,
            "th_class": _th_class(b),
            "n_set_sites": len(set_sites),
            "n_clear_sites": len(clear_sites),
            "n_clear_explained": len(explained),
            "n_clear_unexplained": len(unexplained),
            "fields": fields,
            "field_names": [names.get(f, "?") for f in fields],
            "set_sites": set_sites,
            "clear_sites": clear_sites,
        }
        per_bit.append(entry)
        (genuine_bits if cls == "genuine" else init_zero_bits).append(b)

    genuine_bits.sort()
    init_zero_bits.sort()

    # contiguous bands over the genuine list
    bands: list = []
    for b in genuine_bits:
        if bands and b == bands[-1][1] + 1:
            bands[-1][1] = b
        else:
            bands.append([b, b])
    band_rows = []
    for lo, hi in bands:
        fields_in_band = sorted({f for pb in per_bit if pb["class"] == "genuine"
                                  and lo <= pb["bit"] <= hi for f in pb["fields"]})
        band_rows.append({
            "lo": lo, "hi": hi, "width": hi - lo + 1,
            "fields": fields_in_band,
            "field_names": sorted({names.get(f, "?") for f in fields_in_band}),
        })

    genuine_th = [b for b in genuine_bits if _th_class(b)]

    out = {
        "generator": "studies/completion-journal/research/set_clear_census.py",
        "engine_truth": {
            "th_bytes_1pt": "896-960, 966-975",
            "th_bytes_2pt": "182-186",
        },
        "stats": dict(sorted(stats.items())),
        "summary": {
            "bits_cleared_total": len(clears_by_bit),
            "bits_set_and_cleared": len(toggled_bits),
            "genuine_toggle_bits": len(genuine_bits),
            "init_zeroing_bits": len(init_zero_bits),
            "genuine_bands": len(band_rows),
            "genuine_bits_in_treasure_hunter_range": len(genuine_th),
        },
        "genuine_toggle_bits": genuine_bits,
        "genuine_bands": band_rows,
        "init_zeroing_bits": init_zero_bits,
        "genuine_bits_in_th_range": genuine_th,
        "per_bit": per_bit,
    }
    dest = os.path.join(_HERE, "set_clear_census.json")
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, sort_keys=False)

    print(json.dumps({"stats": out["stats"], "summary": out["summary"],
                      "genuine_bands": out["genuine_bands"]}, indent=2))
    print(f"wrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
