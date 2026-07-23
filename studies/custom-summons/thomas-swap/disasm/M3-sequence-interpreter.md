# M3 — THE NATIVE SEQUENCE / OPCODE INTERPRETER (the choreography stream)

**Slice M3 of the FF9SpecialEffectPlugin.dll summon-cutscene disasm round.** All RVAs image-base-relative
(x64 `ImageBase 0x180000000`; x86 `0x10000000`). Every claim below is reproducible from the user's own
installed DLL with `refkit.py` + the helper scripts named at the end. **Read-only static analysis; no DLL
was modified, no game bytes were extracted.**

---

## 0. HEADLINE — the prior round's model of this layer was structurally wrong, and the correction is good news for the ops we wanted

The prior round called `0xeea4..0x12321` "a mega-interpreter that executes the effect's command stream."
It is not an interpreter over a `.seq`-style command stream. It is the **HLE syscall dispatcher of a
PlayStation MIPS-R3000 interpreter**:

- The real dispatcher entry is **`0xee80`**, not `0xeea4` (`0xeea4` is the continuation after the bound
  check). Signature: `int nativeCall(PsxCtx* ctx /*rcx*/, int opcode /*edx*/)`.
- **`0xee98: cmp edx, 0xd7 / ja 0x12321`** → the opcode space is exactly **0..0xD7 = 216 ops**.
- Dispatch is an MSVC **image-relative jump table at `.text` RVA `0x12358`, 216 dword entries**
  (`0xeeb8: lea rcx,[rip-0xeebf]` → `rcx = ImageBase`; `0xeec3: movsxd rax,edx`;
  `0xeec6: mov edx,[rcx+rax*4+0x12358]`; `0xeecd: add rdx,rcx`; `0xeed0: jmp rdx`).
  The table ends at `0x126b8`, followed by `0xCCCCCCCC` padding.
- A **parallel `.data` function-pointer table at `0x68780`** is indexed by the *same* opcode number,
  216 entries, ending exactly at `0x68e40` (the next qwords are RTTI `.rdata` pointers). It names the
  primary native function each opcode calls. Slot **20 is NULL** in both builds.
- The opcode number itself is produced one level down, by a **MIPS `JAL` to the magic address
  `0xFF000000 | op`** — see §3.

**What this buys us immediately:** the explicitly-open item is answered. The native per-mesh hide/show
opcodes are **157 (`Hi_ShowSummonModelMesh`) and 158 (`Hi_HideSummonModelMesh`)**, with the whole summon
roster pinned to concrete opcode numbers (§2). **What it costs us:** there is no "wait N frames" opcode and
no authorable command stream at this layer — the choreography's *timing and control flow are MIPS machine
code*, not data (§3, §6). That reshapes the re-import roadmap and is the single most important finding here.

---

## 1. THE DISPATCH + OPERAND MECHANISM (CONFIRMED, cross-arch)

### 1.1 Two independent tables agree, 12/12

| fn | native body | interp call site | jump-table op | `.data` table op | agree |
|---|---|---|---|---|---|
| Hi_StopSummonTexAnim | 0x18930 | 0xf408 | 11 | 11 | ✓ |
| Hi_StartSummonTexAnim | 0x188a0 | 0xf439 | 12 | 12 | ✓ |
| Hi_RegisterSummonModel | 0x15ee0 | 0xf75a | 23 | 23 | ✓ |
| Hi_DrawSummonModel | 0x17710 | 0xf851 | 25 | 25 | ✓ |
| Hi_SetSummonMotion | 0x17a10 | 0xf87e | 26 | 26 | ✓ |
| Hi_ModifySummonModelRGB | 0x18b50 | 0x10106 | 65 | 65 | ✓ |
| Hi_SetSummonMotFrame | 0x17a70 | 0x10d6a | 100 | 100 | ✓ |
| Hi_ModifySummonModelAbr | 0x18af0 | 0x1157a | 147 | 147 | ✓ |
| Hi_GetSummonBonePos | 0x185b0 | 0x115cb | 149 | 149 | ✓ |
| **Hi_ShowSummonModelMesh** | 0x187e0 | 0x117df | **157** | **157** | ✓ |
| **Hi_HideSummonModelMesh** | 0x18840 | 0x11806 | **158** | **158** | ✓ |
| Hi_GetSummonBoneMatrix | 0x18630 | 0x1195a | 164 | 164 | ✓ |

Reproduce: `py m3_op.py` (in the scratch set; the logic is 20 lines — see §8).

### 1.2 The x86 build reproduces the table byte-for-byte in *meaning*

The 32-bit DLL has the same 216-entry op→fn table at **RVA `0x50e18`**, with **the same NULL at slot 20**
and the same functions at the same indices:

| op | x64 fn | x86 fn | independent confirmation |
|---|---|---|---|
| 23 | 0x15ee0 | 0x13080 | B5's `Hi_RegisterSummonModel@0x13080` |
| 25 | 0x17710 | 0x13ce0 | B5's Draw internals @0x13d24/0x13e33/0x13e6b |
| 26 | 0x17a10 | 0x13f40 | B5's SetMotion zeroes `word[rec+0x50]` @0x13f5c |
| **157** | 0x187e0 | **0x14730** | contains `and [..+0x14], ~bit` @0x14756 (B5's x86 hideMask offset) |
| **158** | 0x18840 | **0x14780** | contains `or  [..+0x14],  bit` @0x147a4 |

Different compiler, different calling convention, different pointer size — same opcode numbers. This is
the strongest evidence class available for a static claim.

### 1.3 Operand access — VERIFIED, and the prior note's "`0x126c0` operand reader" was half the story

There are **two** operand readers, and they are MIPS argument-register accessors:

```c
// 0x126c0  getArgInt(PsxCtx* ctx, int n)
// 0x12740  getArgPtr(PsxCtx* ctx, int n)   == psxptr(ctx->mapper, getArgInt(ctx,n)), NULL for 0
int getArgInt(PsxCtx* ctx, int n) {
    long r = ctx->curThread /*ctx+0xda0*/ << 7;          // register file stride 0x80
    switch (n) {
      case 0: return *(i32*)(ctx + r + 0xca8);           // GPR[4]  = $a0
      case 1: return *(i32*)(ctx + r + 0xcac);           // GPR[5]  = $a1
      case 2: return *(i32*)(ctx + r + 0xcb0);           // GPR[6]  = $a2
      case 3: return *(i32*)(ctx + r + 0xcb4);           // GPR[7]  = $a3
      default: {                                          // O32 stack args
        u32 sp = *(u32*)(ctx + r + 0xd0c);               // GPR[29] = $sp
        return ((i32*)psxptr(ctx->mapper, sp))[n];       // *(sp + n*4)  -> arg4 at sp+16
      }
    }
}
```

`psxptr` = **`0x10e0`** = `PsxVirtualAddrMapper64::resolve(mapper, psxAddr)`:
`addr>>24 == 0x80` → main RAM (`mapper[+0x1fd0] + addr - mapper[+0x1fc8]`);
`(addr & 0xC00000) == 0xC00000` and `addr>>24 > 0` → bank table `mapper[8 + (addr>>24)*0x20]` + `addr & 0x3FFFFF`;
else the `0x1F800000` scratchpad window. **Every pointer-shaped operand in this whole system is a PSX
32-bit virtual address**, not a host pointer.

**The return value goes to `$v0`.** The dispatcher's epilogue tail (`0x12321`) does
`mov r8d, r12d; mov edx, 2; rcx = &GPR[curThread]; jmp 0xd510` — i.e. `setReg(regfile, 2 /*$v0*/, ret)`.

### 1.4 The `PsxCtx` layout, derived from the init at `0xd5d0` (CONFIRMED, self-consistent)

| offset | thing | evidence |
|---|---|---|
| `+0xc18` | `VMThread[2]`, stride **0x40** | `0xd60b: add rcx,0xc18` + `edx=0x40, r8d=2` array-init call `0x4940c` |
| ↳ `+0x18` (`0xc30`) | code base = host ptr to decoded instruction 0 | `0xe240: mov rax,[..+0xc30]` |
| ↳ `+0x20` (`0xc38`) | PSX PC, **signed byte offset**; `< 0` ends the frame | `0xe25c: add dword [..+0xc38],4` |
| ↳ `+0x28` (`0xc40`) | host instruction pointer (16 B/instr) | `0xe264: lea rax,[rbx+0x10]` |
| `+0xc98` | **MIPS register file GPR[32] × 2 threads**, stride **0x80** | `0xe239: lea r14,[rsi+0xc98]`, then `<<7` by tid; ops index `[r14 + reg*4]` |
| `+0xd98` | `PsxVirtualAddrMapper64*` | `0xd66f: mov [r14+0xd98], r12` |
| `+0xda0` | current thread id (init **-1**), values {0,1} | `0xd676`; loop `cmp ebp,2; jl` @`0xd6e8` |
| `+0xda8` | code-region descriptor ptr[] | `0xd6f0`, written by `0x3e21c` |
| `+0xdb8 + tid*0x1000` | 4 KB per-thread MIPS stack (registered in the mapper → `$sp`) | `0xd6b6`+`call 0x12940`; result stored to `[ctx+0xd0c+tid*0x80]` = **GPR[29]** @`0xd6de` |
| `+0x2db8 / +0x2dc0` | MIPS `LO` / `HI` per thread | VM ops 9/10 and 7/8 |
| `+0x2dc8` | pending-branch flag `u8[2]` (**the branch delay slot**) | `0xec0d`, set by VM op 0x32 |
| `+0x2dcc` | pending-branch target `s32[2]` | `0xec1b`, set by VM op 0x32 |

The "arg0..arg3" fields at `rec+0x10..0x1c` are exactly `$a0..$a3`, `rec+0x74` is exactly `$sp`, and the
spill read `psxptr($sp)[n]` puts arg4 at `$sp+16` — **the MIPS O32 calling convention, byte for byte.**
That agreement is the reason to trust this layout.

---

## 2. THE OPS THAT MATTER FOR STAGING / AUTHORING (exact semantics)

All verified by disassembling the native body, and every arity independently confirmed by the x86
build's `cdecl` `[ebp+N]` frame (§4).

| op | call | semantics (native body) |
|---:|---|---|
| **23** | `Hi_RegisterSummonModel($a0 = modelPtr, $a1 = ?)` | `0x15ee0`: free-slot loop bounded `cmp eax,1` → **slot 0 only**; sets `rec+0x50 = 1`, `rec+0x54 = 0`, `data->modelId = modelPtr[0x3c]`. Returns the slot index in `$v0`. |
| **25** | `Hi_DrawSummonModel($a0,$a1,$a2, $a3 = slot, arg4)` | `0x17710` validator: `slot = r9d`, `imul 0x58`, gate `rec+0x50` then `rec+0x00`. **5 args** (arg4 read from `$sp+16` at `0xf804: mov ebp,[rax+0x10]`, pushed at `0xf84d: mov [rsp+0x20],ebp`) — x86 arity 5 agrees. `$a0..$a2` are PSX pointers (the rot/trans/scale vectors per B1/B3). |
| **26** | `Hi_SetSummonMotion($a0 = motionPtr, $a1 = slot)` | `0x17a10`: `rec+0x54 = 0` **then** `data->motion(+0x10) = $a0`. Binding a motion always rewinds the frame counter. |
| **100** | `Hi_SetSummonMotFrame($a0 = slot, $a1 = frame)` | `0x17a70`: `if (motion->frameCount /*u16 @+2*/ >= frame) rec+0x54 = frame; else rec+0x54 = 0;` — **an out-of-range seek WRAPS TO 0, it does not clamp to the last frame.** (Note the comparison is `>=`, so `frame == frameCount` is accepted.) |
| **157** | `Hi_ShowSummonModelMesh($a0 = slot, $a1 = meshOrdinal)` | `0x187e0`: `data->hideMask(+0x20) &= ~(1 << meshOrdinal)` |
| **158** | `Hi_HideSummonModelMesh($a0 = slot, $a1 = meshOrdinal)` | `0x18840`: `data->hideMask(+0x20) \|= (1 << meshOrdinal)` |
| **11** | `Hi_StopSummonTexAnim($a0 = slot, $a1 = part)` | `0x18930` |
| **12** | `Hi_StartSummonTexAnim($a0 = slot, $a1 = part, $a2 = flag)` | `0x188a0`; the handler passes `r8b = ($a2 != 0)` (`0xf435: setne r8b`) — **arg2 is a BOOL, not a value** |
| **147** | `Hi_ModifySummonModelAbr($a0, $a1)` | `0x18af0`; x86 head shows the `0xff` = no-op early-out |
| **65** | `Hi_ModifySummonModelRGB($a0,$a1,$a2,$a3)` | `0x18b50` |
| **149** | `Hi_GetSummonBonePos($a0 = slot, $a1 = bone, $a2 = out*)` | `0x185b0`; `$a2` is a PSX out-pointer (`getArgPtr`) |
| **164** | `Hi_GetSummonBoneMatrix($a0 = slot, $a1 = bone, $a2 = out*)` | `0x18630`; `$a2` via `getArgPtr` |
| **151** | `Hi_FreeEffModel($a0)` | `0x159a0` |
| 6/19/21/22/171 | `Hi_Register{Gou,TexList,Solid,Tex,TexPtr}EffModel` | the 32-slot EFFARR family (`0x220230`, stride 0x30) |
| 24/162/163/145/199 | `Hi_Draw{EffModel,EffModelByBone,MorphEffModel,MorphModelByBone,SliceEffModel}` | the EFFARR draw family |
| 154/155/185/200 | `Hi_Modify{EffModelAbr,EffModelRGB}` / `Hi_SetEffModel{Offset,Slice}` | EFFARR dressing |

**Relevance to the EFFARR hypothesis handed to this round:** the opcode table shows the summon family
(ops 11,12,23,25,26,65,100,147,149,157,158,164) and the eff-model family (ops 6,19,21,22,24,145,151,154,
155,162,163,171,185,191,193,196,198,199,200,206) are **two co-equal, simultaneously available op sets**.
Nothing in the dispatcher privileges one. So "which array is Bahamut drawn through" is decided *by the
effect program*, i.e. by which opcodes ef###.bytes' MIPS code actually executes — it is **not statically
decidable from this table** and must be answered by runtime instrumentation (§7, R1).

## 3. WHERE THE OPCODE NUMBER COMES FROM — the MIPS VM one level down (CONFIRMED)

The executor is **`0xe210`** (`.pdata` `0xe210..0xe240` = prologue, `0xe240..0xed18` = the body/switch).

```
0xe210  rsi = ctx ; rcx = ctx->curThread ; r15 = ImageBase ; r14 = &GPR[curThread]  (ctx+0xc98 + tid*0x80)
0xe250  LOOP: rbx = thread->hostPC ; thread->psxPC += 4 ; thread->hostPC += 0x10
0xe270        eax = *(u16*)rbx ; eax-- ; if (eax > 0x59) goto post       // 90 opcodes, 1..0x5A
0xe280        jmp ImageBase + *(u32*)(ImageBase + eax*4 + 0xed18)        // 2nd image-relative table
0xebfb  post: if (*(u16*)(rbx+2) == 0 && ctx->pendFlag[tid]) {           // the BRANCH DELAY SLOT
0xec1b          v = ctx->pendTarget[tid]; ctx->pendFlag[tid] = 0;
0xec31          if ((v & 0xFF000000) == 0xFF000000)  nativeCall(ctx, v & 0x3FFFFF);   // <-- 0xec41
0xec4b          else if (v < 0)  { map absolute PSX addr -> region-relative offset }
0xecaf          else { thread->hostPC = codeBase + (v>>2)*0x10 ; thread->psxPC = v - 4 ; }
              }
0xecdf  if (thread->psxPC >= 0) goto LOOP;  else return;                 // frame ends when psxPC < 0
```

- **Instruction format: 16 bytes** — `{u16 opcode, u16 delaySlotFlag, s32 dst, s32 srcA, s32 srcB}`.
  One PSX word ↔ one host record: `(v>>2)*0x10` (`0xec8a`/`0xecb9`).
- **VM opcode census (jump table at `.text 0xed18`, 90 entries, opcode = index+1):** ALU
  (`sllv/srlv/srav/add/and/xor/sub/nor/or` @0xe28d-0xe4d1), `mult/multu/div/divu` writing `HI/LO`
  (0xe594-0xe66f), immediate forms + `LUI` (`shl ecx,0x10` @0xe85b), loads/stores through `psxptr`
  (0xe6c8-0xe801), **`J/JAL` = ops 0x32 and 0x3C** (`0xe88f`: set `pendFlag=1`, `pendTarget=imm`),
  **`$ra = PC+8` = op 0x33** (`0xe876`: writes `[r14+0x7c]` = GPR[31]), branches
  `beq/bne/bgez/bltz/blez/bgtz` (0xe8b4-0xe9ab), COP register move via a 64-slot file at RVA `0x211f40`
  (ops 0x3F/0x40), **GTE command dispatch = op 0x41** (`0xeacd`, `cmp eax,0x780010 / 0x158002d /
  0x1400006 / 0x180001` → calls the GTE at `0x3e80` and `0x4b50`), **frame yield = op 0x42**
  (`0xebd5`: `psxPC = -4`, `hostPC = codeBase` → the loop test fails and the executor returns, with the
  program rewound to its entry), and ops 0x43..0x58 are all NOPs.

### 3.1 The consequence for authoring — state it plainly

- **There is no `wait`/`hold N frames` opcode.** Ops 20/27/36/41/133/194/209/214 route to the default
  return; `0x182c0` is literally `ret` and `0x2fd0` is `xor eax,eax; ret`. Nothing in the 216-op table
  touches the frame counter or the thread PC.
- **There is no camera opcode.** No opcode function reaches the installed PSX camera struct `0x69730`
  within a depth-5 call closure; its only writers are `0x13c4`, `0x1644`, `0x1800`, `0x1e80`
  (`SFX_UpdateCamera`'s body), `0x2300`, `0x30c20`, `0x30d50`, `0x3de37` — all on the
  `SFX_Play`/`SFX_UpdateCamera` side, not the HLE side. This **ratifies** FINDINGS §5: the summon camera
  is a data-driven keyframe track, not an op in this stream.
- **Timing and choreography are MIPS control flow**, executed 16 bytes at a time by `0xe210`, and one
  "frame" of a summon = one call of that executor until VM op 0x42 fires.

---

## 4. THE FULL 216-OPCODE TABLE

`handler` = the x64 jump-table target inside `[0xee80,0x12358)`. `native fn x64/x86` = the parallel
`.data` op→fn tables (`0x68780` / `0x50e18`). `args` = **arity taken from the x86 `cdecl` frame**
(`max([ebp+N]) → (N-8)/4 + 1`); a leading `~` means the x86 body has no `ebp` frame and the count is the
x64 handler-derived one instead. `kinds`: `i` = integer operand, `p` = PSX pointer operand (routed through
`psxptr`/`getArgPtr`), `.` = a slot the handler does not read, `-` = no operands. 172 of the 192
frame-bearing functions agree exactly between the two independent derivations; the ~20 that differ are
listed in §5 and are all cases where the *handler* reads fewer operands than the callee declares.

| op | hex | handler (x64) | native fn x64 | native fn x86 | args | kinds | name / notes |
|---:|---:|---|---|---|---:|---|---|
| 0 | 0x00 | 0x0eed2 | 0x02cd0 | 0x02980 | 2 | `ii` |  |
| 1 | 0x01 | 0x0ef2b | 0x02d20 | 0x029d0 | 2 | `ii` |  |
| 2 | 0x02 | 0x0ef84 | 0x2fc80 | 0x24a10 | 4 | `iiii` |  |
| 3 | 0x03 | 0x0f007 | 0x40340 | 0x2f830 | 12 | `iiii` | GTE_RotTransPers |
| 4 | 0x04 | 0x0f145 | 0x47260 | 0x33ea0 | 1 | `i` |  |
| 5 | 0x05 | 0x0f162 | 0x039d0 | 0x035a0 | 2 | `ii` |  |
| 6 | 0x06 | 0x0f1c8 | 0x15b70 | 0x12e00 | 1 | `i` | **Hi_RegisterGouEffModel** EFFARR |
| 7 | 0x07 | 0x0f1fe | 0x02f70 | 0x02c40 | 4 | `iiii` |  |
| 8 | 0x08 | 0x0f29e | 0x03a20 | 0x035f0 | 2 | `ii` |  |
| 9 | 0x09 | 0x0f304 | 0x03cb0 | 0x03940 | 3 | `iii` |  |
| 10 | 0x0A | 0x0f390 | 0x03250 | 0x02ee0 | 1 | `i` |  |
| 11 | 0x0B | 0x0f3ed | 0x18930 | 0x14840 | 2 | `ii` | **Hi_StopSummonTexAnim** summonRec |
| 12 | 0x0C | 0x0f412 | 0x188a0 | 0x147d0 | 3 | `iii` | **Hi_StartSummonTexAnim** summonRec |
| 13 | 0x0D | 0x0f443 | 0x03280 | 0x02f10 | 1 | `i` |  |
| 14 | 0x0E | 0x0f48e | 0x03190 | 0x02e00 | 1 | `i` |  |
| 15 | 0x0F | 0x0f4cf | 0x031d0 | 0x02e40 | 1 | `i` |  |
| 16 | 0x10 | 0x0f510 | 0x03210 | 0x02e80 | 2 | `ii` |  |
| 17 | 0x11 | 0x0faec | 0x032a0 | 0x02f30 | 1 | `i` |  |
| 18 | 0x12 | 0x0f565 | 0x030b0 | 0x02d60 | 5 | `iiii` |  |
| 19 | 0x13 | 0x0f5f8 | 0x15d30 | 0x12f50 | 3 | `iii` | **Hi_RegisterTexListModel** EFFARR |
| 20 | 0x14 | `(default exit)` | 0x00000 | 0x00000 | ~0 | `-` | **NULL slot** (opcode unimplemented in both builds) |
| 21 | 0x15 | 0x0f684 | 0x15ac0 | 0x12d80 | 1 | `i` | **Hi_RegisterSolidEffModel** EFFARR |
| 22 | 0x16 | 0x0f6ba | 0x15c20 | 0x12e90 | 5 | `iiii` | **Hi_RegisterTexEffModel** EFFARR |
| 23 | 0x17 | 0x0f724 | 0x15ee0 | 0x13080 | 2 | `pi` | **Hi_RegisterSummonModel** summonRec |
| 24 | 0x18 | 0x0f767 | 0x16150 | 0x131d0 | 4 | `piii` | **Hi_DrawEffModel** EFFARR |
| 25 | 0x19 | 0x0f7da | 0x17710 | 0x13ce0 | 5 | `piii` | **Hi_DrawSummonModel** summonRec |
| 26 | 0x1A | 0x0f85e | 0x17a10 | 0x13f40 | 2 | `pi` | **Hi_SetSummonMotion** summonRec |
| 27 | 0x1B | `(default exit)` | 0x182c0 | 0x143e0 | ~0 | `-` | EMPTY BODY (`ret`) - registered no-op |
| 28 | 0x1C | 0x0f888 | 0x15940 | 0x12c00 | 2 | `pi` |  |
| 29 | 0x1D | 0x0f8c2 | 0x15a20 | 0x12cc0 | 2 | `pi` |  |
| 30 | 0x1E | 0x0f8ec | 0x159f0 | 0x12ca0 | ~0 | `-` |  |
| 31 | 0x1F | 0x0f906 | 0x15aa0 | 0x12d60 | ~0 | `-` |  |
| 32 | 0x20 | 0x0f919 | 0x182d0 | 0x143f0 | 3 | `iii` |  |
| 33 | 0x21 | 0x0f96e | 0x18340 | 0x14430 | 3 | `iii` |  |
| 34 | 0x22 | 0x0f9c3 | 0x1b380 | 0x16b90 | 2 | `ii` |  |
| 35 | 0x23 | 0x0fa07 | 0x1b4a0 | 0x16c50 | 2 | `.i` |  |
| 36 | 0x24 | `(default exit)` | 0x02fd0 | 0x02c90 | ~0 | `-` | STUB (`xor eax,eax; ret`) |
| 37 | 0x25 | 0x0fa33 | 0x1bab0 | 0x17070 | ~0 | `-` |  |
| 38 | 0x26 | 0x0fa3c | 0x1b4b0 | 0x16c60 | 2 | `ii` |  |
| 39 | 0x27 | 0x0fa63 | 0x1b560 | 0x16cf0 | 1 | `i` |  |
| 40 | 0x28 | 0x0fa7c | 0x1b240 | 0x16ab0 | 2 | `ii` |  |
| 41 | 0x29 | `(default exit)` | 0x182c0 | 0x143e0 | ~0 | `-` | EMPTY BODY (`ret`) - registered no-op |
| 42 | 0x2A | 0x0faa3 | 0x1b310 | 0x16af0 | 2 | `ii` |  |
| 43 | 0x2B | 0x0face | 0x3d660 | 0x2daf0 | 1 | `i` |  |
| 44 | 0x2C | 0x0faec | 0x032a0 | 0x02f30 | 1 | `i` |  |
| 45 | 0x2D | 0x0fb0d | 0x20bd0 | 0x1aac0 | 3 | `iii` |  |
| 46 | 0x2E | 0x0fb3d | 0x20c00 | 0x1aaf0 | 4 | `iiii` |  |
| 47 | 0x2F | 0x0fb75 | 0x20c50 | 0x1ab40 | 4 | `piii` |  |
| 48 | 0x30 | 0x0fbe8 | 0x20930 | 0x1a7b0 | ~0 | `-` |  |
| 49 | 0x31 | 0x0fc08 | 0x20950 | 0x1a7d0 | 2 | `ii` |  |
| 50 | 0x32 | 0x0fc32 | 0x20980 | 0x1a810 | 1 | `i` |  |
| 51 | 0x33 | 0x0fc72 | 0x208d0 | 0x1a750 | 2 | `pp` |  |
| 52 | 0x34 | 0x0fc9f | 0x209b0 | 0x1a850 | 1 | `p` |  |
| 53 | 0x35 | 0x0fcb6 | 0x20a20 | 0x1a8c0 | 3 | `ppp` |  |
| 54 | 0x36 | 0x0fcf3 | 0x3c110 | 0x2cdf0 | 3 | `pip` |  |
| 55 | 0x37 | 0x0fd2e | 0x3c320 | 0x2cf50 | 4 | `piii` |  |
| 56 | 0x38 | 0x0fda1 | 0x3c9b0 | 0x2d2d0 | 3 | `iii` |  |
| 57 | 0x39 | 0x0fdf4 | 0x3ca00 | 0x2d320 | 3 | `ppi` |  |
| 58 | 0x3A | 0x0fe31 | 0x3cae0 | 0x2d3d0 | 2 | `pp` |  |
| 59 | 0x3B | 0x0fe5b | 0x3cce0 | 0x2d4b0 | 3 | `ppii` |  |
| 60 | 0x3C | 0x0febe | 0x3cf30 | 0x2d660 | 6 | `ppii` |  |
| 61 | 0x3D | 0x0ff4d | 0x3d170 | 0x2d7d0 | 3 | `ppi` |  |
| 62 | 0x3E | 0x0ff8a | 0x3d420 | 0x2d960 | 6 | `ppii` |  |
| 63 | 0x3F | 0x10058 | 0x3f0c0 | 0x2ec80 | 2 | `ii` |  |
| 64 | 0x40 | 0x1007f | 0x3f180 | 0x2ecc0 | 5 | `piii` |  |
| 65 | 0x41 | 0x100d7 | 0x18b50 | 0x14a20 | 4 | `iiii` | **Hi_ModifySummonModelRGB** summonRec |
| 66 | 0x42 | 0x10110 | 0x3f6f0 | 0x2f330 | 13 | `ppii` | GTE_RotTransPers |
| 67 | 0x43 | 0x1028a | 0x3fc70 | 0x2f570 | 12 | `piiiiiiii` |  |
| 68 | 0x44 | 0x103c3 | 0x40730 | 0x2fa10 | 8 | `pppiiii` |  |
| 69 | 0x45 | 0x104b4 | 0x409d0 | 0x2fb90 | 9 | `pppi` | GTE_RotTransPers |
| 70 | 0x46 | 0x105a1 | 0x40f90 | 0x2ff30 | 5 | `ppii` | GTE_RotTransPers |
| 71 | 0x47 | 0x10604 | 0x413b0 | 0x30160 | 7 | `ipii` |  |
| 72 | 0x48 | 0x10693 | 0x41670 | 0x30300 | 7 | `pppi` | GTE_RotTransPers |
| 73 | 0x49 | 0x1072f | 0x41b80 | 0x305b0 | 7 | `pppiiii` | GTE_RotTransPers |
| 74 | 0x4A | 0x107bb | 0x42180 | 0x30950 | 7 | `pppiiii` | GTE_RotTransPers |
| 75 | 0x4B | 0x10847 | 0x42be0 | 0x30f00 | 7 | `pppiiii` | GTE_RotTransPers |
| 76 | 0x4C | 0x108d3 | 0x434b0 | 0x31400 | 6 | `piiiii` |  |
| 77 | 0x4D | 0x10947 | 0x43800 | 0x317d0 | 2 | `pi` |  |
| 78 | 0x4E | 0x1096f | 0x44560 | 0x321f0 | 4 | `ppii` | GTE_RotTransPers |
| 79 | 0x4F | 0x109bd | 0x324f0 | 0x26140 | 3 | `ipp` |  |
| 80 | 0x50 | 0x109f9 | 0x32540 | 0x261c0 | 2 | `pp` |  |
| 81 | 0x51 | 0x10a23 | 0x325f0 | 0x261f0 | 1 | `p` |  |
| 82 | 0x52 | 0x10a3d | 0x34330 | 0x274b0 | 2 | `ip` |  |
| 83 | 0x53 | 0x10a66 | 0x34380 | 0x27510 | 2 | `pppp` |  |
| 84 | 0x54 | 0x10ab6 | 0x34710 | 0x27870 | 3 | `ppp` |  |
| 85 | 0x55 | 0x10af3 | 0x34820 | 0x27900 | 2 | `pp` |  |
| 86 | 0x56 | 0x10b1d | 0x34860 | 0x27950 | 2 | `pp` |  |
| 87 | 0x57 | 0x10b4a | 0x35490 | 0x28010 | 1 | `p` |  |
| 88 | 0x58 | 0x10b61 | 0x354e0 | 0x28050 | 2 | `pp` |  |
| 89 | 0x59 | 0x10b8b | 0x380c0 | 0x29c50 | 4 | `pppp` |  |
| 90 | 0x5A | 0x10bdb | 0x48800 | 0x34d80 | ~0 | `-` |  |
| 91 | 0x5B | 0x10be5 | 0x488c0 | 0x34dd0 | 2 | `pi` |  |
| 92 | 0x5C | 0x10c0d | 0x48b10 | 0x34ec0 | 4 | `iiii` |  |
| 93 | 0x5D | 0x10c58 | 0x48e70 | 0x35160 | 0 | `-` |  |
| 94 | 0x5E | 0x10c65 | 0x30780 | 0x24d30 | 2 | `ii` |  |
| 95 | 0x5F | 0x10c8f | 0x307a0 | 0x24d50 | 5 | `ipiii` |  |
| 96 | 0x60 | 0x10cef | 0x30880 | 0x24db0 | 1 | `i` |  |
| 97 | 0x61 | 0x10d05 | 0x30930 | 0x24df0 | 1 | `i` |  |
| 98 | 0x62 | 0x10d1b | 0x30a70 | 0x24eb0 | 1 | `i` |  |
| 99 | 0x63 | 0x10d34 | 0x30bd0 | 0x24f90 | 1 | `i` |  |
| 100 | 0x64 | 0x10d4d | 0x17a70 | 0x13f90 | 2 | `ii` | **Hi_SetSummonMotFrame** summonRec |
| 101 | 0x65 | 0x10d74 | 0x486a0 | 0x34cb0 | ~0 | `-` |  |
| 102 | 0x66 | 0x10d7e | 0x3d800 | 0x2dc70 | 2 | `ii` |  |
| 103 | 0x67 | 0x10da5 | 0x3daa0 | 0x2dd10 | 2 | `ii` |  |
| 104 | 0x68 | 0x10dcf | 0x3db80 | 0x2dd70 | ~0 | `-` |  |
| 105 | 0x69 | 0x10dd9 | 0x3db90 | 0x2dd80 | 0 | `i` |  |
| 106 | 0x6A | 0x10df2 | 0x3dbf0 | 0x2ddf0 | ~0 | `-` |  |
| 107 | 0x6B | 0x10dff | 0x3de20 | 0x2e020 | 0 | `-` |  |
| 108 | 0x6C | 0x10e09 | 0x313d0 | 0x253b0 | ~0 | `-` |  |
| 109 | 0x6D | 0x10e13 | 0x313f0 | 0x253d0 | 0 | `i` |  |
| 110 | 0x6E | 0x10e2c | 0x31520 | 0x25510 | 0 | `-` |  |
| 111 | 0x6F | 0x10e36 | 0x3d670 | 0x2db10 | 2 | `pi` |  |
| 112 | 0x70 | 0x10e5e | 0x3d6c0 | 0x2db60 | 2 | `pi` |  |
| 113 | 0x71 | 0x10e86 | 0x3d7a0 | 0x2dc10 | 2 | `pi` |  |
| 114 | 0x72 | 0x10eb1 | 0x3d7d0 | 0x2dc40 | 1 | `p` |  |
| 115 | 0x73 | 0x10ec8 | 0x30620 | 0x24c30 | ~0 | `-` |  |
| 116 | 0x74 | 0x10ed2 | 0x306b0 | 0x24c90 | 0 | `-` | camKeys |
| 117 | 0x75 | 0x10edc | 0x306f0 | 0x24cd0 | 2 | `pp` |  |
| 118 | 0x76 | 0x10f06 | 0x30710 | 0x24cf0 | 2 | `pp` |  |
| 119 | 0x77 | 0x10f30 | 0x30730 | 0x24d10 | 1 | `p` |  |
| 120 | 0x78 | 0x10f47 | 0x44a30 | 0x32540 | 1 | `p` |  |
| 121 | 0x79 | 0x10f5e | 0x48760 | 0x34d00 | ~0 | `-` |  |
| 122 | 0x7A | 0x10f68 | 0x48740 | 0x34ce0 | 1 | `i` |  |
| 123 | 0x7B | 0x10f7e | 0x44d50 | 0x32660 | ~0 | `-` |  |
| 124 | 0x7C | 0x10f88 | 0x44d60 | 0x32670 | 1 | `i` |  |
| 125 | 0x7D | 0x10fa1 | 0x44da0 | 0x326b0 | 1 | `i` |  |
| 126 | 0x7E | 0x10fba | 0x44dc0 | 0x326d0 | 2 | `ip` |  |
| 127 | 0x7F | 0x10fe3 | 0x44f60 | 0x32800 | 2 | `ip` |  |
| 128 | 0x80 | 0x1100c | 0x450c0 | 0x32930 | 3 | `iip` |  |
| 129 | 0x81 | 0x11046 | 0x450f0 | 0x32950 | 2 | `ip` |  |
| 130 | 0x82 | 0x1106f | 0x46320 | 0x33500 | 3 | `ippp` |  |
| 131 | 0x83 | 0x110c1 | 0x45350 | 0x32a50 | 2 | `ip` |  |
| 132 | 0x84 | 0x110ea | 0x45480 | 0x32b30 | 1 | `i` |  |
| 133 | 0x85 | `(default exit)` | 0x454a0 | 0x32b50 | 7 | `-` |  |
| 134 | 0x86 | 0x11103 | 0x457c0 | 0x32de0 | 3 | `iip` |  |
| 135 | 0x87 | 0x1113d | 0x45970 | 0x32ee0 | 2 | `ii` |  |
| 136 | 0x88 | 0x11167 | 0x45a80 | 0x32f60 | 2 | `ii` |  |
| 137 | 0x89 | 0x11191 | 0x460e0 | 0x333d0 | 2 | `ii` |  |
| 138 | 0x8A | 0x111bb | 0x46e80 | 0x33ca0 | 1 | `i` |  |
| 139 | 0x8B | 0x111d1 | 0x3efc0 | 0x2ebf0 | 4 | `iipi` |  |
| 140 | 0x8C | 0x1121d | 0x47070 | 0x33da0 | 1 | `i` |  |
| 141 | 0x8D | 0x11233 | 0x3eed0 | 0x2ebb0 | 3 | `iip` |  |
| 142 | 0x8E | 0x1126d | 0x47a00 | 0x34420 | 3 | `ppi` |  |
| 143 | 0x8F | 0x112a9 | 0x3edb0 | 0x2eb40 | 4 | `ippi` |  |
| 144 | 0x90 | 0x11307 | 0x47b40 | 0x34530 | 7 | `iiiiiii` |  |
| 145 | 0x91 | 0x1138f | 0x17190 | 0x13a00 | 6 | `piiiii` | **Hi_DrawMorphModelByBone** EFFARR |
| 146 | 0x92 | 0x11403 | 0x47e30 | 0x34640 | 14 | `iiiiiiiiipppii` | GTE_RotTransPers |
| 147 | 0x93 | 0x1155d | 0x18af0 | 0x149d0 | 2 | `ii` | **Hi_ModifySummonModelAbr** summonRec |
| 148 | 0x94 | 0x11584 | 0x484e0 | 0x34bd0 | 1 | `p` |  |
| 149 | 0x95 | 0x1159b | 0x185b0 | 0x14530 | 3 | `iip` | **Hi_GetSummonBonePos** summonRec |
| 150 | 0x96 | 0x115d5 | 0x3dae0 | 0x2dd40 | 1 | `i` |  |
| 151 | 0x97 | 0x115eb | 0x159a0 | 0x12c60 | 1 | `i` | **Hi_FreeEffModel** EFFARR |
| 152 | 0x98 | 0x11601 | 0x1b9e0 | 0x16fd0 | 2 | `ii` |  |
| 153 | 0x99 | 0x11628 | 0x3f3a0 | 0x2ef40 | 11 | `piiiiipiiii` |  |
| 154 | 0x9A | 0x11729 | 0x18990 | 0x14890 | 2 | `ii` | **Hi_ModifyEffModelAbr** EFFARR |
| 155 | 0x9B | 0x11750 | 0x189f0 | 0x148e0 | 4 | `iiii` | **Hi_ModifyEffModelRGB** EFFARR |
| 156 | 0x9C | 0x1179b | 0x1b5c0 | 0x16d40 | 2 | `ii` |  |
| 157 | 0x9D | 0x117c2 | 0x187e0 | 0x14730 | 2 | `ii` | **Hi_ShowSummonModelMesh** summonRec |
| 158 | 0x9E | 0x117e9 | 0x18840 | 0x14780 | 2 | `ii` | **Hi_HideSummonModelMesh** summonRec |
| 159 | 0x9F | 0x11810 | 0x03ab0 | 0x03690 | 1 | `p` |  |
| 160 | 0xA0 | 0x11827 | 0x1b8d0 | 0x16f00 | 2 | `ii` |  |
| 161 | 0xA1 | 0x1184e | 0x1b870 | 0x16eb0 | 1 | `i` |  |
| 162 | 0xA2 | 0x11867 | 0x167f0 | 0x13550 | 4 | `piii` | **Hi_DrawEffModelByBone** EFFARR |
| 163 | 0xA3 | 0x118b3 | 0x16cc0 | 0x137e0 | 6 | `pppiii` | **Hi_DrawMorphEffModel** EFFARR |
| 164 | 0xA4 | 0x1192a | 0x18630 | 0x145a0 | 3 | `iip` | **Hi_GetSummonBoneMatrix** summonRec |
| 165 | 0xA5 | 0x11964 | 0x02fd0 | 0x02c90 | ~4 | `piii` | STUB (`xor eax,eax; ret`) |
| 166 | 0xA6 | 0x119b6 | 0x02fe0 | 0x02ca0 | 3 | `pii` |  |
| 167 | 0xA7 | 0x119f3 | 0x15200 | 0x126b0 | 2 | `ii` | **Hi_DebugPSGData** EFFARR |
| 168 | 0xA8 | 0x11a1a | 0x455f0 | 0x32c70 | 2 | `ip` |  |
| 169 | 0xA9 | 0x11a43 | 0x456d0 | 0x32d10 | 2 | `ip` |  |
| 170 | 0xAA | 0x11a6c | 0x453c0 | 0x32ab0 | 2 | `ip` |  |
| 171 | 0xAB | 0x11a95 | 0x15e10 | 0x12ff0 | 3 | `ppp` | **Hi_RegisterTexPtrModel** EFFARR |
| 172 | 0xAC | 0x11ad5 | 0x3c560 | 0x2d0c0 | 3 | `pip` |  |
| 173 | 0xAD | 0x11b10 | 0x3c730 | 0x2d1b0 | 2 | `pp` |  |
| 174 | 0xAE | 0x11b3a | 0x45ab0 | 0x32f90 | 3 | `iip` |  |
| 175 | 0xAF | 0x11b74 | 0x45f90 | 0x332e0 | 2 | `ii` |  |
| 176 | 0xB0 | 0x11b9b | 0x46cb0 | 0x33c00 | 3 | `iii` |  |
| 177 | 0xB1 | 0x11bd4 | 0x18440 | 0x14490 | 3 | `iip` |  |
| 178 | 0xB2 | 0x11c0e | 0x184b0 | 0x144d0 | 3 | `iip` |  |
| 179 | 0xB3 | 0x11c48 | 0x3bf40 | 0x2ccd0 | 2 | `ii` |  |
| 180 | 0xB4 | 0x11c6f | 0x322e0 | 0x25f80 | 1 | `ii` |  |
| 181 | 0xB5 | 0x11c96 | 0x32310 | 0x25fc0 | 1 | `i` |  |
| 182 | 0xB6 | 0x11cac | 0x323a0 | 0x26050 | 3 | `iii` |  |
| 183 | 0xB7 | 0x11ce8 | 0x46670 | 0x33770 | 2 | `ii` |  |
| 184 | 0xB8 | 0x11d12 | 0x02fd0 | 0x02c90 | ~2 | `ip` | STUB (`xor eax,eax; ret`) |
| 185 | 0xB9 | 0x11d3b | 0x18a40 | 0x14930 | 2 | `ii` | **Hi_SetEffModelOffset** EFFARR |
| 186 | 0xBA | 0x11d63 | 0x46020 | 0x33350 | 2 | `ii` |  |
| 187 | 0xBB | 0x11d8a | 0x1b980 | 0x16f80 | 2 | `ii` |  |
| 188 | 0xBC | 0x11db1 | 0x468d0 | 0x33990 | 1 | `i` |  |
| 189 | 0xBD | 0x11dc7 | 0x48770 | 0x34d10 | 8 | `iiiipiii` |  |
| 190 | 0xBE | 0x11e69 | 0x44a60 | 0x32560 | 1 | `i` |  |
| 191 | 0xBF | 0x11e9a | 0x17b30 | 0x14030 | 2 | `ii` | **Hi_GetSplitMdlVertex** EFFARR |
| 192 | 0xC0 | 0x11ec4 | 0x02fd0 | 0x02c90 | ~2 | `ii` | STUB (`xor eax,eax; ret`) |
| 193 | 0xC1 | 0x11eee | 0x17ae0 | 0x13fe0 | 3 | `iip` | **Hi_SplitMdlVertex** EFFARR |
| 194 | 0xC2 | `(default exit)` | 0x182c0 | 0x143e0 | ~0 | `-` | EMPTY BODY (`ret`) - registered no-op |
| 195 | 0xC3 | 0x11f28 | 0x02fd0 | 0x02c90 | ~5 | `iippi` | STUB (`xor eax,eax; ret`) |
| 196 | 0xC4 | 0x11f8c | 0x18000 | 0x14230 | 5 | `iippi` | **Hi_GetMdlVertexPtr** EFFARR |
| 197 | 0xC5 | 0x11ff0 | 0x18ba0 | 0x14a70 | 1 | `i` |  |
| 198 | 0xC6 | 0x12009 | 0x18c00 | 0x14ac0 | 1 | `i` | **Hi_SplitMdlVertex** EFFARR |
| 199 | 0xC7 | 0x12022 | 0x16570 | 0x133c0 | 4 | `pppi` | **Hi_DrawSliceEffModel** EFFARR |
| 200 | 0xC8 | 0x12081 | 0x18a90 | 0x14980 | 2 | `ii` | **Hi_SetEffModelSlice** EFFARR |
| 201 | 0xC9 | 0x120b9 | 0x314f0 | 0x254e0 | 1 | `i` |  |
| 202 | 0xCA | 0x120cf | 0x1b500 | 0x16ca0 | 1 | `i` |  |
| 203 | 0xCB | 0x120e8 | 0x1ba30 | 0x17010 | 1 | `i` |  |
| 204 | 0xCC | 0x12101 | 0x3c0d0 | 0x2cdb0 | 6 | `iiiiip` |  |
| 205 | 0xCD | 0x12177 | 0x3bce0 | 0x2cab0 | 2 | `ii` |  |
| 206 | 0xCE | 0x1219e | 0x47290 | 0x33ec0 | 2 | `pi` | **Hi_RegisterGouEffModel**, **Hi_RegisterTexListModel** EFFARR |
| 207 | 0xCF | 0x121c9 | 0x46890 | 0x33940 | 2 | `ii` |  |
| 208 | 0xD0 | 0x121f3 | 0x47330 | 0x33f50 | 4 | `ppip` | **Hi_RegisterSummonModel** summonRec |
| 209 | 0xD1 | `(default exit)` | 0x182c0 | 0x143e0 | ~0 | `-` | EMPTY BODY (`ret`) - registered no-op |
| 210 | 0xD2 | 0x12242 | 0x324b0 | 0x26110 | 4 | `iiii` |  |
| 211 | 0xD3 | 0x1228d | 0x464f0 | 0x33630 | ~0 | `-` |  |
| 212 | 0xD4 | 0x12294 | 0x32260 | 0x25f30 | 1 | `i` |  |
| 213 | 0xD5 | 0x122a7 | 0x462a0 | 0x334a0 | 1 | `i` |  |
| 214 | 0xD6 | `(default exit)` | 0x182c0 | 0x143e0 | ~0 | `-` | EMPTY BODY (`ret`) - registered no-op |
| 215 | 0xD7 | 0x122ba | 0x18ce0 | 0x14b10 | 1 | `ppi` |  |
---

## 5. WHERE THE TWO ARITY DERIVATIONS DISAGREE (full disclosure)

20 of 216. **Trust the x86 column**: the x64 number counts only the operands the *handler* reads, and a
handler legitimately reads fewer than the callee declares (the callee may default/ignore trailing params,
or the compiler folded a constant). The reverse cases (x86 < x64) are places where my x64 block walk
over-counted because two opcodes share a fall-through region.

| op | fn x64 | fn x86 | x64-derived | x86 frame | direction |
|---:|---|---|---:|---:|---|
| 3 | 0x40340 | 0x2f830 | 4 | 12 | handler under-reads |
| 35 | 0x1b4a0 | 0x16c50 | 1 | 2 | handler under-reads |
| 59 | 0x3cce0 | 0x2d4b0 | 4 | 3 | x64 over-count |
| 60 | 0x3cf30 | 0x2d660 | 4 | 6 | handler under-reads |
| 62 | 0x3d420 | 0x2d960 | 4 | 6 | handler under-reads |
| 64 | 0x3f180 | 0x2ecc0 | 4 | 5 | handler under-reads |
| 66 | 0x3f6f0 | 0x2f330 | 4 | 13 | handler under-reads |
| 67 | 0x3fc70 | 0x2f570 | 9 | 12 | handler under-reads |
| 68 | 0x40730 | 0x2fa10 | 7 | 8 | handler under-reads |
| 69 | 0x409d0 | 0x2fb90 | 4 | 9 | handler under-reads |
| 70 | 0x40f90 | 0x2ff30 | 4 | 5 | handler under-reads |
| 71 | 0x413b0 | 0x30160 | 4 | 7 | handler under-reads |
| 72 | 0x41670 | 0x30300 | 4 | 7 | handler under-reads |
| 83 | 0x34380 | 0x27510 | 4 | 2 | x64 over-count |
| 105 | 0x3db90 | 0x2dd80 | 1 | 0 | x64 over-count |
| 109 | 0x313f0 | 0x253d0 | 1 | 0 | x64 over-count |
| 130 | 0x46320 | 0x33500 | 4 | 3 | x64 over-count |
| 133 | 0x454a0 | 0x32b50 | 0 (routed to default) | 7 | the jump table sends 133 to the default exit while the .data table still names 0x454a0 |
| 180 | 0x322e0 | 0x25f80 | 2 | 1 | x64 over-count |
| 215 | 0x18ce0 | 0x14b10 | 3 | 1 | x64 over-count |

**None of the 12 summon ops is in this list.** Every summon op's arity is doubly confirmed.

24 opcodes have no x86 `ebp` frame (leaf/naked): 20, 27, 30, 31, 36, 37, 41, 48, 90, 101, 104, 106, 108,
115, 121, 123, 165, 184, 192, 194, 195, 209, 211, 214 - of which 20 is NULL, {27,41,194,209,214} are the
empty `ret` at `0x182c0`, and {36,165,184,192,195} are the `xor eax,eax; ret` stub at `0x2fd0`.

---

## 6. WHAT THIS MEANS FOR "DECODABLE / RE-IMPORTABLE" - the staged roadmap

The prior round's menu item #5 ("emit the native Show/Hide `.seq` opcode into `ef###`") assumed a data
command stream. **That assumption is refuted.** A correct staging looks like this:

### Rung A - READ, no new decode needed (do this first)
The op table is now a complete, checkable dictionary of *every* native call an effect can make. Commit it
as a data file (`opcode`, `name?`, `x64 rva`, `x86 rva`, `arity`, `kinds`). It immediately powers:
- a **cutscene inspector**: hook nothing, just interpret a runtime trace of `(opcode, $a0..$a3)` tuples;
- a **linter** for our authored `[[summon]]` block (mesh-ordinal range vs `meshCount`, motion-frame range
  vs `frameCount`, ABR `0xff` no-op, TexAnim part ids).

### Rung B - TRACE, the highest-value next instrument (LOW effort, no DLL patch)
Everything needed to log the effect's *entire* choreography sits at fixed offsets inside the plugin's own
runtime state, readable exactly like the ROOT probe already reads `SummonData+0x40`:
`ctx+0xda0` (thread), `ctx+0xc98+tid*0x80` (`$a0..$a3`), `ctx+0x2dc8`/`ctx+0x2dcc` (the pending trap word
`0xFF000000|op`). A managed reader sampling the pending-trap word per tick yields **the real opcode
timeline of a real Bahamut cast** - which settles the EFFARR-vs-summon question empirically, gives the
exact frame at which each `Hi_HideSummonModelMesh` fires, and gives the exact `Hi_SetSummonMotFrame`
schedule. Caveat: `ctx` is a heap object; its address must be recovered first (OPEN item 2). This is a
*read*, in the same provenance class as the ROOT probe.

### Rung C - WRITE: the honest cost
Emitting new choreography means **emitting MIPS R3000 machine code** into the effect's code region, not
opcodes into a stream. That is feasible - the ops are just `jal 0xFF0000xx` with `$a0..$a3` set by
`lui/ori/addiu`, one instruction per 4 PSX bytes, terminated by the yield - and a tiny assembler covering
~10 instruction forms would cover every summon op. But it is a different project from "write a `.seq`"
and must be planned as one.

### Rung D - the cheap intermediate win (PROPOSAL, needs an owner go/no-go)
Because ops 157/158 are exact, emission-free and 1-bit-per-model-mesh, a **surgical patch of the hide
mask** is available *without* any code emission: the mask is a plain `u32` at `SummonData+0x20`, at a
fixed offset from a fixed base (`summonModels[0] @0x220830 -> +0x00 -> +0x20`). A managed write there is
the mirror of the ROOT probe's read and would deliver native-precision hiding today, superseding the
managed `HideMeshes=` key filter. It is a *write* into the plugin's runtime state, so it is flagged as a
proposal, not a recommendation.

---

## 7. OPEN ITEMS (do not guess these)

1. **Where the effect's MIPS code region comes from.** `SFX_Play@0x1e50 -> 0x2880` memcpy's the whole
   blob handed to it into a fixed `.data` staging buffer (dst `lea rcx,[rip+0x365055]` @`0x2894` ->
   **RVA `0x3678F0`**; `effnum` stored at **`0x3678E8`** @`0x28bd`), then runs `0x2910`, `0x30c20`
   (camera init), `0x12940`, `0x12bc0`, tail `0x313f0`. The code-region descriptors at `ctx+0xda8` are
   written by `0x3e21c` (inside `0x3de20`, which is also op **107**). **I did NOT prove the decoded
   instruction stream is built from that blob** rather than from a pre-decoded DLL-resident table. The
   x64 `.data` section is ~6 MB virtual / 0x19400 raw - almost entirely BSS - so whatever it is, it is
   built at runtime. Settling this is the single most important remaining question for re-import.
2. **Recovering the live `PsxCtx*`.** `0xd5d0` (the ctx init) is called from `0x2300`; the ctx is not a
   DLL global I could identify statically. Rung B needs its address.
3. **Naming the other ~180 opcodes.** Only 32 leftover debug strings exist (all `Hi_*` model ops); the
   rest are almost certainly PSX `libgpu`/`libgte`/`libspu` HLE and must be named behaviourally. Ops
   90/93/101/104/106/107/115/116/121 are 0-arg system ops and are the natural next targets.
4. **Which array the visible Bahamut is drawn through.** Not statically decidable (see section 2). Rung B
   answers it.
5. **The two execution threads.** `ctx+0xda0` takes values {0,1} with two register files and two 4 KB
   stacks. I did not determine what thread 1 is used for.

---

## 8. REPRODUCTION

All from `studies/custom-summons/thomas-swap/disasm/` with `import refkit`:

    import refkit, struct
    pe = refkit.load(); base = refkit.image_base(pe)
    jt   = struct.unpack('<216I', refkit.read_rva(pe,   0x12358, 216*4))  # handler per opcode
    ft   = struct.unpack('<216Q', refkit.read_rva(pe,   0x68780, 216*8))  # native fn per opcode (x64)
    pe86 = refkit.load('x86')
    ft86 = struct.unpack('<216I', refkit.read_rva(pe86, 0x50e18, 216*4))  # native fn per opcode (x86)
    list(refkit.disasm(pe, 0xee80,  0xeed4))   # bound check + image-relative dispatch
    list(refkit.disasm(pe, 0x126c0, 0x12740))  # getArgInt
    list(refkit.disasm(pe, 0x12740, 0x127d4))  # getArgPtr
    list(refkit.disasm(pe, 0xe210,  0xe290))   # MIPS executor prologue + fetch/decode

Sanity assertions that must hold: `ft[157]-base == 0x187e0`, `ft[158]-base == 0x18840`,
`ft86[157]-0x10000000 == 0x14730`, `ft86[158]-0x10000000 == 0x14780`, `ft[20] == 0` and `ft86[20] == 0`,
and the byte at RVA `0x126b8` is `0xCC`.

---

## 9. PROVENANCE

Read-only static analysis of the user's own installed `FF9SpecialEffectPlugin.dll` (x64 + x86). Output is
RVAs, mnemonics, struct offsets, table indices and control flow only. **No DLL was modified. No creature
geometry, animation, texture or `ef###.bytes` content was read, extracted or written anywhere** - the
staging-buffer address in section 7 was derived from instruction operands, not from any file's contents.
Every native claim cites `fn@rva`; every managed claim cites `file:line`. Runtime-only values (the whole
`PsxCtx`, the register files, the code region) are labelled as such and asserted only as *layout*.
