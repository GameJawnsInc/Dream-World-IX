# Known issues & limitations

This page maps the rough edges in the public beta — what's not wired up yet, what's
authored by hand rather than in a form, and the handful of things the engine genuinely can't do on
a custom field id. None of these block the core loop (fork or author a field → build → deploy →
play); they're the places where you'll reach for the CLI, a text editor, or Blender instead of the
GUI, or accept a faithful-but-not-identical result.

It splits into two parts: **[the Workspace GUI](#part-a--the-workspace-gui)** and
**[engine & authoring](#part-b--engine--authoring-limitations)**.

---

## Part A — the Workspace GUI

The desktop **Workspace** folds the authoring tools into one PySide6 window.
It's entirely optional — the CLI does everything without it.

### Launching it

There is **no `ff9mapkit gui` subcommand yet.** For an **installed** copy (pip / uv / the Windows
installer — no repo checkout), the launcher is the **`ff9mapkit-workspace`** entry point:

```powershell
ff9mapkit-workspace
```

From a repo checkout, launch the Workspace directly:

```powershell
py apps\ff9_workspace.pyw                  # the front door
# …or as a module:
py -m ff9mapkit.workspace.shell
```

(`pip install -e ".[gui]"` first, or `py -m pip install ff9mapkit[gui]`.) Note that the CLI's
`ff9mapkit edit` command opens an **older, single-field** Tkinter form editor — *not* the Workspace.

### The Workspace edits the logic layer, not the spatial layer

The Workspace authors a field's **logic** (the `field.toml`). It does **not** author the **spatial
layer** — camera angle, walkmesh geometry, and background art layers. Those are posed in **Blender**
(via the add-on → a `scene.toml`) or written by hand. In the editor tree, **Camera** appears as a
note pointing to Blender rather than an editable form, for exactly this reason: camera / walkmesh /
layers / positions are spatial. See the
[Blender add-on README](../blender/README.md).

### Only some `field.toml` sections have visual forms

These sections have dedicated forms in the editor:

> **Field**, **Dialogue**, **Encounter**, **Music**, **Cutscene**, **Party**, **Startup beat**,
> **NPCs**, **Gateways**, **Events**, **Chests**, **Flags**, **Markers**, **Choices**, and
> **Effects (SPS)**. (**Camera** is a tree note pointing to Blender — see above.) Shared `[[flag]]`
> tables also have modal editors at campaign and journey scope.

Every **other** documented section is authored **directly in TOML** (by hand or in your editor of
choice) — including `[[prop]]`, `[[ladder]]`, `[[jump]]`, `[[savepoint]]`,
`[[on_entry]]`, `[start_inventory]`, `[[equipment]]`, `[[shop]]`, `[[item_text]]`, and the
ATE blocks. The full schema for all of these is in [`FORMAT.md`](FORMAT.md). A field's TOML and its
forms stay in sync, so hand-edited sections coexist with form-edited ones in the same file.

### The campaign Map view is read-only

The campaign **Map** shows the field graph (which field exits to which), but it's a **viewer, not a
canvas** — there's no drag-to-place or draw-a-connection yet. To change the graph, open a node and
edit its gateways/exits in the form.

### A failed background job can grey its buttons

A background job (Build / Import / Deploy) that fails to **launch** can leave its panel buttons
greyed out until you reopen the window. This is a known bug; reopening the Workspace clears it.

### Some CLI features have no GUI surface yet

A number of commands are CLI-only for now — use the terminal for:

- `export-art` (offline background-PNG assembly),
- the paint-guide / from-scratch art workflow (`guide`, the paint template),
- the custom-model suite (`model-gltf` / `model-import` / `model-mint` / `model-anim` /
  `model-export`),
- the `world-*` overworld suite (terrain, reclaim, coast, water, entrances, encounters, atlas),
- `audio-import` (custom music / SFX) and `music-list` / `sfx-list`,
- `logic-map` / `lint-eb` (whole-script analysis of a verbatim fork — the Script panel covers the
  edit flow, not these reports).

(`import-chain`, `import-all`, and whole-campaign / journey builds are no longer on this list — the
Import tab has panels for the first two, and the Build & Deploy tab compiles and deploys campaigns
and journeys.)

### Custom hub art is set in the TOML, not the dialog

The **New Journey → World Hub** dialog takes the hub's background as a single free-text "borrow a
real field" value (a FBG/MAPID like `N11_HUT`). Fuller custom hub art — setting the hub field's
`area` and `borrow_field` explicitly — is done by editing the generated `journeys.toml` afterward.
See [`JOURNEYS.md`](JOURNEYS.md).

### A dialogue edit can be "(saved)" yet still show the old line in-game (text-block shadow)

A saved Script-panel edit still needs a rebuild + redeploy, and can be shadowed by a higher-priority
mod folder's copy of the same text block — full symptom → cause → fix in
[`TROUBLESHOOTING.md`](TROUBLESHOOTING.md#wrong-dialogue-but-correct-behavior--or-a-saved-edit-that-still-shows-the-old-line).

---

## Part B — engine & authoring limitations

These are the structural limits — what depends on the bundled engine patches, and the small set of
behaviors that are genuinely blocked on a custom field id even with them.

### Novel fields run on stock Memoria; forked fields want the patch set

A **novel** field (from scratch, or borrowing a real field's background art) runs on a **stock,
unmodified Memoria** install — no engine patching needed.

A **forked** field reproduces its *physical* layer (scene, walkmesh, camera, NPCs/props, dialogue,
gateways, encounters) on stock Memoria too, but FF9 hardcodes a number of behaviors against the
*original* field's id — narrow-map letterbox masking, a few off-mesh / after-battle / per-actor
fixes, the overworld→field entry redirect. Those are lost when the fork runs under a new id and
**cannot be restored from script bytecode alone.** The bundled fidelity patch set
([`memoria-patches/`](../../memoria-patches/), `s23`–`s33`) restores them for fork fidelity;
the bundle also carries `s22` (the in-game debug menu (~)), `s34` (the worldmap mesh-override
lever behind the `world-*` mesh commands), and the `s36`–`s41` netsync patches (experimental
co-op). The showcase opening ships with that custom
Memoria build. Exactly what's stock vs. patch-restored is in [`ENGINE.md`](ENGINE.md).

### A few behaviors are engine-blocked even with the patches

A small set of behaviors are keyed to a real field id (or a fixed compile-time engine structure) in
ways that no script and no `fldMapNo` wrapper can reach. These remain genuinely blocked on a custom
id:

- a **brand-new FMV slot** (beyond the existing movie table) plus its paired audio,
- **ATE seen-state / trophy bookkeeping** on a custom id (the ATE itself plays fine; only the
  achievement bookkeeping is id-bound).

(A custom **playable party member** is no longer on this list — the `[[playable]]` block defines
and recruits one with zero engine changes; see
[`examples/thirteenth-character/`](../examples/thirteenth-character/).)

The full per-behavior breakdown — stock, patch-restored, or genuinely engine-blocked, with the
stock-Memoria workaround for each — is in [`FORK_FIDELITY.md`](FORK_FIDELITY.md).

### Custom overworld — shipped, with residual limits

The custom-overworld pillar shipped in 1.0.0b12. The `world-*` suite reshapes walkable terrain
(`world-terrain`), reclaims ocean cells as land (`world-reclaim`), carries real coastlines onto
reclaimed ocean (`world-coast`), synthesizes graded open-ocean water (`world-water`), and adds a
new overworld entrance into a custom field (`world-entrance`), alongside encounter, texture, and
minimap tooling. `world-reclaim` / `world-coast` / `world-entrance` need the bundled `s34` engine
patch; the texture, encounter, and environment commands run on stock Memoria.

The residual limits: there is no full brand-new `WorldScene` mint — all overworld authoring edits
the real world map in place; coastlines are placed from real coastal tiles rather than drawn from
scratch; and continent-scale layouts and texturing brand-new geometry remain frontier work. A
multi-field structure that doesn't need the overworld is still built as a **field-chain campaign**
(`import-chain` + a `campaign.toml`, or a `journeys.toml` over several campaigns). Engine detail:
[`OVERWORLD_ENGINE.md`](OVERWORLD_ENGINE.md).

### Per-door arrival spawn needs `--verbatim`

A **synthesized** (non-`--verbatim`) fork can't reconstruct a field's per-door arrival table — it
spawns the player at one fixed point regardless of which gateway they entered through. When the
**entry door matters** (a room with several entrances arriving at different spots), fork with
**`import --verbatim`**, which carries the donor's real entry logic. This is a faithful-fork choice,
not a bug — the synthesized path trades that detail for editability.

---

## See also

- [`ENGINE.md`](ENGINE.md) — stock vs. enhanced Memoria, and the full engine-bundle patch map.
- [`FORK_FIDELITY.md`](FORK_FIDELITY.md) — the full map of what a fork does and doesn't reproduce.
- [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) — first-run failures as symptom → cause → fix.
- [`FORMAT.md`](FORMAT.md) — the complete `field.toml` schema (every section above).
- [`../../SETUP.md`](../../SETUP.md) — install, the dev loop, and the GUI overview.
