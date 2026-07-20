# Regions, gateways & encounters (authoring reference)

Canonical sources: memory `project-ff9-gateway-regions.md` (trigger mechanics + region arming + the >2-region bug) and `project-ff9-encounters.md` (after-battle fix + battle music + the song-0 fork BGM fix). Lines below are quoted verbatim from those files or CLAUDE.md §7.

## Region trigger mechanics

Quoted verbatim from CLAUDE.md §7:

> - Region triggers only fire when `usercontrol == 1`. **Region tag 2 = tread** (every frame in
>   the quad), **tag 3 = press-to-interact** (action button), **tag 10 = Main_Reinit** (runs after
>   battle). The player must actually REACH the zone (place it where he demonstrably stands).
> - Exit walk-out direction is set by the polygon's **point ORDER** (q[0]→q[1] edge first = walk
>   forward, no "circle").

The IsInQuad dead-zone law, quoted verbatim from CLAUDE.md §7:

> **`IsInQuad`/`TreadQuad` test a FAN of consecutive vertex-triplets, not the real polygon** —
> 3 collinear points = a zero-area triangle = a DEAD ZONE. Use a convex quad with the last
> vertex DOUBLED.

Debug method (from `project-ff9-gateway-regions`): a spawn-covering test zone is the definitive "do triggers work here at all" probe; bisect the variables, don't theorize.

## Fade-before-Field()

Quoted verbatim from CLAUDE.md §7:

> **A field→field warp MUST fade to black BEFORE `Field()`** — else the destination loads *in the
> clear* and the player sees its camera wire up to him (~0.8s of the scroll camera sitting on the
> bare scene centre, player in a corner = the "static screen on spawn"). The proven fade is
> `fade_filter(6,24,0,255,255,255) + wait(25)` (SUB mode → white = screen→black), exactly what
> gateways/ladders/the field-70 opening emit. The kit lever: `content.event.warp(..., fade=True)`
> (choice-warps + cutscene `then_warp` use it). Never insta-warp a player-visible transition.
> `entry_settle` is the *destination*-side complement (assumes the field already loaded black, i.e.
> the source faded).

## Region arming & the >2-region bug

Quoted verbatim from `project-ff9-gateway-regions`:

> **Region arming = overwrite a Main_Init `Wait` filler with an `Init*` call, shift-free.** A region entry
> (a gateway, an event, a camera-switch zone) is appended to a free entry slot, then *activated* from Main_Init
> (entry 0, tag 0) by `eb.edit.activate`, which overwrites a 3-byte `Wait(2)` filler with the equal-length
> `InitRegion(slot,0)` / `InitObject` / `InitCode(slot,0)`. NPCs use `InitObject`; gateways use `InitRegion`.

> ★ **The blank/borrowed Main_Init has only TWO `Wait(2)` fillers.** A content-rich field (e.g. 2 gateways + 2
> events) overflows them: the first 2 regions patch the fillers shift-free; the 3rd+ must **INSERT** its `Init*`
> into Main_Init.

The historical bug (fixed 2026-06-11, kit 0.9.14): the insert fallback used raw `insert_bytes`, leaving other entry-0 functions' `fpos` STALE → the region SILENTLY never armed. Fix, quoted verbatim:

> route the fallback through `edit.insert_in_function(data, 0, 0, 0, init_bytes)` (the fpos-fixing insert — the same primitive `[startup]` uses), so any number of regions arm even on a borrowed field.
> Verify in-game/offline: `disasm <eb> -e 0` and count `InitRegion`/`InitObject`/`InitCode` == #regions/objects;
> trace the chain Main_Init→`InitCode(arm)`→arm-entry→`InitRegion(event)`.

## Encounters

Quoted verbatim from `project-ff9-encounters`:

> - `SetRandomBattles(0x3C, pattern, s0,s1,s2,s3)` — encoding `3C 00 <pat:1> <s0:2><s1:2><s2:2><s3:2>` (argflag 0 = all immediate; sizes [1,2,2,2,2]).
> - `SetRandomBattleFrequency(0x57, freq)` — `57 00 <freq:1>` (0–255; 255 ≈ a battle every ~12 steps).
> A battle SCENE id carries its own enemies AND battle background, so reuse an existing scene.

## The after-battle softlock + fix (tag-10 Main_Reinit)

Quoted verbatim from CLAUDE.md §7:

> A field cloned from a cutscene field lacks an entry-0 **tag-10 Main_Reinit** → after-battle
> **softlock** (`EnterBattleEnd` suspends objects; nothing resumes them). Fix: add a tag-10 that
> `FadeFilter(2,16,…)` (overrides BattleResultUI's 256-frame timed fade) + re-enables move.

Minimal tag-10 body, quoted verbatim from `project-ff9-encounters`: "**`EnableMove(0x2E) ; return(0x04)`** = `2E 04`" — the `return` at level 0 triggers `ExitBattleEnd()` → objects resume. Without the fast `FadeFilter` prepended, the 256-frame battle-return fade plays out in full (slow fade, not a perf issue).

## Battle & field music

Quoted verbatim from CLAUDE.md §7:

> BattlePatch `Music:` = the akao **song-play id** (0 = Battle Theme), NOT a file number. Field
> BGM = `RunSoundCode(0, <song id>)` (song id, not file number; Vivi's Theme = 9).

Song-0 fork battle BGM (fixed 2b0927b, in-game proven 2026-06-22), quoted verbatim from `project-ff9-encounters`:

> `_donor_battle_bgm_pairs` now carries the donor's real song INCLUDING 0; only an UNMAPPED
> scene (`song is None`) is skipped. A re-fork/re-deploy emits `Battle: <scene> / Music: 0`, pinning the standard
> Battle Theme on the custom id.

## In-game gotchas

Quoted verbatim from `project-ff9-gateway-regions`:

> - **~ Reload does NOT refresh a campaign field's `.eb`** — after a `deploy_campaign` redeploy you must fully
>   **RELAUNCH** the game to load the new `.eb` (~ Reload works for the single-field test slot, not campaign members).
> - For a clean narrative-state demo, the **~ → Flags readout is the reliable proof** (it
>   reads `gEventGlobal` directly, immune to art/floors/rendering).

## Pointers

- Memory: `project-ff9-gateway-regions.md`, `project-ff9-encounters.md`, `project-ff9-story-flags.md` (the flags a gateway/event sets).
- Docs: `ff9mapkit/docs/FORMAT.md` (`[[gateway]]`/`[[event]]`/`[encounter]` schema).
