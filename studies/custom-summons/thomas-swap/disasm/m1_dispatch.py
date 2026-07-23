"""M1 -- map the .data function-pointer dispatch table to opcode indices.

Finds the contiguous run of code pointers around the known handler slots and derives
opcode = (slot - tableBase)/8. Committable analysis helper; prints RVAs only.
"""
from __future__ import annotations
import struct
import refkit

NAMED = {
    0x159a0: "Hi_FreeEffModel", 0x15ac0: "Hi_RegisterSolidEffModel",
    0x15b70: "Hi_RegisterGouEffModel", 0x15c20: "Hi_RegisterTexEffModel",
    0x15d30: "Hi_RegisterTexListModel", 0x15e10: "Hi_RegisterTexPtrModel",
    0x15ee0: "Hi_RegisterSummonModel", 0x16150: "Hi_DrawEffModel",
    0x16570: "Hi_DrawSliceEffModel", 0x167f0: "Hi_DrawEffModelByBone",
    0x16cc0: "Hi_DrawMorphEffModel", 0x17190: "Hi_DrawMorphModelByBone",
    0x17710: "Hi_DrawSummonModel", 0x17a10: "Hi_SetSummonMotion",
    0x17a70: "Hi_SetSummonMotFrame", 0x17ae0: "Hi_SplitMdlVertex",
    0x17b30: "Hi_GetSplitMdlVertex", 0x18000: "Hi_GetMdlVertexPtr",
    0x185b0: "Hi_GetSummonBonePos", 0x18630: "Hi_GetSummonBoneMatrix",
    0x187e0: "Hi_ShowSummonModelMesh", 0x18840: "Hi_HideSummonModelMesh",
    0x188a0: "Hi_StartSummonTexAnim", 0x18930: "Hi_StopSummonTexAnim",
    0x18990: "Hi_ModifyEffModelAbr", 0x189f0: "Hi_ModifyEffModelRGB",
    0x18a40: "Hi_SetEffModelOffset", 0x18a90: "Hi_SetEffModelSlice",
    0x18af0: "Hi_ModifySummonModelAbr", 0x18b50: "Hi_ModifySummonModelRGB",
    0x18c00: "Hi_SplitMdlVertex2", 0x15200: "Hi_DebugPSGData",
    0x47290: "reg_effmodel_auto", 0x47330: "reg_summonmodel_blob",
}


def main():
    pe = refkit.load()
    base = refkit.image_base(pe)
    text = next(s for s in pe.sections if s.Name.startswith(b".text"))
    lo, hi = text.VirtualAddress, text.VirtualAddress + text.Misc_VirtualSize
    start, size = 0x68000, 0x1400
    raw = refkit.read_rva(pe, start, size)
    ptrs = []
    for i in range(0, size - 8, 8):
        va = struct.unpack_from("<Q", raw, i)[0]
        r = va - base
        ptrs.append((start + i, r if (va and lo <= r < hi) else None))
    # longest contiguous run of valid code pointers
    best = (0, 0, 0)
    run_start = None
    for j, (slot, r) in enumerate(ptrs):
        if r is not None:
            if run_start is None:
                run_start = j
        else:
            if run_start is not None and j - run_start > best[0]:
                best = (j - run_start, run_start, j)
            run_start = None
    if run_start is not None and len(ptrs) - run_start > best[0]:
        best = (len(ptrs) - run_start, run_start, len(ptrs))
    n, a, b = best
    tbl_base = ptrs[a][0]
    print(f"dispatch table: base RVA {hex(tbl_base)} .. {hex(ptrs[b-1][0]+8)}  slots={n}")
    for j in range(a, b):
        slot, r = ptrs[j]
        nm = NAMED.get(r)
        if nm:
            print(f"  opcode 0x{(slot - tbl_base)//8:02x} ({(slot - tbl_base)//8:3d})  "
                  f"slot {hex(slot)} -> {hex(r)}  {nm}")


if __name__ == "__main__":
    main()
