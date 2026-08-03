# FF9 message / text-box survey — the complete map (2026-08-03)

> Three censuses run in parallel and cross-checked: the Memoria engine source
> (`C:\gd\FFIX\Memoria\Assembly-CSharp\`), all 817 HW field-script exports
> (`C:\gd\FFIX\reference\test2\` — 817 files; 411 carry a duplicate `jp` section, so
> "US-only" numbers below are the true per-field census), and the kit's own authoring
> surface. Every claim carries its ref. Conflicts between the censuses were resolved by
> reading the source directly (§12). Consumers: any dialogue/window authoring work, the
> author-presentation-layer roadmap (§11), fork fidelity.

## 0. The model in one paragraph

A field script displays text ONLY by opening numbered dialog windows (ids 0-7) over a
`.mes` text entry; there is no print opcode, no number opcode, no title-card opcode.
One opcode family (4 open verbs + close/wait/raise) × one 8-bit style flags byte × the
tag language *inside* the text entry = every message presentation in the game: NPC talk,
cutscene lines, system announces, ATE banners, HUDs, tutorials, letters, menus, numeric
input. The window is a `Dialog` object (`Global\Dialog\Dialog.cs`) managed by a pool
(`DialogManager.cs`); `ETb.NewMesWin` (`ETb.cs:91-165`) is the single entry point.
Re-issuing a window id REPLACES that window (`ETb.cs:96` DisposWindowByID); different ids
coexist (pool is unbounded — `DialogManager.cs:184-203`).

## 1. The opcodes

| Op | Hex | HW name | Args (read order) | Blocks? | US uses |
|---|---|---|---|---|---|
| MES | 0x1F | WindowSync | `win, flags, textId` | yes | 12,665 |
| MESN | 0x20 | WindowAsync | `win, flags, textId` | no | 11,324 |
| MESA | 0x95 | WindowSyncEx | `talkerUid, win, flags, textId` | yes | 4,368 |
| MESAN | 0x96 | WindowAsyncEx | `talkerUid, win, flags, textId` | no | 319 |
| CLOSE | 0x21 | CloseWindow | `win` | no | 2,697 |
| CLOSEALL | 0xEB | CloseAllWindows | — | no | 0 in stock |
| WAITMES | 0x54 | WaitWindow | `win` | yes | 7,233 |
| NOINITMES | 0x53 | PreventWindowInit | — | no | rare |
| MESVALUE | 0x66 | SetTextVariable | `slot 0-7, value` | no | 10,127 |
| CHOOSEPARAM | 0x7C | EnableDialogChoices | `availMask, defaultAbsRow` | no | 412 |
| SETSIGNAL | 0xE3 | SetDialogProgression | `value` → `ETb.gMesSignal` | no | 374 |
| RAISE | 0x8E | RaiseWindows | — (+22 depth to all) | no | 4,260 |
| MESB | 0xD0 | BattleDialog | `battleTextId` | no | — |

Impls: `EventEngine.DoEventCode.cs:410-580` (window family), `:1963-1969` (0x7C),
`:2978-2981` (0xE3), `:2662-2669` (0xD0). WindowSync+WindowAsync are the 6th/8th most
common opcodes in the entire game's field code.

- **Blocking** = `gCur.wait = 254`, resolved when the window id is no longer active
  (`EBin.cs:136-155`). **Window id 255 is the "no window" sentinel** — never emit it.
- `MES`/`MESN` attach the **executing entity** as speaker (`DoEventCode.cs:457,503`);
  `MESA`/`MESAN` name the speaker explicitly (first arg). This is the ONLY speaker
  mechanism — there is no per-actor tail tag.
- `CloseWindow` can block after all: if the window has a voice-acting clip and no
  choices, the script stalls until the clip ends (`DoEventCode.cs:527-558`).
- ⚠ **`CloseWindow` on a `[PAGE]`-split entry turns the page instead of closing**
  (`Dialog.cs:616-624` — `Hide()` short-circuits while pages remain).

## 2. The flags byte (decoded from `ETb.cs:481-489` + `FlagsToStyles` `ETb.cs:167-186`)

| Bit | Value | Name | Effect |
|---|---|---|---|
| 0 | 1 | ResetChooseMask | KEEP the running `sChoose` as this window's default (clear = reset to the 0x7C-supplied default). Stock never uses it |
| 1 | 2 | — | unused, no reader |
| 2 | 4 | ChatStyleWithoutTail | chat-frame sprite, no tail, screen-fixed |
| 3 | 8 | winMOG | Mognet caption (only when bit7 CLEAR) |
| 4 | 16 | TransparentStyle | frameless text (wins over 4) |
| 5 | 32 | NotFollowActor | place at actor once, don't track — **and kills the neck-turn**: `SetFollow` requires `(flags & 160) == 128` (`EventEngine.cs:1281-1294`) |
| 6 | 64 | winATE | ATE caption (only when bit7 CLEAR) |
| 7 | 128 | ChatStyle | THE actor-attach bit: window style Auto + tail + follow + `sLastTalker` neck-turn. Without it `targetPo` is nulled (`ETb.cs:98-99`) |

**Three laws:**
1. **Captions need bit7 CLEAR** — `128|64` renders a chat bubble and silently DROPS the
   ATE caption (`ETb.cs:170-181`). Caption windows are always Plain-style.
2. **16 &gt; 4 &gt; (Auto|Plain)** in style resolution; `128|16` = frameless text pinned to the
   actor (stock: the Hot&amp;Cold floating dig number, flag 144).
3. On the **world map** (`gMode==3`) the actor is force-detached — no bubbles-with-tails
   there, ever (`ETb.cs:106-107`).

Stock's actual flag distribution (US-only, all 4 open verbs):
`128` 60.2% (dialogue) · `0` 25.4% (system/plain) · `8` 4.4% (moogle) · `64` 3.5% (ATE)
· `4` 3.4% (HUD/tutorial pages) · `16` 2.8% (transparent) · `160` ×16 · `132` ×5 · `144` ×3.
The three rare combos are deliberate, not noise: **160** = chat without camera-pan (the
play's sword QTE `test2_15.txt:1833-1854`, Brahne's Odin ritual `test2_312.txt:252-259`);
**132** = attached but tail-less (off-screen voices: "&lt;Tinkle.&gt;" `test2_445.txt:1917`,
"Zzz..." `test2_95.txt:3143`); **144** = transparent-on-actor (H&amp;C dig number
`test2_221.txt:4508`).

## 3. Stock conventions — window ids, sync-vs-async, closing

**The de-facto window-id slot map** (US census cross-tab):
- **0-4** = dialogue slots (flag 128 dominant); id 0 also owns the ATE title card (849 of
  1,001 winATE uses) and is the cutscene default.
- **5** = moogle/minigame announce slot (flag 8/4).
- **6** = HUD + debug slot (the `Error Env Play` Main_Init boilerplate lives here in
  ~every field — 4,068 calls; treat it as noise, not design).
- **7** = **the system-announce slot**: `"  Received Item!  "` / `"  Received 0 Gil!  "`
  at flags 0 (3,680 sites). The kit's chest box (win 7, flags 0) matches stock exactly.

**The most common stock idiom is not WindowSync — it is manual sync:**
```
WindowAsync(id, flags, mes) ; RaiseWindows() ; WaitWindow(id)
```
7,285 of 7,590 `RaiseWindows` sit immediately after a `WindowAsync`. Async fate census:
56% `WaitWindow`, 17% explicit `CloseWindow`, 22% replaced in-place by the next
`WindowAsync` on the same id (the HUD-refresh idiom), 4% left open. Per flag: winATE
titles are 99.9% async+`WaitWindow` (so a fade/Wait can run underneath); moogle menus
(flag 8) are NEVER waited — hand-polled then `CloseWindow` so Cancel can be distinguished;
HUDs (flag 4) are 88% replace-in-place.

**A script explicitly closes a window in exactly three situations:** a timed toast
(`WindowAsync + Wait(N) + CloseWindow` — `test2_133.txt:1147-1151`), staged captions
("On your mark!/Get set!/GO!" — `test2_510.txt:919-932`), and multi-window UI teardown
(`test2_249.txt:1885-1892`). Everything else lets the player's confirm or the next
same-id window dispose it.

## 4. THE DECISION TABLE — situation → stock form

| Situation | The stock form | Canonical site |
|---|---|---|
| NPC talk (player-initiated) | `WindowSync(1, 128, txid)` from the NPC's SpeakBTN, after DisableMove/TurnToward | `test2_133.txt:2863-2890` |
| Cutscene line, rotating speakers | `WindowSyncEx(uid, 0, 128, txid)` — ONE window id, explicit speaker per line | `test2_440.txt:308-370` (20-line 4-speaker scene) |
| Line where the camera must NOT pan | flags **160** | `test2_312.txt:252-259` |
| Off-screen / sleeping voice | flags **132** | `test2_95.txt:3143` |
| System announce (item/gil got) | `SetTextVariable(0, v)` + `WindowSync(7, 0, txid)` with `[ITEM=0]`/`[NUMB=0]` | `test2_41.txt:577-586` |
| Readable sign / plaque | `WindowSync(0, 0, txid)`, text opens `= … =` | `test2_1.txt:1880` |
| ATE title card | fade + `WindowAsync(0, 64, txid)` + `RaiseWindows` + `Wait(20)` + `WaitWindow(0)` → `Field(N)` | `test2_510.txt:248-275` |
| Menu with a caption skin | picker `WindowSync(1, 64, …)` (ATE) / `WindowAsync(2, 8, …)` (moogle) | `test2_100.txt:315-317`, `test2_110.txt:451-474` |
| Live HUD counter | dedicated looping code entry: `SetTextVariable` + re-issue `WindowAsync(6, 4, txid)` on change, `Wait(1)` | `test2_133.txt:1166-1177` |
| Auto-expiring toast | `WindowAsync(7, 4, txid)` + `Wait(240)` + `CloseWindow(7)` | `test2_133.txt:1147-1151` |
| Countdown captions | async + Wait + Close, staged, same id | `test2_510.txt:919-932` |
| QTE button prompt | `WindowAsync(1, 160, txid)` replace-in-place, never closed | `test2_15.txt:1831-1856` |
| Letter / narration overlay | `WindowAsync(3, 16, txid)` (transparent) | `test2_343.txt:1714`, ending narration `test2_788.txt:197` |
| Persistent hint under rolling dialogue | `WindowAsync(1, 16, hint)` held across N `WindowSync` pages, then `CloseWindow(1)` | `test2_178.txt:1297-1307` |
| Choice menu | rows in the TEXT (`[CHOO]`), optional `EnableDialogChoices(mask, default)`, read sysvar 9 after | §7; `test2_110.txt:451-474` |
| Numeric input | 5 simultaneous windows: persistent panel + digit readout + transparent per-digit cursors | `test2_249.txt:1782-1892` (Treno auction) |
| Two speakers at once | two `WindowAsync` + the `gMesSignal` handshake (§8) | `test2_41.txt:731-743` |
| "You don't know where you are" | `SetFieldName(255/94)` / `ResetFieldName()` — 3 fields only; there is NO on-field title popup (menu/save-slot label only, `MainMenuUI.cs:520-524`) | `test2_726.txt:110-112` |

## 5. Window geometry — the ground truth

- **Width is (almost) always auto-measured.** `AutomaticSize` (`Dialog.cs:1560-1592`)
  measures every page; `[STRT=w,l]`'s width is IGNORED whenever `CanAutoResize()` is true
  — which is always for script windows except: Fossil Roo lever fields 1400-1425,
  the Auction transparent windows, ChocoHot plain windows (`Dialog.cs:1594-1624`).
  `[STRT]`'s line count acts as a MINIMUM only. The `force` 3rd param and `UseSizeHint`
  are dead (`Dialog.cs:362,1623`).
- **★ `[WDTH]` IS DUMMIED.** `ApplyFormatTag` consumes it and does nothing —
  `DialogBoxSymbols.cs:650-653`, "Unused anymore… variable width is now automatically
  handled"; the `OnWidths` body `:905-935` is dead. Every `[WDTH=…]` the kit emits is
  inert decoration (harmless; width reservation must come from sentinel text — which is
  what the HUD max-width-sentinel law already does). Choice-window shrink on masked rows
  comes from `ParseChoiceTags` physically DELETING the rows + re-measure, not from WDTH.
- **`[MPOS=x,y]`** = absolute top-left, y measured down, ×`ResourceYMultipier` on BOTH
  axes; **setting it NULLS the actor attach** (`Dialog.cs:896-897`) → no tail. A third
  param `[MPOS=x,y,winId]` anchors this window to ANOTHER window's top-left corner,
  re-evaluated per frame (`Dialog.cs:1502-1511`) — stock never uses it.
- **`[TAIL=…]` full set** (`FFIXTextTag.cs:222-239`): `UPR UPL LOR LOL UPC LOC` +
  force-variants `UPRF UPLF LORF LOLF` (never auto-flip at screen edges, skip overlap
  avoidance — `Dialog.cs:936-955,1143-1148`) + `DEFT` (bottom-center dialogue default).
  With an actor attached the code picks the side automatically from the LISTENER's
  relative position when no tag is present (`Dialog.cs:914-929`), auto-flips at screen
  edges, and avoids overlapping another window (`DialogManager.cs:161-174`). WITHOUT an
  actor (Plain style), the same codes mean screen-CORNER anchors; captioned windows
  force Center (`Dialog.cs:965-1026`).
- `[OFFT=x,y,z]` = world-space offset of the tail anchor (writes `actor.mesofs*`,
  `DialogBoxSymbols.cs:646-649`) — per-window, stock-rare, useful for tall models.
- Depth: `68 - 2*id` (`Dialog.cs:886-895`) — id 0 is frontmost; `RaiseWindows` +22 all.
- Sizes: width min 29px(PSX), line height 68 UI-px + 20 padding; UI scale ≈4.82 in 4:3
  (`Dialog.cs:364-391`, `UIManager.cs:653-666`).

## 6. The tag language (what a `.mes` entry can say)

Seven parse layers (`TextParser.cs:63-101`); the load-bearing subset:

**Stream:** `[ENDN]` end · `[PAGE]` page-break (each page = its own parser; VA gets
`_P&lt;n&gt;` suffixes) · `[TBLE]` = the WHOLE entry becomes a `\n`-split string TABLE (read
back via `[TEXT=bank,slot]` where bank=that entry's txid, slot=gMesValue index —
`ETb.cs:270-283`; this is how world location names + the mognet roster work).

**Window-level** (consumed before render, `DialogBoxSymbols.cs:576-658`): `[IMME]`
instant-pop · `[FLIM]` force-typewriter · `[NFOC]` = FlagButtonInh (player can't dismiss)
**and** FlagResetChoice=false (§7 hazard) · `[NANI]` skip grow animation · `[TAIL]` ·
`[STRT]` · `[MPOS]` · `[OFFT]` · `[ANIM=target,interp…]` animated-tag keyframes (stock:
the blinking Mognet icon, injected engine-side `TextOpCodeModifier.cs:30-35`).

**Substitution:** `[ZDNE]`-class name tags + `[PTY1-4]` · `[TEXT=bank,slot]` ·
`[NUMB=slot]` live number (re-rendered EVERY frame the gMesValue changes —
`Dialog.cs:1415-1427` — this is the whole HUD mechanism) · **`[NUMB=slot,selSlot]`** =
the single-window digit-highlight spinner, full recipe in a source comment
(`Dialog.cs:1429-1474`), stock-unused · `[ITEM=slot]` item name auto-colored.

**Flow/timing:** `[WAIT=n]` typewriter pause · `[SPED=n]` speed (`FFIXTextModifier.cs:56-60`)
· `[TIME=n]` auto-close after n frames + undismissable; `[TIME=-1]` = undismissable,
script-closed only (`DialogBoxSymbols.cs:811-829`) · `[NTUR]` disable turbo-skip ·
`[SIGL=n]`/`[INCS]` = write/increment `ETb.gMesSignal` WHEN THE TEXT APPEARS
(`:834-866`) — the script reads it as sysvar 8 (§8) · `[PSND=id]` play SFX at a text
position (`:868-876`).

**Style:** `[RRGGBB]`/`[RRGGBBAA]`/`[AA]` color push, `[-]` pop (stock palette: C8C8C8
white · B880E0 pink · 68C0D8 cyan · D06050 brown · C8B040 yellow · 78C840 green · 909090
grey) · `[HSHD]`/`[NSHD]` shadow toggle (+`[HSHD=Outline]` etc.) · `[BCOL=…]` background
quad behind text (up to 12 params, rect-mapped) · `[FONT=+n/-n/*n//n/RESET]` font scale ·
`[b] [i] [u] [s] [c] [sup] [sub] [MIRR] [JSTF]` · layout `[MOVE=dx,dy] [XTAB=x] [FEED=n]
[YADD/YSUB=n] [SPAY=n] [FRAM=dx,dy] [CENT]`.

**Images:** `[ICON=n]` · `[SPRT=atlas,name,w,h,alpha]` ARBITRARY atlas sprites inline ·
`[DBTN/CBTN/KCBT/JCBT=NAME]` button glyphs (CBTN honours rebinding) · `[MOBI=n]`
mobile-only · `[PNEW(=bit)]` icon shown iff `gMesValue[0]&amp;(1&lt;&lt;bit)`.

**.mes structure:** entries delimited by `[STRT=`; `[TXID=n]` re-anchors explicit ids
(`FF9TextTool.ExtractSentense:311-330`); `[LOADMES=file]` #includes another `.mes`
(`FF9TextTool.cs:63-94`). Load is a per-txid CUMULATIVE MERGE, base game LAST-applied-
first → [[project-ff9-text-block-shadow]].

## 7. Choices

No choice opcode — rows live in the text after `[CHOO]` (first row line); the block runs
to end-of-text unless `{ResetTags}` terminates it (the ONLY early terminator,
`DialogBoxSymbols.cs:194`). `[PCHC=count,cancelRow]` declares count+cancel;
`[PCHM=count,cancelRow]` additionally honours the 0x7C mask (`SetupChoose` `:660-707`).
Masked rows are PHYSICALLY DELETED from the text (`:202-237`); `EnableDialogChoices`'s
2nd arg is an ABSOLUTE row index converted to visible-row index (`ETb.cs:248-260`).
Result = **sysvar 9** (`GetChoose`), absolute row counting hidden rows; cancel writes the
cancel row's index. Stock: 2-3 rows dominate; most menus never call 0x7C at all (753 of
2,696 near-window reads have one); the ATE picker ORs `32768` into the mask to keep its
Cancel row alive; the moogle menu distinguishes chose-Cancel from pressed-Cancel via
`IsButton` (`test2_110.txt:459`).

⚠ **THE CHOICE-RESET HAZARD:** `InitializeChoice` runs on EVERY window and zeroes
`SelectChoice` unless the window carries `[NFOC]` (`Dialog.cs:92-104`). Any interstitial
window between the choice and its sysvar-9 read destroys the result. (The kit's stepper
already learned this; it generalizes to ALL choice flows.)

## 8. Signals — text-synchronized choreography (mechanism corrected)

`SetDialogProgression(n)` (0xE3) writes `ETb.gMesSignal`; sysvar 8 reads it
(`DoEventCode.cs:2980`, `GetSysvar.cs:36`). `[SIGL=n]`/`[INCS]` set/increment the SAME
variable at the moment the tag's text position APPEARS (typewriter-aware, one-per-tick
queued — `DialogBoxSymbols.cs:836-866`). So the Zorn&amp;Thorn unison
(`test2_41.txt:731-743`: zero it → open both windows → `while (GetDialogProgression &lt; 2)`)
is driven by `[INCS]`-class tags inside the `.mes` entries — invisible in the HW exports,
which is why grep-level reads mislabel it. **The general capability: a script can block
until the text reaches a marked syllable** — mid-line camera cuts, SFX stings, actor
reactions timed to words. Stock uses it only for window-open sync; the substrate is far
more general.

## 9. The other channels (not the field dialog window)

- **Battle:** `MESB` 0xD0 → `UIManager.Battle.SetBattleMessage(text, priority=4)` from
  the battle zone's `.mes`; the engine's own battle titles/messages are priority-queued
  with config-driven display ticks (`BattleHUD.Public.cs:287-326`). Damage popups =
  `HUDMessage` styles, NOT script-reachable (`HUDMessage.cs:113-141,234-246`).
- **World map:** same MES/MESN, actor force-detached; text ids 40/41 are hardcoded to
  the enter-location bubble (`ETb.cs:105-112`); location label = world text entry 0's
  `[TBLE]` table (`WorldHUD.cs:818-846`).
- **Timer:** 0x69/0x7D/0x8D → `TimerUI` digit sprites; remaining time = sysvar 17;
  save-persisted + re-stamped on every map load → THE COUNTDOWN EXIT LAW
  ([[project-ff9-minigame-ui-substrates]]).
- **Menus from script:** `Menu(0)` main · `(1,charSlot)` name-entry (after
  `SetName(slot, txid)`) · `(2,shopId)` shop · `(4,0)` save · `(5,0)` chocograph
  (`EventService.cs:6-26`; 3/6/7/8 dead).
- **Field name:** `SetFieldName(txid)`/`ResetFieldName` (0xB0/0xB1) → `mapNameStr`,
  consumed by the pause menu/save slot ONLY — no popup exists (`DoEventCode.cs:2399-2408`).
- **Icons:** `Bubble(1)` "!" (0x68) · `ShowHereIcon` (0xEF) · `ATE(mode)` (0xD7 →
  [[project-ff9-ate-system]]).
- **Voice acting:** `VoicePlayer.PlayFieldZoneDialogAudio(FieldZoneId, mesId, dialog)`
  fires on EVERY window open (`ETb.cs:150`) and page turn. Path probe order:
  `Voices/{lang}/{zone}/va_{mes}` → `…_ID{uid}` → `…_{SpeakerName}` → base, `_P{n}` per
  page, per-choice `_{row}` on cursor move; `.akb` then `.ogg`
  (`VoicePlayer.cs:125-236`). **zone = OUR text_block for a custom field** → custom
  fields can ship voice acting as loose Ogg files with zero engine work (§11).
- **Per-field engine hardcodes** (fork-fidelity relevant): special-HUD keyed on
  (FieldZoneId, lang, mesId) (`EventHUD.CheckSpecialHUDFromMesId`); autoresize
  exemptions (Fossil Roo/Auction/ChocoHot, `Dialog.cs:1594-1624`); Iifa 1657 per-mesId
  camera exemption (`ETb.cs:123-141`); mes-skip list (`ETb.IsSkipped:285-315`). A fork
  on a real zone id INHERITS these; a custom id gets none.

## 10. The kit's authoring surface today (condensed; full inventory in the 2026-08-03 census)

Every author-facing lane and the exact window it emits — all ids/flags HARD-CODED except
4 blocks (`[[behavior.hud]]`, behavior `announce`, `[[numeric_input]]`, `[[qte]]`):

| Lane | Emits | Matches stock? |
|---|---|---|
| `[[npc]] dialogue` / `[[event]] message` / `[[on_entry]]` / shop greeting | `WindowSync(1, 128, txid)` | ✓ (stock also favors id 0; fine) |
| `[[cutscene]]` say (cast) | `WindowSyncEx(uid, 0, 128, txid)` | ✓ the real cutscene form |
| chest / event received box | `SetTextVariable(0,·)` + `WindowSync(7, 0, txid)` | ✓ byte-faithful incl. `[STRT]`+`DEFT` |
| ATE title (`[[gateway]] ate_title`) | `WindowAsync(0, 64, txid)`, `[IMME][CENT=W]`, no tail | ✓ |
| choices (`[[choice]]`, savepoint, mognet) | `WindowSync/Async` + `[CHOO]`/`[PCHC]`/`[PCHM]` + 0x7C, dispatch via sysvar-9 switch | ✓ incl. dynamic flag-gated masks |
| `[[behavior.hud]]` | `SetTextVariable` × N + one-shot `WindowAsync(6, 16, txid)` + `[NFOC]` | stock uses flag 4 + re-issue; ours is the better `[NUMB]` re-render form |
| `[[numeric_input]]` | the 5-window Treno keypad, byte-grounded | ✓ (9 stock fields carry it verbatim) |
| mognet letter/status | `WindowAsync(3, 16, ·)` letter, `(5, 8, ·)` status | ✓ |
| `[[qte]]` | `WindowAsync(1, 160, ·)` prompts | ✓ (the play's exact flag) |
| `[[item_text]]` | TextPatch.txt `&gt;DATABASE` (relaunch) | Memoria channel |

Text authoring: one `.mes` writer (`content/text.py` — `mes_entry`/`build_mes`/wrap at
28 units); speaker form `Name\n“line”`; `[PAGE]` supported; `tail` author-settable on 11
blocks, `[STRT]` only via chest/event `box`, `[MPOS]` only via savepoint `menu_pos` +
numinput `pos`. txids allocate from 500 (synth) / donor-max+1000 (verbatim carry).
`text_block` = the field's own id + auto-`MessageFile` registration
([[project-ff9-text-block-shadow]]). All 7 languages get identical authored text;
`[[logic_edit]] kind="text"` (donor lines) is the only per-language surface.

## 11. GAPS — engine capabilities the authoring layer doesn't reach (ranked)

The full 25-item list with seams lives in the census; the ones that matter, grouped:

**Tier 1 — trivial plumbing, immediate expressive win — ★★ BUILT + IN-GAME PROVEN (commit
d9f224c4; all 6 WINSTYLE bench checks owner-confirmed @30601). The dresser is
`text.dress_window` + `text.default_tail` (THE WINDOW-GEOMETRY LAW: detached-style windows ship
tail-less); a tread `once=false` event re-fires while standing (level-triggered) — a repeatable
readable wants the unbuilt `[[event]] trigger="action"` follow-up:**
1. **`style`/`flags` + `window` keys on every dialogue-bearing block** (today: flags
   settable NOWHERE, window on only 4 blocks). Unlocks: frameless narration lines,
   no-pan lines (160), off-screen voices (132), tail-less-attached (4), Mognet-caption
   reuse. Seam: `collect_text._add` (`build.py:7232`) + the emitters already take kwargs.
2. **`actor = "&lt;npc&gt;"` on `[[npc]]`/`[[event]]`/`[[choice]]` lines** → `WindowSyncEx`
   (stock's own cutscene form; uid resolution exists in `conductor._uid_for`). Also add
   the missing `window_async_ex` wrapper (0x96 has ZERO kit emitters).
3. **`instant`/`speed`/`duration` keys** → `[IMME]`/`[SPED]`/`[TIME=n]` (auto-expiring
   toasts without the Wait+Close boilerplate). `[TIME]`/`[IMME]` are already proven in
   kit-internal strings.
4. **`box = [w, lines]` and `pos = [x,y]` promoted to all blocks** (today chest/event
   and savepoint/numinput only). Note `[STRT]` width is autosize-ignored; `box` really
   means line-minimum + the no-autoresize paths; `pos` = `[MPOS]` (detaches actor — lint
   when combined with a tail).
5. **Tag vocabulary documentation + lint** — colors/icons/buttons pass through today
   with zero validation and a wrong width model (`_tag_render_width` treats most layout
   tags as 0). A color/icon name table + validator in `content/text.py`, mirroring
   `TAIL_CODES`.

**Tier 2 — new capability, moderate work:**
6. **Voice-acted custom fields.** The engine already probes
   `Voices/{lang}/{text_block}/va_{txid}.ogg` on every window. A `[[npc]] voice = "file.ogg"`
   key + a deploy copy step = full VA with zero DLL. (Choice-row and per-page variants
   free.) Nothing in the kit touches this today.
7. **Text-synchronized choreography** — `[SIGL]`/`[INCS]` + sysvar-8 polling as a
   cutscene step (`say` with `signal_at = "word"` → split-insert `[INCS]`, next steps
   gated on the signal). Mid-line camera cuts / SFX stings; the engine substrate is
   proven by stock's unison windows. `[PSND=id]` is the zero-logic variant for pure SFX.
8. **Multi-window scene verbs** — cutscene/behavior step kinds `open`/`close`/`wait_window`
   (wrappers for 0x20/0x21/0x54/0x8E exist only as raw `encode` inside mognet/numinput).
   Unlocks the Mogster two-window tutorial form, unison speech, staged countdowns.
9. **`variables = [...]` on any line** — bind gMesValue slots to flags/counters/gil
   before the window (the chest already does exactly this); gives every line live
   `[NUMB]`/`[ITEM]`/`[TEXT]` access + `[PNEW=bit]` conditional icons.
10. **Per-language authored text** — accept `dialogue = { us = "...", fr = "..." }`;
    `mes_parts` is already per-language, only the broadcast needs splitting.

**Tier 3 — non-stock presentation (engine-present, stock-unused):**
11. **The single-window spinner** `[NUMB=value,sel]` (recipe in `Dialog.cs:1429-1474`) —
    a cleaner numeric_input v2 with no cursor windows.
12. **Window-anchored windows** `[MPOS=x,y,winId]` — HUD clusters that move as one.
13. **Animated tags** `[ANIM=…]` (keyframed icon/color/offset animation), **background
    quads** `[BCOL]`, **font scaling** `[FONT]`, arbitrary **atlas sprites** `[SPRT]`,
    force-tails, `[OFFT]` tail-anchor offsets for tall models, `[NTUR]` for
    turbo-immune tutorial text.
14. **`[TBLE]` state-text windows** — one entry holding N variants indexed by a
    gMesValue slot (the unbuilt alternative already noted in the minigame survey).

**Known kit defects surfaced by the census** (fix regardless): `[[prop]] dialogue`
silently ignored on synthesized fields (works verbatim-only); `tail` validated on only
4 of 11 blocks; `[[logic_edit]]` can't touch kit-authored (`[TXID=]`) lines; no
txid-ceiling lint; `_tag_render_width` under-models layout tags.

## 11b. THE READING BRACKETS — the FadeFilter census (2026-08-03, all 817 scripts, us-section)

FadeFilter (0xEC) engine truth (`DoEventCode.cs:632-648`, `SceneDirector.cs:640-663`): the MODE arg
contributes ONLY bit 1 — `&2` = the SUBTRACTIVE shader channel, else ADDITIVE (two independent
globals, `_FadeColor_ABR2`/`_ABR1`; a full clear needs BOTH a mode-7 sub-clear and a mode-5
add-clear); the INTENSITY arg is read and DISCARDED (stock's `VAR_GlobUInt8_17` dance is inert);
fades LERP from the channel's current colour (chaining cross-fades). **THE RAISE LAW:** the fader
is a UI-layer panel above dialog depth 54-68; `RaiseWindows` (+22, `DialogManager.RiseAll`) is what
lifts text above it — every bright-text bracket carries it; three stock shapes omit it ON PURPOSE
so text emerges with the scene.

241 fade-around-window bracket sites, ZERO overlapping the 830 warp / 849 ATE-title / 256 card-game
transition fades — disjoint idioms. The shapes (kit `dim =` names starred):

| type | in-fade | RW | out | sites |
|---|---|---|---|---|
| ★ letter | `2,24,·,R,R,B` (9 per-field tints, R=G, B=R+20..50) | yes | `7,16` | 100 / 50 fields |
| ★ voice (window FIRST, dim under it) | `2,15,·,64-128 grey` | yes | `7,15` | ~40 (Memoria, Oeilvert, Kuja, Soulcage `48`, Garland `32`, eavesdrop `100`) |
| ★ inscription | `2,8,·,96 grey` | yes | **`2,8,·,0,0,0`** cross-fade | 4 (Berkmea 804 +) |
| ★ blackout (Eiko's Ipsen story, 1609) | `6,8,·,white` | **NO** | `7,16` before the read-wait | 7 |
| per-line blackout alternation | `6,24` ↔ `7,16` per line | in-half | — | ~26 (Pand. 2705, Bran Bal) |
| exposition (ends in blackout) | `2,32/64,·,128 grey` | yes | `6,64,white` | 4 (Memoria) |
| ending monologues | `7,1` → window → `6,30,white` | NO | — | 11 (3000-3003) |

Non-bracket fade families (excluded): inn/tent sleep sepia (`3,32,·,128,96,0` ×65), standing
Main_Init scene filters (Evil Forest/Memory `40,40,32`, Tot's flashback `130,160,170` — the one
Memoria-patched tuple), white flashes (`0/4` add + `1/5` clears, the Chocobo dream snap-to-white).
Letter text = the From-header; voice/blackout = unattributed; stock never Name-attributes a dimmed
window (the speaker form is the CHAT convention).

## 12. Corrections to prior knowledge (this survey supersedes)

1. **`[WDTH]` is dummied** (`DialogBoxSymbols.cs:650-653`) — the 2026-07-18 savepoint
   decode described the dead `OnWidths` body as live. Observed shrink/width behavior is
   ParseChoiceTags row-deletion + AutomaticSize. Kit `[WDTH]` emissions are inert.
2. **`GetDialogProgression` reads `gMesSignal`, not `gMesCount`** — the export-census
   reading ("windows opened so far") was wrong; the unison idiom works via in-text
   `[INCS]`/`[SIGL]` tags the exports don't show (§8). `gMesCount` exists but is
   engine-internal (EIcon importance).
3. `[STRT]` width is ignored under autosize (nearly always) — "deliberate non-parity"
   in the savepoint memory is in fact full parity: stock's own values are ignored too.
4. Flag 16 vs 4 for HUDs: stock's hunt HUD is flag **4** (chat-frame no-tail); the
   kit's flag-16 frameless HUD is a deliberate improvement, not stock parity.
