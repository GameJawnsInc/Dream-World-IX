# PATHDGATE (field 30950) — the field-side half of Path D rung 6

A scratch bench field whose one job is to prove the **entrance** leg of the 9013 round trip:
walk onto a marked pad → fade → land on world **9013** at the V-shore bench island's landing
point. Authored and verified **offline only**; nothing here has been deployed or playtested.

| | |
|---|---|
| Field id / name | **30950 / PATHDGATE** (`EVT_PATHDGATE.eb.bytes`, `FBG_N11_PATHDGATE`) |
| Text block | **30950** (the field's own id — never a real block) |
| Mod folder | **`FF9CustomMap`** (the field side; 9013's geometry lives in `FF9CustomMap-world`) |
| Destination | `WorldMap(9013)` at world **(425.0, −479.0)**, facing **224** (south-east) |
| Return contract | 9013's exit sets `D8:2 = 9999`, then `Field(30950)` |

**Id check at authoring time:** 30950 appears in neither live `DictionaryPatch.txt`
(`FF9CustomMap` holds 6000–6399, 30500, 30800–30850, 30900; `FF9CustomMap-world` holds 4600,
6602, `WorldScene 9013`). **Re-check before deploying** — EventDB is one flat global namespace
across every stacked folder and other sessions deploy continuously:

```sh
grep -ohE "(FieldScene|WorldScene|BattleScene) 30950" \
  "C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/FF9CustomMap/DictionaryPatch.txt" \
  "C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/FF9CustomMap-world/DictionaryPatch.txt"
# must print NOTHING
```

---

## Why the world jump is spliced in, not authored in the toml

There is deliberately **no `[[gateway]]` block**. No declarative surface reaches a custom
world id:

* `[[gateway]] to = <id>` compiles to `Field()` — a **field** warp (`build.py:6298`).
* `[[gateway]] to = "worldmap"` compiles to the verbatim shared **exit cascade**
  (`build.py:6283-6295` → `content/worldexit.py`), which routes only the thirteen *stock*
  `wldMapNo`s 9000–9012 through `(ScenarioCounter band) × (region key D8:2)`. **9013 is in
  s73's custom 9013–9099 band; no cascade arm emits it.**

So the field ships gateway-less and `inject_worldjump.py` appends one tread region carrying
the single-target `WorldMap(9013)` form (opcode `0xB6`) to the **deployed** `.eb.bytes`,
all seven locales. Step 2 below is therefore **not optional** — without it the field is an
empty room.

---

## Deploy sequence (run from the worktree root)

`C:\gd\Dream-World-IX\.claude\worktrees\path-d-rung-6-handoff-e2535a`

### 1 — deploy the field

```sh
py tools/deploy_field.py studies/path-d-new-world/rung6/fieldside/pathdgate.field.toml \
   --id 30950 --name PATHDGATE --mod-folder FF9CustomMap
```

> ⚠ **`--name PATHDGATE` is mandatory.** `deploy_field.py` forces a sandbox identity and
> defaults the internal name to `TEST<id>` (`deploy_field.py:64`), which would deploy
> `EVT_TEST30950.eb.bytes` — and step 2 would then find nothing to patch (it reports
> `MISSING` and exits 1; safe, but you would have deployed a dead room).
>
> `--id 30950` is likewise mandatory — without it you land in the shared 4003 sandbox slot.
> `--mod-folder FF9CustomMap` matches this worktree's `.ff9deploy.toml` pin; passing it
> explicitly keeps the command correct if that file changes.

The build's own `text_block = 30950` is used as-is (this worktree's `.ff9deploy.toml` pins no
`text_block`, so nothing overrides it).

### 2 — splice in the world jump

```sh
py studies/path-d-new-world/rung6/fieldside/inject_worldjump.py --dry-run   # look first
py studies/path-d-new-world/rung6/fieldside/inject_worldjump.py            # then write
```

Defaults: `--mod-folder "C:\Program Files (x86)\Steam\steamapps\common\FINAL FANTASY IX\FF9CustomMap"`,
`--field-name PATHDGATE`, all seven locales. Expected output is seven `OK` lines, each
`slot 4, 1192 -> 1336 B (+144), Range body 107 B, all funcs decode clean`.

* **Idempotent** — a file that already carries a `WorldMap` op is `SKIP`ped, no backup is
  written, exit 0. Re-running after a partial run or an unchanged deploy is free.
* **Backups** go to `C:\gd\Dream-World-IX\backups\rung6-pathdgate\<UTC stamp>\<lang>\`
  (the MAIN repo, not this worktree — a worktree dies with its branch and would take the
  only copy of the pre-patch bytes with it). Override with `--backup-dir`.
* Nothing is written until the patched bytes pass every check in the script's docstring,
  including the non-destructive invariant (no pre-existing function may change).

### 3 — sanity-check the deployed bytes (optional, 5 seconds)

```sh
cd ff9mapkit && py -m ff9mapkit lint-eb \
  "C:/Program Files (x86)/Steam/steamapps/common/FINAL FANTASY IX/FF9CustomMap/StreamingAssets/assets/resources/commonasset/eventengine/eventbinary/field/us/EVT_PATHDGATE.eb.bytes"
```

Expected: **`1 error(s), 0 warning(s)`** — exactly one `entry0/tag1: empty function body`.
That error is present on the untouched blank-field template itself and on every field the
kit has ever built (the template's entry-0 declares its slot size 65 bytes short of its own
tag-1 `RETURN`; `eb-src` renders those bytes as a `.gap ... live code the engine reaches by
func fpos`). Anything **more** than that one error means something went wrong.

### 4 — RELAUNCH the game

**Required.** 30950 is a brand-new id, so its `FieldScene` line is a new DictionaryPatch
registration and DictionaryPatch is read **at launch**, not by the `~` menu reload. (A
*later* re-deploy of the same id only needs `~ → Reload field`.)

### 5 — reach it in-game

`~` → **Warp to field** → **30950**. You arrive at the default spawn, back-centre of the
room, facing the camera.

---

## What the owner should see (playtest script — entrance leg only)

1. **Arrive at 30950.** A checkerboard room. Dead ahead, down-screen at the front edge, a
   floor **teleport pad** with a floating **balloon** over it. That pair is the landmark —
   the trigger has no pixels of its own.
2. **Walk straight forward (W / down-screen)** onto the pad. On contact the screen should
   **fade to black over ~24 frames**, hold ~25 frames, then hand off to the overworld.
3. **You should be standing on world 9013**, on the V-shore bench island's grass lawn, at
   `(425, −479)` facing south-east, with the island's central massif on your right and a
   clear walking corridor down the east side.
4. **Failure signatures worth naming precisely:**
   * *Nothing happens on the pad* → the region never armed (step 2 skipped, or a re-deploy
     wiped it), or movement was disabled when you crossed.
   * *Fade, then a black screen / crash* → 9013 not reachable (check `WorldScene 9013` is
     still registered in `FF9CustomMap-world` and that the engine bundle with s73 is live).
   * *Fade, then you land somewhere in 9013 that is NOT the bench island* → `D8:2` got
     re-zeroed, so WORLD13's entry-14 stamped stock WORLD11's default point over the
     preset. That is the one thing the `D8:2 = 35` write exists to prevent.
   * *You land and immediately fall / cannot move* → the y seed or the ground under
     (425, −479); the site pass measured 3.200, topo 0, one walkable sheet, 13u clearance.

The **return leg** cannot be tested until the world-side half exists. Its contract is below.

---

## The return contract (what the world side must write)

9013's exit must set `D8:2 = 9999` immediately before `Field(30950)`. The field carries the
matching arrival row:

```toml
[[player.arrival]]
entrance = 9999
pos = [0, -1100]
face = 128
```

which compiled (verified in the built `.eb`) to
`if (Global.Int16[2] == 9999) { x = 0; z = −1100; face = 128 }` ahead of the player's
`CreateObject`/`TurnInstant` — so the player materialises there on frame 0, no flash of the
default spawn.

`pos` is **400u north of the trigger zone's near edge on purpose**: the trigger is a *tread*
region that fires every frame the player stands in it, so a return landing inside the band
would bounce straight back to 9013 in a loop. Any change to `ZONE_CORNERS` must keep that
gap.

Any other entrance value (including a `~` warp, which writes none) falls through to
`[player] spawn = [0, 0]`.

---

## Reverting

| What | How |
|---|---|
| The whole deploy (field + its DictionaryPatch line) | `py tools/scroll_out/revert_deploy_30950.py` — written by step 1, per-id, reverts only 30950 |
| Just the splice, keeping the deploy | copy the seven files back from `C:\gd\Dream-World-IX\backups\rung6-pathdgate\<stamp>\<lang>\EVT_PATHDGATE.eb.bytes` |
| Nothing at all | step 1 already reverts *this id's* prior deploy before installing; deploying 30950 never touches another id |

Removing the DictionaryPatch registration needs a **relaunch** to take effect.

---

## ⚠ Every re-deploy wipes the splice

`deploy_field.py` overwrites all seven `EVT_PATHDGATE.eb.bytes`. **Re-run step 2 after every
step 1.** It is idempotent, so the safe habit is simply to always run them as a pair.

---

## Files here

| Path | What |
|---|---|
| `pathdgate.field.toml` | the bench: camera, walkmesh, placeholder art, spawn, arrival 9999, the two landmark props, and a build-inert `[[marker]]` that draws the injected zone on the layout probe |
| `inject_worldjump.py` | the post-deploy splice; `--dry-run`, idempotent, verifies before writing, backs up per file |
| `prove_guard.py` | breaks the verifier on purpose and shows it refuses — run it against an unpatched built `.eb` |
| `art/back.png`, `art/floor.png` | ARRTEST's placeholder checkerboard, copied verbatim (the camera + walkmesh here are ARRTEST's, so the art lands correctly) |
| `layout/topdown.png`, `layout/camview.png`, `layout/report.txt` | `tools/field_layout_probe.py` output for this toml |
| `layout/pathdgate.injected.ebs` | the patched `us` script decompiled to `.ebs` source — the annotated, human-readable decode of what gets deployed |

## Geometry cheat sheet

ARRTEST's frame, verbatim. **FRONT = toward the camera = NEGATIVE z.** Facing byte
0 = south (at the camera), 64 = west, 128 = north (away), 192 = east.

```
   z = +257  ────────────────────────────  BACK  (up-screen)
                      ●  spawn (0, 0) face 0
   z = -1100          ◐  arrival 9999 (0,-1100) face 128
   z = -1500  ┌──────────────────────────┐
              │   ▣ pad + balloon        │  the injected tread zone
   z = -1900  └──────────────────────────┘  q0(-600,-1900) → q1(600,-1900) = walk-out edge
   z = -1931  ────────────────────────────  FRONT (down-screen, toward the camera)
              x = -1220              x = +1220
```

The player's centre can never pass `z = -1851` (walkmesh front −1931 + the 80u controller
radius), so the strip covers every reachable point at the front and cannot be skirted along
z. It **can** be walked around at `|x| > 600` — deliberate: the pad is a door the player
chooses, not an invisible wall.

---

## Offline verification already run (no deploys, no game writes)

| Check | Result |
|---|---|
| `ff9mapkit lint <toml>` | `OK -- no problems.` |
| `ff9mapkit build` into a scratch dir | 7 locales + `FBG_N11_PATHDGATE` scene; `FieldScene 30950 11 PATHDGATE PATHDGATE 30950` |
| `inject_worldjump.py --dry-run` | 7/7 `OK`, slot 4, 1192 → 1336 B, Range body 107 B |
| `inject_worldjump.py` (write, into a scratch copy) | 7/7 patched, post-write read-back byte-identical |
| re-run on the patched copy | 7/7 `SKIP`, no backup written, exit 0, files untouched |
| `ff9mapkit lint-eb` × 7 patched locales | 1 error each — identical to the unpatched build **and** to the blank template: the splice adds zero findings |
| `eb-src` → `eb-asm` round trip × 7 patched locales | **7/7 BYTE-EXACT** through the kit's independent decoder |
| `prove_guard.py` | control passes; 3/3 deliberate defects refused |
| `tools/field_layout_probe.py` | routes on-mesh; the only warnings are the two co-located `collision = false` props (a geometry-only false positive) and the zone-outline marker route hugging the walkmesh edge |

*Not verified, and not verifiable offline:* that the engine actually accepts `WorldMap(9013)`
for a custom world id, and that the landing point plays as measured. Those are the playtest.
