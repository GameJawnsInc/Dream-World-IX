"""V-M1-07 step C: the MOTION path -- does bones[0] get the root translation? bone stride?"""
import refkit
pe = refkit.load()
fns = refkit.functions(pe)
# which pdata functions cover 0x7a20..0x8100 ?
print("pdata funcs in 0x7800..0x8200:")
for b, e in fns:
    if 0x7700 <= b < 0x8300:
        print("   ", hex(b), hex(e), "size", e-b)
