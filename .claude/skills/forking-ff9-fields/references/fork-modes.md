# Fork modes — the decision matrix + the object-carry checklist

Distilled from `ff9mapkit/docs/FORK_FIDELITY.md`, `FORK_REPORT.md`, `OBJECT_CARRY.md`,
`PLAYER_GRAFT.md`, `TEXT_CARRY.md` and memory `[[project-ff9-verbatim-fork]]` /
`[[project-ff9-object-carry]]`. Quotes are verbatim from those sources — read them for depth.

## Mode matrix

| Mode | Command | What it ships | When to pick |
|---|---|---|---|
| BG-borrow (plain) | `ff9mapkit import <field>` | The real field's art via DictionaryPatch — "BG-borrow with no object/text/func carry" (FORK_FIDELITY.md) | Quick reuse of real art under a room you author yourself |
| Editable | `ff9mapkit import <field> --editable` | "an AUTHORING SCAFFOLD, not a faithful playable clone — camera + walkmesh + art + the mechanical content, and you RE-AUTHOR the rest (NPCs/props/dialogue/events not carried)" (memory `project-ff9-verbatim-fork`) | Repaint/reshape a real field in Blender; you re-author the content |
| Native + carry flags | `ff9mapkit import <field> --native --graft-player-funcs --carry-text` | Seamless per-tile native scene + verbatim object graft + grafted player funcs + carried per-language text — declarative kit blocks stay editable | A faithful room you still want to edit declaratively |
| Verbatim | `ff9mapkit import <field> --verbatim` (implies `--native`) | "a real field's WHOLE .eb (entry-0 + all objects + all gateways, layout intact) + its whole .mes, remapping only Field() destinations" (memory `project-ff9-verbatim-fork`) | The MOST FAITHFUL fork — real story logic + real text |
| Verbatim chain | `ff9mapkit import-chain <seed> --verbatim` | Every member forks native + verbatim; in-chain `Field()` exits retargeted to the chain's own member ids (out-of-chain exits stay live seams) | A connected SLICE of the game, doors wired between the forks |

From FORK_FIDELITY.md ("Play a fork today"), verbatim:

> Note: faithful carry is **opt-in** (the three flags above). A plain `import` is BG-borrow with no
> object/text/func carry. For the most faithful single field use `import --verbatim`; for a connected region use
> `import-chain --verbatim` (each member runs its real logic + speaks, doors wired to siblings — the scenario-zero
> caveats above are then governed by each donor's real story gating, presettable per-member with `[startup]`).

What a non-verbatim faithful fork still does NOT get (FORK_FIDELITY.md, verbatim):

> **You don't get:** the field plays in its **scenario-zero state** — every story-gated NPC/door/event
> defaults to the not-yet-happened branch (hidden areas may be exposed, story NPCs absent); you **spawn at
> one fixed point** no matter which gateway you arrived through; any field-entry **cutscene won't auto-fire**
> from the C# table (re-author it declaratively with `[[on_entry]]` — a gated, once field-load beat); exit
> gateways warp correctly but **don't advance the ScenarioCounter** unless you add a `[[gateway]]`
> `set_scenario`/`set_flags`.

## The fork-report workflow (FORK_REPORT.md, verbatim)

> 1. `fork-report <field>` → pick a field whose verdict is **CLEAN static-roster** for a faithful fork (or accept
>    the diorama trade-off for a story-event field).
> 2. `fork-report <field> --explain` → read what the cast actually does; if its NPCs need their quest logic, fork
>    `--verbatim` (else `import --native --graft-player-funcs --carry-text`).
> 3. `ff9mapkit import <field> --native --graft-player-funcs --carry-text` (the recipe it suggests).
> 4. Add the suggested `[startup]` block so the fork boots in the right beat.

## Object-carry checklist

The carry surface, per `ff9mapkit/docs/OBJECT_CARRY.md` (verbatim):

> Carry is reached through `ff9mapkit import` flags `--graft-player-funcs` (player-tag ≥ 2 interactions
> fire — docs/PLAYER_GRAFT.md), `--carry-text` (verbatim real-words dialogue — docs/TEXT_CARRY.md), and
> `--save-moogle` (verbatim save point — docs/SAVEPOINT.md).

What is solved today (FORK_FIDELITY.md "Solved (faithful today)", verbatim lines):

> - **OBJECTS** — verbatim `.eb`-entry graft, STARTSEQ-helper closure, player-function graft, op78 expr-uid
>   remap, multi-`DefinePlayerCharacter` normalization.
> - **TEXT** — verbatim per-language `.mes` carry for grafted NPC tag-3 dialogue + text player funcs, remapped
>   to a clean TXID band; byte-identical when not carried.

Checklist when a fork looks or behaves wrong:

- **Lighting flat/bright?** The native fork must ship the donor's MapConfigData verbatim
  (`[field] mapconfig=`) — see memory `[[project-ff9-object-carry]]` follow-up #1.
- **Field particle effects (fire/smoke/glows) missing?** "the .sps bins + spt.tcb load by the RUNNING
  scene name, so a fork must CARRY the donor's" (memory `[[project-ff9-sps-fork]]`) — the kit stages an
  `sps/` sidecar; older forks may need a re-fork or backfill.
- **NPC talks but shows wrong/empty text?** Ship `--carry-text` (remaps the windows) or `--verbatim`
  (ships the whole donor `.mes`) — the fork-report Dialogue axis warns before you fork.
- **Interaction dropped to render-only?** `init_only` carry means its player tag was not grafted — add
  `--graft-player-funcs`, or the func is refused (text/exotic/non-Zidane/sibling): read
  `fork-report --explain` and consider `--verbatim`.
- **Whole-scene occlusion / fork behaviors off after deploy?** Check `ForkDonorPatch.txt` first — see
  `references/fork-gate-summary.md`.
- **Wrong donor entirely?** One FBG backs multiple field ids (one per story-visit); import by the exact
  numeric field id, not the FBG-name substring, when siblings exist.
