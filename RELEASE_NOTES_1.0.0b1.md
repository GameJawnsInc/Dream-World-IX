# Dream World IX 1.0.0b1 — first public beta

**Dream World IX** is a toolkit for building brand-new playable *Final Fantasy IX* fields — and
faithfully forking the real ones — for the [Memoria engine](https://github.com/Albeoris/Memoria)
(Steam FF9). Author a whole custom field (camera, walkmesh, painted background, NPCs, dialogue,
gateways, encounters, events, story branching, cutscenes) from a single declarative `field.toml` and
compile it into a drop-in mod — or **fork any of FF9's ~674 real fields** and carry their content
faithfully.

> This is an **early public beta**. The engine work is in-game proven, but expect rough edges in the
> docs and tooling. Bug reports and field-authoring questions are welcome.

## Getting started

- **[FORKING_FF9.md](FORKING_FF9.md)** — a guided GUI walkthrough: fork a slice of FF9, change a line
  of dialogue, and play it back. The fastest end-to-end taste of the toolkit.
- **[SETUP.md](SETUP.md)** — install, prerequisites, the dev loop, and your first field.
- **[ff9mapkit/docs/](ff9mapkit/docs/)** — the full toolkit reference and feature list.

## Highlights

- **Fork any real field** (`ff9mapkit import <field> --verbatim`) — camera, walkmesh, NPCs, props,
  dialogue, lighting, encounters, and story logic carried from the original.
- **Author original fields** from a declarative `field.toml`: painted backgrounds with depth occlusion,
  math-derived camera + walkmesh, NPCs, gateways, events, story flags, cutscenes, ladders, jumps, props,
  and save points.
- **Multi-field campaigns and journeys** — chain forked fields into a playable arc with a hub selector.
- **Custom 3D battle backgrounds** and battle/encounter tuning (no engine rebuild).
- **A PySide6 desktop Workspace** (`apps/ff9_workspace.pyw`) and a Blender add-on for visual authoring.
- **Offline lint + validation** so content errors are caught before the game ever loads.

## Engine bundle (required for forked fields)

A **novel** field (built from scratch or borrowing a real field's art) runs on a **stock, unmodified
Memoria** install. A **forked** field needs a small set of fork-fidelity engine patches.

**If you fork real fields, download `dwix-custom-memoria-1.0.0b1.zip` from the assets below** and follow
the install steps in [ff9mapkit/docs/ENGINE.md](ff9mapkit/docs/ENGINE.md). Disc-1 fork gates are in-game
proven; the newest late-disc softlock gates (s29) are still being playtested.

## Provenance

Dream World IX **ships no Final Fantasy IX game data.** Like a ROM-hack patcher, it operates only on
assets read from a copy of the game you legally own — regenerated from *your* install via
`ff9mapkit extract-templates`. It is an unofficial, fan-made tool, not affiliated with or endorsed by
Square Enix.

## License

[MIT](LICENSE) (© 2026 GameJawnsInc) — covers the Dream World IX / `ff9mapkit` source code only. The
bundled engine patches modify [Memoria](https://github.com/Albeoris/Memoria) (MIT, © Albeoris).

---

See **[Known issues](ff9mapkit/docs/KNOWN_ISSUES.md)** for current limitations and
**[Troubleshooting](ff9mapkit/docs/TROUBLESHOOTING.md)** when something breaks.
