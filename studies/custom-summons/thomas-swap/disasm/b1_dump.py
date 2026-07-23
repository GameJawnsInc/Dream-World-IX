"""B1 -- dump the real bodies around Hi_GetSummonBoneMatrix and the pose/draw path."""
import sys
sys.path.insert(0, r'C:/gd/Dream-World-IX/.claude/worktrees/unruffled-moser-861897/studies/custom-summons/thomas-swap/disasm')
import refkit

pe = refkit.load()
fns = refkit.functions(pe)
base = refkit.image_base(pe)

def dump(lo, hi, label=""):
    print(f"\n===== {label}  [{hex(lo)}..{hex(hi)}]  size={hi-lo} =====")
    for ins in refkit.disasm(pe, lo, hi):
        rt = refkit._rip_target(ins, base)
        extra = f"   ; -> RVA {hex(rt)}" if rt is not None else ""
        print(f"  {hex(ins.address-base)}: {ins.mnemonic}\t{ins.op_str}{extra}")

def frange(rva):
    return refkit.func_of(fns, rva)

import argparse
ap = argparse.ArgumentParser()
ap.add_argument("targets", nargs="*", help="hex RVAs to dump the covering .pdata function of")
ap.add_argument("--range", nargs=2, help="explicit lo hi")
args = ap.parse_args()

if args.range:
    lo = int(args.range[0], 16); hi = int(args.range[1], 16)
    dump(lo, hi, "explicit")
for t in args.targets:
    rva = int(t, 16)
    fr = frange(rva)
    if fr:
        dump(fr[0], fr[1], f"func covering {t}")
    else:
        print(f"no .pdata function covers {t}")
