"""C4 adversarial re-derivation -- independent container walk (no ef_container import)."""
import os, struct, glob, sys, collections

SCR = r"C:\gd\SCRATCH\summon-format"

def s16(b,o): return struct.unpack_from('<h', b, o)[0]
def u16(b,o): return struct.unpack_from('<H', b, o)[0]
def s8(b,o):  return struct.unpack_from('<b', b, o)[0]
def u32(b,o): return struct.unpack_from('<I', b, o)[0]

def walk(blob):
    """Mirror fn 0xd390 exactly. Returns (chunks, endpos)."""
    p = 0
    chunkCount = s16(blob, p); p += 2
    pos = 0x800
    chunks = []
    for ordinal in range(chunkCount):
        chunkIndexField = s16(blob, p)
        resourceCount   = s16(blob, p+2); p += 4
        res = []
        for j in range(resourceCount):
            rid  = s8(blob, p)
            info = s8(blob, p+1)
            n    = s16(blob, p+2) << 11
            p += 4
            off = pos
            pos += n
            extra = None
            if rid == 2 and info != 0:
                extra = s16(blob, p) << 11
                pos += extra; p += 2
            res.append(dict(id=rid, info=info, size=n, off=off, extra=extra))
        chunks.append(dict(ordinal=ordinal, idxField=chunkIndexField,
                           resources=res))
    return chunks, pos, p

def programs(blob, chunk):
    """id-3 payload -> list of 16 relocated program offsets (0 = absent). Mirrors 0xd390@0xd415."""
    r3 = [r for r in chunk['resources'] if r['id'] == 3]
    if not r3: return None
    r = r3[0]
    payload = r['off']
    psxBase = 0x801e7700 + (chunk['ordinal'] & 1) * 0x5000
    ptr = u32(blob, payload)
    headerRel = (ptr & 0x0fffffff) - (psxBase & 0x0fffffff)
    progs = []
    for k in range(16):
        v = u32(blob, payload + headerRel + 8 + 4*k)
        progs.append(0 if v == 0 else (v & 0x0fffffff) - (psxBase & 0x0fffffff))
    return dict(headerRel=headerRel, progs=progs, payload=payload, size=r['size'])

def sequence(blob):
    out = []
    p = 0x400
    while p + 3 <= 0x800:
        c, a1, a2 = blob[p], blob[p+1], blob[p+2]
        out.append((p, c, a1, a2)); p += 3
        if c == 0x00: break
    return out

files = sorted(glob.glob(os.path.join(SCR, "ef*.bytes")))
print("files:", len(files))

lenfail = []
idxcensus = collections.Counter()
multi = []
allchunks = 0
for f in files:
    blob = open(f,'rb').read()
    ch, endpos, tblend = walk(blob)
    allchunks += len(ch)
    if endpos != len(blob): lenfail.append((os.path.basename(f), hex(endpos), hex(len(blob))))
    idxs = [c['idxField'] for c in ch]
    idxcensus[tuple(idxs)] += 1
    if len(ch) > 1: multi.append((os.path.basename(f), idxs))
print("chunks total:", allchunks)
print("length mismatches:", len(lenfail), lenfail[:5])
print("chunkIndex-vector census:")
for k,v in sorted(idxcensus.items(), key=lambda kv:-kv[1]):
    print("   ", k, "x", v)
print("multi-chunk files:", multi)

print()
print("=== 0x80+N program-liveness validation ===")
def run(key):
    fails = []
    total = 0
    unresolved = 0
    for f in files:
        blob = open(f,'rb').read()
        ch, _, _ = walk(blob)
        progtab = [programs(blob, c) for c in ch]
        cur = 0
        for (p, c, a1, a2) in sequence(blob):
            if c == 0x05:
                if key == 'ordinal':
                    cur = a1 if a1 < len(ch) else None
                else:
                    m = [i for i,cc in enumerate(ch) if cc['idxField'] == a1]
                    cur = m[0] if m else None
            elif c >= 0x80:
                total += 1
                N = c - 0x80
                if cur is None:
                    unresolved += 1
                    fails.append((os.path.basename(f), hex(p), hex(c), 'UNRESOLVED-CHUNK'))
                    continue
                pt = progtab[cur]
                if pt is None or N >= 16 or pt['progs'][N] == 0:
                    fails.append((os.path.basename(f), hex(p), hex(c), f'chunk{cur} prog{N} dead'))
    return total, fails, unresolved

for key in ('ordinal','chunkIndex'):
    total, fails, unres = run(key)
    print(f"key={key}: {total} 0x80+N opcodes, FAILURES={len(fails)} (unresolved-chunk {unres})")
    for x in fails[:20]: print("     ", x)
    byfile = collections.Counter(x[0] for x in fails)
    print("     by file:", dict(byfile))
