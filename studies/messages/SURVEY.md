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

## 6b. ★★ THE IN-TEXT CENSUS — what stock actually writes inside its entries (2026-08-03)

**The gap this closes.** Everything above §6 was censused from the *script* side (the 817 HW exports):
opcodes, flags, window ids, fade brackets. §6 itself was never a census at all — it is a **capability
list read off the engine parser**, so it says which tags exist and nothing about which stock uses. This
reads the real `.mes` for every field text block in the install (`dialogue.extract_field_mes`) and
counts. **64 blocks, 40,896 entries.**

**★ First surprise, and it is structural: there are only 64 field text blocks for 831 mapped fields.**
Text is per-ZONE, not per-field — block 694 serves 35 fields, 289 serves 28, 276 serves 27, and exactly
ONE block in the game is used by a single field. `FF9TextTool.FieldZoneId` is that zone id. Consequences:
the text-block shadow law (§10, [[project-ff9-text-block-shadow]]) is far broader than "a field" — writing
a real block collides with a whole *town*; and a voice file keyed `Voices/{lang}/{zone}/va_{n}` covers a
zone's entire dialogue, which is why Echo-S-style packs are organized the way they are.

| tag | uses | blocks | tag | uses | blocks |
|---|---|---|---|---|---|
| `STRT` | 40,896 | 64 | `WAIT` | 1,068 | 64 |
| `ENDN` | 38,006 | 64 | **`OFFT`** | **1,023** | **64** |
| **colour** | **20,438** | **64** | `NFOC` | 981 | 64 |
| **`HSHD`** | **20,438** | **64** | `MPOS` | 714 | 57 |
| `SPED` | 15,277 | 64 | `ICON` | 663 | 57 |
| `TAIL` | 12,702 | 64 | `NUMB` | 493 | 64 |
| `MOVE` | 8,135 | 64 | `NANI` | 473 | 55 |
| `WDTH` *(dummied)* | 5,877 | 64 | `XTAB` | 470 | 64 |
| `IMME` | 5,352 | 64 | `PCHM` | 438 | 57 |
| `TEXT` | 4,893 | 57 | `DBTN` | 304 | 64 |
| `CENT` | 3,822 | 64 | `ITEM` | 294 | 64 |
| `TIME` | 2,918 | 64 | `TBLE` | 171 | 57 |
| `FEED` | 2,637 | 64 | **`INCS`** | **121** | **9** |
| `CHOO` | 1,927 | 64 | **`SIGL`** | **63** | **10** |
| `PCHC` | 1,489 | 64 | `PAGE` | 20 | 2 |

Name tags: `ZDNE` 5,928 · `DGGR` 5,126 · `STNR` 2,659 · `VIVI` 1,321 · `FRYA` 1,143 · `QUIN` 4.

### ★ Colour is the third most-used tag in the game, and it is SEMANTIC

20,438 pushes, in every single block — not the decorative afterthought §6 implies. Six codes only:

| code | uses | what it marks |
|---|---|---|
| `C8C8C8` white | 9,953 | **the RESTORE** — the explicit pop back to body text |
| `68C0D8` cyan | 9,603 | **substituted names** — almost always wrapping a `[TEXT=0,n]` |
| `C8B040` yellow | 404 | **quantities and items** — `[NUMB=0] Gil`, `[ITEM=0]`, "Card" |
| `B880E0` pink | 246 | mostly dev/`Debug` strings |
| `D06050` brown | 210 | rare |
| `78C840` green | 22 | 2 blocks |

**THE COLOUR LAW: stock colours what it did not author.** Cyan and yellow mark the *runtime-substituted*
parts of a line — a name the player chose, a number, an item — so colour is how FF9 tells the reader
"this word came from your save, not the script." It is not emphasis and never decoration.

Two hard sub-laws, both exact:
1. **Every colour push is paired with `[HSHD]`.** The counts are identical to the unit: 20,438 = 20,438.
   Memoria's importer encodes exactly this pair as its named colour tokens (`FieldTags.cs:40-45`,
   `"[68C0D8][HSHD]" -> "{Cyan}"`). A bare colour with no shadow toggle is not a shape stock ships.
2. **Stock NEVER pops with `[-]`** — zero occurrences across all 64 blocks. It re-pushes `C8C8C8`
   explicitly to close every span. `[-]` parses, but emitting it is off-idiom.

`909090` grey, listed in §6's palette, appears **zero** times in field text.

### ★ Button glyphs: stock has exactly two idioms, and neither is mid-sentence

`[DBTN=NAME]` (default binding) / `[CBTN=NAME]` (follows the player's rebinding) draw the button
sprite inline. Eleven names ship, with counts: `SELECT` 72 · `START` 64 · `PAD` 52 · `SQUARE` 23 ·
`CROSS` 22 · `UP`/`LEFT`/`RIGHT`/`CIRCLE`/`DOWN` 15 each · `TRIANGLE` 14.

**The character immediately following a glyph is never a space.** Across all 64 blocks it is:

| after the glyph | sites | the idiom |
|---|---|---|
| `:` | 128 | a **legend row** — `[DBTN=START]: Overwrite`, `[DBTN=SELECT]: Skip` |
| `[` | 192 | another **tag** — the glyph ENDS the phrase (`Press [DBTN=SELECT][MOBI=…]`) |
| a space | **0** | — |

So stock's prose never flows *through* a glyph. A glyph either leads a legend row (colon, no space)
or terminates a phrase.

### ★★★ THE SPACE-AFTER-GLYPH LAW — and *why* stock has no space there

Found in-game (bench 30603 rounds 2-3, owner: *"the colon follows nicely, the two spaces on either
side still makes it appear uneven… more space on the left than the right"*). That asymmetry is real,
and the first explanation — sprite overhang — was **wrong**. The engine drops the spaces on purpose,
in **both** passes:

```csharp
// measure  NGUIText.cs:885
if (!isSpace || !afterImage) { currentX += advanceX; … }
// print    NGUIText.cs:1081
if (!afterImage || ch != ' ')  { …draw the glyph… }
```

`afterImage` is set where the image advances `currentX` (`:820`) and is cleared **only by a non-space
character** — a space skips the whole block without clearing the flag. So:

1. **Every consecutive space after a glyph is swallowed, not merely the first.** Padding to the right
   is impossible at any width, which is exactly the left-heavy result the playtest saw (the left side
   is untouched; the right side vanishes entirely).
2. `IsSpace` (`:660-663`) is `' '`, U+2009 thin, U+200A hair, U+200B zero-width — none of them work.
3. **This is WHY the census found zero spaces after a glyph.** Stock's `:` idiom works precisely
   because a colon is a non-space character that clears the flag. The game didn't avoid the shape by
   taste; the shape does not render.

**U+00A0 (no-break space) is NOT in `IsSpace`, and round 4 confirmed it in-game** — it survives the
drop and renders as a real gap (owner: *"NBSP reads as a gap… technically it works"*). So the engine
does leave one escape hatch for a glyph mid-sentence.

⚠ **But it stays an escape hatch, not the recommendation.** Stock writes a glyph mid-sentence **zero**
times across 40,896 entries, so the construction has no shipping precedent at any spacing — and by
this survey's own Tier-3 rule, adopting a stock-unused shape is *invention, not fidelity*. The owner's
read of the result was "not sure how it fits visually," which is what an off-idiom shape looks like.
**Use the legend form.** If you genuinely need the glyph inline, U+00A0 works; tune the count (the
bench used two, which reads wide — one is nearer a normal word space).

Enforced: `text.space_after_glyph_problems` lints a space following any inline-image tag
(`DBTN`/`CBTN`/`KCBT`/`JCBT`/`ICON`/`SPRT`) rather than letting the author's spacing silently no-op.

### ★ 16 documented tags stock never uses in field text

`ANIM` · `NTUR` · `PSND` · `NSHD` · `BCOL` · `FONT` · `SPAY` · `FRAM` · `SPRT` · `KCBT` · `JCBT` ·
`PNEW` · `MIRR` · `JSTF` · `LOADMES` · `TXID`.

This **reframes Tier 3**. Those were listed as "engine-present, stock-unused" capabilities to adopt; the
census says several are Memoria extensions or engine leftovers with no shipping precedent at all, so
adopting one is *invention*, not fidelity — the project's own incremental-verbatim-first rule applies.
⚠ Note especially **`PSND`** (the SFX-at-a-text-position tag §11 item 7 recommends as the zero-logic
sting variant): **zero stock uses**, so it is unproven rather than merely underused.

### Corrections to §6 from this census

1. **`[OFFT]` is NOT "stock-rare"** — 1,023 uses across all 64 blocks. That claim was a guess.
2. **`[WDTH]` ships 5,877 inert tags** in all 64 blocks — stock's own values are ignored too, which
   independently corroborates the §12.1 DUMMIED finding rather than resting on the source read alone.
3. **`[PAGE]` is nearly unused** (20 uses, 2 blocks). The kit supports it; stock effectively does not.
4. Pervasive-but-under-exposed by the kit: `SPED` (15,277, every block), `MOVE` (8,135), `TIME` (2,918,
   every block), `NFOC` (981, every block), `TEXT` (4,893), `ICON` (663), `DBTN` (304).
5. `INCS`/`SIGL` are now *counted*, not inferred: 121 and 63 uses in 9 and 10 blocks — small, deliberate,
   and consistent with §8b's reading of the unison idiom.

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

## 7a. ★★★ THE BROADCAST-CONFIRM LAW — one press dismisses EVERY window (2026-08-03, in-game)

**A confirm press is not routed to a focused or topmost window. It is delivered to all of them.**

```csharp
public void OnKeyConfirm(GameObject go) {                    // DialogManager.cs:335-341
    if (PersistenSingleton<UIManager>.Instance.IsPause) return;
    foreach (Dialog dialog in this.activeDialogList.ToList())
        dialog.OnKeyConfirm(go);                             // ← every active window, no filter
}
```

Each `Dialog.OnKeyConfirm` then closes itself if it has finished typing and **`!ignoreInputFlag`**
(`Dialog.cs:789`) — and `ignoreInputFlag` **is** `FlagButtonInh` (`Dialog.cs:408-412`, the same
backing field). The only writers of it in the whole engine are the `[TIME=n]`/`[TIME=-1]` tag
(`OnTime` :811-829), `[NFOC]`, and `ForceControlByEvent`.

**Consequence: an async window that is not dismiss-inhibited cannot survive ANY other window's
dismissal.** The press that advances a line of dialogue takes every other open window down with it.
So the "persistent hint under rolling dialogue" idiom (§4) is not just async-open + late-close — the
hint MUST carry `[TIME=-1]` or `[NFOC]`, or it dies on the reader's first press.

**Found in-game, not offline** (bench 30603 round 1, owner: *"the hint goes away when advancing the
'Watch the hint above...' tailed message"*). The scene linted clean, built clean, and every offline
gate passed — nothing in a static read of the emitted opcodes can see this, because the defect lives
in how the *engine* fans out an input. It is the §11-Tier-2 companion to the movement arc's
CONTROLLER-DEACTIVATION LAW: both are cases where two independently-correct emissions interact through
engine state the bytes don't mention.

Enforced at the call site: `build._validate_window_scene` refuses an unheld window that is still live
across a blocking `say`/`wait_window`, and refuses `hold` + `wait_window` on the SAME id (a held window
can never be dismissed, so that wait would hang forever). Pinned in `test_multiwindow.py`.

**Corollary for two simultaneous attached windows:** the engine does NOT reposition to avoid an
overlap — `CheckDialogOverlap` (`DialogManager.cs:161-174`) only *reports* one, and the callers use it
to flip a tail, nothing more. Two bubbles at the same screen height simply overlap, and the LOWER
window id (higher depth) draws in front, clipping the other's leading glyphs. Stage simultaneous
speakers with real horizontal separation **and** a depth stagger; do not rely on the engine.

## 7a-bis. ★★★ THE TURBO-CONFIRM LAW — the press nobody made (2026-08-04, playtest 30801)

**The environmental sibling of §7a: same fan-out, but the confirm is SYNTHESIZED BY THE ENGINE, every
frame, with the player's hands off the pad.** §7a costs you one window per real press; this costs you
*every* window, continuously, and no amount of script correctness survives it.

```csharp
// UIKeyTrigger.cs:198 — runs EVERY render frame, unconditionally
HandleDialogControlKeyPressCustomInput();
// UIKeyTrigger.cs:834
if (dialogConfirmKeys.Any(c => IsInputDown(c) || keyCommand == c) || ShouldTurboDialog(dialogConfirmKeys))
    UIManager.Instance.Dialogs.OnKeyConfirm(activeButton);        // ← §7a's fan-out, no key down
// UIKeyTrigger.cs:974-991
private Boolean ShouldTurboDialog(List<Control> confirmKeys) {
    if (!Configuration.Control.TurboDialog || preventTurboKey) return false;
    if (TurboKey || ((IsInput(Control.RightBumper) || ShiftKey) && confirmKeys.Any(IsInput)))
        if (UIManager.Instance.Dialogs.IsDialogNeedControl()) return true;   // "some window has FlagButtonInh == false"
    return false;
}
```

`TurboDialog` defaults to **1** in `Memoria.ini` — it is on for everybody. `TurboKey` is a **latch**
toggled by **F9** (`:393-399`) with **no on-screen indicator**, and it persists across field reloads
and warps for the whole game session. `IsDialogNeedControl()` (`DialogManager.cs:422-427`) is
satisfied by any window whose `FlagButtonInh` is false — i.e. every ordinary kit window.

**Symptom, verbatim (owner, bench 30801):** a window *"opens, and when it's finished with the opening
animation and the text shows, it immediately does the closing animation and exits the entire dialogue
tree"* — with no input. Frame-accurate: `Dialog.OnKeyConfirm` is a no-op until `CompleteAnimation`, so
a continuously-asserted confirm kills the window at exactly the moment the text finishes.

**Why it reads as a script bug and burned four rounds.** A CHOICE window is immune by accident —
`UILabel.cs:804-806` sets `preventTurboKey` while a choice/overlay renders — so the *selector*
survives; the confirm that picks a row clears the latch (`:838`), and every reply page opened after it
is killed on sight. That looks exactly like a defect in the choice→reply transition. It is not. It is
not in the `.eb` at all: the field's whole 4617-byte script contains no `CloseWindow (0x21)`, no
`CloseAllWindows (0xEB)`, no `[TIME]`, and no second window on a live id.

**The lever for THIS arm: `[NTUR]`** (`NGUIText.NoTurboDialog` → `FFIXTextTagCode.TurboOff` →
`DialogBoxSymbols.cs:327-329` → `UIKeyTrigger.preventTurboKey = true`). Upstream Memoria, not one of
our patches, so it is stock-safe. Crucially it does **not** touch `FlagButtonInh` — unlike `[NFOC]`
and `[TIME=n]`, the other two inhibitors, which stop the *player's* confirm too and therefore hang a
blocking `WindowSync` forever on `wait == 254` (`EBin.cs:137-148`). The flag is sticky: nothing clears
`preventTurboKey` until a confirm/cancel is actually delivered (`:838`/`:849`), so one render pass of
the tag covers the window's whole life.

Enforced at the call site: `content/text.dress_window` emits `[NTUR]` automatically on any **readout**
window (text containing `[NUMB=]`/`[TEXT=]`/`[ITEM=]` — a number the player opened a menu to read is
not "story to skip"), an explicit `no_turbo` key overrides either way, and `build.validate` refuses
`no_turbo = false` on a readout. Narrative dialogue is deliberately left skippable, like the base
game's. Pinned in `test_window_attrs.py`.

### 7a-bis-2. ★★★ ARM B — the SECOND arm, the one `[NFOC]` walks into (2026-08-05)

**`ShouldTurboDialog` has TWO arms, and the fix for the first is the trigger for the second.** The
block quoted above is arm A only; here is the whole tail of `UIKeyTrigger.cs:974-991`:

```csharp
// ARM A (:981-982) — the broadcast above
if (UIManager.Instance.Dialogs.IsDialogNeedControl()) return true;   // → OnKeyConfirm fan-out
// ARM B (:984-988) — reached ONLY when arm A did NOT fire, i.e. when EVERY open window is
//                    dismiss-inhibited (FlagButtonInh) and so "needs no control"
if (VoicePlayer.scriptRequestedButtonPress
    && ActiveDialogList.Any(d => d.Style == WindowStyleAuto || d.Style == WindowStyleTransparent))
{ ETb.sKey &= ~Confirm; EventInput.ReceiveInput(Confirm); }
```

Arm B does not close a window. It **SYNTHESIZES a Confirm into the SCRIPT'S OWN input stream** — and
`scriptRequestedButtonPress` is set by **`B_KEYON` itself** (`EBin.cs:1080`), re-armed every
`ProcessEvents` tick (`EventEngine.ProcessEvents.cs:11-14`). So the "obvious" repair for arm A —
inhibit the window with `[NFOC]`, then poll for a real press — is **arm B's exact precondition**: the
poll reads a press nobody made, on frame 1. Same symptom, second mechanism, and it is why
`[NFOC]` + poll is not a fix.

**ARM B's PREDICATE, and the two locks.** `Dialog.WindowStyle` comes from `ETb.FlagsToStyles`
(`ETb.cs:167-186`): bit 128 → Auto (else Plain), then bit 16 → Transparent overrides, else bit 4 →
NoTail. So the exposed flag bytes are **128 / 16 / 144 / 160**, and **0 / 4 / 8 / 64 / 132 are safe**.
Two independent locks, and the kit ships both:
- **`[NTUR]`** — `preventTurboKey` bails at `:976`, *before either arm*. Necessary but not
  sufficient on its own as a design: it is re-asserted only while a label RENDERS
  (`DialogBoxSymbols.cs:327-329` via `UILabel.OnFill`) and is cleared by any delivered
  confirm/cancel (`:838`/`:849`), so a fully-typed static page can lose it mid-life.
- **a window STYLE outside the predicate** — structural, needs no tag and no render pass. **This is
  the primary guard.**

**The safe polled shape**, in full: `WindowAsync(win, flags=0)` → `Wait(debounce)` → poll
`const4(0xB0000) B_KEYON` → `CloseWindow(win)`, with the `.mes` entry carrying **`[NTUR][NFOC]`**.
Stock-common, not an invention: 2,034 `WindowAsync`+poll sites across 115 shipping fields (field
2950, Chocobo's Forest, is the verbatim readout precedent).

**In the kit:** `content/text.py` owns the law — `window_style_of(flags)` transcribes
`FlagsToStyles` and **`turbo_injectable(flags)` IS arm B's predicate**, derived from it rather than
hand-listed. `content/event.polled_window` REFUSES an injectable style at the emitter (that guard is
structural, so it is made unrepresentable rather than linted); `polled_window_problems` scores the
rest on the emitted `.mes` entry, and `build.validate` runs it on both lanes that can emit the shape
(`[[choice.options]]` and `[ate]` options). ⚠ **Still unbenched, recorded here so it is not
re-discovered:** `[[qte]]` (flags 160), `[[behavior.hud]]` and `content/numinput.py` (flags 16) all
open inhibited windows *inside* arm B's predicate while polling `B_KEYON` — a latched F9 can resolve
a QTE or a Treno bid with no press. The instrument to see it (`text.turbo_injectable`) now exists;
nothing calls it on those three lanes.

## 7b. ★★ THE RAISE-SATURATION LAW — the raise is clamped, not uniform (2026-08-03)

`DialogManager.RiseAll` (`:436-446`) bumps a window by `DialogAdditionalRaiseDepth` (22) **only while
its depth is below `DialogMaximumDepth + DialogAdditionalRaiseDepth` = 90**. Base depth is `68 - 2*id`,
so the ceiling is reached at different raise counts per id:

| id | base | after 1 | after 2 | after 3 |
|---|---|---|---|---|
| 0 | 68 | **90** (saturated) | 90 | 90 |
| 1 | 66 | 88 | **110** | 110 |
| 7 | 54 | 76 | **98** | 98 |

So the "id 0 is frontmost" rule (§5) holds only up to saturation: **after a third raise the id order
INVERTS** — window 1 sits at 110, in front of window 0's 90. Stock never trips it because it raises
once per window OPEN (7,285 of 7,590 raises sit immediately after a `WindowAsync`); each new window
enters below the raised ones and is lifted together with them, preserving order. A bare re-raise of an
unchanged stack is the shape that breaks it, and stock has none. (Cross-check: the Treno 5-window
keypad, §4's richest multi-window UI, calls `RaiseWindows` **zero** times — the raise belongs to the
fade brackets of §11b, not to multi-window UI.) Kit: `opcodes.raise_windows` carries the law, and
`open` never folds a raise in — it stays a separate step, as it is a separate opcode in stock.

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

### 8b. ★★ The FULL unison recipe, and THE SIGNAL-TIMEOUT LAW (2026-08-03 — supersedes the sketch above)

Reading the whole site rather than the `while` line changes the shape materially. Field 41 @731-743,
verbatim, is **six** beats, not three:

```
SetDialogProgression( 0 )                                   ; zero it
WindowAsync( 2, 128, 182 )                                  ; Zorn's window (Thorn's obj opens win 3 @908)
set VAR_GlobUInt8_29 = 250                                  ; ★ SEED A FRAME COUNTDOWN
while ( (GetDialogProgression < 2) && (VAR_GlobUInt8_29 > 0) ) { Wait(1) ; VAR_GlobUInt8_29-- }
while ( (!IsButton(Confirm)) && (!IsButton(Moogle)) ) { Wait(1) }   ; ★ poll the dismiss MANUALLY
CloseWindow( 2 ) ; CloseWindow( 3 ) ; SetDialogProgression( 0 )     ; ★ close BOTH, re-zero
```

Four things the one-liner missed:

1. **★ THE SIGNAL-TIMEOUT LAW — stock never trusts the signal.** Every guarded wait seeds a 250-frame
   (~8s) countdown beside the condition. Census across all 817 scripts: 319 `GetDialogProgression`
   reads in 81 fields, of which **117 carry the guard** (112 × `< 2`, 3 × `< 4`, 2 × `< 3`); the
   unguarded shapes (`== 0` ×113, `!GetDialogProgression` ×42, `< 1` ×31) are single-window waits where
   the script itself is the only writer. **A cross-object/text-driven wait is ALWAYS guarded.** Reason:
   text is not a guaranteed event — a shorter translation can omit the tag, a skip can race it, a
   replaced window never renders its own tag — and an unguarded spin then hangs the field forever.
2. **The script polls the dismiss button itself**, because the windows are undismissable (below).
3. **The script closes both windows**, and re-zeroes the signal after.
4. **The counting is entirely in the text.** Field 41 contains 31 `SetDialogProgression` calls and
   **every one of them is `SetDialogProgression(0)`** — nothing in the script ever writes 1 or 2. The
   `< 2` is reached by two `[INCS]` tags, one per speaker's entry. That is the strongest available
   confirmation of §12's correction, and it is visible only by grepping the *whole* field.

**★ THE BRACKET-FORM CAVEAT (new).** Memoria has TWO tags behind the name `IncreaseSignal`:

| what the text says | enum reached | effect |
|---|---|---|
| `[INCS]` (bracket/original format — what the kit writes) | `IncreaseSignalEx` | signal only |
| `{IncreaseSignal}` (modern curly format) | `IncreaseSignal` | signal **+ `FlagButtonInh`** |

`FFIXTextTag.OriginalTagNames:343` maps the string `"INCS"` to the **Ex** (signal-only) form; the
compound one is reachable only from the curly format and is what `Import/Fields/FieldTags.cs:45`
rewrites the sequence **`[INCS][TIME=-1]` → `{IncreaseSignal}`** into. So stock's unison entries carry
that PAIR, and the `[TIME=-1]` is **load-bearing, not redundant** — it is what makes the window
undismissable, which is in turn why the script has to poll `IsButton` itself. Emitting `[INCS]` alone
leaves the window dismissable and the player can race the handshake.

Also corrected while here: `[TIME=n]` has a **third** mode. `OnTime` (`DialogBoxSymbols.cs:811-829`)
sets `EndMode = n` + `FlagButtonInh` for `n > 0`, sets `FlagButtonInh` alone for `-1`, and for **`0`
CLEARS `FlagButtonInh`** — re-granting dismissal to a window an earlier tag inhibited.

**★★ BUILT AND IN-GAME PROVEN** (kit `1.0.0b17`+; bench 30603, owner-confirmed round 2): cutscene steps
`open` / `close` / `wait_window` / `raise` (item 8) and `set_signal` / `wait_signal` + the text-side
`signal` / `hold` keys (item 7). The wait compiles stock's guarded shape and there is **no unguarded
form to author** — `timeout <= 0` raises. Emissions and laws pinned in
`ff9mapkit/tests/test_multiwindow.py`.

**The handshake itself is confirmed, by a measurement the bench was built to force.** The unison's
post-signal wait is 60 frames (~2s) against a 250-frame (~8.3s) guard, so the pause length reports
which path the loop took — its failure mode is otherwise indistinguishable from success, since a
timed-out wait still continues and still closes both windows. Owner measured **~2-3s**: the `[INCS]`
tags fired as each line finished typing and the wait exited **on the signal**. So text→script
synchronization is real, not just plausible from source — mid-line camera cuts, SFX stings and actor
reactions timed to words all have a proven substrate.

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
7. **Text-synchronized choreography** — ★ **BUILT** (§8b): `signal = "+"|n` / `hold` on any
   say/open line, `{set_signal = n}` and the guarded `{wait_signal = n, timeout = 250}` step.
   Mid-line camera cuts / SFX stings now compose from these. STILL UNBUILT: splitting a signal
   into the MIDDLE of a line (`signal_at = "word"`) — today the tag lands at the end — and
   `[PSND=id]`, the zero-logic pure-SFX variant.
8. **Multi-window scene verbs** — ★ **BUILT**: cutscene step kinds `open`/`close`/`wait_window`/
   `raise` on both flavors (narration + cast), with a window ledger that refuses a leaked or
   un-closable window. Unlocks unison speech, staged countdowns, a held hint under rolling
   dialogue. STILL UNBUILT: the same verbs as `[behavior]` step kinds.
9. **`variables = [...]` on any line** — bind gMesValue slots to flags/counters/gil
   before the window (the chest already does exactly this); gives every line live
   `[NUMB]`/`[ITEM]`/`[TEXT]` access + `[PNEW=bit]` conditional icons.
10. **Per-language authored text** — accept `dialogue = { us = "...", fr = "..." }`;
    `mes_parts` is already per-language, only the broadcast needs splitting.

### ★ THE TWO OPEN PIECES — the whole gap list's live items (2026-08-04)

Everything else in Tiers 1-2 is built and in-game proven. These two are what a next session picks up,
written to be startable cold.

**A. Per-language authored text (item 10).** Today every language gets the SAME authored string: the
build resolves one line and broadcasts it to all 7 (`suffix, {lang: suffix for lang in langs}` — the
pattern repeats at each `_verbatim_*_messages` site and in `collect_text`). The plumbing underneath is
ALREADY per-language — `mes_parts` is keyed by lang and `[[logic_edit]] kind="text"` edits donor lines
per-language today — so the work is splitting the broadcast, not building a channel.
- **Seam:** every `{lang: suffix for lang in langs}` construction in `build.py`, plus `_add`/`_add_raw`
  in `collect_text` (which assemble ONE line and hand it to `build_mes`).
- **Shape:** accept a table wherever a string is accepted (`dialogue`, `message`, `say`/`open`, choice
  `prompt`/`text`/`reply`, `speaker`); missing languages fall back to `us`, which keeps every existing
  single-string project byte-identical.
- **Watch:** wrapping is per-language (widths differ by script); the speaker convention differs by
  language and the engine knows it — `VoicePlayer.cs:147-155` detects the name line by `\n“` (English),
  `\n「` (Japanese), `:\n` (German/French), `\n─` (Italian/Spanish). `with_speaker` emits the English
  form unconditionally, so a per-language lane should carry the per-language attribution shape too, or
  VA name-keyed lookups silently miss on non-English.

**B. Mid-line signals — `signal_at = "word"` (the rest of item 7).** `signal`/`hold` and the guarded
`wait_signal` are built and proven, but a signal tag can only land at the END of a line, so a script
can block until a line finishes typing and no finer. The engine substrate is finer-grained than the
kit: `[SIGL]`/`[INCS]` fire at whatever text POSITION they occupy, typewriter-aware.
- **Why it matters:** end-of-line sync gives unison. MID-line sync is what times a camera cut, an SFX
  sting, or an actor's flinch to a *particular word* — the capability §8 called "far more general".
- **Seam:** `text.dress_window` appends the tag as a suffix; mid-line means splicing at a match inside
  the string BEFORE wrapping (so the tag doesn't land inside a wrapped word), then the existing
  `wait_signal` steps gate on it unchanged.
- **Shape:** `signal_at = "<substring>"` (first occurrence, error if absent so a typo is not a silent
  no-op), or a list for several marks in one line.
- **Precedent, and its limit:** stock's `[SIGL]` sites are mid-line (`"YES![WAIT=30][SIGL=1] THAT'S
  IT![WAIT=25][SIGL=2]"`, quoted in `DialogBoxSymbols.cs:846`) — so the SHAPE is stock-grounded, but
  stock only ever consumes it for window-open sync. Anything beyond that is ours, and the Tier-3 rule
  applies: ground each use against a real site before shipping it as an idiom.
- ⚠ **`[PSND=id]` is NOT the shortcut it looks like.** §6b: zero stock uses in field text. The
  earlier recommendation of it as the "zero-logic SFX variant" was a parser-read, not a census result.

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
