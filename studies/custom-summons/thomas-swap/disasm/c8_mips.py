"""C8 independent verification: walk ef###.bytes per fn 0xd390, extract id-3 payloads,
and decode the code region with the DLL's OWN decode table (dumped from 0x66c70)."""
import struct, glob, os, sys, refkit

pe = refkit.load()
TB = 0x66c70
ent = []
i = 0
while True:
    d = pe.get_data(TB + i*0x38, 0x38)
    mask, match = struct.unpack_from("<II", d, 0)
    if mask == 0: break
    ent.append((mask, match))
    i += 1
# NOTE: loop reads NEXT mask to decide continuation; entry 0 is included unconditionally.

def decode(word):
    for idx, (m, mt) in enumerate(ent):
        if (word & m) == mt:
            return idx
    return None

def walk(path):
    b = open(path, 'rb').read()
    n = struct.unpack_from("<h", b, 0)[0]
    p = 2; pos = 0x800; out = []
    for c in range(n):
        ci, rc = struct.unpack_from("<hh", b, p); p += 4
        for j in range(rc):
            rid = struct.unpack_from("<b", b, p)[0]
            info = struct.unpack_from("<b", b, p+1)[0]
            sz = struct.unpack_from("<h", b, p+2)[0] << 11
            p += 4
            if rid == 3:
                out.append((pos, sz))
            pos += sz
            if rid == 2 and info != 0:
                pos += struct.unpack_from("<h", b, p)[0] << 11; p += 2
    return b, pos, out

files = sorted(glob.glob(r"C:/gd/SCRATCH/summon-format/ef*.bytes"))
if len(sys.argv) > 1: files = [f for f in files if os.path.basename(f) in sys.argv[1:]]
tot_words = tot_ok = 0
worst = []
nfile = 0
for f in files:
    try:
        b, endpos, id3 = walk(f)
    except Exception as e:
        print("WALKFAIL", f, e); continue
    if endpos != len(b):
        print("CURSOR MISMATCH", os.path.basename(f), hex(endpos), hex(len(b))); continue
    nfile += 1
    for (off, sz) in id3:
        pay = b[off:off+sz]
        ptr = struct.unpack_from("<I", pay, 0)[0]
        psxbase = 0x801E7700  # low 28 bits only matter
        hdr = (ptr & 0x0FFFFFFF) - (psxbase & 0x0FFFFFFF)
        # code region = [0, hdr); test words from offset 4 (word0 is the header pointer)
        if not (0 < hdr <= sz): print("BADHDR", os.path.basename(f), hex(hdr), hex(sz)); continue
        ok = bad = 0
        for o in range(4, hdr - 3, 4):
            w = struct.unpack_from("<I", pay, o)[0]
            if decode(w) is None: bad += 1
            else: ok += 1
        tot_words += ok + bad; tot_ok += ok
        r = ok / max(1, ok + bad)
        worst.append((r, os.path.basename(f), ok, bad, hex(hdr)))
worst.sort()
print("files walked clean: %d/%d ; entries in decode table: %d" % (nfile, len(files), len(ent)))
print("id-3 code words: %d  decoded-as-MIPS: %d (%.4f%%)" % (tot_words, tot_ok, 100*tot_ok/max(1,tot_words)))
print("worst 10 images:")
for r, nm, ok, bad, h in worst[:10]:
    print("   %.4f  %-14s ok=%-7d bad=%-5d headerRel=%s" % (r, nm, ok, bad, h))
print("images at 100%%: %d / %d" % (sum(1 for w in worst if w[0] == 1.0), len(worst)))
