"""V-C2: independent re-derivation of the ef###.bytes resource-table walker.

Written FROM SCRATCH off a fresh disassembly of fn 0xd390..0xd4ef in
FF9SpecialEffectPlugin.dll (x64).  Deliberately does NOT import ef_container.py.

Two grammars are tested:
  A = claim C2 exactly as STATED  (no conditional extra field)
  B = what the disassembly actually does (extra u16 when id==2 and info!=0)

No game bytes are written; only counts/offsets are printed.
"""
import glob, os, struct, sys, collections

SCRATCH = r"C:/gd/SCRATCH/summon-format"


def s16(b, o):
    return struct.unpack_from("<h", b, o)[0]


def s8(b, o):
    return struct.unpack_from("<b", b, o)[0]


def walk(blob, extra_rule):
    """extra_rule: None (grammar A) or a callable(id, info)->bool (grammar B variants)."""
    p = 0
    n_chunks = s16(blob, p); p += 2
    cursor = 0x800
    chunks = []
    for ci in range(n_chunks):
        if p + 4 > len(blob):
            raise ValueError("chunk hdr past EOF")
        chunk_idx = s16(blob, p)
        n_res = s16(blob, p + 2)
        p += 4
        res = []
        for ri in range(n_res):
            if p + 4 > len(blob):
                raise ValueError("res hdr past EOF")
            rid = s8(blob, p)
            info = blob[p + 1]
            size = s16(blob, p + 2)
            p += 4
            cursor += size << 11
            ex = None
            if extra_rule is not None and extra_rule(rid, info, chunk_idx):
                ex = s16(blob, p)
                p += 2
                cursor += ex << 11
            res.append((rid, info, size, ex))
        chunks.append((chunk_idx, res))
    return n_chunks, chunks, cursor, p


NATIVE = lambda rid, info, cidx: rid == 2 and info != 0
CSHARP = lambda rid, info, cidx: rid == 2 and cidx == 0

def main():
    files = sorted(glob.glob(os.path.join(SCRATCH, "ef*.bytes")))
    print("corpus files:", len(files))
    results = {}
    for label, rule in (("A_as_stated", None), ("B_native", NATIVE), ("C_csharp", CSHARP)):
        ok = bad = err = 0
        firstbad = []
        for f in files:
            blob = open(f, "rb").read()
            try:
                nc, ch, cur, tend = walk(blob, rule)
            except Exception as e:
                err += 1
                if len(firstbad) < 5:
                    firstbad.append((os.path.basename(f), "ERR " + str(e)))
                continue
            if cur == len(blob):
                ok += 1
            else:
                bad += 1
                if len(firstbad) < 5:
                    firstbad.append((os.path.basename(f), f"cursor={cur:#x} len={len(blob):#x} d={cur-len(blob)}"))
        results[label] = (ok, bad, err)
        print(f"{label:12s} exact={ok:4d} mismatch={bad:4d} error={err:4d}  e.g. {firstbad[:3]}")

    # structural census under the native rule
    pair = collections.Counter()
    idc = collections.Counter()
    nchunk = collections.Counter()
    tab_end_max = 0
    extra_vals = collections.Counter()
    for f in files:
        blob = open(f, "rb").read()
        nc, ch, cur, tend = walk(blob, NATIVE)
        nchunk[nc] += 1
        tab_end_max = max(tab_end_max, tend)
        for cidx, res in ch:
            for rid, info, size, ex in res:
                idc[rid] += 1
                if rid == 2:
                    pair[(cidx == 0, info != 0)] += 1
                    if ex is not None:
                        extra_vals[ex] += 1
    print("\nchunkCount histogram:", dict(sorted(nchunk.items())))
    print("resource id histogram:", dict(sorted(idc.items())))
    print("id2 (chunkIndex==0, info!=0) census:", dict(pair))
    print("extra-u16 value histogram (top):", extra_vals.most_common(8))
    print("max table end offset:", hex(tab_end_max), " (< 0x400 sequence start?)",
          tab_end_max < 0x400)

    # does any file have a resource with negative/zero size, or id>9?
    odd = []
    for f in files:
        blob = open(f, "rb").read()
        nc, ch, cur, tend = walk(blob, NATIVE)
        for cidx, res in ch:
            for rid, info, size, ex in res:
                if size <= 0 or rid < 0 or rid > 9:
                    odd.append((os.path.basename(f), rid, info, size))
    print("\nodd resources (size<=0 or id outside 0..9):", odd[:20], "count", len(odd))


if __name__ == "__main__":
    main()
