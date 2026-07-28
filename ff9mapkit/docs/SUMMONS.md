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
> - **Repaint in place (`summon-reskin export-art` + `[[reskin.texel]]`)** — TIER W rung W6a, the
>   second lever on the SAME `summon-reskin` verb: not a colour rotation but the texel INDICES
>   themselves, so it can move a shape, an edge, a silhouette — the one thing a CLUT recolour
>   structurally cannot do. **Landed this rung for creature texture pages only** (the one texel
>   class measured free of every known hazard corpus-wide) and **offline-proven**: the indexed
>   round trip is byte-identical on all 93 stock creature pages across all 24 decodable packages,
>   every refusal ships with a test, and a composed proof artifact (the W4 spectral-mist Bahamut
>   rebuilt plus a hard-edged brand stamped on its own wing) gates clean end to end — an in-game
>   cast is the next step, not yet run in this rung. **Rung W6b-1 extended it to the effect's own
>   SCENERY** — sky domes, fire fields, ground planes — at 4, 8 and 15 bpp, with remedies for the
>   multi-writer, spilling and multi-palette cells and a named refusal (carrying its measurement) for
>   the ones no remedy touches: see [the scenery texel lane](#the-scenery-texel-lane-w6b-1) below.
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
| `acknowledge_texanim` | **deprecated — a no-op, with one exception** | it used to be required before a scenery target could build on a texanim-armed effect. The assumption behind it is a measurement now — **when the table decodes** — so on every stock container it does nothing: still accepted (and reported) for one release so older specs keep building, `scaffold` no longer emits it, and you should delete the line. The exception: on an armed table the reader **cannot decode**, the measurement never ran, and the key is **required** for scenery in its original meaning (orthogonality assumed, not proven). See THE TEXANIM TABLE, below. |
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
| a **creature** target on a TEXANIM-armed effect whose table **does not decode** | *nothing lifts this — it's outright* | the table's format is read now, but the lift is conditional on a **successful parse**, never on the absence of an error. A region the reader cannot decode is the state this tool was in before it could read any of them, so each scope gets exactly its pre-W7 posture: creature refuses outright, and a **scenery** target is back to needing `acknowledge_texanim = true` (the key's original meaning). An unknown container shape must degrade to the safe behaviour, not slip past it. |
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

- **THE TEXANIM TABLE — read, and no longer a refusal.** Corpus-wide, exactly five stock creature
  packages carry a non-empty texture-animation region between the model image's geometry block and
  its first motion clip — **ef038** (Shiva, 116 bytes) and **ef177 / ef493 / ef494 / ef495**
  (Carbuncle ×4, 364 bytes each and byte-identical: one creature shipped as four ability rows).
  Everywhere else that span is zero bytes. Earlier releases refused every creature edit on those five
  because the region's layout was unread. It is read now: `u32 clipCount`, then one 20-byte **clip**
  record per clip, then one 12-byte destination **window** per clip, then packed 4-byte frame lists —
  three arrays that account for every byte of the region exactly, which is what proves the reading.
  **What it describes is a texel blit**: a small rectangle of 8-bit palette *indices* copied from a
  spare strip into a live window **inside one creature part's own 128×128 page**. It never binds or
  writes a palette word, never rewrites palette contents (its rectangles cannot even reach the
  palette strip), and never touches a UV. So a recolour survives it **by construction** — a blit of
  indices looks the same under any palette — and a scenery target was never in its reach at all,
  because every clip names a *creature* part and every rectangle is local to that part's page. Both
  refusals lifted; `acknowledge_texanim` is a deprecated no-op. (On the PC build nothing plays these
  tables anyway: the only engine code that reaches the region writes three state fields and returns.)
  Full record: `studies/custom-summons/tier-w/W7-TEXANIM.md`.
- **THE REGION INVARIANT — the rule that replaced the refusal.** The engine compares the region's own
  start against the first motion clip and takes a different code path when they are equal, so **that
  span is never resized, relocated, zeroed or rewritten, and its start offset is never edited** — by
  either lever. Both a recolour and a repaint are in-place splices that never need to, so honouring it
  costs nothing; every build asserts it on the bytes it is about to hand back and reports the verdict
  in `plan`. This tool ships a **reader** for the table, never a writer: there is no consumer of it in
  the shipped engine, so no authored edit to it could be verified.
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

## Repaint a stock summon's texture in place — the texel lane (`[[reskin.texel]]`)

`summon-reskin` is a per-index **colour function** — it can rotate a hue, but it structurally
cannot move a texel from one index to another, so it can never change a shape, an edge, or a
silhouette. The texel lane is the second lever on the same verb: it rewrites the **indices**
themselves. Lands in a new sibling module, `summons/repaint.py`, which *consumes* what
`reskin.py` already derives (`creature_pages`, `PaletteMap`, `texanim_region`, a `partition`
parameter on `_regions`) rather than re-deriving it — `reskin.py`'s own docstring earmarks the
repaint as "a different lane" and now names where it lives.

**TWO SURFACES, ONE LEVER.** Rung W6a shipped the **creature texture pages**: every id-4 page is
single-writer (0 collisions against every scenery rect and every id-9 block, measured over 24
packages / 93 pages) and uniform 8bpp — the one texel class free of every hazard the corpus carries.
Rung **W6b-1** added the effect's own **scenery** — sky domes, fire fields, ground planes, energy
rings — at 4, 8 and 15 bpp, with a remedy for each of the hazards that surface actually carries and a
refusal, by name and with its measurement, for the ones no remedy touches. See
**[the scenery texel lane](#the-scenery-texel-lane-w6b-1)**, below.

```
ff9mapkit summon-reskin export-art --ef 227 --out C:/gd/SCRATCH/summon-format/repaint/ef227/art
  # decode every creature page to a paintable indexed PNG + a coverage overlay + a guarded scaffold
ff9mapkit summon-reskin build  bahamut_emblem.toml   # resolves [[reskin.texel]] ALONGSIDE [[reskin.target]]
ff9mapkit summon-reskin plan   bahamut_emblem.toml   # every gate, no write
ff9mapkit summon-reskin verify bahamut_emblem.toml   # re-check what's staged, as bytes
ff9mapkit summon-reskin deploy bahamut_emblem.toml   # write the override, same ledger as the CLUT lane
ff9mapkit summon-reskin revert bahamut_emblem.toml   # undo exactly what deploy wrote
```

There is no separate CLI verb: `export-art` is a new `summon-reskin` action (only on the reskin
lane — `summon-rescore` does not carry it), and `build`/`plan`/`verify`/`deploy`/`revert` climb the
**same six-verb ladder** already documented above, now resolving whichever of `[[reskin.target]]`
(CLUT lane) / `[[reskin.texel]]` (texel lane) a spec declares — either alone, or **both in one
file**: a spec carrying both builds the recolour first and hands its patched bytes to the repaint,
so the two levers ship as ONE container, ONE ledger, and ONE revert, with their changed-byte sets
gated disjoint (see Orthogonality, below).

### `export-art` — the paint workflow

```
ff9mapkit summon-reskin export-art --ef <id> [--out DIR] [--art-lane indexed|direct15] [--no-coverage]
```

Reads the stock container out of your own install (or `--from <file>`), decodes every addressable
page — creature parts **and** every scenery cell whose depth the container states — and writes, per
part, under a **local-only** root (`export.assert_local_only` — no
repo path, no `StreamingAssets` tree, no install path, no `--force`, because a decoded page is
Square-Enix content):

- **`tex.part<N>.png`** — the paintable page itself, at the format of record (below).
- **`tex.part<N>.coverage.png`** — the same page with its never-sampled texels hatched (green =
  outer pad, red = an interior hole); omit with `--no-coverage`.
- **`art.manifest.json`** — one record per part: `stock_sha256` (the drift guard a later `build`
  re-checks), `page_offset`/`page_bytes`/`wh`/`clut_offset`/`tpage`/`clut`, and the measured
  `covered_texels`/`dead_texels`/`interior_holes`/`transparent_indices` census.
- **`texel.scaffold.toml`** — a fully guarded `[[reskin.texel]]` table, every `expect_*` filled in
  from the derivation and every row `enabled = false` — the same "scaffold at identity, dial one
  row at a time" posture the CLUT lane's own `scaffold` uses.

`--art-lane rgba` is named in the CLI on purpose, not omitted: asking for it returns the
measurement that rules it out (below) rather than a bare "unknown choice" error.

### The format of record: an INDEXED PNG, never RGBA

Every export is a **P-mode (palette-indexed) PNG** whose *pixels are the palette indices*, with the
live CLUT row loaded as the PNG's own palette (**display-only** — the container stays the palette
authority, and this lane writes **zero CLUT bytes**) and `tRNS` marking the one transparent entry
so the cutout is visible to a painter, not just correct on import. Measured over every stock
creature page: `decode → P-mode PNG → reload → indices` is **byte-identical 93/93** across all 24
decodable packages. An RGBA round trip is not: 8.31% of the corpus's palette entries duplicate the
full 16-bit word (STP included), so an RGBA export that **paints nothing at all** still moves 1,844
of 16,384 texels re-importing ef251 part 0 — a lane whose no-op is not a no-op cannot carry a
byte-identity gate, so `rgba` refuses with that number rather than shipping a silent trap. Import
refuses anything that isn't mode `"P"`, isn't the exported size (no rescale — an index page has no
meaningful resample), or uses an index past the page's own CLUT row length.

### The `[[reskin.texel]]` schema

`[reskin]` gains no new required key for the texel lane — `effect`/`label`/`expect_sha256`/
`allow_unguarded` mean exactly what they mean for `[[reskin.target]]` (a spec may declare either
table, or both, under one `[reskin]` header). `[reskin.orthogonality]` gains one more switch:

| key | required | meaning |
|---|---|---|
| `orthogonality.reskin` | *conditional* | a sibling `[[reskin.target]]` spec's path (relative to THIS file), composed onto by `compose = true` — see Composing with the CLUT lane, below. |
| `orthogonality.compose` | no, default `false` | `true` rebuilds the named `reskin` sibling and splices this spec's texel edits onto ITS patched bytes instead of stock — the CLI's own one-spec path sets this implicitly whenever a spec carries both tables. |

`[[reskin.texel]]` (repeatable — one row per page you touch):

| key | required | meaning |
|---|---|---|
| `name` | **yes** | the page's *derived* name, over BOTH namespaces: `tex.part{N}` for a creature part, `cell.{writer}.x{X}_y{Y}` for a scenery VRAM page-cell (e.g. `cell.s0.x704_y256`, `cell.id9.s0.x832_y384`). The old rect spelling `page.*.h256` still refuses — an `h = 256` rect is **not** an addressable unit, it is two stacked cells the engine uploads separately — and the refusal now names the two `cell.*` halves it splits into. `export-art` prints every name the container declares, and every cell it refuses with the reason. |
| `source` | *conditional* | the indexed PNG path (relative to the spec file), required the moment the row is `enabled`. |
| `enabled` | no, default `true` | `false` ships the row's *intent* without splicing a byte — its guards and acknowledgement only become mandatory the moment it's switched on. |
| `expect_page_offset` / `expect_page_bytes` / `expect_page_wh` | no | guards: if the container's own id-4 header derives a different span, the build refuses rather than splice into a place this row wasn't authored against. `export-art`'s scaffold fills these in for you. |
| `palette_from` | no | names the CLUT-lane row (`creature.part{N}`) this page indexes into, as a stated cross-reference — a page's palette is a HEADER FACT, not a choice, so naming any other row refuses. Omitted = the stock palette, 0 CLUT bytes touched (this rung's default). |
| `acknowledge_cutout_reshape` | *conditional* | required (`= true`, a literal boolean — a truthy string refuses rather than arms) before an edit that crosses the transparent-index boundary in either direction may build. See THE CUTOUT LAW, below. |
| `acknowledge_texanim_frames` | *conditional* | required (`= true`, a literal boolean) before a repaint that touches **some** of an animated clip's rectangles and leaves its siblings stock may build — a deliberately asymmetric strip. See THE TEXANIM CO-TRANSFORM, below. |
| `expect_bpp` | no *(scenery: strongly advised)* | **4, 8 or 15** — stated by you, CHECKED against the container's own `so` record, never chosen for you. The same `0x4000` bytes are 256 / 128 / 64 texels wide at 4 / 8 / 15 bpp, so a wrong depth makes a picture of the wrong shape that nonetheless packs to exactly the right byte count. Guarded a second time against the chunk's own `nClut4`/`nClut8`. |
| `expect_cell` | no | `[X, Y]` — the VRAM page-cell this row means. Refuses on a creature page, whose addressable unit is the id-4 PART. |
| `acknowledge_cotransform` | *conditional* | required (`= true`, a literal boolean) on **every** row of a VRAM cell that more than one writer uploads, and only reachable once every one of those writers is named with its own art. See THE CO-TRANSFORM REMEDY, below. |
| `acknowledge_spill` | *conditional* | required (`= true`, a literal boolean) on **every** row of a model whose picture crosses a VRAM column, and only reachable once every cell that model reads is named. See THE NAME-EVERY-COLUMN GATE, below. |
| `note` | no | free text, carried into manifests/reports only. |

### THE CUTOUT LAW, at the texel level

`0x0000` decodes to alpha 0 on every stock summon, and the corpus puts **exactly one** such entry
in every one of its 93 CLUT rows, always at index 0 — the transparent set is **derived from the
active palette** on every build, never assumed to be `{0}`. A palette recolour can never touch this
(the CLUT lane already carries "`0x0000` stays `0x0000`" as one of its five hard rules), but a
texel edit changes which *index* a pixel holds, so it controls the model's silhouette directly.
Every enabled row is counted **both directions** — `punch` (an opaque texel crossing into the
transparent index) and `fill` (a transparent texel crossing into an opaque one) — and any non-zero
count REFUSES unless the row says `acknowledge_cutout_reshape = true`. That is the one escape hatch
this lane needs that the CLUT lane doesn't: reshaping a torn wing edge is a legitimate texel-level
artistic move; painting through a hole by accident is not, and this is what catches the difference.

### THE TEXANIM CO-TRANSFORM — an obligation, not a refusal

Five stock creature packages carry a texture-animation table (see THE TEXANIM TABLE, above): **ef038**
(Shiva) and **ef177 / ef493 / ef494 / ef495** (Carbuncle ×4). Earlier releases refused a texel repaint
on all five outright, with no key. The table is decoded now, so the hazard is a **known set of
rectangles** rather than an opaque window: per clip, the live destination window plus every source
frame it can blit into that window. The build checks your actual edit against that set, per clip
family, and there are exactly three outcomes:

* **your edit touches none of those rectangles** → it builds. The animation cannot disturb it.
* **your edit reaches every rectangle of each family** → it builds. What the tool measures is
  **reach** — at least one changed texel in each rectangle — not that the same transform landed on
  each; a dense whole-page repaint (a global recolour, a filter, a full repaint) passes in practice,
  while a *sparse* page-wide remap can genuinely miss a rectangle and refuse (correctly: that
  rectangle really is left stock). Whether the reached rectangles were repainted *consistently* is
  your claim as the author, and the build note says so.
* **your edit repaints some and leaves siblings stock** → it **refuses**, and the message is a work
  order: the clip, the rectangles you painted, and the exact ones you left stock. The reason is
  concrete — the first time that clip runs, the window shows art your repaint never touched and the
  cast flickers between two pictures. Repaint the siblings the same way, or say
  `acknowledge_texanim_frames = true` on that row to state that the asymmetry is deliberate.

Treat overlapping rectangles as **one group and paint the union of their texels the same way** —
two of Carbuncle's mouth frames sit one row apart and share texels (and one eye frame overlaps
them into a three-rect group), so transforming each rect independently would double-apply on the
overlap. The readouts group them for you; the build itself checks reach per rect. `export-art`'s
report and scaffold and `plan` all print the protected set, so you can see it **before** you paint.
A table the reader **cannot decode** still refuses outright, exactly as before — the lift is
conditional on a successful parse.

### The dead pad — reported, never fatal

Only **64.0%** of the corpus's creature texels are sampled by any face (975,202 of 1,523,712 across
all 93 pages) — the rest is padding the geometry never reads. And over 99.6% of a page's dead
texels form ONE border-connected margin, which is why `export-art`'s `.coverage.png` (rasterised
from the container's OWN uv pools, corner-included so a one-texel-thin face still lights its own
texel) is a complete instruction: paint inside the island. Editing the pad is **inert**, exactly the
way a hue rotation is inert on the CLUT lane's achromatic cloud bands — so it's reported, with a
per-target dead/live split and a count, and never fails a build.

### Composing with the CLUT lane — one container, one ledger, one revert

Two routes to the same artifact, because the two levers' byte spans are provably disjoint (the CLUT
strip and the texel pages sit adjacent and non-overlapping in the container, e.g. on ef227:
palettes at `0x0621a0..0x062da0`, texel pages at `0x04a1a0..0x0621a0`):

- **one spec, both tables** — a `[reskin]` spec carrying `[[reskin.target]]` *and*
  `[[reskin.texel]]` builds the recolour first and hands its patched bytes to the repaint. This is
  the CLI's own path whenever both tables are present.
- **`[reskin.orthogonality] reskin = "…"` + `compose = true`** — a texel-ONLY spec composes onto a
  SHIPPED reskin spec's own rebuild, so the palette half keeps exactly one source of truth instead
  of being copied into a second file that can drift.

Either way the kit **proves** the disjointness rather than asserting it: the composed build's own
self-check rebuilds the CLUT half from its own spec and intersects the two changed-offset sets —
"THE COMPOSED HALVES ARE DISJOINT" is its own gate, right beside the region-partition gate that
proves the CLUT strip, the id-4 header, and every geometry/program/camera/sequence region stayed
byte-identical under the texel lane's own inverted partition. The reverse direction works too: a
`[[reskin.target]]` spec can name `orthogonality.repaint = "…"`, and the CLUT lane's own
`self_check` grows a `repaint` intersection gate — `reskin.py`'s `ORTH_REBUILDERS` now carries both
`rescore` and `repaint`.

### The scenery texel lane (W6b-1)

A summon's cinematic ships **its own scenery** — sky domes, fire fields, ground planes, energy rings —
and rung W6b-1 makes those editable too. Be warned up front about the shape of it, because it is
unusual: **the codec never fails and the gate refuses most of the surface.** That asymmetry is the
honest answer, not a limitation being worked around.

**The addressable unit is the VRAM PAGE-CELL** — 64 halfwords × 128 lines = `0x4000` bytes, the
quantum the engine uploads — named `cell.{writer}.x{X}_y{Y}`. It is deliberately not the container's
page *rect*: most stock rects are 256 lines tall and cover **two stacked cells** whose hazards
routinely differ (on Phoenix's column 576 the top half is a two-palette refusal and the bottom half is
clean 4bpp), and the rect view could name only the top one. The per-cell map names **1,179** cells
that previously had no name at all.

**Three depths, dispatched on what the container declares — never on the picture you hand back:**

| depth | the file(s) you edit | the rule |
|---|---|---|
| **8bpp** | `<cell>.png`, P-mode indexed | identical to the creature lane |
| **4bpp** | `<cell>.png`, P-mode indexed, 256×128 | **one byte per texel, values 0..15** — never Pillow's 4-bit mode, so no PNG bit-order convention can reach the container. An index above 15 REFUSES rather than being masked into a different, plausible colour |
| **15bpp** | `<cell>.png` RGBA8 **+ `<cell>.stp.png`** | direct colour, no palette at all. RGB is authoritative; **alpha is a cutout flag that is checked and discarded**; the sidecar carries bit 15 (the hardware's blend selector) and **is authoritative**. A missing sidecar refuses — it cannot be recovered, because "a hole" and "black, but blended" are different values that render identically |

State the depth with **`expect_bpp`**. It is *checked*, never chosen: the same `0x4000` bytes are 256,
128 or 64 texels wide at the three depths, so a wrong depth produces a wrong-shaped picture that packs
to exactly the right byte count — the one number on this lane that can be wrong quietly.

#### The four remedies — obligations you can discharge, not refusals

**THE CO-TRANSFORM REMEDY.** Some VRAM cells are uploaded by **more than one writer**, and across the
whole stock corpus **not one of those writer pairs holds the same bytes** — they are genuinely
different pictures shown at different points in the cast. Repainting one and leaving the others stock
makes the cast flicker between the new art and the old, which only a playtest catches. So: name every
writer, supply art for each, and put `acknowledge_cotransform = true` on every row of the cell. The
refusal names exactly which writers are **LEFT STOCK** and the `cell.*` names to add.

> **There is no "same art for all writers" shorthand, on purpose.** A key that broadcast one PNG to N
> writers would be the tool asserting the uploads are interchangeable, which the container's own data
> denies. Two rows MAY name the same file — that is your decision to unify the flicker — and the build
> discloses it rather than accepting it silently.

**THE NAME-EVERY-COLUMN GATE.** A model's `u` coordinate is 8-bit, but an 8bpp page is only 128 texels
wide, so a picture can reach into the *next* VRAM column — sometimes into a different resource
entirely. Every spilling picture in the corpus is wider than one page, and **none of them spills by a
negligible amount**, so a page-scope edit hands you half a picture and silently changes a model this
cell does not name. Name every cell the model reads, art for each, `acknowledge_spill = true`. Three
things refuse: a **foreign** model reading this cell (page scope is simply the wrong unit there), an
**unnamed** column, and a column **no writer in the container uploads** — there, nothing puts bytes at
that address, so the obligation cannot be discharged and no art exists to supply. A read-only stitched
`spill.<geom>.png` preview ships beside the editable cells: **judge the whole picture, edit the pieces
it is made of.**

**THE DISPLAY-PALETTE RULE.** A cell read by several models through *different* palettes is one index
array with several renderings. The editable PNG is in the lowest-addressed binding's key; every other
key ships as a NAMED read-only `<cell>.as-x{X}_y{Y}.png` alternate view of the same bytes. Both are in
the manifest, because an author who never learns the second key would tune a colour they cannot see.

**THE SHARED-READ DISCLOSURE.** A cell several models read at the *same* depth through the *same*
palette carries no signal at all that one edit changes two things — so the build **names the other
models**. A disclosure, never a refusal.

#### What refuses, by name, with its measurement

- **DEPTH-UNKNOWN — most of the surface.** **93% of scenery cells have no model in the container that
  samples them**, so the file never states their colour depth. A statistical probe was built to guess
  it and **falsified**: 54.5% agreement on a three-way choice. It does not ship, not even as a
  suggestion, because a plausible guess here writes a wrong-shaped picture that every other gate
  passes.
- **SAME-BYTES-TWO-DEPTHS.** Two models read one byte block at different depths — two different index
  arrays over the same bytes, and no single picture is coherent under both. Refuses *earlier* than the
  palette logic and with its own message.
- **PROGRAM-VRAM WRITE.** Some effects' own programs re-upload VRAM while the cast runs. A repaint
  there is a **lost edit with no symptom** — the container on disc still holds your art. The
  direction matters and is measured: a program that only *reads* VRAM back cannot clobber anything, so
  those containers **disclose** instead of refusing (which is what makes Phoenix's fire field editable
  at all).
- **An UNWRITTEN column** — see the spill gate, above.
- **RGBA for the indexed lane, and `--quantize`/`--mint-clut`** — unchanged, and refused for their own
  reasons rather than this one: RGBA is about exact recovery, and a palette *writer* conflicts with a
  `[[reskin.target]]` on the same palette.

Run `export-art` before you paint: it lists every cell it refuses **and why**, and the emitted scaffold
prints them as a commented block. On this surface the refusals *are* most of the shape, so they are
written to teach rather than merely to omit.

#### One more thing the build now protects

A scenery repaint writes into the container's id-0 **page pixel stream**, which the page-block header
and its rect table point at. Both are now gated on every build, and the page map is **re-derived** from
the patched bytes and compared — not merely byte-checked — because a mis-seek there would re-aim the
whole map while the container still parsed, the length still matched and every palette still
re-derived. The fail-safe is proven non-vacuous against a deliberately perturbed rect table.

Every law, its measurement and its provenance live in the study record:
`studies/custom-summons/tier-w/W6b-SCENERY.md` (and `W6-TEXEL.md` for the creature lane).

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
TOML (a rescore, a repaint, or a study-only retime) and intersects its changed-offset set with the
reskin's own — an empty intersection is the proof that the two edits land in disjoint bytes and can
ship together. The sibling is named in `[reskin.orthogonality]` (`rescore = "…"`, `repaint = "…"`,
`retime = "…"`), resolved **relative to the spec file's own directory**, never the module's. A
sibling named `repaint` reads its effect id out of its OWN `[reskin]` table (a texel spec is a
`[reskin]` spec too — one file, two possible levers), not a `[repaint]` table that doesn't exist. A
texel-only spec proves the same disjointness from its own side, in reverse: `orthogonality.reskin =
"…"` names the CLUT sibling it composes onto (see the texel-lane section, above). A sibling the spec names
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
