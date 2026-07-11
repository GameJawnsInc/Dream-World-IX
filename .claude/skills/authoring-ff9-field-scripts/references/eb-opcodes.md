`ff9mapkit/ff9mapkit/eb/_optables.py` is the AUTHORITATIVE opcode source — auto-generated from Memoria source (`EventEngineUtils.cs` `opArgCount`/`opArgSize` + `EventEngine.DoEventCode.cs` names; regen: `python -m ff9mapkit.eb._regen_optables`). Never fork or hand-copy it; read it directly. It exposes `OP_ARG_COUNT[op]` (negative = variable count), `OP_ARG_SIZE[op]` (per-operand byte widths), `OP_NAMES[op]` (mnemonics). The full table is deliberately NOT reproduced here.

Deep recipe: memory `project-ff9-eb-script-tooling.md` (the `.eb` bible). All lines below are quoted verbatim from that memory or the repo brief (CLAUDE.md §7).

## Binary format

Quoted verbatim from `project-ff9-eb-script-tooling`:

> - Layout: `[44B header][84B PSX name][entry table @128][entry data...]`. `raw[3]` = entryCount.
> - Entry table: 10 slots × 8B = `off(2) sz(2) loc(1) fl(1) pad(2)`. `off`/file pos = `128 + off`.
> - Entry: `type(1) funcCount(1) [tag(2) fpos(2)]×funcCount  then function code`.
>   **`funcBasePos = entryStart + 2`** and `fpos` is measured from there (i.e. fpos includes the
>   func-table bytes; func0 fpos is typically `funcCount*4`). Empty entry = `maxPosEntry <= pos`.
> - Code: `opcode(1; if 0xFF then 2-byte 0x100|next)`; if `op>=0x10 && argCount!=0` an `argFlag` byte
>   follows (bit i set ⇒ arg i is an EXPRESSION, else a constant of size `opArgSize[op][i]`).
>   Expressions are postfix, terminated by `0x7F`; const push `0x7D`(2B)/`0x7E`(4B); vars `>=0xC0`.
> - Entry type: object = 2, main = 0. Object NPCs must be spawned by `InitObject(idx,0)` in Main_Init.

## Opcode traps (the crash list)

Quoted verbatim from CLAUDE.md §7:

> Opcode traps worth memorizing: **`Battle = 0x2A`** (NOT PreloadField — encoding a warp as
> 0x2A starts a battle on a bad scene id → crash/black); real `PreloadField = 0xFD` is a no-op
> HINT on Steam; `Field = 0x2B` is the real warp; **`0x01` is an undocumented unconditional
> JMP** (don't overwrite a Wait that sits right after it — the activation is skipped). Camera/
> scroll mechanics: **`SETCAM = 0x7E`** (switch active camera), **`BGCACTIVE = 0x71`** (enable
> scroll / camera-services).

And from `project-ff9-eb-script-tooling` (the lesson that fired real battles):

> LESSON: **verify an opcode value against the engine tables (`OP_NAMES`) before encoding** — never trust a self-written "expect".
> Self-loop: `Field(N)` from inside field N is a no-op → falls through to `TerminateEntry(255)` → kills the player → battle inits null → crash.

## Expression sub-language

Quoted verbatim from CLAUDE.md §7:

> **Expression sub-language**: opcode `0x05` + a `0x7F`-terminated RPN stack; var token byte =
> `0xC0 | (type<<2) | source`. `B_SYSVAR=0x7A` (code 9 = `GetChoose`, reads the picked choice
> row); `GetItemCount` = expr fn `0x64`. Reusable for chests/levers/choices.

Var-token detail, quoted verbatim from `project-ff9-story-flags`:

> Var token byte = `0xC0|(VariableType<<2)|VariableSource` (+`0x20` long-index).
> `VariableSource`: Global=0(persistent)/Map=1(transient)/Instance=2.
> `VariableType`: SBit0/Bit1/Int24 2/UInt24 3/SByte4/Byte5/Int16 6/UInt16 7.
> The full assignment-operator family is `op_binary` 0x2C..0x45 (`B_LET`..`B_OR_LET_E`).

## Talk-func minimum size

Quoted verbatim from CLAUDE.md §7:

> **A talk func (tag 3) MUST be ≥ 9 bytes.** `IsActuallyTalkable` polls `tag3[ip+7]`/`[ip+8]` every frame the
> player is near it → a shorter func indexes past the entry buffer = an `IndexOutOfRangeException` each frame
> (non-fatal, spams `Memoria.log`). The kit pads short talk funcs; non-interactive props are **`bare`** (Init-only,
> no tag-3 — matches shipping set-dressing, dodges the poll).

## Load-bearing op values (short list — the full table stays in `_optables.py`)

Quoted verbatim from `project-ff9-eb-script-tooling`:

> Key opcodes: InitObject=0x09 args[1,1] (no argFlag, `09 II 00`); Wait=0x22 args[1] (`22 00 NN`);
> SetModel=0x2F args[2,1]; CreateObject=0x1D args[2,2]; SetStandAnimation=0x33 arg[2];
> DefinePlayerCharacter=0x2C (0 args); NOP/NOTHING=0x00; WindowSync=0x1F args[1,1,2];
> WindowAsync=0x20 args[1,1,2]; TWIST/SetControlDirection=0x67 args[1,1]; RaiseWindows=0x8E; WaitWindow=0x54.

## Verify every edit

Disasm-verify all entries decode clean before deploy (`ff9mapkit disasm`; historical `eb_disasm.py`). Bytecode is language-identical across the 7 per-language `.eb` — assert expected bytes per-file, then patch the same offset in each. Safe insertion into a non-last function = `edit.insert_in_function` (fixes sibling `fpos`; plain `insert_bytes` leaves them stale).

## Pointers

- Memory: `project-ff9-eb-script-tooling.md` — injection recipes (NPC / talk / dialogue text / events / cutscenes / ladders).
- Docs: `ff9mapkit/docs/FORMAT.md` (the field.toml schema that compiles into `.eb`).
