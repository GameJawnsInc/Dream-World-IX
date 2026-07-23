# Silent Bench — the host-silent battle bench (field 30112)

**★★ TWO-MACHINE PROVEN 2026-07-23** (the reliability-round session): the host's random battle on
this bench was silent for BOTH players — the host truly silent, and the guest's diorama honored
the `0xFFFE` host-silent sentinel with no carried theme and no local fallback — and warping back
to field 250 afterward resumed the field music for BOTH players cleanly (the stop-not-suspend
path: no stacking, no double copies — the exact defect this bench exists to catch). Closed via the
engine's **s54** fix on the guest side, not a change to this bench or its recipe, which stands
unchanged for future re-runs; see `../b36-round.md` (Lane 1) for the mechanism.

A minimal walkable field that **force-stops whatever BGM is playing on any entry** and whose
random encounters play **no battle music**, so a two-machine netsync session can verify the
battle-diorama's **host-silent BGM-carry lane** (s41/B3.6, wire v10). No stock FF9 field has a
silent random battle — every random-encounter field maps to song 0 (the Battle Theme) — so we
mint one. The field also has no BGM of its own to give away, so — unlike the first cut of this
bench, whose playtest found it silently *inherited* whatever track was already resident — it no
longer depends on a "warp in fresh, before anything else plays" precondition: `[music] stop`
kills the carried-in track (the host's own previous field, or the guest's follow-warp source,
e.g. Evil Forest's theme) unconditionally, every time.

- **Field id:** `30112` (the coop test band 30110–30200; 30110 = twin altar, 30111 = twin vault).
- **Internal name as deployed:** `TEST30112` (the `deploy_field.py` sandbox name; the follow-warp
  keys on the *id* 30112, so this is cosmetic).
- **Source:** `studies/battle-coop/silent-bench/silent_bench.field.toml` (+ `art/` placeholder PNGs).
- **Scene:** cloned from the proven-walkable `coopgate` coop-band field — a flat 2440×2188-unit room.
- **Encounter:** scene `67` (Evil Forest / Trail — the game's **first and weakest** battles, so
  testers are not wiped mid-bench), `freq = 200` (of 255; higher = more frequent → a fight fires
  within ~30 s of walking).

## What `[music] stop` + `battle_music = -1` emit (mechanically)

**`[music] stop = true`** is consumed in **`ff9mapkit/ff9mapkit/content/music.py`**
(`add_stop_current_music`) and wired from **`build.py`**'s synthesize path: it prepends
`RunSoundCode(265, 0xFFFF)` — `FF9SOUND_SONG_STOPCURRENT()` — to the very start of Main_Init
(entry 0, tag 0), via `eb.edit.insert_in_function(eb, 0, 0, 0, ...)`. A `rel_off=0` prepend is
always safe and, applied last among Main_Init's rel_off-0 inserts, becomes the field's literal
FIRST instruction — no earlier code path can let a carried-in resident song survive. `ObjNo` is
ignored by this dispatch case (Memoria's `FF9Snd.cs` `FF9AllSoundDispatch`, case 265 →
`FF9SOUND_SONG_STOPCURRENT()`, no args) — the `0xFFFF` sentinel is simply the byte-true stock
convention: a census of all 818 shipping field `.eb` scripts finds `RunSoundCode(265, 0xFFFF)`
used exactly this way 3934 times (never any other `ObjNo` value), so the field kills whatever was
playing without needing to know what it was.

`[encounter] battle_music = N` is consumed in **`ff9mapkit/ff9mapkit/build.py`**:

- `build.py:7061` — `battle = (int(e["scene"]), int(e.get("battle_music", 0)))` → `(67, -1)`.
- `build.py:7908` — `bp_lines += [f"Battle: {scene}", f"Music: {mus}"]` → writes into `BattlePatch.txt`:

  ```
  // >>> ff9mapkit field 30112 BattlePatch (auto -- edit the field.toml, not here)
  Battle: 67
  Music: -1
  // <<< ff9mapkit field 30112
  ```

At runtime this populates `FF9SndMetaData.BtlBgmPatcherMapper[67] = -1` (scene-keyed, mod-global).
`GetMusicForBattle` for scene 67 then returns **-1** = *"no special battle song"*. FF9 normally
falls back to the currently-playing **field BGM** on a -1 (the field bleeds into the battle) — so
without `[music] stop` the trick would need a fresh warp (no resident field BGM playing) for a -1
battle to be silent. With `[music] stop` force-killing the resident track on every entry, the field
has nothing to bleed into the battle **on ANY entry**, fresh warp or not. (Contrast: `battle_music
= 0`, the default, pins scene 67 to the standard Battle Theme.)

Reference: `ff9mapkit/ff9mapkit/battle_bgm.py` (the `(field, scene) → song` map; -1 = "no mapping,
field BGM bleeds in"), `docs/FORMAT.md` `[encounter] battle_music` + `[music] stop`.

## The guest-side expectation (what the diorama must do)

From `studies/battle-coop/b36-round.md` (Lane 1, the swirl+BGM carry, wire v10):

- The **host** samples the audible battle song at the swirl:
  `wireSong = (songid != -1) ? songid : FF9Snd.GetCurrentMusicId()`. On this bench `songid == -1`
  (our `Music: -1`) **and** `GetCurrentMusicId()` returns -1 — the field's own `[music] stop` has
  already force-stopped whatever was resident, on ANY entry, not just a fresh warp — so the host
  ships wire sentinel **`0xFFFE` = "host audibly silent"** on the type-1 boot block.
- Sentinels: `0xFFFF` = *unknown* → the guest falls through to its **local** BGM computation
  (fail-safe). `0xFFFE` = *host-silent* → the guest **suspends its own BGM and plays nothing**.

**Expected observable on the guest's diorama:** the guest boots the same battle through the swirl,
renders the fight, and plays **NO music** — it must NOT fall through to a local battle theme (that
would be the `0xFFFF` path and a BGM-carry bug). Silent host battle → silent guest diorama.

This is the whole reason the bench exists: without a genuinely silent host battle you can only ever
exercise the `0xFFFF` (unknown → local fallback) path, never the `0xFFFE` (host-silent → suspend) one.

## Playtest recipe

**A RELAUNCH is required first** — a new field-id registration (`MessageFile`/`FieldScene 30112`)
and the `BattlePatch.txt` `Music:` line are read once at launch, not on a `~` reload.

Host (main PC, FF9CustomMap already deployed):
1. Fully quit FF9 and relaunch (registers 30112 + the BattlePatch line).
2. Open the debug menu: **`~` → Warp to field → `30112`**. No special timing needed — the field's
   `[music] stop` force-stops whatever was already playing the instant Main_Init runs, so warping in
   with a track already resident (the normal case) is now the PROOF condition, not a precondition to
   avoid.
3. Walk around the room until a random encounter fires (~30 s at freq 200).
4. **Expected (host):** the battle plays with **no music** — silence over the fight. (The weak Evil
   Forest enemies won't threaten the party.) Win/flee back to the field.

Guest (laptop) — needs 30112 staged + a relaunch (see the staging dir's `PATCH-LINES.txt`):
5. With a netsync session paired and the guest **following** the host, when the host's silent battle
   starts the guest's screen boots the **battle diorama** through the swirl. The guest's own
   follow-warp into 30112 (e.g. carrying in Evil Forest's theme) is likewise force-silenced by
   `[music] stop` on arrival.
6. **Expected (guest):** the diorama renders the same fight and plays **nothing** (host-silent
   `0xFFFE` path). A local battle theme on the guest = the BGM-carry bug this bench is here to catch.

## Deploy / staging / revert

- **Deployed** (this session) into the live shared folder with the id explicit:
  ```
  py tools/deploy_field.py studies/battle-coop/silent-bench/silent_bench.field.toml --id 30112 --mod-folder FF9CustomMap
  ```
  Verified: DictionaryPatch gained only the two 30112 lines (30003/30110/30111 untouched);
  `BattlePatch.txt` created with `Battle: 67` / `Music: -1`.
- **Laptop staging:** the deployed 30112 files + the exact patch lines the laptop must merge are in
  the session scratchpad: `…/scratchpad/silent-bench-laptop-stage/` (`FF9CustomMap/…` + `PATCH-LINES.txt`).
- **Revert:** `py tools/scroll_out/revert_deploy_30112.py` (or `tools/scroll_out/revert_deploy.py`
  for the latest deploy). It surgically drops only the 30112 DictionaryPatch lines, removes the
  `FBG_N11_TEST30112` scene + `EVT_TEST30112` scripts, and deletes the `BattlePatch.txt` it created
  (there was no live BattlePatch before this deploy).
