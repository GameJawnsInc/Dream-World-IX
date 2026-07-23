"""V-C2 part 2: why grammar-A (claim as stated) fails, and is the endpoint a NATIVE check?"""
import struct, glob, os
from v_c2_walk import walk, NATIVE, SCRATCH

blob = open(os.path.join(SCRATCH, "ef000.bytes"), "rb").read()
print("ef000 len", hex(len(blob)))
print("raw table bytes 0x00..0x30:", blob[:0x30].hex(" "))
for label, rule in (("A_as_stated", None), ("B_native", NATIVE)):
    nc, ch, cur, tend = walk(blob, rule)
    print(f"\n--- {label}: chunks={nc} tableEnd={tend:#x} cursor={cur:#x} (len {len(blob):#x})")
    for cidx, res in ch:
        print(f"  chunk idx={cidx} nres={len(res)}")
        for rid, info, size, ex in res:
            print(f"    id={rid:3d} info={info:3d} sizeSectors={size:5d} extra={ex}")

# how many bytes of misalignment does grammar A accumulate?
tot = 0
for f in sorted(glob.glob(os.path.join(SCRATCH, "ef*.bytes"))):
    b = open(f, "rb").read()
    _, ch, _, _ = walk(b, NATIVE)
    n = sum(1 for _, res in ch for r in res if r[3] is not None)
    tot += n
print("\ntotal resources carrying the conditional extra u16 across corpus:", tot)
