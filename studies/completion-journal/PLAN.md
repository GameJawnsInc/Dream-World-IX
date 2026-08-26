# An in-game 100%-completion Journal for FF9 — scoping study

> Standing reference. Read-only research pass: nothing was built, deployed, or
> played. Every engine claim is static source against the LIVE PATCHED clone at
> `C:/gd/FFIX/Memoria` (HEAD `6b8bb2d5` + the `memoria-patches/` stack applied),
> not against stock Memoria. No in-game behaviour was observed by anyone in this
> pass — where a mechanism has never run, it says UNVERIFIED.

**STATUS: ★ rungs 0 + 0b + T1 + T1b + ROUND 6 ALL OWNER-CONFIRMED in-game. Every DLL-free read path works, the offline `journal report` reads a real save, and the 7-page in-game dashboard opens, holds, and shows its own LIVE numbers on bench 30801. ★ ROUND 6 PLAYTEST-CONFIRMED (2026-08-26): the `[[text_table]]` lane resolves both STRING rows live — T.Hunter rank shows the computed 'G' at 215 points (the old frozen literal was 'H', and a sibling save block at 178 points still reads H, so the letter is per-save computed), Hunt winner resolves 'Vivi' (index 2) — and BOTH cross-validate EXACTLY against the offline `journal report` on the same container. Live-rows-only pages confirmed good (Party 2 lines, Combat & Meta 3, no "S. purchases"). ⚠ Windows self-closing during a playtest = TURBO-DIALOG (F9), not the mod -- check that FIRST (§7.1). ★ ROUND 7 PLAYTEST-CONFIRMED (owner, New Game 2026-08-26): the checklist page's marks update LIVE IN PLAY — two cargo-hold pickups flipped their rows to OK while the three uncollected rows held '--', the names rendered off the live tables in the engine's own item colour, the gil literals and the width were right. The atlas latch join is verified end-to-end (b7174/b7175 verify=playtested). The bench now carries ALL 7 packs of d1.prima-vista (15 menu rows). What round 7 built: the entry catalog is LIVE code — `journalcatalog.py` + shipped `data/journal_catalog.toml` (the 55-section spine + the first authored section, d1.prima-vista, 30 prose-passed rows seeded from the treasure_join atlas; deferrals declared, all 8 laws lint-breakable) and the CHECKLIST surface (`checklist_pages`/`render_checklist`: live `Global.Bit` marks + runtime `[ITEM=]` names + gil literals, packed under the 8-slot/13-line ceilings). ★ ROUND 8 BUILT, UNPLAYTESTED: the NEXT-OBJECTIVE ladder — `[[section]] objective` (authored: prima-vista "Kidnap Princess Garnet"; the rest title-fallback), one `story.next_objective` catalog row (offline read + rank-ladder-class `.eb` expression + generated `objectives` [TBLE], all from ONE `main_story_ladder()`), rendered full-width as the story page's last line; offline cross-validated on 3 real save blocks (SC 1000→"Kidnap Princess Garnet", 6000→"Fossil Roo", 7200→"Alexandria (the coronation)"). AUTHORING SCOPE (owner): through Vivi reaching the roof with Puck — the current 30 rows ARE that scope (castle bits 7223/3793/7211 are past it, next seeds). ★ THE MENU: owner directed a real in-game Journal replacing Folklore's row — design proposal + 4 ratification questions in `MENU-DESIGN.md` (JournalPatch.txt data plumbing, 3 tabs, rungs M0-M5). MENU-DESIGN.md ★ RATIFIED (all 4 as recommended: Folklore hidden / 3 tabs / "????" gating / merged story tab) and rung M0 IS BUILT + DEPLOYED (s81: the Journal takes Folklore's menu seat, skeleton scene, [Journal] Enabled default-on ini gate; gates clean, backup 20260826-152511). M0 ★ OWNER-CONFIRMED (row works, skeleton opens/closes clean) and rung M1 IS BUILT + DEPLOYED (s82: the STORY tab -- NOW banner + the 44-row section list off JournalPatch.txt; the kit now emits the catalog sidecar at every deploy: render_patch/_emit_journal_patch/deploy copy, golden-tested). NEXT = playtest M1 (RELAUNCH; the Journal opens on the STORY tab: banner reads the save's objective, list shows reached titles + "????" beyond, current row yellow, scroll works, cancel clean) + 30801's story-page objective line (still unplaytested); then M2 = the section-detail pane with live latch marks; the standing §4c owner ask (disc-3/4 checkpointed saves) stays open.**

**★ §7.2 Q3 ANSWERED BY THE OWNER (the tier decision): FULL FIDELITY — the
walkthrough-shaped journal, T4-high, "aware that it will take a massive amount of
human authoring" (their words). Consequences now in force: (1) the Q2/Q2b censuses
run FIRST and their numbers bound the generator claim before any row is authored;
(2) the catalog schema freezes only after those numbers land, and it carries the
set-then-clear window column, `exclusive_group`/`run_mode`, a provenance tag, and
runtime name resolution (§7.4) from day one; (3) the turbo-proof page primitive
(`WindowAsync` + `[NFOC]` + input poll) is built BEFORE mass authoring so rows are
never authored against the wrong surface; (4) Q5 defaults to NON-localized
(identical bodies in 7 language dirs, the kit's standing convention) unless the
owner says otherwise; (5) Q4 posture per the owner's earlier ruling: the GameFAQs
guide is a reference/cross-check, never reproduced — facts re-derived from engine
bytes + our own censuses, prose original, missable verdicts OURS (from the census
and the owner's playthrough), not a copy of any compilation's selection. The
standing owner ask from §4c stays open: disc-3/4 checkpointed saves are worth more
to this feature than any amount of engineering.**
---

## 1. Verdict

**Feasible, and the interesting question is which tier — not whether.** The
substrate is all there: the engine already keeps ~30 completion-bearing values,
the kit already decodes `gEventGlobal` and renders a save report, and the project
has already shipped a brand-new FF9 menu screen once (`FolkloreUI.cs`, 2197
lines, s45+s46).

**On the ScenarioCounter-dictionary hypothesis, directly: the mechanism is sound
and the resolution is wrong for a quest tracker.** ScenarioCounter is `gEventGlobal[1]<<8 | gEventGlobal[0]`
(`Global/Event/EventState.cs:16-18`), readable DLL-free from `.eb` and offline
from a save. Its real resolution is **321 distinct absolute values set across the
676 real fields** (`research/CENSUS_DIGEST.md:14`), which is too granular to be
human-meaningful, and the kit's curated join is **52 anchors carrying only 39
distinct place names** — `Alexandria Castle` appears 5×, `Lindblum` 3×, and seven
more names twice (measured over `ff9mapkit/ff9mapkit/flags.py:431-445`). It is a
nearest-anchor LOCATION lookup — which is exactly what `nearest_milestone()`
(`flags.py:491-497`) does with it — not a quest list.

**Monotonicity is UNRECONCILED and both numbers are in the repo.** The old
676-field census records `{'++': 7, '--': 7, '+=': 1, …}`
(`research/CENSUS_DIGEST.md:15`) — seven fields decrementing. The
narrative-state arc's 818-field probe measures **889 absolute SC writes vs 2
relative**, i.e. "near-pure absolute assignment", and that arc carries the
reconciliation as its own open risk #5 (`studies/narrative-state/PLAN.md`).
Either way `EventState.cs:16-22` is an unguarded read/write property, so
"SC ≥ close_sc ⇒ permanently missed" is **not** a free derivation — but how
un-free is currently unknown, and this study should not be cited as having
settled it. **Do not build a missable column on it until that census is
reconciled**; it is cheap to settle and it gates the feature's worst failure
mode.

**Verdict:** the counter is an excellent *chapter heading* and a poor *quest
key*. Build the journal as a read over the whole state inventory (§2), with
ScenarioCounter as one column. **The single biggest cost is not the screen —
it is catalog prose**, and the repo has already measured that cost: its best
generator turned 937 machine-derived candidate bits into **17** curated per-bit
meanings (§4b(ii)).

**Recommended commitment: T0 + T1 + T1b now** (T1b is the in-game floor — a
~25-counter paged dashboard on stock Memoria, and the thing worth shipping if the
catalog program is ever declined). **T2 on an owner call**, where the actual
decision is not aesthetic: T2 ships the custom engine, which is free for any mod
already forking fields (those need the s23-s33 gates anyway) and a **new tax on a
novel-field-only mod**. **Nothing above T3 until a catalog generator's residue
has been measured** (§7 Q2).

### 1.1 The rung-0 probe — build this first

**The riskiest cheap assumption is that the DLL-free read paths work at all.**
Three mechanisms carry most of T0/T1b/T3 and **none has ever executed**:
`Null.SBit[5]` (memoria_variable — zero shipping precedent anywhere),
`flex(16,3)` `PLAYER_ABILITY_LEARNT` (no kit emitter today), and the
expression-valued `SetTextVariable` (the kit's helper is immediate-only —
`eb/opcodes.py:466`).

**One bench field in the scratch band (30000-32767), one window, one playtest
round.** Full probe spec and its two guards → §7.1. If those reads work, the
ladder is a scheduling question; if any returns 0, the whole DLL-free half
collapses onto the C# path — and you learn that on day one instead of after a
catalog exists.

---

## 2. What the game already knows

Five distinct stores, not one. "Addressable" below means: readable by an `.eb`
script on **stock** Memoria (no DLL), because that is the axis that decides
whether a tier needs the engine bundle.

| Category | Where it lives | Decoded today? | DLL-free `.eb` read? |
|---|---|---|---|
| ScenarioCounter | `gEventGlobal[0..1]` | ★ yes (`flags.py:745-763`) | ★ `Global.UInt16[0]` |
| Treasure-Hunter points + rank | derived: popcount of bytes 896-960 & 966-975 (×1) + 182-186 (×2), `Global/Event/EventState.cs:62-70`; ranks H..S at `:53-61` | ★ yes (`flags.py:421`, TH_POINT_RANGES) | ★ `Null.SBit[5]` (memoria_variable `TREASURE_HUNTER_POINTS`, index 5 of the enum at `Global/EBin.cs:2416-2431`) |
| **Per-chest identity** | **nowhere** — each chest's bit is authored in its own field's `.eb` | **NO** | **N/A — no registry exists** |
| Key items (obtained + used) | `FF9StateGlobal.rare_item_obtained` / `rare_item_used`, HashSet<Int32> (`Global/ff9/State/FF9StateGlobal.cs:975-976`) | partial (names read live, `keyitems.py:1-25`) | ★ engine-level `const(256+n) B_HAVE_ITEM` (op 100, `eb/_exprtable.py:38`) — **but the KIT refuses it today**† |
| Chocographs found / dug | Int24 @byte 187 / @byte 184 (`Global/ChocographUI.cs:243-256`) | ★ yes | ★ but **sign-extends** — see §6 |
| Sandy beaches (21) | 21 bits from 856 (`Global/EMinigame.cs:472-483`) | ★ yes | ★ 21 static reads (no computed index) |
| Stellazzio (13) | UInt16 @byte 355, 13-bit (`EMinigame.cs:415-427`); also key items 48-60 | ★ yes | ★ |
| Chocobo beak Lv (1-99) / terrain ability | `gEventGlobal[139]` (`EMinigame.cs:280-283`) / `[191]` (`ChocographUI.cs:245`) | ★ yes | ★ |
| Mognet delivered / Stiltzkin tally / letter slots | bytes 1032 / 1033 / 1034+4k; give+read locks bits 8376-8503 (`content/mognet.py:10-27`) | ★ yes | ★ |
| Ragtime quiz | `(gEventGlobal[198]>>3)&31` of 16 (`Global/battle/BattleAchievement.cs:38-46`) | derivable | ★ |
| Tetra Master cards + W/L/D | `FF9SAVE_MINIGAME` card list; kinds/points/collector-level derived (`Global/Quad/Mist/QuadMistDatabase.cs:111-241`) | offline yes | ★ `B_SYSVAR[19]` (**clamped to 95**, `EventEngine.GetSysvar.cs:57-69`) or `Null.SBit[3]`/`[4]` |
| Frogs / gil / play time | `Frogs` / `party.gil` / `Settings.time` | ★ yes | ★ sysvars 16 / 6 / 20 |
| Per-character AP + mastery | `PLAYER.pa` / `pa_extended` | offline yes | ★ `flex(16,3)` `PLAYER_ABILITY_LEARNT` (`Global/EBin.cs:2388-2410`) — **no kit emitter today** |
| **ATEs (79 of 83)** | `AchievementState.AteCheck` Int32[100]; id computed by the hardcoded `EMinigame.MappingATEID` switch | no | **NO** |
| **Ever-learned ability sets, synthesis count, auction wins, Stiltzkin buys, Quadmist win list** | `AchievementState` (`Global/Achievement/AchievementState.cs:106-180`) | no | **NO** |
| Kill counts (per model + 8 categories) | `modelKillCount` / `categoryKillCount` (`FF9StateGlobal.cs:849-850`) | no | **NO** (NCalc only) |
| Achievement keys | `AchievementState.EvtReservedArray` Int32[17], **2 bits = a STATUS, not a count** | no | **NO** |
| **Bestiary / per-recipe synthesis / Nero family / 8 of 9 friendly monsters** | **nowhere** | **NO** | **NO** |
| Step count | `EventState.gStepCount` — declared, saved, sysvar-7 readable, **never incremented** (`NCalc/NCalcUtility.cs:247` carries the TODO) | n/a | reads 0 forever |

† **Kit-level gap, one line.** `content/behavior.py:1740` raises unless
`0 <= iid <= 254`, so the `item:` HUD lane cannot address key items (256+n) or
cards (512+n) — exactly the ids a journal wants. Lifting the bound is trivial;
doing it correctly also needs disambiguation against the folklore band, which
mints its entries as important-ids 80-254 in the same namespace (§T2).

**Three structural facts fall out of this table and they set every tier boundary
below.**

1. **The `AchievementState` bucket is unreachable from `.eb`, and is a
   *bounded* offline problem rather than an open-ended one.**
   `ParseAchievementDataToJson` runs only on the encrypted main node
   (`Global/JsonParser.cs:46`); the extra carries only
   `95000_Setting / 20000_Event / 40000_Common / 30000_MiniGame` (`:225-240`).
   **Revised during the T1 build:** its save node `80000_Achievement` is a
   **fixed-size, sentinel-padded block** — 100+17+8+221+63+3+300 Int32s = 2848
   bytes, arrays tail-padded with −1. That is a materially cheaper location
   problem than "map the whole flat stream", which is how the scoping pass
   priced it. It still stays OUT of T1 (shipped as labelled `untracked` rows),
   but T3's blocker is smaller than originally written.
2. **The achievement array is a latch, not a counter.** `AchievementStatusesEnum`
   = `{NotUnlockYet, ReadyToUnlock, UnlockComplete, Invalid}` (verified by
   reading the file). `ReportAchievement` computes `percentProgress`
   transiently and persists nothing but the status
   (`Assets/SiliconSocial/AchievementManager.cs:72-94`). The `Target`
   denominators ARE engine-native and worth transcribing; the numerators are not
   stored and must still be recomputed from the scattered stores.
3. **There is no chest registry at any price.** The engine's only chest-aware
   code is the blind weighted popcount above. The kit's own `[[chest]]` block
   REQUIRES an explicit `flag_idx` for exactly this reason
   (`ff9mapkit/ff9mapkit/content/chest.py:43-45`).

---

## 3. The tier ladder

Synthesized from four independent designs. The ordering principle that survived
adversarial review: **calibrate the numbers where no NGUI law applies, then
render them; the screen is cheap and the catalog is not.**

| T | What ships | Engine | Entries | Eng. LOC (feature) | + tests/docs/GUI | Playtest rounds | Authoring | Risk class |
|---|---|---|---|---|---|---|---|---|
| **T0** | debug-menu completion panel | DLL (1 existing file) | ~25-40 counters | ~150-300 C# | ~0 (dev surface) | 0-1 | none | ★ proven substrate |
| **T1** | offline `journal report` + Workspace panel | none | ~40-90 metrics | ~400-700 py | +500-900 test, +60-120 doc, ~20 form | 0 | ~90 rows, mechanical | ★ proven substrate |
| **T1b** | in-game field read-out (paged dashboard) | **none — stock Memoria** | ~25 counters / ~6 pages | ~400-700 py | +400-800 test, +60-120 doc | 3-5 | ~250-350 `.mes` lines | high |
| **T2** | `JournalUI` menu screen, folklore-shaped | DLL (~600-800 new C#) | 50-300 named rows | ~600-800 C# + ~1,500 py | +800 test, +200-400 doc, ~20 form | 3-5 | 50-300 rows | high |
| **T3** | per-row state + counters + static meter dashboard | DLL (+~750-1,250) | ~300 observable rows | +~750-1,250 C# **+ the heterogeneous resolver (no donor, unpriced)** | +300-600 test | +5-8 | ~300 rows ≈ 10-13 authoring-days | medium |
| **T4** | the mined chest atlas + missable verdicts | none beyond T3 | ~600-1,800 | **generator unpriced** — the grant↔latch join is new branch-walking work, NOT a re-run of the 464-LOC `gen_flag_lore.py` archetype (§T4) | — | 0 new | **~600-1,800 rows + an owner playthrough** | low |
| **T5** | bars-in-list, scrolling detail, per-entry art | +~600-1,000 C# | as T4 | +~600-1,000 | +300-600 test | +8-15 | + per-entry model tokens | medium, and **it mints two new widget classes** |

**LOC bases** (so no cell is a free-floating guess): T1/T1b python bands against
`content/gauge.py` 334 / `content/numinput.py` 413 / `content/choice.py` 310;
T2's ~1,500 py against the folklore precedent `content/folklore.py` 467 +
`tests/test_folklore.py` 821 + build/config/deploy wiring ~195; the C# bands
against `FolkloreUI.cs`'s measured 1296 code lines (§4a); test bands against
`test_folklore.py` 821 / `test_itemdata.py` 845; doc bands against a FORMAT.md
section (60-120 lines) plus an optional dedicated doc (200-400) plus ~10 CHANGELOG
lines; GUI at ~20 LOC for a form spec versus 600-900 for a dedicated Workspace
tab. **§4b(iii)'s cautionary tale is that folklore shipped with zero docs and zero
GUI — do not repeat that omission by leaving these columns off the estimate.**

**T3's entry count is a band, not the 310 the designs quoted.** That subtotal
embedded 52 story beats which measure as **39 distinct** (§6.9), so the honest
figure is ~**297-310** and it should be re-summed per category before anyone
schedules against it.

**Read the LOC and the ROUNDS as the estimate; the "Risk class" column mixes two
different risks on purpose and you should read it that way — T4's "low" is a DATA
risk (the denominator is unknown, §T4) while T5's "medium" is a CODE risk (new
widget surface).** Every engineer-day figure on this page is a derived conversion
at an unvalidated ~250-400 diff-LOC/day, applied to a codebase measured at 38.5%
comment-only lines (`FolkloreUI.cs` = 2197 lines → 1296 code / 812 comment / 89
blank). No LOC-per-day or rounds-per-day rate exists anywhere in this repo.
Rounds gate on one human who is also the catalog verifier and the only person who
can play the game.

---

### T0 — the debug-menu completion panel

**Player sees:** nothing. This is a developer surface and its job is
calibration.

**Mechanism:** extend `StorySummary()` in
`Global/UI/UIKey/Ff9mkDebugMenu.cs:2530` into its own tab. The debug menu is
immediate-mode, so **zero of the ~20 NGUI construction laws apply.**

**Roughly half the numbers have a first-party accessor; the other half must be
re-derived.** Free: the `Memoria.GameState` facade
(`Memoria/Battle/Calculator/BattleCalculator.cs:31-70` — Frogs,
CategoryKillCount, ModelKillCount, TotalKillCount, EscapeCount, BattleCount,
TetraMaster*, TreasureHunterPoints, GameTime, ScenarioCounter, HasKeyItem, Gil,
Thefts), plus `EventState.GetTreasureHunterPoints()` and
`QuadMistDatabase.MiniGame_GetCollectorLevel()`. **Not free — verified this
pass:** `EMinigame.CountVisitedSandyBeach()` is `private static`
(`Global/EMinigame.cs:474`), as are `numOfTreasures` / `numOfSandyBeach`
(`:762-763`), and the chocograph read is inline inside `AllTreasureAchievement()`
(`:430-438`), which returns `void`. `Memoria.GameState` exposes **no**
`AchievementState`, chocographs, beaches or Stellazzio. So beaches, chocographs,
Stellazzio and beak level must be re-derived from raw `gEventGlobal` in the new
panel — which is fine, and is exactly the arithmetic every tier above reuses,
but it is net-new code at the tier the whole ladder is calibrated on.

**Why it is first:** the project's own standing rule is *calibrate the instrument
before you judge with it.* T0 proves every read path before any surface is
minted, and it costs one existing file.

**It had to fix a live defect first — ★ DONE, owner-confirmed in-game.** The
shipped debug readout popcounted `gEventGlobal` bytes 1047-1063 and printed it as
**"chests opened"**; that band is bits 8376-8511, the **Mognet give/read lock
table** (`ff9mapkit/ff9mapkit/flags.py:56, :269-283`). `RegionLabel` carried the
same `[chest_opened]` label and additionally called 8512-16319 the "safe custom
band" while `flags.py:53` sets `FIRST_SAFE_FLAG = 8712` — i.e. it was telling
authors that 8512 is safe, which is the documented save-corrupter. The kit and
the research notes carried the mislabel too.

Fixed on `master` by `memoria-patches/s78-debug-menu-flag-band-labels.patch`
(+ `content/chest.py`, `research/STORY_FLAGS.md`); `RegionLabel` now splits the
Mognet mailbox / give locks / read locks / margin / read-mail payload bands
separately and floors the safe band at 8712.

**One of this study's own sub-findings was wrong and is recorded here so it is
not "re-fixed".** The scoping pass flagged `bit == 184 || bit == 191` as a
bit-versus-byte confusion against the chocograph offsets. **It is not a bug** —
those are byte 23's genuinely *bit*-addressed engine handshake (field-menu guard
at 23.0, boot scratch at 23.7). The real gap was the opposite: the *byte*-184-191
chocograph range (bits 1472-1535) had no label at all. s78 adds it and documents
the two addressing modes at the call site.

**The standing lesson for the journal, unchanged:** a Bit var's index is a bit
address (`byte = n>>3`), a Byte/Int16/Int24 var's index is a **raw byte offset**.
Every row in §2 mixes both. Anyone who builds a journal by reading a readout
without checking which addressing mode a row uses inherits a wrong number — which
is exactly how the "chests opened" line survived this long.

**Blocker:** an engine DLL rebuild AUTO-DEPLOYS over the live install with no
backup (CLAUDE.md §4). Back up `Assembly-CSharp.dll` first.

---

### T1 — the offline report

**Player sees:** nothing in-game. `py -m ff9mapkit journal report <save>` and a
panel in the existing Story State tab: *"Disc 3 — Alexandria Castle (SC 7200) ·
Chocographs 17/24 found, 12/24 dug · Beaches 9/21 · Stellazzio 11/13 · Key items
44/70 · Treasure Hunter 287 pts (rank C) · Beak Lv 38/99 · Cards 61 kinds, rank
14/31"*, plus an A→B diff of what one session completed.

**Mechanism:** extend the SHIPPED decoder, do not write one.
`flags.decode_gEventGlobal` (`flags.py:745-763`) already computes
ScenarioCounter, FieldEntrance, Treasure-Hunter points, the Mognet lock popcount
and every set bit grouped by region; `gEventGlobal_from_save` (`:766-790`) lifts
the base64 blob; `render_report` (`:838-856`) prints it; `render_diff` does the
delta. `workspace/savedoc.py` (842 LOC) is a shipping Qt seat that already
renders it with Treasure-Hunter points on screen. A new
`ff9mapkit/ff9mapkit/journal.py` (sibling of `refarc.py`) adds the named
byte/Int24/UInt16 reads from §2.

**The non-gEventGlobal state splits into a cheap path and an expensive one, and
the designs conflated them.** The Memoria-**extra** JSON sidecar
(`95000_Setting / 20000_Event / 40000_Common / 30000_MiniGame`, `JsonParser.cs:225-240`)
is plain JSON on disc — reachable with **no decryption at all**. **And the kit
already reads it**: `save_items.py` + `sjbinary.py` parse that sidecar today, so
the scoping pass's "T1 must add the extra-JSON reader" blocker is **void**.
Measured during the build, `40000_Common` also carries `frog_no`, `steal_no`,
`escape_no`, `battle_no`, the 8 kill categories and `kills_per_model`, and
`30000_MiniGame` carries the whole card list — which makes
`MiniGame_GetPlayerPoints` and `MiniGame_GetCollectorLevel` **exactly reproducible
offline** (measured on a real save: 431 pts, collector Lv 2). The
**encrypted main block** is the expensive half: it decrypts fine (below) but is
"a flat, schema-ordered value stream" (`save.py:12`) for which the kit has no
offset map — it locates `gEventGlobal` by scanning for its 2732-char Base64
field (`_find_b64_geg`, `:86-96`), a targeted trick, not a parser.

**Two row-level corrections found by executing the reads, not by reading source.**
(a) The gEventGlobal Stiltzkin byte 1033 is **not** the counter
`AllStiltzkinItem=8` scores — that is `AchievementState.StiltzkinBuy`
(`EMinigame.cs:50-52`) — so that denominator must not be attached to byte 1033.
(b) The Treasure-Hunter ×2 band (bytes 182-186) **overlaps** the
chocograph-opened Int24 (bytes 184-186), so dug chocographs already contribute 48
TH points: those two rows are **not independent**, and presenting them as separate
progress bars double-counts. All 10 `AchievementInfo` denominators were
re-verified across `DataWorld` and `DataJapanese` (all 87 keys) and are
**identical**, so the targets are region-independent.

**Why this is the highest-confidence tier in the ladder:** its rows are
transcribed engine constants with a `file:line` source, not prose. The engine's
own `Target` values pin nearly every denominator exactly —
`AllStiltzkinItem=8`, `AllPasssiveAbility=63`, `AllAbility=183`,
`AllSandyBeach=21`, `AllTreasure=24`, `ChocoboLv99=99`, `Frog99=99`,
`ATE80=79`, `CardWinAll=235`, `Moonstone4=4`
(`AchievementManager.cs`, the `AchievementInfo` dictionary).

**Blockers — much narrower than the designs assumed, and T1 is now BUILT.**
`flags.gEventGlobal_from_save` reads OPEN JSON or bare base64 only
(`flags.py:766-769`), but `ff9mapkit/ff9mapkit/save.py` closes that gap and it is
verified, not speculative: AES-256-CBC, PBKDF2-HMAC-SHA1 ×1000, salt
`[3,3,1,4,7,0,9,7]`, password literal `"System.Security.SecureString"`
(`save.py:1-24`), exposing `FF9Save.gEventGlobal(n)` over real
`EncryptedSavedData` slots. `save_items.py` + `sjbinary.py` cover the extra
sidecar. **Every gEventGlobal-backed row in §2 is reachable today, and the reads
were executed against a real save container** — TH 215 pts, chocographs 9 found /
6 dug, Stellazzio 5/13, ragtime 3/16, beak Lv 16/99, Mognet 13 delivered, hunt
winner 2, coins 13/51, cards 431 pts / collector Lv 2. All decoded sanely, which
retires the "does the substrate actually work offline" question entirely.

The one remaining gap: per §2 fact 1 the `AchievementState` bucket is
main-block-only, so T1 cannot validate the achievement rows T3 would render —
but that is a bounded 2848-byte fixed-layout block, not the open-ended
flat-stream mapping the scoping pass assumed.

---

### T1b — the in-game read-out, stock Memoria

**Player sees:** a journal you talk to — a book prop, an NPC, or a save-point
sibling. Confirm opens a `[[choice]]` menu (Story / Treasure / Chocobo / Cards /
Moogles / Misc); each choice draws one bordered window of live counters.

**Mechanism:** pure `.eb`. `SetTextVariable` (0x66) publishes into `[NUMB=n]`
slots; prose rows come from `[TBLE=]` banks read via `[TEXT=bank,slot]` →
`ETb.GetStringFromTable` (`Global/ETb/ETb.cs:270-283`); the choice list is
`EnableDialogChoices` 0x7C, already emitted by `content/choice.py:156-208`. Bar
art can ride the shipped `[[gauge]]` background-overlay lane (in-game proven on
bench 30420).

**The load-bearing detail the whole tier rests on, and it has a kit gap.**
`SetTextVariable`'s value operand is read by `getv2()`, which **branches on the
instruction's `gArgFlag` byte** (`EventEngine.cs:1349-1362`, arg-flag at
`DoEventCode.cs:43`): bit set → `CalcExpr()` → a full Int32 expression; bit clear
→ a sign-extended 2-byte immediate. **Only the immediate path is capped at
±32767** — the expression path is not, which is what makes a live counter
publishable at all. The kit can emit arg-flags (`eb/opcodes.py:49-64`,
`arg_flags=`) but its helper `set_text_variable(slot, value)` is
**immediate-only** (`eb/opcodes.py:466`). Adding the expression lane is small,
and it is the single mechanism the whole zero-DLL tier stands on — put it in the
rung-0 probe (§7.1), not in T1b's build.

**Four ceilings decide the whole tier and none of them move without a DLL:**

| Ceiling | Value | Source |
|---|---|---|
| live integer slots | **8, globally** — one `Int32[8]` shared by every open window | `ETb.cs:230-234, :500` |
| windows | 8 named ids; depth = `68 − id·2`, so high ids sink | `Global/Dialog/Dialog.cs:1949-1959` |
| window text | **pages, never scrolls**; ~13-14 lines at `DialogLineHeight` 68, clamped y∈[24,~998] | `Dialog.cs:292-296, :1139-1146, :1761-1777` |
| choice rows | ~16 (kit packs availability into a UInt16, `choice.py:166-175`); engine tolerates ~31 (`Dialog.cs:213-231`) but the geometry binds first | — |

Plus a soft one: **there is no computed bit index for `gEventGlobal`.**
`EBin.expr_varSpec` reads the variable index as immediate bytes off the
instruction pointer (`Global/EBin.cs:464-478`); Memoria's 0xD3 computed indexing
applies to `gScriptVector`/`gScriptDictionary` only (`:1637-1665`). So 21 beach
bits is 21 statically emitted tokens, and entry count buys `.eb` bytes linearly
against the 64 KB offset budget (`ff9mapkit/ff9mapkit/binutils.py:39-47` —
measure with `eb_budget_used`, never `len()`).

**T1b is worth building and T1b's successors are not.** A paged 8-slot dashboard
is a genuinely good product for ~25 counters. Extending the same substrate to
per-entry rows means ~75 pages at 600 entries and ~220 at 1,770, with no cursor
and no scroll — at which point the folklore-shaped DLL screen (T2) is both
cheaper and strictly better. **The zero-DLL bet stops paying between T1b and
T3.** T1b is therefore also the **floor**: if the catalog program (§4b) is ever
declined, this ~25-counter dashboard is the shippable feature that survives.

**A silent-ignore trap found while building the probe.**
`behaviortoml.table()` (`content/behaviortoml.py:147-150`) returns `None` unless
`[[behavior.unit]]` exists — so a `[behavior]` block carrying **only** a `hud` is
**silently dropped at build time**, with no error and no warning. A dashboard is
exactly that shape. This is the project's signature defect class (a guard that
never executes) sitting directly in T1b's authoring path; gate it before
authoring, not after a black window.

**Two unresolved build questions.** (a) **Where does it live?** `[[logic_add]]`
is refused unless the project carries `[verbatim_eb]` (`build.py:930-934`), so
the journal prop either rides a verbatim fork or ships on a synthesized field —
decide before authoring, it changes the deploy story. (b) **`[TBLE]`'s upper
bound — ★ RESOLVED, and the caveat was narrower than it read.**
`NGUIText.GetDialogWidthFromSpecialOpcode` (`NGUIText.cs:60-84`) does carry a
second, packed `[TEXT=]` decode for `tableId > Byte.MaxValue` that
`DialogBoxSymbols`' replacement path does not implement — but that decoder's
**only** call site is `OnWidths`, the `[WDTH]` tag handler, which Memoria marks
`// Dummied` (`DialogBoxSymbols.cs:905`). The live render is a plain
`ETb.GetStringFromTable(UIntParam(0), UIntParam(1))`
(`DialogBoxSymbols.cs:59-60`), and width comes from `Dialog.AutomaticSize` over
the rendered strings. So the two passes cannot diverge unless an entry carries
`[WDTH=]`, which the kit never emits. **The under-256 rule is retired**; the real
rule is "no `[WDTH=]` on an entry that carries a `[TEXT=]`". The shipped bench's
banks are txid 509/510.

**★ THE `[[text_table]]` LANE SHIPPED** (`ff9mapkit/ff9mapkit/content/texttable.py`).
A block declares `name` + `rows`; the build emits one `[TBLE=<n>,]` `.mes` entry
per bank (added last, so a field without one stays byte-identical) and
back-substitutes the allocated txid into every `[TEXT=<name>,slot]` reference
through `content.text.txid_map` — the same function `build_mes` derives its own
mapping from, so an off-by-one bank is unrepresentable rather than checked. An
unknown name raises at the substitution site: the in-game symptom of a bad bank is
`String.Empty`, a blank line with no log. This is what unfroze T1b's two string
rows (owner: *"T hunter rank and chests opened are wrong"*).

**Unexercised mechanism, must be benched:** `Null.SBit[5]` for
`TREASURE_HUNTER_POINTS`. The encoding is verified statically —
`VariableSource.Null` = 3, `VariableType.Any` = 0 = `SBit`, and
`EvaluateValueExpression` dispatches `Null`+`Any` to
`GetMemoriaCustomVariable` (`Global/EBin.cs:1621-1637`, enum at `:2416-2431`
with `TREASURE_HUNTER_POINTS` at index 5) while every other `varType` under
`Null` falls through and **returns 0 silently**; the kit's packing at
`eb/exprasm.py:105-122` matches `EBin.getVarOperation` (`EBin.cs:511-519`)
byte-for-byte, giving `C3 05`. But there is **zero shipping precedent** anywhere
and no kit helper. Bench it before any tier depends on it.

---

### T2 — the `JournalUI` screen, folklore-shaped

**Player sees:** a real FF9 menu screen — the authentic scrolling entry list on
the left (stock key-item bars, cursor, hold-to-repeat rail with SFX 103,
snap-drag quantization), two stacked bordered windows on the right showing
category headline progress as text and the selected entry's description, L1/R1
category paging, `???` for locked rows. It looks like a screen Square shipped
because every pixel of it is.

**Mechanism:** a near-verbatim fork of `Global/FolkloreUI.cs`. Reused
essentially unchanged: runtime scene construction (`:1663-1760`) — backdrop =
`MainMenuUI` child 4 reskinned to `item_bg`, fade = `ScreenFadeGameObject` clone,
the two framed panes via `BuildFramedPane` (`:1624-1661`) at 780×500 @(410,150)
and 780×360 @(410,−300), body label from `LocationInfoPanel.GetChild(0)`, the
list from `ItemScene.KeyItemListPanel` → `RecycleListPopulator` with the
preserve-the-bake capture and the `SetDragAmount(0,0)` fixpoint (`:1743-1800`);
the pointer rect; Show/Hide/Cancel and the bumper `StepCategory` +
`MuteActiveSound` settle (`:256-320`). Routing is the same six sites in
`Global/UI/UIManager.cs` (`:157`, `:200-215`, `:244-245`, `:410-411`, `:648`,
`:726-731`) plus a `Journal` member **appended** to `UIState` (`:767-769` — never
a mid-enum insert; the ordinals are serialized).

**The opener should be `Menu(6,0)`, not a menu row.**
`EventService.FF9Menu_Command` has cases 0/1/2/4/5 only — **3, 6, 7 and 8 are
free** (verified by reading `Global/Event/EventService.cs:5-27`) — and
`OpenChocoGraph` (`:58-68`) is a ~10-line template. That lets any NPC, prop or
save point open the screen for ~12-14 C# lines. **What calls it is an owner
decision and it decides T1b's fate:** if the opener is a book prop or a
save-point sibling, T1b's field read-out and T2's screen are the same object at
two fidelities and T1b is a genuine stepping stone; if the opener is a menu row
after all, T1b is throwaway. Recommend the prop. A 10th main-menu row instead
costs seven edit sites in `MainMenuUI.cs` (`:73-74, :208-216, :589-590, :614-615,
:777-822, :833-834, :947`) **and is unverified** — the 684-unit layout walk
(`:806-822`) is playtest-proven at 8 and 9 rows only, and Folklore already took
the 9th.

**The journal must NOT reuse the key-item spine.** Folklore mints entries as
important-ids 80-254 because boolean ownership was its state model; that band is
175 slots, ids ≥256 are Memoria-sidecar-only and silently lost on a Steam-Cloud
time desync, folklore's dup check covers only `[[folklore]]` blocks
(`build.py:8609-8617`), and `ItemUI.DisplayKeyItem` now `continue`s on
`FolkloreConfig.Enabled && FolkloreRegistry.IsFolklore(id)`
(`Global/ItemUI.cs:725-735`) so any journal minting key items would appear inline
in the stock Key Items list unless it registers in the same filter. A journal
reading `gEventGlobal` / `AchievementState` / `MiniGame.SavedData` /
`Memoria.GameState` directly needs no key items at all — which deletes the
175-entry ceiling and the cross-feature id collision together. `RecycleListPopulator`
has no row-count cap (`Global/Recycle/RecycleListPopulator.cs:99-175`).

**Entry text should ship in the journal's own sidecar, not in a field `.mes`.**
Because our DLL parses our own registry (the `FolklorePatch.txt` recipe —
`FolkloreUI.cs:2085-2133`, `AssetManager.FolderLowToHigh` +
`TryFindAssetInModOnDisc`, per-folder try/catch, higher folder overrides per id),
entry strings can live there with per-language columns copying the
`LocalizationPatch.txt` CSV shape (`Memoria/Assets/Text/LanguageMap.cs:191-203`).
Routing journal text through a custom field `.mes` block instead imports an
entire hazard set for no benefit: the per-txid cumulative merge that always
includes the base game (the invisible partial "vanilla squat" —
`ff9mapkit/ff9mapkit/deploystack.py:1-33`), the mesID Int16 truncation at 32767
(`Global/Honolulu/HonoluluFieldMain.cs:19,:70`), mandatory `MessageFile`
registration or `DataPatchers` SKIPS the whole FieldScene into a black screen,
and a **hard THROW** if any of the 7 language dirs is missing
(`Memoria/Assets/Import/Fields/FieldImporter.cs:392-393`,
`Memoria/Assets/Import/Text/TextImporter.cs:22-26`).

**Blockers.** (a) The row count is the **player's**, not the designer's:
`MenuItemRowCount` binds default **12**, user-settable
(`Memoria/Configuration/Structure/InterfaceSection.cs:68`,
`Access/Interface.cs:107-110`), and the live install is 16 (`Memoria.ini:329`).
Folklore derives `rowCount = round(bakedClipHeight / rowH)`
(`FolkloreUI.cs:1792-1794`) and faithfully honours it — every text budget and
"fits on one page" claim must survive the **whole settable range** (the accessor
floors at `Math.Max(1, …)`, the config default is 12, and this install runs 16),
and a playtest at one setting proves nothing about another. (b) The detail body does **not** scroll —
`Overflow.ShrinkContent` (`:1727`) means over-long text silently shrinks to
illegibility. The kit's existing budget (6 lines × 32 chars, help ≤135 chars,
`content/folklore.py:142-144`, lint-enforced `:424-432`) was measured against a
DIFFERENT surface (the key-item parchment popup) and is UNVERIFIED for this pane.
(c) This ships the custom engine — free for anything already forking fields
(which needs the s23-s33 gates anyway), a new tax on a novel-field-only mod.
(d) **No sidecar is carried by a campaign or journey deploy today**: `grep -i
folklore tools/deploy_campaign.py tools/deploy_journey.py` returns nothing, while
`tools/deploy_field.py:349-385` has it. That carry is unbudgeted work in every
design that proposes a mod-root registry, and it is the same failure class as the
New-Game override wipe.

---

### T3 — per-row state, counters, and the meter dashboard

**Player sees:** rows that carry state, not just names — `Cleyra 7/9`, grey text
for locked entries, missables in the stock warning colour with a hint in the
detail pane. Plus a second view: a **static** framed panel of 8 category meters
(icon, name, filling bar, cur/max), paged.

**Mechanism.** The counter column re-enables the Key-Item donor cell's second
caption/number children that folklore deactivated (`FolkloreUI.cs:1892-1893`) and
heads them with `GOScrollablePanel.CaptionPanel`'s `Name2`/`Info2` — **available
only when `childCount == 4`** (`Memoria/Scenes/GOScrollablePanel.cs:47-65`),
i.e. conditional on the donor cloned. Colour states via `FF9TextTool.White/Gray`
exactly as `AbilityUI.DisplaySADetail` does per row (`Global/AbilityUI.cs:1140-1160`).

**The meter dashboard's donor is `StatusUI.AbilityPanelList[i]`** — a framed
panel holding exactly 8 baked `AbilityItemHUD` rows (`Global/StatusUI.cs:409-413`),
each = child0 icon sprite + child1 name label + child2 `APBarHUD`
(`Assets/Sources/Scripts/UI/Common/APBarHUD.cs:6-19`: `UISlider`,
`ap_bar_progress`/`ap_bar_complete` foreground, cur/max labels, mastered star).
**It is static — exactly 8 rows per page, hardcoded.** More than 8 categories
means paging, not scrolling. Do not try to make it scroll; that is T5.

**Two mandatory passes that are easy to miss.** `GOSubPanel.ChangeDims`
(`Memoria/Scenes/GOSubPanel.cs:42-68`) resizes the cell ROOT widget, the
SnapDrag heights, the table columns and the clip region — **and nothing else**;
every reshaped cell needs an explicit child re-anchor + fontSize rescale
(`Global/ItemUI.cs:164-176` is the template). And anchors re-assert every frame,
so every repositioned clone needs `SetAnchor(null)` (`FolkloreUI.cs:1681-1682`).

**Blockers.** A second view inside one `UIScene` doubles the Show/Hide/Cancel and
`ButtonGroupState.ActiveGroup` handshake — the folklore record shows cursor/sound
state is where rounds get spent (the 2-frame `MuteActiveSound` settle at
`:287-320` exists purely to suppress one spurious beep). The AP-bar sprite names
are atlas-resident but their presence in whichever atlas the journal's panel
resolves against is UNVERIFIED offline; guard with `atlas.GetSprite(...) != null`
as `FolkloreUI.cs:1684-1686` already does. **The runtime cost is unmeasured** —
folklore's name-label-only list profiled 4 ms awake / 8-18 ms first frames; 8
slider+sprite+label rows is a different drawcall profile. Bracket the first
rendered frames; a synchronous stopwatch cannot see NGUI's real cost.

**And the honest structural point:** folklore's per-entry state is ONE boolean
over a registered set (`FolkloreRegistry.IsFolklore(id)` against
`rare_item_obtained`). A completion journal's per-row state is heterogeneous by
construction — bit/byte/Int24/UInt16 arithmetic, HashSet membership, save-JSON
module reads, and per §2 fact 2 a numerator the achievement array does not store.
**That resolver is net-new C# with no donor, it is where every row's correctness
lives, and it appears in none of the four designs' line counts.** The screen is a
copy; the journal is not.

---

### T4 — the mined chest atlas + missable verdicts

**Player sees:** the thing the ask actually pictures. *"Cleyra Trunk — 3/5
treasures, 2 PERMANENTLY MISSED"*. *"Stiltzkin, Burmecia — window closed; not
purchased."* A per-room checklist with permanent-miss verdicts.

**Mechanism, and only half of it is a read.** The verdict half is: a per-entry
`close_sc` threshold compared against ScenarioCounter. The atlas half is **not a
read at all** — it is a static authored map laid over an opaque popcount, mined
offline from ~674 real fields' `.eb`. The harness exists: `logic_map.py` (697
LOC) extracts per-routine dialogue, item/gil/shop/save-menu grants
(`ADD_ITEM_OP = 0x48` at `:36`), GLOB flag reads and writes, warps and battles;
`battle/locate.py` (577 LOC) is the working all-674-field census precedent,
version-gated and cached to `provision.cache_dir()` rather than committed;
`research/flag_census.py` decoded all 676 fields with 0 scan errors; room names
come from `reference/field-manifest.tsv` (817 rows → 389 rooms / 58 areas).

**Do not price this as "re-run the existing generator" — but the branch-walking
half now EXISTS.** `logic_map.Node` (`logic_map.py:73-88`) carries `says`,
`gives`, `flags_set`, `flags_read`, `warps`, `battles`, `branches`, `unresolved`
as **independent flat lists scoped to a whole routine** — a bag, not a
(grant, latch) tuple. Pairing them requires real control-flow analysis, which
`research/gen_flag_lore.py` never did.

**★ SUPERSEDED BY THE NARRATIVE-STATE ARC.** `ff9mapkit/ff9mapkit/eb/cfg.py` now
ships `FuncFlow` (basic blocks, dominators, if/else polarity, switch-case
`==`/`in`, compound-AND atoms, join points killing claims, loop-exit negation,
dead-code = no claim) and `FieldFlow` (arm/call-graph context propagation,
available-expressions fixpoint, and **kill/def analysis with bit/byte/word
aliasing** — the once-latch `if(bit==0){bit=1;…}` idiom was producing provably
false guards at 304 of 2,832 story sites before that fix). `research/dominance_census.py`
runs it over **818 fields / 34,867 funcs, 0 degraded, deterministic**. That is
the instrument this tier's generator needed and did not have, already built and
already adversarially reviewed. **Re-price T4's generator down accordingly — but
see the coverage ceiling below, which moves the estimate in the other direction.**

A computed AddItem operand is still diverted to `unresolved` (`logic_map.py:359-362`)
and `item_inert` grants are dropped (`:363`), so the item side keeps its
false-negative floor.

**Blockers, and they are the reason this tier is rated low.**

- **The denominator is unknown and the repo carries three conflicting figures.**
  The engine's ranges are bytes 896-960 and 966-975 (verified by reading
  `EventState.cs:62-70`). `research/CENSUS_DIGEST.md:103-111` clusters sum to
  **386** distinct bits — but its last row spans bytes **960-971**, which
  includes the unscored 961-965 and excludes 972-975, so 386 is not a count of
  scored bits. `research/STORY_FLAGS.md:100` says **327** distinct bits over
  896-975. The community breakdown (181 chests + 143 field items + 89 rewards +
  25 Chocograph chests + 5 bubbles + 3 cracks = 446 treasures / "477 points")
  does not self-reconcile — 413 + 66 = 479. And the engine blindly counts every
  set bit in range regardless of provenance, so any non-treasure flag parked
  there inflates the score. **"Chests N/446" is fabrication; "Treasure Hunter:
  287 pts, rank C" is a read.** Ship the rank.
- **Missability is derived, never observed, and the narrative-state arc has now
  MEASURED how derivable it is: not very.** Rung 0 of that arc predicted that
  CFG dominance would lift SC-window attribution past 55% of write sites. **The
  prediction was FALSIFIED at 36.2%** (direct dominance 18.3% → +armed context
  29.4% → +co-located SC advance 36.2%), and only **257 of 974 story bits get a
  hard SC window**. The reason is structural, not a tooling gap: ~90% of story
  sites live outside `Main_Init`, and **32% of story sites are once-flag-gated
  and interaction-driven rather than beat-gated**. Two consequences pull in
  opposite directions for a journal — a once-flag IS exactly the "did the player
  do this" latch a collectible row wants (good), but it carries no derivable
  *window*, so the missable column stays largely un-derivable (bad). A wrong
  threshold confidently tells a player they permanently missed something still
  obtainable. Still the worst failure mode, still a DATA risk.
- **A monotone "collected" latch is WRONG for ~76 bits.** The corpus census finds
  **94 bits explicitly cleared somewhere**, 85 of them set-then-clear, and the
  ground-truth pass ("Q2 MEASURED" §7.1) trims that to **~76 credible
  per-location toggles** after excluding 9 reused-dispatch bits. (The original
  example here — "Desert Palace sanctum band 3536-3542" — was REFUTED by that
  pass: those bits are clear-only, never machine-set; the real Desert Palace
  toggle region is 3552-3599.) Those need windows `[on, off)`, not a latch. A journal that renders "bit set =
  obtained forever" will show a collected item reverting to un-collected mid-game.
  This is a correctness bug the scoping pass did not have and it must be in the
  catalog schema from the start, not retrofitted.
- **The treasure question gets a real number from the same census:** **412 of
  1,110 written bits sit in Treasure-Hunter-scored bytes**, and TH membership is a
  **cost** signal, not a class signal — seeding those bits inflates the player's
  rank. That confirms §T4's "the engine blindly counts every set bit in range":
  ~37% of all script-written bits land in the scored region regardless of whether
  they represent treasure.
- **The worktree skip trap is live right here.** `provision.templates_present()`
  returns **False** in this worktree (measured this pass by running it), and
  `ff9mapkit/conftest.py:86-116` drops modules that do game-data I/O at import
  and converts data-absence into `pytest.skip`, on top of 276 further `skipif`
  markers. A 674-field census test written here would SKIP and the run would
  still be green. Run in the MAIN repo or extract templates first.
- **Some categories are unrepresentable at any tier and must be labelled NOT
  TRACKED, never silently omitted:** per-chest identity, the ~197-entry bestiary
  (`AchievementState.enemy_no` is a scalar; `modelKillCount` counts kills per
  battle MODEL and exists only in the modern save), per-recipe synthesis (only
  `synthesisCount`, `Global/ShopUI.cs:429-431`), the Nero family (a grep for
  "Nero" over the whole Assembly-CSharp returns nothing), 8 of the 9 friendly
  monsters (only the Yan blessing bit 1584 is engine-grounded), and step count.
- **"100%" is ill-defined in one save.** Mutually exclusive: the Festival of the
  Hunt's 3 winners (`EMinigame.cs:295-303`), the ATE pair that is exactly why
  the trophy needs 79 of 83 (`ATE80` Target = 79), the "not every reward in one
  playthrough" subset, Excalibur II vs a relaxed pace, Collector's Level exactly
  1700 (which glitches the rank label, so 1699 is the practical max), Yan
  strictly last, Pumice Pieces spent vs kept. Without an `exclusive_group` /
  `run_mode` column the totals are simply wrong and a full bar never fills —
  which reads as a bug.

---

### T5 — bars in the scrolling list, a scrolling detail body, per-entry art

**This is the tier the obvious plan puts first, and it is the most expensive one
on the page.** The correction that inverts the schedule:

**There is no bar-per-row donor in FF9.** A repo-wide grep for
`new AbilityItemHUD` returns exactly two construction contexts, both STATIC:
`Global/StatusUI.cs:412` (inside `for childIndex < 8`) and
`Global/EquipUI.cs:1284-1286` (three fixed slots). Every RECYCLING list cell in
the ability screen is barless — `DisplayAADetail` builds `ItemListDetailHUD`
(`Global/AbilityUI.cs:1047`) and `DisplaySADetail` builds
`ItemListDetailWithIconHUD` (`:1121`). The AP bar in the ability SCREEN lives in
the DETAIL pane via `AbilityInfoHUD`. And `FF9UIDataTool.DisplayAPBar`
(`Assets/Sources/Scripts/UI/Common/FF9UIDataTool.cs:239-261`) is **not a callable
API for arbitrary numbers** — its signature is
`(PLAYER, abilityId, isShowText, APBarHUD)` and it derives cur/max internally
from `ff9abil.FF9Abil_GetAp`. It is a readable template, not a function you call.

So a bar inside a `RecycleListPopulator` cell means grafting an `APBarHUD`
subtree into a cell prefab, re-anchoring five sub-widgets after every
`ChangeDims`, and binding it inside the recycle callback where cells are reused
across rows and stale slider values persist. **A scrolling detail body is worse**
— a second scroll compound in one scene re-opens the whole scroll-sum law set
(panel transform and clipOffset counter-slide; only their SUM is scroll-invariant,
`FolkloreUI.cs:1789-1800`) plus pointer-depth and scene-space limit-rect
resolution. That law set cost roughly 9 of s45's ~23 rounds to mint.

Against the project's own measured law — **the defect follows the authorship**
(12 of 13 playtest verdicts and 32 of 37 named defects landed on the round's
newest surface; 0 of 13 were predicted by a green gate) — T5 mints two new widget
classes in the exact subsystem where that law was measured. **Recommendation:
don't, unless the owner specifically wants it after seeing T3.**

---

## 4. The three cost centres, sized separately

### (a) Engine / UI

**Grounded, and the cheapest of the three.** Measured this pass by parsing the
patch bodies (`grep -c '^+' minus the file headers`):

| patch | added | removed | files |
|---|---|---|---|
| `s45-folklore-submenu` | **975** | 15 | 5 |
| `s46-folklore-render-rig` | **1407** | 6 | 1 |
| `s43-debug-menu-ux-tilde` | **399** | 215 | 2 |

(RECON and two designs quote s45 as "937 added". RECON's own per-file list sums
to **975** while its headline says 937 — an unexplained arithmetic error in the
source, not two measurements of different things. The diff size is 975/15.)

`FolkloreUI.cs` is 2197 lines → **1296 code / 812 comment-only / 89 blank**.
So a folklore-shaped journal screen is ~600-800 lines and a fully-featured one
~1,300-1,900, plus ~50-180 lines across `UIManager.cs` / `EventService.cs` /
`Assembly-CSharp.csproj`. **The LOC is not the cost — the ROUNDS are: s45 took
~23 in-game rounds and s46 ~9** (`studies/folklore-codex/SUBMENU.md:296-405`).
The NGUI law set eliminates the ~10 rounds of mechanism discovery, not the ~6-8
rounds of geometry and feel.

### (b) Catalog data authoring — **THE DOMINANT COST**

The four designs converge on "~80-85% of catalog rows are machine-seedable, only
names and lore are hand-written." **The repo's own two precedents measure the
opposite.**

**(i) The "fully machine-generated" catalog generates no prose.**
`ff9mapkit/ff9mapkit/data/region_catalog.toml` has **73** `[[arc]]` blocks
(measured; all four designs say ~90), and every one of its `note` values collapses
to about four string templates — 34 match the literal
`"… seed = the lowest id -- verify if it mis-lands"`. Compare the hand-curated
`data/reference_arcs.toml:24`: *"The opening: the Tantalus play, kidnapping
Garnet, the escape from Alexandria."* The generator emits a restatement of the
row's own key fields.

**(ii) The measured skeleton→meaning yield in this repo is 1.8%.**
`research/gen_flag_lore.py` (464 LOC) — the best generator this project has for
exactly this problem — produced `research/FLAG_LORE.md` (5,685 lines) covering
**937** candidate bits at confidence `{c: 391, b: 546, a: 0}`
(`FLAG_LORE.md:3-6`, which states outright it is "a CANDIDATE table for human
curation, not shipped names"). The curated survivors in `flags.py:311-420`
`STORY_REGIONS` are 35 entries, of which **17 are single-bit promotions**.
937 → 17.

**(iii) The prior experiment ran and the catalog is what didn't get finished.**
`[[folklore]]` shipped 100% of its mechanism — `content/folklore.py` 467 LOC,
`tests/test_folklore.py` 821 LOC, 2197 lines of C#, ~30 playtest rounds — and the
total authored content in the entire repository is **5 entries**, all in one demo
file (`grep -rn '^\[\[folklore\]\]' --include=*.toml .` → 5 hits, all
`studies/folklore-codex/p0-demo/`). Zero in `ff9mapkit/examples/`. Zero mentions
in `docs/` or `CHANGELOG.md`. **Mechanism 100%, catalog 2.9% of its own 175-slot
band.** Any plan whose thesis is "the data file is the durable asset" owes an
explanation of why folklore's wasn't.

Those 5 entries are also the CHEAP case — invented flavour fiction
(`folkp0.field.toml:42` says so), unfalsifiable by construction. A journal row
asserts a checkable FF9 fact with no offline oracle, against three length-linted
strings per entry.

**Derived authoring rate** (estimate, unverified — no hours-per-row figure exists
anywhere in this repo): **~15 min/row** where the fact comes from engine data
(key items, cards, chocographs, beaches, Stellazzio), **~30 min/row** where it
must be mined from `.eb` and arbitrated (treasure atoms, missable windows).
Assumed blend and divisor, stated once so the arithmetic is checkable: **~75%
engine-sourced / ~25% mined** at the observable tier shading to ~50/50 at the
full tier, and **7 h/day**.

| catalog | rows | authoring |
|---|---|---|
| observable set (T3) | ~300 | ≈ 80 h ≈ **11-13 days** (estimate, unverified) |
| story + chests + key items (T4 low) | ~600 | ≈ 150-300 h ≈ **21-43 days** (estimate, unverified) |
| true 100% (T4 high) | ~1,770 | ≈ 440-660 h ≈ **63-94 days** (estimate, unverified) + a 60-100 h owner playthrough |

**The ~1,770 row is quoted for scale only and this document does not endorse its
components.** It sums ~30 per-category counts whose largest single term is **446
treasures** — the figure §T4 blocker 1 declares unusable (it does not
self-reconcile, 413+66=479≠477, and it disagrees with both of the repo's own
census numbers) — and it also embeds "93 achievement keys", corrected to **87** in
§6.3. Treat 1,770 as an upper-bound sketch with at least two known-bad terms, not
a target. The defensible tiers are ~300 (observable) and ~600 (story + chests +
key items); anything above that is gated on §7 Q2.

**Shipping multiplies but authoring does not:** the kit writes 7 language dirs
(`config.py:34`) with identical bodies for non-localized content. If the journal
is ever genuinely localized, every figure above ×7.

### (c) Observability research — "which bit flips for entry N"

Sized between (a) and (b), and **serial on one person.** Two parts:

- **Machine — got substantially cheaper.** The branch-walking join no longer has
  to be written: `eb/cfg.py` + `research/dominance_census.py` already run a sound,
  kill-aware, deterministic dominance pass over 818 fields / 34,867 funcs. What
  that census CANNOT do is now also measured, which is the more important half:
  **36.2% site coverage, 257 of 974 story bits windowed.** The instrument is
  built; the ceiling is the finding.
- **Human — unchanged, and now with a measured hole.** The only oracle that
  promotes a generated row is a real playthrough with checkpointed saves, diffed
  with `flags.diff_reports`. The narrative-state arc's calibration corpus is **19
  populated saves with NOTHING after SC 7200** — discs 3 and 4 have **zero ground
  truth**. Since the back half of the game is where most missables and most
  one-of-a-kind collectibles live, a completion journal is disproportionately
  exposed to exactly the region with no saves to validate against. **This is a
  concrete ask for the owner: disc-3/4 checkpointed saves are worth more to this
  feature than any amount of engineering.**

**Which dominates: (b), by a wide margin, and (c) is the schedule risk.** (a) is
a copy of a measured file. The catalog is a writing project with an engineering
prerequisite, and every design on the table priced it as an engineering project
with a writing footnote.

---

## 5. The walkthrough as a source

The referenced guide is bover_87's *Final Fantasy IX Walkthrough & Guide*,
GameFAQs FAQ id 71891.

**Access.** Direct fetch FAILED on every prescribed route: WebFetch → HTTP 403 on
both the section URL and the `/faq` variant; raw curl with a Chrome UA → 403;
`r.jina.ai` proxy → 403; the browser MCP extension was not connected. Everything
below was recovered through the **Wayback Machine CDX API** (86 of ~89 named
sections, snapshots 2020-2026). **The live guide (v2.01) was never read by
anyone in this pass.** Three sections were never fetched and are unidentified.

**What it is structurally good for.** It is far more machine-parseable than a
typical FAQ: stable section slugs, 265 room-level `<h4>/<h5>` anchors across the
41 walkthrough pages, a repeating `<table class="ffaq">` per room whose row
headers are literally `Items` / `Enemies` (112 Items rows, 92 Enemies rows), 1,267
hyperlinked item pickups and 375 enemy references resolving into a canonical
`items#<anchor>` / `enemy-list#<anchor>` vocabulary, 41 boss stat blocks on a
fixed 12-column schema, and — the apparently useful bit — **missability encoded as
inline colour, not prose**: `color:#ff0000` = missable (1,791 spans guide-wide),
`color:#ff6600` = limited-quantity-late (1,199). Total body scale **≥ ~125,000
words** (a lower bound: computed over 86 of ~89 sections).

**Two findings that cut the colour convention's value sharply.** (a) Only **39
red and 64 orange** spans fall inside the 41 *walkthrough* pages — the rest live
in the Items/Shops **reference tables**. The colour marking is a property of the
reference apparatus, not of the room-by-room narrative a journal would walk. (b)
The guide's own dedicated "Missable Item Walkthrough" section is ~850 words, 38
list items, **zero headings, zero tables, zero colour spans** — i.e. the one
section aimed squarely at this problem is the least parseable thing in the guide.
Caveat: nobody audited whether `#ff0000`/`#ff6600` are used *only* for missable
semantics, so even the 39/64 may not all be missability marks.

**The one join the game can make is the ITEM NAME.** The guide's item anchors are
canonical English names and the kit ships a 256-entry id↔name table baked from
Memoria's open-source `RegularItem` enum (`ff9mapkit/ff9mapkit/_itemdb.py:11-12`).
Everything else in the guide is keyed to **human narrative position** — named
room, disc, story beat. **No field id, flag index or scenario counter appears
anywhere in its markup.** So it cannot supply the chest→bit map; it can only
cross-check one.

**What it cannot be used for: shipping.** Its own Legal Stuff section reads *"This
guide may be not be reproduced under any circumstances except for personal,
private use. It may not be placed on any web site or otherwise distributed
publicly without advance written permission,"* and its Copyright Notice reserves
all rights to bover_87 (2015-2022). Only the uncopyrightable facts may be
re-derived and re-expressed in original wording.

**Two provenance gaps nobody has closed, and they need an owner decision BEFORE a
generator is written.**

1. **The repo has no policy for third-party sources at all.**
   `ff9mapkit/docs/PROVENANCE.md` governs exactly two things — Square-Enix binary
   bytes, and Square-Enix game TEXT (`:75-96`, the FLAG_LORE ≤110-char cap and the
   save-moogle line, "the repository's only committed game-text exceptions").
   Grepping it for jegged / fandom / gamefaqs returns nothing. Yet the great
   majority of the per-category counts a journal would use (446 treasures, 9
   friendly monsters, 4 Moonstones, 24 Blue Magic, the missable-window map, the
   PONR-by-disc map) trace to **jegged.com and Fandom**, whose licences nobody
   checked. GameFAQs is simply the only source whose licence was examined —
   because it was the only one actually read.
2. **"Missable" is a selection, not a fact.** The colour convention is a judgement
   the author applied to a corpus he assembled and graded in two tiers. Copying
   raw item locations is a facts case; copying the SET of things he decided are
   missable imports his selection and arrangement — the protectable layer of a
   compilation — and that is precisely the column a journal most wants.

Note also that a shipped `journal_catalog.toml` is **package-data by
construction** (`ff9mapkit/pyproject.toml:85-93` is a literal 5-entry array,
deliberately not a glob), i.e. a distribution posture FLAG_LORE explicitly does
not have. `PROVENANCE.md:100-102` is already stale about that array — it claims
package-data is restricted to `data/provenance/*` while `:93` also ships
`reference_arcs.toml` and `region_catalog.toml`.

**Recommended posture:** treat guide-derived facts as a CROSS-CHECK column with
its own provenance tag, never as a text source, and get the owner's decision on
third-party compilations before the generator is written rather than after.

---

## 6. What was refuted

Claims that did NOT survive verification. Each is written here so nobody
re-litigates it.

1. **"`AbilityScene.ActiveAbilityListPanel`'s cell is a baked shipping donor for
   a row with a progress bar and an X/Y counter."** FALSE. `new AbilityItemHUD`
   appears only at `StatusUI.cs:412` (static, 8 rows) and
   `EquipUI.cs:1284-1286` (3 fixed). Scrolling lists use `ItemListDetailHUD`
   (`AbilityUI.cs:1047`) and `ItemListDetailWithIconHUD` (`:1121`) — neither has
   a bar. **This inverts the cost ordering:** a paged static meter dashboard is a
   verbatim clone; a bar in a recycling cell is net-new surface.
2. **"`FF9UIDataTool.DisplayAPBar` is the populate idiom."** It takes
   `(PLAYER, abilityId, isShowText, APBarHUD)` and derives cur/max internally
   (`FF9UIDataTool.cs:239-261`). A readable template, not a callable API.
3. **"The 93-key achievement table is Square's own definition of completion."**
   The enum has **88 members: 87 real keys (ordinals 0-86) plus the
   `AchievementKeyCount` sentinel = 87** (`Assets/SiliconSocial/AcheivementKey.cs:5-94`,
   re-counted this pass). Two of the 87 are system keys held outside the per-save
   array (`AchievementState.cs:77-80`), leaving **85** normal keys. RECON said 93
   and 94 in two places; all four designs inherited it.
4. **"`EvtReservedArray` gives a checklist with per-row state AND denominator —
   'Stiltzkin 6/8', 'ATEs 61/79'."** The 2 bits store an
   `AchievementStatusesEnum` status. `totalProgress` is a live argument, computed
   and discarded (`AchievementManager.cs:79-88`). Three further holes:
   `ReportAchievement` **hard-returns for `AllAbility` and `CardWinAll`**
   (`:74-75`, verified) so two headline rows have no state at all;
   `UnlockComplete` is written only downstream of
   `if (!Social.IsSocialPlatformAuthenticated()) return;` (`:113-114`), so on an
   offline install every earned key sits at `ReadyToUnlock` forever — **a journal
   must test `!= NotUnlockYet`, never `== UnlockComplete`, or a 100% save renders
   as 0%**; and `IsFastTrophyMode` rewrites `totalProgress` first.
5. **"`Null.UInt16[5]` reads TREASURE_HUNTER_POINTS."** It reads **zero,
   silently**. `EvaluateValueExpression`'s `VariableSource.Null` arm switches on
   `varType` with only `Any` / `Vector` / `VectorSize` / `Dictionary`, falling
   through to 0 for everything else (`Global/EBin.cs:1621-1645`). `Any == 0 ==
   SBit`, so the token is `Null.SBit[5]` → `C3 05`.
6. **"Popcount categories are computed with a bit loop over
   `Global.Bit[856+i]`."** No computed bit index exists for `gEventGlobal`;
   `expr_varSpec` reads immediates (`EBin.cs:464-478`). 21 beaches = 21 static
   tokens.
7. **"Chocographs read as `Global.Int24[184]`, and 0xFFFFFF fits a `B_CONST4`
   compare."** The engine's Int24 read **sign-extends** —
   `buffer[ofs] | buffer[ofs+1]<<8 | ((SByte)buffer[ofs+2] << 16)`
   (`EBin.cs:1858-1861`) — so a completed field reads **−1**, and any compare
   against 16777215 fails. The engine masks on the next line
   (`EMinigame.cs:434-436`). The masking step was absent from every design.
8. **"ScenarioCounter is monotonic, so missability is a pure read."** Refuted,
   but the *replacement* is now itself unsettled: `CENSUS_DIGEST.md:15` says
   seven fields decrement it; the narrative-state 818-field probe says 889
   absolute writes vs 2 relative. `EventState.cs:16-22` is unguarded either way,
   so a `close_sc` threshold still needs proving rather than looking up — but see
   §1: **this study did not settle the count, and neither has anyone else yet.**
9. **"`SCENARIO_MILESTONES` gives 52 story beats."** 52 keys, **39 distinct
   names** (measured). A naive render lists Alexandria Castle five times, and a
   "34 / 52 beats" progress row has 13 duplicate denominators. It is an AREA
   table, which is what `flags.py:423-430` says it is — and it already superseded
   a 43-anchor predecessor that mislabelled five beats.
10. **"~80-85% of catalog rows are machine-seedable."** True of the SCHEMA, false
    of the row. See §4b: the generated catalog's prose is a four-template
    restatement, and the measured skeleton→meaning promotion rate is 17/937.
11. **"`logic_map` emits (grant, latch) tuples — that tuple IS a treasure row."**
    `Node` carries independent flat lists per routine with no association,
    ordering, or branch attribution (`logic_map.py:73-88`). The chest join is new
    work, not a re-run.
12. **"~386 distinct bits in the 1-point band vs the community's 413 — a ~6%
    disagreement."** 386 is arithmetically correct as a sum of the digest rows but
    its last row spans bytes 960-971, straddling the engine's scored ranges;
    `research/STORY_FLAGS.md:100` gives 327 for an overlapping definition. Two
    repo numbers, neither aligned to what the engine counts. The disagreement is
    **unquantified**, not 6%.
13. **"Sidecar survival across a campaign deploy is UNVERIFIED."** Now verified,
    against the designs: `grep -i folklore tools/deploy_campaign.py
    tools/deploy_journey.py` returns **nothing**, while `deploy_field.py:349-385`
    has the carry. A mod-root registry is definitively NOT carried today.
14. **"The chest-band mislabel survives in two places."** It was three places
    plus a missing chocograph byte-range label — **all fixed on `master` (s78),
    owner-confirmed in-game**, see §T0. And one sub-finding of this study was
    itself wrong: the `bit == 184 || bit == 191` test is correct as written (byte
    23's bit-addressed handshake), not a bit/byte confusion.
15. **"A journal is the same screen with a different data source, so the second
    one is a copy."** True of presentation, false of data. Folklore's per-entry
    state is one boolean over a registered set; a journal's is heterogeneous and
    needs a net-new resolver with no donor (§T3).
16. **"s45 is 937 added lines / 980 added lines."** 975 added / 15 removed across
    5 files (measured). s46 = 1407/6. s43 = 399/215. Minor, but this is the single
    measured anchor under every C# effort figure and nobody re-derived it.

---

## 7. What to prototype first, and the open questions

### 7.1 The rung-0 probe — one bench field, one playtest round

**The riskiest cheap assumption is that the DLL-free read paths work at all.**
**TWO** mechanisms carry most of T0/T1b/T3 and have never executed:
`Null.SBit[5]` (memoria_variable, zero shipping precedent anywhere) and
`flex(16,3)` `PLAYER_ABILITY_LEARNT` (no kit emitter). A third unexercised idiom,
the `[TBLE=]` state bank driven by a computed slot, rides along.

**CORRECTION — the expression-valued `SetTextVariable` is NOT unexercised and NOT
a kit gap.** The scoping pass called it a third never-run mechanism; that was
wrong. The kit **already emits it at three in-game-proven call sites** —
`content/behavior.py:2640-2643` (the HUD live pass), `content/numinput.py:413`,
`content/mognet.py:292` — via `opcodes.encode(0x66, slot, expr, arg_flags=0b10)`.
Only the *named helper* `set_text_variable` (`eb/opcodes.py:466`) was
immediate-only. So publishing a computed counter was never blocked; what was
missing was a way to *author* one declaratively.

**And the operand ceiling is not Int32 — it is 26-bit signed (±33,554,431).**
Every COMPUTED intermediate goes through `expr_Push_v0_Int24`
(`Global/EBin.cs:1270-1274`), which ORs the Int26 class tag into bits 26-28
**without masking**; only a bare terminal var token reaches `getv()` unmasked. So
an overflow does not truncate — it **corrupts the `VariableSource` field**, and
the value is then read back as a different kind of variable entirely. This is the
same 26-bit CalcStack ceiling that killed Path B's dynamic region test. Any
journal row that multiplies or sums must be checked against it, and
`play time in seconds` (capped at 2,160,001) must be divided *inside* the
expression.

**Build one bench field in the scratch band (30000-32767) that displays, in one
window:** Treasure-Hunter points via `Null.SBit[5]`, published through the
**expression** form of `SetTextVariable`; ScenarioCounter via `Global.UInt16[0]`;
the chocograph Int24 both raw and masked (to observe the sign-extension in the
wild); one key item via `const(256+n) B_HAVE_ITEM` (which also exercises the
`behavior.py:1740` bound lift from §2†); one ability via `flex(16,3)`; and one
`[TEXT=bank,slot]` glyph driven from a computed slot.

**It falsifies cheaply.** If the two unexercised reads work, T0/T1b/T2/T3 all
stand and the ladder is a scheduling question. If either returns 0, the whole
DLL-free half of the ladder collapses onto the C# path and the plan changes on
day one instead of after a catalog exists. Cost: one field, one round.

### ★ RUNG-0 RESULT — deployed 30800, owner-playtested, 3 saves

**The DLL-free half of the ladder STANDS.** Measured in-game against New Game
(all zero, correct), SLOT1FILE1 and SLOT1FILE2:

| row | mechanism | New Game | FILE1 | FILE2 | verdict |
|---|---|---|---|---|---|
| TH POINTS | `Null.SBit[5]` | 0 | 178 | 215 | **★ CONFIRMED** |
| SCENARIO | `Global.UInt16[0]` | 0 | 6000 | 7200 | ★ control holds |
| CHOCO RAW / MASKED | `Global.Int24[187]` ± mask | 0 | 1727 | 1727 | ★ reads; mask **not exercised** |
| KEY ITEM 0 | `const(256) B_HAVE_ITEM` | 0 | 1 | 1 | ★ CONFIRMED |
| ZIDANE AA:6 | `flex(16,3)` | 0 | 0 | 0 | **INCONCLUSIVE** |
| CLAMPED ROW | `B_DIV`+`B_GE`+`B_MULT` | 0 | 6 | 7 | ★ CONFIRMED |

**1. `Null.SBit[5]` works.** The memoria_variable read with zero shipping
precedent anywhere returns real, per-save Treasure-Hunter points. This was the
single largest unknown in the study and it is now closed.

**2. Two-instrument cross-validation — the strongest evidence in this document.**
The in-game `.eb` expression and the offline Python decoder (`journal report`,
T1) were run against the same save container and agree EXACTLY:
FILE1 → SC 6000 / TH 178 / choco 1727, offline → SC 6000 / TH 178 / **9**/24 found;
FILE2 → SC 7200 / TH 215 / choco 1727, offline → SC 7200 / TH 215 / 9/24 found.
`popcount(1727) = 9`. Two independent implementations over two different access
paths (live engine heap vs AES-decrypted save block) landing on the same three
numbers is a much stronger result than either alone.

**3. Expression arithmetic composes.** `B_DIV` / `B_GE` / `B_MULT` evaluate
correctly inside an expression-valued `SetTextVariable`, and the doubled-value
clamp idiom produces the right answer (SC/1000 → 6 and 7). The auto-wrap the
compiler now emits is therefore emitting a shape that demonstrably works.

**4. `flex(16,3)` is NOT confirmed, and the engine has a silent-zero path.**
`PLAYER_ABILITY_LEARNT(charIdx, abilityId, alsoCheckEquip)` (`EBin.cs:421-435`)
`break`s **without assigning `_v0`** when the character is null, has no AP, or
when `FF9Abil_GetIndex` does not find that ability id in the character's list.
So `0` cannot be distinguished from "the read fell through". It could not be
resolved offline either: both tested saves are `main (vanilla)` with no Memoria
extra, so the ability store is genuinely absent — the T1 reader correctly reports
`unavailable` rather than 0, which independently validates the Finding-5 fix on
real data. **A follow-up probe must read an ability the character has certainly
mastered, plus a deliberate known-bad index as a control.**

**5. The Int24 sign-extension bites ONLY at the 24th chocograph — and that is
this feature's target state.** Computed exactly: 23 found reads 8,388,607; **24
found reads −1**. At 9 found the mask is a true no-op, which is why RAW and
MASKED matched and why this row could not fire. So the hazard is invisible at
every state EXCEPT 24/24 completion — meaning a completion journal is precisely
the feature that reaches it, and it can never be caught by testing on a partial
save. **Always mask; never rely on a playtest to reveal this one.**

### ★ RUNG-0b RESULT — the flex lane is CONFIRMED, and every zero is explained

Re-probed 30800 with a decomposition matrix instead of seven independent reads,
because `_v0 = 0` is set *before* the switch (`EBin.cs:360`) and so a fallthrough
is byte-identical to a real zero — no value-inspection trick can separate them.

| row | FILE1 (SC 6000) | FILE2 (SC 7200) | reading |
|---|---|---|---|
| ZIDANE LV `flex(13,1)` | **16** | **22** | ★ **the flex lane WORKS** |
| BADCHR LV `flex(13,1)` arg 99 | 0 | 0 | ★ negative control fires |
| ACT6 TO ID `flex(6,1)` | 6 | 6 | ★ pure conversion works |
| PARTY SLOT0 `flex(10,1)` | 0 | 0 | correct — Zidane IS old-index 0 |
| AA6 NOEQ / EQ `flex(16,3)` | 0 / 0 | 0 / 0 | correct — see below |

**`PLAYER_LEVEL` returns 16 and 22 and TRACKS the save.** It takes the identical
`GetPlayer(CharacterOldIndexToID(args[0]))` path `PLAYER_ABILITY_LEARNT` uses, so
the whole lane — 0xD3 emission, commandId, argCount, left-to-right arg push,
character resolve — is proven. The same call with index 99 returns 0, so the
null-player fallthrough is real and observable. **Both polarities of one engine
line, in one round.**

**And the original ambiguity had a mundane cause: ability id 6 is `Full-Life`.**
`abilities.name_of(6)` = Full-Life (an AA), and `abilities.pool_for_preset(0)`
shows Zidane's 48-ability pool **does not contain it** — it is White Magic.
So `FF9Abil_GetIndex(Zidane, 6) < 0` → `break` → 0, every time, on every save.
Rung 0's probe had baked the literal `6` arbitrarily ("no resolver in a
falsification path"), and it happened to pick a spell the character structurally
cannot learn. **The read was never broken; the question was malformed.**

**Residual, stated rather than glossed:** we proved the lane works and that the
break path yields 0, but we have **not** observed `PLAYER_ABILITY_LEARNT`
returning **1**. That arm is a one-line comparison and the lane around it is
confirmed, so this does not warrant another round — but any journal row built on
it must pick an ability **in that character's pool**, which is checkable offline
via `abilities.pool_for_preset()`. A row that silently asks for an out-of-pool
ability reads 0 forever and looks like un-collected progress.

### ★ T1b — BUILT, and the five-round bug was TURBO-DIALOG, not the mod

The dashboard ships 7 pages over the same 48-row catalog as the offline report
(31 rows carry an `.eb` expression, 17 declare a reason, a row with neither or
both fails lint). Owner-confirmed in-game: the selector works, pages open, and
the windows hold.

**They did not hold for five rounds, and none of it was the mod.**
`Memoria.ini [Control] TurboDialog = 1` (the DEFAULT) plus the `TurboKey` latch
makes `ShouldTurboDialog` (`UIKeyTrigger.cs:974-991`) return true **with no key
pressed**, so `UIKeyTrigger.cs:834-837` broadcasts `OnKeyConfirm` to every open
window every frame and any window without `FlagButtonInh` closes the moment it
finishes animating. **F9 toggles it, it survives field reloads for the whole
session, and nothing on screen says so.**

**The methodological lesson, which cost more than the bug.** Four candidate fixes
were shipped one per playtest — instant selector (wrong, restored), `[IMME]` on
replies (a real defect, real gate, not this), window-id reuse (no change),
branch-vs-switch (not applicable). The round that actually moved was the one that
shipped a **control** instead of a fix: a plain NPC window on the same field,
same window id, no selector. It closed too, which eliminated the entire choice
lane in one interaction.

**And the earlier "control" was invalid** — bench 30800 carries `[NFOC]`, which
sets `FlagButtonInh` and makes a window *structurally immune* to this exact
mechanism. "30800 stayed open" was evidence of nothing. A `[NFOC]`/`[TIME]`
window can never be a control for a dismissal bug.

**Design consequence for any tier above T1b:** a blocking `WindowSync` info page
**cannot be made turbo-proof from TOML**. The only immunity flags (`[NFOC]`,
`[TIME=n]`) also block the player's own confirm and hang the script waiting for a
dismissal that never comes. A page that must survive a player's turbo setting
needs the async shape — `WindowAsync` + `[NFOC]` + an explicit input poll. **This
is a real product question, not a bench quirk: turbo is on by default, so a
shipped journal would flash past for anyone who ever pressed F9.**

**Cosmetic, and a real T1b datum:** the header word-wrapped
(`=== COMPLETION PROBE / RUNG` / `0 ====`). The window's real character budget is
narrower than the authored line. T1b's page layout must be measured against the
live window, not assumed — this is the same class as §T2 blocker (b).

Two guards while building it: `ETb.GetStringFromTable` bounds the SLOT and the
UPPER row index but has **no lower bound** on `tableIndex = gMesValue[index]`
(`ETb.cs:270-283`) — a negative published value indexes a negative array element,
so a clamp is required. **The kit now emits it for you**: `compile()` wraps every
slot a `[TEXT=…]` tag reads in `E E const(0) B_GE B_MULT`
(`behavior.hud_row_index_clamp`), so an unclamped publish is unrepresentable
rather than merely refused — and `eb/exprsem.py` classifies every `op_binary`
operator's arity + side effects, so a hud expression that underflows the
CalcStack or writes save state fails at build. And re-check the live
`DictionaryPatch.txt` before deploying, because ~18 concurrent worktrees share
one install and the registrations move.

### ★ Q2 + Q2b + THE TOGGLE CENSUS — MEASURED (the full-fidelity gate numbers)

Six-agent adversarial pass over all 818 fields (not a 20-field slice — the full
corpus cost the same 2 minutes). Instruments: `research/treasure_join.py` +
`wf-q2-artifacts/` (the fold/indirect/rejoin scripts the verifiers wrote);
regenerable JSONs beside them, gitignored.

**Q2 ANSWER: the chest atlas IS generator-grade — but not at the number the raw
script printed, and the honest unit is the REWARD EVENT, not the grant site.**

- The script's own headline (2,343 grant sites, 70.5% single-latch) **measures
  dead code**. FF9's compiler emits a 4-arm reward macro (clamped-gil / item /
  card / literal-gil) and folds the selector to a literal; `FieldFlow` does not
  constant-fold, so **1,200 of 2,343 sites (51.2%) are statically unreachable
  template arms — and they are 100% latch/latch-write by construction** (dead
  arms sit inside the once-guard). Live-site single-latch is 39.8%. Neither
  number is the answer.
- **The honest unit: grouping by (field, latch-bit) gives 400 direct reward
  events over 341 distinct latch bits; 344 (86%) have exactly one live grant
  site** — a clean item-id + latch-bit pair a generator can emit. Calibrated:
  two hand-disassembled latches byte-confirmed (f706 Elixir/7687, f301 Ice
  Cavern Tent/7271; Ice Cavern's 8 chests are the contiguous run 7264-7271).
- **The `unresolved` class is one missing INTER-PROCEDURAL join, not unminable
  treasure.** One shared dispatcher (caller: `Byte[226]=Bit[N]`,
  `Int16[224]=<literal reward code>`, `RunScriptSync(2,uid,12|13)`, commit
  `Bit[N]=Byte[226]`) absorbs 286 of 298 unresolved + 140 of 294 bare rows.
  **204 call sites across 120 fields carry LITERAL codes** (85 item / 14 card /
  105 gil) — all machine-derivable at the CALLER. Reward-code encoding decoded
  and engine-confirmed: 0-255 item, 256-511 key item, 512-611 card, ≥1000 gil
  (amount = code−1000) — which is why dead literal-gil arms read as ~16.7M gil
  (`item_id − 1000`): **986 of 2,343 rows are "gil" and almost none are gil.**
- **Derivable total ≈ 400 direct + ~204 indirect ≈ 600 rewards over ~500 latch
  bits.** The residue after the upgrades is mostly latch-less BY DESIGN and
  correctly excluded from a chest atlas: Chocobo H&C dig payouts (table-driven),
  Stellazzio turn-ins (SC-windowed), story key items latched by SC/visit, and
  the `B_HAVE_ITEM(id)==0`-guarded key items — the inventory IS the latch, and
  the journal already reads inventory.
- **Verifier refutations the v2 generator MUST fix** (8/10 + 8/10 samples
  confirmed; the refutations are structural): **(F4)** an unguarded grant can
  false-pair to a NEIGHBORING chest's bit when `innermost_guard_block` walks
  out (proven at f600); **(F5)** one reward's rows can split across two bits
  (f2803, f2259, f764); **(F6)** **48 of 332 live strong latch bits (14.5%) are
  story gates, not treasure** — worst case bit 3818, a Gizamaluke CATCH-UP flag
  that Main_Init mass-sets when SC≥3740: a journal reading it as "collected" is
  a guaranteed false positive. The mass-set-under-SC idiom is itself derivable
  → the generator needs a catch-up-set filter; **(F7)** 7 live latch bits carry
  more than one item id. Also: the write side must accept the
  `Bit[N] = <variable>` commit form (135 corpus-wide), the same-function
  fallback must actually be implemented (docstring promised, code didn't), and
  the atlas must KEY ON THE LATCH BIT, not the field id — disc-variant fields
  (911/1911 Treno) carry identical bits and double-count.
- **TREASURE HUNTER RANK IS NOT A COMPLETION METRIC** (engine-verified,
  EventState.cs:53-72): bytes 961-965 — bits 7688-7727 — are NOT scored yet
  hold **33 real chest latches** (Cleyra, Burmecia/Vault, Mountain Path, Fossil
  Roo, Oeilvert, Alexandria/Steeple, Bran Bal); and the 2-pt chocograph band
  1456-1495 receives ZERO field-script writes (written by the chocograph
  layer, not `.eb`). The journal's completeness bar must count latch bits; the
  rank stays display-only.

**Q2b ANSWER: ZERO ScenarioCounter relative writes exist.** 889 absolute
literal SC writes across 818 fields, 0 relative/computed — measured two
independent ways (CFG-reachable and raw linear; `research/sc_relative_scan.py`),
agreeing exactly. Both prior figures ("7 fields", "2 sites") were regex
artifacts of `flag_census.py`'s cruder scanner (3 flagged fields re-examined by
hand: no relative SC write in any). **One whole non-derivability class for the
missable column is gone** — a `SC >= close_sc ⇒ missed` rule can never be
invalidated by a relative delta. The remaining open half is absolute-value
ORDERING across branching paths (§7.2 Q2c's saves are the oracle for that).

**THE TOGGLE CENSUS: PLAN.md's 94/85 reproduces EXACTLY** (`research/
set_clear_census.py`), and the strict init-zeroing contamination is ZERO. But 9
of the 85 are reused compiled dispatch/housekeeping (184, 189, 197-199, 808,
2102-2103, 2611, 2650, 3612) — exclude them; **~76 narrow per-location bits are
the credible `[on,off)` window population** for the schema. **One of this
study's own worked examples is REFUTED: the "Desert Palace sanctum band
3536-3542" is NOT a set-then-clear toggle** — those 7 bits are cleared once
each and never machine-set anywhere (read-only guards over native party state);
the REAL Desert Palace toggle content is the 26-bit region 3552-3599.

**THE TURBO-PROOF PAGE: the believed shape was half a defect mint.**
`ShouldTurboDialog` has TWO arms (UIKeyTrigger.cs:974-991). Arm A (:981-982) is
the known broadcast; **arm B (:984-988) fires exactly when every open window is
dismiss-inhibited AND any has Auto/Transparent style AND the script armed
`B_KEYON` — and it SYNTHESIZES a Confirm into the script's own input stream.**
So "`[NFOC]` + poll" alone reproduces the bug through a second mechanism. The
proven shape (assembled + disassembled offline, 32 bytes/page): **`WindowAsync`
with flags 0** (Plain style — structurally outside arm B's predicate) **+
`[NTUR][NFOC]` + a `B_KEYON(0xB0000)` poll + `Wait(8)` debounce + `CloseWindow`
+ `Wait(4)`**, values published before the open so AutomaticSize bakes real
widths. **CORRECTED COST: +26 bytes per page, not the +27 this design costed**
— the 32-byte block replaces a **6**-byte `WindowSync`, not a 5-byte one (every
opcode ≥ 0x10 with operands carries an argFlag byte, `eb/opcodes.encode:57-58`);
measured on the built 30801 artifact, 4693 → 4719. The shape is STOCK-COMMON —
2,034 poll-adjacent-async sites across 115 fields — so this is not a shape stock
never builds. Kit gaps to close while building it (**all now CLOSED** — see
`ff9mapkit/CHANGELOG.md` and SURVEY.md §7a-bis-2):
`want_no_turbo` (content/text.py:494 post-fix; was :399-408) is **backwards** for
inhibited windows (suppresses `[NTUR]` exactly where arm B needs it);
`hold = true` on a SYNC reply emits `[TIME=-1]` on a `WindowSync` — an
unconditional softlock nothing lints; no `[NFOC]` authoring key; no polled-page
concept; three private button-mask tables and no style↔turbo law. Cross-lane
exposure (recorded, out of this arc's scope): `[[qte]]`, `[[behavior.hud]]`,
and numinput all open Auto/Transparent inhibited windows while polling — inside
arm B's predicate — so a latched F9 can resolve a QTE with no press.

### ★ THE BUILD ROUND — v2.2 atlas + the turbo-proof story page (unplaytested)

Two build lanes, each adversarially verified twice; every verifier defect closed
and re-proven. **The defect followed the authorship all four times** — every
fresh defect landed on the round's newest surface (the weak-class promotion, the
tag policy), never on the mechanism.

- **`treasure_join` v2.2 — 410 reward events over 410 latch bits, 15/15 gates,
  each gate broken once on purpose.** The v2.1→v2.2 delta, all from the
  re-verify: `post_dom` now tells the truth about exit-less functions (14.1% of
  the corpus; the label is `indeterminate-no-exit`, never a phantom "sibling
  arm"); the shared-writer rule is a JOIN rule for every class (a synthetic
  in-process gate breaks it each run) — and it mirrors the corpus gate EXACTLY:
  the weak-row census's `written-by-N-rooms` heuristic briefly applied to
  strong rows collapsed the atlas 410→333 by killing legitimate multi-room
  chests (Cleyra Sandpit/Inn). Weak-class rows promote only through the
  writer/clearer census (23 rows → 11 promote / 11 refuse, every clause born
  from a proven row). The clear-side census exists (94 bits cleared live, 29 by
  a Main_Init; f706 zeroes three of its own chest bits and the events say so).
- **The turbo-proof story page — SHIP verdict, byte-exact, pages 1-6 the
  in-field control.** `content/event.polled_window()` (refuses arm-B styles and
  bad masks at the emitter), `want_no_turbo` repaired with proof the reorder
  only ADDS `[NTUR]`, the sync-hold/no-focus softlock refused on EVERY
  dialogue-bearing lane (not just `[[choice]]`), `polled` refused outside its
  two wired lanes, the `[WDTH]` forbidden-tag arm made fireable, and a
  non-verbatim `[[prop]] dialogue` now refuses as NOT-WIRED (it silently
  dropped before — the sweep's softlock refusal there was false). 401 tests in
  the domain+adjacent set, zero skips (this worktree currently HAS templates).
- **Cost:** +26 bytes/page (measured; the design's +27 forgot WindowSync's
  argFlag byte).

**NEXT = the 30801 playtest**: rank letter + hunt winner (round 6) AND the
polled story page (A/B vs the six sync pages). Every observation must state the
F9 state.

### 7.2 The other open questions, in the order they gate work

*(The pass opened with "does `save.py` decrypt a real slot?" — **ANSWERED, yes**,
verified this pass; see §T1's blockers for the narrower gap that replaces it.)*

1. **What does a "journal" actually mean here?** A completion TRACKER (this
   document's assumption) and an active-objective quest LOG have different engine
   surfaces and different catalogs. The ladder is stable under the first reading
   and partly wrong under the second. This is the cheapest question to answer and
   it reorders everything below it.
2. **★ ANSWERED — see "Q2 MEASURED" above.** Generator-grade at the reward-event
   unit: 400 direct + ~204 indirect ≈ 600 derivable rewards over ~500 latch
   bits, with a mandatory v2 upgrade list (constant fold, caller join, variable
   commit form, catch-up filter, latch-bit keying).
2b. **★ ANSWERED — zero relative SC writes exist** (889 absolute, 0 relative;
   both prior figures were scanner artifacts). The missable column's remaining
   derivability risk is absolute-value ordering across branches, not deltas.
2c. **Can the owner supply disc-3/4 saves?** The calibration corpus stops at SC
   7200. The back half of the game holds most of the missables this feature is
   for, and has no ground truth. See §4c.
3. **What is the MINIMUM catalog that makes the feature worth shipping?** If the
   answer is "the ~25-counter dashboard", T1b is the product and §4b's dominant
   cost never has to be paid. If it is "every chest", T4's data risk is the
   project. Nothing between T1b and T4 is a natural stopping point, so pick one
   deliberately rather than by drift.
4. **Owner decision on provenance** for third-party compilations and for shipping
   FF9 room/item names in package-data — needed BEFORE a generator is written
   (§5).
5. **Localize or not.** The kit writes 7 language dirs with identical bodies for
   non-localized content (`config.py:34`); genuine localization multiplies every
   authoring figure in §4b by 7. This is an owner call, not an implementation
   detail, and it should be made before the catalog schema is frozen.
6. **Measure the detail-pane character budget.** The kit's 6×32 lore budget was
   measured against the key-item parchment popup, a different surface. The
   `ShrinkContent` pane shrinks rather than clips, so an over-budget row is
   illegible, not visibly broken.
7. **Bracket the first rendered frames** of any meter panel before believing it
   is free. Folklore's list is name-labels only; sliders and sprites are a
   different drawcall profile, and a synchronous stopwatch cannot see NGUI's real
   cost.

### 7.3 The gates this arc owes, named now

Every mature arc here ships a one-command gate
(`studies/path-d-new-world/terrain_gate.py`, the docsite gates). Name them before
the first row is authored, not after:

- **`journal lint`** — a CLI verb on the `lint-eb` / `lint-campaign` /
  `lint-journey` precedent (`cli.py:6488, :6528, :6788, :8675`).
- **Catalog schema lint** — every row has a category, a source citation, a
  resolvable predicate, and an `exclusive_group` / `run_mode` tag where §T4's
  mutual exclusions apply.
- **Cross-feature id uniqueness** — folklore's duplicate check covers only
  `[[folklore]]` blocks (`build.py:8609-8617`). If the journal ever mints ids in
  the same band, that check must widen or the collision is silent.
- **Text-budget lint** — per-row string budgets enforced at the call site, against
  the *measured* pane budget (§7.2 Q6), not the inherited parchment-popup one.
- **A resolver round-trip** — for every catalog row, the §T3 state resolver
  returns a value on a known save. This is the gate that would actually catch a
  wrong row, and it is the one with no precedent in the repo.

**Standing caveat: a green run in this worktree proves nothing** —
`provision.templates_present()` is False here (measured), and `conftest.py:86-116`
converts data-absence into `pytest.skip`. Run the gates in the MAIN repo.

### 7.4 One risk nobody in the pass raised

**The owner's install stacks Moguri** (`Memoria.ini [Mod] FolderNames` —
`"FF9CustomMap", "FF9CustomMap-world", "MoguriMain", "MoguriVideo"`). Key-item
ids, ability pools and item names can therefore differ from stock. **Any
id-keyed journal row must resolve its display name at RUNTIME from the live
tables, never bake a name table into the catalog** — otherwise the journal shows
correct state under a wrong label, which is the hardest defect class to notice.
This is a catalog-schema constraint and it appears in none of the four designs.

### Standing laws this arc inherits

- **A GREEN GATE SUITE IS A REGRESSION HARNESS, NOT AN ORACLE** — 0 of 13
  playtest verdicts predicted by a gate.
- **THE DEFECT FOLLOWS THE AUTHORSHIP** — 12 of 13 verdicts and 32 of 37 named
  defects on the round's newest surface. Minting two new widget classes (T5) is
  minting defect surface.
- **A green run in this worktree proves nothing** — `templates_present()` is
  False here, measured.
- **Calibrate the instrument before you judge with it** — which is the entire
  argument for T0 preceding everything.
