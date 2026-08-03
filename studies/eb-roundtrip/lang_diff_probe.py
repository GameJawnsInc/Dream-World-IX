"""Rung 1 follow-up probes.

A. Per-language diff geography: for each EVT, diff every lang against us byte-by-byte.
   Where do differences live? (max diff offset; any diff at/after 0x80 = real bytecode
   divergence, contradicting the lang-identical law.) Also: length mismatches.
B. Empty-slot `off` convention: what does a parked off point at? (prior non-empty
   entry's end? next entry's start? something else?)
C. Name region: does [0x04..0x2C) + [0x2C..0x80) behave as ONE 124-byte text field?
   (first NUL position; bytes after the NUL constant or garbage?)

Run from the repo root:  py studies/eb-roundtrip/lang_diff_probe.py
"""
from __future__ import annotations

import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ff9mapkit"))

from envelope_census import collect_binaries                     # noqa: E402
from ff9mapkit.eb.model import EbScript, ENTRY_TABLE_OFF        # noqa: E402


def main():
    bins = collect_binaries()

    # -- A. diff geography --
    len_mismatch = []
    diff_past_name = []                     # (evt, lang, first diff offset >= 0x80)
    max_diff_off = Counter()                # histogram of max diff offset (bucketed)
    for evt, per_lang in sorted(bins.items()):
        base = per_lang.get("us")
        if base is None:
            continue
        for lang, d in per_lang.items():
            if lang == "us":
                continue
            if len(d) != len(base):
                len_mismatch.append((evt, lang, len(base), len(d)))
                continue
            diffs = [i for i in range(len(d)) if d[i] != base[i]]
            if not diffs:
                continue
            hi = max(diffs)
            max_diff_off[min(hi, 0x80)] += 1          # bucket: anything < 0x80 vs exactly where
            past = [i for i in diffs if i >= 0x80]
            if past:
                diff_past_name.append((evt, lang, past[0], len(past)))

    print("== A. per-language diff geography (vs us) ==")
    print(f"  length mismatches: {len(len_mismatch)}")
    for row in len_mismatch[:10]:
        print(f"    {row}")
    print(f"  max-diff-offset buckets (0x80 bucket = any diff at/past 0x80): {sorted(max_diff_off.items())}")
    print(f"  pairs with diffs at/past 0x80: {len(diff_past_name)}")
    for row in diff_past_name[:15]:
        print(f"    {row}")

    # -- B. empty-slot off convention + C. name NUL structure --
    conv = Counter()
    nul_tail = Counter()                    # what fills the name region after the first 0x00
    for evt, per_lang in sorted(bins.items()):
        data = per_lang.get("us") or next(iter(per_lang.values()))
        try:
            eb = EbScript.from_bytes(data)
        except Exception:                                        # noqa: BLE001
            continue
        prev_end_rel = ENTRY_TABLE_OFF + eb.entry_count * 8 - ENTRY_TABLE_OFF  # rel table end
        last_end_rel = None
        for e in eb.entries:
            if not e.empty:
                last_end_rel = e.abs_end - ENTRY_TABLE_OFF
                continue
            # candidates the parked off might equal
            nxt = next((n for n in eb.entries[e.index + 1:] if not n.empty), None)
            if last_end_rel is not None and e.off == last_end_rel:
                conv["prev_nonempty_end"] += 1
            elif nxt is not None and e.off == nxt.off:
                conv["next_nonempty_off"] += 1
            elif e.off == len(data) - ENTRY_TABLE_OFF:
                conv["file_end"] += 1
            elif e.off == prev_end_rel:
                conv["table_end"] += 1
            else:
                conv[f"other({e.off})"] += 1
        name = data[4:0x80]
        z = name.find(b"\x00")
        tail = name[z:] if z >= 0 else b""
        nul_tail["all_zero" if set(tail) <= {0} else "nonzero_tail"] += 1

    print("\n== B. empty-slot off convention ==")
    for k, n in conv.most_common(12):
        print(f"  {k}: {n}")

    print("\n== C. name region [0x04..0x80) after first NUL ==")
    print(f"  {dict(nul_tail)}")


if __name__ == "__main__":
    main()
