"""Independent raw disassembly of the RotMatrix builders + matmul + node chain.
ADVERSARIAL VERIFY: does NOT reuse euler_validate.confirm_disasm(). Own code path, own import
resolution. Reads the user's own DLL read-only via refkit. Prints RVAs/mnemonics only.
"""
from __future__ import annotations
import sys
from pathlib import Path

_DISASM = Path(__file__).resolve().parents[2] / "disasm"
sys.path.insert(0, str(_DISASM))
import refkit  # noqa: E402


def build_import_map(pe, base):
    imp = {}
    if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
        for mod in pe.DIRECTORY_ENTRY_IMPORT:
            dll = mod.dll.decode(errors="replace")
            for f in mod.imports:
                if f.address is None:
                    continue
                name = f.name.decode(errors="replace") if f.name else f"ord{f.ordinal}"
                imp[f.address - base] = (dll, name)
    return imp


def resolve_thunk(pe, base, imp, thunk_rva):
    """A thunk stub is `jmp qword [rip+X]`. Resolve the import it points at."""
    for ins in refkit.disasm(pe, thunk_rva, thunk_rva + 8):
        t = refkit._rip_target(ins, base)
        if t is not None:
            return imp.get(t), ("%s %s" % (ins.mnemonic, ins.op_str)), t
        return None, ("%s %s" % (ins.mnemonic, ins.op_str)), None
    return None, None, None


def dump(pe, base, imp, lo, hi, label):
    print(f"\n===== {label}  [0x{lo:x} .. 0x{hi:x}) =====")
    for ins in refkit.disasm(pe, lo, hi):
        rva = ins.address - base
        note = ""
        # annotate call targets
        if ins.mnemonic == "call":
            try:
                tva = int(ins.op_str, 16)
                trva = tva - base
                note = f"   -> rva 0x{trva:x}"
                name, stub, imprva = resolve_thunk(pe, base, imp, trva)
                if name:
                    note += f"  THUNK {stub}  == {name[0]}!{name[1]}"
                elif stub and "rip" in stub:
                    note += f"  ({stub})"
            except ValueError:
                pass
        # annotate rip-relative data refs
        rt = refkit._rip_target(ins, base)
        if rt is not None and ins.mnemonic != "call":
            note += f"   [rip->0x{rt:x}]"
            if rt in imp:
                note += f" import {imp[rt][0]}!{imp[rt][1]}"
        print(f"  0x{rva:04x}: {ins.mnemonic:8s} {ins.op_str}{note}")


def main():
    pe = refkit.load("x64")
    base = refkit.image_base(pe)
    imp = build_import_map(pe, base)
    print(f"image_base=0x{base:x}  imports={len(imp)}")
    # a couple of msvcr imports for sanity
    for rva, (d, n) in sorted(imp.items()):
        if n in ("cos", "sin", "tan", "sqrt", "atan2"):
            print(f"  import @IATrva 0x{rva:x}: {d}!{n}")

    dump(pe, base, imp, 0x37a0, 0x3850, "Rx builder 0x37a0")
    dump(pe, base, imp, 0x3850, 0x3910, "Ry builder 0x3850")
    dump(pe, base, imp, 0x3910, 0x39d0, "Rz builder 0x3910")
    dump(pe, base, imp, 0x3450, 0x3799, "matmul 0x3450 (full body)")
    dump(pe, base, imp, 0x7d40, 0x7dc0, "node builder chain 0x7d40..0x7dc0")


if __name__ == "__main__":
    main()
