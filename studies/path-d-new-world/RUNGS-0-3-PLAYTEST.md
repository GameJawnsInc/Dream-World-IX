# Path D — Rungs 0–3, the one-relaunch playtest script

Everything below is already built and deployed. **Relaunch FF9 once** (a DLL rebuild *and* a new
`DictionaryPatch` registration both require it — `~` reload is not enough), then work down the list.
Each step changes exactly ONE variable from the step before it.

**Engine:** `s70` + `s71` + `s72`, built 2026-07-29, both arches, 0 errors.
**Pre-build DLL backup:** `py tools/restore_memoria_dll.py 20260729-153010` reverts the whole engine.
**Everything is inert until deliberately armed** — a normal disc-1/4 load is unaffected, and so is every
other concurrent worktree.

---

## Before you start

**`ArmWorldReload` has two preconditions** (`Ff9mkDebugMenu.cs:1431-1432`, found this pass — the plan did
not price them): `UIManager.State == WorldHUD` **and** `sys.mode == 3`. So:

> **Load a save and walk out onto the OVERWORLD first.** The button cannot be fired from a field, a
> battle, or the main menu — it silently reports `reload world: overworld only`.

Use a save you don't mind reloading. Rung 2 runs a real dispatcher's script, which writes ordinary
world-state bytes.

**Where the evidence lives.** Two different files, and the distinction matters:

| What | File |
|---|---|
| Our own `[PathD …]` lines | `<game>\Memoria.log` |
| Unity exceptions / NREs / stack traces | `<game>\x64\FF9_Data\output_log.txt` |

⚠ The plan said to read Rung 0's result in `Memoria.log`. **That is wrong** — there is no Unity→Memoria
log bridge, so a plain `Debug.Log` and every Unity exception land only in `output_log.txt`. Our new lines
go through `Memoria.Prime.Log`, so they *do* reach `Memoria.log`. Expect to look in both.

---

## Step A — Rung 0: is a new world id reachable at all?

1. On the overworld, press **`~`** → **Go** tab → the **"Reload overworld on a state"** box.
2. Type **`31000`** (a genuinely unregistered id) and press **Go**.

**PASS:** the screen tries to reload and fails *informatively* — `output_log.txt` gets a
`KeyNotFoundException` from `FF9DBAll.EventDB[MapNo]` inside `ff9InitStateWorldMap`, and `Memoria.log`
gets `[PathD s70] force world state -> 31000 (EXPERIMENTAL, outside 9000-9012)`. A hung/black screen here
is the EXPECTED shape of success — the id genuinely has no script.

**FAIL:** the menu still refuses with "need an id 9000-9012" (patch didn't land), or the game dies with
nothing in either log.

> ⚠ **Do not use an id in 4000-9899 or 30000-32767 at random** — the plan suggested that, but any id
> registered by a stacked `DictionaryPatch` already HAS an EventDB row, so you'd get an
> `ArgumentNullException` from loading a *field* `.eb` down the world path instead of the clean
> unregistered-id signal. `31000` is confirmed free in both live registries.

**Recover:** reload your save.

---

## Step B — Rung 2: does a NEW dispatcher id actually run a script?

*(Deliberately before Rung 1 — it touches no geometry, so it isolates the state axis completely.)*

1. Back on the overworld, `~` → **Go** → type **`9013`** → **Go**.

**PASS:** the overworld loads **normally, on the real disc-1 geometry**, running a verbatim clone of
WORLD11's script. Reopen `~` and confirm the World tab's dispatcher readout says **9013**. `Memoria.log`
should carry `[PathD s72] WorldScene 9013 -> EVT_WORLD_WORLD13 (mes 68)` from mod-load time.

That combination — registered at load, warped to, world runs, id reads 9013 — is the whole Rung 2 claim.

**FAIL:** immediate crash on warp, or the id silently reads back as something else (a fallback would
falsify "EventDB has no range check").

---

## Step C — Rung 1: THE PIVOTAL ONE — can WorldDisc be minted in C#?

This is the question the entire plan hinges on.

1. `~` → **Go** tab → tick **`[ ] Path D: synthetic WorldDisc (next world load)`** so it reads `[x]`.
   (Session-only; it clears itself on every relaunch.)
2. Type **`31000`** again → **Go**. (Unregistered on purpose — Rung 1 has no dispatcher of its own.)

**PASS:** `Memoria.log` shows `[PathD s71] WorldDisc replaced by a synthetic WorldDisc_SPIKE (480 IsSea
blocks)`, and `output_log.txt` contains **no NRE and no IndexOutOfRangeException inside `WMWorld`'s
`Initialize` / `OnInitialize` / `LoadBlocks` / `DetectUnseenBlocks`**. The only exception should be the
same `KeyNotFoundException` from Step A — i.e. it got all the way past the geometry and died at the
*dispatcher* lookup. `WMWorld.cs:1226`'s `Finished Loading Blocks!` is the strongest positive.

**FAIL:** any NRE/IndexOutOfRange inside those `WMWorld` functions, or a hang.

**Recover:** untick the toggle (or just relaunch — it defaults off), then reload your save.

---

## Step D — Rung 3: the combination

> ⚠ **THE TRAP (hit for real 2026-07-29, Rung 3 attempt 1).** Step C ends in a black screen, so you have
> to restart — and the spike toggle is **session-only by design**, so the restart clears it. "Leave the
> toggle armed" across Steps C→D is impossible. Attempt 1 warped to 9013 with the spike silently OFF and
> got a perfectly normal stock disc-1: the right behaviour, the wrong experiment. **Always confirm
> `[PathD s71] … ARMED` is in `Memoria.log` before reading a Rung 3 result.**
>
> You do NOT need to restart to run this. From a working 9013 (or any overworld), just re-arm and warp —
> the toggle takes effect on the next world load.

1. On the overworld, `~` → **Go** tab → tick the spike so it reads **`[x]`**.
2. **Confirm it armed:** `Memoria.log` should gain `[PathD s71] synthetic WorldDisc spike ARMED`.
3. `~` → **Go** → **`9013`** → **Go**.

**PASS — and this is the money shot:** the world loads as **open ocean containing only the Southern
Ring's reclaimed cells**, with a working script. Nothing else. That is a 480-cell grid that did not exist
as a baked asset ten seconds earlier.

**Please grab a screenshot or a short capture of this one** — it is the first visual evidence Path D is
real, and it is the exact thing I cannot see for myself.

**Expected oddities that are NOT bugs:**
- **56 land cells floating in the ocean.** The install already ships 56 disc-1 `Terrain.ff9mesh` overrides in
  `FF9CustomMap-world` (the Southern Ring's work), so those cells take the proven s34 reclaim path. The
  plan claimed "no override files exist yet, so every cell is plain sea" — that is **refuted by the live
  install**. I left them in deliberately: they're the already-in-game-proven path, and an ocean with only
  those cells in it is an unmistakable success picture.
- **A water shrine, some quicksand, and a building** in odd places. Blocks 219 / 91 / 115 / 389 carry
  stock special-object cases keyed on the block Number, which I kept stock-faithful. Seeing them is
  *positive* evidence that cell addressing works.
- **You may not be able to move.** There's no player yet — that's Rung 4.

---

## If Rung 1 fails

Don't start engineering around it. Send me `output_log.txt` and `Memoria.log` and I'll read the stack
trace — the plan's fallback (a real third disc + a baked Unity `WorldDisc` AssetBundle) is XL and blocked
on an asset-authoring capability the toolkit doesn't have, so it's worth being certain the failure is real
and not one of the incidental landmines before going near it.

Three such landmines were already found and fixed pre-emptively this pass, none of which are about
WorldDisc substitution at all: `Form2Transforms` never being initialised, `CurrentX`/`CurrentY` left at
zero, and `DetectUnseenBlocks` indexing `Blocks[0,-1]` because with no player the sentinel actor sits at
the world origin.

---

## Step E — Rung 5a: the FIRST authored land in a Path D world

Deployed 2026-07-29. A synthetic cliff island, minted by the shipped `world-island` verb (a look already
in-game proven as island E), written into **Path D's own override namespace** for the first time:

```
py -m ff9mapkit world-island --center 800,-672 --radius 44 --lobes 1 --seed 44 \
    --mod-folder FF9CustomMap-world --target-disc 9 --all-sea-target
```

Offline result: **all gates CLEAN** (geometry, UV language, placement census 0 MISS) across 5 blocks —
`(11,10) (12,9) (12,10) (12,11) (13,10)`, 990 tris total, centre grounding y=3.2 on Terrain topo 0.
Two advisory warnings (`tex-zero-uv`, `tex-one-window`); every `one-window` hit is on a block border, the
known false positive.

45 files landed under `WorldMap/Disc9/`, and the real `Disc1`+`Disc4` trees stayed byte-identical across
all 987 files. The `discmirror` guard fired on its first production use:
`disc-4 mirror: refused for Disc9 (not a real disc -- a synthetic override namespace is deliberately unmirrored)`.

### How to look at it

No rebuild needed — this is data. A first-time block needs a **world re-entry** to stream the override.

1. `~` → **Go** → confirm the spike reads `[x]` for CLONE only if you want the stock map; for this test
   leave it **BLANK** (unticked).
2. `~` → **Go** → `9013` → **Go**.
3. `~` → **World** → teleport to **(800, -672)** — the centre of the grid, and of the island.

**PASS:** an island with a rock cliff wall and grass top, alone in the ocean, walkable at the centre.

**What this proves if it lands:** the full authoring path works into a world that did not exist — read
real bytes from disc 1, write into a namespace disjoint from it, render on a runtime-minted WorldDisc.
That is Rung 5a, and the first content ever authored into a third FF9 overworld.

**What it does NOT prove:** anything about synthesis quality. This look was already accepted; the point of
choosing it was that any failure is *plumbing*, not art. The genuine synthesis question (the terrace wall,
prediction-registered) comes after → [`SYNTHESIS-RECONSIDERED.md`](SYNTHESIS-RECONSIDERED.md).
