"""A1: control-flow call graph + data-xref to summon array. Distinguishes stubs from real bodies."""
import sys, re
sys.path.insert(0, r'C:/gd/Dream-World-IX/.claude/worktrees/unruffled-moser-861897/studies/custom-summons/thomas-swap/disasm')
import refkit

pe = refkit.load()
fns = refkit.functions(pe)
base = refkit.image_base(pe)

# Full instruction walk: build call/jmp target index AND absolute-immediate data refs.
# capstone renders direct branch as "call 0x18630" (absolute VA) and rip-mem as "[rip + 0xX]".
CF = {}          # target_rva -> [(from_rva, mnem)]
DATAREF = {}     # target_rva (from rip-relative lea/mov) -> [(from_rva, mnem, op)]
absimm_re = re.compile(r'^0x([0-9a-f]+)$')

for ins in refkit.iter_instructions(pe, fns):
    m = ins.mnemonic
    op = ins.op_str
    # control flow direct branch
    if m.startswith('j') or m == 'call':
        mm = absimm_re.match(op.strip())
        if mm:
            tgt = int(mm.group(1), 16) - base
            CF.setdefault(tgt, []).append((ins.address - base, m))
    # rip-relative data reference
    t = refkit._rip_target(ins, base)
    if t is not None:
        DATAREF.setdefault(t, []).append((ins.address - base, m, op))

def func_of(rva):
    return refkit.func_of(fns, rva)

# summon array + known scratch bases
TARGETS = {
    0x220830: "summonModels[] base",
    0x220060: "camera anchor scratch",
}
print("### DATA XREFS to known scratch/array bases (approx: refs landing in [base, base+0x200))")
for tb, label in TARGETS.items():
    print(f"\n-- {label} @ {hex(tb)} --")
    for t in sorted(DATAREF):
        if tb <= t < tb + 0x200:
            for (fr, mn, op) in DATAREF[t]:
                f = func_of(fr)
                fs = f"[{hex(f[0])}..{hex(f[1])}]" if f else "?"
                print(f"   {hex(t)}: from {hex(fr)} {mn} {op}  in {fs}")

# The error stubs (small funcs, xref site==begin). For each, who branches to it?
STUBS = {
    "Hi_DebugPSGData": 0x1534c,
    "Hi_DrawEffModel": 0x16547,
    "Hi_DrawSliceEffModel": 0x167cd,
    "Hi_DrawEffModelByBone": 0x16c9d,
    "Hi_GetSummonBoneMatrix": 0x16c80,
    "Hi_DrawSummonModel": 0x179f2,
}
print("\n\n### WHO BRANCHES/CALLS INTO EACH ERROR STUB (=> real body) ###")
for name, stub in STUBS.items():
    srcs = CF.get(stub, [])
    print(f"\n-- {name} stub@{hex(stub)} : {len(srcs)} inbound branch(es)")
    for fr, mn in srcs:
        f = func_of(fr)
        fs = f"[{hex(f[0])}..{hex(f[1])}] sz={f[1]-f[0]}" if f else "?"
        print(f"   from {hex(fr)} {mn}  in {fs}")
