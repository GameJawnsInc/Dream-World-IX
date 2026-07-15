# HANDOFF — the MOUNTAIN / INTERIOR-TOPOGRAPHY arc (state + next steps)

> **Status: the mountain arc is CLOSED and in-game proven.** This file replaces the original
> productization brief (all 3 of its tasks — productize `world-mountain`, the gore-panel re-run, the
> alcove camera zoom — are closed; see §5). Everything below is the durable state a fresh session needs.
> Last updated 2026-07-15. Deep detail: memory `project-ff9-overworld-interior-topography`,
> `studies/overworld-topography/README.md`, `ff9mapkit/docs/OVERWORLD_ENGINE.md`, `git log`.

---

## 1. What ships now

**`world-mountain`** — carry a REAL rock massif onto a DEPLOYED kit island:

```
ff9mapkit world-mountain --mod-folder FF9CustomMap-world --near WX,WZ [--center WX,WZ]
                         [--donor BX[-BX1],BY[-BY1]] [--reach 96] [--disc 1] [--dry-run]
ff9mapkit world-island   --mod-folder M --center WX,WZ --radius R --seed S [--ground grass|desert]
ff9mapkit world-mirror   --mod-folder M          # ALWAYS after a custom-ocean deploy
```

**Qualified donors** (each measured by its own anatomy pass — never add one unmeasured):

| donor | `--donor` | class | proven |
|---|---|---|---|
| Uaho | `0,0` | small: terrain + OBJECT-aperture plug + alcove floor | ★ in-game (byte-identity oracle) |
| Crag | `10,5-6` | cross-block, no apertures, own tile band, desert feet | ★ in-game ("looks verbatim") |
| Daguerreo horseshoe | `5-6,15-16` | ENSEMBLE: hanging bowl + animated falls/river + object collar | ★ in-game (3 rounds) |

**Ground families** (`--ground`, `grassland.GROUNDS`) — THE TRANSLATION LAW IS UNIVERSAL (the
2026-07-15 census, `ground_families_anatomy.py`): grass (bit-frozen identity) · desert (topo 17; mains
`+(0.65332, −0.09863)`, wall `+(−0.27127, −0.02066)`) · scrub (topo 4; `+(0.25977, −0.06738)`; the
grass↔dirt ecotone set; borrows the desert wall) · brush (topo 38; `+(0.45703, −0.20215)`; its stock
wall IS the desert wall) · snow (topo 27; `+(0.0, −0.33691)`; icy wall `+(−0.44021, +0.05161)`) · canyon
(topo 45; `+(0.7793, −0.31641)`; red wall `+(−0.69509, −0.49722)`) · dunes (topo 41; `+(0.38964,
−0.13477)`; its OWN set — the family-model exception; borrows the desert wall). Sampler round 1
(2026-07-15) added the stock-role CLASS axis (`GROUNDS[..]["cls"]`): grass/desert/snow/canyon ★
island-class (canyon verbatim-compared at (486,−678) — "alright"; verbatim mixes more lighter browns =
the vocabulary-share axis, earmark-only) · scrub =
TRANSITION (seam strips only — filled it's a tiling mismatch; macro-tile parity falsified) · brush =
SLOPE (flat fills read as canopy) · dunes = INTERIOR (no native coast). Sampler islets — see §3.

## 2. The two identity oracles (run these after ANY change to the carve/mint)

```
py studies/overworld-topography/mountain_productize_check.py     # Uaho bench, byte-for-byte
py studies/overworld-topography/interior_productize_check.py     # island E forest+hill
py -m pytest -n 6 -q          # from ff9mapkit/ ONLY (repo root picks up tools/*.py as tests)
```
TRACK A of the mountain check must print IDENTICAL. Every law below was added *through* these oracles —
they are the reason the Uaho/crag deploys never regressed. `ff9mapkit extract-templates` first if the
suite reports missing fixtures.

## 3. Live benches (all in FF9CustomMap-world, disc-4 mirrored)

| bench | island | massif | teleport |
|---|---|---|---|
| Uaho (grass) | r31 seed 42 @ (160,−1246), blocks (2,18-19) | (162,−1246) | (136.5, −1245.5) E |
| Crag (DESERT) | r50 seed 11 @ (64,−1216), blocks (0-1,18-19) | (70,−1218) | (30.5, −1217.5) E |
| Horseshoe (ensemble) | r72 seed 42 @ (1280,−1184), blocks (18-21,17-19) | (1288,−1190) | (1227.5, −1189.5) E |
| Desert check island | r52 @ (768,−1216), blocks (11-12,18-19) | — (pure plain) | — |
| THE GROUND SAMPLER (5 islets, r22 seed 11, row 19) | scrub (480,−1248) (7,19) · brush (608,−1248) (9,19) · snow (864,−1248) (13,19) · canyon (992,−1248) (15,19) · dunes (1120,−1248) (17,19) | — | teleport to each centre |

Uaho's pristine mint is preserved game-side as the deployed file's `.pristine-r31s42` sibling (the
identity oracle's TRACK A input). New blocks need a world re-entry; disc 4 needs a relaunch.

## 4. The laws this arc minted (all engine- or byte-grounded)

- **THE CARRY LAW / ROCK-RIGID** — carried rock never deforms beyond the global affine (de-tilt + DY);
  ALL seating deformation goes to the GRASS (a donor-shaped pure-Y apron over `gblend`).
- **THE WELD-SAFE LIFT** — worldmap meshes don't share vertex entries: lift per POSITION, apply to every
  coincident entry, taper only at borders facing NON-span blocks.
- **THE DONOR-DISPATCH STRIP** — a carried IDALL keeps topograph+flags, drops donor event/area (area
  feeds `w_cameraArea2Place` → the alcove camera zoom; event 1-3 = a latent place-entrance trigger).
- **THE ENSEMBLE-APERTURE LAW** — a big massif's extra ring is the river/falls MOUTH, owned by the UNION
  of Object/Falls/River/RiverJoint verts. Uaho's object-only aperture (→ plug) is the SMALL-mountain
  special case. Ensemble rings get NO plug: the parts carry and cover the hole as stock does.
- **THE FOOTPRINT SWEEP** — every donor terrain tri centroid-inside the rim rides VERBATIM *outside* the
  ring accounting (tunnel linings, weld-isolated shingles). Free shingles touch the sheet at one vertex
  → they break manifold chaining by nature. Empty on Uaho/crag.
- **THE WALK-LEGALITY LAW** — the ground query reads the hit tri's `tangent.x` as the IDALL for MOVEMENT
  legality: `(id & 0xFC) >> 2` indexed into a per-vehicle 64-bit mask (`ff9.cs
  w_movementCheckTopographID`; foot `{0x0010667F, 0xD8FF3CFF}` — blocks 49/58, walks 0/13/17/37).
- **THE SCENERY SEAL** — worldmap shaders never consume tangents, so carried aux parts store a
  blocked-topo IDALL (49) in that channel: look-but-don't-touch scenery = stock's own semantics.
- **THE FREE-RIDE TRAP** — the s34 sidecar loads the donor's WHOLE prefab; un-overridden parts render
  verbatim. Deploy BLANKS for every ensemble part on every span block + a `Donor.txt` divert to a donor
  block carrying all deployed part transforms.
- **THE DEAD-RELIEF DISCOVERY** (other session) — `world-island`'s rolling relief never applied away from
  block (0,0); flat interiors are in-game approved up to r52; the field is RETIRED (resurrection spec in
  the studies README).

## 5. Closed / parked — do not re-explore without a new idea

- Original brief's tasks: `world-mountain` productized ★ · the gore-panel probe REJECTED unconfounded
  (statistics reproduce the law's parameters, never the painted look — THE FORM LESSON at panel scale;
  needs a new *measurement* idea, not a re-fit) · the alcove camera zoom FIXED ★.
- From-scratch massif SYNTHESIS — falsified over 8 rounds (`massif_synth.py` is the record).
- THE DESERT TILE FIDELITY CHECK — CLOSED, neither gap reads at scale ("a fine desert"); if desert ever
  needs more, the lever is a patch-VOCABULARY sampler (stock is only ~32% mains), not window phase.
- A walkable hanging bowl — declined by the user (scenery-only = stock); it would be a designed terrain
  path, not a carry fix.

## 6. Next steps (the menu, roughly by value)

1. **More ground families via the translation law — ★ DONE incl. the sampler playtest 2026-07-15**
   (see §1; the law is universal, `GROUNDS` grew 5 families + the CLASS axis, dirt 19/20 byte-proved
   the family model, dunes/41 is the exception with its own set; names brush/dunes chosen by the user).
   Remaining crumbs only: dirt-16's structure if the dry-lakebed look is ever wanted; the
   vocabulary-share earmark (stock grounds are only partly mains — desert precedent says it may never
   read at scale).
2. **A desert beach — rung A ★ DONE offline 2026-07-15** (THE BEACH TRANSLATION LAW: topo-32 desert
   sand = the grass band +335 u-texels w/ own v pins; `coastmorph.SAND_BANDS`, every beach verb
   family-keyed, desert proven on all 15 real blocks; + THE ABSENT-PART LAW fix in morph_in_place).
   **THE FIRST MINTED DESERT BEACH is ★ DEPLOYED (playtest pending)**: real block (16,5), teleport
   ≈ (1074,−336), the block's own real beach at (1061,−358) = the built-in A/B; disc 1 only. The
   island-B transplant path is CLOSED by census (no self-contained desert landmass exists in stock);
   the in-place frame failure was diagnosed as part re-labeling and dissolved by THE SWASH LEVER
   (3.8 keeps the wash re-band in-cell). The remaining prize = the LADDER MINT (sea5/sea1/wash over
   open sea4) that gives OUR minted islands beaches. → the coast-mosaic memory ("THE DESERT BEACH").
3. **A composed showcase island** — the pieces (island + mountain + forest + hill + entrance +
   waystation field) have never been assembled into ONE designed place. This is where the arc's tools
   turn into content.
4. **`--ground` on `world-forest`/`world-hill`** — cheap plumbing (forest is grass-native in stock, so
   arguably skip); hills on desert islands is the real want.
5. **Mint robustness** — the r69-r72 sweep showed shape-gate/sliver sensitivity per seed; the adaptive
   density + >8u refinement fixed the cases we hit, but a systematic large-radius seed sweep would tell
   us whether big islands are dependable.
6. **Engine (s37) candidates, both cosmetic + user-side**: the ~30px-west minimap icon bias; the F6
   disc-switch not arming the navi map; `SelfTestOffset` for the coop east-door bias.
7. **Coop state-mirror** — Phases 0-5 landed on master (wire v6); gated on the two-machine session
   (BOTH DLLs must update). User-only.

## 7. Git note (bit me once — check before claiming a merge)

The **main repo `C:\gd\Dream-World-IX` is checked out on `claude/interior-topography-plan-b61671`**, not
`master`. A bare `cd C:\gd\Dream-World-IX && git merge <feature>` therefore merges into THAT branch, not
master (this session claimed "merged to master" several times and was wrong; corrected at the end by
`git -C <repo> fetch . claude/interior-topography-plan-b61671:master`, a clean fast-forward that leaves
the working tree alone). Verify with explicit paths — `git -C <repo> log -1 master` and
`git -C <repo> merge-base --is-ancestor <branch> master` — never by `cd` + `git log` (the tool's cwd
resets between calls).

## 8. Hard constraints (CLAUDE.md §2 — the ones this arc lives by)

- **I cannot see the running game.** Every "look in-game" step is a STOP-and-ask. The offline eye
  (`massif_face_render.py`, `desert_fidelity_eye.py`, ad-hoc Moguri renders) iterates; only finals
  playtest. Ask for MIST OFF on texture verdicts.
- One change per in-game test. Commit freely on a feature branch → `master`.
- Study the real bytes before authoring a mechanic; a law without a measurement is a guess.
- Deploy the overworld ONLY to `FF9CustomMap-world`; `world-mirror` after every custom-ocean deploy.
