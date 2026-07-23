# Adversarial verification: claim `motion-framecount`

**Verdict: CONFIRMED** (independently re-derived from FF9SpecialEffectPlugin.dll, x64).

## Claim under test
The motion clip (record's DATA block +0x10 target) stores its frame count as a **u16 at
motion+0x02**, used to clamp `SetSummonMotFrame` and to loop/hold the frame counter in `Draw`.

## Struct spine re-derived (fresh disasm, not trusting prior notes)
Record array: base RVA `0x220830`, stride `0x58`, index `imul r8, idx, 0x58; add r8, base`.
- `record+0x00` qword = pointer to the model DATA block.
- `DATA+0x10` qword = the MOTION pointer.
- `record+0x50` byte = active/registered flag (0 => error path).
- `record+0x54` u16 = the motion frame counter.
- `motion+0x02` u16 = the clip FRAME COUNT (the value under test).

## Evidence 1 — write side, `Hi_SetSummonMotion` real body @0x17a10
```
0x17a17 imul r8, rax, 0x58              ; stride 0x58
0x17a1b lea  rax,[rip+0x208e0e] -> base 0x220830
0x17a25 cmp  byte[r8+0x50], 0           ; active flag
0x17a2c mov  rax,[r8]                   ; DATA block ptr (record+0)
0x17a36 mov  word[r8+0x54], dx (=0)     ; zero the frame counter
0x17a3b mov  [rax+0x10], rcx            ; store MOTION ptr at DATA+0x10
```
Confirms motion ptr lives at DATA+0x10 and record+0x54 is the frame counter zeroed on new motion.

## Evidence 2 — clamp side, `Hi_SetSummonMotFrame` real body @0x17a70 (99 bytes; NOT the panic stub — the stub is the `0x17ab6` tail)
```
0x17a8c mov   rax,[r8]                  ; DATA block
0x17a94 mov   rax,[rax+0x10]            ; MOTION ptr
0x17a98 movzx ecx, word[rax+2]          ; frameCount = u16 @ motion+0x02   <-- CLAIM
0x17a9c cmp   ecx, edx                  ; frameCount vs requestedFrame(edx)
0x17a9e jge   0x17aac                   ; if frameCount >= requested -> store requested
0x17aa2 mov   word[r8+0x54], 0          ; else reset counter to 0
0x17aac mov   word[r8+0x54], dx         ; store requested frame
```
Read offset = motion+0x02, u16 (`word ptr`). Semantics: store requested frame iff it fits
(`frameCount >= requested`), else clamp to 0. Matches the claim's "clamp" exactly.

## Evidence 3 — loop/hold side, `Hi_DrawSummonModel` real body (func 0x17740..0x179f2; cited insn @0x177bd, NOT the 0x179f2 panic stub)
```
0x177b7 mov   r9,[rdi]                  ; DATA block (record+0)
0x177bd mov   rax,[r9+0x10]             ; MOTION ptr
0x177c1 movzx ecx, word[rax+2]          ; frameCount = u16 @ motion+0x02   <-- CLAIM
0x177c5 movzx eax, word[rdi+0x54]       ; currentFrame
0x177c9 cmp   ecx, eax
0x177cb jg    0x177e2                   ; frameCount > current -> keep advancing
0x177cd test  byte[rsp+0x60], 1         ; loop flag
0x177d2 je    0x177db
0x177d4 mov   word[rdi+0x54], 0         ; loop: reset to 0
0x177db dec   cx / mov word[rdi+0x54],cx; hold: clamp to frameCount-1
```
Read offset = motion+0x02, u16. `jg keep` reproduced; the fall-through does loop-to-0 (flag set)
or hold-at-(frameCount-1). Matches the claim's "loop/hold in Draw".

## Refutation checks (all negative)
- **Error-stub confusion:** none. All three reads sit in real bodies that do work; the panic
  funclets are the `int3` tails (`0x17ab6`, `0x17a44`, `0x179f2`) reached only on active-flag/null fail.
- **Offset:** every read is `word ptr [<motionptr> + 2]` — exactly +0x02, never a different offset.
- **Width/endianness:** `movzx word ptr` = native LE u16; no fixed-point/byte-swap assumption involved.
- **Scratch-buffer mislabel:** the frame count lives inside the MOTION clip (a real heap/asset
  pointer chased through DATA+0x10), not in the zero-on-disk `.data` scratch region — its VALUE is
  runtime-only but its LAYOUT (u16 @ +0x02) is fully code-derivable, as claimed.
- **Comparison semantics:** consistent across both consumers — SetMotFrame `jge` (store-or-clamp-0),
  Draw `jg` (keep-else-loop/hold). No contradiction with the stated "clamp / loop/hold" wording.

## Note for authoring
motion+0x00 is read by neither consumer here; only motion+0x02 (frame count) drives clamp/loop.
This is a per-clip constant that bounds animation, not a per-frame transform source — it does not
help recover the creature's true per-frame world transform (that remains the camera/bone-matrix
question). Recorded only to close this claim.
