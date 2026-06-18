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

Install a built mod by copying its folder next to `FF9_Launcher.exe` (or zip it with
`ff9mapkit pack`). No DLL is required for a novel field.

## Forked fields & the fidelity patch set

A **forked** field (`import --verbatim` / `--native` / `--editable`) reproduces a real field on a
custom id. Its *physical* layer — scene, walkmesh, camera, NPCs/props, dialogue, gateways,
encounters — works on **stock Memoria**. But FF9 hardcodes a number of behaviors against the
*original* field's id (`fldMapNo`), and those are lost when the fork runs under a new id:
narrow-map letterbox masking, a few off-mesh / after-battle / per-actor fixes, the overworld→field
entry redirect, and similar. They cannot be restored from script bytecode alone.

The bundled engine patch set restores them: **[`memoria-patches/`](../../memoria-patches/) `s23`–`s28`**
wrap the hardcoded `fldMapNo == N` engine gates with an *effective field id* so they fire for a
custom fork, and `s23` gives a forked narrow field the donor's exact tuned width. These patches are
applied to a local Memoria build; the showcase opening ships with that custom Memoria. (The `s22`
F6 debug menu is a **dev-only** convenience and is *not* part of the shipped engine.)

The full per-behavior breakdown — stock, patch-restored, or genuinely engine-blocked — is in
[`FORK_FIDELITY.md`](FORK_FIDELITY.md) and [`FORK_IDGATE_MAP.md`](FORK_IDGATE_MAP.md).

## Optional engine polish (nice-to-have, not required)

Two small possible Memoria improvements would make the experience smoother; they are **not** needed
for a field to work, and the project isn't actively upstreaming them:

1. **Overlay texture cache** (`BGSCENE_DEF`): caches decoded overlay PNGs by path so field
   loads / battle-returns don't re-decode them.
2. **FieldCreatorScene PNG-path fix** (Memoria PR #1433, left as-is): the in-editor scene export writes overlay PNGs to the
   game root instead of the field folder, which black-screens the editor. (This kit's CLI
   pipeline doesn't use that editor, so the bug doesn't affect kit users — but fixing it
   makes the official in-engine editor usable as an alternative authoring path.)

A stretch goal is contributing the kit's camera math to fix the editor's degenerate
flat-floor camera-anchor solver.

## Data provenance / redistribution

**The kit ships no Final Fantasy IX game data** — the base assets it needs are regenerated from
your own install via `ff9mapkit extract-templates`. **Background art and walkmeshes you author are
yours;** the kit never ships copyrighted content. See [`PROVENANCE.md`](PROVENANCE.md) for the full
rationale, the patches-not-bytes mechanism, and the airtight guarantee.
