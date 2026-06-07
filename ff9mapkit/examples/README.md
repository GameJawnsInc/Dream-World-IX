# Examples

Worked `field.toml` projects. Build any with `ff9mapkit build <path>` (see
[`docs/TUTORIAL.md`](../docs/TUTORIAL.md) to get started).

| Example | Shows |
|---|---|
| [`SHOWCASE/`](SHOWCASE) | **Start here** — one field exercising most of the content stack: NPC + dialogue, a flag-gated NPC, a chest event, an encounter + BGM, and a narration cutscene. Builds offline with placeholder art. |
| [`vivi-hut/`](vivi-hut) | The original worked example — a painted interior with a talking NPC. Its build reproduces an **in-game-verified** script byte-for-byte (the golden master). |
| [`scroll-demo/`](scroll-demo) | A larger-than-screen **scrolling** field with painted layers + foreground occlusion. |
| [`blender-scroll-room/`](blender-scroll-room) | A scrolling room authored via the **Blender add-on** (camera + walkmesh exported, then `build`). |
| [`toolkit-test/`](toolkit-test) | A minimal net-new field used to prove the end-to-end pipeline. |

For the complete capability list see [`docs/FEATURES.md`](../docs/FEATURES.md); for how the hard parts
work, [`docs/TECHNICAL.md`](../docs/TECHNICAL.md).
