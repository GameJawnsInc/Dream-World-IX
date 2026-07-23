# V-C1 — ADVERSARIAL VERIFICATION: `SFX_Play` blob copy + header-sector copy

**Claim C1 (from `M2-container-format.md` §1):** `SFX_Play` (export @0x1e50 → body @0x2880) memcpy's the
whole `ef###.bytes` blob into a static buffer at RVA **0x3678f0** and stores the effect number at RVA
**0x3678e8**; the first **0x800** bytes (sector 0 = the header sector) are then copied to RVA **0x3208d0**
by fn **0x490d0**.

**VERDICT: CONFIRMED.** Every number re-derived from a fresh refkit disassembly of the user's own installed
DLL, plus two independent corroborations the original artifact did not use (the **x86 build**, and the
**managed `SFX.cs` signature**). Two ancillary corrections to `M2-container-format.md` are recorded in §5 —
neither touches C1's statement.

All x64 RVAs are for `x64/FF9_Data/Plugins/FF9SpecialEffectPlugin.dll`, `ImageBase 0x180000000`,
646 `.pdata` functions. Read-only static analysis; no DLL was modified.

---

## 1. The export → body edge (independently re-derived)

`refkit.exports(pe)` returns **13** exports; `SFX_Play` = **0x1e50**. Disassembling `[0x1e50,0x1e60)`:

```
0x1e50: jmp 0x180002880        ; then int3 padding
```

`refkit.func_of(fns, 0x2880)` → `.pdata` RUNTIME_FUNCTION **[0x2880 .. 0x2904)**. So the export is a pure
thunk and 0x2880 is the **real body** (a genuine `.pdata` entry with a prologue, not an MSVC cold error
funclet — it has `mov [rsp+8],rbx / push rdi / sub rsp,0x20` and ends in a tail `jmp`).

## 2. The blob memcpy (fn 0x2880) — verbatim

```asm
0x2880: mov   qword ptr [rsp+8], rbx
0x2885: push  rdi
0x2886: sub   rsp, 0x20
0x288a: mov   rdi, r9              ; arg3 (req)
0x288d: mov   ebx, ecx             ; arg0 (effnum)
0x288f: test  r8d, r8d             ; arg2 (size)
0x2892: je    0x1800028a3          ; size == 0 -> skip the copy
0x2894: lea   rcx, [rip+0x365055]  ; -> 0x3678f0     DEST
0x289b: movsxd r8, r8d             ; size, sign-extended
0x289e: call  0x180049cd8          ; memcpy          (rdx = arg1 = bin, UNTOUCHED since entry)
0x28a3: xor   ecx, ecx
0x28a5: call  qword [rip+0x47885]  ; -> IAT 0x4a130 = MSVCR120!_time64
0x28ab: mov   rcx, rax
0x28ae: call  qword [rip+0x47874]  ; -> IAT 0x4a128 = MSVCR120!srand
0x28b4: mov   rcx, rdi
0x28b7: mov   dword [rip+0x36502b], ebx   ; -> 0x3678e8   EFFECT NUMBER
0x28bd: mov   dword [rip+0x66ee1], 0      ; -> 0x697a8
0x28c7: call  0x180002910
0x28cc: call  0x180030c20
0x28d1: lea   rdx, [rip+0x20f5a8]  ; -> 0x211e80
0x28d8: lea   rcx, [rip+0x574131]  ; -> 0x576a10
0x28df: call  0x180012940
0x28e4: mov   rcx, qword [rip+0x6437d] ; -> 0x66c68
0x28eb: mov   dword [rcx+0xc], eax
0x28ee: call  0x180012bc0
0x28f3: mov   ecx, ebx
...
0x28ff: jmp   0x1800313f0
```

**Call target 0x49cd8 IS `memcpy`.** It is not a function (`func_of` returns None) — it is an import thunk
strip: `0x49cd8: jmp qword [rip+0x4ba] -> IAT 0x4a198`, and resolving the import directory gives
`MSVCR120.dll!memcpy` (the adjacent thunks 0x49cde/0x49ce4/0x49cea are `memset`/`sin`/`sqrt`, confirming the
thunk table is correctly aligned).

**Argument binding.** MS x64 ABI: `rcx,rdx,r8,r9`. `rcx` is overwritten with the literal 0x3678f0; `rdx` is
never written between entry and the call; `r8d` is sign-extended in place. Therefore the call is exactly

```c
memcpy(/*dst*/ (void*)0x3678f0, /*src*/ arg1_bin, /*n*/ (ptrdiff_t)arg2_size);
```

**"the whole blob"** — corroborated on the managed side (`Assembly-CSharp` is open source, so this is
independent of the DLL): `Global/SFX/SFX.cs:747`
`public static extern void SFX_Play(Int32 effnum, IntPtr bin, Int32 size, IntPtr req);` and the live call
site `SFX.cs:1979` `SFX.SFX_Play((Int32)effNum, binHandle.AddrOfPinnedObject(), binAsset.Length, ...)` —
`size` **is** the whole `ef###.bytes` asset length. `SFX.cs:1984` passes `(IntPtr)null, 0`, which is exactly
what the `test r8d,r8d; je` guard at 0x2892 exists for. The four-argument shape matches the register use
1:1 (`rdi = r9 = req` is later fed to 0x2910).

**"stores the effect number at 0x3678e8"** — `ebx` is loaded from `ecx` (arg0 = `effnum`) at 0x288d and
stored to 0x3678e8 at 0x28b7. Confirmed.

**0x3678f0 is a genuine static (uninitialized) buffer, not mislabeled runtime scratch in the wrong sense.**
Section table: `.data` VA 0x4f000, VirtualSize 0x5d3440 (ends 0x622440), **SizeOfRawData only 0x1a000**.
0x3678f0 lies far past the raw image → **zero bytes on disk**, i.e. BSS-style static storage inside `.data`.
That is the correct reading: the *address* is static and verifiable, the *contents* are runtime-only. There
is ≥ 0x2BAB50 bytes of headroom above 0x3678f0 inside the section — comfortably more than the largest stock
effect (`ef227` = 0xc9000), so "memcpy the whole blob" is structurally coherent.

**Independent corroboration that 0x3678f0 IS the container base:** fn **0xd740** @0xd7e3 does
`lea rax,[rip+0x35a106] -> 0x3678f0` … `mov qword [rbx+8], rax` … `call 0x18000d390` — i.e. it installs
0x3678f0 as `ctx->blob` (the `r8` the table walker 0xd390 dereferences) immediately before invoking the
walker. And the sector-streaming path @0x3ecc9-0x3ece5 computes
`memcpy(dst, 0x3678f0 + (cursor − [0x3678ec]) << 11, n)` — the blob is read back sector-wise from the same
base. Only **4** instructions in the whole image reference 0x3678f0: 0x2894 (the write), 0xd7e3, 0x3ecdb,
0x49101. All four are consistent with "one static container buffer".

## 3. The header-sector copy (fn 0x490d0) — verbatim

`refkit.func_of(fns, 0x490d0)` → `.pdata` **[0x490d0 .. 0x49167)** (a real body).

```asm
0x490d0: sub   rsp, 0x28
0x490d4: mov   eax, dword [rip+0x52f8f6]   ; -> 0x5789d0
0x490da: mov   edx, ecx
0x490dc: mov   dword [rip+0x31e809], r8d   ; -> 0x3678ec   (sector base)
0x490e3: mov   dword [rip+0x31e66b], ecx   ; -> 0x367754
0x490e9: mov   dword [rip+0x31e7f9], ecx   ; -> 0x3678e8   (effect number, again)
0x490ef: mov   dword [rip+0x52f8df], eax   ; -> 0x5789d4
0x490f5: call  0x18000d740                 ; <-- the table walk happens HERE, BEFORE the copy
0x490fa: lea   rcx, [rip+0x2d77cf]         ; -> 0x3208d0   DEST
0x49101: lea   rax, [rip+0x31e7e8]         ; -> 0x3678f0   SRC (blob base, i.e. FILE OFFSET 0)
0x49108: mov   edx, 0x10                   ; 16 iterations
0x4910d: nop   dword ptr [rax]
0x49110: movups xmm0, [rax]                ; loop body: 8 x movups load + 8 x movups store
0x49113: movups xmm1, [rax+0x10]
0x49117: lea   rcx, [rcx+0x80]             ; 0x80 bytes per iteration
0x4911e: lea   rax, [rax+0x80]
0x49125: movups [rcx-0x80], xmm0
...
0x49159: movups [rcx-0x10], xmm1
0x4915d: dec   rdx
0x49160: jne   0x180049110
0x49162: add   rsp, 0x28
0x49166: ret
```

**Length: 0x10 iterations × 0x80 bytes = 0x800 exactly.** **Direction: `rax`/0x3678f0 is loaded from,
`rcx`/0x3208d0 is stored to** — dest = 0x3208d0, src = blob byte 0. Both halves of the claim confirmed
literally.

**0x3208d0 really is used as the header sector.** Only 3 instructions reference it: 0x232f
(`lea rdx,[0x3208d0]`, in fn [0x2300..0x2612)), **0x3deba (`movzx eax, word ptr [0x3208d0]`)** — a `u16` read
at offset 0, i.e. `chunkCount` per M2 §2 — and 0x490fa (the write). Consistent, and arithmetic-consistent
with M2 §1's sequence pointer `0x320cd0 = 0x3208d0 + 0x400`.

## 4. x86 cross-check — the decisive independent witness

Different codegen, same source. `refkit.load('x86')`, ImageBase 0x10000000, export `SFX_Play` @0x1d10:

```asm
0x1d10: push ebp / mov ebp,esp
0x1d13: push [ebp+0x14]      ; req
0x1d16: mov  edx, [ebp+0xc]  ; bin
0x1d19: push [ebp+0x10]      ; size
0x1d1c: mov  ecx, [ebp+8]    ; effnum
0x1d1f: call 0x10002640      ; __fastcall(ecx=effnum, edx=bin, [size, req] on stack)
```

Body @0x2640:

```asm
0x2643: mov  eax, [ebp+8]        ; size
0x2647: mov  esi, ecx            ; effnum
0x2649: test eax, eax
0x264b: je   0x1000265c          ; size == 0 -> skip
0x264d: push eax                 ; n    = size
0x264e: push edx                 ; src  = bin
0x264f: push 0x1034f680          ; dst  = the static blob buffer
0x2654: call 0x10035e66          ; -> jmp [0x100360d0] = MSVCR120!memcpy
0x2671: mov  dword [0x1055e788], esi   ; effect number
0x2677: mov  dword [0x101a9dc0], 0     ; the 0x697a8 analogue
0x2681: call 0x100026c0 / 0x10024ff0 / 0x1000ffc0(0x101f9ef0) / 0x10010260
0x26a9: call 0x100253d0                ; the 0x313f0 analogue
```

Structurally identical, instruction for instruction, including the `size == 0` guard and the argument order.

And the header-sector copy, in the x86 build, is **not** unrolled — it is the literal call:

```asm
0x35334: push 0x800          ; n   = 0x800   <-- the length as an explicit immediate
0x35339: push 0x1034f680     ; src = the blob base
0x3533e: push 0x10308730     ; dst = the header-sector buffer
0x35343: mov  dword [0x10050e10], 0x100
0x3534d: call 0x10035e66     ; memcpy
```

This is the single strongest confirmation available: the x64's 16×0x80 SSE loop is the *inlined* form of a
`memcpy(headerSector, blob, 0x800)` that the x86 compiler left as a call with **0x800 as a literal
immediate**. No reading of the unrolled loop is required to know the length. The x86 sector-stream path
@0x2ea77-0x2ea8c likewise mirrors the x64 @0x3ecc9-0x3ece5 (`blob + (cursor − base) << 11`).

## 5. Corrections to `M2-container-format.md` (do not affect C1)

1. **§1's load-chain row for 0x490d0 has the internal order INVERTED.** It reads "copies blob[0x000..0x800]
   … → 0x3208d0; then calls 0xd740". The real order inside fn 0x490d0 is `call 0xd740` **@0x490f5 FIRST**,
   then the 0x800 copy @0x490fa-0x49160. Any downstream reasoning that assumes the table walker sees the
   already-populated 0x3208d0 copy is wrong — the walker (0xd740 → 0xd390) reads `ctx->blob` = **0x3678f0**
   directly (0xd7e3), not the header-sector copy.
2. **§1 presents 0x490d0 as if `SFX_Play` reaches it in-line. It does not.** A whole-image scan for direct
   `call`/`jmp` to 0x490d0 finds **exactly one** call site: **@0x3e6a4**, inside fn **[0x3de37 .. 0x3ed32)**
   — the sector-feed state machine. Its arguments come from runtime globals
   (`ecx = [0x3231f4]`, `r8d = [0x3231f0]` @0x3e697/0x3e69e), and it increments `[0x3231f0]` on return. So
   the header-sector copy is an **asynchronous later step of the load state machine**, not part of the
   `SFX_Play` call itself. C1's word "then" is temporally accurate; the chain table's implied adjacency is
   not.
3. **New (not in M2): fn 0x490d0 also re-publishes the effect number** to **0x3678e8** *and* **0x367754**
   (@0x490e9/0x490e3), and stores its `r8d` argument to **0x3678ec** — which the streaming memcpy @0x3eccf
   subtracts from the running sector cursor. So **0x3678ec is a sector BASE index, not a byte size.** Any
   future claim that 0x3678ec holds the blob length would be false.

## 6. What could still falsify this, and why it does not

| falsifier tried | result |
|---|---|
| Is 0x2880 an MSVC cold error funclet that merely *names* the function? | No — reached by a direct `jmp` from the export, has a real prologue/epilogue, own `.pdata` range, no `__wassert`/error string. |
| Is 0x49cd8 something other than `memcpy`? | Resolved through the import directory: `IAT 0x4a198 = MSVCR120.dll!memcpy`. |
| Could `rcx` be reloaded before the call (dest ≠ 0x3678f0)? | Only `movsxd r8,r8d` sits between the `lea` and the `call`. |
| Is the copy length something other than 0x800? | x64: `edx = 0x10`, 0x80 bytes/iteration. x86: `push 0x800` literal. Two builds agree. |
| Is the direction reversed (0x3208d0 → 0x3678f0)? | Loads are from `rax`(0x3678f0), stores to `rcx`(0x3208d0); x86 pushes dst=0x10308730, src=0x1034f680. |
| Is 0x3678f0 the "STATIC_TABLE"-class error (a label on runtime scratch)? | The *address* is static and cited; the *contents* are explicitly runtime-only (zero on disk, past `SizeOfRawData`). Stated as such — no content claim is made. |
| Is the C# signature dead-code hearsay (the `SFXBinaryFile.cs` trap)? | `SFX.cs:747/815/1979` is a live `DllImport` + live call site with a `GCHandle`-pinned asset, not a parser. It is used only as *corroboration* of argument order; the binding is proven from the register use alone. |

## 7. Provenance

Read-only static analysis of the user's own installed `FF9SpecialEffectPlugin.dll` (x64 and x86) via
`refkit.py`, plus open-source `Assembly-CSharp` at `C:/gd/FFIX/Memoria/`. No game bytes were extracted or
written anywhere. No DLL was modified. Every figure above is a structural offset/length/register, not
content.
