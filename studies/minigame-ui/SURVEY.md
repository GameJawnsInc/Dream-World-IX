# Stock minigame / UI substrate survey (2026-07-25)

> Two independent censuses — the Memoria engine source (`C:\gd\FFIX\Memoria`) and
> the 817 HW field-script exports (`C:\gd\FFIX\reference\test2\`) — run in
> parallel and CONVERGED on every headline. This file is the distilled, durable
> catalog; consumers: the fort-condor war-room UI, any future `[minigame]` lane,
> and the kit's dialog/window vocabulary. Full agent transcripts are ephemeral;
> every claim here carries its file ref.

## THE HEADLINE (both censuses independently)

**FF9 has NO number-display / gauge / score opcode.** Every live number the PC
game ever shows on a field — hunt points, auction bid, jump-rope count, frog
tally, H&C score/depth, Pandemonium altitude — is the same three generic
opcodes, re-issued from a looping code entry:

```
SetTextVariable(slot, value)      ; 0x66 — 8 slots (ETb.gMesValue[0..7])
WindowAsync(winID, flags, textID) ; 0x20 — REDRAW same winID = replace = update
CloseWindow(winID)                ; 0x21     (8 windows, Dialog.WindowID.ID0..7)
```

- The dialog engine re-renders a window **every frame its `[NUMB=n]` variables
  change** (`Dialog.cs:1409-1427` UpdateMessageValue) — the redraw loop only
  needs a dirty check.
- `flags=16` (`ETb.WindowTransparentStyle`) = body+border alpha 0 → **frameless
  floating HUD text**; `flags=4` = chat-no-tail. Position/layout live in the
  `.mes` text: `[MPOS=x,y]` `[TBLE]` `[XTAB]` `[YADD]` `[NUMB]`
  `[ICON]` `[SPRT]` (`NGUIText.cs:1490-1555`). (⚠ `[WDTH]` is DUMMIED in the
  engine — inert; reserve width with sentinel text → `studies/messages/SURVEY.md` §5.)
- **The `MinigameHUD` prefab family (jump rope / auction pad / Hippaul / chocobo
  dig button...) is MOBILE-ONLY** — `FieldHUD.DisplaySpecialHUD` opens with
  `if (!FF9StateSystem.MobilePlatform) return;` (`FieldHUD.cs:115-118`). On PC
  those prefabs render NOTHING; there is no engine dig gauge to de-hardcode.
  The overlays key on (`FF9TextTool.FieldZoneId`, mesId) or `fldMapNo` — a
  custom field on its own text block never trips them.

## The five substrates worth building on (ranked)

### 1. The live-counter HUD daemon (Festival of the Hunt shape) — ★ build first
`test2_128.txt:427-440` (field 550), duplicated VERBATIM into all 12 festival
fields: a dedicated code entry loops `if (local_mirror < global) { mirror it;
SetTextVariable(1, v); WindowAsync(6, 4, textid) } Wait(1)`. Fully portable, no
field-id gate anywhere. Three simultaneous strips (gil / wave / units) fit in
one text id — the auction already drives 5 variables in one window. Pairs with
the already-proven timer triplet (0x69/0x8D/0x7D) for clock + score.
**Kit shape:** a `[[behavior.hud]]` lane — compiler emits the daemon entry +
the `.mes` line; ticker publishes values by writing the mirrored globals.

### 2. The numeric stepper (Treno auction) — the game's numeric INPUT (★★ built as `[[numeric_input]]` + choice `recall`, FULLY IN-GAME PROVEN on bench 30417 "NUMPAD", 4 rounds — `numinput_bench.py`)
`test2_249.txt:1783-1908` (field 909, `Code10_31`): 3-digit ×100 bid stepper —
window 6 = frame + legend; windows 3/4/5 = per-digit CURSORS, each a transparent
(`flags=16`) empty-text window positioned under one digit; Left/Right swaps
cursor windows, Up/Down mutates with a hand-rolled auto-repeat ramp, ceiling
clamped vs `GetGil`, cancel = sentinel 65535. **Nine shipping fields carry this
byte-for-byte** (852/909/1600/1607/1909/2800/2950/2951/2952) — the studio's own
reusable snippet, so a kit `[[numeric_input]]` emitter has multiple goldens.
Memoria's author even ships the single-dialog modern form as a source comment:
`[NUMB=digitVar,selVar]` renders the selected digit pink (`Dialog.cs:1429-74`,
`DialogBoxSymbols.cs:161-170`).

### 3. Shop-as-hire-menu — native armoury, zero DLL (★★ built as the ITEM POOL and FULLY IN-GAME PROVEN first try — `[[behavior.pool]] item=` + `have_item` cond + `item:` hud source, bench 30418 "ARMOURY", all six beats: strip/shop/muster/crier/cap/reload — `armoury_bench.py`)
`Menu(2, shopId)` (opcode 0x75) opens `ShopUI` from ANY field, no id gate
(`DoEventCode.cs:2317-2342`; the full Menu enum: 0=main 1=name-entry 2=shop
4=save 5=chocograph; 3/6/7/8 dead). Stock lives in `Data/Items/ShopItems.csv`
(merges by shop id; ids 0-31 must survive the merge — `ff9buy.cs:23-45`), and
**the kit already ships `[[shop]] id ≥ 32` + `[[npc]] opens_shop`**
(FORMAT.md). The polling half is vanilla: expression token 0x64 `B_HAVE_ITEM`
= `GetItemCount(id)` — the kit emits it today (`content/region.py:71`). Sell
"Soldier Contract" items; the ticker converts inventory → pooled spawns.
Gotchas: the shop HARD-PAUSES field scripts (`SetEventEnable(false)`) but the
timer keeps ticking (`TimerUI.cs:205-235`) — an armoury phase, not a hot-swap
(the buy-anywhere [[choice]] poller keeps that role); stock non-equip items →
clean Item-shop type; items are real inventory (survive saves, sellable);
`AddShopItem` 0x115 can mutate the roster mid-run; the kit's encoder already
speaks the 0xFF-prefix page (`opcodes.py:44`) — only `_optables.py` arg-shape
rows past 0x10A are missing (a small add, scoped in the behavior-trees PLAN).

### 4. The QTE core (Blank sword duel, field 64) — prompt/poll/score split (★★ built as `[[qte]]` and FULLY IN-GAME PROVEN, bench 30419 "ENGARDE", 3 rounds — prompts/poll/scoring/flag/replay all pass, calibration closed at a 98 — `engarde_bench.py`; one modal entry, since stock's 3-entry split existed only for its actor choreography. THE PAR LESSON: stock's forgiveness lives in the COMBO channel, which only pays over LENGTH — short bouts need a kinder divisor, `par` default 65 at rounds=10, raise toward 80+ for stock-length bouts)
`test2_15.txt` entries 2/3/4: one entry ISSUES prompts (8 text ids, random with
a no-repeat blocklist), a PARALLEL entry polls `IsButton(mask)` per frame, a
third aggregates. The reaction timer is a countdown byte decremented by the
poller whose LEFTOVER value IS the speed bonus; combo/max-combo accumulate in
globals. Plus `EnableDialogChoices(availMask, initIndex)` (0x7C, 833 uses) —
grey out individual menu rows by bitmask (complement to our requires_flag row
VANISHING). Engine's only field-64 hook is a +30% Steam-assist rewrite
(`EMinigame.cs:9-31`) — cosmetic, skippable.

### 5. Tiles as script-driven 2D sprites — the closest thing to a custom gauge (★★ built as `[[gauge]]` and FULLY IN-GAME PROVEN, bench 30420 "WATERWORKS", 3 rounds — bars/stepper-feed/shimmer/cover/reload round 1, live shop-follow + `item:` source rounds 2-3, closed at "all checks out" — `waterworks_bench.py`)
`SetTileColor` 0x59 / `ShowTile` 0x5B / `SetTilePositionEx` 0x5A /
`MoveTileLoop` 0x5C / `SetTileAnimationFrame` 0xE7 / `AttachTile` 0x92 (follows
an actor) — ~25K combined uses; field 64 pulses a tile by a Sin-driven color.
**The build**: NOT per-segment ShowTile — `EBG_animShowFrame` decode showed a
scene ANIMATION is a list of TARGET overlays with frame *i* showing exactly
overlay *i* (255 = all off), so `[[gauge]]` generates segments+1 fill-state
PNGs as pure-Memoria overlays + one `Loop`-less (SingleFrame) ANIMATION and
drives the bar with ONE SetTileAnimationFrame per tick (level = a branchless
clamp expression inline in the opcode arg). One daemon entry for all gauges,
state in ENTRY LOCALS (stock field 64's `allocate 2` — the kit's first loc>0
mint), so `[behavior]` coexists. Scene hosts: novel .bgx / NATIVE own-scene
`USE_BASE_SCENE` hybrid (base indices read from the field's own .bgs header;
the minigame-arena path) / BG-borrow (donor-name .bgx + pinned counts;
scene-shared, bench-only). The pulse carries field 64's shade VERBATIM
(`Sin(t<<2)/360+144`, `EBG_overlaySetShadeColor` rgb/128). ⚠ REAL cameras
need `centerOffset` added to `cam.to_canvas`'s novel-field convention (this
donor: [26, 400]) — the naive spawn-column anchor landed OFF the boot view;
the bench projects the boot window and pins the bars inside it.
Two more laws from the playtests: **THE OVERLAY-TEXTURE-CACHE LAW** —
`MemoriaOverlayTextureCache` is a STATIC dict keyed by PATH, so same-name art
edits survive ~Reload showing the OLD texture; gauge art ships with sha1
CONTENT-HASHED filenames (changed art = new path = true hot reload) at 4×
texel resolution on canvas-size quads (uniform cells under the engine
upscale). And a saturation lesson: a gil bar showing FULL against a small
`max` IS the live read working — calibrate `max` to the expected range
(round 1's "nothing when buying" was a ≥5000 purse pegging max=5000).
Text-side alternative (unbuilt): `[TBLE=bank]` value-indexed string swap
(`ETb.cs:270-283`) — one `.mes` entry holding N bar states indexed by a
`gMesValue` slot.

## Smaller confirmed facts (keep, they cost playtests elsewhere)

- **`AddShopItem` 0x115 — ★★ FULLY IN-GAME PROVEN (ARMOURY rounds 2-4)** as the
  `add_shop_item`/`remove_shop_item` behavior verbs (event-Once lane, remove-then-add
  idempotence, unknown-shop lint). Session semantics decoded: `ff9buy.ShopItems` is a
  STATIC process table — mutations survive New Game AND ~ Reload, reset only at
  relaunch. Two laws minted en route: THE INVENTORY-SNAPSHOT LAW (have_item reads a
  top-of-tick mirror; the pool's live consumption raced a live read) and THE
  DRAINING-CONDITION LAW (one branch/unit/tick — several once-effects on a transient
  moment must flag-latch it). **`AddShopSynthesis` 0x116 — ★★ ALSO FULLY PROVEN
  (ARMOURY round 5, "phoenix down forges")** as `add_shop_synth`/`remove_shop_synth`:
  the mutation is INVERTED (shop grafted onto the RECIPE, guard on the recipe);
  result-NAME selectors resolve to the deterministic CSV mint (keyed by resolved item
  id); lint refuses BUY-shop targets; THE HIDDEN-RECIPE IDIOM = declare the locked
  recipe on a PARKED shop id, graft the real shop at runtime.
- **`0xAE MINIGAME` (Tetra Master)** launches from any field but is a FLOW
  TERMINATOR (`return 7`) — must be the last thing its function does; gate on
  `B_SYSVAR[19]` ≥ 5 cards (`DoEventCode.cs:2378-86`). The uid-keyed
  `EMinigame.Set*Id` helpers are inert on custom fields.
- **`AddFrog` 0xE0 / `GetFrogAmount`** — the game's ONE engine-backed counter
  opcode (writes THE frog counter; field-agnostic).
- **Name entry** = `Menu(1, charId)` — renames a real PLAYER; not a generic
  string prompt. **Party select** = `0xB2 PARTYMENU(minSize, lockedMask)`.
- **`Bubble` 0x68** ("!"/"?" over the player) and **`ShowHereIcon` 0xEF**
  (mode 3 = unconditional) — free 1-bit HUD sprites. `WIPERGB` 0xEC = screen
  flash; `GAMEOVER` 0xF5 exists.
- **`GetTimerTime` is additive-extendable mid-run** — `ChangeTimerTime(
  GetTimerTime + 10)` is H&C's time-bonus idiom (`test2_221.txt:1562`); the cut
  minigame in field 1853 (`test2_513.txt:1046-1230`, text-stripped but wired)
  even does score-extends-clock.
- **`gScriptVector` is SAVE-PERSISTED** (`JsonParser.cs:521-545`) — the
  behavior compiler's size←0/size←n table seed is what keeps stale saves inert;
  keep it law.
- **Custom NGUI HUD panel (DLL path, when script windows hit their limit):**
  ~150-250 lines cloning `TimerUI.cs`'s lifecycle (Singleton + prefab +
  `AddChild(UIManager…)`), labels via `NGUITools.AddWidget<UILabel>`, bar donor
  `APBarHUD` (UISlider); drive it by READING `ETb.gMesValue` each frame so the
  field script's plain `SetTextVariable` is the whole wire protocol — no new
  opcode. ~8 of the ~20 NGUI construction laws apply (no list/scroll laws).
  An order of magnitude smaller than the s45 codex screen.
- Rival-bidder AI (auction): per-NPC private budget in ENTRY LOCALS seeded
  `base*(rand&255+128)/256` (`test2_249.txt:1953-83`); the Nero shuffle carries
  the double-or-nothing ante loop (`test2_518.txt:1290-1325`); the frog ponds
  carry the bitmask spawn pool + per-actor local wander/flee
  (`test2_182.txt:3161-3255`). Ragtime Mouse is battle-side, nothing to mine.
- `CloseAllWindows` 0xEB and `PreventWindowInit` 0x53 exist in the engine and
  are used by ZERO shipping fields — free real estate, but verbatim-first says
  bench them before trusting them.

## What this buys fort-condor, concretely

1. A real HUD row — `Gil 1250 | Units 8/20 | Depot 24` — as one transparent
   window + three SetTextVariables from the ticker (substrate #1). No DLL.
2. The war council can grow a "how many?" count picker (substrate #2) and/or an
   armoury SHOP phase between waves (substrate #3) with native gil handling.
3. Wave banners ("WAVE 2 — southwest!") = a second window slot, event-Once
   announces already do the timing.
