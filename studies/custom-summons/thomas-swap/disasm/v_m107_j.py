"""V-M1-07 step J: the OTHER writer of DATA+0x38 -- model_prepare@0x7120 :71f7. Persistent alloc?"""
import re
import refkit
pe = refkit.load()
fns = refkit.functions(pe)
BASE = refkit.image_base(pe)

f = refkit.func_of(fns, 0x7120)
print("model_prepare fn:", hex(f[0]), hex(f[1]), f[1]-f[0])
for ins in refkit.disasm(pe, f[0], f[1]):
    print(f"  {hex(ins.address-BASE)}: {ins.mnemonic}\t{ins.op_str}")

# broader sweep: ANY write form to [reg+0x38] where reg != rsp/rbp-frame
print("\n=== broader: any mov/lea/movups store into [reg + 0x38] (non-rsp) ===")
PAT = re.compile(r"^(?:qword|dword|xmmword)? ?ptr \[(?!rsp)(r[a-z0-9]+) \+ 0x38\],")
for ins in refkit.iter_instructions(pe, fns):
    if ins.mnemonic in ("mov", "movups", "movdqu", "movaps") and PAT.match(ins.op_str):
        fn = refkit.func_of(fns, ins.address - BASE)
        print(f"  {hex(ins.address-BASE)}  fn {hex(fn[0]) if fn else '?'}  {ins.mnemonic} {ins.op_str}")
