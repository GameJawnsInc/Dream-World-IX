# Guest field-interaction suppression: chests + talk — a source census

**Status:** research only, nothing implemented. Read-only pass over `C:\gd\FFIX\Memoria\` (live engine
tree, source of truth — current at time of research, DLL tree ahead of the patch stack with uncommitted
s42), the `memoria-patches\s36-netsync-ghost.patch` / `s38-netsync-spectator-field.patch` sidecars, the
`studies\battle-coop\inventory-authority.md` census, the kit's `ff9mapkit\ff9mapkit\content\*.py`
(chest.py, coop.py, npc.py, region.py, savepoint.py, shop.py, mognet.py), and one real stock chest
transcript (`C:\gd\FFIX\reference\test2\test2_57.txt`, field 200 "Prima Vista/Hallway", `ChestA_*`). All
engine cites are `file:line` against the live tree unless marked otherwise. Companion documents in this
same directory (`camera.md`, `surface-sweep.md`) cover the other polish-round agents' scope (camera
follow, gateway suppression, platforms/ladders, dialogue/ATE mirroring, and a broader menu-family sweep
that independently corroborates several findings here).

---

## 1. The field interaction input path, end to end

### 1.1 STARTING a new interaction — the single choke point

There is exactly **one** call site that can begin a brand-new tag-3 (talk) interaction for the
player-controlled actor: `EventCollision.CollisionRequest(PosObj po)` (`EventCollision.cs:236`).

It is invoked once per rendered game-loop tick, for the controlled actor only, from two sites in
`EventEngine.ProcessEvents()`:

- **Field mode (gMode==1):** `EventEngine.ProcessEvents.cs:181`, inside a block gated on
  `obj.uid == this._context.controlUID` (`:177`) **and** `this.GetUserControl()` (`:180`, defined at
  `EventEngine.cs:1415-1418` as `this._context?.usercontrol == 1`).
- **Overworld mode (gMode==3):** `EventEngine.ProcessEvents.cs:69`, same-shaped gate at `:55-59`
  (`obj.uid == controlUID && this._context.usercontrol != 0`).

Inside `CollisionRequest` (`EventCollision.cs:236-312`), two independent sub-checks feed a **new**
tag-3 `Request`:

- `EventCollision.CheckNPCInput(po)` (`EventCollision.cs:85-117`, called at `:242`) — for NPC-shaped
  actors (`cid==4`).
- `EventCollision.CheckQuadInput(po)` (`EventCollision.cs:60-83`, called at `:279`) — for quad/region
  objects (`cid==3`).

Both share the identical shape:

```csharp
UInt32 interactInput = ETb.KeyOn() & (instance.gMode != 1 ? EventInput.Confirm : (EventInput.Confirm | EventInput.Special));
if (interactInput > 0u) {
    Obj obj = /* find the talkable target in range */;
    if (obj != null && Is{NPC,Quad}Talkable(po, obj)) {
        ...angle/range checks...
        if (instance.Request(obj, 1, 3, false)) { ClearPathFinding(po); return true; }
    }
}
```

(`EventCollision.cs:63,67-69,75` for the quad form; `:88,93,95-96,99,108` for the NPC form.)

`ETb.KeyOn()` (`ETb/ETb.cs:65-70`) returns `ETb.sKeyOn`, a **press-edge** mask (`inputs & ~previousKey`,
computed once per tick in `ETb.ProcessKeyEvents()`, `ETb.cs:50-56`) sourced from `ETb.GetInputs()` →
`FPSManager.DelayedInputs` (`ETb.cs:58-63`). `FPSManager.DelayedInputs` is populated by
`EventInput.ReadInputLight()` (`Memoria/Application/FPSManager.cs:124-138`, calling
`EventInput.ReadInputLight()` at `EventInput.cs:216-247`, which itself calls
`EventInput.ProcessInput()` → `EventInput.GetKey()` → `UIManager.Input.GetKeyTrigger/GetKey`
(`EventInput.cs:260-356`). This is the **B_KEYON opcode's own underlying data source** — the `.eb`
opcode `B_KEYON` (0x4F/79) reads the *same* `ETb.KeyOn()` value (`EBin.cs:1078-1084`,
`case op_binary.B_KEYON: ... _v0 = (Mathf.Abs(EvaluateValueExpression() & ETb.KeyOn(...)) <= 0) ? 0 : 1;`).
So the engine-level "is a new interaction being requested" check and a `.eb` script's own internal
`IsButton(...)` poll are **the same physical read**, just consumed from two different call sites (one
in C#, one from bytecode).

Target resolution: `EventCollision.CheckQuadInput` finds its target via
`instance.TreadQuad(po, 4)` (`EventCollision.cs:66`) → `EventEngine.TreadQuad(po, mode)`
(`EventEngine.TreadQuad.cs:6-22`), which computes `tagID = (mode & 4) == 0 ? 2 : 3` (`:11`) and scans
`_context.activeObj` for a `cid==3` object **that has a defined tag-3 function** (`GetIP(obj2.sid, tagID,
...) != nil`, `:15`) in range. **A quad with only a tag-2 (Range) function and no tag-3 can never match
`TreadQuad(po, 4)`** — it is structurally invisible to `CheckQuadInput`. This is the load-bearing fact
for §4.

Dispatch itself: `instance.Request(obj, 1, 3, false)` (`EventEngine.cs:336-346`) does
`ip = GetIP(p.sid, 3, p.ebData); if (ip != nil) this.Call(p, ip, level, ew, null);` — `Call`
(`EventEngine.cs:356-371`) sets `obj.ip = ip; obj.level = level; obj.wait = 0;`, i.e. it **begins**
executing the target's tag-3 function from its start. `Request` also gates on `level < p.level`
(`EventEngine.cs:339`) — a currently-running interaction at level 1 cannot be re-`Request`ed at level 1
while it is mid-flight, so `CollisionRequest` structurally cannot re-enter an object that is already
running its own talk function.

### 1.2 ADVANCING an already-open dialogue window — a completely separate path

A `WindowSync` opcode (`MES`, `EBin.event_code_binary` `0x1F`, handler at
`EventEngine.DoEventCode.cs:410-460`) ends with `this.gCur.wait = 254; return 1;` (`:458`). `254` is the
engine's "wait for a window to close" sentinel, consumed generically in `EBin.ProcessCode`
(`EBin.cs:136-157`):

```csharp
if (s1.wait != 0) {
    if (s1.wait == 254) {                       // EBin.cs:138 — "Wait for a window to close"
        if (s1.winnum == 255) s1.wait = 0;
        else if (!ETb.MesWinActive(s1.winnum)) { s1.winnum = 255; s1.wait = 0; }
    } else if (s1.wait != 255) s1.wait--;
    next0(); continue;
}
```

The blocked object's script is **not** polling `B_KEYON` at all while waiting — the interpreter itself
skips it every tick until `ETb.MesWinActive(winnum)` goes false. The window is closed by a **wholly
separate consumer of the physical Confirm button**: `UIKeyTrigger.HandleDialogControlKeyPressCustomInput()`
(`UI/UIKey/UIKeyTrigger.cs:798-825`, called every `Update()` frame from `:182`), which reads
`PersistenSingleton<HonoInputManager>.Instance.IsInputDown(ctrl)` **directly** (`:807,815,818`) — this
does **not** go through `ETb.KeyOn()`/`FPSManager.DelayedInputs`/the `B_KEYON` opcode at all — and calls
`PersistenSingleton<UIManager>.Instance.Dialogs.OnKeyConfirm(activeButton)` (`:810`) to close/advance the
window. Once the window closes, `EBin.ProcessCode`'s wait-254 check clears `s1.wait` on its own and the
object's script resumes on the *next* tick.

### 1.3 Answer to "is there a clean engine-level distinction?" — **YES**

| | STARTING | ADVANCING |
|---|---|---|
| Entry point | `EventCollision.CollisionRequest` → `CheckNPCInput`/`CheckQuadInput` (`EventCollision.cs:60-117,236-312`) | `UIKeyTrigger.HandleDialogControlKeyPressCustomInput` (`UIKeyTrigger.cs:798-825`) |
| Reads Confirm via | `ETb.KeyOn()` (press-edge, same source the `B_KEYON` opcode reads) | `HonoInputManager.IsInputDown` directly |
| Consumes | An **idle** controlled actor's per-tick collision/tread scan | A **running** dialog UI's per-`Update` poll |
| Effect | `EventEngine.Request`→`Call` (`EventEngine.cs:336-371`) — begins a NEW tag-3 execution | `Dialogs.OnKeyConfirm` — closes/advances the UI, which lets `EBin.ProcessCode`'s wait-254 check (`EBin.cs:138-148`) resume the ALREADY-running script |

Neither path calls the other. A guard placed anywhere in `CollisionRequest`/`CheckNPCInput`/
`CheckQuadInput`/`EventEngine.Request` (i.e. the STARTING lane) is structurally incapable of touching
window-advance, because window-advance never reaches those functions.

**One nuance:** a `.eb` script *can* poll `B_KEYON` **itself**, from inside an already-running tag-2
(Range/tread) function, entirely bypassing `CollisionRequest`/`Request(obj,1,3,...)`. This is exactly
how stock treasure chests are dispatched — see §2/§4.

---

## 2. The stock `.eb` chest idiom

Ground truth: `C:\gd\FFIX\reference\test2\test2_57.txt` (field 200, "Prima Vista/Hallway"),
`Function ChestA_Init` / `Function ChestA_Range` (lines 937-1043), matching `ff9mapkit`'s own
`content/chest.py` docstring provenance note ("field 200 entry 9; field 407 entries 12/22").

**Dispatch tag:** the real chest has **no tag-3 function at all** — only `ChestA_Init` (tag 0) and
`ChestA_Range` (tag 2, i.e. the tread/Range function, entered via `instance.TreadQuad(po, 2)` +
`Request(obj, 1, 2, false)` at `EventCollision.cs:281,284`, which is **unconditional** — gated only by
`CheckQuadPush` (`EventCollision.cs:363-...`, a field-id special-case table with no button read, default
`true`), not by any Confirm check). `ChestA_Range` runs **every tick** the player treads its quad. The
Confirm gate lives **inside the function body**, as the disassembled transcript's `IsButton(655360L)` —
`0xA0000` = `EventInput.Confirm (0x20000) | EventInput.Special (0x80000)`, the exact mask
`CheckNPCInput`/`CheckQuadInput` build at the C# layer (§1.1) — reading the same `ETb.sKeyOn` state,
just from bytecode instead of from `EventCollision.cs`.

**The idiom, byte-for-byte** (`test2_57.txt:959-1043`):
```
Function ChestA_Range
    ifnot ( IsMovementEnabled ) { return }
    if ( (!VARL_GenBool_7244) && VAR_LocUInt8_0 ) {   // not yet opened, and Init finished
        Bubble( 1 )                                    // the floating "!" prompt
        if ( IsButton(655360L) ) {                      // Confirm|Special, THIS FRAME
            ... DisableMove/DisableMenu bracket ...
            RunSoundCode3(...) x2                       // lid-creak SFX
            RunAnimation( 7336 ); WaitAnimation()        // lid opens
            if ( GetItemCount(112) < 99 ) {
                Wait( 2 )
                if ( VARL_GenBool_7244 == 0 ) {
                    RunSoundCode3(...)                   // item jingle
                    set VARL_GenBool_7244 = 1            // <<< THE ONCE-FLAG, SET HERE
                    SetTextVariable( 0, 112 )
                    AddItem( 112, 1 )                    // <<< THE ITEM-GRANT OPCODE
                    WindowSync( 7, 0, 70 )                // <<< THE MESSAGE, AFTER THE FLAG
                }
            } else { WindowSync( 7, 0, 74 ) }            // "Cannot carry another Item."
            ... EnableMove/EnableMenu bracket ...
        }
    }
    return
```

**The chest convention, precisely:** the once-flag (`VARL_GenBool_7244 = 1`, a save-persistent
`GLOB_BOOL`) is written **before** `AddItem`/`WindowSync` (line 999, vs. `AddItem` at 1002 and
`WindowSync` at 1003) — so a re-entrant press (or, relevantly, a second machine independently evaluating
the same script) that lands *while the Received box is still open* sees the flag already set and takes
the `else` branch on the next evaluation, rather than double-granting. `ff9mapkit`'s own `coop.py`
independently names this exact convention verbatim: *"The flag is set BEFORE the message (FF9's
treasure-chest convention) so the gate can't double-fire while the window is open"*
(`content/coop.py:151-152`).

**The kit's own `[[chest]]` content, by contrast, uses a *different* dispatch tag.** `content/chest.py`'s
docstring says so explicitly (`chest.py:17-20`): *"real chests put the open in the object's tag-2 RANGE
function... the kit uses the object's tag-3 talk handler (press X while near)... a different dispatch
tag."* `build_chest_open` (`chest.py:133-150`) also orders its writes differently — `give` (the
`AddItem`/`AddGil`) then `set_text_variable`+`window_sync` (the message) **then** `_region.set_var(...,
1)` (the flag latch) at `chest.py:147`, i.e. flag **after** message, the reverse of the stock
convention. This matters directly for §4: it means a kit-authored `[[chest]]` **is** reachable through
the tag-3 `CollisionRequest` path, while a **verbatim-forked real chest is not**.

---

## 3. Today's behavior when a following guest opens a chest

**Which chest is reachable depends on its shape** (§2): a kit-authored `[[chest]]` (tag-3) is reachable
identically to any NPC talk. A verbatim-forked real chest (tag-2, internal `B_KEYON`) is *also* reachable
today, because nothing currently gates either path for a netsync guest — s38 deliberately left tag-2 and
`B_KEYON` untouched (per project brief: "s38 deliberately did NOT block tread regions... or dialogue/
B_KEYON").

**What writes land, and where:**

1. `AddItem`/`AddGil` (opcode `0x48`/`0xCE`; `ITEMADD` handler cited at
   `EventEngine.DoEventCode.cs:1433` per `studies\battle-coop\inventory-authority.md:166`) executes
   **locally on the guest's own EventEngine instance**, mutating the **guest's own real**
   `FF9StateSystem.Common.FF9.item` bag. There is no host/guest shared object — host and guest are
   separate processes on separate machines, each running its own `EventEngine`/`ETb`/bag.
2. The once-flag write (`GLOB_BOOL`/`gEventGlobal` bit) also lands in the **guest's own**
   `FF9StateSystem.EventState.gEventGlobal` array.
3. **That flag write is transient.** `NetSyncClient.ApplyStoryBeforeEvents()`
   (`Memoria/Netsync/NetSyncClient.cs:201-205`) is called from `HonoluluFieldMain.cs:135` on every field
   load, **before** `Main_Init` reads any GLOB var (comment at `HonoluluFieldMain.cs:135`: "co-op: a
   following guest mirrors the HOST's gEventGlobal before Main_Init reads it"). Its
   `ApplyStoryImpl()` (`NetSyncClient.cs:207-247`) calls `NetSyncState.ApplyStory(host)`
   (`NetSyncState.cs:79-88`) → `ApplyStoryTo` (`:92-115`), which overwrites **every byte of the guest's
   `gEventGlobal` outside indices [2032,2041]** (`MaskLo`/`MaskHi`, `NetSyncState.cs:35-36,107-109`)
   with the host's last-broadcast snapshot. A chest's once-flag is not in that 10-byte coop-cell mask, so
   the **next field re-entry silently reverts it to whatever the host's own chest state is** — "the chest
   is closed again," exactly as `inventory-authority.md`'s "★ THE LIVE DEFECT" section documents
   (re-verified above against the current live tree, not just the prior study).
4. **There is no guest→host write channel on the field.** An engine-wide grep of the live Netsync tree
   for the item-mutation primitives returns zero hits — re-verified directly for this task:
   `grep -rnE "FF9Item_Remove|FF9Item_Add|FF9Item_Set" Assembly-CSharp/Memoria/Netsync/` → **exit 1, no
   matches** (checked against the current `C:\gd\FFIX\Memoria` tree). The mirror
   (`NetSyncState.ApplyStory`) is a strictly one-directional HOST→GUEST overlay; nothing in `Netsync/`
   ever mutates the host's bag or the host's `gEventGlobal` from guest-side data.

**What the HOST sees:** nothing. The host's own `EventEngine`/`gEventGlobal`/bag are on a different
machine/process and are never touched by anything the guest's local script does. The host's own copy of
that same chest object remains exactly as it was — closed if the host hasn't opened it, its own flag byte
unaffected. There is no visual or state change on the host's screen from a guest-side chest open.

**Net effect, restated precisely:** for a **kit-authored (tag-3) chest**, repeated field re-entry lets a
guest re-open it and re-grant the item every time (session-scoped, discarded by the exit ramp
(`NetSyncState.cs:117+`, "SESSION EXIT RAMP") on session end, but live and player-visible for the
duration — "an unbounded local item farm," per `inventory-authority.md:33`). For a **verbatim-forked
(tag-2) chest**, the exact same mechanics apply — it is *not* actually closed by s38 today (§4) — the
prior study's characterization ("theater, not corruption") still holds: the item lands in the guest's bag,
nothing on the host ever reads it, and the exit ramp erases it from disk, but the client-side illusion of
having looted a chest the host never touched is exactly as reproducible as the kit-chest case.

---

## 4. Choke-point evaluation for suppressing guest-INITIATED interactions

Constraint recap: must NOT break (a) advancing an already-open window, (b) tread regions/`[[coop]]`
plates and gateways, (c) auto-fired non-talk events. Guard convention already established by s38:
`Memoria.Netsync.NetSyncClient.IsMirroringStory` (`NetSyncClient.cs:269-272`, true "while a following
guest's live gEventGlobal holds the HOST's story," armed at `NetSyncClient.cs:242` right after a
successful `ApplyStory`, and remaining true through the follow session until the exit ramp fires).

### Option A — gate `EventCollision.CheckNPCInput` / `CheckQuadInput` (the talk-range/interaction-check site)

Add `if (Memoria.Netsync.NetSyncClient.IsMirroringStory) return false;` at the top of
`EventCollision.cs:85` (`CheckNPCInput`) and `:60` (`CheckQuadInput`) — matching the existing s38 pattern
at, e.g., `UIKeyTrigger.cs:678,834` and `EventEngine.DoEventCode.cs:971,984`.

**Blocks:** the `Request(obj,1,3,...)` call that *begins* a tag-3 interaction — kit-authored NPCs
(talk), kit-authored `[[chest]]` (tag-3 per §2), kit-authored `[[shop]] zone=`/`[[savepoint]]` regions
(both use `_region.INTERACT_TAG = 3`, §5), and any real stock NPC/region whose "talk" is dispatched
through this same tag-3 lane (the majority of talkable NPCs, per `npc.py:6` — "`_SpeakBTN` (func tag 3)"
is the standard NPC shape carried by verbatim forks too).

**Structurally cannot leak into:** tag-2-only objects. `TreadQuad(po, 4)` (`EventEngine.TreadQuad.cs:11,
15`) only ever matches an object that has a **defined tag-3 function**; a pure tag-2 body (a `[[coop]]`
plate, a gateway, a stock chest) is invisible to `CheckQuadInput`'s target search regardless of this
patch. Window-advance is untouched (§1.3 — disjoint code paths). Auto-fired tag-2/tag-10 events are
untouched (they don't route through `CheckNPCInput`/`CheckQuadInput` at all).

**Leaks (does NOT block):** the verbatim-fork chest idiom (§2/§3) and any other tag-2 body that reads
`B_KEYON` internally — this includes, per independent cross-check in `world/entrance.py:218-289`, the
kit's own `--action-prompt` walk-up gateway ("`[FICON][B_KEYON(Confirm)][JZ->RET]...[Field][RETURN]`" —
same tag-2-with-internal-poll shape as a chest), and per `content/mognet.py`/`content/savepoint.py`
provenance notes, likely some stock Mognet moogle interactions if any use the same idiom (not verified
here — see §5's flag).

**Hazard class:** none of the gArgUsed-trap kind. `CheckNPCInput`/`CheckQuadInput`/`CollisionRequest` are
plain C# methods, not opcode handlers inside `EventEngine.DoEventCode`'s per-statement switch — they
never call `getv()`/consume `gArgFlag`, so `commandDefault2`'s IP-rewind-on-unconsumed-arg mechanism
(the trap CLAUDE.md documents, concretely demonstrated at `EventEngine.DoEventCode.cs:966-970` for the
`ENCOUNT` gate) simply does not apply to this choke point. The refusal also happens **before**
`EventEngine.Request`/`Call` ever runs (§1.1), so no object's `ip`/`wait`/`level` is ever touched by a
suppressed attempt — there is no half-started interaction to leave in a bad state, no per-frame IP-rewind
risk of any kind.

### Option B — mask the `B_KEYON` opcode's Confirm/Special bits while mirroring (the underlying-read site)

Patch `EBin.cs:1078-1084` (or `ETb.KeyOn()` itself) to force the Confirm/Special bits out of the returned
mask while `IsMirroringStory`.

**Blocks:** everything Option A blocks, **plus** the verbatim-fork chest's internal `IsButton(655360L)`
poll (§2) and the `--action-prompt` walk-up-gateway idiom (`world/entrance.py:218-289`) — both read the
identical underlying data.

**Leaks/breaks:** this is coarser than it looks. It reads as "block Confirm for interaction-starting
purposes," but `B_KEYON` is a generic bit-test opcode reused for **any** button, on **any** object,
for **any** purpose a script author chose — the ATE trigger is the clearest counter-example
(`content/ate.py:14,21,70`, `content/region.py:97-98,246-255`): `if (usercontrol AND avail AND
B_KEYON(SELECT))`. That specific case tests the `Select` bit (`0x1u`), not `Confirm`/`Special`
(`0x20000`/`0x80000`), so a Confirm-only mask happens not to break ATEs — but it demonstrates the opcode
has no reserved "interaction-start" semantics; it is load-bearing for whatever the field author wired to
it. The concrete, already-identified breakage: it **also** disables the action-prompt gateway idiom
(`world/entrance.py`), which the design brief explicitly wants to keep working (tag-2 regions "including
gateways" are meant to stay live for a following guest). It would not break window-advance (§1.3, disjoint
path) or `[[coop]]` plates (verified: `content/coop.py`'s `gate_range_body`/`hold_loop_body`
(`coop.py:145-163,197-...`) read only `_region.MOVEMENT_GATE` + `cond_peer_in_rect`/presence — **zero**
`B_KEYON`/`KEYON` references anywhere in `coop.py`, confirmed by grep). This is exactly why
`inventory-authority.md`'s Rung-2 note calls a blanket B_KEYON mask "risky — it risks wedging any script
that polls a button" (`inventory-authority.md:280-282`) rather than recommending it outright.

**Hazard class:** `B_KEYON`'s handler (`EBin.cs:1078`) is an **expression-opcode** case inside
`EBin`'s RPN stack evaluator (`EvaluateValueExpression()`), not a **statement-opcode** case inside
`EventEngine.DoEventCode`'s per-tick switch — it has no `getv()`/`gArgFlag`/`commandDefault2` involvement
at all (confirmed: the case body is two stack pops, no `getv*()` calls), so the gArgUsed trap does not
apply here either. No IP-rewind hazard for the same reason as Option A — the read happens mid-expression,
well before any statement-level dispatch/rewind logic runs.

### Option C — mask the raw input source (`EventInput.ReadInput`/`ReadInputLight`, or `HonoInputManager`)

**Blocks:** everything B blocks, at an even lower layer.

**Leaks/breaks:** **worse than B, likely fatal to the "don't break window-advance" constraint.**
`UIKeyTrigger.HandleDialogControlKeyPressCustomInput` (§1.2) reads
`PersistenSingleton<HonoInputManager>.Instance.IsInputDown(ctrl)` **directly** (`UIKeyTrigger.cs:807,
815,818`) — a *different* consumer than `ETb`/`EventInput`'s `FPSManager.DelayedInputs` pipeline
(`FPSManager.cs:124-138` calls `EventInput.ReadInputLight()`, a *separate* code path from whatever masks
`HonoInputManager` at the source). Masking at `EventInput.ReadInput`/`ReadInputLight` would leave
`HonoInputManager.IsInputDown` unaffected (so window-advance would still work) but is functionally
identical to Option B for the `.eb`-visible Confirm bit, with strictly more blast radius (every other
`EventInput` consumer in the file — menus, chocobo digging, minigames, `IsMenuON`, etc. — see
`EventInput.cs:39-58,193-213`). Masking at `HonoInputManager` itself (the true "raw" layer) would **also**
break window-advance, since `UIKeyTrigger` reads it directly. **Not recommended** — no additional benefit
over Option B and materially higher risk of hitting the excluded (a).

### Recommendation

**Ship Option A now** (gate `CheckNPCInput`/`CheckQuadInput` on `IsMirroringStory`) as the primary,
low-risk fix. It closes the entire kit-authored interaction surface — NPCs, `[[chest]]`, `[[shop]] zone=`,
`[[savepoint]]` (§5) — which is the surface the kit actually *ships* content on, with a two-line diff in
the exact style of the existing s38 gates, zero gArgUsed exposure, and zero risk to (a)/(b)/(c).

**Layer Option D on top (new, not enumerated above but falls out of the census): gate the `MENU` opcode**
(`EventEngine.DoEventCode.cs:2297-2311`, `0x75`) on `IsMirroringStory`, using the exact
getv-before-return pattern already proven safe at the `ENCOUNT` gate (`DoEventCode.cs:966-971`: both
`getv1()` calls MUST execute before the early `return 0`, or `commandDefault2` rewinds the IP and the
opcode spins forever — **this is the one site in this whole census where the gArgUsed trap is live and
must be respected**). This does not touch chests (they never call `Menu()`) but closes the
save/shop/party-change/Mognet **menu-opening** family regardless of how the request reached it (tag-3 or
tag-2-internal-B_KEYON) — see §5. `studies\field-coop\surface-sweep.md` (a sibling agent's independent
sweep) arrived at the identical `Menu()`-opcode recommendation for the same reason and explicitly flagged
coordinating rather than building two overlapping gates — corroborating evidence, not this agent's
finding alone.

**Leave the verbatim-fork chest's internal-`B_KEYON` hole open for now.** It is real (§3), but per
`inventory-authority.md`'s own prior verdict (independently re-confirmed here): it is session-scoped
theater, not corruption, and the only available closes (Option B/C) either break the action-prompt
gateway idiom outright or add first-class new risk with no corresponding severity justification. A
future, more surgical fix would need to distinguish "chest-shaped" tag-2 bodies from "gateway-shaped"
tag-2 bodies by pattern (proximity + `Bubble` + `IsButton` + `AddItem`/`AddGil` + `WindowSync`, vs.
proximity + `Bubble` + `IsButton` + `Field()`), which is a per-field content classification problem, not
a clean engine choke point — out of scope for an engine-level suppression pass.

**Fields requiring a talk to proceed:** irrelevant for a spectator by design. The guest's own story
progression is never authored by the guest completing an interaction — `NetSyncState.ApplyStory`
(§3.3) overwrites the guest's `gEventGlobal` from the host's snapshot at every field load, and the
autoload exit ramp (`NetSyncState.cs:117+`) discards all session-local guest state on session end. A
guest who can never *start* a talk never needs to, because their story state was never theirs to advance
in the first place while mirroring.

---

## 5. Savepoint moogle / shop / Mognet — do they ride the same path?

**Yes, for the kit's own authored content — one choke point (Option A) covers all three.**

- **Savepoint moogle:** `savepoint.py:9` — "always a type-2 entry, 3 funcs, tag 3" (matches the real
  donor: `savepoint.py:51-52,240` cite "field 300 (Ice Cavern/Entrance) entry 3 tag 3"). The
  region-shaped variant (`savepoint_region`, `savepoint.py:606-618`) explicitly assembles
  `(0, init), (_region.RANGE_TAG, tread), (_region.INTERACT_TAG, action)` — `RANGE_TAG=2` for the
  tread-only `Bubble(1)` "!" prompt, **`INTERACT_TAG=3`** (`content/region.py:113-115`) for the actual
  save dispatch. This is the proper tag-3 lane, reachable by `CheckQuadInput`/`TreadQuad(po,4)`, not the
  chest's internal-poll idiom.
- **Shop:** identical shape. `shop.py:89-97` (`shop_region`) assembles the same
  `(0,init),(RANGE_TAG,tread=Bubble),(INTERACT_TAG,action=shop_dispatch)` triple; the NPC-opener variant
  (`shop.py:60-66`, `shop_speak_body`) is a plain tag-3 `_SpeakBTN`-style body.
- **Mognet:** the kit's minted 42nd-moogle identity rides the **savepoint moogle's own tag-3 talk menu**
  (per the project brief §10's Mognet entries — "the 42nd moogle... joins FF9's real letter network,"
  wired through the same save-moogle NPC object) — same tag-3 lane, same choke point.

Once inside any of these (the menu is open), subsequent navigation is menu-cursor input (row
select/confirm), which — like dialogue-window-advance (§1.2) — is a UI-level consumer, not a re-entrant
`CollisionRequest` call; Option A's single refusal-at-the-door is sufficient and does not need to also
suppress in-menu navigation once a session has (in the non-mirroring case) legitimately started.

**Caveat — flagged, not resolved here (explicitly another agent's territory per `surface-sweep.md`):**
`surface-sweep.md:89-133` independently censuses this same family from the "what happens today" angle and
recommends the complementary `Menu()`-opcode gate (§4 Option D) specifically because it also covers
**stock, non-kit shop/save/Mognet dialogue** reached via ordinary dialogue-choice `B_KEYON` polling
(untouched by s38, per that document's B.1-B.3), which is a superset this agent's census did not
independently re-derive byte-for-byte. Recommend the two gates (Option A tag-3 refusal + Option D `Menu()`
refusal) ship together, per that document's own recommendation, rather than treating Option A alone as
closing the whole menu-family surface.

---

## Method note

Every C# claim above was re-checked against the live `C:\gd\FFIX\Memoria` tree during this pass (not
trusted from prior study prose alone) — in particular the `IsMirroringStory` definition/arming site, the
`NetSyncState.ApplyStory` mask bounds, the zero-hit item-mutation grep in `Netsync/`, and the `MENU`
opcode's `getv1()`/`getv1()`/return shape — because the brief noted the live tree is ahead of the patch
stack (uncommitted s42) and memory files carry an explicit staleness warning. One correction found by
this re-verification: `inventory-authority.md:166` cites the `ITEMADD` (`AddItem`, opcode `0x48`) handler
at `DoEventCode.cs:1433` — independently re-read for this task, it is actually at
**`DoEventCode.cs:1442`** in the current tree (a ~9-line drift, presumably from intervening edits between
that study and this pass). Not load-bearing for §1-§4's engine-choke-point argument (the chest's write
path matters for §3's *effect*, not for where to *gate*), but flagged since the brief asked for
file:line precision on every engine claim and the prior figure no longer matches.
