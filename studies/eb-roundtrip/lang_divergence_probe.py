"""Rung 1 probe 3: characterize the per-language BYTECODE divergence.

The lang-identical law is false corpus-wide -- quantify it at EVT level and look at
WHAT diverges:
  - per EVT: which langs diverge from us (masked name region [0x04..0x80))?
  - equal-length divergences: decode the instruction containing each diff offset --
    is it a Wait operand (jp text pacing), a txid, something else?
  - unequal-length divergences: how many EVTs, which langs?

Run from the repo root:  py studies/eb-roundtrip/lang_divergence_probe.py
"""
from __future__ import annotations

import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "ff9mapkit"))

from envelope_census import collect_binaries                     # noqa: E402
from ff9mapkit.eb.model import EbScript                          # noqa: E402
from ff9mapkit.eb import disasm                                  # noqa: E402

NAME_LO, NAME_HI = 0x04, 0x80


def masked(d: bytes) -> bytes:
    return d[:NAME_LO] + d[NAME_HI:]


def instr_at(eb: EbScript, off: int):
    """(entry_idx, tag, mnemonic, operands, byte_index_in_instr) of the instruction containing `off`."""
    for e in eb.entries:
        if e.empty or not (e.abs_start <= off < e.abs_end):
            continue
        for f in e.funcs:
            if not (f.abs_start <= off < f.abs_end):
                continue
            try:
                for ins in disasm.iter_code(eb.data, f.abs_start, f.abs_end):
                    if ins.off <= off < ins.end:
                        return (e.index, f.tag, ins.name, tuple(ins.args), off - ins.off)
            except Exception:                                    # noqa: BLE001
                return (e.index, f.tag, "?decode-fail", (), None)
        return (e.index, None, "?in-entry-but-no-func", (), None)
    return (None, None, "?not-in-any-entry", (), None)


def main():
    bins = collect_binaries()
    evt_equal = 0
    evt_name_only = 0
    diverge_langs = Counter()               # lang -> count of EVTs diverging (equal or not)
    uneq_evts = []
    eq_diff_evts = []
    for evt, per_lang in sorted(bins.items()):
        base = per_lang.get("us")
        if base is None or len(per_lang) < 2:
            continue
        bad_eq, bad_uneq = [], []
        for lang, d in per_lang.items():
            if lang == "us":
                continue
            if len(d) != len(base):
                bad_uneq.append(lang)
            elif masked(d) != masked(base):
                bad_eq.append(lang)
        for lg in bad_eq + bad_uneq:
            diverge_langs[lg] += 1
        if not bad_eq and not bad_uneq:
            evt_name_only += 1
        if bad_uneq:
            uneq_evts.append((evt, sorted(bad_uneq)))
        elif bad_eq:
            eq_diff_evts.append((evt, sorted(bad_eq)))

    print(f"EVTs identical across langs outside the name region: {evt_name_only}")
    print(f"EVTs with EQUAL-length bytecode divergence: {len(eq_diff_evts)}")
    print(f"EVTs with UNEQUAL-length divergence: {len(uneq_evts)}")
    print(f"divergence count by lang: {dict(diverge_langs.most_common())}")
    lang_sets = Counter(tuple(l) for _, l in uneq_evts)
    print(f"unequal-length lang sets: {lang_sets.most_common(8)}")

    # -- decode a sample of equal-length diffs --
    print("\n== equal-length diff sites (sample) ==")
    site_ops = Counter()
    shown = 0
    for evt, langs in eq_diff_evts:
        per_lang = bins[evt]
        base = per_lang["us"]
        eb = EbScript.from_bytes(base)
        d = per_lang[langs[0]]
        diffs = [i for i in range(len(d)) if d[i] != base[i] and i >= NAME_HI]
        # group consecutive offsets into runs
        runs = []
        for i in diffs:
            if runs and i == runs[-1][1]:
                runs[-1][1] = i + 1
            else:
                runs.append([i, i + 1])
        for lo, hi in runs[:2]:
            loc = instr_at(eb, lo)
            site_ops[str(loc[2])] += 1
            if shown < 12:
                print(f"  {evt} [{langs[0]}] @{lo}..{hi}: us={base[lo:hi].hex()} "
                      f"{langs[0]}={d[lo:hi].hex()}  in entry {loc[0]} tag {loc[1]} op {loc[2]} args {loc[3]}")
                shown += 1
    print(f"\n  diff-site op histogram: {site_ops.most_common(15)}")


if __name__ == "__main__":
    main()
