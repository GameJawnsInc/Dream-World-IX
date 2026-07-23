"""C10 verification step E: DISCRIMINATING POWER of the 0-violation corpus result.

A 0-failure test is worthless if almost any mapping would also score 0. This measures
how many violations ALTERNATIVE index mappings produce, plus the tightness of the
used-N set vs the live-program set per chunk.
"""
import glob
import os
import random
from collections import Counter

from v_c10_corpus import walk, programs, sequence, SCRATCH


def collect():
    rows = []          # (file, chunk_ordinal, N)
    chunk_live = {}    # (file, ordinal) -> set of live program indices
    for path in sorted(glob.glob(os.path.join(SCRATCH, "ef*.bytes"))):
        name = os.path.basename(path)[:5]
        data = open(path, "rb").read()
        chunks, cursor, _ = walk(data)
        pinfo = [programs(data, ch) for ch in chunks]
        for i, pi in enumerate(pinfo):
            if pi and not pi["bad"]:
                chunk_live[(name, i)] = {k for k, v in enumerate(pi["progs"]) if v}
        cur = 0
        for c, a1, a2, off in sequence(data):
            if c == 0x05:
                cur = a1
            elif c >= 0x80:
                rows.append((name, cur, c - 0x80))
    return rows, chunk_live


def fails(rows, chunk_live, fn):
    n = 0
    for name, ordi, N in rows:
        live = chunk_live.get((name, ordi))
        if live is None or fn(N) not in live:
            n += 1
    return n


rows, chunk_live = collect()
print(f"0x80+N opcodes: {len(rows)}  (N>0: {sum(1 for r in rows if r[2])})")
print(f"chunks with a program table: {len(chunk_live)}")
print(f"identity      N -> N        failures = {fails(rows, chunk_live, lambda N: N)}")
print(f"shift +1      N -> (N+1)%16 failures = {fails(rows, chunk_live, lambda N: (N+1) % 16)}")
print(f"shift -1      N -> (N-1)%16 failures = {fails(rows, chunk_live, lambda N: (N-1) % 16)}")
print(f"reverse       N -> 15-N     failures = {fails(rows, chunk_live, lambda N: 15-N)}")
print(f"collapse      N -> 0        failures = {fails(rows, chunk_live, lambda N: 0)}")
random.seed(1)
worst = []
for t in range(200):
    perm = list(range(16))
    random.shuffle(perm)
    worst.append(fails(rows, chunk_live, lambda N, p=perm: p[N]))
print(f"random permutations (n=200): min={min(worst)} median={sorted(worst)[100]} max={max(worst)}")
print(f"  permutations scoring 0: {sum(1 for w in worst if w == 0)}")

# tightness: per chunk, is used-N set == live set?
used = {}
for name, ordi, N in rows:
    used.setdefault((name, ordi), set()).add(N)
eq = sub = other = 0
for k, u in used.items():
    live = chunk_live.get(k, set())
    if u == live:
        eq += 1
    elif u < live:
        sub += 1
    else:
        other += 1
print(f"chunks referenced by 0x80+N: {len(used)}  used==live {eq}  used<live {sub}  neither {other}")
sizes = Counter(len(v) for v in chunk_live.values())
print(f"live-set size histogram: {dict(sorted(sizes.items()))}")
