"""B5 x86 cross-check helpers. x86 DLL: no .pdata, absolute (non-RIP) addressing.

Locate functions via the SAME leftover error strings, but x86 references them as
absolute immediates (push/lea/mov imm32 == image_base + string_rva). We find those
sites by scanning .text raw bytes for the 4-byte LE immediate, then disassemble a
window to read the instruction + surrounding code.
"""
import struct
import sys
import refkit
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

pe = refkit.load('x86')
BASE = refkit.image_base(pe)  # 0x10000000
md = Cs(CS_ARCH_X86, CS_MODE_32)
md.detail = True

TEXT = next(s for s in pe.sections if s.Name.startswith(b'.text'))
TEXT_RVA = TEXT.VirtualAddress
TEXT_SIZE = TEXT.Misc_VirtualSize
TEXT_BYTES = pe.get_data(TEXT_RVA, TEXT_SIZE)


def imm_xref_sites(target_rva):
    """RVAs in .text whose 4-byte content == BASE+target_rva (an absolute operand)."""
    needle = struct.pack('<I', BASE + target_rva)
    out = []
    start = 0
    while True:
        i = TEXT_BYTES.find(needle, start)
        if i < 0:
            break
        out.append(TEXT_RVA + i)
        start = i + 1
    return out


def disasm_window(begin_rva, nbytes):
    code = pe.get_data(begin_rva, nbytes)
    return list(md.disasm(code, BASE + begin_rva))


def instr_referencing(target_rva, back=16, fwd=8):
    """For each immediate-xref site, find the instruction that contains it by
    disassembling a small window ending near the operand location."""
    results = []
    for site in imm_xref_sites(target_rva):
        # the imm32 is an operand; the instruction starts a few bytes before `site`.
        # try starting points from site-back..site-1, pick the disasm that lands an
        # instruction whose bytes include `site` and whose op_str mentions the abs addr.
        found = None
        for b in range(back, 0, -1):
            begin = site - b
            if begin < TEXT_RVA:
                continue
            try:
                ins_list = disasm_window(begin, b + fwd)
            except Exception:
                continue
            for ins in ins_list:
                r = ins.address - BASE
                if r <= site < r + ins.size and (site + 4) <= r + ins.size:
                    # instruction fully contains the imm dword
                    if ('%x' % (BASE + target_rva)) in ins.op_str.replace('0x', ''):
                        found = (r, ins.mnemonic, ins.op_str)
                        break
            if found:
                break
        results.append((site, found))
    return results


def find_start(rva, maxback=600):
    """Function start = first byte after a run of >=2 int3 (0xcc) padding before rva."""
    data = TEXT_BYTES
    off = rva - TEXT_RVA
    for i in range(off, max(off - maxback, 1), -1):
        if data[i - 1] == 0xcc and data[i - 2] == 0xcc:
            return TEXT_RVA + i
    return None


def dump_fn(rva_hint, maxbytes=0x400):
    """Disassemble a function starting at the int3-delimited start covering rva_hint,
    stopping at the trailing int3 padding."""
    start = find_start(rva_hint)
    if start is None:
        start = rva_hint
    code = pe.get_data(start, maxbytes)
    out = []
    for ins in md.disasm(code, BASE + start):
        out.append(ins)
        if ins.mnemonic == 'int3':
            # stop once we hit padding after at least one ret
            if any(x.mnemonic in ('ret', 'jmp') for x in out[:-1]):
                break
    return start, out


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--fn', dest='fn')  # hex rva hint -> auto-bound + dump the whole function
    ap.add_argument('--str', dest='needle')
    ap.add_argument('--ref', dest='ref_rva')  # hex rva of a string; show referencing instrs
    ap.add_argument('--dis', dest='dis')      # hex rva:count to disassemble
    a = ap.parse_args()
    if a.fn:
        start, ins_list = dump_fn(int(a.fn, 16))
        print('FUNC start @%s (%d instrs)' % (hex(start), len(ins_list)))
        for ins in ins_list:
            print('  %s: %s\t%s' % (hex(ins.address - BASE), ins.mnemonic, ins.op_str))
    if a.needle:
        for rva, txt in refkit.find_strings(pe, a.needle):
            print(hex(rva), repr(txt))
    if a.ref_rva:
        t = int(a.ref_rva, 16)
        for site, found in instr_referencing(t):
            if found:
                print('  ref-site %s : instr@%s  %s %s' % (hex(site), hex(found[0]), found[1], found[2]))
            else:
                print('  ref-site %s : (no clean instr decode)' % hex(site))
    if a.dis:
        rva_s, cnt_s = a.dis.split(':')
        rva = int(rva_s, 16)
        cnt = int(cnt_s)
        code = pe.get_data(rva, cnt)
        for ins in md.disasm(code, BASE + rva):
            print('  %s: %s\t%s' % (hex(ins.address - BASE), ins.mnemonic, ins.op_str))
