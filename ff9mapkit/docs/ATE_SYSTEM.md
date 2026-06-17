# ATE System — byte-accurate teardown of FF9's Active Time Events

> **What this is.** A reverse-engineering teardown of FF9's **Active Time Event (ATE)** system — the optional
> "Active Time Event / Press SELECT" cutscenes of off-screen characters — grounded byte-for-byte in the Memoria
> C# source and in real shipping `.eb` bytes extracted from the user's `p0data`. Produced by the `ate-teardown`
> workflow (6 parallel subsystem dossiers → synthesis → **10 load-bearing claims adversarially verified, all
> confirmed high-confidence** → real-field disassembly), 2026-06-13. North star = **emulate/export the real
> game**, not recreate from scratch. Companion gap note lives in `FORK_FIDELITY.md`; deep recipe in project
> memory `project-ff9-ate-system`.

---

## Headline

**An ATE is almost entirely field-`.eb`-script-driven.** The Memoria engine contributes only three small,
separable things; the *trigger logic, the menu, and the cutscene dispatch all live in the field's own
bytecode*. There is **no dedicated "open the ATE menu" opcode and no engine-side ATE cutscene dispatcher**
(`FieldMap.cs` has zero ATE code). The engine's three jobs:

1. **A blinking on-field HUD prompt** ("Active Time Event / Press SELECT"), armed by **one** event opcode —
   `AICON`, byte **`0xD7`** (kit mnemonic **`ATE`**) — and drawn Blue (new) or Gray (seen) by `EIcon.ProcessAIcon`.
2. **A window-style flag** `winATE = 64 (0x40)` that makes an *ordinary* choice-dialog window render with the
   ATE caption (`Dialog.CaptionType.ActiveTimeEvent`).
3. **Achievement-only bookkeeping** when an ATE dialog closes (`ProcessATEDialog → MappingATEID →
   ATE80Achievement`), writing a 100-int `AteCheck` array in the **achievement** save block (the "watch 79 ATEs"
   trophy) — *not* in the story heap, and *never* read back to run a cutscene.

> ### ⚠ The keystone correction (vs the initial scouting note)
> The ATE-enable opcode is **`AICON` (enum index `0xD7` = 215)**, **NOT `BARATE`**. `BARATE` is an unrelated
> `BA*`-family battle-animation opcode at enum index **`0x10D` (269, encoded `0xFF 0x0D`)** whose handler is a
> genuine no-op (`getv1(); getv2(); return 0;`). The "ATE" substring in `BARATE` is a naming-collision red
> herring. The kit's `eb/_optables.py` mapping `0xD7: 'ATE'` is **byte-correct** (it *is* `AICON`).

---

## 1. Opcode & flag reference

| Token | Engine name | Hex / encoding | Args | Role |
|---|---|---|---|---|
| kit `ATE` | **`AICON`** | `0xD7` (215), 1-byte op | 1 (`mode`) | **The ATE-enable opcode.** Calls `EIcon.SetAIcon(mode)` — arms/hides the HUD prompt. No menu, no cutscene, no seen-write. |
| `BARATE` | `BARATE` | `0x10D` (269) → bytes `0xFF 0x0D` | reads+discards `getv1`+`getv2` | Battle-animation rate; **NO-OP red herring**, not ATE. |
| `WindowSync` | `MES` | `0x1F` | textID + `uiFlags` | Window opcode; with `uiFlags & 64` → ATE-captioned dialog. |
| `WindowAsync` | `MESN` | `0x20` | textID + `uiFlags` | Same, async. (`MESA=0x95`/`MESAN=0x96` behave identically.) |
| — (flag) | `winATE` | `64 = 0x40` | — | `uiFlags` bit ⇒ `CaptionType.ActiveTimeEvent`. |
| in-expr `op7A(9)` | `B_SYSVAR(9)` → `GetChoose` | expr token `0x7A`, sysvar code `9` | — | Reads `DialogManager.SelectChoice` (the picked row). |
| stmt `op_0B` | `JMP_SWITCH` | statement `0x0B` | base + per-case offsets | The engine's switch primitive; the ATE branch table. |

**Citations (Memoria source, `Assembly-CSharp/Global/…`):**
- `AICON` handler — `Event/Engine/EventEngine.DoEventCode.cs:648-653`:
  `case EBin.event_code_binary.AICON: // 0xD7, "ATE", "Enable or disable ATE"` → `mode = getv1(); EIcon.SetAIcon(mode);`.
- `AICON` enum index — `EBin.cs:2304` (pure auto-increment enum opening `NOP` at `:2089`; index = line − 2089 = 215 = `0xD7`; anchors `POS@2118→0x1D`, `MES@2120→0x1F`, `MESN@2121→0x20` confirm no gaps).
- `BARATE` — enum `EBin.cs:2358` (index 269 = `0x10D`); handler `DoEventCode.cs:78-83` is the no-op.
- `winATE` — `ETb/ETb.cs:486` `public const Int32 winATE = 64;`. Flag→style — `ETb.cs:179-180`
  `else if ((flags & ETb.winATE) > 0) captionType = Dialog.CaptionType.ActiveTimeEvent;`.
- `GetChoose` — sysvar 9 (`Event/Engine/EventEngine.GetSysvar.cs:37-38 → ETb.GetChoose()`); `ETb.cs:262-268`
  returns `DialogManager.SelectChoice`. Expr token `B_SYSVAR=0x7A` (kit `eb/_exprtable.py`).
- `op_0B` = `JMP_SWITCH` — `EBin.cs:1482-1487` (dispatch) + `EBin.cs:1339-1368` (table walk).

> **Mnemonic vs identifier:** the kit calls `0xD7` `ATE`; the engine identifier is `AICON`. Same opcode (215).
> **Statement `0x7A` ≠ expr token `0x7A`:** as a *statement* opcode `0x7A` is `SetLeftAnimation`
> (`_optables.py`); only the *in-expression* `0x7A` token is `B_SYSVAR`. Don't conflate them.

---

## 2. The HUD prompt (engine — `EIcon` + `ActiveTimeEvent`)

The on-field blinking prompt is driven entirely by **one integer**, `EIcon.sAIconMode`, set verbatim by the
`AICON` opcode's `mode` arg. There is **no proximity check, no region check, and no "available ATE" registry** —
the script decides.

**`EIcon.SetAIcon(mode)`** (`EIcon.cs:443-454`): `mode == 0` hides the icon; otherwise stores
`sAIconMode = mode` and resets `sAIconTimer = 44`.

**`EIcon.ProcessAIcon()`** (`EIcon.cs:416-436`), each event tick:

```csharp
if (sAIconMode > 0 && ((sAIconMode & 4) > 0 || GetUserControl())) {
    sAIconTimer++;
    if ((sAIconMode & 3) != 2)            { currentATE = Blue; ShowAIcon(true, Blue); }   // new
    else if ((sAIconTimer / 15 & 1) > 0)  { currentATE = Gray; ShowAIcon(true, Gray); }   // seen, ~15f flicker
} else ShowAIcon(false, currentATE);
```

- **Gate:** prompt shows only when `sAIconMode > 0` **and** (force bit `&4` set **or** the player has control).
- **Colour is purely `sAIconMode & 3`** — `!= 2` ⇒ **Blue** (steady), `== 2` ⇒ **Gray** (flickers on a ~15-frame
  cadence). `ATEType { Blue = 1, Gray = 2 }` (`Global/ATEType.cs`). **The HUD has zero seen-awareness** —
  `AteCheck` is read only by the trophy counter, never here. The "new vs seen" look is an **emergent convention**:
  the *script* reads a story flag and passes `mode 1` vs `mode 2`.
- `ShowAIcon → UIManager.Field.EnableATE(isActive, type) → ActiveTimeEvent.EnableATE` (the NGUI widget at
  `Global/Active/ActiveTimeEvent.cs`) — cosmetic: SELECT glyph (platform-specific), Blue/Gray sprites, the
  2-second blink coroutines. `FieldHUD.OnATEClick` (`FieldHUD.cs:313-316`) is a **dead NGUI passthrough** (zero
  C# callers) that only re-enables the Blue sprite — it does **not** open the menu.

### `ATE(mode)` arg semantics — the arg is a **3-bit flag word, NOT an enum**

★ **Engine-source ground truth** (`EIcon.ProcessAIcon` + `SetAIcon`, `Global/EIcon.cs:416-454`; the only
mode-aware switch *downstream* is on `ATEType {Blue = 1, Gray = 2}`, `Global/ATEType.cs`). The engine **never
compares the arg to `1`/`5`/`6` by name** — `SetAIcon` stores the raw byte verbatim into `sAIconMode` (no
clamp, no validation, no `default:` — `EIcon.cs:443-454`), and `ProcessAIcon` reads only **three bits** of it:

- **`> 0`** — enable gate. `0` = disable/hide (mode 0 calls `ShowAIcon(false)` to hide the icon, `EIcon.cs:445`).
- **`& 3 == 2`** — **Gray** banner (unskippable; blinks on a ~15-frame cadence, `EIcon.cs:426`). Anything else
  (`& 3 != 2`) ⇒ **Blue** "Press SELECT" (steady).
- **`& 4`** — **force** bit (`kAIconForce`, `EIcon.cs:472`): show even when the player has **no** user control.
  Without it, the icon shows only while `GetUserControl()` is true.

High bits (≥ 8) are masked out entirely, so `9` behaves like `1`, `14` like `6`. That leaves **8 reachable
low-bit combinations**, of which the game ships exactly **four**:

| byte | bits | `&3` → colour | `&4` force | net behaviour | shipped? |
|---|---|---|---|---|---|
| **0** | `000` | — | — | **off / hide** | ✅ 436× (the clear/disarm between brackets) |
| **1** | `001` | Blue | no | **Blue, optional** — shows only with control; you may ignore it | ✅ 552× |
| 2 | `010` | Gray | no | Gray *but can't show during a no-control beat* → useless for a forced scene | ❌ never |
| 3 | `011` | Blue | no | duplicate of mode 1 | ❌ |
| 4 | `100` | Blue | yes | Blue, forced | ❌ |
| **5** | `101` | Blue | yes | **Blue, forced** — re-flashes the SELECT glyph during auto-play | ✅ 1× (field 206 only) |
| **6** | `110` | Gray | yes | **Gray, forced** = the grey unskippable banner | ✅ 51× |
| 7 | `111` | Blue | yes | duplicate of mode 4/5 | ❌ |

So there are only **five distinct observable behaviours** (off / Blue-optional / Blue-forced / Gray-optional /
Gray-forced); the game uses four of them (never Gray-optional). The unused byte values aren't "missing modes" —
they're either **redundant** (3 ≈ 1; 4/7 ≈ 5) or **useless** (2 = Gray-without-force, which can't drive the
no-control off-screen beats Gray exists for). That is *why* every sweep only ever finds `{0, 1, 5, 6}`.

**Fresh full-coverage scan** (kit disassembler over **all 818** field event scripts from `p0data`, 2026-06-16):
**459 fields** carry an ATE, **1040 call sites, ZERO expression-args** (every mode byte is a literal — nothing
hidden behind a computed value), distinct values **exactly `{0, 1, 5, 6}`** (no `2`, no `3/4/7+`), histogram
**`{1: 552, 0: 436, 6: 51, 5: 1}`**. This re-verifies the original "676-field sweep" (`{1: 473, 0: 358, 6: 45,
5: 1}`) — **identical value set**, larger counts only because the scope is wider (818 vs 676 scripts). The lone
mode-5 site lands byte-exact on field 206's documented offset 2640, anchoring the decoder.

**★ The mode-6 flip-flop is now SETTLED by engine source, not byte-sweep inference.** An earlier draft called
mode 6 a "screen-transition fade, NOT a grey ATE"; the next overturned it to "grey unskippable." `EIcon.cs`
ends the argument: `6 = 0b110 = Gray (&3==2) + force (&4)` → the grey, force-shown, blinking banner. The
"grey unskippable" reading is correct, and it is now a **decode, not a guess.**

FF9's **two real ATE flavors** map cleanly onto the bits:

- **Optional / Blue (`mode 1`)** — the Press-SELECT menu hubs (fields 1901 Eiko, 552 Lindblum, 206 Prima Vista,
  …): armed in `Main_Init`, Blue, no force → the prompt shows only when you have control, so you may ignore it.
  *(Earlier revisions mislabeled these "forced" — they are OPTIONAL.)*
- **Forced / Gray (`mode 6`)** — 51 mandatory captioned off-screen story scenes (field 956 Gargant; the
  Festival-of-the-Hunt cluster 2105/2113/2114/2157/2161-2163/2211 chains 10-11 sequential grey-ATE scenes,
  caption txids 91-101 / 116-126). Bracketed `ATE(6) … ATE(0)` and played under a `DisableMove..EnableMove`
  lock with a `winATE(64)` caption and **no menu** — the bottom-left grey "ACTIVE TIME EVENT" banner blinks
  throughout. **Author one with `[cutscene] ate = true` (`ate_mode = 6`, the default).** ★ In-game @30008 /
  real 956 @30010.
- **Mode 5 (Blue + force) appears exactly ONCE** — field 206 entry-0 tag-1, the rotating Press-SELECT hub
  opening its menu window. Discouraged for authoring (a force-shown *Blue* icon re-flashes the SELECT glyph
  during auto-play — see the press-glyph note below).

> **The press-glyph mechanics** (`ActiveTimeEvent.cs`): the on-field icon widget owns the "Press SELECT" glyph
> (`PressSelectSprite`), gated by colour — the **Blue** display coroutine (`DisplayBlueATEText`) cycles it ON
> (~2s/2s), so a *visible* Blue icon always flashes "Press SELECT"; the **Gray** coroutine never calls
> `SetSpriteVisibility`, so a Gray icon shows no press glyph. Force-showing a Blue ATE (mode 5) therefore wrongly
> invites a button press during an auto-play — which is exactly the artifact a mode-5 test produced.

> **The forced-vs-interactive discriminator IS the mode byte** (corrected — an earlier draft here guessed it was
> "structural, both mode 1"): `mode 1` = Blue/OPTIONAL (a Press-SELECT menu hub — arm in `Main_Init`, the
> `winATE(64)` menu in a later entry; e.g. 1901 Eiko, 552 Lindblum, 206), `mode 6` = Gray/FORCED (auto-plays under
> a `DisableMove..EnableMove` lock, no menu, grey HUD banner; e.g. 956 Gargant). **Field 1901 is a mode-1 OPTIONAL
> hub, NOT forced** — the earlier read saw only its `Main_Init` arm and missed the entry-1 Eiko menu.

---

## 3. The menu, the pick, and the dispatch (all `.eb`-driven)

There is **no ATE-menu opcode**. The selectable ATE menu is a *regular* `MES`/`MESN` window carrying
`uiFlags & 64` (winATE), which only changes its *caption type*. The script then reads the chosen row and branches
itself:

```
1. ATE(mode)                      ; 0xD7 — arm the blinking prompt (mode picks Blue/Gray/force)
2. <poll SELECT in-expr>          ; B_KEYON/B_KEY, gated usercontrol==1 — the .eb polls; engine only sets the bit
3. WindowSync(win, 64, textID)    ; 0x1F + winATE — the ATE-captioned choice list
4. op_05({ op7A(9) … op7F })      ; GetChoose: push DialogManager.SelectChoice
5. op_0B(base, off0, off1, …)     ; JMP_SWITCH on the chosen row → per-ATE playback blocks
6. <per branch>                   ; winATE caption windows + Field()/PreloadField() warps + ordinary event code
```

**SELECT input:** `EventInput.Select = 1u` (`EventInput.cs:537`), OR-ed into the input word on press
(`EventInput.cs:298-301`). The engine **only sets the bit**; the field `.eb` polls it (gated `usercontrol==1`).

---

## 4. Seen-state & the ATE80 trophy (engine bookkeeping, *not* a dispatcher)

When **any** dialog closes, `Dialog.AfterHidden()` (`Global/Dialog/Dialog.cs:678`) calls
`ETb.ProcessATEDialog(this)`, which acts only on `CapType == ActiveTimeEvent`:

- **`isCompulsory = (ETb.LastATEDialogID == -1 && dialog.Id == 0)`** (`ETb.cs:413`). A *forced* ATE shows with
  window `Id==0` and no preceding menu (so `LastATEDialogID` is still −1). An *optional chosen* ATE was preceded
  by the menu window (`LastATEDialogID == 1`). `ProcessATEDialog` maintains this state machine via
  `LastATEDialogID = dialog.Id` (`:423`) with resets at `:431` (`Id==0`) and the Prima Vista crash-site
  special-case `:427` (`fldLocNo==40 && fldMapNo==206 && SC==1900 && SelectChoice==1` — "trying to avoid the ATE").
- **`MappingATEID(dialog, SelectChoice, isCompulsory)`** (`EMinigame.cs:529-673`) is a **pure int lookup** keyed on
  `(fldLocNo, fldMapNo, selectedChoice, ScenarioCounter, isCompulsory)` → a global **0–82 ATE id** (`-1` if none).
  Its only callers are `ProcessATEDialog`. **It runs no warp/cutscene** — it's purely the trophy id.
- **`ATE80Achievement(ateID)`** (`EMinigame.cs:512-527`): idempotently sets `AteCheck[ateID]=1`, counts set flags
  over `i ∈ 0..82` **excluding indices 6, 7, 14**, and `ReportAchievement(AcheivementKey.ATE80, count)`. Trophy
  target `factor = 79` (`AchievementManager.cs:326-327`) — 80 countable slots vs a threshold of 79.

**Save persistence:** `FF9StateSystem.Achievement.AteCheck` is an `Int32[100]` on the `AchievementState`
MonoBehaviour (`AchievementState.cs:11,116`, `ATE_CHECK_SIZE=100 @:106`) — a **distinct state object, NOT the
2048-byte `gEventGlobal` story heap**. Serialized as `"AteCheckArray"` under the **`"80000_Achievement"`** save
node (`JsonParser.cs:1632-1635` save / `:1720-1726` load). The kit already documents this at
`ff9mapkit/flags.py:180-184`.

---

## 5. Real-field byte patterns (extracted from `p0data` via `ff9mapkit.extract`)

Encoding: `0xD7` + a 1-byte argFlag (`0x00` = immediate) + one 1-byte operand ⇒ **`d7 00 mm` decodes to
`ATE(mm)`** (3-byte instruction).

### Flavor A — Compulsory / auto ATE (grey, unskippable, no menu)
The real forced flavor is **mode 6 (Gray + force-show)**: the field brackets its cutscene body `ATE(6) … ATE(0)`
and plays it under a `DisableMove..EnableMove` lock with a `winATE(64)` caption and NO menu — the bottom-left grey
"ACTIVE TIME EVENT" banner blinks throughout (`ActiveTimeEvent.cs`). 45 real fields do this; e.g. **field 956
(Gargant)**, reproduced in-game as a `--verbatim` fork (§7, slot 30010, armed by `[startup] scenario = 7006`).

> **Correction (2026-06-13).** An earlier draft put **field 1901 `EVT_TRENO2_TR_BHE_0` (Eiko)** here as the
> "compulsory, no menu" anchor. That was wrong — 1901 is a **mode-1 OPTIONAL Press-SELECT menu hub** (Flavor B):
> the **Eiko ATE menu** (a `winATE` list + `GetChoose` + `op_0B` jump table, in the body entry). The earlier
> teardown looked only at 1901's `Main_Init` ATE(1) arm (the `[804] ATE(1) … [873] ATE(0)` bracket) and misread
> "no menu = forced"; the menu lives in the body entry like every hub, and the `op_0B`/`GetChoose` it dismissed as
> "unrelated Treno shops" IS that Eiko menu. (The intermediate guesses `mode 6 = transition fade` and "no real
> field forces a winATE cutscene" were also wrong — see §4: mode 6 is the grey unskippable, 45 real fields.)

### Flavor B — Interactive "Press SELECT → pick one" menu (the canonical hub)
**Field 206 `EVT_DOWNSHIP_BT_FRT_0` (Prima Vista crash site)**:
```
[2640] ATE(5)                  ; force-show icon — offer the ATE
[2702] WindowSync(1, 64, 353)  ; MES, winnum 1, uiFlags=64 (winATE), textID 353 (menu list)
[2727] op_05({ op7A(9) … })    ; GetChoose test
[7751] WindowSync(1, 64, 98)   ; winATE choice list
[7757] op_05({ op7A(9) op7F }) ; push GetChoose (selected row, 0-based)
[7761] op_0B(0,1201,15,238,472,703,934)  ; JUMP TABLE on choice → per-ATE blocks
[7837] WindowAsync(0, 64, 99)  ; an ATE row's caption window (winATE) … (100,101,102 follow)
[5809] Field(208) / [7785] PreloadField(5,208)  ; the chosen ATE warps/plays its scene
```
**One-line mechanism:** `winATE(64)` window → `op7A(9)` (GetChoose) → `op_0B` jump table → each branch plays its
ATE. The engine's `ProcessATEDialog → MappingATEID → ATE80Achievement` converts the **same** `SelectChoice` into
a global ATE id **only** for the trophy; it does not pick or run the cutscene.

*(Re-confirmed by direct disassembly of field 206's `.eb` extracted from the user's `p0data` (kit `disasm`):
the exact `op_0B(0,1201,15,238,472,703,934)` and the `op_06(122, 1900→, 2005→, 2010→)` scenario dispatch in
`Main_Init` are byte-verified — see §7 for the in-game test forks built from them.)*

---

## 6. Kit (`ff9mapkit`) coverage today

- **Disassembler:** names `0xD7 → 'ATE'` with `OP_ARG_COUNT[0xD7]=1`, `OP_ARG_SIZE[0xD7]=[1]` (`eb/_optables.py`).
  A full 274-element diff of the kit's `OP_ARG_COUNT`/`OP_ARG_SIZE` vs the engine's `opArgCount`/`opArgSize`
  (`EventEngineUtils.cs`) is **byte-for-byte identical** — so the kit's `0xD7` metadata *is* `AICON`'s.
  `read_code([0xD7,0x00,0x05], 0) → ATE(5)`.
- **`--verbatim` fork carries ATEs faithfully.** `content/verbatim.py` rewrites **only** `Field` (`0x2B`)
  destinations (`remap_fields`, `struct.pack_into` at `i.off+2`); it ships the donor's **whole `.eb` + whole
  `.mes`**. Every `AICON`/`0xD7` op, the `winATE(64)` flag, and all entries pass through **byte-identical**.
- **Net-new ATE authoring — BUILT + ★ IN-GAME PROVEN (the `[ate]` primitive).** `opcodes.ate(mode)` (0xD7); `region.cond_ate_select()`
  = the menu-open gate **byte-identical to field 552** (`usercontrol==1 AND avail==1 AND B_KEYON(SELECT)`;
  `B_KEYON=0x4F`, `Select=1u`); `content/ate.py` synthesizes a SELECT-polling menu code-entry (a tag-1 loop
  reusing `content.choice` for the `winATE(64)` menu + `GetChoose` branch) + the Main_Init wiring
  (`ATE(mode)` + an own avail flag + `InitCode`). Declarative `[ate]` block wired into `build.py`
  (`collect_text` → `_apply_ate`). `tests/test_ate.py`. *(The `0x8000` high bit on the field-100
  `EnableDialogChoices` mask is still unexplained — not needed by the synth path.)*
  **Both ATE flavors are now authorable:** the interactive menu above (`[ate]`) AND the **compulsory /
  auto-advance** flavor (`[cutscene] ate = true` — the `ATE(mode)…ATE(0)` bracket + `winATE` caption, mirroring
  the real grey **mode-6** fields like 956 Gargant — NOT field 1901, which is an optional menu hub;
  `content/cutscene.py`). Offline-proven (`tests/test_ate.py`) + ★ IN-GAME PROVEN @30008 (the grey banner
  auto-plays, no press-prompt).
- **Disassembler under-naming gaps (quality-of-life):** `ATE(mode)` prints the raw int (no Blue/Gray/force
  meaning); `op_0B` shows raw with no branch-target annotation; inline `op7A(9)` isn't surfaced as
  `GetChoose`/`B_SYSVAR(9)`.

---

## 7. Emulate / export plan (north star = emulate the real game)

**Posture: verbatim-fork-first.** Reading/preserving ATEs already meets the emulate-not-recreate north star —
`--verbatim` ships the whole `.eb`+`.mes` and remaps only `Field()`, so the **entire ATE trigger + menu +
dispatch (all `.eb`/`.mes`-resident) survives byte-identical.** The only holes are (a) authoring a *new* ATE and
(b) the engine-table dependency for seen-state / global trophy id.

**The `[ate]` authoring primitive — BUILT (commits `8d50ab7` + the `build.py` wiring).** A synthesized ATE owns
its OWN availability flag, so — unlike a fork — it needs no real-beat narrative state. Declarative shape:
```toml
[ate]
prompt = "Active Time Event"   # the menu title
mode = 5                        # ATE(mode): 1 Blue / 2 Gray / 5 force-show
options = [
  { text = "What's Vivi up to?", reply = "Vivi is out shopping!" },   # reply = a narration window
  { text = "And Steiner?",       warp = 555 },                        # or warp to a cutscene field (hub->dest)
  { text = "Leave" },                                                  # last row = B-cancel
]
```
→ `ATE(mode)` + avail-flag + `InitCode(menu)` prepended to Main_Init; a menu code-entry whose tag-1 loop opens
the `winATE` menu on the real `usercontrol AND avail AND B_KEYON(SELECT)` gate and branches via `GetChoose`. Each
row reuses the `content.choice` action vocab (`reply`/`warp`/`set_flag`/…).

**The compulsory / auto-advance flavor — BUILT (`[cutscene] ate = true`).** An auto-playing cutscene styled as an
ATE: the kit brackets the cutscene body `ATE(mode) … ATE(0)` and renders its windows with the `winATE(64)` caption
— which is *also* what makes the engine tag the closed dialog `isCompulsory` (`ETb.ProcessATEDialog`). Works on
both cutscene paths (narration entry + actor-in-NPC-loop choreography). So:
```toml
[cutscene]
ate = true                 # GREY UNSKIPPABLE ATE (default ate_mode = 6): ATE(6)…ATE(0) + winATE caption windows
# ate_mode = 1             # opt-in: the quiet no-icon variant (no HUD banner under the control-lock)
steps = [ { say = "..." }, { wait = 30 } ]
```
**Two real templates — the default is the grey unskippable one:**
- **`ate_mode = 6` (grey, force-show) = the DEFAULT, the authentic UNSKIPPABLE ATE.** Real forced ATEs (956, the
  Festival cluster) use mode 6: a grey, force-shown icon that renders *even under the control-lock*, driving the
  bottom-left **"ACTIVE TIME EVENT"** HUD banner (`ActiveTimeEvent.cs`) — its grey "ATE" sprite blinks 1s on / 1s
  off (`DisplayGrayATEText`) with **no** "Press SELECT" glyph. ★ **IN-GAME PROVEN** @30008 (the kit holds `ATE(6)`
  armed across the whole body, so the grey banner blinks throughout the dialog — *more legible than real 956*,
  which clears it behind a white fade-in; this matches what players remember). Real `ATE(6)` also reproduced
  @30010 (field 956).
- **`ate_mode = 1` (Blue, no force) = the opt-in quiet variant.** mode 1's render gate (`mode>0 && ((mode&4) ||
  GetUserControl())`) fails under the control-lock, so **no HUD banner shows** — the player sees only the `winATE`
  caption windows. ★ Also proven @30008 (before the mode-6 switch). Use it for a low-key auto-ATE.
> **Avoid `ate_mode = 5`** (Blue + force): a force-shown *Blue* icon re-flashes the "Press SELECT" glyph (the Blue
> display coroutine), wrongly inviting a button press during an auto-play — the artifact the first 30008 deploy
> showed. Grey (6) suppresses that glyph; Blue (5) does not. Seen-state / the ATE80 trophy still register only on a
> real field id — the fidelity wall below.
*Remaining nice-to-haves:* disassembler QoL (name `ATE(mode)` modes, surface inline `op7A(9)` as `GetChoose`,
annotate `op_0B` targets).

**Cold-reproducing a REAL ATE in a fork — the ATE-AVAILABILITY WORD (★ IN-GAME PROVEN).** Every ATE hub's
Main_Init arms the prompt only when a story-set **availability bitmask word** in `gEventGlobal` is nonzero — for
Evil Forest (200) and Lindblum (550/552) it's the **UInt16 at byte 236** (`opDC(236)`; field 552 Main_Init
`[965] word236 != 0` → `[976] ATE(1)`, else the disarm `ATE(0)`). The game sets bits as ATEs unlock, AND the field
copies it into the menu's `EnableDialogChoices` mask (552 `[995] opD8(241) = opDC(236)`), so **each bit = one
offered ATE row**. A cold fork boots with word236 = 0 → disarm → SELECT does nothing. **THIS — not the scenario
counter — is why scenario-only forks of Lindblum/Dali showed no ATE.**

Seed it and the field arms its OWN ATE (the internal avail vars `opD0(238)`/`opC5(152)` are set BY the arm branch,
not by a prior cutscene). `opDC(N)` reads the UInt16 at *byte* N, so it's a `[startup] words` write:
```toml
[startup]
scenario = 3115                          # the content beat (Lindblum pre-festival; field 552 exits if SC < 3115)
words = [{byte = 236, value = 0x0F}]     # bits 0-3 = the 4 first-visit Lindblum ATEs (each bit = one menu row)
```
★ In-game proven: a `--verbatim` Lindblum-552 fork with this seed boots straight into the real Small-Town Knight
ATE menu, no cutscenes replayed. (Avail-word differs per region — 200/550/552 = byte 236; 1850 = 489/490/3905;
Dali-350 + 1600 need several; find a field's avail-word by disassembling it (`ff9mapkit disasm <field>`) and reading the `opDC` site that gates its ATE menu.) Low-level equivalent:
`[startup] flags` setting the word's bits (flag `N*8+bit` = byte N bit `bit`; e.g. flag 1888 = byte 236 bit 0).

**The fidelity wall (document in `FORK_FIDELITY.md`, don't fight):** ATE **trigger/menu/cutscene** = `.eb`-faithful
via `--verbatim`. But **seen-state (`AteCheck`) + the ATE80 trophy** come from C# `MappingATEID`, **keyed on real
`fldLocNo`/`fldMapNo`/`ScenarioCounter`**. So an authored/forked ATE on a **custom field id (≥4000) will NOT
register seen-state or count toward the trophy** — no `MappingATEID` switch row matches. Emulating that requires
either a **verbatim fork onto a *real* field id** (parasitic on the real `MappingATEID` row) or a **DLL
`MappingATEID` extension** (outside the no-DLL boundary).

**In-game proven (2026-06-13):**
- **Synthesized ATE** — a `[ate]` block on a custom field (`FF9CustomMap-ate` **slot 30007**): the "Active Time
  Event" prompt → SELECT → a `winATE` menu (3 authored rows) → pick shows the row's text. No carried logic.
- **Cold-reproduced REAL ATE** — a `--verbatim` Lindblum-552 fork, `[startup] scenario = 3115` + `words =
  [{byte = 236, value = 0x0F}]`, text block 276 → **slot 30006**: boots straight into the real **Small-Town Knight**
  ATE menu (4 real rows, real text, centered real window). The avail-word seed is the whole trick.
- The earlier `--verbatim` forks of two real menu hubs (1901 Eiko, 206 Prima Vista — both mode-1 OPTIONAL, not
  compulsory) confirmed `--verbatim` *carries* the bytes but a cold scenario-only fork doesn't *arm* — that's the
  avail-word, now solved (above).
- Not yet observed: the `AteCheck`/ATE80 "seen" mark does **not** fire on a custom id (no `MappingATEID` row) — the
  documented engine-table gap.

> **Kit fix this session — `[startup]` now works on scenario-jump-table fields.** The interactive-ATE hubs
> (field 206 and ~11% of fields) gate their content with a `0x06` jump table in `Main_Init`; `[startup]` must set
> the ScenarioCounter *ahead* of it. The byte-inserter (`eb/edit.insert_in_function`) previously refused any
> insert into a `0x06` function. Since the engine is uniformly IP-relative (`s1.ip += offset` for every jump,
> incl. the switch tables, `EBin.cs`), a **prepend at the function start moves the whole body wholesale and can't
> straddle anything** — so it's always safe. The inserter now allows the boundary prepend (mid-function inserts
> into a `0x06` func are still refused). This is what let the field-206 fork build.

---

## 8. Open questions / needs in-game proof

1. ~~**`op_0B` literals for field 206**~~ — **RESOLVED:** re-extracted from the user's `p0data` and byte-confirmed
   (`op_0B(0,1201,15,238,472,703,934)` + the `op_06` SC dispatch).
2. **`ATE(mode)` combos** — the common modes are now ★ IN-GAME PROVEN (mode 1 Blue @30007; mode 6 Gray+force
   @30008/30010), confirming `&3` (colour) + `&4` (force). C# still says the rest is "unknown"; exotic combos
   beyond `{0,1,5,6}` remain untested.
3. **In-game ATE-fork fidelity** — ★ RESOLVED for render/dispatch: verbatim forks' winATE menus render + dispatch
   on a custom id (real Eiko menu @30009, real grey-unskippable Gargant-956 @30010, synth menu @30007,
   Small-Town-Knight @30006). Residual: the `AteCheck`/ATE80 "seen" trophy is predicted NOT to register on a
   custom id (no `MappingATEID` row) — a non-event, not yet directly observed.
4. **The `0x8000` high bit** on the ATE-menu `EnableDialogChoices` availability mask — exact role (grey vs hide vs
   gate menu rows) undocumented in the kit; needs a focused disasm pass.
5. **The exact SELECT-poll idiom** (`B_KEYON` vs `B_KEY`) real ATE fields use — inferred, should be byte-quoted
   from field 206's open sequence (~`[2727]`).
