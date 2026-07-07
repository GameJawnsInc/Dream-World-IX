# Engine requirements & notes

## Novel fields run on stock Memoria

A **novel** field — built from scratch, or borrowing a real field's background art — needs **no
engine modifications**. Everything it relies on already ships in
[Memoria](https://github.com/Albeoris/Memoria):

- the `FieldScene` **DictionaryPatch** directive that registers a custom field id
  (how the kit *mints* that id — area `>= 10`, BG-borrow vs custom scene — is in
  [`TECHNICAL.md`](TECHNICAL.md) §1),
- loading a **pure-Memoria background scene** (`.bgx`) + its overlay PNGs,
- loading the **walkmesh** (`.bgi.bytes`),
- loading the per-language **event script** (`.eb`),
- **cumulative mod text** (`.mes`) merged over the base block.

The after-battle freeze fix (the entry-0 tag-10 "Main_Reinit") is emitted as **script
bytecode** by the kit, not an engine change, so encounters work on stock Memoria too.

**Scrolling** (larger-than-screen rooms) is likewise pure data: the kit widens the scene's
`Range`/`Viewport` and emits the standard `EnableCameraServices` opcode, and Memoria's built-in
3D scroll does the panning. No engine change.

Several whole pillars are also stock-engine (no DLL): custom 3D **models**
(`model-gltf` / `model-import` / `model-mint` / `model-anim` / `model-export` — Memoria's loose-FBX
model importer already ships), custom **battle backgrounds**, custom **music and SFX**
(`audio-import`), **FMV** swaps, and custom **playable characters** (the `[[playable]]` block).

Install a built mod by copying its folder next to `FF9_Launcher.exe` and registering the folder
name in `Memoria.ini` under `[Mod] FolderNames` (or zip it with `ff9mapkit pack`). No DLL is
required for a novel field.

## Forked fields & the fidelity patch set

A **forked** field (`import --verbatim` / `--native` / `--editable`) reproduces a real field on a
custom id. Its *physical* layer — scene, walkmesh, camera, NPCs/props, dialogue, gateways,
encounters — works on **stock Memoria**. But FF9 hardcodes a number of behaviors against the
*original* field's id (`fldMapNo`), and those are lost when the fork runs under a new id:
narrow-map letterbox masking, a few off-mesh / after-battle / per-actor fixes, the overworld→field
entry redirect, and similar. They cannot be restored from script bytecode alone.

The bundled engine patch set restores them: **[`memoria-patches/`](../../memoria-patches/) `s23`–`s34`**
wrap the hardcoded `fldMapNo` engine gates with an *effective field id* (and an *effective field name*)
so they fire for a custom fork, and `s23` gives a forked narrow field the donor's exact tuned width.
`s34` is the one patch in the range that isn't a field-fork wrap: a loose **overworld-mesh override**,
required by the custom-overworld commands `world-reclaim` / `world-coast` / `world-entrance`. These
patches are applied to a local Memoria build; the showcase opening ships with that custom Memoria. The
disc-1 gates, the s30/s31 walk+occlusion and s33 menu-LOCATION fixes, and `s32` (proven in-game through
the fork-verification harness) are verified; some `s29` sites and `s33` sibling sweeps remain unverified
until those zones are forked and playtested. (The `s22` F6 debug menu also ships in the engine bundle —
a user-facing tool with four context-adaptive tabs, **Go / Cheats / Flags / Time**, available in the
field, in battle, and on the overworld — but it's not a fork-fidelity patch and isn't part of the
upstream-candidate set.)

The full per-behavior breakdown — stock, patch-restored, or genuinely engine-blocked — is in
[`FORK_FIDELITY.md`](FORK_FIDELITY.md) and [`FORK_IDGATE_MAP.md`](FORK_IDGATE_MAP.md) (the per-site
verification ledger); the per-file history and status of every patch in `memoria-patches/` (what each
file covers and folds, live vs dev-tool vs superseded vs upstream) is in
[`memoria-patches/README.md`](../../memoria-patches/README.md).

## Installing the custom engine

A **forked** field needs this engine, and so does overworld mesh authoring — every command that
emits loose mesh overrides (`world-terrain`, `world-reclaim`, `world-coast`, `world-water`,
`world-entrance`, `world-deploy`, `world-mesh-build`) relies on the `s34` mesh-override loader;
the atlas/texture, encounter, environment, and marker commands run on stock Memoria. A **novel**
field does not need it, and neither do the custom-models, battle-background, or audio pillars. Three ways to
get it:

1. **Windows installer / `ff9mapkit setup` (easiest).** The installer's "engine patches" task
   installs the bundled `dwix-custom-memoria-<version>.zip`; equivalently, run
   `ff9mapkit setup --install-engine <that-zip>`. Both back up the original DLLs automatically
   before overwriting.
2. **Pre-built bundle (manual).** Download `dwix-custom-memoria-<version>.zip` from the project's
   GitHub **Releases** and follow its `INSTALL.txt`: back up your `x64\FF9_Data\Managed\` and
   `x86\FF9_Data\Managed\` DLLs, then copy the bundle's three managed DLLs (`Assembly-CSharp.dll`
   + the matched `Memoria.Prime.dll` / `UnityEngine.UI.dll`) into **both** folders, overwriting.
   The bundle is a compiled, **MIT-licensed** Memoria build (© Albeoris) plus the Dream World IX
   patches, and ships **zero** game data. It's pinned to a specific Memoria base — if you run a much
   newer Memoria and hit crashes, use option 3.
3. **Build from source (version-robust).** Apply `memoria-patches/s23` + `s24` + `s29` + `s30` + `s31` + `s32` + `s33` + `s34` to a
   [Memoria](https://github.com/Albeoris/Memoria) source clone and compile `Assembly-CSharp` with
   VS MSBuild; this matches whatever Memoria version you build against. The build replaces your
   install's `Assembly-CSharp.dll`.

The clean long-term fix is **upstreaming** `s23`–`s33` into Memoria (they're small and
`EffectiveFieldId`-gated, so stock-game behavior is untouched) — then no custom engine is needed for
forked fields. `s34` is a different case — a new capability rather than an identity-safe fidelity
wrap — so whether it belongs upstream is a separate decision.

## Optional engine polish (not required)

Two small possible Memoria improvements would make the experience smoother; they are **not** needed
for a field to work, and the project isn't actively upstreaming them:

1. **Overlay texture cache** (`BGSCENE_DEF`): caches decoded overlay PNGs by path so field
   loads / battle-returns don't re-decode them.
2. **FieldCreatorScene PNG-path fix** (Memoria PR #1433, left as-is): the in-editor scene export writes overlay PNGs to the
   game root instead of the field folder, which black-screens the editor. (This kit's CLI
   pipeline doesn't use that editor, so the bug doesn't affect kit users — but fixing it
   makes the official in-engine editor usable as an alternative authoring path.)

## Data provenance / redistribution

**The kit ships no Final Fantasy IX game data** — the base assets it needs are regenerated from
your own install via `ff9mapkit extract-templates`. **Background art and walkmeshes you author are
yours;** the kit never ships copyrighted content. See [`PROVENANCE.md`](PROVENANCE.md) for the full
rationale and the patches-not-bytes mechanism.
