# Known issues & limitations

This is an honest map of the rough edges in the public beta — what's not wired up yet, what's
authored by hand rather than in a form, and the handful of things the engine genuinely can't do on
a custom field id. None of these block the core loop (fork or author a field → build → deploy →
play); they're the places where you'll reach for the CLI, a text editor, or Blender instead of the
GUI, or accept a faithful-but-not-identical result.

It splits into two parts: **[the Workspace GUI](#part-a--the-workspace-gui)** and
**[engine & authoring](#part-b--engine--authoring-limitations)**.

---

## Part A — the Workspace GUI

The desktop **Workspace** (`apps/ff9_workspace.pyw`) folds the authoring tools into one PySide6 window.
It's entirely optional — the CLI does everything without it — and it's the youngest part of the kit,
so it has the most gaps.

### Launching it

There is **no `ff9mapkit gui` subcommand yet.** Launch the Workspace directly:

```powershell
py apps\ff9_workspace.pyw                  # the front door
# …or as a module:
py -m ff9mapkit.workspace.shell
```

(`pip install -e ".[gui]"` first, or `py -m pip install PySide6`.) Note that the CLI's
`ff9mapkit edit` command opens an **older, single-field** Tkinter form editor — *not* the Workspace.

### The Workspace edits the logic layer, not the spatial layer

The Workspace authors a field's **logic** (the `field.toml`). It does **not** author the **spatial
layer** — camera angle, walkmesh geometry, and background art layers. Those are posed in **Blender**
(via the add-on → a `scene.toml`) or written by hand. In the editor the **Camera** form is
**read-only** for exactly this reason: camera / walkmesh / layers / positions are spatial, so the
form points you to Blender rather than letting you edit them there. See the
[Blender add-on README](../blender/README.md).

### Only some `field.toml` sections have visual forms

About ten sections have dedicated forms in the editor:

> **Field**, **Camera** (read-only), **Dialogue**, **Encounter**, **Music**, **Cutscene**, **NPCs**,
> **Gateways**, **Events**, **Markers**, **Choices**.

Every **other** documented section is authored **directly in TOML** (by hand or in your editor of
choice) — including `[[prop]]`, `[[ladder]]`, `[[jump]]`, `[[savepoint]]`, `[[flag]]`, `[startup]`,
`[[on_entry]]`, `[party]`, `[start_inventory]`, `[[equipment]]`, `[[shop]]`, `[[item_text]]`, and the
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

- `import-chain` in its general form (forking an arbitrary connected region),
- `import-all` (the bulk Blender-ready archive),
- `export-art` (offline background-PNG assembly),
- the paint-guide / from-scratch art workflow (`guide`, the paint template),
- `build-all` (compiling a whole `campaign.toml`).

### Custom hub art is set in the TOML, not the dialog

The **New Journey → World Hub** dialog takes the hub's background as a single free-text "borrow a
real field" value (a FBG/MAPID like `N11_HUT`). Fuller custom hub art — setting the hub field's
`area` and `borrow_field` explicitly — is done by editing the generated `journeys.toml` afterward.
See [`JOURNEYS.md`](JOURNEYS.md).

### A dialogue edit can be "(saved)" yet still show the old line in-game (text-block shadow)

Rewriting a verbatim fork's shipped dialogue in the **Script** panel and seeing **"(saved)"** only means
the edit is recorded in the field's `field.toml` (as a `[[logic_edit]]`). Two more things have to be true
for it to appear in-game:

1. **Rebuild + redeploy.** GUI save does **not** touch the `.mes` — the build rewrites it. Re-run
   `py tools/deploy_field.py …` (single field) or, for a journey/campaign member,
   `py tools/deploy_campaign.py <campaign.toml> --apply` / `py tools/deploy_journey.py <journeys.toml> --apply`,
   then **F6 → Reload field** (or relaunch). An F6 reload *without* a redeploy just re-reads the stale `.mes`.

2. **No text-block shadow.** A field reads dialogue from `field/<text_block>.mes`, and the engine serves
   that block from the **highest-priority** folder in `Memoria.ini FolderNames`. Campaign members and
   worktree test slots all default to the shared block **1073**, so if a higher-priority folder (a churned
   master `FF9CustomMap`, a leftover prior-journey folder, …) also defines 1073, it **shadows** your
   edit — the engine shows *that* folder's old text, not yours. (The same gotcha hits `[[on_entry]]` lines.)

The deploy step guards this: `deploy_field` **and** `deploy_campaign` / `deploy_journey` run the text-block
**shadow check** and print a `TEXT SHADOWED: …` warning that names the blocking folder and a safe alternative
block; the Script panel also flags a dialogue edit on the shared default 1073 as a heads-up. **Fixes:**
deploy your folder higher in `FolderNames`, remove the higher folder's copy of the block, or pin a unique
`[field] text_block` (any real mesID no higher folder defines). Diagnose directly:

```powershell
py -c "from ff9mapkit.deploystack import check_text_block_shadow, shadow_warning; from ff9mapkit.config import find_game_path; print(shadow_warning(check_text_block_shadow(find_game_path(None), '<your-mod-folder>', <block>)) or 'clear')"
```

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
**cannot be restored from script bytecode alone.** The bundled engine patch set
([`memoria-patches/`](../../memoria-patches/), `s23`/`s24`/`s29`) restores them for fork fidelity, and the
showcase opening ships with that custom Memoria build. Exactly what's stock vs. patch-restored is in
[`ENGINE.md`](ENGINE.md).

### A few behaviors are engine-blocked even with the patches

A small set of behaviors are keyed to a real field id (or a fixed compile-time engine structure) in
ways that no script and no `fldMapNo` wrapper can reach. These remain genuinely blocked on a custom
id:

- a **brand-new FMV slot** (beyond the existing movie table) plus its paired audio,
- a **13th playable party member** (the character roster is a fixed compile-time enum with a
  fixed-layout save),
- **ATE seen-state / trophy bookkeeping** on a custom id (the ATE itself plays fine; only the
  achievement bookkeeping is id-bound).

The full per-behavior breakdown — stock, patch-restored, or genuinely engine-blocked, with the
stock-Memoria workaround for each — is in [`FORK_FIDELITY.md`](FORK_FIDELITY.md).

### No custom overworld / world map

There is no `WorldScene` mint, so a **custom overworld is not supported.** A multi-field structure is
built as a **field-chain campaign** (`import-chain` + a `campaign.toml`, or a `journeys.toml` over
several campaigns), not as a navigable world map. The overworld is the hardest unstarted piece; see
[`FORK_FIDELITY.md`](FORK_FIDELITY.md).

### Per-door arrival spawn needs `--verbatim`

A **synthesized** (non-`--verbatim`) fork can't reconstruct a field's per-door arrival table — it
spawns the player at one fixed point regardless of which gateway they entered through. When the
**entry door matters** (a room with several entrances arriving at different spots), fork with
**`import --verbatim`**, which carries the donor's real entry logic. This is a faithful-fork choice,
not a bug — the synthesized path trades that detail for editability.

---

## See also

- [`ENGINE.md`](ENGINE.md) — stock vs. enhanced Memoria, and the `s23`/`s24`/`s29` patch set.
- [`FORK_FIDELITY.md`](FORK_FIDELITY.md) — the full, honest map of what a fork does and doesn't reproduce.
- [`FORMAT.md`](FORMAT.md) — the complete `field.toml` schema (every section above).
- [`../../SETUP.md`](../../SETUP.md) — install, the dev loop, and the GUI overview.
