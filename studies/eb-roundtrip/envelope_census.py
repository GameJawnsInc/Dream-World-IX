"""Rung 1 of the eb-roundtrip arc: the FILE-ENVELOPE census.

Answers the grammar-deciding questions from studies/eb-roundtrip/PLAN.md over every
field event binary in the install, all languages:

  1. header [0x04..0x2C): constant across files, or varying? (distinct values)
  2. name block [0x2C..0x80): does it differ per language? per field?
  3. entry table: empty-slot off/loc/flags/pad conventions; physical order == table
     order?; entries contiguous (first at table end, no inter-entry gaps)?
  4. EOF slack after the last entry?
  5. func tables: fpos[0] == funcCount*4 and strictly ascending (i.e. derivable)?
  6. per-language bytecode identity: with the name block masked, are all langs of one
     EVT byte-identical?

Reads the install directly via the kit's extractor (one bundle load, one container
sweep). Read-only; writes nothing to the install.

Run from the repo root:  py studies/eb-roundtrip/envelope_census.py
"""
from __future__ import annotations

import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ff9mapkit"))

from ff9mapkit import extract                                    # noqa: E402
from ff9mapkit.eb.model import EbScript, ENTRY_TABLE_OFF, NAME_OFF, NAME_LEN  # noqa: E402

NAME_END = NAME_OFF + NAME_LEN                                   # 0x80


def collect_binaries():
    """{evt_name: {lang: bytes}} for every eventbinary/field/<lang>/*.eb.bytes in the bundle."""
    bundle = extract._events_bundle()
    if not bundle:
        sys.exit("no events bundle found -- is the FF9 install reachable?")
    env = extract._load_env(extract._streaming_assets() / bundle)
    out = defaultdict(dict)
    for k, obj in env.container.items():
        kl = k.lower()
        if "eventbinary/field/" not in kl or not kl.endswith(".eb.bytes"):
            continue
        parts = kl.split("eventbinary/field/")[1].split("/")
        lang, fname = parts[0], parts[-1]
        evt = fname[:-len(".eb.bytes")]
        out[evt][lang] = extract._raw_bytes(obj.read())
    return dict(out)


def census():
    bins = collect_binaries()
    langs = sorted({lg for d in bins.values() for lg in d})
    print(f"{len(bins)} EVT names, langs: {langs}, "
          f"{sum(len(d) for d in bins.values())} binaries")

    headers = Counter()                     # distinct header[4:0x2C] values
    byte2 = Counter()                       # raw[2] "unknown" u8
    name_per_field_differs = 0              # any lang pair differing in the name block
    name_langs_equal = 0                    # all langs share one name block
    bytecode_lang_mismatch = []             # EVTs whose masked bytes differ across langs
    empty_off = Counter()                   # empty-slot off conventions (relative to what?)
    empty_meta = Counter()                  # (loc, flags, pad) of empty slots
    nonempty_pad = Counter()                # pad of NON-empty slots
    order_violations = []                   # table order != physical order
    gap_files = []                          # inter-entry gaps or table-end gap
    eof_slack = Counter()                   # bytes after last entry end
    fpos_noncanon = []                      # fpos[0] != funcCount*4 or non-ascending
    overlap_files = []                      # entries overlapping
    entry_counts = Counter()

    for evt, per_lang in sorted(bins.items()):
        # -- per-language comparisons (name block + masked bytecode) --
        datas = list(per_lang.values())
        if len(datas) > 1:
            names = {d[NAME_OFF:NAME_END] for d in datas}
            if len(names) > 1:
                name_per_field_differs += 1
            else:
                name_langs_equal += 1
            masked = {d[:NAME_OFF] + d[NAME_END:] for d in datas}
            if len(masked) > 1:
                bytecode_lang_mismatch.append(evt)

        # -- structural walk on ONE representative (us if present) --
        data = per_lang.get("us") or datas[0]
        try:
            eb = EbScript.from_bytes(data)
        except Exception as e:                                   # noqa: BLE001
            print(f"  PARSE FAIL {evt}: {e}")
            continue
        headers[data[4:NAME_OFF]] += 1
        byte2[data[2]] += 1
        entry_counts[eb.entry_count] += 1

        table_end = ENTRY_TABLE_OFF + eb.entry_count * 8
        nonempty = [e for e in eb.entries if not e.empty]
        for e in eb.entries:
            slot = data[ENTRY_TABLE_OFF + e.index * 8: ENTRY_TABLE_OFF + (e.index + 1) * 8]
            pad = int.from_bytes(slot[6:8], "little")
            if e.empty:
                # off convention: record relative to prior non-empty entry's END and raw
                empty_off[("raw0" if e.off == 0 else "nonzero")] += 1
                empty_meta[(e.loc, e.flags, pad)] += 1
            else:
                nonempty_pad[(e.loc, e.flags, pad)] += 1

        # physical order + contiguity + overlap
        phys = sorted(nonempty, key=lambda e: e.abs_start)
        if [e.index for e in phys] != [e.index for e in nonempty]:
            order_violations.append(evt)
        pos = table_end
        gaps = []
        for e in phys:
            if e.abs_start > pos:
                gaps.append((pos, e.abs_start - pos, data[pos:e.abs_start]))
            elif e.abs_start < pos:
                overlap_files.append((evt, e.index, pos - e.abs_start))
            pos = max(pos, e.abs_end)
        if gaps:
            gap_files.append((evt, gaps))
        slack = len(data) - pos
        eof_slack[slack] += 1

        # func-table canonicality
        for e in nonempty:
            fp = [f.fpos for f in e.funcs]
            if not fp:
                continue
            if fp[0] != e.func_count * 4 or any(b <= a for a, b in zip(fp, fp[1:])):
                fpos_noncanon.append((evt, e.index, fp[:6]))

    print("\n== 1. header [0x04..0x2C) ==")
    for h, n in headers.most_common(5):
        print(f"  x{n}: {h.hex()}")
    print(f"  distinct header values: {len(headers)}")
    print(f"  raw[2] values: {dict(byte2)}")
    print(f"  entryCount distribution: {sorted(entry_counts.items())}")

    print("\n== 2. name block per language ==")
    print(f"  fields where langs DIFFER in the name block: {name_per_field_differs}")
    print(f"  fields where all langs share one name block: {name_langs_equal}")

    print("\n== 6. per-language bytecode identity (name masked) ==")
    print(f"  MISMATCHED EVTs: {len(bytecode_lang_mismatch)}")
    for evt in bytecode_lang_mismatch[:10]:
        print(f"    {evt}")

    print("\n== 3. entry table ==")
    print(f"  empty-slot off: {dict(empty_off)}")
    print(f"  empty-slot (loc, flags, pad): {empty_meta.most_common(5)}")
    print(f"  non-empty (loc, flags, pad) top: {nonempty_pad.most_common(5)}")
    print(f"  table-order != physical-order files: {len(order_violations)} {order_violations[:5]}")
    print(f"  overlapping entries: {len(overlap_files)} {overlap_files[:5]}")

    print("\n== 3b/4. gaps + EOF slack ==")
    print(f"  files with inter-entry/table-end gaps: {len(gap_files)}")
    for evt, gaps in gap_files[:8]:
        gd = ", ".join(f"@{o}+{n}b={b[:8].hex()}" for o, n, b in gaps)
        print(f"    {evt}: {gd}")
    print(f"  EOF slack distribution: {sorted(eof_slack.items())}")

    print("\n== 5. func tables ==")
    print(f"  non-canonical func tables: {len(fpos_noncanon)}")
    for row in fpos_noncanon[:10]:
        print(f"    {row}")


if __name__ == "__main__":
    census()
