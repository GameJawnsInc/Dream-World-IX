import sys, refkit
pe = refkit.load()
def dump(b,e,label):
    print(f"\n===== {label}  [0x{b:x}..0x{e:x}]  ({e-b} bytes) =====")
    for ins in refkit.disasm(pe, b, e):
        print(f"  0x{ins.address:06x}: {ins.mnemonic:10s} {ins.op_str}")
if __name__ == "__main__":
    for a in sys.argv[1:]:
        b,e,lab = a.split(":")
        dump(int(b,16), int(e,16), lab)
