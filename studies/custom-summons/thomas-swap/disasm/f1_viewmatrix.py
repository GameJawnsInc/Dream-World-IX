"""f1_viewmatrix.py -- FORMAT.md section 1 reproduction: the summon's WORLD->SCREEN stage.

Proves, from the user's own installed FF9SpecialEffectPlugin.dll (read-only, RVAs only):

  1. SFX_Update (export @0x1d60) tail-jumps its body @0x13a0; every tick it copies the installed
     PSX camera (32 B @RVA 0x69730) verbatim into the DLL global VIEW MATRIX @RVA 0x1C1DC8,
     publishes that global's PSX address into psxCtx[+0x14] (psxCtx = qword @RVA 0x66c68), and
     installs the GTE screen params OFX=160 @0x211fa0, OFY=120 @0x211fa4, H @0x211fa8.
  2. Both per-mesh engines re-load *resolve(psxCtx[+0x14]) into the GTE rot/trans registers and
     compose it with each bone matrix -- so bones[] are WORLD matrices and this is the view stage.
  3. The projection is GTE RTPS @0x3e80: SX = OFX + ((IR1 * ((H<<16)/SZ3)) >> 16), same for SY.

Usage:  py f1_viewmatrix.py
"""
import struct
import refkit

BASE = 0x180000000
CAM_RVA   = 0x69730     # installed PSX camera MATRIX (32 B: 9x s16 fp12, pad, 3x s32 trans)
VIEW_RVA  = 0x1C1DC8    # the DLL global VIEW matrix -- the copy the draw path actually consumes
PSXCTX    = 0x66C68     # qword -> PsxCtx; PsxCtx+0x14 = PSX address of VIEW_RVA
OFX, OFY, H = 0x211FA0, 0x211FA4, 0x211FA8


def show(pe, lo, hi, want):
    for ins in refkit.disasm(pe, lo, hi):
        rva = ins.address - BASE
        if rva in want:
            print(f"  {hex(rva):>9s}: {ins.mnemonic}\t{ins.op_str}\t; {want[rva]}")


def main():
    pe = refkit.load()
    fns = refkit.functions(pe)

    exp = refkit.exports(pe)
    assert exp["SFX_Update"] == 0x1d60, exp["SFX_Update"]
    sec = [s for s in pe.sections if s.Name.rstrip(b"\x00") == b".text"][0]
    d = sec.get_data()
    i = 0x1d60 - sec.VirtualAddress
    assert d[i] == 0xE9 and sec.VirtualAddress + i + 5 + struct.unpack("<i", d[i + 1:i + 5])[0] == 0x13a0
    print("SFX_Update export 0x1d60 -> jmp 0x13a0  (body 0x13a0..0x1610; INVISIBLE to .pdata xrefs)")

    print("\n[1] SFX_Update body -- per-tick camera snapshot + GTE screen params:")
    show(pe, 0x13a0, 0x1610, {
        0x13ac: "gate: effect state word[0x323170] != -1",
        0x1452: "rdx = &VIEW matrix (RVA 0x1C1DC8)",
        0x145f: "call 0x12940 = host -> PSX address",
        0x1464: "rcx = [0x66c68] = PsxCtx",
        0x1475: "PsxCtx[+0x14] = psx(&VIEW)      <== the pointer the draw path reads",
        0x14ea: "xmm2 = camera[+0x10..0x1f]  (m22, TRX, TRY, TRZ)",
        0x14f1: "xmm0 = camera[+0x00..0x0f]  (m00..m21)",
        0x14f8: "OFX = 160",
        0x1502: "OFY = 120",
        0x150c: "VIEW[0x00] = camera rot      <== the 32-byte verbatim camera copy",
        0x151a: "VIEW[0x10] = camera trans",
        0x1536: "eax = camera H (word @0x69750)",
        0x1542: "GTE H = camera H",
        0x15e4: "call 0x30d50 = run the effect tick (all Draws happen below here)",
        0x1601: "*outFrameIndex = ++tick   (the `ref SFX.frameIndex` out-param)",
    })

    print("\n[2] Hi_DrawSummonModel -> 0x4eb0 per-bone pass -- compose VIEW with each bone matrix:")
    show(pe, 0x4ff9, 0x5544, {
        0x5178: "rbx = [0x66c68] = PsxCtx",
        0x5186: "ecx = PsxCtx[+0x14] = PSX ptr to VIEW",
        0x51fa: "call 0x3b60 MulMatrix(VIEW, bones[i], local)   -> local.R = M.R * bone.R",
        0x5295: "GTE R <- VIEW.R",
        0x5327: "GTE T <- VIEW.t",
        0x5376: "GTE V0 <- bones[i].t",
        0x5390: "call 0x3d60 RotTrans  -> M.R*bone.t + M.t",
        0x53a1: "GTE R <- local (= M.R * bone.R)",
        0x53bf: "GTE T <- the RotTrans result   <== the model-view actually fed to RTPS",
    })

    print("\n[3] the shared emitter 0x56c0 installs the same VIEW:")
    show(pe, 0x56c0, 0x58f9, {
        0x56cd: "rdi = [0x66c68] = PsxCtx",
        0x576d: "GTE R <- (*PsxCtx[+0x14]).R",
        0x579a: "ecx = PsxCtx[+0x14]",
        0x57fd: "GTE T <- (*PsxCtx[+0x14]).t",
    })

    print("\n[4] GTE RotTransPers 0x3e80 -- the exact screen mapping:")
    show(pe, 0x3e80, 0x40c1, {
        0x3f79: "IR1 = sat16(MAC1)",
        0x3f91: "IR2 = sat16(MAC2)",
        0x3fef: "SZ3 = clamp(MAC3, 0, 0xffff)",
        0x400d: "eax = H",
        0x4017: "H << 16",
        0x401b: "q = (H<<16) / SZ3",
        0x4035: "IR1 * q",
        0x4039: ">> 16",
        0x403d: "+ OFX",
        0x4052: "-> SX",
        0x4065: "+ OFY",
    })

    print("\n[5] who else can move the screen params (a probe must log them, not assume 160/120):")
    idx = refkit.xref_index(pe, OFX, 0x211fb4, fns)
    for t in sorted(idx):
        for (fr, m, o) in idx[t]:
            f = refkit.func_of(fns, fr)
            print(f"  {hex(t)} <- {hex(fr)} in fn {hex(f[0]) if f else '??'}   {m} {o}")


if __name__ == "__main__":
    main()
