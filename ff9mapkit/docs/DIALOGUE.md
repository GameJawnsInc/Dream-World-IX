# Dialogue — author, preview, and view FF9 field text

The dialogue pillar covers the **words** of a field: writing them well-formatted, previewing how they wrap
on the FF9 screen, and **reading real FF9 dialogue back out** of the game (to view the original writing, or
to lift it into your own room). It complements the Logic Editor (which owns *structure* — who stands where,
which option gives what) and the camera/walkmesh tools (placement, owned by Blender).

It's available two ways: the **CLI** (`ff9mapkit dialogue` / `dialogue-import`) and the **PySide6
Workspace** (`apps/ff9_workspace.pyw`), where every dialogue-bearing field (`dialogue` / `message` /
`prompt` / `reply`) gets a live FF9-window wrap preview right in the editor forms. Both sit on one tk-free
core, `ff9mapkit.dialogue`.

---

## Where dialogue lives in a `field.toml`

Dialogue is authored in-place across the content sections — there's no separate "dialogue" block (only an
optional `[dialogue] wrap` width knob):

| Section | The text |
|---|---|
| `[[npc]]` | `dialogue = "..."`, optional `speaker`, optional `tail` (window-pointer corner) |
| `[[event]]` | `message = "..."` (+ `speaker` / `tail`) |
| `[[choice]]` | `prompt = "..."` and each option's `reply = "..."` |
| `[cutscene]` | each `{ say = "..." }` step |

At build time the kit collects all of it, applies the speaker prefix + auto-wrap, and writes one
`<text-block>.mes` (default block `1073`) plus the `WindowSync` opcodes that show each line. **That whole
path is unchanged** — this pillar only *reads* and *previews*.

### Well-formatted text (the wrap preview)

FF9 does **not** auto-wrap: the window grows to fit the widest line, so a long unbroken line runs off the
screen. The kit pre-breaks lines using a proportional glyph model (`W`/`M` are ~3× as wide as `i`/`l`).
It's an approximation (the in-game font is a runtime TrueType, so pixel-exact wrapping is impossible
offline), tuned to break a hair early so it never overflows. The editor's **live preview** shows exactly
how each line will break, and warns when an unbreakable over-wide word remains. Tune per field with
`[dialogue] wrap = <units>` (default 28; `wrap = false` turns wrapping off and you hand-break with `\n`).

---

## CLI

### View a field's authored dialogue
```
ff9mapkit dialogue examples/SHOWCASE/showcase.field.toml [--clean]
ff9mapkit dialogue path/to/campaign.toml                   # review EVERY member field at once
```
Lists every line with its final on-screen wrapping; `--clean` strips FF9 control tags for a plain read.
Flags any line that may still overflow. Pass a **`campaign.toml`** (a `[campaign]` manifest) instead of a
single field and it auto-detects it and reviews every member field in member order — per-field sections
plus a roll-up (total lines, which fields may overflow). A member that fails to load is noted and skipped,
never aborts the review.

### Import / view real FF9 dialogue
```
ff9mapkit dialogue-import 100 --lang us                     # a real field, live from your install
ff9mapkit dialogue-import alxt_map016                       # by FBG-name substring (Alexandria is ALXT, not "alexandria")
ff9mapkit dialogue-import HUT_INT --mod release/FF9CustomMap  # a built mod folder — NO install needed
ff9mapkit dialogue-import 100 --zone-id 33                  # read the field's <33>.mes text block directly
ff9mapkit dialogue-import 100 --all                        # also show system/notification windows + dupes
ff9mapkit dialogue-import 100 --out alex.dialogue.json      # also write a JSON view (gitignored)
```
Prints `NPC → txid → "text"`. Reading the live install needs UnityPy (`py -m pip install UnityPy`). When a
real field's lines come back **unresolved**, the note says *why* — UnityPy not installed, the install /
`resources.assets` not found (pass `--game`), or "the source is fine, this field's block just didn't cover
these txids; pass `--zone-id`."

**By default it shows only real dialogue.** Windows whose flags lack the `0x80` text-box bit are
**system/notification** windows (a field's "Error …" guard, the "Received item!" popups) — hidden unless
`--all`. A line referenced from several funcs of one object is collapsed to one row (preferring the NPC-talk
representation). And the `@x,z` position is shown only for kit-built mod folders — on a *real* field it's the
player-clone's `D9(0)/D9(4)` convention, meaningless for the field's own NPCs, so it's suppressed.

The **offline proof**: the kit's own shipped hut (`release/FF9CustomMap`) decodes its `.eb`, parses its
`.mes`, and joins to *"I miss you Zidane"* with zero game install — the whole pipeline, provable in tests.

### Re-author a fork's dialogue (`import --dialogue`)
```
ff9mapkit import <field> --dialogue --out F     # fork a field AND bring its dialogue in to re-author
```
Appends the real field's NPC lines to the imported `field.toml` as ready-to-use `[[npc]]` blocks (real model
resolved by GEO name so anims auto-resolve, the line as clean editable text, a `pos = [0, 0]` placeholder) —
the "fork a field and rewrite its script" workflow. They're emitted **commented out**: a fork already
carries the field's NPCs verbatim as `[[object]]` (object-carry), so these *parallel* them — uncomment the
ones you want to re-author, reposition + rewrite, and drop the matching `[[object]]` if you're replacing it.
They become **kit-authored content** (re-wrapped at build), not a faithful graft.

---

## Workspace (the GUI)

There's no separate dialogue surface — dialogue is edited **in place** in the field editor forms of the
PySide6 Workspace (`apps/ff9_workspace.pyw`). Any field whose value shows in an FF9 text window —
`dialogue`, `message`, `prompt`, `reply` — is a multi-line text box (Enter is a real line break, `[PAGE]`
opens a new window) with a **live wrap preview** pinned underneath: it shows exactly where each line will
break on the FF9 screen as you type, and warns when a line may overflow the window. The preview reuses the
same build-time wrapper (`dialogue.wrap_preview` / `dialogue.overflow`), and honours the field's
`[dialogue] wrap` width (`wrap = false` shows the line raw). Saving writes the same `.field.toml` the rest
of the editor uses.

To read real FF9 dialogue inside the Workspace, use the **Import** view: its **"View dialogue"** action
(field id/name + language) runs `dialogue-import` and streams the joined `NPC → txid → "text"` lines into
the Output panel. The same view's fork options carry a real field's dialogue verbatim ("Real dialogue,
verbatim") or bring it in as editable `[[npc]]` stubs to re-author ("Dialogue as editable [[npc]] stubs").

---

## How the import works (the two read directions)

To show "NPC says X" for a real field, the spine reads two independent stores and joins on **txid**:

1. **The `.eb` → dialogue calls.** `scan_dialogue` walks the field script and collects every dialogue-window
   opcode (`WindowSync`/`WindowAsync` `0x1F`/`0x20`, the `…Ex` variants `0x95`/`0x96`) and the **text id** it
   shows (an immediate operand). An NPC's talk handler is func tag 3; other tags are event/cutscene lines.
2. **The `.mes` → text.** A field's text file is `<zone-id>.mes`, named by the field's **text-zone id**
   (`1073` for a custom field; a small id like `33` = Alexandria for a real one). Base-game `.mes` entries
   are **index-implicit** — there are *no* `[TXID=n]` tags; the txid is just the entry's 0-based position
   (`[STRT=..]text[ENDN][STRT=..]text[ENDN]…`, exactly as Memoria's `FF9TextTool.ExtractSentense` reads it).
   `parse_mes` handles both that and the kit's explicit `[TXID=n]` form.
3. **Join** on txid → the viewable lines.

The field → text-zone-id map is the engine's own `eventIDToMESID` table (baked into the kit as
`_fieldtext.EVENT_ID_TO_MES`), so `dialogue-import` reads the **right** block directly — txids are 0-based
positions every field's text shares, so they can't identify the block alone. Among a block's per-language
copies (resources.assets carries no language in the path) the requested language is picked by stopword
match. `--zone-id <n>` overrides the table; the `.eb` decode is exact regardless.

## Provenance

Real FF9 dialogue is Square-Enix text. The kit **never commits it** — `dialogue-import` reads it live from
*your* install (or your built mod), and the optional `--out` sidecar uses the `*.dialogue.json` suffix that
`.gitignore` excludes. Only the dialogue **you write** (in a `field.toml`) belongs in the repo.
