# S6 — Danger

```toml
[tutorial]
track = "S"
step = 6
builds_on = ["s5-lights-camera"]
goal = "Random battles in your field — choose what spawns, how often, and win one."
requires = ["game", "gui", "assets"]
```

A field with no risk is scenery. This step arms random encounters — and picks the weakest ones
in the game, so the win is a win.

**Starting from:** any deployed room of the spine's pair.

## 1. Arm the field

In the Editor, open the **Encounter** section:

![The encounter form — battle scene by name, frequency, battle music](../../../docsite/assets/shots/editor-encounter_light.png)

- **Battle scene** — which monsters spawn: an id or a `BSC_` name; **Browse…** lists them.
  `BSC_EF_R007` is Evil Forest's pool — the first and weakest battles in FF9, the right pick for
  a first fight in a starter party's room.
- **Frequency (0-255)** — how often walking triggers a battle. The default 255 is relentless;
  `64` is a comfortable stroll with occasional trouble.
- **Battle music id** — blank keeps the normal battle theme.

One thing the form does silently but is worth knowing: adding an encounter also adds the
**after-battle re-entry handler** the field needs. Without one, a field freezes when the battle
returns — the kit wires it so yours doesn't.

## 2. Pick a fight

Deploy, **~ → Reload**, and walk. **What you should see:** within a stretch of walking, the
screen swirls into battle against Evil Forest monsters; win it, and the party lands back in the
room, walkable, with the field music resumed (S5's pick included).

If battles feel too frequent or too rare, that is the **Frequency** dial — one change, one
deploy, one walk: the S2 loop again.

## Next

- [S7 — Ship it](s7-ship-it.md): bundle the rooms into a campaign, point New Game at it, and
  package a zip.
- Scene pools, per-scene boss music, battle tuning: [`[encounter]`](../FORMAT.md#encounter-optional)
  · [`[[battle_bgm]]`](../FORMAT.md#battle_bgm-optional-array-of-tables) ·
  [BATTLE_DESIGN.md](../BATTLE_DESIGN.md).
