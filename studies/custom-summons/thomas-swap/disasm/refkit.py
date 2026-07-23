"""refkit -- the shared reverse-engineering instrument for the FF9SpecialEffectPlugin.dll disasm round.

Every disasm agent stands on THIS ONE verified tool rather than re-implementing PE/capstone parsing
(the "calibrate the instrument before you judge with it" law -- a wrong PE walk silently poisons
every downstream finding). Committable: pure format-parser code, ZERO extracted stock bytes (it reads
the user's own installed DLL at runtime and prints RVAs/mnemonics -- never writes game bytes anywhere).

The DLL (x64, 435 KB, MSVC2013, unpacked) carries leftover ASCII debug strings that name almost every
internal function (`Hi_GetSummonBoneMatrix ()`, `Hi_SetSummonMotion()`, ...). Those strings are
referenced from inside the very functions they name (classic `printf`/assert pattern), so the reliable
way to LOCATE a function is:

    string_rva  = find the "Hi_Foo" string's RVA
    xref_rvas   = find every `lea reg, [rip+disp]` whose target == string_rva
    func_start  = the .pdata RUNTIME_FUNCTION whose [begin,end) range covers an xref

This module exposes exactly those primitives, plus a linear capstone disassembly of a function body.

Usage (from any agent):
    import refkit
    pe   = refkit.load()                       # x64 by default
    fns  = refkit.functions(pe)                # [(begin_rva, end_rva), ...] from .pdata, sorted
    smap = refkit.string_rvas(pe)              # {rva: text} for every ASCII run >= 4 chars
    rva  = refkit.find_string(pe, "Hi_GetSummonBoneMatrix")   # -> rva or None
    xr   = refkit.xrefs_to(pe, rva)            # [(from_rva, mnemonic, op_str), ...]
    fn   = refkit.func_of(fns, xr[0][0])       # -> (begin, end) covering that xref
    for ins in refkit.disasm(pe, fn[0], fn[1]):
        print(hex(ins.address), ins.mnemonic, ins.op_str)

CLI self-test / quick lookups:
    py refkit.py                     # self-test: parse .pdata, locate the Hi_Summon* roster by xref
    py refkit.py --func Hi_GetSummonBoneMatrix   # locate + disassemble that function
    py refkit.py --list-strings Summon           # every string containing "Summon" + its RVA
"""
from __future__ import annotations
import argparse
import re
import sys
from bisect import bisect_right

import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_64, CS_MODE_32

DLL_X64 = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\x64\FF9_Data\Plugins\FF9SpecialEffectPlugin.dll"
DLL_X86 = r"C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\x86\FF9_Data\Plugins\FF9SpecialEffectPlugin.dll"


def load(arch: str = "x64") -> pefile.PE:
    """Parse the DLL and its data directories. `arch` in {'x64','x86'}."""
    path = DLL_X64 if arch == "x64" else DLL_X86
    pe = pefile.PE(path, fast_load=True)
    pe.parse_data_directories(directories=[
        pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"],
        pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXCEPTION"],
        pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
    ])
    pe._refkit_arch = arch  # type: ignore[attr-defined]
    return pe


def _md(pe: pefile.PE) -> Cs:
    mode = CS_MODE_64 if getattr(pe, "_refkit_arch", "x64") == "x64" else CS_MODE_32
    md = Cs(CS_ARCH_X86, mode)
    md.detail = False
    return md


def image_base(pe: pefile.PE) -> int:
    return pe.OPTIONAL_HEADER.ImageBase


def functions(pe: pefile.PE):
    """[(begin_rva, end_rva), ...] from the x64 .pdata RUNTIME_FUNCTION table, sorted by begin.

    x64 only (x86 has no .pdata). For x86 fall back to `export_bodies` + linear scan.
    """
    out = []
    if hasattr(pe, "DIRECTORY_ENTRY_EXCEPTION"):
        for entry in pe.DIRECTORY_ENTRY_EXCEPTION:
            sf = entry.struct
            out.append((sf.BeginAddress, sf.EndAddress))
    out.sort()
    return out


def func_of(fns, rva: int):
    """The (begin,end) function range covering `rva`, or None. `fns` = functions(pe)."""
    begins = [b for b, _ in fns]
    i = bisect_right(begins, rva) - 1
    if i < 0:
        return None
    b, e = fns[i]
    return (b, e) if b <= rva < e else None


def _section_for_rva(pe: pefile.PE, rva: int):
    for s in pe.sections:
        if s.VirtualAddress <= rva < s.VirtualAddress + max(s.Misc_VirtualSize, s.SizeOfRawData):
            return s
    return None


def read_rva(pe: pefile.PE, rva: int, size: int) -> bytes:
    return pe.get_data(rva, size)


def string_rvas(pe: pefile.PE, min_len: int = 4):
    """{rva: text} for every printable ASCII run of length >= min_len across the whole image.

    RVA is computed from each string's file offset via the containing section.
    """
    data = pe.__data__
    out = {}
    for m in re.finditer(rb"[ -~]{%d,}" % min_len, data):
        foff = m.start()
        # map file offset -> rva
        for s in pe.sections:
            start = s.PointerToRawData
            end = start + s.SizeOfRawData
            if start <= foff < end:
                rva = s.VirtualAddress + (foff - start)
                out[rva] = m.group().decode("latin-1")
                break
    return out


def find_string(pe: pefile.PE, needle: str):
    """First RVA whose string contains `needle` (substring). None if absent."""
    for rva, txt in string_rvas(pe).items():
        if needle in txt:
            return rva
    return None


def find_strings(pe: pefile.PE, needle: str):
    """[(rva, text), ...] for every string containing `needle`, sorted by rva."""
    return sorted((rva, txt) for rva, txt in string_rvas(pe).items() if needle in txt)


_RIP_RE = re.compile(r"\[rip ([+-]) 0x([0-9a-f]+)\]")


def _rip_target(ins, base: int):
    """RVA an instruction's RIP-relative operand resolves to, or None."""
    if "rip" not in ins.op_str:
        return None
    m = _RIP_RE.search(ins.op_str)
    if not m:
        return None
    disp = int(m.group(2), 16) * (1 if m.group(1) == "+" else -1)
    return (ins.address - base) + ins.size + disp


def iter_instructions(pe: pefile.PE, fns=None):
    """Yield every instruction in the image, disassembled PER FUNCTION off the .pdata table
    (realigns at each function start -- a plain linear section sweep desyncs on embedded data
    and silently drops real instructions, which is why a naive xref scan finds nothing)."""
    md = _md(pe)
    base = image_base(pe)
    fns = fns or functions(pe)
    for b, e in fns:
        try:
            code = read_rva(pe, b, e - b)
        except Exception:
            continue
        for ins in md.disasm(code, base + b):
            yield ins


def xrefs_to(pe: pefile.PE, target_rva: int, fns=None):
    """[(from_rva, mnemonic, op_str), ...]: every instruction whose RIP-relative operand
    resolves to target_rva. Disassembles per-function (see iter_instructions) so it does not
    desync. Catches `lea reg,[rip+disp]` string loads -- the primary function-locator signal."""
    base = image_base(pe)
    hits = []
    for ins in iter_instructions(pe, fns):
        if _rip_target(ins, base) == target_rva:
            hits.append((ins.address - base, ins.mnemonic, ins.op_str))
    return hits


def xref_index(pe: pefile.PE, lo_rva: int, hi_rva: int, fns=None):
    """{target_rva: [(from_rva, mnemonic, op_str), ...]} for every RIP-relative reference whose
    target lands in [lo_rva, hi_rva). ONE image walk -- far cheaper than xrefs_to per target when
    resolving a whole roster of strings at once."""
    base = image_base(pe)
    out = {}
    for ins in iter_instructions(pe, fns):
        t = _rip_target(ins, base)
        if t is not None and lo_rva <= t < hi_rva:
            out.setdefault(t, []).append((ins.address - base, ins.mnemonic, ins.op_str))
    return out


def locate_function(pe: pefile.PE, name: str, fns=None):
    """Best-effort: locate the function whose body references the debug string `name`.

    Returns dict {name, string_rva, xrefs:[rva...], func:(begin,end)|None, note}.
    """
    fns = fns or functions(pe)
    srva = find_string(pe, name)
    if srva is None:
        return {"name": name, "string_rva": None, "func": None, "note": "string not found"}
    xr = xrefs_to(pe, srva)
    funcs = []
    for from_rva, _, _ in xr:
        f = func_of(fns, from_rva)
        if f and f not in funcs:
            funcs.append(f)
    return {
        "name": name,
        "string_rva": srva,
        "xrefs": [x[0] for x in xr],
        "func": funcs[0] if funcs else None,
        "all_funcs": funcs,
        "note": "ok" if funcs else "string found, no code xref (data-only or indirect)",
    }


def disasm(pe: pefile.PE, begin_rva: int, end_rva: int):
    """Yield capstone instructions for [begin_rva, end_rva). Linear disasm of the function body."""
    md = _md(pe)
    size = end_rva - begin_rva
    code = read_rva(pe, begin_rva, size)
    base = image_base(pe)
    yield from md.disasm(code, base + begin_rva)


def exports(pe: pefile.PE):
    """{name: rva} for every export."""
    out = {}
    if hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
        for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
            if e.name:
                out[e.name.decode()] = e.address
    return out


SUMMON_ROSTER = [
    "Hi_RegisterSummonModel", "Hi_DrawSummonModel", "Hi_SetSummonMotion", "Hi_SetSummonMotFrame",
    "Hi_GetSummonBonePos", "Hi_GetSummonBoneMatrix", "Hi_ShowSummonModelMesh", "Hi_HideSummonModelMesh",
    "Hi_StartSummonTexAnim", "Hi_StopSummonTexAnim", "Hi_ModifySummonModelAbr", "Hi_ModifySummonModelRGB",
]


def _self_test(arch="x64"):
    pe = load(arch)
    fns = functions(pe)
    print(f"[refkit] arch={arch} image_base={hex(image_base(pe))} sections={len(pe.sections)}")
    print(f"[refkit] .pdata functions: {len(fns)}")
    exp = exports(pe)
    print(f"[refkit] exports: {len(exp)} -> {sorted(exp)[:4]}...")
    print("[refkit] locating the Hi_Summon* roster by string-xref:")
    ok = 0
    for name in SUMMON_ROSTER:
        info = locate_function(pe, name, fns)
        srva = info["string_rva"]
        f = info["func"]
        nx = len(info.get("xrefs", []))
        if f:
            ok += 1
            print(f"   {name:26s} str@{hex(srva) if srva else '-':>10s} xrefs={nx:2d} "
                  f"FUNC[{hex(f[0])}..{hex(f[1])}] size={f[1]-f[0]}")
        else:
            print(f"   {name:26s} str@{hex(srva) if srva else '-':>10s} xrefs={nx:2d} -- {info['note']}")
    print(f"[refkit] located {ok}/{len(SUMMON_ROSTER)} summon functions by xref")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arch", default="x64", choices=["x64", "x86"])
    ap.add_argument("--func", help="locate + disassemble the function referencing this debug string")
    ap.add_argument("--list-strings", help="print every string containing this substring + its RVA")
    ap.add_argument("--max", type=int, default=400, help="max instructions to print for --func")
    args = ap.parse_args()

    if args.list_strings:
        pe = load(args.arch)
        for rva, txt in find_strings(pe, args.list_strings):
            print(f"{hex(rva):>10s}  {txt!r}")
        return
    if args.func:
        pe = load(args.arch)
        fns = functions(pe)
        info = locate_function(pe, args.func, fns)
        print(info["name"], "string_rva", hex(info["string_rva"]) if info["string_rva"] else None,
              "xrefs", [hex(x) for x in info.get("xrefs", [])])
        f = info["func"]
        if not f:
            print("no function body located:", info["note"])
            return
        print(f"FUNC [{hex(f[0])}..{hex(f[1])}] size={f[1]-f[0]}")
        for i, ins in enumerate(disasm(pe, f[0], f[1])):
            if i >= args.max:
                print("... (truncated)")
                break
            print(f"  {hex(ins.address)}: {ins.mnemonic}\t{ins.op_str}")
        return
    _self_test(args.arch)


if __name__ == "__main__":
    main()
