# Custom summons — transplant, recolour, reframe

> **Status.** Three surfaces on this page, at three different maturities.
>
> - **Transplant (`[[summon]]`)** — the *mechanism* is hand-built and **in-game proven** (Milestone
>   1b, 2026-07-24 — a user's own skinned model, posed every frame by a stock summon's real 93-bone
>   skeleton, "it works, thomas flies with the dragon's motion": `studies/custom-summons/
>   thomas-swap/m1b/RUNBOOK.md`). The *productized kit surface* around that mechanism (the
>   `[[summon]]` block's schema + validation, the deploy engine, `summon-import`/`summon-deploy`)
>   is landed and test-covered, per the binding Milestone-2 plan (`studies/custom-summons/
>   thomas-swap/m2/DESIGN.md`). Full key reference: [FORMAT.md —
>   `[[summon]]`](FORMAT.md#summon-optional-repeatable). Blender round-trip, step by step:
>   [tutorial 11](tutorials/11-summon-transplant.md).
> - **Recolour in place (`summon-reskin`) and reframe in place (`summon-rescore`)** — promoted
>   from the TIER W study (`studies/custom-summons/tier-w/PLAN.md`) and **cast-proven in-game on
>   TWO stock summons**: Bahamut ef227 (rungs W2–W4: reframed, retimed, and whole-set recoloured,
>   "worked as described" on every cast) and, past the point where the tools were generalised to
>   ANY stock summon (rung W5), Phoenix ef211 (scenery recolour + camera reframe) and Madeen ef251
>   (creature recolour) — all three levers judged in-game a second time on effects the tools were
>   never hand-tuned against. Unlike the transplant lane, these two verbs never swap in a new
>   model: they edit a stock summon's OWN container bytes — palettes for a reskin, camera pose/
>   focal-distance keyframes for a rescore — and ship the result as a mod-folder override plus a
>   self-contained revert script, exactly like every other summon verb. Schema, refusals and the
>   laws behind them are documented on this page (there is no separate FORMAT.md block — a reskin/
>   rescore spec is its own standalone TOML, not a `field.toml` block); step by step:
>   [tutorial 14](tutorials/14-summon-reskin-rescore.md).
>
> **Separate surface, still explicitly out of scope:** *dumping* a summon's raw container to
> stdout/SCRATCH for reading, and *forking* one summon's structure into a brand-new effect
> (`summon-inspect` / `summon-disasm` / `summon-fork`, the study's disassembly-only
> `ef_container.py` reading path + `summons/ef_geom_writer.py`) is a different job with different
> failure modes and stays unshipped (`disasm/TRANSPLANT.md` §2.3). `summon-reskin`/`summon-rescore`
> (this page) and `summon-export`/`summon-rig-ref` (below) are the container-reading surfaces that
> DO ship: they read a stock container to export it or edit it in place, never to fork it into a
> second one.

## What this is

"Wear a stock FF9 summon's real cast — its live bones, its native camera, its damage timing — with
your own model." Not a billboard composited over the fight: the puppet is posed, frame by frame,
from the same skeletal data the real creature uses, so it flies, banks, and scales exactly like
the donor (`disasm/TRANSPLANT.md` §1 — ten iterations of a hand-choreographed rigid overlay were a
proven "fidelity dead end" before this approach).

## The two lanes

| | **hybrid** (default) | **overlay** |
|---|---|---|
| Motion | the donor's real per-frame bones, read live from the running native cast | the donor's motion clips, decoded once to loose `.anim` files in your mod folder |
| Camera / staging | inherited for free — the same `Camera.main` every SFX effect renders through | the overlay host `.seq` nests the donor cast, so the donor's camera + fly-by carry for free; the `.sfxmodel` also ships default anchor curves, and a `[summon.staging]` table replaces them with **authored** Movement/Rotation/Scaling curves + an animation playlist (see *An original summon* below) |
| Engine requirement | **needs the custom `memoria-patches` build** — the s58 `SfxHybridDrive` feature (`studies/custom-summons/thomas-swap/m0/S58-DRAFT.md`); `summon-deploy` **refuses to arm** on a stock engine | **stock Memoria** — the DLL-free rung-7 FileList/`.sfxmodel`/`.anim` route |
| Fidelity | the proven ceiling: real articulation + real staging + real camera | flapping motion only; the clip carries **no** root travel worth naming (every axis of every Bahamut clip ≤246 units — `disasm/TRANSPLANT.md` §3.5) unless you also supply staging |
| `lane =` | `"hybrid"` | `"overlay"` |

Pick **hybrid** unless you specifically need a build without the custom engine — it is strictly
the more faithful lane and is the one that shipped M1b.

## The recipe (one block, no `.eb`)

```toml
[[summon]]
donor  = 227                    # the native summon whose cast we inherit (id or SpecialEffect name)
model  = "thomas_skinned.fbx"   # your retargeted mesh, bone000..092
lane   = "hybrid"                # or "overlay"
```

Everything else — the mint id/name, the private sequence-host id, the hide mask, the overlay-only
staging/clip knobs — has a byte-grounded default. Full table:
**[FORMAT.md → `[[summon]]`](FORMAT.md#summon-optional-repeatable)**.

Two facts worth knowing before you read that table:

- **The cast trigger is NOT this block.** `[[summon]]` emits assets + an engine-arm manifest, not
  bytecode. Firing the cast is the existing ability → effect lane you already use for any command:
  point an `Actions.csv` row's `vfx1` (kit key on `animationId1`, `battle/actiondelta.py:64`) at
  the block's `private_ef` id (`authoring-ff9-battles`). The block's build **reminds** you to do
  this; it never edits `Actions.csv` for you.
- **Never point anything at the donor's own `ef{donor:D3}/` folder.** A `FileList.txt`/`Model`
  line dropped there silently replaces the ENTIRE native cast for that effect id — fatal to the
  hybrid lane, which needs the native engine actually running so the live bone data exists to read
  (`m0/FBX-PATHS.md` §3, "the donor-FileList replacement law"). That's why the block always mints
  a **private, stock-absent** effect id (`private_ef`, default auto-picked from the 24 unused
  `SpecialEffect` slots) to host the sequence + (overlay only) the JSON mesh.

## An original summon — no donor at all (overlay lane)

A transplant *wears* a stock cast. An **original** summon has no donor to wear: you author the cast
yourself. Four optional keys turn the overlay lane into that, and they make `donor` optional:

```toml
[[summon]]
lane       = "overlay"                                     # DLL-free, stock Memoria
model      = "nimbra/6400.fbx"
private_ef = 91                                            # PIN it -- see the warning below
sequence   = "nimbra.seq"                                  # your own PlayerSequence.seq, copied verbatim
manifest   = "nimbra_manifest.sfxmodel"                    # the bare name FileList.txt reveals
clips      = ["emerge.anim", "drift.anim", "strike.anim"]  # authored clips (vs "all"/"none"/indices)
particles  = ["MistWisps.sfxmodel"]                        # sprite models, copied beside the manifest

[summon.staging]                    # the table's PRESENCE selects curve staging
anchor = "target_average"           # caster | target_average | world
start  = 0
end    = 330                        # pin it: your .seq's WaitSFXDone beat depends on it

[[summon.staging.move]]             # -> Movement pieces, in order. Offsets are added to the anchor.
duration = 45
from = [0, -900, 0]
to   = [0,  120, 0]
ease = ["Linear", "SinusOut", "Linear"]
[[summon.staging.move]]
duration = 285                      # `from` omitted -> the engine inherits the previous destination
to   = [0, 190, 0]

# [[summon.staging.turn]]  -> Rotation pieces (ABSOLUTE euler)
# [[summon.staging.scale]] -> Scaling pieces (a scalar `from`/`to` fans out to all three axes)
# [[summon.staging.play]]  -> the Animations playlist: clip = "emerge", speed = 2, repeat = 2
```

With `sequence` set, **nothing stock is read**: no donor `.seq`, no `ef###.bytes`, no drift guard —
so the whole emit runs offline and everything it produces is yours to commit.

The build refuses, rather than shipping something the engine drops in silence:

- **the `.seq` is linted** (`ff9mapkit summon-seq-lint` runs the same checks standalone). An unknown
  operation is dropped by the parser *with no log*, and an unknown argument key is stored and never
  read — so a typo is invisible until a playtest. The linter also refuses `PlayCamera`/`ShiftWorld`
  (inert or harmful — see `studies/custom-summons/rung8-epic/STORYBOARD.md` §2) and checks the
  proven cast laws: no clip-bound wait inside the `PlaySFX…WaitSFXDone` window, no `EffectPoint`
  under a background blackout, a `PlayAnimation: … Anim=Idle` release, `Char=` on every
  `CreateVisualEffect`, and every `SFXModel=`/`SFX=` resolving to something staged.
- **the curves must span `end - start`** on all three axes, every first piece must carry a `from`,
  and an unrecognised `ease` name is refused (the engine silently falls back to `Constant`).
- **`move` and `turn` are required; `scale` is optional.** An omitted curve is never loaded at all, and
  the engine then pins that channel at its constructor seed for the whole cast. For movement and
  rotation that seed is zero — the world origin, and euler `(0,0,0)` written over your FBX's own
  orientation every frame. Scaling alone is seeded to `1` (it is built `asScaling`), so leaving it out
  is a harmless identity scale.
- **`ease` is five names on a creature curve, not seven.** `Turning1`/`Turning2` are **sprite-only**:
  they are the only interpolations that read the engine's `customParam` dictionary, and they read it
  without a null check — which is fine for a particle (it is handed one) and a `NullReferenceException`
  on *every render frame* for an FBX (it is handed `null`). Use `Constant`, `Linear`, `Sinus`,
  `SinusIn`, or `SinusOut`. In a **particle** `.sfxmodel` the two are legal and useful, but only when
  that sprite's `Emission` carries a `ParameterMin0`/`ParameterMax0` pair — without one the dictionary
  is null there too, and `summon-seq-lint` says so.
- **the playlist must cover the window.** There is no loop flag — a short playlist *freezes* the
  model on its last frame — so `repeat` is checked against each clip's real frame count.
- **`anchor = "target"` is refused**: a multi-target cast passes a null target into the position
  setup, every `TargetPosition*` evaluates to 0, and the creature renders at the world origin.

> ⚠ **Pin `private_ef`.** Auto-allocation walks the stock-absent set ascending and lands on **18**,
> whose legacy semantics are *"would apply effect instantly"*. The mild ids are **80 / 84 / 91**.

**File paths are relative to the TOML that declares them** — `model`, `sequence`, `clips`, `particles`
and `textures` all resolve against the field toml's own directory, whether the block is reached through
`lint`/`build` or through `ff9mapkit summon-deploy --from-toml <file>` (which rebases them the same way,
so the verb works from any working directory). Absolute paths are taken as given. Unlike the field's own
asset refs (`[[layers]] image`, `portrait`, …), these are **not** confined to the toml's directory: a
`[[summon]]` block may reach into a sibling folder that owns the artifact.

## Relaunch vs. recast

| change | takes effect on |
|---|---|
| the `3DModel <id> <name>` DictionaryPatch line (first deploy of a new mint id) | **relaunch** |
| the `[SfxHybrid]` ini section (read once at process start) | **relaunch** |
| the s58 engine feature itself (building/deploying the DLL) | **relaunch** |
| the host `ef{private_ef}/PlayerSequence.seq` + the loose model FBX (+ overlay `.sfxmodel`/`FileList.txt`/`.anim`) | **recast** — zero-cache, mod-folder shadowed, re-read per cast |

So the first arm of a new summon costs one relaunch; iterating the model or its motion afterward
does not.

## Arming the hybrid lane — `summon-deploy`

Deploying a `[[summon]]` block's **assets** (the model, the DictionaryPatch line, the host `.seq`)
is a deliberately **separate** step from writing `Memoria.ini [SfxHybrid]` — the ini write mutates
the user's live engine config and is relaunch-gated, so arming is the explicit, confirm-first
`--arm` flag on `summon-deploy` (the same shape as `coop host`: never a silent side effect of
`build`). `ff9mapkit build`/`lint` **validate** a `[[summon]]` block today (schema, lane,
donor/private-ef sanity, the `vfx1` reminder); the CLI verbs `summon-import` (the Blender return
trip) and `summon-deploy` (standalone asset deploy + arm) drive `summons.deploy.stage_import()` /
`summons.deploy.deploy()` — the latter does rows 1/1b/2 always, and (with `--arm`) row 3.

It follows the kit's existing `[Netsync]` writer pattern exactly (`coop.py`), not a new one:
back up `Memoria.ini` first (`coop._backup_ini`, `:352`), rewrite the section in place
(`coop.update_ini_section`, `:294` — survives repeated headers, drops poisoned duplicate keys),
vet every pair for control characters (`coop._check_ini_pair`, `:260`), and print the applied diff
(mirroring `write_netsync`, `:361`). One gate is new and decisive: **before writing `[SfxHybrid]`,
`summon-deploy` string-probes the deployed `Assembly-CSharp.dll` for the `SfxHybridDrive` type
name** (the same presence check `m1b/RUNBOOK.md` §0 used by hand). Absent that string, the running
engine is stock and the hybrid lane **refuses to arm** — "the hybrid lane requires the s58
SfxHybridDrive engine; deploy the custom Memoria bundle or use `lane = "overlay"`." This is the
kit's engine-independence split made executable for summons: a **novel** field still runs on stock
Memoria, but the **hybrid** summon lane requires the custom engine, while **overlay** (DLL-free)
is never gated.

## Provenance, in plain terms

- **A stock summon's own bytes never leave your machine.** `summon-export` / `summon-rig-ref`
  (already shipped — the `_cmd_summon_export`/`_cmd_summon_rig_ref` verbs in `cli.py`) refuse to
  write outside `C:/gd/SCRATCH/summon-transplant/` — no repo path, no mod folder, no install path,
  no `--force` (`summons/export.py`'s `assert_local_only`). This is unchanged by anything on this page.
- **Your own retargeted model is yours.** `summon-import` packages *your* mesh — skinned onto the
  stock rig reference, never containing the donor's own geometry — into *your own* mod folder. Same
  footing as any other verbatim-fork carry: your content, your output.
- **The decoded donor clips (overlay lane) follow the same line.** They deploy as loose `.anim`
  files into your mod folder (yours to ship), but the offline decode that produced them stays under
  `C:/gd/SCRATCH/summon-transplant/`, never committed.
- **The donor `.seq` splice is Square-Enix-derived** (a copy of the real donor sequence with one
  spliced line). It is fetched fresh from *your* install at deploy time, drift-guarded against a
  known hash, and never written back into the repo.

## Design-risk flag — read before you invest in skinning

A humanoid or vehicle mesh riding a **93-node, long-necked flyer's** skeleton poses *correctly*
(every bone goes exactly where the dragon's bone goes) and can still **look wrong** — the donor's
silhouette and yours may simply disagree (a train's rigid flat panels vs. a dragon's flex, a
biped's two legs vs. a quadruped's four). This is a design judgment call, not a defect the kit can
detect for you: preview your retarget against the donor's own clips (`summon-export --anims all`
gives you the full clip set to scrub in Blender) before committing to final art.

## Reused, not reinvented (the transplant lane)

| piece | module |
|---|---|
| the forward exporter (rig + skin + clips, glTF) | `summons/export.py` (`export_summon_glb`, `export_rig_ref`) |
| the model-struct adapter + offline clip decoder | `summons/build.py`, `summons/motion.py` |
| the mint (GEO id, name, `3DModel` line) | `models/mint.py` — same `MINT_BAND_START = 6000` band and `[[mint]]` uses |
| the `.anim` clip writer | `models/anim.py:clip_to_anim_json` — the JSON `AnimationClipReader.ReadAnimationClip_JSON` already reads; no new clip format |
| the `Memoria.ini` section writer | `coop.py` — `update_ini_section` / `_backup_ini` / `_check_ini_pair` / `write_netsync` |
| the cast trigger | the existing `vfx1` ability lane, `battle/actiondelta.py:64` — paired, not compiled, by `[[summon]]` |

The reskin/rescore lanes (below) reuse the same container reader, texture decoder, and write ledger
the rest of the kit already ships — `summons/container.py` (extended, not forked, by this
promotion), `summons/texture.py`, and a new `summons/ledger.py` that is a strict superset of the
transplant lane's own write/backup/readback/revert accumulator (`summons/deploy.py`'s `_Ledger`,
left as-is — this is a documented, one-directional duplication, not a silent fork).

## Recolour a stock summon in place — `summon-reskin`

Not a texture repaint and not a new model: a **CLUT recolour**. Not one texel moves. `summon-reskin`
reads a stock summon's container out of *your own install*, rotates its declared palettes — the
creature's **and** the effect's own scenery (see THE EFFECT-OWNED SCENERY LAW, below) — through HSV,
and splices the result back at the exact same file offsets. Geometry, UVs, the program, the
sequence, and the camera are untouched; the container's byte length never changes. Ships as a
mod-folder override with a self-contained revert script, exactly like every other summon verb.

```
ff9mapkit summon-reskin scaffold --ef 211            # read the install, EMIT a complete guarded toml
ff9mapkit summon-reskin plan     phoenix_reskin.toml  # resolve every target, print the numbers, no write
ff9mapkit summon-reskin build    phoenix_reskin.toml  # stage the container + previews + scripts locally
ff9mapkit summon-reskin verify   phoenix_reskin.toml  # re-check what's staged, as bytes
ff9mapkit summon-reskin deploy   phoenix_reskin.toml  # write the override straight into a mod folder
ff9mapkit summon-reskin revert   phoenix_reskin.toml  # undo exactly what deploy wrote
```

`scaffold` is the intended starting point on **any** stock summon, not just the ones this page
names: it reads your install, derives every palette the container declares (creature parts *and*
scenery cells, whichever exist), measures each row's hue/saturation/value and its 5-bit headroom,
and emits a complete TOML with the drift-guard hash filled in, every acknowledgement it can compute
pre-filled, and every declared row `enabled = false`. You dial `hue_to`/`saturation`/`value` and
flip rows on — you never hand-type an offset, a VRAM cell, or a palette name.

### The spec schema

`[reskin]` (one per spec):

| key | required | meaning |
|---|---|---|
| `effect` | **yes** | the stock `SpecialEffect` id to recolour (e.g. `211` for Phoenix). Selects which container the build reads out of your install. |
| `label` | no | a human tag carried into reports/manifests; no engine meaning. Defaults to `"reskin"`. |
| `expect_sha256` | *needed unless the effect has a registered hash* | sha256 of the pristine stock container this edit was derived against — THE DRIFT GUARD. Without it, and without an entry already registered for `effect` in the module's own hash table, the build REFUSES unless `allow_unguarded = true`. `scaffold` fills this in from your own install. |
| `allow_unguarded` | no | splice with **no** drift guard at all — an explicit escape hatch for a deliberately unguarded edit, never a default. |
| `acknowledge_texanim` | *conditional* | required (`= true`) before an **enabled scenery** target may build on an effect whose id-4 texanim region is armed. A **creature** target on such an effect is refused outright — no key lifts that one (THE TEXANIM GATE, below). |
| `defaults` | no | a `[reskin.defaults]` sub-table of transform fields (`hue_rotate` / `hue_to` / `saturation` / `value`) every `[[reskin.target]]` row inherits unless it overrides them. |
| `spans` | no | a `[reskin.spans.<name>]` sub-table per named span (`offset`, `length`) — GUARDS on the derivation: if the container's own header derives a different span, the build refuses rather than splice into a place this edit was not derived against. |
| `orthogonality` | no | a `[reskin.orthogonality]` sub-table naming sibling spec paths (`rescore = "…"`, `retime = "…"`), resolved **relative to this spec file's own directory** — see Orthogonality, below. |

`[[reskin.target]]` (repeatable — one row per palette you touch):

| key | required | meaning |
|---|---|---|
| `name` | **yes** | the palette's *derived* name: `creature.part{N}` (the creature strip) or `pal.s{slot}.x{X}_y{Y}.e{entries}` (a scenery cell, keyed on chunk SLOT + VRAM cell + bit depth). A hand-authored ef227 spec's legacy `scenery.*` / `c{index}_*` names still resolve through an alias map. `scaffold` prints every name the container actually declares. |
| `enabled` | no, default `true` | `false` ships the row's *intent* without splicing a byte — its acknowledgements only become mandatory the moment it is switched on. `scaffold` pre-seeds every declared row `enabled = false`. |
| `hue_rotate` | no, default `0.0` | a hue **delta** in degrees. Mutually exclusive with `hue_to` on one row — declaring both refuses. |
| `hue_to` | no | the **absolute** hue in degrees the palette's own measured mean hue should land on; the build computes the delta for you. Required on **every** writer of a multi-writer CLUT cell (see the refusal table). |
| `saturation` | no, default `1.0` | a scale on S. |
| `value` | no, default `1.0` | a scale on V. `> 1.0` on a palette that already peaks at 31/31 (zero headroom) refuses without `acknowledge_headroom`. |
| `acknowledge_shared` | *conditional* | required (`= true`) before an **enabled** target on a DERIVED-shared palette may build (bound by more than one GEOM model, or unattributed at incomplete `so`-coverage — see the laws, below). |
| `acknowledge_headroom` | *conditional* | required (`= true`) before a `value > 1.0` on a zero-headroom row may build. |
| `expect_entries` / `expect_vram` / `expect_offset` | no | guards: if the derivation disagrees with what you name here, the build refuses rather than splice at a place this row was not authored against. |
| `note` | no | free text, carried into manifests/reports only. |

The five hard rules below apply to **every** target and are not configurable by any key: `0x0000`
stays `0x0000` (the OPAQUE cutout); the transparency bit is carried, never recomputed; every output
channel clamps to 0–31; the rotation runs in HSV over the decoded BGR555 and re-encodes to 5 bits;
and every changed byte must land inside a derived span, or the build refuses outright.

### Refusals

| trigger | satisfied by | why (the law) |
|---|---|---|
| no `expect_sha256`, and the effect has no registered hash | `allow_unguarded = true` | a Steam/Moguri patch or another mod could move a span under the edit and nothing would notice — the drift guard exists so that never happens quietly. |
| a **creature** target on a TEXANIM-armed effect | *nothing lifts this — it's outright* | THE TEXANIM GATE: the arming table is per creature PART and its internal format is unread, so a running animation may cycle the CLUT word, the texels/UVs, or the CLUT contents — only one of those three leaves a static recolour intact. |
| a **scenery** target on a TEXANIM-armed effect | `acknowledge_texanim = true` at `[reskin]` | the same table's reach into the effect's own set is *plausible* but unproven — the acknowledgement states exactly that, in those words. |
| a DUAL-DEPTH CLUT cell touched (two different entry-count readings of the same VRAM bytes) | *nothing lifts this — it's outright* | the two readings are two different pictures over the same bytes, and no evidence exists either way about how they interact. |
| a MULTI-WRITER cell (more than one file offset streams into the same VRAM cell) with not every writer named | name every writer | recolouring one writer leaves the others stock, and the cast flickers between two keys. |
| … named, but not every one with `hue_to` | rewrite every writer with `hue_to` | each writer has its own measured mean hue, so a shared `hue_rotate` **delta** lands them on *different* hues — the flicker this gate exists to stop. |
| a DERIVED-shared palette enabled | `acknowledge_shared = true` on that target | it may only be recoloured as the group it is — the acknowledgement shows the author knows more than one set piece moves together. |
| `value > 1.0` on a row whose brightest live channel is already 31/31 | `acknowledge_headroom = true` on that target | "stock leaves headroom" was an ef227-only measurement — 46 of the corpus's 93 creature rows (all six of ef211's) have none, and a lift there can only flatten the ramp, never brighten it. |
| a `build`/`deploy` destination inside a checkout, a mod-asset tree, or (without an explicit allow) the game install | *never — no `--force`* | the same local-only provenance guard every summon verb already enforces. |
| `deploy` into a mod folder that already has a `ModFileList.txt` | *never — and this verb never creates one either* | THE SILENT-FALLBACK LAW, below. |

One more gate lives beside the table above, reported rather than raised as an exception: the
self-check measures the worst **relative-luminance ordering** (Spearman ρ) any recoloured palette
survives at, on every `plan`/`build`/`verify`/`deploy`. Nothing configures a threshold, but a failing
self-check still blocks `build`/`deploy` from writing a byte (a *verdict* refusal — the CLI's own
exit code 1 — rather than the exception-raising refusals in the table, exit code 2). The study's own
shipped rows never go below 0.90; a lower ρ means light/dark modelling within that ramp is inverting
under the hue you chose (see THE SATURATED-RAMP LAW, below).

### The laws behind the refusals (house voice, study-grounded)

- **THE TEXANIM GATE.** Corpus-wide, exactly five stock creature packages (ef038, ef177, ef493,
  ef494, ef495) carry a non-empty texture-animation region between the id-4 geometry block and its
  first motion clip — everywhere else that span is zero bytes. The arming ops index the record PER
  CREATURE PART, and the table's own byte layout has never been read, so whether a running texanim
  cycles the CLUT word, the texels/UVs, or the CLUT contents is unsettled — and only one of those
  three leaves a static palette recolour intact. That is why a creature target refuses outright
  there and a scenery target only needs a stated, unproven acknowledgement
  (`studies/custom-summons/tier-w/W5-GENERALIZE.md` §1, `PLAN.md` rung W5).
- **Headroom is measured, never assumed.** "Stock leaves headroom for a brighter value" was true
  of ef227 (its six creature rows peak at 22–28 of 31) and false of the corpus at large — 46 of 93
  creature CLUT rows peak at the 5-bit ceiling, including every one of Phoenix ef211's. The gate
  measures each row's own peak rather than trusting the one effect the tools were first proven on
  (`W5-GENERALIZE.md` §1).
- **THE SATURATED-RAMP LAW, plus the TWO-LOBE refinement.** A reskin's *reachable* hue range shrinks
  as the creature's own mean saturation rises, and at the extreme it is absolute: Phoenix and
  Rebirth Flame (mean S 0.711, the two most saturated stock creatures) cannot reach **any** cold hue
  under the luminance-ordering gate — their whole passing arc is stock ±25°. Where a forbidden
  trough exists, it sits on the **stock hue's complement**, with a passing lobe on either side — for
  a fire ramp, cyan/teal *and* violet both pass; the pure blue between them does not
  (`PLAN.md` "Status — W5"; `W5-GENERALIZE.md` §2). This is why Phoenix ef211 ships a
  **scenery-only** reskin (its own creature rows are parked `enabled = false`, at the measured
  passing key, one gate away) while the creature-lever's second proof rides Madeen ef251 instead —
  a summon whose lower mean saturation actually reaches a cold hue.
- **THE EFFECT-OWNED SCENERY LAW, and H-first.** A summon's cinematic is a self-contained set —
  creature, props, *and* an authored ground/sky/fire-field that travels with the effect and is drawn
  on its own schedule — not the arena it happens to be cast in (falsified by casting the same
  summon in two different locations and seeing the same ground both times). Rescoring the camera
  without regard for that set shows the set's edges, so: **focal distance (H) is the safest lever**
  — it reframes without moving the eye, exposing less of the effect's own set than a pose change
  would — and a phase that draws effect models (readable off the camera lane's own scaffold) is a
  phase where the reframe budget is tight (`PLAN.md` "★ THE EFFECT-OWNED SCENERY LAW"). Reskin
  inherits this too: a reskin's scope is the WHOLE set, creature and scenery, precisely because the
  scenery is part of what the cinematic was authored to show.
- **THE ADDITIVE-COMPOSITING COROLLARY, and probe-then-key.** For a VFX texture that the engine
  blends additively, the in-game read keeps whichever channel the blend favours — a cold, desaturated
  key that looked right in an offline preview washed to near-white against stock fire cores in the
  live cast, and lowering saturation on an already-max-sat ramp made it worse, not better (the
  attempt clipped every entry and the blow-out gate refused it: fire IS max-sat; the lawful punch is
  **hue at saturation 1.0**). The recovery method that generalises: stage a diagnostic PROBE first —
  every live entry of the bound palettes driven to one saturated primary — and read what the *cast*
  shows, not what the preview PNG shows, before committing to a final key
  (`PLAN.md` "Status — W5"; the magenta probe that re-grounded Phoenix's scenery lever after its
  first cast read stock).
- **Hot per cast, and THE SILENT-FALLBACK LAW.** A staged container is re-read from disc on every
  cast — no `~ → Reload` needed to see a new spec take effect, and no relaunch either, once the
  override is in place. The failure mode this cuts both ways on: `SFX.Play` suppresses its own
  missing-asset error, so a wrong mod folder, a stray file extension, a selector picking a track
  you didn't edit, or another `FolderNames` entry shipping its own copy of the same effect id ALL
  produce the identical symptom — "nothing changed" — with nothing logged anywhere. Deliberately
  large first deltas and `verify`'s byte-level re-check exist because of this one law, shared
  verbatim with the rescore lane below.
- **The ModFileList refusal.** When a mod folder carries a `ModFileList.txt`, the engine's asset
  lookup TRUSTS that list and never probes the folder directly — so a file the list omits is
  invisible, and (per the law above) that invisibility logs nothing. `deploy` refuses outright into
  such a folder rather than silently maintaining a registry it doesn't own, and — like the
  transplant lane's own ledger — never creates one itself: doing so would make every *other* file in
  that folder invisible at a stroke.

## Reframe a stock summon's camera in place — `summon-rescore`

A summon's camera is not reached from the effect's own program: it is played by the container's
sequence stream, which names a camera sub-file inside an id-2 archive — the **same block format**
the battle engine's `camera_codec` already round-trips, byte-for-byte, across all 372 stock
containers. `summon-rescore` reads a stock summon out of your install, applies a declarative delta
in the read-out's own vocabulary (shot / chunk / sub-file / sequence / local frame / pose / focal
distance), and splices the re-serialised block back at the **same length** — nothing else in the
container moves.

```
ff9mapkit summon-rescore read     --ef 211            # the full shot READ-OUT, every keyframe in human terms
ff9mapkit summon-rescore scaffold --ef 211            # read the install, EMIT a shot-table toml
ff9mapkit summon-rescore plan     phoenix_rescore.toml # resolve every edit, print the delta, no write
ff9mapkit summon-rescore build    phoenix_rescore.toml # stage the container + scripts locally
ff9mapkit summon-rescore verify   phoenix_rescore.toml # re-check what's staged, as bytes
ff9mapkit summon-rescore deploy   phoenix_rescore.toml # write the override straight into a mod folder
ff9mapkit summon-rescore revert   phoenix_rescore.toml # undo exactly what deploy wrote
```

### The three hard constraints (each enforced at the call site, not just stated)

1. **Durations are never touched.** A camera's keyframe timing and the effect program's own phase
   thresholds are two clocks the original author kept aligned by construction — a content rescore
   moves neither. Any `duration` key (`focal.duration`, `camera_move.duration`,
   `target_move.duration`) is refused outright; retiming both clocks together is a separate,
   study-only lane this promotion does not ship.
2. **The container's byte length never changes.** A camera sub-file's length is fixed by the next
   id-2 directory entry, and the slack is 0–2 bytes corpus-wide — so the rescored block must
   re-serialise to *exactly* the stock length, or the build refuses rather than risk shifting the
   directory.
3. **A Code's `frame` word's undecoded high bits survive**, because this lane never writes one at
   all — the strongest form of preserving marks nobody has decoded yet.

### The spec schema

`[rescore]` (one per spec):

| key | required | meaning |
|---|---|---|
| `effect` | **yes** | the stock `SpecialEffect` id to reframe. |
| `label` | no | a human tag, no engine meaning. Defaults to `ef###`. |
| `expect_sha256` | no | sha256 of the pristine stock container this edit was derived against. Unlike the reskin lane, this is a **warn-not-refuse** guard: an effect with no registered hash and no `expect_sha256` builds anyway, reported as "UNGUARDED" rather than blocked — matching the deploy engine's existing posture toward an unrecognised donor. Set it (or let `scaffold` set it) whenever you want drift caught rather than warned about. |
| `acknowledge_dynamic_ops` | *conditional* | required (`= true`) before the build proceeds on a container carrying a `PLAY_CAMERA arg2=3` op — see THE DYNAMIC-OP DISCLOSURE, below. A stale `= true` on a container with **zero** dynamic ops also refuses (a spec copied from another effect). |

`[[edit]]` (repeatable — one row per keyframe you touch):

| key | required | meaning |
|---|---|---|
| `shot` | *one of `shot` / `chunk`+`subfile`* | the shot LETTER from the read-out (`A`, `B`, …). |
| `chunk` / `subfile` | *one of `shot` / `chunk`+`subfile`* | the (chunk, id-2 sub-file) pair the shot resolves to. When both a letter and a pair are given, they're cross-checked — a mismatch means the read-out this spec was written against is not the effect in front of you. |
| `sequence` | no, default `0` | which of the block's declared tracks to edit (see THE THREE-SEQUENCE TRAP, below). |
| `all_sequences` | no | `true` fans the identical delta across every declared track — required whenever the block's alternates genuinely differ and you haven't confirmed the one you're naming is the only one that can play. |
| `frame` | **yes** | the keyframe's LOCAL frame number, exactly as the read-out prints it. |
| `occurrence` | no, default `0` | which repeat of that frame number, on a block that reuses one (a placement and the move it starts often share a frame). |
| `camera` / `target` | no | the 6-byte pose sub-tables: `code` / `flags` / `pitch` / `orientation` / `roll` / `distance`. |
| `focal` | no | the 4-byte focal sub-table: `distance` — **H, the projection distance** — is the one camera value an in-game capture can observe directly, so it's the calibrated half of any reframe; `flags` is the other editable field. `duration` is refused. |
| `camera_move` / `target_move` | no | the 4-byte movement sub-tables: `type` / `unknown`. `duration` is refused. |

### Refusals

| trigger | satisfied by | why (the law) |
|---|---|---|
| any `duration` key on any of the three movement/focal sub-tables | *nothing — refused outright* | the two-clocks law: a camera reframe that also drifts a duration desyncs the cut from the program's phase beat. |
| the rescored block re-serialises to a different length | *nothing — refused outright* | the id-2 directory's slack is 0–2 bytes; only a same-length splice is legal here. |
| a block's alternates genuinely differ and only one track was edited | `all_sequences = true`, or edit every track | THE THREE-SEQUENCE TRAP: the runtime selector may pick an alternate you never touched, and the cast looks completely unchanged. |
| no `acknowledge_dynamic_ops`, and the container runs a `PLAY_CAMERA arg2=3` op | `acknowledge_dynamic_ops = true` | THE DYNAMIC-OP DISCLOSURE, below. |
| `acknowledge_dynamic_ops = true`, but the container runs zero such ops | remove the key | a stale acknowledgement copied from another effect states a risk this container does not carry. |
| a `build`/`deploy` destination inside a checkout, a mod-asset tree, or (without an explicit allow) the game install | *never — no `--force`* | the same local-only provenance guard every summon verb enforces. |
| `deploy` into a mod folder that already has a `ModFileList.txt` | *never — and this verb never creates one either* | THE SILENT-FALLBACK LAW (see the reskin section, above — shared verbatim). |

### THE DYNAMIC-OP DISCLOSURE

`PLAY_CAMERA` with `arg2 == 3` chooses its block from a table keyed by the **battle field at
runtime** — a table that is not merely undecoded, it is *absent from the container entirely*. So
from these bytes alone nothing can say whether the (chunk, sub-file) pair you're editing is *also*
the target of a lookup under some other battle condition, or which other blocks that lookup might
reach instead. Corpus-wide this is the common case, not the exception: **324 of 372 stock effects**
carry at least one such op — Bahamut ef227, the effect these tools were first hand-proven on, was
the outlier with zero. That is why `acknowledge_dynamic_ops` exists and why its own message spells
out that only an in-game cast across *varied* battle conditions closes the question an offline gate
cannot.

## Orthogonality — proving a reskin and a rescore can ship on one container together

The proof runs from the **reskin** side: its `self_check` rebuilds a **sibling** spec from its own
TOML (a rescore, or a study-only retime) and intersects its changed-offset set with the reskin's own
— an empty intersection is the proof that the two edits land in disjoint bytes and can ship
together. The sibling is named in `[reskin.orthogonality]` (`rescore = "…"`, `retime = "…"`),
resolved **relative to the spec file's own directory**, never the module's. A sibling the spec names
but that doesn't exist FAILS the gate outright; a sibling nobody named is SKIPPED with that stated,
so an unproven disjointness is never reported as a proven one — and a sibling that targets a
*different* effect id is skipped too (rebuilding Bahamut's camera proves nothing about a reskin of
Phoenix). On top of the changed-offset intersection, the check also gates whole regions
byte-identical: sector 0 (the resource table + sequence stream), every id-3 program image, every
camera block, every GEOM block, the id-4 header+texel region, and the id-2 model image — i.e.
everything a repaint or a retime would touch instead. There is no reverse gate on the rescore side
today — running `summon-rescore`'s own `verify`/`plan` proves only that lane's own byte-identity; the
disjointness proof is authored once, from whichever lane's spec names the other as a sibling.

## Byte-identity acceptance — how this promotion is held to the study's own proof

These verbs are only as trustworthy as their claim to reproduce what TIER W already cast in-game.
Rebuilding the *committed* study specs through the kit's own CLI/module code must reproduce the
exact bytes the study staged and the owner judged in-game — install-gated (it skips cleanly without
the user's own FF9 install and the study's committed spec tomls), re-deriving rather than trusting a
recorded hash, the same posture the transplant lane's own M1b acceptance test uses:

| artifact | study sha256 | covered by |
|---|---|---|
| ef227 reskin (Bahamut, W4 whole-set recolour) | `7fef205f…` | `summon-reskin`'s own CLI acceptance test |
| ef211 reskin v2 (Phoenix, GLACIAL v2 scenery key) | `4daab8ad…` | `summon-reskin`'s own CLI acceptance test |
| ef251 reskin (Madeen, GLACIAL MADEEN creature recolour) | `78b395f8…` | `summon-reskin`'s own CLI acceptance test |
| ef227 rescore (Bahamut, W2 opening reframe) | `8146eff4…` | `summons.rescore`'s own module-level acceptance test |
| ef211 rescore (Phoenix, H 384→288 camera pull) | `7979566f…` | the CLI acceptance test (`summon-rescore build` end-to-end, in `tests/test_summon_reskin.py`) |

Every cast-proven artifact the promotion's design brief named is pinned: the three reskins and the
ef227 rescore at module level, and the ef211 rescore through the full CLI build path — the one place
the second verb's whole read → build → splice → stage ladder runs against real bytes.

## Further reading

- [FORMAT.md — `[[summon]]`](FORMAT.md#summon-optional-repeatable) — every key, its default, both lanes.
- [tutorial 11 — the Blender round-trip](tutorials/11-summon-transplant.md) — the transplant, step by step.
- [tutorial 14 — recolour and reframe a stock summon](tutorials/14-summon-reskin-rescore.md) — the
  `summon-reskin`/`summon-rescore` workflow, step by step.
- `studies/custom-summons/thomas-swap/disasm/TRANSPLANT.md` — the full feasibility study (why the
  hybrid wins, the milestone ladder, the risk ledger).
- `studies/custom-summons/thomas-swap/m0/FBX-PATHS.md` — the file-by-file path resolution this
  block's deploy contract is built on.
- `studies/custom-summons/thomas-swap/m0/S58-DRAFT.md` — the `[SfxHybrid]` engine feature spec.
- `studies/custom-summons/thomas-swap/m2/DESIGN.md` — the binding module plan this page follows.
- `studies/custom-summons/tier-w/PLAN.md` — the reskin/rescore ladder (W1–W5), every law, the
  full cast record on both proof summons.
- `studies/custom-summons/tier-w/W5-GENERALIZE.md` — the generalisation report: what each lane
  became, the laws it minted, the second-proof cast protocol.
