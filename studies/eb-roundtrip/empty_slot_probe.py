"""Rung 1 probe 4: what do the non-derivable empty-slot `off` values point at?

Pick files whose empty slots park at a value that is NOT the previous entry's end and
print the full entry table + where that value would land.

Run from the repo root:  py studies/eb-roundtrip/empty_slot_probe.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ff9mapkit"))

from envelope_census import collect_binaries                     # noqa: E402
from ff9mapkit.eb.model import EbScript, ENTRY_TABLE_OFF        # noqa: E402


def main():
    bins = collect_binaries()
    shown = 0
    for evt, per_lang in sorted(bins.items()):
        data = per_lang.get("us") or next(iter(per_lang.values()))
        eb = EbScript.from_bytes(data)
        odd = []
        for e in eb.entries:
            if not e.empty:
                continue
            prev = next((p for p in reversed(eb.entries[:e.index]) if not p.empty), None)
            if prev is None or e.off != prev.abs_end - ENTRY_TABLE_OFF:
                odd.append(e)
        if not odd:
            continue
        print(f"\n{evt}: file len {len(data)}, {eb.entry_count} slots")
        offs = sorted({x.off for x in odd})
        for e in eb.entries:
            mark = " <-- ODD EMPTY" if any(o.index == e.index for o in odd) else ""
            kind = "EMPTY" if e.empty else f"sz={e.size} type={e.type} funcs={e.func_count}"
            print(f"  slot {e.index:2d}: off={e.off:5d} {kind}{mark}")
        for o in offs:
            landing = next((f"INSIDE entry {e.index} (start {e.abs_start - ENTRY_TABLE_OFF}, "
                            f"end {e.abs_end - ENTRY_TABLE_OFF})"
                            for e in eb.entries
                            if not e.empty and e.abs_start - ENTRY_TABLE_OFF <= o < e.abs_end - ENTRY_TABLE_OFF),
                           "no entry")
            starts = [e.index for e in eb.entries if not e.empty and e.abs_start - ENTRY_TABLE_OFF == o]
            ends = [e.index for e in eb.entries if not e.empty and e.abs_end - ENTRY_TABLE_OFF == o]
            print(f"  odd off {o}: lands {landing}; ==start of {starts}; ==end of {ends}; "
                  f"==file end {o == len(data) - ENTRY_TABLE_OFF}")
        shown += 1
        if shown >= 4:
            break


if __name__ == "__main__":
    main()
