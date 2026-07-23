"""A1: per-function classification for the plugin's Hi_* region."""
import sys, re
sys.path.insert(0, r'C:/gd/Dream-World-IX/.claude/worktrees/unruffled-moser-861897/studies/custom-summons/thomas-swap/disasm')
import refkit

pe = refkit.load()
fns = refkit.functions(pe)
base = refkit.image_base(pe)
absimm_re = re.compile(r'^0x([0-9a-f]+)$')

# name each Hi_ string rva
hi_strings = {rva: txt for rva, txt in refkit.find_strings(pe, "Hi_")}

# full data + control walk
strref = {}   # func_begin -> set of hi string names referenced
cf_out = {}   # func_begin -> set of call/jmp target rvas
arr_ref = {}  # func_begin -> set of array bases touched
ARRAYS = {0x220830:"SUMMON", 0x220230:"EFFARR", 0x220060:"CAMANCHOR", 0x220890:"DBGCTX"}

def fb(rva):
    f = refkit.func_of(fns, rva)
    return f[0] if f else None

for ins in refkit.iter_instructions(pe, fns):
    b = fb(ins.address - base)
    if b is None: continue
    t = refkit._rip_target(ins, base)
    if t is not None:
        if t in hi_strings:
            strref.setdefault(b, set()).add(hi_strings[t].replace("()","").replace(" ",""))
        for ab, nm in ARRAYS.items():
            if ab <= t < ab+0x80:
                arr_ref.setdefault(b, set()).add(nm)
    if ins.mnemonic.startswith('j') or ins.mnemonic=='call':
        mm = absimm_re.match(ins.op_str.strip())
        if mm:
            cf_out.setdefault(b, set()).add(int(mm.group(1),16)-base)

# who calls each function (inbound)
cf_in = {}
for b, tgts in cf_out.items():
    for t in tgts:
        cf_in.setdefault(t, set()).add(b)

# print table for the region
print(f"{'begin':>8} {'end':>8} {'sz':>5}  strref / arrays / #callers")
for b, e in fns:
    if not (0x15000 <= b < 0x19000 or 0x2300 <= b < 0x3200): continue
    sz = e-b
    s = strref.get(b, set())
    a = arr_ref.get(b, set())
    callers = cf_in.get(b, set())
    tag = ""
    if sz <= 31 and s: tag = "  <-- ERROR-STUB"
    print(f"{hex(b):>8} {hex(e):>8} {sz:>5}  str={sorted(s)} arr={sorted(a)} callers={len(callers)}{tag}")
