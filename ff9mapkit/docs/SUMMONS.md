# Custom summon transplants (`[[summon]]`)

> **Status.** The transplant *mechanism* is hand-built and **in-game proven** (Milestone 1b,
> 2026-07-24 — a user's own skinned model, posed every frame by a stock summon's real 93-bone
> skeleton, "it works, thomas flies with the dragon's motion": `studies/custom-summons/
> thomas-swap/m1b/RUNBOOK.md`). This page documents the **productized kit surface** around that
> mechanism, per the binding Milestone-2 module plan (`studies/custom-summons/thomas-swap/m2/
> DESIGN.md`): the `[[summon]]` block's schema + validation (`content/summon.py`, wired into
> `ff9mapkit build`/`lint`), the deploy engine (`summons/deploy.py`), and the `summon-import` /
> `summon-deploy` CLI verbs are all landed and test-covered. Full key reference:
> [FORMAT.md — `[[summon]]`](FORMAT.md#summon-optional-repeatable). The Blender round-trip, step
> by step: [tutorial 11](tutorials/11-summon-transplant.md).
>
> **Separate surface, explicitly out of scope here:** reading/forking a summon's raw container
> bytes (`summon-inspect` / `summon-disasm` / `summon-fork`, `summons/ef_container.py` +
> `summons/ef_geom_writer.py`) is a different provenance class with different failure modes and is
> not part of `[[summon]]` (`disasm/TRANSPLANT.md` §2.3). `summon-export` / `summon-rig-ref`
> (below) already ship and are the one piece the two surfaces share.

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
| Camera / staging | inherited for free — the same `Camera.main` every SFX effect renders through | the overlay host `.seq` nests the donor cast, so the donor's camera + fly-by carry for free; the `.sfxmodel` also ships default anchor curves (`staging` is a forward-compat knob — both values emit the same today) |
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

## Reused, not reinvented

| piece | module |
|---|---|
| the forward exporter (rig + skin + clips, glTF) | `summons/export.py` (`export_summon_glb`, `export_rig_ref`) |
| the model-struct adapter + offline clip decoder | `summons/build.py`, `summons/motion.py` |
| the mint (GEO id, name, `3DModel` line) | `models/mint.py` — same `MINT_BAND_START = 6000` band and `[[mint]]` uses |
| the `.anim` clip writer | `models/anim.py:clip_to_anim_json` — the JSON `AnimationClipReader.ReadAnimationClip_JSON` already reads; no new clip format |
| the `Memoria.ini` section writer | `coop.py` — `update_ini_section` / `_backup_ini` / `_check_ini_pair` / `write_netsync` |
| the cast trigger | the existing `vfx1` ability lane, `battle/actiondelta.py:64` — paired, not compiled, by `[[summon]]` |

## Further reading

- [FORMAT.md — `[[summon]]`](FORMAT.md#summon-optional-repeatable) — every key, its default, both lanes.
- [tutorial 11 — the Blender round-trip](tutorials/11-summon-transplant.md) — the step-by-step guide.
- `studies/custom-summons/thomas-swap/disasm/TRANSPLANT.md` — the full feasibility study (why the
  hybrid wins, the milestone ladder, the risk ledger).
- `studies/custom-summons/thomas-swap/m0/FBX-PATHS.md` — the file-by-file path resolution this
  block's deploy contract is built on.
- `studies/custom-summons/thomas-swap/m0/S58-DRAFT.md` — the `[SfxHybrid]` engine feature spec.
- `studies/custom-summons/thomas-swap/m2/DESIGN.md` — the binding module plan this page follows.
