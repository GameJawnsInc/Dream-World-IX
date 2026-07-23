"""Independent verification of the 'dispatch-interpreter' claim.

Claim: every summon Hi_* fn is called from exactly one site inside the mega-interpreter
[0xeea4..0x12321], and each handler entry lives in a .rdata fn-ptr table [0x68780..0x68cf8].

We do NOT reuse refkit.xrefs_to (RIP-relative only -> misses `call rel32`). We build our own
call/jmp target map by disassembling every .pdata function, and a full-image qword scan for
pointers into the code.
"""
import sys
sys.path.insert(0, r'C:/gd/Dream-World-IX/.claude/worktrees/unruffled-moser-861897/studies/custom-summons/thomas-swap/disasm')
import refkit, struct
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

pe = refkit.load()
base = refkit.image_base(pe)
fns = refkit.functions(pe)
md = Cs(CS_ARCH_X86, CS_MODE_64)
md.detail = True

INTERP = (0xeea4, 0x12321)
TBL = (0x68780, 0x68cf8)

# --- 1. Build a call/jmp target -> [caller_rva] map across ALL pdata functions ---
calls = {}   # target_rva -> list of (from_rva, mnem)
jmps = {}
for b, e in fns:
    try:
        code = refkit.read_rva(pe, b, e - b)
    except Exception:
        continue
    for ins in md.disasm(code, base + b):
        if ins.mnemonic in ('call', 'jmp'):
            op = ins.op_str
            # direct rel target shows as bare hex absolute address in capstone
            if op.startswith('0x'):
                try:
                    tgt = int(op, 16) - base
                except ValueError:
                    continue
                d = calls if ins.mnemonic == 'call' else jmps
                d.setdefault(tgt, []).append((ins.address - base, ins.mnemonic))

# --- 2. Scan the whole image for qwords that are code pointers (image_base + rva) ---
data = pe.__data__
# map rva ranges from sections for file-offset lookups
def rva_to_off(rva):
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData):
            return s.PointerToRawData + (rva - s.VirtualAddress)
    return None

def off_to_rva(off):
    for s in pe.sections:
        if s.PointerToRawData <= off < s.PointerToRawData + s.SizeOfRawData:
            return s.VirtualAddress + (off - s.PointerToRawData)
    return None

# Dump the claimed table region as qwords
print("=== TABLE REGION DUMP [0x%x..0x%x] ===" % TBL)
tbl_entries = {}   # entry_rva -> [slot_rva,...]
off0 = rva_to_off(TBL[0])
n = (TBL[1] - TBL[0]) // 8
for i in range(n):
    foff = off0 + i * 8
    val = struct.unpack('<Q', data[foff:foff + 8])[0]
    slot_rva = TBL[0] + i * 8
    if val == 0:
        continue
    ent = val - base
    if 0 < ent < 0x200000:
        tbl_entries.setdefault(ent, []).append(slot_rva)

# --- 3. Full-image qword scan: where does each summon entry appear as a pointer? ---
def find_ptr_slots(entry_rva):
    """all rvas in the image whose qword == base+entry_rva"""
    needle = struct.pack('<Q', base + entry_rva)
    out = []
    start = 0
    while True:
        i = data.find(needle, start)
        if i < 0:
            break
        r = off_to_rva(i)
        if r is not None and i % 8 == (rva_to_off(TBL[0]) % 8):  # not enforcing align
            pass
        out.append((i, r))
        start = i + 1
    return out

# Summon roster entries (independently checked below). name -> entry rva
ROSTER = {
    "Hi_RegisterSummonModel": 0x15ee0,
    "Hi_DrawSummonModel":     0x17710,
    "Hi_SetSummonMotion":     0x17a10,
    "Hi_SetSummonMotFrame":   0x17a70,
    "Hi_GetSummonBonePos":    0x185b0,
    "Hi_GetSummonBoneMatrix": 0x18630,
    "Hi_ShowSummonModelMesh": 0x187e0,
    "Hi_HideSummonModelMesh": 0x18840,
    "Hi_StartSummonTexAnim":  0x188a0,
    "Hi_StopSummonTexAnim":   0x18930,
    "Hi_ModifySummonModelAbr":0x18af0,
    "Hi_ModifySummonModelRGB":0x18b50,
}

def inrange(r, lohi):
    return lohi[0] <= r < lohi[1]

print("\n=== PER-FUNCTION CALLER + TABLE ANALYSIS ===")
print("%-24s %-9s %-40s %-30s" % ("name","entry","callers(call sites)","ptr-slots(all image)"))
for name, ent in ROSTER.items():
    cs = calls.get(ent, [])
    js = jmps.get(ent, [])
    interp_callers = [c for c in cs if inrange(c[0], INTERP)]
    other_callers = [c for c in cs if not inrange(c[0], INTERP)]
    slots = find_ptr_slots(ent)
    tbl_slots = [r for _, r in slots if r is not None and inrange(r, TBL)]
    other_slots = [r for _, r in slots if r is not None and not inrange(r, TBL)]
    print("\n%s  entry=0x%x" % (name, ent))
    print("  call sites total=%d  in-interp=%d  outside=%d" % (len(cs), len(interp_callers), len(other_callers)))
    print("    in-interp: %s" % ["0x%x"%c[0] for c in interp_callers])
    if other_callers:
        print("    OUTSIDE : %s" % [("0x%x/%s"%(c[0],c[1])) for c in other_callers])
    if js:
        print("    jmp-tail: %s" % [("0x%x"%j[0]) for j in js])
    print("  ptr-slots in-table=%s  outside-table=%s" %
          (["0x%x"%r for r in tbl_slots], ["0x%x"%r for r in other_slots]))
