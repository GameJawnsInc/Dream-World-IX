# Engine requirements & notes

## Runs on stock Memoria

A field built by this kit needs **no engine modifications**. Everything it relies on already
ships in [Memoria](https://github.com/Albeoris/Memoria):

- the `FieldScene` **DictionaryPatch** directive that registers a custom field id,
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
`ff9mapkit pack`). No DLL is shipped or required.

## Optional engine polish (nice-to-have, not required)

Two small Memoria improvements make the experience smoother; they are **not** needed for a
field to work and are intended to be upstreamed so everyone benefits:

1. **Overlay texture cache** (`BGSCENE_DEF`): caches decoded overlay PNGs by path so field
   loads / battle-returns don't re-decode them.
2. **FieldCreatorScene PNG-path fix**: the in-editor scene export writes overlay PNGs to the
   game root instead of the field folder, which black-screens the editor. (This kit's CLI
   pipeline doesn't use that editor, so the bug doesn't affect kit users — but fixing it
   makes the official in-engine editor usable as an alternative authoring path.)

A stretch goal is contributing the kit's camera math to fix the editor's degenerate
flat-floor camera-anchor solver.

## Data provenance / redistribution

**The kit ships no Final Fantasy IX game data.** The base assets it needs (a cleaned "blank"
field script + an exit-region template + the test fixtures) are *derived* from FF9 field data,
so instead of bundling them the repo ships only our copy/insert **patches** (our edits + copy
offsets, never game bytes) and a SHA-256 manifest; `ff9mapkit extract-templates` regenerates the
assets from the user's **own** install into a local cache. See [`PROVENANCE.md`](PROVENANCE.md)
for the full rationale + the airtight guarantee (no insert run ever duplicates a source-file run).
**Background art and walkmeshes you author are yours;** the kit never ships copyrighted content.
