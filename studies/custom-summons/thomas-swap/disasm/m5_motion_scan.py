"""M5 -- structural scanner: find MOTION-clip headers inside a raw ef###.bytes blob.

Pure format-parser code (committable). It reads the user's own extracted stock blob from the
LOCAL SCRATCH dir and prints only STRUCTURE (offsets/counts) -- never game content bytes.

The decoded Motion header (from FF9SpecialEffectPlugin.dll fn 0x7820 / x86 0x70c0):
    +0x02 u16 frameCount
    +0x04/+0x06/+0x08 u16 tx,ty,tz : s16 CONSTANT if (flags & 1/2/4) else u16 byte-offset to
                                     an s16[frameCount] per-frame track (motion-relative)
    +0x0a u8  flags (bits 0..2 only)
    +0x0c u32 rotKeyOff   (motion-relative byte offset, < 0x10000 on disk)
    +0x10 u32 fineKeyOff  (motion-relative byte offset, < 0x100000 on disk; 0 = absent)
  rot key table: nodeCount x 8 bytes { u16 a0; s16 a1; u16 a2; s16 flags }
     per axis: flags bit set -> literal raw angle; clear -> u8 track at motion+field, index = frame
  fine key table: nodeCount x 8 bytes, same shape, nibble track (2 frames/byte), index = frame>>1
"""
import struct, sys, os, math

def scan(path, max_nodes=64):
    b = open(path,'rb').read()
    n = len(b)
    hits=[]
    for m in range(0, n-0x14, 2):
        fc = struct.unpack_from('<H', b, m+2)[0]
        if not (2 <= fc <= 2048): continue
        fl = b[m+0x0a]
        if fl & 0xF8: continue
        r0 = struct.unpack_from('<I', b, m+0x0c)[0]
        r1 = struct.unpack_from('<I', b, m+0x10)[0]
        if not (0x14 <= r0 < 0x10000): continue
        if r1 != 0 and not (0x14 <= r1 < 0x100000): continue
        if m + r0 + 8 > n: continue
        if r1 and m + r1 + 8 > n: continue
        # translation fields must be in-bounds tracks when not constant
        ok = True
        for i,bit in enumerate((1,2,4)):
            if not (fl & bit):
                off = struct.unpack_from('<H', b, m+4+2*i)[0]
                if off < 0x14 or m+off+2*fc > n: ok = False; break
        if not ok: continue
        # walk the rot key table: count how many consecutive 8-byte entries are self-consistent
        cnt = 0
        while cnt < max_nodes and m + r0 + (cnt+1)*8 <= n:
            e = m + r0 + cnt*8
            a0, a1, a2, kf = struct.unpack_from('<HhHh', b, e)
            if kf & ~0x7: break
            bad = False
            for v, bit in ((a0,1),(a1,2),(a2,4)):
                if kf & bit:
                    if not (-4096 <= (v if v<32768 else v-65536) <= 4096): bad=True
                else:
                    if v < 0x14 or m + v + fc > n: bad=True
            if bad: break
            cnt += 1
        if cnt < 2: continue
        # the fine table (if present) must agree on node count
        fcnt = 0
        if r1:
            half = (fc+1)//2
            while fcnt < cnt and m + r1 + (fcnt+1)*8 <= n:
                e = m + r1 + fcnt*8
                a0,a1,a2,kf = struct.unpack_from('<HhHh', b, e)
                if kf & ~0x7: break
                bad=False
                for v,bit in ((a0,1),(a1,2),(a2,4)):
                    if not (kf & bit):
                        if v < 0x14 or m + v + half > n: bad=True
                if bad: break
                fcnt += 1
            if fcnt != cnt: continue
        hits.append((m, fc, fl, r0, r1, cnt))
    return hits

if __name__ == '__main__':
    for p in sys.argv[1:]:
        h = scan(p)
        print(f"== {os.path.basename(p)}  size={os.path.getsize(p)}  candidates={len(h)}")
        for m,fc,fl,r0,r1,cnt in h[:25]:
            print(f"   @{m:#08x} frames={fc:4d} flags={fl} rotKeyOff={r0:#06x} fineKeyOff={r1:#07x} nodes>={cnt}")
