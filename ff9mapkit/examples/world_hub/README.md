# World Hub — a playable journey selector (MVP scaffold)

A **World Hub** is a playable field that lets the player pick which **journey** to play, then warps them
in. A *journey* = a complete playable arc (one or more chained campaign slices). The hub's only job is
**select → (optionally seed) → warp**; it's decoupled from journey internals — it needs only
`{name, entry field id, optional seed}` per row. It is **NOT** a custom worldmap (no engine fork — just a
field + a dialogue-choice menu + warps). See the deep notes in memory `project-ff9-world-hub`.

The hub is one field; its journeys warp into **real verbatim forks of actual FF9 fields** (real logic + lines):

| What | Id / folder | Role |
|---|---|---|
| `hub.field.toml` | 4500 / `FF9CustomMap-ow` | The hub. Walk as a Moogle, talk to Stiltzkin → a journey menu. |
| **Dali** (journey 1) | 4100 / `FF9CustomMap-sf` | A **verbatim** (native) fork — the *real* Dali story, real lines, real party-setup (story_flags' `DALI_CAPSTONE` chain, source field 359). The faithful flagship; the hub seeds `scenario = 2600` ("Waking up in Dali") before warping. |
| **Treno** (journey 2) | 4501 / `FF9CustomMap-ow` | A **verbatim** (native) single-field fork of the **Treno Pub** (source field 1900, `TR_BAR`) — a clean, beat-agnostic field with 3 real NPCs + 17 real lines. Forked into `journey_treno/` and deployed to the 4501 slot; the hub seeds `scenario = 7550` ("Treno"). One door is a *live seam* back into the real game. |

`journeys.toml` is the **generator input** — `ff9mapkit gen-hub journeys.toml` emits the `hub.field.toml`
above (see *Generate the hub* below). The hub stays **thin**: per journey it knows only `{id, name, entry id,
optional seed}`; HOW a journey plays internally is the fork's own business.

> The two trivial stub fields `journey_one.field.toml` / `journey_two.field.toml` are the original
> **zero-dependency scaffold** — they just prove the warp landed (a Moogle greets you), with no fork to
> deploy. Point a `journeys.toml` `entry` at one of them (e.g. 4502) to demo the select→warp loop without
> first deploying a real fork.

## How it works

- **Moogle PC** — `[player] model = 220` re-skins the field avatar to the iconic Moogle (`GEO_NPC_F0_MOG`,
  the save moogle — **not** 199, which is a bat-winged variant). The new `[player] model=` option; movement
  clips auto-resolved via the Info Hub model→animation join. Control ≠ party — the party menu is unchanged;
  the Moogle is just who you *walk* as.
- **The menu** — a normal `[[npc]]` (Stiltzkin) + `[[choice]]`. Each option has `warp = <entry id>` (the new
  choice **warp action**) and optionally `set_scenario`. Picking a row plays the transition sound and
  `Field()`s into that journey — grounded in real FF9 talk-handler warps (the Dali innkeeper, the airship).
- **One-way** — to switch journeys, start a New Game, which lands you back on the hub (the field-70
  New-Game override now points at 4500 — `tools/retarget_newgame_warp.py 4500`, seamless, no FMV).
- **Camera on entry** — Memoria's smooth-camera follower (`CameraStabilizer`) eases the camera to the player
  on *every* field load; you only notice it when the entry camera is far off, *and* there's no transition to
  hide the settle. Every real way into the hub already has that transition: **New Game** comes through the
  engine's start/field fade-to-black, and the journeys are verbatim forks with their own entrances — so the
  settle happens behind black and you see it already at rest. The lone exception is the **F6 debug warp**, an
  instant jump with no fade (a dev tool; players never use it). `[camera] entry_settle = N` (the generator
  emits 45) adds a black hold that reinforces the settle behind the entry fade; set `0` to drop it. To test a
  faded entry yourself, F6 → Warp **4502** (`hub_lobby.field.toml`) and walk through its door into the hub.

## Setup (provenance: you supply the game bytes)

The hub BG-borrows a real FF9 room, so it needs that room's **camera**, extracted from *your* install (the
repo ships zero game data — `*.bgx` is gitignored here). Extract the hub camera:

```bash
# from the kit root (ff9mapkit/)
py -m ff9mapkit extract-field 950   # -> .ff9mapkit-cache/fields/950/camera.bgx
# (or copy it next to hub.field.toml as camera_hub.bgx — see `gen-hub --extract-camera` below)
```

The **Treno** journey is a verbatim fork you generate from your install (the repo ships zero game bytes —
`journey_treno/` is gitignored). Regenerate it once:

```bash
# from the kit root (ff9mapkit/) — ships the Treno Pub's real .eb + .mes + native scene
py -m ff9mapkit import fbg_n20_trno_map417_tr_bar_0 --verbatim --out examples/world_hub/journey_treno \
    --name JOURNEY_TRENO --id 4501
# then set text_block = 22 in the emitted JOURNEY_TRENO.field.toml (1073 is shadowed by FF9CustomMap)
```

The **Dali** journey points at story_flags' `DALI_CAPSTONE` chain, already deployed in `FF9CustomMap-sf`. To
fork your own multi-screen journey, see *Scaffold → real hub* below.

## Deploy + playtest the loop

Deploy the **Treno fork** and the **hub** (Dali is already deployed in `FF9CustomMap-sf`). Run **from the kit
root** (`ff9mapkit/`) so `py -m ff9mapkit` picks up *this* checkout, not an editable install pointing at
another worktree — `deploy_field.py` lives one level up at the repo root, hence `../tools/`:

```bash
# from the kit root (ff9mapkit/)
py ../tools/deploy_field.py examples/world_hub/journey_treno/JOURNEY_TRENO.field.toml --id 4501
py ../tools/deploy_field.py examples/world_hub/hub.field.toml --id 4500
```

> Deploying several fields into one folder churns the `DictionaryPatch` — each `deploy_field --id N` first
> reverts N's prior deploy (a stale folder snapshot), which can drop a sibling's line (the *assets* survive).
> After deploying both, verify the `DictionaryPatch` lists **both** 4500 and 4501; if not, add the missing
> `FieldScene` line by hand (the assets are already on disk). See memory `project-ff9-text-block-shadow`.

Then in-game (relaunch once if the ids are brand-new, else **F6 → Reload field**):

1. **New Game** (lands on the hub), or **F6 → Warp → 4500**.
2. You're a Moogle. Walk to **Stiltzkin** and talk.
3. Pick **The Village of Dali** → the real verbatim Dali entrance (real lines/NPCs, seeded to the "waking up"
   beat). Pick **Treno, City of Nobles** → the Treno Pub (real NPCs + dialogue).
4. **Stay here, kupo...** closes the menu without warping.

That's the full **select → seed → warp into real content** loop.

## Generate the hub from `journeys.toml`

Instead of hand-authoring `hub.field.toml`, describe the journeys in a small registry and let the kit emit
the hub field — the **"hardcoded MVP → generator"** step. The hub stays *thin*: per journey just
`{id, name, entry field id, optional seed}`.

```bash
# from the kit root (ff9mapkit/)
py -m ff9mapkit gen-hub examples/world_hub/journeys.toml --out examples/world_hub/hub.field.toml
```

That reads [`journeys.toml`](journeys.toml) (a `[hub]` table + one `[[journey]]` row per destination) and
writes a `hub.field.toml` **logically identical** to the hand-authored one above (same Moogle PC, narrator,
and warp menu) — then build/deploy it exactly as in the previous section. Add or reorder journeys by editing
`journeys.toml` and regenerating; the emitted `hub.field.toml` is a build artifact (don't hand-edit it). The
generator validates the registry offline (id bands, dup names, the `text_block` 1073 shadow trap, menu
paging) before emitting.

### Let the generator fetch the camera for you

The BG-borrow camera still has to come from *your* install, but you don't have to extract it by hand. Set
`[hub] borrow_field = 950` in `journeys.toml` (the real field this room *is*) and add `--extract-camera`:

```bash
py -m ff9mapkit gen-hub examples/world_hub/journeys.toml --extract-camera --out examples/world_hub/hub.field.toml
```

That pulls field 950's camera into a **shared, gitignored workspace cache** (`.ff9mapkit-cache/fields/950/`,
override with `$FF9MAPKIT_DATA`) and points the emitted `[camera] borrow` at that one copy — so `gen-hub`
then build/deploy "just works", no manual step, and a second hub borrowing the same room reuses the cache.
You can also pre-warm the cache for any field(s) directly:

```bash
py -m ff9mapkit extract-field 950          # -> .ff9mapkit-cache/fields/950/{camera.bgx, walkmesh.bgi}
```

## Scaffold → real hub (all three steps now done)

- **(a) New Game lands on the hub** — the field-70 override points at 4500 (`tools/retarget_newgame_warp.py
  4500`), seamless (no opening FMV). ✓
- **(b) Real journey destinations** — the journeys warp into real forked slices already deployed in stacked
  folders (Dali 4100 verbatim, Ice Cavern 30100 editable), not trivial stubs. The hub seeds each journey's
  beat with `set_scenario`; the slice's own `[startup]`/`[party]`/verbatim party-setup does the rest. ✓
- **(c) The `[[journey]]` block + generator** — `ff9mapkit gen-hub journeys.toml` (see above). ✓

**The cross-folder contract:** the hub (`FF9CustomMap-ow`) `Field()`-warps into ids registered by *other*
mod folders (Dali's 4100 is in `FF9CustomMap-sf`). That works because all folders are stacked in
`Memoria.ini`'s `FolderNames` and field ids are globally distinct (EventDB is global). So adding a real
journey is just: deploy its chain into *some* stacked folder, then point a `[[journey]] entry` at its entry
id — no change to the hub's own build. To add your own: `ff9mapkit import-chain <seed> --out … --verbatim`
→ `build-all` into a folder → add an `[[journey]]` row → regenerate + redeploy the hub.

## Placement

Spawn / NPC coordinates are confirmed **in-game** (per the kit's hard constraint — the camera/walkmesh are
the borrowed field's). The player spawns use each room's real player spawn (guaranteed on-floor); nudge the
narrator if it lands off the walkmesh.
