import struct,sys
import m5_motion_verify as V
b=open(sys.argv[1],'rb').read()
print(f"{'motion':>10} {'fr':>3} {'fl':>2}   rootTranslation per-axis: min..max (span), maxStep")
for spec in sys.argv[2:]:
    m=int(spec,16); fc=V.u16(b,m+2); fl=b[m+0xa]
    out=[]
    for i,bit in enumerate((1,2,4)):
        if fl & bit:
            out.append(f"{'XYZ'[i]}=const({V.s16(b,m+4+2*i)})")
        else:
            o=V.u16(b,m+4+2*i); vals=[V.s16(b,m+o+2*t) for t in range(fc)]
            d=[abs(vals[t+1]-vals[t]) for t in range(fc-1)]
            out.append(f"{'XYZ'[i]}={min(vals)}..{max(vals)}(span {max(vals)-min(vals)},maxStep {max(d) if d else 0})")
    print(f"{m:#010x} {fc:3d} {fl:2d}   " + "  ".join(out))
