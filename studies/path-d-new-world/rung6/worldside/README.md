# Path D Rung 6 — the WORLD-SIDE half (9013 → field 30950)

Two scripts that make world **9013** exit to a real field. Both are **authored and offline-verified
only** — nothing in this directory has been run against the game install in write mode.

| | |
|---|---|
| **Trigger cell** | `(13, 17)` → block `(6, 8)`, tag **`0x9135`** |
| **Destination** | `Field(30950)`, with `GLOB[1062] = 9013` |
| **Armed patch** | 14 walkable triangles, world x `418…432`, z `-560…-548` |
| **Landing** (field-side half's problem) | `(425.0, 3.2, -479.0)` face `224`, 81.3u from the trigger |
| **Files touched** | 7 × `EVT_WORLD_WORLD13.eb.bytes` + 1 × `Block[6][8] Terrain.ff9mesh` |

Coordinates come from `../site.json` (the site-selection survey). Do not re-derive them by hand.

---

## What the player experiences

Walking onto the armed grass patch on foot raises the FF9 **“!” action-prompt bubble** — the same
cue every real overworld town uses — and nothing else happens while you stand there. **Pressing
Confirm** locks movement and the menu, fades the screen to black over 24 frames, stamps the
world-map arrival sentinel, and loads field 30950.

### The body, opcode by opcode (93 bytes, disassembled from the live spliced file)

```
  0  EXPR  Map.Byte[24] == 100  AND  NOT Global.Byte[190]   ; HUD idle AND on foot
 12  JZ  +77 ─────────────────────────────────────────────► RET   ; in a vehicle / HUD busy: inert
 15  Bubble(1)                                              ; the "!" FICON over the player
 18  EXPR  B_KEYON(EventInput.Confirm)
 26  JZ  +63 ────────────────────────────────────────────►  RET   ; not pressed: just show "!"
 29  DisableMove ; DisableMenu ; CloseWindow(6) ; CloseWindow(7)
 37  RunWorldCode(32,75) ; RunWorldCode(41,0)               ; PSX music fade / leftover — Memoria no-ops
 47  FadeFilter(2, 24, 255,255,255)                         ; SUB toward white == fade to BLACK
 55  Wait(25)
 58  D8:2 = 9999                                            ; "arrived from the world map" sentinel
 66  <ready poll on B_SYSVAR(200)>                          ; constant 0 on Memoria — exits at once
 79  GLOB[1062] = 9013                                      ; worldexit.WORLD_STATE_VAR
 88  Field(30950)
 92  RET
```

Every piece is `entrance.entrance_func_body_direct(30950, world_state=9013, prompt=True, …)` — the
kit primitive, not hand-assembly. Three things are worth knowing about it:

- **The fade is before `Field()`**, which is the rule (`project-ff9-gateway-regions`). Without it the
  destination loads in the clear and the player watches the smooth-cam settle.
- **`D8:2 = 9999`** makes the destination's `[[player.arrival]]` dispatch see the real
  “came from the world map” value instead of a stale last-gateway entrance.
- **Opcode `0x2B` is `Field`.** `0x2A` is `Battle`; the script refuses to write a body containing it.

---

## Orchestrator invocations

Run everything from `ff9mapkit/` so the local package shadows any installed copy.

```
cd C:\gd\Dream-World-IX\.claude\worktrees\path-d-rung-6-handoff-e2535a\ff9mapkit
set W=C:\gd\Dream-World-IX\.claude\worktrees\path-d-rung-6-handoff-e2535a\studies\path-d-new-world\rung6\worldside
```

### 1. Dry-run both (writes nothing, creates nothing)

```
py %W%\splice_exit.py --dry-run
py %W%\arm_tiles.py   --dry-run
```

Both currently exit **0** against the live install. Read the two `RESULT:` lines before proceeding.

### 2. Deploy — one shared backup dir, so one revert command undoes both

```
py %W%\splice_exit.py ^
   --backup-dir C:\gd\Dream-World-IX\backups\rung6-worldside ^
   --report %W%\..\rung6_splice_report.json --log %W%\..\rung6_splice.log.txt
py %W%\arm_tiles.py ^
   --backup-dir C:\gd\Dream-World-IX\backups\rung6-worldside ^
   --report %W%\..\rung6_arm_report.json --log %W%\..\rung6_arm.log.txt
```

Omit `--backup-dir` and each script mints its own timestamped dir under
`C:\gd\Dream-World-IX\backups\`. Backups go to the **main repo**, never this worktree — a worktree
is deleted when its branch merges and would take the only copy of the pre-edit bytes with it
(`project-ff9-worktree-parked-backups`).

Both scripts are **idempotent**: re-running is a no-op (`mode=already-current`, 0 triangles changed).

### 3. Revert

```
copy /Y "<backup>\eb\<lang>\EVT_WORLD_WORLD13.eb.bytes"  "<game>\FF9CustomMap-world\StreamingAssets\assets\resources\commonasset\eventengine\eventbinary\world\<lang>\"
copy /Y "<backup>\mesh\Block[6][8] Terrain.ff9mesh"      "<game>\FF9CustomMap-world\FF9_Data\WorldMap\Disc9\0_1\r8\"
```

`<backup>/manifest-eb.json` and `<backup>/manifest-mesh.json` carry the source path and sha256 of
every parked file, so a revert is verifiable. The mesh backup restores the owner-accepted bench
block byte-for-byte (md5 `0a25f3e4…`, `bench_manifest.json`).

`arm_tiles.py` also leaves `<name>.bak-<ts>` beside the deployed mesh (`deploy_override`'s own
backup) — a second, independent copy.

### 4. Verify offline again at any time

```
py C:\Users\skaki\AppData\Local\Temp\claude\...\scratchpad\worldside_verify\run_verify.py
```

Stages a scratch game root from the live files, runs both scripts against it in real write mode,
and asserts the whole chain. Exit 0 = green.

---

## Hot-reload story

| Change | Reload with | Why |
|---|---|---|
| `Block[6][8] Terrain.ff9mesh` | `~ → World → Reload overworld on state` | Loose `.ff9mesh` overrides are re-read on every world load (s34 `WorldMeshOverride`). ~1s iteration. |
| `EVT_WORLD_WORLD13.eb.bytes` | same | The world dispatcher `.eb` is loaded with the world state; re-entering 9013 re-reads it. |
| **Registration** — `WorldScene 9013`, `DictionaryPatch`, `FolderNames`, `BattlePatch`, a DLL rebuild | **RELAUNCH** | Read once at launch. |

Rung 6 changes **content only** — the `WorldScene 9013 WORLD13` registration line already exists.
So: **no relaunch needed for this half.** Field 30950 is the field-side half's problem, and the
*first* deploy of a new field id does need a relaunch to register its DictionaryPatch line.

---

## What was verified offline, and how

Harness: `scratchpad/worldside_verify/run_verify.py` → `verify_log.txt` (0 failures).

**`.eb` splice, all 7 locales**
- Each locale patched **its own base**: us/uk/es/fr/gr/it 9348 B → 9445 B, **jp 9336 B → 9433 B**,
  every one `+97`. All 7 pre-images have distinct sha256 except us/uk; the 84-byte PSX name region
  is byte-identical before/after in each file. Nothing was cloned across locales.
- The spliced body is byte-identical in us and jp (the *bytecode* is language-independent; the
  *files* are not — that is exactly the distinction `load_all_dispatchers` warns about).
- Structural walk: **96 → 97 functions, 0 ragged, before and after.** (The 16 zero-length stock
  functions are classified `empty`, not `ragged` — they are a legitimate WORLD11 shape.)
- `size_delta == body(93) + 4` (the new func-table slot). Entry count stable at 23. Every other
  function in the file byte-identical, addressed positionally. u16 headroom 56 KB of 64 KB free.
- **`eb-src` accepts the spliced file** (`exit 0`; `write_source` raises on any deviation, so this
  is an independent byte-exact round-trip). Diff vs the pristine decompile is exactly two things:
  entry 0's `raw=` blob (object-0 is kept verbatim — “non-canonical func table”), and the parked
  empty slots 15–22 gaining an explicit `off=8828` because the bodies moved and theirs did not.
  Both round-trip; neither is damage.

**Tile arming**
- Write path asserted to be the **sentinel-disc** one (`Disc9`, no `Disc1`/`Disc4` segment anywhere).
- Geometry proven untouched: verts / normals / uvs byte-identical, `vcount` stable at 3444, only
  `tangent.x` written, 42 vertex rows = 3 × 14 triangles. `validate_blockmesh` (the engine's own
  loader predicates + the UNINDEXED CONTRACT) passes.
- Armed geometry's full 3-corner bbox lies inside cell (13,17)'s 32u footprint, so no armed corner
  can fire a cell tag that matches no function.
- Read-back: re-decoded the written file, 14 triangles carry `event=1`, byte-identical to what was
  serialized.

**Guards proven able to fail** (an unexecuted guard is not a guard):

| Guard | Broken how | Result |
|---|---|---|
| locale file present | `--eb-name EVT_WORLD_NOPE` | refused, exit 2 |
| retarget disc inside the cell | `--center cell --radius 20` | refused, exit 2 |
| bench freshness | armed block + changed params | refused, exit 2 |
| stale arming | `--center 440,-550 --radius 5` over an armed block | refused, exit 2; `--disarm-stale` clears 14 and passes |

---

## The disc-4 mirror question (asked explicitly)

**`deploy_override` does not call `discmirror.auto_mirror`.** The mirror is an explicit post-step
that each CLI verb runs for itself (33 call sites; `cli.py:3842`, `island.py:1059`, `terrain.py:171`,
…). `arm_tiles.py` deliberately does not run it.

Even if it did, it would be a no-op: `auto_mirror` refuses any source disc outside
`_REAL_DISCS = (1, 4)` — `discmirror.py:189-192`, *“a synthetic override namespace is deliberately
unmirrored”*. That refusal was added precisely because a Disc9 → Disc4 mirror would recreate the
collision engine patch s74 exists to prevent. So there is no mirror to suppress on this path, and
that is true both by omission and by the kit's own guard.

---

## Residual risks

1. **`Map.Byte[24] == 100` is half the trigger's gate.** The template's own gate requires the world
   HUD to be idle. Any machinery that leaves `Byte[24]` off 100 disarms the trigger — this is the
   coupling that blackscreened the nameplate lane three times. We are *not* summoning the nameplate,
   so `Byte[24]` should sit at the idle 100, and this is the shipped configuration proven in-game
   (waystation 6500, 2026-07-13). **If the “!” never appears, suspect this first**, and the fix is
   the `nameplate=True` variant of the same primitive, which swaps in an on-foot-only gate.
2. **The site's own openness screen fires on this cell** (40.3% blocked). The site agent's judgement
   is that the note's window is the whole 32u cell, which overhangs the south shore, and that every
   lawn cell on a ~90u ring island trips it. The 12u armed patch itself is 100% grass. I did not
   re-litigate this — but it is the one measurement that disagrees with the plan, so if the
   playtester reports getting stuck near the trigger, that note called it.
3. **The live `.ff9world.jsonl` ledger does not exist yet** in `FF9CustomMap-world`. That means
   `deploy_override`'s ownership refusal is in its permissive bootstrap mode and will **not** protect
   this first write. The `bench_manifest.json` freshness gate is what actually guards it — and as of
   this writing block (6,8) still md5-matches the accepted bench. **Re-run the dry-run immediately
   before deploying**; 5 of the 7 Disc9 clusters were rewritten by other sessions on 2026-08-04.
4. **Only the trigger cell's tag is added.** Cells adjacent to the armed patch are not armed, so a
   player who leaves the patch loses the “!” — intended, and how real entrances behave.
5. **The 8 non-walkable (topo 59) triangles inside the retarget disc are deliberately left unarmed.**
   Arming them is inert (the player cannot stand on a non-walkable triangle, so its IDALL is never
   the hit triangle), but it is surface minted for nothing. `--no-walkable-only` restores the plain
   `retarget_tiles` behaviour if a playtest ever suggests coverage is short.
6. **Field 30950 must exist and be registered before the trigger is used.** A `Field()` to an
   unregistered id is the classic null-`.eb` black screen. That is the field-side half's contract.

---

## Files

| Path | What |
|---|---|
| `splice_exit.py` | the `.eb` splice, 7 locales, with the full verification pass |
| `arm_tiles.py` | the tile arming + `deploy_override`, with the freshness / stale / geometry guards |
| `_common.py` | shared roots, backup convention, structural-walk + disassembly helpers |
| `armed_manifest.json` | positive record of the md5 this script produces from the accepted bench |
| `../site.json` | the site-selection survey (authoritative coordinates) |
