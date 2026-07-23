# V-M1-13 — the eff-slot NULL-data error stub is a HARD HANG

**Verdict: CONFIRMED** (with one factual correction to the wording of the statement — see §5).

Claim under test (M1-13, source `M1-effmodel-array.md` §3 lines 127-130):

> A NULL data pointer in an eff slot is a hard hang, not a soft failure: the error stub calls `0x151a0`,
> which prints `'HIRAISHI ERROR:'` into DBGCTX `0x220890` and then spins in an unconditional self-loop
> forever. Therefore any cast that registers an eff model provably ran the pool-init opcode.

Everything below was re-derived from a **fresh** `refkit` disassembly of the user's installed
`FF9SpecialEffectPlugin.dll` (x64 **and** x86), plus a fresh PE section/reloc walk. The cited evidence
was **not** trusted; every RVA was re-disassembled off its own `.pdata` `RUNTIME_FUNCTION` range (no
linear sweep, so no desync risk), and the "cold error funclet vs real body" trap was explicitly checked.

---

## 1. Real body, not a cold funclet

`refkit.func_of(fns, 0x15ac0)` → `.pdata` range **`[0x15ac0, 0x15b66)`**. The disassembly of that whole
range contains the slot-scan loop, the slot mutation, the `ret`, **and** both error tails. It is one
contiguous real body — there is no separate cold funclet here, and the error tails are *inside* the
function's own `.pdata` range (they are the fall-out branches, not an MSVC `$LN` cold chunk living
elsewhere). The "names itself in a string" trap does not apply: the string is referenced from the error
tail of the body that owns it.

Full re-disassembly of `Hi_RegisterSolidEffModel @0x15ac0`:

```
180015ac0  mov   qword ptr [rsp+8], rbx
180015ac5  push  rdi
180015ac6  sub   rsp, 0x20
180015aca  xor   edi, edi                      ; rdi = 0  (the NULL/zero source all round)
180015acc  lea   rbx, [rip + 0x20a75d]         ; 0x15ad3 + 0x20a75d = EFFARR 0x220230
180015ad3  mov   eax, edi
180015ad5  cmp   byte ptr [rbx+0x20], dil      ; slot.active == 0 ?
180015ad9  je    0x180015ae8                   ;   -> free slot found
180015adb  inc   eax
180015add  add   rbx, 0x30                     ; STRIDE 0x30
180015ae1  cmp   eax, 0x20                     ; 32 SLOTS
180015ae4  jl    0x180015ad5
180015ae6  jmp   0x180015b32                   ; POOL FULL -> error tail A
180015ae8  cmp   qword ptr [rbx], rdi          ; slot.data == NULL ?
180015aeb  je    0x180015b4c                   ; YES -> error tail B      <<< THE CITED BRANCH
180015aed  mov   word ptr [rbx+0x20], 1        ; active=1, sliceOn=0
...
180015b31  ret                                 ; the ONLY ret in the function
180015b32  lea   rdx, [rip + 0x355a7]          ; -> 0x4b0e0   (tail A)
180015b39  lea   rcx, [rip + 0x20ad50]         ; -> 0x220890  DBGCTX
180015b40  call  qword ptr [rip + 0x345ca]     ; -> 0x4a110
180015b46  call  0x1800151a0
180015b4b  int3
180015b4c  lea   rdx, [rip + 0x3558d]          ; -> 0x4b0e0   (tail B)
180015b53  lea   rcx, [rip + 0x20ad36]         ; -> 0x220890  DBGCTX     <<< CITED
180015b5a  call  qword ptr [rip + 0x345b0]     ; -> 0x4a110              <<< CITED
180015b60  call  0x1800151a0                                             <<< CITED
180015b65  int3                                                          <<< CITED
```

Every cited displacement recomputes exactly:
`0x15b53 + 7 + 0x20ad36 = 0x220890` · `0x15b5a + 6 + 0x345b0 = 0x4a110` · `0x15b39 + 7 + 0x20ad50 = 0x220890`.

**Resolved symbols (fresh):**
* `0x4a110` = import thunk **`MSVCR120.dll!sprintf`** (walked `DIRECTORY_ENTRY_IMPORT`).
* string `@0x4b0e0` = `"Hi_RegisterSolidEffModel()\nmemory not enough!"`
* string `@0x4b078` = `"HIRAISHI ERROR:\n\n%s\n"`

Note both error tails (pool-full **and** NULL-data) use the **same** string and the **same** stub — the
two failure modes are indistinguishable from the message alone.

---

## 2. `0x151a0` has NO reachable return path — the refutation test FAILS

`.pdata` range for the stub: **`[0x151a0, 0x151ff)`**. Complete byte-level disassembly of the entire
range (nothing elided):

```
1800151a0  4881ec38010000      sub     rsp, 0x138
1800151a7  488b05529e0300      mov     rax, [rip+0x39e52]        ; __security_cookie
1800151ae  4833c4              xor     rax, rsp
1800151b1  4889842420010000    mov     [rsp+0x120], rax
1800151b9  4c8d05d0b62000      lea     r8,  [rip+0x20b6d0]       ; = 0x220890  DBGCTX  (the %s ARG)
1800151c0  488d15b15e0300      lea     rdx, [rip+0x35eb1]        ; = 0x4b078 "HIRAISHI ERROR:\n\n%s\n"
1800151c7  488d4c2420          lea     rcx, [rsp+0x20]           ; DEST = a LOCAL stack buffer
1800151cc  ff153e4f0300        call    qword ptr [rip+0x34f3e]   ; = 0x4a110 sprintf
1800151d2  4c8d05dbaf2000      lea     r8,  [rip+0x20afdb]       ; = 0x2201b4
1800151d9  488d1560af2000      lea     rdx, [rip+0x20af60]       ; = 0x220140
1800151e0  498bc8              mov     rcx, r8
1800151e3  0f1f4000            nop
1800151e7  660f1f840000000000  nop
1800151f0  483bca              cmp     rcx, rdx
1800151f3  498bc0              mov     rax, r8
1800151f6  480f45c2            cmovne  rax, rdx
1800151fa  488bc8              mov     rcx, rax
1800151fd  ebf1                jmp     0x1800151f0      ; EB F1 -> 0x151ff - 0x0F = 0x151f0
1800151ff  cc                  int3                     ; padding past the .pdata end
```

Exhaustive properties of the range, verified instruction-by-instruction:

| test | result |
|---|---|
| any `ret` / `leave;ret` / tail `jmp` to another function | **none** |
| any conditional branch that could exit the loop | **none** (`cmovne` is a *move*, not a branch; the only jump is `EB F1`, unconditional) |
| any memory access inside the loop that could fault → SEH escape | **none** — `cmp/mov/cmovne/mov` on registers only |
| any call inside the loop that could throw | **none** |
| any external/volatile state the loop reads | **none** — `rcx` toggles between two link-time constants forever |
| stack restored (`add rsp,0x138`) | **never** (irrelevant — it never returns) |

The loop is a pure register ping-pong: `rcx == rdx ? rax = r8 : rax = rdx; rcx = rax; goto top`. It
alternates `rcx` between `0x2201b4` and `0x220140` indefinitely. **Nothing in the process can break it
except thread termination.** The stated refutation condition — "showing `0x151a0` has a reachable return
path" — is not satisfiable. It is a busy-spin hard hang (100% of one core, no crash, no log, no window
message pump), which matches the user-visible symptom class "the game locks up", *not* a soft skip.

### x86 cross-check (independent codegen, same source)

The 32-bit build carries the same string at RVA `0x36d5c`; a raw immediate scan of `.text` for
`imagebase+0x36d5c` finds exactly one referencing site, `0x1266f`, inside the analogous stub `@0x12650`:

```
10012650  push ebp / mov ebp,esp / sub esp,0x104 / <security cookie>
10012663  68f0862010    push 0x102086f0          ; DBGCTX (x86)  -- the %s ARG
10012668  8d85fcfeffff  lea  eax,[ebp-0x104]     ; DEST = LOCAL stack buffer
1001266e  685c6d0310    push 0x10036d5c          ; "HIRAISHI ERROR:\n\n%s\n"
10012673  50            push eax
10012674  ff1584600310  call dword ptr [0x10036084]   ; sprintf
1001267a  83c40c        add  esp, 0xc
1001267d  b924812010    mov  ecx, 0x10208124
10012682  bab0802010    mov  edx, 0x102080b0
10012687  eb07          jmp  0x10012690
10012690  81f9b0802010  cmp  ecx, 0x102080b0
10012696  b824812010    mov  eax, 0x10208124
1001269b  0f45c2        cmovne eax, edx
1001269e  8bc8          mov  ecx, eax
100126a0  ebee          jmp  0x10012690          ; unconditional self-loop, no ret
100126a2  cc            int3
```

Different register allocation, different calling convention, **identical semantics**: format into a
local buffer, then spin forever with no `ret`. Two independent builds agree.

---

## 3. The second half — "provably ran the pool-init opcode"

This is an *inference*, so I re-derived its two premises separately.

**Premise A — the slot's `data` pointer is zero unless something assigns it at runtime.**
* `EFFARR @0x220230` lies at file-VA `0x220230`, far past `.data`'s `SizeOfRawData` (`.data` VA `0x4f000`,
  raw `0x1a000` ⇒ raw coverage ends at `0x69000`). `pe.get_data(0x220230, 0x30*32)` → **0 non-zero bytes**.
  Same for `DBGCTX 0x220890` → 0 non-zero bytes. (This is the "mislabeled runtime scratch" trap checked
  in the right direction: the array *is* correctly labelled runtime-only.)
* Base-relocation walk: **610** relocs total in the image, **0** of them in page `0x220000-0x221000`.
  So no statically-initialised, relocated pointer can land in a slot. Nothing but runtime code writes it.

**Premise B — exactly one function ever writes a NON-NULL `data`, and it has exactly one caller.**

I enumerated every instruction in the image that references the array range `0x220230..0x220830`
(`refkit.xref_index`) — 21 `lea` sites — then scanned each owning function for `mov qword ptr [...]`
stores. Results:

| RVA | store | value | role |
|---|---|---|---|
| `0x15958` (`Hi_InitEffModel@0x15940`) | `[rax-0x22]` = slot+0x00 | `r9 = 0` | clears all 32 |
| **`0x15982`** (`Hi_InitEffModel@0x15940`) | `[rax]` = slot+0x00, `rax` = `0x1597c+0x20a8b4` = **`0x220230`** | **`rcx` = pool cursor**, `rcx += 0xC8`, `rax += 0x30`, `dec rdx` | **THE ONLY non-NULL assigner** |
| `0x15a08` (`@0x159f0`) | `[rax-0x22]`, `rax` = `0x220252` | `rdx = 0` | a second 32-slot NULL-clear |
| `0x30ca8` (`@0x30c20`) | `[rax-0x22]`, `rax` = `0x220252` | `rbx = 0` (`xor ebx,ebx @0x30c2d`) | a global reset, NULL-clear |
| `0x15a80` (`@0x15a20`) | `[rax]`, `rax` = `0x15a79+0x20adb7` = **`0x220830`**, stride **`0x58`** | pool cursor | the **summon** array init — different array, not EFFARR |

`Hi_InitEffModel @0x15940` in full (its `.pdata` entry is folded into a neighbour, so I disassembled the
byte range and validated the two loops close cleanly):

```
180015940  xor  r9d, r9d
180015943  lea  rax, [rip+0x20a908]        ; 0x1594a + 0x20a908 = 0x220252 = EFFARR+0x22
180015950  mov  word ptr [rax], r8w        ; slot.handle = index
180015954  mov  byte ptr [rax-2], r9b      ; slot.active = 0
180015958  mov  qword ptr [rax-0x22], r9   ; slot.data   = NULL
18001595f  mov  [rax-0x1a],r9 / [rax-0x12],r9 / [rax-0xa],r9
18001596b  lea  rax, [rax+0x30]
18001596f  cmp  r8d, 0x20                  ; 32 slots
180015973  jl   0x180015950
180015975  lea  rax, [rip+0x20a8b4]        ; = 0x220230 EFFARR base
18001597c  test edx, edx
18001597e  jle  0x180015995                ; count <= 0 -> assign nothing
180015982  mov  qword ptr [rax], rcx       ; slot[k].data = poolCursor
180015985  add  rcx, 0xc8                  ; sizeof(ModelData) = 0xC8
18001598c  lea  rax, [rax+0x30]
180015990  dec  rdx / jne 0x180015982
180015995  ret
```

**Caller enumeration:** I disassembled *all 646* `.pdata` functions and collected every `call`/`jmp` with
an immediate target of `0x15940`. Result: **exactly one** — `call 0x180015940 @0x18000f8b8`, inside the
mega-interpreter `@0xeea4`. Its context:

```
18000f888  cmp  dword ptr [rip+0x358056], 0x12d       ; opcode gate
18000f892  je   0x1800122f1
18000f898  movsxd rbx, dword ptr [r13+0xda0]          ; stream index
18000f8a4  shl  rbx, 7
18000f8a8  call 0x180012740                           ; -> rax = pool base
18000f8ad  mov  edx, dword ptr [rbx+r13+0xcac]        ; count, from the effect's own command stream
18000f8b5  mov  rcx, rax
18000f8b8  call 0x180015940                           ; Hi_InitEffModel(pool, count)
```

So: `data != NULL` ⟸ only `Hi_InitEffModel` ⟸ only the interpreter's pool-init opcode. Combined with the
empirical premise "a real Bahamut cast does not lock the game up", the inference holds:

> **Any cast that successfully registers an eff model must have executed the pool-init opcode with
> `count > slotIndex`.** Slots `>= count` keep `data == NULL`; the `(count+1)`-th *simultaneous*
> registration takes such a slot and hangs. The declared count is therefore a **hard cap**, and
> exceeding it is a lockup, never a dropped model.

Two honest caveats on the inference (neither refutes it):
1. It is *conditional on a runtime observation* ("the game does not hang during a real cast"). Statically
   the DLL only proves the implication, not the antecedent.
2. Success does **not** prove the pool was large enough for the whole cast — only that it covered the
   slots actually taken. And a hang from the pool-full tail (`0x15b32`) is byte-for-byte
   indistinguishable from a NULL-data hang, so a lockup cannot be attributed to one cause from the
   message alone.

---

## 4. Practical consequence for the re-import pillar (why this matters)

* `Hi_InitEffModel` **zeroes every slot first, then assigns only `count` of them.** A hand-authored
  `ef###.bytes` MUST emit the pool-init opcode (`0x12d`, per the gate at `0x0f888`) *before* any
  eff-model register opcode, with `count >= ` the maximum number of eff models live at once. Getting it
  wrong is a **hard lockup requiring task-kill**, not a visual glitch — this belongs in any future
  `.seq`/container linter as a **blocking** check, not a warning.
* `Hi_FreeEffModel @0x159a0` hangs on the same stub if the slot is already inactive **or** its data is
  NULL (`0x159ba`, `0x159c1` → `0x159cd` → `call 0x151a0`). Double-free = lockup too.
* `DBGCTX 0x220890` holds the last error message string (written by the caller). A future native-side
  probe reading that address after a freeze gets the exact failing function name for free.

---

## 5. The one correction to the claim's wording

The statement says the stub *"prints `'HIRAISHI ERROR:'` **into** DBGCTX `0x220890`"*. The data flow is
the reverse, and nothing is printed anywhere observable:

* The **caller** (`0x15b5a`) does `sprintf(DBGCTX@0x220890, "Hi_RegisterSolidEffModel()\nmemory not enough!")`
  — i.e. the *function-name message* is what lands in DBGCTX.
* `0x151a0` then does `sprintf(<local stack buffer @rsp+0x20>, "HIRAISHI ERROR:\n\n%s\n", DBGCTX)` —
  DBGCTX is the `%s` **argument**, and the destination is a **local stack buffer** (`lea rcx,[rsp+0x20]`),
  confirmed identically in the x86 build (`lea eax,[ebp-0x104]`).
* That formatted buffer is then **never emitted** — no `printf`, `puts`, `OutputDebugString`, or file
  write follows; the very next instruction begins the spin. So the string is only recoverable by a
  debugger attaching to the hung process (or by reading `DBGCTX` in memory).

This is cosmetic with respect to the load-bearing conclusion (hard hang; pool-init provably ran), which
stands unmodified.

---

## 6. Reproduction

```
cd studies/custom-summons/thomas-swap/disasm
py -c "import refkit;pe=refkit.load();fns=refkit.functions(pe);\
print(refkit.func_of(fns,0x151a0));\
[print(hex(i.address),i.bytes.hex(),i.mnemonic,i.op_str) for i in refkit.disasm(pe,0x151a0,0x151ff)]"
py -c "import refkit;pe=refkit.load();print(pe.get_data(0x4b078,32).split(b'\0')[0], pe.get_data(0x4b0e0,64).split(b'\0')[0])"
py -c "import refkit;pe=refkit.load();print(sum(1 for b in pe.get_data(0x220230,0x600) if b))"   # -> 0
```
