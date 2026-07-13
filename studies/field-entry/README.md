# Field entry — spawn points & entry settle (investigation, 2026-07-13)

> **STATUS: RUNGS 1+2 ★ IN-GAME PROVEN (2026-07-13).** The ARRTEST playtest matched the authored
> table exactly — default spawn facing WEST ("good"), and both doors landed the player at the
> authored coordinates; the only defect was this study's own front/back PROSE, which had the depth
> axis inverted (the user caught it: "might've just been cardinal mixup" — it was; **FRONT = toward
> the camera = NEGATIVE z**, `FloorFrame zb=+257/zf=-1931`, labels fixed everywhere). Bonus proof:
> a self-loop `Field(<own id>)` gateway reloads the field cleanly, so one field can test its own
> arrival table. **RUNG 3 BUILT (same day, offline-complete):** the campaign-graph entrance audit —
> `campaign.lint_campaign` (g2) walks `plan.edges` (which already carry `entrance`) + `entry_entrance`
> and warns on the COLLAPSE (distinct inbound entrances, no rows), SAME-ENTRANCE ambiguity (doors the
> destination can't tell apart), PARTIAL coverage (an inbound entrance falling through to default),
> and DEAD rows (an entrance never routed); verbatim members are exempt (donor table carried) and
> rows on one are flagged IGNORED (the verbatim composition never reads `[player]` face/arrival —
> verified against `compose_verbatim_eb`). Field-local `build.lint_player_arrivals` (in `lint_all`)
> flags verbatim dead keys + uncovered self-loop entrances. 8 tests; pure lint, no bytes changed —
> no playtest needed. **RUNG 4 BUILT (same day, offline-complete):** entry_settle honesty — the
> key is now DOCUMENTED (FORMAT.md `[camera]` + the multicam note); `entry_settle` inside
> `[[camera]]` MULTICAM blocks now APPLIES (first nonzero wins — it used to be silently skipped,
> on exactly the scrolling class that needs it most); the build WARNS (once, not per-language)
> when a requested settle can't insert (no plain reveal fade), via a `warnings=` kwarg on
> `build_script` (the compose_verbatim_eb convention); `build.lint_entry_settle` (in `lint_all`)
> flags the verbatim dead-key, boolean/negative/non-integer values, and disagreeing multicam
> values; a non-numeric value (e.g. a future "auto") no longer crashes `int()` mid-build.
> 6 tests. **RUNG 5 BUILT (same day, offline-complete):** arrival-aware import — the new
> `eventscan.scan_arrival_table` ATTRIBUTES each placement to its entrance (`decode_switch` case
> values for the Alexandria-style 0x06 form; if-chain conds for 706/kit forks — so authored tables
> round-trip through the same decoder), and every NON-verbatim import (`import` editable/native/
> borrow/lightweight + `import-chain` members) now emits the donor's table as `[[player.arrival]]`
> rows via one shared `extract._player_block` renderer (verbatim keeps its bare spawn — the donor
> .eb IS the table; no-rows output is byte-identical to the old emitters). Un-emittable rows are
> dropped sane (negative entrance skipped, out-of-compass facing omitted, duplicate entrance keeps
> the LAST block = if-chain semantics); `y` decoded but not emitted (the known gap). Verified live:
> `import 100` emits Alexandria's exact 3-door table (201/204/231 + faces) and lints clean; the
> arrival CLASS is in-game proven (ARRTEST), so no new playtest needed. FORK_FIDELITY #9's
> "a synth fork can't reconstruct the per-DOOR table" caveat is RETIRED. 5 tests. Build facts: `[player] face` (the D9(6) spawn-facing
> const patch) and `[[player.arrival]]` (per-entrance dispatch compiled as field-706-style
> `if (D8:2 == N)` const-override blocks before `CreateObject` — the generalized ladder splice) are
> in the kit with 12 tests; the offline oracle round-trip holds (author → build →
> `scan_player_arrivals` → the same table), arrival rows get the spawn's placement lint, absent keys
> are byte-identical (hut golden green), FORMAT.md documents both, and fork-report's Arrival advisory
> now names the vocabulary. The proof field lives on 4003 (`ARRTEST/` here — a self-loop: two
> edge gateways re-enter the field with entrance 1/2; default spawn faces WEST, the west door lands
> front-right facing NORTH, the east door back-left facing SOUTH). It displaced the coop twin vault from
> the 4003 slot (restore: `py tools/deploy_field.py studies/battle-coop/coopgate/coopgate.field.toml`).
> Rungs 6–7 (the GUI panel, the settle auto-estimator) remain open.
> The rest of this document is the investigation that shaped it.
>
> Original opening framing: this was the gap map for the two halves of
> the field-entry moment: WHERE the player appears (spawn / arrival placement) and HOW the first
> seconds look (entry settle / the camera black-hold). Both features exist today in a half-built,
> telling shape: **the kit models the DEPARTURE side of every transition completely and the
> ARRIVAL side almost not at all** — and neither feature has a real GUI surface. Sources: the kit
> at HEAD (all cites below), the world-hub memory (the entry_settle origin + the open estimator
> question), and the gateway-regions memory (region mechanics).

## Verdict

Both features are important exactly as suspected, and the gap is narrower than it looks: **every
mechanism needed to close the arrival side already ships in the kit** — the entrance-index write,
the conditional-placement splice, the facing emission, and even a byte-grounded *decoder* for the
real per-door arrival tables. What's missing is vocabulary (TOML), one compile step, lint, and any
GUI at all. Entry settle is smaller: it works, but it's undocumented, default-off, hand-tuned by
copying "the hub precedent," and silently no-ops in several cases. The single highest-value build
is the **per-entrance arrival table** (`[[player.arrival]]`) — it closes a named FORK_FIDELITY gap
(`docs/FORMAT.md:680` already calls per-door spawn "a separate gap") and makes multi-door custom
fields feel like real fields for the first time.

---

## Feature 1 — spawn points

### The engine mechanism (complete map)

A cross-field transition is a two-sided contract on one save-backed variable, **`D8:2`** — the
field-entrance index (`FIELD_ENTRANCE_IDX`, `ff9mapkit/ff9mapkit/content/region.py:53`):

- **Departure (the kit does this everywhere):** the exit writes `D8:2 = <entrance>` immediately
  before `Field(target)`. The field-109 gateway template bakes it at `REL_ENTRANCE = 263`
  (`content/gateway.py:24,58`); choice/event warps thread `entrance=` (`content/event.py:80-106`);
  ladder tops (`top_entrance`), platforms (`warp_entrance`), journey edges, and the hub's
  `[[journey]] entrance` all carry it (`hub.py:104,418-419`, `campaign.py:903-908`).
- **Arrival (real fields only):** the destination's player Init reads `D8:2` (`05 D8 02 7F`) into
  a `0x06 JMP_SWITCHEX` and branches to one placement block per entrance — `SetVar D9(0)=x,
  D9(4)=z, D9(6)=facing` (+ `TurnInstant`). The kit already *decodes* this pattern byte-for-byte:
  `eventscan.scan_player_arrivals` (`eventscan.py:1152-1194`). Real examples: Alexandria Main
  Street (field 100) has **4** arrival blocks; the Dali weapon shop has 2; field 706 (the
  Gizamaluke vine) uses the `if (D8:2 == N) { placement }` conditional form in its player Init.

**The asymmetry:** the kit's synthesized player Init **never reads `D8:2`**.
`npc.set_player_spawn` (`content/npc.py:300-309`) patches exactly two constants — `D9(0)` x and
`D9(4)` z. So every gateway arriving at a synthesized field, whatever entrance value it faithfully
wrote, lands the player at the *identical* spot. The fork-report even tells the user this
("Arrival: N per-door spawn points … a SYNTH fork uses one `[player] spawn`",
`forkreport.py:965-967`) — it reports a table the kit gives you no way to author.

The one kit-emitted conditional arrival is ladder-specific: `ladder.inject_reentry_spawn`
(`content/ladder.py:577-633`) splices `if (D8:2 == entrance) { on-vine placement }` right after
`DefinePlayerCharacter` — jump-safe, in-game proven, faithful to 706. **The general mechanism is
proven; only the general vocabulary is missing.**

### Current inventory — logic

| Piece | State |
|---|---|
| `[player] spawn = [x, z]` | The only arrival primitive. No facing, no Y, no floor id (`build.py:4811-4814`). |
| Facing at spawn | **Absent for the player** — NPCs get `D9(6)` + `TurnInstant` (`content/npc.py:117,133`); ladders (`face_angle`) and worldmap arrivals (`arrive_face`) get facing; `[player]` does not. |
| Per-entrance dispatch | Ladder re-entry only (`inject_reentry_spawn`). `set_player_spawn` even carries an unused `entry_index` param — the plumbing anticipates more. |
| Campaign/import | `import`/`import-chain` **collapse the donor's real per-door table to one spawn** (nearest the visible centroid, `extract.py:1053-1063`) on non-verbatim forks. `remap_fields` retargets `Field()` literals only, never `D8:2` writes (`content/verbatim.py:25-39`) — right for verbatim↔verbatim, and exactly why a synth member ignores the routed entrance. |
| Lint | Spawn on-mesh + near-edge advisory (`build.py:2667-2677`). Nothing entrance-aware; no "all doors land at one spot" audit. |
| Docs | `FORMAT.md:191` documents `spawn`; `FORMAT.md:680` names per-door spawn as "a separate gap". |

### Current inventory — GUI

| Surface | Spawn | Notes |
|---|---|---|
| Blender add-on | **The only authoring surface.** One `FF9_Spawn` empty (`blender/.../ops.py:1160-1179`), position only — the empty's rotation is ignored, exports `[player] spawn=[x,z]` (`bridge.py:582-584`), round-trips on import, drawn as a green star in the paint overlay. | No facing, no per-entrance markers, by design one marker. |
| Workspace field tree | **Absent.** No `player`/`camera` section in `_SECTION_SPEC` (`workspace/shell.py:132-136`); the "Camera (Blender)" node is a dead-end placeholder ("author them in Blender", `shell.py:3646-3649`). The map view doesn't render the spawn. | The Import tab *shows* the fork-report arrival advisory — read-only prose. |
| Form editor (`ff9mapkit edit`) | **Absent.** No PLAYER/CAMERA spec (`editor/forms.py:52-254`). `GATEWAY_SPEC` exposes `to` + `entrance` — the departure half only (`forms.py:77-86`). | |

### What a user cannot express today

1. **Different arrival spots per door** on any synthesized/non-verbatim field (THE gap).
2. **Facing at spawn** — you always appear in the template's default orientation.
3. **Y / floor** — `[x, z]` cannot disambiguate XZ-overlapping floors.
4. **A campaign-routed entrance honored by a synth member** — the entrance index arrives and is ignored.

### Proposed vocabulary (design sketch — grounded, not landed)

```toml
[player]
spawn  = [0, -2000]     # unchanged: the default arrival (unmatched entrances)
facing = 6144           # NEW: D9(6) + TurnInstant — the consts NPCs already get

[[player.arrival]]      # NEW: per-entrance dispatch
entrance = 2            # matches the [[gateway]] entrance= the source field wrote
pos      = [430, -880]
facing   = 4096         # optional
# y      = 0            # optional, multi-floor disambiguation
```

Compile shape: chained `if (D8:2 == N) { placement }` blocks spliced after
`DefinePlayerCharacter` — **exactly the proven `inject_reentry_spawn` splice** (also 706's real
byte shape; handles sparse entrance ids; avoids re-deriving the `0x06` switch encoding).
Verification is a closed loop the kit already owns: **`scan_player_arrivals` becomes the offline
oracle** — author → build → scan → the same table comes back.

### Rungs (incremental, verbatim-first)

1. **`[player] facing`** — smallest rung; byte-parity with the NPC Init consts; one in-game check.
2. **`[[player.arrival]]`** — the dispatch table; scan round-trip test + in-game proof on 4003
   (two doors → two distinct arrivals + facings).
3. **Lint** — (a) each arrival on-mesh (reuse the existing spawn check per row); (b) the campaign
   graph audit: inbound edges whose `entrance` has no matching arrival → "all doors land at one
   spawn" warning.
4. **Arrival-aware import** — non-verbatim forks emit the donor's REAL table as
   `[[player.arrival]]` rows instead of collapsing it (extract already decodes it). Directly
   closes the FORK_FIDELITY arrival line.
5. **GUI** — Blender: numbered arrival markers (entrance property; facing from the empty's Z
   rotation — the marker already exists, this generalizes it). Workspace: a "Player & entry"
   section in the field tree (spawn/facing/arrivals/entry_settle are logic-adjacent scalars — they
   fit the form model; only the *position picking* is spatial and stays in Blender/map-view).

---

## Feature 2 — entry settle

### Mechanism (works, proven)

`content/entry_settle.py` inserts `DisableMove ; Wait(n) ; EnableMove` before Main_Init's first
integer-mode reveal fade, so the engine's universal smooth-cam (`CenterCameraOnPlayer`, scaled by
the user's `CameraStabilizer` ini) converges behind the still-black screen. It is the same
black-hold the real game performs naturally (the world-hub memory's deep-why: real fields fill the
pre-reveal time with title cards + cast setup; a bare synth field reveals ~130 bytes in). The
source-side complement is the warp fade (`event.warp(fade=True)` / the gateway template's
`WARP_FADE`) — a destination can only settle behind black if the source faded to black.

### Current inventory

- `[camera] entry_settle = <frames>` — manual, **default OFF** (`build.py:4828-4836`); the
  `ff9mapkit new` scaffold omits it entirely (`pack.py:83-125`).
- `[hub] entry_settle` — the ONE auto-application, default 45 (`hub.py:72,116,381-382`).
- fork-report advises `= 45` for **scrolling synth forks only** (`forkreport.py:930-941`) — the
  only surface that ever suggests it, shown as read-only prose in the Workspace Import tab.
- **Not documented in `FORMAT.md` at all.** No GUI anywhere (Workspace, form editor, Blender: zero).
- In practice authors copy values by hand — `examples/continent-v1/waystation.field.toml:35`
  carries `entry_settle = 45  # (the hub precedent)`.

### Gaps

1. **The value is a guess.** The world-hub memory logs the open estimator:
   `entry_settle ≈ bind_delay + ln(delta) / −ln(CameraStabilizer/100)` where `delta` = the spawn's
   projected offset from the camera's null-player home — computable from the kit's own projection
   math (`scene`/`cam`). Catch: `CameraStabilizer` is per-user ini (best-effort for the default 85).
2. **Discoverability.** Default-off + undocumented → every author rediscovers the drift. The
   fork-report rule (scrolling camera + synth entry ⇒ suggest) exists but never reaches `lint_all`,
   and brand-new fields (not forks) get no advisory at all.
3. **Silent no-ops.** `wait<=0`, no reveal fade, or an expression-mode fade → the input is returned
   unchanged with no warning (`content/entry_settle.py:29-47`). A user who *asked* for a settle
   should hear that it didn't apply.
4. **Two hand-coordinated halves.** `fade=true` (source) and `entry_settle` (destination) must both
   be right; there is no single lever or cross-check.
5. **Bounds worth keeping (not bugs):** verbatim forks carry the donor's real entry sequence
   (settle unneeded); the bare F6 warp cannot be helped by any script (no black to hide behind).

### Rungs

1. **Docs + honesty** — add `entry_settle` to `FORMAT.md` `[camera]`; build-time warning when it was
   requested but couldn't apply. (Tiny.)
2. **Lint advisory** — generalize the fork-report rule into `lint_all`: scrolling camera + synth
   Main_Init + large spawn↔camera-center delta + no `entry_settle` → suggest a value.
3. **`entry_settle = "auto"`** — the projection estimator (the research rung; calibrate against the
   proven hub 45–60 and the waystation 45).
4. **GUI** — lives in the same Workspace "Player & entry" section as spawn/facing (rung 5 above).

---

## Combined ranked worklist

| # | Build | Size | Why first |
|---|---|---|---|
| 1 | `[player] facing` | XS | Parity the NPCs already have; unblocks arrival rows carrying facing. |
| 2 | `[[player.arrival]]` per-entrance dispatch | M | THE feature; closes the named FORMAT.md/FORK_FIDELITY gap; decoder-as-oracle test loop. |
| 3 | entry_settle docs + silent-no-op warning | XS | Cheapest honesty win. |
| 4 | Lint: arrival audit + settle advisory | S | Makes both features discoverable without GUI work. |
| 5 | Arrival-aware import (real tables on synth forks) | M | Fork-fidelity: forks stop collapsing per-door arrivals. |
| 6 | Workspace "Player & entry" section + Blender arrival markers | M | First real GUI surface for both features. |
| 7 | `entry_settle = "auto"` estimator | M/R | Research rung; the world-hub open question. |

## Open questions

- **Switch vs if-chain:** compile `[[player.arrival]]` as the 706-style if-chain (proven splice) or
  the Alexandria-style `0x06` switch (byte-denser, matches the most common real shape)? Recommend
  if-chain first — verbatim-grounded and already shipping in the ladder path.
- **Umbrella block:** spawn, facing, arrivals, `entry_settle`, `hide_area_title`, `[[on_entry]]`,
  `[startup]` are all Main_Init-adjacent "entry moment" primitives. Worth a unifying `[entry]`
  umbrella someday? (Not now — the pieces should land individually first.)
- **`[[gateway]] to="worldmap"`** already has the richer arrival model (`arrive=` + `arrive_face`,
  the ARRIVAL-CLEARANCE law) — the field-side proposal deliberately converges on the same nouns.
