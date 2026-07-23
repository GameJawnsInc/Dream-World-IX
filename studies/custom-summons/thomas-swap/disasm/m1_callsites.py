"""M1 -- direct call sites of the Eff/Summon model entry points, plus .data dispatch-table slots.

Committable analysis helper; reads the user's own DLL, prints RVAs only.
"""
from __future__ import annotations
import struct
import refkit

TARGETS = {
    0x159a0: "Hi_FreeEffModel",
    0x15ac0: "Hi_RegisterSolidEffModel",
    0x15b70: "Hi_RegisterGouEffModel",
    0x15c20: "Hi_RegisterTexEffModel",
    0x15d30: "Hi_RegisterTexListModel",
    0x15e10: "Hi_RegisterTexPtrModel",
    0x15ee0: "Hi_RegisterSummonModel",
    0x16150: "Hi_DrawEffModel",
    0x16570: "Hi_DrawSliceEffModel",
    0x167f0: "Hi_DrawEffModelByBone",
    0x16cc0: "Hi_DrawMorphEffModel",
    0x17190: "Hi_DrawMorphModelByBone",
    0x17710: "Hi_DrawSummonModel",
    0x17a10: "Hi_SetSummonMotion",
    0x17a70: "Hi_SetSummonMotFrame",
    0x17ae0: "Hi_SplitMdlVertex",
    0x17b30: "Hi_GetSplitMdlVertex",
    0x18000: "Hi_GetMdlVertexPtr",
    0x185b0: "Hi_GetSummonBonePos",
    0x18630: "Hi_GetSummonBoneMatrix",
    0x187e0: "Hi_ShowSummonModelMesh",
    0x18840: "Hi_HideSummonModelMesh",
    0x188a0: "Hi_StartSummonTexAnim",
    0x18930: "Hi_StopSummonTexAnim",
    0x18990: "Hi_ModifyEffModelAbr",
    0x189f0: "Hi_ModifyEffModelRGB",
    0x18a40: "Hi_SetEffModelOffset",
    0x18a90: "Hi_SetEffModelSlice",
    0x18af0: "Hi_ModifySummonModelAbr",
    0x18b50: "Hi_ModifySummonModelRGB",
    0x18c00: "Hi_SplitMdlVertex2",
    0x15200: "eff_accessor_15200",
}


def main():
    pe = refkit.load()
    fns = refkit.functions(pe)
    base = refkit.image_base(pe)
    hits = {k: [] for k in TARGETS}
    for ins in refkit.iter_instructions(pe, fns):
        if ins.mnemonic not in ("call", "jmp"):
            continue
        op = ins.op_str
        if not op.startswith("0x"):
            continue
        try:
            t = int(op, 16) - base
        except ValueError:
            continue
        if t in hits:
            hits[t].append((ins.address - base, ins.mnemonic))
    # .data dispatch table 0x68780..0x68cf8: which slots hold these RVAs?
    tab = {}
    try:
        raw = refkit.read_rva(pe, 0x68700, 0x700)
        for i in range(0, len(raw) - 8, 8):
            va = struct.unpack_from("<Q", raw, i)[0]
            if va:
                r = va - base
                if r in TARGETS:
                    tab.setdefault(r, []).append(0x68700 + i)
    except Exception as e:  # pragma: no cover
        print("table read failed:", e)
    for rva in sorted(TARGETS):
        name = TARGETS[rva]
        cs = hits[rva]
        slots = tab.get(rva, [])
        inside = [c for c in cs if 0xeea4 <= c[0] < 0x12321]
        print(f"{name:26s} @{hex(rva):>8s} callers={len(cs):2d} "
              f"(in-interp {len(inside)}) slots={[hex(s) for s in slots]}")
        for c, mn in cs:
            tag = " [INTERP]" if 0xeea4 <= c < 0x12321 else ""
            f = refkit.func_of(fns, c)
            print(f"      {mn} from {hex(c)}  in FUNC {hex(f[0]) if f else '?'}{tag}")


if __name__ == "__main__":
    main()
