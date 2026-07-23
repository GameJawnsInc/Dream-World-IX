# Silent Bench — the host-silent battle bench (field 30112)

A minimal walkable field whose random encounters play **no battle music**, so a two-machine
netsync session can verify the battle-diorama's **host-silent BGM-carry lane** (s41/B3.6, wire
v10). No stock FF9 field has a silent random battle — every random-encounter field maps to
song 0 (the Battle Theme) — so we mint one.

- **Field id:** `30112` (the coop test band 30110–30200; 30110 = twin altar, 30111 = twin vault).
- **Internal name as deployed:** `TEST30112` (the `deploy_field.py` sandbox name; the follow-warp
  keys on the *id* 30112, so this is cosmetic).
- **Source:** `studies/battle-coop/silent-bench/silent_bench.field.toml` (+ `art/` placeholder PNGs).
- **Scene:** cloned from the proven-walkable `coopgate` coop-band field — a flat 2440×2188-unit room.
- **Encounter:** scene `67` (Evil Forest / Trail — the game's **first and weakest** battles, so
  testers are not wiped mid-bench), `freq = 200` (of 255; higher = more frequent → a fight fires
  within ~30 s of walking).

## What `battle_music = -1` emits (mechanically)

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
the trick is to **warp in FRESH**: with no resident field BGM playing, a -1 battle is **silent**.
(Contrast: `battle_music = 0`, the default, pins scene 67 to the standard Battle Theme.)

Reference: `ff9mapkit/ff9mapkit/battle_bgm.py` (the `(field, scene) → song` map; -1 = "no mapping,
field BGM bleeds in") and `docs/FORMAT.md` `[encounter] battle_music`.

## The guest-side expectation (what the diorama must do)

From `studies/battle-coop/b36-round.md` (Lane 1, the swirl+BGM carry, wire v10):

- The **host** samples the audible battle song at the swirl:
  `wireSong = (songid != -1) ? songid : FF9Snd.GetCurrentMusicId()`. On this bench `songid == -1`
  (our `Music: -1`) **and** `GetCurrentMusicId()` returns -1 (nothing playing on a fresh warp), so
  the host ships wire sentinel **`0xFFFE` = "host audibly silent"** on the type-1 boot block.
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
2. Open the debug menu: **`~` → Warp to field → `30112`**. Do this **FRESH** — warp straight in
   before any resident field BGM starts, so there is no field music to bleed into the battle.
3. Walk around the room until a random encounter fires (~30 s at freq 200).
4. **Expected (host):** the battle plays with **no music** — silence over the fight. (The weak Evil
   Forest enemies won't threaten the party.) Win/flee back to the field.

Guest (laptop) — needs 30112 staged + a relaunch (see the staging dir's `PATCH-LINES.txt`):
5. With a netsync session paired and the guest **following** the host, when the host's silent battle
   starts the guest's screen boots the **battle diorama** through the swirl.
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
